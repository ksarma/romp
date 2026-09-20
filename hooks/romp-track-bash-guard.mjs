#!/usr/bin/env node
// romp-track-bash-guard.mjs, a PreToolUse hook on the Bash tool: refuse a shell command that would
// write a TRACKED file (plans/file-review.md, decision 47).
//
// The vendored guard (vendor/track-changents/hooks/track-guard.mjs) denies a raw Write / Edit /
// MultiEdit on a tracked file and points the session at track-edit. It never sees a write made
// through the Bash tool, and a session in auto mode is told to make its file changes that way: cp
// and mv over the file, tee, a heredoc redirected into it, sed -i, a python or node one-liner. A
// dry run (2026-09-09) saw a session run track-config and cp in one compound command on a tracked
// file; the flag printed on and the cp landed raw, with no change recorded for the person to accept
// or reject. This hook closes that path.
//
// It reads the command, extracts the paths the command would write (extractWriteTargets below
// states the grammar), resolves them against the session's working directory (the payload's cwd;
// a `cd` earlier in the command moves it, and a `cd` inside a subshell moves it only up to the
// closing parenthesis, as in the shell), and refuses (exit 2, the reason on stderr) when one of
// them is a tracked text file of its project, per that project's .trackchanges/config.json, read
// through the same store-io the CLIs and the vendored guard use. A path is judged under its own
// name and under the name the kernel would open: every symlink in it resolved, and a `..` after a
// directory that exists applied to that directory's REAL path, as the kernel applies it, not to its
// spelling (review round 3, 2026-09-19: `<out>/link/../docs/report.md` was folded to
// `<out>/docs/report.md` before the resolve step, the link segment gone, and the write landed on the
// tracked file the link led beside; a `..` after a directory that does not exist yet folds lexically,
// so `mkdir -p <out>/run-$$ && echo x > <out>/run-$$/../plain.log` keeps its verdict), so a link to
// a tracked file does not carry a write past it. A read-only command (cat, grep, diff, git) names no
// write target and passes. A command the extraction cannot see through (eval, xargs, a script held
// in a variable) passes too: never a silent block of ordinary work. So does a python or node
// one-liner whose write path is computed (a name, `sys.argv`, `os.environ`, `process.env`): the
// interpreter scan reads a literal path (by its text, whatever characters it holds, since the fifth
// commit) and, since that commit, refuses a template or format string (an f-string, `.format(`, `%`,
// a template literal with `${`) as a path it can see is filled in; a scan that flagged a computed
// one would refuse ordinary scripting and still miss the common forms (review round 1, 2026-09-18,
// by execution); the vendored skill tells the session not to write a tracked file that way. A write
// whose TARGET it cannot read is refused, though, while a tracked project is in play (2026-09-18; a
// research session reported through the box admin, 2026-09-17, that a `cp` whose operands were shell
// variables overwrote a tracked file with no change recorded, while the same cp spelled out was
// refused: the hook dropped every target it could not read). Such a target is one built from a
// variable, a `$(...)` or a backtick, a `~user`, a brace list past the cap, or a glob the hook
// cannot expand (no match, the cwd unknown, past the caps); in play means the session's cwd, the
// directory a `cd` moved to, or the folder a copy lands in sits under a `.trackchanges/config.json`
// whose tracked list holds an entry the literal rule could refuse (a text name the veto list does
// not cover, or a note the link closure reaches from one), the directory judged under its real path
// and its name, and for a copy's landing folder only when a tracked file could land there
// (inPlayFor and its helpers, below); a landing folder that no project claims counts too when an
// entry of it is or leads to a tracked file whose name the copy could take (round 3: `cp "$SRC"
// <outside>/` over a link there onto a tracked file overwrote the file while the same copy spelled
// out was refused; guardedEntryIn). The project the target's OWN literal directory part sits in is
// asked first, from any cwd, for every such target the hook can place, absolute or relative to a
// write-time directory it knows, when a tracked file could land in that folder (round 2 for a numeric
// target; round 3 for every unreadable word and for a relative spelling, after `cp x
// <project>/notes/$N.md` from a cwd in no project overwrote a tracked note while `<project>/notes/`,
// the literal name and the numeric spelling were all refused). A LITERAL relative target after a
// `cd` the hook cannot follow (a `cd` to a name the shell fills in, `cd -`, `popd`, a `cd` inside an
// if, loop or case body, or a `cd` to a directory the command cannot enter when the hook runs, one
// the command may make first or one the cd fails on, leaving the shell where it was) is refused too
// while the cwd's project is in play, with the reason (the directory is not known) and the remedy
// (an absolute target, or a `cd` to a literal directory that exists), where before it was dropped:
// one such `cd` turned a refused write on a tracked file into an allowed one (round 3; the cost, a
// `mkdir -p build && cd build && cmd > log.txt` from a tracked cwd, is stated in decision 47).
//
// One narrowing, from the round-1 review and corrected twice since: a target whose only expansions
// are `$$` and `${$}` and whose text lands outside every project in play is dropped, since the
// shell's process id cannot carry a path separator back into the project (`/tmp/build-$$.log`, the
// commonest such write, refused inside every tracked project before round 1). The set is those two
// spellings and NOTHING ELSE, in every shell (review round 3, 2026-09-19): every other candidate can
// be unset or shadowed by the command and then hold a path. Round 1 listed `$RANDOM`, `$SECONDS` and
// `$BASHPID` as read-only integers; round 2 dropped BASHPID (zsh leaves it assignable) and kept the
// other two under bash and zsh, per shell; round 3 measured `unset RANDOM; RANDOM=../x`, `local
// RANDOM=` inside a function and `declare -g` in bash, `typeset -h RANDOM` inside a function in zsh,
// and a sourced file carrying the unset, each of which carried a traversal onto a tracked file while
// the hook read the word as numeric. No shell refuses every road to assigning those names; every
// shell refuses every road to `$$` (`unset '$'` is not a valid name in bash, zsh or dash). The cost
// is stated, not hidden: a legitimate `log.$RANDOM` inside a tracked project is refused, with the
// reason and a one-step remedy (name it with `$$`, spell it out, or write outside the tracked
// project), a false refusal that is recoverable, where an overwrite with no change recorded is not.
// A numeric target is judged by where it lands: its literal directory part resolved through the
// filesystem (a link in it, and a `..` after one), each existing entry of that directory whose name
// the process id could spell (`x-4242` for `x-$$`) followed as the write would follow it (round 3:
// an entry made before the command, a link into a tracked folder, was not resolved), and a fold
// that leaves no expansion handed to the literal rule (a fold onto a link to a tracked file was
// allowed while its literal spelling was refused). Deliberate false refusals of this rule, each
// stated in decision 47 and pinned in both directions: a numeric name whose literal directory part
// is a folder where a tracked file could land is refused from any cwd while its literal spelling may
// pass (`<root>/x-$$/y.md` and `<root>/docs/build-$$.log` alike; the landing gate is folder-granular,
// so the class is the gate on the literal directory part, not the first segment as round 2's
// addendum stated it), with a refusal that names the folder when the expansion names one and offers
// a literal name or a write outside the project (unknown-folder text, in evaluate); a numeric name in
// a folder of more than 2000 entries inside a tracked project is refused unscanned (LANDING_SCAN_CAP,
// which the own-project step shares with a copy's landing folder); a segment that is nothing but an
// expansion cancelled by a `..` (`<out>/$$/../x.md`) is not narrowed, since such a segment could be
// empty at run time were the set ever widened, and the shell would climb one level higher than the
// fold. Two things this rule does not see, stated: a link the same command creates under or after the
// numeric segment (the pid-candidate scan reads only entries that exist when the hook runs; a same-command
// `ln -s` with literal operands and an untouched name BEFORE the numeric segment, in the literal directory
// part, IS followed since the fifth commit, M3, evaluate holding the command's links while it places the
// target), and an entry named by the process id in a folder OUTSIDE every project
// that holds more than 2000 entries, which is not listed (a fail-closed cap there would refuse every
// temp log in a large `/tmp` from a tracked cwd, round 1's false refusal; this box's `/tmp` held 2767
// entries when measured on 2026-09-19). A variable of unknown content, a substitution and a bare
// expansion stay refused whatever their literal text, because a `../` inside the value reaches back
// in (verified by the review by overwriting a tracked file); a `$(date)` in a log's name is refused
// too, and that class is stated, not solved.
//
// Quoting forms (round 3): `$'...'` is ANSI-C quoting in bash and zsh, a literal word with the
// escapes processed (a `$'<tracked path>'` was a non-literal word dropped from a cwd in no project,
// and bash wrote the tracked file); inside a script the command hands to `sh`, `dash` or `ksh` the
// word is one the hook cannot read, since dash reads a literal dollar and a single-quoted string,
// bash in POSIX mode reads ANSI-C quoting, and the hook does not know which `sh` is, so its text is
// the path bash would write and the own-project step judges that spelling. `$"..."` (bash's locale
// translation; a literal dollar in zsh) is read with the double-quote rules and kept non-literal. A
// bare `$` before anything but a name, a digit, a special parameter, `{`, `(`, `'` or `"` is a
// literal dollar in bash, zsh and dash alike, so it is text: a folder whose name holds a dollar
// (`\$dir`, `'$dir'`, a project at `p$x`) is judged by that literal name, where before every dollar
// in a word's text read as an expansion (a literal-dollar folder took the unknown-folder refusal
// with a false reason, and a numeric write into a project whose root name held a dollar was allowed
// while its literal spelling was refused). The lexer's marks say which characters came from an
// expansion (the third mark, `x`), and every reader below decides on the marks, never on the text.
//
// Of the session's environment the hook reads HOME (for `~` and a leading `$HOME`, as the shell
// would), TRACKCHANGES_ROOT (the root override the CLIs honour, for a directory under it) and
// ROMP_SID, and no other environment variable, whatever the command names (that would read names
// shaped like secrets and guess at the cwd); since B2 (below) it does read a name the command's OWN
// TEXT sets to a plain string, and PWD and OLDPWD from its own directory model, never from the
// environment. Of the environment's values only HOME's can appear in a refusal, and only
// as a path the hook resolved through it (the target a `~/` or a leading `$HOME` names, or the
// project root a bare `cd` lands in); a value the command's own text set can appear too, as the path
// it resolved to (round 5 of the review, 2026-09-20, correcting a sentence B2 had made false); TRACKCHANGES_ROOT is named by the variable, never by its value,
// and ROMP_SID is never printed (review round 2, 2026-09-18, correcting a round-1 clause that claimed
// no environment value reaches a message: a `"$HOME/x.md"` target is expanded and refused by its
// resolved path, which is HOME's value). The refusal says the target is not literal and asks for the
// path spelled out, which then takes today's verdict (a file outside the project runs as usual, a
// tracked one goes through track-edit). With no such project in play the word is dropped, as before; since B2 (below)
// an expansion whose value the guard can read is resolved first, and the resolved path takes the literal verdict.
// Like the vendored guard it lets a non-text file through (an image or a PDF cannot take a tracked
// edit, so the raw write is the only way to regenerate a figure), and it exits 0 at once, before
// stdin is read, when ROMP_SID is absent from its environment (decision 24: registered machine-wide,
// inert in every session romp did not launch).
//
// Cost: a couple of small reads of config.json per target and, when the project's tracked list is
// non-empty and a target is not on it by name, ONE walk of the project's markdown tree per call
// (store-io's link closure, the same walk the vendored guard pays once per Write), however many
// files the command lands: a directory copy of hundreds of files must not pay the walk once per
// file, or the call outruns the installer's 10 s hook timeout and the harness runs the command
// unjudged. A glob operand costs a listing of the directories it names; a directory source costs a
// listing of the source tree (less than the copy itself pays), skipped when the landing directory
// does not exist yet under any project that tracks anything; a numeric target costs a listing of
// its literal directory (bounded by LANDING_SCAN_CAP) and a `..` after an existing directory one
// realpath.
//
// Round 4 (2026-09-19, the walk-around lens) closed eight more in-model roads: cp/mv/install/ln read a per-writer
// option table (COPY_OPT), so a flag that takes no argument (`-Z`, a bare `--context`) no longer eats an operand
// and an option the table does not know refuses the command; `env -C DIR`, `env --chdir=DIR` and `sudo -D DIR`
// run the inner command in DIR (its relative operands judged there, this command only); the wrapper set gained
// `setsid`, `flock`, `taskset`, `chrt` and `numactl`, each peeling its own operand (`flock … -c 'cmd'` reads the
// script like `sh -c`); a same-command assignment to HOME (`HOME=…`, `export HOME=…`, `env HOME=… cmd`) makes
// `$HOME` and `~` unreadable for the rest of the command; a word whose literal head parents a tracked root, or
// sits under one, refuses (a non-numeric expansion can spell a root or carry a `../` into it); a directory the
// hook cannot search before a `..` is unresolvable, not folded lexically; and a symlink an `ln -s` makes earlier
// in the same command redirects a later literal target to what it points at.
//
// The walk-around lens, second pass (2026-09-19) closed six FAMILIES of in-model write the hook read yet let through,
// each stated here as one rule, not a list of cases. (1) OPTION TABLES: the per-writer tables and sort's `-o` accept a
// glued short form (`sort -oFILE`), so the operand is recognised; `env -S`/`--split-string` runs a shell string and is
// read like `flock -c`, not skipped as an operand. (2) ANY ASSIGNMENT FORM: HOME (the one variable the guard expands)
// as an lvalue in any form the shells offer (`HOME=`, `HOME+=`, `export`/`declare`/`typeset`/`local`/`readonly HOME`,
// `read HOME`, `printf -v HOME`, `mapfile`/`readarray HOME`, `env HOME=… cmd`, `getopts … HOME`, `for HOME in`)
// makes `$HOME` and `~` unreadable for the whole command (since the third pass, the bare identifier anywhere, below). (3) IN-COMMAND PREFIX MUTATIONS: an earlier
// `rm`/`rmdir`/`mv`/hard `ln`/`cp -l`/`cp -s` that removes, renames or aliases a path makes every later word under
// that prefix unreadable, since what it resolves to at run time is not what the hook sees (mutated/recordMutations);
// the `ln -s` class-H rewrite is kept only when nothing else in the command touched the link name or its source, and
// a relative link source resolves against the LINK's directory as the kernel does. (4) STAT ERRORS REFUSE: a stat,
// lstat, realpath, readdir or config-read error other than ENOENT (a mode-000 parent, a mode-000 tracked folder or
// `.trackchanges`, the whole project mode 000, EACCES, ELOOP, ENOTDIR) anywhere on a judged path is an answer the
// hook does not have, so it REFUSES from any cwd, naming the error and the path (UnknownPath; the class-G flip applied
// to the class, since a directory it cannot search may itself be a tracked project). (5) NESTED MARKERS: a `.git`,
// `.obsidian` or `.trackchanges` found between a tracked project's root and the target refuses, naming both markers,
// where store-io's nearest-marker rule would read the write as untracked (outerTrackingRoot); the nearest-marker rule
// stays for the untracked case. (6) A cd THE GUARD CANNOT KNOW leaves the directory unknown from that point (as `cd -`
// already does), so a later literal relative target refuses with the construct named: a cd after `&&`/`||` (its run
// depends on the previous status), a cd in a pipeline or backgrounded (a subshell), a cd under a wrapper (an external
// `cd` that does not exist), `pushd -n` or a pushd rotate, a physical cd (`cd -P`, after `set -P`, or an option the
// guard does not model), and a call of a function whose body ran a cd (the body is modelled as not moving the shell,
// the CALL as unknown). A plain unconditional cd in sequence keeps its handling; `env -C DIR` resolves its operand
// physically, as chdir(2) does. Each family errs toward a false refusal, recoverable in one step, never a missed
// overwrite; the costs are listed with the change.
//
// The walk-around lens, THIRD pass (2026-09-19) re-keyed six of those rules on what the guard can SEE, after a third attack
// walked around each enumeration with the next spelling (a nameref and `select HOME in` past the assignment forms; a
// glued `env -Cdocs`, an abbreviated `env --chd=` and `--c`, a nested `env -C docs env -C ..` and an `env -S` string
// beginning with env's own option past the wrapper lists; a non-literal `ln -s` source past class H; zsh's `set -o
// chaselinks` past the physical-cd list; a two-segment expansion under a grandparent past the direct-children scan; and
// `cp --targ` from a cwd in no project past the unknown-option refusal). The reviewer's rule (2026-09-19 08:50Z,
// paraphrased): a rule implemented as an enumeration of spellings is a case list, and the next spelling walks around it;
// a rule is keyed on a token, an unparsed option, a non-literal operand or the presence of a construct, never on a list
// of forms. (a) BARE IDENTIFIER: the identifier of a variable the guard expands (HOME, EXPANDED_NAMES) appearing anywhere
// in the command outside a `$`-expansion makes that expansion unreadable for the whole command, and a bare `cd` or a `cd
// ~` after it leaves the directory unknown (bareExpandedNames); no list of assignment forms. (b) FULLY PARSED OR REFUSED:
// every wrapper in PREFIXES is parsed against its own option table (WRAPPER_OPT) or the command refuses naming the option
// (unknown, abbreviated, glued to a letter the table lacks, or filled in by the shell), the words after it judged by their
// own project; a nested chdir composes (`env -C a env -C b` enters a, then b under a); `env -S`/`--split-string` and
// sudo's -e, -i, -s, -R and -h are opaque and refused outright, never recursed; `time -o FILE` is a write of FILE.
// (c) NON-LITERAL LINK SOURCE: a symbolic link whose source the guard cannot read or place marks the link NAME as mutated,
// so a later write through it refuses (recordSymlink); class H keeps only a literal source it can place. (d) SHELL
// OPTIONS, AN ALLOWLIST: an option on `set`, `shopt`, `setopt` or `unsetopt` that is not on the inert lists
// (INERT_SET_LETTERS, INERT_SET_OPTIONS, INERT_SHOPT: exit status, tracing, history recording, completion, prompts, job
// control and syntax choices that move no path, built from the shells' own option lists) leaves the directory unknown from
// that point (shellOptionChange); since the fifth commit every entry is decided by THE CRITERION stated at the tables
// (nothing that changes how a word is expanded, matched or split, where a relative path resolves, or which grammar is in
// force), which took `-f`, `noglob`, `nomatch`, `markdirs`, `cdsilent`, `pushdminus`, `extquote`, `set -k` and their kin
// off. (e) ANY DEPTH: the parent-prefix rule finds every tracked root
// under the literal head at any depth (parentTrackedRoots, breadth-first, PARENT_SCAN_BUDGET). (f) UNKNOWN OPTION REFUSES
// EVERYWHERE: an option a writer's table does not know refuses on every path the writer is reached through, each
// candidate operand judged by its own project from any cwd (optionCandidates), and the mutation and symlink recorders
// mark every candidate. Also from that pass: `chdir` (zsh's and dash's cd, no command in bash) leaves the directory
// unknown, and coreutils `link` is a hard-link maker (a write target and a family-3 mutation). The costs, each stated and
// measured in tools/romp-track-bash-guard-corpus.json: a `~/` write beside a mention of HOME, an `env -S` line, a
// relative write after `shopt -s globstar`, a write through a link whose source is a variable, and a variable-named
// file in a folder that holds a tracked project at any depth beneath it, each from a cwd in play (the last from any).
//
// THE FIFTH COMMIT (2026-09-19, the reviewer's ruling on the fourth pass, whose three attackers and literal-dollar
// matrix ran against the head with the six rules) closed six misses and settled a boundary question, each keyed on a
// visible construct and never on a spelling. M6, first: 576 of the matrix's refusals put a shell-live `$` inside the
// double quotes of the remedy's `--file "..."`, so the pasted line named another file in bash and a third in zsh; the
// argument is single-quoted (shellQuote, trackEditLine), pinned by a paste through real bash and real zsh. M1: rule (a)
// keyed on the literal identifier, and a variable NAME assembled from expansions or spelled by a substitution (`export
// ${h}${m}=...`, `declare -n r=${h}${m}`, `printf -v "${h}${m}"`, `typeset ${h}${m}=`, `read ${h}${m}`, `export
// "$(printf 'HOME=...')"`, `read -r "$(printf HOME)"`) reassigned HOME with no literal token; now a name operand that is
// not a literal identifier on any assignment, declaration, nameref, export, typeset, local, readonly, read, mapfile,
// getopts, unset or `printf -v`, or an expansion in lvalue position of a `let` or `(( ))`, marks every expanded name
// unreadable for the whole command and a bare `cd` or `cd ~` unknown (assembledNameOperand, homeUnreadableWhy); a
// literal name other than an expanded one and a read-only twin change nothing. M2: the redirection lexer did not consume
// zsh's clobber-override `!` after `>`, `>>`, `&>` and `&>>`, so the tracked file became a plain argument and zsh
// clobbered it; the lexer now consumes `!` and `|` after `>`, `>>`, `>&`, `>>&`, `&>` and `&>>` (clobberSuffix,
// WRITE_REDIRECTS), records the operator as spelled, and records bash's reading beside zsh's where they differ. M3: a
// class-H link with literal operands made BEFORE a numeric segment, in the literal directory part of a numeric target,
// was neither followed nor refused (applyInCommandLinks ran on the literal fold, and the numeric view resolved the
// directory through a filesystem where the link did not yet exist); extract now returns the command's links and evaluate
// follows them while it places the targets it could not read, and a numeric or opaque word under a prefix an earlier
// command mutated is refused with the family-3 reason (mutatedUnderLiteralPart). M4: the interpreter scan dropped every
// literal path matching `[{}$]` and the node classes excluded `$`, so a literal path in a tracked folder holding a
// dollar was never judged; a `$` in a plain string is text, so the path is kept and judged by name, and a template or
// format string (an f-string, `.format(`, `%`, a template literal with `${`) is unreadable and refuses while a project
// is in play (scanScript, scriptTemplateTargets), while a computed path stays out of model by the contract. M5: eleven
// options sat on the inert lists against the rule; the lists now carry THE CRITERION (at INERT_SET_LETTERS_WHY) and
// every entry its reason, the eleven and what the criterion took off with them are gone, and bash's `set -k`, measured
// writing a tracked file through a `cp` the guard read as writing nothing, is read both ways (setsKeywordMode). B1
// (ruled yes): a recorded alias (a hard link, `cp -l`, `cp -s`, `link`, a symbolic link whose source the guard cannot
// read) carries its source, and the in-play question for a write through it is asked of where the write LANDS, from any
// cwd (aliasSourceInPlay): a source in a tracked project puts that project in play, a source the guard cannot read
// refuses from any cwd, a source outside every project is allowed. The costs, measured against
// tools/romp-track-bash-guard-corpus.json (none of the 164 ordinary commands newly refuses): a `~/` write beside a
// `printf -v "$name"`, a relative write after `set -f` or `shopt -s nocasematch`, an f-string path from a tracked cwd,
// and a write through a link whose source is a substitution from a cwd in no project.
//
// B2 AS RULED (THE FIFTH PASS'S SECOND COMMIT, 2026-09-19; the reviewer's option (c) on the measured delta: the
// resolution half kept, the refusal half dropped; the dropped sequence is fork PR #780's cb0b15422 and 24acdce20). A
// literal head outside every project bounds nothing once an opaque expansion follows it, since a `..` inside the
// value escapes any prefix (the matrix's `x='../sub-on/p$abc'; printf poison > <out>/$x/rep.md` from a cwd in no
// project overwrote the tracked note while class E asked only whether the head parents or sits under a root). So
// extract RESOLVES every expansion whose value it can read before a word is judged (resolveWord, valueOf, and since the
// seventh pass recordPlainWord and recordSegment): a name the command set to a plain string earlier, at the top level in plain sequence; HOME
// through the guard's home; PWD through the directory it knows; OLDPWD, `~+` and `~-` through the directory before a
// `cd` in the same command; none of HOME, PWD and OLDPWD once the command names the name outside an expansion or may
// fill it in (rule (a) and M1, keyed on EXPANDED_NAMES, which lists every name valueOf substitutes:
// unreadableExpandedNames). The resolved word is judged as literal (`x=other.md; echo hi > docs/$x` by name, allowed;
// `x='../docs/report.md'; cp base/report.md scratch/$x` refused by name; `PWD=<web>; cp <web>/base/report.md
// $PWD/docs/report.md` from a tracked cwd refused as not literal, the reason naming the mention of PWD). What stays
// opaque (a `$(...)`, a `${name:-x}`, a name the command does not set to a plain string, a loop variable, a name a
// `read` fills in, any name once an eval, a source, an unknown wrapper option or a call of a function the command
// defines ran) keeps the verdict the working directory gives it: refused as not literal from a cwd in a tracked
// project (class F and the cwd rule, as before B2), dropped from a cwd in no project. THE PRINCIPLE (the reviewer's,
// 2026-09-19): a guard is strictest where its subject is and loosest where its subject is not; this guard's subject
// is tracked files inside projects; from a tracked cwd an opaque expansion is refused before and after B2, since that
// is where the danger and the user's intent live; from a cwd in no project the guard reaches furthest from its
// subject and must not refuse on a value it cannot know. The threat model is the user's own box against ACCIDENT, not
// malice: for the dropped refusal half to be worth the refusals it added, an accidental opaque value would have to
// hold a climbing relative path AND land on a tracked file, issued from a cwd outside every project; a variable
// holding climbing relative text is rare by accident, a user in a scratch directory writing `$USER.log` or `$(date
// +%s).md` is ordinary, and a guard that refuses ordinary work gets switched off. THE RESIDUAL, with its boundary: a
// literal head outside every project followed by an opaque expansion whose value can climb with `..` is allowed from
// a cwd in no project; from a tracked cwd the refusal stands unchanged. The cost, measured against
// tools/romp-track-bash-guard-corpus.json (the b2-readable and b2-opaque entries, 44 shapes from a cwd in no project
// and from a tracked one; a sample of shapes, not the population of commands): none of the 164 ordinary commands
// changes verdict; the 22 readable shapes refuse 3 times after resolution, each by name on a tracked file the value
// reaches (one of them a live overwrite before), and 20 of their 22 refusals from the tracked cwd became allowances;
// the 22 opaque shapes keep their verdicts, refused from the tracked cwd and allowed from the cwd in no project.
//
// THE PIN ADDENDUM (2026-09-19, after the fifth pass's mutation lens and attacker; the second commit of the ruled
// sequence). Seven B2 claims no test held: five are pinned (a mid-word `$HOME` beside a mention of HOME; a loop
// variable, a `read`, a `mapfile` and a `getopts` into a name set earlier; the copy of the names a `$(...)` inherits;
// the fresh scope of a `flock -c` string), with resolution under a bare `.git` repo beside them, each from a tracked
// cwd, where an unresolved name is refused and a resolved one judged by name; the poison of an unknown wrapper option
// and of an `env -S` string is not pinned, disclosed for a ruling (fork PR #780's body: an external command cannot
// reassign the calling shell's names, so whether that poison stays is the reviewer's call, and a pin would fix one
// side of it). The attacker's in-model overwrites are closed, each a stated rule applied to a construct the guard could
// already see, no rule added (the PWD and OLDPWD finding is closed in B2's own commit above: EXPANDED_NAMES names
// every name valueOf substitutes). `cp --parents`, a known flag, had its landing computed as the basename; the source
// lands at its whole spelling under the destination (`under` in copyTargets). Python's `-c` was matched only at the
// end of a word, so `-c'CODE'`, `-uc'CODE'`, `-bc'CODE'` and `-Ic'CODE'` were skipped as unknown options; the cluster
// is read as python reads it. Node's `--eval=CODE` was skipped too (`--print=X` takes no code: node reads the script
// from stdin, measured). A triple-quoted python path was read as an empty string with text after it and dropped
// (pyStringArg), and a template literal holding a quote matched neither the literal nor the template class (nodeStr).
// None of the 164 ordinary commands newly refuses. The contract's writer list names a concatenation and an escape
// sequence among the interpreter paths that pass (measured: `open("docs\x2freport.md","w")` lands).
//
// THE SIXTH PASS (2026-09-19; the mutation lens over the ruled sequence's head: seventy-five mutations, thirteen green,
// each a claim the code made that no test held). Nine are pinned, each with its refused row run unguarded in a real
// shell and every allowed row run with the tracked subset fingerprinted after: the unreadable-name marks reach a
// `$(...)` (PWD reassigned outside and `$PWD` inside: bash and zsh wrote another project's tracked file); a cd the
// guard cannot follow leaves OLDPWD unknown (`cd docs; cd "$(pwd)"; cp <src> $OLDPWD/report.md` overwrote the tracked
// file through the stale value); a nameref, a `printf -v` and a `readarray` into a name set earlier make it
// unreadable (bash landed the write in the tracked folder through each); a `$(...)`'s own assignments do not come back
// (a shared map refused the write by name, falsely); an empty value is not read; with `cp --parents` a destination
// that is not there is read as a directory (cp writes nothing without it; the guard's reading of the landing is what
// refuses); python's `-m` ends the option walk (a heredoc after `-mjson.tool` is the module's stdin data, allowed and
// run). The recordAssignments line that poisoned the names after an unknown wrapper option, an `env -S` string or a
// `flock -c` string was unreachable (each branch continues before recordAssignments runs; the first two poison in
// their own branches of extract) and is removed; a `flock -c` string is pinned as it measures, no poisoner, the later
// write judged by name on the resolved value. Not pinned, for a ruling: whether the poison of an unknown wrapper
// option, an `env -S` string and `xargs` stays (an external command cannot reassign the calling shell's names; both
// sides are observable once ruled). No verdict changes: the corpus's 285 entries keep theirs.
//
// THE SEVENTH PASS (2026-09-19; the sixth pass's ATTACKER on 86c0643ec, whose report the workflow that ran it read as no finding
// when the agent died on 529s, so fd531044b's message and fork PR #780's body said the attacker filed none: it filed 77 in-model
// live overwrites in 13 spelling classes, each a value the command SPELLS that this resolution half resolved to a string the
// shell does not produce, judged the wrong path and allowed while the shell wrote a tracked file; 0 structural). Closed as ONE
// rule, THE READABILITY RULE, stated once at RESOLVED_NAME below and implemented as one predicate (plainSequence, plainValue,
// recordPlainWord, recordSegment, taintWord): a name is readable only when every write to it is a plain top-level
// `NAME=plain-string` the shell performs as spelled, and any other construct that can write it makes it unreadable, keyed on the
// construct's shape and never on a list of commands (the reviewer's framing: B2's unknown-defaults-to-unreadable doctrine,
// already applied to a `read` and a loop variable, applied to assignment; a contract that states its boundary as a list is
// falsified by the first construct nobody listed, which is why the rule replaces the list). The classes: C1 a tilde opening an
// assignment value (plainValue: `~/` and `~` resolve through HOME, `~+` and `~-` through PWD and OLDPWD, a `~user` and a tilde
// after a `:` leave the name unreadable); C2 a declaration flag that transforms the value (at this pass `-g`, `-x`, `-r` and
// `--` alone were inert; since round 5's addendum no option word is, ATTRIBUTE_ONLY_FLAGS picks the refusal's text; the
// attribute persists, so the taint is sticky); C3 a nameref (the target is tainted, or every
// name when the target is one the shell fills in; `unset` does not free a nameref's target, refTargets); C4 an assembled name
// operand (the resolved name is tainted when it resolves, every name when it does not); C5 scoping (a pipeline's tail, a `{ }`
// group whose closing brace is piped or backgrounded, a wrapper's argument, an assignment-only segment's words read left to
// right; C5e, `time x=b` and a prefix on a special builtin, shell-dependent and unreadable); C6 functions (`function NAME {` is
// a definition; a call by the head as spelled, a wrapper's name included, poisons); C7 a subscript. Found with the fix, the same
// rule's unlisted spellings, each a live overwrite at 86c0643ec: an eval that assembles `HOME=` then a `~` write (the poison
// now covers HOME, PWD and OLDPWD), zsh's `print -v x` and `${x::=..}`, and a piped `{ cd docs; }` group whose cd was followed
// (the group frame restores the directory). A plain `unset NAME` in plain sequence RESETS the name (the shells drop its value
// and attributes, measured), so a plain write after it is readable again. From a tracked cwd every one of the attacker's 62 rows
// there refuses, by name where the value resolves (a `~/` value, an assembled name that resolves, two assignment words read
// in order) and as not literal with the construct named otherwise; from a cwd in no project the 15 rows the guard resolved
// wrongly split into 5 refused by name (the value resolves) and 10 the ruled residual (an opaque expansion after a literal head
// outside every project, allowed, and the write lands: the boundary B2 states, unchanged by this pass). The cost, measured
// against the corpus (285 entries, no verdict changes) and the dollar matrix and stated with the change: a `~/` value resolves
// through HOME at no cost; `declare -i x=5` (and `-a`, `-A`) then `$x`, `let x=5` then `$x`, a pipeline-tail assignment (which
// zsh keeps) and a piped plain group then `$x` each refuse from a tracked cwd where the shell's value was known.
// THE ADDENDUM (romp-manager's four items, the same day): (1) a plain top-level `HOME=<path>` assignment is the one readable
// write to HOME (readableHomeWrites): `~` and `$HOME` in LATER commands resolve through it, a bare `cd` moves to it (resolved
// against the cwd like `cd <dir>`; a bare `pushd` is no such move: bash and dash stay, zsh goes home, so it leaves the
// directory unknown, a live overwrite since before this pass closed with it), and a
// `$(...)` and a script handed to a named shell inherit it (the shells keep HOME exported), while the prefix form `HOME=<path>
// cmd` stays unreadable with its own reason (unreadableExpandedNames, kind 'homePrefix'), since bash, zsh and dash expand cmd's
// `$HOME` and `~` before the prefix applies and cmd itself runs under the new HOME; (2) the refusal for a cd under `builtin`,
// `command` or `time` says what each shell does (WRAPPED_CD_WHY: bash and zsh move under `builtin`, bash and dash under
// `command`, bash and zsh under `time`; the verdict stays unknown), where it said the shell does not move; (3) the prefix form's
// own text, above; (4) the test file runs its real-shell evidence legs through one probe that reports a shell that is
// missing or too old with a `NOT RUN` line per leg, never a silent pass (CI's shell job has no zsh; since round 5 the probe
// covers dash and a bash below the 4.3 the legs need, macOS's 3.2, and any spawn of a shell the probe declined throws).
// THE SEVENTH PASS'S ATTACKER (2026-09-19; on 93bb93b68, at the rule's own boundary): two misses, 0 structural, each a construct
// the lexer already produced that the implementation realised at one level only, and a sibling found while closing them.
// F2, a `{ }` group NESTED in a piped or backgrounded group (13 live rows in bash, zsh and dash, a cd face included): one
// frame opened for the first `{` and popped on the FIRST `}`, so the piped OUTER brace was never a subshell boundary and
// `x=docs/report.md; { { x=scratch/keep.md; }; } | cat; cp base/report.md $x` resolved x to the inner value; the group
// frames are nesting-aware (openGroup, closeGroups: a group closing in plain sequence hands its names to the enclosing
// group, a piped or backgrounded close taints every name and restores the directory, and zsh's trailing `}` of `{ cmd }`
// closes after the segment, pendingClose), and a declaration inside a group notes its name too (noteGroupName: `{ declare
// x=..; } | cat` and `{ export x=..; } | cat` kept x readable at ONE level, found here). F1, zsh's precommand modifiers
// `noglob`, `nocorrect` and `-` (ZSH_MODIFIERS; 14 live rows in zsh alone, `noglob cd` and `builtin noglob cp` included;
// bash and dash fail on the word with 127 and write nothing): they were read as commands named so and the writer behind them
// was never seen; they are wrappers of the shape of `command` and `builtin` (a reserved word, no option, one command after
// it), with an empty WRAPPER_OPT table and a WRAPPED_CD_WHY text for a cd behind one. RO, found beside the attacker's readonly
// rows: `readonly x=docs/report.md; declare x=scratch/keep.md; cp base/report.md $x` (and `typeset`, `export`, `unset`) wrote
// the tracked file in bash and dash, which keep the readonly value and continue past the error, while the guard adopted the
// later value; a readonly name keeps its value and every later write is skipped (readonlyNames), the one write outside the
// plain form that resolves at no cost (the attacker's plain-reassign rows abort every shell and were safe by shell
// semantics; they are refused by the readonly value now). The one twin that moves: `command noglob cp ...`, allowed before
// and refused by name now, a spelling no shell runs (`command` looks `noglob` up as an external program), priced in fork PR
// #780's body.
//
// ROUND 5'S SECOND ADDENDUM (2026-09-20; the round's verifier, driving the addendum's rows and its own): two live false allows in
// zsh alone, one reading of a `}` behind both, a closing brace that shares a segment with the command before it. (1) A brace
// body on one line, `if (( 0 )) { cd ../scratch }; cp ../base/report.md report.md` from docs/ (and the `for y ()`, `while`,
// `until`, `select`, `case a { b) .. }` and `for y in; { .. }` spellings): compoundBody closed the frame at the `}` before the
// cd in its own segment was read, so the cd zsh skipped was followed and the write resolved to scratch/report.md while zsh
// wrote the tracked docs/report.md (bash and dash reject the spelling); pre-existing at the round-4 head, claimed closed by the
// addendum's F6 and F7, whose rows had the brace on its own segment. That addendum read the brace after the segment's command
// in compoundBody alone (`oneSegment`), for the heads of BODY_CLOSER, and claimed the cd face closed for every head. (2) The
// trailing `}` of zsh's `{ cmd }` was read as the command's LAST OPERAND, cp's, mv's, install's and ln's destination
// (`{ cp ../base/report.md report.md }` from docs/), so the tracked file was read as a source and the copy onto it allowed
// while zsh performed it; that addendum cut the trailing braces at the writer (`variants`) and claimed the operand face closed
// in a plain group, a `then` or `do` body, a function body and a group after `&&`. Both claims were false while the function
// frame and the words after a spliced brace were read the old way: the third addendum, below, holds the rule instead.
//
// ROUND 5'S THIRD ADDENDUM (2026-09-20; the round's verifier, on the second addendum's head): twenty live false allows in the
// family the second addendum claimed closed, a `}` sharing a segment with the words before it, in the frames that addendum's
// fix did not reach. The FUNCTION-body scan popped its frame at the brace before the cd sharing the segment was read, so the cd
// was followed as plain sequence: `f() { cd ../scratch }; cp ../base/report.md report.md` from docs/ was allowed while zsh
// wrote docs/report.md, in thirteen spellings (`function f { .. }`, which dash runs too, `function f() { .. }`, `f g () { .. }`,
// `! f() { .. }`, nested, two commands, a newline separator, an `&&` join, a redirect after the brace, a quoted operand, pushd,
// a group holding the definition). After compoundBody spliced a shared-segment brace, the words after it in the segment
// (`else { .. }`, `always { .. }`, a while's condition group) became OPERANDS of the body's command, so a writer in the other
// block was never a command: `if (( 1 )) { cp .. } else { : }`, `if (( 0 )) { : } else { cp .. }`, `{ cp .. } always { : }`,
// `{ : } always { cp .. }`, `while { cp .. } { break }` allowed while zsh copied. And `repeat 1 { cp .. }` read the brace body as
// repeat's operands. Reproducing them found more of the same reading: `if (( 0 )) cd ../scratch` and `if [[ 1 = 2 ]] cd ..`
// (zsh's one-command body after `))` or `]]`, walked as plain sequence), `if [[ 1 = 1 ]] { cp .. }` and `elif [[ 1 = 1 ]] {
// cp .. }` (the condition's words were the segment's command, the body's writer their operand), `always` nested in a body,
// `} else {` with the else block on later lines (read as a plain group after the frame closed), and, from the redirect
// placement, `{ cd ../scratch; } > report.md`, `{⏎cd ../scratch⏎} > report.md` and `if true; then cd ../scratch; fi >
// report.md`, whose redirection every shell opens before the construct runs, in docs/, while the guard judged it after the
// cd it followed inside (bash, zsh and dash wrote the tracked file). THE RULE (splitAtClosers, at the lexer, where it is
// stated once): an unquoted `}` that follows other words in its segment ends its construct only after those words are read
// as the construct's own command, and every word after it begins a new command; the lexer cuts the segment before such a
// brace, so every frame kind (a compound body, a condition group, a function body, a plain group, a repeat body, and the
// `else`, `elif` and `always` continuations) reads a one-line brace form as its `;` twin, through the code it already had.
// compoundBody reads the continuations (`else`/`elif` keep the frame open; a `{` first after `if`, `while` or `until` with no
// `(( ))` between is a condition group whose `}` leaves the frame waiting for the body; a one-command body follows `))`,
// `]]` or a condition group's `}`) and drops a condition's words before the body so commandOf reads the body's command;
// `repeat N` is dropped before either body form; a function body's count stops at a compound head inside it and reads the
// second brace of a `} }` segment; and a closer segment's redirections are judged in the directory saved when its construct
// opened (closedConstruct, addRedirects). The second addendum's `oneSegment` splice, its trailing-brace cut at the writer,
// the group scan's `always` splice and the seventh pass's pendingClose are gone, replaced by the one cut. Pinned with the
// verifier's twenty rows, the rows found beside them, and a generated matrix (frame kind x brace placement x face x position,
// every row run through the hook and unguarded in the three shells; the rows the matrix produces are the pin).
//
// ROUND 5'S FOURTH ADDENDUM (2026-09-20; the round's verifier, on the third addendum's head): the function body's count read
// a QUOTED brace word as a brace of the body, against the rule's own text (a quoted brace is an operand): `f() { echo "}"; cd
// ../scratch; }; cp ../base/report.md report.md` from docs/ popped the frame at the quoted word, followed the cd as plain
// sequence and was allowed while bash, zsh and dash wrote docs/report.md (present at round 4's head; `'}'`, `\}`, `printf %s
// "}"`, pushd, `"{"`, a newline, a piped body, coproc and the name face alike). The census of the hook's brace reads found the
// same gap in the reserved-word reads (RESERVED holds `{` and `}`): the lexer took `[[` after ANY word spelled as a reserved
// word for the test keyword (`echo "{" [[ x > report.md ]]` and `echo { [[ .. ]]`: echo's operands and a redirection, which
// bash and dash perform), and commandOf and rawHeadIndexOf skipped a quoted reserved word as if it were one (`"{" cd
// ../scratch; cp ..`: a command named `{`, the cd its operand, every shell staying in docs/). Every brace read checks
// plainWord now: the body count and its one-segment check (a quoted `{` heading the body's segment is the command of zsh's
// and dash's one-command body), the lexer's `[[` (the test keyword after unquoted reserved words alone) and the two skips (a
// quoted reserved word is the command and the words after it its operands, so `"{" cp a b` is judged as any command the guard
// does not know). Pinned with the verifier's rows, bash, zsh and dash by execution, and five matrix kinds (a quoted brace word
// in a function body, defined and called, a quoted opening brace, and two twins with a brace inside a word).
//
// THE LISTS THAT REMAIN are not written here (round 5 of the review, 2026-09-20). The hand-written census that stood here
// omitted the two lists whose gap falls on the WRITE side, the compound-head frame push and CLOSERS, and that omission is
// how a `select` missing from both slipped through round 3: an instrument built to bound the hand-maintained lists that
// was itself a hand-maintained list, with a gap on the dangerous side. The census is DERIVED FROM THIS SOURCE at test time
// instead (tools/romp-track-bash-guard-census.mjs, run by tools/romp-track-bash-guard.test.mjs): every column-0 `const`,
// `let` or `var` whose initializer opens a Set, an array, an object table, an `Object.fromEntries(` or a `new RegExp(` is
// enumerated by reading the module's text (the method and its blind spots are stated in that file), the writer cases of
// extract's switch and the markers markerAt reads with them, and each is classified by the side its GAP falls on (a missing
// element causes a WRITE the guard reads as plain or as no write, or a false REFUSAL) against the consumer line that decides
// it, which must exist in this file. A list this file gains in one of those shapes that the census does not name, or one
// whose side is not classified, or a consumer line that moved, reds that test; a list planted in a scratch copy in one of
// the shapes the census reads reds it (measured with the change, and again by round 5's addendum's census lens, which
// planted fourteen shapes: twelve landed green while live on the write side, three of those are read since, `var`, a
// declaration split after its `=` and spacing drift, and the rest are named in the module as its blind spots, an inline
// literal at its point of use, a second declarator, a second `switch`, a call, a string, a regex literal, a `let` filled in
// later, a declaration inside a function). The two write-side tables to know from the
// code: BODY_CLOSER (the compound heads with their closers, from which the frame push, CLOSERS and COMPOUND_HEADS all
// read: a head not listed opens no frame, and a body that may not run is read as plain sequence) and PREFIXES (an unlisted
// wrapper is read as its own command, an unmodelled writer by the contract, so the set is stated on the four surfaces and
// the unlisted wrappers the passes found, unshare, nsenter, script, setarch, setpriv, are on the contract's list).
// THE CONTRACT. This guard is best-effort against known write forms: it refuses the shell writes it models and, by
// design, allows anything it does not recognise, so it never blocks ordinary work it cannot read; it is a backstop, not
// a complete boundary. The allow-by-default for an unmodelled writer is deliberately not flipped, since flipping it
// would refuse almost all normal work. What it does refuse, while a tracked project is in play, is a write it reads but
// cannot place: a target it cannot read, a path it cannot check (a stat error other than not-found), an option on a
// modelled writer or wrapper it does not parse in full, an env -S string, a shell option it does not know to be inert
// for paths, a link whose source it cannot read, a `~` or `$HOME` write beside a mention of HOME or beside a variable
// name the shell fills in, a template or format string as an interpreter's write path, and, from any working directory,
// a write through an alias the command makes (a hard link, `cp -l`, `cp -s`, `link`, a link whose source it cannot read)
// whose source lies in a tracked project or is one it cannot read. A value it can read is resolved first and the real
// path judged. A name is readable only when every write to it in the command is a plain top-level `NAME=plain-string`
// the shell performs as spelled: no tilde opening the value, no declaration flag at all, no `declare`, `typeset` or `local`
// (dash has none of the three; `export` and `readonly` with no option word are the two declarations every shell performs),
// no nameref reaching it, no name the shell fills in, no subshell, pipeline, piped group or body scope, no `{ }` group
// opened after `&&`, `||` or `|`, no wrapper argument, no
// call of a function the command defines in any spelling, no subscript; any other construct that can write the name,
// listed here or not, leaves it unreadable, the doctrine a `read` and a loop variable already had. HOME, PWD, OLDPWD,
// `~+` and `~-` are read the same way: HOME after a plain top-level `HOME=<path>` assignment of its own, and none of
// the three once the command names or may fill in the name in any other form. These write forms are not modelled and
// still
// reach a tracked file: rsync; awk with a redirect inside its program; ed; ex; make; find with -delete or -exec; a
// git subcommand that writes the working tree (checkout, stash, apply, reset, rm, clean, mv); a computed or escaped
// path inside an interpreter (a name, sys.argv, os.environ or process.env, a concatenation that does not open with a string
// literal, or an escape sequence in the string, in python3 -c or node -e); a script the shell reads from elsewhere (eval, xargs, a sourced file, trap,
// a command whose name is an expansion, a script held in a variable); a command that runs another command and is
// outside the guard's wrapper set (unshare, nsenter, script, setarch, setpriv, strace and their kin); a link
// made by a writer outside the model (python, tar, rsync) that a later modelled write follows; shuf -o; a cd through
// CDPATH; and an opaque expansion from a cwd outside every project, leading or after a literal head outside every
// project (a `..` inside the value could climb into a project; from a cwd in a tracked project the same word is
// refused as not literal). The same paragraph, and this writer list, are on the vendored SKILL.md, hooks/README.md
// and docs/install.md, pinned identical by a test.

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { findVaultRoot, isTrackedFile, isNonTextPath, hasNulBytes } from '../vendor/track-changents/store-io.mjs';
import { relPathFor, trackedPaths as readTrackedPaths, untrackedPaths as readUntrackedPaths, trackedClosure } from '../vendor/track-changents/store-io.mjs';
import engine from '../vendor/track-changents/engine.js';

// ── lexer ───────────────────────────────────────────────────────────
//
// A command is cut into simple commands ("segments") at |, ||, &&, ;, &, newline, ( and ), and before an
// unquoted `}` that follows other words (splitAtClosers, below the lexer: zsh's `{ cmd }` closer heads a
// segment of its own, read after the command). Each
// segment is a list of words and a list of redirections, and `op` names the operator that ended
// it, so a later pass can tell a pipeline from a list. A `(` or `)` is also emitted as a marker
// segment (`paren`) so the scope of a subshell is known: a `cd` inside one moves nothing after the
// `)`. A word keeps the text the shell would see after quote removal, `marks` ('u' at each
// character that was unquoted, 'q' at one that was quoted or escaped, 'x' at one an expansion stands
// for) so a later pass can tell a glob character from a quoted one and an expansion from a literal
// dollar, and two flags: `literal`, false once the word carries anything the shell would expand that
// the hook cannot ($VAR, ${...}, $(...), backticks, ~user, a process substitution), and `glob`, true
// for a word whose only expansion is an unquoted `*`, `?` or `[...]`, which extractWriteTargets
// expands against the filesystem the way the shell would. An expansion that leaves no text (a
// `$(...)`, a backtick) stands as one NUL character marked 'x', a character no path can hold, so its
// place in the word survives every later slicing. Brace expansion happens here, as in the shell
// before every other expansion: an unquoted `{a,b}` or `{1..3}` makes one word per alternative
// (`mv report.md{.new,}` names two operands), and a redirection target that expands to several words
// is one redirection per alternative: bash calls it an ambiguous redirect and writes nothing, zsh
// (multios, on by default) writes each, and the hook names each (2026-09-18; before, it read bash's
// rule and named none, so `> docs/{a,b}.md` in zsh rewrote a tracked file unjudged).
// A leading ~/ is expanded to the home directory, as the shell would. A heredoc body
// (<<EOF ... EOF) and a here-string (<<< word) are data, not commands: kept on the segment whose
// command opened them (not the one current when the line ends, which after
// `python3 - <<EOF && echo done` is the echo) for the python, node and shell stdin scans, and
// never lexed as shell. `>(cmd)` and `<(cmd)` are process substitutions: cmd is read like a
// `$(...)`, and the word stands for a /dev/fd path the hook cannot resolve. Inside `[[ ... ]]`
// (the unquoted keyword, in command position) a `>` or `<` compares and redirects nothing, and
// `&&`, `||`, `(` and `)` are the test's own operators; `(( ... ))` is arithmetic. `opaque` is set
// when the command is more than the lexer can follow: an unterminated quote, or eval, xargs or a
// shell -c with a script it cannot read.

// The write redirections, with zsh's clobber-override suffixes (the fifth commit, 2026-09-19, M2): zsh reads a `!` or a
// `|` after `>`, `>>`, `>&`, `>>&`, `&>` and `&>>` as "write even under NO_CLOBBER" (`>! f`, `>>! f`, `&>! f`, `>>| f`,
// `>&| f`, `>>&` appends both streams), and the fourth attack wrote a tracked file through `>! docs/report.md` while the
// lexer read the `!` as the target word and the file as an argument. The lexer consumes the suffix as it consumed `>|`,
// and records BOTH shells' readings where they differ (bash reads `>! f` as a redirection onto a file named `!` with `f`
// an argument, and `>!f` as a redirection onto `!f`; `>>&`, `>>|`, `>&|`, `&>|` are syntax errors in bash and write
// nothing), so a command refuses when either shell would write the tracked file.
const WRITE_REDIRECTS = new Set(['>', '>>', '>|', '&>', '&>>', '>&', '<>', '>!', '>>!', '>>|', '>&!', '>&|', '>>&', '>>&!', '>>&|', '&>!', '&>|', '&>>!', '&>>|']);
const SHELLS = new Set(['sh', 'bash', 'zsh', 'dash', 'ksh']);
// Command wrappers the hook peels to reach the write inside: it reads them so a write behind one is judged as if
// spelled without it. `setsid`, `flock`, `taskset`, `chrt` and `numactl` were added in review round 4 (2026-09-19),
// each with operand-aware peeling below (a lockfile, a CPU mask, a priority, an option's argument), after the
// walk-around lens found `setsid cp …`, `flock -x . cp …`, `taskset -c 0 cp …`, `chrt -o 0 cp …` and
// `numactl -C0 cp …` allowed while `nohup cp …` and `timeout 5 cp …` were refused. A command that is neither
// modelled nor a known wrapper is read as its own command, as before. The gap of this set falls on the ALLOW side
// (a wrapper not listed, `unshare`, `nsenter`, `script`, `setarch`, `setpriv`, is read as its own command, an
// unmodelled writer by the contract), so the set is stated on the four surfaces; each wrapper listed here is then
// parsed in full against WRAPPER_OPT or refused (the walk-around lens third pass, rule (b), 2026-09-19).
// zsh's precommand modifiers `noglob`, `nocorrect` and `-` (ZSH_MODIFIERS; the seventh pass's attacker, F1, 2026-09-19) are
// wrappers of the same shape as `command` and `builtin`: reserved words that take no option and run the command after them
// (with globbing off, spelling correction off, or a `-` before argv[0]). zsh runs `noglob cp base/report.md docs/report.md`
// and `- cp ...`; bash and dash have no such word and fail with 127 before the cp. They were read as commands named `noglob`,
// so the writer behind them was never seen and zsh wrote the tracked file (14 rows, `noglob cd` included); a modifier after
// an external wrapper or `command` is an external program that is not there (measured: `nice noglob cp`, `command noglob
// cp` write nothing), and it is peeled all the same, the cost a refusal of a spelling no shell runs.
const ZSH_MODIFIERS = new Set(['noglob', 'nocorrect', '-']);
const PREFIXES = new Set(['sudo', 'command', 'builtin', 'exec', 'nice', 'nohup', 'time', 'env', 'timeout', 'ionice', 'stdbuf', 'setsid', 'flock', 'taskset', 'chrt', 'numactl', ...ZSH_MODIFIERS]);
const RESERVED = new Set(['do', 'then', 'else', 'elif', 'if', 'while', 'until', '!', '{', '}']);
// The shells verified (round 3, 2026-09-19, by execution) to read `$'...'` as ANSI-C quoting: bash 5.2 and zsh 5.9,
// the shells the Bash tool runs, so the top-level command (shell null) reads it so too. dash, `/bin/sh` here, reads a
// literal dollar and a single-quoted string; ksh was not verified; `sh` may be either. A shell not in this set
// gets the restricted reading (the header): the word is one the hook cannot read.
const ANSI_C_SHELLS = new Set(['bash', 'zsh']);
// The one class of expansion the narrowing reads (the header): the shell's process id, in its two spellings. Every
// other parameter can be unset or shadowed by the command and then hold a path (round 3, by execution in bash, zsh
// and dash), so nothing else is ever numeric.
const NUMERIC_EXPANSIONS = ['$$', '${$}'];

// `at` is the literal folder a copy lands in when the landing NAME is not literal (`cp "$SRC" docs/`,
// `cp -t docs "$SRC"`): the refusal of such a word is judged by that folder's project, not the cwd's.
// `numeric` marks a non-literal word whose every expansion is `$$` or `${$}`: such a word's text is a path with
// digits to be filled in and can carry no `../` and no glob, so inPlayFor may read its literal segments to see
// that it lands outside every project in play.
function word(text, literal, raw, extra) {
  return {
    text, literal, raw, glob: !!(extra && extra.glob), marks: extra && extra.marks != null ? extra.marks : null,
    at: extra && extra.at != null ? extra.at : null, numeric: !!(extra && extra.numeric),
    why: extra && extra.why ? extra.why : null,   // why an expansion in it stayed opaque (resolveWord's named expansion), for the refusal
  };
}

// What the `$` at `pos` of `src` begins: { kind, len }. 'numeric' is `$$` or `${$}` (NUMERIC_EXPANSIONS); 'home' is
// `$HOME` or `${HOME}` (the caller decides whether it stands at the start of a word followed by a slash or the
// word's end, the one place it is expanded like `~`); 'var' a parameter the hook does not read (`$NAME`, `$1`, `$?`
// and the other one-character specials); 'brace' a `${...}` of unknown content; 'sub' a `$(`; 'ansi' a `$'`;
// 'locale' a `$"`; and 'dollar' a bare `$` before anything else, which bash, zsh and dash all leave as a literal
// dollar (`$/x` prints `$/x`), so it is text, not an expansion (round 3).
function expansionAt(src, pos) {
  for (const spelling of NUMERIC_EXPANSIONS) if (src.startsWith(spelling, pos)) return { kind: 'numeric', len: spelling.length };
  const next = src[pos + 1];
  if (next === '{') {
    const close = src.indexOf('}', pos + 2);
    if (close >= 0 && src.slice(pos + 2, close) === 'HOME') return { kind: 'home', len: close + 1 - pos };
    return { kind: 'brace', len: 2 };
  }
  if (next === '(') return { kind: 'sub', len: 2 };
  if (next === "'") return { kind: 'ansi', len: 2 };
  if (next === '"') return { kind: 'locale', len: 2 };
  const m = src.slice(pos + 1).match(/^[A-Za-z_][A-Za-z0-9_]*/);
  if (m && m[0] === 'HOME') return { kind: 'home', len: 1 + m[0].length };
  if (m) return { kind: 'var', len: 1 + m[0].length };
  if (next != null && /[0-9?!#@*-]/.test(next)) return { kind: 'var', len: 2 };
  return { kind: 'dollar', len: 1 };
}
// Whether the character after a leading `$HOME` starts its path or ends the word: a slash, an operator,
// whitespace or the end. `$HOMEDIR`, `$HOME.bak` and `${HOME:-/tmp}` never reach here (the name or the brace
// body differs), and `$HOME"x"` stays an expansion the hook does not read (review round 1, 2026-09-18: the
// same directory spelled `~/` was expanded and allowed while `"$HOME/"` was refused, though both come from
// the same os.homedir() read; the carve-out is at the word's start, with a slash or the end after it, so
// nothing else about a word changes).
const homeBoundary = (ch) => ch === undefined || ch === '/' || /[\s;&|()<>]/.test(ch);

// The text of an ANSI-C quoted body (`$'...'`), the escapes bash and zsh process: \a \b \e \E \f \n \r \t \v \\
// \' \" \? an octal \nnn, \xHH, \uHHHH, \UHHHHHHHH and \cX; an escape neither knows keeps its backslash.
function ansiC(body) {
  const simple = { a: '\x07', b: '\b', e: '\x1b', E: '\x1b', f: '\f', n: '\n', r: '\r', t: '\t', v: '\v', '\\': '\\', "'": "'", '"': '"', '?': '?' };
  let out = '';
  for (let i = 0; i < body.length; i++) {
    if (body[i] !== '\\' || i + 1 >= body.length) { out += body[i]; continue; }
    const c = body[i + 1];
    let m;
    if (c in simple) { out += simple[c]; i++; continue; }
    if ((m = body.slice(i + 1).match(/^[0-7]{1,3}/))) { out += String.fromCharCode(parseInt(m[0], 8) & 0xff); i += m[0].length; continue; }
    if ((m = body.slice(i + 1).match(/^x([0-9A-Fa-f]{1,2})/))) { out += String.fromCharCode(parseInt(m[1], 16)); i += m[0].length; continue; }
    if ((m = body.slice(i + 1).match(/^u([0-9A-Fa-f]{1,4})/)) || (m = body.slice(i + 1).match(/^U([0-9A-Fa-f]{1,8})/))) {
      try { out += String.fromCodePoint(parseInt(m[1], 16)); } catch { out += m[0]; }
      i += m[0].length; continue;
    }
    if (c === 'c' && i + 2 < body.length) { out += String.fromCharCode(body.charCodeAt(i + 2) & 0x1f); i += 2; continue; }
    out += '\\';
  }
  return out;
}

// Whether `text` has an unquoted glob character, per `marks`.
function hasGlobChar(text, marks) {
  for (let i = 0; i < text.length; i++) if (marks[i] === 'u' && (text[i] === '*' || text[i] === '?' || text[i] === '[')) return true;
  return false;
}

// Brace expansion on a word's text with its marks: the first unquoted `{...}` holding an unquoted
// top-level comma, or a `..` sequence of integers or single letters, makes one alternative per
// member, each carried through the rest of the word (so `a{b,c}{d,e}` gives four), nested braces
// included; a `{` with no `}`, or `{x}` with neither, is text. Returns [text, marks] pairs, or
// null past BRACE_CAP alternatives or BRACE_DEPTH_CAP nested lists (a word the hook then cannot
// resolve; the depth cap, round 3, keeps a list nested thousands deep from overflowing the stack,
// which evaluate would have read as allow).
const BRACE_CAP = 512;
const BRACE_DEPTH_CAP = 64;
function braceSequence(inner) {
  let m = inner.match(/^(-?\d+)\.\.(-?\d+)(?:\.\.(-?\d+))?$/);
  if (m) {
    const a = parseInt(m[1], 10);
    const b = parseInt(m[2], 10);
    const step = (m[3] != null && Math.abs(parseInt(m[3], 10))) || 1;
    if (Math.abs(b - a) / step + 1 > BRACE_CAP) return null;
    const pad = /^-?0\d/.test(m[1]) || /^-?0\d/.test(m[2]) ? Math.max(m[1].replace('-', '').length, m[2].replace('-', '').length) : 0;
    const out = [];
    for (let v = a; a <= b ? v <= b : v >= b; v += a <= b ? step : -step) out.push((v < 0 ? '-' : '') + String(Math.abs(v)).padStart(pad, '0'));
    return out;
  }
  m = inner.match(/^([A-Za-z])\.\.([A-Za-z])(?:\.\.(-?\d+))?$/);
  if (m) {
    const a = m[1].charCodeAt(0);
    const b = m[2].charCodeAt(0);
    const step = (m[3] != null && Math.abs(parseInt(m[3], 10))) || 1;
    const out = [];
    for (let v = a; a <= b ? v <= b : v >= b; v += a <= b ? step : -step) out.push(String.fromCharCode(v));
    return out;
  }
  return undefined;
}
function braceExpand(text, marks, depth = 0) {
  if (depth > BRACE_DEPTH_CAP) return null;
  for (let i = 0; i < text.length; i++) {
    if (text[i] !== '{' || marks[i] !== 'u') continue;
    let depthBraces = 0;
    let close = -1;
    const commas = [];
    for (let j = i; j < text.length; j++) {
      if (marks[j] !== 'u') continue;
      if (text[j] === '{') depthBraces++;
      else if (text[j] === '}') { if (--depthBraces === 0) { close = j; break; } }
      else if (text[j] === ',' && depthBraces === 1) commas.push(j);
    }
    if (close < 0) break;   // no closing brace: the text stands
    let alts;
    if (commas.length) {
      alts = [];
      let from = i + 1;
      for (const c of [...commas, close]) { alts.push([text.slice(from, c), marks.slice(from, c)]); from = c + 1; }
    } else {
      const seq = braceSequence(text.slice(i + 1, close));
      if (seq === undefined) continue;   // {x}: text; a later brace may still expand
      if (seq === null) return null;
      alts = seq.map((s) => [s, 'u'.repeat(s.length)]);
    }
    const out = [];
    for (const [t, m] of alts) {
      const rest = braceExpand(t + text.slice(close + 1), m + marks.slice(close + 1), depth + 1);
      if (!rest) return null;
      for (const [rt, rm] of rest) {
        out.push([text.slice(0, i) + rt, marks.slice(0, i) + rm]);
        if (out.length > BRACE_CAP) return null;
      }
    }
    return out;
  }
  return [[text, marks]];
}

// `arith` holds the bodies of `(( ... ))` and `$(( ... ))`, which run in the current shell and can assign a name
// (`(( HOME = 5 ))`), for the assignment scan (the walk-around lens second pass, 2026-09-19); they are never lexed as commands.
const newSegment = () => ({ words: [], redirects: [], heredocs: [], subs: [], arith: [], arithAt: [], op: '' });   // arithAt: the number of words before each `(( ))` (round 5's third addendum: compoundBody tells `if (( 0 )) {` from `if { cond } {` by it)

// `shell` is the name of the shell the command is a script of, when the call is a recursion into `sh -c '...'`,
// `bash <<EOF` or a `$(...)` inside one (null for the Bash tool's own command): it decides whether `$'...'` is
// ANSI-C quoting (ANSI_C_SHELLS). The numeric set is the same in every shell (round 3).
export function lex(command, shell = null) {
  const src = String(command);
  const ansiCQuoting = shell == null || ANSI_C_SHELLS.has(shell);
  const segments = [];
  let seg = newSegment();
  let buf = '';
  let raw = '';
  let marks = '';
  let sawExpansion = false;   // the word carries an expansion the hook cannot resolve
  let numericOnly = true;     // every expansion so far is `$$` or `${$}` (meaningful with sawExpansion)
  let inWord = false;
  let opaque = false;
  let inTest = false;   // inside [[ ... ]], where > and < compare strings
  // what the next word is: a redirect target, a heredoc delimiter, a here-string, or data (<)
  let expect = null;
  const pendingHeredocs = [];
  let i = 0;

  const mk = (t, m) => {
    const g = !sawExpansion && hasGlobChar(t, m);
    // numeric: every expansion is the process id AND no unquoted glob character sits beside it (a `*` in a segment
    // could match a project's name, so such a word gets no narrowing; review round 1)
    return word(t, !sawExpansion && !g, raw, { glob: g, marks: m, numeric: sawExpansion && numericOnly && !hasGlobChar(t, m) });
  };
  // Quoted or escaped text: never a glob character, never a brace to expand, and literal (a `\$` is a dollar).
  const quoted = (t) => { buf += t; marks += 'q'.repeat(t.length); };
  // The home directory a leading `~/`, `$HOME/` or `${HOME}/` expands to: literal text like `quoted`, marked
  // 'h' so extract can tell later whether the command reassigns HOME (2026-09-19, walk-around lens: `HOME=notes;
  // > $HOME/seed.md` reassigns HOME to a tracked folder before the write, but the guard read os.homedir()).
  const home = (t) => { buf += t; marks += 'h'.repeat(t.length); };
  // Text an expansion stands for, marked 'x' so the readers below can tell it from a literal dollar (round 3).
  const expanded = (t) => { buf += t; marks += 'x'.repeat(t.length); };
  // An expansion the hook cannot read at all: the word is not literal and gets no numeric narrowing; `t` is its
  // text in the word (the spelling, `$NAME`), or one NUL when it leaves none (a `$(...)`, a backtick).
  const opaqueExpansion = (t = '\0') => { sawExpansion = true; numericOnly = false; expanded(t); };
  // A word whose reading depends on the shell that runs it (`$'...'` under sh, `$"..."`): not literal, no
  // narrowing, and its text kept as literal characters, so the own-project step sees the path bash would write.
  const ambiguous = () => { sawExpansion = true; numericOnly = false; };
  const endWord = () => {
    if (!inWord) return;
    if (expect) {
      if (expect.kind === 'target') {
        // a target that brace-expands to several words: bash's ambiguous redirect writes nothing, zsh's
        // multios writes each (2026-09-18), so each is a redirection of its own; past the cap the word is one
        // the hook cannot read
        const alts = braceExpand(buf, marks);
        if (alts) for (const [t, m] of alts) seg.redirects.push({ op: expect.op, target: mk(t, m) });
        else seg.redirects.push({ op: expect.op, target: word(buf, false, raw, { marks }) });
        // M2: bash reads the `!` zsh consumed as the first character of the target word, so a glued `>!docs/report.md`
        // is a write of `!docs/report.md` there (the spaced form's bash target, a file named `!`, was recorded at the
        // operator); both readings are judged, and the refusal names the one that lands on a tracked file
        if (expect.bang === 'glued') seg.redirects.push({ op: expect.op, target: mk('!' + buf, 'u' + marks) });
      } else if (expect.kind === 'heredoc') pendingHeredocs.push({ delim: buf, stripTabs: expect.stripTabs, owner: seg });
      else if (expect.kind === 'herestring') seg.heredocs.push(buf);
      expect = null;
    } else {
      // the keyword: unquoted, in command position (first in its segment, or after unquoted reserved words alone; round 5's
      // fourth addendum: after `echo "{"`, `echo {` or `echo "if"` the `[[` and its `>` are echo's operands and a redirection,
      // which bash and dash perform, so `echo "{" [[ x > report.md ]]` from docs/ truncated the tracked file while the guard
      // read a comparison)
      if (raw === '[[' && seg.words.every((w) => plainWord(w) && RESERVED.has(w.text))) inTest = true;
      else if (raw === ']]') inTest = false;
      const alts = braceExpand(buf, marks);
      if (!alts) seg.words.push(word(buf, false, raw, { marks }));
      else for (const [t, m] of alts) seg.words.push(mk(t, m));
    }
    buf = ''; raw = ''; marks = ''; sawExpansion = false; numericOnly = true; inWord = false;
  };
  // A word of the test's own grammar (`>` or `&&` inside [[ ... ]]): ends any word under way, stands alone.
  const bareWord = (t) => { endWord(); inWord = true; buf = t; raw = t; marks = 'u'.repeat(t.length); endWord(); };
  const endSegment = (op) => {
    endWord();
    if (expect) expect = null;   // a redirect with no target: leave it
    inTest = false;
    seg.op = op;
    if (seg.words.length || seg.redirects.length || seg.heredocs.length || seg.subs.length || seg.arith.length) segments.push(seg);
    else if (op && segments.length && segments[segments.length - 1].paren && !segments[segments.length - 1].op) {
      // the operator after a `)` (`(cd a) && cd b`): the segment it would end is empty, so it is kept on the paren
      // marker, and a later pass reading the operator before a `cd` sees it (the walk-around lens second pass, 2026-09-19; before, it was lost)
      segments[segments.length - 1].op = op;
    }
    seg = newSegment();
  };
  // After a newline, the bodies of every heredoc opened on the line just ended, each on the
  // segment that opened it (already pushed by reference when an operator ended it on that line).
  const readHeredocBodies = () => {
    while (pendingHeredocs.length) {
      const { delim, stripTabs, owner } = pendingHeredocs.shift();
      const lines = [];
      for (;;) {
        if (i >= src.length) break;
        let j = src.indexOf('\n', i);
        if (j < 0) j = src.length;
        const line = src.slice(i, j);
        i = Math.min(j + 1, src.length);
        const cmp = stripTabs ? line.replace(/^\t+/, '') : line;
        if (cmp === delim) break;
        lines.push(line);
      }
      owner.heredocs.push(lines.join('\n'));
    }
  };
  // (( ... )): arithmetic, no command and no redirection in it; skip to the matching )).
  const skipArithmetic = () => {
    let depth = 2;
    const start = i;
    while (i < src.length && depth > 0) {
      if (src[i] === '(') depth++;
      else if (src[i] === ')') depth--;
      i++;
    }
    if (depth > 0) opaque = true;
    seg.arithAt.push(seg.words.length);   // endWord ran before the `((`, so this is the index of the word that follows it
    seg.arith.push(src.slice(start, Math.max(start, i - 2)));
  };
  // Skip a $( ... ) or ${ ... } from just after its opener to its closer, quotes honoured;
  // returns the inner text. The word carrying it is not literal.
  const skipNested = (open, close) => {
    let depth = 1;
    const start = i;
    while (i < src.length && depth > 0) {
      const c = src[i];
      if (c === '\\') { i += 2; continue; }
      if (c === "'") { const e = src.indexOf("'", i + 1); i = e < 0 ? src.length : e + 1; continue; }
      if (c === '"') {
        i++;
        while (i < src.length && src[i] !== '"') { if (src[i] === '\\') i++; i++; }
        i++;
        continue;
      }
      if (c === open) depth++;
      else if (c === close) depth--;
      i++;
    }
    if (depth > 0) opaque = true;
    return src.slice(start, Math.max(start, i - 1));
  };
  // A `$(...)` (or `$(` inside double quotes): the command inside runs, the word carries one NUL for it.
  const substitution = () => {
    opaqueExpansion(); raw += '$('; i += 2; const inner = skipNested('(', ')'); raw += inner + ')';
    // `$(( ... ))` is arithmetic, run in the current shell (an assignment in it persists): kept for the assignment
    // scan and not read as a command (the walk-around lens second pass, 2026-09-19); a `$( ... )` is a command in a subshell, as before
    if (inner.startsWith('(') && inner.endsWith(')')) seg.arith.push(inner.slice(1, -1));
    else seg.subs.push(inner);
  };
  // A `${...}` of unknown content: the spelling stays in the word, marked as an expansion.
  const braceParameter = () => { raw += '${'; i += 2; const inner = skipNested('{', '}'); raw += inner + '}'; opaqueExpansion('${' + inner + '}'); };
  // A backtick command: as `$(...)`; unterminated, the rest of the command is opaque.
  const backtick = () => {
    const e = src.indexOf('`', i + 1);
    inWord = true; opaqueExpansion();
    if (e < 0) { opaque = true; raw += src.slice(i); i = src.length; return; }
    seg.subs.push(src.slice(i + 1, e));
    raw += src.slice(i, e + 1); i = e + 1;
  };

  while (i < src.length) {
    const c = src[i];
    if (c === ' ' || c === '\t') { endWord(); i++; continue; }
    if (c === '\n') {
      endWord();
      i++;
      readHeredocBodies();   // the bodies belong to the line just ended
      endSegment('\n');
      continue;
    }
    if (c === '#' && !inWord) {   // comment to the end of the line
      while (i < src.length && src[i] !== '\n') i++;
      continue;
    }
    if (c === '\\') {
      if (src[i + 1] === '\n') { i += 2; continue; }   // line continuation
      inWord = true; quoted(src[i + 1] == null ? '' : src[i + 1]); raw += src.slice(i, i + 2); i += 2;
      continue;
    }
    if (c === "'") {
      const e = src.indexOf("'", i + 1);
      if (e < 0) { opaque = true; quoted(src.slice(i + 1)); raw += src.slice(i); inWord = true; i = src.length; break; }
      inWord = true; quoted(src.slice(i + 1, e)); raw += src.slice(i, e + 1); i = e + 1;
      continue;
    }
    if (c === '"') {
      inWord = true;
      raw += '"';
      i++;
      let closed = false;
      while (i < src.length) {
        const d = src[i];
        if (d === '"') { closed = true; raw += '"'; i++; break; }
        if (d === '\\' && i + 1 < src.length && '"\\$`\n'.includes(src[i + 1])) {
          if (src[i + 1] !== '\n') quoted(src[i + 1]);
          raw += src.slice(i, i + 2); i += 2; continue;
        }
        if (d === '$') {
          // the quoted spelling of the two expansions the hook reads (review round 1, 2026-09-18): a leading
          // "$HOME/..." is the home directory, as `~/` is; "$$" and "${$}" are numeric. A parameter is marked as an
          // expansion; a bare dollar is text (round 3); `$'` and `$"` quote nothing inside double quotes.
          const e = expansionAt(src, i);
          if (e.kind === 'home' && buf === '' && !sawExpansion && (src[i + e.len] === '/' || src[i + e.len] === '"')) {
            home(os.homedir()); raw += src.slice(i, i + e.len); i += e.len; continue;
          }
          if (e.kind === 'numeric') { sawExpansion = true; expanded(src.slice(i, i + e.len)); raw += src.slice(i, i + e.len); i += e.len; continue; }
          if (e.kind === 'sub') { substitution(); continue; }
          if (e.kind === 'brace') { braceParameter(); continue; }
          if (e.kind === 'var' || e.kind === 'home') { opaqueExpansion(src.slice(i, i + e.len)); raw += src.slice(i, i + e.len); i += e.len; continue; }
          quoted('$'); raw += '$'; i++; continue;
        }
        if (d === '`') { backtick(); continue; }
        quoted(d); raw += d; i++;
      }
      if (!closed) opaque = true;
      continue;
    }
    if (c === '`') { backtick(); continue; }
    if (c === '$') {
      // a leading $HOME or ${HOME} followed by a slash or the word's end is the home directory, as `~/` is
      // (review round 1, 2026-09-18); $$ and ${$} are numeric; a parameter, a `${...}`, a `$(...)` are expansions
      // the hook does not read; `$'...'` and `$"..."` are quoting forms (the header); a bare `$` is text
      const e = expansionAt(src, i);
      if (e.kind === 'home' && buf === '' && !sawExpansion && homeBoundary(src[i + e.len])) {
        inWord = true; home(os.homedir()); raw += src.slice(i, i + e.len); i += e.len; continue;
      }
      inWord = true;
      if (e.kind === 'numeric') { sawExpansion = true; expanded(src.slice(i, i + e.len)); raw += src.slice(i, i + e.len); i += e.len; continue; }
      if (e.kind === 'sub') { substitution(); continue; }
      if (e.kind === 'brace') { braceParameter(); continue; }
      if (e.kind === 'ansi') {
        // $'...': the body up to an unescaped quote (`\'` does not end it)
        let j = i + 2;
        while (j < src.length && src[j] !== "'") j += src[j] === '\\' && j + 1 < src.length ? 2 : 1;
        if (j >= src.length) { opaque = true; ambiguous(); quoted(src.slice(i + 2)); raw += src.slice(i); i = src.length; break; }
        const body = ansiC(src.slice(i + 2, j));
        if (!ansiCQuoting) ambiguous();
        quoted(body); raw += src.slice(i, j + 1); i = j + 1;
        continue;
      }
      if (e.kind === 'locale') { ambiguous(); raw += '$'; i++; continue; }   // the `"` that follows is read as a double-quoted string
      if (e.kind === 'var' || e.kind === 'home') { opaqueExpansion(src.slice(i, i + e.len)); raw += src.slice(i, i + e.len); i += e.len; continue; }
      buf += c; marks += 'u'; raw += c; i++;   // a bare dollar: text
      continue;
    }
    if (c === '~' && !inWord) {
      const rest = src.slice(i + 1);
      if (rest === '' || /^[\s/;&|)]/.test(rest)) { inWord = true; home(os.homedir()); raw += '~'; i++; continue; }
      inWord = true; opaqueExpansion(c); raw += c; i++;   // ~user: not resolved here
      continue;
    }
    // operators
    if (c === '<' || c === '>' || c === '&' || c === '|' || c === ';' || c === '(' || c === ')') {
      // inside [[ ... ]] a > or < is a string comparison, not a redirection, and &&, ||, ( and ) are the
      // test's own operators: each a word of its own, the segment going on
      if (inTest && (c === '<' || c === '>')) { bareWord(c); i++; continue; }
      if (inTest && ((c === '&' && src[i + 1] === '&') || (c === '|' && src[i + 1] === '|'))) { bareWord(c + c); i += 2; continue; }
      if (inTest && (c === '(' || c === ')')) { bareWord(c); i++; continue; }
      // >(cmd) or <(cmd): a process substitution. cmd runs and is read like a $(...); the word stands
      // for a /dev/fd path the hook cannot resolve, so `tee >(cat) file` still names file.
      if ((c === '>' || c === '<') && src[i + 1] === '(') {
        endWord();
        i += 2;
        const inner = skipNested('(', ')');
        seg.subs.push(inner);
        inWord = true;
        const t = c + '(' + inner + ')';
        opaqueExpansion(t); raw += t;
        endWord();
        continue;
      }
      // a digits-only word glued to < or > is the descriptor (2>file still writes file): drop it
      if (inWord && /^[0-9]+$/.test(buf) && (c === '<' || c === '>')) { buf = ''; raw = ''; marks = ''; inWord = false; }
      else endWord();
      if (c === '(' && src[i + 1] === '(') { i += 2; skipArithmetic(); continue; }   // (( ... )) compares or counts
      // A write redirection's operator, then zsh's optional clobber-override suffix (M2, the fifth commit): `!` or `|`
      // after `>`, `>>`, `>&`, `>>&`, `&>` or `&>>`. The recorded op is the operator as spelled, so the refusal names it;
      // with a `!` the bash reading is recorded too (a file named `!` when a space follows, `!word` when glued, see
      // endWord), since bash does not know the suffix and the guard does not know which shell runs the line.
      const clobberSuffix = (op) => {
        if (src[i] === '|') { i++; return { kind: 'target', op: op + '|' }; }
        if (src[i] === '!') {
          i++;
          const glued = i < src.length && !/[\s;&|()<>]/.test(src[i]);
          if (!glued) seg.redirects.push({ op: op + '!', target: word('!', true, '!', { marks: 'u' }) });   // bash: the target is a file named `!`
          return { kind: 'target', op: op + '!', bang: glued ? 'glued' : 'spaced' };
        }
        return { kind: 'target', op };
      };
      if (c === '>') {
        let op = '>';
        i++;
        if (src[i] === '>') { op = '>>'; i++; }
        if (src[i] === '&') {
          i++;
          // a dup (2>&1, >&-) is no write; `>& word` writes word, and zsh's `>>& word` appends both streams to it. The dup is
          // read only when the word after `>&` is exactly a digit run or exactly `-` and a word delimiter follows (round 5,
          // 2026-09-20: any word opening with a digit or `-` was skipped as a dup, so `printf x >&2-3` in a tracked folder was
          // invisible while bash and zsh wrote the file `2-3`, and zsh writes `2-`, `-2` and `1-` too); `>>&` is zsh's alone and
          // has no dup form there (`>>&2` appends to a file named `2`, measured), so it is never a dup.
          const dup = op === '>' ? (src.slice(i).match(/^(?:[0-9]+|-)(?=$|[\s;&|()<>])/) || [null])[0] : null;
          if (dup) { i += dup.length; continue; }
          op += '&';
        }
        expect = clobberSuffix(op);
        continue;
      }
      if (c === '<') {
        if (src[i + 1] === '<' && src[i + 2] === '<') { i += 3; expect = { kind: 'herestring' }; continue; }
        if (src[i + 1] === '<') { const strip = src[i + 2] === '-'; i += strip ? 3 : 2; expect = { kind: 'heredoc', stripTabs: strip }; continue; }
        if (src[i + 1] === '>') { i += 2; expect = { kind: 'target', op: '<>' }; continue; }
        if (src[i + 1] === '&') { i += 2; while (i < src.length && /[0-9-]/.test(src[i])) i++; continue; }
        i++; expect = { kind: 'data' }; continue;
      }
      if (c === '&') {
        if (src[i + 1] === '>') { const app = src[i + 2] === '>'; i += app ? 3 : 2; expect = clobberSuffix(app ? '&>>' : '&>'); continue; }
        if (src[i + 1] === '&') { i += 2; endSegment('&&'); continue; }
        i++; endSegment('&'); continue;
      }
      if (c === '|') { const or = src[i + 1] === '|'; i += or ? 2 : 1; endSegment(or ? '||' : '|'); continue; }
      if (c === ';') { i += src[i + 1] === ';' ? 2 : 1; endSegment(';'); continue; }
      // ( or ): a segment break and a scope marker
      i++; endSegment(c);
      segments.push({ ...newSegment(), paren: c });
      continue;
    }
    inWord = true; buf += c; marks += 'u'; raw += c; i++;
  }
  endSegment('');
  readHeredocBodies();
  if (pendingHeredocs.length) opaque = true;
  return { segments: splitAtClosers(segments), opaque };
}

// THE CLOSING BRACE (round 5's third addendum, 2026-09-20; the round's verifier found twenty live false allows in one family
// at the second addendum's head, every one a `}` sharing a segment with words before it). THE RULE, stated here and read by
// every frame kind through the segments it produces: an unquoted `}` that follows other words in its segment ends its
// construct only after those words are read as the construct's own command, and every word after it begins a new command;
// so the lexer cuts the segment before such a brace (command | brace and the rest), before any frame logic runs,
// and a `}` is always the first word of its segment (or preceded by `}` alone). A brace body, function body, group or
// repeat body written on one line is then walked exactly as its `;` or newline twin, by the same code, and no frame kind
// needs a reading of its own. Before this, the function-body scan popped its frame at `f() { cd ../scratch }` before the cd
// in the same segment was read, so the cd was followed as plain sequence and `cp ../base/report.md report.md` from docs/ was
// allowed while zsh wrote docs/report.md (13 spellings: `function f { .. }`, `function f() { .. }`, `f g () { .. }`, `! f()
// { .. }`, nested, two commands, a newline separator, an `&&` join, a redirect after the brace, a quoted operand, pushd, a
// group holding the definition); the compound body's reader spliced the shared-segment brace and left the words after it,
// `else { .. }`, `always { .. }`, a body after a condition group, as OPERANDS of the body's command (`if (( 1 )) { cp .. }
// else { : }`: the copy's destination read as a source; `{ : } always { cp .. }`, `while { cp .. } { break }`: the writer
// never a command); and `repeat 1 { cp .. }` read the brace body as repeat's operands. Each of those is refused now, with the
// construct named. The command's segment keeps the redirections, heredocs, substitutions and arithmetic of the line (a
// redirection on `{ cd x } > f` is opened before the group runs, in the directory the shell started in, where a judgment
// before the cd reads it) and remembers the braces cut from its tail (`closerTail`): bash and dash read a `}` after a command
// as one more operand (`cp a }` writes a file named `}` where no group is open; they reject the group spelling and run
// nothing), so extract judges a writer under both readings. zsh's `} always {` continues the group it follows: the three
// words are dropped, so the try-list and the always-list are one group, closed by the last brace, whose operator says whether
// the whole construct ran in a subshell (`{ x=1 } always { : } | cat` keeps x unchanged in zsh, F5). bash and dash have no
// `always`: when the try-list's `}` shares its segment with the try-list's last command (`{ : } always { cd ../scratch; }`),
// they read that brace, `always`, `{` and the words after them on the same segment as OPERANDS of that command and close the
// group at the next `}` of its own, so the always-list's first command runs in zsh alone (from docs/, followed by `cp
// ../base/report.md report.md`, zsh moved and bash and dash wrote docs/report.md, the matrix's row); the piece is marked
// `alwaysHead`, and extract reads a cd there as a move it cannot know and an assignment there as unreadable. When the
// try-list's `}` has its own segment (`{ :; } always { cd ../docs; }`), bash and dash reject the line at `always` and run
// nothing (measured), so zsh's reading alone stands and the piece is not marked. A quoted brace is an operand and is not read
// here (`cp a '}'`), nor by any frame's brace count or reserved-word read (`braces`, `compoundBody`, the group scan,
// `closedConstruct`, `peelIndex`, `commandOf`, `rawHeadIndexOf`, the lexer's `[[`): round 5's fourth addendum found `braces`
// popping a function frame at `echo "}"` and `commandOf` skipping a quoted `{` as if reserved, each a live false allow.
function splitAtClosers(segments) {
  const brace = (w) => (plainWord(w) && (w.text === '{' || w.text === '}') ? w.text : null);
  const out = [];
  for (const seg of segments) {
    const pieces = [];
    let words = seg.words;
    let arithAt = seg.arithAt || [];
    for (;;) {
      let alwaysHead = false;   // this piece's command is the first of an always-list whose `} always {` follows a cut in this segment
      while (words.length >= 3 && brace(words[0]) === '}' && plainWord(words[1]) && words[1].text === 'always' && brace(words[2]) === '{') {
        words = words.slice(3);
        arithAt = arithAt.map((n) => n - 3).filter((n) => n >= 0);
        alwaysHead = words.length > 0 && pieces.length > 0;
      }
      let before = false;   // a word other than `}` stands before the brace in this piece
      let cut = -1;
      for (let i = 0; i < words.length && cut < 0; i++) {
        if (brace(words[i]) === '}') { if (before) cut = i; }
        else before = true;
      }
      if (cut < 0) { pieces.push({ words, arithAt, alwaysHead }); break; }
      let tailEnd = cut;
      while (tailEnd < words.length && brace(words[tailEnd]) === '}') tailEnd++;
      pieces.push({ words: words.slice(0, cut), arithAt: arithAt.filter((n) => n <= cut), closerTail: words.slice(cut, tailEnd), alwaysHead });
      words = words.slice(cut);
      arithAt = arithAt.filter((n) => n > cut).map((n) => n - cut);
    }
    // the first piece is the segment itself, keeping its redirections, heredocs, substitutions, arithmetic and paren marker; a
    // later piece emptied by the `always` drop is not a command; the last piece keeps the operator that ended the segment
    const kept = [pieces[0], ...pieces.slice(1).filter((p) => p.words.length)];
    const op = seg.op;   // read before the first piece, the segment itself, takes `;` (`{ x=1 } | cat` had lost its pipe to that overwrite)
    kept.forEach((p, i) => {
      const s = i === 0 ? seg : newSegment();
      s.words = p.words;
      s.arithAt = p.arithAt;
      s.closerTail = p.closerTail || null;
      s.alwaysHead = !!p.alwaysHead;
      s.op = i === kept.length - 1 ? op : ';';
      out.push(s);
    });
  }
  return out;
}

// ── a path the hook could not check ───────────────────────────────
//
// The walk-around lens second pass (2026-09-19, the walk-around lens's second pass): a filesystem error other than ENOENT on a path the hook
// judges (an lstat, a realpath or a listing that fails with EACCES, ELOOP, ENOTDIR or anything else) is an answer
// the hook does not have, and it REFUSES the write, naming the error and the entry that blocked the check, where
// before each such error unwound to a catch that read it as allow (`chmod 755 notes && cp base/report.md
// notes/n1.md` with notes/ mode 000 at check time overwrote the tracked note; the whole project mode 000 from a cwd
// outside it overwrote every tracked file; `.trackchanges` mode 000 read as a project that tracks nothing). The
// class is the reviewer's flip of class G applied to every judged path, so it runs from ANY cwd: a directory the
// hook cannot search may itself be a tracked project. The cost is a false refusal of a write under a directory the
// session may not search (that write fails on its own, EACCES, unless a chmod earlier in the same command opens it,
// which is the overwrite the class closes), recoverable in one step: make the entry readable in a command of its
// own, or spell a path that does not pass through it. ENOENT stays what it was: a file that does not exist yet.
class UnknownPath extends Error {
  constructor(code, p, why = null) { super(`${code}: ${p}`); this.code = code; this.path = p; this.why = why; }
}
const isUnknownPath = (e) => e instanceof UnknownPath;
// What an error code means, for the refusal.
function describeError(code) {
  return ({
    EACCES: 'permission denied', EPERM: 'operation not permitted', ELOOP: 'a link that loops', ENOTDIR: 'a component is not a directory',
    ENAMETOOLONG: 'the name is too long', EIO: 'an input/output error', EINVAL: 'not a readable value',
  })[code] || `error ${code}`;
}
// The deepest entry on the way to `p` that the process can lstat: for an EACCES that is the folder whose mode blocks
// the check, for an ELOOP the link that loops, for an ENOTDIR the file a later segment treats as a folder.
function blockingEntry(p) {
  let q = p;
  for (let i = 0; i < 200; i++) {
    const parent = path.dirname(q);
    if (parent === q) return q;
    q = parent;
    try { fs.lstatSync(q); return q; } catch { /* keep climbing */ }
  }
  return q;
}
// A directory the hook must look into or through: an error other than ENOENT there is an UnknownPath.
function checkSearchable(dir) {
  try { fs.accessSync(dir, fs.constants.R_OK | fs.constants.X_OK); }
  catch (e) { if (!e || e.code !== 'ENOENT') throw new UnknownPath((e && e.code) || 'EACCES', dir); }
}
// A listing the hook needs: null when the directory does not exist, the names when it can be read, and an
// UnknownPath for any other failure (the walk-around lens second pass; before, every failure read as an empty or absent folder).
function readdirOrNull(dir) {
  try { return fs.readdirSync(dir); }
  catch (e) { if (e && e.code === 'ENOENT') return null; throw new UnknownPath((e && e.code) || 'EACCES', dir); }
}

// ── paths as the kernel opens them ─────────────────────────────────

// A path as segments between slashes, each { t, m } (text, and marks or null for literal text), empty ones
// dropped; and back again.
function segmentsOf(text, marks) {
  const segs = [];
  let s = 0;
  for (let i = 0; i <= text.length; i++) {
    if (i === text.length || text[i] === '/') { if (i > s) segs.push({ t: text.slice(s, i), m: marks ? marks.slice(s, i) : null }); s = i + 1; }
  }
  return segs;
}
const joinSegments = (segs) => '/' + segs.map((s) => s.t).join('/');
const isExpansion = (seg) => seg.m != null && seg.m.includes('x');
const wholeExpansion = (seg) => seg.m != null && seg.m.length > 0 && !/[^x]/.test(seg.m);

// The segments of an absolute path folded as the kernel would open it: `.` dropped, and each `..` applied to the
// REAL path of the directory before it when that directory exists and is spelled literally (a link there leads
// elsewhere, and the kernel follows it before it goes up), lexically when it does not exist yet (a folder the
// command makes first, or one an expansion names). Returns { segs }, { unresolvable: <prefix> } when a directory
// before a `..` exists but cannot be resolved or searched (a link that loops, or a directory the hook may not
// stat because it or a parent is mode 000: the kernel could not open the path either, so the write's landing is
// unknown, class G, round 4, 2026-09-19; a dangling link is followed to where its target would be, as realPathOf
// resolves one, so it folds), or { emptiable: true } when the `..` would cancel a segment that is nothing but an
// expansion (the header: such a segment could be empty at run time were the set widened, and the shell would then
// climb one level higher than the fold; round 3, defence in depth).
function foldSegments(segs) {
  const acc = [];
  let hops = 0;
  for (const seg of segs) {
    if (seg.t === '.') continue;
    if (seg.t !== '..') {
      acc.push(seg);
      // class H (the walk-around lens second pass, 2026-09-19): a link this command makes earlier in the line is followed here, as the
      // kernel will follow it once it exists, so `ln -s ../web/docs d && cp x d/../report.md` climbs from the link's
      // TARGET; the prefix match on the unfolded spelling that round 4 used missed `./d`, `base/../d` and `d/../d`.
      if (activeLinks && activeLinks.size && !acc.some(isExpansion)) {
        for (let n = 0; n < 40; n++) {
          const target = applyInCommandLinks(joinSegments(acc), activeLinks);
          if (target == null) break;
          if (++hops > 40) return { unresolvable: joinSegments(acc) };
          acc.length = 0;
          acc.push(...segmentsOf(target, null));
        }
      }
      continue;
    }
    if (!acc.length) continue;   // the root's parent is the root
    if (wholeExpansion(acc[acc.length - 1])) return { emptiable: true };
    if (!acc.some(isExpansion)) {
      const prefix = joinSegments(acc);
      // class G (round 4, 2026-09-19) and the walk-around lens second pass: a directory the hook cannot stat or search before a `..` (mode 000
      // at check time, a link that loops, a file where a directory is needed) is an UnknownPath, thrown from
      // lstatOrNull or realPathOf and refused by evaluate with the error named, never folded lexically. Round 4 caught
      // the error here and answered { unresolvable }, refused only while a project was in play; the same error on the
      // target itself unwound to evaluate's catch, which read it as allow (`chmod 755 locked && cp base/report.md
      // locked/lnk/report.md` overwrote the tracked file). A link chain deeper than realPathOf follows is unresolvable.
      const st = lstatOrNull(prefix);
      if (st) {
        const real = realPathOf(prefix);
        if (real == null) return { unresolvable: prefix };
        acc.length = 0;
        acc.push(...segmentsOf(path.dirname(real), null));
        continue;
      }
    }
    acc.pop();
  }
  return { segs: acc };
}
// The links the command under judgment makes (class H), read by foldSegments while extract and evaluate run: an
// absolute link path the command creates, mapped to the absolute path it points at.
let activeLinks = null;

// A literal target's path as the kernel would open it (foldSegments), resolved against `dir` when relative:
// { path }, { unresolvable }, or null when the target is relative and no directory is known.
function resolveLiteral(text, dir) {
  const abs = path.isAbsolute(text) ? text : (dir ? dir + '/' + text : null);
  if (abs == null) return null;
  const folded = foldSegments(segmentsOf(abs, null));
  if (folded.unresolvable) return { unresolvable: folded.unresolvable };
  return { path: joinSegments(folded.segs) };
}
// The same as one string, or null (unresolvable or unplaceable): for a stat the caller makes.
function literalPath(text, dir) {
  const r = resolveLiteral(text, dir);
  return r && r.path ? r.path : null;
}
// The path `abs` leads to through a symlink the command creates before this word (class H, 2026-09-19): `links`
// maps an absolute link path the command makes to the absolute path it points at, so `ln -s docs mydocs && cp x
// mydocs/report.md` reads mydocs/report.md as docs/report.md. Called by foldSegments on each prefix as it folds
// (the walk-around lens second pass), so the match is on the folded path and a `..` after the link climbs from its target, as the kernel
// does. Returns the rewritten path, or null when no recorded link is a prefix of `abs`.
function applyInCommandLinks(abs, links) {
  const p = abs.replace(/\/{2,}/g, '/');
  let best = null;
  for (const dst of links.keys()) if ((p === dst || p.startsWith(dst + '/')) && (!best || dst.length > best.length)) best = dst;
  return best == null ? null : links.get(best) + p.slice(best.length);
}
// The directory a `cd` names, as the shell resolves it: lexically (bash, zsh and dash fold `..` against the
// spelling of the current directory, not its real path, unless told otherwise), so a `cd link/..` lands beside
// the link. Absolute text needs no directory.
function resolveAgainst(text, cwd) {
  if (path.isAbsolute(text)) return path.normalize(text);
  if (!cwd) return null;
  return path.resolve(cwd, text);
}
// Whether the command could enter `dir` when the hook runs: a directory (a link to one included) the process
// may search. A `cd` to anything else fails in bash, zsh and dash, the shell stays where it was, and a `;` list
// goes on (round 3: `cd nosuchdir; cp base/report.md docs/report.md` was judged under nosuchdir/ while the copy
// ran in the project; a mode-000 directory, a regular file and a dangling link fail the same way).
function enterable(dir) {
  try {
    if (!fs.statSync(dir).isDirectory()) return false;
    fs.accessSync(dir, fs.constants.X_OK);
    return true;
  } catch { return false; }
}

// ── pathname expansion ─────────────────────────────────────────────

const escapeRe = (s) => s.replace(/[.*+?^${}()|[\]\\/]/g, '\\$&');
const POSIX_CLASSES = {
  alpha: 'a-zA-Z', digit: '0-9', alnum: 'a-zA-Z0-9', upper: 'A-Z', lower: 'a-z', space: '\\s', blank: ' \\t',
  punct: '!-\\/:-@\\[-`{-~', xdigit: '0-9A-Fa-f', cntrl: '\\x00-\\x1f', graph: '!-~', print: ' -~',
};
// A path segment's unquoted glob characters as a RegExp over one name (`*` any run, `?` one
// character, `[...]` a class, `[!...]` or `[^...]` its complement, a `[` with no `]` text), or null
// when the segment has none. As in the shell, a name starting with `.` is matched only by a pattern
// starting with a `.`.
function globRegex(text, marks) {
  let re = '';
  let any = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (marks[i] !== 'u') { re += escapeRe(c); continue; }
    if (c === '*') { any = true; re += '[^/]*'; continue; }
    if (c === '?') { any = true; re += '[^/]'; continue; }
    if (c === '[') {
      let j = i + 1;
      if (text[j] === '!' || text[j] === '^') j++;
      if (text[j] === ']') j++;   // a ] first is a member
      while (j < text.length && text[j] !== ']') j++;
      if (j >= text.length) { re += '\\['; continue; }   // unmatched: text
      any = true;
      let body = text.slice(i + 1, j);
      let neg = false;
      if (body[0] === '!' || body[0] === '^') { neg = true; body = body.slice(1); }
      let cls = '';
      for (let k = 0; k < body.length; k++) {
        const m = body.slice(k).match(/^\[:([a-z]+):\]/);
        if (m && POSIX_CLASSES[m[1]]) { cls += POSIX_CLASSES[m[1]]; k += m[0].length - 1; continue; }
        cls += '\\]^['.includes(body[k]) ? '\\' + body[k] : body[k];
      }
      re += '[' + (neg ? '^' : '') + cls + ']';
      i = j;
      continue;
    }
    re += escapeRe(c);
  }
  if (!any) return null;
  if (text[0] !== '.') re = '(?!\\.)' + re;
  try { return new RegExp('^' + re + '$'); } catch { return null; }
}

// The paths an unquoted glob names, read off the filesystem as the shell would expand it (one
// literal word per match, absolute, in name order; a literal tail after a glob segment must
// exist; a trailing slash keeps only directories; a `..` climbs from the real path of an existing
// directory, as the kernel does). [] when nothing matches (zsh then runs nothing, and bash passes
// the pattern text through as a name, one no session means as a path). null when the hook cannot
// expand it: a relative pattern with the cwd unknown, or more directory entries or matches than the
// caps, a word the caller keeps as unresolvable.
const GLOB_MATCH_CAP = 2000;
const GLOB_READ_CAP = 50000;
function expandGlob(w, cwd) {
  const text = w.text;
  const marks = w.marks || 'u'.repeat(text.length);
  const absolute = path.isAbsolute(text);
  if (!absolute && !cwd) return null;
  let paths = [absolute ? path.parse(text).root : cwd];
  const parts = [];
  for (let s = 0, i = 0; i <= text.length; i++) {
    if (i === text.length || text[i] === '/') { if (i > s) parts.push([text.slice(s, i), marks.slice(s, i)]); s = i + 1; }
  }
  const trailingDir = text.endsWith('/');
  let read = 0;
  let globbed = false;
  const stepUp = (p) => {
    if (path.dirname(p) === p) return p;
    if (!lstatOrNull(p)) return path.dirname(p);
    const real = realPathOf(p);
    return real == null ? null : path.dirname(real);
  };
  for (const [t, m] of parts) {
    const re = globRegex(t, m);
    if (!re) {
      if (t === '.') continue;
      if (t === '..') { paths = paths.map(stepUp).filter((p) => p != null); continue; }
      paths = paths.map((p) => path.join(p, t));
      continue;
    }
    globbed = true;
    const next = [];
    for (const p of paths) {
      let names;
      try { names = fs.readdirSync(p); } catch { continue; }
      read += names.length;
      if (read > GLOB_READ_CAP) return null;
      names.sort();
      for (const n of names) {
        if (!re.test(n)) continue;
        next.push(path.join(p, n));
        if (next.length > GLOB_MATCH_CAP) return null;
      }
    }
    paths = next;
    if (!paths.length) return [];
  }
  if (!globbed) return [word(text, true, w.raw)];
  const out = [];
  for (const p of paths) {
    let isDir = false;
    let exists = true;
    try { isDir = fs.statSync(p).isDirectory(); } catch { try { fs.lstatSync(p); } catch { exists = false; } }   // a dangling link exists
    if (!exists || (trailingDir && !isDir)) continue;
    out.push(word(trailingDir ? p + '/' : p, true, w.raw));
  }
  return out;
}

// ── the grammar: which words a segment would write ─────────────────

// Per-wrapper option tables (the walk-around lens third pass, rule (b), 2026-09-19): a wrapper in PREFIXES is parsed
// IN FULL against its table or the command is refused as unreadable, naming the option. Before, an option the guard
// did not know was skipped as a flag and an argument-taking option was read only in the spellings a list named, so
// the next spelling walked around it: `env -Cdocs cp …` (a glued short form) was not a chdir, `env --chd=docs` and
// `env --c docs` (GNU abbreviations) were skipped, a nested `env -C docs env -C ..` kept the second chdir alone,
// resolved against the cwd, and `env -S` was read as a shell string when env applies its OWN getopt to the split
// words (`env -S '-u FOO cp a b'`, `env -S '-C docs cp …'`, `env -S '-- cp …'` each ran a copy the shell reading
// took for a non-writer). Each table is taken from the wrapper's own `--help` on this box (coreutils 9.x env, nice,
// nohup, timeout and stdbuf; util-linux ionice, setsid, flock, taskset and chrt; numactl's command-running options;
// sudo 1.9; GNU time; bash 5.2's `command`, `builtin`, `exec` and `time`): `argShort` letters take a value (glued or
// the next word, as getopt reads them), `flagShort` letters take none, `argLong` names take a value (`=` or the next
// word), `flagLong` none, `optLong` a value glued with `=` only. `chdir` names the option pair that runs the command
// in another directory (env -C, sudo -D), `script` the pair that hands a string to `$SHELL -c` (flock -c, read like
// `sh -c`), `writes` the pair whose value is a FILE the wrapper writes (GNU time -o), `lead` the count of positional
// operands before the command (flock's lockfile, taskset's mask, chrt's priority, timeout's duration), `numeric`
// whether a bare `-N` is an adjustment (nice -19), `dash` whether a lone `-` is a flag (env - cmd). `refuse` names
// the options the guard reads as OPAQUE and never recurses: env -S/--split-string (env's own splitter: options,
// assignments, `--` and its own quoting rules over the string; the reviewer's ruling), and sudo's -e (edits files),
// -i and -s (run a shell over the rest), -R (a chroot moves every path) and -h (help or host, by its argument). A
// long option is matched exactly: an abbreviation (`--chd`) or an unknown name refuses, with the remedy of the long
// form the guard knows or the wrapper dropped. The gap of every table falls on the REFUSE side: an option missing
// from a table is a false refusal, recoverable in one step, never a write that passes.
const WRAPPER_OPT = {
  sudo: {
    argShort: 'CDgprtTUu', flagShort: 'AbBEHKknPSVv',
    argLong: ['close-from', 'chdir', 'group', 'host', 'prompt', 'role', 'type', 'command-timeout', 'other-user', 'user'],
    flagLong: ['askpass', 'background', 'bell', 'preserve-env', 'set-home', 'help', 'remove-timestamp', 'reset-timestamp', 'list', 'non-interactive', 'preserve-groups', 'stdin', 'version', 'validate'],
    optLong: ['preserve-env'], chdir: { short: 'D', long: 'chdir' }, refuse: { short: 'eishR', long: ['edit', 'login', 'shell', 'chroot'] },
  },
  env: {
    argShort: 'uC', flagShort: 'i0v', argLong: ['unset', 'chdir'],
    flagLong: ['ignore-environment', 'null', 'debug', 'help', 'version', 'list-signal-handling'], optLong: ['block-signal', 'default-signal', 'ignore-signal'],
    chdir: { short: 'C', long: 'chdir' }, refuse: { short: 'S', long: ['split-string'] }, dash: true,
  },
  nice: { argShort: 'n', flagShort: '', argLong: ['adjustment'], flagLong: ['help', 'version'], numeric: true },
  nohup: { argShort: '', flagShort: '', argLong: [], flagLong: ['help', 'version'] },
  time: { argShort: 'fo', flagShort: 'apqv', argLong: ['format', 'output'], flagLong: ['append', 'portability', 'quiet', 'verbose', 'help', 'version'], writes: { short: 'o', long: 'output' } },
  timeout: { argShort: 'ks', flagShort: 'v', argLong: ['kill-after', 'signal'], flagLong: ['preserve-status', 'foreground', 'verbose', 'help', 'version'], lead: 1 },
  ionice: { argShort: 'cnpPu', flagShort: 'thV', argLong: ['class', 'classdata', 'pid', 'pgid', 'uid'], flagLong: ['ignore', 'help', 'version'] },
  stdbuf: { argShort: 'ioe', flagShort: '', argLong: ['input', 'output', 'error'], flagLong: ['help', 'version'] },
  setsid: { argShort: '', flagShort: 'cfwhV', argLong: [], flagLong: ['ctty', 'fork', 'wait', 'help', 'version'] },
  flock: {
    argShort: 'wE', flagShort: 'sxunoFhV', argLong: ['timeout', 'conflict-exit-code'],
    flagLong: ['shared', 'exclusive', 'unlock', 'nonblock', 'close', 'no-fork', 'verbose', 'help', 'version'], lead: 1, script: { short: 'c', long: 'command' },
  },
  taskset: { argShort: '', flagShort: 'apchV', argLong: [], flagLong: ['all-tasks', 'pid', 'cpu-list', 'help', 'version'], lead: 1 },
  chrt: {
    argShort: 'TPD', flagShort: 'bdfiorRampvhV', argLong: ['sched-runtime', 'sched-period', 'sched-deadline'],
    flagLong: ['batch', 'deadline', 'fifo', 'idle', 'other', 'rr', 'reset-on-fork', 'all-tasks', 'max', 'pid', 'verbose', 'help', 'version'], lead: 1,
  },
  numactl: { argShort: 'ipPCNm', flagShort: 'abl', argLong: ['interleave', 'preferred', 'preferred-many', 'physcpubind', 'cpunodebind', 'membind'], flagLong: ['all', 'balancing', 'localalloc'] },
  command: { argShort: '', flagShort: 'pvV', argLong: [], flagLong: [] },
  builtin: { argShort: '', flagShort: '', argLong: [], flagLong: [] },
  exec: { argShort: 'a', flagShort: 'cl', argLong: [], flagLong: [] },
  // zsh's precommand modifiers take no option (zshmisc(1), Precommand Modifiers): an option after one refuses like any other
  noglob: { argShort: '', flagShort: '', argLong: [], flagLong: [] },
  nocorrect: { argShort: '', flagShort: '', argLong: [], flagLong: [] },
  '-': { argShort: '', flagShort: '', argLong: [], flagLong: [] },
};

// Words of a segment after the command's prefixes (sudo and its options, env with its options and
// K=V arguments, nice, the round-4 wrappers, ...), leading assignments and reserved words. Returns
// { name, args, chdirs, writes, wrapped }, with `chdirs` the directories the wrappers run the command
// in, IN ORDER (`env -C DIR`, `env --chdir=DIR`, `sudo -D DIR`, and a nested `env -C a env -C b`, whose
// second directory resolves against the first: the caller enters each in turn, so the inner command's
// relative paths are judged where the kernel runs it, round 4 and the third pass), `writes` the files a
// wrapper itself writes (`time -o FILE`); { script, scriptFlag } when a wrapper runs a shell string
// (`flock … -c 'cmd'`); { unknown: { option, wrapper, value, rest } } when a wrapper carries an option
// its table does not parse in full (the caller refuses, naming it; `value` is a `=value` part, `rest` the
// words after it, each a candidate the own-project step judges); { opaque: { option, wrapper, script,
// rest } } for env -S and the sudo options the table refuses outright; or null for an empty segment.
function commandOf(words) {
  let k = 0;
  const chdirs = [];
  const writes = [];
  const wrappers = [];   // the wrappers peeled, in order (the seventh pass: the cd text names the innermost one and what it does with a cd)
  let wrapped = false;   // the walk-around lens second pass (family 6): a wrapper prefix was peeled before the command
  for (;;) {
    while (k < words.length && plainWord(words[k]) && RESERVED.has(words[k].text)) k++;   // unquoted: `"{" cd ../scratch` runs a command named `{`, and the cd is its operand (round 5's fourth addendum)
    const first = k;
    while (k < words.length && /^[A-Za-z_][A-Za-z0-9_]*\+?=/.test(words[k].raw)) k++;
    // The readability rule (the sixth pass's attacker, C5c, 2026-09-19): after a wrapper an assignment-shaped word is the
    // wrapper's ARGUMENT, not an assignment (bash looks `command x=b` up as a command; env sets it for a command that is not
    // there; `time x=b` assigns in bash alone), so the segment is not assignment-only: the words come back as the arguments
    // of a command with no name, and recordSegment (taintWord) reads each as a write it does not follow. Before, null came back and
    // the caller read the segment as plain assignments, so `x=../docs/report.md; command x=other.md; cp base/report.md
    // scratch/$x` resolved $x to other.md while every shell kept the tracked path.
    if (k >= words.length) return wrapped ? { name: '', args: words.slice(first), chdirs, writes, wrapped, wrappers } : null;
    const name = path.basename(words[k].text);
    if (!PREFIXES.has(name)) return { name, args: words.slice(k + 1), chdirs, writes, wrapped, wrappers };
    wrapped = true;
    wrappers.push(name);
    k++;
    const spec = WRAPPER_OPT[name];
    let lead = spec.lead || 0;
    const unknown = (option, value = null) => ({ unknown: { option, wrapper: name, value, rest: words.slice(k + 1) } });
    const opaque = (option, script) => ({ opaque: { option, wrapper: name, script, rest: words.slice(k + 1) } });
    // the value of an option at letter `j` of word `k`: the glued rest of the word, else the next word
    const valueAt = (j) => (j < words[k].text.length - 1 ? sliceWord(words[k], j + 1) : (words[k + 1] || null));
    while (k < words.length) {
      const w = words[k];
      const t = w.text;
      if (t === '--') { k++; break; }
      // a word the shell fills in before the command: a lead positional it may stand for (`timeout "$T" cmd`); anything
      // else could be an option or the command itself, and neither is parsed, so it refuses (the third pass)
      if (!w.literal) { if (lead > 0) { lead--; k++; continue; } return unknown(w.raw); }
      if (t === '-') { if (spec.dash) { k++; continue; } break; }
      if (!t.startsWith('-') || t.length < 2) {
        if (lead > 0) { lead--; k++; continue; }   // a leading positional: flock's lockfile, taskset's mask, chrt's priority, timeout's duration
        break;   // the command
      }
      if (t.startsWith('--')) {
        const eq = t.indexOf('=');
        const nm = eq < 0 ? t.slice(2) : t.slice(2, eq);
        const value = eq < 0 ? (words[k + 1] || null) : sliceWord(w, eq + 1);
        const step = eq < 0 ? 2 : 1;
        if (spec.refuse && spec.refuse.long.includes(nm)) return opaque(`${name} --${nm}`, value);
        if (spec.chdir && nm === spec.chdir.long) { chdirs.push({ word: value, flag: `${name} --${nm}` }); k += step; continue; }
        if (spec.script && nm === spec.script.long) return { script: value, scriptFlag: `${name} --${nm}` };
        if (spec.writes && nm === spec.writes.long) { if (value) writes.push(value); k += step; continue; }
        if (spec.argLong.includes(nm)) { k += step; continue; }
        if (spec.optLong && spec.optLong.includes(nm)) { k++; continue; }
        if (eq < 0 && spec.flagLong.includes(nm)) { k++; continue; }
        return unknown(t, eq < 0 ? null : value);
      }
      if (spec.numeric && /^-\d+$/.test(t)) { k++; continue; }   // nice -19: the adjustment
      // a short option, alone or in a cluster: flags go on, the first value-taking letter ends the cluster
      let step = 1;
      let done = false;
      for (let j = 1; j < t.length && !done; j++) {
        const ch = t[j];
        if (spec.refuse && spec.refuse.short.includes(ch)) return opaque(`${name} -${ch}`, valueAt(j));
        if (spec.chdir && ch === spec.chdir.short) { chdirs.push({ word: valueAt(j), flag: `${name} -${ch}` }); step = j < t.length - 1 ? 1 : 2; done = true; break; }
        if (spec.script && ch === spec.script.short) return { script: valueAt(j), scriptFlag: `${name} -${ch}` };
        if (spec.writes && ch === spec.writes.short) { const v = valueAt(j); if (v) writes.push(v); step = j < t.length - 1 ? 1 : 2; done = true; break; }
        if (spec.argShort.includes(ch)) { step = j < t.length - 1 ? 1 : 2; done = true; break; }
        if (spec.flagShort.includes(ch)) continue;
        return unknown(`-${ch}`);
      }
      k += step;
    }
  }
}

// Whether a file landing under `dir` (absolute; it need not exist yet) could be tracked. False
// only when the directory does not exist and its nearest existing ancestor sits under no project
// with a non-empty tracked list: nothing can be nested under a directory that is not there, and a
// project whose list is empty tracks nothing. An existing directory may hold a project of its own
// below it, so a copy into one is walked. With TRACKCHANGES_ROOT set every path is judged against
// that root, so nothing is skipped.
function mayHoldTracked(dir) {
  if (process.env.TRACKCHANGES_ROOT) return true;
  let p = dir;
  for (;;) {
    let exists = false;
    try { exists = fs.existsSync(p); } catch { /* unreadable: treat as absent */ }
    if (exists) break;
    const parent = path.dirname(p);
    if (parent === p) return false;
    p = parent;
  }
  if (p === dir) return true;
  let root = findVaultRoot(path.join(p, 'x'));   // findVaultRoot starts at the parent of the path given
  // a nearest root whose list is empty may sit inside a project whose list is not (the walk-around lens second pass, family 5)
  while (root && !trackedPaths(root).length) { const up = path.dirname(root); root = up === root ? null : findVaultRoot(path.join(up, 'x')); }
  return !!root && trackedPaths(root).length > 0;
}

// The files a copy of `src` lands as when its destination is `dst`: `dst` itself for a file, and
// for a directory source (cp -r, mv of a folder) each file under it at dst/<its path>, never the
// directory itself. The whole source tree is walked (the copy itself reads every file, so the walk
// costs less than the command), except when nothing under the landing directory could be tracked
// (mayHoldTracked). A source the hook cannot read (absent, not literal) is taken as one file.
function landing(src, dst, cwd) {
  if (!src.literal) return [dst];
  const abs = literalPath(src.text, cwd);
  let isDir = false;
  try { isDir = abs != null && fs.statSync(abs).isDirectory(); } catch { /* absent or unreadable: one file */ }
  if (!isDir) return [dst];
  const dstAbs = dst.literal ? literalPath(dst.text, cwd) : null;
  if (!dstAbs) return [dst];   // an unresolvable destination: the caller drops it
  if (!mayHoldTracked(dstAbs)) return [];
  const out = [];
  const stack = [''];
  while (stack.length) {
    const rel = stack.pop();
    let entries;
    try { entries = fs.readdirSync(path.join(abs, rel), { withFileTypes: true }); } catch { continue; }
    for (const e of entries) {
      const r = rel ? path.join(rel, e.name) : e.name;
      if (e.isDirectory()) stack.push(r);   // a symlinked directory is copied as a link: one entry, not descended
      else out.push(word(path.join(dst.text, r), true, dst.raw));
    }
  }
  return out;
}

// install's -d / --directory: every operand is a directory to create and no file is written. The
// flag is read inside a short-option cluster too (`-dm755`, `-pd`), stopping at a letter that takes the
// rest of the word as its value (m, o, g, S, Z, t), and case-sensitive: `-D` copies a file. install only:
// `cp -d` is --no-dereference and `ln -d` still makes a link (review round 1, 2026-09-18: `install -d "$A"
// "$B"` was refused as a copy whose destination the hook could not read, and the literal `install -d docs/new
// notes/new2` as a write under a tracked folder, though the command makes directories and writes no file).
function installDirOnly(t) {
  if (t === '--directory') return true;
  if (!/^-[^-]/.test(t)) return false;
  for (const ch of t.slice(1)) {
    if (ch === 'd') return true;
    if ('mogSZt'.includes(ch)) return false;
  }
  return false;
}

// Per-writer option tables for cp, mv, install and ln, taken from coreutils' own option definitions
// (`<verb> --help`, coreutils 9.x), so the operand walk never GUESSES whether an option consumes the
// next word (review round 4, 2026-09-19: the guessed table treated cp/mv's `-Z` and a bare `--context`
// as consuming an operand, when both take none; `cp -Z base/report.md docs/report.md` had the source
// eaten as `-Z`'s argument, the destination misread, and the copy onto the tracked file allowed). Each
// verb lists: `argShort`, the short letters that take an argument (its glued rest, or the next word);
// `flagShort`, the short letters that take none; and `argLong` (long options needing a SEPARATE word
// when spelled without `=`) beside `knownLong` (every long option name, so an option the table does not
// know refuses the command rather than being read as a flag). `-t`/`--target-directory`,
// `-T`/`--no-target-directory` and install's `-d`/`--directory` are handled before the table (they set
// where the copy lands or make it write no file). An optional-argument option (`--backup`, `--context`,
// `cp --preserve`, `--reflink`, `--update`) takes a word only when glued with `=`, so it sits in
// `knownLong` (a flag) and not in `argLong`.
const COPY_OPT = {
  cp: {
    argShort: 'S',
    flagShort: 'abdfHilLnPpRrsuvxZ',
    argLong: new Set(['suffix', 'sparse', 'no-preserve']),
    knownLong: new Set(['archive', 'attributes-only', 'backup', 'copy-contents', 'debug', 'force', 'interactive', 'link', 'dereference', 'no-clobber', 'no-dereference', 'parents', 'recursive', 'remove-destination', 'strip-trailing-slashes', 'symbolic-link', 'no-target-directory', 'verbose', 'one-file-system', 'help', 'version', 'preserve', 'no-preserve', 'reflink', 'sparse', 'update', 'context', 'suffix', 'target-directory']),
  },
  mv: {
    argShort: 'S',
    flagShort: 'bfinuvZ',
    argLong: new Set(['suffix']),
    knownLong: new Set(['backup', 'force', 'interactive', 'no-clobber', 'no-copy', 'strip-trailing-slashes', 'update', 'verbose', 'context', 'debug', 'help', 'version', 'suffix', 'target-directory', 'no-target-directory']),
  },
  install: {
    argShort: 'gmoS',
    flagShort: 'bcCdDpsvZ',
    argLong: new Set(['group', 'mode', 'owner', 'strip-program', 'suffix']),
    knownLong: new Set(['backup', 'compare', 'directory', 'debug', 'group', 'mode', 'owner', 'preserve-timestamps', 'strip', 'strip-program', 'suffix', 'target-directory', 'no-target-directory', 'verbose', 'preserve-context', 'context', 'help', 'version']),
  },
  ln: {
    argShort: 'S',
    flagShort: 'bdFfiLnPrsv',
    argLong: new Set(['suffix']),
    knownLong: new Set(['backup', 'directory', 'force', 'interactive', 'logical', 'no-dereference', 'physical', 'relative', 'symbolic', 'suffix', 'target-directory', 'no-target-directory', 'verbose', 'help', 'version']),
  },
};
const sliceWord = (a, n) => word(a.text.slice(n), a.literal, a.raw, { glob: a.glob, marks: a.marks && a.marks.slice(n) });

// The words an option the table does not know leaves unplaced (rule (f), the third pass, 2026-09-19): with such an
// option in the list the walk cannot tell an operand from the option's value, so every operand-looking word, and the
// `=value` of a long option, is a candidate the caller records as a target it cannot read (judged by its own project
// from any cwd) or marks as a path the command may have changed.
function optionCandidates(args) {
  const out = [];
  for (const a of args) {
    const t = a.text;
    if (t.startsWith('--') && t.includes('=')) { out.push(sliceWord(a, t.indexOf('=') + 1)); continue; }
    if (t.startsWith('-') && t.length > 1) continue;
    out.push(a);
  }
  return out;
}

// Rule (d) (the walk-around lens third pass, 2026-09-19, recast by the reviewer as an ALLOWLIST whose gap falls on the
// safe side): a shell option the command sets or clears changes how the shell reads a later path, a cd or a glob, and
// the guard models none of that, so an option on `set`, `shopt`, `setopt` or `unsetopt` that is not on the inert list
// leaves the directory UNKNOWN from that point, and a later literal relative target refuses with the construct named.
// The second pass listed `set -P`, `set -o physical` and `setopt chase_links`, and zsh's `set -o chaselinks` and
// `set -o chasedots` walked around the list.
//
// THE CRITERION (the fifth commit, 2026-09-19; the reviewer's ruling after the fourth pass found eleven options on the
// lists against the rule as stated: `-f`, `noglob`, `nomatch`, `badpattern`, `numericglobsort`, `markdirs`, `cdsilent`,
// `pushdsilent`, `pushdignoredups`, `pushdminus`, `extquote`). An option earns a place on an inert list only if it
// changes NEITHER how a word is expanded, matched or split (globbing, brace expansion, quoting, aliases, history
// expansion, parameter and pattern substitution, field splitting, spelling correction), NOR where a relative path
// resolves (cd, pushd, physical paths, links, CDPATH), NOR which grammar is in force (posix, restricted, sh emulation,
// keyword assignments, short loop forms, comments). Everything else, exit status, tracing, history RECORDING, completion,
// prompts, job control, line editing, arithmetic output, startup files, is inert. Every entry below carries the one-line
// reason it meets the criterion, verified by reading the option's description in bash 5.2.21 (`help set`; the shopt
// section of bash(1)), zsh 5.9 (zshoptions(1)) and dash 0.5.12 (dash(1)) on this box on 2026-09-19, and by execution
// where the description left a doubt (`set -k` let `cp base/report.md docs/report.md X=1` write the tracked file, since
// with keyword assignments the trailing word is an assignment, not a third operand; `histsubstpattern` changed what
// `${v:s/?x?/report/}` expanded to; `ksharrays` changed what `$a` expanded to; `nocasematch` and `patsub_replacement`
// changed a pattern substitution's result). An option whose description left a doubt the box could not settle is OFF
// the list (`multibyte`, `combiningchars`, the bash `compatNN` options, `assoc_expand_once`): unverified defaults to the
// refuse side. Applying the criterion took the eleven off and, by the same rule, twenty-six more from the `set -o` list
// (`histexpand`, `keyword`, `localpatterns`, `histsubstpattern`, `cshjunkiehistory`, `correct`, `correctall`,
// `sunkeyboardhack`, `combiningchars`, `multibyte`, `ksharrays`, `kshzerosubscript`, `kshtypeset`, `shortloops`,
// `shortrepeat`, `cshjunkieloops`, `shwordsplit` and the nine of the eleven that are `set -o` names), twelve from the
// shopt list (`assoc_expand_once`, `compat31` to `compat44`, `extquote`, `nocasematch`, `noexpand_translation`,
// `patsub_replacement`) and six letters (`-f` bash noglob, `-k` bash keyword, `-E` zsh pushdsilent, `-H` bash histexpand,
// `-F` zsh noglob, `-y` zsh shwordsplit). A single letter is inert only when it is inert in BOTH bash and zsh (the Bash
// tool runs one of the two and the guard does not know which), each letter's option in each shell read off `set -X;
// set -o` on this box. Names are compared as zsh compares them (case and underscores ignored, a `no` prefix negating),
// so `set -o pipe_fail`, `setopt NO_NOMATCH` and `shopt -s histappend` read as their plain spellings. A gap here (an
// inert option not listed) is a false refusal, recoverable in one step (drop the option, or spell the target
// absolutely), never a write that passes. INERT_OPTIONS is exported for the data-driven test that holds every entry to a
// real option of a shell on this box, a reason, and, for a letter, an inert option in both shells.
const INERT_SET_LETTERS_WHY = {
  e: { bash: 'errexit', zsh: 'errexit', why: 'exit on a failing command; no word or path changes' },
  u: { bash: 'nounset', zsh: 'nounset', why: 'an unset variable is an error that stops the command; the guard reads no value from the environment beyond HOME' },
  x: { bash: 'xtrace', zsh: 'xtrace', why: 'traces commands to stderr' },
  v: { bash: 'verbose', zsh: 'verbose', why: 'echoes input lines to stderr' },
  n: { bash: 'noexec', zsh: 'noexec', why: 'reads commands without running them; nothing writes' },
  C: { bash: 'noclobber', zsh: 'noclobber', why: 'a `>` refuses to overwrite an existing file; the guard reads the redirection as a write either way' },
  a: { bash: 'allexport', zsh: 'allexport', why: 'marks assigned variables for export; no expansion or path change' },
  m: { bash: 'monitor', zsh: 'monitor', why: 'job control' },
  b: { bash: 'notify', zsh: null, why: 'job-status notices in bash; zsh refuses `set -b` as an unknown option, and nothing after it changes' },
  h: { bash: 'hashall', zsh: 'histignoredups', why: 'command-location caching in bash; history recording in zsh' },
  t: { bash: 'onecmd', zsh: 'singlecommand', why: 'the shell exits after one command; what follows never runs' },
};
const INERT_SET_OPTIONS_WHY = {
  // bash `set -o` and dash `set -o`
  allexport: 'marks assigned variables for export', emacs: 'the line editor mode', errexit: 'exit on a failing command',
  errtrace: 'the ERR trap is inherited by functions', functrace: 'the DEBUG and RETURN traps are inherited by functions',
  hashall: 'command-location caching', history: 'command history is recorded', ignoreeof: 'end-of-file does not exit the shell',
  interactivecomments: 'comments in an interactive shell; the Bash tool runs a non-interactive one, where a `#` word is a comment whichever way this is set (measured on this box)',
  monitor: 'job control', noclobber: 'a `>` refuses to overwrite; the guard reads the redirection as a write either way',
  noexec: 'reads commands without running them', nolog: 'accepted and ignored by bash', notify: 'job-status notices',
  nounset: 'an unset variable is an error that stops the command', onecmd: 'the shell exits after one command',
  pipefail: 'a pipeline\'s exit status', verbose: 'echoes input lines', vi: 'the line editor mode', xtrace: 'traces commands',
  // zsh: errors, tracing, scoping
  errreturn: 'return from a function on a failing command', evallineno: 'line numbers inside eval', localoptions: 'options set in a function are restored at its return',
  localtraps: 'traps set in a function are restored at its return', localloops: 'break and continue stop at a function boundary',
  warncreateglobal: 'a warning when a function creates a global', warnnestedvar: 'a warning when a function sets an outer variable',
  typesetsilent: 'typeset prints nothing for an existing parameter', typesettounset: 'a declared parameter stays unset until assigned; the guard reads no declared value',
  printexitvalue: 'prints a non-zero exit status', printeightbit: 'eight-bit characters in completion listings', continueonerror: 'a script goes on after a fatal error',
  debugbeforecmd: 'when the DEBUG trap runs', sourcetrace: 'announces each file the shell loads', trapsasync: 'when traps run while waiting for a child',
  singlecommand: 'the shell exits after one command',
  // zsh: clobbering, which the guard reads as a write either way, and multiple redirections, each of which it names
  clobber: 'whether `>` may overwrite; the redirection is read as a write either way', clobberempty: 'whether `>` may overwrite an empty file; read as a write either way',
  appendcreate: 'whether `>>` may create under NO_CLOBBER; read as a write either way', histallowclobber: 'adds `|` to redirections in the history record',
  multios: 'several redirections tee or cat; the guard names every target either way',
  // zsh: history recording (banghist, history EXPANSION, is off the list: it rewrites later words)
  appendhistory: 'the history file is appended', extendedhistory: 'timestamps in the history file', histexpiredupsfirst: 'which history entries are trimmed first',
  histfcntllock: 'how the history file is locked', histfindnodups: 'duplicates in a history search', histignorealldups: 'duplicates dropped from the history list',
  histignoredups: 'consecutive duplicates dropped from the history list', histignorespace: 'a line starting with a space is not recorded',
  histlexwords: 'how a history file is split into words when READ back', histnofunctions: 'function definitions are not recorded', histnostore: 'the history command is not recorded',
  histreduceblanks: 'blanks trimmed in the history record', histsavebycopy: 'how the history file is rewritten', histsavenodups: 'duplicates dropped when the history file is written',
  histverify: 'a history expansion is shown before it runs', histbeep: 'a beep on a missing history entry', incappendhistory: 'history lines are appended as entered',
  incappendhistorytime: 'history lines are appended after each command', sharehistory: 'the history file is shared between shells',
  // zsh: prompts, completion, listing and the line editor (interactive machinery)
  promptbang: '`!` in prompts', promptcr: 'a carriage return before the prompt', promptpercent: '`%` in prompts', promptsp: 'a partial line before the prompt is preserved',
  promptsubst: 'expansions in prompts', transientrprompt: 'the right prompt is removed after a line', alwayslastprompt: 'completion listings return to the prompt',
  alwaystoend: 'the cursor after a completion', autolist: 'ambiguous completions are listed', automenu: 'menu completion after repeated tabs',
  autoparamkeys: 'the character inserted after a completed parameter', autoparamslash: 'a slash after a completed directory parameter',
  autoremoveslash: 'a completed slash removed before a delimiter', bashautolist: 'listing on the second completion request', completealiases: 'aliases are distinct for completion',
  completeinword: 'completion from inside a word', listambiguous: 'when a completion list is shown', listbeep: 'a beep on an ambiguous completion',
  listpacked: 'completion list layout', listrowsfirst: 'completion list layout', listtypes: 'file-type marks in completion listings',
  menucomplete: 'menu completion', recexact: 'an exact completion match is accepted', dvorak: 'the keyboard layout spelling correction assumes; correction itself is off this list',
  singlelinezle: 'single-line command editing', zle: 'the line editor is used', overstrike: 'the line editor starts in overstrike mode',
  flowcontrol: 'start/stop characters in the line editor', beep: 'a beep on a line-editor error',
  // zsh: command hashing and job control
  hashcmds: 'command locations are cached', hashdirs: 'command directories are cached', hashexecutablesonly: 'only executables are cached',
  hashlistall: 'the whole command path is hashed before completion', pathdirs: 'a command name with a slash is searched on PATH too; which binary runs, not what it writes',
  pathscript: 'a script file named at invocation is searched on PATH', autocontinue: 'disowned stopped jobs are continued', autoresume: 'a one-word command resumes a job of that name',
  bgnice: 'background jobs run at a lower priority', checkjobs: 'jobs are reported before exit', checkrunningjobs: 'running jobs are reported before exit',
  hup: 'jobs get SIGHUP at exit', longlistjobs: 'the long job-notice format', mailwarning: 'a warning about a read mail file', posixjobs: 'job control in subshells',
  posixtraps: 'EXIT traps in functions', posixargzero: '$0 keeps the invocation name',
  // zsh: syntax choices that move no path and change no expansion
  bsdecho: 'the echo builtin\'s escape handling', bashrematch: 'which variables a `=~` match sets', rematchpcre: 'the regex dialect of `=~`', casematch: 'case sensitivity of `=~`',
  cbases: 'the output format of hexadecimal arithmetic', octalzeroes: 'a leading zero reads as octal in arithmetic', forcefloat: 'arithmetic is floating point',
  cprecedences: 'arithmetic operator precedence', kshoptionprint: 'how option settings are printed', kshautoload: 'how an autoloaded function file is read',
  functionargzero: '$0 inside a function', cshnullcmd: 'a bare redirection fails instead of running NULLCMD; the redirection is read as a write either way',
  shnullcmd: 'a bare redirection runs `:`; the redirection is read as a write either way', rcs: 'startup files after /etc/zsh/zshenv', globalrcs: 'the global startup files',
  login: 'a login shell', globalexport: 'typeset -x also sets -g', rmstarsilent: 'no prompt before `rm *`', rmstarwait: 'a wait before the `rm *` prompt',
};
const INERT_SHOPT_WHY = {
  checkhash: 'a hashed command is checked to exist before it runs', checkjobs: 'jobs are listed before exit', checkwinsize: 'LINES and COLUMNS are updated',
  cmdhist: 'a multi-line command is one history entry', completefullquote: 'quoting of metacharacters in completed names', execfail: 'a failed exec does not exit the shell',
  extdebug: 'debugger behaviour', forcefignore: 'FIGNORE suffixes in completion', gnuerrfmt: 'the error message format', histappend: 'the history file is appended',
  histreedit: 'a failed history substitution can be re-edited', histverify: 'a history substitution is shown before it runs', hostcomplete: 'hostname completion',
  huponexit: 'jobs get SIGHUP when a login shell exits', inheriterrexit: 'command substitution inherits errexit',
  interactivecomments: 'comments in an interactive shell; the Bash tool runs a non-interactive one, where a `#` word is a comment whichever way this is set (measured on this box)',
  lithist: 'newlines are kept in multi-line history entries', localvarinherit: 'a local variable inherits the outer value; the guard reads no declared value',
  localvarunset: 'unsetting a local variable in an outer scope', loginshell: 'set by the shell for a login shell, read-only', mailwarn: 'a warning about a read mail file',
  noemptycmdcompletion: 'completion on an empty line', progcomp: 'programmable completion', progcompalias: 'alias expansion for programmable completion',
  promptvars: 'expansions in prompts', shiftverbose: 'an error message from shift', varredirclose: 'a `{var}>file` descriptor is closed after the command; the file is written either way',
  xpgecho: 'the echo builtin\'s escape handling',
};
const INERT_SET_LETTERS = Object.keys(INERT_SET_LETTERS_WHY).join('');
const INERT_SET_OPTIONS = new Set([...Object.keys(INERT_SET_OPTIONS_WHY)]);
const INERT_SHOPT = new Set([...Object.keys(INERT_SHOPT_WHY)]);
export const INERT_OPTIONS = { letters: INERT_SET_LETTERS_WHY, set: INERT_SET_OPTIONS_WHY, shopt: INERT_SHOPT_WHY };
const normalizeOption = (name) => name.toLowerCase().replace(/[_-]/g, '');
function inertOption(name, table) {
  const n = normalizeOption(name);
  return table.has(n) || (n.startsWith('no') && table.has(n.slice(2)));
}
// Whether a `set` or `shopt` turns on bash's keyword mode (`set -k`, `set -o keyword`, `shopt -so keyword`), under which an
// assignment-shaped word ANYWHERE in a simple command is an assignment and not an operand (M5's criterion took `-k` off
// the inert list as a grammar change, and execution showed why: `set -k; cp base/report.md docs/report.md X=1` wrote the
// tracked file in bash while the guard read three operands and a destination that is no directory, so no write at all).
// zsh has no such mode (`-k` is interactivecomments there), so extract reads a later writer's operands BOTH ways.
function setsKeywordMode(name, args) {
  if (name !== 'set' && name !== 'shopt') return false;
  for (let k = 0; k < args.length; k++) {
    const t = args[k].text;
    if (!args[k].literal) continue;
    if (name === 'set' && /^-[A-Za-z]*k/.test(t)) return true;
    if (/^-[A-Za-z]*o/.test(t) && args[k + 1] && args[k + 1].literal && normalizeOption(args[k + 1].text) === 'keyword') return true;
  }
  return false;
}
const isAssignmentWord = (w) => /^[A-Za-z_][A-Za-z0-9_]*\+?=/.test(w.raw);
// The reason a `set`/`shopt`/`setopt`/`unsetopt` leaves the directory unknown, or null when every option it names is
// inert (or it only prints or queries). Positional parameters after `set` are not options (`set -- a b`, `set x y`).
function shellOptionChange(name, args) {
  const reason = (w) => `an earlier \`${name} ${w}\` sets a shell option that may make the shell resolve paths physically, or that I do not know to be inert for paths, cd and globbing, so where a later relative path lands is not known`;
  if (name === 'set') {
    for (let k = 0; k < args.length; k++) {
      const w = args[k];
      const t = w.text;
      if (t === '--' || t === '-' || t === '+') break;   // positional parameters follow, or `set -` (tracing off)
      if (!/^[-+]/.test(t)) break;
      if (!w.literal) return reason(w.raw);
      for (let j = 1; j < t.length; j++) {
        const ch = t[j];
        if (ch === 'o') {
          const v = args[k + 1];
          if (!v) return null;   // `set -o` alone lists the options
          if (!v.literal || !inertOption(v.text, INERT_SET_OPTIONS)) return reason(`${t} ${v.raw}`);
          k++;
          break;
        }
        if (!INERT_SET_LETTERS.includes(ch)) return reason(t);
      }
    }
    return null;
  }
  if (name === 'shopt') {
    let setO = false;
    let changes = false;
    let flags = '';
    const names = [];
    for (const w of args) {
      const t = w.text;
      if (!w.literal) return reason(w.raw);
      if (/^-[supqo]+$/.test(t)) { flags += (flags ? ' ' : '') + t; if (t.includes('o')) setO = true; if (t.includes('s') || t.includes('u')) changes = true; continue; }
      if (t.startsWith('-')) return reason(t);
      names.push(w);
    }
    if (!changes) return null;   // a print or a query changes nothing
    for (const w of names) if (!inertOption(w.text, setO ? INERT_SET_OPTIONS : INERT_SHOPT)) return reason(`${flags} ${w.raw}`);
    return null;
  }
  // setopt / unsetopt: single letters with - or +, `-o NAME`, and bare option names
  for (let k = 0; k < args.length; k++) {
    const w = args[k];
    const t = w.text;
    if (!w.literal) return reason(w.raw);
    if (t === '--') continue;
    if (/^[-+]/.test(t) && t.length > 1) {
      for (let j = 1; j < t.length; j++) {
        const ch = t[j];
        if (ch === 'o') { const v = args[k + 1]; if (!v) return null; if (!v.literal || !inertOption(v.text, INERT_SET_OPTIONS)) return reason(`${t} ${v.raw}`); k++; break; }
        if (!INERT_SET_LETTERS.includes(ch)) return reason(t);
      }
      continue;
    }
    if (!inertOption(t, INERT_SET_OPTIONS)) return reason(w.raw);
  }
  return null;
}

// The operands of a cp/mv/install/ln command, its `-t`/`--target-directory` folder and its
// `-T`/`--no-target-directory` flag, per the verb's option table. Returns { operands, targetDir,
// noTargetDir }, { installDir: true } when it writes only directories (install -d), or { unknown } when
// an option the table does not know is met, so the caller refuses the command naming that option (the
// remedy: spell it without the option, or use the long form the table knows).
function parseCopyOptions(args, verb) {
  const spec = COPY_OPT[verb];
  const operands = [];
  let targetDir = null;
  let noTargetDir = false;
  let parents = false;   // cp --parents: each source lands at <destination>/<the source path as spelled> (the pin addendum)
  for (let k = 0; k < args.length; k++) {
    const a = args[k];
    const t = a.text;
    if (t === '--') { operands.push(...args.slice(k + 1)); break; }
    if (t === '-t' || t === '--target-directory') { targetDir = args[k + 1] || null; k++; continue; }
    if (t.startsWith('--target-directory=')) { targetDir = sliceWord(a, 19); continue; }
    if (t === '-T' || t === '--no-target-directory') { noTargetDir = true; continue; }
    if (verb === 'install' && a.literal && installDirOnly(t)) return { installDir: true };
    if (t.startsWith('--') && t.length > 2) {
      const eq = t.indexOf('=');
      const nameL = eq < 0 ? t.slice(2) : t.slice(2, eq);
      if (eq < 0 && spec.argLong.has(nameL)) { k++; continue; }   // a separate argument
      if (verb === 'cp' && eq < 0 && nameL === 'parents') { parents = true; continue; }
      if (spec.knownLong.has(nameL)) continue;                     // a flag, or a value glued with `=`
      return { unknown: t };
    }
    if (t.startsWith('-') && t.length > 1) {
      let consumedNext = false;
      let unknown = null;
      for (let j = 1; j < t.length; j++) {
        const ch = t[j];
        if (ch === 't') {   // -tDIR (glued) or -t DIR (next word)
          if (j < t.length - 1) targetDir = sliceWord(a, j + 1);
          else { targetDir = args[k + 1] || null; consumedNext = true; }
          break;
        }
        if (ch === 'T') { noTargetDir = true; continue; }
        if (verb === 'install' && ch === 'd') return { installDir: true };
        if (spec.argShort.includes(ch)) { if (j === t.length - 1) consumedNext = true; break; }   // its glued rest, or the next word, is the value
        if (spec.flagShort.includes(ch)) continue;
        unknown = '-' + ch;
        break;
      }
      if (unknown) return { unknown };
      if (consumedNext) k++;
      continue;
    }
    operands.push(a);
  }
  return { operands, targetDir, noTargetDir, parents };
}

// cp / mv / install / ln: the last operand is the destination, unless -t DIR names the directory;
// a destination that is an existing directory receives each source under its own name. A glob
// operand is expanded first, as the shell expands it before the command sees its operands. A
// link is one directory entry whatever it points at: ln names its link and walks no source.
// `cp --parents` (the pin addendum, 2026-09-19; the fourth and fifth passes' `cp --parents docs/report.md ../web/`
// wrote web/docs/report.md while the guard, which knew the option as a flag, judged web/report.md): the source
// lands at <destination>/<the source path as spelled>, a `..` in it climbing from the destination as cp's own
// `../web2/../abs/a/b/c.md` does, and the destination is a directory or cp writes nothing (one that is not there
// when the hook runs is read as one, the refuse side).
// Returns { targets } or { unknown } (an option the table does not know, for the caller to refuse).
function copyTargets(args, cwd, verb) {
  const land = (s, d) => (verb === 'ln' ? [d] : landing(s, d, cwd));
  const parsed = parseCopyOptions(args, verb);
  if (parsed.unknown) return { unknown: parsed.unknown };
  if (parsed.installDir) return { targets: [] };   // directories made, no file written
  const { operands, targetDir: targetDirRaw, noTargetDir, parents } = parsed;
  // the name a source takes under a destination directory: its basename, or with --parents its whole spelling
  const under = (dirText, s) => {
    if (!parents) return word(path.join(dirText, path.basename(s.text)), s.literal, s.raw, { at: dirText });
    const prefix = dirText.replace(/\/+$/, '') + '/';
    const rel = s.text.replace(/^\/+/, '');
    const cut = s.text.length - rel.length;
    return word(prefix + rel, s.literal, s.raw, { at: dirText, marks: s.marks ? 'q'.repeat(prefix.length) + s.marks.slice(cut) : null, numeric: s.numeric });
  };
  let targetDir = targetDirRaw;
  const expanded = [];
  for (let k = 0; k < operands.length; k++) {
    const o = operands[k];
    if (!o.glob) { expanded.push(o); continue; }
    const m = expandGlob(o, cwd);
    // A source that matches nothing is no operand (zsh runs nothing; bash names a file that is not there
    // and cp stops). A destination that matches nothing is a target the hook cannot read (bash writes the
    // pattern's text as the name; 2026-09-18), as is a glob past the caps or with the cwd unknown: one
    // operand, not literal, for the refusal to name.
    const isDst = !targetDir && k === operands.length - 1;
    if (!m || (!m.length && isDst)) expanded.push(word(o.text, false, o.raw, { marks: o.marks }));
    else expanded.push(...m);
  }
  // A destination or a target folder the hook cannot read is returned as it stands (not literal), so the
  // caller's add records it for the refusal (2026-09-18); before, it was dropped and the copy passed.
  const out = [];
  if (targetDir) {
    if (targetDir.glob) { const m = expandGlob(targetDir, cwd); targetDir = m && m.length === 1 ? m[0] : word(targetDir.text, false, targetDir.raw, { marks: targetDir.marks }); }
    if (!targetDir.literal) return { targets: [targetDir] };
    for (const s of expanded) out.push(...land(s, under(targetDir.text, s)));
    return { targets: out };
  }
  if (expanded.length < 2) return { targets: out };
  const dst = expanded[expanded.length - 1];
  if (!dst.literal) return { targets: [dst] };
  const resolved = literalPath(dst.text, cwd);
  let isDir = parents;   // with --parents the destination is a directory, or cp writes nothing
  if (!noTargetDir && resolved && !isDir) { try { isDir = fs.statSync(resolved).isDirectory(); } catch { isDir = /\/$/.test(dst.text); } }
  if (isDir) {
    for (const s of expanded.slice(0, -1)) out.push(...land(s, under(dst.text, s)));
    return { targets: out };
  }
  if (expanded.length === 2) return { targets: land(expanded[0], dst) };
  // three or more operands and a destination that is no directory: cp, mv, install and ln each stop
  // with "target is not a directory" and write nothing
  return { targets: out };
}

// sed: every file operand when -i / --in-place is given (the script is the first operand unless
// -e or -f supplied it).
function sedTargets(args) {
  let inPlace = false;
  let scriptGiven = false;
  const operands = [];
  for (let k = 0; k < args.length; k++) {
    const a = args[k];
    if (a.text === '--') { operands.push(...args.slice(k + 1)); break; }
    if (a.text === '-e' || a.text === '--expression' || a.text === '-f' || a.text === '--file') { scriptGiven = true; k++; continue; }
    if (a.text === '-l' || a.text === '--line-length') { k++; continue; }
    if (a.text.startsWith('--expression=') || a.text.startsWith('--file=')) { scriptGiven = true; continue; }
    if (a.text === '--in-place' || a.text.startsWith('--in-place=')) { inPlace = true; continue; }
    if (a.text.startsWith('--')) continue;
    if (a.text.startsWith('-') && a.text.length > 1) {
      // a cluster: -ni, -Ei, -i.bak, -ne 's/x/y/' (e and f take the next word as the script)
      const letters = a.text.slice(1);
      let m = letters.match(/^([nrEszu]*)([ief])(.*)$/);
      if (m) {
        if (m[2] === 'i') inPlace = true;
        else { scriptGiven = true; if (m[3] === '') k++; }
      } else if (/i/.test(letters)) inPlace = true;
      continue;
    }
    operands.push(a);
  }
  if (!inPlace) return [];
  return scriptGiven ? operands : operands.slice(1);
}

// perl: every file operand when -i is among its switches (the program is the first operand unless
// -e / -E supplied it).
function perlTargets(args) {
  let inPlace = false;
  let scriptGiven = false;
  const operands = [];
  for (let k = 0; k < args.length; k++) {
    const a = args[k];
    if (a.text === '--') { operands.push(...args.slice(k + 1)); break; }
    if (a.text.startsWith('-') && a.text.length > 1) {
      const letters = a.text.slice(1);
      for (let j = 0; j < letters.length; j++) {
        const ch = letters[j];
        if (ch === 'i') { inPlace = true; break; }              // -i, -i.bak, -pi.bak: the rest is the suffix
        if (ch === 'e' || ch === 'E') { scriptGiven = true; if (j === letters.length - 1) k++; break; }
        if (ch === 'l' || ch === '0') { while (j + 1 < letters.length && /[0-7]/.test(letters[j + 1])) j++; continue; }   // optional octal, the cluster goes on (-lpe)
        if ('MmIxFCdDV'.includes(ch)) break;                     // switches that eat the rest of the word
      }
      continue;
    }
    operands.push(a);
  }
  if (!inPlace) return [];
  return scriptGiven ? operands : operands.slice(1);
}

// Paths a python or node script opens for writing, read off its text. A literal path with a write
// mode counts: open('x', 'w'), open('x', mode='a'), open('x', encoding='utf8', mode='w'),
// open(mode='w', file='x'), Path('x').open('w'), Path('x').write_text(...), shutil.copy(src, 'x');
// fs.writeFileSync('x', ...), appendFile, createWriteStream, openSync('x', 'w'), copyFile(src, 'x'),
// rename(src, 'x'). A call's arguments may span lines, as a formatter wraps them in a heredoc
// script. M4 (the fifth commit, 2026-09-19): a `$` inside a plain string is TEXT, so a literal path is kept
// whatever characters it holds and judged by its name (the fourth pass's matrix wrote a tracked
// `p$abc/rep.md` through eight interpreter forms while the scan dropped every path matching `[{}$]`,
// and the node classes excluded `$`); a TEMPLATE or FORMAT string (a python f-string, a string with
// `.format(` or `%` applied to it, a JS template literal holding `${`) is a path the interpreter fills
// in, which the hook can see and cannot read, so it is returned as unreadable (scriptTemplateTargets)
// and refused while a project is in play; a computed path (a name, `sys.argv`, `os.environ`,
// `process.env`, a call, a concatenation) stays out of model, by the contract.
const PY_ARG = '((?:[^()]|\\([^()]*\\))*)';   // an argument list with one level of nested parentheses (a `.format(...)`, a join)
const PY_OPEN = new RegExp(`\\b(?:io\\.)?open\\(${PY_ARG}\\)`, 'g');
const PY_PATH_OPEN = new RegExp(`\\bPath\\(${PY_ARG}\\)\\s*\\.open\\(${PY_ARG}\\)`, 'g');
const PY_PATH_WRITE = new RegExp(`\\bPath\\(${PY_ARG}\\)\\s*\\.write_(?:text|bytes)\\(`, 'g');
const PY_SHUTIL = new RegExp(`\\bshutil\\.(?:copy|copyfile|copy2|move)\\(${PY_ARG}\\)`, 'g');
// One JS string literal: its quote (group g) and its body (group g + 1). The body runs to the next quote of the SAME
// kind, so the other two quotes inside it are text (the pin addendum, 2026-09-19: a body class that excluded every
// quote could not span `\`docs/${"report"}.md\``, so a template literal holding a string was neither a literal nor a
// template and the write it named was never judged); a `${` inside a backtick body makes it a template (nodeStringArg).
const nodeStr = (g) => `(["'\`])((?:(?!\\${g})[^\\n])*)\\${g}`;
const NODE_STR = nodeStr(1);
// A path argument that BEGINS with a string literal and goes on (`'docs/' + name`, `'docs/x'.concat(y)`, `'a' .trim()`) is a
// path the interpreter builds from a literal the guard can see, so it is a template (unreadable, refused while a project is
// in play), never a miss: round 4's regression-1 found the `\s*[,)]` these classes required after the literal dropped such a
// call from both lists, where the base had refused it. The group after the literal holds the continuation (empty for a plain
// literal); nodeStringArg reads it. Python's pyStringArg makes the same decision (`rest`).
const NODE_WRITE = new RegExp(`\\b(?:writeFile|writeFileSync|appendFile|appendFileSync|createWriteStream|truncate|truncateSync)\\(\\s*${NODE_STR}(\\s*[^,)\\s][^,)]*)?\\s*[,)]`, 'g');
const NODE_OPEN = new RegExp(`\\b(?:open|openSync)\\(\\s*${NODE_STR}(\\s*[^,)\\s][^,)]*)?\\s*,\\s*(["'\`])([rwaxs+]*)\\4`, 'g');
const NODE_COPY = new RegExp(`\\b(?:copyFile|copyFileSync|rename|renameSync|cp|cpSync)\\(\\s*${nodeStr(1)}[^,]*,\\s*${nodeStr(3)}(\\s*[^,)\\s][^,)]*)?\\s*[,)]`, 'g');

// A python call's argument list, as { positional: [...], keyword: { name: text } }, each value
// the source text; commas inside quotes or nested parentheses do not split.
function pyArgs(list) {
  const parts = [];
  let cur = '';
  let q = null;
  let depth = 0;
  for (const ch of list) {
    if (q) { cur += ch; if (ch === q) q = null; continue; }
    if (ch === "'" || ch === '"') { q = ch; cur += ch; continue; }
    if (ch === '(' || ch === '[') depth++;
    else if (ch === ')' || ch === ']') depth--;
    if (ch === ',' && depth <= 0) { parts.push(cur); cur = ''; continue; }
    cur += ch;
  }
  if (cur.trim()) parts.push(cur);
  const positional = [];
  const keyword = {};
  for (const p of parts) {
    const m = p.match(/^\s*([A-Za-z_]\w*)\s*=(?!=)\s*([\s\S]*)$/);
    if (m) keyword[m[1]] = m[2];
    else positional.push(p);
  }
  return { positional, keyword };
}
// The text of a plain string literal ('x' or "x"), or null for anything else (an f-string, a name).
function pyString(text) {
  const r = pyStringArg(text);
  return r && r.literal != null ? r.literal : null;
}
// How a python string argument reads (M4): { literal } for a plain string whatever it holds (a `$`, a `{` in a non-f
// string are text; a raw or bytes prefix keeps the text as written), { template } for an f-string or a string with
// `.format(` or `%` applied to it (the interpreter fills the path in), and null for anything else (a name, a call, a
// concatenation: the computed path the contract leaves out of model).
function pyStringArg(text) {
  const s = String(text == null ? '' : text).trim();
  // the delimiter is three quotes or one (the pin addendum, 2026-09-19: a triple-quoted plain path was read as an empty
  // string with text after it and dropped, so `open("""docs/report.md""","w")` wrote the tracked file unjudged); the
  // body runs to the first closing delimiter, so the other quote inside it is text
  const m = s.match(/^([A-Za-z]{0,3})('''|"""|['"])([\s\S]*?)\2([\s\S]*)$/);
  if (!m) return null;
  const rest = m[4].trim();
  if (/f/i.test(m[1])) return { template: s };
  if (/^\.format\(/.test(rest) || /^%/.test(rest)) return { template: s };
  if (rest !== '') return { template: s };   // a literal that goes on (`'docs/' + x`, `'a' 'b'`): a path built from a literal the guard sees (round 5)
  return { literal: m[3] };
}
// `after` is what follows the literal before the argument ends (a `+ x`, a `.concat(y)`): a template then (round 5)
const nodeStringArg = (quote, body, after = '') => (after.trim() !== '' || (quote === '`' && body.includes('${')) ? { template: quote + body + quote + after } : { literal: body });
const PY_WRITE_MODE = /[wax+]/;

// Every write path a script names: `literal` paths (judged by name) and `template` strings (unreadable, refused while a
// project is in play).
function scanScript(kind, text) {
  const out = { literal: [], template: [] };
  const take = (r) => { if (!r) return; if (r.literal != null) out.literal.push(r.literal); else if (r.template) out.template.push(r.template); };
  const t = String(text);
  if (kind === 'python') {
    for (const m of t.matchAll(PY_OPEN)) {
      const { positional, keyword } = pyArgs(m[1]);
      const file = pyStringArg(keyword.file != null ? keyword.file : positional[0]);
      const mode = pyString(keyword.mode != null ? keyword.mode : (keyword.file != null ? positional[0] : positional[1]));
      if (file && mode != null && PY_WRITE_MODE.test(mode)) take(file);
    }
    for (const m of t.matchAll(PY_PATH_OPEN)) {
      const { positional, keyword } = pyArgs(m[2]);
      const mode = pyString(keyword.mode != null ? keyword.mode : positional[0]);
      if (mode != null && PY_WRITE_MODE.test(mode)) take(pyStringArg(pyArgs(m[1]).positional[0]));
    }
    for (const m of t.matchAll(PY_PATH_WRITE)) take(pyStringArg(pyArgs(m[1]).positional[0]));
    for (const m of t.matchAll(PY_SHUTIL)) { const { positional, keyword } = pyArgs(m[1]); take(pyStringArg(keyword.dst != null ? keyword.dst : positional[1])); }
  } else if (kind === 'node') {
    for (const m of t.matchAll(NODE_WRITE)) take(nodeStringArg(m[1], m[2], m[3] || ''));
    for (const m of t.matchAll(NODE_OPEN)) if (/[wa+]/.test(m[5])) take(nodeStringArg(m[1], m[2], m[3] || ''));
    for (const m of t.matchAll(NODE_COPY)) take(nodeStringArg(m[3], m[4], m[5] || ''));
  }
  return out;
}
// The literal write paths of a script (the grammar the tests pin); its template paths are scriptTemplateTargets.
export function scriptWriteTargets(kind, text) { return scanScript(kind, text).literal; }
export function scriptTemplateTargets(kind, text) { return scanScript(kind, text).template; }

// Interpreter options that take the next word as their operand; anything else starting with - is
// an option on its own, and the first other word is the script file.
const INTERPRETER_OPERANDS = {
  python: new Set(['-W', '-X', '--check-hash-based-pycs']),
  node: new Set(['-r', '--require', '--import', '--input-type', '-C', '--conditions', '--loader', '--experimental-loader', '--env-file', '--title']),
};

// What a shell (sh, bash, ...) runs, from its arguments: { script } for -c, alone or in a cluster
// (-lc, -ec; null when no operand follows), { stdin: true } when no -c and no script file is
// given (bash <<EOF, bash -s <<EOF, bash - <<EOF, a pipe), and {} for a script file, whose
// contents are not in the command. Each `o` in an option cluster takes the next word (`-euo
// pipefail`, `-ox errexit`), and under bash each `O` too (`-O extglob`, `-iO extglob`, `-Oc extglob
// '...'`): zsh takes no word after -O and dash rejects it (round 3: `bash -O extglob -c '<script>'`
// read extglob as the operand, the script was never scanned, and a literal tracked target in it
// passed).
function shellScript(args, shell) {
  let c = false;
  let s = false;
  let operand;
  for (let k = 0; k < args.length; k++) {
    const t = args[k].text;
    if (t === '--' || t === '-') { operand = args[k + 1]; break; }
    if (t === '-o' || t === '+o' || t === '--rcfile' || t === '--init-file' || (shell === 'bash' && (t === '-O' || t === '+O'))) { k++; continue; }
    if (/^[-+][A-Za-z]+$/.test(t)) {
      if (t[0] === '-' && t.includes('c')) c = true;
      if (t[0] === '-' && t.includes('s')) s = true;
      let takes = (t.match(/o/g) || []).length;
      if (shell === 'bash') takes += (t.match(/O/g) || []).length;
      k += takes;
      continue;
    }
    if (t.startsWith('--')) continue;
    operand = args[k];
    break;
  }
  if (c) return { script: operand || null };
  if (s || !operand) return { stdin: true };
  return {};
}

// The paths a command would write, each as { path, how }, resolved against `cwd` (the session's
// working directory; a `cd` earlier in the command moves it, a `cd` inside `( ... )` only up to
// the `)`, a `cd` inside an if, loop or case body leaves it unknown once the body closes, since
// the body may not run, and one the lexer cannot read, one to a directory the command cannot enter
// when the hook runs, `cd -` and popd leave it unknown too). A glob is expanded against the
// filesystem, as the shell would expand it before the command runs, so `sed -i ... docs/*.md`
// names each file. `how` names the writing construct for the refusal. Returns { targets, opaque,
// unresolved }: `unresolved` lists the write targets the hook could not read, each { raw, how, dir,
// at, numeric, text, marks, why } (the word as typed, the construct, the directory current at the
// write or null when unknown, the folder a copy lands in when that much is literal, the word's text
// when its only expansions are numeric else null, the text and marks themselves, and why a LITERAL
// word is here, when it is: { kind: 'unknownDir', text } for a relative one whose directory is not
// known, { kind: 'unresolvable', text } for one crossing a directory the hook cannot resolve), for
// evaluate to refuse while a tracked project is in play (the header; 2026-09-18). `shell` is the
// name of the shell whose script `command` is when the call is a recursion into `sh -c '...'`,
// `bash <<EOF` or a `$(...)` inside one (null for the Bash tool's own command): it decides how
// `$'...'` reads (lex). A recursion deeper than RECURSION_CAP substitutions is not followed and the
// command is marked opaque, so a command nested thousands deep cannot overflow the stack and take
// the literal targets read before it with it (round 3: about 1100 nested `$(` made evaluate's catch
// return allow on a command whose first word copied onto a tracked file).
const RECURSION_CAP = 64;
// The variables the guard EXPANDS from its own environment: HOME alone (for `~`, a leading `$HOME` and `${HOME}`,
// the lexer's 'h' mark). PWD, OLDPWD and TMPDIR are in the same class of names a command can reassign, but the guard
// never expands them, so their `$…` (and `~+`, `~-`) is already a word it cannot read; a name added to expansionAt
// goes here too, or an assignment to it would go unseen. The walk-around lens third pass (rule (a), 2026-09-19): the
// second pass listed the assignment FORMS (`HOME=`, `HOME+=`, `export`/`declare`/`typeset`/`local`/`readonly HOME`,
// `read HOME`, `printf -v HOME`, `mapfile`/`readarray HOME`, `getopts … HOME`, `for HOME in`), and the next spelling
// walked around the list: a nameref (`declare -n r=HOME; r=<dir>`), `select HOME in …`, the glued `printf -vHOME`.
// So the rule is keyed on what the guard can SEE, not on a list of forms: the bare identifier of an expanded variable
// appearing ANYWHERE in the command outside a `$`-expansion (as a word, inside a word such as `r=HOME` or `-vHOME`,
// quoted or not, or in an arithmetic body) makes that variable's expansion unreadable for the WHOLE command. The
// cost is a false refusal of a command that only mentions the name (`echo HOME=x; > ~/log`, `grep HOME rc > ~/out`,
// a path holding the text HOME) beside a `~/` or `$HOME/` write from a tracked cwd, recoverable by spelling the path;
// the gap the fourth pass found (2026-09-19): a NAME the shell fills in (`export ${h}${m}=…`, `declare -n r=${h}${m}`,
// `printf -v "${h}${m}"`, `typeset ${h}${m}=`, `read ${h}${m}`, `export "$(printf 'HOME=…')"`, `read -r "$(printf HOME)"`)
// reassigns HOME with no literal token anywhere, so assembledNameOperand (below) closes it on the visible construct.
// B2 as ruled (2026-09-19; the fifth pass's attacker on B2's first draft): valueOf substitutes PWD and OLDPWD beside HOME,
// and while this list named HOME alone `PWD=<web>; cp <web>/base/report.md $PWD/docs/report.md` from a tracked cwd was
// resolved through the directory the guard knew and allowed while the shell wrote the tracked file (refused as not
// literal before B2). The list names every name valueOf substitutes, so rule (a) and M1 cover
// each: a mention of PWD or OLDPWD outside an expansion, or a name the shell fills in, makes `$PWD`, `$OLDPWD`, `~+` and
// `~-` unreadable for the whole command (unreadableExpandedNames), and the word they stand in keeps the cwd rule.
const EXPANDED_NAMES = ['HOME', 'PWD', 'OLDPWD'];
function bareExpandedNames(segments) {
  const found = new Set();
  const scan = (text, marks) => {
    for (const name of EXPANDED_NAMES) {
      for (let at = text.indexOf(name); at >= 0; at = text.indexOf(name, at + 1)) {
        // outside an expansion: none of these characters came from one ('x') or from the guard's own home text ('h')
        if (marks && /[xh]/.test(marks.slice(at, at + name.length))) continue;
        found.add(name);
        break;
      }
    }
  };
  for (const s of segments) {
    for (const w of s.words) scan(w.text, w.marks);
    for (const r of s.redirects) scan(r.target.text, r.target.marks);
    for (const a of s.arith) scan(a, null);
  }
  return found;
}
// M1 (the fifth commit, 2026-09-19): a variable NAME the shell fills in. The fourth attack reassigned HOME with no literal
// HOME token by assembling the name (`h=HO; m=ME; export ${h}${m}=<dir>`, `declare -n r=${h}${m}; r=<dir>`, `printf -v
// "${h}${m}"`, `typeset ${h}${m}=`, `read ${h}${m}`) or by spelling it inside a substitution (`export "$(printf
// 'HOME=…')"`, `declare "$(…)"`, `read -r "$(printf HOME)"`), and the write through `$HOME` landed on the tracked file. The
// rule is keyed on the construct the guard can SEE without evaluating anything: a name operand that is not a literal
// identifier (it carries an expansion, a substitution, or is itself a quoted expansion) on an assignment, declaration,
// nameref, export, typeset, local, readonly, read, mapfile, getopts, unset or `printf -v`, a `let` or `(( ))` whose lvalue
// carries an expansion, marks EVERY expanded name (EXPANDED_NAMES) unreadable for the whole command, and a bare `cd` or
// a `cd ~` after it leaves the directory unknown, as rule (a) does; a name operand that is a literal identifier other than
// an expanded name (`export FOO="$BAR"`, `declare -n r=foo`, `read -p "$msg" ans`, `printf -v var "$x"`) changes nothing,
// and a read-only twin (`echo ${h}${m}`, `printf '%s' "$HOME"`) is not a name operand at all. The cost is a `~/` or
// `$HOME/` write beside such a construct from a tracked cwd, recoverable by spelling the path.
const NAME_OPERAND_COMMANDS = new Set(['export', 'declare', 'typeset', 'local', 'readonly', 'read', 'printf', 'mapfile', 'readarray', 'getopts', 'unset', 'let']);
// An expansion in lvalue position of an arithmetic body or a `let` word: `${h}${m} = 5`, `$x+=1`, `${n}++` (a comparison,
// `$x == 1`, `$x <= 1`, `$x != 1`, is not one).
const ARITH_ASSIGNED_EXPANSION = /(?:\$\{[^}]*\}|\$[A-Za-z_][A-Za-z0-9_]*|\$\([^)]*\))[A-Za-z0-9_${}]*\s*(?:\+\+|--|(?:[-+*/%&|^]|<<|>>)?=(?!=))/;
function assembledNameOperand(segments) {
  // whether the slice [from, to) of a word's text came from an expansion (an 'x' mark, or the NUL a `$(...)` stands as)
  const carries = (w, from = 0, to = undefined) => {
    if (!w) return false;
    if (!w.marks) return w.text.slice(from, to).includes('\0');
    return /x/.test(w.marks.slice(from, to)) || w.text.slice(from, to).includes('\0');
  };
  // the NAME part of a NAME[=VALUE] or NAME[+=VALUE] operand (up to the first unquoted `=`), and where its value starts
  const nameOf = (w) => {
    for (let i = 0; i < w.text.length; i++) {
      if (w.text[i] === '=' && (!w.marks || w.marks[i] === 'u')) return { name: [0, w.text[i - 1] === '+' ? i - 1 : i], value: i + 1 };
    }
    return { name: [0, w.text.length], value: null };
  };
  for (const s of segments) {
    for (const a of s.arith) if (ARITH_ASSIGNED_EXPANSION.test(a)) return { verb: '(( ))', raw: a.trim() };
    const cmd = commandOf(s.words);
    if (!cmd || cmd.unknown || cmd.opaque || 'script' in cmd || !NAME_OPERAND_COMMANDS.has(cmd.name)) continue;
    const { name, args } = cmd;
    const hit = (w) => ({ verb: name, raw: w.raw });
    if (name === 'let') { for (const w of args) if (!w.literal && ARITH_ASSIGNED_EXPANSION.test(w.raw)) return hit(w); continue; }
    if (name === 'printf') {   // `-v NAME`, glued or the next word, is printf's one name operand
      for (let k = 0; k < args.length; k++) {
        const t = args[k].text;
        if (t === '--' || !t.startsWith('-') || t.length < 2) break;
        if (!args[k].literal) return hit(args[k]);
        const v = t.indexOf('v');
        if (v > 0) { const nm = v < t.length - 1 ? sliceWord(args[k], v + 1) : args[k + 1]; if (carries(nm)) return hit(nm); break; }
      }
      continue;
    }
    if (name === 'read' || name === 'mapfile' || name === 'readarray') {
      const valued = name === 'read' ? 'dinNptu' : 'dnOsuCc';   // options whose value is not a name (bash's read and mapfile)
      for (let k = 0; k < args.length; k++) {
        const w = args[k];
        const t = w.text;
        if (t === '--') { for (const n of args.slice(k + 1)) if (carries(n)) return hit(n); break; }
        if (t.startsWith('-') && t.length > 1) {
          if (!w.literal) return hit(w);   // an option the shell fills in may be a name
          for (let j = 1; j < t.length; j++) {
            const ch = t[j];
            if (name === 'read' && (ch === 'a' || ch === 'A')) { const nm = j < t.length - 1 ? sliceWord(w, j + 1) : args[++k]; if (carries(nm)) return hit(nm); break; }   // the array NAME
            if (valued.includes(ch)) { if (j === t.length - 1) k++; break; }
            if (name === 'read' && ch === 'k' && j === t.length - 1 && args[k + 1] && /^\d+$/.test(args[k + 1].text)) { k++; break; }   // zsh's -k [num]
          }
          continue;
        }
        if (carries(w)) return hit(w);
      }
      continue;
    }
    if (name === 'getopts') {   // getopts OPTSTRING NAME [ARGS...]: the second operand is the name
      const ops = args.filter((w) => !(w.text.startsWith('-') && w.text.length > 1));
      if (ops[1] && carries(ops[1])) return hit(ops[1]);
      continue;
    }
    // export, declare, typeset, local, readonly, unset: NAME[=VALUE] operands after the options; with a nameref option
    // (`declare -n`, `typeset -n`, `local -n`) the VALUE is a name too
    const nameref = name !== 'export' && name !== 'readonly' && name !== 'unset' && args.some((w) => w.literal && /^-[A-Za-z]*n/.test(w.text));
    for (const w of args) {
      const t = w.text;
      if (t === '--') continue;
      if (/^[-+]/.test(t) && t.length > 1) { if (!w.literal) return hit(w); continue; }
      const { name: [a, b], value } = nameOf(w);
      if (carries(w, a, b)) return hit(w);
      if (nameref && value != null && carries(w, value)) return hit(w);
    }
  }
  return null;
}
// Why `~` and `$HOME` are unreadable in this command, or null: rule (a)'s bare identifier, or M1's assembled name. The text
// is the reason clause the refusal and the unknown-directory message carry.
function homeUnreadableWhy(segments) {
  return unreadableExpandedNames(segments).get('HOME') || null;
}
// Every expanded name (EXPANDED_NAMES) the command may reassign, each with the reason clause the refusal carries: rule
// (a)'s bare identifier for that name, or M1's assembled name (which may be any of them). valueOf reads none of these
// (B2 as ruled, 2026-09-19: B2's first draft held back HOME alone, and a `PWD=` or `OLDPWD=` in the command was resolved
// through the guard's own directory model, a live overwrite the fifth pass's attacker found).
// `homeWrites` (the seventh pass's addendum, item 1) holds the indices of the segments whose HOME mentions are the one
// readable write, a plain top-level `HOME=<path>`; those words are not a bare mention. A `HOME=<path>` as a prefix on a
// command is, with its own reason (kind 'homePrefix'), since the shells expand that command's `$HOME` and `~` before the
// prefix applies and run the command under the new HOME.
function unreadableExpandedNames(segments, homeWrites = new Set()) {
  const bare = bareExpandedNames(segments.map((s, idx) => (homeWrites.has(idx) ? { words: [], redirects: s.redirects, arith: s.arith } : s)));
  const a = bare.size === EXPANDED_NAMES.length ? null : assembledNameOperand(segments);
  const out = new Map();
  for (const name of EXPANDED_NAMES) {
    if (bare.has(name)) {
      let prefix = null;
      if (name === 'HOME') for (const s of segments) { const h = rawHeadIndexOf(s.words); const k = s.words.findIndex((x) => /^HOME=/.test(x.raw)); if (h > 0 && k >= 0 && k < h) { prefix = s.words[k]; break; } }
      if (prefix) out.set(name, { kind: 'homePrefix', name, text: `the command sets HOME as a prefix on a command (${prefix.raw} ...), which bash, zsh and dash apply after expanding that command's own \`$HOME\` and \`~\` and which the command then runs under, so a write through HOME there may name either home` });
      else out.set(name, { kind: 'bare', name, text: `the command names ${name} outside an expansion${name === 'HOME' ? ' in a form other than a plain `HOME=<path>` assignment of its own' : ''} (an assignment, a declaration, a nameref, a read or an argument that could reassign it)` });
    } else if (a) out.set(name, { kind: 'assembled', name, text: `the command's \`${a.verb}\` takes a variable name the shell fills in when it runs (${a.raw}), and a name I cannot read may be ${name}` });
  }
  return out;
}
// B2 (the fifth pass's second commit, 2026-09-19, the reviewer's ruling with its condition): a literal head outside every
// project bounds nothing once an opaque expansion follows it, since a `..` inside the value escapes any prefix (the fourth
// pass's matrix: `x='../sub-on/p$abc'; printf poison > <out>/$x/rep.md` from a cwd in no project overwrote the tracked
// note, since class E asked only whether the head parents or sits under a root). So the guard RESOLVES every expansion
// whose value it can read and judges the real path; what stays opaque keeps the verdict the working directory gives it
// (the reviewer's option (c), 2026-09-19: refused as not literal from a tracked cwd, dropped from a cwd in no project;
// the header states the principle and the residual with its boundary). PWD is read through the directory the guard
// knows; OLDPWD, `~+` and `~-` through the directory before a `cd` in the same command; HOME through the guard's own home,
// or through the one plain `HOME=<path>` write below; none of the three once the command names the name outside an
// expansion in any other form or may fill it in (rule (a) and M1: valueOf reads no name on EXPANDED_NAMES that
// unreadableExpandedNames returns). A value that is empty or holds a space, a glob character or an expansion of its own
// is not read (the shell would split or match it). A `$(...)`, a backtick and a `${name:-x}` stay opaque.
//
// THE READABILITY RULE (the sixth pass's attacker, 2026-09-19: 77 in-model live overwrites in 13 spelling classes, each a
// value the command SPELLS that this half resolved to a string the shell does not produce; the reviewer's framing: this is
// B2's own unknown-defaults-to-unreadable doctrine, already applied to a `read` and a loop variable, applied to
// assignment). A name is readable only when every write to it in the command is a plain top-level `NAME=plain-string`
// the shell performs as spelled: a word of a segment holding assignment words alone, in plain sequence (no if, loop,
// case, subshell or function body, no `{ }` group that is piped or backgrounded or that was OPENED after `&&`, `||` or `|`
// or behind `time`, not after `&&`, `||` or `|`, not piped
// or backgrounded itself, no wrapper before it), the words of that segment read left to right as the shells perform them,
// the value literal, non-empty, without whitespace or a glob character, and without a tilde the shell would expand (an
// unquoted `~` opening the value or following a `:`, which bash, zsh and dash all expand there: `~/` and `~` resolve
// through HOME, `~+` and `~-` through PWD and OLDPWD, when those are readable, and `~user` never); of the declarations only
// `export NAME=plain-string` and `readonly NAME=plain-string` count as that write, and only with no option word (a `--`
// before the operands aside): they are the two every shell performs, while `declare`, `typeset` and `local` are no commands
// of dash (`x=docs/report.md; declare x=scratch/keep.md; cp base/report.md $x` wrote the tracked file in dash, measured
// 2026-09-20, while bash and zsh assigned) and an option word on `export` or `readonly` is one bash rejects, assigning nothing,
// while zsh may perform it (`export -r`, `readonly -r`, `-x`, `-g`; round 5's addendum, the freeze lens). ANY OTHER CONSTRUCT
// THAT CAN WRITE THE NAME MAKES IT UNREADABLE from that construct to the end of the
// command, and a plain write after it does not restore it (a declaration attribute persists, a nameref persists): a
// declaration flag outside the inert set (`-l`, `-u`, `-i`, `-a`, `-A`, `-n`, zsh's `-L`, `-R` and their kin), a nameref
// (`declare -n r=x` writes x through r), a subscript (`x[0]=`, `x[1,8]=`, `printf -v 'x[0]'`), `+=`, an assignment-shaped
// word in any other position (an argument of a wrapper or of any command, `let x=5`, a prefix `x=v cmd`, which dash and
// bash's POSIX mode keep for a special builtin), the bare identifier as a word or a token of a word that is not an option
// (`read x`, `printf -v x`, `unset x`, `mapfile x`, zsh's `print -v x` and `set -A x`, the target of a nameref), an
// assignment inside a `${x=..}`, `${x:=..}` or zsh `${x::=..}` expansion, the name in an arithmetic body, a `for` or
// `select` variable, a `{ }` group whose closing brace is piped or backgrounded, at any nesting (a subshell, so its
// assignments and cds, the groups inside it included, did not happen here; the seventh pass's attacker, F2), and, for every
// name at once, an eval, a source, xargs, a call of a function the command defines
// (`f() {`, `function f {` and `function f () {` alike, called by any spelling, a wrapper's name included) or a name
// operand the shell fills in (M1's construct, `export $h=...`: the resolved name is tainted when h is readable, every name
// when it is not). ONE write outside the plain form resolves, at no cost: a name made readonly in the command (`readonly
// x=..`, `readonly x`, `declare -r`, `typeset -r`) keeps its readonly value and every later write to it is skipped
// (readonlyNames), since no shell performs one (bash, zsh and dash stop the command list on a plain assignment; bash keeps
// the value and continues past a `declare`, `typeset`, `export` or `unset` of it, and so does dash where the word is no
// command of its), so the readonly value is the shell's wherever the command reaches a later word (the seventh pass's
// attacker's RO rows and a sibling found with them: `readonly x=docs/report.md; declare x=scratch/keep.md; cp base/report.md
// $x` wrote the tracked file in bash and dash while the guard adopted the later value); the freeze is read only from the
// segment's own unwrapped `readonly` with no option word, in plain sequence (round 5: a declaration behind a wrapper freezes
// nothing in the shells that run the wrapper as an external command and taints the name; round 5's addendum: neither does a
// `readonly` in a body that may not run, a subshell, a pipeline or a function body (`if false; then readonly x; fi` froze the
// guard's x while every shell performed the later write, 34 rows), nor `declare -r` or `typeset -r` (no commands of dash), nor
// a `readonly` with an option word (bash rejects `-r`, `-x`, `-g` and assigns nothing), nor `local -r` at the top level; each
// taints the name instead, the reason at `frozen` in recordSegment). The
// predicate is one predicate in five parts (plainSequence, plainValue, recordPlainWord, recordSegment, taintWord, in extract)
// and is keyed on the construct, never on a
// list of commands, so a spelling nobody listed is caught by the shape it must take: a name the command touches
// anywhere but in the one readable form is a name it may write. The scope half of the rule (no if, loop, case, select,
// subshell or function body) is decided on the segment's PARSED structure after the peel (BODY_CLOSER, peelIndex, above),
// never on its first word. The cost, measured against the corpus and the dollar
// matrix and stated in fork PR #780's body, each shell's behaviour by execution (2026-09-20, bash 5.2, zsh 5.9, dash 0.5.12): a
// `~/` value resolves through HOME at no cost; `declare -i x=5` then `$x` (bash and zsh write scratch/5, dash has no declare and
// copies onto scratch/report.md), `declare -a x=5` and `declare -A x=5` then `$x` (bash writes scratch/5; zsh rejects the scalar
// value and stops the command list, writing nothing; dash copies onto scratch/report.md), a pipeline-tail assignment (zsh keeps
// it, bash and dash do not), a `{ }` group that is piped, a `let` (bash and zsh write scratch/5; dash has no let and copies onto
// scratch/other.md), an `export x` of a name set earlier THEN written again (`x=a; export x; x=b`, where every shell holds b; the
// plain `x=a; export x` alone was refused before this rule too, as not literal, so it is a refusal whose reason the rule changed
// and not one it added) and a bare mention of the name as a word before the write each refuse from a tracked
// cwd where the value would have resolved. HOME's one readable write is a plain top-level `HOME=<path>` word of a
// segment of assignments alone (readableHomeWrites, a pre-pass; the prefix `HOME=<path> cmd` is excluded, since bash,
// zsh and dash expand cmd's `$HOME` and `~` before the prefix applies and cmd itself runs under the new HOME), read for
// the segments after it and inherited by a `$(...)` and by a script handed to a named shell (a variable that came from
// the environment stays exported when reassigned, measured in all three); any other mention of HOME outside an
// expansion leaves it unreadable for the whole command, as before, and so does an eval, a source or a call of a function
// the command defines from that point, for HOME, PWD and OLDPWD as for every name.
const RESOLVED_NAME = /^\$(?:\{([A-Za-z_][A-Za-z0-9_]*)\}|([A-Za-z_][A-Za-z0-9_]*))/;
const VAR_ASSIGNERS = new Set(['export', 'declare', 'typeset', 'readonly']);   // NAME=VALUE operands that persist in this shell at the top level
const VAR_POISONERS = new Set(['eval', 'source', '.', 'xargs']);   // after these the guard reads no assigned name
// The declaration flags that change neither the value nor what the name refers to (`-g`, `-x`, `-r`). Until round 5's
// addendum a declaration carrying only these was read as the plain write; now NO option word keeps a declaration readable
// (bash rejects `-r`, `-x` and `-g` on `export` and `readonly`, and `declare`/`typeset` are no commands of dash, recordSegment),
// so the table only picks the refusal's TEXT: a letter outside it names the flag as one that can change the value or what
// the name is (`-l` lowercases, `-u` uppercases, `-i` evaluates, `-a`/`-A` make an array, `-n` a nameref, zsh's `-L n`/`-R n`
// pad or truncate, `-Z`, `-U`, `-T`, `-t`, `-H`, `-h`, `-F`, `-E`, `-p` prints), a letter inside it names the shells'
// disagreement. Either way the name is tainted, so the gap of this list changes no verdict.
const ATTRIBUTE_ONLY_FLAGS = new Set(['g', 'x', 'r']);
const IDENTIFIER = /^[A-Za-z_][A-Za-z0-9_]*$/;
// The index of a segment's command word as spelled: the first word that is neither a reserved word nor assignment-shaped,
// before any wrapper is peeled (-1 for assignments alone). A `NAME=value` before it is a prefix assignment on the command.
function rawHeadIndexOf(words) {
  let k = 0;
  while (k < words.length && ((plainWord(words[k]) && RESERVED.has(words[k].text)) || /^[A-Za-z_][A-Za-z0-9_]*\+?=/.test(words[k].raw))) k++;   // a quoted reserved word is the command (round 5's fourth addendum)
  return k < words.length ? k : -1;
}
// The tokens of a word's text that are identifiers and came from the command's own text (not from an expansion, mark 'x',
// nor from the guard's home, mark 'h'): `r=x` yields r and x, `x[0]` yields x, `'x'` yields x.
function identifierTokens(text, marks) {
  const out = [];
  for (const m of text.matchAll(/[A-Za-z_][A-Za-z0-9_]*/g)) {
    if (marks && /[xh]/.test(marks.slice(m.index, m.index + m[0].length))) continue;
    if (/^[0-9]/.test(m[0])) continue;
    out.push(m[0]);
  }
  return out;
}
// The one readable write to HOME (the seventh pass's addendum, item 1, 2026-09-19): the indices of the segments whose every
// bare mention of HOME is a plain `HOME=<path>` word (the value literal, non-empty, without whitespace, a glob character or a
// tilde the shell would expand) in a segment of plain assignment words alone, in plain sequence, before any compound
// construct of the command (a subshell, a `{ }` group, a function, an if, loop or case; a `HOME=` after one is not read,
// the conservative side, since the walk's frames decide the rest). Such a write the shells perform as spelled, keep exported
// and expand `~` and `$HOME` in LATER commands through (measured in bash 5.2, zsh 5.9 and dash 0.5.12). The prefix form
// `HOME=<path> cmd` is not one: the shells expand cmd's own `$HOME` and `~` BEFORE the prefix applies (`HOME=/x printf '%s'
// ~/z` prints the previous home in all three) while cmd itself runs under the new HOME (a script or interpreter that expands
// `~` sees /x), so a write through HOME in that command may name either home; it stays unreadable with its own reason
// (unreadableExpandedNames, kind 'homePrefix').
// THE ONE TABLE of the compound heads that open a body which may not run, each with the reserved word that closes it
// (round 5 of the review, 2026-09-20). Round 4 found the frame push and CLOSERS each restating a SUBSET of COMPOUND_HEADS:
// `select` was in COMPOUND_HEADS and in neither, so a select body (which bash and zsh skip when stdin is at EOF) was walked
// as this shell's own plain sequence, its assignment adopted and its cd followed. The push, CLOSERS and COMPOUND_HEADS now
// READ this table, so no second list can drift. Its gap falls on the WRITE side: a head not listed opens no frame, and a
// body that may not run is read as plain sequence. `function` is a compound head too (a definition, not a run: the function
// frame in extract) and closes on its brace, so it is not in this table. Since round 5's addendum (2026-09-20, the frame
// lens) each entry also names the word that OPENS the body (`then`, `do`, `in`; the `)` of zsh's `foreach`) and whether the
// head takes a word list rather than a command list (`list`), so the walk can tell where a body begins and ends in the
// spellings that close it with a `}` or with nothing: zsh's brace bodies (`if [[ .. ]] {`, `while (( .. )) {`, `for y (..) {`,
// `case x {`, `repeat n {`), bash's brace-body `for y in ..; {` and `select ..; {` (bash and zsh skip both when the list is
// empty or stdin is at EOF), and zsh's one-command bodies (`for y (..) cmd`, `repeat n cmd`, `if (..) cmd`); each of these
// was walked as plain sequence past a body the shell skipped, its cd followed and standing for the write after it (F4, F6,
// F7). zsh's `repeat` and `foreach .. end` are heads (bash and dash have no such words: `repeat` is not found and `foreach y
// (a)` is a syntax error, so a frame there costs nothing); compoundBody in extract reads the table. Round 5's second addendum
// (2026-09-20, the round's verifier): a brace body written on one line, its `}` sharing a segment with the body's last command
// (`if (( 0 )) { cd ../scratch }; cp ../base/report.md report.md` from docs/, zsh alone), closed its frame at the brace BEFORE
// that command was read, so the skipped cd was followed and the write resolved to scratch/ while zsh wrote docs/report.md;
// since the third addendum the lexer cuts the segment before such a brace (splitAtClosers), so every head of this table, the
// function frame and the group scan read the one-line form as its `;` twin. The `list` flag also tells compoundBody which heads
// take a condition list, where a `{` first after the head is a condition group (`while { cond } { body }`) and not the body.
const BODY_CLOSER = {
  if: { opener: 'then', closer: 'fi' }, while: { opener: 'do', closer: 'done' }, until: { opener: 'do', closer: 'done' },
  for: { opener: 'do', closer: 'done', list: true }, case: { opener: 'in', closer: 'esac', list: true }, select: { opener: 'do', closer: 'done', list: true },
  repeat: { opener: 'do', closer: 'done', list: true }, foreach: { opener: ')', closer: 'end', list: true },
};
const CLOSERS = {};   // closer -> the heads it closes, derived from BODY_CLOSER: fi -> [if], done -> [while, until, for, select, repeat], esac -> [case], end -> [foreach]
for (const [head, { closer }] of Object.entries(BODY_CLOSER)) (CLOSERS[closer] = CLOSERS[closer] || []).push(head);
const COMPOUND_HEADS = new Set([...Object.keys(BODY_CLOSER), 'function']);
// THE FRAME'S PEEL (round 5, 2026-09-20). The frame decision (a body that may not run: its names unreadable, its cd made
// unknown at the closer) was keyed on the segment's FIRST word, so anything the shell reads past before the reserved word hid
// the head and no frame opened: a leading `!`, `time`, `{`, and `select` (round 4: six of its seven highs were this one
// defect, each a live overwrite in bash, zsh or dash, and the wrapped `cd` spelling walked around round 3's unknown-directory
// refusal by being confidently wrong instead of unknown). The head is the first word that remains after peeling, in order,
// everything the shell itself reads past before it reads a reserved word: the pipeline negation `!` (a run of them: bash takes
// `! ! cmd`), the `time` keyword and its `-p` and `--` (bash takes `time -p -- cmd`; zsh and dash reject the options, so a frame
// there refuses a line no shell runs), the group braces `{` and `}` (the brace scan in extract opens and closes their frames,
// re-peeling between them, so `! { ! { x=1; }; } | cat` opens both), the body openers `then`, `do`, `else` and `elif`, after
// which a compound head opens a NESTED body whose closer must close the inner frame and not the outer (`if false; then if true;
// then :; fi; x=1; fi` adopted x at round 4's head: the inner `fi` closed the outer frame), the wrapper words in PREFIXES
// (`command`, `builtin`, `exec`, zsh's modifiers, the external wrappers) and assignment-prefix words; each unquoted, as a
// reserved word must be. Measured 2026-09-20 in bash 5.2, zsh 5.9 and dash 0.5.12: bash runs the compound behind `!`, `! !`,
// `time`, `time -p`, `time --` and `{`; zsh behind `!`, `time` and `{`; dash behind `!` and `{`; behind a wrapper or an
// assignment word every shell stops on the `then` or `do` with a syntax error and runs nothing, so a frame there costs
// nothing. A redirection is not a word to the lexer (zsh alone accepts one before a compound command), so it never hides a
// head. Two reserved words are read in extract rather than peeled (round 5's addendum): `coproc` (bash and zsh), whose command
// runs in a coprocess, a subshell of its own, so the words after it are read inside a frame that keeps no name and restores
// the directory; and zsh's `always`, which continues a `{ }` group into its always-list. PEEL FOR THE FRAME, NOT FOR THE
// FREEZE: recordSegment's readonly skip decides the opposite way and requires the declaration to be the segment's own
// unwrapped `readonly` in plain sequence; the reason both decisions hold is written there, beside `frozen`.
const FRAME_PEEL = new Set(['!', 'time', 'then', 'do', 'else', 'elif', ...PREFIXES]);   // the braces are peeled by peelIndex's callers, which open and close their frames
const TIME_OPTIONS = new Set(['-p', '--']);
const plainWord = (w) => !!(w && w.literal && (!w.marks || w.marks[0] === 'u'));   // unquoted and literal, as a reserved word must be
// The index of the first word from `from` that the shell would read as a reserved word or a command name: past the peel
// words, a `time`'s options, assignment-shaped words and, when `braces` is set, the group braces (words.length when nothing
// remains). With `wrappers` off the wrapper words of PREFIXES are not peeled: before a `(` the word is the function's NAME
// (`env() { x=..; }` defines a function called env, the sixth pass's C6b), so the name peel reads past `!`, `time` and the
// braces alone.
function peelIndex(words, from = 0, braces = true, wrappers = true) {
  let k = from;
  let afterTime = false;
  while (k < words.length) {
    const w = words[k];
    if (plainWord(w) && afterTime && TIME_OPTIONS.has(w.text)) { k++; continue; }
    afterTime = false;
    if (plainWord(w) && ((FRAME_PEEL.has(w.text) && (wrappers || !PREFIXES.has(w.text) || w.text === 'time')) || (braces && (w.text === '{' || w.text === '}')))) { afterTime = w.text === 'time'; k++; continue; }
    if (isAssignmentWord(w)) { k++; continue; }
    break;
  }
  return k;
}
// The segment's compound head: the text of the word at peelIndex when it is a plain word, else null.
const compoundHeadOf = (words, from = 0) => { const w = words[peelIndex(words, from)]; return plainWord(w) ? w.text : null; };
function readableHomeWrites(segments) {
  const out = new Set();
  let opened = false;
  for (let idx = 0; idx < segments.length; idx++) {
    const seg = segments[idx];
    if (seg.paren) { opened = true; continue; }
    if (seg.op === '(' || seg.words.some((w) => w.text === '{' || w.text === '}') || COMPOUND_HEADS.has(compoundHeadOf(seg.words))) opened = true;   // the head after the peel (round 5)
    if (opened || !seg.words.length || !seg.words.every(isAssignmentWord)) continue;
    const prevOp = idx > 0 ? segments[idx - 1].op : '';
    if (prevOp === '&&' || prevOp === '||' || prevOp === '|' || seg.op === '|' || seg.op === '&') continue;
    let found = false;
    let ok = true;
    for (const w of seg.words) {
      if (!bareExpandedNames([{ words: [w], redirects: [], arith: [] }]).has('HOME')) continue;
      if (!/^HOME=/.test(w.raw)) { ok = false; break; }
      const v = w.text.slice(5);
      const tilde = (w.marks[5] === 'u' && v[0] === '~') || [...v.matchAll(/:~/g)].some((m) => w.marks[5 + m.index + 1] === 'u');
      if (!w.literal || w.glob || !v || /[\s\0*?[]/.test(v) || tilde) { ok = false; break; }
      found = true;
    }
    if (ok && found && !bareExpandedNames([{ words: [], redirects: seg.redirects, arith: seg.arith }]).has('HOME')) out.add(idx);
  }
  return out;
}
// What the shell's own cd does under each wrapper that is not an external command (the seventh pass's addendum, item 2,
// measured 2026-09-19 in bash 5.2, zsh 5.9 and dash 0.5.12): the dollar matrix's rows 2874 and 2875 (`builtin cd`, `command
// cd`) were refused with a text saying the shell does not move, while bash and zsh (builtin) and bash and dash (command) DO
// move. The verdict stays unknown, since which shell runs the line is not known; the text says what each shell does. A
// wrapper not in this table runs an external `cd`, which moves nothing in any shell.
const WRAPPED_CD_WHY = {
  builtin: 'runs the shell\'s own cd in bash and zsh, which moves the shell, and no command in dash, which has no `builtin` and stays',
  command: 'runs the shell\'s own cd in bash and dash, which moves the shell, and an external cd in zsh, which moves nothing',
  time: 'is a reserved word in bash and zsh, so the cd runs in this shell and moves it, and an external command in dash, where the cd moves nothing',
  // zsh's precommand modifiers (the seventh pass's attacker, F1): `noglob cd docs` moves zsh, bash and dash fail on the word
  noglob: 'is a zsh precommand modifier, so in zsh the shell\'s own cd runs and moves it, and no command in bash and dash, which stay',
  nocorrect: 'is a zsh precommand modifier, so in zsh the shell\'s own cd runs and moves it, and no command in bash and dash, which stay',
  '-': 'is a zsh precommand modifier, so in zsh the shell\'s own cd runs and moves it, and no command in bash and dash, which stay',
};
// Whether every expansion left in `text` is the process id (for the numeric flag of a partly resolved word).
function numericRunsOnly(text, marks) {
  for (let i = 0; i < text.length;) {
    if (marks[i] !== 'x') { i++; continue; }
    let j = i;
    while (j < text.length && marks[j] === 'x') j++;
    if (!NUMERIC_EXPANSIONS.includes(text.slice(i, j))) return false;
    i = j;
  }
  return true;
}
export function extractWriteTargets(command, cwd, shell = null) {
  return extract(command, { dir: cwd || null, unknownDir: !cwd, unknownWhy: cwd ? null : 'no working directory is known for it', shell, depth: 0 });
}
function extract(command, ctx) {
  const { shell, depth } = ctx;
  const prevLinks = activeLinks;
  const { segments, opaque } = lex(command, shell);
  const targets = [];
  const unresolved = [];
  let dir = ctx.dir;
  let unknownDir = ctx.unknownDir;
  let unknownWhy = ctx.unknownWhy;   // for the refusal: which construct made the directory unknown (round 3)
  let keywordMode = !!ctx.keywordMode;   // bash's `set -k` is on from an earlier segment (setsKeywordMode)
  // B2: the names this command set to a plain string (name -> value; null for a name a write the readability rule does not
  // follow touched, which stays null: a later plain write does not restore it), why each such name is unreadable (for the
  // refusal), the directory before the last `cd` (OLDPWD), and whether an eval, a source, a function call or a name operand
  // the shell fills in has run since (then no name is read, and poisonWhy says which construct)
  const vars = ctx.vars || new Map();
  const unreadableWhy = ctx.unreadableWhy || new Map();
  let oldDir = ctx.oldDir === undefined ? null : ctx.oldDir;
  let varsPoisoned = !!ctx.varsPoisoned;
  let poisonWhy = ctx.poisonWhy || null;
  const definedFunctions = ctx.definedFunctions || new Set();
  // The readability rule's two marks: a name a construct outside the plain form may write (sticky), and the whole table
  // once a construct may write any name. The text names the construct, so the refusal can say why the name was not read.
  const wroteThrough = (name, construct, raw) => `the command writes \`${name}\` through ${construct} (${raw}), which I do not follow`;
  const taint = (name, why) => {
    if (!name || !IDENTIFIER.test(name)) return;
    if (vars.has(name) && vars.get(name) === null) return;
    vars.set(name, null);
    if (why && !unreadableWhy.has(name)) unreadableWhy.set(name, why);
  };
  const poison = (why) => { if (!varsPoisoned) { varsPoisoned = true; poisonWhy = why; } };
  // the readable writes to HOME in this command (the seventh pass's addendum, item 1), decided before the walk
  const homeWrites = readableHomeWrites(segments);
  const setUnknown = (why) => { unknownDir = true; if (!unknownWhy) unknownWhy = why; };
  const setKnown = (d) => { dir = d; unknownDir = false; unknownWhy = null; };
  // B2: a `cd` or `pushd` sets OLDPWD to the directory it left, when the guard knew it; a move it cannot follow leaves
  // OLDPWD unknown
  const moveTo = (d) => { oldDir = unknownDir ? null : dir; setKnown(d); };
  const moveUnknown = (why) => { oldDir = null; setUnknown(why); };
  // Class D (2026-09-19): a leading `~/`, `$HOME/` or `${HOME}/` expands through os.homedir(), but a
  // command can reassign HOME before the write (`HOME=notes; > $HOME/seed.md` from a tracked project put
  // the write in a tracked folder while the guard read the real home). Since the third pass (rule (a)) the
  // trigger is the bare identifier HOME anywhere in the command outside an expansion (bareExpandedNames),
  // not a list of assignment forms; when it appears, the home the guard read may not be the one the shell
  // uses, so a word that expanded it (marked 'h') is a target the hook cannot read, and a `cd` to such a
  // word, or a bare `cd`, leaves the directory unknown, for the whole command.
  // the expanded names this command may reassign (rule (a), M1; B2 as ruled: PWD and OLDPWD beside HOME), the
  // parent's marks inherited by a `$(...)` and a script, its own added
  const unreadableNames = new Map(ctx.unreadableNames || []);
  for (const [k, v] of unreadableExpandedNames(segments, homeWrites)) if (!unreadableNames.has(k)) unreadableNames.set(k, v);
  const homeWhy = ctx.homeWhy || unreadableNames.get('HOME') || null;
  const homeAssigned = ctx.homeAssigned || !!homeWhy;   // HOME unreadable for the whole command: a mention outside an expansion in any form but the plain write, or a name the shell fills in
  // HOME unreadable NOW: for the whole command as above, or from an eval, a source, a call of a function the command defines
  // or a name operand the shell fills in on (the readability rule: such a construct may write any name, HOME included; before
  // it, `e=$(printf 'HO%s' ME=<notes>); eval "$e"; printf poison > ~/n1.md` resolved `~` through the guard's home and bash,
  // zsh and dash wrote the tracked note)
  const homeUnreadableNow = () => homeAssigned || varsPoisoned;
  const homeWhyNow = () => homeWhy || (varsPoisoned && poisonWhy ? { kind: 'poisoned', name: 'HOME', text: poisonWhy } : null);
  const homeWord = (w) => !!(homeUnreadableNow() && w && w.marks && w.marks.includes('h'));
  // B2: the plain-string value of `name` as the shell will expand it, or null when the guard cannot read it. An expanded
  // name the command names outside an expansion, or may fill in (M1), is not read (PWD and OLDPWD as HOME; B2's first
  // draft read the guard's own directory for `$PWD` while `PWD=<dir>; cp x $PWD/docs/report.md` wrote a tracked file);
  // no name is read once the table is poisoned (the readability rule), HOME, PWD and OLDPWD included.
  const valueOf = (name) => {
    if (varsPoisoned) return null;
    if (name === 'HOME') return homeAssigned ? null : (vars.has('HOME') && vars.get('HOME') != null ? vars.get('HOME') : os.homedir());
    if (name === 'PWD') return unknownDir || unreadableNames.has('PWD') ? null : dir;
    if (name === 'OLDPWD') return unreadableNames.has('OLDPWD') ? null : oldDir;
    if (!vars.has(name)) return null;
    return vars.get(name);
  };
  // B2: a word with the expansions the guard can read replaced by their values (quoted text, since a value with a
  // space or a glob character is not read), the rest left as they stand; the word's raw spelling is kept for the refusal.
  // The lexer's home text (mark 'h', a leading `~/` or `$HOME/` expanded through the guard's own home) is replaced by the
  // value a plain `HOME=<path>` earlier in the command set, when HOME is readable (the seventh pass's addendum, item 1).
  const resolveWord = (w) => {
    if (!w || !w.marks) return w;
    const homeSet = w.marks.includes('h') && !homeUnreadableNow() && vars.has('HOME') && vars.get('HOME') != null;
    if ((w.literal || !w.marks.includes('x')) && !homeSet) return w;
    const T = w.text;
    const M = w.marks;
    let text = '';
    let marks = '';
    let changed = false;
    let named = null;   // the first expanded name left opaque because the command names or may fill it in, or a construct wrote it (the refusal says so)
    const unread = (name) => {
      if (named) return null;
      if (unreadableNames.has(name)) named = { ...unreadableNames.get(name), kind: 'namedExpansion' };
      else if (unreadableWhy.has(name)) named = { kind: 'namedExpansion', name, text: unreadableWhy.get(name) };
      else if (varsPoisoned && poisonWhy) named = { kind: 'namedExpansion', name, text: poisonWhy };
      return null;
    };
    for (let i = 0; i < T.length;) {
      if (M[i] === 'h' && homeSet) {   // the guard's home text stands for HOME, which the command set to a plain string earlier
        let j = i;
        while (j < T.length && M[j] === 'h') j++;
        const v = vars.get('HOME');
        text += v;
        marks += 'q'.repeat(v.length);
        changed = true;
        i = j;
        continue;
      }
      if (M[i] !== 'x') { text += T[i]; marks += M[i]; i++; continue; }
      let j = i;
      while (j < T.length && M[j] === 'x') j++;
      const run = T.slice(i, j);
      let value = '';
      let ok = true;
      let end = j;
      for (let k = 0; k < run.length && ok;) {
        const m = run.slice(k).match(RESOLVED_NAME);
        if (m) {
          const v = valueOf(m[1] || m[2]);
          if (v == null) { unread(m[1] || m[2]); ok = false; break; }
          value += v;
          k += m[0].length;
          continue;
        }
        // `~+` and `~-`: the tilde stands as one expansion and the sign follows it as text
        if (run[k] === '~' && k === run.length - 1 && end < T.length && M[end] === 'u' && (T[end] === '+' || T[end] === '-')) {
          const v = valueOf(T[end] === '+' ? 'PWD' : 'OLDPWD');
          if (v == null) { unread(T[end] === '+' ? 'PWD' : 'OLDPWD'); ok = false; break; }
          value += v;
          k++;
          end++;
          continue;
        }
        ok = false;
      }
      if (!ok || value === '' || /[\s*?[\0]/.test(value)) { text += T.slice(i, j); marks += M.slice(i, j); i = j; continue; }
      text += value;
      marks += 'q'.repeat(value.length);
      changed = true;
      i = end;
    }
    if (!changed) return named ? { ...w, why: named } : w;
    const hasX = marks.includes('x') || text.includes('\0');
    const g = !hasX && hasGlobChar(text, marks);
    return word(text, !hasX && !g, w.raw, { glob: g, marks, at: w.at, numeric: hasX && numericRunsOnly(text, marks) && !hasGlobChar(text, marks), why: named });
  };
  // THE PREDICATE of the readability rule (the statement is at RESOLVED_NAME). Three parts share it, each run once a segment's
  // own words have been judged (an assignment takes effect for LATER segments; a prefix assignment expands the old value in
  // its own command): plainSequence says whether a segment's assignments are this shell's own, in order; recordPlainWord
  // reads the one form the rule reads, one word at a time as the shells perform them (the caller resolves each word with
  // the names the words before it set, C5d); recordSegment reads every other segment as writes the rule does not follow,
  // keyed on the SHAPE of each word and never on a list of commands, so a construct nobody listed is caught by the shape it
  // must take to name the variable.
  const plainSequence = (seg, idx) => {
    const prevOp = idx > 0 ? segments[idx - 1].op : '';
    if (!frames.every((f) => f.kind === 'group')) return { ok: false, why: 'an if, loop, case or function body, or a subshell' };   // a plain `{ }` group runs in this shell (one opened after `&&`, `||` or `|`, or behind `time`, is not plain: below); its closing brace settles a piped or backgrounded one
    // round 5's addendum (F1, F9): a group opened after `&&`, `||` or `|` is skipped, or run in a subshell, whole, whatever line
    // its body sits on; a group behind `time` loses an assignment made alone in it in zsh (`x=a; time { x=b; }` leaves a)
    const cond = frames.find((f) => f.conditional);
    if (cond) return { ok: false, why: cond.conditional === '|' ? 'a `{ }` group opened after `|`, a pipeline member bash and dash run in a subshell (zsh keeps the last in this shell)' : `a \`{ }\` group opened after \`${cond.conditional}\`, which may not run` };
    if (frames.some((f) => f.timed)) return { ok: false, why: 'a `{ }` group behind `time`, whose assignment zsh does not keep when it stands alone in the group' };
    if (seg.alwaysHead) return { ok: false, why: 'the first command of an always-list on the line of its `always`, which zsh runs and bash and dash read as operands of the command before `always`' };   // round 5's third addendum, the matrix's row
    if (prevOp === '&&' || prevOp === '||') return { ok: false, why: `a command after \`${prevOp}\`, which may not run` };
    if (prevOp === '|' || seg.op === '|') return { ok: false, why: 'a pipeline, whose members bash and dash run in a subshell (zsh keeps the last in this shell)' };
    if (seg.op === '&') return { ok: false, why: 'a backgrounded command, which runs in a subshell' };
    return { ok: true, why: null };
  };
  // The value of a plain assignment word as the shell stores it: the text after `=`, with a tilde the shell expands there
  // resolved (`~/` and `~` through HOME, `~+` through PWD, `~-` through OLDPWD, when readable); null with the reason when the
  // value is not a plain string (empty, split, matched or filled in by the shell, a `~user`, a tilde after a `:`, which bash,
  // zsh and dash all expand in an assignment, or a tilde through a name the guard cannot read). The lexer expands `~` at a
  // word's start alone, so inside a value it is text (mark 'u') and is read here (C1: `x=~/../notes-api/docs/report.md; cp
  // base/report.md $x` was read as a path under the cwd while all three shells wrote through the home).
  const plainValue = (w, eq) => {
    const v = w.text.slice(eq + 1);
    if (!w.literal || w.glob || v === '' || /[\s\0*?[]/.test(v)) return { value: null, why: 'a value that is empty, or that the shell would split, match or fill in' };
    const marksV = w.marks ? w.marks.slice(eq + 1) : 'u'.repeat(v.length);
    if (marksV[0] === 'u' && v[0] === '~') {
      const m = v.match(/^~([+-]?)(?=\/|$)/);
      if (!m) return { value: null, why: 'a value that begins with `~user`, a directory the shell looks up and I do not read' };
      const home = valueOf(m[1] === '+' ? 'PWD' : m[1] === '-' ? 'OLDPWD' : 'HOME');
      if (home == null) return { value: null, why: `a value that begins with \`~${m[1]}\`, which I cannot read here` };
      return { value: home + v.slice(m[0].length), why: null };
    }
    for (const m of v.matchAll(/:~/g)) if (marksV[m.index + 1] === 'u') return { value: null, why: 'a value with a tilde after a colon, which bash, zsh and dash expand' };
    return { value: v, why: null };
  };
  // the innermost open `{ }` group notes a name written inside it (a plain word or a declaration's operand), so its closing
  // brace, or an enclosing group's, can taint the name when the group turns out to have run in a subshell (F2: `{ declare
  // x=scratch/keep.md; } | cat` kept x readable because the declaration branch noted nothing)
  const noteGroupName = (name) => { const g = frames.length && frames[frames.length - 1].kind === 'group' ? frames[frames.length - 1] : null; if (g) g.names.add(name); };
  // the readable form: a word of a segment holding assignment words alone (commandOf gave null), resolved by the caller
  const recordPlainWord = (w, seg, idx, seq) => {
    const m = w.raw.match(/^([A-Za-z_][A-Za-z0-9_]*)(\+?=)/);
    if (!m) return;   // a reserved word (`{`, `}`, `then`, `!`)
    const name = m[1];
    noteGroupName(name);   // the closing brace of a piped or backgrounded group taints them (a subshell), at any nesting (F2)
    if (name === 'HOME') {   // read as the pre-pass decided (readableHomeWrites); any other mention made HOME unreadable for the whole command
      if (homeAssigned || !homeWrites.has(idx) || !seq.ok) return;
      const { value } = plainValue(w, m[0].length - 1);
      if (value != null) vars.set('HOME', value);
      return;
    }
    if (EXPANDED_NAMES.includes(name)) return;   // PWD and OLDPWD: the mention made them unreadable for the whole command (rule (a)); the directory model is not overridden
    if (readonlyNames.has(name)) return;   // a readonly name keeps its value: the shells refuse the write (readonlyNames)
    if (m[2] === '+=') { taint(name, wroteThrough(name, '`+=`, an append', w.raw)); return; }
    if (!seq.ok) { taint(name, wroteThrough(name, seq.why, w.raw)); return; }
    const { value, why } = plainValue(w, m[0].length - 1);
    if (value == null) { taint(name, wroteThrough(name, why, w.raw)); return; }
    if (vars.has(name) && vars.get(name) === null) return;   // a write the rule did not follow touched it earlier: it stays unreadable
    vars.set(name, value);
  };
  const rawHeadIndex = rawHeadIndexOf;
  const rawHeadOf = (words) => { const k = rawHeadIndex(words); return k < 0 ? null : words[k].text; };
  // the names a nameref points at: `unset` does not free them (bash writes x through r after `declare -n r=x; unset x`, measured)
  const refTargets = ctx.refTargets || new Set();
  // The names made readonly in this command (`readonly x=..`, `readonly x`, `declare -r`, `typeset -r`; the seventh pass's
  // attacker, RO, and a sibling found with it): no shell performs a later write to one, so the name KEEPS its readonly value
  // and every later write is skipped (the one case where a write the rule does not read resolves, at no cost: the shell's
  // value is the readonly one wherever the command reaches a later word). Measured 2026-09-19: on a plain `x=..` bash, zsh
  // and dash stop the command list (nothing after it runs); on a `declare x=..`, `typeset x=..`, `export x=..` or `unset x`
  // bash prints the error, KEEPS the readonly value and continues, and so does dash where the word is no command of its
  // (`declare`, `typeset`), so `readonly x=docs/report.md; declare x=scratch/keep.md; cp base/report.md $x` wrote the tracked
  // file in both while the guard, which adopted the later value, read scratch/keep.md and allowed (from a cwd in no project
  // too, where a taint would have left the word the ruled residual). A `+r` (zsh can drop the attribute) is a flag outside the
  // inert set and taints the name as before.
  const readonlyNames = ctx.readonlyNames || new Set();
  // A word's writes by shape, on the word as resolved (`w`, so `export $h=v` with h readable taints the name h holds) and as
  // spelled (`pre`, so a value's text is not read as a mention): (i) an lvalue shape at any position, the head included
  // (`x[0]=v` is a command to the lexer), with a name the shell fills in before the `=` poisoning every name; (ii) the bare
  // identifier as a whole word or a token of a word that is not an option, in the command's own text (`read x`, `printf -v
  // x`, zsh's `print -v x`, `declare -n r=x`'s target, `let "x = 5"`); (iii) an assignment inside a `${x=..}`, `${x:=..}`
  // or zsh `${x::=..}` expansion.
  const taintWord = (w, pre, k, headIdx, cmd) => {
    if (!w || !w.text) return;
    const T = w.text;
    const M = w.marks || 'u'.repeat(T.length);
    const headName = cmd && cmd.name ? cmd.name : cmd && cmd.wrapped ? cmd.wrappers[cmd.wrappers.length - 1] : (headIdx >= 0 ? seg0(headIdx) : null);
    // a name the shell fills in before an `=` (`export $(echo x)=v`, `declare $h=v` with h opaque; M1's construct, C4): the
    // name part came from an expansion (mark 'x', or the NUL a substitution stands as), so it may be any name
    const eq = T.indexOf('=');
    const namePart = eq > 0 ? T.slice(0, eq) : '';
    const insideBraces = (namePart.match(/\{/g) || []).length > (namePart.match(/\}/g) || []).length;   // the `=` of a `${x:=..}` sits inside the expansion: rule (iii) below reads it
    if (namePart && !insideBraces && !/[\s/]/.test(namePart) && (namePart.includes('\0') || /x/.test(M.slice(0, eq)))) { poison(`the command's \`${headName || 'command'}\` takes a variable name the shell fills in when it runs (${w.raw}), and a name I cannot read may be any name`); return; }
    const m = T.match(/^([A-Za-z_][A-Za-z0-9_]*)(\+?=|\[)/);
    if (m) {
      const where = m[2] === '[' ? 'a subscript' : headIdx > k ? `a prefix assignment on \`${headName}\`, which the shell keeps for that command (dash and bash's POSIX mode keep it for a special builtin)` : cmd && cmd.wrapped && !cmd.name ? `an argument of the wrapper \`${headName}\`, which the shell hands to it rather than assigning` : `an assignment-shaped word of \`${headName}\``;
      taint(m[1], wroteThrough(m[1], where, w.raw));
    }
    if (k !== headIdx && !(/^[-+]/.test(pre.text) && pre.text.length > 1)) for (const t of identifierTokens(pre.text, pre.marks)) if (!m || t !== m[1]) taint(t, wroteThrough(t, `a word of \`${headName || pre.text}\` that names it`, pre.raw));
    for (const e of pre.text.matchAll(/\$\{([A-Za-z_][A-Za-z0-9_]*)(?:\[[^\]]*\])?:*=/g)) if ((pre.marks || '')[e.index] === 'x') taint(e[1], wroteThrough(e[1], 'a `${name=..}`, `${name:=..}` or `${name::=..}` expansion, which assigns it', pre.raw));
  };
  let seg0 = () => null;   // the text of the segment's word at an index, bound per segment by recordSegment
  // an arithmetic body (`(( x = 5 ))`, `$(( x++ ))`, `let`'s cousin `for (( x=0; ... ))`) may assign any name in it
  const taintArith = (seg) => { for (const a of seg.arith) for (const t of identifierTokens(a, null)) taint(t, wroteThrough(t, 'an arithmetic body, which may assign it', `(( ${a.trim()} ))`)); };
  // every other segment (a command, a wrapper, a declaration, a loop head): each word a write the rule does not follow
  const recordSegment = (seg, idx, cmd, preWords) => {
    const seq = plainSequence(seg, idx);
    const headAt = peelIndex(seg.words);   // the compound head after the peel (round 5): `! for x in ...` names its variable too
    const head = compoundHeadOf(seg.words);
    const headIdx = rawHeadIndex(seg.words);
    seg0 = (i) => (seg.words[i] ? seg.words[i].text : null);
    // (1) a for or select loop variable
    const loopVar = seg.words[headAt + 1];
    if ((head === 'for' || head === 'select' || head === 'foreach') && loopVar && loopVar.literal) taint(loopVar.text, wroteThrough(loopVar.text, `a \`${head}\` loop variable`, loopVar.raw));
    // (2) a construct that may write ANY name: an eval, a source, xargs, a call of a function the command defines by any spelling
    // (the head as spelled, before a wrapper peel: `env() { x=..; }; env true` runs the function, C6b)
    const rawHead = rawHeadOf(seg.words);
    if (cmd && (VAR_POISONERS.has(cmd.name) || definedFunctions.has(cmd.name) || (rawHead != null && definedFunctions.has(rawHead)))) {
      poison(VAR_POISONERS.has(cmd.name) ? `an earlier \`${cmd.name}\` may assign any name` : `an earlier call of \`${definedFunctions.has(cmd.name) ? cmd.name : rawHead}\`, a function the command defines, may assign any name`);
      return;
    }
    // (2b) M1's own detector, per segment: a name operand the shell fills in on a reader or declaration (`read $h`, `printf -v
    // "$h"`, `declare -n r=$h`) may name any variable, so every name is unreadable from here (rule (a) already holds HOME, PWD
    // and OLDPWD for the whole command)
    const assembled = assembledNameOperand([seg]);
    if (assembled) poison(`the command's \`${assembled.verb}\` takes a variable name the shell fills in when it runs (${assembled.raw}), and a name I cannot read may be any name`);
    // (3) a declaration: an `export NAME=plain-string` or `readonly NAME=plain-string` with no option word, in plain sequence,
    // is the plain write (readonly freezing the name); `declare`, `typeset` and `local` (no commands of dash), any option word,
    // a nameref, a name with no value, a subscript, or a value the guard does not read, taints the name; a nameref's target too
    // (`declare -n r=x` writes x through r), or every name when the target is one the shell fills in
    const handled = new Set();
    if (cmd && (VAR_ASSIGNERS.has(cmd.name) || cmd.name === 'local')) {
      const flags = cmd.args.filter((w) => /^[-+]/.test(w.text) && w.text.length > 1);
      // an option word the shell fills in (`declare $f x=y`, `declare -$f x=y`) poisons every name through M1's per-segment
      // detector (2b) above, which reads every non-literal option word of a declaration; a second poison here was shadowed
      // by it on every row and is gone (the seventh pass's close; the sixth pass removed an unreachable poison the same way)
      const bad = flags.filter((w) => w.text !== '--' && (w.text[0] === '+' || w.text.startsWith('--') || ![...w.text.slice(1)].every((c) => ATTRIBUTE_ONLY_FLAGS.has(c))));
      const nameref = flags.some((w) => w.literal && /^-[A-Za-z]*n/.test(w.text));
      // an option word anywhere (round 5's addendum, the freeze lens RC3 and RC4): bash's `export` takes -fnp and its `readonly`
      // -aAfp, so `export -r x=v`, `readonly -x x=v` print "invalid option" and assign nothing while zsh freezes on some of them and
      // dash exits; an option after an operand (`declare x=v -r`) is an operand to bash ("not a valid identifier"), which then
      // assigns x WITHOUT the attribute; and `--` is the one option word every shell reads, before the operands alone
      const firstOperand = cmd.args.findIndex((w) => !(/^[-+]/.test(w.text) && w.text.length > 1));
      const optionAfterOperand = firstOperand >= 0 && cmd.args.slice(firstOperand).some((w) => /^[-+]/.test(w.text) && w.text.length > 1);
      const plainOptions = flags.every((w) => w.text === '--') && !optionAfterOperand;
      const portable = cmd.name === 'readonly' || cmd.name === 'export';   // POSIX special builtins, the declarations every shell performs
      // PEEL FOR THE FRAME, NOT FOR THE FREEZE (round 5 of the review, 2026-09-20). Two decisions read a word behind a wrapper
      // and pull opposite ways. The FRAME peels: the shell reads the reserved word behind a `!`, a `time` or a brace, so a
      // body there may not run and its names and cd must not be adopted (peelIndex). The FREEZE must not: `frozen` was
      // computed from the PEELED command name, so `env readonly x=scratch/keep.md; x=docs/report.md; cp base/report.md $x`
      // added x to readonlyNames, the later plain write was skipped, and the guard kept scratch/keep.md while bash, zsh and
      // dash (env runs an external `readonly` that does not exist, so nothing froze) performed the write and copied onto the
      // tracked file: the one place in the readability rule where a write the guard does not read still RESOLVES, so the one
      // place its failure is an allow. A wrapper that runs an external command cannot freeze a shell variable, and whether a
      // given word is such a wrapper depends on the shell (measured 2026-09-20: `command readonly` freezes in bash and dash and
      // runs an external command in zsh; `builtin readonly` freezes in bash and zsh and is no command in dash; `noglob readonly`
      // freezes in zsh alone; env, nice, nohup, timeout, setsid and stdbuf freeze nowhere), so a uniform peel breaks one of the
      // two. The freeze therefore applies only when it is UNAMBIGUOUS in this shell: the declaration is the segment's own
      // command, unwrapped (`!cmd.wrapped`), a `readonly` with no option word (a `--` before the operands aside) and a plain
      // NAME or NAME=plain-string operand, in plain sequence (`seq.ok`: not in an if, loop, case, select or function body, a
      // subshell, a pipeline, a backgrounded command, after `&&` or `||`, or in a group opened after one of them). Round 5's
      // addendum measured each of the other roads (the freeze lens, 54 rows, every one allowed at round 5's head while a shell
      // performed the later write onto the tracked file): a bare `readonly x` in a body that may not run, a piped or
      // backgrounded group, a subshell, a pipeline, after `&&` or `||` or in a function never called froze the guard's x and no
      // shell's (the skip ran before the scope check, RC1); `declare -r` and `typeset -r` freeze in bash and zsh and are "not
      // found" in dash, which then performs the write (RC2); `export -r`, `readonly -r`, `-x`, `-g` are options bash rejects,
      // assigning nothing (RC3); an option after the operand is an operand to bash (RC4); `local -r x` at the top level is
      // rejected by bash (RC5). A declaration of any kind reached through ANY wrapper (`env export x=..` and `command declare
      // x=..` adopted the value the same way) freezes nothing and TAINTS every name it declares, below, since which shell runs
      // the line is not known and the shells differ on whether the assignment happened: fail toward refusing; so does every
      // road above.
      const frozen = !cmd.wrapped && seq.ok && cmd.name === 'readonly' && plainOptions;   // the names become readonly (readonlyNames)
      // bash and dash reject `local` outside a function and zsh rejects `local -n` (measured 2026-09-19), so a top-level
      // `local -n r=x` writes nothing through r; r itself is tainted below, as every `local` name is (zsh performs a plain
      // `local x=v` at the top level, bash and dash do not)
      const localTop = cmd.name === 'local' && frames.every((f) => f.kind === 'group');
      for (const w of cmd.args) {
        if (/^[-+]/.test(w.text) && w.text.length > 1) { handled.add(w); continue; }
        const m = w.text.match(/^([A-Za-z_][A-Za-z0-9_]*)(\+?=|\[|$)/);
        if (!m) continue;   // a value operand (zsh's `typeset -L 17`), or a word taintWord reads
        if (/x/.test((w.marks || '').slice(0, m[1].length)) || w.text.slice(0, m[1].length).includes('\0')) continue;   // a name the shell fills in: taintWord poisons
        handled.add(w);
        const name = m[1];
        if (nameref && m[2] === '=' && !localTop) {
          const target = w.text.slice(m[0].length);
          if (w.literal && IDENTIFIER.test(target)) { refTargets.add(target); taint(target, wroteThrough(target, `a nameref (\`${cmd.name} -n\`: a write to \`${name}\` writes \`${target}\`)`, w.raw)); }
          else poison(`the command's \`${cmd.name} -n\` makes \`${name}\` a reference to a name the shell fills in (${w.raw}), which may be any name`);
        }
        if (EXPANDED_NAMES.includes(name)) continue;   // HOME, PWD, OLDPWD: unreadable for the whole command by the mention (rule (a))
        // a flag outside the inert set taints the name whether or not it is readonly (zsh drops the attribute with `typeset +r x`
        // and then performs the next write, measured), and so does a nameref declaration
        if (bad.length) { taint(name, wroteThrough(name, `a \`${cmd.name}\` flag that can change the value or what the name is (${bad.map((f) => f.text).join(' ')})`, w.raw)); continue; }
        if (nameref) { taint(name, wroteThrough(name, `a nameref (\`${cmd.name} -n\`)`, w.raw)); continue; }
        if (readonlyNames.has(name)) continue;   // a readonly name keeps its value: the shells refuse the write (readonlyNames)
        // a declaration behind a wrapper (the freeze comment above): the shells differ on whether it ran, so the name is unreadable
        if (cmd.wrapped) { taint(name, wroteThrough(name, `a \`${cmd.name}\` behind the wrapper \`${cmd.wrappers[cmd.wrappers.length - 1]}\`, which runs the shell's own ${cmd.name} in some shells and an external command that assigns nothing in others`, w.raw)); continue; }
        if (frozen) {
          readonlyNames.add(name);   // from here every later write to it is one the shells refuse
          noteGroupName(name);   // a freeze inside a `{ }` group that turns out piped or backgrounded was a subshell's: closeGroups undoes it (round 5's addendum)
          if (m[2] === '' && !(vars.has(name) && vars.get(name) === null)) continue;   // `readonly x` alone: the value it has stays the one it has
        }
        if (cmd.name === 'local') { taint(name, wroteThrough(name, 'a `local`, which zsh performs at the top level and bash and dash reject', w.raw)); continue; }
        // round 5's addendum: the declarations dash has no command for, and an option word bash rejects (RC2 to RC4 above)
        if (!portable) { taint(name, wroteThrough(name, `a \`${cmd.name}\`, which dash has no command for, so whether the shell assigned the name depends on which shell runs the line`, w.raw)); continue; }
        if (!plainOptions) { taint(name, wroteThrough(name, `an option word on \`${cmd.name}\` (${flags.map((f) => f.text).join(' ')}), which bash rejects, assigning nothing, while another shell may perform it`, w.raw)); continue; }
        if (m[2] === '[') { taint(name, wroteThrough(name, 'a subscript', w.raw)); continue; }
        if (m[2] === '+=') { taint(name, wroteThrough(name, '`+=`, an append', w.raw)); continue; }
        if (m[2] === '') { taint(name, wroteThrough(name, `a \`${cmd.name}\` of the name alone, which may change how it is read`, w.raw)); continue; }
        if (!seq.ok) { taint(name, wroteThrough(name, seq.why, w.raw)); continue; }
        const { value, why } = plainValue(w, m[0].length - 1);
        if (value == null) { taint(name, wroteThrough(name, why, w.raw)); continue; }
        if (vars.has(name) && vars.get(name) === null) continue;
        vars.set(name, value);
        noteGroupName(name);   // a declaration inside a `{ }` group that turns out piped is a subshell's write too (F2)
      }
    }
    // (3b) a plain `unset NAME` (or `unset -v NAME`) in plain sequence RESETS the name: bash, zsh and dash drop its value and
    // every attribute (`declare -l x; unset x; x=../docs/REPORT.MD` gives the spelled value, measured), so a plain write after it
    // is the readable form again; the table stays poisoned if it was, a name a nameref points at stays unreadable (bash still
    // writes it through the reference after the unset), and any other `unset` flag taints its operands
    if (cmd && cmd.name === 'unset' && seq.ok) {
      const flags = cmd.args.filter((w) => /^-/.test(w.text) && w.text.length > 1);
      const plainUnset = flags.every((w) => w.literal && (w.text === '-v' || w.text === '--'));
      for (const w of cmd.args) {
        if (/^-/.test(w.text) && w.text.length > 1) { handled.add(w); continue; }
        if (!w.literal || !IDENTIFIER.test(w.text) || EXPANDED_NAMES.includes(w.text)) continue;   // an assembled or subscripted name: taintWord reads it
        handled.add(w);
        if (readonlyNames.has(w.text)) continue;   // a readonly name is not unset: bash keeps the value and continues, zsh and dash stop
        if (plainUnset && !refTargets.has(w.text)) { vars.delete(w.text); unreadableWhy.delete(w.text); }
        else taint(w.text, wroteThrough(w.text, `an \`unset\`${refTargets.has(w.text) ? ' of a name a nameref points at' : ` with ${flags.map((f) => f.text).join(' ')}`}`, w.raw));
      }
    }
    // (4) every other word, the head included, by shape (taintWord)
    for (let k = 0; k < seg.words.length; k++) {
      if (handled.has(seg.words[k])) continue;
      taintWord(seg.words[k], preWords[k] || seg.words[k], k, headIdx, cmd);
    }
    // (5) an arithmetic body may assign any name in it
    taintArith(seg);
    // (6) the readers' name operands by RESOLVED text (a glued `-vNAME` included), beside the shape rule: the resolved text is
    // what the shell assigns (`read $h` with h set to x reads into x)
    if (cmd && (cmd.name === 'read' || cmd.name === 'mapfile' || cmd.name === 'readarray' || (cmd.name === 'unset' && !seq.ok) || cmd.name === 'getopts')) {
      for (const w of cmd.args) if (!(w.text.startsWith('-') && w.text.length > 1)) { const n = w.text.match(/^[A-Za-z_][A-Za-z0-9_]*/); if (n) taint(n[0], wroteThrough(n[0], `a name operand of \`${cmd.name}\``, w.raw)); }
    }
    if (cmd && cmd.name === 'printf') {
      const v = cmd.args.findIndex((w) => /^-[A-Za-z]*v/.test(w.text));
      if (v >= 0) {
        const t = cmd.args[v].text;
        const nm = t.length > t.indexOf('v') + 1 ? t.slice(t.indexOf('v') + 1) : (cmd.args[v + 1] && cmd.args[v + 1].text);
        const n = nm && nm.match(/^[A-Za-z_][A-Za-z0-9_]*/);
        if (n) taint(n[0], wroteThrough(n[0], 'a `printf -v`', cmd.args[v].raw));
      }
    }
  };
  const homeUnknownText = () => `${(homeWhyNow() || {}).text || 'the command names HOME outside an expansion'}, so \`~\` and \`$HOME\` name a directory I cannot read here`;
  // Class H (2026-09-19): a symlink an `ln -s` with literal operands and an untouched name makes before a later word,
  // resolved as the kernel will resolve it once it exists. `links` maps an absolute link path to the absolute path it
  // points at; foldSegments (in resolveLiteral) follows it as it folds a later literal target, so a `..` after the link
  // climbs from its target. The walk-around lens second pass (2026-09-19) settled the one true statement: an `ln -s`
  // with literal operands whose name and source no other command in the line touched is resolved; every OTHER
  // same-command path change (a hard link, `cp -l`/`cp -s`, a non-literal `ln -s`, or a name/source an earlier
  // rm/mv/ln mutated) is a family-3 mutation and refuses, since the hook cannot resolve it after the fact.
  const links = ctx.links || new Map();
  // Class 'mutated' (the walk-around lens second pass, family 3, 2026-09-19): a command earlier in the line that REMOVES, RENAMES or makes a
  // hard/symbolic LINK at a path changes what a later word under that path resolves to, so the hook's hook-time view is
  // stale and a later literal target there is unreadable. `mutated` maps an absolute prefix to the verb that touched it.
  // rm/rmdir/mv remove a path (mv also creates its destination from the source, which may alias a tracked file); ln,
  // cp -l and cp -s create a link/alias. mkdir and a plain new directory are NOT recorded: a fresh empty directory
  // hides no tracked file, and marking it would refuse the common `mkdir out && write out/x`.
  const mutated = ctx.mutated || [];
  // B1 (the fifth commit, 2026-09-19): a record that ALIASES a source (a hard `ln`, `cp -l`, `cp -s`, coreutils `link`, or
  // a symbolic link whose source the guard could not read or place, rule (c)) carries `alias` and the literal absolute
  // `source` it aliases (null when the guard cannot read it), so evaluate can ask the in-play question of where the write
  // LANDS, the source, from any cwd (aliasSourceInPlay); a remove or a rename carries neither.
  const markMutated = (abs, verb, extra = null) => { if (abs) mutated.push({ prefix: abs.replace(/\/+$/, ''), verb, alias: !!(extra && extra.alias), source: extra && extra.source ? extra.source : null }); };
  const underMutated = (abs) => mutated.find((m) => abs === m.prefix || abs.startsWith(m.prefix + '/')) || null;
  // The mutated record under a word's LITERAL directory part (the text before its first expansion, up to the last slash),
  // for a word the hook cannot read (M3, the fifth commit): a numeric or opaque target under a link the same command made
  // with a source it could not read is refused with the family-3 reason, where before the non-literal branch returned
  // first and the numeric view resolved the link's name through a filesystem where the link did not yet exist.
  const mutatedUnderLiteralPart = (w) => {
    if (!mutated.length || !w.marks) return null;
    const exp = w.marks.indexOf('x');
    const prefix = exp < 0 ? w.text : w.text.slice(0, exp);
    const cut = prefix.lastIndexOf('/');
    if (cut < 0) return null;
    const dirText = prefix.slice(0, cut) || '/';
    if (!path.isAbsolute(dirText) && unknownDir) return null;
    return underMutated(path.normalize(path.isAbsolute(dirText) ? dirText : dir + '/' + dirText));
  };
  const mutatedWhy = (m) => ({ kind: 'mutated', verb: m.verb, prefix: m.prefix, alias: m.alias, source: m.source });
  // Record the paths a remove, rename or link command touches, resolved against the current dir (the walk-around lens second pass, family 3).
  // Rule (f) (the third pass, 2026-09-19): an option the writer's table does not know leaves the operands unplaced (which
  // is the source, which the destination, which an option's value), so every literal candidate word is marked as a
  // path this command may have changed; before, the recorder returned and a later write under the moved path was read
  // against the hook-time tree.
  const recordMutations = (name, args, cwd) => {
    if (!cwd) return;
    const abs = (w) => (w && w.literal ? literalPath(w.text, cwd) : null);
    const markAllCandidates = (verb) => { for (const c of optionCandidates(args)) markMutated(abs(c), verb); };
    if (name === 'rm' || name === 'rmdir' || name === 'unlink' || name === 'shred') {
      for (const a of args) if (!(a.text.startsWith('-') && a.text.length > 1)) markMutated(abs(a), name);
      return;
    }
    if (name === 'link') {   // coreutils link(1): a hard link at the second operand, the sibling of a hard `ln` (the third pass)
      const ops = args.filter((a) => !(a.text.startsWith('-') && a.text.length > 1));
      if (ops.length >= 2) markMutated(abs(ops[1]), 'link', { alias: true, source: abs(ops[0]) });
      return;
    }
    if (name === 'mv') {
      const parsed = parseCopyOptions(args, 'mv');
      if (parsed.unknown) { markAllCandidates('mv'); return; }
      if (parsed.installDir) return;
      const ops = parsed.operands;
      const destDir = parsed.targetDir;
      if (destDir && destDir.literal) { for (const s of ops) { markMutated(abs(s), 'mv'); markMutated(literalPath(path.join(destDir.text, path.basename(s.text)), cwd), 'mv'); } return; }
      for (const s of ops) markMutated(abs(s), 'mv');   // sources removed; the last, the destination, created
      return;
    }
    if (name === 'ln') {
      // a SYMBOLIC ln with literal operands the hook can place is class H (recordSymlink resolves the link for a later
      // word, and marks the NAME of every other symbolic link, rule (c)); a HARD link is a mutation here, since it
      // aliases the source's inode and the hook cannot resolve it after the fact.
      const parsed = parseCopyOptions(args, 'ln');
      if (parsed.unknown) { markAllCandidates('ln'); return; }
      if (parsed.installDir) return;
      const symbolic = args.some((a) => a.literal && (a.text === '--symbolic' || (/^-[^-]/.test(a.text) && a.text.includes('s'))));
      if (symbolic) return;
      if (parsed.targetDir && parsed.targetDir.literal) { for (const s of parsed.operands) markMutated(literalPath(path.join(parsed.targetDir.text, path.basename(s.text)), cwd), 'ln', { alias: true, source: abs(s) }); return; }
      const ops = parsed.operands;
      if (ops.length >= 2) markMutated(abs(ops[ops.length - 1]), 'ln', { alias: true, source: ops.length === 2 ? abs(ops[0]) : null });   // several sources into a directory: which one an entry aliases is not read
      else if (ops.length === 1) markMutated(literalPath(path.join(cwd, path.basename(ops[0].text)), cwd), 'ln', { alias: true, source: abs(ops[0]) });   // ln src -> ./basename
      return;
    }
    if (name === 'cp') {
      const parsed = parseCopyOptions(args, 'cp');
      if (parsed.unknown) { markAllCandidates('cp'); return; }
      const linky = args.some((a) => a.literal && ((/^-[^-]/.test(a.text) && (a.text.includes('l') || a.text.includes('s'))) || a.text === '--link' || a.text === '--symbolic-link'));
      if (!linky || parsed.installDir) return;
      if (parsed.targetDir && parsed.targetDir.literal) { for (const s of parsed.operands) markMutated(literalPath(path.join(parsed.targetDir.text, path.basename(s.text)), cwd), 'cp -l', { alias: true, source: abs(s) }); return; }
      const ops = parsed.operands;
      if (ops.length >= 2) markMutated(abs(ops[ops.length - 1]), 'cp -l', { alias: true, source: ops.length === 2 ? abs(ops[0]) : null });
    }
  };
  // Record the symlinks an `ln -s` makes when the hook can place both the link NAME and a LITERAL source, so a later
  // word through the link is judged as the path it leads to (class H). Rule (c) (the third pass, 2026-09-19): every
  // other symbolic link the command makes at a name the hook can place (a source that is not literal, `ln -s "$PWD/docs"
  // mydocs`, `ln -s $(echo docs) md3`; a source it cannot resolve; a name or source an earlier command mutated) marks
  // that NAME as mutated, so a later write through it refuses with the reason; before, such a link recorded nothing and
  // `cp base/report.md mydocs/report.md` was judged as the un-followed name, an untracked file, and overwrote the
  // tracked one. A link name the hook cannot place is the ln's own unreadable target, refused by copyTargets.
  const recordSymlink = (args, cwd) => {
    if (!cwd) return;
    const symbolic = args.some((a) => a.literal && (a.text === '--symbolic' || (/^-[^-]/.test(a.text) && a.text.includes('s'))));
    if (!symbolic) return;
    const parsed = parseCopyOptions(args, 'ln');
    if (parsed.unknown || parsed.installDir) return;   // an unknown option: recordMutations marks every candidate (rule (f))
    // the source is relative to the link's OWN directory, not the cwd (a symlink target is `readlink`-relative): the walk-around lens second pass
    // (family 3) after `ln -s ../docs sub/d` recorded `sub/d -> <cwd>/docs` and a write through it was judged outside.
    const record = (src, dstAbs) => {
      if (!dstAbs) return;
      const srcAbs = src.literal ? (path.isAbsolute(src.text) ? src.text : literalPath(src.text, path.dirname(dstAbs))) : null;
      if (!srcAbs || underMutated(dstAbs) || underMutated(srcAbs)) { markMutated(dstAbs, 'ln -s', { alias: true }); return; }   // rule (c): the name is unknown, and what it aliases is not read (B1)
      links.set(dstAbs, srcAbs);
    };
    if (parsed.targetDir) {
      if (!parsed.targetDir.literal) return;   // the ln's own target, refused by copyTargets
      const dirAbs = literalPath(parsed.targetDir.text, cwd);
      for (const s of parsed.operands) {
        if (s.literal) record(s, literalPath(path.join(parsed.targetDir.text, path.basename(s.text)), cwd));
        else markMutated(dirAbs, 'ln -s', { alias: true });   // the link's name is the source's basename, which the hook cannot read: the folder is unknown
      }
      return;
    }
    if (parsed.operands.length < 2) return;
    const dst = parsed.operands[parsed.operands.length - 1];
    if (!dst.literal) return;   // the ln's own target, refused by copyTargets
    const dstAbs = literalPath(dst.text, cwd);
    let dstIsDir = false;
    try { dstIsDir = dstAbs != null && fs.statSync(dstAbs).isDirectory(); } catch { /* a new link name */ }
    if (dstIsDir) {
      for (const s of parsed.operands.slice(0, -1)) {
        if (s.literal) record(s, literalPath(path.join(dst.text, path.basename(s.text)), cwd));
        else markMutated(dstAbs, 'ln -s', { alias: true });
      }
      return;
    }
    if (parsed.operands.length === 2) record(parsed.operands[0], dstAbs);
    else markMutated(dstAbs, 'ln -s', { alias: true });   // several sources into a name that is not a directory: ln fails or the name is unknown
  };
  // A write target the hook cannot read (the header). A process substitution (`>(cmd)`) is a pipe and
  // never a file, so it is dropped, not recorded.
  const cannotRead = (w, how, why = null) => {
    if (/^[<>]\(/.test(w.text)) return;
    const here = unknownDir ? null : dir;
    unresolved.push({
      raw: w.raw, how, dir: here, at: w.at ? literalPath(w.at, here) : null, numeric: w.numeric ? w.text : null,
      text: w.text, marks: w.marks, why,
    });
  };
  const add = (w, how) => {
    try { addInner(w, how); }
    catch (e) { if (isUnknownPath(e) && !(e.why && e.why.how)) e.why = { ...(e.why || {}), how, raw: w && w.raw ? w.raw : (w && w.text) || 'the path' }; throw e; }
  };
  const addInner = (w, how) => {
    if (!w) return;   // a word that is only an expansion (`"$(mktemp)"`) has no text after quote removal, and is still a target
    // class D: the command reassigned HOME, so a word that expanded it (marked 'h') is unreadable. Recorded by its
    // raw spelling with no marks, so the own-project step does not read the guard's home value and the cwd rule decides.
    if (homeUnreadableNow() && w.marks && w.marks.includes('h')) { cannotRead(word(w.raw, false, w.raw), how, { kind: 'homeAssigned', text: (homeWhyNow() || {}).text || 'the command names HOME outside an expansion' }); return; }
    if (w.glob) {
      // every match, as the shell names each (a redirection onto several: zsh's multios writes each, bash
      // writes none and says so, so the over-count costs a command bash refuses anyway); no match, the cwd
      // unknown or past the caps is a target the hook cannot read (2026-09-18)
      const m = expandGlob(w, unknownDir ? null : dir);
      if (m && m.length) for (const x of m) add(x, how);
      else cannotRead(w, how);
      return;
    }
    if (!w.literal) {
      // M3 / B1 (the fifth commit): a word the hook cannot read whose literal directory part sits under a prefix an earlier
      // command removed, renamed or linked is unreadable for THAT reason, so the family-3 refusal and the alias's source
      // decide, from any cwd; before, it was recorded with no reason and judged against a tree where the link did not exist
      const m = mutatedUnderLiteralPart(w);
      cannotRead(w, how, m ? mutatedWhy(m) : (w.why || null));
      return;
    }
    if (!w.text) return;
    // a literal relative target whose directory is not known is refused, not dropped (round 3): the same word
    // spelled absolute is judged, and one `cd` the hook could not follow turned a refused write into an allowed one
    if (!path.isAbsolute(w.text) && unknownDir) { cannotRead(w, how, { kind: 'unknownDir', text: unknownWhy }); return; }
    // class 'mutated' (the walk-around lens second pass, family 3): a later literal target under a prefix an earlier rm/mv/ln/cp -l/cp -s touched
    // is unreadable, since what it resolves to at run time is not what the hook sees now.
    if (mutated.length && !unknownDir) {
      const abs = path.isAbsolute(w.text) ? w.text : dir + '/' + w.text;
      const m = underMutated(path.normalize(abs));
      if (m) { cannotRead(w, how, mutatedWhy(m)); return; }
    }
    // class H: foldSegments (in resolveLiteral) follows a symlink the command made earlier in the same line as it
    // folds, so `mydocs/report.md` reads through `mydocs -> docs` and a `..` after the link climbs from its target
    // (the walk-around lens second pass, 2026-09-19; before, a single-hop prefix match on the unfolded spelling missed `./mydocs`, `base/../mydocs`).
    const p = resolveLiteral(w.text, dir);
    if (!p) return;
    if (p.unresolvable) { cannotRead(w, how, { kind: 'unresolvable', text: p.unresolvable }); return; }
    targets.push({ path: p.path, how });
  };
  let sawOpaqueCommand = false;
  // A script run by `sh` (a `$(...)`, a heredoc-fed shell, a `-c` operand) is read as that shell reads it; a
  // `$(...)` in this command runs in this command's shell, so it inherits `shell`, and the directory state.
  const recurse = (text, sh = shell, fresh = sh !== shell) => {
    if (depth >= RECURSION_CAP) { sawOpaqueCommand = true; return; }
    // B2: a `$(...)` runs in a subshell of this shell and sees its names (a copy: its own assignments do not come back);
    // a script handed to a named shell sees the environment alone, so it inherits none of them (fail closed: a name
    // this command set but did not export is empty there, and one it exported may be read by a script the guard does
    // not follow)
    // HOME's plain-string value crosses into a fresh shell too: a variable that came from the environment stays exported when
    // reassigned, so `HOME=<dir>; sh -c 'echo > ~/x'` writes under <dir> (measured in bash, zsh and dash, the seventh pass)
    const homeValue = vars.has('HOME') && vars.get('HOME') != null ? [['HOME', vars.get('HOME')]] : [];
    const sub = extract(text, {
      dir, unknownDir, unknownWhy, shell: sh, depth: depth + 1, homeAssigned: homeUnreadableNow(), homeWhy: homeWhyNow(), unreadableNames, links, cdFunctions, mutated, keywordMode,
      vars: fresh ? new Map(homeValue) : new Map(vars), unreadableWhy: fresh ? new Map() : new Map(unreadableWhy), refTargets: fresh ? new Set() : new Set(refTargets), readonlyNames: fresh ? new Set() : new Set(readonlyNames), oldDir, varsPoisoned: fresh ? false : varsPoisoned, poisonWhy: fresh ? null : poisonWhy, definedFunctions,
    });
    targets.push(...sub.targets);
    unresolved.push(...sub.unresolved);
    if (sub.opaque) sawOpaqueCommand = true;
  };
  // What a command at segment `idx` reads on stdin, as text the hook holds: its own heredocs and
  // here-strings, and those of the commands piped into it (cat <<EOF | python3 -).
  const stdinBodies = (idx) => {
    const out = [...segments[idx].heredocs];
    for (let j = idx - 1; j >= 0 && segments[j].op === '|'; j--) out.push(...segments[j].heredocs);
    return out;
  };
  // Open scopes, innermost last: a subshell frame holds the dir to restore at its `)`; a function
  // frame (`f() { ... }`, a body defined, not run) holds the dir to restore at its closing brace;
  // a compound frame (if, while, until, for, case) records whether a cd ran in its body.
  // The walk-around lens second pass (family 6): a function whose body moves the shell moves it when CALLED, which the
  // guard does not follow. (A shell option that changes how paths resolve, `set -P`, `set -o chaselinks`, is rule (d)
  // since the third pass: the directory is unknown from the option on, shellOptionChange.)
  const cdFunctions = ctx.cdFunctions || new Set();   // names of functions defined here whose body ran a cd/pushd/popd
  const markFunctionBody = () => {
    for (let j = frames.length - 1; j >= 0; j--) {
      if (frames[j].kind === 'subshell') return;   // a cd in a subshell inside the body restores at its )
      if (frames[j].kind === 'function') { frames[j].bodyMoved = true; return; }
    }
  };
  const frames = [];
  // The `{ }` group frames (C5b, nesting-aware since the seventh pass's attacker, F2): a group frame holds the names assigned
  // inside it and the directory state at its `{`. A group that closes in plain sequence hands its names to the enclosing
  // group (whose own brace may be piped); one whose closing brace is piped or backgrounded ran in a subshell, so its names are
  // tainted and its directory restored. zsh's trailing `}` of `{ cmd }` heads a segment of its own since the third addendum
  // (splitAtClosers), read after the command like the `;` twin's; the seventh pass's pendingClose, which held it back, is gone.
  // Round 5's addendum (the frame lens, 2026-09-20): a group whose OPENING brace follows `&&`, `||` or `|` is `conditional`
  // (the operator kept): the shells skip it, or run it in a subshell, whole, so nothing inside it is this shell's own, on
  // whatever line the body sits (plainSequence and the cd handler read the flag; the same-line `false && { x=1; }` was refused
  // by the assignment's own previous operator while `false && {⏎x=1⏎}` read a newline there and adopted x, 36 rows in bash, zsh
  // and dash, F1, `test -d d || {⏎mkdir d⏎cd d⏎}` the lead). A group behind `time` is `timed`: zsh does not keep an assignment
  // made alone inside it (`x=a; time { x=b; }` leaves a in zsh and b in bash, measured), so its assignments are unreadable
  // (F9) while its cd, which moves every shell, is followed.
  const openGroup = (conditional = null, timed = false) => frames.push({ kind: 'group', names: new Set(), dir, unknownDir, unknownWhy, oldDir, conditional, timed });
  const closeGroups = (n, op) => {
    for (let i = 0; i < n && frames.length && frames[frames.length - 1].kind === 'group'; i++) {
      const g = frames.pop();
      if (i === n - 1 && (op === '|' || op === '&')) {
        const how = op === '|' ? 'a `{ }` group that is piped, which the shells run in a subshell' : 'a `{ }` group that is backgrounded, which the shells run in a subshell';
        for (const nm of g.names) { readonlyNames.delete(nm); taint(nm, wroteThrough(nm, how, '{ ... }')); }   // a name frozen inside the group was frozen in the subshell alone (round 5's addendum, the freeze lens: `{ readonly x; } | cat; x=..` performed the later write in every shell)
        ({ dir, unknownDir, unknownWhy, oldDir } = g);
      } else if (frames.length && frames[frames.length - 1].kind === 'group') {
        for (const nm of g.names) frames[frames.length - 1].names.add(nm);
      }
    }
  };
  const isScope = (f) => f.kind === 'subshell' || f.kind === 'function';   // CLOSERS and BODY_CLOSER (module level) name the compound frames
  const isCompound = (f) => !!f && Object.hasOwn(BODY_CLOSER, f.kind);
  const restore = (f) => { ({ dir, unknownDir, unknownWhy } = f); };
  // A compound frame (the heads of BODY_CLOSER) records whether a cd ran in its body (`moved`), whether its body opener has
  // been read (`opened`: `then`, `do`, `in`, foreach's `)`), the brace depth of a brace body (`braces`) and a `)` that closed
  // with nothing after it (`afterParen`, so the next segment is zsh's one-command body: `if (x) cmd`, `for y (..) cmd`).
  // `oneSegment` on any frame says its body is the segment being read and it closes before the next one (a compound frame
  // applies `moved`, a function or coproc frame restores the directory); `untilChild` on a coproc frame says it closes with
  // the compound frame pushed above it (round 5's addendum).
  const pushCompound = (head) => { const f = { kind: head, moved: false, opened: false, braces: 0, condition: false, awaitBody: false, afterParen: false, dir, unknownDir, unknownWhy }; frames.push(f); return f; };   // the directory at the head: a redirection on the closer is judged there (closedConstruct)
  const closeCompoundAt = (j) => {
    if (frames.slice(j).some((f) => f.moved)) setUnknown('an earlier `cd` sits in an if, loop or case body that may not run');
    frames.length = j;
    afterChildClosed();
  };
  const closeCompound = (kinds) => {
    for (let j = frames.length - 1; j >= 0 && !isScope(frames[j]); j--) {
      if (!kinds.includes(frames[j].kind)) continue;
      closeCompoundAt(j);
      return;
    }
  };
  const popFunction = (f) => {
    if (f.bodyMoved && f.name) cdFunctions.add(f.name);
    // a `function NAME` without parentheses whose body opens on a later segment (round 5's addendum, F10): bash and zsh define it,
    // dash has no `function` word and runs the body as plain commands in THIS shell, so a cd in it leaves the directory unknown
    if (f.dashRuns && f.bodyMoved) setUnknown('an earlier `cd` sits in the body of a `function NAME` written without parentheses, which bash and zsh define and dash, having no `function` word, runs in this shell');
    else restore(f);
    frames.pop();
  };
  // a scope whose body was the frame pushed above it closes with that frame (round 5's addendum): a function whose body is a
  // subshell or a compound command (`f() (..)`, `f() if ..; fi`), a coproc whose command is a compound (`coproc if ..; fi`),
  // and any one-segment frame whose one segment opened a frame of its own
  const afterChildClosed = () => {
    const t = frames[frames.length - 1];
    if (!t) return;
    if (t.kind === 'function' && (t.depth === 0 || t.oneSegment)) { popFunction(t); afterChildClosed(); return; }
    if (t.kind === 'subshell' && (t.untilChild || t.oneSegment)) { restore(t); frames.pop(); afterChildClosed(); return; }
    if (isCompound(t) && t.oneSegment) closeCompoundAt(frames.length - 1);
  };
  const closeOneSegment = () => {
    for (;;) {
      const t = frames[frames.length - 1];
      if (!t || !t.oneSegment) return;
      if (t.kind === 'function') popFunction(t);
      else if (t.kind === 'subshell') { restore(t); frames.pop(); }
      else closeCompoundAt(frames.length - 1);
    }
  };
  const closeSubshell = (op) => {
    for (let j = frames.length - 1; j >= 0; j--) {
      if (frames[j].kind === 'case' || frames[j].kind === 'function') return;   // in a case body a ) ends a pattern
      if (frames[j].kind === 'subshell') {
        restore(frames[j]);
        frames.length = j;
        // the `)` that ends a compound head's word list or condition (round 5's addendum): foreach's body opens here; a `)` with
        // nothing between it and the next word makes that word zsh's one-command body (`if (x) cmd`, `for y (..) cmd`, F6)
        const t = frames[frames.length - 1];
        if (isCompound(t) && !t.opened) { if (t.kind === 'foreach') t.opened = true; else t.afterParen = op === ''; }
        afterChildClosed();
        return;
      }
    }
  };
  // The body of the innermost compound frame, read on a segment (round 5's addendum; the frame lens found each spelling walked
  // as plain sequence past a body the shell skipped, F4, F6, F7; the third addendum, 2026-09-20, made this the one reader of
  // every brace-body form, over the segments splitAtClosers cuts, so a `}` always heads its segment and the body's last command
  // is read before it). The opener word as the segment's first plain word (or `in` in a case head) marks the body open; an
  // unquoted `{` before the opener is a brace body (zsh's `if [[ .. ]] {`, `while (( .. )) {`, `for y (..) {`, `case x {`,
  // `repeat n {`; bash's `for y in ..; {` and `select ..; {`), the braces inside it counted, whose matching `}` closes the frame
  // with `moved` applied. Two things keep the frame open at that `}`: an `if` body's `else` or `elif` on the same segment (zsh
  // accepts no other placement) reopens the body at the next `{`; and a `{` that is the first word after `if`, `while` or
  // `until` on the head's own segment with no `(( ))` between (`arithAt`) is a CONDITION group, not the body, so its `}` leaves
  // the frame waiting for the body (a `{`, the opener, or one command, on this segment or a later one: zsh continues `while {
  // false }⏎{ .. }` across the newline), and a cd inside it is a body's, unknown at the close, the safe reading of a list that
  // runs at least once. zsh's one-command body is read as the body too: the segment after a head that takes a word list (`list`
  // in the table) or after a `)` with nothing between (`afterParen`), and the word after a `(( ))` condition, after `]]`, or
  // after a condition group's `}` (`if (( 0 )) cd ../scratch; cp ..` was walked as plain sequence and the skipped cd followed);
  // such a frame closes before the next segment (`oneSegment`). The words of a condition that share the segment with the body's
  // first command (`[[ 1 = 1 ]]` before `{ cp .. }` or before one command, an elif's) are dropped, with the caller's as-spelled
  // words dropped alike (`mirror`), so commandOf reads the body's command and not the condition's; a case head's patterns are
  // not a condition and stay. An `in` after a `for` or `select` head is its list, not a body; a `{` or `}` inside a body opened
  // by its keyword is a plain group and changes nothing. Returns the index after a `}` that closed the frame, so the next reader
  // (a function frame's braces, the group scan) does not read the same brace, and 0 when the frame stays open. A body the walk
  // cannot see the end of stays open, the safe direction: every later name is unreadable and a cd inside is applied at the
  // closer or never trusted.
  const compoundBody = (seg, start, f, headSegment = false, mirror = null) => {
    const { opener, list } = BODY_CLOSER[f.kind];
    const arithBefore = (i) => (seg.arithAt || []).includes(i);
    const drop = (from, to) => {   // the condition's words before the body's first command, dropped from the segment and the mirror
      if (from < 0 || to <= from || f.kind === 'case') return 0;
      seg.words.splice(from, to - from);
      if (mirror) mirror.splice(from, to - from);
      return to - from;
    };
    let condStart = start;   // where a condition's words begin on this segment while the body is not yet open
    let first = true;
    for (let i = start; i < seg.words.length; i++) {
      const w = seg.words[i];
      const plain = plainWord(w);
      if (f.braces > 0) {
        if (plain && w.text === '{') f.braces++;
        else if (plain && w.text === '}' && --f.braces === 0) {
          if (f.condition) { f.condition = false; f.awaitBody = true; condStart = i + 1; first = false; continue; }   // the condition group closed: the body follows
          const next = seg.words[i + 1];
          if (f.kind === 'if' && plainWord(next) && (next.text === 'else' || next.text === 'elif')) { f.opened = false; condStart = i + 2; i++; first = false; continue; }   // the same frame goes on
          closeCompoundAt(frames.indexOf(f));
          return i + 1;
        }
        first = false;
        continue;
      }
      if (!f.opened) {
        if (plain && w.text === opener) { f.opened = true; f.afterParen = false; f.awaitBody = false; first = false; continue; }
        if (plain && w.text === '{') {
          if (headSegment && i === start && !list && !f.afterParen && !arithBefore(i)) { f.condition = true; f.braces = 1; first = false; continue; }   // `if { cond } { body }`, `while { cond } { body }`
          i -= drop(condStart, i);
          f.opened = true; f.braces = 1; f.afterParen = false; f.awaitBody = false; first = false;
          continue;
        }
        if (plain && list && w.text === 'in') { first = false; continue; }
        // zsh's one-command body
        if ((first && start === 0 && (list || f.afterParen)) || f.awaitBody || (headSegment && !list && arithBefore(i))) { drop(condStart, i); f.opened = true; f.oneSegment = true; f.afterParen = false; f.awaitBody = false; return 0; }
        if (plain && !list && w.text === ']]' && i + 1 < seg.words.length && !(plainWord(seg.words[i + 1]) && (seg.words[i + 1].text === '{' || seg.words[i + 1].text === opener))) { drop(condStart, i + 1); f.opened = true; f.oneSegment = true; return 0; }
      }
      first = false;
    }
    return 0;
  };
  const movedHere = () => {
    for (let j = frames.length - 1; j >= 0 && !isScope(frames[j]); j--) frames[j].moved = true;
  };
  activeLinks = links;   // foldSegments follows these while this command's literal targets resolve (the walk-around lens second pass)
  // The braces of a function body: the frame closes, restoring the dir, when its depth returns to 0. Returns the index of
  // the first word AFTER the brace that closed the body (round 5: `{ y=1; f() { :; }; } | cat` had the body's `}` counted
  // here and then again by the group scan, which closed the piped group one brace early, so y stayed readable while the
  // shells ran the group in a subshell); `from` when no function frame is open, and the segment's length while the body goes
  // on. Read from `from` (round 5's third addendum): on a `} }` segment the first brace closes the compound body inside the
  // function and this reads the second, and a compound head inside the body (`f() { if (( 0 )) { cd x } }`) ends the count,
  // since its brace body is counted by its own frame (compoundBody) and was counted here too, which left the function frame
  // open to the end of the command. Only an unquoted brace counts (round 5's fourth addendum): `f() { echo "}"; cd ../scratch;
  // }; cp ../base/report.md report.md` from docs/ popped the frame at the quoted word, followed the cd as plain sequence and
  // was allowed while bash, zsh and dash wrote the tracked file (the `'}'`, `\}`, `printf %s "}"`, pushd, name and newline
  // forms alike); a quoted `{` heading the body's segment is the command of zsh's and dash's one-command body, not its opener.
  const braces = (seg, from = 0) => {
    const f = frames[frames.length - 1];
    if (!f || f.kind !== 'function') return from;
    // a body without braces (zsh and dash accept `f() cmd` and `function f cmd`; bash rejects them): this one segment is the
    // body, defined and not run, and the frame closes before the next segment (round 5's addendum, F3: the frame was popped
    // here and the body read as the enclosing scope's, its assignment adopted and its cd followed, in zsh, dash and through
    // `sh -c` from every shell)
    if (f.depth === 0 && from === 0 && !(seg.words.length && plainWord(seg.words[0]) && seg.words[0].text === '{')) { f.oneSegment = true; return 0; }
    for (let i = from; i < seg.words.length; i++) {
      const w = seg.words[i];
      if (plainWord(w) && Object.hasOwn(BODY_CLOSER, w.text)) break;   // a compound inside the body: its own frame counts its braces
      if (plainWord(w) && w.text === '{') f.depth++;
      else if (plainWord(w) && w.text === '}' && --f.depth <= 0) { popFunction(f); return i + 1; }
    }
    return seg.words.length;
  };
  // The frame a segment's leading closer ends, for its redirections (round 5's third addendum): bash, zsh and dash open a
  // compound command's, a `{ }` group's or a function body's redirections before the construct runs, in the directory the shell
  // is in at its start, so `{ cd ../scratch; } > report.md` from docs/ truncates docs/report.md in all three (and `if true; then
  // cd ../scratch; fi > report.md` the same), where the guard judged the target after the cd it had followed inside and allowed
  // the write. A `fi`, `done`, `esac` or `end` names its frame through CLOSERS; a run of `}` closes, from the top, the frames
  // whose braces they are (a group's one, a function body's depth, a compound brace body's count), and the outermost of those
  // is the construct the redirection belongs to. null when the segment closes nothing the guard tracks.
  const closedConstruct = (seg) => {
    let k = peelIndex(seg.words, 0, false);
    const w = seg.words[k];
    if (!plainWord(w)) return null;
    if (Object.hasOwn(CLOSERS, w.text)) {
      for (let j = frames.length - 1; j >= 0 && !isScope(frames[j]); j--) if (CLOSERS[w.text].includes(frames[j].kind)) return frames[j];
      return null;
    }
    if (w.text !== '}') return null;
    let n = 0;
    while (k < seg.words.length && plainWord(seg.words[k]) && seg.words[k].text === '}') { n++; k++; }
    let outer = null;
    for (let j = frames.length - 1; j >= 0 && n > 0; j--) {
      const f = frames[j];
      const own = f.kind === 'group' ? 1 : f.kind === 'function' ? f.depth : isCompound(f) ? f.braces : 0;
      if (!own) break;
      outer = f;
      n -= Math.min(n, own);
    }
    return outer;
  };
  // the write redirections of a segment, judged in the directory of the construct its leading closer ends (closedConstruct) when
  // there is one, else where the walk stands
  const addRedirects = (seg, construct) => {
    const saved = { dir, unknownDir, unknownWhy };
    if (construct) ({ dir, unknownDir, unknownWhy } = construct);
    try { for (const r of seg.redirects) if (WRITE_REDIRECTS.has(r.op)) add(r.target, `${r.op} redirection`); }
    finally { if (construct) ({ dir, unknownDir, unknownWhy } = saved); }
  };
  for (let idx = 0; idx < segments.length; idx++) {
    const seg = segments[idx];
    closeOneSegment();   // a one-segment body read on the previous segment closes here (round 5's addendum)
    if (seg.paren === '(') {
      const next = segments[idx + 1];
      const prev = segments[idx - 1];
      // the name is read after the peel (round 5): `! f() { x=..; }` and `{ f() { x=..; }; }` are definitions too, and were read
      // as a subshell before a plain group, whose assignment the guard adopted while no shell ran the body
      const rest = prev && prev.op === '(' ? prev.words.slice(peelIndex(prev.words, 0, true, false)) : [];
      // the word list of a `for`, `select` or `foreach` head, or the condition of an `if` or `while` (`for y (a b)`, `if (cmd)`):
      // a subshell frame for the words inside, and closeSubshell tells the compound frame its `)` closed
      const listOf = rest.length > 0 && plainWord(rest[0]) && Object.hasOwn(BODY_CLOSER, rest[0].text);
      // `name() {`, and since round 5's addendum every spelling that puts one or more words before an EMPTY pair of parentheses:
      // zsh's `f g () {` defines both names and `env f () {` defines env and f, running nothing, while bash and dash reject them
      // all with a syntax error; the paren path had read a rest of two words as a subshell before a plain group, whose
      // assignment the guard adopted and whose cd it followed (40 rows in zsh, F2)
      if (!listOf && next && next.paren === ')' && rest.length) {
        const names = rest.filter((w) => !(plainWord(w) && w.text === 'function')).map((w) => w.text);
        for (const nm of names) definedFunctions.add(nm);   // B2: a call of any of them may assign any name
        frames.push({ kind: 'function', name: names.length ? names[names.length - 1] : rest[rest.length - 1].text, bodyMoved: false, dir, unknownDir, unknownWhy, depth: 0 });   // name() ... : a definition, not a run
        idx++;
        continue;
      }
      frames.push({ kind: 'subshell', dir, unknownDir, unknownWhy });
      continue;
    }
    if (seg.paren === ')') { closeSubshell(seg.op); continue; }
    const construct = closedConstruct(seg);   // before any frame closes: the construct this segment's leading closer ends, for its redirections
    // the innermost frame reads the segment from `from`: a compound frame its opener, brace body, condition group or one-command
    // body (compoundBody), a function frame its body's braces; a closer that ends one frame hands the rest of the segment to the
    // frame beneath (`} }`: a compound brace body's, then the function body's around it; round 5's third addendum)
    let from = 0;
    for (;;) {
      const t = frames[frames.length - 1];
      const next = isCompound(t) ? compoundBody(seg, from, t) : t && t.kind === 'function' ? braces(seg, from) : from;
      if (next <= from) break;
      from = next;
    }
    // A `{ }` group at the top level (C5b), at ANY nesting (the seventh pass's attacker, F2, 2026-09-19): a frame the readability
    // rule looks through (a plain group runs in this shell; one opened after `&&`, `||` or `|`, or behind `time`, is not plain, round 5's addendum) until its closing brace is piped or backgrounded, when the group ran
    // in a subshell: every name assigned inside it, the groups nested in it included, is tainted and the directory it moved to
    // restored (`{ cd docs; } | cat; cp base/report.md docs/report.md` was judged from docs/ while bash wrote the tracked file
    // from the cwd, found with the sixth pass's fix). Before this pass one frame opened for the first `{` and popped on the
    // FIRST `}`, so in `x=docs/report.md; { { x=scratch/keep.md; }; } | cat; cp base/report.md $x` the piped OUTER brace was
    // never seen as a subshell boundary, x resolved to the inner value and bash, zsh and dash wrote the tracked file (13 rows,
    // a cd face and a one-level declaration included). A segment may carry several braces (`{ {`, and `} }`, which all three shells accept without a `;`
    // between); zsh's `{ cmd }`, with the brace after the command (bash and dash need the `;`), reaches here as the `;` twin,
    // the brace heading a segment of its own (splitAtClosers, round 5's third addendum), and the segment's operator settles the
    // LAST brace it closes. openGroups / closeGroups below.
    let k = from;   // the index after the leading braces, and after the peel words before and between them (round 5)
    if (frames.every((f) => f.kind === 'group') && seg.words.length > from) {
      const brace = (w) => ((w.text === '{' || w.text === '}') && w.marks && w.marks[0] === 'u' ? w.text : null);
      const prevOp = idx > 0 ? segments[idx - 1].op : '';
      const conditional = prevOp === '&&' || prevOp === '||' || prevOp === '|' ? prevOp : null;   // every group this segment opens is skipped or run in a subshell whole (round 5's addendum, F1)
      k = peelIndex(seg.words, from, false);
      let closes = 0;
      // zsh's `{ try-list } always { always-list }` (round 5's addendum, F5) reaches here as one group: the lexer dropped the
      // `} always {`, so the group closes at the last `}`, whose operator says whether the whole construct ran in a subshell
      while (k < seg.words.length && brace(seg.words[k]) === '}') { closes++; k = peelIndex(seg.words, k + 1, false); }
      if (closes) closeGroups(closes, k >= seg.words.length ? seg.op : '');
      let start = from;
      while (k < seg.words.length && brace(seg.words[k]) === '{') { openGroup(conditional, seg.words.slice(start, k).some((w) => plainWord(w) && w.text === 'time')); start = k + 1; k = peelIndex(seg.words, k + 1, false); }
    }
    // `function NAME {` and `function NAME` then `{` (bash, zsh; the parentheses optional): a definition, not a run (C6a: it was
    // read as a command named `function`, so the body's assignment was read as the shell's own and the call poisoned nothing).
    // The frame is the one `name() {` gets; a `{` on this segment is the body's and counts here, a `{` on the next segment is
    // counted by `braces`; `function NAME () {` takes the paren path above. The word is read after the peel and after the
    // leading braces, whose group frames are open by now (round 5: `{ function f { x=..; }; } | cat`).
    {
      const p = peelIndex(seg.words, k, false);
      if (seg.words.length >= p + 2 && plainWord(seg.words[p]) && seg.words[p].text === 'function' && seg.words[p + 1].literal && seg.op !== '(' && !frames.some((f) => f.kind === 'function')) {
        // every word up to the body's `{` is a name (round 5's addendum, F2: zsh's `function f g {` defines both and runs nothing;
        // bash rejects the spelling); with no `{` on this segment the body is the next segment, a `{ }` group counted by `braces`
        // or zsh's one-command body, which dash, having no `function` word, runs in THIS shell (`function f⏎{⏎cd ../docs⏎}` moved
        // dash and the write after it landed on the tracked file, F10), so a cd in such a body leaves the directory unknown at
        // its close (`dashRuns`, popFunction)
        let q = p + 1;
        while (q < seg.words.length && !(plainWord(seg.words[q]) && seg.words[q].text === '{')) { if (seg.words[q].literal) definedFunctions.add(seg.words[q].text); q++; }
        const body = q < seg.words.length;
        frames.push({ kind: 'function', name: seg.words[p + 1].text, bodyMoved: false, dir, unknownDir, unknownWhy, depth: body ? 1 : 0, dashRuns: !body });
        seg.words = seg.words.slice(q + (body ? 1 : 0));
        // the body opens on the next segment, which `braces` counts; the segment's redirections are still judged, since dash,
        // having no `function` word, runs the line as a command and performs them (`function f echo x > report.md` truncated
        // the tracked file in dash while the emptied segment was skipped whole: round 5's third addendum, the matrix's row)
        if (!seg.words.length) { addRedirects(seg, construct); continue; }
      }
    }
    // `coproc` (a reserved word of bash and zsh; round 5's addendum, F8): the command after it, in bash a NAME and a compound
    // body, runs in a coprocess, a subshell whose assignments and cd never reach this shell while its writes land, so the word
    // (and the NAME) is dropped and the rest is read inside a frame that keeps no name and restores the directory: a brace body
    // counts its braces like a function body, a compound body closes with its compound, a simple command closes with its
    // segment. `coproc {⏎x=other.md⏎}; cp base/report.md scratch/$x` adopted x and `coproc {⏎cd ../scratch⏎}` followed the cd
    // (31 rows in bash and zsh at round 5's head), and `coproc cp base/report.md docs/report.md` was an operand of a command
    // named coproc, the residual the contract listed; each is refused now. dash has no coproc (not found, nothing runs).
    {
      const p = peelIndex(seg.words, k, false);
      if (seg.words.length > p && plainWord(seg.words[p]) && seg.words[p].text === 'coproc') {
        let q = p + 1;
        const bodyWord = (w) => !!(w && plainWord(w) && (w.text === '{' || Object.hasOwn(BODY_CLOSER, w.text)));
        if (seg.words[q] && seg.words[q].literal && IDENTIFIER.test(seg.words[q].text) && bodyWord(seg.words[q + 1])) q++;   // bash's NAME before a compound body
        seg.words = seg.words.slice(q);
        if (!seg.words.length) continue;
        if (plainWord(seg.words[0]) && seg.words[0].text === '{') { frames.push({ kind: 'function', name: null, bodyMoved: false, dir, unknownDir, unknownWhy, depth: 0, coproc: true }); braces(seg); }
        else if (plainWord(seg.words[0]) && Object.hasOwn(BODY_CLOSER, seg.words[0].text)) frames.push({ kind: 'subshell', dir, unknownDir, unknownWhy, coproc: true, untilChild: true });
        else frames.push({ kind: 'subshell', dir, unknownDir, unknownWhy, coproc: true, oneSegment: true });
      }
    }
    // B2: the expansions the guard can read are resolved before the segment's words and targets are judged
    for (const r of seg.redirects) r.target = resolveWord(r.target);
    if (commandOf(seg.words) === null) {
      // assignment words alone, this shell's own when in plain sequence (the readability rule's one readable form): the frame of
      // an if, while or until head opens first, then each word is resolved with the names the words before it set and recorded,
      // left to right as the shells perform them (C5d: `x=../docs/report.md y=$x` gives y the NEW x); the redirections were
      // resolved above, before any of them (bash expands a redirection before it assigns)
      const head0 = compoundHeadOf(seg.words);   // after the peel (round 5), read from the one table
      if (head0 != null && Object.hasOwn(BODY_CLOSER, head0)) compoundBody(seg, peelIndex(seg.words) + 1, pushCompound(head0), true);
      const seq = plainSequence(seg, idx);
      seg.words = seg.words.map((w) => { const r = resolveWord(w); recordPlainWord(r, seg, idx, seq); return r; });
      addRedirects(seg, construct);
      for (const inner of seg.subs) recurse(inner);
      taintArith(seg);   // a bare `(( x = 5 ))` is a segment with no words: its body may assign any name in it
      continue;
    }
    let preWords = seg.words;   // as spelled: the readability rule reads a mention in the command's own text, not in a resolved value
    seg.words = seg.words.map(resolveWord);
    addRedirects(seg, construct);   // a glob: every match (add); a closer's redirections in the construct's start directory
    for (const inner of seg.subs) recurse(inner);
    // the compound head after the peel (round 5), read from the one table; Object.hasOwn, since `in` consulted the prototype
    // chain and a command word that is an Object.prototype key (`toString`, `constructor`, `__proto__`) inside a body threw
    // in the walk and evaluate's catch-all turned the throw into an allow (round 4's extra4-4; the catch-all refuses now)
    const head = compoundHeadOf(seg.words);
    if (head != null && Object.hasOwn(CLOSERS, head)) closeCompound(CLOSERS[head]);
    else if (head != null && Object.hasOwn(BODY_CLOSER, head)) {
      const f = pushCompound(head);
      const at = peelIndex(seg.words);
      // zsh's `repeat N cmd` and `repeat N { .. }` (round 5's addendum, F4; the third addendum for the brace form): the words after
      // the count are the body, run N times (0 included), so `repeat N` is dropped and the rest read as the body, one command
      // (`repeat 2 cp base/report.md docs/report.md` writes the tracked file in zsh; bash and dash have no repeat and run nothing)
      // or a brace body, whose writer commandOf had read as repeat's operand (`repeat 1 { cp .. }` allowed while zsh copied)
      if (head === 'repeat' && seg.words.length > at + 2) { seg.words = seg.words.slice(at + 2); preWords = preWords.slice(at + 2); compoundBody(seg, 0, f, true, preWords); }
      else compoundBody(seg, at + 1, f, true, preWords);
    }
    const cmd = commandOf(seg.words);
    if (!cmd) {
      // assignment words (and reserved words) alone once compoundBody dropped a condition's words or the head branch `repeat N`
      // (round 5's second and third addenda: `if [[ 1 = 1 ]] { x=.. }`, `repeat 0 { x=.. }`): recorded as the assignment-only
      // path above records them, inside the frame the head pushed, so the body's assignment is unreadable with the body's own
      // reason (before, the `}` or `repeat` was read as the command and the assignment as its word: a refusal, with the wrong
      // construct named); anything else keeps the taint-by-shape read
      if (seg.words.every((w) => isAssignmentWord(w) || (plainWord(w) && RESERVED.has(w.text)))) {
        const seq = plainSequence(seg, idx);
        for (const w of seg.words) recordPlainWord(w, seg, idx, seq);
        taintArith(seg);
      } else recordSegment(seg, idx, null, preWords);
      continue;
    }
    if (cmd.unknown) {
      // rule (b) (the third pass, 2026-09-19): a wrapper option its table does not parse in full. The option, its `=value`
      // and every later word are recorded as targets the hook cannot read, so the own-project step judges each literal
      // one by its own directory (an absolute path inside a project refuses from any cwd) and the cwd rule the rest;
      // the command behind the wrapper is not read, since the option may have moved it or taken part of it.
      const { option, wrapper, value, rest } = cmd.unknown;
      const why = { kind: 'unknownOption', option, wrapper };
      cannotRead(word(option, false, option), wrapper, why);
      if (value) cannotRead(value, wrapper, why);
      for (const w of rest) cannotRead(w, wrapper, why);
      varsPoisoned = true;   // B2: what the wrapper ran is not known
      continue;
    }
    if (cmd.opaque) {
      // `env -S STRING` and the sudo options the table refuses (rule (b)): the string, or the rest of the line, goes
      // through a splitter the hook does not read, so nothing behind the option is read as a command. The option, the
      // string, each word the string would split into and every later word are recorded as targets the hook cannot read,
      // so a path inside a project refuses from any cwd and the cwd rule decides the rest.
      const { option, script, rest } = cmd.opaque;
      const why = { kind: 'opaqueScript', option };
      cannotRead(word(option, false, option), option, why);
      if (script) {
        cannotRead(script, option, why);
        if (script.literal) for (const s of lex(script.text).segments) for (const w of s.words) cannotRead(w, option, why);
      }
      for (const w of rest) cannotRead(w, option, why);
      sawOpaqueCommand = true;
      varsPoisoned = true;   // B2
      continue;
    }
    if ('script' in cmd) {   // `flock … -c 'string'` runs the string through `$SHELL -c`, read like `sh -c` (round 4)
      if (cmd.script && cmd.script.literal) recurse(cmd.script.text, shell, true);   // `$SHELL -c`: a fresh shell, the names not inherited (B2)
      else if (cmd.script) sawOpaqueCommand = true;
      continue;
    }
    const asSpelled = cmd.args;
    let { name } = cmd;
    if (/^(python[0-9.]*|pypy[0-9]*)$/.test(name)) name = 'python';
    else if (name === 'nodejs') name = 'node';
    // rule (d) (the third pass): a shell option not on the inert allowlist leaves the directory unknown from here
    if (name === 'set' || name === 'shopt' || name === 'setopt' || name === 'unsetopt') {
      const why = shellOptionChange(name, asSpelled);
      if (why) { setUnknown(why); movedHere(); }
      if (setsKeywordMode(name, asSpelled)) keywordMode = true;
    }
    // bash's keyword mode (setsKeywordMode): a later writer's operands are read as spelled and with every assignment-shaped
    // word dropped, and a write under either reading is judged; zsh reads the words as spelled
    let variants = keywordMode && asSpelled.some(isAssignmentWord) ? [asSpelled, asSpelled.filter((w) => !isAssignmentWord(w))] : [asSpelled];
    // The braces the lexer cut from this command's tail (splitAtClosers, round 5's third addendum; the second addendum had found
    // the trailing `}` of zsh's `{ cp ../base/report.md report.md }` read as cp's destination, so the tracked file zsh overwrote
    // was read as a source, and cut it here): zsh reads them as closers, the reading the frames took; bash and dash read a `}`
    // after a command as one more operand (`cp a }` writes a file named `}` where no group is open, and they reject the group
    // spelling), so each writer is judged as cut and with the braces back as operands, and a write under either reading is refused.
    if (seg.closerTail && seg.closerTail.length) variants = [...variants, ...variants.map((v) => [...v, ...seg.closerTail])];
    for (const args of variants) {
    // the walk-around lens second pass (family 6): a call to a function whose body moved the shell moves the cwd, which the guard does not
    // follow into the call, so the directory is unknown from here (the body was modelled as not moving the shell)
    const calledAsSpelled = rawHeadOf(seg.words);   // the head before a wrapper peel: a function named like a wrapper is called by that name (C6b)
    if (cdFunctions.has(name)) setUnknown(`an earlier call of the function \`${name}\` may change the directory, which I do not follow`);
    else if (calledAsSpelled != null && cdFunctions.has(calledAsSpelled)) setUnknown(`an earlier call of the function \`${calledAsSpelled}\` may change the directory, which I do not follow`);
    // a file a wrapper itself writes (`time -o FILE`): judged in the shell's cwd, and again below once the wrappers'
    // chdirs are entered, since the guard does not order one wrapper's option against another's chdir (over-counting is
    // the refuse direction)
    for (const w of cmd.writes) add(w, 'time -o');
    // `env -C DIR`, `env --chdir=DIR`, `sudo -D DIR`, and a nested chdir (`env -C a env -C b`, rule (b)): each is entered
    // in turn, the next resolved against the last, for this command only (its redirections, processed above, stay in
    // the shell's cwd). A literal DIR is entered like a `cd`; a non-literal one, a `~`/`$HOME` one after a mention of
    // HOME, or one the command cannot enter, leaves the directory unknown, so the inner relative targets are refused with
    // the reason rather than dropped (round 4, 2026-09-19: `env -C DIR cp …` dropped the whole segment and the copy
    // landed on the tracked file). env's and sudo's chdir is chdir(2), which the kernel resolves (a `..` after a symlink
    // climbs from its real target), so the operand is folded physically, not lexically (family 6: `env -C lnout/.. cp …`).
    const chdirSaved = cmd.chdirs.length ? { dir, unknownDir, unknownWhy } : null;
    for (const c of cmd.chdirs) {
      if (!c.word) { setUnknown(`an earlier \`${c.flag}\` names no directory`); continue; }
      if (homeWord(c.word)) { setUnknown(`an earlier \`${c.flag} ${c.word.raw}\` goes through HOME, and ${homeUnknownText()}`); continue; }
      if (!c.word.literal) { setUnknown(`an earlier \`${c.flag}\` names ${c.word.raw}, a directory the shell fills in when the command runs`); continue; }
      const r = resolveLiteral(c.word.text, unknownDir ? null : dir);
      if (r == null) setUnknown(`an earlier \`${c.flag}\` follows a directory I could not read`);
      else if (r.unresolvable) setUnknown(`an earlier \`${c.flag} ${c.word.raw}\` follows a directory I cannot resolve`);
      else if (!enterable(r.path)) { dir = r.path; setUnknown(`an earlier \`${c.flag} ${c.word.raw}\` names a directory the command cannot enter when I check it`); }
      else setKnown(r.path);
    }
    if (chdirSaved) for (const w of cmd.writes) add(w, 'time -o');
    switch (name) {
      case 'cd': case 'pushd': {
        // The walk-around lens second pass (family 6): a `cd` the guard cannot know ran in THIS shell leaves the directory unknown. Whichever
        // of these holds, the shell may not move where the guard would place it (or moves in a subshell, or physically),
        // so a later literal relative target refuses with the construct named, as `cd -` and a non-literal cd already do.
        // A construct is checked only when the cd would OTHERWISE cleanly move (enterable, literal), so the round-3
        // "cannot enter" and non-literal reasons, which are more specific, keep their message (`mkdir -p x && cd x`).
        const prevOp = idx > 0 ? segments[idx - 1].op : '';
        const opts = args.filter((w) => w.literal && /^-/.test(w.text) && w.text !== '-' && w.text !== '--');
        const rotate = name === 'pushd' && args.some((w) => w.literal && /^[-+]\d+$/.test(w.text));
        const pushdN = name === 'pushd' && opts.some((w) => w.text === '-n');
        const physical = opts.some((w) => /P/.test(w.text));
        const unmodeled = opts.some((w) => !/^-[LPe@n]+$/.test(w.text)) && !rotate;
        let block = null;
        if (prevOp === '&&' || prevOp === '||') block = `an earlier \`${name}\` after \`${prevOp}\` may not run, so where it lands is not known (its move depends on the previous status)`;
        else if (seg.alwaysHead) block = `an earlier \`${name}\` is the first command of an always-list on the line of its \`always\`, which zsh runs and bash and dash read as operands of the command before \`always\`, so where the shell is after it depends on which shell runs the line`;   // round 5's third addendum
        else if (seg.op === '|' || prevOp === '|') block = `an earlier \`${name}\` is part of a pipeline, so it runs in a subshell and moves nothing in this shell`;
        else if (seg.op === '&') block = `an earlier \`${name}\` is backgrounded, so it runs in a subshell and moves nothing in this shell`;
        else if (frames.some((f) => f.kind === 'group' && f.conditional)) {
          // round 5's addendum (F1): the group the cd sits in was opened after `&&`, `||` or `|`, so the shells skip it whole, or run it
          // in a subshell (`test -d ../scratch || {⏎mkdir ../scratch⏎cd ../scratch⏎}⏎cp ../base/report.md report.md` was judged from
          // scratch/ while bash, zsh and dash, the directory there, skipped the group and wrote the tracked docs/report.md)
          const g = frames.find((f) => f.kind === 'group' && f.conditional);
          block = g.conditional === '|'
            ? `an earlier \`${name}\` sits in a \`{ }\` group opened after \`|\`, a pipeline member that bash and dash run in a subshell and zsh in this shell, so where the shell is after it depends on which shell runs the line`
            : `an earlier \`${name}\` sits in a \`{ }\` group opened after \`${g.conditional}\`, which may not run, so where it lands is not known`;
        }
        else if (cmd.wrapped) {
          // the seventh pass's addendum, item 2 (WRAPPED_CD_WHY): under `builtin`, `command` and `time` the shell's own cd runs in
          // some shells and moves them, so the text says which; under every other wrapper an external cd runs and moves nothing
          const w = cmd.wrappers[cmd.wrappers.length - 1];
          block = WRAPPED_CD_WHY[w]
            ? `an earlier \`${name}\` runs under a wrapper (\`${w}\`), which ${WRAPPED_CD_WHY[w]}, so where the shell is after it depends on which shell runs the line`
            : `an earlier \`${name}\` runs under a wrapper (\`${w}\`), an external \`${name}\` that moves nothing in this shell`;
        }
        else if (pushdN) block = 'an earlier `pushd -n` pushes a directory without changing to it';
        else if (rotate) block = 'an earlier `pushd` rotates the directory stack, so where it lands is not known';
        else if (physical) block = `an earlier \`${name}\` resolves \`..\` physically (\`-P\`, or an option I do not model), so where it lands is not known`;
        else if (unmodeled) block = `an earlier \`${name}\` carries an option I do not model, so where it lands is not known`;
        let a = args.find((w) => !w.text.startsWith('-') || w.text === '-');
        if (a && a.glob) {   // cd docs/*: one match is the directory; several, or none, leave it unknown
          const m = expandGlob(a, unknownDir ? null : dir);
          a = m && m.length === 1 ? m[0] : word(a.text, false, a.raw, { marks: a.marks });
        }
        // a bare `cd`, or a `cd ~/x`, goes to HOME: a directory the guard cannot read once the command names HOME (rule (a)); after a
        // plain `HOME=<dir>` (the addendum, item 1) the bare cd is a `cd <dir>`, resolved against the current directory like any
        // literal cd (the dollar matrix's row 2847, `HOME='p$abc'; cd; printf poison > rep.md`, moved the guard to the bare string
        // and the relative write was judged nowhere while bash wrote the tracked folder under the cwd)
        // A bare `pushd` is not a bare `cd`: bash exchanges the top two entries of the directory stack and fails when there is one
        // (the shell stays), dash has no pushd (the shell stays), zsh goes to the home directory; measured 2026-09-19, when the
        // guard read it as a move to HOME and `pushd; cp base/report.md docs/report.md` was allowed while bash and dash wrote
        // the tracked file. Where the shell is after it is not known.
        if (!a && name === 'pushd' && !block) block = 'an earlier bare `pushd` exchanges the top two directories of the stack, or fails when there is one (bash; dash has no pushd), or goes to HOME (zsh), so where the shell is after it is not known';
        if (!a && !block && !homeUnreadableNow()) { const hv = valueOf('HOME'); a = word(hv, true, name, { marks: 'q'.repeat(hv.length) }); }
        if (!a) { if (block) moveUnknown(block); else moveUnknown(`an earlier bare \`${name}\` goes to HOME, and ${homeUnknownText()}`); }
        else if (a.text === '-') moveUnknown(`an earlier \`${name} -\` returns to a directory this command did not set`);
        else if (homeWord(a)) moveUnknown(`an earlier \`${name} ${a.raw}\` goes through HOME, and ${homeUnknownText()}`);
        else if (!a.literal) moveUnknown(`an earlier \`${name}\` names ${a.raw}, a directory the shell fills in when the command runs`);
        else {
          const to = resolveAgainst(a.text, unknownDir ? null : dir);
          if (to == null) moveUnknown(`an earlier \`${name}\` follows one I could not read`);
          else if (!enterable(to)) {
            // the shell stays put when a cd fails, so a relative write after it lands where the command started;
            // a directory the command makes first (`mkdir -p x && cd x`) is not there when the hook runs either
            // (round 3; the cost is stated in decision 47)
            dir = to;
            moveUnknown(`an earlier \`${name} ${a.raw}\` names a directory the command cannot enter when I check it (it may be made first, or the cd may fail and the write land where the command started)`);
          } else if (block) moveUnknown(block);   // the walk-around lens second pass: a clean move the guard cannot rely on
          else moveTo(to);
        }
        movedHere();
        if (a && a.literal && a.text !== '-') markFunctionBody();   // a real cd in a function body moves it when called
        break;
      }
      case 'popd': moveUnknown('an earlier `popd` returns to a directory this command did not set'); movedHere(); break;
      // `chdir` is cd's synonym in zsh and dash and no command in bash, and the guard does not know which shell runs the
      // line (the third pass): a cd it cannot know ran, family 6
      case 'chdir': setUnknown('an earlier `chdir` moves the shell in zsh and dash and fails in bash, so where the shell is after it is not known'); movedHere(); break;
      case 'cp': case 'mv': case 'install': case 'ln': {
        // copyTargets stats the destination to see whether it is a directory, so a stat error there (the walk-around lens second pass, family 4)
        // is an UnknownPath; attach the verb and the last operand's spelling for the refusal before it propagates.
        let r;
        try { r = copyTargets(args, unknownDir ? null : dir, name); }
        catch (e) {
          if (isUnknownPath(e) && !(e.why && e.why.how)) {
            const ops = args.filter((a) => !(a.text.startsWith('-') && a.text.length > 1));
            e.why = { ...(e.why || {}), how: name, raw: ops.length ? ops[ops.length - 1].raw : name };
          }
          throw e;
        }
        if (r.unknown) {
          // rule (f) (the third pass, 2026-09-19): the option is refused wherever the writer is reached, and since the
          // operands cannot be placed, each candidate word is recorded too, so an operand inside a tracked project is
          // judged by its own project from any cwd (before, `cp --targ <abs docs> <abs src>` from a cwd in no project was
          // dropped with the option word alone, and the copy landed on the tracked file).
          const why = { kind: 'unknownOption', option: r.unknown };
          cannotRead(word(r.unknown, false, r.unknown), name, why);
          for (const c of optionCandidates(args)) cannotRead(c, name, why);
        } else {
          for (const w of r.targets) add(w, name);
          if (name === 'ln') recordSymlink(args, unknownDir ? null : dir);   // class H: a symlink for a later word in the same command
        }
        break;
      }
      case 'link': {   // coreutils link(1): one hard link, made at the second operand (the third pass; the sibling of a hard `ln`)
        const ops = args.filter((a) => !(a.text.startsWith('-') && a.text.length > 1));
        if (ops.length >= 2) add(ops[1], 'link');
        break;
      }
      case 'tee':
        for (const a of args) if (!(a.text.startsWith('-') && a.text.length > 1)) add(a, 'tee');
        break;
      case 'dd':
        for (const a of args) if (a.text.startsWith('of=')) add(word(a.text.slice(3), a.literal, a.raw, { glob: a.glob, marks: a.marks && a.marks.slice(3) }), 'dd');
        break;
      case 'sponge': case 'truncate':
        for (let k = 0; k < args.length; k++) {
          const a = args[k];
          if (name === 'truncate' && (a.text === '-s' || a.text === '--size' || a.text === '-r' || a.text === '--reference')) { k++; continue; }
          if (a.text.startsWith('-') && a.text.length > 1) continue;
          add(a, name);
        }
        break;
      case 'sort':
        for (let k = 0; k < args.length; k++) {
          const t = args[k].text;
          if (t === '-o' || t === '--output') add(args[k + 1], 'sort -o');
          else if (t.startsWith('--output=')) add(sliceWord(args[k], 9), 'sort -o');
          else if (/^-o./.test(t)) add(sliceWord(args[k], 2), 'sort -o');   // the glued short form `-oFILE` (the walk-around lens second pass, family 1; shuf -o stays out of model, its writer contract)
        }
        break;
      case 'sed':
        for (const w of sedTargets(args)) add(w, 'sed -i');
        break;
      case 'perl':
        for (const w of perlTargets(args)) add(w, 'perl -i');
        break;
      case 'python': case 'node': {
        const kind = name;
        let inline = null;
        let stdin = true;   // no script operand: the script is on stdin (python3 <<EOF, python3 -u <<EOF)
        for (let k = 0; k < args.length; k++) {
          const a = args[k];
          // python's short options, read as a cluster the way python reads them (the pin addendum, 2026-09-19; before, `-c`
          // was matched at the END of a word, so `-c'CODE'`, `-uc'CODE'`, `-bc'CODE'` and `-Ic'CODE'`, the code glued
          // on, were skipped as unknown options and the write in the code was never scanned): `c` and `m` take the rest of
          // the word or the next word, `W` and `X` a value the same way, every other letter is a flag
          if (kind === 'python' && a.literal && /^-[^-]/.test(a.text)) {
            let seen = null;
            for (let j = 1; j < a.text.length; j++) {
              const ch = a.text[j];
              if (ch === 'c') { inline = j < a.text.length - 1 ? sliceWord(a, j + 1) : (args[k + 1] || null); seen = 'c'; break; }
              if (ch === 'm') { seen = 'm'; break; }   // a module: its code is not in the command
              if (ch === 'W' || ch === 'X') { if (j === a.text.length - 1) k++; break; }
            }
            if (seen) { stdin = false; break; }
            continue;
          }
          // node's code takes the next word after -e, --eval, -p, --print or the cluster -pe, or is glued with `=` to --eval
          // (the pin addendum: `--eval='CODE'` was skipped as an unknown option); `--print=X` takes no code, node then reads
          // the script from stdin (measured on node 22), so it stays a flag and a heredoc after it is the script
          if (kind === 'node' && (a.text === '-e' || a.text === '--eval' || a.text === '-p' || a.text === '--print' || a.text === '-pe')) { inline = args[k + 1] || null; stdin = false; break; }
          if (kind === 'node' && a.literal && /^--eval=/.test(a.text)) { inline = sliceWord(a, 7); stdin = false; break; }
          if (a.text === '-') break;   // stdin, said so
          if (INTERPRETER_OPERANDS[kind].has(a.text)) { k++; continue; }
          if (a.text.startsWith('-')) continue;
          stdin = false;   // a script file: its contents are not in the command
          break;
        }
        // a literal path is judged by its name whatever it holds; a template or format string is a target the hook can
        // see and cannot read, refused while a project is in play (M4); a computed path stays out of model (the contract)
        const scan = (text) => {
          const r = scanScript(kind, text);
          for (const p of r.literal) add(word(p, true, p), `${kind} script`);
          for (const tpl of r.template) cannotRead(word(tpl, false, tpl, { marks: 'x'.repeat(tpl.length) }), `${kind} script`, { kind: 'templatePath' });
        };
        if (inline) {
          if (inline.literal) scan(inline.text);
          else sawOpaqueCommand = true;
        } else if (stdin) {
          for (const body of stdinBodies(idx)) scan(body);
        }
        break;
      }
      case 'eval': case 'xargs': sawOpaqueCommand = true; break;
      default:
        if (SHELLS.has(name)) {
          // the script is read as the shell named reads it (`$'...'` is quoting under bash and zsh only; the
          // options a cluster takes a word for differ; shellScript and lex)
          const sh = shellScript(args, name);
          if ('script' in sh) {
            if (sh.script && sh.script.literal) recurse(sh.script.text, name);
            else if (sh.script) sawOpaqueCommand = true;
          } else if (sh.stdin) {
            for (const body of stdinBodies(idx)) recurse(body, name);   // bash <<'EOF' ... EOF: the body is the script
          }
        }
    }
    if (chdirSaved) ({ dir, unknownDir, unknownWhy } = chdirSaved);   // env -C / sudo -D moved the cwd for this command only
    // the walk-around lens second pass (family 3): record a remove/rename/link this segment made AFTER judging its own targets, so it changes
    // the reading of LATER segments only, never this command's own write
    recordMutations(name, args, unknownDir ? null : dir);
    }
    recordSegment(seg, idx, cmd, preWords);   // B2 and the readability rule: this segment's writes hold for the segments after it
  }
  activeLinks = prevLinks;
  // `links` (class H) are returned so evaluate can follow them while it places the targets the hook could not read (M3):
  // a numeric target's literal directory part is folded through a link the same command makes before it, as the kernel
  // will follow it once it exists (`ln -s <proj>/notes <out>/d && echo x > <out>/d/x-$$.md` landed in the tracked folder
  // while the numeric view resolved `<out>/d` through a filesystem where the link did not yet exist).
  return { targets, opaque: opaque || sawOpaqueCommand, unresolved, links };
}

// ── the verdict ─────────────────────────────────────────────────────

// One command's targets share one memo, keyed by the Map of link closures evaluate creates for
// the call (the Map is the call's identity; the tests hold one too): the project root per
// directory, the two config lists per root and the real path per directory, each read once per
// call however many landing files a directory copy names (twenty thousand landing files judged
// with a config read and a root search each took seconds; with the memo, a stat or two per file).
// `activeMemo` is the memo of the isGuardedPath call under way (synchronous, so never two at
// once); trackedPaths and untrackedPaths below are store-io's readers behind it, so trackedIn
// reads as isTrackedFile does.
const memos = new WeakMap();
let activeMemo = null;
const newMemo = (closures) => ({ closures, roots: new Map(), configs: new Map(), realDirs: new Map() });
function memoFor(closures) {
  if (!closures) return newMemo(new Map());
  let m = memos.get(closures);
  if (!m) { m = newMemo(closures); memos.set(closures, m); }
  return m;
}
// The two lists of `root`'s config. A config.json that exists but cannot be read (its folder or the file mode 000,
// or a body that does not parse) is an UnknownPath, refused for every write under that root: store-io answers an
// empty list for it, the vendored guard's posture (a guard that cannot read the config denies nothing), and the walk-around lens second pass
// (2026-09-19) measured `chmod 755 .trackchanges && cp base/report.md docs/report.md` with `.trackchanges` mode 000 at
// check time overwriting the tracked file through that answer. A config that is not there (ENOENT) tracks nothing.
function readConfigChecked(root) {
  const cfg = path.join(root, '.trackchanges', 'config.json');
  let present = true;
  try { fs.accessSync(cfg, fs.constants.R_OK); }
  catch (e) { if (e && e.code === 'ENOENT') present = false; else throw new UnknownPath((e && e.code) || 'EACCES', cfg, { kind: 'config', root }); }
  const tracked = readTrackedPaths(root);
  const untracked = readUntrackedPaths(root);
  if (present) {
    let parsed = null;
    try { parsed = JSON.parse(fs.readFileSync(cfg, 'utf8')); } catch (e) { throw new UnknownPath((e && e.code) || 'EINVAL', cfg, { kind: 'config', root }); }
    if (!parsed || typeof parsed !== 'object') throw new UnknownPath('EINVAL', cfg, { kind: 'config', root });
  }
  return { tracked, untracked };
}
function configOf(root) {
  const m = activeMemo;
  if (!m) return readConfigChecked(root);
  let c = m.configs.get(root);
  if (!c) { c = readConfigChecked(root); m.configs.set(root, c); }
  return c;
}
function trackedPaths(root) { return configOf(root).tracked; }
function untrackedPaths(root) { return configOf(root).untracked; }
function rootOf(file) {
  if (process.env.TRACKCHANGES_ROOT) return process.env.TRACKCHANGES_ROOT;
  const m = activeMemo;
  const dir = path.dirname(file);
  if (m && m.roots.has(dir)) return m.roots.get(dir);
  const root = findVaultRoot(file);
  if (m) m.roots.set(dir, root);
  return root;
}

// store-io's isTrackedFile, with the link closure (its one costly step: a walk of every .md
// under the root and a read of every tracked note) built once per root per call and kept in
// `closures`, a Map the caller holds for the call. The three steps and their order are
// isTrackedFile's own: the veto list wins, then the explicit list by name (an exact entry or a
// `dir/` prefix, which also covers a file that does not exist yet), then the closure.
// tools/romp-track-bash-guard-shapes.test.mjs pins isTrackedFile's body to these steps, so a
// vendored bump that changes them fails there by name.
function trackedIn(root, file, closures) {
  const rel = relPathFor(root, file);
  if (engine.isTracked(untrackedPaths(root), rel)) return false;
  const list = trackedPaths(root);
  if (engine.isTracked(list, rel)) return true;
  if (!list.length) return false;
  let closure = closures.get(root);
  if (!closure) { closure = trackedClosure(root); closures.set(root, closure); }
  return closure.has(rel);
}

// The path the kernel opens for `file`: every symlink in it resolved (the native realpath, which
// also reports each name as the filesystem spells it), for a file that need not exist yet: its
// directory's real path (memoised per call) with the name appended, and a dangling link followed
// to where its target would be. null when nothing of the path exists. One lstat for an absent
// file, one more realpath for one that exists.
// No exception for an absent file (ENOENT is null); any other failure (EACCES on a parent, ELOOP, ENOTDIR) is an
// UnknownPath the caller refuses (the walk-around lens second pass, 2026-09-19; before, it unwound to a catch that read it as allow).
const lstatOrNull = (file) => {
  try { return fs.lstatSync(file, { throwIfNoEntry: false }) || null; }
  catch (e) { if (e && e.code === 'ENOENT') return null; throw new UnknownPath((e && e.code) || 'EACCES', file); }
};
function realPathOf(file, depth = 0, st = lstatOrNull(file)) {
  if (st) {
    // a dangling link is followed to where its target would be (ENOENT). A NON-symlink whose realpath fails for any
    // other reason (a component the process may not search, a file where a directory is needed) is an UnknownPath the
    // caller refuses (the walk-around lens second pass); a symlink falls through to the readlink walk below, so a link that loops resolves to
    // null through the depth cap (unresolvable, its existing wording), never a thrown error.
    try { return fs.realpathSync.native(file); }
    catch (e) { if (!st.isSymbolicLink() && e && e.code !== 'ENOENT') throw new UnknownPath(e.code, file); }
    if (!st.isSymbolicLink() || depth >= 40) return null;
    let target;
    try { target = path.resolve(path.dirname(file), fs.readlinkSync(file)); } catch { return null; }
    return realPathOf(target, depth + 1);
  }
  const dir = path.dirname(file);
  if (dir === file) return null;
  const m = activeMemo;
  let realDir = m ? m.realDirs.get(dir) : undefined;
  if (realDir === undefined) { realDir = realPathOf(dir, depth); if (m) m.realDirs.set(dir, realDir); }
  return realDir == null ? null : path.join(realDir, path.basename(file));
}

// Whether `file`, an absolute path, is a tracked TEXT file of its project by that name: a
// directory, a non-text file by name, a file outside any project, an untracked file, and a
// tracked binary under a text-looking name all answer false; so does any error (the vendored
// guard's posture: a guard that cannot read the config denies nothing). `st` is the file's lstat,
// or null for a file that does not exist yet (which may still be tracked by folder).
function guardedByName(file, closures, st = lstatOrNull(file)) {
  if (isNonTextPath(file)) return false;
  if (st && (st.isDirectory() || (st.isSymbolicLink() && (fs.statSync(file, { throwIfNoEntry: false }) || st).isDirectory()))) return false;
  const root = rootOf(file);
  if (!root) return false;
  if (!(closures ? trackedIn(root, file, closures) : isTrackedFile(root, file))) {
    // the walk-around lens second pass (2026-09-19, family 5): the nearest marker is not the only one. A `.git`, `.obsidian` or `.trackchanges`
    // made between a tracked project's root and the file (`mkdir docs/.git`, an empty `notes/.trackchanges`) makes the
    // folder its own config-less root to store-io's nearest-marker search, and every write under it read as untracked
    // while the outer list still names the file. Which project's rules apply is not known, so the write is refused,
    // naming both markers; a file the outer list does not name, and the untracked case, keep the nearest root's answer.
    if (!process.env.TRACKCHANGES_ROOT) {
      const outer = outerTrackingRoot(root, file, closures);
      if (outer) throw new UnknownPath('EMARKER', file, { kind: 'nestedMarker', outer, inner: root, marker: markerAt(root) });
    }
    return false;
  }
  if (hasNulBytes(file)) return false;
  return true;
}
// The root marker store-io found `root` by (its own order), for the nested-marker refusal.
function markerAt(root) {
  for (const m of ['.obsidian', '.git', '.trackchanges']) { try { if (fs.existsSync(path.join(root, m))) return m; } catch { /* unreadable: the next */ } }
  return '.trackchanges';
}
// The nearest root ABOVE `inner` whose list names `file` (by name, the folder prefix or the link closure), or null.
function outerTrackingRoot(inner, file, closures) {
  let dir = path.dirname(inner);
  for (let i = 0; i < 40 && dir !== path.dirname(dir); i++) {
    const r = findVaultRoot(path.join(dir, 'x'));   // findVaultRoot starts at the parent of the path given
    if (!r) return null;
    if (closures ? trackedIn(r, file, closures) : isTrackedFile(r, file)) return r;
    dir = path.dirname(r);
  }
  return null;
}

// Whether a write to `file` (an absolute path) lands on a tracked text file: under the name given,
// or under the name the kernel opens for it (realPathOf), so a symlink to a tracked file, inside
// or outside its project, does not carry a write past the guard. The name given is judged first,
// so a tracked file that is itself a link out of its project stays guarded. `closures` (optional)
// is the per-call Map evaluate passes so that one command's targets share one closure per root
// and one memo (above); without it the answer comes from store-io's isTrackedFile directly.
export function isGuardedPath(file, closures) {
  const prev = activeMemo;
  activeMemo = memoFor(closures);
  try {
    const st = lstatOrNull(file);
    if (guardedByName(file, closures, st)) return true;
    const real = realPathOf(file, 0, st);
    return real != null && real !== file && guardedByName(real, closures);
  } catch (e) {
    if (isUnknownPath(e)) throw e;   // the walk-around lens second pass: an answer the hook does not have is the caller's to refuse, never a false
    return false;
  } finally { activeMemo = prev; }
}

// ── a target the hook could not read: which project is in play ─────
//
// The pieces below decide whether a non-literal write target is refused (the header). They run
// outside isGuardedPath's memo, so `memo` ({ closures, roots }) is the per-call store evaluate
// hands them: the link closure per root shared with the literal verdicts, and the answer per
// directory, so a command with several such targets reads each config once.

// Whether `p` lies outside `root` (both absolute): not the root itself and not under it.
function outside(p, root) {
  const rel = path.relative(root, p);
  return rel === '..' || rel.startsWith('..' + path.sep) || path.isAbsolute(rel);
}

// A tracked entry the literal rule could refuse: a text name that the veto list does not cover. A
// non-text entry (a tracked figure) passes by name, and a vetoed one never counts, so a project
// whose list holds only those is not in play (review round 1, 2026-09-18: a figures-only and a
// veto-all project refused every non-literal write with a message whose premise no literal write
// there could meet). The list is read once per root, not once per entry.
const refusableEntry = (off) => (raw) => {
  if (typeof raw !== 'string' || !raw) return false;
  const e = raw.replace(/^\.?\//, '');
  return !isNonTextPath(e) && !engine.isTracked(off, e);
};
const closureFor = (root, memo) => {
  let closure = memo.closures.get(root);
  if (!closure) { closure = trackedClosure(root); memo.closures.set(root, closure); }
  return closure;
};
// Whether `root` tracks something the literal rule could refuse: a refusable entry on its list, or,
// when every listed entry is a figure or vetoed, a note the link closure reaches from one (a tracked
// image can carry a whole-line link to a tracked note; the closure excludes vetoed notes itself).
function tracksRefusable(root, memo) {
  if (memo.refusable.has(root)) return memo.refusable.get(root);
  let ok = false;
  const cfg = readConfigChecked(root);
  const list = cfg.tracked;
  if (list.length) {
    const live = refusableEntry(cfg.untracked);
    ok = list.some(live);
    if (!ok) for (const rel of closureFor(root, memo)) if (live(rel)) { ok = true; break; }
  }
  memo.refusable.set(root, ok);
  return ok;
}

// The project that tracks something refusable at `dir` (a directory), as { root, dir, fromEnv }, or
// null. `dir` is judged under its real path first (every symlink resolved, as realPathOf resolves
// a target's) and then under its lexical name, the first project found winning, the way the
// literal rule judges a target under both names (review round 1, 2026-09-18: the lexical search
// alone let `cp "$SRC" link/` pass where link led into a tracked project's folder, while the same
// copy spelled out was refused; the real path alone would have flipped two correct refusals, a
// folder under a tracked `docs/` that links out and a cwd that is such a link, to allow). `fromEnv`
// says the root is TRACKCHANGES_ROOT's, which stands in for the marker search only for a directory
// under it (before round 1 it answered for every directory on the machine, so with it set every
// non-literal write anywhere was refused, and its value was echoed in the refusal); outside it the
// marker search runs. That is a chosen asymmetry with the literal rule, whose rootOf sends every
// file to the env root as the vendored guard does: a second tracked project's non-literal writes are
// refused under the fallback while its literal ones are judged against the env root. The loud
// answer was preferred to returning null, which would let those writes pass unjudged. The caller
// never prints an env root: a value read from the environment stays out of every message.
function trackingRootAt(dir, memo) {
  if (!dir) return null;
  if (memo.roots.has(dir)) return memo.roots.get(dir);
  let hit = null;
  checkSearchable(dir);   // the walk-around lens second pass: a directory the hook may not search is an UnknownPath, not a directory in no project
  const real = realPathOf(dir);
  const env = process.env.TRACKCHANGES_ROOT ? path.resolve(process.env.TRACKCHANGES_ROOT) : null;
  for (const d of real && real !== dir ? [real, dir] : [dir]) {
    const fromEnv = !!env && !outside(d, env);
    let root = fromEnv ? env : findVaultRoot(path.join(d, 'x'));   // findVaultRoot starts at the parent of the path given
    // the walk-around lens second pass (family 5): a nearest root that tracks nothing refusable (a nested `.git`, an empty `.trackchanges`) may
    // sit inside a project that does; a word the hook cannot read under it is judged by that outer project, as class F
    // judges any expansion under a tracked root (its value can carry a `../` into the tracked files)
    while (root && !fromEnv && !tracksRefusable(root, memo)) {
      const up = path.dirname(root);
      root = up === root ? null : findVaultRoot(path.join(up, 'x'));
    }
    if (root && tracksRefusable(root, memo)) { hit = { root, dir: d, fromEnv }; break; }
  }
  memo.roots.set(dir, hit);
  return hit;
}

// Whether a write whose NAME the hook cannot read could land on a tracked file when it lands in
// `hit.dir`, a folder of `hit.root`: a refusable tracked entry at or below the folder (a file under it,
// or a folder entry that holds it or sits in it), an existing entry of the folder that is already
// guarded (isGuardedPath: a tracked file by name, or a link onto one, whose name the write could take),
// or a note under the folder that the link closure reaches. Asked for a copy's landing folder and for
// the literal directory part of a target the hook can place (the own-project step of inPlayFor), so it
// is folder-granular: a numeric FILE name in a folder that holds a tracked file by name
// (`<root>/docs/build-$$.log`) is refused from any cwd while its literal spelling passes, a deliberate
// false refusal stated in decision 47 (round 3; a name-aware gate was weighed and not built: it would
// narrow a write guard's refusal on a pattern match, with no name to match past the cap below). The
// readdir is bounded: past LANDING_SCAN_CAP entries the folder is taken as in play rather than scanned
// (review round 1, 2026-09-18: the branch refused every copy into any folder of a project that tracks
// anything, from every cwd; the refuters' narrowing by tracked entries alone let `cp "$SRC" outbox/`
// pass where outbox/report.md linked to the tracked file, and the copy then overwrote it, so the
// folder's own entries are asked too). The cap is a deliberate false refusal, stated in decision 47 and
// escalated with the PR rather than hidden (review round 2, 2026-09-18): a copy whose landing name the
// hook cannot read, or a numeric name (round 3, when the own-project step put that class under the same
// gate), is refused in any folder of a tracked project over 2000 entries, even when nothing tracked
// could land there, with the generic refusal text. Both sides of the boundary are pinned by execution
// (tools/romp-track-bash-guard.test.mjs, the caps test), so the number can be chosen rather than
// inherited; the round measured the scan it avoids at about 30 microseconds per entry, against the
// installer's 10 s hook timeout.
const LANDING_SCAN_CAP = 2000;
function landingInPlay(hit, memo) {
  const { root, dir } = hit;
  const rel = relPathFor(root, dir).replace(/^\.?\//, '').replace(/\/+$/, '');
  const folder = rel === '' ? '' : rel + '/';
  const cfg = readConfigChecked(root);
  const live = refusableEntry(cfg.untracked);
  for (const raw of cfg.tracked) {
    if (!live(raw)) continue;
    const e = raw.replace(/^\.?\//, '');
    if (e.startsWith(folder)) return true;                        // an entry at or below the landing folder
    if (e.endsWith('/') && folder.startsWith(e)) return true;     // the landing folder sits in a tracked folder
  }
  const names = readdirOrNull(dir);   // absent: nothing there to take the name of; unreadable: an UnknownPath (the walk-around lens second pass)
  if (names) {
    if (names.length > LANDING_SCAN_CAP) return true;
    for (const n of names) if (isGuardedPath(path.join(dir, n), memo.closures)) return true;
  }
  for (const r of closureFor(root, memo)) if (r.startsWith(folder) && live(r)) return true;
  return false;
}

// With no project above a copy's landing folder, the entry there, if any, that is or leads to a tracked
// file (a link into a project; a folder under the environment root), whose name a copy the hook cannot
// read could take and the kernel would follow: as { root, dir, fromEnv, guardedEntry }, the root that of
// the file the entry leads to, so the refusal names the tree the write reaches (round 3: `cp "$SRC"
// <outside>/` over <outside>/report.md, a link onto a tracked file, overwrote it while the same copy
// spelled out was refused, since trackingRootAt answered null for the folder and nothing else was asked;
// the same when the folder sits under a project whose list holds nothing refusable, or under a bare
// repository root). Bounded by LANDING_SCAN_CAP: past it a folder that no project claims is NOT taken as
// in play, the opposite of landingInPlay's default, since refusing every unreadable copy into any large
// folder on the machine would be the round-1 false refusal an order of magnitude wider; that residual is
// stated with the PR.
function guardedEntryIn(dir, memo) {
  const names = readdirOrNull(dir);
  if (!names || names.length > LANDING_SCAN_CAP) return null;
  const env = process.env.TRACKCHANGES_ROOT ? path.resolve(process.env.TRACKCHANGES_ROOT) : null;
  for (const n of names) {
    const entry = path.join(dir, n);
    if (!isGuardedPath(entry, memo.closures)) continue;
    const root = env || findVaultRoot(realPathOf(entry) || entry);
    if (root) return { root, dir, fromEnv: !!env, guardedEntry: n };
  }
  return null;
}

// Whether the expansion segment `seg` ({ t, m }) could spell `name`: each run of expansion characters stands
// for a run of digits (the process id), every other character, a literal dollar included whatever its
// quoting, for itself (round 3: every dollar-shaped run was a run of digits, so a project whose root was
// named `p$x` read as diverging from a target inside it, and a numeric write into its tracked folder was
// allowed while the literal spelling was refused).
function couldSpell(seg, name) {
  let re = '';
  for (let i = 0; i < seg.t.length; i++) {
    if (seg.m && seg.m[i] === 'x') { if (i === 0 || seg.m[i - 1] !== 'x') re += '\\d+'; continue; }
    re += escapeRe(seg.t[i]);
  }
  return new RegExp(`^${re}$`).test(name);
}

// How a numeric-only target reads, once placed: `segs`, its path's segments folded as the kernel would open
// them (foldSegments, after a relative spelling is resolved against the write-time directory); `idx`, the
// first segment still holding an expansion (-1 when a `..` folded every expansion away, and then `literal`
// is the path); `dir`, the literal directory part before it, as spelled; `folder`, that segment's typed text
// when the expansion names a folder rather than the file; and `candidates`, the entries that exist now whose
// names the process id could spell, each followed as the write would follow it (spelledCandidates). null
// when a relative target's directory is not known (the cwd rule then refuses it unnarrowed); { emptiable }
// or { unresolvable } from the fold.
function numericView(u, memo) {
  if (u.view !== undefined) return u.view;
  let segs = segmentsOf(u.text, u.marks);
  if (!path.isAbsolute(u.text)) {
    if (!u.dir) return (u.view = null);
    segs = [...segmentsOf(u.dir, null), ...segs];
  }
  const folded = foldSegments(segs);
  if (folded.emptiable || folded.unresolvable) return (u.view = { emptiable: !!folded.emptiable, unresolvable: folded.unresolvable || null, candidates: [] });
  return (u.view = viewOf(folded.segs, memo, { left: LANDING_SCAN_CAP }));
}
function viewOf(segs, memo, budget) {
  const text = joinSegments(segs);
  const idx = segs.findIndex(isExpansion);
  if (idx < 0) return { segs, text, literal: text, idx, dir: path.dirname(text), folder: null, candidates: [] };
  const dir = idx === 0 ? '/' : joinSegments(segs.slice(0, idx));
  const folder = idx < segs.length - 1 ? segs[idx].t : null;
  return { segs, text, literal: null, idx, dir, folder, candidates: spelledCandidates(segs, idx, dir, memo, budget) };
}
// The entries of `dir` (under its real path) that exist now and whose names the expansion segment could
// spell, each as the view of the path with that name in the segment's place, the tail folded under the
// entry's real path (a link there leads where the kernel goes), and a later expansion segment spelled the
// same way, flattened; bounded by LANDING_SCAN_CAP entries per listing and by `budget` in all (round 3: a
// link made before the command, `<out>/ld-0` onto a tracked folder, was never resolved when `<out>/ld-$SECONDS`
// named it; with the set now the process id alone the entry is one the pid could spell). A listing past the
// cap, or one that fails, yields no candidates: for a folder inside a tracked project landingInPlay has
// already refused at the cap, and for one outside every project the header states why the scan is open.
function spelledCandidates(segs, idx, dir, memo, budget) {
  const out = [];
  const realDir = realPathOf(dir) || dir;
  const names = readdirOrNull(realDir);
  if (!names || names.length > LANDING_SCAN_CAP) return out;
  const seg = segs[idx];
  const tail = segs.slice(idx + 1);
  for (const n of names) {
    if (!couldSpell(seg, n)) continue;
    if (--budget.left < 0) return out;
    const entry = path.join(realDir, n);
    const folded = foldSegments([...segmentsOf(realPathOf(entry) || entry, null), ...tail]);
    if (folded.emptiable || folded.unresolvable) continue;
    const v = viewOf(folded.segs, memo, budget);
    out.push(v, ...v.candidates);
  }
  return out;
}

// Whether a numeric-only target (`view`) lands outside `root` for certain: under its folded spelling, under
// the spelling with its literal directory part resolved (`/tmp/link/x-$$.md` where link leads into the
// project), and under every entry that exists now that the process id could spell, each compared with the
// root's segments (a target segment holding an expansion could spell the root's own when its literal pieces
// fit around a run of digits, `/tmp/build-$$/x.md` against a project at /tmp/build-4242, so that one is not
// taken as diverging; one whose literal pieces cannot fit diverges, as a literal segment that differs does)
// and with the root's real path as well as its name.
function numericOutside(view, root) {
  const diverges = (ps, r) => {
    const rs = r.split('/').filter(Boolean);
    for (let i = 0; i < rs.length; i++) {
      if (i >= ps.length) return true;                                  // the target sits above the root
      if (isExpansion(ps[i])) { if (couldSpell(ps[i], rs[i])) return false; return true; }
      if (ps[i].t !== rs[i]) return true;
    }
    return false;   // every root segment matched: the root itself, or under it
  };
  const realRoot = realPathOf(root) || root;
  const spellings = [view.segs];
  const realDir = realPathOf(view.dir);
  if (realDir != null && realDir !== view.dir) spellings.push([...segmentsOf(realDir, null), ...view.segs.slice(view.idx < 0 ? view.segs.length - 1 : view.idx)]);
  for (const c of view.candidates) spellings.push(c.segs);
  return spellings.every((ps) => [root, realRoot].every((r) => diverges(ps, r)));
}

// The project a target the hook cannot read would land in, asked before the cwd's (round 2 for a numeric
// target, round 3 for every such target and for a relative spelling; the header): for a numeric target, its
// view's literal directory part, then each entry the process id could spell; a fold that leaves no expansion
// is handed to the literal rule first (`{ literal }`: round 3, a fold onto a link to a tracked file was
// allowed while its literal spelling was refused). For a word with an expansion the hook does not read, the
// literal text before its first expansion names the folder the write lands in or one above it, never one
// below (an expansion can only add segments or climb), so asking that folder's project errs toward
// refusing, never toward allowing; a word whose reading is ambiguous as a whole (no expansion mark: `$'...'`
// under sh, `$"..."`) is asked by its whole text. Returns a hit ({ root, dir, fromEnv }, with `unknownFolder`
// when the expansion names a folder, `literal` for the literal rule's answer), or null.
function ownProjectFor(u, memo) {
  if (u.numeric != null) {
    const view = numericView(u, memo);
    if (!view || view.emptiable || view.unresolvable) return null;
    for (const v of [view, ...view.candidates]) {
      if (v.literal != null && isGuardedPath(v.literal, memo.closures)) return { literal: v.literal };
      const own = trackingRootAt(v.dir, memo);
      if (own && landingInPlay(own, memo)) return v.folder ? { ...own, unknownFolder: v.folder, carried: path.isAbsolute(u.text) && v.text.startsWith(own.root + '/') } : own;
    }
    return null;
  }
  if (!u.marks) return null;
  const exp = u.marks.indexOf('x');
  const prefix = exp < 0 ? u.text : u.text.slice(0, exp);
  const cut = prefix.lastIndexOf('/');
  let dirText = cut < 0 ? '' : prefix.slice(0, cut + 1);
  const segPrefix = cut < 0 ? prefix : prefix.slice(cut + 1);   // the literal head of the segment the first expansion sits in
  if (!path.isAbsolute(dirText)) { if (!u.dir) return null; dirText = u.dir + '/' + dirText; }
  const folded = foldSegments(segmentsOf(dirText, null));
  if (!folded.segs) return null;
  const D = joinSegments(folded.segs);
  const own = trackingRootAt(D, memo);
  // class F (round 4, 2026-09-19): D is under a tracked root. A non-literal expansion below it can carry a `../`
  // back into the project's tracked files (measured: `v='../notes/seed'; > <tgt>/scratch/$v.md` overwrote the
  // tracked note), so the write is refused whether or not a tracked file could land in D directly; before, the
  // landing-folder gate let an untracked subfolder of a tracked project pass.
  if (own) return own;
  // class E (round 4, 2026-09-19): D is not under a tracked root, but it is a PARENT of one or more, and the
  // expansion right after D could spell a root's name (its literal head is a prefix of the root's), so the write
  // could land in a project (measured: `abc='$abc'; > BASE/roots/p$abc/docs/report.md` from a cwd in no project).
  // Only when D sits under no project at all: when D is itself under a project (a non-refusable one, so `own` is
  // null), the cwd rule already decides and this listing would be spent per call for nothing.
  // B2 as ruled (the reviewer's option (c), 2026-09-19): when D is under no project and parents no root, the word keeps
  // the cwd rule whatever follows D. Every value the guard can read was resolved in extract, so an expansion left here is
  // opaque, and a `..` inside its value could climb from D into a project; the refusal of that case (the dropped half of
  // B2, fork PR #780's cb0b15422) fired only from a cwd in no project, where the guard is furthest from its subject, and is
  // not built: the residual is stated on the four surfaces with its boundary (from a tracked cwd the same word is refused
  // as not literal by the cwd rule, as before B2).
  if (process.env.TRACKCHANGES_ROOT || findVaultRoot(path.join(D, 'x'))) return null;
  return parentTrackedRoots(D, segPrefix, memo);
}

// The tracked projects that sit UNDER `dir` at ANY depth and whose path the expansion after `dir` could spell (class E;
// rule (e) of the walk-around lens third pass, 2026-09-19: round 4 listed the direct children only, and `x=f/notes-api;
// cp <src> ../../$x/docs/report.md` from a cwd in no project spelled two segments and reached a root one level down
// unseen). The first segment under `dir` must start with the expansion's literal head `segPrefix`; below that the
// expansion can spell anything. The walk is breadth-first, so a root close to `dir` is found before a deep tree spends
// the budget; a symbolic link is asked whether it is a root and not descended; a directory the hook cannot list is
// skipped (this walk judges no path of the write itself, so an error here is not family 4's); it is bounded by
// PARENT_SCAN_BUDGET entries in all and LANDING_SCAN_CAP per listing, past which the rest is not scanned (open there,
// as the outside-folder scans are, and stated with the change). Returns { root, dir, fromEnv, parentOf: [absolute
// roots] }, or null.
const PARENT_SCAN_BUDGET = 20000;
function parentTrackedRoots(dir, segPrefix, memo) {
  const names = readdirOrNull(dir);
  if (!names || names.length > LANDING_SCAN_CAP) return null;
  const env = process.env.TRACKCHANGES_ROOT ? path.resolve(process.env.TRACKCHANGES_ROOT) : null;
  const found = [];
  let root = null;
  let fromEnv = false;
  let budget = PARENT_SCAN_BUDGET - names.length;
  const rootAt = (d) => {
    const r = env && !outside(d, env) ? env : findVaultRoot(path.join(d, 'x'));   // findVaultRoot starts at the parent of the path given
    return r && r === d && tracksRefusable(r, memo) ? r : null;
  };
  const take = (d, r) => { found.push(d); if (!root) { root = r; fromEnv = !!env && !outside(d, env); } };
  let level = [];
  for (const n of names) if (!segPrefix || n.startsWith(segPrefix)) level.push(path.join(dir, n));   // the expansion cannot spell the others
  while (level.length && budget > 0) {
    const next = [];
    for (const d of level) {
      let st;
      try { st = fs.lstatSync(d); } catch { continue; }
      if (st.isSymbolicLink()) {
        let isDir = false;
        try { isDir = fs.statSync(d).isDirectory(); } catch { continue; }
        if (isDir) { const r = rootAt(d); if (r) take(d, r); }   // a link to a project counts; a link is not descended
        continue;
      }
      if (!st.isDirectory()) continue;
      const r = rootAt(d);
      if (r) { take(d, r); continue; }   // a root's inside is that project's own class F
      let sub;
      try { sub = fs.readdirSync(d); } catch { continue; }
      if (sub.length > LANDING_SCAN_CAP) continue;
      budget -= sub.length;
      if (budget <= 0) break;
      for (const n of sub) next.push(path.join(d, n));
    }
    level = next;
  }
  return found.length ? { root, dir, fromEnv, parentOf: found } : null;
}

// The tracked project in play for a write target the hook could not read, as { root, dir, fromEnv }, or
// null. A copy into a literal folder lands there whatever the name (`at`), so that folder decides and
// the cwd does not: its project must track something refusable and the folder must be one such a
// landing could reach (landingInPlay), or, with no such project above it, an entry of it must be or
// lead to a tracked file (guardedEntryIn). Any other such target is asked about the project its own
// literal directory part sits in first (ownProjectFor), from any cwd: the narrowing measured a numeric
// target against the roots the cwd and a `cd` derive only, so a numeric write into a SECOND tracked project
// was dropped while its literal spelling was refused (round 2; two refuters overwrote a tracked note that
// way, from a cwd in another project and from a cwd in none), and the same held for a variable's spelling
// and for a relative numeric one until round 3. Then the directory current at the write and the session's
// cwd both count, the first under a project that tracks something refusable; except that a target whose
// only expansions are numeric is dropped when it lands outside every project the two directories derive
// (numericOutside), and, when refused, names the folder the expansion stands for when it stands for one
// (`unknownFolder`: the refusal then says the folder's name is what is not known, wherever the target is
// refused, since the reason is the same at every depth; round 2's addendum ruled the text for the first
// segment, round 3 gave it to the class). A fully opaque target (`"$(mktemp)"`, `"$F"`) and one with a
// variable of unknown content beside the numbers stay refused: nothing about them bounds where the write
// lands, and a `../` inside a variable reached a tracked file when a refuter tried the general
// literal-prefix rule (review round 1, 2026-09-18). Of the session's environment this reads only
// TRACKCHANGES_ROOT (trackingRootAt); no variable named in the command is ever read.
function inPlayFor(u, cwd, memo) {
  if (u.at) {
    const hit = trackingRootAt(u.at, memo);
    if (hit) return landingInPlay(hit, memo) ? hit : null;
    return guardedEntryIn(u.at, memo);
  }
  const own = ownProjectFor(u, memo);
  if (own) return own;
  const hits = [];
  for (const d of [u.dir, cwd]) {
    const hit = trackingRootAt(d, memo);
    if (hit && !hits.some((h) => h.root === hit.root)) hits.push(hit);
  }
  if (!hits.length) return null;
  if (u.numeric != null) {
    const view = numericView(u, memo);
    if (view && !view.emptiable && !view.unresolvable) {
      // the drop needs an absolute spelling: a relative numeric target is measured against its own project above
      // (the refuse direction, round 3) and stays refused here even when the write-time directory is known and
      // outside every project in play, a documented false refusal (round 2 declined to trade it for an allowance
      // that would rest on the write-time directory; docs/install.md states it)
      if (path.isAbsolute(u.text) && hits.every((h) => numericOutside(view, h.root))) return null;
      if (view.folder) return { ...hits[0], unknownFolder: view.folder, carried: path.isAbsolute(u.text) && view.text.startsWith(hits[0].root + '/') };
    }
  }
  return hits[0];
}

// The remedy line is read by a person and PASTED into bash or zsh (the fifth commit, 2026-09-19, M6): the fourth pass's
// matrix found 576 refusals whose `--file "<path>"` held a shell-live `$` inside the double quotes (a project at `p$42`),
// so the pasted line named another file in bash (`p2`) and a third in zsh (`p`). The argument is single-quoted, where
// nothing expands; a single quote inside the path closes the quote, escapes itself and reopens (`'\''`), the spelling
// the kernel's file-comments messages use. Pinned by a test that runs the pasted line through real bash and real zsh.
const shellQuote = (s) => `'${String(s).replace(/'/g, `'\\''`)}'`;
const trackEditLine = (file) => `  node ~/.claude/hooks/track-edit.mjs --file ${shellQuote(file)} --old '<exact unique text>' --new '<replacement>'`;
const TRACK_EDIT = trackEditLine('<the file>');

// The walk-around lens second pass (2026-09-19): a filesystem error other than ENOENT on a path the hook judges
// (an lstat, realpath, readdir or config read that fails with EACCES, ELOOP, ENOTDIR, EINVAL and the rest) is an
// answer the hook does not have, so it REFUSES, naming the error and the entry that blocked the check, from any cwd
// (the blocked directory may itself be a tracked project). `how` is the writing construct, `raw` the word as typed.
function statErrorRefusal(how, raw, e) {
  if (e.why && e.why.kind === 'nestedMarker') {
    // family 5: a marker between a tracked root and the file makes which project's rules apply unknown
    const { outer, inner, marker } = e.why;
    return `This command is blocked here: its ${how} names ${raw}, which ${outer} tracks, but a \`${marker}\` at ${inner} `
      + `between that project and the file makes ${inner} its own root, so I cannot tell which project's rules apply to `
      + `the write, and a tracked file written with no change for me to accept or reject is what this guard prevents. `
      + `Remove the ${marker} at ${inner}, or make the change with track-edit, which records it for me to accept or reject:
${TRACK_EDIT}`;
  }
  if (e.why && e.why.kind === 'config') {
    return `This command is blocked here: its ${how} names ${raw}, and I could not read the tracking config at ${e.path} `
      + `(${describeError(e.code)}), so I cannot tell whether ${e.why.root} tracks the file it writes, and a tracked file `
      + `written with no change for me to accept or reject is what this guard prevents. Make that config readable in a `
      + `command of its own, or make the change with track-edit, which records it for me to accept or reject:
${TRACK_EDIT}`;
  }
  const blocker = blockingEntry(e.path);
  return `This command is blocked here: its ${how} names ${raw}, and I could not check ${blocker} on that path `
    + `(${describeError(e.code)}), so I cannot tell whether the write lands on a tracked file, and a tracked file written `
    + `with no change for me to accept or reject is what this guard prevents. Make ${blocker} readable in a command of its `
    + `own, or write a path that does not pass through it: a tracked file then takes its change through track-edit:
${TRACK_EDIT}`;
}

// Returns a block reason string when the command must be denied, or null to allow.
export function evaluate(raw) {
  let payload;
  try { payload = JSON.parse(raw); } catch { return null; }
  if (!payload || payload.tool_name !== 'Bash') return null;
  const command = payload.tool_input && payload.tool_input.command;
  if (typeof command !== 'string' || !command) return null;
  const cwd = typeof payload.cwd === 'string' && payload.cwd ? payload.cwd : process.cwd();
  // THE CATCH-ALL REFUSES (round 5 of the review, 2026-09-20). An exception the walk did not anticipate is the strongest
  // signal the guard has that it does not understand the command in front of it, and until this round every catch in
  // evaluate turned one into the most permissive answer available, an allow (round 4's extra4-4: a command word that is an
  // Object.prototype key threw inside the walk and the command ran). Now any exception other than an UnknownPath (which has
  // its own refusal) refuses while a tracked project is in play, naming the exception, and passes with no project in play,
  // the guard's subject being tracked files inside projects; when it cannot tell whether one is in play it refuses.
  try { return judge(command, cwd); }
  catch (e) { return internalErrorRefusal(e, cwd); }
}
// The refusal for an exception evaluate did not anticipate (the catch-all above): the exception's name and message, the
// project in play named as every refusal names it.
function internalErrorRefusal(e, cwd) {
  const named = `${(e && e.name) || 'Error'}: ${String((e && e.message) || e).replace(/\s+/g, ' ').slice(0, 300)}`;
  let hit;
  try { hit = trackingRootAt(cwd, { closures: new Map(), roots: new Map(), refusable: new Map() }); }
  catch (e2) { hit = { root: null, dir: cwd, fromEnv: false, unknown: `${(e2 && e2.name) || 'Error'}: ${String((e2 && e2.message) || e2).replace(/\s+/g, ' ').slice(0, 300)}` }; }
  if (!hit) return null;   // no tracked project in play from this directory: the guard's subject is not here
  const where = hit.unknown ? `whether ${cwd} sits in a project that tracks files is not known either (${hit.unknown}), and such a project` : `${hit.fromEnv ? 'the project TRACKCHANGES_ROOT names' : hit.root}`;
  return `This command is blocked here: while reading it I hit an error of my own (${named}), so I cannot tell whether it `
    + `writes a tracked file, and ${where} tracks files whose changes are recorded for me to accept or reject. Run it in a `
    + `plainer form (one command, its paths spelled out), or make the change with track-edit, which records it for me to accept `
    + `or reject:\n${TRACK_EDIT}`;
}
function judge(command, cwd) {
  let targets;
  let unresolved;
  let links;
  try { ({ targets, unresolved, links } = extractWriteTargets(command, cwd)); }
  catch (e) { if (isUnknownPath(e)) return statErrorRefusal(e.why && e.why.how ? e.why.how : 'write', e.why && e.why.raw ? e.why.raw : 'the path', e); throw e; }   // any other throw: the catch-all refuses
  const seen = new Set();
  const closures = new Map();
  for (const t of targets) {
    if (seen.has(t.path)) continue;
    seen.add(t.path);
    let guarded;
    try { guarded = isGuardedPath(t.path, closures); }
    catch (e) { if (isUnknownPath(e)) return statErrorRefusal(t.how, t.path, e); throw e; }
    if (!guarded) continue;
    return `Track-changes is ON for ${t.path}, so this command is blocked here `
      + `(its ${t.how} would write the file silently, with no change for me to accept or reject). `
      + `Make the change with track-edit instead, which records it for me to accept or reject:\n${trackEditLine(t.path)}`;
  }
  // A target the hook could not read, while a tracked project is in play (the header): refused, since
  // the same path spelled out would be judged and this one cannot be (2026-09-18). After the literal
  // targets, so a command that also writes a tracked file by name gets the more useful answer. A root
  // that came from TRACKCHANGES_ROOT is named by the variable, never by its value: an environment value
  // in a message is the road that put keys into transcripts this month, and a refusal is read and pasted
  // (review round 1, 2026-09-18). Each refusal says its own reason and a remedy the person can take
  // (review round 2 and 3: a generic line with the wrong reason, or a remedy that asks for a value nobody
  // can know before the command runs, reads as a broken tool).
  const memo = { closures, roots: new Map(), refusable: new Map() };
  const prevLinks = activeLinks;
  activeLinks = links || null;   // M3: the command's own links are followed while the unreadable targets are placed
  try {
  for (const u of unresolved) {
    let hit = null;
    try {
      hit = inPlayFor(u, cwd, memo);
      // B1: a write through an alias the command made lands where the alias's SOURCE is, so that source's project is in
      // play from any cwd, and an alias whose source the hook could not read is refused from any cwd
      if (!hit && u.why && u.why.kind === 'mutated' && u.why.alias) hit = aliasSourceInPlay(u.why, memo);
    }
    catch (e) { if (isUnknownPath(e)) return statErrorRefusal(u.how, u.raw, e); throw e; }   // any other throw: the catch-all refuses (round 5; `hit = null` allowed here before)
    if (!hit) continue;
    if (hit.literal) {
      // a numeric target whose fold leaves no expansion, or whose number could spell an entry that exists, lands on
      // a tracked file the literal rule knows (round 3)
      return `Track-changes is ON for ${hit.literal}, so this command is blocked here: its ${u.how} names ${u.raw}, and that lands `
        + `on ${hit.literal} (a \`..\` in it climbs from a link, or the shell's number could spell an entry that exists there), so the `
        + `${u.how} would write the file silently, with no change for me to accept or reject. Make the change with track-edit instead, `
        + `which records it for me to accept or reject:\n${trackEditLine(hit.literal)}`;
    }
    const where = hit.fromEnv ? 'the project TRACKCHANGES_ROOT names' : hit.root;
    if (hit.unknownSource) {
      // B1: the alias's source is a word the hook could not read, so the write may land on a tracked file of any project
      return `This command is blocked here: its ${u.how} names ${u.raw}, and an earlier \`${u.why.verb}\` in the same command `
        + `linked ${u.why.prefix} to a source I cannot read, so the write may land on whatever file that source names, a tracked `
        + `file of any project included, and a tracked file written with no change for me to accept or reject is what this guard `
        + `prevents. Run the \`${u.why.verb}\` in a command of its own with the source spelled out, or write the real path: a `
        + `tracked file then takes its change through track-edit:\n${TRACK_EDIT}`;
    }
    if (u.why && u.why.kind === 'mutated') {
      // family 3 (the walk-around lens second pass): an earlier rm/mv/ln/cp -l/cp -s in the same command touched a path prefix this write uses,
      // so what it resolves to at run time is not what the hook sees; refuse, naming the verb and the path.
      const acted = u.why.verb === 'rm' || u.why.verb === 'rmdir' ? 'removed' : (u.why.verb === 'mv' ? 'renamed' : 'linked');
      return `This command is blocked here: its ${u.how} names ${u.raw}, and an earlier \`${u.why.verb}\` in the same command `
        + `${acted} ${u.why.prefix}, so what that path resolves to when the command runs is not what I see now, and I cannot `
        + `tell whether the write lands on a tracked file, and ${where} tracks files whose changes are recorded for me to `
        + `accept or reject. Run the \`${u.why.verb}\` in a command of its own, or write a path that does not pass through `
        + `${u.why.prefix}: a tracked file then takes its change through track-edit:\n${TRACK_EDIT}`;
    }
    if (u.why && u.why.kind === 'unknownOption' && u.why.wrapper) {
      // rule (b) (the third pass): a wrapper option the guard does not parse in full (unknown, abbreviated, glued to a
      // letter it does not know, or filled in by the shell), so what the wrapper runs, and where, is not known.
      return `This command is blocked here: its \`${u.why.wrapper}\` wrapper carries the option ${u.why.option}, which I do not read in `
        + `that spelling (an option I do not know, an abbreviation, or a form I do not parse), so I cannot tell what the command `
        + `behind it would write or where, and ${where} tracks files whose changes are recorded for me to accept or reject. `
        + `Spell the option in the long form I know, or drop the wrapper: outside that project the command then runs as usual, `
        + `and a tracked file takes its change through track-edit instead:\n${TRACK_EDIT}`;
    }
    if (u.why && u.why.kind === 'unknownOption') {
      // class A (round 4): an option the writer's table does not know, so the operands cannot be placed and the
      // write target is unreadable. The remedy is the command without the option, or its long form the table knows.
      return `This command is blocked here: its ${u.how} carries the option ${u.why.option}, which I do not recognise, so I `
        + `cannot tell which file it would write, and ${where} tracks files whose changes are recorded for me to accept or `
        + `reject. Spell the command without that option, or use the long form I know: outside that project the command then `
        + `runs as usual, and a tracked file takes its change through track-edit instead:\n${TRACK_EDIT}`;
    }
    if (u.why && u.why.kind === 'opaqueScript') {
      // rule (b) (the third pass): env -S hands env a string that env's own splitter reads (its options, assignments, `--`
      // and quoting), and sudo -e/-i/-s/-R/-h run an editor, a shell or a chroot over the rest; neither is read here.
      return `This command is blocked here: its \`${u.why.option}\` hands the rest of the command to a splitter or a shell of its `
        + `own, which I do not read, so I cannot tell what runs or which file it would write, and ${where} tracks files whose `
        + `changes are recorded for me to accept or reject. Spell the command without \`${u.why.option}\`: outside that project it `
        + `then runs as usual, and a tracked file takes its change through track-edit instead:\n${TRACK_EDIT}`;
    }
    if (u.why && u.why.kind === 'homeAssigned') {
      // class D (round 4), rule (a) since the third pass: the command names HOME outside an expansion, so it may reassign HOME
      // before the write and `$HOME` and `~` name a directory I cannot read (I read only my own home, and never a variable the
      // command sets). The remedy is to spell the path out.
      // (the readability rule, the seventh pass: HOME is read from the guard's own environment and after a plain `HOME=<path>`
      // assignment of its own at the top level of the command, in no other form and not after an eval, a source or a call of
      // a function the command defines; the sentence used to say the guard never reads a variable the command sets)
      return `This command is blocked here: its ${u.how} names ${u.raw}, but ${u.why.text}, so \`$HOME\` and \`~\` name a directory I `
        + `cannot read here (I read HOME from my own environment, and after a plain \`HOME=<path>\` assignment of its own at the top `
        + `level of the command; in no other form, and not after an eval, a source or a call of a function the command defines). `
        + `I cannot tell which file the write lands in, and ${where} tracks files whose changes are recorded for me to accept `
        + `or reject. Spell the path out: outside that project the command then runs as usual, and a tracked file takes its `
        + `change through track-edit instead:\n${TRACK_EDIT}`;
    }
    if (u.why && u.why.kind === 'templatePath') {
      // M4 (the fifth commit): the script's write path is a template or format string the interpreter fills in
      return `This command is blocked here: its ${u.how} opens ${u.raw} for writing, a path built from a template or format string `
        + `(an f-string, a \`.format(\` or \`%\` applied to the string, a template literal holding \`\${...}\`, or a string literal `
        + `with more appended to it, a \`+\` or a method call), which the `
        + `interpreter fills in when it runs, so I cannot tell which file it writes, and ${where} tracks files whose changes are `
        + `recorded for me to accept or reject. Spell the path as a plain string: outside that project the command then runs as `
        + `usual, and a tracked file takes its change through track-edit instead:\n${TRACK_EDIT}`;
    }
    if (hit.parentOf) {
      // class E (round 4; any depth since the third pass): the literal head of the target sits above tracked projects, and
      // the expansion could spell the path down to one.
      const list = hit.parentOf.join(', ');
      return `This command is blocked here: its ${u.how} names ${u.raw}, and ${hit.dir} sits above the tracked project`
        + `${hit.parentOf.length > 1 ? 's' : ''} ${list}, whose name${hit.parentOf.length > 1 ? 's' : ''} the shell's expansion could `
        + `fill in when the command runs. I cannot tell which file the write lands in, and those projects track files whose changes `
        + `are recorded for me to accept or reject. Spell the path out, or write outside those projects: a tracked file then takes `
        + `its change through track-edit instead:\n${TRACK_EDIT}`;
    }
    if (u.why && u.why.kind === 'unknownDir') {
      // a literal relative target whose directory the hook cannot follow (round 3): the word is spelled out, the
      // directory is what is not known, and the remedy is a spelling that needs no directory
      return `This command is blocked here: its ${u.how} names ${u.raw}, a relative path, and the directory it is relative to is not `
        + `known when I check the command: ${u.why.text}. I cannot tell which file the write lands in, and ${where} tracks files `
        + `whose changes are recorded for me to accept or reject. Spell the target as an absolute path, or cd to a literal directory `
        + `that exists first: outside that project the command then runs as usual, and a tracked file takes its change through `
        + `track-edit instead:\n${TRACK_EDIT}`;
    }
    if (u.why && u.why.kind === 'unresolvable') {
      return `This command is blocked here: its ${u.how} names ${u.raw}, and ${u.why.text}, a directory on that path, is one I cannot `
        + `resolve (a dangling or looping link, or a directory I may not search), so I cannot tell which file the write lands in, and `
        + `${where} tracks files whose changes are recorded for me to accept or reject. Spell the path without that directory: outside `
        + `that project the command then runs as usual, and a tracked file takes its change through track-edit instead:\n${TRACK_EDIT}`;
    }
    if (hit.unknownFolder) {
      // Review round 2's addendum (2026-09-18) and round 3 (2026-09-19): the reason is not that the target sits in a
      // tracked project but that the folder's NAME is not known when the hook runs, so the text says that, names the
      // folder, and offers what the person can do: a literal folder name of their own, or a write outside the project
      // (round 3 replaced a remedy that asked for the folder as the shell would name it, a value nobody can know before
      // the command runs). The
      // project is named only when the target as typed does not carry it (a relative spelling; round 3): an absolute
      // one does, home-relative for a `~/` or `$HOME/` spelling, and an environment root's value stays out of the
      // message as everywhere.
      const project = hit.carried ? 'that project' : where;
      return `This command is blocked here: its ${u.how} names ${u.raw}, and ${hit.unknownFolder}, the folder it writes `
        + `into, is a name the shell fills in with a number when the command runs. I cannot tell which folder the write lands in, `
        + `and ${project} tracks files whose changes are recorded for me to accept or reject. `
        + `Spell the folder out with a literal name of your own, or write outside that project: an untracked folder then takes `
        + `the write as usual, and a tracked file takes its change through track-edit instead:\n${TRACK_EDIT}`;
    }
    const entry = hit.guardedEntry
      ? `, and ${hit.dir} holds ${hit.guardedEntry}, which is or leads to a tracked file of that project, a name the copy could take`
      : '';
    // B2 as ruled: an expanded name the command names or may fill in (PWD, OLDPWD; HOME takes the homeAssigned text above)
    // is one the guard would otherwise read, so the refusal says why it did not
    const named = u.why && u.why.kind === 'namedExpansion' ? ` (${u.why.text}, so I do not read \`$${u.why.name}\` here)` : '';
    return `Track-changes is ON in ${where}, so this command is blocked here: its ${u.how} names ${u.raw}, `
      + `which is not a literal path${entry}${named}. The shell fills that in when the command runs, so I cannot tell which `
      + `file it would write, and a tracked file written that way would carry no change for me to accept or `
      + `reject. Spell the path out: outside that project the command then runs as usual, and a tracked file `
      + `takes its change through track-edit instead:\n${TRACK_EDIT}`;
  }
  } finally { activeLinks = prevLinks; }
  return null;
}

// B1 (the fifth commit, 2026-09-19): the project in play for a write through an alias the same command made (a hard `ln`,
// `cp -l`, `cp -s`, `link`, or a symbolic link whose source the guard could not read, `why.alias`), asked of where the
// write LANDS, the alias's source, not of where the shell is: a literal source in a project that tracks something
// refusable puts that project in play from any cwd (the fourth pass's matrix: `cp -s <proj>/notes/seed.md <out>/alias &&
// printf poison > <out>/alias` from a cwd in no project overwrote the tracked note, since the in-play gate read the cwd
// alone; its twin with a source outside every project stays allowed), and a source the guard could not read is refused
// from any cwd (`unknownSource`), since it may name a tracked file of any project. Returns a hit, or null.
function aliasSourceInPlay(why, memo) {
  if (why.source == null) return { root: null, dir: null, fromEnv: false, unknownSource: true };
  const st = lstatOrNull(why.source);
  const dir = st && st.isDirectory() ? why.source : path.dirname(why.source);
  const hit = trackingRootAt(dir, memo);
  return hit ? { ...hit, viaSource: why.source } : null;
}

const invokedDirectly = (() => {
  try { return process.argv[1] && fs.realpathSync(process.argv[1]) === fileURLToPath(import.meta.url); }
  catch { return false; }
})();

if (invokedDirectly) {
  // Registered machine-wide by install.sh, so it runs on every Bash call in every Claude Code
  // session on the machine; it acts only in sessions romp launched. Both romp backends put the
  // session's stable id in its environment as ROMP_SID and hook commands inherit that environment;
  // no ROMP_SID means not a romp session, so pass the call through before stdin is read (the
  // vendored guard does the same, vendor/track-changents/patches/0004).
  if (!process.env.ROMP_SID) process.exit(0);
  let raw = '';
  process.stdin.setEncoding('utf8');
  process.stdin.on('data', (c) => { raw += c; });
  process.stdin.on('end', () => {
    let reason = null;
    // evaluate refuses its own exceptions (the catch-all); a throw that escapes it anyway refuses too, since this hook cannot
    // tell what it was asked and a false allow loses a person's work where a false refusal costs one retry (round 5)
    try { reason = evaluate(raw); } catch (e) { reason = `This command is blocked here: the guard that judges shell writes to tracked files failed while reading it (${(e && e.name) || 'Error'}: ${String((e && e.message) || e).replace(/\s+/g, ' ').slice(0, 300)}), so I cannot tell whether it writes a tracked file. Run it in a plainer form (one command, its paths spelled out), or make the change with track-edit, which records it for me to accept or reject:\n${TRACK_EDIT}`; }
    if (reason) { process.stderr.write(reason + '\n'); process.exit(2); }
    process.exit(0);
  });
}
