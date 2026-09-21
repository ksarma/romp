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
venv is built with the interpreter the kernel runs. `install.sh` runs that same
pick as its preflight (`bin/romp-serve --print-python`) and stops, naming the
interpreter and the install command, when it is older than 3.10, the floor the
kernel and the Agent SDK share; `bin/romp-serve` refuses to start the kernel on
one below it, so a manager never respawns a kernel that cannot run. The
reference's [The kernel's Python](reference.md#the-kernels-python) has the full
rule, what a mismatch reports, and how the kernel keys the match.

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

Install extra interpreters with `uv python install --no-bin <version>` and reach
them through `uv python find <version>` or a venv, never as a bare `python3.X`
on `PATH`.

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

On macOS the login agent runs the manager under its own copy of `node`
(`romp-node`, in the state directory), so Full Disk Access can be granted to romp
alone; a `node` that cannot run from a copy (Homebrew's build is one) is
detected and the system `node` used instead, and `ROMP_NO_NODE_COPY=1` in
`~/.config/romp/service.env` skips the copy (`0`, `false`, `no` and `off` are off; any
other non-empty value, `disabled` and `none` included, is on). See the
[reference](reference.md#service-environment-and-credentials).

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
  shell command (a `cp` or `tee` onto the file, a `>` redirection, `sed -i`). In a project that
  tracks files it also refuses a shell write whose target it cannot read (a variable, a
  substitution, a glob or brace list it cannot expand) and asks for the path spelled out; a copy
  whose name it cannot read into a folder where a tracked file could land is refused wherever the
  command is run from, and so is a relative path after a `cd` the guard cannot follow (to a name
  the shell fills in, inside an `if` or a loop, or to a folder that does not exist yet), with the
  reason. A temp file named only by the shell's process id (`$$`), at an absolute path where no
  tracked file could land (outside the project you are working in, and not in a folder of another
  project where a tracked file could land), still runs; a name built from `$RANDOM` or `$SECONDS`
  is refused, since a script can reassign those, and the same `$$` name written as a relative path,
  from a session in such a project, is refused. It also reads the common command wrappers `setsid`,
  `flock`, `taskset`, `chrt` and `numactl` to the write inside them, runs `env -C DIR`, `env
  --chdir=DIR` and `sudo -D DIR` in DIR, refuses a `cp`/`mv`/`install`/`ln` option it does not know
  (spell the command without it), treats `$HOME` and `~` as unreadable once the command reassigns
  HOME, and refuses a variable or substitution whose literal head is above or under a tracked
  project (its value could name or climb into one). A second pass (2026-09-19) added six more rules:
  the option tables accept a glued short form (`sort -oFILE`), and `env -S` (read then as a shell
  string) is refused outright since the third pass, below; an assignment to HOME in any form
  (`HOME+=`, `read HOME`, `printf -v HOME`, `export`/`declare`/`local HOME`, `for HOME in`, and since
  the third pass any mention of HOME outside an expansion) makes `$HOME` and `~` unreadable for the
  whole command; an earlier `rm`, `mv`, hard `ln`, `cp -l` or `cp -s` that removes, renames or
  aliases a path makes a later write under it unreadable; a stat or config-read error other than
  not-found anywhere on a path it checks (a mode-000 folder, `.trackchanges` or project) refuses from
  any working directory, naming the error; a `.git`, `.obsidian` or `.trackchanges` between a tracked
  project and the file refuses, naming both markers; and a `cd` it cannot know ran in this shell
  (after `&&`/`||`, in a pipeline, backgrounded, under a wrapper, `pushd -n`, a physical `cd -P` or
  `set -P`, or a call of a function that cd's) leaves the directory unknown, so a later relative write
  refuses. A third pass (2026-09-19) re-keyed six of those rules on what the guard can see, not on a
  list of spellings: the bare identifier HOME anywhere in the command outside a `$`-expansion (a
  nameref, `select HOME in`, a glued `printf -vHOME`, `unset HOME`, a mention in an argument) makes
  `~` and `$HOME` unreadable and a bare `cd` or `cd ~` unknown; every wrapper it peels (`env`,
  `sudo`, `nice`, `nohup`, `time`, `timeout`, `ionice`, `stdbuf`, `setsid`, `flock`, `taskset`,
  `chrt`, `numactl`, `command`, `builtin`, `exec`, and since the seventh pass zsh's precommand
  modifiers `noglob`, `nocorrect` and `-`, which hid the writer behind them) is parsed in full
  against its own option table or
  the command is refused naming the option (an unknown, abbreviated or non-literal one: spell the
  long form the guard knows, or drop the wrapper), a glued `env -Cdocs` is a chdir, a nested `env -C a
  env -C b` enters a then b under a, `env -S` and sudo's `-e`, `-i`, `-s`, `-R` and `-h` are refused
  outright, and `time -o FILE` is a write of FILE; an `ln -s` whose source is not literal makes the
  link name unknown, so a later write through it refuses; a `set`, `shopt`, `setopt` or `unsetopt`
  option not on the inert allowlist (`set -e`, `-u`, `-x`, `-v`, `-n`, `-C`, `-o errexit`, `nounset`,
  `pipefail`, `xtrace`, `verbose`, `noclobber`, and the options about history recording, completion,
  prompts and job control pass; anything that changes how a word is expanded, matched or split, where a
  relative path resolves, or which grammar is in force, `set -f`, `noglob`, `set -P`, `set -o
  chaselinks`, `shopt -s globstar`, `set -k`, does not) leaves the directory unknown, so a later
  relative write refuses (spell the target absolutely);
  the parent-prefix rule finds a tracked project at any depth under the literal head, so
  `../../$x/docs/report.md` refuses when `$x` could spell the way down to one; an option a writer's
  table does not know (`cp --targ`) refuses wherever the writer is reached, its operands judged by
  their own project from any cwd; `chdir` (zsh's and dash's cd) leaves the directory unknown, and
  coreutils `link` is a hard-link maker. The costs are measured against
  `tools/romp-track-bash-guard-corpus.json` (164 ordinary developer commands stay allowed; the
  refusals added are a `~/` write beside a mention of HOME, an `env -S` line, a relative write after
  `shopt -s globstar`, a write through a link whose source is a variable, and a variable-named file in
  a folder with a tracked project anywhere beneath it). The fifth commit (2026-09-19) closed what a
  fourth attack found, each keyed on a visible construct: a variable name the shell fills in on an
  assignment, declaration, nameref, export, typeset, local, readonly, read, mapfile, getopts, unset,
  `printf -v`, `let` or `(( ))` (`export ${h}${m}=...`, `declare -n r=${h}${m}`, `read -r "$(printf
  HOME)"`) makes `~` and `$HOME` unreadable, since a name the guard cannot read may be HOME; zsh's
  clobber-override redirections (`>!`, `>>!`, `&>!`, `>>|` and their kin, spaced or glued) are
  writes, judged in bash's and zsh's readings (dash reads `>! f` as bash does, a file named `!`,
  rejects `>>| f` and `>&| f`, and writes f through `&>| f`, measured 2026-09-20); `[[ a > f ]]`
  and `(( a > f ))` compare in bash and zsh and are read in dash's grammar too since round 5's fifth
  addendum (2026-09-20: a command named `[[` performing the `>`, a subshell running the `(( ))` body
  as a command list), so a tracked f there refuses naming dash and the construct, a process
  substitution among the test's operands runs in bash (`[[ -f <(echo x > f) ]]` writes f) and an
  operator glued to the closing `]]` is a redirection or list operator (`[[ a ]]>f` writes f in
  every shell), each judged as anywhere since the addendum's fix-up (2026-09-20), since its second fix-up
  the same day an expansion nested in a `${...}` word (`${x:-$(cp a b)}`, a backtick, a `<(...)`) is read as
  the command it runs in every position, and a literal echo or printf piped into a shell reading stdin is
  that shell's script (a producer the guard cannot see, `cat f | bash`, stays unread, as does a script
  handed to a shell outside the set it reads, busybox sh or ash among them), and since its third fix-up the same day an unquoted here-document body's expansions are read as the commands they run and the expanded body is the consumer's script (a quoted delimiter keeps the body as written), a `$(echo '...')` or a backtick with literal operands is the text it prints where the shell puts it (so `bash -c "$(echo 'cp a b')"` and `$(echo cp) a b` copy), a `${x:-word}` alone is read as a script under its default word, zsh's `=(cmd)` runs its command, a shell fed through a subshell, a group, an if or loop body, a `/dev/stdin` operand, a `<(echo '...')` script, a redirection on the compound's closer or a `-c` script's inner shell reads what was piped or redirected to it, and a copying writer whose one unquoted operand the shell may split into two refuses while a project is in play (a `${...}` word the guard cannot read as a script, a producer outside its output model (since round 6's second commit, 2026-09-21, the model reads a subshell or a group of echo, printf and silent commands as what it prints), a redirection on the closing brace of zsh's brace-body compound and a command whose name is an expansion the resolver never reads stay unread and are named), and `[[ $a > $b ]]`
  with `$b` the guard cannot read refuses from a tracked cwd (the remedy: `expr`, or a cwd outside
  the project); a link the command makes is followed into a numeric
  name's folder too, and one whose source is not literal refuses a numeric write through it; a
  python or node path that is a plain string is judged by its text whatever it holds (a `$` is
  text), while one built from an f-string, `.format(`, `%` or a template literal with `${}` is
  refused as unreadable; a hard link, `cp -l`, `cp -s`, `link` or a link whose source is not literal
  puts the project its SOURCE lies in in play from any working directory, and one whose source the
  guard cannot read refuses from any; the inert shell-option lists carry their criterion (an option
  is inert only if it changes neither how a word is expanded, matched or split, nor where a relative
  path resolves, nor which grammar is in force; `set -f`, `noglob`, `nomatch`, `markdirs`,
  `cdsilent`, `pushdminus`, `extquote`, `set -k` and their kin are off them, and bash's `set -k` is
  read both ways); and the remedy line quotes its `--file` path in single quotes, so a path holding
  a `$` pastes back unchanged. Its second commit (B2 as the reviewer ruled it, option (c) on the
  measured delta: the resolution half kept, the refusal half dropped) reads the values it can: a
  name the command sets to a plain string earlier (`x='../sub'`, `export x=...`, at the top level in
  plain sequence), HOME, PWD, OLDPWD, `~+` and `~-`, resolving them in every word and judging the
  real path (so `x=other.md; echo hi > docs/$x` is judged by name and allowed, and
  `x='../docs/report.md'; cp base/report.md scratch/$x` refuses by name), and reads none of HOME,
  PWD and OLDPWD once the command names the name outside an expansion or may fill it in (so
  `PWD=<dir>; cp x $PWD/docs/report.md` from a tracked cwd is refused as not literal, the reason
  naming the mention); what stays opaque (a name the command never sets, one set in a body, after
  `&&`, in a subshell, by a `read`, a loop, an eval, a sourced file or a function call, a `$(...)`)
  keeps the verdict the working directory gives it, refused as not literal from a cwd in a tracked
  project and allowed from a cwd in no project. The principle: a guard is strictest where its
  subject is and loosest where its subject is not; this guard's subject is tracked files inside
  projects, and from a cwd in no project it must not refuse on a value it cannot know (a user in a
  scratch directory writing `$USER.log` or `$(date +%s).md` is ordinary work, and a guard that
  refuses ordinary work gets switched off). The residual, with its boundary: a literal head outside
  every project followed by an opaque expansion whose value can climb with `..` is allowed from a
  cwd in no project; from a tracked cwd the refusal stands unchanged. The cost is measured against
  the corpus, a sample: none of the 164 ordinary commands changes verdict; of 44 shapes with a
  literal head outside every project followed by an expansion, run from a cwd in no project and from
  a tracked one, the 22 readable ones refuse 3 times after resolution, each by name on a tracked
  file (20 refusals from the tracked cwd became allowances), and the 22 opaque ones keep their 22
  refusals from the tracked cwd and their 22 allowances from the cwd in no project. A pin addendum
  (2026-09-19) pinned the fifth pass's unpinned claims from the tracked cwd, where an unresolved
  name is refused and a resolved one judged by name, and closed what its attacker found, each a
  stated rule applied to a construct the guard could already see: `cp --parents` lands each source
  at its whole path under the destination, so `cp --parents docs/report.md ../web/` is judged on
  web/docs/report.md; python's `-c` is read inside its option cluster with the code glued on
  (`-c'...'`, `-uc'...'`, `-Xutf8 -c'...'`) and node's `--eval=` with its code (`--print=` takes
  none, node then reads the script from stdin); and a triple-quoted python path is the plain string
  it is, while a template literal holding a quote is still a template. None of the 164 ordinary
  commands newly refuses. A seventh pass (2026-09-19) closed what the sixth pass's attacker found,
  77 in-model overwrites in 13 spelling classes of one miss, with the readability rule stated below
  (a name is readable only after plain top-level `NAME=plain-string` writes and nothing else: a
  tilde opening a value, a transforming declaration flag, a nameref, a name the shell fills in, a
  pipeline or a piped group, a wrapper's argument, a `function NAME {` definition called later or a
  subscript each leaves it unreadable, and a plain `unset` frees it again), reads a plain top-level
  `HOME=<path>` for the commands after it (the prefix `HOME=<path> cmd` excluded, since the shells
  expand that command's `$HOME` and `~` first), and makes the refusal for a `cd` under `builtin`,
  `command` or `time` say which shells move. This guard is best-effort against known write forms: it
  refuses the shell writes it models and, by design, allows anything it does not recognise, so it
  never blocks ordinary work it cannot read; it is a backstop, not a complete boundary. The
  allow-by-default for an unmodelled writer is deliberately not flipped, since flipping it would
  refuse almost all normal work. What it does refuse, while a tracked project is in play, is a write
  it reads but cannot place: a target it cannot read, a path it cannot check (a stat error other
  than not-found), an option on a modelled writer or wrapper it does not parse in full, an env -S
  string, a shell option it does not know to be inert for paths, a link whose source it cannot read,
  a `~` or `$HOME` write beside a mention of HOME or beside a variable name the shell fills in, a
  template or format string as an interpreter's write path, and, from any working directory, a write
  through an alias the command makes (a hard link, `cp -l`, `cp -s`, `link`, a link whose source it
  cannot read) whose source lies in a tracked project or is one it cannot read. A value it can read
  is resolved first and the real path judged. A name is readable only when every write to it in the
  command is a plain top-level `NAME=plain-string` the shell performs as spelled: no tilde opening
  the value, no declaration flag at all, no `declare`, `typeset` or `local` (dash has none of the three; `export` and `readonly` with no option word are the two declarations every shell performs), no nameref reaching it, no name the shell fills
  in, no subshell, pipeline, piped group or body scope, no `{ }` group opened after `&&`, `||` or `|`, no wrapper argument, no call of a function
  the command defines in any spelling, no subscript; any other construct that can write the name,
  listed here or not, leaves it unreadable, the doctrine a `read` and a loop variable already had.
  HOME, PWD, OLDPWD, `~+` and `~-` are read the same way: HOME after a plain top-level `HOME=<path>`
  assignment of its own, and none of the three once the command names or may fill in the name in any
  other form. THE RESIDUAL PROPERTY. The guard refuses a write only when it resolves the command to a writer it models (the writer cases of extract's switch, a write redirection, an interpreter's write call it scans) reached through a road it reads (the wrapper set, the shells' script roads, the readings of the resolver, the alias and hash roads), with a target it can place or cannot read. Every write that still reaches a tracked file is one the guard does not resolve to such a writer through such a road, whether or not its text stands in the command, and falls in one of these classes, each measured by execution in tools/romp-track-bash-guard.test.mjs (THE RESIDUAL TABLE, whose rows are the population this statement is over): a writer outside the model, a program, or a write form of a program the hook models, that writes the file by its own nature and is not among the write forms the hook reads (rsync, patch, tar -x, ed, ex, vim, make, shuf -o, gawk -i inplace, awk's print redirect, uniq, scp, openssl -out, shred, curl -o, wget -O, find -exec, a git alias or a subcommand that writes the tree, bash's history -w, zsh's sysopen and mapfile modules, sed's e command and a w command in a sed script the resolver cannot read, busybox's applets); a reader outside the roads, a program that runs a command or a script the hook does not follow into it (xargs, an interpreter's system, exec or subprocess call, a wrapper outside the set, a shell outside SHELLS, a file the command writes and then runs or sources); a command name the resolver never reads, a command whose name is an expansion of a kind the resolver does not read ("$@", $1, $*, "${a[@]}", a loop variable, a name read, printf -v or a nameref filled, ${SHELL}, a substitution outside the output model such as $(which cp), a ${...} operator form the resolver does not read); a script held in a variable, a value the command gives a name through a construct the resolver does not read (`read`, `printf -v`, a positional parameter), run as a command or handed to a shell (`$c` after `read c`, `eval "$1"`, `bash -c "$c"` after `printf -v c`; a value an assignment word gives, whitespace included, is read through THE HEAD CANDIDATES since round 6's fourth commit); a producer outside the output model, a pipe into a shell from anything but a literal echo or printf, alone or in a subshell or group of such commands (a call of a function the command defines, a tee or a further pipe, a cat of a file); zsh's glob grouping, a `(..)` inside a word handed to zsh, read as a subshell by the lexer's zsh grammar while zsh globs it (a lexer gap, stated since the first commit of this round); an opaque expansion from a cwd outside every project, a leading opaque expansion, or one after a literal head outside every project, from a cwd in no project (B2 as ruled, with its boundary). A shape outside these classes that reaches a tracked file is a rule to state, not a residual. If you had installed track-changents yourself, the installer
  re-points those links at the bundled copy, which carries fixes the checkout lacks, and says so.

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
