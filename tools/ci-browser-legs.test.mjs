// The shared browser-legs CI step, held to the tree from CI's Shell job, which runs tools/*.test.mjs with no npm ci. The
// gating vscode-extension job runs npm test before it installs a browser, so every browser leg skips at launch there; the
// step "Browser legs (node --test over ci-browser-legs.txt)" runs the legs named in vscode-extension/ci-browser-legs.txt
// after the job's Chromium install with ROMP_BROWSER_LEGS_REQUIRE=1: the one shared launcher, inBrowser in
// ui/webview/real-viewer-leg.ts, reads the switch (any non-empty value arms it) and under it a leg that cannot launch fails
// naming the switch and the reason instead of skipping.
// WHAT THIS MODULE DOES NOT HOLD. The roster rule (a rostered leg launches through inBrowser alone, with no playwright load,
// launch, skip or todo of its own, in Chromium) is the PR reviewer's to check: nothing in the tree reads a leg's source for
// it, so the step reads a rostered leg green in the four cases the rule's homes name (the test of those homes below). Nor
// does anything here check that every browser leg in the tree is rostered. A green here is:
//   - the step exists once in that job, directly after the Chromium install step (by step NAMES), with the switch and
//     the run line, in the job's default working directory, and no step before the Test step installs or caches
//     Playwright (the property plans/markdown-viewer.md's CI sentence states and tools/markdown-viewer-plan-gate-adopt.test.mjs
//     pins, restated here so the two pins cannot disagree); every file path the step's comment names is in the tree;
//   - the step carries a timeout-minutes of its own that fits the margin under the job's cap at the measured head (the job's
//     comment derives it and names the same number), and the script passes node a --test-timeout above the largest own
//     { timeout } a rostered leg passes and under the step's bound, so a hung leg fails by name before the step is cut;
//   - the roster is well formed: every line is a bundle path (out-tests/<dir>/<name>.test.js), no line is duplicated, and
//     every line names a source that exists in the tree;
//   - each home of the roster rule (the roster header, the step's comment, the script's header and CONTRIBUTING.md) states
//     it as the PR reviewer's, names the four cases the step reads green and their witness here, and says that nothing
//     checks that every browser leg in the tree is rostered (a text pin: it holds what the homes say); the witness is
//     executed: the script with the real node and the real reporter reads green one synthetic rostered leg of each case
//     (an own launch whose failure is swallowed, a module that launches nothing, a child process whose failure is
//     tolerated, a todo that passes beside a real pass), each failure marked as it happens;
//   - vscode-extension/.vscodeignore names the CI-only files (the roster, the script and its reporter);
//   - the script the step calls (vscode-extension/scripts/ci-browser-legs.sh) exists, is executable and runs node --test
//     over the roster array (no xargs, so node's status is the step's on every platform) with the reporter
//     scripts/ci-browser-legs-reporter.mjs beside the spec reporter; run on synthetic trees with a stub node on PATH that
//     records the node --test call and writes the record a case hands it, it refuses a missing roster file, a stale line, a
//     duplicate, a missing bundle and a malformed line (six shapes, each shown with its whitespace visible), each red naming
//     the line and the remedy; runs the pre-run checks alone under --check; prints "no legs in the roster" and starts no
//     node on an empty roster; and after node --test reads the reporter's record and derives, per rostered leg, that at
//     least one result attributed to it is a pass with no skip or todo, a test and not a suite, and not node's file-level
//     result, red naming the leg otherwise (todo-only, a describe() that registers none, a file that registered nothing, a
//     failure inside a todo); turns a skipped test into a red naming the test, its reason and the switch's state in the run
//     (set to 1 as the step has it, or unset as a local run may); reds a failure inside a todo and a file that failed as a
//     whole (timed out, or threw at load) by name; prints the lost-browser remedy beside a leg whose failure names the
//     switch; and passes node's own failure status through. The two remedies that move a leg off the step, after an unrun
//     leg and after a skip under the switch, take its line out of the roster, each read from the script's stderr. The
//     reporter itself is executed here over synthetic bundles with a real node --test (the shapes above, a bundle that throws
//     at load, and a name holding a tab and a newline), and so is the composition: the script with the real node and the
//     real reporter over those shapes as rostered legs;
//   - the phrase the script reads a lost browser by is a literal in ui/webview/real-viewer-leg.ts's source, the SHARED
//     PHRASE between the helper and the script, so a reword on either side is red here rather than a remedy dropped in
//     silence. That pin reads text and guards the phrase alone: that inBrowser FAILS with it under the switch and skips
//     without is executed by ui/webview/real-viewer-leg-switch.test.ts (a child node --test with PLAYWRIGHT_BROWSERS_PATH
//     emptied), which the vscode-extension job runs under npm test and, rostered, in the step itself.
// Synthetic values only in the script's trees. Run: node --test tools/ci-browser-legs.test.mjs
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
const SCRIPT = path.join(EXT, 'scripts', 'ci-browser-legs.sh');
const REPORTER = path.join(EXT, 'scripts', 'ci-browser-legs-reporter.mjs');
const STEP = 'Browser legs (node --test over ci-browser-legs.txt)';
const INSTALL = 'Install the pinned Playwright Chromium';
const TEST_STEP = 'Test';
const JOB = 'vscode-extension';
const SWITCH = 'ROMP_BROWSER_LEGS_REQUIRE';
const RUN_LINE = 'bash scripts/ci-browser-legs.sh';
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
/** The job's cap in minutes, read from its one plain timeout-minutes line (asserted, not skipped: a matrix expression here
 *  needs the pins that derive from the cap re-anchored). */
function jobCap(job) {
  const capLine = job.lines.find((l) => /^    timeout-minutes: \d+$/.test(l));
  assert.ok(capLine, 'the ' + JOB + ' job has one plain timeout-minutes line (a matrix expression here needs this pin re-anchored, not skipped)');
  return { cap: Number(/(\d+)$/.exec(capLine)[1]), capLine };
}

test('the step exists once in the ' + JOB + ' job, directly after the Chromium install step, with the switch, the run line and the job\'s default working directory, and every file path its comment names is in the tree', () => {
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
  assert.equal(step.fields.run, RUN_LINE, 'the run line calls the script, which runs node --test over the roster');
  assert.ok(!('working-directory' in step.fields), 'no working-directory override: the roster, the script and out-tests/ are under the job\'s default, vscode-extension/');
  assert.match(job.lines.join('\n'), /^    defaults:\n      run:\n        working-directory: vscode-extension$/m, 'the job\'s default working directory is vscode-extension');
  const comment = step.comments.join('\n');
  // the three numbers are a property of the comment, not a spelling: a step duration in seconds, a job duration in minutes and the
  // job's cap, read from the job's own timeout-minutes line so a raised cap turns a stale sentence red (a lowered one is already
  // red in tests/test_ci_bats_bound.py::ExtensionJobCeiling, which floors the cap at 40; this pin is about the SENTENCE matching
  // the line, not about the cap's value); all three measured on the runner (the first run's placeholder held none of them, and
  // the pin that accepted it by its spelling was the kind that lets a filled sentence go red for its wording)
  const { cap } = jobCap(job);
  assert.ok(/measured on the runner/.test(comment), 'the step\'s comment says its numbers were measured on the runner');
  assert.ok(/\b\d+ s\b/.test(comment), 'the step\'s comment carries the step\'s seconds');
  const minutes = /\b(\d+) min\b/.exec(comment);
  assert.ok(minutes, 'the step\'s comment carries the job\'s minutes');
  assert.ok(new RegExp('\\b' + cap + '-minute cap\\b').test(comment), 'the comment names the job\'s cap as ci.yml sets it (' + cap + ' minutes): a cap change rewrites the sentence; this pin holds the sentence to the line, whatever the cap, while a LOWERED cap is tests/test_ci_bats_bound.py::ExtensionJobCeiling\'s red (it floors the cap at 40): two guards, two properties');
  assert.ok(Number(minutes[1]) < cap, 'the stated job minutes (' + minutes[1] + ') sit under the cap (' + cap + ')');
  assert.ok(comment.includes(ROSTER), 'the comment names the roster');
  // every file path the comment names is in the tree, resolved from the repository root or from vscode-extension/ (the job's
  // default working directory, which the comment's scripts/ paths are relative to), so a comment that points a reader at a
  // file the tree no longer holds is red here (holds the property over the paths the comment spells with a file suffix)
  const named = [...comment.replace(/\n\s*#\s?/g, ' ').matchAll(/(?<![\w.\/<>-])(?:[A-Za-z][\w.-]*\/)*[A-Za-z][\w-]*(?:\.[\w-]+)*\.(?:txt|ts|mjs|js|sh|md|yml|py)\b/g)].map((m) => m[0]);
  assert.ok(named.length > 0, 'the comment names files by path (none read means the path reader stopped matching, not that the comment names none)');
  const gone = named.filter((p) => !fs.existsSync(path.join(REPO, p)) && !fs.existsSync(path.join(EXT, p)));
  assert.deepEqual(gone, [], 'the step\'s comment names a file the tree does not hold (from the repository root or from vscode-extension/): ' + JSON.stringify(gone) + '; the paths read: ' + JSON.stringify(named));
  assert.ok(!step.lines.join('\n').includes(String.fromCharCode(0x2014)), 'no em dash');
});

/** The per-file bound the script passes node, in ms, read from its node --test line (one such flag). */
function testTimeoutMs() {
  const m = read(SCRIPT).match(/--test-timeout=(\d+)/g) || [];
  assert.equal(m.length, 1, 'the script passes node --test one --test-timeout: ' + JSON.stringify(m));
  return Number(m[0].slice('--test-timeout='.length));
}

test('the step is bounded twice: its own timeout-minutes fits the margin under the job\'s cap at the measured head and the job\'s comment derives that number; node\'s --test-timeout in the script sits above the largest own { timeout } a rostered leg passes and under the step\'s bound, so a hung leg fails by name before the step is cut', () => {
  const job = extensionJob();
  const { cap, capLine } = jobCap(job);
  const step = steps(job).find((s) => s.name === STEP);
  assert.ok(step, 'the step exists (the first test holds the rest of its shape)');
  const bound = Number(step.fields['timeout-minutes']);
  assert.ok(Number.isInteger(bound) && bound >= 1, 'the step carries a timeout-minutes of its own (a roster whose legs exceed it fails this step by name rather than cancelling the job nameless): ' + JSON.stringify(step.fields['timeout-minutes']));
  // the margin the bound was cut from: the job's measured minutes and seconds in the step's own comment, under the cap
  const comment = step.comments.join('\n');
  const took = /in a job of (\d+) min (\d+) s/.exec(comment);
  assert.ok(took, 'the step\'s comment states the measured job time as "in a job of N min N s"');
  const marginSeconds = cap * 60 - (Number(took[1]) * 60 + Number(took[2]));
  assert.ok(bound * 60 <= marginSeconds, 'the step\'s bound (' + bound + ' min) fits the margin under the cap at the measured head (' + marginSeconds + ' s): a step that runs to its bound still ends the job under ' + cap + ' minutes; a larger roster raises the bound and the cap together; a job whose other phases grow under an unchanged cap re-measures the margin the same way (the step comment states the same)');
  assert.ok(comment.includes('re-measures here'), 'the step\'s comment names the re-measure condition for growth outside the roster (the job\'s other phases toward the cap), not only the roster-growth trigger');
  const jobComment = job.lines.slice(0, job.lines.indexOf(capLine)).filter((l) => /^\s*#/.test(l)).join('\n');
  assert.ok(new RegExp('\\b' + bound + ' minutes \\(its timeout-minutes\\)').test(jobComment), 'the job\'s cap comment derives the step\'s bound and names the same number (' + bound + ' minutes (its timeout-minutes)): a changed bound rewrites the sentence');
  // the job comment's sentence about this step (from "The Browser legs step below" to its end) points at this pin for the margin
  // and carries no copy of the measured job time or the margin in seconds: the measured time has one home, the step comment
  // above, which this pin reads (the job comment's other sentences record the served step's own history and are not read here)
  const about = /The Browser legs step below[\s\S]*?in the same PR\./.exec(jobComment.replace(/\n\s*#\s?/g, ' '));
  assert.ok(about, 'the job comment holds one sentence about the Browser legs step, from "The Browser legs step below" to "in the same PR."');
  assert.ok(!/\d+ min \d+ s/.test(about[0]) && !/\b\d+ s\b/.test(about[0]), 'the job comment\'s sentence about this step carries no copy of the measured job time or the margin in seconds (one home: the step comment, read by this pin): ' + about[0]);
  assert.ok(about[0].includes('tools/ci-browser-legs.test.mjs'), 'that sentence names this file as where the margin is derived: ' + about[0]);
  // node's per-file bound: above every own { timeout: N } a rostered source passes (else a legitimate slow leg is cut), under
  // the step's bound (else the step is cut nameless first)
  const ms = testTimeoutMs();
  const own = [];
  for (const e of parseRoster(read(path.join(EXT, ROSTER)))) {
    const src = sourceOf(e.bundle);
    if (!fs.existsSync(src)) continue;   // a stale line is the well-formed test's red
    for (const m of read(src).matchAll(/\btimeout:\s*(\d+)/g)) own.push({ bundle: e.bundle, ms: Number(m[1]) });
  }
  const largest = own.reduce((a, b) => (b.ms > a.ms ? b : a), { bundle: '(no rostered source passes a timeout)', ms: 0 });
  assert.ok(ms > largest.ms, 'node\'s --test-timeout (' + ms + ' ms) exceeds the largest own timeout a rostered leg passes (' + largest.ms + ' ms in ' + largest.bundle + '), so a leg that runs to its own bound is not cut by the file bound');
  assert.ok(ms < bound * 60 * 1000, 'node\'s --test-timeout (' + ms + ' ms) is under the step\'s bound (' + bound + ' min = ' + bound * 60 * 1000 + ' ms), so a hung file fails by name before the step is cut');
});

test('no step before the Test step installs a Playwright browser or restores its cache (the CI_SKIP property the gate-adopt pin reads; the legs skip under npm test and run only in the step above)', () => {
  const all = steps(extensionJob());
  const testAt = all.findIndex((s) => s.name === TEST_STEP);
  assert.ok(testAt > 0, 'the Test step is not the first step');
  const before = all.slice(0, testAt).flatMap((s) => s.code).join('\n');
  assert.ok(!/^\s+run: npx playwright install\b/m.test(before), 'no Playwright install before the Test step');
  assert.ok(!/^\s+path: ~\/\.cache\/ms-playwright\s*$/m.test(before) && !/^\s+key: playwright-/m.test(before), 'no browser-cache restore before the Test step');
  const install = all.find((s) => s.name === INSTALL);
  assert.match(install.fields.run || '', /^npx playwright install chromium$/, 'the install step installs Chromium alone (the roster rule\'s Chromium, the one engine a rostered leg launches, rests on this)');
});

// ── the roster and the tree ───────────────────────────────────────────────────────────────────────────────

const WELL_FORMED = /^out-tests\/\S+\.test\.js$/;
const sourceOf = (bundle) => path.join(REPO, bundle.replace(/^out-tests\//, '').replace(/\.test\.js$/, '.test.ts'));
/** Roster lines: [{ n, bundle }], comments and blanks dropped. */
function parseRoster(text) {
  return text.split('\n').map((line, i) => ({ n: i + 1, line })).filter(({ line }) => !/^\s*(#|$)/.test(line)).map(({ n, line }) => ({ n, bundle: line }));
}
/** A line's place, for every red that names one: "<file> line <n> (<bundle>)". */
const where = (file, e) => file + ' line ' + e.n + ' (' + e.bundle + ')';

test('the roster is well formed: each line is a bundle path naming a source in the tree, once (whether a line\'s source launches through inBrowser alone is the PR reviewer\'s to check: nothing in the tree reads it)', () => {
  const roster = parseRoster(read(path.join(EXT, ROSTER)));
  assert.ok(roster.length > 0, ROSTER + ' holds at least one line (the switch test is rostered, below): an empty roster would pass the loop below over nothing');
  const seen = new Map();
  for (const e of roster) {
    assert.match(e.bundle, WELL_FORMED, ROSTER + ' line ' + e.n + ' (' + JSON.stringify(e.bundle) + '): a line is a bundle path, out-tests/<dir>/<name>.test.js (a trailing space, tab or carriage return counts; the quoting shows it)');
    assert.ok(!seen.has(e.bundle), where(ROSTER, e) + ' duplicates line ' + seen.get(e.bundle) + ': remove one');
    seen.set(e.bundle, e.n);
    const src = sourceOf(e.bundle);
    assert.ok(fs.existsSync(src), where(ROSTER, e) + ' names ' + path.relative(REPO, src) + ', which is not in the tree (the source moved or was deleted): fix the line');
  }
});

/** The roster rule's four homes, and what each says: the rule is the PR reviewer's to check, the four cases the step reads
 *  green because nothing in the tree reads a leg's source for the rule, the witness of those four below, and that nothing
 *  checks that every browser leg in the tree is rostered. Each home is read with its line breaks and comment markers folded to one space and compared without
 *  case, so a rewrap or a capitalised lead-in is not a reword. */
const RULE_HOMES = [path.join(EXT, ROSTER), CI, SCRIPT, path.join(REPO, 'CONTRIBUTING.md')];
const RULE_WORDS = [
  'the roster rule is checked by the pr\'s reviewer',
  'a rostered leg that launches its own browser and swallows a failed launch without skipping',
  'a rostered module that launches nothing',
  'a leg that drives a browser from a child process and tolerates the child\'s failure',
  'a todo test that passes beside a real pass',
  'nothing checks that every browser leg in the tree is rostered, and main has no such check',
  'tools/ci-browser-legs.test.mjs runs a synthetic leg of each case and reads it green',
];

test('each home of the roster rule (the roster header, the step\'s comment, the script\'s header and CONTRIBUTING.md) states the rule as the PR reviewer\'s, names the four cases the step reads green, and says that nothing checks that every browser leg in the tree is rostered', () => {
  const flat = (text) => text.split('\n').map((l) => l.replace(/^\s*(?:#|\/\/)\s?/, '').trim()).join(' ').replace(/`/g, '').replace(/\s+/g, ' ').toLowerCase();
  for (const f of RULE_HOMES) {
    const text = flat(read(f));
    const missing = RULE_WORDS.filter((w) => !text.includes(w));
    assert.deepEqual(missing, [], path.relative(REPO, f) + ' is a home of the roster rule and does not say ' + JSON.stringify(missing) + ': each home states the rule as the PR reviewer\'s, names the four cases the step reads green (nothing in the tree reads a leg\'s source for the rule) and says that nothing checks that every browser leg in the tree is rostered, so a reader of any one of them does not take the rule for a machine check. A text pin: it holds that each home says these words, whatever the wrap; that the four cases read green is what the homes state, not what this test executes');
  }
});


/** vscode-extension/.vscodeignore's patterns hold a relative path, anchored to the whole path: `**` any run of path characters
 *  including /, `*` a run inside ONE segment. That is minimatch's reading, which vsce applies to .vscodeignore when it packs the
 *  VSIX (not executed here: the Shell job has no node_modules). tests/test_lab_dist.py reads the same file with Python's fnmatch,
 *  whose `*` crosses `/` (fnmatched below spells that reading), so the two readers part on a single `*` against a path with more
 *  segments; the pin below executes that divergence and asserts the two readers AGREE on every path it asks about, so a pattern
 *  that parts them on one of those paths is red here rather than a VSIX that differs from what the Python pin read. */
const escapeRe = (piece) => piece.replace(/[.+?^${}()|[\]\\]/g, '\\$&');
function vscodeignored(patterns, rel) {
  return patterns.some((p) => new RegExp('^' + p.split(/(\*\*|\*)/).map((piece) => piece === '**' ? '.*' : piece === '*' ? '[^/]*' : escapeRe(piece)).join('') + '$').test(rel));
}
/** The same file under Python's fnmatch (tests/test_lab_dist.py's `fnmatch.fnmatchcase(rel, p)`): `*` and `**` any run including /,
 *  `?` one character; the file holds no bracket class. */
function fnmatched(patterns, rel) {
  return patterns.some((p) => new RegExp('^' + p.split(/(\*\*|\*|\?)/).map((piece) => piece === '**' || piece === '*' ? '.*' : piece === '?' ? '.' : escapeRe(piece)).join('') + '$').test(rel));
}

test('the CI-only files under vscode-extension/ (the roster, the script and the reporter) are named by .vscodeignore, so vsce ships none of them in the extension people install', () => {
  const patterns = read(path.join(EXT, '.vscodeignore')).split('\n').map((l) => l.trim()).filter((l) => l && !l.startsWith('#'));
  for (const rel of [ROSTER, path.relative(EXT, SCRIPT), path.relative(EXT, REPORTER)]) {
    assert.ok(fs.existsSync(path.join(EXT, rel)), rel + ' exists under vscode-extension/ (a moved file re-anchors this pin)');
    assert.ok(vscodeignored(patterns, rel), rel + ' would ship in the VSIX: name it in vscode-extension/.vscodeignore (a pattern the file\'s glob semantics match: ' + JSON.stringify(patterns) + ')');
  }
  assert.ok(!vscodeignored(patterns, 'package.json') && !vscodeignored(patterns, 'dist/extension.js'), 'the matcher does not swallow shipped files (a pattern over-matching would pass the pin for the wrong reason)');
  // the two readers' `*`, executed: this matcher keeps `*` inside one segment where fnmatch's crosses `/`, so `scripts/*` reaches
  // scripts/a/b.sh under fnmatch and not under minimatch; on every path this pin asks about the two readers must agree, else the
  // VSIX vsce packs differs from what tests/test_lab_dist.py read from the same file
  assert.equal(vscodeignored(['scripts/*'], 'scripts/a/b.sh'), false, 'minimatch\'s reading: * stays inside one segment');
  assert.equal(fnmatched(['scripts/*'], 'scripts/a/b.sh'), true, 'fnmatch\'s reading: * crosses /');
  assert.equal(vscodeignored(['scripts/**'], 'scripts/a/b.sh'), true, '** crosses segments in both readers');
  for (const rel of [ROSTER, path.relative(EXT, SCRIPT), path.relative(EXT, REPORTER), 'package.json', 'dist/extension.js']) {
    assert.equal(vscodeignored(patterns, rel), fnmatched(patterns, rel), rel + ': the two readers of .vscodeignore part on this path (minimatch, vsce\'s: ' + vscodeignored(patterns, rel) + '; fnmatch, tests/test_lab_dist.py\'s: ' + fnmatched(patterns, rel) + '), so a pattern in the file leans on a single * across a /: write it so both readers agree, or re-derive this pin and the Python one together: ' + JSON.stringify(patterns));
  }
});

// ── the script ────────────────────────────────────────────────────────────────────────────────────────

function bash(args, opts = {}) {
  const r = spawnSync('bash', args, { encoding: 'utf8', ...opts });
  assert.equal(r.error, undefined, 'bash runs: ' + (r.error && r.error.message));
  return r;
}

test('the script exists, is executable, runs node --test over the roster array (no xargs) with the reporter beside the spec reporter, and spells the empty-roster guard (each executed below through the stub)', () => {
  assert.ok(fs.existsSync(SCRIPT), 'the step\'s script exists at ' + path.relative(REPO, SCRIPT));
  assert.ok(fs.statSync(SCRIPT).mode & 0o111, 'the script is executable');
  assert.ok(fs.existsSync(REPORTER), 'the reporter the script passes to node --test exists at ' + path.relative(REPO, REPORTER));
  const src = read(SCRIPT);
  assert.match(src, /^REPORTER=\.\/scripts\/ci-browser-legs-reporter\.mjs$/m, 'the script names the reporter once, as REPORTER, by a path node resolves from vscode-extension/');
  assert.equal((src.match(/--test-reporter="\$REPORTER" --test-reporter-destination="\$rep"/g) || []).length, 1, 'node --test is handed the reporter with a destination file the script reads after the run (executed below)');
  assert.ok(src.includes('echo "no legs in the roster"; exit 0'), 'the empty-roster guard is spelled in the script (executed below)');
  assert.match(src, /^node --test .*"\$\{legs\[@\]\}" \|\| status=\$\?$/m, 'node --test runs the roster array directly and its status is kept, so the status is node\'s own on every platform (xargs would map a failed command\'s status to 123 on GNU and to 1 on BSD and macOS; executed below: 1 and 7 pass through)');
  assert.ok(!src.split('\n').some((l) => !/^\s*#/.test(l) && /xargs/.test(l)), 'no xargs on a code line of the script (a comment may name it)');
  // the header states the post-run property as what the record proves, A TEST OF ITS BUNDLE PASSED, and names the boundary of
  // that proof (node's events carry no launch). A text pin on the header's prose, the # lines before the code: it holds that the
  // header says what the record proves and no more, so a reader does not take the property for a launch record; the derivation
  // itself is executed in the post-run test below over records with no pass, and the boundary's other home, the parenthetical
  // in the unrun red, is read from the script's stderr there.
  const headLines = src.split('\n').slice(1);
  const headEnd = headLines.findIndex((l) => !l.startsWith('#'));
  const scriptHeader = headLines.slice(0, headEnd < 0 ? headLines.length : headEnd).map((l) => l.replace(/^# ?/, '')).join(' ');
  assert.ok(scriptHeader.includes('derives, per rostered leg, that A TEST OF ITS BUNDLE PASSED') && scriptHeader.includes('That is the whole of what the record can prove: node\'s events carry no launch'), 'the script header states the post-run property as A TEST OF ITS BUNDLE PASSED and its boundary, "That is the whole of what the record can prove: node\'s events carry no launch" (a text pin on the header\'s prose: it guards that the header states what the record proves and its boundary, so the property is not read as a launch record; the derivation is executed below. Holds the sentence: a reword of the header\'s two phrases moves this pin too)');
});

/** A synthetic tree: the script and the reporter under vscode-extension/scripts; under ui/webview two browser legs as SOURCES
 *  (a and b launch through inBrowser; a has a bundle, b none; a's second test has a newline and a # in its name, spelled \n
 *  and # in the source as node's record escapes them), whose text decides nothing here (the script reads a source's presence
 *  alone); and a stub node on PATH that records its arguments and then either runs the REAL node over them
 *  (CBL_STUB_REAL_NODE names it: the composition of the script, node and the real reporter) or writes CBL_STUB_REPORT (when
 *  set) to the reporter's destination and exits CBL_STUB_EXIT (0 unless set). Returns a runner over roster text (null removes
 *  the file) that runs the script with the switch set to 1 as the step does (stub.switch names another value; null runs it
 *  unset, as a local run may; stub.check runs --check; stub.report is the record the stub writes; stub.exit its exit;
 *  stub.real runs the real node); `node` in its result is the argument list of the node --test call without the reporter
 *  flags. `ext` is the physical path of the tree's vscode-extension, as node spells a bundle in its record, and
 *  `rec(bundle, fields...)` spells one record line for that bundle (the reporter's eight fields, the path first). */
function syntheticTree(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'cbl-'));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const ext = path.join(root, 'vscode-extension');
  for (const d of ['vscode-extension/scripts', 'vscode-extension/out-tests/ui/webview', 'ui/webview', 'bin']) fs.mkdirSync(path.join(root, d), { recursive: true });
  fs.copyFileSync(SCRIPT, path.join(ext, 'scripts', 'ci-browser-legs.sh'));
  fs.copyFileSync(REPORTER, path.join(ext, 'scripts', 'ci-browser-legs-reporter.mjs'));
  const shared = 'import { inBrowser } from "./real-viewer-leg";\n';
  const web = (name, text) => fs.writeFileSync(path.join(root, 'ui', 'webview', name), text);
  web('a-browser.test.ts', shared + 'test("leg a opens the page", async (t) => { await inBrowser(t, async (browser) => {}); });\n'
    + 'test("leg a keeps the slice\\nwhole # 2", async (t) => { await inBrowser(t, async (browser) => {}); });\n');
  web('b-browser.test.ts', shared + 'test("leg b opens the page", async (t) => { await inBrowser(t, async (browser) => {}); });\n');
  fs.writeFileSync(path.join(ext, 'out-tests', 'ui', 'webview', 'a-browser.test.js'), '');
  const log = path.join(root, 'node-args.txt');
  fs.writeFileSync(path.join(root, 'bin', 'node'), [
    '#!/bin/sh',
    'printf \'%s\\n\' "$@" > "' + log + '"',
    'if [ -n "${CBL_STUB_REAL_NODE:-}" ]; then exec "$CBL_STUB_REAL_NODE" "$@"; fi',
    'prev=""',
    'for a in "$@"; do',
    '  case "$a" in --test-reporter-destination=*) if [ "$prev" = "--test-reporter=./scripts/ci-browser-legs-reporter.mjs" ] && [ -n "${CBL_STUB_REPORT:-}" ]; then printf \'%s\\n\' "$CBL_STUB_REPORT" > "${a#--test-reporter-destination=}"; fi;; esac',
    '  prev="$a"',
    'done',
    'exit "${CBL_STUB_EXIT:-0}"',
    '',
  ].join('\n'), { mode: 0o755 });
  const A = 'out-tests/ui/webview/a-browser.test.js', B = 'out-tests/ui/webview/b-browser.test.js';
  const run = (roster, stub = {}) => {
    if (roster === null) fs.rmSync(path.join(ext, ROSTER), { force: true }); else fs.writeFileSync(path.join(ext, ROSTER), roster);
    fs.rmSync(log, { force: true });
    const env = { ...process.env, PATH: path.join(root, 'bin') + path.delimiter + process.env.PATH };
    delete env.CBL_STUB_REPORT; delete env.CBL_STUB_EXIT; delete env.CBL_STUB_REAL_NODE; delete env.NODE_TEST_CONTEXT;
    env[SWITCH] = '1';
    if (stub.switch === null) delete env[SWITCH]; else if (stub.switch !== undefined) env[SWITCH] = stub.switch;
    if (stub.report !== undefined) env.CBL_STUB_REPORT = stub.report;
    if (stub.exit !== undefined) env.CBL_STUB_EXIT = String(stub.exit);
    if (stub.real) env.CBL_STUB_REAL_NODE = process.execPath;
    const r = bash([path.join(ext, 'scripts', 'ci-browser-legs.sh'), ...(stub.check ? ['--check'] : [])], { cwd: root, env });
    const args = fs.existsSync(log) ? fs.readFileSync(log, 'utf8').split('\n').filter(Boolean) : null;
    return { status: r.status, out: r.stdout, err: r.stderr, node: args && args.filter((a) => !a.startsWith('--test-reporter') && !a.startsWith('--test-timeout=')), reporters: args && args.filter((a) => a.startsWith('--test-reporter')), testTimeout: args && args.find((a) => a.startsWith('--test-timeout=')) };
  };
  const real = fs.realpathSync(ext);
  const rec = (bundle, ...fields) => [path.join(real, bundle), ...fields].join('\t') + '\n';
  return { run, root, ext: real, rec, A, B };
}

test('the script runs the rostered legs through node --test when the roster is well formed and current, runs the pre-run checks alone under --check (which does not require the bundle), and prints "no legs in the roster" and starts no node on an empty roster', (t) => {
  const { run, rec, A, B } = syntheticTree(t);
  // the stub's record: a's one test passed (with no record a rostered leg is red as unrun, the property the post-run test executes)
  const ok = run('# header\n\n' + A + '\n', { report: rec(A, 'pass', 'test', '-', 'test', 'leg a opens the page', '', '-') });
  assert.equal(ok.status, 0, 'a well-formed roster whose sources and bundles are present runs clean, exit 0; stderr:\n' + ok.err);
  assert.deepEqual(ok.node, ['--test', A], 'node --test received the roster\'s one bundle');
  assert.equal(ok.testTimeout, '--test-timeout=' + testTimeoutMs(), 'node --test received the per-file bound the script spells (its edges are pinned above)');
  assert.deepEqual(ok.reporters.filter((a) => !a.startsWith('--test-reporter-destination=')), ['--test-reporter=spec', '--test-reporter=./scripts/ci-browser-legs-reporter.mjs'], 'the spec reporter for the log and the step\'s own reporter for the post-run read');
  assert.ok(!ok.out.includes('no legs in the roster'));
  // --check: the pre-run checks alone, no node started; the bundle check is the step's run's, so b (a source, no bundle) passes here
  const check = run('# header\n' + A + '\n' + B + '\n', { check: true });
  assert.equal(check.status, 0, '--check over a well-formed roster whose sources are present exits 0, a bundle not yet built included; stderr:\n' + check.err);
  assert.ok(check.out.includes('ci-browser-legs: the roster is well formed and every line names a source in the tree: 2 rostered (--check reads the roster alone and starts no node --test; the step\'s run also checks that each rostered bundle is built under out-tests/)'), '--check prints its agreement line with the count of rostered lines: ' + JSON.stringify(check.out));
  assert.equal(check.node, null, '--check starts no node');
  const empty = run('# only a comment\n\n   \n');
  assert.equal(empty.status, 0, 'an empty roster exits 0 (the guard, not a red); stderr:\n' + empty.err);
  assert.ok(empty.out.includes('no legs in the roster'), 'the guard says so: ' + JSON.stringify(empty.out));
  assert.equal(empty.node, null, 'node was not started: with no file arguments node --test would run its default glob');
});

test('the script refuses, naming the line and the remedy, on: a missing roster file, a stale line, a duplicate, a missing bundle, and a malformed line (six shapes, each shown with its whitespace visible as bash\'s %q spells it); every refusal after the roster is read ends with the summary line, and no leg ran', (t) => {
  const { run, A, B } = syntheticTree(t);
  const C = 'out-tests/ui/webview/c-browser.test.js';
  const SUMMARY = 'ci-browser-legs: the roster is malformed or stale, or a rostered bundle is not built (above); no leg ran';
  const refused = (r, ...needles) => {
    assert.equal(r.status, 1, 'exit 1; stderr: ' + r.err);
    for (const n of needles) assert.ok(r.err.includes(n), 'stderr names ' + JSON.stringify(n) + ':\n' + r.err);
    assert.equal(r.node, null, 'no leg ran');
    assert.ok(r.err.includes(SUMMARY), 'the summary line closes the refusal:\n' + r.err);
  };
  const missing = run(null);
  assert.equal(missing.status, 1, 'a missing roster file is red, exit 1; stderr:\n' + missing.err);
  assert.ok(missing.err.includes('ci-browser-legs: ' + ROSTER + ' is not in vscode-extension/, where the roster is read from: restore it'), 'a missing roster file is red naming the file and the remedy (restore it):\n' + missing.err);
  assert.equal(missing.node, null, 'no leg ran');
  refused(run('# header\n' + A + '\n' + C + '\n'), ROSTER + ' line 3: \'' + C + '\' names ui/webview/c-browser.test.ts, which is not in the tree (the source moved or was deleted): fix the roster line');
  refused(run(A + '\n' + A + '\n'), ROSTER + ' line 2: \'' + A + '\' duplicates line 1: remove one');
  refused(run(B + '\n'), ROSTER + ' line 1: \'' + B + '\' is not under out-tests/ (the Test step\'s npm test builds it; locally, node esbuild.js --tests): build the bundles before this step');
  // a malformed line: the LINE is shown as bash's %q spells it, so an invisible cause (a carriage return, a tab, a trailing
  // space, leading whitespace) is visible in the red: a source path in place of a bundle path, a carriage return at the end, a
  // tab and pasted text after the path, a leading tab, spaces then a tab before the path, and a trailing space
  refused(run('ui/webview/a-browser.test.ts\n'), ROSTER + ' line 1: ui/webview/a-browser.test.ts is not a bundle path (out-tests/<dir>/<name>.test.js; a trailing space, tab or carriage return counts and is shown here as bash\'s %q spells it): fix the line');
  refused(run(A + '\r\n'), ROSTER + ' line 1: $\'' + A + '\\r\' is not a bundle path');
  refused(run(A + '\tpasted text\n'), ROSTER + ' line 1: $\'' + A + '\\tpasted text\' is not a bundle path');
  refused(run('\t' + A + '\n'), ROSTER + ' line 1: $\'\\t' + A + '\' is not a bundle path');
  refused(run('  \t' + A + '\n'), ROSTER + ' line 1: $\'  \\t' + A + '\' is not a bundle path');
  refused(run(A + ' \n'), ROSTER + ' line 1: ' + A + '\\  is not a bundle path');
});

test('after node --test the script derives per rostered leg that at least one attributable pass ran, red otherwise (todo-only, a describe() that registers none, a file that registered nothing, a failure inside a todo); reds a skipped test naming the test, its reason and the switch\'s state; reds a failure inside a todo and a file that failed as a whole by name; prints the lost-browser remedy beside a leg whose failure names the switch; passes node\'s status through; the unrun and the skip remedies take the line out of the roster', (t) => {
  const { run, root, rec, A, B } = syntheticTree(t);
  const PASS = rec(A, 'pass', 'test', '-', 'test', 'leg a opens the page', '', '-');
  const skipped = run(A + '\n', { report: PASS + rec(A, 'pass', 'test', 'skip', 'test', 'leg a keeps the slice\\nwhole # 2', 'no playwright chromium on this box', '-') });
  assert.equal(skipped.status, 1, 'a skip under the switch is red; stderr: ' + skipped.err);
  assert.deepEqual(skipped.node, ['--test', A], 'the leg ran (the skip is read from the run, not refused before it)');
  assert.ok(skipped.err.includes('ci-browser-legs: skipped with ' + SWITCH + '=1: \'leg a keeps the slice\\nwhole # 2\' # SKIP no playwright chromium on this box (' + A + ')'), 'the skip names the test as the record spells it (a newline written \\n), its reason and its leg:\n' + skipped.err);
  assert.ok(skipped.err.includes('a rostered leg skipped a test with ' + SWITCH + '=1, so the step claims coverage it did not run'), 'the skip\'s red says the step claims coverage it did not run:\n' + skipped.err);
  assert.ok(skipped.err.includes('only inBrowser in ui/webview/real-viewer-leg.ts turns a launch it cannot make into a failure here') && skipped.err.includes('until every test of the leg runs here, take its line out of ' + ROSTER), 'the skip\'s red carries the set-switch remedy (only inBrowser turns a launch it cannot make into a failure) and the remedy that takes the line out of the roster:\n' + skipped.err);
  assert.ok(!skipped.err.includes('no test of this leg passed'), 'a leg with a pass beside its skip is not called unrun:\n' + skipped.err);
  // the same skip with the switch unset, as a local run may have it: still red, and the message says the switch is unset
  // and that the step sets it, instead of claiming a state the run did not have
  const unset = run(A + '\n', { report: PASS + rec(A, 'pass', 'test', 'skip', 'test', 'leg a opens the page', 'why', '-'), switch: null });
  assert.equal(unset.status, 1, 'a skip with the switch unset is red too; stderr: ' + unset.err);
  assert.ok(unset.err.includes('skipped with ' + SWITCH + ' unset: \'leg a opens the page\' # SKIP why (' + A + ')'), 'a skip with the switch unset names the test, its reason, its leg and the switch as unset:\n' + unset.err);
  assert.ok(unset.err.includes('a rostered leg skipped a test with ' + SWITCH + ' unset, so this run claims coverage it did not run: the step sets ' + SWITCH + '=1'), 'the unset-switch red says this run claims coverage it did not run and that the step sets the switch:\n' + unset.err);
  assert.ok(!unset.err.includes(SWITCH + '=1:') && !unset.err.includes('with ' + SWITCH + '=1,'), 'no line claims the switch was set:\n' + unset.err);
  const clean = run(A + '\n', { report: PASS + rec(A, 'pass', 'suite', '-', 'test', 'a suite with tests', '', '-') });
  assert.equal(clean.status, 0, 'a pass beside a suite\'s own pass: no red: ' + clean.err);
  assert.equal(clean.err, '', 'nothing on stderr when every rostered leg passed a test');
  // the property: no attributable pass. Four shapes, each red naming the leg and what the record held, none called a skip
  const UNRUN = 'ci-browser-legs: ' + A + ': no test of this leg passed in this run (the record holds ';
  const none = run(A + '\n', { report: rec(A, 'pass', 'test', '-', 'file-level', A, '', '-') });
  assert.equal(none.status, 1, 'a file that registered nothing is red; stderr: ' + none.err);
  assert.deepEqual(none.node, ['--test', A], 'the leg ran (the empty run is read from the record, not refused before it)');
  assert.ok(none.err.includes(UNRUN + '0 skipped, 0 todo, 0 suite and 1 file-level results for it), so the step claims coverage it did not run') && none.err.includes('so take its line out of ' + ROSTER + ' until one runs'), 'a file that registered nothing is red as unrun with what the record held (1 file-level result) and the remedy that takes the line out of the roster:\n' + none.err);
  // the unrun red carries the boundary of what the record proves beside its remedy (read from the run's stderr): a pass is the
  // most the record proves, and the browser part's own run is read only by the skip and lost-browser lines when its launch is reached
  assert.ok(none.err.includes('a rostered leg holds a test that runs and passes here (a pass is the most the record proves: a pass from a test needing no browser satisfies this check, and the browser part\'s own run is read only by the skip and lost-browser lines when its launch is reached)'), 'the unrun red says, beside its remedy, that a pass is the most the record proves, so a reader of the red does not take the property for a launch record (holds the sentence as the script emits it: a reword of the parenthetical in the script moves this pin too):\n' + none.err);
  const suite = run(A + '\n', { report: rec(A, 'pass', 'suite', '-', 'test', 'a suite that registers none', '', '-') });
  assert.equal(suite.status, 1, 'a describe() that registers no test is red; stderr: ' + suite.err);
  assert.ok(suite.err.includes(UNRUN + '0 skipped, 0 todo, 1 suite and 0 file-level results for it)'), 'a describe() that registers none is red as unrun with what the record held (1 suite result):\n' + suite.err);
  const todos = run(A + '\n', { report: rec(A, 'pass', 'test', 'todo', 'test', 'bodyless todo', '', '-') + rec(A, 'pass', 'test', 'todo', 'test', 'a todo with a passing body', 'waiting on the browser', '-') });
  assert.equal(todos.status, 1, 'a leg whose tests are all todo is red; stderr: ' + todos.err);
  assert.ok(todos.err.includes(UNRUN + '0 skipped, 2 todo, 0 suite and 0 file-level results for it)'), 'a todo-only leg is red as unrun with what the record held (2 todo results):\n' + todos.err);
  assert.ok(!todos.err.includes('failed inside a todo'), 'a todo that passed is not a discarded failure:\n' + todos.err);
  const todoFail = run(A + '\n', { report: rec(A, 'fail', 'test', 'todo', 'test', 'a real failure inside a todo', 'the leg is broken', 'testCodeFailure') });
  assert.equal(todoFail.status, 1, 'a failure inside a todo is red although node exits 0; stderr: ' + todoFail.err);
  assert.ok(todoFail.err.includes('ci-browser-legs: ' + A + ': \'a real failure inside a todo\' failed inside a todo (the leg is broken): node discards the failure (# fail 0, exit 0), so the step would read green over a broken test: remove the todo, or fix the test and remove it'), 'a failure inside a todo is red by name with the test, its message, why node hides it (# fail 0, exit 0) and the remedy:\n' + todoFail.err);
  assert.ok(todoFail.err.includes(UNRUN + '0 skipped, 1 todo, 0 suite and 0 file-level results for it)'), 'and the leg ran no counting pass:\n' + todoFail.err);
  // a real pass beside a failure inside a todo: the property holds, the discarded failure is still red
  const mixed = run(A + '\n', { report: PASS + rec(A, 'fail', 'test', 'todo', 'test', 'a swallowed failure', 'the leg is broken', 'testCodeFailure') });
  assert.equal(mixed.status, 1, 'a failure inside a todo beside a real pass: exit 1; stderr:\n' + mixed.err);
  assert.ok(mixed.err.includes('\'a swallowed failure\' failed inside a todo (the leg is broken)') && !mixed.err.includes('no test of this leg passed'), 'a failure inside a todo beside a real pass is still red by name, and the leg is not called unrun:\n' + mixed.err);
  for (const r of [none, suite, todos, todoFail]) assert.ok(!r.err.includes('skipped with'), 'an unrun leg is not called a skip:\n' + r.err);
  // two rostered legs, one of which ran nothing: the red names that one and not the other (attribution is per bundle)
  fs.writeFileSync(path.join(root, 'vscode-extension', B), '');   // b has no bundle in the tree by default
  const two = run(A + '\n' + B + '\n', { report: PASS + rec(B, 'pass', 'test', 'todo', 'test', 'leg b todo', '', '-') });
  assert.equal(two.status, 1, 'two rostered legs, one that ran nothing: exit 1; stderr:\n' + two.err);
  assert.ok(two.err.includes('ci-browser-legs: ' + B + ': no test of this leg passed') && !two.err.includes('ci-browser-legs: ' + A + ': no test'), 'the leg that ran nothing is named and the one that passed is not:\n' + two.err);
  // a file that failed as a whole (node's file-level result failing: a timeout under --test-timeout, or a throw at load)
  const timedOut = run(A + '\n', { report: rec(A, 'fail', 'test', '-', 'file-level', A, 'test timed out after 300000ms', 'testTimeoutFailure'), exit: 1 });
  assert.equal(timedOut.status, 1, 'node\'s failure stands');
  assert.ok(timedOut.err.includes('ci-browser-legs: ' + A + ' failed as a whole (testTimeoutFailure: test timed out after 300000ms): a file that timed out under node\'s --test-timeout, or threw at load, ran no test that counts'), 'a file that failed as a whole is red naming the file and the failure type:\n' + timedOut.err);
  assert.ok(!timedOut.err.includes('no test of this leg passed'), 'a failed file is node\'s red, not called unrun on top:\n' + timedOut.err);
  // node's own exit status is the step's: the roster array is node's argument list, with no xargs to map it (GNU 123, BSD 1)
  const failed = run(A + '\n', { report: rec(A, 'fail', 'test', '-', 'test', 'leg a opens the page', 'an assertion of the leg\'s own failed', 'testCodeFailure'), exit: 1 });
  assert.equal(failed.status, 1, 'node\'s failure is the step\'s, as node\'s own status');
  assert.equal(failed.err, '', 'a failure for a reason of the leg\'s own gets no label of the script\'s (node\'s own report carries it):\n' + failed.err);
  // a failure whose message names the switch is inBrowser failing to launch under it: the remedy is printed beside the leg
  const LOST = SWITCH + ' is set and this leg cannot run: no playwright browser on this box; the browser leg needs one: browserType.launch: Executable doesn\'t exist at /nowhere';
  const lost = run(A + '\n', { report: rec(A, 'fail', 'test', '-', 'test', 'leg a opens the page', LOST, 'testCodeFailure'), exit: 1 });
  assert.equal(lost.status, 1);
  assert.ok(lost.err.includes('ci-browser-legs: ' + A + ': \'leg a opens the page\' failed under ' + SWITCH + '=1 because inBrowser could not launch (' + LOST + '): the runner lost its browser: check the Chromium install step'), 'a failure whose message names the switch is red with the lost-browser remedy beside the leg (check the Chromium install step):\n' + lost.err);
  // the phrase quoted AFTER other text (the rostered switch test's assertion messages embed a child run's stdout, which carries
  // it): an ordinary failure of the leg, no LOST line, no label of the script's, node's red passed through
  const quoted = run(A + '\n', { report: rec(A, 'fail', 'test', '-', 'test', 'leg a opens the page', 'the leg failed under the switch; the child run printed: ' + LOST, 'testCodeFailure'), exit: 1 });
  assert.equal(quoted.status, 1, 'node\'s failure stands');
  assert.ok(!quoted.err.includes('the runner lost its browser'), 'a message that quotes the phrase after other text is not a lost browser (LOST reads the start of the message):\n' + quoted.err);
  assert.equal(quoted.err, '', 'an ordinary failure gets no label of the script\'s:\n' + quoted.err);
  // the switch under a non-"1" non-empty value: the script reads it as set (any non-empty value arms it, as the helper does),
  // naming the value in the skip's red and giving the set-switch remedy
  const yes = run(A + '\n', { report: PASS + rec(A, 'pass', 'test', 'skip', 'test', 'leg a opens the page', 'why', '-'), switch: 'yes' });
  assert.equal(yes.status, 1, 'a skip under the switch set to yes is red; stderr: ' + yes.err);
  assert.ok(yes.err.includes('skipped with ' + SWITCH + '=yes: \'leg a opens the page\' # SKIP why (' + A + ')'), 'the skip names the switch\'s value as the run had it (yes):\n' + yes.err);
  assert.ok(yes.err.includes('a rostered leg skipped a test with ' + SWITCH + '=yes, so the step claims coverage it did not run') && yes.err.includes('only inBrowser in ui/webview/real-viewer-leg.ts turns a launch it cannot make into a failure here'), 'the set-switch remedy, not the unset one: the script\'s two reads arm on any non-empty value:\n' + yes.err);
  const both = run(A + '\n', { report: rec(A, 'pass', 'test', 'skip', 'test', 'leg a opens the page', 'why', '-'), exit: 7 });
  assert.equal(both.status, 7, 'with a failure and a skip node\'s own status (7) stands, not overwritten by the skip\'s status=1, and the skip is still named');
  assert.ok(both.err.includes('skipped with ' + SWITCH + '=1'), 'with node\'s own failure status (7) the skip is still named:\n' + both.err);
});

/** Synthetic bundles for the reporter and the composition: each a node:test module of one shape, written under `dir` as
 *  out-tests/ui/webview/<name>-browser.test.js; returns the bundle paths by shape. */
function writeShapes(dir) {
  const w = (name, body) => { fs.writeFileSync(path.join(dir, 'out-tests', 'ui', 'webview', name + '-browser.test.js'), body); return 'out-tests/ui/webview/' + name + '-browser.test.js'; };
  const head = 'const { test, describe } = require("node:test"); const assert = require("node:assert");\n';
  return {
    passSkip: w('pass-skip', head + 'test("one pass", () => {});\ntest("one skip", (t) => { t.skip("no browser # here"); });\n'),
    todoBoth: w('todo-both', head + 'test.todo("bodyless todo");\ntest("a todo with a passing body", { todo: "waiting on the browser" }, () => {});\n'),
    describeNone: w('describe-none', head + 'describe("a suite that registers none", () => {});\n'),
    nothing: w('nothing', ''),
    todoFail: w('todo-fail', head + 'test("a real failure inside a todo", { todo: true }, () => { assert.fail("the leg is broken"); });\n'),
    mixed: w('mixed', head + 'test("one real pass", () => {});\ntest("a swallowed failure", { todo: true }, () => { assert.fail("the leg is broken"); });\n'),
    describePass: w('describe-pass', head + 'describe("outer suite", () => { test("inner pass\\nwith a newline\\tand a tab", () => {}); });\n'),
    lost: w('lost', head + 'test("the launch", () => { assert.fail("' + SWITCH + ' is set and this leg cannot run: no playwright browser on this box"); });\n'),
    loadThrow: w('load-throw', head + 'throw new Error("thrown at load");\n'),
  };
}

test('the reporter, executed with a real node --test over synthetic bundles: one line per result attributed to its file, a describe() as a suite, a skip and a todo as directives, a failure inside a todo as a fail, node\'s file-level result marked for a file that registered nothing and for a file that threw at load, and a name\'s tab and newline written \\t and \\n', (t) => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'cbl-rep-'));
  t.after(() => fs.rmSync(dir, { recursive: true, force: true }));
  fs.mkdirSync(path.join(dir, 'out-tests', 'ui', 'webview'), { recursive: true });
  const S = writeShapes(dir);
  const out = path.join(dir, 'record.tsv');
  const env = {}; for (const k of ['PATH', 'HOME', 'TMPDIR']) if (process.env[k] !== undefined) env[k] = process.env[k];
  const r = spawnSync(process.execPath, ['--test', '--test-reporter=' + REPORTER, '--test-reporter-destination=' + out, ...Object.values(S)], { cwd: dir, encoding: 'utf8', env, timeout: 120000 });
  assert.equal(r.status, 1, 'node exits 1 (the lost shape fails for real); stderr: ' + r.stderr);
  const real = fs.realpathSync(dir);
  const lines = fs.readFileSync(out, 'utf8').split('\n').filter(Boolean).map((l) => l.split('\t'));
  const of = (bundle) => lines.filter((f) => f[0] === path.join(real, bundle)).map((f) => f.slice(1));
  assert.deepEqual(of(S.passSkip), [['pass', 'test', '-', 'test', 'one pass', '', '-'], ['pass', 'test', 'skip', 'test', 'one skip', 'no browser # here', '-']]);
  assert.deepEqual(of(S.todoBoth), [['pass', 'test', 'todo', 'test', 'bodyless todo', '', '-'], ['pass', 'test', 'todo', 'test', 'a todo with a passing body', 'waiting on the browser', '-']]);
  assert.deepEqual(of(S.describeNone), [['pass', 'suite', '-', 'test', 'a suite that registers none', '', '-']], 'a describe() that registers none is one suite result and nothing else');
  assert.deepEqual(of(S.nothing), [['pass', 'test', '-', 'file-level', S.nothing, '', '-']], 'a file that registered nothing is node\'s file-level pass, marked');
  assert.deepEqual(of(S.todoFail), [['fail', 'test', 'todo', 'test', 'a real failure inside a todo', 'the leg is broken', 'testCodeFailure']]);
  assert.deepEqual(of(S.mixed), [['pass', 'test', '-', 'test', 'one real pass', '', '-'], ['fail', 'test', 'todo', 'test', 'a swallowed failure', 'the leg is broken', 'testCodeFailure']]);
  assert.deepEqual(of(S.describePass), [['pass', 'test', '-', 'test', 'inner pass\\nwith a newline\\tand a tab', '', '-'], ['pass', 'suite', '-', 'test', 'outer suite', '', '-']], 'the inner test first, then the suite; the name\'s newline and tab escaped');
  assert.deepEqual(of(S.lost), [['fail', 'test', '-', 'test', 'the launch', SWITCH + ' is set and this leg cannot run: no playwright browser on this box', 'testCodeFailure']]);
  // a file that threw at load is node's file-level result FAILING, and the file-level mark on it is the one input the script's
  // file-failed-whole red reads in a real run (the post-run test above hands the script that row through the stub); the message
  // is node's own (the throw's text goes to the file's stderr, not to the event), so it is read as present, not by its words
  const thrown = of(S.loadThrow);
  assert.deepEqual(thrown.map((f) => [f[0], f[1], f[2], f[3], f[4], f[6]]), [['fail', 'test', '-', 'file-level', S.loadThrow, 'testCodeFailure']], 'a file that threw at load is node\'s file-level result, failing, and marked file-level: ' + JSON.stringify(thrown));
  assert.ok(thrown[0][5] !== '', 'the file-level failure carries node\'s message: ' + JSON.stringify(thrown));
  assert.equal(lines.length, 13, 'thirteen results over the nine bundles and no other line: ' + JSON.stringify(lines));
  assert.ok(lines.every((f) => f.length === 8), 'eight fields per line');
});

test('the composition, executed: the script with the real node and the real reporter over the shapes as rostered legs reds todo-only, describe-none, nothing and a failure inside a todo by leg, names the skip, prints the lost-browser remedy, reds a file that threw at load as failed as a whole, and passes a clean roster', (t) => {
  const { run, root } = syntheticTree(t);
  const S = writeShapes(path.join(root, 'vscode-extension'));
  // each shape's source in the tree, since the script refuses a line whose source is absent (the text decides nothing here)
  const shared = 'import { inBrowser } from "./real-viewer-leg";\n';
  for (const b of Object.values(S)) {
    const name = path.basename(b, '.test.js');
    fs.writeFileSync(path.join(root, 'ui', 'webview', name + '.test.ts'), shared + 'test("x", async (t) => { await inBrowser(t, async () => {}); });\n');
  }
  const all = run(Object.values(S).join('\n') + '\n', { real: true });
  assert.equal(all.status, 1, 'node\'s exit 1 (the lost shape) is the script\'s; stderr: ' + all.err);
  for (const b of [S.todoBoth, S.describeNone, S.nothing, S.todoFail]) assert.ok(all.err.includes('ci-browser-legs: ' + b + ': no test of this leg passed in this run'), b + ' is red as unrun:\n' + all.err);
  for (const b of [S.passSkip, S.mixed, S.describePass, S.lost, S.loadThrow]) assert.ok(!all.err.includes('ci-browser-legs: ' + b + ': no test of this leg passed'), b + ' is not called unrun:\n' + all.err);
  assert.ok(all.err.includes('ci-browser-legs: ' + S.loadThrow + ' failed as a whole (testCodeFailure: '), 'the composition reds the file that threw at load as failed as a whole, from the reporter\'s file-level mark on node\'s failing file-level result:\n' + all.err);
  assert.ok(all.err.includes('ci-browser-legs: ' + S.todoFail + ': \'a real failure inside a todo\' failed inside a todo (the leg is broken)') && all.err.includes('ci-browser-legs: ' + S.mixed + ': \'a swallowed failure\' failed inside a todo (the leg is broken)'), 'the composition reds the failure inside a todo by leg for the todo-fail and the mixed shapes:\n' + all.err);
  assert.ok(all.err.includes('skipped with ' + SWITCH + '=1: \'one skip\' # SKIP no browser # here (' + S.passSkip + ')'), 'the composition names the skip with its reason (a # inside it kept) and its leg:\n' + all.err);
  assert.ok(all.err.includes('ci-browser-legs: ' + S.lost + ': \'the launch\' failed under ' + SWITCH + '=1 because inBrowser could not launch (' + SWITCH + ' is set and this leg cannot run: no playwright browser on this box): the runner lost its browser: check the Chromium install step'), 'the composition prints the lost-browser remedy beside the leg whose failure names the switch:\n' + all.err);
  assert.ok(all.err.includes(S.describeNone + ': no test of this leg passed in this run (the record holds 0 skipped, 0 todo, 1 suite and 0 file-level results for it)') && all.err.includes(S.nothing + ': no test of this leg passed in this run (the record holds 0 skipped, 0 todo, 0 suite and 1 file-level results for it)'), 'the composition reds describe-none and nothing as unrun with what the record held (a suite result, a file-level result):\n' + all.err);
  const clean = run(S.describePass + '\n', { real: true });
  assert.equal(clean.status, 0, 'a leg whose test passes inside a describe(): green; stderr: ' + clean.err);
  assert.equal(clean.err, '', 'nothing on stderr');
});

test('the four cases the roster rule\'s homes name read green, executed: the script with the real node and the real reporter over one synthetic rostered leg of each (an own launch whose failure is swallowed, a module that launches nothing, a child process whose failure is tolerated, a todo that passes beside a real pass) exits 0 with nothing on stderr', (t) => {
  // witnesses of what the step cannot see, named at each home of the roster rule: a mechanism that closes one of the four turns
  // this red, and the homes' sentence moves with it. Each leg that stands for a failure writes a mark beside its bundle when the
  // failure happens, so the green below is read over a run in which the launch threw, the child failed and the todo ran
  const { run, root, ext } = syntheticTree(t);
  const head = 'const { test } = require("node:test"); const fs = require("node:fs"); const { spawnSync } = require("node:child_process");\n';
  const w = (name, body) => { fs.writeFileSync(path.join(root, 'vscode-extension', 'out-tests', 'ui', 'webview', name + '-browser.test.js'), head + body); fs.writeFileSync(path.join(root, 'ui', 'webview', name + '-browser.test.ts'), '// the synthetic source of a witness leg: its presence is what the script reads\n'); return 'out-tests/ui/webview/' + name + '-browser.test.js'; };
  const W = {
    ownLaunch: w('own-launch', 'test("opens a page", async () => { let browser = null; try { browser = await (async () => { throw new Error("browserType.launch: a synthetic launch that fails"); })(); } catch (e) { fs.writeFileSync(__filename + ".mark", String(e.message)); } if (!browser) return; });\n'),
    launchesNothing: w('launches-nothing', 'test("a source pin", () => { if ("a".length !== 1) throw new Error("unreachable"); });\n'),
    childTolerated: w('child-tolerated', 'test("drives a page from a child", () => { const r = spawnSync(process.execPath, ["-e", "process.exit(3)"]); if (r.status !== 0) fs.writeFileSync(__filename + ".mark", String(r.status)); });\n'),
    todoBeside: w('todo-beside', 'test("a real pass", () => {});\ntest("the browser part", { todo: "a synthetic todo" }, () => { fs.writeFileSync(__filename + ".mark", "ran"); });\n'),
  };
  const r = run(Object.values(W).join('\n') + '\n', { real: true });
  assert.equal(r.status, 0, 'the four cases read green (exit 0): a change that makes the step see one of them turns this red, and the four homes of the roster rule drop that case in the same change; stderr:\n' + r.err);
  assert.equal(r.err, '', 'nothing on stderr for the four cases (no red and no remedy line)');
  assert.deepEqual(r.node, ['--test', ...Object.values(W)], 'node --test ran the four witness legs');
  for (const [what, b] of [['the own launch threw', W.ownLaunch], ['the child exited 3', W.childTolerated], ['the todo body ran', W.todoBeside]]) assert.ok(fs.existsSync(path.join(ext, b + '.mark')), what + ' in this run (the mark beside ' + b + '), so the green above is read over the case, not over a leg that skipped it');
});

/** The executed test of the switch's behaviour, which the phrase pin below names and does not replace. */
const SWITCH_TEST = path.join(REPO, 'ui', 'webview', 'real-viewer-leg-switch.test.ts');

test('the phrase the script reads a lost browser by is a literal in inBrowser\'s source, the shared phrase between ui/webview/real-viewer-leg.ts and the script, so a reword on either side is red here rather than a remedy dropped in silence; the behaviour is executed by ui/webview/real-viewer-leg-switch.test.ts, which exists and drives inBrowser', () => {
  const script = read(SCRIPT);
  assert.match(script, /^SWITCH=ROMP_BROWSER_LEGS_REQUIRE$/m, 'the script names the switch once, as SWITCH');
  const m = /awk -v msg="([^"]+)"/.exec(script);
  assert.ok(m, 'the script hands awk the phrase it reads a failure block by (awk -v msg="...")');
  const phrase = m[1].replace(/\$SWITCH\b/g, SWITCH);
  assert.ok(phrase.startsWith(SWITCH + ' is set'), 'the phrase names the switch: ' + phrase);
  const helper = read(path.join(REPO, 'ui', 'webview', 'real-viewer-leg.ts'));
  assert.ok(helper.includes('"' + phrase + ': "'), 'the shared phrase: ui/webview/real-viewer-leg.ts holds the literal ' + JSON.stringify(phrase + ': ') + ' that vscode-extension/scripts/ci-browser-legs.sh hands awk (awk -v msg=), so a reword in one file is red here and the lost-browser remedy is never dropped in silence. This reads source text and guards the phrase alone, not the behaviour: that inBrowser FAILS with it under ' + SWITCH + ' and skips without is executed by ' + path.relative(REPO, SWITCH_TEST) + ' (a child node --test with PLAYWRIGHT_BROWSERS_PATH emptied), which the vscode-extension job runs; a green here with that test red is a helper that carries the words and not the behaviour');
  // the executed test this message points at exists and is rostered (so the step runs its leg with a browser on every CI
  // run, and the Test step runs its three child arms); what it asserts is its own to state, and the PR's reviewer holds it to
  // the roster rule. The helper's playwrightInstalled export has that test as its consumer (the reason the child names is
  // derived from the helper's own module read, never from a second one): presence pins, which say only that the file names these
  assert.ok(fs.existsSync(SWITCH_TEST), 'the executed test of the switch exists at ' + path.relative(REPO, SWITCH_TEST));
  assert.ok(read(SWITCH_TEST).includes('playwrightInstalled()'), path.relative(REPO, SWITCH_TEST) + ' consumes the helper\'s playwrightInstalled export (a presence pin: the export is not dead code in this tree)');
  assert.ok(parseRoster(read(path.join(EXT, ROSTER))).some((e) => e.bundle === 'out-tests/ui/webview/real-viewer-leg-switch.test.js'), path.relative(REPO, SWITCH_TEST) + ' is rostered in ' + ROSTER + ', so the step runs its leg with a browser on every CI run');
});
