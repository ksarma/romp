// The feed page loads ONLY feed.css — the kernel serves a single <link> (kernel.py) and the VS Code feed
// webview mirrors it (extension.ts) — so styles.css and its :root never reach this surface. A var(--x) used
// here WITHOUT a fallback must therefore be DEFINED here, or every declaration naming it is invalid at
// computed-value time: background falls to transparent, border-color to currentColor, color to inherited.
// That is how .fask-stallbtn — deliberately FILLED working-yellow "so the stall is noticed" — rendered as a
// quiet white outline for two days: it referenced --st-working-bg/fg, which lived only in styles.css (the
// user 2026-07-25). Host-injected vars (--vscode-*) and JS-set per-card channels (--card-r/g/b) are fine
// BECAUSE every use carries a literal fallback; this test holds that line for them too.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const CSS = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "feed.css"), "utf8");

test("every fallback-less var() in feed.css is defined in feed.css", () => {
  // definitions: `--name:` anywhere in the sheet (:root or a selector — both make the var resolvable)
  const defined = new Set([...CSS.matchAll(/(--[a-zA-Z0-9-]+)\s*:/g)].map((m) => m[1]));
  // uses with no fallback: `var(--name)` — a `var(--name, fallback)` never hits this pattern
  const bare = [...CSS.matchAll(/var\(\s*(--[a-zA-Z0-9-]+)\s*\)/g)].map((m) => m[1]);
  const missing = [...new Set(bare.filter((v) => !defined.has(v)))].sort();
  assert.deepEqual(missing, [],
    "used without a fallback but never defined in feed.css (define it in :root or add a fallback): "
    + missing.join(", "));
});

// The same rule, per THEME: a definition inside `body.theme-light { ... }` resolves only while that class is on the
// body, so a token declared THERE alone is undefined on the two dark themes. The check above counted it as defined
// (any `--name:` in the sheet), which is how Slice 4 of plans/markdown-viewer.md shipped the tip and important callout
// rules naming --st-awaitbg-bg and --st-compacting-bg, both light-block-only here: in the dark themes the callout's
// --callout went invalid at computed-value time and the rail, the wash and the title's tint fell away (the review
// round 2). Read with the light block cut out, every bare var() must still find its definition; a light-only token
// is a token missing from :root.
test("every fallback-less var() used outside the light block is defined outside it (a light-only token does not resolve on the dark page)", () => {
  const at = CSS.indexOf("\nbody.theme-light {");
  assert.ok(at >= 0, "the light block is present");
  const end = CSS.indexOf("\n}", at);
  assert.ok(end > at, "the light block closes");
  const dark = (CSS.slice(0, at) + CSS.slice(end + 2)).replace(/\/\*[\s\S]*?\*\//g, "");
  const defined = new Set([...dark.matchAll(/(--[a-zA-Z0-9-]+)\s*:/g)].map((m) => m[1]));
  const bare = [...dark.matchAll(/var\(\s*(--[a-zA-Z0-9-]+)\s*\)/g)].map((m) => m[1]);
  const missing = [...new Set(bare.filter((v) => !defined.has(v)))].sort();
  assert.deepEqual(missing, [],
    "used without a fallback and defined only under body.theme-light (define it in :root too): " + missing.join(", "));
});

test("the callout tints' status tokens resolve on the feed page in the dark themes", () => {
  // the incident pin (Slice 4, review round 2): the two tokens the tip and important callout rules name stand in :root
  const root = CSS.slice(CSS.indexOf(":root {"), CSS.indexOf("\n}", CSS.indexOf(":root {")));
  assert.match(root, /--st-awaitbg-bg:\s*#54B204;/, "--st-awaitbg-bg is defined in feed.css's :root (mirrors styles.css)");
  assert.match(root, /--st-compacting-bg:\s*#14b8a6;/, "--st-compacting-bg is defined in feed.css's :root (mirrors styles.css)");
});

test("the stall chip's working-yellow actually resolves on the feed page", () => {
  // the incident pin, so a refactor that moves the definition back out of feed.css names the victim
  assert.match(CSS, /--st-working-bg:\s*#e0b020/, "--st-working-bg is defined in feed.css (mirrors styles.css)");
  assert.match(CSS, /--st-working-fg:\s*#332600/, "--st-working-fg is defined in feed.css (mirrors styles.css)");
});
