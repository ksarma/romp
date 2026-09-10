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
| `romp refresh` | Restart every kernel immediately through the manager, then the postal bus, picking up new code (cut turns resume with their history). Exits 3 when the manager answered and refused the restart (see [The manager's control port](#the-managers-control-port)): nothing restarted, the bus included |
| `romp update [host…]` | Push this machine's committed Romp to attached remotes and restart them at once (every deploy restart is immediate; boot reconcile resumes the cut turns with their history); a remote stopped by `romp down` is synced and left stopped |
| `romp up` | Start the kernel: through the login service when one is installed, in the foreground otherwise. Clears a `romp down` marker |
| `romp down` | Stop the kernel and keep it stopped until `romp up`. Turns in flight get 5 seconds to finish first; sessions resume with their history at the next start. See [Stopping the kernel on purpose](#stopping-the-kernel-on-purpose) |
| `romp version` | Version report across the moving parts |
| `romp spend-rebuild [--apply] [--by-session] [--allow-lower]` | Recount the spend ledger's token columns (`spend.json`) from the transcripts' per-call usage; dollars and turn counts untouched. A dry run by default; `--apply` writes and keeps a backup; a bucket whose recount is lower than recorded is kept unless `--allow-lower` (a transcript may be gone) |
| `romp help` | The same list, from the terminal |

**Update notices.** Romp watches for new tagged releases and, on a checkout that tracks
`main`, for new commits, and offers each one once as a banner with an Update button. The gear's
**Automatic updates** control (under *Updates & debug*) decides what happens: *Check and
ask* shows the banner, *Install automatically* converges on its own, and *Off* stops both the
checks and the banners, so a machine whose owner merges to `main` all day hears nothing about it
and keeps running what it has until they restart Romp themselves. An automatic converge takes one
of two routes, decided by what the new commits touch. When the new commits change code the
running kernel executes, Romp restarts at once, and the restart cuts the turns in flight, which
resume with their history on the new code; a comment or formatting edit that leaves that code's
parsed form unchanged does not count. A change anywhere else (the UI, the docs, the CLI, the
postal bus, tests) converges in place with the kernel left up: the served bundles are rebuilt, a
postal change restarts the bus alone, and no turn is cut. A converge to `main` in
this mode comes no sooner than 25 minutes after the last deploy restart, so a busy `main` costs
at most one restart per batch of merges. The one command that waits for a quiet window is
`romp refresh --quiet`. Reloads are separate from that control and happen in every
mode: a page the kernel serves reloads itself when the kernel serving it restarts or serves a
newer build than the page runs, once any gesture in progress has ended and any file still
shipping has settled, and the notification center's one line says which happened. The banner that
reads "A newer romp build is available" appears only where the page cannot reload itself, such as
a host that forbids it; the VS Code panes keep their own prompt, because their bundle comes from
the installed extension. A chat page with an attachment still uploading first finishes the
upload, then reloads. The message waiting on the upload is sent if that session's tab is the
active one; otherwise it stays in that tab's composer with the file attached, and a notice says
so. A notice still on screen when the page reloads, that one or a failed save's, is shown again
on the fresh page. If the upload has not finished within a minute, the page reloads anyway and
reports the lost attachment on the next load.

**User todos.** A session can flag a decision or an input it needs from you and keep working
meanwhile. Each open todo is listed under *Waiting on you* on the card at the bottom of that
session's transcript, with Reply and Dismiss, and a session that resumes after a restart or a
compaction is handed its open todos back so it can withdraw the ones that no longer apply. A
session that withdraws a todo you already answered or dismissed, or one it already withdrew, is
told so plainly, with the time, and not handed an error; only an id that is unknown or another
session's is refused as one. A withdrawal the kernel cannot carry out is refused, never reported
as closed: a todo held on an attached machine the kernel cannot reach, or one running older
romp, is reported as still standing, and a stored todo whose closing record is damaged is
reported as unreadable, with the record named. The feature is off by default. The gear's **User todos** checkbox (under *Sessions*) turns it on for
one machine at a time: each kernel keeps its own copy, and the choice does not spread to other
attached machines. While it is off, sessions on that machine are not offered the tools that flag
or withdraw a todo, nothing is listed, and nothing is handed back on resume. Todos flagged
earlier stay stored and reappear when you turn it back on; the kernel's log says how many are
waiting. Every filing, answer, dismissal and withdrawal is also appended to `user-todos-log.jsonl`
beside the store under Romp's state directory, one line per event and never rewritten, so the list
can be rebuilt if the store is ever lost. The **Waiting on you** pane (bottom bar, off by default)
collects every open todo across all sessions and attached machines into one list with the same
Reply and Dismiss; because the switch is per machine, the pane says when it is off on this one and
still lists the other machines' todos. A file path in the one-line text or in the detail is a link
that opens the file, on the session's card and in the pane alike. Paths that link: absolute, `~/`, `./`
and `../` paths, relative paths whose last segment has a file extension, and `file://` URIs. A bare path
is made of ASCII letters, digits and `_ . ~ / -` only, so any other character ends it (a space, `+`, `#`,
`(`, `@`, `=`, `%`, `:`, an accented letter); a `file://` URI runs to the next whitespace, angle bracket,
quote, backtick or closing parenthesis. Sentence punctuation at the end of either is left out of the
link, as is a trailing `/` or `~`, and a token holding a doubled `//` is not a path. A relative path is read against the working directory of the session that flagged it.
An http or https address in the text or the detail is a link too, shown as typed and opened in a new tab;
it runs to the next whitespace, quote, angle bracket or backtick, sentence punctuation after it stays
outside the link, and so does a closing bracket the address itself did not open (`(see https://example.invalid/a)`
links the address alone). A path-shaped run inside an address is part of the address, never a file link.
A todo can also name the file it is about, through the tool's `file` argument. The kernel that holds the
session makes the path absolute and stores it: `~` is expanded, a relative path is read against the
session's working directory like one in the text, and a `file://` URI becomes its path. The todo shows the
file as a chip that opens it, on the session's card and in the pane alike, and a comment you send from that
file's Comments panel offers to answer the todo however you opened the file. The kernel does not check that
the file exists. A mistyped absolute path is stored as typed, with no warning; its chip opens nothing and no
Send offers the todo. It is cleared like any other todo, by your Reply or Dismiss or by the session's
withdraw. A value the kernel cannot make into a path on the session's machine is kept as given: the todo is
still filed, and the tool's reply says why and asks for the absolute path. That happens for a relative path from
a session whose working directory the kernel does not know, a `file://` URI that does not carry an absolute
path, a URL of another scheme, and a spelling no path can have (a NUL byte in it, or a length past the
machine's limit). The list a resuming session is handed back shows the path after the text of each todo that
names one. A todo can carry a web address of its own as well, through the tool's `link` argument: an http or
https address, shown as a chip beside the file's on the session's card and in the pane alike, opening in a new
tab. The chip's label keeps the part that tells two addresses apart: a GitHub `pull/N` or `issues/N` address
reads `owner/repo#N`, any other address as its host and last two path segments; the whole address is on hover. Only
such an address is taken: anything else (another scheme, a bare host, a value with whitespace or a character that does not print in it, one past
2048 characters) is refused, the todo is not filed, and the tool's reply says why. The kernel does not fetch the
address, so a mistyped host is stored as typed. The handed-back list shows the address after the path. A todo's
text takes at most 300 characters and its detail 4000, a pinned note's bounds; a longer one is refused before
anything is filed, and the tool's reply names the bound.

**Pinned notes.** A session can pin a short note above its own transcript: what you should see
first whenever you open it, such as where things stand, a warning, or a summary. The notes sit in
a strip between the tab bar and the transcript, oldest first, and the strip takes no space while a
session has none. Each row is one line, and every row's full text is its title, so a hover reads
any note whole on a desktop. A text the row cannot show whole ends in an ellipsis; its full text
sits behind the row's *details* hint, as does any detail the session added, and a row that shows
its whole text has no hint. Whether a row is cut is measured on the page, so the same note can fit
a desktop and offer the hint on a phone or in a narrow pane.
Click the row or the hint to read it (the hint is a button, so the keyboard reaches it too). When more than three notes are
pinned, the older ones fold behind a *+N more* row. The strip is at most a few rows tall and
scrolls past that, so the transcript and the composer stay on screen. A file path, a web address or a pull
request number in a note links the way it does in a user todo. Each row has an **Unpin** control (click it
twice; a tap elsewhere, or leaving the control, takes the first click back); a session unpins its
own notes with `unpin_note`, and unpinning a note that is already down is a plain answer, not an
error. A note's line takes at most 300 characters and its detail 4000; a terminal escape sequence
is dropped whole, and control characters other than a newline or a tab are dropped. At most eight
notes stay pinned per session; a ninth drops the
oldest, and the session is told which. The notes live in `pinned-notes.json` under Romp's state
directory, keyed by session, so they survive a kernel restart and reappear when a session is
revived. There is no switch: the two tools are always offered, since a pinned note asks nothing of
you.

These are for scripting and for agents rather than daily use:

| Command | What it does |
|---|---|
| `romp url` | Print only the tokened dashboard URL, for piping |
| `romp sessions [--json]` | The fleet with each session's state, identity colours, directory and backend |
| `romp perf [--interval <s>] [--json]`, `romp perf log on\|off` | The kernel's performance counters as rates over two snapshots (below); `--json` prints one raw snapshot; `log on\|off` turns the `romp-perf` stderr log on or off without a restart |
| `romp perf client [--minutes <n>] [--json]` | What the open dashboards' browsers spent on the frames they received (below): handler milliseconds per minute by frame type with window p50/p90/p99 and max, the worst minute's main-thread-free p90, long animation frames and their attributed callbacks, the worst minute, heap and DOM, the slowest frames, per dashboard and pane over the last `<n>` minutes (default 10) |
| `romp api-health` | The API-health signal as JSON (see [The API-health signal](#the-api-health-signal)): per-credential, per-model-family retry and give-up rates over rolling windows, with a derived state |
| `romp mail …` | The postal service from the shell (below) |
| `romp send <session> [--tag <label>] <text>` | Hand a session a message, on either backend. Anything a script, cron job, or launcher composes SHOULD carry a tag (one word, letters/digits/dashes, up to 24 chars): the chat then renders it as machine-sent under that label instead of as the user's typed words. Raw POST /send callers pass it as the JSON `tag` field (`{name, text, tag}`; a malformed tag fails the whole send, loudly); `--tag` is the CLI's equivalent. Both resolve to the `<!-- romp-tag: <label> -->` marker in the delivered text. An unknown session is refused with the kernel's reason and exit 1; a session the kernel knows whose backend refuses it (an ended SDK session addressed by id, an ended comment thread by id or name, a tmux-backed session no pane runs) is refused the same way, HTTP 409 with the kernel's reason, and the message is not delivered; a session an attached machine runs, addressed by the name that machine lists or by its id, receives it through that machine's kernel, whose refusal is relayed in its words |
| `romp new --model <id> <name>` | Model for the Claude Code session: a family alias such as `fable` (follows the family's newest release) or a full id such as `claude-fable-5` (a pin); re-asserted if `<name>` already runs |
| `romp new --effort <level> <name>` | Reasoning effort for the Claude Code session (`high`, `ultracode`, ...); re-asserted if `<name>` already runs |
| `romp new --env NAME=VALUE <name>` | A per-session env var for the Claude Code session, repeatable; a re-run against a running `<name>` replaces the whole set; vars not re-named are dropped |
| `romp new --no-env <name>` | Clear a running Claude Code session's per-session env (declares the empty set) |
| `romp new --in <tag> <name>` | Put the new Claude Code or Codex session in `<tag>`, so its tab lands in that group (repeatable; a name that does not exist yet creates the tag). Applies to `<name>` if it already runs. The kernel echoes `tags` (the session's tags) and, per `--in`, the stored name it landed as (`tagsApplied`, beside `tagsRequested`): a name the store trimmed or clamped prints as "applied as"; a missing echo, or a tag the kernel refused, prints a warning |
| `romp new --no-inherit <name>` | Run inside a romp session, `romp new` sends that session's stable id (`ROMP_SID`) as the new session's `parent` (marked `parentAuto`), and the kernel copies the parent's tags onto the child; inside a comment thread, the parent is the session the thread belongs to. This flag withholds the parent, so the new session starts outside them. A kernel that never ran the calling session creates the session untagged and echoes `parentIgnored`, which the CLI reports in one line. Raw POST /new callers pass `parent` (a live name or a known sid; an unknown one is a 400 unless `parentAuto` is set) and `tags` (a list of names); opening a name that already runs never inherits; a name that is being registered by another request right now is a 409 whose `error` says which door holds it |
| `romp tag [<name>] [--add <session>…] [--remove <session>…] [--color <hex>] [--rename <new>] [--delete] [--host <kernel>]` | Session tags. Bare, it lists them; with a name, it merges one tag (created on first use). A tagged session leaves the untagged view, and its tab sits in that tag's section of the strip. `--host` edits an attached kernel's tag |
| `romp interrupt <session>` | Interrupt whatever turn a session is taking; the session stays open. A session an attached machine runs, addressed by the name that machine lists or by its id, is interrupted by that machine's kernel. An unknown session is refused with the kernel's reason and exit 1 |
| `romp compact <session> [--wait] [--timeout <s>]` | Compact a session's context in place (Claude's `/compact`: summarize the history, keep the session's name, id, mailbox, and watches): the alternative to ending and recreating a long-lived session, and the external hand a session needs since it cannot `/compact` itself mid-turn. Quiet session → compacts now; open turn → queued, fires alone the moment the turn ends (the same safe path the chat's compact button uses). `--wait` blocks until the compaction has started and cleared, polling the kernel's own `compacting` signal on the `/sessions` rows (also the field to point a `romp watch` predicate at for scripted recycling); exits 1 honestly on timeout. A remote session's compaction is requested on its own kernel; `--wait` can't follow it from here and says so |
| `romp end <session>\|self [--now\|--when-idle]` | End a session, at once by default. `--when-idle` ends it once its current turn settles, so the closing reply lands first; a session an attached machine runs, addressed by the name that machine lists or by its id, is ended by that machine's kernel, and `--when-idle` waits on the session's settle there. `self` names the calling session (from inside a session) and defaults to `--when-idle`, which `--now` overrides. An unknown session is refused with the kernel's reason and exit 1 |
| `romp move <session> <dir>` | Move a Claude Code session's working directory to `<dir>` (the folder must already exist); the conversation, name, mail and history stay with the session. Quiet session → moves now; open turn → queued, fires when the turn ends. See [Moving a session to another folder](#moving-a-session-to-another-folder) |
| `romp emoji <session> [<emoji>\|--clear]` | Put one emoji before the session's name on its tab; `--clear` removes it, and an empty argument is a usage error, not a clear; with no argument, print the current one (an empty line when there is none). Exactly one emoji is accepted; a refusal prints the kernel's reason. A live session is named by name or id, a dormant one by id, for setting, clearing and reading alike. A read by an id that has a record on this machine comes from the names registry and works with the kernel stopped; any other read (a name, or the id of a session an attached machine owns) goes through the kernel's `GET /emoji?target=`, which forwards to the owning machine as the set does. See [A session's tab emoji](#a-sessions-tab-emoji) |
| `romp checkin <host>` / `romp checkout <host>` | Publish this machine to an attached hub, or withdraw it. The hub files this machine under the name it declares only when that name is a machine name (letters, digits, dots, hyphens or underscores, starting with a letter or digit, at most 128 characters). Any other declared name is refused with a 400 that states the rule and echoes nothing, is recorded nowhere, and is said once on both machines: on the hub, one stderr line and one Log entry under the `refused` kind, naming the value as a clipped repr; on this machine, one stderr line, one dial-log record and one Log entry carrying the hub's reason, after which the same name is not re-sent until it, or the hub's kernel, changes. A hub's `POST /tunnels/trust` for a host it has never seen (the remembered-hosts entry that tiers relayed mail by origin) holds the wider rule that registry's writers share, a machine name or an ssh alias (letters, digits, dots, hyphens, underscores, at-signs, colons or square brackets, not starting with a hyphen, at most 255 characters), because a hub keys an attached peer by its ssh alias and carries that alias when you set trust between two of your machines; anything else is refused the same way, on the hub, with nothing recorded. `ROMP_HOST_NAME` (the kernel) and `ROMP_POSTAL_HOST` (the postal bus) override the declared name only when they clear the same rule; an unusable value (a space, an at-sign, a trailing newline) is set aside once, on stderr or in the bus log, and the derived name (the short hostname, else the platform's machine name, else a minted id) is used |
| `romp default-dir [PATH]` | The default working directory for new sessions; no argument prints it, `""` clears it |
| `romp debug [on\|off\|status]` | Judge debug mode, where rejection rows carry the full input and reply |
| `romp resume <id> [--name <n>] [--detach]` | Resume one exact conversation by UUID |
| `romp refresh --quiet` | Refresh at the next quiet window instead — waits for sessions to finish their turns (15-min backstop). The ONLY door to the quiet window: a deploy (a peer's `romp update`, a release self-update, an automatic converge) restarts immediately, by the user's 2026-09-08 decision |
| `romp down --wait <s>`, `romp down --now` | How long `romp down` waits for turns in flight to finish (0 to 600 seconds; default 5), or no wait at all |
| `romp up --foreground` | Run the manager in this terminal even with a login service installed (its log in front of you); the manager refuses to start beside a running one |

Raw `POST` callers, anything that talks to the kernel's routes directly rather
than through `romp`, follow one body contract, and the postal bus's own routes
share it. The request carries the serve token (`X-Romp-Token`, or `?token=`)
and is authorized before its body is read. The body is delimited by
`Content-Length` alone: no `Transfer-Encoding` (411), the header once and a
plain decimal (400 otherwise), and at most 1 MiB (413 beyond that, refused
before a byte is read). A body that arrives short of its announced length is
400, one that stalls for 30 seconds is 408, and every refusal closes the
connection. The body is a JSON object; an array, string, number or `null` is a
400 naming what arrived, echoed bounded and well formed. A flag field
(`delete`, `on`, `mkdir`, `tracked`, and the like) is a JSON boolean: `true`
and `false` apply, an absent field or an explicit `null` reads as the route's
default, and anything else (the string `"false"`, `0`, `1`) is a 400 naming the
field, with nothing acted on.

Three routes exist for the Obsidian timeline panel, which has the state
directory but no socket to the kernel: `POST /flag` (`{id, flag, value}`: one
of the lane gear's toggles, `hideFromFeed`, `postalServiceOff` or `notify`,
with a JSON boolean; here `value` is required, and an absent or `null` value is
a 400, never a default, since a missing value must not read as "off"), `POST
/views` (`{views, edited?, writeId?}`: the whole views blob, judged as the
dashboards' write is and answered with the same `viewsAck` document, `ok`, the
post-write `views` and `seq`, any `refused` tags and an `error` line), and
`POST /order` (`{order: [sid, …]}`, merged into the saved order so lanes the
drag did not carry keep their slots). Each lands through the setter its socket
op uses; a store that cannot be read or written answers 200 with `ok:false` and
the reason the dashboards see, and an unknown key or a wrong type is a 400
naming it. The panel finds the kernel through the `serve-port` record the
kernel writes beside `serve-token` in the state directory once its socket is
bound; with a record nothing answers on, the panel refuses the gesture and says
the kernel is not running rather than writing a file the kernel cannot check.
With no record at all (a kernel older than the panel wrote the token and no
port) it tries the port the command line resolves, `ROMP_KERNEL_PORT`, then
`ROMP_SERVE_PORT`, else `29855`, and its refusal says so when nothing answers
there. Record or fallback, the panel first asks the port to prove itself: a
`GET /healthz` with no token, on `127.0.0.1` only, must answer `200 ok` with
the kernel's `X-Romp-Boot` identity before the token is sent, and a port that
answers as anything else is refused by name and never sees the token.

`--env` gives one session its own environment, so two sessions in the same
directory can run with different toggles (a `FEATURE_FLAG=1`, a `CLAUDE_CODE_*`
switch) without editing the directory's `.claude/settings*.json`, which reaches
every session there and outlives them all. Re-running `romp new --env` against
a running session declares its full per-session env: any var you don't name
again is dropped, and `romp new --no-env <name>` declares the empty set, which
clears them all. Keep secrets out of it: each value is copied into
per-session files and the session registry under `~/.local/state/romp/`. A
credential never goes in `--env`, and never in `service.env` either: a payload
naming `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN` or `CLAUDE_CODE_OAUTH_TOKEN`
is refused outright. A session's credential is Claude Code's own resolution,
the `apiKeyHelper` in its settings for a key and the login otherwise; see
[Service environment and credentials](#service-environment-and-credentials).

Two things to know before building on `romp sessions --json`. **`waiting` means
at rest**, the ordinary state of a session that has finished its turn, so
matching it as an alert badges the whole idle fleet as needing you; the states
that want a person are `permission` and `picker` (a live prompt) and `blocked`.
(`romp sessions` emits the RAW backend states; the dashboard's chip states,
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

### A session's tab emoji

A session's tab can carry one emoji before its name, so you can tell the
sessions apart at a glance by role or state. It can be set from three places,
which share one validator and one store:

- **The tab.** Right-click it and choose **Emoji…** for the picker: a search
  box over a curated list (name and keyword prefixes, no network), a **Recent**
  row (the last 16 picks, kept per browser), a grid by category with a strip
  that jumps to each, and a footer with a field for an emoji the list does not
  have, **Set**, and **Clear**. Clicking a cell, Enter in the search box (the
  first result) and **Set** with a typed value all send the same
  `setSessionEmoji` WebSocket op (`{type: "setSessionEmoji", id, emoji}`;
  `emoji: ""` clears, and **Clear** sends exactly that); only the kernel
  judges the value. The picker stays open for the answer. The kernel answers
  with `{type: "emojiSet", id, emoji}` when the store has it: the tab strip
  changes on that confirm, the way a rename changes on `renamed`, the picker
  closes, and the emoji joins the Recent row. A refusal comes back as a `warn`
  with the reason, which the picker shows in its hint line above the field,
  with a typed value left in the field to fix. **Set** with the field empty is
  refused in place, without a round trip: to clear, use **Clear**.
- **The session itself.** The `set_emoji(emoji)` tool, beside `set_working`, so
  a session can mark what it is doing (a moon while it runs unattended).
- **The shell.** `romp emoji <session> <emoji>`, `romp emoji <session> --clear`,
  and `romp emoji <session>` to read; the success line shows the value the
  kernel stored. The tool and the command both go through `POST /emoji` with
  `{"target": <live name or id>, "emoji": <emoji | "">}`; the reply is
  `{"ok": true, "id", "emoji"}` or `{"ok": false, "error": <one line>}`. The
  `emoji` key must be present and must be a string: a body without it, or with
  a null or a number in it, is a 400, never a clear. A dormant session is set,
  cleared and read by its id. The write goes to the names registry through the
  kernel. A read by an id that has a record on this machine comes from that
  registry directly, whether or not the kernel is running; any other read asks
  `GET /emoji?target=<live name or id>`, the read half of the POST, which
  answers `{"ok": true, "id", "emoji"}` (`""` when there is none) or
  `{"ok": false, "error": <one line>}`. A name means a live session, so a
  dormant session is found by its id only. A session an attached machine owns
  is also named by its id, for setting, clearing and reading alike: the kernel
  forwards the request to that machine's kernel and relays its answer. A remote
  kernel from a release before these routes answers `that host's kernel
  (<host>) predates tab emoji`; a dead tunnel answers `the session's own kernel
  (<host>) did not answer`. When the kernel on this machine predates the read
  route, `romp emoji <session>` says so and asks for a restart of Romp.

What is accepted: exactly one emoji as a keyboard offers it. A base emoji, with
or without the emoji presentation selector (U+FE0F); a skin-tone form; a joined
(ZWJ) sequence such as a family or a profession; a keycap; a two-letter flag; a
tag-sequence flag. What is refused, each with a one-line reason: letters,
digits, punctuation, whitespace inside, a second emoji, a lone skin tone or
joiner, a text-default symbol without the selector (`©`, `☺`, `♥` as bare
characters, which would render as text), a value that is not text (a JSON null
or number), and text no UTF-8 output can carry (an unpaired surrogate). A stray
invisible character beside a valid emoji (a text-presentation selector from a
document paste, a doubled selector, a zero-width space) is refused with the
stray's code point named, whether it follows a flag, precedes a keycap's mark,
or sits beside any other emoji. The value is at most 48 bytes (the longest
standard sequence is 35). Empty input clears.

The grammar follows UTS #51 as far as the Unicode property tables reach: a
skin tone goes only on a code point with the Emoji_Modifier_Base property
(hands, faces, people) and directly after it; tag characters build a
subdivision flag only on the black flag (U+1F3F4); a joined sequence has at
most four parts. RGI membership, whether fonts draw a joined sequence as one
glyph, is not checked: it needs the sequence list rather than the property
tables, so a well-formed chain of up to four emoji is accepted as typed. The
code-point tables come from Unicode 16.0. An emoji from a newer release is
refused until the tables are updated, and the refusal names it by code point
(`not an emoji: U+1FA8A (not in this kernel's emoji tables)`) because most
fonts would draw the character itself as a box. The tables alone decide, not
the Python interpreter's own Unicode database, which may be older (Python 3.12
and 3.13 ship Unicode 15): a Unicode 16.0 emoji is accepted, and quoted in a
refusal, on every supported Python. An accepted emoji is drawn with the
viewing machine's own emoji font, so one from the newest Unicode release can
still show as an empty box on a machine whose font predates it.

The emoji is stored as the fifth field of the session's entry in the names
registry (`names/<id>`: name, directory, colors, emoji), beside the name and
color it decorates, so it survives restarts, resumes and revives and follows a
dormant session. Every writer of the entry carries it and publishes the whole
entry atomically (a temp file in the same directory, moved into place). The
kernel's writers never publish over an entry that reads with no name, which is
another writer's window or a damaged file: the entry is re-read once, then left
as it is, and the problem is reported with the session's id in the kernel log
and the dashboard's error center. A five-field entry always carries all four
identity fields: an entry that had no color yet (one
from before colors, or a Codex session whose launch failed) is given one when
its emoji is set, as a launch would give it one. It reaches the browser
inside the per-tab metadata of the same push a rename or recolor rides, for
this machine's sessions and for those of attached machines, whose kernels ship
it in their own frames; nothing polls. On the tab the emoji is part of the
tab's accessible name: a screen reader speaks the character's name before the
session name, since two same-named sessions may differ only by it.

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
romp mail remote                 # legacy singleton scheme only (ROMP_POSTAL_PEERS=0): connect this remote machine to your laptop's bus; peer mode refuses
```

### Mail inside a session (MCP tools)

| Tool | What it does |
|---|---|
| `send_message(to, body, kind)` | Message a live session by name; `kind` declares delegate / coordinate / question |
| `check_inbox()` | Read messages sent to you (also delivered at the end of each turn) |
| `list_agents()` | The live sessions, each with its branch and working-note |
| `set_working(text)` | Publish what you hold so peers steer clear |
| `set_emoji(emoji)` | Put one emoji before your own session's name on its tab; `''` clears it. Refused, with the reason, for anything but exactly one emoji |
| `pin_note(text, detail?)` | Pin a short note above the session's own transcript for you (where things stand, a warning, a summary); the line takes at most 300 characters and the detail 4000; returns its id, what is pinned now, and any note the eight-per-session bound dropped |
| `unpin_note(id)` | Take a pinned note down; one already down is a plain answer, not an error |
| `check_sent()` | Whether your sent messages were read yet |
| `recall_message(to, id?)` | Unsend a message the recipient hasn't read |
| `add_user_todo(text, detail?, file?, link?)` | The session flags something it needs from you and keeps working; offered only while the **User todos** switch is on. `text` is the one-line todo, `detail` optional longer context, `file` the absolute path of the file the todo is about, `link` the http or https address it is about (User todos, above) |
| `withdraw_user_todo(id)` | Take back a todo by the id `add_user_todo` returned |

Not the same tools: romp peers are discovered only through the postal service's `list_agents`. Claude Code also ships its own `ListAgents` and `SendMessage` tools, which list the account's Anthropic cloud sessions and this session's own subagents: a different system, and a cloud session in that list is easy to mistake for a romp peer (the user 2026-09-08, who found one there that read like a session of theirs). The recommended setting is `"permissions": { "deny": ["ListAgents"] }` in the Claude Code settings, so the only list of agents a session sees is romp's; `SendMessage` must stay allowed, because continuing a subagent uses it.

### When a send is refused

A send whose record cannot be written, or that cannot be placed in the
recipient's inbox, is refused: the bus answers `503` with `ok: false` and the
reason, nothing is delivered and nothing is recorded, and the sender still
holds the text to retry. Two outcomes are not refusals, because the message is
already in the recipient's hands: the recipient read it in the instant before
its record failed, or the bus could not take it back out of the inbox. The
send then answers the id, and the bus says on stderr and on the dashboard that
the message log has no record of that message. A bus stopped between placing a
message and recording it writes the missing record from the message's own
headers at its next start. `check_sent` and `romp mail sent`
show a message the bus had to give up on later (a cross-host record it could
not write, a file it could not read, a write a restart found unfinished) as
`bounced`, marked `refused` with the reason; a peer's refusal that did come
back as a note still reads `undeliverable, returned to you`. A message file the bus cannot read, in a
recipient's inbox or in the cross-host outbox, is moved aside once (see the
state files below), its sender's receipt reads refused, and the dashboard's
error center says so under the `refused` kind.

### Claude Code 2.1.224 or newer

Mail to a terminal (tmux) session delivers through Claude Code's per-session
inbox socket, which the CLI added in 2.1.224: delivery is instant and never
touches a half-typed draft. An older Claude Code still works: delivery falls
back to typing the mail into the pane, which is slower and waits for a free
prompt, and `romp` says so at launch, with the upgrade being one
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

### The file viewer's per-browser choices

The file viewer keeps two choices in the browser's own storage, not on the
kernel, so they survive a kernel restart and apply on every surface that shows
the viewer (the chat, the feed, the Files pane): the Rendered or Raw view of a
markdown file (`romp:fileviewFmt`) and the text size (`romp:fileviewTextSize`,
one of 70, 80, 90, 100, 115, 130, 150, 175 or 200 percent, set by the **A−** /
**A+** buttons or Ctrl/Cmd + wheel over the text). The size scales the prose,
its headings, the code and the Raw view together, and the prose measure with
them; a value outside the table reads as 100.

### Pictures from the web in a viewed file

A markdown file shown in the viewer may carry pictures and clips from the web. The
gear's **Pictures from the web in files** setting is the list of hosts whose figures load
when the file opens; a figure from any other host is shown as a box naming the host, makes
no request, and loads on one click, together with every other figure from that host in the
file. A host loaded that way stays loaded until the page reloads. The list is kept with the
other gear settings in the browser's own storage (`figureHosts` under `romp:settings`), one
host name per entry, exact (`github.com` does not cover `gist.github.com`), and it starts as
`github.com`, `raw.githubusercontent.com`, `user-images.githubusercontent.com`,
`camo.githubusercontent.com`, `avatars.githubusercontent.com`,
`objects.githubusercontent.com`, `private-user-images.githubusercontent.com`,
`github.githubassets.com`, `localhost` and `127.0.0.1`. The kernel's own address, which
every figure stored beside the file loads through, needs no entry; a `data:` image makes no
request and is never gated. An inline `<svg>` whose `fill`, `stroke`, `filter`, `clip-path`,
`mask`, `marker-start`, `marker-mid` or `marker-end` attribute names another host with
`url(...)` is a figure from the web too, and is gated the same way. An entry is read as the
browser reads a host: an address pasted whole (`https://cdn.test/a.png`), a port
(`cdn.test:8080`) or a path is stored as the host alone (`cdn.test`), an internationalised
name in its `xn--` form and an IPv4 address without leading zeros, and the gear shows the
stored form on its next open. A line the browser cannot read as a host is kept, allows
nothing, and is named under the list in the gear. A change to the list, saved from this tab's
gear or another tab's, reaches an open file without a reload: a host added to the list
restores its boxes where the file stands. A host removed from the list takes effect at the
file's next paint (a re-open, or a switch between Raw and Rendered); a picture already
fetched stays on the page until then. The setting applies to files shown in the viewer, on
every surface; a picture in a chat message is not gated.

### The tab strip's per-browser choices

The chat tab strip keeps its grouping choices in the browser's own storage, under
`romp:tabgroups`, not on the kernel: whether the tabs are grouped by tag, which groups
are folded, which tabs show while their group is folded (**Show when folded**), and
which sessions are hidden inside their group (**Hide**, in the section's at-a-glance
view). The tab's right-click menu writes the same hide entry: **Hide tab** on a shown copy,
**Show tab** on a hidden one (a hidden copy has no tab on the strip; the way back is the view's
**Show**, and the group's count opens the view while the group is open). The row follows the copy
the menu speaks for: the copy you right-clicked while its group holds the session, else the
session's one remaining group, and none under two or more (the copy is known by its tag's id, and
by its name when no tag has that id, so a rename keeps it and so does a tag made again under the
same name; a tag added from the flyout while the row named the one remaining group keeps the row
on that group, even when the removed tag comes back); that group's tag must already exist (a
tag still being created has no row until the kernel answers), and the tabs must be grouped by tag.
On the flat strip, on the phone layout and for the untagged sessions after the divider, where hides
do not apply, the menu has no such row; an untagged session gets the row once a tag added from the
menu's **Tags** flyout gives it a group. A pin or a hide names the session and its group (the tag's name,
and the tag's id
when it is this kernel's), follows the tag through a rename, and is dropped at the next
pin or hide change once the session has left the group or closed; a fold or an open
carries it as it is. Folding or opening a group never changes which of
its sessions are hidden. A store written before hiding existed reads as nothing hidden.
A key in the store that this build does not know is carried through its writes unchanged.

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

The backends apply the change differently. A Claude Code session switches
model live but reloads to apply a new effort: the chat shows "Reloading
session…" and the effort badge shows switching-dots until the reload completes,
and a session that is mid-turn reloads when the turn ends. A Claude Code (tmux)
session gets the CLI's own command typed into its pane. `/model` there asks for a
confirmation, which the kernel accepts on your behalf so the pane is never
left waiting on a keystroke the dashboard cannot send; `/effort` and `/fast`
apply in place.

### Fast mode, from the chat statusline

The statusline's badges (permission mode, model, effort) are each a small
dropdown. A fourth appears when the session reports Claude Code's fast-mode
state (an Opus-only research preview, billed at a premium): it reads **Fast**
in orange while fast mode is on, **Slow** while it's off, and **Cooldown**
while fast requests are rate-limited. Picking On or Off sends the CLI's own
`/fast` command; the badge never appears on a session that cannot run fast
mode. Turning it on while the session is on a non-Opus model makes the CLI
switch to a fast-capable one, which the chat shows as the command's own
confirmation. If the CLI refuses the toggle (for example, the account has
extra usage turned off), a toast says why and the pick reverts to off;
the control never silently disappears.

### Per-session billing (login vs API key)

A Claude Code session bills the machine's Claude login (subscription usage) or
the API key, chosen per session. The key is Claude Code's own: the CLI runs the
`apiKeyHelper` configured in its settings (the helper; setup under [A key from
a secret manager](#a-key-from-a-secret-manager)) and holds what it prints.
Romp holds no key and passes none to a session (the user 2026-09-08, who wants
romp to hold no key). The per-session pick decides only whether the helper
runs for that session.

The new-session picker's **Billing** row states the case whenever the backend
toggle says Claude Code: segmented buttons when the selected host offers both choices,
and with only one real choice, the same spot writes out which applies,
`Login (name@example.com)` or `API key`. The key choice exists when Claude
Code's settings for the kernel's working directory carry a helper; romp reads
the setting and never runs it for this. A live session's tab menu (the
control left the statusline on 2026-08-09) carries a **Billing** submenu that
lists BOTH choices on every box (since 2026-09-08; it used to exist only when
both were real): the choice this machine cannot bill is greyed and inert, with
the reason in its hover, `no Claude login signed in on this machine`, `no
apiKeyHelper configured`, or `the apiKeyHelper is set in managed settings,
login cannot apply`. The status payload carries the same availability as
`authAvail` (`authBoth` rides beside it for older clients). Switching
reconnects the session to apply; until that reconnect lands, the menu entry's
sub-line reads `applying…` and the tab hover's Billing row says the pick is
applying, not confirmed yet.

On a one-auth box the picker never chooses the missing side. A remembered
default that names the side this box cannot bill is set aside at spawn and the
unpicked rule below decides instead, in both directions: a remembered login
pick on a machine with no login seeds new sessions on the API key when a
helper is configured, exactly as a remembered key pick on a helper-less machine
already fell to the declared side, else the login, and the set-aside is said
once per process as a problem row. An explicit pick that names the missing
side (a session picked "login" on a box that later lost its login) launches on
the other side when one exists and says so once per session start, on the tab
menu's Billing sub-line as `⚠ login unavailable, billing API key` and in the
log; the fall itself rides the status as `authPickFell`, so the hover
and the sub-line never infer one. A pick with nothing to fall to (a box with
neither side) launches as picked and the CLI decides; the sub-line then says
the side is unavailable and claims no fall. A side whose availability cannot
be read just now (the operator's settings file, or `~/.claude.json`, mid-rewrite
or unreadable) is cannot-tell: the launch keeps the pick as is, says so once
per session, and never falls on a read failure. `setAuth` refuses the
missing side with that same reason in the toast.

A pick reaches the CLI through the session's per-session settings layer, the
file the SDK hands the CLI as its `--settings` argument. A login pick writes
`"apiKeyHelper": ""` into that file: the layer outranks the settings files for
the same key, and the empty string disables the helper for that one process
(verified on Claude Code 2.1.257), so the session authenticates with the login.
A key pick, or no pick, writes nothing about the helper; the CLI runs it and
the session bills the key. On a box with a helper, every session without a
login pick therefore bills the key. Login tokens the kernel finds in its own
environment at startup (`ANTHROPIC_AUTH_TOKEN`, `CLAUDE_CODE_OAUTH_TOKEN`) are
claimed at boot, so a key-billed session never inherits one, and handed back to
login-billed launches.

The login is named by its account (the email the credential store records);
the key option is labelled plainly `API key`. No fragment of the key, not even
a last-4 tail, ever reaches a browser or a screen, and romp never sees the key
at all. A new session defaults to the last pick made anywhere, and before any
pick to the key when a helper is configured; with neither, to the side
`ROMP_EXPECTED_AUTH` declares (see below); when that side is the key, the
picker's Billing row writes `API key` out even when the box has no Claude login
to show beside it. A remembered
key pick on a box whose settings carry no helper leaves new sessions unpicked,
and the kernel log says so once, naming the settings file to configure.
Claude Code (tmux) sessions are not covered by the picker: their CLI lives in
the tmux server's environment, which the kernel does not control, and resolves
its credential the way any `claude` in a terminal does.

A tab not yet loaded after a reconnect shows "Not loaded yet — click to load"
as its hover tooltip, until its transcript arrives. The strip's skeleton tabs
appear after the page's bundle has said it is listening (its `ready`), never
before it.

A Claude Code session's chat tab carries the same fact as a `Billing` row in
its hover tooltip, one-auth machines included; Claude Code (tmux) sessions,
whose billing romp cannot know, and Codex sessions, which bill no Claude
account, show no row. The row
has four readings. Unless one of the three cases below applies, it reads
`API key` or `Login (name@example.com)` (`Login` alone when the account name is
unknown): once the session's CLI has reported which credential it found (its
init names the source), the row shows that side; before any report it shows
the intent the session was launched with. While a switch is still reconnecting
the session, the row appends `(applying, not confirmed yet)` to the side:
`Login (applying, not confirmed yet)`. A pick naming a side this machine cannot
bill leads with the warning, the reason, and the side the launch fell to:
`⚠ Login picked, but no Claude login signed in on this machine — this session
bills the API key`; with nothing to fall to, the tail says the launch went out
as picked. A pick you made that the CLI's own report contradicts (a login pick
whose CLI reports a key, a key pick whose CLI landed on the login) is worded as
one: `⚠ Login picked, but the CLI reports the API key; this session bills
that`, and, for a key pick, the same with the sides swapped. A default nobody
picked is never worded that way: a session started unpicked on a box whose
`apiKeyHelper` supplies the key reads `API key`. The tab menu's Billing
sub-line says the same in fewer words: `API key` or `Login (name@example.com)`,
`applying…`, `⚠ login unavailable, billing API key`, and `⚠ CLI reports API
key`.

Failures are loud rather than silent: a session that lands on the other auth
than it was launched for is flagged in the Log panel, and a dead credential
("Not logged in", an invalid or expired key) blocks the session's card with the
fix named, and is never auto-retried.

The auth check compares each session's landing against a declaration of the
box's design. `ROMP_EXPECTED_AUTH=key` (or `login`) in `service.env` (the
declaration) says which side the box's sessions are meant to bill: a session
landing on the declared side is quiet, and one landing on the other side is
flagged, naming the declaration. An undeclared box (the variable unset, or any
other value) compares each landing against what that session was launched for
and stays quiet when they agree. With a helper configured, an unpicked session
bills the key whatever the box declares, and the declaration is checked against
the CLI's report at each init, never applied as a label (`ROMP_EXPECTED_AUTH=key`
describes such a box truthfully and stays quiet; `ROMP_EXPECTED_AUTH=login`
flags every unpicked session's keyed landing in the Log panel, and the session
keeps billing the key); without a helper, the declaration seeds what an
unpicked session is *taken* to bill: the Billing row's fallback before the CLI
has reported, the picker's written-out choice, and the spend pause's reading of
a session that reports nothing all read the declared side, where they read the
login before. One explicit gear **Billing** pick supersedes
the declaration from then on: the remembered pick becomes the box's expectation
and the env var goes inert (it described the unpicked design), so re-seeded
spawns are judged against your pick, never against stale doctrine. The one
exception is an API-key pick remembered from a box that no longer holds a
key: it is set aside at spawn, so it seeds nothing, and the declaration
decides the unpicked default again (the per-init check still judges each
landing against the pick).

The kernel also checks, once at boot and before anything is spawned, that no
retired key path is still configured. A `service.env` that still carries a key
line from an earlier romp, a provider marker beside it, or a kernel
environment carrying one of the retired names stops the kernel with a message
that names the file and the variable names, never a value; the names and the
fix are under [Service environment and
credentials](#service-environment-and-credentials). Romp injects no credential
into any launch, so Claude Code's own resolution decides every landing, and
the per-init check above confirms each one.

The usage rail reflects a mixed machine: the window bars (5 hours / 7 days /
Fable 5) are drawn once, aggregated across every connected host's login as the
worst reading per window, and an `API` cell beside them carries the
key-billed dollars (the last day and the last 30 days, numbers only). Hovering
breaks both down per host, one column per host, side by side, and a host
can show its login's windows and its key's spend together. The key-billed
dollars come from the sessions whose CLI reported a key source at init, judged
against the declaration; a login turn's computed cost is dollars nobody pays
and is left out.

What the API cell measures: the Claude Code CLI's own cost figure. At the end
of every turn the CLI reports the session's cost so far (`total_cost_usd`, at
list price, fast mode included). romp records the difference from the previous
turn into a ledger of hour and day buckets (`spend.json`), with the turn's
token counts from the CLI's per-model usage totals, which cover subagents and
sidechains. The hover's windows sum those buckets: `1 hour`, `1 day` and `1
week` from the hour buckets, `1 month` as a rolling 30 days from the day
buckets, and `this month` as the calendar month so far. Two kinds of spend
never reach the cell: the CLI's own permission-classifier and token-count
calls, which the CLI leaves out of its report, and a turn cut short by a
kernel restart, which never reports a cost. The judge pipeline's cost is
recorded separately (`judge-usage.jsonl`) and is not part of this cell. Day
buckets recorded before 2026-08-10 predate the per-turn fold and are inflated;
they stay as recorded, and a window that includes one says so in the hover.

The gear's analytics modal (the Sessions and Judges bars) shows the session
dollars from the same ledger, over periods made of the same whole buckets:
`1h` is this hour and the one before it, `24h` this hour and the 24 hours
before it, `30d` today and the 30 local dates before it, and the footnote
names where the period starts: a time in your browser's clock for the hour
periods, and for `30d` the kernel's own local date (the day buckets are the
kernel's dates, whatever zone the browser is in). Every figure in the modal
(the ledger dollars, the transcript tokens, the judge dollars) is cut at
that same start, so the `judges = N% of session cost` line compares two
figures over the same span. On a host that runs a login beside a key, once
the key has billed a turn, the session dollars count key-billed turns only,
as the API cell does, and the footnote says so. Where the ledger began
inside the period, the modal adds an estimate for the time before the
ledger's first bucket, priced from the transcripts' tokens with a per-model
table, and labels the two amounts; that first bucket is partial (recording
began partway through its hour or day), so turns earlier in it are in
neither amount, and the footnote states that too. The estimate stands alone
only when the ledger has no bucket of the period's kind at all. The estimate
misses fast mode's premium and any model the table lacks, and it prices
every session's transcript, login sessions included.

The token count beside the dollars is every kind together: fresh input,
output, cache writes, and cache reads. Cache reads are most of it: every API
call within a turn (one per tool step) re-reads the whole context from the
cache, so a long session's single turn can read tens of millions of tokens at
a tenth of the input price. The hover splits each window's count by kind, so
the size of the number carries its explanation. A result that carries no
per-model usage map is counted from the main loop alone, and the error center
says so once: once per session when the CLI left the map out, once per kernel
run when the Agent SDK the kernel imported has no field for it.

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
- `ROMP_NO_SDK=1` skips the Claude Code backend's Agent SDK venv (Claude Code
  (tmux) sessions still work).

For the one-line installer (`bootstrap.sh`), which passes all of the above
through to `install.sh`:

- `ROMP_DIR=<path>` where to clone; default `~/romp`.
- `ROMP_REF=<tag|branch>` install a specific ref; default is the newest
  `vMAJOR.MINOR.PATCH` release tag (prerelease-suffixed tags are skipped),
  falling back to `main` when none is published.
- `ROMP_NO_PATH=1` leaves your shell rc alone.

**File comments** (the viewer's Comments panel) have two prerequisites and one
consent. The **User todos** switch (above) is what lets a session flag a file
for you to look at: without it the session has no `add_user_todo` tool, so no
todo appears under Waiting on you, and a comment you send from the viewer
reaches the session as a plain message. The machine whose kernel holds the
file needs `node`: the kernel runs a small node helper for every read and
write of a file's comments, and without it the viewer shows no Comments
action. For the session to reply, `install.sh` must have linked the comment
tools into `~/.claude/hooks` on that machine. Writing a comment also stands
behind the **File editing** consent, like any dashboard write to a file, and so
does **Send to session**: the send is recorded in the comments log, so with the
consent off it is refused and the panel offers the consent and sends again on
yes. The gear reports a machine that is missing node or the comment tools.

### Judge concurrency

- `ROMP_JUDGE_CONCURRENCY=<1..16>` sets how many judge calls run at once,
  across every tier; the default is 6. The judges read it once, when they
  load, so set it where the kernel's service sees it (`service.env`, then a
  restart). A value outside the range is applied at the nearer bound; a value
  that is not an integer is ignored, with one line on the kernel's stderr. The
  same knob is a kernel setting, **Judge concurrency**, the last row of the
  gear's Judges section below the model and effort picks: a pick there
  applies on the judges' next pass with no restart, wins over the variable,
  and follows to every connected machine like the other judge settings; its
  Default option clears the setting back to the variable, else 6.

### Session backends

- **Enable Claude Code tmux backend** (the gear's Updates & debug section; off
  by default) decides whether the new-session picker and the gear's Default
  backend list offer **Claude Code (tmux)**, a Claude Code session in a
  terminal pane that Romp follows by reading the terminal. The setting gates
  the offer alone: sessions already running on that backend keep working and
  keep their label, `romp new -t` still works, and a saved default of Claude
  Code (tmux) is set aside while the setting is off (new sessions use Claude
  Code) and returns when it comes back. Like the judge settings, a change
  applies at once, without a restart, and follows to every connected machine.
  The backends read as **Claude Code** (the default), **Claude Code (tmux)**
  and **Codex** everywhere: the picker, the gear, the tab tooltip's Backend
  row.

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
while on macOS it reloads the job, which restarts it. Either rewrite drops a
line you added to the unit or the plist by hand; a drop-in survives it (see
[Two things still need a restart](#two-things-still-need-a-restart)). The
service unit bakes in whatever is set at install time, so a renumbered port
that only lives in your shell leaves the supervised manager on the old one, and
the two collide.

### The manager's control port

The manager (`romp up`, or the login service) listens on loopback at `:7432`
(`ROMP_MANAGER_PORT`). `GET /status` is open: `romp status` and the probes read
it. Every request that changes state needs a serve token in an `X-Romp-Token`
header:

- `POST /restart-all`: `romp refresh`, the automatic converge, the release
  self-update, and the dashboard's Restart, which posts the kernel's own
  `/restart` and is forwarded here by the kernel.
- `POST /restart`: `romp-manager restart [kernel]`, one kernel. No romp verb and
  no front end uses it.
- `POST /stop`: `romp down`.
- `POST /ensure`: a front end asking for a kernel (the VS Code extension).

The token is the same 0600 file the kernel gates its own writes with
(`~/.local/state/romp/serve-token`, or `ROMP_SERVE_TOKEN`). The manager accepts
the token of every kernel it manages: the primary root's file, and each
`kernels.json` profile's own `<stateDir>/serve-token`, since a profile kernel
serves with its own root's token and presents it when its dashboard's Restart or
its converge posts here. Every file is read fresh on every request, so a
reminted token is honoured without a manager restart. A request with no token,
or one the manager does not hold, is answered 401 with a one-line body, and the
manager logs one line naming the address and the door, never the token.

When nothing is at the primary root's token path as the manager starts, it mints
the file itself (the kernel's shape: 18 random bytes as base64url, mode 0600,
written whole) before its port opens, so a manager whose kernel never got as far
as minting one can still be stopped. While a token file that does exist cannot
be read by the manager (another owner, an unreadable mode, a directory), or is
a symlink (the manager reads no token through a link, as the kernel does),
every state-changing request is answered 503, saying so, until the file is
repaired: the doors never open on a missing token. A readable file with a loose
mode is accepted as it is; the kernel tightens the mode at its next start.
Before this gate (2026-09-10) a local process restarted every session by
posting to the port.

`romp refresh`, `romp down`, the dashboard's Restart, the release self-update,
the automatic converge and the VS Code extension all send the header. When the
manager refuses one of them anyway, the refusal is said where that caller
reports. The manager's control client (`romp refresh`, `romp-manager
restart-all` and `romp-manager restart [kernel]`) exits 3 when the manager
answered and refused, against 1 when nothing answered, prints the manager's
answer, and puts one line on stderr naming the door, the status and the way
out (`romp down` runs the same client but captures its output, composes its
own line from it and exits 1; see Stopping): on a 401, whether it sent the
token it read from the file under
its own state root (then the manager runs under another root, and the fix is
to run the command from a shell whose state root, `ROMP_STATE_DIR` or
`XDG_STATE_HOME`, is the manager's) or from `ROMP_SERVE_TOKEN` (then unset or
correct it), or found none to send (then the file and the reason); on a 503,
the manager's own file to repair. `romp refresh` bounces the postal bus only
after the manager took the request, so a refused refresh restarts nothing.
The dashboard's Restart answers the page with the refusal instead of acking a
restart that will not happen, and both it and the converge put a notice in the
bell naming the status and the way out (`romp refresh` from a shell whose
state root is the manager's: the client reads the token file under its own
root, or `ROMP_SERVE_TOKEN` when set, so a shell under another root sends a
token the manager does not hold), with one line on the kernel's stderr that
names where the kernel read its token and a `manager-refused-restart-all` row
in `restart-audit.jsonl`; `romp down` prints the refusal and the remedy (below,
under Stopping); the extension's toast says whether this window found a token
and where it read it, and, for a token read from the file, that the manager
runs under another state root. A script of your own that posts to the port
needs the header too. Read the file and hand it to curl on stdin rather than
in argv, which every account on the machine can read:

    printf 'header = "X-Romp-Token: %s"\n' "$(cat ~/.local/state/romp/serve-token)" \
      | curl -fsS -X POST --config - http://127.0.0.1:7432/restart-all

The manager and the pieces that call it ship in one checkout, so a `romp
refresh` after an update moves them together. A caller on older code than the
manager (another checkout's `romp` on PATH, or a script of your own without the
header) is refused with 401, and the manager's log names it; `romp refresh`
from the checkout the manager runs from recovers, and the script needs the
header above.

### The kernel's Python

The kernel and its Agent SDK venv (`sdkvenv` under the state directory) must
run the same Python: the venv's compiled extensions import into the kernel
process. The match is on the tag venv names its `lib` directory with (`3.14`,
or `3.14t` for a free-threaded build), not on the version alone, so a
free-threaded build's venv matches that build and no other. `bin/romp-serve`
picks the interpreter in this order: `ROMP_PYTHON` if set, refused with one
line when it is not an executable interpreter (a pin naming a removed path
used to reach the exec and crash-loop the manager); otherwise the interpreter
the venv's `pyvenv.cfg` records, if it still runs and still reports the venv's
tag, the recorded X.Y plus the build its `lib` directory names (an upgrade
that repoints `python3` leaves the recorded path runnable while the venv is
stale); otherwise another interpreter of that same minor and the same build on
`PATH` or in `~/.local/bin`, which the venv still matches, with a line saying
so (`python3.14t` and then `python3.14` for a free-threaded venv; the build is
read from `sys.abiflags`, not from the file name, because uv's free-threaded
install links `python3.14` to `python3.14t`); otherwise the newest `pythonX.Y`
on `PATH` or in `~/.local/bin`, the rule for a machine with no venv yet, with a
line saying the venv must be rebuilt for it. So installing a newer Python does not change what the kernel
runs at its next restart. On a machine that runs romp as a service, pin it
anyway: `ROMP_PYTHON=/usr/bin/python3.12` in `service.env` makes the choice
explicit and holds if the venv is deleted or rebuilt. Pin the versioned path,
not `python3`, which an upgrade repoints.

Moving romp to another Python, whether another version or the free-threaded
build of the same one, takes four steps, and skipping any one of them leaves a
kernel that cannot start sessions: set `ROMP_PYTHON` to the new interpreter in
`service.env`, run `bin/romp-sdk-setup` with the same value (and, if the Codex
backend is set up, re-run `bin/romp-codex-setup` after it: it follows the SDK
venv's record, so a plain run rebuilds `codexvenv` for the new interpreter),
run the test suite on that interpreter, then restart the manager. The setup
script compares the venv's record (the version `pyvenv.cfg` holds plus the tag
of its `lib/python3.X` directory, never the venv's own `bin/python`, a symlink
that follows a repointed base interpreter) against the new interpreter's tag,
rebuilds on any difference and says from what to what. A kernel that does come
up on a Python the venv was not built for logs one line naming both tags, and
each Claude Code session reports the mismatch and the remedy that fits: the
`ROMP_PYTHON` pin when the venv's recorded interpreter still runs (the kernel
checks by running it), the rebuild when it does not. `romp new` and the
browser's create refuse with the same verdict, read from the disk at the moment
of the request, so a venv rebuilt while the kernel runs is reported on both
surfaces as set up after romp started, with the restart as the remedy. The
Codex venv (`codexvenv`, built by `bin/romp-codex-setup`) follows the same
pick and the same rebuild check, and the kernel adds only the site-packages
built for its own tag from it as well; nothing on the restart path runs the
script, so a move needs its own re-run of `bin/romp-codex-setup`, and until
then the kernel logs the mismatch once, naming that remedy, and refuses Codex
sessions.

### Service environment and credentials

The manager runs as a login service (launchd on macOS, systemd --user on
Linux), so it does not receive variables exported by your shell rc. Configure
the service in `~/.config/romp/service.env` using plain `KEY=VALUE` lines and
owner-only permissions (`chmod 600`). The file carries the billing declaration
(`ROMP_EXPECTED_AUTH`, below) and the service knobs (the ports, the CLI scopes
and their memory limits, the perf log), never a key. The service reads the file
at manager startup, so a change needs a manager restart. `ROMP_SERVICE_ENV_FILE`
overrides the file's path.

Romp holds no API key (the user 2026-09-08, who wants romp to hold no key). A
session's credential is Claude Code's own resolution: the `apiKeyHelper` in its
settings (the helper) for a key, the login otherwise. Romp injects no credential
into a session, a judge child or a tmux pane, runs no key command, reads no
secret-manager reference, and keeps no key in `service.env`.

A retired key path stops the kernel at boot. A `service.env` that still carries
`ROMP_API_KEY_CMD`, `ROMP_API_KEY_REF` or `ANTHROPIC_API_KEY`, or one of the
1Password CLI's names (`OP_SERVICE_ACCOUNT_TOKEN`, `OP_CONNECT_HOST`,
`OP_CONNECT_TOKEN`, `OP_ACCOUNT`, `OP_SESSION_*`: romp no longer runs `op`, and a
helper that needs that token reads it from a file of its own), a
`service.env.source` marker beside it, or a kernel environment that carries one
of those names at boot is a boot failure: the kernel stops before anything is
spawned, and the message names the file and the variable names, never a value,
says that romp did not start, and gives the fix (remove the lines, configure
the helper, declare the billing, start again). The supervised manager retries
and writes the message to its `manager.log` each time until the file is
repaired. The manager refuses in the same way, before it starts the tmux
server, when its own environment carries one of the names (it is what receives
`service.env`, and every terminal pane inherits the server's globals), and
`romp new -t` refuses to start a terminal session while the tmux server's
globals carry `ANTHROPIC_API_KEY`. A key romp holds is a key a session can
print, so there is no quiet fallback anywhere.

At boot the kernel also names, once and as information rather than a problem,
the variables in its own environment shaped like credentials (names ending
`_API_KEY` or `_TOKEN`, and 1Password's own `OP_*` names) that reach every
session's Claude process and the shells it spawns: the SDK hands each session
the kernel's environment, and romp takes only the login tokens it claims at
boot (see [The login](#the-login)) out of it. The line carries names only,
never values, and a second provider's key placed there on purpose is nothing
to act on. To keep a variable away from sessions, remove it from `service.env`
or from the service unit's environment and restart the manager.

#### A key from a secret manager

Claude Code's own credential resolution is the only key path. Point Claude
Code's [`apiKeyHelper`](https://code.claude.com/docs/en/settings-reference#apikeyhelper)
at your secret manager: the CLI runs the helper, holds what it prints, and
re-runs it after `CLAUDE_CODE_API_KEY_HELPER_TTL_MS` (five minutes by default)
and on a 401 or 403. Every session and every key-billed judge call runs the
helper inside its own Claude Code process. Romp never sees the key: the
Billing picker and the tooltip row read the setting to know that a key exists,
and no surface of romp's fetches it.

1. Write a script that prints the key from your secret manager, and make it
   executable. The script fetches its own credential: the CLI runs the helper
   as a child of the service, with no desktop app to unlock, so the secret
   manager needs a credential that works unattended, and that credential
   belongs in a `chmod 600` file the script reads, not in any environment.
   With 1Password that is a
   [service account](https://developer.1password.com/docs/service-accounts/)
   with read access to the one vault and nothing else:

        #!/bin/sh
        # ~/.config/romp/fetch-api-key (chmod 700): print the API key, nothing else
        OP_SERVICE_ACCOUNT_TOKEN="$(cat ~/.config/op/service-account-token)" \
            exec op read --no-newline "op://vault/item/field"

    Any secret manager's CLI works the same way (`aws secretsmanager
    get-secret-value --query SecretString --output text`, `vault kv get
    -field=…`, `bw get password …`, `gcloud secrets versions access latest
    --secret=…`, `pass show …`): one line on stdout, exit 0. The CLI must be on
    the service's PATH. The service installer records PATH at install time, so
    run `romp-service install` again after changing it.

2. Point Claude Code at the script in `~/.claude/settings.json`:

        { "apiKeyHelper": "/path/to/fetch-api-key" }

    Claude Code reads its settings files in a fixed precedence: managed
    settings (`/etc/claude-code/managed-settings.json`; `/Library/Application
    Support/ClaudeCode/managed-settings.json` on macOS), then a project's
    `.claude/settings.local.json` and `.claude/settings.json`, then
    `$CLAUDE_CONFIG_DIR/settings.json` (`~/.claude/settings.json` by default).
    The highest file that defines `apiKeyHelper` as a string wins; a `null`
    falls through to the next file. The kernel acts on the two files the
    operator of the box controls, the managed and the user file: they decide
    whether the box has a key side at all (the Billing picker's key choice,
    the default for unpicked sessions and judge calls), and they name the one
    helper the kernel runs in-process for its own two calls. A project's own
    `.claude/settings.json` is Claude Code's business: the CLI runs that helper
    for sessions in the project, behind its trust prompt, and the per-init auth
    check reports where such a session landed, but the kernel never runs a
    command a repository checked in, and its fast-mode probe stands down for a
    session whose project would resolve a different helper. The per-session
    settings layer romp writes for a login pick sits above the project files,
    which is how a login pick disables the helper for one session (see
    [Per-session billing](#per-session-billing-login-vs-api-key)). The kernel
    reads the files fresh on every check, so a helper added later counts at
    once; a settings file that cannot be read or parsed is a problem row in the
    Log panel, and the box reads as having no helper until it reads. A helper
    set in the MANAGED file outranks the per-session layer, so no login pick can
    disable it: on such a box the Billing picker offers no login choice and a
    login pick is refused with that reason, never billed to the key quietly.
    The kernel keeps the value its own two calls fetch only within the helper's
    TTL: it is cleared when the TTL ends, when a run fails, and when the helper
    is removed from the settings.

3. Declare the billing in `service.env`: `ROMP_EXPECTED_AUTH=key`. On a box
   with a helper every session without a login pick bills the key, so the
   declaration is true, and the per-init auth check stays quiet on every keyed
   landing and flags a login landing. Leave no key line in the file: one left
   over from an earlier romp, or a marker beside the file, is the boot failure
   above.

4. Restart the service once, for the declaration; `service.env` loads at
   manager startup. Sessions and judges run the helper from their next launch.

Judges (`claude -p` children of the kernel) launch with no credential in their
environment. A key-billed judge call resolves the helper itself, inside its own
CLI, the way a session does. A login-billed call passes the same helper
suppression (`--settings '{"apiKeyHelper": ""}'`) and gets back the login
tokens the kernel claimed at boot. A helper that fails inside a judge's CLI
fails that call with a credential error, which latches the session's
judge-auth-down state like any other credential failure (see
[judges.md](judges.md#billing-and-when-the-credential-itself-is-broken)); it
never falls back to the login.

The kernel makes two API calls of its own: the model catalog refresh and the
fast-mode organisation probe. Both read the helper from the settings files
above, in the same order, for the kernel's working directory, and run it
in-process. The value lives in the kernel's memory for the helper's TTL
(`CLAUDE_CODE_API_KEY_HELPER_TTL_MS`, five minutes by default, the CLI's own
interval) and goes to the one request that asked, never to an environment
variable, a file or a log line. The helper runs through `/bin/sh` with stdin
from `/dev/null`, a 15-second timeout, stderr discarded and never logged (a
secret manager's diagnostics can quote its own token), and a minimal
environment: `PATH`, `HOME`, `USER`, `LOGNAME`, `TMPDIR`, `LANG`, `LC_*`, `TERM`,
`CLAUDE_CONFIG_DIR` and the `XDG_*` names, and nothing of romp's, the serve
token included. Its output must be one non-empty line with no whitespace, at
most 16 KiB; a trailing newline is forgiven. A helper that fails is a problem
row in the Log panel in static words. With no helper configured the catalog
serves its cached list, or its built-in one, and the kernel log says why at
each refresh attempt (boot, and once per model id it does not know); the
pickers still work, and Claude Code's own alias table still tracks each
family's newest. The fast-mode probe then leaves the CLI's own check standing
and says nothing.

#### The login

A box with no helper bills the login. Authenticate through Claude Code's own
CLI login flow (`claude /login`) and pick **Login** in Billing, or leave the
pick alone: with no helper the picker offers no key choice, and every session
and judge call lands on the login. No extracted OAuth token is needed. Login
tokens the kernel finds in its own environment at startup
(`ANTHROPIC_AUTH_TOKEN`, `CLAUDE_CODE_OAUTH_TOKEN`) are claimed at boot and
handed only to login-billed launches, so a key-billed session never inherits
one. Declare `ROMP_EXPECTED_AUTH=login` when the box is meant to stay on the
login: a session whose CLI then reports a key (a helper in a project's
`.claude/settings.json`, say) is flagged in the Log panel, naming the
declaration.

### Rotating the key

Rotation is a change to the vault item behind the helper, and nothing else.
Claude Code caches what the helper printed and re-runs it after
`CLAUDE_CODE_API_KEY_HELPER_TTL_MS` (five minutes by default) and on a 401 or
403, so running sessions and judges pick the new key up within the TTL, or at
the first refusal of the old one, with no restart and no reconnect. The
kernel's own two calls re-run the helper on the same interval. Nothing in romp
needs to know: `romp keyswap` prints a short note saying that rotation is the
vault item, and does nothing else. Remote kernels each read their own
machine's Claude Code settings, so a key shared across machines rotates once,
in the vault, and everywhere within the TTL.

### Two things still need a restart

`service.env` loads when the manager starts: the service reads it into the
manager's environment, every kernel inherits that environment, and `romp
refresh` restarts kernels, not the manager (unless `bin/romp-manager` itself
changed since the manager started: then a supervised manager exits and its
respawn reads the file), so a value added, changed or removed there reaches
the kernel at the next manager restart, `systemctl --user restart
romp-manager` on Linux and `launchctl kickstart -k gui/$(id
-u)/com.romp.manager` on macOS. A line in the unit's own `Environment=`, in a
drop-in, or in the profile a shell-wrapped `ExecStart` sources (Linux), or in
the plist's `EnvironmentVariables` (macOS), is different: a manager restart
re-applies it, so it has to be removed where it is and the service definition
reloaded before the restart. On Linux that is `systemctl --user daemon-reload`
after editing a unit or a drop-in, then the restart. On macOS `launchctl
kickstart -k` restarts the job as launchd loaded it and does not re-read the
plist, so the job is reloaded instead, and the reload is `romp-service
install`: it rewrites the plist (a line added to it by hand goes with the
rewrite), boots the job out, waits until the old job has left launchd,
bootstraps the plist again and checks that the job runs, which is the reload
and the restart in one. It waits because `launchctl bootout` only starts the
old job's teardown: a manager draining live sessions takes seconds to exit, and
a `launchctl bootstrap` issued while it drains is refused with `Input/output
error` and leaves no agent loaded at all, the old job gone and the new one not
accepted (an install ended that way before the installer waited). A plist you
edited by hand, which the install would overwrite, takes the same sequence by
hand, wait included: `launchctl bootout gui/$(id -u)/com.romp.manager`; then
`launchctl print gui/$(id -u)/com.romp.manager`, repeated until it fails; then
`launchctl bootstrap gui/$(id -u)
~/Library/LaunchAgents/com.romp.manager.plist`, repeated if it is refused. On
Linux `romp-service install` rewrites the unit and reloads systemd but leaves a
running manager as it is, so the restart still follows. The rewrite drops a
line added to the unit by hand, as the plist rewrite does; a drop-in survives
it, so a line of your own belongs in `service.env` or a drop-in.

### Stopping the kernel on purpose

`romp down` stops the kernel and keeps it stopped until `romp up`. The manager
is supervised (`Restart=always` under systemd, `KeepAlive` under launchd), so a
kernel or manager that merely exits is back within seconds. `romp down` instead
stops the login service itself (`systemctl --user stop romp-manager.service`;
on macOS `launchctl bootout` of the agent), which nothing respawns, and then
probes the processes themselves rather than trusting the exit code of
`romp-service stop`.

Before stopping, `romp down` gives the turns in flight `--wait` seconds
(default 5, up to 600) to reach a turn boundary. It asks the kernel to quiesce
(`POST /down`), which holds new turn starts and new session creation, and then
reports whether the kernel went quiet or which sessions are still mid-turn and
about to be cut. `--now` skips the wait, not the request: when a kernel answers
on the port, the same `POST /down` goes out with a wait of 0 and nothing is
reported about it, so the token check below still comes first; the hold it arms
is the grace the kernel keeps after any wait, and the kernel probe re-arms it
right before the signal. A
`romp new` or a dashboard create during the hold is refused with one line
saying the kernel is being stopped on purpose and no new session can start; the
line names no command, because inside a session its reader is an agent, and an
agent told to run `romp up` would undo the stop. If the stop never lands, the
kernel carries on by itself: the hold is a lease, and it lapses a short grace
period after the wait. The stop then cuts what a `romp refresh` cuts, and it
comes back the same way (see [What survives a restart](#what-survives-a-restart)).

`romp down` signals only a kernel it has confirmed as its own: one that
accepted this romp's serve token on `POST /down` and named the pid that
`GET /version` also reports. A kernel that rejects the token (HTTP 401 or 403)
is another romp's or another program's. When the quiesce request is rejected,
`romp down` prints `romp down: the kernel on :<port> is not the one this romp
manages (it rejected the serve token); not touching it. Check
ROMP_KERNEL_PORT and the state dir` and exits 1, before the marker is written
or anything is stopped. Under `--now` the same request goes out with a wait of
0 whenever a kernel answers on the port, so a rejected token ends the command
at the same point; the kernel probe asks again right before the signal, and a
rejection there removes the marker.

The exit code of `romp-service stop` decides the first step; the probes after
it run every time:

- Exit 0 (the unit or agent stopped), 3 (no login service installed) or 4
  (installed but not running): on to the probes. After a 3 or a 4, any manager
  running is outside the service (a foreground `romp up`, a hand
  `romp-manager up`).
- Any other exit: the service refused to stop, and the kernel is most likely
  still up. `romp down` releases the quiesce hold, removes its marker, prints
  `romp down: the login service did not stop` and exits 1.
- The manager probe: `romp-manager status` on the control port (`:7432` by
  default). A manager that answers is stopped through its own control endpoint
  (`romp-manager down`, a `POST /stop` carrying the serve token; see [The
  manager's control port](#the-managers-control-port)). Two outcomes:
  - The manager answers and refuses (HTTP 401: the manager does not hold the
    token this romp sent, so it runs under another state root or belongs to
    another romp, or this romp found no token to send, at its token file or in
    `ROMP_SERVE_TOKEN`, and sent none; HTTP 503: the manager cannot read its
    own token file). Said at once, with no poll: `romp down` releases the hold,
    removes the marker, writes a `down-failed` row naming the status, prints
    `romp down: the manager on :<port> refused the stop (HTTP <status>: <the
    manager's words>). <the remedy> The kernel keeps running.` and exits 1. The
    remedy names where this romp read its token: for the file under its state
    root it says to check `ROMP_STATE_DIR` and `ROMP_MANAGER_PORT`; for
    `ROMP_SERVE_TOKEN` it says to unset the variable in this shell or set it to
    the manager's token, or check `ROMP_MANAGER_PORT` (the state root changes
    nothing while the variable is set); when this romp found no token, it
    names the file and the reason and says to point `ROMP_STATE_DIR` at the
    manager's state root or set `ROMP_SERVE_TOKEN`; on a 503 it says to repair
    the manager's file.
  - The manager takes the stop and is given up to seven seconds to leave (the
    manager itself waits five for its kernels, then sends SIGKILL). One still
    answering after that: `romp down` releases the hold, removes the marker,
    prints `romp down: a manager is still running on :<port> (pid <pid>)`,
    which says to stop it by hand and run `romp down` again, and exits 1.
- The kernel probe: `GET /healthz` on the kernel port (`:29855` by default). A
  kernel the earlier steps already asked to stop gets three seconds of drain
  first. One still answering (it ran with no manager, or outlived the
  manager's SIGTERM) must first be confirmed as this romp's: `POST /down` with
  a wait of 0 under the serve token must answer 200 naming a pid, and
  `GET /version` must name the same pid. That pid is sent the manager's own
  stop signal (SIGTERM) and given up to six seconds to leave. Any other answer
  (a rejected token, a 200 without a pid, a pid `GET /version` disagrees with,
  another HTTP code, no answer) leaves the kernel alone: `romp down` releases
  the hold, removes the marker, appends a superseding `down-failed` row to
  `restart-audit.jsonl`, prints
  `romp down: the kernel on :<port> was not confirmed as the one this romp
  manages (<why>); not touching it. Check ROMP_KERNEL_PORT and the state dir`
  (a rejected token gets the rejected-token line instead) and exits 1. One
  still answering six seconds after the signal gets the same release and
  `down-failed` row, then
  `romp down: the kernel on :<port> (pid <pid>) is still running after being
  asked to stop`, which says to stop it by hand and run `romp down` again,
  and exits 1.
- Nothing left answering: a `[romp] down` line that says what stopped (the
  service, a manager outside it, a kernel the probe found, or a kernel that
  answered the quiesce and has since gone) and names `romp up`, or
  `[romp] nothing was running` when neither the service nor a manager was up
  (the auto-start stays held until `romp up`), and exit 0.

With a login service installed, the unit stays enabled, so it comes back at
`romp up` or when the service manager next starts it. On Linux that is the
next boot, not the next login: `romp-service install` enables
linger, so your `systemd --user` instance outlives your logins and a stopped
unit stays stopped through them (where the linger call failed, the instance
ends at logout and the next login starts the unit again). On macOS the
booted-out agent loads again at the next login.

The stop leaves a marker, `down-by-romp` under the state directory (with the
time and the command), so the stopped kernel reads as stopped on purpose. While
the marker exists and no manager answers, `romp status` prints
`down (romp down at HH:MM; romp up to start)` and exits 0 instead of the
manager's not-running error; a marker from an earlier day shows its date
(`down (romp down at 2026-09-04 17:12; romp up to start)`), and one with no
readable time drops it (`down (romp down; romp up to start)`). A manager that
does answer outranks the marker: `romp status` prints its usual report and
exits 0. `romp-service status` reports the marker too, as
`stopped by romp down at HH:MM (romp up to start)`.

The marker also blocks romp's other ways of bringing the kernel back.
`romp-manager ensure` refuses to bring the manager back. `ensure` is the
supervised start that `romp update <host>` and the dashboard's remote restart
run on the far host, so a remote stopped by
`romp down` is left stopped: `romp update` syncs its code, restarts nothing,
and says so, and `romp up` there boots the new code. The dashboard's
Start button and an attach's bootstrap, which boot a bare kernel on a host with
no manager, decline the same way and name `romp up` on that host. `romp up`
clears the marker and starts the service; a manager started any other
deliberate way (the login service at the next boot, a hand
`systemctl --user start`) clears it too.

`romp down` also appends a row to `restart-audit.jsonl` that names the action, so the kernel's
restart-cut ledger records the cut as a `down`, not an anonymous SIGTERM; a
`romp down` whose stop did not land appends a superseding `down-failed` row,
so a later cut of the kernel it left running is never blamed on it.

Sessions come back at the next `romp up` from what is already on disk: the
kernel's boot reconcile reads each session's registry entry and state tail and
needs nothing written at shutdown. A session whose turn had ended before the
stop is revived on demand, with its history, the next time something reaches it;
a session cut mid-turn is resumed at boot and told its turn was cut. When the
stop was a `romp down` (the newest `restart-audit.jsonl` row is a `down`, and
the cut turn started at or before its time), the notice also gives the stop
time, the start time and the gap, so a model resumed hours later re-checks what
it was running before relying on it.

Terminal (tmux) sessions survive the stop where they survive a service restart
(see [What survives a restart](#what-survives-a-restart)): on
Linux `systemctl --user stop` kills everything in the service's cgroup, so the
tmux server and its sessions live on only when the manager started it in its
own transient scope (the default under the service since 2026-09-05; off with
`ROMP_CLI_SCOPE=0`, and not yet true of a tmux server that predates the scopes).
On macOS there is no cgroup kill, and the tmux server survives the stop.

Only `romp refresh` stops the postal bus on purpose; `romp down` leaves it
alone, but on Linux a bus the kernel started dies with the service anyway: the
kernel runs `romp-postal-service ensure` at boot, which spawns the bus in a
process session of its own but inside the service's cgroup, and the service stop
kills that cgroup. A bus started from a session's postal MCP server lives in
that session's scope and keeps running. Either way the next kernel boot runs
`ensure` again, so at worst mail parks until `romp up`.

### What survives a restart

A kernel restart ends every session's CLI. On `romp refresh`, the manager's
restart-all, `romp down` or a service stop, the kernel receives SIGTERM and drains: it
closes each CLI, and a CLI still running when the drain's bound expires gets
SIGTERM, then SIGKILL. The manager does the same to the kernel: one still
running five seconds after the manager's SIGTERM, on a restart as on a stop, is
sent SIGKILL and the manager logs it; on a restart the fresh kernel then starts
as usual. A crash respawn has no drain: the kernel died without
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

A message the kernel cannot handle does not end the session's CLI. The kernel
handles each streamed message on its own: when a handler raises, it logs the
exception type and the failing frame (file, line and function, first on the line
so the error center's clipped row still shows it), the message's type and
subtype, what that message lost (an assistant or user message is also a
transcript record, so the chat rebuilds it from disk; a compaction boundary is
one too, while a model or mode change's confirmation line is not; a turn result
still settles its turn, and the line says so only when the settle ran; a
stream-only frame's content is gone until the next such frame), the exception's
own text (uuid-shaped ids shortened to eight characters, clipped to 160
characters; it carries whatever the raising code put in it, never the message's
content), and a compact frame chain (innermost first: file, line and function
for at most the innermost eight frames, no locals, at most 600 characters,
dropping outer frames first so the failing frame is always named) to the kernel
log and the dashboard's error center, then goes on to the next message. A
failure while filing a turn result (its spend, its API-health note, its
live-tail sweep) still settles the turn: the session reads waiting, its queue
moves, and a reconnect that waited for the turn's end runs; the spend
accounting runs last among the result's bookkeeping, so its failure skips
nothing else. A handler that fails on every message is one error-center entry,
showing its first occurrence: the repeat count is kept on the kernel's problem
ring (appended to the row's text, past what the error center displays), every
repeat is a kernel log line, and an entry the ring has since dropped re-enters
with its full detail.
Before 2026-09-06 one such exception ended the receive loop, which closed the
CLI in the middle of its work (the in-flight turn, its subagents, its background
tasks) and resumed the session as after a crash. A fault of the stream itself,
such as the CLI exiting or its transport closing, still ends the loop; the log
names the failing task and its frame chain, and the session resumes with its
history, told what was cut.

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
(`romp up --foreground`, or `romp up` with no service installed) scopes nothing
unless `ROMP_CLI_SCOPE=1` is set, which turns both on. The kernel logs which it chose at start (`cli scope: on` or `off`, with the
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
  Leave it unset, or set it equal to `MemoryMax`; the two are the same thing:
  cgroup v2's `memory.high` defaults to `max`, and usage cannot pass an equal
  soft limit without reaching the hard one, where `MemoryMax` takes over: with
  the swap limit below at `0` (the recommendation), or no swap on the machine,
  the cap is the kill; with swap allowed, the scope swaps first and is killed
  when its swap allowance is used up (a finite `MemorySwapMax`) or when the
  machine's swap is full. Never set it below `MemoryMax`:
  throttling reclaims memory, and with the swap limit at `0` (or no swap) a
  runaway that allocates tens of GB of anonymous memory in seconds holds none
  Linux can reclaim, so a lower soft limit only stalls the process for
  minutes while it creeps toward the cap and the whole machine sits at high
  memory pressure (measured 2026-09-10 on the administrator's box with a 12G
  soft limit under a 16G cap and `MemorySwapMax=0`: about 50 MiB every 5
  seconds, PSI memory `full` at 42 percent; the throttle's delay grows with the
  overage, so the rate holds for that pair only). That stall is memory pressure
  `systemd-oomd` can act on: on a machine where it is set to act on the user
  manager's pressure (`systemctl show user@$(id -u).service -p
  ManagedOOMMemoryPressure` prints `kill`) it can kill the whole throttled
  scope, `OOMPolicy=continue` notwithstanding. When the scope can swap, the
  throttle pushes the runaway's pages to swap instead, the slowdown the swap
  entry below describes, so a lower soft limit helps in neither case.
- `ROMP_CLI_SCOPE_MEMORY_SWAP_MAX`: the swap limit (`MemorySwapMax=`). Without
  it, a scope at `MemoryMax` pushes pages to swap instead of being killed, until
  the machine's swap is used up, and the swapping slows every other process. On
  a machine with swap, set it to `0`, so a scope over its limit is killed rather
  than swapped.
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
253) and reports it the same way, quoting systemd; the policy refused on such a
systemd, by a failure that names it, is the plain line described in the
`OOMPolicy=continue` paragraph below, and the memory limits are then probed
apart from it, so they stand there when that probe passes; the paragraph on the
boot probe names the two other outcomes.
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
the kernel's boot line and `/api-health` (the `cliScope` block) said the value
was in force. So with the scopes on, the kernel runs the wrapper's own steps
once at its start: it starts a probe scope carrying the memory properties and
`OOMPolicy=continue`, and has a throwaway child write the adjustment to its own
`oom_score_adj`. A refusal there is a problem line at the kernel's start (a
plain line when only the policy was refused, by a failure that named it), joins
`cliScope.rejected` in `/api-health`, and reaches the wrapper as an empty
variable, or, for the policy, as `ROMP_CLI_SCOPE_OOM_POLICY_REJECTED=1`, so no
launch repeats it. When the combined probe fails and a memory limit is set, the
kernel probes apart whichever member the deciding failure did not decide for, so
the verdict is a probe result rather than a guess. When the failure names the
policy (a systemd before 253), it probes the limits alone once more: if that
scope starts, only the policy is refused and the limits stand (the
memory-controller check below then runs with the limits alone); if it fails too,
the limits are refused with the policy, as one problem line quoting both
failures; if it does not answer, the policy is refused and the limits are left
unsettled, as described next. When the failure does NOT name the policy (a memory
size systemd refuses), it probes the policy alone once more: a pass drops the
memory limits alone and keeps the policy on every scope (the marker goes down
empty and `/api-health` reads `continue`), a failure naming the policy refuses it
with the limits quoting both, and a raise or a failure that does not name it
leaves the policy unsettled with the limits refused. The
adjustment's problem line quotes the shell and says which step
failed: it names the floor only when the file opened and the write was refused;
otherwise it says the file could not be opened, and why. The wrapper's
`ignored:` line makes the same distinction. A probe that does not answer (the
user bus away at that moment) settles nothing. The kernel says so in its log (a
plain line, not a problem), hands the values down as read, and lists them in its
boot line as set but not settled, naming the check; the values whose checks did
answer keep their own verdict in the same line, so an unanswered check for one
value never makes another unknown. `cliScope.unsettled` in `/api-health` names
the check too. Whether the values apply is then known from the wrapper's report
on each launch. The wrapper keeps the same guard on every launch. Its pre-flight
scope carries the properties. If that fails, it retries bare; if the bare scope
starts, it tries once more with the properties, and only that second failure
drops them, for that launch, with one `ignored:` line quoting the failure that
decided. (A bare failure is the fallback described above, counted under
`cliScope.fallbacks`.) The CLI then starts in its scope without the memory
limits; the adjustment is still written. On a launch the kernel drove, an
`ignored:` line quoting a systemd rejection means the machine changed under the
running kernel.

The wrapper sets `OOMPolicy=continue` on every scope, whether or not a memory
limit is set. A scope's default is `stop` (the user manager's
`DefaultOOMPolicy`): when Linux's OOM killer kills one process in the scope, any
process, over a limit of the scope's or with none set, systemd stops the whole
scope, which ends the CLI and every tmux server, `setsid` job and background
task in it. That happened on 2026-09-10: the machine-wide OOM killer took one
tool child in a session's scope that had no limits, the CLI exited 143, the
kernel resumed the session, and 41 background tasks died with it. With
`continue`, only the killed process is gone, and a kill contained in one process
never becomes a cut turn. The property has to be set when the scope is created:
`systemctl set-property` takes cgroup properties only, so a limit added to a
running scope cannot add it. Until 2026-09-10 the wrapper set it only along
with a memory limit, so a scope started without one kept `stop`. A systemd
before 253 refuses `OOMPolicy=` on a scope and stops the whole scope on an OOM
kill inside it, as every scope did before the property went on all of them; the
kernel's probe at its start (above) settles the refusal once, hands the wrapper
`ROMP_CLI_SCOPE_OOM_POLICY_REJECTED=1` so that no launch finds it out again, and
says so in a plain line rather than a problem, since the refusal is the
machine's systemd version, not a setting to fix. The memory limits are probed
apart from the policy (above), so on such a systemd they still apply; a problem
line comes only when a limit is refused. The variable is the kernel's, not a
setting: the kernel sends it on every launch with an explicit value, `1` or
empty, so a value inherited from the manager's environment is never read.
`/api-health` shows the policy as `cliScope.oomPolicy`. When a session's CLI
dies mid-turn, the kernel names the cause from three signals, primary first:
the CLI's own exit, the scope's cgroup counter, and systemd's record of the
scope. The first is the CLI's own exit: the SDK reports how the process ended,
and a death by SIGKILL (signal 9) is the OOM killer's signature under
`continue`, the cgroup's own killer and the machine's global one alike. It
survives the scope's collection: a lone CLI IS the scope's last process, so the
scope is gone the instant it dies and the counter with it, but the exit is
always read. The exit is -9 because every layer of the launch chain execs in
place, so a `claude_bin` wrapper must exec too: a shim that runs the CLI as a
child reports the child's SIGKILL as its own exit 137, which the kernel reads as
a plain exit, and such a shim also defeats the interrupt escalation and the
orphan finder, so it is outside what romp supports. An exit of -1 is the SDK's
own sentinel for an exit it could not read (a SIGHUP death reports the same) and
is logged in those words, never as a kill by signal 1. The second is the scope's
cgroup `memory.events`, whose `oom_kill` count is read against a baseline taken
at the start of each turn (one file read per turn) and decides what a SIGKILL
was, since on cgroup v2 the counter counts the memcg killer's and the global
killer's kills alike. An increase over the baseline with a SIGKILL exit names
the CLI's death out of memory. A readable counter that did NOT rise with a
SIGKILL exit excludes the kernel's killers and leaves a kill by hand or a
userspace killer the counter cannot see (earlyoom), so the kernel names a kill
by signal 9 with no OOM kill counted, in its log and in the notice the session
reads, and never says out of memory. A counter that cannot be read on a loaded
unit (a legacy hierarchy, a `memory.events` that will not open) leaves the
SIGKILL standing alone as the killer's signature, with the unit's `Result`
stated beside it; a counter gone with the scope's collection hands the decision
to the journal (below). One timing race sits between the show and the read: a
unit the show called loaded whose cgroup systemd collects before `memory.events`
is opened (about 10 ms after a lone process's death) reads as a loaded unit with
an unreadable counter, so its SIGKILL is named out of memory from the exit alone,
with no journal read. An increase WITHOUT a SIGKILL exit is a contained tool-child kill the
CLI outlived, named as a child and never as the CLI's own death, and only
against a baseline that was read: the whole-life count without one is context,
not a verdict. The third is the unit's `Result=oom-kill`, which systemd records
on a scope WITHOUT the property when it stops the scope over an OOM kill in it:
a launch on a systemd that refused the property (the marker above), a launch
whose pre-flight dropped the properties (the `ignored:` line above), or a scope
started before the property went on every one. The Result survives on the unit
only while a member outlives the SIGTERM; when every process goes down on it,
systemd collects the unit within milliseconds of the CLI's exit, before the SDK
reports that exit, and `systemctl show` finds nothing. For a unit already gone
the kernel therefore reads the user manager's last journal lines for it,
whatever the exit (`journalctl --user -n 5 -o cat -t systemd -u <unit>`,
bounded like the show; `-t systemd` keeps the manager's own lines, since a
scope member's `logger` lines carry the unit too and would push them out of the
window), and reads them from the last `Started` line on (whatever the manager's
`StatusUnitFormat=` puts after the word: the unit, its description, or both), so
an earlier unit of the same name inside the window is not read as this one. `<unit>:
Failed with result 'oom-kill'` names the whole-scope stop, with the journal as
the source. `<unit>: A process of this unit has been killed by the OOM killer`
is the manager's record of each OOM kill in the scope, written before the unit
is collected and surviving it; it is whole-life, so with a non-SIGKILL exit it
names nothing (a contained kill under `continue` leaves it too), and with a
SIGKILL exit and the scope collected it is what decides, with the stop line and
the manager's `<unit>: systemd-oomd killed N process(es) in this unit` line (its
record of a kill by systemd-oomd, the one userspace killer that leaves a line):
with any of the three the death is out of memory, with none of them the kernel
names a kill by signal 9 that the journal does not record (a kill by hand, or
earlyoom, which leaves no line) and never says out of memory, and a journal that
cannot be read or has no line for the unit reads the same way, since a definite
verdict needs a definite record. The kernel names the OOM
kill, with the evidence, in its log line for the resume and in the notice the
session reads, instead of reporting a bare exit; a memory limit is named beside
it only when `MemoryMax` is set and the controller is not known to leave it
unapplied, as context and never as a guess, in the boot line's own words: in
force when the controller check settled so, set for the scope but not settled
when that check or the memory-limits probe settled nothing. A non-SIGKILL exit
with no counter increase reads as no OOM verdict and the bare notice. Every path
writes one plain log line saying what was read and what was not: a scope
already collected (the counter gone, and what the journal said), a loaded unit
whose `memory.events` cannot be read (with its `Result`), a `systemctl show`
that fails, and a `journalctl` that fails or has no line all say so, and none
is silent. systemd logs each kill to the user journal as `<unit>: A process of
this unit has been killed by the OOM killer` (`journalctl --user --since today
| grep 'romp-session-'`), and a scope it stopped over one as `<unit>: Failed
with result 'oom-kill'`; without the memory controller delegated to the user
manager (below) it logs neither. When the kernel's start-time controller check
settled that verdict (it runs only with a memory limit set) the heal says so
beside the kill verdict; otherwise the evidence carries no such clause.

The limits need the memory controller delegated to the systemd user manager;
stock systemd delegates it (`systemctl show user@$(id -u).service -p
DelegateControllers` lists `memory`). Without it, systemd accepts the
properties, reports them from `systemctl --user show`, and applies nothing; the
cases are an administrator's drop-in on `user@.service`, the legacy cgroup
hierarchy, a kernel booted with the controller off, and a container whose cgroup
subtree lacks it. The kernel checks for this at its start, inside the probe
scope above: the scope's cgroup has a `memory.max` file when, and only when, the
controller is there. A missing one is a problem line at the kernel's start, and
`/api-health` carries the verdict as `cliScope.memoryControllerDelegated`. A
probe that exits non-zero or does not answer (its scope fails to start, it does
not finish, its command is killed or exits without a marker) is tried once more;
one that exits 0 without printing a marker is not. When no try gives a verdict,
that is a problem line too: it says what each try did (one try, or two) and
quotes systemd's refusal, the exit status, or what was printed; and the check is
left unsettled: the verdict stays `null`, and `cliScope.unsettled` names it.
Whether the memory limits apply is then unknown until the next kernel start. To
check a live session, run from a shell inside it: `cat /sys/fs/cgroup$(cut -d:
-f3 /proc/self/cgroup)/memory.max` prints the limit in bytes, `max` when none
applies, and fails when the controller is not there.

A suggested starting point for a shared 62 GB machine that hosts a dozen
sessions: `ROMP_CLI_SCOPE_MEMORY_MAX=28G`, `ROMP_CLI_SCOPE_MEMORY_HIGH=28G`,
`ROMP_CLI_SCOPE_MEMORY_SWAP_MAX=0`, `ROMP_CLI_SCOPE_OOM_SCORE_ADJ=500` (the
soft limit is written out equal to the hard one; leaving it unset is the same
setting). One session can still take nearly half the machine, far more than any
ordinary tool call needs; the kernel (a few GB), the other sessions and the
system keep the rest. When a session's scope reaches 28 GB, the cgroup's OOM
killer kills the largest process in it, with no throttling or swapping first.
Usually that is a tool's process, and the session goes on with a failed tool
call. When the CLI is itself the largest process, it dies, and the kernel
resumes the session with its history, as after any CLI death. An adjustment of
500 adds 500 points to each session's OOM score, on a scale where 1000 points
is the whole of the machine's memory, so earlyoom and Linux's OOM killer, which
rank processes by that score, choose a session before the kernel.

Size the cap to sit inside the threshold of the machine's own OOM killer, so
the scoped kill happens first. At its defaults, earlyoom acts once available
memory and free swap are both at or below 10 percent, so with swap it acts
later than at 10 percent of memory available (`MemorySwapMax=0` keeps the scope
out of swap and does not change when earlyoom acts). Those thresholds are its
`-m` and `-s` percentages (`-M` and `-S` in KiB), set in `/etc/default/earlyoom`
on Debian and Ubuntu; earlyoom logs the thresholds it runs with when it starts
(`journalctl -u earlyoom -b`), and `pgrep -a earlyoom` shows its flags. On a
machine running it, the cap plus what the kernel, the other sessions and the
system hold at the time should stay under that point. `systemd-oomd` chooses a
whole cgroup by its own rules (reclaim activity on its pressure path, swap use
on its swap path; `man oomd.conf`) and is not steered by `oom_score_adj`. A
machine with neither is bounded by Linux's OOM killer at exhaustion. earlyoom
and Linux's OOM killer choose a process by `oom_score`, so with the adjustment
of 500 on every session they pick a session before the kernel, but the pick is
not scoped to the runaway's cgroup and can be a well-behaved session. Staying
under the threshold keeps the kill inside the scope that caused it. A heap
flag on the process is no substitute for the cap: node's
`--max-old-space-size` limits the V8 heap only, and a typed array's backing
store is allocated outside it, so a process can pass that figure many times
over with the flag in force.

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

## Kernel performance counters

`GET /perf` returns one JSON document of counters the kernel keeps at all
times: what its pusher, judge and HTTP threads have done since the process
started. The route takes the serve token. The counters cost a lock and a few
dictionary increments per event, so they stay on; nothing is formatted or
serialized until a request reads them. `romp perf` takes two snapshots
`--interval` seconds apart (default 10) and prints the difference as rates on
one screen: pusher cycles and wakes per second, the cycles the minimum
interval between cycle starts held and the watched-tab wakes exempt from it,
cycle time percentiles, the share of cycle time in each stage, CPU split between the pusher thread, the
judge threads and the rest of the process, builds served from cache against
rebuilds, bytes sent per slot as full frames, deltas and deduplicated frames,
goal-store loads and writes per second, judge passes and their durations
with the CPU each pass cost, the producer's wakes against the waits they
ended, the chain memo's hits and misses, the evidence gate's runs against
skips per judge tier, memory and thread count. `romp perf --json` prints one raw snapshot. If the
kernel restarted between the two snapshots the counters have started over, so
the command says so and exits non-zero instead of printing negative rates; a
refused token is reported as such, not as a dead kernel.

The snapshot's fields, all plain numbers (`ms` is milliseconds of wall time):

- `now`, `since`, `uptime_s`, `log`: the clock, when the counters started,
  seconds since the process started, and whether the `romp-perf` log is on.
- `process`: `rss_kb` (resident set size in KB: the current size on Linux, read
  from `/proc`; the peak, `ru_maxrss`, on macOS, which has no `/proc`), `threads`,
  `cpu_s`, `pid`, and the exact memory gauges:
  `rss_anon_kb` and `hwm_kb` (the anonymous and the peak resident size from
  `/proc/self/status`; null with `source` "unavailable" where `/proc` is
  absent, since `rss_kb` there is a peak from `ru_maxrss` and is never passed
  off as a current figure), `allocated_blocks` (the interpreter's live
  allocations, `sys.getallocatedblocks`), `gc_gen2` (generation-2 collections
  so far) and `malloc` with `arena`, `hblkhd`, `uordblks`, `fordblks` in bytes
  (glibc's `mallinfo2`: the arena size, the bytes in mmap'd blocks, the bytes in
  use and the free bytes the allocator holds; the malloc half of the heap only,
  pymalloc's arenas being invisible to it; null where glibc 2.33 or newer is
  absent). Two snapshots an hour apart answer where resident memory goes:
  blocks flat while rss climbs points at the allocator, blocks climbing at an
  object graph, a `caches` gauge climbing at that cache. `romp perf` prints
  them on a `memory` line with the window's deltas beside the levels.
- `caches`: one block per cache the kernel, the judge and the event model keep,
  each an exact occupancy (a `len()` or a sum of `len()`s under the cache's
  lock; nothing estimated): `jsonl` with `entries`, `file_bytes` and `records`
  (the event model's incremental reader), `asm`, `asm_keylocks` and `trailing`
  (the assembly cache, its per-key locks and the torn-tail memo), `judge_parse`,
  `judge_recon` and `judge_chain` (the judge's per-session parse, reconciliation
  and chain memos), `parse` (the kernel's parsed sessions), `built_chat` with
  `entries` and `ms_bytes` (the cached chat payloads and their materialized
  serializations), `judge_usage` with `rows`, `img` with `entries` and `bytes`
  (the data-URL previews), `path_links`, `space_paths`, `session_stamp`,
  `task_seg` and `session_tok`. `romp perf` prints them on a `caches` line. The
  memos report their own occupancy under `memos`.
- `pusher`: `cycles`, `wakes` (every wake call; a burst of wakes runs one
  cycle), `wakes_live` (the wakes that carried a session id: that session's
  live tail changed), `wakes_event` and `wakes_backstop` (how the cycle came
  to run: a wake arrived before it started, or none did and the 0.5 s backstop
  ran it), `held` and `held_ms` (cycles the minimum interval between cycle
  starts delayed, and the total delay), `exempt` (cycles that ran inside the
  interval because a watched chat tab's live tail changed; a cycle released
  early from a hold counts in both), `cycle_ms_sum`, `cycle_ms_max` (since
  start), `cycle_ms_last`, `cycle_cpu_ms_sum` (the pusher thread's own CPU
  time), `cycle_ms_p50`, `cycle_ms_p90`, `cycle_ms_ring_max`, `ring_n`
  from the last 256 cycles, `sends` (every payload that went to a client; a
  deduped frame the client already holds is not one), and `idle_cycles`,
  `idle_ms_sum`, `idle_cpu_ms_sum` (cycles that set no wake, sent no payload
  and saved no goal store: what a longer wait between cycles would have
  skipped; a conservative undercount, since a wake set by another thread or a
  periodic repost of an unchanged frame marks a cycle busy). The interval is
  1.0 s (`PUSH_MIN_INTERVAL_S` in
  the kernel): a cycle starts no sooner than that after the previous one
  began unless the live tail of a chat tab a connected client is watching
  changed (a Claude Code session's streamed text, an echo, a turn's end, the
  session ending), which runs its cycle at once. A Claude Code (tmux)
  session's mid-turn output has no event: it refreshes on the backstop cycle,
  which runs at the later of the previous cycle's end plus 0.5 s and its start
  plus the interval. `ROMP_PUSH_MIN_INTERVAL=<seconds>` in the kernel's
  environment overrides it; 0 removes the bound.
- `stages_ms`: `jobs` (the cycle's tick jobs outside the push), `push`, and
  inside it `push.chat`, `push.feed`, `push.timeline`, `push.send`. The
  `push.*` stages count every push, including the one a connecting page gets,
  so they can add up to more than `push`.
- `builds`: `chat`, `feed`, `timeline`, each with `cached`, `built`, `ms`; `feed` also carries
  `dirty`, the rebuilds a kernel-side mutation forced past the view signature (a card reply, a
  clear, a follow-up: the mutation is invisible to the signature and must not wait out the
  rebuild interval).
  `chat` also carries `active_built` and `bg_built` (rebuilds of the watched
  tab against rebuilds of a background tab; every tab, the watched one
  included, is served while its complete per-session signature is unchanged
  and rebuilds when a component moved), `bg_miss`, a map from each labelled component of the
  chat-build signature (the kernel's `_CHAT_SIG_LABELS`: the transcript, the
  states files, the goal store and its hold, the archive, episodes, sdk
  registry and death marker, the task and user-todo stores, the pinned notes, the pending cut,
  the working note, the needs-you bit, the live tail's revision, the liveness
  row, the clock booleans, the backend's queue and brackets, the parked ops,
  the limit hold, the retry state, the live task rows, the watches, the
  awaiting-stamp view, the warm-anchor revision, the suspension count, the names digest, the flags
  and bell files, the colormap, the account, cleared.jsonl, the host, the
  cwd-derived rows, the CLAUDE.md chain, the forks, and the three build-time
  dependencies `taskout`, `pathlink` and `postal`; plus `cold` for a tab with
  no cached build and `nosig` for one whose signature could not be taken) to
  the background rebuilds it caused, and `moved`, the builds left uncached
  because their signature changed while they ran (the next cycle rebuilds and
  caches). A rebuild with several moved components counts under each, so the
  map's sum can exceed `bg_built`. `romp perf` prints the split and the
  non-zero causes after the chat average.
- `sends`: `full`, `delta`, `deduped`, each a map from slot name (`chat`,
  `feed`, `bars`, `taborder`, ...) to `count` and `bytes`. A deduplicated frame
  was built and compared, then not sent.
- `goals`: `loads`, `saves`, `writes` on the goal stores through the writer's
  loader (`load_goals`) and `save_goals`; the pusher's read-only loads go
  through the shared store cache and show under `memos.shared`, not here.
  `loads_shared` is the one number this block keeps for those reads: the calls
  the cache answered (a hit, or a version parsed there), so
  `loads + loads_shared` is every store read; the cache's own hit/miss split is
  `memos.shared`. A save that would rewrite identical bytes is a save without
  a write. `scans`, `scan_hits`,
  `scan_parses` count the give-up scan behind the judge-failure notice: calls,
  stores served from its per-store memo, and stores read and parsed (or
  attempted) because they were new, changed, or failed to parse on the
  previous call. `disk_hits`, `disk_misses` and `disk_seeds` count the memo
  behind the no-op save check: the file's identity matched and it was not
  parsed, it was read and parsed (or attempted), or the entry was filled from
  the publish's own write. `absent_hits` and `absent_misses` count the memo
  behind the two triage sweeps over stores no discovered session owns:
  answered from the memo, or loaded and evaluated because the store, its
  override journal or its archive changed or was new. `noop_hash_ms` is the
  time `save_goals` spent serializing a held store for its no-op check (the
  cost a conditional tail save would remove); `romp perf` prints it as a rate
  on the `goals` line so that item can be judged from a measurement.
  `unreadable_stores` is a gauge, not a counter: the goals files currently in
  a fault episode. A read-failure episode is a file that exists and did not
  read; bytes that do not parse are no episode on a read (`load_goals`
  quarantines them aside and answers a fresh store); met by a save's strict
  read they end the publish and stand as a `store-unwritable` episode.
  `load_goals` raises on a read fault, never an empty store; the per-session
  boundary (`load_goals_or_fault`) contains the fault to that session, files
  one `store-unreadable` judge-errors row per episode and skips the session's
  goal-derived work for that build or pass; a judge pass that reaches the
  store outside that boundary files a `pass-crash` row for the session
  instead (the captioner reads through it, so its fault is the
  `store-unreadable` row); nothing is published over the file, and the next
  good read or publish through the boundary ends the episode. A publish that
  failed (`store-unwritable`), on the write or on the save's own read of the
  file, stands in the same table. `romp perf` prints it on the `goals` line
  when it is not zero, and the kernel warns the chat pane once per episode
  for a listed session.
  `lineage_reads` counts `resume_lineage` calls, each a read and parse of one
  session's whole states file: the episode-boundary check consults it only for
  a head the memoized episode log does not hold yet, so at steady state the
  counter stays near zero. A steady non-zero rate has three causes: heads are
  changing (`/clear` boundaries and first observations); a live session's
  current leaf is a recorded resume fork, which is never appended to the
  episode log and so reads its lineage every pass (benign; one read per such
  session per pass); or the guard order in `_episode_boundary_check` regressed.
  `romp perf` prints the rate on the `goals` line.
- `memos`: the identity memos on the goal-store path. `pass` is the
  judge pass's stat-keyed store memo (`hit`, `miss`, `fail`, `evict`, `punch`,
  `live`, `snap`, and its occupancy `entries`, `bytes`); `shared` is the
  pusher's shared read-only store cache (`hit`, `miss`, `compare_miss`,
  `refuse`, `dup`, `absent`, `corrupt`, `unreadable_journal`, `evict`,
  `fallback`, `poisoned`, with `entries`, `bytes` and `off`); `chain` is the
  write-moment chain memo (`hit`, `miss`, `populate`, `bypass`). The compaction
  sweep after each judge pass evicts from `pass` and `shared` the entries of
  stores no session in the discover window owns, so both stay bounded by the
  live board.
  In `pass`, `hit` and `miss` are stores served from memory against decoded,
  summed over passes; `fail` is a file version that did not decode (remembered
  until the file changes) or a read that failed (read again next pass), either
  way out of the snapshot and served live; `evict` counts entries dropped for
  files gone from the directory or for stores no discovered session owns;
  `punch` entries copied so a user gesture could be applied to them; `live` and
  `snap` the feed's store reads served live through the shared cache against
  those served from the pass snapshot; `entries` and `bytes` are the memoized
  files and their summed size. In `shared`, `compare_miss` is an identity that
  matched with bytes that did not; `refuse` a fill under a moving archive,
  served but not published; `dup` a concurrent fill of the same version
  published first; `absent`, `corrupt` and `unreadable_journal` stores handed
  to the writer's loader or served as a fresh store; `evict` entries dropped
  for files gone from the directory or for stores no discovered session owns;
  `fallback` calls served by the writer's loader while the cache is off;
  `poisoned` write attempts on a shared view; `bytes` the raw store bytes held
  for the compare and `off` 1 once a write attempt switched the cache off,
  until the kernel restarts. In `chain`, the memo behind the write-moment
  chain check, which asks before every planner mint whether the prompt sits on
  a rewound-away branch, a hit served a memoized check, a miss built one, a
  populate stored one (a build that failed is a miss with no populate), and a
  bypass built without memoizing because an input file could not be stat'd.
  Five more are the judge's, since the 2026-09-09 fold. `courierSkip` is the
  courier's change gate (`skipped`, `scanned`, `recorded`): a scan that placed
  nothing and left nothing incomplete (an open link repair, a repair that
  raised, a store that did not read) is recorded, and a session whose parse,
  store, journal, archive and episode log have not moved since such a scan is
  skipped whole; a raise inside one session's scan is that session's
  `pass-crash` row, not the pass's.
  `plannerSkip` is the planner's inner change gate (`skipped`,
  `planned`, `recorded`). The planner runs behind two gates. The outer gate is
  the judge's evidence gate around `_plan_session` (`docs/judges.md`, "Ops and
  knobs"): a session whose signature equals the one the planner stamped after
  its last complete run is skipped before it is submitted. It keys on the
  inner gate's inputs, the reg by its `spawnedAt` and backend values rather
  than by identity, plus `cleared.jsonl`, the death marker and the session's
  stall records. The inner gate
  sits inside `_plan_session` and sees only the sessions the outer gate ran: a
  session whose parse, store, journal, archive, episode log, its leaf's task
  store, captions file and reg have not moved since a pass that had nothing to
  do, and none of whose running background launches has crossed its deadline,
  is not planned again. The inner key
  carries `cleared.jsonl`, the death marker and the stall slice too (this
  fork's three terms beyond upstream's key), so an input only the outer gate
  would key re-arms both gates and an outer re-arm is never swallowed by an
  inner skip. The inner gate records a pass only when it placed
  nothing, left the store's key where it was, and ran to completion; a
  deferral without a write, or a side file that exists and did not read,
  marks the run incomplete, and that session is planned again next pass. So
  `plannerSkip` counts the sessions the outer gate let through, not every
  planner skip: an idle session stops at the outer gate and appears in neither
  `skipped` nor `planned`. Outside a pass frame (`romp-judge --plan`) the
  outer gate stamps nothing, and the inner gate does the skipping.
  `backref` is the
  sender-board walk behind the courier's link repair, built once per state of
  the sender stores and served while they stand (`served`, `built`; a sender
  store that does not read is skipped, not every recipient). `captions` and
  `goalArchive` are the per-file read memos behind the index tier's caption
  readers and the re-plan's cleared context, each parsed once per file state
  (`served`, `parsed` or `loaded`). `captions` keeps the index tier's
  strictness: an absent captions file is empty and never cached; an existing
  file that fails to read answers nothing to the index bodies (the stage is
  marked incomplete and one `captions-unreadable` row is written per episode)
  and is never cached either. `goalArchive` never holds a record that did not
  read (the `_unread` shape): an archive that exists and cannot be read or
  parsed is answered as that marked empty shape, marks the running judge
  stage incomplete, and is read again next time. The courier's and the
  planner's change-gate tables are pruned to the sessions each pass
  discovers, and the evidence gate's stamps are cleared at a fixed cap.
  The rest are the kernel's own memos, each a flat map of counters. `lift_gate` is
  the awaiting-lift job's per-session identity gate: `skip` and `load`
  (session-cycles that took no store read against the ones that read it, a
  probe on the shared read-only view), `shared` (probes the shared cache
  answered), `writer` (session-ticks that loaded the writer's copy because a
  lift was due) and `noop`
  (writer loads whose fresh decision filed nothing, the store having moved
  between the probe and the load), and the gauge `entries` (sessions
  remembered). `bg_tops` is the placed-launch memo behind that lift and the
  feed's background-task classification, keyed on the parse object and the
  store object: `hit` and `miss` (calls answered from the per-version map
  against looked up), `resolve` (launch ids looked up on a miss, placed or
  not), `walk` and `walk_neg` (transcript walks, and the walks that left a
  launch unresolved: an upper bound on what a negative walk cache would
  save), `idx_build` (placement indexes built, one per store object asked, a
  writer's private copy included) and the gauge `entries` (sessions holding a
  map). `nudge_walk` is the auto-nudge walk's per-cycle cost (it runs
  for every alive session every cycle, wake-only when the toggle is off):
  `walked` and `gated` (session-cycles visited, and the ones a session gate
  returned on), `loads` and `shared` (store reads taken for the decision, and
  the ones the shared read-only cache answered), `deleg_hit` and `deleg_miss`
  (the delegated-work check served from its own memo, keyed on the shared
  view's identity, or computed), `lifted` (lifts the wake-only dead-man
  filed), `evict` (sessions that left the alive set, whose entries were
  dropped from the placement-gate memo and the delegation memo) and the gauge
  `entries` (sessions holding a placement-gate entry). `nudgeGate` is that
  walk's planner-placement gate (upstream's memo since the 2026-09-09 fold; it
  replaced this fork's own gate memo and the walk's counters for it): the
  answer is derived once per (parse, shared view, episodes log, `cleared.jsonl`
  state) and served while all four stand (`served`, `derived`; a healthy quiet
  box serves almost every cycle). A parse the cache does not hold or a store
  that is not the current shared view is derived every cycle and never
  memoized, a failed derivation caches nothing, and the memo is bounded by the
  alive set (the walk evicts the sessions that left it) and a 512-entry cap.
  `cleared` is the feed's clear set, parsed once per state of `cleared.jsonl`
  (its stat, taken before the read) and served while the file stands
  (`served`, `derived`).
  `wire` is the pusher's per-build wire caches: `feed_cards_hit` and
  `feed_cards_miss` (the per-card encode served from its memo against run),
  `feed_body` and `bars_body` (whole frames serialized, at most once per build
  each), `bars_sig_fallback` (bars builds that could not be keyed and took the
  whole dump for their signature), and `default_str` (values no wire encoder
  could serialize as JSON and shipped as `str()`, one per encode; the kernel's
  stderr names each such type once).
  `intr_marks` is the interrupt-marks memo, one entry per (session, parse
  family) keyed on the parse object's identity and the machine-cut stamp:
  `hit` and `miss` (reads served from memory against re-tallied), `evict`
  (entries dropped for sessions that left the alive set, or the whole memo
  cleared once it holds 512 entries), and the gauge `entries`.
  `sessions_scope` is the pusher cycle's discover memo, one sweep per
  (window, forks) key per cycle: `hit` and `miss` (session-row reads inside a
  cycle served from the cycle's rows against swept) and `wide_hit` and
  `wide_miss` (the wide walk taken for a live session idle longer than the
  caption window); the memo lives for one cycle, so it has no occupancy gauge.
  `caps` is the memo behind the captioner-store reader every timeline lane,
  the feed's held card and the postal join read (named `captions` until the
  2026-09-09 fold, when the judge's file-read memo of that name arrived), keyed
  on the file's identity (inode, mtime, size) taken before the read: `hit`
  and `miss` (reads served from memory against read and parsed), `fail` (a
  read that did not succeed on a file that exists, after a stat that succeeded
  or one that failed other than for a file that cannot exist, no such file or
  a name too long for the filesystem; nothing is memoized, and the kernel's
  stderr names the file once per episode, with the stat's error when the stat
  failed), `evict` (entries dropped: a lane that left the timeline, the
  512-entry bound, or the pop of an entry whose file is now absent), and the
  gauge `entries`. `states_overlay` is the states-log fold behind the
  awaiting overlay: `hit` (the records were the cached ones), `append` (only
  the appended rows were folded), `refold` (every row was folded: a rewrite, a
  shrink, or the file's first fold), `fail` (a read that failed on a file that
  exists; the fold answered no overlay, memoized nothing, and the kernel's
  stderr names the file once per episode), `evict` (entries dropped for
  sessions that left the alive set), and `entries`. `thread_reg` is the SDK
  registry reader's memo, keyed like `caps`, with the same `hit`, `miss`,
  `fail` and `entries` (its `fail` counts a read that did not succeed, as the
  caps memo's does, and also a body that is not JSON or not a JSON object,
  answered as a failed read and not memoized; its stderr line names the
  stat's error when the stat failed too); its `evict` counts the 512-entry
  bound and the pop of an absent file's entry.
  `feed_segs` is the feed build's per-session memo of the values that are pure
  functions of a session's parse and goal store (the seam maps, the tree shape
  and each top goal's flattened tree), keyed on the parse object, the served
  store's identity, the names registry, the working bit and the session row's
  name and colour: `hit` and `miss` (sessions served from the memo against
  recomputed and stored), `bypass_live` (a build whose parse was a live-merge
  copy: computed for that build only), `bypass_degraded` (a walk that swallowed
  an exception: computed, never stored), `bypass_unkeyed` (a store whose
  identity does not stand for its content: a rewind hold, a failed gesture
  replay, the shared cache switched off, no store file), `bypass_unscoped` (a
  build outside a pusher cycle: read but never filled), `evict` (entries dropped
  for sessions that left the alive set), and the gauge `entries`. `lanes` is the
  per-lane segment memo in the timeline build: a lane's bars, segment ends,
  last activity, compaction markers and judging marks, held while the lane's
  parsed transcript, goal store and captions are the same objects as the
  previous build's and its other inputs (live, the branch clip, the host's
  suspensions, the archive file) are unchanged. One outcome per lane per bars
  build (a full build, or the live-only first paint): `hit` (served), `miss`
  (derived, and held unless the archive file could not be stat'ed),
  `live_tail` (a live tail was merged, so the lane was derived and not held),
  `complain_skip` (the parse or a stage failed, or a mark carries a time the
  horizon cannot compare) and `unshared_skip` (a private store with content;
  derived and not held); `evict` (entries dropped for lanes that left a full
  build's lane set or past the 256-entry bound), the gauge `entries`, and
  `segs_hit` and `segs_miss`, the segments served against derived, which
  weight the hit rate by cost. Since the 2026-09-09 fold those counters read the live lanes alone: a dead lane is
  the timeline's dead-lane memo's, and its outcomes ride the same block as `dead_serve`
  (served from that memo), `dead_miss` (derived, and cached unless its store faulted or a
  stage complained) and `dead_failed_serve` (served as the empty lane a failed parse was
  cached as, until the transcript's stat moves).
  `chat_merge_sets` is the live-tail merge's memo of the sets it derives from
  a parsed transcript (the uuids and user texts the transcript already holds,
  and the newest human turn's time), one entry per session keyed on the
  parsed session object's identity, shared by the chat, feed and timeline
  builds of one cycle: `hit` and `miss` (merges served from the memo against
  derived) and the gauge `entries` (sessions held; the pusher drops a session
  that is neither shown as a tab nor alive).
  `chat_postal` is the chat fold's memo of a tab's sealed postal cards, keyed
  on the values the cards embed from outside the transcript (the message log's
  identity and, per card, its caption and its peer's name and colour): `gate`
  (fold-gate checks that re-hydrated a tab's sealed cards because one of those
  values moved, or because the entry was sealed outside the pusher's names
  snapshot and had to be verified), `hit` (checks that verified the sealed
  cards from their recorded values without hydrating), and `commit_new` (raw
  postal events hydrated at fold commits: the events a folding build newly
  seals, or every relevant event of the prefix a demoted build rebuilds, so a
  demotion counts its rebuilt tail again; the sealed cards a folding build
  reuses are not counted). Before this memo every judge pass re-hydrated every tab's
  sealed cards, although a caption is the only judge-written value a card
  carries.
  `chat_ledger` is the chat build's memo of a session's goal-tree walk and
  live roots (interim: the round-4 plan expects P4's complete chat signature
  to remove most of the rebuilds it serves), keyed on the parsed transcript's
  identity, the store's identity and seams, `cleared.jsonl`'s identity and
  the warm-anchor table's per-session revision: `hit` and `miss`,
  `bypass_live` (a build that merged live atoms: the last turn's segments
  differ from the parse's), `bypass_hold` (an armed rewind hold filters a
  store copy per build), `bypass_empty` (a store with no nodes), `evict`
  (entries dropped for tabs no longer shown) and the gauge `entries`.
  `chat_fold_tasks` is the per-turn memo of the transcript's task fold
  (interim, the same reason). It serves repeated builds over one parse: a
  live-merged build of an unchanged transcript scans its last turn only. A
  build after a transcript write scans every turn again, since a parse mints
  new atom lists. `hit` and `miss` count turns served from the memo against
  turns scanned, plus the gauge `entries` (sessions held).
- `judge`: `passes`, `ms_sum`, `ms_last`, `ms_mean` (wall time; a pass waits
  on model calls), `cpu_ms_sum` (CPU time of the judge tier threads and every
  per-session worker they run; the workers' share is `cpu_ms_workers`; the
  producer thread's own per-pass work is not included and shows under the
  process line's "other"), `wakes` (every wake of the producer: the backends'
  pokes, `POST /tick`, and two kernel-internal sites; one SDK turn fires
  several, so this is an upper bound on the poke rate), `wakes_event` and
  `wakes_backstop` (how the producer's 3 s wait ended; `wakes - wakes_event`
  is the number of wakes a pass absorbed; the write-moment chain memo's
  counters are under `memos.chain`, not here). `tiers` holds
  the evidence gate's counters per gated tier (`plan`, `close`, `unblock`,
  `group`, `consolidate`, `distill`, and `index`, the captioner and archiver;
  there is no `courier` row, the courier running on its own change gate,
  `memos.courierSkip`; the `plan` row counts the planner's outer gate, and
  `memos.plannerSkip` its inner one over the sessions the outer gate let
  through): `ran` (per-session stage
  runs), `skipped` (runs the gate declined because nothing the tier reads had
  changed), `stamped` (runs that ended complete and recorded what they
  judged), `bypassed` (runs with no signature to record, or whose parse ran
  under a cut that moved after the gate looked), `incomplete` (runs a
  deferral or a failed call left unfinished; for the index tier, sessions
  that had a caption or an
  archive to write this pass, or whose captions file, archive record or unit
  cache exists and did not read, or whose unit-cache publish failed; the
  read and publish failures each write one `judge-errors.jsonl` row per
  failure episode, `captions-unreadable`, `session-archive-unreadable`,
  `units-cache-unreadable` or `units-cache-write-failed`, beside the
  `store-unreadable` row a goals file that does not read writes, and the
  session runs again every pass until the file reads; an archive record that
  reads but is not one is content, so the archiver rebuilds it, with the row
  still written once), `due_clock` (runs a
  background task's deadline made due), plus `stamps`, the number of
  per-session records held. The index tier's signature is the session's
  parse pair, captions file, archive record and unit cache, and no goal
  store: its idle path reads none.
  `skipped / (ran + skipped)` is the share of per-session runs the gate saved;
  `romp perf` prints it per tier on the `tiers` line and adds `cpu/pass` to
  the `judge` line, since the judge's CPU share alone cannot tell a cheaper
  pass from a faster cadence.
- `http`: request `count` and `ms` per `METHOD /path` for GET, POST, HEAD and
  OPTIONS, the query string removed and `/dist/*`, `/media/*` and
  `/remote/*/…` collapsed to one key each, for at most 256 keys; further keys
  fold into `other`. A WebSocket upgrade is counted when it arrives and not
  timed, since its handler runs for the life of the socket.

`POST /perf` with the body `{"log": true}` or `{"log": false}` turns the
`romp-perf` stderr log on or off in the running kernel (`romp perf log on|off`).
The log prints one line per chat build and per frame sent or deduplicated. It
goes where the manager's stderr goes: under systemd, `journalctl --user -u
romp-manager -f | grep romp-perf`; under launchd (macOS), `tail -f
~/.local/state/romp/manager.log | grep romp-perf`. Setting `ROMP_PERF=1` in the
kernel's environment still turns it on at start.

These counters describe the kernel process only. `tools/ui-bench.mjs` measures
the browser's side: it replays a recorded or synthetic frame stream into a
headless Chromium and reports per frame the shim's handler time, the time the
bundle spent on the frame (the shim's handoff to it, whether made inside the
socket handler or from a queued flush task) and the time until the main thread
is free again, plus long animation frames, JavaScript heap, and DOM size, and
with `--cpu-profile` the functions inside the bundles that took the time. See
"Measuring dashboard pane performance" in `CONTRIBUTING.md`.

## Browser-side performance telemetry

The counters above say what the kernel spent. What the browser spent on the
frames it received is measured in the panes themselves, by
`ui/webview/perf-telemetry.ts`:

- The feed, Outline, Waiting on you and chat bundles wrap their window
  `message` handler, so each frame's synchronous handling time is recorded by
  frame type: the frame's `type` string as it is (`feed`, `chatTail`, `session`,
  `tabOrder`, `bars`, or any other type that is a short identifier: letters,
  digits, `_ . : -`, at most 32 characters), a raw delta as `delta:<slot>`
  (`delta:other` when the slot is not such an identifier), a shell message (a
  `romp` field and no `type`) as `shell`, and `other` for a frame with neither,
  a `type` that is not a short identifier, or any type past the 32 distinct
  types a minute the pane tracks; frames the handler ignores count too. The
  federation layer, which every kernel page loads, times its own prefixing,
  delta application and merge of each frame as `fed:<type>`, nested outside the
  pane's handler; each level records its own time, so `fed:feed` and `feed` add
  up to the frame's cost.
  The federation layer hands its merged frames (`feed`, `tabOrder`, `data`,
  `bars`) to the pane's handler by direct call once the pane has registered it
  (`window.__rompFed.onFrame`, through `ui/webview/frame-listener.ts`), so
  `fed:<type>` is that layer's own compute; it dispatches them on `window` only
  when nothing registered, and every other frame still arrives as a `window`
  `message` event. A `message` listener from another JavaScript world (a
  browser extension's content script) that reads `event.data` receives a
  structured clone of every frame dispatched on `window`, tens of milliseconds
  for a multi-megabyte board; the direct call keeps the merged frames out of
  its reach. See "A message listener from another world" in `CONTRIBUTING.md`
  for the check that finds such a listener.
  The timeline's listener is wrapped the same way on both hosts (the VS Code
  bundle directly; the kernel page's inline boot through the `window.__rompPerf`
  that `federation.js` publishes before it runs), so `data`, `bars`, `hover`,
  `activeChat`, `revealEvent` and `models` are timed like any pane's frames.
  The Files pane receives no frames; its collector times the viewer's own paint
  pass instead, as `fileview:paint` (a text body painted) and `fileview:reflow`
  (the comments panel's re-place of its cards over reflowed text: the body's
  width changed, or a text-size step), so the cost of a large reviewed file
  shows per minute under app `files`; the pane's socket replies (`fileSaved`,
  `fileGitLink`) count under `fed:<type>` as on every pane.
  The dashboard shell (the top-level window that frames the panes) runs the
  same collector under app `shell` with no frame types at all: Chromium reports
  an iframe's long animation frames to the top-level window only, so a pane
  script that blocked the main thread is attributed there (`files.js:paintAll@9000`)
  and the shell's row is where it lands; the row goes over the shell's own
  socket, and up to twenty rows are held while that socket is closed.
- Per type and minute: count, summed and maximum handler time, the exact
  number of frames over 16.7 ms (one dropped frame at 60 Hz) and at or over
  100 ms, and a 14-bucket log2 histogram (under 1 ms, 1-2, 2-4, ..., 2048-4096,
  4096 and over) that is additive across minutes, so `romp perf client`
  computes window percentiles from it.
- Two `requestAnimationFrame` callbacks after the outermost handler it records
  how long the main thread stayed busy with the work the handler queued (a
  deferred render, layout, paint). A hidden document or a pane the shell has
  set to `display:none` takes no sample, and a sample armed before such a hide
  is cancelled (on `visibilitychange`, or on the `resize` that takes the
  pane's viewport to zero).
- A `PerformanceObserver` on `long-animation-frame` entries (Chrome 123+;
  `longtask` where that is missing, with no attribution) records each frame
  over 50 ms with its blocking time and the scripts the browser attributes it
  to. The browser names the top-level callback it invoked, not the hottest
  function, so a key is `<file>:<function>@<character position>`
  (`feed.js:render@1200`, `feed.js:(anonymous)@48213`), and an inline page
  script (the pane shim, whose socket callback runs for every frame) is
  `page:<function>@<position>`. The release build keeps identifiers, which
  keeps the function name in a key readable across rebuilds (the position
  still moves with any edit to the bundle); whitespace and syntax are still
  minified.
- Once a minute the pane posts ONE `clientDiag` row on the socket it already
  uses for breadcrumbs, only when something happened that minute (a frame
  arrived or a long frame was observed); the kernel appends it to
  `client-diag.jsonl` under the state directory with the dashboard id (`wid`)
  and its own clock. A frame whose whole synchronous handling ran 100 ms or
  more also posts a `slowframe` row at once, carrying the long-frame
  attribution when the browser reports one for that frame; at most five such
  rows a minute per pane, the rest counted in the minute row.
- The kernel rotates `client-diag.jsonl` once it reaches 8 MB: the file
  becomes `client-diag.jsonl.1` (replacing the previous one) and a new file
  starts, so at most two files, about 16 MB, are kept. A minute row is about
  1 KB, so one open dashboard writes a few MB a day.

Rows carry numbers and code identifiers only, never card text, session names,
file paths or transcript content: an element id inside an invoker name is
stripped (`DIV#tab-web.onclick` is recorded as `DIV.onclick`), an element
source as `[src]`, and a script URL as its basename.

The two rows, as the kernel writes them (`t` its clock, `wid` the dashboard id):

- `{"t", "wid", "surface": "perf", "what": "minute", "data": {app, since,
  span_ms, frames: {<type>: {n, ms_sum, ms_max, n16, n100, hist}}, free: {n,
  p50, p90, max} | null, loaf: {n, blocking_ms, worst_ms, top: [{k, ms, n,
  inv}], src}, slow: {sent, suppressed, suppressed_worst_ms}, heap_mb?, dom,
  visible, hidden_pane, ua}}`. `app` is the pane (`chat`, `feed`, `fleet`,
  `waiting`, `timeline`, `files`) or `shell` for the top-level window; `since` is the minute's start on the browser's clock
  (epoch ms) and `span_ms` its length (shorter than a minute when the page was
  hidden or closed); `hist` is the 14 bucket counts; `free` is null when no
  sample was taken; `loaf.top` is the five largest keys by summed duration,
  `inv` the last invoker seen for each (`WebSocket.onmessage`,
  `Window.requestAnimationFrame`, `DIV.onclick`), `src` is `loaf`, `longtask`
  or `none`; `slow` counts the slowframe rows sent and the slow frames past
  the cap, with the worst of those; `heap_mb` is
  `performance.memory.usedJSHeapSize` and is absent outside Chrome; `dom` is
  the element count; `visible` is the document's visibility, `hidden_pane`
  the zero-viewport test the pane shim uses for a pane the shell has set to
  `display:none`; `ua` is `chrome-desktop`, `safari-ios` or `other`.
- `{"t", "wid", "surface": "perf", "what": "slowframe", "data": {app, type, ms,
  dom, loaf?: {ms, blocking_ms, top: [{k, ms, inv}]}}}`. `type` is the frame
  as received on the wire and `ms` its whole synchronous handling, the
  federation layer included.

`romp perf client [--minutes <n>] [--json]` reads the file and its `.1`
predecessor (no kernel round trip, so it works with the kernel down) and folds
the last `<n>` minutes (default 10) per dashboard id and pane into one screen:
the pane's total handler milliseconds per minute, then each frame type sorted
by its share, with frames per minute, milliseconds per minute, p50/p90/p99 as
histogram bucket upper bounds over the whole window, the maximum, and the
share of frames over 16.7 ms and at or over 100 ms; the worst minute's
main-thread-free p90 (each minute row's p90 is over that minute's samples, and
the screen shows the largest, so it is not a window percentile like the handler
columns); long frames and blocking milliseconds per minute with the worst
entry; the top attributed keys with their invokers; the worst minute (the one
with the most handler time: its span from the minute's start to the row's
arrival at the kernel, frame counts and long frames); heap and DOM at the last
sample; and the five slowest slow frames in the window with their attribution,
plus how many more there were. An absent file or one without perf rows is
reported as no browser telemetry yet (the bundles predate it or no dashboard
has loaded them: rebuild the bundles and reload the dashboard); perf rows all
older than the window are reported with their age. `--json` prints the folded
panes, with a per-minute array (`t`, `since`, `total_ms`, `loaf_n`,
`blocking_ms`) so a spike is visible without re-reading the file.

In DevTools, `window.__rompPerf.snapshot()` in a pane's frame is the minute
in progress in the same shape, plus a derived `p90_le` per type, `active`
(whether it will be sent), `observer` (`loaf`, `longtask`, `none`),
`pending_slow` (slow frames waiting for their long-frame report) and
`free_pending` (a main-thread sample armed). A page without `performance.now`
(the node test stand-ins) gets no telemetry and an unwrapped handler; every
other browser API is behind a feature check, and nothing in the module throws
into the pane.

## The API-health signal

`GET /api-health` returns one JSON document describing how the API is treating
the sessions this kernel runs. It is computed from frames the kernel already
parses: the per-attempt retry frame, each successful response, and the settle
of a turn the CLI gave up on. The route takes the serve token, like every read
that is more than a bare counter; `romp api-health` prints the document. The
kernel takes no action on it: a consumer reads the signal and applies its own
policy (move traffic to another key, hold a batch).

Events are bucketed by **auth-source label** and **model family**
(`"<auth>|<family>"`, for example `key:helper|fable`), because rate
limits are per model family per account: pooled, one family's storm disappears
under another family's clean traffic. The auth label comes from the
`apiKeySource` the CLI reports at init. A key is labelled by its source word,
never by its material, since the kernel holds no key: `key:helper` for a key
the helper supplied, `key:env` for one the CLI found in its own environment,
`key:managed` for a managed login key, and `key:<source>` for any other source
word the CLI enumerates, lowercased. Two accounts behind one helper are one
bucket. A login is labelled by a salted digest of the account digest the usage
bars stamp, so the same login gives the same label within one install, and
nothing about the credential itself is in any label. The salt lives at
`STATE/api-health-salt`, minted once at 0600; an empty file makes a login's
label the account digest itself, so a bucket can be matched to the log.

### Top-level fields

- `schema`: `1`, incremented on any incompatible change.
- `asOf`: wall-clock epoch seconds at which this response was computed from the
  event ring. Every window and every state is computed at read time, so `asOf`
  is the response time. A clock step moves it; a reader that wants a freshness
  check a clock step cannot fake uses `seq`.
- `bootId`, `bootAt`, `uptimeS`: the kernel process identity, the same id
  `/version` and `X-Romp-Boot` carry. `bootAt` is the boot's stamp in this
  signal: the kernel's start truncated to the millisecond, the precision of
  every other stamp in the payload, or, when the previous kernel's last
  transition overlaps the start, one millisecond past that row; every bucket
  the boot seeded carries this same number as its `stateSince`, and so does
  every row the boot filed. `/version`'s `started` is the whole-second boot
  time. A changed `bootId` means a restart, and the windows restarted with it.
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
- `cliScope`: scope bookkeeping carried on this payload, not part of the API
  signal itself: the per-session scopes (see "What survives a restart" and
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
    line at the kernel's start; and `OOMPolicy` when this systemd refused the
    policy on a scope. When the deciding failure named the policy (a systemd
    before 253) it is a plain line (the machine's systemd version, not a setting)
    and any memory limits, probed once more without the policy, were taken and
    stand, or could not be settled (then in `unsettled` as `memoryLimits`). When
    the deciding failure did NOT name the policy, the memory limits are what was
    refused and join this list, and the policy is probed alone: if it stands it is
    kept off this list (`oomPolicy` reads `continue`); if it too is refused it
    joins this list, the one line quoting both refusals a problem; if that probe
    cannot be settled the policy is `unsettled` instead. A problem otherwise.
  - `oomPolicy`, the OOM policy every session scope carries: `"continue"`, or
    `null` when this systemd refused it or the scopes are off. With `continue`
    an OOM kill inside a scope ends that process alone; under systemd's default
    `stop` it ended the whole scope, the CLI and its background tasks included.
  - `memoryControllerDelegated`, the kernel's start-time check of whether a
    probe scope carrying the memory properties had a `memory.max` file in its
    cgroup: `true`, `false` (systemd holds the sizes above and applies nothing;
    also a problem line), or `null` when no memory limit is set, the scopes are
    off, or the check could not be settled. A `null` beside a memory limit shown,
    with `on: true`, is that last case: a check at the kernel's start did not
    answer, and `unsettled` says which.
  - `unsettled`, the names of the kernel's start-time checks that were due and
    settled nothing: `memoryLimits` (the probe scope carrying the memory
    properties did not answer, or failed both with and without them; or, with
    the policy refused, the probe with the limits alone did not answer),
    `oomPolicy` (the same probe, which carries the policy too, so the two are
    named together when a limit is set and the probe settles nothing; or alone,
    when the memory limits were refused and the policy, probed by itself, did
    not answer or failed without naming it, the limits then in `rejected`; or
    alone when no limit is set, the probe then carrying the policy by itself,
    and it did not answer or failed both with and without it, `rejected` then
    empty),
    `memoryController` (the check inside it
    gave no marker), `oomScoreAdj` (the throwaway child's write did not answer).
    Empty when every due check answered, and when none was due (the scopes
    off). A value listed above whose check is named here is set and handed to
    the wrapper as read, and whether it applies is not known at the kernel's
    start; the other fields cannot show this (`oomScoreAdj` present, `rejected`
    empty and `memoryControllerDelegated` `true` read the same whether the
    adjustment's check answered or not). Each named check is also a line in the
    boot log saying why.
  - `limitsIgnored`, wrapper `romp-cli-scope: ignored: …` lines since boot (each
    also a problem line, `cli scope: session <name> (<sid8>) started its CLI
    without one of its scope's settings: <line>`). It counts lines, not
    launches: one launch writes one line for each value the wrapper refuses,
    one for the scope properties together (the memory limits and the OOM policy)
    when systemd rejects them, and one for an adjustment it could not write.
    `on: true` with a limit set and
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
file knows comes back `unknown` with `stateSince` at the boot's stamp. For each
bucket whose persisted state was not already `unknown` the reload files
`<state> -> unknown` at that stamp, so the transitions list is continuous across
the restart, and the first read with enough evidence records `unknown -> <state>`
after it. The boot's stamp is the kernel's start truncated to the millisecond,
or one millisecond past the newest transition the file carries when that one
is not before the start (the previous kernel filed it after this one started,
or the clock stepped), so the restart row is always the newest row; the payload
serves that stamp as `bootAt`, and the kernel log says when it was moved. The
pre-restart state is not carried over: an empty ring is no
evidence. A state file, or an entry in it, that cannot be read is skipped and
logged, and never keeps the Claude Code backend from starting.

Earlier builds appended one row per transition to `STATE/api-health.jsonl`. A
kernel that boots without a state file seeds one from that ledger's last 64 KB,
once, and leaves the ledger alone; once the state file exists the ledger is
never read again and can be deleted.

### The bottom bar's indicator

The dashboard's bottom bar carries an API cell (a dot and a word beside the
spend figures) that is computed independently of this signal, from two things
the kernel owns directly:

- Each alive session's newest transcript API-error record, latched until the
  session produces assistant output again (a user prompt does not clear it,
  romp's own retry included), plus the live retrying state of Claude Code
  sessions.
- The retry-pause file (`retry-paused.json` under the state directory). A
  pause writes `paused`, `t` (when it began, the auto-resume floor) and its
  `reason`: `limit`, `spend`, or none for a manual stop. A spend pause adds
  `bills`, the billing the capped session was on (`login` or `key`); only
  fresh assistant output from a session on that billing lifts it. Un-pausing
  a spend pause, by that lift or by the Resume button, records `liftedAt`
  (the time of the output record that lifted it, or of the Resume click) and
  `supersedes` (the floor of the pause it cleared; informational, nothing
  reads it); both ride every later write until a newer spend un-pause
  replaces them, and a spend-limit record older than `liftedAt` engages
  nothing, since the lift already ruled on it. A limit or manual un-pause
  records neither. When a limit pause lifts while a spend-limit record is
  standing, the file reads unpaused for one cycle before the spend pause
  engages: each writer rules on one signal per cycle, and the spend engage
  runs before the lift in the pusher's order, so it sees a paused file and
  rules on the record the next cycle.

The kernel pushes the cell's frame to shell clients only when it changed, and
again to a shell that sends `ready`:

```json
{"type": "apiHealth", "state": "ok | degraded | paused",
 "cls": "429 | 529 | offline | errors | ''", "reason": "'' | limit | spend | manual",
 "text": "<the rail's words>", "waiting": 0, "retrying": 0, "blocked": 0,
 "since": 0, "tmux": 0, "seq": 0,
 "sessions": [{"sid": "", "name": "", "color": null, "kind": "retrying | blocked",
               "cls": "", "status": null, "since": 0, "suppressed": false}]}
```

`seq` counts the retry-pause file's writes since the kernel started. A press
on the detail's pause button writes that file, so the frame that answers the
press carries a moved `seq` whatever state it brings, and the shell clears
the button's acknowledgment on it; a frame from before the press carries the
old one. It is an event counter, not a clock, and restarts at 0 with the
kernel. `waiting` is `retrying` plus `blocked`. `cls` is the plurality class over the
affected sessions, ties resolved 429, then 529, then offline, then errors.
`since` is the pause's time when paused, else the earliest affected session's
event (a record's timestamp, or the retrying turn's start), else 0. `tmux`
counts alive Claude Code (tmux) sessions, which the cell sees through their
transcripts only. Every timestamp is an event's time, never the clock, so an
unchanged world sends nothing. On-you failures (a too-long prompt, a spent
model allowance, a dead credential, a refusal) are not counted; a spend cap is,
and engages the `spend` pause in the same cycle.

The cell's hover and its click detail carry a **History** section read from
this signal: the shell fetches `GET /api-health` when the hover or the detail
opens, and again when a frame lands on an open one, authenticating with the
dashboard's own cookie the way its other reads do. Nothing polls; the frame
carries no history and is unchanged. The section shows `overall.state` with
the worst bucket's `stateSince` and `why` (naming the bucket and the bucket
count when there is more than one; a bucket the boot seeded is `unknown`
since `bootAt`: the boot time or, when an older kernel's last row overlaps
it, one millisecond past that row, because the backend seeds its `stateSince`
with the stamp it serves as `bootAt`, the one the tail uses for the boot),
one row per window from `config.windows` (`requests` plus `noStatus` as the
attempts, saying how many of them had no status when there are any, `rate429`
and `rate5xx` as percentages over the attempts with a status, `gaveUp`, and
`sessionsRetrying` as the sessions that retried in the window; a window
reads `no attempts` only when every one of those is zero; a window whose
`complete` is false says how long the kernel has been up), up to six rows
of `transitions` newest first with the state entered and how long it held
(until the same bucket's next transition, `so far` for the current one; a
hold from before `bootAt` ends at the boot, since every bucket comes back
`unknown` at a restart), and the payload's `asOf`. A row the boot filed
(`<state> -> unknown`, its `why` the restart reason) reads `kernel
restarted`; where the tail crosses `bootAt` without such a row (the bucket
was already `unknown` when the previous kernel stopped, so the boot filed
nothing), a `kernel restarted` divider is inserted, and it takes none of the
six slots. A read that fails (a non-2xx, or no answer) shows one line saying
so in place of the rows, never the previous numbers.

## Where things live

State is written under `${XDG_STATE_HOME:-~/.local/state}/romp/`. Transcripts
are read in place from where Claude Code writes them (`~/.claude/projects/`)
and never copied.

The self-updater's report, `update-report.json`, is read once, by the next
kernel boot or by the running kernel's banner poll, and archived as
`update-report-last.json`; `update.log` beside it has the updater's full
output. An update that landed on disk but was not restarted into (no manager,
or a manager that did not take the restart request or did not answer it within
60 seconds) is filed in the Log with the step that runs it: `romp refresh` when
a manager is there, `romp up` when none is. A boot that already runs the landed
release says so instead of asking for another restart. A report that is not a
JSON object is moved aside, never deleted, to
`update-report.json.corrupt-<UTC stamp>` (the same `-1`, `-2` suffix rule) with
one Log entry under the `refused` kind; one that cannot be moved stays where it
is and is said once per fault.

Three small files there hold settings you set by hand: `session-flags.json`
(per-session flags, the postal isolation switch among them), `session-order.json`
(the saved tab and lane order) and `notify-cards.json` (the bell overrides). A
change to one of them is refused, never written over an empty, when the file
exists but cannot be read; the refusal reaches the dashboard's error center
under the `refused` kind, with the reason, and the same change can be tried
again. A file whose bytes cannot be parsed (a torn write) is moved aside, never
deleted, to `<file>.corrupt-<UTC stamp>` in the same directory (a `-1`, `-2`
suffix when two land in the same second), the store starts over empty, and an
entry under the same kind says so. A file that cannot be read at all keeps
showing its last-read values until it can. Nothing here needs a restart; the
sidecars are yours to inspect or delete.

Two small ledgers there, `auto-nudge.json` (the auto-nudge switch and its
per-goal records) and `retry-suppressed.json` (the sessions whose auto-retry
you stopped), are moved aside rather than overwritten when their bytes do not
parse: the file is renamed `<name>.corrupt-<UTC stamp>` beside the original
(`-1`, `-2`, ... when a second one lands in the same second), the dashboard's
error center says so, and the ledger reads as a fresh install until you
restore it from that file. Nothing is deleted. Any other read fault leaves the
file untouched: the kernel serves the last copy it read, writes nothing to it,
and says so once, until the file reads again. A write that fails (a full or
read-only disk) is told to the gesture that asked, the gear's toast or the
stop button's warning, and said once per fault episode in the error center;
the automatic pass sends nothing whose record could not land, and the file
keeps what it holds.

Two ledgers there record restarts. `restart-audit.jsonl` gets a row from
whatever asks for one: `romp refresh`, `romp down`, the dashboard's restart
button, the kernel's own update, and the manager before each SIGTERM it sends
(action `manager-sigterm`, with a `trigger` naming what set it off: `restart`,
`restart-all`, `refresh` for the stale-manager self-bounce, `cli-down` for a
stop while `romp down`'s marker is on disk, `stop` for any other). When a
SIGTERM arrives, the kernel reads the last eight rows, newest first, for a
request within the last 90 seconds (20 minutes for a request that asked to
wait for a quiet window) and no older than its own start: a request that
predates the process was delivered to the kernel before it, so the walk ends
there. A row with an action names the request. The kernel's own `signal` and
`parent-gone` rows are verdicts a previous kernel filed on its exit, never a
request, and are passed over. A `down-failed` row (written when a `romp down`
did not stop the kernel) cancels the `down` written before it. The manager's
`manager-sigterm` row is a note that the manager sent the signal, not a
request: it answers only when no request row written before it lies within the
window and this kernel's lifetime, with `manager-sigterm: <trigger>` as the
reason, so a `down` followed by the manager's `cli-down` note still reads as
the `down`, and a note aimed at another kernel's pid is ignored. A row with no
action (the `romp refresh` row on builds before it labeled the row) is skipped,
and the manager's `restart-all` note written after it is what names the
refresh.

When no row qualifies, the kernel writes a row with action `signal`: the signal
name, its pid and its parent's pid, the manager pid it was started with,
whether a manager restart was pending, `managerRequested: false`, and
`managerStopped`. That last field is what the kernel can see of a service stop
or restart, which signals the kernel and the manager at once: the manager's pid
is already gone, or the manager's own stop note lands while the kernel drains
or within half a second after. With `managerStopped: true` the reason reads
`signal; the manager was stopped too (a service stop or restart)`; otherwise
`signal, not requested through the manager`, which means no request was on
record when the kernel read the ledger, not that the sender is known. The
sender's pid is never recorded; a Python signal handler does not receive it. A
kernel whose manager disappears writes a row with action `parent-gone` before
it exits. `restart-cuts.jsonl` gets one row per exit naming the turns the drain
cut and the reason: the audit row's `action: reason`, the `signal` row's
reason, or `parent-gone: the manager exited; the kernel followed it`. A second
SIGTERM during the drain is ignored; the first writes the row. The manager's
log says `exited without a restart request (signal or crash); respawning` when
a kernel exits that it did not ask to stop or restart.

The two host registries there, `remotes.json` (attached and checked-in
machines, each row with that machine's serve token) and `remotes-known.json`
(machines remembered for re-attach, with the mail tier you set for each), are
read at boot under the rule their doors apply: a checked-in row's host must be
a machine name, an attached row's an ssh alias, a remembered row's either. A
row that fails (one filed before the doors applied the rule) is set aside,
never loaded and never written back: the rows are moved to
`<file>.refused-<UTC stamp>` beside the original (`-1`, `-2` when a second one
lands in the same second; the `remotes.json` sidecar is 0600, since its rows
carry tokens), the file is rewritten without them, and one stderr line plus one
Log entry under the `refused` kind names each host as a clipped repr, never the
raw string.

The postal service's own files live under `postal/` there: `mail/<session>/`
(a maildir per recipient), `outbox/<host>/` and `readbox/<host>/` (cross-host
mail and read receipts awaiting their peer). A record or message file the bus
cannot parse or read is moved aside once, never deleted, to
`<name>.corrupt-<UTC stamp>` beside the original (an inbox file lands beside
its `new/` directory, out of every listing; a `-1`, `-2` suffix when two land
in the same second), the rest of the store is served, the sender's receipt for
that message reads refused, and the error center says so under the `refused`
kind. At start the bus removes the temporary files a crash left behind (a
message written but never placed, a store record never finished), closes each
one's receipt as refused, and says so once. The sidecars are yours to inspect
or delete.

## Switches

Effective immediately, no restart.

`touch` to **disable**, `rm` to re-enable:

- `~/.claude/romp-postal-off`: the postal service

`touch` to **enable**, `rm` to turn back off:

- `~/.claude/romp-summarize-on`: the live tmux activity phrase. Off by default,
  because it spends tokens on every turn and the Claude Code backend reports
  what a session is doing without it.
