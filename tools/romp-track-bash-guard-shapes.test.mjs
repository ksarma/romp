// The Bash-side track guard (hooks/romp-track-bash-guard.mjs; plans/file-review.md, decision 47): the
// shell shapes its review (2026-09-10) found misread, each pinned here in both directions where the
// shape has two (a write the guard missed, and an ordinary command it refused for a file the command
// never touches). A subshell's cd ends at its `)`; a heredoc body belongs to the command that opened
// it, so `python3 - <<EOF && echo done` is read; a shell fed its script by heredoc is read like `sh -c`;
// `bash -lc` is `bash -l -c`; `python3 -u <<EOF` still reads stdin; `sudo -u USER cp` is a cp; `[[ a > b ]]`
// compares; `Path('x').open('w')` and `open(mode='w', file='x')` are writes. The verdict builds the
// project's link closure once per call, not once per landing file, so a directory copy costs one
// walk. And the branches no other test reached (the prefixes, pushd and popd, node -p and --print,
// the NUL-byte rule, the directory walk cap) are pinned so removing one fails by name. Synthetic: a
// project under os.tmpdir(), invented paths, no session data.
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

// ── the tracked binary under a text name, and the walk cap ─────────

test('a tracked file that is binary under a text-looking name passes: the NUL-byte rule', () => {
  const blob = path.join(proj, 'notes', 'blob.md');
  fs.writeFileSync(blob, Buffer.from([0x89, 0x50, 0x4e, 0x47, 0, 0, 0, 0x0d]));
  assert.equal(evaluate(payload('cp base/report.md notes/blob.md')), null, 'a binary cannot take a tracked edit');
  fs.writeFileSync(blob, 'text after all\n');
  assert.ok(evaluate(payload('cp base/report.md notes/blob.md')), 'the same name as text is refused');
});

test('a directory source is walked to 500 files and no further', () => {
  const big = path.join(proj, 'big');
  fs.mkdirSync(big);
  for (let k = 0; k < 600; k++) fs.writeFileSync(path.join(big, `f${String(k).padStart(3, '0')}.txt`), 'x');
  const { targets: t } = extractWriteTargets('cp -r big docs/new', proj);
  assert.equal(t.length, 500, 'the cap');
  assert.ok(t.every((x) => x.path.startsWith(path.join(proj, 'docs', 'new') + path.sep)));
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
});
