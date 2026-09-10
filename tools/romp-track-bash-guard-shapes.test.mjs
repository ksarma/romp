// The Bash-side track guard (hooks/romp-track-bash-guard.mjs; plans/file-review.md, decision 47): the
// shell shapes its review (2026-09-10) found misread, each pinned here in both directions where the
// shape has two (a write the guard missed, and an ordinary command it refused for a file the command
// never touches). A subshell's cd ends at its `)`; a heredoc body belongs to the command that opened
// it, so `python3 - <<EOF && echo done` is read; a shell fed its script by heredoc is read like `sh -c`;
// `bash -lc` is `bash -l -c`; `python3 -u <<EOF` still reads stdin; `sudo -u USER cp` is a cp; `[[ a > b ]]`
// compares; `Path('x').open('w')` and `open(mode='w', file='x')` are writes. The verdict builds the
// project's link closure once per call, not once per landing file, so a directory copy costs one
// walk. And the branches no other test reached (the prefixes, pushd and popd, node -p and --print,
// the NUL-byte rule) are pinned so removing one fails by name. The review's second round added:
// `&&` and `||` inside `[[ ... ]]` stay in the test; a quoted `[[` is data; a brace list is expanded
// before the operands are read; a wrapped `open(` call and a here-string script are scanned; a
// process substitution is a word, not a segment break; a glob operand is expanded against the
// filesystem; a directory source is walked to every file; a symlink to a tracked file is the
// tracked file; and store-io's isTrackedFile is pinned to the steps the verdict copies. Synthetic:
// a project under os.tmpdir(), invented paths, no session data.
//
// Run: node --test tools/romp-track-bash-guard-shapes.test.mjs
import { test, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

import { evaluate, extractWriteTargets, scriptWriteTargets, lex, isGuardedPath } from '../hooks/romp-track-bash-guard.mjs';

const HOOK = fileURLToPath(new URL('../hooks/romp-track-bash-guard.mjs', import.meta.url));
const ROMP_SID = '11111111-2222-3333-4444-555555555555';

let proj;       // the scratch project: .trackchanges/ at its root, tracked docs/report.md and notes/
let report;     // proj/docs/report.md, tracked text
let rootFile;   // proj/report.md, untracked, at the root

beforeEach(() => {
  proj = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'romp-bash-guard-shapes-')));
  for (const d of ['.trackchanges', 'docs', 'base', 'notes', 'sub']) fs.mkdirSync(path.join(proj, d));
  fs.writeFileSync(path.join(proj, '.trackchanges', 'config.json'),
    JSON.stringify({ v: 2, tracked: ['docs/report.md', 'notes/'] }));
  report = path.join(proj, 'docs', 'report.md');
  rootFile = path.join(proj, 'report.md');
  fs.writeFileSync(report, 'The api session cut tail latency by 40%.\n');
  fs.writeFileSync(rootFile, 'a root copy\n');
  fs.writeFileSync(path.join(proj, 'base', 'report.md'), 'an older copy\n');
  delete process.env.TRACKCHANGES_ROOT;
});

afterEach(() => {
  try { fs.rmSync(proj, { recursive: true, force: true }); } catch { /* ignore */ }
});

const payload = (command, cwd = proj) => JSON.stringify({ tool_name: 'Bash', tool_input: { command }, cwd });
const targets = (command, cwd = proj) => extractWriteTargets(command, cwd).targets.map((t) => t.path).sort();
const PY_WRITE = "open('docs/report.md','w').write('x')";

// ── a cd inside a subshell ends at its ) ───────────────────────────

test('a cd inside ( ... ) moves nothing after the ): the untracked write after it is allowed, the tracked one refused', () => {
  // the shell writes proj/report.md (untracked); before the fix the hook resolved it under docs/ and refused
  for (const cmd of [
    '(cd docs && ls) && cp base/report.md report.md',
    '(cd docs; make) ; echo x > report.md',
    'if (cd docs); then cp base/report.md report.md; fi',
    '( cd docs ) ; tee report.md < base/report.md',
    '(cd notes && ls) && echo x > new.md',
  ]) {
    assert.deepEqual(targets(cmd), [path.join(proj, path.basename(cmd.includes('new.md') ? 'new.md' : 'report.md'))], cmd);
    assert.equal(evaluate(payload(cmd)), null, `allowed: ${cmd}`);
  }
  // the other direction: the shell writes the tracked docs/report.md; before the fix the hook resolved it elsewhere and passed
  for (const cmd of [
    '(cd base && ls) && cp base/report.md docs/report.md',
    '(cd sub; pwd); echo x > docs/report.md',
    '(cd sub && make) && cp base/report.md docs/report.md',
    '(cd sub; ls) | cat && cp base/report.md docs/report.md',
  ]) {
    assert.deepEqual(targets(cmd), [report], cmd);
    assert.ok(evaluate(payload(cmd)), `refused: ${cmd}`);
  }
  assert.equal(targets('(cd docs && ls) && echo x > new.md', path.join(proj, 'notes')).length, 1);
  assert.ok(evaluate(payload('(cd .. && ls) && echo x > new.md', path.join(proj, 'notes'))), 'from inside the tracked folder the write stays there');
});

test('a write inside the subshell, a brace group and a nested subshell resolve as the shell does', () => {
  assert.deepEqual(targets('(cd docs && cp ../base/report.md report.md)'), [report], 'inside the parentheses the cd holds');
  assert.deepEqual(targets('{ cd docs; } && cp ../base/report.md report.md'), [report], 'a brace group runs in the current shell: its cd holds after');
  assert.deepEqual(targets('(cd sub && (cd ../docs && ls) && echo x > report.md)'), [path.join(proj, 'sub', 'report.md')], 'the inner ) restores the outer subshell\'s dir');
  assert.deepEqual(targets('cd docs && (cd ../sub) && echo x > report.md'), [report], 'a cd before the subshell still holds after it');
  assert.deepEqual(targets('(cd docs); cd sub; echo x > report.md'), [path.join(proj, 'sub', 'report.md')]);
});

test('a cd inside an if, loop or case body leaves the cwd unknown once the body closes: the body may not run', () => {
  // before the fix `if false; then cd docs; fi; cp base/report.md report.md` was refused as a write to docs/report.md
  for (const cmd of [
    'if false; then cd docs; fi; cp base/report.md report.md',
    'while false; do cd docs; done; echo x > report.md',
    'for d in docs; do cd "$d"; done; echo x > report.md',
    'case $x in a) cd docs;; esac; echo x > report.md',
  ]) {
    assert.deepEqual(targets(cmd), [], `unresolvable after the body: ${cmd}`);
    assert.equal(evaluate(payload(cmd)), null, `allowed: ${cmd}`);
  }
  assert.deepEqual(targets('if true; then cd docs; cp ../base/report.md report.md; fi'), [report], 'inside the body the cd holds');
  assert.deepEqual(targets('if true; then echo x > docs/report.md; fi; cp base/report.md docs/report.md'), [report, report], 'a body with no cd leaves the cwd as it was (evaluate dedupes)');
  assert.deepEqual(targets('for f in a b; do cp "$f" docs/report.md; done; echo x > docs/report.md'), [report, report], 'the loop body and the echo each name it');
  assert.deepEqual(targets('if x; then (cd docs); fi; cp base/report.md docs/report.md'), [report], 'a subshell cd inside a body moves nothing');
  assert.deepEqual(targets('case $x in a) echo x > docs/report.md;; b) ls;; esac'), [report], 'a ) that ends a case pattern closes no subshell');
});

// ── heredoc bodies belong to the command that opened them ──────────

test('a python or node heredoc script followed by &&, |, ; or & on the opener line is read', () => {
  const body = `\n${PY_WRITE}\nEOF`;
  for (const opener of [
    "python3 - <<'EOF' && echo done",
    "python3 - <<'EOF' | tee /dev/null",
    "python3 - <<'EOF' ; echo done",
    "python3 - <<'EOF' || echo failed",
    "python3 - <<'EOF' &",
    "python3 - <<EOF 2>&1 | tail -1",
  ]) {
    const cmd = opener + body;
    assert.ok(targets(cmd).includes(report), `the tracked path is a target of: ${JSON.stringify(opener)}`);
    assert.ok(evaluate(payload(cmd)), `refused: ${JSON.stringify(opener)}`);
  }
  assert.deepEqual(targets("node - <<'EOF' && echo done\nrequire('fs').writeFileSync('docs/report.md', 'x')\nEOF"), [report]);
  const { segments } = lex("python3 - <<'EOF' && echo done\nx = 1\nEOF");
  assert.deepEqual(segments.map((s) => [s.words.map((w) => w.text).join(' '), s.heredocs.length, s.op]),
    [['python3 -', 1, '&&'], ['echo done', 0, '\n']], 'the body sits on the python segment; op names the operator that ended each');
});

test('a heredoc piped into python or node is its stdin too; a heredoc redirected into a file is the redirect\'s write, not a script', () => {
  assert.deepEqual(targets(`cat <<'EOF' | python3 -\n${PY_WRITE}\nEOF`), [report]);
  assert.deepEqual(targets(`cat <<'EOF' | tee log.txt | python3\n${PY_WRITE}\nEOF`), [path.join(proj, 'log.txt'), report].sort(), 'through a tee');
  assert.deepEqual(targets(`cat <<'EOF' > docs/other.md && echo done\n${PY_WRITE}\nEOF`), [path.join(proj, 'docs', 'other.md')], 'data into other.md');
  assert.deepEqual(targets(`cat <<'EOF' && python3 -\n${PY_WRITE}\nEOF`), [], 'after && the body is not python\'s stdin');
});

// ── shells fed a literal script ────────────────────────────────────

test('a shell reading its script from a heredoc is read like sh -c: bash <<EOF, bash -s <<EOF, bash - <<EOF, sh <<EOF', () => {
  const body = '\ncp base/report.md docs/report.md\nEOF';
  for (const opener of ["bash <<'EOF'", "bash -s <<'EOF'", "bash - <<'EOF'", 'bash <<EOF', "bash -euo pipefail <<'EOF'", "sh <<'EOF'", "cat <<'EOF' | bash", "cat <<'EOF' | sudo bash -s"]) {
    const cmd = opener + body;
    assert.deepEqual(targets(cmd), [report], opener);
    assert.ok(evaluate(payload(cmd)), `refused: ${opener}`);
  }
  assert.deepEqual(targets("bash run.sh <<'EOF'\ncp base/report.md docs/report.md\nEOF"), [], 'a script file: the body is its input, not its commands');
  assert.deepEqual(targets("bash <<'EOF'\ncd docs && cp ../base/report.md report.md\nEOF\ncp base/report.md report.md"), [report, rootFile].sort(), 'the script\'s cd stays in the child shell');
});

test('a -c in an option cluster is a -c: bash -lc, sh -ec, bash -xc; a variable script there is opaque', () => {
  for (const cmd of [
    "bash -lc 'cp base/report.md docs/report.md'",
    "sh -ec 'cp base/report.md docs/report.md'",
    "bash -xc 'cp base/report.md docs/report.md'",
    "zsh -ic 'cp base/report.md docs/report.md'",
    "bash -euo pipefail -c 'cp base/report.md docs/report.md'",
    "bash -l -c 'cp base/report.md docs/report.md'",
    "bash -c -l 'cp base/report.md docs/report.md'",
    "bash -c -- 'cp base/report.md docs/report.md'",
  ]) {
    assert.deepEqual(targets(cmd), [report], cmd);
    assert.ok(evaluate(payload(cmd)), `refused: ${cmd}`);
  }
  assert.ok(extractWriteTargets('bash -lc "$SCRIPT"', proj).opaque, 'a script the hook cannot read is marked so');
  assert.equal(evaluate(payload('bash -lc "$SCRIPT"')), null);
  assert.deepEqual(targets('bash -x run.sh'), [], 'no -c, a script file');
});

// ── interpreter options before a heredoc ───────────────────────────

test('python or node with options and a heredoc on stdin is read: -u, -B, -I, -X utf8, --input-type=module, --no-warnings', () => {
  const py = `\n${PY_WRITE}\nEOF`;
  for (const opener of ["python3 -u <<'EOF'", "python3 -B <<'EOF'", "python3 -I <<'EOF'", "python3 -X utf8 <<'EOF'", "python3 -W ignore -u <<'EOF'", "python3 -u - <<'EOF'"]) {
    assert.deepEqual(targets(opener + py), [report], opener);
  }
  const js = "\nimport fs from 'node:fs'; fs.writeFileSync('docs/report.md', 'x')\nEOF";
  for (const opener of ["node --input-type=module <<'EOF'", "node --input-type module <<'EOF'", "node --no-warnings <<'EOF'", "node -r ./setup.cjs <<'EOF'"]) {
    assert.deepEqual(targets(opener + js), [report], opener);
  }
  assert.deepEqual(targets("python3 -m json.tool <<'EOF'\n{\"a\": 1}\nEOF"), [], 'a module: the body is its input');
  assert.deepEqual(targets("python3 -u fix.py <<'EOF'\n" + PY_WRITE + '\nEOF'), [], 'a script file after options: the body is its input');
  assert.deepEqual(targets(`python3 -uc "${PY_WRITE}"`), [report], 'a -c in a cluster');
});

// ── prefixes with options ──────────────────────────────────────────

test('a prefix with options still leads to the command: sudo -u, sudo -n, env -u, timeout -s, exec -a, time -p, command -p', () => {
  for (const cmd of [
    'sudo -u nobody cp base/report.md docs/report.md',
    'sudo -n cp base/report.md docs/report.md',
    'sudo -E -H cp base/report.md docs/report.md',
    'sudo -u nobody -- cp base/report.md docs/report.md',
    'env -u FOO cp base/report.md docs/report.md',
    'env -i FOO=1 cp base/report.md docs/report.md',
    'timeout -s KILL 5 cp base/report.md docs/report.md',
    'timeout 5 cp base/report.md docs/report.md',
    'exec -a copier cp base/report.md docs/report.md',
    'time -p cp base/report.md docs/report.md',
    'command -p cp base/report.md docs/report.md',
    'nohup cp base/report.md docs/report.md',
    'builtin echo x > docs/report.md',
    'ionice -c 3 -n 7 cp base/report.md docs/report.md',
    'stdbuf -o L tee docs/report.md',
    'stdbuf -o0 tee docs/report.md',
    'nice -n 19 ionice -c 3 sudo -n cp base/report.md docs/report.md',
  ]) {
    assert.deepEqual(targets(cmd), [report], cmd);
  }
  assert.deepEqual(targets('env -C base cp report.md ../docs/report.md'), [], 'env -C runs the command elsewhere: its relative paths are not the cwd\'s');
  assert.deepEqual(targets('sudo -D base cp report.md ../docs/report.md'), []);
});

test('pushd moves the cwd like cd; popd leaves it unknown', () => {
  assert.deepEqual(targets('pushd docs && echo x > report.md'), [report]);
  assert.deepEqual(targets('pushd docs >/dev/null; cp ../base/report.md report.md; popd'), ['/dev/null', report], 'the >/dev/null is a redirect target too');
  assert.deepEqual(targets('cd base; popd; echo x > report.md'), [], 'after popd the cwd is whatever was pushed');
  assert.deepEqual(targets(`cd base; popd; echo x > ${report}`), [report], 'an absolute path needs no cwd');
});

// ── [[ ... ]] and (( ... )) compare ────────────────────────────────

test('[[ a > b ]] and (( a > b )) compare and write nothing; [ a > b ] and test a > b redirect, as in the shell', () => {
  for (const cmd of [
    '[[ a > docs/report.md ]]',
    '[[ docs/other.md > docs/report.md ]] && echo hi',
    'if [[ "$name" > docs/report.md ]]; then echo newer; fi',
    '[[ docs/report.md < b ]]',
    '(( 3 > 2 )) && echo yes',
    'for ((i=0; i<3; i++)); do echo $i; done',
    '[[ -f docs/report.md ]] && cat docs/report.md',
  ]) {
    assert.deepEqual(targets(cmd), [], cmd);
    assert.equal(evaluate(payload(cmd)), null, `allowed: ${cmd}`);
  }
  assert.deepEqual(targets('[[ x ]] > docs/report.md'), [report], 'after ]] a > redirects again');
  assert.deepEqual(targets('[ a > docs/report.md ]'), [report], 'single brackets are a command: the shell redirects');
  assert.deepEqual(targets('test a > docs/report.md'), [report]);
  assert.deepEqual(targets('[[ a > b ]]; echo x > docs/report.md'), [report], 'the next command is not inside the test');
  assert.deepEqual(targets('[[ a>docs/report.md ]] && echo x > docs/other.md'), [path.join(proj, 'docs', 'other.md')], 'glued, the shell still compares');
  const { segments } = lex('[[ a>b ]]');
  assert.deepEqual(segments[0].words.map((w) => w.text), ['[[', 'a', '>', 'b', ']]'], 'the comparison is a word of its own');
});

test('a function definition is not a run: a cd in its body moves nothing after it; a write in it is still a target', () => {
  for (const cmd of [
    'f() { cd docs; }; cp base/report.md report.md',
    'function f() { cd docs; }\ncp base/report.md report.md',
    'f() {\n  cd docs\n  ls\n}\ncp base/report.md report.md',
    'f() { cd docs; }; g() { pushd notes; }; echo x > report.md',
  ]) {
    assert.deepEqual(targets(cmd), [rootFile], cmd);
    assert.equal(evaluate(payload(cmd)), null, `allowed: ${cmd}`);
  }
  assert.deepEqual(targets('f() { cd docs; cp ../base/report.md report.md; }'), [report], 'inside the body the cd holds');
  assert.deepEqual(targets('f() { echo x > docs/report.md; }; f'), [report], 'a write in the body is read, since the body may run');
  assert.deepEqual(targets('f() { (cd docs); echo x > report.md; }; f'), [rootFile], 'a subshell inside the body');
  assert.deepEqual(targets('cd docs; f() { cd ..; }; echo x > report.md'), [report], 'a cd before the definition holds');
});

// ── python and node write spellings ────────────────────────────────

test('Path(x).open with a write mode, open with keyword arguments in any order, io.open, and fs.openSync with a write flag are writes', () => {
  for (const script of [
    "from pathlib import Path; Path('docs/report.md').open('w').write('x')",
    "Path('docs/report.md').open(mode='a')",
    "open(mode='w', file='docs/report.md')",
    "open('docs/report.md', encoding='utf8', mode='w')",
    "open(file='docs/report.md', mode='w', encoding='utf8')",
    "open('docs/report.md', 'w', encoding='utf8')",
    "io.open('docs/report.md', 'w')",
    "with open('docs/report.md', 'r+') as f: pass",
  ]) {
    assert.deepEqual(scriptWriteTargets('python', script), ['docs/report.md'], script);
  }
  for (const script of [
    "Path('docs/report.md').open()",
    "Path('docs/report.md').open('r')",
    "open('docs/report.md', encoding='utf8')",
    "open(file='docs/report.md', mode='r')",
    "open(os.path.join(d, 'report.md'), 'w')",
    "open(f'{d}/report.md', 'w')",
    "open(name, 'w')",
  ]) {
    assert.deepEqual(scriptWriteTargets('python', script), [], `no literal write: ${script}`);
  }
  assert.deepEqual(scriptWriteTargets('python', "open('a,b.md', 'w')"), ['a,b.md'], 'a comma inside the path');
  assert.deepEqual(scriptWriteTargets('node', "fs.writeSync(fs.openSync('docs/report.md', 'w'), 'x')"), ['docs/report.md']);
  assert.deepEqual(scriptWriteTargets('node', "fs.open('docs/report.md', 'a+', cb)"), ['docs/report.md']);
  assert.deepEqual(scriptWriteTargets('node', "fs.openSync('docs/report.md', 'r')"), []);
  assert.deepEqual(scriptWriteTargets('node', "fs.openSync('docs/report.md')"), []);
  assert.ok(evaluate(payload(`python3 -c "from pathlib import Path; Path('docs/report.md').open('w').write('x')"`)));
  assert.ok(evaluate(payload(`node -e "require('fs').openSync('docs/report.md', 'w')"`)));
});

test('node inline scripts in each spelling: -e, --eval, -p, --print', () => {
  for (const flag of ['-e', '--eval', '-p', '--print']) {
    assert.deepEqual(targets(`node ${flag} "require('fs').writeFileSync('docs/report.md', 'x')"`), [report], flag);
  }
  assert.deepEqual(targets(`node -e "$SCRIPT"`), [], 'a script in a variable');
  assert.ok(extractWriteTargets('node -e "$SCRIPT"', proj).opaque);
});

// ── the refusal's words ────────────────────────────────────────────

test('the refusal speaks of a change, the person\'s word, never a suggestion', () => {
  const reason = evaluate(payload('cp base/report.md docs/report.md'));
  assert.ok(reason);
  assert.ok(!/\bsuggestions?\b/i.test(reason), `CONTEXT.md's avoided word for a change: ${reason}`);
  assert.ok(!/\b(diff|annotation)s?\b/i.test(reason.split('\n')[0]));
  assert.ok(reason.includes('for me to accept or reject'));
  assert.ok(reason.includes('track-edit'));
});

// ── the tracked binary under a text name, and the directory walk ───

test('a tracked file that is binary under a text-looking name passes: the NUL-byte rule', () => {
  const blob = path.join(proj, 'notes', 'blob.md');
  fs.writeFileSync(blob, Buffer.from([0x89, 0x50, 0x4e, 0x47, 0, 0, 0, 0x0d]));
  assert.equal(evaluate(payload('cp base/report.md notes/blob.md')), null, 'a binary cannot take a tracked edit');
  fs.writeFileSync(blob, 'text after all\n');
  assert.ok(evaluate(payload('cp base/report.md notes/blob.md')), 'the same name as text is refused');
});

// How many times `fn` lists directory `dir` (the source of a copy, or the project root).
function countReaddirs(dir, fn) {
  const real = fs.readdirSync;
  let n = 0;
  fs.readdirSync = function (p, ...rest) {
    if (path.resolve(String(p)) === dir) n++;
    return real.call(this, p, ...rest);
  };
  try { fn(); } finally { fs.readdirSync = real; }
  return n;
}

test('a directory source is walked to every file it carries: past 500 entries, and into a subfolder behind them', () => {
  // decision 47 says a directory source is walked to the files it carries, with no cap; the first
  // version stopped after 500 directory entries, so a subfolder listed after 500 files was never
  // descended and its landing on a tracked file passed (the review's second round)
  const big = path.join(proj, 'big');
  fs.mkdirSync(big);
  for (let k = 0; k < 600; k++) fs.writeFileSync(path.join(big, `f${String(k).padStart(3, '0')}.txt`), 'x');
  const { targets: t } = extractWriteTargets('cp -r big docs/new', proj);
  assert.equal(t.length, 600, 'every file, not the first 500');
  assert.ok(t.every((x) => x.path.startsWith(path.join(proj, 'docs', 'new') + path.sep)));
  // 500 plain files and a docs/ subfolder whose report.md lands on the tracked docs/report.md
  const big2 = path.join(proj, 'big2');
  fs.mkdirSync(path.join(big2, 'docs'), { recursive: true });
  for (let k = 0; k < 500; k++) fs.writeFileSync(path.join(big2, `f${k}.txt`), 'x');
  fs.writeFileSync(path.join(big2, 'docs', 'report.md'), 'lands on the tracked file\n');
  const reason = evaluate(payload('cp -r big2/. .'));
  assert.ok(reason && reason.includes(report), `the landing in the subfolder is seen: ${reason}`);
  assert.ok(evaluate(payload('cp -r big2/docs .')), 'the control: the subfolder alone');
  assert.equal(evaluate(payload('cp -r big2 base/')), null, 'the same tree into an untracked folder passes');
});

test('a directory copied into a folder that does not exist yet, under no project that tracks anything, is not walked', () => {
  // the walk is the one cost that grows with the source, so it is skipped when nothing under the landing
  // directory can be tracked: the directory is absent (so no project is nested under it) and its nearest
  // existing ancestor is under no project, or under one whose tracked list is empty
  const src = path.join(proj, 'base', 'tree');
  fs.mkdirSync(path.join(src, 'sub'), { recursive: true });
  for (let k = 0; k < 20; k++) fs.writeFileSync(path.join(src, `n${k}.md`), 'x');
  fs.writeFileSync(path.join(src, 'sub', 'report.md'), 'x');
  const elsewhere = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-bash-guard-elsewhere-'));
  try {
    fs.mkdirSync(path.join(elsewhere, '.trackchanges'));
    fs.writeFileSync(path.join(elsewhere, '.trackchanges', 'config.json'), JSON.stringify({ v: 2, tracked: [] }));
    let t;
    let walks = countReaddirs(src, () => { ({ targets: t } = extractWriteTargets(`cp -r base/tree ${elsewhere}/new`, proj)); });
    assert.equal(walks, 0, 'a project that tracks nothing: no walk');
    assert.deepEqual(t, []);
    fs.mkdirSync(path.join(elsewhere, 'new'));
    walks = countReaddirs(src, () => { ({ targets: t } = extractWriteTargets(`cp -r base/tree ${elsewhere}/new`, proj)); });
    assert.equal(walks, 0, 'the files land under new/tree, still absent: no walk');
    walks = countReaddirs(src, () => { ({ targets: t } = extractWriteTargets(`cp -r base/tree/. ${elsewhere}/new`, proj)); });
    assert.ok(walks >= 1, 'landing in an existing directory, which may hold a project of its own below it: walked');
    assert.equal(t.length, 21, 'every file, the subfolder included');
    walks = countReaddirs(src, () => { ({ targets: t } = extractWriteTargets('cp -r base/tree notes/new', proj)); });
    assert.ok(walks >= 1, 'a new folder under the project that tracks: walked');
    assert.ok(t.some((x) => x.path === path.join(proj, 'notes', 'new', 'sub', 'report.md')));
    assert.ok(evaluate(payload('cp -r base/tree notes/new')), 'and its landing files are tracked by the folder entry');
  } finally { fs.rmSync(elsewhere, { recursive: true, force: true }); }
});

// ── one closure per call ───────────────────────────────────────────

// A project whose tracked list is non-empty: a target not on the list by name falls to store-io's
// link closure, a walk of every .md under the root. Count the walks by the readdir of the root.
function countRootReaddirs(fn) {
  const real = fs.readdirSync;
  let n = 0;
  fs.readdirSync = function (p, ...rest) {
    if (path.resolve(String(p)) === proj) n++;
    return real.call(this, p, ...rest);
  };
  try { fn(); } finally { fs.readdirSync = real; }
  return n;
}

test('a directory copy to an untracked destination walks the project once, not once per landing file', () => {
  const bundle = path.join(proj, 'base', 'bundle');
  fs.mkdirSync(bundle);
  for (let k = 0; k < 40; k++) fs.writeFileSync(path.join(bundle, `n${k}.md`), `note ${k}\n`);
  for (let k = 0; k < 30; k++) fs.writeFileSync(path.join(proj, 'sub', `s${k}.md`), `filler ${k}\n`);
  let reason;
  const walks = countRootReaddirs(() => { reason = evaluate(payload('cp -r base/bundle docs/new')); });
  assert.equal(reason, null, 'docs/new/* is not tracked');
  assert.equal(walks, 1, `one closure for 40 landing files, not ${walks}`);
  const many = countRootReaddirs(() => { reason = evaluate(payload('echo a > o1.txt; echo b > o2.txt; echo c > o3.txt; echo d > o4.txt; echo e > o5.txt')); });
  assert.equal(reason, null);
  assert.equal(many, 1, 'five literal targets, one walk');
  const started = Date.now();
  evaluate(payload('cp -r base/bundle docs/new'));
  assert.ok(Date.now() - started < 2000, 'well under the installer\'s 10 s hook timeout');
});

test('the per-call closure agrees with store-io\'s isTrackedFile on every kind of path', () => {
  // explicit entry, a new file under a tracked folder, a note reached through a whole-line link
  // from a tracked note, a vetoed note, a plain untracked file, and a file in another project
  fs.writeFileSync(report, 'The api session cut tail latency by 40%.\n\n[[linked]]\n\n[[vetoed]]\n');
  fs.writeFileSync(path.join(proj, 'docs', 'linked.md'), 'reached through the link\n');
  fs.writeFileSync(path.join(proj, 'docs', 'vetoed.md'), 'the owner said no\n');
  fs.writeFileSync(path.join(proj, '.trackchanges', 'config.json'),
    JSON.stringify({ v: 2, tracked: ['docs/report.md', 'notes/'], untracked: ['docs/vetoed.md'] }));
  const cases = {
    [report]: true,
    [path.join(proj, 'notes', 'new.md')]: true,
    [path.join(proj, 'docs', 'linked.md')]: true,
    [path.join(proj, 'docs', 'vetoed.md')]: false,
    [path.join(proj, 'docs', 'other.md')]: false,
    [rootFile]: false,
  };
  const closures = new Map();
  for (const [file, expected] of Object.entries(cases)) {
    assert.equal(isGuardedPath(file), expected, `store-io: ${file}`);
    assert.equal(isGuardedPath(file, closures), expected, `memoized: ${file}`);
  }
  assert.equal(closures.size, 1, 'one closure for the one root');
  assert.ok(evaluate(payload('echo x > docs/linked.md')), 'the refusal reaches a link-tracked note through the memo');
  assert.equal(evaluate(payload('echo x > docs/vetoed.md')), null, 'the veto wins');
});

// ── the review's second round: [[ ]] with && and ||, a quoted [[ ──

test('&& and || inside [[ ... ]] stay in the test: a > after them compares; after ]] they end it and a > redirects', () => {
  // before the fix && and || ended the segment inside the test, so `[[ -n a && b > docs/report.md ]]` had
  // its > read as a redirection onto the tracked file and the command was refused though bash writes nothing
  for (const cmd of [
    '[[ -n "$x" && "$y" > docs/report.md ]] && echo newer',
    '[[ -z "$x" || "$y" > docs/report.md ]]',
    '[[ -n a && b > docs/report.md ]]',
    '[[ ( a > docs/report.md ) ]]',
    '[[ -n "$x" && ( "$y" > docs/report.md || -z "$z" ) ]]',
    'if [[ -f base/report.md && base/report.md > docs/report.md ]]; then echo newer; fi',
    'while [[ -n a || b > docs/report.md ]]; do break; done',
    '[[ "$x" == "]]" && a > docs/report.md ]]',
  ]) {
    assert.deepEqual(targets(cmd), [], cmd);
    assert.equal(evaluate(payload(cmd)), null, `allowed: ${cmd}`);
  }
  assert.deepEqual(targets('[[ -n a && b ]] && echo x > docs/report.md'), [report], 'after ]] the && ends the test and the > writes');
  assert.deepEqual(targets('[[ -n a ]] || echo x > docs/report.md'), [report]);
  const { segments } = lex('[[ -n a && b > c ]] && echo done');
  assert.deepEqual(segments.map((s) => [s.words.map((w) => w.text).join(' '), s.op]),
    [['[[ -n a && b > c ]]', '&&'], ['echo done', '']], 'one segment for the test, its && a word of it');
});

test('a quoted or escaped [[ is data, as is [[ in operand position: a > after it redirects', () => {
  // before the fix the quote-removed text `[[` switched the lexer into the test, whatever its spelling or
  // position, and every > to the end of the segment was read as a comparison: `echo "[[" > docs/report.md`
  // passed and wrote the tracked file
  for (const cmd of [
    'echo "[[" > docs/report.md',
    "printf '%s\\n' '[[' > docs/report.md",
    'echo \\[\\[ > docs/report.md',
    'echo "[[" >> docs/report.md',
    'echo [[ > docs/report.md',
    'echo "[[ a > b ]]" > docs/report.md',
    'echo "[[" ; echo x > docs/report.md',
    'echo "[[" | tee docs/report.md',
  ]) {
    assert.deepEqual(targets(cmd), [report], cmd);
    assert.ok(evaluate(payload(cmd)), `refused: ${cmd}`);
  }
  const { segments } = lex('echo "[[" > docs/report.md');
  assert.deepEqual(segments[0].redirects.map((r) => r.target.text), ['docs/report.md'], 'the > is a redirection');
});

// ── brace expansion ────────────────────────────────────────────────

test('a brace list is expanded before the operands are read: mv x{.new,}, cp {a,b}/x, tee and sed -i lists, nested lists and sequences', () => {
  // before the fix `docs/report.{md,bak}` was one literal word, a name with braces in it, never tracked
  fs.writeFileSync(path.join(proj, 'docs', 'report.md.new'), 'the replacement\n');
  const bak = path.join(proj, 'docs', 'report.bak');
  for (const [cmd, expected] of [
    ['mv docs/report.md{.new,}', [report]],
    ['cp {base,docs}/report.md', [report]],
    ['tee docs/report.{md,bak} < base/report.md', [bak, report].sort()],
    ["sed -i 's/a/b/' docs/report.{md,bak}", [bak, report].sort()],
    ['cp base/{report,other}.md docs/', [path.join(proj, 'docs', 'other.md'), report].sort()],
    ['echo x | tee docs/{re{p,q}ort,other}.md', [path.join(proj, 'docs', 'other.md'), report, path.join(proj, 'docs', 'reqort.md')].sort()],
    ['tee notes/n{1..3}.md', [1, 2, 3].map((k) => path.join(proj, 'notes', `n${k}.md`))],
    ['tee notes/n{01..03}.md', ['01', '02', '03'].map((k) => path.join(proj, 'notes', `n${k}.md`))],
    ['tee notes/{a..c}.md', ['a', 'b', 'c'].map((k) => path.join(proj, 'notes', `${k}.md`))],
    [`tee ${proj}/notes/{x,y}.md`, ['x', 'y'].map((k) => path.join(proj, 'notes', `${k}.md`))],
  ]) {
    assert.deepEqual(targets(cmd), expected, cmd);
    assert.ok(evaluate(payload(cmd)), `refused: ${cmd}`);
  }
  const { segments } = lex('mv docs/report.md{.new,}');
  assert.deepEqual(segments[0].words.map((w) => w.text), ['mv', 'docs/report.md.new', 'docs/report.md'], 'two operands');
  assert.ok(segments[0].words.every((w) => w.literal));
});

test('what a brace list does not write: three operands and no directory, an ambiguous redirect, {x}, a quoted brace, a list past the cap', () => {
  assert.deepEqual(targets('cp base/report.md docs/report.{md,bak}'), [], 'cp stops: the last operand is not a directory');
  assert.equal(evaluate(payload('cp base/report.md docs/report.{md,bak}')), null);
  assert.deepEqual(targets('mkdir -p docs/{a,b}; cp base/report.md docs/{a,b}/report.md'), []);
  assert.deepEqual(targets('echo x > docs/{report,other}.md'), [], 'an ambiguous redirect: the shell writes nothing');
  assert.equal(evaluate(payload('echo x > docs/{report,other}.md')), null);
  assert.deepEqual(targets('echo x > docs/{report}.md'), [path.join(proj, 'docs', '{report}.md')], 'no comma: text');
  assert.deepEqual(targets("echo x > 'docs/{report,other}.md'"), [path.join(proj, 'docs', '{report,other}.md')], 'quoted: text');
  assert.deepEqual(targets('echo x > docs/\\{report,other\\}.md'), [path.join(proj, 'docs', '{report,other}.md')], 'escaped: text');
  assert.deepEqual(targets('echo x > "docs/${d}.md"'), [], 'a parameter expansion is not a brace list');
  assert.deepEqual(targets('tee notes/n{1..1000}.md'), [], 'past the cap the word is unresolvable and passes');
  assert.deepEqual(targets('{ echo x; } > docs/report.md'), [report], 'a brace group is a group, and its redirection writes');
  assert.deepEqual(targets("awk '{print}' base/report.md > docs/report.md"), [report]);
});

// ── the python scan across lines, and a here-string script ─────────

test('a python open( call whose arguments span lines is read: a formatter wraps a heredoc script that way', () => {
  // before the fix the argument class excluded newlines, so the wrapped call matched nothing and the
  // write landed raw while the one-line spelling was refused
  const wrapped = "with open(\n    'docs/report.md',\n    'w',\n) as f:\n    f.write('x')";
  assert.deepEqual(scriptWriteTargets('python', wrapped), ['docs/report.md']);
  assert.deepEqual(scriptWriteTargets('python', "open(\n    'docs/report.md',\n    mode='w',\n)"), ['docs/report.md']);
  assert.deepEqual(scriptWriteTargets('python', "Path(\n    'docs/report.md'\n).open(\n    'w'\n)"), ['docs/report.md']);
  assert.deepEqual(scriptWriteTargets('python', "open('docs/report.md',\n     'w')"), ['docs/report.md']);
  assert.deepEqual(scriptWriteTargets('python', "open(\n    'docs/report.md',\n    'r',\n)"), [], 'a read mode, wrapped');
  assert.deepEqual(scriptWriteTargets('python', "open(\n    os.path.join(d, 'report.md'),\n    'w',\n)"), [], 'a nested call, wrapped');
  assert.deepEqual(targets(`python3 - <<'EOF'\n${wrapped}\nEOF`), [report]);
  assert.ok(evaluate(payload(`python3 - <<'EOF'\n${wrapped}\nEOF`)));
});

test('a here-string is a script on stdin like a heredoc: python3 - <<< "...", node <<< "...", bash <<< "..."', () => {
  // before the fix the <<< word was dropped as data and never reached the stdin scans, while the same
  // script as -c or as a heredoc was refused
  for (const cmd of [
    `python3 - <<< "${PY_WRITE}"`,
    `python3 <<< "${PY_WRITE}"`,
    `python3 -u - <<< "${PY_WRITE}"`,
    `node <<< "require('fs').writeFileSync('docs/report.md', 'x')"`,
    `node - <<< "require('fs').writeFileSync('docs/report.md', 'x')"`,
    'bash <<< "cp base/report.md docs/report.md"',
    "sh -s <<< 'cp base/report.md docs/report.md'",
    `cat <<< "${PY_WRITE}" | python3 -`,
  ]) {
    assert.deepEqual(targets(cmd), [report], cmd);
    assert.ok(evaluate(payload(cmd)), `refused: ${cmd}`);
  }
  assert.deepEqual(targets('cmd <<< docs/report.md'), [], 'the here-string operand is data, not a write target');
  assert.deepEqual(targets(`python3 - <<< "print(open('docs/report.md').read())"`), [], 'a read');
  assert.deepEqual(targets('python3 - <<< "$SCRIPT"'), [], 'a script in a variable names nothing');
  assert.deepEqual(targets(`cat <<< "${PY_WRITE}" && python3 -`), [], 'after && the string is not python\'s stdin');
  assert.deepEqual(targets('cat < base/report.md > docs/other.md'), [path.join(proj, 'docs', 'other.md')], 'a < operand is a file read, not data');
});

// ── process substitution ───────────────────────────────────────────

test('a process substitution is a word, not a segment break: tee >(cat) file names file, and the command inside is read', () => {
  // before the fix >( was read as a > redirection whose target the ( then dropped, and the words after the )
  // began a new segment headed by the path itself, so tee's operand was never seen
  for (const cmd of [
    'echo x | tee >(cat) docs/report.md',
    'echo x | tee -a >(wc -l) docs/report.md',
    'tee >(cat) >(cat) docs/report.md',
    'cp <(cat base/report.md) docs/report.md',
    'sort <(cat base/report.md) -o docs/report.md',
    'echo hi > >(tee docs/report.md)',
    'diff <(cat a) <(tee docs/report.md < base/report.md)',
  ]) {
    assert.deepEqual(targets(cmd), [report], cmd);
    assert.ok(evaluate(payload(cmd)), `refused: ${cmd}`);
  }
  for (const cmd of ['cat <(echo hi) > docs/other.md', 'diff <(cat docs/report.md) <(cat base/report.md)', 'tee >(cat) report.md']) {
    assert.equal(evaluate(payload(cmd)), null, `allowed: ${cmd}`);
  }
  assert.deepEqual(targets('cat <(echo hi) > docs/other.md'), [path.join(proj, 'docs', 'other.md')]);
  assert.deepEqual(targets('tee >(cat) report.md'), [rootFile]);
  const { segments } = lex('tee >(cat) docs/report.md');
  assert.equal(segments.length, 1, 'one segment');
  assert.deepEqual(segments[0].words.map((w) => w.text), ['tee', '>(cat)', 'docs/report.md']);
  assert.deepEqual(segments[0].subs, ['cat'], 'the command inside is read like a $(...)');
  assert.ok(!segments[0].words[1].literal, 'the word stands for a /dev/fd path the hook cannot resolve');
});

// ── pathname expansion ─────────────────────────────────────────────

test('a glob operand is expanded against the filesystem as the shell expands it: a glob source into a tracked folder is refused', () => {
  // before the fix a landing word took the SOURCE's literal flag, so `cp drafts/*.md notes/` named nothing and
  // each file landed raw under the tracked folder, while `cp drafts/a.md notes/` was refused
  fs.mkdirSync(path.join(proj, 'drafts', 'sub'), { recursive: true });
  for (const [f, text] of [['a.md', 'a'], ['b.md', 'b'], ['c.txt', 'c'], [path.join('sub', 'd.md'), 'd']]) fs.writeFileSync(path.join(proj, 'drafts', f), text + '\n');
  fs.writeFileSync(path.join(proj, 'docs', 'other.md'), 'untracked prose\n');
  const inNotes = (...names) => names.map((n) => path.join(proj, 'notes', n)).sort();
  assert.deepEqual(targets('cp drafts/*.md notes/'), inNotes('a.md', 'b.md'));
  assert.deepEqual(targets('cp -r drafts/* notes/'), inNotes('a.md', 'b.md', 'c.txt', path.join('sub', 'd.md')), 'a directory matched by the glob is walked like a directory source');
  assert.deepEqual(targets('cp drafts/* notes'), inNotes('a.md', 'b.md', 'c.txt', path.join('sub', 'd.md')), 'the walk does not read -r (cp without it skips the directory: a miss on the safe side)');
  assert.deepEqual(targets('cp -t notes drafts/*.md'), inNotes('a.md', 'b.md'));
  assert.deepEqual(targets('mv drafts/?.md notes/'), inNotes('a.md', 'b.md'));
  assert.deepEqual(targets('cp drafts/[ab].md notes/'), inNotes('a.md', 'b.md'));
  assert.deepEqual(targets('cp drafts/[!a]*.md notes/'), inNotes('b.md'));
  assert.deepEqual(targets('cp drafts/a*.md docs/report.md'), [report], 'a glob source and a file destination');
  for (const cmd of ['cp drafts/*.md notes/', 'cp -t notes drafts/*', 'mv drafts/* notes/', 'cp drafts/a*.md docs/report.md', 'install -m 644 drafts/*.md notes/']) {
    assert.ok(evaluate(payload(cmd)), `refused: ${cmd}`);
  }
  // the other operands a glob can name
  assert.deepEqual(targets("sed -i 's/a/b/' docs/*.md"), [path.join(proj, 'docs', 'other.md'), report].sort());
  assert.deepEqual(targets('cat x | tee docs/rep*.md'), [report]);
  assert.deepEqual(targets("perl -pi -e 's/a/b/' docs/*"), [path.join(proj, 'docs', 'other.md'), report].sort());
  assert.deepEqual(targets('echo x > docs/rep*.md'), [report], 'one match for a redirection: the shell writes it');
  assert.deepEqual(targets('cp base/report.md docs/rep*.md'), [report], 'one match for the destination');
  assert.deepEqual(targets('tee */report.md'), [path.join(proj, 'base', 'report.md'), report].sort(), 'a glob directory and a literal tail that must exist');
  assert.deepEqual(targets('cd doc* && echo x > report.md'), [report], 'a cd through a glob with one match moves there');
  assert.deepEqual(targets('cd */ && echo x > report.md'), [], 'several matches: the cwd is unknown');
  assert.ok(evaluate(payload("sed -i 's/a/b/' docs/*.md")));
});

test('what a glob does not write: several destination matches, no match, a quoted glob, a glob after a cd the lexer cannot read, dotfiles', () => {
  fs.writeFileSync(path.join(proj, 'docs', 'other.md'), 'untracked prose\n');
  fs.writeFileSync(path.join(proj, 'notes', '.hidden.md'), 'h\n');
  assert.deepEqual(targets('cp base/report.md docs/*.md'), [], 'two matches for the destination: cp stops, target is not a directory');
  assert.equal(evaluate(payload('cp base/report.md docs/*.md')), null);
  assert.deepEqual(targets('cp base/report.md report.md docs/report.md'), [], 'the same without a glob: three operands and no directory');
  assert.deepEqual(targets('cp base/*.rst notes/'), [], 'no match: zsh runs nothing, bash names a file the session did not mean');
  assert.equal(evaluate(payload('cp base/*.rst notes/')), null);
  assert.deepEqual(targets('echo x > docs/*.md'), [], 'two matches for a redirection: ambiguous, the shell writes nothing');
  assert.deepEqual(targets("cp base/report.md 'notes/*.md'"), [path.join(proj, 'notes', '*.md')], 'a quoted glob is a name');
  assert.ok(evaluate(payload("cp base/report.md 'notes/*.md'")), 'and under the tracked folder that name is tracked');
  assert.deepEqual(targets('cp base/report.md notes/\\*.md'), [path.join(proj, 'notes', '*.md')], 'escaped: a name');
  assert.deepEqual(targets('cd "$D" && cp *.md notes/'), [], 'a relative glob after a cd the lexer cannot read is unresolvable');
  assert.deepEqual(targets('tee notes/*'), [], 'a * does not match a name starting with a dot');
  assert.deepEqual(targets('tee notes/.*'), [path.join(proj, 'notes', '.hidden.md')], 'a pattern starting with a dot does');
  assert.deepEqual(targets('tee notes/[.]hidden.md'), [], 'nor does a class');
  const { segments } = lex('cp drafts/*.md "notes/*.md"');
  assert.ok(segments[0].words[1].glob && !segments[0].words[1].literal, 'the unquoted glob is marked so');
  assert.ok(!segments[0].words[2].glob && segments[0].words[2].literal, 'the quoted one is a literal name');
  assert.ok(!extractWriteTargets('cp drafts/*.md notes/', proj).opaque, 'a glob is not an opaque command');
});

// ── the name the kernel opens ──────────────────────────────────────

test('a symlink to a tracked file is the tracked file: a write through it, inside or outside the project, is refused; a tracked name that is itself a link stays refused', () => {
  // before the fix the path was judged by its spelling alone, so `echo x > free.md` with free.md a link to
  // the tracked docs/report.md passed and rewrote the tracked file
  const elsewhere = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-bash-guard-links-'));
  try {
    fs.symlinkSync(report, path.join(proj, 'free.md'));
    fs.mkdirSync(path.join(elsewhere, 'o'));
    fs.symlinkSync(report, path.join(elsewhere, 'o', 'l.md'));
    fs.symlinkSync(path.join(proj, 'docs'), path.join(proj, 'linkdir'));
    fs.symlinkSync(path.join(proj, 'notes'), path.join(proj, 'linked'));
    fs.symlinkSync(path.join(proj, 'notes', 'newer.md'), path.join(proj, 'dangling'));
    fs.symlinkSync(rootFile, path.join(proj, 'tolink.md'));
    for (const cmd of [
      'echo x > free.md',
      'cp base/report.md free.md',
      "sed -i 's/a/b/' free.md",
      `echo x > ${path.join(elsewhere, 'o', 'l.md')}`,
      'echo x > linkdir/report.md',
      'echo x > linked/new.md',
      'echo x > dangling',
    ]) {
      assert.ok(evaluate(payload(cmd)), `refused: ${cmd}`);
    }
    for (const cmd of ['echo x > tolink.md', 'echo x > linkdir/new.md', 'cat free.md', `cp free.md ${elsewhere}/copy.md`]) {
      assert.equal(evaluate(payload(cmd)), null, `allowed: ${cmd}`);
    }
    assert.equal(isGuardedPath(path.join(proj, 'free.md')), true, 'through store-io directly');
    assert.equal(isGuardedPath(path.join(elsewhere, 'o', 'l.md'), new Map()), true, 'and through the per-call closure');
    assert.equal(isGuardedPath(path.join(proj, 'dangling'), new Map()), true, 'a dangling link into the tracked folder');
    assert.equal(isGuardedPath(path.join(proj, 'tolink.md')), false, 'a link to an untracked file');
    // the tracked file itself a link out of the project: its name is tracked, so the write is refused as before
    fs.rmSync(report);
    fs.writeFileSync(path.join(elsewhere, 'ext.md'), 'outside\n');
    fs.symlinkSync(path.join(elsewhere, 'ext.md'), report);
    assert.ok(evaluate(payload('echo x > docs/report.md')));
  } finally { fs.rmSync(elsewhere, { recursive: true, force: true }); }
});

// ── the steps the verdict copies from store-io ─────────────────────

test('store-io\'s isTrackedFile has the three steps trackedIn copies, in that order, so a vendored change to them fails here by name', () => {
  // the verdict runs isTrackedFile's steps with the link closure memoised per call (one walk for a directory
  // copy, not one per landing file); the copy holds only while store-io's own function keeps these steps
  const storeIo = fs.readFileSync(fileURLToPath(new URL('../vendor/track-changents/store-io.mjs', import.meta.url)), 'utf8');
  const m = storeIo.match(/export function isTrackedFile\(vaultRoot, file\) \{\n([\s\S]*?)\n\}/);
  assert.ok(m, 'store-io exports isTrackedFile(vaultRoot, file)');
  const steps = m[1].split('\n').map((l) => l.replace(/\s*\/\/.*$/, '').trim()).filter(Boolean);
  assert.deepEqual(steps, [
    'const rel = relPathFor(vaultRoot, file);',
    'if (engine.isTracked(untrackedPaths(vaultRoot), rel)) return false;',
    'const list = trackedPaths(vaultRoot);',
    'if (engine.isTracked(list, rel)) return true;',
    'if (!list.length) return false;',
    'return trackedClosure(vaultRoot).has(rel);',
  ], 'store-io\'s isTrackedFile changed: mirror the change in trackedIn (hooks/romp-track-bash-guard.mjs), then update this pin');
  const hook = fs.readFileSync(HOOK, 'utf8');
  const body = hook.match(/function trackedIn\(root, file, closures\) \{\n([\s\S]*?)\n\}/);
  assert.ok(body, 'the hook has trackedIn(root, file, closures)');
  for (const line of [
    'const rel = relPathFor(root, file);',
    'if (engine.isTracked(untrackedPaths(root), rel)) return false;',
    'const list = trackedPaths(root);',
    'if (engine.isTracked(list, rel)) return true;',
    'if (!list.length) return false;',
    'return closure.has(rel);',
  ]) assert.ok(body[1].includes(line), `trackedIn keeps the step: ${line}`);
});

// ── the hook as a process, on the shapes above ─────────────────────

test('the hook process rules the same way on a subshell cd, a chained heredoc and a heredoc-fed shell', () => {
  const run = (command) => {
    const env = { ...process.env, ROMP_SID };
    delete env.TRACKCHANGES_ROOT;
    return spawnSync(process.execPath, [HOOK], { input: payload(command), encoding: 'utf8', env });
  };
  assert.equal(run('(cd docs && ls) && cp base/report.md report.md').status, 0, 'ordinary work after a subshell cd');
  const missed = run('(cd base && ls) && cp base/report.md docs/report.md');
  assert.equal(missed.status, 2, missed.stderr);
  assert.ok(missed.stderr.includes(report));
  assert.equal(run(`python3 - <<'EOF' && echo done\n${PY_WRITE}\nEOF`).status, 2);
  assert.equal(run("bash <<'EOF'\ncp base/report.md docs/report.md\nEOF").status, 2);
  assert.equal(run("bash -lc 'cp base/report.md docs/report.md'").status, 2);
  assert.equal(run('[[ a > docs/report.md ]]').status, 0);
  assert.equal(run('sudo -n cp base/report.md docs/report.md').status, 2);
  assert.equal(run("python3 -u <<'EOF'\n" + PY_WRITE + '\nEOF').status, 2);
  // the second round's shapes
  assert.equal(run('[[ -n "$x" && "$y" > docs/report.md ]] && echo newer').status, 0, 'a comparison after && inside [[ ]]');
  assert.equal(run('echo "[[" > docs/report.md').status, 2, 'a quoted [[ is data');
  assert.equal(run(`python3 - <<< "${PY_WRITE}"`).status, 2, 'a here-string script');
  assert.equal(run('echo x | tee >(cat) docs/report.md').status, 2, 'an operand after a process substitution');
  assert.equal(run('mv docs/report.md{.new,}').status, 2, 'a brace list');
  assert.equal(run('cp base/*.md notes/').status, 2, 'a glob source into the tracked folder');
  assert.equal(run('cp base/report.md docs/report.{md,bak}').status, 0, 'three operands and no directory: cp writes nothing');
});
