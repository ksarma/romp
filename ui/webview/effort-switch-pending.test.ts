// Effort-switch UX (the user 2026-07-06): switching an /effort level reconnects the SDK session to apply it
// (--effort is a connect-time flag). Two cues, mirroring the model badge's switching-dots: (1) the effort
// badge shows the pulsing accent dots while the reconnect is pending (st.effortPending), and (2) an animated
// "Reloading session…" element (kind:"reconnecting") renders in the chat flow until the new client connects.
// render.ts has no jsdom harness → source pins.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const RENDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");
const CSS = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "styles.css"), "utf8");

test("the effort badge shows switching-dots while a reconnect is pending, like the model badge", () => {
  assert.match(RENDER, /effortPending\?: boolean;/);   // status carries it
  assert.match(RENDER, /\(kind === "effort" && !!st\.effortPending\)/);          // effort feeds `pending`
  assert.match(RENDER, /const showDots = pending && \(kind === "model" \|\| kind === "effort"\);/);   // dots for both reconnect-style badges (billing moved to the tab menu, 2026-08-09)
});

test("a live reconnect has its own ChatEvent kind, dispatched to renderReconnecting", () => {
  assert.match(RENDER, /kind: "reconnecting"; effort\?: string;/);
  assert.match(RENDER, /ev\.kind === "reconnecting"\) return renderReconnecting\(ev\)/);
  // checked BEFORE the compact-boundary case (a live signal, not a boundary)
  const recon = RENDER.indexOf('ev.kind === "reconnecting") return renderReconnecting(ev)');
  const compact = RENDER.indexOf('ev.kind === "compact") return renderCompact(ev)');
  assert.ok(recon > 0 && compact > 0 && recon < compact);
});

test("renderReconnecting draws the accent loader dots + a 'Reloading session' line naming the effort", () => {
  assert.match(RENDER, /function renderReconnecting\(ev: Extract<ChatEvent, \{ kind: "reconnecting" \}>\)/);
  assert.match(RENDER, /el\("div", "turn turn-reconnecting"\)/);
  assert.match(RENDER, /line\.appendChild\(metaDots\(\)\);/);   // the SAME pulsing accent dots as the badge
  assert.match(RENDER, /Reloading session — applying \$\{ev\.effort\} effort…/);
  assert.match(RENDER, /"Reloading session…"/);                // effort-less fallback
  assert.match(CSS, /\.turn-reconnecting \.dot \{[^}]*background: var\(--accent\)/);   // accent (loading), not a status color
});

test("a pick HELD for live work renders a waiting line, not the reloading animation", () => {
  // the kernel holds an effort pick while the session's subagents and background tasks run (the reload
  // would kill them) and carries the hold on the event (`held`) and the status (`pickHeld`); the
  // element then says what it waits for, with no loader dots, and its title names the counts
  assert.match(RENDER, /kind: "reconnecting"; effort\?: string; held\?: PickHeld \| null;/);
  assert.match(RENDER, /effortPending\?: boolean; pickHeld\?: PickHeld \| null;/);
  assert.match(RENDER, /interface PickHeld \{ surfaces: string\[\]; subagents: number; tasks: number \}/);
  assert.match(RENDER, /if \(ev\.held\) \{/);
  assert.match(RENDER, /Applying \$\{ev\.effort\} effort when the background work finishes/);
  assert.match(RENDER, /"Applying the change when the background work finishes"/);
  assert.match(RENDER, /line\.title = pickHeldTitle\(ev\.held\);/);
  // the dots and the reloading words live in the else branch: a hold shows neither
  const fn = RENDER.slice(RENDER.indexOf("function renderReconnecting("), RENDER.indexOf("interface PickHeld"));
  const held = fn.indexOf("if (ev.held) {"), els = fn.indexOf("} else {");
  assert.ok(held > 0 && els > held);
  assert.ok(fn.indexOf("line.appendChild(metaDots());") > els, "no loader dots while held");
  assert.ok(fn.indexOf("Reloading session") > els, "no reload claim while held");
  assert.match(RENDER, /waiting on \$\{n\} subagent\$\{n === 1 \? "" : "s"\} and \$\{m\} background task/);
});
