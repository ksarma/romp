#!/usr/bin/env python3
"""Automatic updates of THIS machine (the user 2026-08-09): at kernel boot, one async check reads
origin's newest release tag (git ls-remote — the remote's own refs, never the local tag list) and
compares it against the VERSION-file release. Modes (update-mode.json, default "ask" — ON out of
the box): ask = the shell's update banner offers it; auto = the kernel updates itself once per
discovered version; off = never checks. The update runs DETACHED (fetch + ff-only merge ONTO THE TAG + install.sh,
report to update-report.json, restart through the manager door only on success), and the outcome is
always filed as a sync notice — by the next boot, or by /update-check's poll on the still-running
kernel (fail loudly, never silent). Synthetic tags/paths only."""
import inspect
import io
import json
import os
import re
import subprocess
import tempfile
import threading
import time
import unittest
from unittest import mock
from romp_load import load_source
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
# Raw-run belt over conftest's suspenders — via the ENVIRONMENT, not a module attribute: loading the
# kernel re-executes romp_judge into the same module object, which RESETS a hand-assigned jd.STATE
# back to the env-derived default (verified 2026-08-09 — the webpush test's attribute rebind only
# holds under pytest because conftest moves XDG_STATE_HOME first). ROMP_STATE_DIR is the designed
# override and is read on every (re)execution, so it protects a bare `python3 tests/...` run too.
# Scoped to the loads and RESTORED right after (the modules capture STATE at exec): left set, it
# outranks conftest's XDG_STATE_HOME for every test module pytest imports after this one — which is
# exactly how this file's first cut broke two postal-bus tests three modules downstream.
_STATE_TD = tempfile.TemporaryDirectory()
_PREV_STATE_DIR = os.environ.get("ROMP_STATE_DIR")
os.environ["ROMP_STATE_DIR"] = _STATE_TD.name
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "test-token-DO-NOT-USE")
# A dead manager port: any update/converge path a test exercises unstubbed dials nothing real.
# (2026-08-14: the converge route, hit by this suite while genuine main-drift existed, posted an
# IMMEDIATE restart-all to the LIVE manager — every suite run bounced every kernel on the box.)
os.environ["ROMP_MANAGER_PORT"] = "1"
load_source("romp_event_model", os.path.join(BIN, "romp-event-model"))
jd = load_source("romp_judge", os.path.join(BIN, "romp-judge"))
km = load_source("romp_kernel_update", os.path.join(BIN, "romp-kernel"))
if _PREV_STATE_DIR is None:
    os.environ.pop("ROMP_STATE_DIR", None)
else:
    os.environ["ROMP_STATE_DIR"] = _PREV_STATE_DIR


def _serve_get(path, headers=None):
    """The real do_GET over a fake socket (the webpush-test harness): (status, body_bytes)."""
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
    return captured.get("status"), h.wfile.getvalue()


def _dials_only(port, dials=None, allow=()):
    """An http.client.HTTPConnection that refuses every port but `port` (and the ports in `allow`) at
    construction (an OSError, which a reader sees as a failed read) and records each (host, port) asked for in
    `dials`. The safety rail of the manager-port tests, which run with ROMP_MANAGER_PORT absent or empty on
    purpose: whatever the code under test does with the absence, nothing here reaches a manager the test did
    not start. On 2026-09-10 a review probe with the variable absent reached a development box's live manager
    through the drift door, which mapped the absence to the manager's default port, and every session on the
    box restarted. The patch lands on the http.client module itself, so the test's own urllib request to the
    Routes server goes through it too, as HTTPConnection("127.0.0.1:PORT") with port None: the port is read off
    the host then, and a test that drives the route passes its server's port in `allow`."""
    Real = km.http.client.HTTPConnection

    class Only(Real):
        def __init__(self, host, p=None, *a, **kw):
            eff = p
            if eff is None and ":" in str(host):
                eff = int(str(host).rpartition(":")[2])
            if dials is not None:
                dials.append((host, eff))
            if eff != port and eff not in allow:
                raise OSError("the test refuses a connection to port %r: only its fake manager on %r may be dialled" % (eff, port))
            super().__init__(host, p, *a, **kw)
    return Only


class _PeerWritesOnCompare(str):
    """A reason string whose ONE comparison against the fault latch runs the staged concurrent writer (the
    deterministic staging of tests/test_free_threaded_caches.py): the peer thread's call lands inside the
    compare-and-set window that the GIL never opens by itself. Armed once; the writer runs on the first
    compare only."""

    def __new__(cls, s, writer):
        o = str.__new__(cls, s)
        o._writer, o.armed = writer, False
        return o

    def __eq__(self, other):
        if self.armed:
            self.armed = False
            self._writer()
        return str.__eq__(self, other)

    __hash__ = str.__hash__


class Fresh(unittest.TestCase):
    """Every test starts with no update state: fresh STATE dir, empty avail/latch, empty notices."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.saved = jd.STATE
        jd.STATE = Path(self.td.name)
        km._UPDATE_AVAIL[0] = ""
        km._UPDATE_STATE[0] = ""
        # the drift door's in-flight flag and latched outcome (review round 5 of the confirm step): a test that
        # mocks _run_main_update and clicks the drift door takes the flag in the route and never runs the
        # converge's finally that clears it, so every later read would say running and skip the counts
        km._MAIN_CONVERGE_INFLIGHT[0] = False
        km._MAIN_CONVERGE_OUTCOME[0] = None
        with km._SYNC_LOCK:
            del km._SYNC_NOTICES[:]

    def tearDown(self):
        jd.STATE = self.saved
        self.td.cleanup()

    def notices(self):
        with km._SYNC_LOCK:
            return list(km._SYNC_NOTICES)


class Semver(unittest.TestCase):
    def test_parses_plain_releases_only(self):
        self.assertEqual(km._semver("v0.6.0"), (0, 6, 0))
        self.assertEqual(km._semver("1.12.3"), (1, 12, 3))
        for junk in ("", None, "v1.2", "v1.2.3-rc1", "release", "v1.2.3.4", "v1.2.x"):
            self.assertIsNone(km._semver(junk), junk)

    def test_orders_numerically_not_lexically(self):
        self.assertGreater(km._semver("v0.10.0"), km._semver("v0.9.9"))


class ModeStore(Fresh):
    def test_default_is_ask_the_check_is_on_out_of_the_box(self):
        self.assertEqual(km._update_mode(), "ask")

    def test_set_and_persist(self):
        km._set_update_mode("auto")
        self.assertEqual(km._update_mode(), "auto")
        km._set_update_mode("off")
        self.assertEqual(km._update_mode(), "off")

    def test_garbage_is_refused_at_both_ends(self):
        km._set_update_mode("yes please")               # setter drops it
        self.assertEqual(km._update_mode(), "ask")
        (jd.STATE / "update-mode.json").write_text(json.dumps({"mode": "banana"}))
        self.assertEqual(km._update_mode(), "ask", "an unknown stored mode reads as the default")


class LatestReleaseTag(unittest.TestCase):
    def _ls(self, stdout, rc=0, stderr=""):
        return mock.patch.object(km.subprocess, "run", return_value=subprocess.CompletedProcess(
            args=[], returncode=rc, stdout=stdout, stderr=stderr))

    def test_picks_the_numerically_newest_real_release(self):
        out = ("aaa\trefs/tags/v0.9.9\n"
               "bbb\trefs/tags/v0.10.0\n"
               "ccc\trefs/tags/v0.10.0^{}\n"          # peeled duplicate of the annotated tag
               "ddd\trefs/tags/nightly\n"             # not a release number
               "eee\trefs/tags/v0.2.0\n")
        with self._ls(out):
            self.assertEqual(km._latest_release_tag(), "v0.10.0")

    def test_no_release_tags_is_empty_not_an_error(self):
        with self._ls("aaa\trefs/tags/nightly\n"):
            self.assertEqual(km._latest_release_tag(), "")

    def test_git_failure_raises_so_the_caller_can_say_so(self):
        with self._ls("", rc=128, stderr="fatal: could not read from remote"):
            with self.assertRaises(RuntimeError):
                km._latest_release_tag()


class UpdateCheck(Fresh):
    def test_mode_off_never_even_asks_the_network(self):
        km._set_update_mode("off")
        with mock.patch.object(km, "_latest_release_tag", side_effect=AssertionError("must not run")):
            km._update_check()
        self.assertEqual(km._UPDATE_AVAIL[0], "")

    def test_newer_release_in_ask_mode_raises_the_banner_on_every_shell(self):
        sent = []
        with mock.patch.object(km, "_kernel_ver", return_value="v0.6.0+"), \
             mock.patch.object(km, "_latest_release_tag", return_value="v0.7.0"), \
             mock.patch.object(km, "_send_to_app", side_effect=lambda app, m: sent.append((app, m))):
            km._update_check()
        self.assertEqual(km._UPDATE_AVAIL[0], "v0.7.0")
        self.assertEqual(sent, [("shell", {"type": "updateAvail", "cur": "v0.6.0+", "tag": "v0.7.0",
                                           "boot": km._BOOT_ID})],
                         "the offer names the kernel life it came from, so a page can retire it")

    def test_same_or_older_release_is_silence(self):
        sent = []
        for latest in ("v0.6.0", "v0.5.9", ""):
            with mock.patch.object(km, "_kernel_ver", return_value="v0.6.0"), \
                 mock.patch.object(km, "_latest_release_tag", return_value=latest), \
                 mock.patch.object(km, "_send_to_app", side_effect=lambda app, m: sent.append(m)):
                km._update_check()
        self.assertEqual((km._UPDATE_AVAIL[0], sent), ("", []))

    def test_no_local_release_number_means_nothing_to_compare(self):
        with mock.patch.object(km, "_kernel_ver", return_value=None), \
             mock.patch.object(km, "_latest_release_tag", side_effect=AssertionError("must not run")):
            km._update_check()                        # no raise — the check just stands down

    def test_network_failure_is_a_stderr_note_never_a_crash(self):
        with mock.patch.object(km, "_kernel_ver", return_value="v0.6.0"), \
             mock.patch.object(km, "_latest_release_tag", side_effect=RuntimeError("no route to host")):
            km._update_check()
        self.assertEqual(km._UPDATE_AVAIL[0], "")

    def test_auto_mode_updates_once_per_discovered_version(self):
        ran = []
        with mock.patch.object(km, "_kernel_ver", return_value="v0.6.0"), \
             mock.patch.object(km, "_latest_release_tag", return_value="v0.7.0"), \
             mock.patch.object(km, "_run_update", side_effect=lambda tag: ran.append(tag) or True), \
             mock.patch.object(km, "_send_to_app"):
            km._set_update_mode("auto")
            km._update_check()
            self.assertEqual(ran, ["v0.7.0"])
            self.assertEqual(json.loads((jd.STATE / "update-attempted.json").read_text())["tag"], "v0.7.0")
            # a SECOND boot finding the same version does not loop the failed attempt — it says so
            # in the Log and falls back to offering the banner. (The in-memory discovery is
            # per-run, so a fresh boot starts empty — modeled by clearing it.)
            km._UPDATE_AVAIL[0] = ""
            km._update_check()
        self.assertEqual(ran, ["v0.7.0"], "one automatic attempt per version")
        self.assertTrue(any(not n["ok"] and "v0.7.0" in n["text"] for n in self.notices()))

    def test_rediscovering_the_same_release_mid_run_stays_quiet(self):
        # the 6h re-check re-finds a version for weeks — only a CHANGED discovery is new information
        sent = []
        with mock.patch.object(km, "_kernel_ver", return_value="v0.6.0"), \
             mock.patch.object(km, "_latest_release_tag", return_value="v0.7.0"), \
             mock.patch.object(km, "_send_to_app", side_effect=lambda app, m: sent.append(m)):
            km._update_check()
            km._update_check()
            km._update_check()
        self.assertEqual(len(sent), 1, "one banner push per discovered version, not one per pass")

    def test_a_newer_release_than_the_announced_one_reoffers(self):
        sent = []
        with mock.patch.object(km, "_kernel_ver", return_value="v0.6.0"), \
             mock.patch.object(km, "_send_to_app", side_effect=lambda app, m: sent.append(m)):
            with mock.patch.object(km, "_latest_release_tag", return_value="v0.7.0"):
                km._update_check()
            with mock.patch.object(km, "_latest_release_tag", return_value="v0.8.0"):
                km._update_check()
        self.assertEqual([m["tag"] for m in sent], ["v0.7.0", "v0.8.0"])
        self.assertEqual(km._UPDATE_AVAIL[0], "v0.8.0")

    def test_a_mode_flip_applies_on_the_next_pass_without_a_restart(self):
        # every pass re-reads the mode: turning the gear setting on mid-run must not need a boot
        sent = []
        km._set_update_mode("off")
        with mock.patch.object(km, "_kernel_ver", return_value="v0.6.0"), \
             mock.patch.object(km, "_send_to_app", side_effect=lambda app, m: sent.append(m)):
            with mock.patch.object(km, "_latest_release_tag", side_effect=AssertionError("off must not ask")):
                km._update_check()
            km._set_update_mode("ask")
            with mock.patch.object(km, "_latest_release_tag", return_value="v0.7.0"):
                km._update_check()
        self.assertEqual([m["tag"] for m in sent], ["v0.7.0"])


class CheckLoop(Fresh):
    def test_two_cadences_one_loop_and_a_crash_never_kills_the_thread(self):
        # The loop carries TWO watchers since the mesh-aware notice (the user 2026-08-14): the cheap
        # origin/main drift probe every round (minutes — a merge should be noticed promptly), the
        # release-tag check on its old six-hour stride. Either watcher dying must not kill the loop,
        # nor one watcher's crash starve the other.
        releases = []
        drifts = []
        converges = []
        naps = []

        # T230b: the loop is unhooked through ITS OWN seam - the stop event - never by patching the
        # process-global time.sleep (that patch, a counter raising SystemExit on call #2, was consumed
        # by leaked heartbeat threads sleeping in the window and hung five CI jobs for 15 silent
        # minutes each). The stub returns True on the 2nd wait (the event fired) and RAISES on any
        # later wait: a loop wired to wait but not to return would otherwise hang this very pin.
        class Stop:
            def wait(self, s):
                naps.append(s)
                if len(naps) == 2:
                    return True
                if len(naps) > 2:
                    raise AssertionError("the loop kept waiting after the stop event fired")
                return False

        def release_pass():
            releases.append(1)
            raise RuntimeError("boom")                 # a dying release check must not kill the loop…

        def drift_pass():
            drifts.append(1)
            if len(drifts) == 1:
                raise RuntimeError("boom")             # …nor a dying drift probe the NEXT drift probe

        def converge_pass():
            converges.append(1)                        # stubbed: the real one spawns node + rglobs ui/
            raise RuntimeError("boom")                 # …nor a dying dist converge any of them

        # T230c: FAST-FAIL if the loop ever regresses to the shared time.sleep. Without this guard the
        # test blocked in a real 300 s sleep until the 600 s CI backstop, whose os._exit then swallowed
        # this pin's own named failure (reproduced: `F` + the timeout dump, the message nowhere).
        # Main-thread-only, a plain function (never a recording mock a foreign sleeper could fill).
        main = threading.get_ident()

        def guard(s):
            if threading.get_ident() == main:
                raise AssertionError("the update-check loop must wait on its own seam, not the shared time.sleep")
        with mock.patch.object(km, "_update_check", side_effect=release_pass), \
             mock.patch.object(km, "_main_drift_check", side_effect=drift_pass), \
             mock.patch.object(km, "_dist_converge_check", side_effect=converge_pass), \
             mock.patch.object(km.time, "sleep", guard), \
             mock.patch.object(km, "_CHECK_LOOP_STOP", Stop()):
            km._update_check_loop()                    # RETURNS on the stop event
        self.assertEqual(len(releases), 1, "the six-hour stride: one release check across two fast rounds")
        self.assertEqual(len(drifts), 2, "the drift probe runs every round, surviving its own crash")
        self.assertEqual(len(converges), 2, "the dist converge runs every round, surviving its own crash")
        self.assertEqual(naps, [km._MAIN_CHECK_EVERY_S] * 2)
        self.assertEqual(km._UPDATE_CHECK_EVERY_S, 6 * 3600)
        self.assertEqual(km._MAIN_CHECK_EVERY_S, 300)


    def test_the_loop_never_sleeps_through_the_shared_time_sleep(self):
        # T230b (the user 2026-09-03, five hung CI jobs since 08-27): the loop's cadence wait must be a
        # loop-PRIVATE seam, never the process-global time.sleep. The sibling test above used to
        # patch km.time.sleep with a counter that raised SystemExit on call #2 — and any OTHER
        # thread sleeping in the window (test_heartbeat_thread leaks _heartbeat daemons that sleep
        # every 10s for the rest of the run) consumed a count; when a foreign thread drew #2,
        # threading swallowed its SystemExit and the loop spun forever on a no-op sleep: a silent
        # 15-minute job. Deterministic, no timing: a spinning foreign sleeper runs throughout; the
        # shared sleep is a PLAIN guard (never a recording mock the spinner would fill) that raises
        # only on the MAIN thread — so a loop reaching time.sleep fails in milliseconds, never hangs.
        # The seam patch deliberately has NO create=True (T230c): an absent or RENAMED seam then
        # fails as an AttributeError in under a second — still red-first and named — where create=True
        # would have minted a dead attribute and let the loop wait on the real Event to the backstop.
        import threading
        stop = threading.Event()
        main = threading.get_ident()

        def spinner():
            while not stop.is_set():
                time.sleep(0)
        t = threading.Thread(target=spinner, daemon=True)
        t.start()
        releases, drifts, naps = [], [], []

        def guard(s):
            if threading.get_ident() == main:
                raise AssertionError("the update-check loop must wait on its own seam, not the shared time.sleep")

        class Stub:
            def wait(self, s):
                naps.append(s)
                if len(naps) == 2:
                    return True                        # the stop event fires → the loop must RETURN
                if len(naps) > 2:
                    raise AssertionError("the loop kept waiting after the stop event fired")
                return False

        def release_pass():
            releases.append(1)
            raise RuntimeError("boom")

        def drift_pass():
            drifts.append(1)
        try:
            with mock.patch.object(km, "_update_check", side_effect=release_pass), \
                 mock.patch.object(km, "_main_drift_check", side_effect=drift_pass), \
                 mock.patch.object(km, "_dist_converge_check"), \
                 mock.patch.object(km.time, "sleep", guard), \
                 mock.patch.object(km, "_CHECK_LOOP_STOP", Stub()):
                km._update_check_loop()               # returns — the stop event is the loop's exit
        finally:
            stop.set()
            t.join(timeout=2)
        self.assertEqual(naps, [km._MAIN_CHECK_EVERY_S] * 2)
        self.assertEqual(len(releases), 1)
        self.assertEqual(len(drifts), 2)


class RunUpdate(Fresh):
    def test_detached_child_lands_on_the_tag_installs_reports_and_restarts_only_on_success(self):
        calls = []
        # The release remote is pinned: this test's Popen seam swallows every subprocess, the
        # resolver's `git remote` included, and the real checkout's layout (a maintainer's clone
        # has `upstream`) must not decide what a plain-install script says. The resolver has its
        # own tests (test_main_drift_notice.ReleaseRemote).
        with mock.patch.object(km.subprocess, "Popen", side_effect=lambda *a, **kw: calls.append((a, kw))), \
             mock.patch.object(km, "_release_remote", return_value="origin"), \
             mock.patch.dict(km.os.environ, {"ROMP_MANAGER_PORT": "7777"}):
            self.assertTrue(km._run_update("v0.7.0"))
        (a, kw), = calls
        self.assertEqual(a[0][:2], ["bash", "-c"])
        self.assertTrue(kw.get("start_new_session"), "install.sh + the restart take the kernel down — the child must outlive it")
        script = a[0][2]
        # EXACTLY the release commit, never the branch tip (the user 2026-08-09): the tag is fetched
        # by explicit refspec and fast-forwarded onto — an update to v0.7.0 means running v0.7.0
        self.assertIn("git fetch origin refs/tags/v0.7.0:refs/tags/v0.7.0", script)
        self.assertIn("git merge --ff-only v0.7.0", script)
        self.assertNotIn("git pull", script, "a pull takes whatever the branch has gained past the tag")
        self.assertIn("./install.sh", script)
        self.assertIn("update-report.json", script)
        # the restart rides the SUCCESS branch only: everything after `if` up to `else` has it,
        # the failure branch does not
        ok_branch, fail_branch = script.split("\nelse\n", 1)      # the OUTER else, column 0
        self.assertIn("/restart-all'", ok_branch,
                      "the self-update deploy bounces IMMEDIATELY (T160, the user's call from live "
                      "experience — the quiet window cost minutes per push; explicit "
                      "`romp refresh --quiet` still drains)")
        self.assertNotIn("when=quiet", ok_branch, "no drain default on the deploy path")
        self.assertIn("curl -fsS --max-time 60 -X POST 'http://127.0.0.1:", ok_branch,
                      "-f: a non-2xx answer from whatever holds the manager port is not a restart — the "
                      "report's `restarted` is read from curl's exit, never assumed; --max-time: a manager "
                      "that accepts and never answers ends the request instead of holding the latch with no "
                      "report (review find, 2026-09-08)")
        self.assertIn('"action": "self-update"', ok_branch,
                      "the script stamps restart-audit.jsonl at curl time, so the dying kernel's "
                      "restart-cuts row joins to a named reason instead of reading anonymous")
        self.assertNotIn("/restart-all", fail_branch)
        self.assertLess(ok_branch.index("/restart-all'"), ok_branch.index("update-report.json"),
                        "the report is written AFTER the restart request, with what the request did")
        self.assertEqual(km._UPDATE_STATE[0], "running")

    def test_no_manager_means_no_restart_leg(self):
        calls = []
        env = {k: v for k, v in km.os.environ.items() if k != "ROMP_MANAGER_PORT"}
        with mock.patch.object(km.subprocess, "Popen", side_effect=lambda *a, **kw: calls.append(a)), \
             mock.patch.dict(km.os.environ, env, clear=True):
            self.assertTrue(km._run_update("v0.7.0"))
        self.assertNotIn("/restart-all", calls[0][0][2])

    def test_refuses_junk_tags_and_reentry(self):
        with mock.patch.object(km.subprocess, "Popen", side_effect=AssertionError("must not spawn")):
            self.assertFalse(km._run_update("v1; rm -rf /"), "a tag is shell payload — semver or nothing")
        with mock.patch.object(km.subprocess, "Popen"):
            self.assertTrue(km._run_update("v0.7.0"))
            self.assertFalse(km._run_update("v0.7.0"), "one update at a time")


class HonestLaunch(Fresh):
    """A launch that did not happen is neither an update in flight nor an attempt."""

    def test_a_spawn_that_raises_gives_the_latch_back_and_says_so(self):
        # the raise used to escape _run_update with the in-flight latch still set: every later
        # update refused for the kernel's life, every banner waiting on a child that never existed
        with mock.patch.object(km.subprocess, "Popen", side_effect=OSError("resource temporarily unavailable")):
            self.assertFalse(km._run_update("v0.0.9"))
        self.assertEqual(km._UPDATE_STATE[0], "", "nothing is running")
        ns = self.notices()
        self.assertEqual(len(ns), 1)
        self.assertFalse(ns[0]["ok"])
        self.assertIn("v0.0.9", ns[0]["text"])
        self.assertIn("resource temporarily unavailable", ns[0]["text"])
        with mock.patch.object(km.subprocess, "Popen"):
            self.assertTrue(km._run_update("v0.0.9"), "the next launch is not refused")

    def _auto_pass(self, cur="v0.0.8"):
        with mock.patch.object(km, "_kernel_ver", return_value=cur), \
             mock.patch.object(km, "_latest_release_tag", return_value="v0.0.9"), \
             mock.patch.object(km, "_send_to_app"):
            km._set_update_mode("auto")
            km._update_check()

    def test_a_refused_auto_launch_is_not_an_attempt(self):
        # another update holds the in-flight latch. The pass must not spend the version's one
        # automatic try on a launch that never happened — the marker used to be written FIRST, and
        # the next pass then reported "ran once without landing" about a run that never ran — nor
        # stand on the discovery as acted-on
        km._UPDATE_STATE[0] = "running"
        with mock.patch.object(km.subprocess, "Popen", side_effect=AssertionError("must not spawn")):
            self._auto_pass()
        self.assertFalse((jd.STATE / "update-attempted.json").exists(), "a refusal is not an attempt")
        self.assertEqual(km._UPDATE_AVAIL[0], "", "the discovery re-arms — the next pass tries again")
        km._UPDATE_STATE[0] = ""                                  # the in-flight update ended
        ran = []
        with mock.patch.object(km, "_run_update", side_effect=lambda tag: ran.append(tag) or True):
            self._auto_pass()
        self.assertEqual(ran, ["v0.0.9"], "the retry the re-armed slot stands for")
        self.assertEqual(json.loads((jd.STATE / "update-attempted.json").read_text())["tag"], "v0.0.9",
                         "the marker records a launch that happened")

    def test_a_refusal_for_an_update_already_in_flight_keeps_that_updates_tag(self):
        # the pass found v0.0.9 while the update to v0.0.8 was still running: the launch is refused
        # (one at a time), and the re-arm must give the slot BACK to the in-flight update's tag, not
        # blank it: /update-check's `tag` names what is pending, and nothing about the running
        # update changed (review find, 2026-09-08). Once it ends, the next pass tries v0.0.9.
        km._UPDATE_STATE[0] = "running"
        km._UPDATE_AVAIL[0] = "v0.0.8"
        with mock.patch.object(km.subprocess, "Popen", side_effect=AssertionError("must not spawn")):
            self._auto_pass(cur="v0.0.7")
        self.assertEqual(km._UPDATE_AVAIL[0], "v0.0.8", "the in-flight update's tag stays pending")
        self.assertFalse((jd.STATE / "update-attempted.json").exists())
        km._UPDATE_STATE[0] = ""                                  # the in-flight update ended
        ran = []
        with mock.patch.object(km, "_run_update", side_effect=lambda tag: ran.append(tag) or True):
            self._auto_pass(cur="v0.0.7")
        self.assertEqual(ran, ["v0.0.9"], "the newer release is tried once the slot is free")

    def test_a_spawn_failure_in_auto_mode_leaves_no_marker_and_no_latch(self):
        with mock.patch.object(km.subprocess, "Popen", side_effect=OSError("no bash")):
            self._auto_pass()                                     # used to raise out of the pass
        self.assertFalse((jd.STATE / "update-attempted.json").exists())
        self.assertEqual((km._UPDATE_STATE[0], km._UPDATE_AVAIL[0]), ("", ""))
        self.assertTrue(any(not n["ok"] and "v0.0.9" in n["text"] for n in self.notices()))


class ReportConsumption(Fresh):
    def test_success_with_restart_files_once_and_archives(self):
        (jd.STATE / "update-report.json").write_text(json.dumps({"ok": True, "tag": "v0.7.0", "restarted": True}))
        rep = km._consume_update_report()
        self.assertTrue(rep["ok"])
        ns = self.notices()
        self.assertEqual(len(ns), 1)
        self.assertTrue(ns[0]["ok"])
        self.assertIn("v0.7.0", ns[0]["text"])
        self.assertFalse((jd.STATE / "update-report.json").exists(), "consumed — never re-filed")
        self.assertTrue((jd.STATE / "update-report-last.json").exists())
        self.assertIsNone(km._consume_update_report(), "second boot: nothing left to file")

    def test_failure_is_a_loud_not_ok_notice(self):
        (jd.STATE / "update-report.json").write_text(json.dumps({"ok": False, "tag": "v0.7.0",
                                                                 "why": "the pull or install failed"}))
        km._consume_update_report()
        ns = self.notices()
        self.assertEqual(len(ns), 1)
        self.assertFalse(ns[0]["ok"])
        self.assertIn("update.log", ns[0]["text"])

    def test_running_only_clears_the_inflight_latch(self):
        km._UPDATE_STATE[0] = "running"
        (jd.STATE / "update-report.json").write_text(json.dumps({"ok": False, "tag": "v0.7.0"}))
        km._consume_update_report(running_only=True)
        self.assertEqual(km._UPDATE_STATE[0], "")

    def test_a_boot_that_finds_a_non_object_report_does_not_crash(self):
        # main() calls _consume_update_report() bare: `.get` on a parsed null / [] / number raised
        # and took the boot down with it — after the rename, so the next boot came up with nothing
        p = jd.STATE / "update-report.json"
        p.write_text("[]")
        rep = km._consume_update_report()
        self.assertIsInstance(rep, dict)
        self.assertFalse(rep["ok"])
        self.assertFalse(p.exists())
        self.assertFalse((jd.STATE / "update-report-last.json").exists(), "not an outcome — not archived as one")
        aside = sorted(jd.STATE.glob("update-report.json.corrupt-*"))
        self.assertEqual(len(aside), 1, aside)
        self.assertEqual(aside[0].read_text(), "[]", "set aside as evidence, never deleted")
        ns = self.notices()
        self.assertEqual(len(ns), 1)
        self.assertFalse(ns[0]["ok"])
        self.assertEqual(ns[0].get("kind"), "refused", "a state file moved aside rings the refused bell, like every quarantine")
        self.assertIn(aside[0].name, ns[0]["text"])
        self.assertIsNone(km._consume_update_report(), "the next boot finds nothing to file")

    def test_a_second_unreadable_report_in_the_same_second_keeps_the_first(self):
        # the sidecar wears the quarantine convention (`.corrupt-<stamp>`, `-n` for a same-second
        # repeat): a plain `.bad` was one fixed name, so a second junk report overwrote the first's bytes
        p = jd.STATE / "update-report.json"
        real = km.time.strftime
        fixed = lambda fmt, *a: "20260101T000000Z" if fmt == "%Y%m%dT%H%M%SZ" else real(fmt, *a)
        with mock.patch.object(km.time, "strftime", side_effect=fixed):
            for junk in ("[]", "null"):
                p.write_text(junk)
                self.assertFalse(km._consume_update_report()["ok"])
        kept = {x.name: x.read_text() for x in jd.STATE.glob("update-report.json.corrupt-*")}
        self.assertEqual(kept, {"update-report.json.corrupt-20260101T000000Z": "[]",
                                "update-report.json.corrupt-20260101T000000Z-1": "null"})

    def test_the_quarantine_moves_only_the_file_whose_bytes_it_read(self):
        # the ledger and state-reader quarantines stat BEFORE the read and decline when the file is
        # no longer the one whose bytes failed (review find, 2026-09-08): here the child's real
        # report lands between the read of the junk and the move, and the move must NOT carry the
        # real report off as junk. The fresh bytes get their own (bounded) read instead.
        p = jd.STATE / "update-report.json"
        p.write_text("[]")
        real_loads, fresh = json.loads, {"ok": True, "tag": "v0.0.9", "restarted": False,
                                         "why": "the manager on port 7777 did not take the restart request"}
        def loads_then_publish(raw, *a, **kw):
            d = real_loads(raw, *a, **kw)
            if not isinstance(d, dict):                           # the junk was read: a peer publishes now
                p.write_text(json.dumps(fresh))
            return d
        with mock.patch.object(km.json, "loads", side_effect=loads_then_publish):
            km._UPDATE_STATE[0] = "running"
            rep = km._consume_update_report(running_only=True)
        self.assertEqual(rep, fresh, "the replacement is what gets consumed")
        self.assertEqual(list(jd.STATE.glob("update-report.json.corrupt-*")), [], "nothing was moved aside")
        self.assertTrue((jd.STATE / "update-report-last.json").exists(), "the real report was archived as one")
        self.assertEqual(km._UPDATE_STATE[0], "")
        ns = self.notices()
        self.assertEqual(len(ns), 1)
        self.assertIn("v0.0.9", ns[0]["text"])
        self.assertNotIn("could not be read", ns[0]["text"])

    def test_a_junk_report_that_cannot_be_moved_aside_is_said_once_and_stays(self):
        # a read-only state dir: the move fails. Silence here left the latch cleared with no word on
        # why (review find, 2026-09-08); the convention is one loud notice per fault episode, the
        # junk left in place as evidence, and the poll told the reason. A move that later succeeds
        # ends the episode, so the next unmovable file speaks again.
        p = jd.STATE / "update-report.json"
        p.write_text("[]")
        denied = PermissionError(13, "Permission denied")
        with mock.patch.object(km.os, "replace", side_effect=denied):
            km._UPDATE_STATE[0] = "running"
            rep = km._consume_update_report(running_only=True)
            self.assertEqual(km._UPDATE_STATE[0], "", "the child wrote SOMETHING: nothing is in flight")
            self.assertFalse(rep["ok"])
            self.assertIn("could not be moved aside", rep["why"])
            self.assertIn("Permission denied", rep["why"])
            self.assertTrue(p.exists(), "the evidence stays where it is")
            ns = self.notices()
            self.assertEqual(len(ns), 1)
            self.assertEqual((ns[0]["ok"], ns[0].get("kind")), (False, "refused"))
            self.assertIn("Permission denied", ns[0]["text"])
            self.assertFalse(km._consume_update_report()["ok"], "the boot finds it again")
            self.assertEqual(len(self.notices()), 1, "the same fault is said once per episode")
        self.assertFalse(km._consume_update_report()["ok"])
        self.assertEqual(len(list(jd.STATE.glob("update-report.json.corrupt-*"))), 1, "moved once it can be")
        self.assertEqual(len(self.notices()), 2, "the move is its own word")
        p.write_text("null")
        with mock.patch.object(km.os, "replace", side_effect=denied):
            km._consume_update_report()
        self.assertEqual(len(self.notices()), 3, "a fault after a proved move is a new episode")

    def test_the_restart_hint_names_the_step_that_works_for_the_case(self):
        # `romp refresh` asks the manager; with no manager it exits 1 (review find, 2026-09-08). So
        # the no-manager report's hint names `romp up`, the manager-refused report's names `romp
        # refresh`, and a report from before the `why` field (main's no-manager shape: ok, not
        # restarted, nothing else) reads as the no-manager case it was.
        cases = ((dict(why="no manager is running this kernel"), "romp up"),
                 (dict(why="the manager on port 7777 did not take the restart request"), "romp refresh"),
                 (dict(why="the manager on port 7777 did not answer the restart request within 60 s"), "romp refresh"),
                 (dict(), "romp up"))
        for extra, cmd in cases:
            with km._SYNC_LOCK:
                del km._SYNC_NOTICES[:]
            (jd.STATE / "update-report.json").write_text(json.dumps({"ok": True, "tag": "v0.0.9",
                                                                     "restarted": False, **extra}))
            km._consume_update_report(running_only=True)
            ns = self.notices()
            self.assertEqual(len(ns), 1, extra)
            self.assertIn("`%s`" % cmd, ns[0]["text"], extra)
            self.assertNotIn("romp on", ns[0]["text"], "a retired spelling: the manager runs as `romp up`")
            # the no-manager hint may still NAME `romp refresh` (to say it needs the manager) but never
            # as the step; the manager hint never sends the user to start a manager that is there
            other = "(`romp refresh`) to run it" if cmd == "romp up" else "`romp up`"
            self.assertNotIn(other, ns[0]["text"], extra)

    def test_a_boot_that_already_runs_the_landed_tag_does_not_ask_for_another_restart(self):
        # the report says "on disk, not restarted"; when nobody polled before the user restarted by
        # hand, the boot that RUNS the tag is the one consuming it — its notice says this start runs
        # it, instead of asking for the restart that just happened
        # "v0.0.9+" FIRST: every release tag sits on the release PR's merge commit, not on the
        # VERSION-bump commit, so a checkout exactly on the tag reads the + (per _kernel_ver's own
        # docstring); a bare string compare made this arm dead on every real release (review
        # find, 2026-09-08). The bare shape still counts (a tag placed on the bump commit itself).
        rep = {"ok": True, "tag": "v0.0.9", "restarted": False, "why": "no manager is running this kernel"}
        for ver in ("v0.0.9+", "v0.0.9"):
            with km._SYNC_LOCK:
                del km._SYNC_NOTICES[:]
            (jd.STATE / "update-report.json").write_text(json.dumps(rep))
            with mock.patch.object(km, "_kernel_ver", return_value=ver):
                km._consume_update_report()
            ns = self.notices()
            self.assertEqual(len(ns), 1, ver)
            self.assertTrue(ns[0]["ok"], ver)
            self.assertIn("this start is running it", ns[0]["text"], ver)
            self.assertIn("no manager is running this kernel", ns[0]["text"], ver)
            self.assertNotIn("restart romp yourself", ns[0]["text"], ver)
        # a kernel on any other version (or one whose version reader has nothing) still asks; and
        # the still-running kernel's poll (running_only) never claims to run it, whatever it reports
        for ver, running_only in (("v0.0.8", False), ("v0.0.8+", False), ("v0.0.10", False), (None, False),
                                  ("v0.0.9", True), ("v0.0.9+", True)):
            with km._SYNC_LOCK:
                del km._SYNC_NOTICES[:]
            (jd.STATE / "update-report.json").write_text(json.dumps(rep))
            with mock.patch.object(km, "_kernel_ver", return_value=ver):
                km._consume_update_report(running_only=running_only)
            ns = self.notices()
            self.assertEqual(len(ns), 1, (ver, running_only))
            self.assertIn("restart romp yourself", ns[0]["text"], (ver, running_only))
            self.assertNotIn("this start is running it", ns[0]["text"], (ver, running_only))


class Routes(Fresh):
    @classmethod
    def setUpClass(cls):
        from http.server import ThreadingHTTPServer
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), km.Handler)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def _post(self, path, token=True, body=None, legacy=False):
        """A POST as the banner's ARMED click sends it (2026-09-10): {"confirmed": true} unless the
        test says otherwise. `body` is the JSON object to send; {} is the unconfirmed click. `legacy` is
        the request the banner sent before the confirm step, fetch('/update',{method:'POST'}) with no
        body at all: Content-Length 0 and no Content-Type, as http.client sends a bodiless POST."""
        import urllib.request, urllib.error
        headers = {"X-Romp-Token": km.TOKEN} if token else {}
        data = None if legacy else json.dumps({"confirmed": True} if body is None else body).encode()
        req = urllib.request.Request("http://127.0.0.1:%d%s" % (self.port, path), method="POST",
                                     data=data, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, r.read().decode()
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode()

    def test_update_check_is_gated_and_reports_the_state(self):
        status, _ = _serve_get("/update-check")
        self.assertEqual(status, 403)
        km._UPDATE_AVAIL[0] = "v0.7.0"
        status, body = _serve_get("/update-check", headers={"X-Romp-Token": km.TOKEN})
        d = json.loads(body)
        self.assertEqual((status, d["tag"], d["mode"], d["state"]), (200, "v0.7.0", "ask", ""))
        self.assertEqual(d["boot"], km._BOOT_ID, "the banner detects the NEW kernel by this flipping")

    def test_update_check_poll_consumes_a_failed_report_mid_run(self):
        km._UPDATE_STATE[0] = "running"
        (jd.STATE / "update-report.json").write_text(json.dumps({"ok": False, "tag": "v0.7.0",
                                                                 "why": "the pull or install failed"}))
        _, body = _serve_get("/update-check", headers={"X-Romp-Token": km.TOKEN})
        d = json.loads(body)
        self.assertEqual((d["failed"], d["state"]), ("the pull or install failed", ""))
        self.assertTrue(any(not n["ok"] for n in self.notices()), "the failure reached the Log too")

    def test_a_success_headed_for_restart_is_left_for_the_next_boot(self):
        # consuming it mid-run would file the notice into THIS dying kernel's in-memory ring — the
        # new kernel's boot must find the report and log the success durably
        km._UPDATE_STATE[0] = "running"
        (jd.STATE / "update-report.json").write_text(json.dumps({"ok": True, "tag": "v0.7.0",
                                                                 "restarted": True}))
        _, body = _serve_get("/update-check", headers={"X-Romp-Token": km.TOKEN})
        d = json.loads(body)
        self.assertEqual((d["failed"], d["updated"], d["state"]), ("", "", "running"))
        self.assertTrue((jd.STATE / "update-report.json").exists(), "not consumed — the next boot files it")
        self.assertEqual(self.notices(), [])

    def test_post_update_requires_something_known_and_the_token(self):
        code, _ = self._post("/update", token=False)
        self.assertEqual(code, 403)
        km._MAIN_DRIFT[0] = km._MAIN_DRIFT[1] = ""     # module state: a prior drift pass must not leak in
        code, body = self._post("/update")
        self.assertEqual(code, 409, "nothing known → nothing to act on: " + body)
        km._UPDATE_AVAIL[0] = "v0.7.0"
        ran = []
        with mock.patch.object(km, "_run_update", side_effect=lambda tag: ran.append(tag) or True):
            code, body = self._post("/update")
        self.assertEqual((code, ran), (200, ["v0.7.0"]))

    def _audit_rows(self):
        p = jd.STATE / "restart-audit.jsonl"
        return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []

    def test_post_update_refuses_an_unconfirmed_click_and_runs_nothing(self):
        # 2026-09-10: one click on the banner POSTed /update, and a click that only meant to focus the
        # dashboard window landed on it; every session on the box restarted mid-turn. The banner now
        # arms on the first click and posts {"confirmed": true} on the second, and the kernel holds
        # the same line: a body without the confirmation is refused before any check is read, so a
        # page that predates the confirm step (or a stray POST) cannot restart the box on one click.
        km._UPDATE_AVAIL[0] = "v0.7.0"
        km._MAIN_DRIFT[0] = km._MAIN_DRIFT[1] = ""
        ran = []
        with mock.patch.object(km, "_run_update", side_effect=lambda tag: ran.append(tag) or True), \
             mock.patch.object(km, "_run_main_update", side_effect=lambda *a, **kw: ran.append(a)):
            for body in ({}, {"confirmed": False}, {"confirmed": "yes"}, {"confirmed": 1}, "legacy"):
                # "legacy": the request a page loaded before the confirm step sends, an EMPTY body (not
                # the JSON text {}): it rides _json_object_body's empty branch, which no other route test
                # reaches, and must get the same 400 and the same text, never a 500
                code, text = self._post("/update", legacy=True) if body == "legacy" else self._post("/update", body=body)
                self.assertEqual(code, 400, (body, text))
                self.assertIn("confirmed click", text, body)
            km._UPDATE_AVAIL[0] = ""
            km._MAIN_DRIFT[0] = "aaaa1111"
            code, text = self._post("/update", body={})
            self.assertEqual(code, 400, "the drift door is the same door: " + text)
        self.assertEqual(ran, [], "nothing launched, nothing converged")
        self.assertEqual(self._audit_rows(), [], "a refused click is not a restart request; no row")
        self.assertEqual(km._UPDATE_STATE[0], "", "not latched")
        km._MAIN_DRIFT[0] = ""
        # a body that is not JSON, or not an object, is a 400 too, never a traceback
        code, text = self._post("/update", body=[1, 2])
        self.assertEqual(code, 400, text)
        # the refusal comes BEFORE the kernel's own checks are read, executed two ways: with nothing
        # pending, an unconfirmed click still gets the 400 (a route that decided the nothing-pending 409
        # first would answer 409); and with the check slots replaced by lists that raise when indexed,
        # the 400 still comes back (a route that read a slot first would 500)
        km._UPDATE_AVAIL[0] = ""
        km._MAIN_DRIFT[0] = km._MAIN_DRIFT[1] = ""
        code, text = self._post("/update", body={})
        self.assertEqual((code, "confirmed click" in text), (400, True), "refused before the 409 is decided: " + text)

        class _Unread(list):
            def __getitem__(self, i):
                raise AssertionError("a kernel check was read before the confirmed refusal")
        saved_avail, saved_drift = km._UPDATE_AVAIL, km._MAIN_DRIFT
        km._UPDATE_AVAIL, km._MAIN_DRIFT = _Unread([""]), _Unread(["", ""])
        try:
            code, text = self._post("/update", body={})
        finally:
            km._UPDATE_AVAIL, km._MAIN_DRIFT = saved_avail, saved_drift
        self.assertEqual((code, "confirmed click" in text), (400, True), "no check slot was read: " + text)

    def test_an_empty_body_is_an_empty_object(self):
        # the branch the legacy bodiless POST rides: a body of no bytes is {} with no error, so the route
        # names the missing confirmation instead of a parse error
        self.assertEqual(km._json_object_body(b""), ({}, None))

    def test_a_confirmed_click_writes_its_audit_row_tagged_update_confirmed(self):
        # the ledger tells a confirmed banner click from every other door: `via: update-confirmed`
        # rides on the row of both doors the click can take (a pending release, main drift)
        km._UPDATE_AVAIL[0] = "v0.7.0"
        km._MAIN_DRIFT[0] = km._MAIN_DRIFT[1] = ""
        with mock.patch.object(km, "_run_update", side_effect=lambda tag: True):
            code, _ = self._post("/update")
        self.assertEqual(code, 200)
        rows = self._audit_rows()
        self.assertEqual([(r["action"], r["tag"], r.get("via")) for r in rows],
                         [("self-update", "v0.7.0", "update-confirmed")])
        self.assertEqual(rows[0]["addr"], "127.0.0.1")
        km._UPDATE_AVAIL[0] = ""
        km._UPDATE_STATE[0] = ""
        km._MAIN_DRIFT[0] = "aaaa1111"
        ran = []
        with mock.patch.object(km, "_run_main_update", side_effect=lambda *a, **kw: ran.append(a)):
            code, _ = self._post("/update")
            self.assertEqual(code, 200)
            for _ in range(200):
                if ran:
                    break
                time.sleep(0.01)
        rows = self._audit_rows()
        self.assertEqual([(r["action"], r["tag"], r.get("via")) for r in rows][-1],
                         ("main-converge", "aaaa1111", "update-confirmed"))
        km._MAIN_DRIFT[0] = ""

    def test_update_check_carries_what_a_restart_would_stop_over_every_backend(self):
        # the banner's confirm step names these under the first click: how many sessions the restart
        # stops and how many of them it interrupts, summed over every backend the kernel runs (the SDK
        # backend and the Codex backend, each through its own restart_impact), never a guess from the
        # page. Both globals are saved and restored: another test's real Codex backend would otherwise
        # add its sessions to the count
        class Fake:
            def __init__(self, imp):
                self.imp = imp

            def restart_impact(self):
                return self.imp
        saved = km._sdk_backend, km._codex_backend

        def check():
            _, body = _serve_get("/update-check", headers={"X-Romp-Token": km.TOKEN})
            d = json.loads(body)
            return d["sessions"], d["midTurn"]
        try:
            km._UPDATE_AVAIL[0] = "v0.7.0"      # an offer: the counts are read only when a label can be worded (review round 6)
            km._sdk_backend, km._codex_backend = Fake((3, 1)), Fake((2, 1))
            self.assertEqual(check(), (5, 2), "a mixed box: Claude and Codex sessions summed")
            km._sdk_backend, km._codex_backend = Fake((3, 1)), None
            self.assertEqual(check(), (3, 1), "the Codex backend never built: no Codex session runs here")
            km._sdk_backend, km._codex_backend = Fake((3, 1)), False
            self.assertEqual(check(), (3, 1), "the Codex module unavailable: the same")
            km._sdk_backend, km._codex_backend = False, Fake((2, 1))
            self.assertEqual(check(), (2, 1), "a Codex-only box: its sessions are what the restart stops")
            km._sdk_backend, km._codex_backend = False, False
            self.assertEqual(check(), (0, 0), "no backend can run a session: nothing to stop")
            # the SDK backend still being constructed (main() builds it on a thread at boot): the impact
            # is UNKNOWN, and the route says null, never a 0/0 that reads as authoritative
            km._sdk_backend, km._codex_backend = None, Fake((2, 1))
            self.assertEqual(check(), (None, None))
            self.assertIsNone(km._restart_impact())
        finally:
            km._sdk_backend, km._codex_backend = saved

    def test_restart_impact_reads_the_backends_already_built_and_never_builds_one(self):
        # _restart_impact must not call _sdk() or _codex(): a /update-check landing in the boot window
        # would otherwise construct the backend on the request thread
        saved = km._sdk_backend, km._codex_backend
        try:
            km._sdk_backend, km._codex_backend = False, None
            with mock.patch.object(km, "_sdk", side_effect=AssertionError("built the SDK backend")), \
                 mock.patch.object(km, "_codex", side_effect=AssertionError("built the Codex backend")):
                self.assertEqual(km._restart_impact(), (0, 0))
                km._sdk_backend = None
                self.assertIsNone(km._restart_impact())
        finally:
            km._sdk_backend, km._codex_backend = saved

    def test_update_check_says_how_many_other_kernels_the_managers_restart_all_restarts(self):
        # the counts are this kernel's; the manager's restart-all restarts every kernel in its registry.
        # otherKernels is read from that registry as the manager itself lists it (GET /status on the
        # control port, the live map restartAll loops), never from kernels.json: the entries whose port is
        # not this kernel's. A fake manager answers here; ROMP_MANAGER_PORT points at it for the read
        import http.server
        from http.server import ThreadingHTTPServer
        answer = {"status": 200, "body": ""}
        hits = []

        class FakeManager(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                hits.append(self.path)
                if self.path != "/status":
                    self.send_response(404); self.end_headers(); return
                body = answer["body"].encode()
                self.send_response(answer["status"])
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *a):
                pass
        mgr = ThreadingHTTPServer(("127.0.0.1", 0), FakeManager)
        threading.Thread(target=mgr.serve_forever, daemon=True).start()
        saved_port = os.environ.get("ROMP_MANAGER_PORT")

        def registry(*ports):
            return json.dumps({"ok": True, "manager": {"pid": 1, "controlPort": mgr.server_address[1], "stale": False},
                               "kernels": [{"id": "k%d" % p, "port": p, "pid": 2, "restarts": 0, "upSec": 5} for p in ports]})

        def check():
            _, body = _serve_get("/update-check", headers={"X-Romp-Token": km.TOKEN})
            d = json.loads(body)
            self.assertEqual("manager" in d, km._manager_port(os.environ.get("ROMP_MANAGER_PORT")) is None,
                             "`manager: false` rides the answer exactly when no manager started this kernel (a port set: absent, "
                             "whatever the registry answered; absent or empty: present)")
            return d["otherKernels"]
        try:
            km._UPDATE_AVAIL[0] = "v0.7.0"      # an offer: the counts are read only when a label can be worded (review round 6)
            os.environ["ROMP_MANAGER_PORT"] = str(mgr.server_address[1])
            answer["body"] = registry(km.PORT, 31111)
            self.assertEqual(check(), 1, "one other kernel in the registry")
            self.assertEqual(km._other_kernels(), 1)
            answer["body"] = registry(km.PORT)
            self.assertEqual(check(), 0, "this kernel alone")
            answer["body"] = registry(31111, 31112)
            self.assertEqual(check(), 2, "a registry that does not list this kernel: every entry is another")
            answer["body"] = registry(km.PORT, 31111, 31112)
            self.assertEqual(km._manager_kernels(), [{"id": "k%d" % p, "port": p, "pid": 2, "restarts": 0, "upSec": 5}
                                                     for p in (km.PORT, 31111, 31112)], "the registry as the manager lists it")
            # unknown, never a guess: the manager answers something other than 200, or a body of another
            # shape, or nothing at all (a dead port); the route says null and the banner says the other
            # kernels may restart too (the manager did not answer; no article), never the single-kernel form.
            # Each failed read is said on stderr once per episode: the next test
            answer["status"], answer["body"] = 500, "{}"
            self.assertIsNone(check(), "a status other than 200")
            answer["status"], answer["body"] = 200, "not json"
            self.assertIsNone(check(), "not JSON")
            answer["body"] = json.dumps({"ok": True})
            self.assertIsNone(check(), "no kernels list")
            answer["body"] = json.dumps({"ok": True, "kernels": "main"})
            self.assertIsNone(check(), "kernels of another shape")
            os.environ["ROMP_MANAGER_PORT"] = "1"
            self.assertIsNone(check(), "nothing answers on the port")
            # no port in the environment, or an empty one: no manager started this kernel, so the read asks
            # nothing (an empty registry, 0 other kernels, the label's plain form) and the drift door's
            # restart dials nothing on the same absence (the next test). Review round 4 had both dial the
            # manager's DEFAULT port so the label and the restart would agree; on a development box that
            # port is another operator's live manager, and a probe with the variable absent restarted every
            # session on the box through the door (2026-09-10). The fake counts its requests and none arrives;
            # the connection class refuses every port but the fake's, so whatever the code does with the
            # absence this test reaches no manager it did not start
            os.environ.pop("ROMP_MANAGER_PORT", None)
            answer["status"], answer["body"] = 200, registry(km.PORT, 31111)
            before = len(hits)
            with mock.patch.object(km.http.client, "HTTPConnection", _dials_only(mgr.server_address[1])):
                self.assertEqual((km._manager_kernels(), check()), ([], 0), "the variable absent: no manager, nothing asked")
                os.environ["ROMP_MANAGER_PORT"] = ""
                self.assertEqual((km._manager_kernels(), check()), ([], 0), "the variable empty: the same")
            self.assertEqual(len(hits), before, "no request reached the fake on an absent or empty variable")
            self.assertEqual((km._manager_port(None), km._manager_port(""), km._manager_port("7777")), (None, None, 7777),
                             "one rule for every door: the value when set, else no manager")
        finally:
            if saved_port is None:
                os.environ.pop("ROMP_MANAGER_PORT", None)
            else:
                os.environ["ROMP_MANAGER_PORT"] = saved_port
            km._MANAGER_READ_FAULT[0] = ""
            mgr.shutdown()

    def test_with_no_manager_port_neither_door_dials_a_manager_and_with_one_both_dial_it(self):
        # No manager started this kernel when ROMP_MANAGER_PORT is absent or empty, so the banner's registry
        # read asks nothing (0 other kernels) and the drift door's restart dials nothing: the new code is on
        # disk and the sync surface says so, naming `romp up`, the tag door's wording for the same case
        # (`romp refresh` exits 1 without a manager). /update-check carries `manager: false` then, so the
        # banner words the click as the update on disk it is (its fifth label form, "Update romp on disk
        # now; restart it yourself to run it", over a confirm that reads Update), never the plain restart
        # form: 0 other kernels alone is also a manager running this kernel by itself (review round 5).
        # With a port set the field is absent, as an older kernel's answer is. Review round 4 had
        # both doors map the absence to the manager's DEFAULT port so the label and the restart would agree,
        # and the drift door had done so since before the confirm step; the guess is another operator's
        # live manager on a development box, and on 2026-09-10 a review probe with the variable absent
        # drove the door and every session on the box restarted. Red at 22d540a5: the door dialled the
        # default port (recorded here, never connected). Set to a fake manager's port, both doors dial it as
        # before. The fake stands in for a manager on an ephemeral port and records every request; the
        # connection class refuses every other port at construction, so whatever the code does with the
        # absence this test reaches no manager it did not start. The converge's own steps are stubbed
        import http.server
        from http.server import ThreadingHTTPServer
        hits = []

        class FakeManager(http.server.BaseHTTPRequestHandler):
            def _answer(self, body):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                hits.append(("GET", self.path))
                self._answer(json.dumps({"ok": True, "kernels": [{"id": "k1", "port": km.PORT}, {"id": "k2", "port": 31111}]}).encode())

            def do_POST(self):
                hits.append(("POST", self.path))
                self._answer(b"{}")

            def log_message(self, *a):
                pass
        mgr = ThreadingHTTPServer(("127.0.0.1", 0), FakeManager)
        threading.Thread(target=mgr.serve_forever, daemon=True).start()
        port = mgr.server_address[1]
        dials, notices, audits = [], [], []
        saved_port = os.environ.get("ROMP_MANAGER_PORT")
        try:
            km._UPDATE_AVAIL[0] = "v0.7.0"      # an offer: the counts are read only when a label can be worded (review round 6)
            with mock.patch.object(km.http.client, "HTTPConnection", _dials_only(port, dials)), \
                 mock.patch.object(km, "_rebuild_dist", return_value=(True, "")), \
                 mock.patch.object(km, "_checkout_sha", return_value="abcdef0123456789"), \
                 mock.patch.object(km, "_audit_restart_request", side_effect=lambda *a, **kw: audits.append(a[0])), \
                 mock.patch.object(km, "_sync_notice", side_effect=lambda *a, **kw: notices.append((a[0], kw.get("ok", True)))):
                for value in (None, ""):
                    if value is None:
                        os.environ.pop("ROMP_MANAGER_PORT", None)
                    else:
                        os.environ["ROMP_MANAGER_PORT"] = value
                    self.assertEqual(km._manager_kernels(), [], "no manager: an empty registry (%r)" % (value,))
                    self.assertEqual(km._other_kernels(), 0)
                    _, body = _serve_get("/update-check", headers={"X-Romp-Token": km.TOKEN})
                    d = json.loads(body)
                    self.assertEqual((d["otherKernels"], d["manager"]), (0, False),
                                     "no other kernels, and no manager: the banner's on-disk form, not the plain restart form (%r)" % (value,))
                    km._run_main_update("restart", True, manager_port=value)     # the /update handler's ack-time value
                    km._run_main_update("restart", True)                         # the daemon's default: the env, read here
                    km._restart_this_kernel("test", manager_port=value)          # the rule the other doors now share
                    km._restart_this_kernel("test")
                self.assertEqual(dials, [], "no door dialled anything with the variable absent or empty")
                self.assertEqual(hits, [], "nothing reached the fake manager")
                self.assertEqual(audits, ["kernel-asks-manager-restart-all"] * 4,
                                 "no main-converge request was audited: none went out (the four rows are _restart_this_kernel's own)")
                self.assertEqual(len(notices), 4, "each drift-door converge said what it did not do")
                for text, ok in notices:
                    self.assertFalse(ok, "said as a failure: the new code is on disk and not running")
                    self.assertIn("no manager is running this kernel", text)
                    self.assertIn("`romp up` starts one", text, "the step named works without a manager")
                    self.assertNotIn("\u2014", text)
                # the variable set to the fake's port: both doors dial it, and the answered request posts no notice
                os.environ["ROMP_MANAGER_PORT"] = str(port)
                self.assertEqual(len(km._manager_kernels()), 2, "the registry as the fake lists it")
                self.assertEqual(km._other_kernels(), 1)
                _, body = _serve_get("/update-check", headers={"X-Romp-Token": km.TOKEN})
                self.assertNotIn("manager", json.loads(body), "with a port set the field is absent: the label names the restart")
                km._run_main_update("restart", True, manager_port=str(port))
                km._run_main_update("restart", True)
            self.assertEqual([h for h in hits if h[0] == "POST"], [("POST", "/restart-all")] * 2, "both restart requests reached the fake")
            self.assertEqual(len([h for h in hits if h[0] == "GET"]), 3, "the two direct registry reads and the route's reached the fake")
            self.assertEqual(set(dials), {("127.0.0.1", port)}, "every dial went to the port the environment named")
            self.assertEqual(len(notices), 4, "the answered restart requests posted no failure notice")
            self.assertEqual(audits[-2:], ["main-converge"] * 2, "a request that went out was audited")
        finally:
            if saved_port is None:
                os.environ.pop("ROMP_MANAGER_PORT", None)
            else:
                os.environ["ROMP_MANAGER_PORT"] = saved_port
            km._MANAGER_READ_FAULT[0] = ""
            mgr.shutdown()

    def test_update_check_reads_no_counts_and_dials_no_registry_when_nothing_is_offered(self):
        # review round 6 of the confirm step (2026-09-10): the registry read and the impact count ran on every
        # idle /update-check, a page load with no offer pending included, against the route's own comment (read
        # only when a label can be worded from them): every idle page load dialled the manager and waited its
        # 1 s timeout on a silent one. Both are skipped when nothing is offered (no release tag after the
        # dismissal filter, no drift sha): every count null, no dial, and the banner's note() records no counts
        # from such an answer (the node scenario in tests/test_update_banner_confirm.py), since null there means
        # not asked, not unknown; the manager field, served on every answer, it does record (review round 7).
        # The connection class refuses every port: a read that runs is seen as a dial
        import contextlib
        saved_port, saved_be = os.environ.get("ROMP_MANAGER_PORT"), (km._sdk_backend, km._codex_backend)
        dials, asked, err = [], [], io.StringIO()

        class Fake:
            def restart_impact(self):
                asked.append(1)
                return (3, 1)

        def check():
            with contextlib.redirect_stderr(err):
                _, body = _serve_get("/update-check", headers={"X-Romp-Token": km.TOKEN})
            return json.loads(body)
        try:
            os.environ["ROMP_MANAGER_PORT"] = "7777"
            km._sdk_backend, km._codex_backend = Fake(), None
            km._UPDATE_AVAIL[0] = ""
            km._MAIN_DRIFT[0] = km._MAIN_DRIFT[1] = ""
            with mock.patch.object(km.http.client, "HTTPConnection", _dials_only(-1, dials, allow={self.port})):
                d = check()
                self.assertEqual((d["tag"], d["drift"], d["sessions"], d["midTurn"], d["otherKernels"], d["state"]),
                                 ("", "", None, None, None, ""), "nothing offered: every count null")
                self.assertEqual((dials, asked), ([], []), "nothing offered: no registry read, no impact count")
                self.assertNotIn("manager", d, "a port is set: the field is absent, as before")
                km._UPDATE_AVAIL[0] = "v0.7.0"
                km._dismiss_update("v0.7.0")
                d = check()
                self.assertEqual((d["tag"], d["sessions"], d["otherKernels"]), ("", None, None), "a dismissed release is no offer")
                self.assertEqual((dials, asked), ([], []))
                km._UPDATE_AVAIL[0] = "v0.7.1"
                d = check()
                self.assertEqual((d["tag"], d["sessions"], d["midTurn"], d["otherKernels"]), ("v0.7.1", 3, 1, None),
                                 "a release offered: the counts are read (the registry dial is refused by the rail: null)")
                self.assertEqual((len(dials), len(asked)), (1, 1))
                km._UPDATE_AVAIL[0] = ""
                km._MAIN_DRIFT[1] = "abcdef01"
                d = check()
                self.assertEqual((d["drift"], d["driftSha"], d["sessions"]), ("restart", "abcdef01", 3), "a drift offered: the same")
                self.assertEqual((len(dials), len(asked)), (2, 2))
        finally:
            km._sdk_backend, km._codex_backend = saved_be
            if saved_port is None:
                os.environ.pop("ROMP_MANAGER_PORT", None)
            else:
                os.environ["ROMP_MANAGER_PORT"] = saved_port
            km._MAIN_DRIFT[0] = km._MAIN_DRIFT[1] = ""
            km._MANAGER_READ_FAULT[0] = ""

    def test_update_check_reads_no_registry_while_the_update_runs(self):
        # while the update runs the banner shows the wait and its poll reads boot, failed and updated alone,
        # so the route skips the registry read (a loopback GET, up to 1 s on a manager that accepts and
        # never answers, and a stderr line per episode about a label that is not on screen) and answers
        # every count null. The fake manager here never answers: a read would hold the handler for the
        # timeout, and the socket records whether one was made at all
        import contextlib
        import socket
        srv = socket.socket()
        srv.bind(("127.0.0.1", 0))
        srv.listen(5)
        accepted = []

        def acceptor():
            while True:
                try:
                    c, _ = srv.accept()
                except OSError:
                    return
                accepted.append(c)
        threading.Thread(target=acceptor, daemon=True).start()
        saved_port, saved_state = os.environ.get("ROMP_MANAGER_PORT"), km._UPDATE_STATE[0]
        km._MANAGER_READ_FAULT[0] = ""
        err = io.StringIO()
        try:
            km._UPDATE_AVAIL[0] = "v0.7.0"      # an offer: the counts are read only when a label can be worded (review round 6)
            os.environ["ROMP_MANAGER_PORT"] = str(srv.getsockname()[1])
            km._UPDATE_STATE[0] = "running"
            t0 = time.monotonic()
            with contextlib.redirect_stderr(err):
                _, body = _serve_get("/update-check", headers={"X-Romp-Token": km.TOKEN})
            took = time.monotonic() - t0
            d = json.loads(body)
            self.assertEqual((d["state"], d["otherKernels"], d["sessions"], d["midTurn"]), ("running", None, None, None))
            self.assertEqual(accepted, [], "no connection reached the manager while the update runs")
            self.assertEqual(err.getvalue(), "", "no fault line about a label the banner is not showing")
            self.assertLess(took, 1.0, "the poll did not wait on the manager's timeout")
            # the control: idle again, the same route reads the registry (and the silent manager is said)
            km._UPDATE_STATE[0] = ""
            with contextlib.redirect_stderr(err):
                _, body = _serve_get("/update-check", headers={"X-Romp-Token": km.TOKEN})
            self.assertIsNone(json.loads(body)["otherKernels"])
            self.assertEqual(len(accepted), 1, "the idle read dialled the manager")
            self.assertIn("did not answer its registry read", err.getvalue())
        finally:
            km._UPDATE_STATE[0] = saved_state
            if saved_port is None:
                os.environ.pop("ROMP_MANAGER_PORT", None)
            else:
                os.environ["ROMP_MANAGER_PORT"] = saved_port
            km._MANAGER_READ_FAULT[0] = ""
            for c in accepted:
                c.close()
            srv.close()

    def _drift_click_and_wait(self, sha="abcdef01", kind="restart", timeout=10.0):
        """Click the drift door as the armed banner does, then wait for the converge thread to end (the
        in-flight flag clears in its finally). Returns the POST's (status, body)."""
        km._UPDATE_AVAIL[0] = ""
        km._MAIN_DRIFT[0], km._MAIN_DRIFT[1] = (sha, "") if kind == "pull" else ("", sha)
        res = self._post("/update")
        t0 = time.monotonic()
        while km._MAIN_CONVERGE_INFLIGHT[0] and time.monotonic() - t0 < timeout:
            time.sleep(0.01)
        self.assertFalse(km._MAIN_CONVERGE_INFLIGHT[0], "the converge thread did not end within %ss" % timeout)
        return res

    def test_the_drift_converge_is_running_to_every_poll_and_a_second_click_starts_no_second_one(self):
        # review round 5 of the confirm step (2026-09-10): the drift converge never set _UPDATE_STATE, so while
        # it ran every window's 3 s poll dialled the manager's registry (up to 1 s each on a silent manager, a
        # stderr line per episode) and a page loaded mid-converge read state "" with the drift still offered,
        # so a second confirmed click started a second converge thread and wrote a second audit row. Now a
        # dedicated in-flight flag (_MAIN_CONVERGE_INFLIGHT) is taken in the route before the thread starts and
        # cleared in the converge's finally: /update-check answers state "running" and every count null with no
        # dial while it is set, the second click hears converging and starts nothing, and the latched outcome of
        # the previous converge is cleared at the click. The converge is the real one, blocked on an Event inside
        # its bundle rebuild (the step before the manager dial), so the flag's set and clear are the code's own;
        # the fake manager on an ephemeral port answers the registry read and the restart request, and the
        # connection class refuses every other port but the Routes server's own
        import contextlib
        import http.server
        from http.server import ThreadingHTTPServer
        hits, dials, gate, builds = [], [], threading.Event(), []

        class FakeManager(http.server.BaseHTTPRequestHandler):
            def _answer(self, body):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                hits.append(("GET", self.path))
                self._answer(json.dumps({"ok": True, "kernels": [{"id": "k1", "port": km.PORT}, {"id": "k2", "port": 31111}]}).encode())

            def do_POST(self):
                hits.append(("POST", self.path))
                self._answer(b"{}")

            def log_message(self, *a):
                pass
        mgr = ThreadingHTTPServer(("127.0.0.1", 0), FakeManager)
        threading.Thread(target=mgr.serve_forever, daemon=True).start()
        port = mgr.server_address[1]

        def blocked_build():
            builds.append(time.monotonic())
            gate.wait(10)
            return True, ""

        def check():
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                _, body = _serve_get("/update-check", headers={"X-Romp-Token": km.TOKEN})
            return json.loads(body), err.getvalue()
        saved_port, saved_tried = os.environ.get("ROMP_MANAGER_PORT"), km._INPLACE_TRIED[0]
        km._MANAGER_READ_FAULT[0] = ""
        try:
            os.environ["ROMP_MANAGER_PORT"] = str(port)
            km._INPLACE_TRIED[0] = ""
            km._MAIN_CONVERGE_OUTCOME[0] = {"failed": "a stale outcome", "updated": "", "why": "", "hint": ""}
            with mock.patch.object(km.http.client, "HTTPConnection", _dials_only(port, dials, allow={self.port})), \
                 mock.patch.object(km, "_rebuild_dist", side_effect=blocked_build), \
                 mock.patch.object(km, "_checkout_sha", return_value="abcdef01"), \
                 mock.patch.object(km, "_send_to_app"):
                km._UPDATE_AVAIL[0] = ""
                km._MAIN_DRIFT[0], km._MAIN_DRIFT[1] = "", "abcdef01"
                code, body = self._post("/update")
                self.assertEqual((code, json.loads(body)), (200, {"ok": True, "state": "converging"}))
                for _ in range(500):
                    if builds:
                        break
                    time.sleep(0.01)
                self.assertEqual(len(builds), 1, "the converge thread is running, blocked in its rebuild step")
                self.assertTrue(km._MAIN_CONVERGE_INFLIGHT[0])
                t0 = time.monotonic()
                d, said = check()
                self.assertLess(time.monotonic() - t0, 1.0, "the poll waited on no registry read")
                self.assertEqual((d["state"], d["sessions"], d["midTurn"], d["otherKernels"]), ("running", None, None, None),
                                 "mid-converge: the wait's state, and no counts")
                self.assertEqual((d["failed"], d["updated"]), ("", ""), "the previous converge's latched outcome was cleared at the click")
                self.assertEqual([h for h in hits if h[0] == "GET"], [], "no registry read reached the manager while the converge runs")
                self.assertEqual([x for x in dials if x[1] != self.port], [], "no dial but the test's own request to the route")
                self.assertEqual(said, "", "no fault line about a label the banner is not showing")
                code, body = self._post("/update")
                self.assertEqual((code, json.loads(body)), (200, {"ok": True, "state": "converging"}),
                                 "a second click hears converging, like the tag door's second click hears running")
                time.sleep(0.05)
                self.assertEqual(len(builds), 1, "and started no second converge")
                rows = [r for r in self._audit_rows() if r["action"] == "main-converge"]
                self.assertEqual(len(rows), 1, ("one audit row for two clicks", rows))
                self.assertEqual((rows[0]["via"], rows[0]["tag"]), ("update-confirmed", "abcdef01"))
                gate.set()
                t0 = time.monotonic()
                while km._MAIN_CONVERGE_INFLIGHT[0] and time.monotonic() - t0 < 10:
                    time.sleep(0.01)
                self.assertFalse(km._MAIN_CONVERGE_INFLIGHT[0], "the converge's finally cleared the flag")
                self.assertEqual([h for h in hits if h[0] == "POST"], [("POST", "/restart-all")], "one restart request went out, to the fake")
                d, said = check()
                self.assertEqual((d["state"], d["otherKernels"]), ("", 1), "idle again: the poll reads the registry, which lists one other kernel")
                self.assertEqual([h for h in hits if h[0] == "GET"], [("GET", "/status")], "the idle read dialled the manager once")
                self.assertEqual((d["failed"], d["updated"]), ("", ""), "a restart the manager took latches no outcome: the boot id ends the wait")
        finally:
            gate.set()
            km._INPLACE_TRIED[0] = saved_tried
            if saved_port is None:
                os.environ.pop("ROMP_MANAGER_PORT", None)
            else:
                os.environ["ROMP_MANAGER_PORT"] = saved_port
            km._MANAGER_READ_FAULT[0] = ""
            km._MAIN_DRIFT[0] = km._MAIN_DRIFT[1] = ""
            mgr.shutdown()

    def test_the_auto_converge_is_running_to_every_poll_through_the_decorators_own_flag(self):
        # review round 6 of the confirm step (2026-09-10): the route takes the in-flight flag for a click, but the
        # auto converge calls _run_main_update directly (_main_drift_check), so the decorator's set at the
        # function's entry is its only cover, and no test failed without it. Called directly here, on a thread
        # blocked in its rebuild step: /update-check reads running with every count null and dials no registry.
        # Red with the decorator's set deleted (mutation-tested in the round); the fake manager takes the restart
        import http.server
        from http.server import ThreadingHTTPServer
        hits, dials, gate, builds = [], [], threading.Event(), []

        class FakeManager(http.server.BaseHTTPRequestHandler):
            def _answer(self, body):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                hits.append(("GET", self.path))
                self._answer(json.dumps({"ok": True, "kernels": [{"id": "k1", "port": km.PORT}]}).encode())

            def do_POST(self):
                hits.append(("POST", self.path))
                self._answer(b"{}")

            def log_message(self, *a):
                pass
        mgr = ThreadingHTTPServer(("127.0.0.1", 0), FakeManager)
        threading.Thread(target=mgr.serve_forever, daemon=True).start()
        port = mgr.server_address[1]

        def blocked_build():
            builds.append(1)
            gate.wait(10)
            return True, ""
        saved_port, saved_tried = os.environ.get("ROMP_MANAGER_PORT"), km._INPLACE_TRIED[0]
        try:
            os.environ["ROMP_MANAGER_PORT"] = str(port)
            km._INPLACE_TRIED[0] = ""
            km._UPDATE_AVAIL[0] = ""
            km._MAIN_DRIFT[0], km._MAIN_DRIFT[1] = "", "abcdef01"     # the offer the auto converge acts on
            with mock.patch.object(km.http.client, "HTTPConnection", _dials_only(port, dials, allow={self.port})), \
                 mock.patch.object(km, "_rebuild_dist", side_effect=blocked_build), \
                 mock.patch.object(km, "_checkout_sha", return_value="abcdef01"), \
                 mock.patch.object(km, "_send_to_app"):
                t = threading.Thread(target=km._run_main_update, args=("restart", True), kwargs={"manager_port": str(port)}, daemon=True)
                t.start()
                for _ in range(500):
                    if builds:
                        break
                    time.sleep(0.01)
                self.assertEqual(len(builds), 1, "the converge is running, blocked in its rebuild step")
                self.assertTrue(km._MAIN_CONVERGE_INFLIGHT[0], "the decorator's own set: no route took the flag")
                _, body = _serve_get("/update-check", headers={"X-Romp-Token": km.TOKEN})
                d = json.loads(body)
                self.assertEqual((d["state"], d["sessions"], d["midTurn"], d["otherKernels"]), ("running", None, None, None))
                self.assertEqual([h for h in hits if h[0] == "GET"], [], "no registry read while the converge runs")
                gate.set()
                t.join(10)
                self.assertFalse(t.is_alive())
                self.assertFalse(km._MAIN_CONVERGE_INFLIGHT[0], "the finally cleared it")
                self.assertEqual([h for h in hits if h[0] == "POST"], [("POST", "/restart-all")], "the converge reached the manager")
        finally:
            gate.set()
            km._INPLACE_TRIED[0] = saved_tried
            if saved_port is None:
                os.environ.pop("ROMP_MANAGER_PORT", None)
            else:
                os.environ["ROMP_MANAGER_PORT"] = saved_port
            km._MAIN_DRIFT[0] = km._MAIN_DRIFT[1] = ""
            km._MANAGER_READ_FAULT[0] = ""
            mgr.shutdown()

    def test_a_converge_thread_that_fails_to_start_gives_the_flag_back_and_the_next_click_converges(self):
        # review round 6 of the confirm step (2026-09-10): the route takes the in-flight flag before Thread.start();
        # a start that raises must give it back, or every later poll reads running and every later click hears
        # converging with nothing running, and no test failed with that except made a no-op. A Thread subclass
        # whose start raises for the converge's target alone (an unconditional patch would break the test
        # server's own request threads): the 500, the flag clear, no running push, and the NEXT click's converge
        # runs through to the manager. Red with the except made a no-op (mutation-tested in the round). Review
        # round 7: the take of the flag (_main_converge_begin) clears the last converge's latched outcome, and the
        # except gave back the flag alone, so a start that raised erased an outcome the waiting windows had not
        # read yet and their polls read the wait's neither state for good; the except now gives the outcome back
        # too, and the 500's readers still see it. The next click's take clears it, and a restart the manager
        # took latches none
        import http.server
        from http.server import ThreadingHTTPServer
        hits, dials, pushed, fails = [], [], [], [True]
        Real = threading.Thread
        stale = {"failed": "romp is updated on disk but the restart request failed (HTTP 500)", "updated": "", "why": "", "hint": ""}

        class FakeManager(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                hits.append(("POST", self.path))
                self.send_response(200)
                self.send_header("Content-Length", "2")
                self.end_headers()
                self.wfile.write(b"{}")

            def log_message(self, *a):
                pass

        class StartFails(Real):
            def start(self):
                if self._target is km._run_main_update and fails[0]:
                    fails[0] = False
                    raise RuntimeError("no thread")
                return super().start()
        mgr = ThreadingHTTPServer(("127.0.0.1", 0), FakeManager)
        Real(target=mgr.serve_forever, daemon=True).start()
        port = mgr.server_address[1]
        saved_port, saved_tried = os.environ.get("ROMP_MANAGER_PORT"), km._INPLACE_TRIED[0]
        try:
            os.environ["ROMP_MANAGER_PORT"] = str(port)
            km._INPLACE_TRIED[0] = ""
            km._UPDATE_AVAIL[0] = ""
            km._MAIN_DRIFT[0], km._MAIN_DRIFT[1] = "", "abcdef01"
            km._MAIN_CONVERGE_OUTCOME[0] = dict(stale)       # the last converge's ending, still unread by a waiting window
            with mock.patch.object(km.http.client, "HTTPConnection", _dials_only(port, dials, allow={self.port})), \
                 mock.patch.object(km, "_rebuild_dist", return_value=(True, "")), \
                 mock.patch.object(km, "_checkout_sha", return_value="abcdef01"), \
                 mock.patch.object(km, "_send_to_app", side_effect=lambda app, m: pushed.append(m)), \
                 mock.patch.object(threading, "Thread", StartFails):
                code, body = self._post("/update")
                self.assertEqual((code, body), (500, "romp could not start the converge: no thread"))
                self.assertFalse(km._MAIN_CONVERGE_INFLIGHT[0], "the flag was given back")
                self.assertEqual(pushed, [], "no running push for a converge that never started")
                self.assertEqual(km._MAIN_CONVERGE_OUTCOME[0], stale, "and so was the outcome the take had cleared (review round 7)")
                for reader in ("the window that clicked", "a window still waiting on the last converge"):
                    _, body = _serve_get("/update-check", headers={"X-Romp-Token": km.TOKEN})
                    d = json.loads(body)
                    self.assertEqual((d["state"], d["failed"], d["updated"]), ("", stale["failed"], ""), reader + ": idle, the outcome served")
                code, body = self._post("/update")
                self.assertEqual((code, json.loads(body)["state"]), (200, "converging"), "the next click starts the converge")
                t0 = time.monotonic()
                while km._MAIN_CONVERGE_INFLIGHT[0] and time.monotonic() - t0 < 10:
                    time.sleep(0.01)
                self.assertFalse(km._MAIN_CONVERGE_INFLIGHT[0])
                self.assertEqual(hits, [("POST", "/restart-all")], "and it ran through to the manager")
                self.assertEqual([m.get("state") for m in pushed], ["running"], "the second click's running push")
                self.assertIsNone(km._MAIN_CONVERGE_OUTCOME[0], "the click that started a converge cleared the old outcome")
        finally:
            km._INPLACE_TRIED[0] = saved_tried
            if saved_port is None:
                os.environ.pop("ROMP_MANAGER_PORT", None)
            else:
                os.environ["ROMP_MANAGER_PORT"] = saved_port
            km._MAIN_DRIFT[0] = km._MAIN_DRIFT[1] = ""
            km._MANAGER_READ_FAULT[0] = ""
            mgr.shutdown()

    def _drift_click_whose_thread_fails_to_start(self, before_raise=None):
        """The drift door clicked with a Thread whose start raises for the converge's target alone (the test
        server's own request threads start), so the route's except runs its give-back. `before_raise` runs
        inside that start, between the route's take of the flag and its except: the place a writer of the
        outcome slot can land meanwhile (review round 8 of the confirm step, 2026-09-10). A context manager
        that yields the running pushes; a fake manager on an ephemeral port behind _dials_only, as every
        Routes probe of the door, though nothing dials it: no thread runs."""
        import contextlib
        import http.server
        from http.server import ThreadingHTTPServer
        pushed, dials = [], []
        Real = threading.Thread

        class FakeManager(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                self.send_response(200)
                self.send_header("Content-Length", "2")
                self.end_headers()
                self.wfile.write(b"{}")

            def log_message(self, *a):
                pass

        class StartFails(Real):
            def start(self):
                if self._target is km._run_main_update:
                    if before_raise:
                        before_raise()
                    raise RuntimeError("no thread")
                return super().start()

        @contextlib.contextmanager
        def door():
            mgr = ThreadingHTTPServer(("127.0.0.1", 0), FakeManager)
            Real(target=mgr.serve_forever, daemon=True).start()
            port = mgr.server_address[1]
            saved_port, saved_tried = os.environ.get("ROMP_MANAGER_PORT"), km._INPLACE_TRIED[0]
            try:
                os.environ["ROMP_MANAGER_PORT"] = str(port)
                km._INPLACE_TRIED[0] = ""
                km._UPDATE_AVAIL[0] = ""
                km._MAIN_DRIFT[0], km._MAIN_DRIFT[1] = "", "abcdef01"
                with mock.patch.object(km.http.client, "HTTPConnection", _dials_only(port, dials, allow={self.port})), \
                     mock.patch.object(km, "_rebuild_dist", return_value=(True, "")), \
                     mock.patch.object(km, "_checkout_sha", return_value="abcdef01"), \
                     mock.patch.object(km, "_send_to_app", side_effect=lambda app, m: pushed.append(m)), \
                     mock.patch.object(threading, "Thread", StartFails):
                    yield pushed
            finally:
                km._INPLACE_TRIED[0] = saved_tried
                if saved_port is None:
                    os.environ.pop("ROMP_MANAGER_PORT", None)
                else:
                    os.environ["ROMP_MANAGER_PORT"] = saved_port
                km._MAIN_DRIFT[0] = km._MAIN_DRIFT[1] = ""
                km._MANAGER_READ_FAULT[0] = ""
                km._UPDATE_STATE[0] = ""
                mgr.shutdown()
        return door()

    def test_the_give_back_restores_what_the_take_cleared_not_what_an_earlier_read_saw(self):
        # review round 8 of the confirm step (2026-09-10): the round-7 give-back read the slot on the line BEFORE
        # the take of the flag (_main_converge_begin) and restored that read when Thread.start raised. An auto
        # converge ending between the read and the take (it is not gated on the flag) latched a newer outcome,
        # which the take cleared and the except then overwrote with the older read: None (the newer outcome lost,
        # every waiting window polling the wait's neither state for good) or a stale outcome served in its place.
        # The take now hands back what it cleared, read under the same lock hold, and the except restores exactly
        # that. Modelled with _main_converge_begin wrapped to run the auto converge's ending before the real take,
        # with the slot None and with a stale outcome in it at the click; red at 27c1cf3d8 in both
        real = km._main_converge_begin
        new = {"failed": "an auto converge ended between the read and the take", "updated": "", "why": "", "hint": ""}
        old = {"failed": "a stale outcome", "updated": "", "why": "", "hint": ""}

        def latch_then_take():
            km._main_converge_outcome(failed=new["failed"])
            km._main_converge_end()
            return real()
        for name, before in (("the slot None at the click", None), ("a stale outcome in the slot at the click", dict(old))):
            with self.subTest(name):
                km._MAIN_CONVERGE_OUTCOME[0] = before
                with self._drift_click_whose_thread_fails_to_start() as pushed, \
                     mock.patch.object(km, "_main_converge_begin", side_effect=latch_then_take):
                    code, body = self._post("/update")
                    self.assertEqual((code, body), (500, "romp could not start the converge: no thread"))
                    self.assertFalse(km._MAIN_CONVERGE_INFLIGHT[0], "the flag was given back")
                    self.assertEqual(pushed, [], "no running push for a converge that never started")
                    self.assertEqual(km._MAIN_CONVERGE_OUTCOME[0], new, "the outcome the take cleared is the one given back")
                    _, body = _serve_get("/update-check", headers={"X-Romp-Token": km.TOKEN})
                    d = json.loads(body)
                    self.assertEqual((d["state"], d["failed"], d["updated"]), ("", new["failed"], ""), "a waiting window's poll ends on it")

    def test_the_give_back_yields_to_an_outcome_latched_between_the_take_and_the_failed_start(self):
        # review round 8 (tests-1): the give-back restores the outcome the take cleared only while the slot is still
        # None, the clause round 7 wrote and did not pin. An auto converge that starts after the take and ends
        # before Thread.start raises has latched a newer outcome; an unconditional restore overwrote it with the
        # older one. Red with the `is None` clause removed on a copy of 27c1cf3d8
        old = {"failed": "a stale outcome", "updated": "", "why": "", "hint": ""}
        new = {"failed": "an auto converge ended between the take and the failed start", "updated": "", "why": "", "hint": ""}
        km._MAIN_CONVERGE_OUTCOME[0] = dict(old)
        with self._drift_click_whose_thread_fails_to_start(before_raise=lambda: km._main_converge_outcome(failed=new["failed"])) as pushed:
            code, body = self._post("/update")
            self.assertEqual((code, body), (500, "romp could not start the converge: no thread"))
            self.assertFalse(km._MAIN_CONVERGE_INFLIGHT[0], "the flag was given back")
            self.assertEqual(pushed, [], "no running push")
            self.assertEqual(km._MAIN_CONVERGE_OUTCOME[0], new, "the newer outcome stands; the older one is not reinstated over it")
            _, body = _serve_get("/update-check", headers={"X-Romp-Token": km.TOKEN})
            d = json.loads(body)
            self.assertEqual((d["state"], d["failed"], d["updated"]), ("", new["failed"], ""), "and is what every poll reads")

    def test_the_give_back_yields_to_a_tag_door_start_between_the_take_and_the_failed_start(self):
        # review round 8 (correctness-1): the tag door's start (_run_update, through the route's tag branch or the
        # auto path) sets its running state and clears the slot for the child it launched. One landing between the
        # drift door's take and its except left the slot None, so the round-7 give-back (gated on None alone)
        # reinstated the outcome the take had cleared behind the running child, and once the child's report was
        # consumed every poll read that stale ending. The except now restores nothing while _UPDATE_STATE is
        # running, and the tag door's clear holds _MAIN_CONVERGE_LOCK, so the compare and the store cannot
        # straddle it. Red at 27c1cf3d8: the slot held the stale outcome after the 500
        old = {"failed": "a stale outcome", "updated": "", "why": "", "hint": ""}
        km._MAIN_CONVERGE_OUTCOME[0] = dict(old)

        def check():
            _, body = _serve_get("/update-check", headers={"X-Romp-Token": km.TOKEN})
            return json.loads(body)

        def tag_door_starts():
            with mock.patch.object(km.subprocess, "Popen", side_effect=lambda *a, **kw: None):
                if not km._run_update("v0.7.0"):
                    raise AssertionError("the tag door did not start")
        with self._drift_click_whose_thread_fails_to_start(before_raise=tag_door_starts) as pushed:
            code, body = self._post("/update")
            self.assertEqual((code, body), (500, "romp could not start the converge: no thread"))
            self.assertFalse(km._MAIN_CONVERGE_INFLIGHT[0], "the drift door's flag was given back")
            self.assertEqual(pushed, [], "no running push from the drift door")
            self.assertEqual(km._UPDATE_STATE[0], "running", "the tag door's child is in flight")
            self.assertIsNone(km._MAIN_CONVERGE_OUTCOME[0], "the tag door's clear stands: nothing is reinstated behind its child")
            d = check()
            self.assertEqual((d["state"], d["failed"], d["updated"]), ("running", "", ""), "the wait for the tag door's child")
            km._UPDATE_STATE[0] = ""      # the child's report consumed
            d = check()
            self.assertEqual((d["state"], d["failed"], d["updated"]), ("", "", ""), "idle after it, with no stale ending served")

    def test_both_running_pushes_say_when_no_manager_started_the_kernel(self):
        # review round 6 of the confirm step (2026-09-10): the running push flips every window into the wait, and
        # the wait's words promised a restart and a reload on a kernel no manager started, where nothing restarts.
        # Both doors' pushes carry `manager: false` when no manager started the kernel (the shape of
        # /update-check's field: present only then, absent with a port set), and the shell relays it to the
        # banner, which words the wait as the update on disk. The tag door's child is Popen-mocked; the drift
        # door's converge is the real one, with its rebuild stubbed: it dials nothing with the variable absent
        # and dials the set port once, which the rail refuses (a failed outcome, nothing reached)
        pushed, dials = [], []
        saved_port, saved_tried = os.environ.get("ROMP_MANAGER_PORT"), km._INPLACE_TRIED[0]
        try:
            km._INPLACE_TRIED[0] = ""
            with mock.patch.object(km.http.client, "HTTPConnection", _dials_only(-1, dials, allow={self.port})), \
                 mock.patch.object(km.subprocess, "Popen", side_effect=lambda *a, **kw: None), \
                 mock.patch.object(km, "_rebuild_dist", return_value=(True, "")), \
                 mock.patch.object(km, "_checkout_sha", return_value="abcdef01"), \
                 mock.patch.object(km, "_send_to_app", side_effect=lambda app, m: pushed.append(m)):
                for value, expect in ((None, False), ("7777", None)):
                    if value is None:
                        os.environ.pop("ROMP_MANAGER_PORT", None)
                    else:
                        os.environ["ROMP_MANAGER_PORT"] = value
                    del pushed[:]
                    km._UPDATE_AVAIL[0] = "v0.7.0"
                    km._MAIN_DRIFT[0] = km._MAIN_DRIFT[1] = ""
                    code, _ = self._post("/update")
                    self.assertEqual(code, 200)
                    km._UPDATE_STATE[0] = ""
                    code, _ = self._drift_click_and_wait()
                    self.assertEqual(code, 200)
                    self.assertEqual([m.get("state") for m in pushed], ["running", "running"], "one running push per door (%r)" % (value,))
                    self.assertEqual([m.get("manager") for m in pushed], [expect, expect],
                                     "the field rides the push exactly when no manager started this kernel (%r)" % (value,))
                    self.assertEqual([("manager" in m) for m in pushed], [expect is not None] * 2, "absent, not null, with a port set (%r)" % (value,))
                self.assertEqual([x for x in dials if x[1] != self.port], [("127.0.0.1", 7777)],
                                 "no dial with the variable absent; one to the set port, refused by the rail")
        finally:
            km._INPLACE_TRIED[0] = saved_tried
            km._UPDATE_STATE[0] = ""
            if saved_port is None:
                os.environ.pop("ROMP_MANAGER_PORT", None)
            else:
                os.environ["ROMP_MANAGER_PORT"] = saved_port
            km._MAIN_DRIFT[0] = km._MAIN_DRIFT[1] = ""
            km._MANAGER_READ_FAULT[0] = ""

    def test_the_drift_doors_outcome_reaches_every_poll_when_the_banner_cannot_see_it_end(self):
        # review round 5 of the confirm step (2026-09-10): the no-manager branch of _run_main_update said its
        # outcome on the sync surface alone; the banner that started the converge stayed in its wait, polling
        # /update-check every 3 s in every open window until a hand reload, and the same for a restart request
        # the manager refused and for a refused pull. Now the outcome is latched (_MAIN_CONVERGE_OUTCOME) and
        # served through the poll's own fields: no manager reads `updated` with the on-disk wording (the poll
        # ends through its d.updated exit and re-offers no click that cannot work), the refused request and the
        # refused pull read `failed`. The banner re-shows Update on `failed` only while the answer still carries an
        # offer (review round 6): the refused request keeps its drift slot, the refused pull's refusal re-arms it,
        # so that answer carries no drift and the failure text shows alone until the next check re-offers (a
        # re-shown Update got the route's 409, rendered as "already ran" though nothing ran). Latched, not consumed: the
        # running push flipped every window into the wait, so two readers both see it. The converge itself
        # audits no restart request (its own row, with when and sha, is not written); the click's route row,
        # via update-confirmed, stands: exactly one main-converge row. No dial with the variable absent
        import http.server
        from http.server import ThreadingHTTPServer
        hits, dials, notices = [], [], []

        class RefusingManager(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                hits.append(("POST", self.path))
                self.send_response(500)
                self.send_header("Content-Length", "0")
                self.end_headers()

            def log_message(self, *a):
                pass
        mgr = ThreadingHTTPServer(("127.0.0.1", 0), RefusingManager)
        threading.Thread(target=mgr.serve_forever, daemon=True).start()
        port = mgr.server_address[1]
        saved_port, saved_tried = os.environ.get("ROMP_MANAGER_PORT"), km._INPLACE_TRIED[0]

        def check():
            _, body = _serve_get("/update-check", headers={"X-Romp-Token": km.TOKEN})
            return json.loads(body)
        try:
            km._INPLACE_TRIED[0] = ""
            os.environ.pop("ROMP_MANAGER_PORT", None)
            with mock.patch.object(km.http.client, "HTTPConnection", _dials_only(port, dials, allow={self.port})), \
                 mock.patch.object(km, "_rebuild_dist", return_value=(True, "")), \
                 mock.patch.object(km, "_checkout_sha", return_value="abcdef0123456789"), \
                 mock.patch.object(km, "_sync_notice", side_effect=lambda *a, **kw: notices.append((a[0], kw.get("ok", True)))), \
                 mock.patch.object(km, "_send_to_app"):
                code, body = self._drift_click_and_wait()
                self.assertEqual((code, json.loads(body)["state"]), (200, "converging"))
                for reader in ("the window that clicked", "another window the running push flipped into the wait"):
                    d = check()
                    self.assertEqual((d["state"], d["failed"], d["updated"], d["why"]), ("", "", "abcdef01", km._NO_MANAGER_WHY), reader)
                    self.assertIn("`romp up` starts one", d["hint"], reader)
                    self.assertEqual((d["manager"], d["otherKernels"]), (False, 0), reader)
                self.assertEqual([x for x in dials if x[1] != self.port], [], "nothing dialled with the variable absent")
                self.assertEqual(hits, [])
                self.assertEqual([ok for _, ok in notices], [False], "one failure notice on the sync surface")
                self.assertIn(km._NO_MANAGER_WHY, notices[0][0])
                rows = self._audit_rows()
                self.assertEqual([r["action"] for r in rows], ["main-converge"], ("the click's route row alone", rows))
                self.assertEqual(rows[0]["via"], "update-confirmed")
                self.assertTrue("when" not in rows[0] and "sha" not in rows[0],
                                "the converge's own row (when and sha) is not written: no restart request went out (%r)" % rows)
                # a manager that refuses the restart request: `failed`, so the banner re-offers Update
                os.environ["ROMP_MANAGER_PORT"] = str(port)
                code, body = self._drift_click_and_wait()
                self.assertEqual(code, 200)
                d = check()
                self.assertEqual(hits, [("POST", "/restart-all")], "the request reached the fake, which refused it")
                self.assertEqual((d["state"], d["updated"]), ("", ""))
                self.assertIn("the restart request failed", d["failed"])
                self.assertIn("HTTP 500", d["failed"])
                self.assertNotIn("manager", d, "a port is set")
                self.assertEqual((d["drift"], d["driftSha"]), ("restart", "abcdef01"), "the refused request keeps its offer: Update re-shows")
                self.assertEqual([ok for _, ok in notices], [False, False])
                # a refused pull (no commit named for the move): `failed` with the refusal's own words, and the
                # answer carries no offer (the refusal re-armed the slot), so the banner shows the text alone
                km._MAIN_DRIFT[0], km._MAIN_DRIFT[1] = "abcdef01", ""
                km._run_main_update("pull", True, manager_port=None, target="")
                d = check()
                self.assertIn("no commit was named for the move", d["failed"])
                self.assertIn("the next check re-reads main and offers the update again", d["failed"],
                              "the text promises the re-offer, never a button that will not show")
                self.assertEqual((d["drift"], d["driftSha"], km._MAIN_DRIFT[0]), ("", "", ""), "no offer stands after a refused pull")
                self.assertEqual([ok for _, ok in notices], [False, False, False])
                self.assertEqual([h for h in hits], [("POST", "/restart-all")], "the refusal dialled nothing")
        finally:
            km._INPLACE_TRIED[0] = saved_tried
            if saved_port is None:
                os.environ.pop("ROMP_MANAGER_PORT", None)
            else:
                os.environ["ROMP_MANAGER_PORT"] = saved_port
            km._MAIN_DRIFT[0] = km._MAIN_DRIFT[1] = ""
            mgr.shutdown()

    def test_a_converge_that_dies_on_an_exception_latches_a_failed_outcome_and_the_next_click_runs_again(self):
        # review round 6 of the confirm step (2026-09-10): an exception out of _run_main_update (here the bundle
        # rebuild raising) left every waiting window polling for good: the decorator's finally cleared the
        # in-flight flag, but nothing latched an outcome or posted a notice, so /update-check answered state "",
        # failed "", updated "" to every reader, the wait's neither state. The decorator now latches `failed`
        # first, then posts the ok=False notice, then re-raises (the thread's traceback still reaches stderr, the
        # Log's); latch before notice, so a notice helper that raises cannot skip the latch. A manager port is set
        # and nothing is dialled: the exception comes before the dial. The flag is clear afterwards, so a retry
        # click starts a fresh converge, which runs through to the manager
        import http.server
        from http.server import ThreadingHTTPServer
        dials, notices, deaths, builds, hits = [], [], [], [], []

        class Manager(http.server.BaseHTTPRequestHandler):
            def _answer(self, body):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):            # the idle polls' registry read, once the converge has ended
                hits.append(("GET", self.path))
                self._answer(json.dumps({"ok": True, "kernels": [{"id": "k1", "port": km.PORT}]}).encode())

            def do_POST(self):
                hits.append(("POST", self.path))
                self._answer(b"{}")

            def log_message(self, *a):
                pass
        mgr = ThreadingHTTPServer(("127.0.0.1", 0), Manager)
        threading.Thread(target=mgr.serve_forever, daemon=True).start()
        port = mgr.server_address[1]
        saved_port, saved_tried = os.environ.get("ROMP_MANAGER_PORT"), km._INPLACE_TRIED[0]

        def build():
            builds.append(1)
            if len(builds) == 1:
                raise RuntimeError("esbuild vanished")
            return True, ""

        def check():
            _, body = _serve_get("/update-check", headers={"X-Romp-Token": km.TOKEN})
            return json.loads(body)
        try:
            km._INPLACE_TRIED[0] = ""
            os.environ["ROMP_MANAGER_PORT"] = str(port)
            with mock.patch.object(km.http.client, "HTTPConnection", _dials_only(port, dials, allow={self.port})), \
                 mock.patch.object(km, "_rebuild_dist", side_effect=build), \
                 mock.patch.object(km, "_checkout_sha", return_value="abcdef01"), \
                 mock.patch.object(km, "_sync_notice", side_effect=lambda *a, **kw: notices.append((a[0], kw.get("ok", True)))), \
                 mock.patch.object(threading, "excepthook", lambda args: deaths.append(args.exc_value)), \
                 mock.patch.object(km, "_send_to_app"):
                code, body = self._drift_click_and_wait()
                self.assertEqual((code, json.loads(body)["state"]), (200, "converging"))
                self.assertEqual([type(e).__name__ for e in deaths], ["RuntimeError"], "the exception still leaves the thread: re-raised")
                text = "the converge stopped on an error, RuntimeError: esbuild vanished; the Log has the traceback"
                for reader in ("the window that clicked", "another window the running push flipped into the wait"):
                    d = check()
                    self.assertEqual((d["state"], d["failed"], d["updated"]), ("", text, ""), reader)
                self.assertEqual([ok for _, ok in notices], [False], "exactly one failure notice on the sync surface")
                self.assertIn("esbuild vanished", notices[0][0])
                self.assertEqual([h for h in hits if h[0] == "POST"], [], "no restart request went out: the exception came before the dial")
                self.assertEqual([x for x in dials if x[1] not in (port, self.port)], [], "nothing but the fake and the route's own server")
                # the retry: the flag is clear, so the next click starts a fresh converge, which reaches the manager
                code, body = self._drift_click_and_wait()
                self.assertEqual((code, json.loads(body)["state"]), (200, "converging"))
                self.assertEqual(len(builds), 2, "a fresh converge ran")
                self.assertEqual([h for h in hits if h[0] == "POST"], [("POST", "/restart-all")], "and asked the manager for the restart")
                d = check()
                self.assertEqual((d["state"], d["failed"], d["updated"]), ("", "", ""), "a restart the manager took latches no outcome")
        finally:
            km._INPLACE_TRIED[0] = saved_tried
            if saved_port is None:
                os.environ.pop("ROMP_MANAGER_PORT", None)
            else:
                os.environ["ROMP_MANAGER_PORT"] = saved_port
            km._MAIN_DRIFT[0] = km._MAIN_DRIFT[1] = ""
            km._MANAGER_READ_FAULT[0] = ""
            mgr.shutdown()

    def test_a_notice_helper_that_raises_still_leaves_the_failed_outcome_latched(self):
        # review round 7 of the confirm step (2026-09-10): round 6 wrote the decorator's except as latch, then notice,
        # then re-raise, so that a notice helper that raises cannot skip the latch, and said so in its docstring; no
        # test held the order (the two lines swapped left the pin above green). Here the notice helper raises too:
        # the thread dies on the helper's error (the converge's own rides along as its context; the re-raise line
        # is never reached), the finally still clears the flag, and every reader finds the latched outcome, which
        # names the converge's error. Red with the latch and the notice swapped (verified in the round)
        import http.server
        from http.server import ThreadingHTTPServer
        dials, deaths, hits = [], [], []

        class Manager(http.server.BaseHTTPRequestHandler):
            def _answer(self, body):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):            # the idle polls' registry read, once the converge has ended
                hits.append(("GET", self.path))
                self._answer(json.dumps({"ok": True, "kernels": [{"id": "k1", "port": km.PORT}]}).encode())

            def do_POST(self):
                hits.append(("POST", self.path))
                self._answer(b"{}")

            def log_message(self, *a):
                pass
        mgr = ThreadingHTTPServer(("127.0.0.1", 0), Manager)
        threading.Thread(target=mgr.serve_forever, daemon=True).start()
        port = mgr.server_address[1]
        saved_port, saved_tried = os.environ.get("ROMP_MANAGER_PORT"), km._INPLACE_TRIED[0]

        def check():
            _, body = _serve_get("/update-check", headers={"X-Romp-Token": km.TOKEN})
            return json.loads(body)
        try:
            km._INPLACE_TRIED[0] = ""
            os.environ["ROMP_MANAGER_PORT"] = str(port)
            with mock.patch.object(km.http.client, "HTTPConnection", _dials_only(port, dials, allow={self.port})), \
                 mock.patch.object(km, "_rebuild_dist", side_effect=RuntimeError("esbuild vanished")), \
                 mock.patch.object(km, "_checkout_sha", return_value="abcdef01"), \
                 mock.patch.object(km, "_sync_notice", side_effect=RuntimeError("the sync ring is gone")), \
                 mock.patch.object(threading, "excepthook", lambda args: deaths.append(args.exc_value)), \
                 mock.patch.object(km, "_send_to_app"):
                code, body = self._drift_click_and_wait()
                self.assertEqual((code, json.loads(body)["state"]), (200, "converging"))
                self.assertEqual([type(e).__name__ for e in deaths], ["RuntimeError"], "the thread died on an exception")
                self.assertFalse(km._MAIN_CONVERGE_INFLIGHT[0], "the finally cleared the flag")
                text = "the converge stopped on an error, RuntimeError: esbuild vanished; the Log has the traceback"
                self.assertEqual((km._MAIN_CONVERGE_OUTCOME[0] or {}).get("failed"), text,
                                 "the latch was written before the notice helper ran, and holds the converge's own error")
                for reader in ("the window that clicked", "another window the running push flipped into the wait"):
                    d = check()
                    self.assertEqual((d["state"], d["failed"], d["updated"]), ("", text, ""), reader)
                self.assertEqual([h for h in hits if h[0] == "POST"], [], "no restart request went out: the exception came before the dial")
                self.assertEqual([x for x in dials if x[1] not in (port, self.port)], [], "nothing but the fake and the route's own server")
        finally:
            km._INPLACE_TRIED[0] = saved_tried
            if saved_port is None:
                os.environ.pop("ROMP_MANAGER_PORT", None)
            else:
                os.environ["ROMP_MANAGER_PORT"] = saved_port
            km._MAIN_DRIFT[0] = km._MAIN_DRIFT[1] = ""
            km._MANAGER_READ_FAULT[0] = ""
            mgr.shutdown()

    def test_the_tag_door_clears_the_drift_doors_latched_outcome_and_none_is_served_while_its_child_runs(self):
        # review round 6 of the confirm step (2026-09-10): the drift door's outcome stayed latched when the TAG
        # door started (only _main_converge_begin and the converge's decorator cleared it), and /update-check
        # folded the slot into its answer whether or not the tag child was in flight, so every window's wait
        # for a release update ended at once with the previous converge's words. Two halves, each red alone
        # under mutation in the round's probes: _run_update clears the slot once its child is launched (the
        # route's tag branch and the auto path alike; after the spawn since review round 7, so a spawn that
        # raises leaves it, the sibling below), and the route serves the slot only while _UPDATE_STATE
        # is not running, so an auto converge that latches an outcome while a release child runs does not end
        # that wait either (the child's own report does, consumed above the fold)
        km._MAIN_CONVERGE_OUTCOME[0] = {"failed": "a stale outcome", "updated": "", "why": "", "hint": ""}
        km._UPDATE_AVAIL[0] = "v0.7.0"
        km._MAIN_DRIFT[0] = km._MAIN_DRIFT[1] = ""

        def check():
            _, body = _serve_get("/update-check", headers={"X-Romp-Token": km.TOKEN})
            return json.loads(body)
        try:
            with mock.patch.object(km.subprocess, "Popen", side_effect=lambda *a, **kw: None), \
                 mock.patch.object(km, "_send_to_app"):
                code, body = self._post("/update")
            self.assertEqual((code, json.loads(body)), (200, {"ok": True, "state": "running"}))
            self.assertIsNone(km._MAIN_CONVERGE_OUTCOME[0], "the tag door's start cleared the drift door's slot")
            for reader in ("the window that clicked", "another window the running push flipped into the wait"):
                d = check()
                self.assertEqual((d["state"], d["failed"], d["updated"]), ("running", "", ""), reader)
            # the second half: an outcome latched while the child runs (an auto converge ending) is not served
            km._main_converge_outcome(failed="a converge that ended while the child ran")
            d = check()
            self.assertEqual((d["state"], d["failed"]), ("running", ""), "the tag child's wait ends on its own report alone")
            km._UPDATE_STATE[0] = ""
            d = check()
            self.assertEqual((d["state"], d["failed"]), ("", "a converge that ended while the child ran"),
                             "idle: the latched outcome is served")
            # the auto path takes the same door: _run_update itself clears the slot
            km._MAIN_CONVERGE_OUTCOME[0] = {"failed": "a stale outcome", "updated": "", "why": "", "hint": ""}
            with mock.patch.object(km.subprocess, "Popen", side_effect=lambda *a, **kw: None):
                self.assertTrue(km._run_update("v0.7.1"))
            self.assertIsNone(km._MAIN_CONVERGE_OUTCOME[0], "_run_update clears the slot for every caller, the auto path included")
        finally:
            km._UPDATE_STATE[0] = ""

    def test_a_tag_door_spawn_that_raises_leaves_the_drift_doors_latched_outcome_to_the_waiting_windows(self):
        # review round 7 of the confirm step (2026-09-10): _run_update cleared the drift door's latched outcome beside
        # its running state, before its Popen was known to have succeeded, and the spawn's except gave the latch
        # back but not the slot, so a tag-door start that failed to spawn erased an outcome the waiting windows had
        # not read yet (the poll leaves the wait only on failed, updated or a boot change) and their polls read
        # the wait's neither state for good. The clear now sits after the spawn: a spawn that raises leaves the
        # slot as it found it (the route's 500, the latch given back, no running push, the outcome served with
        # state ""), through the route and the auto path alike, and a spawn that succeeds clears it as round 6
        # pinned. Nothing is served early in between: the fold is gated on _UPDATE_STATE, and the running push
        # goes out only once _run_update has returned True
        stale = {"failed": "romp is updated on disk but the restart request failed (HTTP 500)", "updated": "", "why": "", "hint": ""}
        km._MAIN_CONVERGE_OUTCOME[0] = dict(stale)
        km._UPDATE_AVAIL[0] = "v0.7.0"
        km._MAIN_DRIFT[0] = km._MAIN_DRIFT[1] = ""
        pushed = []

        def check():
            _, body = _serve_get("/update-check", headers={"X-Romp-Token": km.TOKEN})
            return json.loads(body)
        try:
            d = check()
            self.assertEqual((d["state"], d["failed"]), ("", stale["failed"]), "the outcome, served before the click")
            with mock.patch.object(km.subprocess, "Popen", side_effect=OSError("fork failed")), \
                 mock.patch.object(km, "_send_to_app", side_effect=lambda app, m: pushed.append(m)):
                code, body = self._post("/update")
            self.assertEqual((code, body), (500, "romp could not start the update to v0.7.0; the Log has the reason"))
            self.assertEqual(km._UPDATE_STATE[0], "", "the latch was given back")
            self.assertEqual(pushed, [], "no running push for a child that never existed")
            self.assertEqual(km._MAIN_CONVERGE_OUTCOME[0], stale, "the slot is as the click found it")
            for reader in ("the window that clicked", "a window still waiting on the last converge"):
                d = check()
                self.assertEqual((d["state"], d["failed"], d["updated"]), ("", stale["failed"], ""), reader)
            self.assertEqual([n["ok"] for n in self.notices()], [False], "the spawn failure is said on the sync surface")
            # the auto path takes the same door: the same failure leaves the slot too
            with mock.patch.object(km.subprocess, "Popen", side_effect=OSError("fork failed")):
                self.assertFalse(km._run_update("v0.7.1"))
            self.assertEqual((km._UPDATE_STATE[0], km._MAIN_CONVERGE_OUTCOME[0]), ("", stale), "the auto path leaves it as well")
            # a spawn that succeeds clears it, the round-6 rule
            with mock.patch.object(km.subprocess, "Popen", side_effect=lambda *a, **kw: None), \
                 mock.patch.object(km, "_send_to_app", side_effect=lambda app, m: pushed.append(m)):
                code, body = self._post("/update")
            self.assertEqual((code, json.loads(body)), (200, {"ok": True, "state": "running"}))
            self.assertIsNone(km._MAIN_CONVERGE_OUTCOME[0], "a launched child clears the slot")
            self.assertEqual([m.get("state") for m in pushed], ["running"], "and its running push goes out")
            d = check()
            self.assertEqual((d["state"], d["failed"]), ("running", ""), "the wait for this update, with no old outcome")
        finally:
            km._UPDATE_STATE[0] = ""
            km._UPDATE_AVAIL[0] = ""

    def test_a_manager_port_that_is_not_a_port_reads_as_no_manager_and_is_said_once(self):
        # review round 5 of the confirm step (2026-09-10): _manager_port did int(value) outside every caller's
        # try, so a ROMP_MANAGER_PORT that was not a number (a typo on a kernel started by hand) made every
        # /update-check answer 500 with a traceback and the click's converge thread die with one on stderr and
        # no notice. Red at 5275a4d6 with 'abc' (ValueError from the route) and with '7_777' (int() accepts the
        # underscore, so the drift door dialled 7777). Now the value reads as no manager on every door, said on
        # stderr once per distinct value on a latch of its own (not the registry read's episode), and
        # /update-check answers 200 with `manager: false`, no dial anywhere. Digits outside the port range read
        # the same way (review round 6): getaddrinfo takes a port modulo 65536, so 0 and a value above 65535
        # dialled a port the operator never named (72968, a typo of one digit, is the manager's default 7432;
        # verified with a fake on P and the variable at P plus 65536: three of four doors reached it, the tag
        # door's curl refused the value on its own). Red at fc912080e with '0' and '70000': the dials were
        # made (and refused by the rail)
        import contextlib
        dials, notices, audits = [], [], []
        saved_port, saved_tried = os.environ.get("ROMP_MANAGER_PORT"), km._INPLACE_TRIED[0]
        km._MANAGER_PORT_FAULT[0] = ""
        err = io.StringIO()
        try:
            km._UPDATE_AVAIL[0] = "v0.7.0"      # an offer: the counts are read only when a label can be worded (review round 6)
            with contextlib.redirect_stderr(err):
                self.assertEqual((km._manager_port(" 7777 "), km._manager_port("7_777"), km._manager_port("abc"), km._manager_port("\u00b2")),
                                 (7777, None, None, None), "decimal digits only: a superscript two passes isdigit and fails int()")
                self.assertEqual((km._manager_port("0"), km._manager_port("70000"), km._manager_port("65535"), km._manager_port("1")),
                                 (None, None, 65535, 1), "within the port range: 0 and 70000 are not ports, the ends are")
            self.assertEqual(len(err.getvalue().splitlines()), 5, "one line per distinct non-port value")
            err.seek(0); err.truncate()
            km._MANAGER_PORT_FAULT[0] = ""
            with mock.patch.object(km.http.client, "HTTPConnection", _dials_only(-1, dials, allow={self.port})), \
                 mock.patch.object(km, "_rebuild_dist", return_value=(True, "")), \
                 mock.patch.object(km, "_checkout_sha", return_value="abcdef01"), \
                 mock.patch.object(km, "_audit_restart_request", side_effect=lambda *a, **kw: audits.append(a[0])), \
                 mock.patch.object(km, "_sync_notice", side_effect=lambda *a, **kw: notices.append((a[0], kw.get("ok", True)))), \
                 contextlib.redirect_stderr(err):
                for value in ("abc", "7_777", "0", "70000"):
                    os.environ["ROMP_MANAGER_PORT"] = value
                    km._INPLACE_TRIED[0] = ""
                    for _ in range(2):
                        status, body = _serve_get("/update-check", headers={"X-Romp-Token": km.TOKEN})
                        self.assertEqual(status, 200, (value, body[:200]))
                        d = json.loads(body)
                        self.assertEqual((d["manager"], d["otherKernels"], d["state"]), (False, 0, ""), value)
                    self.assertEqual(km._manager_kernels(), [], value)
                    km._run_main_update("restart", True, manager_port=value)
                    km._run_main_update("restart", True)
                    km._restart_this_kernel("test", manager_port=value)
                    km._restart_this_kernel("test")
                    with mock.patch.object(km.subprocess, "Popen", side_effect=lambda *a, **kw: None):
                        self.assertTrue(km._run_update("v0.7.0"))
                        km._UPDATE_STATE[0] = ""
                lines = err.getvalue().splitlines()
            self.assertEqual(dials, [], "no door dialled anything on a value that is not a port")
            self.assertEqual(lines, ["ROMP_MANAGER_PORT is 'abc', not a port; read as no manager",
                                     "ROMP_MANAGER_PORT is '7_777', not a port; read as no manager",
                                     "ROMP_MANAGER_PORT is '0', not a port; read as no manager",
                                     "ROMP_MANAGER_PORT is '70000', not a port; read as no manager"],
                             "said once per distinct value, naming it, across every poll and door")
            self.assertEqual([ok for _, ok in notices], [False] * 8, "each drift-door converge said what it did not do")
            for text, _ in notices:
                self.assertIn("`romp up` starts one", text)
            self.assertEqual(audits, ["kernel-asks-manager-restart-all"] * 8, "no main-converge row from the door: no request went out")
            self.assertEqual(km._MANAGER_READ_FAULT[0], "", "the registry read's episode latch is not the one used")
        finally:
            km._INPLACE_TRIED[0] = saved_tried
            if saved_port is None:
                os.environ.pop("ROMP_MANAGER_PORT", None)
            else:
                os.environ["ROMP_MANAGER_PORT"] = saved_port
            km._MANAGER_PORT_FAULT[0] = ""
            km._MANAGER_READ_FAULT[0] = ""

    def test_a_manager_that_accepts_and_never_answers_is_timed_out_and_said_once_per_episode(self):
        # the registry read's 1 s timeout has to reach the connection: without it every /update-check
        # handler thread hangs on a manager that accepts and never writes (the fake here: a raw listening
        # socket whose accepted connections are never read or answered). The read runs on a daemon thread
        # joined with a bound, so the regression it guards cannot hang the module; the elapsed time is at
        # least the timeout, so the None is the timeout's, not a refusal's; no tight upper bound (the box
        # runs sweeps under load). The kwarg itself is pinned on the default path through a recording
        # connection class that fails at once, so nothing waits a real second. And the failure is said on
        # stderr once per episode: the first failed read after a clean one, not the second; a clean read
        # ends the episode, and the next failure is said again
        import contextlib
        import socket
        srv = socket.socket()
        srv.bind(("127.0.0.1", 0))
        srv.listen(5)
        accepted = []

        def acceptor():
            while True:
                try:
                    c, _ = srv.accept()
                except OSError:
                    return
                accepted.append(c)              # never read, never answered
        threading.Thread(target=acceptor, daemon=True).start()
        import http.server
        from http.server import ThreadingHTTPServer

        class FakeManager(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                body = json.dumps({"ok": True, "kernels": [{"id": "k1", "port": km.PORT}]}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *a):
                pass
        mgr = ThreadingHTTPServer(("127.0.0.1", 0), FakeManager)
        threading.Thread(target=mgr.serve_forever, daemon=True).start()
        saved_port = os.environ.get("ROMP_MANAGER_PORT")
        km._MANAGER_READ_FAULT[0] = ""
        err = io.StringIO()

        def read(timeout):
            got = []
            t = threading.Thread(target=lambda: got.append(km._manager_kernels(timeout=timeout)), daemon=True)
            t0 = time.monotonic()
            t.start()
            t.join(10)
            self.assertFalse(t.is_alive(), "the registry read did not return within 10 s: the timeout did not reach the connection")
            return got[0], time.monotonic() - t0
        try:
            km._UPDATE_AVAIL[0] = "v0.7.0"      # an offer: the counts are read only when a label can be worded (review round 6)
            os.environ["ROMP_MANAGER_PORT"] = str(srv.getsockname()[1])
            with contextlib.redirect_stderr(err):
                ks, took = read(0.2)
            self.assertIsNone(ks)
            self.assertGreaterEqual(took, 0.2, "the None came from the timeout, not from a refusal")
            self.assertEqual(len(accepted), 1, "the connection reached the silent manager")
            lines = err.getvalue().splitlines()
            self.assertEqual(len(lines), 1, "the first failed read is said, once: %r" % lines)
            self.assertIn("did not answer its registry read", lines[0])
            self.assertIn("timed out", lines[0])
            self.assertIn(str(srv.getsockname()[1]), lines[0])
            self.assertNotIn("\u2014", lines[0])
            with contextlib.redirect_stderr(err):
                ks, _ = read(0.2)
            self.assertIsNone(ks)
            self.assertEqual(len(err.getvalue().splitlines()), 1, "the second failed read of the episode is not said again")
            # a clean read ends the episode; the next failure opens a new one and is said
            os.environ["ROMP_MANAGER_PORT"] = str(mgr.server_address[1])
            with contextlib.redirect_stderr(err):
                self.assertEqual(km._manager_kernels(), [{"id": "k1", "port": km.PORT}])
            self.assertEqual(km._MANAGER_READ_FAULT[0], "")
            os.environ["ROMP_MANAGER_PORT"] = str(srv.getsockname()[1])
            with contextlib.redirect_stderr(err):
                ks, _ = read(0.2)
            self.assertEqual(len(err.getvalue().splitlines()), 2, "said again after a clean read")
            # a changed reason within an episode is said too: the dead port after the silent one
            os.environ["ROMP_MANAGER_PORT"] = "1"
            with contextlib.redirect_stderr(err):
                self.assertIsNone(km._manager_kernels())
                self.assertIsNone(km._manager_kernels())
            lines = err.getvalue().splitlines()
            self.assertEqual(len(lines), 3, lines)
            self.assertIn("port 1", lines[2])
            # the kwarg on the default path (the route passes nothing): a connection class that records
            # its timeout and fails at once, so the pin costs no real second
            seen = []
            Real = km.http.client.HTTPConnection

            class Recording(Real):
                def __init__(self, *a, **kw):
                    seen.append(kw.get("timeout"))
                    super().__init__(*a, **kw)

                def getresponse(self):
                    raise socket.timeout("timed out")
            os.environ["ROMP_MANAGER_PORT"] = str(mgr.server_address[1])
            with mock.patch.object(km.http.client, "HTTPConnection", Recording), contextlib.redirect_stderr(err):
                self.assertIsNone(km._manager_kernels())
                _, body = _serve_get("/update-check", headers={"X-Romp-Token": km.TOKEN})
                self.assertIsNone(json.loads(body)["otherKernels"], "the route answers null for the timed-out read")
                self.assertIsNone(km._manager_kernels(timeout=0.5))
            self.assertEqual(seen, [1.0, 1.0, 0.5], "the default 1 s reaches the connection, from the route too")
        finally:
            if saved_port is None:
                os.environ.pop("ROMP_MANAGER_PORT", None)
            else:
                os.environ["ROMP_MANAGER_PORT"] = saved_port
            km._MANAGER_READ_FAULT[0] = ""
            for c in accepted:
                c.close()
            srv.close()
            mgr.shutdown()

    def test_post_update_converges_main_drift_when_no_release_is_pending(self):
        # the drift click is a REAL restart, so the converge is stubbed: a live manager must never hear
        # a test (2026-08-14: this exact route, exercised unstubbed while real drift existed, restart-
        # stormed the machine running the suite — each run bounced every kernel on the box)
        km._UPDATE_AVAIL[0] = ""
        km._MAIN_DRIFT[0], km._MAIN_DRIFT[1] = "aaaa1111", ""
        ran = []
        with mock.patch.object(km, "_run_main_update",   # the route hands over its ack-time port too
                               side_effect=lambda kind, immediate=False, manager_port=None, target="":
                                   ran.append((kind, immediate, target))):
            code, body = self._post("/update")
            self.assertEqual(code, 200)
            self.assertIn("converging", body)
            for _ in range(200):                       # the route hands off to a daemon thread
                if ran:
                    break
                time.sleep(0.01)
        self.assertEqual(ran, [("pull", True, "aaaa1111")],
                         "the banner click is the user's own deliberate cut, onto the commit the banner named")
        km._MAIN_DRIFT[0] = ""

    def test_an_update_that_landed_but_did_not_restart_is_consumed_with_its_reason(self):
        # the manager did not take the restart request: the child reports ok + restarted:false +
        # why, and the still-running kernel's poll consumes THAT into the truthful next step. The
        # kernel used to sit on "running" forever (the child claimed restarted:true before asking),
        # and its only not-restarted wording blamed a missing manager
        km._UPDATE_STATE[0] = "running"
        why = "the manager on port 7777 did not take the restart request"
        (jd.STATE / "update-report.json").write_text(json.dumps({"ok": True, "tag": "v0.0.9",
                                                                 "restarted": False, "why": why}))
        _, body = _serve_get("/update-check", headers={"X-Romp-Token": km.TOKEN})
        d = json.loads(body)
        self.assertEqual((d["updated"], d["why"], d["failed"], d["state"]), ("v0.0.9", why, "", ""))
        self.assertFalse((jd.STATE / "update-report.json").exists(), "consumed")
        ns = self.notices()
        self.assertEqual(len(ns), 1)
        self.assertTrue(ns[0]["ok"])
        for s in ("v0.0.9", "on disk", why, "romp refresh"):
            self.assertIn(s, ns[0]["text"])
        self.assertNotIn("no manager is running", ns[0]["text"], "a manager IS running — it did not take the request")

    def test_update_check_carries_the_restart_hint_for_the_case(self):
        # the banner shows the kernel's hint verbatim, so the no-manager case names the command
        # that works there (`romp refresh` exits 1 with no manager; review find, 2026-09-08)
        for why, cmd in (("no manager is running this kernel", "romp up"),
                         ("the manager on port 7777 did not take the restart request", "romp refresh")):
            km._UPDATE_STATE[0] = "running"
            (jd.STATE / "update-report.json").write_text(json.dumps({"ok": True, "tag": "v0.0.9",
                                                                     "restarted": False, "why": why}))
            _, body = _serve_get("/update-check", headers={"X-Romp-Token": km.TOKEN})
            d = json.loads(body)
            self.assertEqual((d["updated"], d["why"]), ("v0.0.9", why))
            self.assertIn(cmd, d["hint"], why)
            self.assertNotIn("romp on", d["hint"])
        km._UPDATE_STATE[0] = ""
        _, body = _serve_get("/update-check", headers={"X-Romp-Token": km.TOKEN})
        self.assertEqual(json.loads(body)["hint"], "", "no hint when nothing landed")

    def test_two_clicks_launch_one_update_and_the_second_hears_running(self):
        # two windows click Update: one child, and the second click is told `running` so its banner
        # joins the wait instead of racing a second launch. The route's guard for a launch refused
        # BECAUSE a concurrent click just took the latch (_run_update False AND the latch set) is the
        # `running` answer too, never the 500 a failed spawn earns (review find, 2026-09-08).
        km._UPDATE_AVAIL[0] = "v0.0.9"
        km._MAIN_DRIFT[0] = km._MAIN_DRIFT[1] = ""
        spawned, pushed = [], []
        with mock.patch.object(km.subprocess, "Popen", side_effect=lambda *a, **kw: spawned.append(a)), \
             mock.patch.object(km, "_send_to_app", side_effect=lambda app, m: pushed.append(m)):
            first = self._post("/update")
            second = self._post("/update")
        self.assertEqual((first[0], json.loads(first[1])), (200, {"ok": True, "state": "running"}))
        self.assertEqual((second[0], json.loads(second[1])), (200, {"ok": True, "state": "running"}))
        launches = [a for a in spawned if a[0][:2] == ["bash", "-c"]]    # the seam also sees git helpers
        self.assertEqual(len(launches), 1, ("one launch for two clicks", [a[0][:2] for a in spawned]))
        self.assertEqual([m.get("state") for m in pushed], ["running"], "one running push")
        self.assertEqual(self.notices(), [], "nothing failed, so nothing is filed")
        # the race itself: the launch is refused because the latch was taken between the route's
        # check and _run_update's own (a concurrent click won)
        km._UPDATE_STATE[0] = ""
        def won_the_race(tag):
            km._UPDATE_STATE[0] = "running"
            return False
        with mock.patch.object(km, "_run_update", side_effect=won_the_race), \
             mock.patch.object(km, "_send_to_app"):
            code, body = self._post("/update")
        self.assertEqual((code, json.loads(body)["state"]), (200, "running"))
        km._UPDATE_STATE[0] = ""

    def test_a_report_that_is_not_an_object_is_set_aside_and_the_poll_still_answers(self):
        # null / [] / a number parse but carry nothing: `.get` on them 500'd every poll for the
        # kernel's life (never consumed, so every poll hit the same file again)
        p = jd.STATE / "update-report.json"
        for junk in ("null", "[]", "3"):
            km._UPDATE_STATE[0] = "running"
            with km._SYNC_LOCK:
                del km._SYNC_NOTICES[:]
            p.write_text(junk)
            status, body = _serve_get("/update-check", headers={"X-Romp-Token": km.TOKEN})
            self.assertEqual(status, 200, junk)
            d = json.loads(body)
            self.assertEqual(d["state"], "", "nothing is in flight — the child wrote SOMETHING")
            self.assertIn("update-report.json.corrupt-", d["failed"])
            self.assertFalse(p.exists())
            aside = list(jd.STATE.glob("update-report.json.corrupt-*"))
            self.assertEqual(len(aside), 1, aside)
            self.assertEqual(aside[0].read_text(), junk, "evidence kept, never deleted")
            aside[0].unlink()
            ns = self.notices()
            self.assertEqual((len(ns), ns[0]["ok"]), (1, False))
            status, body = _serve_get("/update-check", headers={"X-Romp-Token": km.TOKEN})
            self.assertEqual((status, json.loads(body)["failed"]), (200, ""), "the next poll is quiet")
            self.assertEqual(len(self.notices()), 1, "said once")

    def test_the_update_click_hears_a_failed_launch_instead_of_waiting_on_it(self):
        # a spawn that fails after the click: the route used to answer 200 and push state:'running'
        # to every window with the latch set — every banner waited forever on a child that never
        # existed, and every later click was refused
        km._UPDATE_AVAIL[0] = "v0.0.9"
        km._MAIN_DRIFT[0] = km._MAIN_DRIFT[1] = ""
        pushed = []
        with mock.patch.object(km.subprocess, "Popen", side_effect=OSError("no bash")), \
             mock.patch.object(km, "_send_to_app", side_effect=lambda app, m: pushed.append(m)):
            code, body = self._post("/update")
        self.assertEqual(code, 500, body)
        self.assertIn("could not start the update to v0.0.9", body)
        self.assertEqual(pushed, [], "no 'running' push for a launch that did not happen")
        self.assertEqual(km._UPDATE_STATE[0], "", "not latched — the next click can try again")
        self.assertTrue(any(not n["ok"] and "v0.0.9" in n["text"] for n in self.notices()), "the Log says why")


class ManagerReadLatch(unittest.TestCase):
    """The once-per-episode latches under a concurrent writer (review round 5 of the confirm step, 2026-09-10;
    the staging of tests/test_free_threaded_caches.py). Every /update-check poll is a request-handler thread;
    on a free-threaded interpreter two polls that fail the registry read at once both saw the empty latch and
    both wrote the line (8 of 3000 trials on 3.14t). Under the GIL the compare and the store cannot
    interleave, so the interleaving is staged: the reason string's one comparison against the latch runs the
    peer's call. With _MANAGER_READ_LOCK the peer blocks until the first call has stored its reason and then
    finds the latch equal; without it the peer writes inside the window and the line is written twice."""

    def test_the_once_per_episode_line_is_written_once_under_a_concurrent_writer(self):
        import contextlib
        km._MANAGER_READ_FAULT[0] = ""
        err = io.StringIO()
        peer = threading.Thread(target=lambda: km._manager_read_fault(7777, "GET /status: the peer's reason"), daemon=True)

        def writer():
            peer.start()
            peer.join(0.3)       # with the lock the peer is parked on it; without, it has written its line by now
        why = _PeerWritesOnCompare("GET /status: the peer's reason", writer)
        try:
            why.armed = True
            with contextlib.redirect_stderr(err):
                km._manager_read_fault(7777, why)
                peer.join(5)
            self.assertFalse(peer.is_alive(), "the peer's call did not return: the lock was not released")
            lines = err.getvalue().splitlines()
            self.assertEqual(len(lines), 1, ("the episode's line, once", lines))
            self.assertIn("the peer's reason", lines[0])
            self.assertEqual(str(km._MANAGER_READ_FAULT[0]), "GET /status: the peer's reason")
        finally:
            km._MANAGER_READ_FAULT[0] = ""


class Wiring(unittest.TestCase):
    """Source pins: the check runs at boot, the banner ships on the landing page, the gear posts."""

    @classmethod
    def setUpClass(cls):
        cls.src = Path(os.path.join(BIN, "romp-kernel")).resolve().read_text()
        cls.gear = (Path(BIN).parent / "ui" / "webview" / "gear.js").read_text()

    def test_boot_starts_the_check_loop_and_files_the_last_report(self):
        # the LOOP, not a one-shot: kernels outlive browser tabs by weeks (the user 2026-08-09),
        # so a boot-only check would almost never fire
        self.assertIn("threading.Thread(target=_update_check_loop, daemon=True).start()", self.src)
        self.assertIn("_consume_update_report()                                   # last self-update's outcome", self.src)

    def test_the_banner_dismissal_is_per_release(self):
        # Not-now silences THE dismissed tag; a strictly newer release found by a later pass is
        # new information and re-offers
        self.assertIn("if(waiting||!tag||tag===dismissedTag)return;", self.src)
        self.assertIn("dm.onclick=function(){dismissedTag=curTag;", self.src)

    def test_the_landing_ships_the_banner_and_the_shell_relay(self):
        self.assertIn("_stale_block(v) + _update_block() + _rdrift_block()", self.src)
        self.assertIn("window.__rompUpdateOffer=offer", self.src)
        self.assertIn("m.type==='updateAvail'&&window.__rompUpdateOffer", self.src)
        self.assertIn("window.__rompUpdateOffer(m.cur||'',m.tag||'',m.drift||'',m.boot||'',m.state||'',m.manager)", self.src,
                      "the relay hands the push's manager field to the banner, which words the wait by it (review round 6)")

    def test_offers_retire_on_the_truth_not_in_an_error_banner(self):
        # the user 2026-08-15: a stale offer survived the restart it asked for; its Update click hit a
        # converged kernel and painted "Could not start the update" over a working dashboard. The offer
        # now (a) carries + checks the pushing kernel's boot, (b) retires when the 30s /version poll
        # sees a new boot, (c) treats the 409 as "already done" — retire + Log, never a dead-end error,
        # and (d) can be re-derived on page load from /update-check's new drift fields.
        self.assertIn("if(boot&&bootNow&&boot!==bootNow)return;", self.src)
        self.assertIn("window.__rompUpdBoot=function(b)", self.src)
        self.assertIn("if(v&&v.boot&&window.__rompUpdBoot)window.__rompUpdBoot(v.boot);", self.src)
        self.assertIn("/no newer release or main commit/.test(em)", self.src)
        self.assertIn("__rompNotify('sync','the update this prompt offered already ran", self.src)
        self.assertIn("else if(d.drift&&d.driftSha)offer(d.cur||'',d.driftSha,d.drift);", self.src)
        # …and an update starting ANYWHERE flips every window to the in-flight wait
        self.assertIn("if(state==='running'){waiting=true;go.hidden=true;dm.hidden=true;", self.src)
        self.assertIn('{"type": "updateAvail", "state": "running", "boot": _BOOT_ID}', self.src)

    def test_the_gear_offers_the_three_modes_and_posts_the_pick(self):
        self.assertIn("id=rs-updates", self.gear)
        # the row says what Off does (the user 2026-09-03, who wanted to turn off the notices about
        # new romp commits and could not tell that this switch is where): Off is the notices-off
        # setting, said in upstream's words since #1174 landed (slice 3, ruling G), and the build-reload
        # prompt is named as the one thing it does not cover
        self.assertIn("Off never checks", self.gear)
        self.assertIn("is not an update notice and stays on", self.gear)
        for opt in ("value=ask", "value=auto", "value=off"):
            self.assertIn(opt, self.gear)
        # the post is gesture-stamped (2026-08-29): setUpdateMode rides federation's queued
        # KERNEL_SETTING class, so the kernel orders applies by the click's own time — minted through
        # the gesture clock (ui/webview/gesture-clock.js), above every stamp the page has seen
        self.assertIn("post({ type: 'setUpdateMode', mode: upm.value, gt: gclock.stamp('update-mode') })", self.gear)
        # fill() renders through setShow now (2026-09-01): the same silent write, plus the
        # honest marked-option injection when a stored value is off this page's list
        self.assertIn("setShow(upm, v.updateMode)", self.gear)
        self.assertIn('msg.get("type") == "setUpdateMode"', self.src)

    def test_the_update_control_is_headed_automatic_updates(self):
        # The row's heading is upstream's "Automatic updates" (the 2026-09-09 fold, slice 3). The fork had
        # retitled it "Updates and update notices" (2026-09-03, so that someone looking for the switch that
        # stops the notices about new commits could tell this was it); the fold trims the fork's divergence to
        # what upstream lacks, and the help line's own words cover the notices ("one banner covers both",
        # "Off never checks"). Both sites in gear.js carry the heading, the row and the stale-pick toast's
        # label table, and the reference names the control by the same heading so a reader finds it in the gear.
        self.assertIn("<b>Automatic updates <span class=rs-mixed hidden></span></b>", self.gear)
        self.assertIn("'update-mode': 'Automatic updates',", self.gear)
        self.assertNotIn("Updates and update notices", self.gear)
        ref = re.sub(r"\s+", " ", (Path(BIN).parent / "docs" / "reference.md").read_text())
        self.assertIn("**Automatic updates** control (under *Updates & debug*)", ref)
        self.assertNotIn("Updates and update notices", ref)

    def test_the_copy_says_an_automatic_update_restarts_at_once_or_converges_in_place(self):
        # The help line for Install automatically said the converge restarts "at the next quiet
        # moment". Since T269 every deploy restart is immediate (_run_main_update's immediate=True
        # default; the auto caller passes no override), and a pulled range that touches no kernel
        # code converges in place with the kernel left up (_kernel_code_changed + _in_place_converge).
        # The copy names both routes. The route line is pinned too, so a change to the route flags
        # the copy for re-reading.
        self.assertIn("if not _kernel_code_changed(_kernel_sha(), pulled) and _in_place_converge(pulled):",
                      self.src)
        self.assertNotIn("quiet moment", self.gear,
                         "the gear still promises a quiet-window restart; since T269 every deploy restart "
                         "is immediate and romp refresh --quiet is the only door to the quiet window")
        self.assertIn("Install automatically converges by itself: a change to kernel code restarts it at "
                      "once (turns in flight are cut and resume with their history); anything else (the "
                      "UI, the docs, the postal bus) converges in place with the kernel left up;",
                      self.gear)

    def test_the_copy_says_an_automatic_update_restarts_at_once(self):
        # T269 (folded 2026-09-09): every deploy restart is immediate, and `romp refresh --quiet` is the
        # quiet window's one door (test_kernel_remote_update pins the code). The gear's help line and
        # the reference's Update-notices paragraph said the automatic mode restarted "at the next quiet
        # moment", which no caller has done since T160. Nor is the restart every converge's route (the
        # fold's review, F4): _run_main_update returns before it when the pulled range touches no kernel
        # code. _kernel_code_changed classes each changed file by the RUNNING PROCESS its code lives in
        # (_restart_class): the kernel's own Python and launchers are kernel class, postal/ and the bus's
        # script bin/romp-postal-service are the bus's, .md files are never code, and a kernel-class
        # Python file whose AST is unchanged is skipped; the UI, tests, docs and cli/ converge through
        # _in_place_converge with the kernel left up, the served bundles rebuilt. Both texts name the
        # routes by that class rule, never by directory (the fold's verification, round 2: a directory
        # list over-claims for the bus's script under bin/): code the running kernel executes restarts
        # at once, anything else converges in place. The code pin couples the copy to the route it
        # describes.
        self.assertIn("if not _kernel_code_changed(_kernel_sha(), pulled) and _in_place_converge(pulled):", self.src,
                      "the pull converge's in-place route, which the copy describes")
        ref = (Path(BIN).parent / "docs" / "reference.md").read_text()
        para = next(p for p in re.split(r"\n\s*\n", ref) if p.lstrip().startswith("**Update notices.**"))
        para = re.sub(r"\s+", " ", para)
        for text, where in ((self.gear, "gear.js"), (para, "reference.md")):
            self.assertFalse("quiet moment" in text, "%s: the automatic mode does not wait for a quiet window" % where)
            self.assertIn("converges in place", text, "%s: a change outside kernel code converges with the kernel up" % where)
        # the gear sentence is upstream's (#1174, the fork's own offer of this copy, landed 2026-09-09): the
        # later wording by the same author, taken whole at the fold (slice 3, ruling G)
        self.assertIn("Install automatically converges by itself: a change to kernel code restarts it at once (turns in "
                      "flight are cut and resume with their history); anything else (the UI, the docs, the postal bus) "
                      "converges in place with the kernel left up; Off never checks.", self.gear)
        self.assertIn("*Install automatically* converges on its own", para)
        self.assertIn("When the new commits change code the running kernel executes, Romp restarts at once", para)
        self.assertNotIn("`kernel/`, `bin/`", para, "the paragraph names the class rule, not a directory list")
        self.assertIn("converges in place with the kernel left up", para)
        self.assertIn("`romp refresh --quiet`", para, "the paragraph names the quiet window's one door")

    def test_the_reference_documents_the_click_on_a_kernel_no_manager_started(self):
        # review round 6 of the confirm step (2026-09-10): the Update-notices paragraph documented the red Restart
        # and the "manager did not answer" hedge and never the kernel no manager started (round 5's fifth label
        # form: a green Update confirm, nothing restarted). The copy is coupled to label() and face(), whose text
        # it quotes, and to the two things the second click then does: the in-place converge when the change is
        # outside kernel code (the route line pinned above), else the code on disk with `romp up` named as the
        # step that runs it
        ref = (Path(BIN).parent / "docs" / "reference.md").read_text()
        para = next(p for p in re.split(r"\n\s*\n", ref) if p.lstrip().startswith("**Update notices.**"))
        para = re.sub(r"\s+", " ", para)
        self.assertIn("When no manager started the kernel", para)
        clause = para[para.index("When no manager started the kernel"):]
        self.assertIn('"Update romp on disk now; restart it yourself to run it"', clause, "the label the banner shows, quoted")
        self.assertIn("green Update", clause, "the confirm reads Update in green, not the red Restart")
        self.assertIn("nothing restarts", clause)
        self.assertIn("converges in place when the change is outside kernel code", clause, "the in-place route runs first")
        self.assertIn("`romp up`", clause, "the step that runs kernel code landed on disk")
        self.assertNotIn("\u2014", clause[:clause.index("The gear")], "no em dash in the new clause")
        self.assertIn("if(impact.manager===false)return 'Update romp on disk now; restart it yourself to run it';", self.src, "the label the copy quotes")
        self.assertIn("cf.textContent=disk?'Update':'Restart';", self.src, "the confirm the copy names")

    def test_the_banner_names_the_restart_the_user_must_run_when_the_update_landed_on_disk(self):
        # `updated` from /update-check means ON DISK, not running: the banner carries the reason
        # the restart did not happen and names the step that runs the new code
        self.assertIn("(d.why?', but '+d.why:'')", self.src)
        # the kernel words the step by case (`romp refresh` exits 1 with no manager; review find,
        # 2026-09-08): the banner shows its hint, with the manager case as the fallback text
        self.assertIn("(d.hint||'restart romp yourself (romp refresh) to run it')", self.src)


class ReleaseChannelMigration(unittest.TestCase):
    """The REQUIRED migration (the user 2026-08-31): installs the old drift banner walked onto a
    detached main sha must return to the release channel on the next tag. From a sha AHEAD of the
    tag, `git merge --ff-only <tag>` fails — the script now falls back to checking the tag out
    directly when HEAD is not itself on any tag, loudly in the update log. EXECUTED on a real
    throwaway repo pair (bare origin + detached install), not a source pin: the fallback's git
    behavior is the thing under test."""

    def _repos(self, tmp):
        """origin (bare) with c1 —tag v9.9.8→ c2 —tag v9.9.9→ c3 (main tip); the install cloned
        and DETACHED at c3 — ahead of v9.9.9, on no tag: the walked-onto-main shape."""
        env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
               "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid"}
        def g(cwd, *args):
            r = subprocess.run(["git", *args], cwd=cwd, env=env, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, "git %s: %s%s" % (" ".join(args), r.stdout, r.stderr))
            return r.stdout.strip()
        src = os.path.join(tmp, "src")
        os.makedirs(src)
        g(src, "init", "-q", "-b", "main")
        with open(os.path.join(src, "install.sh"), "w") as f:
            f.write("#!/bin/sh\nexit 0\n")
        os.chmod(os.path.join(src, "install.sh"), 0o755)
        g(src, "add", "install.sh")
        g(src, "commit", "-qm", "c1")
        g(src, "tag", "v9.9.8")
        g(src, "commit", "-qm", "c2", "--allow-empty")
        g(src, "tag", "v9.9.9")
        g(src, "commit", "-qm", "c3", "--allow-empty")
        bare = os.path.join(tmp, "origin.git")
        g(tmp, "clone", "-q", "--bare", src, bare)
        inst = os.path.join(tmp, "install")
        g(tmp, "clone", "-q", bare, inst)
        g(inst, "checkout", "-q", "--detach", "origin/main")     # the old banner's walk
        return g, inst

    def _run(self, tag, inst):
        """Capture _run_update's script via the Popen seam, run it SYNCHRONOUSLY. The log and
        report are shared hermetic state — start each run clean or one test reads another's."""
        for f in ("update.log", "update-report.json"):
            try:
                (km.jd.STATE / f).unlink()
            except OSError:
                pass
        calls = []
        env = {**os.environ, "ROMP_MANAGER_PORT": ""}            # no manager → no restart leg
        # The install clones its bare `origin` directly, the plain layout; the resolver would say
        # so, but the Popen seam below swallows its `git remote` too, so it is pinned here.
        with mock.patch.object(km.subprocess, "Popen", side_effect=lambda *a, **kw: calls.append(a)), \
             mock.patch.object(km, "ROOT", Path(inst)), \
             mock.patch.object(km, "_release_remote", return_value="origin"), \
             mock.patch.dict(km.os.environ, env, clear=True):
            km._UPDATE_STATE[0] = ""
            self.assertTrue(km._run_update(tag))
        km._UPDATE_STATE[0] = ""
        script = calls[0][0][2]
        subprocess.run(["bash", "-c", script], cwd=inst, capture_output=True, text=True)
        return script

    def test_a_walked_onto_main_install_returns_to_the_release_channel_loudly(self):
        with tempfile.TemporaryDirectory() as tmp:
            g, inst = self._repos(tmp)
            self._run("v9.9.9", inst)
            self.assertEqual(g(inst, "rev-parse", "HEAD"), g(inst, "rev-parse", "v9.9.9^{}"),
                             "HEAD landed exactly on the tag — back on the release channel")
            rep = json.loads((km.jd.STATE / "update-report.json").read_text())
            self.assertTrue(rep.get("ok"), rep)
            self.assertEqual((rep.get("restarted"), rep.get("why")), (False, "no manager is running this kernel"),
                             "the no-manager leg says what did not happen, and why")
            log = (km.jd.STATE / "update.log").read_text()
            self.assertIn("return to the release channel", log,
                          "the move is LOUD in the update log, never a silent history jump")

    def test_forward_only_no_path_ever_moves_an_install_backward(self):
        # the user's freeze ruling (2026-08-31): walked-along installs freeze WHERE THEY SIT —
        # never rolled back — and move only when a NEW release offers forward. The guarantee is
        # the offer gate itself: _run_update is reachable only through _update_check, which
        # refuses any tag whose version is not strictly newer than the running one — so the
        # migration's explicit checkout can only ever land on a release AHEAD of the install.
        src = inspect.getsource(km._update_check)
        self.assertIn("if not lv or lv <= cur:", src)
        i_gate = src.index("if not lv or lv <= cur:")
        i_run = src.index("_run_update(latest)")
        self.assertLess(i_gate, i_run, "the strictly-newer gate precedes the only auto _run_update call")

    def test_a_branch_checkout_never_takes_the_fallback(self):
        # the maintainer guard: a main-tracking BRANCH clone ahead of the tag keeps the harmless
        # no-op fast-forward it always had — the fallback yanking it onto a tag would strand the
        # very mesh the channel gate exists to keep noticed
        with tempfile.TemporaryDirectory() as tmp:
            g, inst = self._repos(tmp)
            g(inst, "checkout", "-q", "main")                     # a dev clone, ahead of v9.9.9
            head = g(inst, "rev-parse", "HEAD")
            self._run("v9.9.9", inst)
            self.assertEqual(g(inst, "rev-parse", "HEAD"), head,
                             "branch checkouts are never moved by the migration")
            log = (km.jd.STATE / "update.log").read_text()
            self.assertNotIn("return to the release channel", log)

    def test_the_normal_release_to_release_move_never_takes_the_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            g, inst = self._repos(tmp)
            g(inst, "checkout", "-q", "--detach", "v9.9.8")       # a healthy bootstrap install
            self._run("v9.9.9", inst)
            self.assertEqual(g(inst, "rev-parse", "HEAD"), g(inst, "rev-parse", "v9.9.9^{}"))
            log = (km.jd.STATE / "update.log").read_text()
            self.assertNotIn("return to the release channel", log,
                             "the fast-forward is the whole move — no fallback, no log line")

    def _run_with_manager(self, tag, inst, curl_exit):
        """Like _run, but WITH a manager port and a fake `curl` on PATH standing in for the manager
        door: it records whether the report already existed when the restart was requested, then
        exits as told (0: the manager took it; 7: curl's connection refused). Nothing is dialed."""
        for f in ("update.log", "update-report.json"):
            try:
                (km.jd.STATE / f).unlink()
            except OSError:
                pass
        calls = []
        with mock.patch.object(km.subprocess, "Popen", side_effect=lambda *a, **kw: calls.append(a)), \
             mock.patch.object(km, "ROOT", Path(inst)), \
             mock.patch.object(km, "_release_remote", return_value="origin"), \
             mock.patch.dict(km.os.environ, {"ROMP_MANAGER_PORT": "7777"}):
            km._UPDATE_STATE[0] = ""
            self.assertTrue(km._run_update(tag))
        km._UPDATE_STATE[0] = ""
        fake, seen, args = os.path.join(inst, "fake-bin"), os.path.join(inst, "curl-saw"), os.path.join(inst, "curl-args")
        os.makedirs(fake)
        with open(os.path.join(fake, "curl"), "w") as f:
            f.write("#!/bin/sh\nprintf '%s ' \"$@\" > \"$T_ARGS\"\n"
                    "if [ -e \"$T_REPORT\" ]; then echo present > \"$T_SEEN\"; "
                    "else echo absent > \"$T_SEEN\"; fi\nexit \"$T_CURL_EXIT\"\n")
        os.chmod(os.path.join(fake, "curl"), 0o755)
        env = {**os.environ, "PATH": fake + os.pathsep + os.environ.get("PATH", ""),
               "T_REPORT": str(km.jd.STATE / "update-report.json"), "T_SEEN": seen, "T_ARGS": args,
               "T_CURL_EXIT": str(curl_exit)}
        subprocess.run(["bash", "-c", calls[0][0][2]], cwd=inst, env=env, capture_output=True, text=True)
        rep = json.loads((km.jd.STATE / "update-report.json").read_text())
        with open(seen) as f, open(args) as a:
            return rep, f.read().strip(), a.read().strip()

    def test_the_report_says_what_the_restart_request_actually_did(self):
        # The manager door can be shut (gone, or a stale port). The report used to be written
        # BEFORE the request, claiming restarted:true — an "updated and restarted" report the
        # running kernel leaves for a next boot that never comes: latch wedged, banner "updating…"
        # forever, every later update refused. Executed end to end on a real repo pair.
        with tempfile.TemporaryDirectory() as tmp:
            g, inst = self._repos(tmp)
            g(inst, "checkout", "-q", "--detach", "v9.9.8")
            rep, saw, args = self._run_with_manager("v9.9.9", inst, curl_exit=7)
        self.assertEqual(saw, "absent", "the report is written AFTER the restart request, never before")
        self.assertIn("--max-time 60", args, "the request is bounded: a manager that never answers cannot "
                                             "hold the latch with no report (review find, 2026-09-08)")
        self.assertEqual((rep["ok"], rep["restarted"]), (True, False))
        self.assertIn("port 7777", rep["why"])
        self.assertIn("did not take the restart request", rep["why"])
        with tempfile.TemporaryDirectory() as tmp:
            g, inst = self._repos(tmp)
            g(inst, "checkout", "-q", "--detach", "v9.9.8")
            rep, saw, _ = self._run_with_manager("v9.9.9", inst, curl_exit=0)
        self.assertEqual(saw, "absent")
        self.assertEqual((rep["ok"], rep["restarted"], rep.get("why")), (True, True, None),
                         "a request the manager took is the one report the next boot files")

    def test_a_restart_request_the_manager_never_answers_is_not_a_restart(self):
        # curl's exit 28 is its own timeout: the manager accepted the connection and never answered.
        # Without --max-time that curl hung for good, the report was never written, and the latch
        # held with nothing to consume (review find, 2026-09-08). The timeout reads as not restarted,
        # with a why of its own, and the running kernel's poll consumes it like the refused case.
        with tempfile.TemporaryDirectory() as tmp:
            g, inst = self._repos(tmp)
            g(inst, "checkout", "-q", "--detach", "v9.9.8")
            rep, saw, args = self._run_with_manager("v9.9.9", inst, curl_exit=28)
        self.assertEqual(saw, "absent")
        self.assertIn("--max-time 60", args)
        self.assertEqual((rep["ok"], rep["restarted"]), (True, False))
        self.assertIn("port 7777", rep["why"])
        self.assertIn("did not answer the restart request within 60 s", rep["why"])
        self.assertNotIn("did not take", rep["why"], "a timeout is its own reason, not a refusal")


class BootOnTheTag(Fresh):
    """The boot that already runs the landed tag, judged by the REAL version reader on a repo shaped
    like every release: VERSION bumped in one commit, the tag on the commit after it (the release
    PR's merge), so a checkout exactly on the tag reads `vX.Y.Z+`. The mocked arms above pin the
    comparison; this pins the shape the comparison must survive (review find, 2026-09-08)."""

    def test_a_release_checkout_reads_the_plus_and_the_boot_still_says_it_runs_it(self):
        env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
               "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid"}
        def g(cwd, *args):
            r = subprocess.run(["git", *args], cwd=cwd, env=env, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, "git %s: %s%s" % (" ".join(args), r.stdout, r.stderr))
            return r.stdout.strip()
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "src")
            os.makedirs(src)
            g(src, "init", "-q", "-b", "main")
            with open(os.path.join(src, "VERSION"), "w") as f:
                f.write("9.9.9\n")
            g(src, "add", "VERSION")
            g(src, "commit", "-qm", "VERSION 9.9.9")                       # the bump
            g(src, "commit", "-qm", "merge the release PR", "--allow-empty")   # where the tag lands
            g(src, "tag", "v9.9.9")
            saved_ver, saved_head = km._VER, dict(km._HEAD_CACHE)
            try:
                with mock.patch.object(km, "ROOT", Path(src)):
                    km._VER = None
                    km._HEAD_CACHE.update(ts=0.0, full=None, short=None)
                    self.assertEqual(km._kernel_ver(), "v9.9.9+", "the shape every release checkout reads")
                    (jd.STATE / "update-report.json").write_text(json.dumps(
                        {"ok": True, "tag": "v9.9.9", "restarted": False, "why": "no manager is running this kernel"}))
                    rep = km._consume_update_report()
            finally:
                km._VER = saved_ver
                km._HEAD_CACHE.clear()
                km._HEAD_CACHE.update(saved_head)
        self.assertTrue(rep["ok"])
        ns = self.notices()
        self.assertEqual(len(ns), 1)
        self.assertIn("this start is running it", ns[0]["text"])
        self.assertNotIn("restart romp yourself", ns[0]["text"])


if __name__ == "__main__":
    unittest.main()
