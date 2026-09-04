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
         toggleSectionCollapsed, reorderTagOrder, applyTagOrder, TABGROUPS_KEY, DEFAULT_COLLAPSED } from "./tab-groups";

const ui = (...p: string[]) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", ...p), "utf8");
const RENDER = ui("webview", "render.ts");
const CSS = ui("webview", "styles.css");
const MENU = ui("webview", "tag-menu.ts");
const VIEWS = ui("webview", "session-views.ts");

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
  assert.deepEqual(sectionTabs(["loose"], unions), [{ name: null, color: "", ids: ["loose"] }]);
});

test("executed: per-browser state — on by default, archived starts folded, toggles remember, junk reads as the default", () => {
  const d = parseTabGroups(null);
  assert.deepEqual(d, { on: true, collapsed: [], expanded: [] });
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
  assert.deepEqual(parseTabGroups('{"on":false,"collapsed":["qa",3],"expanded":"x"}'), { on: false, collapsed: ["qa"], expanded: [] },
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
    writeTabGroups({ on: false, collapsed: ["qa"], expanded: ["archived"] });
    assert.ok(store.has(TABGROUPS_KEY), "persisted under the one key");
    assert.deepEqual(readTabGroups(), { on: false, collapsed: ["qa"], expanded: ["archived"] });
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
  assert.match(RENDER, /const sectioned = tgState\.on && anySectioned\(visibleIds, unions\);/);
  assert.match(RENDER, /for \(const sec of sectionTabs\(visibleIds, unions\)\)/, "the pure module owns the rule");
  assert.match(RENDER, /if \("head" in item\) \{ bar\.appendChild\(makeGroupHead\(item\.head, item\.collapsed\)\); continue; \}/);
  // flat strip when off / untagged: the same ids, no headers
  assert.match(RENDER, /\} else \{\s*\n\s*for \(const id of visibleIds\) plan\.push\(\{ id \}\);/);
});

test("a folded section renders its header alone with a count + one pip; the ACTIVE tab's section never folds; cycling skips folded ids", () => {
  assert.match(RENDER, /const collapsed = sec\.name !== null && isSectionCollapsed\(tgState, sec\.name\) && !\(activeId !== null && sec\.ids\.includes\(activeId\)\);/,
    "auto-expand on activate — keyboard focus can never land on a hidden node");
  assert.match(RENDER, /if \(collapsed\) \{ for \(const id of sec\.ids\) collapsedTabIds\.add\(id\); continue; \}/);
  assert.match(RENDER, /function visibleOrder\(\): string\[\] \{ return order\.filter\(\(id\) => tabInView\(id\) && !collapsedTabIds\.has\(id\)\); \}/,
    "every cycling path walks visibleOrder (session-views.test pins the three callers)");
  const head = RENDER.slice(RENDER.indexOf("function makeGroupHead("), RENDER.indexOf("function sectionHeadOf("));
  assert.match(head, /n\.textContent = String\(sec\.ids\.length\);/, "the count");
  assert.match(head, /el\("span", "tab-group-pip" \+ \(blocked \? " blocked" : ""\)\)/, "one summary pip: working, or red for blocked/waiting");
  assert.ok(!head.includes('"tab-dot"'), "never a .tab-dot — the kernel's mobile scrape keys on the tab pips' vocabulary");
  assert.match(head, /const sep = el\("div", "tab-group-sep"\);/, "the untagged trail is UNLABELED (the ruling): a separator, not a header");
});

test("headers are click-safe: data-act on the node, the action on the stable #tabs delegate, one render path via the event", () => {
  assert.match(RENDER, /head\.dataset\.act = "toggle-group";/);
  assert.match(RENDER, /"toggle-group": \(el\) => \{\s*\n\s*const name = el\.dataset\.group;\s*\n\s*if \(name\) writeTabGroups\(toggleSectionCollapsed\(readTabGroups\(\), name\)\);/);
  assert.match(RENDER, /window\.addEventListener\(TABGROUPS_EVENT, \(\) => renderTabs\(\)\);/, "the same-window delivery");
  assert.match(RENDER, /window\.addEventListener\("storage", \(e\) => \{ if \(e\.key === TABGROUPS_KEY\) renderTabs\(\); \}\);/, "…and a sibling pane's");
  assert.match(RENDER, /if \(name\) writeTabGroups\(toggleSectionCollapsed/);
  assert.doesNotMatch(RENDER.slice(RENDER.indexOf('"toggle-group": (el) => {'), RENDER.indexOf('"toggle-group": (el) => {') + 300), /renderTabs\(\)/,
    "the toggle does not render itself — the event does, so a local toggle and a sibling pane's take one path");
});

test("dragging a header reorders tagOrder through the views path — the store the timeline's pill drag writes (source pins)", () => {
  assert.match(RENDER, /head\.draggable = true;/);
  assert.match(RENDER, /draggedGroup = name;/);
  const drop = RENDER.slice(RENDER.indexOf('tabs.addEventListener("drop"'), RENDER.indexOf("tabDragCommitted = true;"));
  assert.match(drop, /if \(draggedGroup\) \{/);
  assert.match(drop, /postViews\(applyTagOrder\(v, reorderTagOrder\(viewTagUnion\(v\)\.map\(\(u\) => u\.name\), draggedGroup, to\)\)\);/,
    "the FULL union order, one optimistic blob, setTimelineViews underneath (postViews)");
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

test("the section chrome reuses the strip's type sizes — labels match labels (font-size rule)", () => {
  const head = CSS.match(/\.tab-group-head \{[^}]*\}/)![0];
  const tab = CSS.match(/^\.tab \{[\s\S]*?\n\}/m)![0];
  assert.equal(head.match(/font-size: ([\d.]+em)/)![1], tab.match(/font-size: ([\d.]+em)/)![1], "the header wears the tab's size");
  assert.match(CSS, /\.tab-group-count \{ font-size: 0\.82em; opacity: 0\.7; \}/, "the count at the sub-line size every menu uses");
  assert.match(CSS, /\.tab-group-dot \{ flex: 0 0 auto; width: 7px; height: 7px; border-radius: 50%;/, "the tab pip's 7px dot");
  assert.match(CSS, /\.tab-group-pip\.blocked \{ background: var\(--st-blocked-bg\); \}/, "status colours keep their meaning");
  assert.match(CSS, /\.tab-group-sep \{ flex: 0 0 auto; width: 1px;/);
});
