// The chat-tab appearance themes (T113, tightened by T115 — the user 2026-08-27, reacting to the
// contributor's strip pass): CLASSIC, the default, is the PRE-720 tab strip byte-for-byte, with
// typography the ONE permitted difference — the user's amended words: fine with any font changes,
// nothing else. So: NO identity tint at any state, the thick 1.5px selected ring, the neutral
// line under the strip, gap 0, and the full pre-720 label fade. T115 verified this by pixel-diffing
// a real pre-720 build: with fonts normalized, zero differing pixels outside the (out-of-scope)
// tag-controls box. YATHARTH is the contributor's merged strip aesthetic exactly, opt-in via
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
  // The user revoked the at-rest wash (T115 amendment): outside the yatharth block there must be
  // no identity-tinted tab background at all. Every tinted background in the stylesheet is scoped.
  const tintRules = CSS.split("\n").filter((l) => /\.tab[^{]*\{[^}]*color-mix\(in srgb, var\(--chip-bg\)/.test(l));
  for (const l of tintRules) assert.match(l, /^body\.chat-theme-yatharth /, "tint rule must be theme-scoped: " + l);
  const ringLine = CSS.match(/^\.tab\.active\.colored \{.*$/m)![0];
  assert.ok(!ringLine.includes("color-mix"), "the classic selected tab is the gray fill + ring, no tint layer");
});

test("Classic: the label fade is the pre-720 formula — no theme branch, no brightening scale", () => {
  assert.match(RENDER, /const t = Math\.min\(0\.85, \(Lc - Lt\) \/ \(Lc - Lb\)\);/);
  assert.doesNotMatch(RENDER, /chatTabTheme[^\n]*\? 1 :/, "fadedColor no longer branches on the theme");
});

test("Yatharth: his strip verbatim, scoped to the theme class", () => {
  assert.match(CSS, /body\.chat-theme-yatharth #tabbar \{\n  border-bottom: 1px solid color-mix\(in srgb, var\(--active-accent, rgba\(255, 255, 255, 0\.3\)\) 40%, transparent\);\n\}/);
  assert.match(CSS, /body\.chat-theme-yatharth #tabs \{ gap: 0 3px; \}/, "his 3px seam of air between the flat tints");
  assert.match(CSS, /body\.chat-theme-yatharth \.tab\.colored:not\(\.tab-blocked\) \{\n  background: color-mix\(in srgb, var\(--chip-bg\) 9%, transparent\);\n\}/);
  assert.match(CSS, /body\.chat-theme-yatharth \.tab\.colored:not\(\.tab-blocked\):hover \{\n  background: color-mix\(in srgb, var\(--chip-bg\) 15%, transparent\);\n\}/);
  assert.match(CSS, /body\.chat-theme-yatharth \.tab\.active\.colored:not\(\.tab-blocked\) \{\n  background: color-mix\(in srgb, var\(--chip-bg\) 22%, transparent\);\n  border-color: color-mix\(in srgb, var\(--chip-bg\) 55%, transparent\);\n  box-shadow: none;\n\}/);
});

test("the gear offers the picker in the one menu vocabulary, Classic first", () => {
  assert.match(GEAR, /\{ id: 'classic', name: 'Classic',/);
  assert.match(GEAR, /\{ id: 'yatharth', name: 'Yatharth',/);
  assert.match(GEAR, /housePick\(tt, 'tabtheme', tabThemeRowHTML, function \(id\) \{ var s = load\(\); s\.chatTabTheme = id; save\(s\); ttPaint\(\); \}\);/);
});
