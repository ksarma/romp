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
history and _api_health_push still sends nothing on an unchanged world, a route read in between included; the
backend's aggregator is seeded with the kernel's own boot clock, the one the route stamps as bootAt, so a bucket
the boot seeded has one since-time in the head, the divider and the boot's row (review round 2); that clock is the
float, to the millisecond, and the seed is clamped past the restored tail, so the restart row is the newest row
however close the previous kernel's last transition came to this start (review round 3); the aggregator owns that
stamp (truncated with floor, so its whole seconds are /version's started) and serves it as bootAt, so bootAt, the
seeded stateSince and the restart row are one number clamp or not, and a restored row with a null t is skipped, never
the whole history (review round 4).

Synthetic only: a private synthetic sid, invented key material assembled at run time, a fixed epoch."""
import inspect
import io
import json
import math
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
        self.ah = sb.ApiHealth(tempfile.mkdtemp(), boot_at=km._STARTED)     # seeded the way _sdk_locked seeds the live one
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
        self.assertIn("if(!sawRestart){out+='<div class=\"ru-tip-row ah-hrow ah-boot\">", HIST)
        self.assertIn("<span class=ah-hword>kernel restarted</span>", HIST)
        self.assertIn('"bootAt": self.boot_stamp', inspect.getsource(sb.ApiHealth.snapshot),
                      "bootAt is the aggregator's own seed stamp, served in its snapshot")
        self.assertNotIn('out["bootAt"]', inspect.getsource(km.Handler.do_GET), "the route stamps no second number")


class OneClock(unittest.TestCase):
    """The head's since, the boot's restart row and the route's bootAt read ONE clock, the kernel's own start
    (_STARTED), passed to the backend at construction. Before (review round 2): the aggregator seeded itself from
    its own clock, seconds after _STARTED (the backend is built after the boot's imports and warm-up), and the
    hover's head named one minute for a bucket the boot seeded while its divider named the other whenever that gap
    straddled a minute; the JS branch that keyed the head on the bucket's why being the restart reason was dead,
    because the read that serves the payload replaces that reason with its own. Round 3: the clock is the FLOAT, to
    the millisecond the payload's stamps carry (int() sat on the second boundary before the process started, under a
    row the previous kernel filed in that same second, and the tail read that row as current above the restart row),
    and the seed is clamped one millisecond past a restored row that is not before it, with one log line. Round 4: the
    aggregator owns the stamp (ApiHealth.boot_stamp: the start truncated to the millisecond with floor, or the clamp)
    and serves it as bootAt, so the route stamps nothing of its own: bootAt, the seeded stateSince and the restart row
    are one number in the clamp case too (the route's round(_STARTED, 3) was a second number there, and it named the
    next second when the start's fraction rounded up, so int(bootAt) == started failed for a fraction of boots)."""

    def setUp(self):
        self.d = tempfile.mkdtemp()
        ah = sb.ApiHealth(self.d)
        self.label = _label(ah)
        self.key = self.label + "|fable"
        for e in _storm(T0 - 600, T0, self.label):
            ah._push(e)
        ah.snapshot(T0)                              # thrashing, persisted: the next boot files thrashing -> unknown

    def _check(self, snap, boot):
        b = snap["buckets"][self.key]
        row = snap["transitions"][-1]
        self.assertEqual(b["stateSince"], boot, "the seeded since IS the boot clock")
        self.assertEqual((row["t"], row["from"], row["to"], row["why"]), (boot, "thrashing", "unknown", sb.API_HEALTH_RESTART_WHY),
                         "and so is the restart row's stamp")
        self.assertEqual(b["state"], "unknown")
        self.assertNotEqual(b["why"], sb.API_HEALTH_RESTART_WHY,
                            "the read that served this payload wrote its own reason over the seed's, so the section can key nothing on it")

    def test_the_aggregator_seeds_state_since_and_the_restart_row_from_boot_at(self):
        snap = sb.ApiHealth(self.d, boot_at=T0 + 30).snapshot(T0 + 31)
        self._check(snap, T0 + 30)

    def test_the_backend_hands_its_boot_at_to_the_aggregator_and_the_kernel_passes_its_start(self):
        be = sb.SdkBackend(self.d, "/bin/true", lambda *a, **k: None, boot_at=T0 + 30)
        self._check(be.api_health.snapshot(T0 + 31), T0 + 30)
        # the kernel's construction site passes _STARTED, the clock the route stamps as bootAt: the float, never
        # int() (review round 3); the route rounds it to the millisecond, the precision the aggregator stamps in
        src = inspect.getsource(km._sdk_locked)
        self.assertIn("boot_at=_STARTED)", src)
        self.assertNotIn("boot_at=int(_STARTED)", src)
        self.assertIn('"bootAt": self.boot_stamp', inspect.getsource(sb.ApiHealth.snapshot))
        self.assertNotIn('out["bootAt"]', inspect.getsource(km.Handler.do_GET))
        # and the section reads stateSince alone: no why-keyed branch, nothing for it to be dead on
        self.assertIn("var since=b?b.stateSince:0;", HIST)
        self.assertNotIn("b.why===RESTART_WHY", HIST)

    def test_the_route_serves_boot_at_state_since_and_the_restart_row_as_one_number(self):
        be = self._seeded(self.d, km._STARTED, [])              # seeded the way _sdk_locked seeds the live one
        out = self._route(be)
        b = out["buckets"][self.key]
        row = [r for r in out["transitions"] if r["why"] == sb.API_HEALTH_RESTART_WHY][-1]
        self.assertEqual(out["bootAt"], be.ah.boot_stamp, "the aggregator's own stamp, served as bootAt")
        self.assertLessEqual(out["bootAt"], km._STARTED)
        self.assertLess(km._STARTED - out["bootAt"], 0.001, "the kernel's start truncated to the millisecond")
        self.assertEqual(int(out["bootAt"]), int(km._STARTED),
                         "/version's started: the same start in whole seconds (the restored tail is years old: no clamp)")
        self.assertEqual(b["stateSince"], out["bootAt"], "head since and bootAt: one number")
        self.assertEqual(row["t"], out["bootAt"], "the restart row's stamp too")

    @staticmethod
    def _seeded(d, boot, lines):
        class _Seeded(_Backend):
            def __init__(inner):
                inner.ah = sb.ApiHealth(d, boot_at=boot, log=lines.append)
        return _Seeded()

    def _route(self, be):
        saved = km._sdk
        try:
            km._sdk = lambda: be
            status, body = _serve_get("/api-health", {"Cookie": "romp_token=" + TOK})
        finally:
            km._sdk = saved
        self.assertEqual(status, 200, body[:200])
        return json.loads(body)

    def test_a_same_second_race_reads_one_stamp_in_the_head_the_divider_and_the_restart_row(self):
        # the previous kernel's last read filed AFTER this kernel's start (it drains under SIGTERM while still serving
        # and the manager respawns at once, or the clock stepped): the seed is clamped past that row, and bootAt IS the
        # clamped stamp. Before (review round 4): the route stamped round(_STARTED, 3), so the head (stateSince) and the
        # restart row read the clamped stamp while the divider read bootAt, and with a minute boundary inside the gap
        # the head named one minute and the divider the one before
        d, key = self._previous_kernel(km._STARTED + 0.2)
        lines = []
        be = self._seeded(d, km._STARTED, lines)
        out = self._route(be)
        b = out["buckets"][key]
        row = [r for r in out["transitions"] if r["why"] == sb.API_HEALTH_RESTART_WHY][-1]
        old = round(km._STARTED + 0.2, 3)
        self.assertEqual(out["bootAt"], be.ah.boot_stamp, "bootAt is the seed's own stamp")
        self.assertAlmostEqual(out["bootAt"], old + 0.001, delta=1e-6, msg="one millisecond past the previous kernel's row")
        self.assertEqual(b["stateSince"], out["bootAt"], "the head's since")
        self.assertEqual(row["t"], out["bootAt"], "the restart row")
        self.assertEqual(row["t"], max(r["t"] for r in out["transitions"]), "the newest row")
        self.assertIn(int(out["bootAt"]), (int(km._STARTED), int(km._STARTED) + 1),
                      "the clamp may cross the second; /version's started stays int(_STARTED)")
        self.assertEqual(len([ln for ln in lines if "not before this boot" in ln]), 1, lines)
        # the section reads the three from these fields and nothing else, so they show one time
        self.assertIn("var since=b?b.stateSince:0;", HIST)
        self.assertIn("boot=d.bootAt,", HIST)
        self.assertIn("<span class=ru-tip-k>'+hmd(boot)+'</span><span class=ah-hword>kernel restarted</span>", HIST)

    def test_the_stamp_is_the_start_truncated_to_the_millisecond_so_its_whole_seconds_are_versions_started(self):
        # floor, never round: a start at X.9996 rounded to (X+1).000 while /version's started is int(X.9996) = X, and
        # the int(bootAt) == started pins failed for the boots whose fraction was .9995 or more (review round 4). The
        # floor never lands on the next second either: a float one step below a whole second multiplies to more than
        # half an ulp below it, so the largest float under X+1 truncates to X.999
        for x in (T0, T0 + 0.4, T0 + 0.9994, T0 + 0.9995, T0 + 0.9996, T0 + 0.9999,
                  math.nextafter(T0 + 1, 0), math.nextafter(T0 + 2, 0), time.time()):
            ah = sb.ApiHealth(tempfile.mkdtemp(), boot_at=x)
            self.assertEqual(int(ah.boot_stamp), int(x), repr(x))
            self.assertLessEqual(ah.boot_stamp, x, repr(x))
            self.assertLess(x - ah.boot_stamp, 0.001, repr(x))
            self.assertEqual(ah.boot_stamp, round(ah.boot_stamp, 3), "at the millisecond")
            self.assertEqual(ah.snapshot(x + 1)["bootAt"], ah.boot_stamp, "served as bootAt")
        self.assertEqual(sb.ApiHealth(tempfile.mkdtemp(), boot_at=T0 + 0.9996).boot_stamp, T0 + 0.999)
        self.assertEqual(sb.ApiHealth(tempfile.mkdtemp(), boot_at=math.nextafter(T0 + 1, 0)).boot_stamp, T0 + 0.999)

    def _previous_kernel(self, last_t):
        """A state file as the previous kernel left it: its last read filed unknown -> thrashing at `last_t`."""
        d = tempfile.mkdtemp()
        ah = sb.ApiHealth(d)
        label = _label(ah)
        for e in _storm(last_t - 600, last_t, label):
            ah._push(e)
        ah.snapshot(last_t)
        return d, label + "|fable"

    def test_the_restart_row_is_the_newest_row_when_the_previous_kernel_filed_in_this_boot_s_second(self):
        # the previous kernel drains under SIGTERM while still serving, and an open card's re-read filed a transition
        # at T0 + 0.7; the manager respawned at once and this kernel's _STARTED is T0 + 0.9. int() of that is T0,
        # BEFORE the row, and a seed there sorted under it: the tail read the old kernel's thrashing as the current
        # state above the restart row while the head said unknown since the boot (review round 3)
        d, key = self._previous_kernel(T0 + 0.7)
        lines = []
        ah = sb.ApiHealth(d, boot_at=T0 + 0.9, log=lines.append)
        snap = ah.snapshot(T0 + 1.5)
        rows = snap["transitions"]
        self.assertEqual(rows[-1]["why"], sb.API_HEALTH_RESTART_WHY)
        self.assertEqual(ah.boot_stamp, T0 + 0.9, "the float boot, already at the millisecond")
        self.assertEqual(rows[-1]["t"], ah.boot_stamp, "the restart row at the float boot")
        self.assertEqual(snap["bootAt"], ah.boot_stamp, "served as bootAt")
        self.assertEqual(rows[-1]["t"], max(r["t"] for r in rows), "the newest row in the tail")
        self.assertAlmostEqual(rows[-2]["t"], T0 + 0.7, delta=1e-6)
        self.assertGreater(rows[-2]["t"], int(T0 + 0.9), "the int seed sat under this row")
        b = snap["buckets"][key]
        self.assertEqual(b["stateSince"], rows[-1]["t"], "the head's since and the row: one number")
        self.assertEqual([ln for ln in lines if "not before this boot" in ln], [], "nothing to clamp: the boot is past the row")

    def test_a_boot_not_past_the_restored_tail_seeds_one_millisecond_past_it_and_says_so_once(self):
        # the previous kernel filed AFTER this one's start (the two overlapped, or the clock stepped back): the seed
        # moves one millisecond past that row and the log says so once. Judged at the millisecond the tail is kept
        # in: a boot anywhere inside the row's own millisecond truncates to it and is clamped; one in the next
        # millisecond truncates to that and stamps there on its own (review round 4: floor, where round() sent a
        # boot 0.6 ms into the row's millisecond past it unreported)
        for boot, clamped in ((T0 + 0.65, True), (T0 + 0.7, True), (T0 + 0.7004, True), (T0 + 0.7009, True),
                              (T0 + 0.701, False), (T0 + 0.7015, False)):
            d, key = self._previous_kernel(T0 + 0.7)
            lines = []
            ah = sb.ApiHealth(d, boot_at=boot, log=lines.append)
            snap = ah.snapshot(T0 + 2)
            row, b = snap["transitions"][-1], snap["buckets"][key]
            self.assertEqual(row["why"], sb.API_HEALTH_RESTART_WHY, boot)
            self.assertAlmostEqual(row["t"], T0 + 0.701, delta=1e-6, msg=repr(boot))
            self.assertEqual(row["t"], max(r["t"] for r in snap["transitions"]), "the restart row stays the newest")
            self.assertEqual(b["stateSince"], row["t"], "one number: the head's since and the row")
            self.assertEqual(snap["bootAt"], row["t"], "and bootAt, clamp or not: the aggregator's own stamp")
            self.assertEqual(ah.boot_stamp, row["t"])
            said = [ln for ln in lines if "not before this boot" in ln]
            self.assertEqual(len(said), 1 if clamped else 0, (boot, lines))
            if clamped:
                self.assertIn("%.3f" % (T0 + 0.7), said[0])


class StateFileRows(unittest.TestCase):
    """A restored row the seed cannot stamp is skipped and counted, and never costs the other rows (review round 4:
    the seed's max over the restored stamps met a null t that _row_ok had passed, raised, and the outer guard dropped
    every bucket and transition the file held, with the file's other rows sound)."""

    def test_a_row_with_a_null_or_missing_t_is_skipped_and_the_rest_of_the_history_kept(self):
        d = tempfile.mkdtemp()
        ah = sb.ApiHealth(d)
        label = _label(ah)
        key = label + "|fable"
        for e in _storm(T0 - 600, T0, label):
            ah._push(e)
        ah.snapshot(T0)                                        # unknown -> thrashing at T0, persisted
        p = Path(d, sb.API_HEALTH_STATE_FILE)
        doc = json.loads(p.read_text())
        good = list(doc["transitions"])
        self.assertEqual([(r["from"], r["to"], r["t"]) for r in good], [("unknown", "thrashing", T0)])
        # a hand-edited file, or a row from a build that wrote t differently: null, missing, a string, a bool, NaN
        bad = [dict(good[0], t=None), {k: v for k, v in good[0].items() if k != "t"}, dict(good[0], t="%.3f" % (T0 + 1)),
               dict(good[0], t=True), dict(good[0], t=float("nan"))]
        doc["transitions"] = [bad[0], good[0], bad[1], bad[2]]
        doc["buckets"][key]["transitions"] = [bad[3], good[0], bad[4]]
        p.write_text(json.dumps(doc))
        lines = []
        ah2 = sb.ApiHealth(d, boot_at=T0 + 10, log=lines.append)
        snap = ah2.snapshot(T0 + 11)
        self.assertEqual([ln for ln in lines if "unreadable" in ln], [], "the file is readable; five ROWS are not")
        skipped = [ln for ln in lines if "malformed row(s) skipped" in ln]
        self.assertEqual(len(skipped), 1, lines)
        self.assertIn("5 malformed", skipped[0])
        self.assertEqual(ah2.boot_stamp, T0 + 10, "nothing to clamp: every row the seed could stamp is before the boot")
        self.assertEqual(snap["bootAt"], T0 + 10)
        self.assertEqual([(r["from"], r["to"], r["t"]) for r in snap["transitions"]],
                         [("unknown", "thrashing", T0), ("thrashing", "unknown", T0 + 10)],
                         "the sound row kept, the restart row filed after it")
        b = snap["buckets"][key]
        self.assertEqual((b["state"], b["stateSince"]), ("unknown", T0 + 10), "the bucket came back")
        self.assertEqual([r["t"] for r in b["transitions"]], [T0, T0 + 10], "its own tail too")
        for r in bad:
            self.assertFalse(sb.ApiHealth._row_ok(r), r)
        self.assertTrue(sb.ApiHealth._row_ok(good[0]))
        self.assertTrue(sb.ApiHealth._row_ok(dict(good[0], t=int(T0))), "an int stamp is a number")

    def test_an_int_t_past_float_range_is_skipped_as_one_row_and_the_rest_of_the_history_kept(self):
        """Review round 5: math.isfinite converts an int to float first and raises OverflowError past about 309
        digits, and json.loads reads a 400-digit integer literal as such an int (1e400 reads as inf, which the finite
        check already rejects). The raise left _row_ok for _seed's outer guard, which dropped every restored row and
        bucket for the one row, against the promise that a bad row is skipped and counted and the other rows kept."""
        d = tempfile.mkdtemp()
        ah = sb.ApiHealth(d)
        label = _label(ah)
        key = label + "|fable"
        for e in _storm(T0 - 600, T0, label):
            ah._push(e)
        ah.snapshot(T0)                                        # unknown -> thrashing at T0, persisted
        p = Path(d, sb.API_HEALTH_STATE_FILE)
        doc = json.loads(p.read_text())
        good = list(doc["transitions"])
        self.assertEqual([(r["from"], r["to"], r["t"]) for r in good], [("unknown", "thrashing", T0)])
        huge = dict(good[0], t=10 ** 400)
        doc["transitions"] = [good[0], huge]
        p.write_text(json.dumps(doc))
        back = json.loads(p.read_text())["transitions"][1]["t"]
        self.assertIsInstance(back, int, "json reads the literal back as an int, not as inf")
        with self.assertRaises(OverflowError):
            float(back)
        lines = []
        ah2 = sb.ApiHealth(d, boot_at=T0 + 10, log=lines.append)
        snap = ah2.snapshot(T0 + 11)
        self.assertEqual([ln for ln in lines if "unreadable" in ln], [], "the file is readable; one ROW is not")
        skipped = [ln for ln in lines if "malformed row(s) skipped" in ln]
        self.assertEqual(len(skipped), 1, lines)
        self.assertIn("1 malformed", skipped[0])
        self.assertEqual(ah2.boot_stamp, T0 + 10, "nothing to clamp: the one row the seed could stamp is before the boot")
        self.assertEqual(snap["bootAt"], T0 + 10)
        self.assertEqual([(r["from"], r["to"], r["t"]) for r in snap["transitions"]],
                         [("unknown", "thrashing", T0), ("thrashing", "unknown", T0 + 10)],
                         "the sound row kept, the restart row filed after it")
        b = snap["buckets"][key]
        self.assertEqual((b["state"], b["stateSince"]), ("unknown", T0 + 10), "the bucket came back")
        self.assertEqual([r["t"] for r in b["transitions"]], [T0, T0 + 10], "its own tail too")
        self.assertFalse(sb.ApiHealth._row_ok(huge), "rejected as a row, no raise")
        self.assertFalse(sb.ApiHealth._row_ok(dict(good[0], t=-(10 ** 400))), "the negative side too")
        self.assertTrue(sb.ApiHealth._row_ok(dict(good[0], t=1e300)), "a large float the range holds is a number")


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
        self.assertIsInstance(out["bootAt"], float)
        self.assertEqual(out["bootAt"], round(out["bootAt"], 3), "to the millisecond, as every stamp in the payload")
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

    def test_the_reference_says_what_the_boot_stamp_is(self):
        # review round 4: the seeded-bucket sentence said `bootAt` is the kernel's own start, which the clamp case
        # contradicted, and the field said `started` is bootAt's whole seconds, which a rounded-up fraction broke
        doc = re.sub(r"\s+", " ", Path(DOCS, "reference.md").read_text())
        sec = re.sub(r"\s+", " ", self._section())
        self.assertIn("a bucket the boot seeded is `unknown` since `bootAt`: the boot time or, when an older kernel's "
                      "last row overlaps it, one millisecond past that row", sec)
        self.assertIn("`bootAt` is the boot's stamp in this signal: the kernel's start truncated to the millisecond", doc)
        self.assertIn("`/version`'s `started` is the whole-second boot time", doc)
        self.assertIn("the payload serves that stamp as `bootAt`, and the kernel log says when it was moved", doc)
        self.assertNotIn("`started` is its whole seconds", doc)
        self.assertNotIn("The boot's stamp is `bootAt` itself", doc)

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
