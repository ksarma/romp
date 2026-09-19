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
// one-liner whose write path is computed (a name, an f-string, `sys.argv`, `os.environ`,
// `process.env`): the interpreter scan reads a literal path only, and a scan that flagged a computed
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
// numeric segment (the pid-candidate scan reads only entries that exist when the hook runs; the class-H
// rewrite that DOES follow a same-command `ln -s` with literal operands and an untouched name, below,
// runs for a literal target, not for the numeric candidate scan), and an entry named by the process id in a folder OUTSIDE every project
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
// ROMP_SID; it never reads a variable named in the command (that would read names shaped like
// secrets and guess at the cwd). Of those three, only HOME's value can appear in a refusal, and only
// as a path the hook resolved through it (the target a `~/` or a leading `$HOME` names, or the
// project root a bare `cd` lands in); TRACKCHANGES_ROOT is named by the variable, never by its value,
// and ROMP_SID is never printed (review round 2, 2026-09-18, correcting a round-1 clause that claimed
// no environment value reaches a message: a `"$HOME/x.md"` target is expanded and refused by its
// resolved path, which is HOME's value). The refusal says the target is not literal and asks for the
// path spelled out, which then takes today's verdict (a file outside the project runs as usual, a
// tracked one goes through track-edit). With no such project in play the word is dropped, as before.
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
// (INERT_SET_LETTERS, INERT_SET_OPTIONS, INERT_SHOPT: exit status, tracing, history, completion, prompts, job control
// and syntax choices that move no path, built from the shells' own option lists) leaves the directory unknown from that
// point (shellOptionChange); every option about cd, pushd, physical paths, links, globbing, brace expansion, aliases,
// quoting, restricted or POSIX mode is off the lists. (e) ANY DEPTH: the parent-prefix rule finds every tracked root
// under the literal head at any depth (parentTrackedRoots, breadth-first, PARENT_SCAN_BUDGET). (f) UNKNOWN OPTION REFUSES
// EVERYWHERE: an option a writer's table does not know refuses on every path the writer is reached through, each
// candidate operand judged by its own project from any cwd (optionCandidates), and the mutation and symlink recorders
// mark every candidate. Also from that pass: `chdir` (zsh's and dash's cd, no command in bash) leaves the directory
// unknown, and coreutils `link` is a hard-link maker (a write target and a family-3 mutation). The costs, each stated and
// measured in tools/romp-track-bash-guard-corpus.json: a `~/` write beside a mention of HOME, an `env -S` line, a
// relative write after `shopt -s globstar`, a write through a link whose source is a variable, and a variable-named
// file in a folder that holds a tracked project at any depth beneath it, each from a cwd in play (the last from any).
//
// THE LISTS THAT REMAIN, each with the side its GAP falls on (a missing entry causes a false refusal, or a write):
//   PREFIXES (the wrapper set): gap = a WRITE (an unlisted wrapper is read as its own command, an unmodelled writer by
//     the contract), so the set is stated on the four surfaces and the unlisted wrappers the passes found (unshare,
//     nsenter, script, setarch, setpriv) are on the contract's list.
//   WRAPPER_OPT (each wrapper's option table): gap = a false refusal (an option not in the table refuses).
//   COPY_OPT (cp/mv/install/ln): gap = a false refusal (an option not in the table refuses, on every path).
//   INERT_SET_LETTERS, INERT_SET_OPTIONS, INERT_SHOPT: gap = a false refusal (an option not listed makes the directory
//     unknown).
//   EXPANDED_NAMES: gap = a WRITE only if expansionAt ever substitutes a name not listed here; today it substitutes HOME
//     alone, and the two are one edit apart (the comment at each names the other).
//   NUMERIC_EXPANSIONS: gap = a false refusal (an expansion not listed is unreadable).
//   ANSI_C_SHELLS, SHELLS: gap = a false refusal (a shell not listed gets the restricted reading, or is not recursed
//     and its script's literal targets are judged by the own-project step as words the hook cannot read).
//   The writer cases (cp, mv, install, ln, link, tee, dd, sponge, truncate, sort, sed, perl, python, node, the shells):
//     gap = a WRITE, by the contract's allow-by-default for an unmodelled writer, stated below with the list of the ones
//     the passes found.
//   The root markers (.obsidian, .git, .trackchanges, store-io's own): gap = a WRITE only if store-io adds a marker;
//     markerAt mirrors store-io's list and family 5 refuses a nested one.
//   The sed, perl, truncate and interpreter option lists: gap = an over-count (an unknown option is read as a flag and
//     the operand after it as a file), the refuse direction.
//
// THE CONTRACT. This guard is best-effort against known write forms: it refuses the shell writes it models and, by
// design, allows anything it does not recognise, so it never blocks ordinary work it cannot read; it is a backstop, not
// a complete boundary. The allow-by-default for an unmodelled writer is deliberately not flipped, since flipping it would
// refuse almost all normal work. What it does refuse, while a tracked project is in play, is a write it reads but cannot
// place: a target it cannot read, a path it cannot check (a stat error other than not-found), an option on a modelled
// writer or wrapper it does not parse in full, an env -S string, a shell option it does not know to be inert for paths,
// a link whose source it cannot read, and a `~` or `$HOME` write beside a mention of HOME. These write forms are not
// modelled and still reach a tracked file: rsync; awk with a redirect inside its program; ed; ex; make; find with -delete
// or -exec; a git subcommand that writes the working tree (checkout, stash, apply, reset, rm, clean, mv); a computed path
// inside an interpreter (python3 -c, node -e); a script the shell reads from elsewhere (eval, xargs, a sourced file, trap,
// a command whose name is an expansion, a script held in a variable); a wrapper outside the guard's set (unshare,
// nsenter, script, setarch, setpriv); shuf -o; a cd through CDPATH; and a leading opaque expansion from a cwd outside every
// project. The same paragraph, and this writer list, are on the vendored SKILL.md, hooks/README.md and docs/install.md,
// pinned identical by a test.

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { findVaultRoot, isTrackedFile, isNonTextPath, hasNulBytes } from '../vendor/track-changents/store-io.mjs';
import { relPathFor, trackedPaths as readTrackedPaths, untrackedPaths as readUntrackedPaths, trackedClosure } from '../vendor/track-changents/store-io.mjs';
import engine from '../vendor/track-changents/engine.js';

// ── lexer ───────────────────────────────────────────────────────────
//
// A command is cut into simple commands ("segments") at |, ||, &&, ;, &, newline, ( and ). Each
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

const WRITE_REDIRECTS = new Set(['>', '>>', '>|', '&>', '&>>', '>&', '<>']);
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
const PREFIXES = new Set(['sudo', 'command', 'builtin', 'exec', 'nice', 'nohup', 'time', 'env', 'timeout', 'ionice', 'stdbuf', 'setsid', 'flock', 'taskset', 'chrt', 'numactl']);
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
const newSegment = () => ({ words: [], redirects: [], heredocs: [], subs: [], arith: [], op: '' });

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
      } else if (expect.kind === 'heredoc') pendingHeredocs.push({ delim: buf, stripTabs: expect.stripTabs, owner: seg });
      else if (expect.kind === 'herestring') seg.heredocs.push(buf);
      expect = null;
    } else {
      // the keyword: unquoted, in command position (first in its segment, or after a reserved word)
      if (raw === '[[' && (!seg.words.length || RESERVED.has(seg.words[seg.words.length - 1].text))) inTest = true;
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
      if (c === '>') {
        if (src[i + 1] === '>') { i += 2; expect = { kind: 'target', op: '>>' }; continue; }
        if (src[i + 1] === '|') { i += 2; expect = { kind: 'target', op: '>|' }; continue; }
        if (src[i + 1] === '&') {
          i += 2;
          if (/[0-9-]/.test(src[i] || '')) { while (i < src.length && /[0-9-]/.test(src[i])) i++; continue; }   // dup: 2>&1, >&-
          expect = { kind: 'target', op: '>&' };
          continue;
        }
        i++; expect = { kind: 'target', op: '>' }; continue;
      }
      if (c === '<') {
        if (src[i + 1] === '<' && src[i + 2] === '<') { i += 3; expect = { kind: 'herestring' }; continue; }
        if (src[i + 1] === '<') { const strip = src[i + 2] === '-'; i += strip ? 3 : 2; expect = { kind: 'heredoc', stripTabs: strip }; continue; }
        if (src[i + 1] === '>') { i += 2; expect = { kind: 'target', op: '<>' }; continue; }
        if (src[i + 1] === '&') { i += 2; while (i < src.length && /[0-9-]/.test(src[i])) i++; continue; }
        i++; expect = { kind: 'data' }; continue;
      }
      if (c === '&') {
        if (src[i + 1] === '>') { const app = src[i + 2] === '>'; i += app ? 3 : 2; expect = { kind: 'target', op: app ? '&>>' : '&>' }; continue; }
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
  return { segments, opaque };
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
  let wrapped = false;   // the walk-around lens second pass (family 6): a wrapper prefix was peeled before the command
  for (;;) {
    while (k < words.length && RESERVED.has(words[k].text)) k++;
    while (k < words.length && /^[A-Za-z_][A-Za-z0-9_]*=/.test(words[k].raw)) k++;
    if (k >= words.length) return null;
    const name = path.basename(words[k].text);
    if (!PREFIXES.has(name)) return { name, args: words.slice(k + 1), chdirs, writes, wrapped };
    wrapped = true;
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
// `set -o chasedots` walked around the list. The inert lists are built from the shells' own option lists (`set -o`
// and `shopt` in bash 5.2, `set -o` in zsh 5.9, `set -o` in dash) and hold the options about exit status, tracing,
// history, completion, prompts, job control, quoting-free syntax choices and the like; every option about cd, pushd,
// physical paths, links, globbing, brace expansion, aliases, quoting, restricted or privileged mode, POSIX mode or the
// input source is OFF the lists, so its mention makes the directory unknown. A single letter is inert only when it is
// inert in BOTH bash and zsh (the Bash tool runs one of the two and the guard does not know which): `-e -u -x -v -n
// -C -f -a -m -b -k -h -t -E -H` and zsh's `-F -y`; `-P` (bash physical), `-T` (zsh cdablevars), `-w` (zsh chaselinks),
// `-B` (bash braceexpand), `-J`, `-N`, `-D`, `-G`, `-I` and the rest are not. Names are compared as zsh compares
// them (case and underscores ignored, a `no` prefix negating), so `set -o pipe_fail`, `setopt NO_NOMATCH` and
// `shopt -s histappend` read the same as their plain spellings. A gap here (an inert option not listed) is a false
// refusal, recoverable in one step (drop the option, or spell the target absolutely), never a write that passes.
const INERT_SET_LETTERS = 'euxvnCfambkhtEHFy';
const INERT_SET_OPTIONS = new Set([
  // bash `set -o`, all but braceexpand, physical, posix and privileged
  'allexport', 'emacs', 'errexit', 'errtrace', 'functrace', 'hashall', 'histexpand', 'history', 'ignoreeof', 'interactivecomments',
  'keyword', 'monitor', 'noclobber', 'noexec', 'noglob', 'nolog', 'notify', 'nounset', 'onecmd', 'pipefail', 'verbose', 'vi', 'xtrace',
  // dash `set -o`: the rest of its list is above; `stdin` and `debug` are not inert (the input source, the debug hooks)
  // zsh `set -o` / setopt: the error, tracing and scoping options
  'errreturn', 'evallineno', 'localoptions', 'localtraps', 'localloops', 'localpatterns', 'warncreateglobal', 'warnnestedvar', 'typesetsilent',
  'typesettounset', 'printexitvalue', 'printeightbit', 'continueonerror', 'debugbeforecmd', 'sourcetrace', 'trapsasync', 'singlecommand',
  // zsh: clobbering, which the guard reads as a write either way
  'clobber', 'clobberempty', 'appendcreate', 'histallowclobber', 'multios',
  // zsh: history (banghist is not: history expansion rewrites later words)
  'appendhistory', 'extendedhistory', 'histexpiredupsfirst', 'histfcntllock', 'histfindnodups', 'histignorealldups', 'histignoredups',
  'histignorespace', 'histlexwords', 'histnofunctions', 'histnostore', 'histreduceblanks', 'histsavebycopy', 'histsavenodups',
  'histsubstpattern', 'histverify', 'histbeep', 'incappendhistory', 'incappendhistorytime', 'sharehistory', 'cshjunkiehistory',
  // zsh: prompts, completion, listing and the line editor (interactive machinery)
  'promptbang', 'promptcr', 'promptpercent', 'promptsp', 'promptsubst', 'transientrprompt', 'alwayslastprompt', 'alwaystoend', 'autolist',
  'automenu', 'autoparamkeys', 'autoparamslash', 'autoremoveslash', 'bashautolist', 'completealiases', 'completeinword', 'listambiguous',
  'listbeep', 'listpacked', 'listrowsfirst', 'listtypes', 'menucomplete', 'recexact', 'correct', 'correctall', 'dvorak', 'singlelinezle',
  'zle', 'overstrike', 'sunkeyboardhack', 'flowcontrol', 'beep', 'combiningchars', 'multibyte',
  // zsh: command hashing and job control
  'hashcmds', 'hashdirs', 'hashexecutablesonly', 'hashlistall', 'pathdirs', 'pathscript', 'autocontinue', 'autoresume', 'bgnice',
  'checkjobs', 'checkrunningjobs', 'hup', 'longlistjobs', 'mailwarning', 'posixjobs', 'posixtraps', 'posixargzero',
  // zsh: syntax choices that move no path
  'bsdecho', 'bashrematch', 'rematchpcre', 'casematch', 'cbases', 'octalzeroes', 'forcefloat', 'cprecedences', 'ksharrays',
  'kshzerosubscript', 'kshoptionprint', 'kshtypeset', 'kshautoload', 'functionargzero', 'shortloops', 'shortrepeat', 'cshjunkieloops',
  'cshnullcmd', 'shnullcmd', 'nomatch', 'badpattern', 'numericglobsort', 'markdirs', 'rcs', 'globalrcs', 'login', 'globalexport',
  'shwordsplit', 'rmstarsilent', 'rmstarwait', 'cdsilent', 'pushdsilent', 'pushdignoredups', 'pushdminus',
]);
const INERT_SHOPT = new Set([
  'assocexpandonce', 'checkhash', 'checkjobs', 'checkwinsize', 'cmdhist', 'compat31', 'compat32', 'compat40', 'compat41', 'compat42',
  'compat43', 'compat44', 'completefullquote', 'execfail', 'extdebug', 'extquote', 'forcefignore', 'gnuerrfmt', 'histappend', 'histreedit',
  'histverify', 'hostcomplete', 'huponexit', 'inheriterrexit', 'interactivecomments', 'lithist', 'localvarinherit', 'localvarunset',
  'loginshell', 'mailwarn', 'noemptycmdcompletion', 'nocasematch', 'noexpandtranslation', 'patsubreplacement', 'progcomp', 'progcompalias',
  'promptvars', 'shiftverbose', 'varredirclose', 'xpgecho',
]);
const normalizeOption = (name) => name.toLowerCase().replace(/[_-]/g, '');
function inertOption(name, table) {
  const n = normalizeOption(name);
  return table.has(n) || (n.startsWith('no') && table.has(n.slice(2)));
}
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
  return { operands, targetDir, noTargetDir };
}

// cp / mv / install / ln: the last operand is the destination, unless -t DIR names the directory;
// a destination that is an existing directory receives each source under its own name. A glob
// operand is expanded first, as the shell expands it before the command sees its operands. A
// link is one directory entry whatever it points at: ln names its link and walks no source.
// Returns { targets } or { unknown } (an option the table does not know, for the caller to refuse).
function copyTargets(args, cwd, verb) {
  const land = (s, d) => (verb === 'ln' ? [d] : landing(s, d, cwd));
  const parsed = parseCopyOptions(args, verb);
  if (parsed.unknown) return { unknown: parsed.unknown };
  if (parsed.installDir) return { targets: [] };   // directories made, no file written
  const { operands, targetDir: targetDirRaw, noTargetDir } = parsed;
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
    for (const s of expanded) out.push(...land(s, word(path.join(targetDir.text, path.basename(s.text)), s.literal, s.raw, { at: targetDir.text })));
    return { targets: out };
  }
  if (expanded.length < 2) return { targets: out };
  const dst = expanded[expanded.length - 1];
  if (!dst.literal) return { targets: [dst] };
  const resolved = literalPath(dst.text, cwd);
  let isDir = false;
  if (!noTargetDir && resolved) { try { isDir = fs.statSync(resolved).isDirectory(); } catch { isDir = /\/$/.test(dst.text); } }
  if (isDir) {
    for (const s of expanded.slice(0, -1)) out.push(...land(s, word(path.join(dst.text, path.basename(s.text)), s.literal, s.raw, { at: dst.text })));
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

// Paths a python or node script opens for writing, read off its text. Only a literal path with a
// write mode counts: open('x', 'w'), open('x', mode='a'), open('x', encoding='utf8', mode='w'),
// open(mode='w', file='x'), Path('x').open('w'), Path('x').write_text(...), shutil.copy(src, 'x');
// fs.writeFileSync('x', ...), appendFile, createWriteStream, openSync('x', 'w'), copyFile(src, 'x'),
// rename(src, 'x'). A call's arguments may span lines, as a formatter wraps them in a heredoc
// script. A path that is a template or an f-string with an expression is not literal and is
// skipped, as is a call whose arguments the scan cannot read (a nested call).
const PY_OPEN = /\b(?:io\.)?open\(([^()]*)\)/g;
const PY_PATH_OPEN = /\bPath\(\s*(['"])([^'"\n]+)\1\s*\)\s*\.open\(([^()]*)\)/g;
const PY_PATH_WRITE = /\bPath\(\s*(['"])([^'"\n]+)\1\s*\)\s*\.write_(?:text|bytes)\(/g;
const PY_SHUTIL = /\bshutil\.(?:copy|copyfile|copy2|move)\(\s*[^,()\n]+,\s*(['"])([^'"\n]+)\1/g;
const NODE_WRITE = /\b(?:writeFile|writeFileSync|appendFile|appendFileSync|createWriteStream|truncate|truncateSync)\(\s*(['"`])([^'"`\n$]+)\1/g;
const NODE_OPEN = /\b(?:open|openSync)\(\s*(['"`])([^'"`\n$]+)\1\s*,\s*(['"`])([rwaxs+]*)\3/g;
const NODE_COPY = /\b(?:copyFile|copyFileSync|rename|renameSync|cp|cpSync)\(\s*(['"`])[^'"`\n]*\1\s*,\s*(['"`])([^'"`\n$]+)\2/g;

// A python call's argument list, as { positional: [...], keyword: { name: text } }, each value
// the source text; commas inside quotes do not split.
function pyArgs(list) {
  const parts = [];
  let cur = '';
  let q = null;
  for (const ch of list) {
    if (q) { cur += ch; if (ch === q) q = null; continue; }
    if (ch === "'" || ch === '"') { q = ch; cur += ch; continue; }
    if (ch === ',') { parts.push(cur); cur = ''; continue; }
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
  const m = String(text == null ? '' : text).match(/^\s*(['"])([^'"\n]*)\1\s*$/);
  return m ? m[2] : null;
}
const PY_WRITE_MODE = /[wax+]/;

export function scriptWriteTargets(kind, text) {
  const out = [];
  const t = String(text);
  if (kind === 'python') {
    for (const m of t.matchAll(PY_OPEN)) {
      const { positional, keyword } = pyArgs(m[1]);
      const file = pyString(keyword.file != null ? keyword.file : positional[0]);
      const mode = pyString(keyword.mode != null ? keyword.mode : (keyword.file != null ? positional[0] : positional[1]));
      if (file && mode != null && PY_WRITE_MODE.test(mode)) out.push(file);
    }
    for (const m of t.matchAll(PY_PATH_OPEN)) {
      const { positional, keyword } = pyArgs(m[3]);
      const mode = pyString(keyword.mode != null ? keyword.mode : positional[0]);
      if (mode != null && PY_WRITE_MODE.test(mode)) out.push(m[2]);
    }
    for (const m of t.matchAll(PY_PATH_WRITE)) out.push(m[2]);
    for (const m of t.matchAll(PY_SHUTIL)) out.push(m[2]);
  } else if (kind === 'node') {
    for (const m of t.matchAll(NODE_WRITE)) out.push(m[2]);
    for (const m of t.matchAll(NODE_OPEN)) if (/[wa+]/.test(m[4])) out.push(m[2]);
    for (const m of t.matchAll(NODE_COPY)) out.push(m[3]);
  }
  return out.filter((p) => !/[{}$]/.test(p));
}

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
// the gap is none: there is no form of assignment that does not spell the name.
const EXPANDED_NAMES = ['HOME'];
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
  const setUnknown = (why) => { unknownDir = true; if (!unknownWhy) unknownWhy = why; };
  const setKnown = (d) => { dir = d; unknownDir = false; unknownWhy = null; };
  // Class D (2026-09-19): a leading `~/`, `$HOME/` or `${HOME}/` expands through os.homedir(), but a
  // command can reassign HOME before the write (`HOME=notes; > $HOME/seed.md` from a tracked project put
  // the write in a tracked folder while the guard read the real home). Since the third pass (rule (a)) the
  // trigger is the bare identifier HOME anywhere in the command outside an expansion (bareExpandedNames),
  // not a list of assignment forms; when it appears, the home the guard read may not be the one the shell
  // uses, so a word that expanded it (marked 'h') is a target the hook cannot read, and a `cd` to such a
  // word, or a bare `cd`, leaves the directory unknown, for the whole command.
  const homeAssigned = ctx.homeAssigned || bareExpandedNames(segments).has('HOME');
  const homeWord = (w) => !!(homeAssigned && w && w.marks && w.marks.includes('h'));
  const HOME_UNKNOWN = 'the command names HOME outside an expansion, so it may reassign HOME before this runs and `~` and `$HOME` name a directory I cannot read';
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
  const markMutated = (abs, verb) => { if (abs) mutated.push({ prefix: abs.replace(/\/+$/, ''), verb }); };
  const underMutated = (abs) => mutated.find((m) => abs === m.prefix || abs.startsWith(m.prefix + '/')) || null;
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
      if (ops.length >= 2) markMutated(abs(ops[1]), 'link');
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
      if (parsed.targetDir && parsed.targetDir.literal) { for (const s of parsed.operands) markMutated(literalPath(path.join(parsed.targetDir.text, path.basename(s.text)), cwd), 'ln'); return; }
      const ops = parsed.operands;
      if (ops.length >= 2) markMutated(abs(ops[ops.length - 1]), 'ln');
      else if (ops.length === 1) markMutated(literalPath(path.join(cwd, path.basename(ops[0].text)), cwd), 'ln');   // ln src -> ./basename
      return;
    }
    if (name === 'cp') {
      const parsed = parseCopyOptions(args, 'cp');
      if (parsed.unknown) { markAllCandidates('cp'); return; }
      const linky = args.some((a) => a.literal && ((/^-[^-]/.test(a.text) && (a.text.includes('l') || a.text.includes('s'))) || a.text === '--link' || a.text === '--symbolic-link'));
      if (!linky || parsed.installDir) return;
      if (parsed.targetDir && parsed.targetDir.literal) { for (const s of parsed.operands) markMutated(literalPath(path.join(parsed.targetDir.text, path.basename(s.text)), cwd), 'cp -l'); return; }
      const ops = parsed.operands;
      if (ops.length >= 2) markMutated(abs(ops[ops.length - 1]), 'cp -l');
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
      if (!srcAbs || underMutated(dstAbs) || underMutated(srcAbs)) { markMutated(dstAbs, 'ln -s'); return; }   // rule (c): the name is unknown
      links.set(dstAbs, srcAbs);
    };
    if (parsed.targetDir) {
      if (!parsed.targetDir.literal) return;   // the ln's own target, refused by copyTargets
      const dirAbs = literalPath(parsed.targetDir.text, cwd);
      for (const s of parsed.operands) {
        if (s.literal) record(s, literalPath(path.join(parsed.targetDir.text, path.basename(s.text)), cwd));
        else markMutated(dirAbs, 'ln -s');   // the link's name is the source's basename, which the hook cannot read: the folder is unknown
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
        else markMutated(dstAbs, 'ln -s');
      }
      return;
    }
    if (parsed.operands.length === 2) record(parsed.operands[0], dstAbs);
    else markMutated(dstAbs, 'ln -s');   // several sources into a name that is not a directory: ln fails or the name is unknown
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
    if (homeAssigned && w.marks && w.marks.includes('h')) { cannotRead(word(w.raw, false, w.raw), how, { kind: 'homeAssigned' }); return; }
    if (w.glob) {
      // every match, as the shell names each (a redirection onto several: zsh's multios writes each, bash
      // writes none and says so, so the over-count costs a command bash refuses anyway); no match, the cwd
      // unknown or past the caps is a target the hook cannot read (2026-09-18)
      const m = expandGlob(w, unknownDir ? null : dir);
      if (m && m.length) for (const x of m) add(x, how);
      else cannotRead(w, how);
      return;
    }
    if (!w.literal) { cannotRead(w, how); return; }
    if (!w.text) return;
    // a literal relative target whose directory is not known is refused, not dropped (round 3): the same word
    // spelled absolute is judged, and one `cd` the hook could not follow turned a refused write into an allowed one
    if (!path.isAbsolute(w.text) && unknownDir) { cannotRead(w, how, { kind: 'unknownDir', text: unknownWhy }); return; }
    // class 'mutated' (the walk-around lens second pass, family 3): a later literal target under a prefix an earlier rm/mv/ln/cp -l/cp -s touched
    // is unreadable, since what it resolves to at run time is not what the hook sees now.
    if (mutated.length && !unknownDir) {
      const abs = path.isAbsolute(w.text) ? w.text : dir + '/' + w.text;
      const m = underMutated(path.normalize(abs));
      if (m) { cannotRead(w, how, { kind: 'mutated', verb: m.verb, prefix: m.prefix }); return; }
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
  const recurse = (text, sh = shell) => {
    if (depth >= RECURSION_CAP) { sawOpaqueCommand = true; return; }
    const sub = extract(text, { dir, unknownDir, unknownWhy, shell: sh, depth: depth + 1, homeAssigned, links, cdFunctions, mutated });
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
  const CLOSERS = { fi: ['if'], done: ['while', 'until', 'for'], esac: ['case'] };
  const isScope = (f) => f.kind === 'subshell' || f.kind === 'function';
  const restore = (f) => { ({ dir, unknownDir, unknownWhy } = f); };
  const closeSubshell = () => {
    for (let j = frames.length - 1; j >= 0; j--) {
      if (frames[j].kind === 'case' || frames[j].kind === 'function') return;   // in a case body a ) ends a pattern
      if (frames[j].kind === 'subshell') { restore(frames[j]); frames.length = j; return; }
    }
  };
  const closeCompound = (kinds) => {
    for (let j = frames.length - 1; j >= 0 && !isScope(frames[j]); j--) {
      if (!kinds.includes(frames[j].kind)) continue;
      if (frames.slice(j).some((f) => f.moved)) setUnknown('an earlier `cd` sits in an if, loop or case body that may not run');
      frames.length = j;
      return;
    }
  };
  const movedHere = () => {
    for (let j = frames.length - 1; j >= 0 && !isScope(frames[j]); j--) frames[j].moved = true;
  };
  activeLinks = links;   // foldSegments follows these while this command's literal targets resolve (the walk-around lens second pass)
  // The braces of a function body: the frame closes, restoring the dir, when its depth returns to 0.
  const braces = (seg) => {
    const f = frames[frames.length - 1];
    if (!f || f.kind !== 'function') return;
    if (f.depth === 0 && !(seg.words.length && seg.words[0].text === '{')) { frames.pop(); return; }   // a body without braces: not followed
    for (const w of seg.words) {
      if (w.text === '{') f.depth++;
      else if (w.text === '}') f.depth--;
    }
    if (f.depth <= 0) { if (f.bodyMoved && f.name) cdFunctions.add(f.name); restore(f); frames.pop(); }
  };
  for (let idx = 0; idx < segments.length; idx++) {
    const seg = segments[idx];
    if (seg.paren === '(') {
      const next = segments[idx + 1];
      const prev = segments[idx - 1];
      const named = prev && prev.op === '(' && (prev.words.length === 1 || (prev.words.length === 2 && prev.words[0].text === 'function'));
      if (next && next.paren === ')' && named) {
        const fname = prev.words.length === 1 ? prev.words[0].text : prev.words[1].text;
        frames.push({ kind: 'function', name: fname, bodyMoved: false, dir, unknownDir, unknownWhy, depth: 0 });   // name() ... : a definition, not a run
        idx++;
        continue;
      }
      frames.push({ kind: 'subshell', dir, unknownDir, unknownWhy });
      continue;
    }
    if (seg.paren === ')') { closeSubshell(); continue; }
    braces(seg);
    for (const r of seg.redirects) if (WRITE_REDIRECTS.has(r.op)) add(r.target, `${r.op} redirection`);   // a glob: every match (add)
    for (const inner of seg.subs) recurse(inner);
    const head = seg.words.length ? seg.words[0].text : '';
    if (head in CLOSERS) closeCompound(CLOSERS[head]);
    else if (head === 'if' || head === 'while' || head === 'until' || head === 'for' || head === 'case') frames.push({ kind: head, moved: false });
    const cmd = commandOf(seg.words);
    if (!cmd) continue;
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
      continue;
    }
    if ('script' in cmd) {   // `flock … -c 'string'` runs the string through `$SHELL -c`, read like `sh -c` (round 4)
      if (cmd.script && cmd.script.literal) recurse(cmd.script.text);
      else if (cmd.script) sawOpaqueCommand = true;
      continue;
    }
    const { args } = cmd;
    let { name } = cmd;
    if (/^(python[0-9.]*|pypy[0-9]*)$/.test(name)) name = 'python';
    else if (name === 'nodejs') name = 'node';
    // rule (d) (the third pass): a shell option not on the inert allowlist leaves the directory unknown from here
    if (name === 'set' || name === 'shopt' || name === 'setopt' || name === 'unsetopt') {
      const why = shellOptionChange(name, args);
      if (why) { setUnknown(why); movedHere(); }
    }
    // the walk-around lens second pass (family 6): a call to a function whose body moved the shell moves the cwd, which the guard does not
    // follow into the call, so the directory is unknown from here (the body was modelled as not moving the shell)
    if (cdFunctions.has(name)) setUnknown(`an earlier call of the function \`${name}\` may change the directory, which I do not follow`);
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
      if (homeWord(c.word)) { setUnknown(`an earlier \`${c.flag} ${c.word.raw}\` goes through HOME, and ${HOME_UNKNOWN}`); continue; }
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
        else if (seg.op === '|' || prevOp === '|') block = `an earlier \`${name}\` is part of a pipeline, so it runs in a subshell and moves nothing in this shell`;
        else if (seg.op === '&') block = `an earlier \`${name}\` is backgrounded, so it runs in a subshell and moves nothing in this shell`;
        else if (cmd.wrapped) block = `an earlier \`${name}\` runs under a wrapper, an external \`${name}\` that does not exist, so the shell does not move`;
        else if (pushdN) block = 'an earlier `pushd -n` pushes a directory without changing to it';
        else if (rotate) block = 'an earlier `pushd` rotates the directory stack, so where it lands is not known';
        else if (physical) block = `an earlier \`${name}\` resolves \`..\` physically (\`-P\`, or an option I do not model), so where it lands is not known`;
        else if (unmodeled) block = `an earlier \`${name}\` carries an option I do not model, so where it lands is not known`;
        let a = args.find((w) => !w.text.startsWith('-') || w.text === '-');
        if (a && a.glob) {   // cd docs/*: one match is the directory; several, or none, leave it unknown
          const m = expandGlob(a, unknownDir ? null : dir);
          a = m && m.length === 1 ? m[0] : word(a.text, false, a.raw, { marks: a.marks });
        }
        // a bare `cd`, or a `cd ~/x`, goes to HOME: a directory the guard cannot read once the command names HOME (rule (a))
        if (!a) { if (block) setUnknown(block); else if (homeAssigned) setUnknown(`an earlier bare \`${name}\` goes to HOME, and ${HOME_UNKNOWN}`); else setKnown(os.homedir()); }
        else if (a.text === '-') setUnknown(`an earlier \`${name} -\` returns to a directory this command did not set`);
        else if (homeWord(a)) setUnknown(`an earlier \`${name} ${a.raw}\` goes through HOME, and ${HOME_UNKNOWN}`);
        else if (!a.literal) setUnknown(`an earlier \`${name}\` names ${a.raw}, a directory the shell fills in when the command runs`);
        else {
          const to = resolveAgainst(a.text, unknownDir ? null : dir);
          if (to == null) setUnknown(`an earlier \`${name}\` follows one I could not read`);
          else if (!enterable(to)) {
            // the shell stays put when a cd fails, so a relative write after it lands where the command started;
            // a directory the command makes first (`mkdir -p x && cd x`) is not there when the hook runs either
            // (round 3; the cost is stated in decision 47)
            dir = to;
            setUnknown(`an earlier \`${name} ${a.raw}\` names a directory the command cannot enter when I check it (it may be made first, or the cd may fail and the write land where the command started)`);
          } else if (block) setUnknown(block);   // the walk-around lens second pass: a clean move the guard cannot rely on
          else setKnown(to);
        }
        movedHere();
        if (a && a.literal && a.text !== '-') markFunctionBody();   // a real cd in a function body moves it when called
        break;
      }
      case 'popd': setUnknown('an earlier `popd` returns to a directory this command did not set'); movedHere(); break;
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
          if (kind === 'python' && /^-[WX]./.test(a.text)) continue;   // -Xutf8, -Wignore: an option with its value glued on
          if (kind === 'python' && /^-[A-Za-z]*c$/.test(a.text)) { inline = args[k + 1] || null; stdin = false; break; }
          if (kind === 'node' && (a.text === '-e' || a.text === '--eval' || a.text === '-p' || a.text === '--print')) { inline = args[k + 1] || null; stdin = false; break; }
          if (a.text === '-') break;   // stdin, said so
          if (kind === 'python' && a.text === '-m') { stdin = false; break; }   // a module
          if (INTERPRETER_OPERANDS[kind].has(a.text)) { k++; continue; }
          if (a.text.startsWith('-')) continue;
          stdin = false;   // a script file: its contents are not in the command
          break;
        }
        if (inline) {
          if (inline.literal) for (const p of scriptWriteTargets(kind, inline.text)) add(word(p, true, p), `${kind} script`);
          else sawOpaqueCommand = true;
        } else if (stdin) {
          for (const body of stdinBodies(idx)) for (const p of scriptWriteTargets(kind, body)) add(word(p, true, p), `${kind} script`);
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
  activeLinks = prevLinks;
  return { targets, opaque: opaque || sawOpaqueCommand, unresolved };
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

const TRACK_EDIT = '  node ~/.claude/hooks/track-edit.mjs --file "<the file>" --old "<exact unique text>" --new "<replacement>"';

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
  let targets;
  let unresolved;
  try { ({ targets, unresolved } = extractWriteTargets(command, cwd)); }
  catch (e) { return isUnknownPath(e) ? statErrorRefusal(e.why && e.why.how ? e.why.how : 'write', e.why && e.why.raw ? e.why.raw : 'the path', e) : null; }
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
      + `Make the change with track-edit instead, which records it for me to accept or reject:\n`
      + `  node ~/.claude/hooks/track-edit.mjs --file "${t.path}" --old "<exact unique text>" --new "<replacement>"`;
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
  for (const u of unresolved) {
    let hit = null;
    try { hit = inPlayFor(u, cwd, memo); }
    catch (e) { if (isUnknownPath(e)) return statErrorRefusal(u.how, u.raw, e); hit = null; }
    if (!hit) continue;
    if (hit.literal) {
      // a numeric target whose fold leaves no expansion, or whose number could spell an entry that exists, lands on
      // a tracked file the literal rule knows (round 3)
      return `Track-changes is ON for ${hit.literal}, so this command is blocked here: its ${u.how} names ${u.raw}, and that lands `
        + `on ${hit.literal} (a \`..\` in it climbs from a link, or the shell's number could spell an entry that exists there), so the `
        + `${u.how} would write the file silently, with no change for me to accept or reject. Make the change with track-edit instead, `
        + `which records it for me to accept or reject:\n`
        + `  node ~/.claude/hooks/track-edit.mjs --file "${hit.literal}" --old "<exact unique text>" --new "<replacement>"`;
    }
    const where = hit.fromEnv ? 'the project TRACKCHANGES_ROOT names' : hit.root;
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
      return `This command is blocked here: its ${u.how} names ${u.raw}, but the command names HOME outside an expansion (an `
        + `assignment, a declaration, a nameref, a read or an argument that could reassign it), so it may reassign HOME before this `
        + `runs and \`$HOME\` and \`~\` no longer name a directory I can read (I read my own home, never a variable the command sets). `
        + `I cannot tell which file the write lands in, and ${where} tracks files whose changes are recorded for me to accept `
        + `or reject. Spell the path out: outside that project the command then runs as usual, and a tracked file takes its `
        + `change through track-edit instead:\n${TRACK_EDIT}`;
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
    return `Track-changes is ON in ${where}, so this command is blocked here: its ${u.how} names ${u.raw}, `
      + `which is not a literal path${entry}. The shell fills that in when the command runs, so I cannot tell which `
      + `file it would write, and a tracked file written that way would carry no change for me to accept or `
      + `reject. Spell the path out: outside that project the command then runs as usual, and a tracked file `
      + `takes its change through track-edit instead:\n${TRACK_EDIT}`;
  }
  return null;
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
    try { reason = evaluate(raw); } catch { reason = null; }
    if (reason) { process.stderr.write(reason + '\n'); process.exit(2); }
    process.exit(0);
  });
}
