// The shared module of the Bash-side track guard's tests (hooks/romp-track-bash-guard.mjs; plans/file-review.md, decision 47).
// Two test files import it: tools/romp-track-bash-guard.test.mjs, the grammar and the process, and
// tools/romp-track-bash-guard-rows.test.mjs, the after-source fixes' rows test and THE ASSIGNING HEAD's census. The two tests
// were the main file's last, the rows test among its slowest, and node --test runs the files of a run side by side but the tests
// of one file one after another, so they have a file of their own (fork PR 975, before its round 2: CI's vendored-tooling job had
// come within minutes of its cap). What both files need is here, moved from the main file unchanged and imported, never copied: THE PROBE'S
// RUN (the one binding of node's child_process and the wrappers that check every spawn), THE ONE PRESENCE FUNCTION and THE
// OVERRIDE, the shell probe and shellsFor, THE INVOKED PROGRAM's gate, NO STARTUP FILE OF THE ACCOUNT'S and THE CLEARED
// ENVIRONMENT, the checked spawnSync, the sixth pass's world and its legs. Importing the module registers the scratch project's
// beforeEach and afterEach on the importing file's tests, as they were registered when this code opened the main file. The name
// does not match *.test.mjs, so node --test runs no test of its own here.

import { beforeEach, afterEach } from 'node:test';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawn as rawSpawn, spawnSync as rawSpawnSync } from 'node:child_process';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';

// THE PROBE'S RUN (round 7 of fork PR #780 review, thirty-third commit; by construction since the thirty-fourth). A probe of THE
// REFUSING PROGRAM runs with a fourth pipe, so its run ends only when every process holding one of its pipes has exited. The thirty-third
// commit knew a probe by its exact text among a spawn's arguments, and the round's verifiers ran one with three pipes past it four ways,
// every pin green: the probe on the standard input of a shell's -s (X4s), the probe as the command of spawnSync's shell option (X4h), a
// newline after it (X4p), and a second binding of child_process (X4e), which the source pin, reading the `node:child_process` spelling
// alone, did not see. The class is every run of a probe without the fourth pipe, whatever starts it: an argument, the standard input, a
// shell option, an environment value, a script file, any binding of child_process, any program. So the probe refuses itself: probeOf
// opens every probe with PROBE_GUARD, a line under which the shell runs nothing more unless its descriptor 3 is a socket (node makes each
// pipe of a spawn a socket pair, the fourth among them); otherwise it prints PROBE_GUARD_LINE on stderr and exits 125, so the command is
// never run, no recorded refusal shape takes that stderr (condition (ii)), and the real-programs test names it at its call site. And
// earlier, before any process starts: this file's spawnSync, its raw binding (_spawnSync) and its spawn throw by name for a spawn any of
// whose texts (the command, each argument, the standard input as a string or bytes, each value of the environment it is given, argv0)
// holds PROBE_GUARD, unless its fourth descriptor is a pipe or it is the parse check (bash's, zsh's or dash's own -n words, which run
// nothing, the probe their last word and held by no other text, no shell option). The source pin holds child_process to the one import;
// a binding it cannot read (a specifier computed at run time) meets the probe's own guard. What the guard reads is a socket at descriptor
// 3, which the fourth pipe is: a spawn that hands descriptor 3 some other socket passes it (inheriting this process's descriptor 3 hands
// none: in a test process it is the event loop's epoll, measured).
const PROBE_GUARD_LINE = "THE PROBE'S RUN: this probe ran without the fourth pipe, so it runs nothing";
const PROBE_GUARD = `[ -S /dev/fd/3 ] || { echo "${PROBE_GUARD_LINE}" >&2; exit 125; }`;
const splitSpawnArgs = (rest) => (rest.length && !Array.isArray(rest[0]) && rest[0] !== undefined ? [[], rest[0]] : rest);   // (cmd, [args], [options])
// every text a spawn hands a program: its command, each string argument, the standard input (a string or bytes), each value of the
// environment it is given, and argv0
const spawnTexts = (cmd, args, opts) => {
  const o = opts || {};
  const input = typeof o.input === 'string' ? [o.input] : ArrayBuffer.isView(o.input) ? [Buffer.from(o.input.buffer, o.input.byteOffset, o.input.byteLength).toString('utf8')] : [];
  return [String(cmd), ...(Array.isArray(args) ? args : []).filter((a) => typeof a === 'string'), ...input, ...Object.values(o.env || {}).filter((v) => typeof v === 'string'), ...(typeof o.argv0 === 'string' ? [o.argv0] : [])];
};
const refusePipelessProbe = (cmd, args, opts) => {
  const held = spawnTexts(cmd, args, opts).filter((t) => t.includes(PROBE_GUARD));
  if (!held.length) return;
  const o = opts || {};
  const a = Array.isArray(args) ? args : [];
  const base = path.basename(String(cmd));
  if (!o.shell && ['bash', 'zsh', 'dash'].includes(base) && held.length === 1 && held[0] === a[a.length - 1] && JSON.stringify(a) === JSON.stringify(parseArgv(base, held[0]))) return;   // the parse check: read, not run
  if (Array.isArray(o.stdio) && o.stdio.length >= 4 && o.stdio[3] === 'pipe') return;
  throw new Error(`THE PROBE'S RUN: a probe of THE REFUSING PROGRAM ran without the fourth pipe, so the run could end before a command its program detached had exited; run it through runProbe: ${String(cmd)} ${JSON.stringify(held[0]).slice(0, 200)}`);
};
const _spawnSync = (cmd, ...rest) => { refusePipelessProbe(cmd, ...splitSpawnArgs(rest)); return rawSpawnSync(cmd, ...rest); };
const spawn = (cmd, ...rest) => { refusePipelessProbe(cmd, ...splitSpawnArgs(rest)); return rawSpawn(cmd, ...rest); };

import * as guard from '../hooks/romp-track-bash-guard.mjs';

// a namespace import, so a run of either test file against an older hook (the red-on-base check) reports each test on its own
// rather than failing the whole file on a missing export
const { evaluate, extractWriteTargets, scriptWriteTargets, scriptTemplateTargets, lex, INERT_OPTIONS } = guard;

const HOOK = fileURLToPath(new URL('../hooks/romp-track-bash-guard.mjs', import.meta.url));
const ROMP_SID = '11111111-2222-3333-4444-555555555555';
const PNG = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, 0, 0, 0, 0x0d]);

let proj;       // the scratch project: .trackchanges/ at its root, tracked docs/report.md, notes/, figs/plot.png
let report;     // proj/docs/report.md, tracked text
let other;      // proj/docs/other.md, untracked

beforeEach(() => {
  proj = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'romp-bash-guard-')));
  for (const d of ['.trackchanges', 'docs', 'base', 'notes', 'figs']) fs.mkdirSync(path.join(proj, d));
  fs.writeFileSync(path.join(proj, '.trackchanges', 'config.json'),
    JSON.stringify({ v: 2, tracked: ['docs/report.md', 'notes/', 'figs/plot.png'] }));
  report = path.join(proj, 'docs', 'report.md');
  other = path.join(proj, 'docs', 'other.md');
  fs.writeFileSync(report, 'The api session cut tail latency by 40%.\n');
  fs.writeFileSync(other, 'untracked prose\n');
  fs.writeFileSync(path.join(proj, 'base', 'report.md'), 'an older copy\n');
  fs.writeFileSync(path.join(proj, 'figs', 'plot.png'), PNG);
  delete process.env.TRACKCHANGES_ROOT;
});

afterEach(() => {
  try { fs.rmSync(proj, { recursive: true, force: true }); } catch { /* ignore */ }
});

const payload = (command, cwd = proj, tool = 'Bash') => JSON.stringify({ tool_name: tool, tool_input: { command }, cwd });
const ROMP_NOUNS = /\b(romp|card|board|column|goal|nudge|dashboard|panel|viewer|dismiss\w*|cleared)\b/i;

// THE ONE PRESENCE FUNCTION and THE OVERRIDE (round 7 of fork PR #780 review, fiftieth commit; the reviewer's conditions on CI run
// 36109232805, 2026-09-25). Every check of whether this machine has a program goes through presenceOf: the shell probe below, the named
// programs, THE INVOKED PROGRAM's gate (at namedPresent), and the rows tests' own program checks (toolPresent, hasProgram). The real check
// comes first: a path by its existence and its exec bit (a relative path from the leg's cwd), a name by a PATH lookup, or the record a caller
// measured (the shell probe's spawn, which also reads bash's version). This box cannot make /usr/bin/zsh absent without elevated
// privileges, and its runs never use them: by name, absence is reproduced for real (a PATH of links to every program but the hidden ones,
// the round's runner-env-node.sh), and by path only through THE OVERRIDE, ROMP_TEST_ABSENT_PROGRAMS, read here and nowhere else: names
// separated by blanks or commas, each a program this machine has that the run treats as absent, a path counting as absent when its last
// component is listed. It applies only where the real check found the program present, so every NOT RUN line names its source: "is not on
// this runner" (the real check, by the probe's spawn or the PATH lookup) or "is not on this runner (no executable file at that path)" (the
// real filesystem check), against "is treated as absent by the test override ROMP_TEST_ABSENT_PROGRAMS, which lists zsh (present on this
// machine)". The override is a disclosed box-side reproduction only and NEVER WHAT CI RELIES ON: a pin at the end of tools/romp-track-bash-guard.test.mjs reds when it
// is set while GITHUB_ACTIONS or CI is, so CI's green for a row that runs a program by its path rests on the runner's real filesystem check.
const ABSENT_OVERRIDE = 'ROMP_TEST_ABSENT_PROGRAMS';
const absentSet = (value, label) => ({ names: new Set(String(value || '').split(/[\s,]+/).filter(Boolean)), label });
// set while GITHUB_ACTIONS or CI is, THE OVERRIDE is refused: not read here, and the pin at the end of tools/romp-track-bash-guard.test.mjs reds on it
const overrideInCi = (env) => ((env.GITHUB_ACTIONS || env.CI) && env[ABSENT_OVERRIDE] !== undefined ? `THE OVERRIDE is set while the run is in CI (${ABSENT_OVERRIDE}=${JSON.stringify(env[ABSENT_OVERRIDE])}, ${env.GITHUB_ACTIONS ? 'GITHUB_ACTIONS' : 'CI'} set): CI's absences must come from the real check, so unset it there` : null);
const OVERRIDE_ABSENT = absentSet(overrideInCi(process.env) === null ? process.env[ABSENT_OVERRIDE] : '', `the test override ${ABSENT_OVERRIDE}`);
const isExecFile = (file) => { try { if (!fs.statSync(file).isFile()) return false; fs.accessSync(file, fs.constants.X_OK); return true; } catch { return false; } };
const BY_PATH_WHY = 'is not on this runner (no executable file at that path)';
// the real check alone: a path by its existence and exec bit (a relative one from `cwd`), a name by a lookup over `PATH` (default this process's)
const realPresence = (program, { PATH = process.env.PATH, cwd = null } = {}) => {
  if (program.includes('/')) return isExecFile(path.resolve(cwd || process.cwd(), program)) ? { ok: true, why: null } : { ok: false, why: BY_PATH_WHY };
  return String(PATH || '').split(':').some((d) => d !== '' && isExecFile(path.join(d, program))) ? { ok: true, why: null } : { ok: false, why: 'is not on this runner' };
};
// the real check (or the record `real` a caller measured), then the absent set (THE OVERRIDE, or one a pin hands in) for a program found present
const presenceOf = (program, { absent = OVERRIDE_ABSENT, real = null, PATH, cwd } = {}) => {
  const r = real || realPresence(program, { PATH, cwd });
  if (!r.ok) return r;
  const base = program.slice(program.lastIndexOf('/') + 1);
  return absent.names.has(base) ? { ...r, ok: false, why: `is treated as absent by ${absent.label}, which lists ${base} (present on this machine)`, source: 'absent set' } : r;
};

// The shells this runner has, through ONE probe. Every real-shell evidence leg of the two test files asks shellsFor for the shells it
// wants: a shell that is missing, or present but below the version floor the legs need, is reported LOUDLY on stderr, once per
// leg with the leg's line, and its leg does not run; it never passes in silence and never reds with a value mismatch (the
// seventh pass's addendum, item 4, 2026-09-19: CI's shell job has no zsh and failed on unguarded zsh legs at 50e85deec; round 5,
// 2026-09-20: two dash legs sat outside the probe, one skipping its assertion in silence and one throwing a bare TypeError, the
// bash legs ran outside it too, and a bash that starts but is too old declined with a value-mismatch red, since the probe asked
// only whether the shell starts: 48 lines of the test file spelled a bash 4.x construct then, `declare -n` the newest at 4.3, counted by
// grep -c -E "declare -[a-zA-Z]*[nlugA]|typeset -[a-zA-Z]*[nlug]|mapfile|readarray|\|&" over its non-comment lines, and the
// CI vendored-tooling job's macOS cell ships bash 3.2.57). Every spawn of a shell in either test file goes through the `spawnSync` wrapper below,
// which throws by name when the probe declined that shell, so a leg that reaches a shell without asking shellsFor is a loud red
// naming the shell, whatever its list is called or how it loops, never a silent run and never a red naming nothing.
// The refusable case is run by hand with a `zsh` stub that exits 1 first on PATH: each file passes and prints its NOT RUN lines.
const SHELL_FLOOR = { bash: [4, 3] };   // bash 4.3 for `declare -n`; nothing here needs a zsh or dash newer than the oldest CI build
// The probe reads no startup file of the account's (round 7 of fork PR #780 review, thirty-second commit, the round's verifiers): it ran
// `zsh -c true` under the inherited environment, so zsh read ~/.zshenv and the probe ran whatever that file runs; zsh now takes -f, bash
// --norc and --noprofile, and the environment is PATH alone, so bash reads no BASH_ENV either (dash reads nothing when not interactive).
// The probe's record is the real check THE ONE PRESENCE FUNCTION starts from (the fiftieth commit), so THE OVERRIDE reaches the shells too.
const probeShell = (sh) => presenceOf(sh, { real: probeShellRun(sh) });
const probeShellRun = (sh) => {
  const r = _spawnSync(sh, sh === 'bash' ? ['--norc', '--noprofile', '-c', 'printf %s "$BASH_VERSION"'] : sh === 'zsh' ? ['-f', '-c', 'true'] : ['-c', 'true'], { encoding: 'utf8', env: { PATH: process.env.PATH } });
  if (r.status !== 0) return { ok: false, why: 'is not on this runner' };
  const floor = SHELL_FLOOR[sh];
  if (!floor) return { ok: true, why: null };
  const v = String(r.stdout || '').trim();
  const m = v.match(/^(\d+)\.(\d+)/);
  const below = !m || Number(m[1]) < floor[0] || (Number(m[1]) === floor[0] && Number(m[2]) < floor[1]);
  return below ? { ok: false, why: `is ${v || 'of a version it did not print'} on this runner, below the ${floor.join('.')} its legs need`, version: v } : { ok: true, why: null, version: v };
};
const SHELL_PROBE = Object.fromEntries(['bash', 'zsh', 'dash'].map((sh) => [sh, probeShell(sh)]));
const HAS_SHELL = Object.fromEntries(Object.entries(SHELL_PROBE).map(([sh, p]) => [sh, p.ok]));
// `present` and `report` are parameters so the line itself is pinned in-process (the seventh pass's close): a runner without a
// shell gets exactly one line per missing or too-old shell per leg, on stderr, and the leg's list without it. `present` holds,
// per shell, a boolean (present or missing) or the probe's own record (`{ ok, why }`, a too-old shell naming the version found).
const probeOk = (present, sh) => (present[sh] !== null && typeof present[sh] === 'object' ? present[sh].ok : !!present[sh]);
const probeWhy = (present, sh) => (present[sh] !== null && typeof present[sh] === 'object' && present[sh].why ? present[sh].why : 'is not on this runner');
const shellsFor = (list, what = null, present = SHELL_PROBE, report = (line) => console.error(line)) => {
  for (const sh of list) if (!probeOk(present, sh)) report(`NOT RUN: real ${sh} ${probeWhy(present, sh)}, so its evidence leg did not run${what ? `: ${what}` : ''} (${(new Error().stack.split('\n')[2] || '').trim().replace(/^at /, '')})`);
  return list.filter((sh) => probeOk(present, sh));
};
// A command can NAME a program as well as run in a shell: the consumer of a piped script (`echo '..' | zsh`), the shell of a
// `-c` or of a here-document (`zsh -c '..'`, `zsh <<EOF`), a busybox applet. The row's evidence needs that program too: on a
// box without it the present shells report "command not found", no shell writes, and a pin measured where it was present
// reads as a mismatch (round 5's fifth addendum, fourth fix-up, 2026-09-20: CI's ubuntu runner has no zsh, so 181 matrix rows
// went red there, 41 of the piped-script matrix's 60 rows naming zsh as the consumer, all 120 of the stdin-script matrix's and
// 20 of the heredoc-body matrix's 30, the rest matching because no shell wrote them with zsh present either, and 2 rows of the
// fix-ups' rows tests, while every leg RUNNING in zsh was already NOT RUN through the probe; the runner has no ksh and no
// busybox either). So a row whose command names a program this box lacks is NOT RUN by name, the same loud line
// through shellsFor, and its in-process verdict alone is compared, never a red on evidence the box cannot give and never a
// silent pass. The programs: the probe's three shells, by the probe; `sh`, `ksh` and `busybox` (the matrices' other consumers
// and the rows tests' residual rows) by THE ONE PRESENCE FUNCTION's PATH lookup (`command -v` before the fiftieth commit), the fixtures'
// own `absent` accounting.
const NAMED_PROGRAMS = ['sh', 'ksh', 'busybox'];
const NAMED_PROBE = { ...SHELL_PROBE, ...Object.fromEntries(NAMED_PROGRAMS.map((p) => [p, presenceOf(p)])) };
// the programs a command spells as words; a name glued to a path, an extension or a longer word is not one (`/bin/sh`, `x.sh`, the `sh` of `bash`)
const programsNamed = (cmd, table = NAMED_PROBE) => Object.keys(table).filter((p) => new RegExp(`(?<![\\w./-])${p}(?![\\w./-])`).test(cmd));
// THE INVOKED PROGRAM (round 7 of fork PR #780 review, fiftieth commit; the reviewer's conditions on CI run 36109232805, 2026-09-25). The
// gate keyed on the programs a command NAMES from the table above, each spelled as a bare word, so a row whose bash leg ran
// `/usr/bin/zsh --emulate sh -c '..'` passed it (a name glued to a path is none of its words) and the row's bash and dash legs ran a zsh the
// CI runner does not have: bash said "No such file or directory", no shell wrote, and the row went red (C-path-zsh-emu-nad, not ok 920),
// while every pre-push run passed on a box that has zsh. The class is every row whose command runs, from a shell's leg or behind a wrapper,
// a program the runner may lack, by name or by an absolute or relative path, whichever program it is. So the gate also derives, from the
// row's own command text, THE PROGRAM EACH COMMAND SEGMENT RUNS, and asks THE ONE PRESENCE FUNCTION whether that program is on this
// machine; a program that is not here makes the row NOT RUN with the reason, one line per program, its verdict still asserted, never a
// silent skip and never a false pass. The derivation reads the text with the hook's lexer (the segments, their words after quote removal,
// their command and process substitutions and here-documents), and per segment: the reserved words and the words a shell reads as its own
// are no program (SHELL_OWN); assignments are stepped past; a wrapper (WRAPPERS: exec, command, env, nice, timeout, xargs and the rest) is
// stepped past with its options and operands, itself a program where the walk reads it as one (WRAPPERS' comment: the walk reads `time`
// as a shell's own word only where nothing but reserved words and redirections stands before it in a segment no pipe feeds, in a text
// only bash or zsh reads, and as the program time wherever else the walk reaches it, a name the text binds or rebinds aside); the word
// after them is the program (an assignment whose
// word the lexer does not hold as literal or holds a blank, and a name, or a wrapper's path, the readings below set aside, stop the walk
// instead: THE NON-LITERAL WORDS and THE STATED LIMIT, in the class of what the derivation does not read). The texts a shell runs
// are read the same way, to a depth of eight: a shell's operands that hold a blank or an operator (its -c text, however its options are
// spelled), the here-documents and here-strings it is fed, what echo, printf or cat pipe into it or print in a process substitution it reads,
// and the texts eval, trap, emulate -c, alias (a global alias's value aside), env -S, flock -c, su -c, find -exec and capsh's `--` run, each
// as far as THE NON-LITERAL WORDS allow, and the text of mapfile -C (readarray -C), env -S, su, runuser or script -c and emulate -c only where
// its option is a word of its own (a text glued to the option, after `=` or after an option word clustering other letters is in the class
// of what the derivation does not read). The
// rows here bind and make their own programs on purpose, so three readings keep the gate to programs this machine is asked for: a name the
// command spells in a binding shape (a function, an alias, a path a hash binds it to, zsh's `=name` and its function table) is no program; a
// name the text spells in a rebinding shape is no program: the two readers take such a shape anywhere in the raw text as a binding, a
// command word or not (an echo or printf operand, a comment, a quoted string such as a grep pattern, a file spelled under a literal
// directory of a PATH the text sets), and since the fifty-sixth commit a text that rebinds one name no longer sets aside every other (THE
// REBOUND NAMES, the reviewer's ruling at 01:00Z): it sets aside an alias's name, a hashed (THE HASHED NAMES), an autoloaded or an enabled
// name, a function, command or alias table entry, the builtins of a zsh module it loads (a table measured with `zmodload -lF`), and a name
// it spells as a file under a literal directory of a PATH it sets; and a path the text also spells whole elsewhere, as a word of its own (a
// copy of cp it makes, or links, before it runs it; since the fifty-seventh commit a longer path it starts, `./tool.bak` for `./tool`, is
// no such spelling), is no program of this machine's (since the fifty-ninth commit, "elsewhere" is counted: the text spells the path whole
// more often than a first walk reads it as the program a segment runs; the first walk, like every walk, stops at a name or path the
// reading binds or rebinds, so a whole spelling behind it counts toward setting that path aside; THE WRAPPER'S PATH, at programsInvoked).
// The walk stops at
// each name these readings set aside, and at each such path that names a wrapper (on a second walk, run only where the first sets such a
// path aside), and does not step past it, so what that name or path runs is not read (below): the path reading sets a wrapper's path aside
// where the raw text spells that path whole more often than the first walk reads it as a program, and a wrapper's path these readings do
// not set aside is stepped past (the fifty-ninth commit, on the reviewer's re-verifier: the stop asked whether the text spelled a wrapper's
// path twice, which counted its program words, so `/usr/bin/env q780-no-such-program x; /usr/bin/env q780-no-such-program y` was
// measured). A spelling that is not whole, with a quote, a backslash or a glob inside the path (`/usr/bin/e''nv`), is not counted as a
// spelling (the sixtieth and sixty-first commits, on the reviewer's re-verifiers, cut this text's sentences on the runs of a wrapper's
// path). At any
// other such path the walk reads on as at the program the path
// names, so a shell's texts and find's -exec are read there and only the path is set aside (the fifty-eighth commit cut this text's claim
// that the walk stops at every path these readings set aside, on the reviewer's verifier: a copy of bash the text makes and then runs with
// a -c text has that text read). Where the text rebinds a
// name the reader cannot know, the row is NOT RUN with that reason, its hook verdict still asserted, never measured and never red: a name so
// bound, or a table's key, spelled with an expansion (an alias's name that is one variable's expansion binds that variable's value only where
// the text spells the variable once before the alias, that spelling a literal assignment `n=c` or a read of it from a literal here-string
// `read n <<< c`, it and the alias at top level, the text naming no IFS, and, since the sixty-second commit, the variable no parameter
// THE SHELLS' PARAMETERS lists; a write that never spells the name is not seen, in the class below); a
// PATH set wholly to an expansion or holding an expansion entry other
// than the PATH it replaces (`<lit>:$PATH` and `$PATH:<lit>` are known); an alias of an alias beyond one level (an alias whose value is the
// word `alias` defines aliases, and the words after its name bind as alias's do; one whose value runs alias with words of its own is no
// such level); a zsh module outside the table; a handler for every name not found; and a global alias's name where a command stands. Where the rows run a program that was absent on purpose where their evidence
// was measured, THE RECORDED ABSENCES below say so per row, and the gate turns for it. What the derivation does not read, stated as its
// class: a program word that is an expansion (`$z -c ..`, `"$(command -v zsh)"`, a tilde) or holds a blank; THE NON-LITERAL WORDS, where
// a word the lexer does not hold as literal is, by the lexer's rule, one carrying an expansion the hook cannot resolve (`$x`) or an
// unquoted glob character (`[`): every text an alias, eval, trap, emulate -c or mapfile -C (readarray -C) command runs, and the text echo
// or printf prints into a shell, where any one of that command's operands is such a word, whichever it is (the text itself, a trap's signal
// word, a word beside a literal value); a shell's operand that is such a word (its -c text, capsh's `--` text among them), its other
// operands still read; and what follows an assignment whose word is such a word or holds a blank (`X=$y q780-no-such-program ..`), since the
// walk stops at that word (the fifty-ninth commit, on the reviewer's re-verifier, states this rule once, where the fifty-eighth named the
// alias road alone: THE NON-LITERAL WORDS' test pins a witness of each road as measured and its literal control as NOT RUN, and the alias
// witnesses, `alias c="q780-no-such-program $x"`, `alias [=q780-no-such-program` and a literal value beside such a word, are the
// fifty-eighth commit's); what a name the text binds or
// rebinds runs, where that is a hashed path, a table entry's value or the value of an alias that a name defining aliases defines; the
// command a wrapper or a shell runs where the text binds or rebinds that wrapper's or shell's name, or where the path reading above sets
// aside the wrapper's path it runs, since the walk stops at such a name or path (the fifty-seventh commit, on the reviewer's verifier: THE STATED LIMIT's
// witnesses, `hash -p /usr/bin/env env`, `alias env='env '`, `aliases[env]=env`, a function env and a copy of env made as ../scratch/env,
// each then running env q780-no-such-program, are measured, and since the fifty-eighth so are `hash -p /usr/bin/bash bash`, `alias
// bash=bash`, a function bash and a bash the text copies under a PATH it sets, each then running bash -c 'q780-no-such-program x'; a
// shell's or find's path the text makes is read on, above; and since the fifty-ninth the stop at a wrapper's path asks the path reading's
// count, as the filter at the walk's end does); the command behind a wrapper's path set aside on a count that takes in a whole spelling at
// a place the first walk does not read, since a whole spelling counts wherever it stands (the sixtieth commit, on the reviewer's
// re-verifier: `eval "/usr/bin/env $x"; /usr/bin/env q780-no-such-program ../base/report.md report.md` is measured); a global alias's
// value, which runs wherever its name stands; a write to the variable an alias's name expands that never spells the variable's name
// (`n=q780-no-such-program`, then `export "$(printf '\156')=zz"` before `alias $n=cp`), which the first reading of THE REBOUND NAMES does
// not see, so the alias binds the value of the one spelling it reads (the sixty-second commit, on the reviewer's ruling B: its test pins
// that witness as measured and, as its control, the same text whose second write spells the name, NOT RUN); a `time` where a shell's
// choice differs from the rule in WRAPPERS' comment, since the walk follows the rule, as at two places THE TIME WORD's test pins beside
// their controls: bash runs /usr/bin/time for a `time` after a leading redirection or quoted (`\time`, `"time"`) at the head of a text it
// runs, where the walk reads the shell's own word (`bash -c '>/dev/null time cp ../base/report.md report.md'` is measured in a world with
// no time, its control `bash -c 'X=1 time cp ../base/report.md report.md'` NOT RUN naming time), and busybox's sh runs its own applet
// where the walk reads the program, the safe side, since such a row goes NOT RUN where no time is on the PATH (`busybox sh -c 'time cp
// ../base/report.md report.md'` is NOT RUN naming time in a world without it, measured in one with it); no committed row takes either
// road: of the commands the legs gate (GATED_ROWS), eight spell time, each in the row's own text alone, so none has a leading redirection
// or a quoted time at the head of a bash or zsh text, or a time in a busybox text (the sixty-fifth commit, on the reviewer's call after
// its re-verifiers);
// a name the text spells in a binding shape at a place no shell binds it, which the two binding readers set aside all the same, since they
// take the shape anywhere in the raw text (above), a slash name among them, which bash never binds as an alias's name: `echo alias
// q780-no-such-program=cp; q780-no-such-program ../base/report.md report.md` and `alias /nonexistent/q780/tool=cp; /nonexistent/q780/tool
// ../base/report.md report.md`, where bash refuses the name, are measured, each control, the same text with `zz` in the binding shape, is
// NOT RUN, and so is a different missing name beside the first binding shape (`q780-other-missing`); a name in the gate's table (bash, zsh,
// dash, sh, ksh, busybox) is read wherever the text spells it as a word, a binding shape of it in an echo operand notwithstanding, so the
// road holds only for names outside the table; no committed row takes it to a program a machine may lack: in every committed row whose text
// sets aside a name where no shell binds that name at the row's use (AL-same-line, AL-unalias and AL-name-read-var among them; a name bound
// anywhere is no program anywhere), the name set aside is env or one no system ships (c, foo, s, report.md, x.md), and the five rows a
// reading of command words alone would change bind their name by a file the row
// writes and sources or by an env operand (the sixty-sixth commit, on the reviewer's ruling A and decision 9: the test of THE STATED
// LIMIT's roads of round 8, in tools/romp-track-bash-guard.test.mjs, pins each witness here and below beside its control, a gate call each); a path the text spells whole more often
// than the first walk reads it as a program, which the path reading sets aside whether or not the text makes it, a path the text only
// tests, removes, echoes, quotes or comments among them (`[ -x /nonexistent/q780/tool ] && /nonexistent/q780/tool x` is measured, its
// control `/nonexistent/q780/tool x` NOT RUN); committed rows take it only where the path, if made, runs as a child whose effect cannot
// reach the write: the 17 commands whose derivation the filter changes each spell their path as the target of cp, ln -s or `cat >`, 13 of
// them make it, and in four (S21-bound-set, S21-bound-cd, S21-bound-bare-set, S21-bound-rel-set) the copy's source is absent here and on
// the runner, so the path is set aside unmade, and where it is made it runs as a child that cannot change the parent's `$1` or cwd (bash,
// zsh and dash write report.md either way); a path rm removes is no false pass, since it is then absent on every machine (the sixty-sixth
// commit, on the reviewer's ruling C); the text of mapfile -C (readarray -C), env -S, su, runuser or script -c and emulate -c where it is
// glued to its option or given after `=` (`-C'..'`, `-S'..'`, `-c'..'`, `--split-string=..`, `--command=..`), or follows an option word
// clustering other letters (`-tC '..'`, `-vS '..'`, `-lc '..'`, `-qc '..'`, `emulate sh -Lc '..'`), since the walk reads such a text only
// where its option is a word of its own (`mapfile -C'q780-no-such-program x #' -c 1 <<< x` is measured, its control with `-C` apart NOT
// RUN, and each other form's witness likewise beside its control); the 20 S21 rows with a glued -C, S20-mapfile-glued-set,
// RT-script-wrapper and RT-script-typescript take it, and none hides a missing program (a reader of these forms would add cp or mv, present
// wherever the suite runs, to 14 of them and nothing to the rest); the walk does not learn the glued forms, since it would need each
// program's option grammar (S21-ctl-mapfile-dC's `mapfile -dC '..'` is -d with `C` as its delimiter) (the sixty-sixth commit, on the
// reviewer's ruling E, correctness-1); in a case whose `case` begins its segment, every `)`-closed segment, since the walk takes each for a
// pattern, a subshell's body among them (`case a in a) (q780-no-such-program x) ;; esac` is measured), and after zsh's brace-form case,
// which no `esac` closes, every such segment to the end of the text (`case a { a) true }; (q780-no-such-program x)`, whose subshell zsh
// runs, is measured), the control `(q780-no-such-program x)` outside any case NOT RUN; no committed gated row takes either road (with the
// pattern skip removed, four commands change, each gaining only its pattern word) (the sixty-sixth commit, on the reviewer's ruling E,
// correctness-2); what runs behind a path the reading binds as a name, since the first walk stops there as every walk does, so a truly
// missing path run behind it and again bare is spelled whole more often than read, and set aside: "binds" is the reading's (for a hash or
// an alias of a slash name bash binds nothing), and the witness is one bash and zsh bind, `function /usr/bin/env { :; }; /usr/bin/env
// ./tool x; ./tool y`, measured, its control without the function NOT RUN; no committed row runs a path the reading binds as a name:
// definedNames' `function NAME` pattern binds `../base/report.md` after the word `function` in five rows (S11-kd-alias-function,
// S11-kd-bound-function, S11-kd-alias-function-fed, S11-kd-alias-function-notes, S11-kd-twin-hash-function), where the walk stops at
// `function` and reads no program (the sixty-sixth commit, on the reviewer's ruling E, extra6-1); a text reached behind `builtin` (an eval,
// trap, emulate -c, alias or mapfile -C text alike), and an eval text after eval's own `--`, since the walk reads neither (`builtin eval
// 'q780-no-such-program x'`, `builtin trap 'q780-no-such-program x' EXIT` and `eval -- 'q780-no-such-program x'`, each of which bash and
// zsh run, are measured, their control `eval 'q780-no-such-program x'` NOT RUN, and the other three behind `builtin` likewise beside
// theirs); the rows that take it (R6Q-O-builtin-eval-dashdash, the three R6Q-O-eval-dashdash forms, R6Q-O-untracked-twin, E29-trap-builtin)
// hide only cp, echo and builtin (the sixty-sixth commit, on the reviewer's ruling E, extra6-2); and a
// program a shell reaches by a road the list above does not follow (a script file's own lines, a `(( ))` or `$((` body read as
// commands, an array's elements, a pattern a `case` or zsh's `for NAME (..)` holds). A miss there runs the leg. Where the leg asserts that
// a shell writes, the absent program then reds it by name on that machine (no shell writes), never a false pass; where the leg asserts
// that no shell writes, or an absence, the absent program gives the very result the leg asserts, and the leg passes without having run it
// (the reviewer's verifier on the fifty-first commit). Two populations of that kind are read otherwise. THE CLEARED ENVIRONMENT's legs: since
// the fifty-third commit a name a leg's processes looked up and found nowhere reds the leg by that name, read from the leg's strace record
// of lookups and execs, whatever text the name stood in (a script file's lines, a -c operand or an eval text holding an expansion among
// them), as far as THE LOOKUP ROADS' self-test pins each road (THE LOOKUP RECORD, at their test; the fifty-second commit's attribution of
// each program word to an execve missed a name in such a text, since bash and dash make no execve for a name they do not find); and since
// the fifty-fourth a program word this derivation cannot resolve (one it does not read and that has no literal name: an expansion, a glob or
// a tilde in the program's place, a word holding a blank, zsh's `=name`) reds the leg where no execve its literal operands attribute to it
// ran, so a segment skipped on a check that finds no such program looks nothing up and still reds (the reviewer's ruling at 17:18Z, F1). And the
// matrix rows outside `needs`, whose write is placed by a recorder before the row runs where the program it names is absent (THE WRITE'S
// PLACE, at rowsNotRun). Any other leg that asserts no write through a program this derivation misses passes where that program is absent.
// The lexer is the hook's own, so a defect in it that drops a segment drops that segment's program here with the same consequences; the pin
// at the end of tools/romp-track-bash-guard.test.mjs holds the derivation to an independent reading of the text for the zsh family over every row the legs gated.
// the words a shell reads as its own, never a program it looks up: the reserved words, and the builtins of bash, zsh (its modules' among them)
// and dash
const SHELL_OWN = new Set(['!', '{', '}', '[[', ']]', '((', '))', 'if', 'then', 'elif', 'else', 'fi', 'case', 'esac', 'for', 'foreach', 'select', 'while', 'until', 'do', 'done', 'in', 'end', 'function', '.', ':', '[', 'alias', 'autoload', 'bg', 'bind', 'bindkey', 'break', 'builtin', 'bye', 'caller', 'cd', 'chdir', 'compgen', 'complete', 'compopt', 'continue', 'declare', 'dirs', 'disable', 'disown', 'echo', 'emulate', 'enable', 'eval', 'exit', 'export', 'false', 'fc', 'fg', 'float', 'functions', 'getln', 'getopts', 'hash', 'help', 'history', 'integer', 'jobs', 'kill', 'let', 'limit', 'local', 'logout', 'mapfile', 'popd', 'print', 'printf', 'private', 'pushd', 'pushln', 'pwd', 'read', 'readarray', 'readonly', 'rehash', 'return', 'sched', 'set', 'setopt', 'shift', 'shopt', 'source', 'suspend', 'test', 'times', 'trap', 'true', 'type', 'typeset', 'ulimit', 'umask', 'unalias', 'unfunction', 'unhash', 'unlimit', 'unset', 'unsetopt', 'vared', 'wait', 'whence', 'where', 'which', 'zcompile', 'zformat', 'zle', 'zmodload', 'zparseopts', 'zstyle', 'sysopen', 'sysread', 'sysseek', 'syswrite', 'zsystem', 'zf_chgrp', 'zf_chmod', 'zf_chown', 'zf_ln', 'zf_mkdir', 'zf_mv', 'zf_rm', 'zf_rmdir', 'zf_sync', 'zstat', 'zselect', 'zsocket', 'ztcp', 'zpty']);
// a wrapper runs the command after its options and operands: `arg` the options that take the next word, `operands` the words before the
// command, `assign` the NAME=VALUE words it takes (`any`: every word holding `=`, as env takes one, `BASH_FUNC_c%%=..` among them, since
// the fifty-second commit, whose execve record found env's command unread past such a word), `text` the options whose next word is a
// command line it runs, `query` an option under which it runs nothing, `sub` a subcommand word first, `own` a shell's own word (no program
// looked up), which the walk reads as a program where it is spelled as a path and, for `time` alone, at the places below. The walk reads
// `time` spelled as a name as a shell's own word only where three things hold: nothing but reserved words (`!`, `{`, `if`, `then`, `do`
// and the like) and redirections (which the lexer holds apart from the words, except the `{name}` of a named descriptor whose name is a
// plain identifier, as in `{fd}>/dev/null`, which it holds as a word, so the walk reads that word as the program there and never reaches a
// `time` after it; the `{name}` of one whose name is an array element, as in `{a[0]}>/dev/null`, it holds as a word it does not hold as
// literal, so the walk stops at that word under THE NON-LITERAL WORDS and never reaches a `time` after it either) stands before it in its
// segment, so no assignment and no wrapper; no pipe feeds the segment; and the text under way is one only bash or zsh reads (`dashReads`
// false, at programsInvoked).
// Wherever else the walk reaches it, a name the text binds or rebinds aside, it reads the program /usr/bin/time (the name `time`, which the
// gate looks up on the PATH): in the row's own text, in a text a shell other than bash or zsh runs or env -S, flock -c, su, runuser or
// script runs, after an assignment, a wrapper or a pipe, and in a find -exec (THE TIME WORD, at readSegment; the sixty-second commit, on the
// reviewer's execution checker, whose record showed dash running /usr/bin/time in six committed commands while this comment called time a
// shell's own word; the sixty-fifth commit, on the reviewer's call after its re-verifiers, states the rule alone, and where a shell's choice
// differs from it the walk follows the rule, a stated limit in the header; the seventieth commit, on the reviewer's closing check, names the
// redirections, since the walk applies the rule to the lexer's words, and pins the texts flock -c, runuser and script run in THE TIME
// WORD's shapes; the seventy-first commit, on the reviewer's re-check, says the lexer holds a named descriptor's `{name}` as a word; the
// seventy-second, on the reviewer's re-check of it, narrows that to a name that is a plain identifier and says an array element's stops the
// walk as a word the lexer does not hold as literal).
// numactl joined with the sixty-second commit, so this table holds every wrapper of the hook's PREFIXES but builtin (a shell's own word
// here, SHELL_OWN)
const WRAPPERS = {
  exec: { own: true, arg: ['-a'] }, command: { own: true, query: /^-[a-zA-Z]*[vV]/ }, time: { own: true, arg: ['-f', '-o', '--format', '--output'] },
  noglob: { own: true }, nocorrect: { own: true }, '-': { own: true }, coproc: { own: true }, repeat: { own: true, operands: 1 },
  nohup: {}, eatmydata: {}, fakeroot: {}, setsid: {}, setpriv: {},
  env: { arg: ['-u', '--unset', '-C', '--chdir', '-a', '--argv0'], text: ['-S', '--split-string'], assign: 'any' },
  nice: { arg: ['-n', '--adjustment'] }, timeout: { arg: ['-s', '--signal', '-k', '--kill-after'], operands: 1 },
  stdbuf: { arg: ['-i', '-o', '-e', '--input', '--output', '--error'] }, ionice: { arg: ['-c', '--class', '-n', '--classdata', '-p', '--pid', '-P', '--pgid', '-u', '--uid'] },
  chrt: { operands: 1 }, taskset: { operands: 1 }, chroot: { arg: ['--userspec', '--groups'], operands: 1 },
  numactl: { arg: ['-i', '--interleave', '-p', '--preferred', '-P', '--preferred-many', '-C', '--physcpubind', '-N', '--cpunodebind', '-m', '--membind'] },
  xargs: { arg: ['-a', '--arg-file', '-d', '--delimiter', '-E', '-I', '-L', '-n', '--max-args', '-P', '--max-procs', '-s', '--max-chars', '--process-slot-var'] },
  sudo: { arg: ['-u', '--user', '-g', '--group', '-C', '--close-from', '-D', '--chdir', '-h', '--host', '-p', '--prompt', '-R', '--chroot', '-T', '--command-timeout', '-U', '--other-user', '-r', '--role', '-t', '--type'], assign: true },
  doas: { arg: ['-u', '-C'] },
  strace: { arg: ['-e', '-o', '-p', '-s', '-u', '-E', '-I', '-b', '-a', '-O', '-S', '-P', '-X', '--output'] },
  ltrace: { arg: ['-e', '-o', '-p', '-s', '-u', '-a', '-n', '-l', '-F', '-A', '-D', '-x', '-L'] },
  perf: { sub: true, arg: ['-e', '--event', '-o', '--output', '-p', '--pid', '-t', '--tid', '-C', '--cpu', '-G', '--cgroup', '-r', '--repeat', '-x', '--field-separator', '-I', '--interval-print', '-D', '--delay', '-F', '--freq', '-c', '--count', '-m', '--mmap-pages', '-u', '--uid', '-j', '--branch-filter', '--post', '--pre', '--control'] },
  unshare: { arg: ['-S', '--setuid', '-G', '--setgid', '-R', '--root', '-w', '--wd', '--map-user', '--map-group', '--map-users', '--map-groups', '--propagation', '--setgroups'] },
  nsenter: { arg: ['-t', '--target', '-S', '--setuid', '-G', '--setgid'] },
  prlimit: { arg: ['-p', '--pid', '-o', '--output'] },
  flock: { arg: ['-w', '--timeout', '-E', '--conflict-exit-code'], text: ['-c', '--command'], operands: 1 },
};
// a program whose operands, here-documents and fed text are a script it runs (a list for reading texts, never for presence)
const SCRIPT_SHELL = /^(?:sh|r?bash|dash|r?zsh\d*|ksh\d*|mksh|pdksh|oksh|lksh|yash|posh|ash|hush|t?csh|fish|busybox)$/;
const ASSIGNMENT = /^[A-Za-z_][A-Za-z0-9_]*(?:\[[^\]]*\])?\+?=/;
const SCRIPT_TEXT = /[\s;&|<>()`$]/;   // an operand of a shell that reads as a command line, not an option or a name
// THE HASHED NAMES (round 7 of fork PR #780 review, fifty-seventh commit; the reviewer's verifier on the fifty-sixth): the names a hash's words
// bind to a path, read as the hook's hash site reads them (THE GLUED PATH): a `p` among its option words, its path glued (`-p/usr/bin/cp`) or
// the next word, binds each word after the options, which end at the first word that is no option or after `--`, unless a `t` stands in an
// option word before that word's `p` or in one with none (it prints: `-tp/usr/bin/cp foo`, `-p/usr/bin/cp -t foo`); a `-p` after `--` is a
// name (`-- -p/usr/bin/cp foo`); and zsh's `NAME=PATH` binds NAME. A hash with no such `p` (`hash env`) finds a name on its PATH, the lookup
// the gate asks about, and binds it to nothing else. Measured in bash 5.2 and zsh 5.9, each shell reading its own table back: the first three
// shapes bind nothing, `-p/usr/bin/cp -- foo` binds foo in bash (zsh refuses -p), `hash q780-no-such-program` binds nothing. Each entry is
// [the name, its word].
const hashBound = (ws) => {
  let bound = false;
  let prints = false;
  let k = 0;
  for (; k < ws.length && /^-./.test(ws[k]); k++) {
    if (ws[k] === '--') { k++; break; }
    const j = ws[k].indexOf('p', 1);
    if (ws[k].slice(1, j < 0 ? ws[k].length : j).includes('t')) prints = true;
    if (j < 0) continue;
    bound = true;
    if (j + 1 === ws[k].length) k++;   // the path is the next word
  }
  return ws.slice(k).flatMap((w) => (w.indexOf('=') > 0 ? [[w.slice(0, w.indexOf('=')), w]] : bound && !prints ? [[w, w]] : []));
};
// the names the text spells in the shapes that bind a function, an alias or a hashed path, read over its whole raw text, a command word or
// not (a name so spelled anywhere is no program anywhere in it): `f()` (zsh's `f g ()` too), `function f`, `alias f=..`, `hash -p PATH f` (the
// path glued or apart) and zsh's `hash f=PATH` as THE HASHED NAMES read them, `functions[f]=..`, `autoload f` and an exported function's
// `BASH_FUNC_f%%=..`, which the bash it reaches defines as f
const hashedNames = (text) => [...text.matchAll(/(?:^|[\s;&|(){}`'"])hash\s+([^\n;&|'"]*)/g)].flatMap((m) => hashBound(m[1].trim().split(/\s+/).filter(Boolean)).map(([name]) => name));
const definedNames = (text) => new Set([
  ...[...text.matchAll(/(?:^|[\s;&|(){}`'"])(?:function\s+)?((?:[A-Za-z_][\w.:+-]*[ \t]+)*[A-Za-z_][\w.:+-]*)\s*\(\s*\)/g)].flatMap((m) => m[1].split(/[ \t]+/)),
  ...[...text.matchAll(/(?:^|[\s;&|(){}`'"])function\s+([^\s(){};|&'"]+)/g)].map((m) => m[1]),
  ...[...text.matchAll(/(?:^|[\s;&|(){}`'"])alias\s+(?:-\S+\s+)*['"]?([^\s=;|&'"]+)['"]?=/g)].map((m) => m[1]),
  ...hashedNames(text),
  ...[...text.matchAll(/(?:^|[\s;&|(){}`'"])functions\[([^\]]+)\]=/g)].map((m) => m[1].replace(/^['"]|['"]$/g, '')),
  ...[...text.matchAll(/(?:^|[\s;&|(){}`'"])autoload\s+((?:-\S+\s+)*)([^\n;&|'"]*)/g)].flatMap((m) => m[2].trim().split(/\s+/).filter((n) => n && !/^[-+]/.test(n))),
  ...[...text.matchAll(/(?:^|[\s;&|(){}`'"])BASH_FUNC_([^\s%=;&|'"]+)%%=/g)].map((m) => m[1]),   // an exported function bash takes from its environment (the fifty-second commit)
]);
// THE REBOUND NAMES (round 7 of fork PR #780 review, fifty-sixth commit; the reviewer's rulings at 00:32Z and 01:00Z). A text that rebinds how
// a name resolves no longer sets aside every other name: the reading sets aside, as no program of this machine's, each name the text spells in
// a rebinding shape, read over the whole raw text as definedNames reads its names, a command word or not (an echo or printf operand, a
// comment, a quoted string such as a grep pattern, a file spelled under a literal directory of a PATH the text sets; a shape at a place no
// shell binds it is in the header's class of what the derivation does not read): an alias's name (a suffix alias's: a word ending in its
// suffix), a name a hash binds to a path (THE HASHED NAMES), an autoloaded or an enabled name, a `functions[NAME]`, `commands[NAME]` or
// `aliases[NAME]` entry, the builtins a zsh module it loads adds (ZSH_MODULE_BUILTINS, measured with `zmodload -lF` under zsh 5.9), and a
// name the text spells as a file under a literal directory of a PATH it sets (a file it makes, copies or links there). The walk stops at
// each such name and does not step past it, so what a rebound wrapper's
// or shell's name runs is not read (the fifty-seventh commit cut this text's claim that every other name is read, on the reviewer's
// verifier: `aliases[env]=env`, then env running a missing program, is measured; THE STATED LIMIT, in the header's class of what the
// derivation does not read). Every other name the walk reaches where a program stands is read as a program, and the walk reads an alias's
// value as the text that alias runs, but for a global alias's (below) and as far as THE NON-LITERAL WORDS, in the header's class of what the
// derivation does not read, allow (the fifty-eighth commit cut this text's claim for every value, on the reviewer's verifier: `alias
// c="q780-no-such-program $x"`, then c, is measured). Four readings go exactly as far as the
// ruling at 01:00Z and no further:
//   an alias whose name is one variable's expansion (`alias $n=cp`) binds that variable's value where the text spells the variable once
//   before the alias and names no IFS, that spelling and the alias each standing at top level (topLevelSegments: in no subshell, brace
//   group, conditional or loop, run in sequence), that spelling is a literal assignment (`n=c`) or a read of that one name from a literal
//   here-string (`read n <<< c`), and, since the sixty-second commit (the reviewer's ruling B), the variable is no parameter THE SHELLS'
//   PARAMETERS lists (`alias $RANDOM=cp` goes to `unknowable`); a write that never spells the name is not seen (the header's class of what the
//   derivation does not read);
//   a PATH the text sets is known where each entry is a literal directory or the PATH it replaces (`<lit>:$PATH`, `$PATH:<lit>`) and at least
//   one entry is a literal directory: the inherited PATH plus literal directories;
//   an alias whose value is the word `alias` (a trailing blank aside) makes its name define aliases, one level: the words after that name bind
//   as alias's operands do (an expansion among them is not followed); an alias whose value runs alias with words of its own, an alias that
//   runs such a name, and one such a name defines to run alias, are chains the reader does not follow;
//   a global alias's value is never read as a command line, and its name binds no name.
// `unknowable` holds each rebinding whose names the reader cannot know: an alias's, a hashed, an autoloaded or an enabled name, or a table's
// key, spelled with an expansion the first reading does not follow (an alias's name that expands a parameter THE SHELLS' PARAMETERS lists
// among them); a PATH the second does not know; a chain the third does not follow; a
// zsh module outside the table; a handler for every name not found. programsInvoked adds a global alias's name standing where a command
// stands. namedPresent makes such a row NOT RUN with that reason, its hook verdict asserted before its legs, never measured and never red, and
// the walk still reads as a program every name it reaches that the text does not rebind (the ruling at 01:00Z, item 1).
const ZSH_MODULE_BUILTINS = {
  'zsh/files': ['chgrp', 'chmod', 'chown', 'ln', 'mkdir', 'mv', 'rm', 'rmdir', 'sync', 'zf_chgrp', 'zf_chmod', 'zf_chown', 'zf_ln', 'zf_mkdir', 'zf_mv', 'zf_rm', 'zf_rmdir', 'zf_sync'],
  'zsh/system': ['syserror', 'sysread', 'syswrite', 'sysopen', 'sysseek', 'zsystem'],
  'zsh/mapfile': [],
};
// THE SHELLS' PARAMETERS (round 8 of fork PR #780 review, sixty-second commit; the reviewer's ruling B): the names the two commands below
// print, among them parameters whose literal write bash and zsh do not keep (RANDOM, SECONDS: bash and zsh bind no `c` for
// `RANDOM=c; alias $RANDOM=cp`; dash does), so an alias whose name expands one of them goes to `unknowable` (THE REBOUND NAMES). Derived by
// execution: each list is the output of the command beside it, run on this box, bash's under the environment its own `env -i` sets and zsh's
// under an environment of PATH and LANG=C.UTF-8 (zsh lists some parameters as special only where they are set, LANG, TERM, TERMINFO,
// POSTEDIT and LC_ALL among them). Under those environments bash 5.2.21 gives 44 names under `-c`, 43 when the same text is fed on its
// standard input; zsh 5.9 gives 73 under plain `zsh -f` with no module named, 111 with zsh/parameter, zsh/datetime, zsh/system and
// zsh/mapfile loaded, 118 with those and zsh/zleparameter, zsh/terminfo, zsh/termcap, zsh/sched and zsh/watch, and 125 with those nine and
// zsh/curses and zsh/langinfo, the two other modules of its build that add one, which is the command here. The union is read, the stricter
// side: a name listed that a shell does not set only sends a row NOT RUN. The sixty-second commit's test re-derives the bash list on every
// runner and the zsh list where zsh is present, each contained in its table; since the sixty-third commit (the reviewer's verifier, whose
// run with TERM set turned the zsh half red) it runs zsh's command under an environment of PATH alone, beside the ZDOTDIR and SHLVL that
// NO STARTUP FILE OF THE ACCOUNT'S adds, where zsh on this box lists 124 of the table's names, LANG not among them.
const SHELL_PARAMETERS = {
  bash: {
    argv: ['env', '-i', 'PATH=/usr/bin:/bin', 'bash', '--norc', '--noprofile', '-c', 'compgen -v'],
    names: ['BASH', 'BASHOPTS', 'BASHPID', 'BASH_ALIASES', 'BASH_ARGC', 'BASH_ARGV', 'BASH_ARGV0', 'BASH_CMDS', 'BASH_COMMAND', 'BASH_EXECUTION_STRING', 'BASH_LINENO', 'BASH_LOADABLES_PATH', 'BASH_SOURCE', 'BASH_SUBSHELL', 'BASH_VERSINFO', 'BASH_VERSION', 'COMP_WORDBREAKS', 'DIRSTACK', 'EPOCHREALTIME', 'EPOCHSECONDS', 'EUID', 'GROUPS', 'HISTCMD', 'HOSTNAME', 'HOSTTYPE', 'IFS', 'LINENO', 'MACHTYPE', 'OPTERR', 'OPTIND', 'OSTYPE', 'PATH', 'PPID', 'PS4', 'PWD', 'RANDOM', 'SECONDS', 'SHELL', 'SHELLOPTS', 'SHLVL', 'SRANDOM', 'TERM', 'UID', '_'],
  },
  zsh: {
    argv: ['zsh', '-f', '-c', 'zmodload zsh/parameter zsh/datetime zsh/system zsh/mapfile zsh/zleparameter zsh/terminfo zsh/termcap zsh/sched zsh/watch zsh/curses zsh/langinfo; print -l ${(k)parameters[(R)*special*]}'],
    names: ['!', '#', '$', '*', '-', '0', '?', '@', 'ARGC', 'CDPATH', 'COLUMNS', 'EGID', 'EPOCHREALTIME', 'EPOCHSECONDS', 'EUID', 'FIGNORE', 'FPATH', 'FUNCNEST', 'GID', 'HISTCHARS', 'HISTCMD', 'HISTSIZE', 'HOME', 'IFS', 'KEYBOARD_HACK', 'LANG', 'LINENO', 'LINES', 'MAILPATH', 'MANPATH', 'MODULE_PATH', 'NULLCMD', 'OPTARG', 'OPTIND', 'PATH', 'PPID', 'PROMPT', 'PROMPT2', 'PROMPT3', 'PROMPT4', 'PS1', 'PS2', 'PS3', 'PS4', 'PSVAR', 'RANDOM', 'READNULLCMD', 'SAVEHIST', 'SECONDS', 'SHLVL', 'SPROMPT', 'TRY_BLOCK_ERROR', 'TRY_BLOCK_INTERRUPT', 'TTYIDLE', 'UID', 'USERNAME', 'WATCH', 'WORDCHARS', 'ZCURSES_COLORS', 'ZCURSES_COLOR_PAIRS', 'ZSH_EVAL_CONTEXT', 'ZSH_SUBSHELL', '_', 'aliases', 'argv', 'builtins', 'cdpath', 'commands', 'dirstack', 'dis_aliases', 'dis_builtins', 'dis_functions', 'dis_functions_source', 'dis_galiases', 'dis_patchars', 'dis_reswords', 'dis_saliases', 'epochtime', 'errnos', 'fignore', 'fpath', 'funcfiletrace', 'funcsourcetrace', 'funcstack', 'functions', 'functions_source', 'functrace', 'galiases', 'histchars', 'history', 'historywords', 'jobdirs', 'jobstates', 'jobtexts', 'keymaps', 'langinfo', 'mailpath', 'manpath', 'mapfile', 'module_path', 'modules', 'nameddirs', 'options', 'parameters', 'patchars', 'path', 'pipestatus', 'prompt', 'psvar', 'reswords', 'saliases', 'status', 'sysparams', 'termcap', 'terminfo', 'userdirs', 'usergroups', 'watch', 'widgets', 'zcurses_attrs', 'zcurses_colors', 'zcurses_keycodes', 'zcurses_windows', 'zsh_eval_context', 'zsh_scheduled_events'],
  },
};
const SHELL_PARAMETER_NAMES = new Set(Object.values(SHELL_PARAMETERS).flatMap((s) => s.names));
const EXPANDS = /[$`]/;
const VALUE_NAME = /^[^\s/=$`'"\\;&|<>(){}*?[\]~#!]+$/;   // a literal value that stands for itself as a command's name
const escapeRe = (t) => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
// the words of a command's operands from `s[i]`, to the first newline, `;`, `&`, `|` or `)` outside quotes: each its text with quotes removed
const operandWords = (s, i) => {
  const out = [];
  let cur = null;
  let q = null;
  for (; i < s.length; i++) {
    const ch = s[i];
    if (q) { if (ch === q) q = null; else cur.text += ch; continue; }
    if (/[\n;&|)]/.test(ch)) break;
    if (/\s/.test(ch)) { if (cur) out.push(cur); cur = null; continue; }
    if (!cur) cur = { text: '' };
    if (ch === "'" || ch === '"') { q = ch; continue; }
    if (ch === '\\' && i + 1 < s.length && s[i + 1] !== '\n') { cur.text += s[++i]; continue; }
    cur.text += ch;
  }
  if (cur) out.push(cur);
  return out.map((w) => w.text);
};
// which of a text's segments stand at its top level: in no subshell, brace group, conditional or loop, not the head of a compound, and run in
// sequence (after the text's start, a `;` or a newline, and ended by one of those), so a write there happens once, before what follows it.
// A compound's opening word counts wherever it stands in a segment, and its closing word only at the segment's head, so a word such as
// `echo fi` never closes one; a closing word with none open leaves nothing after it at top level (the stricter side).
const TOP_OPENERS = new Set(['if', 'while', 'until', 'for', 'foreach', 'select', 'case', '{']);
const TOP_CLOSERS = new Set(['fi', 'done', 'esac', '}', 'end']);
const TOP_HEADS = /^(?:[!{}]|if|then|elif|else|fi|while|until|do|done|for|foreach|select|case|esac|function|repeat|coproc|time|end)$/;
const topLevelSegments = (segs) => {
  const seq = (op) => op === '' || op === ';' || op === '\n';
  const out = [];
  let depth = 0;
  for (let k = 0; k < segs.length; k++) {
    const s = segs[k];
    const words = s.words.map((w) => w.text);
    if (s.paren === ')' || (words.length && TOP_CLOSERS.has(words[0]))) depth = depth > 0 ? depth - 1 : Infinity;
    out.push(depth === 0 && s.paren === undefined && seq(k > 0 ? segs[k - 1].op : '') && seq(s.op) && words.length > 0 && !TOP_HEADS.test(words[0]) && !words.includes('{'));
    if (s.paren === '(') depth++;
    depth += words.filter((w) => TOP_OPENERS.has(w)).length;
  }
  return out;
};
// an alias's name that is one variable's expansion, `$n` or `${n}`: the variable is the first or the second group
const ALIAS_VARIABLE = /^\$(?:([A-Za-z_][A-Za-z0-9_]*)|\{([A-Za-z_][A-Za-z0-9_]*)\})$/;
// the name `alias $n=cp` binds, where the alias keyword stands at `at` and `name` is one variable's expansion: that variable's value, under the
// first reading above, else null
const aliasVariable = (text, at, name) => {
  const m = name.match(ALIAS_VARIABLE);
  if (!m || /(?<![A-Za-z0-9_])IFS(?![A-Za-z0-9_])/.test(text)) return null;
  const v = m[1] || m[2];
  let segs;
  try { segs = lex(text).segments; } catch { return null; }
  const top = topLevelSegments(segs);
  const segAt = (p) => segs.findIndex((s, j) => s.start <= p && p < (j + 1 < segs.length ? segs[j + 1].start : Infinity));
  const k = segAt(at);
  if (k < 0 || !top[k] || segs[k].words[0].text !== 'alias') return null;   // the alias at top level, the head of its segment
  const hits = [...text.slice(0, segs[k].start).matchAll(new RegExp(`(?<![A-Za-z0-9_])${v}(?![A-Za-z0-9_])`, 'g'))];
  if (hits.length !== 1) return null;   // the variable named once before the alias
  const j = segAt(hits[0].index);
  if (j < 0 || j >= k || !top[j]) return null;   // that spelling at top level
  const s = segs[j];
  if (s.redirects.length || s.subs.length || (s.viaSubs || []).length) return null;
  const ws = s.words.map((w) => w.raw);
  let value = null;
  if (!s.heredocs.length && ws.length === 1 && s.words[0].literal && ws[0].startsWith(`${v}=`)) value = s.words[0].text.slice(v.length + 1);   // `n=c`
  else if (s.herestring && s.heredocs.length === 1 && (ws.join(' ') === `read ${v}` || ws.join(' ') === `read -r ${v}`)) value = s.heredocs[0];   // `read n <<< c`
  return value !== null && VALUE_NAME.test(value) ? value : null;
};
const reboundNamesOf = (text) => {
  const names = new Set();
  const suffixes = new Set();
  const globals = new Set();
  const dirs = [];
  const unknowable = [];
  const sites = (word) => [...text.matchAll(new RegExp(`(?:^|[\\s;&|(){}\`'"])(${escapeRe(word)})(?=[ \\t])`, 'g'))].map((m) => ({ at: m.index + m[0].length - m[1].length, from: m.index + m[0].length }));
  const defs = [];   // every alias the text defines: { name, value, global, via (the name defining aliases it went through, else null), spelled }
  // an alias command's operands (or those of a name defining aliases), from `from`: options first, `--` ending them; each NAME=VALUE binds NAME
  const aliasWords = (head, at, from, via) => {
    let global = false;
    let suffix = false;
    let opts = true;
    for (const w of operandWords(text, from)) {
      if (opts && w === '--') { opts = false; continue; }
      if (opts && /^[-+]./.test(w)) { if (w.slice(1).includes('g')) global = true; if (w.slice(1).includes('s')) suffix = true; continue; }
      opts = false;
      const eq = w.indexOf('=');
      if (eq <= 0) continue;   // `alias c` prints c's alias: it binds nothing
      let name = w.slice(0, eq);
      if (EXPANDS.test(name)) {
        const param = name.match(ALIAS_VARIABLE);
        if (!via && param && SHELL_PARAMETER_NAMES.has(param[1] || param[2])) { unknowable.push(`${head} ${w}: an alias whose name expands a parameter a shell sets itself or treats as special (THE SHELLS' PARAMETERS)`); continue; }   // the round-8 closure (ruling B)
        const value = via ? null : aliasVariable(text, at, name);
        if (value === null) { unknowable.push(`${head} ${w}: an alias whose name is an expansion the reader does not follow`); continue; }
        name = value;
      }
      (global ? globals : suffix ? suffixes : names).add(name);
      defs.push({ name, value: w.slice(eq + 1), global, via, spelled: `${head} ${w}` });
    }
  };
  for (const s of sites('alias')) aliasWords('alias', s.at, s.from, null);
  for (const m of text.matchAll(/(?:^|[\s;&|(){}`'"])(functions|commands|aliases)\[([^\]]*)\]=/g)) {
    const key = m[2].replace(/^['"]|['"]$/g, '');
    if (EXPANDS.test(key)) { unknowable.push(`${m[1]}[${m[2]}]: a table entry whose name is an expansion`); continue; }
    names.add(key);
    if (m[1] === 'aliases') defs.push({ name: key, value: operandWords(text, m.index + m[0].length)[0] || '', global: false, via: null, spelled: `aliases[${m[2]}]=` });
  }
  // an alias of an alias, one level: a name whose value is the word `alias` defines aliases, and the words after it bind as alias's operands do
  const firstWord = (d) => d.value.trim().split(/\s+/)[0];
  const definers = defs.filter((d) => !d.global && firstWord(d) === 'alias');
  for (const d of definers) {
    if (d.value.trim() !== 'alias' || d.via) { unknowable.push(`${d.spelled}: an alias that runs alias with words of its own, or that a name defining aliases defined`); continue; }
    for (const s of sites(d.name)) aliasWords(d.name, s.at, s.from, d.name);
  }
  const definerNames = new Set(definers.map((d) => d.name));
  for (const d of defs) {
    if (d.via && firstWord(d) === 'alias') unknowable.push(`${d.spelled}: a name defining aliases that a name defining aliases defined, a chain deeper than one level`);
    else if (definerNames.has(firstWord(d))) unknowable.push(`${d.spelled}: an alias that runs ${firstWord(d)}, a name defining aliases, a chain deeper than one level`);
  }
  for (const s of sites('hash')) {
    for (const [name, word] of hashBound(operandWords(text, s.from))) {   // THE HASHED NAMES: the names a hash binds to a path
      if (EXPANDS.test(name)) unknowable.push(`hash ${word}: a hashed name that is an expansion`); else names.add(name);
    }
  }
  for (const [kw, what] of [['autoload', 'an autoloaded name'], ['enable', 'an enabled name']]) {
    for (const s of sites(kw)) {
      const ws = operandWords(text, s.from);
      for (let k = 0; k < ws.length; k++) {
        if (kw === 'enable' && ws[k] === '-f') { k++; continue; }   // enable's -f names the file its builtin loads from
        if (/^[-+]/.test(ws[k])) continue;
        if (EXPANDS.test(ws[k])) unknowable.push(`${kw} ${ws[k]}: ${what} that is an expansion`); else names.add(ws[k]);
      }
    }
  }
  for (const s of sites('zmodload')) {
    const ws = operandWords(text, s.from);
    const opts = ws.filter((w) => /^-/.test(w)).join('');
    if (/[elLd]/.test(opts)) continue;   // a query: it loads nothing
    if (/u/.test(opts)) continue;   // an unload: its names resolve as before
    for (const w of ws) {
      if (/^-/.test(w)) continue;
      if (Object.hasOwn(ZSH_MODULE_BUILTINS, w)) ZSH_MODULE_BUILTINS[w].forEach((b) => names.add(b));
      else unknowable.push(`zmodload ${ws.join(' ')}: a module whose builtins are not in ZSH_MODULE_BUILTINS`);
    }
  }
  if (/(?:^|[\s;&|(){}`'"])command_not_found_handler?\b/.test(text)) unknowable.push('command_not_found_handle(r): a handler for every name not found');
  for (const m of text.matchAll(/(?:^|[\s;&|(){}`'"])(PATH|path)(\+?=\(?|\[[^\]]*\]=)/g)) {
    const i = m.index + m[0].length;
    const array = m[2].endsWith('(');
    const close = text.indexOf(')', i);
    const ws = array ? operandWords(text.slice(0, close < 0 ? text.length : close), i) : operandWords(text, i).slice(0, 1);
    const spelled = `${m[1]}${m[2]}${array ? `${ws.join(' ')})` : ws[0] || ''}`;
    const inherited = array ? /^\$(?:path|\{path(?:\[@\])?\})$/ : /^\$(?:PATH|\{PATH\})$/;
    let entries = array ? ws : (ws[0] || '').split(':');
    if (m[2] === '+=') {
      if (entries.length < 2 || entries[0] !== '') { unknowable.push(`${spelled}: a PATH its last inherited entry is extended by`); continue; }
      entries = entries.slice(1);   // the separator after the inherited PATH
    }
    let literal = 0;
    let expanded = 0;
    for (const e of entries) {
      if (inherited.test(e)) continue;   // the PATH it replaces
      if (EXPANDS.test(e) || /^~/.test(e)) { unknowable.push(`${spelled}: a PATH entry that is an expansion (${e})`); expanded++; continue; }
      dirs.push(e === '' ? '.' : e.replace(/(.)\/+$/, '$1'));
      literal++;
    }
    if (!literal && !expanded && !m[2].startsWith('+')) unknowable.push(`${spelled}: a PATH set wholly to an expansion`);
  }
  return { names, suffixes, globals, dirs, unknowable: [...new Set(unknowable)] };
};
// a name `word` the text rebinds, by the reading above
const reboundBy = (r, text, word) => r.names.has(word) || [...r.suffixes].some((x) => word.endsWith(`.${x}`)) || r.dirs.some((d) => new RegExp(`(?:^|[^\\w./-])${escapeRe(d)}/${escapeRe(word)}(?![\\w./-])`).test(text));
// every program the walk reaches where a program stands in the command text, in the order its segments run them (wrappers included), each
// once: by name unless the text binds or rebinds that name (definedNames, THE REBOUND NAMES), and by path unless the text spells that path
// whole more often than the walk reads it as the program a segment runs, so elsewhere too (a word of its own, as an operand or a
// redirection's target: a file the text makes, copies or links before it runs it; a longer path it starts or ends is none, since the
// fifty-seventh commit), the reads counted on a first walk, which, like every walk, stops at a name or path the reading binds or rebinds, so
// a whole spelling behind it counts toward setting that path aside (THE WRAPPER'S PATH, below). The walk stops at a name so set aside, and at
// a path so set aside that names a wrapper (on a second walk, run only where the first sets such a path aside), so what it runs is not
// read (THE STATED LIMIT, in the header); a wrapper's path neither so set aside nor bound as a name (definedNames) is stepped past (the
// fifty-ninth commit: the stop counted the path's own program words; the sixtieth and sixty-first cut this comment's sentences on the runs
// of such a path); at any other path so set aside it
// reads on as at the program the path names (a shell's texts, find's -exec), and the filter at its end sets the path aside (the fifty-eighth
// commit cut this comment's claim that the walk stops at every path so set aside). `unknown`, when given, receives each rebinding whose
// names the reader cannot know (THE REBOUND NAMES' `unknowable`, and a global alias's name standing where a command stands), for namedPresent's
// NOT RUN. `collect`, when given, receives every PROGRAM WORD the walk whose result stands reaches, read or not, for THE LOOKUP RECORD's
// rule 2 (below, at THE CLEARED ENVIRONMENT's legs): `{ word, read, name, conditional }`. `read` marks a program the walk reads (by name or
// by path, returned below unless a filter above sets it aside); an unread one is a program word the walk stops at (an expansion or a tilde in
// the program's place, a word holding a blank, zsh's `=name`, a name the text rebinds or a global alias's name, the first word after an assignment the
// lexer holds as an expansion), `name` its literal text where it has one (else null; the fifty-third commit dropped the literal operands the
// fifty-second attributed such a word by). `conditional` marks a segment its text runs only on a condition: a body of a loop, of an if, elif or else, of a case
// arm or of a function, a command after && or ||, the texts of trap, alias, mapfile's -C and find's -exec, and what a shell given a -c text
// or an operand, and no -s, is fed on its standard input; the other texts a segment runs (its substitutions, a shell's -c text, eval's)
// share its mark. A subshell's parenthesis is not read, so a command inside `a && ( .. )` after its first is marked unconditional: the
// stricter side
const programsInvoked = (cmd, { collect = null, unknown = null } = {}) => {
  const defined = definedNames(cmd);
  const rebinding = reboundNamesOf(cmd);
  const tell = (why) => { if (unknown && !unknown.includes(why)) unknown.push(why); };
  rebinding.unknowable.forEach(tell);
  // THE WRAPPER'S PATH (the fifty-ninth commit; the reviewer's re-verifier on the fifty-eighth, under the condition at 00:29Z): the state of
  // the walk under way. A path is set aside where the text spells it whole more often than a FIRST walk reads it as the program a segment
  // runs (`made`, below; the first walk, like every walk, stops at a name or path the reading binds or rebinds, so a whole spelling behind it
  // counts toward setting that path aside); where one such path names a wrapper, a second walk stops there (`stops`),
  // so the stop and the filter at the end ask the same question on the same counts. The stop asked instead whether the text spelled a
  // wrapper's path twice, which counted the path's own program words: `/usr/bin/env q780-no-such-program x; /usr/bin/env ..` stopped at
  // both runs, and a missing program behind a wrapper's path the text runs twice, or runs again in a pipe, a substitution or a -c text, was
  // measured. `collect` and `unknown` take the records of the walk whose result stands, never the first walk's where a second one runs.
  let found = [];
  let asProgram = new Map();   // how often the walk read each path as the program a segment runs
  let stops = null;   // the wrapper paths the walk stops at: none on the first walk
  let records = [];   // collect's records of the walk under way
  let cannotKnow = [];   // unknown's, of the walk under way (a global alias's name where a command stands)
  const cannot = (why) => { if (!cannotKnow.includes(why)) cannotKnow.push(why); };
  // THE TIME WORD (the sixty-second commit; the reviewer's execution checker, round 8 of fork PR #780; the rule in WRAPPERS' comment):
  // `dashReads` holds whether a shell other than bash or zsh may read the text under way: the row's own text, which every leg's dash runs;
  // the text a shell other than bash or zsh runs; the text env -S, flock -c, su, runuser or script run, through a program or the account's
  // shell; and a text eval, trap, alias, emulate -c or mapfile -C runs, as the text around it. readSegment reads `time` as the program
  // there, and after an assignment, a wrapper or a pipe, and in a find -exec, and as a shell's own word only where nothing but reserved
  // words and redirections stands before it (the lexer holds a redirection apart from the words, except the `{name}` of a named descriptor
  // whose name is a plain identifier, `{fd}`, which it holds as a word and the walk reads as the program there, and an array element's,
  // `{a[0]}`, a word it does not hold as literal, where the walk stops under THE NON-LITERAL WORDS: WRAPPERS' comment) in a segment no pipe
  // feeds, in a text only bash or zsh reads
  let dashReads = true;
  const TIME_WORD_SHELL = /^(?:r?bash|r?zsh\d*)$/;   // the shells whose texts the walk reads with `time` as a shell's own word (WRAPPERS' comment)
  const readAs = (reads, fn) => { const outer = dashReads; dashReads = reads; try { fn(); } finally { dashReads = outer; } };
  // how often the text spells a path WHOLE (the fifty-seventh commit; the reviewer's verifier on the fifty-sixth, which found a count of every
  // substring setting `./tool` aside beside a made `./tool.bak`): a spelling ends a shell word on each side (the text's edge, a blank, an
  // operator, a quote or a backtick, and before it an assignment's `=` too), so a longer path it starts or ends (`./tool.bak`, `x./tool`) is none
  const mentions = (p) => {
    let n = 0;
    for (let i = cmd.indexOf(p); i >= 0; i = cmd.indexOf(p, i + 1)) if (/^(?:|[\s;&|<>()'"`=])$/.test(i > 0 ? cmd[i - 1] : '') && /^(?:|[\s;&|<>()'"`])$/.test(cmd[i + p.length] || '')) n++;
    return n;
  };
  const note = (word, cond) => { asProgram.set(word, (asProgram.get(word) || 0) + 1); if (!found.includes(word)) found.push(word); if (collect) records.push({ word, read: true, name: word, operands: null, conditional: cond }); };
  // a program word the walk does not read, at `words[i]`: the first word from there that is no assignment, its literal name, and the words
  // after it where every one is literal (the fifty-fourth commit: THE LOOKUP RECORD's rule 2 attributes a word with no name by them)
  const unread = (words, i, cond, named) => {
    if (!collect) return;
    let j = i;
    while (j < words.length && ASSIGNMENT.test(words[j].text)) j++;
    if (j >= words.length) return;   // assignments alone run no program
    const w = words[j];
    const ops = words.slice(j + 1);
    const literal = (x) => x.literal && !x.text.includes('\u0000') && !/^~/.test(x.raw || '');
    records.push({ word: w.raw || w.text, read: false, name: (named || j > i) && literal(w) && !/\s/.test(w.text) ? w.text : null, operands: ops.every(literal) ? ops.map((o) => o.text) : null, conditional: cond });
  };
  const lexOf = (text) => { try { return lex(text); } catch (e) { throw new Error(`THE INVOKED PROGRAM: the command text could not be read (${e.message}): ${String(text).slice(0, 200)}`); } };
  // the text a segment of echo, printf or cat prints, as a shell it feeds reads it: echo's literal operands joined by a blank (its leading
  // options set aside), printf's one operand or its operands under a format of %s, %b and blanks alone (printf -v prints nothing), cat's
  // here-documents; a text holding no blank or operator is no command line
  const printedBy = (s) => {
    const head = s.words[0] ? s.words[0].text : '';
    const ops = s.words.slice(1);
    let texts = [];
    if (head === 'echo') { let j = 0; while (j < ops.length && /^-[neE]+$/.test(ops[j].text)) j++; if (ops.slice(j).every((w) => w.literal)) texts = [ops.slice(j).map((w) => w.text).join(' ').replace(/\\n/g, '\n')]; }   // \n a newline, as dash's and zsh's echo and `echo -e` print it
    else if (head === 'printf' && ops.length && ops.every((w) => w.literal) && ops[0].text !== '-v') {
      if (ops.length === 1) texts = [ops[0].text.replace(/\\n/g, '\n')];
      else if (/^(?:%[sb]|\s|\\n)+$/.test(ops[0].text)) texts = [ops.slice(1).map((w) => w.text).join(' ')];
    } else if (head === 'cat') texts = s.heredocs;
    return texts.filter((t) => SCRIPT_TEXT.test(t.trim()));
  };
  const readText = (text, depth, cond = false) => {
    if (depth > 8 || typeof text !== 'string' || text.trim() === '') return;
    const segs = lexOf(text).segments;
    let inCase = 0;
    let inForList = false;
    // `collect`'s conditional mark: the compounds open at each segment, each holding whether its content runs only on a condition and
    // whether an && or || before the segment, in the list at that level, makes it so; `fnBody` when the next `{` opens a function's body
    const open = [{ kind: 'text', cond, andor: false }];
    let fnBody = false;
    for (let k = 0; k < segs.length; k++) {
      const seg = segs[k];
      if (k > 0) {
        const op = segs[k - 1].op;
        const at = open[open.length - 1];
        if (op === '&&' || op === '||') at.andor = true;
        else if (op === '(' && segs[k - 1].words.length && !seg.words.length && seg.op === ')') fnBody = true;   // `NAME ( )`
        else if (!['|', '|&', '(', ')'].includes(op)) at.andor = false;
      }
      for (const r of seg.words.map((x) => x.text)) {
        const at = open[open.length - 1];
        const here = at.cond || at.andor;
        if (r === 'if' || r === 'while' || r === 'until') open.push({ kind: r === 'if' ? 'if' : 'loop', cond: here, andor: false });
        else if (r === 'then' || r === 'elif' || r === 'else') { if (at.kind === 'if') Object.assign(at, { cond: true, andor: false }); }
        else if (r === 'do') { if (at.kind === 'loop' || at.kind === 'for') Object.assign(at, { cond: true, andor: false }); }
        else if (r === 'done' || r === 'fi' || r === 'esac' || r === '}') { if (open.length > 1) open.pop(); }
        else if (r === 'for' || r === 'foreach' || r === 'select') { open.push({ kind: 'for', cond: here, andor: false }); break; }
        else if (r === 'case') { open.push({ kind: 'case', cond: true, andor: false }); break; }
        else if (r === 'function') { if (seg.words.some((x) => x.text === '{')) open.push({ kind: 'group', cond: true, andor: false }); else fnBody = true; break; }
        else if (r === '{') { open.push({ kind: 'group', cond: here || fnBody, andor: false }); fnBody = false; }
        else if (r !== '!') break;
      }
      const segCond = open[open.length - 1].cond || open[open.length - 1].andor;
      for (const s of seg.subs) readText(s, depth + 1, segCond);
      for (const v of seg.viaSubs || []) if (v.via !== guard.CONSTRUCT_HEADS['(('].via && v.via !== guard.CONSTRUCT_HEADS['$(('].via) readText(v.text, depth + 1, segCond);
      const head = seg.words[0] ? seg.words[0].text : '';
      const last = seg.words.length ? seg.words[seg.words.length - 1].text : '';
      if (inForList) { if (seg.op === ')') inForList = false; continue; }
      if (seg.op === '(' && /^[A-Za-z_][A-Za-z0-9_]*(?:\[[^\]]*\])?\+?=$/.test(last)) { inForList = true; continue; }   // an array's elements, `c=(..)`, `c+=(..)`
      if (head === 'case') { inCase++; continue; }
      if (head === 'esac') { inCase = Math.max(0, inCase - 1); continue; }
      if (inCase && seg.op === ')') continue;   // a pattern
      if ((head === 'for' || head === 'foreach' || head === 'select') && seg.op === '(') { inForList = true; continue; }
      readSegment(seg, k > 0 && /^\|&?$/.test(segs[k - 1].op) ? segs[k - 1] : null, depth, segCond);
    }
  };
  const readSegment = (seg, feeder, depth, cond = false) => {
    const words = seg.words;
    let i = 0;
    let head = !seg.exec;   // THE TIME WORD: nothing but reserved words and redirections (a redirection is none of the lexer's words, except the `{name}` of a named descriptor whose name is a plain identifier, `{fd}`, which the lexer holds as a word and the walk reads as the program there, and an array element's, `{a[0]}`, a word the lexer does not hold as literal, where the walk stops under THE NON-LITERAL WORDS: WRAPPERS' comment) before the word under way, so no assignment or wrapper (a find -exec's words run as a program)
    for (let steps = 0; i < words.length && steps < 32; steps++) {
      const w = words[i];
      const word = w.text;
      if (!w.literal || word === '' || word.includes('\u0000') || /^~/.test(w.raw || '')) { unread(words, i, cond, false); return; }   // an expansion in the program's place (a tilde's HOME among them), or in an assignment's word (THE NON-LITERAL WORDS): not derived
      if (/\s/.test(word)) { unread(words, i, cond, false); return; }   // a command word holding a blank (`"$(echo 'cp a b')"`): a name no machine's PATH or filesystem ships; an assignment's word holding one stops the walk too (THE NON-LITERAL WORDS)
      if (ASSIGNMENT.test(word)) { head = false; i++; continue; }
      if (['!', '{', '}', 'if', 'then', 'elif', 'else', 'fi', 'while', 'until', 'do', 'done', 'end'].includes(word)) { i++; continue; }
      if (['for', 'foreach', 'select', 'case', '[[', '((', 'function'].includes(word)) return;
      if (!word.includes('/') && rebinding.globals.has(word)) { cannot(`${word}: a global alias's name where a command stands`); unread(words, i, cond, true); return; }   // what runs there the reader cannot know (THE REBOUND NAMES)
      if (defined.has(word) || word.startsWith('=')) { if (word.startsWith('=')) unread(words, i, cond, false); return; }   // a name the command binds, or zsh's `=name` (an expansion to a path)
      if (!word.includes('/') && reboundBy(rebinding, cmd, word)) { unread(words, i, cond, true); return; }   // a name the text rebinds (THE REBOUND NAMES): it resolves the name itself
      const base = word.slice(word.lastIndexOf('/') + 1);
      if (stops && word.includes('/') && Object.hasOwn(WRAPPERS, base) && stops.has(word)) { note(word, cond); return; }   // a wrapper's path the filter sets aside (THE WRAPPER'S PATH: a copy the text makes under a wrapper's name among them): no wrapper of this machine's
      const spec = Object.hasOwn(WRAPPERS, base) ? WRAPPERS[base] : null;
      if (spec) {
        if (!spec.own || word.includes('/') || (base === 'time' && (dashReads || feeder || !head))) note(word, cond);   // THE TIME WORD
        head = false;
        i++;
        if (spec.sub) i++;
        if (base === 'coproc' && i + 1 < words.length && ['{', '('].includes(words[i + 1].text)) i++;   // coproc NAME { .. }
        let operands = spec.operands || 0;
        while (i < words.length) {
          const t = words[i].text;
          if (t === '--') { i++; break; }
          if (spec.query && spec.query.test(t)) return;
          if (spec.text && spec.text.includes(t)) { if (words[i + 1]) readAs(true, () => readText(words[i + 1].text, depth + 1, cond)); i += 2; continue; }
          if (spec.arg && spec.arg.includes(t)) { i += 2; continue; }
          if (t === '-' || /^-./.test(t)) { i++; continue; }
          if ((spec.assign || spec.own) && (spec.assign === 'any' ? t.includes('=') : ASSIGNMENT.test(t))) { i++; continue; }
          if (operands > 0) { operands--; i++; continue; }
          break;
        }
        continue;
      }
      if (/^[-+]./.test(word)) return;   // an option where a program would stand (an inner text such as `-e -c`)
      const rest = words.slice(i + 1);
      if (SHELL_OWN.has(word)) { readOwn(word, rest, depth, cond); return; }
      if (defined.has(word)) return;
      note(word, cond);
      if (SCRIPT_SHELL.test(base)) {
        // what the shell is fed on its standard input (a here-document, a pipe, a here-string) is its script only where it has no -c text
        // and no operand, or has -s; else it runs only where the script reads it (`echo '..' | bash -c "$(awk 1)"`, whose zsh leg feeds
        // awk nothing): `collect`'s conditional mark
        const fedCond = cond || (rest.some((r) => !/^[-+]/.test(r.text)) && !rest.some((r) => /^-[A-Za-z]*s/.test(r.text) && !r.text.startsWith('--')));
        readAs(!TIME_WORD_SHELL.test(base), () => {   // THE TIME WORD: the texts this shell runs
          for (const r of rest) if (r.literal && SCRIPT_TEXT.test(r.text)) readText(r.text, depth + 1, cond);
          for (const h of seg.heredocs) readText(h, depth + 1, fedCond);
          if (feeder) for (const t of printedBy(feeder)) readText(t, depth + 1, fedCond);
          for (const s of seg.subs) for (const inner of lexOf(s).segments) for (const t of printedBy(inner)) readText(t, depth + 1, fedCond);
        });
      } else if (base === 'find') {
        for (let j = 0; j < rest.length; j++) if (['-exec', '-execdir', '-ok', '-okdir'].includes(rest[j].text)) { const end = rest.findIndex((x, n) => n > j && (x.text === ';' || x.text === '+')); readSegment({ words: rest.slice(j + 1, end < 0 ? rest.length : end), heredocs: [], subs: [], exec: true }, null, depth + 1, true); }
      } else if (base === 'capsh') {
        const dd = rest.findIndex((x) => x.text === '--');
        if (dd >= 0) readSegment({ words: [{ text: '/bin/bash', literal: true, raw: '/bin/bash' }, ...rest.slice(dd + 1)], heredocs: [], subs: [] }, null, depth + 1, cond);
      } else if (base === 'su' || base === 'runuser' || base === 'script') {
        const c = rest.findIndex((x) => x.text === '-c' || x.text === '--command');
        if (c >= 0 && rest[c + 1]) readAs(true, () => readText(rest[c + 1].text, depth + 1, cond));
      }
      return;
    }
  };
  const readOwn = (word, rest, depth, cond) => {
    if (rest.some((r) => !r.literal)) return;   // no text of a command one of whose operands the lexer does not hold as literal is read (THE NON-LITERAL WORDS, in the header)
    const lits = rest.map((r) => r.text);
    if (word === 'eval') readText(lits.join(' '), depth + 1, cond);
    else if (word === 'trap') { const ops = lits.filter((t) => t !== '--'); if (ops.length >= 2 && !/^-/.test(ops[0])) readText(ops[0], depth + 1, true); }
    else if (word === 'emulate') { const c = lits.indexOf('-c'); if (c >= 0 && lits[c + 1] !== undefined) readText(lits[c + 1], depth + 1, cond); }
    else if (word === 'alias') {   // each value the text an alias runs, but a global alias's (THE REBOUND NAMES): options first, `--` ending them
      let global = false;
      let opts = true;
      for (const t of lits) {
        if (opts && t === '--') { opts = false; continue; }
        if (opts && /^[-+]./.test(t)) { if (t.slice(1).includes('g')) global = true; continue; }
        opts = false;
        const m = t.match(/^[^=]+=(.*)$/s);
        if (m && !global) readText(m[1], depth + 1, true);
      }
    }
    else if (word === 'mapfile' || word === 'readarray') { const c = lits.indexOf('-C'); if (c >= 0 && lits[c + 1] !== undefined) readText(lits[c + 1], depth + 1, true); }
  };
  // one walk over the whole text, stopping at the wrapper paths in `at`; it returns the paths the text spells whole more often than it read them
  const walk = (at) => {
    found = [];
    asProgram = new Map();
    stops = at;
    records = [];
    cannotKnow = [];
    dashReads = true;
    readText(cmd, 0);
    return new Set(found.filter((p) => p.includes('/') && mentions(p) > (asProgram.get(p) || 0)));
  };
  const made = walk(null);
  if ([...made].some((p) => Object.hasOwn(WRAPPERS, p.slice(p.lastIndexOf('/') + 1)))) walk(made);
  if (collect) for (const r of records) collect.push(r);
  cannotKnow.forEach(tell);
  return found.filter((p) => !made.has(p));
};
// every command a leg gated with the default table, by its text: the row id the caller named (the population THE INVOKED PROGRAM's pin reads)
const GATED_ROWS = new Map();
const gatedRowId = (what) => what.replace(/^the residual table's /, '').split(', whose command names it')[0];
// THE RECORDED ABSENCES: the programs a row runs that were ABSENT where its evidence was measured, by design (the row runs a path or a name
// no system it targets has, or one it makes or binds itself before it runs it), derived by running THE INVOKED PROGRAM over every row the
// legs gate on the box that measured them (the round's r7-cifix-harvest). A program absent here changes nothing for such a row (its writers
// were measured without it), so for a program the record holds for the row, the gate turns: the row is NOT RUN where the program IS present
// (its evidence there would not be the evidence measured), and runs where it is absent. Every other program is gated on its presence. The
// pin at the end of tools/romp-track-bash-guard.test.mjs holds each entry to a program the gate derives for its row, so the record names no program a row does not run.
const RECORDED_ABSENT_GROUPS = [
  ['a path named after a shell builtin, run to measure that no file answers to it (a system that ships one, as some distributions do, gives other evidence), and the name its alias would have bound', {
    'S21-slash-set': ['/usr/bin/set'], 'S21-slash-set-head': ['/usr/bin/set'], 'S21-slash-set-script': ['/usr/bin/set'], 'S21-slash-set-root': ['/usr/bin/set'],
    'S21-slash-set-notes': ['/usr/bin/set'], 'S21-slash-set-under-sh': ['/usr/bin/set'], 'S21-slash-rel-set': ['./set'], 'S21-slash-shift': ['/usr/bin/shift'],
    'S21-slash-eval-set': ['/usr/bin/eval'], 'S21-slash-source-heredoc-set': ['/usr/bin/source'], 'S21-slash-dot-heredoc-set': ['./.'], 'S21-slash-emulate-set': ['/usr/bin/emulate'],
    'S21-slash-cd': ['/usr/bin/cd'], 'S21-slash-pushd': ['/usr/bin/pushd'], 'S21-slash-export': ['/usr/bin/export'], 'S21-slash-unset-default': ['/usr/bin/unset'],
    'S21-slash-read': ['/usr/bin/read'], 'S21-ctl-slash-alias': ['/usr/bin/alias', 'c'],
  }],
  ['a name no system has, run to measure the shells failing to find it', { 'P5-ctl-head-literal-unknown-cmd': ['frobnicate'] }],
  ['a word the lexer reads as a command where zsh reads glob syntax, which bash and dash stop at as a syntax error and never run', { 'RT-zsh-glob-group': ['r', 'eport.md'], 'RT-zsh-null-glob-qualifier': ['N', '../base/report.md'] }],
  ["the words after a subscript's operator, which a shell that splits `X[a;b]=a` there runs as a command no system has", { 'E28-split-semicolon': ['b]=a'], 'E28-split-pipe': ['b]=a'], 'E28-split-newline': ['b]=a'] }],
  // the fifty-sixth commit (the reviewer's ruling at 01:00Z, item 4): the name the row runs, which THE REBOUND NAMES read as a program once
  // hash texts stopped setting every name aside; and since the fifty-seventh, by the same mechanism, the three rows whose hash THE HASHED
  // NAMES read as binding nothing (a `t` among its option words, which prints; a `-p` after `--`, which is a name), as the shells do
  ['a name a hash binds none of (its path glued to -p and no name after it, a `t` among its option words, which prints, or its -p after `--`, which is a name), run to measure that the shells then find no program by that name', {
    'S22-ctl-hash-p-glued-no-name': ['foo'], 'S22-ctl-hash-tp-glued': ['foo'], 'S22-ctl-hash-p-glued-then-t': ['foo'], 'S22-ctl-hash-dashdash-first': ['foo'],
  }],
];
const RECORDED_ABSENT = Object.fromEntries(RECORDED_ABSENT_GROUPS.flatMap(([why, rows]) => Object.entries(rows).map(([id, programs]) => [id, { programs, why }])));
// true when every program the command names or invokes is on this box; else the NOT RUN line per missing one, naming `what`, and false.
// The table's programs spelled bare (programsNamed) keep their table's record; every program THE INVOKED PROGRAM derives is asked of THE
// ONE PRESENCE FUNCTION. `opts` is for the pins: `absent` an absent set in place of THE OVERRIDE, `PATH` a PATH the real check alone reads
// for every program (the table's records set aside), `cwd` the directory a relative path is found from (default this process's).
const namedPresent = (cmd, what, table = NAMED_PROBE, report = (line) => console.error(line), { absent = OVERRIDE_ABSENT, PATH = null, cwd = null } = {}) => {
  if (table === NAMED_PROBE && what != null && !GATED_ROWS.has(cmd)) GATED_ROWS.set(cmd, String(what));
  const named = programsNamed(cmd, table);
  const unknown = [];   // the rebindings whose names the reader cannot know (THE REBOUND NAMES): the row is NOT RUN on them
  const all = [...named, ...programsInvoked(cmd, { unknown }).filter((p) => !named.includes(p))];
  const tableRecord = (p) => (table[p] !== null && typeof table[p] === 'object' ? table[p] : { ok: !!table[p], why: table[p] ? null : 'is not on this runner' });
  const id = what == null ? null : gatedRowId(String(what));
  const recorded = id !== null && Object.hasOwn(RECORDED_ABSENT, id) ? RECORDED_ABSENT[id] : null;
  const recordOf = (p) => {
    if (recorded && recorded.programs.includes(p)) return realPresence(p, { PATH: PATH === null ? undefined : PATH, cwd }).ok ? { ok: false, why: `is on this runner, where the row's evidence was measured without it (THE RECORDED ABSENCES: ${recorded.why})` } : { ok: true, why: null };
    return PATH !== null ? presenceOf(p, { absent, PATH, cwd }) : presenceOf(p, { absent, cwd, real: Object.hasOwn(table, p) ? tableRecord(p) : null });
  };
  const records = Object.fromEntries(all.map((p) => [p, recordOf(p)]));
  const present = shellsFor(all, what, records, report).length === all.length;
  if (unknown.length) report(`NOT RUN: the command rebinds a name the reader cannot know (${unknown.join('; ')}), so its evidence leg did not run${what ? `: ${what}` : ''} (${(new Error().stack.split('\n')[1] || '').trim().replace(/^at /, '')})`);
  return present && !unknown.length;
};
// NO STARTUP FILE OF THE ACCOUNT'S (round 7 of fork PR #780 review, thirty-second commit; the round's verifiers found it at the shell
// probe). A shell a leg starts may read a startup file of the account's by three roads. zsh reads $ZDOTDIR/.zshenv, else $HOME/.zshenv,
// unless it is started with -f, and a zsh whose environment has no HOME takes the account's home from the passwd entry. bash started with
// -c and no --norc, not interactive, whose standard input is a socket (a piped spawn's is: node makes its pipes as socket pairs) and whose
// SHLVL is below 1 takes itself for a shell rshd ran and reads /etc/bash.bashrc and ~/.bashrc, the account's where HOME is unset or the
// account's, in place of BASH_ENV (bash's run_startup_files). And bash otherwise reads the file BASH_ENV names, the account's where the
// environment is inherited from this process. So every leg of the test file that ran zsh or bash under an environment of PATH alone read the account's
// ~/.zshenv or ~/.bashrc, whatever those files run, and its reading depended on them. The wrapper gives every spawn whose environment opens
// a road the environment that closes it: ZDOTDIR set to /dev/null, under which zsh finds no file and reads the system's /etc/zsh/zshenv
// alone; SHLVL set to 1, under which bash counts itself a nested shell and reads BASH_ENV alone, which a named environment carries only
// where its leg sets one; and an inherited environment without the account's BASH_ENV. A shell the leg's own command starts inherits it,
// unless the command clears or rewrites that environment first, or starts bash as a login or interactive shell, which reads its profile or
// ~/.bashrc by HOME: THE CLEARED ENVIRONMENT, below, holds those commands (the thirty-third commit: R6V-F-env-i's `env -i` took the first
// road while the thirty-second commit's census, through wrappers on PATH that an absolute path and `env -i` pass by, counted none). A
// leg whose environment names a HOME of its own (every test world's) keeps its reading, so the rows that write a .zshenv into the world's
// HOME and run zsh (RT-zshenv-home) still measure what they measure, and so does one that sets ZDOTDIR, SHLVL or BASH_ENV itself.
const ACCOUNT_HOMES = new Set([(() => { try { return os.userInfo().homedir; } catch { return null; } })(), process.env.HOME].filter(Boolean).map((h) => path.resolve(h)));
const NO_ZDOTDIR = '/dev/null';
const accountStartupRoads = (env, inherited = false) => {
  const acct = !env.HOME || ACCOUNT_HOMES.has(path.resolve(env.HOME));
  return { zshenv: acct && !env.ZDOTDIR, bashrc: acct && !(/^\d+$/.test(env.SHLVL || '') && Number(env.SHLVL) >= 1), bashEnv: inherited && env.BASH_ENV !== undefined };
};
const withoutAccountStartup = (opts) => {
  const inherited = !(opts && opts.env);
  const env = inherited ? process.env : opts.env;
  const roads = accountStartupRoads(env, inherited);
  if (!roads.zshenv && !roads.bashrc && !roads.bashEnv) return opts;
  const next = { ...env };
  if (roads.zshenv) next.ZDOTDIR = NO_ZDOTDIR;
  if (roads.bashrc) next.SHLVL = '1';
  if (roads.bashEnv) delete next.BASH_ENV;
  return { ...(opts || {}), env: next };
};
// THE CLEARED ENVIRONMENT (round 7 of fork PR #780 review, thirty-third commit; the round's verifiers on the thirty-second, LOW: that
// commit's census counted the shells its wrappers on PATH started, and R6V-F-env-i's `env -i .. /usr/bin/bash -c c` passed them by, so the
// row's bash opened the account's ~/.bashrc in every leg, bash, zsh and dash alike: under no HOME and no SHLVL, its standard input a socket,
// it took the rshd branch; strace over every process of the four modules' run found those three opens and no other). The keep-out above
// reaches a shell a leg's command starts only through the environment that shell inherits. A command that clears or rewrites that
// environment first, starts a shell by the passwd entry or by $SHELL, or starts bash as a login or interactive shell under no HOME of a
// world, takes a road the keep-out cannot close, so the wrapper reads each text a spawn hands a program (an argument holding a blank or an
// operator, and the standard input it is fed) and the spawn's other words for the spellings that do so. A clear, a road when the text
// names bash or zsh (a word whose last component is bash, rbash or zsh, one glued to an option such as env's -S, or an expansion of SHELL,
// BASH, ZSH_NAME, ZSH_ARGZERO or $0): env's clearing operands (-i or a short cluster holding it, a lone -, --ignore-environment and every
// abbreviation of it, -u or --unset naming HOME, SHLVL or ZDOTDIR, and -S or --split-string, whose string env splits into a command of its
// own); exec's -c (a cluster holding c); setpriv's --reset-env; sudo, pkexec, doas and systemd-run, which reset the environment for the
// command they run; and a word naming HOME, SHLVL or ZDOTDIR anywhere but in a read of it and in an assignment of a value that keeps its
// road shut (SHLVL a count of 1 or more; HOME or ZDOTDIR a literal absolute path that is no account home), so unset, export -n, typeset
// +x, read, printf -v and `${NAME:=word}` each count. A start of a shell the text need not name, a road wherever it stands: su, runuser,
// login, ssh, machinectl, script, tmux and screen, which start the passwd entry's shell or $SHELL, sudo's -s, -i, --shell and --login,
// and systemd-run's -S and --shell. And where the spawn's environment has no HOME of a world, a bash given a login or interactive option
// (-l, -i, --login, --rcfile, --init-file, a cluster holding l or i), `exec -l`, or an argv0 opening with `-` (`exec -a`, env's -a or
// --argv0); zsh needs no such reading, since every file of the account's it reads by name lies under the ZDOTDIR the keep-out gives. A
// road throws by name unless its text is one of CLEARED_LEGS, each run under strace in every present shell by the thirty-third commit's
// test and pinned to open no startup file under the account's home; since the fifty-first commit a row's legs run only where every
// program THE INVOKED PROGRAM derives from its text is on this box, and since the fifty-third a leg reds where its strace record shows a
// name its processes looked up found nowhere, or a path one ran absent, and since the fifty-fourth where a program word the derivation
// cannot resolve has no execve its literal operands attribute to it (THE LOOKUP RECORD, at that test). The reading
// is of spellings, read wherever they stand, a quoted text or a here-document included, so a clear before a shell it does not start costs
// a listing and nothing else.
// The thirty-fourth commit (the round's verifiers on the thirty-third, LOW: `python3 -c 'import os; os.execve("/usr/bin/bash", .., {})'`
// and `perl -e '%ENV=(); exec "/usr/bin/bash", ..'` passed the wrapper and opened the account's ~/.bashrc in every leg under strace, and
// `exec -c /proc/self/exe -c ..` its ~/.bashrc in bash's leg and its .zshenv in zsh's): the classes are a clear a program makes by its own
// call, and a shell named by a path whose last component is none of bash, rbash and zsh. The reading takes each whole where its members can
// be named. A program that runs code it is handed (CODE_RUNNER: python, perl, ruby, php, tcl, lua, node, deno, bun, gawk and awk, R, julia,
// PowerShell, osascript, a version suffix included) is a clear, since its code may clear the environment and the reader reads no code (gawk
// passes a change to ENVIRON on to what it starts, measured; mawk does not, and is not among them). A startup shell answers to every name
// it has on this box (bash's and zsh's binaries under each of their names on PATH, rzsh here, and each script on PATH whose #! line runs
// zsh, zsh5 and env_parallel.zsh here), to a /proc/<pid>/exe, which names the running shell where a shell execs it, to those names inside a
// program's code (a word split at every character a path's name does not hold), and to SHELL, BASH, ZSH_NAME and ZSH_ARGZERO named bare
// (`$ENV{SHELL}`, `os.environ["SHELL"]`). And fail closed: a clear is a road where a value the reader cannot read stands in a program's
// place (holdsUnreadName: an expansion, a glob or a leading `~` in a command word or among the operands of a program that runs its operands
// as a command, `env -i $sh -c ..` among them). The texts read are the spawn's words, each argument holding a blank or an operator, the
// standard input as a string or as bytes (one holding a NUL byte is data, an archive tar reads), each text value of an environment the
// spawn names (an exported function's body), and the content of a script a shell is started on by its path. What a reader of spellings
// still cannot read, stated as its class: a clear the text spells through an expansion (`e=env; $e -i bash`; failing closed there, on an
// unread value in a text that names a shell, flags 914 spawns of 288 distinct texts in the test module's run, none of which starts a shell
// under a cleared environment), a program the reader does not name that clears the environment by its own call or option (a compiled
// program, a wrapper whose clearing option is not listed here), code that computes a shell's name, and a shell reached by a name no text
// and no PATH entry spells (a link or copy made outside the text, a script named inside a text). The census by strace over every process of
// the four modules' run is the measurement that sees each of them.
const STARTUP_NAME = /^(?:HOME|SHLVL|ZDOTDIR)$/;
// a text's words for the reader: the reads of the three names taken out first (`$HOME`, `${HOME}`, `${HOME:-w}`, `${#HOME}`; `${HOME=w}`
// and `${HOME:=w}` assign, and stay), then split at blanks and operators, quotes and backslashes dropped
const clearedWords = (text) => String(text).replace(/\$(?:HOME|SHLVL|ZDOTDIR)(?![A-Za-z0-9_])/g, '').replace(/\$\{[#!]?(?:HOME|SHLVL|ZDOTDIR)(?=[}:#%/^,@?+[-])(?!:?=)/g, '').split(/[\s;&|()`{}<>]+/).map((w) => w.replace(/['"\\]/g, '')).filter(Boolean);
const wordBase = (w) => w.slice(w.lastIndexOf('/') + 1);
const longOf = (o, name) => o.startsWith('--') && o.length > 2 && name.startsWith(o.slice(2).split('=')[0]);   // a long option or an abbreviation of it
const ENV_CLEARERS = new Set(['sudo', 'pkexec', 'doas', 'systemd-run']);   // reset the environment for the command they run
const SHELL_STARTERS = new Set(['su', 'runuser', 'login', 'ssh', 'machinectl', 'script', 'tmux', 'screen']);   // start the passwd entry's shell, or $SHELL
// programs that run code they are handed, each able to clear or rewrite the environment of a program it starts by its own call, in code
// the reader does not read (the thirty-fourth commit): a clear, a road when the text names a startup shell
const CODE_RUNNER = /^(?:python|perl|ruby|php|tclsh|wish|expect|lua|luajit|node|nodejs|deno|bun|gawk|awk|nawk|Rscript|julia|pwsh|osascript)[\d.]*$/;
// the names a startup shell answers to (the thirty-fourth commit): bash, rbash and zsh; every file on PATH that is bash's or zsh's binary
// under another name, or a script whose #! line runs zsh; derived once, when a reading first needs them. A /proc/<pid>/exe names the
// running program, the shell itself when a shell execs it, and is read apart (PROC_EXE)
const deriveStartupShellNames = (dirs) => {
  const names = { bash: new Set(['bash', 'rbash']), zsh: new Set(['zsh']) };
  const real = (p) => { try { return fs.realpathSync(p); } catch { return null; } };
  const binary = {};
  for (const sh of Object.keys(names)) for (const d of dirs) { const r = real(path.join(d, sh)); if (r) { binary[r] = sh; break; } }
  for (const d of dirs) {
    let entries = [];
    try { entries = fs.readdirSync(d); } catch { continue; }
    for (const n of entries) {
      const r = real(path.join(d, n));
      if (r === null) continue;
      if (Object.hasOwn(binary, r)) { names[binary[r]].add(n); continue; }
      let head = '';
      try {
        const st = fs.statSync(r);
        if (!st.isFile() || !(st.mode & 0o111)) continue;
        const fd = fs.openSync(r, 'r');
        try { const b = Buffer.alloc(128); head = b.toString('latin1', 0, fs.readSync(fd, b, 0, 128, 0)); } finally { fs.closeSync(fd); }
      } catch { continue; }
      const line = head.split('\n')[0];
      if (line.startsWith('#!') && /(?:^|[\s/])zsh(?:\s|$)/.test(line)) names.zsh.add(n);
    }
  }
  return names;
};
let STARTUP_SHELL_NAMES = null;
const startupShellNames = () => (STARTUP_SHELL_NAMES ??= deriveStartupShellNames(String(process.env.PATH || '').split(':').filter(Boolean)));
const PROC_EXE = /\/proc\/[^\s/'"]*\/exe(?![\w.-])/;
const keepsRoadShut = (name, value) => (name === 'SHLVL' ? /^0*[1-9]\d*$/.test(value) : /^\/[^$`~*?[]*$/.test(value) && !ACCOUNT_HOMES.has(path.resolve(value)));
// a clear: a road when the text names bash or zsh
const clearingSpellings = (text) => {
  const found = [];
  const ws = clearedWords(text);
  for (let i = 0; i < ws.length; i++) {
    const w = ws[i];
    const base = wordBase(w);
    if (base === 'env') {
      for (let j = i + 1; j < ws.length; j++) {   // env's operands up to its command word
        const o = ws[j];
        if (o === '-') { found.push('env -'); continue; }
        if (o === '--') continue;
        if (o.startsWith('--')) {
          if (longOf(o, 'ignore-environment') || longOf(o, 'split-string')) found.push(`env ${o}`);
          else if (longOf(o, 'unset')) { const name = o.includes('=') ? o.slice(o.indexOf('=') + 1) : ws[++j] || ''; if (STARTUP_NAME.test(name)) found.push(`env ${o} ${name}`); }
          else if (!o.includes('=') && (longOf(o, 'chdir') || longOf(o, 'argv0'))) j++;   // its value word
          continue;
        }
        if (o.startsWith('-')) {
          for (let k = 1; k < o.length; k++) {
            if (o[k] === 'i') found.push(`env ${o}`);
            else if (o[k] === 'S') { found.push(`env ${o}`); break; }   // the split string: its words stand in the text, the first glued to -S
            else if (o[k] === 'u') { const name = o.slice(k + 1) || ws[++j] || ''; if (STARTUP_NAME.test(name)) found.push(`env -u ${name}`); break; }
            else if ('Ca'.includes(o[k])) { if (k === o.length - 1) j++; break; }   // the rest of the cluster, or the next word, is its value
          }
          continue;
        }
        if (/^[A-Za-z_]\w*=/.test(o)) continue;   // an assignment: the name rule below reads it
        break;
      }
    }
    if (w === 'exec') for (let j = i + 1; j < ws.length && ws[j].startsWith('-'); j++) { if (/^-[^-]*c/.test(ws[j])) found.push(`exec ${ws[j]}`); if (/^-[^-]*a$/.test(ws[j])) j++; }
    if (base === 'setpriv') for (let j = i + 1; j < ws.length; j++) if (ws[j].length >= 7 && longOf(ws[j], 'reset-env')) found.push(`setpriv ${ws[j]}`);
    if (ENV_CLEARERS.has(base)) found.push(base);
    if (CODE_RUNNER.test(base)) found.push(base);   // its own call may clear the environment, in code the reader does not read
    if (/HOME|SHLVL|ZDOTDIR/.test(w)) {
      const a = w.match(/^(HOME|SHLVL|ZDOTDIR)=(.*)$/);
      if (!(a && keepsRoadShut(a[1], a[2]))) found.push(`the name in ${w}`);
    }
  }
  return found;
};
// a text that names a startup shell: a word whose last component is a name one answers to (an argv0's leading `-` and an option glued
// before it, as env's `-Sbash` or `--split-string=zsh`, taken off), a word of it split at every character a path's name does not hold (a
// path in a program's code, `"/usr/bin/bash",`), a /proc/<pid>/exe, or an expansion of a parameter that holds a shell's path, or that
// parameter's name alone (`$ENV{SHELL}`, `os.environ["SHELL"]`)
const SHELL_PARAMS = /\$\{?(?:SHELL|BASH|ZSH_NAME|ZSH_ARGZERO|0)(?![A-Za-z0-9_])|(?<![A-Za-z0-9_$])(?:SHELL|BASH|ZSH_NAME|ZSH_ARGZERO)(?![A-Za-z0-9_])/;
const namesStartupShell = (text) => {
  const t = String(text);
  if (SHELL_PARAMS.test(t) || PROC_EXE.test(t)) return true;
  const { bash, zsh } = startupShellNames();
  const named = (w) => { const b = wordBase(w).replace(/^-/, ''); return bash.has(b) || zsh.has(b); };
  return clearedWords(t).some((w) => named(w.replace(/^--[\w-]*=/, '').replace(/^-[^-/]*S(?=.)/, ''))) || t.split(/[^\w./+-]+/).some(named);
};
// a text that may name the program a clear starts by a value the reader cannot read (fail closed, the thirty-fourth commit): a word where a
// program's name stands (a command word, the first of its piece that is no assignment and no reserved word, or any operand of a program
// that runs its operands as a command, RUNS_OPERANDS; a code runner's operands are its code, read for a shell's name alone) holding an
// expansion (a parameter other than $?, $#, $!, $- and $$, a command substitution, ANSI-C quoting), a glob (`*`, `?`, a bracket expression)
// or a leading `~`. The pieces: the text split at the operators that end or open a command (; & | ( ) { } a newline, a backtick, $( ), a
// single-quoted span and a backslash-escaped character expanding nothing
const RUNS_OPERANDS = new Set(['env', 'exec', 'command', 'builtin', 'eval', '.', 'source', 'sudo', 'doas', 'pkexec', 'run0', 'systemd-run', 'setpriv', 'nice', 'nohup', 'timeout', 'time', 'xargs', 'find', 'strace', 'ltrace', 'chroot', 'setsid', 'flock', 'stdbuf', 'ionice', 'chrt', 'taskset', 'unshare', 'nsenter', 'prlimit', 'capsh', 'eatmydata', 'fakeroot', 'perf', 'valgrind', 'busybox', 'watch', 'parallel', 'script', 'su', 'runuser', 'ssh', 'tmux', 'screen', 'sg', 'newgrp', 'sh', 'bash', 'rbash', 'zsh', 'rzsh', 'dash', 'ksh', 'mksh']);
const RESERVED = new Set(['!', 'if', 'then', 'else', 'elif', 'while', 'until', 'do', 'time', 'function', 'coproc', 'noglob', 'nocorrect']);
const unreadWord = (w) => /\$[\w{(@*'"]/.test(w.replace(/\$[?#!$-]/g, '')) || /[*?]/.test(w) || (/\[[^\]]*\]/.test(w) && w !== '[' && w !== '[[') || w.startsWith('~');
const holdsUnreadName = (text) => {
  const t = String(text).replace(/(\$?)'[^']*'/g, (m, ansi) => (ansi ? '$Q' : 'Q')).replace(/\\[\s\S]/g, 'E').replace(/\$\{[^}]*\}/g, '$V');   // an escaped character is a literal; a braced expansion one word
  for (const piece of t.split(/\$\(|[;&|(){}\n`]/)) {
    const ws = piece.split(/\s+/).map((w) => w.replace(/["\\]/g, '')).filter(Boolean);
    const c = ws.findIndex((w) => !/^[A-Za-z_]\w*=/.test(w) && !RESERVED.has(w));
    if (c < 0) continue;
    const at = RUNS_OPERANDS.has(wordBase(ws[c])) ? ws.slice(c) : [ws[c]];
    if (at.some(unreadWord)) return true;
  }
  return false;
};
// a start of a shell the text need not name: a road wherever it stands
const shellStarterSpellings = (text) => {
  const found = [];
  const ws = clearedWords(text);
  for (let i = 0; i < ws.length; i++) {
    const base = wordBase(ws[i]);
    if (SHELL_STARTERS.has(base)) found.push(base);
    if (base === 'sudo' || base === 'systemd-run') {
      for (let j = i + 1; j < ws.length && ws[j].startsWith('-') && ws[j] !== '--'; j++) {
        const o = ws[j];
        const long = base === 'sudo' ? ['shell', 'login'] : ['shell'];
        if (o.startsWith('--')) { if (long.some((n) => longOf(o, n))) found.push(`${base} ${o}`); continue; }
        const letters = base === 'sudo' ? 'si' : 'S';
        const valued = base === 'sudo' ? 'ughpCDrtTRU' : 'pEMuHG';
        for (let k = 1; k < o.length; k++) {
          if (letters.includes(o[k])) { found.push(`${base} ${o}`); break; }
          if (valued.includes(o[k])) { if (k === o.length - 1) j++; break; }
        }
      }
    }
  }
  return found;
};
// a bash started as a login or interactive shell, which reads its profile or ~/.bashrc by HOME: a road under no HOME of a world
const loginSpellings = (text) => {
  const found = [];
  const ws = clearedWords(text);
  for (let i = 0; i < ws.length; i++) {
    const w = ws[i];
    const base = wordBase(w);
    const bashName = PROC_EXE.test(w) || startupShellNames().bash.has(base.replace(/^-/, ''));
    if (bashName && base.startsWith('-')) found.push(base);
    if (bashName && !base.startsWith('-')) {
      for (let j = i + 1; j < ws.length && /^[-+]/.test(ws[j]); j++) {
        const o = ws[j];
        if (o === '--login' || o === '--rcfile' || o === '--init-file' || /^-[^-]*[li]/.test(o)) found.push(`${base} ${o}`);
        if (['--rcfile', '--init-file', '-O', '+O', '-o', '+o'].includes(o)) j++;   // its value word
      }
    }
    if (w === 'exec') {
      for (let j = i + 1; j < ws.length && ws[j].startsWith('-'); j++) {
        if (/^-[^-]*l/.test(ws[j])) found.push(`exec ${ws[j]}`);
        if (/^-[^-]*a$/.test(ws[j])) { if ((ws[j + 1] || '').startsWith('-')) found.push(`exec ${ws[j]} ${ws[j + 1]}`); j++; }
      }
    }
    if (base === 'env') {
      for (let j = i + 1; j < ws.length && ws[j].startsWith('-'); j++) {
        if ((ws[j] === '-a' || (longOf(ws[j], 'argv0') && !ws[j].includes('='))) && (ws[j + 1] || '').startsWith('-')) found.push(`env ${ws[j]} ${ws[j + 1]}`);
        else if (/^--a[a-z0-9]*=-/.test(ws[j])) found.push(`env ${ws[j]}`);
      }
    }
  }
  return found;
};
// the commands a leg may run though they clear the environment before a shell, each with the row that runs it, its cwd in the sixth
// pass's world and why no shell it starts reads a startup file of the account's (measured by the thirty-third commit's test)
const CLEARED_LEGS = new Map([
  ["env -i SHLVL=1 'BASH_FUNC_c%%=() { cp ../base/report.md report.md; }' /usr/bin/bash -c c", ['R6V-F-env-i', 'nad', 'SHLVL=1 inside the cleared environment: bash counts itself nested, takes no rshd branch and reads no startup file']],
  ["e=echo; env -i $e 'cp ../base/report.md report.md' | bash", ['S8-wp-env-i', 'nad', "the environment cleared is echo's; the bash reading the pipe is the leg shell's child and inherits its environment"]],
  ["printf '%s\\n' 'cp ../base/report.md report.md' > ../scratch/.zshenv; ZDOTDIR=../scratch zsh -c :", ['RT-zshenv-zdotdir', 'nad', "ZDOTDIR is the world's scratch/, where the row wrote the .zshenv zsh reads"]],
  ["printf '%s\\n' 'cp ../base/report.md report.md' > ../scratch/.zshenv; HOME=../scratch zsh -c :", ['RT-zshenv-home', 'nad', "HOME is the world's scratch/, where the row wrote the .zshenv zsh reads"]],
  ["mkdir -p ../scratch/z; printf 'cp ../base/report.md report.md\\n' > ../scratch/z/.zshrc; ZDOTDIR=../scratch/z zsh -i -c true", ['RT-zsh-zdotdir-i', 'nad', "ZDOTDIR is a directory under the world's scratch/, where the row wrote the .zshrc zsh reads"]],
  ["mkdir -p ../scratch/h; printf 'cp ../base/report.md report.md\\n' > ../scratch/h/.bash_profile; HOME=$PWD/../scratch/h bash -l -c true", ['RT-bash-login-home', 'nad', "HOME is a directory under the world's scratch/, where the row wrote the .bash_profile the login bash reads"]],
  ["script -qc 'cp ../base/report.md report.md' /dev/null", ['RT-script-wrapper', 'nad', "script runs its command under $SHELL, else /bin/sh; the world's environment names no SHELL", 'script']],
  ['script -qc true report.md', ['RT-script-typescript', 'nad', "script runs its command under $SHELL, else /bin/sh; the world's environment names no SHELL", 'script']],
  ['tmux -L rompguardtest new -d cp ../base/report.md report.md; while tmux -L rompguardtest has-session 2>/dev/null; do sleep 0.1; done', ['RT-tmux-new', 'nad', "tmux runs its command under the passwd entry's shell, with the world's HOME", 'tmux']],
  // the thirty-fourth commit's reading (a code runner, a value where a program's name stands), each leg found by the reader over every spawn
  // the module made at the commit before
  ["echo 'cp ../base/report.md report.md' | awk 1 | bash", ['RT-pipe-awk', 'nad', "awk starts nothing and its environment is the leg's; the bash reading the pipe is the leg shell's child and inherits its environment", 'awk']],
  ["echo 'cp ../base/report.md report.md' | bash -c \"$(awk 1)\"", ['R6Q-S-awk', 'nad', "awk runs in the command substitution of a bash -c that is the leg shell's child, inheriting its environment, and starts nothing", 'awk']],
  ['cp /usr/bin/cp ../scratch/c2; HOME=$PWD/../scratch; ~/c2 ../base/report.md report.md', ['R6Q-B-home-head', 'nad', "HOME is rewritten to the world's scratch/, and ~/c2 is the copy of cp the row made there; no shell starts"]],
  ['e=$(yes HOME=notes | head -1); eval "$e"; x=~/n1.md; printf poison > $x', ['U10a', 'na', 'eval runs the HOME=notes the pipeline printed, a rewrite of HOME, and no shell starts after it']],
]);
// the script a spawn of a shell runs by its path: the shell's first word that is no option and no option's value, unless -c or -s is given
const scriptOperand = (cmd, strs) => {
  if (!['bash', 'rbash', 'zsh', 'rzsh', 'dash', 'sh', 'ksh', 'mksh'].includes(path.basename(String(cmd)))) return null;
  for (let i = 0; i < strs.length; i++) {
    const a = strs[i];
    if (a === '--') return strs[i + 1] ?? null;
    if (!/^[-+]./.test(a)) return a;
    if (!a.startsWith('--') && /^[-+][^-]*[cs]/.test(a)) return null;
    if (['-o', '+o', '-O', '+O', '--rcfile', '--init-file'].includes(a)) i++;
  }
  return null;
};
// the reader's verdict on one spawn: null, or the text and the spellings by which a shell it starts may read the account's startup files.
// The texts: the spawn's own words; each argument holding a blank or an operator; the standard input, a string or bytes; each value of the
// environment the spawn names that holds one (an exported function's body among them); and, where the spawn runs a shell on a script by
// its path, that script's content, up to 256 KB (the thirty-fourth commit)
const clearedTexts = (cmd, args, input, namedEnv, cwd) => {
  const strs = (Array.isArray(args) ? args : []).filter((a) => typeof a === 'string');
  const isText = (a) => /[\s;&|]/.test(a);
  const fed = typeof input === 'string' ? input : ArrayBuffer.isView(input) ? Buffer.from(input.buffer, input.byteOffset, input.byteLength).toString('utf8') : '';
  const stdin = fed.includes('\0') ? '' : fed;   // a standard input holding a NUL byte is data (an archive tar reads), no text a shell runs
  const script = scriptOperand(cmd, strs);
  const files = [];
  if (script !== null) {
    try {
      const p = path.resolve(cwd ? String(cwd) : process.cwd(), script);
      const st = fs.statSync(p);
      if (st.isFile() && st.size <= 262144) files.push(fs.readFileSync(p, 'utf8'));
    } catch { /* no file of that name */ }
  }
  return [[String(cmd), ...strs.filter((a) => !isText(a))].join(' '), ...strs.filter(isText), ...(stdin ? [stdin] : []), ...Object.values(namedEnv || {}).filter((v) => typeof v === 'string' && isText(v)), ...files];
};
// `listed` the commands let through (CLEARED_LEGS; the fifty-third commit's witnesses add their own for their legs alone)
const clearedRoad = (cmd, args, env, input, { namedEnv = null, cwd = null, listed = CLEARED_LEGS } = {}) => {
  if (String(cmd) === process.execPath) return null;   // node runs the hook or a test file of the guard, whose own legs meet this wrapper there
  const noWorldHome = !env || !env.HOME || ACCOUNT_HOMES.has(path.resolve(env.HOME));
  for (const t of clearedTexts(cmd, args, input, namedEnv, cwd)) {
    if (listed.has(t)) continue;
    const starts = shellStarterSpellings(t);
    if (starts.length) return { text: t, spellings: starts };
    const clears = clearingSpellings(t);
    if (clears.length && (namesStartupShell(t) || holdsUnreadName(t))) return { text: t, spellings: clears };
    const login = noWorldHome ? loginSpellings(t) : [];
    if (login.length) return { text: t, spellings: login };
  }
  return null;
};
const CLEARED_THROW = ({ text, spellings }) => `THE CLEARED ENVIRONMENT: a leg's command clears or rewrites the environment before it starts bash or zsh, starts a shell it need not name, or starts bash as a login or interactive shell under no HOME of a world, so that shell may read a startup file of the account's (${spellings.join(', ')}): ${JSON.stringify(text).slice(0, 300)}; give the shell its keep-out in the command itself (SHLVL=1 for bash, a world's HOME or a ZDOTDIR for zsh) and list the command in CLEARED_LEGS, whose test runs it under strace`;
// THE LIVE-VALUE CHECK (round 5): the spawnSync every leg of the two test files calls. A shell the probe declined throws by name, so a leg
// written outside shellsFor cannot run that shell in silence, however its list is spelled; `table` and `raw` are parameters so
// the wrapper is pinned in-process against a synthetic table. It hands every spawn the options NO STARTUP FILE OF THE ACCOUNT'S gives,
// and throws by name for a spawn THE PROBE'S RUN or THE CLEARED ENVIRONMENT refuses.
const guardedSpawn = (table, raw, listed = CLEARED_LEGS) => (cmd, ...rest) => {
  if (Object.hasOwn(table, cmd) && !probeOk(table, cmd)) throw new Error(`a real-shell leg ran ${cmd} outside the probe: real ${cmd} ${probeWhy(table, cmd)}; ask shellsFor first`);
  const [args, opts] = splitSpawnArgs(rest);   // spawnSync(cmd, [args], [options])
  refusePipelessProbe(cmd, args, opts);
  const road = clearedRoad(cmd, args, opts && opts.env ? opts.env : process.env, opts && opts.input, { namedEnv: opts && opts.env, cwd: opts && opts.cwd, listed });
  if (road) throw new Error(CLEARED_THROW(road));
  return raw(cmd, args, withoutAccountStartup(opts));
};
const spawnSync = guardedSpawn(SHELL_PROBE, _spawnSync);

// A second scratch directory beside the project, outside every project: the target of the writes the round
// found refused although they land nowhere near a tracked file. Under os.tmpdir(), as the project is.
const outsideDir = () => fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'romp-bash-guard-outside-')));

// a file's sha256 in hex, the fingerprint the legs compare before and after a run
const shaOf = (p) => crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');

// A shell leg whose every process is waited for (the seventh verify round's tg-m7-10, 2026-10-05): the shell runs as the leader of a process group of
// its own (setsid, which does not fork where its caller leads no group, as the test's own child does not: the group's id is the leg's pid), and after
// it exits each process left in that group, a background job or a process substitution the shell does not wait for, is waited for, and killed past the
// leg's time (only the processes the leg started), so none writes into the world the next build makes: a row's `nice tee <out>/scratch/x.py > <out>/log
// 2>&1 &` (the filled-in wrapper word's remedy row, gone since) made its file after its leg had returned in 1 to 3 of 300 legs at load 33
// (tg-r-flake-race.log in the review's notes), and a build that removed out/ meanwhile failed with ENOTEMPTY on out/scratch (5 of 467 mutant runs of
// the round before). Where setsid is not on the runner the shell runs as before and nothing is waited for
const SETSID = (() => { for (const d of String(process.env.PATH || '').split(':')) { const p = path.join(d || '.', 'setsid'); try { fs.accessSync(p, fs.constants.X_OK); if (fs.statSync(p).isFile()) return p; } catch { /* the next directory */ } } return null; })();
const ledSpawn = guardedSpawn(SHELL_PROBE, (cmd, args, opts) => (SETSID ? _spawnSync(SETSID, [cmd, ...args], opts) : _spawnSync(cmd, args, opts)));   // the shell checked as this file's spawnSync checks it, then run behind setsid
const spawnLeg = (shell, argv, opts) => {
  const r = ledSpawn(shell, argv, opts);
  if (!SETSID || !r.pid) return r;
  const tick = new Int32Array(new SharedArrayBuffer(4));
  const deadline = Date.now() + (opts.timeout || 20000);
  for (let killed = false; ;) {
    try { process.kill(-r.pid, 0); } catch { break; }   // ESRCH: no process of the group is left
    if (!killed && Date.now() > deadline) { killed = true; try { process.kill(-r.pid, 'SIGKILL'); } catch { /* gone meanwhile */ } }
    Atomics.wait(tick, 0, 0, 10);
  }
  return r;
};
// The attacker's world, rebuilt before each shell run: home/, notes-api/ (tracks docs/report.md, notes/ and figs/plot.png; an
// untracked docs/REPORT.MD beside the tracked file; base/report.md, the copy source; scratch/, untracked), web/ (tracks
// docs/report.md and notes/), out/ (in no project). A row spells {W}, {NA}, {WEB} and {OUT}; `fill` puts the paths in.
const sixthPassWorld = () => {
  const W = outsideDir();
  const HOME = path.join(W, 'home');
  const NA = path.join(W, 'notes-api');
  const WEB = path.join(W, 'web');
  const OUT = path.join(W, 'out');
  const project = (root, tracked, files) => {
    fs.mkdirSync(path.join(root, '.trackchanges'), { recursive: true });
    fs.writeFileSync(path.join(root, '.trackchanges', 'config.json'), JSON.stringify({ v: 2, tracked }));
    for (const [rel, content] of Object.entries(files)) { fs.mkdirSync(path.dirname(path.join(root, rel)), { recursive: true }); fs.writeFileSync(path.join(root, rel), content); }
  };
  const build = () => {
    for (const d of [HOME, NA, WEB, OUT]) fs.rmSync(d, { recursive: true, force: true });
    fs.mkdirSync(HOME, { recursive: true });
    fs.mkdirSync(path.join(OUT, 'scratch'), { recursive: true });
    fs.writeFileSync(path.join(OUT, 'scratch', 'keep.md'), 'keep\n');
    project(NA, ['docs/report.md', 'notes/', 'figs/plot.png'], { 'docs/report.md': 'NA-ORIG\n', 'docs/REPORT.MD': 'NA-UPPER\n', 'notes/n1.md': 'NA-NOTE\n', 'figs/plot.png': 'PNG', 'base/report.md': 'NA-BASE-POISON\n', 'scratch/keep.md': 'keep\n', 'scratch/other.md': 'other\n' });
    project(WEB, ['docs/report.md', 'notes/'], { 'docs/report.md': 'WEB-ORIG\n', 'notes/n1.md': 'WEB-NOTE\n', 'base/report.md': 'WEB-BASE-POISON\n', 'scratch/keep.md': 'keep\n' });
  };
  // the tracked subset: both projects' docs/report.md and figs/plot.png by sha, and every entry under notes/
  const fingerprint = () => {
    const acc = [];
    for (const [root, tag] of [[NA, 'NA'], [WEB, 'WEB']]) {
      for (const f of ['docs/report.md', 'figs/plot.png']) { const p = path.join(root, f); acc.push(`${tag}/${f}=${fs.existsSync(p) ? shaOf(p).slice(0, 12) : 'ABSENT'}`); }
      const notes = path.join(root, 'notes');
      if (fs.existsSync(notes)) for (const n of fs.readdirSync(notes).sort()) acc.push(`${tag}/notes/${n}=${shaOf(path.join(notes, n)).slice(0, 12)}`);
    }
    return acc.join(' ');
  };
  const fill = (s) => s.replaceAll('{W}', W).replaceAll('{NA}', NA).replaceAll('{WEB}', WEB).replaceAll('{OUT}', OUT);
  const cwds = { na: NA, nas: path.join(NA, 'scratch'), nad: path.join(NA, 'docs'), nan: path.join(NA, 'notes'), out: OUT };   // nan: the tracked notes/ folder (the second fix-up's rows)
  const env = { PATH: process.env.PATH, HOME, LC_ALL: 'C.UTF-8' };
  // the hook as a process from the row's cwd, HOME the world's home
  const hook = (cmd, cwd) => { const r = spawnSync(process.execPath, [HOOK], { input: payload(cmd, cwd), encoding: 'utf8', env: { ...env, ROMP_SID } }); return { status: r.status, reason: String(r.stderr || '') }; };
  // the row run unguarded in a real shell over a fresh world: whether the tracked subset changed
  const run = (cmd, cwd, shell) => {
    build();
    const before = fingerprint();
    const argv = shell === 'bash' ? ['--norc', '--noprofile', '-c', cmd] : shell === 'zsh' ? ['-f', '-c', cmd] : ['-c', cmd];
    const r = spawnLeg(shell, argv, { cwd, input: '', encoding: 'utf8', env, timeout: 20000 });   // every process the leg started waited for (spawnLeg)
    return { changed: fingerprint() !== before, status: r.status, stderr: String(r.stderr || '').slice(0, 300) };
  };
  build();
  return { W, HOME, NA, WEB, OUT, build, fingerprint, fill, cwds, env, hook, run, rm: () => fs.rmSync(W, { recursive: true, force: true }) };
};
const BY_NAME_RE = /^Track-changes is ON for /;

// a shell's own words that read the text and run nothing (bash's, zsh's or dash's -n): THE PROBE'S RUN lets the parse check through,
// and the residual table's probes (tools/romp-track-bash-guard.test.mjs) ask it, condition (i)
const parseArgv = (shell, cmd) => (shell === 'bash' ? ['--norc', '--noprofile', '-n', '-c', cmd] : shell === 'zsh' ? ['-f', '-n', '-c', cmd] : ['-n', '-c', cmd]);   // read, not run: condition (i)

export {
  ABSENT_OVERRIDE, ACCOUNT_HOMES, BY_NAME_RE, BY_PATH_WHY, CLEARED_LEGS, CODE_RUNNER, ENV_CLEARERS, GATED_ROWS, HAS_SHELL, HOOK,
  INERT_OPTIONS, NAMED_PROBE, NAMED_PROGRAMS, NO_ZDOTDIR, OVERRIDE_ABSENT, PROBE_GUARD, PROBE_GUARD_LINE, RECORDED_ABSENT, ROMP_NOUNS,
  ROMP_SID, SCRIPT_SHELL, SHELL_PARAMETERS, SHELL_PARAMETER_NAMES, SHELL_PROBE, SHELL_STARTERS, WRAPPERS, ZSH_MODULE_BUILTINS, _spawnSync,
  absentSet, clearedRoad, deriveStartupShellNames, escapeRe, evaluate, extractWriteTargets, gatedRowId, guardedSpawn, isExecFile, lex,
  namedPresent, other, outsideDir, overrideInCi, parseArgv, payload, presenceOf, probeOk, probeShell, probeWhy, programsInvoked,
  programsNamed, proj, realPresence, report, scriptTemplateTargets, scriptWriteTargets, shaOf, shellStarterSpellings, shellsFor,
  sixthPassWorld, spawn, spawnLeg, spawnSync, startupShellNames, withoutAccountStartup, wordBase,
};
