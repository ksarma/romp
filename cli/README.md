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
| `perf_public.py` | (imported) | The public shape shared by `romp perf export --public`, `romp restart-metrics --json --public` and the served-snapshot invariant test: the browser's `ident` grammar over every key and string (else `other`), the kernel's route register for the `http` block, the joined-identifier tables, the denylist, the invariant walk and the identifier scan. |
| `restart_metrics.py` | `romp restart-metrics` | What kernel restarts do to the sessions, read from the state ledgers and the kernel's routes; `--json --public` applies `perf_public.py`'s shape to the document (no session name, id, pid, scope or label). |
