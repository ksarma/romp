// The shared launcher's switch, executed: inBrowser in ./real-viewer-leg reads ROMP_BROWSER_LEGS_REQUIRE, and under the
// switch, inBrowser FAILS a launch it cannot make, naming the switch and the reason, instead of skipping, where without it
// the leg skips naming the reason (CI's browser-legs step sets the switch after the job's Chromium install; the Test step,
// before any install, does not). The test below began as fork PR 860's test of this behaviour, copied with its mechanism
// unchanged (two lines differed: the comment's name for the leg it drives, and the --test-name-pattern that picks it); this
// branch adds a third arm, the switch set to a non-"1" non-empty value ("yes"), which executes the arming rule every header
// states (any non-empty value counts) and is OFFERED to 860 for its copy, so the two branches carry one mechanism and,
// until 860 takes the arm, not one test. Beside the third arm, whose words already made the test's title differ from 860's,
// this branch narrows the title from the browser legs' skip to the skip of a leg that launches through the shared launch:
// inBrowser's read of the switch changes that skip alone.
// This branch also asserts, under both armed arms, that the failure's message begins with the phrase the step's script
// reads a lost browser by, read at run time from vscode-extension/scripts/ci-browser-legs.sh, which 860 does not have, so
// that assertion stays this branch's and the offer to 860 is the third arm alone.
// The leg it drives is this file's own, above it, which opens a page through inBrowser. The mechanism: a child
// `node --test --test-name-pattern=<leg> <this bundle>` with an env BUILT from three of this process's variables, PATH, HOME
// and NODE_OPTIONS (never inherited: the runner's NODE_TEST_CONTEXT would put the child's report on this process's channel,
// and an ambient switch would leak into the "unset" arm), PLAYWRIGHT_BROWSERS_PATH pointed at a fresh empty directory, so the
// real pw.chromium.launch() throws, and TMPDIR set to a fresh directory of the child's own; with the switch the child records
// `# fail 1` and a line carrying the switch's name and this machine's reason, without it `# skipped 1` and the reason. Each
// failed launch leaves a playwright-artifacts-* and a playwright_chromiumdev_profile-* directory in the child's temporary
// directory (Playwright makes both before it finds no browser, and removes neither), so the empty browsers directory and
// each child's temporary directory sit in one scratch directory under out-tests/ that the test removes, and the test asserts
// that each child's leg reports its own temporary directory, under that scratch directory, and that the scratch directory is
// gone after the children ran. This branch adds those temporary directories and their two assertions, which 860's copy does
// not have (the review's round 11, regression-1: each run left six such directories in this process's temporary directory). On a box with a browser the outer leg launches and passes; the switch test passes on any box,
// since its child never sees the browser. tools/ci-browser-legs.test.mjs pins the phrase the step's script reads a lost
// browser by to the helper's source text and names this file as the test of the behaviour; a green there with a red here is
// a helper that carries the words and not the behaviour. Rostered in vscode-extension/ci-browser-legs.txt, so the step runs
// the outer leg with a browser and reads its record on every CI run. Synthetic: a one-paragraph page.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import { spawnSync } from "node:child_process";
import { EXT, inBrowser, playwrightInstalled } from "./real-viewer-leg";   // the shared launch, used by the legs that launch through it, and its switch read

test("the launcher's own leg opens a page through the shared launch", { timeout: 60000 }, async (t) => {
  // the temporary directory Playwright makes its launch directories in, reported for the switch test below, whose children
  // each run this leg with a temporary directory of their own
  t.diagnostic("temporary directory: " + os.tmpdir());
  await inBrowser(t, async (browser) => {
    const page = await browser.newPage();
    await page.setContent("<!DOCTYPE html><p>a page</p>");
    assert.equal(await page.evaluate(() => document.querySelector("p")!.textContent), "a page");
  });
});

test("ROMP_BROWSER_LEGS_REQUIRE, read in the shared launch helper, turns the skip of a leg that launches through it into a failure that names the switch and the reason, under \"1\" and under another value (any non-empty value counts), and without it the skip stands naming the reason: CI's browser-legs step after the Chromium install sets it", { timeout: 180000 }, (t) => {
  // a child run of this file's leg with playwright pointed at an empty browsers directory (the pane bench's probe):
  // under the switch the leg fails naming the switch and the reason; without it the leg skips, as the Test step's run does.
  // The reason the child names is this machine's: with the module installed and its browsers hidden, no browser; with the module
  // absent, no module (the maintainer's round 6, tests-6: the regex demanded the browser reason alone, so a runner without the
  // module reported a FAILURE here where the file's contract says every browser leg skips with a stated reason); derived from
  // the same module read the helper's launch guards on (playwrightInstalled), never a two-way alternation. The assertions read
  // the property (the switch's name and the reason on the failure's line; the reason on the skip) and not the helper's
  // connective wording, which is the shared helper's to choose. Under the switch they also read that the failure's message
  // begins with the phrase the step's script reads a lost browser by (its awk -v msg= literal, with $SWITCH as the script sets
  // it), read from the script at run time, so the executed message and the script's reader are held to one another (the
  // script's header states which failures its lost-browser read reads).
  const why = playwrightInstalled() ? "no playwright browser" : "playwright is not installed under vscode-extension";
  const esc = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const script = fs.readFileSync(path.join(EXT, "scripts", "ci-browser-legs.sh"), "utf8");
  const lit = /awk -v msg="([^"]+)"/.exec(script), sw = /^SWITCH=(\S+)$/m.exec(script);
  if (!lit || !sw) assert.fail("vscode-extension/scripts/ci-browser-legs.sh sets SWITCH and hands awk the phrase it reads a lost browser by (awk -v msg=\"...\")");
  const phrase = lit[1].replace(/\$SWITCH\b/g, sw[1]);
  // the failure's TAP error field, from its start: quoted, or a block scalar whose value opens the next line
  const begins = new RegExp("^\\s*error: [\"'|-]*\\s*" + esc(phrase), "m");
  t.diagnostic("the reason a browser leg names on this machine: " + why);
  // one scratch directory holds the empty browsers directory and each child's temporary directory, made before the try so
  // that the finally removes everything the children leave, the directories of their failed launches among it
  const scratch = fs.mkdtempSync(path.join(EXT, "out-tests", "switch-scratch-"));
  try {
    const empty = path.join(scratch, "no-browsers");
    fs.mkdirSync(empty);
    // the child's environment is built, not inherited: under `node --test` this process carries the runner's NODE_TEST_CONTEXT,
    // and a child inheriting it reports on the runner's channel instead of its stdout. TMPDIR is the child's own, a fresh
    // directory under the scratch directory: a failed launch leaves a playwright-artifacts-* and a
    // playwright_chromiumdev_profile-* directory there, which a TMPDIR copied from this process would leave behind
    const base: Record<string, string> = {};
    for (const k of ["PATH", "HOME", "NODE_OPTIONS"]) if (process.env[k] !== undefined) base[k] = process.env[k] as string;
    const run = (env: Record<string, string>) => {
      const tmp = fs.mkdtempSync(path.join(scratch, "tmp-"));
      const r = spawnSync(process.execPath, ["--test", "--test-name-pattern=launcher's own leg", __filename],
        { cwd: EXT, encoding: "utf8", timeout: 100000, env: { ...base, ...env, PLAYWRIGHT_BROWSERS_PATH: empty, TMPDIR: tmp } });
      // the child's leg reports the temporary directory it ran with (node's TAP output escapes a backslash or a # in a
      // diagnostic, so the report is read by its last two parts, the scratch directory's and the child's, which mkdtemp names
      // from letters and digits)
      const told = /^\s*# temporary directory: (.*)$/m.exec(r.stdout);
      assert.ok(told && told[1].endsWith(path.join(path.basename(scratch), path.basename(tmp))), "the child's leg reports its own temporary directory, " + tmp + ", under the scratch directory the test removes, not this process's, where Playwright's playwright-artifacts-* and playwright_chromiumdev_profile-* directories from its failed launch would be left: " + (told ? told[1] : "no report") + "\n" + r.stdout.slice(-1500));
      t.diagnostic("a child's temporary directory after its run holds " + JSON.stringify(fs.readdirSync(tmp).sort()));
      return r;
    };
    const req = run({ ROMP_BROWSER_LEGS_REQUIRE: "1" });
    assert.match(req.stdout, /^# fail 1$/m, "the leg failed under the switch\n" + req.stdout.slice(-1500));
    assert.match(req.stdout, new RegExp("ROMP_BROWSER_LEGS_REQUIRE[^\\n]*" + esc(why)), "the switch: a failure naming it and the reason (" + why + ") on one line\n" + req.stdout.slice(-1500));
    assert.match(req.stdout, begins, "under \"1\": the failure's message begins with the phrase the step's script reads a lost browser by (" + phrase + "), so the script prints its lost-browser remedy beside the leg\n" + req.stdout.slice(-1500));
    // any non-empty value counts (the headers' rule, executed): a value that is not "1" fails the leg the same way
    const yes = run({ ROMP_BROWSER_LEGS_REQUIRE: "yes" });
    assert.match(yes.stdout, /^# fail 1$/m, "the leg failed under the switch set to \"yes\" (any non-empty value counts)\n" + yes.stdout.slice(-1500));
    assert.match(yes.stdout, new RegExp("ROMP_BROWSER_LEGS_REQUIRE[^\\n]*" + esc(why)), "under \"yes\": a failure naming the switch and the reason (" + why + ") on one line\n" + yes.stdout.slice(-1500));
    assert.match(yes.stdout, begins, "under \"yes\": the failure's message begins with the phrase the step's script reads a lost browser by (" + phrase + ")\n" + yes.stdout.slice(-1500));
    const plain = run({});
    assert.match(plain.stdout, /^# skipped 1$/m, "without the switch the leg skips\n" + plain.stdout.slice(-1500));
    assert.match(plain.stdout, new RegExp(esc(why)), "and the skip names the reason (" + why + ")\n" + plain.stdout.slice(-1500));
  } finally {
    fs.rmSync(scratch, { recursive: true, force: true });
  }
  // nothing the children made is left: their temporary directories, and every playwright-artifacts-* and
  // playwright_chromiumdev_profile-* directory their failed launches left in them, were in the scratch directory
  assert.ok(!fs.existsSync(scratch), "the scratch directory that held the children's temporary directories is gone after the test: " + scratch);
});
