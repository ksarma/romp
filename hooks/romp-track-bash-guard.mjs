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
// in a variable) passes too: never a silent block of ordinary work. So does a script the guard cannot see (round 5's fifth
// addendum's second fix-up, 2026-09-20, names both beside the heredoc-fed forms it reads): one piped into a shell from anything
// but a literal echo or printf (`cat f | bash`; a `"$s"` whose value has whitespace, which the guard never resolves; a tee, a
// subshell, a group or a function before the pipe), and one handed to a shell outside SHELLS (busybox `sh` or `ash`, whose `[[`
// is a builtin that performs the redirection: `busybox sh -c '[[ x > report.md ]]'` wrote from docs/ in every shell, measured).
// So does (the third fix-up, the same day, which reads seven classes those verifiers found: the paragraph below) a script a `${...}`
// word stands for when the guard cannot read the word (`bash -c "${x:-$(cat f)}"`; a default word it can read is read since that
// fix-up), one fed by a redirection on the closing brace of zsh's brace-body compound (`if [[ a ]] { bash } <<'EOF'`), and one a
// command named by an expansion runs (`${SHELL} -c '..'`, `echo '..' | $SHELL`, named below among the writers).
// So does a python or node
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
// THE ADDENDUM (the reviewer's four items, the same day): (1) a plain top-level `HOME=<path>` assignment is the one readable
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
// ROUND 5'S FIFTH ADDENDUM (2026-09-20; the fourth addendum's builder measured it and the reviewer ruled it fixed before the
// round): `[[ x > report.md ]]` from docs/, alone, in an if or in a group, was allowed while dash, which has no `[[`, ran a
// command named so and performed the redirection (writers=[dash]); the hook read the test under bash and zsh grammar, where a
// `>` between `[[` and `]]` compares. The rule, stated once at the lexer's closeTest: a construct the hook reads under bash and
// zsh grammar contributes its dash reading to the write set too, a command named `[[` performing every redirection among its
// operands (the words after a `&&` or `||` a further command, spliced into the walk by withDashPieces), a subshell running the
// `(( ))` body as a command list (viaSubs), each target judged as any redirection or writer and the refusal naming dash and the
// construct (CONSTRUCT_HEADS's `via`). The derivation over the lexer's non-redirecting reads found two more with the same shape,
// closed the same way: a `$((` whose first `(` closes before the last, which bash and zsh read as `$( (` and run (`echo $((x >
// report.md);(y))` truncated the tracked file in both), and a `$(...)` or backtick inside any arithmetic body, which every
// shell runs (`(( $(echo x > report.md) ))` wrote in all three, `for (( i=$(..); .. ))` in bash and zsh); and it found where
// dash parses nothing, so no dash reading is due: a `for (( ))` head, a `((` after any word but a reserved one, an unquoted
// parenthesis inside the test, a here-string, a process substitution. A script handed to dash or sh takes the dash reading
// (`dash -c '[[ x > report.md ]]'` was allowed while every shell spawned dash and wrote), one handed to bash the test alone
// (TEST_ARITH_SHELLS). The costs, each measured with no shell writing: `[[ $a > $b ]]` with `$b` unreadable from a tracked cwd
// (the non-literal rule; the refusal offers `expr` or a cwd outside the project), the words after a `&&` inside the test (dash
// skips them when `[[` is not found; read as running since a command named `[[` on PATH would run them), `>>` and `<>` onto an
// existing tracked file through a command that is not found (the operator opens the file and writes no byte; the same spelling
// onto a name that does not exist yet under a tracked folder creates it), and the dead spellings no shell parses (`} (( .. ))`).
// Pinned with the rows test (each row through the hook as a process and unguarded in bash, zsh and dash), the reserved-word
// derivation (every word of RESERVED, BODY_CLOSER, CLOSERS and the keyword reads, quoted and unquoted, with a `>` and a writer
// operand: the two constructs were the only false allows) and the construct matrix (head x position x operator x target, the
// heads from CONSTRUCT_HEADS, the fixture romp-track-bash-guard-construct-matrix.json).
//
// ROUND 5'S FIFTH ADDENDUM, FIX-UP (2026-09-20; the addendum's verifier, on its head): two reads at the test's boundaries
// failed toward allowing, both inside the addendum's own construct. A process substitution among the operands was read as
// the test's `<` and a `(` (the test's own operators were read before the expansion), so `[[ -f <(echo x > report.md) ]]`
// from docs/ was allowed while bash performed it and wrote, in every position, through `bash -c` and a heredoc-fed bash (zsh
// after `!`, in a pipeline, with `&`, `|&` and under coproc too); and an operator glued to the closing `]]` was read as a word of the test, since the operator read ran
// before the `]]` under way had ended the word, so `[[ a ]]>report.md`, `]]>|`, `]]&&cp ..`, `]]||cp ..` and `]]||cd ..; cp
// ..` were allowed while bash, zsh and dash wrote. The lexer's operator read ends a `]]` under way first and reads `<(` and
// `>(` before the test's own `<` and `>` (THE TEST'S BOUNDARIES, beside the rule at closeTest); under dash's grammar alone a
// `<(` is `<` and an unquoted `(`, the syntax error dash makes of it, so closeTest gives such a test no dash reading. The
// construct matrix crosses the placement of the write with head, position, operator and target (among the operands, inside a
// `$(...)` or a `<(...)` among them, glued to the closer, spaced after it: the regions a construct has), and the rows test
// pins the verifier's rows.
//
// ROUND 5'S FIFTH ADDENDUM, SECOND FIX-UP (2026-09-20; the fix-up's verifiers): two reads failing toward allowing, each a
// class, one at the lexer and one present since the guard's first commit. (1) THE NESTED EXPANSION: a `$(...)`, a backtick or
// a `<(...)` inside a `${...}` word was never lexed (the `${` read skipped its inner text whole), so `echo ${x:-$(cp
// ../base/report.md report.md)}` from docs/ was allowed while bash, zsh and dash copied, and so were `${x-..}`, `${x:=..}`,
// `${x#..}`, `${x:?..}`, `${x/b/..}`, `${x[..]}`, the backtick, the double-quoted word, the `${` nested two deep, the word as
// an operand of `[[ ]]` and of `(( ))`, `dash -c` and the `<(...)` bash alone performs; 20 of the verifiers' 21 rows, from docs/,
// notes/, the project root and out/. THE RULE, at nestedExpansions in the lexer and on decision 47 in the same words: an expansion nested inside a parameter-expansion word is read as the command it runs, recursively, in every position (an operand, inside `[[ ]]`, inside `(( ))`, a redirection target, a quoted word), exactly as an expansion among plain operands is read; the `${` read descends. (2) THE PIPED SCRIPT: `echo 'cp ../base/report.md report.md' | bash`, `echo 'echo x > report.md' | sh`, `echo '[[ x >
// report.md ]]' | dash` and `printf '%s\n' '[[ a ]]>report.md' | bash` were allowed while every shell wrote: the heredoc-fed
// shell and the here-string were read, a pipe from echo or printf was neither read nor named. THE RULE, at stdinBodies in
// extract and on decision 47 in the same words: when a pipeline's last command is a shell of SHELLS reading its script from stdin (no `-c`, no script operand: `bash`, `bash -s`, `sh -`, dash) and the command piped into it is an echo or a printf, the words echo or printf would print are the script, read as the here-string form already is, under the grammar the shell named uses (dash's for `sh` and `dash`, TEST_ARITH_SHELLS); a producer the guard cannot see stays THE RESIDUAL, named
// above. The two populations, each through the hook as a process and the three shells unguarded: the param-word matrix (every
// `${...}` operator form x the nested expansion x the word's position x the cwd, 1020 rows, `FALSE ALLOWS 0`, the refusals where
// no shell writes counted by class) and the piped-script matrix (producer x quoting x script x consumer x form, 270 literal rows,
// `FALSE ALLOWS 0`, plus 30 residual rows pinned allowed). The matrix's own find, folded in before the fixture was written: bash
// performs a `<(...)` inside a DOUBLE-QUOTED `${...}` word's pattern, replacement and message parts (`"${x#<(cmd)}"` wrote), so
// the descent reads `<(` in every double-quoted word, the `:-` family's over-read a counted cost.
//
// ROUND 5'S FIFTH ADDENDUM, THIRD FIX-UP (2026-09-20; the second fix-up's two verifiers, on its head): seven live classes, each
// present at the pushed head, four written by bash, zsh and dash, and three more found while pinning them. (1) THE UNQUOTED BODY:
// `cat <<EOF` with `$(cp ../base/report.md report.md)` on the body's line was allowed while every shell copied; the body was kept
// as the consumer's data and never lexed. THE RULE, at readHeredocBodies and on decision 47 in the same words: a here-document whose delimiter has no quoted character has its body expanded by the shell before the command reads it, so a `$(...)`, a backtick, a `${...}` and a `$name` in the body are read as they are anywhere else and the body the consumer reads is the text after those expansions; a delimiter with any quoted character keeps the body as written and runs nothing
// (2) THE RESOLVED SUBSTITUTION: `bash -c "$(echo 'cp ..')"`, `bash <<< "$(echo '..')"`, that line in a here-document fed to bash and
// `echo "$(echo '..')" | bash` were allowed while every shell ran the printed text. THE RULE, at resolvedSub in the lexer and on
// decision 47 in the same words: a `$(...)` or a backtick whose command is one echo or printf with literal operands and no redirection prints text the guard can see, and that text stands in the word where the shell puts it, whole where no shell splits an expansion's result (inside double quotes, as a here-string, in a here-document body, as the word of a `${...}` operator), split at blanks into the words the shell makes among unquoted operands, and at a redirection target both, the whole text as dash opens it and each blank-separated field as zsh opens it (bash opens the one field, or none of several), each a redirection of its own, so the word is literal and a script it forms is read as the here-string form already is; when echo's two readings differ, a word that is the substitution alone keeps both texts and a script formed from it is read under each
// (3) THE DEFAULT WORD (found beside the rows): `bash -c "${x:-$(echo 'cp ..')}"` was allowed while every shell copied. THE RULE, at
// defaultReading and on decision 47 in the same words: `${name:-word}`, `${name-word}`, `${name:=word}` and `${name=word}` stand for word when the name is unset, and `${name:+word}` and `${name+word}` when it is set, so when word lexes to one literal text under the word's quoting that text is a reading of the word, read as a script where the word is one (a `-c` operand, a here-string, a here-document body fed to a shell), in every position, since zsh splits no expansion's result
// (4) ZSH'S `=(cmd)`: `echo ${x:-=(cp ..)}` was allowed while zsh copied, the spelling read nowhere. THE RULE, at eqProcsubStart and on
// decision 47 in the same words: zsh performs `=(cmd)` where a word begins, unquoted (an operand, an assignment's value, the word of a `${...}` operator, a replacement part), and nowhere else, so it is read as `<(cmd)` is, cmd running and read like a `$(...)`, for the Bash tool's command and for a script handed to zsh
// (5) THE CONSUMER'S STDIN: `echo 'cp ..' | (bash)`, `| if true; then bash; fi`, `| bash /dev/stdin`, `bash <(echo '..')`, `bash < <(echo
// '..')`, `| bash -c 'bash'` and `| sh -c sh` were allowed while every shell (bash and zsh for the process substitutions) copied, and
// `(bash) <<'EOF'` beside them. THE RULE, at stdinBodies (producerAt, closerStdin, THE INHERITED STDIN in recurse, STDIN_NAMES in
// shellScript) and on decision 47 in the same words: a compound command's standard input is the pipeline's, and so is what a redirection on its closer feeds it, so every command inside it that reads its script from stdin reads what was piped into the compound or redirected onto its closer; a `<` into the standard input feeds the command what it names, read when it is a process substitution whose command is a literal echo or printf, as a script operand that is one is read; a script operand naming the standard input (`-`, `/dev/stdin`, `/dev/fd/0`, `/proc/self/fd/0`) reads it; and a `-c` script, a `$(...)` and a script the shell reads from a file run with their caller's standard input
// (6) THE SPLIT OPERAND (found while pinning the IFS cost): `IFS=:; cp $(echo 'a:b')` and `cp $1` named no target. THE RULE, at the
// copying writers' case in extract and on decision 47 in the same words: when a copying writer (cp, mv, install, ln) has fewer operands than its two and one of them is an unquoted expansion the guard did not resolve, the shell may split it into the operands the writer needs, so that operand is a target the hook cannot read
// The populations (the third fix-up's two fixtures, tools/romp-track-bash-guard-stdin-script-matrix.json and
// tools/romp-track-bash-guard-heredoc-body-matrix.json, each stating its own): the script's road x the shape around the shell x the
// shell x the script, 600 rows, `FALSE ALLOWS 0`; the delimiter's quoting x the body's line x the consumer, 180 rows, `FALSE ALLOWS 0`,
// the refusals where no shell writes counted by class. The verdicts of the earlier fixtures are unchanged.
//
// ROUND 6 (2026-09-20; round 5's ruling on the third fix-up's head): THE RESOLVER'S CONTRACT, stated in full at the reading
// functions (echoOutput, printfOutput, segmentOutput, literalOutput, defaultWordReading) and consumed in two places, lex's
// placeReading and extract's scriptTexts. Round 5 found four readings of the third fix-up that turned a refusal of the base into an
// allow, each a reading the machinery believed and trusted: (1) printfOutput ignored a conversion's width and precision, so `echo x >
// $(printf '%.9s' report.mdXX)` from docs/ was judged on report.mdXX and allowed while bash, zsh and dash wrote report.md (and the
// same through an assignment, a double-quoted copy operand, `%c`, `%.0s`, `%.*s`, a `-c` script, a pipe, a process substitution, a
// here-string and a here-document); (2) an unquoted glob character made the default word and an echo operand non-literal, so the
// readings switched off and `bash -c "${x:-cp ../base/*.md report.md}"`, `$(echo cp ../base/*.md report.md)` alone and their kin went to
// the shell unread and allowed while every shell copied; (3) the union of echo's and `%b`'s readings lacked the octal escape without
// a leading zero, so `echo x > $(echo 'repor\164.md')` was judged on repor\164.md and allowed while dash wrote report.md, and
// `$(printf '%b' 'repor\164.md')` while bash and dash did; (4) THE SPLIT OPERAND exempted every double-quoted word, so `cp "$@"`
// with the positional parameters set to the copy's two operands was allowed while every shell copied (and `"${@}"`, `"${@:2}"`,
// `"${arr[@]}"`, `"${!m[@]}"`, zsh's `"${(@)arr}"`, `"${=s}"`, `"${(s: :)s}"`, `"${(f)s}"`, `"${(z)s}"` and `"$arr[@]"`). THE RULES:
// a reading function answers sound texts, unresolvable, or null, and nothing else; a reading takes the text road (the word's
// literal characters) only when plain, one text from no interpretation, and every other reading travels the script road, so no
// conversion, escape or option a reader could get wrong reaches a target judgement, and UNRESOLVABLE refuses in both places
// (placeReading marks the word and writes no text; scriptTexts records it as a target the hook cannot read and returns no
// text). printf's `%s` and `%b` are read with the `-` flag, a width and a precision (the shells agree on them, measured), `%%`
// and the escapes of each shell's format and `%b` readers; every other conversion, flag, a `*` from a non-digit operand, a width
// or precision over a non-ASCII operand, an option word and a missing format are UNRESOLVABLE, and `-v` is the empty text every
// shell prints (THE PRINTF GRAMMAR at printfOutput says why each). THE ESCAPE READERS (nine, one per reader and shell) are derived from the manuals and pinned by
// execution, the octal forms among them. A glob character, a brace list or a shell-dependent quoting in an echo operand or in the
// default word is UNRESOLVABLE, as is an expansion the resolver does not read inside either (`$(echo $t)`, `${x:-$(cat f)}`), so
// `s='cp ..'; echo "$s" | bash`, the piped-script matrix's residual-value producer, is refused now (the fixture's rows moved out of
// the residual set). THE SINGLE FIELD (dqSingleField) exempts a double-quoted operand from the split rule only when the guard
// proves it one field. THE CRASH (round 5's correctness-3): `printf` with no format, `printf --` and `printf -v` gave an empty
// reading, the walk threw, and the catch-all refused inside a project and passed outside one while every shell wrote
// (`cd <project>/docs && cp ../base/report.md $(printf)report.md` from a scratch directory); the missing format is UNRESOLVABLE now
// and `-v` the empty text it prints, judged by name, and THE
// CATCH-ALL REFUSES FROM EVERY CWD (evaluate says why: the walk throws before the hook knows what the command reaches, and the
// cwd bounds nothing). Pinned: the structural test that derives the reading functions from this source and reds when one is
// called outside the two places or a word's readings are read elsewhere, the readers and the printf forms by execution in the
// three shells, the rows test's round-6 group (the four readings' allows, refused, with the shells that write), the shapes
// test's single-field rows, and the catch-all's three stages from a cwd in no project. Not closed here, stated: zsh's glob
// grouping (`cp ../base/(r)eport.md report.md` handed to zsh, literal or through a reading) is read as a subshell by the
// lexer's zsh grammar and allowed while zsh copies, a lexer gap outside the resolver, named for the round.
//
// ROUND 6, SECOND COMMIT (2026-09-21; round 5's rulings C, D, E, F and G). THE ALIAS ROAD (extra7-2): a writer behind a shell
// alias the command defines was read as an unknown command and allowed while its text stood in the command; measured by the
// shells' grammars (bash: the first unquoted word of a simple command, under `expand_aliases` when not interactive, never on the
// line that defines it, a trailing blank chaining; dash: wherever a reserved word may occur, in the input stream, so through `-c`
// on the next line; zsh: command position, `-g` in every position, `-s` a suffix, from a file or a pipe and never through `zsh
// -c`), dash copied through `-c`, zsh and dash through a here-document or a pipe, bash under the option. THE HEAD SPLICE reads a
// command name that stands for a text the shell runs in its place, the text spliced in and the segment re-lexed with its tail as
// spelled: an alias body bound on an earlier line (`aliases`; a `-g` alias makes every later unquoted word spelled so a target the
// hook cannot read; `unalias` is not read, the safe side), a hashed path (`hash -p PATH NAME`, `hash NAME=PATH`), a path the
// command made by copying or linking another command (`bound`: `cp /usr/bin/cp ../scratch/c2; ../scratch/c2 a b`), and the
// readings of an expansion the resolver established (`${x:-cp} a b` ran the copy in every shell while the reading `cp` went unused
// in head position: the contract's head role yields the readings now); a binding the resolver cannot read makes the name a target
// the hook cannot read, and an alias whose NAME it cannot read makes every later command name one. `eval` and `trap` with text the
// resolver reads are scripts of this shell (`eval 'cp a b'`, `trap 'cp a b' EXIT` ran the copy while allowed); `source` and `.` of
// the standard input read what the command reads. THE OUTPUT MODEL (tests-1): a subshell or a `{ }` group before a pipe, and the
// list inside a `$(...)`, a backtick or a `<(...)`, prints what its echo, printf and silent commands print (listOutput; a `cat`
// fed one here-document prints its body), the text placed on the closer that carries the pipe and read as the consumer's script; a
// command the model does not read beside a printer makes the list UNRESOLVABLE, refused, its commands still read; a list with no
// printer is outside the model, the residual relabelled honestly on every surface (a producer outside the output model: a function
// call, a tee, a further pipe, a cat of a file), and the piped-script matrix's residual set is keyed on the model, not on a hand
// list. THE RESIDUAL PROPERTY (C, extra7-3), below, replaces the closing hand list: the classes it states are those THE RESIDUAL
// TABLE measures, and the reviewer's narrower sentence (the hook cannot read a command whose text it cannot statically resolve) is
// withdrawn with the alias road, since the property must cover a command the hook can read and still does not resolve to a writer.
// THE EVIDENCE A ROW NEEDS (E, regression-3): the matrices' NOT RUN skip is keyed on the fixture's `needs`, the programs a row's
// evidence needs, derived by hiding each named program behind a scratch PATH, so a row the running shell writes before the named
// consumer is reached is measured on a runner without that consumer; a runner lacking zsh is reproduced in the test file itself.
// The construct matrix pins the key set of CONSTRUCT_HEADS by kind (F), derives its population sentence from its tables (G), and
// the four constructs the param-word note named without a row have rows.
//
// ROUND 6, THIRD COMMIT (2026-09-21; the round's three verifiers on the second commit's head, every finding a command a shell
// wrote onto the tracked file while the guard allowed it, each closed by refusing and none relabelled). ZSH'S UNBRACED FLAGS:
// `$=name`, `$^name` and `$~name` are zsh's `${=name}`, `${^name}` and `${~name}` without the braces (zshexpn), and the lexer
// read a `$` before `=`, `^` or `~` as a literal dollar, so `cp "$=X"` with two paths in X was a one-operand cp the split rule
// never saw, and `cp ../base/report.md $~X` a copy onto the literal name `$~X`, both allowed while zsh split, or substituted,
// and copied; expansionAt reads the three as expansions under zsh's grammar (a script handed to bash or dash keeps the literal
// dollar) and dqSingleField proves none of them one field. THE SPLIT TARGET: the resolved substitution's rule called a
// redirection target a place no shell splits, and bash and zsh split it (zsh opens every blank-separated field under MULTIOS,
// bash the one field or none of several, an ambiguous redirect) while dash opens the whole text, so `echo x > $(echo 'report.md
// ')` was judged on the untracked name `report.md ` and allowed while bash and zsh wrote report.md, and `> $(echo x report.md)`
// while zsh wrote x and report.md; endWord records each field the resolver's blanks cut as a redirection of its own beside the
// whole text (expandedFields), and the rule's sentence on decision 47 says so. THE ALIAS ROAD INTO A TEXT PARSED LATER: a text
// the shell parses after the segment handing it over has run (eval's and trap's operands, a sourced standard input, a `$(...)`,
// a backtick, a `<(...)`) was lexed as its own text, its line count starting at 1, so an alias bound on line 1 never stood on
// an earlier line and `alias c=cp; eval 'c ../base/report.md report.md'` copied in zsh and dash (bash under `expand_aliases`)
// while allowed, as did `trap`, `. /dev/stdin`, `echo $(c ..)` and a backtick; lineOf gives such a text coordinates strictly
// between the outer segment's line and the next (`lineBase`, `lineStep`; recurse), so a binding on or before the outer line is
// seen inside it, a binding made inside it is seen on its later lines and on every later outer line, and never on the outer
// line itself, as the shells parse (`eval 'alias c=cp'; c a b` expands in none of them). A SOURCED PROCESS SUBSTITUTION and A
// DESCRIPTOR AS THE SCRIPT: `. <(echo 'cp a b')` and `source <(..)` (bash and zsh; zsh's `. =(..)` too) are read as `bash
// <(..)` is; a script operand naming a numbered descriptor (`/dev/fd/N`, `/proc/self/fd/N`: `bash /dev/fd/3 3<<'EOF'` ran the
// body in every shell, `bash /dev/fd/9 9<<< '..'` and `. /dev/fd/3 3<<< '..'` in bash and zsh) reads every body the command
// carries (isStdinName; the lexer keeps no descriptor on a body, so the over-read is the safe side); and a `--rcfile` or
// `--init-file` process substitution is read whether or not `-i` is spelled (bash reads it only when interactive: the refusal
// without `-i` is a stated cost). THE SED SCRIPT: sed's `w` and `W` commands and the `w` flag of `s` write the file they name,
// and sed was a writer through `-i` alone, so `sed -n 'w report.md' ../base/report.md` and `sed 's/x/y/w report.md' ..` wrote
// in every shell while allowed; sedWriteFiles reads a literal script over GNU sed's command grammar and sedScriptWrites judges
// each file by name (a plain-string name in the script resolves first: `f=report.md; sed -n "w $f"` refuses by name), a script
// whose reader stops at a letter the grammar lacks refuses naming the letter (sed itself rejects such a script; a reader that
// misread an address would stop the same way, so it does not guess), and a script the resolver cannot read stays the residual,
// named in the property. A GLOB IN THE COMMAND NAME: `/usr/bin/[c]p a b` ran cp in every shell while the walk read an unknown
// command; the sorted matches stand in the name's place through THE HEAD SPLICE (several make the first the command and the
// rest its leading operands, as the shells do), a pattern the guard cannot expand is a name it cannot read, and one matching
// nothing stands as spelled. ZSH'S OTHER HEADS: `=cp a b` (zsh's `=cmd`, the path of cp) is spliced under zsh's grammar,
// `emulate sh -c TEXT` runs TEXT as a script of zsh, and `zf_mv`, `zf_ln`, `zf_rm` and `zf_rmdir` (zsh/files) are the coreutils
// commands by another name. A CAT OF THE STANDARD INPUT inside a `$(...)` with nothing in the list feeding it (`echo 'cp a b' |
// { bash -c "$(cat)"; }`, `| bash -c 'eval "$(cat)"'`: every shell ran the piped text) is UNRESOLVABLE under THE OUTPUT MODEL,
// refused where a script is built from it; a cat after a pipe inside the list stays the producer outside the model. THE
// RESIDUAL TABLE gains the members of its classes the verifier found (a `$(which cp)` head and the `${...}` operator heads,
// setarch and linux64, uniq, awk's redirect, scp, openssl, shred, bash's history -w, zsh's sysopen and mapfile, a sed script
// the resolver cannot read, a written sed -f file), the writer class is restated to cover a write form of a program the hook
// models, and the child test that reproduces a runner lacking zsh counts the rows' NOT RUN line, not the probe's. Stated, not
// decided here: deleting or moving a tracked file (`rm report.md`, `mv report.md other.md`) is allowed, since the guard's
// contract is the write that lands on a tracked file; whether the tracked set shrinking is a write for it to refuse is a scope
// question raised with the round.
//
// ROUND 6, FOURTH COMMIT (2026-09-21; the round's three verifiers on the third commit's head, every finding a command a shell wrote
// onto the tracked file while the guard allowed it, each closed by refusing and none relabelled, and each rule keyed on the shells'
// grammars rather than on the spelling that found it). THE DESCRIPTOR FEED: a script operand naming a numbered descriptor reads a `<`
// on that descriptor too (`bash /dev/fd/3 3< <(echo 'cp a b')`, `python3 /dev/fd/3 3< <(..)` and `. /dev/fd/3 3< <(..)` ran the
// printed text in bash and zsh while textsOf skipped every `<` off the standard input; shellScript answers the descriptor named,
// fdOfName, and stdinBodies reads it; a `<` on a descriptor no operand names stays unread, since the shell reads its script
// elsewhere). THE EXEC FEED: a bare `exec` with redirections alone opens them for the rest of this shell and for the processes it
// starts (`exec 3<<< 'cp a b'; . /dev/fd/3` and `exec < <(echo 'cp a b'); bash` ran the text in bash and zsh), so its bodies feed
// every later consumer (execFeeds, shared by every recursion). THE ALIAS BODY: a body holding a `$` or a backtick after quote removal
// is expanded when the alias is USED (`alias c='$x'`, then `x=cp`, then `c a b` copied in dash, and through a here-document in
// every shell), so it binds null, refused as a text the resolver does not read, as an expansion at the definition already did; a
// `-g` alias at a redirection target is refused as one among the words is (`alias -g R=report.md` then `echo x > R` wrote in zsh);
// zsh's `functions[NAME]=BODY` binds NAME as an alias does. THE BOUND PATH: a path the command made by copying or linking a command
// is looked up by the head's text however spelled (`'../scratch/c2'`, `"$PWD/../scratch/c2"`, `$x` resolved to it: the lookup read
// the unquoted literal spelling alone), by a pattern's matches among the paths bound (`../scratch/c?`: the file is made when the
// command runs, so the filesystem cannot expand the pattern at check time), through PATH for a bare name (`ln -s /usr/bin/cp
// ../scratch/c2; PATH=../scratch c2 a b`), and a `cat FILE > DEST` binds DEST as cp does; a head through a HOME the command
// reassigns, or through a PATH set to a value the resolver does not read, is one the hook cannot read while a path is bound. THE
// COMPOUND PRODUCER: a keyword compound before the pipe (`for i in 1; do echo 'cp a b'; done | bash`; while, until, if and case
// alike) prints what the list from its head to its closer prints, and the head runs the body a number of times the model does not
// count, so a printer inside it makes the list UNRESOLVABLE (placed on the closer segment that carries the pipe, listOutput naming
// the head) and a body with no printer stays outside the model; dash reads `(( list ))` in command position as a subshell in a
// subshell, so `((echo 'cp a b')) | bash` prints the list's text there (bash and zsh read arithmetic and stop), the reading placed
// as the producer's. THE OPTION TERMINATOR: `eval -- TEXT` (bash and zsh), `. -- FILE` and `source -- FILE` read past the `--`.
// THE HEAD CANDIDATES (extract): every plain-string value ANY assignment word of the command gives a name, in every scope and form,
// whitespace included, shared by every recursion; a word that is one `$name` expansion the readability rule did not resolve stands
// for each value where it is a command name or a script (scriptTexts, roles 'head' and 'text'), the script road's union, so `c=cp;
// export c; $c a b`, `(c=mv); c=cp; $c a b`, `c=cp; echo '$c'; $c a b`, `declare c=cp; $c a b`, `eval c=cp` then `$c a b`, `c=cp bash
// -c '$c a b'`, `env c=cp bash -c '..'`, `f() { local c=cp; $c a b; }; f`, `c='cp a b'; $c`, `bash -c "$c"` and `eval "$c"` refuse
// (the last three were the residual "a script held in a variable", whose class is restated to the names a construct the resolver
// does not read fills in); a target keeps the readability rule, whose safe side is the refusal it already gives an unreadable name;
// the glued default word (`${c:-c}p a b` ran cp in every shell while the reading `c` was dropped for the glued `p`) carries its
// reading with the literal text around it (THE GLUED READING, readingsOf in lex). THE IFS RULE: while the command names IFS, an
// expansion not inside one pair of double quotes splits at IFS's characters, a rule the resolver does not compute, so the
// readability rule does not read it there (a target refuses as one the hook cannot read, a copying writer's one operand as split, a
// command name through scriptTexts) and lex declines to resolve a substitution at a redirection target too (`IFS=:; echo x >
// $(echo 'report.md:x')` opened report.md in zsh under MULTIOS; `x=a:report.md; IFS=:; tee $x`, `cp $x` and `IFS=: eval '..'`
// wrote in bash and dash), the rule holding in every text the command hands over. THE FED SUBSTITUTION: a `$(...)`, a backtick or a
// `<(...)` whose list the resolver does not read runs a command outside the output model, which may read the standard input, so
// where this command feeds that input with a text the guard read (a pipe from a producer it reads, a closer's redirection, an exec
// feed, the caller's) the word is UNRESOLVABLE (`echo 'cp a b' | bash -c "$(head -1)"`, `$(sed '')`, `$(tr a a)`, `$(awk 1)`,
// `$(dd)`, `$(</dev/stdin)`, `$(command cat)`, `$(busybox cat)` and `bash <(cat)` each ran the piped text while the rule that
// refused `$(cat)` was keyed on the spelling `cat`); with nothing fed the text is not in the command and the word keeps the
// residual; a process substitution so marked is recorded (cannotRead dropped every `<(..)` before); the cost, stated and pinned: a
// cat of a FILE in a fed segment refuses too. THE SED FILE: sed's `-f FILE` naming the standard input or a descriptor this command
// feeds stands for the bodies fed, a `<(..)` for the text it prints, each read over the sed grammar (`sed -n -f /dev/stdin f <<< 'w
// report.md'`, `-f <(echo 'w report.md')`, `-f /dev/fd/3 .. 3<<< '..'`, `--file=<(..)` and the here-document form wrote in bash
// and zsh, dash through the here-document). THE VALUED NAMES: the value of PS0, PS1, PS2, PS3, PS4 and PROMPT_COMMAND is a script of
// this shell (bash runs a prompt string's `$(..)` when it prints the prompt or traces a command: `PS4='$(cp a b)'; set -x; :`,
// `PS4='..' bash -xc :`, `export PS4=..` and `PROMPT_COMMAND='cp a b' bash -i` ran the copy), ENV and BASH_ENV name a file the shell
// sources, read when it is a `<(..)` the resolver reads (`ENV=<(echo 'cp a b') dash -i`; the lexer keeps a glued `<(..)` in its
// word as bash does, `ENV=/dev/fd/63`), bash's `${name@P}` runs the value's `$(..)` (each candidate value read), and `mapfile -C
// CALLBACK` runs the callback (SCRIPT_VALUED_NAMES, STARTUP_FILE_NAMES, readValuedWords). ENV'S OPERAND: after env an assignment
// operand however quoted is env's (`env 'X=a b' cp a b` copied in every shell while the quoted word was read as the command name).
// THE RESIDUAL TABLE gains the members its classes lacked (unshare, setpriv, perf and prlimit, wrappers outside the set; parallel, a
// reader like xargs; an alias in a sourced written file; an eval printing before the pipe; perl's File::Copy) and loses the two THE
// HEAD CANDIDATES read.
//
// ROUND 6, FIFTH COMMIT (2026-09-21; the round's three verifiers on the fourth commit's head: every finding a command a shell
// wrote onto the tracked file while the guard allowed it, each closed by a rule fitted to its class, none relabelled, and the
// table gaining the members its classes lacked). THE PARAMETER'S VALUE (defaultWordReading, lex's defaultReading, extract's
// scriptTexts): a default word's text is the parameter's value when it is set and the word otherwise, and the reading was the
// word alone, so `c=cp; ${c:-cat} a b` ran the copy in every shell (and `${c-cat}`, `${c:-}`, `${c:-''}`, `"${c:-}"`, `${c:?}`,
// `${c?}`, `${c:=cat}`, through `eval "${c:-cat} a b"`, as a piped script's consumer and as a here-string's); the reading carries
// the name (`params`, with the literal text glued around the expansion, so the value stands where the expansion stands) and
// scriptTexts joins the value the readability rule and THE HEAD CANDIDATES hold for it, refusing the word as UNRESOLVABLE where
// that value is not readable: a name a construct the resolver does not follow wrote (`read c`, `c=$(which cp)`), one a value the
// resolver could not establish was given, or one the command never sets, whose value is the shell's own (a `${X:-default}`
// command name or script from a tracked cwd with X untouched refuses, a stated cost; the `+` forms depend on no value and keep
// the word alone; a default word glued to another expansion is UNRESOLVABLE). THE MOVED SHELL (extract's return, recurse's
// adopt): a cd inside a text this shell ran in place (eval's text, a sourced standard input, here-string or `<(..)`, a head
// splice, emulate's and mapfile's texts) moved nothing for the rest of the command, so `eval 'cd ../notes'; cp ../base/report.md
// n1.md` landed on the tracked notes/ in every shell while the copy was judged from docs/ (with `eval "cd $d"`, `pushd`, `.
// /dev/stdin`, `source /dev/stdin <<< ..`, `. <(echo ..)`, an alias whose body is a cd, `alias c=cd`, `c=cd; $c ..`, inside a
// function, and the copy through cp, mv, tee, a `>`, sed -i, python or `bash -c`); the sub-walk's directory state comes back and
// is adopted, recorded on the frames and on a function body around it, and a trap action that moves leaves the directory unknown
// (`trap 'cd ../notes' DEBUG; cp ..` moved bash and zsh before the cp). THE DUPLICATED DESCRIPTOR (lex's dups, fdsFor): `[n]<&m`
// was skipped, so `exec 3< <(echo 'cp a b'); bash <&3`, `bash 0<&3`, `bash 3< <(..) <&3`, `{ bash; } 3< <(..) <&3`, `bash
// /dev/fd/4 4<&3` and `exec <&3; bash` ran the text in bash and zsh; a consumer reads every descriptor a dup on its segment or on
// an exec feed reaches, to a fixpoint, and a dup from a word the lexer cannot read reads every descriptor fed. THE PASSED-THROUGH
// TEXT (passthroughCat, pipedScripts): a plain `cat` of its standard input before a pipe prints what feeds it (`echo 'cp a b' |
// cat | bash`, `cat < <(echo ..) | bash`, `exec 3< <(..); cat <&3 | bash`, `(echo ..) | cat | bash` and `| (cat | bash)` each ran
// the text in the shells named), so that text is the consumer's script; a cat with an option word is UNRESOLVABLE where a text is
// fed (`cat -s` passes a script unchanged), a cat of a file stays the residual, and the property's fifth class says so. THE
// STARTUP FEED (the shells' branch): a BASH_ENV or ENV value naming the standard input or a descriptor the shell is fed is the
// text fed, sourced at startup (`BASH_ENV=/dev/stdin bash -c : <<< 'cp a b'`, `echo '..' | BASH_ENV=/dev/stdin bash -c :`,
// `BASH_ENV=/dev/fd/3 .. 3< <(..)`, through export, env and a nested `bash -c`, and `ENV=/dev/stdin dash -i -c :`), read whether
// or not this shell would. THE EXPORTED FUNCTION (the walk; commandOf's env operand): env sets any operand holding a `=`, and a
// bash the command starts imports `BASH_FUNC_NAME%%=() { .. }` as the function NAME, so the quoted word was read as a command
// name while `env 'BASH_FUNC_c%%=() { cp "$@"; }' bash -c 'c a b'` (and through `env -i`, `echo c | env .. bash`, `bash -s <<<
// c`, a `BASH_FUNC_cat%%` shadowing cat) copied in every shell; the word is a definition, its body read as `export -f`'s is. THE
// SPLICED DEFINITION (defLineOf): a definition made inside a head splice bound at Infinity, after every later use, so `alias
// a=alias`, then `a c=cp`, then `c a b` copied in dash (and, through a here-document or a pipe, in every shell); it binds at the
// spliced segment's line. THE CALLED BODY (functionBodies, popFunction, the walk, recurse's runFunction and callArgs): a function
// the command defines, called where a text the guard holds feeds it, was an unknown command while its body ran a shell on that
// text (`f() { bash; }; echo 'cp a b' | f`, `f <<< ..`, `f <<'EOF'`, `f < <(..)`, bodies of `sh`, `cat | bash`, `. /dev/stdin`
// and `bash "$@"` called with /dev/stdin, the call inside a subshell or a group); the definition's text is kept by name and
// replayed at the call with the fed text on its standard input and the call's operands, a call inside its own body not followed
// again. THE HEAD CANDIDATES' three gaps (noteCandidate, candidateTexts, scriptTexts): `+=` appends (`c=c; c+=p; $c a b` copied
// in bash and zsh), a value's newline is a blank where the value is a command name (`c='cp<newline>a b'; $c` copied in bash and
// dash), and two names in one quoted text compose (`a=cp; b='a b'; eval "$a $b"`, `bash -c "$a $b"` and `sh -c "$a $b"` copied in
// every shell); and THE ASSIGNMENT VALUE (lex's assignmentValue, noteCandidate's value road): no shell splits an expansion's
// result in an assignment's value, while the lexer cut `x=$(echo 'cp a b')` into three words and the candidates read `cp` alone
// (`$x` then copied in bash and dash), so the value is one text, and a value that is a reading on the script road (`x=$(printf
// '%s' 'cp a b')`) is a candidate through scriptTexts, one the resolver could not establish marking the name (unreadValues),
// refused where the name is a command name or a script. THE RESIDUAL TABLE gains the members its classes lacked that the
// verifiers measured: zsh's `${=c}`, `${~c}`, `${(z)c}`, `$=c`, `${(L)c}`, `${c:s/x/p/}` and `${c:q}`; bash's `${c:0:2}`,
// `${c:0}`, `${c,}`, `${c@P}`, `${c@E}`, `${c//x}`, `${c#}` and `${c%?}`; arrays by every spelling; getopts's OPTARG, REPLY,
// select and a loop variable after its loop; a function's positionals and its `eval "$*"`; `${d:=$c}`, `declare d=$c` and `set --
// $c`; a `read` or `mapfile` of a fed text, inside a called body too; the loader `/lib64/ld-linux-x86-64.so.2`; xargs by every
// spelling; a written `.zshenv` read through ZDOTDIR or HOME; a name glued to another expansion in head position; an eval, a
// backgrounded echo, `time`, `yes | head`, a second `| bash` and a tee before the pipe; python's `os.truncate` and `os.write`,
// and its `os.system` through a called body or a descriptor. The contract paragraph says on its four surfaces that deleting or
// moving a tracked file away is not a write the guard refuses, a scope question raised with the round's review. Stated costs,
// each pinned with no shell writing: an untouched `${X:-word}` command name or script from a tracked cwd; `cat -n` before a pipe
// fed a text; `exec 3<<< ..; BASH_ENV=/dev/fd/3 bash -c :` (bash does not read it there); `env 'BASH_FUNC_..' sh -c c` (dash
// imports nothing); a function calling itself before its shell.
//
// ROUND 6, SIXTH COMMIT (2026-09-21; the round's three verifiers on the fifth commit's head, an attack lens, a residuals lens
// and the body auditor: every finding a command a shell wrote onto the tracked file while the guard allowed it, three of them
// roads by which a text the hook could not establish reached an allow through a null; the mechanism is fixed once, stated
// here, and the rows follow from it). THE APPLIED RESOLVER (printerOf, shapeOnPrinter, segmentOutput, listOutput,
// closerOutput): once the resolver applies to a segment (its head is a literal echo or printf, or a cat fed a here-document,
// alone or in a list or group of them), every shape it does not model is UNRESOLVABLE, never null: a redirection, a
// here-document, a `<`, a substitution or an arithmetic body on the printer (`echo 'cp a b' 2>/dev/null | bash`,
// `</dev/null`, `3>/dev/null`, `>/dev/stdout`, `2>>`, `2>|`, `2<>`, zsh's MULTIOS write forms, the same inside `$(..)`, a
// here-string, a `<(..)` and a here-document, each ran the text in the shells named while the printer was dropped as outside
// the model and the list read as printer-less), a `&&`, `||`, `&` or `|` after it inside a list (`(echo 'cp a b' && true) |
// bash` and its `||`, `& wait` and `| cat` forms ran the text in every shell), and a redirection on the closer of the
// subshell or group holding it (`(echo ..) 2>/dev/null | bash`, `(time echo ..) 2>/dev/null | bash`); null is reserved for a
// segment whose head is no printer at all, the residual the property names; pinned by execution over every list operator and
// every redirection operator the lexer has. THE UNREAD SCRIPT WORD (scriptTexts): a script word that is no expansion and
// still not literal (a glob character, a brace list past the cap, a quoting whose reading depends on the shell) is a text the
// resolver cannot establish, refused (`bash -c cp\ ../base/*.md\ report.md`, `[r]eport.md`, `?eport.md`, the same through `sh
// -c`, `dash -c` and `eval`, python's and node's inline words holding a `*`, each ran in bash and dash while no text was read
// and nothing was refused). THE SPECIAL PARAMETER (lex's braceParameter, defaultWordReading): a default word over a digit run
// or a special parameter is a default word too; the `+` forms stand for the word alone, a `-`, `=` or `?` form over `#`, `?`,
// `0`, `$`, `!`, `-`, `@` or `*` stands for a value that is the shell's own, UNRESOLVABLE, and one over a positional
// parameter carries the name to THE POSITIONAL VALUE (`${#:+cp} a b`, `${0:+cp}`, `${$:+bash} -c '..'`, `${1:-cp} a b`,
// `${@:-cp}`, `${!:-cp}`, `${0:-x} -c '..'` ran the copy in the shells named while the grammar read names alone). THE
// ASSIGNED DEFAULT (lex's paramAssigns, extract's noteCandidates): `${name:=word}` and `${name=word}` give name word's texts
// as candidates, a word the resolver cannot establish marking the name (`: ${e:=cp}; $e a b`, `true ${e:=cp}`, `x=${e:=cp}`,
// `: ${e:=cd}; $e ../notes; cp ..`, `: ${e:='cp a b'}; eval "$e"` ran in every shell while the assignment was recorded
// nowhere). THE SHELL'S OPTION WORD (shellScript's optionWord, the walk's readShell): a word in option position of a shell in
// SHELLS, with words after it, that the resolver did not read stands for each text it can (its readings, a candidate, a
// positional), the shell read again with each in its place, and for none is refused on the side WRAPPER_OPT takes for an
// option a wrapper's table does not know, every later word a target the hook cannot read; as the last word it is the operand,
// so `bash -c "$x"` keeps the residual (`set -- -c; bash "$1" 'cp a b'`, `bash "${f:--c}" ..`, `f=-c; bash ${f-x} ..`,
// `a=(-c); bash "${a[@]}" ..`, `bash {-c,} ..` ran the script in the shells named while the expansion was taken as the script
// FILE operand and the `-c` it stood for was never seen). THE POSITIONAL VALUE (bindPositionals, positionalWords,
// expandPositionals, setOperands, positionalsApply, the walk; CANDIDATE_TOKEN and RESOLVED_NAME take a digit, `$@` and `$*`):
// THE CALLED BODY's replay runs for every call, fed or not (`f() { bash "$@"; }; f -c 'cp a b'`, `f() { bash -c "$1"; }`,
// `"$*"`, `eval "$1"`, `"$@"` and `$1` as the command name, a nested call, `f() { bash <<< "$1"; }`, `eval "cp $1 $2"` ran in
// every shell while the replay ran for a fed call alone), and the positional parameters this shell holds are the replayed
// call's operands or those a `set` with no option word gave (`set -- 'cp a b'; eval "$1"`, `set -- cp a b; "$@"`, `$*`, `set
// -- x cp; shift; "$@" ..`), standing in place of a whole word that is one of them, read through the readability rule and THE
// HEAD CANDIDATES for a `$N` inside a word, and joined by one blank for `"$*"` and `"$@"` in a here-string or an unquoted
// here-document body; a `shift` by a count not read, a `set` whose operands or option words the resolver does not read (`set
// -A` is zsh's array assignment), an `eval` of a text it does not read or a sourced file rebinds them to values not known,
// after which a positional word is UNRESOLVABLE; a body being defined has positionals of its own (`set -- cp; f() { $1 a b;
// }; f cat` runs cat, allowed), the replay reads a body's aliases as of the definition's line (functionLines: `f() { c a b;
// }`, then `alias c=cp`, then `f` expands in no shell), and a fresh or fed shell's positional parameters are its own, not
// read (`bash -c '$1 a b' _ cp`, the residual). THE EMPTY ALTERNATIVE (lex's braceEmpty, the walk's variants): bash drops an
// unquoted empty word a brace list expands to and zsh keeps it, so a writer's operands are judged under both readings and an
// empty word in command position is dropped (`{cp,} a b`, `{mv,} a b`, `{bash,} -c '..'`, `{,cp} a b` copied in bash while
// the lexer's empty operand was judged as `cp '' a b`, a copy no shell performs). THE RESIDUAL TABLE loses the fifteen rows
// these rules refuse (the positional rows, the function-body rows, the inner pipe, the backgrounded and the timed echo,
// `${d:=$c}`) and gains the members the verifiers measured that no rule reads: a function's call of itself, zsh's autoload of
// a written file, a `.` reached through a value, nsenter, tmux, an alias in a sourced written file, a fresh shell's own
// positional parameters, a `read` value as a trap action or inside a `-c` script; the property's second, third and fourth
// classes are restated for them. Stated costs, each pinned with no shell writing: `echo "$(cat f)" | bash` (a substitution in
// a printer's operand), `bash -c "$x" _ a b` (an expansion before further words), `${#-cp} a b` (a `-` form over a special
// parameter); `bash -c "$x"` alone stays the residual and `bash -c "${x:-..}"` the fifth commit's stated cost: two spellings,
// two rules, each stated.
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
// whose source lies in a tracked project or is one it cannot read. Deleting or moving a tracked file away (`rm`, `unlink`,
// `mv` to another name, `find -delete`) is not a write it refuses: the contract is the write that lands on a tracked file,
// and whether the tracked set shrinking is such a write is a scope question raised with the round's review and not decided
// here. A value it can read is resolved first and the real
// path judged. A name is readable only when every write to it in the command is a plain top-level `NAME=plain-string`
// the shell performs as spelled: no tilde opening the value, no declaration flag at all, no `declare`, `typeset` or `local`
// (dash has none of the three; `export` and `readonly` with no option word are the two declarations every shell performs),
// no nameref reaching it, no name the shell fills in, no subshell, pipeline, piped group or body scope, no `{ }` group
// opened after `&&`, `||` or `|`, no wrapper argument, no
// call of a function the command defines in any spelling, no subscript; any other construct that can write the name,
// listed here or not, leaves it unreadable, the doctrine a `read` and a loop variable already had. HOME, PWD, OLDPWD,
// `~+` and `~-` are read the same way: HOME after a plain top-level `HOME=<path>` assignment of its own, and none of
// the three once the command names or may fill in the name in any other form. THE RESIDUAL PROPERTY. The guard refuses a
// write only when it resolves the command to a writer it models (the writer cases of extract's switch, a write redirection,
// an interpreter's write call it scans) reached through a road it reads (the wrapper set, the shells' script roads, the
// readings of the resolver, the alias and hash roads), with a target it can place or cannot read. Every write that still
// reaches a tracked file is one the guard does not resolve to such a writer through such a road, whether or not its text
// stands in the command, and falls in one of these classes, each measured by execution in
// tools/romp-track-bash-guard.test.mjs (THE RESIDUAL TABLE, whose rows are the population this statement is over): a writer
// outside the model, a program, or a write form of a program the hook models, that writes the file by its own nature and is
// not among the write forms the hook reads (rsync, patch, tar -x, ed, ex, vim, make, shuf -o, gawk -i inplace, awk's print
// redirect, uniq, scp, openssl -out, shred, curl -o, wget -O, find -exec, a git alias or a subcommand that writes the tree,
// bash's history -w, zsh's sysopen and mapfile modules, sed's e command and a w command in a sed script the resolver cannot
// read, busybox's applets); a reader outside the roads, a program that runs a command or a script the hook does not follow
// into it (xargs, an interpreter's system, exec or subprocess call, a wrapper outside the set, a shell outside SHELLS, a file
// the command writes and then runs or sources, a function's call of itself, which the replay does not follow again); a
// command name the resolver never reads, a command whose name is an expansion of a kind the resolver does not read
// ("${a[@]}", a loop variable, a name read or filled by getopts, printf -v or a nameref, a name the shell itself sets (${SHELL}, $0, $BASH, $ZSH_ARGZERO, $_ after a command), a substitution outside the
// output model such as $(which cp), a ${...} operator form the resolver does not read, a positional parameter of a script
// handed to a fresh shell with arguments of its own; "$@", $1 and $* stand for the operands of a called function or of a
// `set` this shell ran since round 6's sixth commit); a script held in a variable, a value the command gives a name through a
// construct the resolver does not read (`read`, `printf -v`, a positional parameter of a fresh shell's script), run as a
// command or handed to a shell (`$c` after `read c`, `eval "$1"` inside a `bash -c` given arguments, `bash -c "$c"` after
// `printf -v c`; a value an assignment word gives, whitespace included, is read through THE HEAD CANDIDATES since round 6's
// fourth commit, and a `${name:=word}` gives word since the sixth); a producer outside the output model, a pipe into a shell, or a write redirection into a process substitution running one,
// from anything but a literal echo or printf, alone or in a subshell or group of such commands, or a plain cat passing such a
// text through (a call of a function the command defines, a tee or a pipe through another command, a cat of a file); zsh's
// glob grouping, a `(..)` inside a word handed to zsh, read as a subshell by the lexer's zsh grammar while zsh globs it (a
// lexer gap, stated since the first commit of this round); zsh's hook functions, a function the command defines under a name zsh calls on its own (chpwd, precmd, preexec, periodic, zshexit, and the names in chpwd_functions and its kin), whose body runs when the shell moves, prompts or exits, from the directory the shell is in then, while the guard judges the definition where it stands; an opaque expansion from a cwd outside every project, a leading
// opaque expansion, or one after a literal head outside every project, from a cwd in no project (B2 as ruled, with its
// boundary). A shape outside these classes that reaches a tracked file is a rule to state, not a residual. The same
// paragraph,
// and THE RESIDUAL PROPERTY, are on the vendored SKILL.md, hooks/README.md
// and docs/install.md, pinned identical by a test; the property is on decision 47, docs/guide.md and the ledger entry too, pinned
// identical there as well, and its classes are the ones tools/romp-track-bash-guard.test.mjs's RESIDUAL_TABLE measures.
// ROUND 6, SEVENTH COMMIT (2026-09-21; the round's three verifiers on the sixth commit's head): a regression, an unsound reading and the round's
// pre-existing allows, the mechanism fixed and the rest disclosed as residual rows. THE SPLICED PRINTER (printerOf, splicedPrinter, splicedOutput):
// a command name that is an expansion THE HEAD CANDIDATES resolve to a printer is spliced BEFORE printer-ness is decided (the same order the writer,
// consumer and passthrough heads had), so `e=echo; $e 'cp a b' | bash` reads the printed text as before the sixth commit dropped it to a null; a
// text no candidate makes a printer stays null (the residual). THE UNSOUND UNICODE (shellEscapes): every `\u` and `\U`, bare or with hex, is Undecodable
// for every reader (zsh renders a bare `\u` as a NUL a substitution drops, so the script under zsh was the text before it). THE SHADOWED BUILTIN and
// THE DEFINITION'S NAME: a function under a builtin's name (cd, pushd, popd, chdir) runs the function through THE CALLED BODY, and the name of a
// `name()` definition moves nothing. THE PARAMETER TABLES (lex, the walk): zsh's `aliases`/`galiases`/`saliases` bind an alias and `commands` a hashed
// path, keyed and whole-array forms. THE COMPOSED VALUE (noteCandidate, THE SET'S OPERANDS): a value whose expansions are names the command gives
// values (`c=$1`, `c="$*"`, `c=$d`) stands for their composition, so a positional laundered through a name and split by the shell is read, a top-level
// `set` seeded into the candidates so a later `c=$1` reads it. THE POSITIONAL LIST'S SPELLINGS (positionalSpelling): `${@:N}`, `${@:N:M}`, zsh's
// `$argv` and `${@[N,M]}` read as the list. THE EMPTY ALTERNATIVE among a call's operands: the body is replayed under bash's reading (the empty word
// dropped) and zsh's (kept). The head splice reconstructs its siblings from a resolved word's text, not its raw spelling, so a `"$@"` the walk already
// expanded is not re-expanded (spliceRaw). Every remaining allow-and-write the verifiers measured is a RESIDUAL_TABLE row with its writers.
// ROUND 6, EIGHTH COMMIT (2026-09-22; the round's three verifiers on the seventh commit's head): the regression closed through every wrapper, two
// mechanism defects that let a shell write while the guard allowed, and the rest disclosed as rows. THE WRAPPED PRINTER (commandOf, printerOf): the
// seventh commit's splice restored the bare `$e 'cp a b' | bash` refusal and left the same printer behind a wrapper allowed (`e=echo; command $e
// 'cp a b' | bash`, and env, nice, exec, builtin, time, nohup, timeout, stdbuf, setsid, ionice, taskset, chrt, flock, numactl, sudo and zsh's
// modifiers, piped and substituted), where the round-5 head refused each as a wrapper option it did not read; commandOf records the word its
// walk stopped at (`at`), and printerOf splices an expansion standing there through THE SPLICED PRINTER, the segment re-lexed and the wrapper
// peeled again on the spliced text, one road for the printer as for the writer, consumer and passthrough heads. THE VANISHING OPERAND
// (mayVanish, vanishVariants, the copying writers' case, recordMutations): a copying writer with three or more operands, one an unquoted
// expansion the shell may make no word of (an unset or empty name, `${c:-}`, an empty substitution, `$*`, `$@` and `"$@"` with no positional
// parameter, an empty array, a pattern under nullglob or null_glob with the directory unknown), was read as a copy into a directory named by
// the tracked file and allowed while every shell ran the two-operand copy onto it; the operand count is a set now, the destination judged under
// the list as spelled and under every list with such operands dropped, a write under any of them refused naming the operand dropped, the
// bound paths and class H recorded under each list, a rename or a hard link with such an operand marking every literal operand as a path the
// command may have changed, and more than VANISH_CAP such operands a target the hook cannot read. THE PAREN RULE (parenCloses; the lexer's
// scope markers, skipNested, closeSubshell): an unparenthesised case pattern's `)` inside `( .. )` or `$( .. )` closed the lexer's subshell or
// substitution, so the producer after it was lost and `(case x in x) echo 'cp a b';; esac) | bash`, `bash -c "$(case ..)"`, the here-string,
// the here-document and the process substitution were allowed while every shell ran the text, where the walk's closeSubshell already knew that
// in a case body a `)` ends a pattern; the rule has one home now, asked by the walk over its frames and by the lexer over the scopes it tracks,
// so such a `)` is a marker that pairs with no `(` and a substitution reads past it, and the case beside its printer is UNRESOLVABLE (THE
// COMPOUND PRODUCER). The residual table gains the names the shell itself sets (`$0`, `${0}`, `"$0"`, `$BASH`, `$SHELL` and `$ZSH_ARGZERO` as
// the command, with `-c`, a here-document and a pipe, and `$_` after a command), zsh's hook functions (`chpwd` and `chpwd_functions`, whose
// body runs where the cd lands) and zsh's `(N)` glob qualifier, the property's third class naming the shell-set names and an eighth class the
// hook functions; the piped-script matrix names, in a field of its own, the allowed rows whose writer evidence needs ksh, a shell no box
// running the matrix has, so their allow rests on ksh's `[[` grammar (TEST_ARITH_SHELLS) and on no measured writer.
// ROUND 6, NINTH COMMIT (2026-09-22; the round's three verifiers on the eighth commit's head): four defects of the round's own class (a
// reading that resolves a word wrongly and thereby allows), each fixed at the mechanism, and the rest disclosed as rows. THE POSITIONAL TARGET
// (positionalWords' target mode, expandPositionals): a redirection whose target is a positional list of several elements was joined into one
// quoted name, so `set -- a.md report.md; echo x > $@` wrote report.md in zsh, which opens every element (MULTIOS), while the guard judged the
// name `a.md report.md`; `"$@"` kept the first element alone; and a single unquoted element's pattern went unexpanded while bash expands it. The
// list stands now for the joined name dash opens beside each element zsh opens, a single unquoted element for itself with its pattern read, an
// element that is an expansion for a target the hook cannot read, one redirection per word, under every write operator, on a closer's and an
// `exec`'s redirection. THE PEELED NAME (commandOf's wrapperIdx; nameRoads, boundRoad): the alias, hash and bound-path roads were asked of the
// head the wrapper walk left, so a binding of a wrapper's own name was never seen once operands followed it (`alias command=cp`, then `command a
// b`, copied in dash, and every name of the wrapper set, `[` and `[[`; `hash -p /usr/bin/cp env` in bash, `hash env=/usr/bin/cp` in zsh; a copy or
// link of cp at `../scratch/env` on PATH, as `env a b`, `../scratch/env a b` and `nice env a b`, in every shell); every word the walk peeled is
// asked the three roads and the binding spliced at that word, `[` and `[[` admitted by their text. THE VANISHED TEXT (candidateTexts' vanish,
// scriptTexts, noteCandidate): an expansion the command never gives a value may be empty, and the shell drops the empty text before a script is
// handed over, so `eval cp $c a b`, `eval cp "$c" a b` (eval's join), `eval cp $(true) a b`, `trap "cp $c a b" EXIT`, `bash -c "cp $c a b"` through
// every shell, python's inline code and `x="cp $c a b"; $x` ran the two-operand copy in every shell while allowed; the text with such expansions
// removed is one script the shell may run, read beside the residual (the word stays opaque), never in THE SHELL'S OPTION WORD's place, whose
// empty answer is a refusal. THE WRITTEN PROCESS SUBSTITUTION (lex's streamSite and procsubFeeds, streamOutput, outDups, the fd of a write;
// extract's recurseSubs and inheritedTexts): a write redirection into `>(cmd)` is a pipe into cmd, so the printed text, or a closer's list's, is
// cmd's standard input where the redirection is on the standard output or a descriptor a `>&` routes it to, UNRESOLVABLE where an `exec` opens
// it for every later command, outside the model on another descriptor or from a command that is no printer; zsh's `>>(cmd)` reads as `>` and the
// substitution; `echo 'cp a b' > >(bash)` and thirty-nine forms ran in bash and zsh while allowed. The residual table gains sed's `s///e` flag and
// bare `e`, logsave, script's typescript, node's writeFileSync under another name, python's Path held in a name, dbus-run-session and capsh, and
// through `>(..)` a cat of a file, a `while read` and a python (12 rows; 199 rows over 8 classes); the property's fifth class names the write
// redirection into a process substitution on the seven surfaces and patch 0009; the eighth commit's records date it 2026-09-22, the day of its
// commit. Every fix pinned by execution (the ninth commit's rows test, the writers measured in bash, zsh and dash; red on the eighth commit's
// head at S9-pt-at, S9-pn-alias-command, S9-vt-eval-unset and S9-ps-echo, each `0 !== 2`).

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
// never lexed as shell, except that a literal echo or printf piped into a shell reading stdin is that shell's script
// (extract's stdinBodies, the second fix-up), and that an unquoted body's expansions are performed by the shell before the
// consumer reads it, so they are read as they are anywhere and the body kept is the text after them (readHeredocBodies, the third
// fix-up); a substitution whose command is a literal echo or printf is the text it prints (resolvedSub, the third fix-up). An expansion nested inside a `${...}` word (`${x:-$(cmd)}`, a backtick, a
// `<(...)`) is read as the command it runs, in every position (nestedExpansions, the second fix-up). `>(cmd)` and `<(cmd)` are process substitutions: cmd is read like a
// `$(...)`, and the word stands for a /dev/fd path the hook cannot resolve, inside `[[ ... ]]` too, where bash performs it
// (round 5's fifth addendum's fix-up, 2026-09-20). Inside `[[ ... ]]`
// (the unquoted keyword, in command position) a `>` or `<` compares in bash and zsh, and `&&`, `||`, `(` and `)` are the
// test's own operators there, up to the unquoted `]]` that closes the test (an operator glued to that word is the
// redirection or list operator it is anywhere else, the fix-up); `(( ... ))` is arithmetic in bash and zsh. dash has neither word, and since round 5's fifth
// addendum (2026-09-20) each construct is read in BOTH grammars: its dash reading, a command named `[[` performing every
// redirection among its operands, a subshell running the `(( ))` body as a command list, adds its writes to the segment (the
// rule is stated once, at closeTest below; the shell facts at TEST_ARITH_SHELLS and CONSTRUCT_HEADS). `opaque` is set
// when the command is more than the lexer can follow: an unterminated quote, or eval, xargs or a
// shell -c with a script it cannot read.

// The write redirections, with zsh's clobber-override suffixes (the fifth commit, 2026-09-19, M2): zsh reads a `!` or a
// `|` after `>`, `>>`, `>&`, `>>&`, `&>` and `&>>` as "write even under NO_CLOBBER" (`>! f`, `>>! f`, `&>! f`, `>>| f`,
// `>&| f`, `>>&` appends both streams), and the fourth attack wrote a tracked file through `>! docs/report.md` while the
// lexer read the `!` as the target word and the file as an argument. The lexer consumes the suffix as it consumed `>|`,
// and records the readings of bash and zsh where they differ (bash reads `>! f` as a redirection onto a file named `!` with `f`
// an argument, and `>!f` as a redirection onto `!f`; `>>&`, `>>|`, `>&|`, `&>|` are syntax errors in bash and write
// nothing; dash, measured 2026-09-20 for round 5's fifth addendum, reads `>! f`, `>>! f` and `&>! f` as bash does, rejects
// `>>| f` and `>&| f` as syntax errors, and reads `&>| f` as `&` then `>| f`, a write of f the zsh reading names), so a
// command refuses when any of the three shells would write the tracked file.
const WRITE_REDIRECTS = new Set(['>', '>>', '>|', '&>', '&>>', '>&', '<>', '>!', '>>!', '>>|', '>&!', '>&|', '>>&', '>>&!', '>>&|', '&>!', '&>|', '&>>!', '&>>|']);
export const SHELLS = new Set(['sh', 'bash', 'zsh', 'dash', 'ksh']);   // exported for the piped-script matrix's consumer population (the second fix-up)
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
// The shells verified (round 5's fifth addendum, 2026-09-20, by execution) to read `[[ ... ]]` as the test keyword and
// `(( ... ))` as arithmetic, where a `>` between them compares and redirects nothing: bash 5.2 and zsh 5.9, the shells the
// Bash tool runs (ksh has both words by its manual and is entered unverified). dash 0.5.12, `/bin/sh` here, has neither
// word: `[[ x > f ]]` is a command named `[[` whose operands are `x` and `]]` and whose `> f` is a redirection it performs
// before the lookup fails (docs/report.md truncated, the fourth addendum's finding); the words after a `&&` or `||` among
// those operands are a further command dash runs or skips by the status of `[[` (not found on this box: the `||` branch
// runs, `[[ -z a || b > f ]]` and `[[ a || cd ../docs ]]` measured; the `&&` branch is read as running too, since a command
// named `[[` on PATH would make it run); an unquoted `(` or `)` between `[[` and `]]` is a syntax error in dash, which then
// runs nothing on the line; `(( x > f ))` is a subshell inside a subshell running the command `x` with that redirection
// (`(( cp a b ))` copies), in command position alone: after `for`, `time`, a wrapper word, an assignment word, `}` or any
// other word the `((` is a syntax error in dash and runs nothing (`for (( ... ))`: "Bad for loop variable"); `$(( ... ))`
// is arithmetic in dash whatever its parentheses, while bash and zsh read a `$((` whose first `(` closes before the last as
// `$( (`, a command substitution, and run its list (`echo $((x > f);(y))` wrote f in both); a `$(...)` or backtick inside
// any arithmetic body runs in all three. A process substitution among the test's operands (the addendum's fix-up, 2026-09-20,
// by execution) is performed by bash in every position (`[[ -f <(echo x > f) ]]` wrote f alone, after `!`, as an if or while
// condition, in a group, in a called function, after `&&`, inside `$(...)`), by zsh after `!`, in a pipeline (on either side of
// the `|`), backgrounded with `&`, with `|&` and under `coproc` (each measured writing f), while zsh rejects it alone, in `( )`, in
// a group, as an if condition, in a called function, inside `$(...)` and through `zsh -c` (`process substitution <(...) cannot be
// used here`, nothing written), and by dash never (`<` and an unquoted `(`: a syntax error, nothing on the line runs); an operator glued to the closing `]]` (`[[ a ]]>f`) is a redirection on the test in bash and zsh and in
// dash the command's redirection after its operand `]]`: all three wrote f. `sh` may be dash or bash and takes both readings; a
// shell not in this set takes the dash reading alone (the lexer's `testGrammar` and `dashGrammar`).
const TEST_ARITH_SHELLS = new Set(['bash', 'zsh', 'ksh']);
// The constructs read in both grammars, with each reading's text for the refusal (the lexer reads the two command-position
// heads and the expansion at their characters; this table carries what each shell makes of them, and the matrix generator
// in tools/romp-track-bash-guard.test.mjs derives its head population from the command-position entries and pins the key set
// of this table by kind, so a head added here without a matrix kind reds a pin: a command-position head changes the fixture's row
// count, an `expansion: true` head the key set the fixture lists; round 6's second commit, ruling F). `via` is appended to a write's `how`
// (`> redirection`, `cp`) when the write was found through the construct's dash reading, so the refusal names dash and the
// construct; `expandVia` when it was found through a substitution inside the body, which every shell runs.
export const CONSTRUCT_HEADS = {
  '[[': { closer: ']]', bash: 'the test keyword: a `>` or `<` between them compares; an expansion among them (`$(...)`, a backtick, `<(...)`) is performed first and its command runs; the grammar ends at the unquoted `]]`, an operator glued to it a redirection or list operator', dash: 'a command named `[[`: its operands words, every redirection among them performed before the lookup fails, the words after a `&&` or `||` a further command', via: ' inside a `[[ ... ]]` (a comparison in bash and zsh; dash has no `[[`, runs a command named so and performs the redirection)' },
  '((': { closer: '))', bash: 'arithmetic: a `>` compares', dash: 'in command position, a subshell inside a subshell running the body as a command list; after any other word a syntax error', via: ' inside a `(( ... ))` (arithmetic in bash and zsh; dash has no `((`, runs its body as a command list in a subshell)', expandVia: ' inside a `$(...)` in a `(( ... ))` body (an expansion every shell runs)' },
  '$((': { closer: '))', expansion: true, bash: 'arithmetic when the `(` after `$(` closes at the very end, else `$( (`, a command substitution whose list runs', dash: 'arithmetic, whatever the parentheses inside', via: ' inside a `$(( ... ))` whose first `(` closes before the last (`$( (` to bash and zsh, a command substitution they run; arithmetic to dash)', expandVia: ' inside a `$(...)` in a `$(( ... ))` body (an expansion every shell runs)' },
};
// The text a write found inside a `${...}` word carries in its refusal (nestedExpansions), and the nesting depth past which the
// `${` read stops descending (the command is marked opaque; the shells reject such a depth long before).
export const BRACE_WORD_VIA = ' inside a `${...}` word (an expansion the shell performs before the word is used, in every position)';
const NESTED_DEPTH_CAP = 64;
// THE THIRD FIX-UP (round 5's fifth addendum, 2026-09-20; the second fix-up's two verifiers found seven live classes, each present
// at the pushed head, four of them written by bash, zsh and dash; the rules are stated at their homes below: readHeredocBodies,
// resolvedSub, defaultReading and the `=(` read in lex, shellScript, and extract's stdinBodies). The names a script operand can
// give the standard input, so `bash /dev/stdin`, `sh /dev/fd/0` and `python3 /dev/stdin` read the script the pipe or the
// here-document feeds them (each measured writing in bash, zsh and dash); the text a write found inside an unquoted here-document
// body carries in its refusal; and the text a script the guard resolved carries.
const STDIN_NAMES = new Set(['-', '/dev/stdin', '/dev/fd/0', '/proc/self/fd/0']);
// A script operand that names what this command feeds the shell: the standard input by one of its names, or ANY descriptor by number
// (`/dev/fd/N`, `/proc/self/fd/N`; round 6's third commit, 2026-09-21: `bash /dev/fd/3 3<<'EOF' .. EOF` ran the body in bash, zsh and dash
// and `bash /dev/fd/9 9<<< 'cp a b'` in bash and zsh while the operand was read as a script file whose contents are not in the command).
// The lexer keeps no descriptor on a here-document or here-string body, so such an operand reads every body the command carries, the
// standard input's among them: an over-read on the safe side (a body on another descriptor is refused as the script when it writes).
const isStdinName = (text) => STDIN_NAMES.has(text) || /^\/(?:dev|proc\/self)\/fd\/[0-9]+$/.test(text);
const fdOfName = (text) => { const m = text.match(/^\/(?:dev|proc\/self)\/fd\/([0-9]+)$/); return m ? m[1] : null; };   // the numbered descriptor a script operand names (`/dev/fd/3`), null for the standard input's own names (THE DESCRIPTOR FEED, round 6's fourth commit)
export const HEREDOC_BODY_VIA = ' inside an unquoted here-document body (an expansion every shell performs before the command reads the body)';
export const READING_VIA = (raw) => ` as a text the word \`${raw}\` stands for (a script formed from it is read under each text it can stand for)`;
// The mark of text the lexer resolved from a substitution ('e', THE RESOLVED SUBSTITUTION in lex): unquoted for a glob, since bash
// and dash glob a substitution's result (`sed -i .. $(echo '*.md')` rewrote the match in both, measured; zsh does not), never a
// brace list (`> $(echo '{a,b}.md')` writes the literal name in all three) and never a reserved word (no expansion's result is one).
const isGlobMark = (m) => m === 'u' || m === 'e';
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
function expansionAt(src, pos, zsh = false) {
  for (const spelling of NUMERIC_EXPANSIONS) if (src.startsWith(spelling, pos)) return { kind: 'numeric', len: spelling.length };
  const next = src[pos + 1];
  // zsh's unbraced expansion flags (round 6's third commit, 2026-09-21; zshexpn, Parameter Expansion: `$=spec`, `$^spec` and `$~spec`
  // are `${=spec}`, `${^spec}` and `${~spec}` without the braces, the value word-split, rc-expanded or glob-substituted): an expansion
  // of the name under zsh's grammar, where before the `$` was a literal dollar, so `X=report.md; cp ../base/report.md $~X` from docs/
  // was judged on the text `$~X` and allowed while zsh copied onto the tracked file, `$^X` the same, and `cp "$=X"` with two paths in
  // X was read as a one-operand cp (the split rule never saw it) while zsh split and copied. In bash and dash the `$` before `=`, `^`
  // or `~` is a literal dollar, and a script handed to either keeps that reading; the Bash tool's own command is read under both.
  if (zsh && next != null && '=^~'.includes(next)) {
    let k = pos + 1;
    while (k < src.length && '=^~'.includes(src[k])) k++;
    const name = src.slice(k).match(/^(?:[A-Za-z_][A-Za-z0-9_]*|[0-9]+|[?!#@*$-])/);
    return { kind: 'var', len: (k - pos) + (name ? name[0].length : 0) };
  }
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
  for (let i = 0; i < text.length; i++) if (isGlobMark(marks[i]) && (text[i] === '*' || text[i] === '?' || text[i] === '[')) return true;
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

// The index of the `)` that closes the `(` at `text[0]`, quotes and escapes honoured as skipNested honours them; -1 when
// none does. Tells a `$(( ... ))` that is arithmetic in every shell (the `(` after `$(` closes at the very end) from a `$((`
// bash and zsh read as `$( (` (round 5's fifth addendum).
function parenCloseAt(text) {
  let depth = 0;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (c === '\\') { i++; continue; }
    if (c === "'") { const e = text.indexOf("'", i + 1); if (e < 0) return -1; i = e; continue; }
    if (c === '"') { i++; while (i < text.length && text[i] !== '"') { if (text[i] === '\\') i++; i++; } continue; }
    if (c === '(') depth++;
    else if (c === ')') { depth--; if (depth === 0) return i; }
  }
  return -1;
}
// `arith` holds the bodies of `(( ... ))` and `$(( ... ))`, which run in the current shell and can assign a name
// (`(( HOME = 5 ))`), for the assignment scan (the walk-around lens second pass, 2026-09-19); they are never lexed as commands.
// `viaSubs` holds the command lists a construct's other reading runs, each with the text the refusal appends (round 5's fifth
// addendum, 2026-09-20): a `(( ))` body under dash's reading, a `$((` bash and zsh read as `$( (`, and every `$(...)` or backtick
// inside an arithmetic body; `dashPieces` the further commands dash reads after a `&&` or `||` inside a `[[ ... ]]`, spliced into
// extract's walk after the test's segment (withDashPieces), and `dashFirstOp` the operator that joins the first of them.
const newSegment = () => ({ words: [], redirects: [], heredocs: [], stdin: [], dups: [], outDups: [], subs: [], arith: [], arithAt: [], viaSubs: [], dashPieces: null, dashFirstOp: '', op: '', start: 0, paramAssigns: [] });   // paramAssigns: the `${name:=word}` assignments the segment's words perform, name and the word's texts (null: a text the resolver could not establish), for THE HEAD CANDIDATES (THE ASSIGNED DEFAULT, round 6's sixth commit)   // dups: the input descriptors this command duplicates, `[n]<&m` as { to: n or '0', from: m, or null for a word the lexer cannot read } (THE DUPLICATED DESCRIPTOR, round 6's fifth commit: `exec 3< <(echo '..'); bash <&3` read the text through 3 while the `<&` was skipped)   // start: the source index the segment begins at (extract counts the lines before it: THE ALIAS ROAD applies to a later line)   // stdin: the words a `<` redirects into the standard input (the third fix-up: `bash < <(echo '..')` reads the script the substitution prints)   // arithAt: the number of words before each `(( ))` (round 5's third addendum: compoundBody tells `if (( 0 )) {` from `if { cond } {` by it)

// `shell` is the name of the shell the command is a script of, when the call is a recursion into `sh -c '...'`,
// `bash <<EOF` or a `$(...)` inside one (null for the Bash tool's own command): it decides whether `$'...'` is
// ANSI-C quoting (ANSI_C_SHELLS). The numeric set is the same in every shell (round 3).
export function lex(command, shell = null, opts = {}) {
  const src = String(command);
  const ansiCQuoting = shell == null || ANSI_C_SHELLS.has(shell);
  // The nested read's options (round 5's fifth addendum, second fix-up, 2026-09-20; nestedExpansions below): the inner text of a
  // `${...}` word is lexed with this function, where a `#` opens no comment (`${x:-a #$(cmd)}` runs cmd in bash, zsh and dash,
  // measured) and, when the word stands inside double quotes, a single quote is a character (`"${x:-'$(cmd)'}"` runs cmd in all
  // three, where the unquoted `${x:-'$(cmd)'}` runs nothing) and a `$'` is a dollar; a `<(` is read as the process substitution
  // it is anywhere (bash performs it inside a double-quoted word's pattern, replacement and message parts, `"${x#<(cmd)}"`,
  // `"${x/b/<(cmd)}"`, `"${x:?<(cmd)}"`, measured writing; no shell performs it in `"${x:-<(cmd)}"` and its kin, a priced cost).
  // `depth` counts the nesting, capped so a `${` inside a `${` thousands deep cannot overflow the stack.
  const comments = opts.comments !== false;
  const dqInner = opts.quotes === 'double';
  const nestDepth = opts.depth || 0;
  // The third fix-up's modes (2026-09-20). `heredoc`: an unquoted here-document body, one word of text whose `$(...)`, backticks,
  // `${...}` and `$name` every shell performs before the command reads the body, a backslash quoting only `$`, a backtick, a
  // backslash and a newline, every other character (a quote, a blank, an operator) text (readHeredocBodies). `oneWord`: the word of a
  // `${...}` operator, where a blank, a `#`, a `;`, a `&`, a `|`, a parenthesis and a `<` or `>` not opening a process substitution
  // are characters of the word (defaultReading). `braceWord`: the inner text of a `${...}` (nestedExpansions, defaultReading), where
  // zsh performs `=(cmd)` after the operator too. `noSplit`: the word stands where no shell splits an expansion's result (inside double
  // quotes, a here-string, a here-document body, the word of a `${...}` operator, which zsh never splits), so a resolved substitution is
  // one text there; a redirection target is not such a place (bash and zsh split it, dash does not: THE SPLIT TARGET at endWord). `ifsNamed`: the command names IFS, so an unquoted substitution's result splits by a rule
  // the guard does not read, and is not resolved among operands.
  const hdInner = opts.quotes === 'heredoc';
  const oneWord = !!opts.oneWord;
  const braceWord = !!opts.braceWord;
  const noSplitOpt = !!opts.noSplit;
  const ifsNamed = opts.ifsNamed != null ? opts.ifsNamed : /\bIFS\b/.test(src);
  // The two grammars (round 5's fifth addendum, 2026-09-20). Under testGrammar (the Bash tool's own command, `sh`, and the shells
  // of TEST_ARITH_SHELLS) `[[` in command position is the test keyword and `((` opens arithmetic; under dashGrammar (the same
  // command and `sh`, and every shell not in that set) the dash reading is added at closeTest and skipArithmetic, and for a script
  // handed to dash itself it is the only reading: `[[` is a plain word there, `((` two `(`, read by the paren path as dash reads them.
  const testGrammar = shell == null || shell === 'sh' || TEST_ARITH_SHELLS.has(shell);
  const dashGrammar = shell == null || shell === 'sh' || !TEST_ARITH_SHELLS.has(shell);
  const zshGrammar = shell == null || shell === 'zsh';   // zsh's own forms (`=(cmd)`, the third fix-up): read for the Bash tool's command, whose shell is not known, and for a script handed to zsh
  const segments = [];
  const lexScopes = [];   // THE PAREN RULE's scopes, innermost last: 'subshell' at a `(` marker, 'case' at a segment headed by `case` (its `esac` drops it and every scope inside), asked at each `)` through parenCloses
  let seg = newSegment();
  let buf = '';
  let raw = '';
  let marks = '';
  let sawExpansion = false;   // the word carries an expansion the hook cannot resolve
  let numericOnly = true;     // every expansion so far is `$$` or `${$}` (meaningful with sawExpansion)
  let inWord = false;
  let opaque = false;
  let inTest = false;   // inside [[ ... ]], where > and < compare strings (bash and zsh; dash's reading is added when the test closes)
  let testStart = -1;   // the source index after the `[[` that opened the test, for its dash reading (closeTest)
  let opAt = -1;        // the source index of the operator ending the segment under way (the test's span ends there when no `]]` closed it)
  // what the next word is: a redirect target, a heredoc delimiter, a here-string, or data (<)
  let expect = null;
  let inDq = false;          // inside a double-quoted string of the main loop (a resolved substitution is one text there)
  let wordReadings = null;   // the texts the word under way can stand for beyond its spelling, with the spelling they belong to (THE RESOLVED SUBSTITUTION, THE DEFAULT WORD)
  let wordUnresolvable = null;   // { raw, why }: the resolver looked at an expansion of the word under way and could not establish its text (THE RESOLVER'S CONTRACT: placeReading below)
  let wordMayReadStdin = null;   // the spelling of a `$(...)`, a backtick or a `<(...)` of the word under way whose list the resolver does not read (THE FED SUBSTITUTION, round 6's fourth commit: its command may read the standard input, and extract's scriptTexts refuses it where this command feeds that input with a text it read)
  let fdDigits = null;       // the descriptor number glued before the operator being read (`3<`), so a `<` on another descriptor is not the standard input
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
  // The texts the word under way can stand for beyond its spelling, when the word is the expansion that carries them alone
  // (unquoted or inside double quotes): THE RESOLVED SUBSTITUTION's two echo readings and THE DEFAULT WORD (both below).
  // the literal text around the expansion that carries the word's readings ({ before, after }; both empty when the word is the expansion
  // alone), or null when the word holds more than that one expansion
  const glueOf = () => {
    if (!wordReadings) return null;
    if (raw === wordReadings.raw || raw === '"' + wordReadings.raw + '"' || (oneWord && raw.endsWith(wordReadings.raw))) return { before: '', after: '' };   // in a `${...}` word (oneWord) the name and operator precede the expansion, so a default word that is one `${...}` carries the inner readings up (`${x:-${y:-cp a b}}`)
    // THE GLUED READING (round 6's fourth commit, 2026-09-21): the expansion glued to literal text stands for each reading with that text
    // around it (`${c:-c}p a b` ran cp in every shell while the default word's reading `c` was dropped for the glued `p`; a `NAME=<(..)`
    // assignment's value is the file the substitution stands for): the word's one run of expansion marks is the expansion, its
    // spelling or the NUL a substitution stands as, and the text on either side is literal
    const runs = [...marks.matchAll(/x+/g)];
    if (runs.length !== 1) return null;
    const [r] = runs;
    const inner = buf.slice(r.index, r.index + r[0].length);
    if (inner !== wordReadings.raw && inner !== '\0') return null;
    const before = buf.slice(0, r.index);
    const after = buf.slice(r.index + r[0].length);
    if (before.includes('\0') || after.includes('\0')) return null;
    return { before, after };
  };
  const readingsOf = () => { const g = glueOf(); return g ? wordReadings.texts.map((t) => g.before + t + g.after) : []; };
  // THE DEFAULT WORD's params with the glue around the expansion (round 6's fifth commit: `eval "${c:-cat} a b"` with c=cp ran `cp a b`, so the
  // value stands where the expansion stands, the literal text around it kept), null when the word holds another expansion beside it
  const paramsOf = () => { if (!wordReadings || !wordReadings.params) return null; const g = glueOf(); return g ? wordReadings.params.map((p) => ({ ...p, before: g.before + (p.before || ''), after: (p.after || '') + g.after })) : null; };
  const glueUnresolvable = () => ({ raw: wordReadings.raw, why: `the word glues \`${wordReadings.raw}\`, whose text depends on a parameter's value, to another expansion, so the text the word stands for is not known` });   // a default word beside another expansion in one word (`${c:-cat}$x`): the value would stand in a text the resolver cannot compose
  // THE SPLIT TARGET (round 6's third commit, 2026-09-21): the fields bash and zsh make of a resolved substitution's text at a
  // redirection target, the text cut at every blank the resolver placed (an 'e' mark; a quoted blank is text in every shell), the
  // empty fields dropped; none when no such blank cuts it (the whole text is then the one redirection endWord already records).
  const expandedFields = (t, m) => {
    const out = [];
    let s = 0;
    for (let k = 0; k <= t.length; k++) if (k === t.length || (m[k] === 'e' && /[ \t\n]/.test(t[k]))) { if (k > s) out.push([t.slice(s, k), m.slice(s, k)]); s = k + 1; }
    return out.length === 1 && out[0][0] === t ? [] : out;
  };
  const endWord = () => {
    if (!inWord) return;
    if (expect) {
      if (expect.kind === 'target') {
        // a target that brace-expands to several words: bash's ambiguous redirect writes nothing, zsh's
        // multios writes each (2026-09-18), so each is a redirection of its own; past the cap the word is one
        // the hook cannot read
        const alts = braceExpand(buf, marks);
        if (alts) for (const [t, m] of alts) seg.redirects.push({ op: expect.op, target: mk(t, m), fd: expect.fd });
        else seg.redirects.push({ op: expect.op, target: word(buf, false, raw, { marks }), fd: expect.fd });   // `fd`: the descriptor opened, for THE WRITTEN PROCESS SUBSTITUTION (null: the standard output)
        // THE SPLIT TARGET (round 6's third commit, 2026-09-21; the round's verifiers): a resolved substitution placed unquoted at a
        // redirection target is split at its blanks by bash and zsh (zsh opens every field under MULTIOS, on by default; bash opens
        // the one field, or given several refuses the ambiguous redirect and writes nothing) and not by dash, which opens the whole
        // text, so each field is a redirection of its own beside the whole text: `echo x > $(echo 'report.md ')` from docs/ wrote
        // report.md in bash and zsh and `> $(echo x report.md)` wrote x and report.md in zsh, while the guard judged the whole text
        // alone ('report.md ', 'x report.md': untracked names) and allowed both. Every shell's target is now among the redirections.
        if (/[ \t\n]/.test(buf)) for (const [t, m] of expandedFields(buf, marks)) seg.redirects.push({ op: expect.op, target: mk(t, m) });
        // M2: bash reads the `!` zsh consumed as the first character of the target word, so a glued `>!docs/report.md`
        // is a write of `!docs/report.md` there (the spaced form's bash target, a file named `!`, was recorded at the
        // operator); both readings are judged, and the refusal names the one that lands on a tracked file
        if (expect.bang === 'glued') seg.redirects.push({ op: expect.op, target: mk('!' + buf, 'u' + marks) });
      } else if (expect.kind === 'heredoc') pendingHeredocs.push({ delim: buf, stripTabs: expect.stripTabs, owner: seg, quoted: /q/.test(marks) });   // any quoted character in the delimiter: the body is not expanded (the third fix-up, readHeredocBodies)
      else if (expect.kind === 'dup') {
        // THE DUPLICATED DESCRIPTOR (round 6's fifth commit, 2026-09-21; the body auditor: `exec 3< <(echo 'cp a b'); bash <&3`, `bash 0<&3`,
        // `bash 3< <(..) <&3`, `{ bash; } 3< <(..) <&3` and `cat <&3 | bash` ran the printed text in bash and zsh while the `<&` was skipped): the
        // word is the descriptor duplicated onto `n` (bash: REDIRECTION, Duplicating File Descriptors; dash(1) and zshmisc(1) alike), a run of
        // digits, with a `-` after it moving it; `-` alone closes and duplicates nothing; a word the lexer cannot read (an expansion) may name any
        // descriptor, recorded as null, so a consumer reading `n` reads every descriptor this command feeds (the safe side)
        const m = buf.match(/^([0-9]+)-?$/);
        if (buf !== '-') seg.dups.push({ to: expect.fd == null ? '0' : expect.fd, from: m && !sawExpansion ? m[1] : null });
      }
      else if (expect.kind === 'herestring') {
        // a word with readings stands for each of them, and for nothing else (the third fix-up); one the resolver could not establish is
        // recorded on the segment's stdin for scriptTexts to refuse (THE RESOLVER'S CONTRACT), never handed to the consumer as its spelling;
        // one whose readings depend on a parameter's value (THE DEFAULT WORD's params, round 6's fifth commit) is recorded there too, so
        // scriptTexts reads the value beside the word
        const rd = readingsOf();
        if (wordUnresolvable) seg.stdin.push(Object.assign(word(buf, false, raw, { marks }), { fd: null, unresolvableReading: wordUnresolvable, herestring: true }));
        else if (wordReadings && wordReadings.params) { const ps = paramsOf(); seg.stdin.push(Object.assign(word(buf, false, raw, { marks }), ps ? { fd: null, readings: rd, readingParams: ps, herestring: true } : { fd: null, unresolvableReading: glueUnresolvable(), herestring: true })); }
        else if (rd.length) seg.heredocs.push(...rd);
        else seg.heredocs.push(buf);
      }
      else if (expect.kind === 'data') {
        // a `<` into the standard input, or into the descriptor numbered before it (the third fix-up); the word carries the readings a
        // `<(echo '..')` stands for and the resolver's mark, for extract's scriptTexts (THE RESOLVER'S CONTRACT)
        const rd = readingsOf();
        const extra = { fd: expect.fd == null ? null : expect.fd };
        if (rd.length) extra.readings = rd;
        if (wordReadings && wordReadings.params) { const ps = paramsOf(); if (ps) { extra.readings = rd; extra.readingParams = ps; } else extra.unresolvableReading = glueUnresolvable(); }
        if (wordUnresolvable) extra.unresolvableReading = wordUnresolvable;
        if (wordMayReadStdin) extra.mayReadStdin = wordMayReadStdin;   // THE FED SUBSTITUTION: `bash < <(head -1)` after a pipe reads the piped text
        seg.stdin.push(Object.assign(mk(buf, marks), extra));
      }
      expect = null;
    } else {
      // the keyword: unquoted, in command position (first in its segment, or after unquoted reserved words alone; round 5's
      // fourth addendum: after `echo "{"`, `echo {` or `echo "if"` the `[[` and its `>` are echo's operands and a redirection,
      // which bash and dash perform, so `echo "{" [[ x > report.md ]]` from docs/ truncated the tracked file while the guard
      // read a comparison)
      if (testGrammar && raw === '[[' && seg.words.every((w) => plainWord(w) && RESERVED.has(w.text))) { inTest = true; testStart = i; }
      else if (raw === ']]' && inTest) closeTest(i - 2, true);
      const alts = braceExpand(buf, marks);
      if (!alts) seg.words.push(word(buf, false, raw, { marks }));
      else for (const [t, m] of alts) { const bw = mk(t, m); if (alts.length > 1 && t === '') bw.braceEmpty = true; seg.words.push(bw); }   // THE EMPTY ALTERNATIVE (round 6's sixth commit): an empty alternative of a brace list is a word bash drops and zsh keeps (extract judges both readings)
      const rd = readingsOf();
      if (rd.length && (!alts || alts.length === 1)) seg.words[seg.words.length - 1].readings = rd;   // the word alone carries its readings (THE RESOLVED SUBSTITUTION, THE DEFAULT WORD)
      if (wordReadings && wordReadings.params && (!alts || alts.length === 1)) { const ps = paramsOf(); const last = seg.words[seg.words.length - 1]; if (ps) { last.readings = rd; last.readingParams = ps; } else last.unresolvableReading = glueUnresolvable(); }   // THE DEFAULT WORD's params (round 6's fifth commit): the names whose values the readings depend on, with the glue around the expansion, read beside the texts in extract's scriptTexts (the readings may be none: `${c:?}` stands for the value alone); glued to another expansion, the word is UNRESOLVABLE
      if (wordUnresolvable) for (let k = alts ? alts.length : 1; k > 0; k--) seg.words[seg.words.length - k].unresolvableReading = wordUnresolvable;   // every word the expansion is part of (each brace alternative) carries the mark (THE RESOLVER'S CONTRACT)
      if (wordMayReadStdin) for (let k = alts ? alts.length : 1; k > 0; k--) seg.words[seg.words.length - k].mayReadStdin = wordMayReadStdin;   // THE FED SUBSTITUTION
    }
    buf = ''; raw = ''; marks = ''; sawExpansion = false; numericOnly = true; inWord = false; wordReadings = null; wordUnresolvable = null; wordMayReadStdin = null;
  };
  // A word of the test's own grammar (`>` or `&&` inside [[ ... ]]): ends any word under way, stands alone.
  const bareWord = (t) => { endWord(); inWord = true; buf = t; raw = t; marks = 'u'.repeat(t.length); endWord(); };
  const endSegment = (op) => {
    endWord();
    if (expect) expect = null;   // a redirect with no target: leave it
    if (inTest) closeTest(opAt);   // a test the operator ends before its `]]`: dash's command ends at the same operator
    inTest = false;
    seg.op = op;
    seg.shell = shell;   // THE SPLICED PRINTER (round 6's seventh commit) re-lexes a spliced command name under this segment's grammar
    // THE PAREN RULE's scopes (round 6's eighth commit): a segment headed by `case` opens a case body; its `esac` closes it and every scope opened inside
    { const head = compoundHeadOf(seg.words); if (head === 'case') lexScopes.push('case'); else if (head != null && Object.hasOwn(CLOSERS, head) && CLOSERS[head].includes('case')) { const j = lexScopes.lastIndexOf('case'); if (j >= 0) lexScopes.length = j; } }
    // THE SITE a segment prints from, for THE PIPED SCRIPT (a `|` after it) and THE WRITTEN PROCESS SUBSTITUTION (a write redirection
    // on it whose target is `>(cmd)`): { kind, spelling, target, segs } with `kind` a simple command ('segment'), the list a closer ends
    // ('subshell', 'group', a keyword closer's name), dash's `(( ))` ('arith'), `target` the segment the reading is placed on; null outside
    // the model. The reading itself is streamOutput's (a reading function, called as placeReading's argument alone: THE RESOLVER'S CONTRACT
    // is structural), given `view`, the segment with the redirections that carry the text removed (a pipe carries it on none; a process
    // substitution on one), so every other redirection on it still makes the text UNRESOLVABLE (shapeOnPrinter, closerOutput).
    const streamSite = (view) => {
      if (view.words.length && !(view.words.length === 1 && plainWord(view.words[0]) && (view.words[0].text === '}' || Object.hasOwn(CLOSERS, view.words[0].text)))) return { kind: 'segment', spelling: view.words.map((w) => w.raw).join(' '), target: seg };   // THE PIPED SCRIPT: the producer's printed text, for extract's pipedScripts (THE RESOLVER'S CONTRACT); every piped segment with words is asked since round 6's seventh commit (segmentOutput answers null for a head that is no printer, and a head that is an expansion THE HEAD CANDIDATES resolve is read through THE SPLICED PRINTER), where the gate had been a literal echo or printf among the words; a `}` or a keyword closer alone falls to its own branch below (THE OUTPUT MODEL reads the group or compound around it)
      if (!view.words.length && segments.length && segments[segments.length - 1].paren === ')') {
        // THE OUTPUT MODEL (round 6's second commit, 2026-09-20; round 5's tests-1: `(echo 'cp ..') | bash` was pinned allowed under a label
        // that called the producer one the guard cannot read, while bash, zsh and dash ran the copy): a subshell before the pipe prints
        // what the list between its parentheses prints, so listOutput's reading of that list is placed on the `)` marker that carries
        // the pipe (producerAt finds it as the segment before the consumer)
        const close = segments.length - 1;
        let depth = 0;
        let open = -1;
        for (let j = close; j >= 0 && open < 0; j--) { if (segments[j].paren === ')' && !segments[j].pattern) depth++; else if (segments[j].paren === '(' && --depth === 0) open = j; }   // a `)` ending a case pattern pairs with no `(` (THE PAREN RULE)
        if (open < 0) return null;
        return { kind: 'subshell', segs: segments.slice(open + 1, close), spelling: spellingOf(segments.slice(open, close + 1)), target: seg.redirects.length || seg.heredocs.length || (seg.stdin && seg.stdin.length) ? seg : segments[close] };   // with a redirection after the `)` this segment is pushed and carries the pipe (producerAt reads the segment before the consumer), else the `)` marker does
      }
      if (view.words.length === 1 && plainWord(view.words[0]) && view.words[0].text === '}') {
        // and a `{ }` group before the pipe (its closer heads this segment, splitAtClosers's cut): the list from the segment holding the
        // matching `{` to here, placed on this closer segment
        let depth = 1;
        let open = -1;
        for (let j = segments.length - 1; j >= 0 && open < 0; j--) {
          for (let k = segments[j].words.length - 1; k >= 0; k--) {
            const w = segments[j].words[k];
            if (!plainWord(w)) continue;
            if (w.text === '}') depth++;
            else if (w.text === '{' && --depth === 0) { open = j; break; }
          }
        }
        return open >= 0 ? { kind: 'group', segs: segments.slice(open), spelling: spellingOf(segments.slice(open)) + ' }', target: seg } : null;
      }
      if (view.words.length === 1 && plainWord(view.words[0]) && Object.hasOwn(CLOSERS, view.words[0].text)) {
        // THE COMPOUND PRODUCER (round 6's fourth commit, 2026-09-21; the round's verifiers: `for i in 1; do echo 'cp a b'; done | bash`,
        // `while`, `until`, `if` and `case` before the pipe each ran the echoed text in bash, zsh and dash while the producer was neither
        // read nor refused): a keyword compound before the pipe prints what the list from its head to this closer prints, and the head
        // itself (a loop that runs its body some number of times, a condition that may not) is a command the model does not read, so a
        // printer inside it makes the list UNRESOLVABLE (refused as the consumer's script) and a body with no printer stays outside the
        // model (the residual); placed on this closer segment, which carries the pipe
        const closer = view.words[0].text;
        let depth = 1;
        let open = -1;
        for (let j = segments.length - 1; j >= 0 && open < 0; j--) {
          const h = compoundHeadOf(segments[j].words);
          if (h === closer) depth++;
          else if (h != null && CLOSERS[closer].includes(h) && --depth === 0) open = j;
        }
        return open >= 0 ? { kind: `\`${closer}\``, segs: segments.slice(open), spelling: spellingOf(segments.slice(open)) + ' ' + closer, target: seg } : null;
      }
      if (dashGrammar && !view.words.length && view.arith.length === 1 && !view.redirects.length && nestDepth < NESTED_DEPTH_CAP) {
        // and dash's reading of `(( list ))` in command position before the pipe, a subshell inside a subshell running the list (round 6's
        // fourth commit: `((echo 'cp a b')) | bash` ran the echoed text in dash while bash and zsh read arithmetic and stopped): what the
        // list prints is the pipe's text under dash, so its reading is the producer's (bash and zsh print nothing there, a reading the
        // consumer's refusal covers)
        return { kind: 'arith', text: view.arith[0], depth: nestDepth + 1, spelling: '((' + view.arith[0] + '))', target: seg };
      }
      return null;
    };
    if (op === '|') { const site = streamSite(seg); if (site) placeReading(streamOutput(site, seg), site.spelling, 'segment', site.target); }
    // THE WRITTEN PROCESS SUBSTITUTION (round 6's ninth commit, 2026-09-22; the round's verifiers: `echo 'cp a b' > >(bash)` ran the text in
    // bash and zsh while allowed, and `printf`, `1>`, `>|`, `>>`, `&>`, zsh's `>>(bash)`, `>(sh)`, `>(zsh)`, `>(dash)`, `>(env bash)`, `>(command
    // bash)`, `>(bash -s)`, `>(cat | bash)`, a subshell or a group before the redirection, `exec > >(bash)`, `3> >(bash) >&3`, `exec 3> >(bash)`
    // with a later `>&3`, a resolved `$e` printer bare and behind `command`, an echoed `echo poison > report.md` and `sed -i` the same, where
    // the same `>(bash)` fed by a tee or a cat was read): a write redirection whose target is a process substitution `>(cmd)` is a pipe
    // into cmd (bash: Process Substitution; zshexpn(1)), so what the command writes on that descriptor is cmd's standard input, read as THE
    // PIPED SCRIPT is: the segment's own printed text where the redirection is on the standard output, or on a descriptor a `>&` of this
    // command routes it to (outDups), the list's text where the redirection stands on a closer, UNRESOLVABLE where an `exec` opens it for
    // every later command (whose output the model does not follow), and outside the model on another descriptor or from a command that is
    // no printer (a cat of a file: the residual the property names). The reading is kept beside the substitution's text (procsubFeeds) for
    // extract's recurseSubs, which reads cmd with that text as its standard input (its consumers refuse an UNRESOLVABLE text as a piped one).
    {
      const fedSubs = seg.redirects.filter((r) => WRITE_REDIRECTS.has(r.op) && r.target.text.startsWith('>(') && procsubOf(r.target) != null);
      if (fedSubs.length) {
        const fedInner = new Set(fedSubs.map((r) => procsubOf(r.target)));
        const view = { ...seg, redirects: seg.redirects.filter((r) => !fedSubs.includes(r)), subs: seg.subs.filter((t) => !fedInner.has(t)) };   // the substitution fed is the road, not an operand's substitution (shapeOnPrinter)
        const c = seg.words.length ? commandOf(seg.words) : null;
        const isExec = !!(c && c.wrapped && c.name === '' && !c.args.length && c.wrappers.includes('exec'));
        // THE ROUTED STANDARD OUTPUT (round 6's tenth commit, 2026-09-22; the round's verifiers: `echo TXT 3> >(bash) 2>&3 1>&2` ran the text
        // in bash and zsh while the one-hop check missed the chain fd1->fd2->fd3->`>(bash)`): the standard output reaches the descriptor a
        // process substitution opens not only when a single `>&` routes it there but along a chain of them, so onStdout follows the dup
        // graph. The two arrays (seg.redirects, seg.outDups) keep no interleaved order, so the walk over-approximates (a `>&` is treated as
        // reaching wherever its target reaches, whatever the order the shell applied them): a reversed chain that leaves fd1 at the terminal
        // is refused all the same, the safe side of a route the guard does not order.
        const groupSite = isExec ? null : streamSite(view);   // a subshell, group or keyword compound before the redirection carries the pipe; its body's own `>&` routes its output to the opened descriptor (the round's verifiers: `{ echo TXT >&3; } 3> >(bash)`)
        const dupsHere = [...seg.outDups, ...(groupSite && groupSite.segs ? groupSite.segs.flatMap((s) => s.outDups || []) : [])];
        const onStdout = (r) => {
          const fd = r.fd == null ? '1' : r.fd;
          const reach = new Set([fd]);
          for (let grew = true; grew;) { grew = false; for (const d of dupsHere) if (reach.has(d.to) && !reach.has(d.from)) { reach.add(d.from); grew = true; } }
          return reach.has('1');
        };
        seg.procsubFeeds = [];
        for (const r of fedSubs) {
          const site = isExec ? { kind: 'exec', spelling: seg.words.map((w) => w.raw).join(' ') } : onStdout(r) ? groupSite : null;
          const holder = {};
          if (site) placeReading(streamOutput(site, view), site.spelling, 'segment', holder);
          seg.procsubFeeds.push({ inner: procsubOf(r.target), printed: holder.printed || null });
        }
      }
    }
    if (seg.words.length || seg.redirects.length || seg.heredocs.length || seg.subs.length || seg.arith.length || seg.viaSubs.length || seg.stdin.length || seg.dups.length) segments.push(seg);   // a segment holding only a `<` or a `<&` (a closer's, after a `)`) is kept too (round 6's sixth commit: `exec 3< <(echo 'cp a b'); (bash) <&3` ran the text in bash and zsh while the dup after the `)` was dropped with its segment, and `(cat <<'EOF' ..) </dev/null | bash` lost THE APPLIED RESOLVER's mark the same way)
    else if (op && segments.length && segments[segments.length - 1].paren && !segments[segments.length - 1].op) {
      // the operator after a `)` (`(cd a) && cd b`): the segment it would end is empty, so it is kept on the paren
      // marker, and a later pass reading the operator before a `cd` sees it (the walk-around lens second pass, 2026-09-19; before, it was lost)
      segments[segments.length - 1].op = op;
    }
    seg = newSegment();
    seg.start = i;
  };
  // the spelling of a run of segments, for a compound producer's reading (the refusal names it)
  const spellingOf = (segs) => segs.map((x) => (x.paren ? x.paren : x.words.map((w) => w.raw).join(' ') + (x.op && x.op !== '|' && x.op !== ')' ? x.op : ''))).join(' ').replace(/\s+/g, ' ').trim();
  // After a newline, the bodies of every heredoc opened on the line just ended, each on the
  // segment that opened it (already pushed by reference when an operator ended it on that line).
  const readHeredocBodies = () => {
    while (pendingHeredocs.length) {
      const { delim, stripTabs, owner, quoted: q } = pendingHeredocs.shift();
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
      const body = lines.join('\n');
      // THE UNQUOTED BODY (round 5's fifth addendum, third fix-up, 2026-09-20; the second fix-up's verifiers found `cat <<EOF` with
      // `$(cp ../base/report.md report.md)` on the body's line, and with `${x:-$(cp ..)}`, from docs/ allowed while bash, zsh and dash
      // copied: the body was kept as the consumer's data, never lexed, though the shell performs its expansions before any consumer
      // reads it). THE RULE: a here-document whose delimiter has no quoted character has its body expanded by the shell before the
      // command reads it, so a `$(...)`, a backtick, a `${...}` and a `$name` in the body are read as they are anywhere else (a
      // substitution as the command it runs, a `${...}` word's nested expansions and default word, a substitution whose command is a
      // literal echo or printf as the text it prints) and the body the consumer reads is the text after those expansions, where a
      // backslash quotes only `$`, a backtick, a backslash and a newline, and a quote is a character (`${x:-'$(cp a b)'}` in a body
      // runs the copy in all three shells, measured; `<<-` strips the tabs and expands alike); a delimiter with any quoted character
      // (`<<'EOF'`, `<<"EOF"`, `<<\EOF`, `<<E"O"F`) keeps the body as written and runs nothing (measured). The expanded body is the
      // consumer's stdin text (a shell fed by it reads the script the shell will run: `bash <<EOF` with `$(echo 'echo x > report.md')`
      // on a line wrote report.md in all three, the printed text parsed as a redirection, while the same body after `<<'EOF'` runs the
      // echo and prints), and the commands the expansions run join the owning segment's `viaSubs` (`HEREDOC_BODY_VIA`).
      if (q || !/[$`]/.test(body) || nestDepth >= NESTED_DEPTH_CAP) { owner.heredocs.push(body); continue; }
      const x = lex(body, shell, { quotes: 'heredoc', comments: false, depth: nestDepth + 1, ifsNamed });
      if (x.opaque) opaque = true;
      const w = x.segments.length === 1 && x.segments[0].words.length === 1 ? x.segments[0].words[0] : null;
      // the consumer reads the body after the shell's expansions: a body that is one word with readings hands over the readings alone (the
      // spelling is not a text the consumer sees; round 6's second commit, when THE HEAD SPLICE read the spelling `${x:-'cp a b'}` as a
      // plain script and refused a body every shell runs as a quoted command name), any other body its text after quote removal
      if (w && w.readingParams) owner.stdin.push(Object.assign(word(w.text, false, w.raw, { marks: w.marks }), { fd: null, readings: w.readings, readingParams: w.readingParams, herestring: true }));   // a body that is one default word depends on the parameter's value: recorded for scriptTexts to join the value or refuse (THE PARAMETER'S VALUE, round 6's fifth commit: `c=cp; bash <<EOF` with `${c:-cat} a b` as the body ran the copy)
      else if (w && w.readings) for (const t of w.readings) owner.heredocs.push(t);
      else owner.heredocs.push(w ? w.text : body);
      if (w && w.unresolvableReading) owner.stdin.push(Object.assign(word(w.text, false, w.raw, { marks: w.marks }), { fd: null, unresolvableReading: w.unresolvableReading, herestring: true }));   // the body's text is not known: scriptTexts refuses the consumer (THE RESOLVER'S CONTRACT)
      for (const sg of x.segments) {
        for (const t of sg.subs) owner.viaSubs.push({ text: t, via: HEREDOC_BODY_VIA });
        for (const v of sg.viaSubs) owner.viaSubs.push(v);
      }
    }
  };
  // THE RULE (round 5's fifth addendum, 2026-09-20; the fourth addendum's builder measured `[[ x > report.md ]]` from docs/
  // allowed while dash truncated the tracked file, and the reviewer ruled that a construct must be read on the safe side for
  // every shell the guard claims, bash, zsh and dash, not for the grammar it was written against): a construct the hook reads
  // under bash and zsh grammar (`[[ ... ]]`, `(( ... ))`, a `$(( ... ))`) contributes, in addition, its dash reading to the
  // write set: where dash reads the construct as a plain command (`[[`), the words after the head are its operands and every
  // redirection operator among them a redirection dash performs before the command is looked up, and the words after a `&&`
  // or `||` among them a further command; where dash reads it as a subshell (`((`, two nested `(`), its body is a command list
  // dash runs; and each target so found is judged exactly as any redirection or writer the hook already judges. Beside it:
  // a substitution inside an arithmetic body (`$(...)`, a backtick) runs in every shell and is read as a command, and a `$((`
  // whose first `(` closes before the last is a command substitution in bash and zsh and is read as one. The reading holds
  // in every position (alone, after `!`, as an if, while or until condition, in a group, in a pipeline, in a function body,
  // after `&&` or `||`) because it is made here, where the construct is lexed, and the walk judges what it records as it
  // judges every other segment: a literal tracked target refuses by name with `how` naming dash and the construct
  // (CONSTRUCT_HEADS's `via`); a non-literal target takes the hook's existing rule for a non-literal redirection target
  // (refused as not literal while a tracked project is in play, dropped from a cwd in no project), so `[[ $a > $b ]]` with `$b`
  // unreadable is refused from a tracked cwd, a priced cost stated in decision 47 (the remedy in the refusal: compare outside
  // the project, or with `expr`); a `for (( ... ))` head, a `((` after any word but a reserved one, and a `[[` whose operands
  // hold an unquoted parenthesis are syntax errors in dash and get no dash reading (TEST_ARITH_SHELLS states each fact).
  // The rest of the grammar (a here-doc body, a here-string, a process substitution, a quoted string, a brace list) was
  // checked the same way: dash reads a here-doc as data, rejects `<<<` and `>(`/`<(` as syntax errors, reads quotes alike,
  // and writes a brace list's spelling as one literal name (`{a,b}.md`), a residual named in decision 47. THE TEST'S
  // BOUNDARIES (the addendum's fix-up, 2026-09-20; the addendum's verifier found a process substitution among the operands read
  // as two words of the test while bash performed it, `[[ -f <(echo x > report.md) ]]` writing from docs/ in every position,
  // and an operator glued to the closing `]]` read as a word of the test, `[[ a ]]>report.md` writing in all three shells;
  // the population had been the operators among the operands, not every place a write can sit against the construct): the
  // test's grammar covers the words between `[[` and the unquoted `]]` that closes it and only the test's own operators among
  // them; an expansion among the operands (a `$(...)`, a backtick, a `<(...)` or `>(...)`) is performed by the shell before the
  // test reads a word and is read as the command it runs, where it is lexed; and an operator glued to the closing `]]` is
  // outside the test, the redirection or list operator it is anywhere else, read after the test has closed. Both are made at
  // the lexer's operator read, so they hold in every position the construct can stand in; the construct matrix crosses the
  // placement of the write (among the operands, inside a `$(...)` or a `<(...)` among them, glued to the closer, spaced after
  // it) with head, position, operator and target, the placements being the regions a construct has.
  //
  // (( ... )): arithmetic in bash and zsh, no command and no redirection in it; skip to the matching )). Its `$(...)` and
  // backticks run in every shell and are read as commands (viaSubs); in command position dash reads it as a subshell running
  // the body, which is read as a command list under the rule above.
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
    const body = src.slice(start, Math.max(start, i - 2));
    seg.arith.push(body);
    expansionsOf(body, CONSTRUCT_HEADS['(('].expandVia);
    if (dashGrammar && seg.words.every((w) => plainWord(w) && RESERVED.has(w.text))) seg.viaSubs.push({ text: body, via: CONSTRUCT_HEADS['(('].via });
  };
  // The substitutions inside an arithmetic body, each a command every shell runs: read with this lexer and kept with the text the
  // refusal appends (a nested construct's own viaSubs come along).
  const expansionsOf = (body, via) => {
    for (const s of lex(body, shell).segments) {
      for (const t of s.subs) seg.viaSubs.push({ text: t, via });
      for (const v of s.viaSubs) seg.viaSubs.push(v);
    }
  };
  // The dash reading of the test that just closed (the rule above), over the source between `[[` and `end` (the `]]`, or the
  // operator that ended the segment): lexed under dash's grammar as `[[ <span>`, the first segment is the command named `[[`,
  // whose write redirections join this segment's with `how` naming the construct, and every later segment (after a `&&` or
  // `||` dash read) is a further command, kept as a piece for extract's walk. An unquoted parenthesis among the operands is a
  // syntax error in dash, which then runs nothing on the line, so such a test gets no dash reading.
  const closeTest = (end, closed = false) => {
    inTest = false;
    const from = testStart;
    testStart = -1;
    if (!dashGrammar || from < 0) return;
    const span = src.slice(from, Math.max(from, end));
    const dash = lex('[[ ' + span + (closed ? ' ]]' : ''), 'dash');   // the `]]` is the last command's operand in dash (`cp a b ]]` fails on it)
    if (dash.opaque || dash.segments.some((s) => s.paren)) return;
    const [first, ...rest] = dash.segments;
    if (!first) return;
    for (const r of first.redirects) {
      if (!WRITE_REDIRECTS.has(r.op)) continue;
      if (seg.redirects.some((q) => q.op === r.op && q.target.text === r.target.text)) continue;   // recorded by the bash reading too (`&>` inside the test)
      seg.redirects.push({ op: r.op, target: r.target, how: `${r.op} redirection${CONSTRUCT_HEADS['[['].via}` });
    }
    if (!rest.length) return;
    rest.forEach((s, k) => { s.dashPiece = { construct: '[[ ... ]]', op: k === 0 ? first.op : rest[k - 1].op }; });
    seg.dashPieces = [...(seg.dashPieces || []), ...rest];
    if (!seg.dashFirstOp) seg.dashFirstOp = first.op;
  };
  // Skip a $( ... ) or ${ ... } from just after its opener to its closer, quotes honoured (a single quote is a character when
  // the `${` stands inside double quotes, `dq`, as the shells read it: `"${x:-'}'}"` closes at the first brace); a `$(...)`
  // inside a `${...}`, a `${...}` inside a `$(...)` and a backtick inside either are skipped as the units the shells parse
  // them as, so a closer inside them is their own (`${x:-$(echo } > f)}` runs the echo with the brace as its operand; the
  // second fix-up, 2026-09-20). Returns the inner text. The word carrying it is not literal.
  const skipNested = (open, close, dq = false) => {
    let depth = 1;
    const start = i;
    while (i < src.length && depth > 0) {
      const c = src[i];
      if (c === '\\') { i += 2; continue; }
      if (c === "'" && !dq) { const e = src.indexOf("'", i + 1); i = e < 0 ? src.length : e + 1; continue; }
      if (c === '"') {
        i++;
        while (i < src.length && src[i] !== '"') { if (src[i] === '\\') i++; i++; }
        i++;
        continue;
      }
      if (c === '$' && src[i + 1] === '(' && open !== '(') { i += 2; skipNested('(', ')'); continue; }
      if (c === '$' && src[i + 1] === '{' && open !== '{') { i += 2; skipNested('{', '}'); continue; }
      if (c === '`') { const e = src.indexOf('`', i + 1); i = e < 0 ? src.length : e + 1; continue; }
      if (c === open) depth++;
      else if (c === close) {
        // THE PAREN RULE inside a `$(..)`, a `<(..)`, a `>(..)` or zsh's `=(..)` (round 6's eighth commit): a `)` that ends a case pattern closes nothing, read
        // off the text so far by this lexer's own case tracking (lex's patternParen; one rule, one home), so `$(case x in x) echo 'cp a b';; esac)` is the
        // whole case, whose list THE OUTPUT MODEL then reads (a `case` beside a printer: UNRESOLVABLE). Asked only where the text so far spells `case`.
        if (open === '(' && nestDepth < NESTED_DEPTH_CAP && /\bcase\b/.test(src.slice(start, i)) && lex(src.slice(start, i), shell, { depth: nestDepth + 1 }).patternParen) { i++; continue; }
        depth--;
      }
      i++;
    }
    if (depth > 0) opaque = true;
    return src.slice(start, Math.max(start, i - 1));
  };
  // A `$(...)` (or `$(` inside double quotes): the command inside runs, the word carries one NUL for it.
  // THE RESOLVED SUBSTITUTION (round 5's fifth addendum, third fix-up, 2026-09-20; the second fix-up's verifiers found `bash -c
  // "$(echo 'cp ../base/report.md report.md')"`, `bash <<< "$(echo '..')"`, that line inside a here-document fed to bash and `echo
  // "$(echo '..')" | bash` from docs/ allowed while bash, zsh and dash ran the printed text as the script: the `$(...)` was read as the
  // command it runs, an echo that writes nothing, and the text it prints, which the guard could see, was never the script). THE RULE:
  // a `$(...)` or a backtick whose command is one echo or printf with literal operands and no redirection prints text the guard can
  // see (literalOutput), and that text stands in the word where the shell puts it, trailing newlines dropped as the shells drop
  // them: whole where no shell splits an expansion's result (inside double quotes, as a here-string, in a here-document body, as the
  // word of a `${...}` operator), among unquoted operands split at blanks into the words the shell makes (bash and dash; zsh splits
  // nothing and its reading, the whole text, is the default word's below), and at a redirection target both, the whole text (dash)
  // and each field (zsh; bash one field or none: THE SPLIT TARGET at endWord, round 6's third commit), each marked 'e'
  // (isGlobMark), so the word is literal: a script it forms is read as the here-string form already is (`bash -c "$(echo 'echo x >
  // report.md')"` writes in all three, measured), `$(echo cp) a b` is a copy of a onto b (all three write), `x=$(echo a.md); cp b $x`
  // resolves, and `bash -c $(echo 'cp a b')`, split, hands `cp` alone to bash (no shell writes). When echo's two readings differ (a
  // backslash in an operand: bash prints it as spelled, zsh and dash interpret it; `bash -c "$(echo 'cp a b\c')"` copied in zsh and
  // dash and not in bash, measured), a word that is the substitution alone keeps both texts as its readings and a script formed from
  // it is read under each (endWord, readingsOf); any other word that holds them stays an expansion the guard does not read (the
  // non-literal rule as a target or a writer's operand; a `-c` operand so built is the residual decision 47 names). Not resolved: a
  // substitution among unquoted operands while the command names IFS (its result splits by a rule the guard does not read: `IFS=:;
  // cp $(echo 'a:b')` copies in all three), and a here-document delimiter, which no shell expands.
  // THE ONE PLACE in lex where a reading reaches a word (THE RESOLVER'S CONTRACT, stated at the reading functions below the lexer):
  // `r` is a reading function's answer (sound texts, unresolvable, or null), `spelling` the expansion as typed, `mode` where the
  // reading goes: 'text', a `$(...)` or a backtick whose printed text stands where the shell puts it (THE RESOLVED SUBSTITUTION);
  // 'readings', a word that stands for each text (THE DEFAULT WORD, a `<(...)` or `=(...)` read as the file it stands for);
  // 'segment', the text a segment's command prints into a pipe (THE PIPED SCRIPT). Returns false when the resolver does not apply
  // (null), and the caller keeps the word an expansion as before, its command read; true when the reading was placed or the
  // word marked unresolvable. UNRESOLVABLE never writes a text: the word stays an expansion (the base's refusal as a target) and
  // carries the reason (`word.unresolvableReading`, attached at endWord), so a script consumer refuses it too (extract's scriptTexts). A
  // plain reading alone (one text produced by no interpretation) takes the text road; every other reading is the word's
  // `readings`, read on the script road while the word keeps the non-literal rule as a target.
  // THE ASSIGNMENT VALUE (round 6's fifth commit, 2026-09-21; the body auditor: `x=$(echo 'cp ../base/report.md report.md'); $x` gave x the
  // whole text in every shell and ran the copy while the lexer cut the resolved text into three words, so the candidates read `cp`
  // alone): no shell splits an expansion's result in the value of an assignment word (bash: Simple Command Expansion and Shell
  // Parameters; dash(1): Word Expansions, "field splitting is not performed on assignments"; zsh splits no expansion), the words before
  // it being assignment words alone or a declaration command (`export`, `declare`, `typeset`, `local`, `readonly`, whose operands bash
  // and zsh read as assignments; dash splits an `export` operand, and the whole text is the reading that runs the copy in bash and zsh,
  // the safe side, while a value holding a blank never resolves into a target)
  const assignmentValue = () => /^[A-Za-z_][A-Za-z0-9_]*\+?=/.test(buf) && /^u+$/.test(marks.slice(0, buf.indexOf('=') + 1)) && seg.words.every((w, k) => isAssignmentWord(w) || (plainWord(w) && RESERVED.has(w.text)) || (k === 0 && plainWord(w) && (VAR_ASSIGNERS.has(w.text) || w.text === 'local')));
  const placeReading = (r, spelling, mode, target = seg) => {
    if (r == null) return false;
    const printed = (props) => Object.assign(word('\0', false, spelling, { marks: 'x' }), props);   // `target`: the segment the producer's printed text is placed on (the producer itself, or the closer of the subshell or group holding it: THE OUTPUT MODEL, round 6's second commit)
    if (r.unresolvableReading) {
      if (mode === 'segment') { target.printed = printed({ unresolvableReading: { raw: spelling, why: r.unresolvableReading } }); return true; }
      if (!sawExpansion) opaqueExpansion(hdInner && mode === 'text' ? spelling : undefined);   // in a here-document body the spelling stays in the text, as for a substitution with no reading
      inWord = true;
      wordUnresolvable = { raw: spelling, why: r.unresolvableReading };
      return 'unresolvable';   // placed as a mark: a substitution's caller reads its commands as commands all the same (resolvedSub)
    }
    const trimmed = [...new Set(r.texts.map((t) => t.replace(/\n+$/, '')))];   // trailing newlines dropped as the shells drop them
    if (mode === 'segment') { target.printed = printed({ readings: trimmed }); return true; }
    inWord = true;
    if (mode === 'readings' || trimmed.length > 1 || !r.plain) {
      // the script road: the word is an expansion standing for each text; as a target it keeps the non-literal rule
      if (!sawExpansion) opaqueExpansion();
      wordReadings = { raw: spelling, texts: trimmed, params: r.params || null };   // params: THE DEFAULT WORD's names (round 6's fifth commit), read beside the texts in extract's scriptTexts
      return true;
    }
    // the text road: one plain text stands in the word where the shell puts it, whole where no shell splits an expansion's
    // result and split at blanks among unquoted operands (bash and dash; zsh splits nothing, and its reading, the whole text, is
    // the default word's)
    const text = trimmed[0];
    if (dqInner || hdInner || inDq || noSplitOpt || oneWord || (expect && expect.kind === 'herestring') || assignmentValue()) { quoted(text); return true; }
    if (ifsNamed) return false;   // among unquoted operands, and at a redirection target (round 6's fourth commit: `IFS=:; echo x > $(echo 'report.md:x')` opened report.md in zsh while the text was judged whole), while the command names IFS the result splits by a rule the guard does not read: not resolved, the expansion stays (a target the hook cannot read) and its command is read
    if (expect) { buf += text; marks += 'e'.repeat(text.length); return true; }   // a redirection target, or a `<`: the whole text, globbed; at a write target endWord adds each blank-separated field beside it (THE SPLIT TARGET)
    const parts = text.split(/[ \t\n]+/);   // '' at an end when the text begins or ends with a blank: the word under way ends there
    parts.forEach((part, k) => {
      if (k > 0) { endWord(); raw = spelling; }
      if (part) { inWord = true; buf += part; marks += 'e'.repeat(part.length); }
    });
    if (!buf && raw === spelling) inWord = false;   // an empty result alone makes no word, as in the shells
    return true;
  };
  const resolvedSub = (spelling, inner) => {
    if (expect && expect.kind === 'heredoc') return false;   // a here-document delimiter, which no shell expands
    // placeReading's answer: true, a sound reading stands in the word and the substitution's commands print alone (echo, printf, a
    // silent command, a cat of a here-document: nothing in it writes); 'unresolvable', the word is marked and the caller reads the
    // substitution's commands as commands all the same (round 6's second commit: `$(echo x > f; echo 1)` printed a text the model
    // cannot establish while its echo wrote f, and a mark alone lost the write from a cwd in no project); false, no reading or one lex
    // declines to place (the command names IFS), the commands read as before
    return placeReading(literalOutput(inner, shell, nestDepth), spelling, 'text');
  };
  const substitution = () => {
    raw += '$('; i += 2; const inner = skipNested('(', ')'); raw += inner + ')';
    // `$(( ... ))` is arithmetic in bash, zsh and dash when the `(` after the `$(` closes at the very end, run in the current
    // shell (an assignment in it persists): kept for the assignment scan and not read as a command (the walk-around lens second
    // pass, 2026-09-19), its substitutions read as the commands every shell runs (round 5's fifth addendum); a `$((` whose first `(`
    // closes BEFORE the end is `$( (` to bash and zsh, a command substitution whose list they run (`echo $((x > f);(y))` wrote f in
    // both, measured 2026-09-20), and an arithmetic error to dash, so it is read as a command list too and kept for the assignment
    // scan; a `$( ... )` is a command in a subshell, as before
    if (inner.startsWith('(') && parenCloseAt(inner) === inner.length - 1) { opaqueExpansion(); const body = inner.slice(1, -1); seg.arith.push(body); expansionsOf(body, CONSTRUCT_HEADS['$(('].expandVia); }
    else if (inner.startsWith('(') && inner.endsWith(')')) { opaqueExpansion(); seg.arith.push(inner.slice(1, -1)); seg.viaSubs.push({ text: inner, via: CONSTRUCT_HEADS['$(('].via }); }
    else { const r = resolvedSub('$(' + inner + ')', inner); if (r !== true) { if (!r) { opaqueExpansion(hdInner ? '$(' + inner + ')' : undefined); wordMayReadStdin = '$(' + inner + ')'; } seg.subs.push(inner); } }   // in a here-document body the spelling stays in the text (the consumer's script reads it again where the shell runs it); a list the resolver does not read may read the standard input (THE FED SUBSTITUTION)
  };
  // A `${...}` of unknown content: the spelling stays in the word, marked as an expansion, and the expansions nested in it are
  // read (nestedExpansions); `dq` says whether the word stands inside double quotes.
  const braceParameter = (dq = false) => {
    raw += '${'; i += 2; const inner = skipNested('{', '}', dq); raw += inner + '}';
    opaqueExpansion('${' + inner + '}');
    const op = inner.match(/^([A-Za-z_][A-Za-z0-9_]*|[0-9]+|[#?$!@*-])(:?[-=+?])/);   // THE DEFAULT WORD's name and operator, when the word has one (`?` since round 6's fifth commit: the word is a message and the text is the value alone); THE SPECIAL PARAMETER (round 6's sixth commit): a digit run or a special parameter before the operator is a default word too (bash: Shell Parameter Expansion; dash(1): Parameter Expansion), defaultWordReading says what it stands for
    const nested = nestedExpansions(inner, dq, !!op);   // ONE descent serves both reads: a second lex per level was exponential in the nesting (the cap test's 70 levels never returned)
    if (op && nested) {
      const placed = defaultReading(inner, op[0].length, nested, { name: op[1], op: op[2] });   // true: a sound reading placed (wordReadings holds it); 'unresolvable': the mark; false: no reading
      const r = placed === true && wordReadings && wordReadings.raw === '${' + inner + '}' ? { texts: wordReadings.texts, params: wordReadings.params } : null;
      // THE ASSIGNED DEFAULT (round 6's sixth commit, 2026-09-21; the body auditor: `: ${e:=cp}; $e a b`, `: ${e=cp}`, `true ${e:=cp}`, `echo ${e:=cp} >/dev/null`,
      // `x=${e:=cp}`, `: ${e:=c}${f:=p}; $e$f a b`, `: ${e:=cd}; $e ../notes; cp ..` and the value handed to `bash -c` or `eval` each ran the copy in
      // every shell while the assignment the operator performs was recorded nowhere): `${name:=word}` and `${name=word}` assign word to name when it is
      // unset (or empty, with the colon), so word's texts are candidates of the name (THE HEAD CANDIDATES read them where `$name` is a command name or
      // a script), and a word the resolver could not establish, or one whose text depends on another parameter, marks the name unreadable there
      if (/=$/.test(op[2]) && IDENTIFIER.test(op[1])) seg.paramAssigns.push({ name: op[1], texts: r && r.texts && !(r.params || []).some((p) => p.name !== op[1]) ? r.texts : null });
    }
  };
  // THE DEFAULT WORD (round 5's fifth addendum, third fix-up, 2026-09-20; found beside the verifiers' rows while reproducing them:
  // `bash -c "${x:-$(echo 'cp ../base/report.md report.md')}"` from docs/ allowed while bash, zsh and dash copied, the `${...}` word
  // the residual "a script held in a variable" while its word was text the guard could read). THE RULE: `${name:-word}`,
  // `${name-word}`, `${name:=word}` and `${name=word}` stand for word when the name is unset (or empty, with the colon), and
  // `${name:+word}` and `${name+word}` when it is set, so a script formed from such a word alone runs word's text in the shell that
  // reads it; when word lexes to one literal text under the word's quoting (its substitutions resolved; a blank, an operator
  // character and a `#` are characters of the word; inside double quotes a single quote is a character, so `bash -c "${x:-'cp a b'}"`
  // hands a command named `cp a b` to bash and writes nothing, while the unquoted `bash -c ${x:-'cp a b'}` copies in all three and
  // `bash -c "${x:-cp a b}"` too, measured), the text joins the word's readings (readingsOf) and is read as a script where the word is
  // one (a `-c` operand, a here-string, a here-document body fed to a shell), in every position, since zsh splits no expansion's
  // result (`bash -c ${x:-cp a b}` unquoted copies in zsh and hands `cp` alone to bash in bash and dash, measured); the `${...}` word
  // itself keeps the non-literal rule everywhere else, and a `${name}` with no operator, `${name:?word}` (the shell exits, the word
  // is a message) and every other form give no reading.
  // THE PARAMETER'S VALUE (round 6's fifth commit, 2026-09-21; the residuals verifier: `c=cp; ${c:-cat} ../base/report.md report.md` ran
  // the copy in every shell while the reading was `cat` alone, and `${c-cat}`, `${c:-}`, `${c:-''}`, `"${c:-}"`, `${c:?}`, `${c?}`,
  // `${c:=cat}`, the same through `eval`, as a piped script's consumer and as a here-string's, alike): the text a default word stands
  // for is the parameter's value when it is set (or non-empty, with the colon) and the word otherwise, so a reading of the word alone
  // is sound only when the value is known too; the reading carries the name (`params`), and extract's scriptTexts, which alone reads
  // extract's names, joins the value THE HEAD CANDIDATES and the readability rule hold for it (a plain assignment of the command) and
  // refuses the word as UNRESOLVABLE where that value is not readable: a name a construct the resolver does not follow wrote (`read c`,
  // `c=$(which cp)`), or one the command never sets, whose value is the shell's own, which the guard does not read (a `${X:-default}`
  // command name or script from a tracked cwd with X untouched is refused, a stated cost; the `+` forms depend on no value and keep
  // the word alone). A nested default word carries the inner word's names up with its own.
  const defaultReading = (inner, prefixLen, nested, param) => placeReading(defaultWordReading(nested, prefixLen, param), '${' + inner + '}', 'readings');
  // THE NESTED EXPANSION (round 5's fifth addendum, second fix-up, 2026-09-20; the fix-up's verifiers found `echo ${x:-$(cp
  // ../base/report.md report.md)}` from docs/ allowed while bash, zsh and dash copied, and the same through `${x-..}`, `${x:=..}`,
  // `${x#..}`, `${x:?..}`, `${x/b/..}`, `${x[..]}`, a backtick, a `<(...)` in bash, a `${` nested two deep, inside double quotes,
  // as an operand of `[[ ]]` and of `(( ))`, and through `dash -c`: the `${` read skipped its inner text whole, so nothing inside a
  // parameter expansion was ever lexed): an expansion nested inside a parameter-expansion word is read as the command it runs,
  // recursively, in every position (an operand, inside `[[ ]]`, inside `(( ))`, a redirection target, a quoted word), exactly
  // as an expansion among plain operands is read; the `${` read descends. The inner text is lexed with this lexer under the same
  // shell, with no comment (a `#` is a character there) and in the quoting the word stands in (inside double quotes a single
  // quote is a character and `$'` a dollar; unquoted, a single-quoted part runs nothing; a `<(` is read in both, since bash
  // performs it unquoted anywhere in the word and double-quoted in the pattern, replacement and message parts), and every
  // substitution it finds (a `$(...)`, a backtick, a `<(...)`, the substitutions of a `$((...))`) joins this segment's
  // viaSubs with a text naming the word, where the walk reads it as any `$(...)` of the command; the `${...}` word itself keeps
  // the non-literal rule (as a target or a writer's operand it is refused while a project is in play). The cost, measured with no
  // shell writing: the word's command is read whatever the parameter's state, so `x=1; echo ${x:-$(cp a b)}` and `${x:+$(cp a
  // b)}` with x unset refuse while no shell runs the copy (the shells evaluate the word only when the operator's condition holds);
  // `"${x:-<(cp a b)}"` refuses while no shell performs a process substitution there; `${x[<(cp a b)]}` refuses while every shell
  // rejects the subscript; `(( ${x:-<(cp a b; echo 1)} ))` refuses while bash and zsh report an arithmetic error and dash a syntax
  // error (the param-word matrix counts each class).
  const nestedExpansions = (inner, dq, always = false) => {
    if (!always && !/[$`]|<\(|>\(|=\(/.test(inner)) return null;   // no expansion can start without one of these (`=(`: zsh's process substitution, the third fix-up); a default word is lexed for its text all the same
    if (nestDepth >= NESTED_DEPTH_CAP) { opaque = true; return null; }
    // the inner text as one word (oneWord: its blanks and operator characters are the word's, its substitutions one text each, as
    // zsh reads the word and as every shell reads it inside double quotes), since the third fix-up, which reads THE DEFAULT WORD from
    // the same descent; the substitutions it holds are read the same in either mode
    const nested = lex(inner, shell, { comments: false, quotes: dq ? 'double' : 'plain', depth: nestDepth + 1, braceWord: true, oneWord: true, noSplit: true, ifsNamed });
    if (nested.opaque) opaque = true;
    for (const s of nested.segments) {
      for (const t of s.subs) seg.viaSubs.push({ text: t, via: BRACE_WORD_VIA });
      for (const v of s.viaSubs) seg.viaSubs.push(v);
    }
    return nested;
  };
  // A backtick command: as `$(...)`; unterminated, the rest of the command is opaque.
  const backtick = () => {
    const e = src.indexOf('`', i + 1);
    inWord = true;
    if (e < 0) { opaqueExpansion(); opaque = true; raw += src.slice(i); i = src.length; return; }
    const inner = src.slice(i + 1, e);
    raw += src.slice(i, e + 1); i = e + 1;
    { const r = resolvedSub('`' + inner + '`', inner); if (r !== true) { if (!r) { opaqueExpansion(hdInner ? '`' + inner + '`' : undefined); wordMayReadStdin = '`' + inner + '`'; } seg.subs.push(inner); } }   // resolved as a `$(...)` is (THE RESOLVED SUBSTITUTION; THE FED SUBSTITUTION)
  };

  // zsh's third process substitution, `=(cmd)` (round 5's fifth addendum, third fix-up, 2026-09-20; the second fix-up's verifiers
  // found `echo ${x:-=(cp ../base/report.md report.md)}` from docs/ allowed while zsh copied, `=(` appearing nowhere in the hook, and
  // the bare `cat =(cp ..)` refused by accident, its parenthesis read as a subshell). THE RULE: zsh performs `=(cmd)` where a word
  // begins, unquoted: an operand (`cat =(cmd)`, `: =(cmd)`), an assignment's value (`x==(cmd)`), the word of a `${...}` operator
  // (`${x:-=(cmd)}`, `${x:-${y:-=(cmd)}}`, `${(e)x:-=(cmd)}`) and a replacement part (`${x/b/=(cmd)}`), each measured writing in zsh
  // (bash and dash reject the spelling and run nothing), and nowhere else (`${x:-a=(cmd)}`, `[[ -n =(cmd) ]]`, `"${x:-=(cmd)}"` and
  // `${x:-"=(cmd)"}` run nothing, measured, so inside double quotes it is not read; the pattern part `${x#=(cmd)}` is read all the same, a priced cost); so it is read as
  // `<(cmd)` is: cmd runs and is read like a `$(...)`, and the word stands for a file the hook cannot resolve. `x=(a b)` is an array
  // assignment, not this, and keeps its reading.
  const eqProcsubStart = () => zshGrammar && inWord && !dqInner && !inDq && buf.endsWith('=') && marks.endsWith('u') && (buf.length === 1 || buf[buf.length - 2] === '=' || (braceWord && /[-=?+#%/:[]/.test(buf[buf.length - 2])));
  while (i < src.length) {
    const c = src[i];
    // the third fix-up's modes (the prologue): a here-document body is text but for `$`, a backtick and the backslash's four escapes;
    // the word of a `${...}` operator keeps its blanks and operator characters, a process substitution's opener excepted
    if (hdInner) {
      if (c === '\\') {
        const n = src[i + 1];
        if (n === '$' || n === '`' || n === '\\') { inWord = true; quoted(n); raw += src.slice(i, i + 2); i += 2; }
        else if (n === '\n') i += 2;
        else { inWord = true; quoted('\\'); raw += '\\'; i++; }
        continue;
      }
      if (c !== '$' && c !== '`') { inWord = true; quoted(c); raw += c; i++; continue; }
    } else if (oneWord && ' \t\n#;&|()<>'.includes(c) && !((c === '<' || c === '>') && src[i + 1] === '(') && !(c === '(' && eqProcsubStart())) {
      inWord = true; buf += c; marks += 'u'; raw += c; i++;
      continue;
    }
    if (c === ' ' || c === '\t') { endWord(); i++; continue; }
    if (c === '\n') {
      endWord();
      opAt = i;
      i++;
      readHeredocBodies();   // the bodies belong to the line just ended
      endSegment('\n');
      continue;
    }
    if (c === '#' && !inWord && comments) {   // comment to the end of the line (not inside a `${...}` word: nestedExpansions)
      while (i < src.length && src[i] !== '\n') i++;
      continue;
    }
    if (c === '\\') {
      if (src[i + 1] === '\n') { i += 2; continue; }   // line continuation
      inWord = true; quoted(src[i + 1] == null ? '' : src[i + 1]); raw += src.slice(i, i + 2); i += 2;
      continue;
    }
    if (c === "'" && !dqInner) {   // inside a double-quoted `${...}` word a single quote is a character (nestedExpansions)
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
      inDq = true;
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
          const e = expansionAt(src, i, zshGrammar);
          if (e.kind === 'home' && buf === '' && !sawExpansion && (src[i + e.len] === '/' || src[i + e.len] === '"')) {
            home(os.homedir()); raw += src.slice(i, i + e.len); i += e.len; continue;
          }
          if (e.kind === 'numeric') { sawExpansion = true; expanded(src.slice(i, i + e.len)); raw += src.slice(i, i + e.len); i += e.len; continue; }
          if (e.kind === 'sub') { substitution(); continue; }
          if (e.kind === 'brace') { braceParameter(true); continue; }
          if (e.kind === 'var' || e.kind === 'home') { opaqueExpansion(src.slice(i, i + e.len)); raw += src.slice(i, i + e.len); i += e.len; continue; }
          quoted('$'); raw += '$'; i++; continue;
        }
        if (d === '`') { backtick(); continue; }
        quoted(d); raw += d; i++;
      }
      inDq = false;
      if (!closed) opaque = true;
      continue;
    }
    if (c === '`') { backtick(); continue; }
    if (c === '$') {
      // a leading $HOME or ${HOME} followed by a slash or the word's end is the home directory, as `~/` is
      // (review round 1, 2026-09-18); $$ and ${$} are numeric; a parameter, a `${...}`, a `$(...)` are expansions
      // the hook does not read; `$'...'` and `$"..."` are quoting forms (the header); a bare `$` is text
      const e = expansionAt(src, i, zshGrammar);
      if (e.kind === 'home' && buf === '' && !sawExpansion && homeBoundary(src[i + e.len])) {
        inWord = true; home(os.homedir()); raw += src.slice(i, i + e.len); i += e.len; continue;
      }
      inWord = true;
      if (e.kind === 'numeric') { sawExpansion = true; expanded(src.slice(i, i + e.len)); raw += src.slice(i, i + e.len); i += e.len; continue; }
      if (e.kind === 'sub') { substitution(); continue; }
      if (e.kind === 'brace') { braceParameter(dqInner || hdInner); continue; }
      if (e.kind === 'ansi') {
        if (dqInner || hdInner) { buf += c; marks += 'u'; raw += c; i++; continue; }   // inside a double-quoted `${...}` word or a here-document body a `$'` is a dollar (nestedExpansions, readHeredocBodies)
        // $'...': the body up to an unescaped quote (`\'` does not end it)
        let j = i + 2;
        while (j < src.length && src[j] !== "'") j += src[j] === '\\' && j + 1 < src.length ? 2 : 1;
        if (j >= src.length) { opaque = true; ambiguous(); quoted(src.slice(i + 2)); raw += src.slice(i); i = src.length; break; }
        const body = ansiC(src.slice(i + 2, j));
        if (!ansiCQuoting) ambiguous();
        quoted(body); raw += src.slice(i, j + 1); i = j + 1;
        continue;
      }
      if (e.kind === 'locale') { if (!dqInner && !hdInner) { ambiguous(); raw += '$'; i++; continue; } buf += c; marks += 'u'; raw += c; i++; continue; }   // the `"` that follows is read as a double-quoted string; inside a double-quoted `${...}` word the `$` is a dollar
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
      opAt = i;
      // THE TEST'S BOUNDARIES (round 5's fifth addendum's fix-up, 2026-09-20; the addendum's verifier found both reads failing
      // toward allowing): the test's grammar ends at the unquoted `]]` word, so an operator glued to it is outside the test, the
      // redirection or list operator it is anywhere else, and the `]]` under way ends here, before the operator is read (before,
      // `[[ a ]]>report.md` truncated the file in bash, zsh and dash while the `>` was read as a word of the test; `]]>|`, `]]&&cp
      // ..` and `]]||cd ..` the same); and an expansion among the operands is performed by the shell before the test reads a word,
      // a process substitution too (`[[ -f <(echo x > report.md) ]]` wrote in bash, in every position; zsh performs it after `!`, in a
      // pipeline, with `&`, `|&` and under coproc, and rejects it alone, in `( )`, in a group, in if, in a called function, in `$(...)`
      // and via `zsh -c`; dash rejects it), so `<(` and `>(` are read as the process substitution they are anywhere,
      // before the test's own `<` and `>`, and the command inside runs. Under dash's grammar alone they are `<` or `>` and an
      // unquoted `(`, as dash reads them: the parenthesis closeTest reads as dash's syntax error.
      if (inTest && inWord && raw === ']]') endWord();
      // >(cmd) or <(cmd): a process substitution. cmd runs and is read like a $(...); the word stands
      // for a /dev/fd path the hook cannot resolve, so `tee >(cat) file` still names file.
      if (testGrammar && (c === '>' || c === '<') && src[i + 1] === '(') {
        if (!(inWord && buf)) endWord();   // glued to a word under way, the substitution is part of that word, as bash reads it (`ENV=<(cmd)` is the one word `ENV=/dev/fd/63`; round 6's fourth commit: the cut before `<(` made the startup file's word the command name)
        i += 2;
        const inner = skipNested('(', ')');
        seg.subs.push(inner);
        inWord = true;
        const t = c + '(' + inner + ')';
        opaqueExpansion(t); raw += t;
        if (c === '<' && !placeReading(literalOutput(inner, shell, nestDepth), t, 'readings')) wordMayReadStdin = t;   // the file the word stands for holds the text a literal echo or printf prints (extract's `bash <(echo '..')`, `bash < <(echo '..')`; THE RESOLVER'S CONTRACT); a list the resolver does not read may read the standard input (THE FED SUBSTITUTION)
        endWord();
        continue;
      }
      // inside [[ ... ]] a > or < is a string comparison, not a redirection, and &&, ||, ( and ) are the
      // test's own operators: each a word of its own, the segment going on (bash and zsh; dash's reading is added at closeTest,
      // and dash's `>|` is kept in the test's span so that reading sees it where a `|` would have ended the segment: bash and
      // zsh reject the line, dash writes through it, round 5's fifth addendum)
      if (inTest && c === '>' && src[i + 1] === '|') { bareWord('>|'); i += 2; continue; }
      if (inTest && (c === '<' || c === '>')) { bareWord(c); i++; continue; }
      if (inTest && ((c === '&' && src[i + 1] === '&') || (c === '|' && src[i + 1] === '|'))) { bareWord(c + c); i += 2; continue; }
      if (inTest && (c === '(' || c === ')')) { bareWord(c); i++; continue; }
      // zsh's `=(cmd)` (eqProcsubStart above): read after the test's own parenthesis, since zsh performs none inside `[[ ]]`
      if (zshGrammar && c === '(' && eqProcsubStart()) {
        buf = buf.slice(0, -1); marks = marks.slice(0, -1); raw = raw.slice(0, -1);
        i++;
        const inner = skipNested('(', ')');
        seg.subs.push(inner);
        const t = '=(' + inner + ')';
        opaqueExpansion(t); raw += t;
        placeReading(literalOutput(inner, shell, nestDepth), t, 'readings');   // as `<(cmd)`: the file holds what a literal echo or printf prints (`zsh =(echo '..')`)
        endWord();
        continue;
      }
      // a digits-only word glued to < or > is the descriptor (2>file still writes file): drop it
      fdDigits = null;
      if (inWord && /^[0-9]+$/.test(buf) && (c === '<' || c === '>')) { fdDigits = buf; buf = ''; raw = ''; marks = ''; inWord = false; }
      else endWord();
      if (testGrammar && c === '(' && src[i + 1] === '(') { i += 2; skipArithmetic(); continue; }   // (( ... )) compares or counts in bash and zsh; under dash's grammar alone it is two `(`, read below
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
        if (src[i] === '>' && !(testGrammar && zshGrammar && src[i + 1] === '(')) { op = '>>'; i++; }   // THE WRITTEN PROCESS SUBSTITUTION (round 6's ninth commit): zsh reads `>>(cmd)` as `>` and the process substitution `>(cmd)` (`echo x >>(bash)` ran the text in zsh, measured; bash and dash reject the spelling and run nothing), so under zsh's grammar the second `>` opens the substitution
        if (src[i] === '&') {
          i++;
          // a dup (2>&1, >&-) is no write; `>& word` writes word, and zsh's `>>& word` appends both streams to it. The dup is
          // read only when the word after `>&` is exactly a digit run or exactly `-` and a word delimiter follows (round 5,
          // 2026-09-20: any word opening with a digit or `-` was skipped as a dup, so `printf x >&2-3` in a tracked folder was
          // invisible while bash and zsh wrote the file `2-3`, and zsh writes `2-`, `-2` and `1-` too); `>>&` is zsh's alone and
          // has no dup form there (`>>&2` appends to a file named `2`, measured), so it is never a dup.
          const dup = op === '>' ? (src.slice(i).match(/^(?:[0-9]+|-)(?=$|[\s;&|()<>])/) || [null])[0] : null;
          if (dup) { if (dup !== '-') seg.outDups.push({ from: fdDigits == null ? '1' : fdDigits, to: dup }); i += dup.length; continue; }   // `[n]>&m`: descriptor n (the standard output when no n) is duplicated onto m, recorded for THE WRITTEN PROCESS SUBSTITUTION (`echo '..' 3> >(bash) >&3` routes the text through 3)
          op += '&';
        }
        expect = clobberSuffix(op);
        expect.fd = fdDigits;   // the descriptor the write opens (`3> f`), read by THE WRITTEN PROCESS SUBSTITUTION; null is the standard output
        continue;
      }
      if (c === '<') {
        if (src[i + 1] === '<' && src[i + 2] === '<') { i += 3; expect = { kind: 'herestring' }; continue; }
        if (src[i + 1] === '<') { const strip = src[i + 2] === '-'; i += strip ? 3 : 2; expect = { kind: 'heredoc', stripTabs: strip }; continue; }
        if (src[i + 1] === '>') { i += 2; expect = { kind: 'target', op: '<>', fd: fdDigits == null ? '0' : fdDigits }; continue; }   // `[n]<>word`: descriptor n, the standard input when no n (bash: Opening File Descriptors for Reading and Writing)
        if (src[i + 1] === '&') { i += 2; expect = { kind: 'dup', fd: fdDigits }; continue; }   // `[n]<&word`: the descriptor word names is duplicated onto n (the standard input when no n), recorded at endWord (THE DUPLICATED DESCRIPTOR, round 6's fifth commit; before, the digits were skipped and the consumer read nothing through them)
        i++; expect = { kind: 'data', fd: fdDigits }; continue;   // the standard input, or the descriptor numbered before the `<` (the third fix-up: `bash 3</dev/null` still reads the pipe)
      }
      if (c === '&') {
        if (src[i + 1] === '>') { const app = src[i + 2] === '>'; i += app ? 3 : 2; expect = clobberSuffix(app ? '&>>' : '&>'); expect.fd = null; continue; }   // both streams: the standard output among them (THE WRITTEN PROCESS SUBSTITUTION reads it as fd 1)
        if (src[i + 1] === '&') { i += 2; endSegment('&&'); continue; }
        i++; endSegment('&'); continue;
      }
      if (c === '|') { const or = src[i + 1] === '|'; i += or ? 2 : 1; endSegment(or ? '||' : '|'); continue; }
      if (c === ';') { i += src[i + 1] === ';' ? 2 : 1; endSegment(';'); continue; }
      // ( or ): a segment break and a scope marker
      i++; endSegment(c);
      const marker = { ...newSegment(), paren: c, start: i - 1 };
      // THE PAREN RULE (round 6's eighth commit): a `(` opens a subshell scope; a `)` closes the innermost subshell, unless a case body is open inside it,
      // where it ends a pattern (`pattern`: the marker pairs with no `(`, so the scans over the markers and the walk's frames read the case whole)
      if (c === '(') lexScopes.push('subshell');
      else { const j = parenCloses(lexScopes); if (j >= 0) lexScopes.length = j; else if (lexScopes.includes('case')) marker.pattern = true; }
      segments.push(marker);
      continue;
    }
    inWord = true; buf += c; marks += 'u'; raw += c; i++;
  }
  opAt = src.length;
  endSegment('');
  readHeredocBodies();
  if (pendingHeredocs.length) opaque = true;
  return { segments: splitAtClosers(segments), opaque, patternParen: lexScopes.includes('case') && parenCloses(lexScopes) < 0 };   // patternParen: a `)` after this text would end a case pattern (THE PAREN RULE; skipNested asks it of the text so far)
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
    if (!isGlobMark(marks[i])) { re += escapeRe(c); continue; }
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
  const wrapperIdx = [];   // the index in `words` of each wrapper peeled, in the same order (THE PEELED NAME, round 6's ninth commit: the walk consults the alias, hash and bound-path roads for each)
  let wrapped = false;   // the walk-around lens second pass (family 6): a wrapper prefix was peeled before the command
  for (;;) {
    while (k < words.length && plainWord(words[k]) && RESERVED.has(words[k].text)) k++;   // unquoted: `"{" cd ../scratch` runs a command named `{`, and the cd is its operand (round 5's fourth addendum)
    const first = k;
    while (k < words.length && (/^[A-Za-z_][A-Za-z0-9_]*\+?=/.test(words[k].raw) || (wrappers[wrappers.length - 1] === 'env' && words[k].literal && words[k].text.includes('=')))) k++;   // after env an operand holding a `=`, however quoted and whatever its name, is env's (round 6's fourth commit: `env 'X=a b' cp a b` copied in every shell while the quoted word was read as the command name and the cp as its operand; the fifth: env(1) sets any NAME=VALUE operand, so `env 'BASH_FUNC_c%%=() { cp "$@"; }' bash -c '..'`, whose name is no identifier, was read as a command named so)
    // The readability rule (the sixth pass's attacker, C5c, 2026-09-19): after a wrapper an assignment-shaped word is the
    // wrapper's ARGUMENT, not an assignment (bash looks `command x=b` up as a command; env sets it for a command that is not
    // there; `time x=b` assigns in bash alone), so the segment is not assignment-only: the words come back as the arguments
    // of a command with no name, and recordSegment (taintWord) reads each as a write it does not follow. Before, null came back and
    // the caller read the segment as plain assignments, so `x=../docs/report.md; command x=other.md; cp base/report.md
    // scratch/$x` resolved $x to other.md while every shell kept the tracked path.
    if (k >= words.length) return wrapped ? { name: '', args: words.slice(first), chdirs, writes, wrapped, wrappers, wrapperIdx } : null;
    const name = path.basename(words[k].text);
    if (!PREFIXES.has(name)) return { name, args: words.slice(k + 1), chdirs, writes, wrapped, wrappers, wrapperIdx };
    wrapped = true;
    wrappers.push(name);
    wrapperIdx.push(k);
    k++;
    const spec = WRAPPER_OPT[name];
    let lead = spec.lead || 0;
    const unknown = (option, value = null) => ({ unknown: { option, wrapper: name, value, rest: words.slice(k + 1), at: k } });   // `at`: the word the walk stopped at (THE WRAPPED PRINTER, round 6's eighth commit: printerOf splices an expansion standing there)
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

// THE SED SCRIPT (round 6's third commit, 2026-09-21): the files a literal sed script writes through `w FILE`, `W FILE` and the `w FILE`
// flag of `s`, read over GNU sed's command grammar (sed(1), "sed scripts"): addresses (a number, `first~step`, `$`, `/re/` or `\cREc`
// with `I` and `M`, a second address after `,` with `+N` and `~N`, `!`), the commands with no operand, `q`/`Q`/`l`/`L` with a number,
// a label to the line's or the `;`'s end (`:`, `b`, `t`, `T`), `a`/`i`/`c` text to the end of the line (the `\` form with continuation
// lines), `r`/`R`/`w`/`W`/`e` operands to the end of the line, `s` and `y` with their delimiter (a backslash quotes the next
// character), `s` flags then `w`, `v`, `#` comments, `{` and `}`. The filename runs to the end of the line, leading blanks dropped, as
// GNU reads it (`w report.md}` names `report.md}`, and GNU sed then rejects the unmatched `{`). A command letter the grammar does not
// have stops the read: sed itself rejects the script, but a reader that misread an address would stop the same way, so the script is
// returned unread and the caller refuses naming the letter (the safe side). Returns { files, unread } with `unread` null or the letter.
function sedWriteFiles(s) {
  const files = [];
  const n = s.length;
  let i = 0;
  const skipWs = () => { while (i < n && (s[i] === ' ' || s[i] === '\t')) i++; };
  const toEol = () => { const j = s.indexOf('\n', i); const out = s.slice(i, j < 0 ? n : j); i = j < 0 ? n : j; return out; };
  const toSep = () => { while (i < n && s[i] !== '\n' && s[i] !== ';') i++; };
  const delimited = (d) => { while (i < n) { const c = s[i++]; if (c === '\\') { i++; continue; } if (c === d) return; } };
  const number = () => { while (i < n && /[0-9]/.test(s[i])) i++; };
  const address = () => {
    if (/[0-9]/.test(s[i])) { number(); if (s[i] === '~') { i++; number(); } return true; }
    if (s[i] === '$') { i++; return true; }
    if (s[i] === '/' || s[i] === '\\') { const d = s[i] === '/' ? '/' : s[i + 1]; i += s[i] === '/' ? 1 : 2; delimited(d); while (s[i] === 'I' || s[i] === 'M') i++; return true; }
    return false;
  };
  while (i < n) {
    if (s[i] === ' ' || s[i] === '\t' || s[i] === '\n' || s[i] === ';') { i++; continue; }
    if (s[i] === '#') { toEol(); continue; }
    if (address()) { skipWs(); if (s[i] === ',') { i++; skipWs(); if (s[i] === '+' || s[i] === '~') { i++; number(); } else address(); } skipWs(); while (s[i] === '!') { i++; skipWs(); } }
    skipWs();
    if (i >= n) break;
    const c = s[i++];
    if ('{}=dDgGhHnNpPxzF'.includes(c)) continue;
    if ('qQlL'.includes(c)) { skipWs(); number(); continue; }
    if (':btT'.includes(c)) { toSep(); continue; }
    if ('aic'.includes(c)) {
      skipWs();
      if (s[i] === '\\') { i++; if (s[i] === '\n') i++; }
      for (;;) { const line = toEol(); if (!line.endsWith('\\') || i >= n) break; i++; }
      continue;
    }
    if ('rRe'.includes(c)) { toEol(); continue; }
    if (c === 'w' || c === 'W') { skipWs(); files.push(toEol()); continue; }
    if (c === 'v') { toSep(); continue; }
    if (c === 's') { const d = s[i++]; delimited(d); delimited(d); while (i < n && /[gpiImMe0-9]/.test(s[i])) i++; if (s[i] === 'w') { i++; skipWs(); files.push(toEol()); } continue; }
    if (c === 'y') { const d = s[i++]; delimited(d); delimited(d); continue; }
    return { files, unread: c };
  }
  return { files, unread: null };
}
// sed's script words (`-e`, `--expression=`, or the first operand when neither `-e` nor `-f` gave one) and the files a literal one writes
// (sedWriteFiles), as { targets, unread }: `targets` the file words to judge, `unread` the first script word the reader could not parse
// to its end with the letter it stopped at, or null. A script word that is an expansion is not read (a script held in a variable: the
// residual the property names); a `-f FILE` script is outside the command.
function sedScriptWrites(args, bodiesOf = null) {
  const scripts = [];
  let scriptGiven = false;
  let first = null;
  // `-f FILE`: the script is in a file outside the command (the residual), unless FILE names the standard input or a descriptor this command
  // feeds, or is a `<(..)` the resolver reads (THE SED FILE, round 6's fourth commit; the body auditor: `sed -n -f /dev/stdin ../base/report.md
  // <<< 'w report.md'`, `-f <(echo 'w report.md')`, `-f /dev/fd/3 .. 3<<< '..'`, `--file=<(..)` and the here-document form each wrote report.md
  // while the `-f` script went unread); `bodiesOf` (extract) gives the script words such a FILE stands for, the lexer's `--file=` and its
  // glued `<(..)` two words
  const fileScripts = (f, drop = 0) => { if (bodiesOf && f) scripts.push(...bodiesOf(f, drop)); };   // `drop`: the option text glued before the file (`--file=`, `-f`), so the word's readings are read past it
  for (let k = 0; k < args.length; k++) {
    const a = args[k];
    if (a.text === '--') { if (first == null && args[k + 1]) first = args[k + 1]; break; }
    if (a.text === '-e' || a.text === '--expression') { scriptGiven = true; if (args[k + 1]) scripts.push(args[k + 1]); k++; continue; }
    if (a.text === '-f' || a.text === '--file') { scriptGiven = true; fileScripts(args[k + 1]); k++; continue; }
    if (a.text === '-l' || a.text === '--line-length') { k++; continue; }
    if (a.text.startsWith('--expression=')) { scriptGiven = true; scripts.push(sliceWord(a, 13)); continue; }
    if (a.text.startsWith('--file=')) { scriptGiven = true; if (a.text === '--file=' && args[k + 1] && procsubOf(args[k + 1]) != null) { fileScripts(args[k + 1]); k++; } else fileScripts(a, 7); continue; }
    if (a.text.startsWith('--')) continue;
    if (a.text.startsWith('-') && a.text.length > 1) {
      const m = a.text.slice(1).match(/^([nrEszu]*)([ief])(.*)$/);   // the cluster sedTargets reads: e and f take the rest of the word or the next word
      if (m && m[2] === 'e') { scriptGiven = true; if (m[3] === '') { if (args[k + 1]) scripts.push(args[k + 1]); k++; } else scripts.push(sliceWord(a, 2 + m[1].length)); }
      else if (m && m[2] === 'f') { scriptGiven = true; if (m[3] === '') { fileScripts(args[k + 1]); k++; } else fileScripts(a, 2 + m[1].length); }
      continue;
    }
    if (first == null) first = a;
  }
  if (!scriptGiven && first) scripts.push(first);
  const targets = [];
  let unread = null;
  for (const w of scripts) {
    if (!w.literal) continue;
    const r = sedWriteFiles(w.text);
    for (const f of r.files) if (f) targets.push(word(f, true, w.raw));
    if (r.unread != null && !unread) unread = { word: w, why: `its sed script ${w.raw} reaches the command \`${r.unread}\`, which I do not read, before its end` };
  }
  return { targets, unread };
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
// given (bash <<EOF, bash -s <<EOF, bash - <<EOF, a pipe) or the script operand names the standard
// input (STDIN_NAMES, the third fix-up), and { file } for a script file, whose
// contents are not in the command. Each `o` in an option cluster takes the next word (`-euo
// pipefail`, `-ox errexit`), and under bash each `O` too (`-O extglob`, `-iO extglob`, `-Oc extglob
// '...'`): zsh takes no word after -O and dash rejects it (round 3: `bash -O extglob -c '<script>'`
// read extglob as the operand, the script was never scanned, and a literal tracked target in it
// passed).
function shellScript(args, shell) {
  let c = false;
  let s = false;
  let operand;
  const rc = [];   // bash's `--rcfile FILE` and `--init-file FILE`: a startup file the shell reads when interactive (round 6's third commit: `bash --rcfile <(echo 'cp a b') -i` copied in bash and zsh while the word was skipped as an option's value); read whether or not `-i` is spelled, the safe side
  const done = (r) => (rc.length ? { ...r, rc } : r);
  for (let k = 0; k < args.length; k++) {
    if (!args[k].literal && procsubOf(args[k]) == null) {
      // THE SHELL'S OPTION WORD (round 6's sixth commit): a word the shell fills in where an option or the operand stands, with words after it that
      // may be the script, is neither: the caller reads the texts it stands for or refuses; as the LAST word it is the operand (the script text after
      // `-c`, else a script file), since an option there would leave the shell no operand (`bash -c "$x"` keeps the residual the property names)
      if (k < args.length - 1) return done({ optionWord: args[k], at: k });
      operand = args[k];
      break;
    }
    const t = args[k].text;
    if (t === '--' || t === '-') { operand = args[k + 1]; break; }
    if (t === '--rcfile' || t === '--init-file') { if (args[k + 1]) rc.push(args[k + 1]); k++; continue; }
    if (t === '-o' || t === '+o' || (shell === 'bash' && (t === '-O' || t === '+O'))) { k++; continue; }
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
  if (c) return done({ script: operand || null });
  if (s || !operand || (operand.literal && isStdinName(operand.text))) return done({ stdin: true, fd: operand && operand.literal ? fdOfName(operand.text) : null });   // a script operand naming the standard input, or a descriptor fed by this command, reads it (the third fix-up: `bash /dev/stdin`, `sh /dev/fd/0` ran the piped script in bash, zsh and dash; round 6's third commit: `bash /dev/fd/3 3<<'EOF'`); `fd`: the numbered descriptor it names, so a `<` on that descriptor is read too (THE DESCRIPTOR FEED, round 6's fourth commit: `bash /dev/fd/3 3< <(echo '..')`)
  return done({ file: operand });   // a script file, whose contents are not in the command, unless it is a process substitution printing text the guard can read (extract, `bash <(echo '..')`)
}

// THE RESOLVER'S CONTRACT (round 6 of the review of fork PR #780, 2026-09-20; round 5 found four readings that turned a refusal
// of the base into an allow: a printf whose width or precision the reading ignored, a glob character that switched the readings
// off, an octal escape one reader lacked, and a double-quoted `"$@"` the split rule exempted; each a reading the machinery
// believed and trusted). A reading function (echoOutput, printfOutput, segmentOutput, literalOutput, defaultWordReading below)
// answers ONE of three things and nothing else: `sound(texts)`, the set of texts a shell could print or a word could stand for,
// every text a shell could produce among them, so no other reading is needed; `unresolvable(why)`, the resolver looked and cannot
// establish the text (a conversion or an option it does not model, a glob character or a brace list the shell would expand, a
// quoting whose reading depends on the shell, an escape producing a byte it does not decode, a text no path can hold); or
// `null`, the resolver does not apply (the command is no echo or printf, the word carries an expansion the resolver never reads),
// so the word keeps the rule it had before the resolver existed. A reading reaches the command in ONE place per layer, and
// nowhere else: in lex, `placeReading`, which puts a reading into the word under way; in extract, `scriptTexts`, through which
// every script-consuming site (a `-c` operand, an interpreter's inline code, a here-string, an unquoted here-document body, a
// piped producer, a process substitution read as a file, a command whose name is an expansion) obtains the texts it reads.
// THE TWO ROADS. The text road (placeReading, one text): a reading becomes the word's literal characters, judged as a target, a
// writer's operand or a value, ONLY when it is plain: one text produced by no escape interpretation and no conversion (an echo
// whose operands hold no backslash and take the same options in every shell; a printf whose format holds neither `%` nor a
// backslash), so nothing a reader could get wrong ever reaches a target judgement; every other reading leaves the word an
// expansion (non-literal: the base's refusal as a target while a project is in play) and travels the script road alone. The
// script road (word.readings, scriptTexts): the union of readings, each read as a script; a reading the union lacks can at worst
// leave the script as unread as the base left it (the base read no script held in an expansion: the residual decision 47
// names), never refuse less than the base; the readers are pinned by execution against bash, zsh and dash over the escape and
// printf grammars. UNRESOLVABLE refuses in both places: placeReading marks the word (`word.unresolvableReading`), never writes a text, and
// scriptTexts records the word as a target the hook cannot read (cannotRead, the non-literal refusal) and returns no text, so no
// consumer can turn it into the residual pass. tools/romp-track-bash-guard.test.mjs derives the reading functions from this
// source (a body that calls `sound(` or `unresolvable(`) and reds when one is called outside a reading function or the two
// places, or when a word's readings are read outside them.
const sound = (texts) => ({ texts: [...new Set(texts)] });
const unresolvable = (why) => ({ unresolvableReading: why });
// A plain reading (the text road): the texts came from no interpretation, so a single text may stand in the word.
const plain = (texts) => ({ texts: [...new Set(texts)], plain: true });

// THE ESCAPE READERS, derived from the manuals (bash: echo and printf in Shell Builtin Commands; dash(1): echo and printf;
// zshbuiltins(1): echo and printf) and pinned by execution in the three shells (the test runs every form through every reader):
// what each shell makes of a backslash in an echo operand (bash with `-e` or xpg_echo; its default prints the text as spelled),
// in a printf format and in a `%b` operand. Common to every reader: \a \b \f \n \r \t \v \; an escape a reader does not know keeps
// its backslash. `octal`: 'zero' reads `\0` and up to three octal digits after it (bash's and zsh's echo, zsh's %b); 'bare' reads
// one to three octal digits (every printf format, the `\0` of `\0101` being a digit: backspace then 1); 'both' reads the zero form
// when the first digit is 0 and the bare form otherwise (dash's echo, bash's and dash's %b). `hex`: `\x` and one or two hex digits
// (bash), zero to two (zsh, where `\x` alone is a NUL), none (dash). `unicode`: what each shell reads, `\u` with one to four hex
// digits and `\U` with one to eight (bash, zsh), `\u` with exactly four and no `\U` (dash); EVERY `\u` and `\U` is DECLINED
// (Undecodable) by every reader whatever follows it (since round 6's seventh commit the bare form too: zsh prints a NUL for `\u` with
// no digit, which a substitution drops; bash and dash keep the backslash), since the character printed depends on the shell's locale
// and the bare form on the shell; the field records the shells' grammar and decides nothing. `E`: bash alone reads `\E` as escape. `quotes`: bash's
// printf format alone reads `\"`, `\'` and `\?` as the character (measured; every other reader keeps the backslash). `c`: `\c` ends the
// output ('stop': every echo, every %b, zsh's format) or is text ('literal': bash's and dash's printf format).
// A reader missing an escape a shell interprets yields a text the union lacks, a script the guard reads under the wrong text: the
// WRITE side of the census, bounded by the execution pin.
export const ESCAPE_READERS = {
  'echo bash': { octal: 'zero', hex: 'bash', unicode: 'full', E: true, c: 'stop' },
  'echo zsh': { octal: 'zero', hex: 'zsh', unicode: 'full', E: false, c: 'stop' },
  'echo dash': { octal: 'both', hex: null, unicode: 'four', E: false, c: 'stop' },
  'format bash': { octal: 'bare', hex: 'bash', unicode: 'full', E: true, c: 'literal', quotes: true },
  'format zsh': { octal: 'bare', hex: 'zsh', unicode: 'full', E: false, c: 'stop' },
  'format dash': { octal: 'bare', hex: null, unicode: 'four', E: false, c: 'literal' },
  '%b bash': { octal: 'both', hex: 'bash', unicode: 'full', E: true, c: 'stop' },
  '%b zsh': { octal: 'zero', hex: 'zsh', unicode: 'full', E: false, c: 'stop' },
  '%b dash': { octal: 'both', hex: null, unicode: 'four', E: false, c: 'stop' },
};
// A thrown marker: the reader met a byte it does not decode (an octal or hex escape at or above 0x80: the shell writes one raw byte
// where this text holds characters; a `\u` or `\U` escape, whose output depends on the shell's locale) or a NUL (a text no path
// can hold, and which the shells drop from a substitution's result).
class Undecodable extends Error {}
// `text` read by `reader` (a key of ESCAPE_READERS): { text, stopped } where `stopped` says a `\c` ended the output.
export function shellEscapes(text, reader) {
  const r = ESCAPE_READERS[reader];
  if (!r) throw new Error(`no escape reader named ${reader}`);
  const simple = { a: '\x07', b: '\b', e: '\x1b', f: '\f', n: '\n', r: '\r', t: '\t', v: '\v', '\\': '\\' };
  const byte = (n) => { if (n === 0 || n >= 0x80) throw new Undecodable(); return String.fromCharCode(n); };
  let out = '';
  for (let k = 0; k < text.length; k++) {
    if (text[k] !== '\\' || k + 1 >= text.length) { out += text[k]; continue; }
    const n = text[k + 1];
    const rest = text.slice(k + 1);
    let m;
    if (Object.hasOwn(simple, n)) { out += simple[n]; k++; continue; }
    if (n === 'E' && r.E) { out += '\x1b'; k++; continue; }
    if (r.quotes && (n === '"' || n === "'" || n === '?')) { out += n; k++; continue; }
    if (n === 'c') { if (r.c === 'stop') return { text: out, stopped: true }; out += '\\'; continue; }
    if (r.octal === 'zero' || (r.octal === 'both' && n === '0')) {
      if ((m = rest.match(/^0[0-7]{0,3}/))) { out += byte(parseInt(m[0], 8)); k += m[0].length; continue; }
    }
    if (r.octal === 'bare' || r.octal === 'both') {
      if ((m = rest.match(/^[0-7]{1,3}/))) { out += byte(parseInt(m[0], 8)); k += m[0].length; continue; }
    }
    if (r.hex === 'bash' && (m = rest.match(/^x[0-9A-Fa-f]{1,2}/))) { out += byte(parseInt(m[0].slice(1), 16)); k += m[0].length; continue; }
    if (r.hex === 'zsh' && (m = rest.match(/^x[0-9A-Fa-f]{0,2}/))) { out += byte(m[0].length > 1 ? parseInt(m[0].slice(1), 16) : 0); k += m[0].length; continue; }
    if (n === 'u' || n === 'U') {
      // every `\u` and `\U`, however many hex digits follow (none included): the output depends on the shell's locale (bash and dash
      // print `A` for `\u0041` in a UTF-8 locale and the escape as spelled in the C locale, measured), and the bare form is a NUL in
      // zsh (`printf 'report.md\u'` prints `report.md` and a NUL byte, measured 2026-09-21; a substitution drops the NUL, so the text
      // before it stood alone and `bash -c "$(printf 'cp a b\u')"` ran `cp a b` in zsh while the reading kept the two characters:
      // round 6's seventh commit, the attack verifier), a text the guard does not establish: declined, whatever follows
      throw new Undecodable();
    }
    out += '\\';   // an escape this reader does not know keeps its backslash; the character after it is read on its own
  }
  return { text: out, stopped: false };
}
// The option words each shell's echo takes off the front (the manuals, pinned by execution): bash and zsh take `-n`, `-e`, `-E`
// and their clusters; zsh alone then drops a `-` that ends the options; dash takes one `-n` and nothing else (it prints `-e`).
const ECHO_SHELLS = ['bash', 'zsh', 'dash'];
function echoOperands(words, shell) {
  let k = 0;
  if (shell === 'dash') { if (words.length && words[0].text === '-n') k = 1; }
  else {
    while (k < words.length && /^-[neE]+$/.test(words[k].text)) k++;
    if (shell === 'zsh' && k < words.length && words[k].text === '-') k++;
  }
  return words.slice(k).map((w) => w.text);
}
// What an echo prints: the union over the shells of the operands joined by one space, bash's default (the text as spelled) and
// each shell's escape reading (bash's `-e` and xpg_echo, zsh's and dash's defaults), so every text one of the three prints is in
// it. Plain (the text road) only when no operand holds a backslash and every shell takes the same option words.
function echoOutput(words) {
  const spelled = ECHO_SHELLS.map((sh) => echoOperands(words, sh).join(' '));
  const backslash = spelled.some((t) => t.includes('\\'));
  if (!backslash) return spelled.every((t) => t === spelled[0]) ? plain([spelled[0]]) : sound(spelled);
  const texts = [spelled[0]];   // bash's default reading
  try { ECHO_SHELLS.forEach((sh, k) => texts.push(shellEscapes(spelled[k], `echo ${sh}`).text)); }
  catch (e) { if (e instanceof Undecodable) return unresolvable('an operand of the echo holds an escape for a byte or a NUL I do not decode'); throw e; }
  return sound(texts);
}
// THE PRINTF GRAMMAR (bash: printf in Shell Builtin Commands; dash(1) and zshbuiltins(1): printf; pinned by execution):
// `printf [-v name] format [argument ...]` in bash and zsh, `printf format [argument ...]` in dash, `--` ending the options; a first
// word beginning with `-` that is not `--` or `-` alone is an option to bash and dash (rejected, nothing printed) and a format to
// zsh, and no format prints nothing in every shell while the shells differ on what they report: each is UNRESOLVABLE (round 5's
// correctness-3: an empty reading crashed the walk); `-v` prints nothing in every shell too (bash and zsh assign the text, dash rejects
// the option), measured, so it reads as the empty text, plain (a `printf -v t '..' | bash` feeds bash nothing, the second fix-up's
// row, and a `$(printf -v x a)report.md` is the name report.md, judged by name). The format's escapes are read by the shell's format reader; a `%` opens a
// conversion `%[flags][width][.precision]letter` with flags among `-+ #0`, a width of digits or `*` (the next operand), a precision
// of digits, `*` or nothing after the dot (zero), and the letter. Modelled: `%%` with nothing between (a percent); `%s` and `%b` with
// the `-` flag alone, a width, a precision and `*` from an operand that is a run of digits (the shells agree on these, measured:
// `%.3s`, `%5s`, `%-5s`, `%5.2s`, `%.s`, `%*s`, `%.*s`); a missing operand is the empty string; `%b` reads its operand by the shell's
// `%b` reader and a `\c` there ends the whole output; the format is reused while operands remain and printed once when none is
// consumed. UNRESOLVABLE: every other letter (`%c` prints one character in bash and zsh and a byte in dash; `%q` is bash's and
// zsh's quoting and dash's error; `%d` and the numeric conversions read their operand by rules the shells do not share, an invalid
// one printing 0 with an error in bash and dash and silently in zsh; `%(fmt)T` is the clock), a flag other than `-` (the shells
// ignore `+`, ` `, `#` and `0` on `%s`, measured, but the rule is stated for what is modelled), a `*` from an operand that is not
// digits (a negative width left-justifies), a width or precision on an operand holding a character outside ASCII (bash and dash
// count bytes, zsh characters: `%.2s` of an accented word differs), a `%` with nothing after it or an unknown letter (an error, the
// output cut short), and an escape for a byte or a NUL. Every conversion leaves the reading on the script road (not plain).
const PRINTF_SHELLS = ['bash', 'zsh', 'dash'];
const CONVERSION = /^%([-+ #0]*)(\*|\d+)?(?:\.(\*|\d*))?([\s\S]?)/;
function printfFor(shell, fmt, operands) {
  const reader = `format ${shell}`;
  const bReader = `%b ${shell}`;
  let out = '';
  let n = 0;
  let plainText = true;
  for (let pass = 0; pass < 1 || n < operands.length; pass++) {
    let consumed = false;
    for (let k = 0; k < fmt.length;) {
      if (fmt[k] === '\\' && fmt[k + 1] === '%') { out += '\\'; k++; plainText = false; continue; }   // the backslash is text and the `%` a conversion, as the shells read it (measured: `\%Z` is an invalid directive)
      if (fmt[k] !== '%') {
        const j = fmt.indexOf('%', k);
        const piece = j < 0 ? fmt.slice(k) : fmt.slice(k, j);
        if (piece.includes('\\')) plainText = false;
        const r = shellEscapes(piece, reader);
        out += r.text;
        if (r.stopped) return { text: out, plain: false };
        k = j < 0 ? fmt.length : j;
        continue;
      }
      const m = fmt.slice(k).match(CONVERSION);
      const [whole, flags, width, precision, letter] = m;
      plainText = false;
      if (letter === '%') { if (flags || width || precision != null) return unresolvable(`a \`${whole}\` I do not model (a percent with a flag, width or precision is an error in every shell)`); out += '%'; k += whole.length; continue; }
      if (letter !== 's' && letter !== 'b') return unresolvable(letter ? `a \`${whole}\` conversion I do not model (I read \`%s\` and \`%b\` with the \`-\` flag, a width and a precision, and \`%%\`)` : 'a `%` with no conversion letter, an error in every shell');
      if (flags && flags !== '-') return unresolvable(`the \`${flags}\` flag on \`${whole}\`, which I do not model (I read the \`-\` flag alone)`);
      const take = (spec) => {
        if (spec === '*') { const v = n < operands.length ? operands[n] : ''; n++; if (!/^\d+$/.test(v)) throw unresolvable(`a \`*\` width or precision taken from \`${v}\`, not a run of digits (a negative one justifies left)`); return Number(v); }
        return spec == null ? null : (spec === '' ? 0 : Number(spec));
      };
      let w;
      let p;
      try { w = take(width); p = take(precision); } catch (e) { if (e && e.unresolvableReading) return e; throw e; }
      let arg = n < operands.length ? operands[n] : '';
      n++;
      consumed = true;
      let stopped = false;
      if (letter === 'b') { const r = shellEscapes(arg, bReader); arg = r.text; stopped = r.stopped; }
      if ((w != null || p != null) && /[^\x00-\x7f]/.test(arg)) return unresolvable('a width or precision on an operand holding a character outside ASCII (bash and dash count bytes, zsh characters)');
      if (p != null) arg = arg.slice(0, p);
      if (w != null && arg.length < w) arg = flags === '-' ? arg + ' '.repeat(w - arg.length) : ' '.repeat(w - arg.length) + arg;
      out += arg;
      if (stopped) return { text: out, plain: false };
      k += whole.length;
    }
    if (!consumed) break;   // a format with no conversion prints once, whatever the operands
  }
  return { text: out, plain: plainText };
}
function printfOutput(words) {
  let k = 0;
  if (!words.length) return unresolvable('a printf with no format, which prints nothing and reports an error');
  const first = words[0].text;
  if (first === '--') { k = 1; if (words.length < 2) return unresolvable('a printf with no format after `--`, which prints nothing and reports an error'); }
  else if (first === '-v') return plain(['']);   // prints nothing in every shell (bash and zsh assign the text to the name; dash rejects the option and prints nothing), measured: the empty text, plain
  else if (first.length > 1 && first[0] === '-') return unresolvable(`a printf whose first word is \`${first}\`: an option bash and dash reject and a format zsh prints`);
  const fmt = words[k].text;
  const operands = words.slice(k + 1).map((w) => w.text);
  const texts = [];
  let plainText = true;
  for (const sh of PRINTF_SHELLS) {
    let r;
    try { r = printfFor(sh, fmt, operands); }
    catch (e) { if (e instanceof Undecodable) return unresolvable('an escape in the printf for a byte or a NUL I do not decode'); throw e; }
    if (r.unresolvableReading) return r;
    texts.push(r.text);
    if (!r.plain) plainText = false;
  }
  return plainText && texts.every((t) => t === texts[0]) ? plain([texts[0]]) : sound(texts);
}
// What one lexed segment prints when its command is a literal echo or printf with no redirection, here-document, substitution or
// further command: echoOutput's or printfOutput's reading, UNRESOLVABLE when an operand carries a glob character or a brace list
// the shell expands before the command prints (the text printed is what the expansion gives, which the resolver does not compute)
// or a quoting whose reading depends on the shell, or is an expansion whose value the resolver does not read (`$(echo $t)`: the
// resolver applies to the echo and cannot establish what it prints), and null when the command is anything else (a text the guard
// cannot see, the residual: `$(cat f)`).
// THE APPLIED RESOLVER (round 6's sixth commit, 2026-09-21; the residuals verifier: `echo 'cp a b' 2>/dev/null | bash`, `</dev/null`,
// `3>/dev/null`, `>/dev/stdout`, `>/dev/fd/1`, `2>>`, `2>|`, `2<>`, a here-document or here-string on the echo inside a subshell, the
// same inside `$(..)`, a here-string, a `<(..)` and a here-document, zsh's MULTIOS write forms, and `(echo 'cp a b' && true) | bash`
// with `||`, `&& :`, in a group, after `true;`, across a newline, inside `$(..)`, a `<(..)`, a value and an eval, each ran the text in
// the shells named while the printer was dropped as outside the model and the list read as printer-less, null, the residual pass):
// once the resolver APPLIES to a segment (its head is a literal echo or printf, or a cat fed a here-document, alone or in a list or
// group of them), every shape it does not model is UNRESOLVABLE, never null: a redirection, a here-document, a `<`, a substitution, an
// arithmetic body or a brace the lexer cut on the printer, a `&&`, `||`, `&` or `|` after it inside a list, and a redirection on
// the closer of the subshell or group holding it. null is reserved for a segment whose head is no printer at all (the producer
// outside the output model, the residual the property names).
// THE SPLICED PRINTER (round 6's seventh commit, 2026-09-21; the body auditor: `e=echo; $e 'cp a b' | bash` was REFUSED by name at the
// round-5 head and ALLOWED from the round's first commit while bash, zsh and dash ran the text, and so were `e=printf; $e '%s\n' '..' |
// bash`, `"$e"`, `e=/bin/echo`, `${e}`, `${e}o` with e=ech, `$e cp a b | sh`, and the same head inside `bash -c "$($e '..')"`, a
// here-string and a `<(..)`: printerOf read the raw words, an expansion head was `unknown` to commandOf, and null, the answer reserved
// for a head that is no printer, was the allow). A command name that is an expansion stands for the texts THE HEAD CANDIDATES hold for
// it (activeHeadTexts, extract's resolver over the shared candidates); the segment is read again with each text spliced in the name's
// place, the other words and the segment's redirections as spelled, and where ANY text makes it a literal echo, printf or cat of a
// here-document the resolver applies: the printed text is the union over the texts of what each spliced command prints, and a text
// under which the command is no printer, prints by another rule, or reads as more than one command is UNRESOLVABLE, never null. null
// stays the answer for a head no candidate makes a printer (a name with no value in the command: the residual the property names;
// `e=cat; $e f | bash`: a producer outside the model) and for a name scriptTexts refuses at the head (an unread value). The splice
// is decided BEFORE printer-ness, the same order the writer, consumer and passthrough heads already had (THE HEAD SPLICE in extract).
// Depth is bounded (a value spelled as an expansion, `e='$e'`, would otherwise splice without end): past the cap the printer is
// UNRESOLVABLE.
let activeHeadTexts = null;   // (word) => the texts the name stands for, or null; set by extract while it runs
const SPLICE_DEPTH_CAP = 8;
let spliceDepth = 0;
function splicedPrinter(s, headIdx) {
  if (!activeHeadTexts) return null;
  const headWord = s.words[headIdx];
  const texts = activeHeadTexts(headWord);
  if (!texts || !texts.length) return null;
  if (spliceDepth >= SPLICE_DEPTH_CAP) return { name: 'echo', spliced: [], capped: true, raw: headWord.raw, args: [], chdirs: [], writes: [] };
  const before = s.words.slice(0, headIdx).map((w) => w.raw).join(' ');
  const after = s.words.slice(headIdx + 1).map((w) => w.raw).join(' ');
  const alternatives = [];
  let printer = null;
  spliceDepth++;
  try {
    for (const text of texts) {
      const r = lex([before, text.replace(/\n+/g, ' '), after].filter(Boolean).join(' '), s.shell || null);
      const one = !r.opaque && r.segments.length === 1 && !r.segments[0].paren && !r.segments[0].op ? r.segments[0] : null;
      const seg = one ? { ...one, redirects: [...one.redirects, ...s.redirects], heredocs: [...one.heredocs, ...s.heredocs], stdin: [...(one.stdin || []), ...(s.stdin || [])], dups: [...(one.dups || []), ...(s.dups || [])], subs: [...one.subs, ...s.subs], viaSubs: [...one.viaSubs, ...s.viaSubs], arith: [...one.arith, ...s.arith], closerTail: s.closerTail, op: s.op, shell: s.shell } : null;
      const p = seg ? printerOf(seg) : null;
      if (p && !printer) printer = p;
      alternatives.push({ text, seg, printer: p });
    }
  } finally { spliceDepth--; }
  if (!printer) return null;
  return { name: printer.name, args: alternatives.flatMap((a) => (a.printer ? a.printer.args : [])), spliced: alternatives, raw: headWord.raw, chdirs: [], writes: [] };
}
const printerOf = (s) => {
  if (s.paren) return null;
  const cmd = commandOf(s.words);
  if (!cmd || cmd.opaque) return null;
  if (cmd.unknown) {
    // THE WRAPPED PRINTER (round 6's eighth commit, 2026-09-22; the body auditor: `e=echo; command $e 'cp a b' | bash` was allowed at the seventh
    // commit's head while every shell ran the printed text, and the same behind env, nice, exec, builtin and a printf, where the round-5 head had
    // refused each as a wrapper option it did not read): the wrapper's walk (commandOf) stopped at a word that is an expansion, in the position
    // the command name or an option takes; the word is spliced through THE SPLICED PRINTER as a bare head is, the segment re-lexed with each text
    // in its place, and commandOf peels the wrapper again on the spliced text (one road: the wrapper stripping the writer, consumer and passthrough
    // heads get through the walk's resolved words). A wrapper option the walk does not parse stays what it was (the walk's rule (b) refuses it).
    const at = cmd.unknown.at;
    const w = at != null ? s.words[at] : null;
    return w && !w.literal && w.marks && w.marks.includes('x') ? splicedPrinter(s, at) : null;
  }
  const headIdx = cmd.name ? s.words.length - cmd.args.length - 1 : -1;
  const headWord = headIdx >= 0 ? s.words[headIdx] : null;
  if (headWord && !headWord.literal && headWord.marks && headWord.marks.includes('x')) return splicedPrinter(s, headIdx);   // THE SPLICED PRINTER: a command name that is an expansion (commandOf names it by its spelling), read through the texts it stands for
  if ('script' in cmd || cmd.chdirs.length || cmd.writes.length) return null;
  if (cmd.name === 'echo' || cmd.name === 'printf') return cmd;
  return cmd.name === 'cat' && s.heredocs.length ? cmd : null;
};
// what a spliced printer prints: the union over the texts the name stands for, each read as the command it splices to (THE SPLICED PRINTER)
function splicedOutput(cmd) {
  if (cmd.capped) return unresolvable(`the command name \`${cmd.raw}\` stands for a text that is itself a command name standing for a text, nested past the depth I follow, so the text printed is not known`);
  const texts = new Set();
  for (const a of cmd.spliced) {
    const stands = `the command name \`${cmd.raw}\` stands for \`${a.text}\``;
    if (!a.seg) return unresolvable(`${stands}, a text the shell reads as more than one command or as an operator, beside a text under which it is a ${cmd.name}, so the text printed is not known`);
    if (!a.printer) return unresolvable(`${stands}, a command whose output I do not read, beside a text under which it is a ${cmd.name}, so the text printed is not known`);
    if (a.printer.name !== cmd.name) return unresolvable(`${stands}, which prints by another rule than the ${cmd.name} another text makes it, so the text printed is not known`);
    let r;
    if (cmd.name === 'cat') { const bodies = catOfHeredoc(a.seg); r = bodies ? sound(bodies) : unresolvable(`${stands}, a cat whose here-document I do not read alone, so the text printed is not known`); }
    else r = segmentOutput(a.seg);
    if (r == null) return unresolvable(`${stands}, whose output I do not read, so the text printed is not known`);
    if (r.unresolvableReading) return r;
    for (const t of r.texts) texts.add(t);
  }
  return sound([...texts]);   // the text depends on a value the command gives: the script road, never plain
}
const shapeOnPrinter = (s, name) => {
  if (s.op && s.op !== ';' && s.op !== '\n' && s.op !== '|' && s.op !== ')') return `the ${name} is followed by \`${s.op}\`, an operator outside the model (whether and when its text reaches the stream depends on it), so the text printed is not known`;
  if (s.redirects.length || s.heredocs.length || (s.stdin && s.stdin.length) || (s.closerTail && s.closerTail.length)) return `a redirection, a here-document, a \`<\` or a brace the lexer cut stands on the ${name}, so whether its text reaches the stream is not known`;
  if (s.subs.length || s.viaSubs.length || s.arith.length) return `an operand of the ${name} holds a substitution or an arithmetic body whose text I do not read, so the text printed is not known`;
  return null;
};
function segmentOutput(s) {
  const cmd = printerOf(s);
  if (!cmd || cmd.name === 'cat') return null;
  if (s.op === ')') return null;   // a closer the lexer read as the segment's operator ends the list, not the printer (listOutput reads the list)
  if (cmd.spliced) return splicedOutput(cmd);   // THE SPLICED PRINTER: each text the name stands for, read as the command it splices to
  const shape = shapeOnPrinter(s, cmd.name);
  if (shape) return unresolvable(shape);
  const inner = cmd.args.find((w) => w.unresolvableReading);
  if (inner) return unresolvable(inner.unresolvableReading.why);   // an operand built from a reading the resolver could not establish: neither can this one
  if (cmd.args.some((w) => (w.marks && w.marks.includes('x')) || w.text.includes('\0'))) return unresolvable(`an operand of the ${cmd.name} is an expansion whose value I do not read, so the text printed is not known`);   // the resolver applies to the command and cannot establish what it prints (a value it never reads: `$(echo $t)`)
  if (!cmd.args.every((w) => w.literal)) return unresolvable(`an operand of the ${cmd.name} carries a glob character, a brace list or a quoting the shell expands before the ${cmd.name} prints, so the text printed is not the text spelled`);
  return cmd.name === 'echo' ? echoOutput(cmd.args) : printfOutput(cmd.args);
}
// What a `$(...)`, a backtick or a `<(...)` prints when its command is one echo or printf with literal operands and no redirection,
// here-document, substitution or further command (THE RESOLVED SUBSTITUTION in lex; the file a `bash <(echo '..')` or a `bash <
// <(echo '..')` reads): segmentOutput's reading of the one segment, or null when the command is anything else. `depth` is the
// lexer's nesting, capped as the `${` descent is.
function literalOutput(inner, shell, depth = 0) {
  if (depth >= NESTED_DEPTH_CAP || !(/echo|printf|cat/.test(inner) || (activeHeadTexts && inner.includes('$')))) return null;   // a text with an expansion may name a printer through THE SPLICED PRINTER
  const r = lex(inner, shell, { depth: depth + 1 });
  if (r.opaque) return null;
  return listOutput(r.segments);   // round 6's second commit: the list inside, one segment or several (THE OUTPUT MODEL)
}
// THE OUTPUT MODEL (round 6's second commit, 2026-09-20; round 5's tests-1 found `(echo 'cp ..') | bash` and `{ echo 'cp ..'; } | bash`
// pinned allowed under a label that called the producer one the guard cannot read, while the text stood in the command and bash, zsh
// and dash ran it, and the same wrapper defeated `bash -c "$(...)"`, `bash <(...)` and the here-string): what a command LIST prints, a
// subshell's or a `{ }` group's body before a pipe, the list inside a `$(...)`, a backtick or a `<(...)`. The outputs of its simple
// segments in order, concatenated as the shells concatenate them on the one stream. A segment whose command is a literal echo or
// printf prints segmentOutput's reading, an echo's text followed by the newline every shell adds (when the echo takes no option word
// and its operands hold no backslash: zsh's `-` and a `\c` omit it, so beside another printer such an echo is UNRESOLVABLE), a printf's
// text as it is; a `cat` with no operand (or `-`) fed one here-document prints the body (the text stands in the command: `bash -c
// "$(cat <<'EOF' .. EOF)"` ran the body in every shell, measured); a segment that prints nothing on the stream adds nothing
// (SILENT_COMMANDS with no wrapper, assignment words alone, a paren marker, a `{` or `}` alone); any other segment, or one holding a
// redirection, a here-document elsewhere, a `<`, a substitution, an arithmetic body, or an operator that is not `;`, a newline or the
// list's own closer (a `|` inside sends the segment's output to the next command, `&&`, `||` and `&` are outside the model), puts the
// list outside the model: UNRESOLVABLE when a printer stands beside it (a part of the text on the stream the resolver cannot
// establish), null when nothing in the list prints by the model (`(cat f) | bash`, as `cat f | bash`: the producer outside the output
// model, the residual the surfaces name). One printer alone is its own reading unchanged (plain stays plain: the text road is open to
// `$(echo cp)` as before); several are joined, the union capped at 64 texts (past it, UNRESOLVABLE).
const SILENT_COMMANDS = new Set(['true', ':', 'false', 'test', '[', 'sleep', 'shift', 'break', 'continue', 'exit', 'return', 'wait']);
const catOfHeredoc = (s) => {
  if (!s.heredocs.length || s.redirects.length || (s.stdin && s.stdin.length) || s.subs.length || s.viaSubs.length || s.arith.length || (s.closerTail && s.closerTail.length)) return null;
  const cmd = commandOf(s.words);
  if (!cmd || cmd.unknown || cmd.opaque || 'script' in cmd || cmd.wrapped || cmd.chdirs.length || cmd.writes.length || cmd.name !== 'cat') return null;
  if (cmd.args.some((w) => !(w.literal && (w.text === '-' || w.text === '-u')))) return null;
  return s.heredocs.map((b) => b + '\n');   // the body, each alternative the lexer read of it, with the newline the shell ends the data with
};
function listOutput(segs) {
  const parts = [];
  let outside = false;
  let compound = null;   // the head of a keyword compound in the list (THE COMPOUND PRODUCER): the refusal names it
  for (let k = 0; k < segs.length; k++) {
    const s = segs[k];
    if (s.paren) continue;
    if (s.words.length && s.words.every((w) => plainWord(w) && (w.text === '{' || w.text === '}'))) continue;
    // THE COMPOUND PRODUCER (round 6's fourth commit, 2026-09-21): a keyword compound's head runs its body a number of times the model does
    // not count (a loop), or not at all (a condition), so it is a command the model does not read, and a printer inside it makes the list
    // UNRESOLVABLE, the head named; its closer alone (`fi`, `done`, `esac`, `end`) and a `;;` print nothing and add nothing
    const head0 = compoundHeadOf(s.words);
    if (head0 != null && Object.hasOwn(BODY_CLOSER, head0)) { outside = true; if (!compound) compound = head0; continue; }
    if (s.words.length && s.words.every((w) => plainWord(w) && (Object.hasOwn(CLOSERS, w.text) || w.text === ';;'))) continue;
    // THE APPLIED RESOLVER: a printer followed by an operator outside the model, or carrying a shape outside it, is UNRESOLVABLE with the
    // shape named; a segment whose head is no printer puts the list outside the model (null when nothing in the list prints)
    const printer = printerOf(s);
    if (printer && s.op && s.op !== ';' && s.op !== '\n' && s.op !== ')') return unresolvable(`the ${printer.name} is followed by \`${s.op}\`, an operator outside the model (whether and when its text reaches the stream depends on it), so the text printed is not known`);
    if (s.op && s.op !== ';' && s.op !== '\n' && s.op !== ')') { outside = true; continue; }
    const cat = catOfHeredoc(s);
    if (cat) { parts.push({ texts: cat, plain: false, newline: false }); continue; }
    if (s.redirects.length || s.heredocs.length || (s.stdin && s.stdin.length) || s.subs.length || s.viaSubs.length || s.arith.length || (s.closerTail && s.closerTail.length)) {
      if (printer) return unresolvable(shapeOnPrinter({ ...s, op: '' }, printer.name));
      outside = true;
      continue;
    }
    // THE SPLICED PRINTER: a command name that is an expansion, one of whose texts makes it a printer, prints the union over its texts
    if (printer && printer.spliced) { const r = splicedOutput(printerOf({ ...s, op: '' })); if (r.unresolvableReading) return r; parts.push({ texts: r.texts, plain: false, newline: printer.name === 'echo', echo: printer }); continue; }   // spliced again with the list's own operator cleared, as segmentOutput is called below
    const cmd = commandOf(s.words);
    if (!cmd) { if (s.words.every((w) => isAssignmentWord(w) || (plainWord(w) && RESERVED.has(w.text)))) continue; outside = true; continue; }
    if (cmd.unknown || cmd.opaque || 'script' in cmd || cmd.chdirs.length || cmd.writes.length) { outside = true; continue; }
    if (SILENT_COMMANDS.has(cmd.name) && !cmd.wrapped) continue;
    // a `cat` of the standard input with nothing in the list feeding it prints what the CALLER feeds the command, a text this reading cannot
    // see (round 6's third commit, 2026-09-21: `echo 'cp a b' | { bash -c "$(cat)"; }` and `| bash -c 'eval "$(cat)"'` ran the piped text in
    // every shell while the substitution was outside the model and the script went unread): UNRESOLVABLE, refused where a script or a
    // target is built from it; a cat after a `|` inside the list reads that pipe and stays outside the model with it (the residual)
    if (cmd.name === 'cat' && !cmd.wrapped && !(k > 0 && segs[k - 1].op === '|') && cmd.args.every((w) => w.literal && (w.text === '-' || w.text === '-u' || isStdinName(w.text)))) return unresolvable('a cat of the standard input stands in the list, and what the command feeds it is a text I do not read here, so the text printed is not known');
    if (cmd.name !== 'echo' && cmd.name !== 'printf') { outside = true; continue; }
    const r = segmentOutput({ ...s, op: '' });
    if (r == null) { outside = true; continue; }
    if (r.unresolvableReading) return r;
    parts.push({ texts: r.texts, plain: !!r.plain, newline: cmd.name === 'echo', echo: cmd });
  }
  if (!parts.length) return null;
  if (outside) return unresolvable(compound ? `a \`${compound}\` runs the echo, printf or cat inside it a number of times I do not count, so the text printed is not known` : 'a command whose output I do not read stands in the list beside an echo, a printf or a cat of a here-document, so the text printed is not known');
  if (parts.length === 1) return parts[0].plain ? plain(parts[0].texts) : sound(parts[0].texts);
  let texts = [''];
  for (const p of parts) {
    if (p.newline && p.echo.args.some((w) => /^-/.test(w.text) || w.text.includes('\\'))) return unresolvable('an echo with an option word or a backslash in its operands stands beside another command that prints, and whether its newline is printed differs by shell');
    const pieces = p.texts.map((t) => t + (p.newline ? '\n' : ''));
    texts = texts.flatMap((a) => pieces.map((b) => a + b));
    if (texts.length > 64) return unresolvable('a list printing more alternative texts than I hold');
  }
  return sound(texts);
}
// THE APPLIED RESOLVER at a closer before the pipe (a reading function: it calls listOutput and is placed through placeReading alone): a
// redirection, here-document or `<` on the `)`, the `}` or the compound's closer applies to the whole list, so where the list prints by the
// model its reading is UNRESOLVABLE (`(echo 'cp a b') 2>/dev/null | bash` ran the text in every shell, `(echo ..) >/dev/null | bash` in
// zsh under MULTIOS, `(time echo ..) 2>/dev/null | bash` in every shell, while the closer's redirection left the list unread); a list
// with no printer stays null (the residual)
function closerOutput(segs, closer, what) {
  const r = listOutput(segs);
  if (r == null || !(closer.redirects.length || closer.heredocs.length || (closer.stdin && closer.stdin.length))) return r;
  return unresolvable(`a redirection, a here-document or a \`<\` stands on the ${what} that holds the echo, printf or cat, so whether its text reaches the stream is not known`);
}
// What a segment prints on its standard output at the site lex's streamSite found (THE PIPED SCRIPT, THE WRITTEN PROCESS SUBSTITUTION):
// a simple command's output (segmentOutput), the list a closer ends (closerOutput), dash's `(( ))` list (listOutput over its lex), and for
// an `exec` that opens a process substitution for every later command of the shell, UNRESOLVABLE (the model does not follow what they
// print). A reading function (THE RESOLVER'S CONTRACT), consumed as placeReading's argument alone.
function streamOutput(site, view) {
  if (site.kind === 'exec') return unresolvable('an `exec` opens the process substitution for every later command of this shell, whose output I do not follow, so the text written into it is not known');
  if (site.kind === 'segment') return segmentOutput(view);
  if (site.kind === 'arith') { const r = lex(site.text, 'dash', { depth: site.depth }); return r.opaque ? null : listOutput(r.segments); }
  return closerOutput(site.segs, view, site.kind);
}
// THE DEFAULT WORD's reading (lex's braceParameter reads `${name:-word}` and its kin through this): the one word the nested lex made
// of the operator's word, its name and operator peeled (`prefixLen` literal characters at the text's start). Sound when the word is
// literal (every character quoted or plain), or is one expansion carrying readings of its own (a nested default word, a two-reading
// echo). UNRESOLVABLE when the word is no expansion the resolver leaves alone and still not literal: a glob character or a brace list
// (the shells expand it where the word is unquoted, and the guard does not compute the result), or a `$'...'` whose reading depends on
// the shell (round 5's correctness-2: a `*` made the word non-literal and the script went to the shell unread), or an expansion
// whose value the resolver does not read (`${x:-$(cat f)}`, `${x:-$y}`: the resolver applies to the operator's word and cannot
// establish it; the plain `${x}`, which has no operator, is no reading of this function and keeps the residual). null when the
// operator's word is several segments or empty.
function defaultWordReading(nested, prefixLen, param = null) {
  // THE PARAMETER'S VALUE (round 6's fifth commit; lex's defaultReading says why): the reading carries the name and operator whose value
  // decides between the value and the word (`params`), so extract's scriptTexts can join the value or refuse; a `?` form stands for the
  // value alone (the word is a message the shell prints as it exits), so its reading is no text and the name.
  // THE ALTERNATE VALUE (round 6's tenth commit, 2026-09-22; the round's verifiers: `eval cp ${c:+x} ../base/report.md report.md` ran the
  // two-operand copy in every shell while the word read as `x` alone made three operands and allowed): a `${name:+word}` or `${name+word}`
  // stands for the word when the name is set (and non-empty, with the colon) and for NOTHING otherwise, so the word alone is a sound reading
  // only when the name is known set; the reading carries the name and operator (`plus`), and extract's scriptTexts adds the empty reading (the
  // word dropped) where the name may be unset, refusing a text a copying writer's operand count then makes a write. A name every shell always
  // sets to a non-empty value (`$#`, `$$`, `$0`, `$?`, `$-`) has no empty reading, so its `+` word stands alone as before (THE SPECIAL PARAMETER).
  const ALWAYS_SET = /^[#$0?-]$/;
  const withParam = (r) => {
    if (!param) return r;
    if (/\+$/.test(param.op)) return param.name && ALWAYS_SET.test(param.name) ? r : Object.assign(r, { params: [...(r.params || []), { ...param, plus: true }] });
    return Object.assign(r, { params: [...(r.params || []), param] });
  };
  // THE SPECIAL PARAMETER (round 6's sixth commit, 2026-09-21; the body auditor: `${#:+cp} a b`, `${?:+cp}`, `${0:+cp}`, `${$:+cp}`, `${-:+cp}`, their
  // `+` twins, `${1:-cp}`, `${9:-cp}`, `${10:-cp}`, `${@:-cp}`, `${*:-cp}`, `${!:-cp}`, `set -- x; ${1:+cp} a b`, and the consumers `${$:+bash} -c`,
  // `| ${#:+bash}`, `${#:+eval}` and `${#:+.} <(..)` each ran the copy in the shells named while the default-word grammar read names alone and the
  // word was an expansion the resolver never read): the `+` forms stand for the word or nothing whatever the parameter, so the word alone is their
  // reading; a `-`, `=` or `?` form over a special parameter (`#`, `?`, `0`, `$`, `!`, `-`, `@`, `*`: the count, the status, the shell's name, its
  // pid, the last background pid, the option flags, the positional parameters as a whole) stands for a value that is the shell's own, UNRESOLVABLE;
  // over a positional parameter (a digit run) it carries the name as any default word does, and THE POSITIONAL VALUE in extract joins the operand
  // the name stands for, refusing where none is known
  if (param && !/\+$/.test(param.op) && (param.name === '0' || /^[#?$!@*-]$/.test(param.name))) return unresolvable(`the word stands for the value of the special parameter \`${param.name}\` when it is set, a value that is the shell's own (the count, the status, the shell's name or pid, the option flags, the positional parameters as a whole), which I do not read, so the text is not known`);
  if (param && /\?$/.test(param.op)) return withParam(sound([]));
  if (nested.opaque || nested.segments.length !== 1 || !nested.segments[0].words.length) return null;
  const [s] = nested.segments;
  if (s.words.length > 1) return unresolvable('the word holds a brace list, which zsh expands where the word is unquoted while bash and dash close the `${...}` at its first brace, so the text the shell makes of it is not the text spelled');   // oneWord mode makes one word of the text but for a brace list
  const [w] = s.words;
  if (s.subs.length || s.viaSubs.length) return unresolvable('the word holds a substitution whose text I do not read, so the text the shell makes of it is not known');   // `${x:-$(cat f)}`, `${x:-$(cp a b)}`: the command runs (read through viaSubs) and its output is the word
  if (s.redirects.length || s.heredocs.length || (s.stdin && s.stdin.length)) return null;
  const tail = w.text.slice(prefixLen);
  const tailMarks = (w.marks || '').slice(prefixLen);
  if (w.literal || (param && !IDENTIFIER.test(param.name) && w.glob && !tailMarks.includes('x') && !hasGlobChar(tail, tailMarks) && !tail.includes('\0'))) return withParam(sound([tail]));   // the name and operator are literal characters at the text's start; a special parameter's `?`, `*` or `@` is a glob character to the lexer but the word's NAME (THE SPECIAL PARAMETER), so the word is literal when the text after it is
  if (w.unresolvableReading) return unresolvable(w.unresolvableReading.why);
  if (w.readings && w.marks && /^x+$/.test(w.marks.slice(prefixLen))) return withParam(Object.assign(sound(w.readings), w.readingParams ? { params: [...w.readingParams] } : {}));   // the word is one expansion with readings of its own (a nested default word, a two-reading echo): they are this word's too, and so are the names the inner word depends on
  if ((w.marks && w.marks.slice(prefixLen).includes('x')) || w.text.includes('\0')) return unresolvable('the word holds an expansion whose value I do not read, so the text the shell makes of it is not known');   // `${x:-$(cat f)}`, `${x:-$y}`: the resolver applies to the operator\'s word and cannot establish it
  return unresolvable('the word holds a glob character, a brace list or a quoting whose reading depends on the shell, so the text the shell makes of it is not the text spelled');
}
// THE SINGLE FIELD (round 6, 2026-09-20; for THE SPLIT OPERAND in extract): whether a word spelled entirely inside one pair of double
// quotes is one field in bash, zsh and dash after expansion. THE PROPERTY: inside double quotes no expansion splits except the ones
// the shells define to produce one word per element, so the word is one field unless it holds one of those. Derived from the
// grammars (bash: Special Parameters and Arrays; dash(1): Parameter Expansion; zshexpn(1): Parameter Expansion and its flags):
// `$@` and every `${@...}` (`"${@}"`, `"${@:2}"`, `"${@:1:2}"`, `"${@#x}"`, `"${@/x/y}"`) give one word per positional parameter in
// every shell; a subscript `[@]` (`"${arr[@]}"`, `"${arr[@]:1}"`, `"${!arr[@]}"`, `"${arr[@]/x/y}"`, and zsh's unbraced `"$arr[@]"`)
// one per element; bash's `${!prefix@}` one per name; zsh's flags and modifiers open the brace with `(`, `=`, `~` or `^` (`"${(@)arr}"`,
// `"${(s: :)s}"`, `"${(f)s}"`, `"${(z)s}"`, `"${=s}"`) and split or expand by rules the guard does not read. So a `${...}` whose inner
// text opens with `!`, `(`, `=`, `~` or `^`, or holds an `@`, and a `$@` or `$name[@]` anywhere in the word, make it a word that MAY
// split (the safe side: an unknown form is refused, never exempted); `$name`, `${name}`, `${name<op>...}`, `$*`, `${arr[*]}`, `$#`,
// `$?`, `$$`, `$!`, `$0`, a `$(...)`, a backtick and `$((...))` are one field. Pinned by execution in the three shells
// (tools/romp-track-bash-guard-shapes.test.mjs).
export function dqSingleField(raw) {
  const m = raw.match(/^"([^"]*)"$/);
  if (!m) return false;
  const inner = m[1];
  for (let i = 0; i < inner.length; i++) {
    if (inner[i] === '\\') { i++; continue; }
    if (inner[i] !== '$') continue;
    const n = inner[i + 1];
    if (n === '@') return false;
    if (n === '=' || n === '^' || n === '~') return false;   // zsh's unbraced flags (round 6's third commit): `"$=s"` splits, as the braced `"${=s}"` below does; `^` and `~` on the safe side, as their braced forms are
    if (n === '{') {
      let depth = 1;
      let j = i + 2;
      while (j < inner.length && depth > 0) { if (inner[j] === '{') depth++; else if (inner[j] === '}') depth--; j++; }
      const body = inner.slice(i + 2, depth > 0 ? inner.length : j - 1);
      if (/^[!(=~^]/.test(body) || body.includes('@')) return false;
      i = j - 1;
      continue;
    }
    const name = inner.slice(i + 1).match(/^[A-Za-z_][A-Za-z0-9_]*/);
    if (name && inner.startsWith('[@]', i + 1 + name[0].length)) return false;   // zsh's unbraced subscript
  }
  return true;
}
// The command inside a word that is one process substitution (`<(cmd)`, `>(cmd)`, zsh's `=(cmd)`), as the lexer spells such a word
// (the spelling, every character an expansion's), or null.
const procsubOf = (w) => (w && w.marks && /^x+$/.test(w.marks) && /^[<>=]\([^]*\)$/.test(w.text) ? w.text.slice(2, -1) : null);
// THE VANISHING OPERAND (round 6's eighth commit, 2026-09-22; the residuals verifier: `cp $c ../base/report.md report.md`, `cp ../base/report.md $c
// report.md`, `cp ${c:-} ..`, `cp $(true) ..`, `cp $* ..`, `cp "$@" ..`, `cp ${x[@]} ..`, `c=; cp $c ..`, `cp $1 ..`, `shopt -s nullglob; cp nomatch* ..`,
// and the same through mv, install, `ln -sf` and `ln -f`, from docs/ and by absolute paths from a cwd in no project, each ALLOWED while bash, zsh and
// dash ran the two-operand copy onto the tracked file: copyTargets read three operands and a destination that is no directory as a copy the command
// stops on, while the shell made no word of the empty expansion and ran the copy with two). THE RULE, from the grammars (bash: Word Splitting, "if
// the value is empty, no field results", and Special Parameters; dash(1): Word Expansions; zshexpn(1): Parameter Expansion, Filename Generation):
// an unquoted expansion whose value is empty or unset, or IFS whitespace in bash and dash, yields NO field; so do `$@`, `$*` and `"$@"` with no
// positional parameter, an array's `[@]` with no element, an unquoted command substitution printing nothing, and a pattern matching nothing under
// bash's nullglob or zsh's null_glob (bash and dash keep the pattern's text otherwise, zsh stops); a literal character outside the expansions makes
// at least one field, a double-quoted word the guard proves one field (dqSingleField) is one field however empty, a process substitution is a
// path, and an arithmetic expansion, a `${#name}` length, `$?`, `$$`, `$#` and `$0` are never empty. A copying writer's operand that may vanish
// makes the operand COUNT a set (the mirror of THE SPLIT OPERAND, whose one operand may become several): the destination is judged under the
// list as spelled and under every list with such operands dropped (vanishVariants), a write under any of them refused with the operand dropped
// named; more than VANISH_CAP such operands make the count a target the hook cannot read. A value the readability rule resolved is a literal
// word (resolveWord keeps an empty or blank value as the expansion, so `c=; cp $c a b` is read here); a pattern the guard expanded is its
// matches (copyTargets drops a source matching nothing already, the same reading under a known directory), and one it could not expand (the
// directory unknown) may vanish. Pinned by execution in the three shells (the eighth commit's rows test), the never-empty forms among them.
const NEVER_EMPTY_EXPANSION = /^(?:\$\(\(|\$\{#|\$[?$#0]$|\$\{[?$#0]\}$)/;   // never an empty value in any shell: an arithmetic expansion, a length, and the parameters every shell sets
const VANISH_CAP = 6;
function mayVanish(w, cwdKnown) {
  if (w.literal) return false;
  if (w.glob) return !cwdKnown;
  if (!w.marks || !/^x+$/.test(w.marks)) return false;
  if (dqSingleField(w.raw)) return false;
  if (procsubOf(w) != null) return false;
  return !NEVER_EMPTY_EXPANSION.test(w.raw);
}
// The operand lists the shell may hand a copying writer besides the one spelled: `args` with each non-empty subset of the operands that may vanish
// dropped ({ dropped, kept }), or null past VANISH_CAP such operands (the caller then records the count as a target it cannot read).
function vanishVariants(args, cwdKnown) {
  const vanishing = args.map((a, i) => (!(a.text.startsWith('-') && a.text.length > 1) && mayVanish(a, cwdKnown) ? i : -1)).filter((i) => i >= 0);
  if (vanishing.length > VANISH_CAP) return null;
  const out = [];
  for (let mask = 1; mask < (1 << vanishing.length); mask++) {
    const dropped = vanishing.filter((_, b) => mask & (1 << b));
    out.push({ dropped: dropped.map((i) => args[i]), kept: args.filter((_, i) => !dropped.includes(i)) });
  }
  return out;
}
// what the refusal says of the operands dropped under a vanishing reading
const droppedHow = (name, dropped) => `${name} (once the shell drops ${dropped.map((w) => `\`${w.raw}\``).join(' and ')}, ${dropped.some((w) => w.glob) ? 'a pattern it makes no word of when nothing matches under nullglob or null_glob' : 'an operand it makes no word of when the value is empty or unset'})`;

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
// THE VALUED NAMES (round 6's fourth commit, 2026-09-21; the body auditor: `PS4='$(cp a b)'; set -x; :`, `PS4='$(cp a b)' bash -xc :`,
// `export PS4='$(cp a b)'; bash -xc :` and `PROMPT_COMMAND='cp a b' bash -i </dev/null` each ran the copy while the value stood in the
// command as text). Names whose VALUE the shell runs: bash's prompt strings, whose `$(..)` and backticks run when the prompt is printed or a
// traced command is echoed, and PROMPT_COMMAND, a command run before each prompt (bash(1), PROMPTING). The value assigned is read as a
// script of this shell (extract's readValuedWords).
const SCRIPT_VALUED_NAMES = new Set(['PS0', 'PS1', 'PS2', 'PS3', 'PS4', 'PROMPT_COMMAND']);
// Names whose value is a FILE the shell sources at startup: ENV, read by sh, dash and ksh when interactive and by bash in POSIX mode, and
// BASH_ENV, read by a non-interactive bash (bash(1), INVOCATION; dash(1)). A value that is a process substitution printing a text the
// resolver reads is that text, a script of the shell (`ENV=<(echo 'cp a b') dash -i </dev/null` copied in bash and zsh, the substitution
// performed by the shell running the line); read whether or not `-i` is spelled, the safe side, as `--rcfile` is.
const STARTUP_FILE_NAMES = new Set(['ENV', 'BASH_ENV']);
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
const RESOLVED_NAME = /^\$(?:\{([A-Za-z_][A-Za-z0-9_]*|[0-9]+)\}|([A-Za-z_][A-Za-z0-9_]*|[0-9]))/;   // a positional parameter is a name to the rule since round 6's sixth commit (THE POSITIONAL VALUE): `$1` one digit unbraced (`$10` is `${1}0` in bash and dash but the tenth positional in zsh, so resolveWord's THE MULTI-DIGIT POSITIONAL leaves it unread where zsh may run the line), `${10}` any run braced; its value is the operand extract holds for it, or none
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
// THE PAREN RULE (round 6's eighth commit, 2026-09-22; the residuals verifier: `(case x in x) echo 'cp a b';; esac) | bash` and `bash -c "$(case x in
// x) echo 'cp a b';; esac)"` were allowed while bash, zsh and dash ran the echoed text, the unparenthesised pattern's `)` having closed the lexer's
// subshell or substitution so the producer after it was lost, where the walk's closeSubshell already knew that in a case body a `)` ends a
// pattern): which open scope, innermost last, a `)` closes. The innermost subshell, unless a case body or a function definition is open inside it,
// where the `)` ends a case pattern (or is the definition's own) and closes nothing: -1 then, else the index of the subshell closed. ONE HOME: the
// walk's closeSubshell asks it over its frames, and the lexer asks it over the scopes it tracks (a `(` marker, a segment headed by `case`, its
// `esac`) to mark a `)` that ends a pattern (`pattern` on the marker, skipped by the scans that pair parentheses) and, inside skipNested, to keep
// reading a `$(..)` or `<(..)` past such a `)`; the shells' grammars agree (bash: Compound Commands, case; dash(1): Case; zshmisc(1): Complex
// Commands), each reading the `)` after a pattern as the pattern's end and never as a subshell's.
function parenCloses(kinds) {
  for (let j = kinds.length - 1; j >= 0; j--) {
    if (kinds[j] === 'case' || kinds[j] === 'function') return -1;
    if (kinds[j] === 'subshell') return j;
  }
  return -1;
}
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
// Round 5's fifth addendum (2026-09-20): the further commands dash reads after a `&&` or `||` inside a `[[ ... ]]` (closeTest)
// take their place in the walk as segments of their own after the test's, joined by the operator dash read before each, so the
// walk's rules for a command after `&&` or `||` apply to them (a cd there leaves the directory unknown, an assignment there is
// unreadable, a writer or a redirection there is judged, each refusal naming the construct through `dashPiece`); lex's own output
// stays the bash and zsh reading, one segment per test.
function withDashPieces(segs) {
  if (!segs.some((s) => s.dashPieces && s.dashPieces.length)) return segs;
  const out = [];
  for (const seg of segs) {
    out.push(seg);
    if (!seg.dashPieces || !seg.dashPieces.length) continue;
    const pieces = seg.dashPieces;
    pieces[pieces.length - 1].op = seg.op;
    seg.op = seg.dashFirstOp;
    out.push(...pieces);
  }
  return out;
}
function extract(command, ctx) {
  const prevHeads = activeHeadTexts;   // THE SPLICED PRINTER: the resolver is this text's while it is read and the caller's again after, whatever ends the read
  try { return extractIn(command, ctx); } finally { activeHeadTexts = prevHeads; }
}
function extractIn(command, ctx) {
  const { shell, depth } = ctx;
  const inheritedStdin = ctx.stdin || [];   // what this script's commands read on stdin when nothing of their own feeds them (the third fix-up: a `-c` script's stdin is its caller's)
  let walkIdx = -1;                          // the segment the walk is on (pipedFrom, recurse)
  const prevLinks = activeLinks;
  const ifsNamed = !!ctx.ifsNamed || /\bIFS\b/.test(command);   // THE IFS RULE (round 6's fourth commit, 2026-09-21): the command names IFS, here or in the text that handed this one over, so an unquoted expansion splits by a rule the resolver does not compute (resolveWord, scriptTexts; lex declines the resolved substitution the same way)
  const lexOpts = ifsNamed ? { ifsNamed: true } : {};
  // THE SPLICED PRINTER (round 6's seventh commit): lex asks activeHeadTexts for the texts a command name that is an expansion stands for; this
  // text answers through THE HEAD CANDIDATES once they are noted (headTextsOf, set beside candidateTexts below) and through the caller's resolver
  // before that (the candidates are one map shared by every recursion, so a nested text's first read sees the caller's values); the command is
  // read again below once its own values are noted, so a head the first read could not splice is spliced on the second
  const callerHeads = activeHeadTexts;
  let headTextsOf = null;
  activeHeadTexts = (w) => (headTextsOf ? headTextsOf(w) : callerHeads ? callerHeads(w) : null);
  let lexed = lex(command, shell, lexOpts);
  let segments = withDashPieces(lexed.segments);
  let opaque = lexed.opaque;
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
  // THE ALIAS ROAD (round 6's second commit, 2026-09-20; round 5's extra7-2: `alias c=cp` and, on the next line, `c ../base/report.md
  // report.md` were read as two unknown commands and allowed while dash copied through `-c`, zsh and dash through a here-document or a
  // pipe, and bash under `expand_aliases`, measured; the text stood in the command). `aliases`: name -> { body (the text the shell puts in
  // the name's place, null when the resolver cannot read it), line (the definition's line: the shells expand an alias when a later line
  // is read, never on the line that defines it; bash reads a whole compound before running it, so a use inside one is over-included on
  // the safe side), global (zsh's `-g`: the name is expanded in every word position), suffix (zsh's `-s`: a command word ending in
  // `.name` runs the body with the word as its operand) }. `hashes`: name -> the path `hash -p PATH NAME` (bash) or `hash NAME=PATH`
  // (zsh) binds it to, null when unreadable. `aliasState.unread`: an alias whose NAME the resolver cannot read was defined, so every
  // later command name may be it. `bound`: an absolute path the command made by a copy or a link (cp, install, ln, link, mv) -> the
  // literal source's text, null when the source is not literal, so `cp /usr/bin/cp ../scratch/c2; ../scratch/c2 a b` is read as the copy it
  // runs (measured: every shell copied). `aliasChain`: the alias names being expanded on this road (a name identical to one of them is not
  // expanded again, the shells' own rule). A fresh shell (`bash -c`) inherits no alias or hash; the paths made are on the filesystem for
  // every shell. Consumed by THE HEAD SPLICE in the walk below.
  const aliases = ctx.aliases || new Map();
  const hashes = ctx.hashes || new Map();
  const aliasState = ctx.aliasState || { unread: null };
  const bound = ctx.bound || new Map();
  const aliasChain = ctx.aliasChain || new Set();
  // THE HEAD CANDIDATES (round 6's fourth commit, 2026-09-21; the residuals lens found `c=cp; export c; $c a b`, `(c=mv); c=cp; $c a b`,
  // `c=cp; echo '$c'; $c a b`, `declare c=cp; $c a b`, `eval c=cp` then `$c a b`, `c=cp bash -c '$c a b'` and `f() { local c=cp; $c a b; }; f`
  // each running the copy in a shell while the name was unreadable to the readability rule and the head fell to the residual): every
  // plain-string value ANY assignment word of the command gives a name, in every scope and form (a plain word, a prefix assignment, an
  // operand of export, declare, typeset, local or readonly, a text an eval or a `-c` script hands over), whitespace included, shared by
  // every recursion (a name may be exported into a fresh shell). Read where a word that is one `$name` expansion is a command name or a
  // script (scriptTexts, roles 'head' and 'text'): each value is a text the name may stand for, spliced or read as a script, the script
  // road's union (a value the shell does not use costs a refusal at worst; the readability rule keeps deciding a target, where the safe
  // side is the refusal it already gives an unreadable name). A name no assignment word gives a value (a loop variable, a name read, a
  // positional parameter) stays the residual the property names.
  const candidates = ctx.candidates || new Map();
  const unreadValues = ctx.unreadValues || new Set();   // the names a value the resolver looked at and could not establish is given (round 6's fifth commit): a command name or script formed from such a name is UNRESOLVABLE
  const noteCandidate = (w) => {
    const m = w.text.match(/^([A-Za-z_][A-Za-z0-9_]*)(\+?=)([^]*)$/);
    if (!m || (w.marks && /x/.test(w.marks.slice(0, m[1].length)))) return;   // the name itself an expansion: no candidate (the NUL a substitution stands as is in the value of a word whose readings scriptTexts answers below)
    if (!candidates.has(m[1])) candidates.set(m[1], new Set());
    const set = candidates.get(m[1]);
    // a value that is not a plain string: the texts the word stands for on the script road (a resolved echo or printf that is no plain reading,
    // `x=$(printf '%s' 'cp a b')`, THE GLUED READING with the name before them), obtained through scriptTexts as every text is (THE RESOLVER'S
    // CONTRACT), each a value; a value the resolver looked at and could not establish marks the name (unreadValues); an expansion the resolver
    // never reads gives nothing (the name keeps the residual the property names)
    // THE COMPOSED VALUE (round 6's seventh commit, 2026-09-21; the residuals verifier and the body auditor: `f() { c=$1; $c a b; }; f cp` and its
    // `"$1"`, `${1}`, `local`, `declare`, `typeset`, `export`, `c=$2`, `c="$*"`, `c=$@`, `d=$1; c=$d`, `shift`, `eval "$c .."`, `bash -c "$c .."`,
    // `trap "$c" EXIT`, a global set in a call and used after, a second function reading it, and `set -- 'cp a b'; c=$1; $c` each ran the copy in
    // the shells named while the value, an expansion of a name the command gives values, gave its name nothing): a value whose expansions are
    // each a `$name`, `${name}`, `$N`, `$@` or `$*` the command gives values (candidateTexts, the same reading a command name gets) stands for each
    // text those values and the literal characters around them compose, so `c=$1` inside a called body holds the call's operand and `c=$d` what
    // d holds; a name one of whose values the resolver could not establish marks this name (unreadValues), refused where it is a command name
    // or a script
    const strip = (t) => (t.startsWith(m[1] + m[2]) ? t.slice(m[1].length + m[2].length) : t);
    const values = w.literal ? [m[3]] : (() => {
      const ts = scriptTexts(w, `\`${m[1]}${m[2]}\` value`, 'value');
      if (ts == null) { unreadValues.add(m[1]); return []; }
      if (ts.length) return ts.map(strip);
      const c = candidateTexts(w);
      if (c && c.unread) { unreadValues.add(m[1]); return []; }
      if (c) return c.texts.map(strip);
      const v = candidateTexts(w, true);   // THE VANISHED TEXT: a value whose expansions the command never gives values holds the text with them removed (`x="cp $c a b"; $x` ran the two-operand copy)
      if (v && v.unread) { unreadValues.add(m[1]); return []; }
      return v ? v.texts.map(strip) : [];
    })();
    // `+=` appends the text to the value the name holds (bash: Shell Parameters; zsh: Simple Commands and Pipelines), so each value noted so far
    // stands with the text after it, and the text alone stands too, since the name may hold nothing the command shows (round 6's fifth commit,
    // the residuals verifier: `c=c; c+=p; $c a b` copied in bash and zsh while the append was no assignment word to this reader)
    for (const value of values) {
      if (m[2] === '+=') { for (const v of [...set]) set.add(v + value); set.add(value); continue; }
      set.add(value);
    }
  };
  // the candidates are noted below, once scriptTexts exists (noteCandidate reads a value's texts through it), before the walk
  // THE SET'S OPERANDS as candidates (round 6's seventh commit, 2026-09-21; the residuals verifier and the body auditor: `set -- 'cp ../base/report.md
  // report.md'; c=$1; $c` and `set -- cp ..; c=$*; $c`/`c="$*"; eval "$c"` ran the copy in bash and dash while the value laundered through a name went
  // unread): a top-level `set` binds the positional parameters DURING the walk, after noteCandidates has run, so a `c=$1` before the walk saw no value;
  // here noteCandidates tracks the operands a plain `set` in the command gives (and a `shift` drops), seeding candidates['1'], ['@'] and ['*'] as
  // bindPositionals does in the walk, so a later `c=$N`/`c=$@`/`c=$*` noted below reads them. The union over the whole command (a `set` in a branch the
  // shell does not take seeds here too: the safe side, a refusal at worst); it touches candidates alone, never the positionals the walk binds
  const seedPositional = (ws) => {
    for (const k of [...candidates.keys()]) if (/^[0-9@*]+$/.test(k)) candidates.delete(k);
    const add = (n, t) => { if (!candidates.has(n)) candidates.set(n, new Set()); candidates.get(n).add(t); };
    ws.forEach((w, i) => { if (w && w.literal && !w.text.includes('\0')) add(String(i + 1), w.text); });
    if (ws.every((w) => w && w.literal && !w.text.includes('\0'))) { const j = ws.map((w) => w.text).join(' '); add('@', j); add('*', j); }
  };
  let seedPos;   // set on the first call (positionals is bound below): the call's operands, so a called body's `set` composes with them
  const noteCandidates = () => {
    if (seedPos === undefined) seedPos = Array.isArray(positionals) ? positionals : null;
    if (seedPos) seedPositional(seedPos);
    for (const s of segments) {
      const c0 = commandOf(s.words);
      if (c0 && !c0.wrapped && c0.name === 'set') { const ops = setOperands(c0.args); if (ops && ops.every((w) => w && w.literal && !w.text.includes('\0'))) { seedPos = ops; seedPositional(seedPos); } else if (ops) seedPos = null; }
      else if (c0 && !c0.wrapped && c0.name === 'shift' && Array.isArray(seedPos)) { const n = c0.args.length ? (c0.args[0].literal && /^[0-9]+$/.test(c0.args[0].text) ? Number(c0.args[0].text) : null) : 1; if (n == null) seedPos = null; else { seedPos = seedPos.slice(n); seedPositional(seedPos); } }
      // THE ASSIGNED DEFAULT (round 6's sixth commit): `${name:=word}` gives name each text of word; a word the resolver could not establish marks the name
      for (const pa of s.paramAssigns || []) {
        if (pa.texts == null) { unreadValues.add(pa.name); continue; }
        if (!candidates.has(pa.name)) candidates.set(pa.name, new Set());
        for (const t of pa.texts) candidates.get(pa.name).add(t);
      }
      const c = commandOf(s.words);
      if (c === null) { for (const w of s.words) noteCandidate(w); continue; }
      if (c.unknown || c.opaque || 'script' in c) continue;
      for (const w of s.words.slice(0, c.name ? s.words.length - c.args.length - 1 : s.words.length)) noteCandidate(w);   // the words before the command name: prefix assignments, a wrapper's assignment operands (`env c=cp bash -c '$c a b'`, `c=cp bash -c '..'`)
      if (c.name && (VAR_ASSIGNERS.has(c.name) || c.name === 'local')) for (const w of c.args) noteCandidate(w);
    }
  };
  // THE EXEC FEED (round 6's fourth commit): the segments of a bare `exec` with redirections alone, whose here-documents, here-strings and `<`
  // words feed every later command of this shell and of the processes it starts (`exec 3<<< 'cp a b'; . /dev/fd/3` and `exec < <(echo 'cp a
  // b'); bash` ran the text in bash and zsh while the exec segment fed nothing); shared by every recursion, since a child inherits the descriptors
  const execFeeds = ctx.execFeeds || [];
  // THE POSITIONAL VALUE (round 6's sixth commit, 2026-09-21; the body auditor and the residuals verifier: `f() { bash "$@"; }; f -c 'cp a b'`, `f
  // <(echo ..)`, `f() { bash -c "$1"; }; f 'cp a b'`, `bash -c "$*"`, `eval "$1"`, `"$@"` and `$1` as the command name, `cp -t . ..` through `"$@"`, a
  // nested call, `f() { bash <<< "$1"; }`, `eval "cp $1 $2"` and `bash -c "$1" x y` each ran the copy in every shell while THE CALLED BODY replayed a
  // FED call alone and a positional word stood as an expansion the resolver never read; `c() { shift; "$@"; }; c x cp a b` copied too): the
  // positional parameters this shell holds are the operands of the call being replayed (THE CALLED BODY's `callArgs`, for every call now) or those
  // a `set` with no option word gave (`set -- a b`, `set a b`), read in place of a whole word that is one of them (`"$@"` and `$@` each operand,
  // `"$*"` the operands joined by one blank, `$*` and an unquoted `$N` the operand split at blanks as bash and dash split it, `"$N"` the Nth whole,
  // none where the shell makes no word), through the readability rule and THE HEAD CANDIDATES for a `$N` inside a word (a digit is a name to both),
  // and through THE PARAMETER'S VALUE for a default word over a digit; a `shift` by a count not read, a `set` whose operands or option words the
  // resolver does not read, an `eval` of a text it does not read or a sourced file rebinds them to values not known, after which a positional word
  // is UNRESOLVABLE (refused where it is a command name, a script, a target or a here-string); a `set` or `shift` inside a text this shell runs in
  // place (eval's text, a sourced standard input, a head splice) rebinds them as spelled, the sub-walk's state adopted. A script handed to a fresh
  // or fed shell (`bash -c`, `bash <<EOF`) has positional parameters of its own, which the guard does not read (a `$1` there keeps the residual the
  // property names), as does the command itself before any `set` (the tool's shell hands it none).
  const UNKNOWN_POSITIONALS = 'unknown';
  let positionals = ctx.callArgs != null ? ctx.callArgs : null;   // an array of words (known), UNKNOWN_POSITIONALS (rebound to values not read), or null (not modelled)
  let positionalsWhy = ctx.positionalsWhy || null;
  const bindPositionals = (ws, why = null) => {
    for (const k of [...vars.keys()]) if (/^[0-9]+$/.test(k)) vars.delete(k);
    if (ws === UNKNOWN_POSITIONALS) {
      positionals = ws;
      positionalsWhy = why || positionalsWhy || 'an earlier command rebinds the positional parameters to values I do not read';
      for (let k = 1; k <= 9; k++) { vars.set(String(k), null); if (!unreadableWhy.has(String(k))) unreadableWhy.set(String(k), positionalsWhy); }
      return;
    }
    positionals = ws;
    positionalsWhy = null;
    const note = (n, t) => { if (!candidates.has(n)) candidates.set(n, new Set()); candidates.get(n).add(t); };
    ws.forEach((w, i) => {
      const n = String(i + 1);
      if (w.literal && !w.text.includes('\0')) { vars.set(n, w.text); note(n, w.text); }
      else { vars.set(n, null); unreadableWhy.set(n, `the positional parameter \`${n}\` holds an operand that is an expansion I do not read`); unreadValues.add(n); }
    });
    if (ws.every((w) => w.literal && !w.text.includes('\0'))) { const joined = ws.map((w) => w.text).join(' '); note('*', joined); note('@', joined); } else { unreadValues.add('*'); unreadValues.add('@'); }   // `"$*"` and `"$@"` in a here-string or an unquoted here-document body: the operands joined by one blank, read where the consumer's script names them
  };
  // a body being DEFINED (a function frame that is not running) has positional parameters of its own, the call's, not this shell's: none of the
  // above applies inside it (`set -- cp; f() { $1 a b; }; f cat` runs cat), and the call's replay reads the body with them
  const positionalsApply = () => !frames.some((f) => f.kind === 'function' && !f.running && !f.coproc);
  if (Array.isArray(positionals)) bindPositionals(positionals);
  else if (positionals === UNKNOWN_POSITIONALS) bindPositionals(positionals, positionalsWhy);
  // THE POSITIONAL LIST'S SPELLINGS (round 6's seventh commit, 2026-09-21; the residuals verifier: `f() { "${@:1}"; }; f cp a b`, `"${@:1:1}" "${@:2}"`,
  // `"${@: -3}"`, `"${@:1:$#}"`, `"${@:2}"` after `f x cp a b`, and zsh's `$argv`, `"${argv[@]}"`, `$argv[1] $argv[2] $argv[3]`, `"${(@)argv}"` and
  // `"${@[1,-1]}"` each ran the copy in the shells named while the word was an expansion the resolver never read): beside `$N`, `${N}`, `$@`, `$*`
  // and their braced forms, a whole word may be bash's and zsh's slice of the list, `${@:offset}` and `${@:offset:length}` (bash: Shell Parameter
  // Expansion, `*` alike), the offset counting from 1, a negative one (after the blank bash requires) from the end, the length a run of digits or
  // `$#`, which reaches the end; and under zsh's grammar the array `argv`, the list itself (zshparam(1)), whole (`$argv`, `${argv}`, `${argv[@]}`,
  // `${argv[*]}`, `${(@)argv}`), one element (`$argv[N]`, `${argv[N]}`) or a range (`${argv[N,M]}`, `${@[N,M]}`, `$@[N,M]`, a negative bound
  // counting from the end); an offset of 0 (bash puts `$0`, the shell's own name, at the head of that list) or a length or bound that is not a
  // run of digits is a slice the resolver does not compute: UNRESOLVABLE. Every other `${...}` form over a positional (`${1#x}`, `${1:0:2}`,
  // `${=1}`) stays the residual the property names, a `${...}` operator form the resolver does not read, as the same forms over a name are.
  // The reading: { quoted, from, to (exclusive, Infinity for the end), star (the elements joined by one blank where double-quoted), zero (a slice
  // from $0) }, or null for a word that is none of these.
  const positionalSpelling = (raw) => {
    const m = raw.match(/^("?)\$([^]*)\1$/);
    if (!m) return null;
    const quoted = m[1] === '"';
    const braced = m[2].startsWith('{') && m[2].endsWith('}');
    const t = braced ? m[2].slice(1, -1) : m[2];
    let mm;
    if ((mm = t.match(/^([1-9][0-9]*)$/))) return braced || mm[1].length === 1 ? { quoted, from: Number(mm[1]) - 1, to: Number(mm[1]), star: false } : null;   // an unbraced multi-digit `$10` is `${1}0` in bash and dash and the tenth positional in zsh: no positional here, resolveWord's THE MULTI-DIGIT POSITIONAL leaves it unread where zsh may run the line
    if (/^[@*]$/.test(t)) return { quoted, from: 0, to: Infinity, star: t === '*' };
    if (braced && (mm = t.match(/^([@*]):( ?-?[0-9]+|\$#)(?::([0-9]+|\$#|[^]*))?$/))) {
      const off = mm[2] === '$#' ? null : Number(mm[2]);
      if (off === 0) return { quoted, zero: true, star: mm[1] === '*' };
      const from = off == null ? Infinity : off > 0 ? off - 1 : { fromEnd: -off };
      const len = mm[3] == null ? Infinity : mm[3] === '$#' ? Infinity : /^[0-9]+$/.test(mm[3]) ? Number(mm[3]) : null;
      return { quoted, from, len, star: mm[1] === '*', slice: true };
    }
    if (shell == null || shell === 'zsh') {
      if (t === 'argv' || t === '(@)argv' || /^argv\[[@*]\]$/.test(t)) return { quoted, from: 0, to: Infinity, star: quoted && !/\[@\]$|^\(@\)/.test(t), argv: true };   // `"$argv"` joins as `"$*"` does; `"${argv[@]}"` and `"${(@)argv}"` keep the elements
      if ((mm = t.match(/^(?:argv|[@*])\[(-?[0-9]+)(?:,(-?[0-9]+))?\]$/))) return { quoted, range: [Number(mm[1]), mm[2] == null ? Number(mm[1]) : Number(mm[2])], star: false, argv: true };
    }
    return null;
  };
  // the words a whole positional word stands for: { words } (none where the shell makes no word), { unresolvable: why } where they are not known,
  // null where the word is no positional or the positionals are not modelled; `oneWord`: true at a place that takes one word (a here-string, a
  // `<`), 'target' at a redirection target (THE POSITIONAL TARGET below: the shells differ there), false among operands
  const positionalWords = (w, oneWord) => {
    if (positionals === null || w.literal || !w.marks || !/^x+$/.test(w.marks)) return null;
    const sp = positionalSpelling(w.raw);
    if (!sp) return null;
    if (positionals === UNKNOWN_POSITIONALS) return { unresolvable: positionalsWhy };
    const { quoted, star } = sp;
    // THE IFS RULE over a positional list (round 6's tenth commit, 2026-09-22; the round's verifiers: `set -- .. docs report.md; IFS=/; echo
    // x > "$*"` wrote ../docs/report.md in bash, zsh and dash while allowed): an unquoted `$@`/`$*` splits by IFS (the existing rule), and
    // `"$*"` joins the parameters with the FIRST character of IFS (bash: Special Parameters; dash(1); zshexpn(1)), so a named IFS the resolver
    // does not read leaves the joined name unknown too; at a redirection target dash joins even `"$@"` with that character (measured), so any
    // quoted list there is one the hook cannot read while the command names IFS. The exempt case is a quoted `"$@"` that is not a target: its
    // elements stay separate whatever IFS holds. (The `IFS=' '` and `unset IFS` twins join by whitespace, an untracked name, and are refused
    // here as the unquoted forms already were: a stated cost, the safe side of a value the resolver does not compute.)
    if (ifsNamed && (!quoted || star || oneWord === 'target')) return { unresolvable: `the command names IFS, so the ${quoted ? 'first character it joins the positional parameters with at a redirection target' : 'fields the shell cuts the positional parameters into where they are not double-quoted'} ${quoted ? 'is' : 'are'} not known` };
    if (sp.zero) return { unresolvable: `the word \`${w.raw}\` is a slice of the positional parameters from 0, which bash heads with the shell's own name, a word I do not read` };
    let picked;
    if (sp.slice) {
      if (sp.len === null) return { unresolvable: `the word \`${w.raw}\` slices the positional parameters by a length that is not a run of digits, which I do not compute` };
      const start = sp.from === Infinity ? positionals.length : typeof sp.from === 'object' ? Math.max(0, positionals.length - sp.from.fromEnd) : sp.from;
      picked = positionals.slice(start, sp.len === Infinity ? undefined : start + sp.len);
    } else if (sp.range) {
      const at = (n) => (n < 0 ? positionals.length + n : n - 1);   // zsh: 1 the first, -1 the last
      const [a, b] = [at(sp.range[0]), at(sp.range[1])];
      picked = a <= b ? positionals.slice(Math.max(0, a), Math.max(0, b + 1)) : [];
    } else picked = positionals.slice(sp.from, sp.to === Infinity ? undefined : sp.to);
    const lit = (t, q) => { const marks = (q ? 'q' : 'e').repeat(t.length); const g = !q && hasGlobChar(t, marks); return word(t, !g, w.raw, { glob: g, marks }); };
    if (picked.some((p) => !p.literal || p.text.includes('\0'))) {
      if ((quoted && !star) || oneWord === 'target') return { words: picked.map((p) => ({ ...p })) };   // each operand as the call spelled it (a `<(..)` keeps its readings); at a redirection target every element is a target of its own (THE POSITIONAL TARGET: zsh opens each, a literal one judged by name, an expansion one a target the hook cannot read; round 6's ninth commit: the unquoted form reached a name this branch never bound and the catch-all refused it as an error of the guard's own)
      return { unresolvable: 'an operand this shell holds in its positional parameters is an expansion I do not read, so the words the shell makes of them are not known' };
    }
    const texts = picked.map((p) => p.text);
    // THE POSITIONAL TARGET (round 6's ninth commit, 2026-09-22; the round's verifiers: `set -- a.md report.md; echo x > $@` wrote report.md in zsh
    // while allowed, and `$*`, `${@}`, `${*}`, `"$@"`, `${@:1}`, zsh's `${@[1,2]}` and `$argv`, every write operator, the tracked notes/ folder,
    // a closer's and an `exec`'s redirection, and `set -- 're*.md'; echo x > $1`, which bash wrote through the pattern): at a redirection
    // target zsh opens EVERY element the list stands for, each whole (no splitting, no pattern; MULTIOS, on by default), bash opens the one
    // word the list makes after splitting and pattern expansion and refuses an ambiguous redirect given several, and dash opens the elements
    // joined by one blank as one name (measured: `set -- a.md n1.md; echo x > $@` from notes/ made the file `a.md n1.md` there). So a list of
    // several elements stands for the joined name beside each element, a single unquoted element for itself with its pattern read (bash
    // expands it), and `"$*"` for the joined name; the one-word reading below stayed the whole rule before, the joined name marked quoted, so
    // neither the elements nor the pattern were judged. positionalsApply's caller (expandPositionals) records one redirection per word.
    if (oneWord === 'target') {
      if (quoted && star) return { words: [lit(texts.join(' '), true)] };
      if (texts.length <= 1) return { words: [lit(texts.join(' '), quoted)] };
      return { words: [lit(texts.join(' '), true), ...texts.map((t) => lit(t, true))] };
    }
    if (oneWord || (quoted && star)) return { words: [lit(texts.join(' '), true)] };
    if (quoted) return { words: texts.map((t) => lit(t, true)) };
    return { words: texts.flatMap((t) => t.split(/[ \t\n]+/)).filter(Boolean).map((t) => lit(t, false)) };
  };
  const expandPositionals = (seg) => {
    if (positionals === null || !positionalsApply()) return;
    const mark = (w, why) => Object.assign({ ...w }, { unresolvableReading: { raw: w.raw, why } });
    const out = [];
    for (const w of seg.words) { const r = positionalWords(w, false); if (!r) out.push(w); else if (r.words) out.push(...r.words); else out.push(mark(w, r.unresolvable)); }
    seg.words = out;
    const one = (w) => { const r = positionalWords(w, true); if (!r) return w; if (r.words) return Object.assign(r.words[0] || word('', true, w.raw, { marks: '' }), { fd: w.fd, herestring: w.herestring }); return mark(w, r.unresolvable); };
    if (seg.stdin) seg.stdin = seg.stdin.map(one);
    // THE POSITIONAL TARGET: a redirection whose target is a positional list becomes one redirection per word the list stands for at a target
    const rs = [];
    for (const r of seg.redirects) {
      const p = positionalWords(r.target, 'target');
      if (!p) rs.push(r);
      else if (p.words) { if (!p.words.length) rs.push({ ...r, target: word('', true, r.target.raw, { marks: '' }) }); for (const t of p.words) rs.push({ ...r, target: t }); }
      else rs.push({ ...r, target: mark(r.target, p.unresolvable) });
    }
    seg.redirects = rs;
  };
  // the operands of a `set` (bash: The Set Builtin; dash(1): set; zshbuiltins(1): set): the words after `--` or `-`, or every word when the first
  // is no option; null when set binds nothing (`set -x`, `set -o pipefail`, `set` alone); with an option word before them, or one the resolver did
  // not read, [null] (bound to values not known: `set -A arr ..` is zsh's array assignment and leaves them as they were, a reading the guard does
  // not make)
  const setOperands = (args) => {
    if (!args.length) return null;
    if (!args[0].literal) return [null];
    if (args[0].text === '--' || args[0].text === '-') return args.slice(1);
    if (/^[-+]/.test(args[0].text)) return args.slice(1).some((w) => !w.literal || !/^[-+]/.test(w.text)) || /^[-+][A-Za-z]*o$/.test(args[0].text) ? [null] : null;
    return args;
  };
  // THE LINE OF A SEGMENT, for the alias road's "bound on an earlier line": the top-level command counts its lines; a text the shell
  // parses AFTER the segment that hands it over has run (an eval or trap operand, a sourced standard input, a `$(...)`, a backtick, a
  // `<(...)`: round 6's third commit, 2026-09-21) takes coordinates strictly between that segment's line and the next (`lineBase` the
  // segment's own line, `lineStep` one over the text's line count plus one, nested texts dividing again), so a binding on or before the
  // outer line is seen inside the text (`alias c=cp; eval 'c a b'` copied in zsh and dash, `alias c=cp; echo $(c a b)` in zsh, and the
  // inner text's line 1 read as line 1 saw no binding before it), a binding made inside it on line L is seen on its later lines
  // (bash parses eval's text line by line) and by every later outer line, and not on the outer line itself (`eval 'alias c=cp'; c a b`
  // expands in no shell: the line was parsed whole before eval ran). A head splice stands after every binding (Infinity).
  const lineOf = (seg) => (ctx.headSplice ? Infinity : (ctx.lineBase || 0) + (ctx.lineStep || 1) * (seg && seg.start ? command.slice(0, seg.start).split('\n').length : 1));
  // a definition made inside a head splice binds at the line of the segment the splice stands for (round 6's fifth commit, 2026-09-21; the
  // residuals verifier: `alias a=alias`, then `a c=cp`, then `c a b` copied in dash and, through a here-document or a pipe, in every shell,
  // while the alias the spliced `alias c=cp` defined bound at Infinity and so stood after every later use)
  const defLineOf = (seg) => (ctx.headSplice ? (ctx.spliceLine == null ? Infinity : ctx.spliceLine) : lineOf(seg));
  // THE CALLED BODY (round 6's fifth commit): the text of each function this command defines, name -> the definition as spelled (popFunction),
  // replayed with the call's standard input where a call is fed a text the guard holds (the walk), and the names of the functions being replayed
  // on this road (fnChain: a call inside its own body is not followed again); both shared by every recursion
  const functionBodies = ctx.functionBodies || new Map();
  const functionLines = ctx.functionLines || new Map();   // name -> the line the definition stands on (THE ALIAS ROAD applies to a body as parsed there)
  const fnChain = ctx.fnChain || new Set();
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
    if (/^[0-9]+$/.test(name) && !positionalsApply()) return null;   // THE POSITIONAL VALUE: a body being defined has positionals of its own
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
          // THE IFS RULE (round 6's fourth commit): while the command names IFS, an expansion not inside one pair of double quotes splits at the
          // characters of IFS, a rule the resolver does not compute (`x=a:report.md; IFS=:; tee $x` opened report.md in bash and dash, `x=../base/
          // report.md:report.md; IFS=:; cp $x` copied, while the value was judged whole), so the name is not read there and the word is one the
          // hook cannot read (a target refuses, a copying writer's one operand refuses as split, a command name refuses through scriptTexts)
          if (ifsNamed && !dqSingleField(w.raw)) { if (!named) named = { kind: 'ifsNamed', name: m[1] || m[2], text: `the command names IFS, so the fields the shell cuts \`$${m[1] || m[2]}\` into where it is not double-quoted are not the value as stored` }; ok = false; break; }
          // THE MULTI-DIGIT POSITIONAL (round 6's tenth commit, 2026-09-22; the round's verifiers: `set -- 1 2 3 4 5 6 7 8 9 report.md;
          // echo x > $10` wrote report.md in zsh while allowed): an unbraced `$` before a run of two or more digits is the FIRST positional
          // and the remaining digits as literal text in bash and dash (`$10` is `${1}0`) but the tenth (or later) positional in zsh
          // (zshexpn(1): a multi-digit number after `$` is one positional), so where zsh may run the line the parameter the shell reads is
          // not known; the braced `${10}` is the tenth in every shell and reads as before
          if (!m[1] && /^[0-9]$/.test(m[2]) && k + m[0].length === run.length && /^[0-9]$/.test(T[end] || '') && (shell == null || shell === 'zsh')) {
            if (!named) named = { kind: 'namedExpansion', name: m[2], text: `\`$${m[2]}${T[end]}\` is the ${m[2]} positional parameter and a literal digit in bash and dash but a single multi-digit positional in zsh, so the parameter the shell reads is not known` };
            ok = false; break;
          }
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
    if (!changed) return named ? { ...w, why: named } : w;   // a spread keeps the word's readings (the third fix-up)
    const hasX = marks.includes('x') || text.includes('\0');
    const g = !hasX && hasGlobChar(text, marks);
    const resolved = word(text, !hasX && !g, w.raw, { glob: g, marks, at: w.at, numeric: hasX && numericRunsOnly(text, marks) && !hasGlobChar(text, marks), why: named });
    if (w.readings) resolved.readings = w.readings;   // the texts a `-c` operand or a here-string can stand for survive the resolution (the third fix-up)
    if (w.readingParams) resolved.readingParams = w.readingParams;   // and THE DEFAULT WORD's names (round 6's fifth commit)
    if (w.unresolvableReading) resolved.unresolvableReading = w.unresolvableReading;   // and so does the resolver's mark (THE RESOLVER'S CONTRACT)
    if (w.mayReadStdin) resolved.mayReadStdin = w.mayReadStdin;   // and THE FED SUBSTITUTION's mark
    return resolved;
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
    // the name of a function definition (`f() {`, `{ f() {`, `! f() {`: a word list before an EMPTY pair of parentheses) is no call of it and
    // writes nothing (round 6's sixth commit: THE CALLED BODY's replay read the definition's name as a call of the function it defines, which
    // poisoned every name for the body, so `n=x; f() { cp a $n; }; f` refused `$n` as unreadable while the definition's own read had resolved it)
    if (seg.op === '(' && segments[idx + 1] && segments[idx + 1].paren === '(' && segments[idx + 2] && segments[idx + 2].paren === ')' && !(compoundHeadOf(seg.words) != null && Object.hasOwn(BODY_CLOSER, compoundHeadOf(seg.words)))) return;
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
    // THE ALIAS ROAD's bound paths: a copy or a link this command makes (cp, install, ln, link, mv) binds the destination path to the
    // source's text, so a later command named by that path is read as the source (`cp /usr/bin/cp ../scratch/c2; ../scratch/c2 a b` and
    // `ln -s /usr/bin/cp ../scratch/c2 && ../scratch/c2 a b` copied in every shell, measured); a source the resolver cannot read binds null
    if (name === 'cp' || name === 'install' || name === 'ln' || name === 'mv' || name === 'link') {
      const parseOps = (a) => (name === 'link' ? { operands: a.filter((x) => !(x.text.startsWith('-') && x.text.length > 1)) } : parseCopyOptions(a, name));
      const bindUnder = (parsed) => {
        if (parsed.unknown || parsed.installDir) return;
        const ops = parsed.operands || [];
        const srcText = (w) => (w && w.literal ? w.text : null);
        if (parsed.targetDir) { if (parsed.targetDir.literal) for (const src of ops) { const d = literalPath(path.join(parsed.targetDir.text, path.basename(src.text)), cwd); if (d) bound.set(d, srcText(src)); } }
        else if (ops.length === 2) { const d = abs(ops[1]); if (d) bound.set(d, srcText(ops[0])); }
        else if (ops.length > 2) { const dst = ops[ops.length - 1]; if (dst.literal) for (const src of ops.slice(0, -1)) { const d = literalPath(path.join(dst.text, path.basename(src.text)), cwd); if (d) bound.set(d, srcText(src)); } }
      };
      bindUnder(parseOps(args));
      // THE VANISHING OPERAND: the path is bound under every operand list the shell may hand the writer (`cp $c /usr/bin/cp ../scratch/c2` binds c2 to
      // cp's text once `$c` is dropped); past the cap every literal operand is a path this command may have changed (markMutated, below)
      for (const { kept } of vanishVariants(args, !!cwd) || []) bindUnder(parseOps(kept));
    }
    // THE VANISHING OPERAND (round 6's eighth commit): a rename, a hard link or a linking copy with an operand the shell may make no word of leaves which
    // operand is the source and which the destination unplaced, as an unknown option does (rule (f)), so every literal candidate is a path this command
    // may have changed
    if ((name === 'mv' || name === 'ln' || name === 'cp') && args.some((a) => !(a.text.startsWith('-') && a.text.length > 1) && mayVanish(a, !!cwd))) {
      const symbolic = name === 'ln' && args.some((a) => a.literal && (a.text === '--symbolic' || (/^-[^-]/.test(a.text) && a.text.includes('s'))));   // a symbolic ln is class H under each list (recordSymlink over the variants, in the writer's case)
      const linky = name === 'mv' || (name === 'ln' && !symbolic) || (name === 'cp' && args.some((a) => a.literal && ((/^-[^-]/.test(a.text) && (a.text.includes('l') || a.text.includes('s'))) || a.text === '--link' || a.text === '--symbolic-link')));
      if (linky) { markAllCandidates(name === 'cp' ? 'cp -l' : name); return; }
    }
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
  // The text appended to every write's `how` while the walk stands in a construct's other reading (round 5's fifth addendum):
  // the `via` a recursion was entered with (a `(( ))` body dash runs, a `$((` bash and zsh read as `$( (`, a substitution in
  // an arithmetic body) and the piece text of a further command dash reads after a `&&` or `||` inside a `[[ ... ]]`, so the
  // refusal names dash and the construct wherever the target was found.
  let viaSeg = '';
  const viaOf = () => (ctx.via || '') + viaSeg;
  const pieceVia = (p) => ` as a further command dash reads after the \`${p.op}\` inside a \`${p.construct}\` (bash and zsh compare there and run nothing)`;
  // A write target the hook cannot read (the header). A process substitution (`>(cmd)`) is a pipe and
  // never a file, so it is dropped, not recorded.
  const cannotRead = (w, how, why = null) => {
    if (/^[<>]\(/.test(w.text) && !(why && why.kind === 'unresolvableReading')) return;   // one whose reading the resolver could not establish, or whose command may read a text this command feeds, IS recorded (round 6's fourth commit: `echo 'cp a b' | bash <(cat)` ran the piped text in bash while the mark was dropped with the word)
    const here = unknownDir ? null : dir;
    unresolved.push({
      raw: w.raw, how: how + viaOf(), dir: here, at: w.at ? literalPath(w.at, here) : null, numeric: w.numeric ? w.text : null,
      text: w.text, marks: w.marks, why,
    });
  };
  const add = (w, how) => {
    try { addInner(w, how); }
    catch (e) { if (isUnknownPath(e) && !(e.why && e.why.how)) e.why = { ...(e.why || {}), how: how + viaOf(), raw: w && w.raw ? w.raw : (w && w.text) || 'the path' }; throw e; }
  };
  // THE ONE PLACE in extract where a script-consuming site obtains the texts a word stands for (THE RESOLVER'S CONTRACT, stated at
  // the reading functions above extract). `role` 'text': the word's own text is the script (a `-c` operand, an interpreter's inline
  // code); 'file': the word names what the script is read from (a here-string or a `<` into the standard input, a process
  // substitution as the script operand, a piped producer's printed text), so only its readings count; 'head': the command's name,
  // where a word the resolver could not establish is refused, a word with readings yields them (THE HEAD SPLICE reads the segment
  // again with each in the name's place: round 6's second commit, after `${x:-cp} ../base/report.md report.md` ran the copy in every
  // shell while the reading `cp` went unused in head position) and anything else is the command the walk reads on its own. A word the resolver could not establish is a target the hook cannot read (cannotRead: refused while a project is in
  // play, with the reason) and yields no text, so no site can hand such a script to the shell as the residual pass; a word with
  // readings yields them; a literal word its text (role 'text'); anything else is a script the guard cannot see, the residual
  // decision 47 names, marked opaque.
  // THE HEAD CANDIDATES' template (round 6's fifth commit, 2026-09-21; the residuals verifier: `a=cp; b='../base/report.md report.md'; eval "$a
  // $b"`, `bash -c "$a $b"`, `eval "${a} ${b}"` and `sh -c "$a $b"` each ran the copy in every shell while a word holding two names was no
  // candidate, the one-name rule before it): a word whose expansions are each a `$name` or `${name}` the command gives a value (every run of
  // expansion marks a sequence of such spellings; a value with no blank the readability rule resolved already) stands for each text the
  // values and the literal characters around them compose, the product capped at 64; null when an expansion of another kind stands in the
  // word, or a name has no value, and the word keeps what it had before
  const CANDIDATE_TOKEN = /\$\{([A-Za-z_][A-Za-z0-9_]*|[0-9]+|[@*])\}|\$([A-Za-z_][A-Za-z0-9_]*|[0-9@*])/y;   // a digit is a name to the candidates too (THE POSITIONAL VALUE, round 6's sixth commit): `$1` one digit unbraced (`$10` is `${1}0` in bash and dash but the tenth positional in zsh; resolveWord leaves the multi-digit form unread before it reaches here), `${10}` any run braced; `$@` and `$*` hold the operands joined by one blank, the text a here-string or an unquoted here-document body hands a consumer (`f() { bash <<< "$*"; }` fed the call's operands)
  // THE VANISHED TEXT (round 6's ninth commit, 2026-09-22; the round's verifiers: `eval cp $c ../base/report.md report.md` ran the two-operand
  // copy in bash, zsh and dash while allowed, and `eval "cp $c a b"`, `eval cp "$c" a b` (eval joins its operands with one blank and parses the
  // join, so a quoted empty operand vanishes there too), `eval cp $(true) a b`, `eval cp "$@" a b`, mv, install and `ln -f` the same, `trap "cp
  // $c a b" EXIT`, `bash -c "cp $c a b"` and through sh, dash, zsh, `$1`, `$(true)`, `${c}`, an escaped spelling, behind nice and command, in a
  // subshell, a group, an if and after `&&`, `flock -c`, zsh's `emulate -c`, python's inline code, and `x="cp $c a b"` run as `$x`, `eval $x`,
  // `sh -c "$x"`, `bash <<< "$x"`, through declare and export; where the single-quoted spellings, the default words and a value the command gives
  // c were refused): an expansion the command never gives a value (an unset name, a positional parameter beyond the operands, `$@` and `$*`
  // with none, a substitution outside the output model, an operator form the resolver does not read) MAY be empty, and the shell drops the
  // empty text before the script is handed over (bash: Word Splitting; dash(1): Word Expansions; zshexpn(1)), so the text with every such
  // expansion removed is one script the shell may run: the reading THE VANISHING OPERAND gives a copying writer's operand, given here to a
  // script word and an assignment's value (`vanish`), the other readings of the expansion staying the residual the property names (the word
  // is marked opaque all the same). Never empty: an arithmetic expansion, a length, `$?`, `$$`, `$#`, `$0` and a process substitution (a path),
  // so a run holding one has no vanished reading.
  const NEVER_EMPTY_RUN = /\$\(\(|\$\{#|\$[?$#0](?![A-Za-z0-9_])|\$\{[?$#0]\}|(?:^|[^$])[<>=]\(/;
  const candidateTexts = (w, vanish = false) => {
    if (w.literal || !w.marks || !w.marks.includes('x')) return null;   // no expansion in the word (a glob-shaped head such as `[[`): nothing to stand for
    if (w.text.includes('\0') && (!vanish || NEVER_EMPTY_RUN.test(w.raw))) return null;   // a substitution the resolver did not read stands as a NUL: no candidate; THE VANISHED TEXT reads it as empty unless the spelling holds a never-empty form
    let texts = [''];
    for (let i = 0; i < w.text.length;) {
      let j = i;
      while (j < w.text.length && w.marks[j] === w.marks[i]) j++;
      const run = w.text.slice(i, j);
      if (w.marks[i] !== 'x') { texts = texts.map((t) => t + run); i = j; continue; }
      const names = [];
      let tokens = true;
      CANDIDATE_TOKEN.lastIndex = 0;
      while (CANDIDATE_TOKEN.lastIndex < run.length) { const m = CANDIDATE_TOKEN.exec(run); if (!m) { tokens = false; break; } names.push(m[1] || m[2]); }
      if (!tokens) { if (!vanish || NEVER_EMPTY_RUN.test(run)) return null; i = j; continue; }   // THE VANISHED TEXT: a run the token grammar does not read (a substitution, an operator form) that may be empty stands for nothing
      for (const n of names) {
        if (/^[0-9@*]+$/.test(n) && !positionalsApply()) return null;
        if (/^[0-9@*]+$/.test(n) && positionals === UNKNOWN_POSITIONALS) return { unread: n, why: positionalsWhy };
        if (unreadValues.has(n)) return { unread: n };
        if (!candidates.has(n)) { if (!vanish) return null; continue; }   // THE VANISHED TEXT: a name the command gives no value may be empty
        texts = texts.flatMap((t) => [...candidates.get(n)].map((v) => t + v));
        if (texts.length > 64) return null;
      }
      i = j;
    }
    return { texts };
  };
  headTextsOf = (w) => { const c = candidateTexts(w); return c && c.texts ? c.texts : null; };   // THE SPLICED PRINTER reads THE HEAD CANDIDATES; a name whose value the resolver could not establish answers nothing here (scriptTexts refuses it at the head)
  const scriptTexts = (w, how, role = 'text') => {
    if (!w) return [];
    const optionWord = role === 'option';   // THE SHELL'S OPTION WORD: a text role whose empty answer is a refusal (the caller records the word), so THE VANISHED TEXT, one reading beside the residual, does not stand in for it (`a=(-c); bash "${a[@]}" 'cp a b'` would read as a script file and pass)
    if (optionWord) role = 'text';
    if (role === 'value' && (w.unresolvableReading || w.readingParams)) return null;   // THE HEAD CANDIDATES' value road: an assignment value the resolver looked at and could not establish, or one that depends on a parameter's value (`y=${c:-x}`, read before the walk knows any value), marks its name (noteCandidate, unreadValues) and refuses where the name is used as a command name or a script, never here (`OUT=${OUT:-out}` alone is no write)
    if (w.unresolvableReading) { cannotRead(w, how, { kind: 'unresolvableReading', spelling: w.unresolvableReading.raw, text: w.unresolvableReading.why }); return []; }
    if (w.why && w.why.kind === 'ifsNamed') { cannotRead(w, how, w.why); return []; }   // THE IFS RULE: a `$name` the shell splits by a rule the resolver does not compute is a text it cannot read here
    // THE FED SUBSTITUTION (round 6's fourth commit, 2026-09-21; the body auditor: `echo 'cp a b' | bash -c "$(head -1)"`, `$(sed '')`, `$(tr a a)`,
    // `$(awk 1)`, `$(dd)`, `$(</dev/stdin)`, `$(command cat)`, `$(busybox cat)` and `bash <(cat)` each ran the piped text in bash and dash while
    // the rule that refused `$(cat)` was keyed on the spelling `cat`): a `$(...)`, a backtick or a `<(...)` whose list the resolver does not read
    // runs a command outside the output model, which MAY read the standard input, so where this command feeds that input with a text the
    // guard read (a pipe from a producer it reads, a closer's redirection, an exec feed, the caller's) the text produced may be that text, and
    // the word is UNRESOLVABLE; with nothing fed, the text is not in the command and the word keeps the residual the property names
    if (role !== 'value' && w.mayReadStdin && fedTexts(walkIdx).length) { cannotRead(w, how, { kind: 'unresolvableReading', spelling: w.mayReadStdin, text: 'the substitution runs a command outside the output model (no echo or printf), which may read the standard input, and this command feeds that input with a text I read here, so the text produced may be that text' }); return []; }   // role 'value' is read before the walk, where nothing is fed yet (a value built from a fed cat stays the residual, class 4)
    if (w.readings) {
      if (!w.readingParams) return w.readings;
      // THE PARAMETER'S VALUE (round 6's fifth commit, 2026-09-21; lex's defaultReading says why): the readings of a default word depend on
      // the value of a name the command may set, so the value the readability rule holds for it (a plain assignment performed by now) and
      // every value THE HEAD CANDIDATES hold for it join the texts; a name a construct the resolver does not follow wrote, or one this
      // command never sets (its value is the shell's own, which the guard does not read), makes the word UNRESOLVABLE, refused as a text
      // the hook cannot read, never the word alone
      const texts = new Set(w.readings);
      for (const p of w.readingParams) {
        const { name, before = '', after = '', plus, op } = p;
        if (plus) {
          // THE ALTERNATE VALUE (round 6's tenth commit): `${name:+word}`/`${name+word}` is the word (already in the readings) when the
          // name is set (non-empty, with the colon) and the word dropped otherwise; add the dropped form unless the name is known set,
          // so the empty text the shell may hand over reaches the judgment (a two-operand copy the three-operand reading hid)
          const setKnown = vars.has(name) && vars.get(name) != null && (!/:/.test(op || '') || vars.get(name) !== '');
          const candKnown = candidates.has(name) && [...candidates.get(name)].length > 0 && (!/:/.test(op || '') || [...candidates.get(name)].every((v) => v !== ''));
          const posKnown = /^[0-9@*]+$/.test(name) && positionalsApply() && positionals !== UNKNOWN_POSITIONALS && (name === '@' || name === '*' ? positionals.length > 0 : positionals.length >= Number(name));
          if (!(setKnown || candKnown || posKnown)) texts.add(before + after);
          continue;
        }
        const stands = `the word stands for the value of \`${name}\` when it is set, and`;
        if (varsPoisoned) { cannotRead(w, how, { kind: 'unresolvableReading', spelling: w.raw, text: `${stands} ${poisonWhy || 'an earlier construct may assign any name'}, so that value is not known` }); return []; }
        if (vars.has(name) && vars.get(name) === null) { cannotRead(w, how, { kind: 'unresolvableReading', spelling: w.raw, text: `${stands} ${unreadableWhy.get(name) || `the command writes \`${name}\` through a construct I do not follow`}, so that value is not known` }); return []; }
        if (unreadValues.has(name)) { cannotRead(w, how, { kind: 'unresolvableReading', spelling: w.raw, text: `${stands} a value this command gives \`${name}\` comes from a text I looked at and could not establish, so that value is not known` }); return []; }
        if (!vars.has(name) && !candidates.has(name)) { cannotRead(w, how, { kind: 'unresolvableReading', spelling: w.raw, text: `${stands} this command does not set \`${name}\`, so its value is the shell's own, which I do not read` }); return []; }
        if (vars.has(name)) texts.add(before + vars.get(name) + after);   // the value stands where the expansion stands, the literal text around it kept (`eval "${c:-cat} a b"` with c=cp runs `cp a b`)
        for (const v of candidates.get(name) || []) texts.add(before + v + after);
      }
      return [...texts];
    }
    if (role === 'value') return [];   // an assignment word with no reading of its own gives its name no text (noteCandidate: the readability rule reads the plain value)
    if (role === 'head' || role === 'text' || w.herestring) {
      // THE HEAD CANDIDATES: a word whose expansions are `$name` spellings the readability rule did not resolve stands for each text the
      // command's values compose (candidateTexts); a name one of whose values the resolver looked at and could not establish (`x=$(printf '%q'
      // ..)`, unreadValues) makes the word UNRESOLVABLE; a command name splits at every blank, a newline among them (bash and dash), so a
      // value's newline is a blank in head position (round 6's fifth commit: `c='cp<newline>a b'; $c` copied in bash and dash while the text
      // was read as two commands)
      const c = candidateTexts(w);
      if (c && c.unread) { cannotRead(w, how, { kind: 'unresolvableReading', spelling: w.raw, text: c.why || `a value this command gives \`${c.unread}\` comes from a text I looked at and could not establish, so what the word stands for is not known` }); return []; }
      if (c) return role === 'head' ? c.texts.map((t) => t.replace(/\n+/g, ' ')) : c.texts;
    }
    if (role === 'head') return [];
    if ((role === 'text' || w.herestring) && w.literal && !w.text.includes('\0')) return [w.text];   // a here-string word resolved to a literal text is the script fed (THE POSITIONAL VALUE: `f() { bash <<< "$1"; }`)
    // THE UNREAD SCRIPT WORD (round 6's sixth commit, 2026-09-21; the body auditor: `bash -c cp\ ../base/*.md\ report.md`, `[r]eport.md`, `?eport.md`,
    // `re*.md`, `report.m?`, the same through `sh -c`, `dash -c` and `eval`, and python's and node's inline words holding a `*`, each ran in bash and
    // dash while the word was neither literal nor an expansion, so no text was read and nothing was refused): a script word that is no expansion and
    // still not literal carries a glob character, a brace list past the cap or a quoting whose reading depends on the shell, which the shell expands
    // before the text is handed over, so it is a text the resolver cannot establish: refused, never the residual pass
    if ((role === 'text' || w.herestring) && !w.literal && !(w.marks && w.marks.includes('x')) && !w.text.includes('\0')) { cannotRead(w, how, { kind: 'unresolvableReading', spelling: w.raw, text: 'the word carries a glob character, a brace list or a quoting whose reading depends on the shell, which the shell expands before the text is handed over, so the script the shell reads is not the text spelled' }); return []; }
    // THE VANISHED TEXT (candidateTexts says why): a script word whose expansions the command never gives values stands for the text with
    // them removed, one script the shell may run, beside the residual (the word stays opaque: its other values are not read)
    if ((role === 'text' || w.herestring) && !optionWord && procsubOf(w) == null) {
      const v = candidateTexts(w, true);
      if (v && v.unread) { cannotRead(w, how, { kind: 'unresolvableReading', spelling: w.raw, text: v.why || `a value this command gives \`${v.unread}\` comes from a text I looked at and could not establish, so what the word stands for is not known` }); return []; }
      if (v && v.texts.length) { sawOpaqueCommand = true; vanishedRead = true; return v.texts; }
    }
    if (role === 'text' || w.herestring || procsubOf(w) != null) sawOpaqueCommand = true;
    return [];
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
      cannotRead(w, how, m ? mutatedWhy(m) : (w.why || null));   // the non-literal rule: a word the resolver looked at and could not establish is refused here as any expansion is (THE RESOLVER'S CONTRACT, the text road)
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
    targets.push({ path: p.path, how: how + viaOf() });
  };
  let sawOpaqueCommand = false;
  let vanishedRead = false;   // THE VANISHED TEXT: scriptTexts answered a text with an expansion the command never gives a value removed (the eval case reads it: such a text may rebind the positional parameters)
  // THE VALUED NAMES (round 6's fourth commit): the value of a SCRIPT_VALUED_NAMES assignment is a script of this shell, read through scriptTexts,
  // which since the tenth commit (THE VANISHED TEXT on this road; the round's verifiers: `PS4="\$(cp $c ../base/report.md report.md)"; set -x; true`
  // and the `$(true)` twin ran the copy in bash while the value held a live expansion the literal guard skipped) reads the value with the
  // expansions the command never gives a value removed, the shell dropping them before it prints or traces the prompt; a value that is only a
  // command substitution the resolver did not read stands for nothing (the substitution is read where it runs, at assignment). The value of a
  // STARTUP_FILE_NAMES assignment that is a `<(..)` the resolver reads is that text (the word's readings carry the name and `=` before the text,
  // THE GLUED READING in lex), read whether or not the shell is interactive (bash reads BASH_ENV when it is not, ENV in POSIX mode when it is;
  // dash reads ENV when interactive: the safe side)
  const readValuedWords = (words) => {
    for (const w of words) {
      const m = w.text.match(/^([A-Za-z_][A-Za-z0-9_]*)=/);
      if (!m || (w.marks && /x/.test(w.marks.slice(0, m[1].length)))) continue;
      if (SCRIPT_VALUED_NAMES.has(m[1])) { const v = sliceWord(w, m[0].length); for (const t of scriptTexts(v, `\`${m[1]}\` value`)) recurse(t, shell, false, ` through \`${m[1]}\``); }
      if (STARTUP_FILE_NAMES.has(m[1])) for (const t of scriptTexts(w, `\`${m[1]}\` file`, 'file')) recurse(t.startsWith(m[0]) ? t.slice(m[0].length) : t, shell, false, ` through \`${m[1]}\``);
    }
  };
  // A script run by `sh` (a `$(...)`, a heredoc-fed shell, a `-c` operand) is read as that shell reads it; a
  // `$(...)` in this command runs in this command's shell, so it inherits `shell`, and the directory state.
  // `opts` (round 6's fifth commit): `adopt`, the text runs in THIS shell (eval, a sourced standard input or process substitution, a head
  // splice, emulate's and mapfile's texts), so a cd inside it moves the shell for the rest of this command (THE MOVED SHELL); `trapMove`, the
  // text is a trap action, which runs when the trap fires (before every command under DEBUG, at exit under EXIT), so a cd inside it leaves the
  // directory unknown from here; `runFunction`, `callArgs`, `fnChain`: THE CALLED BODY's replay of a function definition fed a text
  // THE WRITTEN PROCESS SUBSTITUTION (round 6's ninth commit, 2026-09-22; lex's endSegment says why): the commands of this segment's
  // substitutions, each read as any `$(...)` of the command; a `>(cmd)` a write redirection of this command feeds is read with the text
  // the lexer placed beside it as cmd's standard input (procsubFeeds: the printed text, or an UNRESOLVABLE reading its stdin consumers
  // refuse), while one fed by no reading the model makes keeps what a substitution always had (this command's own standard input, the
  // safe side for a passthrough such as `tee`)
  const recurseSubs = (seg) => {
    for (const inner of seg.subs) {
      const feed = (seg.procsubFeeds || []).find((f) => f.inner === inner && f.printed);
      if (feed) recurse(inner, shell, false, ' through the process substitution this command writes into', [feed.printed]);
      else recurse(inner);
    }
  };
  const recurse = (text, sh = shell, fresh = sh !== shell, via = '', stdin = null, chain = aliasChain, spliced = false, opts = {}) => {
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
      ifsNamed, candidates, unreadValues, execFeeds,   // THE IFS RULE, THE HEAD CANDIDATES and THE EXEC FEED hold in every text this command hands over, a fresh shell's included (round 6's fourth commit)
      aliases: fresh ? new Map() : aliases, hashes: fresh ? new Map() : hashes, aliasState: fresh ? { unread: null } : aliasState, bound, aliasChain: chain, headSplice: spliced,   // THE ALIAS ROAD: a fresh shell starts with no alias or hash; the paths made are on the filesystem for every shell
      spliceLine: spliced ? defLineOf(walkIdx >= 0 ? segments[walkIdx] : null) : undefined,   // a definition inside the splice binds at the spliced segment's line (defLineOf)
      functionBodies, functionLines, fnChain: opts.fnChain || fnChain, runFunction: opts.runFunction || null,   // THE CALLED BODY
      callArgs: opts.callArgs !== undefined ? opts.callArgs : (spliced || opts.adopt ? positionals : null), positionalsWhy: opts.callArgs !== undefined ? null : positionalsWhy,   // THE POSITIONAL VALUE: a text this shell runs in place holds this shell's positional parameters; a fresh or fed shell has its own, which the guard does not read
      lineBase: opts.lineBase !== undefined ? opts.lineBase : lineOf(walkIdx >= 0 ? segments[walkIdx] : null), lineStep: (ctx.lineStep || 1) / (String(text).split('\n').length + 1),   // the inner text's lines lie between this segment's line and the next (lineOf)
      vars: fresh ? new Map(homeValue) : new Map(vars), unreadableWhy: fresh ? new Map() : new Map(unreadableWhy), refTargets: fresh ? new Set() : new Set(refTargets), readonlyNames: fresh ? new Set() : new Set(readonlyNames), oldDir, varsPoisoned: fresh ? false : varsPoisoned, poisonWhy: fresh ? null : poisonWhy, definedFunctions,
      via: viaOf() + via,
      // THE INHERITED STDIN (the third fix-up): a `-c` script, a `$(...)` and a script the shell reads from a file run with this
      // command's standard input, so a command inside them reading its script from stdin with nothing of its own feeding it reads
      // what this command reads (`echo 'cp a b' | bash -c 'bash'`, `| sh -c sh`, `| bash -c 'exec bash'`, `| bash -c 'bash -s'` and
      // `| bash -c 'x=$(bash)'` copied in bash, zsh and dash, measured; before, the inner script was read alone and its bash had no
      // producer); a script fed on stdin itself passes nothing on (its shell has consumed the input).
      stdin: stdin != null ? stdin : (walkIdx >= 0 ? stdinBodies(walkIdx) : inheritedStdin),
    });
    targets.push(...(opts.runFunction ? sub.targets.filter((t) => !targets.some((x) => x.path === t.path)) : sub.targets));   // a replayed body's literal writes were judged at the definition already: each path once
    unresolved.push(...sub.unresolved);
    if (sub.opaque) sawOpaqueCommand = true;
    // THE MOVED SHELL (round 6's fifth commit, 2026-09-21; the residuals verifier: `eval 'cd ../notes'; cp ../base/report.md n1.md` and the same
    // through `eval "cd $d"`, `${d:-../notes}`, `pushd`, a sourced standard input, here-string or `<(..)`, an alias of cd or one whose body is a
    // cd, a candidate head `$c` with c=cd, with the copy through cp, mv, tee, a `>`, sed -i, python or a fresh `bash -c`, and inside a function,
    // each landed on the tracked notes/ in the shells named while the later relative target was judged against the directory before the eval;
    // `trap 'cd ../notes' DEBUG; cp ..` moved bash and zsh before the cp): a text this shell ran in place moves it exactly as a top-level cd
    // does, the sub-walk's directory state adopted (known or unknown, with the construct that made it so), the move recorded on the frames
    // around it and on a function body it stands in; a trap action that moves leaves the directory unknown, since when it fires is not known
    if (sub.moved && opts.adopt) { dir = sub.dir; unknownDir = sub.unknownDir; unknownWhy = sub.unknownWhy; oldDir = sub.oldDir; movedHere(); markFunctionBody(); }
    if (opts.adopt && opts.callArgs === undefined && sub.positionals !== undefined && sub.positionals !== positionals) bindPositionals(sub.positionals, sub.positionalsWhy);   // THE POSITIONAL VALUE: a `set` or `shift` inside a text this shell ran in place rebinds this shell's positional parameters (`eval 'set -- cp'; "$@" a b`)
    else if (sub.moved && opts.trapMove) { setUnknown('an earlier `trap` action moves the shell (its cd runs when the trap fires, before a later command under DEBUG or at exit), so where the shell is when the command runs is not known'); movedHere(); markFunctionBody(); }
  };
  // What a command at segment `idx` reads on stdin, as text the hook holds: its own heredocs and
  // here-strings, those of the commands piped into it (cat <<EOF | python3 -), and THE PIPED SCRIPT (round 5's fifth addendum,
  // second fix-up, 2026-09-20; the fix-up's verifiers found `echo 'cp ../base/report.md report.md' | bash`, `echo 'echo x >
  // report.md' | sh`, `echo '[[ x > report.md ]]' | dash` and `printf '%s\\n' '[[ a ]]>report.md' | bash` from docs/, notes/ and
  // the project root allowed while bash, zsh and dash wrote, a form present since the guard's first commit: the heredoc-fed shell
  // and the here-string were read, a pipe from echo or printf was neither read nor named): when a pipeline's last command is a
  // shell of SHELLS reading its script from stdin (no `-c`, no script operand: `bash`, `bash -s`, `sh -`, dash) and the command
  // piped into it is an echo or a printf, the words echo or printf would print are the script, read as the here-string form
  // already is, under the grammar the shell named uses (dash's for `sh` and `dash`, TEST_ARITH_SHELLS), each word as the lexer
  // read it: a quoted script is literal, and an expansion in it keeps its spelling and takes the non-literal rules, as a
  // here-string's does (a value the command set to a plain string resolves first, B2). A producer that is anything else (a `cat
  // f`, a `"$s"` whose value the guard did not read, a function, a subshell, a `tee`, a `{ }` group) prints what the guard cannot
  // see, and its script passes unread: THE RESIDUAL decision 47 and the header name beside the heredoc-fed forms. The producer's
  // words were resolved when its own segment was judged (the pipeline's segments are walked in order).
  // THE CONSUMER'S STDIN (round 5's fifth addendum, third fix-up, 2026-09-20; the second fix-up's verifiers found `echo 'cp
  // ../base/report.md report.md' | (bash)`, `| if true; then bash; fi`, `| bash /dev/stdin`, `| bash /dev/fd/0`, `bash <(echo '..')`,
  // `bash < <(echo '..')`, `bash -s < <(echo '..')`, `| bash -c 'bash'`, `| sh -c sh`, `| bash -c 'exec bash'` and `| bash -c 'bash
  // -s'` from docs/ allowed while bash, zsh and dash copied, `| { bash; }` refused by accident, the brace sharing its segment). THE
  // RULE: a compound command's standard input is the pipeline's, and every command inside it (a subshell, a `{ }` group, an if, a
  // loop, a case body, at any depth) that reads its script from stdin reads what was piped into the compound (the frame the
  // compound opened after the `|` records the producer, `stdinFrom`, and producerAt reads it through the frames; a function body
  // defined there is not run and reads nothing; a `read` or another consumer before the shell inside may have drained the input,
  // `| while read -r l; do bash; done` and `| bash -c 'cat; bash'` write nothing, a priced cost); a `<` into the standard input
  // feeds the command what it names, and zsh's multios feeds the pipe's text too (`echo 'cp a b' | bash </dev/null` copied in zsh
  // and not in bash or dash, measured), so both are read (a `<` on another descriptor, `bash 3</dev/null`, is not the standard
  // input, and the pipe alone is read; all three copied); the text such a `<` names is read when it is a process substitution whose
  // command is a literal echo or printf (literalOutput), as a script operand that is one is (`bash <(echo '..')`, the SHELLS branch);
  // and a script operand that names the standard input (STDIN_NAMES, shellScript) reads it. What a command at segment `idx` reads on
  // stdin, as text the hook holds, is then: its own heredocs and here-strings; the text a `<` into its standard input names; the
  // heredocs of the commands piped into it or into the compound around it (`cat <<EOF | python3 -`, `cat <<EOF | (bash)`); THE
  // PIPED SCRIPT below; and, when nothing of its own or of a producer feeds it, the stdin its caller passed (THE INHERITED STDIN,
  // recurse).
  const producerAt = (idx) => {
    if (idx > 0 && segments[idx - 1].op === '|') return idx - 1;
    for (let j = frames.length - 1; j >= 0; j--) {
      if (frames[j].kind === 'function' && !frames[j].coproc && !frames[j].running) return null;   // a definition: its body runs later, with a stdin of its own (a body being replayed for a fed call reads the call's: THE CALLED BODY)
      if (frames[j].stdinFrom != null) return frames[j].stdinFrom;
    }
    return null;
  };
  const pipedFrom = () => (walkIdx > 0 && segments[walkIdx - 1].op === '|' ? walkIdx - 1 : null);   // the producer piped into the compound the walk is opening
  // THE CLOSER'S STDIN (the third fix-up; found while pinning the compound rows: `(bash) <<'EOF'` with the copy in the body from
  // docs/ was allowed while bash, zsh and dash copied, and `{ bash; } <<'EOF'`, `if true; then bash; fi <<'EOF'` the same, present
  // since the guard's first commit): a redirection on a compound's closer is the compound's, opened before it runs, so a here-document,
  // a here-string or a `<` there feeds every command inside that reads its script from stdin. The text is found when the compound
  // opens, by the closer that matches it: a subshell's `)` (its redirections sit on the segment after the marker), a group's `}` and a
  // keyword compound's closer word (`fi`, `done`, `esac`, `end`, each heading its segment), nesting counted; the frame carries it
  // (`stdinText`) and stdinBodies reads it through the frames. zsh's brace-body forms of the keyword compounds are not matched here
  // (their closer is a `}` the frame counts) and read no such text, the safe direction being a read that is missing here, not a write:
  // the shells run them, so this is a residual named beside the others.
  // `fd`: the numbered descriptor the consumer's script operand names (THE DESCRIPTOR FEED, round 6's fourth commit: `bash /dev/fd/3 3< <(echo
  // 'cp a b')` ran the printed text in bash and zsh, `python3 /dev/fd/3 3< <(..)` and `. /dev/fd/3 3< <(..)` too, while a `<` on a descriptor
  // other than 0 was skipped), so a `<` on that descriptor is read beside the ones on the standard input; a here-document or here-string body
  // is read on any descriptor (the lexer keeps none on it: the safe side); a `<` on a descriptor no operand names stays unread (`bash 3< <(..)`
  // reads its script from the standard input, not from 3)
  // THE DUPLICATED DESCRIPTOR (round 6's fifth commit, 2026-09-21; the body auditor: `exec 3< <(echo 'cp a b'); bash <&3`, `bash 0<&3`, `bash 3<
  // <(..) <&3`, `{ bash; } 3< <(..) <&3`, `exec 3< <(..); cat <&3 | bash` and `bash /dev/fd/4 4<&3` ran the printed text in bash and zsh while
  // every `<&` was skipped by the lexer): the descriptors a consumer at `seg` reads when it reads `fd` (the standard input when null) are `fd`
  // and every descriptor a `[n]<&m` on the segment, or on an exec feed earlier in this shell, duplicates onto one of them, to a fixpoint (bash:
  // Duplicating File Descriptors; dash(1) and zshmisc(1) alike); a dup from a word the lexer cannot read makes every descriptor this command
  // feeds readable (null), since the word may name any of them (the safe side)
  const fdsFor = (seg, fd = null) => {
    const set = new Set(['0']);
    if (fd != null) set.add(fd);
    const dups = [...(seg && seg.dups ? seg.dups : []), ...execFeeds.flatMap((s) => s.dups || [])];
    for (let grew = true; grew;) {
      grew = false;
      for (const d of dups) if (set.has(d.to)) { if (d.from == null) return null; if (!set.has(d.from)) { set.add(d.from); grew = true; } }
    }
    return set;
  };
  const textsOf = (seg, fds = new Set(['0'])) => {
    const out = [...seg.heredocs];
    for (const s of seg.stdin || []) {
      if (s.fd != null && fds && !fds.has(s.fd)) continue;   // `fds`: the descriptors read (THE DUPLICATED DESCRIPTOR); null reads every one
      out.push(...scriptTexts(s, s.herestring ? 'here-string script' : 'standard-input script', 'file'));   // a `<(echo '..')` carries the printed text as its readings; a here-string or body the resolver could not establish refuses
    }
    return out;
  };
  // what a closer's redirections feed the commands inside (THE CONSUMER'S STDIN): its here-documents, its `<` words, and through the descriptors its
  // `<&` dups reach, the exec feeds (round 6's sixth commit: `exec 3< <(echo 'cp a b'); (bash) <&3` ran the text in bash and zsh while the dup
  // after the `)` reached no exec feed)
  const closerTexts = (s) => { const fds = fdsFor(s); return [...textsOf(s, fds), ...execFeeds.flatMap((e) => textsOf(e, fds))]; };
  const closerStdin = (from, kind) => {
    if (kind === 'subshell') {
      let depth = 0;
      for (let j = from; j < segments.length; j++) {
        if (segments[j].paren === '(') depth++;
        else if (segments[j].paren === ')' && !segments[j].pattern && --depth === 0) { const next = segments[j + 1]; return next && !next.words.length ? closerTexts(next) : []; }   // a `)` ending a case pattern pairs with no `(` (THE PAREN RULE)
      }
      return [];
    }
    if (kind === 'group') {
      let depth = 0;
      for (let j = from; j < segments.length; j++) {
        for (const w of segments[j].words) {
          if (!plainWord(w)) continue;
          if (w.text === '{') depth++;
          else if (w.text === '}' && --depth === 0) return closerTexts(segments[j]);
        }
      }
      return [];
    }
    const closer = Object.hasOwn(BODY_CLOSER, kind) ? BODY_CLOSER[kind].closer : null;
    if (!closer) return [];
    let depth = 0;
    for (let j = from; j < segments.length; j++) {
      for (const w of segments[j].words) {
        if (!plainWord(w)) continue;
        if (CLOSERS[closer].includes(w.text)) depth++;
        else if (w.text === closer && --depth === 0) return closerTexts(segments[j]);
      }
    }
    return [];
  };
  // What reaches the command's standard input from OUTSIDE its own segment (`own`: the segment's own bodies, passed by stdinBodies): the closer
  // redirections of the compounds around it, the producer piped into it, an `exec` redirection earlier in this shell (THE EXEC FEED), else what
  // the caller feeds (THE INHERITED STDIN). THE FED SUBSTITUTION reads this with no `own` to know whether a substitution's command may read a
  // text the command carries: a segment's own redirection applies to the command, not to the substitutions the shell performs before it.
  // THE INHERITED STDIN as texts: a caller hands texts, or (THE WRITTEN PROCESS SUBSTITUTION) the printed reading it placed beside a `>(cmd)`
  // it writes into, read here through scriptTexts as a piped producer's is (a sound reading yields its texts; an UNRESOLVABLE one refuses,
  // when a consumer of this text asks for its standard input and not before)
  const inheritedTexts = () => inheritedStdin.flatMap((t) => (typeof t === 'string' ? [t] : scriptTexts(t, 'standard input', 'file')));
  const fedTexts = (idx, fds = new Set(['0']), own = []) => {
    const out = [...own];
    for (let j = frames.length - 1; j >= 0; j--) {   // THE CLOSER'S STDIN of the compounds around the command, innermost first
      if (frames[j].kind === 'function' && !frames[j].coproc && !frames[j].running) break;   // a body being replayed for a fed call reads on (THE CALLED BODY)
      if (frames[j].stdinText && frames[j].stdinText.length) out.push(...frames[j].stdinText);
    }
    const p = producerAt(idx);
    if (p != null) {
      for (let j = p; j >= 0 && segments[j].op === '|'; j--) out.push(...segments[j].heredocs);
      out.push(...pipedScripts(p));
    } else if (!out.length) out.push(...inheritedTexts());
    for (const s of execFeeds) out.push(...textsOf(s, fds));   // THE EXEC FEED: read beside the rest (a descriptor an exec opened stays open through a pipe)
    return out;
  };
  const stdinBodies = (idx, fd = null) => { const fds = fdsFor(segments[idx], fd); return fedTexts(idx, fds, textsOf(segments[idx], fds)); };
  // THE PASSED-THROUGH TEXT (round 6's fifth commit, 2026-09-21; the body auditor: `exec 3< <(echo 'cp a b'); cat <&3 | bash` ran the text in
  // bash and zsh, and `echo 'cp a b' | cat | bash`, `| cat - |`, `cat < <(echo '..') | bash` in the shells named, each with the cat a producer
  // outside the output model): a `cat` with no file operand prints its standard input as it is (`-`, `-u`, `--` and a name of the standard
  // input change nothing), so before a pipe it prints the text this command feeds it (stdinBodies: the producer before it, a `<`, a duplicated
  // descriptor, an exec feed), read as the consumer's script; a cat with another option word (`-n`, `-b`, `-A`, `-e`, `-E`, `-s`, `-t`, `-T`,
  // `-v`) prints a text the option shapes, which the model does not compute, so where a text is fed it is UNRESOLVABLE, refused (`cat -s` and
  // `cat -v` pass an ordinary script unchanged, so the option cannot be skipped on the safe side); a cat of a file, or one fed nothing the
  // guard holds, stays the producer outside the model (the residual)
  const passthroughCat = (s) => {
    if (s.paren || s.redirects.some((r) => WRITE_REDIRECTS.has(r.op)) || (s.closerTail && s.closerTail.length)) return null;   // a write redirection takes the output off the pipe; a `<(..)` on its `<` is the text fed (stdinBodies), so a substitution among the segment's commands is no bar, and an expansion among the operands is (below)
    const cmd = commandOf(s.words);
    if (!cmd || cmd.unknown || cmd.opaque || 'script' in cmd || cmd.chdirs.length || cmd.writes.length || cmd.name !== 'cat') return null;
    if (cmd.args.some((w) => !w.literal)) return null;
    const plainArg = (w) => w.text === '-' || w.text === '--' || w.text === '-u' || isStdinName(w.text);
    if (cmd.args.some((w) => !plainArg(w) && !w.text.startsWith('-'))) return null;   // a file operand: outside the model
    return { options: cmd.args.filter((w) => !plainArg(w)).map((w) => w.text) };
  };
  // THE PIPED SCRIPT (the second fix-up), read at the producer's segment `p` (the segment before the consumer, or before the compound
  // holding it): the words a literal echo or printf would print, or (the fifth commit) the text a plain cat passes through
  const pipedActive = new Set();   // the producers whose feed is being read (a compound fed by the cat itself points its stdinFrom back at it: `cat <<'EOF' | (bash)`)
  const pipedScripts = (p) => {
    if (segments[p].printed) return scriptTexts(segments[p].printed, 'piped script', 'file');   // lex placed the producer's printed text on the segment (placeReading, mode 'segment'): the echo or printf itself, or since round 6's second commit the `)` or `}` closing a subshell or group of such commands (THE OUTPUT MODEL); a producer with no printed text is outside the model
    const cat = passthroughCat(segments[p]);
    if (!cat || pipedActive.has(p)) return [];
    pipedActive.add(p);
    let fed;
    try { const fds = fdsFor(segments[p]); fed = fedTexts(p, fds, textsOf(segments[p], fds).slice(segments[p].heredocs.length)); } finally { pipedActive.delete(p); }   // the cat's own here-documents are fed to the consumer by fedTexts's pipeline loop already: its `<` words and what feeds it are what this adds
    if (!fed.length) return [];
    if (cat.options.length) {
      const spelling = segments[p].words.map((w) => w.raw).join(' ');
      cannotRead(word(spelling, false, spelling, { marks: 'x'.repeat(spelling.length) }), 'piped script', { kind: 'unresolvableReading', spelling, text: `a \`cat\` with the option word ${cat.options.map((o) => `\`${o}\``).join(', ')} stands before the pipe, and what it prints of the text this command feeds it depends on the option, which I do not model, so the script the shell reads is not known` });
      return [];
    }
    return fed;
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
  const openGroup = (conditional = null, timed = false) => frames.push({ kind: 'group', names: new Set(), dir, unknownDir, unknownWhy, oldDir, conditional, timed, stdinFrom: pipedFrom(), stdinText: closerStdin(walkIdx, 'group') });   // stdinFrom: the producer piped into the group; stdinText: what a redirection on its closing brace feeds it (THE CONSUMER'S STDIN, THE CLOSER'S STDIN)
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
  const pushCompound = (head) => { const f = { kind: head, moved: false, opened: false, braces: 0, condition: false, awaitBody: false, afterParen: false, dir, unknownDir, unknownWhy, stdinFrom: pipedFrom(), stdinText: closerStdin(walkIdx, head) }; frames.push(f); return f; };   // stdinFrom: the producer piped into the compound; stdinText: what a redirection on its closer feeds it (THE CONSUMER'S STDIN, THE CLOSER'S STDIN)   // the directory at the head: a redirection on the closer is judged there (closedConstruct)
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
  const popFunction = (f, upTo = walkIdx) => {
    if (f.bodyMoved && f.name) cdFunctions.add(f.name);
    // THE CALLED BODY: the definition's text as spelled, from its first word to the end of the segment its body closes on (`upTo`), kept by
    // each name it defines for a fed call to replay
    if (f.defFrom != null && f.names) { const next = segments[upTo + 1]; const end = next && next.start > f.defFrom ? next.start : command.length; const text = command.slice(f.defFrom, end); for (const nm of f.names) { functionBodies.set(nm, text); functionLines.set(nm, lineOf({ start: f.defFrom })); } }   // functionLines: the definition's line, where its body was parsed (the replay reads aliases as of that line: `f() { c a b; }`, then `alias c=cp`, then `f` expands in no shell)
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
      if (t.kind === 'function') popFunction(t, walkIdx - 1);   // the one-segment body was the previous segment
      else if (t.kind === 'subshell') { restore(t); frames.pop(); }
      else closeCompoundAt(frames.length - 1);
    }
  };
  const closeSubshell = (op) => {
    const j = parenCloses(frames.map((f) => f.kind));   // THE PAREN RULE (one home with the lexer's markers, round 6's eighth commit): in a case body a `)` ends a pattern, and inside a definition it closes nothing
    if (j < 0) return;
    restore(frames[j]);
    frames.length = j;
    // the `)` that ends a compound head's word list or condition (round 5's addendum): foreach's body opens here; a `)` with
    // nothing between it and the next word makes that word zsh's one-command body (`if (x) cmd`, `for y (..) cmd`, F6)
    const t = frames[frames.length - 1];
    if (isCompound(t) && !t.opened) { if (t.kind === 'foreach') t.opened = true; else t.afterParen = op === ''; }
    afterChildClosed();
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
  let movedAny = false;   // a cd, pushd, popd, chdir or a directory-changing option ran at this text's level (THE MOVED SHELL, round 6's fifth commit)
  const movedHere = () => {
    movedAny = true;
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
    try { for (const r of seg.redirects) if (WRITE_REDIRECTS.has(r.op)) add(r.target, r.how || `${r.op} redirection`); }   // a dash-reading redirect carries its own how, naming the construct (round 5's fifth addendum)
    finally { if (construct) ({ dir, unknownDir, unknownWhy } = saved); }
  };
  const countCandidates = () => { let n = 0; for (const set of candidates.values()) n += set.size; return n; };
  let knownCandidates = countCandidates();
  noteCandidates();   // THE HEAD CANDIDATES, over the words as lexed, before the walk (scriptTexts exists by now)
  // THE SPLICED PRINTER: the values this text gives its names were not known to the read above, so a command name that is an expansion was
  // no printer to it; while the candidates grew, the text is read again with them known (a resolved printer may give a name a further value,
  // `x=$($e cp)`: three reads at most), and the walk below reads the last lex
  for (let pass = 0; pass < 3 && countCandidates() !== knownCandidates; pass++) {
    knownCandidates = countCandidates();
    lexed = lex(command, shell, lexOpts);
    segments = withDashPieces(lexed.segments);
    opaque = lexed.opaque;
    noteCandidates();
  }
  for (let idx = 0; idx < segments.length; idx++) {
    const seg = segments[idx];
    walkIdx = idx;
    viaSeg = seg.dashPiece ? pieceVia(seg.dashPiece) : '';
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
        const fnNames = names.length ? names : [rest[rest.length - 1].text];
        frames.push({ kind: 'function', name: fnNames[fnNames.length - 1], names: fnNames, defFrom: prev.start, running: ctx.runFunction != null && fnNames.includes(ctx.runFunction), bodyMoved: false, dir, unknownDir, unknownWhy, depth: 0 });   // name() ... : a definition, not a run; `names`, `defFrom`: the definition's text is kept for a fed call (THE CALLED BODY); `running`: this text is the replay of a fed call, so the body reads the call's standard input
        idx++;
        continue;
      }
      frames.push({ kind: 'subshell', dir, unknownDir, unknownWhy, stdinFrom: pipedFrom(), stdinText: closerStdin(idx, 'subshell') });   // stdinFrom: the producer piped into the subshell; stdinText: what a redirection after its `)` feeds it (THE CONSUMER'S STDIN, THE CLOSER'S STDIN)
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
      const fnNameWord = (w) => !!(w && w.marks && /^u+$/.test(w.marks) && w.text !== '{' && w.text !== '}');   // an unquoted name after `function`: a plain identifier or a glob-shaped one (`[`, `[[`, `?`, `a*`), which bash and zsh take as the function's name (round 6's tenth commit: `function [ { cp "$@"; }; [ a b` ran cp while `[` was glob-marked and the `.literal` test skipped it)
      if (seg.words.length >= p + 2 && plainWord(seg.words[p]) && seg.words[p].text === 'function' && fnNameWord(seg.words[p + 1]) && seg.op !== '(' && !frames.some((f) => f.kind === 'function')) {
        // every word up to the body's `{` is a name (round 5's addendum, F2: zsh's `function f g {` defines both and runs nothing;
        // bash rejects the spelling); with no `{` on this segment the body is the next segment, a `{ }` group counted by `braces`
        // or zsh's one-command body, which dash, having no `function` word, runs in THIS shell (`function f⏎{⏎cd ../docs⏎}` moved
        // dash and the write after it landed on the tracked file, F10), so a cd in such a body leaves the directory unknown at
        // its close (`dashRuns`, popFunction)
        let q = p + 1;
        const fnNames = [];
        while (q < seg.words.length && !(plainWord(seg.words[q]) && seg.words[q].text === '{')) { if (fnNameWord(seg.words[q])) { definedFunctions.add(seg.words[q].text); fnNames.push(seg.words[q].text); } q++; }
        const body = q < seg.words.length;
        frames.push({ kind: 'function', name: seg.words[p + 1].text, names: fnNames, defFrom: seg.start, running: ctx.runFunction != null && fnNames.includes(ctx.runFunction), bodyMoved: false, dir, unknownDir, unknownWhy, depth: body ? 1 : 0, dashRuns: !body });   // `names`, `defFrom`, `running`: THE CALLED BODY, as on the paren path
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
    // THE VALUED NAMES (round 6's fourth commit, 2026-09-21; the body auditor): on the words as spelled, an assignment word in any position
    // whose name the shell runs as a command or sources as a file (SCRIPT_VALUED_NAMES, STARTUP_FILE_NAMES); bash's `${name@P}`, a prompt
    // expansion of the value, runs the value's `$(..)` (`x='$(cp a b)'; : "${x@P}"` copied in bash), so each value the command gives the name
    // is read as a script; zsh's `functions[NAME]=BODY` binds a function the way an alias binds a text (THE ALIAS ROAD; `functions[c]='cp
    // "$@"'; c a b` copied in zsh), a body the resolver reads spliced at the name's later uses and one it does not read binding null
    readValuedWords(seg.words);
    // THE EXPORTED FUNCTION (round 6's fifth commit, 2026-09-21; the residuals verifier: `env 'BASH_FUNC_c%%=() { cp "$@"; }' bash -c 'c a b'`,
    // `env -i .. /usr/bin/bash -c c`, `echo c | env .. bash`, `.. bash -s <<< c` and a `BASH_FUNC_cat%%` shadowing cat each ran the copy in
    // every shell while the quoted word was read as a command name): a bash the command starts imports a variable named `BASH_FUNC_NAME%%`
    // whose value opens with `() {` as the function NAME (bash's import of exported functions, since 4.4), so such an assignment word anywhere
    // in the command defines that function for the bash it reaches, its body read as a definition's is (walked, not run: a writer inside
    // refuses, `cp "$@"` through THE SPLIT OPERAND), as `export -f` already was
    for (const w of seg.words) { const m = w.literal ? w.text.match(/^BASH_FUNC_([A-Za-z_][A-Za-z0-9_]*)%%=(\(\) \{[^]*)$/) : null; if (m) recurse(`${m[1]} ${m[2]}`, 'bash', true, ` through the exported function \`BASH_FUNC_${m[1]}%%\``, []); }
    if (shell == null || shell === 'bash') for (const w of seg.words) for (const e of w.raw.matchAll(/\$\{([A-Za-z_][A-Za-z0-9_]*)@P\}/g)) for (const v of candidates.get(e[1]) || []) recurse(v, shell, false, ` through \`\${${e[1]}@P}\``);
    if (shell == null || shell === 'zsh') {
      // THE PARAMETER TABLES (round 6's seventh commit, 2026-09-21; the residuals verifier: `aliases[c]=cp` on a line before `c a b` inside `zsh <<'EOF'`,
      // `aliases=(c cp)`, the same through `printf .. | zsh`, `galiases[R]=report.md; cp .. R`, `saliases[md]='cp ..'; report.md`, `zsh -c 'commands[c]=
      // /usr/bin/cp; c a b'`, `commands+=(c /usr/bin/cp)` and `commands[c]=/usr/bin/cp` as zsh's own command each ran the copy in the shells named
      // while the guard read an unknown command): zshmodules(1), zsh/parameter: a key set in `aliases`, `galiases` or `saliases` defines an alias as
      // `alias`, `alias -g` and `alias -s` do, one set in `commands` a hashed path as `hash` does, and one set in `functions` a function; the whole-
      // table forms `TABLE=(NAME VALUE ..)` and `TABLE+=(..)` bind each pair (the lexer reads the parenthesised list as a subshell after the
      // assignment word, so the pairs are read from the two segments after it). Bound as of line 0 (the alias road's earlier-line rule refuses the
      // same line too: the safe side), a value that is not literal binding null (unreadable: refused where the name is used); a key that is not
      // literal makes every later command name unreadable (aliasState.unread), as an alias whose name is unreadable does
      const bindTable = (table, name, body) => {
        if (table === 'commands') { hashes.set(name, body); return; }
        aliases.set(name, { body, line: 0, global: table === 'galiases', suffix: table === 'saliases' });
      };
      const TABLES = /^(functions|aliases|galiases|saliases|commands)/;
      const bodyOf = (text, marks, literal) => (literal && !/[$`]/.test(text) && !(marks && /x/.test(marks)) && !text.includes('\0') && !hasGlobChar(text, marks || 'u'.repeat(text.length)) ? text : null);
      for (const w of seg.words) {
        const m = w.text.match(/^(functions|aliases|galiases|saliases|commands)\[([^\]\0]+)\]=([^]*)$/);
        if (!m || (w.marks && /x/.test(w.marks.slice(0, m[0].length - m[3].length)))) continue;
        const valueMarks = w.marks ? w.marks.slice(m[0].length - m[3].length) : null;
        bindTable(m[1], m[2], bodyOf(m[3], valueMarks, !(valueMarks && /[^uq]/.test(valueMarks))));   // the word is no literal to the lexer (its brackets are glob characters); the value part is read by its own marks
      }
      if (seg.op === '(' && seg.words.length === 1 && seg.words[0].literal && TABLES.test(seg.words[0].text) && /^[a-z]+\+?=$/.test(seg.words[0].text) && segments[idx + 1] && segments[idx + 1].paren === '(' && segments[idx + 2] && segments[idx + 2].op === ')' && segments[idx + 3] && segments[idx + 3].paren === ')') {
        const table = seg.words[0].text.replace(/\+?=$/, '');
        const ws = segments[idx + 2].words;
        for (let k = 0; k < ws.length; k += 2) {
          const key = ws[k];
          const val = ws[k + 1];
          if (!key.literal || key.text.includes('\0')) { if (!aliasState.unread) aliasState.unread = key.raw; break; }
          bindTable(table, key.text, val ? bodyOf(val.text, val.marks, val.literal) : null);
        }
      }
    }
    // THE POSITIONAL VALUE (round 6's sixth commit): a whole word that is a positional parameter stands for the operands this shell holds for it
    expandPositionals(seg);
    // B2: the expansions the guard can read are resolved before the segment's words and targets are judged
    for (const r of seg.redirects) r.target = resolveWord(r.target);
    if (seg.stdin) seg.stdin = seg.stdin.map((s) => { const r = resolveWord(s); return r === s ? s : Object.assign(r, { fd: s.fd, herestring: s.herestring }); });   // a here-string or `<` word too (round 6's sixth commit: `f() { bash <<< "$1"; }` fed the operand)
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
      recurseSubs(seg);
      for (const v of seg.viaSubs) recurse(v.text, shell, false, v.via);   // the construct's other reading (round 5's fifth addendum)
      taintArith(seg);   // a bare `(( x = 5 ))` is a segment with no words: its body may assign any name in it
      continue;
    }
    // THE EMPTY ALTERNATIVE in command position (`{,cp} a b`): bash drops the empty word, so the next word is the command and is judged so; zsh runs
    // a command named by the empty word, which writes nothing (the operand position is judged under both readings through `variants` below)
    while (seg.words.length && seg.words[0].braceEmpty) seg.words = seg.words.slice(1);
    let preWords = seg.words;   // as spelled: the readability rule reads a mention in the command's own text, not in a resolved value
    seg.words = seg.words.map(resolveWord);
    addRedirects(seg, construct);   // a glob: every match (add); a closer's redirections in the construct's start directory
    recurseSubs(seg);
    for (const v of seg.viaSubs) recurse(v.text, shell, false, v.via);   // the construct's other reading (round 5's fifth addendum)
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
    // THE EXEC FEED (round 6's fourth commit): a bare `exec` with redirections alone opens them for the rest of this shell
    if (cmd.wrapped && cmd.name === '' && !cmd.args.length && cmd.wrappers.length === 1 && cmd.wrappers[0] === 'exec' && (seg.heredocs.length || (seg.stdin && seg.stdin.length) || (seg.dups && seg.dups.length))) execFeeds.push(seg);   // a bare `exec <&3` duplicates for the rest of this shell too (THE DUPLICATED DESCRIPTOR)
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
      for (const t of scriptTexts(cmd.script, `\`${cmd.scriptFlag || 'flock -c'}\` script`)) recurse(t, shell, true, cmd.script.literal ? '' : READING_VIA(cmd.script.raw));   // `$SHELL -c`: a fresh shell, the names not inherited (B2); the texts the word stands for, each a script (the third fix-up)
      continue;
    }
    // a command whose name is an expansion runs the text the expansion gives: one the resolver could not establish refuses (THE
    // RESOLVER'S CONTRACT; round 5's correctness-2: `$(echo cp ../base/*.md report.md)` alone ran the globbed copy in bash, zsh and
    // dash while its head was an unread expansion), one the resolver never read stays the residual decision 47 names
    const headWord = cmd.args ? seg.words[seg.words.length - cmd.args.length - 1] : null;
    const headIdx = headWord ? seg.words.length - cmd.args.length - 1 : -1;
    // THE HEAD SPLICE (round 6's second commit, 2026-09-20): a command name that stands for a text the shell runs in its place is read
    // again with that text spliced in, the segment's other words and redirections after it as spelled (a body may end in a redirection
    // operator, so the text is spliced and re-lexed, never swapped word for word), beside the segment as spelled: the readings of an
    // expansion the resolver established (`${x:-cp} a b`, `$(echo -e cp) a b`), an alias body the command bound on an earlier line
    // (THE ALIAS ROAD; a suffix alias's body takes the word as its operand; a `-g` alias is expanded in every position, so a later
    // unquoted word spelled so is a target the hook cannot read), a hashed path, and a path the command made by a copy or a link of
    // another command (`bound`: the source's text). A binding whose text the resolver cannot read makes the name a target the hook
    // cannot read (refused while a project is in play); after an alias whose NAME is unreadable, every later command name is one.
    // The splice runs in this shell with this command's names (not a fresh shell), the chain of alias names bounding the recursion.
    const headTexts = headWord ? scriptTexts(headWord, 'command name', 'head').map((t) => ({ text: t, chain: aliasChain })) : [];
    // a glob in the command name (round 6's third commit, 2026-09-21: `/usr/bin/[c]p a b` ran cp in bash, zsh and dash while the walk read an
    // unknown command named so): the matches, sorted as the shells sort them, stand in the name's place as the words the shell makes (the
    // first is the command, the rest lead its operands: `/usr/bin/c? a b` runs cp with the other matches before a and b, and writes
    // nothing when they are several), and the segment is read again with them; a pattern the guard cannot expand (the directory not
    // known, the read past its cap) is a name the hook cannot read; a pattern matching nothing stands as spelled (bash and dash run the
    // literal name, zsh stops with no match), so nothing is spliced
    if (headWord && headWord.glob && !Object.hasOwn(CONSTRUCT_HEADS, headWord.text)) {   // `[[` and `((` carry a glob character and are the constructs the lexer read, not patterns
      const m = expandGlob(headWord, unknownDir ? null : dir);
      if (m == null) cannotRead(headWord, 'command name', { kind: 'aliasUnread', text: `\`${headWord.raw}\` is a pattern I cannot expand here, so which command it names is not known` });
      else if (m.length && !(m.length === 1 && m[0].text === headWord.text)) headTexts.push({ text: m.map((p) => p.text).join(' '), chain: aliasChain });   // expandGlob answers words, sorted: their texts; a pattern that stands as spelled splices nothing
    }
    // zsh's `=cmd` (zshexpn, Filename Expansion: an unquoted word beginning with `=` is the path of the command named) in command position
    // runs that command (round 6's third commit: `=cp a b` copied in zsh while the walk read a command named `=cp`); read under zsh's grammar
    if (headWord && headWord.literal && (shell == null || shell === 'zsh') && headWord.marks && headWord.marks[0] === 'u' && /^=[A-Za-z_][A-Za-z0-9_.+-]*$/.test(headWord.text)) headTexts.push({ text: headWord.text.slice(1), chain: aliasChain });
    // THE PEELED NAME (round 6's ninth commit, 2026-09-22; the round's verifiers: `alias command=cp`, then `command ../base/report.md report.md`
    // copied in dash while allowed, and the same for builtin, exec, env, nice, nohup, time, timeout, sudo, stdbuf, setsid, ionice, flock, taskset,
    // chrt, numactl, zsh's noglob and nocorrect, `[` and `[[`, through a here-document or a pipe in every shell; `hash -p /usr/bin/cp env`,
    // then `env a b` copied in bash and `hash env=/usr/bin/cp` in zsh; a copy or link of cp at `../scratch/env` on PATH, as `env a b`, as
    // `../scratch/env a b` and as `nice env a b`, in every shell; while the same binding of a name outside the wrapper set was refused): the
    // alias, hash and bound-path roads were consulted at the head the wrapper walk left, so a binding of a wrapper's own name was never seen
    // once operands followed it (a bare `command` with no operand was the head and was read). Every word the walk peeled as a wrapper is a
    // name the shell looks up (an alias on the first word, a hashed path or a bound path through the shell's or the wrapper's own PATH
    // search), so the three roads are asked of each, the binding spliced at that word (the words before it as spelled, the text, the words
    // after it, the wrapper peeled again on the spliced text) and an unreadable binding refused as the head's is. `[` is a command name the
    // shells alias (the lexer marks it a pattern, which matches nothing and stands as spelled), and `[[` is one to dash, so both take the
    // alias and hash roads by their text.
    const nameWordOf = (w) => (w && (plainWord(w) || (w.glob && w.marks && /^u+$/.test(w.marks) && (w.text === '[' || w.text === '[['))) ? w.text : null);
    const nameRoads = (hw, hIdx) => {
      const name = nameWordOf(hw);
      if (name == null) return;
      const here = lineOf(seg);
      const a = aliases.get(name);
      if (a && !a.suffix && a.line < here && !aliasChain.has(name)) {
        if (a.body == null) cannotRead(hw, 'command name', { kind: 'aliasUnread', text: `\`${name}\` is an alias this command defines with a text I do not read, so what runs in its place is not known` });
        else headTexts.push({ text: a.body, chain: new Set([...aliasChain, name]), at: hIdx });
      }
      for (const [suf, sa] of aliases) if (sa.suffix && sa.line < here && name.endsWith('.' + suf) && !aliasChain.has(suf)) {
        if (sa.body == null) cannotRead(hw, 'command name', { kind: 'aliasUnread', text: `\`${name}\` ends in a suffix this command aliases to a text I do not read` });
        else headTexts.push({ text: sa.body + ' ' + hw.raw, chain: new Set([...aliasChain, suf]), at: hIdx });
      }
      if (hashes.has(name)) {
        const p = hashes.get(name);
        if (p == null) cannotRead(hw, 'command name', { kind: 'aliasUnread', text: `\`${name}\` is hashed by this command to a path I do not read` });
        else headTexts.push({ text: p, chain: aliasChain, at: hIdx });
      }
      if (aliasState.unread && !a) cannotRead(hw, 'command name', { kind: 'aliasUnread', text: `an earlier \`alias\` of this command binds a name I do not read (${aliasState.unread}), so \`${name}\` may run another command` });
    };
    nameRoads(headWord, headIdx);
    const peeledIdx = cmd.wrapperIdx || [];
    for (const j of peeledIdx) if (j !== headIdx) nameRoads(seg.words[j], j);
    // THE BOUND PATH (round 6's fourth commit, 2026-09-21; the residuals lens ran `cp /usr/bin/cp ../scratch/c2` and then the copy through
    // `'../scratch/c2'`, `"../scratch/c2"`, `$x` with x the path, `"$PWD/../scratch/c2"`, `../scratch/c?` and `~/c2` after `HOME=$PWD/../scratch`,
    // each allowed while every shell ran it, since the lookup read the unquoted literal spelling alone): a path the command made by copying
    // or linking a command (`bound`) is looked up by the head's TEXT however spelled (a quoted spelling runs the file too, unlike an alias; a
    // spelling the readability rule resolved is that text), by a pattern's matches among the paths bound (the file is made when the command
    // runs, so the filesystem cannot expand the pattern at check time), and through PATH for a bare name (the directories a `PATH=` prefix
    // or plain assignment of this command gives, else the guard's own environment; a PATH the command sets to a value the resolver does not
    // read makes a bare name one it cannot read while a path is bound); a head through a HOME the command reassigns is one it cannot read
    // while a path is bound. Nothing here applies while no path is bound.
    const boundRoad = (hw, hIdx) => {
      if (!hw || !bound.size) return;
      const bindHead = (abs) => {
        const src = bound.get(abs);
        if (src == null) cannotRead(hw, 'command name', { kind: 'aliasUnread', text: `\`${hw.raw}\` is a path this command made by copying or linking a source I do not read` });
        else headTexts.push({ text: src, chain: aliasChain, at: hIdx });
      };
      if (hw.marks && hw.marks.includes('h') && homeUnreadableNow()) cannotRead(hw, 'command name', { kind: 'aliasUnread', text: `\`${hw.raw}\` is a path through HOME, which this command reassigns, and this command made a path by copying or linking a command, so which file it names is not known` });
      else if (hw.literal && hw.text.includes('/') && !unknownDir) { const abs = literalPath(hw.text, dir); if (abs && bound.has(abs)) bindHead(abs); }
      else if (hw.glob && !unknownDir) {
        const re = globRegex(hw.text, hw.marks);
        if (re) for (const abs of bound.keys()) if (re.test(abs) || re.test(path.relative(dir, abs)) || re.test('./' + path.relative(dir, abs))) bindHead(abs);
      }
      // a bare name, or `[[`, which dash (having no `[[` keyword and no `[[` builtin) looks up as an external command and finds through PATH
      // (round 6's tenth commit: `cp /usr/bin/cp '../scratch/[['; PATH=../scratch:$PATH; [[ a b` ran cp in dash while `[[` was glob-marked and
      // skipped the lookup); `[` is a builtin in every shell, so a bound `[` never runs, and it is not searched here
      const bareName = hw.literal && !hw.text.includes('/') ? hw.text : (hw.text === '[[' && hw.marks && /^u+$/.test(hw.marks) ? '[[' : null);
      if (bareName != null && !unknownDir) {
        const prefix = seg.words.slice(0, hIdx).find((w) => /^PATH=/.test(w.raw));
        const pathValue = prefix ? (prefix.literal && !prefix.text.includes('\0') ? prefix.text.slice(5) : null) : (vars.has('PATH') ? vars.get('PATH') : (process.env.PATH || ''));
        if (pathValue == null) cannotRead(hw, 'command name', { kind: 'aliasUnread', text: `\`${hw.raw}\` is looked up through a PATH this command sets to a value I do not read, and this command made a path by copying or linking a command, so which file it names is not known` });
        else for (const d of pathValue.split(':')) { const abs = d ? literalPath(path.join(d, bareName), dir) : null; if (abs && bound.has(abs)) bindHead(abs); }
      }
    };
    boundRoad(headWord, headIdx);
    for (const j of peeledIdx) if (j !== headIdx) boundRoad(seg.words[j], j);   // THE PEELED NAME: an external wrapper searches PATH for the name after it, and the shell for the first
    // THE VANISHING HEAD (round 6's tenth commit, 2026-09-22; the round's verifiers: `$c cp ../base/report.md report.md` ran the copy in every
    // shell while `$c` was read as the command name and allowed): a command name that is an expansion the command never gives a value may be
    // empty, and the shell makes no field of it, so the NEXT word is the command (bash: Word Splitting; dash(1); zshexpn(1)); the same reading
    // THE VANISHING OPERAND gives a writer's operand, given here to the head, so the segment is read again with the head dropped (spliced as the
    // empty text, which the splice's join drops), beside the reading that keeps it (the residual a command whose name is an unread expansion is).
    // A head the readability rule resolved to a literal, or one an always-set form makes (mayVanish is false there), keeps its place.
    if (headWord && mayVanish(headWord, !unknownDir) && !headTexts.some((t) => t.text === '' && (t.at == null ? headIdx : t.at) === headIdx)) headTexts.push({ text: '', chain: aliasChain, at: headIdx });
    for (const w of seg.words) if (w !== headWord && plainWord(w)) { const g = aliases.get(w.text); if (g && g.global && g.line < lineOf(seg)) cannotRead(w, 'a global alias', { kind: 'aliasUnread', text: `\`${w.text}\` is a global alias this command defines (zsh expands it in every position), so the word is not the text spelled` }); }
    for (const r of seg.redirects) if (plainWord(r.target)) { const g = aliases.get(r.target.text); if (g && g.global && g.line < lineOf(seg)) cannotRead(r.target, 'a global alias', { kind: 'aliasUnread', text: `\`${r.target.text}\` is a global alias this command defines (zsh expands it at a redirection target too), so the target is not the text spelled` }); }   // round 6's fourth commit: `alias -g R=report.md` then `echo x > R` wrote report.md in zsh while the target escaped the rule
    if (headTexts.length) {
      // a word the walk already expanded to a literal (a positional the replay bound, a `$name` the readability rule read) is spliced as
      // that literal, single-quoted, not by its raw spelling: raw would re-expand in the splice's re-lex, so `$c "$@"` after a `shift` had
      // spliced `cp "$@" "$@"` and doubled the operands to a copy no shell performs (round 6's seventh commit, THE POSITIONAL VALUE meeting
      // THE HEAD SPLICE); a word raw and text agree on, or one still an expansion, keeps its raw
      const spliceRaw = (w) => (w.literal && w.raw !== w.text ? `'${w.text.replace(/'/g, `'\\''`)}'` : w.raw);
      const redirs = seg.redirects.map((r) => `${r.op} ${spliceRaw(r.target)}`).join(' ');
      for (const { text, chain, at = headIdx } of headTexts) {   // `at`: the word the text stands for (the head, or a wrapper name THE PEELED NAME bound), the words around it as spelled
        const before = seg.words.slice(0, at).map(spliceRaw).join(' ');
        const after = seg.words.slice(at + 1).map(spliceRaw).join(' ');
        recurse([before, text, after, redirs].filter(Boolean).join(' '), shell, false, ` through the command name \`${seg.words[at].raw}\``, stdinBodies(idx), chain, true, { adopt: true });   // the spliced text runs in this shell: a cd in it moves the shell (THE MOVED SHELL: `alias c=cd`, then `c ../notes`; `c=cd; $c ../notes`)
      }
    }
    const asSpelled = cmd.args;
    let { name } = cmd;
    if (/^(python[0-9.]*|pypy[0-9]*)$/.test(name)) name = 'python';
    else if (name === 'nodejs') name = 'node';
    else if (/^zf_(mv|ln|rm|rmdir)$/.test(name)) name = name.slice(3);   // zsh/files' builtins are the coreutils commands by another name (round 6's third commit: `zmodload zsh/files; zf_mv a b` moved onto the tracked file in zsh)
    // rule (d) (the third pass): a shell option not on the inert allowlist leaves the directory unknown from here
    if (name === 'set' || name === 'shopt' || name === 'setopt' || name === 'unsetopt') {
      const why = shellOptionChange(name, asSpelled);
      if (why) { setUnknown(why); movedHere(); }
      if (setsKeywordMode(name, asSpelled)) keywordMode = true;
    }
    // THE POSITIONAL VALUE: a `set` with operands binds them (literal ones read; any other, or an option word before them, rebinds them to values not
    // known), a `shift` drops the first n (a count not read rebinds them to values not known)
    if (name === 'set') { const ops = setOperands(asSpelled); if (ops) bindPositionals(ops.every((w) => w && w.literal && !w.text.includes('\0')) ? ops : UNKNOWN_POSITIONALS, 'an earlier `set` rebinds the positional parameters through option words or operands I do not read'); }
    else if (name === 'shift' && positionals !== null) { const n = asSpelled.length ? (asSpelled[0].literal && /^[0-9]+$/.test(asSpelled[0].text) ? Number(asSpelled[0].text) : null) : 1; bindPositionals(n == null || positionals === UNKNOWN_POSITIONALS ? UNKNOWN_POSITIONALS : positionals.slice(n), n == null ? 'an earlier `shift` moves the positional parameters by a count I do not read' : positionalsWhy); }
    // bash's keyword mode (setsKeywordMode): a later writer's operands are read as spelled and with every assignment-shaped
    // word dropped, and a write under either reading is judged; zsh reads the words as spelled
    let variants = keywordMode && asSpelled.some(isAssignmentWord) ? [asSpelled, asSpelled.filter((w) => !isAssignmentWord(w))] : [asSpelled];
    // The braces the lexer cut from this command's tail (splitAtClosers, round 5's third addendum; the second addendum had found
    // the trailing `}` of zsh's `{ cp ../base/report.md report.md }` read as cp's destination, so the tracked file zsh overwrote
    // was read as a source, and cut it here): zsh reads them as closers, the reading the frames took; bash and dash read a `}`
    // after a command as one more operand (`cp a }` writes a file named `}` where no group is open, and they reject the group
    // spelling), so each writer is judged as cut and with the braces back as operands, and a write under either reading is refused.
    if (seg.closerTail && seg.closerTail.length) variants = [...variants, ...variants.map((v) => [...v, ...seg.closerTail])];
    // THE EMPTY ALTERNATIVE (round 6's sixth commit, 2026-09-21; the residuals verifier: `{cp,} ../base/report.md report.md`, `{mv,} ..` and `{bash,} -c
    // '..'` ran in bash while the lexer kept the empty alternative as an operand, `cp '' a b`, a copy no shell performs): bash drops an unquoted empty
    // word a brace list expands to (`printf '[%s]' {cp,}` prints `[cp]`, measured) while zsh keeps it (`[cp][]`), so the operands are judged under both
    // readings, and an empty alternative in command position is spliced away for bash's reading (THE HEAD SPLICE below)
    if (asSpelled.some((w) => w.braceEmpty)) variants = [...variants.map((v) => v.filter((w) => !w.braceEmpty)), ...variants];   // bash's reading first, so the refusal names the writer
    // THE CALLED BODY (round 6's fifth commit, 2026-09-21; the residuals verifier: `f() { bash; }; echo 'cp a b' | f`, `f <<< '..'`, `f <<'EOF'`,
    // `f < <(echo '..')`, a body of `sh`, of `cat | bash`, of `. /dev/stdin`, of `bash "$@"` called with /dev/stdin, and the call inside a
    // subshell or a group, each ran the piped text in the shells named while the call was an unknown command and the body had been read as a
    // definition with a standard input of its own): a function this command defines, called where a text the guard holds feeds it (a pipe, a
    // here-document or here-string, a `<`, a compound's closer, an exec feed, the caller's), runs its body with that text on its standard
    // input, so the definition is read again as the running body (`runFunction`: its frame reads the fed text as a compound's does) with the
    // call's operands (`callArgs`: a shell inside it whose script operand is a positional parameter runs with them); a call inside its own
    // body is not followed again (fnChain)
    {
      const calledRaw = rawHeadOf(seg.words);
      const fnName = functionBodies.has(name) ? name : (calledRaw != null && functionBodies.has(calledRaw) ? calledRaw : null);
      // THE EMPTY ALTERNATIVE among a call's operands (round 6's seventh commit; the body auditor: `f() { "$@"; }; f {cp,} a b`, `f {,cp} a b`, `f
      // {bash,} -c '..'` and `f() { bash "$@"; }; f {-c,} '..'` each ran in bash while the replay bound the empty word bash drops): the body is
      // replayed under bash's reading (the empty word dropped) and under zsh's (kept), as the writer's operands are judged below
      const callVariants = asSpelled.some((w) => w.braceEmpty) ? [asSpelled.filter((w) => !w.braceEmpty), asSpelled] : [asSpelled];
      if (fnName != null && !fnChain.has(fnName)) for (const callArgs of callVariants) recurse(functionBodies.get(fnName), shell, false, ` through the function \`${fnName}\``, stdinBodies(idx), aliasChain, false, { runFunction: fnName, callArgs, fnChain: new Set([...fnChain, fnName]), lineBase: functionLines.get(fnName) });   // THE POSITIONAL VALUE (round 6's sixth commit): the replay runs for every call, fed or not, so the body is read with the call's operands in its positional parameters; its lines lie at the definition's (the aliases bound before the body was parsed apply, later ones do not)
    }
    for (const args of variants) {
    // the walk-around lens second pass (family 6): a call to a function whose body moved the shell moves the cwd, which the guard does not
    // follow into the call, so the directory is unknown from here (the body was modelled as not moving the shell)
    const calledAsSpelled = rawHeadOf(seg.words);   // the head before a wrapper peel: a function named like a wrapper is called by that name (C6b)
    // THE SHADOWED BUILTIN (round 6's seventh commit, 2026-09-21; with THE DEFINITION'S NAME above): a function this command defines under a
    // builtin's name runs in the builtin's place in every shell (bash, zsh and dash find a function before a regular builtin such as cd, pushd,
    // popd and chdir; `command` and `builtin` reach the builtin, and every other wrapper an external command), so the builtin's own reading (a
    // move of the shell) does not apply at the call: the body runs through THE CALLED BODY, and a body that moves the shell leaves the directory
    // unknown at the call (cdFunctions, just below)
    const shadowedByFunction = !cmd.wrapped && (functionBodies.has(name) || (calledAsSpelled != null && functionBodies.has(calledAsSpelled)));
    // THE DEFINITION'S NAME (round 6's seventh commit, 2026-09-21; the residuals verifier: `cd() { cp a b; }; cd ..` moved the shell to HOME while
    // the guard read the name `cd` of the definition as a bare `cd` before the definition registered a segment later, and judged the body's write
    // there): the name before an empty `()` defines a function and runs nothing, so a builtin's own reading (a move) must not fire on it
    const isDefName = !cmd.wrapped && segments[idx + 1] && segments[idx + 1].paren === '(' && segments[idx + 2] && segments[idx + 2].paren === ')';
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
        if (shadowedByFunction || isDefName) break;   // THE SHADOWED BUILTIN: the function runs, not the builtin; THE DEFINITION'S NAME: `cd()` defines, moves nothing
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
        if (seg.dashPiece) block = `an earlier \`${name}\` is a further command dash reads after the \`${seg.dashPiece.op}\` inside a \`${seg.dashPiece.construct}\`, where bash and zsh compare and move nothing, so where the shell is after it depends on which shell runs the line`;   // round 5's fifth addendum
        else if (prevOp === '&&' || prevOp === '||') block = `an earlier \`${name}\` after \`${prevOp}\` may not run, so where it lands is not known (its move depends on the previous status)`;
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
      case 'popd': if (shadowedByFunction || isDefName) break; moveUnknown('an earlier `popd` returns to a directory this command did not set'); movedHere(); break;   // THE SHADOWED BUILTIN / THE DEFINITION'S NAME
      // `chdir` is cd's synonym in zsh and dash and no command in bash, and the guard does not know which shell runs the
      // line (the third pass): a cd it cannot know ran, family 6
      case 'chdir': if (shadowedByFunction || isDefName) break; setUnknown('an earlier `chdir` moves the shell in zsh and dash and fails in bash, so where the shell is after it is not known'); movedHere(); break;   // THE SHADOWED BUILTIN / THE DEFINITION'S NAME
      case 'cp': case 'mv': case 'install': case 'ln': {
        // THE SPLIT OPERAND (round 5's fifth addendum, third fix-up, 2026-09-20; found while pinning the IFS cost: `IFS=:; cp $(echo
        // '../base/report.md:report.md')` from docs/ was allowed while bash, zsh and dash split the one operand into two and copied,
        // and `cp $1`, `cp $(cat f)` the same, present since the guard's first commit: a writer with fewer operands than it needs
        // named no target, and an unquoted expansion the shell splits into several words was that missing operand). THE RULE: when a
        // copying writer has fewer operands than its two and one of them is an unquoted expansion the guard did not resolve, the
        // shell may split it into the operands the writer needs, so that operand is a target the hook cannot read (refused while a
        // project is in play, the non-literal rule). Round 6 (2026-09-20; round 5's extra7-1 found `cp "$@"` copying onto the tracked
        // file in every shell while the rule exempted every double-quoted word): a double-quoted word is exempt only when the guard
        // can prove it one field (dqSingleField, the property stated there); a double-quoted expansion it cannot prove single may
        // split, the `@` forms of every shell and zsh's splitting flags among them.
        const operandsAsSpelled = args.filter((a) => !(a.text.startsWith('-') && a.text.length > 1));
        const maySplit = (a) => !a.literal && !!a.marks && a.marks.includes('x') && !dqSingleField(a.raw);
        if (operandsAsSpelled.length < 2 && operandsAsSpelled.some(maySplit)) cannotRead(operandsAsSpelled.find(maySplit), name, { kind: 'splitOperand' });
        // copyTargets stats the destination to see whether it is a directory, so a stat error there (the walk-around lens second pass, family 4)
        // is an UnknownPath; attach the verb and the last operand's spelling for the refusal before it propagates.
        let r;
        try { r = copyTargets(args, unknownDir ? null : dir, name); }
        catch (e) {
          if (isUnknownPath(e) && !(e.why && e.why.how)) {
            const ops = args.filter((a) => !(a.text.startsWith('-') && a.text.length > 1));
            e.why = { ...(e.why || {}), how: name + viaOf(), raw: ops.length ? ops[ops.length - 1].raw : name };
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
          // THE VANISHING OPERAND (round 6's eighth commit; the rule is stated at mayVanish): the copy is judged again under every operand list the
          // shell may hand the writer with an operand that may vanish dropped, and a write under any of them refuses naming the operand dropped;
          // past VANISH_CAP such operands the count is a target the hook cannot read
          const variants = vanishVariants(args, !unknownDir);
          if (variants == null) cannotRead(args.find((a) => mayVanish(a, !unknownDir)), name, { kind: 'vanishOperand', cap: VANISH_CAP });
          else for (const { dropped, kept } of variants) {
            let rr;
            try { rr = copyTargets(kept, unknownDir ? null : dir, name); }
            catch (e) {
              if (isUnknownPath(e) && !(e.why && e.why.how)) e.why = { ...(e.why || {}), how: droppedHow(name, dropped) + viaOf(), raw: dropped[0].raw };
              throw e;
            }
            if (!rr.unknown) for (const w of rr.targets) add(w, droppedHow(name, dropped));
            if (name === 'ln' && !rr.unknown) recordSymlink(kept, unknownDir ? null : dir);   // class H under this list too: `ln -sf $c report.md ../scratch/l.md` links l.md to the tracked file once `$c` is dropped
          }
        }
        break;
      }
      case 'link': {   // coreutils link(1): one hard link, made at the second operand (the third pass; the sibling of a hard `ln`)
        const ops = args.filter((a) => !(a.text.startsWith('-') && a.text.length > 1));
        if (ops.length >= 2) add(ops[1], 'link');
        for (const { dropped, kept } of vanishVariants(args, !unknownDir) || []) { const k = kept.filter((a) => !(a.text.startsWith('-') && a.text.length > 1)); if (k.length >= 2) add(k[1], droppedHow('link', dropped)); }   // THE VANISHING OPERAND
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
      case 'sed': {
        for (const w of sedTargets(args)) add(w, 'sed -i');
        // sed's `w` and `W` commands and the `w` flag of `s` write the file they name (round 6's third commit: `sed -n 'w report.md'
        // ../base/report.md` and `sed 's/x/y/w report.md' ..` wrote the tracked file in every shell while the guard read sed as a writer
        // through `-i` alone); the files are read off every literal script word (sedScriptWrites), a script the reader cannot parse to its end
        // refuses naming the command it stopped at, and a script that is an expansion stays the residual the property names
        // THE SED FILE (round 6's fourth commit): a `-f FILE` naming the standard input or a descriptor this command feeds stands for the bodies fed
        // (stdinBodies), a `<(..)` for the text it prints (scriptTexts); each is a literal script word for the reader, in the file word's spelling
        const sedFileBodies = (f, drop = 0) => {
          const name = f.text.slice(drop);   // the file past the option text glued before it (`--file=<(..)`, one word as bash reads it)
          const texts = f.literal && isStdinName(name) ? stdinBodies(idx, fdOfName(name)) : (procsubOf(drop ? sliceWord(f, drop) : f) != null ? scriptTexts(f, 'sed -f script', 'file').map((t) => t.slice(drop)) : []);
          return texts.map((t) => word(t, true, f.raw));
        };
        const sw = sedScriptWrites(args, sedFileBodies);
        for (const w of sw.targets) add(w, 'sed w');
        if (sw.unread) cannotRead(sw.unread.word, 'sed script', { kind: 'sedScript', text: sw.unread.why });
        break;
      }
      case 'perl':
        for (const w of perlTargets(args)) add(w, 'perl -i');
        break;
      case 'python': case 'node': {
        const kind = name;
        let inline = null;
        let stdin = true;   // no script operand: the script is on stdin (python3 <<EOF, python3 -u <<EOF)
        let stdinFd = null;   // the numbered descriptor a script operand names (THE DESCRIPTOR FEED: `python3 /dev/fd/3 3< <(..)`)
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
          if (a.literal && isStdinName(a.text)) { stdinFd = fdOfName(a.text); break; }   // stdin, said so (`-`, `/dev/stdin`, `/dev/fd/0`: the third fix-up; a descriptor this command feeds, round 6's third commit; the descriptor named, round 6's fourth)
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
          for (const t of scriptTexts(inline, `${kind} script`)) scan(t);   // the texts the word can stand for (the third fix-up; THE RESOLVER'S CONTRACT)
        } else if (stdin) {
          for (const body of stdinBodies(idx, stdinFd)) scan(body);
        }
        break;
      }
      case 'eval': case 'trap': {
        // round 6's second commit: `eval 'cp ../base/report.md report.md'` and `trap 'cp ../base/report.md report.md' EXIT` ran the copy in
        // every shell while allowed, the text standing in the command. The words eval joins with one space, or trap's action (its first
        // operand, unless an option word or a `-`; `trap SIG` alone resets), are a script of this shell when every word is literal or carries
        // readings (THE RESOLVER'S CONTRACT: a word the resolver could not establish refuses through scriptTexts); an expansion the resolver
        // never reads keeps what the base did, the command marked opaque (`eval "$cmd"`: a script held in a variable, the residual named)
        let ws = args.length && args[0].literal && args[0].text === '--' ? args.slice(1) : args;   // `eval -- TEXT`: bash and zsh read the `--` as the option terminator (round 6's fourth commit: `eval -- cp a b` copied in both while the `--` stood as eval's first word); trap's `--` was read before
        if (name === 'trap') { ws = ws.length >= 2 && !(ws[0].literal && /^-/.test(ws[0].text)) ? [ws[0]] : []; }
        let texts = [''];
        let unread = !ws.length;
        vanishedRead = false;
        for (const w of ws) {
          const ts = scriptTexts(w, name === 'eval' ? 'eval' : 'trap action', 'text');
          if (!ts.length) { unread = true; break; }
          texts = texts.flatMap((a) => ts.map((b) => (a ? a + ' ' : '') + b));
          if (texts.length > 64) { unread = true; break; }
        }
        if (vanishedRead && !unread && name === 'eval') { sawOpaqueCommand = true; if (positionals !== null) bindPositionals(UNKNOWN_POSITIONALS, 'an earlier `eval` of a text I do not read may rebind the positional parameters'); }   // THE VANISHED TEXT read one text of an operand; its other values are not read, and a text this shell runs and the guard does not read may set or shift the positional parameters
        if (unread) { if (name === 'eval') { sawOpaqueCommand = true; if (positionals !== null) bindPositionals(UNKNOWN_POSITIONALS, 'an earlier `eval` of a text I do not read may rebind the positional parameters'); } break; }   // THE POSITIONAL VALUE: a text this shell runs and the guard does not read may set or shift them
        for (const t of texts) recurse(t, shell, false, ` through \`${name}\``, null, aliasChain, false, { adopt: name === 'eval', trapMove: name === 'trap' });   // eval's text runs in this shell and moves it (THE MOVED SHELL); a trap action that moves leaves the directory unknown
        break;
      }
      case 'xargs': sawOpaqueCommand = true; break;
      case 'emulate': {
        // zsh's `emulate [-LR] [shell [flags]] -c TEXT` runs TEXT under the emulation, in this shell (round 6's third commit: `emulate sh -c 'cp a
        // b'` copied in zsh while the walk read an unknown command); the text after `-c` is a script of zsh, read as `eval`'s text is
        for (let k = 0; k < args.length; k++) if (args[k].literal && args[k].text === '-c' && args[k + 1]) for (const tx of scriptTexts(args[k + 1], '`emulate -c` script')) recurse(tx, 'zsh', false, ' through `emulate -c`', null, aliasChain, false, { adopt: true });
        break;
      }
      case 'mapfile': case 'readarray': {
        // bash's `-C CALLBACK` runs CALLBACK as a command every `-c N` lines, its index and the line appended (round 6's fourth commit, the body
        // auditor: `mapfile -C 'cp a b #' -c 1 < f` copied in bash while the callback's text stood in the command unread): the text is a script
        // of this shell, read as eval's text is (the appended index and line are operands the text's last command takes; a text the resolver
        // cannot read refuses through scriptTexts, an expansion it never reads is the residual)
        for (let k = 0; k < args.length; k++) if (args[k].literal && /^-[A-Za-z]*C$/.test(args[k].text) && args[k + 1]) for (const tx of scriptTexts(args[k + 1], `\`${name} -C\` callback`)) recurse(tx, shell, false, ` through \`${name} -C\``, null, aliasChain, false, { adopt: true });
        break;
      }
      case 'alias': {
        // THE ALIAS ROAD's definitions (see `aliases` above): each NAME=BODY operand binds NAME to BODY's text (after quote removal, as the
        // shell stores it) for the segments on a later line; `-g` and `-s` are zsh's global and suffix aliases; `-p`, `-r`, `-m`, `-L` and
        // `--` are option words; an operand with no `=` prints an alias. A BODY the resolver cannot read (an expansion in it) binds the
        // name to null; a NAME it cannot read marks aliasState.unread. `unalias` is not read: a binding stays (the safe side).
        let k = 0;
        let global = false;
        let suffix = false;
        for (; k < args.length && args[k].literal && /^-/.test(args[k].text) && args[k].text !== '-'; k++) { if (args[k].text === '--') { k++; break; } if (args[k].text.includes('g')) global = true; if (args[k].text.includes('s')) suffix = true; }
        for (; k < args.length; k++) {
          const w = args[k];
          const eq = w.text.indexOf('=');
          if (eq < 0) continue;
          const nameLiteral = !w.marks || !w.marks.slice(0, eq).includes('x');
          if (!nameLiteral) { if (!aliasState.unread) aliasState.unread = w.raw; continue; }
          const bodyLiteral = w.literal || (!!w.marks && !w.marks.slice(eq + 1).includes('x') && !hasGlobChar(w.text.slice(eq + 1), w.marks.slice(eq + 1)) && !w.text.includes('\0'));   // THE PEELED NAME (round 6's ninth commit): `alias [=cp` is one word the lexer marks a pattern for the `[` in its NAME, while its body is plain text; the body is read when nothing in IT is an expansion or a pattern
          aliases.set(w.text.slice(0, eq), { body: bodyLiteral && !/[$`]/.test(w.text.slice(eq + 1)) ? w.text.slice(eq + 1) : null, line: defLineOf(seg), global, suffix });   // defLineOf: inside a head splice the definition binds at the spliced segment's line (`alias a=alias`, then `a c=cp`: round 6's fifth commit)   // a body the shell expands when the alias is USED (a quoted `$x` or a backtick; round 6's fourth commit: `alias c='$x'`, then `x=cp`, then `c a b` copied in dash while the body was spliced as the text `$x`) binds null, as an expansion at the definition does: the safe side
        }
        break;
      }
      case 'hash': {
        // bash's `hash -p PATH NAME...` and zsh's `hash NAME=PATH` bind a command name to a path (measured: each shell ran the copy through
        // the bound name); every other option word (`-r`, `-d`, `-l`, `-t`, `-v`, `-f`, `-m`) binds nothing the walk reads
        if (args.length >= 3 && args[0].literal && args[0].text === '-p') { for (const n of args.slice(2)) if (n.literal) hashes.set(n.text, args[1].literal ? args[1].text : null); }
        for (const w of args) {
          const eq = w.text.indexOf('=');
          if (eq <= 0 || (w.marks && w.marks.slice(0, eq).includes('x'))) continue;
          hashes.set(w.text.slice(0, eq), w.literal ? w.text.slice(eq + 1) : null);
        }
        break;
      }
      case 'source': case '.': {
        // a sourced script whose operand names the standard input (`source /dev/stdin <<'EOF'`, `. /dev/stdin <<< '..'`: bash and zsh ran the
        // body, measured) reads what this command reads, in this shell (round 6's second commit); a sourced file's contents are not in the
        // command (the residual the surfaces name; the name poison VAR_POISONERS applies as before)
        const ops = args.length && args[0].literal && args[0].text === '--' ? args.slice(1) : args;   // `. -- FILE`: the option terminator (round 6's fourth commit: `. -- <(echo 'cp a b')` copied in bash and zsh while the `--` was read as the operand)
        if (ops.length && ops[0].literal && isStdinName(ops[0].text)) for (const body of stdinBodies(idx, fdOfName(ops[0].text))) recurse(body, shell, false, ` through \`${name} ${ops[0].text}\``, [], aliasChain, false, { adopt: true });   // the descriptor named is read (THE DESCRIPTOR FEED: `. /dev/fd/3 3< <(..)`); a sourced text runs in this shell and moves it (THE MOVED SHELL)
        // a sourced process substitution is the text a literal echo or printf prints, as a script operand that is one is (round 6's third
        // commit: `. <(echo 'cp a b')` copied in bash and zsh, zsh's `. =(echo '..')` too, while the operand was read as a file outside the command)
        else if (ops.length && procsubOf(ops[0]) != null) for (const t of scriptTexts(ops[0], `\`${name}\` operand`, 'file')) recurse(t, shell, false, ` through \`${name} <(..)\``, null, aliasChain, false, { adopt: true });
        else if (positionals !== null) bindPositionals(UNKNOWN_POSITIONALS, `an earlier \`${name}\` of a file whose contents are not in the command may rebind the positional parameters`);   // THE POSITIONAL VALUE: a sourced file runs in this shell and may set or shift them
        break;
      }
      default:
        if (SHELLS.has(name)) {
          // the script is read as the shell named reads it (`$'...'` is quoting under bash and zsh only; the
          // options a cluster takes a word for differ; shellScript and lex)
          // THE SHELL'S OPTION WORD (round 6's sixth commit, 2026-09-21; the residuals verifier: `set -- -c; bash "$1" 'cp a b'` and through sh, dash
          // and zsh, `bash "$@"` after `set -- -c '..'`, `bash "${f:--c}" ..`, `bash ${f--c} ..`, `f=-c; bash ${f-x} ..`, an array, a loop variable, a
          // function's `$1`, a `read` or `printf -v` value, `$(cat <<'E' ..)` and the brace list `{-c,}`, each ran the script in the shells named while
          // the expansion in option position was taken as the script FILE operand, so the `-c` it stood for was never seen and the literal script
          // after it went unread): a word in option position (before the operand) that the resolver did not read stands for each text it can (its
          // readings, a value THE HEAD CANDIDATES or THE POSITIONAL VALUE hold; the shell is read again with each in the word's place, split at
          // blanks where the word is unquoted) and, when it stands for none, is refused on the side WRAPPER_OPT takes for an option a wrapper's
          // table does not know: the word and every later word a target the hook cannot read. A process substitution there is an operand (a path).
          // THE CALLED BODY's replay reads `bash "$@"` and `bash -c "$1"` through THE POSITIONAL VALUE, which put the call's operands in the words.
          const readShell = (argv, budget) => {
          const sh = shellScript(argv, name);
          if (sh.optionWord) {
            const { optionWord: ow, at } = sh;
            const before = unresolved.length;
            const ts = scriptTexts(ow, `\`${name}\` option or operand`, 'option');
            if (!ts.length) {
              if (unresolved.length === before) { const why = { kind: 'shellOptionWord', option: ow.raw, shell: name }; cannotRead(ow, name, why); for (const r of argv.slice(at + 1)) cannotRead(r, name, why); }
              return;
            }
            const lit = (t) => word(t, true, ow.raw, { marks: 'q'.repeat(t.length) });
            for (const t of ts.slice(0, budget)) {
              const pieces = /^"/.test(ow.raw) || !/[ \t\n]/.test(t) ? [lit(t)] : t.split(/[ \t\n]+/).filter(Boolean).map(lit);   // unquoted, the shell splits the text at blanks (bash and dash; zsh's whole word is read too where it is one)
              readShell([...argv.slice(0, at), ...pieces, ...argv.slice(at + 1)], Math.max(1, Math.floor(budget / ts.length)));
            }
            return;
          }
          // THE STARTUP FEED (round 6's fifth commit, 2026-09-21; the body auditor: `BASH_ENV=/dev/stdin bash -c : <<< 'cp a b'`, `echo '..' |
          // BASH_ENV=/dev/stdin bash -c :`, `BASH_ENV=/dev/fd/3 bash -c : 3< <(..)`, `export BASH_ENV=/dev/stdin; bash -c : <<< '..'`, the same
          // through env and a nested `bash -c`, and `ENV=/dev/stdin dash -i -c :` each ran the fed text while the value was read as a path
          // outside the command): a STARTUP_FILE_NAMES value the command gives (THE HEAD CANDIDATES: a prefix assignment, an export, env's
          // operand, in any text of the command) that names the standard input or a descriptor this shell is fed (STDIN_NAMES, fdOfName) is
          // the text fed, which the shell sources at startup; read whether or not this shell would (bash reads BASH_ENV when not interactive
          // and ENV under POSIX mode when interactive, dash reads ENV when interactive: the safe side, as `--rcfile` is read)
          for (const nm of STARTUP_FILE_NAMES) for (const v of candidates.get(nm) || []) if (isStdinName(v)) for (const body of stdinBodies(idx, fdOfName(v))) recurse(body, name, undefined, ` through \`${nm}\``, []);
          if ('script' in sh) {
            for (const t of scriptTexts(sh.script, `\`${name} -c\` script`)) recurse(t, name, undefined, sh.script.literal ? '' : READING_VIA(sh.script.raw));   // the texts the word can stand for, each a script (THE RESOLVED SUBSTITUTION, THE DEFAULT WORD; THE RESOLVER'S CONTRACT)
          } else if (sh.stdin) {
            for (const body of stdinBodies(idx, sh.fd)) recurse(body, name, undefined, '', []);   // bash <<'EOF' ... EOF, a pipe, `bash /dev/stdin`: the body is the script, and the shell has consumed it (nothing passes on); `bash /dev/fd/3 3< <(..)` reads the descriptor named (THE DESCRIPTOR FEED)
          } else if (sh.file) {
            // `bash <(echo 'cp a b')`, zsh's `=(...)`: the file the shell reads is the text a literal echo or printf prints (the third fix-up;
            // bash and zsh copied); any other file's contents are not in the command
            if (procsubOf(sh.file) != null) for (const t of scriptTexts(sh.file, `\`${name}\` script operand`, 'file')) recurse(t, name);
          }
          // a startup file that is a process substitution is read the same way (round 6's third commit: `bash --rcfile <(echo 'cp a b') -i`)
          for (const f of sh.rc || []) if (procsubOf(f) != null) for (const t of scriptTexts(f, `\`${name} --rcfile\` file`, 'file')) recurse(t, name);
          };
          readShell(args, 16);
        }
    }
    if (chdirSaved) ({ dir, unknownDir, unknownWhy } = chdirSaved);   // env -C / sudo -D moved the cwd for this command only
    // the walk-around lens second pass (family 3): record a remove/rename/link this segment made AFTER judging its own targets, so it changes
    // the reading of LATER segments only, never this command's own write
    recordMutations(name, args, unknownDir ? null : dir);
    if (name === 'cat' && !unknownDir) {
      // a `cat FILE > DEST` copies FILE onto DEST as cp does, so DEST is a bound path (THE BOUND PATH; round 6's fourth commit: `cat /usr/bin/cp >
      // ../scratch/c2; chmod +x ../scratch/c2; ../scratch/c2 a b` copied in every shell while the path was read as an unknown command)
      const ops = args.filter((a) => !(a.text.startsWith('-') && a.text.length > 1));
      const outs = seg.redirects.filter((r) => WRITE_REDIRECTS.has(r.op));
      if (ops.length === 1 && outs.length === 1 && outs[0].target.literal) { const d = literalPath(outs[0].target.text, dir); if (d) bound.set(d, ops[0].literal ? ops[0].text : null); }
    }
    }
    recordSegment(seg, idx, cmd, preWords);   // B2 and the readability rule: this segment's writes hold for the segments after it
  }
  activeLinks = prevLinks;
  // `links` (class H) are returned so evaluate can follow them while it places the targets the hook could not read (M3):
  // a numeric target's literal directory part is folded through a link the same command makes before it, as the kernel
  // will follow it once it exists (`ln -s <proj>/notes <out>/d && echo x > <out>/d/x-$$.md` landed in the tracked folder
  // while the numeric view resolved `<out>/d` through a filesystem where the link did not yet exist).
  // the directory state at the text's end, for a caller whose shell ran this text in place (recurse's adopt: THE MOVED SHELL, round 6's fifth commit)
  return { targets, opaque: opaque || sawOpaqueCommand, unresolved, links, dir, unknownDir, unknownWhy, oldDir, moved: movedAny || dir !== ctx.dir || unknownDir !== !!ctx.unknownDir, positionals, positionalsWhy };
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
  } finally { activeMemo = prev; }   // an exception here is the caller's to refuse: an UnknownPath by its own text, anything else by the catch-all (round 6; until then any other throw was read as not guarded, an allow on an internal error)
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
  // THE CATCH-ALL REFUSES, EVERYWHERE (round 5 of the review, 2026-09-20; round 6 the same day). An exception the walk did not
  // anticipate is the strongest signal the guard has that it does not understand the command in front of it, and until round 5
  // every catch in evaluate turned one into the most permissive answer available, an allow (round 4's extra4-4: a command word
  // that is an Object.prototype key threw inside the walk and the command ran). Round 5 refused while the payload's cwd sat in a
  // tracked project and passed elsewhere. Round 6 refuses from every cwd, for the ORDER of the decisions: judge reads the command
  // (extractWriteTargets) before it asks which project any target puts in play, and it asks per target, of the target's own
  // directory, a `cd` it followed, or a copy's landing folder, never of the cwd alone (a literal `<project>/docs/report.md` from a
  // cwd in no project is refused by name, and a `cd <project> && cp ..` from one by the moved directory). So a throw inside the
  // walk comes BEFORE the hook knows whether the command reaches a tracked file, and the cwd is no bound on what it reaches: an
  // allow on that throw from a cwd in no project protected nothing (round 5's correctness-3 measured it: a `$(printf)` in a target
  // threw a TypeError, and `cd <project>/docs && cp ../base/report.md $(printf)report.md` from a scratch directory wrote the
  // tracked file while the same command from docs/ was refused). Any exception other than an UnknownPath (which has its own
  // refusal) now refuses from any cwd, naming the exception; the cost, an internal error refusing ordinary work outside every
  // project until it is fixed, is one retry and a visible defect, where the allow was an invisible one.
  try { return judge(command, cwd); }
  catch (e) { return internalErrorRefusal(e, cwd); }
}
// The refusal for an exception evaluate did not anticipate (the catch-all above): the exception's name and message, from any
// cwd (round 6). The project the cwd sits in, when one does, is named as every refusal names it; from a cwd in no project the
// refusal says why it refuses there too. A root that came from TRACKCHANGES_ROOT is named by the variable, never by its value.
function internalErrorRefusal(e, cwd) {
  const named = `${(e && e.name) || 'Error'}: ${String((e && e.message) || e).replace(/\s+/g, ' ').slice(0, 300)}`;
  let hit;
  try { hit = trackingRootAt(cwd, { closures: new Map(), roots: new Map(), refusable: new Map() }); }
  catch (e2) { hit = { root: null, dir: cwd, fromEnv: false, unknown: `${(e2 && e2.name) || 'Error'}: ${String((e2 && e2.message) || e2).replace(/\s+/g, ' ').slice(0, 300)}` }; }
  const where = !hit ? 'a command can name a tracked file of any project from any directory (an absolute path, a `cd`), so I refuse here too'
    : hit.unknown ? `whether ${cwd} sits in a project that tracks files is not known either (${hit.unknown}), and such a project tracks files whose changes are recorded for me to accept or reject`
      : `${hit.fromEnv ? 'the project TRACKCHANGES_ROOT names' : hit.root} tracks files whose changes are recorded for me to accept or reject`;
  return `This command is blocked here: while reading it I hit an error of my own (${named}), so I cannot tell whether it `
    + `writes a tracked file, and ${where}. Run it in a `
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
    if (u.why && u.why.kind === 'shellOptionWord') {
      // THE SHELL'S OPTION WORD (round 6's sixth commit): a word the shell fills in where the shell's option or script operand stands, standing
      // for no text the guard could read, so whether it is `-c` and which text the shell runs is not known
      return `This command is blocked here: its \`${u.why.shell}\` takes the word ${u.why.option} where an option or the script operand stands, `
        + `a word the shell fills in when the command runs, so I cannot tell whether it is \`-c\` and which text the shell would run, and `
        + `${where} tracks files whose changes are recorded for me to accept or reject. Spell the option and the script out: outside that `
        + `project the command then runs as usual, and a tracked file takes its change through track-edit instead:\n${TRACK_EDIT}`;
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
    if (u.why && u.why.kind === 'aliasUnread') {
      // THE ALIAS ROAD (round 6's second commit): a command name bound by this command (an alias, a hash, a copied or linked path) to a
      // text the resolver cannot read, an alias whose name it cannot read, or a word a `-g` alias would expand: the reason recorded
      // at the binding is the refusal's text, so the person sees which binding it is
      return `This command is blocked here: its ${u.how} names ${u.raw}, and ${u.why.text}, so I cannot tell what would run or which file it `
        + `would write, and ${where} tracks files whose changes are recorded for me to accept or reject. Spell the command the alias or `
        + `the binding stands for, with its paths: outside that project the command then runs as usual, and a tracked file takes its change `
        + `through track-edit instead:\n${TRACK_EDIT}`;
    }
    if (u.why && u.why.kind === 'sedScript') {
      // THE SED SCRIPT (round 6's third commit): the script reader stopped at a command letter it does not have, so a `w` after it would go unseen
      return `This command is blocked here: ${u.why.text}, and a sed script can write any file through its \`w\` command, so I cannot tell `
        + `which file it would write, and ${where} tracks files whose changes are recorded for me to accept or reject. Spell the script with `
        + `sed's own commands (sed itself rejects a letter it does not have), or write outside that project: there the command then runs as `
        + `usual, and a tracked file takes its change through track-edit instead:\n${TRACK_EDIT}`;
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
    if (u.why && u.why.kind === 'ifsNamed') {
      // THE IFS RULE (round 6's fourth commit): the command names IFS, so an expansion the readability rule could otherwise read splits by a
      // rule the resolver does not compute where it is not double-quoted; the remedy is the quoting, or the words spelled out
      return `This command is blocked here: its ${u.how} names ${u.raw}, and ${u.why.text}, so I cannot tell which words the shell makes of it `
        + `or which file it would write, and ${where} tracks files whose changes are recorded for me to accept or reject. Double-quote the `
        + `expansion, or spell the words out: outside that project the command then runs as usual, and a tracked file takes its change `
        + `through track-edit instead:\n${TRACK_EDIT}`;
    }
    if (u.why && u.why.kind === 'unresolvableReading') {
      // THE RESOLVER'S CONTRACT (round 6): the word is built from an echo, a printf or a `${...}` word the resolver looked at and
      // could not establish, so it says what it could not read, and the remedy is the literal text
      return `This command is blocked here: its ${u.how} is filled in from ${u.why.spelling}, a text the shell produces when the `
        + `command runs, and I could not establish that text: ${u.why.text}. I cannot tell what it would write, and ${where} tracks `
        + `files whose changes are recorded for me to accept or reject. Spell the text out (the path, or the script, as literal `
        + `words): outside that project the command then runs as usual, and a tracked file takes its change through track-edit `
        + `instead:\n${TRACK_EDIT}`;
    }
    if (u.why && u.why.kind === 'splitOperand') {
      // THE SPLIT OPERAND (the third fix-up): the writer's one operand is an unquoted expansion the shell may split into the two it needs
      return `This command is blocked here: its ${u.how} has one operand, ${u.raw}, an expansion the shell fills in and may split into `
        + `several words when the command runs, so I cannot tell which file it would write, and ${where} tracks files whose changes are `
        + `recorded for me to accept or reject. Spell the source and the destination out as two words: outside that project the command `
        + `then runs as usual, and a tracked file takes its change through track-edit instead:\n${TRACK_EDIT}`;
    }
    if (u.why && u.why.kind === 'vanishOperand') {
      // THE VANISHING OPERAND (round 6's eighth commit): more operands the shell may make no word of than the readings the guard follows
      return `This command is blocked here: its ${u.how} has more than ${u.why.cap} operands the shell may make no word of (${u.raw} is one: an unquoted `
        + `expansion whose value may be empty or unset, or a pattern that may match nothing), so how many operands it runs with, and which file it would `
        + `write, is not known, and ${where} tracks files whose changes are recorded for me to accept or reject. Spell the operands out as literal `
        + `words: outside that project the command then runs as usual, and a tracked file takes its change through track-edit instead:\n${TRACK_EDIT}`;
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
    // a `>` between `[[` and `]]` with a target the hook cannot read (`[[ $a > $b ]]`): a comparison in bash and zsh, a redirection
    // in dash, refused by the rule above with the comparison's own remedy beside the path's (round 5's fifth addendum, a priced cost)
    const compare = u.how.includes(CONSTRUCT_HEADS['[['].via) ? ' If this is a string comparison, run it from a directory outside that project, or write it with `expr`, which bash, zsh and dash run alike.' : '';
    return `Track-changes is ON in ${where}, so this command is blocked here: its ${u.how} names ${u.raw}, `
      + `which is not a literal path${entry}${named}. The shell fills that in when the command runs, so I cannot tell which `
      + `file it would write, and a tracked file written that way would carry no change for me to accept or `
      + `reject.${compare} Spell the path out: outside that project the command then runs as usual, and a tracked file `
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
