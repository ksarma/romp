"""The served WINDOW LAB base (T366; T386 stage 2): a hermetic kernel over a synthetic transcript long enough that older history
stays on the server and the page's run is a tail, driven by Playwright through the driver head below (DRIVER_HEAD: the pad, sentOf,
state and frame hooks). The regions labs (test_history_regions_browser.py, test_landing_notice_browser.py)
build on WindowLab; stage 2 retired the paused strip and the detached client (the tail run is always resident and live, so no
window ever pauses live updates: plans/chat-history-regions.md Part B), so the one test here is the driver head's own: a misspelled
ROMP_LAB_ENGINE fails the lab instead of skipping it (UnknownEngineFailsLoudly; PR E review round 1b).
"""
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

import lab_dist

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
EXT = os.path.join(ROOT, "vscode-extension")
# the one skip the engine test shares with the lab: the extension's deps (Playwright) are absent, so no driver head can run
DEPS_ABSENT = "extension deps absent (npm ci not run here): the served guard needs them"
sys.path.insert(0, HERE)
import test_ship_reship_served as _lab   # noqa: E402  the lab kernel's environment (the module, not its classes)

SID = "aaaaaaaa-1111-2222-3333-444444444444"
TURNS = 320   # 640 events: past the wire tail, so older history stays on the server and the page's run is a tail
TOOL_TURN = 40   # the turn whose reply opens with four tool calls and ends with the words (T386's card-anchor road)
TOOL_TURN_TEXT = ("The four checks passed. Two questions for you: which bound do we keep for the retry curve, "
                  "and do we drop the second plot?")
AUQ_TURN = 100   # the turn whose reply asks the user a question and gets its answer (AskUserQuestion): the page anchors that row on
                 # the ANSWER's uuid, a tool_result line no event carries as its own uuid (T386 stage 2, round six: the fill's anchor road)
AUQ_RESULT_UUID = "66666666-7777-8888-9999-%012d" % (2 * AUQ_TURN)
AUQ_QUESTION = "Which bound do we keep for the retry curve?"


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


DRIVER_HEAD = r"""
import { createRequire } from "node:module";
import fs from "node:fs";
const require = createRequire(process.env.EXT_PKG);
const playwright = require("playwright");
const cfg = JSON.parse(fs.readFileSync(process.env.CFG, "utf8"));
// the engine: Chromium unless ROMP_LAB_ENGINE names another Playwright engine (webkit: the phone's engine, which has no scroll
// anchoring; the compact stream lab runs under both). An UNKNOWN name exits 1, a failure: exit 3 is the harness's "no playwright
// browser on this box", a skip unless ROMP_SERVED_TESTS_REQUIRE=1, and a misspelled engine once turned the whole lab into that
// silent skip (review round 1b); a launch that fails keeps 3 (the browser is missing, which is what 3 says)
const engineName = process.env.ROMP_LAB_ENGINE || "chromium";
const engine = playwright[engineName];
if (!engine) { console.error("unknown ROMP_LAB_ENGINE: " + engineName); process.exit(1); }
let browser;
try { browser = await engine.launch(cfg.launch || {}); }   // a lab may ask for classic scrollbars (the settle lab's drag road): Playwright hides them headless by default
catch (e) { console.error("browser-launch-failed: " + e); process.exit(3); }
const page = await browser.newPage({ viewport: { width: 1000, height: 600 } });
// every frame the page sends its kernel, by type: the window asks, the older asks and the re-attach ask are the evidence
await page.addInitScript(() => {
  const send = WebSocket.prototype.send;
  window.__sent = [];
  WebSocket.prototype.send = function (d) {
    try { const m = JSON.parse(d); if (m && m.type) window.__sent.push(m); } catch (e) { /* not a frame */ }
    return send.call(this, d);
  };
});
const pageEvents = [];   // the page's own errors, printed with a boot that fails (a lab's red should name the page's fault, not a bare timeout)
page.on("pageerror", (e) => pageEvents.push("pageerror:" + String(e).slice(0, 300)));
page.on("console", (m) => { if (m.type() === "error") pageEvents.push("console:" + m.text().slice(0, 300)); });
await page.addInitScript(() => {   // the session frames the page receives, for a boot that stalls: how many events each carried, and its tail start
  window.__bootFrames = [];
  window.addEventListener("message", (e) => { const m = e.data; if (m && (m.type === "session" || m.type === "chatTail" || m.type === "chatWindow" || m.type === "chatTurns")) window.__bootFrames.push({ type: m.type, id: String(m.id || "").slice(0, 8), n: Array.isArray(m.events) ? m.events.length : null, tailLo: m.tailLo, headKnown: m.headKnown, skeleton: m.skeleton, proto: m.proto, first: m.firstUuid, last: m.lastUuid, keys: Object.keys(m).slice(0, 14), source: e.source === window ? "page" : "socket" }); });
});
await page.goto(cfg.chat);
await page.waitForSelector("#tabs .tab, #tabs [data-sid]", { timeout: 20000 });
try { await page.waitForFunction(() => document.querySelectorAll("#content .turn[data-uuid]").length >= 40, null, { timeout: 30000 }); }
catch (e) {
  const seen = await page.evaluate(() => ({ turns: document.querySelectorAll("#content .turn[data-uuid]").length, units: document.querySelectorAll("#content [data-unit]").length, gaps: document.querySelectorAll("#content .tx-gap").length, regions: typeof window.__rompRegions === "function" ? window.__rompRegions() : null, sh: (document.getElementById("content") || {}).scrollHeight, frames: (window.__bootFrames || []).slice(0, 12), sent: (window.__sent || []).slice(0, 16).map((m) => m.type + (m.why ? ":" + m.why : "")) })).catch(() => null);
  console.error("boot did not reach forty rows: " + JSON.stringify(seen) + " page events: " + JSON.stringify(pageEvents.slice(0, 6)));
  throw e;
}
await page.waitForTimeout(500);
const state = () => page.evaluate(() => {
  const c = document.getElementById("content");
  const notice = document.querySelector(".tx-landing-notice");   // the ONE landing notice (T386 stage 2); the paused strip is retired
  // the run's rendered EVENT turns: a notice unit at the tail (an api-error note) carries a word, not a uuid
  const turns = Array.from(document.querySelectorAll("#content .turn[data-uuid]")).filter((t) => /^[0-9a-f-]{36}$/.test(t.dataset.uuid));
  return { top: c.scrollTop, sh: c.scrollHeight, ch: c.clientHeight,
           atBottom: c.scrollHeight - c.scrollTop - c.clientHeight <= 2,
           strip: !!document.getElementById("live-paused"),   // must stay absent: no window ever pauses live updates (T386 stage 2)
           notice: !!notice && getComputedStyle(notice).display !== "none", noticeText: notice ? notice.textContent : "",
           gaps: Array.from(document.querySelectorAll("#content .tx-gap")).map((g) => ({ lo: Number(g.dataset.lo), hi: Number(g.dataset.hi), h: g.offsetHeight, loading: g.classList.contains("tx-gap-loading") })),
           firstUuid: turns.length ? turns[0].dataset.uuid : null, lastUuid: turns.length ? turns[turns.length - 1].dataset.uuid : null,
           turns: turns.length,
           frames: (window.__bootFrames || []).slice(-8),   // the last frames the page received (type, id, event count, tail start, source)
           sent: window.__sent.map((m) => m.type + (m.why ? ":" + m.why : "") + (m.what ? ":" + m.what + (m.data && m.data.writer ? ":" + m.data.writer : "") + (m.what === "regionask" && m.data ? ":nav=" + m.data.nav + ":reland=" + m.data.reland : "") : "")) };
});
const sentOf = (type) => page.evaluate((t) => window.__sent.filter((m) => m.type === t).length, type);
const boot = await state();
if (!boot.atBottom) { console.error("the page did not land at the bottom: " + JSON.stringify(boot)); process.exit(1); }
// OLDER events of the transcript itself (turns k0..k1, none resident: the page holds the tail), in the wire's shape, so a
// window around them does not overlap the run and the kernel can place any page ask that follows them
const pad = (n) => String(n).padStart(12, "0");
const older = (k0, k1) => Array.from({ length: k1 - k0 }, (_, i) => k0 + i).flatMap((k) => [
  { uuid: "11111111-2222-3333-4444-" + pad(2 * k), kind: "user", md: "question number " + k + " about the notes api", ts: new Date((cfg.base + 2 * k) * 1000).toISOString() },
  { uuid: "22222222-3333-4444-5555-" + pad(2 * k + 1), kind: "assistant", md: "Answer " + k + ": the handler reads the note by id and returns it.", ts: new Date((cfg.base + 2 * k + 1) * 1000).toISOString() }]);
"""

# road 1 and road 2 in one page: the unasked window first (the reader attached, above the bottom), then the deep link
class WindowLab(unittest.TestCase):
    """The boot: a hermetic kernel over a synthetic transcript longer than the wire tail, the real /chat page served
    from a copy of the built bundle. Subclassed by this module's tests and by the landing lab (T386,
    tests/test_landing_settles_browser.py); carries no tests of its own.

    AGENTIC_TAIL_PAIRS (PR E, 2026-09-19): a subclass may end the transcript's LAST turn with that many (Bash tool, assistant
    text) pairs before its closing text, so the resident tail is one long agentic turn: in compact mode each lone tool between
    two texts is a unit of its own, and the 80-unit tail window then holds a single user row (the shape the phone showed while a
    long turn streamed). Zero, the default, leaves the transcript as it was for every other lab."""
    maxDiff = None
    AGENTIC_TAIL_PAIRS = 0

    @classmethod
    def _skip(cls, why):
        if os.environ.get("ROMP_SERVED_TESTS_REQUIRE") == "1":
            raise AssertionError("ROMP_SERVED_TESTS_REQUIRE=1 but the served lab could not run: " + why)
        raise unittest.SkipTest(why)

    @classmethod
    def setUpClass(cls):
        if not os.path.isdir(os.path.join(EXT, "node_modules", "playwright")):
            cls._skip(DEPS_ABSENT)
        cls.lab = tempfile.mkdtemp(prefix="live-paused-window-")
        dist = os.path.join(cls.lab, "dist")
        lab_dist.copy_dist(dist)   # the checkout's ONE build of the bundles, copied under its lock (tests/lab_dist.py)
        cls.state = os.path.join(cls.lab, "xdg", "romp")
        cwd = os.path.join(cls.lab, "proj")
        for d in ("names", "sdk", "states"):
            os.makedirs(os.path.join(cls.state, d), exist_ok=True)
        os.makedirs(cwd, exist_ok=True)
        Path(cls.state, "session-hosts").write_text("off\n")   # a lab root of its own: no session host (T348)
        Path(cls.state, "names", SID).write_text("web\t%s\t\t\n" % cwd)
        Path(cls.state, "sdk", SID + ".json").write_text(json.dumps(
            {"sid": SID, "name": "web", "cwd": cwd, "mode": "auto", "effort": "high",
             "lastSid": SID, "alive": True, "model": "claude-fable-5-1", "liveModel": "Fable 5.1"}))
        Path(cls.state, "usage.json").write_text(json.dumps({"five_hour": {"pct": 100}, "seven_day": {"pct": 10}}))
        claude = os.path.join(cls.lab, "claude")
        proj = os.path.join(claude, "projects", re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(cwd)))
        os.makedirs(proj, exist_ok=True)
        # TURNS user/assistant pairs, one a second, ending in the past: past the wire tail, so the page holds a tail
        recs, prev = [], None
        base = 1789000000
        for k in range(TURNS):
            u = "11111111-2222-3333-4444-%012d" % (2 * k)
            a = "22222222-3333-4444-5555-%012d" % (2 * k + 1)
            tu = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(base + 2 * k))
            ta = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(base + 2 * k + 1))
            recs.append({"type": "user", "uuid": u, "parentUuid": prev, "timestamp": tu, "sessionId": SID,
                         "message": {"role": "user", "content": "question number %d about the notes api" % k}})
            text = "Answer %d: the handler reads the note by id and returns it." % k
            pa = u
            if k == TOOL_TURN:
                # one turn whose FIRST atoms are tool calls (four, like a card's anchor on a Bash) and whose words come last
                # (T386): a card anchored on the first atom must land the reader on the words, not on the tool group
                for i in range(4):
                    tu_id = "toolu_%03d_%d" % (k, i)
                    tuu = "44444444-5555-6666-7777-%012d" % (10 * k + i)
                    tru = "55555555-6666-7777-8888-%012d" % (10 * k + i)
                    recs.append({"type": "assistant", "uuid": tuu, "parentUuid": pa, "timestamp": ta, "sessionId": SID,
                                 "message": {"role": "assistant", "model": "claude-fable-5-1", "stop_reason": "tool_use",
                                             "content": [{"type": "tool_use", "id": tu_id, "name": "Bash", "input": {"command": "true # check %d" % i}}]}})
                    recs.append({"type": "user", "uuid": tru, "parentUuid": tuu, "timestamp": ta, "sessionId": SID,
                                 "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": tu_id, "content": "ok"}]},
                                 "toolUseResult": {"stdout": "ok", "stderr": "", "interrupted": False, "isImage": False}})
                    pa = tru
                text = TOOL_TURN_TEXT
            if k == AUQ_TURN:
                # one turn whose reply asks the user a question, answered: the answer is a tool_result line whose uuid the kernel
                # files on the tool event as resultUuid, and the page anchors the row on it (the timeline's deep-link anchor)
                tu_id = "toolu_auq_%03d" % k
                tuu = "44444444-5555-6666-7777-%012d" % (10 * k)
                recs.append({"type": "assistant", "uuid": tuu, "parentUuid": pa, "timestamp": ta, "sessionId": SID,
                             "message": {"role": "assistant", "model": "claude-fable-5-1", "stop_reason": "tool_use",
                                         "content": [{"type": "tool_use", "id": tu_id, "name": "AskUserQuestion",
                                                      "input": {"questions": [{"question": AUQ_QUESTION, "header": "Bound", "multiSelect": False,
                                                                               "options": [{"label": "upper", "description": "the upper bound"},
                                                                                           {"label": "lower", "description": "the lower bound"}]}]}}]}})
                recs.append({"type": "user", "uuid": AUQ_RESULT_UUID, "parentUuid": tuu, "timestamp": ta, "sessionId": SID,
                             "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": tu_id, "content": "User answered: upper"}]},
                             "toolUseResult": {"questions": [{"question": AUQ_QUESTION}], "answers": {AUQ_QUESTION: "upper"}}})
                pa = AUQ_RESULT_UUID
                text = "Upper it is: the retry curve keeps its upper bound."
            if k == TURNS - 1 and cls.AGENTIC_TAIL_PAIRS > 0:
                # the last turn's long agentic middle: a tool call, its result, a line of text, repeated (PR E; see the class docstring)
                for i in range(cls.AGENTIC_TAIL_PAIRS):
                    tu_id = "toolu_tail_%03d" % i
                    tuu = "77777777-8888-9999-aaaa-%012d" % (10 * k + i)
                    tru = "88888888-9999-aaaa-bbbb-%012d" % (10 * k + i)
                    txu = "99999999-aaaa-bbbb-cccc-%012d" % (10 * k + i)
                    recs.append({"type": "assistant", "uuid": tuu, "parentUuid": pa, "timestamp": ta, "sessionId": SID,
                                 "message": {"role": "assistant", "model": "claude-fable-5-1", "stop_reason": "tool_use",
                                             "content": [{"type": "tool_use", "id": tu_id, "name": "Bash", "input": {"command": "true # step %d" % i}}]}})
                    recs.append({"type": "user", "uuid": tru, "parentUuid": tuu, "timestamp": ta, "sessionId": SID,
                                 "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": tu_id, "content": "ok"}]},
                                 "toolUseResult": {"stdout": "ok", "stderr": "", "interrupted": False, "isImage": False}})
                    recs.append({"type": "assistant", "uuid": txu, "parentUuid": tru, "timestamp": ta, "sessionId": SID,
                                 "message": {"role": "assistant", "model": "claude-fable-5-1", "stop_reason": "end_turn",
                                             "content": [{"type": "text", "text": "Step %d checked: the handler still reads the note by id." % i}]}})
                    pa = txu
            recs.append({"type": "assistant", "uuid": a, "parentUuid": pa, "timestamp": ta, "sessionId": SID,
                         "message": {"role": "assistant", "model": "claude-fable-5-1", "stop_reason": "end_turn",
                                     "content": [{"type": "text", "text": text}]}})
            prev = a
        Path(proj, SID + ".jsonl").write_text("".join(json.dumps(r) + "\n" for r in recs))
        cls.transcript = os.path.join(proj, SID + ".jsonl")      # a lab that appends a live turn writes here (T386)
        cls.deep_uuid = "11111111-2222-3333-4444-%012d" % 20   # the eleventh question: far above the tail the page holds
        cls.deep_t = base + 20                                     # …and its time, as a card's focus frame carries it
        cls.tool_uuid = "44444444-5555-6666-7777-%012d" % (10 * TOOL_TURN)   # the tool turn's FIRST atom: a card's anchor (T386)
        cls.tool_t = base + 2 * TOOL_TURN + 1
        cls.tool_quote = "which bound do we keep for the retry curve"
        cls.auq_result_uuid = AUQ_RESULT_UUID                     # the answered question's row anchor (round six)
        cls.base = base
        cls.port = _free_port()
        cls.token = "testtok-livepaused"
        env = _lab.kernel_env(cls.lab, claude, dist, cls.port, cls.token)
        cls.klog = os.path.join(cls.lab, "kernel.log")
        cls.kernel = subprocess.Popen([os.path.join(BIN, "romp-kernel")],
                                      stdout=open(cls.klog, "w"), stderr=subprocess.STDOUT, env=env)
        import urllib.request
        for _ in range(120):
            try:
                urllib.request.urlopen("http://127.0.0.1:%d/healthz" % cls.port, timeout=1)
                break
            except Exception:
                time.sleep(0.5)
        else:
            cls.kernel.kill()
            cls._skip("hermetic kernel never served /healthz here")

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "kernel", None):
            cls.kernel.kill()
            cls.kernel.wait()
        shutil.rmtree(getattr(cls, "lab", ""), ignore_errors=True)

    def _drive(self, script, name, extra=None):
        # exit 3 below is the driver's "no browser" (the launch failed): a skip, or a failure under ROMP_SERVED_TESTS_REQUIRE=1. An unknown
        # engine NAME is not that and exits 1, so it reaches the assertion below with its stderr (review round 1b)
        cfg = os.path.join(self.lab, name + ".json")
        with open(cfg, "w") as f:
            json.dump({"chat": "http://127.0.0.1:%d/chat?token=%s" % (self.port, self.token), "sid": SID,
                       "deepUuid": self.deep_uuid, "deepT": self.deep_t, "base": self.base, "transcript": self.transcript,
                       "toolUuid": self.tool_uuid, "toolT": self.tool_t, "toolQuote": self.tool_quote,
                       "shots": os.environ.get("LIVE_PAUSED_SHOTS", ""), **(extra or {})}, f)
        driver = os.path.join(self.lab, name + ".mjs")
        with open(driver, "w") as f:
            f.write(script)
        p = subprocess.run(["node", driver], capture_output=True, text=True, timeout=240,
                           env=dict(os.environ, EXT_PKG=os.path.join(EXT, "package.json"), CFG=cfg))
        if p.returncode == 3:
            if os.environ.get("ROMP_SERVED_TESTS_REQUIRE") == "1":
                raise AssertionError("ROMP_SERVED_TESTS_REQUIRE=1 but no playwright browser to run the served lab")
            raise unittest.SkipTest("no playwright browser on this box — the served guard needs one (CI installs none)")
        klog = ""
        try:
            with open(self.klog) as f:
                klog = f.read()[-2500:]
        except OSError:
            pass
        self.assertEqual(p.returncode, 0, "driver failed:\n" + p.stdout[-3000:] + p.stderr[-3000:] + "\nkernel:\n" + klog)
        line = next((ln for ln in p.stdout.splitlines() if ln.startswith("RESULT:")), None)
        self.assertIsNotNone(line, "driver printed no result:\n" + p.stdout[-3000:])
        r = json.loads(line[len("RESULT:"):])
        if isinstance(r, dict):
            r["_klog"] = klog[-1500:]   # the kernel's own words for the run, beside the measure (a passing run's log is otherwise lost with the lab dir)
        return r


class UnknownEngineFailsLoudly(unittest.TestCase):
    """PR E review round 1b (fresh-4): a misspelled ROMP_LAB_ENGINE must FAIL the served lab, never skip it. The driver head exits 3 for a
    browser that will not launch, which _drive reads as "no playwright browser on this box" (a skip unless ROMP_SERVED_TESTS_REQUIRE=1);
    an unknown engine name once took the same exit, so `ROMP_LAB_ENGINE=Webkit` made every lab under it a silent skip and nothing checked
    in ever ran the WebKit leg the body's claims rest on. The head's engine lines run alone here (the head sliced before its launch), so
    this needs the extension's deps and no browser; the only skip is the deps-absent one, and a misspelled engine never skips."""

    def test_a_misspelled_engine_exits_one_and_names_itself(self):
        if not os.path.isdir(os.path.join(EXT, "node_modules", "playwright")):
            WindowLab._skip(DEPS_ABSENT)
        head = DRIVER_HEAD[:DRIVER_HEAD.index("let browser;")]
        lab = tempfile.mkdtemp(prefix="lab-engine-")
        try:
            cfg = os.path.join(lab, "cfg.json")
            Path(cfg).write_text("{}")
            driver = os.path.join(lab, "engine.mjs")
            Path(driver).write_text(head)
            p = subprocess.run(["node", driver], capture_output=True, text=True, timeout=120,
                               env=dict(os.environ, EXT_PKG=os.path.join(EXT, "package.json"), CFG=cfg, ROMP_LAB_ENGINE="Webkit"))
        finally:
            shutil.rmtree(lab, ignore_errors=True)
        self.assertEqual(p.returncode, 1, "an unknown engine is the lab's failure, never the no-browser skip (3):\n" + p.stdout[-1000:] + p.stderr[-2000:])
        self.assertIn("unknown ROMP_LAB_ENGINE: Webkit", p.stderr)


if __name__ == "__main__":
    unittest.main()
