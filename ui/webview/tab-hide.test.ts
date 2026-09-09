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
import { snapshotModel, snapshotRow, snapshotHeading, hiddenNeeds, hiddenFoldWords, actWords, rowWords, onYou, standInPip, type SnapModel } from "./tab-snapshot";
import { sectionPip, sectionTodoFlag, sectionTodoTitle, sectionTodoPhrase, sectionDoorTitle, doorClick, compactCount, stripAndHidden, SHOW_GROUP_CLICK, BACK_TO_TRANSCRIPT_CLICK } from "./tab-state";
import { repeatedClick } from "./tab-snapshot-view";

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
  assert.match(SNAP, /hide: once\(\(node\) => setRowHidden\(node\.dataset\.id, true\)\),\s*\n\s*show: once\(\(node\) => setRowHidden\(node\.dataset\.id, false\)\),/, "explicit on and off, never a toggle of the stored bit; once per gesture (its own test below)");
  assert.match(SNAP, /"toggle-hidden": once\(\(\) => \{\s*\n\s*if \(!snapView\) return;\s*\n\s*if \(snapHiddenOpen\.has\(snapView\)\) snapHiddenOpen\.delete\(snapView\); else snapHiddenOpen\.add\(snapView\);\s*\n\s*const h = document\.getElementById\("tab-snapshot"\);\s*\n\s*if \(h && snapModel\) syncHiddenFold\(h, snapModel\);\s*\n\s*\}\) \}\);/,
    "the fold's head: view state of the section the pane shows, no store write, no strip render");
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
  assert.match(flat, /fold the group and open it again, and the hidden sessions stay hidden while the rest come back\./);
  assert.match(flat, /The group's header keeps the dot and the ⚑ flag for its hidden sessions \(the dot is red when one of them needs you\), and its count shows two numbers, \*\*6\+2\*\* for six on the strip and two hidden \(the tooltip spells it out\)\./, "the compact count (headWords, compactCount; the user 2026-09-08: the words were too wide a head), and the dot reads the feed too (standInPip)");
  assert.match(flat, /the fold's head says so in red before you open it, and its row says \*\*needs you\*\*\./);
  assert.match(flat, /While the group is open, its count opens this view without folding the group, so hiding a session never needs a fold; the dot and the flag, which appear once something is hidden, do the same\. On a folded header the flag opens the group, as before\./, "the non-folding door, on every open header (round 2: the sentence had claimed the count for a door before the first hide, when it was a plain span)");
  assert.match(flat, /On a folded header the flag opens the group, as before\. While this view shows an open group, its count, dot and flag take you back to the transcript\. Clicking a hidden session's row/, "round 3: the count, the dot and the flag of the group the pane shows are the way back (the sentence on the header's second click, pinned by tab-snapshot.test, stands as it was); round 4: an OPEN group's (a folded group the view shows has no door: its count is a plain span and its flag opens the group)");
  assert.doesNotMatch(flat, /While this view shows a group, its count/, "round 4: the unqualified sentence promised the way back on a folded group's marks too");
  assert.match(flat, /Clicking a hidden session's row shows its transcript, with the header standing in for the tab, and leaves it hidden, its group folded or open as it was\./);
  assert.match(flat, /the hide wins, and the setting resumes when you show it again\./);
  assert.match(flat, /keeps the setting when its group is renamed, and shows again wherever it lands when it leaves the group\./);
  assert.match(GUIDE.replace(/\s+/g, " "), /click one to open that session, which also opens its section if the section is folded \(a hidden session's section stays as it was; see the next paragraph\)\./, "the older sentence about a pick opening the section is exact for hidden members now (round 1)");
  assert.ok(!para.includes("—"), "no em dash in the new guide text");
  assert.ok(!/fleet/i.test(para));
  const ref = REF.slice(REF.indexOf("### The tab strip's per-browser choices"), REF.indexOf("### Model and effort, from the statusline or a typed command")).replace(/\s+/g, " ");
  assert.match(ref, /`romp:tabgroups`, not on the kernel/);
  assert.match(ref, /which sessions are hidden inside their group \(\*\*Hide\*\*, in the section's at-a-glance view\)/, "the guide's name for the surface (round 1: \"the group view\" appeared nowhere else)");
  assert.doesNotMatch(REF, /group view/);
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
