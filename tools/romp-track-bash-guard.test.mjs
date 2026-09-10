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
import { spawn, spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

import { evaluate, extractWriteTargets, scriptWriteTargets, lex } from '../hooks/romp-track-bash-guard.mjs';

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

// ── refusals: the contract's cases ─────────────────────────────────

test('cp over a tracked file is refused, naming the file and track-edit; cat of it is allowed', () => {
  const reason = evaluate(payload('cp base/report.md docs/report.md'));
  assert.ok(reason, 'a cp onto a tracked file is refused');
  assert.ok(reason.includes(report), 'the refusal names the resolved file');
  assert.ok(reason.includes('track-edit'), 'the refusal names the remedy');
  assert.match(reason, /--file "[^"]+docs\/report\.md"/, 'the remedy is the track-edit command line on that file');
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
  assert.deepEqual(targets('cd "$D" && cp a report.md'), [], 'after a cd the lexer cannot read, a relative path is unresolvable and passes');
  assert.deepEqual(targets(`cd "$D" && cp a ${report}`), [report], 'an absolute one still resolves');
  const home = process.env.HOME;
  process.env.HOME = proj;
  try { assert.deepEqual(targets('cp base/report.md ~/docs/report.md', '/'), [report], '~/ is the home directory'); }
  finally { process.env.HOME = home; }
});

test('a command the lexer cannot see through is allowed: variables, eval, xargs, a shell -c it cannot read', () => {
  for (const cmd of [
    'cp "$SRC" "$DST"',
    'cp base/report.md "$OUT"',
    'cp base/report.md docs/$NAME.md',
    'eval "$CMD"',
    'ls docs/*.md | xargs -I{} cp base/{} {}',
    'bash -c "$SCRIPT"',
  ]) {
    assert.equal(evaluate(payload(cmd)), null, `allowed: ${cmd}`);
  }
  assert.ok(extractWriteTargets('eval "$CMD"', proj).opaque);
  assert.ok(!extractWriteTargets('cp a b', proj).opaque);
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
