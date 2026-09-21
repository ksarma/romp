// The shared browser-legs CI step, held to the tree. The gating vscode-extension job runs npm test before it installs a
// browser, so every browser leg skips at launch there; the step "Browser legs (node --test over ci-browser-legs.txt)"
// runs the legs named in vscode-extension/ci-browser-legs.txt after the job's Chromium install with
// ROMP_BROWSER_LEGS_REQUIRE=1, which makes a launch skip a failure (ui/webview/browser-legs-require.ts). This module
// holds, from the repo root and with no dependency installed (CI's shell job runs tools/*.test.mjs with no npm ci):
//   - the step exists once in that job, directly after the Chromium install step (by step NAMES), with the switch and
//     the run line, in the job's default working directory, and no step before the Test step installs or caches
//     Playwright (the property plans/markdown-viewer.md's CI sentence states and tools/markdown-viewer-plan-gate-adopt.test.mjs
//     pins, restated here so the two pins cannot disagree);
//   - completeness is derived, not asserted: the roster PLUS vscode-extension/ci-browser-legs-excluded.txt EQUALS the
//     tree's browser legs, no line is in both, no line is duplicated, every line names an existing source that is a
//     browser leg, every exclusions line carries a reason, and a reason that names Firefox or WebKit is true of the
//     source (and a source that launches one of them says so), so a leg added later takes a verdict: roster or exclusions,
//     never neither;
//   - the script the step calls (vscode-extension/scripts/ci-browser-legs.sh) derives the same census (`--list-legs`,
//     run here and compared), and, run on synthetic trees with a stub node on PATH, refuses a stale line, a leg in
//     neither file, a leg in both, a line without a reason, a duplicate, a line naming no leg and a missing bundle,
//     naming the line and the remedy, and prints "no legs in the roster" on an empty roster without starting node.
// THE CENSUS RULE (the script states the same one): a browser leg is a test module esbuild's test build bundles (a
// .test.ts directly in vscode-extension/src, ui or ui/webview; esbuild.js testBuild reads those three directories) that,
// on a line that is not a // comment, requires or imports the "playwright" package (`("playwright")` or `from
// "playwright"`), or imports ./real-viewer-leg and calls its inBrowser(, the shared launcher. Its roster name is the
// bundle esbuild writes: out-tests/<dir>/<name>.test.js (outbase is the repo root). Synthetic values only in the
// script's trees. Run: node --test tools/ci-browser-legs.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const EXT = path.join(REPO, 'vscode-extension');
const CI = path.join(REPO, '.github', 'workflows', 'ci.yml');
const ROSTER = 'ci-browser-legs.txt';
const EXCLUDED = 'ci-browser-legs-excluded.txt';
const SCRIPT = path.join(EXT, 'scripts', 'ci-browser-legs.sh');
const STEP = 'Browser legs (node --test over ci-browser-legs.txt)';
const INSTALL = 'Install the pinned Playwright Chromium';
const TEST_STEP = 'Test';
const JOB = 'vscode-extension';
const SWITCH = 'ROMP_BROWSER_LEGS_REQUIRE';
const RUN_LINE = 'bash scripts/ci-browser-legs.sh';
const LEG_DIRS = ['vscode-extension/src', 'ui', 'ui/webview'];
const read = (p) => fs.readFileSync(p, 'utf8');

// ── ci.yml by lines (no YAML library: the shell job installs nothing) ──────────────────────────────────

/** The jobs of the workflow: `^  <key>:` lines under `jobs:`, each with its lines up to the next job. */
function jobs(text) {
  const lines = text.split('\n');
  const start = lines.findIndex((l) => /^jobs:\s*$/.test(l));
  assert.ok(start >= 0, 'ci.yml has a jobs: section');
  const out = [];
  for (let i = start + 1; i < lines.length; i++) {
    const m = /^  ([A-Za-z0-9_-]+):\s*$/.exec(lines[i]);
    if (m) out.push({ key: m[1], lines: [] });
    else if (out.length) out[out.length - 1].lines.push(lines[i]);
  }
  return out;
}
/** A job's steps: each starts at a `^      - ` line; its name is its `name:` field (null for a bare `uses:` step); its
 *  fields are the `^        <field>:` lines (comments dropped from `code`); its env the `^          K: V` lines under env:. */
function steps(job) {
  const out = [];
  for (const l of job.lines) {
    if (/^      - /.test(l)) out.push({ name: null, lines: [] });
    if (out.length) out[out.length - 1].lines.push(l);
  }
  for (const s of out) {
    const named = s.lines.find((l) => /^      - name: |^        name: /.test(l));
    s.name = named ? named.replace(/^\s*(- )?name: /, '').trim() : null;
    s.code = s.lines.filter((l) => !/^\s*#/.test(l));
    s.comments = s.lines.filter((l) => /^\s*#/.test(l));
    s.fields = {};
    for (const l of s.code) {
      const f = /^        ([A-Za-z-]+):\s?(.*)$/.exec(l) || /^      - ([A-Za-z-]+): (.*)$/.exec(l);
      if (f) s.fields[f[1]] = f[2].trim();
    }
    s.env = {};
    const at = s.code.findIndex((l) => /^        env:\s*$/.test(l));
    if (at >= 0) for (let i = at + 1; i < s.code.length && /^          \S/.test(s.code[i]); i++) {
      const e = /^          ([A-Za-z_][A-Za-z0-9_]*): (.*)$/.exec(s.code[i]);
      if (e) s.env[e[1]] = e[2].trim();
    }
  }
  return out;
}
function extensionJob() {
  const hits = jobs(read(CI)).filter((j) => j.key === JOB);
  assert.equal(hits.length, 1, 'ci.yml has one ' + JOB + ' job');
  return hits[0];
}

test('the step exists once in the ' + JOB + ' job, directly after the Chromium install step, with the switch, the run line and the job\'s default working directory', () => {
  const job = extensionJob();
  const all = steps(job);
  const names = all.map((s) => s.name);
  assert.equal(names.filter((n) => n === STEP).length, 1, 'exactly one step named ' + JSON.stringify(STEP) + '; the job\'s steps: ' + JSON.stringify(names));
  assert.equal(names.filter((n) => n === INSTALL).length, 1, 'exactly one step named ' + JSON.stringify(INSTALL));
  const at = names.indexOf(STEP), install = names.indexOf(INSTALL), testAt = names.indexOf(TEST_STEP);
  assert.ok(testAt >= 0, 'the job has a step named ' + TEST_STEP);
  assert.equal(at, install + 1, 'the step is directly after the Chromium install step (the legs need the browser it installs, and nothing else in the job moves for it); order: ' + JSON.stringify(names));
  assert.ok(install > testAt, 'the Chromium install is after the Test step, so the legs still skip under npm test and run only here');
  const step = all[at];
  assert.deepEqual(step.env, { [SWITCH]: '"1"' }, 'the step\'s env is the switch alone, set to "1"');
  assert.equal(step.fields.run, RUN_LINE, 'the run line calls the script, which reads the roster into xargs node --test');
  assert.ok(!('working-directory' in step.fields), 'no working-directory override: the roster, the script and out-tests/ are under the job\'s default, vscode-extension/');
  assert.match(job.lines.join('\n'), /^    defaults:\n      run:\n        working-directory: vscode-extension$/m, 'the job\'s default working directory is vscode-extension');
  const comment = step.comments.join('\n');
  assert.ok(comment.includes('measured on the runner at the pushed head'), 'the step\'s comment carries the three numbers measured on the runner (or the placeholder the first run fills)');
  assert.ok(comment.includes(ROSTER) && comment.includes(EXCLUDED), 'the comment names both files');
  assert.ok(!step.lines.join('\n').includes(String.fromCharCode(0x2014)), 'no em dash');
});

test('no step before the Test step installs a Playwright browser or restores its cache (the CI_SKIP property the gate-adopt pin reads; the legs skip under npm test and run only in the step above)', () => {
  const all = steps(extensionJob());
  const testAt = all.findIndex((s) => s.name === TEST_STEP);
  assert.ok(testAt > 0, 'the Test step is not the first step');
  const before = all.slice(0, testAt).flatMap((s) => s.code).join('\n');
  assert.ok(!/^\s+run: npx playwright install\b/m.test(before), 'no Playwright install before the Test step');
  assert.ok(!/^\s+path: ~\/\.cache\/ms-playwright\s*$/m.test(before) && !/^\s+key: playwright-/m.test(before), 'no browser-cache restore before the Test step');
  const install = all.find((s) => s.name === INSTALL);
  assert.match(install.fields.run || '', /^npx playwright install chromium$/, 'the install step installs Chromium alone (the exclusions\' engine reasons rest on this)');
});

// ── the roster, the exclusions and the tree ───────────────────────────────────────────────────────────

const WELL_FORMED = /^out-tests\/\S+\.test\.js$/;
const sourceOf = (bundle) => path.join(REPO, bundle.replace(/^out-tests\//, '').replace(/\.test\.js$/, '.test.ts'));
const bundleOf = (dir, file) => 'out-tests/' + dir + '/' + file.replace(/\.test\.ts$/, '.test.js');
const code = (src) => src.split('\n').filter((l) => !/^\s*\/\//.test(l)).join('\n');
/** THE RULE: the module reaches a browser (see the header). */
function reachesBrowser(src) {
  const c = code(src);
  return /\(\s*"playwright"\s*\)|from\s+"playwright"/.test(c) || (c.includes('"./real-viewer-leg"') && c.includes('inBrowser('));
}
/** The engines other than Chromium a leg names outside comments: as the string "firefox"/"webkit" or as pw.firefox / pw.webkit. */
function otherEngines(src) {
  const c = code(src);
  const out = [];
  if (/"firefox"|\.firefox\./.test(c)) out.push('Firefox');
  if (/"webkit"|\.webkit\./.test(c)) out.push('WebKit');
  return out;
}
function census(root = REPO) {
  const out = [];
  for (const dir of LEG_DIRS) {
    const abs = path.join(root, dir);
    if (!fs.existsSync(abs)) continue;
    for (const f of fs.readdirSync(abs).filter((f) => f.endsWith('.test.ts')).sort()) {
      if (reachesBrowser(read(path.join(abs, f)))) out.push(bundleOf(dir, f));
    }
  }
  return out.sort();
}
/** Roster lines: [{ n, bundle }], comments and blanks dropped. */
function parseRoster(text) {
  return text.split('\n').map((line, i) => ({ n: i + 1, line })).filter(({ line }) => !/^\s*(#|$)/.test(line)).map(({ n, line }) => ({ n, bundle: line }));
}
/** Exclusions lines: [{ n, bundle, reason }] (reason null when the line has no tab). */
function parseExcluded(text) {
  return text.split('\n').map((line, i) => ({ n: i + 1, line })).filter(({ line }) => !/^\s*(#|$)/.test(line)).map(({ n, line }) => {
    const tab = line.indexOf('\t');
    return tab < 0 ? { n, bundle: line, reason: null } : { n, bundle: line.slice(0, tab), reason: line.slice(tab + 1) };
  });
}

test('the roster plus the exclusions equals the tree\'s browser legs, each line names an existing browser leg once, no line is in both, and every exclusions line carries a reason', () => {
  const roster = parseRoster(read(path.join(EXT, ROSTER)));
  const excluded = parseExcluded(read(path.join(EXT, EXCLUDED)));
  const legs = census();
  assert.ok(legs.length > 100, 'the tree holds browser legs (the census found ' + legs.length + '; a count near zero means the rule stopped matching, not that the legs left)');
  const where = (file, e) => file + ' line ' + e.n + ' (' + e.bundle + ')';
  for (const [file, entries] of [[ROSTER, roster], [EXCLUDED, excluded]]) {
    const seen = new Map();
    for (const e of entries) {
      assert.match(e.bundle, WELL_FORMED, where(file, e) + ': a line is a bundle path, out-tests/<dir>/<name>.test.js');
      assert.ok(!seen.has(e.bundle), where(file, e) + ' duplicates line ' + seen.get(e.bundle) + ': remove one');
      seen.set(e.bundle, e.n);
      const src = sourceOf(e.bundle);
      assert.ok(fs.existsSync(src), where(file, e) + ' names ' + path.relative(REPO, src) + ', which is not in the tree (the source moved or was deleted): fix the line');
      assert.ok(reachesBrowser(read(src)), where(file, e) + ' names no browser leg (' + path.relative(REPO, src) + ' reaches no browser by the census rule): remove the line');
    }
  }
  for (const e of excluded) {
    assert.ok(e.reason !== null && e.reason.trim() !== '', where(EXCLUDED, e) + ' has no reason: write the bundle path, a tab, and why the gating job does not run it');
    assert.ok(!e.reason.includes(String.fromCharCode(0x2014)), where(EXCLUDED, e) + ': no em dash');
  }
  const rostered = new Set(roster.map((e) => e.bundle));
  for (const e of excluded) assert.ok(!rostered.has(e.bundle), where(EXCLUDED, e) + ' is also in ' + ROSTER + ': a leg is in one file or the other, keep one');
  const listed = new Set([...rostered, ...excluded.map((e) => e.bundle)]);
  const neither = legs.filter((b) => !listed.has(b));
  assert.deepEqual(neither, [], 'browser legs in neither ' + ROSTER + ' nor ' + EXCLUDED + ' (add each to the roster, or to the exclusions with a tab and a reason): ' + JSON.stringify(neither));
  assert.deepEqual([...listed].sort(), legs, 'the roster plus the exclusions is exactly the tree\'s browser legs');
});

test('an exclusions reason that names Firefox or WebKit is true of the source, a source that launches one says so, and no rostered leg launches an engine the gating job does not install', () => {
  const excluded = parseExcluded(read(path.join(EXT, EXCLUDED)));
  for (const e of excluded) {
    const engines = otherEngines(read(sourceOf(e.bundle)));
    for (const eng of ['Firefox', 'WebKit']) {
      assert.equal(e.reason.includes(eng), engines.includes(eng), EXCLUDED + ' line ' + e.n + ' (' + e.bundle + '): the reason ' + (engines.includes(eng) ? 'names ' : 'does not name ') + eng + ' when the source ' + (engines.includes(eng) ? 'launches it' : 'does not name it outside a comment') + '; the reason reads: ' + e.reason);
    }
    if (engines.length) assert.ok(e.reason.includes('the gating job installs Chromium only'), EXCLUDED + ' line ' + e.n + ': an engine reason says why the gating job cannot run the leg');
  }
  for (const e of parseRoster(read(path.join(EXT, ROSTER)))) {
    const engines = otherEngines(read(sourceOf(e.bundle)));
    assert.deepEqual(engines, [], ROSTER + ' line ' + e.n + ' (' + e.bundle + ') names ' + engines.join(' and ') + ' outside a comment; the gating job installs Chromium only, so under the switch that launch is red: keep the leg in ' + EXCLUDED + ' with that reason');
  }
});

// ── the script ────────────────────────────────────────────────────────────────────────────────────────

function bash(args, opts = {}) {
  const r = spawnSync('bash', args, { encoding: 'utf8', ...opts });
  assert.equal(r.error, undefined, 'bash runs: ' + (r.error && r.error.message));
  return r;
}

test('the script\'s census (--list-legs) is the same set of legs this module derives', () => {
  assert.ok(fs.existsSync(SCRIPT), 'the step\'s script exists at ' + path.relative(REPO, SCRIPT));
  assert.ok(fs.statSync(SCRIPT).mode & 0o111, 'the script is executable');
  const r = bash([SCRIPT, '--list-legs']);
  assert.equal(r.status, 0, r.stderr);
  const listed = r.stdout.split('\n').filter(Boolean).sort();
  assert.deepEqual(listed, census(), 'the script and this test derive the same browser legs');
  const src = read(SCRIPT);
  assert.ok(src.includes('echo "no legs in the roster"; exit 0'), 'the empty-roster guard is spelled in the script (executed below)');
  assert.ok(/\| xargs -r node --test$/m.test(src), 'the roster is read into xargs node --test (executed below)');
});

/** A synthetic tree: the script under vscode-extension/scripts, two browser legs and one plain test module under ui/webview,
 *  a bundle for leg a only, and a stub node on PATH that records its arguments. Returns a runner over roster/exclusions text. */
function syntheticTree(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'cbl-'));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const ext = path.join(root, 'vscode-extension');
  for (const d of ['vscode-extension/scripts', 'vscode-extension/src', 'vscode-extension/out-tests/ui/webview', 'ui/webview', 'bin']) fs.mkdirSync(path.join(root, d), { recursive: true });
  fs.copyFileSync(SCRIPT, path.join(ext, 'scripts', 'ci-browser-legs.sh'));
  const leg = 'import { createRequire } from "node:module";\nconst pw = createRequire(__filename)("playwright");\n';
  fs.writeFileSync(path.join(root, 'ui', 'webview', 'a-browser.test.ts'), leg);
  fs.writeFileSync(path.join(root, 'ui', 'webview', 'b-browser.test.ts'), leg);
  fs.writeFileSync(path.join(root, 'ui', 'webview', 'plain.test.ts'), '// a comment that names requireCjs("playwright") is not a launch\nconst x = 1;\n');
  fs.writeFileSync(path.join(ext, 'out-tests', 'ui', 'webview', 'a-browser.test.js'), '');
  const log = path.join(root, 'node-args.txt');
  fs.writeFileSync(path.join(root, 'bin', 'node'), '#!/bin/sh\nprintf \'%s\\n\' "$@" > "' + log + '"\nexit 0\n', { mode: 0o755 });
  const A = 'out-tests/ui/webview/a-browser.test.js', B = 'out-tests/ui/webview/b-browser.test.js', PLAIN = 'out-tests/ui/webview/plain.test.js';
  const run = (roster, excluded) => {
    if (roster === null) fs.rmSync(path.join(ext, ROSTER), { force: true }); else fs.writeFileSync(path.join(ext, ROSTER), roster);
    if (excluded === null) fs.rmSync(path.join(ext, EXCLUDED), { force: true }); else fs.writeFileSync(path.join(ext, EXCLUDED), excluded);
    fs.rmSync(log, { force: true });
    const r = bash([path.join(ext, 'scripts', 'ci-browser-legs.sh')], { cwd: root, env: { ...process.env, PATH: path.join(root, 'bin') + path.delimiter + process.env.PATH } });
    return { status: r.status, out: r.stdout, err: r.stderr, node: fs.existsSync(log) ? fs.readFileSync(log, 'utf8').split('\n').filter(Boolean) : null };
  };
  return { run, A, B, PLAIN };
}

test('the script runs the rostered legs through node --test when the roster and the tree agree, and prints "no legs in the roster" and starts no node on an empty roster', (t) => {
  const { run, A, B } = syntheticTree(t);
  const ok = run('# header\n\n' + A + '\n', '# header\n' + B + '\ta reason\n');
  assert.equal(ok.status, 0, ok.err);
  assert.deepEqual(ok.node, ['--test', A], 'node --test received the roster\'s one bundle');
  assert.ok(!ok.out.includes('no legs in the roster'));
  const empty = run('# only a comment\n\n   \n', A + '\treason one\n' + B + '\treason two\n');
  assert.equal(empty.status, 0, empty.err);
  assert.ok(empty.out.includes('no legs in the roster'), 'the guard says so: ' + JSON.stringify(empty.out));
  assert.equal(empty.node, null, 'node was not started: with no file arguments node --test would run its default glob');
});

test('the script refuses, naming the line and the remedy, on: a missing file, a stale line, a leg in neither file, a leg in both, a line without a reason, a duplicate, a line naming no leg, a missing bundle, a malformed line', (t) => {
  const { run, A, B, PLAIN } = syntheticTree(t);
  const C = 'out-tests/ui/webview/c-browser.test.js';
  const refused = (r, ...needles) => {
    assert.equal(r.status, 1, 'exit 1; stderr: ' + r.err);
    for (const n of needles) assert.ok(r.err.includes(n), 'stderr names ' + JSON.stringify(n) + ':\n' + r.err);
    assert.equal(r.node, null, 'no leg ran');
    assert.ok(r.err.includes('no leg ran'));
  };
  const missing = run(null, B + '\treason\n');
  assert.equal(missing.status, 1); assert.ok(missing.err.includes(ROSTER) && missing.err.includes('restore it'), missing.err); assert.equal(missing.node, null);
  refused(run('# header\n' + A + '\n' + C + '\n', B + '\treason\n'), ROSTER + ' line 3: \'' + C + '\' names ui/webview/c-browser.test.ts, which is not in the tree (the source moved or was deleted): fix the roster line');
  refused(run(A + '\n', '# nothing excluded\n'), 'browser leg \'' + B + '\' is in neither ' + ROSTER + ' nor ' + EXCLUDED, 'add it to the roster', 'or to the exclusions with a tab and a reason');
  refused(run(A + '\n', A + '\treason\n' + B + '\treason\n'), EXCLUDED + ' line 1: \'' + A + '\' is also ' + ROSTER + ' line 1: a leg is in one file or the other, keep one');
  refused(run(A + '\n', B + '\n'), EXCLUDED + ' line 1: \'' + B + '\' has no reason: write the bundle path, a tab, and why the gating job does not run it');
  refused(run(A + '\n', B + '\t  \n'), EXCLUDED + ' line 1', 'has no reason');
  refused(run(A + '\n' + A + '\n', B + '\treason\n'), ROSTER + ' line 2: \'' + A + '\' duplicates line 1: remove one');
  refused(run(A + '\n', B + '\treason\n' + B + '\tagain\n'), EXCLUDED + ' line 2: \'' + B + '\' duplicates line 1: remove one');
  refused(run(A + '\n' + PLAIN + '\n', B + '\treason\n'), ROSTER + ' line 2: \'' + PLAIN + '\' names no browser leg (ui/webview/plain.test.ts reaches no browser): remove the line');
  refused(run(B + '\n', A + '\treason\n'), ROSTER + ' line 1: \'' + B + '\' is not under out-tests/ (the Test step\'s npm test builds it', 'build the bundles before this step');
  refused(run('ui/webview/a-browser.test.ts\n', A + '\treason\n' + B + '\treason\n'), ROSTER + ' line 1: \'ui/webview/a-browser.test.ts\' is not a bundle path (out-tests/<dir>/<name>.test.js): fix the roster line');
  const stale = run(A + '\n', B + '\treason\n' + C + '\treason\n');
  refused(stale, EXCLUDED + ' line 2: \'' + C + '\' names ui/webview/c-browser.test.ts, which is not in the tree (the source moved or was deleted): fix the line');
});
