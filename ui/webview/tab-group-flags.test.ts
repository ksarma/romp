// A FOLDED SECTION'S USER-TODO FLAG (the user 2026-09-06): a session tab with an open user todo wears
// a ⚑ ("this session flagged something it needs from you"), and folding its section hid the one tab
// mark that means "needs you" — the default-folded `archived` group most of all. The header now
// derives a flag from the SAME session field the tab reads (userTodos, refreshed by every chat
// delta), with a count when more than one member has one and the sessions' names on hover; the flag
// is a focusable button that opens the section. Executed on the pure rule (tab-state.ts + the strip
// plan) and source-pinned on render.ts / styles.css / docs, the tab-groups.test.ts harness (the
// renderer has no jsdom). Synthetic ids and names only — the notes-api demo world.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { viewTagUnion } from "./session-views";
import { planStrip, parseTabGroups, setSectionCollapsed, isSectionCollapsed, type TabSection } from "./tab-groups";
import { sectionTodoFlag, sectionTodoTitle, sectionPip, sectionPipMembers, sectionPipTitle, SHOW_GROUP_CLICK } from "./tab-state";
import { standInPip } from "./tab-snapshot";

const ui = (...p: string[]) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", ...p), "utf8");
const RENDER = ui("webview", "render.ts");
const CSS = ui("webview", "styles.css");
const GUIDE = fs.readFileSync(path.resolve(process.cwd(), "..", "docs", "guide.md"), "utf8");

const HEAD = RENDER.slice(RENDER.indexOf("function makeGroupHead("), RENDER.indexOf("function sectionHeadOf("));
// the header's stand-in block, where the member-derived marks live: from `if (hidden.length) {` (folded, the unpinned
// members; open, the members hidden inside the section, 2026-09-08) to the drag wiring that follows it
const FOLDED = HEAD.slice(HEAD.indexOf("if (hidden.length) {"), HEAD.indexOf("head.draggable = true;"));
const HANDLER = RENDER.slice(RENDER.indexOf('"open-group": (el) => {'), RENDER.indexOf('"open-group": (el) => {') + 260);

// the demo world: web + api in "infra", tests + old1 in "archived" (folded by default), a loose one
const V = {
  active: "all",
  tags: [
    { id: "g1", name: "infra", color: "#4EC9B0", members: ["web", "api"] },
    { id: "g2", name: "archived", color: "#6b7280", members: ["tests", "old1"] },
  ],
};
type Sess = { name: string; userTodos?: { id: string; text: string }[] };
const todo = (n: number) => Array.from({ length: n }, (_, i) => ({ id: `t${i + 1}`, text: `synthetic need ${i + 1}` }));
const heads = (items: ReturnType<typeof planStrip>["items"]) =>
  items.filter((i): i is { head: TabSection; folded: boolean; active: boolean; hidden: string[]; hides: string[] } => "head" in i);

test("executed: a folded section with ONE member holding an open todo shows the flag, count 1, that session named", () => {
  const sessions = new Map<string, Sess>([["tests", { name: "tests", userTodos: todo(1) }], ["old1", { name: "old1", userTodos: [] }]]);
  const plan = planStrip(["web", "tests", "old1"], viewTagUnion(V), parseTabGroups(null), "web", false);
  const archived = heads(plan.items).find((h) => h.head.name === "archived")!;
  assert.equal(archived.folded, true, "archived starts folded — the fold that hid the tab's glyph");
  const flag = sectionTodoFlag(archived.hidden.map((id) => sessions.get(id)));   // the members the header stands in for
  assert.deepEqual(flag, { count: 1, names: ["tests"] });
  assert.equal(sectionTodoTitle(flag!), "waiting on you — tests flagged something it needs from you; click to open this group");
});

test("executed: two members with todos show the count — SESSIONS, not todos — and the tooltip names both", () => {
  const two = sectionTodoFlag([{ name: "tests", userTodos: todo(3) }, { name: "old1", userTodos: todo(1) }]);
  assert.deepEqual(two, { count: 2, names: ["tests", "old1"] }, "one session with three todos still counts once: the header's other number is a session count too");
  assert.equal(sectionTodoTitle(two!), "waiting on you — 2 sessions flagged something they need from you: tests, old1; click to open this group");
  assert.deepEqual(sectionTodoFlag([{ name: "solo", userTodos: todo(3) }]), { count: 1, names: ["solo"] });
});

test("executed: a resolved todo clears the flag on the next frame — the same field, no cache, and the delta re-renders the strip", () => {
  const before = sectionTodoFlag([{ name: "tests", userTodos: todo(1) }]);
  assert.ok(before);
  // the kernel's resolve lands as a delta carrying userTodos: [] (an empty array is a real value, all cleared)
  assert.equal(sectionTodoFlag([{ name: "tests", userTodos: [] }]), null);
  assert.equal(sectionTodoFlag([{ name: "tests", userTodos: null }]), null);
  assert.equal(sectionTodoFlag([{ name: "tests" }]), null, "a host too old to send the field contributes nothing");
  // render.ts: the header reads the live store at render time (sessions.get), never a copy…
  assert.match(FOLDED, /const flag = sectionTodoFlag\(hidden\.map\(\(id\) => sessions\.get\(id\)\)\);/,
    "…over the members the fold hides (a member pinned to show through carries its own glyph; tab-groups.test pins that)");
  // …and the chat delta that carries the field asks for the strip repaint in the same handler; the frame IS
  // the event. Since the 2026-09-07 fold the ask is upstream's scheduleRenderTabs (one rebuild per animation
  // frame, however many tails a pusher cycle lands): the flag still clears on that frame, with no timer
  const delta = RENDER.slice(RENDER.indexOf('if ("userTodos" in msg) s.userTodos = msg.userTodos;'));
  assert.ok(delta.slice(0, 200).includes("scheduleRenderTabs();"), "a userTodos delta repaints the strip on the handler's own frame (no timer)");
  assert.match(RENDER, /function scheduleRenderTabs\(\): void \{\n\s*if \(tabsRaf != null\) return;\n\s*tabsRaf = requestAnimationFrame\(\(\) => \{ tabsRaf = null; renderTabs\(\); \}\);/, "…and that ask is an animation frame, not a timeout");
  // the tab's own glyph gates on the very same field, so the two can never disagree on a frame
  assert.match(RENDER, /if \(s\.userTodos && s\.userTodos\.length\) \{\s*\n\s*const ut = el\("span", "tab-usertodo"\);/);
});

test("executed: no flag on a section with no todos; a member whose session has not landed counts as none", () => {
  assert.equal(sectionTodoFlag([{ name: "web" }, { name: "api", userTodos: [] }]), null);
  assert.equal(sectionTodoFlag([undefined, null]), null, "a placeholder tab (no session yet) has nothing open");
  assert.equal(sectionTodoFlag([]), null);
  // render.ts adds the button only when the rule yields a flag
  assert.match(FOLDED, /if \(flag\) \{\s*\n\s*const b = document\.createElement\("button"\);/);
});

test("executed: federation — a remote host's session counts for its section the same way, under its prefixed name", () => {
  // the chat pane stores a remote session under its prefixed id with its prefixed name (federation.ts
  // prefixInbound); userTodos ride the session frame untouched, and sections group by the same id
  const unions = viewTagUnion({ active: "all", tags: [],
    remoteTags: [{ id: "TESTHOST-A:r1", host: "TESTHOST-A", name: "remotepool", color: "#7aa2f7", members: ["TESTHOST-A:m1", "TESTHOST-A:m2"] }] });
  const st = setSectionCollapsed(parseTabGroups(null), "remotepool", true);
  const plan = planStrip(["local", "TESTHOST-A:m1", "TESTHOST-A:m2"], unions, st, "local", false);
  const pool = heads(plan.items).find((h) => h.head.name === "remotepool")!;
  assert.equal(pool.folded, true);
  const sessions = new Map<string, Sess>([["TESTHOST-A:m1", { name: "TESTHOST-A:web", userTodos: todo(1) }], ["TESTHOST-A:m2", { name: "TESTHOST-A:api" }]]);
  assert.deepEqual(sectionTodoFlag(pool.hidden.map((id) => sessions.get(id))), { count: 1, names: ["TESTHOST-A:web"] },
    "the name is the one its tab shows — host-prefixed like the label");
});

test("the flag never appears twice for one section: one construction, inside the stand-in block, one append; an open header with nothing hidden carries none", () => {
  assert.equal(RENDER.split('b.className = "tab-group-flag";').length - 1, 1, "exactly one place builds it (renderTabs' focus restore only looks one up)");
  assert.equal(FOLDED.split("sectionTodoFlag(").length - 1, 1, "…inside the header's stand-in block");
  assert.equal(FOLDED.split("head.appendChild(b);").length - 1, 1, "appended once");
  assert.equal(HEAD.indexOf("sectionTodoFlag("), FOLDED.indexOf("sectionTodoFlag(") + HEAD.indexOf("if (hidden.length) {"),
    "no second derivation outside the stand-in block");
  // and one header per section in the plan — the flag rides the header, so one flag per section
  const plan = planStrip(["web", "api", "tests", "old1"], viewTagUnion(V), parseTabGroups(null), "web", false);
  assert.deepEqual(heads(plan.items).map((h) => h.head.name), ["infra", "archived"]);
  // OPEN headers with nothing hidden inside them: every member tab wears its own glyph there, so a header
  // flag would be a second mark over the same need; `hidden` is empty, and the block does not run. (Open with a
  // member hidden inside the section, the block runs over that member: tab-hide.test, the user 2026-09-08.)
  const infra = heads(plan.items).find((h) => h.head.name === "infra")!;
  assert.deepEqual([infra.folded, infra.active, infra.hidden], [false, true, []]);
  assert.match(FOLDED, /^if \(hidden\.length\) \{/, "the marks live in the stand-in block: rendered exactly when the header stands in for a member with no tab");
  assert.ok(!HEAD.includes("if (collapsed) {"), "no folded-only block any more: an open header stands in for its hidden members too");
});

test("expanding via the flag: its own data-act opens the group explicitly (never a toggle), on the stable #tabs delegate, one render path", () => {
  // on a FOLDED header; on an open one (`door`: the header stands in for members hidden inside the section) the same
  // button is the non-folding door to the pane, show-group (tab-hide.test, round 1 of the tabhide review 2026-09-08)
  assert.match(FOLDED, /b\.dataset\.act = door \? "show-group" : "open-group";/);
  assert.equal(sectionTodoTitle({ count: 1, names: ["tests"] }, false), "waiting on you — tests flagged something it needs from you; click to open this group", "the folded header's title, as before");
  assert.equal(sectionTodoTitle({ count: 1, names: ["tests"] }, true), "waiting on you — tests flagged something it needs from you; " + SHOW_GROUP_CLICK, "the open header's: what its click does there");
  assert.match(FOLDED, /b\.dataset\.group = name;/);
  assert.match(HANDLER, /const name = el\.dataset\.group;\s*\n\s*if \(name\) writeTabGroups\(setSectionCollapsed\(tabGroups\(\), name, false\)\);/,
    "an explicit OPEN: a press landing after a sibling pane already opened the group must not fold it back");
  assert.doesNotMatch(HANDLER, /toggleSectionCollapsed|renderTabs\(\)/, "no toggle, and the TABGROUPS_EVENT listener renders — not the handler");
  // executed: the write the handler makes opens a folded section, and is idempotent on an open one
  const folded = setSectionCollapsed(parseTabGroups(null), "infra", true);
  assert.equal(isSectionCollapsed(setSectionCollapsed(folded, "infra", false), "infra"), false);
  assert.equal(isSectionCollapsed(setSectionCollapsed(parseTabGroups(null), "archived", false), "archived"), false, "the default-folded group opens too");
  assert.deepEqual(setSectionCollapsed(setSectionCollapsed(folded, "infra", false), "infra", false), parseTabGroups(null), "open on open: unchanged");
  // the delegate resolves the NEAREST data-act, so a click on the flag is the flag's, not the header's fold
  assert.match(ui("webview", "actions.ts"), /closest\("\[data-act\]"\)/);
});

test("click-safe and keyboard: a real button (focusable; Enter and Space click IT — the header's key handler stands down), the action on the delegate, and a drag guard so a press never reorders", () => {
  assert.match(FOLDED, /const b = document\.createElement\("button"\);\s*\n\s*b\.type = "button";/, "a native button: focusable, Enter/Space → its own click → the delegate");
  // the flag is INSIDE the header, whose keydown handler took the bubbling Enter/Space, canceled the
  // button's native activation and clicked the header: toggle-group ran, not open-group (the same fold
  // opened, by luck of the flag riding folded headers only). The handler returns for a key on the flag.
  const keys = HEAD.slice(HEAD.indexOf('head.addEventListener("keydown"'), HEAD.indexOf("const caret = el("));
  assert.match(keys, /^head\.addEventListener\("keydown", \(e\) => \{\s*\n\s*if \(\(e\.target as HTMLElement \| null\)\?\.closest\("\.tab-group-flag, \.tab-group-door"\)\) return;\s*\n/,
    "the guard comes first, before any preventDefault (and stands down for the open header's count button too: tab-hide.test)");
  assert.match(keys, /if \(e\.key === "Enter" \|\| e\.key === " "\) \{ e\.preventDefault\(\); head\.click\(\); \}\s*\n\s*\}\);/,
    "…and the press is the handler's last word (the stand-in's ←/→ and Enter sit between; tab-groups.test.ts)");
  assert.equal(HEAD.split('addEventListener("keydown"').length - 1, 1, "one key handler on the header, none on the button (native activation is the button's)");
  assert.match(FOLDED, /b\.draggable = true;\s*\n\s*b\.addEventListener\("dragstart", \(e\) => \{ e\.preventDefault\(\); e\.stopPropagation\(\); \}\);/,
    "the flag is the innermost draggable under the pointer, so ITS dragstart fires first: canceled, and never reaching the header's (draggedGroup stays null)");
  assert.doesNotMatch(FOLDED, /b\.addEventListener\("click"/, "no per-node click handler — the node is rebuilt on every push");
  assert.match(FOLDED, /b\.title = sectionTodoTitle\(flag, door\);\s*\n\s*b\.setAttribute\("aria-label", b\.title\);/, "the tooltip names the sessions and says what the click does on this header, and a screen reader hears the same");
  assert.ok(RENDER.indexOf("head.addEventListener(\"dragstart\"") > RENDER.indexOf("head.appendChild(b);"), "the header's own drag wiring stays, after the flag");
});

test("executed: the phone layout's flat strip has no headers, so the tabs' own glyphs are the signal there (the kernel's scrape mirrors them)", () => {
  const plan = planStrip(["web", "tests", "old1"], viewTagUnion(V), parseTabGroups(null), "web", true);
  assert.equal(heads(plan.items).length, 0, "nothing folded on the phone — no header, no header flag");
  assert.deepEqual(plan.items, [{ id: "web" }, { id: "tests" }, { id: "old1" }]);
  assert.match(fs.readFileSync(path.resolve(process.cwd(), "..", "kernel", "kernel.py"), "utf8"), /ut:!!t\.querySelector\('\.tab-usertodo'\)/,
    "the phone list scrapes each tab's glyph (tab-usertodo.test pins the rest)");
});

test("the flag wears the tab glyph's class and the header's count size; the button reads in every theme, rings on keyboard focus, never a .tab-dot", () => {
  assert.match(FOLDED, /const glyph = el\("span", "tab-usertodo"\);[^\n]*\n\s*glyph\.textContent = "⚑";/, "the tab's own mark, same class");
  assert.match(FOLDED, /if \(flag\.count > 1\) \{\s*\n\s*const c = el\("span", "tab-group-count"\);[^\n]*\n\s*c\.textContent = String\(flag\.count\);/,
    "the count only when more than one, at the header's own count size (no new font-size)");
  assert.doesNotMatch(FOLDED, /tab-dot/, "pips encode turn state; the kernel's mobile scrape keys on them");
  assert.match(CSS, /\.tab-group-flag \{[^}]*color: var\(--fg\);[^}]*\}/, "the prose tone: a step above the header's dim label, in every theme");
  assert.match(CSS, /\.tab-group-flag \.tab-usertodo \{ color: inherit; \}/, "the glyph follows: its soft white was chosen for a colored chip, and a header has none");
  assert.match(CSS, /\.tab-group-flag:focus-visible \{ outline: 1px solid var\(--accent\); outline-offset: 1px; \}/, "focus chrome is the accent, keyboard only");
  assert.match(CSS, /\.tab-group-flag:hover \{ background: var\(--accent-wash\); \}/, "the accent wash — the one action hover (button-vocab), themed");
  assert.doesNotMatch(CSS.match(/\.tab-group-flag \{[^}]*\}/)![0], /font-size/, "no new font-size: the glyph and count keep their own");
});

test("docs: the guide's tab-groups paragraph says a folded section keeps the flag and the click opens it", () => {
  assert.match(GUIDE, /A folded header keeps the ⚑ flag\s+of any session in it that has asked you for something; when several have, the flag shows how\s+many, and hovering it names them\. Click the flag to open the section\./);
});

test("executed + pinned: BOTH member-derived marks ride a folded header — the state pip, then the flag — over the hidden members only; open headers carry neither", () => {
  // the notes-api world: archived folds by default; old1 is waiting on you, old2 flagged a todo, old3 is
  // quiet; a pinned member's state and todo show on its own tab, so neither mark counts it
  const unions = viewTagUnion({ ...V, tags: [...V.tags, { id: "g3", name: "archived2", color: "#6b7280", members: [] }] });
  const sessions = new Map<string, Sess & { status?: { state: string; apiAuthErr?: boolean } }>([
    ["tests", { name: "tests", status: { state: "needsInput" } }],
    ["old1", { name: "old1", status: { state: "ready" }, userTodos: todo(1) }],
  ]);
  const st = parseTabGroups(null);
  const arch = heads(planStrip(["web", "tests", "old1"], unions, st, "web", false).items).find((h) => h.head.name === "archived")!;
  assert.deepEqual(arch.hidden, ["tests", "old1"]);
  const kind = sectionPip(arch.hidden.map((id) => sessions.get(id)?.status));
  assert.equal(kind, "blocked", "a hidden member waiting on you → the red pip");
  assert.equal(sectionPipTitle(kind!, sectionPipMembers(kind!, arch.hidden.map((id) => sessions.get(id)))), "a session in this group is blocked or waiting on you: tests");
  // render.ts reads the same rule through standInPip (tab-snapshot.ts), which folds the feed's verdict in (tab-hide.test)
  assert.deepEqual(standInPip(arch.hidden.map((id) => ({ session: sessions.get(id), ledger: null }))), { kind: "blocked", names: ["tests"] });
  assert.deepEqual(sectionTodoFlag(arch.hidden.map((id) => sessions.get(id))), { count: 1, names: ["old1"] }, "…and the flag for the other, side by side");
  // pin tests (the waiting one): its state leaves the pip; the flag is unchanged
  const pinned = setSectionCollapsed(st, "archived", true);
  const pinnedSt = { ...pinned, pinned: [{ sid: "tests", name: "archived", id: "g4" }] };
  const unions2 = viewTagUnion({ ...V, tags: [...V.tags.slice(0, 1), { id: "g4", name: "archived", color: "#6b7280", members: ["tests", "old1"] }] });
  const arch2 = heads(planStrip(["web", "tests", "old1"], unions2, pinnedSt, "web", false).items).find((h) => h.head.name === "archived")!;
  assert.deepEqual(arch2.hidden, ["old1"], "the pinned member is on the strip");
  assert.equal(sectionPip(arch2.hidden.map((id) => sessions.get(id)?.status)), null, "its waiting state shows on its own tab, not the header");
  assert.deepEqual(sectionTodoFlag(arch2.hidden.map((id) => sessions.get(id))), { count: 1, names: ["old1"] });
  // render.ts: both marks are built inside the stand-in block, pip before flag, both over `hidden`; the pip through
  // standInPip (the tab's rule with the feed's verdict folded in: tab-hide.test)
  assert.match(FOLDED, /const stand = standInPip\(hidden\.map\(\(id\) => \(\{ session: sessions\.get\(id\), ledger: ledgers\.get\(id\) \}\)\)\);/);
  assert.ok(FOLDED.indexOf("standInPip(") < FOLDED.indexOf("sectionTodoFlag("), "the pip, then the flag");
  assert.ok(HEAD.indexOf('el("span", "tab-group-count")') < HEAD.indexOf("standInPip("), "both after the count — subordinate to the label");
  assert.equal(HEAD.split("standInPip(").length - 1, 1, "one pip derivation, inside the stand-in block: an open header with nothing hidden carries neither mark");
  assert.match(HEAD, /const said = sectionPipTitle\(stand\.kind, stand\.names\);\s*\n\s*pip\.title = door \? `\$\{said\}; \$\{SHOW_GROUP_CLICK\}` : said;/, "the pip's tooltip names the sessions, like the flag's, and on an open header says what its click does");
  assert.match(CSS, /\.tab-group-pip \{ flex: 0 0 auto; width: 6px; height: 6px;/, "small");
});

test("a push while the flag holds focus puts focus back on the rebuilt FLAG, not its header (source pins; the flag lives inside the header, so closest() names the header from both)", () => {
  // renderTabs runs on every kernel push and rebuilds the strip; the header re-focus captured
  // closest(".tab-group-head"), which a focused flag also satisfies, and restored the HEADER — a
  // keyboard user on the ⚑ was walked back a stop every 0.5–3s, the focus ring and label gone
  const cap = RENDER.slice(RENDER.indexOf("const focusedEl = document.activeElement"), RENDER.indexOf("bar.replaceChildren();"));
  assert.match(cap, /const focusedFlag = !!focusedEl\?\.classList\.contains\("tab-group-flag"\);/, "which of the two held focus is remembered");
  assert.match(RENDER, /\(\(focusedFlag && h\.querySelector<HTMLElement>\("\.tab-group-flag"\)\) \|\| \(focusedDoor && h\.querySelector<HTMLElement>\("\.tab-group-door"\)\) \|\| h\)\.focus\(\);/,
    "the rebuilt header's flag when the flag held it (the open header's count button the same, tab-hide.test); the header when this push resolved the todo and the header has none");
  assert.match(RENDER, /const refocusTab = bar\.contains\(document\.activeElement\);\s*\n\s*bar\.replaceChildren\(\);/, "the tab rule's two-line shape stands (chat-focus-model.test)");
});
