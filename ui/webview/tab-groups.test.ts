// TAB GROUPS ARE TAGS (the user 2026-09-04): the chat tab strip sections by HOME tag — the first
// holder in tagOrder, the rule revealIn states — with the untagged trailing, per-browser on/off and
// per-section fold state under romp:tabgroups, and the section headers draggable to reorder
// tagOrder (the kernel-persisted union order the timeline's pill drag writes too). Executed tests on
// the pure module + source pins on render.ts / tag-menu.ts / styles.css (the tab-order.ts pattern;
// no jsdom for render.ts). Synthetic ids only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { viewTagUnion } from "./session-views";
import { sectionTabs, anySectioned, homeTag, parseTabGroups, readTabGroups, writeTabGroups, isSectionCollapsed,
         toggleSectionCollapsed, setSectionCollapsed, planStrip, reorderTagOrder, applyTagOrder, TABGROUPS_KEY,
         DEFAULT_COLLAPSED, sectionKey, sectionRef, isPinned, setPinned, togglePinned, prunePinned, headWords,
         type TabSection, type SectionRef } from "./tab-groups";
import { sectionTodoFlag } from "./tab-state";

const ui = (...p: string[]) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", ...p), "utf8");
const RENDER = ui("webview", "render.ts");
const CSS = ui("webview", "styles.css");
const MENU = ui("webview", "tag-menu.ts");
const VIEWS = ui("webview", "session-views.ts");
const KERNEL = fs.readFileSync(path.resolve(process.cwd(), "..", "kernel", "kernel.py"), "utf8");
const GUIDE = fs.readFileSync(path.resolve(process.cwd(), "..", "docs", "guide.md"), "utf8");

// the notes-api demo world: web + api in "infra", tests in "qa", a loose one; api ALSO in qa
const V = {
  active: "all",
  tags: [
    { id: "g1", name: "qa", color: "#DD42FF", members: ["tests", "api"] },
    { id: "g2", name: "infra", color: "#4EC9B0", members: ["web", "api"] },
    { id: "g3", name: "empty", color: "#e0af68", members: [] },
  ],
  remoteTags: [{ id: "TESTHOST-A:r1", host: "TESTHOST-A", name: "remotepool", color: "#7aa2f7", members: ["TESTHOST-A:m1"] }],
};

test("executed: the home-tag rule — one section per tab, its FIRST holder in tagOrder; sections in union order; the untagged trail", () => {
  const unions = viewTagUnion(V);
  const secs = sectionTabs(["web", "api", "loose", "tests"], unions);
  assert.deepEqual(secs.map((s) => [s.name, s.ids]),
    [["qa", ["api", "tests"]], ["infra", ["web"]], [null, ["loose"]]],
    "api holds qa AND infra — qa is first in the union order, so qa is its home; tabs keep strip order inside; the loose one trails");
  assert.equal(secs[0].color, "#DD42FF", "the section wears its tag's colour");
  assert.equal(homeTag("api", unions)!.name, "qa");
  // the SAME rule revealIn keys on (session-views.ts) — the two must never disagree
  assert.match(VIEWS, /const holder = unions\.find\(\(u\) => u\.members\.includes\(id\)\);/);
  // reorder the tags and api moves home with them — this is why reordering is first-class
  const flipped = viewTagUnion({ ...V, tagOrder: ["infra", "qa"] });
  assert.deepEqual(sectionTabs(["web", "api", "tests"], flipped).map((s) => [s.name, s.ids]),
    [["infra", ["web", "api"]], ["qa", ["tests"]]]);
  // a tag with no visible member yields no section; a remote-homed tag sections by NAME like any other
  assert.ok(!secs.some((s) => s.name === "empty"));
  assert.deepEqual(sectionTabs(["TESTHOST-A:m1"], unions).map((s) => s.name), ["remotepool"]);
});

test("executed: sectioning is on by default exactly when some tag holds a visible tab", () => {
  const unions = viewTagUnion(V);
  assert.equal(anySectioned(["web"], unions), true);
  assert.equal(anySectioned(["loose", "other"], unions), false, "an untagged world keeps the flat strip");
  assert.equal(anySectioned([], unions), false);
  assert.deepEqual(sectionTabs(["loose"], unions), [{ name: null, key: "", color: "", ids: ["loose"] }]);
});

test("executed: per-browser state — on by default, archived starts folded, toggles remember, junk reads as the default", () => {
  const d = parseTabGroups(null);
  assert.deepEqual(d, { on: true, collapsed: [], expanded: [], pinned: [] });
  assert.equal(isSectionCollapsed(d, "infra"), false);
  assert.equal(isSectionCollapsed(d, "archived"), true, "the archived tag exists to put sessions away — folded until opened");
  assert.ok(DEFAULT_COLLAPSED.has("archived"));
  const folded = toggleSectionCollapsed(d, "infra");
  assert.equal(isSectionCollapsed(folded, "infra"), true);
  assert.equal(isSectionCollapsed(toggleSectionCollapsed(folded, "infra"), "infra"), false, "toggling back opens it");
  const opened = toggleSectionCollapsed(d, "archived");
  assert.equal(isSectionCollapsed(opened, "archived"), false, "opening a default-folded section is remembered…");
  assert.deepEqual(opened.expanded, ["archived"]);
  assert.equal(isSectionCollapsed(toggleSectionCollapsed(opened, "archived"), "archived"), true, "…and folding it again drops the memory");
  assert.deepEqual(parseTabGroups('{"on":false,"collapsed":["qa",3],"expanded":"x"}'), { on: false, collapsed: ["qa"], expanded: [], pinned: [] },
    "wrong-typed entries drop; on=false is the one way off");
  assert.deepEqual(parseTabGroups("not json"), d, "a corrupt entry costs the preference, never the dashboard");
  assert.deepEqual(parseTabGroups("[1,2]"), d);
});

test("executed: write → read round-trips through localStorage under romp:tabgroups (the view-order two-path idiom)", () => {
  const store = new Map<string, string>();
  const g: any = globalThis;
  const savedLS = g.localStorage;
  g.localStorage = { getItem: (k: string) => store.get(k) ?? null, setItem: (k: string, v: string) => { store.set(k, v); } };
  try {
    writeTabGroups({ on: false, collapsed: ["qa"], expanded: ["archived"], pinned: [{ tag: "g2", sid: "web" }] });
    assert.ok(store.has(TABGROUPS_KEY), "persisted under the one key");
    assert.deepEqual(readTabGroups(), { on: false, collapsed: ["qa"], expanded: ["archived"], pinned: [{ tag: "g2", sid: "web" }] }, "the pins ride the same blob");
  } finally {
    g.localStorage = savedLS;
  }
  assert.equal(TABGROUPS_KEY, "romp:tabgroups");
});

test("executed: reorderTagOrder — the dragged group takes the target's slot, in the FULL union order", () => {
  const names = ["qa", "infra", "empty", "remotepool"];
  assert.deepEqual(reorderTagOrder(names, "remotepool", "infra"), ["qa", "remotepool", "infra", "empty"], "dragged up: lands before the target");
  assert.deepEqual(reorderTagOrder(names, "qa", "empty"), ["infra", "empty", "qa", "remotepool"], "dragged down: lands after the target");
  assert.deepEqual(reorderTagOrder(names, "qa", "qa"), names, "onto itself: unchanged");
  assert.deepEqual(reorderTagOrder(names, "nope", "qa"), names, "an unknown name: unchanged");
  assert.deepEqual(reorderTagOrder(["a", "a", "b"], "b", "a"), ["b", "a"], "duplicates collapse");
});

test("executed: applyTagOrder writes tagOrder AND re-sorts the local tags array — the timeline's pill-drag contract, so both surfaces agree", () => {
  const nv = applyTagOrder(V, ["infra", "remotepool", "qa", "empty"]);
  assert.deepEqual(nv.tagOrder, ["infra", "remotepool", "qa", "empty"], "the whole union order, remote-homed names included");
  assert.deepEqual(nv.tags!.map((t) => t.name), ["infra", "qa", "empty"], "locals re-sort to match (remote names simply aren't in it)");
  assert.deepEqual(viewTagUnion({ ...nv, remoteTags: V.remoteTags }).map((u) => u.name), ["infra", "remotepool", "qa", "empty"],
    "a rebuild from the posted blob renders the dragged order");
  assert.deepEqual(V.tags.map((t) => t.name), ["qa", "infra", "empty"], "the input blob is untouched");
  assert.deepEqual(applyTagOrder(null, ["a"]), { tagOrder: ["a"], tags: [] }, "a null blob is a fresh one");
});

test("the strip renders sections when the switch is on and some tag holds a visible tab (source pins)", () => {
  assert.match(RENDER, /const plan = planStrip\(visibleIds, viewTagUnion\(effViews\(\)\), readTabGroups\(\), activeId, phoneLayout\(\),/,
    "the pure module owns the rule; the phone layout and the create in flight are its inputs");
  assert.match(RENDER, /collapsedTabIds = plan\.folded;/);
  assert.match(RENDER, /if \("head" in item\) \{ bar\.appendChild\(makeGroupHead\(item\.head, item\.folded, item\.active, item\.hidden\)\); continue; \}/);
});

test("executed: planStrip — sections + folds; the flat strip when off or untagged; the ACTIVE tab's section never folds", () => {
  const unions = viewTagUnion({ ...V, tags: [...V.tags, { id: "g4", name: "archived", color: "#6b7280", members: ["old1", "old2"] }] });
  const st = parseTabGroups(null);
  const p = planStrip(["web", "old1", "loose", "old2"], unions, st, "web", false);
  assert.equal(p.sectioned, true);
  assert.deepEqual(p.items, [
    { head: { name: "infra", key: "g2", color: "#4EC9B0", ids: ["web"] }, folded: false, active: true, hidden: [] }, { id: "web" },
    { head: { name: "archived", key: "g4", color: "#6b7280", ids: ["old1", "old2"] }, folded: true, active: false, hidden: ["old1", "old2"] },
    { head: { name: null, key: "", color: "", ids: ["loose"] }, folded: false, active: false, hidden: [] }, { id: "loose" },
  ], "archived starts folded: its header alone stands in for old1/old2; infra holds the active tab");
  assert.deepEqual([...p.folded], ["old1", "old2"], "the ids keyboard cycling skips");
  const active = planStrip(["web", "old1", "loose"], unions, st, "old1", false);
  assert.deepEqual(active.items[2], { head: { name: "archived", key: "g4", color: "#6b7280", ids: ["old1"] }, folded: false, active: true, hidden: [] },
    "the active tab's section renders open whatever the store says, and is marked as holding it");
  assert.deepEqual([...active.folded], []);
  assert.ok(!planStrip(["web", "old1"], unions, st, null, false).items.some((i) => "head" in i && i.active), "no active tab: no section holds it");
  const off = planStrip(["web", "old1"], unions, { ...st, on: false }, null, false);
  assert.deepEqual(off.items, [{ id: "web" }, { id: "old1" }], "switch off: the flat strip");
  assert.equal(off.sectioned, false);
  assert.deepEqual(planStrip(["loose"], unions, st, null, false).items, [{ id: "loose" }], "an untagged world: flat");
});

test("executed: the PHONE layout renders the flat strip — every visible id, nothing folded, whatever the store says (sectioning is desktop-only)", () => {
  // the kernel's phone chat page hides #tabs and builds its session list by scraping every rendered
  // tab; it has no header to unfold and no switch, so a folded section there (archived, by default)
  // made its sessions unreachable from the only switcher
  const unions = viewTagUnion({ ...V, tags: [...V.tags, { id: "g4", name: "archived", color: "#6b7280", members: ["old1", "old2"] }] });
  for (const st of [parseTabGroups(null), { on: true, collapsed: ["infra", "qa"], expanded: [], pinned: [] }]) {
    const p = planStrip(["web", "old1", "loose", "old2", "tests"], unions, st, null, true);
    assert.equal(p.sectioned, false);
    assert.deepEqual(p.items, [{ id: "web" }, { id: "old1" }, { id: "loose" }, { id: "old2" }, { id: "tests" }], "the flat strip, in strip order");
    assert.deepEqual([...p.folded], [], "visibleOrder excludes nothing on the phone");
  }
  // render.ts decides "phone" by the SAME media rule the kernel's page uses to swap the strip for its
  // list (_CHAT_MOBILE_CSS) — one string on each side, pinned equal here, so they cannot drift
  const media = RENDER.match(/const PHONE_LAYOUT_MEDIA = "([^"]+)";/)![1];
  assert.equal(media, "(pointer:coarse) and (max-width:1024px)");
  assert.ok(KERNEL.includes('"@media ' + media + '{"'), "the kernel's phone CSS gate is the very same rule");
  assert.match(RENDER, /function phoneLayout\(\): boolean \{\s*\n\s*try \{ return window\.matchMedia\(PHONE_LAYOUT_MEDIA\)\.matches; \} catch \{ return false; \}/);
  // …and the phone layout offers no switch, on either mount
  assert.match(RENDER, /\.\.\.\(phoneLayout\(\) \? \{\} : \{\s*\n\s*groupToggle: \{ label: "Group tabs by tag"/);
  // crossing the boundary (an iPad rotation) re-plans the strip: the CSS side of the same rule flips
  // the instant the media query does, so a plan sampled per render only went stale under the phone
  // list (folded tabs absent from the scrape) until the next push. The flip IS the event — one
  // listener on the same MediaQueryList, beside the fold-state listeners; no resize polling.
  assert.match(RENDER, /try \{ window\.matchMedia\(PHONE_LAYOUT_MEDIA\)\.addEventListener\("change", \(\) => renderTabs\(\)\); \} catch \{/);
  assert.ok(RENDER.indexOf("window.addEventListener(TABGROUPS_EVENT, () => renderTabs());") < RENDER.indexOf('matchMedia(PHONE_LAYOUT_MEDIA).addEventListener("change"'),
    "installed once at module scope with the other strip listeners, never inside a render");
});

test("executed + pinned: the section holding the ACTIVE tab is unfoldable while active — no fold action on its header, a title that says so, a click that stores nothing", () => {
  // planStrip renders the active tab's section open whatever the store says, so a fold click there
  // used to store folded=true that could not render: "click to fold this group" did nothing visible
  // on every click, and the stored fold bit when the user switched to another section
  const unions = viewTagUnion(V);
  const st = parseTabGroups(null);
  const marks = (activeId: string | null) => planStrip(["web", "api", "tests", "loose"], unions, st, activeId, false).items
    .filter((i): i is { head: TabSection; folded: boolean; active: boolean; hidden: string[] } => "head" in i).map((i) => [i.head.name, i.active]);
  assert.deepEqual(marks("web"), [["qa", false], ["infra", true], [null, false]], "exactly the section holding the active tab");
  assert.deepEqual(marks("tests"), [["qa", true], ["infra", false], [null, false]]);
  assert.deepEqual(marks(null), [["qa", false], ["infra", false], [null, false]]);
  // a user-folded section holding the active tab: open AND marked (the fold stays stored for later)
  const folded = setSectionCollapsed(st, "infra", true);
  const inf = planStrip(["web", "tests"], unions, folded, "web", false).items
    .find((i) => "head" in i && i.head.name === "infra") as { head: TabSection; folded: boolean; active: boolean };
  assert.deepEqual([inf.folded, inf.active], [false, true]);
  // render.ts: that header carries NO fold action (a distinct data-act the delegate flashes and
  // otherwise ignores), a title that says why, and no pointer cursor promising a click
  const head = RENDER.slice(RENDER.indexOf("function makeGroupHead("), RENDER.indexOf("function sectionHeadOf("));
  assert.match(head, /function makeGroupHead\(sec: TabSection, collapsed: boolean, holdsActive: boolean, hidden: readonly string\[\]\): HTMLElement \{/);
  assert.match(head, /head\.dataset\.act = holdsActive \? "group-active" : "toggle-group";/);
  assert.equal(headWords("infra", 1, 0, false, true).title, "infra — 1 session; holds the active tab, so it stays open; drag to reorder the groups");
  assert.match(head, /const words = headWords\(name, total, hidden\.length, collapsed, holdsActive\);\s*\n\s*head\.title = words\.title;/, "the words are the pure module's");
  assert.match(head, /\+ \(holdsActive \? " holds-active" : ""\)\);/);
  assert.match(head, /head\.draggable = true;/, "it still drags to reorder the groups");
  const del = RENDER.slice(RENDER.indexOf('"group-active": () => {'), RENDER.indexOf('"group-active": () => {') + 120);
  assert.match(del, /^"group-active": \(\) => \{ \/\* [^*]*\*\/ \},/, "a no-op: the delegate's flash is the whole acknowledgement");
  assert.ok(!del.includes("writeTabGroups"), "…and nothing is stored");
  assert.match(CSS, /\.tab-group-head\.holds-active \{ cursor: default; \}/);
});

test("executed: a create in flight sections under the FIRST requested tag in tagOrder — its future home — from the first paint", () => {
  // the kernel tags a new session before its first push so the tab never lands untagged and jumps;
  // the client's provisional tab used to land in the untagged trail (a client-minted id in no
  // union) and move into its group when the frame arrived — the very jump the kernel avoids
  const unions = viewTagUnion(V);
  const st = parseTabGroups(null);
  const p = planStrip(["web", "prov1", "loose"], unions, st, "prov1", false, { id: "prov1", tags: ["infra", "qa"] });
  assert.deepEqual(p.items.map((i) => ("head" in i ? "#" + i.head.name : i.id)), ["#qa", "prov1", "#infra", "web", "#null", "loose"],
    "qa is first in tagOrder of the requested tags → qa is its home (the kernel's own home-tag rule)");
  const none = planStrip(["web", "prov1"], unions, st, "prov1", false, { id: "prov1", tags: [] });
  assert.deepEqual(none.items.map((i) => ("head" in i ? "#" + i.head.name : i.id)), ["#infra", "web", "#null", "prov1"], "no tags asked → the untagged trail");
  assert.deepEqual(V.tags.map((t) => t.members), [["tests", "api"], ["web", "api"], []], "the unions themselves are untouched");
  assert.match(RENDER, /provisionalTags = req\.tags\?\.slice\(\) \?\? \[\];/, "openProvisional keeps the request's tags…");
  assert.match(RENDER, /provisionalId \? \{ id: provisionalId, tags: provisionalTags \} : null\);/, "…and the plan sections the provisional under them");
  const drop = RENDER.slice(RENDER.indexOf("function dropProvisional("), RENDER.indexOf("function adoptProvisional("));
  assert.match(drop, /provisionalTags = \[\];/, "retired with the provisional");
});

test("executed: the header click sets the fold state from what it RENDERED — never a toggle of the stored bit", () => {
  // the active tab's section renders open whatever the store says; a stored toggle there inverted
  // the click: "fold" on default-folded archived (rendered open for the active tab) stored it OPEN
  // for good, and nothing visible changed
  const d = parseTabGroups(null);
  // archived: stored folded, rendered OPEN (active tab inside) → the click says "fold" → still folded, stored minimally
  assert.deepEqual(setSectionCollapsed(d, "archived", true), { on: true, collapsed: [], expanded: [], pinned: [] });
  assert.equal(isSectionCollapsed(setSectionCollapsed(d, "archived", true), "archived"), true);
  assert.deepEqual(toggleSectionCollapsed(d, "archived"), { on: true, collapsed: [], expanded: ["archived"], pinned: [] },
    "…where the stored toggle would have OPENED it");
  // infra folded by the user, then rendered open (active tab inside), click "fold" → stays folded
  const folded = setSectionCollapsed(d, "infra", true);
  assert.deepEqual(setSectionCollapsed(folded, "infra", true), folded);
  assert.deepEqual(setSectionCollapsed(folded, "infra", false), d, "and a rendered-folded click opens it");
  assert.deepEqual(setSectionCollapsed(setSectionCollapsed(d, "archived", false), "archived", true), d, "re-folding a default-folded section drops the memory");
  // the header carries its rendered state; the delegate reads it
  const head = RENDER.slice(RENDER.indexOf("function makeGroupHead("), RENDER.indexOf("function sectionHeadOf("));
  assert.match(head, /head\.dataset\.folded = collapsed \? "1" : "0";/);
  assert.match(RENDER, /if \(name\) writeTabGroups\(setSectionCollapsed\(readTabGroups\(\), name, el\.dataset\.folded !== "1"\)\);/,
    "rendered open → fold; rendered folded → open");
});

test("a folded section renders its header alone with the folded-away count and one MEMBER-derived pip after it — a label, not a session; cycling skips folded ids", () => {
  assert.match(RENDER, /function visibleOrder\(\): string\[\] \{ return order\.filter\(\(id\) => tabInView\(id\) && !collapsedTabIds\.has\(id\)\); \}/,
    "every cycling path walks visibleOrder (session-views.test pins the three callers)");
  const head = RENDER.slice(RENDER.indexOf("function makeGroupHead("), RENDER.indexOf("function sectionHeadOf("));
  assert.match(head, /n\.textContent = words\.count;/, "the count: every member when open, the hidden members when folded (headWords, executed below)");
  // the pip is the MEMBERS' (a hidden one blocked/waiting/working/retrying), never the header's own status
  // (the user 2026-09-06: no session-tab affordances on a header — but a fold must still say a hidden
  // member needs you, the reason the user-todo flag exists); over the hidden members, after the count
  assert.match(head, /const kind = sectionPip\(hidden\.map\(\(id\) => sessions\.get\(id\)\?\.status\)\);/,
    "one summary pip, classified by tab-state.ts — the same rule the tab itself wears (tab-state.test)");
  assert.match(head, /pip\.title = sectionPipTitle\(kind, sectionPipMembers\(kind, hidden\.map\(\(id\) => sessions\.get\(id\)\)\)\);/, "the tooltip names the sessions");
  assert.ok(head.indexOf('el("span", "tab-group-count")') < head.indexOf("sectionPip("), "after the count");
  assert.ok(!head.includes("tabStateClass("), "the header itself wears no state class");
  assert.ok(!head.includes('"tab-dot"'), "never a .tab-dot — the kernel's mobile scrape keys on the tab pips' vocabulary");
  assert.match(head, /const sep = el\("div", "tab-group-sep"\);/, "the untagged trail is UNLABELED (the ruling): a separator, not a header");
  // the tab's own class comes from the same function
  assert.match(RENDER, /const stateCls = tabStateClass\(s\.status\);\s*\n\s*if \(stateCls\) tab\.classList\.add\(stateCls\);/);
  assert.match(CSS, /\.tab-group-pip \{ flex: 0 0 auto; width: 6px; height: 6px; border-radius: 50%; background: var\(--st-working-bg\); \}/, "small: subordinate to the label");
  assert.match(CSS, /\.tab-group-pip\.blocked \{ background: var\(--st-blocked-bg\); \}/, "status colours keep their meaning");
  assert.match(CSS, /\.tab-group-pip\.retrying \{ background: #e67e22; \}/, "amber, the tab's .tab-retrying hue");
});

test("row hairlines count section headers and the separator as row members (T134's floating look must not return)", () => {
  // a wrapped row made only of folded headers got no line: the painter grouped `.tab` children only
  const painter = RENDER.slice(RENDER.indexOf("function paintTabRowLines("), RENDER.indexOf("let tabRowObserver"));
  assert.match(painter, /if \(!\(t\.classList\.contains\("tab"\) \|\| t\.classList\.contains\("tab-group-head"\) \|\| t\.classList\.contains\("tab-group-sep"\)\)\) continue;/);
  // the separator's offsetTop is the row's: gutters are padding, not margin (see the drag-live pin)
  assert.match(CSS, /\.tab-group-sep \{ flex: 0 0 auto; box-sizing: border-box; width: 13px; padding: 8px 6px; background: var\(--box-border\); background-clip: content-box; \}/);
});

test("the picker's Tags row is for SDK and Codex sessions: disabled behind a note on the tmux pick, and no `tags` ride a tmux create", () => {
  // the kernel refuses tags on a tmux create (a terminal session's id is unknown until it starts);
  // the row, prefilled from a tagged active tab, used to turn every terminal create into a refusal.
  // A Codex create takes them (the kernel applies parent/tags on one since the upstream fold's round
  // 2), so the row and the payload follow ONE predicate — executed here on each backend name
  const pred = RENDER.match(/function backendTakesTags\(be: string\): boolean \{ (return [^}]*); \}/);
  assert.ok(pred, "one predicate decides which backend a chip is for");
  const takes = new Function("be", pred![1]) as (be: string) => boolean;
  assert.equal(takes("sdk"), true);
  assert.equal(takes("codex"), true, "a Codex create takes tags");
  assert.equal(takes("tmux"), false, "a terminal session's id is unknown until it starts");
  assert.equal(takes(""), false);
  assert.match(KERNEL, /_create_codex_session\(nm, cwd, client=client,\s+parent=psid or "", tags=ctags\)/,
    "the premise: the kernel's createSession op applies tags on a Codex create");
  const sync = RENDER.slice(RENDER.indexOf("function syncPickerTags("), RENDER.indexOf("function syncPickerAuth("));
  assert.match(sync, /const takes = backendTakesTags\(pickerBackendChoice\(\)\);/);
  assert.match(sync, /wrap\.classList\.toggle\("disabled", !takes\);/);
  assert.match(sync, /\.forEach\(\(b\) => \{ b\.disabled = !takes; \}\);/);
  assert.match(sync, /note\.style\.display = takes \? "none" : "";/);
  assert.match(RENDER, /tgNote\.textContent = "Tags apply to SDK and Codex sessions";/);
  assert.match(RENDER, /beWrap\.addEventListener\("click", \(\) => \{ syncPickerAuth\(\); syncPickerTags\(\); \}\);/, "re-decided on every backend toggle");
  assert.match(RENDER, /syncPickerTags\(\);\s+\/\/ the backend toggle was just reset/, "…and on every open, after the backend reset");
  assert.match(RENDER, /const tags = backendTakesTags\(backend\)\s*\n\s*\? Array\.from\(tgWrap\.querySelectorAll<HTMLElement>\("\.picker-be-opt\.sel"\)\)/,
    "the create handler sends none for tmux, through the same predicate");
  assert.doesNotMatch(RENDER, /const tags = backend === "sdk"/, "no second, SDK-only copy of the rule");
  assert.match(RENDER, /:not\(\.picker-host\):not\(\.picker-auth\):not\(\.picker-tags\) \.picker-be-opt\.sel/, "a selected tag chip never reads as the backend pick");
  assert.match(CSS, /\.picker-tags\.disabled \.picker-be-opt \{ opacity: 0\.45; cursor: default; pointer-events: none; \}/);
});

test("headers are click-safe: data-act on the node, the action on the stable #tabs delegate, one render path via the event", () => {
  assert.match(RENDER, /head\.dataset\.act = holdsActive \? "group-active" : "toggle-group";/);
  assert.match(RENDER, /"toggle-group": \(el\) => \{\s*\n\s*const name = el\.dataset\.group;\s*\n\s*if \(name\) writeTabGroups\(setSectionCollapsed\(readTabGroups\(\), name, el\.dataset\.folded !== "1"\)\);/);
  assert.match(RENDER, /window\.addEventListener\(TABGROUPS_EVENT, \(\) => renderTabs\(\)\);/, "the same-window delivery");
  assert.match(RENDER, /window\.addEventListener\("storage", \(e\) => \{ if \(e\.key === TABGROUPS_KEY\) renderTabs\(\); \}\);/, "…and a sibling pane's");
  assert.match(RENDER, /if \(name\) writeTabGroups\(setSectionCollapsed/);
  assert.doesNotMatch(RENDER.slice(RENDER.indexOf('"toggle-group": (el) => {'), RENDER.indexOf('"toggle-group": (el) => {') + 300), /renderTabs\(\)/,
    "the toggle does not render itself — the event does, so a local toggle and a sibling pane's take one path");
});

test("dragging a header reorders tagOrder through the views path — the store the timeline's pill drag writes (source pins)", () => {
  assert.match(RENDER, /head\.draggable = true;/);
  assert.match(RENDER, /draggedGroup = name;/);
  const drop = RENDER.slice(RENDER.indexOf('tabs.addEventListener("drop"'), RENDER.indexOf("tabDragCommitted = true;"));
  assert.match(drop, /if \(draggedGroup\) \{/);
  assert.match(drop, /postTagOrder\(reorderTagOrder\(viewTagUnion\(effViews\(\)\)\.map\(\(u\) => u\.name\), draggedGroup, to\)\);/,
    "the FULL union order as a LENS write: the store's blob plus tagOrder, never the pending copy; setTimelineViews underneath (postTagOrder → postLens)");
  const over = RENDER.slice(RENDER.indexOf('tabs.addEventListener("dragover"'), RENDER.indexOf("if (!draggedId || !dragGeom) return;"));
  assert.match(over, /target\.classList\.add\("drop-target"\)/, "the target section wears the insertion cue");
  assert.doesNotMatch(over, /setTimeout|Date\.now/, "no time-based logic — the drop is the event");
  assert.match(CSS, /\.tab-group-head\.drop-target \{ box-shadow: inset 2px 0 0 var\(--accent\); \}/);
});

test("the switch lives at the foot of the chat tag-lens menu beside Configure tags…, desktop mount only", () => {
  assert.match(MENU, /groupToggle\?: \{ label: string; on: \(\) => boolean; toggle: \(\) => void \};/);
  assert.match(MENU, /if \(opts\.groupToggle\)\s*\n\s*row\(opts\.groupToggle\.label, opts\.groupToggle\.on\(\), null, true\)\.addEventListener\("click", \(\) => \{ opts\.groupToggle!\.toggle\(\); build\(\); \}\);/,
    "✓-marked when on; flips and repaints in place like the tag rows");
  assert.ok(MENU.indexOf("if (opts.groupToggle)") < MENU.indexOf('row("Configure tags…"'), "beside — above — Configure tags…");
  assert.match(RENDER, /groupToggle: \{ label: "Group tabs by tag", on: \(\) => readTabGroups\(\)\.on,/);
  const mobile = RENDER.slice(RENDER.indexOf('const mslot = document.getElementById("mtag-slot")'), RENDER.indexOf("paintTabRowLines(bar);"));
  assert.ok(!mobile.includes("groupToggle"), "the phone page hides the strip itself, so its mount offers no switch");
});

test("the picker's Tags row: prefilled from the ACTIVE tab, visible and editable, posted as `tags` on createSession", () => {
  assert.match(RENDER, /interface CreateReq \{ name: string; backend: string; dir: string; host: string; auth\?: string; tags\?: string\[\] \}/);
  assert.match(RENDER, /const tgWrap = el\("div", "picker-backend picker-tags"\);/);
  assert.match(RENDER, /const preset = new Set\(activeId \? unions\.filter\(\(u\) => u\.members\.includes\(activeId!\)\)\.map\(\(u\) => u\.name\) : \[\]\);/,
    "the active tab's tags pre-select — never a silent inherit");
  assert.match(RENDER, /b\.addEventListener\("click", \(\) => b\.classList\.toggle\("sel"\)\);/, "multi-select: each chip on its own");
  assert.match(RENDER, /\.\.\.\(tags\.length \? \{ tags \} : \{\}\) \}\);/, "absent when nothing is picked (the kernel's not-asked contract)");
  assert.match(RENDER, /tgWrapEl\.style\.display = pick \|\| !unions\.length \? "none" : "";/, "hidden with no tags to offer, and in pick-mode");
});

test("the section chrome is a LABEL's (the user 2026-09-06): the surface's sub-line size, letter-spaced, ONE size for its text, a bar not a dot", () => {
  const head = CSS.match(/\.tab-group-head \{[^}]*\}/)![0];
  assert.match(head, /font-size: 0\.82em;/, "0.82em is already on the surface (the menus' sub-lines, the ctx-item sub-line) — no new size (ui/CLAUDE.md)");
  assert.match(head, /letter-spacing: 0\.04em;/);
  assert.match(head, /color: var\(--dim\);/);
  assert.match(CSS, /\.tab-group-count \{ opacity: 0\.7; \}/, "the count inherits the header's size — no em nested inside an em");
  assert.match(CSS, /\.tab-group-name \{ font-weight: 600; \}/);
  assert.match(CSS, /\.tab-group-swatch \{ flex: 0 0 auto; width: 3px; height: 12px; border-radius: 1px; background: var\(--dim\); \}/,
    "the tag's colour as a short bar — a 7px dot beside a name is a session pip");
  assert.doesNotMatch(CSS, /\.tab-group-dot/, "the dot is gone");
  const sizes = new Set(Array.from(CSS.matchAll(/\n\.tab-group-[^{\n]*\{[^}]*font-size: ([^;]+);/g)).map((m) => m[1]));
  assert.deepEqual([...sizes], ["0.82em"], "one font-size across every section rule (the flag's glyph keeps the tab glyph's own class)");
  assert.match(CSS, /\.tab-group-sep \{ flex: 0 0 auto; box-sizing: border-box; width: 13px; padding: 8px 6px;/, "a 1px line inside 6px gutters (padding, so its rect is its footprint)");
});

test("the header's structure and gestures read as a label: chevron (flips with the fold) → colour bar → name → count; a keyboard button; hover/focus say fold, never open; tokens only (the user 2026-09-06)", () => {
  const head = RENDER.slice(RENDER.indexOf("function makeGroupHead("), RENDER.indexOf("function sectionHeadOf("));
  const at = (t: string) => { const i = head.indexOf(t); assert.ok(i >= 0, "present: " + t); return i; };
  assert.ok(at('el("span", "tab-group-caret")') < at('el("span", "tab-group-swatch")')
    && at('el("span", "tab-group-swatch")') < at('el("span", "tab-group-name")')
    && at('el("span", "tab-group-name")') < at('el("span", "tab-group-count")'), "chevron, bar, name, count");
  assert.match(head, /caret\.textContent = "▸";/);
  assert.match(CSS, /\.tab-group-head:not\(\.collapsed\) \.tab-group-caret \{ transform: rotate\(90deg\); \}/,
    "the fold state flips it — the sheet's fold-caret idiom, a CSS transition, no timer");
  assert.match(CSS, /\.tab-group-caret \{[^}]*transition: transform 0\.12s ease;/);
  assert.match(head, /if \(sec\.color\) swatch\.style\.background = sec\.color;/, "the tag's colour from the views store");
  // none of a tab's affordances
  assert.ok(!head.includes("tab-close") && !head.includes("tabStateClass(") && !head.includes("tab-dot") && !head.includes("tabCtxGauge("),
    "no close, no state class of its own, no tab pip, no gauge");
  // keyboard: a button to the keyboard, through the same click → delegate path as the pointer; the active
  // tab's header (no fold action) is not a tab stop
  assert.match(head, /head\.setAttribute\("role", "button"\);\s*\n\s*head\.setAttribute\("aria-expanded", collapsed \? "false" : "true"\);/);
  assert.match(head, /if \(!holdsActive\) \{\s*\n\s*head\.tabIndex = 0;\s*\n\s*head\.addEventListener\("keydown", \(e\) => \{\s*\n\s*if \(\(e\.target as HTMLElement \| null\)\?\.closest\("\.tab-group-flag"\)\) return;\s*\n\s*if \(e\.key === "Enter" \|\| e\.key === " "\) \{ e\.preventDefault\(\); head\.click\(\); \}\s*\n\s*\}\);/,
    "…standing down for the flag button inside it (tab-group-flags.test)");
  // a push mid-read must not kick focus off the header: renderTabs re-focuses the same group after the rebuild
  assert.match(RENDER, /const focusedGroup = \(focusedEl\?\.closest\("\.tab-group-head"\) as HTMLElement \| null\)\?\.dataset\.group;\s*\n\s*const focusedFlag = !!focusedEl\?\.classList\.contains\("tab-group-flag"\);\s*\n\s*const refocusTab = bar\.contains\(document\.activeElement\);/,
    "captured before the tab rule (chat-focus-model.test pins that rule's two-line shape)");
  assert.match(RENDER, /if \(h && h\.tabIndex >= 0\) \(\(focusedFlag && h\.querySelector<HTMLElement>\("\.tab-group-flag"\)\) \|\| h\)\.focus\(\); else focusActiveTab\(\);/,
    "…falling back to the active tab when the group is gone or now holds it");
  // hover/focus: the label brightens and the chevron takes the accent — no row wash (that reads "select me")
  assert.match(CSS, /\.tab-group-head:hover, \.tab-group-head:focus-visible \{ color: var\(--fg\); \}/);
  assert.match(CSS, /\.tab-group-head:hover \.tab-group-caret, \.tab-group-head:focus-visible \.tab-group-caret \{ color: var\(--accent\); \}/);
  for (const m of CSS.matchAll(/\n\.tab-group-head:hover[^{\n]*\{([^}]*)\}/g)) assert.doesNotMatch(m[1], /background/, "no wash on hover");
  assert.match(CSS, /\.tab-group-head:focus-visible \{ outline: 1px solid var\(--accent\); outline-offset: -1px; \}/);
  assert.match(head, /head\.draggable = true;/, "still drags to reorder the groups");
  assert.match(head, /head\.dataset\.act = holdsActive \? "group-active" : "toggle-group";/, "…and still folds through the delegate");
  // theme: every section rule resolves through tokens — no raw hex or rgba — so the light theme needs no
  // override, and the tokens are ones the strip already wears (theme-parity.test.ts checks --fg/--dim/
  // --accent against --bg in both themes)
  const rules = Array.from(CSS.matchAll(/\n(\.tab-group-[^{\n]*)\{([^}]*)\}/g));
  assert.ok(rules.length >= 15, "the section rules were found: " + rules.length);
  for (const [, sel, body] of rules) {
    if (sel.trim() === ".tab-group-pip.retrying") continue;   // the one literal: the tab's own amber, checked equal below
    assert.doesNotMatch(body.replace(/var\([^)]*\)/g, "V"), /#[0-9a-fA-F]{3,8}\b|rgba?\(/, "a raw colour in " + sel.trim());
  }
  assert.equal(CSS.match(/\.tab-group-pip\.retrying \{ background: (#[0-9a-fA-F]{6}); \}/)![1], CSS.match(/\.tab\.tab-retrying \{ --state: (#[0-9a-fA-F]{6}); \}/)![1],
    "the pip's retrying amber IS the tab's (a status literal the sheet keeps raw on the tab too)");
  const toks = new Set((rules.map((m) => m[2]).join(" ").match(/var\((--[a-z-]+)/g) || []).map((m) => m.slice(4)));
  for (const t of toks) assert.ok(["--fg", "--dim", "--accent", "--accent-wash", "--box-border", "--st-working-bg", "--st-blocked-bg"].includes(t), "a token the strip does not already wear: " + t);
});

// SHOW WHEN FOLDED (the user 2026-09-06): a member pinned to its section keeps its tab on the strip
// under the folded header, in strip order; the header stands in for the HIDDEN members alone — its
// count and its user-todo flag read those, never a tab already on screen. A view preference like the
// fold, stored beside it under romp:tabgroups, keyed by the section the user sees (sectionKey) and the
// sid. The toggle is a row in the tab menu's Tags flyout beside the "Move to" rows.
const VP = { ...V, tags: [...V.tags, { id: "g4", name: "archived", color: "#6b7280", members: ["old1", "old2", "old3"] }] };
const ARCH: SectionRef = { key: "g4", name: "archived" };
const headsOf = (p: ReturnType<typeof planStrip>) =>
  p.items.filter((i): i is { head: TabSection; folded: boolean; active: boolean; hidden: string[] } => "head" in i);
const MAKE_HEAD = RENDER.slice(RENDER.indexOf("function makeGroupHead("), RENDER.indexOf("function sectionHeadOf("));

test("executed: a folded section with one PINNED member renders the header, then that member; the hidden ids alone fold away", () => {
  const unions = viewTagUnion(VP);
  const st = setPinned(parseTabGroups(null), ARCH, "old2", true);
  assert.equal(isPinned(st, ARCH, "old2"), true);
  assert.equal(isPinned(st, ARCH, "old1"), false, "the sid must match — a pin is one member's, not the tag's");
  assert.equal(isPinned(st, { key: "g2", name: "infra" }, "old2"), false, "…and the section must: a move to another group starts unpinned");
  assert.deepEqual(st.pinned, [{ tag: "g4", sid: "old2" }], "stored under the section's key (the local tag's id) and the sid");
  const p = planStrip(["web", "old1", "old2", "old3", "loose"], unions, st, "web", false);
  assert.deepEqual(p.items.map((i) => ("head" in i ? `#${i.head.name}${i.folded ? "(folded)" : ""}` : i.id)),
    ["#infra", "web", "#archived(folded)", "old2", "#null", "loose"], "the header, then the pinned member in its place; old1/old3 stay folded");
  const arch = headsOf(p).find((h) => h.head.name === "archived")!;
  assert.deepEqual(arch.hidden, ["old1", "old3"], "what the header stands in for");
  assert.deepEqual([...p.folded], ["old1", "old3"], "keyboard cycling skips the hidden ones only — the pinned tab is reachable");
  assert.equal(arch.head.key, "g4", "the plan keys the section as the pin row does (sectionRef)");
  // a second member's pin is its own: setting or clearing one leaves the other (a filter on the tag
  // alone would drop every pin under the tag)
  const two = setPinned(st, ARCH, "old3", true);
  assert.deepEqual(two.pinned, [{ tag: "g4", sid: "old2" }, { tag: "g4", sid: "old3" }]);
  assert.deepEqual(setPinned(two, ARCH, "old3", false).pinned, [{ tag: "g4", sid: "old2" }]);
  assert.deepEqual(setPinned(two, ARCH, "old2", true).pinned, [{ tag: "g4", sid: "old3" }, { tag: "g4", sid: "old2" }], "set on again: one entry, moved to the end");
  // an open section: nothing hidden, pins irrelevant
  assert.deepEqual(headsOf(planStrip(["old1", "old2"], unions, st, "old1", false))[0].hidden, []);
});

test("executed: the folded header's user-todo flag counts HIDDEN members only — a pinned member's own tab shows its glyph", () => {
  const unions = viewTagUnion(VP);
  const sessions = new Map([
    ["old1", { name: "old1", userTodos: [] as { id: string; text: string }[] }],
    ["old2", { name: "old2", userTodos: [{ id: "t1", text: "synthetic need" }] }],
    ["old3", { name: "old3", userTodos: [{ id: "t2", text: "another synthetic need" }] }],
  ]);
  const st0 = parseTabGroups(null);
  const all = headsOf(planStrip(["web", "old1", "old2", "old3"], unions, st0, "web", false)).find((h) => h.head.name === "archived")!;
  assert.deepEqual(sectionTodoFlag(all.hidden.map((id) => sessions.get(id))), { count: 2, names: ["old2", "old3"] }, "nothing pinned: both count");
  const st = setPinned(st0, ARCH, "old2", true);
  const some = headsOf(planStrip(["web", "old1", "old2", "old3"], unions, st, "web", false)).find((h) => h.head.name === "archived")!;
  assert.deepEqual(sectionTodoFlag(some.hidden.map((id) => sessions.get(id))), { count: 1, names: ["old3"] }, "old2 is on the strip: its own tab carries the glyph");
  const both = setPinned(st, ARCH, "old3", true);
  const none = headsOf(planStrip(["web", "old1", "old2", "old3"], unions, both, "web", false)).find((h) => h.head.name === "archived")!;
  assert.equal(sectionTodoFlag(none.hidden.map((id) => sessions.get(id))), null, "every flagged member shown → no header flag");
  // render.ts reads the plan's hidden list for the flag, as for the count and the pip
  assert.match(MAKE_HEAD, /const flag = sectionTodoFlag\(hidden\.map\(\(id\) => sessions\.get\(id\)\)\);/);
});

test("executed: a pin follows the section the user sees — the local tag's id, else the NAME; never a remote host's tag id, which changes with the host set", () => {
  // two hosts carry `infra` and no local tag does: the key was the first host's tag id, so that host
  // detaching (or a local `infra` appearing) re-keyed the section and every pinned member folded away
  // with no gesture on it
  const A = { id: "TESTHOST-A:t1", host: "TESTHOST-A", name: "infra", color: "#4EC9B0", members: ["TESTHOST-A:m1"] };
  const B = { id: "TESTHOST-B:t2", host: "TESTHOST-B", name: "infra", color: "#4EC9B0", members: ["TESTHOST-B:m1"] };
  const both = viewTagUnion({ active: "all", tags: [], remoteTags: [A, B] });
  const infra = both.find((u) => u.name === "infra")!;
  assert.deepEqual(infra.ids, ["TESTHOST-A:t1", "TESTHOST-B:t2"]);
  assert.equal(sectionKey(infra), "infra", "remote-only: the name");
  assert.deepEqual(sectionRef(infra), { key: "infra", name: "infra" });
  let st = setSectionCollapsed(parseTabGroups(null), "infra", true);
  st = setPinned(st, sectionRef(infra), "TESTHOST-B:m1", true);
  assert.deepEqual(st.pinned, [{ tag: "infra", sid: "TESTHOST-B:m1" }]);
  const tabs = (unions: ReturnType<typeof viewTagUnion>, s: typeof st) =>
    planStrip(["TESTHOST-A:m1", "TESTHOST-B:m1", "loose"], unions, s, "loose", false).items.filter((i) => "id" in i).map((i) => (i as { id: string }).id);
  assert.deepEqual(tabs(both, st), ["TESTHOST-B:m1", "loose"], "pinned: on the strip under the folded header");
  const aGone = planStrip(["TESTHOST-A:m1", "TESTHOST-B:m1", "loose"], viewTagUnion({ active: "all", tags: [], remoteTags: [B] }), st, "loose", false);
  assert.deepEqual(aGone.items.map((i) => ("head" in i ? `#${i.head.name}${i.folded ? "(folded)" : ""}` : i.id)), ["#infra(folded)", "TESTHOST-B:m1", "#null", "TESTHOST-A:m1", "loose"],
    "host A detached: B's member is still pinned under the folded header (A's, in no tag now, trails)");
  assert.deepEqual([...aGone.folded], [], "nothing folded away");
  const localToo = viewTagUnion({ active: "all", tags: [{ id: "g7", name: "infra", color: "#4EC9B0", members: ["web"] }], remoteTags: [A, B] });
  const li = localToo.find((u) => u.name === "infra")!;
  assert.equal(sectionKey(li), "g7", "a local tag: its id");
  assert.deepEqual(tabs(localToo, st), ["TESTHOST-B:m1", "loose"], "a local infra appeared: the name-stored pin still matches (lookup takes the key OR the name)");
  // the local id outranks the name, so a rename keeps the pin
  const st2 = setPinned(parseTabGroups(null), sectionRef(li), "web", true);
  assert.deepEqual(st2.pinned, [{ tag: "g7", sid: "web" }]);
  assert.equal(isPinned(st2, { key: "g7", name: "ops" }, "web"), true, "renamed to ops: the id-stored pin stands");
  assert.equal(isPinned(st2, { key: "g8", name: "infra" }, "web"), false, "another local tag that took the name: not this pin");
  // an unpin through the section drops the entry whichever key it was stored under
  assert.deepEqual(setPinned(st, sectionRef(li), "TESTHOST-B:m1", false).pinned, [], "the name-stored entry, dropped through the local id");
  assert.equal(isPinned(st, sectionRef(li), "TESTHOST-A:m1"), false, "the sid must match");
  // sectionKey itself: the local id first, else the name — a remote id never
  assert.equal(sectionKey({ name: "infra", color: "", members: [], ids: ["TESTHOST-A:t1", "g2"], localId: "g2", remotes: [] }), "g2");
  assert.equal(sectionKey({ name: "remotepool", color: "", members: [], ids: ["TESTHOST-A:r1"], localId: null, remotes: [] }), "remotepool");
  assert.equal(sectionTabs(["TESTHOST-A:m1"], viewTagUnion(V))[0].key, "remotepool", "the plan's sections carry the same key");
});

test("executed: prunePinned drops the pins of tags and sessions that no longer exist — on the pin row's write, never per render", () => {
  const unions = viewTagUnion(VP);   // qa g1, infra g2, empty g3, archived g4, remotepool (remote-only)
  const st = { ...parseTabGroups(null), pinned: [
    { tag: "g4", sid: "old2" },                        // stands: archived, a known session
    { tag: "infra", sid: "web" },                      // stands: a union's name (one with a local id too)
    { tag: "remotepool", sid: "TESTHOST-A:m1" },       // stands: a remote-only union, by name
    { tag: "g9", sid: "old1" },                        // a deleted tag
    { tag: "g4", sid: "closed1" },                     // a closed session
    { tag: "TESTHOST-A:r1", sid: "TESTHOST-A:m1" },    // an older store's pin under a remote id: no section answers to it
  ] };
  const known = new Set(["web", "api", "tests", "old1", "old2", "old3", "TESTHOST-A:m1", "loose"]);
  const pruned = prunePinned(st, unions, known);
  assert.deepEqual(pruned.pinned, [{ tag: "g4", sid: "old2" }, { tag: "infra", sid: "web" }, { tag: "remotepool", sid: "TESTHOST-A:m1" }]);
  assert.deepEqual([pruned.on, pruned.collapsed, pruned.expanded], [st.on, st.collapsed, st.expanded], "the fold state rides through untouched");
  assert.equal(prunePinned(pruned, unions, known), pruned, "nothing to drop: the same object");
  // render.ts: the pin row's write is the ONE prune site, over every tab the strip knows (a view-hidden
  // session still exists); the plan reads pins and never rewrites them — a prune per render could act
  // on a transient frame (a views blob mid-write, a host's tags not yet arrived) and put a tab away
  assert.equal(RENDER.split("prunePinned(").length - 1, 1, "one call site");
  assert.match(RENDER, /writeTabGroups\(prunePinned\(togglePinned\(readTabGroups\(\), sec, id\), unionFor\(\), knownTabIds\(\)\)\); build\(\);/);
  assert.match(RENDER, /function knownTabIds\(\): Set<string> \{ return new Set<string>\(\[\.\.\.order, \.\.\.tabMeta\.keys\(\)\]\); \}/);
  const TG = ui("webview", "tab-groups.ts");
  const plan = TG.slice(TG.indexOf("export function planStrip("), TG.indexOf("export function reorderTagOrder("));
  assert.ok(!plan.includes("prunePinned"), "the plan never prunes");
});

test("executed: the pin persists with the fold state under romp:tabgroups, survives the fold writes, and junk entries drop; unpin hides the tab again", () => {
  const d = parseTabGroups(null);
  const on = togglePinned(d, ARCH, "old2");
  assert.deepEqual(on, { on: true, collapsed: [], expanded: [], pinned: [{ tag: "g4", sid: "old2" }] });
  assert.deepEqual(setSectionCollapsed(on, "infra", true).pinned, on.pinned, "a fold write carries the pins through");
  assert.deepEqual(toggleSectionCollapsed(on, "archived").pinned, on.pinned);
  const off = togglePinned(on, ARCH, "old2");
  assert.deepEqual(off, d, "toggling back drops the entry — the menu's one way off");
  assert.deepEqual(togglePinned(off, ARCH, "old2"), on, "and on again");
  assert.deepEqual(setPinned(setPinned(d, ARCH, "old2", true), ARCH, "old2", true).pinned, [{ tag: "g4", sid: "old2" }], "set on twice: one entry");
  assert.deepEqual(parseTabGroups('{"pinned":[{"tag":"g4","sid":"old2"},{"tag":3,"sid":"x"},"junk",null,{"tag":"g1"},{"sid":"old1"}]}').pinned,
    [{ tag: "g4", sid: "old2" }], "only well-formed (tag, sid) string pairs survive a read");
  assert.deepEqual(parseTabGroups('{"pinned":"nope"}').pinned, []);
  assert.deepEqual(parseTabGroups('{"pinned":[{"tag":"g4","sid":"old2","extra":1}]}').pinned, [{ tag: "g4", sid: "old2" }], "unknown fields do not ride along");
  // round trip through the store
  const store = new Map<string, string>();
  const g: any = globalThis;
  const savedLS = g.localStorage;
  g.localStorage = { getItem: (k: string) => store.get(k) ?? null, setItem: (k: string, v: string) => { store.set(k, v); } };
  try {
    writeTabGroups(on);
    assert.deepEqual(readTabGroups().pinned, [{ tag: "g4", sid: "old2" }]);
    writeTabGroups(off);
    assert.deepEqual(readTabGroups().pinned, [], "unpinned: gone from the store");
  } finally {
    g.localStorage = savedLS;
  }
  // unpin → the plan hides the tab again
  const unions = viewTagUnion(VP);
  const shown = planStrip(["web", "old1", "old2"], unions, on, "web", false);
  assert.ok(shown.items.some((i) => "id" in i && i.id === "old2"), "pinned: on the strip");
  const hidden = planStrip(["web", "old1", "old2"], unions, off, "web", false);
  assert.ok(!hidden.items.some((i) => "id" in i && i.id === "old2"), "unpinned: folded away again");
  assert.deepEqual([...hidden.folded], ["old1", "old2"]);
});

test("the toggle is a row in the tab menu's Tags flyout beside the Move-to rows: the home tag's chip, ✓ when on, the fold's own write and render path (source pins)", () => {
  const fly = RENDER.slice(RENDER.indexOf('const sub = el("div", "ctx-menu ctx-sub ctx-sub-tags");'), RENDER.indexOf("// New tag… — an inline input"));
  const pin = fly.slice(fly.indexOf("// SHOW WHEN FOLDED"));
  assert.ok(fly.indexOf('lb.textContent = "Move to " + g.name') < fly.indexOf("// SHOW WHEN FOLDED"), "after the Move-to rows, before New tag…");
  assert.match(pin, /if \(home\) \{\s*\n\s*const sec = sectionRef\(home\);\s*\n\s*const on = isPinned\(readTabGroups\(\), sec, id\);/,
    "only with a home tag (there is no fold to show through otherwise); keyed as the plan keys its sections (sectionRef)");
  assert.doesNotMatch(pin, /isPinned\(readTabGroups\(\), home\.name|togglePinned\(readTabGroups\(\), home\.name|sectionKey\(home\)/,
    "never the bare name (a local tag's key is its id) and never a key without the name (a name-stored pin would not match)");
  assert.match(pin, /const row = el\("div", "ctx-item ctx-item-toggle ctx-item-pin" \+ \(on \? " current" : ""\)\);/, "the menus' ✓ mark when on");
  assert.match(pin, /chip\.style\.background = home\.color \|\| "var\(--dim\)"; row\.appendChild\(chip\);/, "the home tag's chip, like its neighbours");
  assert.match(pin, /lb\.textContent = "Show when folded";/);
  assert.match(pin, /writeTabGroups\(prunePinned\(togglePinned\(readTabGroups\(\), sec, id\), unionFor\(\), knownTabIds\(\)\)\); build\(\);/,
    "the write prunes, notifies (TABGROUPS_EVENT → renderTabs) and the flyout repaints its ✓ — no renderTabs() call of its own");
  assert.doesNotMatch(pin, /renderTabs\(\)|setTimeout/);
  // the phone layout's flat strip has no fold to show through: the plan ignores pins there (no-op by construction)
  const p = planStrip(["web", "old1", "old2"], viewTagUnion(VP), setPinned(parseTabGroups(null), ARCH, "old2", true), "web", true);
  assert.deepEqual(p.items, [{ id: "web" }, { id: "old1" }, { id: "old2" }]);
});

test("executed: a folded section whose EVERY member is pinned stays folded — the chevron tells the truth — and its header says so: the total, not 0, and why nothing is hidden", () => {
  // pin both of infra's members, fold infra: the header read "▸ infra 0" over two visible tabs, and the
  // click flipped it to "▾ infra 2" with nothing else changing
  const unions = viewTagUnion({ ...V, tagOrder: ["infra", "qa"] });   // infra first, so api homes there: infra = web, api
  const infra: SectionRef = { key: "g2", name: "infra" };
  let st = setSectionCollapsed(parseTabGroups(null), "infra", true);
  st = setPinned(setPinned(st, infra, "web", true), infra, "api", true);
  const p = planStrip(["web", "api", "tests"], unions, st, "tests", false);
  const h = headsOf(p).find((x) => x.head.name === "infra")!;
  assert.deepEqual([h.folded, h.hidden], [true, []], "folded — the stored state the click acts on, so the header still opens it — with nothing hidden");
  assert.deepEqual(p.items.map((i) => ("head" in i ? `#${i.head.name}${i.folded ? "(folded)" : ""}` : i.id)), ["#infra(folded)", "web", "api", "#qa", "tests"]);
  assert.deepEqual([...p.folded], [], "every tab reachable");
  // the words render.ts paints for that header
  assert.deepEqual(headWords("infra", 2, 0, true, false), {
    count: "2", label: "infra, 2 sessions, folded, all shown",
    title: "infra — folded, but all 2 sessions are set to show when folded, so none is hidden; click to open",
  }, "the total, never a 0 beside two visible tabs; the title names the menu row that did it");
  assert.equal(headWords("infra", 1, 0, true, false).title, "infra — folded, but its one session is set to show when folded, so none is hidden; click to open");
  // …and for the ordinary folded, part-pinned, open and active headers
  assert.deepEqual(headWords("infra", 2, 2, true, false), { count: "2", label: "infra, 2 sessions folded", title: "infra — 2 sessions folded; click to open" });
  assert.deepEqual(headWords("infra", 2, 1, true, false), { count: "1", label: "infra, 1 session folded", title: "infra — 1 session folded; click to open" },
    "one pinned: the hidden count, the pinned tab shows itself");
  assert.deepEqual(headWords("infra", 2, 0, false, false), { count: "2", label: "infra, 2 sessions", title: "infra — 2 sessions; click to fold this group; drag to reorder the groups" });
  assert.deepEqual(headWords("infra", 3, 0, false, true), { count: "3", label: "infra, 3 sessions", title: "infra — 3 sessions; holds the active tab, so it stays open; drag to reorder the groups" });
  assert.match(MAKE_HEAD, /const words = headWords\(name, total, hidden\.length, collapsed, holdsActive\);\s*\n\s*head\.title = words\.title;/);
  assert.match(MAKE_HEAD, /n\.textContent = words\.count;/);
  assert.ok(!MAKE_HEAD.includes("hidden.length : total"), "no second count rule beside the pure one");
  assert.match(GUIDE, /when every tab in a section is set to\s+show, the folded header shows the full count and its tooltip says nothing is hidden\./);
});
