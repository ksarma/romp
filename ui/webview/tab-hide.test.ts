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
import { createRequire } from "node:module";
import { viewTagUnion } from "./session-views";
import { parseTabGroups, readTabGroups, writeTabGroups, setSectionCollapsed, toggleSectionCollapsed, isSectionCollapsed, planStrip,
         isHidden, setHidden, toggleHidden, isPinned, setPinned, prunePinned, followTagRenames, followAdoption, tagRenames, headWords,
         homeSectionOf, neighborOfFolded, sectionRef, TABGROUPS_KEY, TABGROUPS_EVENT, type StripHead, type SectionRef, type TabGroupsState } from "./tab-groups";
import { snapshotModel, snapshotRow, snapshotHeading, hiddenNeeds, hiddenFoldWords, actWords, rowWords, onYou, standInPip, type SnapModel } from "./tab-snapshot";
import { sectionPip, sectionTodoFlag, sectionTodoTitle, sectionTodoPhrase, sectionDoorTitle, doorClick, compactCount, stripAndHidden, SHOW_GROUP_CLICK, BACK_TO_TRANSCRIPT_CLICK } from "./tab-state";
import { repeatedClick } from "./tab-snapshot-view";
import { pressHold } from "./actions";

const ui = (...p: string[]) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", ...p), "utf8");
const RENDER = ui("webview", "render.ts");
const CSS = ui("webview", "styles.css");
const GUIDE = fs.readFileSync(path.resolve(process.cwd(), "..", "docs", "guide.md"), "utf8");
const REF = fs.readFileSync(path.resolve(process.cwd(), "..", "docs", "reference.md"), "utf8");
const SNAP = RENDER.slice(RENDER.indexOf("let snapView: string | null = null;"), RENDER.indexOf("function showActive("));
const HEAD = RENDER.slice(RENDER.indexOf("function makeGroupHead("), RENDER.indexOf("function sectionHeadOf("));
const TABS = RENDER.slice(RENDER.indexOf("function renderTabs() {"), RENDER.indexOf("function stripAftermath("));
const GROUPS = ui("webview", "tab-groups.ts");

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
  // THE FEED'S VERDICT reaches the header too (round 1 of the review): render.ts derives the pip through standInPip, the
  // tab's rule with onYou folded in, so a hidden session that went idle after asking, which only the feed files under
  // needs-you (lg.needsInput), is red on the strip with its name in the tooltip, as the Hide button's hover promises:
  // the one judgment the row's chip and the Hidden fold's count already made
  const stand = (lg: (id: string) => any) => standInPip(infra.hidden.map((id) => ({ session: sessions.get(id), ledger: lg(id) })));
  assert.deepEqual(stand(() => null), { kind: "blocked", names: ["api"] }, "the tab's own case, as sectionPip says it");
  sessions.set("api", { name: "api", status: { state: "ready" }, userTodos: [] });
  assert.equal(stand(() => null), null, "idle, no verdict: no pip");
  assert.deepEqual(stand((id) => (id === "api" ? { needsInput: true } : null)), { kind: "blocked", names: ["api"] }, "idle, the feed's needs-you: the red pip, api named");
  assert.equal(onYou({ state: "ready" }, { needsInput: true }), true);
  assert.equal(onYou({ state: "needsInput" }, null), true, "the tab's own case is a floor: the feed build trails the chip by one push");
  assert.equal(onYou({ state: "ready" }, { needsInput: false }), false);
  assert.equal(onYou(undefined, null), false);
  assert.deepEqual(standInPip([{ session: { name: "web", status: { state: "working" } }, ledger: { needsInput: false } }]), { kind: "working", names: ["web"] }, "no one on you: the tab's rule decides, gold");
  assert.deepEqual(standInPip([{ session: { name: "web", status: { state: "working" } }, ledger: null }, { session: { name: "api", status: { state: "ready" } }, ledger: { needsInput: true } }]),
    { kind: "blocked", names: ["api"] }, "on you outranks working, and only the on-you member is named");
  assert.equal(standInPip([{ session: null, ledger: null }]), null, "a placeholder tab: nothing");
  assert.equal(snapshotRow("api", { name: "api", status: { state: "ready" } }, { needsInput: true }).needsYou, true, "the row's chip, from the same onYou");
  assert.equal(hiddenNeeds([snapshotRow("api", { name: "api", status: { state: "ready" } }, { needsInput: true }, true)]), 1, "and the fold's count");
  // the words: the count is the compact `<shown>+<hidden>` (the user 2026-09-08, who runs a dozen tag groups: the words
  // "2 hidden" took too much of the strip; round 1 had made the count say how many are hidden because the bare total,
  // "3" beside two tabs, read as a wrong number, and the compact form keeps that honesty, its first number the tabs on
  // the strip, in the width of a plain count); the label keeps the full words, the title spells the form out
  assert.deepEqual(headWords("infra", 3, 1, false, false), { count: "2+1", label: "infra, 3 sessions, 1 hidden",
    title: "infra — 3 sessions, 2 on the strip and 1 hidden; click to fold this group and see its sessions at a glance; drag to reorder the groups" });
  assert.equal(headWords("infra", 3, 2, false, true).count, "1+2");
  assert.equal(headWords("infra", 8, 2, false, false).count, "6+2", "eight members, two hidden: six tabs on the strip");
  assert.equal(headWords("infra", 3, 3, false, false).count, "0+3", "every member hidden: no tab on the strip, and the count says so");
  assert.equal(headWords("infra", 3, 3, false, false).title, "infra — 3 sessions, none on the strip and 3 hidden; click to fold this group and see its sessions at a glance; drag to reorder the groups");
  assert.deepEqual([compactCount(8, 2), compactCount(3, 0), compactCount(1, 1)], ["6+2", "3", "0+1"], "the one source of the form (the door's words lead with it: sectionDoorTitle below)");
  assert.deepEqual([stripAndHidden(8, 2), stripAndHidden(3, 3)], ["6 on the strip and 2 hidden", "none on the strip and 3 hidden"], "the form spelled out, for the hover and the door's name");
  assert.equal(headWords("infra", 3, 2, false, true).label, "infra, 3 sessions, 2 hidden, holds the tab you are reading");
  assert.deepEqual([headWords("infra", 3, 0, false, false).count, headWords("infra", 3, 0, false, false).label], ["3", "infra, 3 sessions"], "nothing hidden: the words as they were");
  assert.equal(headWords("infra", 3, 1, false, true, true).title, "infra — 3 sessions, 2 on the strip and 1 hidden; holds the tab you are reading; click to go back to the transcript; drag to reorder the groups");
  // ROUND 4: the open header the pane shows WITHOUT the tab being read still folds on its click (toggle-group), and its title
  // says so without "and see its sessions at a glance": the sessions are in the pane already, and the count beside it says
  // "shown below" (the round-3 words, sectionDoorTitle `shown`)
  assert.equal(headWords("infra", 3, 1, false, false, false, true).title, "infra — 3 sessions, 2 on the strip and 1 hidden; click to fold this group; drag to reorder the groups");
  assert.equal(headWords("archived", 1, 0, false, false, false, true).title, "archived — 1 session; click to fold this group; drag to reorder the groups");
  assert.doesNotMatch(headWords("infra", 3, 1, false, false, false, true).title, /at a glance/);
  assert.deepEqual([headWords("infra", 3, 1, false, false, false, true).count, headWords("infra", 3, 1, false, false, false, true).label],
                   [headWords("infra", 3, 1, false, false).count, headWords("infra", 3, 1, false, false).label], "shown: the count and the spoken label are as they were (the label carries no click clause)");
  assert.deepEqual(headWords("infra", 3, 1, false, true, true, true), headWords("infra", 3, 1, false, true, true), "shown and holding the tab being read: the way back's words, as before (back implies shown)");
  assert.deepEqual(headWords("infra", 3, 1, false, false, false, false), headWords("infra", 3, 1, false, false), "the default: the pane shows something else, the promise stands");
  // ...and the FOLDED header the pane shows (the header's click folded it and put its sessions in the pane): the click opens
  // it, and the title says that alone, without "and see its sessions at a glance"
  assert.equal(headWords("infra", 3, 3, true, false, false, true).title, "infra — 3 sessions folded; click to open this group");
  assert.equal(headWords("infra", 3, 3, true, true, false, true).title, "infra — 3 sessions folded; holds the tab you are reading; click to open this group");
  assert.equal(headWords("infra", 1, 0, true, false, false, true).title, "infra — folded, but its one session is set to show when folded, so none is hidden; click to open this group");
  assert.equal(headWords("infra", 2, 0, true, false, false, true).title, "infra — folded, but all 2 sessions are set to show when folded, so none is hidden; click to open this group");
  assert.deepEqual([headWords("infra", 3, 3, true, true, false, true).count, headWords("infra", 3, 3, true, true, false, true).label], [headWords("infra", 3, 3, true, true).count, headWords("infra", 3, 3, true, true).label], "folded, shown: the count and the spoken label as they were");
  assert.deepEqual(headWords("infra", 3, 3, true, false, false, false), headWords("infra", 3, 3, true, false), "folded, the pane elsewhere: the promise stands");
  for (const w of [headWords("infra", 3, 3, true, false, false, true), headWords("infra", 1, 0, true, false, false, true), headWords("infra", 3, 1, false, false, false, true)])
    assert.doesNotMatch(w.title, /at a glance/, w.title);
  assert.match(HEAD, /const words = headWords\(name, total, hidden\.length, collapsed, holdsActive, back, shown\);/, "the header passes the bit its own way back and the doors' act read");
  assert.equal(headWords("infra", 3, 2, true, false).count, "2", "folded: the folded-away members, a bare number, as before");
  // render.ts: the marks' block runs whenever the header stands in for a member (folded or open), over `hidden`, the pip
  // through standInPip with each member's ledger; the strip's signature reads the verdict, so the feed build that changes
  // it repaints the header
  assert.match(HEAD, /if \(hidden\.length\) \{\s*\n(?:\s*\/\/[^\n]*\n)*\s*const stand = standInPip\(hidden\.map\(\(id\) => \(\{ session: sessions\.get\(id\), ledger: ledgers\.get\(id\) \}\)\)\);/, "the pip over the stand-in set, open or folded, with the ledger");
  assert.match(TABS, /ledgers\.get\(id\)\?\.needsInput === true\];/, "the verdict is in the strip's signature (tab-strip-skip.test lists it)");
  assert.match(HEAD, /const flag = sectionTodoFlag\(hidden\.map\(\(id\) => sessions\.get\(id\)\)\);/, "the flag over the same set");
  assert.ok(!HEAD.includes("if (collapsed) {"), "no folded-only block: an open header with hidden members carries the marks too");
  assert.match(TABS, /collapsedTabIds = plan\.folded;\s*\n\s*lastStripItems = plan\.items;/, "the plan's headers, hides included, for setActive's unfold (read per holder: tab-groups.test, T264b)");
  // the strip's signature carries the plan's items whole (upstream's shape, T264b; the fork's explicit tuple of the same
  // fields was superseded at the 2026-09-09 fold), and a StripHead carries `hides` (tab-groups.ts planStrip), so a hide
  // flip changes the signature and the strip repaints
  assert.match(TABS, /activeId \? tabInView\(activeId\) : null, plan\.items,\n/, "the plan, hides included, is in the strip's signature (tab-strip-skip.test lists it)");
  assert.match(GROUPS, /export type StripHead = \{ head: TabSection; folded: boolean; active: boolean; hidden: string\[\]; hides: string\[\] \};/, "the item the signature serializes carries the hides");
  assert.notEqual(JSON.stringify(planStrip(ALL, unions, apiHidden, "web", false).items), JSON.stringify(planStrip(ALL, unions, d, "web", false).items), "a hide flip alone is a new signature");
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
  assert.match(SNAP, /hide: once\(\(node\) => setRowHidden\(node\.dataset\.id, true\)\),\s*\n\s*show: once\(\(node\) => setRowHidden\(node\.dataset\.id, false\)\),/, "explicit on and off, never a toggle of the stored bit; once per gesture (its own test below)");
  assert.match(SNAP, /"toggle-hidden": once\(\(\) => \{\s*\n\s*if \(!snapView\) return;\s*\n\s*if \(snapHiddenOpen\.has\(snapView\)\) snapHiddenOpen\.delete\(snapView\); else snapHiddenOpen\.add\(snapView\);\s*\n\s*const h = document\.getElementById\("tab-snapshot"\);\s*\n\s*if \(h && snapModel\) syncHiddenFold\(h, snapModel\);\s*\n\s*\}\) \}\);/,
    "the fold's head: view state of the section the pane shows, no store write, no strip render");
  assert.equal(SNAP.split("delegate(host").length - 1, 1, "one delegate, installed with the host");
  assert.doesNotMatch(SNAP.slice(SNAP.indexOf("function snapshotRowNode("), SNAP.indexOf("function showActive")), /addEventListener\("click"/, "no per-node click handler: the nodes are rebuilt");
  // the write: the pin row's prune site, with the section the pane shows, addressed as a pin addresses it
  assert.match(SNAP, /function setRowHidden\(id: string \| undefined, on: boolean\): void \{\s*\n\s*const head = snapView \? lastStripItems\.find\(\(it\): it is StripHead => "head" in it && it\.head\.name === snapView\) : undefined;\s*\n\s*if \(!id \|\| !head \|\| head\.head\.name === null\) return;\s*\n\s*writeTabGroupsPruned\(setHidden\(tabGroups\(\), head\.head, id, on\)\);\s*\n\}/);
  assert.equal(RENDER.split("prunePinned(").length - 1, 1, "one prune site (writeTabGroupsPruned), shared with the pin row");
  assert.match(RENDER, /function writeTabGroupsPruned\(st: TabGroupsState\): void \{\s*\n\s*writeTabGroups\(prunePinned\(st, viewTagUnion\(effViews\(\)\), knownTabIds\(\), reachableHosts\(\)\)\);/);
  assert.equal(RENDER.split("writeTabGroupsPruned(").length - 1, 4, "the definition, the pin row, the snapshot's write, the tab menu's Hide tab row (the menu door, below)");
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
  assert.match(SNAP, /fh\.setAttribute\("aria-expanded", open \? "true" : "false"\);/, "a disclosure to assistive tech");
  assert.match(SNAP, /fold\.style\.display = n \? "" : "none";/, "the fold shows only while something is hidden");
  assert.match(SNAP, /chip\.textContent = words\.needs;\s*\n\s*chip\.style\.display = words\.needs \? "" : "none";/, "the needs-you chip, only when a hidden member needs you");
  assert.match(SNAP, /^const snapHiddenOpen = new Set<string>\(\);/m, "closed by default, per section (its own test below): the head's count and chip say what is inside");
  // focus follows the toggled row: the same session's button in the other list (its Hide or Show when that held focus, its
  // row when the row did), or the fold's head when that list is folded away
  assert.match(SNAP, /const focusedId = focusedList \? focused!\.closest<HTMLElement>\("\.snap-item"\)!\.dataset\.id : undefined;/);
  assert.match(SNAP, /const focusedAct = !!focused && focused\.classList\.contains\("snap-act"\);/);
  assert.match(SNAP, /const same = focusedId !== undefined \? host\.querySelector<HTMLElement>\(`\.snap-item\[data-id="\$\{focusedId\}"\] \.\$\{focusedAct \? "snap-act" : "snap-row"\}`\) : null;/);
  assert.match(SNAP, /else if \(same\) \(snapHiddenOpen\.has\(next\.name\) \|\| !same\.closest\("\.snap-hidden-list"\) \? same : host\.querySelector<HTMLElement>\("\.snap-hidden-head"\)\)\?\.focus\(\);/);
  // the sync runs on every paint (after the reconcile) and on the head's click
  assert.match(SNAP, /reconcileRows<SnapRow, Element>\(hlist, hid, keyOf, [^\n]*\n\s*syncHiddenFold\(host, next\);/);
});

test("executed + pinned: a hidden session's needs-you is reachable. The fold's chip and its row say so; a pick shows the transcript with the header as stand-in and leaves the fold and the flag alone", () => {
  // the plan: api hidden and active. Its header is marked and stands in; nothing unfolds, since opening infra
  // would bring no tab on screen (the hide stands) and the pick named the session, not the group
  const { p, infra } = strip(apiHidden, "api");
  assert.deepEqual([infra.active, infra.folded, p.folded.has("api")], [true, false, true]);
  assert.match(RENDER, /if \(collapsedTabIds\.has\(id\)\) unfoldSectionOf\(id\);/, "setActive: the unfold is for a folded-away tab");
  assert.match(RENDER, /const holder = lastStripItems\.find\(\(it\) => "head" in it && it\.head\.name !== null && it\.folded && it\.head\.ids\.includes\(id\) && !it\.hides\.includes\(id\)\);/,
    "unfoldSectionOf opens a folded holder that does NOT hide the tab; api's only holder hides it, so nothing opens (per holder since T264b: tab-groups.test)");
  assert.doesNotMatch(RENDER, /hiddenTabIds/, "no union of every header's hides: a hide is per (tab, section)");
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
  const flat = para.replace(/\s+/g, " ");   // the pins read the words, not the wrap
  assert.match(flat, /Each row in this view has a \*\*Hide\*\* button, or \*\*Show\*\* once the session is hidden\./, "round 1: the first sentence had claimed a Hide on every row");
  assert.match(flat, /moves its row under a \*\*Hidden \(N\)\*\* fold at the foot of the view, one click away; the row's \*\*Show\*\* button puts the tab back at once\./);
  // THE MENU DOOR (the user 2026-09-09): the tab's right-click menu hides too; the paragraph says where the row is and is not
  assert.match(flat, /You can also hide a session from its tab: right-click the tab and pick \*\*Hide tab\*\*\. The line under the label names the group the session hides in and where to show it again: the group's view, where its row has the \*\*Show\*\* button\. Which click opens that view depends on the fold: an open group's count opens the view and leaves the group open; a folded group's header opens the group and the view together\. While the menu is open, the row follows the copy you right-clicked, through your edits in the \*\*Tags\*\* flyout and through changes that arrive from elsewhere \(another pane, another dashboard\)\. The menu knows the group by its tag's id, and by its name when no tag has that id: a tag renamed meanwhile keeps the row under its new name, and a tag removed and made again under the same name keeps it too\. Two kinds of group are known by name alone, a group that only another machine's tags make and a tag that was still being created when the menu started following the tab under it \(you typed its name into the \*\*Tags\*\* flyout while the tab had no group, or you right-clicked the tab while the tag's row under \*\*Tags\*\* said creating\): renamed while the session is under two or more groups, the row leaves, and a click writes nothing\. Moving it to another group changes the group the line names\. Removing that group's tag takes the row away, unless the session is left under exactly one other tag, whose group the line then names: under two or more, the menu cannot tell which copy you mean\. If the removed tag comes back \(a removal the kernel refused, or the tag added again from another pane\), the line names your group again, unless you added a tag from the flyout while the line named the one remaining group: that add keeps the line on that group, and the tag coming back does not move it\. While the row is away, adding a tag brings it back for that group, unless the copy's tag is still being created: an add then keeps the copy under the pending tag, and the row stays away until that tag exists\. A removal that leaves one tag brings it back for that one\. Removing one of the session's other tags leaves the line alone\./, "round 6: the group is known by its tag's id first and its name as the fallback (N7 and K8 execute it: a rename beside a remote union under the old name, a tag made again under the same name), the two name-only kinds are named (the remote-only group, N6; a tag still being created when the menu started following the tab, whether typed into the flyout while the tab had no group or right-clicked while its row said creating: round 7, N6b executes the right-clicked one, whose ref carries the placeholder id no tag has after the ack, so the name carries it), and the tag coming back does not move a line the user's own add aimed (P6c executes it); round 5: the tag coming back returns the line to the right-clicked copy (P6 executes it; round 4 latched the other holder), and the rename sentence carries the remote-only limit (N6 executes it: a group only another machine's tags make has no local id, so its rename on a two-holder session loses the row); round 1: the sub-line no longer promises a +1 (wrong with another member hidden) or an open group (a copy shown through a fold hides at once); round 2: the way back names the view and the guide gives the click per fold state (a folded header's click opens the group AND shows the view, so 'open the group and click its count' closed the view on its second step), and the line follows the copy through the flyout; round 3: the sentence states the rule the code runs (round 2's said the row went once the session was in no group, which the copy-scoped code never did), the one-holder return and the add included; round 4: an add under a tag still being created keeps the pending claim, so the row stays away until the tag exists (R5b executes it), and the row follows the copy through a views arrival too, a rename included (THE MENU FOLLOWS THE PUSH and A RENAME PUSHED WHILE THE MENU IS OPEN execute it), so the sentence is scoped to the open menu and not to the flyout");
  assert.doesNotMatch(flat, /While the \*\*Tags\*\* flyout is open, the row follows/, "round 4: the flyout is no longer the only path the row follows");
  assert.match(flat, /Removing one of the session's other tags leaves the line alone\. If the group changes under the menu just before you click, the click hides nothing\. While the tab is still in the group the line named, or has left it for exactly one other group, the line redraws for the group the tab is in now, the menu stays open, and a second click acts on what it says; when the words would not change \(the same group under a new tag\), the line flashes instead and its tooltip says to click again\. If the tab has left that group and is under none, or under two or more \(the menu cannot tell which copy you mean\), or the tabs were ungrouped from another pane, the menu closes and nothing is hidden\. The menu has \*\*Hide tab\*\* only while/, "round 5: the refused click is visible (the guard runs before the dismissal); round 6: the sentence covers the three outcomes the code has (a redraw while the tab resolves to one group, the flash when the words would not change, the dismissal under none, two or more, or the strip ungrouped elsewhere), as C3, C4, K4 and K8 execute them");
  assert.doesNotMatch(flat, /once the session is in no group, the row goes away/, "round 3: the sentence the code did not implement is gone");
  assert.match(flat, /The menu has \*\*Hide tab\*\* only while the tabs are grouped by tag and the tab is in a group, since nothing is hidden on the flat strip, on a phone, or for the untagged sessions after the divider\. A tag that is still being created \(its row under \*\*Tags\*\* says creating\) has no \*\*Hide tab\*\* yet; the row appears once the tag exists\. A hidden session has no tab to right-click, so this view's \*\*Show\*\* button puts it back\./, "round 1: the whole condition (the untagged sessions and the create in flight had no row and no sentence); round 3: the row appeared on the next open, since nothing in the open menu received the create's ack; round 4: the ack runs the open menu's views hook, so the row appears once the tag exists (N5 of the rename test executes it) and the next-open clause is gone");
  assert.doesNotMatch(flat, /it comes a moment later|the next time you open the menu/, "round 3: no promise the code does not keep; round 4: no wait the code no longer imposes");
  assert.match(flat, /fold the group and open it again, and the hidden sessions stay hidden while the rest come back\./);
  assert.match(flat, /The group's header keeps the dot and the ⚑ flag for its hidden sessions \(the dot is red when one of them needs you\), and its count shows two numbers, \*\*6\+2\*\* for six on the strip and two hidden \(the tooltip spells it out\)\./, "the compact count (headWords, compactCount; the user 2026-09-08: the words were too wide a head), and the dot reads the feed too (standInPip)");
  assert.match(flat, /the fold's head says so in red before you open it, and its row says \*\*needs you\*\*\./);
  assert.match(flat, /While the group is open, its count opens this view without folding the group, so hiding a session never needs a fold; the dot and the flag, which appear once something is hidden, do the same\. On a folded header the flag opens the group, as before\./, "the non-folding door, on every open header (round 2: the sentence had claimed the count for a door before the first hide, when it was a plain span)");
  assert.match(flat, /On a folded header the flag opens the group, as before\. While this view shows an open group, its count, dot and flag take you back to the transcript\. Clicking a hidden session's row/, "round 3: the count, the dot and the flag of the group the pane shows are the way back (the sentence on the header's second click, pinned by tab-snapshot.test, stands as it was); round 4: an OPEN group's (a folded group the view shows has no door: its count is a plain span and its flag opens the group)");
  assert.doesNotMatch(flat, /While this view shows a group, its count/, "round 4: the unqualified sentence promised the way back on a folded group's marks too");
  assert.match(flat, /Clicking a hidden session's row shows its transcript, with the header standing in for the tab, and leaves it hidden, its group folded or open as it was, unless the session has another tag whose group is folded and does not hide it: that group opens and the tab shows there, the hide standing where it was\./, "round 5: the pick's unfold is per holder (unfoldSectionOf), so another folded group of the session's tags opens for it");
  assert.match(flat, /the hide wins, and the setting resumes when you show it again\./);
  assert.match(flat, /keeps the setting when its group is renamed, and shows again wherever it lands when it leaves the group\./);
  assert.match(GUIDE.replace(/\s+/g, " "), /click one to open that session, which also opens its section if the section is folded \(with several tags, the first folded group of them that does not hide it; a section that hides the session stays as it was; see the next paragraph\)\./, "the older sentence about a pick opening the section is exact for hidden members now (round 1) and for several tags (round 5)");
  assert.ok(!para.includes("—"), "no em dash in the new guide text");
  assert.ok(!/fleet/i.test(para));
  const ref = REF.slice(REF.indexOf("### The tab strip's per-browser choices"), REF.indexOf("### Model and effort, from the statusline or a typed command")).replace(/\s+/g, " ");
  assert.match(ref, /`romp:tabgroups`, not on the kernel/);
  assert.match(ref, /which sessions are hidden inside their group \(\*\*Hide\*\*, in the section's at-a-glance view\)/, "the guide's name for the surface (round 1: \"the group view\" appeared nowhere else)");
  assert.doesNotMatch(REF, /group view/);
  assert.match(ref, /The tab's right-click menu writes the same hide entry: \*\*Hide tab\*\* on a shown copy, \*\*Show tab\*\* on a hidden one \(a hidden copy has no tab on the strip; the way back is the view's \*\*Show\*\*, and the group's count opens the view while the group is open\)\./, "the menu door (the user 2026-09-09); round 1: the way back names the click that reaches the view");
  assert.match(ref, /The row follows the copy the menu speaks for: the copy you right-clicked while its group holds the session, else the session's one remaining group, and none under two or more \(the copy is known by its tag's id, and by its name when no tag has that id, so a rename keeps it and so does a tag made again under the same name; a tag added from the flyout while the row named the one remaining group keeps the row on that group, even when the removed tag comes back\); that group's tag must already exist \(a tag still being created has no row until the kernel answers\), and the tabs must be grouped by tag\. On the flat strip, on the phone layout and for the untagged sessions after the divider, where hides do not apply, the menu has no such row; an untagged session gets the row once a tag added from the menu's \*\*Tags\*\* flyout gives it a group\./, "round 1: the whole condition the code enforces; round 3: the row waited for the next open; round 4: the ack re-dresses the open menu, so the row is there when the kernel answers, as the guide says; round 5: the general rule (the row follows the copy the menu speaks for, the one-holder case included, which 'present only while the right-clicked copy is in a group' left out) and the untagged session's add (R5); round 6: the identity rule (the id, then the name) and the add that aims the row, mirrored from the guide");
  assert.doesNotMatch(ref, /The row is present only while/, "round 5: the necessary-condition sentence the one-holder resolution broke is gone");
  assert.doesNotMatch(ref, /the menu is next opened/, "round 4: no next-open wait");
  assert.match(ref, /is dropped at the next pin or hide change once the session has left the group or closed; a fold or an open carries it as it is\./, "the prune rule as it is: the pin and hide writes prune, the fold writes do not (round 1)");
  assert.match(ref, /A key in the store that this build does not know is carried through its writes unchanged\./);
  assert.match(ref, /Folding or opening a group never changes which of its sessions are hidden\. A store written before hiding existed reads as nothing hidden\./);
  assert.ok(!ref.includes("—") && !/fleet/i.test(ref));
  // the sheet: the act button wears the small box and the one sub-line size; pattern A hover; the fold's head is
  // the heading's dress as a button; the caret turns with .open; tokens only, no raw color
  const block = CSS.slice(CSS.indexOf("/* HIDE AND SHOW"), CSS.indexOf(".snap-hidden-list {") + 60);
  assert.match(block, /\.snap-item \{ display: flex; align-items: flex-start; gap: 6px; \}/);
  assert.match(block, /\.snap-act \{[^}]*padding: var\(--btn-pad-sm\);[^}]*border-radius: var\(--radius-pill\);/);
  assert.match(block, /\.snap-act:hover \{ border-color: var\(--accent\); color: var\(--accent\); background: var\(--accent-wash\); \}/, "the one action hover");
  // PROGRESSIVE DISCLOSURE (round 1): the act rests unseen and shows on the item's hover or focus; opacity, never display,
  // so Tab reaches it and a reader hears it; always where hover is not a thing
  assert.match(block, /\n\.snap-act \{[^}]*cursor: pointer; opacity: 0;/, "the act rests unseen");
  assert.match(block, /\n\.snap-item:hover \.snap-act, \.snap-item:focus-within \.snap-act \{ opacity: 1; \}/, "shown on the item's hover and while anything in it has focus");
  // ROUND 3: any-pointer, not pointer. `pointer` and `hover` describe the PRIMARY pointing device, so a laptop with a trackpad and a
  // touchscreen reports pointer: fine and hover: hover and round 2's (pointer: coarse) never fired on the very device it named;
  // `any-pointer` is the union of the devices present. tab-hide-browser.test launches Chromium as that laptop and reads the opacity.
  assert.match(block, /\n@media \(hover: none\), \(any-pointer: coarse\) \{ \.snap-act \{ opacity: 1; \} \}/, "always where hover is not a thing, and wherever any pointing device is a finger (round 2: a resting act at opacity 0 still takes a tap; round 3: the primary-device feature missed the touchscreen laptop)");
  assert.doesNotMatch(block, /\(pointer: coarse\)/, "never the primary-device feature here: it is false on a trackpad-plus-touchscreen laptop");
  assert.equal(ui("webview", "feed.css").includes(".snap-act"), false, "the act has no twin in feed.css: the feed page has no section snapshot, so the mirror tests have nothing to hold equal here");
  assert.doesNotMatch(block, /\.snap-act[^{]*\{[^}]*display: none/, "never display: the keyboard path stands");
  assert.match(block, /\.snap-act:focus-visible \{ outline: 1px solid var\(--accent\); outline-offset: 1px; \}/);
  assert.match(block, /\.snap-hidden-head \{[^}]*font-size: 0\.82em; font-weight: 600; letter-spacing: 0\.04em;/, "the heading's dress");
  assert.match(block, /\.snap-hidden\.open \.tab-group-caret \{ transform: rotate\(90deg\); \}/);
  assert.deepEqual([...new Set(block.match(/font-size: [^;]+/g))], ["font-size: 0.82em"], "one sub-line size, the header's");
  assert.equal(block.replace(/\/\*[\s\S]*?\*\//g, "").match(/#[0-9a-fA-F]{3,8}\b/g), null, "no raw color: the light theme needs no override");
  // the fold's needs chip is the row's own red chip class
  assert.match(SNAP, /el\("span", "snap-flag needs snap-hidden-needs"\)/);
});

test("executed + pinned: THE NON-FOLDING DOOR (round 1). An open header's marks over its hidden members show the section in the pane and leave the fold alone; folded, the flag opens the group as before", () => {
  // the two mediums: the flag on an open header over a hidden member ran open-group, a write that opened a group already
  // open (nothing moved), and the pane, the one place to Hide or Show, sat behind the header's click, which folds the
  // group over its reader (a hide cost fold, Hide, open: three gestures and two strip moves). Now the open header's count
  // reads the compact "S+K" and is a button (the door a keyboard reaches), the pip and the flag act the same (show-group), and
  // the handler sets snapView and renders: no store write, so the fold stands. tab-hide-browser.test drives it in Chromium.
  assert.equal(SHOW_GROUP_CLICK, "click to show this group's sessions");
  // ROUND 2: the door's words LEAD WITH THE COUNT'S VISIBLE TEXT (headWords' count), so the name a voice control hears
  // contains the label it sees ("2+1", spelled out after it, or the total); with nothing hidden the click clause says what the pane is
  // for, since every session is on the strip already
  assert.equal(sectionDoorTitle(1, 3), "2+1: 2 on the strip and 1 hidden while this group is open; " + SHOW_GROUP_CLICK);
  assert.equal(sectionDoorTitle(2, 3), "1+2: 1 on the strip and 2 hidden while this group is open; " + SHOW_GROUP_CLICK);
  assert.equal(sectionDoorTitle(3, 3), "0+3: none on the strip and 3 hidden while this group is open; " + SHOW_GROUP_CLICK, "every member hidden");
  assert.equal(sectionDoorTitle(0, 3), "3 sessions; click to see them at a glance and hide any from the strip");
  assert.equal(sectionDoorTitle(0, 1), "1 session; click to see it at a glance and hide it from the strip");
  for (const [hid, total] of [[0, 1], [0, 3], [1, 3], [2, 3], [3, 3]] as const)
    assert.ok(sectionDoorTitle(hid, total).startsWith(headWords("infra", total, hid, false, false).count), `label in name: ${hid} of ${total}`);
  assert.equal(sectionTodoTitle({ count: 1, names: ["api"] }, true), "waiting on you — api flagged something it needs from you; " + SHOW_GROUP_CLICK, "the flag on an open header says what its click does there");
  assert.equal(sectionTodoTitle({ count: 1, names: ["api"] }), "waiting on you — api flagged something it needs from you; click to open this group", "and on a folded one, as before");
  // ROUND 2: the flag's PHRASE, apart from its click clause, is what the header's spoken label appends: the header's own
  // click folds the group or puts the transcript back, so a label ending in the door's instruction contradicted it
  assert.equal(sectionTodoPhrase({ count: 1, names: ["api"] }), "waiting on you — api flagged something it needs from you");
  assert.equal(sectionTodoPhrase({ count: 2, names: ["api", "tests"] }), "waiting on you — 2 sessions flagged something they need from you: api, tests");
  for (const door of [true, false]) assert.ok(sectionTodoTitle({ count: 1, names: ["api"] }, door).startsWith(sectionTodoPhrase({ count: 1, names: ["api"] }) + "; "), "the title is the phrase, then the click");
  assert.match(HEAD, /b\.title = sectionTodoTitle\(flag, door, shown\);\s*\n\s*b\.setAttribute\("aria-label", b\.title\);\s*\n(?:\s*\/\/[^\n]*\n)*\s*spoken \+= "; " \+ sectionTodoPhrase\(flag\);/, "the button keeps its click clause; the header's label takes the phrase alone");
  assert.doesNotMatch(HEAD, /spoken \+= "; " \+ b\.title;/);
  assert.equal(HEAD.split("SHOW_GROUP_CLICK").length - 1, 0, "no click phrase of its own in the header: the three doors take theirs from doorClick");
  assert.equal(HEAD.split("doorClick(shown)").length - 1, 1, "the click phrase reaches the header through the pip's title alone (the count's and the flag's come through their helpers); the label never carries it");
  // ROUND 3: THE WAY BACK on the door. While the pane already shows the section (snapView === name) the door's click changed
  // nothing (show-group over the same snapView) and its words still promised the pane; now it mirrors the header's second
  // click (headWords `back`): its act is show-transcript and its words say the sessions are shown below and the click goes
  // back to the transcript, in the header's own words (BACK_TO_TRANSCRIPT_CLICK), still led by the visible count
  assert.equal(BACK_TO_TRANSCRIPT_CLICK, "click to go back to the transcript");
  assert.equal(sectionDoorTitle(0, 3, true), "3 sessions, shown below; click to go back to the transcript");
  assert.equal(sectionDoorTitle(0, 1, true), "1 session, shown below; click to go back to the transcript");
  assert.equal(sectionDoorTitle(1, 3, true), "2+1: 2 on the strip and 1 hidden while this group is open; the group's sessions are shown below; click to go back to the transcript");
  assert.equal(sectionDoorTitle(3, 3, true), "0+3: none on the strip and 3 hidden while this group is open; the group's sessions are shown below; click to go back to the transcript");
  for (const [hid, total] of [[0, 1], [0, 3], [1, 3], [2, 3], [3, 3]] as const) {
    assert.ok(sectionDoorTitle(hid, total, true).startsWith(headWords("infra", total, hid, false, false).count), `label in name, shown: ${hid} of ${total}`);
    assert.ok(sectionDoorTitle(hid, total, true).endsWith("; " + BACK_TO_TRANSCRIPT_CLICK), `the way back, shown: ${hid} of ${total}`);
    assert.doesNotMatch(sectionDoorTitle(hid, total, true), /click to see|click to show/, "no promise of the pane while it is up");
  }
  assert.ok(headWords("infra", 3, 0, false, true, true).title.includes("; " + BACK_TO_TRANSCRIPT_CLICK + "; "), "the header's second click says it in the same words");
  assert.equal(sectionDoorTitle(0, 3, false), sectionDoorTitle(0, 3), "every other state is as it was");
  // ...and the pip and the flag with it (the coordinator's ruling after round 3): one clause for the three doors, from doorClick
  assert.equal(doorClick(false), SHOW_GROUP_CLICK);
  assert.equal(doorClick(true), BACK_TO_TRANSCRIPT_CLICK);
  assert.equal(sectionTodoTitle({ count: 1, names: ["api"] }, true, true), sectionTodoPhrase({ count: 1, names: ["api"] }) + "; " + BACK_TO_TRANSCRIPT_CLICK, "the flag, shown: the who phrase, then the way back");
  assert.equal(sectionTodoTitle({ count: 1, names: ["api"] }, true, false), sectionTodoTitle({ count: 1, names: ["api"] }, true), "not shown: as it was");
  assert.equal(sectionTodoTitle({ count: 1, names: ["api"] }, false, true), sectionTodoPhrase({ count: 1, names: ["api"] }) + "; click to open this group", "folded: opens the group whatever the pane shows (round 4: a folded header the pane shows renders this; the header's title says the same clause)");
  assert.match(ui("webview", "tab-state.ts"), /export function doorClick\(shown: boolean\): string \{\s*\n\s*return shown \? BACK_TO_TRANSCRIPT_CLICK : SHOW_GROUP_CLICK;\s*\n\}/);
  assert.match(ui("webview", "tab-state.ts"), /return `\$\{lead\}; \$\{doorClick\(true\)\}`;/);
  assert.match(ui("webview", "tab-state.ts"), /\$\{door \? doorClick\(shown\) : "click to open this group"\}/);
  assert.match(HEAD, /pip\.title = door \? `\$\{said\}; \$\{doorClick\(shown\)\}` : said;\s*\n\s*if \(door\) \{ pip\.dataset\.act = doorAct; pip\.dataset\.group = name; \}/, "the pip: the doors' clause and act");
  assert.match(HEAD, /b\.dataset\.act = door \? doorAct : "open-group";\s*\n\s*b\.dataset\.group = name;\s*\n\s*b\.title = sectionTodoTitle\(flag, door, shown\);/, "the flag: the doors' act open, open-group folded; its title from the helper with the same bit");
  // the header: the door is EVERY open header's count (round 2: it existed only over hidden members, so the first hide of a
  // group still went through the header's click, which folds the group over its reader); folded, a plain span. Shown, the
  // way back (round 3), derived from the rendered state as the header's own way back is; the fold untouched either way
  assert.match(HEAD, /const door = !collapsed;\s*\n\s*const doorAct = shown \? "show-transcript" : "show-group";\s*\n\s*const n = door \? document\.createElement\("button"\) : el\("span", "tab-group-count"\);/, "the count is a button on an open header, a span on a folded one; shown, the way back; one act for the three doors");
  assert.match(HEAD, /n\.className = "tab-group-count tab-group-door";\s*\n\s*n\.dataset\.act = doorAct;\s*\n\s*n\.dataset\.group = name;\s*\n\s*n\.title = sectionDoorTitle\(hidden\.length, total, shown\);\s*\n\s*n\.setAttribute\("aria-label", n\.title\);/, "its own act (the way back while the pane shows the section), words (the visible count first) and spoken label");
  assert.equal(HEAD.replace(/\/\/[^\n]*/g, "").split("doorAct").length - 1, 4, "declared once, used by the count, the pip and the flag (the comments aside)");
  assert.match(HEAD, /const shown = snapView === name;\s*\n\s*if \(shown\) head\.classList\.add\("snap-shown"\);/, "one bit, the pane on this section whatever the fold (round 4: declared once, with the header's mark)");
  assert.match(HEAD, /const back = shown && !collapsed && holdsActive;\s*\n\s*if \(back\) head\.dataset\.act = "show-transcript";/, "the header's way back adds open and holdsActive (without holdsActive: another section's header still folds on its own click, its door did nothing); the doors' act and the header's words take the bit as it is");
  assert.equal(HEAD.split("snapView === name").length - 1, 1, "one rendered state, read once");
  assert.equal(HEAD.replace(/\/\/[^\n]*/g, "").replace(/"snap-shown"/g, "").split("shown").length - 1, 8, "declared once; read by the mark, the header's way back, its words, the doors' act, the count's title, the pip's clause and the flag's title (the comments and the snap-shown class string aside)");
  assert.match(HEAD, /n\.draggable = true;\s*\n\s*n\.addEventListener\("dragstart", \(e\) => \{ e\.preventDefault\(\); e\.stopPropagation\(\); \}\);/, "a press on it never starts the header's drag (the flag's rule)");
  assert.match(HEAD, /if \(door\) \{ pip\.dataset\.act = doorAct; pip\.dataset\.group = name; \}/, "the pip too, pointer only");
  assert.match(HEAD, /b\.dataset\.act = door \? doorAct : "open-group";/, "the flag: the doors' act open, open-group folded");
  assert.match(HEAD, /closest\("\.tab-group-flag, \.tab-group-door"\)\) return;/, "the header's key handler stands down for the door as for the flag: Enter and Space are the button's own click");
  // the delegate: snapView, a strip render for the header's mark, the pane; NO write (a fold is the header's own click)
  const DOOR = RENDER.slice(RENDER.indexOf('"show-group": (el) => {'), RENDER.indexOf('"open-group": (el) => {'));
  assert.match(DOOR, /^"show-group": \(el\) => \{\s*\n\s*const name = el\.dataset\.group;\s*\n\s*if \(!name\) return;\s*\n\s*snapView = name;\s*\n\s*renderTabs\(\);\s*\n\s*showActive\(\);\s*\n\s*\},/);
  assert.doesNotMatch(DOOR, /writeTabGroups|setSectionCollapsed|setHidden/, "no store write: the fold is untouched");
  assert.ok(RENDER.indexOf('"show-transcript": () => leaveSnapshot(),') < RENDER.indexOf('"show-group": (el) => {') && RENDER.indexOf('"show-group": (el) => {') < RENDER.indexOf('"open-group": (el) => {'), "on the #tabs delegate beside the header's acts");
  assert.equal((RENDER.match(/writeTabGroups\(setSectionCollapsed\(tabGroups\(\)/g) || []).length, 3, "the fold writes are still the three (tab-groups.test)");
  // the strip's focus restore puts a keyboard user back on the rebuilt door, as on the flag
  assert.match(TABS, /const focusedDoor = !!focusedEl\?\.classList\.contains\("tab-group-door"\);/);
  assert.match(RENDER, /\|\| \(focusedDoor && h\.querySelector<HTMLElement>\("\.tab-group-door"\)\) \|\| h\)\.focus\(\);/);
  // the sheet: the count's dress as a button, the flag's hover and ring, tokens only (tab-groups.test checks the tokens)
  assert.match(CSS, /\n\.tab-group-door \{ margin: 0; padding: 1px 3px; border: 0; border-radius: 3px; background: none; color: inherit; font: inherit; letter-spacing: inherit; line-height: 1; cursor: pointer; \}/);
  assert.match(CSS, /\n\.tab-group-door:hover \{ background: var\(--accent-wash\); opacity: 1; \}/);
  assert.match(CSS, /\n\.tab-group-door:focus-visible \{ outline: 1px solid var\(--accent\); outline-offset: 1px; opacity: 1; \}/);
  // executed: the plan the door leaves as it is. Hide and Show with the section open never touch the fold, and a Show
  // puts the tab back on the strip in the write's own render
  const open = strip(apiHidden);
  assert.deepEqual([open.infra.folded, open.tabs], [false, ["web", "tests", "loose"]]);
  const shown = setHidden(apiHidden, INFRA, "api", false);
  assert.deepEqual([strip(shown).infra.folded, strip(shown).tabs, shown.collapsed, shown.expanded], [false, ["web", "api", "tests", "loose"], [], []], "Show: the tab is back at once, the fold untouched");
});

// ── THE MENU DOOR (the user 2026-09-09) ──────────────────────────────────────────────────────────────────────────────────
// A hide from the tab's right-click menu, with neither the pane nor the Sessions and tags dialog open. This reverses the
// ruling that the pane was the one door (the tabhide design, 2026-09-08). showTabMenu ITSELF runs here: transpiled from
// render.ts with esbuild when the test runs (the chat-exact-tail-exec idiom) over a stand-in for the page, which is fake
// elements recording their class, words, children and listeners, the real store and unions, and recorders for the writes
// the menu makes; the row's presence, place, words and write are read off the menu the real code built. A slice that stops
// compiling against the stand-in fails loudly here (a ReferenceError), which is the point.
const requireCjs = createRequire(__filename);
class FakeEl {
  tag: string; className: string; children: FakeEl[] = []; parent: FakeEl | null = null;
  textContent = ""; innerHTML = ""; title = ""; type = ""; placeholder = ""; maxLength = 0; value = ""; id = "";
  style: Record<string, string> = {}; dataset: Record<string, string> = {}; attrs: Record<string, string> = {};
  listeners: Record<string, Array<(ev: unknown) => void>> = {};
  constructor(tag: string, cls = "") { this.tag = tag; this.className = cls; }
  appendChild(c: FakeEl) { this.children.push(c); c.parent = this; return c; }
  append(...cs: FakeEl[]) { for (const c of cs) this.appendChild(c); }
  replaceChildren(...cs: FakeEl[]) { this.children = []; this.append(...cs); }
  remove() { if (this.parent) this.parent.children = this.parent.children.filter((c) => c !== this); this.parent = null; }
  get firstChild(): FakeEl | null { return this.children[0] ?? null; }
  insertBefore(n: FakeEl, ref: FakeEl | null) { if (!ref) return this.appendChild(n); const at = this.children.indexOf(ref); this.children.splice(at, 0, n); n.parent = this; return n; }
  /** an input's selection (round 5): the fields a browser keeps on the element, so a node that is never moved keeps them */
  selectionStart = 0; selectionEnd = 0; selectionDirection = "none";
  setSelectionRange(a: number, b: number, dir = "none") { this.selectionStart = a; this.selectionEnd = b; this.selectionDirection = dir; }
  get parentNode(): FakeEl | null { return this.parent; }
  after(...cs: FakeEl[]) { const p = this.parent!; const at = p.children.indexOf(this); p.children.splice(at + 1, 0, ...cs); for (const c of cs) c.parent = p; }
  addEventListener(k: string, fn: (ev: unknown) => void) { (this.listeners[k] ||= []).push(fn); }
  fire(k: string, ev: unknown = {}) { for (const fn of this.listeners[k] || []) fn(ev); }
  setAttribute(k: string, v: string) { this.attrs[k] = v; }
  /** THE RECT MODEL (round 3): a menu or a flyout (.ctx-menu) stands where its style put it and is as tall as its rows, one ROW each
   *  (a flyout is a child of the menu but position: fixed, so it is not one of the menu's rows); a row's rect is its slot under the
   *  menu's top; anything else a fixed small box. Enough for the seat and the flyout's placement to be executed, not pinned */
  static ROW = 30;
  rows(): FakeEl[] { return this.children.filter((c) => !c.has("ctx-sub")); }
  getBoundingClientRect(): { left: number; top: number; right: number; bottom: number; width: number; height: number } {
    const num = (v: string | undefined) => parseFloat(v || "0") || 0;
    if (this.has("ctx-menu")) {
      const width = this.has("ctx-sub") ? 200 : 300, height = this.rows().length * FakeEl.ROW, left = num(this.style.left), top = num(this.style.top);
      return { left, top, right: left + width, bottom: top + height, width, height };
    }
    if (this.parent && this.parent.has("ctx-menu")) {
      const pr = this.parent.getBoundingClientRect(), i = this.parent.rows().indexOf(this);
      return { left: pr.left, top: pr.top + i * FakeEl.ROW, right: pr.right, bottom: pr.top + (i + 1) * FakeEl.ROW, width: pr.width, height: FakeEl.ROW };
    }
    return { left: 0, top: 0, right: 120, bottom: 20, width: 120, height: 20 };
  }
  get isConnected(): boolean { let n: FakeEl | null = this; while (n) { if (n.tag === "body") return true; n = n.parent; } return false; }
  querySelector(): FakeEl | null { return null; }
  /** the page's focus, as the prelude's document.activeElement reads it (round 5: the focus carry is executed, not source-pinned) */
  static focused: FakeEl | null = null;
  static focusCalls = 0;
  focus() { FakeEl.focused = this; FakeEl.focusCalls++; }
  has(cls: string) { return this.className.split(/\s+/).includes(cls); }
  get classList() { return { contains: (c: string) => this.has(c), add: (c: string) => { if (!this.has(c)) this.className += " " + c; }, remove: (c: string) => { this.className = this.className.split(/\s+/).filter((k) => k && k !== c).join(" "); }, toggle: () => {} }; }
  click() { const ev = { stopPropagation() {} }; for (const fn of this.listeners.click || []) fn(ev); }
  /** every descendant, depth first, self included */
  all(): FakeEl[] { return [this, ...this.children.flatMap((c) => c.all())]; }
  label() { return this.all().find((n) => n.has("ctx-item-label"))?.textContent; }
  sub() { return this.all().find((n) => n.has("ctx-item-sub"))?.textContent; }
  icon() { return this.all().find((n) => n.has("ctx-icon")); }
}
type MenuHooks = { views: unknown; known: string[]; sessions: Map<string, unknown>; writes: TabGroupsState[]; dismissed: number; renders: number; flags: Array<[string, string, boolean]>; mods: Record<string, unknown>; phone?: boolean; win?: { w: number; h: number }; window?: FakeWin; onRender?: () => void };
/** the page's window as pressHold and the seat read it (round 5): the pane's size, the release listeners a press installs, and `fire` for the release events */
class FakeWin {
  constructor(private size: () => { w: number; h: number }) {}
  get innerWidth() { return this.size().w; }
  get innerHeight() { return this.size().h; }
  setTimeout() { return 0; }
  clearTimeout() {}
  listeners: Record<string, Array<(ev: unknown) => void>> = {};
  addEventListener(k: string, fn: (ev: unknown) => void) { (this.listeners[k] ||= []).push(fn); }
  removeEventListener(k: string, fn: (ev: unknown) => void) { this.listeners[k] = (this.listeners[k] || []).filter((f) => f !== fn); }
  fire(k: string, ev: unknown = {}) { for (const fn of (this.listeners[k] || []).slice()) fn(ev); }
  count(k: string) { return (this.listeners[k] || []).length; }
  /** the phone media rule as render.ts installs its change listener on it (round 6): the listener is kept under "media:change", so a test
   *  flips the harness's phone flag and fires it, the way a rotation does; `matches` is not read here (showTabMenu reads phoneLayout) */
  matchMedia(_query: string) { return { matches: false, addEventListener: (k: string, fn: (ev: unknown) => void) => this.addEventListener("media:" + k, fn) }; }
}
/** a tick, for pressHold's zero timer at the release */
const tick = () => new Promise<void>((r) => setTimeout(r, 2));
type MenuApi = { open: (id: string, copy?: string, at?: { x: number; y: number }) => FakeEl; at: () => { x: number; y: number } | null; push: (views: unknown) => void; changed: () => void };
function liftShowTabMenu(): (hooks: MenuHooks) => MenuApi {
  const lifted = liftShowTabMenuRaw();
  // the page's window and the real pressHold bound to it (render.ts calls pressHold(menu) with the default release, the window)
  return (hooks) => {
    hooks.window ??= new FakeWin(() => hooks.win ?? { w: 1200, h: 800 });
    hooks.mods = { ...hooks.mods, pressHold: (surface: EventTarget) => pressHold(surface, hooks.window as unknown as EventTarget), TABGROUPS_KEY, TABGROUPS_EVENT };
    return lifted(hooks);
  };
}
function liftShowTabMenuRaw(): (hooks: MenuHooks) => MenuApi {
  const a = RENDER.indexOf("function showTabMenu(e: MouseEvent, id: string, copy?: string) {");
  const end = RENDER.indexOf("seatMenu(e.clientX, e.clientY);", a);
  const b = RENDER.indexOf("\n}\n", end) + 3;
  assert.ok(a > 0 && end > a && b > end, "showTabMenu's anchors moved; re-anchor this lift");
  // THE LISTENERS ARE REAL (round 6): the two tab-groups store listeners and the phone media rule's change listener, lifted verbatim with
  // the notifier they call (viewsChanged), are evaluated against the harness window (FakeWin records them and fires them), so a test that
  // fires a storage event, TABGROUPS_EVENT or the media flip drives render.ts's own wiring. Round 5's harness called the hook itself
  // (`changed`), so the store cases passed against a render.ts whose listeners never called the notifier
  const la = RENDER.indexOf('window.addEventListener("storage", (e) => { if (e.key === TABGROUPS_KEY)');
  const lb = RENDER.indexOf("\n", RENDER.indexOf('matchMedia(PHONE_LAYOUT_MEDIA).addEventListener("change"', la)) + 1;
  const notifier = RENDER.match(/\nfunction viewsChanged\(\) \{ tabMenuViewsHook\(\); \}\n/);
  const media = RENDER.match(/const PHONE_LAYOUT_MEDIA = "([^"]+)";/);
  assert.ok(la > 0 && lb > la && notifier && media, "the listeners', the notifier's or the media rule's anchor moved; re-anchor this lift");
  const js = requireCjs("esbuild").transformSync(RENDER.slice(a, b) + RENDER.slice(la, lb) + notifier![0], { loader: "ts" }).code;
  // the page as showTabMenu reads it: the maps and helpers named as render.ts names them
  const prelude = `
    const H = HOOKS;
    const { FakeEl, viewTagUnion, readTabGroups, writeTabGroups, prunePinned, sectionRef, isPinned, setPinned, isHidden, setHidden, pressHold, TABGROUPS_KEY, TABGROUPS_EVENT } = H.mods;
    const PHONE_LAYOUT_MEDIA = ${JSON.stringify(media![1])};
    const el = (tag, cls) => new FakeEl(tag, cls);
    const ctxIcon = (kind, off) => { const sp = new FakeEl("span", "ctx-icon" + (off ? " off" : "")); sp.dataset.kind = kind; return sp; };
    const sessions = H.sessions, tabMeta = new Map();
    const paletteColors = [];
    const dismissTabMenu = () => { H.dismissed++; ctxMenuEl?.remove(); ctxMenuEl = null; tagsFlyNewInput = null; tabMenuViewsHook = () => {}; };   // as render.ts's (pinned in the menu door test): the menu leaves the page, the input and the views hook are cleared (round 5: a stub that left the menu on the page let C4 read a re-dress the page had discarded)
    const closeEmojiPrompt = () => {};
    const setSessionFlag = (id, k, v) => { H.flags.push([id, k, v]); };
    const setSessionColor = () => {}, startTabRename = () => {}, showMovePrompt = () => {}, showEmojiPrompt = () => {};
    const billingSubText = () => "";
    const vscodeApi = null;
    let pendingSessionViews = null, tagsFlyNewInput = null, tabMenuViewsHook = () => {};   // the open menu's views hook (round 4): showTabMenu sets it, the arrival paths call it
    const renderTabs = () => { H.renders++; if (H.onRender) H.onRender(); };   // onRender: a test's probe of what the strip's render sees (round 6: the pin row's words before the hook that the same listener runs next)
    // the flyout's edits post an optimistic blob the real postTagEdit holds (holdViews) and effViews reads back: held here the same way
    const postTagEdit = (nv) => { H.views = nv; }, syncNewTagInput = () => {}, createInFlight = () => false, viewsWrites = [];
    const viewTags = (v) => (v && v.tags) || [];
    const effViews = () => H.views;
    const phoneLayout = () => !!H.phone;   // the page's media rule, as the tests stub it
    const knownTabIds = () => new Set(H.known);
    const reachableHosts = () => new Set();
    function tabGroups() { return readTabGroups(viewTagUnion(effViews())); }
    function writeTabGroupsPruned(st) { const out = prunePinned(st, viewTagUnion(effViews()), knownTabIds(), reachableHosts()); H.writes.push(out); writeTabGroups(out); }
    const browseRouteNow = () => "pane", openBrowse = () => {};
    const location = { protocol: "vscode-webview:" };
    const window = H.window;   // the pane's size, and the release target pressHold installs its listeners on
    const document = { body: new FakeEl("body"), getElementById: () => null, get activeElement() { return FakeEl.focused; } };
    let ctxMenuEl = null, ctxMenuAt = null;
  `;
  const epilogue = `
    return { open: (id, copy, at) => { showTabMenu({ clientX: at ? at.x : 10, clientY: at ? at.y : 10 }, id, copy); return ctxMenuEl; }, at: () => ctxMenuAt,
             // a views arrival as the tabOrder frame handler and onViewsAck make it: the blob held (captureViews / takeViews, which effViews reads), then the
             // notifier (viewsChanged, which runs the hook); 'changed' is the notifier alone, as onKernelCaps runs it after a revert already made (round 5);
             // the store listeners and the media rule's are the module's own, on the harness window (round 6): a test fires the event instead
             push: (views) => { H.views = views; viewsChanged(); }, changed: () => { viewsChanged(); } };
  `;
  return new Function("HOOKS", prelude + js + epilogue) as (hooks: MenuHooks) => MenuApi;
}
/** the Hide tab row's sub-line for a shown copy (round 2: short, and true for an open group, a folded one and a copy shown through the fold alike) */
const HIDE_SUB = (g: string) => `hidden in ${g}; to show it, open the group's view`;
/** the store the menu reads and writes, as the earlier tests stub it */
function withStore<T>(fn: (store: Map<string, string>) => T): T {
  const store = new Map<string, string>();
  const g: any = globalThis;
  const savedLS = g.localStorage;
  g.localStorage = { getItem: (k: string) => store.get(k) ?? null, setItem: (k: string, v: string) => { store.set(k, v); } };
  try { return fn(store); } finally { g.localStorage = savedLS; }
}

test("executed: THE MENU DOOR. Hide tab sits with the toggles after Notify me, names the copy's group, hides in THAT section on a click and dismisses; the label reads Show tab once hidden; the row is absent off the grouped strip", () => {
  const hooks: MenuHooks = {
    views: V, known: ALL,
    sessions: new Map<string, unknown>([["web", { name: "web", status: { state: "ready" } }], ["api", { name: "api", status: { state: "working" } }], ["loose", { name: "loose", status: { state: "ready" } }]]),
    writes: [], dismissed: 0, renders: 0, flags: [],
    mods: { FakeEl, viewTagUnion, readTabGroups, writeTabGroups, prunePinned, sectionRef, isPinned, setPinned, isHidden, setHidden },
  };
  withStore(() => {
    const api = liftShowTabMenu()(hooks);
    const rowOf = (menu: FakeEl) => menu.children.find((it) => it.has("ctx-item-hide"));
    // S1: grouping on (a fresh store), web in infra, the menu opened on its infra copy: the row, its words, its glyph
    let menu = api.open("web", "infra");
    let row = rowOf(menu);
    assert.ok(row, "the row exists on the grouped strip");
    assert.equal(row!.label(), "Hide tab");
    assert.equal(row!.sub(), HIDE_SUB("infra"), "the sub-line names the group and the way back (round 1: no +1, which another hidden member falsifies, and no fold state, which a copy shown through a fold falsifies; round 2: the way back is the group's view, since the click that opens it differs by fold state, and the guide gives both)");
    assert.deepEqual([row!.icon()!.dataset.kind, row!.icon()!.has("off")], ["tab", false], "the tab glyph, unslashed while the tab shows");
    assert.equal(row!.title, HIDE_SUB("infra"), "the whole sentence as the row's tooltip (round 5: the sub-line elides at long names, and its instruction went with it)");
    assert.equal(menu.children.find((it) => it.has("ctx-item-tags"))!.title, "infra", "the Tags row's tooltip is its list");
    assert.ok(row!.has("ctx-item") && row!.has("ctx-item-toggle"), "the toggles' dress");
    // its place: directly after Notify me, before Billing and Tags, no divider added inside the behaviour section
    const items = menu.children;
    const at = (pred: (it: FakeEl) => boolean) => items.findIndex(pred);
    const feedAt = at((it) => it.label() === "Hide from feed"), bellAt = at((it) => it.label() === "Notify me"), hideAt = at((it) => it.has("ctx-item-hide")), tagsAt = at((it) => it.has("ctx-item-tags"));
    assert.ok(feedAt > 0 && bellAt > feedAt && tagsAt > bellAt, "the toggles then Tags, as before");
    assert.equal(hideAt, bellAt + 1, "directly after Notify me");
    assert.ok(hideAt < tagsAt);
    assert.ok(!items.slice(feedAt, tagsAt).some((it) => it.has("ctx-sep")), "no divider between the first toggle and Tags: one behaviour section (tab-tags.test pins the source)");
    // S2: the click: one write through the prune site, this section's entry in the pin's shape, the fold and the pins untouched,
    // the menu dismissed, no strip render of its own (TABGROUPS_EVENT repaints it, the write's own path) and no session flag
    const d0 = hooks.dismissed;   // showTabMenu dismisses any earlier menu as it opens; the click's own dismissal is the one counted
    row!.click();
    assert.equal(hooks.dismissed, d0 + 1, "the click dismisses the menu");
    assert.equal(hooks.writes.length, 1);
    assert.deepEqual(hooks.writes[0].hidden, [{ sid: "web", name: "infra", id: "g1" }]);
    assert.equal(isHidden(hooks.writes[0], INFRA, "web"), true);
    assert.deepEqual([hooks.writes[0].collapsed, hooks.writes[0].pinned, hooks.writes[0].on], [[], [], true]);
    assert.deepEqual([hooks.renders, hooks.flags], [0, []]);
    // the strip's own path reads what the click wrote: web off the strip while infra is open, the header standing in
    const after = strip(readTabGroups(unions));
    assert.deepEqual([after.tabs, after.infra.hides, after.infra.folded], [["api", "tests", "loose"], ["web"], false]);
    // S3: the label reads the stored state. The same menu on the hidden copy reads Show tab (the strip shows no such tab today;
    // the words are true wherever the menu opens), the glyph slashed, and its click shows: an explicit off, never a toggle of
    // whatever a later render stored
    menu = api.open("web", "infra");
    row = rowOf(menu);
    assert.equal(row!.label(), "Show tab");
    assert.equal(row!.sub(), "back on the strip in infra");
    assert.equal(row!.icon()!.has("off"), true);
    const d1 = hooks.dismissed;
    row!.click();
    assert.equal(hooks.writes.length, 2);
    assert.deepEqual(hooks.writes[1].hidden, []);
    assert.deepEqual(strip(readTabGroups(unions)).tabs, ["web", "api", "tests", "loose"], "back at once");
    assert.equal(hooks.dismissed, d1 + 1);
    // S4: a session under two tags (T264b) has a copy in each group, and the menu speaks for the copy it opened from: api in infra
    // and archived, opened on the archived copy, hides under archived alone; on the infra copy, under infra; with no copy named
    // (an older caller): the one remaining holder, else none under two or more (round 3)
    const V2 = { ...V, tags: [V.tags[0], { ...V.tags[1], members: ["old1", "old2", "api"] }], seq: 4 };
    hooks.views = V2;
    const ARCHIVED: SectionRef = { name: "archived", localId: "g2" };
    menu = api.open("api", "archived");
    assert.equal(rowOf(menu)!.sub(), HIDE_SUB("archived"), "the copy's own group");
    rowOf(menu)!.click();
    assert.deepEqual(hooks.writes[2].hidden, [{ sid: "api", name: "archived", id: "g2" }], "THAT copy's section, not the first holder's");
    assert.deepEqual([isHidden(hooks.writes[2], ARCHIVED, "api"), isHidden(hooks.writes[2], INFRA, "api")], [true, false]);
    const u2 = viewTagUnion(V2);
    const open2 = strip(setSectionCollapsed(readTabGroups(u2), "archived", false), "web", ALL, u2);
    assert.deepEqual(open2.tabs, ["web", "api", "tests", "old1", "old2", "loose"], "api's infra copy is on the strip; archived, open, shows it as +1");
    assert.deepEqual(heads(open2.p.items).find((h) => h.head.name === "archived")!.hides, ["api"]);
    menu = api.open("api", "infra");
    assert.equal(rowOf(menu)!.label(), "Hide tab", "the infra copy is shown: its row hides");
    assert.equal(rowOf(menu)!.sub(), HIDE_SUB("infra"));
    rowOf(menu)!.click();
    assert.deepEqual(hooks.writes[3].hidden, [{ sid: "api", name: "archived", id: "g2" }, { sid: "api", name: "infra", id: "g1" }], "one entry per section, the other left standing");
    menu = api.open("api");
    assert.equal(rowOf(menu), undefined, "no copy named, two holders: which copy? none (round 3; round 2 fell to the first holder in tagOrder, a copy the user never touched)");
    hooks.views = V;
    menu = api.open("api");
    assert.equal(rowOf(menu)!.label(), "Show tab", "no copy named, one holder: that copy, unambiguous (infra, where api is hidden now)");
    assert.equal(rowOf(menu)!.sub(), "back on the strip in infra");
    hooks.views = V2;
    // S5: ABSENT where hides do not apply. Group tabs by tag off: no row, the other toggles as before; a session under no tag:
    // no home section, no row; a copy whose tag's create is still in flight (a pending union): no id to address, no row
    hooks.views = V;
    writeTabGroups({ ...readTabGroups(unions), on: false });
    menu = api.open("web", "infra");
    assert.equal(rowOf(menu), undefined, "the flat strip hides nothing: no row");
    assert.ok(menu.children.some((it) => it.label() === "Hide from feed") && menu.children.some((it) => it.has("ctx-item-tags")), "the rest of the menu stands");
    writeTabGroups({ ...readTabGroups(unions), on: true });
    menu = api.open("loose");
    assert.equal(rowOf(menu), undefined, "no tag, no group to hide in");
    assert.ok(rowOf(api.open("web", "infra")), "and back on the grouped strip the row is back");
    hooks.views = { ...V, tags: [...V.tags, { id: "pending-k1", name: "draft", color: "#7aa2f7", members: ["web"] }], seq: 5 };
    menu = api.open("web", "draft");
    assert.equal(rowOf(menu), undefined, "a home whose create is in flight: no row (no id to address, as the flyout's Move-to rows read it)");
    assert.equal(hooks.writes.length, 4, "no write from any of the absent cases");
    // S6 (round 6): THE FLYOUT'S ROWS CARRY THEIR TEXT AS TOOLTIPS. A 40-character destination elides at the flyout's per-row cap
    // (tab-hide-browser measures it) and was readable nowhere in the menu: the held name and the home read through the Hide tab and
    // Tags rows' titles, a destination through nothing. Each Move to and + row carries its label, each held row its name (the
    // creating row too), the pin row its sentence; the ✕ and the + keep their own titles, and the innermost wins on hover
    const long40 = "notes-api-customer-billing-migration-two";
    assert.equal(long40.length, 40, "the New tag input's maximum");
    hooks.views = { ...V, tags: [...V.tags, { id: "g8", name: long40, color: "#7aa2f7", members: [] as string[] }, { id: "pending-k2", name: "draft", color: "#f0f", members: ["web"] }], seq: 6 };
    menu = api.open("web", "infra");
    let fly = flyOf(menu);
    const titled = (label: string) => { const r = fly.children.find((it) => it.label() === label); assert.ok(r, "the row " + label); return r!; };
    assert.equal(titled("infra").title, "infra", "a held row's title is its name");
    assert.equal(titled("draft").title, "draft", "the creating row's too (set before the pending branch)");
    assert.equal(titled("Move to archived").title, "Move to archived", "a Move to row's title is its label");
    assert.equal(titled("Move to " + long40).title, "Move to " + long40, "the 40-character destination, whole, in the tooltip (round 5: no title, the label elided)");
    assert.equal(titled("Show when folded").title, "keep this tab on the strip while infra is folded", "the pin row's title is its sentence");
    assert.ok(titled("Move to archived").all().find((n) => n.has("ctx-tag-plus"))!.title.startsWith("add this tag too"), "the + keeps its own title");
    assert.ok(titled("infra").all().find((n) => n.has("ctx-tag-x"))!.title.startsWith("remove this tag"), "and so does the ✕");
    menu = api.open("loose", "");
    fly = flyOf(menu);
    assert.equal(titled("+ " + long40).title, "+ " + long40, "a + row's title is its label");
    assert.equal(hooks.writes.length, 4, "no write from any of it");
  });
});

test("pinned: the menu door in render.ts. The toggles' dress is one helper the Hide tab row re-uses on its one node; the write is the pin row's, explicit; the copy's home section is computed once in showTabMenu, tracked through the flyout's move and shared with it; the comment records the reversal", () => {
  const at = RENDER.indexOf("function showTabMenu(");
  const MENU = RENDER.slice(at, RENDER.indexOf("document.body.appendChild(menu);", at));
  // the home computation, hoisted: ONE bare readTabGroups().on read (tab-groups.test pins the count at two in all of render.ts), the
  // copy's section tracked (round 2: copyNow, which the move writes; round 3: "" is no copy, an add from no group claims the copy, and
  // the resolution is the copy's own group, else the one remaining holder, else nothing; round 4: the copy is a SectionRef, its tag's
  // local id and name, matched by the id first and the name second, and every resolution latches what it found), and three callers
  assert.match(MENU, /const unionFor = \(\) => viewTagUnion\(effViews\(\)\);\s*\n\s*const holding = \(\) => unionFor\(\)\.filter\(\(g\) => g\.members\.includes\(id\)\);\s*\n\s*const refOf = \(name: string\): SectionRef => \{ const g = unionFor\(\)\.find\(\(u\) => u\.name === name\); return g \? sectionRef\(g\) : \{ name, localId: null \}; \};[^\n]*\n\s*let copyNow: SectionRef \| undefined = copy \? refOf\(copy\) : undefined;\s*\n\s*const sameSection = \(a: SectionRef, b: SectionRef\) => \(a\.localId !== null && b\.localId !== null \? a\.localId === b\.localId : a\.name === b\.name\);[^\n]*\n\s*const heldCopy = \(held: TagUnion\[\]\): TagUnion \| undefined => \{\s*\n\s*const c = copyNow;\s*\n\s*if \(!c\) return undefined;\s*\n\s*return \(c\.localId !== null \? held\.find\(\(g\) => g\.localId === c\.localId\) : undefined\) \?\? held\.find\(\(g\) => g\.name === c\.name\);[^\n]*\n\s*\};\s*\n\s*const homeNow = \(\): TagUnion \| undefined => \{\s*\n\s*if \(!readTabGroups\(\)\.on\) return undefined;\s*\n\s*const held = holding\(\);\s*\n\s*const home0 = heldCopy\(held\) \?\? \(held\.length === 1 && !held\[0\]\.pending \? held\[0\] : undefined\);[^\n]*\n\s*return home0 && !home0\.pending \? home0 : undefined;\s*\n\s*\};\s*\n\s*let refreshHideRow = \(\) => \{\};[^\n]*\n\s*let refreshTags = \(\) => \{\};/,
    "the copy as a section ref (round 4): refOf resolves a name to its union's ref, or the name alone for a tag not yet created; heldCopy matches in two passes (round 6): by the local id over every held union first, then by the name when no union carries the ref's id, so a pushed rename keeps the copy whatever the drag order, the ack replaces a placeholder id, a remote-only group is known by its name, and a same-named tag under a new id keeps the copy the strip still shows; homeNow is a pure function of the ref and the views (round 5): the copy's own group, else the one remaining holder, nothing latched");
  assert.equal(MENU.split("sameSection(").length - 1, 1, "used by the click's guard alone since round 6 (heldCopy resolves in its own two passes, id then name; round 5 shared the comparison, so a same-named union under a new id was no match and the copy fell through): one comparison of two sections (the declaration reads `sameSection = (`)");
  assert.equal(MENU.split("const sameSection = ").length - 1, 1, "declared once");
  assert.equal(MENU.split("homeNow()").length - 1, 3, "the row's gate (rowHome, which its refresh and its click share, round 6), the flyout's per-build read, and the flyout's signature (round 6: the home resolution is an input its rows read; grouping is read through it, never bare)");
  assert.equal(MENU.split("readTabGroups().on").length - 1, 1, "one bare read in the menu, inside homeNow");
  assert.equal(MENU.replace(/\/\/[^\n]*/g, "").split("copyNow").length - 1, 4, "declared, read once by heldCopy (the one matcher, which homeNow and aimAdd share) and written by the user's gestures alone (round 5): the move and the add (aimAdd); a remove leaves it, and no resolution writes it");
  assert.doesNotMatch(MENU, /copyNow = sectionRef\(home0\)/, "round 5: no latch at the resolution (round 4 kept speaking for the one remaining holder after the removed tag came back, and the click hid it)");
  assert.match(MENU, /else postUnionEdits\(nv, a, r\);\s*\n\s*copyNow = sectionRef\(to\);/, "the move writes the destination's ref, whichever wire carried it");
  // round 3: the claim, one helper, read before the edit, on the adds; round 4: the claim is the destination's ref through refOf, so a
  // tag not yet created is claimed by its name alone until the ack's id lands; round 5: the helper AIMS the ref at the user's add: a copy
  // whose own tag holds the session (pending included) keeps it, one whose tag is away with one other holder is aimed at that holder
  // (the copy the menu speaks for; round 4 latched it at the resolution instead), one with no group is claimed by the add's tag; every
  // add gesture runs it, the "+" beside a Move to row included, so an add from the fallback is an add and the row stays
  assert.match(MENU, /const aimAdd = \(name: string\) => \{\s*\n\s*const held = holding\(\);\s*\n\s*if \(heldCopy\(held\)\) return;\s*\n\s*copyNow = held\.length === 1 && !held\[0\]\.pending \? sectionRef\(held\[0\]\) : refOf\(name\);\s*\n\s*\};/);
  assert.equal(MENU.split("aimAdd(").length - 1, 4, "the four adds aim: the + beside a Move to row, the + <name> row, an existing name typed, a new tag");
  assert.match(MENU, /lb\.textContent = "\+ " \+ g\.name; bodyE\.appendChild\(lb\);\s*\n\s*row\.appendChild\(bodyE\);\s*\n\s*row\.addEventListener\("click", \(e2\) => \{ e2\.stopPropagation\(\); const live = liveUnion\(ref\); if \(!live\) \{ refuse\(row, lb\.textContent \?\? ""\); return; \} aimAdd\(live\.name\); editUnion\(live, \{ add: \[id\] \}\); build\(\); sb\.textContent = subText\(\); \}\);/, "the no-group row: the add is the move, on the union resolved at the click (round 7)");
  assert.match(MENU, /if \(existing\) \{ aimAdd\(existing\.name\); editUnion\(existing, \{ add: \[id\] \}\); build\(\); sb\.textContent = subText\(\); return; \}/, "an existing name typed");
  assert.match(MENU, /delete nv\.groups;\s*\n\s*aimAdd\(name\);[^\n]*\n\s*\/\/ ONE targeted create/, "a new tag: the copy goes under it (no row until the ack, which re-dresses the menu through the views hook)");
  // round 4: THE OPEN MENU FOLLOWS A VIEWS ARRIVAL. One module-level hook, set once the menu is on the page (after the ctxMenuEl
  // assignment, before the seat), cleared by dismissTabMenu beside the flyout's input; it runs the Hide tab row's refresh and the Tags
  // block's refresh (the sub-line, then the open flyout's rebuild, gated on what its rows show and carrying the typed text and the focus
  // across). Round 5: ONE NOTIFIER, viewsChanged, runs the hook, and every site that changes what the strip reads calls it: the tabOrder
  // frame handler after the strip is applied, onViewsAck after the input's re-arm, onKernelCaps once the writes in flight are dropped or
  // the kept blob adopted (before the peek and the repaint, like the other two; round 4 missed it, so a reconnect with an edit in flight
  // left a "creating..." row and a stale Hide tab row), the two tab-groups store listeners after their render (another pane's
  // hide, a grouping flip) and, since round 6, the phone media rule's change listener after its render (a rotation: the Hide tab row
  // is gated on the same rule, so the flip takes it off the open menu). Nothing else calls the hook
  assert.match(RENDER, /\nlet tabMenuViewsHook: \(\) => void = \(\) => \{\};\s*\nfunction viewsChanged\(\) \{ tabMenuViewsHook\(\); \}\s*\nfunction dismissTabMenu\(\) \{\s*\n\s*ctxMenuEl\?\.remove\(\);\s*\n\s*ctxMenuEl = null;\s*\n\s*tagsFlyNewInput = null;\s*\n\s*tabMenuViewsHook = \(\) => \{\};\s*\n\}/, "declared beside the menu's node, the notifier beside it; a closed menu's hook is a no-op");
  assert.equal(RENDER.split("tabMenuViewsHook()").length - 1, 1, "the hook has one caller, the notifier; no timer, no other caller");
  assert.equal(RENDER.split("function viewsChanged()").length - 1, 1, "one notifier");
  assert.equal(RENDER.split("viewsChanged();").length - 1, 6, "six callers: the tabOrder frame handler, onViewsAck, onKernelCaps, the storage listener, the TABGROUPS_EVENT listener and the phone media rule's change listener (round 6)");
  assert.match(RENDER, /captureViews\(m\.views \|\| null\);\s*\n\s*applyTabOrder\(m\.order, m\.tabs, [^\n]*\);\s*\n\s*viewsChanged\(\);/, "the tabOrder frame handler calls it once the blob is held and the strip applied");
  assert.match(RENDER, /syncNewTagInput\(\);[^\n]*\n\s*viewsChanged\(\);[^\n]*\n\s*renderTabs\(\);\s*\n\}/, "onViewsAck calls it after the input's re-arm (a create's ack gives a claimed copy its row)");
  assert.match(RENDER, /\} else if \(!adopted\) return;[^\n]*\n\s*viewsChanged\(\);[^\n]*\n\s*if \(activeId\) assertPeekFor\(activeId\);[^\n]*\n\s*renderTabs\(\);\n\}/, "onKernelCaps calls it once the writes in flight are dropped or the kept blob adopted, before the peek and the repaint; a frame that changed nothing shown returns before it");
  assert.match(RENDER, /window\.addEventListener\("storage", \(e\) => \{ if \(e\.key === TABGROUPS_KEY\) \{ renderTabs\(\); viewsChanged\(\); \} \}\);\s*\nwindow\.addEventListener\(TABGROUPS_EVENT, \(\) => \{ renderTabs\(\); viewsChanged\(\); \}\);/, "the two store listeners: the strip's render, then the open menu");
  assert.match(RENDER, /window\.matchMedia\(PHONE_LAYOUT_MEDIA\)\.addEventListener\("change", \(\) => \{ renderTabs\(\); viewsChanged\(\); \}\);/, "the media rule's listener: the same shape (round 6; before, renderTabs alone, and a menu open across a rotation kept its Hide tab row)");
  assert.match(RENDER, /document\.body\.appendChild\(menu\);\s*\n\s*ctxMenuEl = menu;\s*\n\s*tabMenuViewsHook = \(\) => \{ void hold\.defer\(\(\) => \{ if \(gone\(\)\) return; refreshHideRow\(\); refreshTags\(\); \}\); \};[^\n]*\n\s*seatMenu\(e\.clientX, e\.clientY\);[^\n]*\n\}/, "set once the menu is on the page, before the seat: one run through the menu's hold (round 5), the row's refresh and the Tags block's, dropped once the menu is dismissed");
  assert.equal(RENDER.split("tabMenuViewsHook = ").length - 1, 2, "assigned by showTabMenu and cleared by dismissTabMenu; nowhere else (the declaration reads `let tabMenuViewsHook:`)");
  assert.match(MENU, /sb\.textContent = subText\(\);\s*\n\s*tagsItem\.title = sb\.textContent;[^\n]*\n(?:\s*\/\/[^\n]*\n)+\s*let rebuildFly = \(\) => \{\};\s*\n\s*refreshTags = \(\) => \{ sb\.textContent = subText\(\); tagsItem\.title = sb\.textContent; rebuildFly\(\); \};/, "the Tags block's refresh: the sub-line re-read and the row's title with it (round 5), then the flyout's rebuild (a no-op while it is closed)");
  assert.match(MENU, /const flySig = \(\) => \{ const h = homeNow\(\); return JSON\.stringify\(\[unionFor\(\)\.map\(\(g\) => \[g\.name, g\.localId, g\.color, !!g\.pending, g\.members\.includes\(id\), \[\.\.\.g\.locals, \.\.\.g\.remotes\]\.map\(\(t\) => \[t\.id, \(t\.members \|\| \[\]\)\.includes\(id\)\]\)\]\), h \? \[h\.name, h\.localId, isPinned\(tabGroups\(\), sectionRef\(h\), id\)\] : null\]\); \};\s*\n\s*let builtSig = "";\s*\n(?:\s*\/\/[^\n]*\n)+\s*const nrow = el\("div", "ctx-item ctx-item-newtag"\);\s*\n\s*const inp = el\("input", "ctx-tag-input"\) as HTMLInputElement;[\s\S]{0,2200}?\n\s*nrow\.appendChild\(inp\);\s*\n\s*tagsFlyNewInput = inp; syncNewTagInput\(\);\s*\n\s*sub\.appendChild\(nrow\);[^\n]*\n\s*const add = \(n: HTMLElement\) => sub\.insertBefore\(n, nrow\);[^\n]*\n\s*const build = \(\) => \{\s*\n\s*while \(sub\.firstChild && sub\.firstChild !== nrow\) sub\.firstChild\.remove\(\);[^\n]*\n\s*builtSig = flySig\(\);/, "the New tag… input is ONE node per flyout (round 5), on the flyout before the first build; the rows go in front of it and a build clears only what stands above it; what the rows show is stamped at every build, each constituent tag's id and hold included (round 7: a remote same-named tag joining with the session, or an already-joined one taking it, left the union's tuple unchanged and the rows unbuilt)");
  const flyBlock = MENU.slice(MENU.indexOf('const sub = el("div", "ctx-menu ctx-sub ctx-sub-tags");'), MENU.indexOf("const armHoverClose = "));
  assert.doesNotMatch(flyBlock.replace(/\/\/[^\n]*/g, ""), /replaceChildren|sub\.appendChild\(row\)/, "no rebuild sweeps the input or the foot: every row goes through add");
  assert.equal(flyBlock.split("add(").length - 1, 7, "four rows and three dividers go in front of the input");
  assert.equal(flyBlock.split("sub.appendChild(").length - 1, 3, "appended to the flyout directly: the input's row before the first build, then the foot (its divider and Configure tags…) after it");
  assert.match(MENU, /reseatFly = \(\) => \{ if \(sub\.isConnected\) place\(\); \};\s*\n(?:\s*\/\/[^\n]*\n)+\s*rebuildFly = \(\) => \{ if \(!sub\.isConnected \|\| flySig\(\) === builtSig\) return; build\(\); \};/, "the rebuild, run inside the hook's one deferred run (round 5), its two checks inside that parked run: only while the flyout is on the menu and the blob changed what the rows show; nothing is carried, since the input is one node that never moves");
  assert.doesNotMatch(flyBlock, /typed|focused/, "no value or focus copied back: the round-4 restore is gone with the node it restored");
  assert.match(RENDER, /type TabGroupsState, type SectionRef \} from "\.\/tab-groups";/, "SectionRef reaches render.ts");
  assert.match(MENU, /plus\.addEventListener\("click", \(e2\) => \{ e2\.stopPropagation\(\); const live = liveUnion\(ref\); if \(!live\) \{ refuse\(row, lb\.textContent \?\? ""\); return; \} aimAdd\(live\.name\); editUnion\(live, \{ add: \[id\] \}\); build\(\); sb\.textContent = subText\(\); \}\);/, "the + beside a Move to row aims too (round 5), on the union resolved at the click (round 7): from the one-holder fallback it confirms that holder as the copy, so the add is an add and the row stays");
  // round 3: THE MENU'S SEAT. One seat for the menu (the cursor's corner clamped inside the pane; the emoji picker's anchor follows),
  // re-run from the menu's own corner by the row's refresh, and the open flyout re-placed after it; the seat runs once the menu is on
  // the page (the lift's anchor)
  assert.match(MENU, /let corner: \{ x: number; y: number \} \| null = null;\s*\n\s*const seatMenu = \(x: number, y: number\) => \{\s*\n\s*const r = menu\.getBoundingClientRect\(\);\s*\n\s*const mx = Math\.max\(0, Math\.min\(x, window\.innerWidth - r\.width - 4\)\);\s*\n\s*const my = Math\.max\(0, Math\.min\(y, window\.innerHeight - r\.height - 4\)\);\s*\n\s*menu\.style\.left = mx \+ "px";\s*\n\s*menu\.style\.top = my \+ "px";\s*\n\s*ctxMenuAt = \{ x: mx, y: my \};[^\n]*\n\s*corner = ctxMenuAt;\s*\n\s*\};\s*\n\s*let reseatFly = \(\) => \{\};[^\n]*\n\s*const reseat = \(\) => \{ if \(!corner\) return; seatMenu\(corner\.x, corner\.y\); reseatFly\(\); \};/);
  assert.equal(MENU.split("seatMenu(").length - 1, 1, "inside the menu's build the seat runs from the refresh alone");
  assert.match(RENDER, /document\.body\.appendChild\(menu\);\s*\n\s*ctxMenuEl = menu;\s*\n\s*tabMenuViewsHook = [^\n]*\n\s*seatMenu\(e\.clientX, e\.clientY\);[^\n]*\n\}/, "and once at the cursor when the menu is on the page (round 4: the views hook is set just before it)");
  assert.match(MENU, /menu\.appendChild\(sub\);\s*\n(?:\s*\/\/[^\n]*\n)+\s*const place = \(\) => \{\s*\n\s*const ir = tagsItem\.getBoundingClientRect\(\);\s*\n\s*const sr = sub\.getBoundingClientRect\(\);\s*\n\s*if \(ir\.right \+ 2 \+ sr\.width <= window\.innerWidth - 8\) sub\.style\.left = Math\.round\(ir\.right \+ 2\) \+ "px";\s*\n\s*else sub\.style\.left = Math\.max\(8, Math\.round\(ir\.left\) - sr\.width - 2\) \+ "px";\s*\n\s*sub\.style\.top = Math\.max\(0, Math\.min\(ir\.top, window\.innerHeight - sr\.height - 4\)\) \+ "px";\s*\n\s*\};\s*\n\s*place\(\);\s*\n\s*reseatFly = \(\) => \{ if \(sub\.isConnected\) place\(\); \};/, "the flyout's placement is one closure, run at open and on every reseat while the flyout is on the menu (the side rule and the clamp as they were)");
  assert.equal(MENU.split("sub.style.top = ").length - 1, 2, "the flyouts' tops: Billing's at open, the Tags flyout's in place()");
  const hideAt = MENU.indexOf('"ctx-item ctx-item-toggle ctx-item-hide ctx-sub-capped"');
  assert.ok(MENU.indexOf("const homeNow = ") < hideAt && hideAt < MENU.indexOf("const home = homeNow();   // read per build"), "declared before the row; the flyout's read after it");
  assert.match(MENU, /\/\/ unionFor and holding are showTabMenu's \(above the Hide tab row\), shared with that row\s*\n\s*const tagsItem = el\("div", "ctx-item ctx-item-toggle ctx-item-tags ctx-sub-capped"\);/, "the Tags block declares neither");
  // the toggles' dress: one helper (round 2), the toggle helper building its node with it and returning the node (the bell row is
  // the Hide tab row's anchor)
  assert.match(MENU, /const dressToggle = \(item: HTMLElement, kind: "feed" \| "mail" \| "bell" \| "tab", off: boolean, lab: string, sub: string\) => \{\s*\n\s*const bodyEl = el\("span", "ctx-item-body"\);\s*\n\s*const l = el\("span", "ctx-item-label"\); l\.textContent = lab; bodyEl\.appendChild\(l\);\s*\n\s*const sb = el\("span", "ctx-item-sub"\); sb\.textContent = sub; bodyEl\.appendChild\(sb\);\s*\n\s*item\.replaceChildren\(ctxIcon\(kind, off\), bodyEl\);\s*\n\s*\};/);
  assert.match(MENU, /const toggle = \(kind: "feed" \| "mail" \| "bell" \| "tab", off: boolean, lab: string, sub: string, fn: \(\) => void\) => \{\s*\n\s*const item = el\("div", "ctx-item ctx-item-toggle"\);\s*\n\s*dressToggle\(item, kind, off, lab, sub\);\s*\n\s*item\.addEventListener\("click", \(ev\) => \{ ev\.stopPropagation\(\); dismissTabMenu\(\); fn\(\); \}\);\s*\n\s*menu\.appendChild\(item\);\s*\n\s*return item;\s*\n\s*\};/);
  assert.match(MENU, /const bellItem = toggle\("bell", !onBell,/);
  assert.equal(MENU.split("dressToggle(").length - 1, 2, "two callers, the toggle helper and the Hide tab row's refresh (the declaration reads `dressToggle = (`)");
  // the row (rounds 1 to 3): one node with the row's class and the cap's modifier; the refresh reads the phone gate (the switch's
  // predicate), the copy's section and the stored state, dresses the node and seats it after Notify me, or takes it off the menu
  // while there is no section, and ends by seating the menu and the open flyout again (round 3); the click live: the section
  // resolved again, the state SET to the one the row last showed (never a toggle of the click-time bit), nothing written when the
  // copy is already there or has no group any more; the refresh runs once at build. Round 5: the dismissal comes AFTER the guard
  // round 5: the refresh computes the words and returns before any rebuild when they are unchanged and the row is on the menu (the
  // section and the bit still follow: an ack swaps a placeholder id under the same words); the rebuild, the seating and the removal
  // run through the menu's one hold (pressHold(menu)), so a push under a pressed pointer waits for the release, and a parked run
  // checks the menu is still on the page; the section the row names is set as the row comes to show it. Round 6: the refresh is two
  // steps, the words (refreshHideWords) and the placement (reseat), and the placement runs after the words whatever they did, so a
  // flyout that grew while the row's sentence stood is placed again (round 5's unchanged-words return skipped the seat)
  assert.match(MENU, /const reseat = \(\) => \{ if \(!corner\) return; seatMenu\(corner\.x, corner\.y\); reseatFly\(\); \};\s*\n(?:\s*\/\/[^\n]*\n)+\s*const hold = pressHold\(menu\);\s*\n\s*const gone = \(\) => corner !== null && !menu\.isConnected;/, "one hold for the whole menu, declared before the row and the flyout that share it; a parked run's bail reads seated-once-and-off-the-page (the first refresh runs before the mount)");
  assert.equal(MENU.split("pressHold(").length - 1, 1, "one hold");
  assert.equal(RENDER.split("hold.defer(").length - 1, 1, "one run goes through it, the views hook's whole run (the row's refresh and the Tags block's, the flyout's rebuild inside); two separate parked runs would replace each other under one press");
  assert.match(RENDER, /^import \{ pressHold \} from "\.\/actions";/m, "the shared helper, not a copy (round 7: its own import line, so the delegate line other tests pin stands as the base wrote it)");
  assert.match(MENU, /\{\s*\n\s*const row = el\("div", "ctx-item ctx-item-toggle ctx-item-hide ctx-sub-capped"\);[^\n]*\n\s*let hidden = false;[^\n]*\n\s*let shown: ReturnType<typeof sectionRef> \| null = null;[^\n]*\n\s*let dressed: string \| null = null;[^\n]*\n\s*const rowHome = \(\) => \(phoneLayout\(\) \? undefined : homeNow\(\)\);[^\n]*\n(?:\s*\/\/[^\n]*\n)+\s*const refreshHideWords = \(\) => \{\s*\n\s*const home = rowHome\(\);\s*\n\s*if \(!home\) \{ shown = null; if \(dressed === null\) return; dressed = null; row\.remove\(\); return; \}\s*\n\s*shown = sectionRef\(home\);\s*\n\s*hidden = isHidden\(tabGroups\(\), shown, id\);\s*\n\s*const lab = hidden \? "Show tab" : "Hide tab";\s*\n\s*const sub = hidden \? `back on the strip in \$\{home\.name\}` : `hidden in \$\{home\.name\}; to show it, open the group's view`;\s*\n\s*const words = lab \+ "\\n" \+ sub;\s*\n\s*if \(row\.parentNode && words === dressed\) return;\s*\n\s*dressed = words;\s*\n\s*dressToggle\(row, "tab", hidden, lab, sub\);\s*\n\s*row\.title = sub;[^\n]*\n\s*if \(!row\.parentNode\) bellItem\.after\(row\);\s*\n\s*\};\s*\n\s*refreshHideRow = \(\) => \{ refreshHideWords\(\); reseat\(\); \};[^\n]*\n(?:\s*\/\/[^\n]*\n)+\s*const acknowledge = \(\) => \{\s*\n\s*row\.title = `\$\{dressed!\.slice\(dressed!\.indexOf\("\\n"\) \+ 1\)\}\. The group changed just before your click, so it did nothing; click again\.`;\s*\n\s*row\.classList\.remove\("romp-acted"\);\s*\n\s*void row\.offsetWidth;[^\n]*\n\s*row\.classList\.add\("romp-acted"\);\s*\n\s*\};\s*\n\s*row\.addEventListener\("animationend", \(\) => row\.classList\.remove\("romp-acted"\)\);\s*\n\s*row\.addEventListener\("click", \(ev\) => \{\s*\n\s*ev\.stopPropagation\(\);\s*\n\s*const now = rowHome\(\);\s*\n\s*if \(!now\) \{ dismissTabMenu\(\); return; \}\s*\n\s*const sec = sectionRef\(now\), st = tabGroups\(\);\s*\n(?:\s*\/\/[^\n]*\n)*\s*if \(!shown \|\| !sameSection\(sec, shown\)\) \{\s*\n\s*const before = dressed;\s*\n\s*refreshHideRow\(\);\s*\n\s*if \(dressed !== null && dressed === before\) acknowledge\(\);\s*\n\s*return;\s*\n\s*\}\s*\n\s*dismissTabMenu\(\);\s*\n\s*if \(isHidden\(st, sec, id\) === !hidden\) return;\s*\n\s*writeTabGroupsPruned\(setHidden\(st, sec, id, !hidden\)\);\s*\n\s*\}\);\s*\n\s*refreshHideRow\(\);\s*\n\s*\}/,
    "round 5: the guard runs before the dismissal, so a refused click re-dresses the row on a menu still on the page; the no-home branch dismisses explicitly; a click that writes dismisses first, as every other row does; round 6: the refresh and the click read the copy's section through one gate, rowHome, so a click that lands on the phone layout before the flip's parked refresh writes nothing, and a refusal whose re-dress changed no word gives the cue (the sheet's .romp-acted pulse, off on animationend, and the tooltip's note) instead of silence");
  assert.match(CSS, /\n@keyframes romp-acted-pulse \{[^\n]*\}\n\.romp-acted \{ animation: romp-acted-pulse 0\.28s ease-out; \}\n/, "the cue is the sheet's one press acknowledgement (ui/CLAUDE.md), not a new animation");
  assert.equal(MENU.split("acknowledge()").length - 1, 1, "the cue has one caller, the refused click whose re-dress changed nothing");
  assert.doesNotMatch(MENU.slice(MENU.indexOf("// HIDE TAB (the user 2026-09-09)"), MENU.indexOf("// Billing submenu")), /setTimeout|flash\(/, "the class leaves on the animation's own end, never a timer (actions.ts's flash keeps a timer for controls with no node of their own to listen on)");
  assert.equal(MENU.split("phoneLayout()").length - 1, 1, "the gate is read once, in rowHome, which the refresh and the click share (round 6; the flyout's home read is untouched)");
  assert.equal(MENU.split("rowHome()").length - 1, 2, "read by the refresh and by the click");
  assert.match(MENU, /add\(el\("div", "ctx-sep"\)\);\s*\n\s*tagsItem\.title = subText\(\);[^\n]*\n\s*refreshHideRow\(\);[^\n]*\n\s*\};\s*\n\s*build\(\);/, "the flyout's build ends with the Tags row's title and the refresh: every edit path there (a move, a remove, a +, a new or an existing tag) rebuilds the flyout");
  assert.equal(MENU.split("tagsItem.title = ").length - 1, 3, "the Tags row's title: at the build, in the refresh, at every build of the flyout (round 5)");
  assert.equal(MENU.split("row.title = sub;").length - 1, 1, "the Hide tab row's title is its sub-line, set as the row is dressed (round 5)");
  assert.equal(MENU.split("refreshHideRow()").length - 1, 3, "called at build, at the end of the flyout's build, and by the click that found the resolution moved off the copy the row named (round 4); the views hook that also calls it is set past the menu's build (pinned above); no timer, no other caller");
  assert.equal(MENU.split("reseat()").length - 1, 1, "one caller: the refresh's placement step, after the words whatever they did (round 6; round 5 seated on the two exits that changed the words and skipped the seat on the unchanged-words return); no other caller, no timer");
  assert.equal(MENU.split("refreshHideWords()").length - 1, 1, "the words step has one caller, the refresh");
  const bellAt = MENU.indexOf('toggle("bell"'), billingAt = MENU.indexOf("// Billing submenu"), tagsAt = MENU.indexOf('l.textContent = "Tags"');
  assert.ok(bellAt > 0 && hideAt > bellAt && billingAt > hideAt && tagsAt > billingAt, "after the bell, before Billing and Tags");
  const row = MENU.slice(MENU.indexOf("// HIDE TAB (the user 2026-09-09)"), billingAt);
  assert.doesNotMatch(row, /renderTabs\(\)|setTimeout|postMessage|toggleHidden|readTabGroups\(/, "no render of its own, no timer, no wire, never a toggle of the stored bit, never a store read without the unions on a path that writes");
  assert.match(row, /This reverses the earlier ruling that the pane\s*\n\s*\/\/ was the one door to a hide \(2026-09-08\); the user asked for the menu door\./);
  const flatRow = row.replace(/\s*\n\s*\/\/\s?/g, " ");   // the comment's words, not its wrap
  assert.match(flatRow, /hides do not apply on the flat strip, to an untagged session, under a tag whose create is still in flight or on the phone, so the row is absent there\./);
  assert.match(flatRow, /THE ROW FOLLOWS THE COPY, THE CLICK IS LIVE \(rounds 1 and 2\)/, "the comment says which half is read when");
  assert.match(flatRow, /No home at click time \(moved out of every group, or the strip flattened in another pane\): the click dismisses and writes nothing\./);
  assert.match(flatRow, /round 5: the refused click leaves the menu OPEN with the row re-dressed, so the user sees the new words and clicks again, while a click that writes dismisses the menu first, as every other row does/, "the comment states the order (round 5)");
  assert.ok(!row.includes("\u2014"), "no em dash in the new comment");
  const homeComment = MENU.slice(MENU.indexOf("// THE RIGHT-CLICKED COPY'S HOME SECTION, TRACKED."), MENU.indexOf("const unionFor = "));
  assert.match(homeComment.replace(/\s*\n\s*\/\/\s?/g, " "), /The resolution \(round 3\): the named copy's own group while it still holds the session; else the session's ONE remaining holder, the unambiguous case \(an x on the copy's tag on a two-tag session leaves one copy; a caller naming no copy on a one-tag session has one\), which speaks for the copy while its own tag is away; else nothing, so with two or more other holders there is no copy to hide, move or pin/, "the resolution is stated where the computation is (round 3: the one-holder return, the ambiguous case; round 5: the holder speaks for the copy, it does not become it)");
  assert.match(homeComment.replace(/\s*\n\s*\/\/\s?/g, " "), /THE RESOLUTION IS A PURE FUNCTION of the right-clicked copy and the current views \(round 5\): homeNow reads copyNow and writes nothing, so a tag that comes back from elsewhere \(a remove the kernel refused, another pane's add\) makes the menu speak for the copy the user right-clicked again\..*copyNow changes at the user's own gestures alone: a move aims it at the destination \(moveUnion\), and an add aims it at the copy the menu speaks for at that moment \(aimAdd:/, "round 5: the rule and the gestures that write the ref are stated at the computation");
  assert.match(homeComment.replace(/\s*\n\s*\/\/\s?/g, " "), /a tab in the untagged trail carries "" there, which names no group, so it reads as no copy/, "the trail caller is described as it is (round 3: the comment had said the flat strip names none)");
  assert.match(homeComment.replace(/\s*\n\s*\/\/\s?/g, " "), /THE COPY IS A SECTION REF \(round 4\): copyNow holds the copy's tag as a pin addresses its section \(tab-groups\.ts SectionRef: the local tag's id when the frame carries one, and its name\)\. IDENTITY FIRST, THE NAME AS THE FALLBACK \(round 6\): a held union is the copy's by its local id, and by its name only when no held union carries the ref's id \(heldCopy's two passes\)\..*so a remote-only union under the old name cannot take the copy by coming first in the drag order.*The name carries the copy where the id cannot: a tag typed into the flyout while the copy had no group is claimed by its name alone \(aimAdd runs before the create is posted, so the ref never carries an id\); a copy right-clicked under a tag whose create the kernel had not yet answered carries the placeholder id the ack replaces, which no union carries afterwards \(round 7\); a union only remote hosts' tags make has no local id; and a local tag deleted and created again under the same name has a new id, so the same-named union holds the copy, as the strip's section, keyed by the name, still shows it\. A copy the name alone carries is lost to a rename pushed while the session is under two or more groups \(the row leaves, a click writes nothing\), the limit the guide states for the remote-only group and the tag whose create was unanswered\. The click's guard compares the row's section and the resolution through sameSection \(the ids when both are local, else the names, so two remote-only sections are two\), so a copy re-identified under the same words refuses the click once, with the row's cue, and the second click writes for the new id\.\s*$/, "round 4: the tracking is stated where it is computed, its limit included; round 5: no latch sentence closes it; round 6: the id first and the name as the fallback, the drag-order case and the same-named re-create named, and no claim that an add gesture re-aims a name-only ref (aimAdd returns while the copy's tag holds the session, so none does); round 7: the typed create never wears the placeholder id (aimAdd runs before postTagEdit), the right-clicked pending copy does, and the two-holder rename limit is stated for both name-carried kinds (N6b executes the pending one)");
  assert.doesNotMatch(homeComment, /until an add gesture aims the ref at it/, "round 6: the clause was false (heldCopy matches the created tag by its name, so aimAdd returns and no add re-aims the ref)");
  assert.ok(!homeComment.includes("\u2014"));
  // the glyph: a new ctxIcon kind, a tab on the strip's baseline, slashed by the helper's own `off` when hidden
  assert.match(RENDER, /function ctxIcon\(kind: "feed" \| "mail" \| "bell" \| "bill" \| "folder" \| "tag" \| "pencil" \| "smile" \| "tab", off: boolean\): HTMLElement \{/);
  assert.match(RENDER, /: kind === "tab"\s*\n\s*\? '<path d="M2 12\.4 L2 6\.4 [^']*"\/><line x1="1\.2" y1="12\.4" x2="14\.8" y2="12\.4"\/>'/);
  assert.match(RENDER, /import \{ planStrip, readTabGroups, writeTabGroups, setSectionCollapsed, sectionRef, isPinned, setPinned, isHidden, setHidden, prunePinned,/, "isHidden reaches render.ts");
  // the flyout reads the shared computation on every build of its own
  assert.match(MENU, /const home = homeNow\(\);   \/\/ read per build: a move or a remove above changes the copy's group \(the Hide tab row reads the same\)\s*\n\s*for \(const g of others\) \{/);
  assert.doesNotMatch(MENU, /const home = home0 && !home0\.pending \? home0 : undefined;/, "the flyout's own copy of the computation is gone");
});

test("pinned: a tag name never widens the MAIN menu (menu review rounds 2 to 5). .ctx-item-sub keeps the menus' one sub-line size, byte-equal in feed.css; a modifier the two menu rows whose sub-line carries a tag name wear (Hide tab, Tags), and no fixed row and no flyout row does, makes the body take the row's spare width and the text contribute nothing to the menu's intrinsic width, so the menu is as wide as its fixed rows alone in every face and the name elides; the Tags flyout's rows keep their natural width up to a per-row cap", () => {
  // the rows are nowrap and the menu is sized by its widest row, so the Hide tab row's sub-line grew the menu with the tag name (a
  // 512px menu at the 40-character maximum in Inter, clipped at a 450px pane's edge). Round 2 capped .ctx-item-sub itself, which cut
  // the Emoji row's sub-line (36.1em in the light theme's Space Grotesk and in a fallback face) and diverged from feed.css's copy of
  // the rule; round 3 moved the 36em cap to the row's modifier, which still widened the dark theme's menu by 28px (Inter's widest
  // fixed sub-line is 33.1em) and overflowed a 400px pane; round 4 dropped the constant for a structural rule, and put the modifier
  // on every row whose text carries a tag name, the Tags flyout's Move to and Show when folded rows included, which collapsed the
  // flyout (no wide fixed row holds it open) to the New tag input's width and cut a five-character tag's Show when folded line.
  // Round 5: the modifier is the main menu's alone (the Hide tab row and the Tags row, whose sub-line joins the names); a flyout row
  // keeps its natural width up to a per-row cap with an ellipsis, so the ✕ and the + hug their labels as at the base.
  // tab-hide-browser.test measures both in Chromium.
  assert.match(CSS, /\n\.ctx-item-sub \{ font-size: 0\.82em; opacity: 0\.6; \}\n/, "the one rule for the class: the size and the opacity, nothing else (the menus' one sub-line size)");
  assert.equal(CSS.split("\n.ctx-item-sub {").length - 1, 1, "one rule for the class");
  const FEED = ui("webview", "feed.css");
  const subRule = (css: string) => { const at = css.indexOf("\n.ctx-item-sub {"); return css.slice(at, css.indexOf("\n", at + 1)); };
  assert.equal(subRule(FEED), subRule(CSS), "feed.css mirrors the chat menu's chrome (its comment says so) and the sub-line rule is byte-equal there (round 3: the class cap had diverged them)");
  assert.match(CSS, /\n\.ctx-sub-capped \.ctx-item-body \{ flex: 1 1 0; min-width: 0; \}\n\.ctx-sub-capped \.ctx-item-label, \.ctx-sub-capped \.ctx-item-sub \{ width: 0; min-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; \}\n/,
    "the structural rule on the row's modifier, after the class rule: the body takes the spare width (flex-basis 0, min-width 0), the label and sub-line contribute nothing to the intrinsic width (width 0) and fill the body once laid out (min-width 100%), eliding");
  assert.doesNotMatch(CSS, /\.ctx-sub-capped[^\n]*max-width/, "round 4: no em constant (36em left the dark theme's menu 28px wider than its fixed rows)");
  assert.equal(CSS.split("\n.ctx-sub-capped").length - 1, 2, "the modifier's two rules, nothing else");
  assert.doesNotMatch(CSS, /\.ctx-item-hide|\.ctx-item-tags|\.ctx-item-pin/, "the sheet names the modifier, not the rows: any row whose text carries a name wears it");
  // the wearers: the two MAIN-menu rows whose sub-line carries a tag name, and none of the fixed rows and no flyout row (round 5)
  const MENU = RENDER.slice(RENDER.indexOf("function showTabMenu("), RENDER.indexOf("document.body.appendChild(menu);", RENDER.indexOf("function showTabMenu(")));
  const code = RENDER.replace(/\/\/[^\n]*/g, "").replace(/\/\*[\s\S]*?\*\//g, "");
  const wearers = Array.from(code.matchAll(/el\("div", "([^"]*ctx-sub-capped[^"]*)"/g)).map((m) => m[1]).sort();
  assert.deepEqual(wearers, ["ctx-item ctx-item-toggle ctx-item-hide ctx-sub-capped", "ctx-item ctx-item-toggle ctx-item-tags ctx-sub-capped"],
    "the Hide tab row (the sub-line names the group) and the Tags row (the sub-line joins the names) wear it, and nothing else (round 5: the flyout's rows wore it in round 4, and the flyout collapsed)");
  assert.equal(code.split("ctx-sub-capped").length - 1, 2, "two wearers, each on its el() call");
  assert.match(MENU, /for \(const g of others\) \{\s*\n\s*const row = el\("div", "ctx-item ctx-item-toggle"\);/, "a Move to row wears no modifier (round 5): the flyout's per-row cap bounds its label");
  assert.match(MENU, /const row = el\("div", "ctx-item ctx-item-toggle ctx-item-pin" \+ \(on \? " current" : ""\)\);/, "the Show when folded row wears none: the per-row cap bounds its sub-line");
  for (const fixed of [/const item = el\("div", "ctx-item ctx-item-toggle"\);/, /const item = el\("div", "ctx-item ctx-item-toggle ctx-item-billing"\);/]) assert.match(MENU, fixed, "a fixed row wears no modifier: " + fixed.source);
  // the flyout's rows: a per-row cap with an ellipsis (round 2's shape, in the flyout alone), the label's and the sub-line's own, each
  // chosen so a 19-character name is whole and a 40-character one elides in both faces and both engines (the note gives the measurements)
  assert.match(CSS, /\n\.ctx-sub-tags \.ctx-item-label \{ max-width: 22em; overflow: hidden; text-overflow: ellipsis; \}\n\.ctx-sub-tags \.ctx-item-sub \{ max-width: 36em; overflow: hidden; text-overflow: ellipsis; \}\n/,
    "the flyout's two rules, after the modifier's: a label up to 22em (a 19-character destination is 14.5em, a 40-character one 23.8em to 25.5em), a sub-line up to 36em of its own font (the Show when folded line is 30.3em at 19 characters, 38.7em to 41.5em at 40)");
  assert.equal(CSS.split("\n.ctx-sub-tags").length - 1, 2, "the flyout's two rules, nothing else on its class");
  assert.ok(CSS.indexOf("\n.ctx-sub-capped .ctx-item-label") < CSS.indexOf("\n.ctx-sub-tags .ctx-item-label"), "the flyout's rules follow the modifier's");
  assert.doesNotMatch(CSS, /\.ctx-sub-tags[^\n]*(width: 0|min-width|flex)/, "no structural rule in the flyout: nothing there holds it open, so the rows size it");
  assert.match(CSS, /\n\.ctx-item \{ padding: 4px 10px; border-radius: 4px; cursor: pointer; white-space: nowrap; \}/, "the rows stay nowrap: the rule elides, it does not wrap (a wrapped row would grow every menu's rows)");
  const note = CSS.slice(CSS.indexOf("/* A row whose sub-line or label carries a tag name wears a modifier"), CSS.indexOf("\n.ctx-sub-capped .ctx-item-body {"));
  assert.ok(note.length > 100 && !note.includes("\u2014"), "the rule's note, no em dash");
  assert.match(note.replace(/\s+/g, " "), /with no per-face constant: in a capped row the body takes the row's spare width and no more/, "the note states the mechanism");
  assert.match(note.replace(/\s+/g, " "), /The wearers: the Hide tab row and the Tags row, the two rows of the MAIN menu whose sub-line carries a tag name; no row of the Tags flyout \(the rule after this one\)\./, "the note names the two wearers and excludes the flyout (round 5)");
  assert.match(note.replace(/\s+/g, " "), /at 450px, 400px and 383px panes/, "the note names the widths the browser leg measures");
  const flyNote = CSS.slice(CSS.indexOf("/* The Tags flyout's rows wear no modifier (round 5)"), CSS.indexOf("\n.ctx-sub-tags .ctx-item-label {"));
  assert.ok(flyNote.length > 100 && !flyNote.includes("\u2014"), "the flyout rule's note, no em dash");
  assert.match(flyNote.replace(/\s+/g, " "), /A flyout row keeps its natural width up to a per-row cap with an ellipsis \(round 2's shape, in the flyout alone\): 22em for a label, so a 19-character destination is whole \(14\.5em\) and a 40-character one elides \(23\.8em to 25\.5em by face and engine\); 36em of its own font for a sub-line/, "the note states the caps and what they keep whole");
  assert.match(flyNote.replace(/\s+/g, " "), /The ✕ and the \+ sit beside their labels as at the base, and the flyout is as wide as its widest row up to the cap\./);
  assert.match(RENDER, /inp\.placeholder = "New tag…"; inp\.maxLength = 40;/, "the tag name's own bound, the widest case the leg measures");
});

test("executed: THE CLICK IS LIVE (menu review round 1; round 2 puts the mechanism first). Move to in the Tags flyout with the menu still open, then Hide tab: the write names the group the copy now sits in; a copy another pane hid where it sits stays hidden, never flipped back; no home at the click, nothing written", () => {
  // round 1: the row captured its section at build; the flyout's Move to (moveUnion + build(), no dismiss) left the menu open with the
  // copy in another group, so the click wrote a hide for the old section, which prunePinned dropped: one write with hidden [],
  // nothing hidden, no message. Now the click resolves the section again and SETS the state the row promised (the pin row's idiom).
  // Round 2: the first assertion after the move is the write's section, so a failure here is the stale-section write and never the
  // words (THE ROW FOLLOWS THE COPY, below, checks those).
  const hooks: MenuHooks = {
    views: V, known: ALL,
    sessions: new Map<string, unknown>([["web", { name: "web", status: { state: "ready" } }], ["api", { name: "api", status: { state: "working" } }]]),
    writes: [], dismissed: 0, renders: 0, flags: [],
    mods: { FakeEl, viewTagUnion, readTabGroups, writeTabGroups, prunePinned, sectionRef, isPinned, setPinned, isHidden, setHidden },
  };
  const ARCHIVED: SectionRef = { name: "archived", localId: "g2" };
  const rowOf = (menu: FakeEl) => menu.children.find((it) => it.has("ctx-item-hide"))!;
  withStore(() => {
    const api = liftShowTabMenu()(hooks);
    // C1: web's infra copy (THE MENU DOOR pins its words); Move to archived inside the open menu; the click hides in archived
    let menu = api.open("web", "infra");
    let row = rowOf(menu);
    assert.match(row.sub()!, /\binfra\b/, "the row was built for the infra copy");
    moveVia(menu, "archived");
    const u2 = viewTagUnion(hooks.views as typeof V);
    assert.deepEqual(u2.map((g) => [g.name, g.members]), [["infra", ["api", "tests"]], ["archived", ["old1", "old2", "web"]]], "the blob the menu reads now: web under archived");
    const d0 = hooks.dismissed;
    row.click();
    assert.equal(hooks.writes.length, 1);
    assert.deepEqual(hooks.writes[0].hidden, [{ sid: "web", name: "archived", id: "g2" }], "the click is live: the section the copy sits in at the click, not the one the row was built for");
    assert.equal(hooks.dismissed, d0 + 1, "dismissed");
    assert.deepEqual([isHidden(hooks.writes[0], ARCHIVED, "web"), isHidden(hooks.writes[0], INFRA, "web")], [true, false]);
    const p = planStrip(ALL, u2, setSectionCollapsed(readTabGroups(u2), "archived", false), "api", false);
    assert.deepEqual(p.items.filter((i): i is { id: string } => "id" in i).map((i) => i.id), ["api", "tests", "old1", "old2", "loose"], "and the strip's own plan leaves web off under archived");
    assert.deepEqual(heads(p.items).find((h) => h.head.name === "archived")!.hides, ["web"]);
    // C2: ANOTHER PANE hid the copy where it sits between the build and the click (no flyout edit, so no refresh: the row still reads
    // Hide tab). The click finds api already in the promised state under infra: nothing written, nothing flipped back
    hooks.views = V;
    writeTabGroups(d);
    menu = api.open("api", "infra");
    row = rowOf(menu);
    assert.equal(row.label(), "Hide tab", "shown in infra");
    writeTabGroups(setHidden(readTabGroups(unions), INFRA, "api", true));   // the other pane's Hide
    const d1 = hooks.dismissed;
    row.click();
    assert.equal(hooks.dismissed, d1 + 1);
    assert.equal(hooks.writes.length, 1, "no write: the copy is in the promised state already");
    assert.equal(isHidden(readTabGroups(unions), INFRA, "api"), true, "stays hidden (a click-time toggle would have shown it)");
    // C3: no home at the click. The row was built for web in infra; a push then took web out of every group; the click dismisses, writes nothing
    hooks.views = V;
    writeTabGroups(d);
    menu = api.open("web", "infra");
    row = rowOf(menu);
    hooks.views = { ...V, tags: [{ ...V.tags[0], members: ["api", "tests"] }, V.tags[1]], seq: 4 };
    const d2 = hooks.dismissed;
    row.click();
    assert.equal(hooks.dismissed, d2 + 1, "dismissed all the same");
    assert.equal(hooks.writes.length, 1, "nothing written for a copy with no group to hide in");
    assert.deepEqual(readTabGroups(viewTagUnion(hooks.views as typeof V)).hidden, [], "and the store shows it");
    // C4 (round 4): one OTHER holder left at the click. The row was built for api in infra (api under infra and archived); a push then
    // took infra off api, so the resolution is archived, the one holder left, while the row still reads infra; a hide there would be
    // of a copy the user never touched, so the click writes nothing and re-dresses the row for the copy the session has left
    hooks.views = V_API_BOTH;
    writeTabGroups(d);
    menu = api.open("api", "infra");
    row = rowOf(menu);
    assert.equal(row.sub(), HIDE_SUB("infra"));
    hooks.views = { ...V_API_BOTH, tags: [{ ...V_API_BOTH.tags[0], members: V_API_BOTH.tags[0].members.filter((m: string) => m !== "api") }, V_API_BOTH.tags[1]], seq: 5 };
    const d3 = hooks.dismissed;
    assert.equal(menu.isConnected, true);
    row.click();
    assert.equal(hooks.writes.length, 1, "nothing written: the row named infra, and archived is a copy the user never touched (round 4; before, the click wrote hidden [{api, archived, g2}])");
    assert.deepEqual(readTabGroups(viewTagUnion(hooks.views as typeof V)).hidden, [], "the store shows it");
    assert.equal(hooks.dismissed, d3, "the refused click does not dismiss (round 5; round 4 dismissed first, so the re-dress below reached a menu already off the page)");
    assert.equal(menu.isConnected, true, "the menu stays on the page");
    assert.equal(rowOf(menu)?.sub(), HIDE_SUB("archived"), "and the row re-dressed in place for the copy the session has left, where the user sees it");
    assert.equal(rowOf(menu), row, "the same node");
    row.click();
    assert.equal(hooks.writes.length, 2, "the second click acts on the words shown");
    assert.deepEqual(hooks.writes[1].hidden, [{ sid: "api", name: "archived", id: "g2" }], "the copy the re-dressed row names");
    assert.equal(hooks.dismissed, d3 + 1, "a click that writes dismisses");
    assert.equal(menu.isConnected, false, "the menu left the page");
    // C5 (round 5): two REMOTE-ONLY holders, both without a local id. web under ops and ops2, two sections only another host's tags
    // make; the menu on the ops copy; the blob then set WITHOUT the hook (as C4) so ops no longer holds web: the resolution is ops2, the
    // one holder left, while the row still reads ops. Round 4's guard compared the ids first and took null for null, so the hide of
    // ops2, a copy the row never named, went through; sameSection compares two id-less sections by their names, and the click is refused
    const V_R2 = { ...V, tags: [{ ...V.tags[0], members: ["api", "tests"] }, V.tags[1]],
      remoteTags: [{ id: "TESTHOST:r1", host: "TESTHOST", name: "ops", color: "#123456", members: ["web", "api"] }, { id: "TESTHOST:r2", host: "TESTHOST", name: "ops2", color: "#654321", members: ["web"] }], seq: 6 };
    hooks.views = V_R2; hooks.writes = [];
    writeTabGroups(d);
    menu = api.open("web", "ops");
    row = rowOf(menu);
    assert.equal(row.sub(), HIDE_SUB("ops"), "a remote-only section's copy, known by its name");
    hooks.views = { ...V_R2, remoteTags: [{ ...V_R2.remoteTags[0], members: ["api"] }, V_R2.remoteTags[1]], seq: 7 };
    const d4 = hooks.dismissed;
    row.click();
    assert.equal(hooks.writes.length, 0, "nothing written: ops2 is a copy the row never named (round 4 wrote hidden [{web, ops2}], the two null ids read as one section)");
    assert.equal(hooks.dismissed, d4, "refused, the menu open");
    assert.equal(rowOf(menu)?.sub(), HIDE_SUB("ops2"), "the row re-dressed for the one holder left");
    row.click();
    assert.equal(hooks.writes.length, 1, "the second click writes what the row shows");
    assert.equal(isHidden(hooks.writes[0], { name: "ops2", localId: null }, "web"), true);
    assert.equal(isHidden(hooks.writes[0], { name: "ops", localId: null }, "web"), false);
    // C6 (round 5, the control): the same two id-less sections, a blob set without the hook that changes something else (ops2 lets api
    // go) and leaves the copy's own section holding it: the name match carries the copy and the click writes for ops
    hooks.views = { ...V_R2, remoteTags: [V_R2.remoteTags[0], { ...V_R2.remoteTags[1], members: ["web", "api"] }], seq: 8 }; hooks.writes = [];
    writeTabGroups(d);
    menu = api.open("web", "ops");
    row = rowOf(menu);
    hooks.views = V_R2;
    const d5 = hooks.dismissed;
    row.click();
    assert.equal(hooks.dismissed, d5 + 1, "dismissed: the click acts");
    assert.equal(hooks.writes.length, 1);
    assert.equal(isHidden(hooks.writes[0], { name: "ops", localId: null }, "web"), true, "the copy whose resolution did not change: hidden in ops, by the name match of two id-less refs");
    assert.equal(isHidden(hooks.writes[0], { name: "ops2", localId: null }, "web"), false);
  });
});

/** the real Tags flyout, opened by its row's click, and its Move to <g> row clicked: the optimistic blob the stub holds as holdViews does */
function moveVia(menu: FakeEl, to: string) {
  menu.children.find((it) => it.has("ctx-item-tags"))!.click();
  const fly = menu.children.find((it) => it.has("ctx-sub-tags"));
  assert.ok(fly, "the flyout is on the menu");
  const moveRow = fly!.children.find((it) => it.label() === "Move to " + to);
  assert.ok(moveRow, "the Move to row for the other group");
  moveRow!.click();
}
/** the flyout on the menu, opened if it is not */
function flyOf(menu: FakeEl): FakeEl {
  let fly = menu.children.find((it) => it.has("ctx-sub-tags"));
  if (!fly) { menu.children.find((it) => it.has("ctx-item-tags"))!.click(); fly = menu.children.find((it) => it.has("ctx-sub-tags")); }
  assert.ok(fly, "the flyout is on the menu");
  return fly!;
}
const menuHooks = (phone = false): MenuHooks => ({
  views: V, known: ALL,
  sessions: new Map<string, unknown>([["web", { name: "web", status: { state: "ready" } }], ["api", { name: "api", status: { state: "working" } }], ["loose", { name: "loose", status: { state: "ready" } }]]),
  writes: [], dismissed: 0, renders: 0, flags: [], phone,
  mods: { FakeEl, viewTagUnion, readTabGroups, writeTabGroups, prunePinned, sectionRef, isPinned, setPinned, isHidden, setHidden },
});
const ARCHIVED_REF: SectionRef = { name: "archived", localId: "g2" };
/** api under infra AND archived (T264b: a copy in each group) */
const V_API_BOTH = { ...V, tags: [V.tags[0], { ...V.tags[1], members: ["old1", "old2", "api"] }], seq: 4 };

test("executed: THE ROW FOLLOWS THE COPY (menu review round 2). Move to inside the open menu re-dresses the Hide tab row for the destination: the words name the new group in the same sentence; onto a copy the pane hid there the row reads Show tab and its click shows; a + that adds a tag leaves the row as it was", () => {
  // round 1 left the row's words as a snapshot (the group it was built for) while its click acted on the copy's current group, so
  // after a Move to inside the menu the row promised one group and wrote another (and, moved onto a copy the pane had hidden in the
  // destination, read Hide tab over a hidden copy). The flyout's build() now refreshes the row after each of its writes (a move, a
  // remove, an add), keyed on the write, and the click's bit is the refreshed one
  const hooks = menuHooks();
  const rowOf = (menu: FakeEl) => menu.children.find((it) => it.has("ctx-item-hide"))!;
  withStore(() => {
    const api = liftShowTabMenu()(hooks);
    // W1: web's infra copy; Move to archived: the row names archived and no longer infra, the same sentence; the glyph unslashed; one
    // node re-dressed in its place; the click hides in archived
    let menu = api.open("web", "infra");
    let row = rowOf(menu);
    const before = row.sub()!;
    moveVia(menu, "archived");
    assert.match(row.sub()!, /\barchived\b/, "the row speaks for the copy where it now sits");
    assert.doesNotMatch(row.sub()!, /\binfra\b/, "and no longer for the group it left");
    assert.equal(row.sub(), before.replace("infra", "archived"), "the same sentence, the destination named");
    assert.equal(row.sub(), HIDE_SUB("archived"));
    assert.equal(row.title, HIDE_SUB("archived"), "the tooltip follows the re-dress (round 5)");
    assert.equal(menu.children.find((it) => it.has("ctx-item-tags"))!.title, "archived", "the Tags row's tooltip follows the flyout's own edit");
    assert.deepEqual([row.label(), row.icon()!.dataset.kind, row.icon()!.has("off")], ["Hide tab", "tab", false]);
    assert.equal(rowOf(menu), row, "one node, re-dressed");
    assert.equal(menu.children.indexOf(row), menu.children.findIndex((it) => it.label() === "Notify me") + 1, "still directly after Notify me");
    row.click();
    assert.deepEqual(hooks.writes.map((w) => w.hidden), [[{ sid: "web", name: "archived", id: "g2" }]], "and the click hides where the row said");
    // W2: the pane hid api in archived; api is under infra too; the menu on the infra copy reads Hide tab; Move to archived: the row now
    // reads Show tab for archived (the copy is hidden where it sits), the glyph slashed, and its click SHOWS it, the state the
    // refreshed row promised (round 1 read Hide tab there and wrote nothing)
    hooks.views = V;
    writeTabGroups(setHidden(d, ARCHIVED_REF, "api", true));
    menu = api.open("api", "infra");
    row = rowOf(menu);
    assert.equal(row.label(), "Hide tab", "shown in infra");
    moveVia(menu, "archived");
    assert.deepEqual([row.label(), row.sub(), row.icon()!.has("off")], ["Show tab", "back on the strip in archived", true], "the copy is hidden where it now sits");
    row.click();
    assert.equal(hooks.writes.length, 2);
    assert.deepEqual(hooks.writes[1].hidden, [], "the click shows it: the state the refreshed row promised");
    // W3: the flyout's other writes refresh too, and a + that adds a second tag leaves the row as it was: the copy did not move
    hooks.views = V;
    writeTabGroups(d);
    menu = api.open("web", "infra");
    row = rowOf(menu);
    const fly = flyOf(menu);
    fly.children.find((it) => it.label() === "Move to archived")!.all().find((n) => n.has("ctx-tag-plus"))!.click();
    assert.deepEqual(viewTagUnion(hooks.views as typeof V).map((g) => g.members), [["web", "api", "tests"], ["old1", "old2", "web"]], "web under both");
    assert.equal(row.sub(), HIDE_SUB("infra"), "the copy stayed in infra: the row still names it");
    assert.equal(hooks.writes.length, 2, "the flyout's edits write no hide");
  });
});

test("executed: TWO TAGS, MOVED INSIDE THE MENU (menu review round 2). A session under infra and archived, its copy moved to draft from the open menu, then Hide tab: the hide lands in draft whichever copy the menu opened from and whatever the drag order; the flyout's Show when folded and Move to rows speak for the moved copy too", () => {
  // round 1's live click resolved the copy's section as the FIRST remaining holder in tagOrder after a move, so on a session under
  // two tags the hide went to a group the user never touched (archived) and the moved copy stayed shown, and which group depended
  // on the drag order. The section is tracked now (copyNow), written by the move; the flyout's own rows read the same computation
  const DRAFT: SectionRef = { name: "draft", localId: "g3" };
  const draft = { id: "g3", name: "draft", color: "#7aa2f7", members: [] as string[] };
  const V3 = { ...V_API_BOTH, tags: [...V_API_BOTH.tags, draft], seq: 5 };
  const V3_DRAG = { ...V3, tags: [V3.tags[0], V3.tags[2], V3.tags[1]] };   // draft between the two holders in tagOrder
  const hooks = menuHooks();
  const rowOf = (menu: FakeEl) => menu.children.find((it) => it.has("ctx-item-hide"))!;
  const run = (views: typeof V3, copy: "infra" | "archived") => withStore(() => {
    hooks.views = views; hooks.writes = [];
    const api = liftShowTabMenu()(hooks);
    const menu = api.open("api", copy);
    const row = rowOf(menu);
    assert.match(row.sub()!, new RegExp("\\b" + copy + "\\b"), `the row was built for the ${copy} copy`);
    moveVia(menu, "draft");
    const other = copy === "infra" ? "archived" : "infra";
    assert.deepEqual(viewTagUnion(hooks.views as typeof V3).filter((g) => g.members.includes("api")).map((g) => g.name).sort(), [other, "draft"].sort(), `api under ${other} and draft`);
    // the mechanism first (a failure here is the write's section), the words and the flyout's rows after it, read off the same
    // nodes (the click's dismissal is the page's; nothing here rebuilds the menu)
    row.click();
    assert.deepEqual(hooks.writes.map((w) => w.hidden), [[{ sid: "api", name: "draft", id: "g3" }]], `the hide lands in draft alone (from the ${copy} copy, tagOrder ${views.tags.map((g) => g.name).join(",")})`);
    assert.deepEqual([isHidden(hooks.writes[0], DRAFT, "api"), isHidden(hooks.writes[0], INFRA, "api"), isHidden(hooks.writes[0], ARCHIVED_REF, "api")], [true, false, false]);
    assert.equal(row.sub(), HIDE_SUB("draft"), `the row names draft (from the ${copy} copy)`);
    const fly = flyOf(menu);
    assert.equal(fly.children.find((it) => it.has("ctx-item-pin"))!.sub(), "keep this tab on the strip while draft is folded", "the flyout's Show when folded row speaks for the moved copy");
    assert.deepEqual(fly.children.filter((it) => it.label()?.startsWith("Move to ")).map((it) => it.label()), ["Move to " + copy], "the group left is offered back; the other holder is not a move target of this copy");
  });
  run(V3, "infra");
  run(V3, "archived");
  run(V3_DRAG, "infra");
  run(V3_DRAG, "archived");
});

test("executed: THE COPY'S TAG REMOVED inside the menu (menu review rounds 2 and 3). The x on the copy's own tag takes the Hide tab row off the menu with nothing written unless one holder is left, whose copy the menu then speaks for; with the row away the flyout offers + rows, and an add (a + row, an existing name typed) brings the row back for the group it made and the flyout moves again; removing the other tag leaves the row; a caller naming no copy or the trail's empty copy resolves the same way", () => {
  // round 1 left a dead row after the remove: its words for the group left, its click writing nothing on a one-tag session or, on
  // a two-tag session, hiding the other holder's copy, which the user never touched. Round 2 resolved a named copy to its own
  // group or to nothing, and left the menu inert after a "+ <other>" (the copy the add made had no row, no pin row, and "+"
  // where "Move to" belonged) and for the trail's copy, "", which never resolved. Round 3: own group, else the one remaining
  // holder, else nothing; "" is no copy; an add from no group claims the copy
  const hooks = menuHooks();
  const rowOf = (menu: FakeEl) => menu.children.find((it) => it.has("ctx-item-hide"));
  const xOf = (fly: FakeEl, name: string) => fly.children.find((it) => it.label() === name)!.all().find((n) => n.has("ctx-tag-x") && !n.has("ctx-tag-plus"))!;
  const joinRows = (fly: FakeEl) => fly.children.filter((it) => it.label()?.startsWith("+ ") || it.label()?.startsWith("Move to ")).map((it) => it.label());
  const pinRow = (fly: FakeEl) => fly.children.find((it) => it.has("ctx-item-pin"));
  const typeName = (fly: FakeEl, name: string) => { const inp = fly.all().find((n) => n.has("ctx-tag-input"))!; inp.value = name; for (const fn of inp.listeners.keydown || []) fn({ key: "Enter" }); };
  const holders = () => viewTagUnion(hooks.views as typeof V).filter((g) => g.members.includes("web")).map((g) => g.name);
  withStore(() => {
    const api = liftShowTabMenu()(hooks);
    // R1: web under infra alone; remove infra: the row is gone, no write; the flyout offers "+ infra" and "+ archived" and no pin
    // row. "+ archived" (round 3: any add, not only the tag put back) brings the row back for archived, directly after Notify me;
    // the flyout reads "Move to infra" and pins archived; the row's click hides in archived
    let menu = api.open("web", "infra");
    assert.ok(rowOf(menu));
    let fly = flyOf(menu);
    xOf(fly, "infra").click();
    assert.deepEqual(holders(), [], "web under no tag");
    assert.equal(rowOf(menu), undefined, "the row left with the copy");
    assert.equal(hooks.writes.length, 0, "nothing written");
    assert.deepEqual(joinRows(fly), ["+ infra", "+ archived"], "no copy to move: add rows");
    assert.equal(pinRow(fly), undefined, "and nothing to pin");
    fly.children.find((it) => it.label() === "+ archived")!.click();
    assert.deepEqual(holders(), ["archived"]);
    assert.equal(rowOf(menu)?.sub(), HIDE_SUB("archived"), "the add is the move: the row is back for the group the add made (round 2: the menu stayed inert)");
    assert.equal(menu.children.indexOf(rowOf(menu)!), menu.children.findIndex((it) => it.label() === "Notify me") + 1, "directly after Notify me");
    assert.deepEqual(joinRows(fly), ["Move to infra"], "and the flyout moves again");
    assert.equal(pinRow(fly)?.sub(), "keep this tab on the strip while archived is folded", "and pins the copy where it is");
    rowOf(menu)!.click();
    assert.deepEqual(hooks.writes.map((w) => w.hidden), [[{ sid: "web", name: "archived", id: "g2" }]], "the click hides the copy the add made");
    // R1b: the same through the input: an existing name typed while the copy has no group claims it; typed while the copy has a
    // group it is an add, and the row stays with the copy
    hooks.views = V; hooks.writes = []; writeTabGroups(d);   // R1's hide out of the store
    menu = api.open("web", "infra");
    fly = flyOf(menu);
    xOf(fly, "infra").click();
    assert.equal(rowOf(menu), undefined);
    typeName(fly, "archived");
    assert.deepEqual(holders(), ["archived"]);
    assert.equal(rowOf(menu)?.sub(), HIDE_SUB("archived"), "an existing name typed from no group: the copy's new group");
    hooks.views = V;
    menu = api.open("web", "infra");
    fly = flyOf(menu);
    typeName(fly, "archived");
    assert.deepEqual(holders(), ["infra", "archived"]);
    assert.equal(rowOf(menu)?.sub(), HIDE_SUB("infra"), "typed while the copy has a group: an add; the row stays with the copy");
    assert.equal(hooks.writes.length, 0);
    // R2: api under infra and archived, the menu on the infra copy; remove infra: ONE holder is left, so the menu speaks for that copy
    // (round 3; round 2 had no row here, round 1 had the same answer by accident, as the first holder in tagOrder), no write; the
    // flyout offers the tag back as a move and pins archived
    hooks.views = V_API_BOTH;
    menu = api.open("api", "infra");
    assert.equal(rowOf(menu)!.sub(), HIDE_SUB("infra"));
    fly = flyOf(menu);
    xOf(fly, "infra").click();
    assert.equal(rowOf(menu)?.sub(), HIDE_SUB("archived"), "one copy left: the menu speaks for it");
    assert.equal(hooks.writes.length, 0);
    assert.deepEqual(joinRows(fly), ["Move to infra"]);
    assert.equal(pinRow(fly)?.sub(), "keep this tab on the strip while archived is folded");
    // R2b: api under infra, archived and qa, the menu on the infra copy; remove infra: TWO holders left, which copy? none: no row,
    // "+ infra", no pin row; remove archived too: one left, qa, and the row is back for it
    const qa = { id: "g4", name: "qa", color: "#7aa2f7", members: ["api"] };
    hooks.views = { ...V_API_BOTH, tags: [...V_API_BOTH.tags, qa], seq: 5 };
    menu = api.open("api", "infra");
    fly = flyOf(menu);
    xOf(fly, "infra").click();
    assert.equal(rowOf(menu), undefined, "two holders left and no copy of its own: no row (which copy would it hide?)");
    assert.deepEqual(joinRows(fly), ["+ infra"], "no copy to move");
    assert.equal(pinRow(fly), undefined);
    xOf(fly, "archived").click();
    assert.equal(rowOf(menu)?.sub(), HIDE_SUB("qa"), "down to one holder: that copy");
    assert.equal(hooks.writes.length, 0);
    // R3: removing the OTHER tag leaves the copy's row as it was
    hooks.views = V_API_BOTH;
    menu = api.open("api", "infra");
    const row = rowOf(menu)!;
    fly = flyOf(menu);
    xOf(fly, "archived").click();
    assert.deepEqual([rowOf(menu), row.sub()], [row, HIDE_SUB("infra")], "the copy's own group untouched: the row stands");
    // R4: a caller naming no copy (an older one) on a two-holder session: no row (round 3; the first holder in tagOrder before, a
    // copy the user never touched); one holder left after a remove: that copy
    hooks.views = V_API_BOTH;
    menu = api.open("api");
    assert.equal(rowOf(menu), undefined, "no copy named, two holders: none");
    fly = flyOf(menu);
    assert.deepEqual(joinRows(fly), [], "nothing to move to or add: both tags hold the session");
    xOf(fly, "infra").click();
    assert.equal(rowOf(menu)?.sub(), HIDE_SUB("archived"), "one holder left: that copy");
    assert.equal(hooks.writes.length, 0);
    // R5: the untagged trail's copy. The strip writes "" as the copy of a tab behind the trail's head (planStrip's null group), and
    // the menu reads it as no copy (round 3; round 2 read it as a copy named "" that could never resolve, so the menu stayed inert
    // for the copy a "+ infra" made): no row; "+ infra" brings the row for infra, the flyout reads "Move to archived" and pins infra;
    // the "+" beside Move to archived adds a second tag and the row stays with the copy
    hooks.views = V;
    menu = api.open("loose", "");
    assert.equal(rowOf(menu), undefined, "no tag, no row");
    fly = flyOf(menu);
    assert.deepEqual(joinRows(fly), ["+ infra", "+ archived"]);
    assert.equal(pinRow(fly), undefined);
    fly.children.find((it) => it.label() === "+ infra")!.click();
    assert.equal(rowOf(menu)?.sub(), HIDE_SUB("infra"), "the add is the move: the trail's tab has a copy in infra now, and the menu speaks for it");
    assert.deepEqual(joinRows(fly), ["Move to archived"]);
    assert.equal(pinRow(fly)?.sub(), "keep this tab on the strip while infra is folded");
    fly.children.find((it) => it.label() === "Move to archived")!.all().find((n) => n.has("ctx-tag-plus"))!.click();
    assert.deepEqual(viewTagUnion(hooks.views as typeof V).filter((g) => g.members.includes("loose")).map((g) => g.name), ["infra", "archived"]);
    assert.equal(rowOf(menu)?.sub(), HIDE_SUB("infra"), "a second tag added: the copy stayed in infra");
    // R5b: a NEW tag typed for the trail's copy claims it too: the copy is under the pending tag (no row until the ack, which re-dresses
    // the menu: N5 of the rename test), and a "+ archived" after it adds without moving the claim, so the row stays away
    hooks.views = V;
    menu = api.open("loose", "");
    fly = flyOf(menu);
    typeName(fly, "qa");
    assert.deepEqual(viewTagUnion(hooks.views as typeof V).filter((g) => g.members.includes("loose")).map((g) => [g.name, g.pending]), [["qa", true]], "the create in flight holds the session");
    assert.equal(rowOf(menu), undefined, "a pending home: no row");
    fly.children.find((it) => it.label() === "+ archived")!.click();
    assert.equal(rowOf(menu), undefined, "the copy is the pending tag's: a further add does not move the claim, and the row waits for the ack");
    assert.equal(hooks.writes.length, 0, "no hide written by any of it");
    // R6 (round 4): the one-holder fallback LATCHES. After the x on the copy's tag on a two-tag session the menu speaks for the one
    // holder left, and that holder is the copy from then on: every add from there is an add (the copy has a group), so the row stays,
    // the pin row stays and the flyout keeps its Move to rows. Before, copyNow still named the removed tag, so claimIfLoose took every
    // add for a move of the claim: the + beside Move to a third tag took the row and the pin row away and the flyout read "+ <removed>";
    // an existing name typed moved the row to the typed tag; a new tag typed took the row away; the + beside Move to the removed tag
    // jumped the row back to it. A caller naming no copy on a one-holder session lost the row the same way.
    const apiHolders = () => viewTagUnion(hooks.views as typeof V).filter((g) => g.members.includes("api")).map((g) => g.name);
    const plusOf = (f: FakeEl, label: string) => f.children.find((it) => it.label() === label)!.all().find((n) => n.has("ctx-tag-plus"))!;
    const qaEmpty = { id: "g5", name: "qa", color: "#7aa2f7", members: [] as string[] };
    const V3 = { ...V_API_BOTH, tags: [...V_API_BOTH.tags, qaEmpty], seq: 6 };
    const settled = (what: string) => {
      assert.equal(rowOf(menu)?.sub(), HIDE_SUB("archived"), what + ": the row stays with the copy the one holder became");
      assert.equal(pinRow(fly)?.sub(), "keep this tab on the strip while archived is folded", what + ": and the pin row speaks for it");
      assert.ok(joinRows(fly).every((l) => l!.startsWith("Move to ")), what + ": the flyout keeps its Move to rows: " + JSON.stringify(joinRows(fly)));
    };
    // (1) the + beside Move to a third tag, then the Hide click writes the copy the menu spoke for
    hooks.views = V3; hooks.writes = [];
    menu = api.open("api", "infra"); fly = flyOf(menu);
    xOf(fly, "infra").click();
    assert.equal(rowOf(menu)?.sub(), HIDE_SUB("archived"));
    assert.deepEqual(joinRows(fly), ["Move to infra", "Move to qa"]);
    plusOf(fly, "Move to qa").click();
    assert.deepEqual(apiHolders(), ["archived", "qa"], "an add: the session keeps archived");
    settled("(1) the + beside Move to qa");
    assert.deepEqual(joinRows(fly), ["Move to infra"]);
    rowOf(menu)!.click();
    assert.deepEqual(hooks.writes.map((w) => w.hidden.filter((h) => h.sid === "api")), [[{ sid: "api", name: "archived", id: "g2" }]], "the click hides the copy the menu spoke for");
    writeTabGroups(d);   // (1)'s hide out of the store
    // (2) an existing name typed
    hooks.views = V3; hooks.writes = [];
    menu = api.open("api", "infra"); fly = flyOf(menu);
    xOf(fly, "infra").click();
    typeName(fly, "qa");
    assert.deepEqual(apiHolders(), ["archived", "qa"]);
    settled("(2) an existing name typed");
    // (3) a new tag typed: an add; the pending tag does not take the claim
    hooks.views = V3;
    menu = api.open("api", "infra"); fly = flyOf(menu);
    xOf(fly, "infra").click();
    typeName(fly, "draft2");
    assert.deepEqual(viewTagUnion(hooks.views as typeof V).filter((g) => g.members.includes("api")).map((g) => [g.name, !!g.pending]), [["archived", false], ["draft2", true]]);
    settled("(3) a new tag typed");
    // (4) the + beside Move to the removed tag: an add; the copy stays archived's
    hooks.views = V3;
    menu = api.open("api", "infra"); fly = flyOf(menu);
    xOf(fly, "infra").click();
    plusOf(fly, "Move to infra").click();
    assert.deepEqual(apiHolders(), ["infra", "archived"]);
    settled("(4) the + beside Move to infra");
    // (5) a caller naming no copy on a one-holder session, then the + beside Move to: the one holder became the copy
    hooks.views = V;
    menu = api.open("web"); fly = flyOf(menu);
    assert.equal(rowOf(menu)?.sub(), HIDE_SUB("infra"));
    plusOf(fly, "Move to archived").click();
    assert.deepEqual(holders(), ["infra", "archived"]);
    assert.equal(rowOf(menu)?.sub(), HIDE_SUB("infra"), "(5) no copy named, one holder, then the + beside Move to archived: the holder became the copy, the add is an add, the row stays");
    assert.equal(pinRow(fly)?.sub(), "keep this tab on the strip while infra is folded");
    assert.equal(hooks.writes.length, 0, "no hide written by (2) to (5)");
  });
});

test("executed: THE MENU FOLLOWS THE PUSH (menu review round 4). A views arrival while the menu is open re-dresses it in the same event: the copy's tag pushed off a two-tag session leaves the row naming the one holder left, the Tags row's sub-line and the flyout's rows follow, nothing is written, and the click then hides the copy the row names and no other; pushed out of every group, the row leaves and the click writes nothing; a frame that changed nothing the flyout shows leaves its rows and the typed text alone, and one that did carries the text across the rebuild", () => {
  // before: refreshHideRow ran at build and from the flyout's own edits only; the tabOrder frame handler and onViewsAck reached
  // neither, so a push that took infra off api (under infra and archived) left the row reading infra while the click's resolution
  // had moved to archived (0d39f5a8's guard then wrote nothing: C4 in THE CLICK IS LIVE, which still executes the arrival without
  // the hook). Now the arrival runs tabMenuViewsHook: the row's refresh, the Tags row's sub-line, and the flyout's rows when the
  // frame changed what they show
  const hooks = menuHooks();
  const rowOf = (menu: FakeEl) => menu.children.find((it) => it.has("ctx-item-hide"));
  const tagsSub = (menu: FakeEl) => menu.children.find((it) => it.has("ctx-item-tags"))!.sub();
  const joinRows = (fly: FakeEl) => fly.children.filter((it) => it.label()?.startsWith("+ ") || it.label()?.startsWith("Move to ")).map((it) => it.label());
  const pinRow = (fly: FakeEl) => fly.children.find((it) => it.has("ctx-item-pin"));
  const inputOf = (fly: FakeEl) => fly.all().find((n) => n.has("ctx-tag-input"))!;
  const sameNodes = (a: FakeEl[], b: FakeEl[]) => a.length === b.length && a.every((n, i) => n === b[i]);
  withStore(() => {
    const api = liftShowTabMenu()(hooks);
    // P1: api under infra and archived, the menu on the infra copy, the flyout open; the push takes infra off api
    hooks.views = V_API_BOTH;
    let menu = api.open("api", "infra");
    let fly = flyOf(menu);
    assert.equal(rowOf(menu)?.sub(), HIDE_SUB("infra"));
    assert.equal(tagsSub(menu), "infra · archived");
    api.push({ ...V_API_BOTH, tags: [{ ...V_API_BOTH.tags[0], members: ["web", "tests"] }, V_API_BOTH.tags[1]], seq: 5 });
    assert.equal(rowOf(menu)?.sub(), HIDE_SUB("archived"), "the push re-dressed the row for the one holder left (before: it read infra until a flyout edit or the click)");
    assert.equal(tagsSub(menu), "archived", "the Tags row's sub-line follows");
    assert.deepEqual([rowOf(menu)?.title, menu.children.find((it) => it.has("ctx-item-tags"))!.title], [HIDE_SUB("archived"), "archived"], "and both tooltips (round 5)");
    assert.deepEqual(joinRows(fly), ["Move to infra"], "the flyout's rows follow: infra is a move again");
    assert.equal(pinRow(fly)?.sub(), "keep this tab on the strip while archived is folded", "and the pin row speaks for the copy the menu now speaks for");
    assert.equal(hooks.writes.length, 0, "the push wrote nothing");
    rowOf(menu)!.click();
    assert.deepEqual(hooks.writes.map((w) => w.hidden), [[{ sid: "api", name: "archived", id: "g2" }]], "the click hides the copy the row names, and no other");
    writeTabGroups(d);
    // P2: web under infra alone, the flyout open; the push takes web out of every group: the row leaves, the Tags row says none, the
    // flyout offers + rows and no pin row; a click on the row that left writes nothing
    hooks.views = V; hooks.writes = [];
    menu = api.open("web", "infra");
    fly = flyOf(menu);
    const row = rowOf(menu)!;
    api.push({ ...V, tags: [{ ...V.tags[0], members: ["api", "tests"] }, V.tags[1]], seq: 4 });
    assert.equal(rowOf(menu), undefined, "no group left: the row left the menu");
    assert.ok(tagsSub(menu)!.startsWith("none yet"), "the Tags row says so");
    assert.deepEqual(joinRows(fly), ["+ infra", "+ archived"]);
    assert.equal(pinRow(fly), undefined);
    row.click();
    assert.equal(hooks.writes.length, 0, "nothing to hide, nothing written");
    // P3: a frame that changed nothing the flyout shows (another session left archived; the seq bumped): the rows are the same nodes
    // and the text typed into New tag… stands (the ack path's rule: never a rebuild that throws typed text away)
    hooks.views = V; hooks.writes = [];
    menu = api.open("web", "infra");
    fly = flyOf(menu);
    const rowsBefore = fly.children.slice();
    inputOf(fly).value = "qa-";
    api.push({ ...V, tags: [V.tags[0], { ...V.tags[1], members: ["old1"] }], seq: 4 });
    assert.ok(sameNodes(fly.children, rowsBefore), "not rebuilt: the same row nodes");
    assert.equal(inputOf(fly).value, "qa-", "the typed text stands");
    assert.equal(rowOf(menu)?.sub(), HIDE_SUB("infra"), "the row re-read and unchanged");
    // P4: a frame that changed what the flyout shows (a third tag appeared) while text is typed and the input is focused with the caret
    // inside it: the rows are rebuilt in front of the SAME input node (round 5), so its text, caret, selection and focus stand with no
    // restore (round 4 built a new input, copied the value back and called focus(), which put the caret at the end); the foot stays too
    const inp0 = inputOf(fly);
    inp0.focus(); inp0.setSelectionRange(1, 2, "backward");
    const focusCalls = FakeEl.focusCalls;
    const footBefore = fly.children.filter((it) => it.has("ctx-item-configtags") || it.has("ctx-item-newtag"));
    assert.equal(footBefore.length, 2);
    api.push({ ...V, tags: [...V.tags, { id: "g6", name: "draft", color: "#f0f", members: [] as string[] }], seq: 5 });
    assert.ok(!sameNodes(fly.children, rowsBefore), "rebuilt");
    assert.deepEqual(joinRows(fly), ["Move to archived", "Move to draft"], "the new tag's row is there");
    assert.equal(inputOf(fly), inp0, "the same input node (round 4: a new one each build)");
    assert.equal(inp0.value, "qa-", "the typed text stands");
    assert.deepEqual([inp0.selectionStart, inp0.selectionEnd, inp0.selectionDirection], [1, 2, "backward"], "the selection stands");
    assert.equal(FakeEl.focused, inp0, "still the focused element: never removed from the page");
    assert.equal(FakeEl.focusCalls, focusCalls, "no focus() call: nothing to restore");
    assert.ok(fly.children.filter((it) => it.has("ctx-item-configtags") || it.has("ctx-item-newtag")).every((n, i) => n === footBefore[i]), "the foot (the input's row, Configure tags…) stands, the same nodes");
    assert.ok(fly.children.indexOf(inp0.parent!) > fly.children.findIndex((it) => it.label() === "Move to draft"), "the new row went in above the input");
    assert.equal(hooks.writes.length, 0);
    // P5: after the menu is dismissed, a push touches nothing: the hook is cleared with the menu (the real dismissTabMenu is pinned to
    // clear it; the stub here mirrors that line)
    const d0 = hooks.dismissed;
    rowOf(menu)!.click();
    assert.equal(hooks.dismissed, d0 + 1);
    const wordsAfterClick = rowOf(menu)!.sub();
    api.push({ ...V, tags: [{ ...V.tags[0], members: ["api", "tests"] }, V.tags[1]], seq: 6 });
    assert.equal(rowOf(menu)!.sub(), wordsAfterClick, "a closed menu is not re-dressed");
    // P6 (round 5): THE RESOLUTION IS A PURE FUNCTION of the right-clicked copy and the views. api under infra and archived, the menu
    // on the infra copy, the flyout open: the push takes infra off (the row speaks for archived, the one holder left) and a later push
    // puts it back (a remove the kernel refused, another pane's add): the row, the Tags row and the flyout speak for infra again, the
    // copy the user right-clicked, and the click hides infra. Round 4 latched archived at the first resolution and hid archived here
    hooks.views = V_API_BOTH; hooks.writes = []; writeTabGroups(d);
    menu = api.open("api", "infra");
    fly = flyOf(menu);
    const V_OFF = { ...V_API_BOTH, tags: [{ ...V_API_BOTH.tags[0], members: ["web", "tests"] }, V_API_BOTH.tags[1]], seq: 5 };
    api.push(V_OFF);
    assert.equal(rowOf(menu)?.sub(), HIDE_SUB("archived"), "the tag away: the one holder left speaks for the copy");
    assert.deepEqual(joinRows(fly), ["Move to infra"]);
    api.push({ ...V_API_BOTH, seq: 6 });
    assert.equal(rowOf(menu)?.sub(), HIDE_SUB("infra"), "the tag back: the copy the user right-clicked again (round 4 stayed on archived)");
    assert.equal(tagsSub(menu), "infra · archived");
    assert.deepEqual(joinRows(fly), [], "both tags hold the session: nothing to move to");
    assert.equal(pinRow(fly)?.sub(), "keep this tab on the strip while infra is folded", "the pin row speaks for infra again");
    rowOf(menu)!.click();
    assert.deepEqual(hooks.writes.map((w) => w.hidden), [[{ sid: "api", name: "infra", id: "g1" }]], "the click hides the copy the row names, infra (round 4 hid archived)");
    writeTabGroups(d);
    // P6b: the same with a click after EACH resolution: away, the click hides archived; a fresh menu, away then back, the click hides infra
    hooks.views = V_API_BOTH; hooks.writes = [];
    menu = api.open("api", "infra");
    api.push(V_OFF);
    rowOf(menu)!.click();
    assert.deepEqual(hooks.writes.map((w) => w.hidden), [[{ sid: "api", name: "archived", id: "g2" }]], "away: the click hides the holder the row names");
    writeTabGroups(d);
    hooks.views = V_API_BOTH; hooks.writes = [];
    menu = api.open("api", "infra");
    api.push(V_OFF);
    api.push({ ...V_API_BOTH, seq: 7 });
    rowOf(menu)!.click();
    assert.deepEqual(hooks.writes.map((w) => w.hidden), [[{ sid: "api", name: "infra", id: "g1" }]], "back: the click hides infra");
    writeTabGroups(d);
    // P6c: the user's own x on the copy's tag, then the push that puts the tag back (the kernel refused the remove): the copy is the
    // right-clicked one again, since a gesture that removes aims nothing; an ADD gesture from the fallback aims the ref at the holder
    // (R6 in THE COPY'S TAG REMOVED), and that one stands through a later restore
    hooks.views = V_API_BOTH; hooks.writes = [];
    menu = api.open("api", "infra");
    fly = flyOf(menu);
    fly.children.find((it) => it.label() === "infra")!.all().find((n) => n.has("ctx-tag-x") && !n.has("ctx-tag-plus"))!.click();
    assert.equal(rowOf(menu)?.sub(), HIDE_SUB("archived"), "the x: the one holder left");
    api.push({ ...V_API_BOTH, seq: 8 });
    assert.equal(rowOf(menu)?.sub(), HIDE_SUB("infra"), "the remove refused, the tag back: the right-clicked copy again");
    rowOf(menu)!.click();
    assert.deepEqual(hooks.writes.map((w) => w.hidden), [[{ sid: "api", name: "infra", id: "g1" }]]);
    writeTabGroups(d);
    const qaEmpty = { id: "g5", name: "qa", color: "#7aa2f7", members: [] as string[] };
    const V3 = { ...V_API_BOTH, tags: [...V_API_BOTH.tags, qaEmpty], seq: 9 };
    hooks.views = V3; hooks.writes = [];
    menu = api.open("api", "infra");
    fly = flyOf(menu);
    fly.children.find((it) => it.label() === "infra")!.all().find((n) => n.has("ctx-tag-x") && !n.has("ctx-tag-plus"))!.click();
    fly.children.find((it) => it.label() === "Move to qa")!.all().find((n) => n.has("ctx-tag-plus"))!.click();   // the add aims the ref at archived
    assert.equal(rowOf(menu)?.sub(), HIDE_SUB("archived"));
    api.push({ ...V3, tags: [{ ...V3.tags[0], members: ["web", "api", "tests"] }, V3.tags[1], { ...qaEmpty, members: ["api"] }], seq: 10 });   // infra back from elsewhere
    assert.equal(rowOf(menu)?.sub(), HIDE_SUB("archived"), "the user's add aimed the copy at archived: infra coming back does not move it (a gesture, not a resolution, wrote the ref)");
    rowOf(menu)!.click();
    assert.deepEqual(hooks.writes.map((w) => w.hidden), [[{ sid: "api", name: "archived", id: "g2" }]]);
  });
});

test("executed: THE STORE'S OWN EVENTS AND THE CAPS FRAME REACH THE MENU (menu review rounds 5 and 6). Another pane's Hide, delivered by render.ts's own tab-groups store listeners through the one notifier, flips the open menu's row to Show tab and its click shows; a Group tabs by tag switch off takes the row away and turns the open flyout's Move to rows into + rows, on again brings both back; another pane's pin re-dresses the pin row; the pin row's own write, whose event runs the hook inside the write, rebuilds the flyout for the pin before the row's own build and keeps the typed text; onKernelCaps runs the notifier once the writes in flight are dropped or the kept blob adopted, and not when nothing shown changed", () => {
  // round 4 ran the hook from the two views-arrival paths alone: a hide or show written from another pane (the storage event), a
  // grouping flip (TABGROUPS_EVENT) and a reconnect that dropped an edit in flight (onKernelCaps) left the open menu stale, though the
  // guide said the row follows changes from another pane. Round 5: one notifier, viewsChanged, called from every site that changes what
  // the strip reads. Round 6: the listeners themselves are lifted from render.ts onto the harness window and the events are fired
  // (round 5's harness called the hook itself, so these cases passed against listeners that never called the notifier), and the
  // flyout's signature lists every input its rows read (the home resolution and the pin bit with the unions), so a store event that
  // changes what the rows show rebuilds an open flyout; onKernelCaps is lifted and run
  const hooks = menuHooks();
  const rowOf = (menu: FakeEl) => menu.children.find((it) => it.has("ctx-item-hide"));
  const pinRow = (fly: FakeEl) => fly.children.find((it) => it.has("ctx-item-pin"));
  const inputOf = (fly: FakeEl) => fly.all().find((n) => n.has("ctx-tag-input"))!;
  const joinRows = (fly: FakeEl) => fly.children.filter((it) => it.label()?.startsWith("+ ") || it.label()?.startsWith("Move to ")).map((it) => it.label());
  const sameNodes = (a: FakeEl[], b: FakeEl[]) => a.length === b.length && a.every((n, i) => n === b[i]);
  // the menu's own writes dispatch TABGROUPS_EVENT inside writeTabGroups (on the global window, which node has not): the stub fires it on
  // the harness window after the real write, so the module's listener runs inside the write as it does on the page
  hooks.mods.writeTabGroups = (st: TabGroupsState) => { writeTabGroups(st); hooks.window!.fire(TABGROUPS_EVENT); };
  withStore(() => {
    const api = liftShowTabMenu()(hooks);
    const win = hooks.window!;
    assert.deepEqual([win.count("storage"), win.count(TABGROUPS_EVENT), win.count("media:change")], [1, 1, 1], "render.ts's three listeners are on the harness window");
    const storage = () => win.fire("storage", { key: TABGROUPS_KEY });   // a sibling pane's write, as the browser delivers it
    // E1: another pane hid api in infra (its write, then the storage event, which the module's listener answers with the strip's render
    // and the notifier): the row reads Show tab, and its click shows
    let menu = api.open("api", "infra");
    let row = rowOf(menu)!;
    assert.deepEqual([row.label(), row.sub()], ["Hide tab", HIDE_SUB("infra")]);
    writeTabGroups(setHidden(readTabGroups(unions), INFRA, "api", true));   // the other pane's Hide
    const r1 = hooks.renders;
    storage();
    assert.equal(hooks.renders, r1 + 1, "the listener renders the strip");
    assert.deepEqual([row.label(), row.sub(), row.icon()!.has("off")], ["Show tab", "back on the strip in infra", true], "and runs the notifier: the row follows the other pane's hide (round 4: it read Hide tab until a views push)");
    assert.equal(rowOf(menu), row, "the same node");
    row.click();
    assert.equal(hooks.writes.length, 1);
    assert.deepEqual(hooks.writes[0].hidden, [], "the click shows: hidden false for the copy");
    assert.equal(isHidden(readTabGroups(unions), INFRA, "api"), false);
    win.fire("storage", { key: "romp:other" });
    assert.equal(hooks.renders, r1 + 2, "a storage event under another key is not the store's: no render (the listener reads the key)");
    // E2: another pane's Show, the same way
    hooks.writes = [];
    writeTabGroups(setHidden(readTabGroups(unions), INFRA, "api", true));
    menu = api.open("api", "infra");
    row = rowOf(menu)!;
    assert.equal(row.label(), "Show tab");
    writeTabGroups(setHidden(readTabGroups(unions), INFRA, "api", false));   // the other pane's Show
    storage();
    assert.equal(row.label(), "Hide tab", "the row follows the other pane's show");
    row.click();
    assert.deepEqual(hooks.writes.map((w) => w.hidden), [[{ sid: "api", name: "infra", id: "g1" }]], "and the click hides");
    writeTabGroups(d);
    // E3: Group tabs by tag switched off in another pane (the storage event) with the flyout open: the row leaves the menu and the
    // flyout's rows follow (no copy to move: + rows, no pin row; round 6, the home resolution being in flySig: round 5's flyout kept
    // Move to archived, whose click then dropped infra from web while the strip had no sections); on again: both are back
    hooks.writes = [];
    menu = api.open("web", "infra");
    row = rowOf(menu)!;
    let fly = flyOf(menu);
    assert.deepEqual([joinRows(fly), pinRow(fly)?.sub()], [["Move to archived"], "keep this tab on the strip while infra is folded"]);
    writeTabGroups({ ...readTabGroups(unions), on: false });
    storage();
    assert.equal(rowOf(menu), undefined, "grouping off: no hide applies, the row left (before: a dead row until a views push)");
    assert.deepEqual([joinRows(fly), pinRow(fly)], [["+ archived"], undefined], "the flyout followed: an add, not a move, and no pin row (round 6)");
    writeTabGroups({ ...readTabGroups(unions), on: true });
    storage();
    assert.equal(rowOf(menu)?.sub(), HIDE_SUB("infra"), "grouping on again: the row is back");
    assert.equal(rowOf(menu), row, "the same node");
    assert.deepEqual([joinRows(fly), pinRow(fly)?.sub()], [["Move to archived"], "keep this tab on the strip while infra is folded"], "and the flyout's Move to and pin rows with it");
    writeTabGroups({ ...readTabGroups(unions), on: false });
    storage();
    assert.equal(rowOf(menu), undefined);
    const dOff = hooks.dismissed;
    row.click();
    assert.deepEqual([hooks.writes.length, hooks.dismissed], [0, dOff + 1], "a click on the row that left (unreachable on the page) writes nothing and dismisses, the no-home branch");
    writeTabGroups({ ...readTabGroups(unions), on: true });
    // E3b (round 6): another pane pins web in infra: the pin row's words and mark follow (the pin bit is in flySig; before, the row read
    // 'keep this tab...' with no mark while isPinned was true, and its click then wrote the pin OFF)
    menu = api.open("web", "infra");
    fly = flyOf(menu);
    assert.deepEqual([pinRow(fly)!.sub(), pinRow(fly)!.has("current")], ["keep this tab on the strip while infra is folded", false]);
    const rowsB = fly.children.slice();
    writeTabGroups(setPinned(readTabGroups(unions), INFRA, "web", true));   // the other pane's pin
    storage();
    assert.deepEqual([pinRow(fly)!.sub(), pinRow(fly)!.has("current")], ["stays on the strip while infra is folded", true], "the other pane's pin re-dressed the pin row");
    assert.ok(!sameNodes(fly.children, rowsB), "the rows were rebuilt");
    assert.equal(rowOf(menu)?.sub(), HIDE_SUB("infra"), "the Hide tab row stands");
    writeTabGroups(d);
    // E4: the pin row's OWN write. TABGROUPS_EVENT is dispatched inside writeTabGroups, so the module's listener runs the strip's render and
    // the notifier BEFORE the click handler's own build(): the render stub reads the pin row's words before the hook (the old words), and a
    // probe listener installed after the module's reads them after it, still inside the write (the new words: the hook rebuilt the flyout,
    // the pin bit being in flySig since round 6); the handler's build() is a second pass over the same blob. The typed New tag text stands
    // through both, the input being one node (round 5's E4 ran the hook before the click, not inside its write, and asserted no rebuild)
    hooks.writes = [];
    menu = api.open("web", "infra");
    row = rowOf(menu)!;
    fly = flyOf(menu);
    const inp = inputOf(fly);
    inp.value = "qa-";
    let atRender: string | undefined, afterListener: string | undefined;
    hooks.onRender = () => { atRender = pinRow(fly)!.sub(); };
    win.addEventListener(TABGROUPS_EVENT, () => { afterListener = pinRow(fly)!.sub(); });
    pinRow(fly)!.click();
    assert.equal(hooks.writes.length, 1, "the pin's write");
    assert.equal(atRender, "keep this tab on the strip while infra is folded", "the strip's render ran inside the write, before the hook: the old words");
    assert.equal(afterListener, "stays on the strip while infra is folded", "the hook ran inside the write too and rebuilt the flyout for the pin, before the handler's own build()");
    assert.deepEqual([pinRow(fly)!.sub(), pinRow(fly)!.has("current")], ["stays on the strip while infra is folded", true], "the pin row shows the pin");
    assert.equal(inputOf(fly), inp, "the New tag input is the same node");
    assert.equal(inp.value, "qa-", "and the typed text stands through both builds");
    assert.equal(rowOf(menu)?.sub(), HIDE_SUB("infra"), "the Hide tab row stands");
    hooks.onRender = undefined;
  });
  // E5: onKernelCaps itself, lifted from render.ts and run over stubs with a counter for the notifier: a caps frame with a write in
  // flight drops it and notifies; one that adopts the kept blob notifies; one with nothing in flight and nothing adopted returns first
  const a = RENDER.indexOf("function onKernelCaps(");
  const b = RENDER.indexOf("\n}\n", a) + 3;
  assert.ok(a > 0 && b > a);
  const js = requireCjs("esbuild").transformSync(RENDER.slice(a, b), { loader: "ts" }).code;
  type CapsHooks = { writes: number; rejected: unknown; adopts: boolean; changed: number; renders: number; toasts: number; synced: number; peeks: number };
  const run = (h: CapsHooks) => {
    const prelude = `
      const H = HOOKS;
      let kernelCaps = new Set(), rejectedViews = H.rejected, announcedViewsSeq = null, pendingSessionViews = {}, activeId = "web";
      let viewsWrites = Array.from({ length: H.writes }, (_, i) => ({ id: "w" + i }));
      const capsAdopts = () => H.adopts, adoptBase = () => {}, announcedSeq = () => null;
      const warnToast = () => { H.toasts++; }, syncNewTagInput = () => { H.synced++; }, assertPeekFor = () => { H.peeks++; }, renderTabs = () => { H.renders++; };
      const viewsChanged = () => { H.changed++; };
    `;
    new Function("HOOKS", prelude + js + "\nonKernelCaps({ caps: [], viewsSeq: 3 });")(h);
    return h;
  };
  const inflight = run({ writes: 1, rejected: null, adopts: false, changed: 0, renders: 0, toasts: 0, synced: 0, peeks: 0 });
  assert.deepEqual([inflight.changed, inflight.toasts, inflight.synced, inflight.peeks, inflight.renders], [1, 1, 1, 1, 1], "a write in flight dropped: the notifier runs once, with the toast, the input's re-arm, the peek and the render (round 4: 0)");
  const adopted = run({ writes: 0, rejected: { seq: 3 }, adopts: true, changed: 0, renders: 0, toasts: 0, synced: 0, peeks: 0 });
  assert.deepEqual([adopted.changed, adopted.toasts, adopted.renders], [1, 0, 1], "the kept blob adopted: the notifier runs once, no toast");
  const quiet = run({ writes: 0, rejected: null, adopts: false, changed: 0, renders: 0, toasts: 0, synced: 0, peeks: 0 });
  assert.deepEqual([quiet.changed, quiet.renders], [0, 0], "nothing in flight, nothing adopted: the frame returns before the notifier and the render");
});

test("executed: A RENAME PUSHED WHILE THE MENU IS OPEN (menu review rounds 4 and 6). The copy is tracked as a section ref (its tag's local id and name), so a rename of its tag pushed while the menu is open keeps the row on the same copy: the row names the new name, the Hide click writes for that tag under it, and the flyout keeps its Move to and Show when folded rows; the same on a one-tag session, by the id alone when the row was not re-dressed, and with a new tag under the old name beside the rename; the other tag renamed leaves the row; a tag claimed at its create resolves through the ack that replaces its placeholder id; a remote-only group's rename loses the copy (name-matched: the one limit); a remote-only union under the old name beside the rename never takes the copy, in either drag order (the id pass runs first)", () => {
  // before: copyNow was the tag's NAME, so a pushed rename (same id, new name) on a session under two tags made homeNow find no held
  // union of that name, and the fallback did not apply (two holders): the click dismissed and wrote nothing, and the flyout's next
  // build had no Move to and no Show when folded rows. On a one-tag session the fallback hid the defect
  const hooks = menuHooks();
  const rowOf = (menu: FakeEl) => menu.children.find((it) => it.has("ctx-item-hide"));
  const tagsSub = (menu: FakeEl) => menu.children.find((it) => it.has("ctx-item-tags"))!.sub();
  const joinRows = (fly: FakeEl) => fly.children.filter((it) => it.label()?.startsWith("+ ") || it.label()?.startsWith("Move to ")).map((it) => it.label());
  const pinRow = (fly: FakeEl) => fly.children.find((it) => it.has("ctx-item-pin"));
  const typeName = (fly: FakeEl, name: string) => { const inp = fly.all().find((n) => n.has("ctx-tag-input"))!; inp.value = name; for (const fn of inp.listeners.keydown || []) fn({ key: "Enter" }); };
  const renamed = (views: typeof V, i: number, name: string, seq: number) => ({ ...views, tags: views.tags.map((t, k) => (k === i ? { ...t, name } : t)), seq });
  /** api under infra and archived, and an empty qa to move to */
  const V_API_BOTH_QA = { ...V_API_BOTH, tags: [...V_API_BOTH.tags, { id: "g5", name: "qa", color: "#7aa2f7", members: [] as string[] }], seq: 6 };
  withStore(() => {
    const api = liftShowTabMenu()(hooks);
    // N1: the menu on api's infra copy, the flyout open; the push renames infra to platform (g1 keeps its id)
    hooks.views = V_API_BOTH_QA;
    let menu = api.open("api", "infra");
    let fly = flyOf(menu);
    assert.deepEqual(joinRows(fly), ["Move to qa"]);
    api.push(renamed(V_API_BOTH_QA, 0, "platform", 7));
    assert.equal(rowOf(menu)?.sub(), HIDE_SUB("platform"), "the row follows the rename (before: the copy was lost, the row stale)");
    assert.equal(tagsSub(menu), "platform · archived");
    assert.deepEqual(joinRows(fly), ["Move to qa"], "the flyout keeps its Move to rows (before: '+ qa', no copy to move)");
    assert.equal(pinRow(fly)?.sub(), "keep this tab on the strip while platform is folded", "and its Show when folded row, under the new name");
    rowOf(menu)!.click();
    assert.deepEqual(hooks.writes.map((w) => w.hidden), [[{ sid: "api", name: "platform", id: "g1" }]], "the click hides the same copy under its new name (before: dismissed, nothing written)");
    writeTabGroups(d);
    // N1b: the same rename arriving WITHOUT the hook (the blob set directly, the row not re-dressed, as C4 does): the click still writes
    // for the same tag, by its id (the write guard matches the id where the name changed)
    hooks.views = V_API_BOTH_QA; hooks.writes = [];
    menu = api.open("api", "infra");
    hooks.views = renamed(V_API_BOTH_QA, 0, "platform", 8);
    rowOf(menu)!.click();
    assert.deepEqual(hooks.writes.map((w) => w.hidden), [[{ sid: "api", name: "platform", id: "g1" }]], "the same tag, by its id");
    writeTabGroups(d);
    // N2: the one-tag control: web under infra alone, the rename pushed
    hooks.views = V; hooks.writes = [];
    menu = api.open("web", "infra");
    api.push(renamed(V, 0, "platform", 4));
    assert.equal(rowOf(menu)?.sub(), HIDE_SUB("platform"));
    rowOf(menu)!.click();
    assert.deepEqual(hooks.writes.map((w) => w.hidden), [[{ sid: "web", name: "platform", id: "g1" }]]);
    writeTabGroups(d);
    // N3: the rename beside a NEW tag under the old name, holding the session too: the copy is the renamed tag, by its id, never the new
    // infra (a name-first or either-or match would take the new tag)
    hooks.views = V_API_BOTH_QA; hooks.writes = [];
    menu = api.open("api", "infra");
    const V_N3 = renamed(V_API_BOTH_QA, 0, "platform", 9);
    api.push({ ...V_N3, tags: [...V_N3.tags, { id: "g9", name: "infra", color: "#abcabc", members: ["api"] }] });
    assert.equal(rowOf(menu)?.sub(), HIDE_SUB("platform"), "the id decides where the name would match the new tag");
    rowOf(menu)!.click();
    assert.deepEqual(hooks.writes.map((w) => w.hidden), [[{ sid: "api", name: "platform", id: "g1" }]]);
    writeTabGroups(d);
    // N4: the OTHER tag renamed leaves the row as it was
    hooks.views = V_API_BOTH_QA; hooks.writes = [];
    menu = api.open("api", "infra");
    api.push(renamed(V_API_BOTH_QA, 1, "old", 10));
    assert.equal(rowOf(menu)?.sub(), HIDE_SUB("infra"));
    assert.equal(tagsSub(menu), "infra · old");
    rowOf(menu)!.click();
    assert.deepEqual(hooks.writes.map((w) => w.hidden), [[{ sid: "api", name: "infra", id: "g1" }]]);
    writeTabGroups(d);
    // N5: a tag claimed at its create. The trail's copy types a new tag: the claim carries the name alone (aimAdd runs before postTagEdit,
    // so the ref never wears the placeholder id; round 7 corrects the comment that said it did), the optimistic union wears the placeholder
    // id, no row while pending; the ack's blob carries the tag's real id and the hook gives the row (round 3's docs had said the next
    // open) by the name pass, and the click writes that id
    hooks.views = V; hooks.writes = [];
    menu = api.open("loose", "");
    fly = flyOf(menu);
    typeName(fly, "qa");
    assert.equal(rowOf(menu), undefined, "pending: no row");
    const pendingId = viewTagUnion(hooks.views as typeof V).find((g) => g.name === "qa")!.localId!;
    assert.match(pendingId, /^pending-/);
    const held = hooks.views as typeof V;
    api.push({ ...held, tags: held.tags.map((t) => (t.id === pendingId ? { ...t, id: "g7" } : t)), seq: 5 });
    assert.equal(rowOf(menu)?.sub(), HIDE_SUB("qa"), "the ack gave the claimed copy its row");
    assert.equal(menu.children.indexOf(rowOf(menu)!), menu.children.findIndex((it) => it.label() === "Notify me") + 1, "directly after Notify me");
    assert.deepEqual(joinRows(fly), ["Move to infra", "Move to archived"]);
    assert.equal(pinRow(fly)?.sub(), "keep this tab on the strip while qa is folded");
    rowOf(menu)!.click();
    assert.deepEqual(hooks.writes.map((w) => w.hidden), [[{ sid: "loose", name: "qa", id: "g7" }]], "the id followed the ack");
    writeTabGroups(d);
    // N6: a REMOTE-ONLY group has no local id (a remote tag's id is never stored), so its copy is name-matched, and a rename pushed for
    // it on a two-holder session loses the copy: the row leaves, nothing written. The limit the homeNow comment names
    const V_REMOTE = { ...V, remoteTags: [{ id: "TESTHOST:r1", host: "TESTHOST", name: "ops", color: "#123456", members: ["web"] }], seq: 4 };
    hooks.views = V_REMOTE; hooks.writes = [];
    menu = api.open("web", "ops");
    assert.equal(rowOf(menu)?.sub(), HIDE_SUB("ops"), "a remote-only group's copy has its row, by name");
    api.push({ ...V_REMOTE, remoteTags: [{ ...V_REMOTE.remoteTags[0], name: "ops2" }], seq: 5 });
    assert.equal(rowOf(menu), undefined, "renamed remotely: no id to follow, two holders left, no row");
    assert.equal(hooks.writes.length, 0);
    // N6b (round 7): the OTHER name-carried kind, a copy right-clicked under a tag whose create the kernel had not yet answered. web under
    // infra and a pending qa (this pane's create in flight, the placeholder id, holding web), the menu opened on the qa copy: refOf reads
    // the pending union, so copyNow carries the placeholder id, and there is no row while the tag is pending (S5). The ack replaces the
    // placeholder by g7: no held union carries the placeholder, so the name pass carries the copy and the row reads qa. A rename to qa2
    // pushed with two holders then loses the copy (no id to follow, and two holders defeat the one-holder fallback): the row leaves and
    // nothing is written, the limit the guide states beside the remote-only group (N6). The behaviour is round 6's, executed here so the
    // guide's sentence and the code cannot drift apart; with one holder the fallback carries the copy through the rename
    const V_PENDING = { ...V, tags: [...V.tags, { id: "pending-x", name: "qa", color: "#7aa2f7", members: ["web"] }], seq: 4 };
    hooks.views = V_PENDING; hooks.writes = [];
    menu = api.open("web", "qa");
    assert.equal(rowOf(menu), undefined, "pending: no row (S5)");
    const V_ACKED = { ...V_PENDING, tags: V_PENDING.tags.map((t) => (t.id === "pending-x" ? { ...t, id: "g7" } : t)), seq: 5 };
    api.push(V_ACKED);
    assert.equal(rowOf(menu)?.sub(), HIDE_SUB("qa"), "the ack: the name carries the copy to the tag under its real id (the ref holds the placeholder, which no union carries now)");
    api.push(renamed(V_ACKED, 2, "qa2", 6));
    assert.equal(rowOf(menu), undefined, "renamed with two holders (infra and qa2): the name-carried copy is lost and the row leaves");
    assert.equal(hooks.writes.length, 0, "nothing written");
    const V_ONE = { ...V, tags: [{ ...V.tags[0], members: ["api", "tests"] }, V.tags[1], { id: "pending-y", name: "qa", color: "#7aa2f7", members: ["web"] }], seq: 4 };
    hooks.views = V_ONE; hooks.writes = [];
    menu = api.open("web", "qa");
    const V_ONE_ACKED = { ...V_ONE, tags: V_ONE.tags.map((t) => (t.id === "pending-y" ? { ...t, id: "g8" } : t)), seq: 5 };
    api.push(V_ONE_ACKED);
    api.push(renamed(V_ONE_ACKED, 2, "qa2", 6));
    assert.equal(rowOf(menu)?.sub(), HIDE_SUB("qa2"), "one holder: the fallback carries the copy through the rename");
    rowOf(menu)!.click();
    assert.deepEqual(hooks.writes.map((w) => w.hidden), [[{ sid: "web", name: "qa2", id: "g8" }]], "and the click writes the renamed tag's id");
    writeTabGroups(d);
    // N7 (round 6): the rename pushed beside a REMOTE-ONLY union under the OLD name that also holds the session (the kernel respells a
    // remote tag's local member as the bare sid), in both drag orders. The copy is the renamed tag by its id whichever union comes first:
    // heldCopy runs the id pass over every held union before it tries the name. Round 5 took the first union sameSection matched, so
    // with infra dragged before ops the remote infra took the copy by its name: the row read infra and the click hid the remote section
    for (const order of [["infra", "ops", "archived"], ["ops", "infra", "archived"]]) {
      hooks.views = V_API_BOTH; hooks.writes = [];
      menu = api.open("api", "infra");
      const V_N7 = { ...renamed(V_API_BOTH, 0, "ops", 6), remoteTags: [{ id: "TESTHOST:r1", host: "TESTHOST", name: "infra", color: "#123456", members: ["api"] }], tagOrder: order };
      api.push(V_N7);
      assert.deepEqual(viewTagUnion(V_N7).filter((g) => g.members.includes("api")).map((g) => g.name), order, "three holders in the dragged order: " + order.join(", "));
      assert.equal(rowOf(menu)?.sub(), HIDE_SUB("ops"), "the row names the renamed tag, by its id, in the order " + order.join(", ") + " (round 5: infra, the remote union, when it came first)");
      assert.equal(tagsSub(menu), order.join(" · "));
      rowOf(menu)!.click();
      assert.deepEqual(hooks.writes.map((w) => w.hidden), [[{ sid: "api", name: "ops", id: "g1" }]], "and the click hides that copy (round 5 wrote {api, infra} with no id, the remote section)");
      writeTabGroups(d);
    }
  });
});

test("executed: THE FLYOUT'S ROWS ACT ON THE LIVE UNION (menu review round 7). A remote same-named tag joining the copy's union with the session, or an already-joined one taking the session, rebuilds the open flyout's rows, and the x then clears every tag of the name; under a pressed pointer the rebuild is parked and the x and Move to resolve the union again at the click, so the remote copy is cleared too; a union gone by the click refuses with the cue and writes nothing", async () => {
  // Round 6's signature listed each union's name, id, colour, pending state and hold on the session, so a remote infra tag arriving
  // with the session (the union already held it through the local tag) or an already-joined remote infra taking the session changed
  // nothing in the string: rebuildFly was a no-op, the x's handler kept the union it was built from (remotes empty, or the remote's
  // members without the session), applyUnionEdit walked those, and the x removed the local half alone: the remote copy kept the
  // session, the infra row stood and the Hide tab row still read infra; Move to left the remote copy behind the same way. The
  // per-constituent list in the signature covers the push that lands unpressed (A, B); the click-time resolution covers the push that
  // lands under the press, where the rebuild is parked and the rows are the old ones by design (C, C2); a union gone by the click takes
  // the cue (D)
  type Views = { active: string; tags: Array<{ id: string; name: string; color: string; members: string[] }>; remoteTags?: Array<{ id: string; host: string; name: string; color: string; members: string[] }>; seq: number };
  const hooks = menuHooks();
  const rowOf = (menu: FakeEl) => menu.children.find((it) => it.has("ctx-item-hide"));
  const heldRow = (fly: FakeEl, name: string) => fly.children.find((it) => it.label() === name);
  const xOf = (fly: FakeEl, name: string) => heldRow(fly, name)!.all().find((n) => n.has("ctx-tag-x") && !n.has("ctx-tag-plus"))!;
  const moveRow = (fly: FakeEl, name: string) => fly.children.find((it) => it.label() === "Move to " + name)!;
  const sameNodes = (a: FakeEl[], b: FakeEl[]) => a.length === b.length && a.every((n, i) => n === b[i]);
  const R1 = { id: "TESTHOST:r1", host: "TESTHOST", name: "infra", color: "#123456", members: ["api"] };
  const holders = (v: Views) => ({ local: (v.tags.find((t) => t.id === "g1")?.members ?? []).slice(), remote: (v.remoteTags || []).map((t) => t.members.slice()) });
  const V_QA: Views = { ...V_API_BOTH, tags: [...V_API_BOTH.tags, { id: "g5", name: "qa", color: "#7aa2f7", members: [] as string[] }], seq: 6 };
  await withStore(async () => {
    const api = liftShowTabMenu()(hooks);
    const win = hooks.window!;
    const press = (menu: FakeEl) => menu.fire("pointerdown", { button: 0 });
    // A: api under infra and archived, the menu on the infra copy, the flyout open; the push brings a remote infra tag holding api into
    // the union (a host attaching, or its tag taking api). The rows are rebuilt (round 6 left them: the union's tuple was unchanged), and
    // the x on infra clears the local tag and the remote mirror alike: api is under archived alone, the infra row is gone and the Hide
    // tab row names archived
    hooks.views = V_API_BOTH; hooks.writes = [];
    let menu = api.open("api", "infra");
    let fly = flyOf(menu);
    let rows = fly.children.slice();
    const V_A: Views = { ...V_API_BOTH, remoteTags: [R1], seq: 5 };
    api.push(V_A);
    assert.ok(!sameNodes(fly.children, rows), "the rows are rebuilt: a constituent joined with the session (round 6: the same nodes, the union's tuple unchanged)");
    assert.equal(rowOf(menu)?.sub(), HIDE_SUB("infra"), "the row still names infra: the union holds api");
    xOf(fly, "infra").click();
    let after = hooks.views as Views;
    assert.deepEqual(holders(after), { local: ["web", "tests"], remote: [[]] }, "the x cleared both halves (round 6 cleared the local tag alone, and the remote infra kept api)");
    assert.equal(heldRow(fly, "infra"), undefined, "the infra row is gone");
    assert.equal(rowOf(menu)?.sub(), HIDE_SUB("archived"), "and the Hide tab row names the one holder left");
    // B: the remote infra already in the union without api; the push gives it api. The union's hold on api was already true through
    // the local tag, so round 6's string stood and the stale x skipped the remote tag (its members, as built, held no api)
    const V_B0: Views = { ...V_API_BOTH, remoteTags: [{ ...R1, members: ["web"] }], seq: 5 };
    hooks.views = V_B0; hooks.writes = [];
    menu = api.open("api", "infra");
    fly = flyOf(menu);
    rows = fly.children.slice();
    const V_B1: Views = { ...V_B0, remoteTags: [{ ...R1, members: ["web", "api"] }], seq: 6 };
    api.push(V_B1);
    assert.ok(!sameNodes(fly.children, rows), "the rows are rebuilt: a constituent took the session");
    xOf(fly, "infra").click();
    after = hooks.views as Views;
    assert.deepEqual(holders(after), { local: ["web", "tests"], remote: [["web"]] }, "both halves: the remote infra keeps web and lets api go");
    assert.equal(heldRow(fly, "infra"), undefined);
    assert.equal(rowOf(menu)?.sub(), HIDE_SUB("archived"));
    // C: under a PRESSED pointer the rebuild is parked (the menu's hold), so the click lands on the rows built before the push. api under
    // infra, archived and an empty qa; the press; the push brings the remote infra holding api; the release; Move to qa: the move resolves
    // the copy's group again at the click and clears the remote infra too (round 6 moved the local half: the remote infra kept api, so
    // api stood under infra, archived and qa)
    hooks.views = V_QA; hooks.writes = [];
    menu = api.open("api", "infra");
    fly = flyOf(menu);
    rows = fly.children.slice();
    const mv = moveRow(fly, "qa");
    press(menu);
    const V_C: Views = { ...V_QA, remoteTags: [R1], seq: 7 };
    api.push(V_C);
    assert.ok(sameNodes(fly.children, rows), "under the press the rows stand (the rebuild is parked)");
    win.fire("pointerup");
    mv.click();
    after = hooks.views as Views;
    assert.deepEqual(holders(after), { local: ["web", "tests"], remote: [[]] }, "Move to cleared the remote infra as well as the local tag (round 6: the remote infra kept api)");
    assert.deepEqual(viewTagUnion(after).filter((g) => g.members.includes("api")).map((g) => g.name), ["archived", "qa"], "api is under archived and qa: infra let it go everywhere");
    assert.equal(rowOf(menu)?.sub(), HIDE_SUB("qa"), "the row names the destination");
    await tick();
    assert.equal(rowOf(menu)?.sub(), HIDE_SUB("qa"), "the parked run landed and found the same");
    // C2: the same press and push, the x on infra after the release: both halves
    hooks.views = V_API_BOTH; hooks.writes = [];
    menu = api.open("api", "infra");
    fly = flyOf(menu);
    const xInfra = xOf(fly, "infra");
    press(menu);
    api.push(V_A);
    win.fire("pointerup");
    xInfra.click();
    after = hooks.views as Views;
    assert.deepEqual(holders(after), { local: ["web", "tests"], remote: [[]] }, "the x under the parked rebuild cleared both halves (round 6: the local half alone)");
    await tick();
    assert.equal(heldRow(fly, "infra"), undefined);
    // D: the union gone by the click (its tag deleted under the press, no remote): the x refuses with the cue on its row and writes
    // nothing; the release's rebuild then takes the row off
    hooks.views = V_API_BOTH; hooks.writes = [];
    menu = api.open("api", "infra");
    fly = flyOf(menu);
    const infraRow = heldRow(fly, "infra")!;
    press(menu);
    const V_D: Views = { ...V_API_BOTH, tags: [V_API_BOTH.tags[1]], seq: 8 };   // infra deleted
    api.push(V_D);
    win.fire("pointerup");
    assert.ok(!infraRow.has("romp-acted"), "no cue before the click");
    xOf(fly, "infra").click();
    assert.equal(hooks.views, V_D, "nothing posted: the union is gone");
    assert.ok(infraRow.has("romp-acted"), "the row pulses (the refused click's cue)");
    assert.equal(infraRow.title, "infra. The tags changed just before your click, so it did nothing; click again.", "and the tooltip says why and what to do");
    infraRow.fire("animationend");
    assert.ok(!infraRow.has("romp-acted"), "the pulse class leaves on the animation's end");
    await tick();
    assert.equal(heldRow(fly, "infra"), undefined, "the parked rebuild took the row off");
    assert.equal(rowOf(menu)?.sub(), HIDE_SUB("archived"));
  });
});

test("executed: THE FLYOUT FOLLOWS THE ROW (menu review rounds 3 and 6). With the Tags flyout open, an x on the copy's tag takes the Hide tab row out above the Tags row and the flyout's top follows the row; an add that brings the row back moves both down again; a menu clamped at the pane's bottom moves up by the row that came back, and the emoji picker's anchor follows; a flyout clamped at the pane's bottom that grows while the row's words stand (a push adding a tag, the user's New tag) or change (a rename beside new tags) is placed again at its new size", () => {
  // the flyout's top was set once, from the Tags row's rect at open; the refresh then removed or re-inserted the Hide tab row above
  // the Tags row and the flyout stood one row low (or high) until reopened. The refresh ends by seating the menu and the open flyout
  // again, keyed on itself (the write's build), no timer. Executed over the harness's rect model: a menu's rows stack ROW apart under
  // its top; a flyout's top is its style's
  const hooks = menuHooks();
  const rowOf = (menu: FakeEl) => menu.children.find((it) => it.has("ctx-item-hide"));
  const xOf = (fly: FakeEl, name: string) => fly.children.find((it) => it.label() === name)!.all().find((n) => n.has("ctx-tag-x") && !n.has("ctx-tag-plus"))!;
  const top = (n: FakeEl) => parseFloat(n.style.top);
  withStore(() => {
    const api = liftShowTabMenu()(hooks);
    // F1: the row leaves, the flyout follows the Tags row up one row; the row returns, both are back
    let menu = api.open("web", "infra");
    const tags = menu.children.find((it) => it.has("ctx-item-tags"))!;
    let fly = flyOf(menu);
    const tagsTop0 = tags.getBoundingClientRect().top;
    assert.equal(top(fly), tagsTop0, "at open the flyout's top is the Tags row's");
    assert.ok(menu.children.indexOf(rowOf(menu)!) < menu.children.indexOf(tags), "the Hide tab row stands above the Tags row");
    xOf(fly, "infra").click();
    assert.equal(rowOf(menu), undefined);
    assert.equal(tags.getBoundingClientRect().top, tagsTop0 - FakeEl.ROW, "the Tags row moved up by the row that left");
    assert.equal(top(fly), tagsTop0 - FakeEl.ROW, "and the flyout followed it (round 2 left it where the row had been)");
    fly.children.find((it) => it.label() === "+ infra")!.click();
    assert.ok(rowOf(menu));
    assert.equal(tags.getBoundingClientRect().top, tagsTop0);
    assert.equal(top(fly), tagsTop0, "the row back, the flyout back at the Tags row");
    // F2: a menu clamped at the pane's bottom for a copy with no row (the trail's), the flyout open; "+ infra" brings the row in and
    // the menu grows by one row: the clamp moves it up by that row, the flyout follows the Tags row, and the picker's anchor moves
    // with the menu; the row leaving again shrinks the menu but leaves it where it stands (no move without need)
    hooks.win = { w: 1200, h: 800 };
    menu = api.open("loose", "", { x: 10, y: 790 });
    const rows0 = menu.rows().length, menuTop0 = top(menu);
    assert.equal(menuTop0, 800 - rows0 * FakeEl.ROW - 4, "clamped at the pane's bottom");
    assert.deepEqual(api.at(), { x: 10, y: menuTop0 }, "the picker's anchor is the clamped corner");
    fly = flyOf(menu);
    const tags2 = menu.children.find((it) => it.has("ctx-item-tags"))!;
    assert.equal(top(fly), Math.min(tags2.getBoundingClientRect().top, 800 - fly.getBoundingClientRect().height - 4), "the flyout at the Tags row, clamped to the pane too");
    fly.children.find((it) => it.label() === "+ infra")!.click();
    assert.equal(menu.rows().length, rows0 + 1, "the row came in");
    assert.equal(top(menu), menuTop0 - FakeEl.ROW, "the menu moved up by one row: the pane's bottom asked for it");
    assert.deepEqual(api.at(), { x: 10, y: menuTop0 - FakeEl.ROW }, "the picker's anchor followed");
    assert.equal(top(fly), Math.min(tags2.getBoundingClientRect().top, 800 - fly.getBoundingClientRect().height - 4), "the flyout at the Tags row's new place");
    xOf(fly, "infra").click();
    assert.equal(menu.rows().length, rows0);
    assert.equal(top(menu), menuTop0 - FakeEl.ROW, "the menu shrank and stayed: a seat from its own corner moves it only when the pane asks");
    // F3: a closed flyout is not placed (the hover close removes it); the refresh runs and the menu is seated all the same
    menu = api.open("web", "infra");
    fly = flyOf(menu);
    const flyTop = top(fly);
    fly.remove();
    assert.equal(fly.isConnected, false);
    const fly2 = flyOf(menu);   // a new flyout, placed at open
    assert.notEqual(fly2, fly);
    xOf(fly2, "infra").click();
    assert.equal(top(fly), flyTop, "the closed flyout's style is not written");
    assert.equal(top(fly2), menu.children.find((it) => it.has("ctx-item-tags"))!.getBoundingClientRect().top, "the open one follows");
    assert.equal(hooks.writes.length, 0, "no hide written by any of it");
    // F4 (round 6): a flyout clamped at the pane's BOTTOM grows while the Hide tab row's words stand: a push that adds a tag (one Move to
    // row more), then the user's own New tag (a creating... row). The placement runs after every build and rebuild whatever the words did,
    // so the flyout's top moves up and its foot stays inside the pane. Round 5 returned before the seat on unchanged words, and build()
    // reached the seat through that refresh alone, so the flyout grew past the pane's edge with New tag and Configure tags unreachable
    const typeName = (f: FakeEl, name: string) => { const inp = f.all().find((n) => n.has("ctx-tag-input"))!; inp.value = name; for (const fn of inp.listeners.keydown || []) fn({ key: "Enter" }); };
    hooks.views = V; hooks.win = { w: 1200, h: 800 };
    menu = api.open("web", "infra", { x: 10, y: 790 });
    fly = flyOf(menu);
    const tags3 = menu.children.find((it) => it.has("ctx-item-tags"))!;
    const clamped = (f: FakeEl) => Math.min(tags3.getBoundingClientRect().top, 800 - f.getBoundingClientRect().height - 4);
    assert.equal(top(fly), clamped(fly), "at open the flyout is placed against the pane's bottom");
    assert.ok(top(fly) < tags3.getBoundingClientRect().top, "and the clamp is what places it: the Tags row stands lower");
    const h0 = fly.getBoundingClientRect().height;
    api.push({ ...V, tags: [...V.tags, { id: "g6", name: "draft", color: "#f0f", members: [] as string[] }], seq: 4 });
    assert.equal(fly.getBoundingClientRect().height, h0 + FakeEl.ROW, "a tag more: the flyout grew by a row");
    assert.equal(rowOf(menu)?.sub(), HIDE_SUB("infra"), "while the row's words stand");
    assert.equal(top(fly), clamped(fly), "the flyout moved up by that row, its foot inside the pane (round 5 left its top where it was)");
    typeName(fly, "qa");
    assert.equal(fly.getBoundingClientRect().height, h0 + 2 * FakeEl.ROW, "the user's New tag: a creating... row more");
    assert.equal(top(fly), clamped(fly), "placed again");
    // the words change too: a rename beside two new tags. The hook runs the row's refresh before the flyout's rebuild, so round 5 seated
    // at the OLD height and the rebuild's own refresh returned before the seat; the placement after every refresh reads the new height
    hooks.views = V;
    menu = api.open("web", "infra", { x: 10, y: 790 });
    fly = flyOf(menu);
    const tags4 = menu.children.find((it) => it.has("ctx-item-tags"))!;
    const h1 = fly.getBoundingClientRect().height;
    api.push({ ...V, tags: [{ ...V.tags[0], name: "platform" }, V.tags[1], { id: "g6", name: "draft", color: "#f0f", members: [] as string[] }, { id: "g7", name: "qa", color: "#0ff", members: [] as string[] }], seq: 5 });
    assert.equal(rowOf(menu)?.sub(), HIDE_SUB("platform"), "the words changed");
    assert.equal(fly.getBoundingClientRect().height, h1 + 2 * FakeEl.ROW, "and the flyout grew by two rows");
    assert.equal(top(fly), Math.min(tags4.getBoundingClientRect().top, 800 - fly.getBoundingClientRect().height - 4), "placed at the new height (round 5: at the old one)");
    assert.equal(hooks.writes.length, 0, "no hide written by any of it");
  });
});

test("executed: NO REBUILD UNDER A PRESSED POINTER (menu review rounds 5 and 6). A push that lands between a pointerdown on the menu and its release re-dresses the Hide tab row and rebuilds the flyout only on the release, a tick after the click, so the click lands on the node the user pressed; a push that changes nothing the row shows leaves its child nodes alone; a run parked when the click dismissed the menu paints nothing; the release listeners leave with the release; a same-named tag under a new id pushed mid-press: the refused click's re-dress changes no word, so the row pulses and its tooltip says to click again, and the second click writes the new id", async () => {
  // round 4 re-dressed the row with replaceChildren on every hook run, changed or not, and rebuilt the flyout's rows on a sig change,
  // so a frame between mousedown and mouseup swapped the pressed node and the click was lost (probed in Chromium and Firefox: no
  // click at the row, the menu or the document). One pressHold(menu) parks the re-dress, the removal and the rebuild while the
  // pointer is down and runs the newest on the release's own events (a zero timer after the pointerup, so the click, which the
  // browser dispatches right after the pointerup, fires first); the words are compared before any rebuild
  const hooks = menuHooks();
  const rowOf = (menu: FakeEl) => menu.children.find((it) => it.has("ctx-item-hide"));
  const tagsSub = (menu: FakeEl) => menu.children.find((it) => it.has("ctx-item-tags"))!.sub();
  const joinRows = (fly: FakeEl) => fly.children.filter((it) => it.label()?.startsWith("+ ") || it.label()?.startsWith("Move to ")).map((it) => it.label());
  const sameNodes = (a: FakeEl[], b: FakeEl[]) => a.length === b.length && a.every((n, i) => n === b[i]);
  const renamed = (views: typeof V, i: number, name: string, seq: number) => ({ ...views, tags: views.tags.map((t, k) => (k === i ? { ...t, name } : t)), seq });
  const V_API_BOTH_QA = { ...V_API_BOTH, tags: [...V_API_BOTH.tags, { id: "g5", name: "qa", color: "#7aa2f7", members: [] as string[] }], seq: 6 };
  await withStore(async () => {
    const api = liftShowTabMenu()(hooks);
    const win = hooks.window!;
    const press = (menu: FakeEl) => menu.fire("pointerdown", { button: 0 });
    // K1: the menu on api's infra copy, the flyout open; the pointer down on the menu; the rename pushed: nothing is rebuilt (the row's
    // children and the flyout's rows are the same nodes, the words still infra) while the section the row names is still infra; the
    // release, then the click the browser dispatches after it: the click lands, on the same copy by its id (platform, g1), and
    // dismisses; the parked re-dress lands on the tick and paints nothing (the menu is off the page)
    hooks.views = V_API_BOTH_QA;
    let menu = api.open("api", "infra");
    let fly = flyOf(menu);
    let row = rowOf(menu)!;
    let kids = row.children.slice(), flyRows = fly.children.slice();
    press(menu);
    api.push(renamed(V_API_BOTH_QA, 0, "platform", 7));
    assert.ok(sameNodes(row.children, kids), "under the press the row is not re-dressed: the same child nodes (round 4 replaced them on every run)");
    assert.ok(win.count("pointerup") > 0 && win.count("blur") > 0, "a press installs the release listeners on the window");
    assert.equal(row.sub(), HIDE_SUB("infra"), "and still reads infra");
    assert.ok(sameNodes(fly.children, flyRows), "the flyout's rows are not rebuilt under the press either");
    assert.equal(tagsSub(menu), "infra · archived", "the Tags row's sub-line waits too: the hook's run is parked whole");
    win.fire("pointerup");
    assert.equal(win.count("pointerup"), 0, "the release listeners leave with the release");
    assert.ok(sameNodes(row.children, kids), "the re-dress waits for the tick after the release (the click comes first)");
    const d0 = hooks.dismissed;
    row.click();
    assert.deepEqual(hooks.writes.map((w) => w.hidden), [[{ sid: "api", name: "platform", id: "g1" }]], "the click landed: the same copy under its new name, by the id");
    assert.equal(hooks.dismissed, d0 + 1);
    await tick();
    assert.ok(sameNodes(row.children, kids) && row.sub() === HIDE_SUB("infra"), "the parked re-dress found the menu dismissed and painted nothing");
    writeTabGroups(d);
    // K2: the same press and push, released with no click: the tick re-dresses the row (platform) and rebuilds the flyout
    hooks.views = V_API_BOTH_QA; hooks.writes = [];
    menu = api.open("api", "infra");
    fly = flyOf(menu);
    row = rowOf(menu)!;
    kids = row.children.slice(); flyRows = fly.children.slice();
    press(menu);
    api.push(renamed(V_API_BOTH_QA, 0, "platform", 8));
    assert.ok(sameNodes(row.children, kids) && sameNodes(fly.children, flyRows));
    win.fire("pointerup");
    await tick();
    assert.equal(row.sub(), HIDE_SUB("platform"), "released: the re-dress landed");
    assert.ok(!sameNodes(row.children, kids), "new child nodes");
    assert.ok(!sameNodes(fly.children, flyRows), "the flyout rebuilt");
    assert.equal(tagsSub(menu), "platform · archived", "the Tags row's sub-line followed in the same run");
    // K3: two pushes under one press: the newest is what lands (the first parked run is replaced)
    hooks.views = V_API_BOTH_QA;
    menu = api.open("api", "infra");
    row = rowOf(menu)!;
    press(menu);
    api.push({ ...V_API_BOTH_QA, tags: [{ ...V_API_BOTH_QA.tags[0], members: ["web", "tests"] }, V_API_BOTH_QA.tags[1], V_API_BOTH_QA.tags[2]], seq: 9 });   // infra off: archived
    api.push(renamed(V_API_BOTH_QA, 0, "platform", 10));   // back under the renamed tag
    assert.equal(row.sub(), HIDE_SUB("infra"), "still the pressed words");
    win.fire("pointercancel");   // a cancel releases like a pointerup
    await tick();
    assert.equal(row.sub(), HIDE_SUB("platform"), "the newest parked run painted");
    // K4: a push that changed the resolution under the press: the click after the release is judged against the words on the page
    // (infra), so it is refused with nothing written and the menu open; the parked re-dress then lands (archived) and a second click
    // hides the copy the row names
    hooks.views = V_API_BOTH_QA; hooks.writes = [];
    menu = api.open("api", "infra");
    row = rowOf(menu)!;
    press(menu);
    api.push({ ...V_API_BOTH_QA, tags: [{ ...V_API_BOTH_QA.tags[0], members: ["web", "tests"] }, V_API_BOTH_QA.tags[1], V_API_BOTH_QA.tags[2]], seq: 11 });
    win.fire("pointerup");
    const d1 = hooks.dismissed;
    row.click();
    assert.deepEqual([hooks.writes.length, hooks.dismissed, menu.isConnected], [0, d1, true], "refused: the row read infra, the copy is under archived alone; nothing written, the menu open");
    assert.equal(row.sub(), HIDE_SUB("archived"), "the refused click's own refresh re-dressed the row at once (after the release, nothing is held)");
    await tick();
    assert.equal(row.sub(), HIDE_SUB("archived"), "the parked run found the words dressed and left the node");
    row.click();
    assert.deepEqual(hooks.writes.map((w) => w.hidden), [[{ sid: "api", name: "archived", id: "g2" }]], "the second click acts on the words shown");
    writeTabGroups(d);
    // K5: a push that changes nothing the row shows leaves its child nodes (round 4 re-dressed on every run): another session's tag
    // change, the seq bumped
    hooks.views = V_API_BOTH_QA; hooks.writes = [];
    menu = api.open("api", "infra");
    fly = flyOf(menu);
    row = rowOf(menu)!;
    kids = row.children.slice();
    api.push({ ...V_API_BOTH_QA, tags: [V_API_BOTH_QA.tags[0], { ...V_API_BOTH_QA.tags[1], members: ["old1"] }, V_API_BOTH_QA.tags[2]], seq: 12 });
    assert.ok(sameNodes(row.children, kids), "unchanged words: the same child nodes (no press here)");
    assert.equal(row.sub(), HIDE_SUB("infra"));
    // K6: the same words under a new id (an ack replacing a placeholder): the node stands and the click writes the new id
    hooks.views = V; hooks.writes = [];
    menu = api.open("loose", "");
    fly = flyOf(menu);
    const inp = fly.all().find((n) => n.has("ctx-tag-input"))!; inp.value = "qa"; for (const fn of inp.listeners.keydown || []) fn({ key: "Enter" });
    const held = hooks.views as typeof V;
    const pendingId = viewTagUnion(held).find((g) => g.name === "qa")!.localId!;
    api.push({ ...held, tags: held.tags.map((t) => (t.id === pendingId ? { ...t, id: "g7" } : t)), seq: 5 });
    row = rowOf(menu)!;
    kids = row.children.slice();
    api.push({ ...held, tags: held.tags.map((t) => (t.id === pendingId ? { ...t, id: "g7" } : t)), seq: 6 });   // a frame with the same words
    assert.ok(sameNodes(row.children, kids), "the same words: no rebuild");
    row.click();
    assert.deepEqual(hooks.writes.map((w) => w.hidden), [[{ sid: "loose", name: "qa", id: "g7" }]], "the click writes the id the row's section carries");
    // K7: a press with the secondary button holds nothing (a right press yields no click and often no pointerup)
    hooks.views = V_API_BOTH_QA; hooks.writes = [];
    menu = api.open("api", "infra");
    row = rowOf(menu)!;
    menu.fire("pointerdown", { button: 2 });
    assert.equal(win.count("pointerup"), 0, "no hold taken");
    api.push(renamed(V_API_BOTH_QA, 0, "platform", 13));
    assert.equal(row.sub(), HIDE_SUB("platform"), "re-dressed at once");
    // K8 (round 6): a SAME-NAMED tag under a NEW id while the pointer is pressed (a delete and a create under one name: the kernel mints
    // a fresh id on every create, and `romp tag` does this as two pushes). web under infra alone; the press; the push replaces g1 by g9;
    // the release; the click before the parked refresh lands. The row's section is still g1 while the resolution is g9, so the guard
    // refuses by the id; the click's refresh finds the same words and paints nothing, so the row acknowledges instead: the sheet's pulse
    // class, taken off on animationend, and the tooltip's note; the parked run then lands and leaves both (unchanged words); the second
    // click writes g9 and dismisses. Round 5 left the node byte-identical, nothing written, the menu open, no cue: a click that did
    // nothing, and no word about why
    const V_G9 = { ...V, tags: [{ ...V.tags[0], id: "g9" }, V.tags[1]], seq: 14 };
    hooks.views = V; hooks.writes = [];
    menu = api.open("web", "infra");
    row = rowOf(menu)!;
    kids = row.children.slice();
    press(menu);
    api.push(V_G9);
    win.fire("pointerup");
    const d2 = hooks.dismissed;
    assert.ok(!row.has("romp-acted"), "no cue before the click");
    row.click();
    assert.deepEqual([hooks.writes.length, hooks.dismissed, menu.isConnected], [0, d2, true], "refused: the row named g1 and the copy sits under g9; nothing written, the menu open");
    assert.ok(sameNodes(row.children, kids) && row.sub() === HIDE_SUB("infra"), "the same words: nothing painted");
    assert.ok(row.has("romp-acted"), "so the row pulses (round 6; round 5 gave no cue at all)");
    assert.equal(row.title, HIDE_SUB("infra") + ". The group changed just before your click, so it did nothing; click again.", "and the tooltip says why and what to do");
    row.fire("animationend");
    assert.ok(!row.has("romp-acted"), "the pulse class leaves on the animation's end");
    await tick();
    assert.ok(sameNodes(row.children, kids) && row.title.endsWith("click again."), "the parked run landed on unchanged words: the node and the note stand");
    row.click();
    assert.deepEqual(hooks.writes.map((w) => w.hidden), [[{ sid: "web", name: "infra", id: "g9" }]], "the second click writes the new id");
    assert.equal(hooks.dismissed, d2 + 1, "and dismisses");
    writeTabGroups(d);
    // the no-press twin: the same push with no pointer down re-dresses the row's section at once under the same words (the node stands,
    // K6's case), so the first click writes g9
    hooks.views = V; hooks.writes = [];
    menu = api.open("web", "infra");
    row = rowOf(menu)!;
    kids = row.children.slice();
    api.push(V_G9);
    assert.ok(sameNodes(row.children, kids) && row.sub() === HIDE_SUB("infra") && row.title === HIDE_SUB("infra"), "the row stands, naming infra, its tooltip the sentence alone");
    row.click();
    assert.deepEqual(hooks.writes.map((w) => w.hidden), [[{ sid: "web", name: "infra", id: "g9" }]], "no press: the first click writes the new id");
    assert.ok(!row.has("romp-acted"), "and no cue was needed");
    // K8b (round 6): the TWO-HOLDER form. api under infra and archived; the same press, the same replacement of infra's id, the release,
    // the click. heldCopy finds no union under g1 and falls to the name, infra under g9, the copy the strip's infra section (keyed by the
    // name) still shows: the guard refuses by the id with the cue, and the second click writes g9. Round 5 matched nothing (the ids
    // differed and two holders defeat the one-holder fallback), so homeNow was undefined and the no-home branch dismissed the menu in
    // silence with nothing written
    const V_BOTH_G9 = { ...V_API_BOTH, tags: [{ ...V_API_BOTH.tags[0], id: "g9" }, V_API_BOTH.tags[1]], seq: 15 };
    hooks.views = V_API_BOTH; hooks.writes = [];
    menu = api.open("api", "infra");
    row = rowOf(menu)!;
    press(menu);
    api.push(V_BOTH_G9);
    win.fire("pointerup");
    const d3 = hooks.dismissed;
    row.click();
    assert.deepEqual([hooks.writes.length, hooks.dismissed, menu.isConnected], [0, d3, true], "two holders: refused with the menu open (round 5 dismissed it, nothing written, no word)");
    assert.ok(row.has("romp-acted") && row.title.endsWith("click again."), "the cue");
    row.click();
    assert.deepEqual(hooks.writes.map((w) => w.hidden), [[{ sid: "api", name: "infra", id: "g9" }]], "the second click writes the new id for the infra copy");
    assert.equal(hooks.dismissed, d3 + 1);
    writeTabGroups(d);
    // and with no press: the row stays, naming infra (round 5: the row left, the copy unresolved under two holders)
    hooks.views = V_API_BOTH; hooks.writes = [];
    menu = api.open("api", "infra");
    row = rowOf(menu)!;
    api.push(V_BOTH_G9);
    assert.equal(rowOf(menu), row, "the row stands");
    assert.equal(row.sub(), HIDE_SUB("infra"), "naming infra, the same-named tag under its new id");
    row.click();
    assert.deepEqual(hooks.writes.map((w) => w.hidden), [[{ sid: "api", name: "infra", id: "g9" }]]);
  });
});

test("executed: ABSENT ON THE PHONE LAYOUT (menu review round 1). Under the phone media rule the plan is the flat strip and a hide would show nothing, so the menu builds no Hide tab row and writes nothing; the rest of the menu stands; off the phone the row is back", () => {
  // the docs and the comment said the row was absent on the phone; the code never asked (phoneLayout had no read in showTabMenu), so
  // on a coarse-pointer narrow webview pane, where the strip still renders, the row showed and its click wrote a hide the phone's
  // flat plan ignores. The gate is the one the Group tabs by tag switch uses.
  const hooks: MenuHooks = {
    views: V, known: ALL, sessions: new Map<string, unknown>([["web", { name: "web", status: { state: "ready" } }]]),
    writes: [], dismissed: 0, renders: 0, flags: [], phone: true,
    mods: { FakeEl, viewTagUnion, readTabGroups, writeTabGroups, prunePinned, sectionRef, isPinned, setPinned, isHidden, setHidden },
  };
  withStore(() => {
    const api = liftShowTabMenu()(hooks);
    const rowOf = (menu: FakeEl) => menu.children.find((it) => it.has("ctx-item-hide"));
    let menu = api.open("web", "infra");
    assert.equal(rowOf(menu), undefined, "the phone layout: no row (a fresh store, grouping on, a home section: every other gate open)");
    assert.ok(menu.children.some((it) => it.label() === "Hide from feed") && menu.children.some((it) => it.has("ctx-item-tags")), "the rest of the menu stands");
    assert.equal(hooks.writes.length, 0);
    hooks.phone = false;
    menu = api.open("web", "infra");
    assert.equal(rowOf(menu)!.label(), "Hide tab", "off the phone, the same page: the row");
    // THE FLIP WHILE THE MENU IS OPEN (round 6). The media rule's change listener, render.ts's own (lifted with the store listeners onto
    // the harness window), renders the strip and runs the notifier: the row leaves the open menu, the menu stands, nothing is written;
    // the flip back returns the same node. Before, the listener rendered the strip alone, so a menu open across a rotation kept the row
    // and its click wrote a hide the flat phone plan never shows
    const win = hooks.window!;
    const row = rowOf(menu)!;
    const fly = flyOf(menu);
    assert.equal(win.count("media:change"), 1, "render.ts's listener is on the media rule");
    hooks.phone = true;
    const r0 = hooks.renders;
    win.fire("media:change");
    assert.equal(hooks.renders, r0 + 1, "the flip renders the strip");
    assert.equal(rowOf(menu), undefined, "and takes the row off the open menu (before: the row stood)");
    assert.equal(menu.isConnected, true, "the menu stands");
    assert.equal(fly.isConnected, true, "the flyout too");
    assert.equal(hooks.writes.length, 0);
    hooks.phone = false;
    win.fire("media:change");
    assert.equal(rowOf(menu), row, "the flip back: the same node returns");
    assert.equal(row.sub(), HIDE_SUB("infra"));
    // THE CLICK READS THE GATE (round 6): the layout flips and the click lands before the flip's refresh (a finger held across the rotation
    // parks the hook's run through the menu's hold): the row still stands, and its click writes nothing and dismisses, the no-home branch.
    // Before, the click read homeNow alone and wrote hidden [{web, infra, g1}], which planStrip(phone) never shows
    hooks.phone = true;   // no listener fired
    assert.equal(rowOf(menu), row, "the row still stands: nothing ran the refresh");
    const d0 = hooks.dismissed;
    row.click();
    assert.deepEqual([hooks.writes.length, hooks.dismissed, menu.isConnected], [0, d0 + 1, false], "the click reads the gate: nothing written on the phone layout, the menu dismissed");
  });
  // pinned: the same predicate the switch reads (render.ts), so what the strip flattens and what the menu offers cannot disagree
  assert.match(RENDER, /\.\.\.\(phoneLayout\(\) \? \{\} : \{\s*\n\s*groupToggle: \{ label: "Group tabs by tag"/, "the switch's gate");
  assert.match(RENDER, /const PHONE_LAYOUT_MEDIA = "\(pointer:coarse\) and \(max-width:1024px\)";\s*\nfunction phoneLayout\(\): boolean \{/, "one media rule behind it");
  assert.match(RENDER, /\ntry \{ window\.matchMedia\(PHONE_LAYOUT_MEDIA\)\.addEventListener\("change", \(\) => \{ renderTabs\(\); viewsChanged\(\); \}\); \} catch \{ \/\* no matchMedia \*\/ \}\n/, "the flip runs the notifier after the strip's render, the store listeners' shape (round 6)");
});

test("executed + pinned: ONCE PER GESTURE (round 1). A double-click on Hide acts on one row: the platform's click count, no timer", () => {
  // the write's render moves the rows under the pointer at once, so click 2 of a double-click landed on the NEXT row's Hide
  // (the acts sit in one right-hand column) and put a second session away with no gesture aimed at it. UIEvent.detail is the
  // platform's count of the clicks in one gesture (time and distance): 0 for a keyboard press, 1 for a fresh click, 2 and up
  // for the repeats, which act on nothing. Every act of the pane's delegate is wrapped (open, hide, show, the fold's head);
  // the browser leg double-clicks for real.
  assert.equal(repeatedClick({ detail: 0 }), false, "a keyboard press");
  assert.equal(repeatedClick({ detail: 1 }), false, "a fresh click");
  assert.equal(repeatedClick({ detail: 2 }), true, "the second click of a double-click");
  assert.equal(repeatedClick({ detail: 3 }), true);
  assert.equal(repeatedClick(null), false);
  assert.equal(repeatedClick({}), false);
  // ROUND 2: the delegate pulses every matched click before its handler (actions.ts flash), so the swallowed repeat showed
  // the acknowledgement on the button it landed on while nothing happened; the wrapper takes the class back off in the
  // same task. actions.ts stays generic (no detail check there); the browser leg dispatches a detail-2 click and reads it.
  assert.match(SNAP, /const once = \(h: \(node: HTMLElement\) => void\) => \(node: HTMLElement, ev: Event\) => \{ if \(repeatedClick\(ev as UIEvent\)\) \{ node\.classList\.remove\("romp-acted"\); return; \} h\(node\); \};\s*\n\s*delegate\(host, \{ open: once\(\(node\) => \{/);
  assert.match(ui("webview", "actions.ts"), /flash\(el\);\s*\n\s*h\(el, ev\);/, "the pulse precedes the handler, so the handler is where a swallowed click's pulse comes off");
  assert.doesNotMatch(ui("webview", "actions.ts"), /detail/, "the shared delegate knows nothing of click counts");
  assert.equal(SNAP.split("once(").length - 1, 4, "its four uses: open, hide, show, toggle-hidden");
  assert.equal(SNAP.split("const once = ").length - 1, 1, "one wrapper");
  assert.doesNotMatch(SNAP, /lastHideAt|lastClickT|Date\.now\(\) - /, "no timer of ours");
});

test("pinned: THE FOLD GONE under keyboard focus (round 1). The last hidden row shown from another pane, or gone from the section, lands focus on a shown row, never on body", () => {
  // renderSnapshot's last fallback focused the fold's head after syncHiddenFold had set the fold display:none (nothing
  // hidden any more); a browser refuses focus() on a node inside display:none and drops the focus it held there, so Enter
  // and the user's place in the pane were lost. Now a row that changed lists is found by its session id in whichever list
  // it is in (its new position), and a fold that has just gone hands focus to the last shown row, its neighbour. The
  // browser leg executes the three cases in Chromium.
  const paint = SNAP.slice(SNAP.indexOf("function renderSnapshot(): boolean {"), SNAP.indexOf("function syncHiddenFold("));
  assert.match(paint, /const focusedFold = !!focused && host\.contains\(focused\) && !!focused\.closest\("\.snap-hidden"\);/, "read before the update: focus anywhere in the fold (its head, a row)");
  assert.ok(paint.indexOf("const focusedFold =") < paint.indexOf("reconcileRows<SnapRow, Element>("), "before the reconcile");
  assert.match(paint, /syncHiddenFold\(host, next\);\s*\n\s*const foldGone = focusedFold && !hid\.length;/, "decided after the sync that hides the fold");
  assert.match(paint, /if \(focused && host\.contains\(focused\) && !foldGone\) \{ if \(document\.activeElement !== focused\) focused\.focus\(\); \}/, "a node still in the host keeps focus, unless its fold has gone");
  assert.match(paint, /else if \(foldGone\) list\.lastElementChild\?\.querySelector<HTMLElement>\("\.snap-row"\)\?\.focus\(\);/, "the fold gone: the last shown row");
  assert.ok(paint.indexOf("else if (same)") < paint.indexOf("else if (foldGone)") && paint.indexOf("else if (foldGone)") < paint.indexOf("else if (focusedList && focusedAt >= 0"),
    "the same session's new place first, then the fold's neighbour, then the row in its place");
});

test("pinned: the Hidden fold's open state is THE SECTION'S OWN (round 1): opening it in one group's snapshot leaves every other group's fold closed", () => {
  // one page-wide bit, toggled by the head and reset by nothing, arrived open in every later section's snapshot for the
  // page's life; the memory is keyed to the thing folded now (a set of section names), as the strip's folds are keyed to
  // sections, and each fold starts closed until opened there
  assert.match(SNAP, /^const snapHiddenOpen = new Set<string>\(\);/m);
  assert.equal(SNAP.split("snapHiddenOpen").length - 1, 6, "the set; the head's toggle (has, delete, add); the focus rule and syncHiddenFold read it; nothing else");
  assert.match(SNAP, /const open = snapHiddenOpen\.has\(m\.name\);[^\n]*\n\s*fold\.style\.display = n \? "" : "none";\s*\n\s*fold\.classList\.toggle\("open", open\);\s*\n\s*const words = hiddenFoldWords\(n, hiddenNeeds\(m\.rows\), open\);/);
  assert.match(SNAP, /fold\.querySelector<HTMLElement>\("\.snap-hidden-list"\)!\.style\.display = open \? "" : "none";/);
  assert.doesNotMatch(SNAP, /snapHiddenOpen\.clear\(\)/, "a memory, like the strip's folds: leaving the pane and coming back finds the section's fold as it was left");
});

test("executed: the store CARRIES A KEY THIS BUILD DOES NOT KNOW through its writes (round 1): an older pane's fold no longer drops a newer build's list", () => {
  // at the list's introduction a pane still on the previous bundle that folded a group rewrote the blob from the fields it
  // knew and dropped `hidden`, un-hiding every session in the browser's other panes with no gesture on them. From this build
  // on, parseTabGroups keeps what it does not know (`rest`) and writeTabGroups writes it back first, the known keys over it.
  const raw = '{"on":true,"collapsed":["qa"],"pinned":[],"hidden":[{"sid":"api","name":"infra","id":"g1"}],"later":[{"sid":"web","name":"infra"}],"laterFlag":true}';
  const st = parseTabGroups(raw);
  assert.deepEqual(st.rest, { later: [{ sid: "web", name: "infra" }], laterFlag: true }, "the unknown keys, as they came");
  assert.equal(parseTabGroups(null).rest, undefined, "a fresh state has none");
  assert.equal(parseTabGroups('{"on":true}').rest, undefined, "nor a blob of known keys alone");
  assert.equal(parseTabGroups('{"followed":{"g1":"infra"},"followedSeq":{"g1":3}}').rest, undefined, "the memory's keys are known");
  const store = new Map<string, string>();
  const g: any = globalThis;
  const savedLS = g.localStorage;
  g.localStorage = { getItem: (k: string) => store.get(k) ?? null, setItem: (k: string, v: string) => { store.set(k, v); } };
  try {
    writeTabGroups(setSectionCollapsed(st, "qa", false));   // a fold gesture on the older build's part
    const back = JSON.parse(store.get(TABGROUPS_KEY)!);
    assert.deepEqual(back.later, [{ sid: "web", name: "infra" }], "the newer build's list rides the round trip");
    assert.equal(back.laterFlag, true);
    assert.deepEqual([back.collapsed, back.hidden], [[], [{ sid: "api", name: "infra", id: "g1" }]], "the known keys are this build's, over the carried ones");
    assert.deepEqual(readTabGroups(unions).rest, { later: [{ sid: "web", name: "infra" }], laterFlag: true }, "and read back");
    writeTabGroups({ ...parseTabGroups(null), rest: { hidden: "junk", other: 1 } });
    assert.deepEqual([JSON.parse(store.get(TABGROUPS_KEY)!).hidden, JSON.parse(store.get(TABGROUPS_KEY)!).other], [[], 1], "a known key never hides under rest: this build's list is written");
  } finally {
    g.localStorage = savedLS;
  }
  // ROUND 2: an unknown key is written back for the life of the store, so a KNOWN key that a later build retires needs a
  // dropped-keys set beside KNOWN_KEYS, or every pane on that build carries the stale value forever; the note stands at the set
  assert.match(GROUPS, /RETIRING A KEY: taking it out of this set is not enough\.[\s\S]{0,400}const KNOWN_KEYS: ReadonlySet<string> = new Set\(\["on", "collapsed", "expanded", "pinned", "hidden", "followed", "followedSeq"\]\);/);
  // the carry survives every write path's spread: the hide, the pin, the fold, the prune, the rename follow
  assert.deepEqual(setHidden(st, INFRA, "web", true).rest, st.rest);
  assert.deepEqual(setPinned(st, INFRA, "web", true).rest, st.rest);
  assert.deepEqual(setSectionCollapsed(st, "infra", true).rest, st.rest);
  assert.deepEqual(prunePinned(st, unions, new Set(ALL), HOSTS).rest, st.rest);
  assert.deepEqual(followTagRenames(st, [], unions, V).rest, st.rest);
});
