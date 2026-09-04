# cli/ — terminal tools

Python implementations of the terminal-facing romp commands. Run them via
their `bin/` symlinks (`romp version`, `romp update`, `romp keyswap`)
— see `bin/README.md` for the command surface.

| File | Command | What it is |
|---|---|---|
| `version.py` | `romp version` | Version report across the moving parts (working tree vs running kernel vs built bundles). |
| `update.py` | `romp update [host]` | Pushes this machine's committed romp to attached remote kernels over ssh and restarts them. |
| `keyswap.py` | `romp keyswap [<name>]` | Switches which API key the sessions bill, with no kernel restart: rewrites only the `ANTHROPIC_API_KEY=` line of `service.env` from a sibling file, and `--cycle`/`--cycle-all` reconnects running sessions onto it. Prints sha256 heads, never a key. |
| `idle_dots.py` | (hook-fired) | tmux backend only: heals stranded `working` state by inspecting tmux panes. Fired from `hooks/tmux-status.sh`. |
