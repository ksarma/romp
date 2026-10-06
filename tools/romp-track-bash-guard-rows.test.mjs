// The Bash-side track guard's after-source fixes (hooks/romp-track-bash-guard.mjs; plans/file-review.md, decision 47): THE
// ASSIGNING HEAD's census and the rows test, whose rows are AS1 to AS8, each row run through the hook as a process from its cwd
// and unguarded in the shells that write. They were the last two tests of tools/romp-track-bash-guard.test.mjs and moved here
// unchanged (fork PR 975, before its round 2), so node --test, which runs the files of a run side by side and the tests of one
// file one after another, runs them beside that file's tests. What both files need comes from tools/romp-track-bash-guard-testlib.mjs,
// whose import registers the scratch project's hooks here as there. Synthetic: worlds under os.tmpdir(), invented paths, no
// session data.
//
// Run: node --test tools/romp-track-bash-guard-rows.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

// a namespace import, as the shared module takes the hook, so a run against an older hook reports each test on its own
import * as guard from '../hooks/romp-track-bash-guard.mjs';
import {
  BY_NAME_RE, HAS_SHELL, HOOK, NAMED_PROBE, ROMP_NOUNS, SHELL_PROBE, WRAPPERS, escapeRe, namedPresent, outsideDir, presenceOf, programsInvoked,
  realPresence, shellsFor, sixthPassWorld, spawnLeg, spawnSync,
} from './romp-track-bash-guard-testlib.mjs';

// ── the after-source fixes (2026-10-03): the guard after a directory it does not follow ──
//
// A session's report and its derivation (every row reproduced in process and in real shells over a synthetic project) found the guard
// wrong both ways after a construct that leaves the directory unknown (a `source` or `.` of a file, a command named by a variable, a
// `cd` to a variable) and around it. The false allows: a pattern operand of a command named by a variable was dropped when the guard
// could not expand it (the directory not known, or past the caps), so `cd "$d"; "$c" report.m? < /dev/null` from the root truncated
// the tracked report while allowed (AS4-*); and a command named by a variable did not make later variable reads unreadable as a
// `source` does, so `"$PY" <file>; OUT=<project>/out; echo x > "$OUT/report.md"` wrote where the file pointed OUT (AS5-*); and, from the
// verify round, the operands of such a command behind a chdir wrapper were judged in the shell's directory (AS3-envC-*, AS3-envC-var-*),
// and a `time -o FILE` before a wrapper word the guard does not read went unjudged (AS3-time-o-*); and, from the second verify round, a filled-in
// word behind a wrapper whose output reached `|` through the closer of a group, a subshell or a compound around it (found behind nohup and setsid,
// pinned behind nice since item 3 was split out: AS3-nice-filled-group-pipe and its twins), a `[!]` or `[^]` head zsh globs (AS1-armed-neg-class-*),
// and a `time -o FILE` before `env -S`, a sudo option read as opaque or flock's `-c` (AS3-time-o-envS-out, AS3-time-o-flock-*,
// AS3-time-o-sudo-e-out), or a relative one before the road of a command named by a variable (AS3-time-o-rel-*); and, from the third verify round,
// flock's `-c` string behind a chdir wrapper, read in the shell's directory (AS3-*-flock-script), and a `time -o FILE` behind a chdir on the `env
// -S`, sudo and flock roads (AS3-time-o-envC-*, AS3-time-o-rel-envC-*); and, from the fourth verify round, a second chdir option in one env or sudo
// invocation read as a nested one (AS3-*-rpt-*), and a backup option's side-file a later bare name ran (AS8-backup-*); and, from the seventh verify
// round, a bare name a backup's stash or a written file carries, run from PATH after a builtin was turned off later in the text (AS8-builtin-gate-*,
// THE SHELL'S GATE), behind a wrapper (AS8-builtin-exec-*, -command-echo, -slash-*, -bound-env-echo), as a quoted keyword (AS8-builtin-quoted-*) and
// as dash's `builtin` (AS8-builtin-dash-builtin-*), and an abbreviation of a refused wrapper option given the long form (AS3-option-refuse-abbrev-*);
// and, from fork PR 975's round 2, a builtin's name the command shadowed with a function or an alias through a table write the guard does not read
// (AS8-builtin-shadow-*, fresh-2) or that dash looked up through PATH before `%builtin` (AS8-builtin-dash-pctbuiltin-*, correctness-3), both let
// pass by the builtin exemption that round took out (R2), with the disclosed allows fork main makes too (AS8-residual-shadow-*,
// AS8-residual-dash-pctbuiltin-echo-out, and dash's PATH-first `[`, which the bare-name lookup never searched: AS8-residual-dash-pctbuiltin-bracket*).
// The false refusals: a `[` test (AS1-*), a case pattern read as a command name (AS2-*), the poison after a command named by a variable behind a
// chain holding an external program wrapper (AS3-*-no-poison; the mechanism ruling's M1 keeps the poison behind a wrapper the shell runs itself,
// AS3-kept-*, and the directory judged unknown after it behind any wrapper, AS3-road-*, AS3-chain-*-road and AS3-*-moves), and a bare command name
// after a copy and a mention of PATH (AS8-*: since fork PR 975's item 8 as ruled a mention under a program leaves PATH readable, THE ASSIGNING HEAD,
// whose census is the test before this one, and under a PATH the guard does not read every bare name refuses again, fork main's rule, with the
// cost rows AS8-cost-*; a mention under a word the table had on the wrong side, and a name in bash's and zsh's older arithmetic `$[ ... ]`, a write
// again: AS8-root-test-v and AS8-root-test-v-path, AS8-root-jobs-x-*, AS8-root-zsh-*, AS8-root-old-arith-*, with the controls AS8-ctl-old-arith-*
// and the costs AS8-cost-old-arith-dq-target and AS8-cost-old-arith-heredoc-placeholder-out, the `$[` read as text too, any refusal of that reading standing, AS8-root-old-arith-text-*; and the
// assignments fork main does not read either, disclosed: AS8-residual-assign-*, AS8-residual-jobs-x-cp, AS8-residual-zsh-always-*, and PATH
// through zsh's `path` array, AS8-residual-path-zsh-*; and a `$[` whose bracket holds a parenthesis or opens with a space, which neither reading
// refuses, disclosed: AS8-residual-old-arith-*; a builtin's or a keyword's bare name, which the sixth verify round's tg-t6-3 had let pass, is
// refused again under that PATH since R2, its rows the costs AS8-builtin-cd-after-backup and the like); after a command named by
// a variable, a command is judged with that poison set aside too, that walk first (THE TWO WALKS and THE ORDER: AS5-read-through-*, AS5-dual-*, and the
// disclosed allows fork main makes too, AS5-residual-hidden-cd-*, AS5-residual-f3-*, AS5-residual-oldpwd-*, AS5-residual-fresh-oldpwd-out); and
// the remedies that told the person something that would not work (AS6-*, AS7-*, AS8-*, and the third verify round's AS3-nice-filled-group-pipe,
// AS8-target-head-unset, AS8-target-two-*, AS8-target-read-and and -body, AS8-target-pwd-unknown, AS8-target-oldpwd, AS6-writer-operand, and the
// sixth verify round's AS3-option-unheld-*, AS7-compare-*, AS6-script-eval-in-text-*), each refusal now naming ONE remedy, which the census at the
// end proves on every refused row by its remedied twin (M2). One false refusal these fixes lifted is back: a wrapper `nohup` or `setsid` before a
// variable, which they read as the command, refuses as behind every wrapper since that reading was split out (decision 47's follow-up, which
// discloses the spellings that pass beside it: AS3-residual-script-*). Each row: [id, cwd, command, the shells that write the tracked subset when it
// runs unguarded (null: the guard alone, its command one no leg runs), the verdict from the cwd ('allow', 'name', ['dir', text], or
// ['text', text], the text or each text of a list one the refusal must carry, a third element a text or a list of texts it must not
// carry), the verdict from a cwd in no project (null: not asked)]. The rows whose id holds `-residual-` are DISCLOSED residuals, each
// pinned with the verdict it has, allowed with the shells that write where a write gets through, refused for the parenthesized case
// pattern's false refusal (AS2-residual-paren), and named by id in decision 47: the after-source fixes' verify rounds (2026-10-03) ruled
// each a residual to state, not a road to close in this change.
// THE ASSIGNING HEAD's census (fork PR 975's round 1, item 8 as ruled, ROOT, 2026-10-05): every builtin and reserved word of bash, zsh and dash as
// installed is classified in SHELL_WORD_ASSIGNS, as a word that may assign a variable it is given (the taint set MENTION_TAINT_HEADS, derived from the
// table, which the mention rule reads) or one that assigns none, each with its reason. The populations, asked live of each shell present: bash's
// `compgen -b` and `compgen -k`; zsh's `builtins` and `reswords` keys after loading every module installed under its module_path (zsh/newuser aside,
// which defines no builtin and may run its install function), so zparseopts, vared, print and the zsh/files and zsh/system words are in it; dash has no
// list, so `type` is asked of a candidate universe (the bash and zsh populations, the committed dash list and every identifier in the dash binary) and
// the words it calls a shell builtin or keyword are its population. A shell absent on the runner (on CI's Linux runner that is zsh, since it asks bash and dash live; on the macOS cell, which has zsh, it is bash, whose 3.2.57 is below SHELL_FLOOR) is checked against the
// lists below, derived on this box on bash 5.2.21, zsh 5.9 and dash 0.5.12 by the same method; the test says which shells it asked live
const SHELL_WORDS_DERIVED = {
  bash: ['!', '.', ':', '[', '[[', ']]', 'alias', 'bg', 'bind', 'break', 'builtin', 'caller', 'case', 'cd', 'command', 'compgen', 'complete', 'compopt', 'continue', 'coproc', 'declare', 'dirs', 'disown', 'do', 'done', 'echo', 'elif', 'else', 'enable', 'esac', 'eval', 'exec', 'exit', 'export', 'false', 'fc', 'fg', 'fi', 'for', 'function', 'getopts', 'hash', 'help', 'history', 'if', 'in', 'jobs', 'kill', 'let', 'local', 'logout', 'mapfile', 'popd', 'printf', 'pushd', 'pwd', 'read', 'readarray', 'readonly', 'return', 'select', 'set', 'shift', 'shopt', 'source', 'suspend', 'test', 'then', 'time', 'times', 'trap', 'true', 'type', 'typeset', 'ulimit', 'umask', 'unalias', 'unset', 'until', 'wait', 'while', '{', '}'],
  zsh: ['!', '-', '.', ':', '[', '[[', 'alias', 'autoload', 'bg', 'bindkey', 'break', 'builtin', 'bye', 'cap', 'case', 'cd', 'chdir', 'chgrp', 'chmod', 'chown', 'clone', 'command', 'compadd', 'comparguments', 'compcall', 'compctl', 'compdescribe', 'compfiles', 'compgroups', 'compquote', 'compset', 'comptags', 'comptry', 'compvalues', 'continue', 'coproc', 'declare', 'dirs', 'disable', 'disown', 'do', 'done', 'echo', 'echotc', 'echoti', 'elif', 'else', 'emulate', 'enable', 'end', 'esac', 'eval', 'example', 'exec', 'exit', 'export', 'false', 'fc', 'fg', 'fi', 'float', 'for', 'foreach', 'function', 'functions', 'getcap', 'getln', 'getopts', 'hash', 'history', 'if', 'integer', 'jobs', 'kill', 'let', 'limit', 'ln', 'local', 'log', 'logout', 'mkdir', 'mv', 'nocorrect', 'noglob', 'pcre_compile', 'pcre_match', 'pcre_study', 'popd', 'print', 'printf', 'private', 'pushd', 'pushln', 'pwd', 'r', 'read', 'readonly', 'rehash', 'repeat', 'return', 'rm', 'rmdir', 'sched', 'select', 'set', 'setcap', 'setopt', 'shift', 'source', 'stat', 'strftime', 'suspend', 'sync', 'syserror', 'sysopen', 'sysread', 'sysseek', 'syswrite', 'test', 'then', 'time', 'times', 'trap', 'true', 'ttyctl', 'type', 'typeset', 'ulimit', 'umask', 'unalias', 'unfunction', 'unhash', 'unlimit', 'unset', 'unsetopt', 'until', 'vared', 'wait', 'whence', 'where', 'which', 'while', 'zcompile', 'zcurses', 'zdelattr', 'zf_chgrp', 'zf_chmod', 'zf_chown', 'zf_ln', 'zf_mkdir', 'zf_mv', 'zf_rm', 'zf_rmdir', 'zf_sync', 'zformat', 'zftp', 'zgdbmpath', 'zgetattr', 'zle', 'zlistattr', 'zmodload', 'zparseopts', 'zprof', 'zpty', 'zregexparse', 'zselect', 'zsetattr', 'zsocket', 'zstat', 'zstyle', 'zsystem', 'ztcp', 'ztie', 'zuntie', '{', '}'],
  dash: ['!', '.', ':', '[', 'alias', 'bg', 'break', 'case', 'cd', 'chdir', 'command', 'continue', 'do', 'done', 'echo', 'elif', 'else', 'esac', 'eval', 'exec', 'exit', 'export', 'false', 'fg', 'fi', 'for', 'getopts', 'hash', 'if', 'in', 'jobs', 'kill', 'local', 'printf', 'pwd', 'read', 'readonly', 'return', 'set', 'shift', 'test', 'then', 'times', 'trap', 'true', 'type', 'ulimit', 'umask', 'unalias', 'unset', 'until', 'wait', 'while', '{', '}'],
};
const ZSH_WORDS_SCRIPT = 'for f in $module_path/**/*.so(N); do m=${f#$module_path/}; m=${m%.so}; [[ $m == zsh/newuser ]] && continue; zmodload $m >/dev/null 2>&1; done; print -rl -- ${(k)builtins} ${(k)reswords}';
const shellWordsLive = (sh, universe = []) => {   // `sh`: a shell the probe found on this runner (the census asks shellsFor first)
  const ask = (argv, input = undefined) => String(spawnSync(sh, argv, { encoding: 'utf8', env: { PATH: process.env.PATH }, input }).stdout || '').split('\n').map((x) => x.trim()).filter(Boolean);
  if (sh === 'bash') return [...new Set(ask(['--norc', '--noprofile', '-c', 'compgen -b; compgen -k']))].sort();
  if (sh === 'zsh') return [...new Set(ask(['-f', '-c', ZSH_WORDS_SCRIPT]))].sort();
  const bin = ask(['-c', 'command -v dash'])[0];
  const binWords = bin ? [...String(fs.readFileSync(bin, 'latin1')).matchAll(/[a-z_][a-z0-9_]*|\[\[|\]\]|[.:\[!{}]/g)].map((m) => m[0]) : [];
  const cand = [...new Set([...universe, ...SHELL_WORDS_DERIVED.dash, ...binWords])].sort();
  const said = ask(['-c', 'while IFS= read -r w; do type "$w"; done'], cand.join('\n') + '\n');
  return [...new Set(said.map((l) => l.match(/^(\S+) is a (?:special )?shell (?:builtin|keyword)$/)).filter(Boolean).map((m) => m[1]))].sort();
};
// the census over populations and a table: the words no entry classifies, the entries no shell has, and the entries with no boolean or no reason
const assigningCensus = (pops, table) => {
  const all = new Set(Object.values(pops).flat());
  return {
    unclassified: Object.entries(pops).flatMap(([sh, ws]) => ws.filter((n) => !Object.hasOwn(table, n)).map((n) => `${sh} ${n}`)),
    stale: Object.keys(table).filter((n) => !all.has(n)),
    unreasoned: Object.entries(table).filter(([, v]) => !Array.isArray(v) || typeof v[0] !== 'boolean' || typeof v[1] !== 'string' || !v[1].trim()).map(([n]) => n),
  };
};
// THE CENSUS's behavioural leg (fork PR 975's gap pass, 2026-10-06; the completeness check found four words the table called assign-none that assign a
// name they are given, bash's `test -v` and `jobs -x` and zsh's break and continue, and the census, which checked only that each word was classified,
// could not see it; the gap pass's own audit found zsh's return, exit, logout, bye and sysseek beside them): every word the table calls assign-none
// that a shell present here runs as a builtin is run in that shell with operands that assign `p` if the word evaluates one as arithmetic or as a
// subscript, or runs a command its operands give (ASSIGN_SHAPES), each in a subshell of its own whose EXIT trap reports p (in zsh an `always` block
// too, since an error zsh treats as fatal there skips the trap), and a word under which p changed reds. `eval` is the control the leg must see assign
// in every shell it runs. Six words are not run, each for what running it would do (ASSIGN_LEG_SKIP); the gap pass asked them by hand with operands
// that do nothing (signal 0, a closed port on the loopback address). Reserved words are no builtins and take a grammar of their own: `[[`'s arithmetic
// comparison and zsh's repeat count are asked with one operand each (RESERVED_ASSIGN_PROBES). The leg is live only: a shell absent on the runner is not
// asked (CI's Linux runner runs the leg in bash and dash; on the macOS cell zsh runs it, and bash, 3.2.57 there, below SHELL_FLOOR, does not), and the test says which shells it ran. A sample of operand shapes, not a proof: a word that assigns only under some other
// operand is outside what the leg can see
const ASSIGN_SHAPES = [["'p=1'"], ["'0*(p=1)+1'"], ['-v', "'a[p=1]'"], ['-x', 'eval', "'p=1'"], ['eval', "'p=1'"], ["'+0*(p=1)'"], ['1', '-eq', "'0*(p=1)+1'"], ['-u', "'0*(p=1)'", "'0*(p=1)'"], ['-n', "'0*(p=1)+1'"]];
const ASSIGN_LEG_SKIP = { kill: 'sends a signal to the process its operand names', suspend: 'stops the shell', clone: 'starts a shell on the terminal it names', ztcp: 'opens a network connection', zftp: 'opens a network connection', zsocket: 'opens a socket' };
// the reserved words whose operands the shells evaluate as arithmetic, asked live where the word is the shell's own: each that assigns p there must stand on
// the may-assign side (the leg runs builtins alone; a reserved word takes its own grammar)
const RESERVED_ASSIGN_PROBES = { '[[': "[[ 1 -eq '0*(p=1)+1' ]]", repeat: "repeat '0*(p=1)+1' true" };
const ZSH_LOAD_MODULES = 'for f in $module_path/**/*.so(N); do m=${f#$module_path/}; m=${m%.so}; [[ $m == zsh/newuser ]] && continue; zmodload $m >/dev/null 2>&1; done';
// the words of `words` that `sh` (a shell the probe found) runs as a builtin; then each run under every shape: [word, the shapes under which p became 1, the shapes reported]
const assignLeg = (sh, words, root) => {
  const argvOf = (text) => (sh === 'bash' ? ['--norc', '--noprofile', '-c', text] : sh === 'zsh' ? ['-f', '-c', text] : ['-c', text]);
  const kindAsk = sh === 'bash' ? 'type -t -- "$w"' : sh === 'zsh' ? 'whence -w -- "$w"' : 'type "$w"';
  const kinds = spawnSync(sh, argvOf(`${sh === 'zsh' ? ZSH_LOAD_MODULES + '; ' : ''}while IFS= read -r w; do printf '%s\\t%s\\n' "$w" "$(${kindAsk} 2>/dev/null)"; done`), { encoding: 'utf8', env: { PATH: process.env.PATH }, input: words.join('\n') + '\n', cwd: root });
  const builtins = String(kinds.stdout || '').split('\n').map((l) => l.split('\t')).filter(([w, k]) => w && /builtin/.test(k || '')).map(([w]) => w);
  const out = [];
  for (const w of builtins) {
    if (Object.hasOwn(ASSIGN_LEG_SKIP, w)) continue;
    const call = (shape) => (w === '[' ? `[ ${shape.join(' ')} ]` : `${w} ${shape.join(' ')}`);
    const body = ASSIGN_SHAPES.map((shape, i) => (sh === 'zsh'
      ? `( p=0; trap 'echo "S${i} P=$p" >&9' EXIT; { f() { for _q in 1; do ${call(shape)}; done; }; f } always { echo "S${i} P=$p" >&9 } ) >/dev/null 2>&1 </dev/null; `
      : `( p=0; trap 'echo "S${i} P=$p" >&9' EXIT; f() { for _q in 1; do ${call(shape)}; done; }; f ) >/dev/null 2>&1 </dev/null; `)).join('');
    const cwd = fs.mkdtempSync(path.join(root, 'w-'));
    const r = spawnSync(sh, argvOf(`${sh === 'zsh' ? ZSH_LOAD_MODULES + '; ' : ''}exec 9>&1; ${body}`), { encoding: 'utf8', cwd, env: { PATH: process.env.PATH, HOME: cwd }, timeout: 60000, killSignal: 'SIGKILL' });
    assert.ok(!r.error, `the behavioural leg ran ${sh}'s ${w} to its end: ${r.error && r.error.code}`);
    const lines = String(r.stdout || '').split('\n').filter((l) => /^S\d+ P=/.test(l));
    const shapeOf = (l) => ASSIGN_SHAPES[Number(l.match(/^S(\d+)/)[1])].join(' ');
    out.push([w, [...new Set(lines.filter((l) => /P=1$/.test(l)).map(shapeOf))], new Set(lines.map(shapeOf)).size]);
  }
  return out;
};
test("fork PR 975's round 1, item 8 as ruled (ROOT), THE ASSIGNING HEAD's census: every builtin and reserved word of bash, zsh (its modules loaded) and dash, asked live where the shell is here and from SHELL_WORDS_DERIVED where it is not, is classified in SHELL_WORD_ASSIGNS as a word that may assign a variable it is given or one that assigns none, with a reason; the taint set the mention rule reads is derived from that table; a word planted unclassified reds it; and every word it calls assign-none that a shell here runs as a builtin, run with operands that assign if it evaluates one or runs a command, assigns nothing", () => {
  const live = shellsFor(['bash', 'zsh', 'dash'], "THE ASSIGNING HEAD's census");
  const pops = {};
  for (const sh of Object.keys(SHELL_PROBE).filter((x) => x !== 'dash')) pops[sh] = live.includes(sh) ? shellWordsLive(sh) : SHELL_WORDS_DERIVED[sh];
  pops.dash = live.includes('dash') ? shellWordsLive('dash', [...pops.bash, ...pops.zsh]) : SHELL_WORDS_DERIVED.dash;
  for (const sh of Object.keys(SHELL_PROBE)) assert.ok(pops[sh].length > 30, `the census has ${sh}'s words (${pops[sh].length})`);
  assert.ok(pops.zsh.includes('zparseopts') && pops.zsh.includes('vared') && pops.zsh.includes('print') && pops.bash.includes('mapfile') && pops.zsh.includes('sysread'), 'the zsh population holds the module words (zparseopts, vared, print, sysread) and bash the reader mapfile');
  const T = guard.SHELL_WORD_ASSIGNS;
  const c = assigningCensus(pops, T);
  assert.deepEqual(c.unclassified, [], 'every builtin and reserved word of the three shells is classified in SHELL_WORD_ASSIGNS');
  assert.deepEqual(c.unreasoned, [], 'each entry is a boolean with a reason');
  // an entry no shell answers is checked against the committed lists too, so a newer shell here that dropped a word does not red a runner's census
  const everywhere = new Set([...Object.values(pops).flat(), ...Object.values(SHELL_WORDS_DERIVED).flat()]);
  assert.deepEqual(Object.keys(T).filter((n) => !everywhere.has(n)), [], 'every entry is a word one of the three shells has');
  assert.deepEqual([...guard.MENTION_TAINT_HEADS].sort(), Object.keys(T).filter((n) => T[n][0] === true).sort(), 'the taint set the mention rule reads is the table\'s may-assign side, derived');
  // the function clause's words (THE ASSIGNING HEAD's function clause, extractWriteTargets): the entries whose reason says what they run may assign any name
  assert.deepEqual([...guard.FUNCTION_SOURCES].sort(), Object.keys(T).filter((n) => T[n][1].includes('may assign any name')).sort(), 'FUNCTION_SOURCES is the table\'s entries whose reason says what they run may assign any name, derived');
  assert.ok(['eval', 'source', '.', 'trap', 'emulate', 'autoload', 'functions'].every((n) => guard.FUNCTION_SOURCES.has(n)) && [...guard.FUNCTION_SOURCES].every((n) => guard.MENTION_TAINT_HEADS.has(n)), 'a text this shell runs and a word that defines a function stand among them, each on the may-assign side');
  // the words the walk already reads as assigners stand on the may-assign side (NAME_OPERAND_COMMANDS, VAR_ASSIGNERS, the builtins of VAR_POISONERS)
  const hookSrc = fs.readFileSync(HOOK, 'utf8');
  const setOf = (name) => { const at = hookSrc.indexOf(`const ${name} = new Set([`); return at < 0 ? [] : [...hookSrc.slice(at, hookSrc.indexOf(']);', at)).matchAll(/'([^']+)'/g)].map((m) => m[1]); };
  for (const name of ['NAME_OPERAND_COMMANDS', 'VAR_ASSIGNERS', 'VAR_POISONERS']) {
    const ws = setOf(name).filter((n) => Object.hasOwn(T, n));
    assert.ok(ws.length > 0, `the census reads ${name} from the hook`);
    assert.deepEqual(ws.filter((n) => !guard.MENTION_TAINT_HEADS.has(n)), [], `${name}'s builtins are on the may-assign side`);
  }
  // the census reds: a word no entry classifies, an entry with no reason
  assert.deepEqual(assigningCensus({ ...pops, bash: [...pops.bash, 'zz_planted'] }, T).unclassified, ['bash zz_planted'], 'the census reds on a planted unclassified word');
  assert.deepEqual(assigningCensus(pops, { ...T, read: [true, ''] }).unreasoned, ['read'], 'the census reds on an entry with no reason');
  console.log(`# THE ASSIGNING HEAD's census: ${Object.keys(T).length} words (${guard.MENTION_TAINT_HEADS.size} may assign, ${Object.keys(T).length - guard.MENTION_TAINT_HEADS.size} assign none); asked live of ${live.join(', ') || 'no shell'}; from SHELL_WORDS_DERIVED for ${['bash', 'zsh', 'dash'].filter((s) => !live.includes(s)).join(', ') || 'no shell'}; populations bash ${pops.bash.length}, zsh ${pops.zsh.length}, dash ${pops.dash.length}`);
  // the behavioural leg: each assign-none word a shell here runs as a builtin assigns nothing under the shapes; the control, eval, assigns in each shell
  const none = Object.keys(T).filter((n) => T[n][0] === false);
  const root = outsideDir();
  try {
    const ran = [];
    const assigning = [];
    let unreported = 0;
    for (const sh of live) {
      const [[, controlHits]] = assignLeg(sh, ['eval'], root);
      assert.ok(controlHits.includes("'p=1'"), `the behavioural leg sees ${sh}'s eval assign p (the control): ${controlHits.join(' | ')}`);
      const got = assignLeg(sh, none, root);
      assert.ok(got.length > 10, `the behavioural leg ran ${sh}'s assign-none builtins (${got.length})`);
      for (const [w, hits, reported] of got) {
        ran.push(`${sh} ${w}`);
        if (hits.length) assigning.push(`${sh} ${w}: ${hits.join(' | ')}`);
        assert.ok(reported > 0, `the behavioural leg heard from ${sh}'s ${w} under some shape`);
        unreported += ASSIGN_SHAPES.length - reported;
      }
    }
    assert.deepEqual(assigning, [], 'no word the table calls assign-none assigns the name an operand gives it, in any shell here (each one listed belongs on the may-assign side)');
    const reservedSeen = [];
    for (const sh of live) {
      for (const [w, text] of Object.entries(RESERVED_ASSIGN_PROBES)) {
        const argv = sh === 'bash' ? ['--norc', '--noprofile', '-c', `p=0; ${text}; echo "P=$p"`] : sh === 'zsh' ? ['-f', '-c', `p=0; ${text}; echo "P=$p"`] : ['-c', `p=0; ${text}; echo "P=$p"`];
        const r = spawnSync(sh, argv, { encoding: 'utf8', env: { PATH: process.env.PATH }, cwd: root });
        if (!/^P=1$/m.test(String(r.stdout || ''))) continue;
        reservedSeen.push(`${sh} ${w}`);
        assert.equal(T[w][0], true, `${sh}'s ${w} assigns the name in its arithmetic operand, so it stands on the may-assign side`);
      }
    }
    if (live.includes('bash')) assert.ok(reservedSeen.includes('bash [['), "bash's `[[` assigned in its arithmetic comparison (the reserved words' probe ran)");
    console.log(`# THE ASSIGNING HEAD's behavioural leg: ${ran.length} (shell, word) pairs run in ${live.join(', ') || 'no shell'} under ${ASSIGN_SHAPES.length} operand shapes, none assigning; reserved words seen assigning ${reservedSeen.join(', ') || 'none'}, each on the may-assign side; ${unreported} (word, shape) runs reported nothing (an error the shell treats as fatal before the operand is read); not run: ${Object.keys(ASSIGN_LEG_SKIP).join(', ')}`);
  } finally { spawnSync('chmod', ['-R', 'u+rwx', root]); fs.rmSync(root, { recursive: true, force: true }); }
});
test("fork PR 975's round 2, R1 (RULE S), the second axes: THE NAME-RUN AXIS classifies every builtin and reserved word of bash, zsh and dash as one that may change what a name runs or one that does not, option-insensitive, with a reason, and a planted word reds it; and THE COMMAND TABLES, the special parameters a word may write to redefine a head, are each a special parameter of an installed shell, a planted name none", () => {
  const live = shellsFor(['bash', 'zsh', 'dash'], 'RULE S censuses');
  const pops = {};
  for (const sh of Object.keys(SHELL_PROBE).filter((x) => x !== 'dash')) pops[sh] = live.includes(sh) ? shellWordsLive(sh) : SHELL_WORDS_DERIVED[sh];
  pops.dash = live.includes('dash') ? shellWordsLive('dash', [...pops.bash, ...pops.zsh]) : SHELL_WORDS_DERIVED.dash;
  // clause (c): THE NAME-RUN AXIS, over the same population as THE ASSIGNING HEAD's census, derived from the same table
  const R = guard.NAME_RUN_AXIS;
  const rc = assigningCensus(pops, R);
  assert.deepEqual(rc.unclassified, [], 'every builtin and reserved word of the three shells is classified on THE NAME-RUN AXIS');
  assert.deepEqual(rc.stale, [], 'every NAME-RUN entry is a word one of the three shells has');
  assert.deepEqual(rc.unreasoned, [], 'each NAME-RUN entry is a boolean with a reason');
  assert.deepEqual([...guard.NAME_RUN_CHANGERS].sort(), Object.keys(R).filter((n) => R[n][0] === true).sort(), 'NAME_RUN_CHANGERS is the axis\'s may-change side, derived');
  assert.ok(['autoload', 'functions', 'typeset', 'declare', 'readonly', 'enable', 'disable', 'alias', 'unalias', 'hash', 'unhash'].every((n) => guard.NAME_RUN_CHANGERS.has(n)), 'autoload, typeset, declare, readonly (zsh `readonly -fu`) and the table builtins stand on the may-change side (option-insensitive)');
  assert.deepEqual(['echo', 'true', 'cd', 'read', 'export', 'local', 'pwd', 'printf', 'eval'].filter((n) => Object.hasOwn(R, n) && R[n][0]), [], 'a program-like builtin that assigns or runs but changes no function, alias, builtin or hash entry is not on the may-change side');
  assert.deepEqual(assigningCensus({ ...pops, bash: [...pops.bash, 'zz_planted'] }, R).unclassified, ['bash zz_planted'], 'the NAME-RUN census reds on a planted unclassified word');
  assert.deepEqual(assigningCensus(pops, { ...R, read: [true, ''] }).unreasoned, ['read'], 'the NAME-RUN census reds on an entry with no reason');
  // clause (b): THE COMMAND TABLES, each verified as a special parameter of an installed shell (a word that writes one redefines a head)
  const T = guard.NAME_TABLE_PARAMS;
  assert.ok(T.size > 0, 'THE COMMAND TABLES set is non-empty');
  const ask = (sh, argv) => String(spawnSync(sh, argv, { encoding: 'utf8', env: { PATH: process.env.PATH } }).stdout || '');
  const special = new Set();
  if (live.includes('bash')) for (const n of T) if (ask('bash', ['--norc', '--noprofile', '-c', `printf '%s' "\${${n}@a}"`]).includes('A')) special.add(n);
  if (live.includes('zsh')) for (const n of T) if (/association|array/.test(ask('zsh', ['-f', '-c', `print -rn -- "\${(t)${n}}"`]))) special.add(n);
  if (live.includes('bash') || live.includes('zsh')) {
    assert.deepEqual([...T].filter((n) => !special.has(n)), [], 'every committed command table is a writable special parameter of an installed shell');
    if (live.includes('bash')) assert.ok(!ask('bash', ['--norc', '--noprofile', '-c', 'printf "%s" "${ZZ_NOT_A_TABLE@a}"']).includes('A'), 'a planted name is no command-table special parameter in bash');
    if (live.includes('zsh')) assert.ok(!/association|array/.test(ask('zsh', ['-f', '-c', 'print -rn -- "${(t)ZZ_NOT_A_TABLE}"'])), 'a planted name is no command-table special parameter in zsh');
  }
  console.log(`# RULE S: THE NAME-RUN AXIS ${Object.keys(R).length} words (${guard.NAME_RUN_CHANGERS.size} may change a name, ${Object.keys(R).length - guard.NAME_RUN_CHANGERS.size} do not); THE COMMAND TABLES ${T.size}, verified special in ${special.size ? live.filter((s) => s !== 'dash').join(', ') || 'no shell' : 'no shell'}`);
});
test("fork PR 975's round 2, R1 (RULE S), clause (a) SAFE SYNTAX at every nesting level: ruleSafeOf recognizes the safe word forms and the safe syntax positively and fails on anything else, at the top level and nested in a subshell, a brace group, a command substitution, a process substitution, a pipeline, a `&&` list and an unquoted here-document body; a quoted here-document body stays literal", () => {
  // the safe word forms (a): literal, quoted, glob, the plain/braced/special/positional parameters and the default/alternative/length/suffix/prefix ${} forms, command and process substitution; and the safe syntax: a subshell, a brace group, a pipeline, a list
  const SAFE = [
    'cp a b', 'grep -c PATH f', 'echo "the PATH line"', 'sed -n /PATH/p f', 'cp a.md scratch/keep.bak; grep -c PATH f; echo done',
    'echo $x ${y} "$z" plain *.md', 'echo ${x:-y} ${x-y} ${x:+y} ${x+y} ${#x} ${x%w} ${x%%w} ${x#w} ${x##w}', 'echo ${1} $? $$ $@ $# $0 $! $- $*',
    'cat <(cmd a b)', 'echo $(cmd)`other`', 'foo=$(bar) baz', 'echo {1..3} {a,b}', '( echo hi )', '{ grep PATH f; }', 'echo ${x:-$(c)} ${x#$(d)}',
    'cmd a && cmd2 b || cmd3', 'true | grep PATH', "cat <<EOF\n$(cp a b)\nEOF", "cat <<'EOF'\n$((x=1)) {p}>f ${x/a/b}\nEOF",
  ];
  // the forms rule S must fail on: arithmetic, a {NAME} descriptor redirection, a function definition, an array assignment, extglob, a glob qualifier, the other ${} forms, a command-table word, a may-change head
  const UNSAFE = [
    'echo $((x+1))', 'echo $[p=0]', '(( x = 1 ))', 'for ((i=0;i<3;i++)); do :; done', 'true {p}>/dev/null', ': {p}>out', 'true {p[0]}>f', 'true {p}<f', 'true {p}>>f', 'x=1 true {p}>/dev/null',
    'f() { :; }', 'function g { :; }', 'arr=(a b c)', 'cat *(.)', 'echo @(a|b)',
    'echo ${x/a/b}', 'echo ${x//a/b}', 'echo ${x[0]}', 'echo ${!x}', 'echo ${x:2:3}', 'echo ${x^^}', 'echo ${x@P}', 'echo ${(U)x}', 'echo ${x:=y}', 'echo ${x=y}',
    'BASH_ALIASES[ls]=rm', 'functions[g]=x', 'galiases[g]=x', 'autoload -Uz g', 'typeset -fu g', 'declare -fu g', 'readonly -fu g', 'enable -n cd', 'alias g=rm', 'unalias g', 'hash -p /x y',
    "'typeset' -fu g", '"declare" -fu g', '\\typeset -fu g',   // clause (c) reads the head's quote-removed text: a quoted or escaped may-change head is unsafe (the shell still runs the builtin)
  ];
  const nest = {
    top: (f) => f, subshell: (f) => `( ${f} )`, braceGroup: (f) => `{ ${f}; }`, cmdSubst: (f) => `echo $(${f})`,
    procSubst: (f) => `cat <(${f})`, heredoc: (f) => `cat <<EOF\n$(${f})\nEOF`, pipe: (f) => `true | ${f}`, andOr: (f) => `true && ${f}`,
  };
  const over = [];
  const miss = [];
  for (const f of SAFE) { if (!guard.ruleSafeOf(f, null)) over.push(`top: ${JSON.stringify(f)}`); }
  for (const [lvl, wrap] of Object.entries(nest)) for (const f of UNSAFE) { if (guard.ruleSafeOf(wrap(f), null)) miss.push(`${lvl}: ${JSON.stringify(wrap(f))}`); }
  // a safe fragment nested in each safe construct stays safe (the relaxation is kept where the whole command is safe)
  for (const [lvl, wrap] of Object.entries(nest)) for (const f of ['grep -c PATH f', 'cp a b', 'echo ${x:-y}']) { if (!guard.ruleSafeOf(wrap(f), null)) over.push(`${lvl}: ${JSON.stringify(wrap(f))}`); }
  // a direct (uncollapsed) arithmetic or unsafe ${} in an unquoted here-document body is unsafe; a quoted body is literal
  for (const d of ['cat <<EOF\n$((x=1))\nEOF', 'cat <<EOF\n$[x=1]\nEOF', 'cat <<EOF\ntext ${y/a/b}\nEOF']) { if (guard.ruleSafeOf(d, null)) miss.push(`heredocDirect: ${JSON.stringify(d)}`); }
  assert.deepEqual(miss, [], `rule S fails on every unsafe form at every nesting level (${miss.length} slipped through)`);
  assert.deepEqual(over, [], `rule S keeps the relaxation for every safe form (${over.length} over-refused)`);
  // a printf -v command-table write is unsafe in the shell that runs it (clause b over the resolved name); in a subshell (a command or process substitution, a pipe) it redefines nothing in the parent, so it is not flagged there
  assert.ok(!guard.ruleSafeOf('printf -v "aliases[ls]" read', null) && !guard.ruleSafeOf('{ printf -v "functions[g]" x; }', null), 'a printf -v write of a command table is unsafe in the parent shell');
  console.log(`# RULE S clause (a): ${SAFE.length} safe forms kept, ${UNSAFE.length} unsafe forms each failed at ${Object.keys(nest).length} nesting levels`);
});
test("the after-source fixes, the rows: a pattern operand of a command named by a variable is judged by its spelling where the directory is not known and refused past the caps, a command named by a variable makes later variable reads unreadable, a `[` and a case pattern are no pattern the command name stands for, a word the shell fills in behind nohup or setsid refuses as behind every wrapper, a mention of PATH under a program leaves PATH readable while every bare name under a PATH the guard does not read refuses once a path is bound, a command after a command named by a variable is judged with its names read as fork main read them as well, that walk first, and each remedy says what works; each with the shells that write", () => {
  const w = sixthPassWorld();
  const savedHome = process.env.HOME;
  process.env.HOME = w.HOME;
  try {
    const A = ['bash', 'zsh', 'dash'];
    const BZ = ['bash', 'zsh'];
    const N = [];
    const ENV = '{OUT}/scratch/keep.md';   // a file the guard does not read: sourcing it leaves the directory unknown (its one line runs a command no shell finds)
    // two texts a command named by a variable may source (`.` read into the variable), written beside the world, which each build keeps:
    // a DEBUG trap that points OUT at the tracked folder before every later command, and a plain assignment of OUT
    fs.writeFileSync(path.join(w.W, 'debug-trap.sh'), `trap 'OUT=${w.NA}/docs' DEBUG\n`);
    fs.writeFileSync(path.join(w.W, 'set-out.sh'), `OUT=${w.NA}/docs\n`);
    // a program the world holds whose name no command has (THE BOUND NAME's writer into a directory, C): it copies onto the tracked report when run
    fs.mkdirSync(path.join(w.W, 'tools'), { recursive: true });
    fs.writeFileSync(path.join(w.W, 'tools', 'w2'), `#!/bin/sh\ncp '${w.NA}/base/report.md' '${w.NA}/docs/report.md'\n`, { mode: 0o755 });
    const POISONED = 'an earlier `"$c"`, a command name that stands for a text I do not read, may assign any name';
    const REMEDY_ABS = 'Spell the path out as an absolute path: ';   // the ONE remedy a not-literal refusal names (the mechanism ruling, 2026-10-03, M2: the literal-value and command-path clauses the rounds before offered, which did not always lift, are gone)
    const NO_CURE = ['give the variable a literal value', 'name each command named by a variable', 'give each variable'];   // none of the removed cure clauses survives on any refusal
    const rows = [
      // item 4 (FIX 3): the pattern operand of a command named by a variable, after a construct that leaves the directory unknown (tee, the
      // command the variable holds, truncates the tracked report through the pattern); the twins: the same from a cwd in no project, a literal
      // operand, a known command, a known directory
      ['AS4-cd-glob', 'na', 'read d <<< docs; read c <<< tee; cd "$d"; "$c" report.m? < /dev/null', BZ, ['dir', 'names report.m?, a relative path']],
      ['AS4-cd-glob-heredoc-reads', 'na', 'read d <<EOF\ndocs\nEOF\nread c <<EOF\ntee\nEOF\ncd "$d"; "$c" report.m? < /dev/null', A, ['dir', 'names report.m?, a relative path']],
      ['AS4-source-glob', 'na', `read c <<< tee; source ${ENV}; "$c" docs/report.m? < /dev/null`, BZ, ['dir', 'names docs/report.m?, a relative path']],
      ['AS4-dot-glob', 'na', `read c <<< tee; . ${ENV}; "$c" docs/report.m? < /dev/null`, BZ, ['dir', 'names docs/report.m?, a relative path']],
      ['AS4-head-glob', 'na', 'read c <<< tee; "$c" -c x; "$c" docs/report.m? < /dev/null', BZ, ['dir', 'names docs/report.m?, a relative path']],
      ['AS4-ctl-literal', 'na', 'read d <<< docs; read c <<< tee; cd "$d"; "$c" report.md < /dev/null', BZ, ['dir', 'names report.md, a relative path']],
      ['AS4-ctl-known-command', 'na', 'read d <<< docs; cd "$d"; tee report.m? < /dev/null', BZ, ['text', 'names report.m?, which is not a literal path']],
      ['AS4-ctl-known-dir', 'na', 'read c <<< tee; "$c" docs/report.m? < /dev/null', BZ, 'name'],
      ['AS4-ctl-out-abs', 'out', 'read d <<< docs; read c <<< tee; cd "$d"; "$c" {OUT}/scratch/kee? < /dev/null', N, 'allow', null],
      // item 5: a command named by a variable may be `.` or eval and assign any name, so the variables read after it are unreadable, as after a
      // `source` (the value the guard read for OUT is not the one the shell uses: the sourced trap or assignment points it at the tracked folder);
      // the twins: a backgrounded or piped command (a subshell: it assigns nothing here), the command's own redirection (expanded before it runs),
      // the same from a cwd in no project (the ruled residual), and the source the rule already read so
      ['AS5-semi', 'na', 'read c <<< .; "$c" {W}/debug-trap.sh; OUT={NA}/out; echo x > "$OUT/report.md"', BZ, ['text', [`which is not a literal path (${POISONED}, so I do not read \`$OUT\` here)`, REMEDY_ABS], NO_CURE]],
      ['AS5-newline', 'na', 'read c <<< .\n"$c" {W}/debug-trap.sh\nOUT={NA}/out\necho x > "$OUT/report.md"', BZ, ['text', `which is not a literal path (${POISONED}, so I do not read \`$OUT\` here)`]],
      ['AS5-before', 'na', 'OUT={NA}/out; read c <<< .; "$c" {W}/set-out.sh; echo x > "$OUT/report.md"', BZ, ['text', `which is not a literal path (${POISONED}, so I do not read \`$OUT\` here)`]],
      ['AS5-ctl-bg', 'na', 'read c <<< .; "$c" {W}/set-out.sh & OUT={NA}/out; echo x > "$OUT/report.md"', N, 'allow'],
      ['AS5-ctl-pipe', 'na', 'read c <<< .; "$c" {W}/set-out.sh | cat; OUT={NA}/out; echo x > "$OUT/report.md"', N, 'allow'],
      ['AS5-ctl-own-redirect', 'na', 'OUT={NA}/docs; read c <<< cat; "$c" {W}/set-out.sh > "$OUT/report.md"', BZ, 'name', 'name'],
      ['AS5-ctl-own-redirect-untracked', 'na', 'OUT={NA}/scratch; read c <<< cat; "$c" {W}/set-out.sh > "$OUT/log"', N, 'allow'],
      ['AS5-ctl-source', 'na', `source ${ENV}; OUT={NA}/out; echo x > "$OUT/report.md"`, N, ['text', ['(an earlier `source` may assign any name, so I do not read `$OUT` here)', REMEDY_ABS], NO_CURE]],
      // item 5's cost, disclosed: from a tracked cwd, after a command named by a variable, a later variable read, a `~/` write and a bare cd are
      // refused (none writes a tracked file here), and the HOME refusal names the construct; from a cwd in no project each stays allowed
      ['AS5-cost-var', 'na', 'read c <<< true; "$c" x; OUT={OUT}/o; mkdir -p "$OUT"; echo y > "$OUT/a.txt"', N, ['text', [`(${POISONED}, so I do not read \`$OUT\` here)`, REMEDY_ABS], NO_CURE]],
      ['AS5-ctl-cost-var-literal-head', 'na', 'read c <<< true; /usr/bin/true x; OUT={OUT}/o; mkdir -p "$OUT"; echo y > "$OUT/a.txt"', N, 'allow'],   // an allowed control: a command named by its literal path takes no poison (not the remedy the refusal gives, which is the path spelled absolute: M2)
      ['AS5-ctl-cost-var-bg', 'na', 'read c <<< true; "$c" x & OUT={OUT}/o; mkdir -p "$OUT"; echo y > "$OUT/a.txt"', N, 'allow'],   // an allowed control: a backgrounded command assigns nothing here
      // THE UNREAD HEAD's names reach no further than the shell the command runs in (fork PR 975's round 1, B, 2026-10-05): a subshell's names do not come back,
      // so the poison ends at its close (this was a stated cost, poisoned as `(source f)`), and the body of a function the command defines and never calls
      // assigns nothing; inside the subshell the poison holds, and a call of the function poisons as a call does
      ['AS5-subshell-no-poison', 'na', 'read c <<< true; ("$c" x); T={OUT}/t; mkdir -p "$T"; echo y > "$T/a.txt"', N, 'allow'],
      ['AS5-uncalled-no-poison', 'na', 'read c <<< true; f() { "$c" x; }; T={OUT}/t; mkdir -p "$T"; echo y > "$T/a.txt"', N, 'allow'],
      ['AS5-subshell-poison-inside', 'na', 'read c <<< true; T={OUT}/t; ( "$c" x; mkdir -p "$T"; echo y > "$T/a.txt" )', N, ['text', `(${POISONED}, so I do not read \`$T\` here)`]],
      ['AS5-subshell-source-poison', 'na', `read c <<< true; ( "$c" x; source ${ENV} ); T={OUT}/t; mkdir -p "$T"; echo y > "$T/a.txt"`, N, ['text', '(an earlier `source` may assign any name, so I do not read `$T` here)']],   // a source inside the subshell keeps the poison after its close, as \`(source f)\` does; since fork PR 975's round 2 (R5, THE ORDER) the text is fork main's reading's, the head's poison set aside, so the source's poison is the one it names
      ['AS5-called-poison', 'na', 'read c <<< true; f() { "$c" x; }; f; T={OUT}/t; mkdir -p "$T"; echo y > "$T/a.txt"', N, ['text', 'an earlier call of `f`, a function the command defines, may assign any name']],
      // fork main's reading of the names (the same round, B; the round's regression-1): from a cwd in no project the poison had dropped a target the
      // value the command gave puts on a tracked file, where fork main read it and refused by name; THE TWO WALKS (item 8 as ruled, DUAL) walk such a
      // command again with that one poison set aside, so each is refused by name again: the value given before the head and after it, a value built
      // from another after it, a `~/` path, a cd to the value, a `sed -i`, an operand of a second command named by a variable, and the head in an if body
      ['AS5-read-through-before-out', 'out', 'X={NA}/docs; read c <<< true; "$c" x; echo y > "$X/report.md"', BZ, 'name', null],
      ['AS5-read-through-after-out', 'out', 'read c <<< true; "$c" x; X={NA}/docs; echo y > "$X/report.md"', BZ, 'name', null],
      ['AS5-read-through-built-out', 'out', 'Y={NA}; read c <<< true; "$c" x; X=$Y/docs; echo y > "$X/report.md"', BZ, 'name', null],
      ['AS5-read-through-home-out', 'out', 'read c <<< true; "$c" x; echo y > ~/../notes-api/docs/report.md', BZ, 'name', null],
      ['AS5-read-through-cd-out', 'out', 'X={NA}/docs; read c <<< true; "$c" x; cd "$X"; echo y > report.md', BZ, 'name', null],
      ['AS5-read-through-sedi-out', 'out', 'X={NA}/docs; read c <<< true; "$c" x; sed -i s/N/M/ "$X/report.md"', BZ, 'name', null],
      ['AS5-read-through-operand-out', 'out', 'X={NA}/docs; read c <<< true; "$c" x; read e <<< tee; "$e" "$X/report.md" < /dev/null', BZ, 'name', null],
      ['AS5-read-through-if-out', 'out', 'X={NA}/docs; read c <<< true; if true; then "$c" x; fi; echo y > "$X/report.md"', BZ, 'name', null],
      ['AS5-read-through-subshell-out', 'out', 'X={NA}/docs; read c <<< true; ("$c" x); echo y > "$X/report.md"', BZ, 'name', null],
      ['AS5-read-through-uncalled-out', 'out', 'X={NA}/docs; read c <<< true; f() { "$c" x; }; echo y > "$X/report.md"', BZ, 'name', null],
      // the control: a value the command gives on no tracked file stays allowed from a cwd in no project (the ruled residual: AS5-semi's twin there)
      ['AS5-ctl-read-through-untracked-out', 'out', 'X={OUT}/scratch; read c <<< true; "$c" x; echo y > "$X/a.txt"', N, 'allow', null],
      // the walk with that poison set aside (judge's first since fork PR 975's round 2, THE ORDER) reads every name fork main's valueOf reads, PWD and
      // OLDPWD among them (the reviewer's t8-2 on fork PR 975's round 1 pass, whose census of the read-through's names is moot with the read-through
      // gone): after a cd through a value THE UNREAD HEAD's names hid, `$PWD` is that directory and `$OLDPWD` the one it left, each read as fork main read
      // it; the controls name an untracked directory
      ['AS5-read-through-pwd-out', 'out', 'X={NA}/docs; read c <<< true; "$c" x; cd "$X"; echo y > "$PWD/report.md"', BZ, 'name', null],
      ['AS5-read-through-oldpwd-out', 'out', 'X={NA}/docs; read c <<< true; "$c" x; cd "$X"; cd {OUT}; echo y > "$OLDPWD/report.md"', BZ, 'name', null],
      ['AS5-ctl-read-through-pwd-untracked-out', 'out', 'X={OUT}/scratch; read c <<< true; "$c" x; cd "$X"; echo y > "$PWD/a.txt"', N, 'allow', null],
      ['AS5-ctl-read-through-oldpwd-untracked-out', 'out', 'X={OUT}/scratch; read c <<< true; "$c" x; cd "$X"; cd {OUT}; echo y > "$OLDPWD/a.txt"', N, 'allow', null],
      // THE TWO WALKS (item 8 as ruled, DUAL): a command that met a command named by a variable is walked with that head's poison set aside as well as
      // with it taken (the walk with it set aside first since fork PR 975's round 2, THE ORDER), so every reading fork main gave stands beside the
      // poisoned one, not only those a read-through site named: after a cd through the hidden value a target the guard cannot read is in play again (the
      // reviewer's m10-3: a value made by a substitution, a pattern, an operand, `$PWD` in a fresh shell), and a copy into the value's directory and a
      // `sed -i` on a pattern there are refused by name; each passed at the pass before from a cwd in no project while bash and zsh wrote; a head inside a
      // substitution carries the switch into its text; the control names an untracked directory
      ['AS5-dual-held-unread-target-out', 'out', 'X={NA}/docs; read c <<< true; "$c" x; cd "$X"; n=$(date +report.md); echo y > "$n"', BZ, ['text', 'names "$n", which is not a literal path'], null],
      ['AS5-dual-held-glob-out', 'out', 'X={NA}/docs; read c <<< true; "$c" x; cd "$X"; echo y > report.m?', BZ, 'name', null],
      ['AS5-dual-held-unread-operand-out', 'out', 'X={NA}/docs; read c <<< true; "$c" x; cd "$X"; n=$(date +report.md); cp {NA}/base/report.md "$n"', BZ, ['text', 'names "$n", which is not a literal path'], null],
      ['AS5-dual-fresh-pwd-out', 'out', `X={NA}/docs; read c <<< true; "$c" x; cd "$X"; bash -c 'echo y > "$PWD/report.md"'`, BZ, ['text', 'names "$PWD/report.md", which is not a literal path'], null],
      ['AS5-dual-cp-into-dir-out', 'out', 'X={NA}/docs; read c <<< true; "$c" x; cp {NA}/base/report.md "$X/"', BZ, 'name', null],
      ['AS5-dual-sedi-glob-out', 'out', 'X={NA}/docs; read c <<< true; "$c" x; cd "$X"; sed -i s/N/M/ report.m?', BZ, 'name', null],
      ['AS5-dual-head-in-cmdsub-out', 'out', 'X={NA}/docs; read c <<< true; v=$("$c" x; echo y > "$X/report.md")', BZ, 'name', null],
      ['AS5-dual-ctl-untracked-held-out', 'out', 'X={OUT}/scratch; read c <<< true; "$c" x; cd "$X"; n=$(date +a.txt); echo y > "$n"', N, 'allow', null],
      // THE TWO WALKS' B2 disclosure (M3: allows fork main makes too, a witness row each, named in decision 47): the walk with the poison set aside
      // applies a cd's own block and enterable rules as fork main does, where the read-through held the hidden value's directory before them, so a
      // relative write after a cd through the hidden value that fork main does not follow passes from a cwd in no project while the shells write, as the
      // same cd with no head before it passes at fork main and at this change (the pre-existing B2 class: a relative write after a cd the guard does not
      // follow). One row per construct: a cd after `&&`, after `||`, in a conditional group, behind `command` (bash runs the builtin), behind `builtin`,
      // `cd -P`, a cd to a link the command made, behind `time`
      ['AS5-residual-hidden-cd-and-out', 'out', 'X={NA}/docs; read c <<< true; "$c" x; true && cd "$X"; echo y > report.md', BZ, 'allow', null],
      ['AS5-residual-hidden-cd-or-out', 'out', 'X={NA}/docs; read c <<< true; "$c" x; false || cd "$X"; echo y > report.md', BZ, 'allow', null],
      ['AS5-residual-hidden-cd-cond-group-out', 'out', 'X={NA}/docs; read c <<< true; "$c" x; true && { cd "$X"; }; echo y > report.md', BZ, 'allow', null],
      ['AS5-residual-hidden-cd-command-out', 'out', 'X={NA}/docs; read c <<< true; "$c" x; command cd "$X"; echo y > report.md', ['bash'], 'allow', null],
      ['AS5-residual-hidden-cd-builtin-out', 'out', 'X={NA}/docs; read c <<< true; "$c" x; builtin cd "$X"; echo y > report.md', BZ, 'allow', null],
      ['AS5-residual-hidden-cd-P-out', 'out', 'X={NA}/docs; read c <<< true; "$c" x; cd -P "$X"; echo y > report.md', BZ, 'allow', null],
      ['AS5-residual-hidden-cd-made-link-out', 'out', 'ln -s {NA}/docs {OUT}/d; X={OUT}/d; read c <<< true; "$c" x; cd "$X"; echo y > report.md', BZ, 'allow', null],
      ['AS5-residual-hidden-cd-time-out', 'out', 'X={NA}/docs; read c <<< true; "$c" x; time cd "$X"; echo y > report.md', BZ, 'allow', null],
      // the three shapes of the thirteen on which the read-through's refusal was false (B3, B4, B8 in decision 47): a cd through the hidden value in a
      // pipeline or in the background moves no shell that runs the write, and `pushd -n` adds the directory to the stack without entering it, so the
      // relative write lands in the cwd in no project and no shell writes a tracked file; allowed, as at fork main
      ['AS5-dual-ctl-cd-pipe-out', 'out', 'X={NA}/docs; read c <<< true; "$c" x; cd "$X" | cat; echo y > report.md', N, 'allow', null],
      ['AS5-dual-ctl-cd-bg-out', 'out', 'X={NA}/docs; read c <<< true; "$c" x; cd "$X" & wait; echo y > report.md', N, 'allow', null],
      ['AS5-dual-ctl-pushd-n-out', 'out', 'X={NA}/docs; read c <<< true; "$c" x; pushd -n "$X" > /dev/null; echo y > report.md', N, 'allow', null],
      // shell F3, pre-existing under the two walks (fork main takes these poisons itself, so its reading allows them too: M3, a witness row each, named
      // in decision 47): from a cwd in no project a write through a value the command gave passes after a call of a function holding the head, an eval
      // after the head, a call of a function after the head and a `.` of a file after the head; and `$OLDPWD` in an eval's text, after a cd in an eval's
      // text, in a sourced text or in a called function, and in a fresh shell
      ['AS5-residual-f3-func-holds-head-out', 'out', 'read c <<< true; f() { "$c" x; }; f; X={NA}/docs; echo y > "$X/report.md"', BZ, 'allow', null],
      ['AS5-residual-f3-eval-after-out', 'out', `X={NA}/docs; read c <<< true; "$c" x; eval 'Y=1'; echo y > "$X/report.md"`, BZ, 'allow', null],
      ['AS5-residual-f3-func-call-after-out', 'out', 'X={NA}/docs; read c <<< true; f() { :; }; "$c" x; f; echo y > "$X/report.md"', BZ, 'allow', null],
      ['AS5-residual-f3-dot-after-out', 'out', 'X={NA}/docs; read c <<< true; "$c" x; . {OUT}/scratch/keep.md; echo y > "$X/report.md"', BZ, 'allow', null],
      ['AS5-residual-oldpwd-in-eval-out', 'out', `X={NA}/docs; read c <<< true; "$c" x; cd "$X"; cd {OUT}; eval 'echo y > "$OLDPWD/report.md"'`, BZ, 'allow', null],
      ['AS5-residual-oldpwd-after-eval-cd-out', 'out', `X={OUT}/scratch; read c <<< true; "$c" x; cd {NA}/docs; eval 'cd "$X"'; echo y > "$OLDPWD/report.md"`, BZ, 'allow', null],
      ['AS5-residual-oldpwd-after-sourced-cd-out', 'out', `X={OUT}/scratch; read c <<< true; "$c" x; cd {NA}/docs; . <(echo 'cd "$X"'); echo y > "$OLDPWD/report.md"`, BZ, 'allow', null],
      ['AS5-residual-oldpwd-after-func-cd-out', 'out', 'X={OUT}/scratch; read c <<< true; "$c" x; cd {NA}/docs; f() { cd "$X"; }; f; echo y > "$OLDPWD/report.md"', BZ, 'allow', null],
      ['AS5-residual-fresh-oldpwd-out', 'out', `X={NA}/docs; read c <<< true; "$c" x; cd "$X"; cd {OUT}; bash -c 'echo y > "$OLDPWD/report.md"'`, BZ, 'allow', null],
      ['AS5-cost-home-head', 'na', 'cp /usr/bin/cp ~/c2; read c <<< true; "$c" x; ~/c2 base/report.md docs/other.md', N, ['text', [`\`~/c2\` is a path through HOME, which I cannot read here (${POISONED}), and this command made a path by copying, moving or linking, or by writing it, so which file it names is not known`], 'which this command reassigns']],
      ['AS5-cost-home-head-mv', 'na', 'mv {OUT}/scratch/keep.md ~/c2; read c <<< true; "$c" x; ~/c2 base/report.md docs/other.md', N, ['text', 'and this command made a path by copying, moving or linking, or by writing it, so which file it names is not known', 'copying or linking a command']],   // a moved data file makes the bound path too (the third verify round's T3-9)   // a \`~/\` command name while a path is bound: a stated cost, its text HOME's reason
      ['AS5-cost-home', 'na', 'read c <<< true; "$c" x; echo y > ~/a.txt', N, ['text', 'and not after an eval, a source, a command named by a variable with no external program wrapper before it, or a call of a function the command defines']],   // the list says which commands named by a variable (the sixth verify round's tg-t6-6: AS3-nohup-dd-no-home passes)
      ['AS5-cost-home-remedy', 'na', 'read c <<< true; "$c" x; echo y > {W}/home/a.txt', N, 'allow'],   // the HOME refusal's one remedy followed, the path spelled out as an absolute path (the census below builds this twin for every refused row)
      ['AS5-cost-cd', 'na', 'read c <<< true; "$c" x; cd; echo y > a.txt', N, ['dir', 'names a.txt, a relative path']],
      // a second command named by a variable blocks the read too (the verify round's T2-3; its T2-4, an \`&\` on a subshell around the command, is allowed
      // since fork PR 975's round 1, B: the subshell's close ends the poison taken inside it, \`&\` or not); the allowed control names the first by its literal path and backgrounds the second (a command the guard reads, not
      // the remedy the refusal gives, which is the path spelled absolute: M2)
      // since fork PR 975's round 2 (R5, THE ORDER) the first walk is fork main's reading, the poison set aside, and it refuses the second head's relative
      // operand in the directory the first head may have moved, so that is the text; the read of OUT the poison blocks is AS5-cost-var's and
      // AS5-cost-var-two-heads-abs's, whose second head is handed an absolute path
      ['AS5-cost-var-two-heads', 'na', 'read c <<< true; "$c" x; "$d" y; OUT={OUT}/o; mkdir -p "$OUT"; echo y > "$OUT/a.txt"', N, ['dir', ['its command named by `"$d"` names y, a relative path', 'an earlier `"$c"`, a command name that stands for a text I do not read, may move the shell'], NO_CURE]],
      ['AS5-cost-var-two-heads-abs', 'na', 'read c <<< true; "$c" x; "$d" /dev/null; OUT={OUT}/o; mkdir -p "$OUT"; echo y > "$OUT/a.txt"', N, ['text', [`(${POISONED}, so I do not read \`$OUT\` here)`, REMEDY_ABS], NO_CURE]],
      ['AS5-ctl-cost-var-two-heads-literal-bg', 'na', 'read c <<< true; /usr/bin/true x; "$d" y & OUT={OUT}/o; mkdir -p "$OUT"; echo y > "$OUT/a.txt"', N, 'allow'],
      ['AS5-subshell-bg-no-poison', 'na', 'read c <<< true; ("$c" x) & T={OUT}/t; mkdir -p "$T"; echo y > "$T/a.txt"', N, 'allow'],   // the poison ends at the subshell's close, `&` or not (B)
    ];
    // item 1 (FIX 1 and 1b): a `[` is a pattern only where a part of it forms one (an unmatched `[` is text in bash and dash, bash under nullglob
    // keeping it, a lone `[` is text in zsh too, and zsh stops with "bad pattern" on an unclosed one inside a word, writing nothing: the third
    // verify round's T3-10), so after a construct that leaves the directory unknown it is neither a pattern the command name stands for nor a word that may
    // vanish (which made its first operand the command name, its other operands paths); each test form after each construct, nothing written
    const AFTER = [['source', `source ${ENV}; `], ['dot', `. ${ENV}; `], ['head', '"$PY" -c x; '], ['cd', 'cd "$D"; ']];
    const TESTS = [
      ['abs', '[ -f {NA}/results/status.txt ] && echo y'],
      ['rel', '[ -f results/status.txt ] && echo y'],
      ['n', '[ -n "$X" ] && echo y'],
      ['if', 'if [ -f {NA}/results/status.txt ]; then echo y; fi'],
      ['while', 'while [ ! -f {NA}/docs/report.md ]; do sleep 1; done'],
      ['or-exit', '[ -f {NA}/results/status.txt ] || exit 1'],
      ['var-eq', '[ "$X" = done ] && echo y'],
      ['var-alone', '[ "$X" ] && echo y'],
      ['var-if', 'if [ "$S" = done ]; then echo y; fi'],
      ['var-while', 'while [ "$(cat {NA}/docs/report.md)" != NA-ORIG ]; do sleep 1; done'],
      ['dbrack', '[[ "$a" = "$b" ]] && echo same'],
    ];
    for (const [after, prefix] of AFTER) for (const [form, text] of TESTS) rows.push([`AS1-${form}-after-${after}`, 'na', prefix + text, N, 'allow']);
    rows.push(
      ['AS1-source-newline', 'na', `source ${ENV}\n[ -f {NA}/results/status.txt ] && echo y`, N, 'allow'],
      ['AS1-ctl-test', 'na', `source ${ENV}; test -f {NA}/results/status.txt && echo y`, N, 'allow'],
      ['AS1-ctl-dbrack-f', 'na', `source ${ENV}; [[ -f {NA}/results/status.txt ]] && echo y`, N, 'allow'],
      // the twins: a command name that is a pattern stays one the guard cannot expand where the directory is not known, a `[` in a target
      // is the relative path it spells, a `[` the command binds is refused through the binding, and a test's own redirection is a write
      ['AS1-armed-glob-head', 'na', 'cd "$D"; ./c? a b', N, ['text', '`./c?`']],
      ['AS1-armed-class-head', 'na', 'cd "$D"; [c]p a b', N, ['text', '`[c]p`']],
      ['AS1-armed-class-head-source', 'na', `source ${ENV}; [ab] x`, N, ['text', '`[ab]`']],
      // a class whose `]` comes past a `/` is a pattern too: zsh globs it across the slash (`./c[p/x]` ran the copy ./cx), bash and dash run it as spelled
      ['AS1-armed-class-across-slash', 'na', `cp /usr/bin/cp cx; source ${ENV}; ./c[p/x] base/report.md docs/report.md`, ['zsh'], ['text', '`./c[p/x]` is a pattern, matched in a directory that is not known']],
      // a disclosed residual, older than this change: in a known directory a class is read by its path segment, as bash and dash read it, so the
      // name zsh globs across the slash passes as the literal name it spells (zsh overwrote the tracked report)
      ['AS1-residual-zsh-class-across-slash', 'nad', 'cp ../base/report.md repor[t/x].md', ['zsh'], 'allow'],
      // a \`[!]\` or \`[^]\` is a pattern too: zsh reads a class of any one character there (\`./[!]\` ran the copy ./c), bash and dash run it as
      // spelled (the verify round's G1); and the disclosed residual beside the one above, older than this change: in a known directory it is read
      // as text, as bash and dash read it, so the one-character name zsh globs passes (zsh overwrote the tracked report, as a command name and as
      // a target)
      ['AS1-armed-neg-class-source', 'na', `cp /usr/bin/cp c; source ${ENV}; ./[!] base/report.md docs/report.md`, ['zsh'], ['text', '`./[!]` is a pattern, matched in a directory that is not known']],
      ['AS1-armed-neg-class-cd', 'na', 'cp /usr/bin/cp c; cd "$D"; ./[!] base/report.md docs/report.md', ['zsh'], ['text', '`./[!]` is a pattern, matched in a directory that is not known']],
      ['AS1-armed-neg-class-head', 'na', 'cp /usr/bin/cp c; "$PY" -c 0; ./[!] base/report.md docs/report.md', ['zsh'], ['text', '`./[!]` is a pattern, matched in a directory that is not known']],
      ['AS1-armed-caret-class-source', 'na', `cp /usr/bin/cp c; source ${ENV}; ./[^] base/report.md docs/report.md`, ['zsh'], ['text', '`./[^]` is a pattern, matched in a directory that is not known']],
      ['AS1-residual-zsh-neg-class-head', 'na', 'cp /usr/bin/cp c; ./[!] base/report.md docs/report.md', ['zsh'], 'allow'],
      ['AS1-residual-zsh-neg-class-target', 'nad', 'cp ../base/report.md repor[!].md', ['zsh'], 'allow'],
      ['AS1-residual-zsh-caret-class-target', 'nad', 'cp ../base/report.md repor[^].md', ['zsh'], 'allow'],   // the `[^]` twin of the `[!]` residual, disclosed with no witness until now (the fourth verify round's T4-10): in a known directory it is read as text, as bash and dash read it, while zsh globs the one-character class and overwrote the tracked report
      ['AS1-armed-redirect-bracket', 'na', 'cd "$D"; echo x > a[b', N, ['dir', 'names a[b, a relative path']],
      ['AS1-armed-alias', 'na', 'alias [=cp\n[ base/report.md docs/report.md', ['dash'], 'name'],   // zsh reads `[=cp` as a pattern and stops; bash expands no alias here
      ['AS1-armed-alias-after-source', 'na', `source ${ENV}\nalias [=cp\n[ base/report.md docs/report.md`, ['dash'], ['dir', 'names docs/report.md, a relative path']],
      ['AS1-armed-func', 'na', '[() { cp "$1" "$2"; }; [ base/report.md docs/report.md', BZ, 'name'],
      ['AS1-armed-and-write', 'na', `source ${ENV}; [ -f x ] && echo x > {NA}/docs/report.md`, N, 'name', 'name'],
      ['AS1-armed-redirect-abs', 'na', `source ${ENV}; [ -f x ] > {NA}/docs/report.md`, A, 'name', 'name'],
      ['AS1-armed-redirect-rel', 'na', `source ${ENV}; [ -f x ] > docs/report.md`, A, ['dir', 'names docs/report.md, a relative path']],
      // the accepted side effect: a lone `[` operand of a command named by a variable, after a cd the guard does not follow, is the relative
      // path it spells (it was a pattern the guard dropped)
      ['AS1-side-lone-bracket', 'na', 'cd "$D"; "$PY" [', N, ['dir', 'names [, a relative path']],
    );
    // item 2 (FIX 2a as refined): an arm's pattern list of one-word alternatives is matched, never run, so after a construct that leaves the
    // directory unknown a pattern is no command name the guard cannot expand; what the words' expansions do still holds (a substitution in a
    // `${..}` or an arithmetic body runs, an arithmetic body or a `${name::=..}` assigns); a pattern list of another shape is read as before;
    // the parenthesized pattern `(a|b)` (and bash's extglob, zsh's nested forms) is not read so (FIX 2b, not built: the lexer ends a segment at
    // `;;` as at `;`), so after such a construct it is refused where an alternative holds `*`, `?` or `[...]` (a false refusal) and passes otherwise
    const CP_ABS = 'cp {NA}/base/report.md {NA}/docs/report.md';
    for (const [after, prefix] of AFTER) rows.push([`AS2-pending-after-${after}`, 'na', `${prefix}case "$X" in ""|PENDING*) echo p ;; *) echo d ;; esac`, N, 'allow']);
    rows.push(
      ['AS2-later-star', 'na', `source ${ENV}; case "$X" in a) : ;; *) : ;; esac`, N, 'allow'],
      ['AS2-later-qmark', 'na', `source ${ENV}; case "$X" in a) : ;; ?) : ;; esac`, N, 'allow'],
      ['AS2-later-glued-star', 'na', `source ${ENV}; case "$X" in a) : ;; *x) : ;; esac`, N, 'allow'],
      ['AS2-newline', 'na', `source ${ENV}\ncase "$X" in\n  a) echo a ;;\n  *) echo other ;;\nesac`, N, 'allow'],
      ['AS2-first-own-line', 'na', `source ${ENV}; case "$X" in\n""|PENDING*) echo p ;;\nesac`, N, 'allow'],
      ['AS2-cmdsub', 'na', `source ${ENV}; Y=$(case "$X" in a) echo 1 ;; *) echo 2 ;; esac)`, N, 'allow'],
      ['AS2-in-if', 'na', `source ${ENV}; if true; then case "$X" in ""|PENDING*) echo p ;; esac; fi`, N, 'allow'],
      ['AS2-in-while', 'na', `source ${ENV}; while :; do case "$X" in PENDING*) sleep 1 ;; *) break ;; esac; done`, N, 'allow'],
      ['AS2-in-function', 'na', `source ${ENV}; f() { case "$1" in a|PENDING*) echo p ;; esac; }; f x`, N, 'allow'],
      ['AS2-assign-shaped', 'na', 'x=../scratch/other; case "$X" in a|x=report) : ;; esac; echo y > docs/$x.md', N, 'allow'],   // a pattern assigns nothing: x keeps its value, the write lands in scratch/
      // the twins: a substitution in the pattern (in a `${..}`, an arithmetic body, a backtick, a process substitution, the bare form), an
      // arithmetic body or zsh's `${name::=..}` assigning, bash's `${name@P}`, a cd or pushd pattern (no cd runs), a tee in an arm's body,
      // a malformed body, the case's own redirection, the parenthesized pattern (FIX 2b's residual)
      ['AS2-armed-brace-cmdsub', 'na', `X=b; case "$X" in a|\${x:-$(${CP_ABS})}) : ;; esac`, A, 'name', 'name'],
      ['AS2-armed-brace-cmdsub-later-arm', 'na', `X=b; case "$X" in a) : ;; \${x:-$(${CP_ABS})}) : ;; esac`, A, 'name', 'name'],
      ['AS2-armed-brace-cmdsub-newline', 'na', `X=b; case "$X" in\n true|\${x:-$(${CP_ABS})}) : ;;\nesac`, A, 'name', 'name'],   // `true`: a pattern word the program reader knows (it reads the line as a command)
      ['AS2-armed-arith-cmdsub', 'na', `X=b; case "$X" in a|$(( $(${CP_ABS}) + 1 ))) : ;; esac`, A, 'name', 'name'],
      ['AS2-armed-cmdsub', 'na', `X=b; case "$X" in a|$(${CP_ABS})) : ;; esac`, A, 'name', 'name'],
      ['AS2-armed-brace-backtick', 'na', `X=b; case "$X" in a|"\${x:-\`${CP_ABS}\`}") : ;; esac`, A, 'name', 'name'],
      ['AS2-armed-brace-procsub', 'na', `X=b; case "$X" in a|\${x:-<(${CP_ABS})}) : ;; esac`, ['bash'], 'name', 'name'],   // bash alone performs the process substitution there
      ['AS2-armed-arith-assign', 'na', 'x=../scratch/other; case "$X" in a|$((x=1))) : ;; esac; echo y > notes/$x.md', A, ['text', 'the command writes `x` through an arithmetic body']],
      ['AS2-armed-arith-assign-later-arm', 'na', 'x=../scratch/other; case "$X" in a) : ;; $((x=1))) : ;; esac; echo y > notes/$x.md', A, ['text', 'the command writes `x` through an arithmetic body']],
      ['AS2-armed-zsh-assign', 'na', 'x=scratch; case "$X" in a|${x::=docs}) : ;; esac; echo y > $x/report.md', ['zsh'], ['text', 'the command writes `x` through a `${name=..}`, `${name:=..}` or `${name::=..}` expansion']],
      ['AS2-armed-prompt', 'na', "x='$(cp base/report.md docs/report.md)'; case \"$X\" in a|${x@P}) : ;; esac", ['bash'], 'name'],
      ['AS2-armed-cd-first', 'na', 'case "$x" in cd) : ;; esac; echo x > docs/report.md', A, 'name'],
      ['AS2-armed-cd-later', 'na', 'case "$x" in a) : ;; cd) : ;; esac; echo x > docs/report.md', A, 'name'],
      ['AS2-armed-pushd', 'na', 'case "$x" in a|pushd) : ;; esac; echo x > docs/report.md', A, 'name'],
      ['AS2-armed-tee-body', 'na', 'case "$x" in *) echo x | tee docs/report.md ;; esac', A, 'name'],
      ['AS2-armed-malformed', 'na', 'case "$x" in a) echo x | tee docs/report.md b) : ;; esac', N, 'name'],
      ['AS2-armed-case-redirect', 'na', `source ${ENV}; case "$X" in a) : ;; *) echo d ;; esac > docs/report.md`, A, ['dir', 'names docs/report.md, a relative path']],
      ['AS2-residual-paren', 'na', `source ${ENV}; case "$X" in (true|PENDING*) echo p ;; esac`, N, ['text', '`PENDING*`']],   // `true`: a pattern word the program reader knows (it reads the list as a subshell running it)
      ['AS2-residual-extglob', 'na', `source ${ENV}; case "$X" in @(true|PENDING*)) echo p ;; esac`, N, ['text', '`PENDING*`']],   // bash's extglob alternation, not read as a pattern list (FIX 2b's residual: the fourth verify round's T4-10, a witness for the form decision 47 names refused)
      ['AS2-residual-zsh-nested', 'na', `source ${ENV}; case "$X" in true|(PENDING*|x)) echo p ;; esac`, N, ['text', '`PENDING*`']],   // zsh's nested-pattern alternation, likewise refused (T4-10)
      ['AS2-residual-paren-plain', 'na', `source ${ENV}; case "$X" in (true|false) echo p ;; esac`, N, 'allow'],   // words the program reader knows, as above   // a parenthesized list with no \`*\`, \`?\` or \`[...]\` in it passes after such a construct
      // a disclosed residual, older than this change: an alternative that is a substitution reading the case's piped input (the lexer reads the
      // \`|\` between alternatives as a pipe, so the substitution's input is read as the previous alternative's output); every shell copies
      ['AS2-residual-case-alt-reads-stdin', 'na', "echo 'cp base/report.md docs/report.md' | case x in a|$(bash)) : ;; esac", A, 'allow'],
    );
    // item 3, split out (the after-source fixes read a filled-in word behind nohup and setsid as the command it runs; that reading is reverted here,
    // since no rule found separates a launch from a write without reading the word's value, so under M3 no fix of bug vi exists inside fork PR 975;
    // decision 47's follow-up): behind nohup and setsid as behind every other wrapper, a word the shell fills in refuses, the text saying it may be
    // an option of the wrapper or the command the wrapper runs, and naming no spelling the guard cannot judge. A few fork-main refusal witnesses are
    // kept, re-pinned to that text (the `filled` kind), so the M2 census below holds a hand twin for it
    const FILLED = 'a word the shell fills in when the command runs: it may be an option of the wrapper or the command the wrapper runs';
    const FILLED_SPELL = 'Spell the word out as the option or the command it stands for';
    const FILLED_PIPE = `${FILLED_SPELL}, and put the command directly before that \`|\`, with no redirection and no group, subshell or compound around it: `;   // "the command", where the word may stand for an option (the fifth verify round's T5-12)
    const FOLLOWED = ', and it is followed by `|`, directly or through an enclosing group, subshell or compound, so its output may reach another command';
    const HELD_NOHUP = ['names report.md, a relative path', 'an earlier `"$c"` behind `nohup` runs a program I do not read, which may make a link that a later relative path goes through'];   // THE HELD DIRECTORY's refusal behind `nohup --`: the directory not known, the external wrapper named
    rows.push(
      ['AS3-nohup-bg', 'na', 'nohup "$c" {OUT}/scratch/x.py --outdir {OUT}/res > {OUT}/log 2>&1 &', N, ['text', ['`nohup` wrapper carries the option "$c", ' + FILLED, FILLED_SPELL + ': '], ['drop the wrapper', 'directly before that `|`', 'it is followed by']]],
      ['AS3-setsid-bg', 'na', 'setsid "$c" {OUT}/scratch/x.py --outdir {OUT}/res > {OUT}/log 2>&1 &', N, ['text', ['`setsid` wrapper carries the option "$c", ' + FILLED, FILLED_SPELL + ': '], ['drop the wrapper', 'directly before that `|`', 'it is followed by']]],
      ['AS3-nohup-name', 'na', 'read c <<< tee; nohup "$c" docs/report.md < /dev/null', BZ, ['text', ['`nohup` wrapper carries the option "$c", ' + FILLED, FILLED_SPELL + ': '], ['drop the wrapper', 'it is followed by']]],
      ['AS3-setsid-name', 'na', 'read c <<< tee; setsid -w "$c" docs/report.md < /dev/null', BZ, ['text', ['`setsid` wrapper carries the option "$c", ' + FILLED, FILLED_SPELL + ': '], ['drop the wrapper', 'it is followed by']]],
      ['AS3-nohup-name-out', 'out', 'read c <<< tee; nohup "$c" {NA}/docs/report.md < /dev/null', BZ, ['text', ['`nohup` wrapper carries the option "$c", ' + FILLED, FILLED_SPELL + ': '], ['drop the wrapper', 'it is followed by']], null],
      // the filled-in word whose output reaches `|`: the same refusal with the followed-by clause and the piped remedy (the `filled-piped` kind); no "drop
      // the wrapper" (it would pass as a command named by a variable whose output is piped, T3-7), and no "runs" wording (the word may be nohup's own option)
      ['AS3-nohup-pipe', 'nad', "read e <<< echo; nohup $e 'cp ../base/report.md report.md' | bash", BZ, ['text', ['`nohup` wrapper carries the option $e, ' + FILLED, FOLLOWED, FILLED_PIPE], ['drop the wrapper', '`nohup` wrapper runs']]],
      ['AS3-setsid-pipe', 'nad', "read e <<< echo; setsid $e 'cp ../base/report.md report.md' | bash", BZ, ['text', ['`setsid` wrapper carries the option $e, ' + FILLED, FOLLOWED, FILLED_PIPE], ['drop the wrapper', '`setsid` wrapper runs']]],
      // the \`|\` after the closer of a group, a subshell or a compound around the command (outputReachesPipe's group, subshell and compound
      // branches): the same refusal with the followed-by clause and the piped remedy, behind nice as behind every wrapper, and bash and zsh copy (the
      // reviewer's e10-4: these pins went with the item-3 rows, and a mutant that stops the three branches passed the rows test); the control: the
      // remedy followed, the word spelled out and the command directly before the \`|\`
      ['AS3-nice-filled-group-pipe', 'nad', "read e <<< echo; { nice $e 'cp ../base/report.md report.md'; } | bash", BZ, ['text', [`\`nice\` wrapper carries the option $e, ${FILLED}`, FILLED_PIPE], 'drop the wrapper']],   // dropping the wrapper would pass, and bash and zsh copy (T3-7); M2's one remedy is the word before the \`|\`
      ['AS3-nice-filled-group-pipe-ls', 'nad', "read e <<< echo; { nice $e 'ls'; } | bash", N, ['text', FILLED_PIPE, 'drop the wrapper']],
      ['AS3-nice-filled-if-pipe', 'nad', "read e <<< echo; if true; then nice $e 'cp ../base/report.md report.md'; fi | bash", BZ, ['text', [`\`nice\` wrapper carries the option $e, ${FILLED}`, FOLLOWED, FILLED_PIPE], 'drop the wrapper']],
      ['AS3-nice-filled-subshell-pipe', 'nad', "read e <<< echo; ( nice $e 'cp ../base/report.md report.md' ) | bash", BZ, ['text', [`\`nice\` wrapper carries the option $e, ${FILLED}`, FOLLOWED, FILLED_PIPE], 'drop the wrapper']],
      ['AS3-ctl-nice-filled-group-pipe-ls-spelled', 'nad', "nice echo 'ls' | bash", N, 'allow'],   // the ONE remedy followed: the word spelled, the command directly before the \`|\` (M2)
      // DISCLOSED (item 3's split-out follow-up, bug vi; M3's stopping rule): the guard reads no script a command runs from a file, so from the
      // tracked cwd a script outside the command that copies over the tracked report (the world's tools/w2) passes when run by a command named by a
      // variable that holds `sh`, by the same behind `nohup --`, by `sh` itself and by `sh` behind `nohup`, at fork main as here, while the shells
      // run it (dash parses no `<<<`, so its variable stays empty); the filled refusal's one remedy, the word spelled out, leads to the last of them
      // where the word stands for an interpreter; a follow-up, each named in decision 47 beside bug vi's
      ['AS3-residual-script-var-w2', 'na', 'read x <<< sh; "$x" {W}/tools/w2', BZ, 'allow'],
      ['AS3-residual-script-nohup-dd-var-w2', 'na', 'read x <<< sh; nohup -- "$x" {W}/tools/w2', BZ, 'allow'],
      ['AS3-residual-script-sh-w2', 'na', 'sh {W}/tools/w2', A, 'allow'],
      ['AS3-residual-script-nohup-sh-w2', 'na', 'nohup sh {W}/tools/w2', A, 'allow'],
      // DISCLOSED (M3's stopping rule; the reviewer's e10-3): the split restores fork main's verdict for two classes the after-source fixes had
      // refused by name, each allowed at fork main from a cwd in no project while bash and zsh write: behind `env -C <absolute tracked dir>` before
      // `nohup "$c"` the operand is judged in the shell's directory, not the wrapper's, so no project is in play there; and after `nohup "$c"` the
      // names are poisoned as after any option the guard does not read (fork main's B2), so a target built from a variable that lands on the tracked
      // report is dropped from that cwd; a follow-up, each named in decision 47
      ['AS3-residual-envC-abs-nohup-filled-out', 'out', 'read c <<< tee; env -C {NA}/docs nohup "$c" report.md < /dev/null', BZ, 'allow', null],
      ['AS3-residual-nohup-filled-poison-out', 'out', 'read c <<< true; nohup "$c" x; T={NA}/docs; echo y > "$T/report.md"', BZ, 'allow', null],
      // a literal option the table does not parse names ONE remedy, its long form, and no longer "or drop the wrapper", which reached the T3-7 road
      // (\`nice --foo $e '<a cp>' | bash\` with the wrapper dropped passed while bash and zsh copied: the fifth verify round's T5-1 and T5-10)
      ['AS3-option-abbrev', 'na', 'nice --adj=5 cp base/report.md docs/other.md', N, ['text', ['`nice` wrapper carries the option --adj=5, which I do not read in that spelling', 'Spell the option in the long form I know: '], 'drop the wrapper']],
      // an option the table does not hold at all has no long form the guard knows, so its one remedy is the wrapper dropped, and where the command's
      // output goes through `|` there is none, since the wrapper dropped passes as a piped command named by a variable while bash and zsh copy (the
      // sixth verify round's tg-t6-2, T3-7): that refusal states what it refuses and offers track-edit alone
      ['AS3-option-unheld-short', 'na', 'env -a x cp base/report.md docs/other.md', N, ['text', ['`env` wrapper carries the option -a, which I do not know', 'Run the command without the `env` wrapper: '], ['long form', 'drop the wrapper']]],
      ['AS3-option-unheld-long', 'na', 'env --argv0=x cp base/report.md docs/other.md', N, ['text', ['`env` wrapper carries the option --argv0=x, which I do not know', 'Run the command without the `env` wrapper: '], 'long form']],
      ['AS3-option-unheld-numactl', 'na', 'numactl -T cp base/report.md docs/other.md', N, ['text', ['`numactl` wrapper carries the option -T, which I do not know', 'Run the command without the `numactl` wrapper: '], 'long form']],
      ['AS3-option-unheld-pipe', 'nad', "read e <<< echo; nice --foo $e 'cp ../base/report.md report.md' | bash", N, ['text', ['`nice` wrapper carries the option --foo, which I do not know', FOLLOWED], ['Run the command without', 'long form']]],
      ['AS3-option-unheld-pipe-ls', 'nad', "env -a x echo 'ls' | bash", N, ['text', ['`env` wrapper carries the option -a, which I do not know', FOLLOWED], ['Run the command without', 'long form']]],
      // each list `held` reads, by an abbreviation of a long option in it (the seventh verify round's tg-m7-8: flagLong, optLong, the script option), a
      // held option whose output goes through `|`, which keeps its long form, and an empty name, which abbreviates no option (`--=x`: the unheld text)
      ['AS3-option-held-flag', 'na', 'env --deb cp base/report.md docs/other.md', N, ['text', ['`env` wrapper carries the option --deb, which I do not read in that spelling', 'Spell the option in the long form I know: '], 'Run the command without']],
      ['AS3-option-held-opt', 'na', 'env --block=INT cp base/report.md docs/other.md', N, ['text', ['`env` wrapper carries the option --block=INT, which I do not read in that spelling', 'Spell the option in the long form I know: '], 'Run the command without']],
      ['AS3-option-held-script', 'na', "flock {OUT}/scratch/lk --comm='cp base/report.md docs/other.md'", N, ['text', ['`flock` wrapper carries the option --comm=cp base/report.md docs/other.md, which I do not read in that spelling', 'Spell the option in the long form I know: '], 'Run the command without']],
      ['AS3-option-held-piped', 'nad', "nice --adj=5 echo 'cp ../base/report.md report.md' | bash", A, ['text', ['`nice` wrapper carries the option --adj=5, which I do not read in that spelling', 'Spell the option in the long form I know: '], 'Make the change with track-edit instead']],
      ['AS3-option-unheld-empty-name', 'na', 'env --=x cp base/report.md docs/other.md', N, ['text', ['`env` wrapper carries the option --=x, which I do not know', 'Run the command without the `env` wrapper: '], 'long form']],
      // an abbreviation of an option the table refuses outright is that option to the program, so it takes that option's own refusal and never the long
      // form as its remedy, which is refused in its turn (the seventh verify round's tg-m7-7; the census below asks the same of every refused long option)
      ['AS3-option-refuse-abbrev-env', 'na', "env --split='cp base/report.md docs/report.md'", A, ['text', ['its `env --split` hands the rest of the command to a splitter or a shell of its own', 'Spell the command without `env --split`: '], ['long form', 'Run the command without']]],
      ['AS3-option-refuse-abbrev-sudo', 'na', 'sudo --edi docs/other.md', null, ['text', ['its `sudo --edi` hands the rest of the command to a splitter or a shell of its own', 'Spell the command without `sudo --edi`: '], ['long form', 'Run the command without']]],
      // the mechanism ruling (2026-10-03, M1): the ROAD is restored behind any wrapper, since a program run behind an external wrapper cannot move
      // this shell but can change the filesystem a later relative path walks (a symlink), so a relative write after the unread head is refused as a
      // directory not known (`nohup -- "$c" x; echo y > scratch/a.txt`, a cost until the rounds before, is refused again: AS3-nohup-dd-moves). The
      // NAMES stay readable when at least one wrapper before the head is an EXTERNAL program (it runs the head in a child process, which cannot
      // assign this shell's names): a later variable read, a `~/` write and a bare cd after `nohup -- "$c"` stay as they would without it; behind a
      // wrapper the shell runs itself (time, command, builtin, exec, noglob, nocorrect, -) the names are poisoned (the kept rows below)
      // M1 APPLIED WHOLE (fork PR 975's round 1, A, 2026-10-05; the round's tests-1 and regression-2): the program behind `nohup --` runs in a child,
      // so the positional parameters keep their values, and the shell's directory is held (THE HELD DIRECTORY: after `cd <tracked dir>` a relative
      // write onto the tracked report passed from a cwd in no project, the directory left unknown and its project out of play); fork main allowed
      // these two, so they pin roads the held directory and the kept list close beside the rest
      ['AS3-nohup-dd-held-out', 'out', 'cd {NA}/docs; read c <<< true; nohup -- "$c" x; echo y > report.md', BZ, ['dir', HELD_NOHUP], null],
      ['AS3-nohup-dd-positional-out', 'out', 'set -- {NA}/docs/report.md; read c <<< true; nohup -- "$c" x; echo y > "$1"', BZ, 'name', null],
      // the held directory is part of the directory state each frame and each text saves and restores, so a construct between the program and the
      // relative write keeps it (the reviewer's mut F2, tg-m10-6): a subshell and a piped group whose body moves, a function defined and called, a
      // loop and a group whose closer carries the write, the operand of a later command named by a variable, an eval's text, the program run in an
      // eval's text, and the command a chdir wrapper runs; behind `env --` too. Each passed while bash and zsh wrote the tracked report under a
      // mutant that drops the held directory at its site (fork main allows each, as it allows AS3-nohup-dd-held-out)
      ['AS3-nohup-dd-held-subshell-out', 'out', 'cd {NA}/docs; read c <<< true; nohup -- "$c" x; ( cd {OUT} ); echo y > report.md', BZ, ['dir', HELD_NOHUP], null],
      ['AS3-nohup-dd-held-piped-group-out', 'out', 'cd {NA}/docs; read c <<< true; nohup -- "$c" x; { cd {OUT}; } | cat; echo y > report.md', BZ, ['dir', HELD_NOHUP], null],
      ['AS3-nohup-dd-held-func-call-out', 'out', 'cd {NA}/docs; read c <<< true; nohup -- "$c" x; f() { :; }; f; echo y > report.md', BZ, ['dir', HELD_NOHUP], null],
      ['AS3-nohup-dd-held-loop-closer-out', 'out', 'cd {NA}/docs; read c <<< true; nohup -- "$c" x; for i in 1; do :; done > report.md', BZ, ['dir', HELD_NOHUP], null],
      ['AS3-nohup-dd-held-group-closer-out', 'out', 'cd {NA}/docs; read c <<< true; nohup -- "$c" x; { :; } > report.md', BZ, ['dir', HELD_NOHUP], null],
      ['AS3-nohup-dd-held-operand-out', 'out', 'cd {NA}/docs; read c <<< true; nohup -- "$c" x; read e <<< tee; "$e" report.md < /dev/null', BZ, ['dir', HELD_NOHUP], null],
      ['AS3-nohup-dd-held-eval-out', 'out', "cd {NA}/docs; read c <<< true; nohup -- \"$c\" x; eval 'echo y > report.md'", BZ, ['dir', HELD_NOHUP], null],
      ['AS3-nohup-dd-held-in-eval-out', 'out', "cd {NA}/docs; read c <<< true; eval 'nohup -- \"$c\" x'; echo y > report.md", BZ, ['dir', HELD_NOHUP], null],   // the directory the eval's text holds is the shell's after it (adopted)
      ['AS3-nohup-dd-held-envC-out', 'out', 'cd {NA}/docs; read c <<< true; nohup -- "$c" x; env -C {OUT} true; echo y > report.md', BZ, ['dir', HELD_NOHUP], null],
      ['AS3-env-dd-held-subshell-out', 'out', 'cd {NA}/docs; read c <<< true; env -- "$c" x; ( cd {OUT} ); echo y > report.md', BZ, ['dir', ['names report.md, a relative path', 'an earlier `"$c"` behind `env` runs a program I do not read']], null],
      ['AS3-env-dd-held-loop-closer-out', 'out', 'cd {NA}/docs; read c <<< true; env -- "$c" x; for i in 1; do :; done > report.md', BZ, ['dir', ['names report.md, a relative path', 'an earlier `"$c"` behind `env` runs a program I do not read']], null],
      // DISCLOSED (M3's stopping rule; the reviewer's t8-9): where the program behind `nohup --` runs in a function call or a loop body, the body is
      // marked as moving the shell, as a command named by a variable with no wrapper marks it, so the call or the loop's close leaves the directory
      // unknown with none held and a later relative write from a cwd in no project passes, at fork main as here, while bash and zsh write; a
      // follow-up, named in decision 47
      ['AS3-residual-nohup-dd-func-held-out', 'out', 'cd {NA}/docs; read c <<< true; f() { nohup -- "$c" x; }; f; echo y > report.md', BZ, 'allow', null],
      ['AS3-residual-nohup-dd-loop-held-out', 'out', 'cd {NA}/docs; read c <<< true; for i in 1; do nohup -- "$c" x; done; echo y > report.md', BZ, 'allow', null],
      // RULE H (fork PR 975's round 2, R4, 2026-10-06; the round's correctness-2): the held directory ends at a RELATIVE directory change (cd, pushd,
      // popd, cd -) after an unread program, as the non-held branch does, so `$PWD`, `${PWD}` and `~+` read no held directory and a write through them
      // refuses. Before, a relative cd under the held directory carried it, so after `nohup -- "$c" x; cd build` (where build is absent at run time, or a
      // fresh or swapped link) the guard read `$PWD` as the directory the cd named while the real cd failed and the shell stayed, and bash and zsh wrote
      // the tracked report through `$PWD/report.md`, where base refuses the not-literal target. Behind env --, setsid -- and with pushd alike
      ['AS3-relcd-pwd', 'nad', 'read c <<< true; nohup -- "$c" x; cd build; echo y > "$PWD/report.md"', BZ, ['text', 'names "$PWD/report.md", which is not a literal path']],
      ['AS3-relcd-pwd-brace', 'nad', 'read c <<< true; nohup -- "$c" x; cd build; echo y > "${PWD}/report.md"', BZ, ['text', 'names "${PWD}/report.md", which is not a literal path']],
      ['AS3-relcd-tildeplus', 'nad', 'read c <<< true; nohup -- "$c" x; cd build; echo y > ~+/report.md', BZ, ['text', 'names ~+/report.md, which is not a literal path']],
      ['AS3-relcd-env-pwd', 'nad', 'read c <<< true; env -- "$c" x; cd build; echo y > "$PWD/report.md"', BZ, ['text', 'names "$PWD/report.md", which is not a literal path']],
      ['AS3-relcd-setsid-pwd', 'nad', 'read c <<< true; setsid -- "$c" x; cd build; echo y > "$PWD/report.md"', BZ, ['text', 'names "$PWD/report.md", which is not a literal path']],
      ['AS3-relcd-pushd-pwd', 'nad', 'read c <<< true; nohup -- "$c" x; pushd build; echo y > "$PWD/report.md"', BZ, ['text', 'names "$PWD/report.md", which is not a literal path']],
      // DISCLOSED, PRE-EXISTING (base, head and rule H all allow; decision 47): a `$PWD` or `~+` write after the relative cd from a cwd in no project is
      // the B2 residual (the guard reads no cwd there, so the held directory's loss changes nothing), while bash and zsh write the tracked report
      ['AS3-residual-relcd-pwd-out', 'out', 'cd {NA}/docs; read c <<< true; nohup -- "$c" x; cd build; echo y > "$PWD/report.md"', BZ, 'allow', null],
      ['AS3-residual-relcd-tildeplus-out', 'out', 'cd {NA}/docs; read c <<< true; nohup -- "$c" x; cd build; echo y > ~+/report.md', BZ, 'allow', null],
      // and the two cases the held report names as pre-existing allows the lexical-path precondition keeps open (decision 47): a relative cd into a link an
      // unread program made from a cwd in no project, and an absolute cd through a link swapped at run time; base allows each, and bash and zsh write
      ['AS3-residual-relcd-abs-ln-task-out', 'out', 'read c <<< ln; nohup -- "$c" -s {NA}/docs build; cd build; cp {OUT}/scratch/keep.md report.md', BZ, 'allow', null],
      ['AS3-residual-relcd-abs-cd-swaplink-out', 'out', 'read c <<< ln; nohup -- "$c" -sfn {NA}/docs {OUT}/lnk; cd {OUT}/lnk; cp {OUT}/scratch/keep.md report.md', BZ, 'allow', null],
      // THE COST of rule H (decision 47): from a cwd in no project, a cd into a project then an unread program then a relative cd into an untracked
      // directory and a relative write there is allowed again, as base allows it, where the held directory had refused it; nothing is written
      ['AS3-cost-relcd-into-proj-out', 'out', 'cd {NA}; read c <<< true; nohup -- "$c" x; cd scratch; echo y > a.txt', N, 'allow', null],
      // M1's symlink witness (the fourth verify round's S4-2, closed by the restored road): an unread command behind an external wrapper can make a
      // link from an untracked directory into a tracked one, so a later relative write through it is refused as a directory not known; a write by an
      // ABSOLUTE path through such a link is judged by its spelling (the stated precondition: the guard judges a path as spelled where no command it
      // reads made the link), so it passes while the shells write the tracked file
      ['AS3-link-nohup-dd-rel', 'na', 'read c <<< ln; nohup -- "$c" -s ../docs scratch/lnk; echo y > scratch/lnk/report.md', BZ, ['dir', 'names scratch/lnk/report.md, a relative path']],
      ['AS3-link-env-dd-rel', 'na', 'read c <<< ln; env -- "$c" -s ../docs scratch/lnk; echo y > scratch/lnk/report.md', BZ, ['dir', 'names scratch/lnk/report.md, a relative path']],
      ['AS3-residual-link-nohup-dd-abs', 'na', 'read c <<< ln; nohup -- "$c" -s ../docs scratch/lnk; echo y > {NA}/scratch/lnk/report.md', BZ, 'allow'],   // the stated precondition: an absolute write through a link an unread program makes is judged as spelled (decision 47)
      // DISCLOSED (M3's stopping rule; the seventh verify round's tg-m7-2): a loop body whose earlier relative write runs, on the next pass, after a
      // command later in the body that moves the shell or makes a link (a literal cd, a literal ln, a command named by a variable) is read once, at
      // fork main as here, so the shells write through the move or the link; a follow-up, named in decision 47
      ['AS3-residual-loop-plain', 'na', 'read c <<< ln; for i in 1 2; do echo y > scratch/lnk/report.md; "$c" -s ../docs scratch/lnk; done', BZ, 'allow'],
      ['AS3-residual-loop-cd', 'na', 'for i in 1 2; do echo y > report.md; cd docs; done', A, 'allow'],
      ['AS3-residual-loop-ln', 'na', 'for i in 1 2; do echo y > scratch/lnk/report.md; ln -s ../docs scratch/lnk; done', A, 'allow'],
      // and the command named by a variable behind `nohup --`, `env --` or `command --` in that place, read once the same way (found by probe when
      // fork PR 975's body was checked): the road such a head takes leaves the directory not known for what follows it in the text alone, and the
      // write the next pass makes is not read again
      ['AS3-residual-loop-nohup-dd', 'na', 'read c <<< ln; for i in 1 2; do echo y > scratch/lnk/report.md; nohup -- "$c" -s ../docs scratch/lnk; done', BZ, 'allow'],
      ['AS3-residual-loop-env-dd', 'na', 'read c <<< ln; for i in 1 2; do echo y > scratch/lnk/report.md; env -- "$c" -s ../docs scratch/lnk; done', BZ, 'allow'],
      ['AS3-residual-loop-command-dd', 'na', 'read c <<< ln; for i in 1 2; do echo y > scratch/lnk/report.md; command -- "$c" -s ../docs scratch/lnk; done', BZ, 'allow'],
      // DISCLOSED (M3's stopping rule; the seventh verify round's fixer, by probe): the guard reads no text that find's -exec or xargs runs, so a text
      // run once per file or per input line, whose relative write comes before the program that makes a link, passes, at fork main as here, and the
      // second run writes the tracked report through the link the first run made (all three shells, since the text runs in bash; run once, it writes
      // nothing); a follow-up, each named in decision 47
      ['AS3-residual-repeat-find-exec', 'na', "touch {OUT}/scratch/k2.md; find {OUT}/scratch -name '*.md' -exec bash -c 'read c <<< ln; echo y > scratch/lnk/report.md; nohup -- \"$c\" -s ../docs scratch/lnk' \\;", A, 'allow'],
      ['AS3-residual-repeat-xargs', 'na', "printf 'true\\ntrue\\n' | xargs -n1 bash -c 'read c <<< ln; echo y > scratch/lnk/report.md; nohup -- \"$c\" -s ../docs scratch/lnk'", A, 'allow'],   // input lines that name a program on every runner: the evidence gate reads the lines piped toward the shell as its commands, and lines naming no program left the legs NOT RUN (each line is the text's $0 to bash, unused)
      // DISCLOSED (M3's stopping rule): an unread head (unwrapped, or behind `--`) that is backgrounded, piped, in a subshell or in a substitution
      // takes no road there (THE UNHELD ROAD's exemption), at fork main as here, so a link it makes is followed by a later relative write while bash
      // and zsh write the tracked report; a follow-up, each named in decision 47
      ['AS3-residual-fs-plain-bg', 'na', 'read c <<< ln; "$c" -s ../docs scratch/lnk & wait; echo y > scratch/lnk/report.md', BZ, 'allow'],
      ['AS3-residual-fs-plain-pipe', 'na', 'read c <<< ln; "$c" -s ../docs scratch/lnk | cat; echo y > scratch/lnk/report.md', BZ, 'allow'],
      ['AS3-residual-fs-plain-subshell', 'na', 'read c <<< ln; ( "$c" -s ../docs scratch/lnk ); echo y > scratch/lnk/report.md', BZ, 'allow'],
      ['AS3-residual-fs-plain-cmdsub', 'na', 'read c <<< ln; x=$("$c" -s ../docs scratch/lnk); echo y > scratch/lnk/report.md', BZ, 'allow'],
      ['AS3-residual-fs-nohup-dd-bg', 'na', 'read c <<< ln; nohup -- "$c" -s ../docs scratch/lnk & wait; echo y > scratch/lnk/report.md', BZ, 'allow'],
      ['AS3-residual-fs-env-dd-bg', 'na', 'read c <<< ln; env -- "$c" -s ../docs scratch/lnk & wait; echo y > scratch/lnk/report.md', BZ, 'allow'],
      ['AS3-residual-fs-nohup-dd-pipe', 'na', 'read c <<< ln; nohup -- "$c" -s ../docs scratch/lnk | cat; echo y > scratch/lnk/report.md', BZ, 'allow'],
      ['AS3-residual-fs-nohup-dd-subshell', 'na', 'read c <<< ln; ( nohup -- "$c" -s ../docs scratch/lnk ); echo y > scratch/lnk/report.md', BZ, 'allow'],
      // the names stay readable behind external wrappers alone, the `--` spellings among them (M1): a later variable read, a `~/` write and a bare cd
      ['AS3-nohup-dd-no-poison', 'na', 'read c <<< true; nohup -- "$c" x; T={OUT}/t; mkdir -p "$T"; echo y > "$T/a.txt"', N, 'allow'],
      ['AS3-nohup-dd-no-home', 'na', 'read c <<< true; nohup -- "$c" x; echo y > ~/a.txt', N, 'allow'],
      ['AS3-nohup-dd-no-cd', 'na', 'read c <<< true; nohup -- "$c" x; cd; echo y > a.txt', N, 'allow'],
      ['AS3-env-dd-no-poison', 'na', 'read c <<< true; env -- "$c" x; T={OUT}/t; mkdir -p "$T"; echo y > "$T/a.txt"', N, 'allow'],
      ['AS3-env-dd-no-home', 'na', 'read c <<< true; env -- "$c" x; echo y > ~/a.txt', N, 'allow'],
      ['AS3-env-dd-no-cd', 'na', 'read c <<< true; env -- "$c" x; cd; echo y > a.txt', N, 'allow'],
      ['AS3-nice-dd-no-poison', 'na', 'read c <<< true; nice -- "$c" x; T={OUT}/t; mkdir -p "$T"; echo y > "$T/a.txt"', N, 'allow'],
      ['AS3-nice-dd-no-home', 'na', 'read c <<< true; nice -- "$c" x; echo y > ~/a.txt', N, 'allow'],
      ['AS3-nice-dd-no-cd', 'na', 'read c <<< true; nice -- "$c" x; cd; echo y > a.txt', N, 'allow'],
      ['AS3-chain-command-nohup-no-poison', 'na', 'read c <<< true; command nohup -- "$c" x; T={OUT}/t; mkdir -p "$T"; echo y > "$T/a.txt"', N, 'allow'],   // M1: a chain holding an external wrapper (nohup) keeps the names, whatever else precedes it (`command nohup "$c"` qualifies)
      ['AS3-chain-nohup-command-no-poison', 'na', 'read c <<< true; nohup command -- "$c" x; T={OUT}/t; mkdir -p "$T"; echo y > "$T/a.txt"', N, 'allow'],
      // M1's chain spelling (the fifth verify round's tg-m5-3; its filled-in twins went with item 3's split): `command nohup --` keeps the names
      // readable after it (the row above) and takes the road (a later relative write refused as a directory not known), the reason naming the
      // external wrapper the program runs behind, not the first wrapper of the chain (the reviewer's mut F8)
      ['AS3-chain-command-nohup-road', 'na', 'read c <<< true; command nohup -- "$c" x; echo y > scratch/a.txt', N, ['dir', ['names scratch/a.txt, a relative path', 'an earlier `"$c"` behind `nohup` runs a program I do not read'], 'behind `command`']],
      ['AS3-nohup-dd-moves', 'na', 'read c <<< true; nohup -- "$c" x; echo y > scratch/a.txt', N, ['dir', 'names scratch/a.txt, a relative path']],   // M1: the road restored (scratch/a.txt untracked; a cost)
      // behind a wrapper the shell runs itself (not external), the names ARE poisoned: a later variable read is refused as not literal (M1's names
      // predicate; the kept rows, one per non-external wrapper, which the census below ties to the table). Writers N (the T write lands in out/, untracked)
      ['AS3-kept-time-dd', 'na', 'read c <<< true; time -- "$c" x; T={OUT}/t; mkdir -p "$T"; echo y > "$T/a.txt"', N, ['text', [`${POISONED}, so I do not read \`$T\` here`, REMEDY_ABS], NO_CURE]],
      ['AS3-kept-command-dd', 'na', 'read c <<< true; command -- "$c" x; T={OUT}/t; mkdir -p "$T"; echo y > "$T/a.txt"', N, ['text', [`${POISONED}, so I do not read \`$T\` here`, REMEDY_ABS], NO_CURE]],
      ['AS3-kept-builtin-dd', 'na', 'read c <<< true; builtin -- "$c" x; T={OUT}/t; mkdir -p "$T"; echo y > "$T/a.txt"', N, ['text', [`${POISONED}, so I do not read \`$T\` here`, REMEDY_ABS], NO_CURE]],
      ['AS3-kept-exec-dd', 'na', 'read c <<< true; exec -- "$c" x; T={OUT}/t; mkdir -p "$T"; echo y > "$T/a.txt"', N, ['text', [`${POISONED}, so I do not read \`$T\` here`, REMEDY_ABS], NO_CURE]],
      ['AS3-kept-noglob-dd', 'na', 'read c <<< true; noglob -- "$c" x; T={OUT}/t; mkdir -p "$T"; echo y > "$T/a.txt"', N, ['text', [`${POISONED}, so I do not read \`$T\` here`, REMEDY_ABS], NO_CURE]],
      ['AS3-kept-nocorrect-dd', 'na', 'read c <<< true; nocorrect -- "$c" x; T={OUT}/t; mkdir -p "$T"; echo y > "$T/a.txt"', N, ['text', [`${POISONED}, so I do not read \`$T\` here`, REMEDY_ABS], NO_CURE]],
      ['AS3-kept-minus-dd', 'na', 'read c <<< true; - -- "$c" x; T={OUT}/t; mkdir -p "$T"; echo y > "$T/a.txt"', N, ['text', [`${POISONED}, so I do not read \`$T\` here`, REMEDY_ABS], NO_CURE]],
      // and the ROAD behind each of them (the fifth verify round's tg-m5-2: the kept rows pinned it until the round before turned them into names rows):
      // a relative write after the unread head refused as a directory not known, one row per non-external wrapper (the census below ties both row
      // sets to the table), and one whose write lands in the tracked report where bash's \`command\` runs the builtin cd
      ['AS3-road-time-dd', 'na', 'read c <<< true; time -- "$c" x; echo y > scratch/a.txt', N, ['dir', 'names scratch/a.txt, a relative path']],
      ['AS3-road-command-dd', 'na', 'read c <<< true; command -- "$c" x; echo y > scratch/a.txt', N, ['dir', 'names scratch/a.txt, a relative path']],
      ['AS3-road-builtin-dd', 'na', 'read c <<< true; builtin -- "$c" x; echo y > scratch/a.txt', N, ['dir', 'names scratch/a.txt, a relative path']],
      ['AS3-road-exec-dd', 'na', 'read c <<< true; exec -- "$c" x; echo y > scratch/a.txt', N, ['dir', 'names scratch/a.txt, a relative path']],
      ['AS3-road-noglob-dd', 'na', 'read c <<< true; noglob -- "$c" x; echo y > scratch/a.txt', N, ['dir', 'names scratch/a.txt, a relative path']],
      ['AS3-road-nocorrect-dd', 'na', 'read c <<< true; nocorrect -- "$c" x; echo y > scratch/a.txt', N, ['dir', 'names scratch/a.txt, a relative path']],
      ['AS3-road-minus-dd', 'na', 'read c <<< true; - -- "$c" x; echo y > scratch/a.txt', N, ['dir', 'names scratch/a.txt, a relative path']],
      ['AS3-road-command-dd-cd-writes', 'na', 'read c <<< cd; command -- "$c" docs; echo y > report.md', ['bash'], ['dir', 'names report.md, a relative path']],   // zsh's \`command\` finds no external cd, and dash has no \`<<<\`
      // and behind each external wrapper, in the form that reaches an unread head (the sixth verify round's tg-m6-4; the census below ties the road rows
      // to every wrapper of the table): a link made in an untracked directory into the tracked one, then a relative write through it, which bash and
      // zsh land on the tracked report; a lead-bearing wrapper as `<wrapper> <lead> -- "$c"`, which the guard reads as the command named by a variable
      // while the program runs a command named `--` (no shell writes: the guard's reading is the refuse side); sudo asked of the guard alone
      ['AS3-road-env-dd', 'na', 'read c <<< ln; env -- "$c" -s ../docs scratch/lnk; echo y > scratch/lnk/report.md', BZ, ['dir', 'names scratch/lnk/report.md, a relative path']],
      ['AS3-road-nice-dd', 'na', 'read c <<< ln; nice -- "$c" -s ../docs scratch/lnk; echo y > scratch/lnk/report.md', BZ, ['dir', 'names scratch/lnk/report.md, a relative path']],
      ['AS3-road-nohup-dd', 'na', 'read c <<< ln; nohup -- "$c" -s ../docs scratch/lnk; echo y > scratch/lnk/report.md', BZ, ['dir', 'names scratch/lnk/report.md, a relative path']],
      ['AS3-road-setsid-dd', 'na', 'read c <<< ln; setsid -w -- "$c" -s ../docs scratch/lnk; echo y > scratch/lnk/report.md', BZ, ['dir', 'names scratch/lnk/report.md, a relative path']],
      ['AS3-road-ionice-dd', 'na', 'read c <<< ln; ionice -- "$c" -s ../docs scratch/lnk; echo y > scratch/lnk/report.md', BZ, ['dir', 'names scratch/lnk/report.md, a relative path']],
      ['AS3-road-stdbuf-dd', 'na', 'read c <<< ln; stdbuf -oL -- "$c" -s ../docs scratch/lnk; echo y > scratch/lnk/report.md', BZ, ['dir', 'names scratch/lnk/report.md, a relative path']],
      ['AS3-road-numactl-dd', 'na', 'read c <<< ln; numactl -- "$c" -s ../docs scratch/lnk; echo y > scratch/lnk/report.md', BZ, ['dir', 'names scratch/lnk/report.md, a relative path']],
      ['AS3-road-timeout-dd', 'na', 'read c <<< ln; timeout 5 -- "$c" -s ../docs scratch/lnk; echo y > scratch/lnk/report.md', N, ['dir', 'names scratch/lnk/report.md, a relative path']],
      ['AS3-road-flock-dd', 'na', 'read c <<< ln; flock {OUT}/scratch/lk -- "$c" -s ../docs scratch/lnk; echo y > scratch/lnk/report.md', N, ['dir', 'names scratch/lnk/report.md, a relative path']],
      ['AS3-road-taskset-dd', 'na', 'read c <<< ln; taskset 0x1 -- "$c" -s ../docs scratch/lnk; echo y > scratch/lnk/report.md', N, ['dir', 'names scratch/lnk/report.md, a relative path']],
      ['AS3-road-chrt-dd', 'na', 'read c <<< ln; chrt -o 0 -- "$c" -s ../docs scratch/lnk; echo y > scratch/lnk/report.md', N, ['dir', 'names scratch/lnk/report.md, a relative path']],
      ['AS3-road-sudo-dd', 'na', 'read c <<< ln; sudo -- "$c" -s ../docs scratch/lnk; echo y > scratch/lnk/report.md', null, ['dir', 'names scratch/lnk/report.md, a relative path'], null],
      // the operands are words the command takes in the wrapper's directory: a chdir before nohup or setsid (env -C, sudo -D), or before a
      // command named by a variable behind \`--\`, is entered first (tee, the command the variable holds, truncates the tracked report there);
      // sudo's row is asked of the guard alone (no leg runs sudo)
      ['AS3-envC-dashdash-name', 'na', 'read c <<< tee; env -C docs -- "$c" report.md < /dev/null', BZ, 'name'],
      ['AS3-envC-nohup-dashdash-name', 'na', 'read c <<< tee; env -C docs nohup -- "$c" report.md < /dev/null', BZ, 'name'],
      // flock's \`-c\` string runs in the wrappers' directory too, so it is read there (the third verify round's tg-s3-1, an older false allow:
      // bash, zsh and dash overwrote the tracked report); a directory the shell fills in leaves it unknown; the control writes an untracked file
      ['AS3-envC-flock-script', 'na', "env -C docs flock {OUT}/scratch/lk -c 'cp ../base/report.md report.md'", A, 'name'],
      ['AS3-envchdir-flock-script', 'na', "env --chdir=docs flock {OUT}/scratch/lk -c 'cp ../base/report.md report.md'", A, 'name'],
      ['AS3-sudoD-flock-script', 'na', "sudo -D docs flock {OUT}/scratch/lk -c 'cp ../base/report.md report.md'", null, 'name', null],
      ['AS3-envC-var-flock-script-dir', 'na', "read d <<< docs; env -C \"$d\" flock {OUT}/scratch/lk -c 'cp ../base/report.md report.md'", BZ, ['dir', ['names report.md, a relative path', 'an earlier `env -C` names "$d", a directory the shell fills in']]],
      ['AS3-ctl-envC-flock-script-untracked', 'na', "env -C docs flock {OUT}/scratch/lk -c 'cp ../base/report.md other.md'", N, 'allow'],
      // DISCLOSED (M3's stopping rule; found by probe when fork PR 975's body was checked): the same string held in a variable a `read` gave is not
      // read, the residual property's class of a script held in a variable (RT-read-var-head's), so it passes at fork main as here while bash and zsh
      // write the tracked report (dash has no here-string); a follow-up, named in decision 47
      ['AS3-residual-envC-flock-read-script', 'na', "read s <<< 'cp ../base/report.md report.md'; env -C docs flock {OUT}/scratch/lk -c \"$s\"", BZ, 'allow'],
      // S4-1 (the fourth verify round, a false allow this round's flock fix opened and the operand and plain roads carried): GNU env and sudo apply the
      // LAST of one invocation's -C/--chdir/-D, relative to where that invocation starts, while the guard chains them, so a second one in a single
      // invocation leaves the directory not known (the restricted side; a nested `env -C a env -C b` still chains, the control). bash, zsh and dash
      // overwrote the tracked report through the first form
      ['AS3-envC-rpt-flock', 'na', "env -C {OUT} -C . flock {OUT}/scratch/lk -c 'cp base/report.md docs/report.md'", A, ['dir', ['names docs/report.md, a relative path', 'follows another directory option of the same `env`']]],
      ['AS3-envC-rpt-cp', 'na', 'env -C {OUT} -C . cp base/report.md docs/report.md', A, ['dir', ['names docs/report.md, a relative path', 'follows another directory option of the same `env`']]],
      ['AS3-sudoD-rpt-cp', 'na', 'sudo -D {OUT} -D . cp base/report.md docs/report.md', null, ['dir', ['names docs/report.md, a relative path', 'follows another directory option of the same `sudo`']], null],
      // the long spellings (the fifth verify round's tg-m5-1): a repeated \`--chdir\`, \`--chdir\` mixed with \`-C\` either way, the flock form, and sudo's;
      // the refusal spells the option as the command does, a glued value as its one word (tg-m5-7), and so does its sibling for a directory the
      // command cannot enter
      ['AS3-envchdir-rpt-cp', 'na', 'env --chdir={OUT} --chdir=. cp base/report.md docs/report.md', A, ['dir', ['names docs/report.md, a relative path', 'an earlier `env --chdir=.` follows another directory option of the same `env`']]],
      ['AS3-envC-envchdir-rpt-cp', 'na', 'env -C {OUT} --chdir=. cp base/report.md docs/report.md', A, ['dir', ['names docs/report.md, a relative path', 'an earlier `env --chdir=.` follows another directory option of the same `env`']]],
      ['AS3-envchdir-envC-rpt-cp', 'na', 'env --chdir={OUT} -C . cp base/report.md docs/report.md', A, ['dir', ['names docs/report.md, a relative path', 'an earlier `env -C .` follows another directory option of the same `env`']]],
      ['AS3-envchdir-rpt-flock', 'na', "env --chdir={OUT} --chdir=. flock {OUT}/scratch/lk -c 'cp base/report.md docs/report.md'", A, ['dir', ['names docs/report.md, a relative path', 'an earlier `env --chdir=.` follows another directory option of the same `env`']]],
      ['AS3-sudochdir-rpt-cp', 'na', 'sudo --chdir={OUT} --chdir=. cp base/report.md docs/report.md', null, ['dir', ['names docs/report.md, a relative path', 'an earlier `sudo --chdir=.` follows another directory option of the same `sudo`']], null],
      ['AS3-envchdir-nodir-cp', 'na', 'env --chdir=nodir cp base/report.md docs/report.md', N, ['dir', ['names docs/report.md, a relative path', 'an earlier `env --chdir=nodir` names a directory the command cannot enter']]],
      ['AS3-ctl-envC-nested-chain', 'na', 'env -C {OUT} env -C {OUT}/scratch cp {NA}/base/report.md x.txt', N, 'allow'],   // a nested env still chains (two invocations), the control
      // tg-m4-1: the chdirs entered for flock's string are LEFT AFTER it (fromDir), so a later relative write is judged in the shell's directory,
      // not the wrapper's; the discriminator is a relative write that is tracked only under the wrapper's directory
      ['AS3-flock-chdir-left-rel', 'na', 'env -C docs flock {OUT}/scratch/lk -c true; echo x > report.md', N, 'allow'],   // report.md is tracked only under docs; judged in na it is untracked
      ['AS3-ctl-flock-later-tracked', 'na', 'env -C docs flock {OUT}/scratch/lk -c true; echo x > docs/report.md', A, 'name'],   // and a later write that names the tracked file by its real relative path is refused by name
      // tg-m4-5: a nested chdir on the flock road (`env -C a env -C b flock -c`), an older false allow this change closes (the string is read behind both)
      ['AS3-envC-nested-flock', 'na', "env -C scratch env -C ../docs flock {OUT}/scratch/lk -c 'cp ../base/report.md report.md'", A, 'name'],
      ['AS3-ctl-envC-nested-flock-untracked', 'na', "env -C scratch env -C ../docs flock {OUT}/scratch/lk -c 'cp ../base/report.md other.md'", N, 'allow'],
      // a chdir the guard cannot follow (a directory the shell fills in, one the command cannot enter) leaves the operands' directory unknown: refused
      // as a relative path under a directory not known (the verify round's G2; with d=docs, tee truncates the tracked report)
      ['AS3-envC-var-dashdash-dir', 'na', 'read d <<< docs; read c <<< tee; env -C "$d" -- "$c" report.md < /dev/null', BZ, ['dir', ['names report.md, a relative path', 'an earlier `env -C` names "$d", a directory the shell fills in']]],
      // the head's chdirs are entered for its operands alone: a later write is judged in the shell's directory (the verify round's G5)
      ['AS3-envC-dd-bg-later-write', 'na', 'read c <<< tee; env -C docs -- "$c" other.md < /dev/null & echo x > docs/report.md', BZ, 'name'],
      ['AS3-ctl-envC-dd-bg-later-untracked', 'na', 'read c <<< tee; env -C docs -- "$c" other.md < /dev/null & echo x > report.md', N, 'allow'],
      // a \`time -o FILE\` before nohup or setsid, or before another wrapper whose filled-in word refuses, writes FILE (GNU time; bash's and zsh's
      // own \`time\` take no -o, so \`command time\` reaches the program in every shell); from a cwd in no project, refused by name
      ['AS3-time-o-nohup-out', 'out', 'time -o {NA}/docs/report.md nohup "$c" x', ['dash'], 'name', null],
      ['AS3-time-o-nohup-command-out', 'out', 'command time -o {NA}/docs/report.md nohup "$c" x', A, 'name', null],
      ['AS3-time-o-nice-out', 'out', 'time -o {NA}/docs/report.md nice "$c" x', ['dash'], 'name', null],
      ['AS3-time-o-nice-command-out', 'out', 'command time -o {NA}/docs/report.md nice "$c" x', A, 'name', null],
      ['AS3-time-o-envC-nice-out', 'out', 'env -C {NA}/docs time -o report.md nice "$c" x', A, 'name', null],   // behind a chdir the file is written in the wrapper's directory
      // a relative \`time -o FILE\` is opened in the shell's directory before the command runs, so it is judged there, before the road of a command
      // named by a variable leaves the directory unknown (the verify round's G3: nohup's and setsid's filled-in word, and the \`--\` spellings, which
      // take that road), and where a chdir comes after it (G4); the twin: an untracked one from a tracked cwd passes (it was refused for the
      // directory the command itself might move to)
      ['AS3-time-o-rel-nohup-out', 'out', 'command time -o ../notes-api/docs/report.md nohup "$c" x', A, 'name', null],
      ['AS3-time-o-rel-setsid-out', 'out', 'command time -o ../notes-api/docs/report.md setsid "$c" x', A, 'name', null],
      ['AS3-time-o-rel-nohup-dashdash-out', 'out', 'command time -o ../notes-api/docs/report.md nohup -- "$c" x', A, 'name', null],
      ['AS3-time-o-rel-time-dashdash-out', 'out', 'command time -o ../notes-api/docs/report.md -- "$c" x', A, 'name', null],
      ['AS3-time-o-rel-nice-dashdash-out', 'out', 'command time -o ../notes-api/docs/report.md nice -- "$c" x', A, 'name', null],
      ['AS3-time-o-rel-later-envC-out', 'out', 'command time -o ../notes-api/docs/report.md env -C {OUT}/scratch nice "$c" x', A, 'name', null],
      ['AS3-time-o-rel-envC-dashdash-out', 'out', 'env -C {NA}/docs time -o report.md -- "$c" x', A, 'name', null],   // and behind a chdir before it, in the wrapper's directory
      ['AS3-ctl-time-o-dashdash-untracked', 'na', 'command time -o log.txt -- "$c" x', N, 'allow'],
      // and before \`env -S\`, a sudo option read as opaque, or flock's \`-c\` string (the verify round's tg-h-1; from a tracked cwd too for flock;
      // flock rejects its \`-c\` before the lockfile, and time writes the file all the same); sudo's row is asked of the guard alone
      ['AS3-time-o-envS-out', 'out', "command time -o {NA}/docs/report.md env -S 'true x'", A, 'name', null],
      ['AS3-time-o-flock-na', 'na', "command time -o {NA}/docs/report.md flock -c 'true' {OUT}/scratch/lk", A, 'name', 'name'],
      ['AS3-time-o-flock-lock-first-out', 'out', "time -o {NA}/docs/report.md flock {OUT}/scratch/lk -c 'true'", ['dash'], 'name', null],
      ['AS3-time-o-sudo-e-out', 'out', 'command time -o {NA}/docs/report.md sudo -e {OUT}/scratch/keep.md', null, 'name', null],
      // on those roads too, the file is judged behind a chdir before time and in the shell's directory where the chdir comes after it (the third
      // verify round's M3-1: \`env -C <tracked dir> time -o report.md env -S ..\` wrote the tracked report from a cwd in no project); sudo's rows
      // are asked of the guard alone
      ['AS3-time-o-envC-envS-out', 'out', "env -C {NA}/docs time -o report.md env -S 'true x'", A, 'name', null],
      ['AS3-time-o-envC-flock-out', 'out', 'env -C {NA}/docs time -o report.md flock {OUT}/scratch/lk -c true', A, 'name', null],
      ['AS3-time-o-envC-sudo-e-out', 'out', 'env -C {NA}/docs time -o report.md sudo -e {OUT}/scratch/keep.md', null, 'name', null],
      ['AS3-time-o-rel-envC-envS-out', 'out', "command time -o ../notes-api/docs/report.md env -C {OUT}/scratch env -S 'true x'", A, 'name', null],
      ['AS3-time-o-rel-envC-flock-out', 'out', 'command time -o ../notes-api/docs/report.md env -C {OUT}/scratch flock {OUT}/scratch/lk -c true', A, 'name', null],
      ['AS3-time-o-rel-envC-sudo-e-out', 'out', 'command time -o ../notes-api/docs/report.md env -C {OUT}/scratch sudo -e {OUT}/scratch/keep.md', null, 'name', null],
      // the head's file is not judged again behind the wrappers' chdirs after the road (G3's second skip; M3-5): an untracked log before a relative
      // chdir passes
      ['AS3-ctl-time-o-envC-dashdash-untracked', 'na', 'read c <<< true; command time -o log.txt env -C scratch -- "$c" x', N, 'allow'],
      // a cost, refused by name though time writes out/report.md: the guard does not order time's option against the later chdir, so the file is
      // judged in both directories (the fixer's concern 3; the main road over-counts so by design)
      ['AS3-cost-time-o-over-count', 'out', "command time -o report.md env -C {NA}/docs flock -c 'true' {OUT}/scratch/lk", N, 'name', null],
      // M3's stopping rule (the mechanism ruling, 2026-10-03): a false allow fork main also allows is disclosed with a witness row and
      // left as a follow-up, not fixed here. A `--` before a lead-bearing wrapper's lead makes the lead read as the command (`timeout -- 5 cp a b`
      // reads `5` as the command, S4-4), and a command named by a variable behind `nohup --` or `env --` whose output is piped passes as the
      // unwrapped `$e '<cp>' | bash` does (the filled refusal covers `nohup $e`, where the word may be nohup's option, not `nohup -- $e`); each is
      // allowed at fork main and the change
      ['AS3-residual-timeout-dd-lead', 'na', 'timeout -- 5 cp base/report.md docs/report.md', A, 'allow'],
      // and the same \`--\` before the lead of each other lead-bearing wrapper the table marks (the fifth verify round's S5-2; the census below derives the
      // population from the table's \`lead\`): the lockfile, the mask, the priority read as the command; chrt under \`-o\`, whose priority 0 needs no privilege
      ['AS3-residual-flock-dd-lead', 'na', 'flock -- {OUT}/scratch/lk cp base/report.md docs/report.md', A, 'allow'],
      ['AS3-residual-taskset-dd-lead', 'na', 'taskset -- 0x1 cp base/report.md docs/report.md', A, 'allow'],
      ['AS3-residual-chrt-dd-lead', 'na', 'chrt -o -- 0 cp base/report.md docs/report.md', A, 'allow'],
      ['AS3-residual-nohup-dd-pipe', 'nad', "read e <<< echo; nohup -- $e 'cp ../base/report.md report.md' | bash", BZ, 'allow'],
      ['AS3-residual-env-dd-pipe', 'nad', "read e <<< echo; env -- $e 'cp ../base/report.md report.md' | bash", BZ, 'allow'],
      ['AS3-residual-plain-pipe', 'nad', "read e <<< echo; $e 'cp ../base/report.md report.md' | bash", BZ, 'allow'],   // the unwrapped form the two rows above pass as, its own witness (found by probe when fork PR 975's body was checked)
    );
    // the chdir option as the command spells it, in every refusal that names it (the fifth verify round's tg-m5-7, and the sixth's tg-m6-5): for each
    // wrapper whose table carries a chdir option (read from WRAPPER_OPT, as the census below reads it), each spelling commandOf reads (the short and
    // the long option, each with its value glued or a word of its own) and each text that names it (a second chdir option of the same invocation, a
    // directory the command cannot enter, one I cannot resolve: a link loop the command makes); GNU env applies the last of one invocation's options,
    // so the first text's command writes the tracked report in every shell; sudo's rows asked of the guard alone
    {
      const ht = fs.readFileSync(HOOK, 'utf8');
      const ob = ht.slice(ht.indexOf('const WRAPPER_OPT = {'), ht.indexOf('\n};\n', ht.indexOf('const WRAPPER_OPT = {')));
      const keys = [...ob.matchAll(/^ {2}(?:([a-z]+)|'(-)'): \{/gm)].map((m) => ({ name: m[1] || m[2], at: m.index }));
      const chdirSpecs = keys.map((k, i) => { const m = ob.slice(k.at, i + 1 < keys.length ? keys[i + 1].at : ob.length).match(/chdir: \{ short: '([A-Za-z])', long: '([a-z-]+)' \}/); return m ? { wr: k.name, short: m[1], long: m[2] } : null; }).filter(Boolean);
      if (!chdirSpecs.length) throw new Error('no wrapper of WRAPPER_OPT carries a chdir option: the spelling rows read none');
      const spellings = (c, v) => [['short-glued', `${c.wr} -${c.short}${v}`], ['short-separate', `${c.wr} -${c.short} ${v}`], ['long-glued', `${c.wr} --${c.long}=${v}`], ['long-separate', `${c.wr} --${c.long} ${v}`]];
      for (const c of chdirSpecs) {
        const env = c.wr === 'env';
        for (const [form, sp] of spellings(c, '.')) rows.push([`AS3-spelled-${c.wr}-again-${form}`, 'na', `${c.wr} -${c.short} {OUT} ${sp.slice(c.wr.length + 1)} cp base/report.md docs/report.md`, env ? A : null, ['dir', ['names docs/report.md, a relative path', `an earlier \`${sp}\` follows another directory option of the same \`${c.wr}\``]], env ? 'allow' : null]);
        for (const [form, sp] of spellings(c, 'nodir')) rows.push([`AS3-spelled-${c.wr}-enter-${form}`, 'na', `${sp} cp base/report.md docs/report.md`, env ? N : null, ['dir', ['names docs/report.md, a relative path', `an earlier \`${sp}\` names a directory the command cannot enter`]], env ? 'allow' : null]);
        for (const [form, sp] of spellings(c, '{OUT}/l1/x')) rows.push([`AS3-spelled-${c.wr}-resolve-${form}`, 'na', `ln -s {OUT}/l2 {OUT}/l1; ln -s {OUT}/l1 {OUT}/l2; ${sp} cp base/report.md docs/report.md`, env ? N : null, ['dir', ['names docs/report.md, a relative path', `an earlier \`${sp}\` follows a directory I cannot resolve`]], env ? 'allow' : null]);
      }
    }
    // item 8, the session's first case: a mention of PATH (a sed or grep pattern, an echo string) made PATH unreadable, and a copy of any file is a
    // bound path, so every later bare command name was refused as one the lookup might find among the copies (the session's commands, synthetic: a
    // unit file stands in as keep.md, the service manager's calls as reads). As ruled (fork PR 975's round 1, item 8, ROOT): a mention makes a name
    // unreadable only under a head that may assign it in this shell (THE ASSIGNING HEAD, SHELL_WORD_ASSIGNS), so a grep, sed or echo leaves PATH as it
    // was and each passes, a copy named like the later command too; and under a PATH the guard does not read, once the command has bound a path, every
    // bare name refuses again, fork main's rule (ANY_NAME), the narrowing to a name a made path carries gone with every list it needed. The twins: a
    // copied command carrying the name, spliced and judged by name or refused for the PATH not read, and a copy of a source not read
    const K = '{OUT}/scratch/keep.md';
    const BOUND = 'is looked up through a PATH I do not read here, and this command made';
    const ANY_NAME = 'is looked up through a PATH I do not read here, and this command made a path by copying, moving or linking, or by writing it, so which file it names is not known';
    rows.push(
      ['AS8-cp-grep-path-echo', 'na', `cp ${K} {OUT}/scratch/keep.bak; grep -c PATH ${K}; echo done`, N, 'allow'],
      ['AS8-cp-echo-path-word', 'na', `cp ${K} {OUT}/scratch/keep.bak; echo "the PATH line"; echo done`, N, 'allow'],
      ['AS8-mv-grep-path-printf', 'na', `mv ${K} {OUT}/scratch/keep.bak; grep -c PATH {OUT}/scratch/keep.bak; printf 'done\\n'`, N, 'allow'],
      ['AS8-unit-heredoc-sed', 'na', "D={OUT}/scratch; cp -p $D/keep.md $D/keep.md.bak && cat > $D/unit.new <<'EOF'\n[Service]\nEnvironment=PATH=/usr/local/bin:/usr/bin\nEOF\nmv $D/unit.new $D/unit && echo reloaded; tr ' ' '\\n' < $D/unit | sed -E 's/^PATH=.*/PATH=<as above>/'; echo \"lines: $(grep -cE 'APP_(A|B)_PORT' $D/unit)\"", N, 'allow'],
      ['AS8-unit-python-sed', 'na', `cp -p ${K} {OUT}/scratch/keep.bak && python3 - <<'PY'\nopen('{OUT}/scratch/unit.new', 'w').write('Environment=PATH=/usr/bin\\n')\nPY\nsed -E 's/^PATH=.*/PATH=(set)/' {OUT}/scratch/unit.new; printf 'lines: %s\\n' "$(grep -c PATH {OUT}/scratch/unit.new)"`, N, 'allow'],
      // THE ASSIGNING HEAD's own rows: a later program name passes as the session's case does (a builtin's name passes either way), a copy named like
      // that program too (the name the made file carries is no matter while PATH stays readable); a mention under a word that assigns a name it is given still taints (zsh's `print -v` and `getln`, and a
      // head the guard does not read, which may be read, a pattern among them that matches a file named `read` in the cwd: each ran the copied cp onto
      // the tracked report, refused by name); an assignment-shaped word
      // under a program still taints, a stated cost on the restricted side (`grep -c PATH= f` then `ls`)
      ['AS8-cp-sed-path-ls', 'na', `cp ${K} {OUT}/scratch/b.service; sed -n /PATH/p {OUT}/scratch/b.service; ls docs`, N, 'allow'],
      ['AS8-cp-grep-path-collision', 'na', `cp ${K} {OUT}/scratch/ls; grep -c PATH {OUT}/scratch/ls; ls docs`, N, 'allow'],
      ['AS8-root-print-v', 'na', 'cp /usr/bin/cp {OUT}/scratch/c2; print -v PATH {OUT}/scratch; c2 base/report.md docs/report.md', ['zsh'], 'name'],
      ['AS8-root-getln', 'na', 'cp /usr/bin/cp {OUT}/scratch/c2; print -z {OUT}/scratch; getln PATH; c2 base/report.md docs/report.md', ['zsh'], 'name'],
      ['AS8-root-unread-head', 'na', 'printf read > {OUT}/scratch/n; cp /usr/bin/cp {OUT}/scratch/c2; "$(cat {OUT}/scratch/n)" PATH <<< {OUT}/scratch; c2 {NA}/base/report.md {NA}/docs/report.md', BZ, 'name', 'name'],
      ['AS8-root-glob-head', 'na', 'cp /usr/bin/cp {OUT}/scratch/c2; touch {OUT}/scratch/read; cd {OUT}/scratch; rea[d] PATH <<< {OUT}/scratch; c2 {NA}/base/report.md {NA}/docs/report.md', BZ, 'name', 'name'],
      // THE ASSIGNING HEAD's function clause: a head may be a function when it runs though the walk has not seen it defined there, a definition later in
      // the text that a loop's next pass or a body called after it runs first, zsh's `autoload` and `functions -c`, and a `.` through a command named by a
      // variable; each command is walked again with every mention a write, fork main's rule, and refused as fork main refuses it while the shells write
      // (the first five were allowed by THE ASSIGNING HEAD alone, the unread head's by fork main too, which skipped the PATH refusal under an unknown
      // directory); a call of a function the command defines only after its definition runs no function the walk did not read, so case 1's shape beside
      // one passes. An alias the command binds keeps the mention a write (dash expands aliases in a script), a global alias too, and an alias operand
      // whose `=` an expansion may hold binds a name the guard does not read, refused at every later command name as such an alias already was (fork
      // main allowed the copy through it: AS8-alias-unread-operand-cp), a cost where it only prints (AS8-cost-alias-unread-operand)
      ['AS8-root-func-later-loop', 'na', `cp /usr/bin/cp {OUT}/scratch/c2; printf '%s\\n' {OUT}/scratch > {OUT}/p; for i in 1 2; do g read PATH < {OUT}/p; g() { "$@"; }; done; c2 {NA}/base/report.md {NA}/docs/report.md`, A, 'name', 'name'],
      ['AS8-root-func-later-keyword', 'na', `cp /usr/bin/cp {OUT}/scratch/c2; printf '%s\\n' {OUT}/scratch > {OUT}/p; for i in 1 2; do g read PATH < {OUT}/p; function g { "$@"; }; done; c2 {NA}/base/report.md {NA}/docs/report.md`, BZ, 'name', 'name'],
      ['AS8-root-func-later-body', 'na', `cp /usr/bin/cp {OUT}/scratch/c2; printf '%s\\n' {OUT}/scratch > {OUT}/p; h() { g PATH < {OUT}/p; }; g() { read "$@"; }; h; c2 {NA}/base/report.md {NA}/docs/report.md`, A, 'name', 'name'],
      ['AS8-root-func-later-echo', 'na', `cp /usr/bin/cp {OUT}/scratch/c2; printf '%s\\n' {OUT}/scratch > {OUT}/p; for i in 1 2; do echo PATH < {OUT}/p; echo() { read "$@"; }; done; c2 {NA}/base/report.md {NA}/docs/report.md`, A, 'name', 'name'],
      ['AS8-root-func-zsh-autoload', 'na', `cp /usr/bin/cp {OUT}/scratch/c2; printf '%s\\n' {OUT}/scratch > {OUT}/p; mkdir -p {OUT}/fp; printf 'read "$@"\\n' > {OUT}/fp/g; fpath=({OUT}/fp $fpath); autoload -U g; g PATH < {OUT}/p; c2 {NA}/base/report.md {NA}/docs/report.md`, ['zsh'], 'name', 'name'],
      ['AS8-root-func-zsh-functions-c', 'na', `cp /usr/bin/cp {OUT}/scratch/c2; printf '%s\\n' {OUT}/scratch > {OUT}/p; h() { read "$@"; }; functions -c h g; g PATH < {OUT}/p; c2 {NA}/base/report.md {NA}/docs/report.md`, ['zsh'], 'name', 'name'],
      ['AS8-root-func-unread-head-loop', 'na', `cp /usr/bin/cp {OUT}/scratch/c2; printf '%s\\n' {OUT}/scratch:/usr/bin:/bin > {OUT}/p; uniq {W}/tools/w2 {OUT}/scratch/w3; chmod +x {OUT}/scratch/w3; printf 'g() { read "$@"; }\\n' > {OUT}/f.sh; printf '.\\n' > {OUT}/dot; read c < {OUT}/dot; for i in 1 2; do g PATH < {OUT}/p; "$c" {OUT}/f.sh; done; w3`, A, ['text', ANY_NAME]],
      ['AS8-ctl-func-call-unrelated', 'na', `cp ${K} {OUT}/scratch/b.service; h() { echo hi; }; h; grep -c PATH {OUT}/scratch/b.service; ls docs`, N, ['text', ANY_NAME]],
      // RULE S (fork PR 975's round 2, R1, 2026-10-06; enumerate the safe side): ROOT's mention relaxation applies to a command only when it is positively
      // safe, judged over the whole command (one failing segment gives fork main's reading for every mention). Clause (a) SAFE SYNTAX: a `{NAME}` descriptor
      // redirection (`{p}>`, the `:` and echo heads, `>>`, `<`, a prefix assignment before it) assigns the name under any builtin head, which the lexer holds
      // as a word, so the command takes fork main's reading, the name is unreadable, and a write through it refuses (correctness-1; base refused, the PR's
      // ROOT allowed it, bash and zsh wrote); a `{PATH}>` corrupts the PATH a later made name runs through (base refuses the made name, ROOT allowed it).
      // AS8-ctl-func-call-unrelated above is the cost: a function definition is an unquoted parenthesis that is no subshell's or substitution's, so the
      // command takes fork main's reading and the bare `ls` after a bound path refuses, where ROOT alone allowed it (it writes nothing). Clause (b) a word
      // whose resolved, quote-removed text names a command table (bash's BASH_ALIASES, redefined on a later line with aliases expanded, split quoting and a
      // printf -v spelling among them) makes a head run something the guard does not model (fresh-1; base refused, ROOT allowed, bash wrote). Clause (c) a
      // head on the second census axis, may-change-what-a-name-runs (typeset -fu, declare -fu mark a function for autoload, the roads FUNCTION_SOURCES does
      // not carry): base refused, ROOT allowed, zsh wrote. The control keeps the relaxation: the same command without the descriptor redirection, allowed,
      // writing nothing tracked; and the everyday rows above (grep, sed, echo under a program) stay allowed. The `10` and `11` directories give the shell a
      // path for the descriptor number `{p}>` assigns (bash and zsh pick 10 or 11), so the unguarded leg writes the tracked file the exploit reaches.
      ['AS8-ruleS-bracevar-pwd', 'nad', 'mkdir -p 10 11; p={OUT}/x; true {p}>/dev/null; echo y > "$p/../report.md"', BZ, ['text', 'which is not a literal path']],
      ['AS8-ruleS-bracevar-colon', 'nad', 'mkdir -p 10 11; p={OUT}/x; : {p}>/dev/null; echo y > "$p/../report.md"', BZ, ['text', 'which is not a literal path']],
      ['AS8-ruleS-bracevar-echo', 'nad', 'mkdir -p 10 11; p={OUT}/x; echo hi {p}>/dev/null; echo y > "$p/../report.md"', BZ, ['text', 'which is not a literal path']],
      ['AS8-ruleS-bracevar-append', 'nad', 'mkdir -p 10 11; p={OUT}/x; true {p}>>/dev/null; echo y > "$p/../report.md"', BZ, ['text', 'which is not a literal path']],
      ['AS8-ruleS-bracevar-input', 'nad', 'mkdir -p 10 11; p={OUT}/x; true {p}</dev/null; echo y > "$p/../report.md"', BZ, ['text', 'which is not a literal path']],
      ['AS8-ruleS-bracevar-prefix', 'nad', 'mkdir -p 10 11; p={OUT}/x; x=1 true {p}>/dev/null; echo y > "$p/../report.md"', BZ, ['text', 'which is not a literal path']],
      ['AS8-ruleS-bracevar-path', 'out', 'mkdir -p 10 11; cp /usr/bin/cp 10/c2; cp /usr/bin/cp 11/c2; true {PATH}>/dev/null; c2 {NA}/base/report.md {NA}/docs/report.md', BZ, 'name', null],
      ['AS8-ruleS-ctl-noredir', 'nad', 'mkdir -p 10 11; p={OUT}/x; true; echo y > "$p/../report.md"', N, 'allow'],
      ['AS8-ruleS-table-bash-ba', 'na', `OUT={OUT}/scratch\nshopt -s expand_aliases\nBASH_ALIASES[grep]=read\ngrep OUT <<< {NA}/docs\necho x > "$OUT/report.md"`, ['bash'], ['text', 'which is not a literal path']],
      ['AS8-ruleS-table-bash-split', 'na', `OUT={OUT}/scratch\nshopt -s expand_aliases\nprintf -v 'BASH_''ALIASES[grep]' read\ngrep OUT <<< {NA}/docs\necho x > "$OUT/report.md"`, ['bash'], ['text', 'which is not a literal path']],
      ['AS8-ruleS-nameRun-typeset-fu', 'na', `cp /usr/bin/cp {OUT}/scratch/c2; printf '%s\\n' {OUT}/scratch > {OUT}/p; mkdir -p {OUT}/fp; printf 'read "$@"\\n' > {OUT}/fp/g; fpath[1]={OUT}/fp; typeset -fu g; g PATH < {OUT}/p; c2 {NA}/base/report.md {NA}/docs/report.md`, ['zsh'], 'name', 'name'],
      ['AS8-ruleS-nameRun-declare-fu', 'na', `cp /usr/bin/cp {OUT}/scratch/c2; printf '%s\\n' {OUT}/scratch > {OUT}/p; mkdir -p {OUT}/fp; printf 'read "$@"\\n' > {OUT}/fp/g; fpath[1]={OUT}/fp; declare -fu g; g PATH < {OUT}/p; c2 {NA}/base/report.md {NA}/docs/report.md`, ['zsh'], 'name', 'name'],
      // fork PR 975's gap pass (R1, 2026-10-06): `readonly -fu g` marks g for autoload in zsh the same way `typeset -fu` does (readonly is typeset -r in zsh), so readonly
      // belongs on THE NAME-RUN AXIS. It was absent, so the command was positively safe for ROOT and the mention relaxation held (base refused, the PR's HEAD still allowed,
      // zsh wrote); readonly on the axis gives it fork main's reading. The from-out twin (outside 'name') refuses the same way, c2 writing an absolute tracked path.
      ['AS8-ruleS-nameRun-readonly-fu', 'na', `cp /usr/bin/cp {OUT}/scratch/c2; printf '%s\\n' {OUT}/scratch > {OUT}/p; mkdir -p {OUT}/fp; printf 'read "$@"\\n' > {OUT}/fp/g; fpath[1]={OUT}/fp; readonly -fu g; g PATH < {OUT}/p; c2 {NA}/base/report.md {NA}/docs/report.md`, ['zsh'], 'name', 'name'],
      // fork PR 975's gap pass (R1, 2026-10-06): clause (c) read only an UNQUOTED head word (plainWord), so a may-change head spelled with quotes or an escape
      // (`'typeset'`, `"declare"`, `\typeset`) slipped past the axis while the shell still ran the builtin. Clause (c) now reads the head's quote-removed literal
      // text. Base refused each; the PR's HEAD allowed it; a real zsh wrote the tracked file through the autoloaded shadow.
      ['AS8-ruleS-nameRun-typeset-fu-quoted', 'na', `cp /usr/bin/cp {OUT}/scratch/c2; printf '%s\\n' {OUT}/scratch > {OUT}/p; mkdir -p {OUT}/fp; printf 'read "$@"\\n' > {OUT}/fp/g; fpath[1]={OUT}/fp; 'typeset' -fu g; g PATH < {OUT}/p; c2 {NA}/base/report.md {NA}/docs/report.md`, ['zsh'], 'name', 'name'],
      ['AS8-ruleS-nameRun-declare-fu-dquoted', 'na', `cp /usr/bin/cp {OUT}/scratch/c2; printf '%s\\n' {OUT}/scratch > {OUT}/p; mkdir -p {OUT}/fp; printf 'read "$@"\\n' > {OUT}/fp/g; fpath[1]={OUT}/fp; "declare" -fu g; g PATH < {OUT}/p; c2 {NA}/base/report.md {NA}/docs/report.md`, ['zsh'], 'name', 'name'],
      ['AS8-ruleS-nameRun-typeset-fu-bslash', 'na', `cp /usr/bin/cp {OUT}/scratch/c2; printf '%s\\n' {OUT}/scratch > {OUT}/p; mkdir -p {OUT}/fp; printf 'read "$@"\\n' > {OUT}/fp/g; fpath[1]={OUT}/fp; \\typeset -fu g; g PATH < {OUT}/p; c2 {NA}/base/report.md {NA}/docs/report.md`, ['zsh'], 'name', 'name'],
      ['AS8-root-alias-head', 'na', `cp /usr/bin/cp {OUT}/scratch/c2; printf '%s\\n' {OUT}/scratch > {OUT}/p; alias g=read\ng PATH < {OUT}/p\nc2 {NA}/base/report.md {NA}/docs/report.md`, ['dash'], 'name', 'name'],
      ['AS8-root-global-alias', 'na', `cp /usr/bin/cp {OUT}/scratch/c2; printf '%s\\n' {OUT}/scratch > {OUT}/p; alias -g G='read PATH'\nG < {OUT}/p\nc2 {NA}/base/report.md {NA}/docs/report.md`, ['dash'], 'name', 'name'],
      ['AS8-root-alias-unread-operand', 'na', `cp /usr/bin/cp {OUT}/scratch/c2; printf '%s\\n' {OUT}/scratch > {OUT}/p; printf 'g=read\\n' > {OUT}/an; read n < {OUT}/an; alias $n\ng PATH < {OUT}/p\nc2 {NA}/base/report.md {NA}/docs/report.md`, ['dash'], 'name', 'name'],
      // THE ASSIGNING HEAD's table corrected (fork PR 975's gap pass, 2026-10-06; the completeness check's probes, each allowed by the table alone while the
      // shells wrote, where fork main refused it): bash's `test -v` evaluates an array element's subscript as arithmetic, bash's `jobs -x` runs its command
      // in this shell (a function it defines among what it may run, so it is a word of FUNCTION_SOURCES too), and zsh evaluates the operand of break and
      // continue as arithmetic, each assignment in it setting the name; a mention under each taints again, and the census's behavioural leg runs every word
      // the table calls assign-none in each shell present. THE OLDER ARITHMETIC: bash's and zsh's `$[ ... ]` is read as `$(( ... ))`, so a name in it is
      // a write under any head, bare, double-quoted, in a brace list and as a here-string (that one fork main allowed too); a substitution in it is read as
      // the command it runs (AS8-ctl-old-arith-sub, refused by name as fork main refused it), and one with no name in it passes (AS8-ctl-old-arith-plain)
      ['AS8-root-test-v-path', 'nas', "mkdir -p 0; cp /usr/bin/cp 0/c2; test -v 'a[PATH=0]'; c2 {NA}/base/report.md {NA}/docs/report.md", ['bash'], 'name', 'name'],
      ['AS8-root-test-v', 'nan', `p={OUT}/scratch/x.md; test -v 'a[p=0]'; echo y > "$p"`, ['bash'], ['text', ['which is not a literal path', 'a word of `test` that names it']]],
      ['AS8-root-jobs-x-read-path', 'na', 'cp {W}/tools/w2 {OUT}/scratch/w3; jobs -x read PATH <<< {OUT}/scratch:/usr/bin:/bin; w3', ['bash'], ['text', ANY_NAME]],
      ['AS8-root-jobs-x-read', 'nan', 'p={OUT}/scratch/x.md; jobs -x read p <<< 0; echo y > "$p"', ['bash'], ['text', ['which is not a literal path', 'a word of `jobs` that names it']]],
      ['AS8-root-jobs-x-eval-func', 'na', `cp /usr/bin/cp {OUT}/scratch/c2; jobs -x eval 'g() { read "$@"; }'; g PATH <<< {OUT}/scratch; c2 {NA}/base/report.md {NA}/docs/report.md`, ['bash'], 'name', 'name'],
      ['AS8-root-zsh-continue-path', 'nas', "mkdir -p 0; cp /usr/bin/cp 0/c2; for i in 1; do continue '1+(PATH=0)'; done; c2 {NA}/base/report.md {NA}/docs/report.md", ['zsh'], 'name', 'name'],
      ['AS8-root-zsh-continue', 'nan', `p={OUT}/scratch/x.md; for i in 1; do continue '1+(p=0)'; done; echo y > "$p"`, ['zsh'], ['text', ['which is not a literal path', 'a word of `continue` that names it']]],
      ['AS8-root-zsh-break', 'nan', `p={OUT}/scratch/x.md; for i in 1; do break '1+(p=0)'; done; echo y > "$p"`, ['zsh'], ['text', ['which is not a literal path', 'a word of `break` that names it']]],
      ['AS8-root-old-arith-path-ls', 'nas', 'mkdir -p 0; cp /usr/bin/cp 0/c2; ls $[PATH=0] > /dev/null 2>&1; c2 {NA}/base/report.md {NA}/docs/report.md', BZ, 'name', 'name'],
      ['AS8-root-old-arith-path-echo', 'nas', 'mkdir -p 0; cp /usr/bin/cp 0/c2; echo $[PATH=0]; c2 {NA}/base/report.md {NA}/docs/report.md', BZ, 'name', 'name'],
      ['AS8-root-old-arith-path-dq', 'nas', 'mkdir -p 0; cp /usr/bin/cp 0/c2; echo "$[PATH=0]"; c2 {NA}/base/report.md {NA}/docs/report.md', BZ, 'name', 'name'],
      ['AS8-root-old-arith-echo', 'nan', 'p={OUT}/scratch/x.md; echo $[p=0]; echo y > "$p"', BZ, ['text', ['which is not a literal path', 'through an arithmetic body']]],
      ['AS8-root-old-arith-cat', 'nan', 'p={OUT}/scratch/x.md; cat $[p=0] 2>/dev/null; echo y > "$p"', BZ, ['text', ['which is not a literal path', 'through an arithmetic body']]],
      ['AS8-root-old-arith-grep-dq', 'nan', 'p={OUT}/scratch/x.md; grep -c x "$[p=0]" 2>/dev/null; echo y > "$p"', BZ, ['text', ['which is not a literal path', 'through an arithmetic body']]],
      ['AS8-root-old-arith-brace', 'nan', 'p={OUT}/scratch/x.md; echo {1..$[p=0]}; echo y > "$p"', BZ, ['text', ['which is not a literal path', 'through an arithmetic body']]],
      ['AS8-root-old-arith-herestring', 'nan', 'p={OUT}/scratch/x.md; : <<< $[p=0]; echo y > "$p"', BZ, ['text', ['which is not a literal path', 'through an arithmetic body']]],
      ['AS8-ctl-old-arith-sub', 'na', 'echo $[ $(cp base/report.md docs/report.md; echo 1) ]', A, 'name'],
      ['AS8-ctl-old-arith-plain', 'na', 'echo $[1+2]; ls docs', N, 'allow'],
      // THE OLDER ARITHMETIC's two readings (fork PR 975's round 1, the text lens's tg-t12-1): read as arithmetic alone, a `$[ ... ]` in a write target
      // made the word one the guard does not read, which passes from a cwd in no project, so a target that climbs from it into a project was allowed while
      // bash and zsh wrote through the folder its number names and dash through a folder named as the `$[` is spelled, where fork main read it as text and
      // refused (red before the text reading: each was allowed). judge reads every command with `$[` read as text (its first walk since fork PR 975's
      // round 2, THE ORDER) and one whose walk met a `$[` as arithmetic too, any refusal of either reading standing: bare, double-quoted (refused by name,
      // as fork main refused it), a sum, dash's folder named `$[0]`, and a `$[` only an eval's text spells (its quotes split the dollar from the bracket
      // in the command itself); a `$[` in a text bash runs with `-c`, read under bash's grammar (red where the text switch or the note of a `$[` holds
      // under zsh's grammar alone), and one after a command named by a variable, which only the text reading's walk with that head's poison set aside
      // refuses (red where the text reading runs only the walk that takes the poison; the text lens's tg-t13-1 and tg-t13-2); the control, a `$[` in a
      // target outside every project, which both readings allow
      ['AS8-root-old-arith-text-lead-out', 'out', 'mkdir -p 0; echo y > $[0]/../../notes-api/docs/report.md', BZ, ['text', 'names $[0]/../../notes-api/docs/report.md, which is not a literal path'], null],
      ['AS8-root-old-arith-text-dash-out', 'out', "mkdir -p '$[0]'; echo y > $[0]/../../notes-api/docs/report.md", ['dash'], ['text', 'names $[0]/../../notes-api/docs/report.md, which is not a literal path'], null],
      ['AS8-root-old-arith-text-dq-out', 'out', 'mkdir -p 0; echo y > "$[0]"/../../notes-api/docs/report.md', BZ, 'name', null],
      ['AS8-root-old-arith-text-sum-out', 'out', 'mkdir -p 2; echo y > $[1+1]/../../notes-api/docs/report.md', BZ, ['text', 'names $[1+1]/../../notes-api/docs/report.md, which is not a literal path'], null],
      ['AS8-root-old-arith-text-eval-out', 'out', "mkdir -p 0; eval 'echo y > $''[0]/../../notes-api/docs/report.md'", BZ, ['text', 'through `eval` names $[0]/../../notes-api/docs/report.md, which is not a literal path'], null],
      ['AS8-root-old-arith-text-bash-c-out', 'out', "mkdir -p 0; bash -c 'echo y > $[0]/../../notes-api/docs/report.md'", A, ['text', 'names $[0]/../../notes-api/docs/report.md, which is not a literal path'], null],
      ['AS8-root-old-arith-text-two-walks-out', 'out', 'X={OUT}/scratch; read c <<< true; "$c" x; cd "$X"; mkdir -p 0; echo y > $[0]/../../../notes-api/docs/report.md', BZ, ['text', 'names $[0]/../../../notes-api/docs/report.md, which is not a literal path'], null],
      ['AS8-ctl-old-arith-text-target-out', 'out', 'echo y > {OUT}/scratch/n$[1+1].md', N, 'allow', null],
      // the arithmetic reading's stated cost (fork PR 975's round 1, a concern the fixer raised): a double-quoted `$[ ... ]` inside a target from a tracked
      // cwd is a word the guard does not read, refused as not literal, where fork main read it as text and allowed it, and no shell writes a tracked file
      ['AS8-cost-old-arith-dq-target', 'na', 'echo y > "scratch/n$[1+1].md"', N, ['text', 'names "scratch/n$[1+1].md", which is not a literal path']],
      // and the cost fork main has for `$((` that reading `$[` as arithmetic extends to `$[` (fork PR 975's round 2, tests-5): in an unquoted here-document
      // body an arithmetic expansion the guard does not read is held in the word as a placeholder, which reaches the check of the directory the path passes
      // through, so the refusal names the path with a blank where the expansion stood and an error of the check's own, and its remedy, to make that directory
      // readable, does not lift it (the directory is readable); fork main allowed this here-document fed to bash, and no shell writes a tracked file. The
      // M2 census holds it as its one stated exception (M2_STANDS below), so the follow-up, which reads the placeholder as the expansion it stands for,
      // turns that pin red
      ['AS8-cost-old-arith-heredoc-placeholder-out', 'out', 'mkdir -p {OUT}/scratch/0; bash <<EOF\necho y > {OUT}/scratch/$[0]/a.txt\nEOF', N, ['text', ['and I could not check {OUT}/scratch on that path', 'ERR_INVALID_ARG_VALUE']], null],
      // M3, pre-existing (fork main allows each, as this change does, while bash and zsh write; a witness row each, named in decision 47; found by the shell
      // lens on fork PR 975's round 1): a `$[` whose bracket holds a parenthesis or opens with a space, in a target that climbs from a cwd in no project into
      // a project. Read as arithmetic it is a word the guard does not read, which passes from such a cwd as `$((0))` does there (B2's boundary); read as text
      // the target ends at the parenthesis or the space, a file named `$[` in the cwd, so the text reading does not refuse it either. The follow-up keeps
      // the bracket's text, to its matching `]`, in the target under the text reading, judged by its spelling as `$[0]` is
      ['AS8-residual-old-arith-paren-out', 'out', 'mkdir -p 0; echo y > $[(0)]/../../notes-api/docs/report.md', BZ, 'allow', null],
      ['AS8-residual-old-arith-space-out', 'out', 'mkdir -p 0; echo y > $[ 0 ]/../../notes-api/docs/report.md', BZ, 'allow', null],
      ['AS8-alias-unread-operand-cp', 'nad', `printf 'g=cp\\n' > ../scratch/an; read n < ../scratch/an; alias $n\ng ../base/report.md report.md`, ['dash'], ['text', 'binds a name I do not read']],
      ['AS8-cost-alias-unread-operand', 'na', `printf 'll\\n' > {OUT}/an; read n < {OUT}/an; alias $n; ls docs`, N, ['text', 'binds a name I do not read']],
      ['AS8-cost-mention-assignment-shaped', 'na', `cp ${K} {OUT}/scratch/b.service; grep -c PATH= {OUT}/scratch/b.service; ls docs`, N, ['text', ANY_NAME]],
      // fork main's own refusal, a stated cost of item 8 as ruled: under a PATH the command sets to a value the guard does not read, a bare name no
      // made file carries is refused once a path is bound (the narrowing had let `ls` pass)
      ['AS8-cost-unread-path-other-name', 'na', 'cp "$(command -v cp)" {OUT}/scratch/c2; PATH=$X:$PATH; ls docs', N, ['text', ANY_NAME]],
      ['AS8-armed-echo', 'na', 'cp /usr/bin/cp {OUT}/scratch/echo; PATH=$X:$PATH; echo base/report.md docs/report.md', N, 'name'],   // echo is a builtin in every shell: the copy never runs, the refusal is the splice's reading
      ['AS8-armed-c2', 'na', 'read X <<< {OUT}/scratch; cp /usr/bin/cp {OUT}/scratch/c2; PATH=$X:$PATH; c2 base/report.md docs/report.md', BZ, 'name'],
      ['AS8-armed-c2-untracked', 'na', 'read X <<< {OUT}/scratch; cp /usr/bin/cp {OUT}/scratch/c2; PATH=$X:$PATH; c2 base/report.md docs/other.md', N, ['text', ANY_NAME]],
      ['AS8-armed-mv-untracked', 'na', 'read X <<< {OUT}/scratch; mv {OUT}/scratch/keep.md {OUT}/scratch/c2; PATH=$X:$PATH; c2 base/report.md docs/other.md', N, ['text', [BOUND, 'Spell the command by the full path of the program it should run, not a path this command made: ']]],   // a moved file carries the name too (T3-9)
      ['AS8-ctl-mv-fullpath', 'na', 'read X <<< {OUT}/scratch; mv {OUT}/scratch/keep.md {OUT}/scratch/c2; PATH=$X:$PATH; /usr/bin/cp base/report.md docs/other.md', N, 'allow'],   // the ONE remedy (M2): the program's full path, not the made path
      ['AS8-armed-c2-unread-source', 'na', 'read X <<< {OUT}/scratch; cp "$(command -v cp)" {OUT}/scratch/c2; PATH=$X:$PATH; c2 base/report.md docs/report.md', BZ, ['text', '`c2`']],
      ['AS8-ctl-c2-unread-fullpath', 'na', 'read X <<< {OUT}/scratch; cp "$(command -v cp)" {OUT}/scratch/c2; PATH=$X:$PATH; /usr/bin/cp base/report.md docs/other.md', N, 'allow'],   // an allowed control: the program's full path in place of the bound name (the bound-name refusal's one remedy, whose own twin for AS8-armed-c2-unread-source the census below builds)
      // S4-3 (the fourth verify round, a round-1/2 false allow): a backup option on cp, mv, install or ln (-b, --backup, -S, --suffix) makes a side-file
      // under a name the guard does not follow, which bash and zsh ran onto the tracked report (dash does not stash); refused now as every bare name
      // under the unreadable PATH is (item 8 as ruled), so the backup's own rows, one per option, form and verb, went with the narrowing they pinned;
      // the twin with no backup option is refused too, fork main's own refusal (a cost row)
      ['AS8-backup-cp', 'na', 'read X <<< {OUT}/scratch; cp /usr/bin/cp {OUT}/scratch/x; cp -b -S zz /usr/bin/true {OUT}/scratch/x; PATH=$X:$PATH; xzz base/report.md docs/report.md', BZ, ['text', ANY_NAME]],
      // a definition's name runs no command, so it is no lookup (definesName); since fork PR 975's round 2 (R2) the bare `:` in the body is refused as
      // every bare name is, as at fork main, a stated cost (AS8-ctl-function-definition), so the definition is pinned with a body spelled by path
      ['AS8-ctl-function-definition', 'na', 'read X <<< {OUT}/scratch; cp /usr/bin/cp {OUT}/scratch/x; PATH=$X:$PATH; f() { :; }', N, ['text', [ANY_NAME, 'its command name names :', 'Make the change with track-edit instead']]],
      ['AS8-ctl-function-definition-path-body', 'na', 'read X <<< {OUT}/scratch; cp /usr/bin/cp {OUT}/scratch/x; PATH=$X:$PATH; f() { /usr/bin/true; }', N, 'allow'],
      ['AS8-cost-function-call', 'na', 'read X <<< {OUT}/scratch; cp /usr/bin/cp {OUT}/scratch/x; PATH=$X:$PATH; f() { :; }; f', N, ['text', [ANY_NAME, 'Make the change with track-edit instead']]],   // a call of it: fork main's own refusal, with no full path to name
      ['AS8-cost-backup-none', 'na', 'read X <<< {OUT}/scratch; cp /usr/bin/cp {OUT}/scratch/x; cp /usr/bin/true {OUT}/scratch/x; PATH=$X:$PATH; xzz base/report.md docs/report.md', N, ['text', ANY_NAME]],
      // a builtin's or a keyword's bare name after a backup or beside a made file of its name (a cd, an export, an echo whose name the backup took): the
      // sixth verify round's tg-t6-3 had let it pass as a name the three shells run as their own (THE SHELL'S OWN NAME); fork PR 975's round 2 (R2) took
      // that exemption out, since a function or an alias the guard does not read, or dash's `%builtin` PATH entry, makes the shell look such a name up
      // after all (fresh-2, correctness-3: AS8-builtin-shadow-*, AS8-builtin-dash-pctbuiltin-*), so each is refused again as at fork main, a stated cost
      // on which no shell writes, with no remedy where no program stands for the name (cd, export) and the program's full path where one does (echo)
      ['AS8-builtin-cd-after-backup', 'na', 'read X <<< {OUT}/scratch; cp /usr/bin/cp {OUT}/scratch/x; cp -b /usr/bin/true {OUT}/scratch/x; PATH=$X:$PATH; cd {OUT}', N, ['text', [ANY_NAME, 'its command name names cd', 'Make the change with track-edit instead']]],
      ['AS8-builtin-export-after-backup', 'na', 'read X <<< {OUT}/scratch; cp /usr/bin/cp {OUT}/scratch/x; cp -b /usr/bin/true {OUT}/scratch/x; PATH=$X:$PATH; export Y=1', N, ['text', [ANY_NAME, 'its command name names export', 'Make the change with track-edit instead']]],
      ['AS8-builtin-echo-backup-name', 'na', 'read X <<< {OUT}/scratch; cp /usr/bin/cp {OUT}/scratch/ec; cp -b -S ho /usr/bin/true {OUT}/scratch/ec; PATH=$X:$PATH; echo base/report.md docs/report.md', N, ['text', [ANY_NAME, 'its command name names echo', 'Spell the command by the full path of the program it should run']]],
      ['AS8-builtin-cd-same-name-untracked', 'na', 'read X <<< {OUT}/scratch; cp {OUT}/scratch/keep.md {OUT}/scratch/cd; PATH=$X:$PATH; cd docs; echo y > other.md', N, ['text', [ANY_NAME, 'its command name names cd', 'Make the change with track-edit instead']]],
      ['AS8-builtin-cd-same-name', 'na', 'read X <<< {OUT}/scratch; cp {OUT}/scratch/keep.md {OUT}/scratch/cd; PATH=$X:$PATH; cd docs; echo y > report.md', BZ, 'name'],
      ['AS8-builtin-nonbuiltin-after-backup', 'na', 'read X <<< {OUT}/scratch; cp /usr/bin/cp {OUT}/scratch/x; cp -b /usr/bin/true {OUT}/scratch/x; PATH=$X:$PATH; ls docs', N, ['text', ANY_NAME]],
      ['AS8-builtin-env-echo-after-backup', 'na', 'read X <<< {OUT}/scratch; cp /usr/bin/cp {OUT}/scratch/ec; cp -b -S ho /usr/bin/true {OUT}/scratch/ec; PATH=$X:$PATH; env echo base/report.md docs/report.md', BZ, ['text', ANY_NAME]],
      ['AS8-builtin-enable-script', 'na', "printf 'cp base/report.md docs/report.md\\n' > {OUT}/scratch/s.sh; cat {OUT}/scratch/s.sh > {OUT}/scratch/echo; chmod +x {OUT}/scratch/echo; read X <<< {OUT}/scratch; PATH=$X:$PATH; enable -n echo; echo", ['bash'], ['text', ANY_NAME]],
      ['AS8-builtin-noenable-script', 'na', "printf 'cp base/report.md docs/report.md\\n' > {OUT}/scratch/s.sh; cat {OUT}/scratch/s.sh > {OUT}/scratch/echo; chmod +x {OUT}/scratch/echo; read X <<< {OUT}/scratch; PATH=$X:$PATH; echo", N, ['text', [ANY_NAME, 'its command name names echo']]],   // refused again since R2, a stated cost (no `%builtin` on this PATH, so dash runs its builtin too)
      // M3's stopping rule (the fifth verify round): two false allows fork main also allows, disclosed with a witness row each and left as follow-ups.
      // A backup reached by its explicit path (S5-1): the guard binds no backup path, so neither the bound name nor the bound path catches it; and a
      // file the command made from a source the guard does not read, run by its absolute path after a construct that leaves the directory unknown
      // (tg-m5-8: the bound head is read only where the directory is known)
      ['AS8-residual-backup-explicit-path', 'na', 'cp /usr/bin/cp {OUT}/scratch/x; cp -b -S zz /usr/bin/true {OUT}/scratch/x; {OUT}/scratch/xzz base/report.md docs/report.md', A, 'allow'],
      // M3, pre-existing (fork main allows each, as this change does, while the shells write; a witness row each, named in decision 47): PATH set inside a
      // text the guard reads as a poison, a call of a function the command defines or an eval's text, or through zsh's `path` array, which zsh ties to PATH
      // (an assignment of the array, one that keeps `$path` after a new entry, a `+=`, an element, `read -A path`, and the `(P)` flag with `::=` through a
      // name holding PATH: the sound lens's tg-r12-1 on fork PR 975's round 1), is read as the PATH the command gave (none, the guard's own), so a copied
      // command run by its bare name passes; the follow-up reads PATH as unreadable once the command is poisoned or names `path`
      ['AS8-residual-path-func-call', 'na', 'cp /usr/bin/cp {OUT}/scratch/c2; g() { read "$@"; }; g PATH <<< {OUT}/scratch; c2 base/report.md docs/report.md', BZ, 'allow'],
      ['AS8-residual-path-eval', 'na', "cp /usr/bin/cp {OUT}/scratch/c2; eval 'PATH={OUT}/scratch'; c2 base/report.md docs/report.md", A, 'allow'],
      ['AS8-residual-path-zsh-array', 'na', 'cp /usr/bin/cp {OUT}/scratch/c2; path=({OUT}/scratch); c2 base/report.md docs/report.md', ['zsh'], 'allow'],
      ['AS8-residual-path-zsh-array-keep', 'na', 'cp /usr/bin/cp {OUT}/scratch/c2; path=({OUT}/scratch $path); c2 base/report.md docs/report.md', ['zsh'], 'allow'],
      ['AS8-residual-path-zsh-array-append', 'na', 'cp /usr/bin/cp {OUT}/scratch/c2; path+=({OUT}/scratch); c2 base/report.md docs/report.md', ['zsh'], 'allow'],
      ['AS8-residual-path-zsh-array-element', 'na', 'cp /usr/bin/cp {OUT}/scratch/c2; path[1]={OUT}/scratch; c2 base/report.md docs/report.md', ['zsh'], 'allow'],
      ['AS8-residual-path-zsh-read-A', 'na', 'cp /usr/bin/cp {OUT}/scratch/c2; read -A path <<< {OUT}/scratch; c2 base/report.md docs/report.md', ['zsh'], 'allow'],
      ['AS8-residual-path-zsh-indirect', 'na', 'cp /usr/bin/cp {OUT}/scratch/c2; n=PATH; : ${(P)n::={OUT}/scratch:$PATH}; c2 base/report.md docs/report.md', ['zsh'], 'allow'],
      // M3, pre-existing (fork main allows each, as this change does, while a shell writes; a witness row each, named in decision 47; found by the completeness
      // check on fork PR 975's gap pass): a name an expansion the guard does not read assigns, inside an array subscript, a substring offset, an arithmetic
      // expansion in an operator's word (the older spelling too), zsh's `(P)` flag with `::=`, a glob qualifier's code or the `(e)` flag's text; zsh's
      // arithmetic count of repeat; the command bash's `jobs -x` runs, which the walk does not peel; and a trap's action, read where the trap is set while it
      // runs where it fires, after an exit whose status assigns the name it writes through
      ['AS8-residual-assign-subscript', 'nan', 'p={OUT}/scratch/x.md; echo ${a[p=0]}; echo y > "$p"', BZ, 'allow'],
      ['AS8-residual-assign-offset', 'nan', 'p={OUT}/scratch/x.md; v=abc; echo ${v:p=0}; echo y > "$p"', ['bash'], 'allow'],
      ['AS8-residual-assign-default-arith', 'nan', 'p={OUT}/scratch/x.md; echo "${v:-$((p=0))}"; echo y > "$p"', A, 'allow'],
      ['AS8-residual-assign-default-old-arith', 'nan', 'p={OUT}/scratch/x.md; echo ${v:-$[p=0]}; echo y > "$p"', BZ, 'allow'],
      ['AS8-residual-assign-zsh-indirect', 'nan', 'n=p; p={OUT}/scratch/x.md; : ${(P)n::=0}; echo y > "$p"', ['zsh'], 'allow'],
      ['AS8-residual-assign-zsh-glob-qualifier', 'nan', `p={OUT}/scratch/x.md; echo /(e:'p=0':); echo y > "$p"`, ['zsh'], 'allow'],
      ['AS8-residual-assign-zsh-e-flag', 'nan', `p={OUT}/scratch/x.md; echo \${(e):-'$((p=0))'}; echo y > "$p"`, ['zsh'], 'allow'],
      ['AS8-residual-assign-zsh-repeat', 'nan', `p={OUT}/scratch/x.md; repeat 'p=1' true; echo y > "$p"`, ['zsh'], 'allow'],
      ['AS8-residual-jobs-x-cp', 'na', 'jobs -x cp base/report.md docs/report.md', ['bash'], 'allow'],
      ['AS8-residual-assign-zsh-exit-trap', 'nan', `p={OUT}/scratch/x.md; trap 'echo y > "$p"' EXIT; exit 'p=0'`, ['zsh'], 'allow'],
      // M3, pre-existing (fork main allows it, as this change does, while bash writes; a witness row, named in decision 47; found by probe when fork PR
      // 975's body was checked): an assignment of RANDOM is read as the value it gives, while bash keeps no such value (it evaluates the value as
      // arithmetic, reports the error and goes on, `$RANDOM` a number), so a target that climbs out of the tracked notes/ folder through the value
      // makes a new file in that folder in bash; zsh stops at the error and dash keeps the text, so neither writes
      ['AS8-residual-special-param-random', 'na', 'RANDOM=../scratch/x; echo y > notes/$RANDOM', ['bash'], 'allow'],
      // M3, pre-existing (fork main allows each, as this change does, while zsh writes; a witness row each, named in decision 47; found by the text lens on
      // fork PR 975's round 1, tg-t12-9): zsh closes a try block at a `}` with no `;` before it when `always` follows (`{ cmd } always { .. }`), where the
      // lexer reads the `}`, `always` and `{` as words of the command inside, so an assignment, a read and a cd in the block do not count and a write
      // through the name or into the directory passes; the control closes the block with `;`, refused as fork main refuses it. The follow-up reads that `}`
      // as the group's close where `always` follows
      ['AS8-residual-zsh-always-read', 'nan', 'p={OUT}/scratch/x.md; { read p <<< 0 } always { echo y > "$p" }', ['zsh'], 'allow'],
      ['AS8-residual-zsh-always-assign', 'nan', 'p={OUT}/scratch/x.md; { p=0 } always { echo y > "$p" }', ['zsh'], 'allow'],
      ['AS8-residual-zsh-always-cd-out', 'out', '{ cd {NA}/docs } always { echo y > report.md }', ['zsh'], 'allow', null],
      ['AS8-ctl-zsh-always-semicolon', 'nan', 'p={OUT}/scratch/x.md; { read p <<< 0; } always { echo y > "$p"; }', ['zsh'], ['text', ['names "$p", which is not a literal path', 'a word of `read` that names it']]],
      ['AS8-residual-bound-abs-after-cd', 'na', 'read d <<< docs; cp "$(command -v cp)" {OUT}/scratch/c2; cd "$d"; {OUT}/scratch/c2 {NA}/base/report.md {NA}/docs/report.md', BZ, 'allow'],
      // a file this command made by moving or writing it from a source the guard does not read, run by its path, says so (the fifth verify round's T5-11)
      ['AS8-unread-source-mv-head', 'na', 'mv "$S" {NA}/scratch/c2; {NA}/scratch/c2 base/report.md docs/other.md', N, ['text', 'is a path this command made by copying, moving or linking, or by writing it, from a source I do not read', 'by copying or linking a source'], ['text', 'is a path this command made by copying, moving or linking, or by writing it, from a source I do not read']],
      ['AS8-unread-source-cat-head', 'na', 'cat "$S" > {NA}/scratch/c2; {NA}/scratch/c2 base/report.md docs/other.md', N, ['text', 'is a path this command made by copying, moving or linking, or by writing it, from a source I do not read', 'by copying or linking a source'], ['text', 'is a path this command made by copying, moving or linking, or by writing it, from a source I do not read']],
    );
    // THE SHELL'S GATE's rows (the seventh verify round's tg-m7-1): a name read before an `enable`, a `disable` or a `zmodload` may run after it (a loop's
    // next pass, a trap action, a function called in the loop), so a script written into place as echo runs from PATH once the builtin is off (bash, or
    // zsh for `disable`), as does the copied cp stashed as echo by a backup (WROTE_ECHO, STASHED_ECHO). The gate had withdrawn THE SHELL'S OWN NAME's
    // exemption for the whole command; since fork PR 975's round 2 (R2) took that exemption out, every builtin and keyword of these commands is refused
    // under the unreadable PATH as at fork main, gate or no gate, so each row stays a refused write (the shells write) and pins the bound-name refusal,
    // not the gate. The gate's own reading now is THE ASSIGNING HEAD's (AS8-root-gate-*)
    const WROTE_ECHO = "printf 'cp base/report.md docs/report.md\\n' > {OUT}/scratch/s.sh; cat {OUT}/scratch/s.sh > {OUT}/scratch/echo; chmod +x {OUT}/scratch/echo; read X <<< {OUT}/scratch; PATH=$X:$PATH; ";
    const STASHED_ECHO = 'read X <<< {OUT}/scratch; cp /usr/bin/cp {OUT}/scratch/ec; cp -b -S ho /usr/bin/true {OUT}/scratch/ec; PATH=$X:$PATH; ';
    const BACKED_X = 'read X <<< {OUT}/scratch; cp /usr/bin/cp {OUT}/scratch/x; cp -b /usr/bin/true {OUT}/scratch/x; PATH=$X:$PATH; ';
    rows.push(
      ['AS8-builtin-gate-before-path', 'na', "printf 'cp base/report.md docs/report.md\\n' > {OUT}/scratch/s.sh; cat {OUT}/scratch/s.sh > {OUT}/scratch/echo; chmod +x {OUT}/scratch/echo; enable -n echo; read X <<< {OUT}/scratch; PATH=$X:$PATH; echo", ['bash'], ['text', BOUND]],
      ['AS8-builtin-gate-ansic-before-path', 'na', "printf 'cp base/report.md docs/report.md\\n' > {OUT}/scratch/s.sh; cat {OUT}/scratch/s.sh > {OUT}/scratch/echo; chmod +x {OUT}/scratch/echo; $'\\x65nable' -n echo; read X <<< {OUT}/scratch; PATH=$X:$PATH; echo", ['bash'], ['text', BOUND]],   // a spelling the scan does not read: the walk's own
      ['AS8-builtin-gate-for', 'na', `${WROTE_ECHO}for i in 1 2; do echo; enable -n echo; done`, ['bash'], ['text', BOUND]],
      ['AS8-builtin-gate-while', 'na', `printf '\\145nable' > {OUT}/scratch/n; ${WROTE_ECHO}n=0; while [ $n -lt 2 ]; do echo; "$(< {OUT}/scratch/n)" -n echo; n=$((n+1)); done`, ['bash'], ['text', BOUND]],
      ['AS8-builtin-gate-until', 'na', `printf '\\145nable' > {OUT}/scratch/n; ${WROTE_ECHO}n=0; until [ $n -ge 2 ]; do echo; "$(< {OUT}/scratch/n)" -n echo; n=$((n+1)); done`, ['bash'], ['text', BOUND]],
      ['AS8-builtin-gate-trap-exit', 'na', `${WROTE_ECHO}trap echo EXIT; enable -n echo`, ['bash'], ['text', BOUND]],
      ['AS8-builtin-gate-trap-debug', 'na', `${WROTE_ECHO}trap echo DEBUG; enable -n echo; true`, ['bash'], ['text', BOUND]],
      ['AS8-builtin-gate-disable-for', 'na', `${WROTE_ECHO}for i in 1 2; do echo; disable echo; done`, ['zsh'], ['text', BOUND]],
      ['AS8-builtin-gate-func-loop', 'na', `${WROTE_ECHO}for i in 1 2; do f() { echo; }; f; enable -n echo; done`, ['bash'], ['text', BOUND]],   // the function defined in the loop, so the loop's keyword is the first refusal (M2's no-remedy form) as in the other loop rows
      ['AS8-builtin-gate-ansic-loop', 'na', `${WROTE_ECHO}for i in 1 2; do echo; $'\\x65nable' -n echo; done`, ['bash'], ['text', BOUND]],   // a spelling the scan does not read: the walk's own
      ['AS8-builtin-gate-eval-ansic-loop', 'na', `${WROTE_ECHO}for i in 1 2; do echo; eval "\\$'\\\\x65nable' -n echo"; done`, ['bash'], ['text', BOUND]],   // the gate shared with a text the command runs
      ['AS8-builtin-gate-unread-head-loop', 'na', `printf '\\145nable' > {OUT}/scratch/n; ${WROTE_ECHO}for i in 1 2; do echo; "$(< {OUT}/scratch/n)" -n echo; done`, ['bash'], ['text', BOUND]],   // a command name not read (THE UNHELD ROAD)
      ['AS8-builtin-gate-unread-trap', 'na', `printf '\\145nable' > {OUT}/scratch/n; ${WROTE_ECHO}trap echo EXIT; "$(< {OUT}/scratch/n)" -n echo`, ['bash'], ['text', BOUND]],
      ['AS8-builtin-gate-source-loop', 'na', `printf '\\145nable -n echo\\n' > {OUT}/scratch/e.sh; ${WROTE_ECHO}for i in 1 2; do echo; . {OUT}/scratch/e.sh; done`, ['bash'], ['text', BOUND]],   // a text not read, sourced
      // zsh's `disable` and `zmodload` and an eval's text (the seventh verify round's tg-m7-5); `zmodload -F zsh/rlimits -b:ulimit` turns ulimit off, run
      // then from PATH in zsh (measured: tg-r-probe-2.log), and ulimit has no program a remedy could name, so the row pins the gate's name on an echo
      ['AS8-builtin-gate-disable', 'na', `${WROTE_ECHO}disable echo; echo`, ['zsh'], ['text', BOUND]],
      ['AS8-builtin-gate-zmodload', 'na', `${WROTE_ECHO}zmodload zsh/rlimits; echo`, N, ['text', BOUND]],
      ['AS8-builtin-gate-eval-enable', 'na', `${WROTE_ECHO}eval 'enable -n echo'; echo`, ['bash'], ['text', BOUND]],
      // the gate's reading since R2 is THE ASSIGNING HEAD's: a command that may turn a builtin on or off may put a builtin under any name, so a mention under
      // a program taints there (mentionMayAssign), a cost on the restricted side on which no shell writes (beside AS8-cp-sed-path-ls, which passes with no
      // gate); by the scan before the walk, which reaches a gate after the mention (refused at the gate word itself, which has no program), by the walk's
      // own name where the scan does not read the spelling, and by a text not read run here that poisons no name (a `mapfile -C` callback); each row red
      // where its setter is off. The first two are fork main's own refusals; the callback leaves the directory unknown, where fork main skipped the
      // bound-name refusal and allowed the third (THE BOUND NAME survives an unknown directory since an audit of this change), as the change's head before
      // round 2 refused it too
      ['AS8-root-gate-scan', 'na', 'cp {OUT}/scratch/keep.md {OUT}/scratch/b.service; grep -c PATH {OUT}/scratch/b.service; enable -n echo; ls docs', N, ['text', [ANY_NAME, 'its command name names enable,', 'Make the change with track-edit instead']]],
      ['AS8-root-gate-unheld-callback', 'na', 'cp {OUT}/scratch/keep.md {OUT}/scratch/b.service; mapfile -C "$(cat {OUT}/scratch/keep.md)" -c 1 a < {OUT}/scratch/keep.md; grep -c PATH {OUT}/scratch/b.service; ls docs', N, ['text', [ANY_NAME, 'its command name names ls,']]],
      ['AS8-root-gate-walk-ansic', 'na', "cp {OUT}/scratch/keep.md {OUT}/scratch/b.service; $'\\x65nable' -n echo; grep -c PATH {OUT}/scratch/b.service; ls docs", N, ['text', [ANY_NAME, 'its command name names ls,']]],
      // D1 (an audit of fork PR 975's body, its gate behind a command named by a variable, a false allow this change introduced, 2026-10-05): a
      // command named by a variable that holds
      // `enable` turns bash's echo builtin off, and its unread head leaves the directory unknown, where the change had cleared THE BOUND NAME; the
      // refusal now survives the unknown directory, so the later bare `echo` runs the script written into place and is refused (bash alone enables so)
      ['AS8-builtin-gate-var-enable', 'na', `${WROTE_ECHO}read e <<< enable; $e -n echo; echo`, ['bash'], ['text', BOUND]],
      // the backup side file after a `cd "$d"` (the same audit, its backup-after-cd case, a false allow this change introduced): once the directory
      // was unknown the change cleared
      // both the backup refusal and the builtin exemption (since removed, R2), so the stash made under a name not followed ran; THE BOUND NAME now holds under an
      // unknown directory (bash and zsh stash a backup, dash does not)
      ['AS8-backup-after-cd', 'na', 'read d <<< .; read X <<< {OUT}/scratch; cp /usr/bin/cp {OUT}/scratch/x; cp -b -S zz /usr/bin/true {OUT}/scratch/x; PATH=$X:$PATH; cd "$d"; xzz {NA}/base/report.md {NA}/docs/report.md', BZ, ['text', ANY_NAME]],
      // THE BOUND NAME binds the file the writer makes (fork PR 975's round 1, C, 2026-10-05; the round's fresh-1): a cp, mv, install, ln or ln -s of a
      // program into a directory made DIR/<its name>, and only the directory was bound, so the program's name run through the PATH the command set passed
      // while bash, zsh and dash ran it, where fork main refused every bare name once a path was bound; that refusal is fork main's again (item 8 as
      // ruled), and the binding still serves where it does not reach: under a PATH the guard reads, the made file of the name is spliced and its copy
      // judged by name from any cwd (the readable rows: fork main allowed both while every shell wrote). A `-T` and a file destination are refused as
      // every bare name is, fork main's own refusal (the cost rows)
      ['AS8-into-dir-cp', 'na', 'cp {W}/tools/w2 {OUT}/scratch; PATH={OUT}/scratch:$PATH; w2', A, ['text', ANY_NAME]],
      ['AS8-into-dir-cp-made', 'na', 'mkdir -p {OUT}/scratch/bin; cp {W}/tools/w2 {OUT}/scratch/bin; PATH={OUT}/scratch/bin:$PATH; w2', A, ['text', ANY_NAME]],
      ['AS8-into-dir-install', 'na', 'install {W}/tools/w2 {OUT}/scratch; PATH={OUT}/scratch:$PATH; w2', A, ['text', ANY_NAME]],
      ['AS8-into-dir-ln', 'na', 'ln {W}/tools/w2 {OUT}/scratch; PATH={OUT}/scratch:$PATH; w2', A, ['text', ANY_NAME]],
      ['AS8-into-dir-ln-s', 'na', 'ln -s {W}/tools/w2 {OUT}/scratch; PATH={OUT}/scratch:$PATH; w2', A, ['text', ANY_NAME]],
      ['AS8-into-dir-mv', 'na', 'dd if={W}/tools/w2 of={OUT}/w2 status=none; chmod +x {OUT}/w2; mv {OUT}/w2 {OUT}/scratch; PATH={OUT}/scratch:$PATH; w2', A, ['text', ANY_NAME]],
      ['AS8-cost-into-dir-T', 'na', 'cp -T {W}/tools/w2 {OUT}/scratch/w5; PATH={OUT}/scratch:$PATH; w2', N, ['text', ANY_NAME]],
      ['AS8-into-dir-readable-path', 'na', 'cp /usr/bin/cp {OUT}/c2; cp {OUT}/c2 {OUT}/scratch; PATH={OUT}/scratch:/usr/bin:/bin; c2 {NA}/base/report.md {NA}/docs/report.md', A, 'name', 'name'],
      ['AS8-cost-into-file', 'na', 'cp {W}/tools/w2 {OUT}/scratch/keep.md; PATH={OUT}/scratch:$PATH; w2', N, ['text', ANY_NAME]],
      // a file made by a program the walk does not read or by one whose output name it does not hold (rsync and curl, and the reviewer's uniq, gunzip,
      // split, `shuf -o` and dd: each wrote the script the name ran, which bash, zsh and dash ran onto the tracked report while the narrowing to a made
      // name allowed it at fork PR 975's head before this round, and THE JUDGED PROGRAMS' list missed five of them in the pass before), a copy of a source the guard does not read
      // into a directory and a one-operand link of one: refused as every bare name under the unreadable PATH is, fork main's rule, with no list of
      // programs. A one-operand `ln`/`ln -s` makes ./basename(SRC), bound (closing shell F2), which serves a PATH the guard reads (the readable row);
      // its twin naming another program is refused, a cost fork main does not have: fork main bound nothing for one operand and allowed the name, as it
      // allowed the one-operand link's own name while every shell ran it. The control runs the copied program by its full path, the one remedy
      ['AS8-made-rsync', 'na', 'cp /usr/bin/cp {OUT}/scratch/c2; rsync {W}/tools/w2 {OUT}/scratch/w3; PATH={OUT}/scratch:$PATH; w3', A, ['text', ANY_NAME]],
      ['AS8-made-curl', 'na', 'cp /usr/bin/cp {OUT}/scratch/c2; curl -s -o {OUT}/scratch/w3 file://{W}/tools/w2; chmod +x {OUT}/scratch/w3; PATH={OUT}/scratch:$PATH; w3', A, ['text', ANY_NAME]],
      ['AS8-ctl-made-rsync-fullpath', 'na', 'cp /usr/bin/cp {OUT}/scratch/c2; rsync {W}/tools/w2 {OUT}/scratch/w3; PATH={OUT}/scratch:$PATH; /usr/bin/cp base/report.md docs/other.md', N, 'allow'],
      ['AS8-made-one-op-ln-s', 'nas', 'cp /usr/bin/cp {OUT}/scratch/c2; ln -s {W}/tools/w2; PATH={NA}/scratch:$PATH; w2', A, ['text', ANY_NAME]],
      ['AS8-made-one-op-ln', 'nas', 'cp /usr/bin/cp {OUT}/scratch/c2; ln {W}/tools/w2; PATH={NA}/scratch:$PATH; w2', A, ['text', ANY_NAME]],
      ['AS8-made-uniq', 'na', 'cp /usr/bin/cp {OUT}/scratch/c2; uniq {W}/tools/w2 {OUT}/scratch/w3; chmod +x {OUT}/scratch/w3; PATH={OUT}/scratch:$PATH; w3', A, ['text', ANY_NAME]],
      ['AS8-made-gunzip', 'na', 'cp /usr/bin/cp {OUT}/scratch/c2; gzip -c {W}/tools/w2 > {OUT}/scratch/w3.gz; gunzip {OUT}/scratch/w3.gz; chmod +x {OUT}/scratch/w3; PATH={OUT}/scratch:$PATH; w3', A, ['text', ANY_NAME]],
      ['AS8-made-split', 'na', 'cp /usr/bin/cp {OUT}/scratch/c2; split -n 1 {W}/tools/w2 {OUT}/scratch/w3; chmod +x {OUT}/scratch/w3aa; PATH={OUT}/scratch:$PATH; w3aa', A, ['text', ANY_NAME]],
      ['AS8-made-shuf-o', 'na', 'cp /usr/bin/cp {OUT}/scratch/c2; shuf -n 9 -o {OUT}/scratch/w3 {W}/tools/w2; chmod +x {OUT}/scratch/w3; PATH={OUT}/scratch:$PATH; w3', A, ['text', ANY_NAME]],
      ['AS8-made-dd', 'na', 'cp /usr/bin/cp {OUT}/scratch/c2; dd if={W}/tools/w2 of={OUT}/scratch/w3 status=none; chmod +x {OUT}/scratch/w3; PATH={OUT}/scratch:$PATH; w3', A, ['text', ANY_NAME]],
      ['AS8-made-busybox-cp', 'na', 'cp /usr/bin/cp {OUT}/scratch/c2; busybox cp {W}/tools/w2 {OUT}/scratch/w3; PATH={OUT}/scratch:$PATH; w3', A, ['text', ANY_NAME]],   // NOT RUN by name where busybox is absent (NAMED_PROGRAMS)
      ['AS8-made-nonlit-into-dir', 'na', 'read S <<< {W}/tools/w2; cp "$S" {OUT}/scratch; PATH={OUT}/scratch:$PATH; w2', BZ, ['text', ANY_NAME]],
      ['AS8-made-one-op-ln-s-nonlit', 'nas', 'cp /usr/bin/cp {OUT}/scratch/c2; read S <<< {W}/tools/w2; ln -s "$S"; PATH={NA}/scratch:$PATH; w2', BZ, ['text', ANY_NAME]],
      ['AS8-made-one-op-ln-readable-path', 'na', 'cp /usr/bin/cp {OUT}/c2; cd {OUT}/scratch; ln -s {OUT}/c2; PATH={OUT}/scratch:/usr/bin:/bin; c2 {NA}/base/report.md {NA}/docs/report.md', A, 'name', 'name'],
      ['AS8-cost-one-op-ln-s-other-name', 'nas', 'ln -s {W}/tools/w2; PATH={NA}/scratch:$PATH; cat {NA}/docs/report.md', N, ['text', ANY_NAME]],
      ['AS8-made-one-op-ln-s-alone', 'nas', 'ln -s {W}/tools/w2; PATH={NA}/scratch:$PATH; w2', A, ['text', ANY_NAME]],   // the link's own name, which fork main allowed (it bound nothing for one operand) while every shell ran it
      // RULE B (fork PR 975's round 2, R3, 2026-10-06; the round's tests-1, extra4-1, tests-2, correctness-4): one bind helper (bindWrite) serves every
      // writer of the bound map; keys and values are absolute paths resolved at the write (a symbolic link's target against the link's own directory), and
      // a key keeps EVERY value it was given (monotonic), so a later bare name refuses when any binding of it is a writer this command made. Ruling C stored
      // the source as SPELLED, so a relative or a bare source (`c2x`, `zc`) was read as a command name, not the file copied, and a PATH the guard reads let
      // the bare name run the copy; and `ln -s SRC DIR` bound the link's target to itself, overwriting the copy's binding. Each row refused here by name,
      // allowed at the pre-round head, bash, zsh and dash writing the tracked report. extra4-1 (a relative bound source plus the mention ROOT keeps readable,
      // base refuses on the tainted PATH): cp, mv, hard ln, install, a `cat >` and a file destination, from na and from a cwd in no project
      ['AS8-ruleB-extra4-cp', 'na', 'cp /usr/bin/cp zc; cp zc scratch; grep -q PATH base/report.md; PATH={NA}/scratch:/usr/bin:/bin; zc base/report.md docs/report.md', A, 'name'],
      ['AS8-ruleB-extra4-mv', 'na', 'cp /usr/bin/cp zc; mv zc scratch; grep -q PATH base/report.md; PATH={NA}/scratch:/usr/bin:/bin; zc base/report.md docs/report.md', A, 'name'],
      ['AS8-ruleB-extra4-ln', 'na', 'cp /usr/bin/cp zc; ln zc scratch; grep -q PATH base/report.md; PATH={NA}/scratch:/usr/bin:/bin; zc base/report.md docs/report.md', A, 'name'],
      ['AS8-ruleB-extra4-install', 'na', 'cp /usr/bin/cp zc; install zc scratch; grep -q PATH base/report.md; PATH={NA}/scratch:/usr/bin:/bin; zc base/report.md docs/report.md', A, 'name'],
      ['AS8-ruleB-extra4-catredir', 'na', 'cp /usr/bin/cp zc; cat zc > scratch/zc; chmod +x scratch/zc; grep -q PATH base/report.md; PATH={NA}/scratch:/usr/bin:/bin; zc base/report.md docs/report.md', A, 'name'],
      ['AS8-ruleB-extra4-filedst', 'na', 'cp /usr/bin/cp zc; cp zc scratch/zc; grep -q PATH base/report.md; PATH={NA}/scratch:/usr/bin:/bin; zc base/report.md docs/report.md', A, 'name'],
      ['AS8-ruleB-extra4-out', 'out', 'cp /usr/bin/cp zc; cp zc scratch; grep -q PATH {NA}/base/report.md; PATH={OUT}/scratch:/usr/bin:/bin; zc {NA}/base/report.md {NA}/docs/report.md', A, 'name', 'name'],
      // tests-2 (a bare or relative source stored by spelling, no mention, base allows too): cp, mv, install and `cp -t` into a directory under a readable PATH
      ['AS8-ruleB-tests2-cp', 'na', 'cp /usr/bin/cp c2x; cp c2x {OUT}/scratch; PATH={OUT}/scratch:/usr/bin:/bin; c2x {NA}/base/report.md {NA}/docs/report.md', A, 'name', 'name'],
      ['AS8-ruleB-tests2-mv', 'na', 'cp /usr/bin/cp c2x; mv c2x {OUT}/scratch; PATH={OUT}/scratch:/usr/bin:/bin; c2x {NA}/base/report.md {NA}/docs/report.md', A, 'name', 'name'],
      ['AS8-ruleB-tests2-install', 'na', 'cp /usr/bin/cp c2x; install c2x {OUT}/scratch; PATH={OUT}/scratch:/usr/bin:/bin; c2x {NA}/base/report.md {NA}/docs/report.md', A, 'name', 'name'],
      ['AS8-ruleB-tests2-cpt', 'na', 'cp /usr/bin/cp c2x; cp -t {OUT}/scratch c2x; PATH={OUT}/scratch:/usr/bin:/bin; c2x {NA}/base/report.md {NA}/docs/report.md', A, 'name', 'name'],
      // tests-1 (ln -s under a readable PATH: literalPath followed the link this command made and bound its target to itself; base refuses the two-operand
      // and relative-target forms, allows the -t form): the two-operand, a relative target, and the -t form
      ['AS8-ruleB-tests1-lns-two', 'na', 'cp /usr/bin/cp {OUT}/c2; ln -s {OUT}/c2 {OUT}/scratch; PATH={OUT}/scratch:/usr/bin:/bin; c2 {NA}/base/report.md {NA}/docs/report.md', A, 'name', 'name'],
      ['AS8-ruleB-tests1-lns-relsrc', 'out', 'cd {OUT}; cp /usr/bin/cp c2; ln -s ../c2 scratch; PATH={OUT}/scratch:/usr/bin:/bin; c2 {NA}/base/report.md {NA}/docs/report.md', A, 'name', 'name'],
      ['AS8-ruleB-tests1-lns-t', 'na', 'cp /usr/bin/cp {OUT}/c2; ln -s -t {OUT}/scratch {OUT}/c2; PATH={OUT}/scratch:/usr/bin:/bin; c2 {NA}/base/report.md {NA}/docs/report.md', A, 'name', 'name'],
      // correctness-4 (the existing-directory ln -s of a bound source, a false allow this PR introduced, and an empty PATH entry read as the cwd)
      ['AS8-ruleB-corr4-lns-existdir', 'na', 'mkdir -p {OUT}/d; cp /usr/bin/cp {OUT}/c2; ln -s {OUT}/c2 {OUT}/d; PATH={OUT}/d:/usr/bin:/bin; c2 {NA}/base/report.md {NA}/docs/report.md', A, 'name', 'name'],
      ['AS8-ruleB-corr4-empty-path', 'na', 'cp /usr/bin/cp {OUT}/scratch/c2; cd {OUT}/scratch; PATH=:/usr/bin:/bin; c2 {NA}/base/report.md {NA}/docs/report.md', A, 'name', 'name'],
      // DISCLOSED, PRE-EXISTING (base, head and rule B all allow; decision 47): writers rule B's binding model does not reach under a readable PATH, each
      // allowed while bash, zsh and dash write: a `cp -r` directory copy (only the top directory is bound), a `dd of=` and a `tee` writer, and a failed
      // `ln -s` onto an existing name. The relative-symlink move and `cp -a` copy class, whose text re-resolves against the new directory, is a residual
      // named in decision 47 (its write-through shape is not reproduced as a committed row)
      ['AS8-residual-ruleB-cp-r-dir', 'na', 'mkdir -p {OUT}/d; cp /usr/bin/cp {OUT}/d/zc; cp -r {OUT}/d {OUT}/scratch/d2; PATH={OUT}/scratch/d2:/usr/bin:/bin; zc {NA}/base/report.md {NA}/docs/report.md', A, 'allow'],
      ['AS8-residual-ruleB-dd', 'na', 'cp /usr/bin/cp zc; dd if=zc of={OUT}/scratch/zc2 status=none; chmod +x {OUT}/scratch/zc2; PATH={OUT}/scratch:/usr/bin:/bin; zc2 {NA}/base/report.md {NA}/docs/report.md', A, 'allow'],
      ['AS8-residual-ruleB-tee', 'na', 'cp /usr/bin/cp zc; tee {OUT}/scratch/zc2 < zc > /dev/null; chmod +x {OUT}/scratch/zc2; PATH={OUT}/scratch:/usr/bin:/bin; zc2 {NA}/base/report.md {NA}/docs/report.md', A, 'allow'],
      ['AS8-residual-ruleB-failed-lns-exist', 'na', 'cp /usr/bin/cp {OUT}/scratch/c2; ln -s /usr/bin/true {OUT}/scratch/c2; PATH={OUT}/scratch:/usr/bin:/bin; c2 {NA}/base/report.md {NA}/docs/report.md', A, 'allow'],
      // a file this command writes another way than by a copy, a move or a link (a printf redirection, a tee), whose name passed under a PATH the guard
      // does not read while every shell ran it (the reviewer's (b), F-a's unbound writers): refused as every bare name is once a path is bound; such a
      // file is never spliced (a printf'd script copied on with `cat` and run under a builtin's name stays the builtin's: AS8-builtin-noenable-script)
      ['AS8-made-printf', 'na', "cp /usr/bin/cp {OUT}/scratch/c2; printf 'cp base/report.md docs/report.md\\n' > {OUT}/scratch/w4; chmod +x {OUT}/scratch/w4; PATH={OUT}/scratch:$PATH; w4", A, ['text', ANY_NAME]],
      ['AS8-made-tee', 'na', "cp /usr/bin/cp {OUT}/scratch/c2; printf 'cp base/report.md docs/report.md\\n' | tee {OUT}/scratch/w4 > /dev/null; chmod +x {OUT}/scratch/w4; PATH={OUT}/scratch:$PATH; w4", A, ['text', ANY_NAME]],
      // THE SOURCED NAME (the reviewer's (b), S1): `.` and `source` look a name with no slash up through PATH, so a file this command wrote under that name
      // may be what they read, and the builtin `.` had passed it while bash and zsh sourced the script (dash parses no `<<<`); refused for every name, as a
      // bare command name is, with no remedy. Since fork PR 975's round 2 (R2) `.` is itself a bare name refused under that PATH, as at fork main, so the
      // refusal names `.` first, piped or not (the operand's refusal stands behind it)
      ['AS8-sourced-dot', 'na', `${WROTE_ECHO}. echo`, BZ, ['text', [ANY_NAME, 'its command name names .', 'Make the change with track-edit instead']]],
      ['AS8-sourced-dot-piped', 'na', `${WROTE_ECHO}. echo | cat`, BZ, ['text', [ANY_NAME, 'its command name names .', 'Make the change with track-edit instead']]],
      ['AS8-sourced-source', 'na', `${WROTE_ECHO}source echo`, BZ, ['text', [ANY_NAME, 'its command name names source']]],   // `source` is no builtin of dash, which looks it up through PATH, so the head itself refuses first, as at fork main
      // after a copy and a backup, a builtin's name behind `command`, `builtin`, `time` or `exec`, behind a precommand word that takes an option (`command
      // -p`, `time -p`, `exec -a NAME`) and behind zsh's modifiers `noglob`, `nocorrect` and `-`: refused, with no remedy, since no program stands for
      // cd, export or ulimit. These rows pinned THE WRAPPER DROPPED's remedy (the reviewer's M2 gap and t8-4), which asked for the wrapper words dropped
      // so the shell would run its own name; since fork PR 975's round 2 (R2) that name is refused too, so the remedy is gone and each row holds that no
      // refusal names it (the third element). The no-remedy form (M2, the reviewer's t8-10) behind an external `env` or after a gate the scan sees, as before
      ...['cd {OUT}', 'export Y=1', 'ulimit -n'].flatMap((c) => ['command', 'builtin', 'time', 'exec'].map((wr) => [`AS8-drop-${wr}-${c.split(' ')[0]}`, 'na', `${BACKED_X}${wr} ${c}`, N, ['text', [ANY_NAME, `its command name names ${c.split(' ')[0]},`, 'Make the change with track-edit instead'], ['Run `', 'Spell the command by the full path']]])),
      ...[['command-p', 'command -p'], ['time-p', 'time -p'], ['exec-a', 'exec -a q'], ['noglob', 'noglob'], ['nocorrect', 'nocorrect'], ['dash', '-']].map(([id, wr]) => [`AS8-drop-${id}-cd`, 'na', `${BACKED_X}${wr} cd {OUT}`, N, ['text', [ANY_NAME, 'its command name names cd,', 'Make the change with track-edit instead'], ['Run `', 'Spell the command by the full path']]]),
      ['AS8-drop-noremedy-env-cd', 'na', `${BACKED_X}env cd {OUT}`, N, ['text', [ANY_NAME, 'Make the change with track-edit instead'], ['Run `', 'Spell the command by the full path', 'full-path']]],
      ['AS8-drop-noremedy-gate-cd', 'na', `${BACKED_X}/usr/bin/true enable; cd {OUT}`, N, ['text', [ANY_NAME, 'Make the change with track-edit instead'], ['Run `', 'Spell the command by the full path']]],
      // a mention of a gate no shell runs: the exemption it turned off is gone (R2), so the bare echo is refused as every bare name is, a stated cost
      ['AS8-builtin-gate-mention-cost', 'na', `${BACKED_X}echo enable`, N, ['text', ANY_NAME]],
      // a name a wrapper runs is the wrapper's lookup, never the shell's own (the seventh verify round's tg-m7-4: `exec echo` ran the stash in bash,
      // `command echo` in zsh), whatever spells the wrapper: by a path, which names no lookup (`/usr/bin/env echo` and `/usr/bin/nohup echo` ran it in
      // bash and zsh while allowed before this round), or a copy of it the command made
      // (since fork PR 975's round 2, R2, the wrapper itself is refused as a bare name too: `exec` and `command` have no program, so the refusal of echo
      // names no remedy, the full path for echo leaving them refused; and in `exec command ..` the refusal names `exec`, the first word, where it had named
      // `command` while `exec` passed as the shell's own)
      ['AS8-builtin-exec-echo', 'na', `${STASHED_ECHO}exec echo base/report.md docs/report.md`, ['bash'], ['text', [ANY_NAME, 'its command name names echo,', 'Make the change with track-edit instead'], ['Run `', 'Spell the command by the full path']]],
      ['AS8-builtin-command-echo', 'na', `${STASHED_ECHO}command echo base/report.md docs/report.md`, ['zsh'], ['text', [ANY_NAME, 'its command name names echo,', 'Make the change with track-edit instead'], ['Run `', 'Spell the command by the full path']]],
      ['AS8-builtin-exec-command', 'na', 'read X <<< {OUT}/scratch; cp /usr/bin/cp {OUT}/scratch/comm; cp -b -S and /usr/bin/true {OUT}/scratch/comm; PATH=$X:$PATH; exec command base/report.md docs/report.md', ['bash'], ['text', [ANY_NAME, 'its command name names exec,', 'Make the change with track-edit instead'], ['Run `', 'Spell the command by the full path']]],   // bash's exec looks `command` up through PATH and runs the stash
      ['AS8-builtin-slash-env-echo', 'na', `${STASHED_ECHO}/usr/bin/env echo base/report.md docs/report.md`, BZ, ['text', ANY_NAME]],
      ['AS8-builtin-slash-nohup-echo', 'na', `${STASHED_ECHO}/usr/bin/nohup echo base/report.md docs/report.md`, BZ, ['text', ANY_NAME]],
      ['AS8-builtin-bound-env-echo', 'na', `cp /usr/bin/env {OUT}/scratch/e2; ${STASHED_ECHO}{OUT}/scratch/e2 echo base/report.md docs/report.md`, BZ, ['text', ANY_NAME]],
      // a quoted keyword is no keyword: the shells look `'if'`, `"while"` up through PATH and ran the stash (bash and zsh, allowed before this round);
      // a quoted builtin takes the restricted side with it, a stated cost
      ['AS8-builtin-quoted-if', 'na', "read X <<< {OUT}/scratch; cp /usr/bin/cp {OUT}/scratch/i; cp -b -S f /usr/bin/true {OUT}/scratch/i; PATH=$X:$PATH; 'if' base/report.md docs/report.md", BZ, ['text', ANY_NAME]],
      ['AS8-builtin-quoted-while', 'na', "read X <<< {OUT}/scratch; cp /usr/bin/cp {OUT}/scratch/wh; cp -b -S ile /usr/bin/true {OUT}/scratch/wh; PATH=$X:$PATH; \"while\" base/report.md docs/report.md", BZ, ['text', ANY_NAME]],
      ['AS8-builtin-partquoted-for', 'na', "read X <<< {OUT}/scratch; cp /usr/bin/cp {OUT}/scratch/f; cp -b -S or /usr/bin/true {OUT}/scratch/f; PATH=$X:$PATH; f'or' base/report.md docs/report.md", BZ, ['text', ANY_NAME]],   // a quote anywhere in the name, not only at its start (the reading the reserved-word peel keeps: AS8-residual-partquoted-keyword)
      ['AS8-builtin-quoted-echo-cost', 'na', `${STASHED_ECHO}'echo' base/report.md docs/report.md`, N, ['text', ANY_NAME]],
      // DISCLOSED (M3's stopping rule): a reserved word spelled partly quoted (`i'f'`) is read as the keyword, at fork main as here, while the shells
      // look it up through PATH and ran the copy; a follow-up, named in decision 47
      ['AS8-residual-partquoted-keyword', 'na', "read X <<< {OUT}/scratch; cp /usr/bin/cp {OUT}/scratch/i; cp -b -S f /usr/bin/true {OUT}/scratch/i; PATH=$X:$PATH; i'f' base/report.md docs/report.md", BZ, 'allow'],
      // `builtin` is no command of dash, which looks it up through PATH (the seventh verify round's tg-t7-1: a backup stashed sh as `builtin`, and dash ran
      // the piped and the redirected script through it while allowed before this round)
      ['AS8-builtin-dash-builtin-stdin', 'nad', "cp /bin/sh {OUT}/scratch/built; cp -b -S in /usr/bin/true {OUT}/scratch/built; PATH={OUT}/scratch:$PATH; echo 'cp ../base/report.md report.md' | builtin", ['dash'], ['text', ANY_NAME]],
      ['AS8-builtin-dash-builtin-file', 'nad', "printf 'cp ../base/report.md report.md\\n' > {OUT}/scratch/cmds; cp /bin/sh {OUT}/scratch/built; cp -b -S in /usr/bin/true {OUT}/scratch/built; PATH={OUT}/scratch:$PATH; builtin < {OUT}/scratch/cmds", ['dash'], ['text', ANY_NAME]],
      // fork PR 975's round 2, R2 (fresh-2): a builtin's name the command shadows with a function or an alias through a table write the guard does not
      // read (zsh's `printf -v`, `read -r` and `${..::=..}` into `functions`, bash's `BASH_ALIASES` under POSIX mode, which expands aliases in `-c`, on
      // a line of its own since bash expands an alias only on a later line) runs the shadow, here a copy onto the tracked report; THE SHELL'S OWN NAME
      // let the name pass after a copy and an unread PATH, where fork main refused every bare name, so each was allowed at the change's head while the
      // shell wrote, and each is refused again now, the name itself the refusal
      ['AS8-builtin-shadow-zsh-printf-v', 'na', `printf -v 'functions[echo]' '/usr/bin/cp "$@"'; read X <<< {OUT}/scratch; cp /usr/bin/cp {OUT}/scratch/c2; PATH=$PATH:$X; echo base/report.md docs/report.md`, ['zsh'], ['text', [ANY_NAME, 'its command name names echo,']]],
      ['AS8-builtin-shadow-zsh-read-r', 'na', `read -r 'functions[echo]' <<< '/usr/bin/cp "$@"'; read X <<< {OUT}/scratch; cp /usr/bin/cp {OUT}/scratch/c2; PATH=$PATH:$X; echo base/report.md docs/report.md`, ['zsh'], ['text', [ANY_NAME, 'its command name names echo,']]],
      ['AS8-builtin-shadow-zsh-assign-expansion', 'na', `: \${functions[echo]::='/usr/bin/cp "$@"'}; read X <<< {OUT}/scratch; cp /usr/bin/cp {OUT}/scratch/c2; PATH=$PATH:$X; echo base/report.md docs/report.md`, ['zsh'], ['text', [ANY_NAME, 'its command name names echo,']]],
      ['AS8-builtin-shadow-zsh-cd', 'na', `printf -v 'functions[cd]' '/usr/bin/cp "$@"'; read X <<< {OUT}/scratch; cp /usr/bin/cp {OUT}/scratch/c2; PATH=$PATH:$X; cd base/report.md docs/report.md`, ['zsh'], ['text', [ANY_NAME, 'its command name names cd,', 'Make the change with track-edit instead']]],
      ['AS8-builtin-shadow-bash-aliases', 'na', 'POSIXLY_CORRECT=1\nBASH_ALIASES[echo]=/usr/bin/cp\nread X <<< {OUT}/scratch; cp /usr/bin/cp {OUT}/scratch/c2; PATH=$PATH:$X\necho base/report.md docs/report.md', ['bash'], ['text', [ANY_NAME, 'its command name names echo,']]],
      ['AS8-builtin-shadow-bash-printf-v', 'na', "POSIXLY_CORRECT=1\nprintf -v 'BASH_ALIASES[echo]' /usr/bin/cp\nread X <<< {OUT}/scratch; cp /usr/bin/cp {OUT}/scratch/c2; PATH=$PATH:$X\necho base/report.md docs/report.md", ['bash'], ['text', [ANY_NAME, 'its command name names echo,']]],
      // M3, pre-existing (fork main allows each, as this change does, while the shell writes; named in decision 47): the same table writes where no copy
      // and no unread PATH put the bound-name refusal in play, or from a cwd in no project; the guard reads `echo` as the builtin it shadowed, and the
      // follow-up reads a write to a function or alias table as a definition it does not read, refusing every later use of the name
      ['AS8-residual-shadow-zsh-nopath', 'na', `printf -v 'functions[echo]' '/usr/bin/cp "$@"'; echo base/report.md docs/report.md`, ['zsh'], 'allow'],
      ['AS8-residual-shadow-zsh-nocopy', 'na', `printf -v 'functions[echo]' '/usr/bin/cp "$@"'; read X <<< {OUT}/scratch; PATH=$PATH:$X; echo base/report.md docs/report.md`, ['zsh'], 'allow'],
      ['AS8-residual-shadow-bash-nopath', 'na', 'POSIXLY_CORRECT=1\nBASH_ALIASES[echo]=/usr/bin/cp\necho base/report.md docs/report.md', ['bash'], 'allow'],
      ['AS8-residual-shadow-zsh-out', 'out', `printf -v 'functions[echo]' '/usr/bin/cp "$@"'; read X <<< {OUT}/scratch; cp /usr/bin/cp {OUT}/scratch/c2; PATH=$PATH:$X; echo {NA}/base/report.md {NA}/docs/report.md`, ['zsh'], 'allow', null],
      // fork PR 975's round 2, R2 (correctness-3): dash looks echo, printf and test up through PATH before a `%builtin` entry, so under an unread PATH that
      // holds a directory and then `%builtin` a script written into place under the name runs (the script names cp by its full path, since a script that
      // ran echo or printf under that PATH would run itself); THE SHELL'S OWN NAME let the name pass, where fork main refused it, and each is refused
      // again now; reachable from bash and zsh through `dash -c` (every outer shell writes). From a cwd in no project the bound-name refusal is not in play
      // and the script run is no text the guard reads, so it passes at fork main as here (a witness, named in decision 47)
      ...[['echo', 'echo x'], ['printf', 'printf x'], ['test', 'test -n x']].map(([n, call]) => [`AS8-builtin-dash-pctbuiltin-${n}`, 'na', `printf '/usr/bin/cp {NA}/base/report.md {NA}/docs/report.md\\n' > {OUT}/s.sh; cat {OUT}/s.sh > {OUT}/scratch/${n}; chmod +x {OUT}/scratch/${n}; printf '%s\\n' {OUT}/scratch > {OUT}/p; read X < {OUT}/p; PATH=$X:%builtin:$PATH; ${call}`, ['dash'], ['text', [ANY_NAME, `its command name names ${n},`]], null]),
      ['AS8-builtin-dash-pctbuiltin-dash-c', 'na', "printf '/usr/bin/cp {NA}/base/report.md {NA}/docs/report.md\\n' > {OUT}/s.sh; cat {OUT}/s.sh > {OUT}/scratch/echo; chmod +x {OUT}/scratch/echo; printf '%s\\n' {OUT}/scratch > {OUT}/p; dash -c 'read X < {OUT}/p; PATH=$X:%builtin:$PATH; echo x'", A, ['text', [ANY_NAME, 'its command name names echo,']], null],
      ['AS8-residual-dash-pctbuiltin-echo-out', 'out', "printf '/usr/bin/cp {NA}/base/report.md {NA}/docs/report.md\\n' > {OUT}/s.sh; cat {OUT}/s.sh > {OUT}/scratch/echo; chmod +x {OUT}/scratch/echo; printf '%s\\n' {OUT}/scratch > {OUT}/p; read X < {OUT}/p; PATH=$X:%builtin:$PATH; echo x", ['dash'], 'allow', null],
      // M3, pre-existing (fork PR 975's round 2, correctness-3's `[`; fork main allows each, as this change does, while dash writes; a witness row each,
      // named in decision 47): dash looks `[` up through PATH before `%builtin` too, and the bare-name lookup does not search `[` at all, on the premise
      // that it is a builtin in every shell, so a script written into place as `[`, or a copy of cp made under that name, runs from a directory ahead of
      // `%builtin` while allowed from a tracked cwd and from one in no project; reachable from bash through `dash -c` (zsh stops at the unquoted `[` of
      // the file's path, a pattern it cannot match, and makes no file). The follow-up reads `[` as the name dash looks up, as it reads test
      ['AS8-residual-dash-pctbuiltin-bracket', 'na', "printf '/usr/bin/cp {NA}/base/report.md {NA}/docs/report.md\\n' > {OUT}/s.sh; cat {OUT}/s.sh > {OUT}/scratch/[; chmod +x {OUT}/scratch/[; PATH={OUT}/scratch:%builtin:$PATH; [ x ]", ['dash'], 'allow'],
      ['AS8-residual-dash-pctbuiltin-bracket-dash-c', 'na', "printf '/usr/bin/cp {NA}/base/report.md {NA}/docs/report.md\\n' > {OUT}/s.sh; cat {OUT}/s.sh > {OUT}/scratch/[; chmod +x {OUT}/scratch/[; dash -c 'PATH={OUT}/scratch:%builtin:$PATH; [ x ]'", ['bash', 'dash'], 'allow'],
      ['AS8-residual-dash-pctbuiltin-bracket-copy', 'na', 'cp /usr/bin/cp {OUT}/scratch/[; PATH={OUT}/scratch:%builtin:$PATH; [ {NA}/base/report.md {NA}/docs/report.md', ['dash'], 'allow'],
    );
    // item 8, the session's second case: a target holding a variable the guard cannot read (a substitution's value) is refused, naming the ONE
    // remedy that always lifts it, the path spelled out as an absolute path (M2: the literal-value clause the rounds before offered, which did not
    // lift where a later construct blocked the read, is gone, and no row carries it, NO_CURE); a cd elsewhere does not lift it, since the
    // session's directory decides the project in play; a variable with a literal value outside every project passes, one into a tracked file or
    // folder is refused by name. The rows that pinned where the clause was offered or withheld (an operator form, a name given its value after
    // \`&&\`, a loop variable or PWD, a name another command fills, a value with a space, a name after an eval, a source or a function call, a target
    // holding no variable, a literal value added after the substitution) now pin the one remedy alone
    rows.push(
      ['AS8-target-unprovable', 'na', 'T=$(mktemp -d {OUT}/build-XXXXXX); echo x > "$T/t.sh"', N, ['text', REMEDY_ABS, ['cd to', ...NO_CURE]]],
      ['AS8-target-unprovable-cd-out', 'na', 'cd {OUT}; T=$(mktemp -d {OUT}/build-XXXXXX); echo x > "$T/t.sh"', N, ['text', REMEDY_ABS, ['cd to', ...NO_CURE]]],
      ['AS8-target-slug', 'na', 'slug=a/b; echo x > "{OUT}/${slug//\\//__}.txt"', N, ['text', REMEDY_ABS, NO_CURE]],
      ['AS8-target-operator-cure', 'na', 'T=$(mktemp -d {OUT}/build-XXXXXX); echo x > "${T:-x}/t.sh"', N, ['text', REMEDY_ABS, NO_CURE]],
      ['AS8-target-operator-head', 'na', 'read c <<< true; "$c" x; T={OUT}/t; echo x > "${T%/}/t.sh"', N, ['text', REMEDY_ABS, NO_CURE]],
      ['AS8-target-add-after', 'na', 'T=$(mktemp -d {OUT}/build-XXXXXX); T={OUT}/build-out; mkdir -p "$T"; echo x > "$T/t.sh"', N, ['text', REMEDY_ABS, NO_CURE]],
      ['AS8-target-space', 'na', "T='{OUT}/my dir'; echo x > \"$T/t.sh\"", N, ['text', REMEDY_ABS, NO_CURE]],
      ['AS8-target-printf-v', 'na', "printf -v T '%s' {OUT}/b; echo x > \"$T/t.sh\"", N, ['text', REMEDY_ABS, NO_CURE]],
      ['AS8-target-inner-read', 'na', 'read T <<< {OUT}/b; echo "$(echo x > "$T/t.sh")"', N, ['text', REMEDY_ABS, NO_CURE]],
      ['AS8-target-inner-head', 'na', 'read c <<< true; "$c" x; T={OUT}/b; echo "$(echo x > "$T/t.sh")"', N, ['text', REMEDY_ABS, NO_CURE]],
      ['AS8-target-read', 'na', 'read T <<< {OUT}/build-out; echo x > "$T/t.sh"', N, ['text', REMEDY_ABS, NO_CURE]],
      ['AS8-target-unset', 'na', 'echo x > "$T/t.sh"', N, ['text', REMEDY_ABS, NO_CURE]],
      ['AS8-target-no-variable', 'na', 'echo x > "$(mktemp -d {OUT}/build-XXXXXX)/t.sh"', N, ['text', REMEDY_ABS, NO_CURE]],
      ['AS8-target-and', 'na', 'true && T={OUT}/build-out; echo x > "$T/t.sh"', N, ['text', ['through a command after `&&`', REMEDY_ABS], NO_CURE]],
      ['AS8-target-loop', 'na', 'for f in a b; do echo x > "$f.txt"; done', N, ['text', ['through a `for` loop variable', REMEDY_ABS], NO_CURE]],
      ['AS8-target-pwd', 'na', 'PWD={OUT}; cp x $PWD/docs/report.md', N, ['text', ['the command names PWD outside an expansion', REMEDY_ABS], NO_CURE]],
      ['AS8-target-eval', 'na', 'eval "$E"; T={OUT}/build-out; echo x > "$T/t.sh"', N, ['text', ['an earlier `eval` may assign any name', REMEDY_ABS], NO_CURE]],
      ['AS8-target-func', 'na', 'f() { :; }; f; T={OUT}/build-out; echo x > "$T/t.sh"', N, ['text', ['a function the command defines, may assign any name', REMEDY_ABS], NO_CURE]],
      ['AS8-target-read-then-source', 'na', `read T <<< {OUT}/build-out; source ${ENV}; echo x > "$T/t.sh"`, N, ['text', REMEDY_ABS, NO_CURE]], // a literal value in place of the read is not read after the source either
      ['AS8-target-outside', 'na', 'T={OUT}/build-out; mkdir -p "$T"; echo x > "$T/t.sh"', N, 'allow'],
      ['AS8-remedy-abs', 'na', 'mkdir -p {OUT}/build-out; echo x > {OUT}/build-out/t.sh', N, 'allow'],   // the not-literal refusal's one remedy followed, the path spelled absolute (the census below builds such a twin for every refused row)
      ['AS8-target-tracked-folder', 'na', 'T={NA}/notes; echo x > "$T/n2.md"', A, 'name', 'name'],
      ['AS8-target-tracked-file', 'na', 'T={NA}/docs; echo x > "$T/report.md"', A, 'name', 'name'],
      // the third verify round's rows for the clause's conditions (T3-1, T3-2, T3-3 and T2-2's four text conditions, M3-6): under M2 no refusal
      // carries a clause, so each pins the one remedy alone; the allowed controls beside them (a command named by its literal path, a backgrounded
      // command, two literal values) are commands the guard reads, not remedies the refusal offers
      ['AS8-target-read-and', 'na', 'true && read T <<< {OUT}/b; echo x > "$T/t.sh"', N, ['text', REMEDY_ABS, NO_CURE]],
      ['AS8-target-read-body', 'na', 'if true; then read T <<< {OUT}/b; fi; echo x > "$T/t.sh"', N, ['text', REMEDY_ABS, NO_CURE]],
      ['AS8-target-head-unset', 'na', 'read c <<< true; "$c" x; echo y > "$T/a.txt"', N, ['text', REMEDY_ABS, NO_CURE]],
      ['AS8-ctl-target-head-unset-literal-head', 'na', 'read c <<< true; /usr/bin/true x; T={OUT}/t; mkdir -p "$T"; echo y > "$T/a.txt"', N, 'allow'],
      ['AS8-ctl-target-head-unset-bg', 'na', 'read c <<< true; "$c" x & T={OUT}/t; mkdir -p "$T"; echo y > "$T/a.txt"', N, 'allow'],
      ['AS8-target-two-names', 'na', 'read A <<< {OUT}; for L in a; do :; done; echo x > "$A/$L/t.sh"', N, ['text', REMEDY_ABS, NO_CURE]],
      ['AS8-target-two-names-glued', 'na', 'read A <<< {OUT}/b; for L in a; do :; done; echo x > "$A$L/t.sh"', N, ['text', REMEDY_ABS, NO_CURE]],
      ['AS8-target-two-cures', 'na', 'read A <<< {OUT}; read B <<< b; echo x > "$A/$B.sh"', N, ['text', REMEDY_ABS, NO_CURE]],
      ['AS8-ctl-target-two-cures-literal', 'na', 'A={OUT}; B=b; echo x > "$A/$B.sh"', N, 'allow'],
      ['AS8-target-pwd-unknown', 'na', 'cd "$D"; echo x > "$PWD/t.sh"', N, ['text', REMEDY_ABS, NO_CURE]],
      ['AS8-target-oldpwd', 'na', 'echo x > "$OLDPWD/t.sh"', N, ['text', REMEDY_ABS, NO_CURE]],
      ['AS8-target-braced', 'na', 'echo x > "${T}/t.sh"', N, ['text', REMEDY_ABS, NO_CURE]],
      ['AS8-target-braced-head', 'na', 'read c <<< true; "$c" x; T={OUT}/t; echo x > "${T}/t.sh"', N, ['text', REMEDY_ABS, NO_CURE]],
      ['AS8-target-backtick', 'na', 'read T <<< {OUT}/b; echo x > "$T/`echo t`.sh"', N, ['text', REMEDY_ABS, NO_CURE]],
      ['AS8-target-glob-no-name', 'na', `source ${ENV}; echo x > n*.md`, N, ['text', REMEDY_ABS, NO_CURE]],
      ['AS8-target-unset-then-loop', 'na', 'read T <<< {OUT}/b; unset T; for T in a; do :; done; echo x > "$T/t.sh"', N, ['text', REMEDY_ABS, NO_CURE]],
    );
    // item 6: an option of a command named by a variable after a construct that leaves the directory unknown stays refused (the program may read any
    // word as a path); M2's ONE remedy that always lifts it: name the command by its literal path (an option is then not judged as a path) AND spell
    // each path it is handed as an absolute path (a relative one stays under the directory not known); the twins: the literal interpreter with
    // absolute paths, a cd after `;` (passes). The cd the rounds before offered is gone (it did not lift where the directory not known was the
    // command's own `env -C`: the fourth verify round's T4-5)
    const headRemedy = (sp) => `Name the command by its literal path rather than ${sp}, and spell each path it is handed as an absolute path`;
    // a shell reading a script the guard does not read (the piped and script roads) has no command to name, and an option it is handed takes no
    // absolute spelling, so the kind is split and its ONE remedy is the cd that makes the directory known, with no directory option of the command's
    // own (fork main's cd lifted these; the fifth verify round's T5-2); where the unread text itself leaves the directory unknown, the text spelled out
    const SCRIPT_CD = 'Run the command after a cd to a literal absolute directory that exists, as a command of its own (not after `&&`), after the last command that leaves the directory unknown (such as that construct, or a later `source`, `.`, eval, cd to a variable or command named by a variable), with no directory option (`-C`, `--chdir` or `-D`) on the command itself';
    const SCRIPT_TEXT = 'Spell the script out as literal words, with its paths as absolute paths';   // one remedy for the text's own move and an earlier construct's (the sixth verify round's tg-m6-3)
    rows.push(
      ['AS6-source-option', 'na', `source ${ENV}; "$PY" {OUT}/scratch/x.py --outdir {OUT}/res`, N, ['dir', [headRemedy('`"$PY"`')], ['one of its options', 'cd to']]],
      ['AS6-cd-option-value', 'na', 'cd "$D"; "$PY" {OUT}/scratch/x.py --seed 3', N, ['dir', [headRemedy('`"$PY"`')], ['one of its options', 'cd to']]],
      ['AS6-and-cd', 'na', `source ${ENV} && cd {NA} && "$PY" {OUT}/scratch/x.py --outdir {OUT}/res`, N, ['dir', [headRemedy('`"$PY"`')], 'cd to']],
      ['AS6-cd-then-later-head', 'na', `source ${ENV}; cd {NA}; "$PY" x; "$PY" {OUT}/scratch/x.py --outdir {OUT}/res`, N, ['dir', [headRemedy('`"$PY"`')], 'cd to']],
      ['AS6-ctl-literal-interpreter', 'na', `source ${ENV}; /usr/bin/python3 {OUT}/scratch/x.py --outdir {OUT}/res`, N, 'allow'],
      ['AS6-ctl-semi-cd', 'na', `source ${ENV}; cd {NA}; "$PY" {OUT}/scratch/x.py --outdir {OUT}/res`, N, 'allow'],
      ['AS6-ctl-newline-cd', 'na', `source ${ENV}\ncd {NA}\n"$PY" {OUT}/scratch/x.py --outdir {OUT}/res`, N, 'allow'],
      // an operand the command writes (M2): the literal path AND the absolute spelling lift it; either alone does not (the literal path leaves
      // report.md relative to the directory not known; an absolute path leaves an option judged as a path). The remedy twin that lifts it
      ['AS6-writer-operand', 'na', `source ${ENV}; read c <<< tee; "$c" report.md < /dev/null`, N, ['dir', ['names report.md, a relative path', headRemedy('`"$c"`')], ['one of its options', 'cd to']]],
      ['AS6-writer-operand-remedy', 'na', `source ${ENV}; read c <<< tee; /usr/bin/tee {NA}/scratch/report.md < /dev/null`, N, 'allow'],   // M2's one remedy followed: the literal command, the path absolute
      ['AS6-ctl-writer-operand-cd', 'na', `source ${ENV}; cd {NA}/scratch; read c <<< tee; "$c" report.md < /dev/null`, N, 'allow'],
      ['AS6-writer-operand-literal', 'na', `source ${ENV}; /usr/bin/tee report.md < /dev/null`, N, ['dir', ['names report.md, a relative path', 'Spell the target as an absolute path'], ['Name the command', 'cd to']]],   // a literal head: unknownDir, not the q1 head remedy (M2)
      // T5-2's shapes (an option word on the piped, here-string and eval roads after a source), a chdir of the command's own that a cd before it does
      // not reach, and a text whose own earlier command leaves the directory unknown, which no cd reaches (its remedy the script spelled out)
      ['AS6-script-piped-option', 'na', `source ${ENV}; cat "$f" | bash -s -- --seed 3`, N, ['dir', ['its shell reading its script from `cat "$f"` names --seed, a relative path', SCRIPT_CD], ['Spell the target as an absolute path', 'Name the command']]],
      ['AS6-script-herestring-option', 'na', `source ${ENV}; bash -s -- --seed 3 <<< "$X"`, N, ['dir', ['names --seed, a relative path', SCRIPT_CD], 'Spell the target as an absolute path']],
      ['AS6-script-eval-option', 'na', `source ${ENV}; eval "$X" --seed 3`, N, ['dir', ['its script held in `"$X" --seed 3` names --seed, a relative path', SCRIPT_CD], 'Spell the target as an absolute path']],
      ['AS6-script-piped-own-chdir', 'na', 'cat "$f" | env -C "$d" bash -s -- --seed 3', N, ['dir', ['an earlier `env -C` names "$d", a directory the shell fills in', SCRIPT_CD]]],
      ['AS6-script-eval-in-text', 'na', 'eval "$X; $Y" --seed 3', N, ['dir', ['an earlier command of the text `"$X; $Y" --seed 3` stands for may move the shell', SCRIPT_TEXT], ['Run the command after a cd', 'Spell the target as an absolute path']]],
      // and where an earlier construct left the directory unknown too (the sixth verify round's tg-m6-3): a cd does not reach the text's own move, so the
      // text spelled out, with its paths absolute for the earlier construct's directory, is the one remedy for both causes
      ['AS6-script-eval-in-text-after-source', 'na', `source ${ENV}; eval "$X; $Y" --seed 3`, N, ['dir', ['an earlier command of the text `"$X; $Y" --seed 3` stands for may move the shell', SCRIPT_TEXT], 'Run the command after a cd']],
      ['AS6-script-eval-in-text-path-after-source', 'na', `source ${ENV}; eval "$X; $Y" scratch/a.txt`, N, ['dir', ['names scratch/a.txt, a relative path', 'an earlier command of the text `"$X; $Y" scratch/a.txt` stands for may move the shell', SCRIPT_TEXT], 'Run the command after a cd']],
      ['AS6-script-eval-in-text-after-cd-var', 'na', 'read d <<< docs; cd "$d"; eval "$X; $Y" --seed 3', N, ['dir', ['an earlier command of the text `"$X; $Y" --seed 3` stands for may move the shell', SCRIPT_TEXT], 'Run the command after a cd']],
    );
    // item 7: the remedies say what works (M2, one remedy each): a command name that is a pattern the guard cannot expand in a directory not known
    // asks for the name without a pattern after a cd that makes the directory known again; a relative target after such a construct asks for the
    // target as an absolute path (the cd is gone from the target remedy, kept for the pattern head: a pattern read in a known directory is still
    // a residual zsh globs, so the name must lose the pattern too)
    const PATTERN_REMEDY_DIR = 'Spell the command name without a pattern after a cd to a literal absolute directory that exists, as a command of its own (not after `&&`), after the last command that leaves the directory unknown (such as that construct, or a later `source`, `.`, eval, cd to a variable or command named by a variable)';
    const TARGET_REMEDY = 'Spell the target as an absolute path';
    const COMPARE_REMEDY = 'Write the comparison with `expr`, its operator quoted (`expr "$a" \\> "$b"`), which bash, zsh and dash run alike: ';
    rows.push(
      ['AS7-pattern-head-cd', 'na', 'cd "$D"; ./c? a b', N, ['text', `\`./c?\` is a pattern, matched in a directory that is not known when I check the command (an earlier \`cd\` names "$D", a directory the shell fills in when the command runs), so which command it names is not known, so I cannot tell what would run or which file it would write, and {NA} tracks files whose changes are recorded for me to accept or reject. ${PATTERN_REMEDY_DIR}`, 'the alias or the binding']],
      ['AS7-pattern-head-source', 'na', `source ${ENV}; [ab] x`, N, ['text', PATTERN_REMEDY_DIR, 'the alias or the binding']],
      ['AS7-ctl-pattern-head-cd-after-last', 'na', 'cd "$D"; "$PY" {OUT}/scratch/x.py; cd {NA}/scratch; ./c? a b', N, 'allow'],
      ['AS7-target-after-source', 'na', `source ${ENV}; echo x > scratch/a.txt`, N, ['dir', TARGET_REMEDY, 'cd to']],
      ['AS7-target-and-cd', 'na', `source ${ENV} && cd {NA} && echo x > scratch/a.txt`, N, ['dir', TARGET_REMEDY, 'cd to']],
      ['AS7-target-later-head', 'na', `source ${ENV}; cd {NA}; "$PY" x; echo x > scratch/a.txt`, N, ['dir', TARGET_REMEDY, 'cd to']],
      ['AS7-ctl-semi-cd', 'na', `source ${ENV}; cd {NA}; echo x > scratch/a.txt`, N, 'allow'],
      ['AS7-target-cd-relative', 'na', `source ${ENV}; cd scratch; echo x > a.txt`, N, ['dir', TARGET_REMEDY, 'cd to']],
      ['AS7-pattern-head-later-head', 'na', 'cd "$D"; "$PY" {OUT}/scratch/x.py; ./c? a b', N, ['text', ['an earlier `cd` names "$D"', PATTERN_REMEDY_DIR]]],
      ['AS7-target-later-source', 'na', `cd "$D"; source ${ENV}; echo x > scratch/a.txt`, N, ['dir', ['an earlier `cd` names "$D"', TARGET_REMEDY], 'cd to']],
      ['AS7-ctl-target-cd-after-last', 'na', `cd "$D"; source ${ENV}; cd {NA}; echo x > scratch/a.txt`, N, 'allow'],
      // the piped road's remedy is the cd (a shell reading its script from a pipe has no command to name, and a word it is handed may be an option:
      // the fifth verify round's T5-2), not the target's absolute path, which the rounds before gave
      ['AS7-target-piped-road', 'na', `source ${ENV}; cat "$f" | bash -s docs/report.md`, N, ['dir', SCRIPT_CD, ['Name the command', TARGET_REMEDY]]],
      ['AS7-target-remedy-abs', 'na', `source ${ENV}; echo x > {OUT}/scratch/a.txt`, N, 'allow'],   // the directory-not-known target's one remedy followed, the absolute path (the census below builds such a twin for every refused row)
      // a `>` inside `[[ ... ]]` with a target the guard cannot read (a comparison in bash and zsh, a redirection in dash): ONE remedy, the comparison
      // written with `expr`, which writes nothing in any of them (the sixth verify round's tg-t6-4: the text had named a cwd outside the project and
      // `expr` beside the absolute path)
      ['AS7-compare-notlit', 'nad', '[[ $a > $b ]] && echo y', N, ['text', ['which is not a literal path', COMPARE_REMEDY], ['run it from a directory outside', 'Spell the path out']]],
      ['AS7-compare-remedy', 'nad', 'expr $a \\> $b && echo y', N, 'allow'],   // the one remedy followed (the census below builds such a twin for every row of the kind)
    );
    const verdict = (id, cmd, h, want, where) => {
      assert.ok(!h.reason.includes('an error of my own'), `${id}: no internal error ${where}: ${h.reason.split('\n')[0]}`);
      if (want === 'allow') { assert.equal(h.status, 0, `${id}: allowed ${where}: ${cmd}: ${h.reason.split('\n')[0]}`); return; }
      assert.equal(h.status, 2, `${id}: refused ${where}: ${cmd}`);
      assert.ok(!/[\u2013\u2014]/.test(h.reason) && !ROMP_NOUNS.test(h.reason.split(w.W).join('<w>')), `${id}: no em dash or en dash, no romp noun`);
      if (want === 'name') assert.match(h.reason, BY_NAME_RE, `${id}: by name ${where}: ${h.reason.split('\n')[0]}`);
      else {
        if (want[0] === 'dir') assert.ok(h.reason.includes('the directory it is relative to is not known'), `${id}: refused ${where} for the directory not known: ${h.reason.split('\n')[0]}`);
        for (const t of texts(want[1])) assert.ok(h.reason.includes(t), `${id}: refused ${where}, the reason including (${t}): ${h.reason.split('\n')[0]}`);
        for (const t of texts(want[2])) assert.ok(!h.reason.includes(t), `${id}: refused ${where}, the reason without (${t}): ${h.reason.split('\n')[0]}`);
      }
    };
    const texts = (x) => (x == null ? [] : Array.isArray(x) ? x : [x]);   // an expected text, or a list of them
    const fillT = (x) => (Array.isArray(x) ? x.map(fillT) : typeof x === 'string' ? w.fill(x) : x);
    const fillWant = (want) => (Array.isArray(want) ? want.map((s, i) => (i ? fillT(s) : s)) : want);   // an expected text may spell {NA}
    const guardOnly = [];   // the rows asked of the guard alone (writers null: no leg runs their command)
    const reasonAt = {};   // each row's verdict and reason from its own cwd, for the M2 remedy census below
    // THE MADE NAME's legs (fork PR 975's gap pass, 2026-10-06; the completeness check found that the cost rows and THE ASSIGNING HEAD's witness rows never
    // ran their shell legs on any runner, so the writers they claim rested on probes and mutants alone). THE INVOKED PROGRAM gates a leg on every program
    // its command runs, and a name the command makes itself (a copy of a program under a directory its PATH then names), binds itself (a function or an
    // alias of its own that the gate does not read) or runs to measure that no shell finds or reaches it is no program of the runner, so each such leg was
    // NOT RUN. For the rows below, each such name is asked as what it stands for: a made copy by the presence of the program it copies, a bound name as
    // present wherever the shell is (its body runs a builtin), and a name no shell should find or reach by its absence here, THE RECORDED ABSENCES' turn
    // (NOT RUN where the runner has a program of that name, since the row was measured without one; the table itself cannot hold these rows, whose test runs
    // after its pin). Every other program the command runs is gated as before. Fork PR 975's round 2 (tests-3) found 97 rows that ran no leg on any runner
    // and ruled the class: a row whose program is a name the command makes stands in this map, the rule over every such row, not a list of the ones
    // found (THE BOUND NAME's writers into a directory and its one-operand links, AS8-into-dir-*, AS8-made-one-op-ln*, AS8-made-nonlit-into-dir, by the
    // world's w2 they copy; the copies of cp under a readable PATH and through a PATH set in a function or an eval, AS8-into-dir-readable-path,
    // AS8-made-one-op-ln-readable-path, AS8-residual-path-func-call, AS8-residual-path-eval; RULE B's rows, AS8-ruleB-* and AS8-residual-ruleB-cp-r-dir,
    // made after the finding; an alias of cp whose name the reader takes from a file, AS8-alias-unread-operand-cp; and a backup run by its full path,
    // AS8-residual-backup-explicit-path, whose key is that path filled in, as the gate reads it). A rebinding the reader cannot know (a PATH entry that
    // is an expansion, `PATH=$X:$PATH` and its kin, or a global alias's name) holds the leg NOT RUN whatever the map says, so each such row is named in
    // RESTS_ON_PROBES below, its writers resting on the probes (the armed and backup rows the round's refuter moved out of this map among them), and the
    // census after the rows holds that list equal to the rows the gate reports so, both ways
    const CP = '/usr/bin/cp';
    const W2 = '{W}/tools/w2';
    const RESTS_ON_PROBES = new Set([
      'AS8-armed-c2', 'AS8-armed-c2-unread-source', 'AS8-armed-c2-untracked', 'AS8-armed-echo', 'AS8-armed-mv-untracked', 'AS8-backup-after-cd',
      'AS8-backup-cp', 'AS8-builtin-bound-env-echo', 'AS8-builtin-cd-after-backup', 'AS8-builtin-cd-same-name', 'AS8-builtin-cd-same-name-untracked',
      'AS8-builtin-command-echo', 'AS8-builtin-dash-pctbuiltin-dash-c', 'AS8-builtin-dash-pctbuiltin-echo', 'AS8-builtin-dash-pctbuiltin-printf',
      'AS8-builtin-dash-pctbuiltin-test', 'AS8-builtin-echo-backup-name', 'AS8-builtin-enable-script', 'AS8-builtin-env-echo-after-backup',
      'AS8-builtin-exec-command', 'AS8-builtin-exec-echo', 'AS8-builtin-export-after-backup', 'AS8-builtin-gate-ansic-before-path',
      'AS8-builtin-gate-ansic-loop', 'AS8-builtin-gate-before-path', 'AS8-builtin-gate-disable', 'AS8-builtin-gate-disable-for',
      'AS8-builtin-gate-eval-ansic-loop', 'AS8-builtin-gate-eval-enable', 'AS8-builtin-gate-for', 'AS8-builtin-gate-func-loop',
      'AS8-builtin-gate-mention-cost', 'AS8-builtin-gate-source-loop', 'AS8-builtin-gate-trap-debug', 'AS8-builtin-gate-trap-exit',
      'AS8-builtin-gate-unread-head-loop', 'AS8-builtin-gate-unread-trap', 'AS8-builtin-gate-until', 'AS8-builtin-gate-var-enable',
      'AS8-builtin-gate-while', 'AS8-builtin-gate-zmodload', 'AS8-builtin-noenable-script', 'AS8-builtin-nonbuiltin-after-backup',
      'AS8-builtin-partquoted-for', 'AS8-builtin-quoted-echo-cost', 'AS8-builtin-quoted-if', 'AS8-builtin-quoted-while',
      'AS8-builtin-shadow-bash-aliases', 'AS8-builtin-shadow-bash-printf-v', 'AS8-builtin-shadow-zsh-assign-expansion', 'AS8-builtin-shadow-zsh-cd',
      'AS8-builtin-shadow-zsh-printf-v', 'AS8-builtin-shadow-zsh-read-r', 'AS8-builtin-slash-env-echo', 'AS8-builtin-slash-nohup-echo',
      'AS8-cost-backup-none', 'AS8-cost-function-call', 'AS8-cost-unread-path-other-name', 'AS8-ctl-c2-unread-fullpath', 'AS8-ctl-function-definition',
      'AS8-ctl-function-definition-path-body', 'AS8-ctl-mv-fullpath', 'AS8-drop-builtin-cd', 'AS8-drop-builtin-export', 'AS8-drop-builtin-ulimit',
      'AS8-drop-command-cd', 'AS8-drop-command-export', 'AS8-drop-command-p-cd', 'AS8-drop-command-ulimit', 'AS8-drop-dash-cd', 'AS8-drop-exec-a-cd',
      'AS8-drop-exec-cd', 'AS8-drop-exec-export', 'AS8-drop-exec-ulimit', 'AS8-drop-nocorrect-cd', 'AS8-drop-noglob-cd', 'AS8-drop-noremedy-env-cd',
      'AS8-drop-noremedy-gate-cd', 'AS8-drop-time-cd', 'AS8-drop-time-export', 'AS8-drop-time-p-cd', 'AS8-drop-time-ulimit',
      'AS8-residual-dash-pctbuiltin-echo-out', 'AS8-residual-partquoted-keyword', 'AS8-residual-shadow-zsh-nocopy', 'AS8-residual-shadow-zsh-out',
      'AS8-root-global-alias', 'AS8-sourced-dot', 'AS8-sourced-dot-piped', 'AS8-sourced-source',
    ]);
    const MADE = {
      'AS8-root-print-v': { c2: CP }, 'AS8-root-getln': { c2: CP }, 'AS8-root-unread-head': { c2: CP }, 'AS8-root-glob-head': { c2: CP },
      'AS8-root-func-later-loop': { c2: CP }, 'AS8-root-func-later-keyword': { c2: CP }, 'AS8-root-func-later-body': { c2: CP }, 'AS8-root-func-later-echo': { c2: CP },
      'AS8-root-func-zsh-autoload': { c2: CP }, 'AS8-root-func-zsh-functions-c': { c2: CP, g: 'bound' }, 'AS8-root-func-unread-head-loop': { w3: W2 },
      'AS8-ruleS-bracevar-path': { c2: CP }, 'AS8-ruleS-nameRun-typeset-fu': { c2: CP, g: 'bound' }, 'AS8-ruleS-nameRun-declare-fu': { c2: CP, g: 'bound' }, 'AS8-ruleS-nameRun-readonly-fu': { c2: CP, g: 'bound' },
      'AS8-ruleS-nameRun-typeset-fu-quoted': { c2: CP, g: 'bound' }, 'AS8-ruleS-nameRun-declare-fu-dquoted': { c2: CP, g: 'bound' }, 'AS8-ruleS-nameRun-typeset-fu-bslash': { c2: CP, g: 'bound' },
      'AS8-root-alias-head': { c2: CP }, 'AS8-root-alias-unread-operand': { c2: CP, g: 'bound' },
      'AS8-cost-into-file': { w2: 'absent' }, 'AS8-cost-into-dir-T': { w2: 'absent' },
      'AS8-root-test-v-path': { c2: CP }, 'AS8-root-jobs-x-read-path': { w3: W2 }, 'AS8-root-jobs-x-eval-func': { c2: CP }, 'AS8-root-zsh-continue-path': { c2: CP },
      'AS8-root-old-arith-path-ls': { c2: CP }, 'AS8-root-old-arith-path-echo': { c2: CP }, 'AS8-root-old-arith-path-dq': { c2: CP },
      'AS8-residual-path-zsh-array': { c2: CP }, 'AS8-residual-path-zsh-array-keep': { c2: CP }, 'AS8-residual-path-zsh-array-append': { c2: CP },
      'AS8-residual-path-zsh-array-element': { c2: CP }, 'AS8-residual-path-zsh-read-A': { c2: CP }, 'AS8-residual-path-zsh-indirect': { c2: CP },
      'AS8-residual-assign-zsh-glob-qualifier': { 'e:p=0:': 'absent' },   // the reader takes zsh's glob qualifier for a command, which bash and dash never reach (a syntax error)
      // fork PR 975's round 2 (tests-3): the made names of THE BOUND NAME's rows, R3's rows and the residuals beside them
      ...Object.fromEntries(['AS8-into-dir-cp', 'AS8-into-dir-cp-made', 'AS8-into-dir-install', 'AS8-into-dir-ln', 'AS8-into-dir-ln-s', 'AS8-into-dir-mv',
        'AS8-made-nonlit-into-dir', 'AS8-made-one-op-ln', 'AS8-made-one-op-ln-s', 'AS8-made-one-op-ln-s-alone', 'AS8-made-one-op-ln-s-nonlit'].map((id) => [id, { w2: W2 }])),
      ...Object.fromEntries(['AS8-into-dir-readable-path', 'AS8-made-one-op-ln-readable-path', 'AS8-residual-path-func-call', 'AS8-residual-path-eval',
        'AS8-ruleB-tests1-lns-two', 'AS8-ruleB-tests1-lns-relsrc', 'AS8-ruleB-tests1-lns-t', 'AS8-ruleB-corr4-lns-existdir', 'AS8-ruleB-corr4-empty-path'].map((id) => [id, { c2: CP }])),
      ...Object.fromEntries(['AS8-ruleB-extra4-cp', 'AS8-ruleB-extra4-mv', 'AS8-ruleB-extra4-ln', 'AS8-ruleB-extra4-install', 'AS8-ruleB-extra4-catredir',
        'AS8-ruleB-extra4-filedst', 'AS8-ruleB-extra4-out', 'AS8-residual-ruleB-cp-r-dir'].map((id) => [id, { zc: CP }])),
      ...Object.fromEntries(['AS8-ruleB-tests2-cp', 'AS8-ruleB-tests2-mv', 'AS8-ruleB-tests2-install', 'AS8-ruleB-tests2-cpt'].map((id) => [id, { c2x: CP }])),
      'AS8-alias-unread-operand-cp': { g: CP },   // the alias the file names, of cp
      'AS8-residual-backup-explicit-path': { '{OUT}/scratch/xzz': CP },   // the backup of a copy of cp, run by its full path
    };
    const legTable = (id) => {
      if (!Object.hasOwn(MADE, id)) return NAMED_PROBE;
      const t = { ...NAMED_PROBE };
      for (const [key, stand] of Object.entries(MADE[id])) {
        const name = w.fill(key);   // a made path is filled in, as the gate reads the program word
        t[name] = stand === 'bound' ? { ok: true, why: null }
          : stand === 'absent' ? (realPresence(name).ok ? { ok: false, why: "is on this runner, where the row's evidence was measured without a program of that name" } : { ok: true, why: null })
            : presenceOf(w.fill(stand));
      }
      return t;
    };
    const judge = (id, cwd, raw, writers, expect, outside = 'allow') => {
      const cmd = w.fill(raw);
      const at = w.cwds[cwd];
      if (outside != null) { w.build(); verdict(id, cmd, w.hook(cmd, w.cwds.out), fillWant(outside), 'from a cwd in no project'); }   // first, so a row that reds from its cwd has shown its twin from a cwd in no project
      w.build();
      const hAt = w.hook(cmd, at);
      reasonAt[id] = { status: hAt.status, reason: hAt.reason };
      verdict(id, cmd, hAt, fillWant(expect), `from ${cwd}`);
      if (writers === null) { guardOnly.push(id); return; }
      if (namedPresent(cmd, `${id}, whose command names it: ${cmd}`, legTable(id), notRunReport(id), { cwd: at })) for (const shell of shellsFor(A, id)) {
        const r = w.run(cmd, at, shell);
        if (Object.hasOwn(MADE, id)) madeRan.add(id);
        ranHere.add(id);
        assert.equal(r.changed, writers.includes(shell), `${id}: run unguarded, ${shell} ${writers.includes(shell) ? 'writes' : 'leaves'} the tracked subset: ${cmd}: ${r.stderr}`);
      }
    };
    // every row is asked and every failure listed (each message opens with the row's id), so a run against an earlier guard names each row it reds
    const failures = [];
    const madeRan = new Set();   // THE MADE NAME's rows whose legs ran here
    const ranHere = new Set();   // every row whose legs ran here
    const notRun = {};   // each row's NOT RUN lines from the gate, printed as before and kept for the census of RESTS_ON_PROBES
    const notRunReport = (id) => (line) => { (notRun[id] = notRun[id] || []).push(line); console.error(line); };
    for (const [id, cwd, raw, writers, expect, outside] of rows) { try { judge(id, cwd, raw, writers, expect, outside); } catch (e) { failures.push(String(e.message).split('\n')[0]); } }
    // item 4's second cause: a tracked folder holding more entries than the caps (GLOB_MATCH_CAP, 2000) makes the pattern one the guard
    // cannot expand from any directory; tee truncates every file the pattern names
    const crowd = () => { for (let i = 0; i < 2101; i++) fs.writeFileSync(path.join(w.NA, 'notes', `f${i}.md`), 'x\n'); };
    const capRows = [
      ['AS4-cap-root', 'na', 'read c <<< tee; "$c" notes/* < /dev/null', BZ, ['text', 'names notes/*, which is not a literal path']],
      ['AS4-cap-out', 'out', 'read c <<< tee; "$c" {NA}/notes/* < /dev/null', BZ, ['text', 'names {NA}/notes/*, which is not a literal path']],
      ['AS4-cap-ctl-known-command', 'na', 'tee notes/* < /dev/null', A, ['text', 'names notes/*, which is not a literal path']],
      // an absolute pattern whose directory part is itself a pattern, past the caps after a construct that leaves the directory unknown: a target
      // the hook cannot read (judging it by its spelling would place it in no project and pass it; tee truncated both projects' notes)
      ['AS4-cap-wild-dir-cd', 'na', 'read c <<< tee; cd "$D"; "$c" {W}/*/notes/* < /dev/null', BZ, ['text', 'names {W}/*/notes/*, which is not a literal path']],
      ['AS4-cap-wild-dir-source', 'na', `read c <<< tee; source ${ENV}; "$c" {W}/*/notes/* < /dev/null`, BZ, ['text', 'names {W}/*/notes/*, which is not a literal path']],
      // the operand that names a tracked file is refused by name before the pattern past the caps (THE UNREAD OPERAND's tag on the cap's record)
      ['AS4-cap-q1-order', 'na', 'read c <<< tee; "$c" docs/report.md notes/* < /dev/null', BZ, 'name'],
      // DISCLOSED, older than this change: such a pattern past the caps from a cwd in no project passes, its spelled directory in no project
      ['AS4-residual-wild-dir-out', 'out', 'read c <<< tee; "$c" {W}/*/notes/* < /dev/null', BZ, 'allow'],
      ['AS4-residual-wild-dir-known-out', 'out', 'tee {W}/*/notes/* < /dev/null', A, 'allow'],
      // item 7: a command name that is a pattern past the caps, the directory known, asks for the name without a pattern alone, and so does an
      // absolute one after a cd the guard does not follow (the pattern's directory is spelled, so a cd does not change it)
      ['AS7-cap-pattern-head', 'na', '{NA}/notes/f* a b', N, ['text', ['is a pattern matching more names than I read (more than 2000 matches, or more than 50000 entries to read), so which command it names is not known', 'Spell the command name without a pattern: '], 'cd to']],
      ['AS7-cap-pattern-head-abs-cd', 'na', 'cd "$D"; {NA}/notes/f* a b', N, ['text', ['is a pattern matching more names than I read', 'Spell the command name without a pattern: '], ['cd to', 'not known when I check']]],
    ];
    for (const [id, cwd, raw, writers, expect] of capRows) {
      try {
        const cmd = w.fill(raw);
        const at = w.cwds[cwd];
        w.build(); crowd();
        const hAt = w.hook(cmd, at);
        reasonAt[id] = { status: hAt.status, reason: hAt.reason };
        verdict(id, cmd, hAt, fillWant(expect), `from ${cwd}`);
        if (namedPresent(cmd, `${id}, whose command names it: ${cmd}`, NAMED_PROBE, undefined, { cwd: at })) for (const shell of shellsFor(A, id)) {
          w.build(); crowd();
          const before = w.fingerprint();
          const argv = shell === 'bash' ? ['--norc', '--noprofile', '-c', cmd] : shell === 'zsh' ? ['-f', '-c', cmd] : ['-c', cmd];
          const r = spawnLeg(shell, argv, { cwd: at, input: '', encoding: 'utf8', env: w.env, timeout: 60000 });   // as sixthPassWorld's run does
          assert.equal(w.fingerprint() !== before, writers.includes(shell), `${id}: run unguarded over the crowded folder, ${shell} ${writers.includes(shell) ? 'writes' : 'leaves'} the tracked subset: ${cmd}: ${String(r.stderr || '').slice(0, 300)}`);
        }
      } catch (e) { failures.push(String(e.message).split('\n')[0]); }
    }
    assert.deepEqual(failures, [], `every row holds (${failures.length} do not)`);
    // RULE B's memo (fork PR 975's round 2, R3): each bound path is spliced once per head lookup, so a diamond of copies (each x_i and y_i written from
    // both x_(i-1) and y_(i-1)) is judged in linear time. Unmemoized the splice is exponential: a depth-18 diamond took about 16.3 s, past the installer's
    // 10 s timeout, where a killed hook would let the command run; the memo holds it under one second, with the same by-name refusal (the bound name chains
    // to cp). Timed end to end through the hook as a process, the way the installer runs it
    {
      const D = 18;
      const dia = ['cp /usr/bin/cp {OUT}/x0', 'cp /usr/bin/cp {OUT}/y0'];
      for (let i = 1; i <= D; i++) for (const v of ['x', 'y']) { dia.push(`cp {OUT}/x${i - 1} {OUT}/${v}${i}`); dia.push(`cp {OUT}/y${i - 1} {OUT}/${v}${i}`); }
      dia.push('PATH={OUT}:/usr/bin:/bin', `x${D} {NA}/base/report.md {NA}/docs/report.md`);
      const diaCmd = w.fill(dia.join('; '));
      w.build();
      const t0 = process.hrtime.bigint();
      const hDia = w.hook(diaCmd, w.cwds.na);
      const diaMs = Number(process.hrtime.bigint() - t0) / 1e6;
      assert.equal(hDia.status, 2, `RULE B: the depth-${D} diamond of copies is refused (the bound name chains to cp): ${String(hDia.reason).split('\n')[0]}`);
      assert.ok(diaMs < 1000, `RULE B's memo holds the depth-${D} diamond under one second (unmemoized it is exponential, about 16.3 s, past the 10 s installer timeout): ${diaMs.toFixed(0)} ms`);
      console.log(`# RULE B's memo: the depth-${D} diamond of copies judged in ${diaMs.toFixed(0)} ms (unmemoized about 16300 ms)`);
    }
    // THE MADE NAME's map names rows the test has, and where cp, the shells and the world's program are present (this box, CI's bash) their legs ran (asked
    // after every row holds, since a row whose verdict reds runs no leg)
    const rowIds = new Set(rows.map((r) => r[0]));
    assert.deepEqual(Object.keys(MADE).filter((id) => !rowIds.has(id)), [], 'every row THE MADE NAME names is a row of this test');
    if (realPresence(CP).ok && HAS_SHELL.bash) assert.deepEqual(Object.keys(MADE).filter((id) => !madeRan.has(id)), [], 'every row THE MADE NAME names ran its legs here');
    console.log(`# THE MADE NAME: ${madeRan.size} of ${Object.keys(MADE).length} rows ran their legs here`);
    // RESTS_ON_PROBES (fork PR 975's round 2, tests-3): the list names exactly the rows whose legs no runner runs because the gate cannot know a name their
    // command rebinds, so a row that joins the class reds until it is named there, and a named row the gate reads reds until it leaves the list (the
    // reason comes from the command's text alone, so the census holds on every runner); no such row stands in THE MADE NAME's map
    const UNREAD = 'the command rebinds a name the reader cannot know';
    const unreadRows = Object.keys(notRun).filter((id) => notRun[id].some((l) => l.includes(UNREAD))).sort();
    assert.deepEqual(unreadRows.filter((id) => !RESTS_ON_PROBES.has(id)), [], 'every row whose rebinding the gate cannot know is named in RESTS_ON_PROBES');
    assert.deepEqual([...RESTS_ON_PROBES].filter((id) => !unreadRows.includes(id)), [], 'every row RESTS_ON_PROBES names is one whose rebinding the gate cannot know');
    assert.deepEqual(Object.keys(MADE).filter((id) => RESTS_ON_PROBES.has(id)), [], 'no row RESTS_ON_PROBES names stands in THE MADE NAME');
    // THE LEAD AFTER `--` (fork PR 975's round 2, tests-3): the gate reads the command after a lead-bearing wrapper's lead where a `--` ends its options,
    // the population every wrapper of the gate's table with operands before the command (zsh's repeat, a word of the shell's own, aside), the census
    // failing on none; the rows that spell the lead there run their legs (asked at the hook's lead census below)
    const gateLeadWrappers = Object.entries(WRAPPERS).filter(([, s]) => s.operands && !s.own).map(([n]) => n);
    assert.ok(gateLeadWrappers.length >= 5 && ['timeout', 'chrt', 'taskset'].every((n) => gateLeadWrappers.includes(n)), `the census reads the gate's lead-bearing wrappers from its table (saw ${gateLeadWrappers.join(', ')})`);
    for (const wr of gateLeadWrappers) assert.deepEqual(programsInvoked(`${wr} -- q975-lead q975-prog x`), [wr, 'q975-prog'], `the gate reads ${wr}'s lead after \`--\` as the lead and the word after it as the program`);
    console.log(`# RESTS_ON_PROBES: ${RESTS_ON_PROBES.size} rows whose rebinding the gate cannot know; ${ranHere.size} of ${rows.length} rows ran their legs here; the rest ran none here: ${rows.map((r) => r[0]).filter((id) => !ranHere.has(id) && !RESTS_ON_PROBES.has(id) && !guardOnly.includes(id)).join(', ') || 'none'}`);
    const all = [...rows, ...capRows];
    const byItem = Object.fromEntries(['AS1', 'AS2', 'AS3', 'AS4', 'AS5', 'AS6', 'AS7', 'AS8'].map((p) => [p, all.filter((r) => r[0].startsWith(`${p}-`)).length]));
    assert.deepEqual(byItem, { AS1: 67, AS2: 36, AS3: 197, AS4: 17, AS5: 68, AS6: 19, AS7: 17, AS8: 283 }, 'the population by item');
    assert.equal(new Set(all.map((r) => r[0])).size, all.length, 'every id once');
    assert.deepEqual(guardOnly, ['AS3-option-refuse-abbrev-sudo', 'AS3-road-sudo-dd', 'AS3-sudoD-flock-script', 'AS3-sudoD-rpt-cp', 'AS3-sudochdir-rpt-cp', 'AS3-time-o-sudo-e-out', 'AS3-time-o-envC-sudo-e-out', 'AS3-time-o-rel-envC-sudo-e-out', ...['again', 'enter', 'resolve'].flatMap((t) => ['short-glued', 'short-separate', 'long-glued', 'long-separate'].map((f) => `AS3-spelled-sudo-${t}-${f}`))], 'the rows asked of the guard alone (no leg runs sudo)');
    // every disclosed residual row is named by id in decision 47, as the header above says (the third verify round's M3-7), the population derived
    // from the rows and the census failing on none
    const plan = fs.readFileSync(fileURLToPath(new URL('../plans/file-review.md', import.meta.url)), 'utf8');
    const d47 = plan.slice(plan.indexOf('\n47. **'), plan.indexOf('\n48. **'));
    assert.ok(plan.includes('\n47. **') && d47.length > 0, 'decision 47 is found in plans/file-review.md');
    const residualIds = all.map((r) => r[0]).filter((id) => id.includes('-residual-'));
    assert.ok(residualIds.length > 0, 'the census reads the residual rows (none read is no census)');
    assert.deepEqual(residualIds.filter((id) => !new RegExp(`(?<![\\w-])${id}(?![\\w-])`).test(d47)), [], 'each disclosed residual row is named by id in decision 47');
    // and the reverse (the text lens's tg-t13-5 on fork PR 975's round 1): every residual id of an item decision 47 names, a glob among them expanded
    // against the rows, is a row id, so a row removed or renamed under a name decision 47 still gives reds here
    const rowIdSet = new Set(all.map((r) => r[0]));
    const d47Residuals = [...new Set([...d47.matchAll(/(?<![\w-])AS[1-8]-[\w*-]*residual[\w*-]*/g)].map((m) => m[0]))];
    assert.ok(d47Residuals.length > 0, 'the reverse census reads the residual ids decision 47 names (none read is no census)');
    const globRows = (t) => { const re = new RegExp(`^${t.split('*').map(escapeRe).join('[\\w-]*')}$`); return all.filter((r) => re.test(r[0])).length; };
    assert.deepEqual(d47Residuals.filter((t) => (t.includes('*') ? globRows(t) === 0 : !rowIdSet.has(t))), [], 'each residual id decision 47 names is a row id, a glob matching at least one');
    // the wrappers behind which a command named by a variable is POISONED (its names unreadable after it) are those WRAPPER_OPT leaves without its
    // `external` mark: M1's names predicate (the names stay readable when at least one external wrapper precedes the head), so each non-external
    // wrapper has its AS3-kept-* row showing the poison, the population derived from the table and the census failing on none; and no wrapper the
    // table marks external is a builtin, a keyword or a precommand modifier in a shell on this runner (`type`, asked as the round derived the marks,
    // so a mark on such a wrapper reds here)
    const hookText = fs.readFileSync(HOOK, 'utf8');
    const optAt = hookText.indexOf('const WRAPPER_OPT = {');
    const optBody = hookText.slice(optAt, hookText.indexOf('\n};\n', optAt));
    const optKeys = [...optBody.matchAll(/^ {2}(?:([a-z]+)|'(-)'): \{/gm)].map((m) => ({ name: m[1] || m[2], at: m.index }));
    const wrapperMarks = optKeys.map((k, i) => ({ name: k.name, external: optBody.slice(k.at, i + 1 < optKeys.length ? optKeys[i + 1].at : optBody.length).includes('external: true') }));
    const keptWrappers = wrapperMarks.filter((m) => !m.external).map((m) => m.name).sort();
    const keptRows = all.map((r) => r[0]).filter((id) => /^AS3-kept-[a-z]+-dd$/.test(id)).map((id) => id.slice('AS3-kept-'.length, -'-dd'.length)).map((n) => (n === 'minus' ? '-' : n)).sort();
    assert.ok(optKeys.length > 0 && keptWrappers.length > 0 && wrapperMarks.some((m) => m.external), 'the census reads the wrapper table, marked and unmarked');
    assert.deepEqual(keptRows, keptWrappers, 'each non-external wrapper has its AS3-kept-* poison row, and no row names a marked one (M1 names predicate)');
    const roadRows = all.map((r) => r[0]).filter((id) => /^AS3-road-[a-z]+-dd$/.test(id)).map((id) => id.slice('AS3-road-'.length, -'-dd'.length)).map((n) => (n === 'minus' ? '-' : n)).sort();
    assert.deepEqual(roadRows, wrapperMarks.map((m) => m.name).sort(), 'each wrapper of the table has its AS3-road-* row, the road behind it, the external ones included (M1; the fifth verify round\'s tg-m5-2 for the wrappers the shell runs itself, the sixth\'s tg-m6-4 for every wrapper)');
    // each lead-bearing wrapper the table marks has its disclosed witness for a `--` before the lead (M3's stopping rule; the fifth verify round's S5-2)
    const leadWrappers = optKeys.filter((k, i) => /\blead: \d/.test(optBody.slice(k.at, i + 1 < optKeys.length ? optKeys[i + 1].at : optBody.length))).map((k) => k.name).sort();
    const leadRows = all.map((r) => r[0]).filter((id) => /^AS3-residual-[a-z]+-dd-lead$/.test(id)).map((id) => id.slice('AS3-residual-'.length, -'-dd-lead'.length)).sort();
    assert.ok(leadWrappers.length > 0, 'the census reads the lead-bearing wrappers from the table');
    assert.deepEqual(leadRows, leadWrappers, 'each lead-bearing wrapper has its AS3-residual-<wrapper>-dd-lead witness row');
    // and each such witness ran its legs where cp, bash and its wrapper are present (THE LEAD AFTER `--`, fork PR 975's round 2, tests-3: the gate read the
    // lead as the program, so none ran on any runner)
    assert.deepEqual(leadWrappers.filter((n) => !gateLeadWrappers.includes(n)), [], 'every lead-bearing wrapper of the hook\'s table is one the gate reads a lead for');
    if (realPresence(CP).ok && HAS_SHELL.bash) assert.deepEqual(leadRows.filter((wr) => realPresence(wr).ok && !ranHere.has(`AS3-residual-${wr}-dd-lead`)), [], 'every lead-bearing wrapper\'s `--` witness ran its legs here');
    for (const sh of shellsFor(['bash', 'zsh', 'dash'], 'the wrapper census')) {
      for (const { name } of wrapperMarks.filter((m) => m.external)) {
        const argv = sh === 'bash' ? ['--norc', '--noprofile', '-c', 'type -t -- "$W"'] : sh === 'zsh' ? ['-f', '-c', 'whence -w -- "$W"'] : ['-c', 'type "$W"'];   // the name in the environment: a word, never a text the cleared-environment reader takes for a command
        const r = spawnSync(sh, argv, { encoding: 'utf8', env: { PATH: process.env.PATH, W: name } });
        const said = `${r.stdout || ''}${r.stderr || ''}`.trim();
        assert.ok(!/\b(builtin|keyword|reserved)\b/.test(said), `${name} is marked external, but ${sh} says: ${said}`);
      }
    }
    console.log(`# the after-source fixes: ${all.length} rows, by item ${Object.entries(byItem).map(([k, v]) => `${k} ${v}`).join(', ')}; ${all.filter((r) => /-residual-/.test(r[0])).length} disclosed residual rows; asked of the guard alone: ${guardOnly.join(', ')}`);
    // M2's proof over every row (the mechanism ruling, 2026-10-03, option (b), and the fifth verify round's rulings): each refusal names the ONE
    // remedy that always lifts it, and "always" is proved over this population row by row, not once per kind. Every refused row is classified by
    // the cause its reason states (kindOf, never by the remedy it names). For a remedy-offering kind, (1) the reason's remedy sentence (between its
    // last "accept or reject." and ": outside that project") EQUALS the kind's one remedy, so a second remedy beside it reds; and (2) the row's
    // remedied command is built and run through the hook: MECHANICALLY where the remedy is a rewrite (BUILD: an absolute target for notlit, dir,
    // dir-q1 and home, a not-literal word spelled as an absolute path outside every project since its value is what the guard cannot know; the cd
    // for patternHead in a directory not known, with the name spelled without a pattern, and for the script roads, with no directory option of
    // the command's own; the binding's source for aliasUnread; the copied program's full path for boundName; the filled-in word spelled as the
    // row reads it and its command put directly before the `|` for the piped kinds; the comparison written with `expr` for notlit-compare), each
    // refusal the hook then names remedied in turn, and by a
    // HAND twin per row otherwise (HAND); a refused row with neither reds. A twin is lifted when it is allowed, or refused by name for a tracked
    // file it names (the text's own promise: a tracked file takes its change through track-edit). A kind whose remedy does not lift each of its
    // rows is split (dir-q1-script and dir-q1-text out of dir: the fifth verify round's T5-2; patternHead and piped split by the remedy each text
    // names; the sixth verify round's notlit-compare out of notlit, tg-t6-4, and option-unheld and option-unheld-piped out of option, tg-t6-2),
    // and a kind with no remedy that always lifts offers none (by-name; q1-name since the fifth verify round's T5-6: the command spelled out lifts
    // it only where that command merely reads the file; option-unheld-piped, whose wrapper dropped would pass a piped command named by a
    // variable), its reason's first line ending with the cause and the track-edit sentence, nothing between (the sixth verify round's tg-m6-2).
    const line1 = (r) => r.split('\n')[0];
    const kindOf = (reason) => {
      const l = line1(reason);
      if (l.startsWith('Track-changes is ON for ')) return l.includes('a text I do not read, so it may run any command') ? 'q1-name' : 'by-name';
      if (l.includes('the directory it is relative to is not known')) {
        if (/ its command named by `/.test(l)) return 'dir-q1';
        if (/ its (?:shell reading its script from|script held in) /.test(l)) return l.includes('an earlier command of the text ') ? 'dir-q1-text' : 'dir-q1-script';
        return 'dir';
      }
      if (l.includes('which is not a literal path')) return l.includes(' inside a `[[ ... ]]` (a comparison in bash and zsh') ? 'notlit-compare' : 'notlit';   // the comparison's sub-kind by the construct the reason names (the sixth verify round's tg-t6-4)
      if (/ wrapper runs .*, a word the shell fills in when the command runs, so the command it runs is one I do not read/.test(l)) return 'piped';
      if (l.includes('a word the shell fills in when the command runs: it may be an option of the wrapper or the command the wrapper runs')) return l.includes('it is followed by `|`') ? 'filled-piped' : 'filled';
      if (l.includes('which I do not read in that spelling')) return 'option';
      if (/ wrapper carries the option .*, which I do not know, so I cannot tell what the command behind it would write or where/.test(l)) return l.includes('it is followed by `|`') ? 'option-unheld-piped' : 'option-unheld';   // an option the table does not hold, split by whether the output reaches `|` (the sixth verify round's tg-t6-2)
      if (l.includes('is looked up through a PATH I do not read here')) return l.endsWith(TRACK_EDIT_SENTENCE) ? 'boundName-noremedy' : 'boundName';   // a bare name and a sourced name (THE SOURCED NAME), by the program's full path; and the no-remedy form where no program stands for the name or for another name the segment looks up (M2's no-remedy, the reviewer's t8-10; THE WRAPPER DROPPED's remedy came out in fork PR 975's round 2, R2)
      if (l.includes('is a pattern, matched in a directory that is not known')) return 'patternHead-dir';
      if (l.includes('is a pattern matching more names than I read')) return 'patternHead-cap';
      if (l.includes('so I cannot tell what would run or which file it would write')) return 'aliasUnread';
      if (l.includes('`$HOME` and `~` name a directory I')) return 'home';
      if (l.includes('a text the shell produces when the command runs, and I could not establish that text')) return 'producer';
      if (l.includes('hands the rest of the command to a splitter or a shell of its own')) return 'opaque';   // a refused wrapper option, its abbreviation among them (the seventh verify round's tg-m7-7)
      return 'unclassified';
    };
    const remedyOf = (reason) => {
      const l = line1(reason);
      let end = l.indexOf(': outside that project');
      if (end < 0) end = l.indexOf(', or make the change with track-edit');
      const start = end < 0 ? -1 : l.lastIndexOf('reject.', end);
      return start < 0 ? null : l.slice(start + 'reject.'.length, end).trim();
    };
    const PIPE_SHAPE = 'directly before that `|`, with no redirection and no group, subshell or compound around it';
    const REMEDY = {
      notlit: 'Spell the path out as an absolute path',
      'notlit-compare': COMPARE_REMEDY.slice(0, -': '.length),
      home: 'Spell the path out as an absolute path',
      dir: TARGET_REMEDY,
      'dir-q1': (l) => headRemedy((l.match(/ its command named by (`[^`]+`) names /) || [])[1]),
      'dir-q1-script': SCRIPT_CD,
      'dir-q1-text': SCRIPT_TEXT,
      'patternHead-dir': PATTERN_REMEDY_DIR,
      'patternHead-cap': 'Spell the command name without a pattern',
      filled: FILLED_SPELL,
      'filled-piped': `${FILLED_SPELL}, and put the command ${PIPE_SHAPE}`,
      piped: `Spell the command out and put it ${PIPE_SHAPE}`,
      option: 'Spell the option in the long form I know',
      'option-unheld': (l) => `Run the command without the \`${(l.match(/ its `([^`]+)` wrapper carries the option /) || [])[1]}\` wrapper`,
      boundName: 'Spell the command by the full path of the program it should run, not a path this command made',
      aliasUnread: 'Spell the command the alias or the binding stands for, with its paths as absolute paths',
      producer: 'Spell the text out (the path, or the script, as literal words)',
      opaque: (l) => `Spell the command without \`${(l.match(/ its `([^`]+)` hands the rest of the command /) || [])[1]}\``,
    };
    const NO_REMEDY = new Set(['by-name', 'q1-name', 'option-unheld-piped', 'boundName-noremedy']);
    // the no-remedy contract stated positively (the sixth verify round's tg-m6-2): the reason's first line ends with the cause's own last words and the
    // track-edit sentence, nothing between them, so a remedy added before the sentence, or spliced into it, reds (remedyOf, which reads up to a
    // terminator, saw neither)
    const TRACK_EDIT_SENTENCE = ' Make the change with track-edit instead, which records it for me to accept or reject:';
    const NO_REMEDY_CAUSE = {
      'by-name': [/ would write the file silently, with no change for me to accept or reject\)\.$/, / would write the file silently, with no change for me to accept or reject\.$/],
      'q1-name': [/ as an operand, so it may write the file silently, with no change for me to accept or reject\.$/],
      'option-unheld-piped': [/, so its output may reach another command, and \S+ tracks files whose changes are recorded for me to accept or reject\.$/],
      'boundName-noremedy': [/, so I cannot tell what would run or which file it would write, and \S+ tracks files whose changes are recorded for me to accept or reject\.$/],
    };
    const keepsNoRemedy = (k, l) => l.endsWith(TRACK_EDIT_SENTENCE) && NO_REMEDY_CAUSE[k].some((re) => re.test(l.slice(0, -TRACK_EDIT_SENTENCE.length)));
    // the rewrites (BUILD), each from the reason's first line, the command as it stands and the row's cwd
    const refusedWord = (l) => { const m = l.match(/ names (.+?), (?:a relative path|which is not a literal path|and `|but )/); if (!m) throw new Error(`no word named: ${l}`); return m[1]; };
    const lastAt = (cmd, raw, before = cmd.length) => {
      let at = -1;
      for (const m of cmd.matchAll(new RegExp(`(?<=^|[\\s;|&(<>='"])${escapeRe(raw)}(?=$|[\\s;|&)<>'"])`, 'g'))) if (m.index < before) at = m.index;
      if (at < 0) throw new Error(`${raw} is not a word of the command`);
      return at;
    };
    const splice = (cmd, at, raw, by) => cmd.slice(0, at) + by + cmd.slice(at + raw.length);
    const absOf = (raw, cwd) => (raw.startsWith('/') ? raw : path.resolve(cwd, raw));
    // where the statement holding offset `at` starts: after the last `;`, newline or `&` outside quotes and brackets (a `;;` or `&&` is none); an `&&`
    // or `||` before the word in its statement leaves a cd put there after `&&`, which the text rules out, so such a row needs a hand twin
    const stmtStart = (cmd, at) => {
      let q = null; let depth = 0; let start = 0; let andOr = false;
      for (let i = 0; i < at; i++) {
        const c = cmd[i];
        if (q) { if (c === '\\' && q !== "'") i++; else if (c === q) q = null; continue; }
        if (c === '\\') { i++; continue; }
        if (c === "'" || c === '"' || c === '`') { q = c; continue; }
        if (c === '(' || c === '{') { depth++; continue; }
        if (c === ')' || c === '}') { depth--; continue; }
        if (depth) continue;
        if (c === '\n' || (c === ';' && cmd[i + 1] !== ';' && cmd[i - 1] !== ';') || (c === '&' && cmd[i + 1] !== '&' && cmd[i - 1] !== '&' && cmd[i - 1] !== '>' && cmd[i + 1] !== '>')) { start = i + 1; andOr = false; continue; }
        if ((c === '&' && cmd[i + 1] === '&') || (c === '|' && cmd[i + 1] === '|')) { andOr = true; i++; }
      }
      if (andOr) throw new Error('an `&&` or `||` stands before the word in its statement, so the cd needs a hand twin');
      while (cmd[start] === ' ') start++;
      return start;
    };
    // a pattern spelled as one name it matches: `*` none, `?` one letter, a class its first member (zsh's `[!]` and `[^]` one letter)
    const depattern = (t) => {
      let o = '';
      for (let i = 0; i < t.length; i++) {
        const c = t[i];
        if (c === '*') continue;
        if (c === '?') { o += 'x'; continue; }
        if (c === '[') {
          let j = i + 1;
          const neg = t[j] === '!' || t[j] === '^';
          if (neg) j++;
          if (neg && t[j] === ']') { o += 'x'; i = j; continue; }
          const first = j;
          if (t[j] === ']') j++;
          while (j < t.length && t[j] !== ']') j++;
          if (j < t.length) { o += neg ? 'x' : t[first]; i = j; continue; }
        }
        o += c;
      }
      return o;
    };
    const valueRead = (cmd, name) => { const m = cmd.match(new RegExp(`\\bread\\s+${name}\\s*<<<\\s*([^\\s;]+)`)) || cmd.match(new RegExp(`\\bread\\s+${name}\\s*<<EOF\\n([^\\n]*)\\nEOF`)) || cmd.match(new RegExp(`(?:^|[;\\s])${name}=([^\\s;'"$]+)`)); return m ? m[1] : null; };
    const onPath = (prog) => { if (prog.includes('/')) return prog; for (const d of String(process.env.PATH || '').split(':')) { const p = path.join(d || '.', prog); try { fs.accessSync(p, fs.constants.X_OK); if (fs.statSync(p).isFile()) return p; } catch { /* the next directory */ } } return null; };
    const literalOf = (cmd, head) => {
      const m = head.match(/^"?\$\{?([A-Za-z_][A-Za-z0-9_]*)\}?"?$/);
      if (!m) throw new Error(`the command name ${head} is no variable`);
      const p = onPath(valueRead(cmd, m[1]) || 'true');   // the value the row reads into it, or `true` where it reads none
      if (!p) throw new Error(`the value of ${head} is no program on PATH`);
      return p;
    };
    const stripChdirs = (t) => { let prev; do { prev = t; t = t.replace(/(\b(?:env|sudo)\b)\s+(?:-[CD]\s*(?:"[^"]*"|'[^']*'|[^\s;|&]+)|--chdir(?:=|\s+)(?:"[^"]*"|'[^']*'|[^\s;|&]+))/, '$1'); } while (t !== prev); return t; };
    let twinSerial = 0;
    const BUILD = {
      dir: (cmd, l, cwd) => { const raw = refusedWord(l); return splice(cmd, lastAt(cmd, raw), raw, absOf(raw, cwd)); },
      'dir-q1': (cmd, l, cwd) => {
        const raw = refusedWord(l);
        const head = (l.match(/ its command named by `([^`]+)` names /) || [])[1];
        const at = lastAt(cmd, raw);
        const hAt = lastAt(cmd, head, at);
        const out = raw.startsWith('-') ? cmd : splice(cmd, at, raw, absOf(raw, cwd));   // an option is not a path: the literal command reads it as its own
        return splice(out, hAt, head, literalOf(cmd, head));
      },
      notlit: (cmd, l) => { const raw = refusedWord(l); return splice(cmd, lastAt(cmd, raw), raw, `${w.OUT}/scratch/twin-${++twinSerial}.txt`); },
      'notlit-compare': (cmd) => { const m = cmd.match(/\[\[\s+(\S+)\s+>\s+(\S+)\s+\]\]/); if (!m) throw new Error('no `[[ a > b ]]` comparison to write with expr'); return cmd.replace(m[0], `expr ${m[1]} \\> ${m[2]}`); },
      home: (cmd, l) => { const raw = refusedWord(l); const m = raw.replace(/^"|"$/g, '').match(/^(?:~|\$HOME|\$\{HOME\})(\/.*)$/); if (!m) throw new Error(`${raw} is no path through HOME`); return splice(cmd, lastAt(cmd, raw), raw, w.HOME + m[1]); },
      'patternHead-dir': (cmd, l, cwd) => { const raw = refusedWord(l); const at = lastAt(cmd, raw); const s = stmtStart(cmd, at); const out = splice(cmd, at, raw, depattern(raw)); return `${out.slice(0, s)}cd '${cwd}'; ${out.slice(s)}`; },
      'patternHead-cap': (cmd, l) => { const raw = refusedWord(l); return splice(cmd, lastAt(cmd, raw), raw, depattern(raw)); },
      'dir-q1-script': (cmd, l, cwd) => { const raw = refusedWord(l); const s = stmtStart(cmd, lastAt(cmd, raw)); return `${cmd.slice(0, s)}cd '${cwd}'; ${stripChdirs(cmd.slice(s))}`; },
      aliasUnread: (cmd, l, cwd) => {
        const head = refusedWord(l);
        const m = cmd.match(new RegExp(`(?:^|[;\\s])(?:cp|mv)\\s+(/[^\\s;]+)\\s+${escapeRe(head)}(?=[\\s;])`));
        if (!m) throw new Error(`no literal source the binding ${head} stands for`);
        const at = lastAt(cmd, head);
        const out = splice(cmd, at, head, m[1]);
        const from = at + m[1].length;
        const tail = out.slice(from).search(/[;|&\n]/);
        const end = tail < 0 ? out.length : from + tail;
        return out.slice(0, from) + out.slice(from, end).replace(/(^|\s)([^\s'"$~/-][^\s]*\/[^\s]*)/g, (all, sp, p) => `${sp}${path.resolve(cwd, p)}`) + out.slice(end);
      },
      boundName: (cmd, l) => { const raw = refusedWord(l); const m = cmd.match(/(?:^|[;\s])cp\s+(\/[^\s;]+)\s/); if (!m || !onPath(m[1])) throw new Error('no literal program copied into place'); return splice(cmd, lastAt(cmd, raw), raw, m[1]); },
      piped: (cmd) => { const m = cmd.match(/\b(nohup|setsid|nice) \$e ('[^']*')/); const v = valueRead(cmd, 'e'); const c = [...cmd.matchAll(/\|\s*(bash|cat)\b/g)].pop(); if (!m || !v || !c) throw new Error('no `$e` the row reads, or no consumer'); return `${m[1]} ${v} ${m[2]} | ${c[1]}`; },
    };
    BUILD['filled-piped'] = BUILD.piped;
    // the hand twins: the remedy applied by hand where the text asks for a value the row does not give (the word or the program it stands for)
    const HAND = {
      // the re-pinned filled witnesses (item 3 split out): the word spelled out as the program it stands for, allowed where that program writes nothing
      // tracked (python3 on an untracked script), refused by name where it does (tee on the tracked report)
      'AS3-nohup-bg': 'nohup python3 {OUT}/scratch/x.py --outdir {OUT}/res > {OUT}/log 2>&1 &',
      'AS3-setsid-bg': 'setsid python3 {OUT}/scratch/x.py --outdir {OUT}/res > {OUT}/log 2>&1 &',
      'AS3-nohup-name': 'nohup tee docs/report.md < /dev/null',
      'AS3-setsid-name': 'setsid -w tee docs/report.md < /dev/null',
      'AS3-nohup-name-out': 'nohup tee {NA}/docs/report.md < /dev/null',
      'AS3-option-abbrev': 'nice --adjustment=5 cp base/report.md docs/other.md',
      'AS8-armed-mv-untracked': 'read X <<< {OUT}/scratch; mv {OUT}/scratch/keep.md {OUT}/scratch/c2; PATH=$X:$PATH; /usr/bin/cp base/report.md docs/other.md',
      'AS8-armed-c2-unread-source': 'read X <<< {OUT}/scratch; cp "$(command -v cp)" {OUT}/scratch/c2; PATH=$X:$PATH; /usr/bin/cp base/report.md docs/report.md',
      'AS8-unread-source-mv-head': 'mv "$S" {NA}/scratch/c2; /usr/bin/cp {NA}/base/report.md {NA}/docs/other.md',
      'AS8-unread-source-cat-head': 'cat "$S" > {NA}/scratch/c2; /usr/bin/cp {NA}/base/report.md {NA}/docs/other.md',
      'AS6-script-eval-in-text': 'eval "true; true" --seed 3',
      'AS6-script-eval-in-text-after-source': 'source {OUT}/scratch/keep.md; eval "true; true" --seed 3',
      'AS6-script-eval-in-text-path-after-source': 'source {OUT}/scratch/keep.md; eval "true; tee" {NA}/scratch/a.txt',
      'AS6-script-eval-in-text-after-cd-var': 'read d <<< docs; cd "$d"; eval "true; true" --seed 3',
      'AS3-option-unheld-short': 'cp base/report.md docs/other.md',
      // the alias-operand clause's twins (fork PR 975's item 8 as ruled): the alias operand spelled out so no unread name is bound, the command it stood
      // for written with absolute paths (AS8-alias-unread-operand-cp: cp onto the tracked report, refused by name), or the later command run clean
      // (AS8-cost-alias-unread-operand: ls, allowed)
      'AS8-alias-unread-operand-cp': 'cp {NA}/base/report.md {NA}/docs/report.md',
      // THE OLDER ARITHMETIC's two readings (the text lens's tg-t12-1): the target an eval's text spells, its quotes splitting the dollar from the bracket in
      // the command itself, spelled out as the absolute path bash and zsh write (refused by name, the tracked report)
      'AS8-root-old-arith-text-eval-out': "mkdir -p 0; eval 'echo y > {NA}/docs/report.md'",
      'AS8-cost-alias-unread-operand': 'alias ll; ls docs',
      'AS3-option-unheld-long': 'cp base/report.md docs/other.md',
      'AS3-option-unheld-numactl': 'cp base/report.md docs/other.md',
      'AS8-builtin-nonbuiltin-after-backup': 'read X <<< {OUT}/scratch; cp /usr/bin/cp {OUT}/scratch/x; cp -b /usr/bin/true {OUT}/scratch/x; PATH=$X:$PATH; /usr/bin/ls docs',
      'AS8-backup-after-cd': 'read d <<< .; read X <<< {OUT}/scratch; cp /usr/bin/cp {OUT}/scratch/x; cp -b -S zz /usr/bin/true {OUT}/scratch/x; PATH=$X:$PATH; cd "$d"; /usr/bin/true {NA}/base/report.md {NA}/docs/report.md',
      // THE SHELL'S GATE's rows (the seventh verify round's tg-m7-1, tg-m7-4, tg-m7-5): the refused echo spelled by its program's full path; the rows refused
      // first at a gate word, a keyword or a builtin no program stands for (item 8 as ruled) take M2's no-remedy form and need no twin
      'AS8-builtin-gate-before-path': "printf 'cp base/report.md docs/report.md\\n' > {OUT}/scratch/s.sh; cat {OUT}/scratch/s.sh > {OUT}/scratch/echo; chmod +x {OUT}/scratch/echo; enable -n echo; read X <<< {OUT}/scratch; PATH=$X:$PATH; /usr/bin/echo",
      'AS8-builtin-gate-ansic-before-path': "printf 'cp base/report.md docs/report.md\\n' > {OUT}/scratch/s.sh; cat {OUT}/scratch/s.sh > {OUT}/scratch/echo; chmod +x {OUT}/scratch/echo; $'\\x65nable' -n echo; read X <<< {OUT}/scratch; PATH=$X:$PATH; /usr/bin/echo",
      'AS8-builtin-gate-mention-cost': `${BACKED_X}/usr/bin/echo enable`,
      'AS8-root-gate-unheld-callback': 'cp {OUT}/scratch/keep.md {OUT}/scratch/b.service; mapfile -C "$(cat {OUT}/scratch/keep.md)" -c 1 a < {OUT}/scratch/keep.md; grep -c PATH {OUT}/scratch/b.service; /usr/bin/ls docs',
      // dash's `%builtin` road (R2's correctness-3 closures): the written script's name spelled by the program's full path, which runs no lookup
      ...Object.fromEntries([['echo', 'echo x'], ['printf', 'printf x'], ['test', 'test -n x']].map(([n, call]) => [`AS8-builtin-dash-pctbuiltin-${n}`, `printf '/usr/bin/cp {NA}/base/report.md {NA}/docs/report.md\\n' > {OUT}/s.sh; cat {OUT}/s.sh > {OUT}/scratch/${n}; chmod +x {OUT}/scratch/${n}; printf '%s\\n' {OUT}/scratch > {OUT}/p; read X < {OUT}/p; PATH=$X:%builtin:$PATH; /usr/bin/${call}`])),
      'AS8-builtin-dash-pctbuiltin-dash-c': "printf '/usr/bin/cp {NA}/base/report.md {NA}/docs/report.md\\n' > {OUT}/s.sh; cat {OUT}/s.sh > {OUT}/scratch/echo; chmod +x {OUT}/scratch/echo; printf '%s\\n' {OUT}/scratch > {OUT}/p; dash -c 'read X < {OUT}/p; PATH=$X:%builtin:$PATH; /usr/bin/echo x'",
      'AS8-root-gate-walk-ansic': "cp {OUT}/scratch/keep.md {OUT}/scratch/b.service; $'\\x65nable' -n echo; grep -c PATH {OUT}/scratch/b.service; /usr/bin/ls docs",
      // a script written into place as echo and run by its bare name, refused since fork PR 975's round 2 (R2): the program's full path in place of the name
      'AS8-builtin-noenable-script': "printf 'cp base/report.md docs/report.md\\n' > {OUT}/scratch/s.sh; cat {OUT}/scratch/s.sh > {OUT}/scratch/echo; chmod +x {OUT}/scratch/echo; read X <<< {OUT}/scratch; PATH=$X:$PATH; /usr/bin/echo",
      'AS8-builtin-slash-env-echo': `${STASHED_ECHO}/usr/bin/env /usr/bin/echo base/report.md docs/report.md`,
      'AS8-builtin-slash-nohup-echo': `${STASHED_ECHO}/usr/bin/nohup /usr/bin/echo base/report.md docs/report.md`,
      'AS8-builtin-bound-env-echo': `cp /usr/bin/env {OUT}/scratch/e2; ${STASHED_ECHO}{OUT}/scratch/e2 /usr/bin/echo base/report.md docs/report.md`,
      'AS8-builtin-quoted-echo-cost': `${STASHED_ECHO}/usr/bin/echo base/report.md docs/report.md`,
      // the held options' long forms, the empty name's wrapper dropped, and the refused options' commands spelled without them (tg-m7-7, tg-m7-8)
      'AS3-option-held-flag': 'env --debug cp base/report.md docs/other.md',
      'AS3-option-held-opt': 'env --block-signal=INT cp base/report.md docs/other.md',
      'AS3-option-held-script': "flock {OUT}/scratch/lk --command='cp base/report.md docs/other.md'",
      'AS3-option-held-piped': "nice --adjustment=5 echo 'cp ../base/report.md report.md' | bash",
      'AS3-option-unheld-empty-name': 'cp base/report.md docs/other.md',
      'AS3-option-refuse-abbrev-env': 'cp base/report.md docs/report.md',
      'AS3-option-refuse-abbrev-sudo': 'tee docs/other.md < /dev/null',
      // THE BOUND NAME's writers into a directory with no `cp` of a literal program to name (C): the program's full path in place of the name
      'AS8-into-dir-install': 'install {W}/tools/w2 {OUT}/scratch; PATH={OUT}/scratch:$PATH; {W}/tools/w2',
      'AS8-into-dir-ln': 'ln {W}/tools/w2 {OUT}/scratch; PATH={OUT}/scratch:$PATH; {W}/tools/w2',
      'AS8-into-dir-ln-s': 'ln -s {W}/tools/w2 {OUT}/scratch; PATH={OUT}/scratch:$PATH; {W}/tools/w2',
      'AS8-into-dir-mv': 'dd if={W}/tools/w2 of={OUT}/w2 status=none; chmod +x {OUT}/w2; mv {OUT}/w2 {OUT}/scratch; PATH={OUT}/scratch:$PATH; {W}/tools/w2',
      // fork main's own refusals (item 8 as ruled, the cost rows) and the makers with no `cp` of a literal program to name: the program's full path in place
      // of the name, as the remedy says
      'AS8-cost-into-dir-T': 'cp -T {W}/tools/w2 {OUT}/scratch/w5; PATH={OUT}/scratch:$PATH; {W}/tools/w2',
      'AS8-cost-unread-path-other-name': 'cp "$(command -v cp)" {OUT}/scratch/c2; PATH=$X:$PATH; /usr/bin/ls docs',
      'AS8-cost-one-op-ln-s-other-name': 'ln -s {W}/tools/w2; PATH={NA}/scratch:$PATH; /usr/bin/cat {NA}/docs/report.md',
      'AS8-made-nonlit-into-dir': 'read S <<< {W}/tools/w2; cp "$S" {OUT}/scratch; PATH={OUT}/scratch:$PATH; {W}/tools/w2',
      'AS8-made-one-op-ln-s-alone': 'ln -s {W}/tools/w2; PATH={NA}/scratch:$PATH; {W}/tools/w2',
    };
    const trackedNamed = (reason) => {
      const m = line1(reason).match(/^Track-changes is ON for (.+?), so this command is blocked here/);
      if (!m) return false;
      return [path.join(w.NA, 'docs', 'report.md'), path.join(w.WEB, 'docs', 'report.md'), path.join(w.NA, 'figs', 'plot.png')].includes(m[1]) || [w.NA, w.WEB].some((r) => m[1].startsWith(path.join(r, 'notes') + path.sep));
    };
    const lifted = (h) => (h.status === 0 ? 'allow' : h.status === 2 && trackedNamed(h.reason) ? 'name' : null);
    const settle = (id, cwd, cmd0, reason0) => {
      if (Object.hasOwn(HAND, id)) {
        const cmd = w.fill(HAND[id]);
        const h = w.hook(cmd, cwd);
        const v = lifted(h);
        if (!v) throw new Error(`its hand twin is not lifted: ${cmd}: ${line1(h.reason)}`);
        return { how: 'hand', verdict: v, steps: 1 };
      }
      let cmd = cmd0;
      let reason = reason0;
      for (let step = 1; step <= 4; step++) {
        const k = kindOf(reason);
        if (!Object.hasOwn(BUILD, k)) throw new Error(`no hand twin, and the ${k} refusal ${step > 1 ? 'its twin met' : 'it carries'} is no rewrite: ${line1(reason)}`);
        cmd = BUILD[k](cmd, line1(reason), cwd);
        const h = w.hook(cmd, cwd);
        const v = lifted(h);
        if (v) return { how: 'mech', verdict: v, steps: step };
        if (h.status !== 2 || line1(h.reason) === line1(reason)) throw new Error(`its remedy did not lift the refusal: ${cmd}: ${line1(h.reason)}`);
        reason = h.reason;
      }
      throw new Error(`its twin is still refused after four remedies: ${cmd}`);
    };
    // M2_STANDS (fork PR 975's round 2, tests-5): the census's one stated exception, a cost whose refusal no kind classifies and whose remedy does not lift
    // it, each row with the directory its refusal asks to make readable. The here-document placeholder (AS8-cost-old-arith-heredoc-placeholder-out,
    // decision 47 beside the cost) names a path holding the blank that stood for the expansion and an error of the directory check's own, and the
    // directory is readable already, so the remedy changes nothing; the check below asserts the refusal stands after it, so the follow-up that reads
    // the placeholder turns this pin red and the row leaves the exception
    const M2_STANDS = { 'AS8-cost-old-arith-heredoc-placeholder-out': '{OUT}/scratch' };
    const refusedKinds = {};
    for (const [id, r] of Object.entries(reasonAt)) {
      if (r.status !== 2 || Object.hasOwn(M2_STANDS, id)) continue;
      const k = kindOf(r.reason);
      assert.ok(k !== 'unclassified', `${id}: the M2 census classifies every refused row, not: ${line1(r.reason)}`);
      (refusedKinds[k] = refusedKinds[k] || []).push(id);
    }
    const rowOf = Object.fromEntries(all.map((r) => [r[0], r]));
    assert.deepEqual(Object.keys(M2_STANDS).filter((id) => !reasonAt[id] || reasonAt[id].status !== 2), [], 'every row M2_STANDS names is a refused row of this test');
    for (const [id, dirKey] of Object.entries(M2_STANDS)) {
      w.build();
      const dir = w.fill(dirKey);
      fs.accessSync(dir, fs.constants.R_OK | fs.constants.X_OK);
      fs.readdirSync(dir);   // the remedy, the directory read in a command of its own: it is readable
      const h = w.hook(w.fill(rowOf[id][2]), w.cwds[rowOf[id][1]]);
      assert.ok(h.status === 2 && line1(h.reason) === line1(reasonAt[id].reason) && line1(h.reason).includes(`I could not check ${dir} on that path`) && kindOf(h.reason) === 'unclassified', `${id}: M2_STANDS holds a refusal no kind classifies that stands after its remedy (${dir} readable): ${line1(h.reason)}`);
    }
    const capIds = new Set(capRows.map((r) => r[0]));
    const twinFailures = [];
    const tally = {};
    for (const crowded of [false, true]) {
      w.build();
      if (crowded) crowd();
      for (const [k, ids] of Object.entries(refusedKinds)) for (const id of ids) {
        if (capIds.has(id) !== crowded) continue;
        const reason = reasonAt[id].reason;
        if (NO_REMEDY.has(k)) { if (!keepsNoRemedy(k, line1(reason))) twinFailures.push(`${id}: the ${k} refusal offers no remedy, so its first line ends with its cause and the track-edit sentence alone: ${line1(reason)}`); continue; }
        if (!Object.hasOwn(REMEDY, k)) { twinFailures.push(`${id}: ${k} is neither a remedy-offering kind nor a stated no-remedy kind`); continue; }
        const want = typeof REMEDY[k] === 'function' ? REMEDY[k](line1(reason)) : REMEDY[k];
        if (remedyOf(reason) !== want) { twinFailures.push(`${id}: the ${k} refusal names one remedy, (${want}), not (${remedyOf(reason)})`); continue; }
        const t = (tally[k] = tally[k] || { rows: 0, mech: 0, hand: 0, allow: 0, name: 0, chained: 0, chainedIds: [] });
        t.rows++;
        try {
          const r = settle(id, w.cwds[rowOf[id][1]], w.fill(rowOf[id][2]), reason);
          t[r.how]++; t[r.verdict]++;
          if (r.steps > 1) { t.chained++; t.chainedIds.push(id); }
        } catch (e) { twinFailures.push(`${id} (${k}): ${String(e.message).split('\n')[0]}`); }
      }
    }
    assert.deepEqual(twinFailures, [], `every refused row of a remedy-offering kind names its kind's one remedy and has a twin that lifts it (${twinFailures.length} do not)`);
    const remedyKinds = Object.keys(tally).sort();
    const noRemedyKinds = Object.keys(refusedKinds).filter((k) => NO_REMEDY.has(k)).sort();
    assert.ok(remedyKinds.length >= 10 && Object.values(tally).every((t) => t.rows > 0 && t.rows === t.mech + t.hand), `the M2 census twins each refused row of the remedy-offering kinds (saw ${remedyKinds.join(', ')})`);
    console.log(`# M2 over every row: ${remedyKinds.map((k) => `${k} ${tally[k].rows} (twins ${tally[k].mech} mechanical, ${tally[k].hand} by hand; ${tally[k].allow} allowed, ${tally[k].name} by name; ${tally[k].chained} after a second refusal${tally[k].chained ? `: ${tally[k].chainedIds.join(', ')}` : ''})`).join('; ')}; no-remedy kinds ${noRemedyKinds.map((k) => `${k} ${refusedKinds[k].length}`).join(', ')}`);
    // an abbreviation of each long option a wrapper's table refuses outright (its last letter dropped) takes that option's own refusal, its remedy the
    // command without it, asked of the guard from the tracked root (the seventh verify round's tg-m7-7: the long form named as its remedy was refused in
    // its turn); the population read from the table, the census failing on none
    const refuseAbbrevs = optKeys.flatMap((k0, i0) => { const body = optBody.slice(k0.at, i0 + 1 < optKeys.length ? optKeys[i0 + 1].at : optBody.length); const m = body.match(/refuse: \{[^}]*long: \[([^\]]*)\]/); return m ? [...m[1].matchAll(/'([a-z-]+)'/g)].map((x) => [k0.name, x[1].slice(0, -1)]) : []; });
    assert.ok(refuseAbbrevs.length > 1, 'the census reads the refused long options from the table');
    w.build();
    for (const [wr, ab] of refuseAbbrevs) {
      const h = w.hook(`${wr} --${ab} cp base/report.md docs/other.md`, w.cwds.na);
      assert.ok(h.status === 2 && kindOf(h.reason) === 'opaque' && remedyOf(h.reason) === `Spell the command without \`${wr} --${ab}\``, `\`${wr} --${ab}\`, an abbreviation of an option the table refuses, takes that option's own refusal: ${line1(h.reason)}`);
    }
    // where the code lives (the rows above prove what it does; each pin names the rows that red without it)
    const hook = fs.readFileSync(HOOK, 'utf8');
    assert.ok(hook.includes('function formsPattern(w) {') && hook.includes('if (!formsPattern(w)) return [word(text, true, w.raw)];') && hook.includes('if (w.glob) return !cwdKnown && formsPattern(w);'), 'a word is a pattern only where it forms one, a class closing past a slash and a `[!]` or `[^]` among them, asked by expandGlob and mayVanish (behaviour: AS1-*-after-*, AS1-side-lone-bracket, AS1-armed-class-across-slash, AS1-armed-neg-class-*, AS1-armed-caret-class-source)');
    assert.ok(hook.includes("else { const j = parenCloses(lexScopes); if (j >= 0) lexScopes.length = j; else if (lexScopes.includes('case')) marker.pattern = true; }") && hook.includes('if (marker.pattern) markPatternList();'), "THE CASE PATTERN is marked beside the paren rule's line, which stands as it was (behaviour: AS2-pending-*, AS2-later-*)");
    assert.ok(/if \(seg\.casePattern\) \{\n\s+recurseSubs\(seg\);\n\s+for \(const v of seg\.viaSubs\) recurse\(v\.text, shell, false, v\.via\);\n\s+runPromptExpansions\(seg\);\n\s+taintArith\(seg\);\n\s+for \(const w of seg\.words\) taintAssigningExpansions\(w\);\n\s+continue;\n\s+\}/.test(hook), 'a pattern word is no command, and its expansions still run and assign (behaviour: AS2-armed-brace-cmdsub*, AS2-armed-arith-*, AS2-armed-zsh-assign, AS2-armed-prompt)');
    // M1 (the mechanism ruling): the road is RESTORED behind any wrapper (T3-4's every-wrapper line is gone; T2-7's filled-head line went with item 3's
    // split), and the names stay readable only when at least one external wrapper precedes the head (behindExternal)
    assert.ok(!hook.includes('WRAPPER_OPT[n].external === true)) unreadHead = null;'), 'the road is restored behind any wrapper: the every-wrapper-external line that dropped it is gone (behaviour: AS3-nohup-dd-moves, AS3-chain-command-nohup-road, AS3-link-nohup-dd-rel, AS3-link-env-dd-rel, AS3-road-* refused as a directory not known)');
    assert.ok(hook.includes('const behindExternal = !!cmd.wrapped && cmd.wrappers.some((n) => Object.hasOwn(WRAPPER_OPT, n) && WRAPPER_OPT[n].external === true);') && hook.includes("if (unreadHead && !behindExternal && seg.op !== '|' && seg.op !== '&') unreadPoison = "), 'the names stay readable when at least one external wrapper precedes the head (behaviour: AS3-nohup-dd-no-poison, AS3-env-dd-no-poison, AS3-chain-command-nohup-no-poison, AS3-chain-nohup-command-no-poison; and poisoned behind a wrapper the shell runs itself: AS3-kept-time-dd and the other kept rows)');
    assert.ok(hook.includes('if (unreadHead && cmd.writes && cmd.writes.length) { const at = dirNow(); unreadHeadWrites = () => fromDir(at, () => wrapperWrites(cmd)); }') && hook.includes('if (unreadHeadWrites) unreadHeadWrites();'), 'a `time -o FILE` before a command named by a variable is judged before its road moves the directory (behaviour: AS3-time-o-rel-*-dashdash-out, AS3-ctl-time-o-dashdash-untracked)');
    assert.ok(hook.includes('if (unknownDir && !path.isAbsolute(w.text)) w = word(w.text, true, w.raw);') && hook.includes('else { const u0 = unresolved.length; cannotRead(w, how); for (const u of unresolved.splice(u0)) { u.q1 = q1; q1Unresolved.push(u); } return; }'), 'a pattern operand the guard cannot expand is judged by its spelling, or refused past the caps (behaviour: AS4-*-glob, AS4-cap-*)');
    assert.ok(hook.includes("    if (unreadPoison && !frames.some((f) => f.kind === 'function' && !f.running && !f.coproc)) { headPoison.seen = true; if (!headPoison.off) poison(unreadPoison, true); }\n    recordSegment(seg, idx, cmd, preWords);"), 'the poison of a command named by a variable is applied just before recordSegment, never in the body of a function being defined, the first walk taking it and the second setting it aside (behaviour: AS5-semi, AS5-newline, AS5-before, AS5-ctl-bg, AS5-ctl-pipe; AS5-uncalled-no-poison, AS5-called-poison; the second walk: AS5-read-through-*, AS5-dual-*)');
    // the "nothing more" (`!f.otherPoison`) reds no row since fork PR 975's round 2 (R5, THE ORDER): the walk with the head's poison set aside, judge's first,
    // keeps a `source`'s poison inside the subshell on its own, so that conjunct only chose which text AS5-subshell-source-poison showed (verified by its
    // mutant: no row changes); this pin is what holds it
    assert.ok(hook.includes("if (f.headPoison && !f.otherPoison && (f.kind === 'subshell' || f.coproc)) { varsPoisoned = false; poisonWhy = null; }") && hook.includes('if (!varsPoisoned) { varsPoisoned = true; poisonWhy = why; if (sub && fromHead) sub.headPoison = true; }'), "a subshell's close ends THE UNREAD HEAD's poison taken inside it and nothing more (behaviour: AS5-subshell-no-poison, AS5-subshell-bg-no-poison, AS5-subshell-poison-inside; the nothing more is held by this pin alone)");
    // THE TWO WALKS (item 8 as ruled, DUAL): judge walks a command that met such a head with its poison set aside as well as taken, any refusal of either
    // walk standing, and the switch reaches the top-level walk and every text through recurse; the read-through's sites are gone with it. THE ORDER (fork
    // PR 975's round 2, R5 (ii)): the walk with the poison set aside, `$[` read as text, is the first, and the walks that take the poison run only when it
    // allows (behaviour for the order: the shapes test's THE ORDER, red where the poisoned walk runs first; for the poison taken: AS5-semi, AS5-newline,
    // AS5-before and the other AS5 poison rows, red where the walk that takes it is skipped)
    assert.ok(hook.includes('const names = { off: true, seen: false };') && hook.includes('const r0 = judgeWalk(command, cwd, names, closures);') && hook.includes('if (r0 != null) return r0;') && hook.includes('if (!names.seen) return null;') && hook.includes('return judgeWalk(command, cwd, { off: false, seen: false }, closures);') && hook.includes('if (r1 != null || !first.seen) return r1;') && hook.includes('return judgeWalk(command, cwd, { off: true, seen: false }, closures);') && hook.includes("builtinsOff, ruleSafe, headPoison: headPoison || { off: false, seen: false }, headGate });") && hook.includes('bound, builtinsOff, headPoison, headGate, aliasChain: chain,'), "THE TWO WALKS: a command after a command named by a variable is walked with that head's poison set aside, first, and with it taken, any refusal of either walk standing, the switch carried into every text (behaviour: AS5-read-through-*, AS5-dual-* with AS5-dual-head-in-cmdsub-out for the texts, the controls AS5-ctl-read-through-untracked-out and AS5-dual-ctl-untracked-held-out; the order: the shapes test's THE ORDER)");
    assert.ok(!/prePoisonOf|readThroughPoison|headPoisonOnly|preVars|heldOld|holdPre|preHome|real: false/.test(hook), 'no read-through site survives beside the two walks');
    // THE OLDER ARITHMETIC's two readings (fork PR 975's round 1, the text lens's tg-t12-1): judge reads a command whose walk met a `$[` both ways, both
    // walks each, with the `$[` read as a dollar and text and as arithmetic, any refusal of either reading standing. Since THE ORDER (fork PR 975's round
    // 2, R5 (ii)) the text reading's walk with the poison set aside is judge's first walk, the lexer noting a `$[` under either reading before it chooses,
    // and the arithmetic reading runs only where that walk allows and noted one (behaviour: AS8-root-old-arith-text-*, red where the text reading is off
    // or reads it as arithmetic too; the arithmetic reading's rows, AS8-root-old-arith-path-* and the other AS8-root-old-arith-* rows bash and zsh write,
    // red where the note is taken after the text reading's return or the arithmetic reading is skipped; under bash's grammar,
    // AS8-root-old-arith-text-bash-c-out; both walks of the text reading, AS8-root-old-arith-text-two-walks-out; the control
    // AS8-ctl-old-arith-text-target-out, which both readings allow); and the reading is put back when judge returns, so a later lex in the same process
    // reads `$[` as arithmetic again (executed below: red where judge leaves the text reading in place)
    assert.ok(hook.includes("if (oldArithReading) oldArithReading.met = true;\n    if (oldArithReading && oldArithReading.text) return { kind: 'dollar', len: 1 };") && hook.includes('const met = oldArithReading.met;') && hook.includes('if (met) {') && hook.includes('oldArithReading = { text: false, met: false };') && hook.includes('oldArithReading = { text: true, met: false };') && hook.includes('} finally { oldArithReading = prev; }'), "THE OLDER ARITHMETIC's two readings: the lexer notes a `$[` under either reading, before the text reading's return, judge reads every command with it read as text first and a command that met one again as arithmetic, any refusal standing (behaviour: AS8-root-old-arith-text-*, the arithmetic reading's AS8-root-old-arith-* rows, bash's grammar in AS8-root-old-arith-text-bash-c-out and both walks in AS8-root-old-arith-text-two-walks-out, the control AS8-ctl-old-arith-text-target-out)");
    w.build();
    assert.equal(guard.evaluate(JSON.stringify({ tool_name: 'Bash', tool_input: { command: w.fill('echo y > {OUT}/scratch/n$[1+1].md') }, cwd: w.cwds.out })), null, 'a `$[` in a target outside every project is allowed in process, both readings run');
    assert.deepEqual(guard.lex('echo $[p=0]').segments.map((g) => g.arith), [['p=0']], 'after judge read a command both ways, a `$[` is arithmetic again for the next lex in the process (the reading is put back)');
    assert.ok(hook.includes('const held = unknownDir && heldDir && heldDir.real ? heldDir.dir : null;') && hook.includes('for (const d of [u.dir, u.held, cwd]) {') && hook.includes('linkUnknown(why);   // the program cannot move this shell'), 'THE HELD DIRECTORY: the shell\'s own directory, which a program behind an external wrapper did not move, puts its project in play for a relative write (behaviour: AS3-nohup-dd-held-out, AS3-nohup-dd-positional-out, and through each frame and text that saves and restores it, AS3-nohup-dd-held-*-out and AS3-env-dd-held-*-out)');
    assert.ok(hook.includes("{ let at = dirNow(); if (cmd.chdirs && cmd.chdirs.length) fromDir(at, () => { enterChdirs(cmd); at = dirNow(); }); unreadOperandsAtHead = () => fromDir(at, "), "the operands of a command named by a variable are judged in the wrappers' directory (behaviour: AS3-envC-dashdash-name, AS3-envC-nohup-dashdash-name, AS3-envC-var-dashdash-dir)");
    assert.ok(hook.includes('wrapperWrites(cmd.unknown);') && hook.includes('wrapperWrites(cmd.opaque);') && hook.includes("if ('script' in cmd) {   // `flock … -c 'string'` runs the string through `$SHELL -c`, read like `sh -c` (round 4)\n      wrapperWrites(cmd);"), 'a `time -o FILE` before a wrapper option the guard does not read, an opaque option or a flock string is still a write (behaviour: AS3-time-o-nice-out, AS3-time-o-nice-command-out, AS3-time-o-envS-out, AS3-time-o-flock-na, AS3-time-o-rel-later-envC-out)');
    assert.ok(hook.includes("      fromDir(dirNow(), () => {\n        enterChdirs(cmd);\n        for (const t of scriptTexts(cmd.script, "), "flock's string is read behind the wrappers' chdirs (behaviour: AS3-envC-flock-script, AS3-envchdir-flock-script, AS3-sudoD-flock-script, AS3-envC-var-flock-script-dir)");
    assert.ok(hook.includes('if (c.again) { setUnknown(') && hook.includes('again: chdirs.some((c) => c.inv === wrappers.length) })'), 'a second chdir option in one env or sudo invocation leaves the directory not known (S4-1; behaviour: AS3-envC-rpt-*; the nested rows, the allowed controls AS3-ctl-envC-nested-chain and AS3-ctl-envC-nested-flock-untracked and the row refused by name AS3-envC-nested-flock, each red when `again` counts a chdir of an earlier invocation; and AS3-envC-flock-script, a single-chdir row refused by name, red when `again` is always set)');
    assert.ok(hook.includes("const boundWhy = pathValue != null ? null : { kind: 'boundName', text: `\\`${hw.raw}\\` is looked up through a PATH I do not read here, and this command made a path by copying, moving or linking, or by writing it, so which file it names is not known` };") && hook.includes("if (boundWhy) cannotRead(hw, 'command name', noRemedy ? { ...boundWhy, noRemedy } : boundWhy);") && !/ALL_SHELL_BUILTINS|shellRuns|DROP_WRAPPERS|builtinsOff\.given/.test(hook) && !/sameName|madePaths|boundBackup|madeOff|UNMODELED_FILE_WRITERS|noteDirSource/.test(hook), "every bare name under a PATH not read refuses once a path is bound, fork main's rule again (item 8 as ruled), the directory known or not, a builtin's or a keyword's name among them (R2: no exemption for a name the three shells run as their own, and no remedy that drops wrapper words), with no remedy where none lifts it; no narrowing to a made name and no list of programs survives (behaviour: AS8-armed-*, AS8-made-*, AS8-into-dir-*, AS8-backup-cp, AS8-backup-after-cd, AS8-builtin-gate-var-enable, the cost rows AS8-cost-*; R2's closures AS8-builtin-shadow-* and AS8-builtin-dash-pctbuiltin-*, red where a builtin's name is exempt; AS8-drop-*, red where a remedy names wrapper words dropped)");
    assert.ok(hook.includes('if (kind !== true) bind(ops[1].text, srcText(ops[0]));') && hook.includes('if (kind !== false && ops[0].text) bind(path.join(ops[1].text, path.basename(ops[0].text)), srcText(ops[0]));'), 'a writer of two operands binds the file it makes in a directory, both readings where the destination\'s kind is not known, the spelling alone under `-T` or onto a file, which a PATH the guard reads finds (behaviour: AS8-into-dir-readable-path, red where DIR/basename(SRC) is not bound)');
    assert.ok(hook.includes("bound.size && pathValueAt(seg, seg.words.length - args.length) == null) cannotRead(op0, `\\`${name}\\` operand`, { kind: 'boundName', noRemedy: true,"), "a name `.` or `source` looks up through a PATH not read refuses once a path is bound, as a bare command name does, with no remedy; since R2 the head `.` or `source` is refused first under the same PATH, so no row reds without this line (AS8-sourced-dot and AS8-sourced-dot-piped name `.` now), which stands behind the head's refusal");
    assert.ok(hook.includes('const noRemedy = !!boundWhy && ((Object.hasOwn(SHELL_WORD_ASSIGNS, bareName) && !programOnPath(bareName)) || definedFunctions.has(bareName));') && hook.includes('const besideNoRemedy = !u.why.noRemedy && list.some((v) => {') && hook.includes('if (u.why.noRemedy || besideNoRemedy) return '), "M2's no-remedy form for a builtin or a reserved word of any of the three shells with no program of its name, and since R2 for a bare name whose command holds another bare name refused with none (behaviour: AS8-sourced-source, AS8-drop-*, the gate rows refused at the gate's own word; AS8-builtin-exec-echo, AS8-builtin-command-echo, AS8-builtin-dash-builtin-stdin, AS8-builtin-gate-while and AS8-builtin-gate-until, red where echo's full-path remedy is not withheld)");
    // THE ASSIGNING HEAD (item 8 as ruled, ROOT): a mention taints only where the head may assign a name it is given, the set derived from the table the
    // census below checks against the shells (behaviour: the rows whose later name is a program, AS8-unit-*, AS8-cp-sed-path-ls and
    // AS8-cp-grep-path-collision, red where every mention taints, and since R2 the session's rows whose later name is echo or printf too, which THE SHELL'S
    // OWN NAME had let pass either way (AS8-cp-grep-path-echo, AS8-cp-echo-path-word, AS8-mv-grep-path-printf); AS8-root-print-v and AS8-root-getln, red where the table drops the word; AS8-root-glob-head, red where a head the guard does not read, a
    // pattern that matches a file named `read`, is taken for a program; AS8-root-unread-head, refused by THE UNREAD HEAD's own road either way)
    assert.ok(hook.includes('const mentions = mentionMayAssign(seg, cmd);') && hook.includes('        if (mentions) taint(t, wroteThrough(t, ') && hook.includes('    return MENTION_TAINT_HEADS.has(cmd.name);') && hook.includes("export const MENTION_TAINT_HEADS = new Set(Object.keys(SHELL_WORD_ASSIGNS).filter((n) => SHELL_WORD_ASSIGNS[n][0] === true));") && hook.includes("if (!hw || !hw.literal || !hw.text || hw.text.includes('\\0')) return true;") && hook.includes('if (builtinsOff.seen || aliasState.unread || aliases.has(cmd.name) || [...aliases.values()].some((a) => a.global || a.suffix)) return true;'), 'THE ASSIGNING HEAD: a mention of a name in a word taints it only under a head that may assign a name it is given (the table, the census below), a wrapped head, a head not read, an alias the command binds (AS8-root-alias-head), a global alias (AS8-root-global-alias), or wherever the command may turn a builtin on');
    // THE ASSIGNING HEAD's function clause: a command that let a mention pass under a head and may define a function of its name, or any function, is
    // walked again with every mention a write, fork main's rule (behaviour: AS8-root-func-later-loop, red where the second walk is off or a `name()`
    // definition is not recorded; AS8-root-func-later-keyword, where a `function name` one is not; AS8-root-func-zsh-autoload, where FUNCTION_SOURCES
    // is not read; AS8-root-func-unread-head-loop, where a poison does not count; AS8-ctl-func-call-unrelated, red where a call of a function the
    // command defines counts as one that may define any); and an alias operand whose `=` an expansion may hold binds a name the guard does not read
    // (AS8-root-alias-unread-operand, red without it)
    assert.ok(hook.includes('  return again ? walk({ off: true, exempted: new Set(), defined: new Set(), anyDefined: false }) : r;') && hook.includes('        else headGate.exempted.add(cmd.name);') && hook.includes('for (const nm of names) { definedFunctions.add(nm); headGate.defined.add(nm); }') && hook.includes('definedFunctions.add(seg.words[q].text); headGate.defined.add(seg.words[q].text);') && hook.includes('    if (defines) headGate.anyDefined = true;') && hook.includes('    if (cmd && FUNCTION_SOURCES.has(cmd.name)) headGate.anyDefined = true;') && hook.includes('    if (headGate.off) return true;') && hook.includes("may assign any name`, false, VAR_POISONERS.has(cmd.name));") && hook.includes("export const FUNCTION_SOURCES = new Set(Object.keys(SHELL_WORD_ASSIGNS).filter((n) => SHELL_WORD_ASSIGNS[n][1].includes('may assign any name')));"), "THE ASSIGNING HEAD's function clause: the second walk, its switch and the sites that record what it reads");
    assert.ok(hook.includes("if (eq < 0) { if ((w.marks && w.marks.includes('x')) || w.text.includes('\\0')) { if (!aliasState.unread) aliasState.unread = w.raw; } continue; }"), 'an alias operand whose `=` an expansion may hold binds a name the guard does not read (AS8-root-alias-unread-operand, AS8-alias-unread-operand-cp, AS8-cost-alias-unread-operand)');
    // the accepted rulings on what survives the item-3 split (fork PR 975 round 1 verify findings, 2026-10-05)
    assert.ok(hook.includes("else if (ops.length === 1 && name === 'ln' && ops[0].text) {") && hook.includes('if (cwd) bind(path.basename(ops[0].text), srcText(ops[0]));'), 'a one-operand ln binds ./basename(SRC), closing shell F2 (the reviewer\'s t8-3; behaviour: AS8-made-one-op-ln-readable-path, red where it binds nothing; AS8-made-one-op-ln-s, AS8-made-one-op-ln, and its cost AS8-cost-one-op-ln-s-other-name)');
    // THE SHELL'S GATE, kept for THE ASSIGNING HEAD (R2 took out THE SHELL'S OWN NAME, THE WRAPPER DROPPED and the exemptions kept aside to withdraw):
    // set by the scan before the walk, by the walk's gate name and by a text not read run here, and read by mentionMayAssign (behaviour: AS8-root-gate-scan,
    // red where the scan is off; AS8-root-gate-walk-ansic, red where the walk's name does not set it; AS8-root-gate-unheld-callback, red where a text not
    // read run here does not)
    assert.ok(hook.includes('const builtinsOff = { seen: mentionsBuiltinGate(command) };') && hook.includes('if (BUILTIN_GATES.has(name)) gateBuiltins();') && hook.includes("    gateBuiltins();   // THE SHELL'S GATE: a text not read, run here, may turn a builtin on or off") && hook.includes('const gateBuiltins = () => { builtinsOff.seen = true; };'), "THE SHELL'S GATE: set for the whole command by the scan before the walk, by the walk's gate name and by a text not read run here, and read by THE ASSIGNING HEAD (behaviour: AS8-root-gate-scan, AS8-root-gate-walk-ansic, AS8-root-gate-unheld-callback)");
    assert.ok(hook.includes('r.unknown.held = held;') && hook.includes('if (nm.length > 0 && spec.refuse && spec.refuse.long.some((x) => x.startsWith(nm))) return opaque(`${name} --${nm}`, value);') && hook.includes('if (u.why.held) return ') && hook.includes('if (u.why.piped) return `This command is blocked here: its \\`${u.why.wrapper}\\` wrapper carries the option ${u.why.option}, which I do not know, `'), 'a literal wrapper option is split by what the table holds and by whether the output reaches `|` (behaviour: AS3-option-abbrev, AS3-option-held-*, AS3-option-unheld-*; an abbreviation of a refused option takes the refusal of the option it abbreviates: AS3-option-refuse-abbrev-*, and the census over the table above)');
    assert.ok(hook.includes("const compare = u.how.includes(CONSTRUCT_HEADS['[['].via) ? 'Write the comparison with `expr`") && hook.includes('const inText = moved;'), 'the comparison names its one remedy, and the text\'s own move names the text remedy whatever an earlier construct did (behaviour: AS7-compare-notlit, AS6-script-eval-in-text-*)');
  } finally { process.env.HOME = savedHome; w.rm(); }
});
