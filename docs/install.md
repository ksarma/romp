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

`romp-serve` chooses the interpreter each time it starts the kernel: `ROMP_PYTHON`
if set, otherwise the newest of `python3.14` through `python3.10` on `PATH` or in
`~/.local/bin`, otherwise `python3` (`pick_python` in `bin/romp-serve`;
`bin/romp-sdk-setup` applies the same rule, so the SDK venv is built with the
interpreter the kernel runs). `install.sh` only checks that a `python3` exists.

The kernel also runs on free-threaded CPython 3.14t, the build with the GIL off.
The test suite passes there, CI runs it, and the kernel's shared caches are
written for threads that run at the same time (`tests/test_free_threaded_caches.py`
holds the cases). The kernel's builders, judge tiers and request handlers are
threads, so on that build they run in parallel. Nothing selects the free-threaded
build on its own. Name it: for a foreground `romp`, export
`ROMP_PYTHON=/path/to/python3.14t` in the shell; for the login service, put that
line in `~/.config/romp/service.env`, which the manager reads when it starts. The
SDK backend's venv must be built with the same interpreter (`romp-sdk-setup`
reads `ROMP_PYTHON` too). Web Push works on that build: `cryptography`, its soft
dependency, ships free-threaded wheels, and CI installs it on the 3.14t cell.

Installing another interpreter can move the kernel onto it. `uv python install
<version>` puts a `python3.X` shim in `~/.local/bin`, which `pick_python`
searches, so at its next restart the kernel runs the newest version it finds
while the SDK venv stays built for the old one, and every SDK session then fails
at import. Install extra interpreters with `uv python install --no-bin <version>`
and reach them through `uv python find <version>` or a venv, never as a bare
`python3.X` on `PATH`. The kernel and its SDK venv must share one interpreter, so
a move to 3.14t goes in this order: set `ROMP_PYTHON`, rebuild the SDK venv on it
with `bin/romp-sdk-setup`, run the test suite there, then restart.

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
  tracked file silently, and it does nothing in a Claude Code session Romp did not start. If you
  had installed track-changents yourself, the installer re-points those links at the bundled copy,
  which carries fixes the checkout lacks, and says so.

### Manual and custom installs

Install this way to keep Romp somewhere other than `~/romp`, or to run the
latest commit rather than the newest release:

```bash
git clone https://github.com/romp-on/romp.git ~/romp
cd ~/romp
git checkout "$(git tag -l 'v*' --sort=-v:refname | head -n1)"   # newest release
# or:   git checkout main                                        # the latest commit
./install.sh
```

Then add `bin/` to your `PATH` in your shell rc; `install.sh` prints the exact
line for your clone.

```bash
export PATH="$PATH:$HOME/romp/bin"
```

### Installing without API keys on disk

Where a credential may not sit in any file, the kernel can run a command of
yours and hand its output to every session it starts, every judge call and the
catalog fetch, so the unit, `service.env` and every file Romp writes stay
credential-free. One line in `service.env` turns this on; see [Installing
without keys on disk](reference.md#installing-without-keys-on-disk).

## First run

The installer leaves Romp's back end running, so there is nothing to start. Open
the dashboard by typing `romp` in the terminal. That prints the URL at which
Romp can be reached and opens it in your browser.

### In VS Code or Cursor

The installer adds the extension automatically. Reload your editor window and
open Romp from the sidebar.

### Start a session

<video src="../assets/guide/first-session.mp4" controls loop muted playsinline preload="none" data-romp-autoplay width="100%"></video>
