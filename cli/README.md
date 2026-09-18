# cli/ — terminal tools

Python implementations of the terminal-facing romp commands. Run them via
their `bin/` symlinks (`romp version`, `romp update`)
— see `bin/README.md` for the command surface.

| File | Command | What it is |
|---|---|---|
| `version.py` | `romp version` | Version report across the moving parts (working tree vs running kernel vs built bundles). |
| `update.py` | `romp update [host]` | Pushes this machine's committed romp to attached remote kernels over ssh and restarts them. |
| `spend_rebuild.py` | `romp spend-rebuild` | Recounts the token columns of the spend ledger (`spend.json`) from the transcripts' own per-call usage — the recorder mis-diffed the CLI's per-turn `usage` until 2026-09-06. Dollars and turn counts untouched; dry run by default, `--apply` writes and keeps a backup. |
| `perf_export.py` | `romp perf export --public` | Writes one paste-safe copy of the kernel's `GET /perf` counters (or of a saved `romp perf --json` snapshot, `--from`) as `perf-exports/perf-export-<YYYYMMDDTHHMM>.json` under the state directory, mode 0600; `--usage` adds session and feature counts; the flag is required, there is no raw mode. |
| `perf_upload.py` | `romp perf upload <file>` | Sends one export written by `romp perf export --public` to the configured receiver (`--receiver`, else `ROMP_PERF_RECEIVER`, else `~/.config/romp/perf-receiver`), after checking the file again as it stands and asking for a yes on a terminal (`--yes` is the agent's form; no setting stands in for it); one POST, a `201` receipt the only answer accepted, every other answer refused by its status code or error class alone. |
| `perf_public.py` | (imported) | The public shape shared by `romp perf export --public`, `romp restart-metrics --json --public` and the served-snapshot invariant test: the browser's `ident` grammar over every key and string (else `other`), the kernel's route register for the `http` block, the joined-identifier tables, the denylist (every absolute clock stamp among it), the two coarsenings (the uptime to whole minutes, the memory-fraction bounds up to a power of two), the invariant walk and the identifier scan. The form is paste-safe, not unlinkable: measurements stay. |
| `restart_metrics.py` | `romp restart-metrics` | What kernel restarts do to the sessions, read from the state ledgers and the kernel's routes; `--json --public` applies `perf_public.py`'s shape to the document (no session name, id, pid, scope, label or absolute clock stamp; paste-safe, not unlinkable: durations and counts stay). |
