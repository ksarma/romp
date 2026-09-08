#!/usr/bin/env python3
"""Pinned notes (the user 2026-09-08): a session pins short notes above its own transcript for the
person it works for, what they should see first whenever they open it (where things stand, a warning,
a summary). Kernel side, pinned here:

- the store (pinned-notes.json under STATE): the minted id, persistence across a cache clear (a kernel
  restart reads the same file), sid-keying, oldest-first order, the per-session bound (PINNED_NOTES_MAX,
  the oldest dropped first), the store lock, the not-a-store guard;
- unpin's account: "unpinned" now, "already" (a note of its own taken down before, plainly, with when;
  a note the bound dropped says so), "unknown" (an id never this session's: another session's, since the
  store is sid-keyed, or one it never held: loud), "unreadable" (the store file is not a store: the fault
  named, never "no note of yours"); the tombstone that makes "already" possible and its bound;
- the bounds: a session id (_safe_id) at the store and the routes, since one row under any other key
  reads the whole file as not-a-store for every session; the text and detail lengths; control characters
  dropped; a non-object JSON body a 400;
- the POST routes (/pinnote, /unpinnote): the serve token, the answers (the evicted notes named), the
  ack-fast contract (never a synchronous push), the remote forward for a session an attached kernel owns
  and the 502 when that forward lands nothing (the wording shared with /usertodo/withdraw);
- the unpinNote drive op (the strip's own control) landing on the same _unpin_note;
- the wire seams: build_session's `pinnedNotes` field carrying real rows, the chatTail frame, the
  chat-build-sig fold, and the chat page skeleton's strip position, mirrored in the extension's.

PRIVATE synthetic sids (the goal-store fixture rule, generalized: rows minted under the shared
placeholder can be reached by another module's fixtures); the notes-api demo world.
"""
import ast
import contextlib
import inspect
import io
import json
import os
import re
import tempfile
import threading
import unittest
from romp_load import load_source
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
# Hermetic state BEFORE the loads: they resolve their state root at import time, and only pytest runs
# conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
load_source("romp_event_model", os.path.join(BIN, "romp-event-model"))
load_source("romp_judge", os.path.join(BIN, "romp-judge"))
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ["ROMP_SERVE_TOKEN"] = "testtok"
km = load_source("romp_kernel_pn", os.path.join(BIN, "romp-kernel"))
jd = km.jd
pm = load_source("romp_postal_pn_bounds", os.path.join(BIN, "romp-postal-service"))   # its copy of the bounds

SID = "8c8c8c8c-1111-4222-8333-944444444444"
SID2 = "8d8d8d8d-1111-4222-8333-944444444444"
RSID = "8e8e8e8e-1111-4222-8333-944444444444"    # a session an attached remote kernel owns
NOW = 1781200000


class _StoreSandbox(unittest.TestCase):
    """Per-test STATE sandbox + cache reset (the test_user_todos idiom)."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.saved = jd.STATE
        jd.STATE = Path(self.td.name)
        km._pinned_notes_cache.clear()
        km._pinned_notes_bad.clear()

    def tearDown(self):
        jd.STATE = self.saved
        self.td.cleanup()
        km._pinned_notes_cache.clear()
        km._pinned_notes_bad.clear()

    def _file(self):
        return json.loads((jd.STATE / km.PINNED_NOTES_FILE).read_text())


class StoreRoundTrip(_StoreSandbox):
    def test_pin_mints_a_pn_id_and_persists_the_record(self):
        nid, notes, _ = km._pin_note(SID, "Waiting on CI for the login fix", "The api tests flake on the auth step")
        self.assertRegex(nid, r"^pn-[0-9a-f]{8}$")
        self.assertEqual([n["id"] for n in notes], [nid], "the answer is the list after the pin")
        rec = self._file()[SID][0]
        self.assertEqual(rec["id"], nid)
        self.assertEqual(rec["text"], "Waiting on CI for the login fix")
        self.assertEqual(rec["detail"], "The api tests flake on the auth step")
        self.assertIsInstance(rec["createdT"], int)

    def test_detail_is_optional_and_absent_when_blank(self):
        km._pin_note(SID, "Read docs/plan.md first", "   ")
        self.assertNotIn("detail", self._file()[SID][0])

    def test_the_notes_survive_a_cache_clear_the_way_a_restart_reads_them(self):
        nid, _, _ = km._pin_note(SID, "Branch web-login is ready for review")
        km._pinned_notes_cache.clear()                       # a fresh kernel holds no cache
        self.assertEqual([n["id"] for n in km._pinned_notes_for(SID)], [nid])

    def test_the_store_is_sid_keyed(self):
        km._pin_note(SID, "web: the staging port is 8443")
        km._pin_note(SID2, "api: do not merge before the schema lands")
        self.assertEqual([n["text"] for n in km._pinned_notes_for(SID)], ["web: the staging port is 8443"])
        self.assertEqual([n["text"] for n in km._pinned_notes_for(SID2)], ["api: do not merge before the schema lands"])

    def test_the_list_is_oldest_first_by_createdT_not_file_order(self):
        (jd.STATE / km.PINNED_NOTES_FILE).write_text(json.dumps({SID: [
            {"id": "pn-bbbbbbbb", "text": "second", "createdT": NOW + 60},
            {"id": "pn-aaaaaaaa", "text": "first", "createdT": NOW}]}))
        self.assertEqual([n["id"] for n in km._pinned_notes_for(SID)], ["pn-aaaaaaaa", "pn-bbbbbbbb"])

    def test_ids_never_collide_within_a_session(self):
        # the retry loop is DRIVEN: the id source is made to answer the taken id once more before a fresh
        # one (a real 32-bit collision is too rare for the loop to be reached by chance)
        draws = iter(["aaaaaaaa" + "0" * 24, "aaaaaaaa" + "1" * 24, "bbbbbbbb" + "0" * 24])
        seen = []

        class _Uuid:
            def __init__(self):
                self.hex = next(draws); seen.append(self.hex[:8])

        real = km.uuid
        km.uuid = type("U", (), {"uuid4": staticmethod(_Uuid)})
        try:
            first = km._pin_note(SID, "note 0")[0]
            second = km._pin_note(SID, "note 1")[0]
        finally:
            km.uuid = real
        self.assertEqual(first, "pn-aaaaaaaa")
        self.assertEqual(second, "pn-bbbbbbbb", "the colliding draw was refused and the loop drew again")
        self.assertEqual(seen, ["aaaaaaaa", "aaaaaaaa", "bbbbbbbb"], "exactly one retry")
        # a tombstone's id counts as taken too: a re-minted id would make "already unpinned" ambiguous
        km._unpin_note(SID, "pn-bbbbbbbb")
        draws = iter(["bbbbbbbb" + "0" * 24, "cccccccc" + "0" * 24])
        km.uuid = type("U", (), {"uuid4": staticmethod(_Uuid)})
        try:
            self.assertEqual(km._pin_note(SID, "note 2")[0], "pn-cccccccc")
        finally:
            km.uuid = real

    def test_the_bound_drops_the_oldest_first(self):
        self.assertEqual(km.PINNED_NOTES_MAX, 8)
        # written by hand with distinct createdT so the order is not left to the clock's resolution
        (jd.STATE / km.PINNED_NOTES_FILE).write_text(json.dumps({SID: [
            {"id": "pn-%08d" % i, "text": "note %d" % i, "createdT": NOW + i} for i in range(8)]}))
        nid, notes, dropped = km._pin_note(SID, "the ninth")
        self.assertEqual(len(notes), 8, "never more than the bound")
        self.assertEqual(notes[-1]["id"], nid, "the new note is last (newest last)")
        self.assertNotIn("pn-00000000", [n["id"] for n in notes], "the oldest made room")
        self.assertEqual(notes[0]["id"], "pn-00000001")
        self.assertEqual([(d["id"], d["text"]) for d in dropped], [("pn-00000000", "note 0")],
                         "the eviction is REPORTED, never silent: the caller names the note that went")
        live = [t for t in self._file()[SID] if not t.get("unpinnedT")]
        self.assertEqual(len(live), 8, "the file holds the bounded list too")
        tomb = [t for t in self._file()[SID] if t.get("unpinnedT")]
        self.assertEqual([(t["id"], t["dropped"]) for t in tomb], [("pn-00000000", True)], "the dropped note leaves a tombstone marked so")
        acct = km._unpin_note(SID, "pn-00000000")
        self.assertEqual((acct["ok"], acct["state"], acct["dropped"]), (False, "already", True), "a later unpin of it is told what became of it")

    def test_a_pin_needs_a_session_id_so_one_bad_key_cannot_poison_the_store(self):
        # the reader's not-a-store guard requires EVERY top-level key to be a safe id: one row under a
        # session NAME or a path would make the whole file read as empty for every session and refuse
        # every later write (review round 1, 2026-09-08)
        km._pin_note(SID, "web: staging is on port 8443")
        for bad in ("my session", "web/api", "../x", "", "x" * 129):
            with self.subTest(sid=bad):
                with self.assertRaises(ValueError):
                    km._pin_note(bad, "hello")
        km._pinned_notes_cache.clear()
        self.assertEqual([n["text"] for n in km._pinned_notes_for(SID)], ["web: staging is on port 8443"], "the store is intact")
        km._pin_note(SID, "another")                                   # and still writable
        self.assertEqual(len(km._pinned_notes_for(SID)), 2)

    def test_the_helper_that_ships_the_rows_never_reads_the_clock(self):
        # the payload dedups by serialized content (the firstSeen lesson): a per-build value here
        # would re-send every session's chat about once a second
        for fn in (km._pinned_notes_for, km._pinned_note_rows, km._pinned_notes_fp):
            self.assertNotIn("time.time()", inspect.getsource(fn))

    def test_nothing_pinned_is_an_empty_list_and_an_empty_fingerprint(self):
        self.assertEqual(km._pinned_notes_for(SID), [])
        self.assertEqual(km._pinned_notes_fp(SID), "")
        km._pin_note(SID, "one")
        self.assertTrue(km._pinned_notes_fp(SID))
        self.assertEqual(km._pinned_notes_fp(SID2), "", "the fold is per sid")


class Unpin(_StoreSandbox):
    def test_unpin_removes_the_note_and_answers_the_rest(self):
        a, _, _ = km._pin_note(SID, "first")
        b, _, _ = km._pin_note(SID, "second")
        acct = km._unpin_note(SID, a)
        self.assertEqual((acct["ok"], acct["state"]), (True, "unpinned"))
        self.assertEqual([n["id"] for n in acct["notes"]], [b])
        self.assertEqual([n["id"] for n in km._pinned_notes_for(SID)], [b])

    def test_unknown_id_is_refused_loudly_never_a_silent_success(self):
        km._pin_note(SID, "one")
        acct = km._unpin_note(SID, "pn-deadbeef")
        self.assertEqual((acct["ok"], acct["state"]), (False, "unknown"))
        self.assertTrue(acct.get("error"))
        self.assertEqual(len(acct["notes"]), 1, "the list still rides the refusal, so the caller can see it")

    def test_a_second_unpin_of_the_same_id_is_already_with_when_not_a_refusal(self):
        # the #325 shape: the person clicked Unpin on the strip, then the session tidies up with
        # unpin_note. The state it wanted holds, so the answer is plain, not an error the agent retries.
        nid, _, _ = km._pin_note(SID, "one")
        self.assertTrue(km._unpin_note(SID, nid)["ok"])
        again = km._unpin_note(SID, nid)
        self.assertEqual((again["ok"], again["state"], again["dropped"]), (False, "already", False))
        self.assertIsInstance(again["at"], int)
        self.assertEqual(again["notes"], [])
        tomb = self._file()[SID]
        self.assertEqual([(t["id"], "text" in t) for t in tomb], [(nid, False)], "the tombstone is the id and the time, not the text")
        self.assertEqual(km._pinned_notes_for(SID), [], "a tombstone is no row")

    def test_tombstones_are_bounded_per_session(self):
        for i in range(km.PINNED_TOMBSTONES_MAX + 3):
            nid, _, _ = km._pin_note(SID, "note %d" % i)
            km._unpin_note(SID, nid)
        tomb = [t for t in self._file()[SID] if t.get("unpinnedT")]
        self.assertEqual(len(tomb), km.PINNED_TOMBSTONES_MAX)
        self.assertEqual(km._unpin_note(SID, nid)["state"], "already", "the newest unpins are the ones remembered")

    def test_another_sessions_id_is_unknown_here_and_that_note_stands(self):
        theirs, _, _ = km._pin_note(SID2, "api: do not merge before the schema lands")
        km._pin_note(SID, "web: mine")
        acct = km._unpin_note(SID, theirs)
        self.assertEqual((acct["ok"], acct["state"]), (False, "unknown"), "the store is sid-keyed: a session reaches only its own rows")
        self.assertEqual([n["id"] for n in km._pinned_notes_for(SID2)], [theirs], "the other session's note stands")

    def test_the_last_unpin_leaves_only_the_tombstone_under_the_key(self):
        nid, _, _ = km._pin_note(SID, "only one")
        km._unpin_note(SID, nid)
        self.assertEqual([t["id"] for t in self._file()[SID]], [nid])
        self.assertEqual(km._pinned_notes_for(SID), [])
        self.assertEqual(km._pinned_notes_fp(SID), json.dumps(self._file()[SID], sort_keys=True), "the fold moves with the write")

    def test_unpin_against_an_unreadable_store_names_the_fault_not_no_note_of_yours(self):
        # the store reads as EMPTY once loudly; an unpin over that read must not conclude the note
        # never existed (review round 1, 2026-09-08: fail loudly, never a wrong plain answer)
        p = jd.STATE / km.PINNED_NOTES_FILE
        p.write_text("{not json")
        with contextlib.redirect_stderr(io.StringIO()):
            acct = km._unpin_note(SID, "pn-deadbeef")
        self.assertEqual((acct["ok"], acct["state"], acct["notes"]), (False, "unreadable", []))
        self.assertIn("not readable", acct["error"])
        self.assertIn(str(p), acct["error"], "the fault names the file")
        self.assertEqual(p.read_text(), "{not json", "nothing written")
        p.unlink()                                                   # fixed (removed): the plain answers return
        self.assertEqual(km._unpin_note(SID, "pn-deadbeef")["state"], "unknown")


class StoreGuards(_StoreSandbox):
    def test_every_store_mutation_runs_under_the_lock(self):
        real_write = km._write_pinned_notes
        seen = []

        def guarded(cur):
            seen.append(km._pinned_notes_lock._is_owned())
            real_write(cur)

        km._write_pinned_notes = guarded
        try:
            nid, _, _ = km._pin_note(SID, "one")
            km._unpin_note(SID, nid)
        finally:
            km._write_pinned_notes = real_write
        self.assertEqual(len(seen), 2)
        self.assertTrue(all(seen), "a store write outside the lock is the lost-update bug")

    def test_concurrent_pins_lose_nothing(self):
        n = 6
        barrier = threading.Barrier(2)

        def writer(sid):
            barrier.wait()
            for i in range(n):
                km._pin_note(sid, "note %d" % i)

        ts = [threading.Thread(target=writer, args=(s,)) for s in (SID, SID2)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        km._pinned_notes_cache.clear()
        d = self._file()
        self.assertEqual(len(d[SID]) + len(d[SID2]), 2 * n)

    def test_a_file_that_is_not_a_store_reads_empty_loudly_and_is_never_overwritten(self):
        p = jd.STATE / km.PINNED_NOTES_FILE
        p.write_text(json.dumps({"enabled": True}))     # a settings blob, not sid -> list
        err = io.StringIO()
        saved = km.sys.stderr
        km.sys.stderr = err
        try:
            self.assertEqual(km._pinned_notes(), {})
            self.assertEqual(km._pinned_notes(), {}, "the second read is silent (once per file version)")
            with self.assertRaises(RuntimeError):
                km._pin_note(SID, "would replace someone's notes")
        finally:
            km.sys.stderr = saved
        self.assertEqual(err.getvalue().count("is not a pinned-notes store (top-level keys"), 1, "one read notice per file version")
        self.assertEqual(err.getvalue().count("pinned-notes: refusing to overwrite"), 1, "and the refused write says so")
        self.assertEqual(json.loads(p.read_text()), {"enabled": True}, "the file is untouched")
        p.unlink()                                       # fixed (removed): writes flow again
        km._pin_note(SID, "fine now")
        self.assertEqual(len(self._file()[SID]), 1)


def _serve_post(path, body, headers=None):
    """Drive the REAL do_POST dispatcher over a fake socket (the auth-hardening harness)."""
    raw = json.dumps(body).encode() if isinstance(body, (dict, list)) else (body or b"")
    h = km.Handler.__new__(km.Handler)
    h.client_address = ("127.0.0.1", 0)
    hdrs = dict(headers or {})
    hdrs.setdefault("Content-Length", str(len(raw)))
    h.headers = hdrs
    h.path = path
    h.command = "POST"
    h.request_version = "HTTP/1.1"
    h.wfile = io.BytesIO()
    h.rfile = io.BytesIO(raw)
    h.close_connection = True
    captured = {}
    h.send_response = lambda code, *a: captured.__setitem__("status", code)
    h.send_header = lambda k, v: None
    h.end_headers = lambda: None
    h.log_message = lambda *a: None
    h.do_POST()
    return captured.get("status"), h.wfile.getvalue()


class _RouteLab(_StoreSandbox):
    """The route harness (no tests of its own): the pusher stubs and the POST helper that Routes and
    RemoteForward share. RemoteForward is NOT a Routes subclass: it would inherit the seven local-path
    tests and run them again under the remote stubs, a misleading count (review round 1, 2026-09-08)."""

    def setUp(self):
        super().setUp()
        self._push = (km._push_all, km._push_soon)
        self.pushed_soon = []
        # the routes must never build views synchronously (the ack-fast contract): a stray _push_all
        # here is a bug, so it BLOWS UP instead of silently passing
        km._push_all = lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("synchronous _push_all on a postal-called route"))
        km._push_soon = lambda: self.pushed_soon.append(True)

    def tearDown(self):
        km._push_all, km._push_soon = self._push
        super().tearDown()

    def _post(self, path, body, token=True):
        hdrs = {"X-Romp-Token": km.TOKEN} if token else {}
        code, out = _serve_post(path, body, hdrs)
        try:
            return code, json.loads(out.decode() or "{}")
        except ValueError:
            return code, {}


class Routes(_RouteLab):
    """POST /pinnote and /unpinnote: the kernel legs the postal tools stand on."""

    def test_both_routes_require_the_serve_token(self):
        self.assertEqual(self._post("/pinnote", {"id": SID, "text": "x"}, token=False)[0], 403)
        self.assertEqual(self._post("/unpinnote", {"id": SID, "noteId": "pn-deadbeef"}, token=False)[0], 403)

    def test_pin_answers_the_minted_id_and_the_list_and_writes_the_store(self):
        code, res = self._post("/pinnote", {"id": SID, "text": "Waiting on CI for the login fix",
                                            "detail": "The api tests flake on the auth step"})
        self.assertEqual(code, 200)
        self.assertTrue(res["ok"])
        self.assertRegex(res["noteId"], r"^pn-[0-9a-f]{8}$")
        self.assertEqual([n["id"] for n in res["notes"]], [res["noteId"]])
        rec = km._pinned_notes_for(SID)[0]
        self.assertEqual(rec["id"], res["noteId"])
        self.assertEqual(rec["detail"], "The api tests flake on the auth step")

    def test_pin_refuses_a_bodyless_or_textless_ask(self):
        self.assertEqual(self._post("/pinnote", {"id": SID})[0], 400)
        self.assertEqual(self._post("/pinnote", {"text": "no sid"})[0], 400)
        self.assertEqual(self._post("/pinnote", {"id": SID, "text": "   "})[0], 400)
        self.assertEqual(self._post("/pinnote", {"id": SID, "text": "\x00\x00"})[0], 400, "nothing but control characters is a blank")
        code, _ = _serve_post("/pinnote", b"not json", {"X-Romp-Token": km.TOKEN})
        self.assertEqual(code, 400)

    def test_a_non_object_json_body_is_a_400_on_both_routes_never_a_traceback(self):
        for raw in (b'"abc"', b"[1, 2]", b"7", b"true"):
            for path in ("/pinnote", "/unpinnote"):
                with self.subTest(path=path, body=raw):
                    code, out = _serve_post(path, raw, {"X-Romp-Token": km.TOKEN})
                    self.assertEqual(code, 400)
                    self.assertNotIn(b"Traceback", out)

    def test_pin_refuses_an_id_that_is_not_a_session_id_and_the_store_stays_whole(self):
        # one accepted row under a non-session key (a session NAME, a path) made the reader flag the
        # whole file as not-a-store: every session's strip blank, every later pin a 500 (review round 1)
        self._post("/pinnote", {"id": SID, "text": "web: staging is on port 8443"})
        for bad in ("my session", "web/api", "../x"):
            with self.subTest(sid=bad):
                code, out = self._post("/pinnote", {"id": bad, "text": "hello"})
                self.assertEqual(code, 400)
                self.assertIn("session id", out["error"])
                self.assertEqual(self._post("/unpinnote", {"id": bad, "noteId": "pn-deadbeef"})[0], 400)
        km._pinned_notes_cache.clear()
        self.assertEqual([n["text"] for n in km._pinned_notes_for(SID)], ["web: staging is on port 8443"])
        self.assertEqual(self._post("/pinnote", {"id": SID, "text": "another"})[0], 200, "still writable")

    def test_text_and_detail_are_bounded_and_cleaned_of_control_characters(self):
        self.assertEqual((km.PINNED_TEXT_MAX, km.PINNED_DETAIL_MAX), (300, 4000))
        self.assertEqual((pm.PIN_TEXT_MAX, pm.PIN_DETAIL_MAX), (km.PINNED_TEXT_MAX, km.PINNED_DETAIL_MAX),
                         "the postal tool refuses with the kernel's numbers")
        code, out = self._post("/pinnote", {"id": SID, "text": "x" * 301})
        self.assertEqual(code, 400)
        self.assertIn("300", out["error"])
        code, out = self._post("/pinnote", {"id": SID, "text": "fine", "detail": "y" * 4001})
        self.assertEqual(code, 400)
        self.assertIn("4000", out["error"])
        self.assertEqual(self._post("/pinnote", {"id": SID, "text": "x" * 300, "detail": "y" * 4000})[0], 200, "the bound itself is allowed")
        code, res = self._post("/pinnote", {"id": SID, "text": " line1\nline2\ttab\x00nul\x1b[31mred ",
                                            "detail": "d\x07\n keep"})
        self.assertEqual(code, 200)
        rec = km._pinned_notes_for(SID)[-1]
        self.assertEqual(rec["text"], "line1\nline2\ttabnul[31mred", "control characters dropped; newline and tab kept; ends trimmed")
        self.assertEqual(rec["detail"], "d\n keep")
        self.assertEqual(self._post("/pinnote", {"id": SID, "text": "\x1b\x07"})[0], 400, "control characters alone clean to nothing")
        self.assertEqual(km._pinned_note_clean(None), "")

    def test_a_ninth_pin_names_the_note_it_dropped(self):
        for i in range(8):
            self._post("/pinnote", {"id": SID, "text": "note %d" % i})
        code, res = self._post("/pinnote", {"id": SID, "text": "note 8"})
        self.assertEqual(code, 200)
        self.assertEqual([d["text"] for d in res["dropped"]], ["note 0"])
        self.assertEqual(len(res["notes"]), 8)
        code, res = self._post("/pinnote", {"id": SID2, "text": "first here"})
        self.assertEqual(res["dropped"], [], "the key is always there: nothing dropped is an empty list")

    def test_unpin_removes_and_answers_the_rest(self):
        _, a = self._post("/pinnote", {"id": SID, "text": "first"})
        _, b = self._post("/pinnote", {"id": SID, "text": "second"})
        code, out = self._post("/unpinnote", {"id": SID, "noteId": a["noteId"]})
        self.assertEqual(code, 200)
        self.assertTrue(out["ok"])
        self.assertEqual([n["id"] for n in out["notes"]], [b["noteId"]])

    def test_unpin_of_an_unknown_or_foreign_id_answers_ok_false_with_the_reason(self):
        code, out = self._post("/unpinnote", {"id": SID, "noteId": "pn-deadbeef"})
        self.assertEqual(code, 200)
        self.assertEqual((out["ok"], out["state"]), (False, "unknown"), "a loud, plain answer, never a silent success")
        self.assertTrue(out.get("error"))
        _, theirs = self._post("/pinnote", {"id": SID2, "text": "api: theirs"})
        _, out2 = self._post("/unpinnote", {"id": SID, "noteId": theirs["noteId"]})
        self.assertEqual((out2["ok"], out2["state"]), (False, "unknown"), "another session's id is not this session's to take down")
        self.assertEqual(len(km._pinned_notes_for(SID2)), 1)

    def test_unpin_of_an_already_unpinned_note_carries_the_already_account(self):
        _, res = self._post("/pinnote", {"id": SID, "text": "one"})
        self._post("/unpinnote", {"id": SID, "noteId": res["noteId"]})
        code, out = self._post("/unpinnote", {"id": SID, "noteId": res["noteId"]})
        self.assertEqual(code, 200)
        self.assertEqual((out["ok"], out["state"], out["dropped"]), (False, "already", False))
        self.assertIsInstance(out["at"], int)

    def test_unpin_against_an_unreadable_store_answers_the_fault(self):
        (jd.STATE / km.PINNED_NOTES_FILE).write_text("{not json")
        with contextlib.redirect_stderr(io.StringIO()):
            code, out = self._post("/unpinnote", {"id": SID, "noteId": "pn-deadbeef"})
        self.assertEqual(code, 200)
        self.assertEqual((out["ok"], out["state"]), (False, "unreadable"))
        self.assertIn("not readable", out["error"])
        self.assertEqual(self.pushed_soon, [], "nothing changed, so no wake")

    def test_the_withdraw_route_shares_the_no_answer_wording(self):
        # one code path for the four-way "why the remote gave no answer" line (review round 1,
        # 2026-09-08); test_user_todos pins the withdraw route's own 502 behaviour, unchanged
        src = inspect.getsource(km.Handler.do_POST)
        for route in ("/usertodo/withdraw", "/pinnote", "/unpinnote"):
            self.assertIn('_remote_no_answer_why(r, st, "%s")' % route, src)
        self.assertNotIn('why = "the tunnel to %s is not answering', src, "no inline copy of the wording remains")
        r = {"host": "TESTHOST"}
        self.assertEqual(km._remote_no_answer_why(r, 0, "/usertodo/withdraw"), "the tunnel to TESTHOST is not answering (re-dialing)")
        self.assertEqual(km._remote_no_answer_why(r, 404, "/usertodo/withdraw"),
                         "the kernel on TESTHOST predates /usertodo/withdraw: update romp there and restart it")
        self.assertEqual(km._remote_no_answer_why(r, 500, "/pinnote"), "the kernel on TESTHOST answered HTTP 500")
        self.assertEqual(km._remote_no_answer_why(r, 200, "/pinnote"), "the kernel on TESTHOST answered a body that is not JSON")

    def test_unpin_refuses_a_bodyless_ask(self):
        self.assertEqual(self._post("/unpinnote", {"id": SID})[0], 400)
        self.assertEqual(self._post("/unpinnote", {"noteId": "pn-deadbeef"})[0], 400)

    def test_the_routes_ack_fast_and_wake_the_pusher(self):
        # the postal bus times its POST out at 2s: an inline _push_all (a synchronous build of every
        # session's payload) outran it on the user-todo route once. The setUp _push_all stub raises,
        # so this passing IS the proof; the woken pusher carries the strip.
        code, res = self._post("/pinnote", {"id": SID, "text": "one"})
        self.assertEqual(code, 200)
        code, out = self._post("/unpinnote", {"id": SID, "noteId": res["noteId"]})
        self.assertEqual(code, 200)
        self.assertEqual(len(self.pushed_soon), 2, "each landed write wakes the pusher")
        self._post("/unpinnote", {"id": SID, "noteId": "pn-deadbeef"})
        self.assertEqual(len(self.pushed_soon), 2, "a refused unpin changed nothing, so no wake")


class RemoteForward(_RouteLab):
    """A session an attached kernel owns: the routes forward over its tunnel the way /usertodo/withdraw
    does, and a forward that lands nothing is a 502 saying why, never a 200 the tool would echo back."""

    def setUp(self):
        super().setUp()
        self._remote_saved = (km._host_for_sid, km._remote_forward_status)
        self.calls = []
        self.answer = (200, {"ok": True, "noteId": "pn-0badcafe",
                             "notes": [{"id": "pn-0badcafe", "text": "remote note", "createdT": NOW}]})
        km._host_for_sid = lambda sid: ({"host": "TESTHOST", "local_port": 1, "token": "t", "sids": [RSID]}
                                        if sid == RSID else None)
        km._remote_forward_status = lambda r, path, body, method="POST": (self.calls.append((path, body)) or self.answer)

    def tearDown(self):
        km._host_for_sid, km._remote_forward_status = self._remote_saved
        super().tearDown()

    def test_pin_for_a_remote_session_is_forwarded_and_written_nowhere_locally(self):
        code, res = self._post("/pinnote", {"id": RSID, "text": "remote note", "detail": "d"})
        self.assertEqual(code, 200)
        self.assertEqual(res, {"ok": True, "noteId": "pn-0badcafe", "notes": self.answer[1]["notes"], "dropped": []})
        self.assertEqual(self.calls, [("/pinnote", {"id": RSID, "text": "remote note", "detail": "d"})])
        self.assertEqual(km._pinned_notes(), {}, "the owning kernel holds the store")
        # the remote's evictions ride through
        self.answer = (200, {"ok": True, "noteId": "pn-0badcafe", "notes": [], "dropped": [{"id": "pn-00000000", "text": "old"}]})
        code, res = self._post("/pinnote", {"id": RSID, "text": "remote note"})
        self.assertEqual(res["dropped"], [{"id": "pn-00000000", "text": "old"}])

    def test_unpin_for_a_remote_session_is_forwarded_with_its_account(self):
        self.answer = (200, {"ok": False, "state": "already", "at": NOW, "dropped": False, "error": "already unpinned", "notes": []})
        code, res = self._post("/unpinnote", {"id": RSID, "noteId": "pn-deadbeef"})
        self.assertEqual(code, 200)
        self.assertEqual(res, {"ok": False, "state": "already", "at": NOW, "dropped": False, "error": "already unpinned", "notes": []})
        self.assertEqual(self.calls, [("/unpinnote", {"id": RSID, "noteId": "pn-deadbeef"})])
        # a remote kernel that predates the account answers ok alone: nothing is invented
        self.answer = (200, {"ok": False})
        self.assertEqual(self._post("/unpinnote", {"id": RSID, "noteId": "pn-deadbeef"})[1], {"ok": False, "notes": []})

    def test_a_dead_tunnel_or_an_older_remote_is_a_502_that_names_the_cause(self):
        saved = km.sys.stderr
        km.sys.stderr = io.StringIO()
        try:
            self.answer = (0, None)
            code, res = self._post("/pinnote", {"id": RSID, "text": "remote note"})
            self.assertEqual(code, 502)
            self.assertFalse(res["ok"])
            self.assertIn("not answering", res["error"])
            self.assertEqual(res["host"], "TESTHOST")
            self.answer = (404, None)
            code, res = self._post("/unpinnote", {"id": RSID, "noteId": "pn-0badcafe"})
            self.assertEqual(code, 502)
            self.assertIn("predates /unpinnote", res["error"])
        finally:
            km.sys.stderr = saved
        self.assertEqual(self.pushed_soon, [], "a forward wakes no local pusher: nothing local changed")


class DriveOp(_StoreSandbox):
    """unpinNote: the strip's own Unpin control, landing on the same _unpin_note as the route."""

    def setUp(self):
        super().setUp()
        self.sent = []
        self.client = {"send": lambda s: self.sent.append(json.loads(s))}
        self._saved = (km._name_of, km._sdk, km._push_soon)
        km._name_of = lambda sid: "web" if sid == SID else None
        km._sdk = lambda: None
        km._push_soon = lambda: None

    def tearDown(self):
        km._name_of, km._sdk, km._push_soon = self._saved
        super().tearDown()

    def test_unpin_is_an_id_op(self):
        # membership in the ID_OPS tuple itself (a source substring would be satisfied by the elif alone)
        tree = ast.parse(inspect.getsource(km._drive).lstrip())
        ops = None
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "ID_OPS" for t in node.targets):
                ops = ast.literal_eval(node.value)
        self.assertIsNotNone(ops, "ID_OPS is a literal tuple in _drive")
        self.assertIn("unpinNote", ops)

    def test_unpin_removes_the_note_quietly(self):
        nid, _, _ = km._pin_note(SID, "one")
        self.assertTrue(km._drive({"type": "unpinNote", "id": SID, "noteId": nid}, self.client))
        self.assertEqual(km._pinned_notes_for(SID), [])
        self.assertEqual(self.sent, [], "a clean unpin raises no warning")

    def test_unpin_of_a_gone_id_warns_loudly(self):
        nid, _, _ = km._pin_note(SID, "one")
        km._drive({"type": "unpinNote", "id": SID, "noteId": nid}, self.client)
        km._drive({"type": "unpinNote", "id": SID, "noteId": nid}, self.client)      # a second click on a removed row
        self.assertEqual([(m["type"], m["text"]) for m in self.sent], [("warn", "That note was already unpinned.")])
        km._drive({"type": "unpinNote", "id": SID, "noteId": "pn-deadbeef"}, self.client)
        self.assertEqual(self.sent[-1]["text"], "No such note is pinned on this session.")

    def test_unpin_against_an_unreadable_store_warns_with_the_fault(self):
        (jd.STATE / km.PINNED_NOTES_FILE).write_text("{not json")
        with contextlib.redirect_stderr(io.StringIO()):
            km._drive({"type": "unpinNote", "id": SID, "noteId": "pn-deadbeef"}, self.client)
        self.assertEqual(self.sent[-1]["type"], "warn")
        self.assertIn("not readable", self.sent[-1]["text"])
        self.assertNotIn("already", self.sent[-1]["text"])


class WireSeams(unittest.TestCase):
    """The rows reach the strip through the chat frames the transcript pane already reads: one path."""

    def test_the_chat_tail_carries_the_field_beside_user_todos(self):
        src = inspect.getsource(km._send_chat_locked)
        self.assertIn('"pinnedNotes": m.get("pinnedNotes") or []', src)

    def test_the_chat_build_sig_folds_the_per_sid_fingerprint(self):
        src = inspect.getsource(km._chat_build_sig)
        self.assertIn('sig.append(_pinned_notes_fp(sess.get("sid") or ""))', src)

    def test_the_chat_page_skeleton_puts_the_strip_below_the_tabs_and_above_the_transcript(self):
        body = km._chat_body()
        tabs, strip, content = body.index('id="tabbar"'), body.index('id="pinned-notes"'), body.index('id="content"')
        self.assertLess(tabs, strip)
        self.assertLess(strip, content)
        self.assertIn('<div id="pinned-notes" style="display:none"></div>', body, "hidden until notes arrive")
        # the extension's skeleton mirrors it (the composer-files lesson: the two must grow in step)
        ext = Path(HERE).parent / "vscode-extension" / "src" / "page-skeleton.ts"
        self.assertIn('<div id="pinned-notes" style="display:none"></div>', ext.read_text())


class BuildSessionSeam(unittest.TestCase):
    """The chat payload's top-level `pinnedNotes` field carries the session's rows (the userTodos
    harness, with the store swapped)."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        td = Path(self.td.name)
        cdir = td / "launchdir"
        cdir.mkdir()
        proj = td / "projects"
        pdir = proj / jd.re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(str(cdir)))
        pdir.mkdir(parents=True)
        self.tpath = pdir / (SID + ".jsonl")
        names = td / "names"
        names.mkdir()
        (names / SID).write_text("web\t%s\t#abcdef\n" % str(cdir))
        self.saved = (jd.NAMES, jd.PROJECTS, jd.GOALDIR, jd.STATE, km.NAMES,
                      km._read_task_store, km._tmux_sessions, km._GLOBAL_CLAUDE_MD)
        jd.NAMES, jd.PROJECTS, jd.GOALDIR, jd.STATE = names, proj, td / "goals", td
        km.NAMES = names
        km._GLOBAL_CLAUDE_MD = td / "no-global.md"
        km._read_task_store = lambda fsid, fold=None: []
        km._tmux_sessions = lambda: {SID: {"state": "idle", "since": NOW - 100, "model": "", "effort": "",
                                           "context": None, "compactPct": None, "color": None}}
        jd.GOALDIR.mkdir(parents=True)
        km._parse_cache.clear()
        km._pinned_notes_cache.clear()
        rows = [
            {"type": "user", "uuid": "u1", "timestamp": "2026-06-01T00:00:00Z",
             "sessionId": SID, "message": {"role": "user", "content": "wire the login routes"}},
            {"type": "assistant", "uuid": "a1", "parentUuid": "u1", "timestamp": "2026-06-01T00:00:05Z",
             "sessionId": SID,
             "message": {"role": "assistant", "stop_reason": "end_turn",
                         "content": [{"type": "text", "text": "starting on the open routes"}]}},
        ]
        self.tpath.write_text("\n".join(json.dumps(r) for r in rows) + "\n")

    def tearDown(self):
        (jd.NAMES, jd.PROJECTS, jd.GOALDIR, jd.STATE, km.NAMES,
         km._read_task_store, km._tmux_sessions, km._GLOBAL_CLAUDE_MD) = self.saved
        km._parse_cache.clear()
        km._pinned_notes_cache.clear()
        self.td.cleanup()

    def test_no_notes_is_an_empty_field(self):
        self.assertEqual(km.build_session(SID, NOW)["pinnedNotes"], [])

    def test_pinned_notes_ride_the_field_oldest_first(self):
        a, _, _ = km._pin_note(SID, "Read docs/plan.md first", "the plan's second section is the current one")
        b, _, _ = km._pin_note(SID, "Waiting on CI for #12")
        payload = km.build_session(SID, NOW)
        self.assertEqual([n["id"] for n in payload["pinnedNotes"]], [a, b])
        self.assertEqual(payload["pinnedNotes"][0]["detail"], "the plan's second section is the current one")
        self.assertEqual([e for e in payload["events"] if e.get("kind") == "todo"], [],
                         "a pinned note is not a user todo: no split card for it")


if __name__ == "__main__":
    unittest.main()
