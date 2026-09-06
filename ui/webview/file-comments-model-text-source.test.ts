// file-comments-model.ts must be TEXT to git. Its two composite reply keys (`commentId + "\0" + ts`) were
// first written with a raw 0x00 byte inside the string literal instead of the `"\0"` escape. A NUL is a
// legal JS string character, so the module typechecked and its tests passed — but git sniffs the first
// 8000 bytes of a blob for NUL and classifies the whole file as binary when it finds one. Both bytes sat
// inside that window, so the slice's diff showed the module as `Bin 0 -> N bytes` with no textual patch
// to review, and the pre-push privacy scan (`.githooks/pre-push`: `git grep -i -I -l -F ...`) skipped it
// outright — `-I` ignores binary blobs — so a personal identifier typed into this file would have pushed
// clean. gitleaks reads `git log -p`, which prints "Binary files differ" for such a blob, so the
// credential scan was blind to it too. The fix is the repo's existing composite-key idiom (elsewhere
// `sid + "\0" + id`); this pins that no raw NUL comes back, and that no UI source drifts into the window.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const WEBVIEW = path.resolve(process.cwd(), "..", "ui", "webview");
const MODEL = path.join(WEBVIEW, "file-comments-model.ts");
const GIT_BINARY_SNIFF_BYTES = 8000; // git's buffer_is_binary() window (xdiff-interface.c)

test("file-comments-model.ts carries no raw NUL byte anywhere", () => {
  const bytes = fs.readFileSync(MODEL);
  assert.equal(bytes.indexOf(0), -1, `raw 0x00 at byte offset ${bytes.indexOf(0)} — write the "\\0" escape instead`);
});

test("the reply keys spell the separator as the \\0 escape, the repo's composite-key idiom", () => {
  const src = fs.readFileSync(MODEL, "utf8");
  // the two composite keys sendParts() builds: the unsent-reply set, and the lookup per stored reply
  assert.match(src, /r\.commentId \+ "\\0" \+ r\.ts/);
  assert.match(src, /c\.id \+ "\\0" \+ r\.ts/);
});

test("no ui/webview source has a NUL inside git's binary sniff window", () => {
  // The property that keeps the privacy backstop and the review diff working for EVERY module here: a
  // file whose first 8000 bytes hold a NUL is `Bin` to git, unreviewable, and invisible to `git grep -I`.
  // (A NUL beyond the window still reads as text today, but is one reorder away from flipping.)
  const offenders: string[] = [];
  for (const name of fs.readdirSync(WEBVIEW)) {
    if (!/\.(ts|js|css|html)$/.test(name)) continue;
    const head = fs.readFileSync(path.join(WEBVIEW, name)).subarray(0, GIT_BINARY_SNIFF_BYTES);
    if (head.indexOf(0) !== -1) offenders.push(`${name}@${head.indexOf(0)}`);
  }
  assert.deepEqual(offenders, [], `raw NUL inside git's ${GIT_BINARY_SNIFF_BYTES}-byte sniff window: ${offenders.join(", ")}`);
});
