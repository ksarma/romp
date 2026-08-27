// The chat-tab appearance themes (T113, tightened by T115, tuned by T118 — the user 2026-08-27):
// CLASSIC, the default, is the PRE-720 tab strip modulo exactly THREE sanctioned deltas —
// typography (the strip inherits the global Inter/type ladder), T123's 1px hover-gray rest
// outline, T118's 0.9 faded-label scale, and T125's strip band (the multi-row grounding). Everything else reads pre-720: NO identity tint at any state, the thick 1.5px
// selected ring, the neutral line under the strip, gap 0. T115 verified the baseline equality by
// pixel-diffing a real pre-720 build: with fonts normalized, zero differing pixels outside the
// (out-of-scope) tag-controls box — a re-run must subtract the two T118 washes the same way it
// subtracts fonts. YATHARTH is the contributor's merged strip aesthetic exactly, opt-in via
// settings and named for him at the user's explicit ask. The seam is the CHAT TAB STRIP only.
// Source pins per the repo convention; the round-trip is executable.
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

test("Classic: the pre-720 strip verbatim — line, gap 0, gray active fill, ring, stand-down", () => {
  assert.match(CSS, /border-bottom: 1px solid var\(--box-border\);/);
  assert.match(CSS, /#tabs \{ display: flex; flex: 1 1 auto; flex-wrap: wrap; align-items: stretch; gap: 0; \}/);
  assert.match(CSS, /\.tab\.active \{ color: var\(--fg\); background: rgba\(255, 255, 255, 0\.14\); \}/);
  assert.match(CSS, /\.tab\.active\.colored \{ box-shadow: inset 0 0 0 1\.5px var\(--chip-bg\); \}/);
  assert.match(CSS, /\.tab\.tab-blocked\.active\.colored \{ box-shadow: none; \}/, "blocked outranks the ring (2026-07-24)");
});

test("Classic: NO identity tint — every tint rule lives under the theme class", () => {
  // The user revoked the IDENTITY wash (T115 amendment): outside the yatharth block there must be
  // no identity-tinted tab background at all. Every tinted background in the stylesheet is scoped.
  // (T123's rest OUTLINE is neutral hover-gray, not identity — pinned in its own test below.)
  const tintRules = CSS.split("\n").filter((l) => /\.tab[^{]*\{[^}]*color-mix\(in srgb, var\(--chip-bg\)/.test(l));
  for (const l of tintRules) assert.match(l, /^body\.chat-theme-yatharth /, "tint rule must be theme-scoped: " + l);
  const ringLine = CSS.match(/^\.tab\.active\.colored \{.*$/m)![0];
  assert.ok(!ringLine.includes("color-mix"), "the classic selected tab is the gray fill + ring, no tint layer");
});

test("Classic: faded labels brighten 10% — one tunable knob, Yatharth keeps his full fade (T118)", () => {
  assert.match(RENDER, /const CLASSIC_FADE_SCALE = 0\.9;/);
  assert.match(RENDER, /const scale = settings\.chatTabTheme === "yatharth" \? 1 : CLASSIC_FADE_SCALE;/);
  assert.match(RENDER, /const t = Math\.min\(0\.85, \(Lc - Lt\) \/ \(Lc - Lb\)\) \* scale;/);
});

test("Classic: the rest OUTLINE — 1px in the hover gray, no fill, states stand down (T123)", () => {
  const rule = CSS.match(/^body:not\(\.chat-theme-yatharth\) \.tab([^ ]*) \{ border-color: (rgba\([^)]*\)); \}$/m);
  assert.ok(rule, "the rest-outline rule exists, body-scoped OUT of the Yatharth theme");
  assert.equal(rule![2], "rgba(255, 255, 255, 0.06)", "EXACTLY the hover fill's gray — tune them in lockstep");
  for (const excl of [":not(.tab-blocked)", ":not(.active)", ":not(.tab-add)"]) {
    assert.ok(rule![1].includes(excl), "the outline stands down for " + excl.slice(5, -1) +
      " — those states own their border/ring band");
  }
  // border-color is a different property from the state FILLS, so hover needs no exclusion — the
  // outline stays under hover's fill (same color, one object filling in) and the fill itself…
  assert.match(CSS, /\.tab:hover \{ color: var\(--fg\); background: rgba\(255, 255, 255, 0\.06\); \}/);
  // …and no resting FILL remains: the T118 2% wash was replaced by this outline (T123).
  assert.doesNotMatch(CSS, /\.tab[^{]*\{ background: rgba\(255, 255, 255, 0\.0[24]\); \}/);
});

test("Yatharth: his strip verbatim, scoped to the theme class", () => {
  assert.match(CSS, /body\.chat-theme-yatharth #tabbar \{\n  border-bottom: 1px solid color-mix\(in srgb, var\(--active-accent, rgba\(255, 255, 255, 0\.3\)\) 40%, transparent\);\n\}/);
  assert.match(CSS, /body\.chat-theme-yatharth #tabs \{ gap: 0 3px; \}/, "his 3px seam of air between the flat tints");
  assert.match(CSS, /body\.chat-theme-yatharth \.tab\.colored:not\(\.tab-blocked\) \{\n  background: color-mix\(in srgb, var\(--chip-bg\) 9%, transparent\);\n\}/);
  assert.match(CSS, /body\.chat-theme-yatharth \.tab\.colored:not\(\.tab-blocked\):hover \{\n  background: color-mix\(in srgb, var\(--chip-bg\) 15%, transparent\);\n\}/);
  assert.match(CSS, /body\.chat-theme-yatharth \.tab\.active\.colored:not\(\.tab-blocked\) \{\n  background: color-mix\(in srgb, var\(--chip-bg\) 22%, transparent\);\n  border-color: color-mix\(in srgb, var\(--chip-bg\) 55%, transparent\);\n  box-shadow: none;\n\}/);
});

test("Classic: the strip is a BAND — a 3% plane over the page bg, closed by the hairline (T125)", () => {
  // The user (2026-08-27, screenshot): wrapped rows read as floating boxes. The survey verdict
  // across editors (VS Code wrapTabs, JetBrains multi-row), browsers/terminals, and design-system
  // specs (Material's mandatory divider, Carbon/Ant contained tabs) is unanimous: containment
  // comes from the strip owning a background PLANE, closed by ONE bottom hairline — not from
  // per-row lines. 3% white over --bg reproduces VS Code's canonical #252526-over-#1E1E1E band.
  assert.match(CSS, /^body:not\(\.chat-theme-yatharth\) #tabbar \{ background: linear-gradient\(rgba\(255, 255, 255, 0\.03\), rgba\(255, 255, 255, 0\.03\)\), var\(--vscode-sideBar-background, var\(--bg\)\); \}$/m,
    "the band: one Classic-scoped background line, tunable in place; Yatharth keeps his merged look");
  assert.match(CSS, /border-bottom: 1px solid var\(--box-border\);/, "…closed by the ONE existing hairline at the band's bottom edge");
});

test("the gear offers the picker in the one menu vocabulary, Classic first", () => {
  assert.match(GEAR, /\{ id: 'classic', name: 'Classic',/);
  assert.match(GEAR, /\{ id: 'yatharth', name: 'Yatharth',/);
  assert.match(GEAR, /housePick\(tt, 'tabtheme', tabThemeRowHTML, function \(id\) \{ var s = load\(\); s\.chatTabTheme = id; save\(s\); ttPaint\(\); \}\);/);
});
