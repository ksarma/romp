// The live clock a pane runs its ages on (feed-age.ts liveNow): the kernel's `now` on the last frame plus the
// local time elapsed since that frame ARRIVED. Pure, so node --test runs it without a DOM.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { liveNow } from "./feed-age";

test("liveNow adds only the local clock's DELTAS to the kernel's clock — skew between the two never enters", () => {
  const hostNow = 1_000_000;                    // the kernel's clock, as of the frame (epoch s)
  const arrivedMs = 9_000_000_000;              // the browser's clock when the frame landed — hours off the kernel's; irrelevant
  assert.equal(liveNow(hostNow, arrivedMs, arrivedMs), hostNow, "at the arrival the kernel clock IS the frame's `now`");
  assert.equal(liveNow(hostNow, arrivedMs, arrivedMs + 15_000), hostNow + 15, "15 s later, 15 s older");
  assert.equal(liveNow(hostNow, arrivedMs, arrivedMs + 999), hostNow, "whole seconds only: ages never read ahead of the tick");
  assert.equal(liveNow(hostNow, arrivedMs, arrivedMs - 5_000), hostNow, "a local clock that steps BACK cannot make an age negative");
});

test("the anchor is a (now, nowAt) pair that travels with the frame: a re-emit after a quiet hour reads the same live clock as the arrival", () => {
  // federation re-emits the merged frame on a view-order write, on every remote host's frame and on a detach,
  // and the pane sets its clock from whatever frame it is handed. The pair pins the anchor to the WIRE arrival:
  // the same stored frame, re-emitted an hour later, anchors identically. Anchored on the emit instead, every
  // age would go back by the quiet period.
  const T = 1_000_000, arrivedMs = 5_000_000, hourLater = arrivedMs + 3_600_000;
  const anchor = (m: { now: number; nowAt?: number }, handledMs: number) =>
    liveNow(m.now, typeof m.nowAt === "number" ? m.nowAt : handledMs, handledMs);   // fleet.ts's rule
  assert.equal(anchor({ now: T, nowAt: arrivedMs }, arrivedMs), T, "at the arrival");
  assert.equal(anchor({ now: T, nowAt: arrivedMs }, hourLater), T + 3600, "the re-emit keeps the hour");
  assert.equal(anchor({ now: T }, hourLater), T, "a frame with no pair anchors on the handling — the VS Code pipe's frames, which are never re-emitted");
});
