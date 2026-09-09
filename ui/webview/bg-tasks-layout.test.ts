// Background-task box (the user 2026-07-07): ONE dedicated full-width rounded box just above the statusline.
// The one-line header BAR ("Awaiting …" idle / "In the background …" working) sits at the TOP of the box; clicking it expands the list DOWNWARD
// beneath the header inside the SAME box (a normal flex-direction: column, reading top-to-bottom), so nothing
// spills below the box — the earlier design let a shrink-1 box get squeezed and its rows clipped behind the
// composer. It HOLDS its content (flex 0 0 auto), is capped so it never crowds the composer, and the inner
// list scrolls. Status dots are SOLID (the pulsating yellow was distracting). No jsdom for the chat
// renderer → pin at the source.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const CSS = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "styles.css"), "utf8");
const RENDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");
const BOX = (CSS.match(/#bg-tasks \{[^}]*\}/) || [""])[0];
const HEAD = (CSS.match(/\.bg-fold-head \{[^}]*\}/) || [""])[0];

test("#bg-tasks is ONE full-width bordered box (distinct bg) that HOLDS its content, capped", () => {
  assert.match(BOX, /flex: 0 0 auto;/);                       // holds its content (not shrink-1 → no squeeze/clip)
  assert.match(BOX, /max-height: min\(50vh, 340px\);/);       // capped so it never crowds the composer
  assert.match(BOX, /border: 1px solid var\(--box-border\);/);
  assert.match(BOX, /border-radius: 8px;/);
  assert.match(BOX, /background: var\(--box-bg\);/);           // a real box, not a faint borderless line
  assert.match(BOX, /margin: 8px 10px 6px;/);                 // a gap/divider above (+ side inset)
});

test("the list expands DOWNWARD beneath the header (header at the top) — nothing spills below the box", () => {
  assert.match(BOX, /flex-direction: column;/);               // first child (header) at top, list below
  assert.doesNotMatch(BOX, /column-reverse/);
  assert.match(CSS, /\.bg-list \{[^}]*flex: 1 1 auto;[^}]*overflow-y: auto;/);   // inner list scrolls, capped by the box
  // the header bar has NO own border (the box provides it); a bottom border separates it from the list when open
  assert.doesNotMatch(HEAD, /border:/);
  assert.match(CSS, /\.bg-fold-head\.open \{ border-bottom: 1px solid var\(--box-border\); \}/);
  // the fold caret points RIGHT when collapsed → DOWN when open (it expands downward)
  assert.match(RENDER, /car\.textContent = open \? "▾" : "▸";/);
});

// The OPEN list is capped at about six rows (the user 2026-09-08, whose phone showed the box over the
// transcript): seven agents in flight fit under the box's min(50vh, 340px) cap without scrolling, so the
// open box took half the phone's screen and left about three lines of chat between the tab strip and the
// box. The fold itself was already the user's: bgFoldOpen is a page-lifetime Set of session ids, empty
// (closed) by default and written only by the header click and the Awaiting chip, so a box opens only on
// a tap and a reload starts it closed; the fix is the open list's height, not the fold.
test("the open list shows about six rows and scrolls beyond; the cap lifts while a row's details are open (the user 2026-09-08)", () => {
  assert.match(CSS, /\.bg-list:not\(:has\(\.bg-task\.open\)\) \{ max-height: 180px; \}/, "six rows of 29px plus the list's padding");
  assert.match(CSS, /\.bg-list \{[^}]*overflow-y: auto;/, "the inner scroll is the list's own");
  assert.match(BOX, /max-height: min\(50vh, 340px\);/, "the box's own cap still bounds an open row's details");
  // a row's details wear .open on the .bg-task (bgRow), the class that lifts the cap
  assert.match(RENDER, /const row = el\("div", "bg-task bg-" \+ \(t\.status \|\| "running"\) \+ \(t\.awaited \? " bg-awaited" : ""\) \+ \(tOpen && foldable \? " open" : ""\)\);/);
});

test("the fold is the user's: closed by default, opened only by a tap, never by the renderer (the user 2026-09-08)", () => {
  assert.match(RENDER, /const bgFoldOpen = new Set<string>\(\);/, "a page-lifetime Set of session ids, empty (closed) at load");
  const body = RENDER.split("function renderBgTasks(")[1].split("\nfunction ")[0];
  assert.match(body, /const open = bgFoldOpen\.has\(sid\);[\s\S]*?host\.appendChild\(head\);\s*\n\s*if \(!open\) return;/, "not in the set → the header line alone");
  assert.doesNotMatch(body, /bgFoldOpen\.(add|delete|clear)\(/, "the renderer never opens or closes it");
  // the two writers, both gestures (awaiting-rows.test.ts pins the exact list)
  assert.match(RENDER, /"bg-fold": \(el\) => \{[\s\S]{0,200}?if \(bgFoldOpen\.has\(id\)\) bgFoldOpen\.delete\(id\); else bgFoldOpen\.add\(id\);/);
  assert.match(RENDER, /"awaitingChip": \(\) => \{[\s\S]{0,120}?bgFoldOpen\.add\(activeId\);/);
});

test("status dots are SOLID — the pulsating yellow animation is gone", () => {
  assert.doesNotMatch(CSS, /animation: bg-pulse/);
  assert.doesNotMatch(CSS, /@keyframes bg-pulse/);
  assert.match(CSS, /\.bg-dot \{[^}]*background: var\(--bgt\);/);   // just the solid status tint
});

test("each RUNNING task row has a Stop button riding the stable delegate (the user 2026-08-04)", () => {
  // the button posts the SDK's designed stop_task control request, keyed by the id the box shows;
  // gated on status so a finished row never grows a dead control
  // since slice 2 (2026-09-05) the row SPEC decides: a tracked task's Stop handle is its id while it
  // runs (taskRowSpec / awaitRowSpec), and bgRow renders the button from that handle
  assert.match(RENDER, /stopId: status === "running" \? t\.id : null/);
  assert.match(RENDER, /if \(t\.stopId\) \{/);
  assert.match(RENDER, /stop\.dataset\.act = "bg-stop"; stop\.dataset\.id = t\.stopId;/);
  // click-safe: handled on the SAME delegate as the fold toggles, never a per-render listener…
  assert.match(RENDER, /"bg-stop": \(el\) => \{/);
  assert.match(RENDER, /vscodeApi\?\.postMessage\(\{ type: "stopTask", id: activeId, taskId: id \}\);/);
  // …and the click acknowledges IMMEDIATELY, before any round-trip; the row's disappearance (the task's
  // own terminal lifecycle event) is the real confirmation, and a re-render restores a live task's button
  assert.match(RENDER, /btn\.disabled = true; btn\.textContent = "Stopping…";/);
});

test("a row's trailing cluster sits INLINE after the label, left-aligned — never pushed to the right edge (the user 2026-09-05)", () => {
  // Before: .bg-sum grew (flex 1 1 auto) to fill the row, so the arrow, elapsed, status word, Stop and caret
  // hugged the far right — on a wide desktop pane the user missed them entirely. The label now takes only its
  // own width, shrinking with an ellipsis when long (0 1 auto + min-width 0), and the cluster follows it at
  // the existing 8px gap. Every cluster item is 0 0 auto so a long label can never push it off-screen, and
  // nothing in the row uses a spacer, margin-left:auto or space-between.
  const SUM = (CSS.match(/\.bg-sum \{[^}]*\}/) || [""])[0];
  assert.match(SUM, /flex: 0 1 auto; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;/);
  assert.doesNotMatch(SUM, /flex: 1 1 auto/);
  const ROWHEAD = (CSS.match(/\.bg-head \{[^}]*\}/) || [""])[0];
  assert.match(ROWHEAD, /display: flex; align-items: center; gap: 8px;/);
  assert.doesNotMatch(ROWHEAD, /justify-content|space-between/);
  for (const sel of [".bg-since", ".bg-status", ".bg-caret", ".bg-stop", ".tool-open-agent, .sub-head-pin"]) {
    const rule = (CSS.match(new RegExp(sel.replace(/[.,]/g, (c) => "\\" + c) + " \\{[^}]*\\}")) || [""])[0];
    assert.match(rule, /flex: 0 0 auto;/, sel + " holds its width");
    assert.doesNotMatch(rule, /margin-left: auto/, sel + " is not a spacer");
  }
  assert.doesNotMatch(CSS, /\.bg-head [^{]*\{[^}]*margin-left: auto/, "no cluster item is pushed right");
});
