// A /model switch shows animated accent-blue dots in the model badge until the new name lands — the
// server drives it (status.modelPending, event-based, cleared the instant the live model reflects the
// pick) so the badge never lingers on a stale or premature name (the user 2026-07-03: switched to opus,
// the badge kept saying fable). Source-level pins (the statusline DOM isn't jsdom-tested here).
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const RENDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");
const CSS = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "styles.css"), "utf8");

test("Status carries the server-driven modelPending flag", () => {
  assert.match(RENDER, /interface Status \{[^}]*modelPending\?: boolean/);
});

test("syncMetaControls renders dots for a pending model, driven by the server flag (+ local click heuristic)", () => {
  // model + effort both drive dots now (effort reconnects to apply); the model clause is still present. The one
  // gate in front of them: a kind whose pick is HELD for the session's live work (st.pickHeld, 2026-09-09) shows
  // the running value with a mark and no dots (effort-switch-pending.test.ts pins that branch). A model pick
  // is never held (it resolves live, no reconnect), so for the model badge the server flag alone decides. The
  // three lines are pinned in order (review round 7): the held read, then settleMetaHold, the hold-cleared frame's
  // retirement of a loader armed during the hold (review round 6; REQUIRED between them, since the settle is part
  // of the mechanism and an optional group would let its removal pass), then the pending expression, which the
  // server's mode and fast flags join (modePending, fastPending: the reload of a held mode or fast pick, round 7)
  const i0 = RENDER.indexOf("const held = !!st.pickHeld && st.pickHeld.surfaces.includes(kind);");
  assert.ok(i0 > 0, "the held read");
  const gate = RENDER.slice(i0, i0 + 800);
  assert.match(gate, /^const held = !!st\.pickHeld && st\.pickHeld\.surfaces\.includes\(kind\);\s*\n\s*settleMetaHold\(forSid \|\| activeId \|\| "", kind, held\);[^\n]*\n\s*const pending = !held && \(\(kind === "model" && !!st\.modelPending\) \|\| \(kind === "effort" && !!st\.effortPending\)\s*\n\s*\|\| \(kind === "mode" && !!st\.modePending\) \|\| \(kind === "fast" && !!st\.fastPending\)[^\n]*\n\s*\|\| isMetaPending\(kind, st\)\);/);
  assert.match(RENDER, /const showDots = pending && \(kind === "model" \|\| kind === "effort"\);/);   // billing moved to the tab menu (2026-08-09)
  assert.match(RENDER, /if \(!label\.querySelector\("\.meta-dots"\)\) label\.replaceChildren\(metaDots\(\)\);/);
  // the local loader's arm and retirement, the mechanism the settle line above belongs to (review round 6): a click
  // on the row that IS the running value arms none (the model kind excepted: its match is a family prefix), a real
  // change arms it, and the frame where a hold ends retires one armed during the hold (the event, not the timer)
  assert.match(RENDER, /function armMetaPending\(opSid: string, kind: MetaKind, btn: HTMLElement, was: string, value: string\): void \{\n\s+if \(kind !== "model" && matchesMeta\(kind, was, value\)\) return;\n\s+metaPending\.set\(`\$\{opSid\}:\$\{kind\}`, \{ was, until: Date\.now\(\) \+ 20_000 \}\);/);
  assert.match(RENDER, /function settleMetaHold\(sid: string, kind: MetaKind, held: boolean\): void \{\n\s+const key = `\$\{sid\}:\$\{kind\}`;\n\s+if \(held\) \{ metaHeldLast\.add\(key\); return; \}\n\s+if \(metaHeldLast\.delete\(key\)\) metaPending\.delete\(key\);\n\}/);
});

test("metaDots builds three <i> dots", () => {
  assert.match(RENDER, /function metaDots\(\): HTMLElement \{/);
  const body = RENDER.slice(RENDER.indexOf("function metaDots"));
  assert.equal((body.slice(0, body.indexOf("return d;")).match(/el\("i"\)/g) || []).length, 3,
               "exactly three dots");
});

test("the dots are accent-blue, animated, and override the .meta-pending dim", () => {
  assert.match(CSS, /\.meta-dots i \{[^}]*background: var\(--accent\)/, "romp accent blue, not a hardcoded hex");
  assert.match(CSS, /@keyframes meta-dots/);
  assert.match(CSS, /\.meta-pending \.meta-label:has\(\.meta-dots\) \{ opacity: 1; animation: none; \}/,
               "the dots read full-strength, not under the pending dim");
  // staggered so they pulse in sequence
  assert.match(CSS, /\.meta-dots i:nth-child\(2\) \{ animation-delay: 0\.16s; \}/);
  assert.match(CSS, /\.meta-dots i:nth-child\(3\) \{ animation-delay: 0\.32s; \}/);
});
