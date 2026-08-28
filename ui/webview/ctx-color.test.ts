// The ONE context-pressure threshold pair (2026-08-27): warn 70, danger 88 — replacing the 60/85
// ctx-gauge triple and the 70/90 usage-bar pair that disagreed about when the same fullness turns
// alarming. kernel/colormap.py owns the canonical pair (pinned by test_kernel_context_colormap);
// this pins the client mirror and the timeline's inlined copy (plain JS in a foreign host — it
// cannot import, so equality is enforced by grep, the STOPS-parity precedent).
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { CTX_WARN, CTX_DANGER, ctxFallbackColor } from "./ctx-color";

const ui = (...p: string[]) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", ...p), "utf8");

test("the pair is 70/88 and the palette is calm-teal / warn amber / alarm red", () => {
  assert.equal(CTX_WARN, 70);
  assert.equal(CTX_DANGER, 88);
  assert.equal(ctxFallbackColor(0), "#5196B8");
  assert.equal(ctxFallbackColor(CTX_WARN - 1), "#5196B8");
  assert.equal(ctxFallbackColor(CTX_WARN), "#d7a23a");
  assert.equal(ctxFallbackColor(CTX_DANGER - 1), "#d7a23a");
  assert.equal(ctxFallbackColor(CTX_DANGER), "#c0392b");
  assert.equal(ctxFallbackColor(100), "#c0392b");
});

test("the timeline's inlined copies match (it runs inside Obsidian and cannot import)", () => {
  const TL = ui("romp-timeline-view.js");
  const inlined = TL.match(/>= 88 \? '#c0392b' : \(p(?:ct)? >= 70 \? '#d7a23a' : '#5196B8'\)/g) || [];
  assert.equal(inlined.length, 2, "both timeline fallbacks (ctx gauge + usage bar) carry the pair");
  assert.doesNotMatch(TL, />= 85 \? '#c0392b'|>= 90 \? '#c0392b'/, "the old 60/85 and 70/90 pairs are gone");
});

test("kernel and client state the same pair (grep parity — the kernel is python)", () => {
  const CM = fs.readFileSync(path.resolve(process.cwd(), "..", "kernel", "colormap.py"), "utf8");
  assert.match(CM, /CTX_WARN, CTX_DANGER = 70, 88/);
});
