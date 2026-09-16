// A SECTION AT A GLANCE, THE MODEL (tab-snapshot.ts): a header click shows the section's sessions in the
// transcript's place, one row each: name, emoji, identity color, a state pip, a needs-you or waiting word, a
// user-todo flag, what the session is doing now, when it last did anything, its last message on hover. Executed
// on the pure model from synthetic frame data; the pane's wiring is tab-snapshot-pane.test.ts and the view helpers
// tab-snapshot-view.test.ts. This fork's row vocabulary (the emoji cell, the user todos, the plan's hides) rides the
// same cases, and two source pins at the end read render.ts and docs/guide.md for the fork-only parts. The demo
// world only: a notes-api with web / api / tests sessions, invented text.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { snapshotModel, snapshotRow, snapshotHeading, rowWords, rowState, nowLine, noteLine, lastActivity, lastMessage,
         plainText, sameModel, type SnapSessionLike, type SnapLedgerLike } from "./tab-snapshot";

const T0 = 1781100000;
const iso = (t: number) => new Date(t * 1000).toISOString();
const ms = (t: number) => t * 1000;   // status.sinceEpoch is MILLISECONDS on the wire (the kernel's since_ms, render's Date.now())
const sec = { name: "infra", color: "#4EC9B0", ids: ["web", "api", "tests"] };
const sessions = new Map<string, SnapSessionLike>([
  ["web", { name: "web", emoji: "🌐", color: { bg: "#3a7bd5", fg: "#ffffff" }, status: { state: "working", sinceEpoch: ms(T0 - 30) }, userTodos: [],
            events: [{ kind: "user", md: "please add the notes list page", ts: iso(T0 - 300) },
                     { kind: "assistant", md: "Adding the list page now: the\n\nroute and the template.", ts: iso(T0 - 40) }, { kind: "tool", ts: iso(T0 - 20) }] }],
  ["api", { name: "api", color: { bg: "#d53a3a", fg: "#ffffff" }, status: { state: "needsInput", sinceEpoch: ms(T0 - 600) }, userTodos: [{ id: "t1" }, { id: "t2" }],
            events: [{ kind: "assistant", md: "Which database should the notes table use?", ts: iso(T0 - 600) }] }],
  ["tests", { name: "tests", color: null, status: { state: "awaitingBg", sinceEpoch: ms(T0 - 900) }, events: [] }],
]);
const ledgers = new Map<string, SnapLedgerLike>([
  ["web", { summary: "Building the notes-api web pages", workingNote: "editing the list page template", needsInput: false,
            tree: [{ text: "Add the notes list page", current: true }], recent: [{ text: "Add the notes list page", t: T0 - 300 }] }],
  ["api", { summary: "Designing the notes schema", needsInput: true, tree: [{ text: "Pick a database", current: true }], recent: [] }],
  ["tests", { summary: "", needsInput: false, tree: [], recent: [{ text: "Run the notes-api suite", t: T0 - 4000 }] }],
]);
const look = (m: Map<string, unknown>) => (id: string) => (m.get(id) as any) ?? null;

test("executed: one row per member in strip order, from what the client already holds: name, emoji, color, pip by the tab's rule, words, todo count, now line, note, last activity", () => {
  const m = snapshotModel(sec, look(sessions), look(ledgers), null);
  assert.equal(m.name, "infra"); assert.equal(m.color, "#4EC9B0");
  assert.deepEqual(m.rows.map((r) => r.id), ["web", "api", "tests"], "strip order, never re-sorted");
  const [web, api, tests] = m.rows;
  assert.deepEqual([web.name, web.emoji, web.color, web.pip, web.state, web.needsYou, web.waiting, web.todos, web.closed, web.loading],
    ["web", "🌐", { bg: "#3a7bd5", fg: "#ffffff" }, "working", "working", false, false, 0, false, false]);
  assert.equal(web.now, "Add the notes list page", "the now line is the judges' current task, in the user's terms, even when a note is published");
  assert.equal(web.note, "editing the list page template", "the working note is the row's own second line, never the now line");
  assert.equal(web.lastT, T0 - 20, "the newest event in the tail, whatever its kind");
  assert.equal(web.lastMsg, "Adding the list page now: the route and the template.", "the last ASSISTANT message, one line");
  assert.deepEqual([api.pip, api.state, api.needsYou, api.todos], ["awaiting", "needs you: waiting on your answer", true, 2], "a live prompt is on you: the tab's red; the user todos are counted");
  assert.equal(api.now, "Pick a database", "the current task");
  assert.equal(api.note, "", "no note, no second line");
  assert.deepEqual([tests.pip, tests.state, tests.waiting, tests.needsYou], ["waiting", "Awaiting agents", true, false], "awaitingBg: waiting, not on you; the state in the chip's own words (no kind, no count: the historic default word)");
  assert.equal(tests.now, "Run the notes-api suite", "no current task, no summary: the most recent top");
  assert.equal(tests.lastT, T0 - 900, "an empty tail: the state's start, converted from the wire's milliseconds");
  assert.equal(tests.lastMsg, "");
});

test("executed: the now line's precedence (current task, summary, recent top, nothing), one line always; the note is its own line", () => {
  assert.equal(nowLine({ workingNote: "a note", tree: [{ text: "done one", current: false }, { text: "the current one", current: true }], summary: "s" }), "the current one", "a note never leads");
  assert.equal(nowLine({ tree: [{ text: "", current: true }], summary: "the headline" }), "the headline", "a blank current text does not win");
  assert.equal(nowLine({ workingNote: "a note", summary: "   ", recent: [{ text: "" }, { text: "last top" }] }), "last top", "nor stands in for a missing task");
  assert.equal(nowLine({ workingNote: "a note" }), "", "a note alone leaves the now line empty: it is not what the session is accomplishing");
  assert.equal(nowLine({}), ""); assert.equal(nowLine(null), "");
  assert.equal(nowLine({ summary: "x".repeat(300) }).length, 200, "capped: the row is one line and the model stays small");
  assert.equal(noteLine({ workingNote: "  a  note\nwith   breaks ", summary: "s" }), "a note with breaks", "the note, one line");
  assert.equal(noteLine({ workingNote: "", summary: "s" }), ""); assert.equal(noteLine({}), ""); assert.equal(noteLine(null), "");
  assert.equal(noteLine({ workingNote: "x".repeat(300) }).length, 200, "the same cap");
});

test("executed: needs you follows the FEED's column, not the tab's chip: a judge-filed block flags the row whether the session is idle or active", () => {
  // the common case the tab's rule misses: the agent asked a question and went idle; the feed files its card under needs-you
  const idle = snapshotRow("web", { name: "web", status: { state: "idle" } }, { needsInput: true, tree: [{ text: "Pick a database", current: true }] });
  assert.deepEqual([idle.pip, idle.needsYou, idle.state, idle.chip], ["", true, "", { state: "needsInput", text: "Blocked", peer: null }], "idle + feed needs-you: flagged; the chip is the feed's column word and the row's only word for it; the pip stays the tab's (none)");
  const ready = snapshotRow("web", { name: "web", status: { state: "ready" } }, { needsInput: true });
  assert.deepEqual([ready.pip, ready.needsYou, ready.state, ready.chip && ready.chip.text], ["", true, "", "Blocked"]);
  // blocked while active: the feed's verdict stands until the judges rule again, even with a turn open (a rejudge in flight)
  const active = snapshotRow("web", { name: "web", status: { state: "working" } }, { needsInput: true });
  assert.deepEqual([active.pip, active.needsYou, active.state], ["working", true, "working"], "active + feed needs-you: flagged; the tab's own state word and pip stay");
  // no feed verdict for this session: the tab's rule alone
  assert.equal(snapshotRow("web", { name: "web", status: { state: "idle" } }, { needsInput: false }).needsYou, false);
  assert.equal(snapshotRow("web", { name: "web", status: { state: "idle" } }, { needsInput: false }).state, "");
  assert.equal(snapshotRow("web", { name: "web", status: { state: "idle" } }, { needsInput: null }).needsYou, false, "null = no feed build yet: not a verdict");
  assert.equal(snapshotRow("web", { name: "web", status: { state: "needsInput" } }, { needsInput: null }).needsYou, true, "the tab's live prompt still counts (the feed trails the chip by a push)");
  assert.equal(snapshotRow("web", { name: "web", status: { state: "blocked", apiTooLong: true } }, { needsInput: false }).needsYou, true, "the tab's on-you API error too");
  assert.equal(snapshotRow("web", { name: "web", status: { state: "closed" } }, { needsInput: true }).state, "closed", "a closed session keeps its own word");
  assert.equal(rowWords(idle).label, "web; Blocked; Pick a database", "the spoken label says the chip's words, once (T322b: what is heard is what is shown)");
});

test("executed: the on-you chip's words: Blocked for the feed's column and a live prompt; API error only for the tab's own on-you API error, never for a flagless auto-retried one", () => {
  const chipOf = (status: any, lg: any = { needsInput: false }) => snapshotRow("api", { name: "api", status, events: [] }, lg).chip;
  assert.deepEqual(chipOf({ state: "needsInput" }), { state: "needsInput", text: "Blocked", peer: null }, "a live prompt");
  assert.deepEqual(chipOf({ state: "blocked", apiTooLong: true }), { state: "blocked", text: "API error", peer: null }, "an API error only you can clear: the flags say so");
  assert.deepEqual(chipOf({ state: "blocked", apiSpendLimit: true }, { needsInput: true }), { state: "blocked", text: "API error", peer: null });
  assert.deepEqual(chipOf({ state: "blocked" }, { needsInput: true }), { state: "needsInput", text: "Blocked", peer: null }, "a flagless API error is the kernel's transient, auto-retried one: with a feed-filed block the row reads Blocked like any other on-you row");
  assert.deepEqual(chipOf({ state: "retrying" }, { needsInput: true }), { state: "needsInput", text: "Blocked", peer: null }, "…the same as its retrying twin");
  assert.equal(chipOf({ state: "blocked" }), null, "a flagless API error with no feed verdict is not on you: the amber pip alone");
});

test("executed: the spoken label says the chip's words whenever the row wears one, once, then the tab's own phrase", () => {
  const prompt = snapshotRow("api", { name: "api", status: { state: "needsInput" } }, { needsInput: true });
  assert.equal(rowWords(prompt).label, "api; Blocked; needs you: waiting on your answer");
  const apiErr = snapshotRow("api", { name: "api", status: { state: "blocked", apiTooLong: true } }, null);
  assert.equal(rowWords(apiErr).label, "api; API error; needs you: stopped on an API error");
  const rejudge = snapshotRow("web", { name: "web", status: { state: "working" } }, { needsInput: true, tree: [{ text: "Pick a database", current: true }] });
  assert.equal(rowWords(rejudge).label, "web; Blocked; working; Pick a database");
  assert.equal(rowWords(snapshotRow("web", { name: "web", status: { state: "closed" } }, { needsInput: true })).label, "web; Blocked; closed");
  // a todo alone raises needs-you and the count but no chip (this fork's user todos; the chip is the feed's or the tab's
  // word, T322b): the label counts the things right after the name
  assert.equal(rowWords(snapshotRow("x", { name: "x", status: { state: "ready" }, userTodos: [{}] }, null)).label, "x; 1 thing it needs from you");
  assert.equal(rowWords(snapshotRow("web", { name: "web", status: { state: "working" } }, { needsInput: false })).label, "web; working");
  assert.equal(rowWords(snapshotRow("web", { name: "web", status: { state: "awaitingBg" } }, { needsInput: null })).label, "web; Awaiting agents", "an awaiting row's phrase IS the chip's words: said once");
  assert.equal(rowWords(snapshotRow("new1", null, { needsInput: true })).label, "(unnamed); Blocked; opening", "a loading row can wear the chip only through a ledger the client has no session for; spoken all the same");
});

test("executed: the pip and the state word follow tab-state.ts: on-you red, transient amber, closed struck, idle none", () => {
  assert.deepEqual(rowState({ state: "blocked", apiTooLong: true }), { pip: "blocked", state: "needs you: stopped on an API error", needsYou: true, waiting: false, closed: false });
  assert.equal(rowState({ state: "blocked" }).pip, "retrying", "a transient API error is the tab's amber, not red");
  assert.deepEqual(rowState({ state: "retrying" }), { pip: "retrying", state: "API error, retrying on its own", needsYou: false, waiting: false, closed: false });
  assert.equal(rowState({ state: "awaiting" }).pip, "awaiting", "the legacy name an older remote kernel sends");
  assert.deepEqual(rowState({ state: "compacting" }), { pip: "compacting", state: "compacting", needsYou: false, waiting: false, closed: false });
  assert.equal(rowState({ state: "clearing" }).state, "clearing");
  assert.deepEqual(rowState({ state: "closed" }), { pip: "", state: "closed", needsYou: false, waiting: false, closed: true });
  for (const st of ["ready", "idle"]) assert.deepEqual(rowState({ state: st }), { pip: "", state: "", needsYou: false, waiting: false, closed: false }, st + ": no pip");
  assert.equal(rowState({ state: "opening" }).pip, "unknown");
  assert.equal(rowState({ state: "interrupting" }).state, "interrupting");
  assert.equal(rowState(null).pip, "unknown");
  // a user todo is on you whatever the state (this fork's user todos)
  const r = snapshotRow("web", { name: "web", status: { state: "ready" }, userTodos: [{ id: "t1" }] }, null);
  assert.deepEqual([r.pip, r.needsYou, r.todos], ["", true, 1]);
});

test("executed: a placeholder tab (no session frame yet) is a loading row with the meta it has; a closed session is struck", () => {
  const r = snapshotRow("new1", null, null);
  assert.deepEqual([r.name, r.pip, r.loading, r.lastT, r.now, r.lastMsg], ["(unnamed)", "unknown", true, null, "", ""]);
  const meta = snapshotRow("new1", null, null, false, { name: "new1", color: { bg: "#123456", fg: "#ffffff" } });   // the strip's tabMeta: name + color, no frame yet (fifth: this fork's `hidden` is fourth)
  assert.deepEqual([meta.name, meta.pip, meta.loading, meta.color], ["new1", "unknown", true, { bg: "#123456", fg: "#ffffff" }], "a loading row wears the tab's name and color");
  assert.equal(rowWords(meta).label, "new1; opening");
  const landed = snapshotRow("new1", { name: "new1", status: { state: "ready" } }, null, false, { name: "old-name" });
  assert.deepEqual([landed.name, landed.loading], ["new1", false], "the frame outranks the meta once it lands");
  assert.equal(snapshotRow("old", { name: "old", status: { state: "closed" } }, null).closed, true);
  assert.equal(rowWords(snapshotRow("new1", null, null)).label, "(unnamed); opening");
  assert.equal(snapshotRow("x", { name: "x", color: { bg: "#123456", fg: "" } }, null).color, null, "half a color is no color");
});

test("executed: lastActivity walks the tail from the end and skips undated atoms; the sinceEpoch fallback converts the wire's milliseconds", () => {
  assert.equal(lastActivity({ events: [{ kind: "assistant", ts: iso(T0 - 10) }, { kind: "tool" }], status: { state: "working", sinceEpoch: ms(T0 - 99) } }), T0 - 10);
  assert.equal(lastActivity({ events: [{ kind: "postal-service", t: T0 - 5.7 }] }), T0 - 6, "a postal card carries its own epoch");
  assert.equal(lastActivity({ events: [{ kind: "tool", ts: "not a date" }], status: { state: "ready", sinceEpoch: ms(T0 - 1) } }), T0 - 1);
  assert.equal(lastActivity({ events: [], status: { state: "ready", sinceEpoch: null } }), null);
  // a just-created session (events: [], sinceEpoch: Date.now() in ms) 90 s ago must read as 90 s, not as a time far in the future
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
  assert.equal(plainText("x".repeat(500), 400).length, 400, "capped");
  assert.equal(lastMessage({ events: [{ kind: "assistant", text: "plain `text` field" }] }), "plain text field", "the text field when there is no md");
});

test("executed: plainText drops inline HTML and underscore emphasis too: the transcript renders them as structure, a tooltip would show them as typed", () => {
  assert.equal(plainText("<b>x</b>", 400), "x");
  assert.equal(plainText("_x_", 400), "x");
  assert.equal(plainText("<details><summary>Test output</summary>\n12 passed\n</details>", 400), "Test output 12 passed", "the common reply shape: tags go, words stay");
  assert.equal(plainText("<b>bold</b> and <a href='x'>l</a> &amp; <br>", 400), "bold and l &", "tags of every kind, an entity decoded once the tags are gone");
  assert.equal(plainText("__Done__ _emph_ and snake_case __strong__", 400), "Done emph and snake_case strong", "emphasis at word edges goes; snake_case keeps its underscores, as in the file viewer");
  assert.equal(plainText("a < b and c > d", 400), "a < b and c > d", "a bare comparison is not a tag");
  assert.equal(plainText("say &lt;b&gt; &quot;hi&quot; it&#39;s x&nbsp;y", 400), 'say <b> "hi" it\'s x y', "escaped text stays text: decoded after the tag pass, so a typed <b> is not stripped");
  assert.equal(plainText("before <!-- a note\nfor no one --> after", 400), "before after", "an HTML comment goes whole, across lines");
  assert.equal(plainText("line<br>next<br/>last", 400), "line next last", "a break is a space, not a joined word");
});

test("executed: a push that changes nothing a row shows returns the SAME model object: the no-rebuild contract", () => {
  const a = snapshotModel(sec, look(sessions), look(ledgers), null);
  // a fresh frame: new session objects, new arrays, the same content (the client rebuilds them per push)
  const clone = new Map<string, SnapSessionLike>([...sessions].map(([k, v]) => [k, JSON.parse(JSON.stringify(v))]));
  const b = snapshotModel(sec, look(clone), look(ledgers), a);
  assert.equal(b, a, "same object: the renderer skips the rebuild (only the ago texts tick)");
  assert.equal(snapshotModel({ ...sec, ids: [...sec.ids] }, look(clone), look(ledgers), a), a, "a fresh section object, the same content: the same model");
  // a status the row does not show (sinceEpoch when the tail has events) changes nothing
  const noisy = new Map(clone); noisy.set("web", { ...clone.get("web")!, status: { state: "working", sinceEpoch: T0 - 1 } });
  assert.equal(snapshotModel(sec, look(noisy), look(ledgers), a), a, "a flapping input the row never reads cannot move it");
  assert.ok(sameModel(a, a) && !sameModel(null, a));
});

test("executed: new information yields a NEW model: a state change, a new event, a note, a todo, a member, a rename, an emoji, a color, the feed's verdict", () => {
  const a = snapshotModel(sec, look(sessions), look(ledgers), null);
  const with_ = (id: string, patch: Partial<SnapSessionLike>) => { const m = new Map(sessions); m.set(id, { ...sessions.get(id)!, ...patch }); return m; };
  assert.notEqual(snapshotModel(sec, look(with_("web", { status: { state: "ready" } })), look(ledgers), a), a, "state");
  assert.notEqual(snapshotModel(sec, look(with_("web", { events: [...sessions.get("web")!.events!, { kind: "assistant", md: "Done.", ts: iso(T0) }] })), look(ledgers), a), a, "a new event (time and last message)");
  assert.notEqual(snapshotModel(sec, look(with_("web", { userTodos: [{ id: "t9" }] })), look(ledgers), a), a, "a todo (this fork's user todos)");
  assert.notEqual(snapshotModel(sec, look(with_("web", { name: "web2" })), look(ledgers), a), a, "a rename");
  assert.notEqual(snapshotModel(sec, look(with_("web", { emoji: "" })), look(ledgers), a), a, "the emoji");
  const l2 = new Map(ledgers); l2.set("web", { ...ledgers.get("web")!, workingNote: "reviewing the tests" });
  assert.notEqual(snapshotModel(sec, look(sessions), look(l2), a), a, "the working note");
  const l3 = new Map(ledgers); l3.set("web", { ...ledgers.get("web")!, needsInput: true });
  assert.notEqual(snapshotModel(sec, look(sessions), look(l3), a), a, "the feed's needs-you verdict");
  const l4 = new Map(ledgers); l4.set("api", { ...ledgers.get("api")!, needsInput: false });
  assert.equal(snapshotModel(sec, look(sessions), look(l4), a), a, "not when the tab's own live prompt already flags the row: nothing shown changed");
  assert.notEqual(snapshotModel({ ...sec, ids: ["web", "api"] }, look(sessions), look(ledgers), a), a, "a member gone");
  assert.notEqual(snapshotModel({ ...sec, name: "infra2" }, look(sessions), look(ledgers), a), a, "the section itself");
  assert.notEqual(snapshotModel(sec, look(with_("web", { color: { bg: "#000000", fg: "#ffffff" } })), look(ledgers), a), a, "the identity color");
});

test("executed: the words: the heading's count and label, the row's spoken label and hover title", () => {
  assert.deepEqual(snapshotHeading("infra", 3), { count: "3 sessions", label: "Overview of infra: 3 sessions; click one to open it" });
  assert.equal(snapshotHeading("qa", 1).count, "1 session");
  const m = snapshotModel(sec, look(sessions), look(ledgers), null);
  assert.equal(rowWords(m.rows[0]).label, "web; working; Add the notes list page; its note: editing the list page template", "the task first, the note last, named as the session's own");
  assert.equal(rowWords(m.rows[0]).title, "Last message: Adding the list page now: the route and the template.\nClick to open this session.");
  assert.equal(rowWords(m.rows[1]).label, "api; Blocked; needs you: waiting on your answer; 2 things it needs from you; Pick a database", "the chip's word first (T322b), the tab's own phrase, the user todos counted after the state (this fork), then the task");
  assert.equal(rowWords(m.rows[2]).title, "No messages yet.\nClick to open this session.");
});

// ── this fork's pins over render.ts and the guide: the parts upstream's pane test cannot see ─────────────────────
const ui = (...p: string[]) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", ...p), "utf8");
const RENDER = ui("webview", "render.ts");
const GUIDE = fs.readFileSync(path.resolve(process.cwd(), "..", "docs", "guide.md"), "utf8");
const SHOW_SIG = "function showActive(keep?: { uuid: string; y: number } | null) {";
const SHOW_AT = RENDER.indexOf(SHOW_SIG);
assert.ok(SHOW_AT >= 0, "render.ts: showActive's signature moved; re-anchor SNAP");
const SNAP = RENDER.slice(RENDER.indexOf("let snapView: string | null = null;"), SHOW_AT);

test("pinned: the row wears this fork's strip vocabulary (the tab's emoji node, the user-todo flag, the identity color on the name), and the plan's hides ride the section into the model with the strip's meta", () => {
  assert.match(SNAP, /const em = tabEmojiNode\(r\.emoji\); if \(em\) btn\.appendChild\(em\);/, "the tab's emoji node, the same helper the strip uses");
  assert.match(SNAP, /const g = el\("span", "tab-usertodo"\); g\.textContent = "⚑";/, "the tab's flag for a user todo");
  assert.match(SNAP, /if \(r\.color\) name\.style\.color = r\.color\.bg;/);
  // the model call: the section with the plan's hides (tab-hide.test), the client's sessions and ledgers, the previous model, and
  // the strip's meta for a placeholder row (upstream's #1301 review delta, the fifth argument)
  assert.match(SNAP, /const next = snapshotModel\(\{ \.\.\.head\.head, hides: head\.hides \}, \(id\) => sessions\.get\(id\) \?\? null, \(id\) => ledgers\.get\(id\) \?\? null, snapModel, \(id\) => tabMeta\.get\(id\) \?\? null\);\s*\n\s*if \(next === snapModel && host\.childElementCount\) \{/,
    "the same-object check gates the rebuild (the plan's hides ride the section: tab-hide.test)");
});

test("the guide describes the view and the fold rule in this fork's words: the way back, the note line, the chip's triggers and the todo's flag, the dot rule", () => {
  assert.match(GUIDE, /\*\*A section at a glance\.\*\* Clicking a header also shows the section in the transcript's place/);
  assert.match(GUIDE, /The section of the\s+tab you are reading folds like\s+any other; its header then stands in for the tab/);
  assert.doesNotMatch(GUIDE, /never\s+folds \(its header says so/, "the old rule is gone from the guide");
  // the now line's real chain, the note as a second line, the chip as the feed's word, the hover without markup
  assert.match(GUIDE, /What it is doing now comes from its current task, else from the headline of\s+its work so far, else from the last task it had;/);
  assert.match(GUIDE, /a session that has published a note of what it is\s+working on shows the note as a quieter second line\./);
  // the chip's triggers (tab-snapshot.ts snapshotRow, T322b's shared chip): the feed's column first; an open user todo
  // raises the flag and the count at once, and reaches the chip only through the feed, once the session is idle on it
  // (the pull-in ruling of 2026-09-15, item 15 b; the code default: a todo alone is chip null, todos 1)
  assert.match(GUIDE, /\*\*Blocked\*\* when the feed shows one of the\s+session's cards under Blocked/,
    "the chip's first trigger is the feed's column (snapshotRow: feedBlock)");
  assert.match(GUIDE, /the flag and its count show as soon as it\s+flags one\./,
    "an open user todo raises the flag and its count at once (this fork's user todos); the chip waits on the feed");
  assert.match(GUIDE, /the \*\*Blocked\*\* chip\s+follows the feed, at most a moment behind it\./);
  assert.match(GUIDE, /Hover a row for its last message, shown without\s+its formatting;/);
  // the dot is the tab's own state, never the feed's verdict (rowState: the pip; the idle feed-filed row has none)
  assert.match(GUIDE, /a dot for its state \(yellow working, red stopped on a\s+prompt or an API error only you can clear, amber retrying an API error on its own, teal compacting,\s+green waiting on background work, none while it is idle\)/,
    "every pip color the sheet paints (.snap-pip.*), by the tab's own state rule (tab-state.ts), and none for idle");
  assert.match(GUIDE, /A session that asked a question and went quiet shows the chip\s+with no dot: the dot follows the session's own state, the chip follows the feed\./);
  assert.doesNotMatch(GUIDE, /red needs\s+you/, "the old dot rule, a red dot for every needs-you, is gone");
  // the way back: all three exits (render.ts setActive, the Escape listener, show-transcript)
  assert.match(GUIDE, /The transcript comes back when you pick a session, press Escape, or click that header again while\s+its section is open and holds the tab you are reading\./);
  assert.doesNotMatch(GUIDE, /its own note of what\s+it is working on, else its current task/, "the old two-rung chain, note first, is gone");
});

test("executed: the row's chip is the SHARED status chip's words (T322b): Blocked for the feed's column and a live prompt, API error for an on-you API error, 'Awaiting <word>' from the kind, count and rows, the one peer's name; none for working, ready and retrying; a change in it is a model change", () => {
  const m = snapshotModel(sec, look(sessions), look(ledgers), null);
  const [web, api, tests] = m.rows;
  assert.equal(web.chip, null, "working: the pip alone");
  assert.deepEqual(api.chip, { state: "needsInput", text: "Blocked", peer: null }, "a live prompt: the bar's Blocked");
  assert.deepEqual(tests.chip, { state: "awaitingBg", text: "Awaiting agents", peer: null }, "no kind, no count: the historic default word");
  const chipOf = (status: any, lg: any = { needsInput: false }) => snapshotRow("tests", { name: "tests", status, events: [] }, lg).chip;
  assert.deepEqual(chipOf({ state: "awaitingBg", awaitingKind: "agents", awaitingCount: 3 }), { state: "awaitingBg", text: "Awaiting 3 agents", peer: null });
  assert.deepEqual(chipOf({ state: "awaitingBg", awaitingKind: "job", awaitingCount: 1 }), { state: "awaitingBg", text: "Awaiting watch", peer: null }, "the plain words: a job is a watch");
  assert.deepEqual(chipOf({ state: "awaitingBg", awaitingKind: "mixed", awaitingCount: 4 }), { state: "awaitingBg", text: "Awaiting 4", peer: null }, "mixed kinds: the number alone");
  assert.deepEqual(chipOf({ state: "awaitingBg", awaitingItems: [{ kind: "agents", id: "a1" }, { kind: "commands", id: "c1" }] }), { state: "awaitingBg", text: "Awaiting 2", peer: null }, "rows of two kinds: the number alone");
  assert.deepEqual(chipOf({ state: "awaitingBg", awaitingItems: [{ kind: "watches", id: "w1" }, { kind: "watches", id: "w2" }] }), { state: "awaitingBg", text: "Awaiting 2 watches", peer: null });
  const peer = { name: "api", host: "TESTHOST", color: { bg: "#d53a3a", fg: "#ffffff" } };
  assert.deepEqual(chipOf({ state: "awaitingBg", awaitingKind: "peer", awaitingCount: 1, awaitingPeers: [peer] }), { state: "awaitingBg", text: "Awaiting TESTHOST:api", peer }, "one peer: the chip names it");
  assert.deepEqual(chipOf({ state: "awaitingBg", awaitingKind: "peer", awaitingCount: 2, awaitingPeers: [peer, { name: "web" }] }), { state: "awaitingBg", text: "Awaiting 2 peers", peer: null }, "several peers: the count");
  assert.deepEqual(chipOf({ state: "blocked", apiTooLong: true }), { state: "blocked", text: "API error", peer: null }, "the tab's on-you API error: the bar's word for it");
  assert.deepEqual(chipOf({ state: "needsInput" }), { state: "needsInput", text: "Blocked", peer: null }, "a live prompt");
  assert.deepEqual(chipOf({ state: "idle" }, { needsInput: true }), { state: "needsInput", text: "Blocked", peer: null }, "a judge-filed block on an idle session: the feed's column word");
  assert.deepEqual(chipOf({ state: "working" }, { needsInput: true }), { state: "needsInput", text: "Blocked", peer: null }, "…and on an active one");
  assert.equal(chipOf({ state: "ready" }), null); assert.equal(chipOf({ state: "idle" }), null); assert.equal(chipOf({ state: "retrying" }), null, "retrying rides the pip alone");
  assert.equal(chipOf({ state: "closed" }), null, "closed: the struck name says it");
  assert.equal(snapshotRow("tests", null, null, false, { name: "tests" }).chip, null, "a placeholder tab: no chip (this fork's snapshotRow takes hidden fourth, the strip's meta fifth)");
  // the spoken label says the chip's words, once
  assert.equal(rowWords(snapshotRow("tests", { name: "tests", status: { state: "awaitingBg", awaitingKind: "job", awaitingCount: 1 }, events: [] }, null)).label, "tests; Awaiting watch");
  // a change in the chip alone is a model change; nothing changed is the same object
  const s2 = new Map(sessions); s2.set("tests", { ...sessions.get("tests")!, status: { state: "awaitingBg", sinceEpoch: ms(T0 - 900), awaitingKind: "agents", awaitingCount: 3 } });
  assert.notEqual(snapshotModel(sec, look(s2), look(ledgers), m), m, "the count came: a new model");
  // …and a change the chip alone carries (the state phrase unchanged): the one peer's identity colour
  const peerA = { name: "api", color: { bg: "#d53a3a", fg: "#ffffff" } }, peerB = { name: "api", color: { bg: "#3a7bd5", fg: "#ffffff" } };
  const s3 = new Map(sessions); s3.set("tests", { ...sessions.get("tests")!, status: { state: "awaitingBg", sinceEpoch: ms(T0 - 900), awaitingKind: "peer", awaitingCount: 1, awaitingPeers: [peerA] } });
  const m3 = snapshotModel(sec, look(s3), look(ledgers), null);
  const s4 = new Map(s3); s4.set("tests", { ...s3.get("tests")!, status: { ...s3.get("tests")!.status, awaitingPeers: [peerB] } });
  assert.equal(snapshotModel(sec, look(s3), look(ledgers), m3), m3, "the same peer: the same object");
  assert.notEqual(snapshotModel(sec, look(s4), look(ledgers), m3), m3, "the peer's colour changed and nothing else the row says: a new model (sameChip)");
  assert.equal(snapshotModel(sec, look(sessions), look(ledgers), m), m, "nothing changed: the same object");
});
