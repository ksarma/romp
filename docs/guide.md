# Guide

This guide covers how to use Romp and how its back end works.

## The Romp user interface

Romp gathers all your Claude Code sessions into one interface, with six
complementary panes:

- **[The chat](#the-chat)** is the regular interface for talking to a coding
  agent, with features that make a long session easier to scan.
- **[The feed](#the-feed)** is Romp's task-management layer: what is in
  progress, what needs your input, and what is done.
- **[The timeline](#the-timeline)** is the history of what each session worked
  on and how they coordinated; click any part to jump to that moment in the
  chat.
- **[The outline](#the-outline)** lists every session with its tasks, for
  reviewing what a session has done and searching across all of them.
- **[Waiting on you](#waiting-on-you)** lists every user todo a session has
  flagged for you, across all your sessions and machines, with Reply and
  Dismiss on each.
- **[Files](#files)** holds the file viewer in a column of its own, so a file
  stays open beside the chat and the feed.

### The chat

![Tool calls fold into runs; each expands to one line per call](assets/guide/chat-detail.png){ width="100%" }

**Commenting on a file.** Select any passage in the file viewer and it lands in the
composer as a quote chip, labeled with the file and the line the passage lives on. Type
what should change and press **⌘⏎** to set the note aside; keep reading, select the next
passage, and repeat — each staged note remembers its quote and its place. **⏎** sends
everything you staged along with whatever is in the box, so the session applies the lot
in one pass, and you never copy a line out of the document by hand. The line in each
label is checked against the file at the moment you select, so numbers that moved under
you are caught rather than quietly carried. Chips are one-off notes: they go out with the
message and are not kept. For anything worth keeping with the file, use the viewer's
**Comments** panel, described under Files: a file comment is stored beside the file, the
session replies into it, and its edits to a tracked file come back as changes for you to
accept or reject. When several sessions work in the same
repository, or in worktrees of it, the viewer's title bar says which one you opened the
file from: a chip with the session's name, in the same color as its tab. The title bar's
**GitHub ↗** button opens the file on GitHub. When there is nothing to open, the button stays
in place, dimmed, and a caption beside it says why (the file is not committed, the repository
has no origin remote, or its origin is not on GitHub); the button's tooltip repeats the reason
in full. A file on a branch that is not on origin keeps its link, drawn with a dashed border,
and the caption says the branch is not on origin yet. That check reads the local tracking
ref, so after a branch is deleted on GitHub the link looks normal until `git fetch --prune`
has refreshed it.

**Tags and groups.** A tag is a named, colored set of sessions; a session can be in
several. Right-click a tab and open **Tags** to add or remove them. Tags filter every
surface (the tag button in the strip narrows the tabs to the tags you pick), and they group
the tabs: as soon as any session carries a tag, the strip shows one section per tag, in your
tag order, each with a header in the tag's color, and the untagged sessions after a divider
at the end. A session with several tags sits under the first of them in your tag order; its
other tags still filter. Click a header to fold that section down to a count, plus one pip
when a member is working or waiting on you; the section of the tab you are reading never
folds (its header says so, and a click there changes nothing), and the `archived` section
starts folded. Drag a header to reorder the groups, which
reorders the tags on every surface (the timeline's tag table shows the same order). To move
a tab into another group, right-click it and pick **Move to <tag>** under **Tags**: one click
adds that tag and drops the tab's current group tag, leaving its other tags alone. The row's
**+** adds the tag without moving the tab. **Group tabs by tag**, at the foot of the tag
button's menu, turns the sections off for this browser.

### The feed

The feed is Romp's task-management layer: a card for each task. Romp's
[judges](judges.md) watch each session's work, split it into those tasks, and
keep every card current.

Cards sit in three columns:

- <span class="romp-chip romp-chip-working">Working</span> — the session is
  actively working on the task.
- <span class="romp-chip romp-chip-blocked">Blocked</span> — it needs your
  input to move on.
- <span class="romp-chip romp-chip-completed">Completed</span> — done, ready
  for you to review and clear.

![The feed's three columns, with the cues on a card](assets/guide/feed-annotated.png){ width="100%" }

<span class="romp-btn">Background</span> is why the agent is taking the action,
and <span class="romp-btn">Summary</span> is what it did. When a task divides
naturally into parts, the card's <span class="romp-btn">Sub-goals</span> button
opens them.

Cards follow the work rather than the session: one session can hold several
tasks, and a task can be handed from one session to another.

Press <span class="romp-btn">Clear</span> on a card when you are done with it. A
cleared card is archived, and no more work is added to it.

### The timeline

Each row is one session. A bar is a stretch where the session was working, and a
circle is a message you sent. A striped stretch means the session is blocked,
waiting on your input.

![A timeline lane per session, with status and context at the left](assets/guide/timeline-annotated.png){ width="100%" }

Click a bar or a message marker to jump straight to where it happened in the
chat.

Session statuses:

![Each session state and what its color means](assets/guide/status-legend.png){ width="70%" }

### The outline

Every session with its task tree: open work stays up top, finished work folds
beneath. Open the outline to review what a session has worked through, or to
find past work: the search box reaches every session, live or closed.

![The outline: each session's tasks as a tree](assets/guide/outline.png){ width="100%" }

### Waiting on you

One list of every user todo a session has flagged for you, oldest first,
across every session and every attached machine: a decision it needs, a
credential, a pick between two designs. Each row names its session and shows
how long the todo has waited. Reply sends your answer straight into that
session, waking it if it has gone quiet; Dismiss clears the todo without a
reply. A file path in a todo's detail is a link: click it and the file opens in
the Files pane, which comes forward if it was closed. The pane is off by
default, like the outline; turn it on from the bottom bar. Sessions flag todos
only where the gear's **User todos** switch is on, and the switch is per
machine: while it is off on this one, the pane says so and still lists the
other machines' todos. A todo you expected can be missing for two reasons. A
session that has ended keeps its todos out of the list until you revive it
(click **+**; closed sessions are listed under **Recent**). A session you have
hidden from the feed (right-click its tab, **Hide from feed**) keeps them out
too, though its tab still shows the ⚑ mark; **Show in feed** on the same menu
brings them back. The file the todo named is still on disk.

### Files

The Files pane holds the file viewer in a column of its own, beside the chat
and the feed, so an open file covers neither. While the pane is open, a file
link clicked in the chat opens here. When it is closed, the gear's **File
links open in** setting decides where a link opens; set it to **The Files
pane** and the pane comes forward on its own and stays up until you close the
file. Selecting
a passage in it puts the quote in the chat's composer, as it does from the
viewer over the chat. When no file is open, the pane lists the files most
recently open here; click one to open it again. The pane is off by default;
the bottom bar turns it on.

**Comments and tracked changes.** The viewer's **Comments** action opens a panel beside
the file (below it when the column is narrow). Select a passage in either view, Rendered or
Raw, and press the **Comment** button that appears next to the selection; type the note
and press Enter. **Comment on this file** leaves a comment on the file as a whole, which
every file takes. When a passage cannot be mapped from the
Rendered view (a table, a code block), the panel says so, keeps your note, and offers the
Raw view with the passage selected. Comments are stored beside the file, in the
`.trackchanges/` folder at the root of its project (the nearest git repository, vault, or
folder that already holds one; a file with none gets the folder created beside it), in the
format the session's own tools read. A comment made here and a reply the session writes are
the same object, and the two other editors that read the format see them too. Each comment
is a card in the panel: click it to expand, reply into it, or resolve it. The passage it
refers to is highlighted in the file. When the session has rewritten the passage, the card
says so, and **Reveal** finds the passage in the Raw view when the Rendered view cannot
show it.

**Figures.** On an image, whether it is a file of its own or a figure in a markdown page,
drag a rectangle to comment on that part of it. The rectangle stays on the picture with the
author's chip, and the card shows that part of the image. When the image's bytes change the
comment is shown as stale until you resolve it, or press **Re-place** and drag the rectangle
again where it belongs now; the comment keeps its words and its replies, and only the
rectangle changes. A figure embedded in a markdown file, such as `![](plot.png)`, is loaded
from the file's own folder, so a relative path shows in the Rendered view; a web address or a
`data:` image is left as written. A comment on an embedded figure is stored on its embed line,
with the rectangle: the session's tools and the other editors place it on that line, and this
viewer paints the rectangle on the picture. Drawing a rectangle needs a mouse or a trackpad;
on a phone, comment on the file as a whole instead.

**PDFs.** A PDF opens in the browser's own PDF viewer. While **Comments** is open, the viewer
draws the pages itself instead, one below the other, so a rectangle can be dragged on a page
the same way as on an image; the comment names its page, and its card shows that part of the
page once the page has been drawn. Pages are drawn as you scroll near them, so until then the
card shows a line naming the page, and clicking it scrolls the page in. A rectangle drawn on
one page can be placed again on another. Pages are drawn only up to 25 MB of PDF; above that,
or when the page renderer cannot be loaded or the file cannot be opened, the browser's viewer
stays with a line above it saying why, and a comment on the whole file still works. The
renderer ships without pdf.js's standard fonts and CMaps, and without its JPEG 2000, JBIG2, and
fax (CCITT) image decoders, so a PDF that does not embed its fonts may show some text in a
system font, and an image in one of those encodings is left blank, with a line at the top of
the page saying how many; the rest of the page still draws, and the browser's own viewer shows
the whole page.

**Track changes** records a session's edits to the file as changes for you to accept or
reject, instead of letting them land silently. Turn it on for the file or for its folder,
and turn it on for the folder a session will write into *before* it writes: only edits made
while tracking is on are recorded, and a folder can be tracked before its files exist.
Each change is a card in the panel, grouped by the paragraph it falls in, and is marked in
the file: an insertion is tinted, and a deletion is struck at its point in the Raw view.
**Accept** keeps the text as it is and drops the record. **Reject** puts the old text back in
the file. **Accept all** and **Reject all** decide every change at once; Reject all asks you to
confirm. A deletion has nothing to mark in the Rendered view, so its card offers **Reveal**,
which opens the Raw view at the deletion; any change the current view cannot show offers it
too. Reply on a change's card leaves a comment on the change itself, and the session's answer
comes back to that card. While changes are pending, the viewer's **Edit** button refuses,
because a direct edit would move them: accept or reject them first. The session's own
track-edit keeps working. A session's tools refuse to rewrite an image or a PDF as text, so a
tracked folder may hold figures.

**Send to session** hands everything unsent to the session that owns the file as one
message, in your words: the comments and replies you wrote since the last send, each with
what it refers to and the commands the session needs to answer it. The number on the button
is what will go, and the confirm lists it, with the message itself one click away. When the
file was opened from a request under Waiting on you, a checkbox answers that request with
the same send; when tracking is off, another turns it on first, so the session's revisions
come back as changes. When changes are pending, a third checkbox, **accept the pending
changes**, accepts them all before the send, so the session's later edits arrive as new
changes instead of folding into an old one; the message then says how many changes you
accepted and rejected. All are checked by default. One send answers a request; a request
that named several files is answered by the first, and later sends show no checkbox. The
panel then says **Sent to** the session and when, or **Queued for** it when the session has
gone quiet, in which case the message goes when it wakes.

While the panel is open it checks the file, its comments, and the project's tracking list
every few seconds, so a reply the session writes appears without a reload and a file the
session rewrote is shown as it is now. The first comment, like the first save, asks once
whether the dashboard may write files on that machine; the same switch, **File editing** in
the gear, turns it off again, and while it is off a send is refused too (it writes the log)
and asks for the consent back. The **Log** at the foot of the panel is the comments log: what
was sent and when, the changes you accepted or rejected, tracking turned on or off, and your
direct edits to the file, kept beside the comments in the same folder so git keeps it when the
project does. Once a change is decided, its card is gone and the Log keeps the decision: the row
gives the count, and clicking it shows the old and new text of each change. Whether
`.trackchanges/` is committed is the project's call; a `.gitignore` line keeps it out.

If the **Comments** action is missing on a file, the gear's **File comments** row says why:
the kernel that owns the file has no node on its PATH, or it predates the feature. The same
row warns when sessions on that machine cannot reply because their tooling is not linked
into `~/.claude`; running romp's `install.sh` there links it.

## Automatic nudges

Agents stall: they hit an API error, they get interrupted, or they end a turn
leaving it ambiguous whether a task is done. Romp nudges a stalled session with
an injected message, so every task ends up either explicitly done or explicitly
needing your input.

Romp asks the agent, item by item, where each open piece stands: continue what
it can, and say what blocks the rest.

- If the agent can keep going, it does, and you were never interrupted.
- If something needs you, the card flips to <span class="romp-chip romp-chip-blocked">Blocked</span> and names exactly what
  it needs.

Nudging engages only when you are not actively messaging the session, so it
never talks over you and never loops on its own messages.

A session can also be waiting on something unrelated to you: it dispatches work
into the background, then pauses for the result. In that case it shows an
<span class="romp-chip romp-chip-await">Awaiting</span> chip. The chip clears on the
session's next turn, when the task finishes or blocks, when you clear the card,
or as soon as you reply.

## Inter-agent communication (the Romp Postal Service)

Sessions message each other through a mailbox Romp gives them, and every
exchange is visible to you. Each session gets mail tools: send a message to a
session by name, check the inbox, and see who is live. Each session also
publishes a working note saying what it currently holds, so agents can see who
to talk to instead of messaging each other to find out.

The timeline draws an arc for each message. Hover one for its gist:

<video src="../assets/guide/coordination.mp4" controls loop muted playsinline preload="none" data-romp-autoplay width="100%"></video>

Underneath, a local message bus writes the message into a mailbox on disk that
belongs to the recipient, then delivers it: straight away if that session is
idle, otherwise when its current turn ends. The recipient reads it as a message
in its chat, and it appears in the user interface as a card naming the sender
and the kind:

![A message from another session, as the recipient's chat shows it](assets/guide/postal-chat.png){ width="100%" }

Every message declares its kind, which the card wears as a chip:

- <span class="romp-chip-kind romp-chip-delegate">delegation</span> — the recipient owns the work now.
- <span class="romp-chip-kind romp-chip-coordinate">coordination</span> — a heads-up; a reply is optional.
- <span class="romp-chip-kind romp-chip-question">question</span> — an answer is required.

The same mailbox is on the command line, for you and for scripts:

```bash
romp mail send --kind question api "Which auth approach did we settle on?"   # send, to the session named "api"
romp mail inbox                                                              # read this session's messages, and clear them
```

The full mail surface, shell and in-session, is in the
[Reference](reference.md#mail-from-the-terminal). Names resolve against the
currently live sessions; sending to a dead session's name errors instead of
silently parking mail.

## Sessions, revival, and search

A session outlives the conversations inside it. `/clear` starts the agent on a
blank slate, a relaunch starts it over, the kernel restarts: each of those is a
new conversation underneath, and `api` is still the same `api` on your board,
with its history and its cards.

Closed sessions come back. Click **+** and the closed ones are listed under
**Recent**; pick one and Romp offers to revive it, with its history intact, or
to open it read-only. Revival works by picking the session, not by its name, so
a new session that reuses an old name is a new session rather than the old one
resumed.

A session can also move to another folder. When the code it works on moves, say
a subproject that became its own repository, right-click its tab and choose
**Move to folder…** (or run `romp move <session> <dir>`): the conversation,
name, mail and history stay with the session, and from the next turn on the
agent works in the new folder and reads its `CLAUDE.md`.

A session started from another one joins its tags. Forking a session, breaking
a comment thread out into its own session, and running `romp new` inside a
session's shell all put the new session in the parent's groups, so a session's
children land beside it in the tab strip. `romp new --no-inherit` starts one
outside them; `romp new --in <tag>` names the tags directly (repeatable). The
**+** picker shows the tags of the tab you are looking at pre-selected in its
**Tags** row, where you can unpick or add before creating. Opening a name that
already runs inherits nothing: `romp new --in` still applies to it, while from
the picker, a name that already runs is focused and the Tags row is not applied
(a message says so; the row is a prefill, and applying it would move the
running session). Comment threads have no tab and inherit nothing until they
are broken out; `romp new` run inside a thread inherits from the session the
thread belongs to.

Search reaches inside sessions, not just across their names. As sessions run, a
lightweight index judge writes each one a headline and an abstract of what it
did, so searching for the work finds the session that did it, months later.

### Session backends

Sessions run on one of two backends, chosen per session:

- **SDK (the default, strongly recommended).** The kernel manages the Claude
  Code session through the Claude Agent SDK.
- **tmux.** A Claude Code session running in a terminal inside tmux. Run
  `romp new -t <name>` and that terminal session joins the interface like any other, so
  you can work in the terminal directly and still see it in Romp. The cost is
  that Romp has no direct connection to it: it reads what appears in the
  terminal and on disk, and sends messages and nudges by injecting keystrokes.
  That makes it less reliable and less responsive than the SDK, since scraping a
  terminal has edge cases a real API does not, and updates wait on the
  transcript reaching disk.

The two backends interleave freely, so terminal sessions and SDK sessions sit
side by side in the interface and message each other like any other pair.

## The Romp kernel (the back end)

The kernel is the program that runs your agents, watches their work, and serves
the user interface at `127.0.0.1:29855`. You run it on your own machine, with no
hosted service in between. Everything Romp stores stays local; the only traffic
that leaves your machine is `claude` itself, both the agents' own model calls and
the LLM calls in Romp's judge pipeline.

### Linking kernels on other machines

Romp kernels can connect and communicate across multiple machines, e.g. a laptop
and a server. This lets you control them all from one user interface, and lets
their agents communicate across the machines. A linked machine's sessions appear
as
<span class="romp-sid"><span class="host">server:</span>api</span> tabs and
timeline lanes beside your local ones, its cards share the feed, and its
sessions message yours, so an agent on your desktop can hand work to one on the
server.

You link machines from the network popover, which opens from the button at the
bottom right beside the settings gear:

![The network button](assets/guide/network-icon.png){ width="72" }

Every machine gets a row there with two controls. **Attach** brings that machine
into your interface: its sessions, its cards, and mail both ways over the one
connection. **Share my sessions there** puts your sessions in *its* interface,
for when you also work from that machine.

#### Attach a Romp kernel on another machine

Attach any machine you can `ssh` to, such as a server or a desktop that stays
on. Your kernel opens the connection.

1. **Install Romp on that machine**, the same way you installed it on your own
   (see [Install](install.md)).
2. **Check that `ssh <host>` connects without prompting you for anything.** Romp
   opens the connection in the background, so a password or passphrase prompt
   stops it; set up key-based login if you need to. Any target you could type
   after `ssh` works, including a `~/.ssh/config` alias.
3. **Attach it from your interface.** Open the network popover, click **+ Add a
   host**, type the ssh target, and click **Attach**.

The machine appears as a row with a live status, and Romp reads its kernel's
access token over ssh so your browser can authorize against it. A row reading
**kernel not answering** means no Romp kernel is running there: click **Start**,
which brings that machine's Romp up to date with this one's and boots it. Romp
never starts a remote kernel by itself, since a stopped one may be stopped on
purpose.
Detaching keeps the machine under **Previously attached**, so re-linking later
is one click and it returns with the trust level you last gave it.

#### Mail across linked machines

Each linked machine carries a trust level, set on its row, that decides what
happens to mail arriving from it:

- **trusted** — delivered straight to your sessions.
- **directed**, the default — held for your approval as a needs-you card.
- **isolated** — no mail either way; its sessions still appear in your
  interface.

Which to choose, and what each one guards against, is in
[Security and trust](#security-and-trust).

Machines that a linked machine can reach appear to you too, under **Reachable
via relay**: no tunnel of your own, their mail arriving one hop through the
machine in between. They carry the same trust selector as any host, because a
message is judged by where it came from rather than by the route it took.

When another machine is holding mail for approval, **Held for approval
elsewhere** shows you that it is, and how much, with the gist on hover. Acting
on a held message stays on the machine holding it, so this tells you where to
go rather than deciding for you.

Mail for a machine that is offline waits in an outbox and delivers when it comes
back. If it returns and the session you addressed is gone, that refusal comes
back to you. Every machine runs its own postal bus, so a laptop with no
connection at all still has full local messaging; linking only adds reach.

#### Also drive the fleet from the far machine

Attaching leaves the far machine's interface unaware of your sessions. Do this
only if you work from both computers, since mail already crosses both ways
without it.

If that machine can `ssh` to yours, it can just attach you and you are done. A
laptop usually cannot be reached that way: it moves between networks and sits
behind a router that accepts no incoming connections. Work from the laptop
instead:

1. **Attach the always-on machine** you want your sessions to appear on,
   following the steps above.
2. **Tick "Share my sessions there"** on that machine's row.

Your sessions now show up in its interface from whatever network you are on.
Because the laptop is the end that connects, the always-on machine never holds a
way in to it; untick the box and it forgets you. Romp calls this checking in,
and the always-on machine the hub, which is where `romp checkin` and
`romp checkout` get their names.

#### Hand the connection to a different machine

The add-host box has a **from** picker. Leave it on *this machine* and the
tunnel lives here, dropping when this kernel stops. Choose an attached host
instead and the attach is forwarded to that kernel, which dials out itself, so
the connection outlives your laptop. That machine needs its own ssh access to
the target.

The mechanics, including how the tunnels and the check-in handshake work, are in
[How Romp works](architecture.md).

## Remote access

You reach Romp in a browser tab, in the VS Code / Cursor extension, or from your
phone.

### From another machine

The kernel listens only on `127.0.0.1`, so a browser on another machine needs a
path to that port. Two paths work well; one common one does not.

**Plain ssh port forwarding.** From the machine with the browser:

```bash
ssh -N -L 29855:127.0.0.1:29855 <the machine running romp>
```

Then open `http://127.0.0.1:29855` as usual. OpenSSH forwards each browser
socket one-to-one and propagates closes, so a pane that goes away is gone on
both ends.

**Tailscale.** The same setup as for your phone below gives every device you
own a direct path; the dashboard is then a plain URL on your tailnet.

!!! warning "The VS Code port forwarder is not a good path for the browser dashboard"

    VS Code's Remote and Tunnels port forwarder multiplexes every forwarded
    socket over one channel and does not close the far end when the browser
    side goes away. The dashboard's panes are long-lived WebSockets that stream
    view updates, and each pane reconnects when it hears nothing for thirty
    seconds, so through that forwarder every reconnect left a dead connection
    behind on the kernel's side, all of them still receiving full view payloads
    over the one shared channel, and the live panes starved. One such incident
    counted 84 connections from three real panes.

    The kernel now protects itself: it pings every pane on each heartbeat and
    drops one whose ping goes unanswered, a reconnecting pane retires its own
    previous socket at once, and the timeline and feed cross the wire as
    deltas instead of whole payloads. That keeps a forwarded dashboard usable,
    but the forwarder still carries every byte over a channel it shares with
    your editor, so prefer one of the two paths above. The VS Code romp view
    is a different case: its sockets run on the kernel's own machine and close
    when a panel closes, so it never leaks connections, but under Remote or
    Tunnels the extension still relays each whole view payload to the local
    window as it changes. It does not yet take the deltas the browser panes do.

### From your phone

The user interface is a web page, so your phone can run it against a kernel on
another machine. The obstacle is reaching that machine: the kernel listens only
on `127.0.0.1`, which your phone is not on.

[Tailscale](https://tailscale.com) closes that gap, and is free for personal
use. It puts your own devices on a private encrypted network, so your phone can
reach your laptop directly whatever network either one is on. Install it on both
devices and sign in to the same account on each.

In the Tailscale admin console, enable **HTTPS Certificates**, and leave
**MagicDNS** on (it is on by default): the `ts.net` certificate names come from
MagicDNS, so turning it off makes certificate provisioning fail in confusing
ways.

Three settings in the Tailscale app on the kernel's machine decide whether your
phone can reach it at all:

- **Allow incoming connections** must be on. Without it the machine joins the
  network but serves nothing to it, which reads as Romp being broken rather than
  as a Tailscale setting.
- **Use Tailscale DNS settings** must be on. This is MagicDNS on the client, and
  it is what makes the `ts.net` name resolve.
- **Launch Tailscale at login** is worth turning on. The proxy below survives a
  reboot, but it can only serve while Tailscale is running, so without this the
  machine drops off the network until you next open the app.

Then, on that same machine, one command opens Romp to your other devices:

```bash
tailscale serve --bg 29855
```

The bare-port form needs Tailscale 1.56 or newer; on older clients write
`tailscale serve https / http://127.0.0.1:29855`. On macOS the `tailscale`
command is not on your `PATH` until you enable **CLI integration** in the app's
settings.

Two commands go with it, for later rather than now. `tailscale serve status`
prints where the proxy currently points, which is the first thing to check when
a device cannot reach Romp. `tailscale serve reset` undoes the setup and returns
the machine to local-only, so run it when you want remote access off, not as
part of turning it on.

!!! warning "If you change the kernel's port"

    `tailscale serve` remembers the port you gave it, not whatever Romp is
    running on now. Change `ROMP_KERNEL_PORT` and the proxy goes on pointing at
    the old one, so the phone gets a dead page while everything looks healthy on
    the machine itself. Re-run `tailscale serve --bg <new port>` — it replaces
    the existing mapping rather than adding to it.

On the phone, open `https://<machine>.<tailnet>.ts.net/`. Romp answers with a
page asking for your access token; paste in the one `romp` prints. A
year-long cookie remembers the phone afterwards. Prefer this to putting
`?token=<token>` in the address, which works but leaves the token in your
browser history and in anything you share the link through. The cookie is itself
a credential, so only do this on a phone you control.

Only devices signed in to your Tailscale account can reach Romp: Tailscale
checks each device's identity and encrypts the traffic between them, and nothing
is exposed to your local network or to the internet. The proxy survives restarts
of both Tailscale and the kernel.

Two settings are worth changing while you are in the admin console. Turn on
**device approval**, so a new device has to be approved before it can join, and
leave key expiry enabled on the phone. Do not use `tailscale funnel`, the
public-internet variant: it would leave the token as the only thing between the
internet and your agents, with no device check in front of it.

!!! warning "If other people are on your tailnet"

    `tailscale serve` exposes Romp to **every** device on the tailnet, not just
    yours. On a family or team tailnet, the access token becomes the only thing
    standing between other members and your agents. Either keep the tailnet to
    your own devices, or write an ACL restricting the kernel machine to them.

## Security and trust

Romp drives agents that run tools and shell commands as you, so reaching its API
is equivalent to running code as you. Everything below follows from that.

**One token, required on every request.** The kernel and the postal bus both
demand a token on every request, local ones included. Loopback is not a
security boundary: on a multi-user machine every local account can reach your
ports, so without this any other user could inject prompts into your live
sessions. The token is 144-bit random and lives at
`~/.local/state/romp/serve-token` with mode `0600` (readable only by your own
user account). Local tools (the CLI, hooks, the bus, the editor extension) read
that file and send it automatically, so you never type it. Only liveness probes
(`/healthz`, `/version`, `/busy`, and the bus's `/ping`) are exempt.

A browser cannot read that file, which is why the link `romp` prints carries the
token in it. The first visit trades it for a year-long cookie, so the bare
`http://127.0.0.1:29855/` works from then on; `romp url` prints the link again
for a new browser or after clearing cookies. The cookie is a credential in its
own right, so treat a machine holding one as signed in.

**Remote machines.** Every machine mints its own token. When you attach a host,
your machine reads that host's token over ssh and stores it locally (in
`~/.local/state/romp/remotes.json`, also `0600`: it is a credential store).
Dashboard traffic to a remote never crosses the network in the open; it rides
the ssh tunnel, which supplies encryption and machine identity, while the token
authorizes at the far end. Checking a laptop in to a hub reverses which end opens
the connection, so credentials still flow outward from the machine that
initiates, and a hub never holds a way in.

**Trust levels for attached hosts.** Attaching two kernels lets their sessions
message each other, which means a session on the remote machine can put text
into a local session's context, and text in an agent's context can steer it. So
each host carries a trust level, set on its row in the network popover and
remembered per host. The level goes by where a message originated, not by the
route it travelled, so a machine whose mail reaches you relayed through a hub is
judged by the level you gave that machine:

- **trusted** — sessions on both machines message each other freely, as if they
  were on the same machine. For a machine you fully control.
- **directed** (the default for a newly attached host) — you can send work to
  its sessions, but its mail back to you is held for approval: each held message
  becomes a needs-you card with **Approve**, **Edit**, and **Deny**, so a person
  decides before that host's content reaches one of your agents. For rented or
  shared compute.
- **isolated** — no messaging in either direction. Its sessions still appear in
  your interface, but the two mail systems never connect. For gathering kernels
  that have nothing to do with each other into one place to work from.

**What this does not protect against.** Anyone with administrator access to a
machine can read any file on it, the token included, so don't keep long-lived
credentials on a machine you don't trust that far. Any program already running
under your own user account can read the token too, so two sessions on the same
machine are separated by policy rather than by this boundary. The lines Romp can
actually enforce are per-user (the token file) and per-machine (the trust
level).

Full details, including how to report a vulnerability, are in
[SECURITY.md](https://github.com/romp-on/romp/blob/main/SECURITY.md).

## How many tokens does Romp use?

Romp spends tokens on top of what you spend yourself. If you are running models
like Opus or Fable at high effort, the judging costs much less than the sessions
themselves. The analytics modal in settings shows what you actually spent,
separating your sessions from the judge pipeline. You can also reconfigure the
judges from the gear: the high-volume indexing tier defaults to Haiku, and the
judgment tier defaults to Sonnet.
