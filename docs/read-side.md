# The read side: the kernel, the UI, and the three panes

!!! note "Optional reading"
    You don't need any of this to use Romp.
    Describes the system as of **2026-07-24**; the behaviour it documents moves,
    so treat anything here as a snapshot rather than a contract.

Architecture deep dive. Layer 3 turns the records written by the event model
(`event-model.md`) and the summarizer layer (`docs/judges.md`) into the three
web-UI panes you look at: the **feed**, the **chat**, and the **timeline**.

## The governing principle

**Layer 3 derives no meaning. All meaning is computed below it (almost all in
Layer 2); the read side only selects and displays.** The judges write durable
meaning once; the panes are thin projections of it.

A direct consequence: the completion **rollup + "settled" gate** lives in
Layer 2. The producer publishes each goal's rolled-up status (working / blocked /
completed); the feed just paints columns. (Reflected in `docs/judges.md`.)

## The kernel and its clients

- **The kernel is the core, supervised by `romp-manager`.** One process: Layer 1
  (parse) + Layer 2 (the judges) **and** an HTTP server, single writer. Its
  *lifecycle* is owned by **`romp-manager`** — a durable, jupyter-lab-style
  supervisor, started by the login service that `install.sh` sets up, that spawns
  and respawns the kernel (via `romp-serve` → `romp-kernel`) and stays up across
  kernel restarts. Front ends
  (browser, phone, VS Code) ATTACH to the kernel; they never spawn it.
  `romp-serve` points at the Python kernel, so `romp up` supervises it on the
  manager's port (29855), and the front ends and tailscale serve attach unchanged.
- **The UI is served by the kernel.** The front-end (the three panes) is `ui/`. A
  browser hits the kernel's port and gets it.
- **The login service starts the supervisor**; `romp up` instead runs
  `romp-manager` in the foreground (like `jupyter lab`), for machines without the
  service or for watching it work. `romp refresh` restarts the kernel(s),
  `romp status` reports them. The kernel binds loopback only; tailnet/phone reach is
  `tailscale serve` proxying to `127.0.0.1:29855` (there is no `0.0.0.0` opt-in
  door; the tailscale proxy carries the phone path). The UI itself is just a URL
  the kernel serves.
- **Session discovery keys on the rompUuid birth stamp, not a time window.** The
  kernel discovers only sessions carrying the rompUuid birth stamp the launcher
  writes — the same rompUuid registry `event-model.md` defers, which also powers
  session→files stitching. A 48h window is allowed only as a perf bound on how far
  back to parse, never as the eligibility test (a time window is a fragile proxy
  and a banned time-heuristic). The kernel does not read or migrate the legacy
  record stores (`summaries/`, `requests/`, `decision-log`, `corrections/`,
  `digest/`), so old data cannot pollute the new model. Pre-rebuild sessions
  simply never appear: no resume-picker entry, no scrollback over old history.
- **The VS Code extension is a thin client.** It speaks the kernel's WebSocket
  protocol (`vscode-extension/src/extension.ts`: "a THIN CLIENT of the romp web
  kernel", `ws://HOST:kernelPort()/ws?app=...`). Browser and extension render the
  **same served UI** over the **same protocol**, so the two front ends stay
  consistent by construction. Keeping the WS protocol stable is the compatibility
  contract.
- **The feed is pushed as one full frame, then as deltas.** A pane's socket
  receives nothing until the pane's bundle says it is listening. Every
  kernel-served pane page announces `readyGate` on its socket, because the pane
  shim opens the socket before the bundle has loaded and has no inbound buffer;
  the kernel then holds every push to that socket (pusher cycles, broadcasts, a
  reveal) until the bundle sends `ready`. A socket that does not announce
  (federation's remote relays, the VS Code extension's pipes, an older page) is
  served from accept, as it always was. Keepalives and the restart notice reach
  every socket, held or not: the shim consumes both itself. On `ready`, a feed
  socket receives the cached `{type:"feed"}` frame at once, with no build, and the
  frame's `now` is rewritten to the time of the serve. The rewrite matters because
  the pusher builds only while a client is connected: after a night with no
  dashboard open, the cached build's clock is a night old, and the pane would
  anchor every age and tint on it. The pane anchors its live clock on that `now`
  paired with the moment the frame arrived from the wire (federation stamps the
  merged frame with `nowAt`), never on the moment a frame is handed to it: the
  merged frame is re-emitted on a view-order write, on a remote host's frame and
  on a detach, and an anchor taken then moved every age back by the quiet period.
  The shim re-sends `ready` on a reconnect once the bundle has sent its own, so a
  reconnecting pane resyncs at once rather than on the pusher's next cycle; a
  redial that completes before the bundle has loaded sends nothing, and the
  bundle's own `ready` lifts the hold. A `ready` on a socket that is already
  ready is a re-base: the frame is served again rather than deduped.
  The kernel dedups per client. A client
  that announces `?caps=feedDelta` on its socket (the kernel-served feed,
  Outline and Waiting on you pages do) then receives `{type:"feedDelta"}` frames: changed cards by `itemId`, removed
  ids, the same for ledgers by `sid`, and the small top-level fields whole under
  `top` when any changed — and an unchanged board sends such a client nothing at
  all. Every other consumer — the VS Code extension's pipes,
  federation's remote sockets, an older bundle — stays on the full-frame path,
  which keeps its 60 s repost of the unchanged frame. `federation.ts` applies a
  delta onto the last full frame it holds for the host and re-emits a merged full
  frame, so every consumer still sees whole `feed` frames; a delta it cannot
  apply gets a `needFullFeed` and a re-base. A build that carries no `ledgers`
  says nothing about ledgers: the client keeps the ones it holds, and so does the
  kernel's record of them. Card age colours are computed client-side from `t` on
  a live clock (`age-color.ts`, `feed-age.ts`: the payload's `now` plus the local
  time since it landed, so a quiet board's ages and tints keep moving), never
  read from the wire. The Outline pane keeps the same clock: its ages, the
  current goal's elapsed time and its recency cutoff move on a 15 s refresh
  (skipped while the pane is hidden, with one catch-up render when it is shown
  again), since a delta client hears nothing from a quiet board. Full frames still carry the per-card `trgb` for older
  bundles that destructure it; deltas omit it, and the kernel's dedup signature
  ignores it, so a colour step is never a change (it used to re-send the whole
  board on every step: 5.76 MB a push on a board of about 660 cards, measured
  2026-09-02).
- **Liveness is a keepalive, and staleness is event-keyed.** The kernel sends a
  `ka` frame to every socket every 10 s; the pane shim force-closes a socket that
  has gone 30 s without any frame. After a reconnect the shim raises the "what you
  see may be stale" prompt only on the SECOND `ka` arriving before the resync
  frame — one full heartbeat period, bracketed by two kernel heartbeats on that
  socket with no resync between them (a single `ka` can be a beat that was already
  queued when the socket was accepted) — or on the reconnected socket closing
  again before its resync; the first non-keepalive frame retires the prompt. A
  client that falls 16 MB behind is dropped by the kernel, loudly: one `ws drop:`
  line in the kernel log, logged where the drop is decided so every send path is
  covered and naming the push slot whose frame tipped the budget when a push did,
  and a row in the dashboard's bell (at most five drop rows, none older
  than an hour, so they never crowd out a backend problem). Every close of a socket
  that opened leaves a `wsclose` breadcrumb (code, reason, socket age) in
  `client-diag.jsonl`; the redials an outage refuses are counted and reported as
  one `wsconnfail` row on the next open, and at most 20 breadcrumbs wait in the
  shim's queue for it.
- **Both judge tiers run continuously for any live session — no connection gate.**
  The kernel runs the index tier (captioner + archiver) AND the triage tier
  (planner → closer → courier → grouper → consolidator → distiller) in parallel,
  on a short event-driven backstop, whether or not a browser is attached — so the
  goal tree, feed, and timeline are already current the instant a client connects.
  A pass is cheap when nothing changed (cached parses; each judge makes an LLM call
  only on real new work), so always-on costs filesystem stats, not model calls,
  when idle. The tiers are a cost/value GROUPING (see `docs/judges.md`), not a
  runtime gate. Single process means single writer for free, no matter how many
  tabs are open.
- **Views are URL-hash tag selections.** `localhost:PORT/#work,personal` is one
  view; `#work` is another. Each browser tab is an independent view over the same
  kernel, ephemeral, zero-config, many at once. A saved default can live behind the
  settings gear.
- **Port is a per-machine config.** One fixed port the kernel binds at startup.
- **Liveness collapses to three states** (+ the user's `cleared`): **working**
  (open, nothing for you to do — including delegated work and waiting on a
  non-user trigger), **blocked** (needs *you*), **completed**. They map 1:1 onto
  the three feed columns.
- **`blocked` has a deterministic floor the judge cannot override.** A live
  permission / decision prompt is a fact, not a judgment. `blocked = hard OR soft`,
  hard wins: the planner's output can never clear a hard block. This is a merge
  rule, not a prompt instruction — the judge is told nothing special; its verdict
  simply never removes a hard block. Hard and soft rarely collide in time (the
  planner runs on *ended* segments; a live prompt sits on an *open* turn).
- **The read side has two inputs: durable judge records + a thin real-time
  live-state read.** Live state (the chip, the timeline stripes, the hard-block
  floor, "is a session mid-turn right now") comes from `states/<sid>.jsonl` + the
  event tree's open turn. It is deterministic and mechanical, not meaning-logic, so
  it does not violate the principle; it is the one thing that cannot be precomputed
  into a record because it is about *right now*.
- **Comms scope is directory-based, group-wide, alive-gated** (a design sketch —
  see below). A separate axis from view tags.
- **Tags are directory-derived, overridable.** A `directory → tag` map auto-tags a
  session at launch; a per-session manual override handles "get this out of work."
- **Hard data isolation is a separate `ROMP_STATE_DIR` root, manual, rare.** Default is
  one shared root (so views can overlap). Point a kernel at another root only when
  you genuinely need segregated data (a dedicated machine). It is free, because the
  root is already a parameter.

## The runtime picture

```
THE KERNEL  (one always-on process, single writer)
  Layer 1   parse transcripts → event tree
  Layer 2   index tier  (captioner + archiver)                      ALWAYS
            triage tier (planner/closer/courier/grouper/distiller)  ALWAYS (no connection gate)
  HTTP/WS   serve the UI + push pane payloads
  writes →  ~/.local/state/romp/   (the interface)

ROMP POSTAL SERVICE  (always-on infra, below Layer 2)  delivery never waits on a judge

CLIENTS  (0..N, pure readers, render only)
  browser tab(s)      ── each a view (URL-hash tags)
  VS Code extension   ── same WS protocol
```

The records dir is the only interface. The kernel is the only writer. Clients only
read and render. This is the producer/consumer split the whole system rests on,
collapsed into a single process for the common (one-machine) case while preserving
single-writer.

### How mail reaches a session

The bus stores mail per recipient (a Maildir) and the kernel owns the wake
(`POST /deliver`). Three delivery legs, chosen by what the recipient is:

1. **SDK session** — the kernel enqueues the banner on the session's SDK input
   queue. First-class, nothing to scrape.
2. **tmux session on Claude Code ≥ 2.1.224** — one JSON user record written to
   the session's **inbox socket**, the per-session Unix socket the CLI binds and
   registers (with its session id) in `~/.claude/sessions/<pid>.json`. The
   kernel joins that registry on the session's current transcript id
   (`lastSid`), connects, writes one line, done: instant, wakes an idle session,
   delivers between tool calls mid-turn, and never touches the composer, so a
   half-typed draft survives with no stash dance. The CLI treats socket arrivals
   as another-session traffic; its inbound gate can HOLD mail from an
   unverifiable sender (the kernel is one) when the session runs a bypass-class
   permission mode, and a held message silently expires after ~5 minutes — and
   the socket acks nothing, so a hold would read as delivered. That is why
   `bin/romp` launches sessions with the CLI's inbound-accept setting
   (`crossSessionInbound: accept`) and tags them `@romp-inbound-accept`, and the
   kernel takes this leg ONLY for tagged sessions: the tag is written by the
   same launch that made holds impossible, so tag and setting can never
   disagree. Security shape: the socket is owner-only (0600 inside a 0700 dir),
   unreachable from off-machine and from other local users; a same-user process
   could already type into any pane via `tmux send-keys` with FULL user
   authority, while socket mail arrives explicitly labeled as peer traffic with
   approval power stripped — the lower-privilege injection path of the two.
3. **Everything else** (older CLI, untagged launch, socket gone) —
   draft-preserving pane injection at a live ❯ prompt, with the Stop-hook drain
   (`hooks/romp-postal-drain.sh`) as the turn-boundary backstop. Unchanged, and
   still the fallback whenever leg 2 fails for any reason: non-delivery is
   caught by the maildir claim/retry and stuck-mail warnings either way.

## The two inputs

1. **Durable judge records** (`docs/judges.md` writes these):
   - **captions** — per segment and per turn, keyed by id. The activity log.
   - **the goal tree** — nodes + edges + per-node and rolled-up status. The inbox.
   - **courier records** — handoff (propagating / FYI) + which sender goal, keyed by
     message/segment id. The cross-session edges.
   - **archive** — per session, keyed by rompUuid: a sub-sentence **headline** + a
     2-3 sentence **abstract**, summarized from the session's captions (cheap
     input), continuously refreshed as the session gains turns. The index + the
     TOC header.
2. **A thin real-time live-state read**: `states/<sid>.jsonl` (working / permission /
   compacting / idle / closed transitions) + the event tree's open turn. Drives the
   chip, the timeline stripes, the hard-block floor, and the mid-turn pulse.

## The three panes (each a thin projection)

Chat is a zoom into Layer 1; the feed is a zoom into Layer 2; the timeline is the
bridge that shows Layer 1 spatially with Layer 2 labels.

### Chat = the event tree, rendered directly

Per-session tabs. Renders the event tree at the Atom / ContentBlock level (one
widget per block), with **no second transcript parser** — the event model already
produced the tree. Plus the live chip from the state read, and the TOC ledger below
the tabs.

**A send stays visible from the press until its record lands, and each layer
retires on an event, never a timer.** The kernel keeps an input echo (a synthetic
user atom in the backend's live store, mirrored to the registry so a restart cannot
lose it) from `send()` until the transcript carries the same text. For a message fed
into a running turn that record is the `queued_command` attachment the CLI writes
when it splices the message in at its next tool boundary. On the SDK route no floor
retires an echo: it retires only when its text lands in a record stamped at or after
the send (a user record or that attachment), or when the CLI dies holding it
(`dropped`). The CLI extracts no image paths on the stream-json route (its only
image-path test belongs to the interactive composer's paste handler), so an image
path in an SDK send lands as typed and the echo's text matches. `_path_bearing` and
the extension set it tests (png, jpe?g, gif, webp, case-insensitive: the CLI bundle's
single image-path test, pinned equal between kernel and backend) remain for the tmux
settle path only, where the paste hook does run and rewrites the path to
`[Image #N]`. The chat's own image previews (`_user_images`) use a separate set,
built from the served MIME table (`_IMG_MIME`, svg and bmp included), so a preview is
never proposed for a file the image route cannot serve. If the CLI dies holding the
message, the echo is flagged `undelivered` and the chat offers copy-to-composer and
dismiss. A kernel restart does not re-run a mid-turn send: the boot duplicate guard
(`_text_landed`) reads the `queued_command` attachment too, and it scans from the
transcript's byte size at the moment of the send (recorded on the echo as `_echo_off`
with the file id `_echo_fsid`, mirrored in the registry as `off` and `fsid`) to the end
of the file, so a landed send is neither re-queued nor flagged as undelivered however
much the session wrote afterwards. A mark from another file (a /clear or a fork
since), a mark past the end of the file, or an echo with no mark reads the whole file.
The guard used to read a fixed 2 MB tail, which suits the lost verdict and not the
landed one: an attachment further back read as never landed, and the resumed CLI ran
the send again. The found verdict is recorded on the echo (`_landed`), and
`prune_live` and the chat merge retire the echo on it without a text match, so a found
echo always has an exit and a later boot never re-scans it. Every by-text comparison
of an echo against a record, the guard's scan, `prune_live`'s retire, the kernel's
`_atom_user_texts` and its folds, the tmux echo's prune (`_tmux_echo_prune`) and the
user-todo answer's landed check (`_paste_landed_texts`, the match set
`_user_todo_answer_lost` reads), uses one key, `echo_text_key` in
`session_backend.py` (outer whitespace stripped, nothing else). The scan used to
collapse inner whitespace while the prune compared raw text against stripped keys, so
a send with a trailing newline was found, hence neither re-fed nor flagged, and yet
never pruned or dismissable. The client keeps its own pending
bubble (dashed, "sending…") from the press until the kernel's payload accounts for
the text (`ui/webview/send-pending.ts`). At the press the bubble is anchored to the
last stable kernel event, and the user events that already carry its text are
recorded as background. Only a user atom that lands after that anchor, with exactly
the sent text, ends the bubble; the scan runs from the anchor to the end of the
resident events, never over a fixed number of tail events, so an absorbed atom placed
a hundred events above the tail still ends it. One landing ends one bubble: two
identical sends in flight end in send order, and a landing of "test the continue
button" leaves a pending "test" alone. The `undelivered` verdict ends the bubble on
the same terms, so resending a never-delivered message is not ended by the old
bubble's verdict. The kernel's echo atom or queued copy is attributed per send, as a
landing is: the k-th copy of the text after the anchor (an echo no earlier bubble
claimed, or a queued copy beyond the count the press saw) hides the k-th bubble with
that text for that push and proves the kernel received that one send. A claimed echo
is background for every later bubble with the text, so one echo confirms one send.
Identical texts carry no identity of their own, so which copy is whose goes by send
order, as it does for landings. The bubble has no lifetime. A connection drop relabels
it "not confirmed" until a copy attributed to it appears or the message lands. The
label is per bubble, so a group holding one dropped send and one in flight reads "not
confirmed · sending…". ✕ removes the bubble it sits on: the entry's press time rides
the button as `data-qts`, and `dropPending` removes that entry rather than the first
entry with the same text. The chat repaints only when a bubble's state changed (a
redial loop while the kernel is down repaints nothing). A send pressed while its tab
is still a placeholder, with no resident frame, is stamped at the first frame instead.
That stamp reads the events' own kernel stamps: only an event stamped before the
press's second is the anchor or background, so the frame's copy of this send (its
echo, or its landed atom when the CLI was idle) is read as the send's own and not as
an older message. The comparison assumes that the client's clock and the kernel
host's agree to the second; `stampBase` states the assumption. The kernel's queued
bubble carries no stamp, so a late stamp presumes that the frame's newest queued copy
of the text is this send's own (one copy per identical send pressed against the same
placeholder frame); without that, a send into a busy or held queue whose first frame
already listed it sat as a second bubble beside the kernel's copy for the whole wait,
and its ✕ would have cancelled the real queued send. The presumption misreads one
case, stated in `stampBase`: an older identical message already in the queue, with
this send not yet received when the frame was built, is read as this send's copy. A
press-time stamp reads no stamp, since its frame predates the press. An
absorbed atom sits at its send time, above the steps that were already
running, so its event carries `absorbed` and `landedAt`, the time the CLI took it:
the repaired timestamp of the attachment's file-order predecessor (the boundary
record the splice waited for), clamped to the send time when it would be earlier.
`landedT` is never before `t`, with no tolerance window: real transcripts invert only
by clock granularity, and anything larger is a shape the CLI does not write. Each
clamp is counted as `landedT-clamp` in the event model's assembly stats, served
beside `ts-repair` in the version route's `parse` dict. The chat shows the time to
the minute. The bubble wears "joined mid-turn", and when the landing retired a pending
bubble at the tail, a cue stays where the bubble was ("delivered into the running
turn at HH:MM", with a jump) until jump or ✕. The cue hangs under the last event the
chat draws in its current mode; compact mode hides thinking, so a thinking record at
the tail is skipped.

**The ledger is a table of contents** (pure projection of captions + archive):
- top: the archiver's one-sentence headline for the session,
- then **turn captions** as top-level bullets, the whole session (not just recent),
- a multi-segment turn expands to its **segment captions** indented beneath,
- click any line to jump to that point in the transcript.

The captioner emits both grains and the event model gives the turn→segment nesting,
so the TOC is free. (Caveat: a live permission prompt's *content* may exist only in
tmux, not the transcript; a live AskUserQuestion/ExitPlanMode is in the tree as an
unanswered tool_use. The chip state comes from `states/` regardless.)

### Feed = top-level-goal cards, nothing else

**The only cards are top-level goals.** One card per top-level goal, bucketed into
the three columns by the rolled-up status the producer already wrote (working /
blocked / completed). A sub-goal never gets its own card: a block anywhere in the
tree rolls UP, so the *top-level card* moves to BLOCKED and its modal shows which
leaf is blocking; likewise a completed step shows inside the modal, not as its own
Completed card. No read-time DAG rebuild, no status derivation, no handoff repair.

- A card's modal shows the goal's trail (its filed segments + sub-goal tree,
  interleaved).
- **No caption stream.** Turn/segment captions are NOT feed cards — they live in the
  card's trail, the ledger, and the timeline. The rule lives in `build_feed`.
- **Card detail**: a card shows its caption trail; a richer expand view is parked.
- **Clear-all + undo**: a button retires every currently-open top-level card at
  once (batch `cleared`); an **undo** restores that batch if invoked right after.
  For sweeping away a stale backlog you know you don't care about.

### Timeline = segments as bars, with connectors and overlays

- **Lanes**: one per session; each **segment** is a bar `[t, end]` (segments are
  exactly "what the timeline draws as a bar" in the event model), a dot at the
  trigger, idle atoms as the not-working gaps, caption on hover.
- **Stripes**: needs-input (a live permission/picker prompt) / compacting, from the state read.
- **Connectors**: postal messages between lanes, from courier records / the message
  log.
- **Overlays**: focus / hover from the feed and chat (UI ephemera, one WS channel).
- Reads **segments straight from the event model**.
- The timeline lives **in `ui/`** next to chat and feed, sharing one view-builder,
  one bundle, one set of types.

## One view-builder

A single read library (TS, in `ui/`) of pure functions `records → ChatView |
FeedView | TimelineView`. One implementation, because there is one front end.

## What stays in the read side

The read side does no meaning-work: no DAG rebuild, no status derivation, no
handoff classification or repair. Those live in Layer 1/2 — the planner un-blocks
via newest-wins, origin is `trigger.author`, the courier classifies handoffs at
write time, captions are keyed by id upstream. The completion rollup, column
derivation, and the settled gate live in Layer 2, leaving the feed to read status.
Recency fade is the one display-only heuristic the read side keeps.

## Comms scope (directory groups, alive-gated)

**Design sketch — not shipped.** What ships today is live-name addressing with
per-host trust tiers (see `SECURITY.md`); the directory-group gate below has not
been built.

At the postal/infra level, below Layer 2, keyed on the working directory. Separate
from view tags.

- Sessions in the **same directory talk freely** (one project). This fits the
  shared-worktree reality: sibling sessions in one checkout are one group.
- **Cross-directory is blocked by default.** The first attempt surfaces an approval
  to the user; approving opens a **group-wide** edge (every session in dir A ↔ every
  session in dir B), not just the two that triggered it.
- The edge is **alive-gated**: it lives while both directories have ≥1 live session
  and tears down when either empties, so it re-asks next time. Event-based, no
  timer. ("Allow personal and work to talk today; tomorrow they're separate again.")
- A **config allowlist** (directory-pairs or tag-pairs) permanently bypasses the
  gate for pairs you always want open.
- **Agent norm**: sessions should not attempt cross-directory messages unless the
  user directs it; an unsanctioned attempt surfaces the approval prompt rather than
  delivering silently or failing silently.

## Tags and views

A tag is a named, colored set of sessions. The kernel stores tags in
`timeline-views.json` (name, color, members, and `tagOrder`, the order the user
has dragged the tags into); a session may carry several, and a tag may span
attached kernels, joined by name. Tags are edited from a tab's context menu, the
timeline's tag table, the picker's **Tags** row, and `romp tag`. They do three
jobs:

- **Filtering.** Each surface (chat tabs, timeline lanes, outline) keeps its own
  lens: every session, the untagged ones, or any set of tags.
- **Grouping.** The chat tab strip sections by tag whenever a session carries
  one: a header per tag in `tagOrder`, each tab under the first of its tags in
  that order (its home tag), the untagged after a divider. Sections fold per
  browser; dragging a header reorders `tagOrder` for every surface; **Move to
  <tag>** in a tab's menu adds the target tag and drops the home tag in one
  click. Groups are tags: there is no second store and no per-session group
  field.
- **Inheritance.** A session spawned from another joins the parent's tags at the
  creation event: a fork, a promoted comment thread, and `romp new` run inside a
  session (it sends its `ROMP_SID` as `parent`; `--no-inherit` withholds it and
  `--in <tag>` adds tags; a thread's `ROMP_SID` resolves to the session the
  thread belongs to). Opening a running session inherits nothing: `/new`
  re-asserts an explicit `--in` on it, while the picker's createSession op
  warns and leaves the running session's tags alone, because its Tags row is a
  prefill from the active tab rather than an ask. A comment thread inherits
  nothing until it is promoted, since it has no tab. Only the local kernel's
  tags are inherited; a parent held only by a remote kernel's tag is a known gap.
  Every writer of the views blob, the WS `setTimelineViews` full-blob write
  included, runs under `_views_lock`.

The exact project directory still defines the **comms group** sketched above.
The directory-to-tag auto-tagging rule and the URL-hash view selection once
planned here did not ship; the per-surface lens took the hash's place.

## The UI progress surface

When the kernel is catching up on a backlog (an old session opened that needs its
goals judged, or a burst of new activity), it is judging segments it hasn't judged
yet. The UI shows a **progress indicator** ("re-judging…", N pending) so the inbox
filling in is legible rather than mysterious. The kernel exposes the
pending-judgment count; the UI renders it.

## Remote kernels + postal federation

- **Each machine runs its own kernel** (its own records, its own indexing). Records
  stay local to the machine that produced them.
- **Postal federates over SSH.** Local and remote sessions share one bus address; a
  remote session tunnels the bus port to the laptop with `ssh -R
  PORT:127.0.0.1:PORT` and heartbeats for presence (`postal/postal_service.py`), so
  messages cross machines.
- **Viewing remote sessions**: shipped as read-federation — link a remote kernel
  and its sessions appear as `host:name` tabs and timeline lanes in the one local
  dashboard, sharing the feed (the guide's "Linking kernels on other machines"
  covers setup).
- **Comms across machines**: gated per host by trust tier (trusted / directed /
  isolated — see `SECURITY.md`), not by the directory-group sketch above.

## Serve-layer security (auth / CSRF hardening)

Binding `127.0.0.1` is not an auth boundary: any webpage the user opens can reach
localhost, and WebSockets are not covered by CORS, so without origin checks a
malicious page can open `ws://127.0.0.1:PORT/ws` and drive the kernel (inject
prompts, spawn/interrupt sessions). This is the ClawJacked class (CVE-2026-25253).
The Python kernel (`kernel/kernel.py`) closes it.

- **Always-on Origin/Host validation (token-independent).** Validate `Origin` and
  `Host` on every HTTP request AND the `/ws` upgrade; allow only the kernel's own
  origin plus known local client origins (the browser at the kernel's host, the
  `vscode-webview://` extension, the timeline), reject everything cross-site. This
  kills ClawJacked for free; legit local clients send the right Origin/Host.
- **Token REQUIRED on every gated route, loopback included** (Jupyter's model:
  loopback is one network stack shared by every local UID, so the `0600` token
  file — not the socket — is the same-user trust boundary; the gate keeps a
  same-host co-tenant out of `/send` and the bus). Accepted forms: `?token=`
  (browser bootstrap, seeds a `SameSite=Strict` cookie so it never re-prompts),
  the cookie, and `X-Romp-Token` (CLI/hooks/daemons, read from the file). The
  token is baked into how the kernel launches (env/autostart), never a manual
  per-launch flag; a bare browser open of `/` gets a paste-the-token login page
  (bare `romp` prints the link + opens a browser). Only the no-side-effect liveness
  probes are exempt (`/healthz`, `/version`, `/busy`; bus `/ping`) so liveness
  never breaks token-less monitors. `tailscale serve` traffic needs the token
  once per device like any browser — and funnel (public internet through the
  same proxy) must still never be enabled for this port, since the token would
  then be the only gate with no device identity in front of it.
- Regression tests: a cross-site `/ws` upgrade with a foreign `Origin` must be
  rejected, and a token-less loopback request to any gated route must 403
  (tests/test_kernel_auth_hardening.py, tests/test_kernel_ws_auth.py,
  tests/test_postal_token.py).

## Naming

- **kernel** — the one always-on core (Layer 1 + Layer 2 + HTTP/WS serving).
- **ui/** — the front-end package (the three panes).
- **Romp Postal Service** — always-on messaging infra, below Layer 2.
