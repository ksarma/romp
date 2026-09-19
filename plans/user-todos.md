# Requests from sessions: what a session needs from you, held until you or it says otherwise

**Status: design settled 2026-08-20/21, re-decided 2026-09-19 (the reviewer's questions and their answers are
worked into the sections below), and built as five stacked changes (see Build segments at the end): A, the
send path's contract; B, the store, the two postal tools, the card and the switch; C, the resume block; D,
the tab flag and the feed marker; E, the idle hold, the nudge and the badge.** The decisions recorded here
are the plan of record. File and line references describe the tree the design was written against and are
not current (see `plans/README.md`); the segments' own tests are the current map. The authority-tier decision
record is a section of this document (The authority tier: the decision record).

## The problem

A session hits a point mid-turn where one strand of its work needs the user, and says so, once, in passing:
it cannot do X without a decision, an input or an action only they can provide, so it notes that and
continues with Y and Z. The session keeps looking busy (the transcript scrolls, the card sits in Working with
a gold pip) and X vanishes. The user learns about it days later, re-reading a transcript, or never (the user
2026-08-20, describing the recurring shape). The lost items come in two kinds, and both matter:

- **Partial blocks**: one branch is stuck on the user while the rest proceeds. In the demo world, the `api`
  session of `notes-api` needs a decision on the auth scheme before it can wire login, so it builds the
  unauthenticated routes meanwhile.
- **Non-blocking wants**: nothing is stuck yet, but the agent needs something eventually: a test
  credential, an opinion on a naming choice, a review of a draft it can keep polishing.

Today the second kind has no representation at all, and the first kind has one that erases itself.

## Why today's machinery cannot see it

Three stacked holes, traced end to end at design time:

1. **Mid-turn, the ask is invisible by construction.** Judges rule on ended segments only (`run_triage`,
   `kernel/judge.py`), and a segment splits only at genuine new inputs (`kernel/event_model.py`), so an
   autonomous work turn is one segment, and the "I can't do X" sentence sits buried mid-segment behind the
   Y/Z work that follows it. While the turn runs, the card shows Working with open-turn narration.
2. **At turn end, the block usually never files.** The planner's block op requires the segment to leave a
   decision owed; a segment that ends on continuing Y/Z work reads as progress and files as `sub` ops.
   There is no verdict shape for "partially blocked": a node is blocked or it is not.
3. **When a block does file, the system erases it.** Every planner placement runs `_unblock_branch`, an
   unblock on the placed node and its whole ancestor chain (why: new work filed on this branch), so a block
   on the card Y/Z files under dies on the next judged segment. A block on a sibling sub survives that, but
   the unblocker re-examines every open block whenever a newer turn ends (`_unblock_session`) and its prompt
   licenses lifting when the work visibly moved past the question even though nobody typed an answer
   (`UNBLOCK_SYS`). The repo documents this erasure class about itself: the `WHY_UNBLOCK_UNSETTLED` design
   note in `kernel/judge.py` records a blocked-on-the-user goal repeatedly flipped back to working by "new
   work filed" and "answered in passing" rulings while the user's decision was still outstanding, and
   `_mark_nudge_failed`'s moot guard in `kernel/kernel.py` exists because of the same weekend. After a lift
   there is no residue: the decision brief is a blocked-card surface and clears with the block. The nudge
   ladder can resurrect the question much later, but only once the session goes idle with a still-working
   card (`_auto_nudge_tick`); while the session stays busy on Y and Z, nothing fires.

None of this is a bug to patch in the judges. They infer from transcript text, and inference over "I'll note
X and continue" will keep failing in both directions: filing blocks that are not real, and lifting ones that
are. What is missing is a channel where the agent states the need explicitly, and where nothing that reasons
by inference is allowed to clear it.

## The design

A **request**: a first-class object a session files when it needs something from the user (a decision, an
input or an action only they can provide) while it keeps working on whatever else it can. It stays visible
until one of exactly three events clears it, none of them a judgment.

### Name and scope

"Request" is the user-facing word on every surface: the card, the gear, the dashboard's warnings, the bus's
texts and the docs (the reviewer's question 3 and the user's answer, 2026-09-19). The code's name is the
older one, "user todo": the store keys, the helpers, the routes, the WS types and the tool names spell it
`user_todo`, `userTodos`, `/usertodo`, `setUserTodos`, `add_user_todo`, `withdraw_user_todo`, and they stay
that way, since renaming them would cost every fixture for no reader's benefit. Internal identifiers never
use `ask`: the feed payload's `asks` field is the card list itself, and a second meaning of the word in the
same payloads would be a collision. Scope is gatekept by the tool description, not by any classifier: partial
blocks and non-blocking wants both qualify; status updates and FYIs never do, since the user already sees
those.

### The channel: two postal tools

Registration rides the postal MCP server (`postal/postal_service.py`), the one tool surface every romp
session holds, wired at the session level with nothing romp-side restricting subagent inheritance. Two tools:

- **`add_user_todo`**: required `text` (one short line: what is needed and why), optional `detail` (longer
  context for when the short line cannot carry it), optional `blocking` (a boolean, default false: true only
  when the agent cannot go on without the answer). Returns a stable id (`ut-` plus 8 hex, minted kernel-side).
- **`withdraw_user_todo`**: takes the id; stamps the request withdrawn. Withdrawing an id that is not open
  returns a plain answer that says what happened, never a silent success, and an error only when the id is
  not the caller's or unknown: a request the person already answered or dismissed, or one the session
  already withdrew, is the need met, not a failure (the route's `state` / `at` / `owner` fields carry the
  account the tool words).

The descriptions follow the veil (sessions do not know romp exists): they speak of "the person you work for"
and name no romp machinery. The shipped wording is pinned by `tests/test_injected_voice.py`, which also
renders every result text of both tools and scans it the same way.

Construction is `set_working`'s shape: one `MCP_TOOLS` schema entry and one `_mcp_call` branch each, backed by
kernel routes (`POST /usertodo`, `POST /usertodo/withdraw`) the way `_publish_working` posts to `/working`.
The bus branches on the kernel's STATUS first: `_kernel_post` returns `{ok: false, status, error}` for a
refusal, so the agent hears the kernel's own reason (the 409 while the switch is off, a 400 for the caps or a
malformed field, a 502 for a remote leg that failed, a 503 for an unreadable store), and `None` only for an
unreachable kernel. The caps are therefore enforced once, at the kernel's writer, and the bus mirrors no
number.

**The subagent caveat, documented rather than fixed:** postal identifies its caller from the CLI process
environment (`CLAUDE_CODE_SESSION_ID`), so a subagent calling the tool files the request as its parent
session. That is the right behavior (the need belongs to the session the user talks to); it means "who filed
this" is always the session, never an individual subagent, and the docs say so.

### The store

A sid-keyed JSON blob under STATE, following the `notify-cards.json` / `session-flags.json` idiom
((mtime_ns, size) cached read, `_atomic_write(..., sort_keys=True)` publish):

```
~/.local/state/romp/user-todos.json
{ "<sid>": [ { "id": "ut-9f2c1a34",
               "text": "Need the auth-scheme decision to wire login; building the open routes meanwhile",
               "detail": "...optional longer context...",
               "blocking": true,
               "createdT": 1755741000,
               "resolved": { "kind": "answered", "t": 1755749200 } } ] }
```

Open means no `resolved` key. Resolution stamps rather than deletes: `kind` is one of `answered` /
`dismissed` / `withdrawn`, so the record carries its own history (created, cleared, by which event).
`blocking` is stored only when the agent set it true (a bare row is byte-identical to one filed before the
flag existed) and copied to the payload row; segment E reads it for the idle hold and the nudge stand-down,
and a non-blocking request, the tool's default, never moves a card. Kernel-side, so it survives session death
and kernel restarts alike. Rows leave the file by exactly two paths, both touching RESOLVED rows only: the
per-sid resolved-history cap at stamp time (`_USER_TODO_RESOLVED_KEEP`, the newest 64 stay, enforced at the one
place every resolved row is born), and the prune that drops a dead session's resolved rows once its death is
corroborated (`_prune_user_todos`, once per housekeeping pass, on a durable death record and never a
display-set miss). The prune holds an `answered` row whose answer's echo is drop-marked in the session's
registry (`_user_todo_losses_pending`): the kill that ends an SDK session writes alive:false before its shutdown
drop-marks the stranded echo and hands the loss to the seam, whose reopen runs on its own thread, and a pass
between the two would otherwise delete the row the seam is about to reopen. An OPEN row never leaves the file
at all, whatever the session's state.

The store guards its own shape, because the switch file is easy to mistake for it. A `user-todos.json` that is
not sid to list (a settings blob, a JSON list, unparsable text) is reported once per file version in the kernel
log, with what was found, and every writer refuses to overwrite that version until the file is fixed or
removed; without the guard, the next register would replace the whole store with a one-row one. The flagged
version is not read as empty on any user-facing surface either: the card carries the cause in place of the
rows, Reply and Dismiss say nothing was sent and nothing changed, the register route answers 503, and a
withdrawal is told the store could not be read (`owner: null`, never "no such request"). The writer bounds a
request (`_USER_TODO_TEXT_CAP` 500, `_USER_TODO_DETAIL_CAP` 4000 characters): over the cap is refused, never
trimmed, and the route's 400 carries the one-line advice the bus relays. Live data only under STATE, never
in the repo, as ever.

### Lifecycle: an authority tier

Exactly three events clear a request:

1. **The user answers**: the Reply on the card. The reply is put into the session as a message from the
   person the agent works for (injected-voice rules apply, no romp nouns), anchored to the request it answers
   so a terse reply lands unambiguously: the request's own line after `Re:`, a blank line, then the user's
   words, pinned by `tests/test_injected_voice.py`. The stamp is **handover-keyed, not gesture-keyed**: an
   answer a live backend accepts stamps when the backend takes it; an answer parked in the kernel's FIFO (a
   compaction, a hold, a queue ahead) stamps when the parked op drains, through the drain's
   `_parked_answer_handed_over` hook; and an answer whose delivery comes undone **reopens** the request. That
   reopen class (`_reopen_user_todo`, the one un-stamp) covers exactly two events: the recall of a still-queued
   answer (the user pulled it back), and the corroborated loss of its holder (`_user_todo_answer_lost`, which
   reopens unless the transcript proves the text landed; `_user_todo_loss_boot_pass` hands the seam every mark whose
   reopen a kernel death cut short). Every leg keys on a delivery event, never a judgment.
2. **The user dismisses**: clears it without a message; nothing is put into the session. For moot and stale
   items.
3. **The agent withdraws**: via the tool, when it got what it needed some other way or the need evaporated.

**What 'answered' records, per backend.** The stamp records a HANDOVER, not a delivery. On the SDK backend,
`SdkBackend.send` returns True once the text sits in the session's queue (or the stood-down mirror), and the
un-delivery events the backend exposes each carry a reopen: the recall (`SdkSession.unqueue` hands back the
entry as its `_TodoText`, the request id riding as its `todo` attribute, on both the id arm every SDK recall
takes and the index arm), the dropped echo (`_mark_dropped_echoes`), the refused echo (`mark_echo_refused`),
the live-overtaken echo (`settle_echoes`) and the rewind-dropped queue head (`_rewind_failed`), plus the boot
pass over persisted drop marks. The id travels WITH the message (the queue entry, its registry mirror and its
echo), never in a kernel-side table, because the queue is persisted across a restart and a table would be
empty. A backend whose `send` takes no `user_todo` (the Codex backend today) receives the answer without its id
and exposes NO un-delivery event, so an answer to a Codex session stamps on the handed-over send and a lost
message there reads answered: the stated cost until that backend carries an id on its queue. A Codex session
also holds no request tools yet; the next step is to add the two request specs to its dynamic tool list and
service them against the kernel's own routes, a decision of its own.

**Judges and the unblocker get no vote.** Nothing in `judge.py` may write this store, a grep-provable
invariant (`NoJudgeWritesTheStore`), and every call of a store writer in `kernel.py` resolves to a def on an
allow-list of event-driven callers (`NoInferenceWritesTheStore`): the routes, the drive handler, the drain's
hook, the recall, the boot pass, the housekeeping prune. The precedent is the agentTask tier: `open_task`
nodes mirrored from the live task store trump a judge or rollup done because we trust the agent's declaration
over inference. Requests are the same move for the other direction of obligation.

The deliberate, stated cost: an agent that forgets to withdraw leaves a moot request sitting visibly until the
user dismisses it. Accepted: a stale visible request costs one glance and one click; a silently vanished ask
costs whatever X was.

### Withdrawal support: how the agent remembers

One mechanism is rejected outright, not deferred: **idle check-in turns**. A scheduled "do you still need all
of these?" turn was weighed and refused (the user 2026-08-20): at idle the common truth is that everything
registered is still waiting, so check-ins would burn a turn per session per idle to say nothing. Three passive
mechanisms carry the load instead:

1. **The tool description instructs withdrawal at registration time**: the agent learns the contract in the
   same breath it files the need.
2. **Open requests ride into the contexts the agent naturally receives.** On SessionStart after a resume, a
   compaction or a clear (the reviewer's question 8, decided 2026-09-19: all three sources; startup and fork
   stay silent, since a fresh sid or a born fork has no rows), the session sees its open requests phrased as
   its own outstanding notes to the person it works for, with ids and an invitation to withdraw any that are
   met or moot. A passive context block, no forced turn. As built (segment C): the hook,
   `hooks/romp-usertodo-context.sh`, checks that the switch file exists before it reads its payload or costs a
   process, so an install that never turned requests on pays nothing per resume (the kernel stays the one
   authority on the file's value, and the route's `enabled` field silences the hook when a present file says
   off); it then applies the postal hooks' identity gate (the CLI's id must be the sid or the SDK registry's
   lastSid for it, a clear passing on the registry row's existence), so a `claude -p` a session runs from its
   Bash tool never takes its parent's requests; then it asks `POST /usertodo/context` (`{"id": <sid>}`,
   answered `{"ok", "enabled", "block"}`; a read-only route on the session's own host: no pusher wake, no
   forward, no liveness gate, the SessionStart being the evidence) and emits the block as additionalContext.
   The kernel renders the words (`_user_todo_context_block`), so `tests/test_injected_voice.py` scans exactly
   what a session receives: newest first, twelve rows (the kernel constant `_USER_TODO_CONTEXT_CAP`, pinned
   equal to the card's cut-off by a test) then an "and N more from earlier" tail, and the one instruction that
   matters, withdraw what is met or moot. The block is
   the fourth deliberate exception to the injected-voice rule (it speaks as the agent's own notes, not as the
   person asking) and `CLAUDE.md` says so.
3. **The user's dismiss covers the rest.**

### Escalation: the idle endgame

While the session still works, an open request changes no card's column: the session is not waiting on the
user, it told them so. The one earned move: **when the session goes idle with an open BLOCKING request and
nothing else dispatched (no open turn, no background work awaited), the request IS the session's frontier**,
and its card escalates to Blocked (needs-input). A non-blocking request never floors a card.

Mechanically this is a read-side floor in the `perm_top` family, NOT a judge verdict: a verdict would land in
the diary the unblocker examines and could be lifted like any other block. A session with no open card gets
a needs-input placeholder, the same way a goal-less permission prompt does. Both directions are event-keyed,
per the card-move rule: the floor arms on the turn-end or await-drain that empties the frontier while a
blocking request stands, and stands down when the request clears or the session starts new work (a message
arrived, the user acted), each a real event, never a per-build re-derivation from a flapping proxy.

**The status nudge stands down for a session whose idle is already explained by open requests**, the same
reasoning as the no-check-ins call: the request already says what a nudge would fish for, and the escalated
card, not a manufactured turn, is the surface. Scoped to the status-nudge branch ALONE: the awaiting WAKE flows
past an open request, because it is the lost-wakeup backstop for dispatched background work, not a status
ask; and the DEBT machinery flows past too, because it is the one mechanism that unparks a peer silently
waiting on this session's answer, and a request says nothing about what a peer needs. The stand-down lifts the
moment the last request clears: answer, dismiss or withdraw, each a real event the gate's store read sees
live.

**The peer-wait stand-down is local-host only, a known limitation, documented not fixed.** The floor reads
its peer-wait input from `_wait_for_graph`, which keeps an edge only when the awaited peer is in THIS kernel's
alive set: an unanswered ask to a federated peer makes no edge, so a session idle on a cross-host reply still
floors as needs-you. The waitingOn chip and the auto-nudge tick's skip inherit the exact same scope, all three
read the same graph, deliberately. Widening `_wait_for_graph` lifts every surface at once. Segment E builds the
floor, the placeholder, the stand-down, the badge and the notification latch.

### Surfaces

**(a) The card by the composer.** The existing transcript-bottom to-do checklist card (`kind:"todo"`;
renderer `renderTodo` in `ui/webview/render.ts`) becomes a shared card with two sections, **the agent's plan**
(the existing checklist, exactly as today) and **Waiting on you** (open requests, oldest first), each
auto-hiding when empty, so today's behavior is unchanged when no request exists. Each row carries its short
text (a row WITH detail wears a small "details" hint after the text and opens on click, a keyed disclosure; a
bare row renders nothing extra), a **Reply** affordance (the answer path above, a small dialog on the confirm
chrome that quotes the request; Enter sends on a fine pointer only, since on a phone Enter is a newline and the
Send button sends) and a **Dismiss** (two clicks, the first arms in place; the arm is keyed by id so it
survives the card's rebuild while the session streams). A row whose answer is parked in the kernel's FIFO
reads **answer queued** in Reply's place until the op drains or is recalled (the reviewer's question 12): the
row stays where it was, and the queued bubble's cancel is where the answer is recalled; Dismiss stays. A
blocking request wears a small dim **blocking** mark after its text, no colour of status. With more than
twelve open rows the twelve oldest stay inline and the rest are hidden behind a keyed toggle, the checklist's
completed-bulk idiom (the reviewer's question 11, decided at twelve), so a runaway store never floods the card; twelve
is the number the resume block hides beyond, one number for both. Two different things share this card on
purpose: the agent's plan for itself, and the agent's requests of you; the vocabulary below keeps the terms
apart. Both removal sites (Reply sent, Dismiss confirmed) drop the row optimistically and recount the heading;
the kernel's warn re-syncs the view when a removal was refused.

**(b) The tab flag.** A session tab with open requests carries a small, non-numeric mark. Precedent: the
per-tab context gauge and the compacting mini-bar; tabs deliberately carry no counts and this stays that way.
The flag says "something here waits on you", the card says what. Segment D.

**(c) A quiet feed-card marker.** Each of the owning session's feed cards carries a quiet marker (requests
are session-scoped, not card-scoped). **No feed strip in v1**: the feed's banner slot stays single-purpose.
Segment D.

**(d) The app badge.** `_needs_you_count` widens to one number for "things only the user can move": open
requests (of non-ended sessions) plus hard-stopped needs-input sessions (the permission-prompt class stays in;
the author confirmed, 2026-08-20). Dedup rule: the escalation floor is a presentation of requests the count
already includes, so an idle session escalated by its requests adds nothing extra; a session hard-stopped for
another reason counts once as itself. Per-item decision cards count per CARD, not per session. Segment E.

**Muted sessions, a deliberate asymmetry.** A `hideFromFeed` mute quiets the feed and every aggregate built
from it (the card marker, the idle-escalation floor and the badge), because mute means "stop interrupting me
about this session". The card (a) and the tab flag (b) stay: they read the chat payload's `userTodos`, which
mute does not touch, so the session's own tab remains truthful about what it holds.

### Dead and dormant sessions

Two different "not running" states, two different answers:

- **Dormant** (registry alive, no live thread, as after a kernel restart): the session is still addressable,
  its requests show everywhere, and answering one works: the send path revives a dormant session with its
  history intact.
- **Ended** (registry `alive: false`, or, for a session with no registry row, a durable death record under
  `STATE/gone` that no newer states row supersedes): the requests persist in the store but **hide** from every
  surface and every aggregate. Hidden, not cleared: revive the session and they return with it. A dead
  session's requests should neither nag from beyond the grave nor be silently lost. Reply refuses a dead
  session loudly instead of sending into the void.

## The per-install switch, off by default

Everything above is switchable per machine, and requests get their own switch, independent of task tracking
(the user's decision, 2026-09-19): the card and the tab flag work with tracking off by construction, since
`build_session` runs while the feed is replaced by its off frame, while the feed marker, the badge and the idle
hold wait for tracking, and the gear's row says which. `STATE/user-todos-enabled.json` (`{"enabled", "gt"}`,
the thinking-summaries idiom: gesture-clock stand-down, settingStale reply, atomic write, a refused write told
on the socket) holds the answer, the gear's **Requests from sessions** checkbox (Settings, Sessions, Requests)
flips it, and `/version` reports it top-level as `userTodos`. Only a literal `true` turns it on: absent reads
off silently (the shipped default), and a present file of any other shape (unparsable text, a list, the string
"false", `enabled` null or 0) reads off and is said once per file version in the kernel log and the bus's log.
The kernel's reader is memoized on the file's (mtime_ns, size), so the surfaces that consult it per build or
per frame (the card, the routes, the drive ops, the two chatTail frames) pay one stat each; the setter drops
the memo after its own write. It is deliberately not a federation `KERNEL_SETTING`: each kernel keeps its own
copy, and the choice is never proposed or pinned across machines.

While off, every surface refuses and says so: `POST /usertodo` and `/usertodo/withdraw` answer 409 with one
plain line; `userTodoAnswer` and `userTodoDismiss` answer with a warning toast that names the switch; the postal
bus leaves the two tools out of `tools/list` and refuses a call anyway before any post; and `_open_user_todos`,
the one gated store read, returns `[]`, so the card ships no rows with no client logic, and the chatTail frames
carry no `userTodos` key at all, so an install that never turned the feature on ships byte-identical deltas.
The store is untouched by the switch: rows filed while it was on stay on disk and reappear when it is turned
back on, and a boot notice counts the open rows stored behind an off switch. The stdio server declares
`tools.listChanged` and polls the switch file on a thread of its own (one stat per tick, two seconds by default,
`ROMP_POSTAL_SWITCH_POLL`; a malformed value falls back to the default and is said once), so a connected session
is told to re-list on a flip and gains or loses the two tools without a restart.

## The authority tier: the decision record

Status: decided 2026-08-21, written 2026-09-07, moved into this plan 2026-09-19 (the project keeps its design
records under `plans/`).

A request (a need an agent files with the user while it keeps working) is cleared by exactly three events:
the user answers it, the user dismisses it, or the agent withdraws it. The judges and the unblocker get no
vote: nothing in `kernel/judge.py` may write the request store. We chose this because every mechanism that
reasons about blocks by inference has demonstrably erased this exact class of ask; the repo documents it about
itself (`WHY_UNBLOCK_UNSETTLED`, `kernel/judge.py`): blocked-on-the-user goals repeatedly flipped back to
working by "new work filed" and "answered in passing" rulings while the user's decision was still outstanding.
An object whose whole purpose is to survive that inference cannot be clearable by it.

**Considered options.**

- Teach the judges to file and preserve partial blocks. Rejected: judges infer from transcript text, and
  inference over "I can't do X, continuing with Y" fails in both directions, filing blocks that are not real
  and lifting ones that are. Tuning prompts moves the error rate; it cannot make an inference layer
  authoritative.
- Let judges clear requests they deem moot. Rejected for v1; preserved as a deferred option in the weaker
  form of a judge-suggested mootness rendered as a one-click confirm for the user: a suggestion, never a
  clear.

**Consequences.**

- The vanishing stops: once a request is visible, it stays visible until an accountable actor (the user, or
  the agent explicitly) says otherwise.
- The stated cost: an agent that forgets to withdraw leaves a moot request sitting until the user dismisses
  it. The cost is taken deliberately: a stale visible request costs a glance and a click; a silently vanished
  ask costs whatever was asked. Withdrawal is supported passively (the tool description's contract, open
  requests re-surfaced in the contexts the agent naturally receives after a resume, a compaction or a clear),
  never by scheduled check-in turns, which were rejected as noise: at idle the common truth is that everything
  registered is still waiting.
- The precedent generalizes: this is the second authority tier, after agentTask nodes (an agent's open task
  vetoes an inferred done). Any future mechanism that can move cards must treat authority-tier state as
  read-only evidence, not something to rule on.
- The 'answered' stamp is a handover, per backend (Lifecycle above): on the SDK backend every un-delivery
  event carries a reopen; on a backend without an id on its queue a lost answer reads answered, the stated
  cost until that backend carries one.

## Data seams

Three seams, all existing patterns:

- **Chat page**: `build_session` grows a `userTodos` field: open requests only, sorted by `createdT`, store
  values plus the `queued` mark (which moves only when a parked op parks or leaves). The client merges it
  through the upsert's prev-fallback pattern in `render.ts`, and the same rows ride ON the to-do event,
  because the chat wire's steady state is chatTail deltas, which re-send changed EVENTS only; the chatTail
  frames attach the field while the switch is on. **The stability caveat, by name**: `_send_client` dedups by
  comparing the serialized payload (the `firstSeen` lesson), so this field must serialize identically across
  builds when nothing changed. The chat signature keys the sid's own rows, the switch and the flagged-store
  state under `usertodos`, so a register, a stamp, a reopen, a flip or the store going bad rebuilds exactly the
  owning tab; the parked mark reads the sid's ops, which the `ops` component already keys.
- **Feed page**: `build_feed`'s return grows a top-level sid-keyed open-count map for the card marker, and the
  escalation floor and placeholder live in the same column mapping the perm floor uses (segments D and E).
- **Shell**: no new seam; the widened count rides the existing badge WS (segment E).

## Build segments

Five stacked changes, each shipping with its tests, per the standing rule.

**Segment A: the send path's contract.** A message can carry the id of the request it answers: a seventh
parked-op slot (`_op_todo`), `user_todo` on `_send_or_park` and `_send_with_id`, the SDK queue entry
(`_TodoText`), its registry mirrors and its echo, the `todo_lost` constructor seam at the four loss sites, and
the drain's handover reported once through `_parked_answer_handed_over`, a no-op until B. No consumer, nothing
on the board changes.

**Segment B: the store, the tools, the card and the switch.** The store and its helpers, the two postal tools
and their routes, the card's second section with Reply and Dismiss (the parked Reply's "answer queued", the
blocking mark, the cut at twelve), the handover-keyed stamp on A's hook, the recall reopen on both unqueue
arms, the loss seam and its boot pass wired through A's constructor keyword, and the per-install switch with
its gear row, off by default and inert while off. A self-contained capability inside romp's existing model:
it moves no card and calls no judge.

**Segment C: memory across context loss.** The SessionStart hook (sources: resume, compaction and clear; the
switch file's existence checked before any round trip, then the postal hooks' identity gate), its read-only
route and the rendered context block, in the agent's-own-notes voice (the fourth exception to the
injected-voice rule), installed and uninstalled with the other hooks; the block's cut at twelve is the
card's cut-off number, a kernel constant a test pins equal to the card's literal.

**Segment D: ambient visibility.** The tab flag, the feed-card marker and the phone tab's flag, all reading the
fields B ships, all quiet while the switch is off.

**Segment E: the idle endgame.** The escalation floor on blocking requests with its arm record and
placeholder, the status nudge's stand-down, the widened badge with its no-double-count rule, the OS
notification latch (a lost answer's reopen un-latches its id), and the prune's disarm of a dead session's
record. The one segment that moves cards, on a read-side floor keyed to events, never a judge verdict.

## Judges: no vote now, a suggestion later

Explicitly deferred, not in v1: **judge-suggested mootness**. A judge that notices a request looks answered or
overtaken could suggest clearing it, rendered as a one-click confirm for the user on the request itself, never
an auto-clear. Deferred because v1's worth is measured by how much the user trusts the invariant that a visible
request is still real until they or the agent clear it; a suggestion channel is only safe to add once that
trust exists, and it changes no store semantics when it comes.

## Deliberately not in v1

A feed strip or column for requests (the marker and the escalation carry it); a cross-session digest of every
open request (the tab flag, the feed marker and the badge carry it); idle check-in turns (rejected outright, not
deferred); numeric counts on tabs; editing a request's text (withdraw and file again); priorities, deadlines
or ordering beyond creation time; per-request Web Push (the badge and the existing needs-input push cover the
phone); a Dismiss undo (a dismissed request is history the store keeps, and an undo is a reopen of a dismiss,
which the authority tier's reopen rule reserves for a failed delivery; it needs its own decision); the judge
mootness suggestion (deferred above); request tools for Codex sessions (the next step named under Lifecycle).

## Vocabulary

The terms this feature adds, with the words to avoid because they already mean something else in this repo.

**Request**: the user-facing word on every surface (the card, the gear, the warnings, the bus's texts, the
docs) for a need an agent files with the person it works for, a decision, an input or an action only they can
provide, held open while the agent keeps working on whatever else it can. Cleared only by answer, dismiss or
withdraw; never by inference. **User todo** is the code's name for the same object (the store, the helpers,
the routes, the WS types, the tool names) and appears in no user-facing string.
*Avoid in code identifiers*: ask (the feed payload's `asks` field already means the card list), user task.

**Answer**: the user clears a request by replying to it; the reply is put into the session as a message from
the person the agent works for. One of the three clearing events.
*Avoid*: resolve, respond.

**Dismiss**: the user clears a request without a reply, for moot or stale items. Nothing reaches the session.
One of the three clearing events.
*Avoid*: clear (already means removing a card from the feed), delete.

**Withdraw**: the agent takes back its own request, by id, when the need was met some other way or went moot.
The only agent-side clearing event.
*Avoid*: cancel, retract, recall (already means unsending postal mail, and the queued bubble's cancel of a
still-queued answer).

**Blocking**: the agent's own word that it cannot go on without the answer; the flag the idle hold reads. A
request without it is what the tool files by default.

**Escalation**: the single card move a blocking request can earn: when its session goes idle with one open
and nothing else dispatched, the request is the session's frontier and the card enters the Blocked column.
While the session works, requests never move a card.

**Authority tier**: a class of state the judges and the unblocker cannot clear; only designated actors can.
agentTask nodes were the first (an agent's open task vetoes an inferred done); requests are the second
(cleared only by answer, dismiss or withdraw).

A related pre-existing term, kept distinct on purpose: **the agent to-do checklist**, the agent's own plan for
itself, the mirror of Claude Code's live task store, rendered as the transcript-bottom checklist card and as
authority discs in a card's tree. A different thing from a request: the checklist is what the agent owes the
work; a request is what the user owes the agent.
*Avoid*: todo card (ambiguous), plan card.
