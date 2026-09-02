#!/usr/bin/env python3
"""The API-health signal (GET /api-health): ingestion, windows, derived state, labels, ledger.

The kernel already parses every frame the signal needs — the per-attempt api_retry SystemMessage, the
per-response AssistantMessage, the settling ResultMessage — and kept them per session, for one chat
card. The aggregator (sdk_backend.ApiHealth) folds them into one ring keyed by (auth label, model
family) and derives a thrash/degraded/recovering state from the ring at read time. These tests drive
the REAL _on_message with duck-typed frames (the test doubles the retry-detail and give-up suites
use), then the pure functions with hand-built events.

Everything is synthetic: placeholder sids, TESTHOST, an invented key material that is not shaped
like any real credential (assembled, never a credential-shaped literal — the scanner reads this
repo too), and a rebuilt timeline of the incident the design note backtested — its SHAPE, not its
data. State is redirected before the module loads.
"""
import inspect
import json
import os
import stat
import tempfile
import time
import unittest
from importlib.machinery import SourceFileLoader

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
sb = SourceFileLoader("romp_sdk_backend_apihealth", os.path.join(BIN, "romp_sdk_backend.py")).load_module()

SID = "11111111-2222-3333-4444-555555555555"
SID2 = "11111111-2222-3333-4444-666666666666"
KEY_MATERIAL = "test-key-material-" + "q" * 28   # invented; not shaped like any provider's key
# A resolved bucket label, as a session would cache it — DERIVED at run time from the real function,
# never written out: a literal `key:<hex>` is exactly what the credential scanner reads this repo for.
LABEL = sb.api_health_auth_label("ANTHROPIC_API_KEY", salt="test-salt", work_key=KEY_MATERIAL,
                                 launched_keyed=True)
T0 = 1_756_800_000.0                # a fixed synthetic epoch (the sweep is pure in `now`)


# ---- duck-typed frames: _on_message matches on the CLASS objects passed in; msg_to_atom on the NAME ----

class FakeSystemMessage:
    def __init__(self, subtype, data, parent_tool_use_id=None):
        self.subtype, self.data = subtype, data
        self.parent_tool_use_id = parent_tool_use_id


class FakeAssistantMessage:
    def __init__(self, model="claude-fable-5-1", message_id="msg_aaaa", error=None,
                 parent_tool_use_id=None, uuid="u-1"):
        self.model, self.message_id, self.error = model, message_id, error
        self.parent_tool_use_id, self.uuid, self.content = parent_tool_use_id, uuid, []


FakeAssistantMessage.__name__ = "AssistantMessage"


class FakeResultMessage:
    def __init__(self, is_error=False, api_error_status=None, parent_tool_use_id=None):
        self.is_error, self.api_error_status = is_error, api_error_status
        self.parent_tool_use_id = parent_tool_use_id


# The wire frame the 2.1.257 CLI emits for one retry attempt (field names per the design note; the
# values are invented). error_status is the int the aggregator classifies on; `error` the category.
def retry_frame(status=429, category="rate_limit", attempt=1, **extra):
    d = {"attempt": attempt, "max_retries": 10, "retry_delay_ms": 2000,
         "error_status": status, "error": category, "uuid": "u-retry-%d" % attempt, "session_id": SID}
    d.update(extra)
    return d


def _backend(log=None):
    return sb.SdkBackend(tempfile.mkdtemp(), "/bin/true", lambda *a, **k: None, log=log)


def _session(be, sid=SID, label=LABEL, model_id="claude-fable-5-1"):
    """The retry/settle state alone — SdkSession.__init__ builds a whole client/thread these don't need.
    _learn_model is stubbed: the response's model is read by the aggregator hook directly, and the
    real learner needs the model-pending machinery this double does not carry."""
    s = object.__new__(sb.SdkSession)
    s.backend, s.sid, s.name = be, sid, "web"
    s.resume_sid = None
    s.retrying, s.retry_count, s.retry_info = False, 0, None
    s.auth_label, s._ah_turn, s._ah_gaveup = label, 0, None
    s._model_id, s.model, s.chosen_model = model_id, "Fable 5", ""
    s._skill_tool_ids, s._cli_working = set(), True
    s.marks = []
    s._mark = lambda st: s.marks.append(st)
    s._learn_model = lambda pm, raw="": None
    return s


def _feed(s, msg):
    s._on_message(msg, FakeAssistantMessage, FakeResultMessage, FakeSystemMessage)


def _bucket(be, label=LABEL, family="fable", now=None):
    snap = be.api_health_snapshot(now or time.time())
    return snap["buckets"].get("%s|%s" % (label, family))


def _win(be, w="60", **kw):
    b = _bucket(be, **kw)
    return b["windows"][w] if b else None


class IngestsTheRealBranches(unittest.TestCase):
    """The hooks live IN the branches _on_message already runs — one parse, two consumers."""

    def test_an_api_retry_frame_counts_one_attempt_in_the_sessions_bucket(self):
        be = _backend()
        s = _session(be)
        _feed(s, FakeSystemMessage("api_retry", retry_frame(429, "rate_limit")))
        w = _win(be)
        self.assertIsNotNone(w, "the bucket is keyed (auth label, family) from the session")
        self.assertEqual((w["requests"], w["rateLimited"], w["retries"]), (1, 1, 1))
        self.assertEqual((w["sessionsRetrying"], w["turnsRetrying"]), (1, 1))
        self.assertEqual(w["rate429"], 1.0)
        # …and the retry-detail consumer still saw the same frame (the branch was not forked)
        self.assertTrue(s.retrying)
        self.assertEqual(s.marks, ["retrying"])

    def test_the_hook_sits_in_the_existing_api_retry_branch_not_a_second_subscription(self):
        src = inspect.getsource(sb.SdkSession._on_message)
        i_branch = src.index('msg.subtype == "api_retry"')
        i_hook = src.index("self._ah_note_retry(d, msg, _status)")
        i_mark = src.index('self._mark("retrying")')
        self.assertTrue(i_branch < i_hook < i_mark, "the aggregator is fed from the same branch, before the mark")
        self.assertNotIn("retriesRecovered", inspect.getsource(sb.ApiHealth),
                         "the settle-time recovery ledger has no per-attempt status — never a source")

    def test_statuses_classify_into_their_counters(self):
        be = _backend()
        s = _session(be)
        for st, cat in ((429, "rate_limit"), (529, "overloaded"), (503, "server_error"),
                        (400, "unknown"), (None, "unknown")):
            _feed(s, FakeSystemMessage("api_retry", retry_frame(st, cat)))
        w = _win(be)
        self.assertEqual(w["rateLimited"], 1)
        self.assertEqual(w["overloaded"], 1)
        self.assertEqual(w["serverErrors"], 1)
        self.assertEqual(w["otherErrors"], 1)
        self.assertEqual(w["noStatus"], 1, "a status-less attempt is reported…")
        self.assertEqual(w["requests"], 4, "…and excluded from the denominator")
        self.assertEqual(w["retries"], 5)

    def test_a_category_alone_classifies_when_the_status_is_null(self):
        self.assertEqual(sb.api_health_status_class(None, "overloaded"), "529")
        self.assertEqual(sb.api_health_status_class(None, "rate_limit"), "429")
        self.assertEqual(sb.api_health_status_class(None, "server_error"), "5xx")
        self.assertEqual(sb.api_health_status_class(None, "authentication_failed"), "other")
        self.assertEqual(sb.api_health_status_class(None, "unknown"), "none")
        self.assertEqual(sb.api_health_status_class("529", ""), "529", "a digit string is a status too")
        self.assertEqual(sb.api_health_status_class(True, "rate_limit"), "429", "a bool is not a status")

    def test_an_assistant_response_counts_one_ok_per_message_id(self):
        be = _backend()
        s = _session(be)
        # the CLI emits one frame per content block; every frame of one response carries the same id
        for _ in range(3):
            _feed(s, FakeAssistantMessage(message_id="msg_one"))
        _feed(s, FakeAssistantMessage(message_id="msg_two"))
        w = _win(be)
        self.assertEqual(w["ok"], 2, "three frames of one response are ONE ok")
        self.assertEqual(w["requests"], 2)

    def test_a_synthetic_assistant_record_is_not_a_response(self):
        be = _backend()
        s = _session(be)
        _feed(s, FakeAssistantMessage(model="<synthetic>", message_id="msg_syn"))
        _feed(s, FakeAssistantMessage(model="", message_id="msg_empty"))
        self.assertIsNone(_bucket(be), "nothing counted → no bucket")

    def test_sidechain_frames_are_ignored_on_both_sides(self):
        """A subagent's retries never reach the SDK (the CLI folds them into a tool_progress frame it
        drops), so its responses must not count either — symmetric exclusion, or every storm's rate
        is diluted by subagent oks that carried no retries."""
        be = _backend()
        s = _session(be)
        _feed(s, FakeAssistantMessage(message_id="msg_sub", parent_tool_use_id="toolu_01"))
        _feed(s, FakeSystemMessage("api_retry", retry_frame(429, "rate_limit"), parent_tool_use_id="toolu_01"))
        _feed(s, FakeSystemMessage("api_retry", retry_frame(429, "rate_limit", parent_tool_use_id="toolu_01")))
        self.assertIsNone(_bucket(be), "no sidechain frame reaches the ring")
        snap = be.api_health_snapshot()
        self.assertIs(snap["coverage"]["sidechainExcluded"], True, "the payload says so")

    def test_the_ok_hook_checks_parent_tool_use_id_itself(self):
        # the recovery-marker writes sit ABOVE the branch's sidechain guard (m = None); the aggregator
        # must not inherit that false trigger — its own check comes first
        src = inspect.getsource(sb.SdkSession._on_message)
        i_hook = src.index("self._ah_note_assistant(msg)")
        i_guard = src.index('if getattr(msg, "parent_tool_use_id", None):\n                m = None')
        self.assertLess(i_hook, i_guard)
        self.assertIn('if getattr(msg, "parent_tool_use_id", None):\n            return',
                      inspect.getsource(sb.SdkSession._ah_note_assistant))

    def test_a_give_up_pairs_the_error_frame_with_the_settles_status(self):
        """The error-stamped AssistantMessage arrives BEFORE the ResultMessage that carries
        api_error_status, so the frame parks a marker and the settle files the give-up with the status."""
        be = _backend()
        s = _session(be)
        _feed(s, FakeAssistantMessage(model="<synthetic>", message_id="msg_err", error="rate_limit"))
        self.assertIsNotNone(s._ah_gaveup, "the marker is pending")
        self.assertIsNone(_bucket(be), "…and nothing is filed until the settle names the status")
        s._ah_note_result(FakeResultMessage(is_error=True, api_error_status=429))
        w = _win(be)
        self.assertEqual(w["gaveUp"], 1)
        self.assertEqual(w["rateLimited"], 1, "the give-up IS the turn's last failed attempt — status-counted too")
        self.assertEqual(w["ok"], 0)
        self.assertIsNone(s._ah_gaveup, "the marker is spent")
        self.assertEqual(_bucket(be)["lastError"]["status"], 429)

    def test_the_settle_branch_calls_the_hook(self):
        src = inspect.getsource(sb.SdkSession._on_message)
        i_branch = src.index("elif isinstance(msg, ResultMessage):")
        i_hook = src.index("self._ah_note_result(msg)")
        self.assertLess(i_branch, i_hook)
        self.assertLess(i_hook - i_branch, 200, "at the top of the branch, before the settle's own work")

    def test_a_give_up_without_a_status_falls_back_to_its_category(self):
        be = _backend()
        s = _session(be)
        _feed(s, FakeAssistantMessage(model="<synthetic>", message_id="msg_err", error="server_error"))
        s._ah_note_result(FakeResultMessage(is_error=True, api_error_status=None))
        w = _win(be)
        self.assertEqual((w["gaveUp"], w["serverErrors"]), (1, 1))

    def test_a_give_up_is_counted_without_a_storm(self):
        # the existing retriesGaveUp chat marker is gated on self.retrying and has never fired for the
        # give-ups that arrive with no retry frame before them; the signal counts every one
        be = _backend()
        s = _session(be)
        self.assertFalse(s.retrying)
        _feed(s, FakeAssistantMessage(model="<synthetic>", message_id="msg_err", error="billing_error"))
        s._ah_note_result(FakeResultMessage(is_error=True, api_error_status=402))
        self.assertEqual(_win(be)["gaveUp"], 1)
        self.assertEqual(_win(be)["otherErrors"], 1)

    def test_an_error_settle_with_a_status_but_no_frame_still_counts_once(self):
        be = _backend()
        s = _session(be)
        s._ah_note_result(FakeResultMessage(is_error=True, api_error_status=500))
        self.assertEqual(_win(be)["gaveUp"], 1)
        s._ah_note_result(FakeResultMessage(is_error=False, api_error_status=None))
        self.assertEqual(_win(be)["gaveUp"], 1, "a clean settle files nothing")

    def test_turns_and_sessions_retrying_are_distinct_counts(self):
        be = _backend()
        a, b = _session(be, sid=SID), _session(be, sid=SID2)
        for i in range(4):
            _feed(a, FakeSystemMessage("api_retry", retry_frame(429, "rate_limit", attempt=i + 1)))
        a._ah_note_result(FakeResultMessage())            # the turn settles → the next storm is a new turn
        for i in range(3):
            _feed(a, FakeSystemMessage("api_retry", retry_frame(429, "rate_limit", attempt=i + 1)))
        _feed(b, FakeSystemMessage("api_retry", retry_frame(429, "rate_limit")))
        w = _win(be)
        self.assertEqual(w["retries"], 8, "attempts")
        self.assertEqual(w["turnsRetrying"], 3, "two turns of one session + one of the other")
        self.assertEqual(w["sessionsRetrying"], 2)
        self.assertEqual(be.api_health_snapshot()["rate429Basis"], "attempts")

    def test_retries_use_the_sessions_last_model_and_oks_the_responses_own(self):
        be = _backend()
        s = _session(be, model_id="claude-opus-4-8")
        _feed(s, FakeSystemMessage("api_retry", retry_frame(529, "overloaded")))
        _feed(s, FakeAssistantMessage(model="claude-haiku-4-5-20251001", message_id="msg_h"))
        snap = be.api_health_snapshot()
        self.assertIn(LABEL + "|opus", snap["buckets"], "the frame carries no model → the session's")
        self.assertIn(LABEL + "|haiku", snap["buckets"], "the response names its own")
        self.assertEqual(snap["buckets"][LABEL + "|haiku"]["windows"]["60"]["ok"], 1)

    def test_doubles_without_the_aggregator_pass_through(self):
        # the retry-detail suite's _Backend has no api_health; the hooks must not require it
        class _B:
            def _poke(self): pass
            def _forward(self, s, m): pass
        s = object.__new__(sb.SdkSession)
        s.backend, s.sid = _B(), SID
        s.retrying, s.retry_count, s.retry_info = False, 0, None
        s._mark = lambda st: None
        _feed(s, FakeSystemMessage("api_retry", retry_frame()))
        s._ah_note_result(FakeResultMessage(is_error=True, api_error_status=500))
        self.assertEqual(s._ah_turn, 1)


class Windows(unittest.TestCase):
    """api_health_counts over hand-built events: (now - w, now], the three windows, completeness."""

    def _ev(self, t, cls="ok", kind=None, sid="s1", turn=0):
        kind = kind or ("ok" if cls == "ok" else "retry")
        return sb.AhEvent(t, LABEL, "fable", kind, cls, 429 if cls == "429" else None, sid, turn)

    def test_each_window_sees_only_its_own_span(self):
        evs = [self._ev(T0 - 30), self._ev(T0 - 200, "429"), self._ev(T0 - 800), self._ev(T0 - 1000)]
        self.assertEqual(sb.api_health_counts(evs, T0, 60)["requests"], 1)
        self.assertEqual(sb.api_health_counts(evs, T0, 300)["requests"], 2)
        self.assertEqual(sb.api_health_counts(evs, T0, 900)["requests"], 3)
        self.assertEqual(sb.api_health_counts(evs, T0, 300)["rate429"], 0.5)

    def test_the_boundary_is_half_open(self):
        evs = [self._ev(T0 - 60), self._ev(T0)]
        self.assertEqual(sb.api_health_counts(evs, T0, 60)["requests"], 1,
                         "an event exactly one window old has left; one at `now` is in")

    def test_rates_are_null_at_zero_requests(self):
        w = sb.api_health_counts([self._ev(T0 - 5, "none")], T0, 60)
        self.assertEqual((w["requests"], w["noStatus"]), (0, 1))
        self.assertIsNone(w["rate429"])
        self.assertIsNone(w["rate5xx"])

    def test_completeness_follows_uptime(self):
        self.assertFalse(sb.api_health_counts([], T0, 900, uptime_s=100)["complete"])
        self.assertTrue(sb.api_health_counts([], T0, 60, uptime_s=100)["complete"])
        self.assertTrue(sb.api_health_counts([], T0, 900)["complete"], "unknown uptime is not a claim of incompleteness")

    def test_5xx_rate_pools_overloaded_and_server_errors(self):
        evs = [self._ev(T0 - 1, "529"), self._ev(T0 - 2, "5xx"), self._ev(T0 - 3), self._ev(T0 - 4)]
        self.assertEqual(sb.api_health_counts(evs, T0, 60)["rate5xx"], 0.5)


def _storm(t_from, t_to, step=15.0, share=(3, 4), label=LABEL, family="fable", sid="s1"):
    """Attempts every `step` seconds; the pattern positions in `share` (of 5) are 429s — 40% by default."""
    out, t, i = [], t_from, 0
    while t < t_to:
        is429 = (i % 5) in share
        out.append(sb.AhEvent(t, label, family, "retry" if is429 else "ok", "429" if is429 else "ok",
                              429 if is429 else None, sid, i // 20))
        t += step
        i += 1
    return out


def _clean(t_from, t_to, step=15.0, label=LABEL, family="fable", sid="s1"):
    return _storm(t_from, t_to, step, share=(), label=label, family=family, sid=sid)


def _runs(evs, t_from, t_to, step=5, cfg=None):
    """Sample the pure state every `step` s and return the distinct-state runs [(minutes, state)]."""
    cfg = cfg or sb.api_health_config()
    seq, last = [], None
    for now in range(int(t_from), int(t_to), step):
        st = sb.api_health_state(evs, now, cfg)["state"]
        if st != last:
            seq.append((round((now - t_from) / 60.0, 2), st))
            last = st
    return seq


class DerivedState(unittest.TestCase):
    """api_health_state is a pure function of the events and `now` — nothing else."""

    def setUp(self):
        self.cfg = sb.api_health_config()

    def test_no_evidence_is_unknown_never_a_held_claim(self):
        st = sb.api_health_state([], T0, self.cfg)
        self.assertEqual(st["state"], "unknown")
        self.assertFalse(st["evidence"]["sufficient"])
        few = _storm(T0 - 100, T0, share=(0, 1, 2, 3, 4))[:9]     # nine 429s: under minRequests
        self.assertEqual(sb.api_health_state(few, T0, self.cfg)["state"], "unknown")

    def test_a_clean_bucket_with_evidence_is_healthy(self):
        st = sb.api_health_state(_clean(T0 - 290, T0), T0, self.cfg)
        self.assertEqual(st["state"], "healthy")
        self.assertTrue(st["evidence"]["sufficient"])

    def test_the_mid_window_enters_thrashing_at_the_threshold(self):
        evs = _storm(T0 - 290, T0, step=29, share=(3, 4))       # 10 attempts, 4 of them 429 → 0.40
        st = sb.api_health_state(evs, T0, self.cfg)
        self.assertEqual(st["state"], "thrashing")
        self.assertIn("rate429 over 300 s", st["why"])
        self.assertIn("attempts", st["why"], "the basis is named in the reason")

    def test_the_slow_window_enters_on_a_lower_share(self):
        # 0.16 over 900 s with the 300 s window clean and insufficient: the slow path alone
        evs = [sb.AhEvent(T0 - 800 + i * 4, LABEL, "fable", "retry" if i < 4 else "ok",
                          "429" if i < 4 else "ok", 429 if i < 4 else None, "s1", 0) for i in range(25)]
        st = sb.api_health_state(evs, T0, self.cfg)
        self.assertEqual(st["state"], "thrashing")
        self.assertIn("over 900 s", st["why"])

    def test_the_fast_path_needs_its_own_larger_minimum(self):
        ten = _storm(T0 - 50, T0, step=5, share=(0, 1, 2, 3, 4))[:10]     # 10 attempts, all 429, in 60 s
        st = sb.api_health_state(ten, T0, self.cfg)
        self.assertEqual(st["state"], "thrashing", "the 300 s window also holds these ten → its path fires")
        # isolate the fast path: heavy clean traffic keeps the 300 s and 900 s shares under their
        # thresholds, a one-minute gap keeps the 60 s window from ever straddling clean and burst
        # (the sweep evaluates EVERY breakpoint, so a window that slid over both would fire), then a
        # burst of 429s in the last minute
        heavy = _clean(T0 - 890, T0 - 120, step=1)                    # 770 clean attempts
        evs = heavy + _storm(T0 - 59, T0, step=4, share=(0, 1, 2, 3, 4))      # 15 × 429 in 60 s
        st = sb.api_health_state(evs, T0, self.cfg)
        self.assertEqual(st["state"], "healthy", "15 < fastMinRequests; 300 s ≈ 0.08, 900 s ≈ 0.02")
        evs = heavy + _storm(T0 - 59, T0, step=2.5, share=(0, 1, 2, 3, 4))    # 24 × 429 in 60 s
        st = sb.api_health_state(evs, T0, self.cfg)
        self.assertEqual(st["state"], "thrashing", "24 ≥ fastMinRequests at 100%: the fast path alone fires")
        self.assertIn("over 60 s", st["why"])

    def test_degraded_on_server_errors_and_thrashing_wins_when_both(self):
        evs = [sb.AhEvent(T0 - 200 + i * 10, LABEL, "fable", "retry" if i < 4 else "ok",
                          "529" if i < 2 else ("5xx" if i < 4 else "ok"), None, "s1", 0) for i in range(12)]
        st = sb.api_health_state(evs, T0, self.cfg)
        self.assertEqual(st["state"], "degraded")
        self.assertIn("rate5xx", st["why"])
        both = evs + [sb.AhEvent(T0 - 100 + i, LABEL, "fable", "retry", "429", 429, "s1", 0) for i in range(4)]
        self.assertEqual(sb.api_health_state(both, T0, self.cfg)["state"], "thrashing")

    def test_exit_needs_both_windows_clean_and_holds_then_recovers(self):
        # a storm long enough to fill the slow window, then clean traffic
        evs = _storm(T0, T0 + 1800) + _clean(T0 + 1800, T0 + 1800 + 1500)
        runs = _runs(evs, T0, T0 + 1800 + 1500, cfg=self.cfg)
        states = [s for _, s in runs]
        self.assertEqual(states, ["unknown", "thrashing", "recovering", "healthy"])
        t_rec = [m for m, s in runs if s == "recovering"][0]
        t_ok = [m for m, s in runs if s == "healthy"][0]
        # the 900 s window (60 attempts) is under exit429 only once clean traffic has pushed all but
        # six 429s out — 11.25 min at this rate — then the hold: recovering ~13 min after the storm
        # ended, never before 11…
        self.assertGreaterEqual(t_rec, 30 + 11)
        self.assertLessEqual(t_rec, 30 + 15)
        # …and healthy exactly one hold after recovering
        self.assertAlmostEqual(t_ok - t_rec, self.cfg["holdS"] / 60.0, delta=0.1)

    def test_a_dead_band_reading_moves_nothing(self):
        """Between exit (0.10) and enter (0.20) the state HOLDS — the hysteresis. Thrashing stays
        thrashing; the timer resets rather than the state flipping."""
        storm = _storm(T0, T0 + 900)
        dead = _storm(T0 + 900, T0 + 900 + 1200, share=(4,))        # 20% … then diluted by the slow window
        dead = [e for e in dead if int((e.t - T0 - 900) / 15) % 20 < 17 or e.cls == "ok"]   # ~0.15 over time
        evs = storm + dead
        runs = _runs(evs, T0, T0 + 2100, cfg=self.cfg)
        self.assertNotIn("recovering", [s for _, s in runs], "0.15 never satisfies exit ≤ 0.10")
        self.assertNotIn("healthy", [s for _, s in runs])
        self.assertEqual([s for _, s in runs][-1], "thrashing")

    def test_re_entry_from_recovering_is_immediate(self):
        # clean for 14 min: recovering lands ~13.25 min in (see above); a dense 100% burst then starts
        # 45 s later, before the second hold could have completed, and enters at once
        evs = (_storm(T0, T0 + 1800) + _clean(T0 + 1800, T0 + 2640)
               + _storm(T0 + 2640, T0 + 2940, step=3, share=(0, 1, 2, 3, 4)))
        runs = _runs(evs, T0, T0 + 2940, cfg=self.cfg)
        self.assertEqual([s for _, s in runs], ["unknown", "thrashing", "recovering", "thrashing"],
                         "no healthy: the storm came back inside the second hold — re-entry is immediate")
        t_rec = [m for m, s in runs if s == "recovering"][0]
        t_re = [m for m, s in runs if s == "thrashing"][1]
        self.assertLess(t_rec, 44.0)
        self.assertLess(t_re - 44.0, 1.5, "within a minute of the burst starting")

    def test_the_state_is_a_pure_function_of_events_and_now(self):
        evs = _storm(T0 - 600, T0)
        a = sb.api_health_state(evs, T0, self.cfg)
        b = sb.api_health_state(list(reversed(evs)), T0, self.cfg)     # order of the input is irrelevant
        self.assertEqual(a, b)
        self.assertEqual(sb.api_health_state(evs, T0, self.cfg), a, "repeatable — no hidden state")

    def test_the_backtested_incident_shape(self):
        """The design note's per-bucket backtest of the 2026-09-01 incident, rebuilt SYNTHETICALLY
        from its shape: a ~40% 429 share on one family for ~2h23m, a 21-minute clean lull, the storm
        again for ~63 minutes, then clean. The note's runs: thrashing at +1:25 on n = 10; recovering
        ~15 minutes into the lull and healthy two minutes later; thrashing again ~2 minutes into the
        second storm; recovering ~15 minutes after it ended, healthy two minutes later — two entries,
        no flap. The timings here follow from the same rules on the rebuilt traffic."""
        A, B, C, D = T0, T0 + 143 * 60, T0 + 164 * 60, T0 + 227 * 60
        END = T0 + 250 * 60
        evs = _storm(A, B) + _clean(B, C) + _storm(C, D) + _clean(D, END)
        runs = _runs(evs, A, END, cfg=self.cfg)
        self.assertEqual([s for _, s in runs],
                         ["unknown", "thrashing", "recovering", "healthy", "thrashing", "recovering", "healthy"])
        m = dict()
        for minute, s in runs:
            m.setdefault(s, []).append(minute)
        self.assertLessEqual(m["thrashing"][0], 3.0, "entry on the first ten attempts")
        # no recovery until the slow window is clean enough (≥ 11 min of clean traffic at this rate)
        # and the hold has passed — the note saw ~15 min on the real, burstier traffic
        self.assertGreaterEqual(m["recovering"][0], 143 + 11)
        self.assertLessEqual(m["recovering"][0], 143 + 17)
        self.assertAlmostEqual(m["healthy"][0] - m["recovering"][0], 2.0, delta=0.1)
        self.assertGreaterEqual(m["thrashing"][1], 164, "the second entry is the second storm")
        self.assertLessEqual(m["thrashing"][1], 164 + 4)
        self.assertGreaterEqual(m["recovering"][1], 227 + 11)
        self.assertLessEqual(m["recovering"][1], 227 + 17)
        self.assertAlmostEqual(m["healthy"][1] - m["recovering"][1], 2.0, delta=0.1)

    def test_per_bucket_keying_is_load_bearing(self):
        """Pooled with a clean family's heavier traffic, the incident's share vanishes; keyed per
        (auth, family) the affected bucket thrashes while the other stays healthy."""
        storm = _storm(T0 - 900, T0)                                      # 60 attempts, 0.40
        other = _clean(T0 - 900, T0, step=5, family="haiku")              # 180 clean attempts elsewhere
        pooled = sb.api_health_state(storm + other, T0, self.cfg)
        self.assertEqual(pooled["state"], "healthy", "pooled share ≈ 0.10 — the incident disappears")
        ah = sb.ApiHealth(tempfile.mkdtemp())
        for e in storm + other:
            ah._push(e)
        snap = ah.snapshot(T0)
        self.assertEqual(snap["buckets"][LABEL + "|fable"]["state"], "thrashing")
        self.assertEqual(snap["buckets"][LABEL + "|haiku"]["state"], "healthy")
        self.assertEqual(snap["overall"]["state"], "thrashing")
        self.assertEqual(snap["overall"]["worstBucket"], LABEL + "|fable")

    def test_constants_live_in_one_place_with_an_env_override(self):
        self.assertEqual(tuple(self.cfg["windows"]), (60, 300, 900))
        self.assertEqual((self.cfg["minRequests"], self.cfg["fastMinRequests"], self.cfg["holdS"]), (10, 20, 120))
        self.assertEqual((self.cfg["enter429"], self.cfg["enter429Slow"], self.cfg["enter429Fast"], self.cfg["exit429"]),
                         (0.20, 0.15, 0.50, 0.10))
        self.assertEqual(self.cfg["retentionS"], 1800, "twice the longest window: the hold is computable from the ring")
        os.environ["ROMP_API_HEALTH_MIN_REQUESTS"] = "3"
        os.environ["ROMP_API_HEALTH_HOLD_S"] = "10"
        os.environ["ROMP_API_HEALTH_ENTER_429"] = "0.5"
        try:
            c = sb.api_health_config()
            self.assertEqual((c["minRequests"], c["holdS"], c["enter429"]), (3, 10, 0.5))
            three = _storm(T0 - 60, T0, step=20, share=(0, 1))[:3]    # 3 attempts, 2 of them 429
            self.assertEqual(sb.api_health_state(three, T0, c)["state"], "thrashing")
            os.environ["ROMP_API_HEALTH_MIN_REQUESTS"] = "not-a-number"
            self.assertEqual(sb.api_health_config()["minRequests"], 10, "a malformed override is ignored")
        finally:
            for k in ("MIN_REQUESTS", "HOLD_S", "ENTER_429"):
                os.environ.pop("ROMP_API_HEALTH_" + k, None)
        self.assertIn("CLAUDE_CODE_RETRY_WATCHDOG", open(os.path.join(BIN, "romp_sdk_backend.py")).read(),
                      "the persistent-retry overcount caveat is recorded beside the constants")

    def test_the_payload_echoes_the_config(self):
        snap = sb.ApiHealth(tempfile.mkdtemp()).snapshot(T0)
        self.assertEqual(snap["config"]["windows"], [60, 300, 900])
        self.assertEqual(snap["config"]["holdS"], 120)
        self.assertEqual(snap["schema"], 1)


class OverallState(unittest.TestCase):
    def _ah_with(self, *bucket_states):
        ah = sb.ApiHealth(tempfile.mkdtemp())
        for i, st in enumerate(bucket_states):
            fam = "fam%d" % i
            if st == "thrashing":
                evs = _storm(T0 - 600, T0, family=fam)
            elif st == "healthy":
                evs = _clean(T0 - 600, T0, family=fam)
            else:   # unknown: a few events, under minRequests
                evs = _clean(T0 - 60, T0, step=20, family=fam)
            for e in evs:
                ah._push(e)
        return ah.snapshot(T0)

    def test_the_most_severe_bucket_sets_the_overall_state(self):
        snap = self._ah_with("healthy", "thrashing", "healthy")
        self.assertEqual(snap["overall"]["state"], "thrashing", "a healthy fallback bucket must not mask a thrashing one")
        self.assertEqual(snap["overall"]["worstBucket"], LABEL + "|fam1")

    def test_unknown_ranks_below_healthy(self):
        self.assertEqual(self._ah_with("unknown", "healthy")["overall"]["state"], "healthy")
        self.assertEqual(self._ah_with("unknown", "unknown")["overall"]["state"], "unknown")
        self.assertEqual(self._ah_with()["overall"]["state"], "unknown", "no buckets at all reads unknown")
        self.assertIsNone(self._ah_with()["overall"]["worstBucket"])


class SaltedLabels(unittest.TestCase):
    def test_same_material_same_label_within_one_install(self):
        a = sb.api_health_auth_label("ANTHROPIC_API_KEY", salt="salt-1", work_key=KEY_MATERIAL, launched_keyed=True)
        b = sb.api_health_auth_label("ANTHROPIC_API_KEY", salt="salt-1", work_key=KEY_MATERIAL, launched_keyed=True)
        self.assertEqual(a, b)
        self.assertRegex(a, r"^key:[0-9a-f]{12}$")

    def test_a_different_salt_gives_a_different_label(self):
        a = sb.api_health_auth_label("ANTHROPIC_API_KEY", salt="salt-1", work_key=KEY_MATERIAL, launched_keyed=True)
        b = sb.api_health_auth_label("ANTHROPIC_API_KEY", salt="salt-2", work_key=KEY_MATERIAL, launched_keyed=True)
        self.assertNotEqual(a, b, "the label is not a cross-install equality oracle")
        # …and the empty salt is the documented switch to a plain digest
        import hashlib
        plain = sb.api_health_auth_label("ANTHROPIC_API_KEY", salt="", work_key=KEY_MATERIAL, launched_keyed=True)
        self.assertEqual(plain, "key:" + hashlib.sha256(KEY_MATERIAL.encode()).hexdigest()[:12])

    def test_no_fragment_of_the_key_is_in_the_label(self):
        lab = sb.api_health_auth_label("ANTHROPIC_API_KEY", salt="s", work_key=KEY_MATERIAL, launched_keyed=True)
        for i in range(len(KEY_MATERIAL) - 4):
            self.assertNotIn(KEY_MATERIAL[i:i + 5], lab)

    def test_the_source_words_map_to_constant_labels(self):
        self.assertEqual(sb.api_health_auth_label("ANTHROPIC_API_KEY", salt="s", work_key="", launched_keyed=False),
                         "key:env", "the kernel injected nothing → no material to digest")
        self.assertEqual(sb.api_health_auth_label("ANTHROPIC_API_KEY", salt="s", work_key=KEY_MATERIAL, launched_keyed=False),
                         "key:env", "a key the CLI found on its own is not the kernel's material")
        self.assertEqual(sb.api_health_auth_label("apiKeyHelper", salt="s"), "key:helper")
        self.assertEqual(sb.api_health_auth_label("/login managed key", salt="s"), "key:managed")
        self.assertEqual(sb.api_health_auth_label("oauth", salt="s"), "key:oauth")
        self.assertEqual(sb.api_health_auth_label("none", salt="s", acct="0123456789ab"),
                         "login:" + sb._api_health_digest("s", "0123456789ab"))
        self.assertEqual(sb.api_health_auth_label(None, salt="s", acct=""), "login:unknown")
        self.assertEqual(sb.api_health_auth_label("", salt="s", acct=""), "login:unknown")

    def test_the_salt_is_minted_once_at_0600_and_an_empty_file_means_unsalted(self):
        d = tempfile.mkdtemp()
        ah = sb.ApiHealth(d)
        self.assertFalse(os.path.exists(os.path.join(d, sb.API_HEALTH_SALT_FILE)), "nothing written until a label is needed")
        s1 = ah.salt()
        p = os.path.join(d, sb.API_HEALTH_SALT_FILE)
        self.assertTrue(s1 and os.path.exists(p))
        self.assertEqual(stat.S_IMODE(os.stat(p).st_mode), 0o600)
        self.assertEqual(sb.ApiHealth(d).salt(), s1, "one salt per install: a new aggregator reads the same file")
        open(p, "w").close()
        self.assertEqual(sb.ApiHealth(d).salt(), "", "the empty file is the switch")

    def test_the_init_resolves_the_label_once_onto_the_session(self):
        be = _backend()
        be.work_key = KEY_MATERIAL
        s = _session(be, label="unknown")
        s._launched_keyed = True
        s.auth = ""
        s.api_key_auth = False
        s.auth_live = ""
        be._note_auth_source(s, "ANTHROPIC_API_KEY")
        self.assertRegex(s.auth_label, r"^key:[0-9a-f]{12}$")
        self.assertEqual(s.auth_label, "key:" + sb._api_health_digest(be.api_health.salt(), KEY_MATERIAL))
        # the frames that follow file under it
        _feed(s, FakeSystemMessage("api_retry", retry_frame()))
        snap = be.api_health_snapshot()
        self.assertIn(s.auth_label + "|fable", snap["buckets"])
        # …and no fragment of the material is anywhere in the payload or the ledger
        blob = json.dumps(snap) + open(os.path.join(be.state_dir, sb.API_HEALTH_LEDGER)).read()
        for i in range(len(KEY_MATERIAL) - 4):
            self.assertNotIn(KEY_MATERIAL[i:i + 5], blob)

    def test_the_label_source_reuses_the_existing_auth_knowledge(self):
        # not a re-derivation: the same init word _note_auth_source already judges, the kernel's
        # work_api_key material, the usage bars' account digest
        src = inspect.getsource(sb.SdkBackend._note_auth_source)
        self.assertIn("self.api_health.auth_label(", src)
        self.assertIn("work_key=self.work_key", src)
        self.assertIn("acct_digest()", inspect.getsource(sb.ApiHealth.auth_label))


class TransitionLedger(unittest.TestCase):
    def test_a_read_that_observes_a_change_appends_one_row(self):
        d = tempfile.mkdtemp()
        ah = sb.ApiHealth(d)
        p = os.path.join(d, sb.API_HEALTH_LEDGER)
        for e in _storm(T0 - 600, T0):
            ah._push(e)
        ah.snapshot(T0)
        rows = [json.loads(l) for l in open(p)]
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]["from"], rows[0]["to"], rows[0]["bucket"]), (None, "thrashing", LABEL + "|fable"))
        self.assertIn("rate429 over", rows[0]["why"])
        ah.snapshot(T0 + 5)
        self.assertEqual(len(open(p).read().splitlines()), 1, "no change → no row")
        snap = ah.snapshot(T0 + 1500)      # the ring has emptied past retention: unknown
        self.assertEqual(snap["buckets"][LABEL + "|fable"]["state"], "unknown")
        rows = [json.loads(l) for l in open(p)]
        self.assertEqual([r["to"] for r in rows], ["thrashing", "unknown"])
        self.assertEqual(snap["transitions"], rows, "the payload carries the ledger's tail")

    def test_the_ledger_seeds_a_new_aggregator(self):
        # a restart keeps the history and does not re-announce the last state as a fresh transition
        d = tempfile.mkdtemp()
        ah = sb.ApiHealth(d)
        for e in _storm(T0 - 600, T0):
            ah._push(e)
        ah.snapshot(T0)
        ah2 = sb.ApiHealth(d)
        self.assertEqual(ah2._last_state[LABEL + "|fable"][0], "thrashing")
        self.assertEqual(len(ah2.snapshot(T0 + 1)["transitions"]), 1, "an empty ring shows no bucket, files no row")
        for e in _storm(T0 - 600, T0 + 30):      # the storm is still on as the ring refills
            ah2._push(e)
        snap = ah2.snapshot(T0 + 30)
        self.assertEqual(snap["buckets"][LABEL + "|fable"]["state"], "thrashing")
        self.assertEqual(len(open(os.path.join(d, sb.API_HEALTH_LEDGER)).read().splitlines()), 1,
                         "the same state observed after a restart is not a transition")
        # …whereas a restart into a LULL is an honest transition: thrashing → unknown, on the record
        ah3 = sb.ApiHealth(d)
        for e in _clean(T0 + 1000, T0 + 1030):
            ah3._push(e)
        self.assertEqual(ah3.snapshot(T0 + 1030)["buckets"][LABEL + "|fable"]["state"], "unknown")
        rows = [json.loads(l) for l in open(os.path.join(d, sb.API_HEALTH_LEDGER))]
        self.assertEqual([(r["from"], r["to"]) for r in rows], [(None, "thrashing"), ("thrashing", "unknown")])

    def test_state_since_is_the_first_read_that_observed_it(self):
        ah = sb.ApiHealth(tempfile.mkdtemp())
        for e in _storm(T0 - 600, T0):
            ah._push(e)
        a = ah.snapshot(T0)["buckets"][LABEL + "|fable"]["stateSince"]
        b = ah.snapshot(T0 + 40)["buckets"][LABEL + "|fable"]["stateSince"]
        self.assertEqual(a, b, "unchanged state, unchanged since")
        self.assertEqual(a, T0)

    def test_the_ring_is_memory_only_and_the_code_says_why(self):
        d = tempfile.mkdtemp()
        ah = sb.ApiHealth(d)
        for e in _storm(T0 - 600, T0):
            ah._push(e)
        self.assertEqual(os.listdir(d), [], "per-request events are never persisted")
        ah.snapshot(T0)
        self.assertEqual(os.listdir(d), [sb.API_HEALTH_LEDGER], "only the observed transition is")
        head = open(os.path.join(BIN, "romp_sdk_backend.py")).read()
        self.assertIn("Only STATE TRANSITIONS a read observes are\n# written to disk", head)
        self.assertIn("persisting every attempt would add a write per API call", head, "the why is written down")


class Diagnostics(unittest.TestCase):
    def setUp(self):
        sb.SdkSession._retry_shape_logged = False
        sb.SdkSession._sys_subtypes_seen = set()

    def tearDown(self):
        sb.SdkSession._retry_shape_logged = False
        sb.SdkSession._sys_subtypes_seen = set()

    def test_the_first_api_retry_frame_logs_its_sorted_keys_once(self):
        lines = []
        be = _backend(log=lines.append)
        s = _session(be)
        for i in range(3):
            _feed(s, FakeSystemMessage("api_retry", retry_frame(attempt=i + 1)))
        hits = [l for l in lines if "first api_retry frame" in l]
        self.assertEqual(len(hits), 1)
        self.assertIn("keys=['attempt', 'error', 'error_status', 'max_retries', 'retry_delay_ms', "
                      "'session_id', 'uuid']", hits[0], "sorted, keys only")
        self.assertNotIn("rate_limit", hits[0], "values never ride the line (they would carry error text)")

    def test_an_unhandled_system_subtype_logs_once_per_subtype(self):
        lines = []
        be = _backend(log=lines.append)
        s = _session(be)
        for st in ("memory_recall", "memory_recall", "thinking_tokens"):
            _feed(s, FakeSystemMessage(st, {"k1": 1, "k2": 2}))
        hits = [l for l in lines if "unhandled SystemMessage subtype" in l]
        self.assertEqual(len(hits), 2)
        self.assertIn("'memory_recall'", hits[0])
        self.assertIn("['k1', 'k2']", hits[0])
        self.assertIn("'thinking_tokens'", hits[1])

    def test_handled_subtypes_are_never_reported_as_unhandled(self):
        lines = []
        be = _backend(log=lines.append)
        s = _session(be)
        _feed(s, FakeSystemMessage("api_retry", retry_frame()))
        self.assertFalse(any("unhandled SystemMessage" in l for l in lines))
        src = inspect.getsource(sb.SdkSession._on_message)
        i_tasks = src.index('"task_started", "task_progress", "task_updated", "task_notification"')
        i_trail = src.index("elif isinstance(msg, SystemMessage):\n            # A subtype no branch above handles")
        i_asst = src.index("elif isinstance(msg, AssistantMessage):")
        self.assertTrue(i_tasks < i_trail < i_asst, "the trailing branch sits right after the task events")


if __name__ == "__main__":
    unittest.main(verbosity=2)
