// Thinking summaries (2026-09-01), pinned at the source like the other webview tests (the chat
// renderer has no jsdom harness):
//  - the FEED rule: a thinking block is opaque ("Thinking…") only when it has a signature AND no
//    text. The old `ev.encrypted ? "Thinking…" : ev.text` hid every summary once the kernel asked
//    the API for them, because a summarized block carries both a signature and its text. The
//    kernel computes the flag the same way; the renderer re-checks the text so a bundle talking to
//    an older kernel (flag = signature only) still shows any text it is handed.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const ROOT = path.resolve(process.cwd(), "..");
const read = (...p: string[]) => fs.readFileSync(path.join(ROOT, ...p), "utf8");
const RENDER = read("ui", "webview", "render.ts");
const KERNEL = read("bin", "romp-kernel");

test("a thinking block is opaque only when signed AND textless — a summary renders its text", () => {
  const at = RENDER.indexOf('if (ev.kind === "thinking") {');
  assert.ok(at > 0, "the thinking branch exists");
  const branch = RENDER.slice(at, at + 1400);
  assert.match(branch, /const opaque = ev\.encrypted && !\(ev\.text \|\| ""\)\.trim\(\);/,
    "the renderer re-derives opacity from the text it was handed, never from the flag alone");
  assert.match(branch, /t\.textContent = opaque \? "Thinking…" : ev\.text;/);
  assert.match(branch, /if \(opaque\) \{ turn\.appendChild\(t\); return turn; \}/,
    "only the opaque block is the one-liner; a text-bearing block falls through to the clamp");
  assert.ok(!/ev\.encrypted \? "Thinking…"/.test(branch), "the old flag-only rule is gone");
  // the text-bearing path keeps progressive disclosure: clamped to ~2 lines, click to expand, state keyed
  assert.match(branch, /el\("div", "think-clamp"\)/);
  assert.match(branch, /applyFold\(clamp, "expanded", tkey\)/);
});

test("the kernel computes the flag by the same rule (signature AND no text)", () => {
  assert.ok(KERNEL.includes('"encrypted": bool(b.get("signature")) and not (b.get("thinking") or "").strip()'),
    "the ChatEvent builder's flag means opaque, not merely signed");
});
