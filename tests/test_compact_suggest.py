#!/usr/bin/env python3
"""The kernel-level compaction SUGGESTION (the user 2026-08-30, via the nightly optimizer). The
~300k recycle rule stays workers-only; every OTHER session is told — once idle at least an hour,
first past 400k context tokens, again past 800k — that a /compact at a natural boundary would keep
it snappy, its call. Event-keyed end to end: the CROSSING arms it; a per-threshold latch on the
auto-nudge blob makes each fire once per episode; the idle gate reads the settle event's age AT
FIRE TIME; and the latch re-arms only on the session's own context RESET (compact//clear/rewind),
observed as the authoritative token counter falling back below the latched threshold — ignored =
silent forever, acted+regrown+idle = one fresh suggestion per threshold (the manager's amendment).
Workers (their roster tags), comment-thread forks, and mid-turn sessions are excluded at fire
time. The voice render is pinned in test_injected_voice.py. SYNTHETIC fixtures only."""
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
km = SourceFileLoader("romp_kernel_compsug", os.path.join(BIN, "romp-kernel")).load_module()
jd = km.jd

SID = "11111111-2222-3333-4444-eeeeeeeeeeee"
NOW = 1_788_200_000
IDLE = NOW - 7200          # settled two hours ago — past the hour gate
FRESH = NOW - 120          # settled two minutes ago — inside it


class CompactSuggest(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.saved_state = jd.STATE
        jd.STATE = Path(self.td.name)
        km._autonudge_cache.clear()
        km._set_compact_suggest(True)          # T208: default-OFF per install — these tests opt in
        km._autonudge_cache.clear()
        self._orig = {n: getattr(km, n) for n in ("_settle_event_key", "_thread_reg")}
        km._settle_event_key = lambda sid: IDLE
        km._thread_reg = lambda sid: {}
        self._orig_backend = km.Sessions.backend_for
        self.sent = []
        test = self

        class FakeBackend:
            def send(self, sid, body):
                test.sent.append(body)
        km.Sessions.backend_for = staticmethod(lambda sid: FakeBackend())

    def tearDown(self):
        for n, v in self._orig.items():
            setattr(km, n, v)
        km.Sessions.backend_for = self._orig_backend
        jd.STATE = self.saved_state
        km._autonudge_cache.clear()
        self.td.cleanup()

    def _tick(self, tokens, state="idle"):
        return km._compact_suggest_tick(SID, {"state": state, "ctxTokens": tokens}, NOW)

    def _latched(self):
        km._autonudge_cache.clear()
        return (km._auto_nudge_data().get("compactSuggested") or {}).get(SID, [])

    # ── the crossing latch ──
    def test_a_crossing_fires_once_and_latches(self):
        self.assertTrue(self._tick(450_000))
        self.assertEqual(len(self.sent), 1)
        self.assertIn("/compact", self.sent[0])
        # T207 (the user 2026-08-31, who saw the bare send render as their own blue bubble): the
        # send carries the sibling injectors' marker tail so the chat classifies it "romp" (gray
        # bubble), romp-auto = background kernel injection; the PROSE stays the bare constant the
        # injected-voice index scans.
        self.assertIn("<!-- romp-injected -->", self.sent[0])
        self.assertIn("<!-- romp-note:", self.sent[0])
        self.assertNotIn("<!-- romp-auto -->", self.sent[0],
                         "romp-auto means AUTO-NUDGES: its chat gist says 'nudged for a status "
                         "update', which this is not — injected alone renders the prose's first line")
        self.assertNotIn("<!-- romp-system -->", self.sent[0],
                         "person-voiced, not the machine-voiced notice family")
        self.assertNotIn("romp-goal-id", self.sent[0], "the suggestion tracks nothing")
        self.assertEqual(self.sent[0].split("<!--")[0].strip(), km.COMPACT_SUGGEST_TEXT.strip())
        self.assertEqual(self._latched(), [400_000], "latched on the durable record")
        self.assertFalse(self._tick(460_000), "same episode → never a second fire")
        self.assertEqual(len(self.sent), 1)

    def test_the_second_threshold_is_its_own_episode(self):
        self.assertTrue(self._tick(450_000))
        self.assertTrue(self._tick(820_000), "the 800k crossing is new information")
        self.assertEqual(len(self.sent), 2)
        self.assertEqual(sorted(self._latched()), [400_000, 800_000])
        self.assertFalse(self._tick(950_000), "…and both latches now stand: ignored = silent")

    def test_found_past_both_thresholds_fires_one_message(self):
        self.assertTrue(self._tick(900_000))
        self.assertEqual(len(self.sent), 1, "two suggestions in one tick would read as nagging")
        self.assertEqual(sorted(self._latched()), [400_000, 800_000])

    # ── the re-arm: the session's own context reset, never a nag ──
    def test_a_compact_rearms_exactly_the_thresholds_it_fell_below(self):
        self.assertTrue(self._tick(900_000))
        self.assertFalse(self._tick(500_000), "compacted to 500k: below 800k, still above 400k — "
                                              "nothing due (400k stands latched)")
        self.assertEqual(self._latched(), [400_000], "the 800k latch was pruned by the reset")
        self.assertTrue(self._tick(820_000), "regrown past 800k after the reset → one fresh fire")
        self.assertEqual(len(self.sent), 2)

    def test_a_full_reset_rearms_both(self):
        self.assertTrue(self._tick(900_000))
        self.assertFalse(self._tick(50_000), "fresh context — nothing due, latches prune")
        self.assertEqual(self._latched(), [])
        self.assertTrue(self._tick(450_000), "the next 400k crossing is a genuinely new episode")
        self.assertEqual(len(self.sent), 2)

    # ── the idle gate, at fire time ──
    def test_a_fresh_settle_holds_the_fire_without_spending_the_crossing(self):
        km._settle_event_key = lambda sid: FRESH
        self.assertFalse(self._tick(450_000), "settled minutes ago — not idle enough")
        self.assertEqual(self.sent, [])
        self.assertEqual(self._latched(), [], "the crossing stays ARMED — never latch a fire "
                                              "that never went out")
        km._settle_event_key = lambda sid: IDLE
        self.assertTrue(self._tick(450_000), "an hour idle later, the same crossing fires")

    def test_no_settle_evidence_no_fire(self):
        km._settle_event_key = lambda sid: 0
        self.assertFalse(self._tick(450_000))
        self.assertEqual(self.sent, [])

    # ── the exclusions ──
    def test_a_worker_tagged_session_is_never_suggested(self):
        (jd.STATE / "timeline-views.json").write_text(json.dumps(
            {"active": "all", "tags": [{"id": "t1", "name": "notes_workers",
                                        "members": [{"host": "", "sid": SID}]}]}))
        self.assertFalse(self._tick(450_000), "the recycle rule owns workers")
        self.assertEqual(self.sent, [])

    def test_a_muted_session_is_never_suggested(self):
        # the user's explicit per-session opt-out (hideFromFeed) — every sibling injector honors
        # it; a routed review pass caught this tick missing the check (2026-09-01)
        (jd.STATE / "session-flags.json").write_text(json.dumps({SID: {"hideFromFeed": True}}))
        km._flags_cache.clear()
        self.assertFalse(self._tick(450_000))
        self.assertEqual(self.sent, [])
        self.assertEqual(self._latched(), [], "…and the crossing stays armed, never spent")

    def test_a_comment_thread_fork_is_never_suggested(self):
        km._thread_reg = lambda sid: {"threadOf": "11111111-2222-3333-4444-ffffffffffff"}
        self.assertFalse(self._tick(450_000))
        self.assertEqual(self.sent, [])

    def test_a_mid_turn_session_is_never_suggested(self):
        self.assertFalse(self._tick(450_000, state="working"))
        self.assertEqual(self.sent, [])
        self.assertEqual(self._latched(), [], "…and the crossing stays armed for its settle")

    def test_no_token_count_no_fire(self):
        self.assertFalse(self._tick(None))
        self.assertFalse(self._tick(0))
        self.assertEqual(self.sent, [])

    # ── the T208 default: OFF for a fresh install, ON only by this install's own config ──
    def test_a_fresh_install_is_off_and_never_fires(self):
        (jd.STATE / "auto-nudge.json").unlink()        # a virgin install: no blob at all
        km._autonudge_cache.clear()
        self.assertFalse(km._compact_suggest_on(), "absent key reads OFF — shipping the feature "
                                                   "turns it on nowhere (the user's ruling)")
        self.assertFalse(self._tick(900_000), "idle, far past both thresholds — still nothing")
        self.assertEqual(self.sent, [])
        km._autonudge_cache.clear()
        self.assertEqual(self._latched(), [], "…and no latch spent while off")

    def test_the_designed_toggle_flips_it_on_and_off(self):
        km._set_compact_suggest(False)
        km._autonudge_cache.clear()
        self.assertFalse(self._tick(450_000))
        km._set_compact_suggest(True)
        km._autonudge_cache.clear()
        self.assertTrue(self._tick(450_000), "the same crossing fires once opted in")

    # ── the per-install config keys: "how to do it exactly" is config too ──
    def test_custom_thresholds_replace_the_defaults(self):
        d = dict(km._auto_nudge_data())
        d["compactSuggestTokens"] = [100_000, 200_000]
        km._write_auto_nudge(d)
        km._autonudge_cache.clear()
        self.assertTrue(self._tick(150_000), "past the CUSTOM first threshold, under the default")
        self.assertEqual(self._latched(), [100_000])
        self.assertTrue(self._tick(250_000), "…and the custom second is its own episode")

    def test_a_junk_thresholds_shape_falls_to_the_defaults(self):
        d = dict(km._auto_nudge_data())
        d["compactSuggestTokens"] = ["soon", -3]
        km._write_auto_nudge(d)
        km._autonudge_cache.clear()
        self.assertFalse(self._tick(150_000), "junk config never lowers the bar")
        self.assertTrue(self._tick(450_000), "the shipped defaults stand")

    def test_a_custom_idle_window_replaces_the_default(self):
        d = dict(km._auto_nudge_data())
        d["compactSuggestIdleS"] = 30
        km._write_auto_nudge(d)
        km._autonudge_cache.clear()
        km._settle_event_key = lambda sid: FRESH       # two minutes idle — under the default hour
        self.assertTrue(self._tick(450_000), "…but past the custom 30s window")

    # ── the fingerprint row ──
    def test_a_fire_logs_a_countable_row(self):
        self._tick(450_000)
        p = jd.STATE / "nudge-events.jsonl"
        rows = [json.loads(l) for l in p.read_text().splitlines()]
        self.assertEqual([r["verdict"] for r in rows], ["compact-suggested"])
        self.assertEqual(rows[0]["evT"], 450_000, "the row carries the token count it fired on")


if __name__ == "__main__":
    unittest.main()
