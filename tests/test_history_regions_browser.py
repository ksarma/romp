"""T386 stage 2 (the user 2026-09-12, plans/chat-history-regions.md Part B): the chat's history is a list of REGIONS over the
transcript's turns, runs the page holds and gaps it does not, and the tail run is always resident and live. Served, on the
window lab's hermetic kernel over a synthetic transcript longer than the wire tail (the page boots holding the tail; a head gap
stands above it):

- at boot the ONE gap runs from the head to the tail's first turn, in the top spacer, with no ask on the wire;
- a scroll to the top of the resident run brings the gap into the viewport and the gap asks for ITS page directly (one loadTurns
  for the page-aligned span at its bottom edge, the edge the reader met), and the reply fills the space in place: the gap shrinks
  to the run's start, the reader's row keeps its viewport offset through one attributed gap-fill write, and no scroll gesture is
  filed for a move the reader never made;
- a live tail arriving while the reader is up in history lands at the tail (the run's last uuid moves), with no paused strip and
  no notice: nothing pauses live updates any more.

Synthetic fixtures only (placeholder uuids, invented prose); hostname TESTHOST.
"""
import json
import os
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
from tests.test_live_paused_window_browser import DRIVER_HEAD, TURNS, WindowLab  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent   # the checkout: the stream lab reads the default per-turn constant off chat-regions.ts

DRIVER = DRIVER_HEAD + r"""
const painted = () => page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(() => setTimeout(r, 0)))));
const gestures = () => page.evaluate(() => window.__sent.filter((m) => m.what === "scrollgesture").length);
const writes = (writer) => page.evaluate((w) => window.__sent.filter((m) => m.what === "scrollwrite" && m.data && m.data.writer === w).map((m) => [m.data.before, m.data.after]), writer);
// the row under the viewport top and its offset: the fill must keep it there
const rowAtTop = () => page.evaluate(() => {
  const c = document.getElementById("content"); const cTop = c.getBoundingClientRect().top;
  for (const t of Array.from(document.querySelectorAll("#content .turn[data-uuid]"))) { const r = t.getBoundingClientRect(); if (r.bottom > cTop + 1) return { uuid: t.dataset.uuid, y: Math.round(r.top - cTop) }; }
  return null;
});
const regions = () => page.evaluate(() => (typeof window.__rompRegions === "function" ? window.__rompRegions() : null));   // the session's regions (a gap inside a spacer has no element); the base has no hook and its roads still run to their own red
// The kernel's wire settles before any road runs. The pusher's cycle after the connect push's full frame sends this socket ONE
// status-only chatTail (an empty suffix anchored at the list's last key), and the page truncates after that anchor when it applies
// it, as for every tail. On a pusher that cycles on its wakes that frame lands ~0.1 s after the connect push; on one that holds a
// minimum interval between cycles it lands ~2 s after, inside the roads: its application files a scroll gesture and a scroll write
// (road 2 counts gestures across the fill) and, after road 3's post, cuts the synthetic tail away (measured 10 to 55 ms after the
// post). DRIVER_HEAD's frame log records every chatTail with its source, so the wait is on that event; the settled wire then dedups
// the same tail for a minute, longer than the roads take.
await page.waitForFunction(() => (window.__bootFrames || []).some((f) => f.type === "chatTail" && f.source === "socket"), null, { timeout: 15000 }).catch(() => {});
// ROAD 1: the boot holds the tail; one gap from the head to the tail's start, no ask
const bootRegions = await regions(), turnsBefore = await sentOf("loadTurns");
// ROAD 2: a jump to just above the resident run's first turn (into the gap's bottom edge, the edge a reader scrolling up meets; scrollTop 0
// would be the transcript's HEAD, the gap's top edge, and asks for the head page instead); the gap enters the viewport and asks for its bottom page
// first to the top of the rendered window (the top spacer's end), then up one viewport at a time until the gap's element is on screen (bounded)
await page.evaluate(() => { const c = document.getElementById("content"); const sp = document.querySelector("#content .tx-spacer-top"); c.scrollTop = sp ? sp.offsetHeight + 1 : 0; });
await painted();
for (let i = 0; i < 60; i++) {
  if ((await sentOf("loadTurns")) > turnsBefore) break;   // the gap met the viewport and asked: one page (a further step would meet the shrunken gap and ask its next page)
  const seen = await page.evaluate(() => { const c = document.getElementById("content"); const g = document.querySelector("#content .tx-gap"); if (!g) return false; const r = g.getBoundingClientRect(), cr = c.getBoundingClientRect(); return r.bottom > cr.top && r.top < cr.bottom; });
  if (seen) { await page.waitForFunction((n) => window.__sent.filter((m) => m.type === "loadTurns").length > n, turnsBefore, { timeout: 5000 }).catch(() => {}); break; }
  await page.evaluate(() => { const c = document.getElementById("content"); c.scrollTop = Math.max(0, c.scrollTop - c.clientHeight); });
  await painted();
}
await page.waitForFunction((n) => window.__sent.filter((m) => m.type === "loadTurns").length > n, turnsBefore, { timeout: 10000 }).catch(() => {});
const asks = await page.evaluate(() => window.__sent.filter((m) => m.type === "loadTurns").map((m) => ({ lo: m.lo, hi: m.hi })));
const gapsAsked = (await state()).gaps; const regionsAsked = await regions();
const rowBefore = await rowAtTop();
const gesturesBefore = await gestures();
// the reply fills the gap in place: wait for the gap's end to move down to the ask's start (the run inserted), then the paint
await page.waitForFunction((lo) => { const rs = (typeof window.__rompRegions === "function" && window.__rompRegions()) || []; return rs.length > 0 && rs[0].kind === "gap" && rs[0].hi === lo; }, asks.length ? asks[asks.length - 1].lo : -1, { timeout: 15000 }).catch(() => {});
await painted();
const filled = await state(); const regionsFilled = await regions();
const rowAfter = await rowAtTop();
const gesturesAfter = await gestures();
const fills = await writes("gap-fill");
// MEDIUM 2 (T386 stage 2): the head gap's drawn height per turn must match the rendered run's measured per-turn height (a turn is a
// user row plus its reply, so a per-display-unit average drew gaps about half true). Measure the gap element's px/turn and the rendered
// run's px/turn and compare. The run's figure is the estimator's own rule since PR E (ui/webview/turn-estimate.ts): the MEDIAN over the
// turns the window holds WHOLE, a visible user row to the next, each row its border box (offsetHeight); the rows before the first user
// row and after the last are turns the window does not hold whole and are not counted; at an even count the median is the lower middle
// turn. (The old rule, every row's height over the count of user rows, read the whole window as one turn when the window held one user
// row: the phone's 1.43M px gap.)
const gapPerTurn = await page.evaluate(() => { const g = document.querySelector("#content .tx-gap"); if (!g) return null; const lo = Number(g.dataset.lo), hi = Number(g.dataset.hi); return hi > lo ? g.offsetHeight / (hi - lo) : null; });
const runPerTurn = await page.evaluate(() => {
  const c = document.getElementById("content");
  const rows = Array.from(c.querySelectorAll("#content .turn")).filter((t) => !t.classList.contains("tx-spacer") && !t.classList.contains("tx-gap"));
  const isUser = (t) => t.classList.contains("turn-user") && t.style.display !== "none";
  const turns = []; let open = false, acc = 0;
  for (const t of rows) { if (isUser(t)) { if (open) turns.push(acc); open = true; acc = t.offsetHeight; continue; } if (open) acc += t.offsetHeight; }
  if (turns.length < 2) return null;
  turns.sort((a, b) => a - b);
  return turns[(turns.length - 1) >> 1];   // the estimator's median: at an even count the lower middle turn (turn-estimate.ts median)
});
// ROAD 3: a live tail while the reader is up in history: it lands at the tail, nothing pauses
const k = cfg.turns;
const tail = { type: "chatTail", id: cfg.sid, afterUuid: regionsFilled ? regionsFilled[regionsFilled.length - 1].last : filled.lastUuid, events: [
  { uuid: "11111111-2222-3333-4444-" + pad(2 * k), kind: "user", md: "question number " + k + " about the notes api", ts: new Date((cfg.base + 2 * k) * 1000).toISOString() },
  { uuid: "22222222-3333-4444-5555-" + pad(2 * k + 1), kind: "assistant", md: "Answer " + k + ": the handler reads the note by id and returns it.", ts: new Date((cfg.base + 2 * k + 1) * 1000).toISOString() }] };
await page.evaluate((f) => { window.postMessage(f, "*"); }, tail);
// the landing's event: the tail run's last key (the page's regions report, the source the assertion reads) becomes the posted second
// event's; the last RENDERED row is the reader's window far above the tail and never carries it (a wait on it was a 10-s sleep)
await page.waitForFunction((u) => { const rs = (typeof window.__rompRegions === "function" && window.__rompRegions()) || []; return rs.length > 0 && rs[rs.length - 1].kind === "run" && rs[rs.length - 1].last === u; }, tail.events[1].uuid, { timeout: 10000 }).catch(() => {});
// The tail's PAINT settles before anything reads the page. The wait above returns on the regions (the tail applies at once); the
// paint runs on the next animation frame and is not one frame's work: its layout moves the scrollTop under the reader with no
// write (the browser's own adjustment, which the page files as a scroll gesture), the scroll handler's edge check then re-windows
// the view (a spacer row, an anchor-restore write that puts the row back) and the write's echo lands a frame later. The reads
// below and road 2b's gesture baseline raced that chain: here it closes 45 ms after the landing and the reads take 49 ms, the same
// under a four-fold CPU throttle; a runner quick on evaluate round trips read the baseline first and counted two gestures across
// the below-fill, the paint's and the reader's jump (CI). The event is the page's scroll journal going quiet on its own frame
// clock: paint until a paint files no new scroll row (bounded).
const scrollRows = () => page.evaluate(() => window.__sent.filter((m) => m.what === "scrollgesture" || m.what === "scrollwrite" || m.what === "spacer" || m.what === "tailchange" || m.what === "tailmut").length);
for (let i = 0, prev = await scrollRows(); i < 20; i++) { await painted(); const n = await scrollRows(); if (n === prev) break; prev = n; }
const live = await state(); const regionsLive = await regions(); const rowLive = await rowAtTop();
// ROAD 2b (T386 stage 2, low 8): a fill BELOW the viewport. The head gap still stands above the filled run; a jump to the transcript
// top puts the reader at the gap's TOP edge, the edge met by scrolling DOWN, so the gap asks for its top page (lo 0), which fills in
// place with the reader's row held.
const belowBefore = await sentOf("loadTurns"); const belowGesturesBefore = await gestures();
await page.evaluate(() => { const c = document.getElementById("content"); c.scrollTop = 0; });
await painted();
await page.waitForFunction((n) => window.__sent.filter((m) => m.type === "loadTurns").length > n, belowBefore, { timeout: 10000 }).catch(() => {});
const belowAsks = await page.evaluate((n) => window.__sent.filter((m) => m.type === "loadTurns").slice(n).map((m) => ({ lo: m.lo, hi: m.hi })), belowBefore);
const belowRowBefore = await rowAtTop();
await page.waitForFunction(() => { const rs = (typeof window.__rompRegions === "function" && window.__rompRegions()) || []; return rs.length > 0 && rs[0].kind === "run" && rs[0].lo === 0; }, null, { timeout: 10000 }).catch(() => {});
await painted();
const belowRegions = await regions(); const belowRowAfter = await rowAtTop(); const belowGestures = await gestures();
process.stdout.write("RESULT:" + JSON.stringify({ boot: { regions: bootRegions, turns: boot.turns, atBottom: boot.atBottom, notice: boot.notice, strip: boot.strip }, turnsBefore, asks, gapsAsked, regionsAsked, rowBefore, rowAfter, gesturesBefore, gesturesAfter, fills,
  filled: { regions: regionsFilled, gaps: filled.gaps, turns: filled.turns, firstUuid: filled.firstUuid, lastUuid: filled.lastUuid, top: filled.top, notice: filled.notice, strip: filled.strip },
  gapPerTurn, runPerTurn,
  rowLive, below: { asks: belowAsks, regions: belowRegions, rowBefore: belowRowBefore, rowAfter: belowRowAfter, gestures: belowGestures, gesturesBefore: belowGesturesBefore },
  live: { regions: regionsLive, lastUuid: live.lastUuid, atBottom: live.atBottom, notice: live.notice, strip: live.strip, turns: live.turns, top: live.top } }) + "\n");
await browser.close();
"""


class ServedHistoryRegions(WindowLab):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._r = None

    def _result(self):
        if self._r is None:
            type(self)._r = self._drive(DRIVER, "regions", extra={"turns": TURNS})
            print("REGIONS:", json.dumps(self._r), file=sys.stderr)
        return self._r

    def test_the_boot_holds_the_tail_under_one_head_gap_and_asks_for_nothing(self):
        r = self._result()
        b = r["boot"]
        self.assertIsNotNone(r["boot"]["regions"] if "regions" in r["boot"] else r.get("trace1", {}).get("regions"), "the page holds no regions (the base has none: no runs and gaps, only the old window protocol)")
        self.assertTrue(b["atBottom"], "the page boots at the bottom of the tail: %r" % b)
        self.assertEqual([x["kind"] for x in b["regions"]], ["gap", "run"], "one gap, the head to the tail's start, then the tail run: %r" % b["regions"])
        self.assertEqual(b["regions"][0]["lo"], 0, "the gap starts at the head: %r" % b["regions"])
        self.assertGreater(b["regions"][0]["hi"], 0, "the tail does not start at the head (the transcript is longer than the wire tail): %r" % b["regions"])
        self.assertEqual(b["regions"][1]["lo"], b["regions"][0]["hi"], "the tail run starts where the gap ends")
        self.assertIsNone(b["regions"][1]["hi"], "the tail run is open-ended")
        self.assertEqual(r["turnsBefore"], 0, "no page ask before the reader reaches a gap")
        self.assertFalse(b["notice"] or b["strip"], "nothing shows at a plain boot: %r" % b)

    def test_a_gap_entering_the_viewport_asks_for_its_own_page_and_the_reply_fills_the_space_in_place(self):
        r = self._result()
        self.assertIsNotNone(r["boot"]["regions"], "the page holds no regions (the base has none: no runs and gaps, only the old window protocol)")
        tail_lo = r["boot"]["regions"][0]["hi"]
        self.assertEqual(len(r["asks"]), 1, "the gap met the viewport once and asked once: %r" % r["asks"])
        first = r["asks"][0]
        self.assertEqual(first["hi"], tail_lo, "the ask meets the gap at its bottom edge, the edge the reader scrolled up to: %r" % first)
        self.assertLessEqual(first["hi"] - first["lo"], 16, "one page-aligned span, not the whole gap: %r" % first)
        self.assertEqual(first["lo"] % 16, 0, "the span is aligned to the kernel's pages: %r" % first)
        f = r["filled"]
        self.assertEqual([x["kind"] for x in f["regions"]], ["gap", "run"], "the gap shrank rather than split (the run joins the tail): %r" % f["regions"])
        self.assertEqual(f["regions"][0]["hi"], first["lo"], "the gap ends where the new run starts: %r" % f["regions"])
        self.assertEqual(f["regions"][1]["lo"], first["lo"], "…and the tail run now starts there")
        self.assertGreater(f["regions"][-1]["n"], r["boot"]["regions"][-1]["n"], "the tail run grew by the page's events: %r → %r" % (r["boot"]["regions"][-1], f["regions"][-1]))
        self.assertIsNone(f["regions"][-1]["hi"], "the tail is still the tail, open-ended: %r" % f["regions"][-1])
        self.assertEqual(r["gesturesAfter"], r["gesturesBefore"], "the fill filed no scroll gesture for a move the reader never made")
        self.assertGreaterEqual(len(r["fills"]), 1, "the fill's one attributed write (gap-fill) was filed: %r" % r["fills"])
        self.assertIsNotNone(r["rowBefore"], "a row sat under the viewport top before the fill")
        self.assertEqual(r["rowAfter"]["uuid"], r["rowBefore"]["uuid"], "the reader's row is still the row under the viewport top: %r → %r" % (r["rowBefore"], r["rowAfter"]))
        self.assertLessEqual(abs(r["rowAfter"]["y"] - r["rowBefore"]["y"]), 2, "…at its offset: %r → %r" % (r["rowBefore"], r["rowAfter"]))
        self.assertFalse(f["notice"], "a scroll-driven fill shows no notice: the glyph inside the gap is its cue")

    def test_a_gap_met_from_above_asks_for_its_top_page_and_fills_below_the_viewport(self):
        # T386 stage 2, low 8: the head gap's TOP edge, met by scrolling down, asks for the top page (lo 0) and fills with the row held
        r = self._result()
        b = r["below"]
        self.assertGreaterEqual(len(b["asks"]), 1, "the gap met from above asked for no page: %r" % b)
        self.assertEqual(b["asks"][0]["lo"], 0, "the top edge asks for the head page (lo 0): %r" % b["asks"])
        self.assertLessEqual(b["asks"][0]["hi"] - b["asks"][0]["lo"], 16, "one page-aligned span, not the whole gap: %r" % b["asks"])
        self.assertEqual(b["regions"][0]["kind"], "run", "the head page filled into a run at the top: %r" % b["regions"])
        self.assertEqual(b["regions"][0]["lo"], 0, "…starting at the head: %r" % b["regions"])
        self.assertLessEqual(b["gestures"] - b["gesturesBefore"], 1, "the below-fill added no gesture beyond the reader's own jump into the gap: %r" % b)
        if b["rowBefore"] and b["rowAfter"]:
            self.assertEqual(b["rowAfter"]["uuid"], b["rowBefore"]["uuid"], "the reader's row held through the below-fill: %r → %r" % (b["rowBefore"], b["rowAfter"]))

    def test_the_head_gap_is_drawn_at_the_rendered_runs_per_turn_height(self):
        # MEDIUM 2: a gap's height counts TURNS times px-per-turn, not display units; within ten percent of the rendered run's per-turn
        # height, the median over the turns the window holds whole (the estimator's rule since PR E; the driver recomputes it off the rows)
        r = self._result()
        gpt, rpt = r["gapPerTurn"], r["runPerTurn"]
        self.assertIsNotNone(gpt, "the head gap was measured: %r" % r.get("filled"))
        self.assertIsNotNone(rpt, "the rendered run's per-turn height was measured (null when the window holds fewer than two complete turns)")
        self.assertLessEqual(abs(gpt - rpt) / rpt, 0.10, "the gap's px/turn (%r) is within ten percent of the run's (%r)" % (gpt, rpt))

    def test_a_live_tail_lands_while_the_reader_is_up_in_history_and_nothing_pauses(self):
        r = self._result()
        live = r["live"]
        self.assertIsNotNone(r["boot"]["regions"] if "regions" in r["boot"] else r.get("trace1", {}).get("regions"), "the page holds no regions (the base has none: no runs and gaps, only the old window protocol)")
        self.assertEqual(live["regions"][-1]["n"], r["filled"]["regions"][-1]["n"] + 2, "the live tail's two events landed at the end of the tail run (the rendered rows are the reader's window, far above): %r → %r" % (r["filled"]["regions"][-1], live["regions"][-1]))
        self.assertFalse(live["atBottom"], "the reader is still up in history: %r" % live)
        self.assertFalse(live["strip"], "no paused strip exists any more")
        self.assertFalse(live["notice"], "no notice for a live tail")
        self.assertEqual(r["rowLive"]["uuid"], r["rowAfter"]["uuid"], "the tail's arrival did not move the reader: the same row under the viewport top: %r → %r" % (r["rowAfter"], r["rowLive"]))
        self.assertLessEqual(abs(r["rowLive"]["y"] - r["rowAfter"]["y"]), 2, "…at its offset (the spacer estimate above may re-size, the row does not move): %r → %r" % (r["rowAfter"], r["rowLive"]))


# ── PR E (2026-09-19): compact mode streams by unit, and the head spacer holds under a window with one user row ─────────────
STREAM_DRIVER = DRIVER_HEAD + r"""
const painted = () => page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(() => setTimeout(r, 0)))));
// the kernel's wire settles first (its one status-only tail after the connect push), as the regions lab waits
await page.waitForFunction(() => (window.__bootFrames || []).some((f) => f.type === "chatTail" && f.source === "socket"), null, { timeout: 15000 }).catch(() => {});
await painted();
// the window's shape: the top spacer's height (its style, the page's own write), the units and rows it holds, its visible user rows
const shape = () => page.evaluate(() => {
  const c = document.getElementById("content"); const sp = document.querySelector("#content .tx-spacer-top");
  const units = Array.from(document.querySelectorAll("#content [data-unit]"));
  const rows = units.filter((n) => n.classList.contains("turn"));
  const users = rows.filter((n) => n.classList.contains("turn-user") && n.style.display !== "none").length;
  return { spacerTop: sp ? (parseFloat(sp.style.height) || 0) : 0, units: new Set(units.map((n) => n.dataset.unit)).size, rows: rows.length, users,
           atBottom: c.scrollHeight - c.scrollTop - c.clientHeight <= 2, sh: c.scrollHeight, top: c.scrollTop };
});
// the geometry the head spacer's bound derives from: the gap's turn span (the regions), the hidden run units above the window (the
// first rendered unit's index less the gap units), and the tallest row in the window
const geometry = () => page.evaluate(() => {
  const rs = (typeof window.__rompRegions === "function" && window.__rompRegions()) || [];
  const gaps = rs.filter((r) => r.kind === "gap");
  const units = Array.from(document.querySelectorAll("#content [data-unit]"));
  const rows = units.filter((n) => n.classList.contains("turn"));
  return { gapTurns: gaps.reduce((n, g) => n + (g.hi - g.lo), 0), hiddenUnits: units.length ? Number(units[0].dataset.unit) - gaps.length : null,
           maxRow: rows.reduce((m, n) => Math.max(m, n.offsetHeight), 0) };
});
const before = { ...(await shape()), ...(await geometry()) };
// every node of the window is marked; after a frame's paint the unmarked nodes are the ones the paint put there (the rebuild put them all)
const mark = () => page.evaluate(() => { for (const n of document.querySelectorAll("#content [data-unit]")) n.__prE = 1; });
const replaced = () => page.evaluate(() => Array.from(document.querySelectorAll("#content [data-unit]")).filter((n) => !n.__prE).length);
const spacerRows = () => page.evaluate(() => window.__sent.filter((m) => m.what === "spacer" && m.data && m.data.top).map((m) => m.data.top));
const rowsBefore = (await spacerRows()).length;
// the streamed reply follows the tail run's LAST event (its key, as the regions report it: the kernel's own notice rows carry a key, not a
// uuid), so nothing resident is truncated. The frames carry no status: a status replaces the session's whole status object, and one
// without the backend name empties the rewind pass's editable set on the next frame, which marks the view stale for a rebuild (the
// lab's first cut did that and read one rebuild for its own frame's shape).
const anchor = (await page.evaluate(() => { const rs = (typeof window.__rompRegions === "function" && window.__rompRegions()) || []; const t = rs[rs.length - 1]; return t && t.kind === "run" ? t.last : null; })) || (await state()).lastUuid;
const frames = [];
let text = "Streaming reply:";
for (let f = 0; f < 8; f++) {
  text += " more words land in the same bubble, frame " + f + ".";
  await mark();
  const frame = { type: "chatTail", id: cfg.sid, afterUuid: anchor,
                  events: [{ uuid: "aaaaaaaa-bbbb-cccc-dddd-000000000001", kind: "assistant", md: text, ts: new Date((cfg.base + 2 * cfg.turns + 5) * 1000).toISOString() }] };
  await page.evaluate((fr) => { window.postMessage(fr, "*"); }, frame);
  await painted();
  frames.push({ f, replaced: await replaced(), ...(await shape()) });
}
// a tool call lands after the reply: one unit in at the tail, one evicted at the top; then the reply after it grows again
await mark();
await page.evaluate((fr) => { window.postMessage(fr, "*"); }, { type: "chatTail", id: cfg.sid, afterUuid: "aaaaaaaa-bbbb-cccc-dddd-000000000001",
  events: [{ uuid: "aaaaaaaa-bbbb-cccc-dddd-000000000002", kind: "tool", name: "Bash", desc: "", input: JSON.stringify({ command: "true # a step" }), output: "ok", isError: false, ts: new Date((cfg.base + 2 * cfg.turns + 6) * 1000).toISOString() }] });
await painted();
frames.push({ f: "tool", replaced: await replaced(), ...(await shape()), ...(await geometry()) });
const spacers = await spacerRows();   // EVERY spacer row of the session, the boot build's and the first paint's included: the jump was between those two
// the window's edges and the frames the page received, for a failing run's message: what the window's first and last rows are, what
// landed from the socket during the stream (a kernel tail truncating the posted one would show here), the regions' tail run
const edges = await page.evaluate(() => { const rows = Array.from(document.querySelectorAll("#content [data-unit].turn")); const cls = (n) => n.className + "@" + n.dataset.unit; return { first: rows.slice(0, 3).map(cls), last: rows.slice(-3).map(cls), streamed: document.querySelectorAll('#content [data-uuid="aaaaaaaa-bbbb-cccc-dddd-000000000001"]').length }; });
const received = await page.evaluate(() => (window.__bootFrames || []).slice(-14));
const regionsNow = await page.evaluate(() => (typeof window.__rompRegions === "function" ? window.__rompRegions() : null));
const writers = await page.evaluate(() => window.__sent.filter((m) => m.what === "scrollwrite" && m.data).map((m) => m.data.writer));   // every attributed scroll write of the session, in order
process.stdout.write("RESULT:" + JSON.stringify({ engine: process.env.ROMP_LAB_ENGINE || "chromium", before, frames, spacers, edges, received, regions: regionsNow, pageEvents: pageEvents.slice(-12), writers }) + "\n");
await browser.close();
"""


class ServedCompactStream(WindowLab):
    """PR E (2026-09-19), on the served page in compact mode (the default): the transcript's last turn is one long agentic turn (a
    tool call, its result, a line of text, thirty-nine times), so the 80-unit tail window holds ONE user row, the shape the phone
    showed while a long turn streamed. Frames of a growing reply are posted as chatTail frames and two defects are measured:

    - the paint replaces the changed units alone (a growing reply is one unit; a tool landing is one unit in and one evicted at the
      top), where the compact rebuild replaced every node of the window on every frame;
    - the head spacer holds its height through the stream: the per-turn figure is the median over the turns the window holds whole,
      and a window with one user row holds none, so the gap keeps its default; the old figure read the whole window's height as one
      turn and the spacer grew about thirty-fold on the first streamed paint (24k to 1.43M px on the phone).

    Runs in Chromium; ROMP_LAB_ENGINE=webkit runs the same lab in WebKit, the phone's engine (the driver head reads it).
    Synthetic fixtures only (placeholder uuids, invented prose); hostname TESTHOST."""
    AGENTIC_TAIL_PAIRS = 38   # 1 + 38 x 2 + 1 = 78 events in the last turn; with the kernel's closing notice row after it, the 80-unit
                              # window opens on the previous turn's reply and holds ONE user row (two, should that notice ever go: still no
                              # second complete turn, which is the premise)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._r = None

    def _result(self):
        if self._r is None:
            type(self)._r = self._drive(STREAM_DRIVER, "stream", extra={"turns": TURNS})
            print("STREAM:", json.dumps(self._r), file=sys.stderr)
        return self._r

    def test_the_boot_window_holds_no_complete_turn_at_the_bottom(self):
        # the premise the two measurements rest on: the tail window is the agentic turn (one visible user row; two at most, should the
        # kernel's closing notice row go), so it holds no second complete turn, and the reader is at the bottom
        r = self._result()
        b = r["before"]
        self.assertTrue(b["atBottom"], "the page boots at the bottom: %r (page: %r)" % (b, r.get("pageEvents")))
        self.assertIn(b["users"], (1, 2), "one visible user row in the window (two at most): %r (edges %r)" % (b, r["edges"]))
        self.assertLess(b["users"] - 1, 2, "fewer than two complete turns: the estimator has no figure here")
        self.assertGreaterEqual(b["rows"], 60, "a window of many rows, so a rebuild would replace many nodes: %r" % b)
        self.assertGreater(b["spacerTop"], 0, "the head stands in a top spacer: %r" % b)

    def test_a_streamed_frame_replaces_the_changed_units_alone(self):
        # fix 1: eight frames of one growing reply replace one node each; a tool landing replaces its own node (the evicted one leaves);
        # the rebuild replaced every node of the window (about 80) on every frame
        r = self._result()
        frames = r["frames"]
        self.assertEqual(len(frames), 9, "eight reply frames and the tool's: %r" % [f["f"] for f in frames])
        for f in frames:
            self.assertGreaterEqual(f["replaced"], 1, "the paint put the changed unit in: %r" % f)
            self.assertLessEqual(f["replaced"], 3, "…and nothing else (a rebuild replaces the whole window, %r rows): %r (received %r; page %r)" % (r["before"]["rows"], f, r["received"][-10:], r.get("pageEvents")))
            self.assertTrue(f["atBottom"], "the reader follows the tail through the stream: %r" % f)
        self.assertEqual(r["edges"]["streamed"], 1, "the streamed reply stands in the window at the end: %r" % r["edges"])
        self.assertEqual(frames[-1]["units"], r["before"]["units"], "the tool's unit came in at the tail and one left at the top: the span held: %r -> %r" % (r["before"], frames[-1]))

    def test_the_head_spacer_holds_through_the_stream_when_the_window_has_no_complete_turn(self):
        # fix 2: the per-turn figure is the median over complete turns; this window has none, so the gap keeps its DEFAULT per turn and the
        # spacer is the gap at that default plus the hidden run units at the rows' average: at least the gap's default, at most the gap's
        # default plus the hidden units at the window's tallest row. The old figure (the window's height over its one user row) drew the
        # gap about 30x taller on the first paint after the boot build, which is the spacer row this checks as well: every re-size of the
        # session's head spacer, the boot's and the first paint's included, at most doubles it.
        r = self._result()
        default_px = int(re.search(r"export const DEFAULT_TURN_PX = (\d+);", (ROOT / "ui" / "webview" / "chat-regions.ts").read_text()).group(1))
        for where in (r["before"], r["frames"][-1]):
            self.assertGreater(where["gapTurns"], 0, "a head gap stands above the window: %r" % where)
            self.assertIsNotNone(where["hiddenUnits"]); self.assertGreater(where["maxRow"], 0)
            lo = where["gapTurns"] * default_px
            hi = lo + where["hiddenUnits"] * where["maxRow"]
            self.assertGreaterEqual(where["spacerTop"], lo - 1, "the head spacer is at least the gap at the default per turn: %r" % where)
            self.assertLessEqual(where["spacerTop"], hi + 1, "…and at most that plus the hidden run units at the tallest row (the gap was not drawn off the window's height per user row): %r" % where)
        tops = [r["before"]["spacerTop"]] + [f["spacerTop"] for f in r["frames"]]
        self.assertEqual(len(tops), 10)
        self.assertTrue(all(t > 0 for t in tops), "a top spacer stood through the stream: %r" % tops)
        self.assertLessEqual(max(tops) / min(tops), 2.0, "the head spacer's height held within 2x through the stream: %r" % tops)
        self.assertGreaterEqual(len(r["spacers"]), 1, "the boot build filed its spacer row: %r" % (r["spacers"],))
        # the loop below asserts on re-sizes AFTER the boot build (a before of 0 is the boot's own row); its population must be non-empty,
        # or the per-re-size bound is reported checked when nothing was checked (review round 0). The served page files at least one such
        # row: the rows' average measured off the boot build reaches the spacers in the first paint after it (the paint the frame-end take
        # asks for with the reader at the bottom, or the kernel's status-only tail's, whichever runs first)
        self.assertTrue(any(b > 0 for b, _ in r["spacers"]), "a re-size after the boot build filed a row with a non-zero before: %r" % (r["spacers"],))
        for before, after in r["spacers"]:
            if before > 0:
                self.assertLessEqual(after / before, 2.0, "no single spacer re-size doubled it: %r" % (r["spacers"],))



if __name__ == "__main__":
    unittest.main()
