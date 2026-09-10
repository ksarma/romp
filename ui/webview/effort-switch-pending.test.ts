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
import { heldMenuMarks, badgeHeldTip, pickHeldLine, pickHeldTitle, reloadingTitle, RUNNING_TAG } from "./pick-held";

const RENDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");
const CSS = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "styles.css"), "utf8");

test("the effort badge shows switching-dots while a reconnect is pending, like the model badge", () => {
  assert.match(RENDER, /effortPending\?: boolean;/);   // status carries it
  assert.match(RENDER, /\(kind === "effort" && !!st\.effortPending\)/);          // effort feeds `pending`
  // the mode and fast reloads carry the same flag since review round 7 (fastPending, modePending), read into `pending`
  // beside the effort's; the executed slice below drives the pulse from them
  assert.match(RENDER, /pickHeld\?: PickHeld \| null; fastPending\?: boolean; modePending\?: boolean;/);
  assert.match(RENDER, /\(kind === "mode" && !!st\.modePending\) \|\| \(kind === "fast" && !!st\.fastPending\)/);
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
  assert.match(RENDER, /import \{ pickHeldLine, pickHeldTitle, badgeHeldTip, heldRowValue, heldMenuMarks, reloadingTitle, RUNNING_TAG, type PickHeld \} from "\.\/pick-held";/);
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
  assert.match(RENDER, /import \{ pickHeldLine, pickHeldTitle, badgeHeldTip, heldRowValue, heldMenuMarks, reloadingTitle, RUNNING_TAG, type PickHeld \} from "\.\/pick-held";/);
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
  // (the flyout falls back to st.auth, the field that carries the billing pick, when the payload names none:
  // review round 6, executed in auth-selector.test.ts)
  assert.match(flyout, /const current = heldAuth \? \(heldAuth\.current \|\| st\.auth\) === c\.value : st\.auth === c\.value;/);
  assert.match(flyout, /const running = !!heldAuth && heldAuth\.running === c\.value;/);
  assert.match(flyout, /el\("div", "ctx-item" \+ \(current \? " current" : ""\) \+ \(running \? " running" : ""\) \+ \(c\.why \? " disabled" : ""\)\)/);   // main's greyed unavailable side rides beside the held marks (billing-one-auth.test.ts)
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

// A minimal element for the executed statusline slice below: the reads and writes syncMetaControls and metaButton
// make (single-class selectors, dataset, the label's text and dots, the held mark's insertBefore); nothing more
class FakeEl {
  tagName: string; className = ""; dataset: Record<string, string> = {}; style: Record<string, string> = {};
  children: FakeEl[] = []; parent: FakeEl | null = null; text = ""; html = ""; attrs: Record<string, string> = {};
  constructor(tag: string, cls?: string) { this.tagName = tag.toUpperCase(); if (cls) this.className = cls; }
  classes(): string[] { return this.className.split(/\s+/).filter(Boolean); }
  get classList() {
    const self = this;
    return {
      add: (...c: string[]) => { self.className = [...new Set([...self.classes(), ...c])].join(" "); },
      remove: (...c: string[]) => { self.className = self.classes().filter((x) => !c.includes(x)).join(" "); },
      toggle: (c: string, on?: boolean) => { const has = self.classes().includes(c); if (on ?? !has) self.classList.add(c); else self.classList.remove(c); },
      contains: (c: string) => self.classes().includes(c),
    };
  }
  appendChild<T extends FakeEl>(n: T): T { n.remove(); n.parent = this; this.children.push(n); return n; }
  insertBefore<T extends FakeEl>(n: T, ref: FakeEl | null): T {
    n.remove(); n.parent = this;
    const i = ref ? this.children.indexOf(ref) : -1;
    if (i >= 0) this.children.splice(i, 0, n); else this.children.push(n);
    return n;
  }
  removeChild(n: FakeEl): void { const i = this.children.indexOf(n); if (i >= 0) { this.children.splice(i, 1); n.parent = null; } }
  remove(): void { this.parent?.removeChild(this); }
  replaceChildren(...ns: FakeEl[]): void { for (const c of [...this.children]) this.removeChild(c); this.text = ""; for (const n of ns) this.appendChild(n); }
  get firstElementChild(): FakeEl | null { return this.children[0] ?? null; }
  get textContent(): string { return this.text + this.children.map((c) => c.textContent).join(""); }
  set textContent(v: string) { this.replaceChildren(); this.text = v; }
  set innerHTML(v: string) { this.html = v; }
  setAttribute(k: string, v: string): void { this.attrs[k] = v; }
  addEventListener(): void {}
  descendants(): FakeEl[] { const out: FakeEl[] = []; for (const c of this.children) out.push(c, ...c.descendants()); return out; }
  querySelectorAll(sel: string): FakeEl[] { return this.descendants().filter((d) => d.classes().includes(sel.slice(1))); }
  querySelector(sel: string): FakeEl | null { return this.querySelectorAll(sel)[0] ?? null; }
}

test("executed: the reloading line's hover title names the change the reload applies, per kind", () => {
  // round 7's gate emits the reloading element for a fast or mode reload too, and its title said "applying the effort
  // change" for all of them (review round 9, correctness-2 and ui-2). The kernel's event carries the pending kinds
  // (picks: effort, mode, fast) and pick-held.ts words the title from them (reloadingTitle, executed per kind in
  // pick-held.test.ts); renderReconnecting is lifted here and run against one event per variant
  const requireCjs = createRequire(__filename);
  const start = RENDER.indexOf("function renderReconnecting(");
  const end = RENDER.indexOf("\n}\n", start) + 3;
  assert.ok(start > 0 && end > start, "the slice anchors moved; re-anchor");
  const js = requireCjs("esbuild").transformSync(RENDER.slice(start, end), { loader: "ts" }).code;
  const mk = (tag: string, cls?: string) => new FakeEl(tag, cls);
  const render = new Function("el", "dot", "metaDots", "pickHeldLine", "pickHeldTitle", "reloadingTitle", js + "\nreturn renderReconnecting;")(
    mk, () => mk("span", "dot"), () => mk("span", "meta-dots"), pickHeldLine, pickHeldTitle, reloadingTitle);
  const line = (ev: object) => render(ev).querySelector(".reconnecting-line") as FakeEl & { title?: string };
  const tail = ": reloading the session (it re-reads the transcript); any message you send lands once it's back";
  const effort = line({ kind: "reconnecting", effort: "max", held: null, picks: ["effort"] });
  assert.equal(effort.title, "applying the effort change" + tail);
  assert.equal(effort.textContent, "Reloading session \u2014 applying max effort\u2026");   // the inherited visible text, pinned above
  const fast = line({ kind: "reconnecting", effort: "", held: null, picks: ["fast"] });
  assert.equal(fast.title, "applying the fast mode change" + tail, "a fast reload names fast mode, not effort");
  assert.equal(fast.textContent, "Reloading session…");
  const mode = line({ kind: "reconnecting", effort: "", held: null, picks: ["mode"] });
  assert.equal(mode.title, "applying the permission mode change" + tail, "a mode reload names the permission mode");
  assert.equal(line({ kind: "reconnecting", effort: "max", held: null, picks: ["effort", "fast"] }).title,
    "applying the effort and fast mode changes" + tail, "two picks riding one reload");
  // an older kernel's event carries no picks: its effort text still names effort; otherwise the change is unnamed
  assert.equal(line({ kind: "reconnecting", effort: "max", held: null }).title, "applying the effort change" + tail);
  assert.equal(line({ kind: "reconnecting", effort: "", held: null }).title, "applying the settings change" + tail);
  // held: the hold's own words, no reload claim
  const hold = { surfaces: ["fast"], subagents: 1, tasks: 0 };
  const held = line({ kind: "reconnecting", effort: "", held: hold, picks: [] });
  assert.equal(held.title, pickHeldTitle(hold));
  assert.equal(held.textContent, pickHeldLine(hold));
  assert.doesNotMatch(held.title!, /reloading the session/);
  assert.match(RENDER, /line\.title = reloadingTitle\(ev\.picks, ev\.effort\);/);
  assert.match(RENDER, /kind: "reconnecting"; effort\?: string; held\?: PickHeld \| null; picks\?: string\[\];/);
  assert.doesNotMatch(RENDER, /applying the effort change \u2014 reloading/, "the round-8 title, one sentence for every kind");
});

// render.ts's statusline slice, metaCurrent through syncMetaControls (the menu-row rule, the local loader's arm and
// its hold-end retirement, the badge builder), lifted and run with the chat's helpers stubbed to their identities
function liftStatusline(activeId: string) {
  const requireCjs = createRequire(__filename);
  const start = RENDER.indexOf("function metaCurrent(kind: MetaKind, st: Status): string {");
  const end = RENDER.indexOf("\n}\n", RENDER.indexOf("function syncMetaControls(")) + 3;
  assert.ok(start > 0 && end > start, "the slice anchors moved; re-anchor");
  const js = requireCjs("esbuild").transformSync(RENDER.slice(start, end), { loader: "ts" }).code;
  const names = ["heldMenuMarks", "badgeHeldTip", "RUNNING_TAG", "el", "setTip", "modeIconSvg", "riskyMode", "toggleMetaMenu",
                 "pickTone", "readableRgb", "prettyMode", "prettyFast", "fastAvailable", "activeId"];
  const body = js + "\nreturn { syncMetaControls, armMetaPending, settleMetaHold, isMetaPending, metaCurrent, metaPending };";
  return new Function(...names, body)(
    heldMenuMarks, badgeHeldTip, RUNNING_TAG, (tag: string, cls?: string) => new FakeEl(tag, cls), () => {}, () => "", () => false,
    () => {}, () => undefined, (c: unknown) => c, (m: string) => m || "default", (f: string) => f || "", () => true, activeId);
}

test("executed: a click on the running row arms no loader, and the hold-cleared frame retires one armed during the hold", () => {
  // pickValue armed the 20 s metaPending loader for every row, the running one included, so cancelling a held pick
  // by clicking the row tagged running showed the effort badge's dots (a mode's dim pulse) until the timer ended
  // though nothing reloaded, and a no-hold click on the checked current row did the same (review round 6, ui-2).
  // The arm is armMetaPending now: no loader for a value equal to the running one; and settleMetaHold, run per
  // badge from syncMetaControls, retires any loader armed during a hold on the frame where the hold ends
  const SID = "11111111-2222-3333-4444-555555555555";
  const api = liftStatusline(SID);
  const meta = new FakeEl("span", "spinner-meta");
  const hold = { surfaces: ["effort"], subagents: 1, tasks: 0, inflight: true, picked: { effort: "max" } };
  const heldSt = { state: "working", sinceEpoch: null, effort: "high", mode: "default", model: "Opus 5", fast: "off", pickHeld: hold };
  const plainSt = { ...heldSt, pickHeld: null };
  const btn = (kind: string) => meta.querySelectorAll(".meta-btn").find((b) => b.dataset.kind === kind)!;
  const label = (kind: string) => btn(kind).querySelector(".meta-label")!;
  const dots = (kind: string) => !!label(kind).querySelector(".meta-dots");
  const pulse = (kind: string) => btn(kind).classList.contains("meta-pending");
  api.syncMetaControls(meta, heldSt);                                   // the held frame
  assert.ok(btn("effort").classList.contains("meta-held"), "the badge wears the held mark");
  assert.equal(label("effort").textContent, "high", "the label is the running value");
  assert.equal(dots("effort"), false);
  // the cancel: the row tagged running (high) clicked while max is held; pickValue's arm with was == value
  api.armMetaPending(SID, "effort", btn("effort"), api.metaCurrent("effort", heldSt), "high");
  assert.equal(api.metaPending.size, 0, "no loader armed for the running value");
  assert.equal(pulse("effort"), false);
  api.syncMetaControls(meta, plainSt);                                  // the withdrawal's frame: the hold gone, high still runs
  assert.equal(dots("effort"), false, "showDots false: nothing reloads");
  assert.equal(pulse("effort"), false);
  assert.equal(btn("effort").classList.contains("meta-held"), false);
  assert.equal(label("effort").textContent, "high");
  // no hold, the checked current row clicked again: no loader either (the kernel reconnects nothing for it)
  api.armMetaPending(SID, "effort", btn("effort"), "high", "high");
  api.syncMetaControls(meta, plainSt);
  assert.equal(api.metaPending.size, 0);
  assert.equal(dots("effort"), false);
  // a real change (no hold) still arms: the dots until the value lands (the event that clears them) or the timer
  api.armMetaPending(SID, "effort", btn("effort"), "high", "low");
  assert.ok(api.metaPending.has(`${SID}:effort`));
  assert.ok(pulse("effort"));
  api.syncMetaControls(meta, plainSt);
  assert.equal(dots("effort"), true, "the local loader covers the beat before the server's effortPending");
  api.syncMetaControls(meta, { ...plainSt, effort: "low" });
  assert.equal(dots("effort"), false);
  assert.equal(api.metaPending.size, 0, "the landing clears it");
  // the mode kind: a change wears the dim pulse, never the dots; the running row and its '' alias arm nothing
  api.armMetaPending(SID, "mode", btn("mode"), "default", "acceptEdits");
  api.syncMetaControls(meta, plainSt);
  assert.ok(pulse("mode"), "the mode badge's meta-pending class");
  assert.equal(dots("mode"), false);
  api.syncMetaControls(meta, { ...plainSt, mode: "acceptEdits" });
  assert.equal(pulse("mode"), false);
  api.armMetaPending(SID, "mode", btn("mode"), "default", "default");
  api.armMetaPending(SID, "mode", btn("mode"), "", "default");
  assert.equal(api.metaPending.size, 0, "the mode row that is the running value arms nothing, '' aliasing default");
  // the model kind is exempt from the guard: its match is a family prefix, so a matching row can still be a change
  api.armMetaPending(SID, "model", btn("model"), "Opus 5", "opus");
  assert.ok(api.metaPending.has(`${SID}:model`), "the Latest row keeps its local dots");
  api.metaPending.clear();
  btn("model").classList.remove("meta-pending");
  // the hold-cleared frame: a re-pick during the hold armed a loader the hold hid; the frame where the hold ends
  // retires it (the event), where it ran to the 20 s timer before
  api.syncMetaControls(meta, heldSt);
  api.armMetaPending(SID, "effort", btn("effort"), api.metaCurrent("effort", heldSt), "low");
  assert.ok(api.metaPending.has(`${SID}:effort`));
  api.syncMetaControls(meta, heldSt);                                   // still held: the loader stays hidden
  assert.equal(dots("effort"), false);
  assert.equal(pulse("effort"), false);
  api.syncMetaControls(meta, plainSt);                                  // the hold ends with high still running
  assert.equal(api.metaPending.has(`${SID}:effort`), false, "retired by the hold's end, not by the timer");
  assert.equal(dots("effort"), false);
  assert.equal(pulse("effort"), false);
  assert.equal(api.isMetaPending("effort", plainSt), false);
  // the server's own signal still drives the dots for an effort reload after the hold
  api.syncMetaControls(meta, { ...plainSt, effortPending: true });
  assert.equal(dots("effort"), true);
  // ...and, since review round 7, the mode and fast reloads have a server signal of their own (modePending,
  // fastPending): a held mode or fast pick that ARMED showed the picked value flat, no pulse, until the landing,
  // because the hold's marker ends at the arm and only effort had a flag. The flag drives the dim pulse (never the
  // dots, which are the model's and effort's), with no local click needed, and clears when the flag drops
  api.metaPending.clear();
  api.syncMetaControls(meta, { ...plainSt, mode: "bypassPermissions", modePending: true });
  assert.ok(pulse("mode"), "the mode badge pulses on the server's flag alone");
  assert.equal(dots("mode"), false, "never the dots");
  assert.equal(label("mode").textContent, "bypassPermissions", "the label is what the kernel reports");
  assert.equal(pulse("effort"), false, "the effort badge does not read the mode's flag");
  api.syncMetaControls(meta, { ...plainSt, mode: "bypassPermissions" });
  assert.equal(pulse("mode"), false, "the landing drops the flag and the pulse with it");
  api.syncMetaControls(meta, { ...plainSt, fast: "on", fastPending: true });
  assert.ok(pulse("fast"), "the fast badge pulses on the server's flag alone");
  assert.equal(dots("fast"), false);
  api.syncMetaControls(meta, { ...plainSt, fast: "on" });
  assert.equal(pulse("fast"), false);
  // a hold still outranks the flag: while held, a kind shows its mark and no pulse whatever the flag says
  api.syncMetaControls(meta, { ...heldSt, pickHeld: { ...hold, surfaces: ["mode"], picked: { mode: "bypassPermissions" } }, modePending: true });
  assert.equal(pulse("mode"), false, "held: no pulse");
  assert.ok(btn("mode").classList.contains("meta-held"));
  api.syncMetaControls(meta, plainSt);
  // the popover's badges are synced under their thread's sid; the hold-end retires that sid's loader, not the chat's
  const pop = new FakeEl("span", "spinner-meta");
  const TSID = "66666666-7777-8888-9999-aaaaaaaaaaaa";
  api.syncMetaControls(pop, heldSt, TSID);
  api.armMetaPending(TSID, "effort", pop.querySelectorAll(".meta-btn").find((b) => b.dataset.kind === "effort")!, "high", "low");
  api.armMetaPending(SID, "effort", btn("effort"), "high", "low");
  api.syncMetaControls(pop, plainSt, TSID);
  assert.equal(api.metaPending.has(`${TSID}:effort`), false);
  assert.equal(api.metaPending.has(`${SID}:effort`), true, "the chat's own loader is not the popover's to retire");
});
