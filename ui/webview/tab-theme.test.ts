// The chat-tab appearance themes (T113, the user 2026-08-27, reacting to PR 730's strip pass):
// CLASSIC is the tuned default — no line under the strip (multi-row strips made it read wrong),
// the pre-730 thick selected ring back ("really easy to tell which one is selected"), the one
// keeper from 730 (per-tab identity distinguishability) at the user's ~5% wash, and faded tab
// labels ~20% brighter (an older complaint). YATHARTH is 730's aesthetic exactly as merged,
// opt-in via settings and named for its contributor at the user's explicit ask. The seam is the
// CHAT TAB STRIP only. Source pins per the repo convention; the round-trip is executable.
import { test } from "node:test";
import assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { chatTabTheme, DEFAULT_SETTINGS } from "./settings";

const ui = (...p: string[]) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", ...p), "utf8");
const RENDER = ui("webview", "render.ts");
const CSS = ui("webview", "styles.css");
const GEAR = ui("webview", "gear.js");

test("the setting round-trips: classic default, yatharth opt-in, junk normalizes", () => {
  assert.equal(DEFAULT_SETTINGS.chatTabTheme, "classic");
  assert.equal(chatTabTheme("yatharth"), "yatharth");
  assert.equal(chatTabTheme("classic"), "classic");
  assert.equal(chatTabTheme(undefined), "classic");
  assert.equal(chatTabTheme("sparkles"), "classic");
});

test("the theme applies LIVE through the scheme plumbing — a body class, no reload", () => {
  assert.match(RENDER, /document\.body\.classList\.toggle\("chat-theme-yatharth", s\.chatTabTheme === "yatharth"\);/);
  // onExternalSettingsChange already re-runs applyChatScheme + renderTabs on every settings write
  assert.match(RENDER, /onExternalSettingsChange\(\(s\) => \{ settings = s; applyChatScheme\(s\); renderTabs\(\);/);
});

test("Classic: no strip line, the thick ring, the 5% wash (tunable vars), the stand-down", () => {
  assert.match(CSS, /#tabbar \{ --tab-tint-rest: 5%; --tab-tint-hover: 8%; --tab-tint-active: 5%; \}/);
  assert.match(CSS, /border-bottom: 1px solid transparent;/);
  assert.match(CSS, /\.tab\.active\.colored:not\(\.tab-blocked\) \{[^}]*box-shadow: inset 0 0 0 1\.5px var\(--chip-bg\);/s);
  assert.match(CSS, /\.tab\.tab-blocked\.active\.colored \{ box-shadow: none; \}/, "blocked outranks the ring (2026-07-24)");
});

test("Classic: faded tab labels brighten ~20% — one tunable knob, yatharth keeps the full fade", () => {
  assert.match(RENDER, /const CLASSIC_FADE_SCALE = 0\.8;/);
  assert.match(RENDER, /const scale = settings\.chatTabTheme === "yatharth" \? 1 : CLASSIC_FADE_SCALE;/);
  assert.match(RENDER, /const t = Math\.min\(0\.85, \(Lc - Lt\) \/ \(Lc - Lb\)\) \* scale;/);
});

test("Yatharth: PR 730's strip values verbatim, scoped to the theme class", () => {
  assert.match(CSS, /body\.chat-theme-yatharth #tabbar \{\n  --tab-tint-rest: 9%; --tab-tint-hover: 15%; --tab-tint-active: 22%;/);
  assert.match(CSS, /body\.chat-theme-yatharth #tabbar \{[^}]*border-bottom: 1px solid color-mix\(in srgb, var\(--active-accent, rgba\(255, 255, 255, 0\.3\)\) 40%, transparent\);/s);
  assert.match(CSS, /body\.chat-theme-yatharth \.tab\.active\.colored:not\(\.tab-blocked\) \{[^}]*box-shadow: none;/s);
});

test("the gear offers the picker in the one menu vocabulary, Classic first", () => {
  assert.match(GEAR, /\{ id: 'classic', name: 'Classic',/);
  assert.match(GEAR, /\{ id: 'yatharth', name: 'Yatharth',/);
  assert.match(GEAR, /s\.chatTabTheme = th\.id; save\(s\); ttPaint\(\);/);
});
