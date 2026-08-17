// The context battery's id belongs to the STATUSLINE copy alone (found 2026-08-17, in passing, while fixing
// the stuck tab tip). ctxBar() used to mint a hardcoded id="ctx-bar" on every battery it built — and the tab
// tip embeds one too, so an open tip put a SECOND #ctx-bar in the document. The 1s ticker resolves that id
// with getElementById and only document order (statusline before the body-appended tip) saved it from
// refreshing the tip's battery with the ACTIVE session's context — wrong whenever the hovered tab isn't the
// active one. The id now moves to the statusline's call site: ctxBar() mints none, the tip's copy carries
// none, and the ticker still resolves the statusline's battery — now the only #ctx-bar there is.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const RENDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");

test("ctxBar() mints NO id — the id is not the widget's, it is the statusline slot's", () => {
  const start = RENDER.indexOf("function ctxBar()");
  assert.ok(start > 0, "ctxBar exists");
  const fn = RENDER.slice(start, RENDER.indexOf("\n}", start) + 2);
  assert.doesNotMatch(fn, /\.id\s*=/, "no id inside the shared widget builder");
});

test("exactly ONE #ctx-bar minter in the file: the statusline call site", () => {
  assert.equal((RENDER.match(/\.id = "ctx-bar"/g) || []).length, 1, "one minter, so ids stay unique with a tip open");
  assert.match(RENDER, /const bar = ctxBar\(\);\n\s*bar\.id = "ctx-bar";/, "the statusline opts in at its call site");
});

test("the statusline ticker's in-place refresh still resolves the statusline battery by that id", () => {
  // byte-for-byte the ticker lookup that shipped: same id, same setCtxBar refresh (unchanged behavior)
  assert.match(RENDER, /const bar = document\.getElementById\("ctx-bar"\);\n\s*if \(bar\) setCtxBar\(bar, s\.status\.ctx, s\.status\.state === "compacting", s\.status\.ctxColor\);/);
});

test("the tab tip's battery comes from the bare builder — no id rides into the tip", () => {
  // the tip's call stays argument-less (pinned byte-identical in tab-backend-tooltip.test.ts too), and with
  // ctxBar() minting nothing, the tip can never shadow or duplicate the statusline's id again
  assert.match(RENDER, /const bar = ctxBar\(\); setCtxBar\(bar, s\.status\.ctx/);
  assert.doesNotMatch(RENDER, /id="ctx-bar"/, "no markup-side mint either");
});
