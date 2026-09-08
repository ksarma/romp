// The SVG Source view keeps the reader's place as the Raw view does (plans/markdown-viewer.md Slice 2; file-view.ts
// renderBody; the Slice 2 review's third round): its paint reads the place, swaps, runs the seam's hooks, records the
// XML as the text the body was painted from and seats, in the order the Raw branch uses, and the media paint after it
// records no text, so a stale place is never read against a picture or a PDF frame. A source pin, so CI (which runs no
// browser legs) holds the order; file-view-place-svg-source-browser.test.ts measures the reload and the panel toggle in
// headless Chromium. Synthetic fixtures only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const VIEW = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "file-view.ts"), "utf8");
const local = VIEW.split("export function openFileView(")[1].split("\nexport function ")[0];

test("file-view.ts: the SVG Source view's paint reads the place, swaps, runs the hooks, records the XML as shownText and seats; the media paint records no text; those are the only writers of shownText in the viewer, in that order", () => {
  assert.match(local,
    /if \(svgSource && svgText !== null\) \{\n(?:\s*\/\/[^\n]*\n)*\s*const kept = keptPlace\(\);\n\s*body\.replaceChildren\(codeBlock\(svgText, path, true\)\);[^\n]*\n\s*fireRendered\(\);[^\n]*\n\s*shownText = svgText;\n\s*seat\(kept\);\n\s*return;\n\s*\}\n\s*shownText = null;/,
    "the Source view: read, swap, hooks, record, seat; then, for a picture or a frame, no text");
  const writers = Array.from(local.matchAll(/\bshownText = ([^;]+);/g)).map((m) => m[0]);
  assert.deepEqual(writers, ["shownText = svgText;", "shownText = null;", "shownText = text;"], "the Source view's, the media paint's, the text views'");
});
