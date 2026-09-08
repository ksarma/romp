#!/usr/bin/env python3
"""The API cell's hover history (the user 2026-09-08, who wanted the cell's hover to carry some history the
way the spend hover does). The rail's API cell hover and its click detail gain a History section that the
shell reads from GET /api-health when they open: the signal's state with its since-time and reason, one row
per window, the newest transitions with how long each state held, and a kernel restart shown as its own row
or divider. The shell half is _LANDING_APIH_JS (ui/webview/api-health-hover.test.ts pins its source and
tests/test_api_health_hover_browser.py drives it in Chromium); this module holds the KERNEL half: the
payload the section reads, served through the real dispatcher on the credential the shell's fetch carries.

Rules pinned here: every field the section reads is in the payload; the transitions tail is bounded; a
restart files the row whose reason the section matches, and a bucket already unknown files nothing (the
section's bootAt divider covers that case, so the boundary is never hidden); the shell's cookie alone reads
the route with no Origin header, which is what a same-origin GET fetch sends; the apiHealth frame carries no
history and _api_health_push still sends nothing on an unchanged world, a route read in between included.

Synthetic only: a private synthetic sid, invented key material assembled at run time, a fixed epoch."""
import inspect
import io
import json
import os
import re
import tempfile
import time
import unittest
from pathlib import Path
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
DOCS = os.path.join(os.path.dirname(HERE), "docs")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the loads: they resolve their state root at import time, and only pytest runs
# conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
km = load_source("romp_kernel_apih_hover", os.path.join(BIN, "romp-kernel"))
sb = load_source("romp_sdk_backend_apih_hover", os.path.join(BIN, "romp_sdk_backend.py"))

SID = "88888888-aaaa-4bbb-8ccc-000000000001"     # this module's private synthetic sid
KEY_MATERIAL = "test-key-material-" + "h" * 28    # invented; not shaped like any provider's key
T0 = 1_756_800_000.0                              # a fixed synthetic epoch: the derivation is pure in `now`
TOK = km.TOKEN
JS = km._LANDING_APIH_JS
HIST = JS[JS.index("// ── History"):JS.index("// full=false is the HOVER")]


def _storm(t_from, t_to, label, step=14.0):
    """Attempts every `step` seconds, two of every five a 429 retry: 40%, past every enter threshold."""
    out, t, i = [], t_from, 0
    while t < t_to:
        is429 = (i % 5) in (3, 4)
        out.append(sb.AhEvent(t, label, "fable", "retry" if is429 else "ok", "429" if is429 else "ok",
                              429 if is429 else None, SID, i // 20))
        t += step
        i += 1
    return out


def _label(ah):
    return sb.api_health_auth_label("ANTHROPIC_API_KEY", salt=ah.salt(), work_key=KEY_MATERIAL, launched_keyed=True)


def _serve_get(path, headers=None):
    """Drive the REAL do_GET dispatcher over a fake socket and return (status, body): the route's gate and
    its body are what the shell's fetch meets, so the test asks the handler rather than the source."""
    h = km.Handler.__new__(km.Handler)
    h.client_address = ("127.0.0.1", 0)
    h.headers = dict(headers or {})
    h.path = path
    h.command = "GET"
    h.request_version = "HTTP/1.1"
    h.wfile = io.BytesIO()
    h.rfile = io.BytesIO()
    h.close_connection = True
    captured = {}
    h.send_response = lambda code, *a: captured.__setitem__("status", code)
    h.send_header = lambda k, v: None
    h.end_headers = lambda: None
    h.log_message = lambda *a: None
    h.do_GET()
    return captured.get("status"), h.wfile.getvalue().decode("utf-8", "replace")


class _Backend:
    """A stand-in SDK backend over a REAL aggregator on a scratch state dir, one storm in its ring."""

    def __init__(self, storm=True):
        self.ah = sb.ApiHealth(tempfile.mkdtemp())
        self.label = _label(self.ah)
        if storm:
            now = time.time()
            for e in _storm(now - 600, now, self.label):
                self.ah._push(e)

    def api_health_snapshot(self, now=None, uptime_s=None):
        out = self.ah.snapshot(now, uptime_s=uptime_s)
        out["coverage"].update({"sdkSessionsLive": 1, "inTurn": 1, "retrying": 1})
        return out


class Payload(unittest.TestCase):
    """What the section reads, from the aggregator's own snapshot."""

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.ah = sb.ApiHealth(self.d)
        self.label = _label(self.ah)
        self.key = self.label + "|fable"

    def storm(self, lo, hi):
        for e in _storm(lo, hi, self.label):
            self.ah._push(e)

    def test_the_worst_bucket_names_a_bucket_that_carries_since_why_and_the_windows(self):
        self.storm(T0 - 600, T0)
        snap = self.ah.snapshot(T0, uptime_s=100)
        key = snap["overall"]["worstBucket"]
        self.assertEqual(key, self.key)
        self.assertIn(key, snap["buckets"], "the head row reads the bucket the roll-up names")
        b = snap["buckets"][key]
        self.assertEqual((snap["overall"]["state"], b["state"]), ("thrashing", "thrashing"))
        self.assertEqual(b["stateSince"], T0, "since: the read that entered the state")
        self.assertTrue(b["why"].startswith("rate429 over "), b["why"])
        self.assertEqual(snap["config"]["windows"], [60, 300, 900], "the rows come from the config in force")
        self.assertEqual(set(b["windows"]), {str(w) for w in snap["config"]["windows"]},
                         "windows are keyed by the config's seconds, as strings")
        for w in b["windows"].values():
            for k in ("requests", "rate429", "rate5xx", "gaveUp", "sessionsRetrying", "complete"):
                self.assertIn(k, w, k)
        self.assertIs(b["windows"]["60"]["complete"], True)
        self.assertIs(b["windows"]["900"]["complete"], False, "a window longer than the uptime says so")
        self.assertEqual((snap["asOf"], snap["uptimeS"]), (T0, 100.0), "the as-of stamp and the uptime the caveat names")

    def test_transition_rows_carry_the_fields_the_tail_renders_newest_last(self):
        self.storm(T0 - 600, T0)
        self.ah.snapshot(T0)
        snap = self.ah.snapshot(T0 + 2000)          # past retention: the episode closes
        rows = snap["transitions"]
        self.assertEqual([(r["from"], r["to"]) for r in rows], [("unknown", "thrashing"), ("thrashing", "unknown")])
        for r in rows:
            self.assertLessEqual({"t", "bucket", "auth", "family", "from", "to", "why"}, set(r))
            self.assertEqual(r["bucket"], self.key, "durations are computed per bucket, so every row names its own")
        self.assertEqual([r["t"] for r in rows], sorted(r["t"] for r in rows), "newest last; the section sorts newest first")

    def test_the_tail_is_bounded_however_many_transitions_pass(self):
        for i in range(40):                          # two transitions per cycle: unknown -> thrashing -> unknown
            base = T0 + i * 5000
            self.storm(base - 600, base)
            self.ah.snapshot(base)
            snap = self.ah.snapshot(base + 2000)
        self.assertEqual(len(snap["transitions"]), sb.API_HEALTH_TRANSITIONS_KEEP)
        self.assertEqual(snap["transitions"][-1]["t"], T0 + 39 * 5000 + 2000, "the newest is kept")
        m = re.search(r"var HIST_ROWS=(\d+);", JS)
        self.assertLessEqual(int(m.group(1)), sb.API_HEALTH_TRANSITIONS_KEEP, "the section shows a slice of the tail")
        self.assertEqual(int(m.group(1)), 6, "about six rows: what fits the hover")

    def test_a_restart_files_the_row_the_section_matches(self):
        self.storm(T0 - 600, T0)
        self.ah.snapshot(T0)
        ah2 = sb.ApiHealth(self.d, boot_at=T0 + 30)
        snap = ah2.snapshot(T0 + 31)
        row = snap["transitions"][-1]
        self.assertEqual((row["from"], row["to"], row["t"]), ("thrashing", "unknown", T0 + 30))
        self.assertEqual(row["why"], sb.API_HEALTH_RESTART_WHY)
        self.assertIn("var RESTART_WHY='%s';" % sb.API_HEALTH_RESTART_WHY, JS,
                      "the section matches the boot's reason byte for byte")
        self.assertIn("restart=r.why===RESTART_WHY", HIST)
        self.assertIn("(restart?' · kernel restarted':'')", HIST, "and names the restart on the row")
        self.assertEqual(snap["buckets"][self.key]["state"], "unknown", "no held pre-restart state")

    def test_a_bucket_already_unknown_files_nothing_so_the_divider_is_keyed_on_boot_at(self):
        self.storm(T0 - 600, T0)
        self.ah.snapshot(T0)
        self.ah.snapshot(T0 + 2000)                  # thrashing -> unknown before the stop
        n = len(self.ah.snapshot(T0 + 2001)["transitions"])
        ah2 = sb.ApiHealth(self.d, boot_at=T0 + 3000)
        snap = ah2.snapshot(T0 + 3001)
        self.assertEqual(len(snap["transitions"]), n, "already unknown: the boot files no row")
        # so the section cannot key the boundary on a row; it keys it on the payload's bootAt, which the route
        # stamps from the kernel's own boot identity
        self.assertIn("if(!crossed&&pre){crossed=true;", HIST)
        self.assertIn("if(!prevRestart){out+='<div class=\"ru-tip-row ah-hrow ah-boot\">", HIST)
        self.assertIn("<span class=ah-hword>kernel restarted</span>", HIST)
        self.assertIn('out["bootAt"] = int(_STARTED)', inspect.getsource(km.Handler.do_GET))


class Route(unittest.TestCase):
    """The route as the shell's fetch meets it: the real dispatcher, the credential the browser carries."""

    def setUp(self):
        self._saved = km._sdk
        self.be = _Backend()
        km._sdk = lambda: self.be

    def tearDown(self):
        km._sdk = self._saved

    def test_the_route_serves_every_field_the_section_reads(self):
        status, body = _serve_get("/api-health", {"X-Romp-Token": TOK})
        self.assertEqual(status, 200)
        out = json.loads(body)
        for k in ("asOf", "bootAt", "uptimeS", "config", "overall", "buckets", "transitions"):
            self.assertIn(k, out, k)
        self.assertIsInstance(out["config"]["windows"], list)
        self.assertIsInstance(out["bootAt"], int)
        key = out["overall"]["worstBucket"]
        self.assertIn(key, out["buckets"])
        b = out["buckets"][key]
        for k in ("state", "stateSince", "why", "windows", "family", "auth"):
            self.assertIn(k, b, k)
        self.assertEqual(set(b["windows"]), {str(w) for w in out["config"]["windows"]})

    def test_the_cookie_alone_reads_it_with_no_origin_header_the_shell_s_fetch_shape(self):
        # a same-origin GET fetch sends the romp_token cookie and NO Origin header; _origin_ok accepts an absent
        # Origin, so this is exactly the credential the shell's fetch('/api-health') carries (kernel.py's own
        # /usage/fleet read goes the same way). The header form the CLI uses is not what the shell sends.
        status, body = _serve_get("/api-health", {"Cookie": "romp_token=" + TOK})
        self.assertEqual(status, 200, body[:200])
        self.assertIn("buckets", body)
        status, body = _serve_get("/api-health", {"Cookie": "romp_token=" + TOK,
                                                  "Origin": "http://evil.example", "Host": "127.0.0.1:%d" % km.PORT})
        self.assertEqual(status, 403, "a cross-site page's cookie is refused")
        self.assertIn("fetch('/api-health',{cache:'no-store'})", JS)
        self.assertIn("fetch('/usage/fleet',{cache:'no-store'})", km._LANDING_USAGE_JS, "the same shape as the shell's other read")

    def test_a_missing_backend_is_a_loud_503_that_the_section_shows_as_its_failure_line(self):
        km._sdk = lambda: None
        status, body = _serve_get("/api-health", {"Cookie": "romp_token=" + TOK})
        self.assertEqual(status, 503)
        self.assertIn("error", json.loads(body))
        self.assertIn("if(!r.ok)throw new Error('HTTP '+r.status);", HIST, "a non-2xx is the failure, with its status")
        self.assertIn("HIST={error:String((e&&e.message)||e)};", HIST)
        self.assertIn("Could not read the API history: '+esc(HIST.error)", HIST)


class FrameUnchanged(unittest.TestCase):
    """The pushed frame carries no history, and the dedupe still sends nothing on an unchanged world."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self._state, self._alive, self._send, self._sdk = km.jd.STATE, km._alive_sessions, km._send_to_app, km._sdk
        km.jd.STATE = Path(self.td.name)
        km._alive_sessions = lambda now, tmux: []
        self.sent = []
        km._send_to_app = lambda app, m: self.sent.append((app, m))
        self.be = _Backend()
        km._sdk = lambda: self.be
        km._APIH_LAST[0] = None

    def tearDown(self):
        km.jd.STATE, km._alive_sessions, km._send_to_app, km._sdk = self._state, self._alive, self._send, self._sdk
        km._APIH_LAST[0] = None
        self.td.cleanup()

    def test_the_frame_carries_no_history_and_an_unchanged_world_sends_once_across_a_read(self):
        f1 = km._api_health_frame(10, {})
        km._api_health_push(f1)
        self.assertEqual(len(self.sent), 1)
        self.assertEqual(set(f1), {"type", "state", "cls", "reason", "text", "waiting", "retrying", "blocked",
                                   "since", "tmux", "sessions", "seq"}, "the documented keys, nothing added")
        for k in ("windows", "transitions", "buckets", "history", "overall"):
            self.assertNotIn(k, f1)
        # a hover reads the route in between (the read files a transition: the storm classifies)
        status, body = _serve_get("/api-health", {"Cookie": "romp_token=" + TOK})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["overall"]["state"], "thrashing", "the read observed the storm")
        f2 = km._api_health_frame(11, {})
        self.assertEqual(f1, f2, "the world the frame reads did not change")
        km._api_health_push(f2)
        self.assertEqual(len(self.sent), 1, "byte-identical: nothing sent")


class Docs(unittest.TestCase):
    def _section(self):
        doc = Path(DOCS, "reference.md").read_text()
        i = doc.index("### The bottom bar's indicator")
        return doc[i:doc.index("\n## ", i)]

    def test_the_reference_describes_the_section_from_the_payload_s_fields(self):
        sec = self._section()
        self.assertIn("**History**", sec)
        self.assertIn("`GET /api-health`", sec)
        for k in ("`overall.state`", "`stateSince`", "`why`", "`config.windows`", "`requests`", "`rate429`", "`rate5xx`",
                  "`gaveUp`", "`sessionsRetrying`", "`complete`", "`transitions`", "`asOf`", "`bootAt`"):
            self.assertIn(k, sec, k)
        self.assertIn("`kernel restarted`", sec)
        self.assertIn("never the previous numbers", sec)
        self.assertIn("Nothing polls", sec)

    def test_the_guide_tells_the_user_what_the_hover_shows(self):
        guide = Path(DOCS, "guide.md").read_text()
        self.assertIn("the history under it", guide)
        self.assertIn("last 1, 5 and 15 minutes", guide)
        self.assertIn("A kernel restart shows as its own line there", guide)

    def test_the_new_prose_carries_no_em_dash_and_no_fleet(self):
        for text, name in ((HIST, "the section's JS"), (self._section(), "the reference section")):
            self.assertNotIn("—", text, name)
            self.assertNotIn("fleet", text.lower(), name)
        css = km._landing()
        i = css.index(".ah-dot[data-state=thrashing]")
        self.assertNotIn("—", css[i:i + 400])


if __name__ == "__main__":
    unittest.main()
