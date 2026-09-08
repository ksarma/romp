#!/usr/bin/env python3
"""The API cell's hover History section, driven in a real browser (the user 2026-09-08).

The shell page is kernel-served HTML with inline CSS and JS, so it has no jsdom harness: the source pins
(ui/webview/api-health-hover.test.ts) hold the SHAPE and this module holds the BEHAVIOR. A scratch copy of
km._landing() is served from a temp directory over plain HTTP by a handler that also answers GET /api-health
with a synthetic signal (switchable between variants through /variant/<name>, so one page load exercises a
storm, a quiet tail across a restart, an empty signal and two buckets); everything else 404s and the shell
socket is a shim that never opens, as in tests/test_api_health_browser.py. Playwright's chromium drives it:
a frame is handed to window.__rompApiHealth, the hover is opened by mouseenter / focus / Enter, and the
driver reports what the DOM did and how many reads the page made. Skips LOUDLY without the extension's node
deps or a browser (CI installs none).

Synthetic only: invented bucket labels, a fixed shape, times relative to the run so the same-day clock words
apply; no real data."""
import functools
import http.server
import json
import os
import re
import subprocess
import tempfile
import threading
import time
import unittest
from romp_load import load_source

# Hermetic state BEFORE the loads: they resolve their state root at import time, and only pytest runs
# conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
EXT = os.path.join(os.path.dirname(HERE), "vscode-extension")
km = load_source("romp_kernel_apih_hover_browser", os.path.join(BIN, "romp-kernel"))
sb = load_source("romp_sdk_backend_apih_hover_browser", os.path.join(BIN, "romp_sdk_backend.py"))

NOW = int(time.time())
BOOT = NOW - 600
RESTART = sb.API_HEALTH_RESTART_WHY
# invented labels in the digest form (12 hex characters), never real material: low-entropy digits, so nothing
# credential-shaped sits in this file, and every expected string below is built from these, never written out
KEY = "key:" + "0" * 11 + "1" + "|fable"
LOGIN = "login:" + "0" * 11 + "2" + "|fable"
AUTH, LAUTH = KEY.split("|")[0], LOGIN.split("|")[0]
WHY = "rate429 over 300 s = 0.40, n = 20 (attempts)"


def _win(requests, r429, r5xx, gave, sess, complete=True):
    return {"complete": complete, "requests": requests, "ok": requests, "rateLimited": 0, "overloaded": 0,
            "serverErrors": 0, "otherErrors": 0, "noStatus": 0, "gaveUp": gave, "retries": 0,
            "sessionsRetrying": sess, "turnsRetrying": sess, "rate429": r429, "rate5xx": r5xx}


def _bucket(key, state, since, why, windows):
    auth, fam = key.split("|")
    return {"auth": auth, "family": fam, "state": state, "stateSince": since, "why": why, "windows": windows,
            "evidence": None, "transitions": [], "lastError": None}


def _tr(t, key, frm, to, why="x"):
    auth, fam = key.split("|")
    return {"t": t, "bucket": key, "auth": auth, "family": fam, "from": frm, "to": to, "why": why, "evidence": None}


def _base(**over):
    d = {"schema": 1, "asOf": NOW, "uptimeS": 600.0, "complete": False, "seq": 65, "lastEventAt": NOW - 3,
         "rate429Basis": "attempts", "coverage": {"sidechainExcluded": True}, "config": {"windows": [60, 300, 900]},
         "bootId": "4242.%d" % BOOT, "bootAt": BOOT, "overall": {"state": "unknown", "worstBucket": None},
         "buckets": {}, "transitions": []}
    d.update(over)
    return d


STORM_WINS = {"60": _win(4, 0.5, 0.0, 0, 1), "300": _win(20, 0.4, 0.0, 1, 2), "900": _win(45, 0.2, 0.02, 1, 2, complete=False)}
PAYLOADS = {
    # one bucket in a storm; the boot filed thrashing -> unknown, so the tail carries its own restart row
    "storm": _base(overall={"state": "thrashing", "worstBucket": KEY},
                   buckets={KEY: _bucket(KEY, "thrashing", NOW - 300, WHY, STORM_WINS)},
                   transitions=[_tr(NOW - 3000, KEY, "unknown", "healthy"), _tr(NOW - 1200, KEY, "healthy", "thrashing"),
                                _tr(BOOT + 1, KEY, "thrashing", "unknown", RESTART), _tr(NOW - 300, KEY, "unknown", "thrashing")]),
    # the bucket was already unknown when the previous kernel stopped: the boot filed nothing, the tail crosses
    # bootAt with no restart row, and the section must insert the divider
    "quiet": _base(overall={"state": "healthy", "worstBucket": KEY},
                   buckets={KEY: _bucket(KEY, "healthy", NOW - 100, None, {"60": _win(12, 0.0, 0.0, 0, 0), "300": _win(30, 0.0, 0.0, 0, 0), "900": _win(30, 0.0, 0.0, 0, 0, complete=False)})},
                   transitions=[_tr(NOW - 4000, KEY, "unknown", "healthy"), _tr(NOW - 3500, KEY, "healthy", "unknown", "fewer than 10 attempts in every window"),
                                _tr(NOW - 100, KEY, "unknown", "healthy")]),
    # no traffic ever: no bucket, no tail
    "empty": _base(),
    # two buckets of one family: the head names the worst one and counts them
    "two": _base(overall={"state": "thrashing", "worstBucket": KEY},
                 buckets={KEY: _bucket(KEY, "thrashing", NOW - 300, WHY, STORM_WINS),
                          LOGIN: _bucket(LOGIN, "healthy", NOW - 500, None, {"60": _win(0, None, None, 0, 0), "300": _win(11, 0.0, 0.0, 0, 0), "900": _win(11, 0.0, 0.0, 0, 0, complete=False)})},
                 transitions=[_tr(NOW - 500, LOGIN, "unknown", "healthy"), _tr(NOW - 300, KEY, "unknown", "thrashing")]),
}


def _hm(t):
    return time.strftime("%H:%M", time.localtime(t))


def _hmd(t):
    """The section's stamp: HH:MM today, else 'MM-DD HH:MM' (the browser runs on this box's clock and zone)."""
    lt, today = time.localtime(t), time.localtime(NOW)
    hm = _hm(t)
    return hm if (lt.tm_year, lt.tm_yday) == (today.tm_year, today.tm_yday) else time.strftime("%m-%d ", lt) + hm


DRIVER = r"""
import { createRequire } from "node:module";
import fs from "node:fs";
const require = createRequire(process.env.EXT_PKG);
const { chromium } = require("playwright");
const cfg = JSON.parse(fs.readFileSync(process.env.CFG, "utf8"));
let browser;
try { browser = await chromium.launch(); }
catch (e) { console.error("browser-launch-failed: " + e); process.exit(3); }
const page = await browser.newPage({ viewport: { width: 1200, height: 800 } });
const R = { err: {}, pageErrors: [] };
page.on("pageerror", (e) => { R.pageErrors.push(String(e && e.message || e)); });
// the WebSocket shim: the page's sockets never open (no kernel behind the scratch page), without the real
// socket's close-and-redial noise
await page.addInitScript(() => {
  function Fake(url) { this.url = String(url); this.readyState = 0; this.sent = []; this.onopen = this.onmessage = this.onclose = this.onerror = null; }
  Fake.prototype.send = function () { throw new Error("not open"); };
  Fake.prototype.close = function () {};
  Fake.CONNECTING = 0; Fake.OPEN = 1; Fake.CLOSING = 2; Fake.CLOSED = 3;
  window.WebSocket = Fake;
});
await page.goto(cfg.url);
await page.waitForFunction(() => typeof window.__rompApiHealth === "function", null, { timeout: 20000 });
const step = async (name, fn) => { try { await fn(); } catch (e) { R.err[name] = String(e && e.stack || e); } };
const ev = (fn, arg) => page.evaluate(fn, arg);
const rows = () => ev(() => Array.from(document.querySelectorAll("#ah-tip .ah-hist .ah-hrow")).map((n) => ({
  k: (n.querySelector(".ru-tip-k") || {}).textContent || "", w: n.querySelector(".ah-hword") ? n.querySelector(".ah-hword").textContent : null,
  v: n.querySelector(".ru-tip-v") ? n.querySelector(".ru-tip-v").textContent : null, boot: n.classList.contains("ah-boot") })));
const head = () => ev(() => { const h = document.querySelector("#ah-tip .ah-hist");
  const q = (s) => { const n = h && h.querySelector(s); return n ? n.textContent : null; };
  return { word: q(".ah-head .ah-word"), dot: h && h.querySelector(".ah-head .ah-dot") ? h.querySelector(".ah-head .ah-dot").getAttribute("data-state") : null,
           since: q(".ah-since"), sub: q(".ah-hsub"), why: q(".ah-line.ru-tip-reset"), asOf: q(".ru-tip-name .ru-tip-reset"),
           line: q(".ah-line:not(.ru-tip-reset):not(.ah-err)"), err: q(".ah-err"), wait: !!(h && h.querySelector(".ah-wait")),
           names: Array.from(h ? h.querySelectorAll(".ru-tip-name span:first-child") : []).map((n) => n.textContent) }; });
const shown = () => ev(() => document.getElementById("ah-tip").style.display === "block");
const described = () => ev(() => document.getElementById("rail-api").getAttribute("aria-describedby"));
// the mouseenter and the look at what it painted are ONE task: the read fires on the show, so its answer cannot land
// before this returns, and the loader state read here is what the user sees before the answer (a separate round trip
// let the local server answer in between, and the dots were already rows)
const enter = () => ev(() => { const el = document.getElementById("rail-api"); el.dispatchEvent(new MouseEvent("mouseenter", { bubbles: false, clientX: el.getBoundingClientRect().left + 10 }));
  return { wait: !!document.querySelector("#ah-tip .ah-hist .ah-wait"), described: el.getAttribute("aria-describedby"), fetchN: window.__fetchN }; });
const leave = () => ev(() => { document.getElementById("rail-api").dispatchEvent(new MouseEvent("mouseleave")); });
const waitRows = () => page.waitForFunction(() => document.querySelectorAll("#ah-tip .ah-hist .ah-hrow").length > 0, null, { timeout: 8000 });
const waitSel = (s) => page.waitForFunction((s) => !!document.querySelector(s), s, { timeout: 8000 });
const variant = (v) => ev((v) => fetch("/variant/" + v).then((r) => r.text()), v);
const fetchN = () => ev(() => window.__fetchN);
const frame = (over) => Object.assign({ type: "apiHealth", state: "ok", cls: "", reason: "", text: "ok", waiting: 0, retrying: 0, blocked: 0, since: 0, tmux: 0, sessions: [], seq: 1 }, over || {});
// the reads are counted through a wrapper on the page's fetch; the real fetch still runs, so the count is of
// reads the server answered
await ev(() => { const real = window.fetch; window.__fetchN = 0; window.__realFetch = real;
  window.fetch = function (u) { if (String(u).indexOf("/api-health") === 0) window.__fetchN++; return real.apply(window, arguments); }; });
await ev((f) => { window.__rompApiHealth(f); }, frame());
await step("storm", async () => {
  // 1. the hover: the loader's dots first, the rows when the read lands; the cell is described by the tip
  const first = await enter();
  R.stormWaitFirst = first.wait; R.stormDescribed = first.described; R.stormFetchN0 = first.fetchN;
  await waitRows();
  R.storm = { head: await head(), rows: await rows(), fetchN: await fetchN(), shown: await shown() };
  await leave();
  R.stormHidden = !(await shown()); R.stormDescribedAfter = await described();
});
await step("quiet", async () => {
  // 2. the tail crosses bootAt with no restart row: the divider
  await variant("quiet"); await enter(); await waitRows();
  R.quiet = { head: await head(), rows: await rows() };
  await leave();
});
await step("empty", async () => {
  // 3. no bucket: the head says so, no rows
  await variant("empty"); await enter(); await waitSel("#ah-tip .ah-hist .ah-line");
  R.empty = { head: await head(), rows: await rows() };
  await leave();
});
await step("two", async () => {
  // 4. two buckets of one family: the head names the worst by family and auth and counts them
  await variant("two"); await enter(); await waitRows();
  R.two = { head: await head(), rows: await rows() };
  await leave();
});
await step("fail", async () => {
  // 5. a failed read is one loud line in place of the rows: a non-2xx, a rejected fetch, a malformed answer
  await ev(() => { window.fetch = () => Promise.resolve({ ok: false, status: 503 }); });
  await enter(); await waitSel("#ah-tip .ah-err");
  R.fail503 = { head: await head(), rows: await rows() };
  await leave();
  await ev(() => { window.fetch = () => Promise.reject(new Error("Failed to fetch")); });
  await enter(); await page.waitForFunction(() => /Failed to fetch/.test((document.querySelector("#ah-tip .ah-err") || {}).textContent || ""), null, { timeout: 8000 });
  R.failReject = { head: await head(), rows: await rows() };
  await leave();
  await ev(() => { window.fetch = () => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({}) }); });
  await enter(); await page.waitForFunction(() => /malformed/.test((document.querySelector("#ah-tip .ah-err") || {}).textContent || ""), null, { timeout: 8000 });
  R.failMalformed = { head: await head(), rows: await rows() };
  await leave();
  // the real reads come back, and the next hover replaces the failure with the rows
  await ev(() => { window.fetch = function (u) { if (String(u).indexOf("/api-health") === 0) window.__fetchN++; return window.__realFetch.apply(window, arguments); }; });
  await variant("storm"); await enter(); await waitRows();
  R.recovered = { head: await head(), rows: await rows() };
  await leave();
});
await step("focus", async () => {
  // 6. keyboard focus shows the hover as the pointer does; blur hides it
  await ev(() => { document.getElementById("rail-api").focus(); });
  R.focusShown = await shown(); R.focusDescribed = await described();
  await waitRows();
  await ev(() => { document.getElementById("rail-api").blur(); });
  R.blurHidden = !(await shown()); R.blurDescribed = await described();
});
await step("keyboard", async () => {
  // 7. Enter pins the detail with the section in it; Escape closes, focus returns to the cell, and the hover does
  //    NOT pop back from that refocus
  await ev(() => { document.getElementById("rail-api").focus(); });
  await page.keyboard.press("Enter");
  R.kbPinned = await ev(() => { const t = document.getElementById("ah-tip"); return t.style.display === "block" && t.classList.contains("ru-modal"); });
  await waitRows();
  R.kbRows = (await rows()).length; R.kbHead = await head();
  R.kbFetchBefore = await fetchN();
  // 8. a frame landing on the open detail re-reads the history (the world changed)
  await ev((f) => { window.__rompApiHealth(f); }, frame({ state: "degraded", cls: "529", text: "overloaded · 1 waiting", waiting: 1, blocked: 1, since: NOW_PLACEHOLDER, seq: 2 }));
  await page.waitForFunction((n) => window.__fetchN > n, R.kbFetchBefore, { timeout: 8000 });
  R.kbFetchAfter = await fetchN();
  await page.keyboard.press("Escape");
  R.escHidden = !(await shown());
  R.escFocusBack = await ev(() => document.activeElement === document.getElementById("rail-api"));
  await ev(() => new Promise((r) => setTimeout(r, 120)));    // a late answer or the refocus must not re-show it
  R.escStillHidden = !(await shown()); R.escDescribed = await described();
});
if (cfg.shots) await page.screenshot({ path: cfg.shots });
fs.writeSync(1, "RESULT:" + JSON.stringify(R) + "\n");
await browser.close();
process.exit(0);
""".replace("NOW_PLACEHOLDER", str(NOW - 30))


class _Lab(http.server.SimpleHTTPRequestHandler):
    """The scratch page's server: index.html from the temp dir, GET /api-health from PAYLOADS, /variant/<name>
    switches which one; everything else the shell asks for 404s."""
    variant = ["storm"]

    def log_message(self, *a):
        pass

    def _json(self, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/api-health":
            return self._json(PAYLOADS[self.variant[0]])
        if path.startswith("/variant/"):
            name = path.rsplit("/", 1)[1]
            if name in PAYLOADS:
                self.variant[0] = name
            return self._json({"variant": self.variant[0]})
        return super().do_GET()


class ServedHistory(unittest.TestCase):
    """One browser run over the scratch page; each test reads one facet of what it reported."""
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        if not os.path.isdir(os.path.join(EXT, "node_modules", "playwright")):
            raise unittest.SkipTest("extension deps absent (npm ci not run here): the served hover needs a browser")
        cls.lab = tempfile.mkdtemp(prefix="apih-hover-browser-")
        html = km._landing()
        with open(os.path.join(cls.lab, "index.html"), "w") as f:
            f.write(html if isinstance(html, str) else html.decode("utf-8"))
        _Lab.variant[0] = "storm"
        cls.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(_Lab, directory=cls.lab))
        cls.thr = threading.Thread(target=cls.srv.serve_forever, daemon=True)
        cls.thr.start()
        cfg = os.path.join(cls.lab, "cfg.json")
        with open(cfg, "w") as f:
            json.dump({"url": "http://127.0.0.1:%d/" % cls.srv.server_address[1],
                       "shots": os.environ.get("APIH_HOVER_SHOT", "")}, f)
        driver = os.path.join(cls.lab, "driver.mjs")
        with open(driver, "w") as f:
            f.write(DRIVER)
        p = subprocess.run(["node", driver], capture_output=True, text=True, timeout=180,
                           env=dict(os.environ, EXT_PKG=os.path.join(EXT, "package.json"), CFG=cfg))
        cls.srv.shutdown()
        if p.returncode == 3:
            raise unittest.SkipTest("no playwright browser on this box: the served hover needs one (CI installs none)")
        if p.returncode != 0:
            raise AssertionError("driver failed:\n" + p.stdout[-3000:] + p.stderr[-3000:])
        line = next((ln for ln in p.stdout.splitlines() if ln.startswith("RESULT:")), None)
        if line is None:
            raise AssertionError("driver printed no result:\n" + p.stdout[-3000:] + p.stderr[-3000:])
        cls.R = json.loads(line[len("RESULT:"):])

    def test_the_driver_hit_no_script_error(self):
        self.assertEqual(self.R["err"], {})
        self.assertEqual([e for e in self.R["pageErrors"] if "api" in e.lower() or "HIST" in e], [], self.R["pageErrors"])

    def test_the_hover_reads_the_route_once_shows_the_loader_first_and_describes_the_cell(self):
        R = self.R
        self.assertTrue(R["stormWaitFirst"], "the loader's dots stand in until the answer lands")
        self.assertEqual(R["stormFetchN0"], 1, "one read per show, fired on the show")
        self.assertEqual(R["stormDescribed"], "ah-tip")
        self.assertEqual(R["storm"]["fetchN"], 1)
        self.assertTrue(R["storm"]["shown"])
        self.assertFalse(R["storm"]["head"]["wait"], "the dots go when the rows arrive")
        self.assertTrue(R["stormHidden"], "mouseleave hides the hover")
        self.assertIsNone(R["stormDescribedAfter"], "and drops the description")

    def test_the_storm_reads_as_state_since_why_windows_and_the_tail_with_its_restart_row(self):
        h, rows = self.R["storm"]["head"], self.R["storm"]["rows"]
        self.assertEqual((h["word"], h["dot"]), ("thrashing", "thrashing"))
        self.assertEqual(h["since"], "since " + _hmd(NOW - 300))
        self.assertEqual(h["why"], WHY)
        self.assertIsNone(h["sub"], "one bucket: no bucket name, no count")
        self.assertEqual(h["asOf"], "as of " + time.strftime("%H:%M:%S", time.localtime(NOW)))
        self.assertEqual(h["names"], ["History", "State changes"])
        wins = rows[:3]
        self.assertEqual([r["k"] for r in wins], ["1 min", "5 min", "15 min · kernel up 10 min"],
                         "the third window outreaches the uptime and says so")
        self.assertEqual([r["v"] for r in wins],
                         ["4 attempts · 50% 429 · 0% 5xx · 0 gave up · 1 session retrying",
                          "20 attempts · 40% 429 · 0% 5xx · 1 gave up · 2 sessions retrying",
                          "45 attempts · 20% 429 · 2% 5xx · 1 gave up · 2 sessions retrying"])
        self.assertTrue(all(r["w"] is None and not r["boot"] for r in wins))
        tail = rows[3:]
        self.assertEqual([(r["k"], r["w"], r["v"], r["boot"]) for r in tail],
                         [(_hmd(NOW - 300), "thrashing", "5 min so far", False),
                          (_hmd(BOOT + 1), "unknown · kernel restarted", "5 min", False),
                          (_hmd(NOW - 1200), "thrashing", "10 min", False),
                          (_hmd(NOW - 3000), "healthy", "30 min", False)],
                         "newest first; each state held until the bucket's next change; the boot's own row names the restart, so no divider")

    def test_a_tail_crossing_boot_at_without_a_restart_row_gets_the_divider(self):
        h, rows = self.R["quiet"]["head"], self.R["quiet"]["rows"]
        self.assertEqual(h["word"], "healthy")
        self.assertIsNone(h["why"], "no reason line when the bucket has none")
        tail = rows[3:]
        self.assertEqual([(r["k"], r["w"], r["v"], r["boot"]) for r in tail],
                         [(_hmd(NOW - 100), "healthy", "2 min so far", False),
                          (_hmd(BOOT), "kernel restarted", None, True),
                          (_hmd(NOW - 3500), "unknown", "57 min", False),
                          (_hmd(NOW - 4000), "healthy", "8 min", False)])

    def test_no_bucket_says_so_in_place_of_the_rows(self):
        h, rows = self.R["empty"]["head"], self.R["empty"]["rows"]
        self.assertEqual(h["word"], "unknown")
        self.assertEqual(h["line"], "No API traffic seen since the kernel started at %s." % _hmd(BOOT))
        self.assertEqual(rows, [])
        self.assertIsNone(h["since"])

    def test_two_buckets_of_one_family_are_told_apart_by_auth_and_counted(self):
        h, rows = self.R["two"]["head"], self.R["two"]["rows"]
        self.assertEqual(h["word"], "thrashing")
        self.assertEqual(h["sub"], "fable · %s · worst of 2 buckets" % AUTH)
        tail = rows[3:]
        self.assertEqual([r["w"] for r in tail], ["fable · %s thrashing" % AUTH, "fable · %s healthy" % LAUTH])
        self.assertEqual([r["v"] for r in tail], ["5 min so far", "8 min so far"], "each bucket's current state is its own 'so far'")

    def test_a_failed_read_is_one_loud_line_and_never_the_previous_numbers(self):
        R = self.R
        self.assertEqual(R["fail503"]["head"]["err"], "Could not read the API history: HTTP 503")
        self.assertEqual(R["fail503"]["rows"], [], "the rows the last hover showed are gone")
        self.assertEqual(R["failReject"]["head"]["err"], "Could not read the API history: Failed to fetch")
        self.assertEqual(R["failReject"]["rows"], [])
        self.assertEqual(R["failMalformed"]["head"]["err"], "Could not read the API history: malformed answer")
        self.assertIsNone(R["fail503"]["head"]["asOf"], "no as-of stamp on a failure")
        self.assertEqual(R["recovered"]["head"]["word"], "thrashing", "the next successful read replaces the failure")
        self.assertIsNone(R["recovered"]["head"]["err"])

    def test_focus_shows_the_hover_and_blur_hides_it(self):
        R = self.R
        self.assertTrue(R["focusShown"])
        self.assertEqual(R["focusDescribed"], "ah-tip")
        self.assertTrue(R["blurHidden"])
        self.assertIsNone(R["blurDescribed"])

    def test_enter_pins_the_section_a_frame_re_reads_it_and_escape_does_not_re_pop_the_hover(self):
        R = self.R
        self.assertTrue(R["kbPinned"])
        self.assertGreater(R["kbRows"], 3)
        self.assertEqual(R["kbHead"]["word"], "thrashing")
        self.assertGreater(R["kbFetchAfter"], R["kbFetchBefore"], "a frame on the open detail re-reads the history")
        self.assertTrue(R["escHidden"])
        self.assertTrue(R["escFocusBack"], "focus returns to the cell")
        self.assertTrue(R["escStillHidden"], "the refocus did not pop the hover back")
        self.assertIsNone(R["escDescribed"])


if __name__ == "__main__":
    unittest.main()
