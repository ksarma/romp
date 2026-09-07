#!/usr/bin/env python3
"""The user-todo LIFECYCLE LOG (the user 2026-09-03): STATE/user-todos-log.jsonl, one JSON line per
event (filed, answered, dismissed, withdrawn, lost), appended and never rewritten, so the store can
be rebuilt exactly if it is ever lost or corrupted — the recovery that motivated it was lossy because
dashboard answers and dismissals left no trace outside the single store file.

Pinned here:
- each event appends its line from the store's own choke point, AFTER the store write: filed
  (_add_user_todo), answered / dismissed / withdrawn (_resolve_user_todo), lost (_reopen_user_todo,
  whichever delivery failure called it);
- the answered line carries the DELIVERED answer text as `reply` (the delivery-keyed stamp is the
  one place every answer path — immediate, parked drain, merged tmux paste — passes through);
- a log-write failure is one loud stderr line and never breaks the operation: the todo is still
  filed / resolved / reopened;
- the file is append-only (earlier lines are byte-identical after later events) and bounded by
  ROTATION past the size threshold (one older generation kept), not by a per-line cap;
- independent of the feature switch: nothing is gated, and while OFF no event happens, so nothing
  is logged;
- the fold helper _user_todos_from_log rebuilds the store shape: a round trip against the real
  store, a resolution whose filing was rotated away, a lost answer reopening, junk skipped.

SYNTHETIC fixtures only: placeholder UUIDs, the notes-api demo world. The real log holds real text
and lives only under STATE.
"""
import contextlib
import io
import json
import os
import tempfile
import unittest
from romp_load import load_source
from pathlib import Path
from unittest import mock

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
load_source("romp_event_model_utlog", os.path.join(BIN, "romp-event-model"))
load_source("romp_judge_utlog", os.path.join(BIN, "romp-judge"))
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ["ROMP_SERVE_TOKEN"] = "testtok"
km = load_source("romp_kernel_utlog", os.path.join(BIN, "romp-kernel"))
jd = km.jd

SID = "11111111-2222-3333-4444-555555555555"
SID2 = "22222222-3333-4444-5555-666666666666"


def _post(path, body):
    """Drive the REAL do_POST dispatcher over a fake socket (the auth-hardening harness), token on."""
    raw = json.dumps(body).encode()
    h = km.Handler.__new__(km.Handler)
    h.client_address = ("127.0.0.1", 0)
    h.headers = {"X-Romp-Token": km.TOKEN, "Content-Length": str(len(raw))}
    h.path, h.command, h.request_version = path, "POST", "HTTP/1.1"
    h.wfile, h.rfile, h.close_connection = io.BytesIO(), io.BytesIO(raw), True
    captured = {}
    h.send_response = lambda code, *a: captured.__setitem__("status", code)
    h.send_header = lambda k, v: None
    h.end_headers = lambda: None
    h.log_message = lambda *a: None
    h.do_POST()
    try:
        return captured.get("status"), json.loads(h.wfile.getvalue().decode() or "{}")
    except ValueError:
        return captured.get("status"), {}


class _Sandbox(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.saved = (jd.STATE, km._USER_TODOS_LOG_ROTATE_BYTES)
        jd.STATE = Path(self.td.name)
        km._user_todos_cache.clear()
        km._user_todos_bad.clear()
        km._set_user_todos(True)
        self.log = jd.STATE / km.USER_TODOS_LOG_FILE

    def tearDown(self):
        jd.STATE, km._USER_TODOS_LOG_ROTATE_BYTES = self.saved
        self.td.cleanup()
        km._user_todos_cache.clear()
        km._user_todos_bad.clear()

    def lines(self, p=None):
        p = p or self.log
        if not p.exists():
            return []
        return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


class EachEventAppendsItsLine(_Sandbox):
    def test_filed(self):
        tid = km._add_user_todo(SID, "Need the auth-scheme decision to wire login", "OAuth vs cookie")
        rows = self.lines()
        self.assertEqual(len(rows), 1)
        rec = rows[0]
        self.assertEqual({k: rec[k] for k in ("sid", "id", "kind", "text", "detail")},
                         {"sid": SID, "id": tid, "kind": "filed",
                          "text": "Need the auth-scheme decision to wire login", "detail": "OAuth vs cookie"})
        self.assertIsInstance(rec["t"], int)
        self.assertNotIn("reply", rec, "reply rides answered lines only")
        self.assertEqual(set(rec), {"t", "sid", "id", "kind", "text", "detail"}, "the documented shape, nothing else")

    def test_filed_without_detail_logs_an_empty_detail(self):
        km._add_user_todo(SID, "Need the staging port")
        self.assertEqual(self.lines()[0]["detail"], "")

    def test_withdrawn_and_dismissed_carry_the_rows_text(self):
        t1 = km._add_user_todo(SID, "Need the staging port", "for the load test")
        t2 = km._add_user_todo(SID, "Need your pick of the two layouts")
        self.assertTrue(km._resolve_user_todo(SID, t1, "withdrawn"))
        self.assertTrue(km._resolve_user_todo(SID, t2, "dismissed"))
        kinds = [(r["kind"], r["id"]) for r in self.lines()]
        self.assertEqual(kinds, [("filed", t1), ("filed", t2), ("withdrawn", t1), ("dismissed", t2)])
        w = self.lines()[2]
        self.assertEqual((w["text"], w["detail"]), ("Need the staging port", "for the load test"))
        self.assertNotIn("reply", w)

    def test_a_refused_resolution_logs_nothing(self):
        km._add_user_todo(SID, "Need the staging port")
        self.assertFalse(km._resolve_user_todo(SID, "ut-deadbeef", "dismissed"))
        self.assertEqual([r["kind"] for r in self.lines()], ["filed"])

    def test_answered_carries_the_delivered_reply(self):
        tid = km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        body = km._user_todo_answer_body("Need the auth-scheme decision to wire login", "OAuth, please")
        saved = (km._push_soon,)
        km._push_soon = lambda: None
        try:
            km._stamp_user_todo_answered(SID, tid, body)          # the delivery-keyed stamp, as every answer path
        finally:
            (km._push_soon,) = saved
        rec = self.lines()[-1]
        self.assertEqual(rec["kind"], "answered")
        self.assertEqual(rec["reply"], body, "the delivered text — the anchored Re: body — verbatim")
        self.assertIn("OAuth, please", rec["reply"])
        self.assertEqual(rec["text"], "Need the auth-scheme decision to wire login")

    def test_the_answer_op_lands_an_answered_line_through_the_stamp(self):
        tid = km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        sent = []
        client = {"send": lambda s: sent.append(json.loads(s))}
        saved = (km._name_of, km._sdk, km._send_or_park, km._push_soon)
        km._name_of = lambda sid: "web"
        km._sdk = lambda: None
        km._send_or_park = lambda be, sid, text, echo=None, user_todo=None: True
        km._push_soon = lambda: None
        try:
            km._drive({"type": "userTodoAnswer", "id": SID, "todoId": tid, "text": "OAuth, please"}, client)
        finally:
            km._name_of, km._sdk, km._send_or_park, km._push_soon = saved
        self.assertEqual([m for m in sent if m.get("type") == "warn"], [])
        rec = self.lines()[-1]
        self.assertEqual((rec["kind"], rec["id"]), ("answered", tid))
        self.assertIn("OAuth, please", rec["reply"])

    def test_lost_from_the_reopen_seam(self):
        tid = km._add_user_todo(SID, "Need the staging port", "for the load test")
        km._resolve_user_todo(SID, tid, "answered", reply="Re: Need the staging port — 8081")
        self.assertTrue(km._reopen_user_todo(SID, tid))
        rec = self.lines()[-1]
        self.assertEqual({k: rec[k] for k in ("kind", "id", "text", "detail")},
                         {"kind": "lost", "id": tid, "text": "Need the staging port", "detail": "for the load test"})
        self.assertNotIn("reply", rec)
        self.assertFalse(km._reopen_user_todo(SID, tid), "already open: nothing to lift")
        self.assertEqual(len(self.lines()), 3, "…and a no-op reopen logs nothing")

    def test_a_dismiss_or_withdraw_is_never_lifted_so_never_logged_lost(self):
        tid = km._add_user_todo(SID, "Need the staging port")
        km._resolve_user_todo(SID, tid, "dismissed")
        self.assertFalse(km._reopen_user_todo(SID, tid))
        self.assertEqual([r["kind"] for r in self.lines()], ["filed", "dismissed"])


class TheLogNeverBlocksTheOperation(_Sandbox):
    def test_a_failing_append_is_loud_and_the_todo_is_still_filed(self):
        err = io.StringIO()
        with mock.patch.object(km, "_user_todos_log_write", side_effect=OSError("disk full")), \
                contextlib.redirect_stderr(err):
            tid = km._add_user_todo(SID, "Need the staging port")
        self.assertEqual(km._user_todos()[SID][0]["id"], tid, "the store write stands")
        self.assertIn("lifecycle log append failed for filed", err.getvalue())
        self.assertIn("disk full", err.getvalue())
        self.assertFalse(self.log.exists())

    def test_a_failing_append_never_unwinds_a_resolution_or_a_reopen(self):
        tid = km._add_user_todo(SID, "Need the staging port")
        err = io.StringIO()
        with mock.patch.object(km, "_user_todos_log_write", side_effect=OSError("read-only")), \
                contextlib.redirect_stderr(err):
            self.assertTrue(km._resolve_user_todo(SID, tid, "answered", reply="x"))
            self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "answered")
            self.assertTrue(km._reopen_user_todo(SID, tid))
            self.assertNotIn("resolved", km._user_todos()[SID][0])
        self.assertEqual(err.getvalue().count("lifecycle log append failed"), 2)

    def test_the_log_is_written_only_after_the_store_write_landed(self):
        # a refused store write (the not-a-store guard) raises before any log line
        (jd.STATE / "user-todos.json").write_text(json.dumps({"enabled": True}))
        with contextlib.redirect_stderr(io.StringIO()):
            km._user_todos()
            with self.assertRaises(RuntimeError):
                km._add_user_todo(SID, "Need the staging port")
        self.assertFalse(self.log.exists(), "no 'filed' line for a filing that never landed")


class AppendOnlyAndRotation(_Sandbox):
    def test_earlier_lines_are_byte_identical_after_later_events(self):
        t1 = km._add_user_todo(SID, "Need the staging port")
        first = self.log.read_text()
        km._add_user_todo(SID2, "Need the auth-scheme decision")
        km._resolve_user_todo(SID, t1, "withdrawn")
        self.assertTrue(self.log.read_text().startswith(first), "append-only: the head never changes")
        self.assertEqual(len(self.lines()), 3)

    def test_the_writer_is_a_single_append(self):
        import inspect
        src = inspect.getsource(km._user_todos_log_write)
        self.assertIn('open(p, "a", encoding="utf-8")', src)
        self.assertIn('f.write(line + "\\n")', src)
        self.assertNotIn("_atomic_write", src, "no rewrite of the whole file, ever")

    def test_rotation_past_the_threshold_keeps_one_older_generation(self):
        km._USER_TODOS_LOG_ROTATE_BYTES = 400
        ids = [km._add_user_todo(SID, "Need the auth-scheme decision to wire login, take %d" % i) for i in range(6)]
        old = jd.STATE / "user-todos-log.1.jsonl"
        self.assertTrue(old.exists(), "the over-size file was renamed, not truncated")
        self.assertGreater(old.stat().st_size, 400)
        live = self.lines()
        rotated = self.lines(old)
        self.assertEqual([r["id"] for r in rotated] + [r["id"] for r in live], ids,
                         "every line survives across the two generations, in order")
        self.assertGreaterEqual(len(rotated), 1)
        self.assertGreaterEqual(len(live), 1, "the live file started fresh and took the lines after the rename")
        self.assertLessEqual(self.log.stat().st_size, old.stat().st_size)

    def test_a_second_rotation_replaces_the_older_generation(self):
        km._USER_TODOS_LOG_ROTATE_BYTES = 200
        for i in range(12):
            km._add_user_todo(SID, "Need the auth-scheme decision to wire login, take %d" % i)
        gens = sorted(p.name for p in jd.STATE.glob("user-todos-log*.jsonl"))
        self.assertEqual(gens, ["user-todos-log.1.jsonl", "user-todos-log.jsonl"], "exactly two generations")


class IndependentOfTheSwitch(_Sandbox):
    def test_while_off_nothing_happens_so_nothing_is_logged(self):
        km._set_user_todos(False)
        saved = (km._push_all, km._push_soon)
        km._push_all = km._push_soon = lambda *a, **k: None
        try:
            code, _ = _post("/usertodo", {"id": SID, "text": "Need the staging port"})
        finally:
            km._push_all, km._push_soon = saved
        self.assertEqual(code, 409)
        self.assertFalse(self.log.exists())

    def test_the_writer_itself_is_not_gated(self):
        import inspect
        for fn in (km._log_user_todo_event, km._user_todos_log_write):
            self.assertNotIn("_user_todos_on", inspect.getsource(fn))


class TheFold(_Sandbox):
    def _strip_times(self, store):
        out = {}
        for s, rows in store.items():
            out[s] = [{k: (v["kind"] if k == "resolved" else v) for k, v in t.items() if k != "createdT"}
                      for t in rows]
        return out

    def test_round_trip_against_the_real_store(self):
        t1 = km._add_user_todo(SID, "Need the auth-scheme decision to wire login", "OAuth vs cookie")
        t2 = km._add_user_todo(SID, "Need the staging port")
        t3 = km._add_user_todo(SID2, "Need your pick of the two layouts")
        km._resolve_user_todo(SID, t2, "dismissed")
        km._resolve_user_todo(SID2, t3, "answered", reply="Re: … — the second one")
        km._reopen_user_todo(SID2, t3)                            # the answer was lost: open again
        km._resolve_user_todo(SID2, t3, "withdrawn")
        rebuilt = km._user_todos_from_log(self.log.read_text().splitlines())
        self.assertEqual(self._strip_times(rebuilt), self._strip_times(km._user_todos()))
        self.assertEqual(rebuilt[SID][0]["id"], t1)
        self.assertNotIn("resolved", rebuilt[SID][0])
        self.assertEqual(rebuilt[SID][1]["resolved"]["kind"], "dismissed")
        self.assertEqual(rebuilt[SID2][0]["resolved"]["kind"], "withdrawn")
        # createdT is the filed line's time; the resolved stamp's time is the resolution line's
        self.assertEqual(rebuilt[SID][0]["createdT"], self.lines()[0]["t"])

    def test_it_takes_parsed_dicts_too_and_skips_junk(self):
        lines = [{"t": 1, "sid": SID, "id": "ut-1", "kind": "filed", "text": "a", "detail": ""},
                 "not json", json.dumps(["list"]), json.dumps({"kind": "filed"}),
                 {"t": 2, "sid": SID, "id": "ut-1", "kind": "dismissed", "text": "a", "detail": ""}]
        self.assertEqual(km._user_todos_from_log(lines),
                         {SID: [{"id": "ut-1", "text": "a", "createdT": 1, "resolved": {"kind": "dismissed", "t": 2}}]})

    def test_a_resolution_whose_filing_was_rotated_away_keeps_its_history(self):
        lines = [{"t": 9, "sid": SID, "id": "ut-9", "kind": "withdrawn", "text": "Need the port", "detail": "x"}]
        got = km._user_todos_from_log(lines)
        self.assertEqual(got[SID][0]["text"], "Need the port")
        self.assertEqual(got[SID][0]["detail"], "x")
        self.assertEqual(got[SID][0]["resolved"], {"kind": "withdrawn", "t": 9})

    def test_lost_lifts_the_stamp_and_a_duplicate_filed_is_ignored(self):
        lines = [{"t": 1, "sid": SID, "id": "ut-1", "kind": "filed", "text": "a", "detail": ""},
                 {"t": 1, "sid": SID, "id": "ut-1", "kind": "filed", "text": "a", "detail": ""},
                 {"t": 2, "sid": SID, "id": "ut-1", "kind": "answered", "text": "a", "detail": "", "reply": "r"},
                 {"t": 3, "sid": SID, "id": "ut-1", "kind": "lost", "text": "a", "detail": ""}]
        got = km._user_todos_from_log(lines)
        self.assertEqual(got, {SID: [{"id": "ut-1", "text": "a", "createdT": 1}]})

    def test_the_result_has_the_stores_shape(self):
        km._add_user_todo(SID, "Need the port")
        self.assertTrue(km._user_todo_store_shaped(km._user_todos_from_log(self.log.read_text().splitlines())))
        self.assertEqual(km._user_todos_from_log([]), {})


if __name__ == "__main__":
    unittest.main(verbosity=2)
