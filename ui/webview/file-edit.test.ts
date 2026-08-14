// Raw-mode editing in the file viewer (plans/file-browser.md slice 2, the user 2026-08-14): a plain
// textarea over the existing raw view, saved through the sid-routed saveFile WS op with an mtime
// conflict floor — agents edit the same trees, so a stale save REFUSES instead of overwriting.
// Source pins (no jsdom for these modules), the repo convention.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const web = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const VIEW = web("file-view.ts");
const FEED = web("feed.ts");
const FEED_CSS = web("feed.css");
const KERNEL = fs.readFileSync(path.resolve(process.cwd(), "..", "kernel", "kernel.py"), "utf8");

test("Edit arms only off the kernel's own verdicts: text/plain + a Last-Modified anchor", () => {
  assert.match(VIEW, /isText = \(r\.headers\.get\("Content-Type"\) \|\| ""\)\.startsWith\("text\/plain"\);/);
  assert.match(VIEW, /const lm = r\.headers\.get\("Last-Modified"\);/);
  assert.match(VIEW, /editBtn\.hidden = editing \|\| text === null \|\| !isText \|\| !mtime;/);
  // markdown edits from its RAW view — what you edit is what raw shows
  assert.match(VIEW, /if \(isMd && fmt\.md === "rendered"\) \{ fmt\.md = "raw"; saveFmt\(fmt\); \}/);
});

test("the save rides the sid-routed WS op with the mtime floor, and acknowledges before the round-trip", () => {
  assert.match(VIEW, /post\(\{ type: "saveFile", path, sid: sid \|\| undefined, content, baseMtime: mtime, reqId: saveSeq \}\);/);
  assert.match(VIEW, /saveBtn\.disabled = true; saveBtn\.textContent = "Saving…";/);
  // Ctrl/Cmd+S in the editor is the same save
  assert.match(VIEW, /\(e\.ctrlKey \|\| e\.metaKey\) && e\.key\.toLowerCase\(\) === "s"/);
  // replies route by reqId through the boot listener
  assert.match(VIEW, /m\.type === "fileSaved" && editHooks && m\.reqId === editHooks\.reqId/);
  assert.match(VIEW, /m\.type === "fileSaveFailed" && editHooks && m\.reqId === editHooks\.reqId/);
});

test("no exit path can silently eat an edited buffer", () => {
  // the guard lives in closeFileView itself — the browser overlay and Escape close through it
  assert.match(VIEW, /if \(closeGuard && !closeGuard\(\)\) return;/);
  // …and the REPLACE path (opening file B over a dirty editor) asks the same question
  assert.match(VIEW, /if \(document\.getElementById\("romp-fileview"\) && closeGuard && !closeGuard\(\)\) return;/);
  assert.match(VIEW, /const confirmDiscard = \(\): boolean =>\n    !editing \|\| !dirty \|\| window\.confirm/);
  // Escape peels edit mode first, never the whole viewer
  assert.match(VIEW, /if \(editing\) \{\s*\/\/ Escape peels edit mode first, never the whole viewer\n      if \(confirmDiscard\(\)\) exitEdit\(\);\n      return;\n    \}/);
});

test("a conflict keeps the buffer, says why, and Reload asks before discarding", () => {
  assert.match(VIEW, /body\.prepend\(bar2\);/, "the error bar sits ABOVE the textarea — the buffer survives");
  assert.match(VIEW, /if \(\/changed on disk\/\.test\(err\)\) \{/);
  assert.match(VIEW, /dirty = false;\s*\/\/ confirmed once — the replace guard must not ask twice/);
});

test("the kernel's save is atomic, mode-preserving, and refuses the concurrent-agent overwrite", () => {
  assert.match(KERNEL, /def _save_file\(raw, sid, content, base_mtime\):/);
  assert.match(KERNEL, /if int\(st\.st_mtime\) != int\(base_mtime or 0\):/);
  assert.match(KERNEL, /changed on disk since you opened it/);
  assert.match(KERNEL, /fd, tmp = tempfile\.mkstemp\(prefix="\.romp-save-", dir=d\)/);
  assert.match(KERNEL, /os\.replace\(tmp, p\)/);
  assert.match(KERNEL, /os\.chmod\(tmp, stat\.S_IMODE\(st\.st_mode\)\)/);
  assert.match(KERNEL, /elif msg and msg\.get\("type"\) == "saveFile":/);
});

test("the feed boots the viewer with the poster, and the editor wears the code view's metrics", () => {
  assert.match(FEED, /initFileView\(\(m\) => vscodeApi\?\.postMessage\(m\)\);/);
  assert.match(FEED_CSS, /\.fileview-editor \{ flex: 1 1 auto; min-height: 0; width: 100%;/);
});
