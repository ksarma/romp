// The Slice 2 legs (file-view-place-browser, file-view-notebar-browser, file-comments-float-scroll-browser,
// file-view-fold-browser, file-view-place-blocks-browser, file-view-place-reveal-browser, file-view-place-edits-browser,
// file-view-float-anchoring-browser, file-view-leg-page-browser, file-view-place-float-browser,
// file-view-place-html-browser, file-view-place-svg-source-browser, file-view-place-wrapper-end-browser) bundle the
// viewer and read the sheets through
// real-viewer-leg.ts, so the tree that module
// resolves is the tree they test. It must be the cwd's, ../ui/webview from the vscode-extension npm test runs in, the way
// every other browser leg and the node tests beside them find theirs. The module once let an environment variable name
// the tree instead (review of the slice, 2026-09-08): a value left in a shell from running a leg over a copy of the base
// commit would have run these legs over that tree while the rest of the suite read the cwd's, green over a
// regressed tree or red over a good one, with nothing in the output naming either. Two checks: the module reads no
// environment variable at all (what the other legs meet by having no process.env), and with a stale variable of the
// old name in the environment it still resolves the cwd's tree. Running a leg over another tree is done from that
// tree's vscode-extension, as for every leg.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const WEB = path.resolve(process.cwd(), "..", "ui", "webview");

test("real-viewer-leg.ts: the legs' tree is the cwd's ../ui/webview, and no environment variable redirects it", async () => {
  const src = fs.readFileSync(path.join(WEB, "real-viewer-leg.ts"), "utf8");
  assert.ok(!/process\.env\b/.test(src), "the shared leg page reads no environment variable: the tree under test is the cwd's, like every other leg's");
  assert.match(src, /export const UI = path\.resolve\(EXT, "\.\.", "ui", "webview"\)/, "UI is ../ui/webview from EXT, which is process.cwd()");
  const had = Object.prototype.hasOwnProperty.call(process.env, "ROMP_LEG_UI");
  const was = process.env.ROMP_LEG_UI;
  process.env.ROMP_LEG_UI = path.join(WEB, "no-such-tree");                 // the stale shell value the review described
  try {
    const leg = await import("./real-viewer-leg");                          // a dynamic import: the module loads with the variable set
    assert.equal(leg.UI, WEB, "the tree is the cwd's, whatever the environment says");
    assert.ok(fs.existsSync(path.join(leg.UI, "file-view.ts")), "and it holds the viewer the legs bundle");
  } finally {
    if (had) process.env.ROMP_LEG_UI = was; else delete process.env.ROMP_LEG_UI;
  }
});
