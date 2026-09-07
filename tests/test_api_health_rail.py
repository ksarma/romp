#!/usr/bin/env python3
"""The bottom bar's API health cell (the user 2026-09-07): one dot and one word beside the spend cell,
answering 'is the API serving my sessions'. The kernel builds one apiHealth frame per pusher cycle from the
merged live map's retrying state, each alive transcript's LATCHED newest API error (_api_last_failed) and
the retry-pause file, and pushes it to the shells only when it changed; the shell paints the cell from the
frame and builds the click detail from it, with no fetch and no timer.

The rule these tests pin: every field moves on one named event and never on a clock, so two computes over
the same world are byte-identical and send nothing. Synthetic fixtures only (private synthetic sids, the
notes-api demo's web / api / tests names, no paths or error text in any frame)."""
import inspect
import json
import os
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
km = SourceFileLoader("romp_kernel_apih", os.path.join(BIN, "romp-kernel")).load_module()
sb = SourceFileLoader("romp_sdk_backend_apih", os.path.join(BIN, "romp_sdk_backend.py")).load_module()

# A PRIVATE synthetic sid family for this module (never the shared 11111111-2222 placeholder, never real).
SID = ["77777777-aaaa-4bbb-8ccc-00000000000%d" % i for i in range(1, 6)]
NAMES = ["web", "api", "tests", "docs", "build"]
T_STORM = 1_700_000_000          # a storm turn's start (SdkSession.since, once per fresh turn)
T_REC = 1_700_000_100            # an error record's own timestamp
MDOT = "·"


def _frame_keys():
    return {"type", "state", "cls", "reason", "text", "waiting", "retrying", "blocked", "since", "tmux", "sessions"}


class _Fixture(unittest.TestCase):
    """Fixture sessions: `self.sess` is the alive roster, `self.live` the merged live map, `self.errs`
    the latched error per transcript path. Everything the frame reads is patched at the module seam."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self._state = km.jd.STATE
        km.jd.STATE = Path(self.td.name)
        self._alive = km._alive_sessions
        self._last = km._api_last_failed
        self._send = km._send_to_app
        self._backend_for = km.Sessions.__dict__["backend_for"]
        self._color = km._name_color
        self.sess, self.live, self.errs, self.tmux_sids, self.colors = [], {}, {}, set(), {}
        km._alive_sessions = lambda now, tmux: list(self.sess)
        km._api_last_failed = lambda p: self.errs.get(p)
        self.sent = []
        km._send_to_app = lambda app, m: self.sent.append((app, m))
        km.Sessions.backend_for = staticmethod(lambda sid: km._TMUX if sid in self.tmux_sids else object())
        km._name_color = lambda sid: self.colors.get(sid)
        km._APIH_LAST[0] = None
        km._retry_suppress_cache.clear()

    def tearDown(self):
        km.jd.STATE = self._state
        km._alive_sessions = self._alive
        km._api_last_failed = self._last
        km._send_to_app = self._send
        km.Sessions.backend_for = self._backend_for
        km._name_color = self._color
        km._APIH_LAST[0] = None
        km._retry_suppress_cache.clear()
        self.td.cleanup()

    def add(self, i, state="waiting", retry=None, err=None, since=T_STORM):
        """One alive session: `retry` = a retryInfo dict puts it in the api_retry storm; `err` = the latched
        error record's fields (status / category / t / the on-you flags)."""
        path = os.path.join(self.td.name, NAMES[i] + ".jsonl")
        self.sess.append({"sid": SID[i], "name": NAMES[i], "path": path, "anchor": "", "mtime": 0})
        row = {"state": state, "since": since, "backend": "sdk"}
        if retry is not None:
            row["state"] = "retrying"
            row["retryInfo"] = retry
        self.live[SID[i]] = row
        if err is not None:
            e = {"status": None, "category": "unknown", "t": T_REC, "text": "", "uuid": "x",
                 "tooLong": False, "spendLimit": False, "modelLimit": False, "authErr": False, "refusal": False}
            e.update(err)
            self.errs[path] = e
        return SID[i]

    def frame(self, now=10):
        return km._api_health_frame(now, self.live)


class States(_Fixture):
    def test_no_rows_and_no_pause_is_ok(self):
        self.add(0)
        f = self.frame()
        self.assertEqual((f["state"], f["cls"], f["reason"], f["text"]), ("ok", "", "", "ok"))
        self.assertEqual((f["waiting"], f["retrying"], f["blocked"], f["since"]), (0, 0, 0, 0))
        self.assertEqual(f["sessions"], [])

    def test_a_retrying_429_row_reads_rate_limited(self):
        self.add(0, retry={"status": 429, "attempt": 2, "max": 10})
        f = self.frame()
        self.assertEqual((f["state"], f["cls"], f["text"]), ("degraded", "429", "rate limited %s 1 waiting" % MDOT))
        self.assertEqual((f["waiting"], f["retrying"], f["blocked"]), (1, 1, 0))
        self.assertEqual(f["sessions"][0]["kind"], "retrying")

    def test_a_latched_529_record_reads_overloaded(self):
        self.add(0, err={"status": 529, "category": "overloaded"})
        f = self.frame()
        self.assertEqual((f["state"], f["cls"], f["text"]), ("degraded", "529", "overloaded %s 1 waiting" % MDOT))
        self.assertEqual((f["waiting"], f["retrying"], f["blocked"]), (1, 0, 1))
        self.assertEqual(f["sessions"][0]["kind"], "blocked")

    def test_network_down_with_no_status_reads_offline(self):
        self.add(0, retry={"status": None, "networkDown": True})
        f = self.frame()
        self.assertEqual((f["cls"], f["text"]), ("offline", "offline %s 1 waiting" % MDOT))

    def test_a_500_reads_errors(self):
        self.add(0, err={"status": 500, "category": "server_error"})
        f = self.frame()
        self.assertEqual((f["cls"], f["text"]), ("errors", "errors %s 1 waiting" % MDOT))

    def test_a_no_status_record_without_a_network_flag_reads_errors_not_offline(self):
        # only a retrying row can say offline: a transcript record carries no network flag
        self.add(0, err={"status": None, "category": "unknown"})
        self.assertEqual(self.frame()["cls"], "errors")

    def test_plurality_picks_the_most_common_class(self):
        self.add(0, retry={"status": 429})
        self.add(1, retry={"status": 429})
        self.add(2, err={"status": 529, "category": "overloaded"})
        f = self.frame()
        self.assertEqual((f["cls"], f["text"]), ("429", "rate limited %s 3 waiting" % MDOT))

    def test_ties_resolve_in_the_fixed_order(self):
        self.add(0, retry={"status": 429})
        self.add(1, err={"status": 529, "category": "overloaded"})
        self.assertEqual(self.frame()["cls"], "429", "429 before 529")
        self.sess.clear(); self.live.clear(); self.errs.clear()
        self.add(0, err={"status": 529, "category": "overloaded"})
        self.add(1, err={"status": 500, "category": "server_error"})
        self.assertEqual(self.frame()["cls"], "529", "529 before errors")
        self.sess.clear(); self.live.clear(); self.errs.clear()
        self.add(0, retry={"status": None, "networkDown": True})
        self.add(1, err={"status": 500, "category": "server_error"})
        self.assertEqual(self.frame()["cls"], "offline", "offline before errors")

    def test_on_you_failures_do_not_count(self):
        for flag in ("tooLong", "modelLimit", "authErr", "refusal"):
            self.sess.clear(); self.live.clear(); self.errs.clear()
            self.add(0, err={"status": 400, "category": "invalid_request", flag: True})
            f = self.frame()
            self.assertEqual((f["state"], f["waiting"]), ("ok", 0), flag + " is the session's own, not the API's")

    def test_a_spend_limit_record_counts(self):
        self.add(0, err={"status": 400, "category": "billing_error", "spendLimit": True})
        f = self.frame()
        self.assertEqual((f["state"], f["cls"], f["waiting"]), ("degraded", "errors", 1))

    def test_a_spend_pause_outranks_any_class(self):
        self.add(0, retry={"status": 429})
        self.add(1, retry={"status": 429})
        km._set_retry_paused(True, reason="spend")
        f = self.frame()
        self.assertEqual((f["state"], f["reason"], f["text"]), ("paused", "spend", "paused %s spend cap %s 2 waiting" % (MDOT, MDOT)))
        self.assertEqual(f["cls"], "429", "the class still rides along for the detail")

    def test_a_limit_pause_names_the_usage_limit(self):
        self.add(0, retry={"status": 429})
        km._set_retry_paused(True, reason="limit")
        f = self.frame()
        self.assertEqual((f["state"], f["reason"], f["text"]), ("paused", "limit", "paused %s usage limit %s 1 waiting" % (MDOT, MDOT)))

    def test_a_manual_pause_reads_paused_by_you(self):
        self.add(0, err={"status": 500, "category": "server_error"})
        km._set_retry_paused(True)
        f = self.frame()
        self.assertEqual((f["reason"], f["text"]), ("manual", "paused by you %s 1 waiting" % MDOT))

    def test_a_pause_with_nothing_waiting_drops_the_count(self):
        self.add(0)
        km._set_retry_paused(True, reason="limit")
        self.assertEqual(self.frame()["text"], "paused %s usage limit" % MDOT)
        km._set_retry_paused(True, reason="spend")
        self.assertEqual(self.frame()["text"], "paused %s spend cap" % MDOT)
        km._set_retry_paused(True)
        self.assertEqual(self.frame()["text"], "paused by you")

    def test_a_suppressed_row_carries_suppressed_true(self):
        sid = self.add(0, err={"status": 500, "category": "server_error"})
        self.add(1, retry={"status": 429})
        km._suppress_session_retry(sid)
        rows = {r["sid"]: r for r in self.frame()["sessions"]}
        self.assertTrue(rows[SID[0]]["suppressed"])
        self.assertFalse(rows[SID[1]]["suppressed"])
        self.assertEqual(self.frame()["waiting"], 2, "the interrupt says nothing about the API: still counted")

    def test_tmux_backed_sessions_are_counted_for_the_coverage_line(self):
        self.add(0); self.add(1); self.add(2, err={"status": 500, "category": "server_error"})
        self.tmux_sids = {SID[1], SID[2]}
        self.assertEqual(self.frame()["tmux"], 2)

    def test_rows_carry_name_and_color(self):
        self.colors[SID[0]] = {"bg": "#3366cc", "fg": "#ffffff"}
        self.add(0, retry={"status": 429})
        r = self.frame()["sessions"][0]
        self.assertEqual((r["name"], r["color"]), ("web", {"bg": "#3366cc", "fg": "#ffffff"}))

    def test_a_string_status_on_the_wire_is_read_as_a_number(self):
        self.add(0, retry={"status": "529"})
        f = self.frame()
        self.assertEqual((f["cls"], f["sessions"][0]["status"]), ("529", 529))


class NoFlap(_Fixture):
    def test_two_computes_over_the_same_world_are_byte_identical_and_send_once(self):
        self.add(0, retry={"status": 429, "attempt": 3, "retryAt": 1_700_000_050.5})
        self.add(1, err={"status": 500, "category": "server_error"})
        f1 = self.frame(now=10)
        km._api_health_push(f1)
        f2 = self.frame(now=99_999)
        km._api_health_push(f2)
        self.assertEqual(json.dumps(f1, sort_keys=True), json.dumps(f2, sort_keys=True))
        self.assertEqual(len(self.sent), 1, "an unchanged world sends nothing")
        self.assertEqual(self.sent[0][0], "shell")

    def test_attempt_and_retry_at_changes_move_nothing(self):
        self.add(0, retry={"status": 429, "attempt": 3, "retryAt": 100.0, "error": "429 rate limited"})
        km._api_health_push(self.frame())
        self.live[SID[0]]["retryInfo"].update({"attempt": 4, "retryAt": 200.0, "error": "429 again"})
        km._api_health_push(self.frame())
        self.assertEqual(len(self.sent), 1, "per-attempt counters are not inputs")

    def test_a_row_flipping_retrying_to_blocked_with_the_same_count_does_send(self):
        self.add(0, retry={"status": 429})
        km._api_health_push(self.frame())
        self.live[SID[0]] = {"state": "waiting", "since": T_STORM}
        self.errs[self.sess[0]["path"]] = {"status": 429, "category": "rate_limit", "t": T_REC,
                                            "tooLong": False, "modelLimit": False, "authErr": False, "refusal": False}
        km._api_health_push(self.frame())
        self.assertEqual(len(self.sent), 2, "the storm gave up and left a record: new information")
        self.assertEqual(self.sent[1][1]["waiting"], 1)
        self.assertEqual((self.sent[1][1]["retrying"], self.sent[1][1]["blocked"]), (0, 1))

    def test_a_pause_set_and_lifted_each_send_once(self):
        self.add(0)
        km._api_health_push(self.frame())
        km._set_retry_paused(True, reason="limit")
        km._api_health_push(self.frame())
        km._api_health_push(self.frame())
        km._set_retry_paused(False)
        km._api_health_push(self.frame())
        self.assertEqual([m["state"] for _, m in self.sent], ["ok", "paused", "ok"])

    def test_since_is_the_event_stamp_never_the_clock(self):
        self.add(0, retry={"status": 429}, since=T_STORM)
        self.add(1, err={"status": 500, "category": "server_error", "t": T_REC})
        f = self.frame(now=5_000_000_000)
        self.assertEqual(f["since"], T_STORM, "the earliest affected event")
        rows = {r["sid"]: r for r in f["sessions"]}
        self.assertEqual(rows[SID[0]]["since"], T_STORM)
        self.assertEqual(rows[SID[1]]["since"], T_REC)
        km._set_retry_paused(True, reason="spend")
        self.assertEqual(self.frame()["since"], int(km._retry_pause_ts()), "paused: the pause's own t")

    def test_the_roster_order_cannot_reshuffle_an_unchanged_world(self):
        self.add(0, retry={"status": 429})
        self.add(1, err={"status": 500, "category": "server_error"})
        km._api_health_push(self.frame())
        self.sess.reverse()                              # a newer mtime moved a session up the roster
        km._api_health_push(self.frame())
        self.assertEqual(len(self.sent), 1)

    def test_the_ready_handler_resends_the_last_frame_to_a_shell_only(self):
        self.add(0, retry={"status": 429})
        km._api_health_push(self.frame())
        got = []
        km._apih_resend({"app": "shell", "send": got.append})
        km._apih_resend({"app": "chat", "send": lambda s: self.fail("a chat client owns no rail")})
        self.assertEqual(len(got), 1)
        self.assertEqual(json.loads(got[0]), self.sent[0][1], "verbatim: the client diffs state and text")

    def test_nothing_to_resend_before_the_first_frame(self):
        km._apih_resend({"app": "shell", "send": lambda s: self.fail("nothing sent since boot")})


class FrameShape(_Fixture):
    def test_the_frame_and_its_rows_carry_exactly_the_documented_keys(self):
        self.add(0, retry={"status": 429, "error": "the wire's text", "requestId": "req_x"})
        self.add(1, err={"status": 500, "category": "server_error", "text": "API Error: 500"})
        f = self.frame()
        self.assertEqual(set(f), _frame_keys())
        for r in f["sessions"]:
            self.assertEqual(set(r), {"sid", "name", "color", "kind", "cls", "status", "since", "suppressed"})
        s = json.dumps(f)
        self.assertNotIn(".jsonl", s, "no path in any frame")
        self.assertNotIn("API Error", s, "no error text in any frame")
        self.assertNotIn("req_x", s)
        self.assertNotIn("attempt", s)

    def test_apih_class_agrees_with_the_backend_on_shared_statuses(self):
        collapse = {"429": "429", "529": "529", "5xx": "errors", "other": "errors", "none": "errors"}
        for status, cat in ((429, ""), (529, ""), (500, ""), (400, ""), (None, "rate_limit"), (None, "overloaded")):
            self.assertEqual(km._apih_class(status, cat), collapse[sb.api_health_status_class(status, cat)],
                             "status=%r category=%r" % (status, cat))
        self.assertEqual(km._apih_class(None, "", True), "offline", "the one word the backend lacks")

    def test_the_text_table_is_the_rail_s_words(self):
        self.assertEqual(km._APIH_TEXT, {"ok": "ok", "429": "rate limited", "529": "overloaded", "offline": "offline",
                                         "errors": "errors", "limit": "paused %s usage limit" % MDOT,
                                         "spend": "paused %s spend cap" % MDOT, "manual": "paused by you"})
        for v in km._APIH_TEXT.values():
            self.assertNotIn("fleet", v)
            self.assertNotIn("blocked", v)
            self.assertNotIn("—", v)
        self.assertEqual(km._APIH_ORDER, ("429", "529", "offline", "errors"))


class Wiring(unittest.TestCase):
    def test_the_frame_is_built_in_the_jobs_block_after_this_cycle_s_pause_decisions(self):
        src = inspect.getsource(km._pusher_cycle_jobs)
        self.assertIn("_api_health_push(_api_health_frame(now, tmux))", src)
        self.assertLess(src.index("_auto_resume_retry(now, tmux)"), src.index("_api_health_push(_api_health_frame"))
        self.assertNotIn("_api_health", inspect.getsource(km._cached_feed), "not gated by the feed's sig / rebuild floor")

    def test_the_ready_handler_resends_beside_the_badge(self):
        src = Path(BIN, "romp-kernel").read_text()
        i = src.index('client["send"](json.dumps({"type": "badge", "n": _BADGE_LAST[0]}))')
        j = src.index("_apih_resend(client)          #", i)   # the CALL in the ready handler, not the def
        self.assertLess(j - i, 400, "right beside the badge re-send, in the same ready branch")
        self.assertIn("def _apih_resend(client):", src)

    def test_auto_pause_on_limit_latches_reason_limit(self):
        self.assertIn('_set_retry_paused(True, reason="limit")', inspect.getsource(km._auto_pause_on_limit))


class Detail(unittest.TestCase):
    """The click detail's content, pinned at source (no jsdom for the shell page)."""
    JS = km._LANDING_APIH_JS

    def test_the_plain_words_sentences_are_present_verbatim(self):
        for s in ("Auto-retry and the judges are paused until your usage limit resets.",
                  "Auto-retry and the judges are paused: you have reached the monthly spend limit. Raise it at claude.ai/settings/usage.",
                  "Auto-retry and the judges are paused: you stopped them.",
                  "No session is waiting on the API. Auto-retry and the judges are running.",
                  "API · this machine", "Sessions waiting", "since "):
            self.assertIn(s, self.JS)

    def test_the_pause_button_is_the_chat_card_s_and_acknowledges_before_the_round_trip(self):
        self.assertIn("'Resume all auto-retries'", self.JS)
        self.assertIn("'Stop all auto-retries'", self.JS)
        self.assertIn("{type:'setGlobalRetryPaused',value:v}", self.JS)
        press = self.JS[self.JS.index("if(act==='pause')"):self.JS.index("else if(act==='reveal')")]
        self.assertIn("t.disabled=true", press)
        self.assertIn("t.textContent=v?RESUME:STOP", press)
        self.assertIn("t.classList.add('romp-acted')", press)
        self.assertLess(press.index("t.classList.add('romp-acted')"), press.index("__rompShellSend("), "acknowledged first")
        self.assertIn("Not sent", press, "a dead socket is said, not swallowed")

    def test_a_session_row_jumps_to_its_card_the_way_the_log_does(self):
        row = self.JS[self.JS.index("else if(act==='reveal')"):self.JS.index("else if(act==='usage')")]
        self.assertLess(row.index("__rompPaneToggle('feed',true)"), row.index("{romp:'revealCard',itemId:'',sid:sid}"))
        self.assertIn("data-act=reveal data-sid=", self.JS)

    def test_the_coverage_line_appears_only_under_a_tmux_guard(self):
        self.assertIn("if(m.tmux>0)h+=", self.JS)
        self.assertIn("seen through their transcripts only", self.JS)
        self.assertIn(", so a retry in progress there shows only when it fails or recovers.", self.JS)

    def test_the_detail_renders_from_the_last_frame_only(self):
        self.assertNotIn("fetch(", self.JS)
        self.assertNotIn("setInterval", self.JS)
        self.assertNotIn("setTimeout", self.JS)
        self.assertIn("window.__rompApiHealth=function(m){", self.JS)
        self.assertIn("LAST=m;", self.JS)

    def test_the_cell_repaints_only_when_state_or_text_changed_and_shows_on_the_first_frame(self):
        self.assertIn("if(el.hidden)el.hidden=false;", self.JS)
        self.assertIn("if(el.getAttribute('data-state')!==m.state||txt.textContent!==m.text){el.setAttribute('data-state',m.state);txt.textContent=m.text;}", self.JS)
        self.assertIn("if(tip.style.display==='block')tip.innerHTML=html(m);", self.JS)

    def test_actions_are_delegated_on_the_stable_tip_node(self):
        self.assertIn("tip.addEventListener('click',function(ev){", self.JS)
        self.assertEqual(self.JS.count("addEventListener('click'"), 2, "one on #rail-api, one on #ah-tip; none per row")
        self.assertNotIn("onclick=", self.JS.split("back.onclick")[0].split("function open")[0], "no inline handlers in the markup")

    def test_the_words_are_plain_american_and_free_of_romp_nouns(self):
        shown = [s for s in self.JS.split("'") if len(s) > 2]
        for s in shown:
            self.assertNotIn("fleet", s.lower())
        self.assertNotIn("'blocked'", self.JS)
        self.assertNotIn("blocked", self.JS.split("data-act=reveal")[0].split("var PAUSE")[1] if "var PAUSE" in self.JS else "", "the amber state is never called blocked")
        self.assertNotIn("—", self.JS)
        for british in ("colour", "behaviour", "cancelled", "summarise"):
            self.assertNotIn(british, self.JS)
        self.assertIn("(r.kind==='retrying'?'retrying':'stopped')", self.JS)

    def test_the_footer_reaches_the_usage_modal_and_the_log(self):
        self.assertIn("data-act=usage>Usage and spend<", self.JS)
        self.assertIn("data-act=log>Log<", self.JS)
        self.assertIn("window.__rompUsagePanel&&window.__rompUsagePanel()", self.JS)
        self.assertIn("window.__rompOpenErrs&&window.__rompOpenErrs()", self.JS)

    def test_the_pinned_detail_wears_the_usage_modal_s_backdrop_and_escape_hook(self):
        self.assertIn("tip.classList.add('ru-modal')", self.JS)
        self.assertIn("back.classList.add('on')", self.JS)
        self.assertIn("window.__rompApiClose=close;back.onclick=close;", self.JS)
        self.assertIn("window.__rompApiClose=null;", self.JS)


if __name__ == "__main__":
    unittest.main()
