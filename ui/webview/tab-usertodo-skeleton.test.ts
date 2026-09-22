// THE FLAG ON A TAB WHOSE PAYLOAD THIS PAGE HAS NOT BEEN SERVED (the user 2026-09-22, whose flagged sessions wore no
// flag until their tab was clicked). A session's open user todos ride its session payload (build_session's userTodos
// rows, re-sent on every chatTail), and the tab's glyph (tab-usertodo.test.ts), the folded header's flag
// (tab-group-flags.test.ts) and the section snapshot's count (tab-snapshot.test.ts) read that payload. Two upstream
// mechanisms withhold it for a tab nobody has opened: the skeleton diet (a redial, a later chat column, the main pane's
// first dial after a reload) and the cold-tab gate. So the COUNT of a session's open todos now rides the tabOrder roster
// beside its name, colour and emoji (the kernel's _tab_meta; tab-meta.ts TabSessionMeta), the strip meta every chat
// client receives for every listed tab, and the skeleton and placeholder builders paint the flag from it. A todo's text
// stays session content and loads with the tab. Source pins in tab-usertodo.test.ts's style (the renderer has no jsdom
// harness); each names the executed test of the rule it guards. tab-strip-skip.test.ts's census is the RULE these
// instances follow: every glyph the loaded row paints from the session has a strip-meta counterpart in the two rows.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const RENDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");
const SNAP = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "tab-snapshot.ts"), "utf8");
const META = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "tab-meta.ts"), "utf8");

const fn = (src: string, name: string): string => {
  const i = src.indexOf(`function ${name}(`);
  assert.ok(i >= 0, `${name} not found`);
  return src.slice(i, src.indexOf("\n}\n", i) + 3);
};
const skeleton = fn(RENDER, "makeSkeletonTab"), placeholder = fn(RENDER, "makePlaceholderTab");
const renderTabs = RENDER.slice(RENDER.indexOf("function renderTabs() {"), RENDER.indexOf("function stripAftermath("));
const sig = renderTabs.slice(renderTabs.indexOf("const stripSig = JSON.stringify(["), renderTabs.indexOf("const mslotEl = "));
const sigRow = (marker: string): string => {
  const a = sig.indexOf(marker);
  assert.ok(a >= 0, "the signature row " + marker + " is in renderTabs");
  return sig.slice(a, sig.indexOf("];", a));
};
/** The builder paints the flag: the tab's own mark and class (tab-usertodo.test.ts pins the style and the phone scrape),
 *  from the strip meta's count, and never a number on the strip (plans/user-todos.md governs the glyph, not the wire). */
function paintsFlagFromMeta(builder: string, name: string): void {
  assert.match(builder, /const meta = tabMeta\.get\(id\);/, name + " reads the strip meta");
  assert.match(builder, /if \(meta\?\.userTodos\) \{\s*\n\s*const ut = el\("span", "tab-usertodo"\);\s*\n\s*ut\.textContent = "⚑";/,
    name + " paints the tab's own mark from the roster count: the glyph a loaded tab wears (tab-usertodo.test.ts), the class the phone scrape and the header's flag share");
  assert.match(builder, /ut\.title = /, name + ": the flag explains itself on hover, as on a loaded tab");
  const block = builder.slice(builder.indexOf('el("span", "tab-usertodo")'), builder.indexOf('el("span", "tab-usertodo")') + 300);
  assert.doesNotMatch(block, /userTodos\s*\+|`\$\{[^}]*userTodos|String\(meta/, name + ": no count reaches the strip (the glyph is non-numeric on every tab kind)");
  assert.doesNotMatch(block, /tab-dot/, name + ": the flag is not a pip");
  const label = builder.indexOf("tab.appendChild(label);"), glyph = builder.indexOf('el("span", "tab-usertodo")');
  assert.ok(label >= 0 && label < glyph, name + ": the flag follows the label, as on a loaded tab");
}

test("the roster row's count lands on the strip meta: applyTabOrder parses it INLINE and the tabMeta entry type carries it", () => {
  const apply = fn(RENDER, "applyTabOrder");
  // inline, not a helper: chat-split-exec.test.ts lifts applyTabOrder by source into a stub world where a new import would
  // be undefined; a number or nothing: an older kernel's row has no key, and the builders paint nothing for it
  assert.match(apply, /tabMeta\.set\(t\.id, \{[^}]*userTodos: typeof t\.userTodos === "number" \? t\.userTodos : undefined/,
    "the parse is the set literal's own expression (executed over the lifted function: chat-split-exec.test.ts)");
  assert.match(RENDER, /^const tabMeta = new Map<string, \{ name: string; color: Color \| null; emoji\?: string; userTodos\?: number \}>\(\);/m,
    "the entry type names the count (tab-close-optimistic.test.ts holds this declaration within 900 characters of closingTabs)");
  assert.match(META, /export interface TabSessionMeta \{ name: string; color: TabColor \| null; emoji\?: string; userTodos\?: number \| ReadonlyArray<unknown> \| null \}/,
    "tab-meta.ts's shape of a strip member carries it: a count on a roster row, the rows on a session (applyMetaToSession takes a Session through this type)");
  assert.doesNotMatch(fn(META, "applyMetaToSession"), /userTodos/, "the push syncs name, colour and emoji onto a loaded session; its todo rows are the session payload's own and stay so");
});

test("makeSkeletonTab paints the flag from the strip meta's count, never from the stale entry's rows", () => {
  paintsFlagFromMeta(skeleton, "makeSkeletonTab");
  assert.doesNotMatch(skeleton, /stale\??\.userTodos/,
    "the pre-outage session entry a redial keeps underneath is what liveSession exists to hide; its rows are stale, the roster count is the kernel's current");
  const glyph = skeleton.indexOf('el("span", "tab-usertodo")'), widgets = skeleton.indexOf("appendTabAfterWidgets(tab");
  assert.ok(glyph < widgets, "the flag before the after-the-name widgets, as on a loaded tab (skeleton-tabs-wiring.test.ts orders label, widgets, close)");
});

test("makePlaceholderTab paints it too: a tab whose session is still being built has the roster's count already", () => {
  paintsFlagFromMeta(placeholder, "makePlaceholderTab");
});

test("the strip signature's skeleton AND placeholder rows carry the count, so a change repaints; the loaded row still reads the session's rows", () => {
  // without the term a filed or resolved todo on a skeleton computes an EQUAL signature and the repaint is skipped
  // (tab-strip-skip.test.ts: the signature is the input list; its census is the rule, these two are the instances)
  assert.ok(sigRow('return ["k",').includes("m?.userTodos"), "the skeleton row reads the meta's count");
  assert.ok(sigRow('return ["p",').includes("m?.userTodos"), "the placeholder row reads the meta's count");
  assert.ok(sig.includes("!!(s.userTodos && s.userTodos.length)"), "the loaded row's input is unchanged (tab-usertodo.test.ts)");
  // the kernel's painter-key census (tests/test_cold_tab_gate.py) reads the skeleton row's kst?. keys: the count is meta, not status
  assert.ok(!sigRow('return ["k",').includes("kst?.userTodos"), "the count rides the roster row, never the status frame");
});

test("the folded header's flag reads the live session, else the strip meta (executed: tab-group-flags.test.ts, a count, 0, mixed rows and counts)", () => {
  assert.match(RENDER, /const flag = sectionTodoFlag\(hidden\.map\(\(id\) => liveSession\(id\) \?\? tabMeta\.get\(id\)\)\);/,
    "a loaded member's rows, a skeleton or placeholder member's roster count: liveSession is undefined for a skeleton (its stale entry never reads as current), and the roster row stands in");
});

test("snapshotRow reads the roster count FIRST and says why (executed: tab-snapshot.test.ts, the meta-only row and the stale entry)", () => {
  const row = fn(SNAP, "snapshotRow");
  assert.match(row, /const todos = typeof meta\?\.userTodos === "number" \? meta\.userTodos : Array\.isArray\(s\?\.userTodos\) \? s!\.userTodos!\.length : 0;/,
    "the roster count when the kernel sent one, else the session's rows (an older kernel), else nothing");
  const why = row.slice(0, row.indexOf("const todos = "));
  assert.match(why, /sessions\.get\(id\)/, "the comment names the seam: render.ts hands the snapshot sessions.get(id) for every member");
  assert.match(why, /liveSession/, "...which on a redial is the stale pre-outage entry for a skeleton member, the very thing liveSession exists to dodge");
  assert.ok(row.indexOf("meta?.userTodos") < row.indexOf("s?.userTodos"), "roster first: a later reader must not simplify it to rows-first");
  assert.match(SNAP, /export interface SnapMetaLike \{ name\?: string; color\?: SnapColor \| null; userTodos\?: number \}/);
});
