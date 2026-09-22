#!/usr/bin/env python3
"""A user todo's presence rides the tab roster (the user 2026-09-22): a tab a chat client holds as a skeleton or a
placeholder shows its flag before its session payload is served.

Two upstream mechanisms folded after the tab's flag was built withhold a tab's session payload from a client that has
not opened it: the skeleton diet (a status frame instead of the chat, for a dial with skeleton=1 or reconnect=1) and
the cold-tab gate (the tab is not built at all). The flag, the folded group's flag and the snapshot row's count all
read build_session's userTodos rows, which only that payload and its chatTails carry, so a skeleton tab drew no flag
until a click or the idle prefetch released it, and a todo filed while it was a skeleton produced no frame for that
client at all. The fix puts the COUNT of a session's open user todos on every row of the tabOrder frame's `tabs` list
(`userTodos`), built by _tab_meta once per push for every strip sender: a todo's presence is strip metadata beside the
name, the colour and the emoji; its text stays session content that loads with the tab.

Drives the real _push, _push_session_now and _confirm_close_now over the cold-tab fixture (tests/test_cold_tab_gate.py:
four listed tabs, build_session stubbed and counted, a private state root per test; the roster's count is read from the
store, never from a build). Synthetic only: the fixture's own invented sids under a per-test private state root,
invented todo text, hostname TESTHOST, never the shared placeholder sid and never a real session."""
import inspect
import os
import tempfile
import time
import unittest
from unittest import mock
from romp_load import load_source  # noqa: F401  a direct run's floor (tests/romp_load.py); the kernel is the fixture module's

# Hermetic state BEFORE the loads (the fixture module loads the kernel at import): only pytest runs conftest's floor
# (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
from tests.test_cold_tab_gate import _ColdTabFixture, km, S1, S2, S3, S4, TAB_ORDER  # noqa: E402

MOON = "\U0001F319"                      # an emoji for a names record: the roster carries it beside the count


def _row(c, sid):
    """The row for `sid` on the LAST strip client `c` received, checked for the count's key first, so a row without it
    fails on the property (every tabs row carries `userTodos`, 0 included) and not on a KeyError in the caller."""
    strips = [f for f in c["_frames"] if f["type"] == "tabOrder"]
    row = {t["id"]: t for t in strips[-1]["tabs"]}[sid]
    if "userTodos" not in row:
        raise AssertionError("every tabs row carries the count, 0 included: the row for the tab at position %d has keys %s"
                             % (TAB_ORDER.index(sid), sorted(row)))
    return row


def _count(row):
    """A helper row's count (the rows _tab_meta returns), checked for the key first, as _row checks a client's strip row."""
    if "userTodos" not in row:
        raise AssertionError("every helper row carries the count, 0 included: the row has keys %s" % sorted(row))
    return row["userTodos"]


class UserTodosRoster(_ColdTabFixture):
    """The four tests the fix brief marks red before the change, over the real _push, then the requirements its
    critic added: one predicate and one gate for every surface, one switch read and one store read per push, no roster
    for a push with no chat client."""

    def setUp(self):
        super().setUp()
        (km.jd.STATE / "session-hosts").write_text("off")     # a minted state root pins the hosts off (the 2026-09-11 rule)
        self.assertIsNotNone(km._set_user_todos(True), "premise: the switch turns on under the private root")

    def _skeleton_client(self):
        c = self._client(reconnect=True, active=S1)            # the restart reload's dial: the diet, and the tab on screen
        km._clients[:] = [c]
        return c

    # ── the brief's four, red before the change ──
    def test_a_skeleton_client_learns_the_count_of_a_tab_it_never_opened(self):
        km._add_user_todo(S3, "Need the auth-scheme decision")
        c = self._skeleton_client()
        km._push([c])
        self.assertNotIn(S3, self.built, "S3 is a skeleton on a cold kernel: not built")
        self.assertNotIn(("chat", S3), c["sent"], "no chat frame for S3")
        self.assertEqual([f["id"] for f in self._frames(c, "session") if f["id"] == S3], [], "no session frame for S3")
        self.assertIn(S3, self._frames(c, "tabOrder")[-1]["skeleton"], "premise: the page holds S3 as a skeleton")
        self.assertEqual(_row(c, S3)["userTodos"], 1, "the roster row carries the count of S3's open todos")

    def test_a_todo_filed_while_the_tab_is_a_skeleton_ships_a_new_strip_and_no_chat(self):
        t1 = km._add_user_todo(S3, "Need the auth-scheme decision")
        c = self._skeleton_client()
        km._push([c])
        n0 = len(self._frames(c, "tabOrder"))
        t2 = km._add_user_todo(S3, "Need the staging port")    # filed while S3 is a skeleton (the /usertodo route ends in
        km._push([c])                                          #  _push_soon; the cycle that wake produces is run by hand)
        self.assertEqual(len(self._frames(c, "tabOrder")), n0 + 1, "a NEW strip: the count changed, so the per-client dedup let it through")
        self.assertEqual(_row(c, S3)["userTodos"], 2)
        self.assertNotIn(S3, self.built, "still a skeleton: not built")
        self.assertNotIn(("chat", S3), c["sent"], "...and no chat for it")
        km._resolve_user_todo(S3, t1, "dismissed")
        km._resolve_user_todo(S3, t2, "withdrawn")
        km._push([c])
        self.assertEqual(len(self._frames(c, "tabOrder")), n0 + 2, "resolving both ships a strip too")
        self.assertEqual(_row(c, S3)["userTodos"], 0, "an empty count is a real value, not an absent key")

    def test_the_roster_applies_build_sessions_gates(self):
        km._add_user_todo(S3, "Need the auth-scheme decision")
        gone = km.jd.STATE / "gone"
        gone.mkdir(exist_ok=True)
        (gone / (S3 + ".json")).write_text('{"t": %d}' % int(time.time()))   # the corroborated death record, no newer states row
        self.assertTrue(km._user_todo_session_ended(S3), "premise: the gate reads S3 as ended")
        self.assertEqual(len(km._open_user_todos(S3)), 1, "premise: the store still holds the row (hidden, not cleared)")
        c = self._skeleton_client()
        km._push([c])
        self.assertEqual(_row(c, S3)["userTodos"], 0, "an ended session's todos are hidden from the roster as from every surface")
        (gone / (S3 + ".json")).unlink()
        self.assertIsNotNone(km._set_user_todos(False), "premise: the switch turns off")
        c2 = self._skeleton_client()
        km._push([c2])
        self.assertEqual(_row(c2, S3)["userTodos"], 0, "the switch off: no count, as no rows")

    def test_a_fresh_client_gets_the_count_and_todays_top_level_keys(self):
        km._add_user_todo(S3, "Need the auth-scheme decision")
        c = self._client(active=S1)                            # no reconnect, no skeleton term: a fresh page
        km._clients[:] = [c]
        km._push([c])
        to = self._frames(c, "tabOrder")
        self.assertEqual(len(to), 1)
        self.assertEqual(set(to[0]), {"type", "order", "tabs", "views", "live", "selfHost"},
                         "today's frame, key for key: the count rides the rows, not a new top-level key")
        self.assertEqual(sorted(self.built), sorted(TAB_ORDER), "a page that declared no diet is served whole, as today")
        self.assertEqual({sid: _row(c, sid)["userTodos"] for sid in TAB_ORDER}, {S1: 0, S2: 0, S3: 1, S4: 0},
                         "every listed row carries the count, 0 included")
        self.assertEqual(sorted(_row(c, S3)), ["color", "emoji", "id", "name", "userTodos"],
                         "the row: today's four keys and the count")

    # ── the critic's requirements ──
    def test_every_strip_sender_carries_the_count_beside_the_names_fields(self):
        # the three senders (_push above; the per-session push and the close confirmation here) hand the same rows: the
        # count beside the name, the colour and the emoji from the names record. tests/test_kernel_tabs_first.py and
        # tests/test_session_emoji.py hold the source census over the senders and point here for the behaviour.
        (km.NAMES / S3).write_text("tests\t/proj/TESTHOST/app\t#1EA1EB\twhite\t" + MOON + "\n")
        km._add_user_todo(S3, "Need the auth-scheme decision")
        c = self._skeleton_client()
        km._push([c])
        del c["_frames"][:]
        c["sent"].pop(("taborder",), None)                     # forget the strip, so each sender's own is observed
        km._push_session_now(S2)
        row = _row(c, S3)
        self.assertEqual((row["userTodos"], row["emoji"], row["color"], row["name"]),
                         (1, MOON, {"bg": "#1EA1EB", "fg": "#ffffff"}, "tests"), "the per-session push's row")
        del c["_frames"][:]
        c["sent"].pop(("taborder",), None)
        km._confirm_close_now(S4)                              # the stub still lists S4: the confirmation reads False, the strip goes
        row = _row(c, S3)
        self.assertEqual((row["userTodos"], row["emoji"], row["color"], row["name"]),
                         (1, MOON, {"bg": "#1EA1EB", "fg": "#ffffff"}, "tests"), "the close confirmation's row")

    def test_the_roster_and_the_rows_agree_on_what_is_open_through_one_predicate(self):
        # by execution: four row shapes in the store, and the roster's count equals the rows _open_user_todos ships
        # (the two-inputs-one-glyph risk: a loaded tab reads rows, a skeleton tab reads the count)
        km._write_user_todos({S3: [{"id": "ut-00000001", "text": "Need the auth-scheme decision", "createdT": 1},
                                   {"id": "ut-00000002", "text": "Need the staging port", "createdT": 2,
                                    "resolved": {"kind": "dismissed", "t": 3}},
                                   {"text": "a row with no id", "createdT": 4},
                                   "not a record"]})
        rows = km._open_user_todos(S3)
        self.assertEqual([t["id"] for t in rows], ["ut-00000001"], "premise: one open row of the four")
        counts = {r["id"]: _count(r) for r in km._tab_meta(km._chat_tab_sessions(0, {}))}
        self.assertEqual(counts[S3], len(rows), "the count is the rows' length, whatever the store holds")
        self.assertEqual([counts[s] for s in (S1, S2, S4)], [0, 0, 0])
        # by source: the predicate is ONE (_user_todo_open) and the ended gate is ONE (_user_todos_shown); the helper,
        # the rows and the boot notice ask them and re-spell neither
        meta = inspect.getsource(km._tab_meta)
        self.assertIn("_user_todo_open(", meta)
        self.assertIn("_user_todos_shown(", meta)
        self.assertNotIn('"resolved"', meta, "the helper does not re-spell the open row")
        self.assertNotIn("_user_todo_session_ended", meta, "...nor the ended gate")
        # every reader of "is this row open" outside the store's mutators (the predicate's docstring names those): the rows,
        # the boot notice and the answer-lost verdict, whose "open" is the same claim. The check keys on the stamp read,
        # `.get("resolved")`, whatever the row variable is called.
        for fn in (km._open_user_todos, km._user_todos_off_boot_notice, km._user_todo_answer_lost):
            self.assertIn("_user_todo_open(", inspect.getsource(fn), "%s asks the one predicate" % fn.__name__)
            self.assertNotIn('.get("resolved")', inspect.getsource(fn),
                             "%s re-spells no open row: the stamp read belongs to the predicate" % fn.__name__)
        real_build = self._saved[3]                    # the fixture stubs build_session for the pushes: the saved original is the source
        for fn, arg in ((real_build, "sid"), (km._feed_session_key, "fsid")):
            src = inspect.getsource(fn)
            self.assertIn("not _user_todos_shown(%s)" % arg, src, "%s asks the one gate" % fn.__name__)
            self.assertNotIn("_user_todo_session_ended(", src, "%s re-spells no ended gate" % fn.__name__)
        self.assertIn("return not _user_todo_session_ended(sid)", inspect.getsource(km._user_todos_shown),
                      "the gate is the corroborated ended read, negated: hidden, not cleared")

    def test_the_helper_reads_the_switch_and_the_store_once_and_gates_only_a_nonzero_count(self):
        km._add_user_todo(S3, "Need the auth-scheme decision")
        calls = {"on": 0, "store": 0, "shown": []}
        real_on, real_store, real_shown = km._user_todos_on, km._user_todos, km._user_todos_shown

        def on():
            calls["on"] += 1
            return real_on()

        def store():
            calls["store"] += 1
            return real_store()

        def shown(sid):
            calls["shown"].append(sid)
            return real_shown(sid)
        with mock.patch.object(km, "_user_todos_on", on), mock.patch.object(km, "_user_todos", store), \
                mock.patch.object(km, "_user_todos_shown", shown):
            rows = km._tab_meta(km._chat_tab_sessions(0, {}))
        self.assertEqual(len(rows), len(TAB_ORDER))
        self.assertEqual((calls["on"], calls["store"]), (1, 1),
                         "one switch read and one store read for %d listed tabs (the switch file is read on every _user_todos_on call)" % len(TAB_ORDER))
        self.assertEqual(calls["shown"], [S3], "the ended gate runs for the sid with open rows alone")
        calls["on"] = 0
        calls["store"] = 0
        self.assertIsNotNone(km._set_user_todos(False))
        with mock.patch.object(km, "_user_todos_on", on), mock.patch.object(km, "_user_todos", store):
            rows = km._tab_meta(km._chat_tab_sessions(0, {}))
        self.assertEqual([_count(r) for r in rows], [0] * len(TAB_ORDER))
        self.assertEqual((calls["on"], calls["store"]), (1, 0), "the switch off: no store read at all")

    def test_a_push_with_no_chat_client_builds_no_roster(self):
        calls = []
        real = km._tab_meta

        def meta(chat_list):
            calls.append(len(chat_list))
            return real(chat_list)
        with mock.patch.object(km, "_tab_meta", meta):
            pane = self._client(app="fleet")                   # the Outline pane's existing app id on the wire
            km._clients[:] = [pane]
            km._push([pane])
            self.assertEqual(calls, [], "an Outline pane alone: the strip goes to chat clients only, so no roster is built")
            c = self._client(active=S1)
            km._clients[:] = [pane, c]
            km._push([pane, c])
            self.assertEqual(calls, [len(TAB_ORDER)], "a chat client among the targets: the roster is built once for the push")


if __name__ == "__main__":
    unittest.main()
