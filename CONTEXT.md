# romp

romp lets one person direct many concurrent agent sessions by spending their attention where
it counts. This file pins the project's ubiquitous language — definitions only, no
implementation. Seeded 2026-08-21 with the user-todos vocabulary plus the pre-existing terms
it leans on.

## Language

### User todos

**User todo**:
A need an agent registers with the person it works for — a decision, input, or action only
they can provide — held open while the agent keeps working on whatever else it can. Cleared
only by answer, dismiss, or withdraw; never by inference.
_Avoid_: ask (the feed payload's `asks` field already means the card list), request, user task

**Answer**:
The user clears a user todo by replying to it; the reply is injected into the session as a
message from the person the agent works for. One of the three clearing events.
_Avoid_: resolve, respond

**Dismiss**:
The user clears a user todo without a reply — for moot or stale items. Nothing reaches the
session. One of the three clearing events.
_Avoid_: clear (already means removing a card from the feed), delete

**Withdraw**:
The agent takes back its own user todo, by id, when the need was met some other way or went
moot. The only agent-side clearing event.
_Avoid_: cancel, retract, recall (already means unsending postal mail)

**Escalation**:
The single card move a user todo can earn: when its session goes idle with open user todos
and nothing else dispatched, the todo is the session's frontier and the card enters the
Blocked column. While the session works, todos never move a card.

**Authority tier**:
A class of state the judges and the unblocker cannot clear — only designated actors can.
agentTask nodes were the first (an agent's open task vetoes an inferred done); user todos are
the second (cleared only by answer, dismiss, or withdraw).

### Pre-existing attention vocabulary

**Agent to-do checklist**:
The agent's own plan for itself — the mirror of Claude Code's live task store, rendered as
the transcript-bottom checklist card and as authority discs in a card's tree. A different
thing from a user todo: the checklist is what the agent owes the work; a user todo is what
the user owes the agent.
_Avoid_: todo card (ambiguous with user todo), plan card

**Needs-input (the Blocked column)**:
The feed column meaning a decision only the user can make is outstanding. Waiting on a peer,
a build, or another session is not needs-input. `needs_input` is the payload value; Blocked
is the column header.

**The veil**:
Sessions don't know romp exists. Every message romp injects speaks as the person the agent
works for, and romp nouns (card, board, column, goal, nudge) never reach an agent; the few
exceptions are deliberate and enumerated in `CLAUDE.md`.
