---
name: tracked-changes
description: Act as the user's EDITOR — your changes to their files land as accept/reject tracked suggestions (inline diffs + a review panel) instead of applying silently. Works for BOTH an Obsidian vault note AND a code file in VS Code/Cursor — same sidecar, same CLIs. Use when the user asks you to be their editor / proofreader, to edit a file "so I can review/accept the changes", when you receive an "[obsidian] …" or "[obsidian-diff] …" message from a vault/editor (a note, a comment thread, a rewrite or reply request), or when a new session is started to edit a file this way. While acting as editor, FIRST check the tracking flag for EACH file with track-config.mjs: if ON, make every change to that file with the track-edit / track-comment / track-reply CLIs and never the Edit/Write/MultiEdit tools; if OFF, edit normally with Edit/Write.
allowed-tools: Bash, Read, Edit, Write, MultiEdit
---

A PreToolUse guard hook (`track-guard.mjs`, installed alongside these CLIs)
denies raw Write/Edit on tracked files, so forgetting the flag check fails loudly
instead of silently overwriting tracked work — the deny message names the CLI to
use.

# tracked-changes — edit files as reviewable tracked suggestions

You are the user's EDITOR. A flag decides how your changes land: either as TRACKED
SUGGESTIONS the user accepts or rejects in their editor (Obsidian for notes, VS Code
/ Cursor for code), or as normal edits. The flag is PER FILE, not per repo — check
it FIRST, before you touch each file. It is the one control, and you obey it.

## First: is tracking on for THIS file?

Before your first edit to EACH file — every file, every time — run:

```bash
node ~/.claude/hooks/track-config.mjs --file <ABSOLUTE path>
```

It prints `on` or `off`, and **its exit status mirrors that answer: 0 for `on`, 1
for `off`**. A non-zero exit here is the ANSWER, not a failure — read stdout and
proceed; don't retry it, don't report it as a broken command, and don't run it
inside something that aborts on a non-zero status.

The scope it reads is `.trackchanges/config.json`, a flat list of exact file paths
and `folder/` prefixes maintained by the editor's toggle (`engine.isTracked`;
absent file or empty list ⇒ off). So two files in the same repo routinely differ,
and one check covers ONE file — never generalize a `yes` or a `no` to the rest of
the repo or to the rest of your session. Re-check whenever you move to another file,
and re-check a file you've been away from if the user may have flipped its toggle.

- **`on`** → tracked mode for that file: make EVERY change to it through the
  track-changes CLIs below, and NEVER with the Edit / Write / MultiEdit tools. Your
  change is recorded in a sidecar store and the editor renders it as an
  accept/reject diff.
- **`off`** → edit that file normally with the Edit / Write tools; do NOT use
  track-edit or track-comment (the user isn't reviewing suggestions for it).
  One carve-out: if you're pinged to answer a comment thread, you still reply with
  `track-reply` — see "Messages from the editor" below. A reply only adds a
  message to the conversation; it never changes how your edits land.

The CLI-editing rules in the next section apply only to files whose flag is `on`;
the comment-thread reply further down works in EITHER mode.

## When tracking is ON: never touch the file with Edit/Write — use the CLIs

Nor through Bash. A shell write reaches the file behind the tools and leaves no
record: no `cp` or `mv` over it, no `tee`, no `>` or `>>` redirection into it (a
heredoc included), no `sed -i` or `perl -i`, no python `open(..., 'w')` or node
`writeFileSync`. Every write to a tracked file goes through `track-edit`. Check
`track-config`'s exit code as a step of its own, never in a compound command with
the write: its status is 0 when tracking is ON, so `track-config ... && cp ...` runs
the copy on exactly the file it must not touch.

In a project that tracks files, a shell write whose target is not a literal path
is refused as well: a variable such as `"$DST"`, a `$(...)`, a glob or brace list
the guard cannot expand, and a relative path after a `cd` the guard cannot follow
(one to a name the shell fills in, one inside an `if` or a loop, one to a folder
that does not exist yet). The guard cannot tell which file such a word names and
does not read your variables to find out (it reads `HOME` alone, so a leading
`$HOME/` is read as `~/` is), so the refusal holds whatever the word would expand to.
One exception: a target whose only expansions are `$$` or `${$}`, the shell's
process id, at an absolute path where no tracked file could land (outside the
project you are working in, and not in a folder of another project that tracks a
file there), is allowed: `/tmp/build-$$.log` runs. Nothing else is: `$RANDOM`,
`$SECONDS` and every other name can be unset or shadowed and then hold a path, so
`log.$RANDOM` inside a tracked project is refused, in every shell, with the reason
and a way forward. Two deliberate false refusals of this exception, escalated with
the change and stated in decision 47 of plans/file-review.md: a `$$` name whose
folder is one where a tracked file could land (`<root>/x-$$/y.md`,
`<root>/docs/build-$$.log`) is refused from any working directory while its
literal spelling may pass, the refusal naming the folder; and a `$$` name in a
folder of more than 2000 entries inside a tracked project is refused without a
scan of that folder (`LANDING_SCAN_CAP`). Each refusal says what to do. Spell the path out (a tracked file
then takes its change through `track-edit`, a file outside the project an ordinary
write), name a temp file with `$$`, give a folder a literal name of your own, or
write outside the tracked project.

The guard also reads the common wrappers `setsid`, `flock`, `taskset`, `chrt` and
`numactl` to the write inside them, runs `env -C DIR` and `sudo -D DIR` in DIR,
refuses a `cp`/`mv`/`install`/`ln` option it does not know, treats `$HOME` and `~`
as unreadable once the command reassigns HOME, and refuses a variable or
substitution whose literal head is above or under a tracked project. A second pass
added six more: the tables accept a glued short form (`sort -oFILE`); an
assignment to HOME in any form (`HOME+=`, `read HOME`, `printf -v HOME`,
`export`/`declare`/`local HOME`, `for HOME in`, and the rest) makes `$HOME` and `~`
unreadable for the whole command; an earlier `rm`, `mv`, hard `ln`, `cp -l` or `cp
-s` that removes, renames or aliases a path makes a later write under it
unreadable; a stat or config-read error other than not-found anywhere on a path it
checks (a mode-000 folder, `.trackchanges` or project) refuses from any working
directory; a `.git` or `.trackchanges` between a tracked project and the file
refuses; and a `cd` it cannot know ran in this shell (after `&&`/`||`, in a
pipeline, backgrounded, under a wrapper, `pushd -n`, a physical `cd -P`, or a call
of a function that cd's) leaves the directory unknown, so a later relative write
refuses. A third pass re-keyed six of those rules on what the guard can see, not
on a list of spellings, so the refusal you meet is one of these: any mention of
HOME outside an expansion (`declare -n r=HOME`, `select HOME in`, `printf -vHOME`,
`unset HOME`, the word in an argument) makes `~` and `$HOME` unreadable and a bare
`cd` or `cd ~` unknown; a wrapper (`env`, `sudo`, `nice`, `nohup`, `time`,
`timeout`, `ionice`, `stdbuf`, `setsid`, `flock`, `taskset`, `chrt`, `numactl`,
`command`, `builtin`, `exec`, and since the seventh pass zsh's precommand modifiers
`noglob`, `nocorrect` and `-`, which hid the writer behind them) carrying an option it
does not parse in full (an
unknown, abbreviated or non-literal one, `env --chd=docs`) is refused naming the
option (spell the long form, or drop the wrapper), a glued `env -Cdocs` is a chdir,
a nested `env -C a env -C b` enters a then b, `env -S` is refused outright and so
are sudo's `-e`, `-i`, `-s`, `-R` and `-h`, and `time -o FILE` writes FILE; an `ln
-s` with a link whose source is not literal makes the link name unknown, so a
later write through it refuses; a `set`, `shopt`, `setopt` or `unsetopt` naming a
shell option it does not know to be inert for paths (`set -e`, `-u`, `-x`, `-o
pipefail` and the options about history, completion, prompts and job control pass;
`set -P`, `set -o chaselinks`, `shopt -s globstar` and anything about cd, links,
globbing, aliases or quoting do not) leaves the directory unknown, so a later
relative write refuses (spell the target absolutely); a variable in a path whose
literal head has a tracked project at any depth beneath it refuses, naming the
projects; and an option a writer does not know (`cp --targ`) refuses wherever the
writer is reached, from any working directory. The fifth commit (2026-09-19)
closed what a fourth attack found, each keyed on a visible construct: a variable
name the shell fills in on an assignment, declaration, nameref, export, typeset,
local, readonly, read, mapfile, getopts, unset, `printf -v`, `let` or `(( ))`
(`export ${h}${m}=...`, `declare -n r=${h}${m}`, `read -r "$(printf HOME)"`)
makes `~` and `$HOME` unreadable, since a name the guard cannot read may be
HOME; zsh's clobber-override redirections (`>!`, `>>!`, `&>!`, `>>|` and their
kin, spaced or glued) are writes, judged in bash's and zsh's readings (dash reads
`>! f` as bash does, a file named `!`, rejects `>>| f` and `>&| f`, and writes f
through `&>| f`, measured 2026-09-20); `[[ a > f ]]` and `(( a > f ))` compare in
bash and zsh and are read in dash's grammar too since round 5's fifth addendum
(2026-09-20: dash has neither word, so the first is a command named `[[` that
performs the `>` and the second a subshell running its body as a command list;
a `$((` whose first `(` closes before the last is `$( (` to bash and zsh, a
command substitution they run; a `$(...)` inside any arithmetic body runs in
every shell), so a tracked f there refuses naming dash and the construct, a
process substitution among the test's operands runs in bash
(`[[ -f <(echo x > f) ]]` writes f) and an operator glued to the closing `]]`
is a redirection or list operator (`[[ a ]]>f` writes f in every shell), each
judged as anywhere since the addendum's fix-up (2026-09-20), since its second
fix-up the same day an expansion nested in a `${...}` word (`${x:-$(cp a b)}`, a
backtick, a `<(...)`) is read as the command it runs in every position, and a
literal echo or printf piped into a shell reading stdin is that shell's script (a
producer the guard cannot see, `cat f | bash`, stays unread, as does a script
handed to a shell outside the set it reads, busybox sh or ash among them), and since its third fix-up the same day an unquoted here-document body's expansions are read as the commands they run and the expanded body is the consumer's script (a quoted delimiter keeps the body as written), a `$(echo '...')` or a backtick with literal operands is the text it prints where the shell puts it (so `bash -c "$(echo 'cp a b')"` and `$(echo cp) a b` copy), a `${x:-word}` alone is read as a script under its default word, zsh's `=(cmd)` runs its command, a shell fed through a subshell, a group, an if or loop body, a `/dev/stdin` operand, a `<(echo '...')` script, a redirection on the compound's closer or a `-c` script's inner shell reads what was piped or redirected to it, and a copying writer whose one unquoted operand the shell may split into two refuses while a project is in play (a `${...}` word the guard cannot read as a script, a producer outside its output model (since round 6's second commit, 2026-09-21, the model reads a subshell or a group of echo, printf and silent commands as what it prints), a redirection on the closing brace of zsh's brace-body compound and a command whose name is an expansion the resolver never reads stay unread and are named), and
`[[ $a > $b ]]` with `$b` the guard cannot read refuses from a tracked cwd, a
stated cost (compare from a directory outside the project, or with `expr`); a link the
command makes is followed into a numeric name's folder too, and one whose source
is not literal refuses a numeric write through it; a python or node path that is
a plain string is judged by its text whatever it holds (a `$` is text), while
one built from an f-string, `.format(`, `%` or a template literal with `${}` is
refused as unreadable; a hard link, `cp -l`, `cp -s`, `link` or a link whose
source is not literal puts the project its SOURCE lies in in play from any
working directory, and one whose source the guard cannot read refuses from any;
the inert shell-option lists carry their criterion (an option is inert only if
it changes neither how a word is expanded, matched or split, nor where a
relative path resolves, nor which grammar is in force; `set -f`, `noglob`,
`nomatch`, `markdirs`, `cdsilent`, `pushdminus`, `extquote`, `set -k` and their
kin are off them, and bash's `set -k` is read both ways); and the remedy line
quotes its `--file` path in single quotes, so a path holding a `$` pastes back
unchanged. Its second commit (B2 as the reviewer ruled it, option (c) on the
measured delta: the resolution half kept, the refusal half dropped) reads the
values it can: a name the command sets to a plain string earlier (`x='../sub'`,
`export x=...`, at the top level in plain sequence), HOME, PWD, OLDPWD, `~+` and
`~-`, resolving them in every word and judging the real path (so `x=other.md;
echo hi > docs/$x` is judged by name and allowed, and `x='../docs/report.md'; cp
base/report.md scratch/$x` refuses by name), and reads none of HOME, PWD and
OLDPWD once the command names the name outside an expansion or may fill it in
(so `PWD=<dir>; cp x $PWD/docs/report.md` from a tracked cwd is refused as not
literal, the reason naming the mention); what stays opaque (a name the command
never sets, one set in a body, after `&&`, in a subshell, by a `read`, a loop,
an eval, a sourced file or a function call, a `$(...)`) keeps the verdict the
working directory gives it, refused as not literal from a cwd in a tracked
project and allowed from a cwd in no project. The principle: a guard is
strictest where its subject is and loosest where its subject is not; this
guard's subject is tracked files inside projects, and from a cwd in no project
it must not refuse on a value it cannot know (a user in a scratch directory
writing `$USER.log` or `$(date +%s).md` is ordinary work, and a guard that
refuses ordinary work gets switched off). The residual, with its boundary: a
literal head outside every project followed by an opaque expansion whose value
can climb with `..` is allowed from a cwd in no project; from a tracked cwd the
refusal stands unchanged. The cost is measured against the corpus, a sample:
none of the 164 ordinary commands changes verdict; of 44 shapes with a literal
head outside every project followed by an expansion, run from a cwd in no
project and from a tracked one, the 22 readable ones refuse 3 times after
resolution, each by name on a tracked file (20 refusals from the tracked cwd
became allowances), and the 22 opaque ones keep their 22 refusals from the
tracked cwd and their 22 allowances from the cwd in no project. A pin addendum
(2026-09-19) pinned the fifth pass's unpinned claims from the tracked cwd, where
an unresolved name is refused and a resolved one judged by name, and closed what
its attacker found, each a stated rule applied to a construct the guard could
already see: `cp --parents` lands each source at its whole path under the
destination, so `cp --parents docs/report.md ../web/` is judged on
web/docs/report.md; python's `-c` is read inside its option cluster with the
code glued on (`-c'...'`, `-uc'...'`, `-Xutf8 -c'...'`) and node's `--eval=`
with its code (`--print=` takes none, node then reads the script from stdin);
and a triple-quoted python path is the plain string it is, while a template
literal holding a quote is still a template. None of the 164 ordinary commands
newly refuses. A seventh pass (2026-09-19) closed what the sixth pass's attacker
found, 77 in-model overwrites in 13 spelling classes of one miss, with the
readability rule stated below (a name is readable only after plain top-level
`NAME=plain-string` writes and nothing else: a tilde opening a value, a
transforming declaration flag, a nameref, a name the shell fills in, a pipeline
or a piped group, a wrapper's argument, a `function NAME {` definition called
later or a subscript each leaves it unreadable, and a plain `unset` frees it
again), reads a plain top-level `HOME=<path>` for the commands after it (the
prefix `HOME=<path> cmd` excluded, since the shells expand that command's
`$HOME` and `~` first), and makes the refusal for a `cd` under `builtin`,
`command` or `time` say which shells move. This guard is best-effort against
known write forms: it refuses the shell writes it models and, by design, allows
anything it does not recognise, so it never blocks ordinary work it cannot read;
it is a backstop, not a complete boundary. The allow-by-default for an
unmodelled writer is deliberately not flipped, since flipping it would refuse
almost all normal work. What it does refuse, while a tracked project is in play,
is a write it reads but cannot place: a target it cannot read, a path it cannot
check (a stat error other than not-found), an option on a modelled writer or
wrapper it does not parse in full, an env -S string, a shell option it does not
know to be inert for paths, a link whose source it cannot read, a `~` or `$HOME`
write beside a mention of HOME or beside a variable name the shell fills in, a
template or format string as an interpreter's write path, and, from any working
directory, a write through an alias the command makes (a hard link, `cp -l`, `cp
-s`, `link`, a link whose source it cannot read) whose source lies in a tracked
project or is one it cannot read. Deleting or moving a tracked file away (`rm`, `unlink`, `mv` to another name, `find -delete`) is not a write it refuses: the contract is the write that lands on a tracked file, and whether the tracked set shrinking is such a write is a scope question raised with the round's review and not decided here. A value it can read is resolved first and the
real path judged. A name is readable only when every write to it in the command
is a plain top-level `NAME=plain-string` the shell performs as spelled: no tilde
opening the value, no declaration flag at all, no `declare`, `typeset` or `local` (dash has none of the three; `export` and `readonly` with no option word are the two declarations every shell performs), no nameref reaching
it, no name the shell fills in, no subshell, pipeline, piped group or body
scope, no `{ }` group opened after `&&`, `||` or `|`, no wrapper argument, no call of a function the command defines in any
spelling, no subscript; any other construct that can write the name, listed here
or not, leaves it unreadable, the doctrine a `read` and a loop variable already
had. HOME, PWD, OLDPWD, `~+` and `~-` are read the same way: HOME after a plain
top-level `HOME=<path>` assignment of its own, and none of the three once the
command names or may fill in the name in any other form. THE RESIDUAL PROPERTY. The guard refuses a write only when it resolves the command to a writer it models (the writer cases of extract's switch, a write redirection, an interpreter's write call it scans) reached through a road it reads (the wrapper set, the shells' script roads, the readings of the resolver, the alias and hash roads), with a target it can place or cannot read. Every write that still reaches a tracked file is one the guard does not resolve to such a writer through such a road, whether or not its text stands in the command, and falls in one of these classes, each measured by execution in tools/romp-track-bash-guard.test.mjs (THE RESIDUAL TABLE, whose rows are the population this statement is over): a writer outside the model, a program, or a write form of a program the hook models, that writes the file by its own nature and is not among the write forms the hook reads (rsync, patch, tar -x, ed, ex, vim, make, shuf -o, gawk -i inplace, awk's print redirect, uniq, scp, openssl -out, shred, curl -o, wget -O, find -exec, a git alias or a subcommand that writes the tree, bash's history -w, zsh's sysopen and mapfile modules, sed's e command and a w command in a sed script the resolver cannot read, busybox's applets); a reader outside the roads, a program that runs a command or a script the hook does not follow into it (xargs, an interpreter's system, exec or subprocess call, a wrapper outside the set, a shell outside SHELLS, a file the command writes and then runs or sources, a function's call of itself, which the replay does not follow again); a command name the resolver never reads, a command whose name is an expansion of a kind the resolver does not read ("${a[@]}", a loop variable, a name read or filled by getopts, printf -v or a nameref, a name the shell itself sets (${SHELL}, $0, $BASH, $ZSH_ARGZERO, $_ after a command), a substitution outside the output model such as $(which cp), a ${...} operator form the resolver does not read, a positional parameter of a script handed to a fresh shell with arguments of its own; "$@", $1 and $* stand for the operands of a called function or of a `set` this shell ran since round 6's sixth commit); a script held in a variable, a value the command gives a name through a construct the resolver does not read (`read`, `printf -v`, a positional parameter of a fresh shell's script), run as a command or handed to a shell (`$c` after `read c`, `eval "$1"` inside a `bash -c` given arguments, `bash -c "$c"` after `printf -v c`; a value an assignment word gives, whitespace included, is read through THE HEAD CANDIDATES since round 6's fourth commit, and a `${name:=word}` gives word since the sixth); a producer outside the output model, a pipe into a shell from anything but a literal echo or printf, alone or in a subshell or group of such commands, or a plain cat passing such a text through (a call of a function the command defines, a tee or a pipe through another command, a cat of a file); zsh's glob grouping, a `(..)` inside a word handed to zsh, read as a subshell by the lexer's zsh grammar while zsh globs it (a lexer gap, stated since the first commit of this round); zsh's hook functions, a function the command defines under a name zsh calls on its own (chpwd, precmd, preexec, periodic, zshexit, and the names in chpwd_functions and its kin), whose body runs when the shell moves, prompts or exits, from the directory the shell is in then, while the guard judges the definition where it stands; an opaque expansion from a cwd outside every project, a leading opaque expansion, or one after a literal head outside every project, from a cwd in no project (B2 as ruled, with its boundary). A shape outside these classes that reaches a tracked file is a rule to state, not a residual. Whichever way you
write a tracked file, use `track-edit`, so your change comes back to be accepted
or rejected.

For ANY change to the file, use the CLI, NOT the Edit/Write/MultiEdit tools:

- **Make or replace text** — applies the change AND records it as your tracked
  suggestion (attributed to your session, colored by you):

  ```bash
  node ~/.claude/hooks/track-edit.mjs --file <ABSOLUTE path> \
    --old "<exact, unique text to replace>" --new "<replacement>"
  ```

  `--old` must be an exact, unique substring of the file AS IT STANDS NOW.
  `track-edit` REWRITES the file (it applies old→new, then records the op), so your
  next `--old` must be matched against the post-edit text — re-read the file if
  you're unsure rather than quoting your own earlier `--old`. Make ONE focused
  change per call so each reads as a clean diff, and write NO CriticMarkup or diff
  syntax: the text stays clean of markup and the editor derives the diff from the
  sidecar.

  Revising an earlier suggestion of your own? Running `track-edit` again does NOT
  create a revision step — the op-log has no revision chain, and adjacent
  same-author ops COALESCE, so a second edit over the same span silently rewrites
  the existing suggestion instead of adding a turn the reviewer can see. That is
  fine: the reviewer reads the suggestion as it stands now. Do NOT pass `--thread`
  to `track-edit`, even when you are revising in answer to a comment you were
  pinged about: an edit tied to a comment is shown inside that comment instead of
  as its own change in the text, and the reviewer found that confusing. Make every
  edit with plain `track-edit`; when the comment needs words, answer it with
  `track-reply --thread <id>`.

- **Comment on / highlight a span**:

  ```bash
  node ~/.claude/hooks/track-comment.mjs --file <ABSOLUTE path> \
    --anchor "<an exact span copied from the file>" --note "<your comment>"
  ```

- **Reply into a thread** (when the reviewer replies to one of your changes):

  ```bash
  node ~/.claude/hooks/track-reply.mjs --file <ABSOLUTE path> \
    --thread <id> --note "<your reply>"
  ```

The file text stays CLEAN in the sense that matters to the reader — no CriticMarkup,
no diff syntax, nothing but prose — but it is NOT unmodified: `track-edit` writes
your replacement into the file and records the op alongside it, and the editor
renders that op as an accept/reject diff in its review panel.

**One session at a time per file.** There is no locking and no merge. `track-edit`
reads the file at run time, so `--old` is matched against the file AS IT STANDS, not
against what you read earlier: after another session's write your `--old` may no
longer be found (an error, nothing written), or may still match and land against
text you have not seen. When the file changed under changes pending in the sidecar,
`track-edit` usually DETACHES the displaced changes (they stay in the sidecar,
shown as stale) and applies your edit anyway. It REFUSES ("The note changed since
it was read…", nothing written) only when a displaced change is seconds old, since
the other writer's file write may still be in flight; re-read the file and redo
your edit against its current contents. If you know another session is editing
the same file, coordinate with it rather than interleaving edits.

The CLIs locate the project root by `.obsidian/` / `.git/` / `.trackchanges/`, so
they work in a vault OR a plain code repo; set `TRACKCHANGES_ROOT` only if a file is
outside all of those.

## Messages from the editor (either mode)

Two prefixes reach you from Obsidian / VS Code, and both mean "you are the editor
for the file named here":

- **`[obsidian]`** — the commonest one: the message box in either editor, naming the
  file by ABSOLUTE path (`re: <path>`), optionally quoting a `Context:` block of the
  user's selection, then their message. No thread id, so answer in words in your
  normal reply and make any requested change with the right tool for that file's
  mode.
- **`[obsidian-diff]`** — a review-panel ping about a change or a comment: the file
  by ABSOLUTE path, the reviewer's message, and a THREAD id. One message may list
  several comments on the same file, each with its own thread id; address each one
  and reply into each by its own id. A message may also carry only the reviewer's
  accept and reject decisions on your earlier changes, with no comment and so no
  thread id to reply into: nothing needs an answer, and the file already reads as
  decided.

A thread ping can arrive in EITHER mode — answering a thread is a conversation,
separate from how your edits land. Words go back into the thread; edits go into
the text, never linked to the thread:

- **answer in words** with `track-reply --thread <id>` — always available, in
  tracked OR normal mode; it just appends your message to that thread.
- **revise the text** if asked: in tracked (`on`) mode use plain `track-edit`, with
  no `--thread` (the edit shows as its own change in the text, where the reviewer
  accepts or rejects it); in normal (`off`) mode just edit the file directly with
  Edit/Write. Either way, when the comment needs words — to say what you changed,
  or why you did not — `track-reply --thread <id>`.

When you have addressed everything in a message, ask me for another look the same
way you asked for this one, naming the file.

## Starting fresh (a new session opened to edit a file)

If you're a new session and the first thing you're handed is a request to edit a
file this way (a message naming an absolute path + what to do), just begin: check
the flag (`track-config.mjs` above), read the file at that absolute path, and make
your first change with the right tool for the mode — `track-edit` when ON, Edit/Write
when OFF. You don't need any handshake; if it's ON the user is already watching the
review panel.

## Notes

- Always identify the file by the ABSOLUTE path you're handed — this session may
  be in a different working directory, so a relative path won't resolve.
- Editor mode = one focused change at a time, so each is a clean, reviewable diff.
- When you commit work in a project that has a `.trackchanges/` folder and does not
  ignore it, include that folder in the commit: it holds the user's comments on your
  files and the record of your tracked changes, and it is part of the project's
  history.
