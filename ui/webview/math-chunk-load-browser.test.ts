// KaTeX's on-demand chunk (iOS item 6, 2026-10-02) loaded the way a page loads it, in Chromium: the scenes in math-chunk-leg.ts
// run through the shared launcher (real-viewer-leg.ts inBrowser), so in the CI step that runs the rostered legs a lost browser
// fails here instead of skipping. What they hold: a page that shows no math requests no chunk; the first formula requests it once, its TeX
// shown in the pending dress (the sheet's dim tier, a display formula in KaTeX's display box) until the chunk and the two
// common faces are in, then KaTeX's layout in its place; the per-message budget charged per message across the wait; a failed
// load (a 404, a script that registers nothing, a page with no bundle tag) leaves each formula as its source with the reason
// in its title, said once on the console and not retried; a page shaped like the VS Code webview loads the chunk under its
// nonce-only policy. math-chunk-load-webkit-browser.test.ts runs the same scenes in WebKit. Synthetic values only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { inBrowser } from "./real-viewer-leg";
import { SCENES, EXT } from "./math-chunk-leg";

test("the webview-shaped scene models the extension's own policy: script-src by nonce alone, fonts from the webview's source, the bundle tag carrying the nonce", () => {
  const src = fs.readFileSync(path.join(EXT, "src", "extension.ts"), "utf8");
  for (const fn of ["function buildHtml(webview: vscode.Webview): string {", "function buildFeedHtml(webview: vscode.Webview): string {"]) {
    const body = src.slice(src.indexOf(fn), src.indexOf("\n}\n", src.indexOf(fn)));
    assert.ok(body.length > fn.length, fn);
    assert.match(body, /`script-src 'nonce-\$\{n\}'`,/, fn + ": scripts by nonce alone");
    assert.match(body, /`font-src \$\{webview\.cspSource\}`,/, fn + ": KaTeX's faces from the webview's own source");
    assert.match(body, /<script nonce="\$\{n\}" src="\$\{js\}"><\/script>/, fn + ": the bundle tag, nonce on it, that chunk-url.ts derives the chunk's tag from");
  }
});

// one literal bound for every scene (the roster's bound pin reads a literal): the longest scene, the budget's eleven formulas of
// 19,000 characters, takes a few seconds on a loaded box
for (const s of SCENES) {
  test("chromium: " + s.name, { timeout: 120000 }, async (t) => {
    await inBrowser(t, (browser) => s.run(browser, t));
  });
}
