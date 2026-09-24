// The shared launcher's switch, executed: inBrowser in ./real-viewer-leg reads ROMP_BROWSER_LEGS_REQUIRE, and under the
// switch, inBrowser FAILS a launch it cannot make, naming the switch and the reason, instead of skipping, where without it
// the leg skips naming the reason (CI's browser-legs step sets the switch after the job's Chromium install; the Test step,
// before any install, does not). The test below began as fork PR 860's test of this behaviour, copied with its mechanism
// unchanged (two lines differed: the comment's name for the leg it drives, and the --test-name-pattern that picks it); this
// branch adds a third arm, the switch set to a non-"1" non-empty value ("yes"), which executes the arming rule every header
// states (any non-empty value arms it) and is OFFERED to 860 for its copy, so the two branches carry one mechanism and,
// until 860 takes the arm, not one test. Beside the third arm, whose words already made the test's title differ from 860's,
// this branch narrows the title from the browser legs' skip to the skip of a leg that launches through the shared launch:
// the switch turns that skip alone into a failure, and any other leg's own skip stands.
// This branch also asserts, under both armed arms, that the failure's message begins with the phrase the step's script
// reads a lost browser by, read at run time from vscode-extension/scripts/ci-browser-legs.sh, which 860 does not have, so
// that assertion stays this branch's and the offer to 860 is the third arm alone.
// The leg it drives is this file's own, above it, which opens a page through inBrowser. The mechanism: a child
// `node --test --test-name-pattern=<leg> <this bundle>` with an env BUILT from four variables (never inherited: the runner's
// NODE_TEST_CONTEXT would put the child's report on this process's channel, and an ambient switch would leak into the
// "unset" arm) and PLAYWRIGHT_BROWSERS_PATH pointed at a fresh empty directory, so the real pw.chromium.launch() throws; with
// the switch the child records `# fail 1` and a line carrying the switch's name and this machine's reason, without it
// `# skipped 1` and the reason. On a box with a browser the outer leg launches and passes; the switch test passes on any box,
// since its child never sees the browser. tools/ci-browser-legs.test.mjs pins the phrase the step's script reads a lost
// browser by to the helper's source text and names this file as the test of the behaviour; a green there with a red here is
// a helper that carries the words and not the behaviour. Rostered in vscode-extension/ci-browser-legs.txt, so the step runs
// the outer leg with a browser and reads its record on every CI run. Synthetic: a one-paragraph page.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { spawnSync } from "node:child_process";
import { EXT, inBrowser, playwrightInstalled } from "./real-viewer-leg";   // the shared launch, used by the legs that launch through it, and its switch read

test("the launcher's own leg opens a page through the shared launch", { timeout: 60000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const page = await browser.newPage();
    await page.setContent("<!DOCTYPE html><p>a page</p>");
    assert.equal(await page.evaluate(() => document.querySelector("p")!.textContent), "a page");
  });
});

test("ROMP_BROWSER_LEGS_REQUIRE, read in the shared launch helper, turns the skip of a leg that launches through it into a failure that names the switch and the reason, under \"1\" and under any other non-empty value, and without it the skip stands naming the reason: CI's browser-legs step after the Chromium install sets it", { timeout: 180000 }, (t) => {
  // a child run of this file's leg with playwright pointed at an empty browsers directory (the pane bench's probe):
  // under the switch the leg fails naming the switch and the reason; without it the leg skips, as the Test step's run does.
  // The reason the child names is this machine's: with the module installed and its browsers hidden, no browser; with the module
  // absent, no module (the maintainer's round 6, tests-6: the regex demanded the browser reason alone, so a runner without the
  // module reported a FAILURE here where the file's contract says every browser leg skips with a stated reason); derived from
  // the same module read the helper's launch guards on (playwrightInstalled), never a two-way alternation. The assertions read
  // the property (the switch's name and the reason on the failure's line; the reason on the skip) and not the helper's
  // connective wording, which is the shared helper's to choose. Under the switch they also read that the failure's message
  // begins with the phrase the step's script reads a lost browser by (its awk -v msg= literal, with $SWITCH as the script sets
  // it), read from the script at run time, so the executed message and the script's reader are held to one another: the
  // script prints its lost-browser remedy only beside a failure whose message begins with that phrase.
  const why = playwrightInstalled() ? "no playwright browser" : "playwright is not installed under vscode-extension";
  const esc = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const script = fs.readFileSync(path.join(EXT, "scripts", "ci-browser-legs.sh"), "utf8");
  const lit = /awk -v msg="([^"]+)"/.exec(script), sw = /^SWITCH=(\S+)$/m.exec(script);
  if (!lit || !sw) assert.fail("vscode-extension/scripts/ci-browser-legs.sh sets SWITCH and hands awk the phrase it reads a lost browser by (awk -v msg=\"...\")");
  const phrase = lit[1].replace(/\$SWITCH\b/g, sw[1]);
  // the failure's TAP error field, from its start: quoted, or a block scalar whose value opens the next line
  const begins = new RegExp("^\\s*error: [\"'|-]*\\s*" + esc(phrase), "m");
  t.diagnostic("the reason a browser leg names on this machine: " + why);
  const empty = fs.mkdtempSync(path.join(EXT, "out-tests", "no-browsers-"));
  try {
    // the child's environment is built, not inherited: under `node --test` this process carries the runner's NODE_TEST_CONTEXT,
    // and a child inheriting it reports on the runner's channel instead of its stdout
    const base: Record<string, string> = {};
    for (const k of ["PATH", "HOME", "TMPDIR", "NODE_OPTIONS"]) if (process.env[k] !== undefined) base[k] = process.env[k] as string;
    const run = (env: Record<string, string>) => spawnSync(process.execPath, ["--test", "--test-name-pattern=launcher's own leg", __filename],
      { cwd: EXT, encoding: "utf8", timeout: 100000, env: { ...base, ...env, PLAYWRIGHT_BROWSERS_PATH: empty } });
    const req = run({ ROMP_BROWSER_LEGS_REQUIRE: "1" });
    assert.match(req.stdout, /^# fail 1$/m, "the leg failed under the switch\n" + req.stdout.slice(-1500));
    assert.match(req.stdout, new RegExp("ROMP_BROWSER_LEGS_REQUIRE[^\\n]*" + esc(why)), "the switch: a failure naming it and the reason (" + why + ") on one line\n" + req.stdout.slice(-1500));
    assert.match(req.stdout, begins, "under \"1\": the failure's message begins with the phrase the step's script reads a lost browser by (" + phrase + "), so the script prints its lost-browser remedy beside the leg\n" + req.stdout.slice(-1500));
    // any non-empty value arms it (the headers' rule, executed): a value that is not "1" fails the leg the same way
    const yes = run({ ROMP_BROWSER_LEGS_REQUIRE: "yes" });
    assert.match(yes.stdout, /^# fail 1$/m, "the leg failed under the switch set to \"yes\" (any non-empty value arms it)\n" + yes.stdout.slice(-1500));
    assert.match(yes.stdout, new RegExp("ROMP_BROWSER_LEGS_REQUIRE[^\\n]*" + esc(why)), "under \"yes\": a failure naming the switch and the reason (" + why + ") on one line\n" + yes.stdout.slice(-1500));
    assert.match(yes.stdout, begins, "under \"yes\": the failure's message begins with the phrase the step's script reads a lost browser by (" + phrase + ")\n" + yes.stdout.slice(-1500));
    const plain = run({});
    assert.match(plain.stdout, /^# skipped 1$/m, "without the switch the leg skips\n" + plain.stdout.slice(-1500));
    assert.match(plain.stdout, new RegExp(esc(why)), "and the skip names the reason (" + why + ")\n" + plain.stdout.slice(-1500));
  } finally {
    fs.rmSync(empty, { recursive: true, force: true });
  }
});
