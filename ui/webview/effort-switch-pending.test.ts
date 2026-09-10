// Effort-switch UX (the user 2026-07-06): switching an /effort level reconnects the SDK session to apply it
// (--effort is a connect-time flag). Two cues, mirroring the model badge's switching-dots: (1) the effort
// badge shows the pulsing accent dots while the reconnect is pending (st.effortPending), and (2) an animated
// "Reloading session…" element (kind:"reconnecting") renders in the chat flow until the new client connects.
// render.ts has no jsdom harness → source pins.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { heldMenuMarks } from "./pick-held";

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
  assert.match(RENDER, /import \{ pickHeldLine, pickHeldTitle, badgeHeldTip, heldRowValue, heldMenuMarks, RUNNING_TAG, type PickHeld \} from "\.\/pick-held";/);
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
  // the rows name the PICKED value when the status carries it (pickHeld.picked, review round 5), a mode prettified
  // the way the running one is; pick-held.test.ts executes heldRowValue with and without it
  assert.match(fn, /const pickedOf = \(kind: string\) => \{ const p = \(\(held && held\.picked\) \|\| \{\}\)\[kind\]; return p \? \(kind === "mode" \? prettyMode\(p\) : p\) : undefined; \};/);
  assert.match(fn, /const heldRow = \(kind: string, now: string\) => held && held\.surfaces\.includes\(kind\) \? heldRowValue\(now, kind, held, pickedOf\(kind\)\) : now;/);
  assert.match(fn, /rows\.push\(\["Mode", heldRow\("mode", prettyMode\(s\.status\.mode\)\)\]\);/);
  assert.match(fn, /rows\.push\(\["Effort", heldRow\("effort", s\.status\.effort\)\]\);/);
  assert.match(fn, /rows\.push\(\["Billing", billingRowText\(s\.status\)\]\);/, "the Billing row keeps its own decision, from billing-label.ts");
  assert.doesNotMatch(fn, /badgeHeldTip|pickHeldLine/, "not the badge tip's words (it ends on what the badge shows) nor the chat line's");
});

test("the badge menus and the Billing flyout mark a held pick the same way: the check on the picked value, a running tag on the running one", () => {
  // during a hold the effort and mode menus check-marked the RUNNING value (isCurrentMeta over st.effort / st.mode;
  // toggleMetaMenu never read pickHeld) while the tab menu's Billing flyout check-marked the PICKED side (review
  // round 5, ui-2). One convention now, pick-held.ts's heldMenuMarks (executed in pick-held.test.ts): the check on the
  // pick, the running value tagged. render.ts's rows are pinned here and metaRowMarks is executed below
  assert.match(RENDER, /import \{ pickHeldLine, pickHeldTitle, badgeHeldTip, heldRowValue, heldMenuMarks, RUNNING_TAG, type PickHeld \} from "\.\/pick-held";/);
  assert.match(RENDER, /function matchesMeta\(kind: MetaKind, current: string, value: string\): boolean \{/);
  assert.match(RENDER, /function isCurrentMeta\(kind: MetaKind, st: Status, value: string\): boolean \{\n\s+if \(kind === "model"\) return \(st\.model \|\| ""\)\.toLowerCase\(\)\.startsWith\(value\);\n\s+return matchesMeta\(kind, metaCurrent\(kind, st\), value\);\n\}/);
  assert.match(RENDER, /function metaRowMarks\(kind: MetaKind, st: Status, value: string\): \{ current: boolean; running: boolean \} \{\n\s+const held = heldMenuMarks\(kind, st\.pickHeld, metaCurrent\(kind, st\)\);/);
  // the menu rows take their classes from it, and the running row wears the tag in each of the three row shapes
  const menu = RENDER.slice(RENDER.indexOf("function toggleMetaMenu("), RENDER.indexOf("\nfunction ", RENDER.indexOf("function toggleMetaMenu(") + 1));
  assert.match(menu, /const marks = metaRowMarks\(kind, s\.status, c\.value\);\n\s+const item = el\("div", "meta-item" \+ \(marks\.current \? " current" : ""\) \+ \(marks\.running \? " running" : ""\)\);/);
  assert.equal((menu.match(/if \(marks\.running\) (?:head|item)\.appendChild\(runningTag\(\)\);/g) || []).length, 3, "the sub-lined, the icon and the plain row shapes");
  assert.doesNotMatch(menu, /el\("div", "meta-item" \+ \(isCurrentMeta\(kind, s\.status, c\.value\)/, "the rows no longer check the running value alone");
  // the Billing flyout, the same rule: the check on the pick and the tag on the side the CLI reports while held
  const flyout = RENDER.slice(RENDER.indexOf('const sub = el("div", "ctx-menu ctx-sub");'), RENDER.indexOf("menu.appendChild(sub);"));
  assert.match(flyout, /const heldAuth = heldMenuMarks\("auth", st\.pickHeld, st\.authLive \|\| ""\);/);
  assert.match(flyout, /const current = heldAuth \? heldAuth\.current === c\.value : st\.auth === c\.value;/);
  assert.match(flyout, /const running = !!heldAuth && heldAuth\.running === c\.value;/);
  assert.match(flyout, /el\("div", "ctx-item" \+ \(current \? " current" : ""\) \+ \(running \? " running" : ""\)\)/);
  assert.match(flyout, /if \(running\) opt\.appendChild\(runningTag\(\)\);/);
  // the tag is the menu sub-line vocabulary, spaced from the label; no size of its own (ui/CLAUDE.md)
  assert.match(RENDER, /function runningTag\(\): HTMLElement \{\n\s+const tag = el\("span", "meta-item-sub running-tag"\);\n\s+tag\.textContent = " " \+ RUNNING_TAG;/);
  assert.match(CSS, /\.running-tag \{ margin-left: 6px; \}/);
  assert.doesNotMatch((CSS.match(/\.running-tag \{([^}]*)\}/) || ["", ""])[1], /font-size|opacity/);
});

test("executed: metaRowMarks checks the picked row and tags the running row while held, and the current row otherwise", () => {
  // the row-mark rule lifted from render.ts (metaCurrent through metaRowMarks) and run against statuses, with
  // heldMenuMarks supplied from pick-held.ts, so the classes the menu draws are executed, not only pinned
  const requireCjs = createRequire(__filename);
  const start = RENDER.indexOf("function metaCurrent(kind: MetaKind, st: Status): string {");
  const end = RENDER.indexOf("\n}\n", RENDER.indexOf("function metaRowMarks(")) + 3;
  assert.ok(start > 0 && end > start, "the slice anchors moved; re-anchor");
  const js = requireCjs("esbuild").transformSync(RENDER.slice(start, end), { loader: "ts" }).code;
  const api = new Function("heldMenuMarks", js + "\nreturn { metaRowMarks, isCurrentMeta, matchesMeta };")(heldMenuMarks);
  const held = { surfaces: ["effort", "mode"], subagents: 1, tasks: 0, picked: { effort: "max", mode: "bypassPermissions" } };
  const st = { effort: "high", mode: "default", model: "Opus 5", fast: "off", pickHeld: held };
  assert.deepEqual(api.metaRowMarks("effort", st, "max"), { current: true, running: false }, "the pick is checked");
  assert.deepEqual(api.metaRowMarks("effort", st, "high"), { current: false, running: true }, "the running value is tagged");
  assert.deepEqual(api.metaRowMarks("effort", st, "low"), { current: false, running: false });
  assert.deepEqual(api.metaRowMarks("mode", st, "bypassPermissions"), { current: true, running: false });
  assert.deepEqual(api.metaRowMarks("mode", st, "default"), { current: false, running: true }, "the default alias tags the running row");
  assert.deepEqual(api.metaRowMarks("mode", { ...st, mode: "" }, "default"), { current: false, running: true }, "'' aliases default too");
  assert.deepEqual(api.metaRowMarks("fast", st, "off"), { current: true, running: false }, "a kind not held: the current rule");
  assert.deepEqual(api.metaRowMarks("model", st, "opus"), { current: true, running: false });
  // not held at all: the current rule for every kind, no running tag
  const plain = { ...st, pickHeld: null };
  assert.deepEqual(api.metaRowMarks("effort", plain, "high"), { current: true, running: false });
  assert.deepEqual(api.metaRowMarks("effort", plain, "max"), { current: false, running: false });
  // an older kernel's payload (no picked value): nothing checked, the running row tagged
  const older = { ...st, pickHeld: { surfaces: ["effort"], subagents: 1, tasks: 0 } };
  assert.deepEqual(api.metaRowMarks("effort", older, "high"), { current: false, running: true });
  assert.deepEqual(api.metaRowMarks("effort", older, "max"), { current: false, running: false });
  // the running value picked again is no hold, so it is simply current (the kernel reconnects nothing for it)
  assert.equal(api.isCurrentMeta("effort", plain, "high"), true);
  assert.equal(api.matchesMeta("mode", "normal", "default"), true);
});
