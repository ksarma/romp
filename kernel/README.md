# kernel/ — the always-on core

The Python backend: one process (`kernel.py`) that reads every session's Claude
Code transcript, builds the event tree, runs the judges, drives the session
backends, and serves the four panes over HTTP + WebSocket on `127.0.0.1:29855`.
Spawned by `bin/romp-serve` (the `bin/romp-kernel` symlink points here); see
`docs/architecture.md` for the data-flow picture.

Layered bottom-up:

| File | Layer | What it is |
|---|---|---|
| `event_model.py` | 1 | Transcript JSONL → event tree (atoms / segments / turns). The schema is pinned in `docs/event-model.md`. |
| `judge.py` | 2 | The judge engine + every judge prompt (captioner, archiver, planner, …). Writes the durable records (captions, archive, goal tree). `docs/judges.md`. |
| `kernel.py` | 3 | The read side: selects and displays what the layers below computed — HTTP + WebSocket server, pane payload builders, session lifecycle, nudges. `docs/read-side.md`. |

Session control (how romp drives Claude Code) sits behind one seam:

| File | What it is |
|---|---|
| `session_backend.py` | The `SessionBackend` ABC — the single interface both backends implement (guarded by `tests/test_session_api.py`). |
| `sdk_backend.py` | The Agent SDK backend (current default): an exact, event-based control channel. `docs/sdk-backend.md`. The tmux backend lives inside `kernel.py` (`TmuxBackend`). |
| `askparse.py` | tmux backend only: recovers the AskUserQuestion picker from a captured pane (SDK sessions get it natively). |

Shared lookup tables: `colormap.py` (recency tints, single source shared with
the web bundles) and `palette.py` (session-identity colors).

`keysource.py` selects the manager's live API key source: a credential command
(`ROMP_CREDENTIAL_COMMAND=<shell command>`), a
`ROMP_API_KEY_REF=op://vault/item/field` reference, or a legacy
`ANTHROPIC_API_KEY`, in that order of precedence. Source inspection is separate
from resolution so UI/status reads do not fetch secrets. A selected reference is
resolved with `op read --no-newline` for each Claude session launch/reconnect,
key-billed judge call, and direct model-catalog refresh. Explicit cycle checks
also resolve the key to detect rotations; a reconnect resolves it again at
launch. Resolved provider keys are not cached or written to disk. Resolution
failures fail closed. `cli/keyswap.py` (`romp keyswap`) shares the path and
parser to switch commands, references or legacy keys without resolving them.
Removing a service-file source cannot restore a stale startup key. See
`docs/reference.md` for migration and service authentication setup.

`envsource.py` is the command kind's runtime; the reference is that kind's
built-in default (`docs/reference.md`, "A credential command"). It runs the
selected command with the selector file's token as `$1`, parses the
`NAME=VALUE` set it prints, holds the set in one private dict, and lets it out
only for merging into a child's environment: every session CLI's launch options,
every judge call's environment and the catalog fetch's header, never its own
environment or a file. The set is cached on events (a refresh, a cycle, a
switch, an authentication failure, a selector-file edit, a change of source),
concurrent readers coalesce on one run, and a failed run keeps the previous set.
Every function but the value-bearing accessors is value-free. The same module
fingerprints the configured `apiKeyHelper` when the set carries no key, so a
cycle converges on it. `sdk_backend.key_source_verdict` checks the
configuration once at boot, `/api-health` reports it as `keySource`, and
`/keycycle` drives `romp keyswap`. `keysource.py` reaches it only through
`keysource.COMMAND_RESOLVER`, so `envsource.py` loads `keysource.py` and never
the reverse.

Everything here is loaded by file path (`SourceFileLoader`), not installed as a
package — the repo runs straight from a git clone. Python tests live in
`tests/test_*.py`.
