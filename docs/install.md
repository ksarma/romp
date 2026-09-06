# Install

## Requirements

- **[Claude Code](https://docs.claude.com/en/docs/claude-code), signed in.**
  Install it and run `claude` once in a terminal to log in.
- **Python 3.10 or newer, and Node.js.**

    ```bash
    brew install python node               # macOS (Homebrew)
    sudo apt install python3 nodejs npm    # Ubuntu / Debian
    ```

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

## First run

The installer leaves Romp's back end running, so there is nothing to start. Open
the dashboard by typing `romp` in the terminal. That prints the URL at which
Romp can be reached and opens it in your browser.

### In VS Code or Cursor

The installer adds the extension automatically. Reload your editor window and
open Romp from the sidebar.

### Start a session

<video src="../assets/guide/first-session.mp4" controls loop muted playsinline preload="none" data-romp-autoplay width="100%"></video>
