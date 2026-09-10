# Install

## Requirements

- **[Claude Code](https://docs.claude.com/en/docs/claude-code), signed in.**
  Install it and run `claude` once in a terminal to log in.
- **Python 3.10 or newer, and Node.js.**

    ```bash
    brew install python node               # macOS (Homebrew)
    sudo apt install python3 nodejs npm    # Ubuntu / Debian
    ```

### Which Python runs the kernel

The kernel runs on the Python its Agent SDK venv was built with: the venv's
compiled extensions import into the kernel process, so the two must agree.
`romp-serve` picks the interpreter each time it starts the kernel (`pick_python`
in `bin/romp-serve`), trying these in order:

1. `ROMP_PYTHON`, if set. It is refused with one line when it does not name an
   executable interpreter.
2. The interpreter the SDK venv's `pyvenv.cfg` records, if it still runs and is
   still the version and build the venv was built for.
3. Another Python of that same version and build on `PATH` or in `~/.local/bin`,
   with a line saying so.
4. The newest `python3.X` on `PATH` or in `~/.local/bin` (`python3.14` down to
   `python3.10`), else `python3`: the rule for a machine with no venv yet.
   Reached with a venv in place, it also prints that the venv must be rebuilt
   for the pick.

`bin/romp-sdk-setup` and `bin/romp-codex-setup` apply the same rule, so each
venv is built with the interpreter the kernel runs. `install.sh` only checks
that a `python3` exists. The reference's [The kernel's
Python](reference.md#the-kernels-python) has the full rule, what a mismatch
reports, and how the kernel keys the match.

The kernel also runs on free-threaded CPython 3.14t, the build with the GIL off.
The test suite passes there, CI runs it, and the kernel's shared caches are
written for threads that run at the same time (`tests/test_free_threaded_caches.py`
holds the cases). The kernel's builders, judge tiers and request handlers are
threads, so on that build they run in parallel. Nothing selects the free-threaded
build on its own. Name it: for a foreground `romp`, export
`ROMP_PYTHON=/path/to/python3.14t` in the shell; for the login service, put that
line in `~/.config/romp/service.env`, which the manager reads when it starts. The
Claude Code backend's venv must be built with the same interpreter
(`romp-sdk-setup` reads `ROMP_PYTHON` from its own environment, not from that
file). Web Push works on that build: `cryptography`, its soft dependency, ships
free-threaded wheels, and CI installs it on the 3.14t cell.

Installing another interpreter does not move the kernel: `uv python install
<version>` puts a `python3.X` shim in `~/.local/bin`, which steps 3 and 4
search, and a machine whose venv's interpreter still runs stops at step 2. One
hazard remains: with no SDK venv, or with the venv's recorded interpreter gone
and no other Python of its version and build found, the pick reaches step 4,
so at the next restart the kernel runs the newest Python found, that shim
included, and the venv must be rebuilt for it. If romp runs as a service, pin
the interpreter anyway, by its versioned path: `ROMP_PYTHON=/usr/bin/python3.12`
in `~/.config/romp/service.env` holds through a deleted or rebuilt venv, where
`python3` would follow the next upgrade.

A move to another Python, 3.14t included, goes in this order:

1. Put `ROMP_PYTHON=<path>` in `~/.config/romp/service.env`. The manager reads
   it for the kernel; the setup scripts never read it.
2. Rebuild the SDK venv with the same value in the command's own environment:
   `ROMP_PYTHON=<path> bin/romp-sdk-setup`. If the Codex backend is set up,
   re-run `bin/romp-codex-setup` after it: it follows the SDK venv's record, so
   a plain run rebuilds `codexvenv` for the new interpreter.
3. Run the test suite with that interpreter: `<path> -m pytest -q` when it has
   pytest. When it has none, run the suite from a venv built on it (a distro or
   uv-managed Python refuses installs into itself, PEP 668): on Debian and
   Ubuntu install the `python3.X-venv` package first; then
   `<path> -m venv <dir>`, `<dir>/bin/pip install pytest` and
   `<dir>/bin/python -m pytest -q`. The venv's `bin/python` is that
   interpreter.
4. Restart the manager: `romp down`, then `romp up`. Only a manager start reads
   `service.env`; `romp refresh` leaves the manager running, and the kernels it
   restarts inherit the environment the manager started with ([Two things
   still need a restart](reference.md#two-things-still-need-a-restart)),
   unless `bin/romp-manager` itself changed since the manager started: then a
   supervised manager exits on the refresh and the service starts a new one,
   which reads the file, while a foreground manager warns and restarts the
   kernels. For a foreground `romp` with `ROMP_PYTHON` exported in its shell,
   stop it with `Ctrl+C` and run `romp up` from a shell carrying the new
   export.

Run plainly, with no `ROMP_PYTHON` in its environment, `bin/romp-sdk-setup`
keeps the venv's recorded interpreter while it still runs as the venv's version
and build, and rebuilds only in the cases the [architecture
page](architecture.md#what-the-installer-sets-up) lists: the venv's own
`bin/python` or `bin/pip` missing, or that interpreter no longer its version
and build with no other Python of that version and build on `PATH` or in
`~/.local/bin`, when it moves to the newest Python found.

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/romp-on/romp/main/bootstrap.sh | bash
```

Open a new terminal afterwards, so `~/romp/bin` is on your `PATH`, and type
`romp` to launch the user interface in a browser.

The same command updates Romp later. To remove Romp, run `romp uninstall` (add
`--purge` to delete recorded sessions too).

This clones Romp to `~/romp` and installs the newest release.
[What it installs, in detail](architecture.md#what-the-installer-sets-up).

### What the installer links into `~/.claude/`

Everything the installer puts under `~/.claude/` is a symlink back into the clone, so updating
the clone updates it:

- Romp's own hooks, in `~/.claude/hooks/`, registered in `~/.claude/settings.json` (a merge that
  leaves your other hooks alone).
- `romp-postal.mcp.json` (the sessions' mailbox), `romp-session-prompt.md` (appended to a
  session's system prompt), and the `romp-postal` skill in `~/.claude/skills/`.
- The agent-side tooling for [file comments and tracked changes](guide.md#files), from the copy of
  track-changents bundled in the clone (`vendor/track-changents/`): the `track-edit`,
  `track-comment`, `track-reply` and `track-config` commands and the `track-guard.mjs` hook in
  `~/.claude/hooks/`, and the `tracked-changes` skill in `~/.claude/skills/`. The guard is
  registered as a `PreToolUse` hook on `Write|Edit|MultiEdit`; it stops a session from writing a
  tracked file silently, and it does nothing in a Claude Code session Romp did not start. Romp's
  own `romp-track-bash-guard.mjs`, registered on `Bash`, does the same for a write made through a
  shell command (a `cp` or `tee` onto the file, a `>` redirection, `sed -i`). If you
  had installed track-changents yourself, the installer re-points those links at the bundled copy,
  which carries fixes the checkout lacks, and says so.

### Manual and custom installs

Install this way to keep Romp somewhere other than `~/romp`, or to run the
latest commit rather than the newest release:

```bash
git clone https://github.com/romp-on/romp.git ~/romp
cd ~/romp
git checkout "$(git tag -l 'v*' --sort=-v:refname | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' | head -n1)"   # newest release
# or:   git checkout main                                        # the latest commit
./install.sh
```

Then add `bin/` to your `PATH` in your shell rc; `install.sh` prints the exact
line for your clone.

```bash
export PATH="$PATH:$HOME/romp/bin"
```

## First run

The installer leaves Romp's back end running, so there is nothing to start. Open
the dashboard by typing `romp` in the terminal. That prints the URL at which
Romp can be reached and opens it in your browser.

### In VS Code or Cursor

The installer adds the extension automatically. Reload your editor window and
open Romp from the sidebar.

### Start a session

<video src="../assets/guide/first-session.mp4" controls loop muted playsinline preload="none" data-romp-autoplay width="100%"></video>

## License

Romp is [Apache-2.0](https://github.com/romp-on/romp/blob/main/LICENSE); the file viewer draws PDF
pages with [pdf.js](https://mozilla.github.io/pdf.js/), bundled with the interface under the same
Apache-2.0 license.
