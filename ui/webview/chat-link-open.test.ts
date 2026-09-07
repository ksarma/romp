// Links in the chat must follow on click (the user 2026-06-25). On the web dashboard the old handler only
// ever postMessage'd the host an openLink — but the kernel has no openLink handler, so a link click did
// nothing on the web dashboard. Now the click handler splits by host: a web origin (http/https) opens the
// link in the viewer's own browser via window.open; a VS Code webview (vscode-webview: origin) still routes
// to the host extension's openExternal. The chat renderer has no jsdom harness, so pin it at the source.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const RENDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");

// isolate the global anchor-click handler
const HANDLER = (RENDER.match(/closest\?\.\("a\[href\]"\)[\s\S]*?\}, true\);/) || [""])[0];

test("the chat has a global a[href] click handler", () => {
  assert.ok(HANDLER, "found the anchor-click handler");
  assert.match(HANDLER, /e\.preventDefault\(\)/);
});

test("web dashboard (http/https origin) opens the link in the viewer's browser", () => {
  assert.match(HANDLER, /location\.protocol === "http:" \|\| location\.protocol === "https:"/);
  assert.match(HANDLER, /window\.open\(href, "_blank", "noopener,noreferrer"\)/);
});

test("VS Code webview still routes the link to the host (openExternal)", () => {
  assert.match(HANDLER, /vscodeApi\.postMessage\(\{ type: "openLink", href \}\)/);
});

// A control the file-comments panel paints INTO a linked figure in the viewer (a region's rectangle, the overlay a
// press is handed on from, a framed picture) is the panel's activation: its delegate opens the card and cancels the
// anchor. This handler runs first, at the capture phase, and used to open the tab instead (twice with the panel open)
// while no card opened (the 2026-09-06 review of Slice 3). It now asks the panel's registry (panelMark, exact: the
// elements the panel made, never a class or data-act the file's own markup may wear) before it touches the event.
// file-comments-regions-review-3.test.ts drives the panel under a copy of this handler; this pins the handler's side.
test("a click on a file-comments mark inside a linked figure is left to the panel: panelMark is asked before preventDefault", () => {
  assert.match(RENDER, /^import \{ panelMark \} from "\.\/file-comments";$/m, "the registry is the panel's own export");
  assert.match(HANDLER, /if \(panelMark\(e\.target as Element \| null\)\) return;/);
  const ask = HANDLER.indexOf("panelMark(");
  const cancel = HANDLER.indexOf("e.preventDefault()");
  const scheme = HANDLER.indexOf("/^[a-z][a-z0-9+.-]*:/i.test(href)");
  assert.ok(ask > -1 && cancel > -1 && ask < cancel, "the panel's marks are excused before the event is cancelled");
  assert.ok(scheme > -1 && ask < scheme, "…and before the href is even read: whatever the link, the mark is the panel's");
});

test("the web path is checked before the vscode path (web origin wins)", () => {
  const web = HANDLER.indexOf("window.open(href");
  const code = HANDLER.indexOf('type: "openLink"');
  assert.ok(web > -1 && code > -1 && web < code, "window.open branch precedes the openLink branch");
});
