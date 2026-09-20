// The transcript's bottom moving UP under an at-bottom reader keeps them at the bottom, through the pane's own
// writer (T262f, the user 2026-09-08: the pane is unreadable near the bottom; their laptop's scroll breadcrumbs
// showed the view moving up by one fixed amount with no pane write between the rows). When an element at the
// END of #content loses height — the live-ask card cleared, a queued group emptying, the offline foot going —
// the browser clamps scrollTop to the new maximum: an UNWRITTEN move the journal could only file as a gesture,
// and one the follow-mode latch never saw. The rule is the same shape as the boxes-below one: the view's RECORDED
// follow mode (`stick`, the pre-change truth) decides; on, and the tail shrank, the reader is written to the new
// bottom through writeScroll (writer "tail-shrink") — the same place the clamp left them, so nothing visible moves
// twice, but the move is now the pane's, attributed in the journal, and the latch is re-read from a real scroll
// event; off, nothing (the clamp cannot reach a reader more than the shrink above the bottom, and the top line
// they read never moved). Pure rule executed here; render.ts wiring pinned.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { followRebuiltTail, followTailShrink } from "./scroll-keep";
import { hideEdges } from "../test-dom-shim";   // the fake-DOM rule (ui/test-dom-shim.test.ts): a fake element enumerates its primitives alone, so a failing dump never walks its tree

const requireCjs = createRequire(__filename);
const RENDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");

function liftBetween(startAnchor: string, endAnchor: string): string {
  const a = RENDER.indexOf(startAnchor), b = RENDER.indexOf(endAnchor, a);
  assert.ok(a > 0 && b > a, `anchors not found: ${startAnchor.slice(0, 40)} or ${endAnchor.slice(0, 40)} moved; re-anchor`);
  return requireCjs("esbuild").transformSync(RENDER.slice(a, b), { loader: "ts" }).code;
}

test("a follow-mode reader is written to the bottom when the tail shrinks; growth and a scrolled-up reader are left alone", () => {
  assert.equal(followTailShrink(true, -95), true, "the card went: the bottom moved up by 95 px");
  assert.equal(followTailShrink(true, -1), true, "any shrink");
  assert.equal(followTailShrink(true, 0), false);
  assert.equal(followTailShrink(true, 95), false, "growth is the append path's (append-stick) or the reveal's (liveask-reveal), not this rule's");
  assert.equal(followTailShrink(false, -95), false, "reading history: untouched");
});

test("a follow-mode reader whose window was just rebuilt at the tail follows the rows' settling of either sign while armed; unarmed, growth is left to the append path (PR E)", () => {
  assert.equal(followRebuiltTail(true, true, 40.64), true, "the rebuilt rows grew 40 px after the re-window's synchronous bottom write: written back to the bottom");
  assert.equal(followRebuiltTail(true, true, -223), true, "…or shrank (the tail-shrink rule would have caught this one too)");
  assert.equal(followRebuiltTail(true, true, 0), false);
  assert.equal(followRebuiltTail(true, false, 40), false, "not armed: growth is the append path's, as followTailShrink says");
  assert.equal(followRebuiltTail(false, true, 40), false, "reading history: untouched");
});

test("render.ts observes every view's element and #live-ask, and writes the bottom through the scroll-write helper", () => {
  assert.match(RENDER, /import \{[^}]*\bfollowTailShrink\b[^}]*\} from "\.\/scroll-keep";/);
  // the per-view ResizeObserver (it already re-lands the rail) carries the rule
  const m = RENDER.match(/v\.ro = new ResizeObserver\(\(entries\) => \{([\s\S]*?)\n\s*\}\);/);
  assert.ok(m, "the view's ResizeObserver");
  assert.match(m![1], /followTailShrink\(view\.stick, h - lastH\)/, "the recorded follow mode decides, never a post-change atBottom read");
  assert.match(m![1], /writeScroll\(content, content\.scrollHeight, "tail-shrink", true\);/);
  // the re-window's follow rides the same observer, armed by virtualizeToViewport's stick branch; the mark is ended by the events that end
  // the re-window (the reader's own scroll, the view's next paint), never by a delivery, which a rebuild that changed no height never makes:
  // cleared there, the mark stayed armed for good and an unrelated later height change wrote the reader to the bottom (review round 1b)
  assert.match(m![1], /\} else if \(content && lastH >= 0 && activeId === id && view\.shown && content\.clientHeight > 0 && followRebuiltTail\(view\.stick, view\.followRebuilt === true, h - lastH\)\) \{\s*\n[^\n]*\n\s*writeScroll\(content, content\.scrollHeight, "rewindow", true\);/);
  assert.doesNotMatch(m![1], /followRebuilt = false/, "the observer's delivery does not clear the mark");
  assert.match(RENDER, /if \(gv && cls === "gesture"\) gv\.followRebuilt = false;/, "the reader's own scroll (a gesture, never a write's echo) ends it");
  assert.match(RENDER, /const s = sessions\.get\(id\);\s*\n\s*if \(!s\) return v;\s*\n(?:\s*\/\/[^\n]*\n)*\s*v\.followRebuilt = false;/, "…and so does the view's next paint (syncViewInner, before any branch)");
  assert.equal((RENDER.match(/followRebuilt = false/g) || []).length, 2, "two clears, both on an ending event");
  assert.match(RENDER, /v\.followRebuilt = true; \}/, "the stick re-window arms it");
  assert.match(m![1], /activeId === id/, "only the ACTIVE view's element moves the reader");
  // the live-ask host sits inside #content after the threads: its shrink is the card leaving
  assert.match(RENDER, /const tailHost = document\.getElementById\("live-ask"\);/);
  assert.match(RENDER, /followTailShrink\(v\.stick, h - tailLastH\)/);
  assert.equal((RENDER.match(/"tail-shrink"/g) || []).length, 2, "two observers, one writer name");
});

// ── the re-window's mark, executed (review round 1b) ─────────────────────────────────────────────

/** The view observer's callback and the scroll listener, lifted from render.ts and run over one fake scroller: the observer's fake hands
 *  its callback back, the scroller's `addEventListener` hands the listener back; `classify` is what classifyScroll says of a scroll event. */
function liftFollow(classify: () => "gesture" | "write-echo" | "write") {
  const writes: Array<{ writer: string; top: number }> = [];
  let cb: ((entries: any[]) => void) | null = null, onScroll: (() => void) | null = null;
  const content: any = { scrollTop: 1400, scrollHeight: 2000, clientHeight: 600, addEventListener: (_k: string, f: () => void) => { onScroll = f; } };
  const view: any = { stick: true, shown: true, followRebuilt: false, el: hideEdges({ children: [] }), scrollTop: 0 };   // the fake element is built through the shared shim: its children edge is hidden at creation, still readable
  const hooks = { v: view, content, writes, classify, followTailShrink, followRebuiltTail,
                  ResizeObserver: class { constructor(f: (e: any[]) => void) { cb = f; } observe() {} unobserve() {} disconnect() {} } };
  const observer = liftBetween("      let lastH = -1;", "      v.ro.observe(elv);");
  // the listener's whole block: it opens with `c` read off document (the fake scroller here) and closes after the passive option
  const listener = liftBetween('{\n  const c = document.getElementById("content");\n  if (c) c.addEventListener("scroll", () => {', "// The live-ask host (#live-ask) sits INSIDE #content");
  const prelude = `
    const H = HOOKS;
    const v = H.v, id = "A", activeId = "A", views = new Map([["A", H.v]]);
    const document = { getElementById: (x) => (x === "content" ? H.content : null) };
    const ResizeObserver = H.ResizeObserver;
    const scheduleRailSticky = () => {}; const scrollDiagRow = () => {}; const tailChangeRow = () => ({}); const tailLabel = () => "";
    const followTailShrink = H.followTailShrink, followRebuiltTail = H.followRebuiltTail;
    const writeScroll = (c, top, writer) => { H.writes.push({ writer, top }); c.scrollTop = Math.min(top, c.scrollHeight - c.clientHeight); };
    const followReader = () => {}; const atBottom = (x) => x.scrollHeight - x.scrollTop - x.clientHeight <= 2; let pendingBuildRaf = null;
    const classifyScroll = () => H.classify(); let lastScrollWriteAfter = null;
    const gestureEvidence = () => true; const settleLastInput = 0; const settleScrollerHeld = false; const settleGesture = () => {}; const settleSample = () => {};
    let lastKnownSh = 0;
  `;
  new Function("HOOKS", prelude + observer + listener)(hooks);
  assert.ok(cb && onScroll, "the observer and the scroll listener were installed");
  return { view, content, writes, deliver: (h: number) => cb!([{ contentRect: { height: h } }]), scroll: (top: number) => { content.scrollTop = top; onScroll!(); } };
}

test("the re-window's mark is ended by the reader's own scroll, not by a delivery that may never come: armed with no settle delivery, a gesture clears it, and an unrelated later height change writes nothing (review round 1b)", () => {
  const f = liftFollow(() => "gesture");
  f.deliver(1000);                 // the baseline: observe fires once on attach
  f.view.followRebuilt = true;     // the stick re-window armed the follow after its build and its bottom write…
  // …and NO delivery follows: the rebuilt window came out at the same height, so the observer has nothing to report
  f.scroll(900);                   // the reader scrolls up: the re-window is over
  assert.equal(f.view.followRebuilt, false, "the gesture ended the re-window's follow");
  f.deliver(1050);                 // an unrelated later height change (a card growing, an image sizing)
  assert.deepEqual(f.writes.filter((w) => w.writer === "rewindow"), [], "nothing wrote the reader to the bottom (under the old code the arm survived the gesture and this delivery wrote it)");
});

test("…a write's echo does not end it: the re-window's own bottom write echoes as a scroll event, and the rows' settling after it is still followed", () => {
  const f = liftFollow(() => "write-echo");
  f.deliver(1000);
  f.view.followRebuilt = true;
  f.scroll(1400);                  // the echo of the re-window's own write
  assert.equal(f.view.followRebuilt, true, "an echo is no gesture: the arm stands");
  f.deliver(1040);                 // the rebuilt rows settled taller
  assert.deepEqual(f.writes.map((w) => w.writer), ["rewindow"], "the settle is followed");
  assert.equal(f.content.scrollTop, 1400, "…to the bottom");
});
