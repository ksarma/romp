// The shared browser-legs CI step, held to the tree from CI's Shell job, which runs tools/*.test.mjs with no npm ci. The
// gating vscode-extension job runs npm test before it installs a browser, so every browser leg skips at launch there; the
// step "Browser legs (node --test over ci-browser-legs.txt)" runs the legs named in vscode-extension/ci-browser-legs.txt
// after the job's Chromium install with ROMP_BROWSER_LEGS_REQUIRE=1: the one shared launcher, inBrowser in
// ui/webview/real-viewer-leg.ts, reads the switch (any non-empty value counts), and under the switch, inBrowser fails a
// launch it cannot make, naming the switch and the reason, instead of skipping.
// WHAT THIS MODULE DOES NOT HOLD. The roster rule (under the switch, a rostered leg passes only when inBrowser has launched
// Chromium; its homes, read by the homes pin below, state the rest) is the reviewer's to check: nothing in the tree reads a
// leg's source for it, so the step can read green a rostered leg that breaks it, as the examples its homes name show. Nor
// does anything here check that every browser leg in the tree is rostered. A green here is:
//   - the step exists once in that job, directly after the Chromium install step (by step NAMES, over the steps and
//     fields jobs() and steps() read by their lines' shapes), with the switch as its only env, as the env reader reads
//     it (its docstring, which states what it refuses), and the run line, in the job's default working directory, and
//     no Playwright install or cache before the Test step, as the install pin reads them (its docstring); every path
//     PATH_TOKEN reads (its docstring) in the step's comment is in the tree;
//   - the step carries a timeout-minutes of its own that fits the margin under the job's cap at the measured head (the
//     assertion's arithmetic over the step comment's measured figures and phrase and the cap comment's number and
//     passage, read as the comments at those reads state), and the script passes node a --test-timeout above the
//     timeout: values the bound pin reads (boundReds' docstring) in a rostered source and under the step's bound, so a
//     hung leg fails by name before the step is cut. The spellings the bound pin reads and the ones it does not read are
//     boundReds' to state: a value spelled outside them is not held here, and a leg whose file outlasts the file bound
//     meets node's cut and the script's failed-as-a-whole red whatever its own timeout says (the check's guarantee is
//     that no value it reads reaches the file bound, and a leg's whole-file seconds are measured in the PR's body);
//   - the roster is well formed: each line parseRoster keeps (its docstring) is a bundle path as wellFormed reads it (its
//     docstring), no such line is duplicated, and each names a source that exists in the tree;
//   - each home of the roster rule, read in its named section (RULE_HOMES' docstring), states it in the same words: the
//     rule, who checks it, that nothing reads a leg's source for it, its examples as examples (the list after
//     "examples, not the whole set:" holds exactly the phrases of EXAMPLES, the witness table), that a leg built to
//     pass without a browser is outside what the step can detect, the witness, and that nothing checks that every
//     browser leg in the tree is rostered (a text pin: it holds what the homes say); the witness is executed: the
//     script with the real node and the real reporter reads green one synthetic rostered leg of each example in
//     EXAMPLES, each failure marked as it happens, and a control that awaits the catch example's stand-in for inBrowser
//     with no try reads red with the lost-browser remedy;
//   - vscode-extension/.vscodeignore names the CI-only files (the roster, the script and its reporter);
//   - the script the step calls (vscode-extension/scripts/ci-browser-legs.sh) exists, is executable and runs node
//     --test over the roster array (no xargs, so node's status is the step's on every platform) with the reporter
//     scripts/ci-browser-legs-reporter.mjs beside the spec reporter; run on synthetic trees with a stub node on PATH
//     that records the node --test call and writes the record a case hands it, run through a link to the tree on every
//     platform (so the post-run read's key on the physical path is held where the temporary directory is no link), it
//     refuses a missing roster file, a stale line, a duplicate, a missing bundle and a malformed line (nine malformed
//     shapes: six shown with their whitespace as bash's %q spells it, and three non-canonical spellings), each red
//     naming the line and the remedy; runs the pre-run checks alone under --check (the script's header states how it
//     reads it), which refuses a stale, a duplicate and a malformed line as the step's run does; hands node every line
//     of a roster whose last line has no newline; prints "no legs in the roster" and starts no node on an empty roster;
//     and after node --test reads the reporter's record and derives the property and the reds the script's header
//     states, each read from the script's stderr in the cases below, within the scope the script's header states,
//     executed by the foreign-file case below, and passes node's own failure status through. The two remedies that move
//     a leg off the step, after an unrun leg and after a skip under the switch, take its line out of the roster, each
//     read from the script's stderr. The reporter itself is executed here over synthetic bundles with a real node
//     --test (a pass beside a skip, todos, a describe() with a test and without one, a file that registered nothing,
//     failures inside a todo, a lost browser's failure, a bundle that throws at load, and a name holding a tab and a
//     newline), and so is the composition: the script with the real node and the real reporter over those bundles as
//     rostered legs, and over a leg whose test passes and whose error comes after the test ended. After one stub run
//     and after the composition's first real-node run, the record file the script handed its reporter (the path the
//     stub logged, in the fresh TMPDIR the run was given) is gone and that TMPDIR is empty. A roster line holding a
//     backslash is held by seen_at's rows, and a tree under a directory whose name holds one by the post-run key's
//     row, each read as the script's comment above seen_at or above its awk pass states;
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
import { isDeepStrictEqual } from 'node:util';

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

/** The jobs of the workflow: the `^  <key>:` lines after the `jobs:` line (a key of letters, digits, _ and - with only
 *  whitespace after its colon; a quoted key, or a key line with a comment after its colon, is not read, and its lines join
 *  the job before it), each with its lines up to the next such line. */
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
/** A job's steps: each starts at a line of six spaces and `- ` (`^      - `) and runs to the next such line, so a `- `
 *  at another indent does not start one. Its name is the rest of its first `      - name: ` or `        name: ` line,
 *  trimmed, quotes kept (null for a step with neither, a bare `uses:` step), so a name: line at another indent is not
 *  its name. Its comments are its lines whose first non-blank character is #, and `code` the rest, a line with a # after
 *  code included. Its fields are its code lines of eight spaces, a field of letters and -, and a colon, the rest of the
 *  line trimmed as the value, and its opening line when that is `      - <field>: ` and a value, a later line of a field
 *  replacing an earlier one; a field at another indent, a field holding a digit or _, and a quoted field key are not
 *  read. Its table: STEPS_ROWS, run by the test after it.
 *  Its env, the env reader, which reads every step and fails closed: a line in the block it cannot read is refused,
 *  named by its line (the step's envRefused), rather than read past. An env line is a code line of exactly eight spaces
 *  and then `env:`, and the block begins after the step's env line when only whitespace follows its colon. An env line
 *  with anything else after its colon (an inline mapping, a comment, an alias) is refused, and so is a second env line
 *  in the step, each opening a block read the same way. The block runs to the first code line that is not blank and
 *  whose leading run of spaces and tabs holds no tab and eight spaces or fewer. A blank line (empty, or whitespace
 *  alone by \s at any length) and a # line (dropped from the code lines above, at any indent, inside a block scalar's
 *  text too) neither end the block nor are read. Inside it, a line of exactly ten spaces, then a key of letters, digits
 *  and _ beginning with a letter or _, then a colon and a space, is read as that key, its value the rest of the line
 *  trimmed: a block-scalar indicator (`NOTE: |`, `FOO: >-`) is read as the value, and a colon followed by spaces alone
 *  as an empty value, each an extra key, a loud red. Every other line in the block is refused: a quoted key, a key led
 *  by a digit, a key holding another character (a hyphen, a dot, the YAML merge key `<<`), a key with a space before
 *  its colon, a key whose colon ends its line, a line led by nine, or eleven or more, spaces (a block scalar's text, a
 *  value continued on the next line, a key at another depth), and a line with a tab in its leading whitespace. The
 *  first test asserts the Browser legs step's refused lines are none and its env the switch alone. Its table: ENV_ROWS,
 *  run by the test after STEPS_ROWS' test. */
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
    s.envRefused = [];
    let block = false, envLines = 0;
    for (const l of s.code) {
      if (/^        env:/.test(l)) {
        envLines++;
        block = true;
        if (envLines > 1 || !/^        env:\s*$/.test(l)) s.envRefused.push(l);
        continue;
      }
      if (!block || /^\s*$/.test(l)) continue;
      const lead = /^[ \t]*/.exec(l)[0];
      if (!lead.includes('\t') && lead.length <= 8) { block = false; continue; }
      const e = /^          ([A-Za-z_][A-Za-z0-9_]*): (.*)$/.exec(l);
      if (e) s.env[e[1]] = e[2].trim();
      else s.envRefused.push(l);
    }
  }
  return out;
}
/** steps()' table: each row a job's lines and the steps steps() reads from them, by name and fields (and comments where the
 *  row is about them), one spelling inside and one outside each family its docstring names. */
const STEPS_ROWS = [
  { what: 'a line of six spaces and "- " opens a step, and a "- " line at eight spaces does not',
    lines: ['      - name: A', '        - name: C', '      - name: B'], steps: [{ name: 'A', fields: { name: 'A' } }, { name: 'B', fields: { name: 'B' } }] },
  { what: 'a name on the step\'s "- name:" opener', lines: ['      - name: A', '        run: a'], steps: [{ name: 'A', fields: { name: 'A', run: 'a' } }] },
  { what: 'a name on an eight-space "name:" line after a "- uses:" opener', lines: ['      - uses: actions/x@v1', '        name: B'], steps: [{ name: 'B', fields: { uses: 'actions/x@v1', name: 'B' } }] },
  { what: 'a bare "uses:" step, with no name', lines: ['      - uses: actions/x@v1'], steps: [{ name: null, fields: { uses: 'actions/x@v1' } }] },
  { what: 'a name: line at ten spaces is not the step\'s name', lines: ['      - uses: actions/x@v1', '        with:', '          name: C'], steps: [{ name: null, fields: { uses: 'actions/x@v1', with: '' } }] },
  { what: 'a quoted name is read with its quotes', lines: ['      - name: "Test"'], steps: [{ name: '"Test"', fields: { name: '"Test"' } }] },
  { what: 'a # line is a comment and not code, and a # after code is code', lines: ['      - name: A', '        # a comment', '        run: a # b'], steps: [{ name: 'A', fields: { name: 'A', run: 'a # b' }, comments: ['        # a comment'] }] },
  { what: 'a field on an eight-space line, its value trimmed', lines: ['      - name: A', '        timeout-minutes:   5  '], steps: [{ name: 'A', fields: { name: 'A', 'timeout-minutes': '5' } }] },
  { what: 'a field on the step\'s "- " opener', lines: ['      - run: npx playwright install chromium'], steps: [{ name: null, fields: { run: 'npx playwright install chromium' } }] },
  { what: 'a field at ten spaces is not read', lines: ['      - name: A', '        with:', '          run: x'], steps: [{ name: 'A', fields: { name: 'A', with: '' } }] },
  { what: 'a field holding _ is not read', lines: ['      - name: A', '        timeout_minutes: 5'], steps: [{ name: 'A', fields: { name: 'A' } }] },
  { what: 'a field holding a digit is not read', lines: ['      - name: A', '        run2: x'], steps: [{ name: 'A', fields: { name: 'A' } }] },
  { what: 'a quoted field key is not read', lines: ['      - name: A', '        "working-directory": x'], steps: [{ name: 'A', fields: { name: 'A' } }] },
  { what: 'a later line of a field replaces an earlier one', lines: ['      - run: a', '        run: b'], steps: [{ name: null, fields: { run: 'b' } }] },
];
test('steps()\' table: each row\'s steps, names and fields read as steps()\' docstring states', () => {
  const wrong = [];
  for (const row of STEPS_ROWS) {
    const got = steps({ lines: row.lines }).map((s, i) => ({ name: s.name, fields: s.fields, ...(row.steps[i] && row.steps[i].comments ? { comments: s.comments } : {}) }));
    if (!isDeepStrictEqual(got, row.steps)) wrong.push(row.what + ': steps() over ' + JSON.stringify(row.lines) + ' reads ' + JSON.stringify(got) + ', not ' + JSON.stringify(row.steps));
  }
  assert.deepEqual(wrong, [], 'each row of steps()\' table is read as its docstring states; the rows read otherwise: ' + JSON.stringify(wrong));
});
/** The env reader's table: each row a step's lines after its `      - name: S` opener, with `        run: x` after them, and
 *  the env and the refused lines steps() reads from them, one spelling inside and one outside each family its docstring
 *  names. */
const ENV_ON = '          ' + SWITCH + ': "1"', ENV_NO = '          NODE_OPTIONS: --test-only';
const ENV_SW = { [SWITCH]: '"1"' }, ENV_BOTH = { [SWITCH]: '"1"', NODE_OPTIONS: '--test-only' };
const ENV_ROWS = [
  { what: 'NODE_OPTIONS after a blank line, read', lines: ['        env:', ENV_ON, '', ENV_NO], env: ENV_BOTH, refused: [] },
  { what: 'NODE_OPTIONS after a quoted block-scalar key and its text line, both refused', lines: ['        env:', ENV_ON, '          "NOTE": |', '            a text line', ENV_NO], env: ENV_BOTH, refused: ['          "NOTE": |', '            a text line'] },
  { what: 'NODE_OPTIONS after a key whose colon ends its line and its value line, both refused', lines: ['        env:', ENV_ON, '          NOTE:', '            a value', ENV_NO], env: ENV_BOTH, refused: ['          NOTE:', '            a value'] },
  { what: 'a quoted NODE_OPTIONS key, refused', lines: ['        env:', ENV_ON, '          "NODE_OPTIONS": --test-only'], env: ENV_SW, refused: ['          "NODE_OPTIONS": --test-only'] },
  { what: 'a YAML merge key, refused', lines: ['        env:', ENV_ON, '          <<: *x'], env: ENV_SW, refused: ['          <<: *x'] },
  { what: 'NODE_OPTIONS after a line of four spaces alone, which is blank, read', lines: ['        env:', ENV_ON, '    ', ENV_NO], env: ENV_BOTH, refused: [] },
  { what: 'NODE_OPTIONS after a line of whitespace holding a tab, which is blank, read', lines: ['        env:', ENV_ON, '  \t  ', ENV_NO], env: ENV_BOTH, refused: [] },
  { what: 'NODE_OPTIONS after a block-scalar key read with its indicator as the value and its text line refused', lines: ['        env:', ENV_ON, '          NOTE: |', '            a text line', ENV_NO], env: { ...ENV_BOTH, NOTE: '|' }, refused: ['            a text line'] },
  { what: 'a folded block-scalar indicator with a modifier, read as the value', lines: ['        env:', ENV_ON, '          FOO: >-'], env: { ...ENV_SW, FOO: '>-' }, refused: [] },
  { what: 'a # line inside a block scalar\'s text, neither read nor refused', lines: ['        env:', ENV_ON, '          NOTE: |', '            # text that YAML reads as text'], env: { ...ENV_SW, NOTE: '|' }, refused: [] },
  { what: 'a colon followed by a space alone, an empty value', lines: ['        env:', ENV_ON, '          NOTE: '], env: { ...ENV_SW, NOTE: '' }, refused: [] },
  { what: 'a key led by _ and holding digits, read', lines: ['        env:', ENV_ON, '          _A1: x'], env: { ...ENV_SW, _A1: 'x' }, refused: [] },
  { what: 'a value with spaces around it, trimmed', lines: ['        env:', ENV_ON, '          A:   x  '], env: { ...ENV_SW, A: 'x' }, refused: [] },
  { what: 'a key led by a digit, refused', lines: ['        env:', ENV_ON, '          1A: x'], env: ENV_SW, refused: ['          1A: x'] },
  { what: 'a key holding a hyphen, refused', lines: ['        env:', ENV_ON, '          NODE-OPTIONS: x'], env: ENV_SW, refused: ['          NODE-OPTIONS: x'] },
  { what: 'a key holding a dot, refused', lines: ['        env:', ENV_ON, '          a.b: x'], env: ENV_SW, refused: ['          a.b: x'] },
  { what: 'a single-quoted key, refused', lines: ['        env:', ENV_ON, '          \'NODE_OPTIONS\': x'], env: ENV_SW, refused: ['          \'NODE_OPTIONS\': x'] },
  { what: 'a key with a space before its colon, refused', lines: ['        env:', ENV_ON, '          NODE_OPTIONS : x'], env: ENV_SW, refused: ['          NODE_OPTIONS : x'] },
  { what: 'a line of nine spaces, refused', lines: ['        env:', ENV_ON, '         NODE_OPTIONS: x'], env: ENV_SW, refused: ['         NODE_OPTIONS: x'] },
  { what: 'a line of eleven spaces, refused', lines: ['        env:', ENV_ON, '           NODE_OPTIONS: x'], env: ENV_SW, refused: ['           NODE_OPTIONS: x'] },
  { what: 'a line led by a tab, refused', lines: ['        env:', ENV_ON, '\tNODE_OPTIONS: x'], env: ENV_SW, refused: ['\tNODE_OPTIONS: x'] },
  { what: 'a line led by four spaces and a tab, refused and not the end of the block', lines: ['        env:', ENV_ON, '    \tNODE_OPTIONS: x', ENV_NO], env: ENV_BOTH, refused: ['    \tNODE_OPTIONS: x'] },
  { what: 'a # line at two spaces and one at eight, neither the end of the block', lines: ['        env:', ENV_ON, '  # a comment', '        # a comment', ENV_NO], env: ENV_BOTH, refused: [] },
  { what: 'a line of eight spaces ends the block, and a key after it is neither read nor refused', lines: ['        env:', ENV_ON, '        timeout-minutes: 5', ENV_NO], env: ENV_SW, refused: [] },
  { what: 'an env line with spaces after its colon opens the block', lines: ['        env:  ', ENV_ON], env: ENV_SW, refused: [] },
  { what: 'an env line of ten spaces, under with:, is not the step\'s env', lines: ['        with:', '          env:', '            NODE_OPTIONS: x'], env: {}, refused: [] },
  { what: 'an inline mapping after env:, refused', lines: ['        env: { NODE_OPTIONS: --test-only }'], env: {}, refused: ['        env: { NODE_OPTIONS: --test-only }'] },
  { what: 'a comment after env:, refused, its block read', lines: ['        env: # the switch', ENV_ON], env: ENV_SW, refused: ['        env: # the switch'] },
  { what: 'an alias after env:, refused', lines: ['        env: *x'], env: {}, refused: ['        env: *x'] },
  { what: 'a second env line, refused, its block read', lines: ['        env:', ENV_ON, '        timeout-minutes: 5', '        env:', ENV_NO], env: ENV_BOTH, refused: ['        env:'] },
];
test('the env reader\'s table: each row\'s env and refused lines read as steps()\' docstring states', () => {
  const wrong = [];
  for (const row of ENV_ROWS) {
    const [s] = steps({ lines: ['      - name: S', ...row.lines, '        run: x'] });
    const got = { env: s.env, refused: s.envRefused }, want = { env: row.env, refused: row.refused };
    if (!isDeepStrictEqual(got, want)) wrong.push(row.what + ': steps() over ' + JSON.stringify(row.lines) + ' reads ' + JSON.stringify(got) + ', not ' + JSON.stringify(want));
  }
  assert.deepEqual(wrong, [], 'each row of the env reader\'s table is read as steps()\' docstring states; the rows read otherwise: ' + JSON.stringify(wrong));
});
function extensionJob() {
  const hits = jobs(read(CI)).filter((j) => j.key === JOB);
  assert.equal(hits.length, 1, 'ci.yml has one ' + JOB + ' job');
  return hits[0];
}
/** The job's cap in minutes, read from the first of its lines of four spaces, `timeout-minutes: ` and digits alone, so a
 *  step's, at eight spaces, is not read (asserted present, not skipped: a matrix expression here needs the pins that
 *  derive from the cap re-anchored). */
function jobCap(job) {
  const capLine = job.lines.find((l) => /^    timeout-minutes: \d+$/.test(l));
  assert.ok(capLine, 'the ' + JOB + ' job has one plain timeout-minutes line (a matrix expression here needs this pin re-anchored, not skipped)');
  return { cap: Number(/(\d+)$/.exec(capLine)[1]), capLine };
}

/** The tokens of a comment read as file paths, over the comment with its line breaks and # markers folded to one space: a
 *  token of letters, digits, _, . and - joined by /, each segment beginning with a letter and the last ending in a suffix
 *  that begins with a letter (\.[A-Za-z][\w-]*), not preceded by a word character, ., /, <, > or -. A path of another
 *  shape is not read, so it is not checked: one with no such suffix (a directory, out-tests/), a leading ../ or /, a
 *  segment beginning with ., _, - or a digit (.github/workflows/x.yml, vscode-extension/.x, upstream/2026-x.md). A token
 *  ends where a word ends, whatever follows it, so the leading part of a longer path is read, and checked, when it has the
 *  shape: a/b.c/d/ is read as a/b.c, and docs/notes.d/readme as docs/notes.d. A path holding a character outside the
 *  token's (@, +, $, ~, a backslash, among others) is read as the pieces that character splits it into, each read only
 *  when it has the shape on its own: node_modules/@scope/x/index.js is read as scope/x/index.js, and that piece is
 *  checked as a path. A piece right after < or > is not read, since the token may not follow either (a<b/c.ts reads
 *  nothing). Beyond paths, a letter-led word with a dot and a letter-led suffix is read too (a member name, a
 *  Latin abbreviation), a loud red where the tree holds no such file. Its table: PATH_TOKEN_ROWS, run by the test after
 *  it, and the row the first test runs before it reads the step comment. */
const PATH_TOKEN = /(?<![\w.\/<>-])(?:[A-Za-z][\w.-]*\/)*[A-Za-z][\w-]*(?:\.[\w-]+)*\.[A-Za-z][\w-]*\b/g;
const commentPaths = (comment) => [...comment.replace(/\n\s*#\s?/g, ' ').matchAll(PATH_TOKEN)].map((m) => m[0]);
/** PATH_TOKEN's table: each row a comment's text and the tokens commentPaths reads from it, one spelling inside and one
 *  outside each family its docstring names. */
const PATH_TOKEN_ROWS = [
  ['a path of letter-led segments whose last suffix begins with a letter', 'see a/b.toml here', ['a/b.toml']],
  ['a figure, whose suffix begins with a digit', 'measured at 1.86 s', []],
  ['a word whose suffix begins with a digit', 'node a.22 here', []],
  ['a directory', 'out-tests/', []],
  ['a file under that directory', 'out-tests/x.js', ['out-tests/x.js']],
  ['a ../ lead', '../ui/x.ts', []],
  ['the same path with no lead', 'ui/x.ts', ['ui/x.ts']],
  ['a / lead', '/etc/x.conf', []],
  ['the same path with no / lead', 'etc/x.conf', ['etc/x.conf']],
  ['a segment that begins with .', '.github/workflows/x.yml', []],
  ['the same path with its segment letter-led', 'github/workflows/x.yml', ['github/workflows/x.yml']],
  ['a segment that begins with _', '_build/x.ts', []],
  ['a segment that begins with -', '-x/y.ts', []],
  ['a segment that begins with a digit', 'upstream/2026-x.md', []],
  ['the digits later in the segment', 'upstream/x-2026.md', ['upstream/x-2026.md']],
  ['a piece right after <', 'a<b/c.ts', []],
  ['a piece right after >', 'a>b/c.ts', []],
  ['the same piece after a space', 'a b/c.ts', ['b/c.ts']],
  ['the leading part of a longer path that has the shape', 'a/b.c/d/', ['a/b.c']],
  ['the longer path when it has the shape whole', 'a/b.c/d.e', ['a/b.c/d.e']],
  ['a path split by @, read as the piece after it', 'node_modules/@scope/x/index.js', ['scope/x/index.js']],
  ['a path split by @ between two pieces of the shape', 'x/y.ts@z/w.ts', ['x/y.ts', 'z/w.ts']],
  ['a member name', 'Promise.allSettled', ['Promise.allSettled']],
  ['the object alone', 'Promise', []],
  ['a Latin abbreviation', 'e.g. a case', ['e.g']],
  ['a path across a comment\'s line break and # marker', 'the file\n# a/b.toml', ['a/b.toml']],
];
test('PATH_TOKEN\'s table: each row\'s tokens read as PATH_TOKEN\'s docstring states', () => {
  const wrong = PATH_TOKEN_ROWS.filter(([, text, reads]) => !isDeepStrictEqual(commentPaths(text), reads))
    .map(([what, text, reads]) => what + ': commentPaths(' + JSON.stringify(text) + ') reads ' + JSON.stringify(commentPaths(text)) + ', not ' + JSON.stringify(reads));
  assert.deepEqual(wrong, [], 'each row of PATH_TOKEN\'s table is read as its docstring states; the rows read otherwise: ' + JSON.stringify(wrong));
});

test('the step exists once in the ' + JOB + ' job, directly after the Chromium install step, with the switch, the run line and the job\'s default working directory, and every path PATH_TOKEN reads (its docstring) in its comment is in the tree', () => {
  const job = extensionJob();
  const all = steps(job);
  const names = all.map((s) => s.name);
  assert.equal(names.filter((n) => n === STEP).length, 1, 'exactly one step named ' + JSON.stringify(STEP) + '; the job\'s steps: ' + JSON.stringify(names));
  assert.equal(names.filter((n) => n === INSTALL).length, 1, 'exactly one step named ' + JSON.stringify(INSTALL));
  const at = names.indexOf(STEP), install = names.indexOf(INSTALL), testAt = names.indexOf(TEST_STEP);
  assert.ok(testAt >= 0, 'the job has a step named ' + TEST_STEP);
  assert.equal(at, install + 1, 'the step is directly after the Chromium install step, by the two steps\' places among the job\'s steps (the legs need the browser it installs); order: ' + JSON.stringify(names));
  assert.ok(install > testAt, 'the Chromium install step is placed after the Test step, by the two steps\' places (an install or a cache before the Test step is the install pin\'s read, its docstring)');
  const step = all[at];
  assert.deepEqual(step.envRefused, [], 'the step\'s env block holds no line the env reader refuses (its docstring in tools/ci-browser-legs.test.mjs states what it reads and what it refuses), each named here: ' + JSON.stringify(step.envRefused));
  assert.deepEqual(step.env, { [SWITCH]: '"1"' }, 'the step\'s env, as the env reader reads it (its docstring in tools/ci-browser-legs.test.mjs states what it reads and what it refuses), is the switch alone, set to "1"');
  assert.equal(step.fields.run, RUN_LINE, 'the run line calls the script, which runs node --test over the roster');
  assert.ok(!('working-directory' in step.fields), 'no working-directory field among the step\'s fields (steps() states what it reads): the roster, the script and out-tests/ are under the job\'s default, vscode-extension/');
  assert.match(job.lines.join('\n'), /^    defaults:\n      run:\n        working-directory: vscode-extension$/m, 'the job\'s default working directory is vscode-extension');
  const comment = step.comments.join('\n');
  // the three numbers are a property of the comment, not a spelling: a step duration in seconds, a job duration in minutes and the
  // job's cap, read from the job's own timeout-minutes line so a raised cap turns a stale sentence red (a lowered one is already
  // red in tests/test_ci_bats_bound.py::ExtensionJobCeiling, which floors the cap at 40; this pin is about the SENTENCE matching
  // the line, not about the cap's value); all three measured on the runner (the first run's placeholder held none of them, and
  // the pin that accepted it by its spelling was the kind that lets a filled sentence go red for its wording)
  const { cap } = jobCap(job);
  // the step comment read for the text "measured on the runner"
  assert.ok(/measured on the runner/.test(comment), 'the step\'s comment says its numbers were measured on the runner');
  // the step comment read for a figure of digits, a space and s, a word boundary at each end
  assert.ok(/\b\d+ s\b/.test(comment), 'the step\'s comment carries the step\'s seconds');
  // the step comment's first figure of digits, a space and min, a word boundary at each end
  const minutes = /\b(\d+) min\b/.exec(comment);
  assert.ok(minutes, 'the step\'s comment carries the job\'s minutes');
  // the step comment read for the cap jobCap reads, then -minute cap, a word boundary at each end
  assert.ok(new RegExp('\\b' + cap + '-minute cap\\b').test(comment), 'the comment names the job\'s cap as ci.yml sets it (' + cap + ' minutes): a cap change rewrites the sentence; this pin holds the sentence to the line, whatever the cap, while a LOWERED cap is tests/test_ci_bats_bound.py::ExtensionJobCeiling\'s red (it floors the cap at 40): two guards, two properties');
  assert.ok(Number(minutes[1]) < cap, 'the stated job minutes (' + minutes[1] + ') sit under the cap (' + cap + ')');
  assert.ok(comment.includes(ROSTER), 'the comment names the roster');
  // every path PATH_TOKEN reads (its docstring) in the comment is in the tree, resolved from the repository root or from
  // vscode-extension/ (the job's default working directory, which the comment's scripts/ paths are relative to), so a
  // comment that points a reader at a file the tree no longer holds, by a path PATH_TOKEN reads, is red here, and a path
  // it does not read is not checked. The step comment spells no member name, which PATH_TOKEN reads as a path too (its
  // docstring), a red here naming it: the roster rule's words there name allSettled, and ending the process, without the
  // object
  assert.deepEqual(commentPaths('# the lockfile vscode-extension/package-lock.json, a/b.toml and c.css,\n# measured at 1.86 s'), ['vscode-extension/package-lock.json', 'a/b.toml', 'c.css'], 'PATH_TOKEN reads this row\'s three paths, the .json, .toml and .css suffixes alike, across its line break, and not its figure 1.86 (a reader keyed on a list of suffixes goes silent at the next suffix)');
  const named = commentPaths(comment);
  assert.ok(named.length > 0, 'the comment names files by path (none read means PATH_TOKEN stopped matching, or the comment names no path it reads)');
  const gone = named.filter((p) => !fs.existsSync(path.join(REPO, p)) && !fs.existsSync(path.join(EXT, p)));
  assert.deepEqual(gone, [], 'the step\'s comment names a file the tree does not hold (from the repository root or from vscode-extension/): ' + JSON.stringify(gone) + '; the paths read: ' + JSON.stringify(named));
  assert.ok(!step.lines.join('\n').includes(String.fromCharCode(0x2014)), 'no em dash');
});

/** The per-file bound the script passes node, in ms, read from the script's text, a comment included (one --test-timeout=
 *  spelling with digits, asserted, so a second one anywhere in the script is red here). */
function testTimeoutMs() {
  const m = read(SCRIPT).match(/--test-timeout=(\d+)/g) || [];
  assert.equal(m.length, 1, 'the script passes node --test one --test-timeout: ' + JSON.stringify(m));
  return Number(m[0].slice('--test-timeout='.length));
}
/** The bound pin's reds over rostered sources ([{ bundle, src, text }]) against node's per-file bound `ms`. It reads the
 *  source as text, by two patterns. The first reads the word timeout bare or between quotes (' or ", each quote
 *  optional), the word not preceded by a word character or $, or a bracketed ', " or ` string holding the word alone
 *  (whitespace allowed inside the brackets), the bracket not preceded by a word character or $, either followed by only
 *  whitespace and a colon, wherever it stands in the source: in a comment, a string, a ternary, a label or a type
 *  annotation it is read too, and refused or held to the bound, a loud red. Its value token runs from the colon to the
 *  next comma, closing brace or closing parenthesis, or to the end of the source, trimmed. A token of digits, with _
 *  separators or none (/^\d[\d_]*$/), is read with its separators removed, and is red when it reaches the file bound.
 *  Any other token (an exponent spelling, an identifier, an expression, a value with a comment after it) is red naming
 *  the bundle, the source and the token, with the remedy to spell the value as a literal. The second reads the word
 *  timeout with only whitespace between it and a preceding { or , and a following , or }, a shorthand property
 *  ({ timeout }, the value a name in scope), which spells no value to read and is refused the same way (a call argument, a
 *  destructuring or an import binding of that shape is refused as a shorthand too). A Playwright call's own timeout:
 *  option is read by the same rule: a per-call bound above the file bound is a real cut too. Any other spelling of a key
 *  is not read, so its value is not held by this pin: among them a comment between the key and its colon or beside a
 *  shorthand, and a key computed by concatenation. A leg that spells its timeout so meets in the step what any leg meets
 *  whose file runs past the file bound, whatever its own timeout says and however it is spelled: node cancels the file
 *  at the bound, and the script prints its failed-as-a-whole red naming the bundle and testTimeoutFailure, not the test.
 *  Its table: BOUND_ROWS, run by the test after it, and the rows the bound test runs against the script's own bound. */
function boundReds(sources, ms) {
  const reds = [];
  const literal = ', which this pin cannot read as a number: spell the value as a literal (digits, _ separators allowed), so it is held under node\'s --test-timeout';
  for (const s of sources) {
    for (const m of s.text.matchAll(/(?<![\w$])(?:\[\s*(['"`])timeout\1\s*\]|['"]?timeout['"]?)\s*:([^,})]*)/g)) {
      const token = m[2].trim(), at = s.bundle + ' (source ' + s.src + ') spells timeout: ' + token;
      if (!/^\d[\d_]*$/.test(token)) reds.push(at + literal);
      else if (Number(token.replace(/_/g, '')) >= ms) reds.push(at + ' (' + Number(token.replace(/_/g, '')) + ' ms), which reaches node\'s --test-timeout (' + ms + ' ms): the file bound would cut the leg before its own bound fires, so raise --test-timeout in the script (under the step\'s bound) or lower the value');
    }
    for (let i = (s.text.match(/(?<=[{,]\s*)timeout(?=\s*[,}])/g) || []).length; i > 0; i--) reds.push(s.bundle + ' (source ' + s.src + ') spells timeout as a shorthand property ({ timeout })' + literal);
  }
  return reds;
}

/** boundReds' table: each row a source's text and the reds boundReds gives it against a bound of 240000 ms, the value
 *  300000 above it where the row spells one, so a row read is red and a row not read is not: `reds` counts them, and `kind`
 *  names the red of a read row (over, the value reaches the bound; literal, the token is refused; shorthand), one spelling
 *  inside and one outside each family its docstring names. */
const BOUND_ROWS = [
  ['the bare word', '{ timeout: 300000 }', 1, 'over'],
  ['a longer word', '{ timeoutMs: 300000 }', 0],
  ['the word between single quotes', "{ 'timeout': 300000 }", 1, 'over'],
  ['the word between double quotes, a space before the colon', '{ "timeout" : 300000 }', 1, 'over'],
  ['the word between two different quotes', '{ \'timeout": 300000 }', 1, 'over'],
  ['a bracketed double-quoted string', '{ ["timeout"]: 300000 }', 1, 'over'],
  ['a bracketed template string with whitespace inside the brackets', '{ [ `timeout` ]: 300000 }', 1, 'over'],
  ['a bracketed name', '{ [timeout]: 300000 }', 0],
  ['a bracketed string whose quotes differ', '{ [\'timeout"]: 300000 }', 0],
  ['the word directly after $', '{ $timeout: 300000 }', 0],
  ['the word directly after a word character', '{ xtimeout: 300000 }', 0],
  ['the word after a dot, a member access', 'a.timeout: 300000', 1, 'over'],
  ['the bracket directly after a word character, in a comment', '// opts["timeout"]: 300000', 0],
  ['the bracket after a space, in a comment', '// opts ["timeout"]: 300000', 1, 'over'],
  ['the word in a comment', '// timeout: 300000', 1, 'over'],
  ['the word in a string, the closing quote in the token', '"x timeout: 300000"', 1, 'literal'],
  ['the word after a quote that follows a word character', "x'timeout': 300000", 1, 'over'],
  ['the word in a ternary', 'c ? timeout : 300000', 1, 'over'],
  ['a comment between the key and its colon', '{ timeout /* a comment */: 300000 }', 0],
  ['a key built by concatenation', '{ ["time" + "out"]: 300000 }', 0],
  ['a separator spelling above the bound, read whole', '{ timeout: 300_000 }', 1, 'over'],
  ['a separator spelling under the bound', '{ timeout: 1_000 }', 0],
  ['a value with a comment after it', '{ timeout: 300000 /* ms */ }', 1, 'literal'],
  ['a value that runs to the end of the source', 'timeout: 300000', 1, 'over'],
  ['a shorthand property', '{ timeout }', 1, 'shorthand'],
  ['a shorthand between two others', '{ a, timeout, b }', 1, 'shorthand'],
  ['a longer shorthand name', '{ timeouts }', 0],
  ['a comment beside a shorthand', '{ timeout /* a comment */ }', 0],
  ['a call argument of the shorthand\'s shape', 'f(a, timeout, b)', 1, 'shorthand'],
  ['a call argument before the closing parenthesis', 'f(a, timeout)', 0],
];
test('boundReds\' table: each row read or not read as boundReds\' docstring states', () => {
  const KIND = { over: 'which reaches node\'s --test-timeout', literal: 'which this pin cannot read as a number', shorthand: 'spells timeout as a shorthand property' };
  const wrong = [];
  for (const [what, text, count, kind] of BOUND_ROWS) {
    const reds = boundReds([{ bundle: 'out-tests/ui/webview/probe-browser.test.js', src: 'ui/webview/probe-browser.test.ts', text }], 240000);
    if (!(reds.length === count && (!kind || reds[0].includes(KIND[kind])))) wrong.push(what + ': boundReds over ' + JSON.stringify(text) + ' gives ' + JSON.stringify(reds) + ', not ' + (count ? 'one red (' + kind + ')' : 'no red'));
  }
  assert.deepEqual(wrong, [], 'each row of boundReds\' table is read or not read as its docstring states; the rows read otherwise: ' + JSON.stringify(wrong));
});

test('the step is bounded twice: its own timeout-minutes fits the margin under the job\'s cap at the measured head and the job\'s comment names that number; node\'s --test-timeout in the script sits above the timeout: values the bound pin reads in a rostered source (boundReds\' docstring) and under the step\'s bound, so a hung leg fails by name before the step is cut', () => {
  const job = extensionJob();
  const { cap, capLine } = jobCap(job);
  const step = steps(job).find((s) => s.name === STEP);
  assert.ok(step, 'the step exists (the first test holds the rest of its shape)');
  const bound = Number(step.fields['timeout-minutes']);
  assert.ok(Number.isInteger(bound) && bound >= 1, 'the step carries a timeout-minutes of its own (a roster whose legs exceed it fails this step by name rather than cancelling the job nameless): ' + JSON.stringify(step.fields['timeout-minutes']));
  // the margin the bound must fit: the job's measured minutes and seconds in the step's own comment, under the cap
  const comment = step.comments.join('\n');
  // the step comment's first "in a job of N min N s", N digits, with no word boundary after its s
  const took = /in a job of (\d+) min (\d+) s/.exec(comment);
  assert.ok(took, 'the step\'s comment states the measured job time as "in a job of N min N s"');
  const marginSeconds = cap * 60 - (Number(took[1]) * 60 + Number(took[2]));
  assert.ok(bound * 60 <= marginSeconds, 'the step\'s bound (' + bound + ' min) fits the margin under the cap at the measured head (' + marginSeconds + ' s): a step that runs to its bound still ends the job under ' + cap + ' minutes; a larger roster raises the bound and the cap together; a job whose other phases grow under an unchanged cap re-measures the margin the same way');
  // the step comment read for the text "re-measures here" alone, not for what the sentence around it says (a negation
  // passes it)
  assert.ok(comment.includes('re-measures here'), 'the step\'s comment contains the phrase "re-measures here", the words of its re-measure condition for growth outside the roster (the job\'s other phases toward the cap)');
  // the job's cap comment: its # lines before its cap line, read for the step's bound, then " minutes (its
  // timeout-minutes)", a word boundary before the number
  const jobComment = job.lines.slice(0, job.lines.indexOf(capLine)).filter((l) => /^\s*#/.test(l)).join('\n');
  assert.ok(new RegExp('\\b' + bound + ' minutes \\(its timeout-minutes\\)').test(jobComment), 'the job\'s cap comment names the step\'s bound, "' + bound + ' minutes (its timeout-minutes)": a changed bound rewrites the sentence');
  // the job comment's passage about this step: over the cap comment above, folded at its line breaks and # markers to
  // one space, the text from the first "The Browser legs step below" to the next "in the same PR.". It is read for this
  // file's name, where the margin is derived, and for no figure in the two spellings the step comment gives the measured
  // job time and the margin: N min N s (digits, a space, min, a space, digits, a space and s) and N s (digits, a space and
  // s, a word boundary at each end). The measured time has one home, the step comment above. A figure spelled otherwise
  // (12 minutes) is not read, and the N min N s pattern, with no word boundary after its s, also reads N min N before any
  // word that begins with s (12 min 30 seconds, 2 min 3 sessions), a loud red (the job comment's other sentences record
  // the served step's own history and are not read here)
  const about = /The Browser legs step below[\s\S]*?in the same PR\./.exec(jobComment.replace(/\n\s*#\s?/g, ' '));
  assert.ok(about, 'the job comment holds one passage about the Browser legs step, from "The Browser legs step below" to "in the same PR."');
  assert.ok(!/\d+ min \d+ s/.test(about[0]) && !/\b\d+ s\b/.test(about[0]), 'the job comment\'s passage about this step carries a figure of the measured job time or the margin, whose one home is the step comment: ' + JSON.stringify((about[0].match(/\d+ min \d+ s|\b\d+ s\b/) || [''])[0]) + ' in ' + about[0]);
  assert.ok(about[0].includes('tools/ci-browser-legs.test.mjs'), 'that passage names this file as where the margin is derived: ' + about[0]);
  // node's per-file bound: above the timeout: values the bound pin reads in a rostered source (else a legitimate slow leg
  // is cut), under the step's bound (else the step is cut nameless first). First the reader, over synthetic sources against
  // the script's own bound, rows beside BOUND_ROWS (boundReds' docstring states what it reads), each naming itself
  const ms = testTimeoutMs();
  const probe = (text) => boundReds([{ bundle: 'out-tests/ui/webview/probe-browser.test.js', src: 'ui/webview/probe-browser.test.ts', text }], ms);
  const over = ms + 60000;
  const separated = String(over).replace(/\B(?=(\d{3})+$)/g, '_'), exponent = over.toExponential().replace('+', '');
  for (const [text, token, what] of [
    ['test("x", { timeout: ' + separated + ' }, async () => {});', separated, 'a separator spelling above the file bound'],
    ['test("x", { timeout: ' + exponent + ' }, async () => {});', exponent, 'an exponent spelling'],
    ['test("x", { timeout: LEG_TIMEOUT_MS }, async () => {});', 'LEG_TIMEOUT_MS', 'an identifier'],
    ['test("x", { \'timeout\' : ' + separated + ' }, async () => {});', separated, 'a quoted key with a space before its colon'],
    ['test("x", { ["timeout"]: ' + separated + ' }, async () => {});', separated, 'a bracketed string key'],
  ]) {
    const reds = probe(text);
    assert.ok(reds.length === 1 && reds[0].includes('out-tests/ui/webview/probe-browser.test.js') && reds[0].includes('ui/webview/probe-browser.test.ts') && reds[0].includes('timeout: ' + token), 'the bound pin reds ' + what + ' (' + JSON.stringify(text) + '), naming the bundle, the source and the token as spelled: ' + JSON.stringify(reds));
  }
  assert.ok(probe('test("x", { timeout: ' + exponent + ' }, () => {});')[0].includes('spell the value as a literal'), 'a refused token carries the remedy, to spell the value as a literal');
  const shorthand = probe('const timeout = ' + separated + ';\ntest("x", { timeout }, async () => {});');
  assert.ok(shorthand.length === 1 && shorthand[0].includes('out-tests/ui/webview/probe-browser.test.js') && shorthand[0].includes('ui/webview/probe-browser.test.ts') && shorthand[0].includes('a shorthand property ({ timeout })') && shorthand[0].includes('spell the value as a literal'), 'the bound pin refuses a shorthand property ({ timeout }), whose value is a name in scope, naming the bundle and the source, with the remedy to spell the value as a literal: ' + JSON.stringify(shorthand));
  assert.deepEqual(probe('test("x", { timeout: 1_000 }, () => {});\npage.waitForFunction(f, null, { timeout: 5000 });'), [], 'a separator spelling under the file bound, and a Playwright call\'s own timeout: under it, pass');
  const sources = [];
  for (const e of parseRoster(read(path.join(EXT, ROSTER)))) {
    const src = sourceOf(e.bundle);
    if (!fs.existsSync(src)) continue;   // a stale line is the well-formed test's red
    sources.push({ bundle: e.bundle, src: path.relative(REPO, src), text: read(src) });
  }
  assert.deepEqual(boundReds(sources, ms), [], 'the check\'s guarantee: no timeout: value the bound pin reads in a rostered source (boundReds\' docstring) reaches node\'s --test-timeout (' + ms + ' ms). A value spelled outside what it reads is not held here, and its leg meets what any leg whose file outlasts the bound meets: node cancels the file, and the script\'s failed-as-a-whole red names the bundle and testTimeoutFailure, not the test. The file bound cuts a file\'s whole run, so a leg whose timed tests together outlast it is cut all the same: a leg\'s whole-file seconds are measured in the PR\'s body, not here');
  assert.ok(ms < bound * 60 * 1000, 'node\'s --test-timeout (' + ms + ' ms) is under the step\'s bound (' + bound + ' min = ' + bound * 60 * 1000 + ' ms), so a hung file fails by name before the step is cut');
});

/** The install pin: over the steps before the step named Test, as steps() splits the job, it reads a Playwright install
 *  by the union of two reads, so a spelling either reads is read. The first is each step's run field as steps() reads it
 *  (an eight-space `run:` line, or the step's `- run:` opener, its value trimmed) when it begins npx playwright install and
 *  then a word boundary. The second is those steps' code lines (their lines but their # lines, joined) read for run: npx
 *  playwright install and a word boundary after a line's leading whitespace, so a run: nested under with: and a step whose
 *  fields sit at ten spaces are read too. By the word boundary, npx playwright install-deps is read as well. It reads a
 *  Playwright cache from the same code lines, after a line's leading whitespace: path: ~/.cache/ms-playwright with only
 *  whitespace after it, and key: playwright-. A spelling outside them is not read: a run: whose command is on the next
 *  line, another launcher, another key. The code-line patterns are those of the gate-adopt pin in
 *  tools/markdown-viewer-plan-gate-adopt.test.mjs (its installBefore and cacheBefore), but the two pins read different
 *  regions (the gate-adopt pin reads the region its npmTestJob docstring states), differ on the run fields steps() reads
 *  where the code-line pattern does not (the step's `- run:` opener, and more than one space after run:), which this pin
 *  reads and the gate-adopt pin does not, and hold different directions: this pin holds that pin's CI_SKIP direction
 *  alone. Under the plan's CI_RUN sentence the gate-adopt pin requires an install before the Test step, and this pin
 *  refuses any install it reads there, whatever engines it names. Returns the Test step's place and what was read. Its
 *  table: INSTALL_ROWS, run by the test after it. */
function installReads(job) {
  const all = steps(job);
  const testAt = all.findIndex((s) => s.name === TEST_STEP);
  const region = testAt < 0 ? [] : all.slice(0, testAt);
  const before = region.flatMap((s) => s.code).join('\n');
  const install = [
    ...region.filter((s) => /^npx playwright install\b/.test(s.fields.run || '')).map((s) => 'the run field ' + JSON.stringify(s.fields.run)),
    ...[...before.matchAll(/^\s+run: npx playwright install\b.*$/gm)].map((m) => 'the code line ' + JSON.stringify(m[0].trim())),
  ];
  const cache = [...before.matchAll(/^\s+path: ~\/\.cache\/ms-playwright\s*$|^\s+key: playwright-.*$/gm)].map((m) => 'the code line ' + JSON.stringify(m[0].trim()));
  return { testAt, install, cache };
}
/** The install pin's table: each row a job's lines, a step named Test among them, and whether the install pin reads an
 *  install and a cache before that step, one spelling inside and one outside each family its docstring names. */
const TEST_LINES = ['      - name: Test', '        run: npm test'];
const INSTALL_ROWS = [
  ['a named step\'s eight-space run: line, read by both reads', ['      - name: Install', '        run: npx playwright install chromium', ...TEST_LINES], true, false],
  ['an unnamed step\'s "- run:" opener, read through steps()', ['      - run: npx playwright install chromium', ...TEST_LINES], true, false],
  ['a "- run:" opener with a name: line after it, read through steps()', ['      - run: npx playwright install chromium', '        name: Install', ...TEST_LINES], true, false],
  ['two spaces after run:, read through steps()', ['      - name: Install', '        run:  npx playwright install chromium', ...TEST_LINES], true, false],
  ['install-deps, read by the word boundary after install', ['      - name: Deps', '        run: npx playwright install-deps', ...TEST_LINES], true, false],
  ['a longer word than install, not read', ['      - name: Install', '        run: npx playwright installer', ...TEST_LINES], false, false],
  ['a step whose fields sit at ten spaces, read by the code-line pattern', ['      -   name: Install', '          run: npx playwright install chromium', ...TEST_LINES], true, false],
  ['a run: nested under with:, read by the code-line pattern', ['      - uses: actions/x@v1', '        with:', '          run: npx playwright install chromium', ...TEST_LINES], true, false],
  ['a run: whose command is on the next line, not read', ['      - name: Install', '        run: |', '          npx playwright install chromium', ...TEST_LINES], false, false],
  ['another launcher, not read', ['      - name: Install', '        run: pnpm exec playwright install chromium', ...TEST_LINES], false, false],
  ['a # line naming the install, not read (a # line is dropped, and the pattern reads run: after the leading whitespace alone)', ['      - name: A', '        # run: npx playwright install chromium', '        run: echo', ...TEST_LINES], false, false],
  ['an install after the Test step, not read (the steps before it alone)', [...TEST_LINES, '      - name: Install', '        run: npx playwright install chromium'], false, false],
  ['the cache path, read', ['      - uses: actions/cache@v4', '        with:', '          path: ~/.cache/ms-playwright', ...TEST_LINES], false, true],
  ['a longer cache path, not read', ['      - uses: actions/cache@v4', '        with:', '          path: ~/.cache/ms-playwright/chromium', ...TEST_LINES], false, false],
  ['the cache key, read', ['      - uses: actions/cache@v4', '        with:', '          key: playwright-chromium-x', ...TEST_LINES], false, true],
  ['another key, not read', ['      - uses: actions/cache@v4', '        with:', '          key: pw-chromium-x', ...TEST_LINES], false, false],
];
test('the install pin\'s table: each row read or not read as the install pin\'s docstring states', () => {
  const wrong = [];
  for (const [what, lines, install, cache] of INSTALL_ROWS) {
    const r = installReads({ lines });
    if ((r.install.length > 0) !== install || (r.cache.length > 0) !== cache) wrong.push(what + ': the install pin over ' + JSON.stringify(lines) + ' reads the install ' + JSON.stringify(r.install) + ' and the cache ' + JSON.stringify(r.cache) + ', not ' + (install ? 'an install' : 'no install') + ' and ' + (cache ? 'a cache' : 'no cache'));
  }
  assert.deepEqual(wrong, [], 'each row of the install pin\'s table is read or not read as its docstring states; the rows read otherwise: ' + JSON.stringify(wrong));
});
test('no step before the Test step has a Playwright install or cache, as the install pin reads them (its docstring)', () => {
  const job = extensionJob();
  const { testAt, install, cache } = installReads(job);
  assert.ok(testAt > 0, 'the Test step is not the first step');
  assert.deepEqual(install, [], 'no Playwright install before the Test step, as the install pin reads it (its docstring): ' + JSON.stringify(install));
  assert.deepEqual(cache, [], 'no Playwright cache before the Test step, as the install pin reads it (its docstring): ' + JSON.stringify(cache));
  const installStep = steps(job).find((s) => s.name === INSTALL);
  assert.match(installStep.fields.run || '', /^npx playwright install chromium$/, 'the install step installs Chromium alone (the roster rule\'s Chromium, the one engine a rostered leg launches, rests on this)');
});

// ── the roster and the tree ───────────────────────────────────────────────────────────────────────────────

/** A roster line is a bundle path in its canonical spelling: out-tests/<dir>/<name>.test.js with no whitespace, and the
 *  spelling path.posix.normalize leaves unchanged (no empty, . or .. segment). The check reads out-tests/, then any run of
 *  characters with no whitespace, then .test.js, so it also admits a bundle straight under out-tests/ (out-tests/x.test.js),
 *  as the script's well_formed does. Node resolves a bundle to that spelling, so a
 *  line spelled otherwise matches no result of the run, and two spellings of one bundle pass a check keyed on spelling. The
 *  roster test below and the refusal case call this one check; the script's well_formed states it as a segment rule. Its
 *  whitespace is JavaScript's \s and the script's is bash's [[:space:]] in the runner's locale, so the two part on a
 *  non-ASCII space (a no-break space inside a line: bash admits it under C.UTF-8, this check refuses it), a red on one
 *  side. Its table: WELLFORMED_ROWS, run by the test after it, and the refusal case's three non-canonical rows. */
const BUNDLE_SHAPE = /^out-tests\/\S+\.test\.js$/;
const wellFormed = (line) => BUNDLE_SHAPE.test(line) && path.posix.normalize(line) === line;
/** wellFormed's table: each row a line and whether wellFormed admits it, one spelling inside and one outside each family
 *  its docstring names. */
const WELLFORMED_ROWS = [
  ['a bundle path in its canonical spelling', 'out-tests/ui/webview/a-browser.test.js', true],
  ['a bundle straight under out-tests/', 'out-tests/x.test.js', true],
  ['a bundle two directories down', 'out-tests/a/b/c.test.js', true],
  ['a no-break space inside the line', 'out-tests/ui/web\u00a0view/a-browser.test.js', false],
  ['a trailing space', 'out-tests/ui/webview/a-browser.test.js ', false],
  ['a bundle that does not end in .test.js', 'out-tests/ui/webview/a-browser.js', false],
  ['a source path, not under out-tests/', 'ui/webview/a-browser.test.ts', false],
];
test('wellFormed\'s table: each row admitted or refused as wellFormed\'s docstring states', () => {
  const wrong = WELLFORMED_ROWS.filter(([, line, admitted]) => wellFormed(line) !== admitted)
    .map(([what, line, admitted]) => what + ': wellFormed(' + JSON.stringify(line) + ') ' + (admitted ? 'refuses it' : 'admits it'));
  assert.deepEqual(wrong, [], 'each row of wellFormed\'s table is admitted or refused as its docstring states; the rows read otherwise: ' + JSON.stringify(wrong));
});
/** A bundle's source, the tree test's copy of the script's source_of (whose home, the script's header, states the map). */
const sourceOf = (bundle) => path.join(REPO, bundle.replace(/^out-tests\//, '').replace(/\.test\.js$/, '.test.ts'));
/** Roster lines: [{ n, bundle }], n the line's number from 1, a line of whitespace alone (an empty one among them) and one
 *  whose first non-blank character is # dropped, blank by \s, which counts a byte-order mark and a no-break space where
 *  the script's [[:space:]] does not: a line holding one of those before its # is dropped here and refused as malformed
 *  by the script. Every other line is kept whole, a # after its first non-blank character included. Its table:
 *  PARSE_ROSTER_ROWS, run by the test after it. */
function parseRoster(text) {
  return text.split('\n').map((line, i) => ({ n: i + 1, line })).filter(({ line }) => !/^\s*(#|$)/.test(line)).map(({ n, line }) => ({ n, bundle: line }));
}
/** parseRoster's table: each row a roster's text and the lines parseRoster keeps, one spelling inside and one outside each
 *  family its docstring names. */
const PARSE_ROSTER_ROWS = [
  ['a # line', '# a comment', []],
  ['an indented # line', '   # a comment', []],
  ['an empty line', '', []],
  ['a line of whitespace alone', ' \t ', []],
  ['a byte-order mark before the #', '\ufeff# a comment', []],
  ['a no-break space before the #', '\u00a0# a comment', []],
  ['a line of text', 'out-tests/x.test.js', [{ n: 1, bundle: 'out-tests/x.test.js' }]],
  ['a line of text with a # after it, kept whole', 'out-tests/x.test.js # a note', [{ n: 1, bundle: 'out-tests/x.test.js # a note' }]],
  ['kept lines numbered from 1 across the dropped ones', 'a\n# c\n\nb\n', [{ n: 1, bundle: 'a' }, { n: 4, bundle: 'b' }]],
];
test('parseRoster\'s table: each row\'s lines kept or dropped as parseRoster\'s docstring states', () => {
  const wrong = PARSE_ROSTER_ROWS.filter(([, text, kept]) => !isDeepStrictEqual(parseRoster(text), kept))
    .map(([what, text, kept]) => what + ': parseRoster(' + JSON.stringify(text) + ') keeps ' + JSON.stringify(parseRoster(text)) + ', not ' + JSON.stringify(kept));
  assert.deepEqual(wrong, [], 'each row of parseRoster\'s table is kept or dropped as its docstring states; the rows read otherwise: ' + JSON.stringify(wrong));
});
/** A line's place, for the reds below that name a line with its bundle: "<file> line <n> (<bundle>)". */
const where = (file, e) => file + ' line ' + e.n + ' (' + e.bundle + ')';

test('the roster is well formed: each line parseRoster keeps (its docstring) is a bundle path naming a source in the tree, once (the roster rule, under the switch, a rostered leg passes only when inBrowser has launched Chromium, with the rest in its homes, is the reviewer\'s to check: nothing in the tree reads a leg\'s source for it)', () => {
  const roster = parseRoster(read(path.join(EXT, ROSTER)));
  assert.ok(roster.length > 0, ROSTER + ' holds at least one line (the switch test is rostered, below): an empty roster would pass the loop below over nothing');
  const seen = new Map();
  for (const e of roster) {
    assert.ok(wellFormed(e.bundle), ROSTER + ' line ' + e.n + ' (' + JSON.stringify(e.bundle) + '): a line is a bundle path in its canonical spelling, out-tests/<dir>/<name>.test.js with no whitespace and no empty, . or .. segment (a bundle path as wellFormed reads it, its docstring; a trailing space, tab or carriage return counts; the quoting shows it)');
    assert.ok(!seen.has(e.bundle), where(ROSTER, e) + ' duplicates line ' + seen.get(e.bundle) + ': remove one');
    seen.set(e.bundle, e.n);
    const src = sourceOf(e.bundle);
    assert.ok(fs.existsSync(src), where(ROSTER, e) + ' names ' + path.relative(REPO, src) + ', which is not in the tree (the source moved or was deleted): fix the line');
  }
});

/** The script's header: the lines after the shebang up to the first line that does not begin with # in its first column
 *  (an indented comment or a blank line ends it), the one slice the header test below and the homes pin read. */
const scriptHeaderLines = (src) => {
  const lines = src.split('\n').slice(1);
  const end = lines.findIndex((l) => !l.startsWith('#'));
  return lines.slice(0, end < 0 ? lines.length : end);
};
/** The roster rule's homes, each read in its named section: the roster's # lines, the Browser legs step's own comments in
 *  ci.yml (the one step of that name, asserted), the script's header (scriptHeaderLines) and CONTRIBUTING.md whole. The homes
 *  pin folds each section's line breaks and comment markers to one space, drops backticks and compares without case, so a
 *  rewrap or a capitalised lead-in is not a reword, while the same words moved out of the section are. */
const RULE_HOMES = [
  { file: path.join(EXT, ROSTER), section: 'its # lines', read: (text) => text.split('\n').filter((l) => /^\s*#/.test(l)).join('\n') },
  { file: CI, section: 'the Browser legs step\'s own comments', read: () => {
    const hits = steps(extensionJob()).filter((s) => s.name === STEP);
    assert.equal(hits.length, 1, 'ci.yml\'s ' + JOB + ' job has one step named ' + JSON.stringify(STEP) + ', whose own comments are the home of the roster rule read here');
    return hits[0].comments.join('\n');
  } },
  { file: SCRIPT, section: 'its header, the lines after the shebang up to the first that does not begin with #', read: (text) => scriptHeaderLines(text).join('\n') },
  { file: path.join(REPO, 'CONTRIBUTING.md'), section: 'the whole file', read: (text) => text },
];
/** A stand-in for inBrowser, spelled as its cannot() is: under the switch it fails with the phrase the script reads a lost
 *  browser by and a reason, and without the switch it skips. The catch example awaits it inside a try, and the witness
 *  test's control awaits it with no try. Nothing here reads cannot() in ui/webview/real-viewer-leg.ts, so a PR that changes
 *  cannot() rewrites this stand-in to match and re-reads the catch example in the homes: with process.exitCode = 1 added to
 *  cannot(), for example, a real leg that catches the rejection is red as failed as a whole while this witness stays green. */
const standIn = (phrase) => 'const assert = require("node:assert");\nconst inBrowser = async (t, body) => { const why = "no playwright browser on this box (a synthetic stand-in)"; if (process.env.' + SWITCH + ') assert.fail(' + JSON.stringify(phrase + ': ') + ' + why); t.skip(why); };\n';
/** The roster rule's examples, each with its synthetic witness leg, in one table: RULE_WORDS takes each example's phrase from
 *  here, the homes pin holds each home's list after "examples, not the whole set:" to exactly these phrases, and the witness
 *  test below rosters each leg, a plain CommonJS bundle (the Shell job has no node_modules and runs no esbuild). So an example
 *  named with no witness, or a witness removed while its example is still named, is red in the homes pin. `leg(phrase)` is
 *  the bundle's test code, handed the phrase the script reads a lost browser by; `marked` says what the mark a leg writes
 *  beside its bundle proves (null for the leg with no failure to mark), and `markBegins` asks that the mark begin with the phrase. */
const EXAMPLES = [
  { phrase: 'a rostered leg that launches its own browser and swallows a failed launch without skipping', name: 'own-launch', marked: 'the own launch threw',
    leg: () => 'test("opens a page", async () => { let browser = null; try { browser = await (async () => { throw new Error("browserType.launch: a synthetic launch that fails"); })(); } catch (e) { fs.writeFileSync(__filename + ".mark", String(e.message)); } if (!browser) return; });\n' },
  { phrase: 'a rostered module that launches nothing', name: 'launches-nothing', marked: null,
    leg: () => 'test("a source pin", () => { if ("a".length !== 1) throw new Error("unreachable"); });\n' },
  { phrase: 'a leg that drives a browser from a child process and tolerates the child\'s failure', name: 'child-tolerated', marked: 'the child exited 3',
    leg: () => 'test("drives a page from a child", () => { const r = spawnSync(process.execPath, ["-e", "process.exit(3)"]); if (r.status !== 0) fs.writeFileSync(__filename + ".mark", String(r.status)); });\n' },
  { phrase: 'a todo test that passes beside a real pass', name: 'todo-beside', marked: 'the todo body ran',
    leg: () => 'test("a real pass", () => {});\ntest("the browser part", { todo: "a synthetic todo" }, () => { fs.writeFileSync(__filename + ".mark", "ran"); });\n' },
  { phrase: 'a leg that catches inBrowser\'s rejection and passes (a try and catch around the awaited call, .catch(), .then\'s second argument or Promise\'s allSettled)', name: 'catches-rejection',
    marked: 'the stand-in for inBrowser rejected under the switch and the catch took the rejection', markBegins: true,
    leg: (phrase) => standIn(phrase) + 'test("opens a page through the shared launch", async (t) => { try { await inBrowser(t, async () => {}); } catch (e) { fs.writeFileSync(__filename + ".mark", String(e.message)); } });\n' },
];
/** The words every home of the roster rule carries, each sentence whole: the rule, who checks it, that nothing reads a leg's
 *  source for it, the examples' lead-in and each example's phrase (from EXAMPLES), the sentence on a leg built to pass without
 *  a browser, the witness and that nothing checks that every browser leg in the tree is rostered. */
const RULE_LEAD = 'Examples, not the whole set:';
const RULE_BUILT = 'A leg built to pass without a browser is outside what the step can detect.';
const RULE_WORDS = [
  'The roster rule: under the switch, a rostered leg passes only when inBrowser has launched Chromium, and the leg does nothing that lets it pass otherwise (for example: it launches no browser of its own; nothing catches or settles inBrowser\'s rejection, so the rejection fails its test; it does not change ROMP_BROWSER_LEGS_REQUIRE, and hands inBrowser no test context but the one node gave it; it does not end its own process, from a test, a hook or a timer; no condition the runner can leave unmet stands between a browser test and its inBrowser call; it skips and marks todo nothing).',
  'The reviewer of any PR that adds a roster line or changes a rostered leg\'s source or inBrowser checks the rule; the step does not.',
  'Nothing in the tree reads a leg\'s source for the rule, so the step can read green a rostered leg that breaks it.',
  RULE_LEAD,
  ...EXAMPLES.map((e) => e.phrase),
  RULE_BUILT,
  'tools/ci-browser-legs.test.mjs runs a synthetic leg of each example and reads it green.',
  'Nothing checks that every browser leg in the tree is rostered, and main has no such check.',
];

test('each home of the roster rule, read in its named section (RULE_HOMES\' docstring), states it in the same words: the rule, who checks it, that nothing reads a leg\'s source for it, its examples as examples (the list after "examples, not the whole set:" is exactly the phrases of EXAMPLES, the witness table), the sentence on a leg built to pass without a browser, the witness, and that nothing checks that every browser leg in the tree is rostered', () => {
  const flat = (text) => text.split('\n').map((l) => l.replace(/^\s*(?:#|\/\/)\s?/, '').trim()).join(' ').replace(/`/g, '').replace(/\s+/g, ' ').toLowerCase();
  const lead = flat(RULE_LEAD), built = flat(RULE_BUILT), phrases = EXAMPLES.map((e) => flat(e.phrase));
  for (const home of RULE_HOMES) {
    const name = path.relative(REPO, home.file) + ', read in ' + home.section + ',';
    const text = flat(home.read(read(home.file)));
    const missing = RULE_WORDS.filter((w) => !text.includes(flat(w)));
    assert.deepEqual(missing, [], name + ' is a home of the roster rule and does not say ' + JSON.stringify(missing) + ': each home states the rule in the same words, who checks it, its examples as examples, the sentence on a leg built to pass without a browser, the witness and that nothing checks that every browser leg in the tree is rostered, so a reader of any one of them does not take the rule for a machine check. A text pin: it holds that each home says these words in its section, whatever the wrap; that each example reads green is executed by the test "each example the roster rule\'s homes name reads green, executed" below, not by this one');
    const at = text.indexOf(lead) + lead.length;
    const listed = text.slice(at, text.indexOf(built, at)).trim().replace(/\.$/, '').split(';').map((e) => e.trim());
    assert.deepEqual(listed, phrases, name + ' lists after ' + JSON.stringify(RULE_LEAD) + ' ' + JSON.stringify(listed) + ', and the list holds exactly the phrases of EXAMPLES, the witness table, each with its synthetic leg: an example named with no witness, or a witness removed while its example is still named, is red here (add the example and its leg to EXAMPLES, or take the example out of every home)');
  }
});


/** vscode-extension/.vscodeignore's patterns hold a relative path, anchored to the whole path: `**` any run of path characters
 *  including /, `*` a run inside ONE segment, and every other character literally. That is minimatch's reading of those two
 *  wildcards inside a pattern, except a pattern that opens with ** and a slash, which minimatch lets match no directory
 *  (the file's pattern for .map files matches a.map there) and this reader holds to at least one /; minimatch is what vsce
 *  applies to .vscodeignore when it packs the VSIX (not executed here: the Shell job has no node_modules); the file
 *  holds no ?, bracket class, brace or leading ! negation, which minimatch reads and this reader does
 *  not, so a pattern that adds one re-derives this reader. tests/test_lab_dist.py reads the same file with Python's fnmatch,
 *  whose `*` crosses `/` (fnmatched below spells that reading), so the two readers part on a single `*` against a path with more
 *  segments; the pin below executes that divergence and asserts the two readers AGREE, under the file's patterns, on each of
 *  the five paths it asks about (the three CI-only files and two shipped ones), so a pattern that parts them on one of those
 *  paths is red here rather than a VSIX that differs from what the Python pin read. */
const escapeRe = (piece) => piece.replace(/[.+?^${}()|[\]\\]/g, '\\$&');
function vscodeignored(patterns, rel) {
  return patterns.some((p) => new RegExp('^' + p.split(/(\*\*|\*)/).map((piece) => piece === '**' ? '.*' : piece === '*' ? '[^/]*' : escapeRe(piece)).join('') + '$').test(rel));
}
/** The same file under Python's fnmatch (tests/test_lab_dist.py's `fnmatch.fnmatchcase(rel, p)`): `*` and `**` any run including /,
 *  `?` one character, and every other character literally (fnmatch's bracket class is not modelled: the file holds none). */
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
  // scripts/a/b.sh under fnmatch and not under minimatch; under the file's patterns the two readers must agree on each of the
  // five paths this pin asks about, else the VSIX vsce packs differs from what tests/test_lab_dist.py read from the same file
  assert.equal(vscodeignored(['scripts/*'], 'scripts/a/b.sh'), false, 'minimatch\'s reading: * stays inside one segment');
  assert.equal(fnmatched(['scripts/*'], 'scripts/a/b.sh'), true, 'fnmatch\'s reading: * crosses /');
  assert.equal(vscodeignored(['scripts/**'], 'scripts/a/b.sh'), true, '** crosses segments in both readers');
  for (const rel of [ROSTER, path.relative(EXT, SCRIPT), path.relative(EXT, REPORTER), 'package.json', 'dist/extension.js']) {
    assert.equal(vscodeignored(patterns, rel), fnmatched(patterns, rel), rel + ': the two readers of .vscodeignore part on this path (minimatch, vsce\'s: ' + vscodeignored(patterns, rel) + '; fnmatch, tests/test_lab_dist.py\'s: ' + fnmatched(patterns, rel) + '), so a pattern in the file leans on a single * across a /: write it so both readers agree, or re-derive this pin and the Python one together: ' + JSON.stringify(patterns));
  }
});

// ── the script ────────────────────────────────────────────────────────────────────────────────────────

/** The failed-as-a-whole red's words after the file and node's failure: node's rule for failing a file as a whole, which
 *  holds whatever the cause, and where the cause is (the spec output above the red), so the red lists no causes to go stale. */
const FILEFAIL_RULE = 'node fails a file as a whole when its process exits non-zero or is cut at the run\'s --test-timeout outside any one test\'s result: read the spec output above for the cause';

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
  assert.match(src, /^REPORTER=\.\/scripts\/ci-browser-legs-reporter\.mjs$/m, 'the script names the reporter as REPORTER, by a path node resolves from vscode-extension/ (a line REPORTER=./scripts/ci-browser-legs-reporter.mjs, read for its presence)');
  assert.equal((src.match(/--test-reporter="\$REPORTER" --test-reporter-destination="\$rep"/g) || []).length, 1, 'node --test is handed the reporter with a destination file the script reads after the run (executed below)');
  assert.ok(src.includes('echo "no legs in the roster"; exit 0'), 'the empty-roster guard is spelled in the script (executed below)');
  assert.match(src, /^node --test .*"\$\{legs\[@\]\}" \|\| status=\$\?$/m, 'node --test runs the roster array directly and its status is kept, so the status is node\'s own on every platform (xargs would map a failed command\'s status to 123 on GNU and to 1 on BSD and macOS; executed below: 1 and 7 pass through)');
  assert.ok(!src.split('\n').some((l) => !/^\s*#/.test(l) && /xargs/.test(l)), 'no xargs on a code line of the script, a line whose first non-blank character is not # (a comment line may name it; a comment after code on the same line is read as code, a loud red)');
  // the header states the post-run property as what the record proves, A TEST OF ITS BUNDLE PASSED, and names the boundary of
  // that proof (node's events carry no launch). A text pin on the header's prose, the lines scriptHeaderLines reads: it holds that the
  // header says what the record proves and no more, so a reader does not take the property for a launch record; the derivation
  // itself is executed in the post-run test below over records with no pass, and the boundary's other home, the parenthetical
  // in the unrun red, is read from the script's stderr there.
  const scriptHeader = scriptHeaderLines(src).map((l) => l.replace(/^# ?/, '')).join(' ');
  assert.ok(scriptHeader.includes('derives, per rostered leg, that A TEST OF ITS BUNDLE PASSED') && scriptHeader.includes('That is the whole of what the record can prove: node\'s events carry no launch'), 'the script header states the post-run property as A TEST OF ITS BUNDLE PASSED and its boundary, "That is the whole of what the record can prove: node\'s events carry no launch" (a text pin on the header\'s prose: it guards that the header states what the record proves and its boundary, so the property is not read as a launch record; the derivation is executed below. Holds the sentence: a reword of the header\'s two phrases moves this pin too)');
});

/** A synthetic tree: the script and the reporter under vscode-extension/scripts; under ui/webview two browser legs as SOURCES
 *  (a and b launch through inBrowser; a has a bundle, b none; a's second test has a newline and a # in its name, spelled \n
 *  and # in the source as node's record escapes them), whose text decides nothing here (the script reads a source's presence
 *  alone); and a stub node on PATH that records its arguments and then either runs the REAL node over them
 *  (CBL_STUB_REAL_NODE names it: the composition of the script, node and the real reporter) or writes CBL_STUB_REPORT (when
 *  set) to the reporter's destination and exits CBL_STUB_EXIT (0 unless set). Returns a runner over roster text (null removes
 *  the file) that runs the script with the switch set to 1 as the step does (stub.switch names another value; null runs it
 *  unset, as a local run may; stub.check runs --check as the first argument; stub.argv is a list of arguments passed after
 *  it; stub.report is the record the stub writes; stub.exit its exit;
 *  stub.real runs the real node); `node` in its result is the argument list of the node --test call without the reporter
 *  flags. The runner hands the script a fresh TMPDIR per run (removed and made again under the base directory), where the
 *  script's mktemp makes the record file: `tmp` in its result is that directory, and `record` is the path the script handed
 *  its reporter as the destination, read from the argument after --test-reporter=./scripts/ci-browser-legs-reporter.mjs in
 *  the stub's log (null when node was not started). The tree sits in a base directory beside a link to it, and `root` is
 *  the link: the script runs through it on every platform, so its post-run read, which keys the roster's lines by the
 *  physical path (pwd -P) as node resolves a bundle, is held on a plain temporary directory too (ubuntu, where the Shell
 *  job runs), not only where os.tmpdir() sits behind a link; a key on the logical path reds every leg that passed. `ext` is
 *  the physical path of the tree's vscode-extension, as node spells a bundle in its record, and `rec(bundle, fields...)`
 *  spells one record line for that bundle (the reporter's eight fields, the path first). `prefix` is the base directory's
 *  name before the six characters mkdtemp adds: cbl- unless a case names another, as the case of a directory whose name
 *  holds a backslash does. */
function syntheticTree(t, prefix = 'cbl-') {
  const base = fs.mkdtempSync(path.join(os.tmpdir(), prefix));
  t.after(() => fs.rmSync(base, { recursive: true, force: true }));
  fs.mkdirSync(path.join(base, 'tree'));
  const root = path.join(base, 'link');
  fs.symlinkSync(path.join(base, 'tree'), root, 'dir');
  assert.notEqual(fs.realpathSync(root), root, 'the synthetic tree is reached through a link, so the script\'s logical and physical paths differ');
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
    const tmp = path.join(base, 'tmp');
    fs.rmSync(tmp, { recursive: true, force: true });
    fs.mkdirSync(tmp);
    const env = { ...process.env, PATH: path.join(root, 'bin') + path.delimiter + process.env.PATH, TMPDIR: tmp };
    delete env.CBL_STUB_REPORT; delete env.CBL_STUB_EXIT; delete env.CBL_STUB_REAL_NODE; delete env.NODE_TEST_CONTEXT;
    env[SWITCH] = '1';
    if (stub.switch === null) delete env[SWITCH]; else if (stub.switch !== undefined) env[SWITCH] = stub.switch;
    if (stub.report !== undefined) env.CBL_STUB_REPORT = stub.report;
    if (stub.exit !== undefined) env.CBL_STUB_EXIT = String(stub.exit);
    if (stub.real) env.CBL_STUB_REAL_NODE = process.execPath;
    const r = bash([path.join(ext, 'scripts', 'ci-browser-legs.sh'), ...(stub.check ? ['--check'] : []), ...(stub.argv || [])], { cwd: root, env });
    const args = fs.existsSync(log) ? fs.readFileSync(log, 'utf8').split('\n').filter(Boolean) : null;
    const at = args ? args.indexOf('--test-reporter=./scripts/ci-browser-legs-reporter.mjs') : -1;
    const dest = at >= 0 ? args[at + 1] : undefined;
    const record = dest !== undefined && dest.startsWith('--test-reporter-destination=') ? dest.slice('--test-reporter-destination='.length) : null;
    return { status: r.status, out: r.stdout, err: r.stderr, node: args && args.filter((a) => !a.startsWith('--test-reporter') && !a.startsWith('--test-timeout=')), reporters: args && args.filter((a) => a.startsWith('--test-reporter')), testTimeout: args && args.find((a) => a.startsWith('--test-timeout=')), tmp, record };
  };
  const real = fs.realpathSync(ext);
  const rec = (bundle, ...fields) => [path.join(real, bundle), ...fields].join('\t') + '\n';
  return { run, root, ext: real, rec, A, B };
}

/** The script removes its record file (its EXIT trap): read on a run that started node, from the record path the stub logged,
 *  so the emptiness check is not vacuous. That path is in the run's fresh TMPDIR and is gone after the run, and the TMPDIR is
 *  empty. `what` names the run in the messages. */
function assertRecordRemoved(r, what) {
  assert.ok(r.record, what + ': the stub logged the destination the script handed its reporter: ' + JSON.stringify(r.reporters));
  assert.equal(fs.realpathSync(path.dirname(r.record)), fs.realpathSync(r.tmp), what + ': the record file is in the run\'s fresh TMPDIR (the script\'s mktemp reads TMPDIR; compared as real paths, so the same directory spelled through a link counts): ' + r.record);
  assert.ok(!fs.existsSync(r.record), what + ': the record file is gone after the run (the script\'s EXIT trap removes it): ' + r.record);
  assert.deepEqual(fs.readdirSync(r.tmp), [], what + ': the run\'s fresh TMPDIR is empty after the run, so the run left no file there: ' + JSON.stringify(fs.readdirSync(r.tmp)));
}

test('the script runs the rostered legs through node --test when the roster is well formed and current, a last line with no newline included and a tree under a directory whose name holds a backslash (the post-run key\'s row), runs the pre-run checks alone under --check as its first argument (which does not require the bundle, and passes a bundle straight under out-tests/) and not under --check as its second, and prints "no legs in the roster" and starts no node on an empty roster; after its first run the record file the script handed its reporter is gone and the run\'s fresh TMPDIR is empty', (t) => {
  const { run, root, rec, A, B } = syntheticTree(t);
  // the stub's record: a's one test passed (with no record a rostered leg is red as unrun, the property the post-run test executes)
  const ok = run('# header\n\n' + A + '\n', { report: rec(A, 'pass', 'test', '-', 'test', 'leg a opens the page', '', '-') });
  assert.equal(ok.status, 0, 'a well-formed roster whose sources and bundles are present runs clean, exit 0; stderr:\n' + ok.err);
  assert.deepEqual(ok.node, ['--test', A], 'node --test received the roster\'s one bundle');
  assert.equal(ok.testTimeout, '--test-timeout=' + testTimeoutMs(), 'node --test received the per-file bound the script spells (its edges are pinned above)');
  assert.deepEqual(ok.reporters.filter((a) => !a.startsWith('--test-reporter-destination=')), ['--test-reporter=spec', '--test-reporter=./scripts/ci-browser-legs-reporter.mjs'], 'the spec reporter for the log and the step\'s own reporter for the post-run read');
  assert.ok(!ok.out.includes('no legs in the roster'));
  // the record file: the stub wrote a's pass to the path it logged and the script read it there (exit 0 needs that pass), and
  // after the run the path is gone and the run's TMPDIR is empty
  assertRecordRemoved(ok, 'the stub run');
  // --check: the pre-run checks alone, no node started; the bundle check is the step's run's, so b (a source, no bundle) passes here
  const check = run('# header\n' + A + '\n' + B + '\n', { check: true });
  assert.equal(check.status, 0, '--check over a well-formed roster whose sources are present exits 0, a bundle not yet built included; stderr:\n' + check.err);
  assert.ok(check.out.includes('ci-browser-legs: the roster is well formed and every line names a source in the tree: 2 rostered (--check reads the roster alone and starts no node --test; the step\'s run also checks that each rostered bundle is built under out-tests/)'), '--check prints its agreement line with the count of rostered lines: ' + JSON.stringify(check.out));
  assert.equal(check.node, null, '--check starts no node');
  // the --check read's rows (the script's header states it): as the first argument above; as the second argument it is
  // not read, so the step's run starts node over the roster
  const second = run('# header\n' + A + '\n', { argv: ['x', '--check'], report: rec(A, 'pass', 'test', '-', 'test', 'leg a opens the page', '', '-') });
  assert.equal(second.status, 0, '--check as the second argument, the step\'s run over a well-formed roster: exit 0; stderr:\n' + second.err);
  assert.deepEqual(second.node, ['--test', A], '--check as the second argument is not read: the step\'s run starts node --test over the roster');
  assert.ok(!second.out.includes('the roster is well formed'), '--check as the second argument prints no agreement line: ' + JSON.stringify(second.out));
  // a well_formed row (its comment in the script states the shape): a bundle straight under out-tests/, whose source is at
  // the tree's root, passes the pre-run checks
  fs.writeFileSync(path.join(root, 'x.test.ts'), '');
  const straight = run('out-tests/x.test.js\n', { check: true });
  assert.equal(straight.status, 0, 'a bundle straight under out-tests/ passes --check: exit 0; stderr:\n' + straight.err);
  assert.ok(straight.out.includes('the roster is well formed and every line names a source in the tree: 1 rostered'), 'a bundle straight under out-tests/ is rostered: ' + JSON.stringify(straight.out));
  // the empty roster: a comment line, an empty line and a line of whitespace alone, each skipped by the roster loop (the
  // rows the script's comment above well_formed names)
  const empty = run('# only a comment\n\n   \n');
  assert.equal(empty.status, 0, 'an empty roster exits 0 (the guard, not a red); stderr:\n' + empty.err);
  assert.ok(empty.out.includes('no legs in the roster'), 'the guard says so: ' + JSON.stringify(empty.out));
  assert.equal(empty.node, null, 'node was not started: with no file arguments node --test would run its default glob');
  // a last line with no newline, which the roster loop's guard reads (read fails at the end of the file with the line filled):
  // node receives every line. Without the guard a one-line roster reads as empty and a two-line roster drops its last leg,
  // both exiting 0 in silence, so the assertion is on the lines node received and not on the exit alone
  fs.writeFileSync(path.join(root, 'vscode-extension', B), '');   // b's bundle, so both lines of the two-line roster run
  const passes = rec(A, 'pass', 'test', '-', 'test', 'leg a opens the page', '', '-') + rec(B, 'pass', 'test', '-', 'test', 'leg b opens the page', '', '-');
  const oneLine = run(A, { report: passes });
  const twoLines = run(A + '\n' + B, { report: passes });
  assert.deepEqual([oneLine.node, twoLines.node], [['--test', A], ['--test', A, B]], 'a roster whose last line has no newline hands node every line, a one-line roster and a two-line roster alike (the exit alone does not tell: the empty-roster path exits 0 too); stdout:\n' + oneLine.out + twoLines.out);
  assert.equal(oneLine.status, 0, 'the one-line roster with no final newline runs clean; stderr:\n' + oneLine.err);
  assert.equal(twoLines.status, 0, 'the two-line roster whose last line has no newline runs clean; stderr:\n' + twoLines.err);
  // the post-run key's row (the script's comment above its awk pass states the key): a tree under a directory whose name
  // holds a backslash before a y and before a t, its leg's pass recorded under the physical path as node spells it
  const odd = syntheticTree(t, 'cbl-x\\y-a\\tb-');
  assert.ok(odd.ext.includes('cbl-x\\y-a\\tb-'), 'the tree\'s physical path holds the directory name with its two backslashes: ' + odd.ext);
  const oddRun = odd.run(odd.A + '\n', { report: odd.rec(odd.A, 'pass', 'test', '-', 'test', 'leg a opens the page', '', '-') });
  assert.equal(oddRun.status, 0, 'a tree under a directory whose name holds a backslash before a y and before a t runs its leg that passed clean, exit 0; stderr:\n' + oddRun.err);
  assert.equal(oddRun.err, '', 'nothing on stderr for the tree under a directory whose name holds a backslash');
});

test('the script refuses, naming the line and the remedy, on: a missing roster file, a stale line, a duplicate, a missing bundle, and a malformed line (nine malformed shapes: six shown with their whitespace as bash\'s %q spells it, and three non-canonical spellings, a dot segment, a doubled slash and a dot-dot segment, one of them beside the canonical spelling of the same bundle); every refusal after the roster is read ends with the summary line, and no leg ran; --check refuses a stale line, a duplicate and a malformed line the same way; seen_at\'s rows (the script\'s comment above seen_at states how it compares): a line holding a backslash rostered twice is refused as a duplicate, and beside the line holding two backslashes in its place it is not, in the step\'s run and under --check', (t) => {
  const { run, root, rec, A, B } = syntheticTree(t);
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
  // a malformed line, nine shapes. Three non-canonical spellings of a bundle that is present: node resolves each to the
  // canonical spelling, so the post-run read would attribute no result to the line and red a leg that passed, and a
  // duplicate check keyed on spelling would pass one bundle rostered twice. Each is malformed, as wellFormed's docstring and
  // the script's comment above well_formed state, refused by the tree test's wellFormed first, then by the script, alone
  // and beside the canonical line
  const DOT = 'out-tests/./ui/webview/a-browser.test.js', SLASHES = 'out-tests/ui//webview/a-browser.test.js', DOTDOT = 'out-tests/ui/../ui/webview/a-browser.test.js';
  for (const line of [DOT, SLASHES, DOTDOT]) assert.equal(wellFormed(line), false, 'the tree test\'s check refuses ' + JSON.stringify(line) + ', which path.posix.normalize spells ' + JSON.stringify(path.posix.normalize(line)) + ': a bundle path is canonical');
  assert.equal(wellFormed(A), true, 'the tree test\'s check admits the canonical spelling ' + A);
  refused(run(DOT + '\n'), ROSTER + ' line 1: ' + DOT + ' is not a bundle path (out-tests/<dir>/<name>.test.js in its canonical spelling, no empty, . or .. segment;');
  refused(run(SLASHES + '\n'), ROSTER + ' line 1: ' + SLASHES + ' is not a bundle path');
  refused(run(DOTDOT + '\n'), ROSTER + ' line 1: ' + DOTDOT + ' is not a bundle path');
  refused(run(A + '\n' + DOT + '\n'), ROSTER + ' line 2: ' + DOT + ' is not a bundle path');
  // six more, each LINE shown as bash's %q spells it, so an invisible cause (a carriage return, a tab, a trailing space,
  // leading whitespace) is visible in the red: a source path in place of a bundle path, a carriage return at the end, a tab and
  // pasted text after the path, a leading tab, spaces then a tab before the path, and a trailing space
  refused(run('ui/webview/a-browser.test.ts\n'), ROSTER + ' line 1: ui/webview/a-browser.test.ts is not a bundle path (out-tests/<dir>/<name>.test.js in its canonical spelling, no empty, . or .. segment; a trailing space, tab or carriage return counts and is shown here as bash\'s %q spells it): fix the line');
  refused(run(A + '\r\n'), ROSTER + ' line 1: $\'' + A + '\\r\' is not a bundle path');
  refused(run(A + '\tpasted text\n'), ROSTER + ' line 1: $\'' + A + '\\tpasted text\' is not a bundle path');
  refused(run('\t' + A + '\n'), ROSTER + ' line 1: $\'\\t' + A + '\' is not a bundle path');
  refused(run('  \t' + A + '\n'), ROSTER + ' line 1: $\'  \\t' + A + '\' is not a bundle path');
  refused(run(A + ' \n'), ROSTER + ' line 1: ' + A + '\\  is not a bundle path');
  // --check runs the same pre-run checks and skips only the bundle check: a stale line, a duplicate and a malformed line are
  // each refused there as in the step's run (exit 1, the named red, the summary line, no node), with no agreement line
  const refusedUnderCheck = (roster, needle) => {
    const r = run(roster, { check: true });
    refused(r, needle);
    assert.ok(!r.out.includes('the roster is well formed'), '--check prints no agreement line after a refusal:\n' + r.out);
  };
  refusedUnderCheck('# header\n' + A + '\n' + C + '\n', ROSTER + ' line 3: \'' + C + '\' names ui/webview/c-browser.test.ts, which is not in the tree (the source moved or was deleted): fix the roster line');
  refusedUnderCheck(A + '\n' + A + '\n', ROSTER + ' line 2: \'' + A + '\' duplicates line 1: remove one');
  refusedUnderCheck('ui/webview/a-browser.test.ts\n', ROSTER + ' line 1: ui/webview/a-browser.test.ts is not a bundle path');
  // seen_at's rows (the script's comment above seen_at states how it compares), each in the step's run and under --check:
  // a line holding a backslash rostered twice, its line 2 refused as a duplicate of line 1; and that line beside the line
  // holding two backslashes in its place, neither refused, the step's run starting node over both. The sources and the
  // bundles of both lines are in the tree, so a duplicate is the one red either roster can take. The rows that read
  // otherwise are collected and asserted once
  const K1 = 'out-tests/ui/webview/a\\b-browser.test.js', K2 = 'out-tests/ui/webview/a\\\\b-browser.test.js';
  for (const k of [K1, K2]) {
    fs.writeFileSync(path.join(root, 'ui', 'webview', path.posix.basename(k, '.test.js') + '.test.ts'), '');
    fs.writeFileSync(path.join(root, 'vscode-extension', k), '');
  }
  const TWICE = ROSTER + ' line 2: \'' + K1 + '\' duplicates line 1: remove one';
  const BOTH_PASS = rec(K1, 'pass', 'test', '-', 'test', 'leg a opens the page', '', '-') + rec(K2, 'pass', 'test', '-', 'test', 'leg a opens the page', '', '-');
  const SEEN_ROWS = [
    ['a line holding a backslash rostered twice, in the step\'s run: line 2 refused as a duplicate of line 1', K1 + '\n' + K1 + '\n', {}, (r) => r.status === 1 && r.err.includes(TWICE) && r.err.includes(SUMMARY) && r.node === null],
    ['a line holding a backslash rostered twice, under --check: line 2 refused as a duplicate of line 1', K1 + '\n' + K1 + '\n', { check: true }, (r) => r.status === 1 && r.err.includes(TWICE) && r.err.includes(SUMMARY) && r.node === null && !r.out.includes('the roster is well formed')],
    ['that line beside the line holding two backslashes in its place, in the step\'s run: neither refused, node started over both', K1 + '\n' + K2 + '\n', { report: BOTH_PASS }, (r) => r.status === 0 && r.err === '' && isDeepStrictEqual(r.node, ['--test', K1, K2])],
    ['that line beside the line holding two backslashes in its place, under --check: neither refused, both rostered', K1 + '\n' + K2 + '\n', { check: true }, (r) => r.status === 0 && r.err === '' && r.out.includes('the roster is well formed and every line names a source in the tree: 2 rostered')],
  ];
  const seenWrong = [];
  for (const [what, roster, stub, holds] of SEEN_ROWS) {
    const r = run(roster, stub);
    if (!holds(r)) seenWrong.push(what + ': exit ' + r.status + ', node ' + JSON.stringify(r.node) + ', stdout ' + JSON.stringify(r.out) + ', stderr ' + JSON.stringify(r.err));
  }
  assert.deepEqual(seenWrong, [], 'each of seen_at\'s rows reads as the script\'s comment above seen_at states; the rows read otherwise: ' + JSON.stringify(seenWrong));
});

test('after node --test the script derives per rostered leg that a test of its bundle passed, red as unrun when none did (todo-only, a describe() that registers none, a file that registered nothing, a failure inside a todo, a skip-only record); reds a rostered leg\'s skipped test (the scope the script\'s header states), naming the test, its reason and the switch\'s state; reds a rostered leg\'s failure inside a todo, and a file that failed as a whole, by name; prints the lost-browser remedy beside a leg (the lost-browser read the script\'s header states); passes node\'s status through; the unrun and the skip remedies take the line out of the roster', (t) => {
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
  // most the record proves, and, for a leg that follows the roster rule, the browser part's own run is read only by the skip
  // and lost-browser lines when its launch is reached
  assert.ok(none.err.includes('a rostered leg holds a test that runs and passes here (a pass is the most the record proves: a pass from a test needing no browser satisfies this check, and, for a leg that follows the roster rule, the browser part\'s own run is read only by the skip and lost-browser lines when its launch is reached)'), 'the unrun red says, beside its remedy, that a pass is the most the record proves, so a reader of the red does not take the property for a launch record (holds the sentence as the script emits it: a reword of the parenthetical in the script moves this pin too):\n' + none.err);
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
  // a file that failed as a whole: node's file-level result failing, which node reports when the file's process exits
  // non-zero or is cut at --test-timeout outside any one test's result; the red states that rule and points at the spec
  // output for the cause, whatever the cause was, and says nothing of how many tests counted. First a counting pass beside a
  // file-level timeout (a later test hung, or an open handle kept the process alive to the bound: the record cannot say
  // which): red by node's rule, the pass counted, so no unrun red and no line saying the file ran no test that counts
  const passThenCut = run(A + '\n', { report: PASS + rec(A, 'fail', 'test', '-', 'file-level', A, 'test timed out after 240000ms', 'testTimeoutFailure'), exit: 1 });
  assert.equal(passThenCut.status, 1, 'a file cut at the bound after a counting pass is red; stderr:\n' + passThenCut.err);
  assert.ok(passThenCut.err.includes('ci-browser-legs: ' + A + ' failed as a whole (testTimeoutFailure: test timed out after 240000ms): ' + FILEFAIL_RULE), 'a file cut at --test-timeout after a counting pass is red naming the file and the failure type, worded by node\'s rule and pointing at the spec output for the cause:\n' + passThenCut.err);
  assert.ok(!passThenCut.err.includes('no test of this leg passed') && !passThenCut.err.includes('ran no test that counts'), 'the pass counts: no unrun red, and no line says the file ran no test that counts:\n' + passThenCut.err);
  const timedOut = run(A + '\n', { report: rec(A, 'fail', 'test', '-', 'file-level', A, 'test timed out after 300000ms', 'testTimeoutFailure'), exit: 1 });
  assert.equal(timedOut.status, 1, 'node\'s failure stands');
  assert.ok(timedOut.err.includes('ci-browser-legs: ' + A + ' failed as a whole (testTimeoutFailure: test timed out after 300000ms): ' + FILEFAIL_RULE), 'a file that failed as a whole is red naming the file and the failure type, worded by node\'s rule:\n' + timedOut.err);
  assert.ok(!timedOut.err.includes('no test of this leg passed'), 'a failed file is node\'s red, not called unrun on top:\n' + timedOut.err);
  // node's own exit status is the step's: the roster array is node's argument list, with no xargs to map it (GNU 123, BSD 1)
  const failed = run(A + '\n', { report: rec(A, 'fail', 'test', '-', 'test', 'leg a opens the page', 'an assertion of the leg\'s own failed', 'testCodeFailure'), exit: 1 });
  assert.equal(failed.status, 1, 'node\'s failure is the step\'s, as node\'s own status');
  assert.equal(failed.err, '', 'a failure for a reason of the leg\'s own gets no label of the script\'s (node\'s own report carries it):\n' + failed.err);
  // this row's message, LOST, begins with inBrowser's cannot-launch phrase (the switch's name first), as inBrowser fails a
  // launch under it: the remedy is printed beside the leg
  const LOST = SWITCH + ' is set and this leg cannot run: no playwright browser on this box; the browser leg needs one: browserType.launch: Executable doesn\'t exist at /nowhere';
  const lost = run(A + '\n', { report: rec(A, 'fail', 'test', '-', 'test', 'leg a opens the page', LOST, 'testCodeFailure'), exit: 1 });
  assert.equal(lost.status, 1);
  assert.ok(lost.err.includes('ci-browser-legs: ' + A + ': \'leg a opens the page\' failed under ' + SWITCH + '=1 because inBrowser could not launch (' + LOST + '): the runner lost its browser: check the Chromium install step'), 'a failure whose message begins with inBrowser\'s cannot-launch phrase is red with the lost-browser remedy beside the leg (check the Chromium install step):\n' + lost.err);
  // the phrase quoted AFTER other text (the rostered switch test's assertion messages embed a child run's stdout, which carries
  // it): an ordinary failure of the leg, no LOST line, no label of the script's, node's red passed through
  const quoted = run(A + '\n', { report: rec(A, 'fail', 'test', '-', 'test', 'leg a opens the page', 'the leg failed under the switch; the child run printed: ' + LOST, 'testCodeFailure'), exit: 1 });
  assert.equal(quoted.status, 1, 'node\'s failure stands');
  assert.ok(!quoted.err.includes('the runner lost its browser'), 'a message that quotes the phrase after other text is not a lost browser (LOST reads the start of the message):\n' + quoted.err);
  assert.equal(quoted.err, '', 'an ordinary failure gets no label of the script\'s:\n' + quoted.err);
  // the switch set to yes, a row of the script's switch-state read (its comment in the script states what it reads): the
  // skip's red names the value and gives the set-switch remedy
  const yes = run(A + '\n', { report: PASS + rec(A, 'pass', 'test', 'skip', 'test', 'leg a opens the page', 'why', '-'), switch: 'yes' });
  assert.equal(yes.status, 1, 'a skip under the switch set to yes is red; stderr: ' + yes.err);
  assert.ok(yes.err.includes('skipped with ' + SWITCH + '=yes: \'leg a opens the page\' # SKIP why (' + A + ')'), 'the skip names the switch\'s value as the run had it (yes):\n' + yes.err);
  assert.ok(yes.err.includes('a rostered leg skipped a test with ' + SWITCH + '=yes, so the step claims coverage it did not run') && yes.err.includes('only inBrowser in ui/webview/real-viewer-leg.ts turns a launch it cannot make into a failure here'), 'the set-switch remedy under the switch set to yes, not the unset one:\n' + yes.err);
  const both = run(A + '\n', { report: rec(A, 'pass', 'test', 'skip', 'test', 'leg a opens the page', 'why', '-'), exit: 7 });
  assert.equal(both.status, 7, 'with a failure and a skip node\'s own status (7) stands, not overwritten by the skip\'s status=1, and the skip is still named');
  assert.ok(both.err.includes('skipped with ' + SWITCH + '=1'), 'with node\'s own failure status (7) the skip is still named:\n' + both.err);
  // the same record holds one skip and no other result, so the leg ran no counting pass: the unrun red fires beside the skip's
  // line, and its tally names the skip (with a skip counted as a pass this red is not printed; with the skip tally dropped it
  // names 0 skipped)
  assert.ok(both.err.includes(UNRUN + '1 skipped, 0 todo, 0 suite and 0 file-level results for it)'), 'a skip-only record is red as unrun too, naming what the record held (1 skipped): a skip is not a counting pass, and the skip reaches the unrun red\'s tally:\n' + both.err);
  // the foreign-file case, the scope the script's header states: over a roster of A alone, results recorded under
  // out-tests/ui/webview/helper.js, a file the roster does not name (as a leg's run records a file it loads outside its
  // bundle), are read through node's status alone, each row below run and the rows that read otherwise named together.
  // Beside A's counting pass, a foreign skip and a foreign failure inside a todo read green at node's exit 0, and a
  // foreign file-level failure and a foreign failure whose message begins with inBrowser's phrase are node's red at its
  // exit 1, with no line of the script's. With no pass of A's own, A is red as unrun, its tally counting none of the
  // foreign skip, todo, suite and file-level results, and no skip is named. A foreign pass alone is not that row: a pass
  // is none of the tallied kinds, so its zero tally holds under a script that credits foreign results to A's tally
  const H = 'out-tests/ui/webview/helper.js';
  const FOREIGN_ROWS = [
    { what: 'a foreign skip and a foreign failure inside a todo beside A\'s counting pass: exit 0, nothing on stderr', exit: 0, status: 0, err: (e) => e === '',
      report: PASS + rec(H, 'pass', 'test', 'skip', 'test', 'a helper test', 'why', '-') + rec(H, 'fail', 'test', 'todo', 'test', 'a helper todo', 'the helper is broken', 'testCodeFailure') },
    { what: 'a foreign file-level failure and a foreign failure that begins with inBrowser\'s phrase beside A\'s counting pass: node\'s exit 1, nothing on stderr', exit: 1, status: 1, err: (e) => e === '',
      report: PASS + rec(H, 'fail', 'test', '-', 'file-level', H, 'the helper exited 1', 'testCodeFailure') + rec(H, 'fail', 'test', '-', 'test', 'a helper test', LOST, 'testCodeFailure') },
    { what: 'a foreign pass, skip, todo, suite result and file-level pass with no pass of A\'s own: A red as unrun with a zero tally, no skip named', exit: 0, status: 1,
      err: (e) => e.includes(UNRUN + '0 skipped, 0 todo, 0 suite and 0 file-level results for it)') && !e.includes('skipped with'),
      report: rec(H, 'pass', 'test', '-', 'test', 'a helper pass', '', '-') + rec(H, 'pass', 'test', 'skip', 'test', 'a helper skip', 'why', '-') + rec(H, 'pass', 'test', 'todo', 'test', 'a helper todo', '', '-') + rec(H, 'pass', 'suite', '-', 'test', 'a helper suite', '', '-') + rec(H, 'pass', 'test', '-', 'file-level', H, '', '-') },
  ];
  const foreignWrong = [];
  for (const row of FOREIGN_ROWS) {
    const r = run(A + '\n', { report: row.report, exit: row.exit });
    if (r.status !== row.status || !row.err(r.err)) foreignWrong.push(row.what + ': the script exits ' + r.status + ', stderr ' + JSON.stringify(r.err));
  }
  assert.deepEqual(foreignWrong, [], 'the foreign-file case: each row reads as the script\'s header states, a result recorded under a file the roster does not name read through node\'s status alone; the rows read otherwise: ' + JSON.stringify(foreignWrong));
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

test('the composition, executed: the script with the real node and the real reporter over the shapes as rostered legs reds todo-only, describe-none, nothing and a failure inside a todo by leg, names the skip, prints the lost-browser remedy, reds a file that threw at load as failed as a whole, and passes a clean roster; a leg whose test passes and whose error comes after the test ended is red as failed as a whole by node\'s rule, its pass counted; after the first real-node run the record file the script handed its reporter is gone and the run\'s fresh TMPDIR is empty', (t) => {
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
  assert.ok(all.err.includes('ci-browser-legs: ' + S.lost + ': \'the launch\' failed under ' + SWITCH + '=1 because inBrowser could not launch (' + SWITCH + ' is set and this leg cannot run: no playwright browser on this box): the runner lost its browser: check the Chromium install step'), 'the composition prints the lost-browser remedy beside the leg whose failure message begins with inBrowser\'s cannot-launch phrase:\n' + all.err);
  assert.ok(all.err.includes(S.describeNone + ': no test of this leg passed in this run (the record holds 0 skipped, 0 todo, 1 suite and 0 file-level results for it)') && all.err.includes(S.nothing + ': no test of this leg passed in this run (the record holds 0 skipped, 0 todo, 0 suite and 1 file-level results for it)'), 'the composition reds describe-none and nothing as unrun with what the record held (a suite result, a file-level result):\n' + all.err);
  // the record file after a real node --test that exits 1: the reporter wrote the results read above to the path the stub
  // logged, and after the run the path is gone and the run's TMPDIR is empty
  assertRecordRemoved(all, 'the composition\'s real-node run');
  const clean = run(S.describePass + '\n', { real: true });
  assert.equal(clean.status, 0, 'a leg whose test passes inside a describe(): green; stderr: ' + clean.err);
  assert.equal(clean.err, '', 'nothing on stderr');
  // a leg whose test passes and whose error comes after the test ended (a timer's throw, as an unawaited inBrowser call
  // rejects under the switch on a runner with no browser): node counts the pass, then fails the file as a whole, since its
  // process exits non-zero outside any one test's result. The red is node's rule, the pass is counted (no unrun red), and no
  // line says the file ran no test that counts; the spec output the red points at carries the error
  const afterEnd = 'out-tests/ui/webview/after-end-browser.test.js';
  fs.writeFileSync(path.join(root, 'vscode-extension', afterEnd), 'const { test } = require("node:test");\ntest("passes, then its unawaited work fails", () => { setTimeout(() => { throw new Error("a synthetic failure after the test ended"); }, 100); });\n');
  fs.writeFileSync(path.join(root, 'ui', 'webview', 'after-end-browser.test.ts'), shared + 'test("x", async (t) => { await inBrowser(t, async () => {}); });\n');
  const late = run(afterEnd + '\n', { real: true });
  assert.equal(late.status, 1, 'node fails the file whose error came after its test ended, and the script passes that through; stderr:\n' + late.err);
  const lateRed = late.err.split('\n').find((l) => l.startsWith('ci-browser-legs: ' + afterEnd + ' failed as a whole ('));
  assert.ok(lateRed !== undefined && lateRed.endsWith('): ' + FILEFAIL_RULE), 'the file whose error came after its test ended is red as failed as a whole, worded by node\'s rule and pointing at the spec output for the cause: ' + JSON.stringify(lateRed) + '; stderr:\n' + late.err);
  assert.ok(!late.err.includes('no test of this leg passed') && !late.err.includes('ran no test that counts'), 'the leg\'s pass counts: no unrun red, and no line says the file ran no test that counts:\n' + late.err);
  assert.ok(late.out.includes('a synthetic failure after the test ended'), 'the spec output above the red carries the error the red points at:\n' + late.out);
});

test('each example the roster rule\'s homes name reads green, executed: the script with the real node and the real reporter over one synthetic rostered leg of each example in EXAMPLES exits 0 with nothing on stderr, each failure marked as it happens; a control that awaits the catch example\'s stand-in for inBrowser with no try reads red with the lost-browser remedy, so that green is the catch\'s doing', (t) => {
  // witnesses of what the step cannot see, the examples each home of the roster rule names. The witnesses model each example as
  // node's record shows it (a passing test, and for the todo example a todo beside it), so a change to the script or the
  // reporter that reads one of these examples from node's record turns this red, and the homes' list and EXAMPLES move with it.
  // No witness loads playwright: a mechanism keyed on playwright's launch needs witnesses that launch, so the witness set is
  // rewritten, not only re-read, when the follow-up lands. The catch example's stand-in copies cannot() and nothing here reads
  // cannot() (see standIn), so a change to cannot() rewrites the stand-in too. Each leg that stands for a failure writes a mark
  // beside its bundle when the failure happens, so the green below is read over a run in which each of those failures happened
  const { run, root, ext } = syntheticTree(t);
  const phrase = scriptPhrase();
  const head = 'const { test } = require("node:test"); const fs = require("node:fs"); const { spawnSync } = require("node:child_process");\n';
  const w = (name, body) => { fs.writeFileSync(path.join(root, 'vscode-extension', 'out-tests', 'ui', 'webview', name + '-browser.test.js'), head + body); fs.writeFileSync(path.join(root, 'ui', 'webview', name + '-browser.test.ts'), '// the synthetic source of a witness leg: its presence is what the script reads\n'); return 'out-tests/ui/webview/' + name + '-browser.test.js'; };
  const legs = EXAMPLES.map((e) => ({ ...e, bundle: w(e.name, e.leg(phrase)) }));
  const r = run(legs.map((l) => l.bundle).join('\n') + '\n', { real: true });
  assert.equal(r.status, 0, 'each example reads green (exit 0): a change to the script or the reporter that reads one of these examples from node\'s record turns this red, and the four homes of the roster rule drop that example, and EXAMPLES its entry, in the same change. The witnesses model each example as node\'s record shows it: a mechanism keyed on playwright\'s launch needs witnesses that launch, so the witness set is rewritten, not only re-read, when the follow-up lands; stderr:\n' + r.err);
  assert.equal(r.err, '', 'nothing on stderr for the examples (no red and no remedy line)');
  assert.deepEqual(r.node, ['--test', ...legs.map((l) => l.bundle)], 'node --test ran every witness leg');
  for (const l of legs.filter((e) => e.marked)) {
    const mark = path.join(ext, l.bundle + '.mark');
    assert.ok(fs.existsSync(mark), l.marked + ' in this run (the mark beside ' + l.bundle + '), so the green above is read over the example, not over a leg that skipped it');
    if (l.markBegins) assert.ok(fs.readFileSync(mark, 'utf8').startsWith(phrase + ': '), 'the mark beside ' + l.bundle + ' begins with the phrase the script reads a lost browser by (' + JSON.stringify(phrase) + '), so the rejection the catch took is the one the lost-browser read names: ' + JSON.stringify(fs.readFileSync(mark, 'utf8')));
  }
  // the control: the same stand-in awaited with no try, so its rejection fails the test and reaches node's record, and the step
  // reads it red with the lost-browser remedy beside the leg: the catch example's green above is the catch's doing
  const control = w('catch-control', standIn(phrase) + 'test("opens a page through the shared launch", async (t) => { await inBrowser(t, async () => {}); });\n');
  const c = run(control + '\n', { real: true });
  assert.equal(c.status, 1, 'the control, the catch example\'s stand-in awaited with no try, is red (exit 1); stderr:\n' + c.err);
  assert.ok(c.err.includes('ci-browser-legs: ' + control + ': \'opens a page through the shared launch\' failed under ' + SWITCH + '=1 because inBrowser could not launch (' + phrase + ': no playwright browser on this box (a synthetic stand-in)): the runner lost its browser: check the Chromium install step'), 'the control reads red with the lost-browser remedy beside the leg:\n' + c.err);
});

/** The phrase the script reads a lost browser by: the literal it hands awk (awk -v msg="..."), with $SWITCH spelled out. The
 *  phrase pin below and the catch example's witness read it here. */
function scriptPhrase() {
  const m = /awk -v msg="([^"]+)"/.exec(read(SCRIPT));
  assert.ok(m, 'the script hands awk the phrase it reads a failure block by (awk -v msg="...")');
  return m[1].replace(/\$SWITCH\b/g, SWITCH);
}

/** The executed test of the switch's behaviour, which the phrase pin below names and does not replace. */
const SWITCH_TEST = path.join(REPO, 'ui', 'webview', 'real-viewer-leg-switch.test.ts');

test('the phrase the script reads a lost browser by is a literal in inBrowser\'s source, the shared phrase between ui/webview/real-viewer-leg.ts and the script, so a reword on either side is red here rather than a remedy dropped in silence; the behaviour is executed by ui/webview/real-viewer-leg-switch.test.ts, which exists and drives inBrowser', () => {
  const script = read(SCRIPT);
  assert.match(script, /^SWITCH=ROMP_BROWSER_LEGS_REQUIRE$/m, 'the script names the switch as SWITCH (a line SWITCH=ROMP_BROWSER_LEGS_REQUIRE, read for its presence)');
  const phrase = scriptPhrase();
  assert.ok(phrase.startsWith(SWITCH + ' is set'), 'the phrase names the switch: ' + phrase);
  const helper = read(path.join(REPO, 'ui', 'webview', 'real-viewer-leg.ts'));
  assert.ok(helper.includes('"' + phrase + ': "'), 'the shared phrase: ui/webview/real-viewer-leg.ts holds the literal ' + JSON.stringify(phrase + ': ') + ' that vscode-extension/scripts/ci-browser-legs.sh hands awk (awk -v msg=), so a reword of it in either file is red here rather than the lost-browser remedy dropped in silence. This reads source text and guards the phrase alone, not the behaviour: that inBrowser FAILS with it under ' + SWITCH + ' and skips without is executed by ' + path.relative(REPO, SWITCH_TEST) + ' (a child node --test with PLAYWRIGHT_BROWSERS_PATH emptied), which the vscode-extension job runs; a green here with that test red is a helper that carries the words and not the behaviour');
  // the executed test this message points at exists and is rostered (so the step runs its leg with a browser on every CI
  // run, and the Test step runs its three child arms); what it asserts is its own to state, and the reviewer of any PR that
  // changes it holds it to the roster rule. The helper's playwrightInstalled export has that test as its consumer (the
  // reason the child names is derived from the helper's own module read, never from a second one): presence pins, which say
  // only that the file names these
  assert.ok(fs.existsSync(SWITCH_TEST), 'the executed test of the switch exists at ' + path.relative(REPO, SWITCH_TEST));
  assert.ok(read(SWITCH_TEST).includes('playwrightInstalled()'), path.relative(REPO, SWITCH_TEST) + ' consumes the helper\'s playwrightInstalled export (a presence pin: the export is not dead code in this tree)');
  assert.ok(parseRoster(read(path.join(EXT, ROSTER))).some((e) => e.bundle === 'out-tests/ui/webview/real-viewer-leg-switch.test.js'), path.relative(REPO, SWITCH_TEST) + ' is rostered in ' + ROSTER + ', so the step runs its leg with a browser on every CI run');
});
