// Comment threads (the user 2026-08-13): the pure half (comments.ts) is driven behaviorally; the
// render.ts / kernel / CSS wiring is pinned at the source (no jsdom harness for the renderers — the
// repo convention). Synthetic text only.
import { test } from "node:test";
import assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { threadsByAnchor, threadBusy, threadStuck, replyOwed, agentCount, findExact, findAnchorRange, sliceRanges, prunePending, markSkipsParent,
         newCommentCreate, commentCreateFrame, heldCreateFor, createDraftKey, createNameKey, passageLabel, refusedCreateToast, handedBackToast,
         FRAME_EXACT_CUT, frameExact, CREATE_ID_ECHO_CAP, echoAnswer, hostEchoMode, carryMainDraft, capsAnnounceEcho, answerEchoEvidence,
         savedAfterAllToast,
         type CommentThread, type CommentCreate } from "./comments";
import { compactDisplay } from "./compact";
import { hostOf } from "./host-prefix";

const th = (over: Partial<CommentThread>): CommentThread => ({
  tid: "t1", anchorUuid: "a1", exact: "the passage", status: "open", createdT: 0,
  state: "", unread: false, promotedName: "", msgs: [], ...over,
});

// ── findExact: whitespace-tolerant re-anchoring ────────────────────────────────────────────────

test("findExact finds a verbatim passage", () => {
  const r = findExact("Use exponential backoff with jitter.", "exponential backoff");
  assert.ok(r);
  assert.equal("Use exponential backoff with jitter.".slice(r!.start, r!.end), "exponential backoff");
});

test("findExact tolerates collapsed and rewrapped whitespace", () => {
  // the selection was made on one rendering; the re-render wraps the line elsewhere
  const hay = "Cap the delay\n  at two   minutes.";
  const r = findExact(hay, "delay at two minutes");
  assert.ok(r);
  assert.equal(hay.slice(r!.start, r!.end).replace(/\s+/g, " "), "delay at two minutes");
});

test("findExact returns null when the text drifted away", () => {
  assert.equal(findExact("something else entirely", "the old passage"), null);
});

test("findExact never matches an empty selection", () => {
  assert.equal(findExact("anything", "   "), null);
});

// ── findAnchorRange: longest-prefix fallback for cross-message selections ──────────────────────

test("findAnchorRange returns the full match, not partial, when the text is present", () => {
  const r = findAnchorRange("Use exponential backoff with jitter.", "exponential backoff");
  assert.ok(r && !r.partial);
});

test("findAnchorRange falls back to the longest prefix that lives in this turn", () => {
  // the selection continued into the NEXT message; only its head is in the anchor turn
  const hay = "Cap the delay at two minutes for every retry loop.";
  const r = findAnchorRange(hay, "delay at two minutes for every retry loop. And the jitter stays at ten percent.");
  assert.ok(r);
  assert.ok(r!.partial);
  assert.equal(hay.slice(r!.start, r!.end), "delay at two minutes for every retry loop.");
});

test("findAnchorRange refuses a trivial remnant rather than mark the wrong words", () => {
  assert.equal(findAnchorRange("The cap is fine.", "The completely different selection body"), null);
});

// ── sliceRanges: one global range over many text nodes ─────────────────────────────────────────

test("sliceRanges splits a range across nodes", () => {
  // nodes: "Use " (4) | "exponential" (11) | " backoff." (9); range covers "exponential backoff"
  const slices = sliceRanges([4, 11, 9], 4, 23);
  assert.deepEqual(slices, [
    { idx: 1, s: 0, e: 11 },
    { idx: 2, s: 0, e: 8 },
  ]);
});

test("sliceRanges stays inside one node when the range does", () => {
  assert.deepEqual(sliceRanges([10, 10], 12, 15), [{ idx: 1, s: 2, e: 5 }]);
});

// ── grouping + state predicates ────────────────────────────────────────────────────────────────

test("threadsByAnchor groups threads per turn", () => {
  const by = threadsByAnchor([th({ tid: "t1" }), th({ tid: "t2" }), th({ tid: "t3", anchorUuid: "a2" })]);
  assert.deepEqual([...by.keys()], ["a1", "a2"]);
  assert.equal(by.get("a1")!.length, 2);
});

test("the popover keeps the chat renderer but sheds its transcript-coupled hover chrome", () => {
  // the user 2026-08-23, with a recording: hovering inside the comment box appended glow bands into
  // .cmt-msgs (the band math expects the transcript's host), posted dotHover/dotOpen with the MAIN
  // session's id and the THREAD's uuids (cross-lighting the timeline wrongly), and rail time-markers
  // painted 45px left of gutterless turns — a clipped sliver at the popover edge.
  assert.match(UI, /let renderingIntoThread = false;/);
  assert.match(UI, /renderingIntoThread = true;\s*\/\/ same renderer, minus the transcript-coupled hover chrome/);
  assert.match(UI, /renderingIntoThread = false;\s*\n\s*renderingSid = saved;/, "cleared before the fill returns");
  assert.match(UI, /if \(\(anchorUuid \|\| epoch != null\) && !renderingIntoThread\) wireTurnHover/,
    "no glow bands, no cross-pane posts, no dot-nav promises inside the thread");
  assert.match(UI, /epoch != null && !renderingIntoThread && turn\.querySelector/,
    "no rail time-markers on gutterless popover turns");
});

test("an unread thread wears ONE outline box around its whole passage and a shouting rail tick", () => {
  // the user 2026-08-23: the 45% unread tint alone was too subtle — a thread that replied while the
  // box was closed needs a visible element. That element was a yellow corner dot on the run's last
  // segment until 2026-09-08 (then the tab strip's dashed needs-you ring on the mark), and since
  // 2026-09-10 it is ONE outline around the WHOLE highlighted area: the ring was an outline on the
  // inline mark and painted once per line fragment, a dashed box per line. Since 2026-09-12 the box is
  // dashed in the needs-you red again (the user wanted the tab strip's idiom back; matching the notch
  // had made it solid yellow), and a passage of one or two rows wears the per-fragment ring instead —
  // the painter's call, by row count. The box is a positioned child of the turn that render.ts measures
  // from the marks (its pins live in comment-outline.test.ts). The rail tick still grows and
  // double-rings, its halo in the same red. All clear with the unread flag on open.
  assert.doesNotMatch(CSS, /mark\.cmt-hl\.unread\.hl-last::after/, "the corner dot is gone");
  assert.doesNotMatch(CSS, /mark\.cmt-hl\.unread \{ outline/, "no outline on the mark by unread alone: it would paint per line fragment");
  assert.match(CSS, /\.cmt-outline \{ position: absolute; pointer-events: none;[^}]*outline: 1\.5px dashed var\(--st-awaiting-bg\);/s, "one box, the needs-you ring");
  assert.match(CSS, /mark\.cmt-hl\.unread\.cmt-ring \{ outline: 1\.5px dashed var\(--st-awaiting-bg\); outline-offset: 1px; \}/, "the one- or two-row ring, the same stroke");
  assert.match(CSS, /\.cmt-tick\.unread \{[^}]*0 0 0 3px var\(--st-awaiting-bg\); \}/s, "the tick's halo agrees by colour");
  assert.match(UI, /function paintCommentOutlines\(sid: string\): void \{/);
  assert.doesNotMatch(CSS, /mark\.cmt-hl \{[^}]*position: relative;/s, "nothing left for the mark to anchor");
  assert.match(CSS, /\.cmt-tick\.unread \{ width: 10px; height: 6px; right: 0; opacity: 1;/);
  // the clearing story is the existing machinery, untouched: optimistic on open + kernel watermark
  assert.match(UI, /if \(th\) th\.unread = false;\s*\/\/ optimistic; the kernel's watermark reconciles/);
});

test("an unread thread tints its turn's RAIL segment yellow; clicking the rail opens the thread", () => {
  // the user 2026-08-23: the corner dot is easy to miss — the identity line's own segment is the
  // prominent cue. Cleared on this same pass the moment the thread is viewed (openCommentPopover
  // drops the flag and re-runs applyCommentMarks); the clear sweep runs BEFORE the re-apply so a
  // resolved/removed thread can never leave a stale tint.
  assert.match(UI, /for \(const t of Array\.from\(v\.el\.querySelectorAll\("\.turn\.cmt-rail-unread"\)\)\) t\.classList\.remove\("cmt-rail-unread"\);/);
  assert.match(UI, /turn\.classList\.toggle\("cmt-rail-unread", list\.some\(\(t\) => !!t\.unread && t\.status === "open"\)\);/);
  assert.match(CSS, /\.turn\.cmt-rail-unread::before \{ background: var\(--cmt-hl\); opacity: 1; width: 3px; left: 10px; \}/);
  // the rail-hit click checks at CLICK time, so the strip reverts to timeline navigation once read
  assert.match(UI, /const um = turn\.querySelector\("mark\.cmt-hl\.unread"\) as HTMLElement \| null;/);
  assert.match(UI, /if \(um\?\.dataset\.tid && activeId\) \{ openCommentPopover\(activeId, um\.dataset\.tid, e\.clientX, e\.clientY\); return; \}/);
});

test("busy and stuck are disjoint state families", () => {
  for (const s of ["working", "retrying", "compacting"]) assert.ok(threadBusy(s) && !threadStuck(s));
  for (const s of ["permission", "picker"]) assert.ok(threadStuck(s) && !threadBusy(s));
  assert.ok(!threadBusy("waiting") && !threadStuck(""));
});

// ── optimistic sends reconcile against the frame ───────────────────────────────────────────────

test("prunePending spends a pending row when its message lands", () => {
  const pending = [{ text: "why jitter?", t: 1 }, { text: "and the cap?", t: 2 }];
  const msgs = [{ who: "you" as const, text: "why  jitter?", t: 5 }];   // whitespace drift tolerated
  assert.deepEqual(prunePending(pending, msgs), [{ text: "and the cap?", t: 2 }]);
});

test("prunePending spends one pending per landed message — a repeated reply keeps its bubble", () => {
  const pending = [{ text: "why?", t: 1 }, { text: "why?", t: 2 }];
  const msgs = [{ who: "you" as const, text: "why?", t: 5 }];
  assert.deepEqual(prunePending(pending, msgs), [{ text: "why?", t: 2 }]);
});

// ── source pins: the wiring (render.ts, kernel.py, sdk_backend.py, styles.css) ─────────────────

const UI = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");
const CSS = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "styles.css"), "utf8");
const KERNEL = fs.readFileSync(path.resolve(process.cwd(), "..", "kernel", "kernel.py"), "utf8");
const BACKEND = fs.readFileSync(path.resolve(process.cwd(), "..", "kernel", "sdk_backend.py"), "utf8");

test("the selection menu offers Comment, gated on a real transcript turn", () => {
  assert.match(UI, /mk\("Comment", \(\) => openCommentComposer\(/);
  assert.match(UI, /q\?\.uuid && activeId && !isProvisionalId\(activeId\)/);
});

test("marks, badges AND every popover button ride the stable document.body delegate", () => {
  assert.match(UI, /cmtopen: \(elx\) =>/, "delegated — marks are re-created on every rebuild");
  assert.match(UI, /m\.dataset\.act = "cmtopen"/);
  // the count badge is GONE (the user 2026-08-17): the highlight + the rail tick do the speaking
  assert.doesNotMatch(UI, /cmt-badge/);
  for (const act of ["cmtclose", "cmtsend", "cmtbreak", "cmtdelete", "cmtopensession"]) {
    assert.ok(UI.includes(`${act}:`), `${act} handler missing from the body delegate`);
    assert.ok(UI.includes(`dataset.act = "${act}"`), `${act} button missing its data-act`);
  }
  // Resolve is GONE (the user 2026-08-17): Delete is the only closer — the handler survives for
  // legacy resolved rows, but no button mints new ones
  assert.ok(!UI.includes('rs.dataset.act = "cmtresolve"'), "no Resolve button remains");
});

test("highlights re-apply after every render path", () => {
  assert.match(UI, /m\.type === "session" \|\| m\.type === "chatTail" \|\| m\.type === "chatHead" \|\| m\.type === "chatWindow" \|\| m\.type === "chatTurns" \|\| m\.type === "chatEpisode"\)\)\s*\n\s*applyCommentMarks\(String\(m\.id\)\)/);   // chatTurns: a gap's page (T386 stage 2), where chatMore was   // chatWindow / chatMore: the proto-2 pages rebuild DOM too (T323 stage 4b)
  assert.match(UI, /applyCommentMarks\(activeId\);\s+\/\/ the re-window rebuilt turns/,
               "the scroll re-window path re-anchors too");
  // the syncView wrapper covers renders that run OFF the message handlers (tab switch, prebuild)
  assert.match(UI, /function syncView\(id: string, atBottom\?: boolean, anchored: boolean = atBottom !== undefined\): View \{\s*\n\s*const v = syncViewInner\(id, atBottom, anchored\);\s*\n\s*applyCommentMarks\(id\);/);
});

test("a comments frame refreshes the open popover IN PLACE — composer and caret survive", () => {
  assert.match(UI, /prev\.dataset\.mode === mode && prev\.dataset\.tid === \(th \? th\.tid : create!\.uuid\)\s*\n\s*&& prev\.dataset\.status === status/);
  // a create dialog only in its own mode, and an echo-mode one only for the same passage in the same sent state: a
  // dialog opened over it on another passage of the message, or over its own sent dialog, is rebuilt, or the old box's
  // words would be posted there
  assert.match(UI, /&& \(!create \|\| \(\(prev\.dataset\.echo === "1"\) === !!create\.echo\s*\n\s*&& \(!create\.echo \|\| \(prev\.dataset\.exact === create\.exact && prev\.dataset\.sent === sentId\)\)\)\)\) \{/,
    "the in-place refresh of a create dialog is keyed on its mode (a dialog without the stamp is main mode's), and an echo-mode one's "
    + "on the passage and the create it sent. The "
    + "passage and the sent halves are executed in comment-create-gesture-browser.test.ts: the passage half by 'a comment opened from the "
    + "keyboard over an unsent dialog on another passage of the same message gets its own dialog, and the words typed there stay on their "
    + "passage', the sent half by 'a comment opened from the keyboard over a sent dialog on the same message gets its own dialog, and Enter "
    + "there never posts the sent words'. The mode half is a source pin only: a dialog in the other mode over an open one of the same "
    + "message comes only from the keyboard's menu (a press outside closes the open one first), once the host's latest evidence changed "
    + "while that one was open, by its connection's connect push, a caps frame or any create answer from the host, with the key or "
    + "without it, and the rebuild it "
    + "forces keeps the box's typing on its own mode's draft key");
  assert.match(UI, /if \(create && create\.echo\) \{ pop\.dataset\.echo = "1"; pop\.dataset\.exact = create\.exact; pop\.dataset\.sent = sentId; \}/,
    "a full build stamps an echo-mode dialog with its mode, its passage and its sent create, which the in-place key above compares; a "
    + "main-mode dialog carries none, as main's dialog did, and the key reads it as main mode (where the code lives; executed in "
    + "comment-create-gesture-browser.test.ts by the main-mode group, which compares each create dialog's DOM with the base's and reds "
    + "with the stamp on a main-mode dialog, and by 'main mode: a comment opened from the keyboard over a sent dialog on another passage "
    + "of its message keeps the old dialog, and Enter posts its words there, as the base did', which reds when the key needs the stamp; "
    + "with no stamp at all, the leg's tests that read a dialog's mode from it red)");
  assert.match(UI, /function fillCommentMsgs\(list: HTMLElement, th: CommentThread, sid: string\)/);
});

test("the working state starts on the gesture, and delete is optimistic and cuts the work", () => {
  // create: a synthetic working thread marks the passage before any round-trip; the frame's
  // wholesale list replacement retires it, and a refusal drops it with the warn
  assert.match(UI, /tid: "pending:" \+ create\.uuid, anchorUuid: create\.uuid/);
  assert.match(UI, /state: "working",\s*\n\s*unread: false/);
  assert.match(UI, /t\.tid !== "pending:" \+ pa\.uuid/);
  // (main mode keeps those three lines as main had them.) An echo-mode create's synthetic thread is its gesture's, keyed
  // by its id, and only its own refusal (its typed commentCreateFailed) drops it
  assert.match(UI, /tid: "pending:" \+ held\.createId, anchorUuid: create\.uuid/,
    "one synthetic thread per echo-mode create gesture, keyed by its id (where the code lives; executed in comment-create-gesture-browser.test.ts: "
    + "'the first create's acknowledgment retires only its own hold and working mark' and 'an acknowledgment naming a create this viewer does not hold adopts nothing and retires nothing')");
  assert.match(UI, /dropSynthThread\(held\.sid, held\.createId\); refusedCreateBack\(held\);/,
    "an echo-mode refusal's own typed answer drops its synthetic thread and hands its words back (where the code lives; executed in comment-create-gesture-browser.test.ts: "
    + "'a refused comment's own dialog comes back with its typed name, and its working mark goes at once')");
  // reply: the local state flips on send; the kernel's next frame confirms
  assert.match(UI, /cur\.th\.state = "working";\s+\/\/ optimistic/);
  // delete: the highlight goes NOW, and the kernel interrupts the in-flight reply before the kill
  assert.match(UI, /filter\(\(t\) => t\.tid !== cur\.th\.tid\)\);\s*\n\s*applyCommentMarks\(cur\.sid\);\s*\n\s*closeCommentPop\(\);/);
  assert.match(KERNEL, /be\.interrupt\(th\["sid"\]\)[\s\S]{0,200}be\.kill\(th\["sid"\]\)/);
});

test("the popover send acknowledges before any round-trip", () => {
  assert.match(UI, /send\.disabled = true; send\.classList\.add\("busy"\); \}\s+\/\/ ack before the round-trip/);
  assert.match(UI, /the pending bubble IS the acknowledgement/);
});

test("create adopts exactly the thread the kernel named — never a guess", () => {
  assert.match(UI, /m\.type === "commentCreated"/);
  assert.match(UI, /function adoptCommentThread\(sid: string, tid: string\)/);
  assert.match(KERNEL, /"type": "commentCreated", "id": sid, "tid": tid/);
  // the FRAME rides ahead of the ack, so adoption always finds the thread in the map
  assert.match(KERNEL, /fr = _comments_frame\(sid\)\s*\n\s*if fr:\s*\n\s*client\["send"\]\(json\.dumps\(fr\)\)\s*\n\s*client\["send"\]\(json\.dumps\(\{"type": "commentCreated"/);
});

test("a refused reply hands the words back instead of thinking forever", () => {
  assert.match(KERNEL, /"type": "commentSendFailed", "id": sid, "tid": str\(msg\["tid"\]\)/);
  assert.match(UI, /m\.type === "commentSendFailed"/);
  assert.match(UI, /commentDrafts\.set\(String\(m\.tid\), lost\.text\)/);
});

test("ending the parent sweeps its threads' CLIs — no unreachable running sessions", () => {
  assert.match(KERNEL, /_comment_kill_all\(sid, be\)/);
  assert.match(KERNEL, /def _comment_kill_all\(parent_sid, be\):/);
});

test("a refused create un-sticks the popover; a pre-seam anchor tip-forks instead of erroring", () => {
  assert.match(UI, /m\.type === "warn" && pendingCommentAnchor\) \{[\s\S]{0,400}document\.getElementById\("cmt-pop"\)\?\.remove\(\);/);
  assert.match(KERNEL, /def _anchor_adapter\(path, sid\)/);
  assert.match(KERNEL, /return "", cut_t, None/);
});

test("the projection never reads the parent transcript pre-fork", () => {
  assert.match(KERNEL, /if reg\.get\("forkOf"\):\s*\n\s*return \[\]/);
});

test("a promoted thread whose session ended drops off the frame entirely", () => {
  assert.match(KERNEL, /if status == "promoted" and not _thread_reg\(tsid\)\.get\("alive"\):\s*\n\s*continue/);
});

test("promote latches the row before seeding; racing ops refuse through the CAS", () => {
  assert.match(KERNEL, /def _comment_update_if\(parent_sid, tid, expect, \*\*changes\):/);
  assert.match(KERNEL, /_comment_update_if\(parent_sid, tid, \("open", "resolved"\), status="promoting"\)/);
  assert.match(KERNEL, /def _revert\(msg\):/);
});

test("the /kill route sweeps comment threads like the WS endSession op", () => {
  assert.match(KERNEL, /_comment_kill_all\(sid, be\)\s+# its comment threads must not outlive it \(the WS endSession twin\)/);
});

test("the three doors that record a death sweep the session's comment threads: the WS endSession op, the /kill route and the end-on-idle sweep", () => {
  // Each door is pinned by its own kill attribution to the epilogue that follows it: the kill, the death record,
  // _comment_kill_all and the closed frame (the WS op then confirms the close at once). The fork's one routine for
  // the three, _end_and_record, retired at the 2026-09-15 upstream pull-in with the tmux backend whose death
  // corroboration it carried; the doors are upstream's inline arms again, so each is pinned whole and the sweep is
  // counted, one call per door and no fourth. cancelCreate's _end_pending_sid, the one intentional kill outside
  // these doors, records no death by design and is not pinned here. The executed twin (a client door ending one sid
  // through its backend once) is tests/test_kernel_headless_ops.py.
  assert.match(KERNEL, /sys\.stderr\.write\("kill: %s via endSession WS op\\n" % sid\)[^\n]*\n\s+be\.kill\(sid\); _record_death\(sid, int\(time\.time\(\)\), "kill"\)[^\n]*\n\s+_comment_kill_all\(sid, be\)[^\n]*\n\s+_send_to_app\("chat", \{"type": "closed", "id": sid\}\)\n\s+_confirm_close_now\(sid\)/, "the WS endSession op");
  assert.match(KERNEL, /sys\.stderr\.write\("kill: %s via \/kill route\\n" % sid\)[^\n]*\n\s+be\.kill\(sid\)\n\s+_record_death\(sid, int\(time\.time\(\)\), "kill"\)\n\s+_comment_kill_all\(sid, be\)[^\n]*\n\s+_send_to_app\("chat", \{"type": "closed", "id": sid\}\)/, "the /kill route");
  assert.match(KERNEL, /sys\.stderr\.write\("kill: %s via end-on-idle \(self-close%s\)\\n" % \(sid, ", a comment thread" if thread else ""\)\)\n\s+be = Sessions\.backend_for\(sid\)\n\s+be\.kill\(sid\)\n\s+_record_death\(sid, int\(now\), "kill"\)\n\s+_comment_kill_all\(sid, be\)\n\s+_send_to_app\("chat", \{"type": "closed", "id": sid\}\)/, "the end-on-idle sweep's arm");
  assert.equal((KERNEL.match(/_comment_kill_all\(sid, be\)/g) || []).length, 3, "one sweep per door, no fourth");
  assert.doesNotMatch(KERNEL, /_end_and_record/, "the fork's routine is gone with the backend it corroborated");
});

test("a thread that couldn't start says so — the error note renders in the thread", () => {
  // (the pulsing dots this note used to preempt are retired outright — the dots-gone test below)
  assert.match(KERNEL, /be\.launch_error\(tsid\) if hasattr\(be, "launch_error"\) else None/);
  assert.match(UI, /cmt-note cmt-err/);
  assert.match(UI, /if \(th\.status === "open" && th\.error\) \{/);
});

test("Delete is offered on open and resolved threads, never mid-promote", () => {
  // Resolve is gone (the user 2026-08-17) — Delete is the closer for BOTH, still gated off
  // 'promoting'/'promoted' (the kernel refuses those anyway; the button never dangles one)
  assert.match(UI, /if \(th\.status === "open" \|\| th\.status === "resolved"\) \{/);
});

test("break out posts commentPromote and acks with a provisional tab", () => {
  assert.match(UI, /function showBreakoutPrompt\(sid: string, tid: string\)/);
  assert.match(UI, /type: "commentPromote", id: sid, tid, name \}\);\s*\n\s*close\(\);\s*\n\s*closeCommentPop\(\);\s*\n\s*openProvisional\(\{ name, backend: "sdk", dir: "", host: hostOf\(sid\) \}\);/);
});

test("the create dialog pre-reads the kernel's default-comment trio and shows it", () => {
  // The user 2026-08-29: the gear can pin a default model/effort/fast for every NEW thread. The
  // dialog must SHOW the effective default (pick > setting > inherit) so a pick stays a visible
  // deviation; the kernel re-resolves the same order at create, so a stale pre-read can mislabel
  // a chip but never mislaunch a thread.
  assert.match(UI, /let commentDefaults = \{ model: "session", effort: "session", fast: "session" \};/);
  assert.match(UI, /if \(d\.commentDefaults\) adoptCommentDefaults\(d\.commentDefaults\);/);
  assert.match(UI, /function refreshCommentDefaults/);
  // re-read at dialog open, repainting the row IN PLACE (the composer holds focus and a draft)
  assert.match(UI, /refreshCommentDefaults\(\(\) => \{\s*\n\s*if \(pendingCommentAnchor !== create\) return;/);
  assert.match(UI, /const effVal = chosen \|\| setDef\(kind\);/);
  // a version id stored in the setting still labels correctly (families hold their versions)
  assert.match(UI, /function modelChoiceLabel\(value: string\)/);
  assert.match(KERNEL, /"commentDefaults": \{"model": jd\._state_str\("comment-model", "session"\),/);
});

test("fast rides the create end to end, resolved dialog > setting > inherit at the kernel", () => {
  // the chip is offered only where the effective model could run fast (no control that only toasts)
  assert.match(UI, /if \(canFast\(create\.model \|\| setDef\("model"\) \|\| st\?\.model \|\| ""\)\) metaRight\.append\(mkSel\("fast"\)\);/);
  // the dialog's picks ride the held create (newCommentCreate reads anchor.fast) and every frame built from it,
  // the send's and the in-flight retry's alike; the builder is driven directly by the create-identity tests below
  assert.match(UI, /const held = newCommentCreate\(create, text, nm\)/);
  assert.match(UI, /vscodeApi\.postMessage\(commentCreateFrame\(held\)\)/);
  assert.match(UI, /vscodeApi\?\.postMessage\(commentCreateFrame\(c\)\)/);
  assert.match(KERNEL, /def _comment_launch_prefs\(model="", effort="", fast=""\):/);
  assert.match(KERNEL, /model, effort, fast = _comment_launch_prefs\(model, effort, fast\)/);
  assert.match(KERNEL, /fast=str\(msg\.get\("fast"\) or ""\)/);       // the ws op hands it through…
  assert.match(KERNEL, /"fast": str\(msg\.get\("fast"\) or ""\),/);   // …and a lag-parked create keeps it
  assert.match(KERNEL, /fast=pk\.get\("fast", ""\)/);
});

test("kernel registers every comment drive op", () => {
  for (const op of ["commentCreate", "commentReply", "commentResolve", "commentDelete", "commentSeen", "commentPromote"]) {
    assert.ok(KERNEL.includes(`"${op}"`), `${op} missing from ID_OPS/handlers`);
  }
});

test("the comments frame rides its own dedup slot, never the chat delta baseline", () => {
  assert.match(KERNEL, /_send_client\(c, \("comments", s\["sid"\]\), fr\)/);
});

test("a thread fork withholds the names/ entry; promote seeds first, then registers", () => {
  assert.match(BACKEND, /if not thread_of:\s*\n\s*write_name/);
  assert.match(BACKEND, /def promote_thread\(/);
  assert.match(BACKEND, /reg\.get\("threadOf"\):\s*\n\s*continue/, "live_sessions skips threads — no tab");
  assert.match(KERNEL, /err = _seed_fork_stores\(parent_sid, tsid, parent_path, str\(th\.get\("cutUuid"\) or ""\)\)/);
});

test("the WHOLE popover drags — grip anywhere that isn't a control — and closes on tab switch", () => {
  assert.match(UI, /pop\.addEventListener\("pointerdown"/);
  assert.match(UI, /pop\.setPointerCapture\(ev\.pointerId\)/);
  assert.match(UI, /ev\.clientX > pr\.right - 18 && ev\.clientY > pr\.bottom - 18\) return;/);
  assert.match(CSS, /\.cmt-pop \{[^}]*resize: both/s);
  assert.match(CSS, /\.cmt-pop\.sized \.cmt-quote \{/, "a user resize hands the room to the quoted context");
  assert.match(UI, /commentPopPos = \{ x, y \};/);
  assert.match(UI, /if \(openCommentKey && openCommentKey\.sid !== id\) closeCommentPop\(\);/);
  assert.match(CSS, /\.cmt-pop \{[^}]*cursor: grab/s, "the grab hand covers the whole box now");
});

test("picking a model/effort never reads as an outside press — the box stays put", () => {
  // the dropdowns and the break-out dialog are appended to document.body (fixed position, like the
  // statusline's menus), so the outside-press closer must exempt them: it used to close the popover
  // on mousedown and null pendingCommentAnchor before the item's click could land the pick, and a
  // click on the break-out dialog's Cancel stranded the user the same way (the user 2026-08-18)
  assert.match(UI, /if \(!pop \|\| pop\.contains\(ev\.target as Node\)\) return;\s*\n\s*if \(\(ev\.target as HTMLElement\)\.closest\?\.\("\.meta-menu, #fork-prompt"\)\) return;\s*\n\s*closeCommentPop\(\);/);
  // and the surviving popover shows the pick THROUGH the chat's own builder (2026-08-25 parity):
  // the shared menu's click arms the sid-scoped pending dots, and the frame-driven refresh re-runs
  // syncMetaControls on the popover's row exactly as the chat's tick does
  assert.match(UI, /metaPending\.set\(`\$\{opSid\}:\$\{kind\}`, \{ was, until: Date\.now\(\) \+ 20_000 \}\);/);
  assert.match(UI, /if \(th && cm\) syncMetaControls\(cm, threadMetaStatus\(th\), th\.tid\);/);
});

test("marks use the prefix-tolerant anchor matcher", () => {
  assert.match(UI, /findAnchorRange\(nodes\.map\(\(t\) => t\.data\)\.join\(""\), th\.exact\)/);
});

test("the highlight is highlighter-YELLOW — never the selection blue — and one unbroken block", () => {
  assert.match(CSS, /--cmt-hl: #ffd54a;/);
  assert.match(CSS, /mark\.cmt-hl \{[^}]*var\(--cmt-hl\)/s);
  assert.doesNotMatch(CSS.match(/mark\.cmt-hl \{[^}]*\}/s)![0], /var\(--accent\)/);
  // the radius sits only on the run's outer ends — per-segment rounding drew word-boundary seams
  assert.match(UI, /classList\.toggle\("hl-first", i === 0\)/);
  assert.match(CSS, /mark\.cmt-hl\.hl-first \{ border-top-left-radius: 2px/);
  // a fully-covered inline-code span tints at the ELEMENT: a mark inside it can't paint the code's
  // padded background, which left an untinted sliver around every code word (the word-island look)
  assert.match(UI, /host\.classList\.toggle\("cmt-hl-host", th\.status !== "resolved" && th\.status !== "merged"\)/);
  assert.match(UI, /p\.classList\.remove\("cmt-hl-host"\)/);
  assert.match(CSS, /code\.cmt-hl-host \{ background: color-mix\(in srgb, var\(--cmt-hl\) 30%, var\(--code-bg\)\)/);
  assert.match(CSS, /code\.cmt-hl-host > mark\.cmt-hl \{ background: transparent/);
});

test("the create dialog names the thread right there: prefilled <session>-comment-<N>, validated", () => {
  // T289: the prefill is a HINT from the BARE session name (comment-name.ts), remembered on the box so an
  // untouched one is sent as "" and the kernel picks its own default
  assert.match(UI, /const prefill = defaultCommentName\(sess0\?\.name, sid, \(commentThreads\.get\(sid\) \|\| \[\]\)\.length\);\s*\n\s*nameBox\.dataset\.prefill = prefill;\s*\n\s*nameBox\.value = commentDrafts\.get\(nk\) \|\| prefill;/);
  // the name lives IN the header ("New comment: <name>"), the button says Comment, and the picks ride along
  assert.match(UI, /"New comment:"/);
  assert.match(UI, /if \(nameBox\) head\.append\(title, nameBox, maxBtn, closeBtn\);/);   // the maximize button rides between (2026-09-10, comment-pop-size.test.ts)
  assert.match(UI, /send\.setAttribute\("aria-label", create \? "Comment" : "Send"\);/);   // the ➤ carries the word
  // the anchor's picks ride the held create. Main mode: main's send, and main's frame, whole
  assert.match(UI, /const held = newCommentCreate\(create, text, nm\);\s*\n\s*vscodeApi\.postMessage\(commentCreateFrame\(held\)\);/,
    "a main-mode send mints the held create from the anchor, its picks included, and posts main's frame (where the code lives; executed "
    + "in comment-create-gesture-browser.test.ts: 'main mode: a comment's frame is main's, whole, its picks and a createId minted at the "
    + "send and re-posted unchanged, as the base posted it', whose dialog picks a model, an effort and fast, and which compares every "
    + "field of every frame with the base's)");
  // echo mode: the create is held and stamped on its dialog BEFORE its frame is posted, since federation answers a
  // create it cannot deliver (no open relay socket) inside the post itself
  const echoAt = UI.indexOf("function sendEchoCreate(");
  const echoBody = UI.slice(echoAt, UI.indexOf("\nfunction ", echoAt + 10));
  const at = (s: string) => echoBody.indexOf(s);
  const posted = "vscodeApi.postMessage(commentCreateFrame(held));";
  assert.ok(at("const held = newCommentCreate(create, text, nm);") >= 0,
    "the echo-mode send mints the held create from the anchor (where the code lives; executed in comment-create-gesture-browser.test.ts, "
    + "where every first comment's send checks what was posted: firstCreate's precondition, one create carrying the anchor's passage, the "
    + "typed words and a create id, as in 'a second comment on a message, opened while the first comment there is still being created, "
    + "opens empty under the suggested name'; and the anchor's picks riding the posted create, by 'the create dialog's fast pick rides "
    + "the comment's posted create')");
  assert.equal(echoBody.split(posted).length, 2,
    "the echo-mode send posts the held create's frame once (where the code lives; executed in comment-create-gesture-browser.test.ts by "
    + "that same precondition, exactly one create posted for one send, and by 'Enter again in a dialog whose comment is still being "
    + "created posts nothing')");
  assert.ok(at("cmtEchoCreates.set(held.createId, held);") >= 0 && at("cmtEchoCreates.set(held.createId, held);") < at(posted)
            && at("create.createId = held.createId;") >= 0 && at("create.createId = held.createId;") < at(posted),
    "the echo-mode send holds its create and stamps the dialog's createId before it posts the frame (where the code lives; executed in "
    + "comment-create-gesture-browser.test.ts: 'with the real federation bundle, a relay's connect push carrying the marker posts again "
    + "the comment a drop left held, and one without it hands that comment back with no post', whose precondition is the dialog drawn "
    + "sent by the drop's warn inside the send)");
  assert.match(UI, /if \(create && create\.echo\) \{ sendEchoCreate\(pop, create, box, send, text\); return; \}/,
    "the send goes by the dialog's mode, taken when it opened (where the code lives; executed in comment-create-gesture-browser.test.ts: "
    + "'a comment dialog keeps the mode it opened with: one opened on a kernel whose connect push lacks the marker is main's for its whole "
    + "life, though the kernel comes back with the echo while it is open, and one opened after that is echo mode')");
  // the comment's own model/effort selectors reuse the statusline's /models-fed choices + menu skin
  assert.match(UI, /const metaRow = el\("div", "statusline cmt-meta-row"\);/);   // the chat statusline dress (2026-08-25 parity)
  assert.match(UI, /META_CHOICES\[kind\]/);
  assert.match(KERNEL, /model=str\(msg\.get\("model"\) or ""\), effort=str\(msg\.get\("effort"\) or ""\)/);
  // the kernel's default starts from the same count, then bumps past every taken or in-flight name
  // (session names are reserved atomically, 2026-09-08) — the prefill and the default agree on the count
  assert.match(KERNEL, /n = len\(data\.get\("threads"\) or \[\]\) \+ 1[\s\S]{0,400}"%s-comment-%d" % \(sess\["name"\], n\)/);
  assert.match(UI, /const base = thName \|\|/, "break-out prefills the thread's own name");
});

test("the landing pulse fires once per navigation, not once per history-fetch round", () => {
  assert.match(UI, /let flashedAnchor: string \| null = null;/);
  assert.match(UI, /if \(flashKey == null \|\| flashKey !== flashedAnchor\)/);
  assert.match(UI, /landOn\(target, uuid, quoteEl \?\? firstTextAtomBelow\(target\), quote\);/);   // the one landing write, aligned on the words when the frame quotes them (T386)
  assert.match(UI, /if \(anchor\) flashedAnchor = null;/);
});

test("math hosts tint like code hosts — a mark can't paint KaTeX's glyph spacing", () => {
  assert.match(UI, /closest\(".katex"\)/);
  assert.match(CSS, /\.md \.katex\.cmt-hl-host \{ background: color-mix\(in srgb, var\(--cmt-hl\) 30%/);
  assert.match(CSS, /\.md \.katex\.cmt-hl-host mark\.cmt-hl \{ background: transparent/);
});

test("scroll-rail ticks mark the commented spots and jump-open on click", () => {
  assert.match(UI, /function updateCommentRail\(\)/);
  assert.match(UI, /tick\.dataset\.act = "cmtjump"/);
  assert.match(UI, /cmtjump: \(elx\) =>/);
  assert.match(UI, /if \(sid === activeId\) updateCommentRail\(\);/);
  assert.match(CSS, /\.cmt-tick \{/);
  assert.match(CSS, /\.cmt-rail \{ position: fixed;/);
});

test("ticks and message notches share ONE scrollbar frame, so they can never disagree about order", () => {
  // the user 2026-08-17: scrolling through a history load moved the comment highlights relative to
  // the blue message notches — the ticks were placed by uniform index fraction, a second frame that
  // drifts from the notches' measured-height pixel offsets. Both painters now consume
  // contentOffsetFrame, the one event-index → content-pixel mapping.
  assert.match(UI, /function contentOffsetFrame\(/);
  assert.match(UI, /const off = frame\.offsetOf\(evUnit\[idx\]\);/,
    "ticks place by the shared frame, in UNIT space (anchors are events; the frame speaks units)");
  assert.doesNotMatch(UI, /\(idx \/ n\) \* 100/, "the uniform index-fraction percent frame is gone");
  // the rail repaints with the notches (same rAF), so both always draw from one world
  assert.match(UI, /paintRailSticky\(\); paintScrollMarks\(\); updateCommentRail\(\);/);
  // an unchanged tick set moves IN PLACE — ticks are buttons, and a mid-press rebuild eats the click
  assert.match(UI, /kids\.every\(\(k, i\) => k\.dataset\.tid === ticks\[i\]\.th\.tid\)/);
  assert.match(UI, /kids\[i\]\.style\.top = t\.y \+ "px";/);
});

test("while the thread is WRITING the passage holds the await-green tint and NOTHING crawls", () => {
  // the user 2026-08-24 (superseding 2026-08-23's tick-crawl compromise): the in-flight cue is the
  // await-green STATE COLOR on the passage itself — its own new-test block below pins the colors;
  // this one keeps the class wiring and holds the line on motion: no strips, no keyframes, anywhere.
  assert.match(UI, /m\.classList\.toggle\("busy", commentInFlight\(th\)\);/);
  assert.doesNotMatch(CSS, /mark\.cmt-hl\.busy \{[^}]*repeating-linear-gradient/s, "no strips on prose");
  assert.doesNotMatch(CSS, /@keyframes cmt-ants /, "the passage keyframes stay gone");
  assert.doesNotMatch(CSS, /@keyframes cmt-tick-ants/, "…and the tick's miniature march followed them out");
  assert.match(UI, /\+ \(commentInFlight\(th\) \? " busy" : ""\);/);
  assert.match(UI, /\+ ":" \+ \(commentInFlight\(t\.th\) \? 1 : 0\)\)/, "an in-flight flip re-renders the tick");
});

test("the popover renders the thread with the CHAT's own renderer from the branch point", () => {
  assert.match(UI, /renderingSid = th\.tid;/);
  assert.match(UI, /const node = renderEvent\(ev, prev, turnWorkedSecs\(evs, it\.index, thWorking\)\);\s*\n\s*list\.appendChild\(node\);/);   // + the chat's worked footers (the parity bundle, 2026-08-26)
  assert.match(KERNEL, /def _thread_events\(tsid, cut_uuid, now, live_map\):/);
  assert.match(KERNEL, /evs = evs\[at \+ 1:\]/, "sliced to AFTER the branch point — the head system card never rides");
  // the thread's own statusline posts the chat's own ops through the SHARED menu, keyed to the
  // thread sid (toggleMetaMenu's opSid — 2026-08-25 parity: one builder, sid-scoped)
  assert.match(UI, /type: kind === "model" \? "setModel" : kind === "effort" \? "setEffort" : kind === "fast" \? "setFast" : "setMode", id: opSid, value/);
});

test("the tint ladder keeps every state distinct: base < unread < hover", () => {
  const base = CSS.match(/mark\.cmt-hl \{[^}]*var\(--cmt-hl\) (\d+)%/s)![1];
  const unread = CSS.match(/mark\.cmt-hl\.unread \{[^}]*var\(--cmt-hl\) (\d+)%/s)![1];
  const hover = CSS.match(/mark\.cmt-hl:hover \{[^}]*var\(--cmt-hl\) (\d+)%/s)![1];
  assert.ok(Number(base) < Number(unread), "unread must read stronger than read");
  assert.ok(Number(unread) < Number(hover), "hovering an unread mark must still answer");
});

test("comment chrome (badge, popover card) stays on the menu vocabulary", () => {
  assert.match(CSS, /\.cmt-pop \{[^}]*#252526[^}]*\}/s);
  assert.match(CSS, /\.cmt-pop \{[^}]*border-radius: 6px/s);
});

// ── the comment-thread UI pass (the user 2026-08-24, three asks) ─────────────────────────────────

test("an in-flight thread's highlight PULSES await-green — text and hosts in lockstep", () => {
  // mid-reply the passage wears the await-green blend, and it PULSES while generating (the user
  // 2026-08-25, asking for exactly this — superseding the earlier no-motion ruling for THIS state
  // only; the marching ants stay dead below). Settles into the existing full yellow on landing.
  assert.match(CSS, /mark\.cmt-hl\.busy \{\s*\n\s*background-color: color-mix\(in srgb, var\(--st-awaitbg-bg\) 24%, transparent\);\s*\n\s*animation: cmt-busy-pulse 2\.2s ease-in-out infinite;\s*\n\}/);
  // the code/math HOST pairing greens AND pulses the same way, the SAME clock — lockstep by keyframe
  assert.match(CSS, /code\.cmt-hl-host:has\(mark\.cmt-hl\.busy\),\s*\n\.md \.katex\.cmt-hl-host:has\(mark\.cmt-hl\.busy\) \{\s*\n\s*background-color: color-mix\(in srgb, var\(--st-awaitbg-bg\) 24%, transparent\);\s*\n\s*animation: cmt-busy-pulse 2\.2s ease-in-out infinite;/);
  assert.match(CSS, /code\.cmt-hl-host:has\(mark\.cmt-hl\.busy\) \{\s*\n\s*background-color: color-mix\(in srgb, var\(--st-awaitbg-bg\) 24%, var\(--code-bg\)\);\s*\n\s*animation: cmt-busy-pulse-code 2\.2s ease-in-out infinite;/);
  // reduced motion keeps the static green — the pulse joins the loading-cues idiom family
  assert.match(CSS, /@media \(prefers-reduced-motion: reduce\) \{\s*\n\s*mark\.cmt-hl\.busy,[\s\S]{0,160}animation: none; \}\s*\n\}/);
  // the crawl is gone root and branch; the rail tick wears the same state green instead
  assert.doesNotMatch(CSS, /cmt-tick-ants/);
  assert.match(CSS, /\.cmt-tick\.busy \{ background: var\(--st-awaitbg-bg\); \}/);
  // the other highlight states are untouched: base, unread, hover, resolved stay the yellow family
  assert.match(CSS, /mark\.cmt-hl \{\s*\n\s*background: color-mix\(in srgb, var\(--cmt-hl\) 30%, transparent\);/);
  assert.match(CSS, /mark\.cmt-hl\.unread \{ background: color-mix\(in srgb, var\(--cmt-hl\) 45%, transparent\); \}/);
  assert.match(CSS, /mark\.cmt-hl:hover \{ background: color-mix\(in srgb, var\(--cmt-hl\) 58%, transparent\); \}/);
  assert.match(CSS, /mark\.cmt-hl\.resolved \{ background: rgba\(255, 255, 255, 0\.08\); \}/);
});

test("the thread's identity rail runs continuous — no holes at the list's flex gaps", () => {
  // each chat-parity turn's ::before rail segment spans only its own box (top:0..bottom:0), and
  // .cmt-msgs' 6px flex gap sat UNPAINTED between consecutive turns — visible holes in the line.
  // Every turn following another turn stretches its segment up across the gap; non-turn items
  // (pending bubbles, dots, notes) render after the turns, so the + pair never misses.
  assert.match(CSS, /\.turn::before \{ content: ""; position: absolute; left: 10\.5px; top: 0; bottom: 0; width: 2px;/,
    "the base segment this fix extends");
  assert.match(CSS, /\.cmt-msgs \{ flex: 1 1 auto; min-height: 0; overflow-y: auto; display: flex; flex-direction: column; gap: 6px; \}/,
    "the 6px gap the -6px below must stay paired with");
  assert.match(CSS, /\.cmt-msgs \.turn \+ \.turn::before \{ top: -6px; \}/);
  // the day divider between two turns (T339): the flex gap sits on both sides of it and `.turn + .turn` does not fire
  // after it, so its own segment spans margin plus gap each side; derived from the gap and the divider's margins
  const gap = Number(CSS.match(/^\.cmt-msgs \{[^}]*gap: (\d+)px;/m)![1]);
  const margins = CSS.match(/^\.day-divider \{[^}]*margin: (\d+)px 0 (\d+)px;/m)!;
  assert.match(CSS, new RegExp("^\\.cmt-msgs \\.day-divider::before \\{ top: -" + (gap + Number(margins[1])) + "px; bottom: -" + (gap + Number(margins[2])) + "px; \\}", "m"),
    "the popover's divider segment covers the gap above and below");
});

test("the quoted passage is CONTEXT on the thread's opening message — never an item above the branch divider", () => {
  // chronology: the branch happened before the quote, so the quote cannot sit above the divider.
  // It attaches to the opening user message (the chat's citation-as-context idiom), and the
  // standalone block — minted only while the events hadn't landed — is swept when they arrive,
  // which used to leave BOTH on screen: quote on top, "branched" marker below it.
  assert.match(UI, /let quoteHost: HTMLElement \| null = null;\s*\/\/ the thread's OPENING message — the quote's home/);
  assert.match(UI, /if \(!quoteHost && ev\.kind === "user"\) quoteHost = node;/);
  assert.match(UI, /const ctx = el\("div", "cmt-quote cmt-quote-ctx"\);/);
  assert.match(UI, /quoteHost\.insertBefore\(ctx, quoteHost\.firstChild\);/);
  assert.match(UI, /list\.closest\("\.cmt-pop"\)\?\.querySelector\(":scope > \.cmt-quote"\)\?\.remove\(\);/);
  // the pre-events standalone block still renders (there is nothing to attach to yet, and no
  // divider to misorder against) — the create/no-events guard is unchanged
  assert.match(UI, /if \(create \|\| !\(th!\.events \|\| \[\]\)\.length\) \{/);
  assert.match(CSS, /\.cmt-quote-ctx \{ margin: 0 0 4px; \}/);
});

test("the popover's typing dots are retired — the green highlight is the only in-flight cue", () => {
  // the user 2026-08-24 (closing the 2026-08-24 green-highlight pass): "rather than the little
  // spinning dot dot dot thing" — the ellipsis animation goes too. The reply's arrival is announced
  // by the green→yellow settle; the pending bubble still acknowledges the user's own send.
  assert.doesNotMatch(UI, /cmt-dots/);
  assert.doesNotMatch(CSS, /cmt-dots|cmt-dot-pulse/);
  assert.match(UI, /the pending bubble IS the acknowledgement/);
});

// ── T104 (the user 2026-08-26, screenshot): the popover's pending echo wore a one-off washed-gray
// pill — the "third look" the chat killed 2026-07-16, reborn thread-locally — while the chip read
// Ready off one stale relayed frame, so it read as a stuck queued thing with no queued dress. The
// echo now RIDES the chat's own component: renderQueued's bare optimistic group, inherited. ──────
test("the popover's pending echo IS the chat's queued idiom — one component, both boot and live", () => {
  assert.match(UI, /function cmtPendingQueued\(pend: \{ text: string; t: number; imgPaths\?: string\[\] \}\[\]\): HTMLElement \{\s*\n\s*return renderQueued\(\{ kind: "queued", bare: true,/);
  assert.match(UI, /texts: pend\.map\(\(p\) => \(\{ md: p\.text, optimistic: true, cancelable: false, imgPaths: p\.imgPaths \}\)\),/);
  // the parity bundle (2026-08-26): a shipped image rides the pending entry, so the echo renders
  // the SAME thumbnails the chat's echo does — event-sourced from the drop ack, never text-parsed
  assert.match(UI, /if \(previewKind\(m\.path\) === "img"\) cmtShippedImgs\.push\(m\.path\);/);
  assert.match(UI, /imgPaths: cmtShippedImgs\.filter\(\(p2\) => text\.includes\(p2\)\) \}\);/);
  const sites = (UI.match(/cmtPendingQueued\(pend\)/g) || []).length;
  assert.equal(sites, 2, "both render sites — the boot view and the live list — share it");
  // the one-off is gone root and branch: no .pending class minted, no washed-gray CSS
  assert.doesNotMatch(UI, /classList\.add\("pending"\)/);
  assert.doesNotMatch(CSS, /\.cmt-msg\.pending/);
});

// ── THE EXCHANGE LATCH (T102, the user 2026-08-26 — replacing the push-count settle): busy latches
// at the SEND GESTURE (cmtAwaitBase.set in render.ts, before any kernel round-trip — thread-open is
// never the start trigger) and clears ONLY on the reply-arrived event: th.msgs holding MORE
// who==="agent" records than at the send. No push counting (the banned proxy: its all-quiet
// fork-birth frames killed the create-window green, and a stall in its stepping parked green
// forever), no thread-state proxy, no clocks. ────────────────────────────────────────────────────
test("agentCount is the reply-arrived detector's datum — records of the exchange itself", () => {
  const msg = (who: "you" | "agent") => ({ who, text: "x", t: 1 });
  assert.equal(agentCount(th({ msgs: [] })), 0);
  assert.equal(agentCount(th({ msgs: [msg("you")] })), 0, "the send alone arrives no reply");
  assert.equal(agentCount(th({ msgs: [msg("you"), msg("agent")] })), 1, "the reply record raises the count");
  assert.equal(agentCount(th({ msgs: [msg("you"), msg("agent"), msg("you")] })), 1, "a follow-up send does not");
  assert.equal(replyOwed(th({ msgs: [] })), false, "an empty thread owes nothing");
  assert.equal(replyOwed(th({ msgs: [msg("you")] })), true, "…the durable owed half survives reloads");
});

test("busy latches at the SEND gesture and clears exactly on the reply-arrived record (source pins)", () => {
  // create: the gesture latches under the synth tid, before any kernel round-trip
  assert.match(UI, /cmtAwaitBase\.set\(synth\.tid, \{ \.\.\.CMT_LATCH_ZERO \}\);\s+\/\/ the SEND gesture latches the pulse/);
  // follow-up: re-latches at ITS send, with the thread's projected counts at that moment as the base (T237)
  assert.match(UI, /cmtAwaitBase\.set\(cur\.th\.tid, cmtLatchOf\(cur\.th\)\);/);
  // the create's latch carries onto the real thread at adopt (the synth tid retires)
  assert.match(UI, /if \(k\.startsWith\("pending:"\)\) \{ cmtAwaitBase\.set\(tid, cmtAwaitBase\.get\(k\)!\); cmtAwaitBase\.delete\(k\); \}/);
  // (main mode keeps that line as main had it, and skips an echo-mode create's latch: executed below, 'main's adoption
  // never swaps an echo-mode dialog for its thread, and never carries an echo-mode create's latch: with one open, it
  // carries main's latch, clears main's parked adoption and marks the thread seen'). An echo-mode create's latch carries
  // onto its thread at its own ack,
  // in settleAckedCreate
  assert.match(UI, /const k = "pending:" \+ held\.createId, base = cmtAwaitBase\.get\(k\);[^\n]*\n\s*if \(base\) \{ cmtAwaitBase\.delete\(k\); cmtAwaitBase\.set\(tid, base\); \}/,
    "the echo-mode ack carries its own create's latch onto the thread, keyed by the create id (where the code lives; executed below: "
    + "'an echo-mode ack settles the create it answers alone: its hold, its own latch, and its note entry', which runs settleAckedCreate)");
  // the ONE clearing site (T237): the comments frame whose projection carries the SEND (more messages
  // than at the click) — or the thread leaving "open"/erroring. From that frame the KERNEL's replyOwed
  // owns the wash: it reads the thread's transcript with the event model's own turn-end, so a mid-turn
  // interim (the specimen's 'checking…' text) or a backend state flap can never clear the pulse early.
  assert.match(UI, /if \(base !== undefined && cmtLatchReleased\(t, base\)\) cmtAwaitBase\.delete\(t\.tid\);/,
    "against a T237 kernel the latch covers only the pre-round-trip instant (released by the user's own send); an older kernel keeps the T102 reply-arrived clear");
  // the mark's predicate: the latch, then the kernel's owed bit (an older kernel: the records' own owed
  // reading); never a timer, never the client's state read
  assert.match(UI, /if \(cmtAwaitBase\.has\(th\.tid\)\) return true;/);
  assert.match(UI, /const owed = typeof th\.replyOwed === "boolean" \? th\.replyOwed : replyOwed\(th\);/);
  assert.match(UI, /return owed && !cmtInterrupted\.has\(th\.tid\);/,
    "the owed arm carries the T138 stop tombstone — an interrupted send owes nothing until the NEXT send");
  assert.match(UI, /if \(th\.status !== "open" \|\| !!th\.error \|\| threadStuck\(th\.state\)\) return false;/);
  // the push-count proxy is GONE root and branch
  assert.doesNotMatch(UI, /settledPushes|commentBusyLatch|latchBusy|SETTLE_CONFIRM_PUSHES/);
});

test("stuck-green regression: a stalled or missing later frame can never park the pulse", () => {
  // the old settle needed the 0→1→2 stepping to arrive; a parent dropping out of the pushed set (or
  // any withheld frame) left !confirmed true with nothing to clear it. The new clear is the reply
  // RECORD itself: the frame that shows the reply clears the latch in the same breath, and a thread
  // with no latch entry and an agent-tail msgs reads settled with NO further frames needed.
  const msg = (who: "you" | "agent") => ({ who, text: "x", t: 1 });
  assert.equal(replyOwed(th({ msgs: [msg("you"), msg("agent")] })), false,
    "the reply record alone reads settled — no confirmation pushes exist to stall");
  assert.doesNotMatch(UI, /settleConfirmed/);
});

// ── LEG C (the user 2026-08-24): the popover ignored the chat's display settings — thinking blocks
// and raw tool runs rendered regardless of the gear's compact option. The popover now renders the
// chat's OWN display units. Audit (setting → chat honors → popover before/after): compact/hide-
// thinking ✓chat / showed→hidden; compact/fold-tools ✓chat / raw cards→folded (shared expand keys);
// chatScheme ✓both already (body-class CSS, popover in scope); colormap/subgoals/collapsed/grouped
// (feed), judge toggles (timeline), backend/defaultDir (create), showBranch (statusline), tabCtx
// (tab strip) — not transcript-rendering settings, N/A both before and after. ───────────────────
test("the popover renders the chat's display units — thinking hidden, tool runs folded, per the gear", () => {
  const at = UI.indexOf("renderingIntoThread = true;");
  const block = UI.slice(at, at + 2800);   // widened past the T145 relay-note insert
  // 2026-09-08 (the notice-vocabulary pass): the retry-run fold became the generic noticegroup, fed the same
  // per-event foldability the chat computes (isFoldableNotice)
  assert.ok(block.includes("? compactDisplay(evs.map((e) => e.kind), evs.map((e) => e.kind === \"tool\" ? e.name : undefined), evs.map(isFoldableNotice))"),
    "the SAME unit builder the chat uses, gated on the SAME settings.compact");
  assert.ok(block.includes('const key = it.kind === "toolgroup" ? toolGroupKey(run[0]) : noticeGroupKey(run[0]);'),
    "the chat's group identities — tool runs AND notice runs — so expands survive refills");
  assert.ok(block.includes("? renderToolGroup(run as Extract<ChatEvent, { kind: \"tool\" }>[], prev, key, open)"),
    "the chat's own folded lines");
  assert.ok(block.includes('child.classList.add("tg-child");'), "expanded children wear the chat's classes");
});

test("executable, real thinking fixture: the unit stream drops thinking and folds the tool run", () => {
  // the exact shape the popover receives (a thread that thought, ran two tools, then replied)
  const kinds = ["user", "thinking", "tool", "tool", "assistant"];
  const units = compactDisplay(kinds, [undefined, undefined, "Read", "Edit", undefined]);
  assert.deepEqual(units, [
    { kind: "event", index: 0 },
    { kind: "toolgroup", indices: [2, 3] },
    { kind: "event", index: 4 },
  ], "no unit for the thinking block; the consecutive tools fold to one group");
});

test("everything that re-renders the chat's units refills the open popover live", () => {
  assert.match(UI, /function refillOpenCommentPop\(\): void \{/);
  assert.match(UI, /refillOpenCommentPop\(\);   \/\/ the popover renders the same units — its copy of this run must flip too/);
  assert.match(UI, /onExternalSettingsChange\(\(s\) => \{ settings = s; applyChatScheme\(s\); renderTabs\(\); updateStatusline\(\); rerenderAll\(\); refillOpenCommentPop\(\); \}\);/);
});

// ── T106 (the user 2026-08-26, found by the romp-lab loop's first full pass): three seam fixes ────
test("a create refused by parse lag holds its mark and retries on the frame event — never dropped", () => {
  // the kernel's typed nack: transient (the anchor record hasn't hit its parse yet) vs real
  const KERNELSRC = fs.readFileSync(path.resolve(process.cwd(), "..", "kernel", "kernel.py"), "utf8");
  assert.match(KERNELSRC, /ANCHOR_LAG_ERR = "that message isn't in the transcript yet; try again in a moment"/);
  assert.match(KERNELSRC, /"transient": err == ANCHOR_LAG_ERR,/);
  assert.match(KERNELSRC, /else:\s*\n\s*client\["send"\]\(json\.dumps\(\{"type": "warn", "text": err\}\)\)/,
    "no toast for plumbing the retry makes moot; real refusals stay loud");
  // …and the kernel PARKS the lag-refused create and retries it per pusher cycle (the file it is
  // waiting on is its own): a settled session emits no further frames, so the client-side re-post
  // alone starved — the park covers that; the client's frame-keyed belt covers a restart's lost park
  assert.match(KERNELSRC, /with _create_lock:\s*\n\s+if not any\(_parked_key\(pk\) == key for pk in _parked_creates\):\s*\n\s+_parked_creates\.append\(\{"sid": sid, "uuid": str\(msg\["uuid"\]\)/,
    "the park is under the create lock and once per key (upstream #1208; ruling S1 of the 2026-09-10 fold retired the fork's own park wrapper and its second lock)");
  assert.match(KERNELSRC, /def _retry_parked_creates\(\):/);
  assert.match(KERNELSRC, /_retry_parked_creates\(\)   # lag-parked comment creates ride every pusher cycle \(T106\)/);
  assert.match(KERNELSRC, /_PARK_MAX_TRIES = 30/);
  // the client holds the payload at send and re-posts when a session frame proves the parse caught up
  assert.match(UI, /cmtCreateInFlight\.set\(create\.uuid, held\);/);   // the held create is the stamped one the send posted
  assert.match(UI, /retryCmtCreates\(String\(msg\.id \|\| ""\)\);\s+\/\/ a session frame = the kernel re-parsed/);
  assert.match(UI, /const CMT_CREATE_MAX_TRIES = 12;/);
  // the ack retires the hold; a REAL refusal drops the synth honestly
  assert.match(UI, /if \(m\.uuid\) cmtCreateInFlight\.delete\(String\(m\.uuid\)\);\s+\/\/ the ack retires the retry hold/);
  assert.match(UI, /else \{ cmtCreateInFlight\.delete\(String\(m\.uuid\)\); dropSynthThread\(held\.sid, held\.uuid\); \}/);
  // (main mode keeps those lines as main had them.) Echo mode holds each create by its gesture's id
  assert.match(UI, /cmtEchoCreates\.set\(held\.createId, held\);/,
    "an echo-mode hold is the stamped create the send posted, keyed by its id (where the code lives; executed in comment-create-gesture-browser.test.ts: "
    + "'two creates on one message keep one retry hold each')");
  assert.match(UI, /retryEchoCreates\(sid\);/,
    "a session frame's retry covers the echo-mode holds too (where the code lives; executed in comment-create-gesture-browser.test.ts: "
    + "'two creates on one message keep one retry hold each')");
  assert.match(UI, /cmtEchoCreates\.delete\(held\.createId\);\s+\/\/ the ack retires the retry hold/,
    "an echo-mode ack retires the hold of the create it names (where the code lives; executed: 'an echo-mode ack settles the create it "
    + "answers alone: its hold, its own latch, and its note entry' below, and in comment-create-gesture-browser.test.ts 'the first "
    + "create's acknowledgment retires only its own hold and working mark')");
  assert.match(UI, /else \{ cmtEchoCreates\.delete\(held\.createId\); dropSynthThread\(held\.sid, held\.createId\); refusedCreateBack\(held\); \}/,
    "an echo-mode refusal drops its own hold and synth and hands the words back (where the code lives; executed in "
    + "comment-create-gesture-browser.test.ts: 'the first create's refusal leaves the second create's hold armed and its dialog waiting' "
    + "(the hold), 'a refused comment's own dialog comes back with its typed name, and its working mark goes at once' (the synthetic "
    + "thread and the words))");
});

test("the optimistic synth thread survives comments frames until superseded or failed", () => {
  // the frame used to WIPE it: every create's mark blinked between the gesture and the real
  // thread's first frame, and a lag-refused create erased the comment entirely
  assert.match(UI, /const synths = \(commentThreads\.get\(sid\) \|\| \[\]\)\.filter\(\(t\) =>\s*\n\s*t\.tid\.startsWith\("pending:"\) && cmtCreateInFlight\.has\(t\.tid\.slice\("pending:"\.length\)\)/);
  assert.match(UI, /&& !threads\.some\(\(r\) => r\.anchorUuid === t\.anchorUuid\)\);/,
    "a real thread on the same anchor supersedes the synth");
  // (main mode keeps those lines as main had them.) An echo-mode create's goes only with a real thread on its passage
  assert.match(UI, /t\.tid\.startsWith\("pending:"\) && cmtEchoCreates\.has\(t\.tid\.slice\("pending:"\.length\)\)\s*\n\s*&& !threads\.some\(\(r\) => r\.anchorUuid === t\.anchorUuid && frameExact\(r\.exact \|\| ""\) === frameExact\(t\.exact\)\)\)\);/,
    "a real thread on the same passage, compared on the comments frame's cut of it, supersedes an echo-mode synth, and another passage's "
    + "create on that message keeps its mark (where the code lives; executed in comment-create-gesture-browser.test.ts: 'the first create's "
    + "acknowledgment retires only its own hold and working mark' and 'a passage longer than the comments frame's cut has its working mark "
    + "replaced when its thread lands')");
});

test("the pending echo prunes against EVENTS too — a landed user turn never double-shows", () => {
  assert.match(UI, /const evUserMsgs = \(\(th\.events \|\| \[\]\) as ChatEvent\[\]\)/);
  assert.match(UI, /prunePending\(commentPending\.get\(th\.tid\) \|\| \[\], \[\.\.\.th\.msgs, \.\.\.evUserMsgs\]\);/);
});

test("the parity bundle (2026-08-26): dividers, owner-scoped in-turn controls, the sid stamp", () => {
  // day dividers open new days in the popover exactly as in the chat (same helper, same idiom)
  assert.match(UI, /const anchor = itemAnchor\(it, \(i\) => eventEpoch\(evs\[i\]\)\);\s*\n\s*const dayOpen = eventEpoch\(evs\[anchor\]\);[\s\S]{0,300}?if \(dayOpen != null\) \{\s*\n\s*const dv = dayDividerFor\(dayOpen, walk\);/);   // the T145 relay-note insert sits between; the unit timed by its anchor member, the divider decided against the walk's mark (T339)
  // the popover's list is stamped with the THREAD sid, and in-turn controls resolve their owner
  // from the DOM at click time — queued ✕ and the api-error card act on the thread, never the tab
  assert.match(UI, /list\.dataset\.session = th\.tid;/);
  assert.match(UI, /function owningSidOf\(el0: HTMLElement \| null\): string \| null \{/);
  assert.match(UI, /const sidQ = owningSidOf\(el\) \|\| activeId;/);   // resolved once — the optimistic arm reuses it
  assert.match(UI, /\{ type: "cancelQueued", id: sidQ, md: qmd \}/);
  assert.match(UI, /const own = owningSidOf\(b\);\s*\n\s*if \(vscodeApi\) vscodeApi\.postMessage\(\{ type: "apiRetry", id: own, manual: true \}\);/);   // the api-error card's delegate handler (2026-09-08), still owner-scoped
});

test("the thread's running turn offers the chat's stop affordance, owner-scoped to the THREAD (T138)", () => {
  // the user 2026-08-27: threads couldn't be interrupted from the UI at all — diagnosis (a), the
  // affordance was simply absent from the popover statusline (the chat's stopButton never had a
  // popover twin). The fix rides the stable body delegate (this statusline rebuilds per comments
  // frame — press-safety) and pins the target to the thread's own session, never the active tab.
  const at = UI.indexOf("function cmtStateChip(");
  const chip = UI.slice(at, UI.indexOf("\n}", at));
  assert.match(chip, /b\.dataset\.act = "cmtinterrupt";/);
  assert.match(chip, /b\.dataset\.sid = th\.tid;/, "the thread's OWN sid rides the button");
  assert.match(chip, /wrap\.append\(chip, timer, stopBtn\(\)\);/, "working offers it");
  assert.match(chip, /wrap\.append\(chip, stopBtn\(\)\);/, "retrying offers it");
});

test("the popover interrupt posts the THREAD sid, clears the send-latch on the gesture, and acks instantly", () => {
  const at = UI.indexOf("cmtinterrupt: (elx) => {");
  assert.ok(at > 0, "the delegated handler exists (a direct listener would die in the per-frame rebuild)");
  const body = UI.slice(at, UI.indexOf("},", at));
  assert.match(body, /const sid = \(elx as HTMLElement\)\.dataset\.sid;/);
  assert.match(body, /vscodeApi\.postMessage\(\{ type: "interrupt", id: sid \}\);/);
  assert.ok(!body.includes("activeId"), "never the active tab — the owner-scoping class queued-x/Retry were fixed for");
  // T102's latch contract at the interrupt edge: the exchange ends with NO reply record coming, so
  // the pulse clears on the gesture itself — the deciding event — not on a reply that never lands.
  assert.match(body, /cmtAwaitBase\.delete\(sid\);/);
  // …and the OWED arm stands down too (lab phase 4e caught it: replyOwed's trailing-user shape held
  // the mark green forever after a stop). The tombstone is record-count-keyed, never a clock, and a
  // fresh send retires it (re-owed).
  assert.match(body, /cmtInterrupted\.add\(sid\);/);
  assert.match(UI, /return owed && !cmtInterrupted\.has\(th\.tid\);/,   // owed = the kernel's replyOwed, else the msgs read (T237)
    "gesture-pair tombstone: stop sets it, ONLY the next send clears it — the CLI files the interrupt "
    + "as a trailing user-kind record, so any record-shape re-derivation would re-fire (lab-caught)");
  assert.match(UI, /cmtInterrupted\.delete\(cur\.th\.tid\);/);
  assert.match(body, /chip chip-interrupting/, "instant acknowledgment: the chip flips before any kernel round-trip");
});

test("a contentless open thread NEVER renders blank — the loader stays past the backstop (T152)", () => {
  // the live specimen: a fork of a 40MB parent took 200+s to spend across kernel restarts; the 8s
  // boot backstop expired and the popover showed the quote floating over an empty list. The
  // backstop now swaps the loader's LABEL (an honest 'taking longer'), never to blank; error and
  // stuck branches still take over on the frame that says so.
  const at = UI.indexOf('if (!evs.length && !th.msgs.length && th.status === "open" && !th.error) {');
  assert.ok(at > 0, "the never-blank guard exists, gated on BOTH projections being empty");
  const body = UI.slice(at, UI.indexOf("return;", at));
  assert.match(body, /const slow = !cmtBootHolds\(th\.tid\);/);
  assert.match(body, /still opening — the thread's session is taking longer than usual…/);
  assert.match(body, /opening the thread…/);
});

// ── the create's identity: one id per send gesture, the same one on every re-post ─────────────────
// The kernel remembers each create it completed and answers a repeat of it with the same thread's ack.
// Keyed on the words (anchor, passage, text) that memo also swallowed a DELIBERATE second comment in the
// same words on the same passage (review, 2026-09-09). The client stamps the gesture instead: the popover
// mints a createId at the send and every re-post of that gesture carries it, so a repeat is a frame with
// an id the kernel has seen and a fresh gesture never is.
const ANCHOR = { sid: "aaaaaaaa-1111-2222-3333-444444444444", uuid: "a1", exact: "exponential backoff",
                 model: "", effort: "", fast: "", color: "" };

test("a send gesture mints its own create id; a second gesture in the same words on the same passage gets another", () => {
  const first = newCommentCreate(ANCHOR, "fix this", "");
  const second = newCommentCreate(ANCHOR, "fix this", "");
  assert.ok(first.createId.length > 0, "the gesture is stamped");
  assert.notEqual(first.createId, second.createId, "two gestures, two ids, whatever their words");
  assert.equal(first.tries, 0, "the retry count starts at the send");
});

test("the create frame carries the id, and a re-post of the held create is the same frame", () => {
  const held = newCommentCreate({ ...ANCHOR, model: "claude-opus-5", effort: "high", fast: "on", color: "#112233" },
                                "why jitter?", "why-jitter");
  const sent = commentCreateFrame(held);
  assert.deepEqual(sent, { type: "commentCreate", id: ANCHOR.sid, uuid: "a1", exact: "exponential backoff",
                           text: "why jitter?", name: "why-jitter", model: "claude-opus-5", effort: "high",
                           fast: "on", color: "#112233", createId: held.createId });
  held.tries++;                                                   // a transient nack armed the retry
  assert.deepEqual(commentCreateFrame(held), sent, "a retry is the same gesture: the same id, the same words");
});

test("an anchor with no picks sends empty picks and an empty name for the kernel's default", () => {
  const held = newCommentCreate({ sid: ANCHOR.sid, uuid: "a1", exact: "exponential backoff" }, "fix this", "");
  const sent = commentCreateFrame(held);
  assert.equal(sent.name, "");
  assert.equal(sent.model, ""); assert.equal(sent.effort, ""); assert.equal(sent.fast, ""); assert.equal(sent.color, "");
});

test("the popover's send and its frame-keyed retry both post the held create's frame, its id included, in either mode", () => {
  const send = UI.slice(UI.indexOf("function commentSendFromPop("));
  const sendBody = send.slice(0, send.indexOf("\nfunction ", 10));
  assert.match(sendBody, /const held = newCommentCreate\(create, text, nm\)/, "the send mints the gesture's id");
  // main mode: main's send, main's frame whole
  assert.match(sendBody, /vscodeApi\.postMessage\(commentCreateFrame\(held\)\)/,
    "a main-mode send posts main's frame, its id included (where the code lives; executed in comment-create-gesture-browser.test.ts: "
    + "'main mode: a comment's frame is main's, whole, its picks and a createId minted at the send and re-posted unchanged, as the base "
    + "posted it')");
  assert.match(sendBody, /cmtCreateInFlight\.set\(create\.uuid, held\)/, "the hold IS the stamped create");
  const retry = UI.slice(UI.indexOf("function retryCmtCreates("));
  const retryBody = retry.slice(0, retry.indexOf("\nfunction ", 10));
  assert.match(retryBody, /vscodeApi\?\.postMessage\(commentCreateFrame\(c\)\)/,
    "main's retry re-sends main's frame, the same id (where the code lives; executed below, 'main's frame-keyed retry re-posts the "
    + "held create's own frame, its id included, and runs the echo-mode retry for the session too', and by the browser test named above)");
  // echo mode: the create's own frame, its id included, from the send and from the retry
  const echoSend = UI.slice(UI.indexOf("function sendEchoCreate("));
  const echoBody = echoSend.slice(0, echoSend.indexOf("\nfunction ", 10));
  assert.match(echoBody, /vscodeApi\.postMessage\(commentCreateFrame\(held\)\)/,
    "an echo-mode send posts the held create's frame, its id included (where the code lives; executed in comment-create-gesture-browser.test.ts "
    + "by firstCreate's precondition, the posted create's id, in every echo-mode test that sends)");
  const echoRetry = UI.slice(UI.indexOf("function retryEchoCreates("));
  const echoRetryBody = echoRetry.slice(0, echoRetry.indexOf("\nfunction ", 10));
  assert.match(echoRetryBody, /vscodeApi\?\.postMessage\(commentCreateFrame\(c\)\)/,
    "the echo-mode retry re-sends the held frame, id included (where the code lives; executed below, 'the echo-mode frame-keyed retry re-posts "
    + "the held create's own frame: the id minted at the send, on every re-post')");
  assert.doesNotMatch(UI, /type: "commentCreate", id:/, "no hand-built create frame remains");
});

// ── an answer's route, and the echo-mode create it settles (the same-message create collision) ───────────────────────
// Two comments on one message share its uuid. An echo-mode dialog holds its create by the id its gesture minted, and a
// kernel that announces the echo sends that id back in every answer, so an answer settles the create it names. The page
// keeps every id it minted in echo mode for its life; any other answer goes to main's handling (render.ts). The page's
// other half (the dialog each answer adopts into, the words a refusal hands back) is driven in
// comment-create-gesture-browser.test.ts.

test("an answer goes to the echo-mode code only when its createId is one this page minted in echo mode: any other goes to main's handling", () => {
  const minted = new Set(["k2own0create", "k2settled0before"]);
  assert.equal(echoAnswer({ createId: "k2own0create" }, minted), true, "an id this page minted in echo mode");
  assert.equal(echoAnswer({ createId: "k2settled0before" }, minted), true, "one whose create it settled or gave up on too: a late answer is echo mode's");
  assert.equal(echoAnswer({ createId: "k2main0mode" }, minted), false, "a main-mode create's own id: main's frame carries it, and main's handling answers it");
  assert.equal(echoAnswer({ createId: "k2another0viewer" }, minted), false, "another page's: main saw it, so main's handling sees it");
  assert.equal(echoAnswer({}, minted), false, "the key absent: a kernel without the echo");
  assert.equal(echoAnswer({ createId: "" }, minted), false, "an empty id: a kernel with the echo answering an older page's unstamped create");
  assert.equal(echoAnswer({ createId: 7 }, new Set(["7"])), false, "and a key that holds no string");
  assert.match(UI, /else if \(\(m\.type === "commentCreateFailed" && m\.id && m\.uuid \|\| m\.type === "commentCreated" && m\.id && m\.tid\) && echoAnswer\(m, cmtEchoMinted\)\) \{/,
    "the page routes both answers by it, ahead of main's handling (where the code lives; executed in comment-create-gesture-browser.test.ts: "
    + "'the fail-safe: an answer without the key ahead of the connection's connect push hands back the comment still out, sent before the "
    + "push or between the open and the push, local or relayed, with its dialog open or closed, and the page posts nothing more' "
    + "and 'an answer naming no create this page minted in echo mode goes to main's handling, which settles a main-mode comment as the base "
    + "did, and one naming an echo-mode comment never touches main-mode state')");
});

test("a host's evidence of the echo is its latest connection's connect push, caps frame or answer: a createId key shows the echo, its absence shows none, and federation's relayDrop shows nothing", () => {
  assert.equal(capsAnnounceEcho(["tagEdit", "chatProto2", CREATE_ID_ECHO_CAP]), true);
  assert.equal(capsAnnounceEcho(["tagEdit", "chatProto2"]), false, "caps without the cap: no echo");
  assert.equal(capsAnnounceEcho(null), false);
  assert.equal(answerEchoEvidence({ createId: "k2x" }), true, "an answer carrying the key: a kernel with the echo");
  assert.equal(answerEchoEvidence({ createId: "" }), true, "even empty: only a kernel with the echo sends the key");
  assert.equal(answerEchoEvidence({}), false, "the key absent: a kernel without the echo");
  assert.equal(answerEchoEvidence({ createId: "k2x", relayDrop: true }), null, "the page's own answer to a dropped create is no evidence from the host");
  const ev = new Map<string, boolean>([["", true], ["TESTHOST2", false]]);
  assert.equal(hostEchoMode(ev, ANCHOR.sid), true, "a local session: the local kernel's evidence");
  assert.equal(hostEchoMode(ev, "TESTHOST2:" + ANCHOR.sid), false, "a remote session: its own host's evidence, never the local kernel's");
  assert.equal(hostEchoMode(ev, "TESTHOST3:" + ANCHOR.sid), false, "a host with no evidence yet: main mode");
  assert.equal(hostEchoMode(new Map(), ANCHOR.sid), false, "nor has the local kernel, before its first connect push, caps frame or answer");
  assert.match(UI, /if \(m\.type === "commentCreated" \|\| m\.type === "commentCreateFailed"\) echoSideOfAnswer\(m\);/,
    "every create answer is evidence from its host, and one without the key hands back the echo-mode creates out on it before main's "
    + "handling takes it (where the code lives; executed in comment-create-gesture-browser.test.ts: 'the fail-safe: an answer without the "
    + "key ahead of the connection's connect push hands back the comment still out, sent before the push or between the open and the push, "
    + "local or relayed, with its dialog open or closed, and the page posts nothing more', and 'a kernel upgraded under the page is known "
    + "by its connection's connect push carrying the marker, or by an answer carrying the key before that push: the next comment is echo "
    + "mode')");
});

test("an echo-mode answer settles the create its id names, and no other create on that message", () => {
  const first = newCommentCreate(ANCHOR, "Why jitter at all?", "");
  const second = newCommentCreate({ ...ANCHOR, exact: "a jitter of ten percent" }, "And the cap?", "");
  const holds = new Map([[first.createId, first], [second.createId, second]]);
  assert.equal(heldCreateFor(holds, { id: ANCHOR.sid, uuid: "a1", createId: second.createId }), second,
               "the second comment's answer settles the second comment, whichever was sent first");
  assert.equal(heldCreateFor(holds, { id: ANCHOR.sid, uuid: "a1", createId: first.createId }), first);
  assert.equal(heldCreateFor(holds, { id: ANCHOR.sid, uuid: "a1", createId: "k2another0viewer" }), null,
               "an id this viewer holds no create for settles nothing: the pusher acks a parked create to every chat client");
  assert.equal(heldCreateFor(holds, { id: ANCHOR.sid, uuid: "a1", createId: "" }), null,
               "an empty id is no echo-mode create's, even with two held on the message");
  assert.equal(heldCreateFor(new Map([[first.createId, first]]), { id: ANCHOR.sid, uuid: "a1" }), null,
               "nor is an answer with the key absent, even with one held: it names none");
});

test("a synthetic thread is compared with a real one on the comments frame's own cut of the passage, the kernel's number", () => {
  const cut = /"exact": str\(th\.get\("exact"\) or ""\)\[:(\d+)\]/.exec(fs.readFileSync(path.resolve(process.cwd(), "..", "kernel", "kernel.py"), "utf8"));
  assert.ok(cut, "the comments frame's cut of a thread's passage is found in kernel.py");
  assert.equal(FRAME_EXACT_CUT, Number(cut[1]), "the page cuts where the kernel's frame cuts");
  const long = "a".repeat(700);
  assert.equal(frameExact(long), "a".repeat(FRAME_EXACT_CUT));
  assert.equal(frameExact("short passage"), "short passage", "a passage within the cut is itself");
  const astral = "\u{1F600}".repeat(FRAME_EXACT_CUT + 1);
  assert.equal(Array.from(frameExact(astral)).length, FRAME_EXACT_CUT, "counted in code points, as Python slices a str");
  assert.equal(frameExact(frameExact(long)), frameExact(long), "the frame's already-cut passage is its own cut");
});

test("a create dialog's drafts are its passage's: two passages of one message are two drafts, and its name has its own", () => {
  const here = { uuid: "a1", exact: "exponential backoff" }, there = { uuid: "a1", exact: "a jitter of ten percent" };
  assert.notEqual(createDraftKey(here), createDraftKey(there), "two passages of one message, two drafts");
  assert.notEqual(createNameKey(here), createNameKey(there), "and two typed names");
  assert.equal(createDraftKey(here), createDraftKey({ ...here }), "the same passage, the same draft");
  assert.notEqual(createDraftKey(here), createNameKey(here), "the words and the typed name are two drafts");
  assert.ok(createDraftKey(here).startsWith("new:") && createNameKey(here).startsWith("newname:"),
            "the prefixes the comments frame's draft prune keeps (render.ts)");
  assert.ok(createNameKey(here).includes("\n") && !("newname:" + here.uuid).includes("\n"),
            "an echo-mode typed name's key holds a newline, main's (the message's) none: the prune keeps the one and prunes the other as main did");
});

test("a refused comment's toast names its passage on one line, bounded, in quote marks, and says how to reach its words", () => {
  assert.equal(refusedCreateToast("exponential backoff"),
               "Your comment on “exponential backoff” was not saved. Its words are kept: select text anywhere in that message, right-click it and choose Comment to see them.");
  // a comment the page gave up on that the kernel saved after all, the words handed back to its box changed since
  assert.equal(savedAfterAllToast("exponential backoff"),
               "Your comment on “exponential backoff” was saved after all. What you typed in its box since is still there.");
  const long = "Use exponential backoff\nwith a jitter of ten percent, capped at two minutes, and retry the idempotent calls only.";
  const label = passageLabel(long);
  assert.equal(label.length, 74, "72 characters inside the quote marks");
  assert.ok(label.startsWith("“Use exponential backoff with a jitter") && label.endsWith("…”"), label);
  assert.match(UI, /document\.getElementById\("content"\)\?\.addEventListener\("contextmenu", showSelectionMenu\);/,
    "the Comment item is in the selection's context menu, which a right-click opens (a source pin only, of the route the toast describes)");
});

test("an echo-mode dialog whose own draft is empty takes main's draft of the message and moves it, the words and the typed name together", () => {
  const a = { uuid: "a1", exact: "exponential backoff" };
  const d = new Map([["new:a1", "typed under main"], ["newname:a1", "main-name"]]);
  assert.deepEqual(carryMainDraft(d, a), { text: "typed under main", name: "main-name" }, "it says what it moved (render.ts records it after main's give-up)");
  assert.deepEqual([...d.entries()].sort(), [[createDraftKey(a), "typed under main"], [createNameKey(a), "main-name"]].sort(),
                   "an echo-mode dialog takes main's draft of the message, and main's is spent");
  const own = new Map([[createDraftKey(a), "its own"], ["new:a1", "main's"], ["newname:a1", "main-name"]]);
  assert.equal(carryMainDraft(own, a), null, "and null when it moves nothing");
  assert.deepEqual([...own.entries()].sort(), [[createDraftKey(a), "its own"], ["new:a1", "main's"], ["newname:a1", "main-name"]].sort(),
                   "a passage with words of its own takes nothing: main's words and main's typed name wait together, so the name never rides the passage's words");
  const ownName = new Map([[createNameKey(a), "its-name"], ["new:a1", "main's"], ["newname:a1", "main-name"]]);
  carryMainDraft(ownName, a);
  assert.deepEqual([...ownName.entries()].sort(), [[createNameKey(a), "its-name"], ["new:a1", "main's"], ["newname:a1", "main-name"]].sort(),
                   "nor does one with a typed name of its own: main's words would ride it, and main's name would be left alone");
  const nameOnly = new Map([["newname:a1", "main-name"]]);
  assert.deepEqual(carryMainDraft(nameOnly, a), { text: "", name: "main-name" });
  assert.deepEqual([...nameOnly.entries()], [[createNameKey(a), "main-name"]], "a typed name main holds with no words moves too");
  assert.match(UI, /if \(echo && !cmtCreateInFlight\.has\(uuid\)\) \{\n    const moved = carryMainDraft\(commentDrafts, \{ uuid, exact \}\);\n    noteMainBrought\(pendingCommentAnchor, moved\);\n  \}/,
    "an echo-mode dialog runs it as it opens, except while that message's main-mode create is out, and a main-mode dialog never does, "
    + "and what it moved is recorded for the late landing of a comment main's retry gave up on, and of a handed-back comment whose "
    + "words the person brought back into main's draft (where the code lives; executed in "
    + "comment-create-gesture-browser.test.ts: the move by 'words typed in a main-mode dialog come into an echo-mode dialog on their "
    + "passage once the kernel announces the echo, and leave main's draft', the exception by 'an echo-mode dialog on a message whose "
    + "main-mode comment is still out shows that comment's words in its note, not saved yet, until main's handling settles it', the "
    + "other direction's note by 'words typed in an echo-mode dialog wait in a main-mode dialog's note on their passage, and main's "
    + "handling never drops them until the person brings them back', and the record by 'a main-mode comment the page gave up on, its "
    + "words carried into an echo-mode dialog opened after the give-up, is cleared from that box by its late acknowledgment when "
    + "unchanged, and kept with a toast when changed', and the handed-back comment's record by 'the fail-safe: a later "
    + "acknowledgment naming a handed-back comment whose words were brought back into a main-mode box, then moved from main's draft "
    + "into an echo-mode dialog on another passage of the message once the kernel shows the echo again, by the carry as it opens or by "
    + "its Bring it back, clears them from that box when unchanged, the dialog adopting its thread, keeps them with a toast when "
    + "changed, and clears them from that passage's draft when the dialog was closed')");
});

// ── executed: the frame-keyed retries (retryCmtCreates, main's, and retryEchoCreates, lifted from render.ts) ────────
function liftFn(name: string): string {
  const start = UI.indexOf("function " + name + "(sid: string): void {");
  assert.ok(start > 0, "the frame-keyed retry lives in " + name);
  return UI.slice(start, UI.indexOf("\n}\n", start) + 3).replace("(sid: string): void {", "(sid) {");
}
function liftRetry(held: CommentCreate[], name: "retryCmtCreates" | "retryEchoCreates",
                   connPush: Map<string, boolean | "down"> = new Map([["", true]]), sockIsOpen = true) {
  const src = liftFn(name);
  const boundM = /const CMT_CREATE_MAX_TRIES = (\d+);/.exec(UI);
  assert.ok(boundM, "the attempt bound is a named constant");
  const bound = Number(boundM[1]);
  const posted: Record<string, unknown>[] = [];
  const dropped: string[] = [];
  const toasts: string[] = [];
  const back: string[] = [];
  const echoRuns: string[] = [];
  const givenUp = new Map<string, CommentCreate>();
  const paints: number[] = [];
  const prelude = `
    const CMT_CREATE_MAX_TRIES = ${bound};
    const cmtMainGivenUp = mainGivenUp;
    const vscodeApi = { postMessage: (m) => posted.push(m) };
    const dropSynthThread = (sid, k) => dropped.push(k);
    const refusedCreateBack = (c) => back.push(c.createId);${name === "retryCmtCreates" ? "\n    const retryEchoCreates = (sid) => echoRuns.push(sid);" : ""}
    const cmtConnPush = connPush;
    const sockOpen = () => sockIsOpen;
    const paintOpenNote = () => paints.push(1);
    const warnToast = (t) => toasts.push(t);`;
  // main's holds are keyed by the message's uuid, echo mode's by the create id
  const holds = new Map(held.map((c) => [name === "retryCmtCreates" ? c.uuid : c.createId, c] as [string, CommentCreate]));
  const mainGivenUp = new Map<string, CommentCreate>();
  const fn = new Function(name === "retryCmtCreates" ? "cmtCreateInFlight" : "cmtEchoCreates", "cmtEchoGivenUp", "mainGivenUp", "commentCreateFrame",
                          "posted", "dropped", "toasts", "back", "echoRuns", "paints", "connPush", "hostOf", "sockIsOpen", "sid",
                          prelude + "\n" + src + "\n" + name + "(sid);");
  return { run: (sid: string) => { fn(holds, givenUp, mainGivenUp, commentCreateFrame, posted, dropped, toasts, back, echoRuns, paints, connPush, hostOf, sockIsOpen, sid); },
           posted, dropped, toasts, back, echoRuns, givenUp, mainGivenUp, paints, bound };
}

test("main's frame-keyed retry re-posts the held create's own frame, its id included, and runs the echo-mode retry for the session too", () => {
  const held = newCommentCreate(ANCHOR, "fix this", "fix-this");
  held.tries = 1;                                                 // the transient nack armed the retry
  const other = newCommentCreate({ ...ANCHOR, sid: "bbbbbbbb-1111-2222-3333-444444444444", uuid: "b1" }, "and here", "");
  other.tries = 1;
  const { run, posted, dropped, toasts, echoRuns } = liftRetry([held, other], "retryCmtCreates");
  run(ANCHOR.sid); run(ANCHOR.sid);                               // two session frames for the sid: two re-posts
  assert.deepEqual(posted, [commentCreateFrame(held), commentCreateFrame(held)], "main's frame, whole, the same id each time, for this sid's create alone");
  assert.equal(held.tries, 3);
  assert.equal(other.tries, 1, "another session's create waits for its own frame");
  assert.deepEqual([dropped, toasts, echoRuns], [[], [], [ANCHOR.sid, ANCHOR.sid]], "and each frame runs the echo-mode retry for its session");
});

test("the echo-mode frame-keyed retry re-posts the held create's own frame: the id minted at the send, on every re-post", () => {
  const held = newCommentCreate(ANCHOR, "fix this", "fix-this");
  const stamped = held.createId;
  held.tries = 1;
  const other = newCommentCreate({ ...ANCHOR, sid: "bbbbbbbb-1111-2222-3333-444444444444", uuid: "b1" }, "and here", "");
  other.tries = 1;
  const { run, posted, dropped, toasts } = liftRetry([held, other], "retryEchoCreates");
  run(ANCHOR.sid); run(ANCHOR.sid);
  assert.equal(posted.length, 2, "one re-post per frame, for this sid's create alone");
  assert.deepEqual(posted.map((f) => f.createId), [stamped, stamped],
                   "a re-post is the same gesture: the kernel answers it with the thread it made, never a twin");
  assert.deepEqual(posted, [commentCreateFrame(held), commentCreateFrame(held)], "the held frame, whole, each time");
  assert.equal(held.tries, 3);
  assert.equal(other.tries, 1, "another session's create waits for its own frame");
  assert.deepEqual([dropped, toasts], [[], []]);
});

test("the echo-mode frame-keyed retry posts nothing again on a host whose connection's connect push has not shown the echo (before it comes, without the marker, or on the page's own socket from its drop), nor on the page's own socket while it is not open", () => {
  for (const [state, why] of [[undefined, "the connection open and its connect push still to come"], [false, "a connect push without the marker"],
                               ["down", "the page's own socket down since its drop"]] as [boolean | "down" | undefined, string][]) {
    const held = newCommentCreate(ANCHOR, "fix this", "fix-this");
    held.tries = 1;                                                 // a transient nack armed it
    const spent = newCommentCreate({ ...ANCHOR, uuid: "a2" }, "and this", "");
    const connPush = new Map<string, boolean | "down">(state === undefined ? [] : [["", state]]);
    const lift = liftRetry([held, spent], "retryEchoCreates", connPush);
    spent.tries = lift.bound + 1;
    lift.run(ANCHOR.sid);
    assert.deepEqual([lift.posted, lift.toasts, held.tries, lift.paints.length], [[], [], 1, 1],
                     why + ": nothing is posted again, no attempt is counted and none is given up (a give-up comes only with a re-post); the note is still repainted for main's retry just run");
  }
  const remote = newCommentCreate({ ...ANCHOR, sid: "TESTHOST2:" + ANCHOR.sid }, "over there", "");
  remote.tries = 1;
  const lift = liftRetry([remote], "retryEchoCreates", new Map<string, boolean | "down">([["", true], ["TESTHOST2", false]]));
  lift.run(remote.sid);
  assert.deepEqual(lift.posted, [], "a host's own connection is read, never the page's own socket's: that host's connect push lacked the marker");
  const lift2 = liftRetry([remote], "retryEchoCreates", new Map<string, boolean | "down">([["", false], ["TESTHOST2", true]]));
  lift2.run(remote.sid);
  assert.deepEqual(lift2.posted, [commentCreateFrame(remote)], "and a host whose connect push carried it is retried whatever the page's own socket showed");
  // the page's own socket CLOSING (its netState still up, its connection's push read and marked): a post would wait in the
  // shim's queue and go out first on the next socket, whose kernel may lack the echo
  const local = newCommentCreate(ANCHOR, "fix this", "fix-this");
  local.tries = 1;
  const closing = liftRetry([local], "retryEchoCreates", new Map<string, boolean | "down">([["", true]]), false);
  closing.run(ANCHOR.sid);
  assert.deepEqual([closing.posted, local.tries, closing.paints.length], [[], 1, 1],
                   "the page's own socket not open: nothing is posted again and no attempt is counted, the note still repainted");
  const relayed = liftRetry([remote], "retryEchoCreates", new Map<string, boolean | "down">([["TESTHOST2", true]]), false);
  relayed.run(remote.sid);
  assert.deepEqual(relayed.posted, [commentCreateFrame(remote)],
                   "and a relay's retry does not read the page's own socket: federation sends on an open relay and drops on one that is not");
});

test("a create the send has not heard back on is not re-posted, and one past the attempt bound is dropped with the toast, in either mode", () => {
  for (const name of ["retryCmtCreates", "retryEchoCreates"] as const) {
    const fresh = newCommentCreate(ANCHOR, "fix this", "");           // tries 0: the send's own frame is out
    const spent = newCommentCreate({ ...ANCHOR, uuid: "a2" }, "and this", "");
    const lift = liftRetry([fresh, spent], name);
    spent.tries = lift.bound + 1;
    lift.run(ANCHOR.sid);
    assert.deepEqual(lift.posted, [], name + ": the retry waits for a transient nack, and gives up past the bound");
    assert.equal(lift.toasts.length, 1);
    if (name === "retryCmtCreates") {
      assert.deepEqual([lift.dropped, lift.back], [["a2"], []], "main's give-up drops the create's synth by its message's uuid; its words stay in main's draft");
      assert.deepEqual([...lift.mainGivenUp.keys()], [spent.createId],
                       "and the page keeps it as given up, so a late landing of it in an echo-mode box its words were brought back into still settles it there");
    } else {
      assert.deepEqual(lift.dropped, [spent.createId], "the echo-mode give-up drops the create's own synth, by its id");
      assert.deepEqual(lift.back, [spent.createId], "and its words go back to their passage");
      assert.deepEqual([...lift.givenUp.keys()], [spent.createId], "and the page keeps it as given up, so a late landing still settles it");
      assert.match(lift.toasts[0], /^[\x20-\x7e]+$/, "its toast is plain text, with none of the dashes main's toast has");
    }
  }
});

// ── executed: a connection's connect push, read per host, and the re-post it makes when marked (noteConnectPush and ───
// ── repostHeldCreates, lifted) ─────────────────────────────────────────────────────────────────────────────────────────
function liftBody(sig: string, js: string): string {
  const start = UI.indexOf("function " + sig);
  assert.ok(start > 0, "render.ts has function " + sig);
  return UI.slice(start, UI.indexOf("\n}\n", start) + 3).replace(sig, js);
}
test("a marked connection's connect push posts again every echo-mode create still held on its host, whatever its tries, and only that host's; on the page's own socket, nothing while that socket is not open", () => {
  const src = liftBody("repostHeldCreates(host: string): void {", "repostHeldCreates(host) {");
  const fresh = newCommentCreate(ANCHOR, "fix this", "fix-this");   // tries 0: the answer it was owed went with the socket
  const armed = newCommentCreate({ ...ANCHOR, uuid: "a2" }, "and this", "");
  armed.tries = 5;                                                  // a transient nack armed the frame-keyed retry
  const remote = newCommentCreate({ ...ANCHOR, sid: "TESTHOST2:" + ANCHOR.sid }, "over there", "");
  const echoHolds = new Map([fresh, armed, remote].map((c) => [c.createId, c] as [string, CommentCreate]));
  const mainHold = newCommentCreate({ ...ANCHOR, uuid: "a3" }, "main's", "");
  const mainHolds = new Map([[mainHold.uuid, mainHold]]);
  const run = (host: string, open = true) => {
    const posted: unknown[] = [];
    new Function("cmtEchoCreates", "cmtCreateInFlight", "sockOpen", "hostOf", "commentCreateFrame", "vscodeApi", "host", src + "\nrepostHeldCreates(host);")(
      echoHolds, mainHolds, () => open, hostOf, commentCreateFrame, { postMessage: (m: unknown) => posted.push(m) }, host);
    return posted;
  };
  assert.deepEqual(run(""), [commentCreateFrame(fresh), commentCreateFrame(armed)],
                   "the page's own socket: every local echo-mode create's own frame, its id included, whatever its tries, and no main-mode one");
  assert.deepEqual(run("TESTHOST2"), [commentCreateFrame(remote)], "a host's relay: that host's creates alone");
  assert.deepEqual(run("", false), [],
                   "the page's own socket CLOSING as its marked push is handed on posts nothing: the shim would send the posts first on the next "
                   + "socket, whose kernel may lack the echo, and the next connection's connect push decides instead");
  assert.deepEqual(run("TESTHOST2", false), [commentCreateFrame(remote)], "a relay's re-post does not read the page's own socket");
  assert.deepEqual(run("TESTHOST3"), [], "and none for a host that holds no create");
  assert.deepEqual([fresh.tries, armed.tries, remote.tries], [0, 5, 0], "a re-post is not an attempt: the lag retry's bound is untouched");
  assert.equal(echoHolds.size + mainHolds.size, 4, "and it settles nothing: each create's own answer does");
});

test("each connection's connect push is read once, per host: marked, it shows the echo and posts the host's held comments again; unmarked, it shows none, which hands them back, and posts nothing", () => {
  const src = liftBody("noteConnectPush(m: { reemit?: unknown; freshHost?: unknown; createIdEcho?: unknown }): void {", "noteConnectPush(m) {")
    .replace("(window as any).__rompLocalUp", "window.__rompLocalUp");          // the one TypeScript-only mark in it
  const conn = new Map<string, boolean | "down">();
  const calls: string[] = [];
  const win: Record<string, unknown> = {};
  let flipGen: number | null = 0;                                    // the last socket-flip frame's generation (cmtFlipGen)
  const push = (m: Record<string, unknown>) => new Function("cmtConnPush", "noteHostEcho", "repostHeldCreates", "window", "cmtFlipGen", "m", src + "\nnoteConnectPush(m);")(
    conn, (h: string, e: boolean) => calls.push("evidence " + JSON.stringify(h) + " " + e), (h: string) => calls.push("repost " + JSON.stringify(h)), win, flipGen, m);
  push({ type: "tabOrder", order: [], createIdEcho: true });
  assert.deepEqual(calls.splice(0), ['evidence "" true', 'repost ""'],
                   "a bare strip (a page with no federation) is the local kernel's: its marker is the host's evidence of the echo, and the held comments are posted again");
  push({ type: "tabOrder", order: [], createIdEcho: true });
  assert.deepEqual(calls.splice(0), [], "a later strip on the same connection reads nothing: the connection's push was read");
  push({ type: "tabOrder", order: [], freshHost: "TESTHOST2" });
  assert.deepEqual(calls.splice(0), ['evidence "TESTHOST2" false'],
                   "a merged strip is the host's that drove it: a relay's connect push without the marker shows that host has no echo (noteHostEcho "
                   + "hands its echo-mode comments back) and posts nothing again");
  push({ type: "tabOrder", order: [], reemit: true, createIdEcho: true });
  assert.deepEqual(calls.splice(0), [], "federation's re-emit is no host's push");
  assert.deepEqual([...conn.entries()], [["", true], ["TESTHOST2", false]], "each host's connection holds its own reading");
  conn.delete("TESTHOST2");                                          // that host's relay opened again (romp:hostRelayUp)
  push({ type: "tabOrder", order: [], freshHost: "TESTHOST2", createIdEcho: true });
  assert.deepEqual(calls.splice(0), ['evidence "TESTHOST2" true', 'repost "TESTHOST2"'], "and its next connection's push is read afresh");
  conn.set("", "down");                                              // the page's own socket dropped after its push was read
  push({ type: "tabOrder", order: [], createIdEcho: true });
  assert.deepEqual(calls.splice(0), [], "a strip still draining from the dropped socket is that socket's");
  conn.delete("");                                                   // the shim's socket-flip frame: the next connection
  win.__rompLocalUp = false;
  push({ type: "tabOrder", order: [], createIdEcho: true });
  assert.deepEqual(calls.splice(0), [], "and one delivered while the page's own socket is down (the shim's netState) belongs to the socket that dropped");
  win.__rompLocalUp = true;
  push({ type: "tabOrder", order: [] });
  assert.deepEqual(calls.splice(0), ['evidence "" false'], "the next socket's own push is read: a kernel from before the echo, no re-post");
  conn.delete(""); flipGen = null;                                   // a socket-flip frame that carried no generation, or a page whose shim published none
  push({ type: "tabOrder", order: [], createIdEcho: true });
  assert.deepEqual(calls.splice(0), ['evidence "" false'],
    "fails safe: the strip after it cannot be told from a dropped socket's, so it is read as one without the marker, handing the "
    + "comments out on the page's own connection back with nothing posted again, whatever it carries");
  conn.delete("TESTHOST2");
  push({ type: "tabOrder", order: [], freshHost: "TESTHOST2", createIdEcho: true });
  assert.deepEqual(calls.splice(0), ['evidence "TESTHOST2" true', 'repost "TESTHOST2"'], "a relay's connection has no generation: its push is read as ever");
});

// ── executed: the fail-safe, evidence of no echo hands the echo-mode creates out on that host back (handBackEchoCreates ─
// ── and leaveEchoModeWithoutEcho, lifted) ────────────────────────────────────────────────────────────────────────────
function liftRender(sig: string, js: string): string {
  const start = UI.indexOf("function " + sig);
  assert.ok(start > 0, "render.ts has function " + sig);
  return UI.slice(start, UI.indexOf("\n}\n", start) + 3).replace(sig, js);
}

test("a host shown to have no echo has every echo-mode create still out on it handed back: its hold ended with nothing posted, its working mark gone, its words in the note, its open sent dialog closed and a toast for each; another host's and main-mode creates untouched", () => {
  const src = liftRender("handBackEchoCreates(host: string): void {", "handBackEchoCreates(host) {");
  const sent = newCommentCreate(ANCHOR, "Why jitter at all?", "jitter-question");
  sent.tries = 2;                                                   // armed by a transient refusal
  const closed = newCommentCreate({ ...ANCHOR, uuid: "a2", exact: "a jitter of ten percent" }, "And the cap?", "");   // its sent dialog closed before its answer
  const remote = newCommentCreate({ ...ANCHOR, sid: "TESTHOST2:" + ANCHOR.sid, uuid: "r1" }, "Over there.", "");
  const echo = new Map([sent, closed, remote].map((c) => [c.createId, c] as [string, CommentCreate]));
  const mainHold = newCommentCreate({ ...ANCHOR, uuid: "a3" }, "main's", "");
  const main = new Map([[mainHold.uuid, mainHold]]);
  const givenUp = new Map<string, CommentCreate>(), handed = new Set<string>(), held: CommentCreate[] = [closed];
  const calls: string[] = [], toasts: string[] = [], posted: unknown[] = [];
  const run = (host: string, pa: unknown) => new Function("cmtEchoCreates", "cmtCreateInFlight", "cmtEchoGivenUp", "cmtHandedBack", "cmtHeldRefusals",
      "pendingCommentAnchor", "hostOf", "dropSynthThread", "warnToast", "handedBackToast", "closeCommentPop", "paintOpenNote", "vscodeApi", "host",
      src + "\nhandBackEchoCreates(host);")(
    echo, main, givenUp, handed, held, pa, hostOf, (_sid: string, k: string) => calls.push("drop " + k), (t: string) => toasts.push(t),
    handedBackToast, () => calls.push("close"), () => calls.push("note"), { postMessage: (m: unknown) => posted.push(m) }, host);
  const dialog = { sid: ANCHOR.sid, uuid: "a1", exact: ANCHOR.exact, echo: true, createId: sent.createId };   // sent's dialog, open
  run("", dialog);
  assert.deepEqual([...echo.keys()], [remote.createId], "no echo-mode create is left out on the host, so none is retried or posted again; another host's stays");
  assert.deepEqual(posted, [], "and nothing is posted");
  assert.deepEqual([...main.keys()], ["a3"], "no main-mode hold is made or ended: no conversion to main's handling");
  assert.deepEqual(held, [closed, sent], "each one's words wait in the note: the entry its closed dialog made stays, and the open one gets one");
  assert.deepEqual([...handed].sort(), [sent.createId, closed.createId].sort(), "each is marked handed back, which its entry's words say");
  assert.deepEqual([...givenUp.keys()].sort(), [sent.createId, closed.createId].sort(),
                   "and kept with the creates the page stopped handling, so an acknowledgment naming one still settles it as a late landing");
  assert.deepEqual(calls, ["drop " + sent.createId, "drop " + closed.createId, "close"],
                   "each one's working mark and latch go, and its sent dialog, open, closes, with no repaint left for a note it no longer shows");
  assert.deepEqual(toasts, [handedBackToast(ANCHOR.exact), handedBackToast(closed.exact)], "and a toast names each one's passage and says where its words are");
  assert.equal(handedBackToast("p95 latency"),
    "Your comment on “p95 latency” may or may not have been saved, because the kernel restarted as an older version. Its words are kept: select text anywhere in that message, right-click it and choose Comment to see them.",
    "the toast says, in the person's words, that it may or may not have been saved and why, and how to reach the note");
  calls.length = 0;
  run("TESTHOST2", { sid: ANCHOR.sid, uuid: "a9", exact: "other", echo: true });   // an unsent dialog open elsewhere
  assert.deepEqual([[...echo.keys()], calls.slice(-1)], [[], ["note"]], "another host's own evidence hands its create back, and an open dialog's note is repainted");
  assert.match(UI, /const HANDED_BACK_LEAD = " may or may not have been saved, because the kernel restarted as an older version:";/,
    "the note's entry for a handed-back comment leads with the same words (executed in comment-create-gesture-browser.test.ts, whose "
    + "fail-safe tests read the note's text)");
});

test("an echo-mode dialog that has not sent, on a host whose latest evidence shows no echo, turns main mode and is rebuilt, unless a press on its note holds the rebuild; a sent one, a main-mode one, or one on a host still known to echo stays as it is", () => {
  const src = liftRender("leaveEchoModeWithoutEcho(): void {", "leaveEchoModeWithoutEcho() {");
  const run = (pa: Record<string, unknown> | null, evidence: Map<string, boolean>, held = false) => {
    const calls: string[] = [];
    new Function("pendingCommentAnchor", "createIdEcho", "hostOf", "holdNoteRepaint", "renderCommentPopover", "document", src + "\nleaveEchoModeWithoutEcho();")(
      pa, evidence, hostOf, (k: string) => { calls.push("hold " + k); return held; }, () => calls.push("render"),
      { getElementById: () => ({ remove: () => calls.push("remove") }) });
    return calls;
  };
  const none = new Map([["", false]]);
  const unsent = { sid: ANCHOR.sid, uuid: "a1", exact: ANCHOR.exact, echo: true };
  assert.deepEqual([run(unsent, none), unsent.echo], [["hold rebuild", "remove", "render"], false],
                   "an unsent echo-mode dialog on a host without the echo turns main mode, rebuilt from main's draft of its message");
  const pressed = { ...unsent, echo: true };
  assert.deepEqual([run(pressed, none, true), pressed.echo], [["hold rebuild"], false],
                   "a press under way on its note holds the rebuild for the release; the dialog is main mode already");
  const sentDialog = { ...unsent, echo: true, createId: "k1" };
  assert.deepEqual([run(sentDialog, none), sentDialog.echo], [[], true],
                   "a sent one is left as it is: its create was handed back (closing it) or settled, waiting for its thread's frame");
  const mainDialog = { ...unsent, echo: false };
  assert.deepEqual(run(mainDialog, none), [], "a main-mode dialog has nothing to turn");
  for (const ev of [new Map([["", true]]), new Map<string, boolean>(), new Map([["TESTHOST2", false]])]) {
    const d = { ...unsent, echo: true };
    assert.deepEqual([run(d, ev), d.echo], [[], true], "a host still known to echo, or not known either way, or another host without it, changes nothing");
  }
  assert.deepEqual(run(null, none), [], "and with no dialog open there is nothing to do");
  const frameEnd = UI.indexOf("\n}));\n", UI.indexOf("listenForFrames(perfFrameHandler(\"chat\""));
  assert.ok(frameEnd > 0 && /\n  leaveEchoModeWithoutEcho\(\);$/.test(UI.slice(0, frameEnd)),
    "the frame handler turns it as its last step, after main's handling of the frame has run beside the echo-mode dialog (where the code "
    + "lives; executed in comment-create-gesture-browser.test.ts's fail-safe test of an unsent dialog)");
  assert.match(UI, /noteHostEcho\(d\.host, capsAnnounceEcho\(d\.caps\)\);\n  leaveEchoModeWithoutEcho\(\);/,
    "and so does a remote host's caps frame, which reaches the page as an event of its own (where the call lives; executed in "
    + "comment-create-gesture-browser.test.ts: 'the fail-safe: a caps frame without the cap hands back the comment still out on its host, "
    + "local or relayed, with its dialog open or closed, and turns an unsent echo-mode dialog there main mode, the page posting nothing, "
    + "played ahead of the connection's connect push, an order no kernel sends', whose relayed unsent dialog stays echo mode without it)");
});

test("only the kernel's shim assigns the page socket's generation and its open read: no page code writes window.__rompSockGen or window.__rompSockOpen, or builds a socket-flip frame, with or without its generation", () => {
  const REPO = path.resolve(process.cwd(), "..");
  const files: string[] = [];
  const walk = (dir: string) => {
    for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
      const p = path.join(dir, e.name);
      if (e.isDirectory()) { if (!["node_modules", "dist", "out-tests", "out"].includes(e.name)) walk(p); }
      else if (/\.(ts|js|mjs|html)$/.test(e.name) && !/\.test\.(ts|js|mjs)$/.test(e.name)) files.push(p);
    }
  };
  walk(path.join(REPO, "ui")); walk(path.join(REPO, "vscode-extension", "src"));
  assert.ok(files.some((f) => f.endsWith(path.join("ui", "webview", "render.ts"))) && files.length > 50, "the census reads the page code: " + files.length + " files");
  const writes = /__rompSock(Gen|Open)\s*(=(?!=)|\+\+|--|[-+*]=)|(\+\+|--)\s*(window\.)?__rompSockGen|type:\s*"wsup"/;
  const hits = files.filter((f) => writes.test(fs.readFileSync(f, "utf8").split("\n").filter((l) => !/^\s*(\/\/|\*)/.test(l)).join("\n")));
  assert.deepEqual(hits.map((f) => path.relative(REPO, f)), [],
    "no page code writes the generation or the open read, or builds a flip frame: the page reads what the shim assigns (render.ts "
    + "cmtFlipGen, sockOpen)");
  const shim = KERNEL.slice(KERNEL.indexOf("/*shim-core*/"), KERNEL.indexOf("/*end-shim-core*/"));
  assert.ok(writes.test(shim) && /enqueue\(\{type:"wsup",gen:sockGen\}\)/.test(shim) && /window\.__rompSockOpen=function\(\)/.test(shim),
    "and the census's pattern finds the shim's own assignments: the shim is where they live (executed in "
    + "tests/test_pane_shim_return.py's SocketGeneration)");
});

test("the capability the page reads for the createId echo is the one the kernel announces", () => {
  const caps = /^KERNEL_WS_CAPS = \(([^)]*)\)/m.exec(KERNEL);
  assert.ok(caps, "the kernel's caps tuple");
  assert.ok(caps![1].split(",").map((c) => c.trim().replace(/"/g, "")).includes(CREATE_ID_ECHO_CAP),
            "KERNEL_WS_CAPS carries " + CREATE_ID_ECHO_CAP + ", the kernel's announcement that every create answer echoes the createId");
  const leg = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "comment-create-gesture-browser.test.ts"), "utf8");
  assert.match(leg, new RegExp('const ECHO_CAP = "' + CREATE_ID_ECHO_CAP + '";'), "and the browser leg's caps frame names the same");
});

test("a connection's connect push is what posts held comments again: the two reconnect events only open a connection for its push, and the VS Code pipe's return does neither", () => {
  assert.match(UI, /\n  if \(m\.type === "tabOrder"\) noteConnectPush\(m\);\n/,
    "every strip the page is handed goes to noteConnectPush, which reads a connection's first (where the code lives; executed in "
    + "comment-create-gesture-browser.test.ts: 'a comment whose create was never answered is posted again once, by the connect push of the "
    + "page's connection when it comes back carrying the echo, and its acknowledgment settles its note')");
  assert.equal(UI.split("repostHeldCreates(").length - 1, 2,
    "one definition and one call, in noteConnectPush on a marked connection: no connection's open posts anything again (executed in "
    + "comment-create-gesture-browser.test.ts, each counting the posts from before the open: for the page's own socket, 'frames still "
    + "draining from the page's dropped socket post nothing again, and the next connection's connect push does', which fails when the "
    + "romp:wsup listener posts the held comments; for a relay, 'a relay coming back posts again only its own host's comments still held, "
    + "at its connect push, and the page's own connection none of them', which fails when the romp:hostRelayUp listener does; and for "
    + "both, 'a mixed build is read per connection: the page's own socket's connect push and a relay's each decide for their own host's "
    + "comments, the local kernel marked and the remote one not, and the reverse: the marked host's comment is posted again, and the "
    + "other's is handed back as the fail-safe hands a comment back')");
  const wsup = UI.match(/window\.addEventListener\("romp:wsup", \(\) => \{\n  reshipPendingUploads\(\);([\s\S]*?)\n\}\);/);
  assert.ok(wsup, "the page socket's re-ship listener");
  assert.doesNotMatch(wsup![1], /repostHeldCreates|cmtConnPush/,
    "the page's own socket opening again posts nothing: the next connection starts at the shim's socket-flip frame, in frame order (a "
    + "source pin only for the listener; the frame's reading is executed in the test named first)");
  assert.match(UI, /\n  if \(m\.type === "wsup"\) \{\n    cmtFlipGen = typeof m\.gen === "number" && sockGen\(\) !== undefined \? m\.gen : null;\n    if \(cmtFlipGen === null \|\| cmtFlipGen === sockGen\(\)\) cmtConnPush\.delete\(""\);\n  \}\n/,
    "the shim's socket-flip frame carrying the current generation opens the page's next connection for its push, and an earlier "
    + "socket's opens nothing; one carrying no generation opens it for a push read as one without the marker (where the code lives; "
    + "executed in the test named first, and in comment-create-gesture-browser.test.ts: 'the fail-safe: a strip from a socket that opened and dropped before the shim handed any of its frames on, handed on once the next socket is open, is read as no connect push, whether or not the page heard that reopen, so it posts nothing and the open socket's own connect push decides' "
    + "and 'the fail-safe: after a socket-flip frame carrying no generation, or on a page whose shim published none, the next strip is read as one without the marker, whatever it carries, so the comments still out are handed back with nothing posted')");
  assert.match(UI, /window\.addEventListener\("romp:wsup", \(\) => \{ cmtConnPush\.set\("", "down"\); \}\);/,
    "each reopen of the page's own socket reads the connection as down until a flip frame opens the next one (where the code lives; "
    + "executed in comment-create-gesture-browser.test.ts by the tests named just above). Its drop has no listener here: until the "
    + "reopen the entry holds the dropped connection's reading, whose first strip was read, so no strip is read again, and the retry "
    + "posts nothing on the page's own socket while the shim says it is not open, which it is not from the drop to the next open "
    + "(executed in comment-create-gesture-browser.test.ts: 'frames still draining from the page's dropped socket post nothing again, "
    + "and the next connection's connect push does')");
  const relay = UI.match(/window\.addEventListener\("romp:hostRelayUp", \(e\) => \{([\s\S]*?)\n\}\);/);
  assert.ok(relay, "the relay's reopen listener");
  assert.match(relay![1], /\n  if \(h\) cmtConnPush\.delete\(h\);/,
    "a host's relay opening again opens that host's next connection for its push, and posts nothing itself (where the code lives; "
    + "executed in comment-create-gesture-browser.test.ts: 'a relay coming back posts again only its own host's comments still held, at its "
    + "connect push, and the page's own connection none of them', and the relayed cases of 'the fail-safe: a comment still out when its kernel comes back without the echo is handed back at that connection's connect push, local or relayed, sent before the push or between the open and the push, with its dialog open or closed: the dialog closes, the note says it may or may not have been saved and holds its words and typed name, Bring it back is enabled, and the page posts nothing more until the person sends it again')");
  assert.doesNotMatch(UI, /pipeState[^\n]*(repostHeldCreates|cmtConnPush)/,
    "the VS Code pipe's return neither posts nor reopens: the extension replaces the page's html on every reconnect after the first, so a "
    + "page lives one connection, whose first strip is read (a source pin only: no executed test plays a VS Code reconnect)");
});

// ── executed: main's adoption (adoptCommentThread, lifted) leaves echo-mode state alone ──────────────────────────────
test("main's adoption never swaps an echo-mode dialog for its thread, and never carries an echo-mode create's latch: with one open, it carries main's latch, clears main's parked adoption and marks the thread seen", () => {
  const start = UI.indexOf("function adoptCommentThread(sid: string, tid: string): void {");
  assert.ok(start > 0, "render.ts has adoptCommentThread");
  const src = UI.slice(start, UI.indexOf("\n}\n", start) + 3).replace("adoptCommentThread(sid: string, tid: string): void {", "adoptCommentThread(sid, tid) {")
    .replace("cmtAwaitBase.get(k)!)", "cmtAwaitBase.get(k))");                          // the one TypeScript-only mark in it
  const run = (anchor: unknown, latches: Map<string, unknown>, echoIds: string[], adoptSid: string = ANCHOR.sid) => {
    const drafts = new Map([["new:a1", "main's words"], ["newname:a1", "main-name"]]);
    const posted: unknown[] = [];
    const out = new Function("cmtAwaitBase", "cmtEchoMinted", "commentDrafts", "vscodeApi", "renderCommentPopover", "applyCommentMarks", "anchor",
      "let pendingCommentAnchor = anchor, pendingAdoptTid = 't-0002', openCommentKey = null;\n"
      + src + "\nadoptCommentThread('" + adoptSid + "', 't-0002');"
      + " return { pendingCommentAnchor, pendingAdoptTid, openCommentKey };")(
      latches, new Set(echoIds), drafts, { postMessage: (m: unknown) => posted.push(m) }, () => {}, () => {}, anchor);
    return { ...out, drafts: Object.fromEntries(drafts), posted };
  };
  const echoDialog = { sid: ANCHOR.sid, uuid: "a1", exact: "exponential backoff", echo: true, createId: "k2echo" };
  const mainLatch0 = { agent: 2 }, echoLatch0 = { agent: 3 };
  const latches0 = new Map<string, unknown>([["pending:a1", mainLatch0], ["pending:k2echo", echoLatch0]]);
  const kept = run(echoDialog, latches0, ["k2echo"]);
  assert.deepEqual([kept.pendingCommentAnchor, kept.pendingAdoptTid, kept.openCommentKey, kept.drafts],
                   [echoDialog, null, null, { "new:a1": "main's words", "newname:a1": "main-name" }],
                   "an echo-mode dialog open: main's adoption clears main's parked adoption and skips the dialog swap, the dialog and main's "
                   + "draft of its message left as they are and no thread opened over it");
  assert.deepEqual(kept.posted, [{ type: "commentSeen", id: ANCHOR.sid, tid: "t-0002" }], "and marks the thread seen, as main's adoption posts it");
  assert.deepEqual([latches0.get("t-0002"), latches0.get("pending:k2echo"), latches0.has("pending:a1")], [mainLatch0, echoLatch0, false],
                   "and carries main's latch onto the thread, an echo-mode create's staying with its own synthetic thread");
  const other = run(echoDialog, new Map(), ["k2echo"], "bbbbbbbb-1111-2222-3333-444444444444");
  assert.deepEqual([other.pendingCommentAnchor, other.pendingAdoptTid, other.openCommentKey], [echoDialog, null, null],
                   "a thread of another session (a parked adoption run at its frame): the dialog stays open, where main's adoption would close it");
  const mainLatch = { agent: 0 }, echoLatch = { agent: 1 };
  const latches = new Map<string, unknown>([["pending:a1", mainLatch], ["pending:k2echo", echoLatch]]);
  const mainDialog = { sid: ANCHOR.sid, uuid: "a1", exact: "exponential backoff" };
  const took = run(mainDialog, latches, ["k2echo"]);
  assert.deepEqual([took.pendingCommentAnchor, took.openCommentKey, took.drafts, took.pendingAdoptTid],
                   [null, { sid: ANCHOR.sid, tid: "t-0002" }, {}, null],
                   "a main-mode dialog: main's adoption, its drafts spent, the thread opened, the park cleared");
  assert.deepEqual(took.posted, [{ type: "commentSeen", id: ANCHOR.sid, tid: "t-0002" }], "and the thread marked seen, as main's adoption posts it");
  assert.deepEqual([latches.get("t-0002"), latches.get("pending:k2echo"), latches.has("pending:a1")], [mainLatch, echoLatch, false],
                   "a main-mode create's latch carries onto the thread, and an echo-mode create's stays with its own synthetic thread");
});

// ── a thread that became its own session (the user 2026-09-10, with a screenshot) ─────────────────

test("a promoted thread's popup is the quote, one line, and Open the session in the shared button dress", () => {
  // the kernel ships a promoted thread with no messages or events, so the popup renders no list for it:
  // an empty list only grew into the box's fixed height (the void under the quote)
  assert.match(UI, /if \(th && th\.status !== "promoted"\) \{\s*\n(?:\s*\/\/[^\n]*\n)*\s*const list = el\("div", "cmt-msgs"\);/);
  const start = UI.indexOf("} else if (th) {\n    // a thread that became its own session");
  assert.ok(start > 0, "the promoted branch of renderCommentPopover");
  const branch = UI.slice(start, UI.indexOf("document.body.appendChild(pop);", start));
  assert.match(branch, /const open = el\("button", "cmt-act"\) as HTMLButtonElement;/,
               "the shared .cmt-act word-button, never the composer's send-glyph square");
  assert.doesNotMatch(branch, /"cmt-send"/);
  assert.match(branch, /open\.textContent = "Open the session";/);
  assert.match(branch, /open\.dataset\.act = "cmtopensession";/);
  assert.match(branch, /const row = el\("div", "cmt-actions"\);[\s\S]*row\.appendChild\(open\);\s*\n\s*pop\.appendChild\(row\);/, "inside .cmt-actions");
  assert.match(branch, /const note = el\("div", "cmt-note"\);\s*\n\s*note\.textContent = "The discussion continues there\.";/,
               "one line saying where the talk went");
  // and the quote never flexes in this state, whatever size the box is (the .sized rule hands it the free room otherwise)
  assert.match(CSS, /\.cmt-pop\.sized\[data-status="promoted"\] \.cmt-quote \{ flex: 0 0 auto; min-height: 0; \}/);
});

// ── the mark never lands between a table's cells (T349, the user 2026-09-11) ──────────────────────
// The whitespace text between <td>s and <tr>s sits directly under the table's structural elements; an inline <mark>
// placed there gets its own anonymous cell and the columns shift. The DOM pass asks this before wrapping each slice.
test("markSkipsParent: a table's structural parents are skipped, every text-bearing parent is wrapped", () => {
  for (const tag of ["TABLE", "THEAD", "TBODY", "TFOOT", "TR"]) assert.equal(markSkipsParent(tag), true, tag);
  for (const tag of ["TD", "TH", "P", "LI", "CODE", "STRONG", "EM", "SPAN", "DIV", "CAPTION", "A"]) assert.equal(markSkipsParent(tag), false, tag);
  assert.equal(markSkipsParent(null), false); assert.equal(markSkipsParent(undefined), false); assert.equal(markSkipsParent(""), false);
  // a selection across a row: the cells' own text nodes are wrapped, the separators between them are not
  const nodes = [{ text: "Charlie", parent: "TD" }, { text: "\n", parent: "TR" }, { text: "12", parent: "TD" }, { text: "\n", parent: "TR" }, { text: "done", parent: "TD" }];
  const r = findExact(nodes.map((n) => n.text).join(""), "Charlie 12 done")!;
  const wrapped = sliceRanges(nodes.map((n) => n.text.length), r.start, r.end).filter((sl) => !markSkipsParent(nodes[sl.idx].parent)).map((sl) => nodes[sl.idx].text);
  assert.deepEqual(wrapped, ["Charlie", "12", "done"], "one mark per cell, none in the row itself");
});

// ── executed: an ack's settle (settleAckedCreate, lifted from render.ts) ───────────────────────────────────────────
test("an echo-mode ack settles the create it answers alone: its hold, its own latch, and its note entry", () => {
  const start = UI.indexOf("function settleAckedCreate(held: CommentCreate, tid: string): void {");
  assert.ok(start > 0, "the ack's settle lives in settleAckedCreate");
  const src = UI.slice(start, UI.indexOf("\n}\n", start) + 3).replace("(held: CommentCreate, tid: string): void {", "(held, tid) {");
  const first = newCommentCreate(ANCHOR, "Why jitter at all?", "");
  const second = newCommentCreate({ ...ANCHOR, exact: "a jitter of ten percent" }, "And the cap?", "");
  const holds = new Map([[first.createId, first], [second.createId, second]]);
  const latchFirst = { agent: 0, total: 1 }, latchSecond = { agent: 0, total: 2 };
  const latches = new Map<string, unknown>([["pending:" + first.createId, latchFirst], ["pending:" + second.createId, latchSecond]]);
  const spent: string[] = [];
  new Function("cmtEchoCreates", "cmtAwaitBase", "spendLandedWords", "held", "tid", src + "\nsettleAckedCreate(held, tid);")(
    holds, latches, (c: CommentCreate) => spent.push(c.createId), first, "t-0002");
  assert.deepEqual([...holds.keys()], [second.createId], "the ack retires its own create's hold, and the other create's stands");
  assert.equal(latches.get("t-0002"), latchFirst, "its own create's latch carries onto the real thread");
  assert.equal(latches.has("pending:" + first.createId), false, "and leaves the synthetic thread's key");
  assert.equal(latches.get("pending:" + second.createId), latchSecond, "the other create's latch stays with its synthetic thread");
  assert.deepEqual(spent, [first.createId], "and the note entry its dialog's close left, if any, goes: the comment landed");
});
