#!/usr/bin/env python3
"""Pinned notes (the user 2026-09-08): a session pins short notes above its own transcript for the
person it works for, what they should see first whenever they open it (where things stand, a warning,
a summary). Kernel side, pinned here:

- the store (pinned-notes.json under STATE): the minted id, persistence across a cache clear (a kernel
  restart reads the same file), sid-keying, oldest-first order, the per-session bound (PINNED_NOTES_MAX,
  the oldest dropped first), the store lock, the not-a-store guard;
- unpin: the loud refusal of an unknown id, an already-unpinned id and ANOTHER SESSION's id (the store
  is sid-keyed, so a session reaches only its own rows), and the key leaving the file with its last note;
- the POST routes (/pinnote, /unpinnote): the serve token, the answers, the ack-fast contract (never a
  synchronous push), the remote forward for a session an attached kernel owns and the 502 when that
  forward lands nothing;
- the unpinNote drive op (the strip's own control) landing on the same _unpin_note;
- the wire seams: build_session's `pinnedNotes` field carrying real rows, the chatTail frame, the
  chat-build-sig fold, and the chat page skeleton's strip position, mirrored in the extension's.

PRIVATE synthetic sids (the goal-store fixture rule, generalized: rows minted under the shared
placeholder can be reached by another module's fixtures); the notes-api demo world.
"""
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
        nid, notes = km._pin_note(SID, "Waiting on CI for the login fix", "The api tests flake on the auth step")
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
        nid, _ = km._pin_note(SID, "Branch web-login is ready for review")
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
        ids = {km._pin_note(SID, "note %d" % i)[0] for i in range(km.PINNED_NOTES_MAX)}
        self.assertEqual(len(ids), km.PINNED_NOTES_MAX)

    def test_the_bound_drops_the_oldest_first(self):
        self.assertEqual(km.PINNED_NOTES_MAX, 8)
        # written by hand with distinct createdT so the order is not left to the clock's resolution
        (jd.STATE / km.PINNED_NOTES_FILE).write_text(json.dumps({SID: [
            {"id": "pn-%08d" % i, "text": "note %d" % i, "createdT": NOW + i} for i in range(8)]}))
        nid, notes = km._pin_note(SID, "the ninth")
        self.assertEqual(len(notes), 8, "never more than the bound")
        self.assertEqual(notes[-1]["id"], nid, "the new note is last (newest last)")
        self.assertNotIn("pn-00000000", [n["id"] for n in notes], "the oldest made room")
        self.assertEqual(notes[0]["id"], "pn-00000001")
        self.assertEqual(len(self._file()[SID]), 8, "the file holds the bounded list too")

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
        a, _ = km._pin_note(SID, "first")
        b, _ = km._pin_note(SID, "second")
        acct = km._unpin_note(SID, a)
        self.assertTrue(acct["ok"])
        self.assertEqual([n["id"] for n in acct["notes"]], [b])
        self.assertEqual([n["id"] for n in km._pinned_notes_for(SID)], [b])

    def test_unknown_id_is_refused_loudly_never_a_silent_success(self):
        km._pin_note(SID, "one")
        acct = km._unpin_note(SID, "pn-deadbeef")
        self.assertFalse(acct["ok"])
        self.assertTrue(acct.get("error"))
        self.assertEqual(len(acct["notes"]), 1, "the list still rides the refusal, so the caller can see it")

    def test_a_second_unpin_of_the_same_id_is_refused(self):
        nid, _ = km._pin_note(SID, "one")
        self.assertTrue(km._unpin_note(SID, nid)["ok"])
        self.assertFalse(km._unpin_note(SID, nid)["ok"])

    def test_another_sessions_id_is_refused_and_that_note_stands(self):
        theirs, _ = km._pin_note(SID2, "api: do not merge before the schema lands")
        km._pin_note(SID, "web: mine")
        acct = km._unpin_note(SID, theirs)
        self.assertFalse(acct["ok"], "the store is sid-keyed: a session reaches only its own rows")
        self.assertEqual([n["id"] for n in km._pinned_notes_for(SID2)], [theirs], "the other session's note stands")

    def test_the_last_unpin_drops_the_sessions_key(self):
        nid, _ = km._pin_note(SID, "only one")
        km._unpin_note(SID, nid)
        self.assertNotIn(SID, self._file())
        self.assertEqual(km._pinned_notes_for(SID), [])


class StoreGuards(_StoreSandbox):
    def test_every_store_mutation_runs_under_the_lock(self):
        real_write = km._write_pinned_notes
        seen = []

        def guarded(cur):
            seen.append(km._pinned_notes_lock._is_owned())
            real_write(cur)

        km._write_pinned_notes = guarded
        try:
            nid, _ = km._pin_note(SID, "one")
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


class Routes(_StoreSandbox):
    """POST /pinnote and /unpinnote: the kernel legs the postal tools stand on."""

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
        code, _ = _serve_post("/pinnote", b"not json", {"X-Romp-Token": km.TOKEN})
        self.assertEqual(code, 400)

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
        self.assertFalse(out["ok"], "a loud, plain answer, never a silent success")
        self.assertTrue(out.get("error"))
        _, theirs = self._post("/pinnote", {"id": SID2, "text": "api: theirs"})
        _, out2 = self._post("/unpinnote", {"id": SID, "noteId": theirs["noteId"]})
        self.assertFalse(out2["ok"], "another session's id is not this session's to take down")
        self.assertEqual(len(km._pinned_notes_for(SID2)), 1)

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


class RemoteForward(Routes):
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
        self.assertEqual(res, {"ok": True, "noteId": "pn-0badcafe", "notes": self.answer[1]["notes"]})
        self.assertEqual(self.calls, [("/pinnote", {"id": RSID, "text": "remote note", "detail": "d"})])
        self.assertEqual(km._pinned_notes(), {}, "the owning kernel holds the store")

    def test_unpin_for_a_remote_session_is_forwarded_with_its_account(self):
        self.answer = (200, {"ok": False, "error": "no pinned note of yours with that id", "notes": []})
        code, res = self._post("/unpinnote", {"id": RSID, "noteId": "pn-deadbeef"})
        self.assertEqual(code, 200)
        self.assertEqual(res, {"ok": False, "error": "no pinned note of yours with that id", "notes": []})
        self.assertEqual(self.calls, [("/unpinnote", {"id": RSID, "noteId": "pn-deadbeef"})])

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
        self.assertIn('"unpinNote"', inspect.getsource(km._drive))

    def test_unpin_removes_the_note_quietly(self):
        nid, _ = km._pin_note(SID, "one")
        self.assertTrue(km._drive({"type": "unpinNote", "id": SID, "noteId": nid}, self.client))
        self.assertEqual(km._pinned_notes_for(SID), [])
        self.assertEqual(self.sent, [], "a clean unpin raises no warning")

    def test_unpin_of_a_gone_id_warns_loudly(self):
        km._drive({"type": "unpinNote", "id": SID, "noteId": "pn-deadbeef"}, self.client)
        self.assertEqual([m["type"] for m in self.sent], ["warn"])


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
        a, _ = km._pin_note(SID, "Read docs/plan.md first", "the plan's second section is the current one")
        b, _ = km._pin_note(SID, "Waiting on CI for #12")
        payload = km.build_session(SID, NOW)
        self.assertEqual([n["id"] for n in payload["pinnedNotes"]], [a, b])
        self.assertEqual(payload["pinnedNotes"][0]["detail"], "the plan's second section is the current one")
        self.assertEqual([e for e in payload["events"] if e.get("kind") == "todo"], [],
                         "a pinned note is not a user todo: no split card for it")


if __name__ == "__main__":
    unittest.main()
