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
import { snapshotModel, snapshotRow, snapshotHeading, rowWords, rowState, nowLine, noteLine, lastActivity, lastMessage,
         plainText, sameModel, FEED_BLOCK_STATE, type SnapModel, type SnapSessionLike, type SnapLedgerLike } from "./tab-snapshot";

const ui = (...p: string[]) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", ...p), "utf8");
const RENDER = ui("webview", "render.ts");
const CSS = ui("webview", "styles.css");
const GUIDE = fs.readFileSync(path.resolve(process.cwd(), "..", "docs", "guide.md"), "utf8");
const KERNEL = fs.readFileSync(path.resolve(process.cwd(), "..", "kernel", "kernel.py"), "utf8");

const SNAP = RENDER.slice(RENDER.indexOf("let snapView: string | null = null;"), RENDER.indexOf("function showActive() {"));
const SHOW = RENDER.slice(RENDER.indexOf("function showActive() {"), RENDER.indexOf("function showActive() {") + 3200);

const T0 = 1781100000;
const iso = (t: number) => new Date(t * 1000).toISOString();
const ms = (t: number) => t * 1000;   // status.sinceEpoch is MILLISECONDS on the wire (the kernel's since_ms, render's Date.now())
const sec = { name: "infra", color: "#4EC9B0", ids: ["web", "api", "tests"] };
const sessions = new Map<string, SnapSessionLike>([
  ["web", { name: "web", emoji: "🌐", color: { bg: "#3a7bd5", fg: "#ffffff" }, status: { state: "working", sinceEpoch: ms(T0 - 30) }, userTodos: [],
            events: [{ kind: "user", md: "please add the notes list page", ts: iso(T0 - 300) }, { kind: "assistant", md: "Adding the list page now — the\n\nroute and the template.", ts: iso(T0 - 40) }, { kind: "tool", ts: iso(T0 - 20) }] }],
  ["api", { name: "api", color: { bg: "#d53a3a", fg: "#ffffff" }, status: { state: "needsInput", sinceEpoch: ms(T0 - 600) }, userTodos: [{ id: "t1" }, { id: "t2" }],
            events: [{ kind: "assistant", md: "Which database should the notes table use?", ts: iso(T0 - 600) }] }],
  ["tests", { name: "tests", color: null, status: { state: "awaitingBg", sinceEpoch: ms(T0 - 900) }, events: [] }],
]);
const ledgers = new Map<string, SnapLedgerLike>([
  ["web", { summary: "Building the notes-api web pages", workingNote: "editing the list page template", needsInput: false, tree: [{ text: "Add the notes list page", current: true }], recent: [{ text: "Add the notes list page", t: T0 - 300 }] }],
  ["api", { summary: "Designing the notes schema", needsInput: true, tree: [{ text: "Pick a database", current: true }], recent: [] }],
  ["tests", { summary: "", needsInput: false, tree: [], recent: [{ text: "Run the notes-api suite", t: T0 - 4000 }] }],
]);
const look = (m: Map<string, unknown>) => (id: string) => (m.get(id) as any) ?? null;

test("executed: one row per member in strip order, from what the client already holds — name, emoji, color, pip by the tab's rule, flags, now line, last activity", () => {
  const m = snapshotModel(sec, look(sessions), look(ledgers), null);
  assert.equal(m.name, "infra"); assert.equal(m.color, "#4EC9B0");
  assert.deepEqual(m.rows.map((r) => r.id), ["web", "api", "tests"], "strip order, never re-sorted");
  const [web, api, tests] = m.rows;
  assert.deepEqual([web.name, web.emoji, web.color, web.pip, web.state, web.needsYou, web.waiting, web.todos, web.closed, web.loading],
    ["web", "🌐", { bg: "#3a7bd5", fg: "#ffffff" }, "working", "working", false, false, 0, false, false]);
  assert.equal(web.now, "Add the notes list page", "the now line is the judges' current task, in the user's terms, even when a note is published");
  assert.equal(web.note, "editing the list page template", "the working note is the row's own second line, never the now line");
  assert.equal(web.lastT, T0 - 20, "the newest event in the tail, whatever its kind");
  assert.equal(web.lastMsg, "Adding the list page now — the route and the template.", "the last ASSISTANT message, one line");
  assert.deepEqual([api.pip, api.state, api.needsYou, api.todos], ["awaiting", "needs you — waiting on your answer", true, 2], "a live prompt is on you — the tab's red");
  assert.equal(api.now, "Pick a database", "the current task");
  assert.equal(api.note, "", "no note → no second line");
  assert.deepEqual([tests.pip, tests.state, tests.waiting, tests.needsYou], ["waiting", "waiting on background work", true, false], "awaitingBg: waiting, not on you (the Outline's await-green)");
  assert.equal(tests.now, "Run the notes-api suite", "no current task, no summary → the most recent top");
  assert.equal(tests.lastT, T0 - 900, "an empty tail → the state's start, converted from the wire's milliseconds");
  assert.equal(tests.lastMsg, "");
});

test("executed: the now line's precedence (current task, summary, recent top, nothing), one line always; the note is its own line", () => {
  assert.equal(nowLine({ workingNote: "a note", tree: [{ text: "done one", current: false }, { text: "the current one", current: true }], summary: "s" }), "the current one", "a note never leads");
  assert.equal(nowLine({ tree: [{ text: "", current: true }], summary: "the headline" }), "the headline", "a blank current text does not win");
  assert.equal(nowLine({ workingNote: "a note", summary: "   ", recent: [{ text: "" }, { text: "last top" }] }), "last top", "…nor stands in for a missing task");
  assert.equal(nowLine({ workingNote: "a note" }), "", "a note alone leaves the now line empty: it is not what the session is accomplishing");
  assert.equal(nowLine({}), ""); assert.equal(nowLine(null), "");
  assert.equal(nowLine({ summary: "x".repeat(300) }).length, 200, "capped: the row is one line and the model stays small");
  assert.ok(nowLine({ summary: "x".repeat(300) }).endsWith("…"));
  assert.equal(noteLine({ workingNote: "  a  note\nwith   breaks ", summary: "s" }), "a note with breaks", "the note, one line");
  assert.equal(noteLine({ workingNote: "", summary: "s" }), ""); assert.equal(noteLine({}), ""); assert.equal(noteLine(null), "");
  assert.equal(noteLine({ workingNote: "x".repeat(300) }).length, 200, "the same cap");
});

test("executed: needs you follows the FEED's column, not the tab's chip: a judge-filed block flags the row whether the session is idle or active", () => {
  // the common case the tab's rule misses: the agent asked a question and went idle; the feed files its card under needs-you
  const idle = snapshotRow("web", { name: "web", status: { state: "idle" } }, { needsInput: true, tree: [{ text: "Pick a database", current: true }] });
  assert.deepEqual([idle.pip, idle.needsYou, idle.state], ["", true, FEED_BLOCK_STATE], "idle + feed needs-you: flagged, with the feed's word; the pip stays the tab's (none)");
  const ready = snapshotRow("web", { name: "web", status: { state: "ready" } }, { needsInput: true });
  assert.deepEqual([ready.pip, ready.needsYou, ready.state], ["", true, FEED_BLOCK_STATE]);
  // blocked while active: the feed's verdict stands until the judges rule again, even with a turn open (a rejudge in flight)
  const active = snapshotRow("web", { name: "web", status: { state: "working" } }, { needsInput: true });
  assert.deepEqual([active.pip, active.needsYou, active.state], ["working", true, "working"], "active + feed needs-you: flagged; the tab's own state word and pip stay");
  // no feed verdict for this session → the tab's rule alone
  assert.equal(snapshotRow("web", { name: "web", status: { state: "idle" } }, { needsInput: false }).needsYou, false);
  assert.equal(snapshotRow("web", { name: "web", status: { state: "idle" } }, { needsInput: false }).state, "");
  assert.equal(snapshotRow("web", { name: "web", status: { state: "idle" } }, { needsInput: null }).needsYou, false, "null = no feed build yet: not a verdict");
  assert.equal(snapshotRow("web", { name: "web", status: { state: "needsInput" } }, { needsInput: null }).needsYou, true, "…but the tab's live prompt still counts (the feed trails the chip by a push)");
  assert.equal(snapshotRow("web", { name: "web", status: { state: "blocked", apiTooLong: true } }, { needsInput: false }).needsYou, true, "the tab's on-you API error too");
  assert.equal(rowWords(idle).label, "web — needs you — Pick a database", "the spoken label carries the feed's word, once");
});

test("executed: the feed's word claims only what is true of every card in its column (review r2): needs you, no 'stopped'", () => {
  // the column also holds a peer's held message waiting for approval (the session idle, taking input) and the
  // idle user-todo floor; feed.ts marks such a goal "needs you" and nothing about being stopped
  assert.equal(FEED_BLOCK_STATE, "needs you");
  assert.doesNotMatch(FEED_BLOCK_STATE, /stop|answer/);
  const FEED = ui("webview", "feed.ts");
  assert.match(FEED, /"blocked — needs you"/, "the feed pane's own word for a goal in that column");
});

test("executed: the spoken label carries NEEDS YOU whenever the row wears it, whatever the state word (review r2)", () => {
  // the tab's own state words carry it in their text: once, never twice
  const prompt = snapshotRow("api", { name: "api", status: { state: "needsInput" } }, { needsInput: true });
  assert.equal(rowWords(prompt).label, "api — needs you — waiting on your answer");
  const apiErr = snapshotRow("api", { name: "api", status: { state: "blocked", apiTooLong: true } }, null);
  assert.equal(rowWords(apiErr).label, "api — needs you — stopped on an API error");
  // every other state word gets the word in front of it: the review's cases, a rejudge turn and a kept-open closed session
  const rejudge = snapshotRow("web", { name: "web", status: { state: "working" } }, { needsInput: true, tree: [{ text: "Pick a database", current: true }] });
  assert.deepEqual([rejudge.needsYou, rejudge.state], [true, "working"]);
  assert.equal(rowWords(rejudge).label, "web — needs you — working — Pick a database");
  const closed = snapshotRow("web", { name: "web", status: { state: "closed" } }, { needsInput: true });
  assert.deepEqual([closed.needsYou, closed.state], [true, "closed"]);
  assert.equal(rowWords(closed).label, "web — needs you — closed");
  assert.equal(rowWords(snapshotRow("web", { name: "web", status: { state: "compacting" } }, { needsInput: true })).label, "web — needs you — compacting");
  // a todo on an idle row wears the chip too, so the label says so before counting the things
  assert.equal(rowWords(snapshotRow("x", { name: "x", status: { state: "ready" }, userTodos: [{}] }, null)).label, "x — needs you — 1 thing it needs from you");
  // …and never when the row does not wear it
  assert.equal(rowWords(snapshotRow("web", { name: "web", status: { state: "working" } }, { needsInput: false })).label, "web — working");
  assert.equal(rowWords(snapshotRow("web", { name: "web", status: { state: "awaitingBg" } }, { needsInput: null })).label, "web — waiting on background work");
  // a loading row: the flag can be on it only through a ledger the client has no session for; spoken all the same
  assert.equal(rowWords(snapshotRow("new1", null, { needsInput: true })).label, "(unnamed) — needs you — opening");
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

test("executed: lastActivity walks the tail from the end and skips undated atoms; the sinceEpoch fallback converts the wire's milliseconds", () => {
  assert.equal(lastActivity({ events: [{ kind: "assistant", ts: iso(T0 - 10) }, { kind: "tool" }], status: { state: "working", sinceEpoch: ms(T0 - 99) } }), T0 - 10);
  assert.equal(lastActivity({ events: [{ kind: "postal-service", t: T0 - 5.7 }] }), T0 - 6);
  assert.equal(lastActivity({ events: [{ kind: "tool", ts: "not a date" }], status: { state: "ready", sinceEpoch: ms(T0 - 1) } }), T0 - 1);
  assert.equal(lastActivity({ events: [], status: { state: "ready", sinceEpoch: null } }), null);
  // the review's case: a just-created session (events: [], sinceEpoch: Date.now() in ms) 90 s ago must read as 90 s, not as a
  // time far in the future that the renderer clamps to "0s ago"
  const nowS = 1788723633;
  const t = lastActivity({ events: [], status: { state: "opening", sinceEpoch: ms(nowS - 90) } });
  assert.equal(t, nowS - 90); assert.equal(nowS - t!, 90, "an age of 90 s, in the unit the renderer subtracts");
  assert.equal(lastActivity({ events: [], status: { state: "ready", sinceEpoch: ms(T0) + 999 } }), T0, "sub-second ms floor to the second");
});

test("executed: lastMessage takes the newest assistant text as PLAIN words on one line, markdown markers and fences stripped as the file viewer strips them", () => {
  assert.equal(lastMessage({ events: [{ kind: "assistant", md: "first" }, { kind: "user", md: "q" }, { kind: "assistant", md: "  second   line \n two " }, { kind: "tool" }] }), "second line two");
  assert.equal(lastMessage({ events: [{ kind: "assistant", md: "" }] }), "");
  assert.equal(lastMessage({ events: [{ kind: "assistant", md: "**Done.** See `ui/x.ts`:\n```ts\nconst a = 1;\n```\nand [the guide](docs/guide.md)." }] }),
    "Done. See ui/x.ts: const a = 1; and the guide.", "no ** or backticks, no fence line, a link keeps its label");
  assert.equal(plainText("# Heading\n- item *one*\n> quoted ~~gone~~\n1. step", 400), "Heading item one quoted gone step", "block markers go line by line");
  assert.equal(plainText("~~~\ncode\n~~~\nafter", 400), "code after", "tilde fences too: the fence lines go, the fenced body's words stay");
  assert.equal(plainText("x".repeat(500), 400).length, 400, "capped like before");
  assert.equal(lastMessage({ events: [{ kind: "assistant", text: "plain `text` field" }] }), "plain text field", "the text field when there is no md");
});

test("executed: plainText drops inline HTML and underscore emphasis too (review r2): the transcript renders them as structure, a tooltip showed them as typed", () => {
  assert.equal(plainText("<b>x</b>", 400), "x");
  assert.equal(plainText("_x_", 400), "x");
  assert.equal(plainText("<details><summary>Test output</summary>\n12 passed\n</details>", 400), "Test output 12 passed", "the common reply shape: tags go, words stay");
  assert.equal(plainText("<b>bold</b> and <a href='x'>l</a> &amp; <br>", 400), "bold and l &", "tags of every kind, an entity decoded once the tags are gone");
  assert.equal(plainText("__Done__ _emph_ and snake_case __strong__", 400), "Done emph and snake_case strong", "emphasis at word edges goes; snake_case keeps its underscores, as in the file viewer");
  assert.equal(plainText("a < b and c > d", 400), "a < b and c > d", "a bare comparison is not a tag");
  assert.equal(plainText("say &lt;b&gt; &quot;hi&quot; it&#39;s x&nbsp;y", 400), 'say <b> "hi" it\'s x y', "escaped text stays text: decoded after the tag pass, so a typed <b> is not stripped");
  assert.equal(plainText("before <!-- a note\nfor no one --> after", 400), "before after", "an HTML comment goes whole, across lines");
  assert.equal(plainText("line<br>next<br/>last", 400), "line next last", "a break is a space, not a joined word");
  assert.equal(plainText("**Done.** See `ui/x.ts`.", 400), "Done. See ui/x.ts.", "the markdown pass is unchanged");
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
  const l3 = new Map(ledgers); l3.set("web", { ...ledgers.get("web")!, needsInput: true });
  assert.notEqual(snapshotModel(sec, look(sessions), look(l3), a), a, "the feed's needs-you verdict");
  const l4 = new Map(ledgers); l4.set("api", { ...ledgers.get("api")!, needsInput: false });
  assert.equal(snapshotModel(sec, look(sessions), look(l4), a), a, "…but not when the tab's own live prompt already flags the row: nothing shown changed");
  assert.notEqual(snapshotModel({ ...sec, ids: ["web", "api"] }, look(sessions), look(ledgers), a), a, "a member gone");
  assert.notEqual(snapshotModel({ ...sec, name: "infra2" }, look(sessions), look(ledgers), a), a, "the section itself");
  assert.notEqual(snapshotModel(sec, look(with_("web", { color: { bg: "#000000", fg: "#ffffff" } })), look(ledgers), a), a, "the identity color");
});

test("executed: the words — the heading's count and label, the row's spoken label and hover title", () => {
  assert.deepEqual(snapshotHeading("infra", 3), { count: "3 sessions", label: "infra: 3 sessions; click one to open it" });
  assert.equal(snapshotHeading("qa", 1).count, "1 session");
  const m = snapshotModel(sec, look(sessions), look(ledgers), null);
  assert.equal(rowWords(m.rows[0]).label, "web — working — Add the notes list page — its note: editing the list page template", "the task first, the note last, named as the session's own");
  assert.equal(rowWords(m.rows[0]).title, "Last message: Adding the list page now — the route and the template.\nClick to open this session.");
  assert.equal(rowWords(m.rows[1]).label, "api — needs you — waiting on your answer — 2 things it needs from you — Pick a database");
  assert.equal(rowWords(m.rows[2]).title, "No messages yet.\nClick to open this session.");
  assert.equal(rowWords(snapshotRow("x", { name: "x", status: { state: "ready" }, userTodos: [{}] }, null)).label, "x — needs you — 1 thing it needs from you");
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

test("pinned: the kernel puts the working note AND the feed's needs-you verdict on the ledger the chat already receives: two fields, no new frame", () => {
  assert.match(KERNEL, /"current": current, "recent": recent_tops,\s*\n(?:\s*#[^\n]*\n)*\s*"workingNote": Sessions\.working_note\(sid\),\s*\n(?:\s*#[^\n]*\n)*\s*"needsInput": _feed_needs_input_of\(sid\)\}/);
  assert.match(KERNEL, /_feed_needs_input\[0\] = _needs_input_sids\(feed\)/, "set from the feed build's own payload, never re-derived");
  assert.match(KERNEL, /if a\.get\("column"\) == "needs_input" and a\.get\("sid"\)\)/, "the filing rule feed.ts askColumn maps: it.column == needs_input");
  // the chat-build cache: both fields ride the sig, so a background tab's row follows them at the next push
  const SIG = KERNEL.slice(KERNEL.indexOf("def _chat_build_sig(sess):"), KERNEL.indexOf("def _parse(path, sid, now):"));
  assert.match(SIG, /sig\.append\(Sessions\.working_note\(sess\.get\("sid"\) or ""\)\)/);
  assert.match(SIG, /sig\.append\(_feed_needs_input_of\(sess\.get\("sid"\) or ""\) is True\)/,
    "as a BOOL: None (no feed build yet) and False share a signature, so the first feed build after a start does not rebuild every tab (review r2)");
});

test("the guide describes the view and the new fold rule", () => {
  assert.match(GUIDE, /\*\*A section at a glance\.\*\* Clicking a header also shows the section in the transcript's place/);
  assert.match(GUIDE, /The section of the\s+tab you are reading folds like\s+any other; its header then stands in for the tab/);
  assert.doesNotMatch(GUIDE, /never\s+folds \(its header says so/, "the old rule is gone from the guide");
  // the now line's real chain, the note as a second line, needs-you as the feed's word, the hover without markup
  assert.match(GUIDE, /What it is doing now comes from its current task, else from the headline of\s+its work so far, else from the last task it had;/);
  assert.match(GUIDE, /a session that has published a note of what it is\s+working on shows the note as a quieter second line\./);
  assert.match(GUIDE, /\*\*Needs you\*\* appears when the feed shows one of the session's cards under Blocked, when the\s+session is stopped on a prompt or an API error only you can clear, or when it has flagged a todo\s+for you;/,
    "the three triggers of the row's needs-you (tab-snapshot.ts snapshotRow): the feed's column, the tab's own block, an open user todo");
  assert.match(GUIDE, /the \*\*needs you\*\* word\s+follows the feed, at most a moment behind it\./);
  assert.match(GUIDE, /Hover a row for its last message, shown without\s+its formatting;/);
  // the dot is the tab's own state, never the feed's verdict (rowState → pip; the idle feed-filed row has none)
  assert.match(GUIDE, /a dot for its state \(yellow working, red stopped on a\s+prompt or an API error only you can clear, amber retrying an API error on its own, teal compacting,\s+green waiting on background work, none while it is idle\)/,
    "every pip color the sheet paints (.snap-pip.*), by the tab's own state rule (tab-state.ts), and none for idle");
  assert.match(GUIDE, /A session that asked a question and\s+went quiet shows the word with no dot: the dot follows the session's own state, the word follows\s+the feed\./);
  assert.doesNotMatch(GUIDE, /red needs\s+you/, "the old dot rule, a red dot for every needs-you, is gone");
  // the way back: all three exits (render.ts setActive, the Escape listener, show-transcript)
  assert.match(GUIDE, /The transcript comes back when you pick a session, press Escape, or click that header again while\s+its section is open and holds the tab you are reading\./);
  assert.doesNotMatch(GUIDE, /its own note of what\s+it is working on, else its current task/, "the old two-rung chain, note first, is gone");
});
