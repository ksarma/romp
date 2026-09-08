// HIDING SESSIONS INSIDE A TAB GROUP (the user 2026-09-08, who found the pins and the fold not enough: a
// single session should be put away inside its group, from the group's own view, apart from folding the
// whole group). The flag is a per-(tab, section) entry beside the Show-when-folded pins in the per-browser
// romp:tabgroups store (tab-groups.ts TabGroupsState.hidden), the strip plan leaves a hidden member's tab
// off the strip in either fold state and lets the header stand in for it, and the section snapshot lists
// every member with a Hide or Show button and a Hidden (N) fold. Executed on the pure modules (tab-groups.ts,
// tab-snapshot.ts, tab-state.ts) and source-pinned on render.ts / styles.css / the docs, the tab-groups.test.ts
// harness (the renderer has no jsdom). The notes-api demo world, synthetic ids, TESTHOST.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { viewTagUnion } from "./session-views";
import { parseTabGroups, readTabGroups, writeTabGroups, setSectionCollapsed, toggleSectionCollapsed, isSectionCollapsed, planStrip,
         isHidden, setHidden, toggleHidden, isPinned, setPinned, prunePinned, followTagRenames, followAdoption, tagRenames, headWords,
         homeSectionOf, neighborOfFolded, TABGROUPS_KEY, type StripHead, type SectionRef, type TabGroupsState } from "./tab-groups";
import { snapshotModel, snapshotRow, snapshotHeading, hiddenNeeds, hiddenFoldWords, actWords, rowWords, type SnapModel } from "./tab-snapshot";
import { sectionPip, sectionTodoFlag } from "./tab-state";

const ui = (...p: string[]) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", ...p), "utf8");
const RENDER = ui("webview", "render.ts");
const CSS = ui("webview", "styles.css");
const GUIDE = fs.readFileSync(path.resolve(process.cwd(), "..", "docs", "guide.md"), "utf8");
const REF = fs.readFileSync(path.resolve(process.cwd(), "..", "docs", "reference.md"), "utf8");
const SNAP = RENDER.slice(RENDER.indexOf("let snapView: string | null = null;"), RENDER.indexOf("function showActive() {"));
const HEAD = RENDER.slice(RENDER.indexOf("function makeGroupHead("), RENDER.indexOf("function sectionHeadOf("));
const TABS = RENDER.slice(RENDER.indexOf("function renderTabs() {"), RENDER.indexOf("function stripAftermath("));

// the notes-api demo world: web, api and tests in "infra"; old1 and old2 in "archived" (folded by default); a loose one
const V = {
  active: "all",
  tags: [
    { id: "g1", name: "infra", color: "#4EC9B0", members: ["web", "api", "tests"] },
    { id: "g2", name: "archived", color: "#6b7280", members: ["old1", "old2"] },
  ],
  seq: 3,
};
const INFRA: SectionRef = { name: "infra", localId: "g1" };
const ALL = ["web", "api", "tests", "old1", "old2", "loose"];
const HOSTS: ReadonlySet<string> = new Set();
const unions = viewTagUnion(V);
const heads = (items: ReturnType<typeof planStrip>["items"]) => items.filter((i): i is StripHead => "head" in i);
/** the strip as the user reads it: the tab ids on it, the infra header, and the plan */
const strip = (st: TabGroupsState, active = "web", visible: readonly string[] = ALL, u = unions) => {
  const p = planStrip(visible, u, st, active, false);
  return { p, tabs: p.items.filter((i): i is { id: string } => "id" in i).map((i) => i.id), infra: heads(p.items).find((h) => h.head.name === "infra")! };
};
const d = parseTabGroups(null);
const apiHidden = setHidden(d, INFRA, "api", true);

test("executed: the store. An older blob has no hidden list and reads as nothing hidden; the flag rides romp:tabgroups beside the pins; junk drops; the earlier pin shape migrates for hides too", () => {
  assert.deepEqual(d.hidden, [], "fresh: nothing hidden");
  assert.deepEqual(parseTabGroups('{"on":true,"collapsed":["qa"],"pinned":[{"sid":"web","name":"infra","id":"g1"}]}').hidden, [], "a blob from before the list: nothing hidden, the rest as it was");
  assert.deepEqual(parseTabGroups('{"hidden":[{"sid":"api","name":"infra","id":"g1"},{"sid":"old1","name":"archived"},{"sid":3},"x",{"name":"infra"}]}').hidden,
    [{ sid: "api", name: "infra", id: "g1" }, { sid: "old1", name: "archived" }], "the pins' parser: an entry needs a sid and a name; junk drops");
  assert.deepEqual(parseTabGroups('{"hidden":"nope"}').hidden, [], "a wrong-typed list reads as none");
  assert.deepEqual(parseTabGroups('{"hidden":[{"tag":"g1","sid":"api"},{"tag":"gone","sid":"web"}]}', unions).hidden,
    [{ sid: "api", name: "infra", id: "g1" }, { sid: "web", name: "gone" }], "the branch's earlier {tag, sid} shape migrates against the unions, as a pin's does");
  // write and read round-trip through localStorage (the two-path idiom), the pins untouched
  const store = new Map<string, string>();
  const g: any = globalThis;
  const savedLS = g.localStorage;
  g.localStorage = { getItem: (k: string) => store.get(k) ?? null, setItem: (k: string, v: string) => { store.set(k, v); } };
  try {
    const st = setPinned(apiHidden, INFRA, "web", true);
    writeTabGroups(st);
    assert.ok(store.has(TABGROUPS_KEY));
    assert.deepEqual(JSON.parse(store.get(TABGROUPS_KEY)!).hidden, [{ sid: "api", name: "infra", id: "g1" }], "persisted under its own key in the one blob");
    assert.deepEqual(readTabGroups(unions), { on: true, collapsed: [], expanded: [], pinned: [{ sid: "web", name: "infra", id: "g1" }], hidden: [{ sid: "api", name: "infra", id: "g1" }] });
  } finally {
    g.localStorage = savedLS;
  }
});

test("executed: isHidden, setHidden and toggleHidden are per section and explicit, and write neither the fold nor the pins", () => {
  assert.equal(isHidden(d, INFRA, "api"), false);
  assert.equal(isHidden(apiHidden, INFRA, "api"), true);
  assert.deepEqual(apiHidden.hidden, [{ sid: "api", name: "infra", id: "g1" }], "the entry names the section by name and local id, as a pin does");
  assert.equal(isHidden(apiHidden, { name: "archived", localId: "g2" }, "api"), false, "another section: not hidden there");
  assert.equal(isHidden(apiHidden, { name: "infra", localId: null }, "api"), true, "matched by the name alone (a section a remote tag makes)");
  assert.equal(isHidden(apiHidden, { name: "platform", localId: "g1" }, "api"), true, "matched by the local id alone (the tag renamed while no client watched)");
  assert.deepEqual(setHidden(apiHidden, INFRA, "api", true).hidden, apiHidden.hidden, "on twice: one entry");
  assert.deepEqual(setHidden(apiHidden, INFRA, "api", false).hidden, [], "off removes exactly this section's entry");
  const both = setHidden(apiHidden, { name: "archived", localId: "g2" }, "api", true);
  assert.equal(both.hidden.length, 2, "a hide under another section stands beside it");
  assert.deepEqual(setHidden(both, INFRA, "api", false).hidden, [{ sid: "api", name: "archived", id: "g2" }], "off leaves the other section's entry");
  assert.equal(isHidden(toggleHidden(apiHidden, INFRA, "api"), INFRA, "api"), false);
  assert.deepEqual(setHidden(d, { name: null, localId: null }, "loose", true).hidden, [], "the untagged trail has no fold and no hide");
  // the fold lists and the pins ride through untouched, in both directions
  assert.deepEqual([apiHidden.on, apiHidden.collapsed, apiHidden.expanded, apiHidden.pinned], [true, [], [], []]);
  const folded = setSectionCollapsed(apiHidden, "infra", true);
  assert.deepEqual(folded.hidden, apiHidden.hidden, "a fold write carries the hides through");
  assert.deepEqual(setSectionCollapsed(folded, "infra", false).hidden, apiHidden.hidden, "and so does the open");
  assert.deepEqual(setPinned(apiHidden, INFRA, "api", true).hidden, apiHidden.hidden, "a pin write too");
});

test("executed: the strip filter. Open, the section shows its members less the hidden ones; the header stands in for them; the keyboard skips them; the header is an active hidden tab's stand-in", () => {
  const before = strip(d);
  assert.deepEqual(before.tabs, ["web", "api", "tests", "loose"], "nothing hidden: infra's three tabs (archived starts folded)");
  const { p, tabs, infra } = strip(apiHidden);
  assert.deepEqual(tabs, ["web", "tests", "loose"], "api has no tab while infra is open");
  assert.deepEqual([infra.folded, infra.hidden, infra.hides], [false, ["api"], ["api"]], "the header stands in for api, by its own flag");
  assert.deepEqual(infra.head.ids, ["web", "api", "tests"], "the section still holds it: the snapshot lists it, the count includes it");
  assert.ok(p.folded.has("api"), "the keyboard skips it: visibleOrder drops the plan's folded set");
  assert.ok(!p.folded.has("web") && !p.folded.has("tests"));
  // the active tab hidden: the header is marked and stands in, as for a folded tab (focus, arrows, the pane)
  const active = strip(apiHidden, "api");
  assert.deepEqual([active.infra.active, active.infra.folded], [true, false], "an open header marked as holding the tab being read");
  assert.equal(homeSectionOf(active.p.items, "api")!.name, "infra");
  assert.equal(neighborOfFolded(active.p.items, "api", 1), "web", "the arrows step from the header's place");
  assert.equal(neighborOfFolded(active.p.items, "api", -1), "loose");
});

test("executed: collapse then expand leaves hidden hidden. Folding folds everything; opening brings back exactly the members not hidden; the hides never change on a fold", () => {
  const folded = setSectionCollapsed(apiHidden, "infra", true);
  const f = strip(folded);
  assert.deepEqual(f.tabs, ["loose"], "folded: the header alone");
  assert.deepEqual([f.infra.folded, f.infra.hidden, f.infra.hides], [true, ["web", "api", "tests"], ["api"]], "the stand-in set is every member; the hides are still api's flag alone");
  const opened = setSectionCollapsed(folded, "infra", false);
  assert.deepEqual(strip(opened).tabs, ["web", "tests", "loose"], "opened: exactly the non-hidden members are back");
  assert.deepEqual(opened.hidden, apiHidden.hidden, "the flag is as it was");
  assert.deepEqual(toggleSectionCollapsed(toggleSectionCollapsed(apiHidden, "infra"), "infra").hidden, apiHidden.hidden, "a toggle round trip too");
  assert.equal(isSectionCollapsed(opened, "infra"), false);
  // the default-folded section: old1 hidden inside archived, opened, then folded again
  const ARCH: SectionRef = { name: "archived", localId: "g2" };
  const oldHidden = setHidden(setSectionCollapsed(d, "archived", false), ARCH, "old1", true);
  assert.deepEqual(strip(oldHidden).tabs, ["web", "api", "tests", "old2", "loose"], "archived open: old2 shows, old1 is hidden");
  const refolded = setSectionCollapsed(oldHidden, "archived", true);
  assert.deepEqual(strip(refolded).tabs, ["web", "api", "tests", "loose"]);
  assert.deepEqual(strip(setSectionCollapsed(refolded, "archived", false)).tabs, ["web", "api", "tests", "old2", "loose"], "and open again: old1 still hidden");
});

test("executed: pins compose. Four combinations, and the hide wins where they meet; the pin resumes when the session is shown again", () => {
  const folded = setSectionCollapsed(d, "infra", true);
  const shows = (st: TabGroupsState) => ({ open: strip(st).tabs.includes("api"), folded: strip(setSectionCollapsed(st, "infra", true)).tabs.includes("api") });
  assert.deepEqual(shows(d), { open: true, folded: false }, "neither: shown while open, folded away with the rest");
  assert.deepEqual(shows(setPinned(d, INFRA, "api", true)), { open: true, folded: true }, "pinned: shown in both states (Show when folded)");
  assert.deepEqual(shows(apiHidden), { open: false, folded: false }, "hidden: shown in neither");
  const both = setPinned(apiHidden, INFRA, "api", true);
  assert.deepEqual(shows(both), { open: false, folded: false }, "pinned and hidden: the hide wins, in either fold state");
  assert.equal(isPinned(both, INFRA, "api"), true, "the pin is kept, inert");
  const shown = setHidden(both, INFRA, "api", false);
  assert.deepEqual(shows(shown), { open: true, folded: true }, "shown again: the pin resumes");
  // the folded header's stand-in set and count: a hidden pinned member is folded away and counted
  const bothFolded = strip(setSectionCollapsed(both, "infra", true));
  assert.deepEqual(bothFolded.infra.hidden, ["web", "api", "tests"]);
  assert.equal(headWords("infra", 3, 3, true, false).count, "3");
  void folded;
});

test("executed + pinned: nothing lost. An open header wears the pip and the todo flag over its hidden members, and its words say how many are hidden; the strip's signature reads the hides", () => {
  type Sess = { name: string; status?: { state: string }; userTodos?: { id: string }[] };
  const sessions = new Map<string, Sess>([
    ["web", { name: "web", status: { state: "working" } }],
    ["api", { name: "api", status: { state: "needsInput" }, userTodos: [{ id: "t1" }] }],
    ["tests", { name: "tests", status: { state: "ready" } }],
  ]);
  const { infra } = strip(apiHidden);
  assert.equal(infra.folded, false);
  const kind = sectionPip(infra.hidden.map((id) => sessions.get(id)?.status));
  assert.equal(kind, "blocked", "the open header's pip: red, for the hidden member waiting on you (web's working shows on web's own tab)");
  assert.deepEqual(sectionTodoFlag(infra.hidden.map((id) => sessions.get(id))), { count: 1, names: ["api"] }, "and its flag");
  assert.equal(sectionPip(strip(d).infra.hidden.map((id) => sessions.get(id)?.status)), null, "nothing hidden: an open header carries no pip (every tab wears its own)");
  // the words: the count stays the total, the label and the title say how many are hidden
  assert.deepEqual(headWords("infra", 3, 1, false, false), { count: "3", label: "infra, 3 sessions, 1 hidden",
    title: "infra — 3 sessions, 1 hidden; click to fold this group and see its sessions at a glance; drag to reorder the groups" });
  assert.equal(headWords("infra", 3, 2, false, true).label, "infra, 3 sessions, 2 hidden, holds the tab you are reading");
  assert.equal(headWords("infra", 3, 0, false, false).label, "infra, 3 sessions", "nothing hidden: the words as they were");
  assert.equal(headWords("infra", 3, 1, false, true, true).title, "infra — 3 sessions, 1 hidden; holds the tab you are reading; click to go back to the transcript; drag to reorder the groups");
  // render.ts: the marks' block runs whenever the header stands in for a member (folded or open), over `hidden`
  assert.match(HEAD, /if \(hidden\.length\) \{\s*\n(?:\s*\/\/[^\n]*\n)*\s*const kind = sectionPip\(hidden\.map\(\(id\) => sessions\.get\(id\)\?\.status\)\);/, "the pip over the stand-in set, open or folded");
  assert.match(HEAD, /const flag = sectionTodoFlag\(hidden\.map\(\(id\) => sessions\.get\(id\)\)\);/, "the flag over the same set");
  assert.ok(!HEAD.includes("if (collapsed) {"), "no folded-only block: an open header with hidden members carries the marks too");
  assert.match(TABS, /hiddenTabIds = new Set\(plan\.items\.flatMap\(\(it\) => \("head" in it \? it\.hides : \[\]\)\)\);/, "the hidden ids, for setActive");
  assert.match(TABS, /it\.folded, it\.active, it\.hidden, it\.hides\] : it\.id\)\)/, "a hide flip changes the plan's signature, so the strip repaints");
});

test("executed: the pane's model. Hidden rows are flagged and keep needs-you; the heading counts them; the fold's words; the Hide and Show words; a flip alone is a new model", () => {
  const sec = { name: "infra", color: "#4EC9B0", ids: ["web", "api", "tests"], hides: ["api"] };
  const session = (id: string) => ({ web: { name: "web", status: { state: "working" } }, api: { name: "api", status: { state: "ready" }, userTodos: [] }, tests: { name: "tests", status: { state: "ready" } } } as any)[id] ?? null;
  const ledger = (id: string) => (id === "api" ? { needsInput: true, summary: "Designing the notes schema" } : { needsInput: false });
  const m = snapshotModel(sec, session, ledger, null);
  assert.deepEqual(m.rows.map((r) => [r.id, r.hidden]), [["web", false], ["api", true], ["tests", false]], "every member is a row; the hidden one is flagged");
  assert.equal(m.rows[1].needsYou, true, "the feed's needs-you stands on a hidden row: the pane still shows it");
  assert.equal(m.rows[1].state, "needs you");
  assert.equal(hiddenNeeds(m.rows), 1, "the fold's chip counts the hidden members that need you");
  assert.equal(hiddenNeeds(snapshotModel({ ...sec, hides: [] }, session, ledger, null).rows), 0, "a shown member's needs-you is the row's, not the fold's");
  assert.equal(snapshotModel(sec, session, ledger, m), m, "no change: the same object (the renderer rebuilds nothing)");
  const shown = snapshotModel({ ...sec, hides: [] }, session, ledger, m);
  assert.notEqual(shown, m, "the flag flipped and nothing else: a new model, so the rows move between the lists");
  assert.deepEqual(shown.rows.map((r) => r.hidden), [false, false, false]);
  assert.equal(snapshotRow("api", session("api"), ledger("api")).hidden, false, "the default: shown");
  // the words
  assert.deepEqual(snapshotHeading("infra", 3, 1), { count: "3 sessions, 1 hidden", label: "infra: 3 sessions, 1 hidden; click one to open it" });
  assert.deepEqual(snapshotHeading("infra", 3), { count: "3 sessions", label: "infra: 3 sessions; click one to open it" }, "nothing hidden: as before");
  assert.deepEqual(hiddenFoldWords(1, 1, false), { text: "Hidden (1)", needs: "1 needs you",
    label: "Hidden, 1 session hidden from the strip while this group is open, 1 needs you; click to see them",
    title: "1 session hidden from the strip while this group is open; 1 needs you; click to see them" });
  assert.deepEqual(hiddenFoldWords(2, 0, true), { text: "Hidden (2)", needs: "",
    label: "Hidden, 2 sessions hidden from the strip while this group is open; click to fold them",
    title: "2 sessions hidden from the strip while this group is open; click to fold them" });
  assert.equal(hiddenFoldWords(3, 2, false).needs, "2 need you");
  assert.deepEqual(actWords(m.rows[1], "infra"), { text: "Show", label: "Show api on the strip again", title: "Put api's tab back on the strip" });
  assert.deepEqual(actWords(m.rows[0], "infra"), { text: "Hide", label: "Hide web from the strip while infra is open",
    title: "Hide web's tab from the strip while infra is open; it stays in infra, listed under Hidden here, and its needs-you still shows on the header" });
  assert.equal(rowWords(m.rows[1]).label, "api — hidden from the strip — needs you — Designing the notes schema", "a reader hears why the row sits under the fold");
  assert.equal(rowWords(m.rows[0]).label, "web — working", "a shown row's label as before");
});

test("pinned: render.ts. The host's delegate takes hide, show and toggle-hidden; the button passes the rendered state; the write is the one prune site; two keyed lists; focus follows a row across them; the fold is view state", () => {
  // the acts, on the ONE stable host (click-safe: the rows are rebuilt from every push that changes one)
  assert.match(SNAP, /hide: \(node\) => setRowHidden\(node\.dataset\.id, true\),\s*\n\s*show: \(node\) => setRowHidden\(node\.dataset\.id, false\),/, "explicit on and off, never a toggle of the stored bit");
  assert.match(SNAP, /"toggle-hidden": \(\) => \{\s*\n\s*snapHiddenOpen = !snapHiddenOpen;\s*\n\s*const h = document\.getElementById\("tab-snapshot"\);\s*\n\s*if \(h && snapModel\) syncHiddenFold\(h, snapModel\);\s*\n\s*\} \}\);/,
    "the fold's head: view state, no store write, no strip render");
  assert.equal(SNAP.split("delegate(host").length - 1, 1, "one delegate, installed with the host");
  assert.doesNotMatch(SNAP.slice(SNAP.indexOf("function snapshotRowNode("), SNAP.indexOf("function showActive")), /addEventListener\("click"/, "no per-node click handler: the nodes are rebuilt");
  // the write: the pin row's prune site, with the section the pane shows, addressed as a pin addresses it
  assert.match(SNAP, /function setRowHidden\(id: string \| undefined, on: boolean\): void \{\s*\n\s*const head = snapView \? lastStripItems\.find\(\(it\): it is StripHead => "head" in it && it\.head\.name === snapView\) : undefined;\s*\n\s*if \(!id \|\| !head \|\| head\.head\.name === null\) return;\s*\n\s*writeTabGroupsPruned\(setHidden\(tabGroups\(\), head\.head, id, on\)\);\s*\n\}/);
  assert.equal(RENDER.split("prunePinned(").length - 1, 1, "one prune site (writeTabGroupsPruned), shared with the pin row");
  assert.match(RENDER, /function writeTabGroupsPruned\(st: TabGroupsState\): void \{\s*\n\s*writeTabGroups\(prunePinned\(st, viewTagUnion\(effViews\(\)\), knownTabIds\(\), reachableHosts\(\)\)\);/);
  assert.equal(RENDER.split("writeTabGroupsPruned(").length - 1, 3, "the definition, the pin row, the snapshot's write");
  // the row: a real button beside the open button, its act and face from the row's rendered state
  assert.match(SNAP, /const act = document\.createElement\("button"\);\s*\n\s*act\.type = "button";\s*\n\s*item\.append\(btn, act\);/, "a native button: Tab reaches it, Enter and Space are its own click");
  assert.match(SNAP, /act\.className = "snap-act";\s*\n\s*act\.dataset\.act = r\.hidden \? "show" : "hide"; act\.dataset\.id = r\.id;\s*\n\s*act\.textContent = w\.text;\s*\n\s*act\.title = w\.title;\s*\n\s*act\.setAttribute\("aria-label", w\.label\);/,
    "the pure module's words (actWords): face, hover, spoken label");
  // the plan's hides ride the model; two lists, one reconcile each, keyed by the session id
  assert.match(SNAP, /const next = snapshotModel\(\{ \.\.\.head\.head, hides: head\.hides \}, /);
  assert.match(SNAP, /const shown = next\.rows\.filter\(\(r\) => !r\.hidden\), hid = next\.rows\.filter\(\(r\) => r\.hidden\);\s*\n\s*const words = snapshotHeading\(next\.name, next\.rows\.length, hid\.length\);/);
  assert.match(SNAP, /reconcileRows<SnapRow, Element>\(list, shown, keyOf, /);
  assert.match(SNAP, /reconcileRows<SnapRow, Element>\(hlist, hid, keyOf, /);
  assert.match(SNAP, /const hl = el\("div", "snap-list snap-hidden-list"\); hl\.setAttribute\("role", "list"\);/, "the hidden list is a list too");
  assert.match(SNAP, /fh\.className = "snap-hidden-head"; fh\.dataset\.act = "toggle-hidden";/, "the fold's head is a button on the delegate");
  assert.match(SNAP, /fh\.setAttribute\("aria-expanded", snapHiddenOpen \? "true" : "false"\);/, "a disclosure to assistive tech");
  assert.match(SNAP, /fold\.style\.display = n \? "" : "none";/, "the fold shows only while something is hidden");
  assert.match(SNAP, /chip\.textContent = words\.needs;\s*\n\s*chip\.style\.display = words\.needs \? "" : "none";/, "the needs-you chip, only when a hidden member needs you");
  assert.match(SNAP, /^let snapHiddenOpen = false;/m, "closed by default: the head's count and chip say what is inside");
  // focus follows the toggled row: its button in the other list, or the fold's head when that list is folded away
  assert.match(SNAP, /const focusedAct = focused && focusedList && focused\.classList\.contains\("snap-act"\) \? focused\.dataset\.id : undefined;/);
  assert.match(SNAP, /const moved = focusedAct !== undefined \? host\.querySelector<HTMLElement>\(`\.snap-act\[data-id="\$\{focusedAct\}"\]`\) : null;/);
  assert.match(SNAP, /else if \(moved\) \(snapHiddenOpen \|\| !moved\.closest\("\.snap-hidden-list"\) \? moved : host\.querySelector<HTMLElement>\("\.snap-hidden-head"\)\)\?\.focus\(\);/);
  // the sync runs on every paint (after the reconcile) and on the head's click
  assert.match(SNAP, /reconcileRows<SnapRow, Element>\(hlist, hid, keyOf, [^\n]*\n\s*syncHiddenFold\(host, next\);/);
});

test("executed + pinned: a hidden session's needs-you is reachable. The fold's chip and its row say so; a pick shows the transcript with the header as stand-in and leaves the fold and the flag alone", () => {
  // the plan: api hidden and active. Its header is marked and stands in; nothing unfolds, since opening infra
  // would bring no tab on screen (the hide stands) and the pick named the session, not the group
  const { p, infra } = strip(apiHidden, "api");
  assert.deepEqual([infra.active, infra.folded, p.folded.has("api")], [true, false, true]);
  assert.match(RENDER, /if \(collapsedTabIds\.has\(id\) && !hiddenTabIds\.has\(id\)\) unfoldSectionOf\(id\);/, "setActive: the unfold is for a folded-away tab, not a hidden one");
  assert.match(RENDER, /^let hiddenTabIds = new Set<string>\(\);/m, "the ids hidden by their own flag, kept from the last plan beside collapsedTabIds");
  // the same for a hidden member of a FOLDED section: the fold stays as the user left it
  const folded = strip(setSectionCollapsed(apiHidden, "infra", true), "api");
  assert.deepEqual([folded.infra.active, folded.infra.folded, folded.p.folded.has("api")], [true, true, true]);
  // the row keeps the needs-you word and the feed's verdict (the model test above); the open act is the row's own
  assert.match(SNAP, /if \(!rowStillOpen\(snapModel\?\.rows\.find\(\(r\) => r\.id === id\), sessions\.has\(id\), tabMeta\.has\(id\), closingTabs\.has\(id\)\)\) return;\s*\n\s*setActive\(id\); focusActiveTab\(\);/,
    "a hidden row opens like any row");
});

test("executed: a session rename changes nothing (entries key on the sid); a tag rename carries the hide as it carries a pin, on the adoption", () => {
  // the session renamed: the plan and the flag key on ids, never names
  assert.equal(isHidden(apiHidden, INFRA, "api"), true);
  assert.equal(snapshotRow("api", { name: "notes-api", status: { state: "ready" } }, null, isHidden(apiHidden, INFRA, "api")).hidden, true, "a new name, the same row flag");
  assert.deepEqual(strip(apiHidden).tabs, ["web", "tests", "loose"]);
  // the tag renamed, watched: infra becomes platform under the same id; the hide follows, as a pin does
  const V1 = { ...V, tags: [{ ...V.tags[0], name: "platform" }, V.tags[1]], seq: 4 };
  const u1 = viewTagUnion(V1);
  const renames = tagRenames(V, V1);
  assert.deepEqual(renames.map((r) => [r.id, r.from, r.to]), [["g1", "infra", "platform"]]);
  const withPin = setPinned(apiHidden, INFRA, "web", true);
  const carried = followTagRenames(withPin, renames, u1, V1);
  assert.deepEqual(carried.hidden, [{ sid: "api", name: "platform", id: "g1" }], "the hide under the new name, with the id");
  assert.deepEqual(carried.pinned, [{ sid: "web", name: "platform", id: "g1" }], "the pin beside it, the same way");
  assert.deepEqual(carried.followed, { g1: "platform" });
  const after = planStrip(ALL, u1, carried, "web", false);
  assert.deepEqual(after.items.filter((i): i is { id: string } => "id" in i).map((i) => i.id), ["web", "tests", "loose"], "api still hidden, under platform");
  assert.deepEqual(heads(after.items).find((h) => h.head.name === "platform")!.hides, ["api"]);
  assert.equal(followAdoption(withPin, V, V1, u1).hidden[0].name, "platform", "through the adoption's one entry point");
  // a remote-only hide (no id) follows a remote tag's rename by name where the tag holds the session
  const R0 = { active: "all", tags: [], remoteTags: [{ id: "TESTHOST-A:r1", host: "TESTHOST-A", name: "pool", color: "#7aa2f7", members: ["TESTHOST-A:m1"], seq: 2 }] };
  const R1 = { ...R0, remoteTags: [{ ...R0.remoteTags[0], name: "workers", seq: 3 }] };
  const remoteHidden = setHidden(d, { name: "pool", localId: null }, "TESTHOST-A:m1", true);
  assert.deepEqual(remoteHidden.hidden, [{ sid: "TESTHOST-A:m1", name: "pool" }], "no id stored for a remote tag");
  assert.deepEqual(followTagRenames(remoteHidden, tagRenames(R0, R1), viewTagUnion(R1), R1).hidden, [{ sid: "TESTHOST-A:m1", name: "workers" }]);
});

test("executed: leaving the tag. The session shows wherever it lands, its stale entry goes at the next write; a closed session's goes; a fork is a new sid and starts shown; a detached host's stands", () => {
  const known = new Set(ALL);
  // api moved to archived: the entry names infra, so api is not hidden under archived; the write prunes the entry
  const V2 = { ...V, tags: [{ ...V.tags[0], members: ["web", "tests"] }, { ...V.tags[1], members: ["old1", "old2", "api"] }] };
  const u2 = viewTagUnion(V2);
  const moved = strip(setSectionCollapsed(apiHidden, "archived", false), "web", ALL, u2);
  assert.deepEqual(moved.tabs, ["web", "tests", "api", "old1", "old2", "loose"], "api shows under archived (in strip order there), where the entry does not reach");
  assert.deepEqual(prunePinned(apiHidden, u2, known, HOSTS).hidden, [], "the next write drops the entry: no union of the entry's name or id holds api");
  assert.equal(prunePinned(apiHidden, unions, known, HOSTS), apiHidden, "still a member: the same object, nothing dropped");
  // moved back later, after a write pruned it: shown (the hide was api's membership of infra at the time)
  assert.deepEqual(strip(prunePinned(apiHidden, u2, known, HOSTS), "web", ALL, unions).tabs, ["web", "api", "tests", "loose"]);
  // closed: not a known tab any more
  assert.deepEqual(prunePinned(apiHidden, unions, new Set(["web", "tests"]), HOSTS).hidden, []);
  // a fork or a promoted thread is a NEW sid that inherits the tags (the kernel's rule): no entry names it, so it shows
  const V3 = { ...V, tags: [{ ...V.tags[0], members: ["web", "api", "tests", "api-fork"] }, V.tags[1]] };
  const forked = strip(apiHidden, "web", [...ALL, "api-fork"], viewTagUnion(V3));
  assert.deepEqual(forked.tabs, ["web", "tests", "api-fork", "loose"], "the fork's tab is on the strip; api stays hidden");
  // a detached host's entry is not judged: it waits for the host's tabs, as a pin does
  const remote = setHidden(d, { name: "pool", localId: null }, "TESTHOST-A:m1", true);
  assert.equal(prunePinned(remote, unions, known, HOSTS), remote, "the host is not reachable: the entry stands");
  assert.deepEqual(prunePinned(remote, unions, known, new Set(["TESTHOST-A"])).hidden, [], "the host reachable and the session not a known tab: judged, and gone");
  // the pins and the hides are pruned together, and the fold state rides through
  const both = setPinned(apiHidden, INFRA, "api", true);
  const pruned = prunePinned(setSectionCollapsed(both, "infra", true), u2, known, HOSTS);
  assert.deepEqual([pruned.pinned, pruned.hidden, pruned.collapsed], [[], [], ["infra"]]);
});

test("executed: the phone layout and sectioning off render the flat strip, hidden members included, as the folds do", () => {
  assert.deepEqual(planStrip(ALL, unions, apiHidden, "web", true).items, ALL.map((id) => ({ id })), "the phone: every tab, no header to stand in");
  assert.deepEqual(planStrip(ALL, unions, { ...apiHidden, on: false }, "web", false).items, ALL.map((id) => ({ id })), "Group tabs by tag off: the flat strip");
  assert.deepEqual([...planStrip(ALL, unions, apiHidden, "web", true).folded], [], "nothing skipped on the phone");
});

test("docs and the sheet: the guide's paragraph, the reference's section, the sheet's rules (tokens only, the one sub-line size), and no em dash in the new text", () => {
  const para = GUIDE.slice(GUIDE.indexOf("**Hiding a session inside its group.**"), GUIDE.indexOf("### The feed"));
  assert.ok(para.length > 200, "the paragraph is in the tab-groups part of the guide");
  assert.match(para, /Each row in this view has a \*\*Hide\*\* button\./);
  assert.match(para, /moves its row under a\s+\*\*Hidden \(N\)\*\* fold at the foot of the view, one click away; the row's \*\*Show\*\* button puts the\s+tab back\./);
  assert.match(para, /fold the group and open it again, and the hidden\s+sessions stay hidden while the rest come back\./);
  assert.match(para, /the group's header keeps\s+the dot and the ⚑ flag for its hidden sessions/);
  assert.match(para, /the fold's head says so in red before you open it, and its row\s+says \*\*needs you\*\*\./);
  assert.match(para, /Clicking a hidden session's row shows its transcript, with the header standing\s+in for the tab, and leaves it hidden\./);
  assert.match(para, /the hide wins, and the setting resumes when you show it again\./);
  assert.match(para, /keeps the\s+setting when its group is renamed, and shows again wherever it lands when it leaves the group\./);
  assert.ok(!para.includes("—"), "no em dash in the new guide text");
  assert.ok(!/fleet/i.test(para));
  const ref = REF.slice(REF.indexOf("### The tab strip's per-browser choices"), REF.indexOf("### Model and effort, from the statusline or a typed command"));
  assert.match(ref, /`romp:tabgroups`, not on the kernel/);
  assert.match(ref, /which sessions are hidden inside their group \(the group view's \*\*Hide\*\*\)/);
  assert.match(ref, /Folding or opening a group never changes which of\s+its sessions are hidden\. A store written before hiding existed reads as nothing hidden\./);
  assert.ok(!ref.includes("—") && !/fleet/i.test(ref));
  // the sheet: the act button wears the small box and the one sub-line size; pattern A hover; the fold's head is
  // the heading's dress as a button; the caret turns with .open; tokens only, no raw color
  const block = CSS.slice(CSS.indexOf("/* HIDE AND SHOW"), CSS.indexOf(".snap-hidden-list {") + 60);
  assert.match(block, /\.snap-item \{ display: flex; align-items: flex-start; gap: 6px; \}/);
  assert.match(block, /\.snap-act \{[^}]*padding: var\(--btn-pad-sm\);[^}]*border-radius: var\(--radius-pill\);/);
  assert.match(block, /\.snap-act:hover \{ border-color: var\(--accent\); color: var\(--accent\); background: var\(--accent-wash\); \}/, "the one action hover");
  assert.match(block, /\.snap-act:focus-visible \{ outline: 1px solid var\(--accent\); outline-offset: 1px; \}/);
  assert.match(block, /\.snap-hidden-head \{[^}]*font-size: 0\.82em; font-weight: 600; letter-spacing: 0\.04em;/, "the heading's dress");
  assert.match(block, /\.snap-hidden\.open \.tab-group-caret \{ transform: rotate\(90deg\); \}/);
  assert.deepEqual([...new Set(block.match(/font-size: [^;]+/g))], ["font-size: 0.82em"], "one sub-line size, the header's");
  assert.equal(block.replace(/\/\*[\s\S]*?\*\//g, "").match(/#[0-9a-fA-F]{3,8}\b/g), null, "no raw color: the light theme needs no override");
  // the fold's needs chip is the row's own red chip class
  assert.match(SNAP, /el\("span", "snap-flag needs snap-hidden-needs"\)/);
});
