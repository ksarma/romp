# Oversight supervisor — project

**A romp project** (in this fork), split out 2026-08-13 from the
devbox-maintenance work it was originally scoped under — it has no
devbox-specific surface; everything it does is romp (session transcripts, the
kernel control surface, romp state files). This file is its complete home:
status, the policy decisions, the verified design, the build plan, and the
resume point.

## Start here (for the session that owns this project)

1. Read this file top to bottom — it is self-contained (status, policy, the
   recon findings, the design, build plan, open questions).
2. Read `~/code/devbox/claude/CLAUDE.md` for standing research context (scope,
   and the block-handling policy this project operationalizes); it auto-loads
   if installed at `~/.claude/CLAUDE.md`.
3. You run on ksarma's devbox and observe the romp kernel + session
   transcripts described under "What the recon established." You are **not**
   the devbox-maintenance session — that role is separate and has its own
   handoff (`~/code/devbox/docs/HANDOFF.md`). This project is yours alone.

## Project status

- **State: PARKED** by ksarma (2026-08-13) after design + recon completed. Not
  built; no code written.
- **Owner:** ksarma. **Driver when active:** this project's own dedicated
  session (split from devbox-maintenance 2026-08-13).
- **Resume point:** Phase 0 — the read-only monitor (see Build plan). Needs
  ksarma's explicit go before any intervention (Phase 1) code.
- **Policy evolution** (converged with ksarma 2026-08-13): began at "treat any
  block as the agent's wrong turn → redirect," refined to the
  diagnose-then-branch policy below — a block that traces to an approved safe
  objective means change the *approach*, not the wording; otherwise abandon or
  escalate. Loop control is **per-incident**, not per-session; the watch list
  is **opt-in only**; the redirect mechanism structurally cannot circumvent
  (the rewound turn re-runs on Fable, so it must be genuinely different work).

## Purpose

A standing supervisor that watches our AI-safety research sessions and, when a
session is downgraded Fable→Opus because Fable's content classifier blocked a
turn, treats that block as an **oversight signal to heed**: it rewinds the
session past the drift and steers it back onto safe ground, or escalates to
ksarma. This is about *heeding* oversight, not circumventing it.

### Philosophy (from ksarma, this is the spec)

Our research scope is deliberately narrow and safe (mental-health and
character work), pursuing vetted safe high-level objectives. Given that:

- A classifier block means something about the current **approach** triggered
  it. Diagnose first, then branch:
  - **Traces to an approved, in-scope safe objective** → false positive on the
    approach, not the goal. Change the *approach* (a genuinely different
    method/direction) and reach the same safe objective that way.
  - **Cannot be tied to an approved safe objective** → the block caught real
    drift. Abandon that direction; redirect or escalate.
- The guardrail that separates the first case from evasion: the change must be
  a real change in **what** the agent does, not just **how** it phrases it.
  Re-wording the same objective to slip identical work through is evasion —
  never the goal. Whether a block was a genuine false positive is ultimately a
  human judgment call.
- Never switch to a weaker model to get "unblocked."

See also the standing-context file `~/code/devbox/claude/CLAUDE.md`.

## What the recon established (romp internals)

Full map: workflow run `wf_59ade8bf-38c` (4 readers + adversarial verifier,
read-only). Load-bearing findings, all confirmed against code:

### Detection — one event covers both triggers

The Fable→Opus downgrade AND the classifier block are the **same event**: a
transcript record `type:"system"`, `subtype:"model_refusal_fallback"`, written
to the session's `.jsonl`. Live phenomenon here (19 real occurrences in the
corpus, all `claude-fable-5`, all `apiRefusalCategory:"cyber"`). Fields:

- `originalModel` / `fallbackModel` — the downgrade
- `apiRefusalCategory` + `apiRefusalExplanation` — the classifier's own reason
- `refusedUserMessageUuid` — the exact user turn to rewind to (pre-drift)
- `retractedMessageUuids` — the discarded assistant tail

**romp parses this record for display but discards the anchor fields**
(`kernel/event_model.py:950-963` keeps only content/fallback_from/fallback_to;
the WS chat event keeps only from/to/md at `kernel/kernel.py:11736-11742`). A
grep for `refusedUserMessageUuid`/`retractedMessageUuids`/`apiRefusalCategory`
across `kernel/` and `bin/` returns zero hits. **So the supervisor MUST read
the raw `.jsonl`** to get the rewind anchor.

Session → transcript mapping: session name → sid via
`~/.local/state/romp/sdk/<sid>.json` (or `GET /sessions`), then use the reg's
**`lastSid`** (NOT `sid` — they differ after a `/clear`) for the filename:
`~/.claude/projects/<cwd-slug>/<lastSid>.jsonl`, where cwd-slug is the realpath
with non-alphanumerics → `-` (`kernel/sdk_backend.py:164-170`).

Backstop for the untested hard-block case (fallback disabled, or fallback
model also refuses — 0 occurrences on this box, and romp has no
`stop_reason=="refusal"` handler): watch `states/<sid>.jsonl` for
`retriesGaveUp`/`errorKind` (`kernel/sdk_backend.py:525-538`). Any
unrecognized block shape → escalate to human, never guess.

### Action — all primitives exist, no romp change needed for v1

- **Rewind**: SDK-only, in-place branch via `--resume-session-at <uuid>` (no
  truncation). `rewindSend(uuid, text)` rewinds and injects the redirect in one
  op. Kernel path `_rewind_send` (`kernel/kernel.py:10072`) →
  `SdkBackend.rewind` (`kernel/sdk_backend.py:3491`) → `_arm_rewind` (`:3510`)
  → `_options` sets `extra_args={"resume-session-at": …}` (`:3167-3188`).
- **No "pause" freeze exists.** Use `/interrupt` (HTTP `kernel/kernel.py:20812`)
  to stop the in-flight turn. Ordering constraint: rewind is refused while
  busy (`_ops_gate` `:10598`, `_arm_rewind` guards `:3514-3517`), so the
  sequence must be **interrupt → poll `/sessions` for idle → rewind**.
- **Headless control**: rewind/setModel are WebSocket-only ops (`_drive`
  `ID_OPS` `kernel/kernel.py:4204-4206`), reachable with just the 0600
  serve-token (`_authorize` bypasses the Origin gate for a token-bearing
  non-browser client, `:20207-20238`). No HTTP/CLI route for rewind exists;
  either open a `/ws` client or add thin POST routes (`/rewind`, `/setModel`).
- **Escalate**: `/deliver`/postal, but isolation-gated and a refusal is FINAL,
  so a non-postal fallback is required (durable working-note via `/working`,
  and/or push).
- **Template**: `_auto_nudge_tick` (`kernel/kernel.py:1552-1974`,
  `:17375-17376`) is already a server-side detect→act loop that runs with no
  browser open — the architecture this extends.

### The integrity constraint (enforced by the mechanism)

The rewound replacement turn runs on the **chosen model alias — still Fable**
(the Opus swap was only a per-connection live fallback;
`kernel/sdk_backend.py:3161-3162`). Consequences:

- Rewinding and re-sending the **same** flagged prompt re-runs it on Fable and
  re-trips the classifier → infinite loop AND circumvention.
- Therefore the replacement MUST be a genuinely different, safe task, and the
  supervisor must NEVER `setModel` back to Fable to retry the flagged request.
  The redirect is a fixed steering message + the diagnosis, never a reworded
  prompt. This makes evasion structurally impossible — the "genuine change,
  not rewording" guardrail is enforced by the mechanism, not just policy.
- The drift turn has **already completed on Opus** by the time the record
  lands. You cannot pause mid-drift; you can only rewind it away afterward.

## Design

### Detect → act sequence (per enrolled session)

1. Tail the session's transcript `.jsonl` for a new `model_refusal_fallback`
   record (backstop: `retriesGaveUp` in `states/<sid>.jsonl`).
2. Capture the diagnosis: category, explanation, `refusedUserMessageUuid`,
   `retractedMessageUuids`, and the refused user turn + preceding drift.
3. `/interrupt` → poll `/sessions` for idle.
4. Over `/ws`: `rewindSend(uuid=refusedUserMessageUuid, text=<redirect>)`. The
   redirect is a steering message: "this direction tripped our oversight
   classifier (category X); per policy, drop it and either take a
   clearly-different safe approach toward [approved objective] or stop and wait
   — flagged for ksarma." Never a paraphrase of the flagged prompt.
5. Log the incident (structured) and escalate per the budget below.

### Loop-breaking: per-INCIDENT budget (not per-session)

The budget tracks a **local area**, not the session's whole life — a
long-running session that hits an early block, recovers, and hits an unrelated
block much later must not treat the second as "strike 2."

- An **incident** = a local cluster of blocks: blocks a few turns apart, and/or
  sharing `apiRefusalCategory`, and/or rewinds landing near the same anchor.
- Budget per incident: **1** redirect (ksarma's call, revisit with data). A
  block that recurs **within the same local area** is the hard-to-avoid-region
  case → **immediate halt + escalate**, no more rewinding.
- The incident **resets after recovery** (session moves on / N clean turns past
  the region); a later unrelated block starts a fresh incident with a fresh
  budget.
- This makes looping structurally impossible: repeated blocks in one spot
  produce at most one redirect before a human is pulled in.

### Halt must actually halt, and fail safe

On budget-exceed / same-region recurrence: `/interrupt` and leave the session
idle (no re-injection), set a loud durable flag, notify ksarma. If escalation
can't reach ksarma (postal isolation refusal is final), **leave the session
halted** — never resume because escalation failed. Fail safe toward stopping.

### Protected set: explicit opt-in only

The supervisor watches **nothing** unless a session is explicitly enrolled in a
watch list. Belt-and-suspenders: it refuses to act on itself even if enrolled
by mistake. This also moots the "don't eat itself" problem for infra/meta
sessions (they simply aren't enrolled).

### Persistence

The per-incident counters and watch list live in **state files**, not memory —
a supervisor restart must not reset counts and silently re-enable looping
(background monitors don't survive restart; files do).

## Build plan

- **Phase 0 — read-only monitor (start here).** Discovers enrolled sessions,
  tails transcripts for `model_refusal_fallback` (+ `retriesGaveUp` backstop),
  writes a structured incident log with all diagnosis fields. Takes NO action.
  Zero risk; validates the signal on live events; produces the base-rate and
  incident-shape data needed to calibrate the "local area" window and the
  redirect budget.
- **Phase 1 — intervention.** Adds interrupt → rewind → redirect with the
  per-incident budget, halt-and-escalate, opt-in watch list, and self-exclusion.
  Behind an explicit enable flag. Only after Phase 0 has proven detection and
  ksarma approves.
- **Phase 2 (optional) — romp code.** Thin POST routes (`/rewind`,
  `/setModel`) or an in-kernel detector in the `_auto_nudge_tick` tick, as a PR
  against the fork, if preferred over an external WS client.

## Open calibration questions (need Phase 0 data)

- The "local area" window — how many turns count as the same incident.
- What "recovery" looks like — clean turns / progress before an incident resets.
- Whether the redirect budget of 1 holds once we see the real base rate.
- Hard-block (no-fallback / double-refusal) record shape — unobserved on this
  box; confirm behavior if it ever occurs.
