// Thinking summaries (2026-09-01). Two halves, pinned at the source like the other webview tests
// (the chat renderer has no jsdom harness):
//  - the FEED rule: a thinking block is opaque ("Thinking…") only when it has a signature AND no
//    text. The old `ev.encrypted ? "Thinking…" : ev.text` hid every summary once the kernel asked
//    the API for them, because a summarized block carries both a signature and its text. The
//    kernel computes the flag the same way; the renderer re-checks the text so a bundle talking to
//    an older kernel (flag = signature only) still shows any text it is handed.
//  - the GEAR toggle: a per-install kernel-side checkbox beside the other kernel toggles, stamped
//    with its gesture time like every kernel setting this fork emits, filled from /version, named
//    in the stale-gesture toast — and deliberately NOT in federation's KERNEL_SETTING set, so it
//    never queues for or reaches another machine's kernel.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const ROOT = path.resolve(process.cwd(), "..");
const read = (...p: string[]) => fs.readFileSync(path.join(ROOT, ...p), "utf8");
const RENDER = read("ui", "webview", "render.ts");
const GEAR = read("ui", "webview", "gear.js");
const FED = read("ui", "webview", "federation.ts");
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

test("the gear has a Thinking summaries checkbox among the kernel-side toggles, gesture-stamped, filled from /version", () => {
  assert.ok(GEAR.includes("id=rs-thinksum"), "the checkbox exists in the gear markup");
  const at = GEAR.indexOf("id=rs-thinksum");
  assert.ok(GEAR.indexOf("id=rs-conserve") < at && at < GEAR.indexOf("id=rs-fileedit"),
    "…between Conserve memory and File editing, with the other kernel-side toggles");
  const row = GEAR.slice(at, at + 900);
  assert.match(row, /<b>Thinking summaries<\/b>/);
  assert.ok(!/fleet/i.test(row), "no 'fleet' in the copy (repo vocabulary rule)");
  assert.ok(/new SDK session/.test(row) && /running session picks the change up at its next reconnect/.test(row),
    "the sub-copy is honest that a running session is not switched live");
  assert.ok(/Compact transcript still hides them/.test(row),
    "…and that the compact view (default on) keeps hiding thinking, summaries included");
  assert.ok(GEAR.includes("post({ type: 'setThinkingSummaries', enabled: ths.checked, gt: Date.now() })"),
    "the click posts the kernel's designed message with the gesture stamp minted in the literal");
  assert.ok(GEAR.includes("ths.checked = !!v.thinkingSummaries"),
    "the box always shows the kernel's persisted answer, never a page default");
  assert.match(GEAR, /STALE_LABELS = \{[\s\S]*?'thinking-summaries': 'Thinking summaries'/,
    "a stood-down gesture toasts under the row's own name");
});

test("Thinking summaries is per-install: not a KERNEL_SETTING, so it never propagates", () => {
  const setSrc = FED.match(/const KERNEL_SETTING = new Set\(\[([\s\S]*?)\]\)/);
  assert.ok(setSrc, "federation.ts's KERNEL_SETTING set located");
  assert.ok(!setSrc![1].includes("setThinkingSummaries"),
    "the set must not carry it — this kernel keeps its own copy (the sub-copy says so)");
  assert.ok(!FED.includes("setThinkingSummaries"), "…and no other federation path names it either");
  assert.ok(!KERNEL.includes('"thinkingSummaries", _set_thinking_summaries'),
    "…nor the /judge-settings propagation table on the kernel side");
});
