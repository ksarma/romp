// The shared browser-legs CI step, held to the tree from CI's Shell job, which runs tools/*.test.mjs with no npm ci. The
// gating vscode-extension job runs npm test before it installs a browser, so every browser leg skips at launch there; the
// step "Browser legs (node --test over ci-browser-legs.txt)" runs the legs named in vscode-extension/ci-browser-legs.txt
// after the job's Chromium install with ROMP_BROWSER_LEGS_REQUIRE=1: the one shared launcher, inBrowser in
// ui/webview/real-viewer-leg.ts, reads the switch (any non-empty value arms it) and under it a leg that cannot launch fails
// naming the switch and the reason instead of skipping.
// WHICH GATE HOLDS WHICH. The census (what a browser leg IS) lives in vscode-extension/scripts/browser-legs-census.mjs and
// reads each test module's tree with the TypeScript compiler, which is installed only under vscode-extension/node_modules.
// So the completeness property, the roster PLUS vscode-extension/ci-browser-legs-excluded.txt EQUALS the browser legs of the
// extension's test build (what esbuild.js testBuild bundles; the census test holds its directory list equal to that build)
// with every roster line passing the roster gate and every reason's engine and driver words true of its source, is EXECUTED
// in ui/webview/ci-browser-legs-census.test.ts, in the vscode-extension job's test leg (npm test), and by the script's own
// pre-run check in that job; this module cannot run the census and does not claim it. A green here is the parse-free half:
//   - the step exists once in that job, directly after the Chromium install step (by step NAMES), with the switch and
//     the run line, in the job's default working directory, and no step before the Test step installs or caches
//     Playwright (the property plans/markdown-viewer.md's CI sentence states and tools/markdown-viewer-plan-gate-adopt.test.mjs
//     pins, restated here so the two pins cannot disagree);
//   - the step carries a timeout-minutes of its own that fits the margin under the job's cap at the measured head (the job's
//     comment derives it and names the same number), and the script passes node a --test-timeout above the largest own
//     { timeout } a rostered leg passes and under the step's bound, so a hung leg fails by name before the step is cut;
//   - the vscode-extension job runs on every pull request: the workflow's pull_request trigger has no paths or paths-ignore
//     filter and the job has no job-level if:, so the census test there gates every PR that could add a browser leg (the
//     equality holds in that one job after the split, and this is the derivation that it is enough);
//   - both files are well formed: every line is a bundle path (out-tests/<dir>/<name>.test.js), no line is duplicated, no
//     line is in both files, every line names a source that exists in the tree, every exclusions line carries a reason
//     with no em dash, and every reason is exactly one of four closed forms (the grandfather sentence the header quotes,
//     whole and exact; an engine reason, "launches <Firefox|WebKit|Firefox and WebKit>; the gating job installs Chromium
//     only", a tail after the phrase allowed; the embedded-driver sentence the header quotes, whole and exact; a pending
//     line), a reason of no form refused by name and one that reads as a form while carrying another form's phrase, or an
//     engine reason whose tail names a second engine, refused as ambiguous (whether the source reaches the engine named, is
//     an embedded driver, or names a browser leg at all, is the census test's to say); an exclusions reason "pending #<PR>:
//     <why>" (a leg an open PR brings) names a PR and its source is ABSENT from the tree: a present source is red here as
//     arrived, and the promotion remedy derived from that source (a roster line, the engine form, the embedded-driver
//     sentence, the gate's own remedy for a Chromium-only leg that misses it, or no line) is the census test's and the
//     script's to print; the header
//     binds the grandfather reason to one commit in one line and whether each grandfather row's source existed at that
//     commit is the census test's history read (this job's checkout is depth 1 and fetches nothing);
//   - the script the step calls (vscode-extension/scripts/ci-browser-legs.sh) exists, is executable, calls the census
//     module once (--tsv) and node --test over the roster array (no xargs, so node's status is the step's on every platform)
//     with the reporter scripts/ci-browser-legs-reporter.mjs beside the spec reporter, and prints "no legs in the roster" on
//     an empty roster; run on synthetic trees with a stub node on PATH
//     that answers the census call from a TABLE this module writes (so what is executed here is the script's READING of a
//     census, never the census), it refuses a stale line, a leg in neither file, a leg in both, a line without a reason, a
//     duplicate, a line naming no leg, a missing bundle, a malformed line or a line without a reason (the LINE shown with its
//     whitespace visible, and the leg it names, its first word after leading whitespace, attributed to it and never called
//     missing from both files: eight shapes, a tab before a pasted reason on a roster line, a leading tab, spaces then a
//     tab, a trailing space, a carriage return, a blank reason among them), a roster line whose census row carries a gap or
//     an engine, naming the line, the census's
//     sentence and the remedy; stops, judging nothing, when the census exits 1 (no compiler) or 2 (a refusal, whose lines
//     it prints); and after node --test reads the reporter's record (the stub writes a record this module hands it) and
//     derives, per rostered leg, that at least one result attributed to it is a pass with no skip or todo, a test and not a
//     suite, and not node's file-level result, red naming the leg otherwise (todo-only, a describe() that registers none,
//     a file that registered nothing, a failure inside a todo); turns a skipped test into a red naming the test, its reason
//     and the switch's state in the run (set to 1 as the step has it, or unset as a local run may); reds a failure inside a
//     todo and a file that failed as a whole (timed out, or threw at load) by name; prints the lost-browser remedy beside a
//     leg whose failure names the switch; and passes node's own failure status through. The reporter itself is executed
//     here over synthetic bundles with a real node --test (the shapes above, and a name holding a tab and a newline), and so
//     is the composition: the script with the real node and the real reporter over those shapes as rostered legs;
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
const EXCLUDED = 'ci-browser-legs-excluded.txt';
const SCRIPT = path.join(EXT, 'scripts', 'ci-browser-legs.sh');
const REPORTER = path.join(EXT, 'scripts', 'ci-browser-legs-reporter.mjs');
const CENSUS = path.join(EXT, 'scripts', 'browser-legs-census.mjs');
const CENSUS_TEST = path.join(REPO, 'ui', 'webview', 'ci-browser-legs-census.test.ts');
/** The census's home, named in every message here that stops where the parse begins. */
const CENSUS_HOME = 'the census (what a browser leg is, whether a line names one, the roster gate and the engines) is executed by ' + path.relative(REPO, CENSUS_TEST) + ' in the vscode-extension job, not here';
const STEP = 'Browser legs (node --test over ci-browser-legs.txt)';
const INSTALL = 'Install the pinned Playwright Chromium';
const TEST_STEP = 'Test';
const JOB = 'vscode-extension';
const SWITCH = 'ROMP_BROWSER_LEGS_REQUIRE';
const RUN_LINE = 'bash scripts/ci-browser-legs.sh';
/** The phrase an engine reason carries (the census module exports the same as ENGINE_PHRASE and the census test reads it there;
 *  this module runs without node_modules and reads the parse-free half, so it spells the phrase for its own message). */
const ENGINE_PHRASE = 'the gating job installs Chromium only';
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
  assert.ok(comment.includes(ROSTER) && comment.includes(EXCLUDED), 'the comment names both files');
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
  assert.match(install.fields.run || '', /^npx playwright install chromium$/, 'the install step installs Chromium alone (the exclusions\' engine reasons rest on this)');
});

// ── the roster, the exclusions and the tree ───────────────────────────────────────────────────────────

const WELL_FORMED = /^out-tests\/\S+\.test\.js$/;
const sourceOf = (bundle) => path.join(REPO, bundle.replace(/^out-tests\//, '').replace(/\.test\.js$/, '.test.ts'));
/** Roster lines: [{ n, bundle }], comments and blanks dropped. */
function parseRoster(text) {
  return text.split('\n').map((line, i) => ({ n: i + 1, line })).filter(({ line }) => !/^\s*(#|$)/.test(line)).map(({ n, line }) => ({ n, bundle: line }));
}
/** Exclusions lines: [{ n, bundle, reason, pending }] (reason null when the line has no tab; `pending` is undefined for an
 *  ordinary reason, { pr: '<PR>' } for a reason of the class "pending #<PR>: <why>", and { pr: null } for a reason that starts
 *  with "pending" and names no PR). */
function parseExcluded(text) {
  return text.split('\n').map((line, i) => ({ n: i + 1, line })).filter(({ line }) => !/^\s*(#|$)/.test(line)).map(({ n, line }) => {
    const tab = line.indexOf('\t');
    const e = tab < 0 ? { n, bundle: line, reason: null } : { n, bundle: line.slice(0, tab), reason: line.slice(tab + 1) };
    if (e.reason !== null && /^\s*pending/.test(e.reason)) { const m = /^\s*pending #(\d+): \S/.exec(e.reason); e.pending = { pr: m ? m[1] : null }; }
    return e;
  });
}
/** A row's place, for every red that names one: "<file> line <n> (<bundle>)". Module scope: the closed-set loop below reads it too
 *  (a first copy scoped inside one test made that loop die with a ReferenceError on its first refused row instead of naming it). */
const where = (file, e) => file + ' line ' + e.n + ' (' + e.bundle + ')';

test('the vscode-extension job runs on every pull request (no paths filter on the trigger, no job-level if:), so the census test there gates every PR that could add a browser leg', () => {
  const text = read(CI);
  const lines = text.split('\n');
  const on = lines.findIndex((l) => /^on:\s*$/.test(l));
  assert.ok(on >= 0, 'ci.yml has an on: block');
  let end = on + 1;
  while (end < lines.length && !/^\S/.test(lines[end])) end++;
  const trigger = lines.slice(on + 1, end);
  const pr = trigger.findIndex((l) => /^  pull_request:/.test(l));
  assert.ok(pr >= 0, 'the workflow triggers on pull_request; the on: block: ' + JSON.stringify(trigger));
  let prEnd = pr + 1;
  while (prEnd < trigger.length && /^    /.test(trigger[prEnd])) prEnd++;
  const prBlock = trigger.slice(pr, prEnd).filter((l) => !/^\s*#/.test(l));
  assert.ok(!prBlock.some((l) => /^\s+paths(-ignore)?:/.test(l)), 'the pull_request trigger has no paths or paths-ignore filter, so a PR adding a browser leg anywhere runs the workflow; ' + CENSUS_HOME + '; the block: ' + JSON.stringify(prBlock));
  const job = extensionJob();
  assert.ok(!job.lines.some((l) => /^    if:/.test(l)), 'the ' + JOB + ' job has no job-level if:, so it runs whenever the workflow does; ' + CENSUS_HOME);
  assert.ok(fs.existsSync(CENSUS_TEST), 'the census test this module points at exists: ' + path.relative(REPO, CENSUS_TEST));
  assert.ok(fs.existsSync(CENSUS), 'the census module exists: ' + path.relative(REPO, CENSUS));
});

test('both files are well formed: each line is a bundle path naming a source in the tree, once, in one file, and every exclusions line carries a reason with no em dash; a pending line names a PR and its source is absent (whether a line names a browser leg, the equality with the tree, and the promotion remedy for an arrived pending leg are the census test\'s in the vscode-extension job; the reason\'s form is the closed-set test\'s below)', () => {
  const roster = parseRoster(read(path.join(EXT, ROSTER)));
  const excluded = parseExcluded(read(path.join(EXT, EXCLUDED)));
  assert.ok(excluded.length + roster.length > 100, 'the two files hold the tree\'s browser legs (' + (excluded.length + roster.length) + ' lines; a count near zero means the files emptied, not that the legs left); ' + CENSUS_HOME);
  for (const [file, entries] of [[ROSTER, roster], [EXCLUDED, excluded]]) {
    const seen = new Map();
    for (const e of entries) {
      assert.match(e.bundle, WELL_FORMED, file + ' line ' + e.n + ' (' + JSON.stringify(e.bundle) + '): a line is a bundle path, out-tests/<dir>/<name>.test.js (a trailing space, tab or carriage return counts; the quoting shows it)');
      assert.ok(!seen.has(e.bundle), where(file, e) + ' duplicates line ' + seen.get(e.bundle) + ': remove one');
      seen.set(e.bundle, e.n);
      const src = sourceOf(e.bundle);
      if (e.pending) {   // a leg an open PR brings: the reason names the PR, and the line stands only while the source is absent
        assert.ok(e.pending.pr !== null, where(file, e) + ' has a pending reason that names no PR (' + JSON.stringify(e.reason) + '): a pending line reads \'pending #<PR>: <why>\', the PR whose merge of main brings the leg and promotes the line');
        assert.ok(!fs.existsSync(src), where(file, e) + ' is pending #' + e.pending.pr + ' and its source ' + path.relative(REPO, src) + ' is in the tree, so the leg has arrived (#' + e.pending.pr + ' merged main, or this is #' + e.pending.pr + '\'s branch) and the line\'s condition has passed: promote it (a roster line, the engine form, the embedded-driver sentence, the gate\'s own remedy for a Chromium-only leg that misses it, or no line: the remedy derived from the source is printed by ' + path.relative(REPO, CENSUS_TEST) + ' in the vscode-extension job and by scripts/ci-browser-legs.sh --check)');
        continue;
      }
      assert.ok(fs.existsSync(src), where(file, e) + ' names ' + path.relative(REPO, src) + ', which is not in the tree (the source moved or was deleted): fix the line');
    }
  }
  for (const e of excluded) {
    assert.ok(e.reason !== null && e.reason.trim() !== '', where(EXCLUDED, e) + ' has no reason: write the bundle path, a tab, and why the gating job does not run it');
    assert.ok(!e.reason.includes(String.fromCharCode(0x2014)), where(EXCLUDED, e) + ': no em dash');
  }
  const rostered = new Set(roster.map((e) => e.bundle));
  for (const e of excluded) assert.ok(!rostered.has(e.bundle), where(EXCLUDED, e) + ' is also in ' + ROSTER + ': a leg is in one file or the other, keep one');
});

test('the completeness sentence is scoped to the extension\'s test build on every reader surface (the roster header, the exclusions header, the step\'s comment in ci.yml, CONTRIBUTING.md, the census test\'s header), and none of them copies the census\'s directory list, which has one home, the census header, held equal to esbuild.js testBuild by the census test in the vscode-extension job', () => {
  const PHRASE = 'browser leg of the extension\'s test build';
  const LIST = 'vscode-extension/src, ui or ui/webview';
  const surfaces = [path.join(EXT, ROSTER), path.join(EXT, EXCLUDED), CI, path.join(REPO, 'CONTRIBUTING.md'), CENSUS_TEST];
  for (const f of surfaces) {
    const text = read(f);
    assert.ok(text.includes(PHRASE), path.relative(REPO, f) + ' states the completeness bound over the extension\'s test build (the phrase ' + JSON.stringify(PHRASE) + '), not over the whole repository, whose other browser legs carry their own switches');
    assert.ok(!text.includes(LIST), path.relative(REPO, f) + ' copies the census\'s directory list (' + LIST + '); the list has one home, the header of ' + path.relative(REPO, CENSUS) + ', and the census test holds it equal to esbuild.js testBuild by execution, so a copy here would be a second thing to drift');
  }
  assert.ok(read(CENSUS).includes(LIST), path.relative(REPO, CENSUS) + ' spells the directory list in its header (the one home): ' + LIST);
  assert.ok(read(CENSUS_TEST).includes('metafile'), path.relative(REPO, CENSUS_TEST) + ' holds the list to esbuild\'s test build by a metafile build (a presence pin: the executed equality lives there, in the vscode-extension job, which has esbuild)');
  // the roster header states the gate's own clause for a driver string in the words the census's gap sentence uses. The clause is
  // READ from the census module (the sentence rosterGap returns for a driver string, "drives <clause> (line N), which the switch
  // never reaches", the same clause in each of its arms) and the roster header is held to it, so the two homes are one phrase by
  // execution, as the lost-browser phrase is held between the helper and the script below: a reword in either home is red here.
  // The gloss after the clause in the roster, "(the gate reads the string, not a spawn)", is the roster's own and is read as text.
  const gapArms = [...read(CENSUS).matchAll(/return "drives ([^"]+) \(line " \+ r\.embedded\[0\]\.line \+ "\), which the switch never reaches";/g)].map((m) => m[1]);
  assert.ok(gapArms.length > 0 && gapArms.every((c) => c === gapArms[0]), path.relative(REPO, CENSUS) + '\'s rosterGap returns the driver-string gap as "drives <clause> (line N), which the switch never reaches", the same clause in every arm (the clause the roster header is held to is read from here, so an empty read means the sentence moved, not that the clause is free). Holds the sentence frame in the module, "drives <clause> (line N), which the switch never reaches": a reword of the frame moves this pin too; the clause inside it is free here and held to the roster by the next assertion: ' + JSON.stringify(gapArms));
  const rosterHeader = read(path.join(EXT, ROSTER)).split('\n').filter((l) => l.startsWith('#')).map((l) => l.replace(/^# ?/, '')).join(' ');
  assert.ok(rosterHeader.includes('does not drive ' + gapArms[0] + ', which the switch never reaches (the gate reads the string, not a spawn)'), ROSTER + '\'s header states the gate\'s own clause for a driver string in the census\'s words: a leg does not drive ' + gapArms[0] + ', which the switch never reaches (the gate reads the string, not a spawn). One phrase, two homes (' + path.relative(REPO, CENSUS) + '\'s gap sentence and this header), held equal here, so a reword in either is red rather than the two drifting apart; the gloss in parentheses is the roster\'s own words, read as text. Holds the property for the clause (a reword of the clause in both homes stays green) and the sentence for the roster\'s frame and gloss, "does not drive <clause>, which the switch never reaches (the gate reads the string, not a spawn)": a reword of those moves this pin too');
});

test('the grep the exclusions header spells for the pending lines lists exactly the pending rows when run as written from the repo root, and CONTRIBUTING.md spells the same command (residual 1 of the landing condition: a pending line whose PR closes without the leg is found by this command and removed by hand)', () => {
  const text = read(path.join(EXT, EXCLUDED));
  const header = text.split('\n').filter((l) => l.startsWith('#')).join('\n');
  const m = /`(grep [^`]*pending #[^`]*)`/.exec(header);
  assert.ok(m, 'the exclusions header spells, in backticks, a grep for the pending lines');
  const r = spawnSync('bash', ['-c', m[1]], { cwd: REPO, encoding: 'utf8' });
  assert.equal(r.status, 0, 'the command runs from the repo root and finds the rows: ' + r.stderr);
  const rows = parseExcluded(text).filter((e) => e.pending).map((e) => e.bundle + '\t' + e.reason);
  assert.ok(rows.length > 0, 'the exclusions hold pending rows (' + rows.length + '); with none this pin proves nothing');
  assert.deepEqual(r.stdout.split('\n').filter(Boolean), rows, 'the command lists the pending rows and no other line (the header spells the form "pending #<PR>: <why>" twice, which a grep for the bare prefix would list too)');
  assert.ok(read(path.join(REPO, 'CONTRIBUTING.md')).includes('`' + m[1] + '`'), 'CONTRIBUTING.md spells the same command as the header: ' + m[1]);
  // the header records HOW the pending rows were derived (the claim that they were derived, not recalled; the date and time of the
  // read; the command that listed the open PRs, in backticks), and CONTRIBUTING.md makes the same claim and spells the same
  // command, held equal by execution: the command is read from the header and looked for in CONTRIBUTING.md, never spelled here.
  // The header wraps the command onto its own # line and CONTRIBUTING.md wraps its prose, so both are read with their line breaks
  // folded to one space.
  const joined = header.split('\n').map((l) => l.replace(/^# ?/, '')).join(' ');
  const derived = /were DERIVED, not recalled: on (\d{4}-\d{2}-\d{2}) at (\d{2}:\d{2}Z) the fork's open PRs were listed with `([^`]+)`/.exec(joined);
  assert.ok(derived && /pulls\?state=open/.test(derived[3]), 'the exclusions header records how the pending rows were derived: the claim "were DERIVED, not recalled", the date and time of the read ("on <date> at <hh:mm>Z") and, in backticks, the command that listed the open PRs (pulls?state=open); a header that says the rows were recalled, or lost the time or the command, is red (holds the sentence: a reword of the derivation sentence moves this pin too); the header reads: ' + joined.slice(Math.max(0, joined.indexOf('The pending rows at the roster')), Math.max(0, joined.indexOf('The pending rows at the roster')) + 240));
  const contributing = read(path.join(REPO, 'CONTRIBUTING.md')).replace(/\s+/g, ' ');
  assert.ok(contributing.includes('were derived, not recalled') && contributing.includes('`' + derived[3] + '`'), 'CONTRIBUTING.md makes the same claim (were derived, not recalled) and spells, in backticks, the same listing command as the header: ' + derived[3] + ' (holds the property for the command, one command in two homes: a change in both stays green; holds the sentence for the claim "were derived, not recalled" in CONTRIBUTING.md: a reword of it moves this pin too)');
  // and both surfaces state the coupling: a pending row alone does not clear a PR whose module the census refuses, since the census
  // refuses before the equality runs. The sentence is read from the header and looked for in CONTRIBUTING.md: one sentence, two homes.
  const coupling = /A pending row alone does not clear a PR whose module the census refuses[^.]*\./.exec(joined);
  assert.ok(coupling, EXCLUDED + '\'s header states the coupling sentence, "A pending row alone does not clear a PR whose module the census refuses: ...": a pending row is a promise about an absent source, and the census refuses before the equality runs, so a refused module stays red whatever row names it; the sentence is gone or reversed (holds the sentence\'s opening words, "A pending row alone does not clear a PR whose module the census refuses": a reword of them moves this pin too; the rest of the sentence, to its period, is read here and held to CONTRIBUTING.md by the next assertion)');
  assert.ok(contributing.includes(coupling[0]), 'CONTRIBUTING.md states the same coupling sentence as the header (one sentence, two homes, held equal here; gone or reversed there; holds the property for the sentence\'s tail after the opening words: a reword of the tail in both homes stays green): ' + coupling[0]);
});

/** An exclusions reason is exactly one of four closed forms, or refused by name (the census test holds the same rule, in the
 *  vscode-extension job, and drives the source-side verdicts the form leads to): grandfather (the header's bound sentence, whole
 *  and exact); engine ("launches <Firefox|WebKit|Firefox and WebKit>; " then the engine phrase, a tail after it allowed); embedded
 *  (the header's embedded-driver sentence, whole and exact); pending ("pending #<PR>: <why>"). A reason matching none is refused
 *  (there is no reason of its own, so a misspelt exemption cannot pass as one); one that reads as a form while its text carries
 *  another form's phrase, or an engine reason whose tail names a second engine, is refused as AMBIGUOUS, so a tail cannot carry
 *  a second claim. */
const ENGINE_FORM = /^launches (Firefox|WebKit|Firefox and WebKit); /;
function reasonKind(reason, sentence, enginePhrase, embeddedSentence) {
  const head = ENGINE_FORM.exec(reason);
  const forms = [['grandfather', reason === sentence], ['engine', head !== null && reason.slice(head[0].length).startsWith(enginePhrase)], ['embedded', reason === embeddedSentence], ['pending', /^pending #\d+: \S/.test(reason)]];
  const phrases = [['grandfather', reason.includes(sentence)], ['engine', reason.includes(enginePhrase) || /\blaunches (Firefox|WebKit)\b/.test(reason)], ['embedded', reason.includes(embeddedSentence)], ['pending', /\bpending #\d+: /.test(reason)]];
  const matched = forms.filter(([, ok]) => ok).map(([k]) => k);
  const carried = phrases.filter(([k, ok]) => ok && k !== matched[0]).map(([k]) => k);
  const FORMS = 'the four forms the header of ' + EXCLUDED + ' defines (the grandfather sentence as quoted there, whole and exact; \'launches <Firefox|WebKit|Firefox and WebKit>; ' + enginePhrase + '\', a tail after the phrase allowed; the embedded-driver sentence, whole and exact; \'pending #<PR>: <why>\')';
  if (matched.length === 0) return { kind: null, refusal: 'the reason is none of ' + FORMS + '; a reason of its own is not admitted, so a misspelt exemption cannot pass as one' };
  if (matched.length > 1 || carried.length) return { kind: null, refusal: 'the reason is AMBIGUOUS: it reads as the ' + matched.join(' and the ') + ' form and its text also carries the ' + [...matched.slice(1), ...carried].join(' and the ') + ' form\'s phrase; a reason is exactly one of ' + FORMS };
  if (matched[0] === 'engine') {
    // the engines a reason claims have one home, the form's head (the census test reads them there against the source): a tail naming another engine is a second claim
    const second = /\b(Firefox|WebKit)\b/.exec(reason.slice(head[0].length + enginePhrase.length));
    if (second) return { kind: null, refusal: 'the reason is AMBIGUOUS: it reads as the engine form and its tail, after the phrase, names an engine (' + second[1] + '); the engines a reason claims have one home, the form\'s head, so a tail cannot carry a second engine; a reason is exactly one of ' + FORMS };
  }
  return { kind: matched[0], engines: matched[0] === 'engine' ? head[1].split(' and ') : [] };
}
/** The rows of an exclusions file text whose reason is none of the four forms, or ambiguous, each with the sentence the red
 *  carries (the row's place, the refusal, the reason as it reads): one writer for the loop over the real file and for the
 *  synthetic text that drives it below. */
function refusedRows(text, sentence, enginePhrase, embedded) {
  return parseExcluded(text).filter((e) => e.reason !== null).map((e) => ({ e, v: reasonKind(e.reason, sentence, enginePhrase, embedded) })).filter(({ v }) => v.kind === null).map(({ e, v }) => where(EXCLUDED, e) + ': ' + v.refusal + '; the reason reads: ' + e.reason);
}

/** The exclusions header's one bound line: the grandfather sentence and the commit it is bound to, and the embedded-driver
 *  sentence the header quotes after "carries the sentence" (the census module exports the same as EMBEDDED_PHRASE; the census
 *  test holds the two equal, and this module, which cannot load that module's compiler, reads the header's). */
const BOUND_LINE = /^# Every grandfather reason, "([^"]+)", is bound to commit ([0-9a-f]{40}):/;
function grandfatherBound(text) {
  const lines = text.split('\n').filter((l) => l.startsWith('#'));
  const hits = lines.map((l) => BOUND_LINE.exec(l)).filter(Boolean);
  assert.equal(hits.length, 1, EXCLUDED + '\'s header holds exactly one line binding the grandfather reason to a commit (the form: # Every grandfather reason, "<sentence>", is bound to commit <40 hex>: ...; that line is the bound\'s one home, the census test reads it); found ' + hits.length);
  const em = /carries the sentence "([^"]+)"/.exec(lines.map((l) => l.replace(/^# ?/, '')).join(' '));
  assert.ok(em, EXCLUDED + '\'s header quotes the embedded-driver sentence after "carries the sentence"');
  return { sentence: hits[0][1], sha: hits[0][2], embedded: em[1] };
}

test('the exclusions header binds the grandfather reason to one commit, in one line the checkers read, and every reason in the file is exactly one of the four closed forms (the grandfather sentence as quoted, an engine reason with the phrase, the embedded-driver sentence, a pending line): every variant of the exemption is refused by name, a reason carrying two forms\' phrases or an engine tail naming a second engine is refused as ambiguous, and the loop over a file names a refused row by its line (executed over a synthetic text); whether each grandfather row\'s source existed at that commit is read from history by the census test in the vscode-extension job, not here (CI\'s Shell job checks out at depth 1 and fetches nothing, so this module cannot read that commit)', () => {
  const text = read(path.join(EXT, EXCLUDED));
  const { sentence, sha, embedded } = grandfatherBound(text);
  assert.ok(sentence.length > 20, 'the bound line quotes the grandfather sentence: ' + JSON.stringify(sentence));
  assert.ok(embedded.length > 20, 'the header quotes the embedded-driver sentence: ' + JSON.stringify(embedded));
  const refused = refusedRows(text, sentence, ENGINE_PHRASE, embedded);
  assert.deepEqual(refused, [], 'every reason is one of the four forms; the rows refused, each named by line with the four forms and the remedy: ' + refused.join(' || ') + '; ' + CENSUS_HOME);
  const kinds = parseExcluded(text).filter((e) => e.reason !== null).map((e) => ({ e, v: reasonKind(e.reason, sentence, ENGINE_PHRASE, embedded) }));
  const rows = kinds.filter(({ v }) => v.kind === 'grandfather');
  // the loop over a file, executed against what it refuses: a synthetic text of one misspelt row between two admitted rows names the
  // misspelt row by its line and bundle with the four forms (the real file above is refused by the same function)
  const synthetic = '# header\nout-tests/ui/webview/zz-a.test.js\t' + sentence + '\nout-tests/ui/webview/zz-b.test.js\t' + sentence.replace('before', 'befora') + '\nout-tests/ui/webview/zz-c.test.js\tlaunches Firefox; ' + ENGINE_PHRASE + '\n';
  const one = refusedRows(synthetic, sentence, ENGINE_PHRASE, embedded);
  assert.equal(one.length, 1, 'one row refused of three: ' + JSON.stringify(one));
  assert.ok(one[0].startsWith(EXCLUDED + ' line 3 (out-tests/ui/webview/zz-b.test.js): the reason is none of the four forms') && one[0].includes('the reason reads: existing befora'), 'the refused row is named by its line and bundle, with the four forms and the reason as it reads: ' + one[0]);
  assert.ok(rows.length > 0, 'the exclusions hold grandfather rows (' + rows.length + '); zero means the wording stopped matching, not that the rows left');
  assert.ok(text.includes('does not run that history read'), 'the header says which checker reads history and which does not');
  assert.ok(text.includes('Both read a reason\n# as one of four forms'), 'the header says both checkers read a reason as one of four forms');
  assert.ok(text.includes('is refused as ambiguous, so a tail cannot carry a second claim'), 'the header says a reason carrying another form\'s phrase is refused as ambiguous');
  assert.ok(text.split('\n').find((l) => BOUND_LINE.test(l)).includes("reads the file's age, not what it did there"), 'the bound line names its residual: it reads the file\'s age at the commit, not whether the file launched a browser there');
  // the property, executed over synthetic reasons: each form admitted with its kind; every variant of the exemption refused by
  // name; a reason carrying two forms' phrases refused as ambiguous
  const k = (reason) => reasonKind(reason, sentence, ENGINE_PHRASE, embedded);
  assert.deepEqual(k(sentence), { kind: 'grandfather', engines: [] }, 'the sentence as quoted, whole and exact');
  assert.deepEqual(k('launches Firefox and WebKit; ' + ENGINE_PHRASE + '; a locator after the phrase'), { kind: 'engine', engines: ['Firefox', 'WebKit'] }, 'an engine reason, a tail allowed');
  assert.deepEqual(k(embedded), { kind: 'embedded', engines: [] });
  assert.deepEqual(k('pending #862: launches through inBrowser'), { kind: 'pending', engines: [] });
  for (const [what, reason] of [['a capital letter', 'Existing before the roster, unmeasured in the gating job; its owner moves it to the roster with measured numbers'], ['a comma for a semicolon', 'existing before the roster; unmeasured in the gating job, its owner moves it to the roster with measured numbers'], ['doubled and tabbed spacing', 'existing  before the\troster, unmeasured in the gating job; its owner moves it to the roster with measured numbers'], ['the word grandfather', 'the grandfather clause'], ['befora', sentence.replace('before', 'befora')], ['rostar', sentence.replace('the roster,', 'the rostar,')], ['rosters', sentence.replace('the roster,', 'the rosters,')], ['befor', sentence.replace('before', 'befor')], ['grandfathered', 'grandfathered: measured later'], ['predates the roster', 'predates the roster; measured later'], ['an engine without the phrase', 'launches Firefox'], ['a reason of its own', 'launches on its own']]) {
    const v = k(reason);
    assert.equal(v.kind, null, what + ' is refused: ' + JSON.stringify(reason));
    assert.ok(v.refusal.startsWith('the reason is none of the four forms'), what + ': the refusal names the four forms: ' + v.refusal);
  }
  for (const [what, reason] of [['an engine tail carrying the grandfather sentence', 'launches Firefox; ' + ENGINE_PHRASE + '; ' + sentence], ['a pending line naming an engine', 'pending #859: launches Firefox at its merge'], ['a pending line carrying the embedded-driver sentence', 'pending #864: ' + embedded], ['an engine tail naming a second engine', 'launches Firefox; ' + ENGINE_PHRASE + '; also WebKit'], ['an engine tail naming the same engine again', 'launches WebKit; ' + ENGINE_PHRASE + '; WebKit in the pane\'s own scene']]) {
    const v = k(reason);
    assert.equal(v.kind, null, what + ' is refused: ' + JSON.stringify(reason));
    assert.ok(v.refusal.startsWith('the reason is AMBIGUOUS'), what + ': refused as ambiguous: ' + v.refusal);
  }
  // the history read itself (git cat-file -e <sha>:<source> for each row, after a depth-1 fetch when the clone lacks the commit)
  // is ' + path.relative(REPO, CENSUS_TEST) + '\'s: this module states it does not run it, so a green here is the header\'s shape alone
  assert.ok(read(CENSUS_TEST).includes('is bound to commit'), path.relative(REPO, CENSUS_TEST) + ' reads the bound line (a presence pin: the executed check lives there, in the vscode-extension job, and this module does not run it because the Shell job\'s depth-1 checkout lacks commit ' + sha + ' and fetches nothing)');
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

test('the CI-only files under vscode-extension/ (the roster, the exclusions, the script, the census module and the reporter) are named by .vscodeignore, so vsce ships none of them in the extension people install', () => {
  const patterns = read(path.join(EXT, '.vscodeignore')).split('\n').map((l) => l.trim()).filter((l) => l && !l.startsWith('#'));
  for (const rel of [ROSTER, EXCLUDED, path.relative(EXT, SCRIPT), path.relative(EXT, CENSUS), path.relative(EXT, REPORTER)]) {
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
  for (const rel of [ROSTER, EXCLUDED, path.relative(EXT, SCRIPT), path.relative(EXT, CENSUS), path.relative(EXT, REPORTER), 'package.json', 'dist/extension.js']) {
    assert.equal(vscodeignored(patterns, rel), fnmatched(patterns, rel), rel + ': the two readers of .vscodeignore part on this path (minimatch, vsce\'s: ' + vscodeignored(patterns, rel) + '; fnmatch, tests/test_lab_dist.py\'s: ' + fnmatched(patterns, rel) + '), so a pattern in the file leans on a single * across a /: write it so both readers agree, or re-derive this pin and the Python one together: ' + JSON.stringify(patterns));
  }
});

// ── the script ────────────────────────────────────────────────────────────────────────────────────────

function bash(args, opts = {}) {
  const r = spawnSync('bash', args, { encoding: 'utf8', ...opts });
  assert.equal(r.error, undefined, 'bash runs: ' + (r.error && r.error.message));
  return r;
}

test('the script exists, is executable, calls the census module once and node --test over the roster array (no xargs) with the reporter beside the spec reporter, and spells the empty-roster guard (each executed below through the stub)', () => {
  assert.ok(fs.existsSync(SCRIPT), 'the step\'s script exists at ' + path.relative(REPO, SCRIPT));
  assert.ok(fs.statSync(SCRIPT).mode & 0o111, 'the script is executable');
  assert.ok(fs.existsSync(REPORTER), 'the reporter the script passes to node --test exists at ' + path.relative(REPO, REPORTER));
  const src = read(SCRIPT);
  assert.match(src, /^REPORTER=\.\/scripts\/ci-browser-legs-reporter\.mjs$/m, 'the script names the reporter once, as REPORTER, by a path node resolves from vscode-extension/');
  assert.equal((src.match(/--test-reporter="\$REPORTER" --test-reporter-destination="\$rep"/g) || []).length, 1, 'node --test is handed the reporter with a destination file the script reads after the run (executed below)');
  assert.match(src, /^CENSUS=scripts\/browser-legs-census\.mjs$/m, 'the script names the census module once, as CENSUS');
  assert.equal((src.match(/node "\$CENSUS" --tsv/g) || []).length, 1, 'the census is run once, as node "$CENSUS" --tsv (the stub below answers that call; the script\'s --list-legs against the real census is compared in ' + path.relative(REPO, CENSUS_TEST) + ')');
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
  assert.ok(scriptHeader.includes('derives, per rostered leg, that A TEST OF ITS BUNDLE PASSED') && scriptHeader.includes('That is the whole of what the record can prove: node\'s events carry no launch'), 'the script header states the post-run property as A TEST OF ITS BUNDLE PASSED and its boundary, "That is the whole of what the record can prove: node\'s events carry no launch" (a text pin on the header\'s prose: it guards that the header states what the record proves and its boundary, so the property is not read as a launch record; the derivation is executed below; holds the sentence: a reword of the header\'s two phrases moves this pin too)');
});

/** A synthetic tree: the script under vscode-extension/scripts; under ui/webview five browser legs and one plain test module
 *  as SOURCES (a and b launch through inBrowser (a has a bundle, b none; a's second test has a newline and a # in its name,
 *  spelled \n and # in the source as node's record escapes them), p launches through its own playwright copy with a bundle,
 *  m calls inBrowser but keeps its own playwright beside it, k calls inBrowser but keeps a skip of its own before it, f
 *  launches through inBrowser but reaches Firefox, each with a bundle); and a stub node on PATH that answers the script's
 *  census call (node scripts/browser-legs-census.mjs --tsv) with the TABLE below, CBL_STUB_CENSUS (bundle TAB 1|0 TAB gap
 *  TAB engines TAB class, the module's --tsv shape; the sentences are the module's shapes, as values of this table), exiting
 *  CBL_STUB_CENSUS_EXIT with CBL_STUB_CENSUS_ERR on stderr when set; for any other call it records its arguments and then either
 *  runs the REAL node over them (CBL_STUB_REAL_NODE names it: the composition of the script, node and the real reporter) or
 *  writes CBL_STUB_REPORT (when set) to the reporter's destination and exits CBL_STUB_EXIT (0 unless set). The sources' text
 *  decides nothing here: what runs is the script's reading of the table (the census over real sources is executed by the census
 *  test in the vscode-extension job). Returns a runner over roster/exclusions text that runs the script with the switch set to 1
 *  as the step does (stub.switch names another value; null runs it unset, as a local run may; stub.census replaces the table,
 *  stub.censusExit and stub.censusErr the census call's exit and stderr; stub.check runs --check; stub.report is the record the
 *  stub writes; stub.exit its exit; stub.real runs the real node); `node` in its result is the argument list of the node --test
 *  call without the reporter flags. `ext` is the physical path of the tree's vscode-extension, as node spells a bundle in its
 *  record, and `rec(bundle, fields...)` spells one record line for that bundle (the reporter's eight fields, the path first). */
function syntheticTree(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'cbl-'));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const ext = path.join(root, 'vscode-extension');
  for (const d of ['vscode-extension/scripts', 'vscode-extension/src', 'vscode-extension/out-tests/ui/webview', 'ui/webview', 'bin']) fs.mkdirSync(path.join(root, d), { recursive: true });
  fs.copyFileSync(SCRIPT, path.join(ext, 'scripts', 'ci-browser-legs.sh'));
  fs.copyFileSync(REPORTER, path.join(ext, 'scripts', 'ci-browser-legs-reporter.mjs'));
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
  web('plain.test.ts', 'const x = 1;\n');
  for (const b of ['a-browser', 'p-browser', 'm-browser', 'k-browser', 'f-browser']) fs.writeFileSync(path.join(ext, 'out-tests', 'ui', 'webview', b + '.test.js'), '');
  const log = path.join(root, 'node-args.txt');
  fs.writeFileSync(path.join(root, 'bin', 'node'), [
    '#!/bin/sh',
    'case "${1:-}" in *browser-legs-census.mjs)',
    '  if [ -n "${CBL_STUB_CENSUS_ERR:-}" ]; then printf \'%s\\n\' "$CBL_STUB_CENSUS_ERR" >&2; fi',
    '  printf \'%s\' "${CBL_STUB_CENSUS:-}"; exit "${CBL_STUB_CENSUS_EXIT:-0}";;',
    'esac',
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
  const A = 'out-tests/ui/webview/a-browser.test.js', B = 'out-tests/ui/webview/b-browser.test.js', P = 'out-tests/ui/webview/p-browser.test.js', M = 'out-tests/ui/webview/m-browser.test.js', K = 'out-tests/ui/webview/k-browser.test.js', F = 'out-tests/ui/webview/f-browser.test.js', PLAIN = 'out-tests/ui/webview/plain.test.js';
  // the table the stub answers the census call with: one row per module, the module's --tsv shape
  const GAP_P = 'never imports the shared launcher, ui/webview/real-viewer-leg.ts';
  const GAP_M = 'loads playwright itself (playwright): inBrowser owns the one playwright read a rostered leg needs';
  const GAP_K = 'holds a skip or todo of its own (line 3: .skip()';
  const CENSUS_TABLE = [[A, '1', '-', '-', 'shared'], [B, '1', '-', '-', 'shared'], [P, '1', GAP_P, '-', 'own'], [M, '1', GAP_M, '-', 'both'], [K, '1', GAP_K, '-', 'shared'], [F, '1', '-', 'Firefox', 'shared'], [PLAIN, '0', '-', '-', 'none']].map((r) => r.join('\t')).join('\n') + '\n';
  const run = (roster, excluded, stub = {}) => {
    if (roster === null) fs.rmSync(path.join(ext, ROSTER), { force: true }); else fs.writeFileSync(path.join(ext, ROSTER), roster);
    if (excluded === null) fs.rmSync(path.join(ext, EXCLUDED), { force: true }); else fs.writeFileSync(path.join(ext, EXCLUDED), excluded);
    fs.rmSync(log, { force: true });
    const env = { ...process.env, PATH: path.join(root, 'bin') + path.delimiter + process.env.PATH };
    delete env.CBL_STUB_REPORT; delete env.CBL_STUB_EXIT; delete env.CBL_STUB_CENSUS_EXIT; delete env.CBL_STUB_CENSUS_ERR; delete env.CBL_STUB_REAL_NODE; delete env.NODE_TEST_CONTEXT;
    env.CBL_STUB_CENSUS = stub.census !== undefined ? stub.census : CENSUS_TABLE;
    if (stub.censusExit !== undefined) env.CBL_STUB_CENSUS_EXIT = String(stub.censusExit);
    if (stub.censusErr !== undefined) env.CBL_STUB_CENSUS_ERR = stub.censusErr;
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
  return { run, root, ext: real, rec, A, B, P, M, K, F, PLAIN, GAP_P, GAP_M, GAP_K, TABLE: CENSUS_TABLE };
}

const EXCLUDE_REST = (...keep) => ['a', 'b', 'p', 'm', 'k', 'f'].filter((n) => !keep.includes(n)).map((n) => 'out-tests/ui/webview/' + n + '-browser.test.js\treason ' + n + '\n').join('');

test('the script runs the rostered legs through node --test when the roster and the tree agree, and prints "no legs in the roster" and starts no node on an empty roster', (t) => {
  const { run, rec, A } = syntheticTree(t);
  // the stub's record: a's one test passed (with no record a rostered leg is red as unrun, the property the post-run test executes)
  const ok = run('# header\n\n' + A + '\n', '# header\n' + EXCLUDE_REST('a'), { report: rec(A, 'pass', 'test', '-', 'test', 'leg a opens the page', '', '-') });
  assert.equal(ok.status, 0, ok.err);
  assert.deepEqual(ok.node, ['--test', A], 'node --test received the roster\'s one bundle');
  assert.equal(ok.testTimeout, '--test-timeout=' + testTimeoutMs(), 'node --test received the per-file bound the script spells (its edges are pinned above)');
  assert.deepEqual(ok.reporters.filter((a) => !a.startsWith('--test-reporter-destination=')), ['--test-reporter=spec', '--test-reporter=./scripts/ci-browser-legs-reporter.mjs'], 'the spec reporter for the log and the step\'s own reporter for the post-run read');
  assert.ok(!ok.out.includes('no legs in the roster'));
  const empty = run('# only a comment\n\n   \n', EXCLUDE_REST());
  assert.equal(empty.status, 0, empty.err);
  assert.ok(empty.out.includes('no legs in the roster'), 'the guard says so: ' + JSON.stringify(empty.out));
  assert.equal(empty.node, null, 'node was not started: with no file arguments node --test would run its default glob');
});

test('the script refuses, naming the line and the remedy, on: a missing file, a stale line, a leg in neither file, a leg in both, a line without a reason, a duplicate, a line naming no leg, a missing bundle, a malformed line (eight shapes, each shown with its whitespace visible and the leg it names attributed to it, never called missing from both files), a roster line whose census row carries a gap (never imports the launcher; loads playwright itself; a skip of its own) or an engine (Firefox); and stops, judging nothing, when the census exits 1 or 2', (t) => {
  const { run, A, B, P, M, K, F, PLAIN, GAP_P, GAP_M, GAP_K, TABLE } = syntheticTree(t);
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
  // a leg in neither file: the red carries the remedy the census's row derives (b passes the gate: the roster), never a bare add-or-exclude
  const neither = run(A + '\n', '# nothing excluded but the rest\n' + rest);
  refused(neither, 'browser leg \'' + B + '\' is in neither ' + ROSTER + ' nor ' + EXCLUDED + ': add \'' + B + '\' to ' + ROSTER + ' (the source launches through inBrowser alone and reaches no engine but Chromium), with the step\'s measured seconds in the PR body');
  assert.ok(!neither.err.includes('or to the exclusions with a tab and a reason'), 'no bare add-or-exclude:\n' + neither.err);
  // m (inBrowser beside its own playwright, Chromium alone) and f (Firefox) in neither file: the gate's own remedy, and the engine form
  const neitherMF = run(A + '\n', EXCLUDE_REST('a', 'm', 'f'));
  refused(neitherMF, 'browser leg \'' + M + '\' is in neither ' + ROSTER + ' nor ' + EXCLUDED + ': pass the roster gate (the source ' + GAP_M + ': launch through inBrowser alone, with no playwright, launch, skip or todo of the leg\'s own) and add \'' + M + '\' to ' + ROSTER + ' with the step\'s measured seconds in the PR body: the exclusions admit no reason of its own, so a leg that reaches Chromium alone is rostered once it passes the gate', 'browser leg \'' + F + '\' is in neither ' + ROSTER + ' nor ' + EXCLUDED + ': add it to ' + EXCLUDED + ' with a tab and the engine form its header admits, "launches Firefox; ' + ENGINE_PHRASE + '"');
  refused(run(A + '\n', A + '\treason\n' + B + '\treason\n' + rest), EXCLUDED + ' line 1: \'' + A + '\' is also ' + ROSTER + ' line 1: a leg is in one file or the other, keep one');
  // a line without a reason (no tab; a tab and a blank reason): the LINE is shown as bash's %q spells it, so the blank reason's
  // whitespace is visible, and the leg it names is attributed to that line, not called missing from both files
  const noReason = run(A + '\n', B + '\n' + rest);
  refused(noReason, EXCLUDED + ' line 1: ' + B + ' has no reason (the line as bash\'s %q spells it): write the bundle path, a tab, and why the gating job does not run it', 'browser leg \'' + B + '\' is named by a line refused above (' + EXCLUDED + ' line 1): fix that line');
  const blank = run(A + '\n', B + '\t  \n' + rest);
  refused(blank, EXCLUDED + ' line 1: $\'' + B + '\\t  \' has no reason', 'browser leg \'' + B + '\' is named by a line refused above (' + EXCLUDED + ' line 1): fix that line');
  for (const r of [noReason, blank]) assert.ok(!r.err.includes('is in neither'), 'the leg the refused line names is not reported as missing from both files:\n' + r.err);
  refused(run(A + '\n' + A + '\n', B + '\treason\n' + rest), ROSTER + ' line 2: \'' + A + '\' duplicates line 1: remove one');
  refused(run(A + '\n', B + '\treason\n' + B + '\tagain\n' + rest), EXCLUDED + ' line 2: \'' + B + '\' duplicates line 1: remove one');
  refused(run(A + '\n' + PLAIN + '\n', B + '\treason\n' + rest), ROSTER + ' line 2: \'' + PLAIN + '\' names no browser leg: ui/webview/plain.test.ts reaches no browser (the census rule in scripts/browser-legs-census.mjs): remove the line');
  // a module the census marks 0 with a gap in its row: the launcher imported and never called; the row's sentence is printed with the line
  const importer = run(A + '\n' + PLAIN + '\n', B + '\treason\n' + rest, { census: TABLE.replace(PLAIN + '\t0\t-', PLAIN + '\t0\timports ui/webview/real-viewer-leg.ts and never calls its inBrowser through that import: call it, or remove the line') });
  refused(importer, ROSTER + ' line 2: \'' + PLAIN + '\' names no browser leg: ui/webview/plain.test.ts imports ui/webview/real-viewer-leg.ts and never calls its inBrowser through that import: call it, or remove the line');
  refused(run(B + '\n', A + '\treason\n' + rest), ROSTER + ' line 1: \'' + B + '\' is not under out-tests/ (the Test step\'s npm test builds it', 'build the bundles before this step');
  refused(run('ui/webview/a-browser.test.ts\n', A + '\treason\n' + B + '\treason\n' + rest), ROSTER + ' line 1: ui/webview/a-browser.test.ts is not a bundle path (out-tests/<dir>/<name>.test.js; a trailing space, tab or carriage return counts', 'fix the line');
  // a carriage return at the end of the line: the line is shown as bash's %q spells it, so the invisible cause is visible,
  // and the leg it names is attributed to that line, not called missing from both files
  const attributed = (r, file, bundle) => { assert.ok(r.err.includes('browser leg \'' + bundle + '\' is named by a line refused above (' + file + ' line 1): fix that line'), r.err); assert.ok(!r.err.includes('is in neither'), 'the leg the refused line names is not reported as missing from both files:\n' + r.err); };
  const crlf = run(A + '\r\n', B + '\treason\n' + rest);
  refused(crlf, ROSTER + ' line 1: $\'' + A + '\\r\' is not a bundle path'); attributed(crlf, ROSTER, A);
  // the attribution is the line's first word after its leading whitespace: a roster line with a tab and a pasted reason (the
  // shape a copy of an exclusions line leaves when a leg is promoted), a leading tab, spaces then a tab before the path, a
  // trailing space, and a leading tab on a roster line all resolve to the path (a tab cut would leave "<path> " and "<path>\r")
  const pasted = run(A + '\tpasted reason\n', B + '\treason\n' + rest);
  refused(pasted, ROSTER + ' line 1: $\'' + A + '\\tpasted reason\' is not a bundle path'); attributed(pasted, ROSTER, A);
  const leadTab = run(A + '\n', '\t' + B + '\treason\n' + rest);
  refused(leadTab, EXCLUDED + ' line 1: $\'\\t' + B + '\\treason\' is not a bundle path'); attributed(leadTab, EXCLUDED, B);
  const spacesTab = run(A + '\n', '  \t' + B + '\treason\n' + rest);
  refused(spacesTab, EXCLUDED + ' line 1: $\'  \\t' + B + '\\treason\' is not a bundle path'); attributed(spacesTab, EXCLUDED, B);
  const trailing = run(A + ' \n', B + '\treason\n' + rest);
  refused(trailing, ROSTER + ' line 1: ' + A + '\\  is not a bundle path'); attributed(trailing, ROSTER, A);
  const leadTabRoster = run('\t' + A + '\n', B + '\treason\n' + rest);
  refused(leadTabRoster, ROSTER + ' line 1: $\'\\t' + A + '\' is not a bundle path'); attributed(leadTabRoster, ROSTER, A);
  refused(run(A + '\n', B + '\treason\n' + P + '  \treason\n' + EXCLUDE_REST('a', 'b', 'p')), EXCLUDED + ' line 2: $\'' + P + '  \\treason\' is not a bundle path', 'browser leg \'' + P + '\' is named by a line refused above (' + EXCLUDED + ' line 2): fix that line');
  // a refused line naming a bundle that is no leg: the line is refused and the real leg, unnamed by any line, is in neither
  const noLeg = run(A + '\n', PLAIN + '\n' + EXCLUDE_REST('a', 'b'));
  refused(noLeg, EXCLUDED + ' line 1: ' + PLAIN + ' has no reason', 'browser leg \'' + B + '\' is in neither ' + ROSTER + ' nor ' + EXCLUDED);
  // a roster line whose census row carries a gap: the row's sentence is printed between the line and the remedy (p never
  // imports the launcher; m loads playwright itself beside its inBrowser call; k keeps a skip of its own), so rostered, its
  // skip would stay a skip under the step and its private launch would never be the failure naming the switch
  refused(run(A + '\n' + P + '\n', B + '\treason\n' + EXCLUDE_REST('a', 'b', 'p')), ROSTER + ' line 2: \'' + P + '\' does not launch through the one shared launcher (' + GAP_P + '): only inBrowser reads ' + SWITCH + ', so a launch or a skip of the leg\'s own stands outside the switch (a private skip stays a skip; a private launch that fails is never the failure naming the switch): launch through inBrowser (ui/webview/real-viewer-leg.ts), with no launch or skip of the leg\'s own, before rostering it');
  refused(run(A + '\n' + M + '\n', B + '\treason\n' + EXCLUDE_REST('a', 'b', 'm')), ROSTER + ' line 2: \'' + M + '\' does not launch through the one shared launcher (' + GAP_M + '): only inBrowser reads');
  refused(run(A + '\n' + K + '\n', B + '\treason\n' + EXCLUDE_REST('a', 'b', 'k')), ROSTER + ' line 2: \'' + K + '\' does not launch through the one shared launcher (' + GAP_K + '): only inBrowser reads');
  // a roster line whose census row names an engine: the gating job installs Chromium only
  refused(run(A + '\n' + F + '\n', B + '\treason\n' + EXCLUDE_REST('a', 'b', 'f')), ROSTER + ' line 2: \'' + F + '\' reaches Firefox; the gating job installs Chromium only, so under the switch that launch is red: keep the leg in ' + EXCLUDED + ' with that reason');
  // the census did not run (exit 1: no compiler) or refused a form (exit 2): its stderr is shown, nothing is judged, no leg ran
  const noCensus = run(A + '\n', B + '\treason\n' + rest, { census: '', censusExit: 1, censusErr: 'browser-legs-census: the typescript compiler is not installed under vscode-extension/node_modules (a synthetic message)' });
  refused(noCensus, 'browser-legs-census: the typescript compiler is not installed', 'ci-browser-legs: the census did not run (exit 1, above), so nothing was judged and no leg ran');
  assert.ok(!noCensus.err.includes('names no browser leg') && !noCensus.err.includes('is in neither'), 'nothing is judged over a census that did not run:\n' + noCensus.err);
  const refusal = run(A + '\n', B + '\treason\n' + rest, { census: '', censusExit: 2, censusErr: 'browser-legs-census: REFUSED ui/webview/a-browser.test.ts:2: a synthetic refusal' });
  refused(refusal, 'browser-legs-census: REFUSED ui/webview/a-browser.test.ts:2', 'ci-browser-legs: the census refused a form it cannot classify (above, with file and line): rewrite that form, or teach scripts/browser-legs-census.mjs to read it; nothing else was judged and no leg ran');
  assert.ok(!refusal.err.includes('names no browser leg') && !refusal.err.includes('is in neither'), 'nothing else is judged over a refusal:\n' + refusal.err);
  const stale = run(A + '\n', B + '\treason\n' + C + '\treason\n' + rest);
  refused(stale, EXCLUDED + ' line 2: \'' + C + '\' names ui/webview/c-browser.test.ts, which is not in the tree (the source moved or was deleted): fix the line');
});

test('the script allows a pending line while its source is absent, reds a pending reason that names no PR, and once the source is present reds the line with the promotion remedy the census derives (a roster line for a shared Chromium leg; the engine form for an engine leg; the gate\'s own remedy for a Chromium-only leg that misses the gate, private or beside its own playwright, since no form admits it; no line for a non-leg) and not as "in neither" too', (t) => {
  const { run, root, rec, A, P, M, F, PLAIN, GAP_P, GAP_M, TABLE } = syntheticTree(t);
  const C = 'out-tests/ui/webview/c-browser.test.js';
  const rest = EXCLUDE_REST('a');
  const absent = run(A + '\n', C + '\tpending #860: a leg an open PR brings\n' + rest, { report: rec(A, 'pass', 'test', '-', 'test', 'leg a opens the page', '', '-') });
  assert.equal(absent.status, 0, 'a pending line with an absent source is allowed; stderr: ' + absent.err);
  assert.deepEqual(absent.node, ['--test', A], 'the rostered leg ran');
  const check = run(A + '\n', C + '\tpending #860: a leg an open PR brings\n' + rest, { check: true });
  assert.equal(check.status, 0, check.err);
  assert.match(check.out, /1 rostered, 6 browser legs in the census, 1 pending lines naming absent sources/, 'the agreement line counts the pending lines: ' + check.out);
  const noPr = run(A + '\n', C + '\tpending: a leg with no PR named\n' + rest);
  assert.equal(noPr.status, 1, noPr.err);
  assert.ok(noPr.err.includes(EXCLUDED + ' line 1: \'' + C + '\' has a pending reason that names no PR (\'pending: a leg with no PR named\'): a pending line reads \'pending #<PR>: <why>\''), noPr.err);
  assert.equal(noPr.node, null, 'no leg ran');
  // the source arrives (the census table gains its row: a shared Chromium leg): red with the roster remedy naming the PR, once
  fs.writeFileSync(path.join(root, 'ui', 'webview', 'c-browser.test.ts'), 'import { inBrowser } from "./real-viewer-leg";\ntest("leg c opens the page", async (t) => { await inBrowser(t, async (browser) => {}); });\n');
  const present = run(A + '\n', C + '\tpending #860: a leg an open PR brings\n' + rest, { census: TABLE + [C, '1', '-', '-', 'shared'].join('\t') + '\n' });
  assert.equal(present.status, 1, present.err);
  assert.ok(present.err.includes(EXCLUDED + ' line 1: \'' + C + '\' is pending #860 and its source ui/webview/c-browser.test.ts is in the tree, so the leg has arrived (#860 merged main, or this is #860\'s branch) and the line\'s condition has passed: promote it: delete this line and add \'' + C + '\' to ' + ROSTER + ' (the source launches through inBrowser alone and reaches no engine but Chromium), with the step\'s measured seconds in the PR body'), present.err);
  assert.ok(!present.err.includes('is in neither'), 'the arrived leg is not also called missing from both files:\n' + present.err);
  assert.equal(present.node, null, 'no leg ran');
  // a private leg (p: never imports the launcher) and one calling inBrowser beside its own playwright (m), both Chromium alone:
  // no form of the exclusions admits them, so the remedy is the gate's own; an engine leg (f: Firefox): the engine form; a
  // non-leg (plain): no line
  const GATE = (gap, bundle) => 'promote it: pass the roster gate (the source ' + gap + ': launch through inBrowser alone, with no playwright, launch, skip or todo of the leg\'s own), then delete this line and add \'' + bundle + '\' to ' + ROSTER + ' with the step\'s measured seconds in the PR body: the exclusions admit no reason of its own, so a leg that reaches Chromium alone is rostered once it passes the gate';
  const priv = run(A + '\n', P + '\tpending #859: a private leg\n' + EXCLUDE_REST('a', 'p'));
  assert.equal(priv.status, 1, priv.err);
  assert.ok(priv.err.includes('\'' + P + '\' is pending #859') && priv.err.includes(GATE(GAP_P, P)), priv.err);
  const both = run(A + '\n', M + '\tpending #853: calls inBrowser beside a playwright load of its own\n' + EXCLUDE_REST('a', 'm'));
  assert.equal(both.status, 1, both.err);
  assert.ok(both.err.includes('\'' + M + '\' is pending #853') && both.err.includes(GATE(GAP_M, M)), both.err);
  assert.ok(!both.err.includes('why the gating job does not run it'), 'the old remedy, a bare gap sentence the closed set refuses, is gone:\n' + both.err);
  // the engine remedy is held by includes() up to the form's closing quote, here and at the neither red in the refusals test above:
  // a tail appended AFTER the closing quote is not refused by these pins, since the quoted form is what a copy into the exclusions
  // carries and a tail outside it grants nothing, while a tail inside the form that carries a second claim (another form's phrase,
  // a second engine) is refused as ambiguous by the closed-set tests
  const eng = run(A + '\n', F + '\tpending #859: an engine leg\n' + EXCLUDE_REST('a', 'f'));
  assert.equal(eng.status, 1, eng.err);
  assert.ok(eng.err.includes('\'' + F + '\' is pending #859') && eng.err.includes('promote it: keep the line and replace the reason with the engine form the header of ' + EXCLUDED + ' admits, "launches Firefox; ' + ENGINE_PHRASE + '"'), eng.err);
  const none = run(A + '\n', PLAIN + '\tpending #861: a module that is no leg\n' + rest);
  assert.equal(none.status, 1, none.err);
  assert.ok(none.err.includes('\'' + PLAIN + '\' is pending #861') && none.err.includes('promote it: remove the line (the source reaches no browser by the census rule)'), none.err);
  for (const r of [priv, both, eng, none]) assert.ok(!r.err.includes('is in neither'), 'no second red:\n' + r.err);
});

test('after node --test the script derives per rostered leg that at least one attributable pass ran, red otherwise (todo-only, a describe() that registers none, a file that registered nothing, a failure inside a todo); reds a skipped test naming the test, its reason and the switch\'s state; reds a failure inside a todo and a file that failed as a whole by name; prints the lost-browser remedy beside a leg whose failure names the switch; passes node\'s status through', (t) => {
  const { run, root, rec, A, B } = syntheticTree(t);
  const excluded = EXCLUDE_REST('a');
  const PASS = rec(A, 'pass', 'test', '-', 'test', 'leg a opens the page', '', '-');
  const skipped = run(A + '\n', excluded, { report: PASS + rec(A, 'pass', 'test', 'skip', 'test', 'leg a keeps the slice\\nwhole # 2', 'no playwright chromium on this box', '-') });
  assert.equal(skipped.status, 1, 'a skip under the switch is red; stderr: ' + skipped.err);
  assert.deepEqual(skipped.node, ['--test', A], 'the leg ran (the skip is read from the run, not refused before it)');
  assert.ok(skipped.err.includes('ci-browser-legs: skipped with ' + SWITCH + '=1: \'leg a keeps the slice\\nwhole # 2\' # SKIP no playwright chromium on this box (' + A + ')'), 'the skip names the test as the record spells it (a newline written \\n), its reason and its leg:\n' + skipped.err);
  assert.ok(skipped.err.includes('a rostered leg skipped a test with ' + SWITCH + '=1, so the step claims coverage it did not run'), skipped.err);
  assert.ok(skipped.err.includes('only inBrowser in ui/webview/real-viewer-leg.ts turns a launch it cannot make into a failure here') && skipped.err.includes('move it to ' + EXCLUDED + ' with that reason'), skipped.err);
  assert.ok(!skipped.err.includes('no test of this leg passed'), 'a leg with a pass beside its skip is not called unrun:\n' + skipped.err);
  // the same skip with the switch unset, as a local run may have it: still red, and the message says the switch is unset
  // and that the step sets it, instead of claiming a state the run did not have
  const unset = run(A + '\n', excluded, { report: PASS + rec(A, 'pass', 'test', 'skip', 'test', 'leg a opens the page', 'why', '-'), switch: null });
  assert.equal(unset.status, 1, 'a skip with the switch unset is red too; stderr: ' + unset.err);
  assert.ok(unset.err.includes('skipped with ' + SWITCH + ' unset: \'leg a opens the page\' # SKIP why (' + A + ')'), unset.err);
  assert.ok(unset.err.includes('a rostered leg skipped a test with ' + SWITCH + ' unset, so this run claims coverage it did not run: the step sets ' + SWITCH + '=1'), unset.err);
  assert.ok(!unset.err.includes(SWITCH + '=1:') && !unset.err.includes('with ' + SWITCH + '=1,'), 'no line claims the switch was set:\n' + unset.err);
  const clean = run(A + '\n', excluded, { report: PASS + rec(A, 'pass', 'suite', '-', 'test', 'a suite with tests', '', '-') });
  assert.equal(clean.status, 0, 'a pass beside a suite\'s own pass: no red: ' + clean.err);
  assert.equal(clean.err, '', 'nothing on stderr when every rostered leg passed a test');
  // the property: no attributable pass. Four shapes, each red naming the leg and what the record held, none called a skip
  const UNRUN = 'ci-browser-legs: ' + A + ': no test of this leg passed in this run (the record holds ';
  const none = run(A + '\n', excluded, { report: rec(A, 'pass', 'test', '-', 'file-level', A, '', '-') });
  assert.equal(none.status, 1, 'a file that registered nothing is red; stderr: ' + none.err);
  assert.deepEqual(none.node, ['--test', A], 'the leg ran (the empty run is read from the record, not refused before it)');
  assert.ok(none.err.includes(UNRUN + '0 skipped, 0 todo, 0 suite and 1 file-level results for it), so the step claims coverage it did not run') && none.err.includes('move it to ' + EXCLUDED + ' with that reason until one runs'), none.err);
  // the unrun red carries the boundary of what the record proves beside its remedy (read from the run's stderr): a pass is the
  // most the record proves, and the browser part's own run is read only by the skip and lost-browser lines when its launch is reached
  assert.ok(none.err.includes('a rostered leg holds a test that runs and passes here (a pass is the most the record proves: a pass from a test needing no browser satisfies this check, and the browser part\'s own run is read only by the skip and lost-browser lines when its launch is reached)'), 'the unrun red says, beside its remedy, that a pass is the most the record proves, so a reader of the red does not take the property for a launch record (holds the sentence as the script emits it: a reword of the parenthetical in the script moves this pin too):\n' + none.err);
  const suite = run(A + '\n', excluded, { report: rec(A, 'pass', 'suite', '-', 'test', 'a suite that registers none', '', '-') });
  assert.equal(suite.status, 1, 'a describe() that registers no test is red; stderr: ' + suite.err);
  assert.ok(suite.err.includes(UNRUN + '0 skipped, 0 todo, 1 suite and 0 file-level results for it)'), suite.err);
  const todos = run(A + '\n', excluded, { report: rec(A, 'pass', 'test', 'todo', 'test', 'bodyless todo', '', '-') + rec(A, 'pass', 'test', 'todo', 'test', 'a todo with a passing body', 'waiting on the browser', '-') });
  assert.equal(todos.status, 1, 'a leg whose tests are all todo is red; stderr: ' + todos.err);
  assert.ok(todos.err.includes(UNRUN + '0 skipped, 2 todo, 0 suite and 0 file-level results for it)'), todos.err);
  assert.ok(!todos.err.includes('failed inside a todo'), 'a todo that passed is not a discarded failure:\n' + todos.err);
  const todoFail = run(A + '\n', excluded, { report: rec(A, 'fail', 'test', 'todo', 'test', 'a real failure inside a todo', 'the leg is broken', 'testCodeFailure') });
  assert.equal(todoFail.status, 1, 'a failure inside a todo is red although node exits 0; stderr: ' + todoFail.err);
  assert.ok(todoFail.err.includes('ci-browser-legs: ' + A + ': \'a real failure inside a todo\' failed inside a todo (the leg is broken): node discards the failure (# fail 0, exit 0), so the step would read green over a broken test: remove the todo, or fix the test and remove it'), todoFail.err);
  assert.ok(todoFail.err.includes(UNRUN + '0 skipped, 1 todo, 0 suite and 0 file-level results for it)'), 'and the leg ran no counting pass:\n' + todoFail.err);
  // a real pass beside a failure inside a todo: the property holds, the discarded failure is still red
  const mixed = run(A + '\n', excluded, { report: PASS + rec(A, 'fail', 'test', 'todo', 'test', 'a swallowed failure', 'the leg is broken', 'testCodeFailure') });
  assert.equal(mixed.status, 1, mixed.err);
  assert.ok(mixed.err.includes('\'a swallowed failure\' failed inside a todo (the leg is broken)') && !mixed.err.includes('no test of this leg passed'), mixed.err);
  for (const r of [none, suite, todos, todoFail]) assert.ok(!r.err.includes('skipped with'), 'an unrun leg is not called a skip:\n' + r.err);
  // two rostered legs, one of which ran nothing: the red names that one and not the other (attribution is per bundle)
  fs.writeFileSync(path.join(root, 'vscode-extension', B), '');   // b has no bundle in the tree by default
  const two = run(A + '\n' + B + '\n', EXCLUDE_REST('a', 'b'), { report: PASS + rec(B, 'pass', 'test', 'todo', 'test', 'leg b todo', '', '-') });
  assert.equal(two.status, 1, two.err);
  assert.ok(two.err.includes('ci-browser-legs: ' + B + ': no test of this leg passed') && !two.err.includes('ci-browser-legs: ' + A + ': no test'), 'the leg that ran nothing is named and the one that passed is not:\n' + two.err);
  // a file that failed as a whole (node's file-level result failing: a timeout under --test-timeout, or a throw at load)
  const timedOut = run(A + '\n', excluded, { report: rec(A, 'fail', 'test', '-', 'file-level', A, 'test timed out after 300000ms', 'testTimeoutFailure'), exit: 1 });
  assert.equal(timedOut.status, 1, 'node\'s failure stands');
  assert.ok(timedOut.err.includes('ci-browser-legs: ' + A + ' failed as a whole (testTimeoutFailure: test timed out after 300000ms): a file that timed out under node\'s --test-timeout, or threw at load, ran no test that counts'), timedOut.err);
  assert.ok(!timedOut.err.includes('no test of this leg passed'), 'a failed file is node\'s red, not called unrun on top:\n' + timedOut.err);
  // node's own exit status is the step's: the roster array is node's argument list, with no xargs to map it (GNU 123, BSD 1)
  const failed = run(A + '\n', excluded, { report: rec(A, 'fail', 'test', '-', 'test', 'leg a opens the page', 'an assertion of the leg\'s own failed', 'testCodeFailure'), exit: 1 });
  assert.equal(failed.status, 1, 'node\'s failure is the step\'s, as node\'s own status');
  assert.equal(failed.err, '', 'a failure for a reason of the leg\'s own gets no label of the script\'s (node\'s own report carries it):\n' + failed.err);
  // a failure whose message names the switch is inBrowser failing to launch under it: the remedy is printed beside the leg
  const LOST = SWITCH + ' is set and this leg cannot run: no playwright browser on this box; the browser leg needs one: browserType.launch: Executable doesn\'t exist at /nowhere';
  const lost = run(A + '\n', excluded, { report: rec(A, 'fail', 'test', '-', 'test', 'leg a opens the page', LOST, 'testCodeFailure'), exit: 1 });
  assert.equal(lost.status, 1);
  assert.ok(lost.err.includes('ci-browser-legs: ' + A + ': \'leg a opens the page\' failed under ' + SWITCH + '=1 because inBrowser could not launch (' + LOST + '): the runner lost its browser: check the Chromium install step'), lost.err);
  // the phrase quoted AFTER other text (the rostered switch test's assertion messages embed a child run's stdout, which carries
  // it): an ordinary failure of the leg, no LOST line, no label of the script's, node's red passed through
  const quoted = run(A + '\n', excluded, { report: rec(A, 'fail', 'test', '-', 'test', 'leg a opens the page', 'the leg failed under the switch; the child run printed: ' + LOST, 'testCodeFailure'), exit: 1 });
  assert.equal(quoted.status, 1, 'node\'s failure stands');
  assert.ok(!quoted.err.includes('the runner lost its browser'), 'a message that quotes the phrase after other text is not a lost browser (LOST reads the start of the message):\n' + quoted.err);
  assert.equal(quoted.err, '', 'an ordinary failure gets no label of the script\'s:\n' + quoted.err);
  // the switch under a non-"1" non-empty value: the script reads it as set (any non-empty value arms it, as the helper does),
  // naming the value in the skip's red and giving the set-switch remedy
  const yes = run(A + '\n', excluded, { report: PASS + rec(A, 'pass', 'test', 'skip', 'test', 'leg a opens the page', 'why', '-'), switch: 'yes' });
  assert.equal(yes.status, 1, 'a skip under the switch set to yes is red; stderr: ' + yes.err);
  assert.ok(yes.err.includes('skipped with ' + SWITCH + '=yes: \'leg a opens the page\' # SKIP why (' + A + ')'), 'the skip names the switch\'s value as the run had it (yes):\n' + yes.err);
  assert.ok(yes.err.includes('a rostered leg skipped a test with ' + SWITCH + '=yes, so the step claims coverage it did not run') && yes.err.includes('only inBrowser in ui/webview/real-viewer-leg.ts turns a launch it cannot make into a failure here'), 'the set-switch remedy, not the unset one: the script\'s two reads arm on any non-empty value:\n' + yes.err);
  const both = run(A + '\n', excluded, { report: rec(A, 'pass', 'test', 'skip', 'test', 'leg a opens the page', 'why', '-'), exit: 7 });
  assert.equal(both.status, 7, 'with a failure and a skip node\'s own status (7) stands, not overwritten by the skip\'s status=1, and the skip is still named');
  assert.ok(both.err.includes('skipped with ' + SWITCH + '=1'), both.err);
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
  };
}

test('the reporter, executed with a real node --test over synthetic bundles: one line per result attributed to its file, a describe() as a suite, a skip and a todo as directives, a failure inside a todo as a fail, node\'s file-level result marked for a file that registered nothing, and a name\'s tab and newline written \\t and \\n', (t) => {
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
  assert.equal(lines.length, 12, 'twelve results over the eight bundles and no other line: ' + JSON.stringify(lines));
  assert.ok(lines.every((f) => f.length === 8), 'eight fields per line');
});

test('the composition, executed: the script with the real node and the real reporter over the shapes as rostered legs reds todo-only, describe-none, nothing and a failure inside a todo by leg, names the skip, prints the lost-browser remedy, and passes a clean roster', (t) => {
  const { run, root, TABLE } = syntheticTree(t);
  const S = writeShapes(path.join(root, 'vscode-extension'));
  const shared = 'import { inBrowser } from "./real-viewer-leg";\n';
  const rows = [];
  for (const b of Object.values(S)) {
    const name = path.basename(b, '.test.js');
    fs.writeFileSync(path.join(root, 'ui', 'webview', name + '.test.ts'), shared + 'test("x", async (t) => { await inBrowser(t, async () => {}); });\n');
    rows.push([b, '1', '-', '-', 'shared'].join('\t'));
  }
  const census = TABLE + rows.join('\n') + '\n';
  const excl = (...keep) => EXCLUDE_REST() + Object.values(S).filter((b) => !keep.includes(b)).map((b) => b + '\treason\n').join('');
  const all = run(Object.values(S).join('\n') + '\n', excl(...Object.values(S)), { census, real: true });
  assert.equal(all.status, 1, 'node\'s exit 1 (the lost shape) is the script\'s; stderr: ' + all.err);
  for (const b of [S.todoBoth, S.describeNone, S.nothing, S.todoFail]) assert.ok(all.err.includes('ci-browser-legs: ' + b + ': no test of this leg passed in this run'), b + ' is red as unrun:\n' + all.err);
  for (const b of [S.passSkip, S.mixed, S.describePass, S.lost]) assert.ok(!all.err.includes('ci-browser-legs: ' + b + ': no test of this leg passed'), b + ' is not called unrun:\n' + all.err);
  assert.ok(all.err.includes('ci-browser-legs: ' + S.todoFail + ': \'a real failure inside a todo\' failed inside a todo (the leg is broken)') && all.err.includes('ci-browser-legs: ' + S.mixed + ': \'a swallowed failure\' failed inside a todo (the leg is broken)'), all.err);
  assert.ok(all.err.includes('skipped with ' + SWITCH + '=1: \'one skip\' # SKIP no browser # here (' + S.passSkip + ')'), all.err);
  assert.ok(all.err.includes('ci-browser-legs: ' + S.lost + ': \'the launch\' failed under ' + SWITCH + '=1 because inBrowser could not launch (' + SWITCH + ' is set and this leg cannot run: no playwright browser on this box): the runner lost its browser: check the Chromium install step'), all.err);
  assert.ok(all.err.includes(S.describeNone + ': no test of this leg passed in this run (the record holds 0 skipped, 0 todo, 1 suite and 0 file-level results for it)') && all.err.includes(S.nothing + ': no test of this leg passed in this run (the record holds 0 skipped, 0 todo, 0 suite and 1 file-level results for it)'), all.err);
  const clean = run(S.describePass + '\n', excl(S.describePass), { census, real: true });
  assert.equal(clean.status, 0, 'a leg whose test passes inside a describe(): green; stderr: ' + clean.err);
  assert.equal(clean.err, '', 'nothing on stderr');
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
  // run, and the Test step runs its two child arms); what it asserts is its own to state, and the census test holds it to the
  // roster gate. The helper's playwrightInstalled export has that test as its consumer (the reason the child names is derived
  // from the helper's own module read, never from a second one): presence pins, which say only that the file names these
  assert.ok(fs.existsSync(SWITCH_TEST), 'the executed test of the switch exists at ' + path.relative(REPO, SWITCH_TEST));
  assert.ok(read(SWITCH_TEST).includes('playwrightInstalled()'), path.relative(REPO, SWITCH_TEST) + ' consumes the helper\'s playwrightInstalled export (a presence pin: the export is not dead code in this tree)');
  assert.ok(parseRoster(read(path.join(EXT, ROSTER))).some((e) => e.bundle === 'out-tests/ui/webview/real-viewer-leg-switch.test.js'), path.relative(REPO, SWITCH_TEST) + ' is rostered in ' + ROSTER + ', so the step runs its leg with a browser on every CI run');
});
