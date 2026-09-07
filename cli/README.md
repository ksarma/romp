# cli/ — terminal tools

Python implementations of the terminal-facing romp commands. Run them via
their `bin/` symlinks (`romp version`, `romp update`, `romp keyswap`)
— see `bin/README.md` for the command surface.

| File | Command | What it is |
|---|---|---|
| `version.py` | `romp version` | Version report across the moving parts (working tree vs running kernel vs built bundles). |
| `update.py` | `romp update [host]` | Pushes this machine's committed romp to attached remote kernels over ssh and restarts them. |
| `keyswap.py` | `romp keyswap [<name>] [--refresh] [--cycle <session,…>\|--cycle-all]` | Reports which API key the sessions bill (sha256 heads, never a key; a `ROMP_API_KEY_REF` reference is a source identity, never resolved here) and whether the kernel reads what the shell reads. With `ROMP_CREDENTIAL_COMMAND` set (`kernel/envsource.py`), `<name>` writes the one-token selector file the command reads as `$1` and `--refresh` makes the kernel re-run it; `--cycle` / `--cycle-all` reconnect quiet running sessions after a rotation so their new processes pick the new credential up. Where the key lives in a file, upstream's named swap (a rewrite of `service.env` from a sibling profile) is refused: this fork does not write API keys to files. |
| `idle_dots.py` | (hook-fired) | tmux backend only: heals stranded `working` state by inspecting tmux panes. Fired from `hooks/tmux-status.sh`. |
| `spend_rebuild.py` | `romp spend-rebuild` | Recounts the token columns of the spend ledger (`spend.json`) from the transcripts' own per-call usage — the recorder mis-diffed the CLI's per-turn `usage` until 2026-09-06. Dollars and turn counts untouched; dry run by default, `--apply` writes and keeps a backup. |
