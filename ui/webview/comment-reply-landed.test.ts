// T237 (the user 2026-09-03, twice, ~4:25 PM PT): the marked passage must not turn YELLOW until the reply
// has LANDED. Two sightings, one design: the mark wears a faded AWAIT-GREEN `.busy` wash while the thread
// is mid-reply and settles into the yellow `.unread` the moment the reply lands — and both times the green
// failed to apply. Convicted at the source:
//   * `.busy` keyed on a CLIENT gesture latch (cmtAwaitBase) that any session's comments frame could prune
//     (the prune ran against ONE session's thread list) and that cleared on a reply-arrived heuristic
//     (agentCount rising + !threadBusy(state)) — the first agent record of a multi-record turn with the
//     backend's state read as ""/waiting dropped the wash while the thread was still responding; the
//     msgs-derived replyOwed() fallback flips false at that same first record.
//   * `unread` keyed in the kernel on ANY agent record newer than the watermark — an intermediate text
//     block or tool call of a turn in progress painted yellow before the turn ended.
// Fix: the kernel is the one truth (tests/test_comment_threads.py pins the rule): `replyOwed` (green) and
// `unread` = a FINISHED reply newer than the watermark (yellow), both from the thread's transcript with the
// event model's own turn-end. The client keys `.busy` on th.replyOwed and keeps the gesture latch only for
// the pre-round-trip instant (from the send click until a frame carries the send); no timers anywhere.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import type { CommentThread } from "./comments";

const RENDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");
const COMMENTS = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "comments.ts"), "utf8");
const KERNEL = fs.readFileSync(path.resolve(process.cwd(), "..", "kernel", "kernel.py"), "utf8");
const CSS = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "styles.css"), "utf8");

test("the kernel ships replyOwed beside unread, both from the thread's own turn-end", () => {
  assert.match(KERNEL, /def _thread_turn_read\(tsid, reg, state\):/);
  assert.match(KERNEL, /def _turn_landed\(turn\):/);
  assert.match(KERNEL, /def _turn_is_meta\(turn\):/, "compaction boundaries and command-only turns are not landings");
  assert.match(KERNEL, /if landed:\s*\n\s*return False, interrupted/, "the end_turn / interrupt record IS the landing");
  assert.match(KERNEL, /print\("\[comments\] thread %s: transcript parse failed/, "a parse failure is shouted, never swallowed");
  assert.match(KERNEL, /def _agent_landed_after\(events, msgs, seen\):/);
  assert.match(KERNEL, /turn_open, interrupted = _thread_turn_read\(tsid, reg, state\) if status == "open" else \(False, False\)/);
  assert.match(KERNEL, /unread = \(not turn_open\) and _agent_landed_after\(events, msgs, seen\)/);
  assert.match(KERNEL, /reply_owed = status == "open" and \(turn_open or not msgs or \(msgs\[-1\]\["who"\] == "you" and not interrupted\)\)/);
  assert.match(KERNEL, /"unread": unread, "replyOwed": reply_owed,/);
  assert.match(KERNEL, /yellow — means "a FINISHED reply you have not seen"/, "the rule is stated in the docstring");
});

test("the client keys the green wash on the kernel's replyOwed; the gesture latch covers only the pre-round-trip instant", () => {
  const inflight = RENDER.split("const commentInFlight = (th: CommentThread): boolean => {")[1].split("\n};")[0];
  assert.match(inflight, /if \(cmtAwaitBase\.has\(th\.tid\)\) return true;/);
  assert.match(inflight, /const owed = typeof th\.replyOwed === "boolean" \? th\.replyOwed : replyOwed\(th\);/,
    "kernel truth when present; the msgs-derived fallback only for an older kernel");
  assert.match(inflight, /return owed && !cmtInterrupted\.has\(th\.tid\);/);
  assert.doesNotMatch(inflight, /agentCount|threadBusy/, "no reply-arrived heuristic in the wash");
  // the latch clears when a frame carries the SEND — a message newer than the click's newest, or more
  // messages than then (the count alone misses a thread at the projection's 40-message cap) — and only
  // an OLDER kernel (no replyOwed bit) keeps the T102 agent-count-with-settled-state clear
  assert.match(RENDER, /const sendLanded = t\.msgs\.length > base\.n \|\| newestT > base\.t;/);
  assert.match(RENDER, /const legacyReplyArrived = agentCount\(t\) > base\.agents && !threadBusy\(t\.state\);/);
  assert.match(RENDER, /const clear = \(typeof t\.replyOwed === "boolean" \? sendLanded : legacyReplyArrived\) \|\| t\.status !== "open" \|\| !!t\.error;/);
  assert.match(RENDER, /cmtAwaitBase\.set\(cur\.th\.tid, cmtLatchOf\(cur\.th\)\);/, "a follow-up latches on its thread's counts at the click");
  assert.match(RENDER, /cmtAwaitBase\.set\(synth\.tid, \{ n: 0, t: 0, agents: 0 \}\);/, "the create gesture latches its synthetic thread");
  assert.match(RENDER, /unread: false, replyOwed: true, promotedName: "", msgs: \[\], name: nm \|\| "comment"/,
    "the synthetic thread owes its reply from the click");
  assert.match(COMMENTS, /replyOwed\?: boolean;/);
});

test("latches are pruned only against EVERY session's known threads — never one frame's list", () => {
  assert.match(RENDER, /const knownTids = new Set<string>\(\);\s*\n\s*commentThreads\.forEach\(\(list\) => list\.forEach\(\(t\) => knownTids\.add\(t\.tid\)\)\);/);
  assert.match(RENDER, /if \(!k\.startsWith\("pending:"\) && !knownTids\.has\(k\)\) cmtAwaitBase\.delete\(k\);/);
  assert.doesNotMatch(RENDER, /!threads\.some\(\(t\) => t\.tid === k\)\) cmtAwaitBase\.delete\(k\)/,
    "the one-frame prune that dropped other sessions' latches is gone");
  // the "pending:" → real tid carry on adoption stays
  assert.match(RENDER, /if \(k\.startsWith\("pending:"\)\) \{ cmtAwaitBase\.set\(tid, cmtAwaitBase\.get\(k\)!\); cmtAwaitBase\.delete\(k\); \}/);
});

test("a reply landing while its popover is open advances the watermark BEFORE the marks paint", () => {
  const handler = RENDER.split('else if (m.type === "comments" && m.id) {')[1].split("\n  }\n")[0];
  const seen = handler.indexOf('vscodeApi?.postMessage({ type: "commentSeen", id: sid, tid: th.tid });');
  const paint = handler.indexOf("applyCommentMarks(sid);");
  assert.ok(seen > 0 && paint > 0 && seen < paint, "seen-stamp first, paint after — the mark never wears yellow for a reply read as it lands");
  assert.match(handler, /if \(openCommentKey && openCommentKey\.sid === sid\) renderCommentPopover\(\);/);
});

test("no timer anywhere in the colour path", () => {
  const inflight = RENDER.split("const commentInFlight = (th: CommentThread): boolean => {")[1].split("\n};")[0];
  const style = RENDER.split("function styleCommentMark(")[1].split("\n}")[0];
  for (const src of [inflight, style]) assert.doesNotMatch(src, /setTimeout|Date\.now|setInterval/);
});

// ── executed: the mark's classes for the kernel's frames (no jsdom dependency here — a minimal element shim) ──
function markFor(th: CommentThread, latched = false): Set<string> {
  // the latch map's VALUE shape is irrelevant to the wash (has() alone is read) — a zeroed latch stands in
  const inflightSrc = "const commentInFlight = (th) => {" + RENDER.split("const commentInFlight = (th: CommentThread): boolean => {")[1].split("\n};")[0] + "\n};";
  const styleSrc = "function styleCommentMark(m, th) {" + RENDER.split("function styleCommentMark(m: HTMLElement, th: CommentThread): void {")[1].split("\n}")[0] + "\n}";
  const prelude = `
    const cmtAwaitBase = new Map(${latched ? '[["t1", { n: 0, t: 0, agents: 0 }]]' : ""});
    const cmtInterrupted = new Set();
    const threadStuck = (st) => st === "permission" || st === "picker";
    const replyOwed = (th) => { const l = th.msgs.length ? th.msgs[th.msgs.length - 1] : null; return !!l && l.who === "you"; };
    const commentInFlight_ = null;`;
  const classes = new Set<string>();
  const m = { classList: { toggle(c: string, on: boolean) { if (on) classes.add(c); else classes.delete(c); } }, title: "" };
  new Function("m", "th", prelude + "\n" + inflightSrc + "\n" + styleSrc + "\nstyleCommentMark(m, th);")(m, th);
  return classes;
}
const base = (over: Partial<CommentThread>): CommentThread => ({
  tid: "t1", anchorUuid: "a1", exact: "the passage", status: "open", createdT: 0,
  state: "", unread: false, promotedName: "", msgs: [], ...over,
});

test("(v)/(vii) while the popover would show its loader — no exchange yet — the mark is busy, never unread", () => {
  const c = markFor(base({ replyOwed: true, unread: false, msgs: [], events: [] } as Partial<CommentThread>));
  assert.ok(c.has("busy") && !c.has("unread"));
});

test("(vi) a partial reply (the kernel still owes it, whatever the state reads) keeps the wash", () => {
  for (const state of ["working", "", "waiting"]) {
    const c = markFor(base({ state, replyOwed: true, unread: false,
      msgs: [{ who: "you", text: "why jitter?", t: 1 }, { who: "agent", text: "Let me check.", t: 2 }] }));
    assert.ok(c.has("busy") && !c.has("unread"), "state=" + JSON.stringify(state));
  }
});

test("(viii) the finished reply: yellow in the same frame the kernel says it landed, green gone", () => {
  const c = markFor(base({ replyOwed: false, unread: true,
    msgs: [{ who: "you", text: "why jitter?", t: 1 }, { who: "agent", text: "Jitter prevents thundering herds.", t: 2 }] }));
  assert.ok(c.has("unread") && !c.has("busy"));
});

test("the pre-round-trip latch alone keeps a fresh mark busy before any frame carries the send", () => {
  const c = markFor(base({ msgs: [], unread: false }), true);
  assert.ok(c.has("busy") && !c.has("unread"));
});

test("an older kernel (no replyOwed bit) falls back to the msgs-derived read", () => {
  const owed = markFor(base({ msgs: [{ who: "you", text: "why?", t: 1 }] }));
  assert.ok(owed.has("busy"));
  const answered = markFor(base({ msgs: [{ who: "you", text: "why?", t: 1 }, { who: "agent", text: "because", t: 2 }] }));
  assert.ok(!answered.has("busy"));
});

test("the CSS intent stands: green wash while busy, yellow tiers for base/unread", () => {
  assert.match(CSS, /mark\.cmt-hl\.busy \{\s*\n\s*background-color: color-mix\(in srgb, var\(--st-awaitbg-bg\) 24%, transparent\);/);
  assert.match(CSS, /mark\.cmt-hl\.unread \{ background: color-mix\(in srgb, var\(--cmt-hl\) 45%, transparent\); \}/);
});
