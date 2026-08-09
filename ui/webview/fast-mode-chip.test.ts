// Fast mode (the user 2026-08-07): the CLI refuses fast mode to a non-interactive client unless the
// session opts in through the flag-settings layer, so romp opts in per session and puts the result on a
// statusline chip beside model and effort. render.ts has no jsdom harness → source pins.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const RENDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");
const INTENT = fs.readFileSync(path.resolve(process.cwd(), "src", "pipe-intent.ts"), "utf8");

test("fast is a meta kind with its own on/off choices", () => {
  assert.match(RENDER, /type MetaKind = "mode" \| "model" \| "effort" \| "fast" \| "auth";/);
  assert.match(RENDER, /const FAST_CHOICES/);
  assert.match(RENDER, /mode: MODE_CHOICES, model: MODEL_CHOICES, effort: EFFORT_CHOICES, fast: FAST_CHOICES, auth: AUTH_CHOICES,/);
});

test("the chip appears only where fast mode means something", () => {
  // st.fast is "" for a tmux pane (no flag-settings layer to opt in through) → no chip, the same way
  // an empty model or effort produces none
  assert.match(RENDER, /st\.fast \? "fast" : ""/);
  assert.match(RENDER, /if \(st\.fast\) meta\.appendChild\(metaButton\("fast", prettyFast\(st\.fast\)\)\);/);
});

test("the label carries its own key, since a bare on/off would be meaningless in that row", () => {
  assert.match(RENDER, /case "on": return "fast on";/);
  assert.match(RENDER, /case "cooldown": return "fast limited";/);   // the CLI's own rate limit
});

test("picking a value posts setFast, which survives a kernel-restart window", () => {
  assert.match(RENDER, /kind === "fast" \? "setFast"/);
  assert.match(INTENT, /"setFast"/);   // an explicit state-changing pick, so the pipe holds it
});

test("cooldown still counts as ON in the menu — it is rate-limited, not switched off", () => {
  assert.match(RENDER, /if \(kind === "fast"\) return \(\(st\.fast \|\| ""\)\.toLowerCase\(\) === "off"\) === \(value === "off"\);/);
});

test("the tooltip explains the CLI's refusal rather than leaving a raw reason code", () => {
  assert.match(RENDER, /reason === "model_not_allowed" \? "fast mode needs an Opus model"/);
  assert.match(RENDER, /higher speed, higher credit draw, its own rate limit/);
});

test("fast mode wears its own orange, not the blue accent", () => {
  // Upstream picked this hex for the same badge; sharing it means the two read alike, and it is the
  // right call independently — ui/CLAUDE.md reserves --accent for chrome, and this is a STATUS.
  const CSS = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "styles.css"), "utf8");
  const TIMELINE = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "romp-timeline-view.js"), "utf8");
  assert.match(CSS, /--fast: #ff6a00;/);
  assert.match(RENDER, /kind === "fast"\) return \(st\.fast \|\| ""\) === "on" \? "var\(--fast\)" : "";/);
  assert.match(TIMELINE, /const FAST_ORANGE = '#ff6a00';/);   // the lane's star matches the chat's badge
});
