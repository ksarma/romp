// The Bash-side track guard (hooks/romp-track-bash-guard.mjs; plans/file-review.md, decision 47):
// a PreToolUse hook on the Bash tool that refuses a shell command which would write a tracked
// file, the way the vendored guard refuses a raw Write or Edit on one. Driven here two ways: the
// exported evaluate() over synthetic PreToolUse payloads against a scratch project (the
// .trackchanges/config.json the CLIs read), and the hook as a process, with and without ROMP_SID, by its real
// path and through the ~/.claude/hooks/ symlink install.sh registers (the entry guard's realpathSync).
// The grammar is pinned through extractWriteTargets, so a construct the hook stops reading fails
// here by name. Synthetic: a project under os.tmpdir(), invented paths, no session data.
//
// Run: node --test tools/romp-track-bash-guard.test.mjs
import { test, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawn, spawnSync as _spawnSync } from 'node:child_process';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';

import * as guard from '../hooks/romp-track-bash-guard.mjs';
import { CENSUS, census, enumerateLists } from './romp-track-bash-guard-census.mjs';

// a namespace import, so a run of this file against an older hook (the red-on-base check) reports each test on its own
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
const targets = (command, cwd = proj) => extractWriteTargets(command, cwd).targets.map((t) => t.path).sort();
const ROMP_NOUNS = /\b(romp|card|board|column|goal|nudge|dashboard|panel|viewer|dismiss\w*|cleared)\b/i;

// The shells this runner has, through ONE probe. Every real-shell evidence leg below asks shellsFor for the shells it wants: a
// shell that is missing, or present but below the version floor the file's legs need, is reported LOUDLY on stderr, once per
// leg with the leg's line, and its leg does not run; it never passes in silence and never reds with a value mismatch (the
// seventh pass's addendum, item 4, 2026-09-19: CI's shell job has no zsh and failed on unguarded zsh legs at 50e85deec; round 5,
// 2026-09-20: two dash legs sat outside the probe, one skipping its assertion in silence and one throwing a bare TypeError, the
// bash legs ran outside it too, and a bash that starts but is too old declined with a value-mismatch red, since the probe asked
// only whether the shell starts: 45 lines of this file spell a bash 4.x construct, `declare -n` the newest at 4.3, counted by
// grep -c -E "declare -[a-zA-Z]*[nlugA]|typeset -[a-zA-Z]*[nlug]|mapfile|readarray|\|&" over its non-comment lines, and the
// CI Shell job's macOS cell ships bash 3.2.57). Every spawn of a shell in this file goes through the `spawnSync` wrapper below,
// which throws by name when the probe declined that shell, so a leg that reaches a shell without asking shellsFor is a loud red
// naming the shell, whatever its list is called or how it loops, never a silent run and never a red naming nothing.
// The refusable case is run by hand with a `zsh` stub that exits 1 first on PATH: the file passes and prints the NOT RUN lines.
const SHELL_FLOOR = { bash: [4, 3] };   // bash 4.3 for `declare -n`; nothing here needs a zsh or dash newer than the oldest CI build
const probeShell = (sh) => {
  const r = _spawnSync(sh, ['-c', sh === 'bash' ? 'printf %s "$BASH_VERSION"' : 'true'], { encoding: 'utf8' });
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
// THE LIVE-VALUE CHECK (round 5): the spawnSync every leg of this file calls. A shell the probe declined throws by name, so a leg
// written outside shellsFor cannot run that shell in silence, however its list is spelled; `table` and `raw` are parameters so
// the wrapper is pinned in-process against a synthetic table.
const guardedSpawn = (table, raw) => (cmd, ...rest) => {
  if (Object.hasOwn(table, cmd) && !probeOk(table, cmd)) throw new Error(`a real-shell leg ran ${cmd} outside the probe: real ${cmd} ${probeWhy(table, cmd)}; ask shellsFor first`);
  return raw(cmd, ...rest);
};
const spawnSync = guardedSpawn(SHELL_PROBE, _spawnSync);

// ── refusals: the contract's cases ─────────────────────────────────

test('cp over a tracked file is refused, naming the file and track-edit; cat of it is allowed', () => {
  const reason = evaluate(payload('cp base/report.md docs/report.md'));
  assert.ok(reason, 'a cp onto a tracked file is refused');
  assert.ok(reason.includes(report), 'the refusal names the resolved file');
  assert.ok(reason.includes('track-edit'), 'the refusal names the remedy');
  assert.match(reason, /--file '[^']+docs\/report\.md'/, 'the remedy is the track-edit command line on that file, its path single-quoted (the fifth commit: a paste survives a `$` in the path)');
  assert.equal(evaluate(payload('cat docs/report.md')), null, 'a read of the tracked file is not a write');
});

test('the dry run\'s shape: track-config and cp in one compound command is refused', () => {
  const reason = evaluate(payload('node ~/.claude/hooks/track-config.mjs --file docs/report.md && cp base/report.md docs/report.md'));
  assert.ok(reason && reason.includes(report));
  assert.match(reason, /its cp would write the file/);
});

test('a heredoc redirected into a tracked file is refused, and the body is data, never commands', () => {
  assert.ok(evaluate(payload('cat > docs/report.md <<\'EOF\'\nnew text\nEOF')), 'the > target is the write');
  assert.ok(evaluate(payload('cat <<EOF >> docs/report.md\nappended\nEOF')), 'the target may follow the delimiter');
  // A body that happens to read like a cp onto the tracked file is content going somewhere else.
  assert.equal(evaluate(payload('cat > docs/other.md <<\'EOF\'\ncp base/report.md docs/report.md\nEOF')), null);
});

test('sed -i on a tracked file is refused in each of its spellings; sed without -i is a read', () => {
  for (const cmd of [
    'sed -i \'s/cut/reduced/\' docs/report.md',
    'sed -i.bak -e \'s/cut/reduced/\' docs/report.md',
    'sed --in-place \'s/a/b/\' docs/report.md',
    'sed -ni \'p\' docs/report.md',
    'sed -Ei -e \'s/a/b/\' docs/report.md',
  ]) {
    const reason = evaluate(payload(cmd));
    assert.ok(reason && reason.includes(report), `refused: ${cmd}`);
    assert.match(reason, /its sed -i would write/);
  }
  assert.equal(evaluate(payload('sed -n \'1,3p\' docs/report.md')), null);
  assert.equal(evaluate(payload('sed -e \'s/a/b/\' docs/report.md > docs/other.md')), null, 'a sed into an untracked file passes');
});

test('an unrelated path is allowed: an untracked destination, a tracked source copied out, another project', () => {
  assert.equal(evaluate(payload('cp base/report.md docs/other.md')), null);
  assert.equal(evaluate(payload('cp docs/report.md base/copy.md')), null, 'reading the tracked file to copy it elsewhere is not a write to it');
  assert.equal(evaluate(payload('echo hi > docs/other.md')), null);
  const elsewhere = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-bash-guard-other-'));
  try {
    fs.writeFileSync(path.join(elsewhere, 'report.md'), 'x');
    assert.equal(evaluate(payload(`cp base/report.md ${elsewhere}/report.md`)), null, 'a file outside any project passes');
  } finally { fs.rmSync(elsewhere, { recursive: true, force: true }); }
});

test('read-only commands never trip it: cat, grep, diff, git, ls, head, a pipeline of reads', () => {
  for (const cmd of [
    'cat docs/report.md',
    'grep -n latency docs/report.md',
    'diff base/report.md docs/report.md',
    'git diff -- docs/report.md',
    'git checkout -- docs/report.md',
    'git add docs/report.md && git commit -m "report"',
    'ls -la docs/',
    'head -20 docs/report.md | grep api',
    'wc -l docs/report.md 2>/dev/null',
    'sed -n 1p docs/report.md; awk \'{print}\' docs/report.md',
    'node ~/.claude/hooks/track-edit.mjs --file docs/report.md --old "cut" --new "reduced"',
    'node ~/.claude/hooks/track-config.mjs --file docs/report.md',
  ]) assert.equal(evaluate(payload(cmd)), null, `allowed: ${cmd}`);
});

// ── the grammar ────────────────────────────────────────────────────

test('copy verbs: the last operand, a directory destination, -t, mv, install, ln', () => {
  assert.deepEqual(targets('cp base/report.md docs/report.md'), [report]);
  assert.deepEqual(targets('cp base/report.md docs/'), [report], 'a directory destination receives the source under its name');
  assert.deepEqual(targets('cp base/report.md docs'), [report]);
  assert.deepEqual(targets('cp -t docs base/report.md'), [report]);
  assert.deepEqual(targets('cp -r --target-directory=docs base/report.md'), [report]);
  assert.deepEqual(targets('mv tmp.md docs/report.md'), [report]);
  assert.deepEqual(targets('install -m 644 base/report.md docs/report.md'), [report]);
  assert.deepEqual(targets('ln -sf base/report.md docs/report.md'), [report]);
  assert.deepEqual(targets('cp -- base/report.md docs/report.md'), [report]);
  assert.deepEqual(targets('cp base/report.md'), [], 'one operand names no destination');
  assert.deepEqual(targets('install -d docs/new'), [], 'a directory made is no file written');
});

test('ln names its link and walks no directory source: a link is one entry, so linking a folder writes none of its files', () => {
  // cp -r and mv of a folder land its files under the destination, so the source is walked (the test
  // below); ln -s of the same folder makes one entry, the link, whatever the folder holds. The review's
  // consolidation (2026-09-10) found the walk run for ln too, naming docs/<folder>/report.md as a write of
  // a command that writes no file there.
  fs.mkdirSync(path.join(proj, 'base', 'bundle'));
  fs.writeFileSync(path.join(proj, 'base', 'bundle', 'report.md'), 'a copy of the report\n');
  fs.writeFileSync(path.join(proj, 'base', 'bundle', 'notes.md'), 'notes\n');
  const link = path.join(proj, 'docs', 'bundle');
  assert.deepEqual(targets('ln -s base/bundle docs/bundle'), [link], 'the link alone, not the files behind it');
  assert.deepEqual(targets('ln -s base/bundle docs/'), [link], 'into a directory: the link under the source\'s name');
  assert.deepEqual(targets('ln -s -t docs base/bundle'), [link]);
  assert.equal(evaluate(payload('ln -s base/bundle docs/bundle')), null, 'a link beside the tracked file passes');
  // the walk still happens for a copy of the same folder
  assert.deepEqual(targets('cp -r base/bundle docs/bundle'), [path.join(link, 'notes.md'), path.join(link, 'report.md')]);
  assert.deepEqual(targets('mv base/bundle docs/bundle'), [path.join(link, 'notes.md'), path.join(link, 'report.md')]);
  // and a link that replaces a tracked file, or lands under a tracked folder, is still that name
  assert.deepEqual(targets('ln -sf base/bundle/report.md docs/report.md'), [report]);
  assert.ok(evaluate(payload('ln -sf base/bundle/report.md docs/report.md')), 'replacing the tracked file with a link is refused');
  assert.ok(evaluate(payload('ln -s base/bundle notes/bundle')), 'a new entry under a tracked folder is refused, as any new file there is');
});

test('redirections: >, >>, >|, &>, &>>, >&, <>, 2>, a fd prefix; not <, <<<, <&0, 2>&1 or >&2', () => {
  assert.deepEqual(targets('echo x > docs/report.md'), [report]);
  assert.deepEqual(targets('echo x >> docs/report.md'), [report]);
  assert.deepEqual(targets('echo x >| docs/report.md'), [report]);
  assert.deepEqual(targets('cmd &> docs/report.md'), [report]);
  assert.deepEqual(targets('cmd &>> docs/report.md'), [report], '&>> appends both streams to the file');
  assert.deepEqual(targets('cmd >& docs/report.md'), [report], '>& before a word, not a descriptor, writes that file');
  assert.deepEqual(targets('cmd 2>&1 >& docs/report.md'), [report], 'a dup earlier in the command does not hide it');
  assert.deepEqual(targets('cmd <> docs/report.md'), [report], '<> opens the file for reading and writing');
  assert.deepEqual(targets('cmd 2> docs/report.md'), [report]);
  assert.deepEqual(targets('cmd 2>docs/report.md'), [report]);
  assert.deepEqual(targets('cmd >docs/report.md 2>&1'), [report]);
  assert.deepEqual(targets('cmd < docs/report.md'), []);
  assert.deepEqual(targets('cmd <<< docs/report.md'), []);
  assert.deepEqual(targets('cmd >&2; cmd 2>&1; cmd >&-'), []);
  assert.deepEqual(targets('cmd <&0 docs/report.md; cmd <&- docs/report.md'), [], 'a descriptor after <& is a dup; the word after it is an operand');
  assert.deepEqual(targets('echo 2 > docs/other.md'), [other], 'a 2 that is a word, not a descriptor');
});

test('each write redirection is lexed under its own operator and the refusal names it, so none can quietly fall back to a bare >', () => {
  // A mutation that stops reading &>>, >& or <> as itself would still see the trailing > and record a
  // > redirection, so the target alone does not pin the operator: the recorded op and the refusal's wording do.
  for (const op of ['>', '>>', '>|', '&>', '&>>', '>&', '<>']) {
    const { segments } = lex(`cmd ${op} docs/report.md`);
    assert.equal(segments.length, 1, `${op}: one segment`);
    assert.deepEqual(segments[0].words.map((w) => w.text), ['cmd'], `${op}: the target is not a word of the command`);
    assert.deepEqual(segments[0].redirects.map((r) => [r.op, r.target.text]), [[op, 'docs/report.md']], `${op}: one redirection, under its own operator`);
    const reason = evaluate(payload(`cmd ${op} docs/report.md`));
    assert.ok(reason && reason.includes(report), `${op} onto the tracked file is refused`);
    assert.ok(reason.includes(`its ${op} redirection would write the file`), `${op}: the refusal names the operator, in: ${reason}`);
    assert.equal(evaluate(payload(`cmd ${op} docs/other.md`)), null, `${op} onto an untracked file passes`);
  }
});

test('tee, dd, sort -o, sponge and truncate name their files', () => {
  assert.deepEqual(targets('cat x | tee docs/report.md'), [report]);
  assert.deepEqual(targets('cat x | tee -a docs/report.md docs/other.md'), [other, report].sort());
  assert.deepEqual(targets('dd if=/dev/zero of=docs/report.md bs=1 count=1'), [report]);
  assert.deepEqual(targets('sort -o docs/report.md docs/report.md'), [report]);
  assert.deepEqual(targets('cat x | sponge docs/report.md'), [report]);
  assert.deepEqual(targets('truncate -s 0 docs/report.md'), [report]);
});

test('perl -i in its spellings; perl without -i is a read', () => {
  for (const cmd of ['perl -i -pe \'s/a/b/\' docs/report.md', 'perl -pi.bak -e \'s/a/b/\' docs/report.md', 'perl -lpi -e \'s/a/b/\' docs/report.md', 'perl -ni -e \'print\' docs/report.md']) {
    assert.deepEqual(targets(cmd), [report], cmd);
  }
  assert.deepEqual(targets('perl -pe \'s/a/b/\' docs/report.md'), []);
  assert.deepEqual(targets('perl -Mstrict -e \'print 1\' docs/report.md'), [], '-Mstrict is a module, not -i');
});

test('python and node inline scripts: a literal path opened with a write mode; a read mode or a script file is not', () => {
  assert.deepEqual(targets('python3 -c "open(\'docs/report.md\', \'w\').write(\'x\')"'), [report]);
  assert.deepEqual(targets('python3 -c "open(\'docs/report.md\', mode=\'a\').write(\'x\')"'), [report]);
  assert.deepEqual(targets('python -c "from pathlib import Path; Path(\'docs/report.md\').write_text(\'x\')"'), [report]);
  assert.deepEqual(targets('python3 -c "import shutil; shutil.copy(\'base/report.md\', \'docs/report.md\')"'), [report]);
  assert.deepEqual(targets('python3.12 -c "open(\'docs/report.md\', \'w\')"'), [report], 'a versioned interpreter name');
  assert.deepEqual(targets('python3 -c "print(open(\'docs/report.md\').read())"'), []);
  assert.deepEqual(targets('python3 -c "open(\'docs/report.md\', \'r\').read()"'), []);
  assert.deepEqual(targets('python3 fix.py docs/report.md'), [], 'a script file\'s contents are not in the command');
  assert.deepEqual(targets('node -e "require(\'fs\').writeFileSync(\'docs/report.md\', \'x\')"'), [report]);
  assert.deepEqual(targets('node -e "fs.copyFileSync(\'base/report.md\', \'docs/report.md\')"'), [report]);
  assert.deepEqual(targets('node -e "console.log(fs.readFileSync(\'docs/report.md\', \'utf8\'))"'), []);
  // a script on stdin: the heredoc body is the script
  assert.deepEqual(targets('python3 - <<\'EOF\'\nfrom pathlib import Path\nPath(\'docs/report.md\').write_text(\'x\')\nEOF'), [report]);
  assert.deepEqual(targets('python3 <<\'EOF\'\nprint(open(\'docs/report.md\').read())\nEOF'), []);
  assert.deepEqual(scriptWriteTargets('python', 'open(f"{d}/report.md", "w")'), [], 'a path with an expression is not literal');
  assert.deepEqual(scriptWriteTargets('node', 'fs.writeFileSync(`${dir}/report.md`, x)'), []);
});

test('paths resolve against the session cwd, a cd earlier in the command, ~/, and an absolute path', () => {
  assert.deepEqual(targets('cd docs && cp ../base/report.md report.md'), [report], 'cd moves the cwd for what follows');
  assert.deepEqual(targets('cd docs; echo x > report.md'), [report]);
  assert.deepEqual(targets(`cp base/report.md ${report}`), [report], 'an absolute path needs no cwd');
  assert.deepEqual(targets('cp base/report.md docs/report.md', path.join(proj, 'base')), [path.join(proj, 'base', 'docs', 'report.md')], 'relative to the cwd given');
  assert.deepEqual(targets('cd "$D" && cp a report.md'), [], 'after a cd the lexer cannot read, a relative path is no literal target: since round 3 it is refused in a tracked project with the reason, where before it was dropped (the unknown-directory test below)');
  assert.deepEqual(targets(`cd "$D" && cp a ${report}`), [report], 'an absolute one still resolves');
  const home = process.env.HOME;
  process.env.HOME = proj;
  try { assert.deepEqual(targets('cp base/report.md ~/docs/report.md', '/'), [report], '~/ is the home directory'); }
  finally { process.env.HOME = home; }
});

test('a command the lexer cannot see through and that names no target is allowed: eval, xargs, a shell -c it cannot read, a read or a pipe of a variable', () => {
  // The variable-target cps that used to sit here (`cp "$SRC" "$DST"` and its kin) are in the block below:
  // since 2026-09-18 a target the hook cannot read is refused while a tracked project is in play. What stays
  // allowed is a command with no target to judge, and a word that can never be a file (a process substitution).
  for (const cmd of [
    'eval "$CMD"',
    'ls docs/*.md | xargs -I{} cp base/{} {}',
    'bash -c "$SCRIPT"',
    'cat "$F" | grep latency',
    'diff "$A" docs/report.md',
    'tee >(cat) docs/other.md',
    'cmd > >(cat)',
    'if [[ "$name" > docs/report.md ]]; then echo newer; fi',
  ]) {
    assert.equal(evaluate(payload(cmd)), null, `allowed: ${cmd}`);
  }
  assert.ok(extractWriteTargets('eval "$CMD"', proj).opaque);
  assert.ok(!extractWriteTargets('cp a b', proj).opaque);
});

// ── a target the shell fills in, in a tracked project ──────────────
//
// A research session reported (2026-09-17, through the box admin) that `cp "$SRC" "$DST"` overwrote a
// tracked file with no change recorded, while the same cp spelled out was refused: the hook dropped every
// target it could not read. Since 2026-09-18 such a target is refused while a project that tracks anything
// is in play (the session's cwd, the directory a cd moved to, or the folder a copy lands in); of the
// session's environment the hook reads HOME, TRACKCHANGES_ROOT and ROMP_SID and no other variable, whatever the
// command names (since B2 it reads a name the command's own text sets to a plain string, never one from the
// environment); of the environment's values only HOME's can appear in a refusal, as a path resolved through it (review round 2,
// 2026-09-18; the resolved value of a name the command set can appear too since B2). With no such project in play the word is dropped as before, and a literal target keeps its
// verdict. Review round 1 (2026-09-18) bounded the rule in four places, each pinned below: a target whose
// only expansions the running shell keeps unassignable and whose text is an absolute path outside the
// project is allowed; a copy's landing folder counts only when a tracked file could land there; a project
// counts only when its list holds an entry the literal rule could refuse; a directory is judged under its
// real path and its name. Review round 2 (2026-09-18) found two ways around the numeric narrowing by
// execution and one unsound member of its set, each pinned below in both directions: the project the
// target's own literal prefix sits in is asked (a numeric name landing in a second tracked project was
// dropped while its literal spelling was refused), a `..` that folds every expansion away still resolves
// the literal directory part (a link after the fold carried a write into the project), and the numeric set
// is per shell (`$BASHPID` is assignable in zsh, RANDOM and SECONDS under dash).
// Round 2's addendum (2026-09-18) ruled one residual of the first of those a correct refusal and kept it: a
// numeric folder name in the first segment under a tracked root (`<root>/x-$$/y.md`) is refused from any cwd,
// since the folder's name is not known at check time, with a refusal that says so and asks for the folder
// spelled out; pinned beside the same shape one level deeper under an untracked folder, which is allowed.
// Review round 3 (2026-09-19) found three highs and thirty-seven confirmed findings, all pinned below in both
// directions: the numeric set is the process id alone, in every shell (RANDOM and SECONDS can be unset or
// shadowed in bash and zsh, measured; the per-shell table is gone); every target the hook cannot read is
// measured against the project its own literal directory part sits in, absolute or relative; a literal
// relative target after a cd the hook cannot follow is refused with the reason, not dropped; a `..` after a
// link climbs from the link's target, as the kernel does, a fold onto a link file is the file, and an existing
// entry the pid could spell is followed; a literal dollar is literal; `$'...'` is ANSI-C quoting; a landing
// folder no project claims counts when an entry there leads to a tracked file; bash's -O takes a word; the
// extractor's recursions are capped; and the unknown-folder refusal is the landing gate at any depth, with a
// remedy a person can take. The mutation pass over round 3 (2026-09-19) found nine of its claims unpinned, six of
// them behavioural and pinned in the addendum tests below by the shape that reaches each mechanism alone:
// numericOutside's three spellings (the root's own segment past the cap, the literal directory part resolved, a
// candidate entry that leads into the project), couldSpell's literal dollar, the unresolvable prefix, and the
// own-project cut at the first expansion mark; the three prose clauses (docs/install.md, the hook's README row,
// the ledger entry) are pinned in tools/file-review-plan-bash-guard.test.mjs.

const NOT_LITERAL = /is not a literal path/;

// Every shape and its verdict in one map, compared once, so a regression in any shape is reported beside
// the others instead of stopping the loop at the first (review round 1, 2026-09-18). A refusal's four
// properties are folded into its value; a deliberate allowance reads 'allowed'.
const REFUSED = 'refused';
const verdictOf = (cmd, cwd = proj) => {
  const reason = evaluate(payload(cmd, cwd));
  if (reason == null) return 'allowed';
  const faults = [];
  if (!NOT_LITERAL.test(reason)) faults.push('not as a non-literal target');
  if (!reason.includes(proj)) faults.push('without naming the project in play');
  if (!reason.includes('track-edit')) faults.push('without the remedy');
  return faults.length ? `refused, but ${faults.join(', ')}` : REFUSED;
};
const verdicts = (cmds, cwd = proj) => Object.fromEntries(cmds.map((c) => [c, verdictOf(c, cwd)]));
const allOf = (cmds, v) => Object.fromEntries(cmds.map((c) => [c, v]));

test('a write whose target the shell fills in is refused in a tracked project: a variable, a substitution, a backtick, a ~user, a glob or brace list the hook cannot expand', () => {
  const shapes = [
    'cp "$SRC" "$DST"',                                 // the reported shape
    'cp base/report.md "$DST"',                         // a literal source too
    'cp base/report.md docs/$NAME.md',
    'cp base/report.md "${OUT}"',
    'cp base/report.md "$(mktemp -p docs)"',
    'cp base/report.md `mktemp -p docs`',
    'cp base/report.md ~someone/report.md',
    'mv base/report.md "$DST"',
    'install -m 644 base/report.md "$DST"',
    'ln -sf base/report.md "$LINK"',
    'echo x > "$OUT"',
    'echo x >> $LOG',
    'cmd 2> "$ERR"',
    'cat x | tee "$F"',
    'cat x | tee -a docs/other.md "$F"',
    'dd if=/dev/zero of="$F" bs=1 count=1',
    'sort -o "$F" base/report.md',
    'truncate -s 0 "$F"',
    "sed -i 's/a/b/' \"$F\"",
    "perl -pi -e 's/a/b/' $F",
    'cp base/report.md notes/new*.md',                 // a glob with no match: bash writes the pattern's text as the name
    'echo x > notes/new*.md',
    'cd "$D" && cp base/report.md report*.md',          // a glob the hook cannot expand: the cwd unknown
    'tee notes/n{1..1000}.md',                          // a brace list past the cap
    'cp "$SRC" docs/',                                  // a literal folder that holds a tracked file, a name the shell fills in
    'cp -t notes "$SRC"',
    'for f in a b; do cp "$f" docs/; done',
    'cp "$SRC" "$DST"; echo done',                      // in a list
    'echo "$(cp a "$B")"',                              // inside a substitution
  ];
  assert.deepEqual(verdicts(shapes), allOf(shapes, REFUSED));
  assert.ok(evaluate(payload('cp "$SRC" "$DST"')).includes('its cp names "$DST"'), 'the word as typed, quotes included');
  assert.ok(evaluate(payload('echo x > "$OUT"')).includes('its > redirection names "$OUT"'));
  assert.ok(evaluate(payload('cp "$SRC" docs/')).includes('its cp names "$SRC"'), 'a copy into a folder names the source whose name it takes');
  const { unresolved } = extractWriteTargets('cp "$SRC" "$DST"', proj);
  assert.deepEqual(unresolved.map((u) => [u.raw, u.how, u.dir, u.at, u.numeric]), [['"$DST"', 'cp', proj, null, null]], 'the grammar reports the word it could not read');
});

// A second scratch directory beside the project, outside every project: the target of the writes the round
// found refused although they land nowhere near a tracked file. Under os.tmpdir(), as the project is.
const outsideDir = () => fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'romp-bash-guard-outside-')));

test('what stays refused by the review\'s ruling: a substitution or a variable in the name whatever the literal prefix, a relative or bare expansion, a prefix inside the project, a number beside a variable or a glob', () => {
  // The round-1 review (2026-09-18) weighed narrowing the refusal by the word's literal prefix and took only
  // the numeric subset (the test below): a refuter showed by execution that a variable can carry `../` back
  // into the project, so an outside prefix bounds nothing when a variable or a substitution follows it. The
  // `$(date)` timestamped log stays refused with the rest, a cost stated to the user, not a class solved here.
  const out = outsideDir();
  try {
    const shapes = [
      `echo x > "${out}/x-$(date +%s).log"`,                  // a command substitution: the timestamped log
      `echo x > ${out}/x-\`date +%s\`.log`,
      `echo x > ${out}/"$NAME".log`,                          // a variable of unknown content beside an outside prefix
      `echo x > ${out}/"$NAME"`,                              // the refuters' traversal: NAME holding ../<project>/docs/report.md
      `cp base/report.md "${out}/$NAME"`,
      `cp base/report.md "${out}/\${NAME}.md"`,
      `echo x > "${out}/x-$$-$USER.log"`,                     // a number beside a variable of unknown content
      `echo x > "${out}/x-$$$(date +%s).log"`,
      `echo x > ${out}/x-$$*.log`,                            // a glob beside the number: `*` could spell a project's name
      `echo x > ${out}/x-$RANDOMX.log`,                       // not $RANDOM: a variable of that name
      `echo x > ${out}/x-$RANDOM_1.log`,
      `echo x >> "${out}/x-\${BASHPID}.log"`,                  // round 2: zsh, the tool's shell here, lets a command assign BASHPID (the per-shell test below)
      `cmd > ${out}/out-$RANDOM.log`,                          // round 3: RANDOM and SECONDS are out of the numeric set in every shell (the numeric-set test below says why)
      `echo x >> "${out}/x-\${SECONDS}.log"`,
      `echo x > ${out}/t-$SECONDS.log`,
      `echo x > "${out}/run-$$/\${RANDOM}.log"`,
      `echo x > ${out}/$$/../plain.log`,                       // round 3: a segment that is nothing but an expansion, cancelled by a `..`, is not narrowed
      'echo x > build-$$.log',                                // a relative prefix
      'echo x > ../scratch-$$.log',
      'echo x > "$$.log"',                                    // no literal prefix at all
      'echo x > $RANDOM',
      'cp base/report.md "$(mktemp)"',
      `echo x > ${proj}/docs/x-$$.md`,                        // a prefix inside the project
      `tee ${proj}/notes/n-$RANDOM.md < base/report.md`,
      `echo x > ${out}/run-$$/../../${path.basename(proj)}/docs/x-$$.md`,   // a literal traversal after the number, folded before the comparison
      'echo x > ~someone/x-$$.log',                           // a ~user with the number: the home is not read
    ];
    assert.deepEqual(verdicts(shapes), allOf(shapes, REFUSED));
    // the real shell shows why the variable case must stay refused: the value carries the write back onto the
    // tracked file, and nothing in the word's literal text says so
    for (const sh of shellsFor(['bash'], 'the variable case in real bash')) {
      const shell = spawnSync(sh, ['-c', 'echo poison > "$OUT"/"$NAME"'], {
        encoding: 'utf8', env: { PATH: process.env.PATH, OUT: out, NAME: `../${path.basename(proj)}/docs/report.md` },
      });
      assert.equal(shell.status, 0, shell.stderr);
      assert.equal(fs.readFileSync(report, 'utf8'), 'poison\n', 'the tracked file was overwritten through the outside prefix');
    }
  } finally { fs.rmSync(out, { recursive: true, force: true }); }
});

test('the numeric narrowing: a target whose only expansions are $$ or ${$} and whose text is an absolute path outside every project in play is allowed', () => {
  // Review round 1 (2026-09-18): every such write was refused whenever the cwd sat in a tracked project,
  // breaking temp logs and captures box-wide once any project turned tracking on. No shell lets a command
  // assign a path to `$$`, so the word's literal segments bound where the write lands. Round 2 (2026-09-18)
  // dropped $BASHPID from the set, since zsh leaves it assignable; round 3 (2026-09-19) dropped $RANDOM and
  // $SECONDS in every shell, since bash and zsh let a command unset or shadow them (the numeric-set test below).
  const out = outsideDir();
  try {
    const shapes = [
      `echo x > "${out}/build-$$.log"`,
      `npm test > "${out}/test-output-$$.log" 2>&1`,
      `echo x > ${out}/x-\${$}.log`,
      `echo x > "${out}/run-$$/\${$}.log"`,
      `tee -a ${out}/log.$$ < base/report.md`,
      `cp base/report.md ${out}/copy-$$.md`,
      `mv base/report.md "${out}/moved-$$.md"`,
      `sort -o ${out}/sorted-$$.txt base/report.md`,
      `echo x > ${out}/run-$$/../other-$$.log`,               // a traversal that stays outside
      `echo x > ${out}/run-$$/../plain.log`,                   // round 2: a traversal that folds every expansion away, to a plain path outside
      `cd "$D" && echo x > ${out}/x-$$.log`,                   // the cwd unknown: the payload cwd is in play, and the target is outside it
      `cd notes && echo x > ${out}/x-$$.log`,                  // from inside the tracked folder
    ];
    assert.deepEqual(verdicts(shapes), allOf(shapes, 'allowed'));
    // the grammar carries the text for the narrowing, and only for a numeric-only word
    const { unresolved } = extractWriteTargets(`echo x > "${out}/build-$$.log"`, proj);
    assert.deepEqual(unresolved.map((u) => [u.raw, u.numeric]), [[`"${out}/build-$$.log"`, `${out}/build-$$.log`]]);
    assert.equal(extractWriteTargets('echo x > "$OUT"', proj).unresolved[0].numeric, null);
    assert.equal(extractWriteTargets(`echo x > "${out}/x-$$-$USER.log"`, proj).unresolved[0].numeric, null);
    // the number could spell the project's own directory: a project at <out>/build-4242 refuses <out>/build-$$/x.md
    const digits = path.join(out, 'build-4242');
    fs.mkdirSync(path.join(digits, '.trackchanges'), { recursive: true });
    fs.writeFileSync(path.join(digits, '.trackchanges', 'config.json'), JSON.stringify({ v: 2, tracked: ['x.md'] }));
    assert.ok(evaluate(payload(`echo x > ${out}/build-$$/x.md`, digits)), 'the segment with the number could be the root\'s');
    assert.ok(evaluate(payload(`echo x > ${out}/build-\${$}/x.md`, digits)));
    assert.ok(evaluate(payload(`echo x > ${out}/build-$RANDOM/x.md`, digits)), 'and a $RANDOM spelling is refused as any variable is, since round 3');
    assert.equal(evaluate(payload(`echo x > ${out}/other-$$/x.md`, digits)), null, 'a literal segment that differs diverges');
    assert.equal(evaluate(payload(`echo x > ${out}/build-4242x-$$.log`, digits)), null, 'a sibling name, not the root');
    // Review round 2 (2026-09-18): the project the target's OWN literal prefix sits in is asked, so a numeric
    // name landing in a folder of a second tracked project where a tracked file could land is refused, from a
    // cwd in another project and from a cwd in none, as its literal spelling is when that spelling is tracked
    // (the folder entry notes/ here; where the folder holds a tracked file by name only, the numeric name is
    // refused while its literal spelling passes, the deliberate false refusal the round-3 test below pins); the
    // refusal names the second project, the tree the write lands in. Two refuters overwrote a note tracked by
    // folder that way (a one-shot shell's $SECONDS is 0). A $SECONDS or ${RANDOM} spelling is refused there as
    // any variable is, since round 3 took them out of the set. Both directions: a numeric temp write into a
    // folder of a third project where nothing tracked could land stays allowed, as its literal spelling is
    // (bare tracksRefusable on the prefix would refuse it, a round-1-class regression).
    const second = path.join(out, 'second');
    fs.mkdirSync(path.join(second, '.trackchanges'), { recursive: true });
    fs.mkdirSync(path.join(second, 'notes'));
    fs.writeFileSync(path.join(second, '.trackchanges', 'config.json'), JSON.stringify({ v: 2, tracked: ['notes/'] }));
    fs.writeFileSync(path.join(second, 'notes', 'log-0.md'), 'a note tracked by its folder\n');
    const third = path.join(out, 'third');
    fs.mkdirSync(path.join(third, '.trackchanges'), { recursive: true });
    fs.mkdirSync(path.join(third, 'build'));
    fs.writeFileSync(path.join(third, '.trackchanges', 'config.json'), JSON.stringify({ v: 2, tracked: ['docs/report.md'] }));
    for (const cwd of [proj, out]) {
      const where = cwd === proj ? 'from a cwd in another tracked project' : 'from a cwd in no project';
      for (const cmd of [`echo x > ${second}/notes/log-$SECONDS.md`, `echo x > ${second}/notes/log-$$.md`, `cp base/report.md ${second}/notes/copy-\${RANDOM}.md`]) {
        const reason = evaluate(payload(cmd, cwd));
        assert.ok(reason && NOT_LITERAL.test(reason), `${where}, refused as not literal: ${cmd}`);
        assert.ok(reason.includes(`Track-changes is ON in ${second},`), `${where}, the refusal names the project the write lands in: ${reason.split('\n')[0]}`);
        assert.ok(!reason.includes(proj), `${where}, not the cwd's project`);
      }
      assert.match(evaluate(payload(`echo x > ${second}/notes/log-0.md`, cwd)), /^Track-changes is ON for /, `${where}, the literal spelling is refused beside it`);
      assert.match(evaluate(payload(`echo x > ${second}/notes/log-4242.md`, cwd)), /^Track-changes is ON for /, `${where}, a literal name the folder entry covers`);
      assert.equal(evaluate(payload(`echo x > ${third}/build/log-$$.log`, cwd)), null, `${where}, an untracked folder of a third project: nothing tracked could land there`);
      assert.equal(evaluate(payload(`echo x > ${third}/build/log-1.log`, cwd)), null, `${where}, as its literal spelling is`);
    }
    // a symlinked directory in the literal part is judged under its real path too
    fs.symlinkSync(path.join(proj, 'docs'), path.join(out, 'linkdocs'));
    assert.ok(evaluate(payload(`echo x > ${out}/linkdocs/x-$$.md`)), 'the link leads into the project');
    assert.ok(evaluate(payload(`cp base/report.md ${out}/linkdocs/copy-$$.md`)));
    // Review round 2 (2026-09-18): the literal directory part is resolved when a `..` folds every expansion
    // away too. Before, the cut was searched from the position of a `$` the normalized text no longer held,
    // the directory part collapsed to `/`, and a link AFTER the fold carried the write into the project (two
    // refuters overwrote the tracked file with the first shape below, in real bash). Three cases, as ruled:
    // the link after the fold (new), the link before the fold (kept, above), and the fold to a plain path
    // outside every project (in the allowed corpus above), so the fix cannot drift into refusing every fold.
    assert.ok(evaluate(payload(`mkdir -p ${out}/run-$$ && echo x > ${out}/run-$$/../linkdocs/report.md`)), 'the link after the fold: the tail climbs into the project');
    assert.ok(evaluate(payload(`echo x > ${out}/linkdocs/t-$$/../report.md`)), 'the fold inside the linked directory');
    assert.ok(evaluate(payload(`cp base/report.md ${out}/run-$$/../linkdocs/report.md`)));
    assert.ok(evaluate(payload(`echo x > ${out}/run-$$/../linkdocs/report.md`, out)), 'and from a cwd in no project, through the target\'s own prefix');
    assert.equal(evaluate(payload(`echo x > ${out}/run-$$/../plain.log`)), null, 'the fold to a plain path outside stays allowed');
    assert.equal(evaluate(payload(`echo x > ${out}/run-$$/../plain.log`, out)), null);
    // and through the process, both ways
    const run = (command) => spawnSync(process.execPath, [HOOK], { input: payload(command), encoding: 'utf8', env: hookEnv({ ROMP_SID }) });
    assert.equal(run(`echo x > "${out}/build-$$.log"`).status, 0);
    assert.equal(run(`echo x > ${out}/run-$$/../plain.log`).status, 0);
    const refused = run(`echo x > "${out}/x-$(date +%s).log"`);
    assert.equal(refused.status, 2);
    assert.match(refused.stderr, NOT_LITERAL, 'from the tracked cwd a substitution in the name is refused by the cwd rule (B2 as ruled resolves the values it can read and leaves an opaque one to that rule)');
    const folded = run(`mkdir -p ${out}/run-$$ && echo x > ${out}/run-$$/../linkdocs/report.md`);
    assert.equal(folded.status, 2, 'the link after the fold, as a process');
    const crossed = run(`echo x > ${second}/notes/log-$$.md`);
    assert.equal(crossed.status, 2, 'the second project, as a process');
    assert.ok(crossed.stderr.includes(second) && !crossed.stderr.includes(proj), 'naming the project the write lands in');
    // the real shell shows what the refused fold would do: the write lands on the tracked file through the link
    for (const sh of shellsFor(['bash'], 'the fold through the link in real bash')) {
      const shell = spawnSync(sh, ['-c', `mkdir -p ${out}/run-$$ && echo poison > ${out}/run-$$/../linkdocs/report.md`], { encoding: 'utf8', env: { PATH: process.env.PATH } });
      assert.equal(shell.status, 0, shell.stderr);
      assert.equal(fs.readFileSync(report, 'utf8'), 'poison\n', 'the tracked file was overwritten through the link after the fold');
    }
  } finally { fs.rmSync(out, { recursive: true, force: true }); }
});

test('review round 2 addendum: a numeric folder name in the first segment under a tracked root is refused from any cwd, naming the unknown folder; one level deeper under an untracked folder it is allowed', () => {
  // The round-2 own-project branch resolves the literal directory part of `<root>/x-$$/y.md` to the root
  // itself, and the landing gate on a root holds for every project that tracks anything, so the target is
  // refused from any cwd while its literal spelling `<root>/x-4242/y.md` passes when that folder is untracked.
  // Ruled CORRECT and kept (the round-2 addendum, 2026-09-18): the hook cannot compute the literal spelling,
  // since the folder's name does not exist at check time and is not derivable from the text; a write guard
  // that does not know refuses, the person recovers in one step by spelling the folder, and the opposite error
  // overwrites tracked content silently. Pinned in both directions so the next reader cannot close it by
  // widening the allowance: the first-segment target refuses from the project's own cwd, from a cwd in another
  // tracked project and from a cwd in none, and the same shape one level deeper (`<root>/build/x-$$/y.md`,
  // `build` untracked) resolves its literal part to `<root>/build`, fails the landing gate and falls through
  // to the cwd rule: allowed from a neutral cwd and from another project's, refused with the generic text from
  // its own project's cwd (round 1's prefix-inside-the-project ruling), and since round 3 (2026-09-19) that
  // refusal carries the folder text too, since the reason is the same at every depth. The refusal says why: the
  // folder's name is not known, not that the target sits in a tracked project, and it offers a remedy the person
  // can take (round 3: a literal folder name of their own, or a write outside the project; before, it asked for
  // the name the shell would give the folder, a value nobody can know before the command runs). Only a folder
  // segment takes that text: an expansion in the file's own name (`<root>/x-$$.md`, the folder known) and a fold
  // that leaves no expansion (`<root>/run-$$/../y.md`) keep the generic refusal.
  const out = outsideDir();
  try {
    const second = path.join(out, 'second');
    for (const d of ['.trackchanges', 'docs', 'build', 'x-4242', path.join('build', 'x-4242')]) fs.mkdirSync(path.join(second, d), { recursive: true });
    fs.writeFileSync(path.join(second, '.trackchanges', 'config.json'), JSON.stringify({ v: 2, tracked: ['docs/report.md'] }));
    fs.writeFileSync(path.join(second, 'docs', 'report.md'), 'tracked prose\n');
    const src = path.join(proj, 'base', 'report.md');
    const UNKNOWN = /cannot tell which folder/;
    // [command, the folder segment the refusal must name, the target's text as the shell sees it]
    const first = [
      [`echo x > ${second}/x-$$/y.md`, 'x-$$', `${second}/x-$$/y.md`],
      [`cp ${src} "${second}/run-\${$}/copy.md"`, 'run-${$}', `${second}/run-\${$}/copy.md`],   // round 3: the pid's other spelling; ${RANDOM} is out of the set
      [`tee ${second}/t-$$/log.md < ${src}`, 't-$$', `${second}/t-$$/log.md`],
    ];
    const cwds = [[second, 'from the project\'s own cwd'], [proj, 'from a cwd in another tracked project'], [out, 'from a cwd in no project']];
    for (const [cwd, where] of cwds) {
      for (const [cmd, seg, target] of first) {
        const reason = evaluate(payload(cmd, cwd));
        assert.ok(reason, `${where}, the first-segment folder is refused: ${cmd}`);
        assert.match(reason, UNKNOWN, `${where}, the refusal says the folder is not known: ${reason.split('\n')[0]}`);
        assert.ok(reason.includes(seg), `${where}, and names the unknown folder ${seg}: ${reason.split('\n')[0]}`);
        assert.ok(reason.includes('Spell the folder out with a literal name of your own, or write outside that project'), `${where}, and offers a remedy the person can take`);
        assert.ok(!reason.includes('the name the shell would give it'), `${where}, never the name the shell would give the folder, which nobody can know before the command runs`);
        assert.ok(!NOT_LITERAL.test(reason), `${where}, not the generic not-a-literal-path text: ${reason.split('\n')[0]}`);
        assert.ok(!reason.split(target).join('').includes(second), `${where}, the project is not named apart from the target itself: ${reason.split('\n')[0]}`);
        assert.ok(!reason.includes(proj), `${where}, nor the cwd's project`);
        assert.ok(reason.includes('for me to accept or reject') && reason.includes('track-edit'), `${where}, the person's voice and the remedy`);
        assert.ok(!ROMP_NOUNS.test(reason.split(second).join('<project>')) && !/\u2014/.test(reason), `${where}, no romp noun and no em dash`);
      }
      assert.equal(evaluate(payload(`echo x > ${second}/x-4242/y.md`, cwd)), null, `${where}, the spelling the refusal asks for passes: the folder is untracked`);
      assert.equal(evaluate(payload(`cp ${src} ${second}/x-4242/copy.md`, cwd)), null);
    }
    // one level deeper: the literal part is `<root>/build`, untracked, so the target falls through to the cwd rule
    for (const [cwd, where] of cwds.slice(1)) {
      assert.equal(evaluate(payload(`echo x > ${second}/build/x-$$/y.md`, cwd)), null, `${where}, a numeric folder one level deeper under an untracked folder is allowed`);
      assert.equal(evaluate(payload(`cp ${src} "${second}/build/run-\${$}/copy.md"`, cwd)), null, `${where}, as a copy`);
      assert.equal(evaluate(payload(`echo x > ${second}/build/x-4242/y.md`, cwd)), null, `${where}, as its literal spelling is`);
    }
    const deeperOwn = evaluate(payload(`echo x > ${second}/build/x-$$/y.md`, second));
    assert.ok(deeperOwn && UNKNOWN.test(deeperOwn) && deeperOwn.includes('x-$$') && !NOT_LITERAL.test(deeperOwn), 'from its own project\'s cwd the deeper target is refused by the cwd rule, and since round 3 with the folder text: the reason is the same');
    assert.ok(!deeperOwn.split(`${second}/build/x-$$/y.md`).join('').includes(second), 'the absolute target carries the project, which is not named again');
    // the folder known, the file's name not: the generic text, which says the target is not a literal path
    for (const [cmd, why] of [[`echo x > ${second}/x-$$.md`, 'an expansion in the file\'s own name'], [`echo x > ${second}/run-$$/../y.md`, 'a fold that leaves no expansion']]) {
      const reason = evaluate(payload(cmd, out));
      assert.ok(reason && NOT_LITERAL.test(reason) && !UNKNOWN.test(reason), `${why} keeps the generic refusal: ${reason && reason.split('\n')[0]}`);
      assert.ok(reason.includes(`Track-changes is ON in ${second},`), `${why}: naming the project`);
    }
    // and through the process, both ways, from a cwd in no project
    const run = (command, cwd) => spawnSync(process.execPath, [HOOK], { input: payload(command, cwd), encoding: 'utf8', env: hookEnv({ ROMP_SID }) });
    const refused = run(`echo x > ${second}/x-$$/y.md`, out);
    assert.equal(refused.status, 2, 'the first-segment folder, as a process');
    assert.match(refused.stderr, UNKNOWN);
    assert.ok(refused.stderr.includes('x-$$') && !NOT_LITERAL.test(refused.stderr));
    assert.equal(run(`echo x > ${second}/build/x-$$/y.md`, out).status, 0, 'one level deeper, as a process');
    assert.equal(run(`echo x > ${second}/x-4242/y.md`, out).status, 0, 'the literal spelling, as a process');
    // what the refused command does in real bash: the folder takes the shell's pid for its name, a name the
    // hook could not have read, and the write lands in an untracked folder; the refusal is the deliberate one
    for (const sh of shellsFor(['bash'], 'the pid-named folder in real bash')) {
      const shell = spawnSync(sh, ['-c', `mkdir -p ${second}/x-$$ && echo x > ${second}/x-$$/y.md`], { encoding: 'utf8', env: { PATH: process.env.PATH } });
      assert.equal(shell.status, 0, shell.stderr);
      const made = fs.readdirSync(second).filter((n) => /^x-\d+$/.test(n) && n !== 'x-4242');
      assert.equal(made.length, 1, 'one folder named by the pid');
      assert.equal(fs.readFileSync(path.join(second, made[0], 'y.md'), 'utf8'), 'x\n');
      assert.equal(fs.readFileSync(path.join(second, 'docs', 'report.md'), 'utf8'), 'tracked prose\n', 'the tracked file is untouched');
    }
  } finally { fs.rmSync(out, { recursive: true, force: true }); }
});

test('the numeric set is $$ and ${$} in every shell, and nothing else: RANDOM, SECONDS and BASHPID are never numeric, since a command can unset or shadow them', () => {
  // Round 1 (2026-09-18) listed RANDOM, SECONDS and BASHPID as read-only integers; round 2 dropped BASHPID (zsh leaves
  // it assignable) and kept the other two under bash and zsh, per shell; round 3 (2026-09-19) measured, in the shells
  // below, `unset RANDOM; RANDOM=<traversal>` and `local RANDOM=` inside a function in bash, `typeset -h RANDOM` inside a
  // function in zsh, and a plain assignment in dash, each carrying the write onto the tracked file while the hook read
  // the word as numeric (and a sourced file carries the unset with no such word in the command at all). No shell
  // refuses every road to those names; every shell refuses every road to `$$`. So the set is the process id alone, in
  // every shell, and a temp name built from `$RANDOM` inside a tracked project is refused, the cost decision 47 states.
  // Both directions, so the rule cannot be met by refusing everything; the real shells below show the roads.
  const out = outsideDir();
  const back = `../${path.basename(proj)}/docs/report.md`;   // the traversal a refuter assigned: out/../<project>/docs/report.md
  const original = fs.readFileSync(report, 'utf8');
  try {
    const refused = [
      `bash -c 'unset RANDOM; RANDOM=${back}; cp base/report.md "${out}/$RANDOM"'`,      // the bash roads
      `bash -c 'unset SECONDS; SECONDS=${back}; echo x > "${out}/$SECONDS"'`,
      `bash -c 'f(){ local RANDOM=${back}; cp base/report.md "${out}/$RANDOM"; }; f'`,
      `bash -c 'unset RANDOM; declare -g RANDOM=${back}; cp base/report.md "${out}/\${RANDOM}"'`,
      `bash <<'EOF'\nunset RANDOM; RANDOM=${back}; cp base/report.md "${out}/$RANDOM"\nEOF`,
      `bash -c '. ./setenv.sh; cp base/report.md "${out}/$RANDOM"'`,                    // the unset in a sourced file: no such word in the command
      `zsh -c 'f(){ typeset -h RANDOM; RANDOM=${back}; cp base/report.md "${out}/$RANDOM"; }; f'`,   // the zsh road
      `f(){ typeset -h SECONDS; SECONDS=${back}; cp base/report.md "${out}/$SECONDS"; }; f`,         // at the top level
      `unset RANDOM; RANDOM=${back}; cp base/report.md "${out}/$RANDOM"`,
      `sh -c 'RANDOM=${back}; cp base/report.md "${out}/$RANDOM"'`,                    // the dash road (round 2)
      `dash -c 'echo x > ${out}/x-\${RANDOM}.log'`,
      `ksh -c 'echo x > ${out}/x-$RANDOM.log'`,                                          // ksh: no binary here; the name is read from the command
      `bash -c 'echo x > ${out}/x-$RANDOM.log'`,                                         // no assignment in sight: the hook cannot tell
      `zsh -c 'echo x > ${out}/x-$SECONDS.log'`,
      `cmd > ${out}/out-$RANDOM.log`,
      `echo x >> "${out}/x-\${SECONDS}.log"`,
      `echo "$(echo x > ${out}/x-$RANDOM.log)"`,
      `export BASHPID=${back}; cp base/report.md "${out}/$BASHPID"`,                    // round 2's zsh road
      `echo x > ${out}/x-$BASHPID.log`,
    ];
    // B2 (2026-09-19): a shape whose assignment is a plain string at the top level of its shell (`unset RANDOM; RANDOM=<back>;
    // cp … "<out>/$RANDOM"`, `export BASHPID=<back>; …`, the `bash -c`, `declare -g`, heredoc and `sh -c` twins) is RESOLVED,
    // so the guard names the tracked file the traversal lands on; the rest (a name set inside a function, a sourced file,
    // no assignment in sight) stay refused as words it cannot read. Either way the numeric narrowing never applies.
    const resolved = new Set(refused.filter((c) => /(unset (RANDOM|SECONDS); (declare -g )?(RANDOM|SECONDS)=|export BASHPID=|^sh -c 'RANDOM=)/.test(c) && !/f\(\)/.test(c)));
    assert.equal(resolved.size, 7, `the seven shapes B2 resolves: ${[...resolved].join(' | ')}`);
    const byName = (c) => (/^Track-changes is ON for /.test(evaluate(payload(c)) || '') ? 'refused by name' : verdictOf(c));
    assert.deepEqual(Object.fromEntries(refused.map((c) => [c, byName(c)])), Object.fromEntries(refused.map((c) => [c, resolved.has(c) ? 'refused by name' : REFUSED])));
    const allowed = [
      `echo x > "${out}/build-$$.log"`,                                                  // the pid, in every shell and spelling
      `echo x > ${out}/x-\${$}.log`,
      `sh -c 'echo x > ${out}/x-$$.log'`,
      `dash -c 'cp base/report.md ${out}/copy-$$.md'`,
      `bash -c 'echo x > ${out}/x-$$.log'`,
      `zsh -c 'echo x > ${out}/x-\${$}.log'`,
      `ksh -c 'echo x > ${out}/x-$$.log'`,
      `bash <<'EOF'\necho x > ${out}/x-$$.log\nEOF`,
      `echo "$(echo x > ${out}/x-$$.log)"`,
    ];
    assert.deepEqual(verdicts(allowed), allOf(allowed, 'allowed'));
    // the grammar: only the pid is numeric, under every shell
    for (const cmd of [`echo x > ${out}/x-$RANDOM.log`, `bash -c 'echo x > ${out}/x-$RANDOM.log'`, `zsh -c 'echo x > ${out}/x-\${SECONDS}.log'`, `sh -c 'echo x > ${out}/x-$RANDOM.log'`, `echo x > ${out}/x-$BASHPID.log`]) {
      assert.equal(extractWriteTargets(cmd, proj).unresolved[0].numeric, null, `not numeric: ${cmd}`);
    }
    for (const cmd of [`echo x > ${out}/x-$$.log`, `sh -c 'echo x > ${out}/x-$$.log'`, `bash -c 'echo x > ${out}/x-\${$}.log'`]) {
      assert.ok(extractWriteTargets(cmd, proj).unresolved[0].numeric, `numeric: ${cmd}`);
    }
    assert.deepEqual(lex(`echo x > ${out}/x-$RANDOM.log`).segments[0].redirects.map((r) => r.target.numeric), [false]);
    assert.deepEqual(lex(`echo x > ${out}/x-$RANDOM.log`, 'bash').segments[0].redirects.map((r) => r.target.numeric), [false], 'under bash by name too');
    assert.deepEqual(lex(`echo x > ${out}/x-$$.log`, 'sh').segments[0].redirects.map((r) => r.target.numeric), [true]);
    // the real shells: each road measured, the write landing on the tracked file through the assigned traversal
    const run = (sh, script) => spawnSync(sh, ['-c', script], { cwd: proj, encoding: 'utf8', env: { PATH: process.env.PATH, OUT: out, BACK: back } });
    const restore = () => fs.writeFileSync(report, original);
    const overwrites = (sh, script, why) => {
      const r = run(sh, script);
      assert.equal(r.status, 0, `${why}: ${r.stderr}`);
      assert.equal(fs.readFileSync(report, 'utf8'), 'an older copy\n', `${why}: the tracked file was overwritten`);
      restore();
    };
    for (const b of shellsFor(['bash'], 'the RANDOM roads in real bash')) {
      overwrites(b, 'unset RANDOM; RANDOM="$BACK"; cp base/report.md "$OUT/$RANDOM"', 'bash, unset then assign');
      overwrites(b, 'unset SECONDS; SECONDS="$BACK"; cp base/report.md "$OUT/$SECONDS"', 'bash, SECONDS');
      overwrites(b, 'f(){ local RANDOM="$BACK"; cp base/report.md "$OUT/$RANDOM"; }; f', 'bash, local inside a function');
      fs.writeFileSync(path.join(proj, 'setenv.sh'), 'unset RANDOM; RANDOM="$BACK"\n');
      overwrites(b, '. ./setenv.sh; cp base/report.md "$OUT/$RANDOM"', 'bash, the unset in a sourced file');
      run(b, 'RANDOM="$BACK"; echo x > "$OUT/$RANDOM"');
      assert.equal(fs.readFileSync(report, 'utf8'), original, 'the bare assignment alone is the one form bash refuses, the form round 2 measured');
    }
    for (const z of shellsFor(['zsh'], 'the RANDOM roads in real zsh')) {
      overwrites(z, 'f(){ typeset -h RANDOM; RANDOM="$BACK"; cp base/report.md "$OUT/$RANDOM"; }; f', 'zsh, typeset -h inside a function');
      const zr = run(z, 'unset RANDOM; RANDOM="$BACK"; echo x > "$OUT/$RANDOM"');
      assert.notEqual(zr.status, 0, 'zsh refuses the unset-then-assign road, the one round 2 measured');
      assert.equal(fs.readFileSync(report, 'utf8'), original);
    }
    if (shellsFor(['dash'], 'the RANDOM road in real dash').length) overwrites('dash', 'RANDOM="$BACK"; cp base/report.md "$OUT/$RANDOM"', 'dash, a plain assignment');
    // and the pid resists every road in each shell: an unset of `$` is not a valid name (a special builtin's error, which
    // ends a non-interactive zsh or dash, so it is measured on its own), and the write lands under digits
    for (const sh of shellsFor(['bash', 'zsh', 'dash'], 'the pid roads')) {
      const u = run(sh, 'unset "$" && printf "%s" "$$"');
      assert.ok(u.status !== 0 || /^\d+$/.test(u.stdout), `${sh}: an unset of $ fails (zsh, dash) or changes nothing (bash): ${u.stdout} ${u.stderr}`);
      const r = run(sh, 'cp base/report.md "$OUT/pid-$$"');
      assert.equal(r.status, 0, `${sh}: ${r.stderr}`);
      assert.equal(fs.readFileSync(report, 'utf8'), original, `${sh}: the tracked file is untouched`);
      assert.ok(fs.readdirSync(out).some((n) => /^pid-\d+$/.test(n)), `${sh}: the copy landed outside under a name of digits`);
    }
  } finally { fs.rmSync(out, { recursive: true, force: true }); fs.rmSync(path.join(proj, 'setenv.sh'), { force: true }); }
});

test('review round 3: every target the hook cannot read is measured against the project its own literal directory part sits in, absolute or relative, and the numeric folder refusal is the landing gate at any depth', () => {
  // Review round 3 (2026-09-19), three live overwrites against the head hook from a cwd in no project: (1) a RELATIVE
  // numeric target, `cp poison.md ../proj/notes/n$SECONDS.md`, was never measured against the project its prefix names
  // (the own-project step was gated on an absolute spelling) and overwrote a note tracked by folder; (2) a VARIABLE's
  // spelling, `cp x <proj>/notes/$N.md`, and a substitution's were never measured at all (the step was gated on the
  // numeric class), while `<proj>/notes/`, `<proj>/notes/log-0.md`, the glob and the numeric sibling were all refused;
  // (3) a glob with no match in a tracked folder, which bash writes under the pattern's own name, likewise. The step
  // now asks the literal directory part of every unreadable target the hook can place, resolving a relative one against
  // the write-time directory, in the refuse direction only: the prefix names the folder the write lands in or one above
  // it, never one below, so the widening can add refusals and never an allowance; a relative numeric target stays
  // refused from a cwd in a project even when it lands outside (docs/install.md states it). Both directions: the
  // untracked subfolder of the same project stays allowed in every spelling. Beside them, the class round 2's addendum
  // ruled for the first segment, restated: the landing gate on the literal directory part is folder-granular, so a
  // numeric folder name ANYWHERE that gate holds (`<root>/docs/x-$$/y.md`, docs/ holding a tracked file) is refused
  // from any cwd with the unknown-folder text, as `<root>/x-$$/y.md` is, and a numeric FILE name in such a folder
  // (`<root>/docs/build-$$.log`) is refused while its literal spelling passes, a deliberate false refusal stated in
  // decision 47 (a name-aware gate was weighed and not built). One stated residual stays open: a target whose literal
  // directory part sits outside every project but whose substitution carries `../` back in.
  const out = outsideDir();
  try {
    const neutral = path.join(out, 'neutral');
    fs.mkdirSync(neutral);
    fs.writeFileSync(path.join(neutral, 'src.md'), 'a source\n');
    fs.writeFileSync(path.join(out, 'src.md'), 'a source\n');
    const projD = path.join(out, 'projD');
    for (const d of ['.trackchanges', 'docs', 'notes', 'tmpsub']) fs.mkdirSync(path.join(projD, d), { recursive: true });
    fs.writeFileSync(path.join(projD, '.trackchanges', 'config.json'), JSON.stringify({ v: 2, tracked: ['docs/report.md', 'notes/'] }));
    fs.writeFileSync(path.join(projD, 'docs', 'report.md'), 'tracked prose\n');
    fs.writeFileSync(path.join(projD, 'notes', 'n0.md'), 'a tracked note\n');
    const refusedNaming = (cmd, cwd, root, why) => {
      const reason = evaluate(payload(cmd, cwd));
      assert.ok(reason && NOT_LITERAL.test(reason) && reason.includes(`Track-changes is ON in ${root},`), `${why}: ${cmd}: ${reason}`);
      assert.ok(!reason.includes(proj), `${why}: not the cwd's project: ${cmd}`);
    };
    for (const [cwd, rel, where] of [[neutral, '../projD', 'from a neutral cwd'], [out, 'projD', 'from the parent of the project']]) {
      // (1) the relative numeric spelling, by cp, tee and sed -i, and the literal spelling beside it
      for (const cmd of [`cp src.md ${rel}/notes/n$$.md`, `cp src.md ${rel}/notes/n\${$}.md`, `echo poison | tee ${rel}/notes/n$$.md`, `sed -i s/a/b/ ${rel}/notes/n$$.md`, `cp src.md ${rel}/docs/report$$.md`]) {
        refusedNaming(cmd, cwd, projD, `${where}, a relative numeric name into a tracked folder`);
      }
      assert.match(evaluate(payload(`cp src.md ${rel}/notes/n0.md`, cwd)), /^Track-changes is ON for /, `${where}, the literal spelling`);
      assert.equal(evaluate(payload(`cp src.md ${rel}/tmpsub/tmp-$$.log`, cwd)), null, `${where}, an untracked subfolder: allowed`);
      assert.equal(evaluate(payload('echo x > tmp-$$.log', cwd)), null, `${where}, a relative numeric name in a folder of no project: allowed`);
      // the relative folder spelling names the unknown folder AND the project, which the relative target does not carry
      const folder = evaluate(payload(`echo x > ${rel}/x-$$/y.md`, cwd));
      assert.ok(folder && /cannot tell which folder/.test(folder) && folder.includes('x-$$') && folder.includes(`and ${projD} tracks files`), `${where}, the relative folder spelling names the project: ${folder}`);
      // (2) a variable, a brace parameter, a substitution, a backtick, a brace list past the cap, and (3) a glob with no match
      for (const cmd of [
        `cp src.md ${projD}/notes/$N.md`, `cp src.md ${projD}/notes/\${N}.md`, `cp src.md ${projD}/notes/$(date +%s).md`, `cp src.md ${projD}/notes/\`echo n\`.md`,
        `tee ${projD}/notes/$N.md < src.md`, `sed -i s/a/b/ ${projD}/notes/$N.md`, `install -m 644 src.md ${projD}/docs/$N.md`, `echo poison > ${projD}/docs/$N.md`,
        `cp src.md ${projD}/notes/log-{1..600}.md`, `cp src.md ${projD}/notes/nomatch*.md`, `cp src.md ${projD}/x-$N/y.md`, `cp src.md ${rel}/notes/$N.md`,
      ]) refusedNaming(cmd, cwd, projD, `${where}, an unreadable name whose literal prefix is a tracked folder`);
      // class F (round 4, 2026-09-19): a NON-numeric expansion under a tracked root is now refused even in an
      // untracked subfolder, since a `../` in the value can climb back into tracked files; only a target outside
      // every project stays allowed (the substitution carrying `..` back in from a cwd in no project is the
      // documented residual). A numeric ($$) name in the untracked subfolder is allowed (line 731 above).
      for (const cmd of [`cp src.md ${projD}/tmpsub/$N.md`, `cp src.md ${projD}/tmpsub/plain-$N.log`, `cp src.md ${projD}/tmpsub/$SUB/y.md`]) {
        refusedNaming(cmd, cwd, projD, `${where}, a non-numeric expansion under the tracked root`);
      }
      // class E (round 4, 2026-09-19): `out` holds projD, so its literal head is a PARENT of a tracked root and the
      // expansion could spell it; both the whole-word variable and the substitution are refused naming projD beneath.
      for (const cmd of [`cp src.md ${out}/$N.md`, `cp src.md ${out}/$(echo ../projD)/notes/x.md`]) {
        const reason = evaluate(payload(cmd, cwd));
        assert.ok(reason && reason.includes(`sits above the tracked project`) && reason.includes(projD), `${where}, class E names the project beneath: ${cmd}: ${reason}`);
      }
    }
    // the numeric folder refusal is the landing gate at any depth, with the folder text; the numeric FILE name in such a
    // folder is the deliberate false refusal, beside its literal spelling
    const UNKNOWN = /cannot tell which folder/;
    for (const cwd of [neutral, proj, projD]) {
      const deep = evaluate(payload(`echo x > ${projD}/docs/x-$$/y.md`, cwd));
      assert.ok(deep && UNKNOWN.test(deep) && deep.includes('x-$$') && !NOT_LITERAL.test(deep), `docs/ holds a tracked file: the folder text at depth two: ${deep}`);
      assert.ok(!deep.split(`${projD}/docs/x-$$/y.md`).join('').includes(projD), 'the absolute target carries the project, which is not named again');
      assert.ok(deep.includes('Spell the folder out with a literal name of your own, or write outside that project') && !deep.includes('the name the shell would give it'), 'the remedy a person can take');
      assert.equal(evaluate(payload(`echo x > ${projD}/docs/x-4242/y.md`, cwd)), null, 'the literal folder spelling passes');
      const tracked = evaluate(payload(`echo x > ${projD}/notes/x-$$/y.md`, cwd));
      assert.ok(tracked && UNKNOWN.test(tracked), 'under the tracked notes/ the folder text too, where "write outside that project" is the remedy that works');
      assert.match(evaluate(payload(`echo x > ${projD}/notes/x-4242/y.md`, cwd)), /^Track-changes is ON for /, 'since the literal spelling there is a tracked file');
      const file = evaluate(payload(`echo x > ${projD}/docs/build-$$.log`, cwd));
      assert.ok(file && NOT_LITERAL.test(file) && !UNKNOWN.test(file) && file.includes(`Track-changes is ON in ${projD},`), `a numeric FILE name in a folder holding a tracked file: refused with the generic text: ${file}`);
      assert.equal(evaluate(payload(`echo x > ${projD}/docs/build-4242.log`, cwd)), null, 'while its literal spelling passes: the deliberate false refusal');
    }
    for (const cwd of [neutral, proj]) assert.equal(evaluate(payload(`echo x > ${projD}/tmpsub/x-$$/y.md`, cwd)), null, 'a numeric folder under an untracked folder: the gate is false, allowed from outside');
    const ownDeep = evaluate(payload(`echo x > ${projD}/tmpsub/x-$$/y.md`, projD));
    assert.ok(ownDeep && UNKNOWN.test(ownDeep), 'from its own cwd the cwd rule refuses it, and the text still names the folder, since the reason is the same');
    // the grammar carries the text and marks for every unreadable word
    const u = extractWriteTargets(`cp src.md ${projD}/notes/$N.md`, neutral).unresolved[0];
    assert.equal(u.text, `${projD}/notes/$N.md`);
    assert.equal(u.marks.slice(-5, -3), 'xx', 'the variable is marked as an expansion');
    assert.equal(u.numeric, null);
    assert.equal(extractWriteTargets(`cp src.md ${projD}/notes/$(date +%s).md`, neutral).unresolved[0].text, `${projD}/notes/\0.md`, 'a substitution stands as one NUL, so its place in the word is kept');
    // as a process, and in real zsh: the relative numeric copy lands raw in the folder tracked by name
    const run = (command, cwd) => spawnSync(process.execPath, [HOOK], { input: payload(command, cwd), encoding: 'utf8', env: hookEnv({ ROMP_SID }) });
    assert.equal(run('cp src.md ../projD/notes/n$$.md', neutral).status, 2);
    assert.equal(run(`cp src.md ${projD}/notes/$N.md`, neutral).status, 2);
    assert.equal(run('cp src.md ../projD/tmpsub/n$$.md', neutral).status, 0);
    for (const zsh of shellsFor(['zsh'], 'the numeric write in real zsh')) {
      const z = spawnSync(zsh, ['-c', 'cp src.md ../projD/notes/n$$.md'], { cwd: neutral, encoding: 'utf8', env: { PATH: process.env.PATH } });
      assert.equal(z.status, 0, z.stderr);
      assert.ok(fs.readdirSync(path.join(projD, 'notes')).some((n) => /^n\d+\.md$/.test(n)), 'a raw file under the tracked folder, named by the pid');
    }
  } finally { fs.rmSync(out, { recursive: true, force: true }); }
});

test('review round 3: a literal dollar is a literal dollar: a folder or a project whose name holds one is judged by that name, and only an expansion is a number to fill in', () => {
  // Review round 3 (2026-09-19): every `$` in a word's text read as an expansion, so a folder named `$dir` took the
  // unknown-folder refusal with a false reason and a remedy that changed nothing (the folder was already spelled out), and
  // the same reading in the other direction let a numeric write into a project whose root was named `p$x` pass (its root
  // segment could not "spell" itself with a run of digits, so the target read as outside) while the literal spelling was
  // refused; a literal-dollar segment in front of a link into the project hid the link the same way. The lexer marks the
  // characters an expansion stands for, and every reader decides on the marks: `\$dir`, `'$dir'` and a double-quoted
  // `\$dir` are the folder `$dir`. Both directions, from a cwd inside the project and one outside every project, beside
  // the plain-named twins.
  const out = outsideDir();
  try {
    fs.mkdirSync(path.join(proj, '$dir'));
    fs.mkdirSync(path.join(proj, 'plain'));
    const dollar = path.join(out, 'p$x');
    for (const d of ['.trackchanges', 'notes', 'docs']) fs.mkdirSync(path.join(dollar, d), { recursive: true });
    fs.writeFileSync(path.join(dollar, '.trackchanges', 'config.json'), JSON.stringify({ v: 2, tracked: ['notes/', 'docs/report.md'] }));
    fs.writeFileSync(path.join(dollar, 'docs', 'report.md'), 'tracked prose\n');
    const esc = (p) => p.replace(/\$/g, '\\$');
    // the literal-dollar folder: judged as its literal spelling, which is untracked, exactly as the plain folder is
    for (const spelling of [`"${proj}/\\$dir/x-$$.md"`, `'${proj}/$dir/x-'$$.md`, `${proj}/\\$dir/x-$$.md`]) {
      const inside = evaluate(payload(`echo x > ${spelling}`, proj));
      assert.ok(inside && NOT_LITERAL.test(inside) && !/cannot tell which folder/.test(inside), `from the project's cwd the generic text, as the plain twin gets: ${spelling}: ${inside}`);
      assert.equal(evaluate(payload(`echo x > ${spelling}`, out)), null, `from a cwd outside every project: allowed, as the plain twin is: ${spelling}`);
    }
    const plainTwin = evaluate(payload(`echo x > ${proj}/plain/x-$$.md`, proj));
    assert.ok(plainTwin && NOT_LITERAL.test(plainTwin) && !/cannot tell which folder/.test(plainTwin));
    assert.equal(evaluate(payload(`echo x > ${proj}/plain/x-$$.md`, out)), null);
    assert.equal(evaluate(payload(`echo x > "${proj}/\\$dir/x-4242.md"`, out)), null, 'the literal spelling of the file passes too');
    // the literal-dollar root: a numeric write into its tracked folder is refused from any cwd, naming the project, as
    // the literal spelling is refused; a fold onto its tracked file is the tracked file; its untracked folder is allowed
    for (const cwd of [dollar, proj, out]) {
      const reason = evaluate(payload(`echo x > "${esc(dollar)}/notes/rep-$$.md"`, cwd));
      assert.ok(reason && NOT_LITERAL.test(reason) && reason.includes(`Track-changes is ON in ${dollar},`), `the dollar root, numeric: ${reason}`);
      assert.match(evaluate(payload(`echo x > "${esc(dollar)}/notes/rep-4242.md"`, cwd)), /^Track-changes is ON for /, 'the literal spelling');
      assert.match(evaluate(payload(`mkdir -p "${esc(dollar)}/run-$$" && echo poison > "${esc(dollar)}/run-$$/../docs/report.md"`, cwd)), /^Track-changes is ON for /, 'the fold onto the tracked file');
      if (cwd !== dollar) assert.equal(evaluate(payload(`echo x > "${esc(dollar)}/scratch/log-$$.txt"`, cwd)), null, 'an untracked folder of the dollar root, from outside it: allowed');
    }
    // a literal dollar in a directory segment of a numeric target OUTSIDE every project, in front of a link into the
    // project: the link is resolved (before, the cut landed at the dollar and the link below it was never seen)
    fs.mkdirSync(path.join(out, '$lit'));
    fs.symlinkSync(path.join(proj, 'docs'), path.join(out, '$lit', 'dlink'));
    assert.match(evaluate(payload(`mkdir -p "${out}/run-$$" && echo poison > "${out}/run-$$/../\\$lit/dlink/report.md"`)), /^Track-changes is ON for /);
    assert.ok(evaluate(payload(`echo poison > "${out}/\\$lit/dlink/rep-$$.md"`)), 'the folder behind the link is the tracked docs/');
    assert.equal(evaluate(payload(`echo x > "${out}/\\$lit/x-$$.md"`)), null, 'and a numeric name beside the link, in the untracked folder, is allowed');
    // the grammar: a literal dollar is marked as text, an expansion as an expansion; a bare dollar is text
    const t = lex(`echo x > "${proj}/\\$dir/x-$$.md"`).segments[0].redirects[0].target;
    assert.equal(t.text, `${proj}/$dir/x-$$.md`);
    const at = t.text.indexOf('$dir');
    assert.equal(t.marks.slice(at, at + 4), 'qqqq', 'the escaped dollar and its name are quoted text');
    assert.equal(t.marks.slice(-5, -3), 'xx', 'the process id is an expansion');
    assert.ok(t.numeric, 'and the word is numeric-only');
    assert.deepEqual(targets('echo x > docs/x$'), [path.join(proj, 'docs', 'x$')], 'a bare dollar before nothing a shell expands is text in bash, zsh and dash: the word is literal');
    assert.deepEqual(targets('echo x > "docs/a$ b"'), [path.join(proj, 'docs', 'a$ b')]);
    assert.equal(evaluate(payload('echo x > docs/x$')), null, 'an untracked literal name with a dollar in it');
  } finally { fs.rmSync(out, { recursive: true, force: true }); }
});

test('review round 3: a literal relative target after a cd the hook cannot follow is refused with the reason while the cwd\'s project is in play, and passes from a cwd in none', () => {
  // Review round 3 (2026-09-19): a LITERAL relative target whose write-time directory the hook had lost (a `cd` to a
  // name the shell fills in, `cd -`, `popd`, a cd inside a body, or a cd to a directory the command cannot enter: one
  // that does not exist, a file, a dangling link, a mode-000 directory) was dropped from both lists, so `cd "$D" && cp
  // base/report.md docs/report.md` from the project passed and overwrote the tracked file in real bash (a cd of an
  // empty word returns 0 and stays put), while `cd "$D" && cp base/report.md "$T"` was refused: one unreadable cd
  // turned a refused write into an allowed one. Such a target is now refused with its own reason (the directory is
  // not known, and which construct lost it) and a remedy that works (an absolute target, or a cd to a literal
  // directory that exists); the generic text would say the word is not literal, which is false of it. From a cwd in
  // no project it passes as every unreadable target does; an absolute target after the same cd is judged as ever; a
  // cd to a directory that exists still moves the cwd. The cost, stated in decision 47: `mkdir -p sub && cd sub &&
  // cmd > log` from a tracked cwd is refused, since the directory is not there when the hook runs.
  const UNKNOWN_DIR = /the directory it is relative to is not known/;
  fs.mkdirSync(path.join(proj, 'locked'));
  fs.chmodSync(path.join(proj, 'locked'), 0);
  fs.symlinkSync(path.join(proj, 'nowhere'), path.join(proj, 'danglink'));
  const original = fs.readFileSync(report, 'utf8');
  try {
    const cases = [
      ['cd "$D" && cp base/report.md docs/report.md', 'names "$D", a directory the shell fills in'],
      ['cd "$(pwd)"; cp base/report.md docs/report.md', 'names "$(pwd)"'],
      ['cd -; cp base/report.md docs/report.md', 'an earlier `cd -`'],
      ['pushd docs; popd; cp base/report.md docs/report.md', 'an earlier `popd`'],
      ['if false; then cd /etc; fi; cp base/report.md docs/report.md', 'sits in an if, loop or case body that may not run'],
      ['for f in; do cd /etc; done; sed -i s/a/b/ docs/report.md', 'sits in an if, loop or case body'],
      ['cd nosuchdir; cp base/report.md docs/report.md', 'an earlier `cd nosuchdir` names a directory the command cannot enter when I check it'],
      ['cd locked; echo x > docs/report.md', 'an earlier `cd locked` names a directory the command cannot enter'],
      ['cd danglink; sed -i s/a/b/ docs/report.md', 'an earlier `cd danglink`'],
      ['cd base/report.md; cp base/report.md docs/report.md', 'an earlier `cd base/report.md`'],
      ['mkdir -p sub2 && cd sub2 && echo x > out.log', 'an earlier `cd sub2` names a directory the command cannot enter when I check it (it may be made first'],
      ['cd "$D" && cp base/report.md docs/other.md', 'names "$D"'],   // the untracked twin is refused too: the hook cannot tell them apart
    ];
    for (const [cmd, why] of cases) {
      const reason = evaluate(payload(cmd));
      assert.ok(reason && UNKNOWN_DIR.test(reason), `refused, the directory unknown: ${cmd}: ${reason}`);
      assert.ok(reason.includes(why), `saying why: ${cmd}: ${reason.split('\n')[0]}`);
      assert.ok(reason.includes('Spell the target as an absolute path, or cd to a literal directory that exists first'), 'and the remedy');
      assert.ok(!NOT_LITERAL.test(reason) && reason.includes(`and ${proj} tracks files`) && reason.includes('track-edit'), 'not the non-literal text; the project named; the remedy for a tracked file');
      assert.ok(!ROMP_NOUNS.test(reason.split(proj).join('<project>')) && !/\u2014/.test(reason), 'no romp noun and no em dash');
      assert.deepEqual(targets(cmd), [], `no literal target, the word could not be placed: ${cmd}`);
      assert.equal(extractWriteTargets(cmd, proj).unresolved.filter((u) => u.why && u.why.kind === 'unknownDir').length, 1, `the grammar records why: ${cmd}`);
    }
    const out = outsideDir();
    try {
      fs.mkdirSync(path.join(out, 'docs'));
      fs.mkdirSync(path.join(out, 'base'));
      fs.writeFileSync(path.join(out, 'base', 'report.md'), 'x\n');
      for (const [cmd] of cases.slice(0, 7)) assert.equal(evaluate(payload(cmd, out)), null, `from a cwd in no project: ${cmd}`);
      assert.equal(evaluate(payload(`cd "$D" && cp base/report.md ${out}/report.md`)), null, 'an absolute untracked target after the cd is judged as ever');
      assert.match(evaluate(payload(`cd "$D" && cp base/report.md ${report}`)), /^Track-changes is ON for /, 'and an absolute tracked one is refused by name');
      assert.equal(evaluate(payload(`cd "$D" && echo x > ${out}/x-$$.log`)), null, 'an absolute numeric one outside every project too');
    } finally { fs.rmSync(out, { recursive: true, force: true }); }
    assert.deepEqual(targets('cd notes; cp ../base/report.md ../docs/report.md'), [report], 'a cd to a directory that exists still moves the cwd');
    assert.match(evaluate(payload('cd notes; cp ../base/report.md ../docs/report.md')), /^Track-changes is ON for /);
    assert.deepEqual(targets('cd docs && echo x > other.md'), [other]);
    assert.equal(evaluate(payload('cd docs && echo x > other.md')), null, 'and a relative write there keeps its verdict');
    // as a process, and what the refused commands do in real bash: the cd of an empty word and the failed cd both
    // leave the shell where it was, so the copy runs in the project and the tracked file is overwritten unrecorded
    const run = (command) => spawnSync(process.execPath, [HOOK], { input: payload(command), encoding: 'utf8', env: hookEnv({ ROMP_SID }) });
    const refused = run('cd "$D" && cp base/report.md docs/report.md');
    assert.equal(refused.status, 2);
    assert.match(refused.stderr, UNKNOWN_DIR);
    assert.equal(run('cd docs && echo x > other.md').status, 0);
    for (const cmd of ['cd "$D" && cp base/report.md docs/report.md', 'cd nosuchdir; cp base/report.md docs/report.md']) {
      for (const sh of shellsFor(['bash'], cmd)) {
        const shell = spawnSync(sh, ['-c', cmd], { cwd: proj, encoding: 'utf8', env: { PATH: process.env.PATH } });
        assert.equal(shell.status, 0, shell.stderr);
        assert.equal(fs.readFileSync(report, 'utf8'), 'an older copy\n', `the tracked file was overwritten where the command started: ${cmd}`);
        fs.writeFileSync(report, original);
      }
    }
  } finally { fs.chmodSync(path.join(proj, 'locked'), 0o755); }
});

test('review round 3: a path is judged as the kernel opens it: a `..` after a link climbs from the link\'s target, a fold onto a link to a tracked file is the tracked file, and an entry the number could spell is followed', () => {
  // Review round 3 (2026-09-19), three overwrites of a tracked file in real bash against the head hook, each through a
  // spelling the kernel resolves differently from a lexical fold: (1) `<out>/ld/../docs/report.md` with ld a link to the
  // project's notes/: path.normalize dropped `ld/..` before any real-path step, the hook judged <out>/docs/report.md, and
  // the kernel, which follows the link first and climbs from its target, wrote the tracked file (a literal path, so the
  // literal rule too); (2) `<out>/run-$$/../linkfile` with linkfile a link to the tracked file: the fold left a literal
  // path, numericOutside resolved only its directory part and re-appended the name unresolved, and the link was never
  // followed; (3) `<out>/x-$$/report.md` with `<out>/x-4242` an existing link into the project's docs/: the number could
  // spell the entry's name, and nothing resolved it (round 2's case used `$SECONDS`, 0 in a fresh shell; with the set
  // the process id alone the entry must be one the pid could spell, so it is made here beside the command). Each is
  // refused now, naming the file the write lands on; the plain fold to a path outside stays allowed; a link OUT of the
  // project followed by `..` lands outside and is allowed (before, a false refusal naming a file the command never
  // touched); an entry the number cannot spell changes nothing. The scan for such entries is bounded: a folder outside
  // every project that holds more than 2000 entries is not listed (the header says why: this box's /tmp holds
  // thousands, and a fail-closed cap would refuse every temp log in it from a tracked cwd), pinned on both sides so the
  // boundary is a choice rather than an accident.
  const out = outsideDir();
  const original = fs.readFileSync(report, 'utf8');
  try {
    fs.symlinkSync(path.join(proj, 'notes'), path.join(out, 'ld'));
    fs.symlinkSync(report, path.join(out, 'linkfile'));
    fs.symlinkSync(path.join(proj, 'docs'), path.join(out, 'x-4242'));
    fs.symlinkSync(report, path.join(out, 'f-4242'));
    fs.mkdirSync(path.join(out, 'sub'));
    fs.symlinkSync(path.join(out, 'sub'), path.join(proj, 'lnk'));
    // (1) the literal fold: from the project, from a cwd in no project, relative, as a redirect, and after a cd through the link
    for (const [cmd, cwd] of [
      [`cp base/report.md ${out}/ld/../docs/report.md`, proj],
      [`cp ${proj}/base/report.md ${out}/ld/../docs/report.md`, out],
      [`echo poison > ${out}/ld/../docs/report.md`, proj],
      [`cp base/report.md ../${path.basename(out)}/ld/../docs/report.md`, proj],
      [`cd ${out}/ld && cp ${proj}/base/report.md ../docs/report.md`, out],
    ]) {
      assert.deepEqual(targets(cmd, cwd), [report], `resolved as the kernel would: ${cmd}`);
      assert.match(evaluate(payload(cmd, cwd)), /^Track-changes is ON for /, `refused by name: ${cmd}`);
    }
    assert.deepEqual(targets(`cp base/report.md ${proj}/lnk/../plain.md`), [path.join(out, 'plain.md')], 'a link out of the project then ..: the write lands outside');
    assert.equal(evaluate(payload(`cp base/report.md ${proj}/lnk/../plain.md`)), null, 'and is allowed, where before it was refused naming a file the command never touches');
    assert.deepEqual(targets(`cp base/report.md ${out}/nodir/../docs/report.md`), [path.join(out, 'docs', 'report.md')], 'a .. after a directory that does not exist folds lexically, as it did');
    // (2) the numeric fold onto a link file, and the numeric fold through the link directory into the tracked folder
    for (const cwd of [proj, out]) {
      const reason = evaluate(payload(`mkdir -p ${out}/run-$$ && echo x > ${out}/run-$$/../linkfile`, cwd));
      assert.ok(reason && reason.startsWith(`Track-changes is ON for ${path.join(out, 'linkfile')}`), `the fold lands on the link to the tracked file: ${reason}`);
      assert.ok(reason.includes('track-edit') && reason.includes(`--file '${path.join(out, 'linkfile')}'`), 'with the literal remedy');
      assert.ok(evaluate(payload(`cp base/report.md ${out}/ld/../notes/n-$$.md`, cwd)), 'a numeric name after a link and ..: the folder is the tracked notes/');
      assert.equal(evaluate(payload(`echo x > ${out}/run-$$/../plain.log`, cwd)), null, 'the fold to a plain path outside stays allowed');
    }
    // (3) an entry that exists now whose name the number could spell, at the folder position and at the file position
    for (const cwd of [proj, out]) {
      for (const cmd of [`echo x > ${out}/x-$$/report.md`, `cp base/report.md ${out}/x-\${$}/report.md`, `echo x > ${out}/f-$$`]) {
        const reason = evaluate(payload(cmd, cwd));
        assert.ok(reason && /^Track-changes is ON for /.test(reason) && reason.includes(report), `the spelled entry leads to the tracked file: ${cmd}: ${reason}`);
      }
      assert.equal(evaluate(payload(`echo x > ${out}/nope-$$/report.md`, cwd)), null, 'no entry the number could spell: allowed');
      assert.equal(evaluate(payload(`echo x > ${out}/x-$$.log`, cwd)), null, 'the file position, no such entry: allowed');
    }
    // the scan's bound, both sides: past LANDING_SCAN_CAP entries a folder no project claims is not listed
    const big = path.join(out, 'big');
    fs.mkdirSync(big);
    for (let k = 0; k < 2000; k++) fs.writeFileSync(path.join(big, `e${k}`), '');
    fs.symlinkSync(path.join(proj, 'docs'), path.join(big, 'x-4242'));
    assert.equal(fs.readdirSync(big).length, 2001);
    assert.equal(evaluate(payload(`echo x > ${big}/x-$$/report.md`)), null, 'past the cap the folder is not listed: the stated residual');
    fs.rmSync(path.join(big, 'e1999'));
    assert.match(evaluate(payload(`echo x > ${big}/x-$$/report.md`)), /^Track-changes is ON for /, 'at the cap the entry is found');
    // as a process, and in real bash: the fold the hook refuses lands on the tracked file
    const run = (command) => spawnSync(process.execPath, [HOOK], { input: payload(command), encoding: 'utf8', env: hookEnv({ ROMP_SID }) });
    assert.equal(run(`cp base/report.md ${out}/ld/../docs/report.md`).status, 2);
    assert.equal(run(`mkdir -p ${out}/run-$$ && echo x > ${out}/run-$$/../linkfile`).status, 2);
    assert.equal(run(`echo x > ${out}/x-$$/report.md`).status, 2);
    assert.equal(run(`echo x > ${out}/run-$$/../plain.log`).status, 0);
    for (const sh of shellsFor(['bash'], 'the climb from the link target in real bash')) {
      const shell = spawnSync(sh, ['-c', `cp base/report.md ${out}/ld/../docs/report.md`], { cwd: proj, encoding: 'utf8', env: { PATH: process.env.PATH } });
      assert.equal(shell.status, 0, shell.stderr);
      assert.equal(fs.readFileSync(report, 'utf8'), 'an older copy\n', 'the kernel climbed from the link target: the tracked file was overwritten');
      fs.writeFileSync(report, original);
    }
  } finally { fs.rmSync(out, { recursive: true, force: true }); }
});

test('review round 3: $\'...\' is ANSI-C quoting in bash and zsh, a literal word with its escapes processed; under a script handed to sh it is a word the hook cannot read; $"..." stays one; a bare $ is text', () => {
  // Review round 3 (2026-09-19): `$'<tracked path>'` lexed as an opaque `$` and a quoted string, a non-literal word whose
  // text began with `$`, so it was dropped from a cwd in no project (not absolute, so the own-project step skipped it)
  // and bash and zsh, which both read ANSI-C quoting, wrote the tracked file; `cd $'<proj>/docs' && cp x report.md` did
  // the same through the cd. bash and zsh agree on `$'...'`, so at the top level and inside a script handed to either it
  // is a literal word (`\'` does not end it, `\x6f` is `o`); dash, `/bin/sh` here, reads a literal dollar and a
  // single-quoted string, and bash in POSIX mode reads ANSI-C quoting, so inside a script handed to `sh`, `dash` or
  // `ksh` the word is one the hook cannot read, its text the path bash would write, and the own-project step judges
  // that spelling from any cwd. `$"..."` is bash's locale translation and a literal dollar in zsh: read with the
  // double-quote rules and kept non-literal, its text the body. A bare `$` before anything else is a literal dollar in
  // bash, zsh and dash alike, so the word stays literal. Both directions throughout.
  const out = outsideDir();
  try {
    for (const cwd of [out, proj]) {
      for (const cmd of [
        `cp ${proj}/base/report.md $'${proj}/docs/report.md'`,
        `cp ${proj}/base/report.md $'${proj}/docs/rep\\x6frt.md'`,
        `bash -c "cp ${proj}/base/report.md \\$'${proj}/docs/report.md'"`,
        `zsh -c "cp ${proj}/base/report.md \\$'${proj}/docs/report.md'"`,
        `cd $'${proj}/docs' && cp ${proj}/base/report.md report.md`,
      ]) {
        assert.deepEqual(targets(cmd, cwd), [report], `a literal word, the escapes processed: ${cmd}`);
        assert.match(evaluate(payload(cmd, cwd)), /^Track-changes is ON for /, `refused by name: ${cmd}`);
      }
      assert.equal(evaluate(payload(`cp ${proj}/base/report.md $'${out}/x.md'`, cwd)), null, 'an untracked ANSI-C target passes');
      assert.deepEqual(targets(`echo x > $'${out}/it\\'s.md'`, cwd), [path.join(out, "it's.md")], 'an escaped quote does not end it');
      // under sh: not literal, judged by the path bash would write, from any cwd
      const sh = evaluate(payload(`sh -c "cp ${proj}/base/report.md \\$'${proj}/docs/report.md'"`, cwd));
      assert.ok(sh && NOT_LITERAL.test(sh) && sh.includes(`Track-changes is ON in ${proj},`), `under sh the word is one the hook cannot read, judged by its own project: ${sh}`);
      assert.deepEqual(targets(`sh -c "cp ${proj}/base/report.md \\$'${proj}/docs/report.md'"`, cwd), [], 'no literal target under sh');
      // $"...": not literal, judged by its own project
      const locale = evaluate(payload(`cp ${proj}/base/report.md $"${proj}/docs/report.md"`, cwd));
      assert.ok(locale && NOT_LITERAL.test(locale) && locale.includes(`Track-changes is ON in ${proj},`), `$"..." is a word the hook cannot read: ${locale}`);
    }
    assert.equal(evaluate(payload(`sh -c "cp ${proj}/base/report.md \\$'${out}/x.md'"`, out)), null, 'under sh, outside every project, it passes');
    assert.equal(evaluate(payload(`cp base/report.md $"${out}/x.md"`, out)), null);
    assert.ok(evaluate(payload(`cp base/report.md $"${out}/x.md"`, proj)), 'from a tracked cwd the unreadable word is refused, as any is');
    // a bare dollar is text
    assert.deepEqual(targets('echo x > docs/x$'), [path.join(proj, 'docs', 'x$')]);
    assert.equal(evaluate(payload('echo x > docs/x$')), null);
    // in real bash and zsh: the ANSI-C spelling names the tracked file; dash reads a literal dollar
    const original = fs.readFileSync(report, 'utf8');
    for (const sh of shellsFor(['bash', 'zsh'], "the ANSI-C spelling in real bash and zsh")) {
      const r = spawnSync(sh, ['-c', `cp ${proj}/base/report.md $'${proj}/docs/report.md'`], { cwd: out, encoding: 'utf8', env: { PATH: process.env.PATH } });
      assert.equal(r.status, 0, r.stderr);
      assert.equal(fs.readFileSync(report, 'utf8'), 'an older copy\n', `${sh}: the tracked file was overwritten through $'...'`);
      fs.writeFileSync(report, original);
    }
    // round 5: through the probe, the assertion unconditional (it was skipped in silence, with no NOT RUN line, when dash was absent)
    for (const dsh of shellsFor(['dash'], 'the literal dollar in real dash')) {
      const d = spawnSync(dsh, ['-c', "printf '%s' $'/x/y.md'"], { encoding: 'utf8' });
      assert.equal(d.status, 0, d.stderr);
      assert.equal(d.stdout, '$/x/y.md', 'dash reads a literal dollar and a single-quoted string');
    }
  } finally { fs.rmSync(out, { recursive: true, force: true }); }
});

test('review round 3: a copy whose name the hook cannot read into a folder no project claims is refused when an entry there is or leads to a tracked file, naming that file\'s project', () => {
  // Review round 3 (2026-09-19): `cp "$SRC" <outside>/` with <outside>/report.md a link onto the tracked file was
  // allowed from every cwd (the landing branch returned at trackingRootAt's null and never scanned the folder, though
  // round 1's scan exists for exactly this shape inside a project) and overwrote the tracked file, while `cp
  // base/report.md <outside>/report.md` and the glob spelling were refused; the same with the folder under a project
  // whose list tracks nothing, and under a bare repository root. The folder is scanned now, the hit carries the project
  // of the file the entry leads to, and the refusal names that entry. Bounded: past LANDING_SCAN_CAP entries a folder no
  // project claims is not scanned and the copy passes (the opposite of the in-project cap, stated), both sides pinned.
  const out = outsideDir();
  try {
    fs.symlinkSync(report, path.join(out, 'report.md'));
    const gitonly = path.join(out, 'gitonly');
    fs.mkdirSync(path.join(gitonly, '.git'), { recursive: true });
    fs.mkdirSync(path.join(gitonly, 'out'));
    fs.symlinkSync(report, path.join(gitonly, 'out', 'report.md'));
    const empty = path.join(out, 'empty');
    fs.mkdirSync(path.join(empty, '.trackchanges'), { recursive: true });
    fs.mkdirSync(path.join(empty, 'out'));
    fs.writeFileSync(path.join(empty, '.trackchanges', 'config.json'), JSON.stringify({ v: 2, tracked: [] }));
    fs.symlinkSync(report, path.join(empty, 'out', 'report.md'));
    const plain = path.join(out, 'plain');
    fs.mkdirSync(plain);
    fs.writeFileSync(path.join(plain, 'other.md'), 'x\n');
    for (const cwd of [proj, out]) {
      for (const folder of [out, path.join(gitonly, 'out'), path.join(empty, 'out')]) {
        for (const cmd of [`cp "$SRC" ${folder}/`, `cp -t ${folder} "$SRC"`, `mv "$SRC" ${folder}/`, `install -m 644 "$SRC" ${folder}/`]) {
          const reason = evaluate(payload(cmd, cwd));
          assert.ok(reason && NOT_LITERAL.test(reason) && reason.includes(`Track-changes is ON in ${proj},`), `refused, naming the project the entry leads to: ${cmd}: ${reason}`);
          assert.ok(reason.includes(`${folder} holds report.md, which is or leads to a tracked file of that project`), `and the entry: ${reason.split('\n')[0]}`);
        }
        assert.match(evaluate(payload(`cp base/report.md ${folder}/report.md`, proj)), /^Track-changes is ON for /, 'as the literal spelling is');
      }
      assert.equal(evaluate(payload(`cp "$SRC" ${plain}/`, cwd)), null, 'a folder no project claims with nothing guarded in it: allowed');
      assert.equal(evaluate(payload(`cp "$SRC" ${out}/nowhere/`, cwd)), null, 'a folder that does not exist: allowed');
    }
    // the bound, both sides
    const big = path.join(out, 'big');
    fs.mkdirSync(big);
    for (let k = 0; k < 2000; k++) fs.writeFileSync(path.join(big, `e${k}`), '');
    fs.symlinkSync(report, path.join(big, 'report.md'));
    assert.equal(fs.readdirSync(big).length, 2001);
    assert.equal(evaluate(payload(`cp "$SRC" ${big}/`)), null, 'past LANDING_SCAN_CAP a folder no project claims is not scanned: the stated residual');
    fs.rmSync(path.join(big, 'e1999'));
    assert.ok(evaluate(payload(`cp "$SRC" ${big}/`)), 'at the cap the entry is found');
    // as a process, and in real bash: the copy lands on the tracked file through the link
    const run = (command, cwd) => spawnSync(process.execPath, [HOOK], { input: payload(command, cwd), encoding: 'utf8', env: hookEnv({ ROMP_SID }) });
    assert.equal(run(`cp "$SRC" ${out}/`, proj).status, 2);
    assert.equal(run(`cp "$SRC" ${plain}/`, proj).status, 0);
    const original = fs.readFileSync(report, 'utf8');
    for (const sh of shellsFor(['bash'], 'the copy into the outside folder in real bash')) {
      const shell = spawnSync(sh, ['-c', `cp "$SRC" ${out}/`], { cwd: proj, encoding: 'utf8', env: { PATH: process.env.PATH, SRC: 'base/report.md' } });
      assert.equal(shell.status, 0, shell.stderr);
      assert.equal(fs.readFileSync(report, 'utf8'), 'an older copy\n', 'the tracked file was overwritten through the link in the outside folder');
      fs.writeFileSync(report, original);
    }
  } finally { fs.rmSync(out, { recursive: true, force: true }); }
});


test('review round 3 addendum: numericOutside compares three spellings against a root in play, each pinned where it alone refuses: the target\'s own, where an expansion segment that could spell the root\'s segment is not diverging; its literal directory part resolved; and every entry the number could spell', () => {
  // The mutation pass over round 3 (2026-09-19) found the three spellings numericOutside compares unpinned: with any one
  // dropped every test stayed green, since the shapes the rounds pinned were refused before numericOutside was asked (a
  // candidate whose literal path is a tracked file, a link whose real folder is one where a tracked file could land: the
  // own-project step). Each spelling is pinned here by a shape that reaches numericOutside with that step silent, and each
  // refusal is a rule already ruled: a numeric write that could land inside the cwd's project is refused from that cwd
  // (`<proj>/plain/x-$$.md` in the refused corpus) and allowed from a cwd in none. (1) The target's own spelling: a
  // project at `<big>/build-4242` and the write `<big>/build-$$/x.md`, with <big> holding more than LANDING_SCAN_CAP
  // entries, so no entry of it is listed and the segment comparison is all that stands between the number and the root;
  // at the cap the listed entry refuses first, naming the tracked file, so the two mechanisms hand over at the boundary.
  // (2) The literal directory part resolved: `<out>/linkplain`, a link into an UNTRACKED folder of the project (the
  // landing gate is false there), judged as its plain twin is. (3) An entry the number could spell that is a link to the
  // project ROOT, the write landing in an untracked folder under it (`<out>/x-$$/scratch/y.md`, `<out>/x-4242` the link):
  // the candidate's literal path is not tracked and its folder fails the landing gate, and the write lands inside the
  // cwd's project all the same. Beside each, the shape that diverges: a segment whose literal pieces cannot fit, and an
  // entry the number cannot spell.
  const out = outsideDir();
  const UNKNOWN = /cannot tell which folder/;
  try {
    // (1) the root's own segment, past the cap
    const big = path.join(out, 'big');
    fs.mkdirSync(big);
    for (let k = 0; k < 2000; k++) fs.writeFileSync(path.join(big, `e${k}`), '');
    const digits = path.join(big, 'build-4242');
    fs.mkdirSync(path.join(digits, '.trackchanges'), { recursive: true });
    fs.writeFileSync(path.join(digits, '.trackchanges', 'config.json'), JSON.stringify({ v: 2, tracked: ['x.md'] }));
    assert.equal(fs.readdirSync(big).length, 2001, 'past the cap: no entry of the folder is listed');
    const own = evaluate(payload(`echo x > ${big}/build-$$/x.md`, digits));
    assert.ok(own && UNKNOWN.test(own) && own.includes('build-$$') && !/^Track-changes is ON for /.test(own), `the root's own segment could be spelled by the number, with no entry listed: ${own}`);
    assert.equal(evaluate(payload(`echo x > ${big}/other-$$/x.md`, digits)), null, 'a segment whose literal pieces cannot fit diverges');
    assert.equal(evaluate(payload(`echo x > ${big}/build-4242x-$$.log`, digits)), null, 'a sibling name, not the root');
    assert.equal(evaluate(payload(`echo x > ${big}/build-$$/x.md`, out)), null, 'from a cwd in no project the root is not in play, and past the cap the entry is not listed: the stated residual');
    fs.rmSync(path.join(big, 'e1999'));
    assert.match(evaluate(payload(`echo x > ${big}/build-$$/x.md`, digits)), /^Track-changes is ON for /, 'at the cap the listed entry refuses first, naming the tracked file');
    assert.match(evaluate(payload(`echo x > ${big}/build-$$/x.md`, out)), /^Track-changes is ON for /, 'from any cwd');
    // (2) the literal directory part resolved: a link into an untracked folder of the project
    fs.mkdirSync(path.join(proj, 'plain'));
    fs.symlinkSync(path.join(proj, 'plain'), path.join(out, 'linkplain'));
    for (const cmd of [`echo x > ${out}/linkplain/x-$$.md`, `cp base/report.md ${out}/linkplain/c-$$.md`, `tee ${out}/linkplain/t-\${$}.md < base/report.md`]) {
      const reason = evaluate(payload(cmd, proj));
      assert.ok(reason && NOT_LITERAL.test(reason) && reason.includes(`Track-changes is ON in ${proj},`), `from the project's cwd the link into its untracked folder is judged as that folder: ${cmd}: ${reason}`);
      assert.equal(evaluate(payload(cmd, out)), null, `from a cwd in no project it is allowed, as the plain twin is: ${cmd}`);
    }
    const twin = evaluate(payload(`echo x > ${proj}/plain/x-$$.md`, proj));
    assert.ok(twin && NOT_LITERAL.test(twin), 'the plain twin, refused from the project\'s cwd');
    assert.equal(evaluate(payload(`echo x > ${proj}/plain/x-$$.md`, out)), null, 'and allowed from a cwd in none');
    assert.equal(evaluate(payload(`echo x > ${out}/linkplain/x-4242.md`, proj)), null, 'the literal spelling through the link is an untracked file');
    // (3) an entry the number could spell, a link to the project root, the write landing in an untracked folder under it
    fs.symlinkSync(proj, path.join(out, 'x-4242'));
    for (const cmd of [`echo x > ${out}/x-$$/scratch/y.md`, `cp base/report.md ${out}/x-\${$}/scratch/y.md`]) {
      const reason = evaluate(payload(cmd, proj));
      assert.ok(reason && UNKNOWN.test(reason) && reason.includes(`and ${proj} tracks files`) && !NOT_LITERAL.test(reason), `the entry the number could spell leads into the cwd's project: ${cmd}: ${reason}`);
      assert.equal(evaluate(payload(cmd, out)), null, `from a cwd in no project the candidate lands in an untracked folder: allowed: ${cmd}`);
    }
    assert.equal(evaluate(payload(`echo x > ${out}/nope-$$/scratch/y.md`, proj)), null, 'no entry the number could spell: allowed');
    assert.equal(evaluate(payload(`echo x > ${out}/x-4242/scratch/y.md`, proj)), null, 'the literal spelling lands in the untracked folder');
    // as a process
    const run = (command, cwd) => spawnSync(process.execPath, [HOOK], { input: payload(command, cwd), encoding: 'utf8', env: hookEnv({ ROMP_SID }) });
    assert.equal(run(`echo x > ${out}/linkplain/x-$$.md`, proj).status, 2);
    assert.equal(run(`echo x > ${out}/x-$$/scratch/y.md`, proj).status, 2);
    assert.equal(run(`echo x > ${out}/linkplain/x-$$.md`, out).status, 0);
  } finally { fs.rmSync(out, { recursive: true, force: true }); }
});

test('review round 3 addendum: couldSpell reads a literal dollar as itself, never as a run of digits: an existing entry spelled around the dollar is followed, and one with digits where the dollar sits is not', () => {
  // Round 3 made a literal dollar literal in every reader (the literal-dollar test above), and the mutation pass
  // (2026-09-19) found couldSpell's share of that unpinned: with a literal dollar read as digits every test stayed
  // green, since the dollar-root shapes were refused by the landing gate before any entry was spelled. Both directions,
  // from a cwd in no project (the candidate scan is then the only road to a refusal) and from the project's cwd:
  // `<out>/p$x-4242`, a link into the tracked docs/, is an entry `"<out>/p\$x-$$/report.md"` could spell, so the write
  // is refused naming the tracked file; `<out>/q7x-4242`, the same link, is NOT one `"<out>/q\$x-$$/report.md"` could
  // spell, so that write is allowed; and `<out>/p5x-4242`, a link to a plain folder, is not the dollar spelling's entry
  // either, so with `p$x-4242` gone the first write passes: the refusal rested on the entry the dollar spells.
  const out = outsideDir();
  try {
    fs.mkdirSync(path.join(out, 'plainfolder'));
    fs.symlinkSync(path.join(proj, 'docs'), path.join(out, 'p$x-4242'));
    fs.symlinkSync(path.join(out, 'plainfolder'), path.join(out, 'p5x-4242'));
    fs.symlinkSync(path.join(proj, 'docs'), path.join(out, 'q7x-4242'));
    for (const cwd of [out, proj]) {
      const spelled = evaluate(payload(`echo x > "${out}/p\\$x-$$/report.md"`, cwd));
      assert.ok(spelled && /^Track-changes is ON for /.test(spelled) && spelled.includes(report), `the entry the dollar spelling could name leads to the tracked file: ${spelled}`);
      assert.equal(evaluate(payload(`echo x > "${out}/q\\$x-$$/report.md"`, cwd)), null, 'a digit where the dollar sits is not the dollar: no such entry, allowed');
      assert.equal(evaluate(payload(`echo x > "${out}/p5x-$$/report.md"`, cwd)), null, 'the digit spelling names the plain folder\'s link: allowed');
      assert.match(evaluate(payload(`echo x > "${out}/p\\$x-4242/report.md"`, cwd)), /^Track-changes is ON for /, 'the literal spelling through the link');
    }
    // the grammar: the dollar is quoted text and the number the expansion, in one numeric-only word
    const t = lex(`echo x > "${out}/p\\$x-$$/report.md"`).segments[0].redirects[0].target;
    const at = t.text.indexOf('p$x-');
    assert.equal(t.text.slice(at), 'p$x-$$/report.md');
    assert.equal(t.marks.slice(at, at + 6), 'qqqqxx');
    assert.ok(t.numeric);
    fs.unlinkSync(path.join(out, 'p$x-4242'));
    for (const cwd of [out, proj]) assert.equal(evaluate(payload(`echo x > "${out}/p\\$x-$$/report.md"`, cwd)), null, 'with that entry gone the write passes: the refusal rested on the entry the dollar spells, not on the digit twin');
  } finally { fs.rmSync(out, { recursive: true, force: true }); }
});

test('review round 3 addendum: a directory before a `..` that exists but cannot be resolved, a link that loops, is refused as unresolvable with the reason and the remedy, for a literal target and a numeric one, where a lexical fold would let the climb out or misname the file', () => {
  // foldSegments answers { unresolvable } for a literal directory before a `..` that exists but has no real path, and
  // evaluate refuses such a target with its own reason (round 3). The mutation pass (2026-09-19) found that refusal
  // unpinned: folding the prefix lexically instead kept every test green. Pinned with a link that points at itself and a
  // ring of two: the kernel cannot open a path through either, so the hook cannot say where the write lands, and a
  // lexical fold would let `loop/../../plain.md` climb out of the project (allowed) and read `loop/../docs/report.md` as
  // the tracked file by name (refused, with the wrong reason). The literal target is refused with the unresolvable text,
  // naming the construct, the directory and the remedy; the numeric one (`<proj>/loop/../../x-$$.md`) is not narrowed,
  // since its view is unresolvable, and takes the generic refusal; a `..` after a directory that resolves keeps its
  // verdict. Measured with it and reported with the addendum rather than pinned: a dangling link before a `..` is
  // followed to where its target would be, as realPathOf resolves it, and a directory the hook may not search fails the
  // lstat before the fold's check.
  const UNRESOLVABLE = /a directory on that path, is one I cannot resolve/;
  fs.symlinkSync(path.join(proj, 'loop'), path.join(proj, 'loop'));
  fs.symlinkSync(path.join(proj, 'ring-b'), path.join(proj, 'ring-a'));
  fs.symlinkSync(path.join(proj, 'ring-a'), path.join(proj, 'ring-b'));
  const cases = [
    ['cp base/report.md loop/../../plain.md', 'cp', `${proj}/loop`],
    ['cp base/report.md loop/../docs/report.md', 'cp', `${proj}/loop`],
    ['echo x > loop/../docs/report.md', '> redirection', `${proj}/loop`],
    [`sed -i s/a/b/ ${proj}/ring-a/../docs/report.md`, 'sed -i', `${proj}/ring-a`],
    ['cp base/report.md ring-a/../../plain.md', 'cp', `${proj}/ring-a`],
  ];
  for (const [cmd, how, dir] of cases) {
    const reason = evaluate(payload(cmd));
    assert.ok(reason && UNRESOLVABLE.test(reason), `refused as unresolvable: ${cmd}: ${reason}`);
    assert.ok(reason.includes(`its ${how} names `) && reason.includes(`and ${dir}, a directory on that path`), `naming the construct and the directory: ${reason.split('\n')[0]}`);
    assert.ok(reason.includes('Spell the path without that directory') && reason.includes(`and ${proj} tracks files`) && reason.includes('track-edit'), 'the remedy, the project, and the tracked-file road');
    assert.ok(!NOT_LITERAL.test(reason) && !/^Track-changes is ON for /.test(reason), `not the non-literal text and not a refusal by name: ${reason.split('\n')[0]}`);
    assert.ok(!ROMP_NOUNS.test(reason.split(proj).join('<project>')) && !/\u2014/.test(reason), 'no romp noun and no em dash');
    assert.deepEqual(targets(cmd), [], `no literal target, the path could not be resolved: ${cmd}`);
    assert.deepEqual(extractWriteTargets(cmd, proj).unresolved.map((u) => u.why), [{ kind: 'unresolvable', text: dir }], `the grammar records why: ${cmd}`);
  }
  const numeric = evaluate(payload(`echo x > ${proj}/loop/../../x-$$.md`));
  assert.ok(numeric && NOT_LITERAL.test(numeric) && numeric.includes(`Track-changes is ON in ${proj},`), `a numeric target through the loop is not narrowed: ${numeric}`);
  assert.deepEqual(targets('cp base/report.md docs/../base/copy.md'), [path.join(proj, 'base', 'copy.md')], 'a `..` after a directory that resolves folds as ever');
  assert.equal(evaluate(payload('cp base/report.md docs/../base/copy.md')), null);
  const run = (command) => spawnSync(process.execPath, [HOOK], { input: payload(command), encoding: 'utf8', env: hookEnv({ ROMP_SID }) });
  const refused = run('cp base/report.md loop/../../plain.md');
  assert.equal(refused.status, 2);
  assert.match(refused.stderr, UNRESOLVABLE);
  assert.equal(run(`echo x > ${proj}/loop/../../x-$$.md`).status, 2);
  // in real bash the kernel refuses the path too: nothing is written through a link that loops
  for (const sh of shellsFor(['bash'], 'the looping link in real bash')) {
    const shell = spawnSync(sh, ['-c', 'cp base/report.md loop/../../plain.md; cp base/report.md loop/../docs/report.md'], { cwd: proj, encoding: 'utf8', env: { PATH: process.env.PATH } });
    assert.notEqual(shell.status, 0);
    assert.match(shell.stderr, /Too many levels of symbolic links/);
    assert.equal(fs.readFileSync(report, 'utf8'), 'The api session cut tail latency by 40%.\n', 'the tracked file is untouched');
  }
});

test('review round 3 addendum: the own-project cut for a word with an expansion the hook does not read is at the first expansion mark, not the first dollar in the text: a variable under a root whose name holds a dollar is refused naming that project, from a cwd in none and from another project\'s', () => {
  // Round 3's rule that every reader decides on the marks, never on the text, was pinned for the fold, for couldSpell
  // and for a numeric target's literal directory part; the mutation pass (2026-09-19) found ownProjectFor's cut for a
  // non-numeric word unpinned: a cut at the first `$` in the text kept every test green, since no test put a variable
  // or a substitution under a root whose name holds a dollar. Here `"<out>/p\$x/notes/$N.md"` names a tracked folder of
  // the project at `<out>/p$x`: cut at the mark, the literal directory part is that folder and the write is refused
  // naming that project from a cwd in no project and from another project's cwd; cut at the dollar in the text, the
  // directory part would be `<out>/`, in no project, and the write would pass from a cwd in none and be charged to the
  // cwd's project from the other. An untracked folder of the same root stays allowed from a cwd in none, so the pin
  // cannot be met by refusing every dollar root.
  const out = outsideDir();
  try {
    const dollar = path.join(out, 'p$x');
    for (const d of ['.trackchanges', 'notes', 'docs']) fs.mkdirSync(path.join(dollar, d), { recursive: true });
    fs.writeFileSync(path.join(dollar, '.trackchanges', 'config.json'), JSON.stringify({ v: 2, tracked: ['notes/', 'docs/report.md'] }));
    fs.writeFileSync(path.join(dollar, 'docs', 'report.md'), 'tracked prose\n');
    const esc = (p) => p.replace(/\$/g, '\\$');
    const src = path.join(proj, 'base', 'report.md');
    const shapes = [
      `cp ${src} "${esc(dollar)}/notes/$N.md"`,
      `cp ${src} "${esc(dollar)}/notes/\${N}.md"`,
      `cp ${src} "${esc(dollar)}/notes/$(date +%s).md"`,
      `cp ${src} '${dollar}/notes/'$N.md`,
      `tee "${esc(dollar)}/notes/$N.md" < ${src}`,
      `echo x > "${esc(dollar)}/docs/$N.md"`,
    ];
    for (const [cwd, where] of [[out, 'from a cwd in no project'], [proj, 'from another project\'s cwd']]) {
      for (const cmd of shapes) {
        const reason = evaluate(payload(cmd, cwd));
        assert.ok(reason && NOT_LITERAL.test(reason) && reason.includes(`Track-changes is ON in ${dollar},`), `${where}, refused naming the dollar root: ${cmd}: ${reason}`);
        assert.ok(!reason.includes(proj), `${where}, not the cwd's project: ${cmd}`);
      }
    }
    // class F (round 4, 2026-09-19): a non-numeric expansion in an untracked subfolder of the tracked dollar root is
    // refused, since the value can climb via `../` into the tracked docs/report.md; the refusal names the dollar root
    const scratchN = evaluate(payload(`cp ${src} "${esc(dollar)}/scratch/$N.md"`, out));
    assert.ok(scratchN && NOT_LITERAL.test(scratchN) && scratchN.includes(`Track-changes is ON in ${dollar},`), `an untracked subfolder of the dollar root, from a cwd in none: refused under class F: ${scratchN}`);
    // the grammar: the dollar in the root's name is quoted text, the variable the first expansion
    const u = extractWriteTargets(`cp ${src} "${esc(dollar)}/notes/$N.md"`, out).unresolved[0];
    assert.equal(u.text, `${dollar}/notes/$N.md`);
    assert.equal(u.marks.indexOf('x'), u.text.lastIndexOf('$'), 'the first expansion mark sits at the variable, after the literal dollar in the root\'s name');
    assert.ok(u.text.indexOf('$') < u.marks.indexOf('x'), 'and the first dollar in the text is the literal one');
    const run = (command, cwd) => spawnSync(process.execPath, [HOOK], { input: payload(command, cwd), encoding: 'utf8', env: hookEnv({ ROMP_SID }) });
    assert.equal(run(shapes[0], out).status, 2);
    assert.equal(run(`cp ${src} "${esc(dollar)}/scratch/$N.md"`, out).status, 2, 'class F: refused as a process too');
  } finally { fs.rmSync(out, { recursive: true, force: true }); }
});

test('a leading $HOME or ${HOME} followed by a slash or the word end is the home directory, as ~/ is: expanded, and judged by the path it names', () => {
  // Review round 1 (2026-09-18): `~/.cache/x.log` was expanded and allowed while `"$HOME/.cache/x.log"` was
  // refused as not literal, though both come from the same os.homedir() read. Both quoted and unquoted
  // spellings, since the quoted one is read by a separate branch of the lexer and is the common case.
  const home = process.env.HOME;
  process.env.HOME = proj;
  try {
    for (const spelling of ['$HOME/docs/report.md', '"$HOME/docs/report.md"', '${HOME}/docs/report.md', '"${HOME}/docs/report.md"', "$HOME/'docs/report.md'"]) {
      assert.deepEqual(targets(`cp base/report.md ${spelling}`, '/'), [report], spelling);
      assert.match(evaluate(payload(`cp base/report.md ${spelling}`, '/')), /^Track-changes is ON for /, `refused with the file named: ${spelling}`);
    }
    assert.equal(evaluate(payload('cp base/report.md "$HOME/docs/other.md"', '/')), null, 'the untracked file passes');
    assert.deepEqual(targets('cp base/report.md "$HOME"', '/'), [path.join(proj, 'report.md')], 'the word end: the home directory itself, a destination folder');
    assert.deepEqual(targets('cp base/report.md $HOME', '/'), [path.join(proj, 'report.md')]);
    // the boundary: another variable, a suffix, a default, a variable after it, text before it, a quote after it
    const others = ['echo x > $HOMEDIR/x.log', 'echo x > "${HOME:-/tmp}/x.log"', 'echo x > "$HOME/$NAME.md"'];
    for (const cmd of others) assert.deepEqual(targets(cmd), [], `not read: ${cmd}`);
    assert.deepEqual(verdicts(others), allOf(others, REFUSED));
    // B2 (2026-09-19): a `$HOME` elsewhere in a word is read through the guard's home too (the home here is the project), so
    // these resolve to literal paths beside the project and pass; before B2 they were words the hook could not read
    assert.deepEqual(targets('echo x > "$HOME.bak/x.log"'), [`${proj}.bak/x.log`], 'a $HOME glued to text resolves');
    assert.deepEqual(targets('echo x > x$HOME/y'), [path.join(proj, `x${proj}`, 'y')]);
    assert.deepEqual(targets('echo x > $HOME"/x"'), [path.join(proj, 'x')]);
    for (const cmd of ['echo x > "$HOME.bak/x.log"', 'echo x > x$HOME/y', 'echo x > $HOME"/x"']) assert.equal(evaluate(payload(cmd)), null, `resolved to an untracked path: ${cmd}`);
  } finally { process.env.HOME = home; }
  // the refused write the round found: a log under the home, from a cwd inside the tracked project
  const out = outsideDir();
  process.env.HOME = out;
  try {
    assert.equal(evaluate(payload('echo x >> "$HOME/.cache/x.log"')), null);
    assert.equal(evaluate(payload('echo x >> ${HOME}/.cache/x.log')), null);
    assert.equal(evaluate(payload('echo x >> ~/.cache/x.log')), null, 'as the tilde spelling always was');
  } finally { process.env.HOME = home; fs.rmSync(out, { recursive: true, force: true }); }
});

test('TRACKCHANGES_ROOT stands in for the root search only for a directory under it, and its value never reaches the refusal', () => {
  // Review round 1 (2026-09-18): the override answered for every directory on the machine, so with the
  // variable set every non-literal write anywhere was refused, and the value was echoed in the refusal.
  // Outside the env root the marker search runs (a second tracked project is refused under its own name,
  // the chosen asymmetry with the literal rule, which sends every file to the env root); the message names
  // the variable, never its value.
  const plain = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'romp-bash-guard-plain-')));
  const second = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'romp-bash-guard-second-')));
  const saved = process.env.TRACKCHANGES_ROOT;
  try {
    fs.mkdirSync(path.join(plain, '.git'));
    fs.mkdirSync(path.join(second, '.trackchanges'));
    fs.writeFileSync(path.join(second, '.trackchanges', 'config.json'), JSON.stringify({ v: 2, tracked: ['a.md'] }));
    process.env.TRACKCHANGES_ROOT = proj;
    const inside = evaluate(payload('echo x >> "$LOG"'));
    assert.ok(inside && NOT_LITERAL.test(inside), 'under the env root: refused');
    assert.ok(!inside.includes(proj), `the value is not echoed: ${inside}`);
    assert.ok(inside.includes('Track-changes is ON in the project TRACKCHANGES_ROOT names'), 'the variable is named');
    assert.ok(evaluate(payload('echo x >> "$LOG"', path.join(proj, 'docs'))), 'a directory below the env root');
    assert.equal(evaluate(payload('echo x >> "$LOG"', plain)), null, 'outside the env root, with no tracking there: allowed');
    assert.equal(evaluate(payload('cp "$A" "$B"', plain)), null);
    assert.equal(evaluate(payload(`cp "$SRC" ${plain}/`, proj)), null, 'a copy landing outside the env root');
    const fallback = evaluate(payload('echo x >> "$LOG"', second));
    assert.ok(fallback && fallback.includes(second) && !fallback.includes(proj), 'outside the env root the marker search runs: the second project, under its own name');
    // as a process, with the variable set in its environment (the suite otherwise deletes it)
    const env = hookEnv({ ROMP_SID });
    env.TRACKCHANGES_ROOT = proj;
    const run = (command, cwd) => spawnSync(process.execPath, [HOOK], { input: payload(command, cwd), encoding: 'utf8', env });
    assert.equal(run('echo x >> "$LOG"', plain).status, 0, 'outside the env root: allowed');
    const refused = run('echo x >> "$LOG"', proj);
    assert.equal(refused.status, 2);
    assert.ok(!refused.stderr.includes(proj) && refused.stderr.includes('TRACKCHANGES_ROOT'), refused.stderr);
  } finally {
    if (saved === undefined) delete process.env.TRACKCHANGES_ROOT; else process.env.TRACKCHANGES_ROOT = saved;
    fs.rmSync(plain, { recursive: true, force: true });
    fs.rmSync(second, { recursive: true, force: true });
  }
});

test('with the command\'s variables set in the hook\'s environment the refusal still names the word, never a value, and refuses on the tracked project alone', () => {
  // Review round 1 (2026-09-18): the property that the hook resolves no word from its environment was pinned
  // by prose only; a mutant that read a variable when set shipped green. A key-shaped decoy sits in the same
  // environment (assembled here, so the repo's scanner reads no token in the source).
  const decoy = ['sk', 'ant', 'api03', 'x'.repeat(24)].join('-');
  const src = path.join(proj, 'base', 'report.md');
  const run = (command, extra) => spawnSync(process.execPath, [HOOK], { input: payload(command), encoding: 'utf8', env: hookEnv({ ROMP_SID, ...extra }) });
  const tracked = run('cp "$SRC" "$DST"', { SRC: src, DST: report, ROMP_PROBE_TOKEN: decoy });
  assert.equal(tracked.status, 2, tracked.stderr);
  assert.match(tracked.stderr, /names "\$DST"/, 'the word as written');
  for (const value of [report, src, decoy]) assert.ok(!tracked.stderr.includes(value), `no expanded value: ${value}`);
  const untracked = run('cp "$SRC" "$DST"', { SRC: src, DST: other, ROMP_PROBE_TOKEN: decoy });
  assert.equal(untracked.status, 2, 'an environment-resolving mutant would exit 0 here, since the value names an untracked file');
  assert.ok(untracked.stderr.length > 0 && !untracked.stderr.includes(other));
  // and in process
  const saved = process.env.DST;
  process.env.DST = report;
  try {
    const reason = evaluate(payload('cp base/report.md "$DST"'));
    assert.ok(reason && NOT_LITERAL.test(reason) && !reason.includes(report));
  } finally { if (saved === undefined) delete process.env.DST; else process.env.DST = saved; }
});

test('a copy whose landing name the hook cannot read is refused only where a tracked file could land: nothing tracked under the folder allows, an entry there that links to a tracked file refuses', () => {
  // Review round 1 (2026-09-18): the branch refused every such copy into any folder of a project that tracks
  // anything, from every cwd on the machine. The refuters' narrowing by tracked entries alone reopened a
  // symlink overwrite the literal rule refuses, so the folder's existing entries are asked too.
  fs.mkdirSync(path.join(proj, 'scratch'));
  fs.writeFileSync(path.join(proj, 'scratch', 'plain.md'), 'untracked\n');
  const out = outsideDir();
  try {
    for (const cwd of [proj, out]) {
      assert.equal(evaluate(payload(`cp "$SRC" ${proj}/scratch/`, cwd)), null, `nothing tracked under scratch/, from ${cwd === proj ? 'inside' : 'outside'}`);
      assert.equal(evaluate(payload(`cp -t ${proj}/scratch "$SRC"`, cwd)), null);
      assert.equal(evaluate(payload(`install -m 644 "$SRC" ${proj}/scratch/`, cwd)), null);
      assert.equal(evaluate(payload(`mv "$SRC" ${proj}/base/`, cwd)), null, 'base/ holds an untracked file only');
    }
    assert.equal(evaluate(payload('cp "$SRC" scratch/')), null, 'relative to the project');
    // where a tracked file could land, from any cwd: a tracked entry in or below the folder, the folder inside a
    // tracked folder, the root above every entry
    const inPlay = [`cp "$SRC" ${proj}/docs/`, `cp -t ${proj}/notes "$SRC"`, `cp "$SRC" ${proj}/notes/sub/`, `cp "$SRC" ${proj}/`, `cp -r "$SRC" ${proj}/`];
    assert.deepEqual(verdicts(inPlay, out), allOf(inPlay, REFUSED));
    // a note under the folder reached through a link from the tracked file, nested where a readdir does not see it
    fs.mkdirSync(path.join(proj, 'scratch', 'deep'));
    fs.writeFileSync(path.join(proj, 'scratch', 'deep', 'linked.md'), 'reached\n');
    fs.writeFileSync(report, 'The api session cut tail latency by 40%.\n\n[[linked]]\n');
    assert.ok(evaluate(payload(`cp "$SRC" ${proj}/scratch/`, out)), 'a closure note below the folder: a directory copy could land on it');
    fs.rmSync(path.join(proj, 'scratch', 'deep'), { recursive: true });
    assert.equal(evaluate(payload(`cp "$SRC" ${proj}/scratch/`, out)), null, 'gone again');
    // an existing entry of the folder that links to the tracked file: the copy could take its name
    fs.symlinkSync(report, path.join(proj, 'scratch', 'report.md'));
    assert.ok(evaluate(payload(`cp "$SRC" ${proj}/scratch/`, out)), 'a link onto the tracked file sits in the folder');
    assert.ok(evaluate(payload('cp -t scratch "$SRC"')));
    assert.ok(evaluate(payload('cp base/report.md scratch/report.md')), 'as the literal name is refused');
  } finally { fs.rmSync(out, { recursive: true, force: true }); }
});

test('a project is in play only when its list holds an entry the literal rule could refuse: figures only or every entry vetoed track nothing refusable; a figure whose whole-line link reaches a note does', () => {
  // Review round 1 (2026-09-18): the raw length of the tracked list decided, so a project of tracked figures
  // refused every non-literal write with a message no literal write there could meet.
  const config = (obj) => fs.writeFileSync(path.join(proj, '.trackchanges', 'config.json'), JSON.stringify(obj));
  const shapes = ['cp "$SRC" "$DST"', 'echo x > "$OUT"', 'cp "$SRC" figs/', "sed -i 's/a/b/' \"$F\""];
  config({ v: 2, tracked: ['figs/plot.png'] });
  assert.deepEqual(verdicts(shapes), allOf(shapes, 'allowed'), 'figures only');
  assert.equal(evaluate(payload('cp new.png figs/plot.png')), null, 'the literal write to the figure passes, as before');
  config({ v: 2, tracked: ['docs/'], untracked: ['docs/'] });
  assert.deepEqual(verdicts(shapes), allOf(shapes, 'allowed'), 'every entry vetoed');
  assert.equal(evaluate(payload('cp base/report.md docs/report.md')), null, 'no literal write is refused there either');
  config({ v: 2, tracked: ['docs/report.md', 'figs/plot.png'], untracked: ['docs/report.md'] });
  assert.deepEqual(verdicts(shapes), allOf(shapes, 'allowed'), 'a vetoed file and a figure');
  // a tracked figure whose bytes carry a whole-line link to a note: the closure reaches the note, the literal rule
  // refuses it, so the project is in play
  fs.writeFileSync(path.join(proj, 'figs', 'plot.png'), '[[docs/report]]\n');
  config({ v: 2, tracked: ['figs/plot.png'] });
  assert.ok(evaluate(payload('cp base/report.md docs/report.md')), 'the literal rule refuses the linked note');
  const anywhere = shapes.filter((c) => c !== 'cp "$SRC" figs/');
  assert.deepEqual(verdicts(anywhere), allOf(anywhere, REFUSED), 'a target that could land anywhere');
  assert.equal(evaluate(payload('cp "$SRC" figs/')), null, 'but the figure folder holds nothing the linked note could be reached under: a copy there is allowed');
  assert.ok(evaluate(payload('cp "$SRC" docs/')), 'and the note\'s folder refuses it');
  // an entry naming a file that does not exist yet keeps the literal rule live, so it counts
  config({ v: 2, tracked: ['docs/absent.md'] });
  assert.ok(evaluate(payload('cp base/report.md docs/absent.md')));
  assert.ok(evaluate(payload('cp "$SRC" "$DST"')));
});

test('install -d makes directories and writes no file: -d, --directory and a d inside an option cluster; -D copies, and cp -d or ln -d mean something else', () => {
  // Review round 1 (2026-09-18): `install -d "$A" "$B"` was refused as a copy whose destination the hook could
  // not read, and the literal `install -d docs/new notes/new2` as a write under the tracked folder.
  const dirOnly = ['install -d "$A" "$B"', 'install --directory "$A" "$B"', 'install -dm755 "$A" "$B"', 'install -pd "$A" "$B"', 'install -d -m 755 "$A" "$B"', 'install -d -- "$A" "$B"', 'install -d "$DESTDIR/usr/bin" "$DESTDIR/usr/lib"'];
  assert.deepEqual(verdicts(dirOnly), allOf(dirOnly, 'allowed'));
  for (const cmd of dirOnly) assert.deepEqual(extractWriteTargets(cmd, proj).unresolved, [], cmd);
  assert.deepEqual(targets('install -d docs/new notes/new2'), [], 'the literal spelling names no file either');
  assert.equal(evaluate(payload('install -d docs/new notes/new2')), null);
  assert.ok(evaluate(payload('install -D base/report.md "$B"')), '-D copies a file: refused as not literal');
  assert.deepEqual(targets('install -D base/report.md notes/new/report.md'), [path.join(proj, 'notes', 'new', 'report.md')]);
  assert.deepEqual(targets('install -m755d base/report.md docs/report.md'), [report], 'after m the rest of the word is the mode, not a d');
  assert.deepEqual(targets('cp -d base/report.md docs/report.md'), [report], 'cp -d is --no-dereference');
  assert.deepEqual(targets('ln -d base docs/link'), [path.join(proj, 'docs', 'link')], 'ln -d still makes a link');
});

test('an interpreter one-liner whose write path is computed is allowed by design: the scan reads a literal path only', () => {
  // Review round 1 (2026-09-18) named this residual and rejected closing it here: the regex that would catch a
  // computed open() path cannot see os.path.join or an f-string and also matches reads, so it would refuse
  // ordinary scripting and still miss the common forms. The vendored skill tells the session not to write a
  // tracked file this way; the hook does not pretend to see it.
  const computed = [
    `python3 -c "import os; open(os.environ['OUT'], 'w').write('x')"`,
    `python3 -c "import sys; open(sys.argv[1], 'w').write('x')" docs/report.md`,
    `python3 -c "p = 'docs/report.md'; open(p, 'w')"`,
    `node -e "require('fs').writeFileSync(process.env.OUT, 'x')"`,
    `node -e "require('fs').writeFileSync(process.argv[1], 'x')" docs/report.md`,
  ];
  assert.deepEqual(verdicts(computed), allOf(computed, 'allowed'));
  for (const cmd of computed) assert.deepEqual(extractWriteTargets(cmd, proj).unresolved, [], `no unresolved target either: ${cmd}`);
  assert.deepEqual(scriptWriteTargets('python', "open(os.environ['OUT'], 'w')"), []);
  assert.deepEqual(scriptWriteTargets('node', "fs.writeFileSync(process.env.OUT, 'x')"), []);
  assert.ok(evaluate(payload(`python3 -c "open('docs/report.md', 'w')"`)), 'the literal spelling is refused');
});

test('the caps decide which mechanism refuses, and each boundary is pinned by execution: BRACE_CAP, GLOB_MATCH_CAP, GLOB_READ_CAP, LANDING_SCAN_CAP, RECURSION_CAP, BRACE_DEPTH_CAP', () => {
  // Review round 1 (2026-09-18): the three caps could be retuned widely with the suite green. At the cap a
  // brace list or a glob names each file and the verdict is theirs; past it the word is one the hook cannot
  // read and the verdict is the tracked project's.
  const out = outsideDir();
  try {
    const at = extractWriteTargets(`tee ${out}/n{1..512}.md`, proj);
    assert.equal(at.targets.length, 512, 'at BRACE_CAP: every alternative');
    assert.deepEqual(at.unresolved, []);
    assert.equal(evaluate(payload(`tee ${out}/n{1..512}.md`)), null, 'each names an untracked file outside the project');
    const past = extractWriteTargets(`tee ${out}/n{1..513}.md`, proj);
    assert.deepEqual(past.targets, []);
    assert.deepEqual(past.unresolved.map((u) => u.raw), [`${out}/n{1..513}.md`], 'past it: one word the hook cannot read');
    assert.ok(evaluate(payload(`tee ${out}/n{1..513}.md`)), 'refused in the tracked project, though every alternative would land outside');
    // a glob whose matches are all untracked: at the match cap each landing name is judged and allowed; past it the
    // source is a word the hook cannot read, the landing name with it, and docs/ could hold a tracked file
    const big = path.join(proj, 'big');
    fs.mkdirSync(big);
    for (let k = 0; k < 2001; k++) fs.writeFileSync(path.join(big, `m${k}.md`), 'x');
    const some = extractWriteTargets('cp big/m1*.md docs/', proj);   // m1, m10-m19, m100-m199, m1000-m1999
    assert.equal(some.targets.length, 1111);
    assert.deepEqual(some.unresolved, []);
    assert.equal(evaluate(payload('cp big/m1*.md docs/')), null, 'every landing name untracked');
    const all = extractWriteTargets('cp big/*.md docs/', proj);
    assert.deepEqual(all.targets, []);
    assert.deepEqual(all.unresolved.map((u) => [u.raw, u.at]), [['big/*.md', path.join(proj, 'docs')]], 'past GLOB_MATCH_CAP: the landing name cannot be read');
    assert.ok(evaluate(payload('cp big/*.md docs/')), 'and docs/ holds a tracked file');
    // LANDING_SCAN_CAP, both sides (review round 2, 2026-09-18: the cap was a verdict-changing branch with no
    // test, so it could be set to 1 or dropped with the suite green). Nothing tracked can land in big/, so at
    // the cap the folder is scanned and the copy is allowed; one entry past it the folder is taken as in play
    // unscanned and the copy is refused, a deliberate false refusal stated in decision 47 and escalated with
    // the PR. A one-sided assertion would not hold the number: the allow side is what a cap of 1 breaks.
    const bigCopies = ['cp "$SRC" big/', 'cp -t big "$SRC"', 'install -m 644 "$SRC" big/', `cp "$SRC" ${big}/`];
    for (const cmd of bigCopies) assert.ok(evaluate(payload(cmd)), `past LANDING_SCAN_CAP (2001 entries) the folder counts unscanned: ${cmd}`);
    assert.ok(evaluate(payload(`cp "$SRC" ${big}/`, out)), 'from a cwd outside the project too: the landing folder decides');
    // review round 3 (2026-09-19): the same gate holds the own-project step, so a numeric NAME in the folder is under
    // the cap too, from any cwd, with the generic text (the file's name holds the expansion, not a folder's); the
    // literal spelling passes on both sides, so the refusal past the cap is the deliberate false refusal decision 47
    // states for a numeric name as well as a copy
    const numericInBig = evaluate(payload(`echo x > ${big}/tmp-$$.log`, out));
    assert.ok(numericInBig && NOT_LITERAL.test(numericInBig) && !/cannot tell which folder/.test(numericInBig), `past the cap a numeric name in the folder is refused unscanned: ${numericInBig}`);
    assert.equal(evaluate(payload(`echo x > ${big}/tmp-4242.log`, out)), null, 'while its literal spelling passes');
    fs.rmSync(path.join(big, 'm2000.md'));
    assert.equal(fs.readdirSync(big).length, 2000, 'exactly at the cap');
    for (const cmd of bigCopies) assert.equal(evaluate(payload(cmd)), null, `at LANDING_SCAN_CAP (2000 entries) the folder is scanned and nothing tracked could land there: ${cmd}`);
    assert.equal(evaluate(payload(`cp "$SRC" ${big}/`, out)), null);
    assert.equal(evaluate(payload(`echo x > ${big}/tmp-$$.log`, out)), null, 'at the cap the numeric name is scanned for and passes');
    fs.symlinkSync(report, path.join(big, 'm2000.md'));
    assert.ok(evaluate(payload('cp "$SRC" big/')), 'past the cap again, and a scan would have found the link onto the tracked file anyway');
    fs.rmSync(path.join(big, 'm1999.md'));
    assert.ok(evaluate(payload('cp "$SRC" big/')), 'at the cap the scan finds the link onto the tracked file: refused for the right reason');
    fs.rmSync(path.join(big, 'm2000.md'));
    fs.writeFileSync(path.join(big, 'm1999.md'), 'x');
    // the read cap: a directory of exactly GLOB_READ_CAP entries is read, one more is not
    const huge = path.join(out, 'huge');
    fs.mkdirSync(huge);
    for (let k = 0; k < 50000; k++) fs.writeFileSync(path.join(huge, `e${k}`), '');
    const read = extractWriteTargets(`cp ${huge}/e4999? docs/`, proj);
    assert.equal(read.targets.length, 10, 'at GLOB_READ_CAP the listing is read: e49990 to e49999');
    assert.equal(evaluate(payload(`cp ${huge}/e4999? docs/`)), null);
    fs.writeFileSync(path.join(huge, 'e50000'), '');
    const unread = extractWriteTargets(`cp ${huge}/e4999? docs/`, proj);
    assert.deepEqual(unread.targets, []);
    assert.equal(unread.unresolved.length, 1, 'past it the glob is a word the hook cannot read');
    assert.ok(evaluate(payload(`cp ${huge}/e4999? docs/`)));
    // RECURSION_CAP and BRACE_DEPTH_CAP (review round 3, 2026-09-19): a command nested about 1100 `$(` deep overflowed
    // the stack inside the extractor when the hook ran as a process, evaluate's catch read the throw as allow, and the
    // literal cp onto the tracked file before the nesting ran (reproduced in real zsh and dash); a comma brace list
    // nested thousands deep threw the same way. Past the cap the inner command is opaque and the literal targets read
    // before it are judged; at the cap the nesting is read. The generated command keeps kilobytes of `$(` out of this file.
    const nest = (n, inner) => 'cp base/report.md docs/report.md; echo ' + '$('.repeat(n) + inner + ')'.repeat(n);
    assert.ok(!extractWriteTargets(nest(64, 'true'), proj).opaque, 'RECURSION_CAP nested substitutions are read through');
    assert.equal(extractWriteTargets(nest(64, 'cp base/report.md docs/other.md'), proj).targets.length, 2, 'a write at the bottom of them is read');
    assert.ok(extractWriteTargets(nest(65, 'true'), proj).opaque, 'one deeper, the innermost command is opaque');
    for (const n of [65, 1100, 2000]) {
      assert.deepEqual(targets(nest(n, 'true')), [report], `the literal target before the nesting is read at depth ${n}`);
      assert.match(evaluate(payload(nest(n, 'true'))), /^Track-changes is ON for /, `and refused at depth ${n}`);
    }
    assert.equal(evaluate(payload(nest(2000, 'true').replace('docs/report.md', 'docs/other.md'))), null, 'an untracked target before the nesting passes');
    const asProcess = spawnSync(process.execPath, [HOOK], { input: payload(nest(2000, 'true')), encoding: 'utf8', env: hookEnv({ ROMP_SID }) });
    assert.equal(asProcess.status, 2, `as a process, at the depth that failed open: ${asProcess.stderr}`);
    const braces = (n) => 'echo x > docs/report.md; echo ' + 'a{b,'.repeat(n) + 'c' + '}'.repeat(n);
    assert.doesNotThrow(() => extractWriteTargets(braces(6000), proj), 'a brace list nested past BRACE_DEPTH_CAP does not throw');
    assert.match(evaluate(payload(braces(6000))), /^Track-changes is ON for /, 'and the literal target before it is judged');
    assert.equal(extractWriteTargets('echo ' + 'a{b,'.repeat(65) + 'c' + '}'.repeat(65), proj).targets.length, 0);
  } finally { fs.rmSync(out, { recursive: true, force: true }); }
});

test('the same commands pass with no tracked project in play: no .trackchanges/config.json, an empty tracked list, a copy into a folder outside the project', () => {
  const plain = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'romp-bash-guard-plain-')));
  try {
    fs.mkdirSync(path.join(plain, '.git'));   // a repository root, as findVaultRoot reads one, with no tracking
    fs.mkdirSync(path.join(plain, 'docs'));
    fs.mkdirSync(path.join(plain, 'base'));
    fs.writeFileSync(path.join(plain, 'base', 'report.md'), 'x\n');
    const shapes = ['cp "$SRC" "$DST"', 'cp base/report.md "$DST"', 'echo x > "$OUT"', 'cp base/report.md docs/new*.md', "sed -i 's/a/b/' \"$F\"", 'cp "$SRC" docs/', 'tee docs/n{1..1000}.md'];
    for (const cmd of shapes) assert.equal(evaluate(payload(cmd, plain)), null, `allowed with no tracking: ${cmd}`);
    // a project whose tracked list is empty tracks nothing
    fs.mkdirSync(path.join(plain, '.trackchanges'));
    fs.writeFileSync(path.join(plain, '.trackchanges', 'config.json'), JSON.stringify({ v: 2, tracked: [] }));
    for (const cmd of shapes) assert.equal(evaluate(payload(cmd, plain)), null, `allowed with an empty list: ${cmd}`);
    // from the tracked project, a copy into a folder outside it lands nothing tracked: that folder decides, not the cwd
    assert.equal(evaluate(payload(`cp "$SRC" ${plain}/docs/`)), null);
    assert.equal(evaluate(payload(`cp -t ${plain}/docs "$SRC"`)), null);
    assert.equal(evaluate(payload(`cd ${plain} && cp "$SRC" docs/`)), null, 'after a cd out of the project too: the folder the copy lands in decides');
    assert.ok(evaluate(payload(`cd ${plain} && cp a "$DST"`)), 'but a target that could land anywhere is judged by the payload cwd as well as the directory the cd reached');
    assert.ok(evaluate(payload(`cd ${plain} && echo x > "$OUT"`)));
    // a literal target keeps its verdict beside the rule
    assert.equal(evaluate(payload('cp base/report.md docs/other.md')), null, 'a literal untracked target passes');
    assert.match(evaluate(payload('cp base/report.md docs/report.md')), /^Track-changes is ON for /, 'a literal tracked target is refused with the file named');
  } finally { fs.rmSync(plain, { recursive: true, force: true }); }
});

test('beside a non-literal target a literal tracked one is named first, and the refusal for the non-literal one speaks as the person and says how to proceed', () => {
  const both = evaluate(payload('cp base/report.md docs/report.md; cp a "$B"'));
  assert.ok(both.includes(report) && !NOT_LITERAL.test(both), 'the tracked file is the more useful answer');
  const reason = evaluate(payload('cp "$SRC" "$DST"'));
  const prose = reason.split('\n')[0].split(proj).join('<project>');
  assert.ok(!ROMP_NOUNS.test(prose), `no romp noun in: ${prose}`);
  assert.ok(!/\u2014/.test(reason), 'no em dash');
  assert.match(prose, /^Track-changes is ON in /);
  assert.ok(prose.includes('Spell the path out'), 'how to proceed: the literal path');
  assert.ok(prose.includes('outside that project'), 'or a path outside the project');
  assert.ok(prose.includes('for me to accept or reject'), 'the person\'s voice');
  assert.match(reason, /node ~\/\.claude\/hooks\/track-edit\.mjs --file/, 'the remedy for a tracked file');
});

test('a glob is expanded as the shell expands it: a glob source into the tracked folder is refused, and a glob that names no write passes', () => {
  // the review's second round: a landing word took the source's literal flag, so `cp base/*.md notes/` named
  // nothing and each file landed raw under the tracked folder while `cp base/report.md notes/` was refused
  assert.deepEqual(targets('cp base/*.md notes/'), [path.join(proj, 'notes', 'report.md')]);
  assert.ok(evaluate(payload('cp base/*.md notes/')), 'each match lands raw under the tracked folder');
  assert.ok(evaluate(payload('mv base/* notes')));
  assert.ok(evaluate(payload('cp -t notes base/*.md')));
  assert.deepEqual(targets("sed -i 's/a/b/' docs/*.md"), [other, report].sort(), 'every file the glob names');
  assert.deepEqual(targets('cp base/report.md docs/rep*.md'), [report], 'one match for the destination: that file');
  assert.deepEqual(targets('cp base/report.md docs/*.md'), [], 'two matches for the destination: cp stops with "target is not a directory" and writes nothing');
  assert.equal(evaluate(payload('cp base/report.md docs/*.md')), null);
  assert.deepEqual(targets('cp base/report.md docs/other.md docs/report.md'), [], 'the same without a glob: three operands and no directory');
  assert.deepEqual(targets('cp base/*.rst notes/'), [], 'no match: nothing the shell writes as the session meant');
  assert.equal(evaluate(payload('cp base/*.rst notes/')), null);
});

test('a shell -c with a literal script, a command substitution and a loop body are read through', () => {
  assert.deepEqual(targets('bash -c \'cp base/report.md docs/report.md\''), [report]);
  assert.deepEqual(targets('echo "$(cp base/report.md docs/report.md)"'), [report]);
  assert.deepEqual(targets('for f in a b; do cp "$f" docs/report.md; done'), [report]);
  assert.deepEqual(targets('if true; then echo x > docs/report.md; fi'), [report]);
  assert.deepEqual(targets('sudo cp base/report.md docs/report.md'), [report]);
  assert.deepEqual(targets('FOO=1 env BAR=2 cp base/report.md docs/report.md'), [report]);
  assert.deepEqual(targets('nice -n 19 tee docs/report.md'), [report]);
});

test('the lexer: quotes, escapes, comments and line continuations', () => {
  const { segments } = lex('cp "a b" \'c d\' e\\ f # a comment\ncat x');
  assert.equal(segments.length, 2);
  assert.deepEqual(segments[0].words.map((w) => w.text), ['cp', 'a b', 'c d', 'e f']);
  assert.deepEqual(segments[1].words.map((w) => w.text), ['cat', 'x']);
  assert.deepEqual(targets('cp base/report.md \\\n  docs/report.md'), [report], 'a continued line is one command');
  assert.deepEqual(targets('cp base/report.md "docs/report.md"'), [report]);
  assert.deepEqual(targets("cp base/report.md 'docs/report.md'"), [report]);
});

// ── what the guard lets through on purpose ─────────────────────────

test('a tracked file that is not text (an image) passes by name, as with the vendored guard; a new file under a tracked folder is refused', () => {
  assert.equal(evaluate(payload('cp new.png figs/plot.png')), null, 'a tracked image is regenerated, not edited');
  assert.equal(evaluate(payload('cp x figs/other.PNG')), null);
  assert.ok(evaluate(payload('cp base/report.md notes/new.md')), 'a folder tracked before its files exist covers a new file');
  assert.ok(evaluate(payload('echo x > notes/new.md')));
});

test('a payload that is not a Bash call, not JSON, or has no command is allowed', () => {
  assert.equal(evaluate(payload('cp base/report.md docs/report.md', proj, 'Write')), null);
  assert.equal(evaluate('not json'), null);
  assert.equal(evaluate(JSON.stringify({ tool_name: 'Bash', tool_input: {}, cwd: proj })), null);
  assert.equal(evaluate(JSON.stringify({ tool_name: 'Bash', tool_input: { command: 42 }, cwd: proj })), null);
});

test('with no cwd in the payload the process cwd is used', () => {
  const here = process.cwd();
  process.chdir(proj);
  try { assert.ok(evaluate(JSON.stringify({ tool_name: 'Bash', tool_input: { command: 'cp base/report.md docs/report.md' } }))); }
  finally { process.chdir(here); }
});

test('a directory copied into a tracked folder lands its files there: the first tracked one is named; into an untracked folder it passes', () => {
  const reason = evaluate(payload('cp -r base notes/'));
  assert.ok(reason, 'base/report.md would land raw at notes/base/report.md, under the tracked folder');
  assert.ok(reason.includes(path.join(proj, 'notes', 'base', 'report.md')), reason);
  assert.deepEqual(targets('cp -r base docs/new'), [path.join(proj, 'docs', 'new', 'report.md')],
    'a new destination: each file under it, never the directory itself');
  assert.equal(evaluate(payload('cp -r base docs/')), null, 'docs/base/report.md is not tracked');
  assert.equal(evaluate(payload('mv base figs/')), null);
});

test('the refusal speaks as the person and names no machinery', () => {
  const reason = evaluate(payload('cp base/report.md docs/report.md'));
  assert.ok(reason);
  const prose = reason.split('\n')[0].split(report).join('<file>');   // the scratch path is the machine's, not the prose
  assert.ok(!ROMP_NOUNS.test(prose), `no romp noun in: ${prose}`);
  assert.ok(!/\u2014/.test(reason), 'no em dash');
  assert.match(prose, /^Track-changes is ON for /);
  assert.ok(prose.includes('for me to accept or reject'), 'the person\'s voice: their accept or reject');
});

// ── the hook as a process ──────────────────────────────────────────

function hookEnv(extra) {
  const env = { ...process.env, ...extra };
  delete env.TRACKCHANGES_ROOT;
  if (!('ROMP_SID' in extra)) delete env.ROMP_SID;   // the suite may itself run inside a romp session
  return env;
}

test('the hook process exits 0 at once without ROMP_SID, with stdin still open', async () => {
  const child = spawn(process.execPath, [HOOK], { env: hookEnv({}), stdio: ['pipe', 'pipe', 'pipe'] });
  const code = await new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      child.kill('SIGKILL');
      reject(new Error('the hook did not exit within 2 s without ROMP_SID'));
    }, 2000);
    child.on('error', reject);
    child.on('exit', (c) => { clearTimeout(timer); resolve(c); });
  });
  child.stdin.destroy();
  assert.equal(code, 0);
});

test('the hook process with ROMP_SID denies a cp onto a tracked file with exit 2 and the reason on stderr, and passes a read', () => {
  const run = (command) => spawnSync(process.execPath, [HOOK], {
    input: payload(command), encoding: 'utf8', env: hookEnv({ ROMP_SID }),
  });
  const denied = run('cp base/report.md docs/report.md');
  assert.equal(denied.status, 2, denied.stderr);
  assert.ok(denied.stderr.includes(report));
  assert.match(denied.stderr, /track-edit/);
  assert.equal(denied.stdout, '');
  const allowed = run('cat docs/report.md');
  assert.equal(allowed.status, 0, allowed.stderr);
  assert.equal(allowed.stderr, '');
  assert.equal(run('cp base/report.md docs/other.md').status, 0);
  const notLiteral = run('cp "$SRC" "$DST"');
  assert.equal(notLiteral.status, 2, 'a target the hook cannot read, in a tracked project');
  assert.match(notLiteral.stderr, /is not a literal path/);
});

test('the hook run through its installed symlink, as the registered command runs it, still recognises itself and rules the same way', () => {
  // install.sh links ~/.claude/hooks/romp-track-bash-guard.mjs at the file in hooks/ and registers that tilde path as
  // the command, so in production a shell execs the LINK through the shebang: process.argv[1] is the link and
  // import.meta.url the real file, and the entry guard matches them only through realpathSync. Spawned by its real
  // path alone (the tests above), the suite would stay green with that call gone while the installed hook, which
  // exits 0 with no output whenever it does not recognise itself, let every Bash write to a tracked file through.
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-bash-guard-home-'));
  try {
    const hooksDir = path.join(home, '.claude', 'hooks');
    fs.mkdirSync(hooksDir, { recursive: true });
    const link = path.join(hooksDir, 'romp-track-bash-guard.mjs');
    fs.symlinkSync(HOOK, link);
    // HOME is the scratch home so ~ expands to the link's directory; PATH leads with this node so `#!/usr/bin/env node` runs it.
    const env = (extra) => ({ ...hookEnv(extra), HOME: home, PATH: [path.dirname(process.execPath), process.env.PATH || ''].join(path.delimiter) });
    const viaShell = (command, extra) => spawnSync('/bin/sh', ['-c', '~/.claude/hooks/romp-track-bash-guard.mjs'], {
      input: payload(command), encoding: 'utf8', env: env(extra),
    });
    const viaNode = (command) => spawnSync(process.execPath, [link], { input: payload(command), encoding: 'utf8', env: env({ ROMP_SID }) });

    const denied = viaShell('cp base/report.md docs/report.md', { ROMP_SID });
    assert.equal(denied.status, 2, `the registered command, exec'd through the link: ${denied.stderr || denied.error}`);
    assert.ok(denied.stderr.includes(report), denied.stderr);
    assert.match(denied.stderr, /track-edit/);
    assert.equal(denied.stdout, '');
    const allowed = viaShell('cat docs/report.md', { ROMP_SID });
    assert.equal(allowed.status, 0, allowed.stderr);
    assert.equal(allowed.stderr, '');

    const deniedByNode = viaNode('cp base/report.md docs/report.md');
    assert.equal(deniedByNode.status, 2, `node <link>: ${deniedByNode.stderr}`);
    assert.ok(deniedByNode.stderr.includes(report), deniedByNode.stderr);
    assert.equal(viaNode('cp base/report.md docs/other.md').status, 0);

    const noSid = viaShell('cp base/report.md docs/report.md', {});
    assert.equal(noSid.status, 0, 'through the link too, no ROMP_SID means not a romp session');
    assert.equal(noSid.stderr, '');
  } finally { fs.rmSync(home, { recursive: true, force: true }); }
});

test('the hook is executable with a node shebang, as the settings.json command runs it', () => {
  assert.ok(fs.statSync(HOOK).mode & 0o111, 'executable bit');
  assert.ok(fs.readFileSync(HOOK, 'utf8').startsWith('#!/usr/bin/env node\n'));
});

// ── review round 3 addendum: the walk-around lens's in-model overwrites are closed (2026-09-19) ──
//
// A walk-around lens ran ahead of round 4 and found eight classes of in-model command that the hook read but let
// through: an option table that guessed cp/mv's -Z; env -C / sudo -D dropped; command wrappers not peeled; a
// same-command HOME reassignment; an expansion whose literal head parents or sits under a tracked root; an
// unsearchable directory before a `..`; and a symlink the same command makes. Each is pinned here in both
// directions (a refused case and its allowed literal or numeric twin) with a real bash run of at least one case,
// which overwrites the tracked file when run (the pre-fix hook allowed it) and which the hook now refuses.

// A tracked file's sha before and after running a command in a real shell, restored after: proves the command the
// hook refuses is a live overwrite (the pre-fix hook allowed it), the shape the existing round tests use.
const shaOf = (p) => crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const overwrites = (cmd, file, cwd = proj, shell) => {   // `shell` comes from shellsFor at every call (round 5: no default, so no leg runs a shell the probe did not pass)
  const before = fs.readFileSync(file);
  const r = spawnSync(shell, ['-c', cmd], { cwd, encoding: 'utf8', env: { PATH: process.env.PATH } });
  const changed = shaOf(file) !== crypto.createHash('sha256').update(before).digest('hex');
  fs.writeFileSync(file, before);
  return { changed, status: r.status };
};
const runHook = (command, cwd = proj) => spawnSync(process.execPath, [HOOK], { input: payload(command, cwd), encoding: 'utf8', env: hookEnv({ ROMP_SID }) });

test('walk-around A: cp/mv/install/ln read a per-writer option table; a flag that takes no argument (-Z, --context) no longer eats an operand, and an unknown option refuses', () => {
  // coreutils' -Z and a bare --context take no argument; the guessed table read them as consuming the source, so the
  // destination was misread and the copy onto the tracked file passed. Pinned both ways: the flag onto a tracked file
  // is refused and onto an untracked one allowed; an option the table does not know refuses naming it, its literal twin
  // (the command without the option) allowed.
  for (const cmd of ['cp -Z base/report.md docs/report.md', 'cp --context base/report.md docs/report.md', 'mv -Z base/report.md docs/report.md', 'cp -fZ base/report.md docs/report.md', 'install -Z base/report.md docs/report.md']) {
    const reason = evaluate(payload(cmd));
    assert.ok(reason && reason.includes(report), `refused onto the tracked file: ${cmd}: ${reason}`);
  }
  for (const cmd of ['cp -Z base/report.md docs/other.md', 'cp --context base/report.md docs/other.md', 'mv -Z base/report.md docs/other.md']) {
    assert.equal(evaluate(payload(cmd)), null, `allowed onto the untracked twin: ${cmd}`);
  }
  assert.deepEqual(targets('cp --context=unconfined_u base/report.md docs/report.md'), [report], '--context=CTX is glued, no operand eaten');
  // an unknown option: the command is unreadable, refused naming the option while the project is in play; the literal
  // twin (without it) is judged as ever
  const unknown = evaluate(payload('cp --frobnicate base/report.md docs/report.md'));
  assert.ok(unknown && unknown.includes('--frobnicate') && unknown.includes('do not recognise') && unknown.includes(proj), `unknown option refused naming it: ${unknown}`);
  assert.ok(!/\u2014/.test(unknown) && !ROMP_NOUNS.test(unknown.split(proj).join('<p>')), 'no em dash, no romp noun');
  assert.equal(evaluate(payload('cp --frobnicate base/report.md docs/report.md', outsideDir())), null, 'an unknown option from a cwd in no project passes');
  assert.equal(evaluate(payload('cp base/report.md docs/other.md')), null, 'and the same copy without the option, onto an untracked file, is allowed');
  // real bash: cp -Z onto the tracked file overwrites it, the pre-fix hook allowed it
  for (const sh of shellsFor(['bash'], 'cp -Z in real bash')) assert.equal(overwrites('cp -Z base/report.md docs/report.md', report, proj, sh).changed, true, 'cp -Z overwrites the tracked file in real bash');
  assert.equal(runHook('cp -Z base/report.md docs/report.md').status, 2, 'and the hook refuses it');
  assert.equal(fs.readFileSync(report, 'utf8'), 'The api session cut tail latency by 40%.\n', 'the tracked file is intact after the hook run');
});

test('walk-around B: env -C DIR, env --chdir=DIR and sudo -D DIR run the inner command in DIR; its relative operands resolve there, and a non-literal DIR refuses', () => {
  // commandOf returned null for these, so evaluate dropped the whole segment and the copy landed on the tracked file.
  // Now the inner command's operands resolve against DIR (a cd for that command only); a non-literal DIR leaves the
  // directory unknown, so a relative inner target is refused with the reason. Pinned from three cwds.
  const out = outsideDir();
  const web = path.join(out, 'web');
  for (const d of ['.trackchanges', 'docs', 'base']) fs.mkdirSync(path.join(web, d), { recursive: true });
  fs.writeFileSync(path.join(web, '.trackchanges', 'config.json'), JSON.stringify({ v: 2, tracked: ['docs/report.md'] }));
  fs.writeFileSync(path.join(web, 'docs', 'report.md'), 'tracked prose\n');
  fs.writeFileSync(path.join(web, 'base', 'report.md'), 'src\n');
  try {
    for (const cwd of [proj, web, out]) {
      for (const cmd of [`env -C ${proj} cp base/report.md docs/report.md`, `env --chdir=${proj} cp base/report.md docs/report.md`, `sudo -D ${proj} cp base/report.md docs/report.md`, `env -C ${proj} cp -t docs base/report.md`, `env -C ${proj} sed -i s/api/API/ docs/report.md`]) {
        const reason = evaluate(payload(cmd, cwd));
        assert.ok(reason && reason.includes(report), `env -C into the project, from ${cwd}: ${cmd}: ${reason}`);
      }
      assert.equal(evaluate(payload(`env -C ${proj} cp base/report.md docs/other.md`, cwd)), null, `env -C onto an untracked file passes, from ${cwd}`);
    }
    // a non-literal DIR: the inner relative target is refused with the directory-unknown reason while the cwd's project is in play
    const nonLit = evaluate(payload('env -C "$D" cp base/report.md docs/report.md', proj));
    assert.ok(nonLit && /the directory it is relative to is not known/.test(nonLit) && nonLit.includes('env -C'), `non-literal DIR refuses with the reason: ${nonLit}`);
    // the redirection of an env -C command stays in the shell's cwd, not DIR
    assert.deepEqual(targets(`env -C ${out} cp base/report.md docs/report.md > log.txt`, proj), [path.join(out, 'docs', 'report.md'), path.join(proj, 'log.txt')].sort(), 'the operand resolves under DIR, the redirect in the cwd');
    for (const sh of shellsFor(['bash'], 'env -C in real bash')) assert.equal(overwrites(`env -C ${proj} cp base/report.md docs/report.md`, report, out, sh).changed, true, 'env -C into the project overwrites the tracked file in real bash');
    assert.equal(runHook(`env -C ${proj} cp base/report.md docs/report.md`, out).status, 2);
    assert.equal(fs.readFileSync(report, 'utf8'), 'The api session cut tail latency by 40%.\n');
  } finally { fs.rmSync(out, { recursive: true, force: true }); }
});

test('walk-around C: the wrapper set gains setsid, flock, taskset, chrt and numactl, each peeling its own operand', () => {
  // These run another command, like nohup and timeout, but were not peeled, so the write behind them passed. Each is
  // pinned hiding cp, tee and sed -i (refused) and with an untracked target (allowed); flock -c reads its script;
  // nice composes with setsid.
  const wrap = { setsid: 'setsid -w', flock: 'flock -x .', taskset: 'taskset -c 0', chrt: 'chrt -o 0', numactl: 'numactl --physcpubind=0' };
  for (const [name, pre] of Object.entries(wrap)) {
    assert.ok(evaluate(payload(`${pre} cp base/report.md docs/report.md`)) && evaluate(payload(`${pre} cp base/report.md docs/report.md`)).includes(report), `${name} cp refused`);
    assert.ok(evaluate(payload(`${pre} tee docs/report.md < base/report.md`)), `${name} tee refused`);
    assert.ok(evaluate(payload(`${pre} sed -i s/a/b/ docs/report.md`)), `${name} sed -i refused`);
    assert.equal(evaluate(payload(`${pre} cp base/report.md docs/other.md`)), null, `${name} onto an untracked file allowed`);
  }
  assert.ok(evaluate(payload("flock -x . -c 'cp base/report.md docs/report.md'")), 'flock -c reads its shell script');
  assert.equal(evaluate(payload("flock -x . -c 'cp base/report.md docs/other.md'")), null, 'flock -c onto an untracked file allowed');
  assert.ok(evaluate(payload('nice -n 19 setsid -w cp base/report.md docs/report.md')), 'nice composing with setsid');
  assert.ok(evaluate(payload('numactl -C 0 cp base/report.md docs/report.md')), 'numactl with a separate option argument');
  for (const sh of shellsFor(['bash'], 'setsid -w in real bash')) assert.equal(overwrites('setsid -w cp base/report.md docs/report.md', report, proj, sh).changed, true, 'setsid -w cp overwrites the tracked file in real bash');
  assert.equal(runHook('setsid -w cp base/report.md docs/report.md').status, 2);
  assert.equal(fs.readFileSync(report, 'utf8'), 'The api session cut tail latency by 40%.\n');
});

test('walk-around D: a same-command assignment to HOME makes $HOME and ~ unreadable for the rest of the command', () => {
  // The guard expands $HOME and ~ from its own environment; a command that reassigns HOME before the write named a
  // different directory than the guard read. Every assignment form is pinned refused, and the same write with no
  // reassignment is allowed where it should be.
  // Since the seventh pass's addendum (item 1) the plain top-level `HOME=notes;` is the one readable write to HOME: `$HOME`, `~`
  // and `${HOME}` after it resolve through notes/ and the write is refused BY NAME on the tracked note it lands on (the shells
  // perform it as spelled); every other form stays unreadable and is refused as before
  for (const cmd of ['HOME=notes; printf x > $HOME/seed.md', 'HOME=notes; printf x > ~/seed.md', 'HOME=notes; printf x > ${HOME}/seed.md']) {
    const reason = evaluate(payload(cmd));
    assert.ok(reason && /^Track-changes is ON for /.test(reason) && reason.includes(path.join(proj, 'notes', 'seed.md')), `the plain HOME= write resolves and the write is refused by name: ${cmd}: ${reason}`);
    assert.ok(!/\u2014/.test(reason), 'no em dash');
  }
  for (const cmd of ['export HOME=notes; printf x > $HOME/seed.md', "env HOME=notes bash -c 'printf x > $HOME/seed.md'"]) {
    const reason = evaluate(payload(cmd));
    assert.ok(reason && /names HOME outside an expansion|sets HOME as a prefix on a command/.test(reason) && reason.includes(proj), `HOME reassignment in another form refused as unreadable: ${cmd}: ${reason}`);
    assert.ok(!/\u2014/.test(reason), 'no em dash');
  }
  // no reassignment: $HOME expands to the guard's home; a write there passes when it is outside the project
  const home = process.env.HOME;
  const out = outsideDir();
  process.env.HOME = out;
  try {
    assert.equal(evaluate(payload('printf x > $HOME/seed.md')), null, 'no reassignment, a write under the real home outside the project: allowed');
    assert.equal(evaluate(payload('printf x > ~/seed.md')), null, 'the tilde spelling too');
  } finally { process.env.HOME = home; fs.rmSync(out, { recursive: true, force: true }); }
  fs.writeFileSync(path.join(proj, 'notes', 'n1.md'), 'a tracked note\n');
  for (const sh of shellsFor(['bash'], 'the HOME reassignment in real bash')) assert.equal(overwrites('HOME=notes; printf poison > $HOME/n1.md', path.join(proj, 'notes', 'n1.md'), proj, sh).changed, true, 'the HOME reassignment overwrites a tracked note in real bash');
  assert.equal(runHook('HOME=notes; printf poison > $HOME/n1.md').status, 2);
});

test('walk-around E: a word whose literal head parents one or more tracked roots refuses, naming the projects beneath; a numeric-only word there is allowed', () => {
  const R = outsideDir();
  const roots = path.join(R, 'roots');
  fs.mkdirSync(roots);
  const pabc = path.join(roots, 'p$abc');
  for (const d of ['.trackchanges', 'docs']) fs.mkdirSync(path.join(pabc, d), { recursive: true });
  fs.writeFileSync(path.join(pabc, '.trackchanges', 'config.json'), JSON.stringify({ v: 2, tracked: ['docs/report.md'] }));
  fs.writeFileSync(path.join(pabc, 'docs', 'report.md'), 'tracked\n');
  fs.writeFileSync(path.join(R, 'src.md'), 'src\n');
  const out = path.join(R, 'out');
  fs.mkdirSync(out);
  try {
    for (const cmd of [`printf poison > ${roots}/p$abc/docs/report.md`, `cp ${R}/src.md ${roots}/$X/docs/report.md`]) {
      const reason = evaluate(payload(cmd, out));
      assert.ok(reason && reason.includes('sits above the tracked project') && reason.includes(pabc), `class E names the project beneath: ${cmd}: ${reason}`);
      assert.ok(!/\u2014/.test(reason) && !ROMP_NOUNS.test(reason.split(R).join('<r>')), 'no em dash, no romp noun');
    }
    assert.equal(evaluate(payload(`printf x > ${roots}/$$.log`, out)), null, 'a numeric-only word in the parent folder is allowed');
    assert.equal(evaluate(payload(`printf x > ${roots}/plainfile.log`, out)), null, 'a literal file in the parent folder is allowed');
    for (const sh of shellsFor(['bash'], 'the root-spelling expansion in real bash')) assert.equal(overwrites('abc=\'$abc\'; printf poison > roots/p$abc/docs/report.md', path.join(pabc, 'docs', 'report.md'), R, sh).changed, true, 'the expansion spelling the root name overwrites the tracked file in real bash');
    assert.equal(runHook(`printf poison > ${roots}/p$abc/docs/report.md`, out).status, 2);
  } finally { fs.rmSync(R, { recursive: true, force: true }); }
});

test('walk-around F: an unreadable expansion anywhere under a tracked root refuses (the value can carry ..); a numeric one and the literal untracked twin are allowed', () => {
  // measured: v='../notes/seed'; > <tgt>/scratch/$v.md landed in the tracked notes/. scratch is an untracked subfolder
  // of the tracked project, so the landing-folder gate said allow; a non-numeric expansion under the root now refuses.
  const out = outsideDir();
  fs.writeFileSync(path.join(out, 'src.md'), 'src\n');
  fs.mkdirSync(path.join(proj, 'scratch'), { recursive: true });
  fs.writeFileSync(path.join(proj, 'notes', 'seed.md'), 'a tracked note\n');
  try {
    for (const cmd of [`printf poison > ${proj}/scratch/$v.md`, `cp ${out}/src.md ${proj}/scratch/$v.md`, `tee ${proj}/base/$v.md < ${out}/src.md`]) {
      const reason = evaluate(payload(cmd, out));
      assert.ok(reason && NOT_LITERAL.test(reason) && reason.includes(proj), `class F refuses under the tracked root: ${cmd}: ${reason}`);
    }
    assert.equal(evaluate(payload(`printf x > ${proj}/scratch/$$.md`, out)), null, 'a numeric-only name under the root is allowed');
    assert.equal(evaluate(payload(`cp ${out}/src.md ${proj}/scratch/plain.md`, out)), null, 'the documented untracked-subfolder literal twin is allowed');
    for (const sh of shellsFor(['bash'], 'the climbing value in real bash')) assert.equal(overwrites("v='../notes/seed'; printf poison > scratch/$v.md", path.join(proj, 'notes', 'seed.md'), proj, sh).changed, true, 'the ../ inside the value overwrites a tracked note in real bash');
    assert.equal(runHook(`printf poison > ${proj}/scratch/$v.md`, out).status, 2);
  } finally { fs.rmSync(out, { recursive: true, force: true }); }
});

test('walk-around G, folded into family 4: a directory the hook cannot search before a `..` refuses as a stat error, never folded lexically', () => {
  // `locked` mode 000 at hook time: lstat on locked/inner threw EACCES, which unwound to evaluate's catch (allow), and
  // chmod 755 locked && cp base/report.md locked/inner/../../docs/report.md overwrote the tracked file. The walk-around
  // lens second pass (2026-09-19) unified this with family 4: a stat error on a judged path refuses, naming the error.
  fs.mkdirSync(path.join(proj, 'locked', 'inner'), { recursive: true });
  fs.chmodSync(path.join(proj, 'locked'), 0);
  try {
    const reason = evaluate(payload('chmod 755 locked && cp base/report.md locked/inner/../../docs/report.md'));
    assert.ok(reason && /could not check .* on that path \(permission denied\)/.test(reason.replace(/\s+/g, ' ')) && reason.includes(`${proj}/locked`), `unsearchable dir before .. refused: ${reason}`);
    assert.ok(!/\u2014/.test(reason), 'no em dash');
    // a searchable directory before the same `..` folds on the real path, as ever
    fs.chmodSync(path.join(proj, 'locked'), 0o755);
    assert.deepEqual(targets('cp base/report.md locked/inner/../../docs/report.md'), [report], 'a searchable dir folds to docs/report.md');
    fs.chmodSync(path.join(proj, 'locked'), 0);
    for (const sh of shellsFor(['bash'], 'the chmod then the climb in real bash')) assert.equal(overwrites('chmod 755 locked && cp base/report.md locked/inner/../../docs/report.md', report, proj, sh).changed, true, 'the command overwrites the tracked file in real bash once locked is chmod-ed');
    fs.chmodSync(path.join(proj, 'locked'), 0);
    assert.equal(runHook('chmod 755 locked && cp base/report.md locked/inner/../../docs/report.md').status, 2);
  } finally { fs.chmodSync(path.join(proj, 'locked'), 0o755); }
});

test('walk-around H: a symlink the same command makes redirects a later literal target to what it points at', () => {
  for (const cmd of ['ln -s docs mydocs && cp base/report.md mydocs/report.md', 'ln -s docs/report.md mylink.md && cp base/report.md mylink.md', 'ln -s notes ndir && echo hi > ndir/n1.md']) {
    const reason = evaluate(payload(cmd));
    assert.ok(reason && (reason.includes(report) || reason.includes(path.join(proj, 'notes', 'n1.md'))), `in-command link resolved to the tracked file: ${cmd}: ${reason}`);
  }
  assert.equal(evaluate(payload('ln -s base mylink && cp base/report.md mylink/other.md')), null, 'a link to an untracked folder is allowed');
  assert.deepEqual(targets('ln -s docs mydocs && cp base/report.md mydocs/report.md'), [path.join(proj, 'mydocs'), report].sort(), 'the link entry and the redirected copy');
  for (const sh of shellsFor(['bash'], 'the in-command link in real bash')) assert.equal(overwrites('ln -s docs mydocs && cp base/report.md mydocs/report.md', report, proj, sh).changed, true, 'the in-command link overwrites the tracked file in real bash');
  assert.equal(runHook('ln -s docs mydocs && cp base/report.md mydocs/report.md').status, 2);
  assert.equal(fs.readFileSync(report, 'utf8'), 'The api session cut tail latency by 40%.\n');
});

// ── the walk-around lens, second pass: six families closed as rules (2026-09-19) ──
//
// A second walk-around pass ran the hook as a process and found six FAMILIES of in-model write the hook read yet let
// through, each a live overwrite in real bash. Each is closed by ONE rule and pinned here in both directions (every
// listed instance refused, its allowed literal/numeric twin, and a real bash run of one instance per family that
// overwrites the tracked file when run, the pre-fix hook allowing it, and which the hook now refuses).

test('family 1: the option tables accept a glued short form (sort -oFILE), and env -S is refused outright as an opaque string (the third pass, superseding the second pass\'s shell reading)', () => {
  // sort's `-o` glued short form yielded no target; env -S / --split-string was skipped as an operand, so the command
  // it carries was never read. The second pass read the string as a shell command; the third pass (rule (b)) refuses it
  // outright, since env applies its OWN getopt to the split words and `env -S '-u FOO cp …'` ran a copy the shell
  // reading took for a non-writer. So every env -S spelling refuses while the project is in play, the untracked twin too.
  assert.ok(evaluate(payload('sort -odocs/report.md base/report.md')) && evaluate(payload('sort -odocs/report.md base/report.md')).includes(report), 'sort -oFILE refused onto the tracked file');
  for (const cmd of ["env -S'cp base/report.md docs/report.md'", "env -S 'cp base/report.md docs/report.md'", "env --split-string='cp base/report.md docs/report.md'", "env -S'cp base/report.md docs/other.md'"]) {
    const reason = evaluate(payload(cmd));
    assert.ok(reason && /`env (-S|--split-string)` hands the rest of the command to a splitter/.test(reason) && reason.includes(proj), `env -S refused as opaque: ${cmd}: ${reason}`);
  }
  assert.equal(evaluate(payload('sort -odocs/other.md base/report.md')), null, 'sort -oFILE onto the untracked twin is allowed');
  assert.deepEqual(targets('sort -o docs/report.md base/report.md'), [report], 'the separate form still names it');
  for (const sh of shellsFor(['bash'], 'env -S in real bash')) assert.equal(overwrites("env -S'cp base/report.md docs/report.md'", report, proj, sh).changed, true, 'env -S overwrites the tracked file in real bash');
  assert.equal(runHook("env -S'cp base/report.md docs/report.md'").status, 2, 'and the hook refuses it');
  assert.equal(fs.readFileSync(report, 'utf8'), 'The api session cut tail latency by 40%.\n');
});

test('family 2: an assignment to HOME in any form the shells offer makes $HOME and ~ unreadable for the whole command', () => {
  // class D (round 4) matched `HOME=…` alone; the shells offer more, and each carried a write into a tracked folder.
  fs.writeFileSync(path.join(proj, 'notes', 'n1.md'), 'a tracked note\n');
  const forms = [
    'HOME+=/notes; printf poison > "$HOME/report.md"',
    'read HOME <<< notes; printf poison > "$HOME/report.md"',
    'printf -v HOME notes; printf poison > "$HOME/report.md"',
    'declare HOME=notes; printf poison > "$HOME/report.md"',
    'local HOME=notes; printf poison > "$HOME/report.md"',
    'readonly HOME=notes; printf poison > "$HOME/report.md"',
    'typeset HOME=notes; printf poison > "$HOME/report.md"',
    'mapfile HOME <<< notes; printf poison > "$HOME/report.md"',
    'getopts x HOME; printf poison > "$HOME/report.md"',
    'for HOME in notes; do printf poison > "$HOME/report.md"; done',
  ];
  for (const cmd of forms) {
    const reason = evaluate(payload(cmd));
    assert.ok(reason && /names HOME outside an expansion/.test(reason) && reason.includes(proj), `HOME assignment refused: ${cmd}: ${reason}`);
    assert.ok(!/\u2014/.test(reason), 'no em dash');
  }
  // no reassignment: $HOME expands to the guard's home; a write under it outside the project is allowed
  const home = process.env.HOME;
  const out = outsideDir();
  process.env.HOME = out;
  try {
    assert.equal(evaluate(payload('printf x > $HOME/seed.md')), null, 'no reassignment, a write under the real home outside the project');
  } finally { process.env.HOME = home; fs.rmSync(out, { recursive: true, force: true }); }
  for (const sh of shellsFor(['bash'], 'read HOME in real bash')) assert.equal(overwrites('read HOME <<< notes; printf poison > "$HOME/n1.md"', path.join(proj, 'notes', 'n1.md'), proj, sh).changed, true, 'the read HOME reassignment overwrites a tracked note in real bash');
  assert.equal(runHook('read HOME <<< notes; printf poison > "$HOME/n1.md"').status, 2);
  assert.equal(runHook('HOME+=/notes; printf poison > "$HOME/n1.md"').status, 2, 'and the HOME+= form is refused too');
});

test('family 3: a remove, rename or hard/symbolic link earlier in the command makes a later word under that prefix unreadable', () => {
  // rm/mv removing a tracked folder then relinking it, a rename aside and back, and a hard link or cp -l/cp -s aliasing
  // a tracked inode each hid the tracked file behind hook-time state; the mutation makes the later write unreadable.
  fs.writeFileSync(path.join(proj, 'notes', 'n1.md'), 'a tracked note\n');
  const cases = [
    ['rm -rf docs && ln -s notes docs && echo x > docs/n1.md', /an earlier `rm`/],
    ['mv docs docs.old && ln -s notes docs && echo x > docs/n1.md', /an earlier `mv`/],
    ['mv docs d2 && cp base/report.md d2/report.md && mv d2 docs', /an earlier `mv`/],
    ['ln docs/report.md hard.md && cp base/report.md hard.md', /an earlier `ln`/],
    ['cp -l docs/report.md hard2.md && echo x > hard2.md', /an earlier `cp -l`/],
    ['cp -s docs/report.md sl.md && cp base/report.md sl.md', /an earlier `cp -l`/],
  ];
  for (const [cmd, why] of cases) {
    const reason = evaluate(payload(cmd));
    assert.ok(reason && why.test(reason) && reason.includes(proj), `mutation refused: ${cmd}: ${reason}`);
    assert.ok(!/\u2014/.test(reason) && !ROMP_NOUNS.test(reason.split(proj).join('<p>')), 'no em dash, no romp noun');
  }
  // an untracked twin: a remove and a write both clear of any tracked file; and a plain ln -s (class H) still refuses by name
  fs.mkdirSync(path.join(proj, 'scratch'), { recursive: true });
  assert.equal(evaluate(payload('rm -f scratch/old.md && cp base/report.md scratch/new.md')), null, 'a remove and write clear of tracked files is allowed');
  assert.equal(evaluate(payload('cp -l docs/report.md scratch/h.md && echo x > docs/other.md')), null, 'the write after the mutation lands on an untracked file');
  assert.match(evaluate(payload('ln -s docs mydocs && cp base/report.md mydocs/report.md')), /^Track-changes is ON for /, 'a plain ln -s with an untouched name is still resolved by class H');
  for (const sh of shellsFor(['bash'], 'the hard link in real bash')) assert.equal(overwrites('ln docs/report.md hard.md && cp base/report.md hard.md', report, proj, sh).changed, true, 'the hard link overwrites the tracked file in real bash');
  assert.equal(runHook('ln docs/report.md hard.md && cp base/report.md hard.md').status, 2);
});

test('family 4: a stat error other than ENOENT anywhere on a judged path refuses from any cwd, naming the error and the path', () => {
  // an lstat/realpath/readdir/config error (EACCES on a parent, a tracked folder, .trackchanges, the whole project) is
  // an answer the hook does not have, so it refuses. The round-3 catch that read it as allow is gone.
  fs.writeFileSync(path.join(proj, 'notes', 'n1.md'), 'a tracked note\n');
  fs.mkdirSync(path.join(proj, 'locked'), { recursive: true });
  fs.symlinkSync(path.join(proj, 'docs'), path.join(proj, 'locked', 'lnk'));
  const cases = [
    ['locked', 'chmod 755 locked && cp base/report.md locked/lnk/report.md', /could not check .* \(permission denied\)/],
    ['notes', 'chmod 755 notes && cp base/report.md notes/n1.md', /could not check .* \(permission denied\)/],
    ['docs', 'chmod 755 docs && cp base/report.md docs/report.md', /could not check .* \(permission denied\)/],
    ['.trackchanges', 'chmod 755 .trackchanges && cp base/report.md docs/report.md', /could not read the tracking config/],
  ];
  for (const [dir, cmd, why] of cases) {
    fs.chmodSync(path.join(proj, dir), 0);
    let reason;
    try { reason = evaluate(payload(cmd)); } finally { fs.chmodSync(path.join(proj, dir), 0o755); }
    assert.ok(reason && why.test(reason.replace(/\s+/g, ' ')) && reason.includes(proj), `stat error refused (${dir}): ${cmd}: ${reason}`);
    assert.ok(!/\u2014/.test(reason), 'no em dash');
  }
  // the whole project mode 000, from a cwd outside it: still refused (a directory the hook cannot search may be a project)
  const out = outsideDir();
  try {
    fs.chmodSync(proj, 0);
    let reason;
    try { reason = evaluate(payload(`chmod 755 ${proj} && cp ${proj}/base/report.md ${proj}/docs/report.md`, out)); } finally { fs.chmodSync(proj, 0o755); }
    assert.ok(reason && /could not check/.test(reason), `the whole project mode 000 refuses from outside: ${reason}`);
    // a readable path outside every project passes; a mode-000 dir outside every project is the documented false refusal
    assert.equal(evaluate(payload(`cp ${out}/src.md ${out}/plain.md`, out)), null, 'a readable path outside every project passes');
    fs.writeFileSync(path.join(out, 'src.md'), 's\n');
    fs.mkdirSync(path.join(out, 'ol'));
    fs.chmodSync(path.join(out, 'ol'), 0);
    let r2;
    try { r2 = evaluate(payload(`cp ${out}/src.md ${out}/ol/y.md`, out)); } finally { fs.chmodSync(path.join(out, 'ol'), 0o755); }
    assert.ok(r2 && /could not check/.test(r2), 'a mode-000 directory outside every project is refused too (the documented cost)');
  } finally { fs.rmSync(out, { recursive: true, force: true }); }
  for (const sh of shellsFor(['bash'], 'the mode-000 folder in real bash')) assert.equal(overwrites('chmod 755 notes && cp base/report.md notes/n1.md', path.join(proj, 'notes', 'n1.md'), proj, sh).changed, true, 'the mode-000 tracked folder overwrite runs in real bash');
  fs.chmodSync(path.join(proj, 'notes'), 0);
  try { assert.equal(runHook('chmod 755 notes && cp base/report.md notes/n1.md').status, 2); } finally { fs.chmodSync(path.join(proj, 'notes'), 0o755); }
});

test('family 5: a marker between a tracked root and the target refuses, naming both markers; the nearest-marker rule stays for the untracked case', () => {
  // findVaultRoot stops at the nearest marker; a .git or empty .trackchanges made under the project makes the folder its
  // own config-less root and every write under it read as untracked while the outer list still names the file.
  fs.writeFileSync(path.join(proj, 'notes', 'n1.md'), 'a tracked note\n');
  fs.mkdirSync(path.join(proj, 'docs', '.git'), { recursive: true });
  fs.mkdirSync(path.join(proj, 'notes', '.trackchanges'), { recursive: true });
  try {
    const r1 = evaluate(payload('cp base/report.md docs/report.md'));
    assert.ok(r1 && /a `\.git` at .* between that project/.test(r1) && r1.includes(`${proj}/docs`) && r1.includes(proj), `nested .git refused: ${r1}`);
    const r2 = evaluate(payload('echo x > notes/n1.md'));
    assert.ok(r2 && /a `\.trackchanges` at .* between that project/.test(r2), `nested .trackchanges refused: ${r2}`);
    assert.ok(!/\u2014/.test(r1) && !/\u2014/.test(r2), 'no em dash');
    // a file the outer list does not name keeps the nearest root's answer (untracked, allowed)
    assert.equal(evaluate(payload('cp base/report.md docs/other.md')), null, 'a file the outer list does not name is allowed');
  } finally { fs.rmSync(path.join(proj, 'docs', '.git'), { recursive: true, force: true }); fs.rmSync(path.join(proj, 'notes', '.trackchanges'), { recursive: true, force: true }); }
  // no marker between: the write is refused by name as ever
  assert.match(evaluate(payload('cp base/report.md docs/report.md')), /^Track-changes is ON for /, 'with no nested marker the write is judged by name');
  fs.mkdirSync(path.join(proj, 'docs', '.git'), { recursive: true });
  for (const sh of shellsFor(['bash'], 'the nested .git in real bash')) assert.equal(overwrites('cp base/report.md docs/report.md', report, proj, sh).changed, true, 'the copy overwrites the tracked file in real bash even with a nested .git');
  assert.equal(runHook('cp base/report.md docs/report.md').status, 2);
  fs.rmSync(path.join(proj, 'docs', '.git'), { recursive: true, force: true });
});

test('family 6: a cd the guard cannot know ran in this shell leaves the directory unknown, so a later relative write refuses with the construct named', () => {
  // a cd after &&/|| (its run depends on the previous status), a cd in a pipeline or backgrounded (a subshell), a cd
  // under a wrapper, pushd -n, a physical cd, and a call of a cd-bearing function each moved the guard's directory
  // where the shell did not, so a relative write after it was judged in the wrong place.
  const UNKNOWN = /the directory it is relative to is not known/;
  const cases = [
    ['false && cd docs; cp base/report.md docs/report.md', /after `&&` may not run/],
    ['true || cd docs; cp base/report.md docs/report.md', /after `\|\|` may not run/],
    ['[ -d nosuch ] && cd docs; cp base/report.md docs/report.md', /after `&&` may not run/],
    ['cd docs | cat; cp base/report.md docs/report.md', /part of a pipeline/],
    ['cd docs & wait; cp base/report.md docs/report.md', /backgrounded/],
    ['nice cd docs; cp base/report.md docs/report.md', /under a wrapper/],
    ['env cd docs; cp base/report.md docs/report.md', /under a wrapper/],
    ['pushd -n docs; cp base/report.md docs/report.md', /pushes a directory without changing to it/],
    ['set -P; cd notes; cd ..; cp base/report.md docs/report.md', /physically/],
    ['f() { cd docs; }; f; cp ../base/report.md report.md', /call of the function `f`/],
  ];
  for (const [cmd, why] of cases) {
    const reason = evaluate(payload(cmd));
    assert.ok(reason && UNKNOWN.test(reason) && why.test(reason), `family 6 refused: ${cmd}: ${reason && reason.split('\n')[0]}`);
    assert.ok(reason.includes('Spell the target as an absolute path, or cd to a literal directory that exists first'), 'the remedy');
    assert.ok(!/\u2014/.test(reason) && !ROMP_NOUNS.test(reason.split(proj).join('<p>')), 'no em dash, no romp noun');
  }
  // allowed twins: a relative write to an untracked file after cd docs, and a plain unconditional cd sequence judged by name
  assert.equal(evaluate(payload('cd docs && echo x > other.md')), null, 'a plain cd then an untracked relative write is allowed');
  assert.match(evaluate(payload('cd notes; cp ../base/report.md ../docs/report.md')), /^Track-changes is ON for /, 'a plain cd in sequence keeps its handling, refused by name');
  const original = fs.readFileSync(report, 'utf8');
  for (const sh of shellsFor(['bash'], 'the skipped cd in real bash')) {
    const shell = spawnSync(sh, ['-c', 'false && cd docs; cp base/report.md docs/report.md'], { cwd: proj, encoding: 'utf8', env: { PATH: process.env.PATH } });
    assert.equal(shell.status, 0, shell.stderr);
    assert.equal(fs.readFileSync(report, 'utf8'), 'an older copy\n', 'the skipped cd leaves the copy on the tracked file in real bash');
    fs.writeFileSync(report, original);
  }
  assert.equal(runHook('false && cd docs; cp base/report.md docs/report.md').status, 2, 'and the hook refuses it');
});

// ── the walk-around lens, third pass: the family rules are re-keyed on what the guard can see (2026-09-19) ──
//
// A third pass walked around each second-pass enumeration with the next spelling: a nameref and `select HOME in` for
// the HOME assignment forms; a glued `env -Cdocs`, an abbreviated `env --chd=` and `--c`, a nested `env -C docs env -C
// ..` and an `env -S` string beginning with env's own option for the wrapper tables; a non-literal `ln -s` source for
// class H; zsh's `set -o chaselinks` for the physical-cd list; a two-segment expansion under a grandparent for the
// parent-prefix rule; and `cp --targ` from a cwd in no project for the unknown-option refusal. Each rule below is keyed
// on what the guard can see (a token, an unparsed option, a non-literal operand, the presence of a construct), never on
// a list of forms, and is pinned both ways: every listed instance refused, its allowed literal twin allowed, and a real
// shell run of one instance per rule that overwrites the tracked file when unguarded and which the hook now refuses.

const HOME_RULE = /names HOME outside an expansion/;
// A second tracked project under a fresh base directory: `<base>/<rel>` with docs/report.md tracked and base/report.md.
const trackedProjectAt = (base, rel) => {
  const root = path.join(base, rel);
  for (const d of ['.trackchanges', 'docs', 'base']) fs.mkdirSync(path.join(root, d), { recursive: true });
  fs.writeFileSync(path.join(root, '.trackchanges', 'config.json'), JSON.stringify({ v: 2, tracked: ['docs/report.md'] }));
  fs.writeFileSync(path.join(root, 'docs', 'report.md'), 'tracked prose\n');
  fs.writeFileSync(path.join(root, 'base', 'report.md'), 'an older copy\n');
  return root;
};

test('rule (a) bare identifier: the identifier HOME anywhere in the command outside a $-expansion makes $HOME and ~ unreadable, whatever the form; a command that only reads $HOME is judged as before', () => {
  fs.writeFileSync(path.join(proj, 'notes', 'n1.md'), 'a tracked note\n');
  const forms = [
    `declare -n r=HOME; r=${proj}/notes; printf poison > "$HOME/n1.md"`,                       // a nameref (the third pass, P1)
    `f() { local -n r=HOME; r=${proj}/notes; }; f; printf poison > "$HOME/n1.md"`,             // a nameref in a function (P2)
    `select HOME in ${proj}/notes; do break; done <<< 1; printf poison > "$HOME/n1.md"`,       // select, the for the list missed (P18)
    `printf -vHOME '%s' ${proj}/notes; printf poison > "$HOME/n1.md"`,                          // the glued -v (P3)
    `declare -n r=HOME; r=${proj}/notes; printf poison > ~/n1.md`,                              // the tilde spelling (P26)
    'unset HOME; printf poison > "$HOME/n1.md"',                                                 // unset: HOME empty, the write lands in /n1.md or the cwd
    'typeset HOME; printf poison > ~/n1.md',
    'export HOME; printf poison > "$HOME/n1.md"',
    `read 'HOME' <<< ${proj}/notes; printf poison > "$HOME/n1.md"`,                             // the identifier quoted still assigns
    `(( HOME = 5 )); printf poison > "$HOME/n1.md"`,                                            // an arithmetic body (the header claimed it; now it is scanned)
    'echo HOME=/etc/skel; printf poison > "$HOME/n1.md"',                                       // the stated cost: a mention that assigns nothing
  ];
  for (const cmd of forms) {
    const reason = evaluate(payload(cmd));
    assert.ok(reason && HOME_RULE.test(reason) && reason.includes(proj), `HOME named outside an expansion refuses the home write: ${cmd}: ${reason}`);
    assert.ok(reason.includes('Spell the path out'), 'the remedy');
    assert.ok(!/\u2014/.test(reason) && !ROMP_NOUNS.test(reason.split(proj).join('<p>')), 'no em dash, no romp noun');
  }
  // a bare `cd` or a `cd ~` after a mention of HOME in a form the guard does not read leaves the directory unknown, so a later
  // relative write refuses; after the one readable form (a plain top-level `HOME=<dir>;`, the seventh pass's addendum) the bare
  // cd and the `env -C ~` follow the assigned directory and the write is refused by name
  for (const cmd of [`declare -n r=HOME; r=${proj}/notes; cd ~; printf poison > n1.md`, `export HOME=${proj}/notes; cd; printf poison > n1.md`]) {
    const reason = evaluate(payload(cmd));
    assert.ok(reason && /the directory it is relative to is not known/.test(reason) && HOME_RULE.test(reason), `a cd through HOME after its mention: ${cmd}: ${reason}`);
  }
  for (const cmd of [`HOME=${proj}/notes; cd; printf poison > n1.md`, `HOME=${proj}; env -C ~ cp base/report.md docs/report.md`]) {
    const reason = evaluate(payload(cmd));
    assert.ok(reason && /^Track-changes is ON for /.test(reason), `a cd through the plain HOME= write resolves and the write is refused by name: ${cmd}: ${reason}`);
  }
  // the twins: a command that only READS $HOME (an expansion, no bare identifier) is judged by the guard's home as before
  const home = process.env.HOME;
  const out = outsideDir();
  process.env.HOME = out;
  try {
    for (const cmd of ['echo $HOME; printf x > $HOME/seed.md', 'printf x > ~/seed.md', 'echo "${HOME}"; printf x > "$HOME/seed.md"', 'ls $HOMEDIR; printf x > ~/seed.md', 'cd; printf x > seed.md']) {
      assert.equal(evaluate(payload(cmd)), null, `reads of $HOME with no bare identifier: allowed: ${cmd}`);
    }
  } finally { process.env.HOME = home; fs.rmSync(out, { recursive: true, force: true }); }
  assert.equal(evaluate(payload('echo HOME=x; printf x > docs/other.md')), null, 'a mention of HOME with no home write changes nothing');
  assert.equal(evaluate(payload('grep HOME /etc/passwd')), null, 'a read that mentions HOME is a read');
  // real bash: the nameref reassigns HOME and the write lands on the tracked note; the hook refuses it
  const n1 = path.join(proj, 'notes', 'n1.md');
  for (const cmd of [`declare -n r=HOME; r=${proj}/notes; printf poison > "$HOME/n1.md"`, `select HOME in ${proj}/notes; do break; done <<< 1; printf poison > "$HOME/n1.md"`, `printf -vHOME '%s' ${proj}/notes; printf poison > "$HOME/n1.md"`]) {
    for (const sh of shellsFor(['bash'], cmd)) assert.equal(overwrites(cmd, n1, proj, sh).changed, true, `overwrites the tracked note in real bash: ${cmd}`);
    assert.equal(runHook(cmd).status, 2, `and the hook refuses it: ${cmd}`);
  }
});

test('rule (b) fully parsed or refused: a wrapper option outside its table refuses naming it (glued to a letter it does not know, abbreviated, unknown, non-literal), a nested env -C composes, env -S is opaque and refused outright, and every known spelling still peels to the write', () => {
  const R = outsideDir();
  try {
    const refused = [
      // the third-pass env instances
      ['env -Cdocs cp ../base/report.md report.md', /^Track-changes is ON for .*docs\/report\.md/, 'the glued -Cdocs is a chdir into docs'],
      ['env --chd=docs cp ../base/report.md report.md', /`env` wrapper carries the option --chd=docs/, 'an abbreviation refuses'],
      ['env --c docs cp ../base/report.md report.md', /`env` wrapper carries the option --c,/, 'an abbreviation refuses'],
      ['env -C docs env -C .. cp base/report.md docs/report.md', /^Track-changes is ON for .*docs\/report\.md/, 'a nested chdir composes: docs, then .. under docs'],
      ["env -S '-u FOO cp base/report.md docs/report.md'", /`env -S` hands the rest of the command to a splitter/, 'env -S with a leading env option'],
      ["env -S '-i cp base/report.md docs/report.md'", /`env -S` hands/, ''],
      ["env -S '-C docs cp ../base/report.md report.md'", /`env -S` hands/, ''],
      ["env -S '--chdir=docs cp ../base/report.md report.md'", /`env -S` hands/, ''],
      ["env -S '-- cp base/report.md docs/report.md'", /`env -S` hands/, ''],
      ["env -C docs -S 'cp ../base/report.md report.md'", /`env -S` hands/, 'a chdir before -S'],
      ["env -S'cp base/report.md docs/report.md'", /`env -S` hands/, 'glued'],
      ["env --split-string='cp base/report.md docs/report.md'", /`env --split-string` hands/, ''],
      ["env -S 'echo hi'", /`env -S` hands/, 'opaque whatever the string, while the project is in play'],
      // other wrappers, the same rule
      ['env --frobnicate cp base/report.md docs/other.md', /`env` wrapper carries the option --frobnicate/, 'an unknown option refuses even onto an untracked file'],
      ['env "$FLAGS" cp base/report.md docs/other.md', /`env` wrapper carries the option "\$FLAGS"/, 'an option the shell fills in'],
      ['nice -x cp base/report.md docs/other.md', /`nice` wrapper carries the option -x/, ''],
      ['timeout --preserve-stat 5 cp base/report.md docs/other.md', /`timeout` wrapper carries the option --preserve-stat/, 'an abbreviation'],
      ['sudo -s cp base/report.md docs/other.md', /`sudo -s` hands the rest of the command/, 'sudo -s runs a shell over the rest'],
      ['sudo -R / cp base/report.md docs/other.md', /`sudo -R` hands/, 'a chroot moves every path'],
      ['numactl --show cp base/report.md docs/other.md', /`numactl` wrapper carries the option --show/, 'not a command-running option'],
    ];
    for (const [cmd, why, note] of refused) {
      const reason = evaluate(payload(cmd));
      assert.ok(reason && why.test(reason), `${note || 'refused'}: ${cmd}: ${reason}`);
      assert.ok(!/\u2014/.test(reason) && !ROMP_NOUNS.test(reason.split(proj).join('<p>')), 'no em dash, no romp noun');
    }
    // every known spelling peels to the inner command, judged as ever: allowed onto the untracked twin
    const known = [
      'env -i cp base/report.md docs/other.md', 'env -u FOO cp base/report.md docs/other.md', 'env FOO=1 cp base/report.md docs/other.md', 'env - cp base/report.md docs/other.md',
      'env -0 -v -i cp base/report.md docs/other.md', 'env --ignore-environment cp base/report.md docs/other.md', 'env --block-signal=INT cp base/report.md docs/other.md',
      'nice -n 19 cp base/report.md docs/other.md', 'nice -n19 cp base/report.md docs/other.md', 'nice -19 cp base/report.md docs/other.md', 'nice --adjustment=5 cp base/report.md docs/other.md',
      'timeout 5 cp base/report.md docs/other.md', 'timeout -s KILL 5 cp base/report.md docs/other.md', 'timeout --preserve-status 5 cp base/report.md docs/other.md', 'timeout -k 2 --foreground 5s cp base/report.md docs/other.md',
      'timeout "$T" cp base/report.md docs/other.md',
      'sudo -u root cp base/report.md docs/other.md', 'sudo -E -n cp base/report.md docs/other.md', 'sudo --preserve-env=PATH cp base/report.md docs/other.md',
      'nohup cp base/report.md docs/other.md', 'ionice -c 3 cp base/report.md docs/other.md', 'ionice -c3 -n7 cp base/report.md docs/other.md', 'stdbuf -oL cp base/report.md docs/other.md', 'stdbuf -o L cp base/report.md docs/other.md',
      'setsid -w cp base/report.md docs/other.md', 'flock -x . cp base/report.md docs/other.md', 'flock -w 5 . cp base/report.md docs/other.md', 'flock -n . -c "cp base/report.md docs/other.md"',
      'taskset -c 0 cp base/report.md docs/other.md', 'taskset 0x1 cp base/report.md docs/other.md', 'chrt -o 0 cp base/report.md docs/other.md', 'chrt -T 100000 -d 0 cp base/report.md docs/other.md',
      'numactl --physcpubind=0 cp base/report.md docs/other.md', 'numactl -C 0 cp base/report.md docs/other.md', 'numactl -C0 -l cp base/report.md docs/other.md',
      'command cp base/report.md docs/other.md', 'command -p cp base/report.md docs/other.md', 'builtin echo x > docs/other.md', 'exec cp base/report.md docs/other.md', 'exec -a cp cp base/report.md docs/other.md',
      'time -p cp base/report.md docs/other.md', 'time cp base/report.md docs/other.md',
      'env -C docs env -C .. cp base/report.md docs/other.md', 'env -Cdocs cp ../base/report.md other.md', 'env -C base cp report.md ../docs/other.md',
      'nice -n 19 setsid -w ionice -c 3 cp base/report.md docs/other.md',
    ];
    for (const cmd of known) assert.equal(evaluate(payload(cmd)), null, `a known spelling peels and the untracked write is allowed: ${cmd}`);
    for (const cmd of ['env -i cp base/report.md docs/report.md', 'nice -n19 cp base/report.md docs/report.md', 'timeout --preserve-status 5 cp base/report.md docs/report.md', 'flock -w 5 . cp base/report.md docs/report.md', 'time -p cp base/report.md docs/report.md', 'sudo --preserve-env=PATH cp base/report.md docs/report.md', 'env - cp base/report.md docs/report.md']) {
      assert.match(evaluate(payload(cmd)), /^Track-changes is ON for /, `and onto the tracked file it is refused by name: ${cmd}`);
    }
    // GNU time -o writes its file: a write target of its own, in the shell's cwd
    assert.deepEqual(targets('time -o docs/report.md make'), [report], 'time -o FILE is a write');
    assert.match(evaluate(payload('time --output=docs/report.md make')), /its time -o would write/, 'and refused by name');
    assert.equal(evaluate(payload('time -o docs/other.md make')), null, 'onto an untracked file it is allowed');
    // from a cwd in no project: a known wrapper onto an outside file passes; an unknown option beside an absolute path inside
    // the project refuses (the candidate words are judged by their own project, rule (f)'s direction)
    fs.writeFileSync(path.join(R, 'a.md'), 'a\n');
    assert.equal(evaluate(payload(`env -i cp ${R}/a.md ${R}/b.md`, R)), null, 'a known wrapper from a cwd in no project passes');
    assert.equal(evaluate(payload(`env --frobnicate cp ${R}/a.md ${R}/b.md`, R)), null, 'an unknown option with nothing in play is dropped, as every unreadable word is');
    assert.ok(/`env` wrapper carries the option --frobnicate/.test(evaluate(payload(`env --frobnicate cp ${R}/a.md ${proj}/docs/other.md`, R)) || ''), 'an unknown option beside a path inside the project refuses from a cwd in none');
    assert.ok(/`env -S` hands/.test(evaluate(payload(`env -S 'cp ${proj}/base/report.md ${proj}/docs/report.md'`, R)) || ''), 'env -S naming a path inside the project refuses from a cwd in none');
    // real bash: the glued chdir and the env -S string beginning with env's own option each overwrite the tracked file; the hook refuses both
    for (const cmd of ['env -Cdocs cp ../base/report.md report.md', "env -S '-u FOO cp base/report.md docs/report.md'", 'env -C docs env -C .. cp base/report.md docs/report.md']) {
      for (const sh of shellsFor(['bash'], cmd)) assert.equal(overwrites(cmd, report, proj, sh).changed, true, `overwrites the tracked file in real bash: ${cmd}`);
      assert.equal(runHook(cmd).status, 2, `and the hook refuses it: ${cmd}`);
    }
    assert.equal(fs.readFileSync(report, 'utf8'), 'The api session cut tail latency by 40%.\n');
  } finally { fs.rmSync(R, { recursive: true, force: true }); }
});

test('rule (c) non-literal link source: an ln -s whose source the guard cannot read marks the link name unknown, so a later write through it refuses with the reason; a literal source keeps class H', () => {
  fs.writeFileSync(path.join(proj, 'notes', 'n1.md'), 'a tracked note\n');
  fs.mkdirSync(path.join(proj, 'sub'));
  const cases = [
    'ln -s "$(pwd)/docs" mydocs && cp base/report.md mydocs/report.md',    // the third pass, #59 (its `$PWD` spelling resolves since B2, below)
    'ln -sf "$(pwd)/docs" md2 && cp base/report.md md2/report.md',         // N1
    'ln -s $(echo docs) md3 && cp base/report.md md3/report.md',            // N2
    'ln -s "$D" md4; echo x > md4/n1.md',
    'ln -s -t sub "$SRC"; echo x > sub/report.md',                          // the name is the source\'s basename, unreadable: the folder is unknown
    'ln -s "$A" "$B" sub; echo x > sub/report.md',                          // several sources into a directory
    'ln -s docs "$L" md5; echo x > md5/report.md',                          // several sources into a name that is no directory
  ];
  for (const cmd of cases) {
    const reason = evaluate(payload(cmd));
    assert.ok(reason && /an earlier `ln -s` in the same command linked /.test(reason) && reason.includes(proj), `a non-literal link source makes the name unknown: ${cmd}: ${reason}`);
    assert.ok(reason.includes('Run the `ln -s` in a command of its own'), 'the remedy');
    assert.ok(!/\u2014/.test(reason) && !ROMP_NOUNS.test(reason.split(proj).join('<p>')), 'no em dash, no romp noun');
  }
  // the twins: a literal source is resolved (class H), a link to an untracked folder is allowed, and a write NOT through the link is judged as ever
  assert.match(evaluate(payload('ln -s docs mydocs && cp base/report.md mydocs/report.md')), /^Track-changes is ON for /, 'a literal source resolves to the tracked file');
  // B2 (2026-09-19): `$PWD` is a value the guard reads, so the third pass's `"$PWD/docs"` source is literal now and class H refuses by name
  for (const cmd of ['ln -s "$PWD/docs" mydocs && cp base/report.md mydocs/report.md', 'ln -sf "$PWD/docs" md2 && cp base/report.md md2/report.md']) assert.match(evaluate(payload(cmd)), /^Track-changes is ON for /, `a $PWD source resolves, class H: ${cmd}`);
  assert.equal(evaluate(payload('ln -s base mylink && cp base/report.md mylink/other.md')), null, 'a literal link to an untracked folder is allowed');
  assert.equal(evaluate(payload('ln -s "$PWD/base" mylink2 && cp base/report.md docs/other.md')), null, 'a non-literal link the later write does not pass through changes nothing');
  assert.equal(evaluate(payload('ln -s $(echo base) md6; cp base/report.md scratch.md')), null, 'the same, another spelling');
  // real bash: the link to $PWD/docs carries the copy onto the tracked file; the hook refuses it
  for (const cmd of ['ln -s "$PWD/docs" mydocs && cp base/report.md mydocs/report.md', 'ln -s $(echo docs) md3 && cp base/report.md md3/report.md']) {
    for (const sh of shellsFor(['bash'], cmd)) assert.equal(overwrites(cmd, report, proj, sh).changed, true, `overwrites the tracked file in real bash: ${cmd}`);
    for (const l of ['mydocs', 'md3']) fs.rmSync(path.join(proj, l), { force: true });
    assert.equal(runHook(cmd).status, 2, `and the hook refuses it: ${cmd}`);
  }
});

test('rule (d) shell options, an allowlist: an option not known to be inert for paths leaves the directory unknown so a later relative write refuses; set -e, -u, -x, -o pipefail and the rest of the inert list pass', () => {
  // the fixture of the third pass: a project whose `lnout` links out to a sibling folder, so a physical `cd lnout; cd ..`
  // lands in the project's parent while the lexical fold lands in the project
  const B = outsideDir();
  const na = trackedProjectAt(B, 'notes-api');
  fs.mkdirSync(path.join(B, 'scratch'));
  fs.symlinkSync('../scratch', path.join(na, 'lnout'));
  const naReport = path.join(na, 'docs', 'report.md');
  try {
    const physical = 'cd lnout; cd ..; cp notes-api/base/report.md notes-api/docs/report.md';
    const OPTION = /sets a shell option that may make the shell resolve paths physically/;
    const UNKNOWN = /the directory it is relative to is not known/;
    for (const pre of ['set -o chaselinks', 'set -o chasedots', 'set -o CHASE_LINKS', 'set -P', 'set -w', 'set -o physical', 'setopt chaselinks', 'setopt chase_links', 'setopt chasedots', 'unsetopt chaselinks', 'setopt -w', 'shopt -s physical']) {
      const reason = evaluate(payload(`${pre}; ${physical}`, na));
      assert.ok(reason && UNKNOWN.test(reason) && OPTION.test(reason) && /physically/.test(reason), `a physical-resolution option refuses the later relative write: ${pre}: ${reason}`);
      assert.ok(reason.includes(pre.split(' ').slice(0, 2).join(' ')), `the refusal names the construct: ${pre}`);
      assert.ok(!/\u2014/.test(reason) && !ROMP_NOUNS.test(reason.split(B).join('<b>')), 'no em dash, no romp noun');
    }
    // any option NOT on the inert list, whether it touches paths or the guard just does not know it, leaves the directory unknown
    for (const pre of ['shopt -s globstar', 'shopt -s nullglob', 'shopt -s dotglob', 'shopt -s extglob', 'shopt -s autocd', 'shopt -s cdable_vars', 'shopt -s expand_aliases', 'shopt -s lastpipe', 'shopt -s nocaseglob', 'set -o posix', 'set -B', 'set -o frobnicate', 'set -Z', 'setopt extendedglob', 'setopt nullglob', 'setopt autocd', 'setopt magicequalsubst', 'setopt rcquotes', 'setopt banghist', 'setopt frobnicate', 'set -o "$OPT"', 'setopt $OPTS',
      // the fifth commit (2026-09-19): the eleven the fourth pass found on the lists against the rule, and what the criterion took off with them
      'set -f', 'set -o noglob', 'setopt noglob', 'setopt nomatch', 'setopt NO_NOMATCH', 'setopt nonomatch', 'setopt badpattern', 'setopt numericglobsort', 'setopt markdirs', 'setopt cdsilent', 'setopt pushdsilent', 'setopt pushdignoredups', 'setopt pushdminus', 'shopt -s extquote',
      'set -k', 'set -o keyword', 'set -E', 'set -H', 'set -o histexpand', 'set -F', 'set -y', 'setopt shwordsplit', 'setopt ksharrays', 'setopt histsubstpattern', 'setopt correctall', 'setopt shortloops', 'shopt -s nocasematch', 'shopt -s patsub_replacement', 'shopt -s compat31', 'shopt -s assoc_expand_once', 'shopt -s noexpand_translation']) {
      const reason = evaluate(payload(`${pre}; cp base/report.md docs/other.md`));
      assert.ok(reason && UNKNOWN.test(reason) && OPTION.test(reason), `an option off the inert list refuses the later relative write: ${pre}: ${reason}`);
    }
    // the inert list: each passes, the later untracked relative write allowed and the tracked one refused by name
    const inert = [
      'set -e', 'set -u', 'set -x', 'set -v', 'set -n', 'set -C', 'set -a', 'set -m', 'set -b', 'set -h', 'set -t',
      'set +e', 'set -ex', 'set -eu', 'set -euo pipefail', 'set -o pipefail', 'set -o errexit', 'set -o nounset', 'set -o xtrace', 'set -o verbose', 'set -o noclobber',
      'set -o errexit -o nounset', 'set +o xtrace', 'set -o pipe_fail', 'set -o', 'set -- a b', 'set -e -- x y', 'set x y', 'set -',
      'shopt -s histappend', 'shopt -s checkwinsize', 'shopt -u xpg_echo', 'shopt -s inherit_errexit', 'shopt -so pipefail', 'shopt -q globstar', 'shopt -p', 'shopt', 'shopt globstar',
      'setopt errexit', 'setopt ERR_EXIT', 'setopt pipefail', 'setopt noclobber', 'setopt -e', 'unsetopt xtrace', 'unsetopt beep', 'setopt histignorespace', 'setopt promptsubst', 'setopt',
    ];
    for (const pre of inert) {
      assert.equal(evaluate(payload(`${pre}; cp base/report.md docs/other.md`)), null, `an inert option passes and the untracked relative write is allowed: ${pre}`);
    }
    for (const pre of ['set -e', 'set -euo pipefail', 'set -x', 'shopt -s histappend', 'setopt errexit']) {
      assert.match(evaluate(payload(`${pre}; cp base/report.md docs/report.md`)), /^Track-changes is ON for /, `after an inert option the tracked write is refused by name: ${pre}`);
    }
    // an absolute target after an option off the list keeps its verdict: the directory is what is unknown, not the path
    assert.equal(evaluate(payload(`shopt -s globstar; cp ${proj}/base/report.md ${proj}/docs/other.md`)), null, 'an absolute untracked target after a non-inert option is allowed');
    assert.match(evaluate(payload(`set -o chaselinks; cp ${proj}/base/report.md ${proj}/docs/report.md`)), /^Track-changes is ON for /, 'an absolute tracked target after it is refused by name');
    // and from a cwd in no project the relative write after such an option is dropped, as every unreadable word is
    fs.writeFileSync(path.join(B, 'scratch', 'a.md'), 'a\n');
    assert.equal(evaluate(payload('shopt -s globstar; cp a.md b.md', path.join(B, 'scratch'))), null, 'from a cwd in no project the later relative write is dropped');
    // real zsh: `set -o chaselinks` makes `cd lnout; cd ..` land in the parent and the copy on the tracked file; the hook refuses it
    for (const zsh of shellsFor(['zsh'], 'set -o chaselinks in real zsh')) assert.equal(overwrites(`set -o chaselinks; ${physical}`, naReport, na, zsh).changed, true, 'set -o chaselinks carries the copy onto the tracked file in real zsh');
    assert.equal(runHook(`set -o chaselinks; ${physical}`, na).status, 2, 'and the hook refuses it');
    assert.equal(fs.readFileSync(naReport, 'utf8'), 'tracked prose\n');
  } finally { fs.rmSync(B, { recursive: true, force: true }); }
});

test('rule (e) any-depth parent prefix: a literal head that is a proper ancestor of a tracked root at any depth refuses when a non-numeric expansion follows, naming the projects beneath; the grandparent and two-segment cases', () => {
  const R = outsideDir();
  const na = trackedProjectAt(R, path.join('f', 'notes-api'));
  const deep = trackedProjectAt(R, path.join('g', 'h', 'web'));
  const cwd = path.join(R, 'scratch', 'sub');
  fs.mkdirSync(cwd, { recursive: true });
  fs.mkdirSync(path.join(R, 'empty', 'dir'), { recursive: true });
  fs.writeFileSync(path.join(R, 'src.md'), 'src\n');
  fs.symlinkSync(na, path.join(R, 'lnproj'));
  try {
    const refused = [
      [`cp ${R}/src.md ../../$x/docs/report.md`, cwd, na],                       // the third pass, #201: x spells f/notes-api
      [`cp ${R}/src.md ../../$x/notes-api/docs/report.md`, cwd, na],             // #202: x spells f
      [`cp ${R}/src.md ../../f/$x/docs/report.md`, cwd, na],                     // the direct child, as round 4 read it
      [`printf poison > ${R}/$x/docs/report.md`, cwd, na],                        // an absolute head, the grandparent
      [`printf poison > ${R}/g/$x/docs/report.md`, cwd, deep],                    // the great-grandparent's child, three levels
      [`cp ${R}/src.md ../../$x`, cwd, na],                                       // the expansion spells the whole rest
      [`printf poison > ${R}/n$x/docs/report.md`, cwd, null],                     // a literal head `n`: notes-api is under f, not a direct child, so the head filters the first segment only
    ];
    for (const [cmd, at, root] of refused) {
      const reason = evaluate(payload(cmd, at));
      if (root === null) { assert.equal(reason, null, `the literal head filters the first segment, and from a cwd in no project the opaque expansion keeps the cwd rule (B2 as ruled: the opaque-head refusal is not built): ${cmd}`); continue; }
      assert.ok(reason && reason.includes('sits above the tracked project') && reason.includes(root), `class E at any depth names the project beneath: ${cmd}: ${reason}`);
      assert.ok(!/\u2014/.test(reason) && !ROMP_NOUNS.test(reason.split(R).join('<r>')), 'no em dash, no romp noun');
    }
    const both = evaluate(payload(`printf poison > ${R}/$x/docs/report.md`, cwd));
    assert.ok(both.includes(na) && both.includes(deep) && both.includes(path.join(R, 'lnproj')), `every root beneath is named, a link to one included: ${both}`);
    // the twins: a numeric-only name, a literal name, and a folder with no project beneath (not class E; from a cwd in no
    // project the opaque expansion after it keeps the cwd rule and is allowed, B2 as ruled, the residual the four surfaces
    // state with its boundary) are allowed, opaque or with the name set to a plain string first (the resolved path judged)
    for (const cmd of [`cp ${R}/src.md ${R}/empty/$x.log`, `cp ${R}/src.md ../../empty/$x/report.md`, `printf x > ${R}/scratch/$x.log`]) {
      assert.equal(evaluate(payload(cmd, cwd)), null, `no tracked root under the head: allowed from a cwd in no project: ${cmd}`);
      assert.equal(evaluate(payload(`x=plain; ${cmd}`, cwd)), null, `with the name set to a plain string the resolved path is allowed: ${cmd}`);
    }
    assert.equal(evaluate(payload(`printf x > ../../$$.log`, cwd)), null, 'a numeric-only expansion is not class E');
    assert.equal(evaluate(payload(`printf x > ../../plain.log`, cwd)), null, 'a literal name in the grandparent is allowed');
    // real bash: the two-segment expansion reaches the root one level down and overwrites the tracked file; the hook refuses it
    for (const sh of shellsFor(['bash'], 'the two-segment expansion in real bash')) assert.equal(overwrites(`x=f/notes-api; cp ${R}/src.md ../../$x/docs/report.md`, path.join(na, 'docs', 'report.md'), cwd, sh).changed, true, 'the two-segment expansion overwrites the tracked file in real bash');
    assert.equal(runHook(`cp ${R}/src.md ../../$x/docs/report.md`, cwd).status, 2, 'and the hook refuses it');
  } finally { fs.rmSync(R, { recursive: true, force: true }); }
});

test('rule (f) unknown option refuses everywhere: cp --targ refuses direct, wrapped and in a chain, from a cwd in no project when an operand sits in a tracked project, and the mutation recorders mark every candidate operand', () => {
  const R = outsideDir();
  try {
    const OPTION = /carries the option --targ/;
    for (const cmd of ['cp --targ docs base/report.md', 'nice cp --targ docs base/report.md', 'true && cp --targ docs base/report.md', 'cp --targ docs base/report.md; echo done', "sh -c 'cp --targ docs base/report.md'", 'flock -x . -c "cp --targ docs base/report.md"', 'mv --targ docs base/report.md', 'ln --targ docs base/report.md', 'install --targ docs base/report.md', 'cp --targ=docs base/report.md', 'cp -Q base/report.md docs/report.md']) {
      const reason = evaluate(payload(cmd));
      assert.ok(reason && /carries the option (--targ|-Q)/.test(reason) && reason.includes(proj), `an unknown or abbreviated option refuses on every path: ${cmd}: ${reason}`);
    }
    // the third pass, #179: from a cwd in no project, with absolute operands inside the project (the option leaves them
    // unplaced, so each is judged by its own project)
    const abs = `cp --targ ${proj}/docs ${proj}/base/report.md`;
    const reason = evaluate(payload(abs, R));
    assert.ok(reason && OPTION.test(reason) && reason.includes(proj), `an unknown option beside an operand inside the project refuses from a cwd in none: ${reason}`);
    assert.ok(/carries the option --targ/.test(evaluate(payload(`cp --targ=${proj}/docs ${R}/a.md`, R)) || ''), 'the =value of a long option is a candidate too');
    fs.writeFileSync(path.join(R, 'a.md'), 'a\n');
    assert.equal(evaluate(payload(`cp --targ ${R}/a.md ${R}/b.md`, R)), null, 'an unknown option with every operand outside every project is dropped');
    assert.equal(evaluate(payload('cp --frobnicate base/report.md docs/report.md', R)), null, 'relative operands from a cwd in no project resolve outside: dropped, as before');
    // the mutation recorders: an unknown option on mv, ln or cp -l marks every candidate operand, so a later write under one refuses
    const later = extractWriteTargets('mv --targ docs d2; echo x > docs/x.md', proj).unresolved;
    assert.ok(later.some((u) => u.why && u.why.kind === 'mutated' && u.why.verb === 'mv' && u.raw === 'docs/x.md'), `the later write under a candidate is unreadable: ${JSON.stringify(later.map((u) => [u.raw, u.why]))}`);
    const linked = extractWriteTargets('ln -s --targ docs md; echo x > docs/x.md', proj).unresolved;
    assert.ok(linked.some((u) => u.why && u.why.kind === 'mutated' && u.why.verb === 'ln'), 'the symlink recorder yields to the mutation recorder on an unknown option');
    assert.ok(!extractWriteTargets('mv -f docs d2; echo x > base/x.md', proj).unresolved.some((u) => u.why && u.why.kind === 'mutated'), 'a known option marks the operands it places, not a write elsewhere');
    // real bash: the abbreviation resolves to --target-directory and the copy lands on the tracked file; the hook refuses it
    for (const sh of shellsFor(['bash'], 'cp --targ in real bash')) assert.equal(overwrites(abs, report, R, sh).changed, true, 'cp --targ overwrites the tracked file in real bash from a cwd in no project');
    assert.equal(runHook(abs, R).status, 2, 'and the hook refuses it');
    assert.equal(fs.readFileSync(report, 'utf8'), 'The api session cut tail latency by 40%.\n');
  } finally { fs.rmSync(R, { recursive: true, force: true }); }
});

test('the third pass also closed chdir (a cd the guard cannot know) and link (a hard-link maker): each pinned both ways', () => {
  fs.writeFileSync(path.join(proj, 'notes', 'n1.md'), 'a tracked note\n');
  const r1 = evaluate(payload('chdir docs; cp ../base/report.md report.md'));
  assert.ok(r1 && /an earlier `chdir` moves the shell in zsh and dash and fails in bash/.test(r1) && /the directory it is relative to is not known/.test(r1), `chdir leaves the directory unknown: ${r1}`);
  assert.match(evaluate(payload('chdir docs; cp ../base/report.md ' + report)), /^Track-changes is ON for /, 'an absolute target after chdir keeps its verdict');
  assert.equal(evaluate(payload('chdir docs; ls')), null, 'a read after chdir is a read');
  for (const zsh of shellsFor(['zsh'], 'chdir in real zsh')) assert.equal(overwrites('chdir docs; cp ../base/report.md report.md', report, proj, zsh).changed, true, 'chdir moves the shell in real zsh and the copy lands on the tracked file');
  assert.equal(runHook('chdir docs; cp ../base/report.md report.md').status, 2);
  const r2 = evaluate(payload('link docs/report.md hardL.md && cp base/report.md hardL.md'));
  assert.ok(r2 && /an earlier `link` in the same command linked /.test(r2), `link is a family-3 mutation: ${r2}`);
  assert.match(evaluate(payload('link base/report.md notes/n2.md')), /^Track-changes is ON for .*notes\/n2\.md/, 'the link name is a write target');
  assert.equal(evaluate(payload('link base/report.md scratch.md && echo x > docs/other.md')), null, 'a link clear of tracked files, then an untracked write: allowed');
  for (const sh of shellsFor(['bash'], 'coreutils link in real bash')) assert.equal(overwrites('link docs/report.md hardL.md && cp base/report.md hardL.md', report, proj, sh).changed, true, 'the hard link carries the copy onto the tracked file in real bash');
  fs.rmSync(path.join(proj, 'hardL.md'), { force: true });
  assert.equal(runHook('link docs/report.md hardL.md && cp base/report.md hardL.md').status, 2);
});


// ── the fifth commit (2026-09-19): the fourth pass's misses closed as rules on visible constructs ──
//
// The fourth pass (three attackers and the literal-dollar matrix, run as a process at 50e85deec) found six misses and
// two boundary questions the reviewer ruled on. Each is pinned here in both directions with a real shell run: M6 (the
// remedy line survives a paste), M1 (a variable name the shell fills in), M2 (zsh's clobber-override redirections), M3
// (a link made before a numeric segment), M4 (an interpreter's literal path holding a dollar; a template path refuses),
// M5 (the inert lists carry their criterion) and B1 (an alias puts the project its source lies in in play).

// A word for the guard's lexer and the shells alike: single-quoted, a single quote inside it closed, escaped and reopened.
const sq = (s) => `'${s.replace(/'/g, `'\\''`)}'`;

test('M6 the remedy line survives a paste: the --file argument is single-quoted, so a path holding a dollar, a brace, a backtick or a quote reaches track-edit byte for byte through real bash and real zsh', () => {
  const stubDir = outsideDir();
  const home = outsideDir();
  try {
    // a stub `node` that prints its argv NUL-separated, first on PATH: the pasted line runs it in place of the CLI
    fs.writeFileSync(path.join(stubDir, 'node'), '#!/bin/sh\nfor a in "$@"; do printf "%s\\0" "$a"; done\n', { mode: 0o755 });
    const names = ['a$b.md', 'a$abc.md', 'a${x}.md', 'a`b.md', 'a"b.md', "a'b.md", "p$'q.md", 'a b$$.md'];
    for (const n of names) {
      const file = path.join(proj, 'notes', n);
      fs.writeFileSync(file, 'x\n');
      const reason = evaluate(payload(`cp base/report.md ${sq(path.join('notes', n))}`));
      assert.ok(reason && reason.startsWith(`Track-changes is ON for ${file},`), `refused by name: ${n}: ${reason}`);
      const line = reason.split('\n').find((l) => /track-edit\.mjs --file /.test(l));
      assert.ok(line && !line.includes('--file "'), `the --file argument is not double-quoted: ${line}`);
      for (const [shell, argv] of [['bash', ['--norc', '--noprofile', '-c', line]], ['zsh', ['-f', '-c', line]]].filter(([sh]) => shellsFor([sh], 'the remedy paste').length)) {
        const r = spawnSync(shell, argv, { encoding: 'utf8', env: { PATH: `${stubDir}:${process.env.PATH}`, HOME: home } });
        assert.equal(r.status, 0, `${shell} ran the pasted line: ${r.stderr}`);
        const args = r.stdout.split('\0');
        assert.equal(args[0], path.join(home, '.claude', 'hooks', 'track-edit.mjs'), `${shell}: the CLI path, ~ expanded`);
        assert.equal(args[1], '--file');
        assert.equal(args[2], file, `${shell} hands track-edit the intended path byte for byte: ${n}`);
        assert.deepEqual(args.slice(3, 7), ['--old', '<exact unique text>', '--new', '<replacement>'], `${shell}: the placeholders survive too`);
      }
    }
    // the generic remedy's placeholder is single-quoted too, so every refusal reads the same way
    const generic = evaluate(payload('cp base/report.md "$DST"'));
    assert.ok(generic.includes("--file '<the file>' --old '<exact unique text>' --new '<replacement>'"), generic);
  } finally { fs.rmSync(stubDir, { recursive: true, force: true }); fs.rmSync(home, { recursive: true, force: true }); }
});

test('M1 a variable name the shell fills in: an assignment, declaration, nameref, export, typeset, local, readonly, read, mapfile, getopts, unset, printf -v, let or (( )) whose NAME operand carries an expansion makes $HOME and ~ unreadable and a bare cd unknown; a literal name or a read-only twin passes; real bash and zsh overwrite through it', () => {
  const n1 = path.join(proj, 'notes', 'n1.md');
  fs.writeFileSync(n1, 'a tracked note\n');
  const ASSEMBLED = /takes a variable name the shell fills in when it runs/;
  const forms = [
    `h=HO; m=ME; export \${h}\${m}=${proj}/notes; printf poison > "$HOME/n1.md"`,           // the fourth pass's five (attack 1, NEW-1)
    `h=HO; m=ME; declare -n r=\${h}\${m}; r=${proj}/notes; printf poison > "$HOME/n1.md"`,
    `h=HO; m=ME; printf -v "\${h}\${m}" %s ${proj}/notes; printf poison > "$HOME/n1.md"`,
    `h=HO; m=ME; typeset \${h}\${m}=${proj}/notes; printf poison > "$HOME/n1.md"`,
    `h=HO; m=ME; read \${h}\${m} <<< ${proj}/notes; printf poison > "$HOME/n1.md"`,
    `export "$(printf 'HOME=${proj}/notes')"; printf poison > $HOME/n1.md`,                  // the matrix's three (rows 2842 to 2844)
    `declare "$(printf 'HOME=${proj}/notes')"; printf poison > ~/n1.md`,
    `read -r "$(printf HOME)" <<< ${proj}/notes; printf poison > $HOME/n1.md`,
    `h=HO; m=ME; local \${h}\${m}=${proj}/notes; printf poison > ~/n1.md`,                  // the rest of the construct's family
    `h=HO; m=ME; readonly \${h}\${m}=${proj}/notes; printf poison > ~/n1.md`,
    `h=HO; m=ME; unset \${h}\${m}; printf poison > "$HOME/n1.md"`,
    `h=HO; m=ME; (( \${h}\${m} = 5 )); printf poison > ~/n1.md`,
    `h=HO; m=ME; let "\${h}\${m}=5"; printf poison > ~/n1.md`,
    `h=HO; m=ME; mapfile -t \${h}\${m} <<< ${proj}/notes; printf poison > ~/n1.md`,
    `h=HO; m=ME; getopts a \${h}\${m}; printf poison > ~/n1.md`,
    `h=HO; m=ME; read -a \${h}\${m} <<< ${proj}/notes; printf poison > ~/n1.md`,
    `h=HO; m=ME; command export \${h}\${m}=${proj}/notes; printf poison > ~/n1.md`,
    `h=HO; m=ME; printf -v\${h}\${m} %s ${proj}/notes; printf poison > ~/n1.md`,
    `export "$X"; printf poison > $HOME/n1.md`,                                                 // the matrix's adverse row 2845: a word the environment fills in
  ];
  for (const cmd of forms) {
    const reason = evaluate(payload(cmd));
    assert.ok(reason && ASSEMBLED.test(reason) && reason.includes(proj) && reason.includes('may be HOME'), `a name the shell fills in refuses the home write: ${cmd}: ${reason}`);
    assert.ok(reason.includes('Spell the path out'), 'the remedy');
    assert.ok(!/\u2014/.test(reason) && !ROMP_NOUNS.test(reason.split(proj).join('<p>')), 'no em dash, no romp noun');
  }
  // a bare `cd` or a `cd ~` after such a construct leaves the directory unknown, so a later relative write refuses
  for (const cmd of [`h=HO; m=ME; export \${h}\${m}=${proj}/notes; cd; printf poison > n1.md`, `h=HO; m=ME; typeset \${h}\${m}=${proj}/notes; cd ~; printf poison > n1.md`]) {
    const reason = evaluate(payload(cmd));
    assert.ok(reason && /the directory it is relative to is not known/.test(reason) && ASSEMBLED.test(reason), `a cd through HOME after the construct: ${cmd}: ${reason}`);
  }
  // the twins: a literal name other than HOME, and a read-only use of the assembled text, keep the home the guard read
  const home = process.env.HOME;
  const out = outsideDir();
  process.env.HOME = out;
  try {
    for (const cmd of ['h=HO; m=ME; echo ${h}${m}; printf x > ~/seed.md', 'printf "%s" "$HOME"; printf x > "$HOME/seed.md"', 'export FOO="$BAR"; printf x > ~/seed.md', 'h=HO; m=ME; export FOO="${h}${m}"; printf x > ~/seed.md',
      'declare -n r=foo; r=1; printf x > ~/seed.md', 'read -p "$msg" ans <<< y; printf x > ~/seed.md', 'printf -v var "$x"; printf x > ~/seed.md', 'mapfile -d "$d" arr < /dev/null; printf x > ~/seed.md',
      '(( n = $n + 1 )); printf x > ~/seed.md', 'let "i = $i + 1"; printf x > ~/seed.md', '(( $x == 1 )); printf x > ~/seed.md', 'unset FOO; printf x > ~/seed.md', 'getopts "$OPTS" opt "$@"; printf x > ~/seed.md', 'local -n r=other; printf x > ~/seed.md']) {
      assert.equal(evaluate(payload(cmd)), null, `a literal name or a read-only twin keeps the home the guard read: ${cmd}`);
    }
  } finally { process.env.HOME = home; fs.rmSync(out, { recursive: true, force: true }); }
  assert.equal(evaluate(payload('h=HO; m=ME; export ${h}${m}=/x; printf x > docs/other.md')), null, 'the construct with no home write changes nothing');
  // real shells: the assembled name reassigns HOME and the write lands on the tracked note; the hook refuses each
  const bashForms = [forms[0], forms[1], forms[2], forms[3], forms[4], forms[5], forms[7]];
  for (const cmd of bashForms) {
    for (const sh of shellsFor(['bash'], cmd)) assert.equal(overwrites(cmd, n1, proj, sh).changed, true, `overwrites the tracked note in real bash: ${cmd}`);
    assert.equal(runHook(cmd).status, 2, `and the hook refuses it: ${cmd}`);
  }
  for (const zsh of shellsFor(['zsh'], 'the HOME assignment forms in real zsh')) for (const cmd of [forms[0], forms[2], forms[3], forms[4]]) {
    const ov = overwrites(cmd, n1, proj, zsh);
    assert.equal(ov.changed, true, `overwrites the tracked note in real zsh: ${cmd}`);
  }
  assert.equal(fs.readFileSync(n1, 'utf8'), 'a tracked note\n');
});

test("M2 zsh's clobber-override redirections: >! >>! &>! &>>! >&! >>&! and their | twins, spaced or glued, and >>& are write redirections under their own operator, judged in both shells' readings; real zsh overwrites, real bash writes a file named ! or refuses the syntax, and the hook refuses each", () => {
  fs.writeFileSync(path.join(proj, 'notes', 'n1.md'), 'a tracked note\n');
  const ops = ['>!', '>>!', '&>!', '&>>!', '>&!', '>>&', '>>&!', '>>|', '&>|', '&>>|', '>&|', '>>&|'];
  for (const op of ops) {
    const { segments } = lex(`echo poison ${op} docs/report.md`);
    const reds = segments[0].redirects;
    assert.ok(reds.some((r) => r.op === op && r.target.text === 'docs/report.md' && r.target.literal), `${op}: the file after the operator is a literal redirection target under ${op}: ${JSON.stringify(reds.map((r) => [r.op, r.target.text]))}`);
    if (op.endsWith('!')) assert.ok(reds.some((r) => r.op === op && r.target.text === '!'), `${op} spaced: bash's reading, a file named !, is recorded too`);
    assert.deepEqual(segments[0].words.map((w) => w.text), ['echo', 'poison'], `${op}: the file is not an argument`);
    const reason = evaluate(payload(`echo poison ${op} docs/report.md`));
    assert.ok(reason && reason.includes(report) && reason.includes(`its ${op} redirection would write the file`), `${op} onto the tracked file is refused naming the operator: ${reason}`);
    assert.equal(evaluate(payload(`echo poison ${op} docs/other.md`)), null, `${op} onto an untracked file passes`);
    assert.ok(evaluate(payload(`echo poison ${op} notes/n1.md`)).includes(path.join(proj, 'notes', 'n1.md')), `${op} onto a note tracked by folder`);
  }
  // glued: zsh writes docs/report.md and bash a file named !docs/report.md; both are recorded and the tracked one refuses
  assert.deepEqual(lex('echo poison >!docs/report.md').segments[0].redirects.map((r) => [r.op, r.target.text]).sort(), [['>!', '!docs/report.md'], ['>!', 'docs/report.md']]);
  assert.ok(evaluate(payload('echo poison >!docs/report.md')).includes(report), 'the glued form onto the tracked file');
  assert.ok(evaluate(payload('echo poison >>!docs/report.md')).includes(report));
  assert.ok(evaluate(payload('echo poison {fd}>! docs/report.md')).includes(report), 'the named-descriptor form');
  assert.equal(evaluate(payload('echo poison >!docs/other.md')), null, 'glued onto an untracked file passes');
  // bash's reading is judged as well: a project that tracks a file named `!` refuses `>! <untracked>` (bash writes `!`)
  fs.writeFileSync(path.join(proj, '!'), 'bang\n');
  fs.writeFileSync(path.join(proj, '.trackchanges', 'config.json'), JSON.stringify({ v: 2, tracked: ['docs/report.md', 'notes/', 'figs/plot.png', '!'] }));
  const bang = evaluate(payload('echo poison >! docs/other.md'));
  assert.ok(bang && bang.includes(path.join(proj, '!')), `bash's reading, a file named !, is judged: ${bang}`);
  for (const sh of shellsFor(['bash'], 'the file named ! in real bash')) assert.equal(overwrites('echo poison >! docs/other.md', path.join(proj, '!'), proj, sh).changed, true, 'real bash writes the file named !');
  fs.writeFileSync(path.join(proj, '.trackchanges', 'config.json'), JSON.stringify({ v: 2, tracked: ['docs/report.md', 'notes/', 'figs/plot.png'] }));
  fs.rmSync(path.join(proj, '!'), { force: true });
  // real zsh: each form writes (or appends to) the tracked file; real bash does not touch it; the hook refuses each
  for (const cmd of ['echo poison >! docs/report.md', 'echo poison >!docs/report.md', 'echo poison >>! docs/report.md', 'echo poison &>! docs/report.md', 'echo poison >&! docs/report.md', 'echo poison >>| docs/report.md', 'echo poison >&| docs/report.md', 'echo poison &>| docs/report.md', 'echo poison >>& docs/report.md', 'echo poison {fd}>! docs/report.md']) {
    for (const zsh of shellsFor(['zsh'], `the clobber form ${cmd} in real zsh`)) assert.equal(overwrites(cmd, report, proj, zsh).changed, true, `real zsh writes the tracked file: ${cmd}`);
    for (const sh of shellsFor(['bash'], `the clobber form ${cmd} in real bash`)) assert.equal(overwrites(cmd, report, proj, sh).changed, false, `real bash does not write the tracked file (a file named !, or a syntax error): ${cmd}`);
    fs.rmSync(path.join(proj, '!'), { force: true });
    assert.equal(runHook(cmd).status, 2, `the hook refuses: ${cmd}`);
  }
  // the twin the fourth pass named: `>|`, the POSIX spelling, keeps its verdict, and a bare word `!` after a spaced `>` is not a redirection
  assert.ok(evaluate(payload('echo poison >| docs/report.md')).includes(report));
  assert.deepEqual(lex('echo poison > ! docs/report.md').segments[0].redirects.map((r) => r.target.text), ['!'], 'a spaced bare ! is the target word, as both shells read it');
  assert.equal(fs.readFileSync(report, 'utf8'), 'The api session cut tail latency by 40%.\n');
});

test("M3 a link made before a numeric segment: the command's own links are followed into a numeric target's literal directory part, so `ln -s <proj>/notes <out>/d && echo x > <out>/d/x-$$.md` refuses from a cwd in no project and from the tracked cwd; a link pointing outside every project is allowed; a link whose source is not literal refuses with the family-3 reason; real bash lands the write in the tracked folder", () => {
  const out = outsideDir();
  try {
    fs.writeFileSync(path.join(proj, 'notes', 'n1.md'), 'a tracked note\n');
    fs.mkdirSync(path.join(out, 'plain'));
    const cmd = `ln -s ${proj}/notes ${out}/d && echo x > ${out}/d/x-$$.md`;
    for (const [cwd, where] of [[out, 'a cwd in no project'], [proj, 'the tracked cwd']]) {
      const reason = evaluate(payload(cmd, cwd));
      assert.ok(reason && reason.includes(proj) && /is not a literal path/.test(reason), `refused from ${where}, naming the project the link leads into: ${reason}`);
      assert.ok(!/\u2014/.test(reason) && !ROMP_NOUNS.test(reason.split(proj).join('<p>').split(out).join('<o>')), 'no em dash, no romp noun');
    }
    assert.match(evaluate(payload(`ln -s ${proj}/notes ${out}/d && echo x > ${out}/d/x-1.md`, out)), /^Track-changes is ON for /, 'the literal twin, class H, is refused by name');
    assert.match(evaluate(payload(`ln -s ${proj}/notes ${out}/d && echo x > ${out}/d/sub-$$/y.md`, out)), /is a name the shell fills in with a number/, 'a numeric folder under the link too, with the unknown-folder reason');
    for (const cwd of [out, proj]) assert.equal(evaluate(payload(`ln -s ${out}/plain ${out}/d && echo x > ${out}/d/x-$$.md`, cwd)), null, 'a link pointing outside every project: allowed');
    assert.equal(evaluate(payload(`echo x > ${out}/plain/x-$$.md`, out)), null, 'the numeric write with no link: allowed');
    const opaque = evaluate(payload(`ln -s "$SRC" ${out}/d && echo x > ${out}/d/x-$$.md`, out));
    assert.ok(opaque && /an earlier `ln -s` in the same command linked/.test(opaque) && /a source I cannot read/.test(opaque), `a link whose source is not literal refuses with the family-3 reason from a cwd in no project: ${opaque}`);
    assert.ok(opaque.includes('Run the `ln -s` in a command of its own'), 'the remedy');
    // real bash: the link is made and the numeric name lands in the tracked folder, unrecorded; the hook refuses
    for (const sh of shellsFor(['bash'], 'the link then the numeric name in real bash')) {
      const r = spawnSync(sh, ['-c', cmd], { cwd: out, encoding: 'utf8', env: { PATH: process.env.PATH } });
      assert.equal(r.status, 0, r.stderr);
      const landed = fs.readdirSync(path.join(proj, 'notes')).filter((n) => /^x-\d+\.md$/.test(n));
      assert.equal(landed.length, 1, 'the write landed in the tracked folder in real bash');
      fs.rmSync(path.join(out, 'd'), { force: true });
    }
    assert.equal(runHook(cmd, out).status, 2, 'and the hook refuses it');
    assert.equal(runHook(cmd, proj).status, 2);
  } finally { fs.rmSync(out, { recursive: true, force: true }); }
});

test("M4 an interpreter's literal path is judged by its name whatever it holds (a dollar is text), in the eight matrix forms, tracked refused and the untracked twin allowed; a template or format string path refuses as unreadable; a computed path stays out of model; real bash and zsh write the tracked folder through the literal forms and the hook refuses", () => {
  // a project tracking a folder whose name holds a dollar (the matrix's sub-on), beside an untracked twin folder
  for (const d of ['p$abc', 'q$abc']) { fs.mkdirSync(path.join(proj, d)); fs.writeFileSync(path.join(proj, d, 'seed.md'), 'seed\n'); }
  fs.writeFileSync(path.join(proj, '.trackchanges', 'config.json'), JSON.stringify({ v: 2, tracked: ['docs/report.md', 'notes/', 'figs/plot.png', 'p$abc/'] }));
  const forms = (d) => [
    `python3 -c "open('${d}/rep.md','w').write('poison')"`,
    `python3 -c 'open("${d}/rep.md","w").write("poison")'`,
    `python3 -c "from pathlib import Path; Path('${d}/rep.md').write_text('poison')"`,
    `python3 -c "import shutil; shutil.copy('base/report.md','${d}/rep.md')"`,
    `node -e "require('fs').writeFileSync('${d}/rep.md','poison')"`,
    `node -e 'require("fs").writeFileSync("${d}/rep.md","poison")'`,
    `python3 - <<'EOF'\nopen('${d}/rep.md','w').write('poison')\nEOF`,
    `node - <<'EOF'\nrequire('fs').writeFileSync('${d}/rep.md','poison')\nEOF`,
  ];
  const tracked = forms('p\\$abc').map((c, i) => (c.startsWith('python3 -c \'') || c.startsWith('node -e \'') || c.includes('<<') ? forms('p$abc')[i] : c));   // inside double quotes the dollar is escaped for the shell; inside single quotes and a quoted heredoc it is text as spelled
  const untracked = forms('q\\$abc').map((c, i) => (c.startsWith('python3 -c \'') || c.startsWith('node -e \'') || c.includes('<<') ? forms('q$abc')[i] : c));
  assert.equal(tracked.length, 8);
  for (const cmd of tracked) {
    const reason = evaluate(payload(cmd));
    assert.ok(reason && reason.startsWith(`Track-changes is ON for ${path.join(proj, 'p$abc', 'rep.md')},`), `the literal dollar path is refused by name: ${cmd}: ${reason}`);
  }
  for (const cmd of untracked) assert.equal(evaluate(payload(cmd)), null, `the untracked twin is allowed: ${cmd}`);
  // the grammar: the path is kept whatever it holds
  assert.deepEqual(scriptWriteTargets('python', "open('p$abc/rep.md','w')"), ['p$abc/rep.md']);
  assert.deepEqual(scriptWriteTargets('node', "fs.writeFileSync('p$abc/{x}.md', 'y')"), ['p$abc/{x}.md'], 'a brace in a plain string is text too');
  // a template or format string is a path the interpreter fills in: unreadable, refused while the project is in play
  const TEMPLATE = /a path built from a template or format string/;
  for (const cmd of [`python3 -c "d='p\\$abc'; open(f'{d}/rep.md','w').write('poison')"`, `python3 -c "open('{}/rep.md'.format('p\\$abc'),'w')"`, `python3 -c "open('%s/rep.md' % 'p\\$abc','w')"`, `python3 -c "from pathlib import Path; Path(f'{d}/rep.md').write_text('x')"`,
    `node -e 'const d="p$abc"; require("fs").writeFileSync(\`\${d}/rep.md\`,"poison")'`, `node - <<'EOF'\nconst d='p$abc';\nrequire('fs').writeFileSync(\`\${d}/rep.md\`,'poison')\nEOF`, `python3 - <<'EOF'\nd='p$abc'\nopen(f'{d}/rep.md','w').write('poison')\nEOF`]) {
    const reason = evaluate(payload(cmd));
    assert.ok(reason && TEMPLATE.test(reason) && reason.includes(proj), `a template path refuses as unreadable: ${cmd}: ${reason}`);
    assert.ok(reason.includes('Spell the path as a plain string'), 'the remedy');
    assert.ok(!/\u2014/.test(reason) && !ROMP_NOUNS.test(reason.split(proj).join('<p>')), 'no em dash, no romp noun');
  }
  assert.deepEqual(scriptTemplateTargets('python', "open(f'{d}/rep.md','w')"), ["f'{d}/rep.md'"]);
  assert.deepEqual(scriptTemplateTargets('node', 'fs.writeFileSync(`${d}/rep.md`, x)'), ['`${d}/rep.md`']);
  assert.deepEqual(scriptTemplateTargets('node', 'fs.writeFileSync(`plain.md`, x)'), [], 'a template literal with no expression is a plain string');
  assert.deepEqual(scriptWriteTargets('node', 'fs.writeFileSync(`plain.md`, x)'), ['plain.md']);
  // the computed forms stay out of model, by the contract (a name, os.environ, sys.argv, a concatenation)
  const out = outsideDir();
  try {
    // round 5 (regression-1): a concatenation that OPENS with a string literal is a template now (the base refused it, round 4's
    // head let it through); the contract's boundary is a concatenation that does not, a name first
    for (const cmd of [`python3 -c "p='p\\$abc/rep.md'; open(p,'w').write('poison')"`, `python3 -c "import os; open(os.environ['T'],'w')"`, `node -e "require('fs').writeFileSync(process.env.T,'x')"`, `node -e "d='p\\$abc/'; require('fs').writeFileSync(d + 'rep.md','x')"`]) {
      assert.equal(evaluate(payload(cmd)), null, `a computed path is allowed, the contract's boundary: ${cmd}`);
    }
    assert.match(evaluate(payload(`node -e "require('fs').writeFileSync('p\\$abc/' + 'rep.md','x')"`)), /a string literal with more appended to it/, 'a literal-first concatenation is a template, refused (round 5)');
    assert.equal(evaluate(payload(`python3 -c "d='x'; open(f'{d}/rep.md','w')"`, out)), null, 'a template path from a cwd in no project is dropped, as every unreadable word is');
  } finally { fs.rmSync(out, { recursive: true, force: true }); }
  // real shells: the literal forms write the tracked folder (a new file under p$abc/); the hook refuses each
  const rep = path.join(proj, 'p$abc', 'rep.md');
  for (const [i, cmd] of tracked.entries()) {
    for (const shell of shellsFor(i < 2 ? ['bash', 'zsh'] : ['bash'])) {
      const r = spawnSync(shell, ['-c', cmd], { cwd: proj, encoding: 'utf8', env: { PATH: process.env.PATH } });
      assert.equal(r.status, 0, `${shell}: ${cmd}: ${r.stderr}`);
      assert.equal(fs.existsSync(rep) && fs.readFileSync(rep, 'utf8').includes('poison') || fs.readFileSync(rep, 'utf8') === 'an older copy\n', true, `${shell} wrote the tracked folder: ${cmd}`);
      fs.rmSync(rep, { force: true });
    }
    assert.equal(runHook(cmd).status, 2, `and the hook refuses it: ${cmd}`);
  }
  // and the untracked twin runs, writing beside it
  for (const sh of shellsFor(['bash'], 'the untracked twin in real bash')) {
    const q = spawnSync(sh, ['-c', untracked[0]], { cwd: proj, encoding: 'utf8', env: { PATH: process.env.PATH } });
    assert.equal(q.status, 0, q.stderr);
    assert.equal(fs.readFileSync(path.join(proj, 'q$abc', 'rep.md'), 'utf8'), 'poison');
  }
  assert.equal(runHook(untracked[0]).status, 0, 'the hook allows the untracked twin');
});

test("M5 the inert lists carry their criterion: every entry is a real option of a shell on this box with a one-line reason, every letter flips only an option the table holds in bash and in zsh, the options the criterion took off refuse the later relative write while the absolute twin keeps its verdict, and bash's keyword mode is read both ways", () => {
  const norm = (n) => n.toLowerCase().replace(/[_-]/g, '');
  const env = { PATH: process.env.PATH };
  const sh = (shell, cmd) => spawnSync(shell, shell === 'zsh' ? ['-f', '-c', cmd] : ['-c', cmd], { encoding: 'utf8', env });
  const names = (text) => new Map(text.split('\n').map((l) => l.trim().split(/\s+/)).filter((f) => f[0]).map((f) => [norm(f[0]), f[1] || '']));
  // zsh lists an option that is on by default under its `no` spelling (`noevallineno off`), so membership ignores the prefix both ways
  const lists = (m, n) => m.has(n) || m.has('no' + n) || (n.startsWith('no') && m.has(n.slice(2)));
  // round 5: every shell's option list comes through the probe (dash's minter threw a bare TypeError on a runner without dash, and
  // a bash below the floor would have too); a shell the probe declined is null here, reported once, and every consumer below
  // tolerates the null, so the runner's shells are what they judge
  const bashSetO = HAS_SHELL.bash ? names(sh('bash', 'set -o').stdout) : null;
  const bashShopt = HAS_SHELL.bash ? names(sh('bash', 'shopt').stdout) : null;
  const zshSetO = HAS_SHELL.zsh ? names(sh('zsh', 'set -o').stdout) : null;
  const dashSetO = HAS_SHELL.dash ? names(sh('dash', 'set -o').stdout) : null;
  assert.ok((bashSetO == null || bashSetO.size > 20) && (bashShopt == null || bashShopt.size > 40) && (zshSetO == null || zshSetO.size > 150) && (dashSetO == null || dashSetO.size > 10), 'the shells list their options');
  for (const [table, probed] of [[bashSetO, 'bash'], [zshSetO, 'zsh'], [dashSetO, 'dash']]) if (!table) shellsFor([probed], `the inert option names against real ${probed}`);
  // every set -o entry is an option of bash, zsh or dash, every shopt entry one of bash, each with a reason
  for (const [name, why] of Object.entries(INERT_OPTIONS.set)) {
    assert.ok(typeof why === 'string' && why.length >= 10 && !/\u2014/.test(why) && !why.includes('\n'), `${name}: a one-line reason`);
    assert.ok((bashSetO ? lists(bashSetO, norm(name)) : true) || (zshSetO ? lists(zshSetO, norm(name)) : true) || (dashSetO ? lists(dashSetO, norm(name)) : true), `${name}: an option of bash, zsh or dash on this box`);   // a shell the probe declined is taken as the one that has the name (shellsFor said its leg did not run)
  }
  for (const [name, why] of Object.entries(INERT_OPTIONS.shopt)) {
    assert.ok(typeof why === 'string' && why.length >= 10 && !/\u2014/.test(why) && !why.includes('\n'), `${name}: a one-line reason`);
    if (bashShopt) assert.ok(bashShopt.has(norm(name)), `${name}: a shopt option of bash on this box`);
  }
  // the eleven and the criterion's other removals are off the tables
  for (const name of ['noglob', 'nomatch', 'badpattern', 'numericglobsort', 'markdirs', 'cdsilent', 'pushdsilent', 'pushdignoredups', 'pushdminus', 'keyword', 'histexpand', 'shwordsplit', 'ksharrays', 'histsubstpattern', 'correct', 'correctall', 'shortloops', 'localpatterns', 'multibyte']) assert.ok(!(name in INERT_OPTIONS.set), `${name} is off the set -o table`);
  for (const name of ['extquote', 'nocasematch', 'patsubreplacement', 'compat31', 'compat44', 'assocexpandonce', 'noexpandtranslation']) assert.ok(!(name in INERT_OPTIONS.shopt), `${name} is off the shopt table`);
  // every letter: `set -X; set -o` against the baseline names the option the letter flips in each shell, which must be the
  // table's option for that shell and itself on the inert table (a letter that stops the shell, -n and -t, or that a shell
  // rejects, zsh's -b, prints nothing, and the table's word for it is held to the shell's option list)
  const flipped = (shell, L) => {
    // `set -X` against `set +X` (not against the default, which may already be on, as bash's hashall is)
    const on = sh(shell, `set -${L} 2>/dev/null || exit 9; set -o`);
    const off = sh(shell, `set +${L} 2>/dev/null || exit 9; set -o`);
    if (on.status === 9 || off.status === 9 || !on.stdout || !off.stdout) return null;
    const a = names(on.stdout);
    const b = names(off.stdout);
    return [...a].filter(([n, state]) => b.get(n) !== state).map(([n]) => n).sort();
  };
  for (const [L, spec] of Object.entries(INERT_OPTIONS.letters)) {
    assert.ok(typeof spec.why === 'string' && spec.why.length >= 10 && !/\u2014/.test(spec.why), `-${L}: a one-line reason`);
    for (const shell of shellsFor(['bash', 'zsh'])) {
      const want = spec[shell];
      const got = flipped(shell, L);
      if (got == null) { assert.ok(want == null || lists((shell === 'bash' ? bashSetO : zshSetO) || new Map(), norm(want)), `-${L} in ${shell}: the letter stops or is refused by the shell, and the table's option is one the shell lists`); continue; }
      assert.deepEqual(got, want == null ? [] : [norm(want)], `-${L} in ${shell} flips exactly the table's option`);
      if (want != null) assert.ok(norm(want) in INERT_OPTIONS.set, `-${L} in ${shell}: ${want} is itself on the inert table`);
    }
  }
  for (const L of 'fkEHFyPTwBJNDGI') assert.ok(!(L in INERT_OPTIONS.letters), `-${L} is off the letter table`);
  // the options taken off refuse the later relative write (fail closed) and the absolute untracked twin keeps its verdict
  const UNKNOWN = /the directory it is relative to is not known/;
  const OPTION = /sets a shell option that may make the shell resolve paths physically/;
  for (const pre of ['set -f', 'set -o noglob', 'setopt noglob', 'setopt nomatch', 'setopt badpattern', 'setopt numericglobsort', 'setopt markdirs', 'setopt cdsilent', 'setopt pushdsilent', 'setopt pushdignoredups', 'setopt pushdminus', 'shopt -s extquote',
    'set -k', 'set -o keyword', 'set -E', 'set -H', 'set -F', 'set -y', 'setopt ksharrays', 'setopt histsubstpattern', 'shopt -s nocasematch', 'shopt -s patsub_replacement']) {
    const reason = evaluate(payload(`${pre}; cp base/report.md docs/other.md`));
    assert.ok(reason && UNKNOWN.test(reason) && OPTION.test(reason) && reason.includes(pre.split(' ').slice(0, 2).join(' ')), `${pre} refuses the later relative write, naming the construct: ${reason}`);
    assert.equal(evaluate(payload(`${pre}; cp ${proj}/base/report.md ${proj}/docs/other.md`)), null, `${pre}: the absolute untracked twin keeps its verdict`);
    assert.match(evaluate(payload(`${pre}; cp ${proj}/base/report.md ${proj}/docs/report.md`)), /^Track-changes is ON for /, `${pre}: the absolute tracked twin is refused by name`);
  }
  // bash's keyword mode, measured: `set -k` makes a trailing X=1 an assignment, so cp gets two operands and writes the
  // tracked file; the guard reads the operands both ways and refuses; the twin onto an untracked absolute path passes
  const kw = 'set -k; cp base/report.md docs/report.md X=1';
  for (const sh of shellsFor(['bash'], 'set -k in real bash')) {
    assert.equal(overwrites(kw, report, proj, sh).changed, true, 'set -k: real bash writes the tracked file through a cp the guard read as writing nothing');
    assert.equal(overwrites('cp base/report.md docs/report.md X=1', report, proj, sh).changed, false, 'without -k the third operand makes cp fail');
  }
  assert.equal(runHook(kw).status, 2, 'the hook refuses it');
  assert.match(evaluate(payload(`set -k; cp ${proj}/base/report.md ${proj}/docs/report.md X=1`)), /^Track-changes is ON for /, 'the absolute spelling is refused by name under the keyword reading');
  assert.equal(evaluate(payload(`set -k; cp ${proj}/base/report.md ${proj}/docs/other.md X=1`)), null, 'the untracked absolute twin passes');
  assert.equal(evaluate(payload(`set -e; cp ${proj}/base/report.md ${proj}/docs/report.md X=1`)), null, 'without keyword mode the third operand is an operand and cp writes nothing');
});

test('B1 an alias made in the command puts the project its SOURCE lies in in play from any cwd: cp -s, a hard ln, cp -l, link and an ln -s with a substituted source each refuse a write through the alias from a cwd in no project; the twins whose source lies outside every project are allowed; real bash overwrites the tracked note through the alias and the hook refuses', () => {
  const out = outsideDir();
  try {
    const seed = path.join(proj, 'notes', 'seed.md');
    fs.writeFileSync(seed, 'a tracked note\n');
    fs.writeFileSync(path.join(out, 'plain.md'), 'plain\n');
    const rows = [
      [`cp -s ${seed} ${out}/s-alias && printf poison > ${out}/s-alias`, /an earlier `cp -l` in the same command linked/],        // the matrix's rows 2807, 2810, 2811, 2813, 2882, 2910
      [`ln ${seed} ${out}/h3 && printf poison > ${out}/h3`, /an earlier `ln` in the same command linked/],
      [`cp -l ${seed} ${out}/h4 && printf poison > ${out}/h4`, /an earlier `cp -l` in the same command linked/],
      [`cp -s ${seed} ${out}/s-alias; printf poison > ${out}/s-alias`, /an earlier `cp -l` in the same command linked/],
      [`ln -s "$(printf '${proj}/notes')" ${out}/lnk4 && printf poison > ${out}/lnk4/rep.md`, /an earlier `ln -s` in the same command linked .* to a source I cannot read/],
      [`link ${seed} ${out}/h7 && printf poison > ${out}/h7`, /an earlier `link` in the same command linked/],
      [`ln -t ${out} ${seed} && printf poison > ${out}/seed.md`, /an earlier `ln` in the same command linked/],
      [`cp -l ${seed} ${out}/ && cat base/report.md > ${out}/seed.md`, /an earlier `cp -l` in the same command linked/],
    ];
    for (const [cmd, why] of rows) {
      const reason = evaluate(payload(cmd, out));
      assert.ok(reason && why.test(reason), `refused from a cwd in no project: ${cmd}: ${reason}`);
      if (!/cannot read/.test(reason)) assert.ok(reason.includes(proj), `names the project the source lies in: ${reason}`);
      assert.ok(!/\u2014/.test(reason) && !ROMP_NOUNS.test(reason.split(proj).join('<p>').split(out).join('<o>')), 'no em dash, no romp noun');
    }
    // the twins: the source outside every project, the alias outside every project
    for (const cmd of [`cp -s ${out}/plain.md ${out}/s2 && printf poison > ${out}/s2`, `ln ${out}/plain.md ${out}/h5 && printf poison > ${out}/h5`, `cp -l ${out}/plain.md ${out}/h6 && printf poison > ${out}/h6`, `link ${out}/plain.md ${out}/h8 && printf poison > ${out}/h8`, `ln -s ${out} ${out}/lnk5 && printf poison > ${out}/lnk5/rep.md`, `ln -t ${out} ${out}/plain.md && printf poison > ${out}/plain.md`]) {
      assert.equal(evaluate(payload(cmd, out)), null, `a source outside every project: allowed: ${cmd}`);
    }
    assert.equal(evaluate(payload(`cp -s ${seed} ${out}/s-alias && printf poison > ${out}/other.md`, out)), null, 'a write NOT through the alias is judged as ever');
    // the grammar: the record carries the alias and its source
    const u = extractWriteTargets(`cp -s ${seed} ${out}/s-alias && printf poison > ${out}/s-alias`, out).unresolved;
    assert.deepEqual(u.map((x) => [x.why.kind, x.why.alias, x.why.source]), [['mutated', true, seed]]);
    assert.equal(extractWriteTargets(`ln -s "$SRC" ${out}/l && printf poison > ${out}/l/x.md`, out).unresolved[0].why.source, null, 'a source the guard cannot read is recorded as none');
    assert.equal(extractWriteTargets(`rm -f ${out}/x.md && printf poison > ${out}/x.md`, out).unresolved[0].why.alias, false, 'a remove aliases nothing');
    // real bash: the alias carries the write onto the tracked note; the hook refuses
    for (const cmd of [rows[0][0], rows[1][0], rows[2][0], rows[5][0]]) {
      for (const sh of shellsFor(['bash'], cmd)) assert.equal(overwrites(cmd, seed, out, sh).changed, true, `overwrites the tracked note in real bash from a cwd in no project: ${cmd}`);
      for (const a of ['s-alias', 'h3', 'h4', 'h7']) fs.rmSync(path.join(out, a), { force: true });
      assert.equal(runHook(cmd, out).status, 2, `and the hook refuses it: ${cmd}`);
    }
    for (const zsh of shellsFor(['zsh'], 'the alias road in real zsh')) assert.equal(overwrites(rows[0][0], seed, out, zsh).changed, true, 'and in real zsh');
    fs.rmSync(path.join(out, 's-alias'), { force: true });
    assert.equal(fs.readFileSync(seed, 'utf8'), 'a tracked note\n');
  } finally { fs.rmSync(out, { recursive: true, force: true }); }
});


test("B2 as ruled: the values the guard can read are resolved and the real path judged (an in-command plain-string assignment, HOME, PWD, OLDPWD, ~+ and ~-); what stays opaque keeps the verdict the working directory gives it, refused as not literal from the tracked cwd and allowed from a cwd in no project (the residual, stated with its boundary and measured landing); an assignment in a body, after &&, in a subshell, a read, a loop variable, an eval or a function call leaves the name opaque; real bash and zsh overwrite through the resolved value and the hook refuses", () => {
  const out = outsideDir();
  try {
    fs.mkdirSync(path.join(out, 'scratch'));
    fs.mkdirSync(path.join(proj, 'scratch'));
    fs.writeFileSync(path.join(proj, 'notes', 'n1.md'), 'a tracked note\n');
    const BY_NAME = /^Track-changes is ON for /;
    // readable: the resolved path is judged by name, tracked refused and untracked allowed, from a tracked cwd and from one in no project
    for (const [cmd, cwd, want] of [
      ["x='../docs/report.md'; cp base/report.md scratch/$x", proj, BY_NAME],                          // attack 2's row, from the tracked cwd
      [`v='../../${path.basename(proj)}/docs/report.md'; cp ${proj}/base/report.md scratch/$v`, out, BY_NAME],   // and from a cwd in no project beside the project (attack 2's `scratch/$v`)
      [`x='../${path.basename(proj)}/notes'; printf poison > ${out}/$x/rep.md`, out, BY_NAME],                    // the matrix's row 2898: a literal head outside every project, the climb inside the value
      ['x=other.md; echo hi > docs/$x', proj, null],                                                     // resolved to an untracked file: allowed, where before it was refused as not literal
      ['d=docs; cd $d && cp ../base/report.md report.md', proj, BY_NAME],                                // a cd through a resolved name moves the directory
      ['echo x > "$PWD/docs/report.md"', proj, BY_NAME],
      ['cp base/report.md $PWD/scratch/copy.md', proj, null],
      ['cd docs; cp ../base/report.md $OLDPWD/docs/report.md', proj, BY_NAME],
      [`cd ${proj}; cd ${out}; echo poison > ~-/docs/report.md`, out, BY_NAME],                          // attack 1's P11, from a cwd in no project
      [`cd ${out}/scratch && echo x > ~-/scratch/back.log`, proj, null],
      ['echo x > ~+/notes/n2.md', proj, BY_NAME],
      [`a=$HOME/scratch; echo x > $a/h.log`, proj, null],
      [`y=sub; x=$y/deep; mkdir -p ${out}/scratch/$x && echo x > ${out}/scratch/$x/f.log`, out, null],   // a value built from an earlier resolved name
      [`export n=run2; echo x > ${out}/scratch/$n.log`, out, null],
      [`n=run1; echo x > ${out}/scratch/$n.log`, proj, null],                                            // from a tracked cwd too: resolved, outside, allowed
      [`x=a; flock -x . -c "echo x > ${out}/scratch/$x/y"`, out, null],                                  // the outer shell expands the double-quoted name before flock runs it
    ]) {
      const reason = evaluate(payload(cmd, cwd));
      if (want === null) assert.equal(reason, null, `resolved to a path outside every tracked file: allowed: ${cmd}`);
      else assert.ok(reason && want.test(reason), `resolved and judged by name: ${cmd}: ${reason}`);
    }
    // opaque after a literal head (B2 as ruled, the reviewer's option (c), 2026-09-19): the word keeps the verdict the working
    // directory gives it, refused as not literal from the tracked cwd, naming the project (class F and the cwd rule, as before
    // B2), and dropped from a cwd in no project; the allowed rows are run in real bash and zsh from that cwd with the tracked
    // subset fingerprinted after (each lands under <out>/scratch, or fails on a folder that is not there)
    const opaque = [
      `echo x > ${out}/scratch/$name.log`,
      `cp base/report.md ${out}/scratch/$(date +%s).md`,
      `echo x > ${out}/scratch/\${TMPDIR:-x}/a.log`,
      `echo x > ${out}/scratch/\`date +%s\`.log`,
      `if true; then n=a; fi; echo x > ${out}/scratch/$n.log`,                // an assignment in a body may not run
      `false && n=a; echo x > ${out}/scratch/$n.log`,                         // after && it may not run
      `(n=a); echo x > ${out}/scratch/$n.log`,                                // in a subshell it does not persist
      `n=a | cat; echo x > ${out}/scratch/$n.log`,
      `read n <<< a; echo x > ${out}/scratch/$n.log`,
      `for f in a b; do echo x > ${out}/scratch/$f.log; done`,
      `n=a; eval 'n=b'; echo x > ${out}/scratch/$n.log`,                     // an eval may reassign anything
      `f() { n=b; }; n=a; f; echo x > ${out}/scratch/$n.log`,                // a call of a function the command defines may too
      `n=a; . ./rc; echo x > ${out}/scratch/$n.log`,
      `n=$(pwd); echo x > ${out}/scratch/$n.log`,                             // a value the guard cannot read
      `n='a b'; echo x > "${out}/scratch/$n.log"`,                            // a value the shell would split
      `n='*'; echo x > ${out}/scratch/$n.log`,                                // a value the shell would match
      `n=a; n+=b; echo x > ${out}/scratch/$n.log`,
      `n=a; unset n; echo x > ${out}/scratch/$n.log`,
      `n=run1; sh -c 'echo x > ${out}/scratch/$n.log'`,                        // the inner shell sees the environment alone
      `echo x > scratch/$name.log`,                                            // a relative head too
    ];
    const fingerprint = () => `${shaOf(report)} ${fs.readdirSync(path.join(proj, 'notes')).sort().join(',')}`;
    const before = fingerprint();
    for (const cmd of opaque) {
      const fromProj = evaluate(payload(cmd, proj));
      assert.ok(fromProj && NOT_LITERAL.test(fromProj) && fromProj.includes(proj), `from the tracked cwd an opaque expansion is refused as not literal, naming the project: ${cmd}: ${fromProj}`);
      assert.ok(fromProj.includes('track-edit') && !/\u2014/.test(fromProj) && !ROMP_NOUNS.test(fromProj.split(proj).join('<p>').split(out).join('<o>')), 'the remedy, no em dash, no romp noun');
      assert.equal(evaluate(payload(cmd, out)), null, `from a cwd in no project the same word keeps the cwd rule and is allowed: ${cmd}`);
      for (const shell of shellsFor(['bash', 'zsh'])) spawnSync(shell, ['-c', cmd], { cwd: out, encoding: 'utf8', env: { PATH: process.env.PATH } });
    }
    assert.equal(fingerprint(), before, 'the allowed opaque rows, run from the cwd in no project, left the tracked subset as it was');
    // the twins: a numeric name, a literal name, and a word with NO literal head from a cwd in no project (the contract's stated residual)
    for (const cmd of [`echo x > ${out}/scratch/x-$$.log`, `echo x > ${out}/scratch/plain.log`, 'echo x > $name.log', 'echo x > x-$name.log', 'cp base/report.md "$DST"', `n=a; echo x > ${out}/scratch/$n-$$.log`]) {
      assert.equal(evaluate(payload(cmd, out)), null, `allowed from a cwd in no project: ${cmd}`);
    }
    // the grammar: the resolved word is literal and keeps its raw spelling for the refusal; an opaque one keeps its marks
    const r1 = extractWriteTargets(`n=run1; echo x > ${out}/scratch/$n.log`, out);
    assert.deepEqual([r1.targets.map((t) => t.path), r1.unresolved], [[path.join(out, 'scratch', 'run1.log')], []]);
    const r2 = extractWriteTargets(`echo x > ${out}/scratch/$name.log`, out).unresolved;
    assert.equal(r2.length, 1);
    assert.equal(r2[0].raw, `${out}/scratch/$name.log`);
    assert.ok(r2[0].marks.includes('x'));
    // real shells: the matrix's row and P11 overwrite the tracked file when unguarded; the hook refuses each
    const row = `x='../${path.basename(proj)}/notes'; printf poison > ${out}/$x/rep.md`;
    for (const shell of shellsFor(['bash', 'zsh'])) {
      const r = spawnSync(shell, ['-c', row], { cwd: out, encoding: 'utf8', env: { PATH: process.env.PATH } });
      assert.equal(r.status, 0, r.stderr);
      assert.equal(fs.readFileSync(path.join(proj, 'notes', 'rep.md'), 'utf8'), 'poison', `${shell} wrote the tracked folder through the resolved value`);
      fs.rmSync(path.join(proj, 'notes', 'rep.md'));
    }
    assert.equal(runHook(row, out).status, 2, 'the hook refuses the row');
    const p11 = `cd ${proj}; cd ${out}; echo poison > ~-/docs/report.md`;
    for (const sh of shellsFor(['bash'], 'P11 in real bash')) assert.equal(overwrites(p11, report, out, sh).changed, true, 'P11 overwrites the tracked file in real bash from a cwd in no project');
    assert.equal(runHook(p11, out).status, 2, 'and the hook refuses it');
    assert.equal(runHook(`echo x > ${out}/scratch/$name.log`, out).status, 0, 'the process allows the opaque word from a cwd in no project (the cwd rule)');
    assert.equal(runHook(`echo x > ${out}/scratch/$name.log`, proj).status, 2, 'and refuses it from the tracked cwd');
    assert.equal(runHook(`n=run1; echo x > ${out}/scratch/$n.log`, proj).status, 0, 'and allows the resolved twin from the tracked cwd');
    // the residual, with its boundary (the reviewer's option (c), 2026-09-19): a literal head outside every project followed by an
    // opaque expansion whose value can climb with `..` is allowed from a cwd in no project, and when the environment holds such a
    // value the write lands in the tracked folder; from the tracked cwd the same word is refused as not literal
    const residual = `printf poison > ${out}/$x/rep.md`;
    assert.equal(evaluate(payload(residual, out)), null, 'allowed from a cwd in no project: the stated residual');
    assert.match(evaluate(payload(residual, proj)) || '', NOT_LITERAL, 'refused as not literal from the tracked cwd: the boundary');
    for (const shell of shellsFor(['bash', 'zsh'])) {
      const r = spawnSync(shell, ['-c', residual], { cwd: out, encoding: 'utf8', env: { PATH: process.env.PATH, x: `../${path.basename(proj)}/notes` } });
      assert.equal(r.status, 0, r.stderr);
      assert.equal(fs.readFileSync(path.join(proj, 'notes', 'rep.md'), 'utf8'), 'poison', `${shell} lands the write in the tracked folder through the environment's value: the residual as stated`);
      fs.rmSync(path.join(proj, 'notes', 'rep.md'));
    }
    assert.equal(runHook(residual, out).status, 0);
    assert.equal(runHook(residual, proj).status, 2);
  } finally { fs.rmSync(out, { recursive: true, force: true }); }
});

test('a mention of PWD or OLDPWD outside an expansion, or a variable name the shell fills in, makes $PWD, $OLDPWD, ~+ and ~- unreadable for the whole command, as a mention of HOME does (B2 as ruled; its first draft read them through its own directory model, the fifth pass\'s attacker found); a command that only expands them is resolved; real bash, zsh and dash overwrite through the reassigned name and the hook refuses from the tracked cwd, while from a cwd in no project the word keeps the cwd rule', () => {
  const out = outsideDir();
  try {
    fs.mkdirSync(path.join(out, 'scratch'));
    fs.mkdirSync(path.join(proj, 'scratch'));
    fs.writeFileSync(path.join(proj, 'notes', 'n1.md'), 'a tracked note\n');
    const web = trackedProjectAt(out, 'web');
    const webReport = path.join(web, 'docs', 'report.md');
    const scratch = path.join(proj, 'scratch');
    const BARE = 'names PWD outside an expansion';
    const BARE_OLD = 'names OLDPWD outside an expansion';
    // the attacker's rows: from an untracked folder of the tracked project, the reassigned name resolves nowhere the guard can
    // read, so the word keeps the cwd rule (class F, naming the project) and the reason says why the name was not read
    const rows = [
      [`PWD=${web}; cp ${web}/base/report.md $PWD/docs/report.md`, scratch, BARE, ['bash', 'zsh', 'dash']],
      [`PWD=${web}; cp ${web}/base/report.md \${PWD}/docs/report.md`, scratch, BARE, ['bash', 'zsh', 'dash']],
      [`export PWD=${web}; cp ${web}/base/report.md $PWD/docs/report.md`, scratch, BARE, ['bash', 'zsh', 'dash']],
      [`PWD=${web}; cp ${web}/base/report.md ~+/docs/report.md`, scratch, BARE, ['bash']],
      [`declare PWD=${web}; cp ${web}/base/report.md $PWD/docs/report.md`, scratch, BARE, ['bash']],
      [`h=P; export \${h}WD=${web}; cp ${web}/base/report.md $PWD/docs/report.md`, scratch, 'a name I cannot read may be PWD', ['bash', 'zsh']],   // M1's assembled name
      [`cd ${scratch}; OLDPWD=${web}; cp ${web}/base/report.md $OLDPWD/docs/report.md`, out, BARE_OLD, ['bash', 'zsh', 'dash']],
      [`cd ${scratch}; OLDPWD=${web}; cp ${web}/base/report.md ~-/docs/report.md`, out, BARE_OLD, ['bash']],
    ];
    for (const [cmd, cwd, why, shells] of rows) {
      const reason = evaluate(payload(cmd, cwd));
      assert.ok(reason && NOT_LITERAL.test(reason) && reason.includes(proj) && reason.includes(why), `refused as not literal, naming the project and why the name was not read: ${cmd}: ${reason}`);
      assert.ok(!/\u2014/.test(reason) && !ROMP_NOUNS.test(reason.split(proj).join('<p>').split(out).join('<o>')), 'no em dash, no romp noun');
      for (const shell of shellsFor(shells)) assert.equal(overwrites(cmd, webReport, cwd, shell).changed, true, `${shell} overwrites the tracked file through the reassigned name: ${cmd}`);
      assert.equal(runHook(cmd, cwd).status, 2, `the hook refuses: ${cmd}`);
    }
    // after a literal head outside every project the same name is opaque and the word keeps the cwd rule (B2 as ruled): from a
    // cwd in no project it is allowed (run in both shells below, the tracked files unchanged), from the tracked cwd it is refused
    // as not literal with the reason
    const headRow = `PWD=${web}; echo x > ${out}/scratch/$PWD/x.md`;
    assert.equal(evaluate(payload(headRow, out)), null, 'from a cwd in no project the opaque word is dropped');
    assert.equal(runHook(headRow, out).status, 0);
    const headReason = evaluate(payload(headRow, scratch));
    assert.ok(headReason && NOT_LITERAL.test(headReason) && headReason.includes(proj) && headReason.includes(BARE), `from the tracked cwd: ${headReason}`);
    assert.equal(runHook(headRow, scratch).status, 2);
    // the grammar: the word carries why its expansion stayed opaque; without the mention it resolves
    const u = extractWriteTargets(`PWD=${web}; echo x > $PWD/y.md`, scratch).unresolved;
    assert.equal(u.length, 1);
    assert.deepEqual([u[0].why.kind, u[0].why.name], ['namedExpansion', 'PWD']);
    assert.deepEqual(extractWriteTargets('echo x > $PWD/y.md', scratch).targets.map((t) => t.path), [path.join(scratch, 'y.md')]);
    // the twins: a command that only expands PWD or OLDPWD is resolved and judged as B2 does; a mention beside no such
    // expansion changes nothing; the by-name refusal of a resolved tracked path stands
    const twins = [
      [`cp ${web}/base/report.md $PWD/copy.md`, scratch, null],
      [`cp ${web}/base/report.md ~+/copy2.md`, scratch, null],
      [`cd ${out}/scratch && echo x > $OLDPWD/scratch/back.log`, proj, null],
      [`cd ${out}/scratch && echo x > ~-/scratch/back2.log`, proj, null],
      [`echo PWD > ${out}/scratch/pwd.log`, proj, null],
      [`echo x > "$PWD/docs/report.md"`, proj, /^Track-changes is ON for /],
      [`cd docs; cp ../base/report.md $OLDPWD/docs/report.md`, proj, /^Track-changes is ON for /],
    ];
    const before = `${shaOf(report)} ${shaOf(webReport)}`;
    for (const [cmd, cwd, want] of twins) {
      const reason = evaluate(payload(cmd, cwd));
      if (want === null) {
        assert.equal(reason, null, `allowed: ${cmd}`);
        for (const shell of shellsFor(['bash', 'zsh'])) {
          const r = spawnSync(shell, ['-c', cmd], { cwd, encoding: 'utf8', env: { PATH: process.env.PATH } });
          assert.equal(r.status, 0, `${shell}: ${cmd}: ${r.stderr}`);
        }
      } else assert.match(reason, want, `judged by name: ${cmd}`);
    }
    for (const shell of shellsFor(['bash', 'zsh'])) spawnSync(shell, ['-c', headRow], { cwd: out, encoding: 'utf8', env: { PATH: process.env.PATH } });   // lands under <out>/scratch, or fails on the folder that is not there; nothing tracked
    assert.equal(`${shaOf(report)} ${shaOf(webReport)}`, before, 'the allowed twins and the literal-head row left both tracked files as they were');
    assert.equal(fs.readFileSync(path.join(scratch, 'copy.md'), 'utf8'), 'an older copy\n', 'the resolved $PWD twin landed in the untracked folder');
  } finally { fs.rmSync(out, { recursive: true, force: true }); }
});

// ── the pin addendum (2026-09-19): the fifth pass's unpinned claims pinned, and the attacker's misses closed ──
//
// The mutation lens over the fifth pass found seven B2 claims that no test held (each mutation green), and the attacker
// found seven in-model overwrites, each a stated rule the guard failed to apply to a construct it could see (B2's first
// draft read $PWD and $OLDPWD through its own directory model while the command reassigned them, closed in B2's own
// commit, the test before this block; cp --parents was a known flag whose landing was computed as the basename; python's
// -c was matched only at the end of a word and node's --eval= not at all; a triple-quoted python path and a template
// literal holding a quote fell outside the string grammar). Each is
// pinned here in both directions, the refused row beside its allowed twin, with the refused rows run unguarded in real
// shells over the scratch world (a live overwrite, or a new file in the tracked folder) and the twins run with the
// tracked subset hashed after.

// A command run unguarded in a real shell from `cwd` that creates `file` (a new entry in a tracked folder): whether it
// landed; the file is removed after, so the next row starts clean.
const lands = (cmd, file, cwd, shell) => {   // `shell` from shellsFor, as overwrites (round 5)
  const r = spawnSync(shell, ['-c', cmd], { cwd, encoding: 'utf8', env: { PATH: process.env.PATH } });
  const there = fs.existsSync(file);
  fs.rmSync(file, { force: true });
  return { landed: there, status: r.status, stderr: r.stderr };
};
// The tracked subset's fingerprint: the tracked note's sha and the tracked folder's listing.
const trackedFingerprint = () => `${shaOf(report)} ${fs.readdirSync(path.join(proj, 'notes')).sort().join(',')}`;

test("the fifth pass's unpinned B2 claims are pinned from the tracked cwd, where an unresolved name is refused and a resolved one judged by name: a mid-word $HOME beside a mention of HOME stays opaque; a loop variable, a read, a mapfile and a getopts into a name set earlier make it unreadable; a $(...) inherits a copy of the names; a flock -c string starts with none; a value resolves under a bare .git repo; from a cwd in no project the same opaque rows keep the cwd rule (the stated residual, its landing measured); real bash and zsh land in the tracked folder through each and the twins run clean", () => {
  const out = outsideDir();
  const P = path.basename(proj);   // out and proj are siblings under the temp root, so ../../<P> from <out>/scratch is the project
  try {
    fs.mkdirSync(path.join(out, 'scratch'));
    fs.writeFileSync(path.join(proj, 'notes', 'n1.md'), 'a tracked note\n');
    const BY_NAME = /^Track-changes is ON for /;
    const landing = path.join(proj, 'notes', 'x.md');
    // from the tracked cwd an unresolved name is refused as not literal, naming the project (class F and the cwd rule)
    const refused = (cmd, extra = null) => {
      const reason = evaluate(payload(cmd, proj));
      assert.ok(reason && NOT_LITERAL.test(reason) && reason.includes(proj), `refused as not literal from the tracked cwd: ${cmd}: ${reason}`);
      if (extra) assert.ok(reason.includes(extra), `the reason says why: ${cmd}: ${reason}`);
      assert.ok(!/\u2014/.test(reason) && !ROMP_NOUNS.test(reason.split(proj).join('<p>').split(out).join('<o>')), 'no em dash, no romp noun');
    };
    const allowed = (cmd, cwd = proj) => assert.equal(evaluate(payload(cmd, cwd)), null, `allowed: ${cmd}`);
    // B2 as ruled (option (c)): from a cwd in no project the same word keeps the cwd rule and is dropped, the residual the four
    // surfaces state; when the value climbs with `..` the write lands in the tracked folder (measured below), which is the
    // residual's boundary as stated
    const residual = (cmd) => assert.equal(evaluate(payload(cmd, out)), null, `from a cwd in no project the opaque word keeps the cwd rule (the stated residual): ${cmd}`);
    const before = trackedFingerprint();
    // B2l: HOME is not resolved once rule (a) applies, for a MID-WORD $HOME too (a leading $HOME/ is class D, mark 'h'; the
    // mid-word one carries mark 'x' and goes through valueOf). Since the seventh pass's addendum (item 1) the plain top-level
    // `HOME=<dir>;` is the one form the guard reads, so this row resolves through it and is refused BY NAME on the tracked
    // folder from the tracked cwd AND from the cwd in no project (where the residual allowed it before); the `export` form of
    // the same row keeps rule (a): refused as not literal from the tracked cwd, the residual from the cwd in no project
    const homeRow = `HOME=../../${P}/notes; echo x > ${out}/scratch/$HOME/x.md`;
    const homeExportRow = `export HOME=../../${P}/notes; echo x > ${out}/scratch/$HOME/x.md`;
    for (const cwd of [proj, out]) assert.match(evaluate(payload(homeRow, cwd)) || '', BY_NAME, `the plain HOME= write resolves and the write is refused by name from ${cwd === proj ? 'the tracked cwd' : 'a cwd in no project'}`);
    refused(homeExportRow, 'the command names HOME outside an expansion');
    allowed(`echo x > ${out}/scratch/$HOME/x.md`);   // no mention of HOME: resolved through the guard's home, outside every project
    residual(homeExportRow);
    for (const shell of shellsFor(['bash', 'zsh'])) for (const row of [homeRow, homeExportRow]) assert.equal(lands(row, landing, out, shell).landed, true, `${shell} lands x.md in the tracked folder through the reassigned HOME: ${row}`);
    // B2n: a for or select loop variable the command earlier set to a plain string is unreadable
    const forRow = `f=a; for f in ../../${P}/notes/x; do echo x > ${out}/scratch/$f.md; done`;
    refused(forRow);
    refused(`f=a; select f in ../../${P}/notes/x; do echo x > ${out}/scratch/$f.md; break; done <<< 1`);
    allowed(`f=a; for g in b; do echo x > ${out}/scratch/$f.md; done`);   // another loop variable: f stays the plain string
    residual(forRow);
    for (const shell of shellsFor(['bash', 'zsh'])) assert.equal(lands(forRow, landing, out, shell).landed, true, `${shell} lands x.md through the loop variable`);
    // B2o: a read, a mapfile or a getopts into a name set earlier makes it unreadable
    const readRow = `n=a; read n <<< ../../${P}/notes/x; echo x > ${out}/scratch/$n.md`;
    refused(readRow);
    refused(`n=a; mapfile -t n <<< ../../${P}/notes/x; echo x > ${out}/scratch/$n.md`);
    refused(`n=a; getopts x n -x; echo x > ${out}/scratch/$n.md`);
    allowed(`n=a; read m <<< b; echo x > ${out}/scratch/$n.md`);   // a read into another name
    residual(readRow);
    for (const shell of shellsFor(['bash', 'zsh'])) assert.equal(lands(readRow, landing, out, shell).landed, true, `${shell} lands x.md through the read`);
    for (const sh of shellsFor(['bash'], 'the mapfile')) assert.equal(lands(`n=a; mapfile -t n <<< ../../${P}/notes/x; echo x > ${out}/scratch/$n.md`, landing, out, sh).landed, true, 'bash lands x.md through the mapfile');
    // B2q: a $(...) inherits a COPY of the names: resolved inside it, and its own assignments do not come back
    const subRows = [`n=sub; echo $(echo x > ${out}/scratch/$n.log)`, `n=a; x=$(n=b); echo x > ${out}/scratch/$n.log`];
    for (const cmd of subRows) allowed(cmd);
    // B2r, B2s (the poison of an unknown wrapper option and of an env -S string) are NOT pinned here, and neither is the xargs
    // poison: whether that poison stays is flagged for a ruling in fork PR #780's body (an external command cannot reassign
    // the calling shell's variables; an eval, a source or a function call can, and those stay poisoners), and a pin would fix
    // one side of the question. Both sides are observable once ruled (the sixth pass's mutation lens measured them): from a
    // tracked cwd the verdict is a refusal either way but its class differs (rule (b)'s option text with the poison, by name
    // on the resolved value without it); from a cwd in no project the verdict itself flips (allowed with the poison, and the
    // write lands when the value climbs into the tracked folder; refused by name without it). The parsed-wrapper twin resolves.
    allowed(`n=a; env true; echo x > ${out}/scratch/$n.log`);   // a wrapper the guard parses in full changes nothing
    // B2t: a flock -c string runs in a fresh shell and inherits no names (single-quoted, so the inner shell expands it)
    refused(`n=a; flock -x ${out} -c 'echo x > ${out}/scratch/$n.log'`);
    allowed(`n=a; flock -x ${out} -c "echo x > ${out}/scratch/$n.log"`);   // the OUTER shell expands the double-quoted name first
    const flockRow = `export n=../../${P}/notes/x; flock -x ${out} -c 'echo x > ${out}/scratch/$n.md'`;
    refused(flockRow);
    residual(flockRow);
    for (const shell of shellsFor(['bash', 'zsh'])) assert.equal(lands(flockRow, landing, out, shell).landed, true, `${shell} lands x.md through the exported name in the flock string`);
    // a project that tracks nothing refusable (a bare .git repo) is not in play: an opaque word there keeps the cwd rule and is
    // dropped (B2 as ruled; B2's first draft refused it as an opaque head), while a value that resolves into the tracked folder
    // is judged by name from that cwd
    const repo = path.join(out, 'repo');
    fs.mkdirSync(path.join(repo, '.git'), { recursive: true });
    fs.mkdirSync(path.join(repo, 'docs'));
    allowed(`echo x > ${repo}/docs/$name.log`, repo);
    const repoRow = `name=../../../${P}/notes/x; echo x > ${repo}/docs/$name.log`;
    assert.match(evaluate(payload(repoRow, repo)), BY_NAME, 'a value that resolves into the tracked folder is refused by name');
    for (const shell of shellsFor(['bash', 'zsh'])) assert.equal(lands(repoRow, path.join(proj, 'notes', 'x.log'), repo, shell).landed, true, `${shell} lands x.log in the tracked folder from the bare repo`);
    const repoTwins = [`echo x > ${repo}/docs/plain.log`, `n=plain; echo x > ${repo}/docs/$n.log`, `echo x > ${repo}/docs/$name.log`];
    // the allowed twins run in both shells (a status of 0 where the folder exists) and touch nothing tracked
    const clean = [...subRows.map((c) => [c, proj]), [`n=a; env true; echo x > ${out}/scratch/$n.log`, proj], [`f=a; for g in b; do echo x > ${out}/scratch/$f.md; done`, proj], [`n=a; read m <<< b; echo x > ${out}/scratch/$n.md`, proj], [`n=a; flock -x ${out} -c "echo x > ${out}/scratch/$n.log"`, proj], ...repoTwins.map((c) => [c, repo])];
    for (const [cmd, cwd] of clean) {
      for (const shell of shellsFor(['bash', 'zsh'])) {
        const r = spawnSync(shell, ['-c', cmd], { cwd, encoding: 'utf8', env: { PATH: process.env.PATH } });
        assert.equal(r.status, 0, `${shell}: ${cmd}: ${r.stderr}`);
      }
    }
    for (const shell of shellsFor(['bash', 'zsh'])) spawnSync(shell, ['-c', `echo x > ${out}/scratch/$HOME/x.md`], { cwd: proj, encoding: 'utf8', env: { PATH: process.env.PATH, HOME: os.homedir() } });   // the home's absolute path under <out>/scratch: a folder that is not there, nothing tracked
    assert.equal(trackedFingerprint(), before, 'the twins left the tracked subset as it was');
    assert.equal(fs.readFileSync(path.join(out, 'scratch', 'sub.log'), 'utf8'), 'x\n', 'the substitution wrote where the resolved name says');
    // the process: the plain HOME= row refused from both cwds (by name), the export form refused from the tracked cwd, the
    // resolved twin allowed, the export form's residual allowed from a cwd in no project
    assert.equal(runHook(homeRow, proj).status, 2);
    assert.equal(runHook(homeRow, out).status, 2);
    assert.equal(runHook(homeExportRow, proj).status, 2);
    assert.equal(runHook(`echo x > ${out}/scratch/$HOME/x.md`, proj).status, 0);
    assert.equal(runHook(homeExportRow, out).status, 0);
  } finally { fs.rmSync(out, { recursive: true, force: true }); }
});

test("cp --parents lands each source at its whole path under the destination (a known flag whose landing the guard computed as the basename): a tracked path under the destination is refused by name from any cwd, the basename twin and an untracked source are allowed, and real bash, zsh and dash overwrite the tracked file while the hook refuses", () => {
  const out = outsideDir();
  try {
    fs.mkdirSync(path.join(out, 'scratch'));
    const web = trackedProjectAt(out, 'web');
    const webReport = path.join(web, 'docs', 'report.md');
    const BY_NAME = /^Track-changes is ON for /;
    // the grammar: the landing is <destination>/<source as spelled>, a leading slash dropped, a directory source walked
    assert.deepEqual(targets(`cp --parents docs/report.md ${web}/`), [webReport]);
    assert.deepEqual(targets(`cp -t ${web}/ --parents docs/report.md`), [webReport]);
    assert.deepEqual(targets(`cp -r --parents docs ${web}`), [path.join(web, 'docs', 'other.md'), webReport], 'a directory source is walked under its own path');
    assert.deepEqual(targets(`cp --parents /abs/x/y.md ${web}/`), [path.join(web, 'abs', 'x', 'y.md')]);
    assert.deepEqual(targets(`cp docs/report.md ${web}/`), [path.join(web, 'report.md')], 'without the flag the basename lands');
    const nonLiteral = extractWriteTargets(`cp --parents "$SRC" ${web}/`, proj).unresolved;
    assert.equal(nonLiteral.length, 1);
    assert.ok(nonLiteral[0].text.endsWith('/$SRC') && nonLiteral[0].marks.endsWith('xxxx') && nonLiteral[0].at === web, 'a source the guard cannot read lands under the destination folder, its marks kept');
    // refused by name: the whole source path under the destination is the tracked file
    const rows = [
      [`cp --parents docs/report.md ${web}/`, proj, ['bash', 'zsh', 'dash']],
      [`cp -t ${web}/ --parents docs/report.md`, proj, ['bash']],
      [`cp --parents docs/report.md ${web}`, proj, ['bash']],
      [`cp -r --parents docs ${web}/`, proj, ['bash']],
    ];
    // a `..` in the source climbs from the destination, as cp's own landing does: from <out>/scratch, the spelling
    // ../../<proj>/docs/report.md under <out>/scratch/ is the tracked file itself (cp then refuses the same-file copy and
    // writes nothing; the guard's reading of the landing is what is pinned)
    const sub = path.join(out, 'scratch');
    const climb = `cp --parents ../../${path.basename(proj)}/docs/report.md ${sub}/`;
    assert.deepEqual(targets(climb, sub), [report]);
    assert.match(evaluate(payload(climb, sub)), BY_NAME, 'refused by name on the tracked file the climb lands on');
    for (const [cmd, cwd, shells] of rows) {
      const reason = evaluate(payload(cmd, cwd));
      assert.ok(reason && BY_NAME.test(reason) && (reason.includes(webReport) || reason.includes(report)), `refused by name: ${cmd}: ${reason}`);
      for (const shell of shellsFor(shells)) assert.equal(overwrites(cmd, webReport, cwd, shell).changed, true, `${shell} overwrites the tracked file: ${cmd}`);
      assert.equal(runHook(cmd, cwd).status, 2, `the hook refuses: ${cmd}`);
    }
    // the twins: an untracked source under the destination, the basename landing without the flag, a destination in no project
    const twins = [`cp --parents base/report.md ${web}/`, `cp docs/report.md ${web}/`, `cp --parents docs/report.md ${out}/scratch/`];
    const before = shaOf(webReport);
    for (const cmd of twins) {
      assert.equal(evaluate(payload(cmd)), null, `allowed: ${cmd}`);
      for (const shell of shellsFor(['bash', 'zsh'])) {
        const r = spawnSync(shell, ['-c', cmd], { cwd: proj, encoding: 'utf8', env: { PATH: process.env.PATH } });
        assert.equal(r.status, 0, `${shell}: ${cmd}: ${r.stderr}`);
      }
      assert.equal(runHook(cmd).status, 0);
    }
    assert.equal(shaOf(webReport), before, 'the twins left the tracked file as it was');
    assert.equal(fs.readFileSync(path.join(web, 'base', 'report.md'), 'utf8'), 'an older copy\n');
    assert.equal(fs.readFileSync(path.join(out, 'scratch', 'docs', 'report.md'), 'utf8'), fs.readFileSync(report, 'utf8'), 'the flag landed the source under its own path in the untracked folder');
  } finally { fs.rmSync(out, { recursive: true, force: true }); }
});

test("an interpreter's option cluster is read as the interpreter reads it: python's -c with the code glued on (-c'...', -uc'...', -Xutf8 -c'...', -bc'...', -Ic'...'), node's --eval= and -pe, and --print= as the flag it is (the script then comes from stdin); a triple-quoted python path is a plain string and a template literal holding a quote is a template; the untracked twins and the flag-only forms are allowed; real shells overwrite through each refused form and the hook refuses", () => {
  const BY_NAME = /^Track-changes is ON for /;
  const TEMPLATE = /a path built from a template or format string/;
  const py = (d) => [
    `python3 -c'open("${d}","w").write("poison")'`,
    `python3 -uc'open("${d}","w").write("poison")'`,
    `python3 -Xutf8 -c'open("${d}","w").write("poison")'`,
    `python3 -bc'open("${d}","w").write("poison")'`,
    `python3 -Ic'open("${d}","w").write("poison")'`,
    `python3 -c'import shutil; shutil.copy("base/report.md","${d}")'`,
    `python3 -c 'open("""${d}""","w").write("poison")'`,
    `python3 -c "open('''${d}''','w').write('poison')"`,
    `python3 -c 'open(r"""${d}""","w").write("poison")'`,
  ];
  const js = (d) => [
    `node --eval='require("fs").writeFileSync("${d}","poison")'`,
    `node -pe 'require("fs").writeFileSync("${d}","poison")'`,
    `node --print='1+1' <<'EOF'\nrequire("fs").writeFileSync("${d}","poison")\nEOF`,   // --print= takes no code: node reads the script from stdin (measured), so the heredoc body is the script
  ];
  const tracked = [...py('docs/report.md'), ...js('docs/report.md')];
  const untracked = [...py('docs/other.md'), ...js('docs/other.md')];
  for (const cmd of tracked) {
    const reason = evaluate(payload(cmd));
    assert.ok(reason && BY_NAME.test(reason) && reason.includes(report), `refused by name: ${cmd}: ${reason}`);
  }
  for (const cmd of untracked) assert.equal(evaluate(payload(cmd)), null, `the untracked twin is allowed: ${cmd}`);
  // a template literal holding a string expression is a template (unreadable, refused while the project is in play), as the
  // one holding a bare name already was
  for (const cmd of [`node -e 'require("fs").writeFileSync(\`docs/\${"report"}.md\`,"poison")'`, `node -e 'const p = (s) => s; require("fs").writeFileSync(\`docs/\${p("report")}.md\`,"poison")'`]) {
    const reason = evaluate(payload(cmd));
    assert.ok(reason && TEMPLATE.test(reason) && reason.includes(proj), `a template holding a quote refuses as unreadable: ${cmd}: ${reason}`);
  }
  // the grammar
  assert.deepEqual(scriptWriteTargets('python', 'open("""docs/report.md""","w")'), ['docs/report.md']);
  assert.deepEqual(scriptWriteTargets('python', "open('''docs/report.md''','w')"), ['docs/report.md']);
  assert.deepEqual(scriptWriteTargets('python', `open("a'b.md","w")`), ["a'b.md"], 'the other quote inside a string is text');
  assert.deepEqual(scriptTemplateTargets('node', 'fs.writeFileSync(`docs/${"report"}.md`, x)'), ['`docs/${"report"}.md`']);
  assert.deepEqual(scriptWriteTargets('node', 'fs.writeFileSync(`docs/${"report"}.md`, x)'), []);
  assert.deepEqual(scriptWriteTargets('node', `fs.writeFileSync("a'b.md", x)`), ["a'b.md"]);
  assert.deepEqual(scriptWriteTargets('node', `fs.copyFileSync('a.md', "docs/report.md")`), ['docs/report.md'], 'a copy whose two strings use different quotes');
  // the flag-only forms: -W takes `c` as its value (no -c), a cluster with no c names a script file, --eval= of a print, --print= with nothing on stdin
  const flagOnly = [`python3 -Wc 'open("docs/report.md","w")'`, `python3 -c'print(1)'`, `python3 -uc 'print(2)'`, `node --eval='console.log(1)'`, `node -pe '1+1'`, `node --print='2+2' </dev/null`];
  for (const cmd of flagOnly) assert.equal(evaluate(payload(cmd)), null, `allowed: ${cmd}`);
  // real shells: each refused form writes the tracked file when run unguarded (the first in zsh and dash too); the hook refuses
  for (const [i, cmd] of tracked.entries()) {
    for (const shell of shellsFor(i === 0 ? ['bash', 'zsh', 'dash'] : ['bash'])) assert.equal(overwrites(cmd, report, proj, shell).changed, true, `${shell} overwrites the tracked file: ${cmd}`);
    assert.equal(runHook(cmd).status, 2, `the hook refuses: ${cmd}`);
  }
  // the twins and the flag-only forms run and touch nothing tracked
  const before = shaOf(report);
  for (const cmd of [...untracked, ...flagOnly]) {
    for (const sh of shellsFor(['bash'], cmd)) {
      const r = spawnSync(sh, ['-c', cmd], { cwd: proj, encoding: 'utf8', env: { PATH: process.env.PATH } });
      if (!cmd.startsWith('python3 -Wc')) assert.equal(r.status, 0, `bash: ${cmd}: ${r.stderr}`);   // -Wc names a script file that is not there: python exits 2 and writes nothing
    }
    assert.equal(runHook(cmd).status, 0, `the hook allows: ${cmd}`);
  }
  assert.equal(shaOf(report), before, 'the twins left the tracked file as it was');
  assert.equal(fs.readFileSync(other, 'utf8'), 'poison', 'the untracked twin landed');
  // the contract's residual, measured so the list is read as a fact: an escape sequence in the string is a path the
  // interpreter decodes and the guard does not (it is named on the four surfaces beside the other computed forms)
  const escaped = `python3 -c 'open("docs\\x2freport.md","w").write("poison")'`;
  assert.equal(evaluate(payload(escaped)), null, 'an escaped path is out of model, by the contract');
  for (const sh of shellsFor(['bash'], 'the escaped path in real bash')) assert.equal(overwrites(escaped, report, proj, sh).changed, true, 'and it lands when run: the stated residual');
});

// ── the false-refusal corpus: ordinary developer commands and the known false refusals, pinned both ways ──
//
// tools/romp-track-bash-guard-corpus.json lists more than 80 ordinary developer commands (git, tests, builds, reads, cd
// then a read, `set -e` scripts writing outside tracked folders, /tmp writes, interpreter prints, wrappers, writes to
// untracked subfolders of a tracked project) and the 22 false refusals the earlier passes recorded, each with the cwd
// it runs from and the verdict the guard gives at this head. The third pass measured the corpus against the head before
// it (d296806cc) and this one; the entries that newly refuse are marked `since: third pass` with their remedy, so a
// later change that widens the cost shows here by name, and every allowed entry stays allowed.
const CORPUS = JSON.parse(fs.readFileSync(fileURLToPath(new URL('./romp-track-bash-guard-corpus.json', import.meta.url)), 'utf8'));

// The corpus world (shared by the corpus test and round 5's since sweep): the scratch project of beforeEach with a few more entries
const corpusWorld = () => {
  const B = outsideDir();
  // an outside folder beside a second tracked project (for the class-E entries), and a home folder holding a tracked
  // project two levels down (for the rule-(e) cost entry)
  fs.mkdirSync(path.join(proj, 'scratch'));
  fs.mkdirSync(path.join(proj, 'sub'));
  fs.writeFileSync(path.join(proj, 'scratch', 'copy.md'), 'c\n');
  fs.writeFileSync(path.join(proj, 'scratch', 'a.md'), 'a\n');
  fs.symlinkSync(path.join(proj, 'docs', 'report.md'), path.join(proj, 'lnfile.md'));
  fs.symlinkSync(path.join(proj, 'nowhere'), path.join(proj, 'dangling'));
  fs.writeFileSync(path.join(B, 'x.md'), 'x\n');
  fs.symlinkSync(path.join(B, 'x.md'), path.join(proj, 'notes', 'lnout.md'));
  trackedProjectAt(B, 'proj2');
  fs.mkdirSync(path.join(B, 'scratch'));
  fs.writeFileSync(path.join(B, 'src.md'), 'src\n');
  const home = path.join(B, 'home');
  fs.mkdirSync(path.join(home, 'scratch'), { recursive: true });
  trackedProjectAt(home, path.join('code', 'proj3'));
  const cwds = { proj, docs: path.join(proj, 'docs'), out: path.join(B, 'scratch'), home };
  const fill = (s) => s.replace(/<proj>/g, proj).replace(/<out>/g, B).replace(/<home>/g, home);
  return { B, home, cwds, fill };
};

test('the corpus (tools/romp-track-bash-guard-corpus.json): more than 80 ordinary commands stay allowed, the recorded false refusals keep their verdict, and every entry runs from the cwd it names', () => {
  const { B, home, cwds, fill } = corpusWorld();
  const savedHome = process.env.HOME;
  process.env.HOME = home;
  try {
    assert.ok(CORPUS.length >= 102, `at least 80 ordinary commands and the 22 recorded false refusals: ${CORPUS.length}`);
    assert.ok(CORPUS.filter((e) => e.kind === 'ordinary').length >= 80, 'at least 80 ordinary commands');
    assert.equal(CORPUS.filter((e) => e.kind === 'recorded').length, 22, 'the 22 false refusals the earlier passes recorded');
    const got = {};
    const want = {};
    for (const e of CORPUS) {
      assert.ok(['allow', 'refuse'].includes(e.verdict) && cwds[e.cwd], `a well-formed entry: ${JSON.stringify(e)}`);
      if (e.verdict === 'refuse') assert.ok(e.remedy, `a refused entry names its remedy: ${e.command}`);
      const reason = evaluate(payload(fill(e.command), cwds[e.cwd]));
      got[`${e.cwd}: ${e.command}`] = reason == null ? 'allow' : 'refuse';
      want[`${e.cwd}: ${e.command}`] = e.verdict;
      if (reason) assert.ok(!/\u2014/.test(reason) && !ROMP_NOUNS.test(reason.split(proj).join('<p>').split(B).join('<b>')), `no em dash, no romp noun: ${e.command}`);
    }
    assert.deepEqual(got, want);
    const since = CORPUS.filter((e) => e.since);
    assert.ok(since.length >= 5 && since.every((e) => e.kind === 'cost' && e.verdict === 'refuse' && e.remedy), 'each entry a pass added to the cost is refused and names its remedy');
  } finally { process.env.HOME = savedHome; fs.rmSync(B, { recursive: true, force: true }); }
});

// ── the sixth pass (2026-09-19): the mutation lens's unpinned claims are pinned ──
//
// The sixth pass's mutation lens ran seventy-five mutations over the ruled sequence's head and found thirteen green: code
// the hook has that no test held. Nine behavioural claims are pinned below in both directions, the refused row run
// unguarded in a real shell (a live overwrite, or a new file in the tracked folder) and every allowed row run with the
// tracked subset fingerprinted after. The poison line in recordAssignments for an unknown wrapper option, an `env -S`
// string and a `flock -c` string was unreachable (each branch continues before recordAssignments runs) and is removed; the
// flock case is pinned the way it measures, no poisoner. Three claims stay unpinned and are listed in fork PR #780's body:
// whether the poison of an unknown wrapper option, of an `env -S` string and of `xargs` stays awaits a ruling (an external
// command cannot reassign the calling shell's names), and a pin would fix one side of that question.

// a refusal with no em dash and no romp noun, the scratch paths cut out first (a temp root may spell one)
const cleanReason = (reason, ...roots) => { let r = reason; for (const x of roots) r = r.split(x).join('<r>'); return !/\u2014/.test(reason) && !ROMP_NOUNS.test(r); };

test("the sixth pass, the directory model: the unreadable-name marks a command sets reach a $(...) inside it (PWD reassigned outside, $PWD inside), and a cd the guard cannot follow leaves OLDPWD unknown, so a $OLDPWD after it is not read through the stale directory; real bash and zsh overwrite through both and the hook refuses from the tracked cwd; the twins resolve, are allowed and run clean", () => {
  const out = outsideDir();
  try {
    fs.mkdirSync(path.join(proj, 'scratch'));
    fs.writeFileSync(path.join(proj, 'notes', 'n1.md'), 'a tracked note\n');
    const web = trackedProjectAt(out, 'web');
    const webReport = path.join(web, 'docs', 'report.md');
    const scratch = path.join(proj, 'scratch');
    const fingerprint = () => `${shaOf(report)} ${shaOf(webReport)} ${fs.readdirSync(path.join(proj, 'notes')).sort().join(',')}`;
    // a `$(...)` inherits the parent's unreadable-name marks (unreadableNames in the recurse context); without them the inner
    // extract read $PWD through its own directory model while the shell, its PWD reassigned outside the substitution, wrote
    // another project's tracked file
    const subRow = `PWD=${web}; echo $(cp ${web}/base/report.md $PWD/docs/report.md)`;
    const subReason = evaluate(payload(subRow, scratch));
    assert.ok(subReason && NOT_LITERAL.test(subReason) && subReason.includes(proj) && subReason.includes('names PWD outside an expansion'), `refused as not literal from the tracked cwd, saying why the name was not read: ${subReason}`);
    assert.ok(cleanReason(subReason, proj, out), 'no em dash, no romp noun');
    for (const shell of shellsFor(['bash', 'zsh'])) assert.equal(overwrites(subRow, webReport, scratch, shell).changed, true, `${shell} overwrites the tracked file through the substitution: ${subRow}`);
    assert.equal(runHook(subRow, scratch).status, 2, 'the hook refuses');
    // the same mark reaches a script handed to a named shell; that side is the grammar alone, since bash, sh and zsh reset PWD
    // on startup (measured: none wrote a tracked file)
    const u = extractWriteTargets(`PWD=${web}; sh -c 'cp ${web}/base/report.md $PWD/docs/report.md'`, scratch).unresolved;
    assert.equal(u.length, 1);
    assert.deepEqual([u[0].why.kind, u[0].why.name], ['namedExpansion', 'PWD']);
    // a cd the guard cannot follow clears OLDPWD (moveUnknown); kept stale, `$OLDPWD` after `cd "$(pwd)"` would be read as the
    // directory before the FIRST cd while the shell's OLDPWD is the directory before the second, the tracked docs folder
    const staleRow = `cd docs; cd "$(pwd)"; cp ${proj}/base/report.md $OLDPWD/report.md`;
    const staleReason = evaluate(payload(staleRow, proj));
    assert.ok(staleReason && NOT_LITERAL.test(staleReason) && staleReason.includes(proj), `refused as not literal from the tracked cwd: ${staleReason}`);
    assert.ok(cleanReason(staleReason, proj, out), 'no em dash, no romp noun');
    assert.deepEqual(extractWriteTargets(staleRow, proj).unresolved.map((w) => w.raw), ['$OLDPWD/report.md'], 'the word stays unresolved: OLDPWD is unknown after a cd the guard cannot follow');
    for (const shell of shellsFor(['bash', 'zsh'])) assert.equal(overwrites(staleRow, report, proj, shell).changed, true, `${shell} overwrites the tracked file through OLDPWD: ${staleRow}`);
    assert.equal(runHook(staleRow, proj).status, 2, 'the hook refuses');
    // the twins: no reassignment, so $PWD resolves inside the substitution; one cd the guard follows, so $OLDPWD resolves
    const twins = [
      [`echo $(cp ${web}/base/report.md $PWD/copy.md)`, scratch, path.join(scratch, 'copy.md')],
      [`cd docs; cp ../base/report.md $OLDPWD/scratch/copy2.md`, proj, path.join(scratch, 'copy2.md')],
    ];
    const before = fingerprint();
    for (const [cmd, cwd, landing] of twins) {
      assert.equal(evaluate(payload(cmd, cwd)), null, `allowed: ${cmd}`);
      assert.deepEqual(targets(cmd, cwd), [landing], `resolved to the untracked landing: ${cmd}`);
      for (const shell of shellsFor(['bash', 'zsh'])) {
        const r = spawnSync(shell, ['-c', cmd], { cwd, encoding: 'utf8', env: { PATH: process.env.PATH } });
        assert.equal(r.status, 0, `${shell}: ${cmd}: ${r.stderr}`);
        assert.equal(fs.readFileSync(landing, 'utf8'), 'an older copy\n', `${shell} landed the copy where the resolved word says`);
        fs.rmSync(landing);
      }
      assert.equal(runHook(cmd, cwd).status, 0, `the hook allows: ${cmd}`);
    }
    assert.equal(fingerprint(), before, 'the twins left both tracked files and the tracked folder as they were');
  } finally { fs.rmSync(out, { recursive: true, force: true }); }
});

test("the sixth pass, the names: a nameref declaration, a `printf -v` and a `readarray` into a name set earlier make it unreadable (real bash lands the write in the tracked folder through each, zsh through printf -v); a $(...)'s own assignments do not come back (the copy), so the write is judged where the outer value lands; an empty value is not read (refused as not literal from the tracked cwd, allowed from a cwd in no project); a flock -c string does not poison the names (the write judged by name from both cwds, landing unguarded); the twins into another name resolve and run clean", () => {
  const out = outsideDir();
  const P = path.basename(proj);   // out and proj are siblings under the temp root, so ../../<P> from <out>/scratch is the project
  try {
    fs.mkdirSync(path.join(out, 'scratch'));
    fs.writeFileSync(path.join(proj, 'notes', 'n1.md'), 'a tracked note\n');
    const BY_NAME = /^Track-changes is ON for /;
    const landing = path.join(proj, 'notes', 'x.md');
    // from the tracked cwd an unresolved name is refused as not literal, naming the project (class F and the cwd rule); from a
    // cwd in no project the same word keeps the cwd rule and is allowed (the stated residual), and the landing is measured there
    const refused = (cmd) => {
      const reason = evaluate(payload(cmd, proj));
      assert.ok(reason && NOT_LITERAL.test(reason) && reason.includes(proj), `refused as not literal from the tracked cwd: ${cmd}: ${reason}`);
      assert.ok(cleanReason(reason, proj, out), 'no em dash, no romp noun');
      assert.equal(runHook(cmd, proj).status, 2, `the hook refuses: ${cmd}`);
      assert.equal(evaluate(payload(cmd, out)), null, `from a cwd in no project the opaque word keeps the cwd rule (the stated residual): ${cmd}`);
    };
    const before = trackedFingerprint();
    // `declare -n n=other` makes n a nameref, so $n is other's value, not the plain string n held (bash; zsh has no -n)
    const namerefRow = `other=../../${P}/notes/x; n=a; declare -n n=other; echo x > ${out}/scratch/$n.md`;
    refused(namerefRow);
    for (const sh of shellsFor(['bash'], 'the nameref')) assert.equal(lands(namerefRow, landing, out, sh).landed, true, 'bash lands x.md in the tracked folder through the nameref');
    // `printf -v n` assigns n
    const printfRow = `n=a; printf -v n ../../${P}/notes/x; echo x > ${out}/scratch/$n.md`;
    refused(printfRow);
    for (const shell of shellsFor(['bash', 'zsh'])) assert.equal(lands(printfRow, landing, out, shell).landed, true, `${shell} lands x.md through printf -v`);
    // `readarray` (mapfile's synonym) assigns n (bash; zsh has no readarray)
    const readarrayRow = `n=a; readarray -t n <<< ../../${P}/notes/x; echo x > ${out}/scratch/$n.md`;
    refused(readarrayRow);
    for (const sh of shellsFor(['bash'], 'readarray')) assert.equal(lands(readarrayRow, landing, out, sh).landed, true, 'bash lands x.md through readarray');
    // a `$(...)` sees a COPY of the names, so an assignment inside it does not come back: n keeps its plain string and the
    // write is judged where the outer value lands (allowed, under <out>/scratch); with the map shared, the inner assignment
    // would carry the climb out and refuse the write by name, a false refusal
    const copyRow = `n=a; x=$(n=../../${P}/notes/x); echo x > ${out}/scratch/$n.md`;
    assert.equal(evaluate(payload(copyRow, proj)), null, 'allowed from the tracked cwd: the inner assignment does not come back');
    assert.deepEqual(targets(copyRow, proj), [path.join(out, 'scratch', 'a.md')], 'resolved through the outer value');
    for (const shell of shellsFor(['bash', 'zsh'])) {
      const r = spawnSync(shell, ['-c', copyRow], { cwd: proj, encoding: 'utf8', env: { PATH: process.env.PATH } });
      assert.equal(r.status, 0, `${shell}: ${r.stderr}`);
      assert.equal(fs.readFileSync(path.join(out, 'scratch', 'a.md'), 'utf8'), 'x\n', `${shell} wrote where the outer value says`);
      fs.rmSync(path.join(out, 'scratch', 'a.md'));
    }
    assert.equal(runHook(copyRow, proj).status, 0);
    // an empty value is not read (an unquoted empty word is dropped by the shell, so a later operand's place is not what the
    // guard would read): refused as not literal from the tracked cwd, allowed from a cwd in no project, where it writes
    // <out>/scratch/.log
    const emptyRow = `n=; echo x > ${out}/scratch/$n.log`;
    refused(emptyRow);
    for (const shell of shellsFor(['bash', 'zsh'])) {
      const r = spawnSync(shell, ['-c', emptyRow], { cwd: out, encoding: 'utf8', env: { PATH: process.env.PATH } });
      assert.equal(r.status, 0, `${shell}: ${r.stderr}`);
      assert.equal(fs.readFileSync(path.join(out, 'scratch', '.log'), 'utf8'), 'x\n');
      fs.rmSync(path.join(out, 'scratch', '.log'));
    }
    assert.equal(runHook(emptyRow, out).status, 0);
    // a flock -c string does not poison the names (an external command cannot reassign the calling shell's variables; the
    // recordAssignments line that read as if it did was unreachable and is gone): the later write is judged by name on the
    // resolved value from the tracked cwd and from a cwd in no project, and lands in the tracked folder unguarded
    const flockRow = `n=../../${P}/notes/x; flock -x ${out} -c 'true'; echo x > ${out}/scratch/$n.md`;
    for (const cwd of [proj, path.join(out, 'scratch')]) {
      assert.match(evaluate(payload(flockRow, cwd)) || '', BY_NAME, `refused by name from ${cwd === proj ? 'the tracked cwd' : 'a cwd in no project'}`);
      assert.equal(runHook(flockRow, cwd).status, 2);
    }
    for (const shell of shellsFor(['bash', 'zsh'])) assert.equal(lands(flockRow, landing, out, shell).landed, true, `${shell} lands x.md through the value flock left alone`);
    // the twins: a declaration, a printf -v and a readarray into ANOTHER name leave n readable; each allowed, run in the shells
    // that have the builtin, landing under <out>/scratch with the tracked subset unchanged
    const twins = [
      [`declare n=b; echo x > ${out}/scratch/$n.md`, 'b.md', ['bash', 'zsh']],
      [`n=a; printf -v m x; echo x > ${out}/scratch/$n.md`, 'a.md', ['bash', 'zsh']],
      [`n=a; readarray -t m <<< b; echo x > ${out}/scratch/$n.md`, 'a.md', ['bash']],
    ];
    for (const [cmd, name, shells] of twins) {
      assert.equal(evaluate(payload(cmd, proj)), null, `allowed: ${cmd}`);
      assert.deepEqual(targets(cmd, proj), [path.join(out, 'scratch', name)], `resolved: ${cmd}`);
      for (const shell of shellsFor(shells)) {
        const r = spawnSync(shell, ['-c', cmd], { cwd: proj, encoding: 'utf8', env: { PATH: process.env.PATH } });
        assert.equal(r.status, 0, `${shell}: ${cmd}: ${r.stderr}`);
        assert.equal(fs.readFileSync(path.join(out, 'scratch', name), 'utf8'), 'x\n');
        fs.rmSync(path.join(out, 'scratch', name));
      }
      assert.equal(runHook(cmd, proj).status, 0, `the hook allows: ${cmd}`);
    }
    assert.equal(trackedFingerprint(), before, 'the allowed rows left the tracked subset as it was');
  } finally { fs.rmSync(out, { recursive: true, force: true }); }
});

test("cp --parents with a destination that is not there is read as a directory copy (the refuse side: the landing is <destination>/<source as spelled>, and cp itself writes nothing without the directory), so a source whose spelling climbs onto a tracked file is refused by name from a cwd in no project; an untracked landing under the missing destination and an existing untracked folder are allowed, the folder run", () => {
  const out = outsideDir();
  const P = path.basename(proj);
  try {
    fs.mkdirSync(path.join(out, 'scratch'));
    const BY_NAME = /^Track-changes is ON for /;
    const sub = path.join(out, 'scratch');
    // from <out>/scratch the source ../../<P>/docs/report.md is the tracked file, and under the missing <out>/missing the same
    // spelling lands on it again (two `..` climb from missing to the temp root)
    const row = `cp --parents ../../${P}/docs/report.md ${out}/missing`;
    assert.deepEqual(targets(row, sub), [report], 'the landing is read under the missing destination as a directory');
    assert.match(evaluate(payload(row, sub)) || '', BY_NAME, 'refused by name on the tracked file the spelling lands on');
    assert.equal(runHook(row, sub).status, 2, 'the hook refuses');
    for (const shell of shellsFor(['bash', 'zsh'])) {
      const r = overwrites(row, report, sub, shell);
      assert.equal(r.changed, false, `${shell}: cp writes nothing without the directory (the refusal is the guard's reading of the landing)`);
      assert.notEqual(r.status, 0, `${shell}: cp stops on the missing directory`);
    }
    assert.ok(!fs.existsSync(path.join(out, 'missing')), 'cp made no destination');
    // the twins: an untracked landing under the missing destination (allowed; cp still writes nothing), and a source under an
    // existing untracked folder (allowed, run, landing at its whole spelling)
    const under = `cp --parents ../../${P}/base/report.md ${out}/missing`;
    assert.equal(evaluate(payload(under, sub)), null, `allowed: ${under}`);
    assert.equal(runHook(under, sub).status, 0);
    const twin = `cp --parents base/report.md ${out}/scratch/`;
    assert.equal(evaluate(payload(twin, proj)), null, `allowed: ${twin}`);
    const before = shaOf(report);
    for (const shell of shellsFor(['bash', 'zsh'])) {
      const r = spawnSync(shell, ['-c', twin], { cwd: proj, encoding: 'utf8', env: { PATH: process.env.PATH } });
      assert.equal(r.status, 0, `${shell}: ${twin}: ${r.stderr}`);
      assert.equal(fs.readFileSync(path.join(out, 'scratch', 'base', 'report.md'), 'utf8'), 'an older copy\n', `${shell} landed the source at its whole spelling under the folder`);
      fs.rmSync(path.join(out, 'scratch', 'base'), { recursive: true });
      spawnSync(shell, ['-c', under], { cwd: sub, encoding: 'utf8', env: { PATH: process.env.PATH } });   // stops on the missing directory, writes nothing
    }
    assert.equal(runHook(twin, proj).status, 0);
    assert.equal(shaOf(report), before, 'the twins left the tracked file as it was');
    assert.ok(!fs.existsSync(path.join(out, 'missing')), 'the untracked twin under the missing destination made nothing either');
  } finally { fs.rmSync(out, { recursive: true, force: true }); }
});

test("python's -m ends the option walk with no code in the command (a module's code is not there to scan), so a heredoc after `-mjson.tool` or `-m json.tool` is the module's stdin data, allowed and run (json.tool rejects it and writes nothing); the same heredoc after a flag alone is the script, refused by name and overwriting when run", () => {
  const body = 'open("docs/report.md","w").write("poison")';
  const moduleRows = [`python3 -mjson.tool <<'EOF'\n${body}\nEOF`, `python3 -m json.tool <<'EOF'\n${body}\nEOF`];
  const scriptRow = `python3 -u <<'EOF'\n${body}\nEOF`;
  const before = shaOf(report);
  for (const cmd of moduleRows) {
    assert.equal(evaluate(payload(cmd)), null, `allowed: ${cmd}`);
    assert.equal(runHook(cmd).status, 0, `the hook allows: ${cmd}`);
    for (const shell of shellsFor(['bash', 'zsh'])) {
      const r = spawnSync(shell, ['-c', cmd], { cwd: proj, encoding: 'utf8', env: { PATH: process.env.PATH } });
      assert.notEqual(r.status, 0, `${shell}: json.tool rejects the heredoc as data: ${cmd}`);
      assert.match(r.stderr, /Expecting value/, 'read as JSON, not run');
    }
  }
  assert.equal(shaOf(report), before, 'the module runs left the tracked file as it was');
  const reason = evaluate(payload(scriptRow));
  assert.ok(reason && /^Track-changes is ON for /.test(reason) && reason.includes(report), `the heredoc after a flag alone is the script, refused by name: ${reason}`);
  for (const shell of shellsFor(['bash', 'zsh'])) assert.equal(overwrites(scriptRow, report, proj, shell).changed, true, `${shell} overwrites the tracked file through the heredoc script`);
  assert.equal(runHook(scriptRow).status, 2, 'the hook refuses');
});

// ── the seventh pass (2026-09-19): the sixth pass's attacker, and the readability rule that closes its 77 rows ──
//
// The sixth pass's attacker ran the hook as a process against 86c0643ec and executed every row unguarded in bash, zsh and dash
// over a fresh synthetic world, and found 77 in-model live overwrites in 13 spelling classes: each a value the command SPELLS
// that the resolution half resolved to a string the shell does not produce (a tilde opening the value, a declaration flag, a
// nameref, an assembled name, a scope the shells run in a subshell, a wrapper's argument, two assignment words read out of
// order, a `function NAME {` definition, a wrapper-named function, a subscript). The hook closes them as ONE rule, stated at
// RESOLVED_NAME: a name is readable only when every write to it is a plain top-level `NAME=plain-string` the shell performs as
// spelled, and any other construct that can write it makes it unreadable. Pinned below: every one of the 77 rows run through the
// hook as a PROCESS from its cwd (refused, the reason naming the construct or the tracked file the value resolves to; from a cwd
// in no project a row whose value the rule leaves unreadable is the ruled residual, allowed, the word measured opaque), then run
// unguarded in the shells the attacker named with the tracked subset fingerprinted before and after; the twins the attacker said
// must keep their verdict; the false refusals the reviewer asked to see priced; the rule itself against constructs the hook does
// not enumerate; four more live overwrites found with the fix; and the addendum's four items.

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
  const cwds = { na: NA, nas: path.join(NA, 'scratch'), out: OUT };
  const env = { PATH: process.env.PATH, HOME, LC_ALL: 'C.UTF-8' };
  // the hook as a process from the row's cwd, HOME the world's home
  const hook = (cmd, cwd) => { const r = spawnSync(process.execPath, [HOOK], { input: payload(cmd, cwd), encoding: 'utf8', env: { ...env, ROMP_SID } }); return { status: r.status, reason: String(r.stderr || '') }; };
  // the row run unguarded in a real shell over a fresh world: whether the tracked subset changed
  const run = (cmd, cwd, shell) => {
    build();
    const before = fingerprint();
    const argv = shell === 'bash' ? ['--norc', '--noprofile', '-c', cmd] : shell === 'zsh' ? ['-f', '-c', cmd] : ['-c', cmd];
    const r = spawnSync(shell, argv, { cwd, input: '', encoding: 'utf8', env, timeout: 20000 });
    return { changed: fingerprint() !== before, status: r.status, stderr: String(r.stderr || '').slice(0, 300) };
  };
  build();
  return { W, HOME, NA, WEB, OUT, build, fingerprint, fill, cwds, env, hook, run, rm: () => fs.rmSync(W, { recursive: true, force: true }) };
};
const BY_NAME_RE = /^Track-changes is ON for /;

test("the sixth pass's attacker: its 77 in-model rows, run through the hook as a process from each row's cwd, refuse from the tracked cwd (by name where the value resolves, as not literal with the construct named otherwise) and from a cwd in no project split into the five whose value resolves (refused by name) and the ten the rule leaves opaque (the ruled residual, allowed, the word measured opaque); every refused row overwrites the tracked subset when run unguarded in the shells the attacker named, and so does every residual row", () => {
  const w = sixthPassWorld();
  const savedHome = process.env.HOME;
  process.env.HOME = w.HOME;
  try {
    const daemonHome = HAS_SHELL.bash ? spawnSync('bash', ['-c', 'echo ~daemon'], { encoding: 'utf8' }).stdout.trim() : '';
    const hasDaemon = daemonHome !== '' && daemonHome !== '~daemon' && fs.existsSync(daemonHome);
    const A = ['bash', 'zsh', 'dash'];
    const BZ = ['bash', 'zsh'];
    const BD = ['bash', 'dash'];
    const B = ['bash'];
    const Z = ['zsh'];
    const flag = (cmd, f) => ['literal', `a \`${cmd}\` flag that can change the value or what the name is (${f})`];
    const NAMEREF = ['literal', 'a nameref'];
    const CALL = ['literal', /a function the command defines, may assign any name|an if, loop, case or function body/];   // the body's own assignment taints the name first; the call poisons every name
    const SUBSCRIPT = ['literal', 'a subscript'];
    const PIPE = ['literal', 'a pipeline, whose members bash and dash run in a subshell'];
    const wrapper = (n) => ['literal', `an argument of the wrapper \`${n}\`, which the shell hands to it rather than assigning`];
    const prefix = (n) => ['literal', `a prefix assignment on \`${n}\``];
    // [id, cwd, command, the shells the attacker measured writing, the verdict the rule gives]
    const rows = [
      // C1: a tilde opening an assignment value
      ['R1-a', 'na', 'x=~/../notes-api/docs/report.md; cp base/report.md $x', A, 'name'],
      ['R1-b', 'na', 'x=~+/docs/report.md; cp base/report.md $x', BZ, 'name'],
      ['R1-c', 'na', 'cd {WEB}; cd {NA}; x=~-/docs/report.md; cp base/report.md $x', BZ, 'name'],
      ['R1-d', 'na', 'x=~; cp base/report.md $x/../notes-api/docs/report.md', A, 'name'],
      ['R1-e', 'out', 'x=~/../notes-api/docs/report.md; cp {WEB}/base/report.md $x', A, 'name'],
      ['R1-f', 'out', 'x=~+/../notes-api/docs/report.md; cp {WEB}/base/report.md $x', BZ, 'name'],
      ['R1-h', 'na', 'export x=~/../notes-api/docs/report.md; cp base/report.md $x', A, 'name'],
      ['R1-i', 'na', 'declare x=~/../notes-api/docs/report.md; cp base/report.md $x', BZ, 'name'],
      ['R17-r', 'out', 'x=~/../notes-api/docs/report.md; printf poison > $x', A, 'name'],
      ['R17-a2', 'na', 'x=~daemon/../..{W}/notes-api/docs/report.md; cp base/report.md $x', A, ['literal', 'a value that begins with `~user`']],
      ['R17-a3', 'out', 'x=~daemon/../..{W}/notes-api/docs/report.md; cp {WEB}/base/report.md $x', A, 'residual'],
      // C2: a declaration flag that transforms the value
      ['R2-a', 'na', 'declare -l x=../docs/REPORT.MD; cp base/report.md scratch/$x', BZ, flag('declare', '-l')],
      ['R2-b', 'na', 'typeset -l x=../docs/REPORT.MD; cp base/report.md scratch/$x', BZ, flag('typeset', '-l')],
      ['R2-c', 'na', 'typeset -L 17 x=../docs/report.mdZZZ; cp base/report.md scratch/$x', Z, flag('typeset', '-L')],
      ['R2-d', 'na', 'typeset -R 17 x=ZZZ../docs/report.md; cp base/report.md scratch/$x', Z, flag('typeset', '-R')],
      ['R2-e', 'out', 'declare -l x=../../notes-api/docs/REPORT.MD; cp {WEB}/base/report.md {OUT}/scratch/$x', BZ, 'residual'],
      ['R17-m', 'na', 'declare -l x; x=../docs/REPORT.MD; cp base/report.md scratch/$x', BZ, flag('declare', '-l')],
      ['R17-n', 'na', 'typeset -l x; x=../docs/REPORT.MD; cp base/report.md scratch/$x', BZ, flag('typeset', '-l')],
      // C3: a nameref reaching the resolved name (bash)
      ['R3-a', 'na', 'x=other.md; declare -n r=x; r=../docs/report.md; cp base/report.md scratch/$x', B, NAMEREF],
      ['R3-b', 'na', 'declare -n r=x; x=other.md; r=../docs/report.md; cp base/report.md scratch/$x', B, NAMEREF],
      ['R3-c', 'na', 'x=other.md; declare -n r=x; read r <<< ../docs/report.md; cp base/report.md scratch/$x', B, NAMEREF],
      ['R3-d', 'na', 'x=other.md; declare -n r=x; printf -v r ../docs/report.md; cp base/report.md scratch/$x', B, NAMEREF],
      ['R3-e', 'na', 'x=other.md; typeset -n r=x; r=../docs/report.md; cp base/report.md scratch/$x', B, NAMEREF],
      ['R3-f', 'na', 'x=other.md; declare -n r=x; declare r=../docs/report.md; cp base/report.md scratch/$x', B, NAMEREF],
      ['R3-g', 'out', 'x=../../notes-api/docs/other.md; declare -n r=x; r=../../notes-api/docs/report.md; cp {WEB}/base/report.md {OUT}/scratch/$x', B, 'residual'],
      ['R17-o', 'na', 'declare -n r=x; x=other.md; declare -n r; r=../docs/report.md; cp base/report.md scratch/$x', B, NAMEREF],
      // C4: an assembled name operand (the resolved name is written when the name resolves; every name when it does not)
      ['R4-a', 'na', 'x=other.md; h=x; export $h=../docs/report.md; cp base/report.md scratch/$x', A, 'name'],
      ['R4-b', 'na', 'x=other.md; h=x; declare $h=../docs/report.md; cp base/report.md scratch/$x', BZ, 'name'],
      ['R4-c', 'na', 'x=other.md; h=x; typeset $h=../docs/report.md; cp base/report.md scratch/$x', BZ, 'name'],
      ['R4-d', 'na', 'x=other.md; h=x; readonly $h=../docs/report.md; cp base/report.md scratch/$x', A, 'name'],
      ['R4-e', 'na', 'x=other.md; h=x; export "$h=../docs/report.md"; cp base/report.md scratch/$x', A, 'name'],
      ['R4-f', 'na', 'x=other.md; export $(echo x)=../docs/report.md; cp base/report.md scratch/$x', A, ['literal', 'takes a variable name the shell fills in when it runs']],
      ['R4-i', 'na', 'x=other.md; h=x; export ${h}=../docs/report.md; cp base/report.md scratch/$x', A, 'name'],
      ['R4-j', 'out', 'x=../../notes-api/docs/other.md; h=x; export $h=../../notes-api/docs/report.md; cp {WEB}/base/report.md {OUT}/scratch/$x', A, 'name'],
      // C5a: an assignment as the tail of a pipeline
      ['R5-a', 'na', 'x=../docs/report.md; cat </dev/null | x=other.md; cp base/report.md scratch/$x', BD, PIPE],
      ['R17-e', 'na', 'x=../docs/report.md; cat </dev/null | { x=other.md; }; cp base/report.md scratch/$x', BD, PIPE],
      ['R5-a-out', 'out', 'x=../../notes-api/docs/report.md; cat </dev/null | x=z; cp {WEB}/base/report.md {OUT}/scratch/$x', BD, 'residual'],
      // C5b: a { } group that is piped or backgrounded
      ['R5-b', 'na', 'x=../docs/report.md; { x=other.md; } | cat; cp base/report.md scratch/$x', A, ['literal', 'a `{ }` group that is piped']],
      ['R5-c', 'na', 'x=../docs/report.md; { x=other.md; } & wait; cp base/report.md scratch/$x', A, ['literal', 'a `{ }` group that is backgrounded']],
      ['R17-d', 'na', 'x=../docs/report.md; { x=other.md; } 2>&1 | cat; cp base/report.md scratch/$x', A, ['literal', 'a `{ }` group that is piped']],
      ['R5-b-out', 'out', 'x=../../notes-api/docs/report.md; { x=z; } | cat; cp {WEB}/base/report.md {OUT}/scratch/$x', A, 'residual'],
      // C5c: a wrapper before an assignment-shaped word
      ['R5-d', 'na', 'x=../docs/report.md; command x=other.md; cp base/report.md scratch/$x', A, wrapper('command')],
      ['R5-e', 'na', 'x=../docs/report.md; builtin x=other.md; cp base/report.md scratch/$x', A, wrapper('builtin')],
      ['R5-f', 'na', 'x=../docs/report.md; env x=other.md; cp base/report.md scratch/$x', A, wrapper('env')],
      ['R5-g', 'na', 'x=../docs/report.md; nice x=other.md; cp base/report.md scratch/$x', A, wrapper('nice')],
      ['R5-h', 'na', 'x=../docs/report.md; nohup x=other.md; cp base/report.md scratch/$x', A, wrapper('nohup')],
      ['R17-g', 'na', 'x=../docs/report.md; env -i x=other.md; cp base/report.md scratch/$x', A, wrapper('env')],
      ['R17-h', 'na', 'x=../docs/report.md; command -p x=other.md; cp base/report.md scratch/$x', A, wrapper('command')],
      ['R5-d-out', 'out', 'x=../../notes-api/docs/report.md; command x=z; cp {WEB}/base/report.md {OUT}/scratch/$x', A, 'residual'],
      ['R5-f-out', 'out', 'x=../../notes-api/docs/report.md; env x=z; cp {WEB}/base/report.md {OUT}/scratch/$x', A, 'residual'],
      // C5d: two assignment words in one command, the later reading the earlier (the words read left to right, as the shells do)
      ['R5-n', 'na', 'x=other.md; x=../docs/report.md y=$x; cp base/report.md scratch/$y', A, 'name'],
      ['R5-n-out', 'out', 'x=z; x=../../notes-api/docs/report.md y=$x; cp {WEB}/base/report.md {OUT}/scratch/$y', A, 'name'],
      // C5e: shell-dependent (bash assigns under `time`; dash keeps a prefix assignment on a special builtin): unreadable
      ['R5-i', 'na', 'x=../docs/report.md; time x=other.md; cp base/report.md scratch/$x', ['zsh', 'dash'], wrapper('time')],
      ['R5-k', 'na', 'x=other.md; x=../docs/report.md :; cp base/report.md scratch/$x', ['dash'], prefix(':')],
      ['R5-m', 'na', 'x=other.md; x=../docs/report.md export y=1; cp base/report.md scratch/$x', ['dash'], prefix('export')],
      // C6a: `function NAME {` without parentheses is a definition (the attacker filed the same command twice, R6-a and R16-v)
      ['R6-a', 'na', 'function f { x=../docs/report.md; }; x=other.md; f; cp base/report.md scratch/$x', BZ, CALL],
      ['R16-v', 'na', 'function f { x=../docs/report.md; }; x=other.md; f; cp base/report.md scratch/$x', BZ, CALL],
      ['R16-v-out', 'out', 'function f { x=../../notes-api/docs/report.md; }; x=z; f; cp {WEB}/base/report.md {OUT}/scratch/$x', BZ, 'residual'],
      // C6b: a function whose name is a wrapper, called by that name
      ['R16-a', 'na', 'env() { x=../docs/report.md; }; x=other.md; env true; cp base/report.md scratch/$x', A, CALL],
      ['R16-c', 'na', 'command() { x=../docs/report.md; }; x=other.md; command true; cp base/report.md scratch/$x', A, CALL],
      ['R16-d', 'na', 'nice() { x=../docs/report.md; }; x=other.md; nice true; cp base/report.md scratch/$x', A, CALL],
      ['R16-e', 'na', 'sudo() { x=../docs/report.md; }; x=other.md; sudo true; cp base/report.md scratch/$x', A, CALL],
      ['R16-f', 'na', 'exec() { x=../docs/report.md; }; x=other.md; exec true; cp base/report.md scratch/$x', BZ, CALL],
      ['R16-g', 'na', 'nohup() { x=../docs/report.md; }; x=other.md; nohup true; cp base/report.md scratch/$x', A, CALL],
      ['R16-h', 'na', 'setsid() { x=../docs/report.md; }; x=other.md; setsid true; cp base/report.md scratch/$x', A, CALL],
      ['R16-a-out', 'out', 'env() { x=../../notes-api/docs/report.md; }; x=z; env true; cp {WEB}/base/report.md {OUT}/scratch/$x', A, 'residual'],
      // C6c: compounds of C6b with C3 and C7
      ['R16-y', 'na', 'x=other.md; env() { declare -n r=x; r=../docs/report.md; }; env true; cp base/report.md scratch/$x', B, ['literal', /a nameref|function body|a function the command defines/]],   // the body's nameref taints x first
      ['R16-z', 'na', 'x=other.md; env() { x[0]=../docs/report.md; }; env true; cp base/report.md scratch/$x', B, ['literal', /a subscript|function body|a function the command defines/]],
      // C7: a subscripted lvalue
      ['R7-a', 'na', 'x=other.md; x[0]=../docs/report.md; cp base/report.md scratch/$x', B, SUBSCRIPT],
      ['R7-b', 'na', 'x=other.md; x[1,8]=../docs/report.md; cp base/report.md scratch/$x', Z, SUBSCRIPT],
      ['R7-c', 'na', "x=other.md; printf -v 'x[0]' ../docs/report.md; cp base/report.md scratch/$x", B, SUBSCRIPT],
      ['R7-d', 'na', "x=other.md; read 'x[0]' <<< ../docs/report.md; cp base/report.md scratch/$x", B, SUBSCRIPT],
      ['R7-e', 'na', "x=other.md; declare 'x[0]=../docs/report.md'; cp base/report.md scratch/$x", B, SUBSCRIPT],
      ['R7-f', 'na', 'x=other.md; declare x[0]=../docs/report.md; cp base/report.md scratch/$x', B, SUBSCRIPT],
      ['R7-g', 'out', 'x=../../notes-api/docs/other.md; x[0]=../../notes-api/docs/report.md; cp {WEB}/base/report.md {OUT}/scratch/$x', B, 'residual'],
      ['R17-b', 'na', 'x=other.md; x[1,-1]=../docs/report.md; cp base/report.md scratch/$x', Z, SUBSCRIPT],
      ['R17-c', 'na', 'x=other.md; x[0]+=; x[0]=../docs/report.md; cp base/report.md scratch/$x', B, SUBSCRIPT],
    ];
    assert.equal(rows.length, 77, 'the attacker\'s 77 rows');
    let n = 0;
    const tally = { name: 0, literal: 0, residual: 0 };
    for (const [id, cwd, raw, shells, expect] of rows) {
      if (raw.includes('~daemon') && !hasDaemon) { console.error(`NOT RUN: this runner has no user daemon with a home, so ${id} did not run`); continue; }
      const cmd = w.fill(raw);
      const at = w.cwds[cwd];
      const h = w.hook(cmd, at);
      n++;
      if (expect === 'residual') {
        assert.equal(h.status, 0, `${id}: from a cwd in no project a word the rule leaves unreadable keeps the cwd rule (the ruled residual): ${cmd}: ${h.reason}`);
        const ex = extractWriteTargets(cmd, at);
        assert.ok(ex.unresolved.length > 0 && ex.targets.length === 0, `${id}: the word is opaque, not resolved (nothing in model is read): unresolved ${JSON.stringify(ex.unresolved.map((u) => u.raw))}, targets ${JSON.stringify(ex.targets)}`);
        tally.residual++;
      } else {
        assert.equal(h.status, 2, `${id}: the hook refuses: ${cmd}: ${h.reason}`);
        assert.ok(!/\u2014/.test(h.reason) && !ROMP_NOUNS.test(h.reason.split(w.W).join('<w>')), `${id}: no em dash, no romp noun`);
        if (expect === 'name') { assert.match(h.reason, BY_NAME_RE, `${id}: the value resolves and the write is refused by name: ${h.reason.split('\n')[0]}`); tally.name++; }
        else { const named = expect[1] instanceof RegExp ? expect[1].test(h.reason) : h.reason.includes(expect[1]); assert.ok(NOT_LITERAL.test(h.reason) && named, `${id}: refused as not literal, the reason naming the construct (${expect[1]}): ${h.reason.split('\n')[0]}`); tally.literal++; }
      }
      for (const shell of shellsFor(shells, id)) {
        const r = w.run(cmd, at, shell);
        assert.equal(r.changed, true, `${id}: run unguarded, ${shell} writes the tracked subset: ${cmd}: ${r.stderr}`);
      }
    }
    console.log(`# the sixth pass's attacker: ${n} rows run; refused by name ${tally.name}, refused as not literal with the construct named ${tally.literal}, the ruled residual from a cwd in no project ${tally.residual}`);
    assert.equal(n, hasDaemon ? 77 : 75);
    if (hasDaemon) assert.deepEqual(tally, { name: 18, literal: 49, residual: 10 });
  } finally { process.env.HOME = savedHome; w.rm(); }
});

test("the attacker's twins keep their verdicts, and the reviewer's four false refusals are priced: a `~/` value resolves through HOME at no cost; `declare -i x=5` (and -a) then $x, `let x=5` then $x, a pipeline-tail assignment (which zsh keeps) and a piped plain group then $x refuse from the tracked cwd although the shell's value was known; a plain group runs in this shell; `unset` frees a name for a plain write after it unless a nameref points at it", () => {
  const w = sixthPassWorld();
  const savedHome = process.env.HOME;
  process.env.HOME = w.HOME;
  try {
    const NA = w.NA;
    const A = ['bash', 'zsh', 'dash'];
    // [id, command, the verdict: allow (run in every shell, the tracked subset unchanged), name (refused by name), refuse (refused, not by name)]
    const twins = [
      ['R1-T1', 'x="~/../notes-api/docs/report.md"; cp base/report.md $x', 'allow'],   // a quoted tilde is text in the shell too
      ['R1-T2', 'x=~/x.md; cp base/report.md $x', 'allow'],                            // resolved through HOME, lands in the home
      ['R2-T1', 'declare -u x=../docs/report.md; cp base/report.md scratch/$x', 'refuse'],   // the shell writes an uppercase path that is not there
      ['R2-T2', 'declare -x x=../docs/report.md; cp base/report.md scratch/$x', 'name'],
      ['R2-T3', 'declare -g x=../docs/report.md; cp base/report.md scratch/$x', 'name'],
      ['R2-T4', 'declare -- x=../docs/report.md; cp base/report.md scratch/$x', 'name'],
      ['R3-T1', 'x=other.md; declare -n r=y; r=../docs/report.md; cp base/report.md scratch/$x', 'allow'],   // a nameref to another name
      ['R3-T2', 'x=other.md; local -n r=x; r=../docs/report.md; cp base/report.md scratch/$x', 'allow'],     // `local` at the top level: bash and dash reject it, zsh rejects -n
      ['R4-T1', 'h=y; export $h=../docs/report.md; x=other.md; cp base/report.md scratch/$x', 'allow'],      // an assembled name that resolves to another name
      ['R5-T1', 'x=../docs/report.md; (x=other.md); cp base/report.md scratch/$x', 'refuse'],
      ['R5-T2', 'x=../docs/report.md; x=other.md | cat; cp base/report.md scratch/$x', 'refuse'],
      ['R5-T3', 'x=../docs/report.md; x=other.md & wait; cp base/report.md scratch/$x', 'refuse'],
      ['R5-T4', 'x=../docs/report.md; true && x=other.md; cp base/report.md scratch/$x', 'refuse'],
      ['R5-T5', 'x=../docs/report.md; $(x=other.md); cp base/report.md scratch/$x', 'refuse'],
      ['R5-T6', 'x=../docs/report.md; y=$(x=other.md; echo); cp base/report.md scratch/$x', 'refuse'],
      ['R5-T7', 'x=../docs/report.md; cat <(x=other.md); cp base/report.md scratch/$x', 'refuse'],
      ['R5-T8', "x=../docs/report.md; sh -c 'x=other.md'; cp base/report.md scratch/$x", 'refuse'],   // the quoted script is an assignment-shaped argument of sh: it taints x (the inner shell cannot write the outer x, so the refusal is on the safe side), where before the fresh scope alone kept x and the refusal was by name
      ['R5-T9', "x=../docs/report.md; bash -c 'x=other.md'; cp base/report.md scratch/$x", 'refuse'],
      ['R5-T10', 'x=../docs/report.md; if x=other.md; then :; fi; cp base/report.md scratch/$x', 'refuse'],
      ['R5-T11', 'x=../docs/report.md; { x=other.md; } > /dev/null; cp base/report.md scratch/$x', 'allow'],   // a plain group runs in this shell
      ['R5-T12', 'x=../docs/report.md; { x=other.md; }; cp base/report.md scratch/$x', 'allow'],
      ['R5-T13', 'x=../docs/report.md; x=zz cp base/report.md scratch/$x', 'name'],                           // a prefix expands the old value in its own command
      ['R5-j', 'x=../docs/report.md; ! x=other.md; cp base/report.md scratch/$x', 'allow'],
      ['R16-T1', 'f() { x=../docs/report.md; }; x=other.md; f; cp base/report.md scratch/$x', 'refuse'],
      ['R16-w', 'function f() { x=../docs/report.md; }; x=other.md; f; cp base/report.md scratch/$x', 'refuse'],
      ['R7-T1', 'x=(../docs/report.md); cp base/report.md scratch/$x', 'refuse'],
      ['R7-T2', 'declare -a x=(../docs/report.md); cp base/report.md scratch/$x', 'refuse'],   // the report's C7 twin: the -a flag taints, bash and zsh write through the array's first element
      ['R17-j', 'x=other.md; export x=../docs/report.md y=$x; cp base/report.md scratch/$y', 'allow'],   // the shells expand $x before either declaration word is assigned
      ['R17-k', 'x=other.md; declare x=../docs/report.md y=$x; cp base/report.md scratch/$y', 'allow'],
      ['R11-d', 'x=other.md; y=$x; x=../docs/report.md; cp base/report.md scratch/$y', 'allow'],
      ['R11-e', "y=../docs/report.md; x='$y'; cp base/report.md scratch/$x", 'allow'],                      // a literal dollar in a value
      ['UNSET-1', 'declare -l x=AAA; unset x; x=../docs/REPORT.MD; cp base/report.md scratch/$x', 'allow'],  // unset drops the attribute: the plain write after it is readable, and lands on the untracked uppercase file
      ['UNSET-2', 'x=other.md; declare -n r=x; unset x; x=../docs/report.md; cp base/report.md scratch/$x', 'refuse'],   // a name a nameref points at is not freed (bash writes it through r after the unset)
    ];
    for (const [id, raw, want] of twins) {
      const cmd = w.fill(raw);
      const h = w.hook(cmd, NA);
      if (want === 'allow') {
        assert.equal(h.status, 0, `${id}: allowed: ${cmd}: ${h.reason}`);
        const shells = id === 'R3-T1' || id === 'R3-T2' ? ['bash'] : id === 'R17-k' || id === 'UNSET-1' ? ['bash', 'zsh'] : A;
        for (const shell of shellsFor(shells, id)) {
          const r = w.run(cmd, NA, shell);
          assert.equal(r.changed, false, `${id}: run unguarded, ${shell} leaves the tracked subset as it was: ${cmd}: ${r.stderr}`);
        }
        if (id === 'R1-T2') for (const shell of shellsFor(A, id)) { w.run(cmd, NA, shell); assert.ok(fs.existsSync(path.join(w.HOME, 'x.md')), `${id}: ${shell} landed the copy in the home the value resolves through`); }
      } else {
        assert.equal(h.status, 2, `${id}: refused: ${cmd}`);
        if (want === 'name') assert.match(h.reason, BY_NAME_RE, `${id}: by name: ${h.reason.split('\n')[0]}`);
        else assert.ok(NOT_LITERAL.test(h.reason) || BY_NAME_RE.test(h.reason), `${id}: refused (as not literal, or by name where the value the shell keeps is the tracked file): ${h.reason.split('\n')[0]}`);
      }
    }
    // the costs the reviewer asked to see priced (17:24Z), each shell's behaviour by EXECUTION (round 5, 2026-09-20, bash 5.2, zsh
    // 5.9, dash 0.5.12; the comment here had said zsh writes scratch/report.md for -a, which it does not). (1) a `~/` value:
    // resolved, no cost (R1-T2 above). (2) `declare -i x=5` then $x: refused as not literal, the reason naming the flag, while bash
    // and zsh write scratch/5 and dash, which has no declare, copies onto scratch/report.md (x empty); `declare -a x=5` and
    // `declare -A x=5`: bash writes scratch/5, zsh rejects the scalar value for an array ("inconsistent type for assignment") and
    // stops the command list, writing nothing, dash copies onto scratch/report.md. (3) a pipeline-tail assignment: refused, while
    // zsh keeps the tail's assignment (b.log) and bash and dash do not (a.log), all untracked. (4) a piped plain group: refused,
    // while every shell keeps the old value (a.log). And `let x=5` then $x, a construct of the same shape: refused, while bash and
    // zsh write scratch/5 and dash, which has no let, copies onto scratch/other.md.
    // [command, the construct the reason names, the shells run (each writes nothing tracked), the untracked file that shell writes, or null]
    const costs = [
      ['declare -i x=5; cp base/report.md scratch/$x', 'a `declare` flag that can change the value or what the name is (-i)', ['bash', 'zsh'], path.join(NA, 'scratch', '5')],
      ['declare -i x=5; cp base/report.md scratch/$x', 'a `declare` flag that can change the value or what the name is (-i)', ['dash'], path.join(NA, 'scratch', 'report.md')],
      ['declare -a x=5; cp base/report.md scratch/$x', 'a `declare` flag that can change the value or what the name is (-a)', ['bash'], path.join(NA, 'scratch', '5')],
      ['declare -a x=5; cp base/report.md scratch/$x', 'a `declare` flag that can change the value or what the name is (-a)', ['zsh'], null],   // zsh stops on the flag: nothing written (asserted below)
      ['declare -a x=5; cp base/report.md scratch/$x', 'a `declare` flag that can change the value or what the name is (-a)', ['dash'], path.join(NA, 'scratch', 'report.md')],
      ['declare -A x=5; cp base/report.md scratch/$x', 'a `declare` flag that can change the value or what the name is (-A)', ['bash'], path.join(NA, 'scratch', '5')],
      ['declare -A x=5; cp base/report.md scratch/$x', 'a `declare` flag that can change the value or what the name is (-A)', ['zsh'], null],
      ['declare -A x=5; cp base/report.md scratch/$x', 'a `declare` flag that can change the value or what the name is (-A)', ['dash'], path.join(NA, 'scratch', 'report.md')],
      ['x=other.md; let x=5; cp base/report.md scratch/$x', 'an assignment-shaped word of `let`', ['bash', 'zsh'], path.join(NA, 'scratch', '5')],
      ['x=other.md; let x=5; cp base/report.md scratch/$x', 'an assignment-shaped word of `let`', ['dash'], path.join(NA, 'scratch', 'other.md')],
      ['x=a; cat </dev/null | x=b; printf x > {OUT}/scratch/$x.log', 'a pipeline, whose members bash and dash run in a subshell', ['bash', 'zsh', 'dash'], null],
      ['x=a; { x=b; } | cat; printf x > {OUT}/scratch/$x.log', 'a `{ }` group that is piped', ['bash', 'zsh', 'dash'], null],
      // the `export x` item (tests-1, round 4): the plain `x=..; export x` was refused before the readability rule too, as not
      // literal, so the rule changed its REASON here and did not add the refusal; the spelling it newly refuses is the export
      // followed by a later plain write, where every shell holds the later value (the corpus row re-anchored on it)
      ['x=scratch/kept.md; export x; cp base/report.md $x', 'a `export` of the name alone, which may change how it is read', ['bash', 'zsh', 'dash'], path.join(NA, 'scratch', 'kept.md')],
      ['x=a; export x; x=scratch/kept.md; cp base/report.md $x', 'a `export` of the name alone, which may change how it is read', ['bash', 'zsh', 'dash'], path.join(NA, 'scratch', 'kept.md')],
    ];
    for (const [raw, construct, shells, lands] of costs) {
      const cmd = w.fill(raw);
      const h = w.hook(cmd, NA);
      assert.equal(h.status, 2, `the cost row is refused: ${cmd}: ${h.reason}`);
      assert.ok(NOT_LITERAL.test(h.reason) && h.reason.includes(construct) && h.reason.includes('so I do not read `$x` here'), `the reason names the construct: ${h.reason.split('\n')[0]}`);
      for (const shell of shellsFor(shells, `the cost row ${raw}`)) {
        const r = w.run(cmd, NA, shell);
        assert.equal(r.changed, false, `${shell}: the shell wrote nothing tracked (a false refusal, recoverable in one step): ${cmd}: ${r.stderr}`);
        if (lands) assert.ok(fs.existsSync(lands), `${shell} wrote the untracked ${path.basename(lands)}: the shell's value differs from the guard's reading`);
        else if (shell === 'zsh' && /^declare -[aA]/.test(raw)) { assert.notEqual(r.status, 0, `zsh rejects the scalar value for the array flag: ${r.stderr}`); assert.deepEqual(fs.readdirSync(path.join(NA, 'scratch')).sort(), ['keep.md', 'other.md'], 'and writes nothing'); }
      }
    }
    const tail = w.fill('x=a; cat </dev/null | x=b; printf x > {OUT}/scratch/$x.log');
    for (const shell of shellsFor(['bash', 'zsh', 'dash'], 'the pipeline tail')) {
      w.run(tail, NA, shell);
      assert.equal(fs.existsSync(path.join(w.OUT, 'scratch', shell === 'zsh' ? 'b.log' : 'a.log')), true, `${shell} ${shell === 'zsh' ? 'keeps' : 'drops'} the tail's assignment`);
    }
  } finally { process.env.HOME = savedHome; w.rm(); }
});

test('the readability rule itself, not its thirteen classes: a construct that writes the name through a mechanism the hook does not enumerate (zsh print -v, zsh ${x::=..}, an arithmetic body, zsh integer and float declarations) makes the name unreadable, one of them picked at random and then every one; the shells that have the construct write through it while the guard reads the old value', () => {
  const w = sixthPassWorld();
  const savedHome = process.env.HOME;
  process.env.HOME = w.HOME;
  try {
    const hookSource = fs.readFileSync(HOOK, 'utf8');
    for (const name of ["'print'", "'integer'", "'float'", "'::='", 'case \'print\'', 'case \'integer\'']) assert.ok(!hookSource.includes(name), `the hook does not enumerate ${name}`);
    assert.ok(hookSource.includes(':*=/g'), 'the expansion rule is one pattern over `=`, `:=` and `::=`, not a list of operators');
    const UNLISTED = [
      { cmd: 'x=other.md; print -v x ../docs/report.md; cp base/report.md scratch/$x', shells: ['zsh'], construct: 'a word of `print` that names it', tracked: true },
      { cmd: 'x=other.md; : ${x::=../docs/report.md}; cp base/report.md scratch/$x', shells: ['zsh'], construct: 'a `${name=..}`, `${name:=..}` or `${name::=..}` expansion, which assigns it', tracked: true },
      { cmd: 'x=other.md; (( x = 5 )); cp base/report.md scratch/$x', shells: ['bash', 'zsh'], construct: 'an arithmetic body, which may assign it', tracked: false },
      { cmd: 'x=other.md; : $(( x = 5 )); cp base/report.md scratch/$x', shells: ['bash', 'zsh'], construct: 'an arithmetic body, which may assign it', tracked: false },
      { cmd: 'x=other.md; integer x=5; cp base/report.md scratch/$x', shells: ['zsh'], construct: 'an assignment-shaped word of `integer`', tracked: false },
      { cmd: 'x=other.md; float x=5; cp base/report.md scratch/$x', shells: ['zsh'], construct: 'an assignment-shaped word of `float`', tracked: false },
      // round 5 (extra4-5): the SCOPE half of the rule (no if, loop, case, select, subshell or function body), which the six rows
      // above could not see: a body that may not run, behind each construct that hid its head at round 4's head (`{`, `!`, `time`,
      // a select body, a function body inside a group, a subshell) and under each closer (fi, done, esac). Every row was a live
      // false ALLOW at that head; the shells listed keep the tracked path and write the tracked file (dash rejects `time` before a
      // compound command and has no select).
      { cmd: 'x=../docs/report.md; { if false; then x=other.md; fi; }; cp base/report.md scratch/$x', shells: ['bash', 'zsh', 'dash'], construct: 'an if, loop, case or function body, or a subshell', tracked: true },
      { cmd: 'x=../docs/report.md; ! if false; then x=other.md; fi; cp base/report.md scratch/$x', shells: ['bash', 'zsh', 'dash'], construct: 'an if, loop, case or function body, or a subshell', tracked: true },
      { cmd: 'x=../docs/report.md; time if false; then x=other.md; fi; cp base/report.md scratch/$x', shells: ['bash', 'zsh'], construct: 'an if, loop, case or function body, or a subshell', tracked: true },
      { cmd: 'x=../docs/report.md; select y in a; do x=other.md; done </dev/null; cp base/report.md scratch/$x', shells: ['bash', 'zsh'], construct: 'an if, loop, case or function body, or a subshell', tracked: true },
      { cmd: 'x=../docs/report.md; { f() { x=other.md; }; }; cp base/report.md scratch/$x', shells: ['bash', 'zsh', 'dash'], construct: 'an if, loop, case or function body, or a subshell', tracked: true },
      { cmd: 'x=../docs/report.md; (x=other.md); cp base/report.md scratch/$x', shells: ['bash', 'zsh', 'dash'], construct: 'an if, loop, case or function body, or a subshell', tracked: true },
      { cmd: 'x=../docs/report.md; ! while false; do x=other.md; done; cp base/report.md scratch/$x', shells: ['bash', 'zsh', 'dash'], construct: 'an if, loop, case or function body, or a subshell', tracked: true },
      { cmd: 'x=../docs/report.md; ! until true; do x=other.md; done; cp base/report.md scratch/$x', shells: ['bash', 'zsh', 'dash'], construct: 'an if, loop, case or function body, or a subshell', tracked: true },
      { cmd: 'x=../docs/report.md; ! case a in b) x=other.md;; esac; cp base/report.md scratch/$x', shells: ['bash', 'zsh', 'dash'], construct: 'an if, loop, case or function body, or a subshell', tracked: true },
      { cmd: 'x=../docs/report.md; ! for y in; do x=other.md; done; cp base/report.md scratch/$x', shells: ['bash', 'zsh', 'dash'], construct: 'an if, loop, case or function body, or a subshell', tracked: true },
    ];
    const pick = UNLISTED[crypto.randomInt(UNLISTED.length)];
    console.log(`# the rule pin's random pick: ${pick.cmd}`);
    for (const c of [pick, ...UNLISTED]) {
      const h = w.hook(c.cmd, w.NA);
      assert.equal(h.status, 2, `an unlisted write makes the name unreadable: ${c.cmd}: ${h.reason}`);
      assert.ok(NOT_LITERAL.test(h.reason) && h.reason.includes(c.construct) && h.reason.includes('so I do not read `$x` here'), `the reason names the construct: ${c.cmd}: ${h.reason.split('\n')[0]}`);
      for (const shell of shellsFor(c.shells, c.cmd)) {
        const r = w.run(c.cmd, w.NA, shell);
        if (c.tracked) assert.equal(r.changed, true, `${shell} writes the tracked file through the construct: ${c.cmd}: ${r.stderr}`);
        else { assert.equal(r.changed, false, `${shell}: nothing tracked: ${c.cmd}`); assert.ok(fs.readdirSync(path.join(w.NA, 'scratch')).some((n) => /^5/.test(n)), `${shell} wrote scratch/5 (zsh's float spells it 5.000000000): its value of x is not the one the guard would have read`); }
      }
    }
  } finally { process.env.HOME = savedHome; w.rm(); }
});

test('found with the fix, four more live overwrites of the same rule at 86c0643ec: an eval that assembles HOME= then a `~` write (the poison of an eval, a source or a function call now covers HOME, PWD and OLDPWD), a piped `{ cd docs; }` group whose cd the guard followed (the group frame restores the directory), and zsh\'s `print -v` and `${x::=..}` (the rule pin above); each refused, and each writes the tracked file when run unguarded', () => {
  const w = sixthPassWorld();
  const savedHome = process.env.HOME;
  process.env.HOME = w.HOME;
  try {
    const evalRow = w.fill("e=$(printf 'HO%s' ME={NA}/notes); eval \"$e\"; printf poison > ~/n1.md");
    const h1 = w.hook(evalRow, w.NA);
    assert.equal(h1.status, 2, `refused: ${evalRow}: ${h1.reason}`);
    assert.ok(/an earlier `eval` may assign any name/.test(h1.reason) && /(I cannot read here|no longer name a directory I can read)/.test(h1.reason), `the reason names the eval: ${h1.reason.split('\n')[0]}`);
    for (const shell of shellsFor(['bash', 'zsh', 'dash'], 'the eval HOME row')) assert.equal(w.run(evalRow, w.NA, shell).changed, true, `${shell} writes the tracked note through the eval'd HOME`);
    assert.equal(w.hook(w.fill("e=$(printf 'HO%s' ME={NA}/notes); echo \"$e\"; printf x > ~/n1.md"), w.NA).status, 0, 'the twin that only echoes the string resolves ~ through the guard\'s home, outside every project: allowed');
    const groupRow = '{ cd docs; } | cat; cp base/report.md docs/report.md';
    const h2 = w.hook(groupRow, w.NA);
    assert.equal(h2.status, 2, `refused: ${groupRow}: ${h2.reason}`);
    assert.match(h2.reason, BY_NAME_RE, 'the piped group ran in a subshell, so the copy is judged from the cwd and refused by name');
    for (const shell of shellsFor(['bash', 'zsh', 'dash'], 'the piped cd group')) assert.equal(w.run(groupRow, w.NA, shell).changed, true, `${shell} writes the tracked file from the cwd the group did not move`);
    assert.equal(w.hook('{ cd docs; }; cp base/report.md docs/report.md', w.NA).status, 0, 'the plain group moves the shell: from docs/ the target is docs/docs/report.md, untracked and absent, so the copy is allowed (cp then fails on the missing folder)');
    assert.equal(w.hook('{ cd docs; }; cp ../base/report.md report.md', w.NA).status, 2, 'after a plain group\'s cd a relative write lands in docs/: refused by name');
  } finally { process.env.HOME = savedHome; w.rm(); }
});

test("the addendum, item 1: a plain top-level `HOME=<path>` assignment is the one readable write to HOME, read for the commands after it (a `~` write, `$HOME`, a bare `cd`, a `$(...)`, a script handed to a named shell, which inherits the exported value), so the write it leads to is judged by name; the prefix form `HOME=<path> cmd` stays unreadable with its own reason, since the shells expand that command's own `~` and `$HOME` first (measured: the write lands in the previous home) while a script run under it sees the new HOME (measured: the inner shell writes the tracked note); every other form stays refused as before", () => {
  const w = sixthPassWorld();
  const savedHome = process.env.HOME;
  process.env.HOME = w.HOME;
  try {
    const A = ['bash', 'zsh', 'dash'];
    const n1 = path.join(w.NA, 'notes', 'n1.md');
    // readable: resolved through the assigned HOME, refused by name on the tracked note; every shell writes it
    // (the relative `HOME=notes; cd; ...` row: the dollar matrix's row 2847 at the addendum's first head moved the guard to the bare
    // string `notes` and bash wrote the tracked note under the cwd; a bare cd after a plain HOME= is a `cd <dir>` against the cwd)
    for (const raw of ['HOME={NA}/notes; printf poison > $HOME/n1.md', 'HOME={NA}/notes; printf poison > ~/n1.md', 'HOME={NA}/notes; cd; printf poison > n1.md', 'HOME=notes; cd; printf poison > n1.md', "HOME={NA}/notes; sh -c 'printf poison > ~/n1.md'", 'HOME={NA}/notes; echo $(printf poison > ~/n1.md)', 'HOME={NA}/notes; x=~/n1.md; printf poison > $x']) {
      const cmd = w.fill(raw);
      const h = w.hook(cmd, w.NA);
      assert.ok(h.status === 2 && BY_NAME_RE.test(h.reason) && h.reason.includes(n1), `the plain HOME= write resolves and the write is refused by name: ${cmd}: ${h.reason.split('\n')[0]}`);
      for (const shell of shellsFor(A, raw)) assert.equal(w.run(cmd, w.NA, shell).changed, true, `${shell} writes the tracked note through the assigned HOME: ${cmd}`);
    }
    // a bare `pushd` is not a bare `cd` (found here, a live overwrite since before this pass): bash exchanges the stack's top two entries and
    // fails with one (the shell stays), dash has no pushd (it stays), zsh goes home; the guard now leaves the directory unknown and refuses
    // the relative write, which bash and dash land on the tracked file from the cwd they never left
    const pushdRow = 'pushd; cp base/report.md docs/report.md';
    const hpd = w.hook(pushdRow, w.NA);
    assert.ok(hpd.status === 2 && /an earlier bare `pushd` exchanges the top two directories of the stack/.test(hpd.reason) && /the directory it is relative to is not known/.test(hpd.reason), `a bare pushd leaves the directory unknown: ${hpd.reason.split('\n')[0]}`);
    for (const shell of shellsFor(A, 'a bare pushd')) assert.equal(w.run(pushdRow, w.NA, shell).changed, shell !== 'zsh', `${shell}: ${shell === 'zsh' ? 'went home, nothing tracked written' : 'stayed put and wrote the tracked file'}`);
    assert.equal(w.hook('HOME=notes; pushd; printf poison > n1.md', w.NA).status, 2, 'a bare pushd after a plain HOME= is unknown too, not a move to HOME');
    // a relative HOME= naming a directory that is not there: the cd fails and the shell stays, so the guard leaves the directory unknown and refuses the relative write (the safe side), the shells writing the untracked n1.md in the cwd
    const missing = w.hook('HOME=nosuch; cd; printf x > n1.md', w.NA);
    assert.ok(missing.status === 2 && /names a directory the command cannot enter when I check it/.test(missing.reason), `a bare cd to a HOME that is not there leaves the directory unknown: ${missing.reason.split('\n')[0]}`);
    for (const shell of shellsFor(A, 'a bare cd to a missing HOME')) assert.equal(w.run('HOME=nosuch; cd; printf x > n1.md', w.NA, shell).changed, false, `${shell}: the cd failed and the write landed in the cwd, untracked`);
    // readable and harmless: the value leads outside every project, so the write is allowed and lands there
    const outRow = w.fill('HOME={OUT}/h; mkdir -p ~; printf x > ~/seed.md');
    assert.equal(w.hook(outRow, w.NA).status, 0, `allowed: ${outRow}`);
    assert.deepEqual(extractWriteTargets(outRow, w.NA).targets.map((t) => t.path), [path.join(w.OUT, 'h', 'seed.md')], 'the `~` resolves through the assigned HOME');
    for (const shell of shellsFor(A, 'the readable HOME write outside every project')) { const r = w.run(outRow, w.NA, shell); assert.equal(r.changed, false); assert.equal(fs.readFileSync(path.join(w.OUT, 'h', 'seed.md'), 'utf8'), 'x', `${shell} landed the write where the assigned HOME says`); }
    // the prefix form: refused with its own reason, and the frame that says which HOME writes the guard reads
    const prefixRow = w.fill('HOME={NA}/notes printf poison > ~/n1.md');
    const hp = w.hook(prefixRow, w.NA);
    assert.equal(hp.status, 2, `the prefix form is refused: ${prefixRow}`);
    assert.ok(/sets HOME as a prefix on a command/.test(hp.reason) && /apply after expanding that command's own `\$HOME` and `~`/.test(hp.reason) && /after a plain `HOME=<path>` assignment of its own at the top level of the command; in no other form/.test(hp.reason), `the reason says what the prefix form does and which form the guard reads: ${hp.reason.split('\n')[0]}`);
    assert.ok(!/may reassign HOME before this runs/.test(hp.reason) && !/never a variable the command sets/.test(hp.reason), 'the sentence that said the guard never reads a variable the command sets is gone');
    for (const shell of shellsFor(A, 'the prefix form in the shells')) { const r = w.run(prefixRow, w.NA, shell); assert.equal(r.changed, false, `${shell}: the prefix applies after the tilde expanded, so the write went to the previous home (a false refusal, ruled to stay)`); assert.ok(fs.existsSync(path.join(w.HOME, 'n1.md')), `${shell} wrote the previous home's n1.md`); }
    const prefixScript = w.fill("HOME={NA}/notes bash -c 'printf poison > ~/n1.md'");
    assert.equal(w.hook(prefixScript, w.NA).status, 2, 'the prefix form before a script is refused');
    for (const shell of shellsFor(A, 'the prefix form before a script')) assert.equal(w.run(prefixScript, w.NA, shell).changed, true, `${shell}: the inner shell runs under the new HOME and writes the tracked note, which is why the prefix form stays unreadable`);
    // every other form stays as it was: unreadable, refused with rule (a)'s reason
    assert.match(w.hook(w.fill('HOME={NA}/notes && printf poison > ~/n1.md'), w.NA).reason, BY_NAME_RE, 'the assignment before a && is this shell\'s own (the && gates the command after it), so it is read and the write refused by name');
    for (const raw of ['export HOME={NA}/notes; printf poison > $HOME/n1.md', 'HOME=~/sub; printf poison > ~/n1.md', 'HOME=; printf poison > ~/n1.md', 'true && HOME={NA}/notes; printf poison > ~/n1.md', 'if true; then HOME={NA}/notes; fi; printf poison > ~/n1.md']) {
      const h = w.hook(w.fill(raw), w.NA);
      assert.ok(h.status === 2 && /names HOME outside an expansion/.test(h.reason) && !BY_NAME_RE.test(h.reason), `not the plain form, so HOME stays unreadable: ${raw}: ${h.reason.split('\n')[0]}`);
    }
    // the grammar: the lexer's home text is replaced by the assigned value, and a fresh shell inherits it
    assert.deepEqual(extractWriteTargets(w.fill("HOME={NA}/notes; sh -c 'printf poison > ~/n1.md'"), w.NA).targets.map((t) => t.path), [n1]);
    assert.deepEqual(extractWriteTargets(w.fill('HOME={NA}/notes; printf poison > ~/n1.md'), w.NA).targets.map((t) => t.path), [n1]);
  } finally { process.env.HOME = savedHome; w.rm(); }
});

test("the addendum, item 2: a cd under `builtin`, `command` or `time` is still refused as a directory the guard cannot know, but the reason says what each shell does (measured: bash and zsh move under `builtin`, bash and dash under `command`, bash and zsh under `time`) where it said the shell does not move; under `env` an external cd runs and moves nothing", () => {
  const w = sixthPassWorld();
  const savedHome = process.env.HOME;
  process.env.HOME = w.HOME;
  try {
    const rows = [
      ['builtin', "runs the shell's own cd in bash and zsh, which moves the shell, and no command in dash", { bash: true, zsh: true, dash: false }],
      ['command', "runs the shell's own cd in bash and dash, which moves the shell, and an external cd in zsh", { bash: true, zsh: false, dash: true }],
      ['time', 'is a reserved word in bash and zsh, so the cd runs in this shell and moves it, and an external command in dash', { bash: true, zsh: true, dash: false }],
      ['env', 'an external `cd` that moves nothing in this shell', { bash: false, zsh: false, dash: false }],
    ];
    for (const [wrapper, text, moves] of rows) {
      const cmd = `${wrapper} cd docs; cp ../base/report.md report.md`;
      const h = w.hook(cmd, w.NA);
      assert.equal(h.status, 2, `refused: ${cmd}: ${h.reason}`);
      assert.ok(/the directory it is relative to is not known/.test(h.reason) && h.reason.includes(`runs under a wrapper (\`${wrapper}\`)`) && h.reason.includes(text), `the reason says what the shells do under ${wrapper}: ${h.reason.split('\n')[0]}`);
      assert.ok(!h.reason.includes('that does not exist, so the shell does not move'), 'the old text is gone');
      for (const shell of shellsFor(['bash', 'zsh', 'dash'], `${wrapper} cd`)) {
        const r = w.run(cmd, w.NA, shell);
        assert.equal(r.changed, moves[shell], `${shell}: under ${wrapper} the cd ${moves[shell] ? 'moves the shell and the copy lands on the tracked file' : 'moves nothing and the copy lands in the cwd'}: ${r.stderr}`);
      }
    }
  } finally { process.env.HOME = savedHome; w.rm(); }
});

// The self-check reads this file's lines, keyed on the RULE since round 5 (2026-09-20; it was keyed on a closed list of shell-list
// identifiers, `shells|SHELLS|A|B|BZ|BD|Z`, plus two call shapes, so a leg over a list by any other name, a `.forEach` or `.map`,
// or a ternary-picked shell escaped it while the test claimed every leg was covered). A real-shell leg is a call of a shell runner
// (spawnSync, overwrites, lands, w.run, sh, out) on a line that spells a shell ('bash', 'zsh' or 'dash'; a comparison such as
// `shell === 'zsh'` is not a spelling), or a loop (for-of, .forEach, .map) over a literal list holding one or over an identifier
// this file declares as such a list, on a line without shellsFor, HAS_SHELL or SHELL_PROBE (a comment line does not count). The
// scan is the HINT that names the line; the GUARANTEE is the live-value wrapper on spawnSync at the top of this file, which
// throws by name when any call reaches a shell the probe declined, whatever the list is called and however the leg loops.
const legsOutsideProbe = (lines) => {
  const declared = new Set();
  for (const l of lines) { const m = l.match(/^\s*(?:const|let) ([A-Za-z_$][\w$]*) = \[[^\]]*'(?:bash|zsh|dash)'[^\]]*\]/); if (m) declared.add(m[1]); }
  const names = [...declared].map((n) => n.replace(/\$/g, '\\$')).join('|');
  const overDeclared = names ? new RegExp(`for \\(const \\w+ of (?:${names})\\)|\\b(?:${names})\\.(?:forEach|map)\\(`) : null;
  const spellsShell = (l) => /'(?:bash|zsh|dash)'/.test(l.replace(/[!=]==? '(?:bash|zsh|dash)'/g, ''));
  return lines.map((l, i) => `${i + 1}: ${l.trim()}`).filter((l) => {
    if (/^\d+: \/\//.test(l) || /HAS_SHELL|shellsFor\(|SHELL_PROBE/.test(l)) return false;
    if (/\b(?:spawnSync|overwrites|lands|run|sh|out)\(/.test(l) && spellsShell(l)) return true;
    if (/for \(const \w+ of \[[^\]]*'(?:bash|zsh|dash)'|\[[^\]]*'(?:bash|zsh|dash)'[^\]]*\]\.(?:forEach|map)\(/.test(l)) return true;
    return !!(overDeclared && overDeclared.test(l));
  });
};

test('the addendum, item 4, and round 5: every real-shell evidence leg of this file goes through the one probe, whose spawnSync wrapper throws by name for a shell it declined (pinned against a synthetic table), so a runner without a shell, or with a bash below the 4.3 floor, prints a NOT RUN line naming the shell and the version per leg and never passes a leg in silence or reds with a value mismatch; the scan over the source is keyed on the rule (a runner call spelling a shell, a loop over a shell list by any name) and pinned against synthetic lines; the line itself is pinned in-process and as a process, this file run with a zsh stub that exits 1 first on PATH', () => {
  const src = fs.readFileSync(fileURLToPath(import.meta.url), 'utf8').split('\n');
  assert.deepEqual(legsOutsideProbe(src), [], 'a real-shell leg outside the probe');
  assert.equal(typeof HAS_SHELL.bash, 'boolean');
  assert.equal(typeof HAS_SHELL.zsh, 'boolean');
  assert.equal(typeof HAS_SHELL.dash, 'boolean');
  assert.ok(SHELL_PROBE.bash.ok ? /^\d+\.\d+/.test(SHELL_PROBE.bash.version) : /is not on this runner|below the 4\.3/.test(SHELL_PROBE.bash.why), 'the probe read bash\'s version, or says why bash is declined');
  // the scan against synthetic lines: round 4's escapes (a list by another name, .forEach and .map, a ternary-picked shell, a bare
  // identifier list) are caught beside the seventh pass's, a guarded line, a comment and a comparison are not (the literal shell is
  // spelled Q here and filled in at run time, so the scan of this file does not read these lines as legs)
  // (every shell is spelled apart here, QB, QZ and QD, and filled in at run time, so the scan of this file does not read these lines as legs)
  const synthetic = [
    "const AZ2 = [QB, QZ];",
    "const LIST = [QB, QD];",
    "for (const s of AZ2) go(s);",
    "for (const zsh of [QZ]) go(zsh);",
    "for (const s of [QB, QZ, QD]) go(s);",
    "for (const shell of LIST) go(shell);",
    "spawnSync(QZ, ['-c', 'true']);",
    "w.run(cmd, NA, QZ);",
    "overwrites(QZ, 'a; b', 'why');",
    "AZ2.forEach((s) => go(s));",
    "[QB, QZ].map((s) => run(s, x));",
    "run(flag ? QZ : QB, x);",
    "for (const shell of shellsFor([QZ], 'x')) go(shell);",
    "// spawnSync(QZ, ['-c', 'true']) in a comment",
    "const ok = HAS_SHELL.zsh ? run(QZ, x) : null;",
    "const sh = (shell, cmd) => spawnSync(shell, shell === QZ ? ['-f', '-c', cmd] : ['-c', cmd]);",
  ].map((l) => l.replaceAll('QB', `'${['ba', 'sh'].join('')}'`).replaceAll('QZ', `'${['z', 'sh'].join('')}'`).replaceAll('QD', `'${['da', 'sh'].join('')}'`));
  assert.deepEqual(legsOutsideProbe(synthetic).map((l) => Number(l.split(':')[0])), [3, 4, 5, 6, 7, 8, 9, 10, 11, 12], 'ten unguarded legs flagged: the two declarations, the guarded line, the comment and the comparison not');
  // the line itself, in-process: a missing shell is reported once per leg through the reporter and dropped from the leg's list; a
  // present but too-old shell (the probe's record) is reported with the version found, the same loud line, never a value mismatch
  const lines = [];
  assert.deepEqual(shellsFor(['bash', 'zsh', 'dash'], 'a synthetic leg', { bash: true, zsh: false, dash: true }, (l) => lines.push(l)), ['bash', 'dash']);
  assert.equal(lines.length, 1, 'one line for the one missing shell');
  assert.match(lines[0], /^NOT RUN: real zsh is not on this runner, so its evidence leg did not run: a synthetic leg \(/, 'the loud line names the shell and the leg');
  assert.deepEqual(shellsFor(['zsh'], 'x', { zsh: true }, () => assert.fail('a present shell is not reported')), ['zsh']);
  const old = [];
  assert.deepEqual(shellsFor(['bash', 'dash'], 'a nameref leg', { bash: { ok: false, why: 'is 3.2.57(1)-release on this runner, below the 4.3 its legs need', version: '3.2.57(1)-release' }, dash: { ok: true, why: null } }, (l) => old.push(l)), ['dash']);
  assert.equal(old.length, 1);
  assert.match(old[0], /^NOT RUN: real bash is 3\.2\.57\(1\)-release on this runner, below the 4\.3 its legs need, so its evidence leg did not run: a nameref leg \(/, 'a too-old shell declines with the loud line naming the version');
  assert.deepEqual([probeShell('bash').ok, typeof probeShell('bash').version], [SHELL_PROBE.bash.ok, 'string'], 'the probe reads bash\'s version');
  // the live-value check: a spawn of a shell the probe declined throws by name, whatever the call shape; a shell it passed runs
  const calls = [];
  const guarded = guardedSpawn({ bash: true, zsh: false, dash: { ok: false, why: 'is 0.5.12 on this runner, below the 9.9 its legs need' } }, (...a) => { calls.push(a); return { status: 0 }; });
  assert.throws(() => guarded(['z', 'sh'].join(''), ['-c', 'true']), /a real-shell leg ran zsh outside the probe: real zsh is not on this runner; ask shellsFor first/);
  assert.throws(() => guarded('dash', ['-c', 'true']), /real dash is 0\.5\.12 on this runner, below the 9\.9 its legs need/);
  assert.equal(guarded('bash', ['-c', 'true']).status, 0);
  assert.equal(guarded(process.execPath, ['-e', '1']).status, 0, 'a command that is no shell passes through');
  assert.deepEqual(calls.map((a) => a[0]), ['bash', process.execPath]);
  // as a process: this file, run on `the addendum, item 2` alone with a zsh stub first on PATH, prints the line for each of that test's four legs and passes
  const stub = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-bash-guard-zshstub-'));
  const stubShell = ['z', 'sh'].join('');   // the stub's file name, spelled apart so this line is no leg to the scan above
  try {
    fs.writeFileSync(path.join(stub, stubShell), '#!/bin/sh\nexit 1\n', { mode: 0o755 });
    const env = { ...process.env, PATH: `${stub}:${process.env.PATH}` };
    delete env.NODE_TEST_CONTEXT;   // the runner marks its children with it, and a marked `node --test` runs no file ("called recursively")
    const child = spawnSync(process.execPath, ['--test', '--test-name-pattern=the addendum, item 2', fileURLToPath(import.meta.url)], { encoding: 'utf8', env, timeout: 180000 });
    const out = `${child.stdout}\n${child.stderr}`;
    const notRun = out.split('\n').filter((l) => /NOT RUN: real zsh is not on this runner, so its evidence leg did not run: (builtin|command|time|env) cd \(/.test(l));
    assert.equal(notRun.length, 4, `one NOT RUN line per zsh leg of the item-2 test (the runner forwards stderr with a leading #): ${out.slice(0, 2000)}`);
    assert.equal(child.status, 0, `the file passes without zsh (the legs are not run, not failed): ${out.slice(-1500)}`);
    assert.match(child.stdout, /^# pass 1$/m, 'the one selected test passed');
    assert.match(child.stdout, /^# fail 0$/m);
  } finally { fs.rmSync(stub, { recursive: true, force: true }); }
});

// ── the seventh pass's attacker (2026-09-19, on 93bb93b68): the rule's own boundary ──
//
// Two misses, 0 structural (its report in the sweep notes, `quickfix-track-guard-attack1-pass7.md`, its rows in
// `quickfix-track-guard-atk7-rows.json`), and a sibling found while closing them. F2: a `{ }` group nested in a piped or
// backgrounded group (the frame opened for the first `{` and popped on the first `}`, so the piped outer brace was never a
// subshell boundary). F1: zsh's precommand modifiers `noglob`, `nocorrect` and `-`, read as commands named so, hiding the
// writer behind them. RO: a name made readonly then written by a declaration, an export or an unset, which bash and dash
// refuse and continue past with the readonly value while the guard adopted the later one. Every row runs through the hook as
// a process from the row's cwd and then unguarded in bash, zsh and dash over a fresh world, the tracked subset fingerprinted,
// and the test asserts EXACTLY which shells write (the shells that abort or fail on the word write nothing).

test("the seventh pass's attacker, F2: a `{ }` group nested in a piped or backgrounded group runs in a subshell at any nesting, so every name assigned inside it (a plain word or a declaration, at any depth) is unreadable and its cd is undone; the report's 7 rows, the `} }` and one-level declaration siblings found with them, and the twins (a plain nested group, a nested group before `&&`, a piped inner group) keep their verdicts; each refused row overwrites the tracked subset in the shells named and each allowed row leaves it", () => {
  const w = sixthPassWorld();
  const savedHome = process.env.HOME;
  process.env.HOME = w.HOME;
  try {
    const A = ['bash', 'zsh', 'dash'];
    const BZ = ['bash', 'zsh'];
    const PIPED = ['literal', 'a `{ }` group that is piped, which the shells run in a subshell'];
    const BG = ['literal', 'a `{ }` group that is backgrounded, which the shells run in a subshell'];
    // [id, command, the shells that write the tracked subset when run unguarded, the verdict]
    const rows = [
      ['F2a-1', 'x=docs/report.md; { { x=scratch/keep.md; }; } | cat; cp base/report.md $x', A, PIPED],
      ['F2a-2', 'x=docs/report.md; { { { x=scratch/keep.md; }; }; } | cat; cp base/report.md $x', A, PIPED],
      ['F2a-3', 'x=docs/report.md; { { x=scratch/keep.md; }; } & wait; cp base/report.md $x', A, BG],
      ['F2a-4', 'x=docs/report.md; { echo hi; { x=scratch/keep.md; }; } | cat; cp base/report.md $x', A, PIPED],
      ['F2a-5', 'x=docs/report.md; { { x=scratch/keep.md; }; } |& cat; cp base/report.md $x', BZ, PIPED],   // dash has no |&: a syntax error, nothing runs
      ['F2a-6', 'x=docs/report.md; { { x=scratch/keep.md; } } | cat; cp base/report.md $x', A, PIPED],        // `} }` without a `;` between: all three shells accept it
      ['F2a-7', 'x=docs/report.md; { { x=scratch/keep.md; } } & wait; cp base/report.md $x', A, BG],
      ['F2a-8', 'x=docs/report.md; { { declare x=scratch/keep.md; }; } | cat; cp base/report.md $x', A, PIPED],   // dash has no declare: x untouched, the copy lands the same
      ['F2a-9', 'x=docs/report.md; { declare x=scratch/keep.md; } | cat; cp base/report.md $x', A, PIPED],       // ONE level, a declaration: the declaration branch noted no name (found here)
      ['F2a-10', 'x=docs/report.md; { export x=scratch/keep.md; } | cat; cp base/report.md $x', A, PIPED],
      ['F2a-11', 'x=docs/report.md; { { x=scratch/keep.md; }; y=1; } | cat; cp base/report.md $x', A, PIPED],
      ['F2a-12', 'x=docs/report.md; { { x=scratch/keep.md; }; } > /dev/null | cat; cp base/report.md $x', A, PIPED],
      ['F2b-1', '{ { cd scratch; }; } | cat; cp base/report.md notes/n1.md', A, 'name'],
      ['F2b-2', '{ { cd scratch; }; } & wait; cp base/report.md notes/n1.md', A, 'name'],
      ['F2b-3', '{ { cd scratch; } } | cat; cp base/report.md notes/n1.md', A, 'name'],
      ['F2b-4', '{ { cd docs; }; } | cat; cp base/report.md docs/report.md', A, 'name'],
      // twins
      ['F2-T1', 'x=docs/report.md; { x=scratch/keep.md; } | cat; cp base/report.md $x', A, PIPED],
      ['F2-T2', 'x=docs/report.md; { { x=scratch/keep.md; } | cat; }; cp base/report.md $x', A, PIPED],
      ['F2-T3', '{ cd scratch; } | cat; cp base/report.md notes/n1.md', A, 'name'],
      ['F2-T4', 'x=docs/report.md; ( { x=scratch/keep.md; } ) | cat; cp base/report.md $x', A, ['literal', 'an if, loop, case or function body, or a subshell']],
      ['F2-T5', 'x=docs/report.md; { { x=scratch/keep.md; }; } && cp base/report.md $x', [], 'allow'],   // the group runs in this shell: x is the inner value, the copy lands on the untracked keep.md
      ['F2-T6', 'x=docs/report.md; { { x=scratch/keep.md; }; }; cp base/report.md $x', [], 'allow'],
      ['F2-T7', 'x=docs/report.md; { { x=scratch/keep.md; } }; cp base/report.md $x', [], 'allow'],
      ['F2-T8', '{ { cd docs; }; } | cat; cp ../base/report.md report.md', [], 'allow'],   // the cd was a subshell's: the copy is judged from the cwd (report.md there is untracked) and the shells find no ../base
      ['F2-T9', '{ { cd docs; }; }; cp ../base/report.md report.md', A, 'name'],          // a plain nested group moves the shell: the copy lands on docs/report.md
      ['F2-T10', 'x=docs/report.md; { unset x; } | cat; cp base/report.md $x', A, ['literal', '']],   // an unset in a subshell: the guard forgets the name (refused as not literal), the shells keep it
    ];
    let n = 0;
    for (const [id, raw, writers, expect] of rows) {
      const cmd = w.fill(raw);
      const h = w.hook(cmd, w.NA);
      n++;
      if (expect === 'allow') assert.equal(h.status, 0, `${id}: allowed: ${cmd}: ${h.reason}`);
      else {
        assert.equal(h.status, 2, `${id}: refused: ${cmd}: ${h.reason}`);
        assert.ok(!/\u2014/.test(h.reason) && !ROMP_NOUNS.test(h.reason.split(w.W).join('<w>')), `${id}: no em dash, no romp noun`);
        if (expect === 'name') assert.match(h.reason, BY_NAME_RE, `${id}: by name (the group's cd did not move this shell): ${h.reason.split('\n')[0]}`);
        else assert.ok(NOT_LITERAL.test(h.reason) && h.reason.includes(expect[1]), `${id}: refused as not literal, the reason naming the construct (${expect[1]}): ${h.reason.split('\n')[0]}`);
      }
      for (const shell of shellsFor(A, id)) {
        const r = w.run(cmd, w.NA, shell);
        assert.equal(r.changed, writers.includes(shell), `${id}: run unguarded, ${shell} ${writers.includes(shell) ? 'writes' : 'leaves'} the tracked subset: ${cmd}: ${r.stderr}`);
      }
    }
    assert.equal(n, 26);
    // the grammar: the nested value is not resolved (the word stays opaque, no target), where before it resolved to scratch/keep.md
    const ex = extractWriteTargets('x=docs/report.md; { { x=scratch/keep.md; }; } | cat; cp base/report.md $x', w.NA);
    assert.deepEqual([ex.targets.length, ex.unresolved.map((u) => u.raw)], [0, ['$x']], 'the nested piped group leaves x unreadable');
    assert.deepEqual(extractWriteTargets('x=docs/report.md; { { x=scratch/keep.md; }; }; cp base/report.md $x', w.NA).targets.map((t) => t.path), [path.join(w.NA, 'scratch', 'keep.md')], 'a plain nested group is this shell\'s own');
  } finally { process.env.HOME = savedHome; w.rm(); }
});

test("the seventh pass's attacker, F1: zsh's precommand modifiers `noglob`, `nocorrect` and `-` are wrappers (peeled to the writer behind them, a cd behind one leaves the directory unknown with a text saying zsh moves and bash and dash stay, an assignment-shaped word after one is the wrapper's argument); the report's 7 rows and the siblings found with them (`-`, `builtin`/`time`/`exec noglob`, `noglob cd`) refuse, zsh alone writes when run unguarded (bash and dash fail on the word), and the twins keep their verdicts except `command noglob cp`, now refused where no shell runs it (priced)", () => {
  const w = sixthPassWorld();
  const savedHome = process.env.HOME;
  process.env.HOME = w.HOME;
  try {
    const A = ['bash', 'zsh', 'dash'];
    const Z = ['zsh'];
    const MOD = (m) => `runs under a wrapper (\`${m}\`), which is a zsh precommand modifier, so in zsh the shell's own cd runs and moves it, and no command in bash and dash, which stay`;
    // [id, command, the shells that write, the verdict, the shells whose run fails (a non-zero status: the word is no command there)]
    const rows = [
      ['F1-1', 'noglob cp base/report.md docs/report.md', Z, 'name', ['bash', 'dash']],
      ['F1-2', 'noglob mv base/report.md docs/report.md', Z, 'name', ['bash', 'dash']],
      ['F1-3', 'noglob tee docs/report.md < base/report.md', Z, 'name', ['bash', 'dash']],
      ['F1-4', 'noglob dd if=base/report.md of=docs/report.md', Z, 'name', ['bash', 'dash']],
      ['F1-5', 'noglob install base/report.md docs/report.md', Z, 'name', ['bash', 'dash']],
      ['F1-6', 'nocorrect cp base/report.md docs/report.md', Z, 'name', ['bash', 'dash']],
      ['F1-7', 'x=docs/report.md; noglob cp base/report.md $x', Z, 'name', ['bash', 'dash']],
      ['F1-8', ' - cp base/report.md docs/report.md', Z, 'name', ['bash', 'dash']],              // the `-` modifier (a leading space: `zsh -c` reads a string opening with `-` as options)
      ['F1-9', 'builtin noglob cp base/report.md docs/report.md', Z, 'name', ['bash', 'dash']],   // bash: not a shell builtin; dash: no builtin
      ['F1-10', 'time noglob cp base/report.md docs/report.md', Z, 'name', ['bash', 'dash']],
      ['F1-11', 'exec noglob cp base/report.md docs/report.md', Z, 'name', ['bash', 'dash']],
      ['F1-12', 'noglob cd docs; cp ../base/report.md report.md', Z, ['dir', MOD('noglob')], ['bash', 'dash']],   // bash and dash stay and find no ../base
      ['F1-13', 'nocorrect cd docs; cp ../base/report.md report.md', Z, ['dir', MOD('nocorrect')], ['bash', 'dash']],
      ['F1-14', 'x=docs/report.md; noglob x=scratch/keep.md; cp base/report.md $x', A, ['literal', 'an argument of the wrapper `noglob`, which the shell hands to it rather than assigning'], []],   // no shell assigns: zsh runs a command named x=..., bash and dash fail on noglob, and all three copy onto the tracked file
      ['F1-15', 'noglob cp base/report.md notes/', Z, 'name', ['bash', 'dash']],
      // twins
      ['F1-T1', 'x=docs/report.md; noglob printf poison > $x', A, 'name', ['bash', 'dash']],   // the redirection is the shell's, performed before the word is looked up: every shell truncates the file
      ['F1-T2', 'x=docs/report.md; command noglob cp base/report.md $x', [], 'name', A],   // THE MOVED TWIN: `command` looks noglob up as an external program in every shell, so nothing runs; refused by name now (the modifier peeled), allowed before: a cost, priced in fork PR #780's body
      ['F1-T4', 'nice noglob cp base/report.md docs/report.md', [], 'name', A],             // the same: an external wrapper runs an external noglob that is not there
      ['F1-T5', 'noglob nocorrect cp base/report.md docs/report.md', [], 'name', A],        // zsh takes nocorrect as a modifier only first: a command not found, nothing written
      ['F1-T6', 'noglob cp base/report.md scratch/keep.md', [], 'allow', ['bash', 'dash']],   // the writer behind the modifier lands on an untracked file: allowed
      ['F1-T7', 'noglob ls docs', [], 'allow', ['bash', 'dash']],
    ];
    let n = 0;
    for (const [id, raw, writers, expect, fails] of rows) {
      const cmd = w.fill(raw);
      const h = w.hook(cmd, w.NA);
      n++;
      if (expect === 'allow') assert.equal(h.status, 0, `${id}: allowed: ${cmd}: ${h.reason}`);
      else {
        assert.equal(h.status, 2, `${id}: refused: ${cmd}: ${h.reason}`);
        assert.ok(!/\u2014/.test(h.reason) && !ROMP_NOUNS.test(h.reason.split(w.W).join('<w>')), `${id}: no em dash, no romp noun`);
        if (expect === 'name') assert.match(h.reason, BY_NAME_RE, `${id}: by name, the writer behind the modifier seen: ${h.reason.split('\n')[0]}`);
        else if (expect[0] === 'dir') assert.ok(/the directory it is relative to is not known/.test(h.reason) && h.reason.includes(expect[1]), `${id}: the cd behind the modifier leaves the directory unknown and the text says what each shell does: ${h.reason.split('\n')[0]}`);
        else assert.ok(NOT_LITERAL.test(h.reason) && h.reason.includes(expect[1]), `${id}: refused as not literal, the reason naming the construct: ${h.reason.split('\n')[0]}`);
      }
      for (const shell of shellsFor(A, id)) {
        const r = w.run(cmd, w.NA, shell);
        assert.equal(r.changed, writers.includes(shell), `${id}: run unguarded, ${shell} ${writers.includes(shell) ? 'writes' : 'leaves'} the tracked subset: ${cmd}: ${r.stderr}`);
        assert.equal(r.status !== 0, fails.includes(shell), `${id}: ${shell} ${fails.includes(shell) ? 'fails (the word is no command of its)' : 'succeeds'}: status ${r.status}: ${r.stderr}`);
      }
    }
    assert.equal(n, 21);
    for (const shell of shellsFor(['bash', 'dash'], 'the modifier word in bash and dash')) assert.equal(w.run('noglob cp base/report.md docs/report.md', w.NA, shell).status, 127, `${shell} exits 127 on the word noglob`);
    // the out-of-model residual for contrast (the contract's list: unshare): allowed; what the shells do depends on the runner's namespaces, so it is printed, not asserted
    const residual = 'unshare -r cp base/report.md docs/report.md';
    assert.equal(w.hook(residual, w.NA).status, 0, 'unshare is on the contract\'s out-of-model list: allowed');
    for (const shell of shellsFor(A, 'unshare')) console.log(`# unshare -r cp in ${shell} on this runner: ${w.run(residual, w.NA, shell).changed ? 'wrote the tracked file (the residual, live here)' : 'wrote nothing (no user namespace here)'}`);
    // the grammar: the modifier is peeled like `command`, its option table empty, and a definition by its name is a function like any other
    assert.deepEqual(extractWriteTargets('noglob cp base/report.md docs/report.md', w.NA).targets.map((t) => t.path), [path.join(w.NA, 'docs', 'report.md')]);
    assert.deepEqual(extractWriteTargets(' - cp base/report.md docs/report.md', w.NA).targets.map((t) => t.path), [path.join(w.NA, 'docs', 'report.md')]);
    assert.equal(w.hook('noglob -x cp base/report.md scratch/keep.md', w.NA).status, 2, 'an option after a modifier refuses like any wrapper option the table does not hold');
    assert.equal(w.hook('x=scratch/keep.md; noglob() { x=docs/report.md; }; noglob true; cp base/report.md $x', w.NA).status, 2, 'a function named noglob, called by that name, poisons like any wrapper-named function');
  } finally { process.env.HOME = savedHome; w.rm(); }
});

test("found beside the attacker's readonly rows: a name made readonly keeps its value, since no shell performs a later write to it (bash, zsh and dash stop the command list on a plain assignment; bash keeps the value and continues past a `declare`, `typeset`, `export` or `unset` of it, and dash where the word is no command of its), so `readonly x=docs/report.md; declare x=scratch/keep.md; cp base/report.md $x` is refused by the readonly value where the guard adopted the later one and bash and dash wrote the tracked file; the attacker's plain-reassign rows abort every shell and are refused by that value too; a readonly name whose value is untracked stays allowed", () => {
  const w = sixthPassWorld();
  const savedHome = process.env.HOME;
  process.env.HOME = w.HOME;
  try {
    const A = ['bash', 'zsh', 'dash'];
    const B = ['bash'];
    const BD = ['bash', 'dash'];
    const BZ = ['bash', 'zsh'];
    // [id, cwd, command, the shells that write, the verdict, the shells whose run fails]
    const rows = [
      ['RO-6', 'na', 'readonly x=docs/report.md; declare x=scratch/keep.md; cp base/report.md $x', BD, 'name', ['zsh']],        // zsh stops on the declare; bash continues with the readonly value, dash has no declare
      ['RO-7', 'na', 'readonly x=docs/report.md; export x=scratch/keep.md; cp base/report.md $x', B, 'name', ['zsh', 'dash']],  // dash's export refuses and stops
      ['RO-8', 'na', 'readonly x=docs/report.md; unset x; cp base/report.md $x', B, 'name', ['zsh', 'dash']],
      ['RO-9', 'na', 'declare -r x=docs/report.md; declare x=scratch/keep.md; cp base/report.md $x', B, 'name', ['zsh', 'dash']],   // dash: no declare at all, the copy has no destination
      ['RO-10', 'na', 'x=docs/report.md; readonly x; declare x=scratch/keep.md; cp base/report.md $x', BD, 'name', ['zsh']],   // `readonly x` alone freezes the value it has
      ['RO-11', 'na', 'readonly x=docs/report.md; typeset x=scratch/keep.md; cp base/report.md $x', BD, 'name', ['zsh']],
      ['RO-12', 'na', 'readonly x=docs/report.md; local x=scratch/keep.md; cp base/report.md $x', B, 'name', ['zsh', 'dash']],
      ['RO-13', 'out', 'readonly x={NA}/docs/report.md; declare x={OUT}/scratch/keep.md; cp {NA}/base/report.md $x', BD, 'name', ['zsh']],   // from a cwd in no project: resolved by the readonly value, so refused by name (a taint would have left it the residual)
      // the attacker's rows: a plain reassign stops every shell that has the construct (RO-1..4, E1..E3 were allowed and safe by shell semantics; refused by the readonly value now)
      ['RO-1', 'na', 'readonly x=docs/report.md; x=scratch/keep.md; cp base/report.md $x', [], 'name', A],
      ['RO-2', 'na', 'declare -r x=docs/report.md; x=scratch/keep.md; cp base/report.md $x', [], 'name', BZ],    // dash has no declare: x is the later value and the copy lands on keep.md
      ['RO-3', 'na', 'typeset -r x=docs/report.md; x=scratch/keep.md; cp base/report.md $x', [], 'name', BZ],
      ['RO-4', 'na', 'declare -gr x=docs/report.md; x=scratch/keep.md; cp base/report.md $x', [], 'name', BZ],
      ['RO-E1', 'na', 'readonly x=docs/report.md; x=scratch/keep.md || true; cp base/report.md $x', [], 'name', A],
      ['RO-E2', 'na', 'readonly x=docs/report.md; x=scratch/keep.md 2>/dev/null; cp base/report.md $x', [], 'name', A],
      ['RO-E3', 'na', 'readonly x=docs/report.md; set +e; x=scratch/keep.md; cp base/report.md $x', [], 'name', A],
      ['RO-E4', 'na', 'readonly x=docs/report.md; (x=scratch/keep.md) 2>/dev/null; cp base/report.md $x', A, 'name', []],
      ['RO-T1', 'na', 'readonly x=docs/report.md; cp base/report.md $x', A, 'name', []],
      ['RO-T2', 'na', 'readonly x=scratch/keep.md; cp base/report.md $x', [], 'allow', []],
      ['RO-T3', 'na', 'declare -r x=scratch/keep.md; cp base/report.md $x', [], 'allow', ['dash']],   // dash: no declare, the copy has no destination
      ['RO-T4', 'na', 'readonly x=scratch/keep.md; declare x=docs/report.md; cp base/report.md $x', [], 'allow', ['zsh']],   // the readonly value is untracked: allowed, and bash lands the copy there
      ['RO-T5', 'na', 'x=scratch/keep.md; readonly x; cp base/report.md $x', [], 'allow', []],      // `readonly x` alone keeps a readable value readable (a taint before)
    ];
    let n = 0;
    for (const [id, cwd, raw, writers, expect, fails] of rows) {
      const cmd = w.fill(raw);
      const at = w.cwds[cwd];
      const h = w.hook(cmd, at);
      n++;
      if (expect === 'allow') assert.equal(h.status, 0, `${id}: allowed: ${cmd}: ${h.reason}`);
      else { assert.equal(h.status, 2, `${id}: refused: ${cmd}: ${h.reason}`); assert.match(h.reason, BY_NAME_RE, `${id}: by the readonly value: ${h.reason.split('\n')[0]}`); assert.ok(h.reason.includes(path.join(w.NA, 'docs', 'report.md')), `${id}: the readonly value is the path named`); }
      for (const shell of shellsFor(A, id)) {
        const r = w.run(cmd, at, shell);
        assert.equal(r.changed, writers.includes(shell), `${id}: run unguarded, ${shell} ${writers.includes(shell) ? 'writes' : 'leaves'} the tracked subset: ${cmd}: ${r.stderr}`);
        assert.equal(r.status !== 0, fails.includes(shell), `${id}: ${shell} ${fails.includes(shell) ? 'stops on the readonly error' : 'runs through'}: status ${r.status}: ${r.stderr}`);
      }
    }
    assert.equal(n, 21);
    // the grammar: the readonly value is what resolves after the later write, and a `+r` (zsh can drop the attribute) taints as a flag outside the inert set
    assert.deepEqual(extractWriteTargets('readonly x=docs/report.md; declare x=scratch/keep.md; cp base/report.md $x', w.NA).targets.map((t) => t.path), [path.join(w.NA, 'docs', 'report.md')]);
    const plus = w.hook('readonly x=scratch/keep.md; typeset +r x; x=docs/report.md; cp base/report.md $x', w.NA);
    assert.ok(plus.status === 2 && NOT_LITERAL.test(plus.reason) && plus.reason.includes('a `typeset` flag that can change the value or what the name is (+r)'), `+r taints: ${plus.reason.split('\n')[0]}`);
    for (const shell of shellsFor(['zsh'], 'zsh drops the readonly attribute with +r')) assert.equal(w.run('readonly x=scratch/keep.md; typeset +r x; x=docs/report.md; cp base/report.md $x', w.NA, shell).changed, true, 'zsh writes the tracked file after typeset +r');
  } finally { process.env.HOME = savedHome; w.rm(); }
});

test("the seventh pass's mutation lens: the unpinned claims of the readability rule are pinned one by one, each row run through the hook as a process and unguarded in the three shells: a tilde after a colon in a value (all three shells expand it), an option word the shell fills in on a declaration (M1's per-segment detector, the row a plain `declare -$f` with f opaque), a nameref's target not freed by `unset` (the distinguishing row: the freed name is written again), a nameref target the shell fills in, a top-level `local` (zsh performs it, bash continues past it, dash stops), `unset -f`, the two halves of the assembled-name poison alone (a non-declaration command's `$(..)=v` word; `read $h` with h opaque), a wrapper-named function with an inert body (the call poisons) and with a cd (the directory is unknown), `~`, `~+` and `~-` values after an eval (valueOf reads no name once the table is poisoned) and after a PWD mention, `read $h` with h readable (the resolved name), and a glued `printf -vx`", () => {
  const w = sixthPassWorld();
  const savedHome = process.env.HOME;
  process.env.HOME = w.HOME;
  try {
    const A = ['bash', 'zsh', 'dash'];
    const B = ['bash'];
    const BZ = ['bash', 'zsh'];
    const Z = ['zsh'];
    const lit = (t) => ['literal', t];
    const TILDE = (t) => lit(`a value that begins with \`${t}\`, which I cannot read here`);
    // [id, command, the shells that write the tracked subset, the verdict]
    const rows = [
      ['U1', 'x=scratch:~/k; cp base/report.md $x', [], lit('a value with a tilde after a colon, which bash, zsh and dash expand')],
      ['U2', 'y=scratch/keep.md; f=$(printf n); declare -$f x=y; x=docs/report.md; cp base/report.md $y', B, lit("the command's `declare` takes a variable name the shell fills in when it runs (-$f), and a name I cannot read may be any name")],   // bash: declare -n x=y, then x=.. writes y
      ['U2b', 'y=scratch/keep.md; f=$(printf -- -n); declare $f x=y; x=docs/report.md; cp base/report.md $y', B, lit("the command's `declare` takes a variable name the shell fills in when it runs ($f), and a name I cannot read may be any name")],
      ['U3', 'x=docs/report.md; declare -n r=x; unset x; x=scratch/keep.md; r=docs/report.md; cp base/report.md $x', B, lit('a nameref')],   // bash writes x through r after the unset and the plain write: the freed name would resolve to keep.md
      ['U4', 'y=scratch/keep.md; h=$(echo y); declare -n r=$h; r=docs/report.md; cp base/report.md $y', B, lit("the command's `declare` takes a variable name the shell fills in when it runs (r=$h), and a name I cannot read may be any name")],
      ['U4b', 'y=scratch/keep.md; h=$(echo y); export -n r=$h; cp base/report.md $y', [], lit("the command's `export -n` makes `r` a reference to a name the shell fills in (r=$h), which may be any name")],   // the declaration branch's own poison, reached where M1 reads export's -n as no nameref (a cost: bash unexports r, no shell writes)
      ['U5', 'x=docs/report.md; local x=scratch/keep.md; cp base/report.md $x', B, lit('a `local`, which zsh performs at the top level and bash and dash reject')],
      ['U6', 'x=scratch/keep.md; unset -f x; cp base/report.md $x', [], lit('an `unset` with -f')],
      ['U7a', 'y=scratch/keep.md; true $(echo y)=docs/report.md; cp base/report.md $y', [], lit("the command's `true` takes a variable name the shell fills in when it runs ($(echo y)=docs/report.md), and a name I cannot read may be any name")],   // taintWord's name-part poison alone (true is on no name-operand list; a cost)
      ['U7b', "y=scratch/keep.md; h=$(echo y); printf 'docs/report.md\\n' > scratch/line; read $h < scratch/line; cp base/report.md $y", A, lit("the command's `read` takes a variable name the shell fills in when it runs ($h), and a name I cannot read may be any name")],   // M1's per-segment detector alone (no `=` for taintWord's poison)
      ['U8', 'x=scratch/keep.md; env() { :; }; env true; cp base/report.md $x', [], lit('an earlier call of `env`, a function the command defines, may assign any name')],   // an inert body: the call alone poisons (a cost)
      ['U9', 'env() { cd ..; }; env true; cp notes-api/base/report.md notes-api/notes/n1.md', A, ['dir', 'an earlier call of the function `env` may change the directory, which I do not follow']],
      ['U10a', "e=$(printf 'HO%s' ME=notes); eval \"$e\"; x=~/n1.md; printf poison > $x", A, TILDE('~')],
      ['U10b', 'eval true; x=~/n1.md; printf poison > $x', [], TILDE('~')],   // the guard reads no HOME after an eval: the write lands in the home (a cost)
      ['U10c', "eval 'cd docs'; x=~+/report.md; cp ../base/report.md $x", BZ, TILDE('~+')],
      ['U10d', 'eval true; x=~+/scratch/keep.md; cp base/report.md $x', [], TILDE('~+')],
      ['U10e', 'cd scratch; cd ..; eval true; x=~-/keep.md; cp base/report.md $x', [], TILDE('~-')],
      ['U10f', 'cd docs; cd ..; eval true; x=~-/report.md; cp base/report.md $x', BZ, TILDE('~-')],
      ['U10g', 'x=~+/scratch/keep.md; cp base/report.md $x', [], 'allow'],           // without the eval `~+` resolves through the directory the guard knows
      ['U10h', 'cd scratch; cd ..; x=~-/keep.md; cp base/report.md $x', [], 'allow'],
      ['U11', "x=scratch/keep.md; h=x; printf 'docs/report.md\\n' > scratch/line; read $h < scratch/line; cp base/report.md $x", A, lit('a name operand of `read`')],
      ['U12', 'x=scratch/keep.md; printf -vx docs/report.md; cp base/report.md $x', B, lit('a `printf -v`')],
      ['U18', 'PWD=/x; x=~+/docs/report.md; cp base/report.md $x', Z, TILDE('~+')],   // zsh reads the real directory for `~+`, bash the PWD it was given, dash expands no `~+`
    ];
    let n = 0;
    for (const [id, raw, writers, expect] of rows) {
      const cmd = w.fill(raw);
      const h = w.hook(cmd, w.NA);
      n++;
      if (expect === 'allow') assert.equal(h.status, 0, `${id}: allowed: ${cmd}: ${h.reason}`);
      else {
        assert.equal(h.status, 2, `${id}: refused: ${cmd}: ${h.reason}`);
        assert.ok(!/\u2014/.test(h.reason) && !ROMP_NOUNS.test(h.reason.split(w.W).join('<w>')), `${id}: no em dash, no romp noun`);
        if (expect[0] === 'dir') assert.ok(/the directory it is relative to is not known/.test(h.reason) && h.reason.includes(expect[1]), `${id}: the directory is unknown, the reason naming the call: ${h.reason.split('\n')[0]}`);
        else assert.ok(NOT_LITERAL.test(h.reason) && h.reason.includes(expect[1]), `${id}: refused as not literal, the reason naming the construct (${expect[1]}): ${h.reason.split('\n')[0]}`);
      }
      for (const shell of shellsFor(A, id)) {
        const r = w.run(cmd, w.NA, shell);
        assert.equal(r.changed, writers.includes(shell), `${id}: run unguarded, ${shell} ${writers.includes(shell) ? 'writes' : 'leaves'} the tracked subset: ${cmd}: ${r.stderr}`);
        if (id === 'U10b') assert.ok(fs.existsSync(path.join(w.HOME, 'n1.md')), `${shell} wrote the home's n1.md: the value the guard would have read`);
      }
    }
    assert.equal(n, 23);
    // the constructs measured on their own, the three shells agreeing where the row's verdict says they do
    const out = (shell, script) => spawnSync(shell, shell === 'bash' ? ['--norc', '--noprofile', '-c', script] : shell === 'zsh' ? ['-f', '-c', script] : ['-c', script], { cwd: w.NA, encoding: 'utf8', env: w.env, input: '' });
    for (const shell of shellsFor(A, 'the constructs on their own')) {
      assert.equal(out(shell, 'x=a:~/b; printf %s "$x"').stdout, `a:${w.HOME}/b`, `${shell} expands a tilde after a colon in an assignment value`);
      assert.equal(out(shell, 'x=a; unset -f x; printf %s "$x"').stdout, 'a', `${shell}: unset -f leaves the variable`);
      assert.equal(out(shell, 'env() { printf called; }; env true').stdout, 'called', `${shell} calls the function named env, not the program`);
      assert.equal(out(shell, 'x=k; true $(echo x)=v; printf %s "$x"').stdout, 'k', `${shell}: an assignment-shaped argument of true assigns nothing (why U7a is a cost)`);
    }
    for (const shell of shellsFor(['bash'], 'the glued printf -v and the nameref in bash')) {
      assert.equal(out(shell, 'printf -vx hello; printf %s "$x"').stdout, 'hello', 'bash reads the glued -vx');
      assert.equal(out(shell, 'x=k; declare -n r=x; unset x; x=k2; r=v; printf %s "$x"').stdout, 'v', 'bash writes x through r after unset x');
    }
    for (const shell of shellsFor(['zsh'], 'zsh performs a top-level local')) assert.equal(out(shell, 'x=a; local x=b; printf %s "$x"').stdout, 'b');
    for (const shell of shellsFor(['dash'], 'dash stops on a top-level local')) assert.notEqual(out(shell, 'x=a; local x=b; printf %s "$x"').status, 0);
    // the grammar: after an eval no expanded name is read (valueOf), where before it PWD resolved through the directory
    assert.deepEqual(extractWriteTargets('x=~+/scratch/keep.md; cp base/report.md $x', w.NA).targets.map((t) => t.path), [path.join(w.NA, 'scratch', 'keep.md')]);
    assert.deepEqual(extractWriteTargets('eval true; x=~+/scratch/keep.md; cp base/report.md $x', w.NA).targets, []);
  } finally { process.env.HOME = savedHome; w.rm(); }
});

// ── round 5 of the review (2026-09-20): the frame on parsed structure, the freeze unwrapped, the catch-all refusing, the census derived ──
//
// Round 4 (romp-manager's ruling over the seventh pass's head) found seven highs, six of them one defect: the frame decision
// was keyed on the segment's FIRST word, so a leading `!`, `time`, `{`, a `then` or `do` before a nested head, and `select`
// (in COMPOUND_HEADS, in neither the push nor CLOSERS) hid the compound head, no frame opened, and a body that may not run
// was walked as this shell's own plain sequence: the name assigned in it stayed readable and was the write target, and a
// `cd` in it was followed, so the write resolved against a directory the shell never entered (round 3's unknown-directory
// refusal walked around by being confidently wrong instead of unknown). The second root cause pulled the other way: the
// readonly skip was computed from the PEELED command, so a `readonly` behind a wrapper that runs an external command froze
// a name no shell froze and the guard kept a stale value while the later write went through. Every row below runs through
// the hook as a process from its cwd and then unguarded in bash, zsh and dash over a fresh world, the tracked subset
// fingerprinted, the test asserting EXACTLY which shells write; the rows were red at round 4's head (a36e34832, run in a
// scratch copy of this file against that hook: the allowed status where a refusal is asserted, or the reverse), by
// construction, since the head had no frame to open and froze the wrapped name.

const BODY = ['literal', 'an if, loop, case or function body, or a subshell'];
const PIPED_GROUP = ['literal', 'a `{ }` group that is piped, which the shells run in a subshell'];
const UNKNOWN_BODY_CD = ['dir', 'sits in an if, loop or case body that may not run'];

test("round 5, the frame on parsed structure: a compound head behind `!` (a run of them), `time` and its options, `{`, a `then` or `do` (a nested body), a select loop, a function definition behind `!` or inside a group, and each closer opens its frame, so the name a body that may not run assigns is unreadable (the name face) and a cd there leaves the directory unknown at the closer (the cd face); the twins (a plain group behind `!` or `time`, a piped group behind `!` whose cd is undone) keep the shell's own reading; each refused row writes the tracked subset in the shells that accept the spelling and each allowed row leaves it", () => {
  const w = sixthPassWorld();
  const savedHome = process.env.HOME;
  process.env.HOME = w.HOME;
  try {
    const A = ['bash', 'zsh', 'dash'];
    const B = ['bash'];
    const BZ = ['bash', 'zsh'];
    // [id, command, the shells that write the tracked subset when run unguarded (the others reject the spelling and run nothing), the verdict]
    const rows = [
      // the name face: x holds the tracked path; the body that may not run reassigns it; the copy lands where the shell's x says
      ['N1', 'x=docs/report.md; ! if false; then x=scratch/keep.md; fi; cp base/report.md $x', A, BODY],
      ['N2', 'x=docs/report.md; ! ! if false; then x=scratch/keep.md; fi; cp base/report.md $x', B, BODY],            // zsh and dash: a parse error on the second `!`
      ['N3', 'x=docs/report.md; time if false; then x=scratch/keep.md; fi; cp base/report.md $x', BZ, BODY],          // dash: time is an external command, `then` a syntax error
      ['N4', 'x=docs/report.md; time -p if false; then x=scratch/keep.md; fi; cp base/report.md $x', B, BODY],
      ['N5', 'x=docs/report.md; time -- if false; then x=scratch/keep.md; fi; cp base/report.md $x', B, BODY],
      ['N6', 'x=docs/report.md; time -p -- if false; then x=scratch/keep.md; fi; cp base/report.md $x', B, BODY],
      ['N7', 'x=docs/report.md; { if false; then x=scratch/keep.md; fi; }; cp base/report.md $x', A, BODY],
      ['N8', 'x=docs/report.md; if false; then if true; then :; fi; x=scratch/keep.md; fi; cp base/report.md $x', A, BODY],   // the inner fi closed the OUTER frame at round 4's head
      ['N9', 'x=docs/report.md; while false; do while false; do :; done; x=scratch/keep.md; done; cp base/report.md $x', A, BODY],
      ['N10', 'x=docs/report.md; select y in a; do x=scratch/keep.md; done </dev/null; cp base/report.md $x', BZ, BODY],   // stdin at EOF: the body never runs; dash has no select
      ['N11', 'x=docs/report.md; ! select y in a; do x=scratch/keep.md; done </dev/null; cp base/report.md $x', BZ, BODY],
      ['N12', 'x=docs/report.md; ! f() { x=scratch/keep.md; }; cp base/report.md $x', A, BODY],                      // a definition, not a run: read as a subshell then a plain group before
      ['N13', 'x=docs/report.md; { f() { x=scratch/keep.md; }; }; cp base/report.md $x', A, BODY],
      ['N14', 'x=docs/report.md; { function f { x=scratch/keep.md; }; }; cp base/report.md $x', BZ, BODY],           // dash has no `function`
      ['N15', 'y=docs/report.md; { y=scratch/keep.md; f() { :; }; } | cat; cp base/report.md $y', A, PIPED_GROUP],   // the body's `}` closed the piped group one brace early
      ['N16', 'x=docs/report.md; ! { ! { x=scratch/keep.md; }; } | cat; cp base/report.md $x', A, PIPED_GROUP],
      ['N17', 'x=docs/report.md; time { x=scratch/keep.md; } | cat; cp base/report.md $x', BZ, ['literal', /a `\{ \}` group that is piped|an argument of the wrapper `time`/]],   // commandOf reads `time` as a wrapper and taints x as its argument first; the piped group's taint would follow: a refusal either way
      ['N18', 'x=docs/report.md; ! case a in b) x=scratch/keep.md;; esac; cp base/report.md $x', A, BODY],
      ['N19', 'x=docs/report.md; ! until true; do x=scratch/keep.md; done; cp base/report.md $x', A, BODY],
      ['N20', 'x=docs/report.md; ! for y in; do x=scratch/keep.md; done; cp base/report.md $x', A, BODY],
      ['N21', 'x=docs/report.md; ! while false; do x=scratch/keep.md; done; cp base/report.md $x', A, BODY],
      // the cd face: the cd in the body never runs, the copy lands in the tracked folder from the cwd the shell never left
      ['D1', '! if false; then cd scratch; fi; cp base/report.md notes/n1.md', A, UNKNOWN_BODY_CD],
      ['D2', 'time if false; then cd scratch; fi; cp base/report.md notes/n1.md', BZ, UNKNOWN_BODY_CD],
      ['D3', '{ if false; then cd scratch; fi; }; cp base/report.md notes/n1.md', A, UNKNOWN_BODY_CD],
      ['D4', 'select y in a; do cd scratch; done </dev/null; cp base/report.md notes/n1.md', BZ, UNKNOWN_BODY_CD],
      ['D5', '! while false; do cd scratch; done; cp base/report.md notes/n1.md', A, UNKNOWN_BODY_CD],
      ['D6', '! until true; do cd scratch; done; cp base/report.md notes/n1.md', A, UNKNOWN_BODY_CD],
      ['D7', '! case a in b) cd scratch;; esac; cp base/report.md notes/n1.md', A, UNKNOWN_BODY_CD],
      ['D8', '! for y in; do cd scratch; done; cp base/report.md notes/n1.md', A, UNKNOWN_BODY_CD],
      ['D9', 'if false; then if true; then :; fi; cd scratch; fi; cp base/report.md notes/n1.md', A, UNKNOWN_BODY_CD],
      ['D10', '! { cd scratch; } | cat; cp base/report.md notes/n1.md', A, 'name'],   // the piped group's cd is undone: judged from the cwd, by name
      // the twins: a plain group behind `!` or `time` runs in this shell, so its assignment is the shell's own; a piped group's cd is undone, so the write beside it is untracked
      ['T1', 'x=docs/report.md; ! { x=scratch/keep.md; }; cp base/report.md $x', [], 'allow'],
      ['T2', 'x=docs/report.md; time { x=scratch/keep.md; }; cp base/report.md $x', ['zsh'], ['literal', 'an argument of the wrapper `time`']],   // not a twin, a true refusal: bash runs the timed group in this shell (x is keep.md, the copy untracked), zsh runs it in a subshell and keeps the tracked path (measured 2026-09-20: zsh wrote the tracked file), dash rejects the `}`; commandOf's wrapper-argument taint (C5e) holds the refusal
      ['T3', '! { cd docs; } | cat; cp base/report.md scratch/keep.md', [], 'allow'],                 // the mirrored false refusal round 4's refuters found at that head
    ];
    let n = 0;
    for (const [id, raw, writers, expect] of rows) {
      const cmd = w.fill(raw);
      const h = w.hook(cmd, w.NA);
      n++;
      if (expect === 'allow') assert.equal(h.status, 0, `${id}: allowed: ${cmd}: ${h.reason}`);
      else {
        assert.equal(h.status, 2, `${id}: refused: ${cmd}: ${h.reason}`);
        assert.ok(!/\u2014/.test(h.reason) && !ROMP_NOUNS.test(h.reason.split(w.W).join('<w>')), `${id}: no em dash, no romp noun`);
        if (expect === 'name') assert.match(h.reason, BY_NAME_RE, `${id}: by name: ${h.reason.split('\n')[0]}`);
        else if (expect[0] === 'dir') assert.ok(/the directory it is relative to is not known/.test(h.reason) && h.reason.includes(expect[1]), `${id}: the directory is unknown at the closer, the reason naming the body: ${h.reason.split('\n')[0]}`);
        else assert.ok(NOT_LITERAL.test(h.reason) && (expect[1] instanceof RegExp ? expect[1].test(h.reason) : h.reason.includes(expect[1])), `${id}: refused as not literal, the reason naming the construct (${expect[1]}): ${h.reason.split('\n')[0]}`);
      }
      for (const shell of shellsFor(A, id)) {
        const r = w.run(cmd, w.NA, shell);
        assert.equal(r.changed, writers.includes(shell), `${id}: run unguarded, ${shell} ${writers.includes(shell) ? 'writes' : 'leaves'} the tracked subset: ${cmd}: ${r.stderr}`);
      }
    }
    assert.equal(n, 34);
    // the grammar: the head is read after the peel and from the one table; a select body closes on `done`
    const ex = extractWriteTargets('x=docs/report.md; ! if false; then x=scratch/keep.md; fi; cp base/report.md $x', w.NA);
    assert.deepEqual([ex.targets.length, ex.unresolved.map((u) => u.raw)], [0, ['$x']], 'the body behind `!` leaves x unreadable');
    assert.deepEqual(extractWriteTargets('select y in a; do cd scratch; done; cp base/report.md notes/n1.md', w.NA).unresolved.map((u) => u.why && u.why.kind), ['unknownDir'], 'the select frame closes on done and its cd makes the directory unknown');
    assert.deepEqual(extractWriteTargets('x=docs/report.md; ! { x=scratch/keep.md; }; cp base/report.md $x', w.NA).targets.map((t) => t.path), [path.join(w.NA, 'scratch', 'keep.md')], 'a plain group behind `!` is this shell\'s own');
  } finally { process.env.HOME = savedHome; w.rm(); }
});

test("round 5, peel for the frame, not for the freeze: a `readonly`, `declare -r` or `typeset -r` behind a wrapper freezes nothing in the shells that run the wrapper as an external command, so the name is tainted rather than frozen and the later write is judged (it was skipped, the guard keeping the stale value while bash, zsh and dash performed the write); a declaration of any kind behind a wrapper taints its names, since the shells differ on whether it ran; the readonly value kept by an UNWRAPPED freeze still resolves; each wrapper spelling is run in each shell and exactly the shells where no freeze happened write the tracked file", () => {
  const w = sixthPassWorld();
  const savedHome = process.env.HOME;
  process.env.HOME = w.HOME;
  try {
    const A = ['bash', 'zsh', 'dash'];
    const wrapped = (wr, verb) => ['literal', `a \`${verb}\` behind the wrapper \`${wr}\`, which runs the shell's own ${verb} in some shells and an external command that assigns nothing in others`];
    // [id, command, the shells that write the tracked subset (the freeze did not happen there), the verdict]
    const rows = [
      // a readonly behind an external wrapper: no shell freezes; behind a shell word, the shells that have the word freeze and stop
      ['W1', 'x=scratch/keep.md; env readonly x=scratch/keep.md; x=docs/report.md; cp base/report.md $x', A, wrapped('env', 'readonly')],
      ['W2', 'x=scratch/keep.md; nice readonly x=scratch/keep.md; x=docs/report.md; cp base/report.md $x', A, wrapped('nice', 'readonly')],
      ['W3', 'x=scratch/keep.md; nohup readonly x=scratch/keep.md; x=docs/report.md; cp base/report.md $x', A, wrapped('nohup', 'readonly')],
      ['W4', 'x=scratch/keep.md; timeout 5 readonly x=scratch/keep.md; x=docs/report.md; cp base/report.md $x', A, wrapped('timeout', 'readonly')],
      ['W5', 'x=scratch/keep.md; setsid readonly x=scratch/keep.md; x=docs/report.md; cp base/report.md $x', A, wrapped('setsid', 'readonly')],
      ['W6', 'x=scratch/keep.md; stdbuf -o0 readonly x=scratch/keep.md; x=docs/report.md; cp base/report.md $x', A, wrapped('stdbuf', 'readonly')],
      ['W7', 'x=scratch/keep.md; command readonly x=scratch/keep.md; x=docs/report.md; cp base/report.md $x', ['zsh'], wrapped('command', 'readonly')],      // bash and dash run the builtin and freeze; zsh runs an external readonly
      ['W8', 'x=scratch/keep.md; builtin readonly x=scratch/keep.md; x=docs/report.md; cp base/report.md $x', ['dash'], wrapped('builtin', 'readonly')],    // dash has no builtin
      ['W9', 'x=scratch/keep.md; noglob readonly x=scratch/keep.md; x=docs/report.md; cp base/report.md $x', ['bash', 'dash'], wrapped('noglob', 'readonly')],   // zsh alone has the modifier
      ['W10', 'x=scratch/keep.md; env declare -r x=scratch/keep.md; x=docs/report.md; cp base/report.md $x', A, wrapped('env', 'declare')],
      ['W11', 'x=scratch/keep.md; command typeset -r x=scratch/keep.md; x=docs/report.md; cp base/report.md $x', ['zsh', 'dash'], wrapped('command', 'typeset')],   // dash has no typeset either
      ['W12', 'x=scratch/keep.md; builtin declare -r x=scratch/keep.md; x=docs/report.md; cp base/report.md $x', ['dash'], wrapped('builtin', 'declare')],
      ['W13', 'x=scratch/keep.md; noglob typeset -r x=scratch/keep.md; x=docs/report.md; cp base/report.md $x', ['bash', 'dash'], wrapped('noglob', 'typeset')],
      // any declaration behind a wrapper: the guard adopted the value at round 4's head while the shells kept the old one, or differed
      ['W14', 'x=docs/report.md; env export x=scratch/keep.md; cp base/report.md $x', A, wrapped('env', 'export')],
      ['W15', 'x=docs/report.md; command declare x=scratch/keep.md; cp base/report.md $x', ['zsh', 'dash'], wrapped('command', 'declare')],   // bash's command runs the builtin and assigns
      ['W16', 'x=docs/report.md; builtin export x=scratch/keep.md; cp base/report.md $x', ['dash'], wrapped('builtin', 'export')],
      ['W17', 'x=docs/report.md; noglob typeset x=scratch/keep.md; cp base/report.md $x', ['bash', 'dash'], wrapped('noglob', 'typeset')],
      // the order: a name frozen by an UNWRAPPED readonly keeps its value through a wrapped declaration (every shell keeps it too)
      ['W18', 'readonly x=docs/report.md; command declare x=scratch/keep.md; cp base/report.md $x', A, 'name'],
      ['W19', 'x=scratch/keep.md; readonly x; x=docs/report.md; cp base/report.md $x', [], 'allow'],   // the unwrapped freeze holds: every shell stops on the reassignment
    ];
    let n = 0;
    for (const [id, raw, writers, expect] of rows) {
      const cmd = w.fill(raw);
      const h = w.hook(cmd, w.NA);
      n++;
      if (expect === 'allow') assert.equal(h.status, 0, `${id}: allowed: ${cmd}: ${h.reason}`);
      else {
        assert.equal(h.status, 2, `${id}: refused: ${cmd}: ${h.reason}`);
        assert.ok(!/\u2014/.test(h.reason) && !ROMP_NOUNS.test(h.reason.split(w.W).join('<w>')), `${id}: no em dash, no romp noun`);
        if (expect === 'name') assert.match(h.reason, BY_NAME_RE, `${id}: by the readonly value: ${h.reason.split('\n')[0]}`);
        else assert.ok(NOT_LITERAL.test(h.reason) && h.reason.includes(expect[1]), `${id}: refused as not literal, the reason naming the wrapper (${expect[1]}): ${h.reason.split('\n')[0]}`);
      }
      for (const shell of shellsFor(A, id)) {
        const r = w.run(cmd, w.NA, shell);
        assert.equal(r.changed, writers.includes(shell), `${id}: run unguarded, ${shell} ${writers.includes(shell) ? 'performs the later write onto the tracked file (no freeze there, so the guard must not skip it)' : 'froze the name or ran nothing, and left the tracked subset'}: ${cmd}: ${r.stderr}`);
      }
    }
    assert.equal(n, 19);
    // the grammar: a wrapped readonly leaves the name unreadable (no target, the word opaque), an unwrapped one resolves the frozen value
    assert.deepEqual(extractWriteTargets('x=scratch/keep.md; env readonly x=scratch/keep.md; x=docs/report.md; cp base/report.md $x', w.NA).targets, [], 'behind env the name is not frozen and not read');
    assert.deepEqual(extractWriteTargets('readonly x=docs/report.md; x=scratch/keep.md; cp base/report.md $x', w.NA).targets.map((t) => t.path), [path.join(w.NA, 'docs', 'report.md')], 'unwrapped, the readonly value resolves');
  } finally { process.env.HOME = savedHome; w.rm(); }
});

test('round 5, the catch-all refuses: a command word that is an Object.prototype key inside a body no longer throws (an own-property lookup on the compound tables), so the write after it is refused by name where the throw was swallowed into an allow; and an exception planted inside the walk refuses while a tracked project is in play, naming the exception, and passes with no project in play', () => {
  const w = sixthPassWorld();
  const savedHome = process.env.HOME;
  process.env.HOME = w.HOME;
  try {
    for (const word of ['toString', 'constructor', '__proto__', 'valueOf', 'hasOwnProperty']) {
      for (const cmd of [`if true; then ${word}; fi; cp base/report.md docs/report.md`, `{ ${word}; }; cp base/report.md docs/report.md`, `case a in a) ${word};; esac; cp base/report.md docs/report.md`]) {
        const h = w.hook(cmd, w.NA);
        assert.equal(h.status, 2, `${word} in a body throws nothing and the copy is refused: ${cmd}: ${h.reason}`);
        assert.match(h.reason, BY_NAME_RE, `by name: ${h.reason.split('\n')[0]}`);
        assert.ok(!h.reason.includes('an error of my own'), 'no internal error was hit');
      }
      assert.equal(w.hook(`if true; then ${word}; fi; cp base/report.md scratch/keep.md`, w.NA).status, 0, `${word} in a body, the untracked twin: allowed`);
    }
    // the planted throw: the walk's command reader calls path.basename, replaced here by a throw (the default export of node:path is
    // the object the hook holds, so the plant reaches it); the refusal names the exception and the project, and the throw is not swallowed
    const real = path.basename;
    try {
      path.basename = () => { throw new Error('planted by the test'); };
      const inPlay = evaluate(payload('cp base/report.md scratch/keep.md', w.NA));
      assert.ok(inPlay && inPlay.includes('an error of my own (Error: planted by the test)') && inPlay.includes(w.NA) && inPlay.includes('track-edit'), `the planted throw refuses, naming it and the project: ${inPlay}`);
      assert.ok(!/\u2014/.test(inPlay) && !ROMP_NOUNS.test(inPlay.split(w.W).join('<w>')), 'no em dash, no romp noun');
      assert.equal(evaluate(payload('cp x.md y.md', w.OUT)), null, 'from a cwd in no project the same throw passes: the guard\'s subject is not there');
    } finally { path.basename = real; }
    assert.equal(evaluate(payload('cp base/report.md scratch/keep.md', w.NA)), null, 'with the plant removed the copy is judged as ever');
  } finally { process.env.HOME = savedHome; w.rm(); }
});

test("round 5, regression-1: a node or python write whose path argument opens with a string literal and goes on (a `+`, a method call, python's adjacent literals) is a template the interpreter fills in, refused while a project is in play with the reason naming the appended part, where round 4's head matched neither list and allowed it; a concatenation that opens with a name stays out of model; from a cwd in no project the template is dropped like every unreadable word; the interpreters write the tracked file when the row runs", () => {
  const w = sixthPassWorld();
  const savedHome = process.env.HOME;
  process.env.HOME = w.HOME;
  try {
    const refused = [
      `node -e "require('fs').writeFileSync('docs/' + 'report.md', 'x')"`,
      `node -e "require('fs').writeFileSync('docs/report.md'.trim(), 'x')"`,
      `node -e "require('fs').copyFileSync('base/report.md', 'docs/' + 'report.md')"`,
      `node -e "require('fs').copyFileSync('base/' + 'report.md', 'docs/' + 'report.md')"`,
      `node -e "require('fs').openSync('docs/' + 'report.md', 'w')"`,
      `python3 -c "open('docs/' + 'report.md', 'w').write('x')"`,
      `python3 -c "open('docs/report' '.md', 'w').write('x')"`,
      `python3 -c "import shutil; shutil.copy('base/report.md', 'docs/' + 'report.md')"`,
    ];
    for (const cmd of refused) {
      const h = w.hook(cmd, w.NA);
      assert.equal(h.status, 2, `refused: ${cmd}: ${h.reason}`);
      assert.ok(/a path built from a template or format string/.test(h.reason) && /a string literal with more appended to it, a `\+` or a method call/.test(h.reason), `the reason names the appended part: ${h.reason.split('\n')[0]}`);
      assert.equal(w.hook(cmd, w.OUT).status, 0, `from a cwd in no project the template is dropped: ${cmd}`);
    }
    for (const cmd of [`node -e "d='docs/'; require('fs').writeFileSync(d + 'report.md', 'x')"`, `python3 -c "d='docs/'; open(d + 'report.md', 'w').write('x')"`]) {
      assert.equal(w.hook(cmd, w.NA).status, 0, `a concatenation that opens with a name is out of model, the contract's boundary: ${cmd}`);
    }
    // the grammar: the template carries the appended part; a plain literal stays literal
    assert.deepEqual(scriptTemplateTargets('node', "fs.writeFileSync('docs/' + name, x)"), ["'docs/' + name"]);
    assert.deepEqual(scriptTemplateTargets('python', "open('docs/' + name, 'w')"), ["'docs/' + name"]);
    assert.deepEqual(scriptWriteTargets('node', "fs.writeFileSync('docs/report.md', x)"), ['docs/report.md']);
    assert.deepEqual(scriptTemplateTargets('node', "fs.writeFileSync('docs/report.md', x)"), []);
    // the interpreters run the literal-first rows through real bash and write the tracked file
    for (const shell of shellsFor(['bash'], 'the literal-first concatenations')) for (const cmd of [refused[0], refused[5]]) assert.equal(w.run(cmd, w.NA, shell).changed, true, `${shell} runs the interpreter and the tracked file is written: ${cmd}`);
  } finally { process.env.HOME = savedHome; w.rm(); }
});

test("round 5, regression-4: after `>&` a word is a descriptor duplication only when it is exactly a digit run or `-` and a delimiter follows, so a glued write onto a file whose name opens with a digit or a dash (`>&2-3`, `>&2-`, `>&-2`, `>&1-`) is a write, refused in a tracked folder where it was invisible; `>>&` is never a duplication (`>>&2` appends to a file named 2 in zsh); the dups keep their reading; the shells write the files the rule names", () => {
  const w = sixthPassWorld();
  const savedHome = process.env.HOME;
  process.env.HOME = w.HOME;
  try {
    const A = ['bash', 'zsh', 'dash'];
    // [id, command from the tracked folder, the shells that create the file, the file]
    const rows = [
      ['G1', 'cd notes; printf poison >&2-3', ['bash', 'zsh'], '2-3'],
      ['G2', 'cd notes; printf poison >&2-', ['zsh'], '2-'],         // bash: a move of fd 2 (no file); dash: a syntax error
      ['G3', 'cd notes; printf poison >&-2', ['zsh'], '-2'],
      ['G4', 'cd notes; printf poison >&1-', ['zsh'], '1-'],
      ['G5', 'cd notes; printf poison >>&2', ['zsh'], '2'],          // zsh alone has >>&, and it has no dup form: a file named 2
      ['G6', 'cd notes; printf poison >>&2-3', ['zsh'], '2-3'],
      ['G7', 'cd notes; printf poison >&2x', ['bash', 'zsh'], '2x'],   // dash: "Bad fd number", nothing written
    ];
    for (const [id, cmd, writers, file] of rows) {
      const h = w.hook(cmd, w.NA);
      assert.equal(h.status, 2, `${id}: refused: ${cmd}: ${h.reason}`);
      assert.match(h.reason, BY_NAME_RE, `${id}: by name, the file in the tracked folder: ${h.reason.split('\n')[0]}`);
      assert.ok(h.reason.includes(path.join(w.NA, 'notes', file)), `${id}: the refusal names notes/${file}`);
      for (const shell of shellsFor(A, id)) {
        const r = w.run(cmd, w.NA, shell);
        assert.equal(r.changed, writers.includes(shell), `${id}: ${shell} ${writers.includes(shell) ? 'creates' : 'does not create'} notes/${file}: ${r.stderr}`);
        if (writers.includes(shell)) assert.equal(fs.existsSync(path.join(w.NA, 'notes', file)), true, `${id}: ${shell} wrote the file`);
      }
    }
    for (const cmd of ['cd notes; printf poison >&2', 'cd notes; printf poison 2>&1', 'cd notes; printf poison >&-', 'cd notes; printf poison >&23', 'cd notes; printf poison >&2;']) {
      assert.equal(w.hook(cmd, w.NA).status, 0, `a duplication is no write: ${cmd}`);
      for (const shell of shellsFor(A, cmd)) assert.equal(w.run(cmd, w.NA, shell).changed, false, `${shell} creates nothing: ${cmd}`);
    }
    // the grammar
    assert.deepEqual(lex('printf x >&2-3').segments[0].redirects.map((r) => [r.op, r.target.text]), [['>&', '2-3']]);
    assert.deepEqual(lex('printf x >>&2').segments[0].redirects.map((r) => [r.op, r.target.text]), [['>>&', '2']]);
    assert.deepEqual(lex('printf x >&2').segments[0].redirects, []);
    assert.deepEqual(lex('printf x >&-').segments[0].redirects, []);
  } finally { process.env.HOME = savedHome; w.rm(); }
});

test('round 5, the census of the lists that remain is derived from the hook\'s source: every top-level list is enumerated, named in the census with a side and a consumer line that exists, no named list is gone; a list planted in the source reds it, a list removed reds it, a consumer line moved reds it; the enumeration reads the shapes it claims and not the blind spots it states; the two write-side tables round 4 named are there with their side', () => {
  const src = fs.readFileSync(HOOK, 'utf8');
  const c = census(src);
  assert.ok(c.lists.length >= 30, `the enumeration finds the lists: ${c.lists.length}`);
  assert.deepEqual([c.unnamed, c.stale, c.unclassified, c.missingConsumer], [[], [], [], []], `the census holds: ${JSON.stringify({ unnamed: c.unnamed, stale: c.stale, unclassified: c.unclassified, missingConsumer: c.missingConsumer })}`);
  for (const name of ['BODY_CLOSER', 'CLOSERS', 'PREFIXES', 'FRAME_PEEL', 'WRITER_CASES']) assert.equal(CENSUS[name].side, 'WRITE', `${name}: a gap on the write side`);
  for (const name of ['WRAPPER_OPT', 'COPY_OPT', 'INERT_DECLARATION_FLAGS', 'VAR_ASSIGNERS']) assert.equal(CENSUS[name].side, 'REFUSE', `${name}: a gap on the refuse side`);
  assert.ok(c.lists.find((l) => l.name === 'WRITER_CASES').items.includes('cp') && c.lists.find((l) => l.name === 'ROOT_MARKERS').items.includes('.trackchanges'), 'the pseudo-lists carry their items');
  // planted: a list the census does not name reds
  const planted = census(src + "\nconst PLANTED_WRAPPERS = new Set(['unshare']);\n");
  assert.deepEqual(planted.unnamed, [`PLANTED_WRAPPERS (line ${src.split('\n').length + 1})`], 'a planted list is unnamed');
  // removed: a named list that is gone reds
  const removed = census(src.replace("const TIME_OPTIONS = new Set(['-p', '--']);", ''));
  assert.deepEqual(removed.stale, ['TIME_OPTIONS']);
  // moved: a consumer rewritten without the table reds
  const moved = census(src.replace(CENSUS.BODY_CLOSER.consumer, "else if (head === 'if') frames.push({ kind: head, moved: false });"));
  assert.deepEqual(moved.missingConsumer, ['BODY_CLOSER']);
  // the shapes read, and the blind spots stated: a comment, an indented declaration and a Map are not lists here
  const shapes = enumerateLists("const A = new Set(['a']);\nexport const B = ['b'];\nconst C = { c: 1 };\nconst D = Object.fromEntries([]);\nconst E = new RegExp('x|y');\n// const F = new Set(['f']);\n  const G = new Set(['g']);\nconst H = new Map();\nlet I = [];\n");
  assert.deepEqual(shapes.map((l) => l.name), ['A', 'B', 'C', 'D', 'E', 'I']);
  assert.equal(Object.keys(CENSUS).length, c.lists.length, 'the census names exactly the lists enumerated');
});

// The since sweep (round 5, tests-2 and extra6-2). A corpus entry's `since` names the pass at which it NEWLY refuses: at that
// pass's head the row refuses and at the head before it the row is allowed. Round 4 replayed every row against the branch and
// found three labels false (the plain `export n` row and the PWD row refused since the first commit, the prefix-HOME row turned
// at the walk-around lens); no test caught it. This sweep runs every since row through the hook AS IT WAS at the labelled pass's
// head and at that head's parent, taken from this checkout's history with `git archive`; the label `round 5` is this tree's hook
// against the previous head. A checkout without the history (CI's shallow checkout) prints a loud NOT RUN line and runs the
// history-free half alone: every since label in the corpus is one the table knows.
const SINCE_HEADS = {
  'third pass': '50e85deec133b2ef5a83fb4f0971d6f65e9253b6',
  'walk-around lens': '19a69742dd7e740d69a769b0c3eff60c2696c47a',
  'fifth commit': '9c20cdff7a091b83c2f948073be141caf1e81d49',
  'B2 as ruled': 'fbfc151f729431d881af125b93f524182455975c',
  'seventh pass': 'befa93b3f2b37bf3cc830ac9459a8fdb1becda51',
  'seventh pass, the attacker': 'a36e34832173180184fb595ca1c6d0e8b85b8a55',
  'round 5': null,   // this tree; its previous head is the attacker's
};
test("round 5, the since sweep: every corpus row marked `since` newly refuses at the pass it names (allowed by the hook at the head before that pass, refused at the pass's head, both hooks taken from this checkout's history and run as processes over the corpus world); every label is one the sweep's table knows; a checkout without the history says so loudly", () => {
  const since = CORPUS.filter((e) => e.since);
  assert.ok(since.length >= 20, `since rows: ${since.length}`);
  for (const e of since) assert.ok(Object.hasOwn(SINCE_HEADS, e.since), `a since label the sweep knows: ${e.since}: ${e.command}`);
  const REPO = path.resolve(path.dirname(HOOK), '..');
  const git = (...args) => spawnSync('git', ['-C', REPO, ...args], { encoding: 'utf8' });
  const shas = Object.values(SINCE_HEADS).filter(Boolean);
  const missing = shas.filter((sha) => git('cat-file', '-e', `${sha}^{commit}`).status !== 0);
  if (missing.length || git('rev-parse', '--is-inside-work-tree').stdout.trim() !== 'true') {
    console.error(`NOT RUN: the since sweep needs this branch's history and ${missing.length ? `${missing.length} of its ${shas.length} pass heads are not in this checkout` : 'this is not a git checkout'}, so it did not run (the label check above ran)`);
    return;
  }
  const { home, cwds, fill } = corpusWorld();
  const scratch = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-bash-guard-since-'));
  const savedHome = process.env.HOME;
  process.env.HOME = home;
  try {
    const hookAt = (sha) => {
      if (sha == null) return HOOK;
      const dir = path.join(scratch, sha.slice(0, 12));
      if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir);
        const ar = spawnSync('git', ['-C', REPO, 'archive', sha, 'hooks/romp-track-bash-guard.mjs', 'vendor/track-changents'], { maxBuffer: 64 * 1024 * 1024 });   // no shell: the probe rule holds for plumbing too
        assert.equal(ar.status, 0, `git archive ${sha}: ${String(ar.stderr)}`);
        const un = spawnSync('tar', ['-x', '-C', dir], { input: ar.stdout });
        assert.equal(un.status, 0, `tar for ${sha}: ${String(un.stderr)}`);
      }
      return path.join(dir, 'hooks', 'romp-track-bash-guard.mjs');
    };
    const parentOf = (sha) => (sha == null ? SINCE_HEADS['seventh pass, the attacker'] : git('rev-parse', `${sha}^`).stdout.trim());
    const verdict = (hook, e) => spawnSync(process.execPath, [hook], { input: payload(fill(e.command), cwds[e.cwd]), encoding: 'utf8', env: { PATH: process.env.PATH, HOME: home, ROMP_SID } }).status;
    const bad = [];
    for (const e of since) {
      const at = verdict(hookAt(SINCE_HEADS[e.since]), e);
      const before = verdict(hookAt(parentOf(SINCE_HEADS[e.since])), e);
      if (!(at === 2 && before === 0)) bad.push(`${e.since}: ${e.command} (at the pass: ${at}, before it: ${before})`);
    }
    assert.deepEqual(bad, [], `every since row flips at the pass it names (2 at the pass, 0 before)`);
    console.log(`# the since sweep: ${since.length} rows, ${Object.keys(SINCE_HEADS).length} labels, every row newly refuses at its pass`);
  } finally { process.env.HOME = savedHome; fs.rmSync(scratch, { recursive: true, force: true }); }
});
