// The KaTeX chunk's loading scenes (math-chunk-leg.ts) in WebKit, the phone's engine: the same scenes the Chromium leg runs
// (math-chunk-load-browser.test.ts). WebKit is optional: CI installs Chromium alone, so a machine without Playwright's WebKit
// skips here by name, and this file is not on the CI roster. Synthetic values only.
import { test } from "node:test";
import * as path from "node:path";
import { createRequire } from "node:module";
import { SCENES, EXT } from "./math-chunk-leg";

let pw: any = null;
try { pw = createRequire(path.join(EXT, "package.json"))("playwright"); } catch { pw = null; }

for (const s of SCENES) {
  test("webkit: " + s.name, { timeout: s.timeout }, async (t) => {
    if (!pw) { t.skip("optional: playwright is not installed under vscode-extension"); return; }
    let browser: any;
    try { browser = await pw.webkit.launch(); }
    catch (e) { t.skip("optional: no playwright webkit on this machine: " + String((e as Error).message).split("\n")[0]); return; }
    try { await s.run(browser, t); } finally { await browser.close(); }
  });
}
