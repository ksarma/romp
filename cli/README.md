# cli/ — terminal tools

Python implementations of the terminal-facing romp commands. Run them via
their `bin/` symlinks (`romp version`, `romp update`, `romp keyswap`)
— see `bin/README.md` for the command surface.

| File | Command | What it is |
|---|---|---|
| `version.py` | `romp version` | Version report across the moving parts (working tree vs running kernel vs built bundles). |
| `update.py` | `romp update [host]` | Pushes this machine's committed romp to attached remote kernels over ssh and restarts them. |
| `keyswap.py` | `romp keyswap [--cycle <session,…>\|--cycle-all]` | Reports which API key the sessions bill (sha256 heads, never a key) and, after a key rotation, reconnects quiet running sessions so their new processes pick the new key up. Upstream's named swap (`romp keyswap <name>`, a rewrite of `service.env`) is refused: this fork does not write API keys to files. |
| `idle_dots.py` | (hook-fired) | tmux backend only: heals stranded `working` state by inspecting tmux panes. Fired from `hooks/tmux-status.sh`. |
