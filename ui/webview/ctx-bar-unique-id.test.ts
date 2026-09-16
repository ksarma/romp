// The context battery's id belongs to the STATUSLINE copy alone (found 2026-08-17, in passing, while fixing
// the stuck tab tip). ctxBar() used to mint a hardcoded id="ctx-bar" on every battery it built — and the tab
// tip embeds one too, so an open tip put a SECOND #ctx-bar in the document. The 1s ticker resolves that id
// with getElementById and only document order (statusline before the body-appended tip) saved it from
// refreshing the tip's battery with the ACTIVE session's context — wrong whenever the hovered tab isn't the
// active one. The id then moved to the statusline's call site. Since T415 part two (upstream's status-controls.ts,
// adopted at the 2026-09-15 pull-in) the battery's builder is that module's shared ctxBar, imported here as
// buildCtxBar: it mints no id; render.ts keeps a one-line wrapper ctxBar() that mints the statusline slot's id for
// the statusline's call alone; the tab tip calls the bare builder, so its copy carries none; and the ticker still
// resolves the statusline's battery, the only #ctx-bar there is.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const RENDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");
const CONTROLS = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "status-controls.ts"), "utf8");

test("the shared builder (status-controls.ts's ctxBar, imported as buildCtxBar) mints NO id; render.ts's one-line wrapper ctxBar() mints the statusline slot's", () => {
  // the builder, upstream's (T415 part two): the widget's markup and the /compact click, no id
  assert.match(RENDER, /import \{[^}]*\bctxBar as buildCtxBar\b[^}]*\} from "\.\/status-controls";/, "render.ts imports the shared builder under the name buildCtxBar");
  const start = CONTROLS.indexOf("export function ctxBar(");
  assert.ok(start > 0, "the shared builder exists");
  const fn = CONTROLS.slice(start, CONTROLS.indexOf("\n}", start) + 2);
  assert.doesNotMatch(fn, /\.id\s*=/, "no id inside the shared widget builder");
  // the wrapper: the builder's bar with the statusline's id and nothing else, on one line
  assert.match(RENDER, /^function ctxBar\(\): HTMLElement \{ const bar = buildCtxBar\(compactActiveSession\); bar\.id = "ctx-bar"; return bar; \}$/m, "the wrapper is the statusline's minter");
  // the tip's call: the bare builder, and no id assignment on its line or the one after (the bar goes into the row)
  const tip = RENDER.indexOf("const bar = buildCtxBar(compactActiveSession); setCtxBar(bar, s.status.ctx");
  assert.ok(tip > 0, "the tab tip builds its battery from the bare builder");
  const tipLines = RENDER.slice(tip, RENDER.indexOf("\n", RENDER.indexOf("\n", tip) + 1));
  assert.doesNotMatch(tipLines, /\.id\s*=/, "no id assignment rides into the tip's copy");
});

test("exactly ONE #ctx-bar minter in the file: the wrapper, which the statusline alone calls", () => {
  assert.equal((RENDER.match(/\.id = "ctx-bar"/g) || []).length, 1, "one minter, so ids stay unique with a tip open");
  assert.match(RENDER, /const bar = ctxBar\(\);\s+\/\/ the wrapper mints the statusline slot's id/, "the statusline takes its battery from the wrapper, and says why");
  assert.equal((RENDER.match(/(?<!function )\bctxBar\(\)/g) || []).length, 1, "the wrapper has one caller: the statusline (the tip calls the bare builder)");
});

test("the statusline ticker's in-place refresh still resolves the statusline battery by that id", () => {
  // byte-for-byte the ticker lookup that shipped: same id, same setCtxBar refresh (the fill goes
  // through pickTone since the 2026-09-01 dual-palette fold, and the past-100% flag ctxOver rides as the
  // fifth argument since 2026-09-02 — the lookup contract is unchanged)
  assert.match(RENDER, /const bar = document\.getElementById\("ctx-bar"\);\n\s*if \(bar\) setCtxBar\(bar, s\.status\.ctx, s\.status\.state === "compacting", pickTone\(s\.status\.ctxColor, s\.status\.ctxTone\), s\.status\.ctxOver\);/);
});

test("the tab tip's battery comes from the bare builder: no id rides into the tip", () => {
  // the tip calls the shared builder with the chat's /compact click (pinned byte-identical in tab-backend-tooltip.test.ts
  // too), never the wrapper, so it can never shadow or duplicate the statusline's id again
  assert.match(RENDER, /const bar = buildCtxBar\(compactActiveSession\); setCtxBar\(bar, s\.status\.ctx/);
  assert.doesNotMatch(RENDER, /id="ctx-bar"/, "no markup-side mint either");
});
