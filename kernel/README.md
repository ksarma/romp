# kernel/ — the always-on core

The Python backend: one process (`kernel.py`) that reads every session's Claude
Code transcript, builds the event tree, runs the judges, drives the session
backends, and serves the six panes over HTTP + WebSocket on `127.0.0.1:29855`.
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

Two key sources, one switch (`docs/reference.md`, "API keys on disk: the file
mode" and "Installing without keys on disk"):

- `keysource.py` is the file source: where an installation keeps an
  `ANTHROPIC_API_KEY=` line in `service.env`, it is re-read at every session
  launch so a rotation there needs no manager restart. `cli/keyswap.py` (`romp
  keyswap`) loads the same module to read and fingerprint that line, so the
  two cannot disagree about the path or the parse. This fork does not write API
  keys to files: the named swap that would write the line is refused in this
  mode.
- `envsource.py` is the command source, selected by `ROMP_CREDENTIAL_COMMAND`:
  the kernel runs that command with the selector file's token as `$1` and
  merges the `NAME=VALUE` set it prints into every session CLI's launch
  environment, every judge call's and the catalog fetch's, never into its own
  environment or a file. The set is event-cached (invalidated by a refresh, a
  cycle or an authentication failure; a failed run keeps the previous set),
  concurrent readers coalesce on one run, and every function but the one
  injection accessor is value-free. The same module fingerprints the configured
  `apiKeyHelper` when the set carries no key, so a cycle converges on it.
  `sdk_backend.key_source_verdict` checks the configuration once at boot;
  `/api-health` reports it as `keySource`; `/keycycle` drives `romp keyswap`.

A key value never lands in the kernel's own environment and never reaches a
log — the sha256 head (`fingerprint()`) is the only renderable form.

Everything here is loaded by file path (`SourceFileLoader`), not installed as a
package — the repo runs straight from a git clone. Python tests live in
`tests/test_*.py`.
