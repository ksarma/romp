// THE SECTION SNAPSHOT (the user 2026-09-06): a header click shows the section's sessions in the
// transcript's place — one row each: name, emoji, identity color, state pip, needs-you / waiting, ⚑,
// what it is doing now, when it last did anything, the last message on hover — and a row opens its
// session. Executed on the pure model (tab-snapshot.ts) from synthetic frame data, and source-pinned on
// render.ts / styles.css / docs (the renderer has no jsdom — the tab-groups.test.ts harness). The
// demo world only: a notes-api with web / api / tests sessions, placeholder ids, invented text.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { snapshotModel, snapshotRow, snapshotHeading, rowWords, rowState, nowLine, lastActivity, lastMessage, sameModel,
         type SnapModel, type SnapSessionLike, type SnapLedgerLike } from "./tab-snapshot";

const ui = (...p: string[]) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", ...p), "utf8");
const RENDER = ui("webview", "render.ts");
const CSS = ui("webview", "styles.css");
const GUIDE = fs.readFileSync(path.resolve(process.cwd(), "..", "docs", "guide.md"), "utf8");
const KERNEL = fs.readFileSync(path.resolve(process.cwd(), "..", "kernel", "kernel.py"), "utf8");

const SNAP = RENDER.slice(RENDER.indexOf("let snapView: string | null = null;"), RENDER.indexOf("function showActive() {"));
const SHOW = RENDER.slice(RENDER.indexOf("function showActive() {"), RENDER.indexOf("function showActive() {") + 3200);

const T0 = 1781100000;
const iso = (t: number) => new Date(t * 1000).toISOString();
const sec = { name: "infra", color: "#4EC9B0", ids: ["web", "api", "tests"] };
const sessions = new Map<string, SnapSessionLike>([
  ["web", { name: "web", emoji: "🌐", color: { bg: "#3a7bd5", fg: "#ffffff" }, status: { state: "working", sinceEpoch: T0 - 30 }, userTodos: [],
            events: [{ kind: "user", md: "please add the notes list page", ts: iso(T0 - 300) }, { kind: "assistant", md: "Adding the list page now — the\n\nroute and the template.", ts: iso(T0 - 40) }, { kind: "tool", ts: iso(T0 - 20) }] }],
  ["api", { name: "api", color: { bg: "#d53a3a", fg: "#ffffff" }, status: { state: "needsInput", sinceEpoch: T0 - 600 }, userTodos: [{ id: "t1" }, { id: "t2" }],
            events: [{ kind: "assistant", md: "Which database should the notes table use?", ts: iso(T0 - 600) }] }],
  ["tests", { name: "tests", color: null, status: { state: "awaitingBg", sinceEpoch: T0 - 900 }, events: [] }],
]);
const ledgers = new Map<string, SnapLedgerLike>([
  ["web", { summary: "Building the notes-api web pages", workingNote: "editing the list page template", tree: [{ text: "Add the notes list page", current: true }], recent: [{ text: "Add the notes list page", t: T0 - 300 }] }],
  ["api", { summary: "Designing the notes schema", tree: [{ text: "Pick a database", current: true }], recent: [] }],
  ["tests", { summary: "", tree: [], recent: [{ text: "Run the notes-api suite", t: T0 - 4000 }] }],
]);
const look = (m: Map<string, unknown>) => (id: string) => (m.get(id) as any) ?? null;

test("executed: one row per member in strip order, from what the client already holds — name, emoji, color, pip by the tab's rule, flags, now line, last activity", () => {
  const m = snapshotModel(sec, look(sessions), look(ledgers), null);
  assert.equal(m.name, "infra"); assert.equal(m.color, "#4EC9B0");
  assert.deepEqual(m.rows.map((r) => r.id), ["web", "api", "tests"], "strip order, never re-sorted");
  const [web, api, tests] = m.rows;
  assert.deepEqual([web.name, web.emoji, web.color, web.pip, web.state, web.needsYou, web.waiting, web.todos, web.closed, web.loading],
    ["web", "🌐", { bg: "#3a7bd5", fg: "#ffffff" }, "working", "working", false, false, 0, false, false]);
  assert.equal(web.now, "editing the list page template", "the working note leads: the session's own claim of what it is doing");
  assert.equal(web.lastT, T0 - 20, "the newest event in the tail, whatever its kind");
  assert.equal(web.lastMsg, "Adding the list page now — the route and the template.", "the last ASSISTANT message, one line");
  assert.deepEqual([api.pip, api.state, api.needsYou, api.todos], ["awaiting", "needs you — waiting on your answer", true, 2], "a live prompt is on you — the tab's red");
  assert.equal(api.now, "Pick a database", "no note → the current task");
  assert.deepEqual([tests.pip, tests.state, tests.waiting, tests.needsYou], ["waiting", "waiting on background work", true, false], "awaitingBg: waiting, not on you (the Outline's await-green)");
  assert.equal(tests.now, "Run the notes-api suite", "no note, no current task, no summary → the most recent top");
  assert.equal(tests.lastT, T0 - 900, "an empty tail → the state's start");
  assert.equal(tests.lastMsg, "");
});

test("executed: the now line's precedence — note, current task, summary, recent top, nothing — and one line always", () => {
  assert.equal(nowLine({ workingNote: "  a  note\nwith   breaks ", summary: "s" }), "a note with breaks");
  assert.equal(nowLine({ workingNote: "", tree: [{ text: "done one", current: false }, { text: "the current one", current: true }], summary: "s" }), "the current one");
  assert.equal(nowLine({ tree: [{ text: "", current: true }], summary: "the headline" }), "the headline", "a blank current text does not win");
  assert.equal(nowLine({ summary: "   ", recent: [{ text: "" }, { text: "last top" }] }), "last top");
  assert.equal(nowLine({}), ""); assert.equal(nowLine(null), "");
  assert.equal(nowLine({ workingNote: "x".repeat(300) }).length, 200, "capped: the row is one line and the model stays small");
  assert.ok(nowLine({ workingNote: "x".repeat(300) }).endsWith("…"));
});

test("executed: the pip and the state word follow tab-state.ts — on-you red, transient amber, closed struck, idle none", () => {
  assert.deepEqual(rowState({ state: "blocked", apiTooLong: true }), { pip: "blocked", state: "needs you — stopped on an API error", needsYou: true, waiting: false, closed: false });
  assert.deepEqual(rowState({ state: "blocked" }).pip, "retrying", "a transient API error is the tab's amber, not red");
  assert.deepEqual(rowState({ state: "retrying" }), { pip: "retrying", state: "API error, retrying on its own", needsYou: false, waiting: false, closed: false });
  assert.deepEqual(rowState({ state: "awaiting" }).pip, "awaiting", "the legacy name an older remote kernel sends");
  assert.deepEqual(rowState({ state: "compacting" }), { pip: "compacting", state: "compacting", needsYou: false, waiting: false, closed: false });
  assert.equal(rowState({ state: "clearing" }).state, "clearing");
  assert.deepEqual(rowState({ state: "closed" }), { pip: "", state: "closed", needsYou: false, waiting: false, closed: true });
  for (const st of ["ready", "idle"]) assert.deepEqual(rowState({ state: st }), { pip: "", state: "", needsYou: false, waiting: false, closed: false }, st + ": no pip, as in the Outline");
  assert.equal(rowState({ state: "opening" }).pip, "unknown");
  assert.equal(rowState(null).pip, "unknown");
  // a user todo is on you whatever the state
  const r = snapshotRow("web", { name: "web", status: { state: "ready" }, userTodos: [{ id: "t1" }] }, null);
  assert.deepEqual([r.pip, r.needsYou, r.todos], ["", true, 1]);
});

test("executed: a placeholder tab (no session frame yet) is a loading row with the meta it has; a closed session is struck", () => {
  const r = snapshotRow("new1", null, null);
  assert.deepEqual([r.name, r.pip, r.loading, r.lastT, r.now, r.lastMsg], ["(unnamed)", "unknown", true, null, "", ""]);
  const meta = snapshotRow("new1", { name: "new1", color: { bg: "#123456", fg: "#ffffff" } }, null);   // the strip's tabMeta shape: name + color, no status
  assert.deepEqual([meta.name, meta.pip, meta.loading, meta.color], ["new1", "unknown", false, { bg: "#123456", fg: "#ffffff" }]);
  assert.equal(snapshotRow("old", { name: "old", status: { state: "closed" } }, null).closed, true);
  assert.equal(rowWords(snapshotRow("new1", null, null)).label, "(unnamed) — opening");
});

test("executed: lastActivity walks the tail from the end and skips undated atoms; lastMessage takes the newest assistant text", () => {
  assert.equal(lastActivity({ events: [{ kind: "assistant", ts: iso(T0 - 10) }, { kind: "tool" }], status: { state: "working", sinceEpoch: T0 - 99 } }), T0 - 10);
  assert.equal(lastActivity({ events: [{ kind: "postal-service", t: T0 - 5.7 }] }), T0 - 6);
  assert.equal(lastActivity({ events: [{ kind: "tool", ts: "not a date" }], status: { state: "ready", sinceEpoch: T0 - 1 } }), T0 - 1);
  assert.equal(lastActivity({ events: [], status: { state: "ready", sinceEpoch: null } }), null);
  assert.equal(lastMessage({ events: [{ kind: "assistant", md: "first" }, { kind: "user", md: "q" }, { kind: "assistant", md: "  second   line \n two " }, { kind: "tool" }] }), "second line two");
  assert.equal(lastMessage({ events: [{ kind: "assistant", md: "" }] }), "");
});

test("executed: a push that changes nothing a row shows returns the SAME model object — the no-rebuild contract", () => {
  const a = snapshotModel(sec, look(sessions), look(ledgers), null);
  // a fresh frame: new session objects, new arrays, the same content (the client rebuilds them per push)
  const clone = new Map<string, SnapSessionLike>([...sessions].map(([k, v]) => [k, JSON.parse(JSON.stringify(v))]));
  const b = snapshotModel(sec, look(clone), look(ledgers), a);
  assert.equal(b, a, "same object: the renderer skips the rebuild (only the ago texts tick)");
  // the same content in a fresh section object, a fresh color string — still the same model
  assert.equal(snapshotModel({ ...sec, ids: [...sec.ids] }, look(clone), look(ledgers), a), a);
  // a status the row does not show (sinceEpoch when the tail has events; a model name) changes nothing
  const noisy = new Map(clone); noisy.set("web", { ...clone.get("web")!, status: { state: "working", sinceEpoch: T0 - 1 } });
  assert.equal(snapshotModel(sec, look(noisy), look(ledgers), a), a, "a flapping input the row never reads cannot move it");
  assert.ok(sameModel(a, a) && !sameModel(null, a));
});

test("executed: new information yields a NEW model — a state change, a new event, a note, a todo, a member, a rename", () => {
  const a = snapshotModel(sec, look(sessions), look(ledgers), null);
  const with_ = (id: string, patch: Partial<SnapSessionLike>) => { const m = new Map(sessions); m.set(id, { ...sessions.get(id)!, ...patch }); return m; };
  assert.notEqual(snapshotModel(sec, look(with_("web", { status: { state: "ready" } })), look(ledgers), a), a, "state");
  assert.notEqual(snapshotModel(sec, look(with_("web", { events: [...sessions.get("web")!.events!, { kind: "assistant", md: "Done.", ts: iso(T0) }] })), look(ledgers), a), a, "a new event (time and last message)");
  assert.notEqual(snapshotModel(sec, look(with_("web", { userTodos: [{ id: "t9" }] })), look(ledgers), a), a, "a todo");
  assert.notEqual(snapshotModel(sec, look(with_("web", { name: "web2" })), look(ledgers), a), a, "a rename");
  assert.notEqual(snapshotModel(sec, look(with_("web", { emoji: "" })), look(ledgers), a), a, "the emoji");
  const l2 = new Map(ledgers); l2.set("web", { ...ledgers.get("web")!, workingNote: "reviewing the tests" });
  assert.notEqual(snapshotModel(sec, look(sessions), look(l2), a), a, "the working note");
  assert.notEqual(snapshotModel({ ...sec, ids: ["web", "api"] }, look(sessions), look(ledgers), a), a, "a member gone");
  assert.notEqual(snapshotModel({ ...sec, name: "infra2" }, look(sessions), look(ledgers), a), a, "the section itself");
  assert.notEqual(snapshotModel(sec, look(with_("web", { color: { bg: "#000000", fg: "#ffffff" } })), look(ledgers), a), a, "the identity color");
});

test("executed: the words — the heading's count and label, the row's spoken label and hover title", () => {
  assert.deepEqual(snapshotHeading("infra", 3), { count: "3 sessions", label: "infra: 3 sessions; click one to open it" });
  assert.equal(snapshotHeading("qa", 1).count, "1 session");
  const m = snapshotModel(sec, look(sessions), look(ledgers), null);
  assert.equal(rowWords(m.rows[0]).label, "web — working — editing the list page template");
  assert.equal(rowWords(m.rows[0]).title, "Last message: Adding the list page now — the route and the template.\nClick to open this session.");
  assert.equal(rowWords(m.rows[1]).label, "api — needs you — waiting on your answer — 2 things it needs from you — Pick a database");
  assert.equal(rowWords(m.rows[2]).title, "No messages yet.\nClick to open this session.");
  assert.equal(rowWords(snapshotRow("x", { name: "x", status: { state: "ready" }, userTodos: [{}] }, null)).label, "x — 1 thing it needs from you");
});

test("pinned: render.ts shows the snapshot on a header click — snapView set BEFORE the fold write, then the pane swaps; a session pick clears it", () => {
  assert.match(RENDER, /"toggle-group": \(el\) => \{\s*\n\s*const name = el\.dataset\.group;\s*\n\s*if \(!name\) return;\s*\n\s*snapView = name;\s*\n\s*writeTabGroups\(setSectionCollapsed\(tabGroups\(\), name, el\.dataset\.folded !== "1"\)\);\s*\n\s*showActive\(\);/,
    "one rule for open and folded headers: fold or open, and look at the section");
  assert.match(RENDER, /const leavingSnap = snapView !== null;\s*\n\s*snapView = null;\s*\n\s*if \(collapsedTabIds\.has\(id\)\) unfoldSectionOf\(id\);\s*\n\s*if \(activeId === id && anchor == null && anchorT == null\) \{[^\n]*\n\s*if \(leavingSnap\) \{ renderTabs\(\); showActive\(\); \}/,
    "setActive: the pick ends the snapshot, opens a folded-away tab's section, and puts the transcript back even when the pick is the tab already active");
  assert.match(RENDER, /if \(snapView === name\) head\.classList\.add\("snap-shown"\);/, "the header whose section the pane shows is marked");
  assert.match(CSS, /\.tab-group-head\.snap-shown \.tab-group-name \{ color: var\(--fg\); \}/);
});

test("pinned: the open-from-card path — a real button per row, data-act=open on the ONE stable host's delegate, opens + focuses the session", () => {
  assert.match(SNAP, /host = el\("div", "tab-snapshot"\);\s*\n\s*host\.id = "tab-snapshot";\s*\n\s*host\.setAttribute\("role", "region"\);/, "made once");
  assert.match(SNAP, /delegate\(host, \{ open: \(node\) => \{ const id = node\.dataset\.id; if \(id\) \{ setActive\(id\); focusActiveTab\(\); \} \} \}\);/, "installed once, with the host (click-safe: rows are rebuilt)");
  assert.equal(SNAP.split("delegate(host").length - 1, 1, "one delegate, never in the render");
  assert.match(SNAP, /const btn = document\.createElement\("button"\);\s*\n\s*btn\.type = "button";/, "a real button: Tab reaches it, Enter opens");
  assert.match(SNAP, /btn\.dataset\.act = "open"; btn\.dataset\.id = r\.id;/);
  assert.match(SNAP, /btn\.setAttribute\("aria-label", words\.label\);\s*\n\s*btn\.title = words\.title;/, "the pure module's words: the spoken label and the last-message hover");
  assert.match(SNAP, /item\.setAttribute\("role", "listitem"\)/); assert.match(SNAP, /list\.setAttribute\("role", "list"\)/);
  assert.match(SNAP, /const h = document\.createElement\("h2"\); h\.className = "snap-head";/, "a heading, for the structure");
  assert.match(SNAP, /host\.setAttribute\("aria-label", words\.label\);/, "the region is named");
  // the strip's own vocabulary on the row: the tab's emoji node, the tab's ⚑, the identity color on the name
  assert.match(SNAP, /const em = tabEmojiNode\(r\.emoji\); if \(em\) btn\.appendChild\(em\);/);
  assert.match(SNAP, /const g = el\("span", "tab-usertodo"\); g\.textContent = "⚑";/);
  assert.match(SNAP, /if \(r\.color\) name\.style\.color = r\.color\.bg;/);
  assert.match(SNAP, /pip\.setAttribute\("aria-hidden", "true"\)/, "the pip is decoration: its phrase rides the label");
});

test("pinned: a no-change push rebuilds nothing — same object → only the ago texts tick in place; the section gone → the transcript", () => {
  assert.match(SNAP, /const next = snapshotModel\(head\.head, \(id\) => sessions\.get\(id\) \?\? null, \(id\) => ledgers\.get\(id\) \?\? null, snapModel\);\s*\n\s*if \(next === snapModel && host\.childElementCount\) \{/,
    "the same-object check gates the rebuild");
  assert.match(SNAP, /for \(const w of host\.querySelectorAll<HTMLElement>\("\.snap-when\[data-t\]"\)\) \{\s*\n\s*const t = Number\(w\.dataset\.t\); if \(!t\) continue;\s*\n\s*w\.textContent = agehms\(now - t\) \+ " ago"; w\.style\.color = ageColorReadable\(now - t\);/,
    "the model carries epochs, not text: the clock is the renderer's");
  assert.match(SNAP, /if \(!head\) \{ snapView = null; hideSnapshot\(\); return false; \}/, "the section's absence from the strip is the event that ends the view");
  assert.match(RENDER, /if \(snapView\) renderSnapshot\(\);/, "renderTabs (every push) refreshes it");
  assert.match(SHOW, /if \(snapView && renderSnapshot\(\)\) \{\s*\n\s*for \(const v of views\.values\(\)\) v\.el\.style\.display = "none";/, "showActive: every transcript hidden under it");
  assert.match(SHOW, /if \(ta\) \{ ta\.disabled = true; ta\.placeholder = "Pick a session above to write to it"; \}/, "the composer says what to do instead of taking a message with no session");
  assert.match(SHOW, /hideSnapshot\(\);\s*\n\s*const s = activeId \? sessions\.get\(activeId\) : null;/, "a transcript showing → the snapshot hidden");
  assert.match(RENDER, /if \(snapView\) \{ sl\.replaceChildren\(\); return; \}/, "no session's statusline chip under a section list");
  assert.match(RENDER, /if \(!activeId \|\| !liveAsks\.has\(activeId\) \|\| snapView\) \{/, "no live ask card under it");
  assert.match(RENDER, /const s = activeId && !snapView \? sessions\.get\(activeId\) : null;/, "no background-task box under it");
});

test("pinned: the sheet — two sizes (the body's and the header's 0.82em), tokens only, the tab's state colors on the pip, the one action hover", () => {
  const block = CSS.slice(CSS.indexOf("#tab-snapshot {"), CSS.indexOf(".snap-when {") + 200);
  assert.deepEqual([...new Set(block.match(/font-size: [^;]+/g))], ["font-size: 0.82em"], "one sub-line size, the header's; the rest inherit the body");
  assert.match(block, /\.snap-pip\.working \{ background: var\(--st-working-bg\); \}/);
  assert.match(block, /\.snap-pip\.blocked \{ background: var\(--st-blocked-bg\); \}/);
  assert.match(block, /\.snap-pip\.awaiting \{ background: var\(--st-awaiting-bg\); \}/);
  assert.match(block, /\.snap-pip\.waiting \{ background: var\(--st-awaitbg-bg\); \}/);
  assert.match(block, /\.snap-pip\.retrying \{ background: #e67e22; \}/, "the tab's own amber literal (.tab.tab-retrying)");
  assert.match(block, /\.snap-row:hover \{ border-color: var\(--accent\); background: var\(--accent-wash\); \}/);
  assert.match(block, /\.snap-row:focus-visible \{ outline: 1px solid var\(--accent\); outline-offset: -1px; \}/);
  assert.match(block, /\.snap-flag\.needs \{ border-color: transparent; background: var\(--st-blocked-bg\); color: var\(--st-blocked-fg\); \}/, "needs you in the status red, not the accent");
  const stripped = block.replace(/\/\*[\s\S]*?\*\//g, "").replace(/var\([^)]*\)/g, "V");
  assert.deepEqual(stripped.match(/#[0-9a-fA-F]{3,8}\b/g), ["#e67e22"], "no other raw color: the light theme needs no override");
});

test("pinned: the kernel puts the working note on the ledger the chat already receives — one field, no new frame", () => {
  assert.match(KERNEL, /"current": current, "recent": recent_tops,\s*\n(?:\s*#[^\n]*\n)*\s*"workingNote": Sessions\.working_note\(sid\)\}/);
});

test("the guide describes the view and the new fold rule", () => {
  assert.match(GUIDE, /\*\*A section at a glance\.\*\* Clicking a header also shows the section in the transcript's place/);
  assert.match(GUIDE, /The section of the\s+tab you are reading folds like any other; its header then stands in for the tab/);
  assert.doesNotMatch(GUIDE, /never\s+folds \(its header says so/, "the old rule is gone from the guide");
});
