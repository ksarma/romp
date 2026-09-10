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
  // the kernel holds a pick while the session's subagents and background tasks run (the reload would
  // kill them) and carries the hold on the event (`held`) and the status (`pickHeld`); the element then
  // says which pick waits and on what, with no loader dots. The words come from pick-held.ts (executed
  // in pick-held.test.ts, per kind and per state); render.ts is pinned to take them from there
  assert.match(RENDER, /import \{ pickHeldLine, pickHeldTitle, badgeHeldTip, heldRowValue, type PickHeld \} from "\.\/pick-held";/);
  assert.match(RENDER, /kind: "reconnecting"; effort\?: string; held\?: PickHeld \| null;/);
  assert.match(RENDER, /effortPending\?: boolean; pickHeld\?: PickHeld \| null;/);
  assert.match(RENDER, /if \(ev\.held\) \{/);
  assert.match(RENDER, /txt\.textContent = pickHeldLine\(ev\.held\);/);
  assert.match(RENDER, /line\.title = pickHeldTitle\(ev\.held\);/);
  assert.doesNotMatch(RENDER, /Applying \$\{ev\.effort\} effort when the background work finishes/,
    "the round-1 copy named the effort for every held kind");
  // the dots and the reloading words live in the else branch: a hold shows neither
  const start = RENDER.indexOf("function renderReconnecting(");
  const fn = RENDER.slice(start, RENDER.indexOf("\nfunction ", start + 1));   // this function alone
  const held = fn.indexOf("if (ev.held) {"), els = fn.indexOf("} else {");
  assert.ok(held > 0 && els > held);
  assert.ok(fn.indexOf("line.appendChild(metaDots());") > els, "no loader dots while held");
  assert.ok(fn.indexOf("Reloading session") > els, "no reload claim while held");
});

test("a held kind's badge shows the running value with a pending mark: no loader dots, no dim pulse", () => {
  // syncMetaControls reads the one held marker (st.pickHeld.surfaces) for every kind it draws: the label
  // stays the value the kernel reports (the running one while held), a small accent mark says a change
  // waits, and the tip names the pick; effortPending's loader dots and the dim .meta-pending pulse are
  // both off for a held kind, since each claimed a change in progress (review round 2, 2026-09-09)
  assert.match(RENDER, /const held = !!st\.pickHeld && st\.pickHeld\.surfaces\.includes\(kind\);/);
  assert.match(RENDER, /const pending = !held && \(\(kind === "model" && !!st\.modelPending\) \|\| \(kind === "effort" && !!st\.effortPending\)/);
  assert.match(RENDER, /b\.classList\.toggle\("meta-held", held\);/);
  assert.match(RENDER, /const m = el\("span", "meta-held-mark"\);/);
  // the glyph is decoration: hidden from assistive tech, so the badge's name reads "high" and not "high•"
  // (review round 3; the browser leg meta-held-mark-browser.test.ts measures it)
  assert.match(RENDER, /m\.textContent = "•";\s*\n\s*m\.setAttribute\("aria-hidden", "true"\);/);
  assert.match(RENDER, /setTip\(b, held && st\.pickHeld \? badgeHeldTip\(kind, st\.pickHeld\) : metaTip\(kind\)\);/);
  assert.match(CSS, /\.meta-held-mark \{[^}]*color: var\(--accent\)/);
  // the mark's dress (review round 3): it inherits .spinner-meta's size (no font-size of its own, which
  // compounded under the 0.92em to 7.9px), and its raise is flex-compatible: align-self plus a small
  // translate, never vertical-align, which is dead on a flex item and drew the dot on the label's centre
  const rule = (CSS.match(/\.meta-held-mark \{([^}]*)\}/) || [])[1] || "";
  assert.ok(rule, "the mark has a rule");
  assert.doesNotMatch(rule, /font-size/, "no size of its own: it inherits the badge's");
  assert.doesNotMatch(rule, /vertical-align/, "dead on a flex item");
  assert.match(rule, /align-self: flex-start/);
  assert.match(rule, /transform: translateY\(-0\.1em\)/);
  assert.match(rule, /line-height: 1/);
  // the same sync serves mode, model, effort and fast badges (the kinds the statusline draws)
  assert.match(RENDER, /type MetaKind = "mode" \| "model" \| "effort" \| "fast";/);
});

test("the tab tooltip's Mode and Effort rows show a held pick the way the Billing row does", () => {
  // showTabTip's Mode and Effort rows read the status value with no pickHeld read, so during a hold they showed
  // the running value flat while the Billing row in the same popover explained its hold; for a tab that is not
  // the active one the tooltip is the only place its mode and effort can be read (review round 4, 2026-09-10).
  // The rows take their held shape from pick-held.ts (heldRowValue, executed in pick-held.test.ts), the same
  // "until" clause the Billing row and sub-line use, so the three rows of one popover agree
  const start = RENDER.indexOf("function showTabTip(");
  const fn = RENDER.slice(start, RENDER.indexOf("\nfunction ", start + 1));
  assert.ok(start > 0 && fn.length > 0);
  assert.match(fn, /const held = s\.status\.pickHeld;/);
  assert.match(fn, /const heldRow = \(kind: string, now: string\) => held && held\.surfaces\.includes\(kind\) \? heldRowValue\(now, kind, held\) : now;/);
  assert.match(fn, /rows\.push\(\["Mode", heldRow\("mode", prettyMode\(s\.status\.mode\)\)\]\);/);
  assert.match(fn, /rows\.push\(\["Effort", heldRow\("effort", s\.status\.effort\)\]\);/);
  assert.match(fn, /rows\.push\(\["Billing", billingRowText\(s\.status\)\]\);/, "the Billing row keeps its own decision, from billing-label.ts");
  assert.doesNotMatch(fn, /badgeHeldTip|pickHeldLine/, "not the badge tip's words (it ends on what the badge shows) nor the chat line's");
});
