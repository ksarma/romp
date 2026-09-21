// The shared browser-legs CI step, held to the tree. The gating vscode-extension job runs npm test before it installs a
// browser, so every browser leg skips at launch there; the step "Browser legs (node --test over ci-browser-legs.txt)"
// runs the legs named in vscode-extension/ci-browser-legs.txt after the job's Chromium install with
// ROMP_BROWSER_LEGS_REQUIRE=1: the one shared launcher, inBrowser in ui/webview/real-viewer-leg.ts, reads the switch (any
// non-empty value arms it) and under it a leg that cannot launch fails naming the switch and the reason instead of
// skipping. This module holds, from the repo root and with no dependency installed (CI's shell job runs tools/*.test.mjs
// with no npm ci):
//   - the step exists once in that job, directly after the Chromium install step (by step NAMES), with the switch and
//     the run line, in the job's default working directory, and no step before the Test step installs or caches
//     Playwright (the property plans/markdown-viewer.md's CI sentence states and tools/markdown-viewer-plan-gate-adopt.test.mjs
//     pins, restated here so the two pins cannot disagree);
//   - completeness is derived, not asserted: the roster PLUS vscode-extension/ci-browser-legs-excluded.txt EQUALS the
//     tree's browser legs, no line is in both, no line is duplicated, every line names an existing source that is a
//     browser leg, every exclusions line carries a reason, and a reason that names Firefox or WebKit is true of the
//     source (and a source that launches one of them says so), so a leg added later takes a verdict: roster or exclusions,
//     never neither;
//   - a rostered leg launches through the one shared launcher: its source imports ./real-viewer-leg and calls inBrowser(
//     by that name on a code line, and holds no .launch( and no .skip( of its own on a code line. Only inBrowser reads
//     the switch, so a launch or a skip of the leg's own stands outside it: a private skip stays a skip, and a private
//     launch that fails is never the failure naming the switch, which the step's red relies on. The check is textual (a
//     call under an import alias is not read as an inBrowser( call), so an aliased leg is refused until it calls
//     inBrowser( by that name. A rostered leg names no engine but Chromium: the gating job runs a rostered leg in
//     the Chromium it installs, and a leg's Firefox and WebKit runs live elsewhere (a served pytest step, a local run);
//   - the script the step calls (vscode-extension/scripts/ci-browser-legs.sh) derives the same census (`--list-legs`,
//     run here and compared), and, run on synthetic trees with a stub node on PATH, refuses a stale line, a leg in
//     neither file, a leg in both, a line without a reason, a duplicate, a line naming no leg, a missing bundle, a
//     malformed line (shown with its whitespace visible, the leg it names attributed to it), a leg that never calls
//     inBrowser, a leg with a launch or a skip of its own beside inBrowser, and a leg naming Firefox, naming the line and the
//     remedy; prints "no legs in the roster" on an empty roster without starting node; and after node --test turns a
//     skipped test into a red naming the test, the switch's state in the run (set to 1 as the step has it, or unset as
//     a local run may) and the rostered sources whose text holds its name with node's TAP escaping undone, turns a
//     rostered leg that registered no test into a red naming the leg (node's record reports such a file as one passing
//     test named by its path as node received it), prints the lost-browser remedy beside a leg whose failure names the switch, and passes
//     node's own failure status through;
//   - the phrase the script reads a lost browser by is the one inBrowser fails with in ui/webview/real-viewer-leg.ts, so
//     a reword on either side is red here rather than a remedy dropped in silence.
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
  // the three numbers are a property of the comment, not a spelling: a step duration in seconds, a job duration in minutes and the
  // 40-minute cap, all three measured on the runner (the first run's placeholder held none of them, and the pin that accepted it
  // by its spelling was the kind that lets a filled sentence go red for its wording)
  assert.ok(/measured on the runner/.test(comment), 'the step\'s comment says its numbers were measured on the runner');
  assert.ok(/\b\d+ s\b/.test(comment) && /\b\d+ min\b/.test(comment) && /40-minute cap/.test(comment),
    'the step\'s comment carries the three numbers: the step\'s seconds, the job\'s minutes and the 40-minute cap');
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
/** The gap between the module and the one shared launcher, or null when it launches through it: the module imports
 *  ./real-viewer-leg and calls inBrowser( by that name on a code line, and holds no .launch( and no .skip( of its own on
 *  a code line (inBrowser is the one launch that reads the switch; a private launch or skip stands outside it). The
 *  check is textual: a call under an import alias (inBrowser as <alias>) is not read as an inBrowser( call. The
 *  script's shared_launch_gap states the same rule. */
function launchesShared(src) {
  const c = code(src);
  if (!(c.includes('"./real-viewer-leg"') && c.includes('inBrowser('))) return 'no inBrowser( call beside an import of ./real-viewer-leg; a call under an import alias is not read as one';
  if (c.includes('.launch(')) return 'holds a launch of its own (.launch( on a code line)';
  if (c.includes('.skip(')) return 'holds a skip of its own (.skip( on a code line)';
  return null;
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
      assert.match(e.bundle, WELL_FORMED, file + ' line ' + e.n + ' (' + JSON.stringify(e.bundle) + '): a line is a bundle path, out-tests/<dir>/<name>.test.js (a trailing space, tab or carriage return counts; the quoting shows it)');
      assert.ok(!seen.has(e.bundle), where(file, e) + ' duplicates line ' + seen.get(e.bundle) + ': remove one');
      seen.set(e.bundle, e.n);
      const src = sourceOf(e.bundle);
      assert.ok(fs.existsSync(src), where(file, e) + ' names ' + path.relative(REPO, src) + ', which is not in the tree (the source moved or was deleted): fix the line');
      assert.ok(reachesBrowser(read(src)), where(file, e) + ' names no browser leg (' + path.relative(REPO, src) + ' reaches no browser by the census rule): remove the line');
    }
  }
  for (const e of roster) {
    const gap = launchesShared(read(sourceOf(e.bundle)));
    assert.equal(gap, null, where(ROSTER, e) + ' does not launch through the one shared launcher (' + gap + '): only inBrowser reads ' + SWITCH + ', so a launch or a skip of the leg\'s own stands outside the switch (a private skip stays a skip; a private launch that fails is never the failure naming the switch): launch through inBrowser (ui/webview/real-viewer-leg.ts), with no launch or skip of the leg\'s own, before rostering it');
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
    assert.deepEqual(engines, [], ROSTER + ' line ' + e.n + ' (' + e.bundle + ') names ' + engines.join(' and ') + ' outside a comment; the gating job installs Chromium only, so under the switch that launch is red: keep the leg in ' + EXCLUDED + ' with that reason (a leg\'s Firefox and WebKit runs live in a served pytest step or a local run, not in the roster)');
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
  assert.ok(/\| xargs -r node --test /m.test(src), 'the roster is read into xargs node --test (executed below)');
});

/** A synthetic tree: the script under vscode-extension/scripts; under ui/webview five browser legs and one plain test module:
 *  a and b launch through inBrowser (a has a bundle, b none; a's second test has a newline and a # in its name, spelled \n
 *  and # in the source as node's record escapes them), p launches through its own playwright copy with a bundle, m
 *  calls inBrowser but keeps a launch of its own beside it, k calls inBrowser but keeps a skip of its own before it, f
 *  launches through inBrowser but names Firefox, each with a bundle; and a stub node on PATH that records its arguments,
 *  writes CBL_STUB_TAP (when set) to the tap reporter's destination and exits CBL_STUB_EXIT (0 unless set). Returns a
 *  runner over roster/exclusions text that runs the script with the switch set to 1 as the step does (stub.switch names
 *  another value; null runs it unset, as a local run may); `node` in its result is the argument list without the
 *  reporter flags. `ext` is the physical path of the tree's vscode-extension, as node spells a bundle in its record. */
function syntheticTree(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'cbl-'));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const ext = path.join(root, 'vscode-extension');
  for (const d of ['vscode-extension/scripts', 'vscode-extension/src', 'vscode-extension/out-tests/ui/webview', 'ui/webview', 'bin']) fs.mkdirSync(path.join(root, d), { recursive: true });
  fs.copyFileSync(SCRIPT, path.join(ext, 'scripts', 'ci-browser-legs.sh'));
  const priv = 'import { createRequire } from "node:module";\nconst pw = createRequire(__filename)("playwright");\n';
  const shared = 'import { inBrowser } from "./real-viewer-leg";\n';
  const web = (name, text) => fs.writeFileSync(path.join(root, 'ui', 'webview', name), text);
  web('a-browser.test.ts', shared + 'test("leg a opens the page", async (t) => { await inBrowser(t, async (browser) => {}); });\n'
    + 'test("leg a keeps the slice\\nwhole # 2", async (t) => { await inBrowser(t, async (browser) => {}); });\n');
  web('b-browser.test.ts', shared + 'test("leg b opens the page", async (t) => { await inBrowser(t, async (browser) => {}); });\n');
  web('p-browser.test.ts', priv + 'test("leg p opens the page", async (t) => { let browser; try { browser = await pw.chromium.launch(); } catch (e) { t.skip("no browser"); return; } });\n');
  web('m-browser.test.ts', priv + shared + 'test("leg m opens the page", async (t) => { await inBrowser(t, async (browser) => {}); const own = await pw.chromium.launch(); });\n');
  web('k-browser.test.ts', shared + 'test("leg k opens the page", async (t) => { if (!process.env.SYNTHETIC_FIXTURE) { t.skip("no fixture"); return; } await inBrowser(t, async (browser) => {}); });\n');
  web('f-browser.test.ts', shared + 'test("leg f opens the page", async (t) => { await inBrowser(t, async (browser) => { if (browser.browserType().name() !== "firefox") return; }); });\n');
  web('plain.test.ts', '// a comment that names requireCjs("playwright") is not a launch\nconst x = 1;\n');
  for (const b of ['a-browser', 'p-browser', 'm-browser', 'k-browser', 'f-browser']) fs.writeFileSync(path.join(ext, 'out-tests', 'ui', 'webview', b + '.test.js'), '');
  const log = path.join(root, 'node-args.txt');
  fs.writeFileSync(path.join(root, 'bin', 'node'), [
    '#!/bin/sh',
    'printf \'%s\\n\' "$@" > "' + log + '"',
    'prev=""',
    'for a in "$@"; do',
    '  case "$a" in --test-reporter-destination=*) if [ "$prev" = "--test-reporter=tap" ] && [ -n "${CBL_STUB_TAP:-}" ]; then printf \'%s\\n\' "$CBL_STUB_TAP" > "${a#--test-reporter-destination=}"; fi;; esac',
    '  prev="$a"',
    'done',
    'exit "${CBL_STUB_EXIT:-0}"',
    '',
  ].join('\n'), { mode: 0o755 });
  const A = 'out-tests/ui/webview/a-browser.test.js', B = 'out-tests/ui/webview/b-browser.test.js', P = 'out-tests/ui/webview/p-browser.test.js', M = 'out-tests/ui/webview/m-browser.test.js', K = 'out-tests/ui/webview/k-browser.test.js', F = 'out-tests/ui/webview/f-browser.test.js', PLAIN = 'out-tests/ui/webview/plain.test.js';
  const run = (roster, excluded, stub = {}) => {
    if (roster === null) fs.rmSync(path.join(ext, ROSTER), { force: true }); else fs.writeFileSync(path.join(ext, ROSTER), roster);
    if (excluded === null) fs.rmSync(path.join(ext, EXCLUDED), { force: true }); else fs.writeFileSync(path.join(ext, EXCLUDED), excluded);
    fs.rmSync(log, { force: true });
    const env = { ...process.env, PATH: path.join(root, 'bin') + path.delimiter + process.env.PATH };
    delete env.CBL_STUB_TAP; delete env.CBL_STUB_EXIT;
    env[SWITCH] = '1';
    if (stub.switch === null) delete env[SWITCH]; else if (stub.switch !== undefined) env[SWITCH] = stub.switch;
    if (stub.tap !== undefined) env.CBL_STUB_TAP = stub.tap;
    if (stub.exit !== undefined) env.CBL_STUB_EXIT = String(stub.exit);
    const r = bash([path.join(ext, 'scripts', 'ci-browser-legs.sh')], { cwd: root, env });
    const args = fs.existsSync(log) ? fs.readFileSync(log, 'utf8').split('\n').filter(Boolean) : null;
    return { status: r.status, out: r.stdout, err: r.stderr, node: args && args.filter((a) => !a.startsWith('--test-reporter')), reporters: args && args.filter((a) => a.startsWith('--test-reporter')) };
  };
  return { run, root, ext: fs.realpathSync(ext), A, B, P, M, K, F, PLAIN };
}

const EXCLUDE_REST = (...keep) => ['a', 'b', 'p', 'm', 'k', 'f'].filter((n) => !keep.includes(n)).map((n) => 'out-tests/ui/webview/' + n + '-browser.test.js\treason ' + n + '\n').join('');

test('the script runs the rostered legs through node --test when the roster and the tree agree, and prints "no legs in the roster" and starts no node on an empty roster', (t) => {
  const { run, A } = syntheticTree(t);
  const ok = run('# header\n\n' + A + '\n', '# header\n' + EXCLUDE_REST('a'));
  assert.equal(ok.status, 0, ok.err);
  assert.deepEqual(ok.node, ['--test', A], 'node --test received the roster\'s one bundle');
  assert.deepEqual(ok.reporters.filter((a) => !a.startsWith('--test-reporter-destination=')), ['--test-reporter=spec', '--test-reporter=tap'], 'the spec reporter for the log and the tap reporter for the skip check');
  assert.ok(!ok.out.includes('no legs in the roster'));
  const empty = run('# only a comment\n\n   \n', EXCLUDE_REST());
  assert.equal(empty.status, 0, empty.err);
  assert.ok(empty.out.includes('no legs in the roster'), 'the guard says so: ' + JSON.stringify(empty.out));
  assert.equal(empty.node, null, 'node was not started: with no file arguments node --test would run its default glob');
});

test('the script refuses, naming the line and the remedy, on: a missing file, a stale line, a leg in neither file, a leg in both, a line without a reason, a duplicate, a line naming no leg, a missing bundle, a malformed line, a leg that never calls inBrowser, a leg with a launch of its own beside inBrowser, a leg with a skip of its own beside inBrowser, a leg naming Firefox', (t) => {
  const { run, A, B, P, M, K, F, PLAIN } = syntheticTree(t);
  const C = 'out-tests/ui/webview/c-browser.test.js';
  const refused = (r, ...needles) => {
    assert.equal(r.status, 1, 'exit 1; stderr: ' + r.err);
    for (const n of needles) assert.ok(r.err.includes(n), 'stderr names ' + JSON.stringify(n) + ':\n' + r.err);
    assert.equal(r.node, null, 'no leg ran');
    assert.ok(r.err.includes('no leg ran'));
  };
  const rest = EXCLUDE_REST('a', 'b');
  const missing = run(null, B + '\treason\n' + rest);
  assert.equal(missing.status, 1); assert.ok(missing.err.includes(ROSTER) && missing.err.includes('restore it'), missing.err); assert.equal(missing.node, null);
  refused(run('# header\n' + A + '\n' + C + '\n', B + '\treason\n' + rest), ROSTER + ' line 3: \'' + C + '\' names ui/webview/c-browser.test.ts, which is not in the tree (the source moved or was deleted): fix the roster line');
  refused(run(A + '\n', '# nothing excluded but the rest\n' + rest), 'browser leg \'' + B + '\' is in neither ' + ROSTER + ' nor ' + EXCLUDED, 'add it to the roster', 'or to the exclusions with a tab and a reason');
  refused(run(A + '\n', A + '\treason\n' + B + '\treason\n' + rest), EXCLUDED + ' line 1: \'' + A + '\' is also ' + ROSTER + ' line 1: a leg is in one file or the other, keep one');
  refused(run(A + '\n', B + '\n' + rest), EXCLUDED + ' line 1: \'' + B + '\' has no reason: write the bundle path, a tab, and why the gating job does not run it');
  refused(run(A + '\n', B + '\t  \n' + rest), EXCLUDED + ' line 1', 'has no reason');
  refused(run(A + '\n' + A + '\n', B + '\treason\n' + rest), ROSTER + ' line 2: \'' + A + '\' duplicates line 1: remove one');
  refused(run(A + '\n', B + '\treason\n' + B + '\tagain\n' + rest), EXCLUDED + ' line 2: \'' + B + '\' duplicates line 1: remove one');
  refused(run(A + '\n' + PLAIN + '\n', B + '\treason\n' + rest), ROSTER + ' line 2: \'' + PLAIN + '\' names no browser leg (ui/webview/plain.test.ts reaches no browser): remove the line');
  refused(run(B + '\n', A + '\treason\n' + rest), ROSTER + ' line 1: \'' + B + '\' is not under out-tests/ (the Test step\'s npm test builds it', 'build the bundles before this step');
  refused(run('ui/webview/a-browser.test.ts\n', A + '\treason\n' + B + '\treason\n' + rest), ROSTER + ' line 1: ui/webview/a-browser.test.ts is not a bundle path (out-tests/<dir>/<name>.test.js; a trailing space, tab or carriage return counts', 'fix the line');
  // a carriage return at the end of the line: the line is shown as bash's %q spells it, so the invisible cause is visible,
  // and the leg it names is attributed to that line, not called missing from both files
  const crlf = run(A + '\r\n', B + '\treason\n' + rest);
  refused(crlf, ROSTER + ' line 1: $\'' + A + '\\r\' is not a bundle path', 'browser leg \'' + A + '\' is named by a malformed line (' + ROSTER + ' line 1, above): fix that line');
  assert.ok(!crlf.err.includes('is in neither'), 'the leg the malformed line names is not reported as missing from both files:\n' + crlf.err);
  refused(run(A + '\n', B + '\treason\n' + P + '  \treason\n' + EXCLUDE_REST('a', 'b', 'p')), EXCLUDED + ' line 2: ' + P + '\\ \\  is not a bundle path', 'browser leg \'' + P + '\' is named by a malformed line (' + EXCLUDED + ' line 2, above): fix that line');
  // a leg with a launch and a skip of its own never calls inBrowser, the one launch that reads the switch: rostered, its
  // skip would stay a skip under the step and leave it green
  refused(run(A + '\n' + P + '\n', B + '\treason\n' + EXCLUDE_REST('a', 'b', 'p')), ROSTER + ' line 2: \'' + P + '\' does not launch through the one shared launcher (no inBrowser( call beside an import of ./real-viewer-leg; a call under an import alias is not read as one): only inBrowser reads ' + SWITCH + ', so a launch or a skip of the leg\'s own stands outside the switch (a private skip stays a skip; a private launch that fails is never the failure naming the switch): launch through inBrowser (ui/webview/real-viewer-leg.ts), with no launch or skip of the leg\'s own, before rostering it');
  // a leg that calls inBrowser but keeps a launch of its own beside it: the private launch stands outside the switch
  refused(run(A + '\n' + M + '\n', B + '\treason\n' + EXCLUDE_REST('a', 'b', 'm')), ROSTER + ' line 2: \'' + M + '\' does not launch through the one shared launcher (holds a launch of its own (.launch( on a code line)): only inBrowser reads');
  // a leg that calls inBrowser but skips on its own first: under the step that skip stays a skip
  refused(run(A + '\n' + K + '\n', B + '\treason\n' + EXCLUDE_REST('a', 'b', 'k')), ROSTER + ' line 2: \'' + K + '\' does not launch through the one shared launcher (holds a skip of its own (.skip( on a code line)): only inBrowser reads');
  // a leg that launches through inBrowser but names Firefox: the gating job installs Chromium only
  refused(run(A + '\n' + F + '\n', B + '\treason\n' + EXCLUDE_REST('a', 'b', 'f')), ROSTER + ' line 2: \'' + F + '\' names Firefox outside a comment; the gating job installs Chromium only, so under the switch that launch is red: keep the leg in ' + EXCLUDED + ' with that reason');
  const stale = run(A + '\n', B + '\treason\n' + C + '\treason\n' + rest);
  refused(stale, EXCLUDED + ' line 2: \'' + C + '\' names ui/webview/c-browser.test.ts, which is not in the tree (the source moved or was deleted): fix the line');
});

test('after node --test the script turns a skipped test into a red naming the test, the rostered sources holding its name (node\'s TAP escaping undone) and the remedy, turns a rostered leg that registered no test into a red naming the leg, prints the lost-browser remedy beside a leg whose failure names the switch, and passes node\'s own failure status through', (t) => {
  const { run, ext, A } = syntheticTree(t);
  const excluded = EXCLUDE_REST('a');
  const HOLDERS = 'rostered sources whose text holds that test name, node\'s TAP escaping undone: ';
  const tapSkip = 'TAP version 13\n# Subtest: leg a opens the page\nok 1 - leg a opens the page # SKIP no playwright chromium on this box\n# Subtest: some other test\nok 2 - some other test\n1..2\n# tests 2\n# pass 1\n# skipped 1\n';
  const skipped = run(A + '\n', excluded, { tap: tapSkip });
  assert.equal(skipped.status, 1, 'a skip under the switch is red; stderr: ' + skipped.err);
  assert.deepEqual(skipped.node, ['--test', A], 'the leg ran (the skip is read from the run, not refused before it)');
  assert.ok(skipped.err.includes('skipped with ' + SWITCH + '=1: ok 1 - leg a opens the page # SKIP no playwright chromium on this box (' + HOLDERS + A + ')'), skipped.err);
  assert.ok(skipped.err.includes('a rostered leg skipped a test with ' + SWITCH + '=1, so the step claims coverage it did not run'), skipped.err);
  assert.ok(skipped.err.includes('only inBrowser in ui/webview/real-viewer-leg.ts turns a launch it cannot make into a failure here') && skipped.err.includes('move it to ' + EXCLUDED + ' with that reason'), skipped.err);
  // the same skip with the switch unset, as a local run may have it: still red, and the message says the switch is unset
  // and that the step sets it, instead of claiming a state the run did not have
  const unset = run(A + '\n', excluded, { tap: tapSkip, switch: null });
  assert.equal(unset.status, 1, 'a skip with the switch unset is red too; stderr: ' + unset.err);
  assert.ok(unset.err.includes('skipped with ' + SWITCH + ' unset: ok 1 - leg a opens the page # SKIP'), unset.err);
  assert.ok(unset.err.includes('a rostered leg skipped a test with ' + SWITCH + ' unset, so this run claims coverage it did not run: the step sets ' + SWITCH + '=1'), unset.err);
  assert.ok(!unset.err.includes(SWITCH + '=1:') && !unset.err.includes('with ' + SWITCH + '=1,'), 'no line claims the switch was set:\n' + unset.err);
  const unknown = run(A + '\n', excluded, { tap: 'TAP version 13\nok 1 - a name no source spells # SKIP why\n1..1\n' });
  assert.equal(unknown.status, 1);
  assert.ok(unknown.err.includes('(' + HOLDERS + 'none)'), 'a name found in no rostered source says so:\n' + unknown.err);
  // node's record doubles a backslash and writes # as \#, so a's second test (a newline and a # in its name, spelled \n
  // and # in the source) is recorded as "slice\\nwhole \# 2"; the lookup undoes that and finds the source
  const escaped = run(A + '\n', excluded, { tap: 'TAP version 13\nok 1 - leg a keeps the slice\\\\nwhole \\# 2 # SKIP why\n1..1\n' });
  assert.equal(escaped.status, 1);
  assert.ok(escaped.err.includes('skipped with ' + SWITCH + '=1: ok 1 - leg a keeps the slice\\\\nwhole \\# 2 # SKIP why (' + HOLDERS + A + ')'), 'the name is looked up with the record\'s escaping undone:\n' + escaped.err);
  const clean = run(A + '\n', excluded, { tap: 'TAP version 13\nok 1 - leg a opens the page\n1..1\n# tests 1\n# pass 1\n# skipped 0\n' });
  assert.equal(clean.status, 0, 'no skip, no red: ' + clean.err);
  assert.equal(clean.err, '', 'nothing on stderr when every rostered test ran');
  // a rostered leg that registered no test: node's record reports the file as one passing test named by the bundle's
  // path as node received it (the roster line, relative to vscode-extension), with no nested line, and its summary counts
  // it as a pass
  const none = run(A + '\n', excluded, { tap: 'TAP version 13\n# Subtest: ' + A + '\nok 1 - ' + A + '\n1..1\n# tests 1\n# pass 1\n# skipped 0\n' });
  assert.equal(none.status, 1, 'a leg with no test is red; stderr: ' + none.err);
  assert.deepEqual(none.node, ['--test', A], 'the leg ran (the empty run is read from the record, not refused before it)');
  assert.ok(none.err.includes('ci-browser-legs: ' + A + ' registered no test in this run (node\'s record reports the file as one passing test named by its path), so the step claims coverage it did not run'), none.err);
  assert.ok(none.err.includes('move it to ' + EXCLUDED + ' with that reason until one runs'), none.err);
  assert.ok(!none.err.includes('skipped with'), 'an empty run is not called a skip:\n' + none.err);
  // xargs answers a command's exit of 1 to 125 with 123, so that is the status a failed leg gives the step
  const failed = run(A + '\n', excluded, { tap: 'TAP version 13\nnot ok 1 - leg a opens the page\n  ---\n  location: \'' + path.join(ext, A) + ':3:1\'\n  error: \'an assertion of the leg\\\'s own failed\'\n  ...\n1..1\n# fail 1\n', exit: 1 });
  assert.equal(failed.status, 123, 'node\'s failure is the step\'s (through xargs, which answers 123)');
  assert.ok(!failed.err.includes('skipped under'), 'a failure is not called a skip:\n' + failed.err);
  assert.ok(!failed.err.includes('lost its browser'), 'a failure for a reason of the leg\'s own is not called a lost browser:\n' + failed.err);
  assert.ok(!failed.err.includes('registered no test'), 'a failed test is a registered test:\n' + failed.err);
  // a failure whose error names the switch is inBrowser failing to launch under it: the remedy is printed beside the leg,
  // named from the record's location line
  const LOST = SWITCH + ' is set and this leg cannot run: no playwright browser on this box; the browser leg needs one: browserType.launch: Executable doesn\'t exist at /nowhere';
  const lostTap = 'TAP version 13\n# Subtest: leg a opens the page\nnot ok 1 - leg a opens the page\n  ---\n  duration_ms: 1\n  type: \'test\'\n  location: \'' + path.join(ext, A) + ':3:1\'\n  failureType: \'testCodeFailure\'\n  error: "' + LOST + '"\n  code: \'ERR_ASSERTION\'\n  ...\n1..1\n# fail 1\n';
  const lost = run(A + '\n', excluded, { tap: lostTap, exit: 1 });
  assert.equal(lost.status, 123);
  assert.ok(lost.err.includes('ci-browser-legs: ' + A + ': \'leg a opens the page\' failed under ' + SWITCH + '=1 because inBrowser could not launch ("' + LOST + '"): the runner lost its browser: check the Chromium install step'), lost.err);
  const both = run(A + '\n', excluded, { tap: 'TAP version 13\nok 1 - leg a opens the page # SKIP why\n1..1\n', exit: 7 });
  assert.equal(both.status, 123, 'with a failure and a skip node\'s status stands and the skip is still named');
  assert.ok(both.err.includes('skipped with ' + SWITCH + '=1'), both.err);
});

test('the phrase the script reads a lost browser by is the one inBrowser fails with in ui/webview/real-viewer-leg.ts, so a reword on either side is red here rather than a remedy dropped in silence', () => {
  const script = read(SCRIPT);
  assert.match(script, /^SWITCH=ROMP_BROWSER_LEGS_REQUIRE$/m, 'the script names the switch once, as SWITCH');
  const m = /awk -v msg="([^"]+)"/.exec(script);
  assert.ok(m, 'the script hands awk the phrase it reads a failure block by (awk -v msg="...")');
  const phrase = m[1].replace(/\$SWITCH\b/g, SWITCH);
  assert.ok(phrase.startsWith(SWITCH + ' is set'), 'the phrase names the switch: ' + phrase);
  const helper = read(path.join(REPO, 'ui', 'webview', 'real-viewer-leg.ts'));
  assert.ok(helper.includes('assert.fail("' + phrase + ': "'), 'ui/webview/real-viewer-leg.ts (inBrowser) fails with ' + JSON.stringify(phrase + ': <why>') + ', the phrase vscode-extension/scripts/ci-browser-legs.sh reads a lost browser by; a reword in one file moves the other, or the lost-browser remedy is never printed');
});
