#!/usr/bin/env python3
"""The global retry-pause is an API-HEALTH flag, not a permanent switch. The user flips "stop all
auto-retries" to calm the auto-retry + judge storm during an API / usage-limit outage — but the judge
tier is gated on `not _retry_paused_on()`, so a pause that never clears silently kills EVERY judge for
hours (the user 2026-06-30, who noted none of the judges were running and called it an API problem that should
clear the second a successful non-API-error response arrives on any session). _auto_resume_retry
clears it event-based: the first live session that is NOT blocked on an API error AND wrote fresh output
since the pause began (mtime past the pause floor) proves the account can serve requests again.
"""
import json
import os
import tempfile
import time
import unittest
from datetime import datetime, timezone
from romp_load import load_source
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
km = load_source("romp_kernel_rp", os.path.join(BIN, "romp-kernel"))


class RetryPauseAutoResume(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.dir = Path(self.td.name)
        self._orig_state = km.jd.STATE
        km.jd.STATE = self.dir                          # retry-paused.json lives under jd.STATE
        self._orig_alive = km._alive_sessions
        self._orig_apierr = km._api_error
        self._orig_push = km._push_all
        km._push_all = lambda *a, **k: self.fail("a tick job built a push inline (P1 removed those)")
        self._orig_rearm = km.jd.rearm_failed_summaries
        km.jd.rearm_failed_summaries = lambda now, **k: 0   # no given-up cards unless a test says so
        self._was_set = km._pusher_wake.is_set()
        km._pusher_wake.clear()

    def tearDown(self):
        km.jd.STATE = self._orig_state
        km._alive_sessions = self._orig_alive
        km._api_error = self._orig_apierr
        km._push_all = self._orig_push
        km.jd.rearm_failed_summaries = self._orig_rearm
        if self._was_set:
            km._pusher_wake.set()
        else:
            km._pusher_wake.clear()
        self.td.cleanup()

    def _transcript(self, name, mtime):
        p = self.dir / name
        p.write_text("{}\n")
        os.utime(p, (mtime, mtime))
        return str(p)

    # --- the flag records its pause instant ---
    def test_pause_records_a_floor_timestamp(self):
        km._set_retry_paused(True)
        self.assertTrue(km._retry_paused_on())
        self.assertGreater(km._retry_pause_ts(), 0, "a pause records WHEN it began (the auto-resume floor)")
        km._set_retry_paused(False)
        self.assertFalse(km._retry_paused_on())
        self.assertEqual(km._retry_pause_ts(), 0.0, "un-pausing drops the floor")

    # --- recovery clears it ---
    def test_fresh_healthy_session_clears_the_pause(self):
        km._set_retry_paused(True)
        floor = km._retry_pause_ts()
        path = self._transcript("healthy.jsonl", floor + 5)   # wrote output AFTER the pause
        km._alive_sessions = lambda now, tmux: [{"sid": "s1", "path": path}]
        km._api_error = lambda p: None                        # not blocked on an API error
        km._auto_resume_retry(int(time.time()), {})
        self.assertFalse(km._retry_paused_on(), "a served request after the pause proves recovery → resume")

    # --- an api-errored session is NOT proof of recovery ---
    def test_still_errored_session_keeps_the_pause(self):
        km._set_retry_paused(True)
        floor = km._retry_pause_ts()
        path = self._transcript("errored.jsonl", floor + 5)   # fresh mtime, but the last record is an API error
        km._alive_sessions = lambda now, tmux: [{"sid": "s1", "path": path}]
        km._api_error = lambda p: {"text": "overloaded", "status": 529}
        km._auto_resume_retry(int(time.time()), {})
        self.assertTrue(km._retry_paused_on(), "a session still blocked on an API error must not clear the pause")

    # --- a stale success (from before the outage) is NOT proof ---
    def test_stale_session_keeps_the_pause(self):
        km._set_retry_paused(True)
        floor = km._retry_pause_ts()
        path = self._transcript("stale.jsonl", floor - 60)    # last wrote BEFORE the pause
        km._alive_sessions = lambda now, tmux: [{"sid": "s1", "path": path}]
        km._api_error = lambda p: None
        km._auto_resume_retry(int(time.time()), {})
        self.assertTrue(km._retry_paused_on(), "no fresh output since the pause → no evidence the API recovered")

    # --- no-op when not paused ---
    def test_noop_when_not_paused(self):
        km._set_retry_paused(False)
        called = []
        km._alive_sessions = lambda now, tmux: called.append(1) or []
        km._auto_resume_retry(int(time.time()), {})
        self.assertEqual(called, [], "not paused → the resume check does no work")

    # --- delivery (perf batch 2 P1, 2026-09-06): a wake, and a dirty mark only for a store write ---
    def _recovered(self):
        km._set_retry_paused(True)
        floor = km._retry_pause_ts()
        path = self._transcript("healthy.jsonl", floor + 5)
        km._alive_sessions = lambda now, tmux: [{"sid": "s1", "path": path}]
        km._api_error = lambda p: None

    def test_the_clear_wakes_the_pusher_and_leaves_the_views_clean(self):
        self._recovered()
        km._pusher_wake.clear()
        floor = km._views_dirty[0]
        km._auto_resume_retry(int(time.time()), {})
        self.assertFalse(km._retry_paused_on())
        self.assertTrue(km._pusher_wake.is_set(), "the clear wakes the pusher; globalRetryPaused rides its push")
        self.assertEqual(km._views_dirty[0], floor, "no view reads the flag, and nothing was re-armed")

    def test_a_re_arm_marks_the_views_dirty(self):
        # the ONE write on this path the feed shows: a given-up card's summary sentinel goes back to None
        self._recovered()
        km.jd.rearm_failed_summaries = lambda now, **k: 2
        floor = km._views_dirty[0]
        km._auto_resume_retry(int(time.time()), {})
        self.assertGreater(km._views_dirty[0], floor, "store writes the cards show → rebuild past the sig")
        self.assertTrue(km._pusher_wake.is_set())

    def test_the_no_op_paths_neither_wake_nor_dirty(self):
        floor = km._views_dirty[0]
        km._set_retry_paused(False)
        km._auto_resume_retry(int(time.time()), {})
        self.assertFalse(km._pusher_wake.is_set(), "not paused: nothing to deliver")
        km._set_retry_paused(True)
        pfloor = km._retry_pause_ts()
        path = self._transcript("stale.jsonl", pfloor - 60)
        km._alive_sessions = lambda now, tmux: [{"sid": "s1", "path": path}]
        km._api_error = lambda p: None
        km._auto_resume_retry(int(time.time()), {})
        self.assertTrue(km._retry_paused_on())
        self.assertFalse(km._pusher_wake.is_set(), "still paused: nothing to deliver")
        self.assertEqual(km._views_dirty[0], floor)


    # --- the bottom bar's API health cell (2026-09-07) reads the pause and its lift off this same file ---
    def test_the_api_health_frame_reads_paused_limit_then_ok_after_the_clear(self):
        km._set_retry_paused(True, reason="limit")
        floor = km._retry_pause_ts()
        path = str(self.dir / "healthy.jsonl")
        with open(path, "w") as f:
            f.write(_out_line(floor + 5))                      # a login-billed session's answer after the pause
        live = {"s1": {"state": "idle", "auth": "login", "backend": "sdk"}}
        km._alive_sessions = lambda now, tmux: [{"sid": "s1", "name": "web", "path": path}]
        km._api_error = lambda p: None
        saved = km.Sessions.__dict__["backend_for"]
        km.Sessions.backend_for = staticmethod(lambda sid: object())
        km._api_last_failed_cache.clear()
        try:
            f = km._api_health_frame(int(time.time()), live)
            self.assertEqual((f["state"], f["reason"], f["text"]), ("paused", "limit", "paused \u00b7 usage limit"))
            self.assertEqual(f["since"], int(floor), "the pause's own t, not the clock")
            km._auto_resume_retry(int(time.time()), live)
            self.assertFalse(km._retry_paused_on())
            f = km._api_health_frame(int(time.time()), live)
            self.assertEqual((f["state"], f["reason"], f["text"], f["since"]), ("ok", "", "ok", 0))
        finally:
            km.Sessions.backend_for = saved
            km._api_last_failed_cache.clear()


# ── a usage-limit pause lifts on a LOGIN-billed session's fresh ASSISTANT output only (review round 1, 2026-09-07) ──
def _iso(t):
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _out_line(t):
    return json.dumps({"type": "assistant", "uuid": "aaaaaaaa-0000-0000-0000-%012d" % int(t), "timestamp": _iso(t),
                       "message": {"role": "assistant", "content": [{"type": "text", "text": "done"}]}}) + "\n"


def _prompt_line(t, text="please continue"):
    return json.dumps({"type": "user", "uuid": "bbbbbbbb-0000-0000-0000-%012d" % int(t), "timestamp": _iso(t),
                       "message": {"role": "user", "content": [{"type": "text", "text": text}]}}) + "\n"


SID_KEY = "88888888-aaaa-4bbb-8ccc-000000000001"     # a private synthetic family for this module
SID_LOGIN = "88888888-aaaa-4bbb-8ccc-000000000002"


class LimitPauseLift(unittest.TestCase):
    """A usage-limit pause used to lift on ANY alive session whose transcript mtime passed the floor with no
    current _api_error: a key-billed session's streaming output or a human prompt qualified, _auto_pause_on_limit
    re-engaged the next cycle while the window held, and the pause file (so the bottom bar's API cell) flipped
    on every write. The lift now needs a LOGIN-billed session's fresh ASSISTANT output record: the account the
    limit is on, and the API's own answer. The spend and manual pauses keep their mtime rule."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.dir = Path(self.td.name)
        self._orig = (km.jd.STATE, km._alive_sessions, km._push_all, km.jd.rearm_failed_summaries, km._usage,
                      km._send_to_app, km.Sessions.__dict__["backend_for"], km._auth_key_present)
        km.jd.STATE = self.dir
        km._push_all = lambda *a, **k: self.fail("a tick job built a push inline (P1 removed those)")
        km.jd.rearm_failed_summaries = lambda now, **k: 0
        km._usage = lambda: {"limited": {"5h": True}}          # the login account's window is at 100%
        self.sent = []
        km._send_to_app = lambda app, m: self.sent.append((app, m))
        km.Sessions.backend_for = staticmethod(lambda sid: object())
        km._auth_key_present = lambda: True                    # a key exists on this box
        km._APIH_LAST[0] = None
        km._api_err_cache.clear()
        km._api_last_failed_cache.clear()
        self._was_set = km._pusher_wake.is_set()
        km._pusher_wake.clear()

    def tearDown(self):
        (km.jd.STATE, km._alive_sessions, km._push_all, km.jd.rearm_failed_summaries, km._usage,
         km._send_to_app, km.Sessions.backend_for, km._auth_key_present) = self._orig
        km._APIH_LAST[0] = None
        km._api_err_cache.clear()
        km._api_last_failed_cache.clear()
        if self._was_set:
            km._pusher_wake.set()
        else:
            km._pusher_wake.clear()
        self.td.cleanup()

    def _session(self, sid, name, auth, *lines):
        p = self.dir / (name + ".jsonl")
        p.write_text("".join(lines))
        km._alive_sessions = lambda now, tmux: [{"sid": sid, "name": name, "path": str(p)}]
        return str(p), {sid: {"state": "idle", "auth": auth, "authLive": auth, "backend": "sdk"}}

    def _cycle(self, now, live):
        # the pusher's jobs in their order: the limit engages the pause, the resume check, then the frame
        km._auto_pause_on_limit()
        km._auto_resume_retry(now, live)
        f = km._api_health_frame(now, live)
        km._api_health_push(f)
        return f["state"]

    def test_a_key_billed_session_s_output_during_a_limit_leaves_the_pause_and_the_frame_stable(self):
        # the review's probe: a limited window, one key-billed session appending an answer every other cycle
        now = time.time()
        path, live = self._session(SID_KEY, "web", "key", _out_line(now - 60))
        states = []
        for i in range(6):
            if i % 2:
                with open(path, "a") as f:
                    f.write(_out_line(now + i))
                os.utime(path, (now + i, now + i))
            states.append(self._cycle(int(now) + i, live))
        self.assertEqual(states, ["paused"] * 6, "a key-billed session's output says nothing about the login limit")
        self.assertEqual([m["state"] for a, m in self.sent], ["paused"], "one frame: nothing about the API changed")
        self.assertEqual(km._retry_pause_reason(), "limit")

    def test_a_login_billed_session_s_fresh_assistant_output_lifts_it_once(self):
        now = time.time()
        path, live = self._session(SID_LOGIN, "api", "login", _out_line(now - 60))
        self.assertEqual(self._cycle(int(now), live), "paused")
        floor = km._retry_pause_ts()
        os.utime(path, (floor + 1, floor + 1))                 # a fresh mtime over OLD output: not proof
        km._auto_resume_retry(int(now), live)
        self.assertTrue(km._retry_paused_on(), "output from before the pause proves nothing")
        with open(path, "a") as f:
            f.write(_prompt_line(floor + 2))
        km._auto_resume_retry(int(now), live)
        self.assertTrue(km._retry_paused_on(), "a prompt is not the API's answer")
        with open(path, "a") as f:
            f.write(_out_line(floor + 5))                      # the login account served a request
        km._usage = lambda: {"limited": {}}                    # and its usage report caught up
        self.assertEqual(self._cycle(int(now) + 1, live), "ok")
        self.assertFalse(km._retry_paused_on())
        self.assertEqual([m["state"] for a, m in self.sent], ["paused", "ok"], "each side of the lift sent once")

    def test_spend_and_manual_pauses_keep_lifting_on_any_fresh_transcript(self):
        km._usage = lambda: {"limited": {}}
        now = time.time()
        for reason in ("spend", ""):
            path, live = self._session(SID_KEY, "web", "key", _out_line(now - 60))
            km._set_retry_paused(True, reason=reason)
            floor = km._retry_pause_ts()
            os.utime(path, (floor + 1, floor + 1))
            km._auto_resume_retry(int(now), live)
            self.assertFalse(km._retry_paused_on(), "reason %r: the mtime rule is unchanged" % reason)

    def test_a_session_of_unknown_auth_bills_the_login_only_when_this_box_holds_no_key(self):
        now = time.time()
        path, _ = self._session(SID_LOGIN, "tests", "", _out_line(now - 60))
        live = {SID_LOGIN: {"state": "idle"}}                  # a tmux row: no auth fields at all
        self.assertEqual(self._cycle(int(now), live), "paused")
        floor = km._retry_pause_ts()
        with open(path, "a") as f:
            f.write(_out_line(floor + 5))
        km._auth_key_present = lambda: True
        km._auto_resume_retry(int(now), live)
        self.assertTrue(km._retry_paused_on(), "a key on the box: this session may be billing it")
        km._auth_key_present = lambda: False
        km._auto_resume_retry(int(now), live)
        self.assertFalse(km._retry_paused_on(), "no key anywhere: the login is the only account it can bill")


if __name__ == "__main__":
    unittest.main()
