// The switch that makes a browser leg's launch skip a failure. A browser leg (a test module that launches a Playwright
// browser) skips, and says why, where the browser cannot be launched: on a machine without Playwright's browsers, and
// in the gating CI job's Test step, which runs npm test before the job installs Chromium. The step "Browser legs
// (node --test over ci-browser-legs.txt)" in .github/workflows/ci.yml runs the legs named in
// vscode-extension/ci-browser-legs.txt after that install with ROMP_BROWSER_LEGS_REQUIRE=1, and under the switch a skip
// here is a thrown error naming the reason and the remedy, so a runner that lost its browser turns the step red rather
// than green with the coverage gone (the stance ROMP_UI_BENCH_REQUIRE and ROMP_SERVED_TESTS_REQUIRE take for the pane
// bench and the served-page tests). Unset, or any value but "1", nothing changes: the leg skips as before.
// real-viewer-leg.ts's inBrowser launches through launchBrowser, so every leg that imports it reads the switch; a leg
// with a launch of its own reaches the switch by calling launchBrowser (or skipOrFail) itself.
// browser-legs-require.test.ts pins both branches by execution. Test-only: no webview bundle imports it.
export const BROWSER_LEGS_REQUIRE = "ROMP_BROWSER_LEGS_REQUIRE";

/** The fixed phrase a failed Chromium launch carries under the switch: the gating job installs that browser in the
 *  step before the legs run, so its absence is that step's to explain. */
export const LOST_BROWSER = "the runner lost its browser: check the Chromium install step";

type Env = Record<string, string | undefined>;

/** True when the environment demands that a browser leg run: the switch is set to exactly "1". */
export function browserLegsRequired(env: Env = process.env): boolean {
  return env[BROWSER_LEGS_REQUIRE] === "1";
}

/** Skip the test with `why`, or, under the switch, throw an error carrying the switch's name, `why` and `remedy`. */
export function skipOrFail(t: any, why: string, remedy: string, env: Env = process.env): void {
  if (browserLegsRequired(env)) throw new Error(BROWSER_LEGS_REQUIRE + "=1 and this browser leg cannot run: " + why + ". " + remedy);
  t.skip(why);
}

/** Launch `engine` (Chromium unless named) through `pw`, the playwright module (null when it is not installed), and
 *  return the browser. On a missing package or a failed launch: skip the test and return null, or under the switch throw
 *  with the reason's first line and the remedy (a Chromium launch: LOST_BROWSER; another engine: the gating job installs
 *  Chromium only). */
export async function launchBrowser(
  t: any,
  pw: any,
  engine: "chromium" | "firefox" | "webkit" = "chromium",
  launchOpts: any = {},
  env: Env = process.env,
): Promise<any | null> {
  if (!pw) {
    skipOrFail(t, "playwright is not installed under vscode-extension; the browser leg needs it", "run npm ci in vscode-extension (in CI: check the Install deps step)", env);
    return null;
  }
  try {
    return await pw[engine].launch(launchOpts);
  } catch (e) {
    const first = String((e as Error).message).split("\n")[0];
    const remedy = engine === "chromium"
      ? LOST_BROWSER
      : "the gating job installs Chromium only; a leg that launches " + engine + " belongs in ci-browser-legs-excluded.txt with that reason";
    skipOrFail(t, "no playwright " + engine + " on this box; the browser leg needs it: " + first, remedy, env);
    return null;
  }
}
