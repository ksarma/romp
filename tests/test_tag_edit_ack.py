#!/usr/bin/env python3
"""The tags dialog's write path is acknowledged (the user 2026-09-05, who lost a batch of tag
renames and assignments made in "Manage tags").

Root cause: the dialog posted the WHOLE views blob for every edit, built from its own un-echoed
optimistic copy, so a burst of edits carried the pre-burst `at` stamp. The store's stale-writer
guard (test_views_stale_writer.py) stamps a tag on its first edit and then judges the second edit
to the same tag — a create followed by typing its name — stale against the client's OWN previous
write, refuses it, and tells only stderr and the sync notices; the poster never learned, kept
building from the refused copy, and the dialog snapped to the store ("tag N", no members) once the
user paused.

Two changes at the kernel's door, both pinned here through the real WS dispatcher:
  - `tagEdit` — a TARGETED op (create / rename / recolor / addMember / removeMember / delete, by
    tag NAME) applied through _edit_tag, the read-modify-write merge the /tag route already uses,
    which deep-copies the store and so always carries the newest evidence. Never refused as stale.
  - every views write is ANSWERED on the posting socket: {tagEditAck|viewsAck, writeId, ok,
    views, error?, refused?}. The blob in the ack is the post-write client blob, the poster's new
    base; a refusal names what was refused and why, in plain words.
The whole-blob `setTimelineViews` stays for lens and order edits, with the guard unchanged (its
stderr and sync-notice paths still fire) plus the ack. Frames pushed to other clients are unchanged.
Synthetic sids only."""
import json
import os
import tempfile
import time
import unittest
from importlib.machinery import SourceFileLoader

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")

# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
SourceFileLoader("romp_event_model", os.path.join(BIN, "romp-event-model")).load_module()
SourceFileLoader("romp_judge", os.path.join(BIN, "romp-judge")).load_module()
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "test-token-DO-NOT-USE")
km = SourceFileLoader("romp_kernel_tagack", os.path.join(BIN, "romp-kernel")).load_module()

SID1 = "11111111-2222-3333-4444-555555555501"
SID2 = "11111111-2222-3333-4444-555555555502"
SID3 = "11111111-2222-3333-4444-555555555503"
WEB = {"id": "gA", "name": "web", "color": "#3b82f6", "members": [SID1]}


def store_tag(name):
    return next((t for t in km._timeline_views()["tags"] if t["name"] == name), None)


class _Wire(unittest.TestCase):
    """A dashboard's timeline socket, through the real dispatcher; every ack it receives is kept."""

    def setUp(self):
        try:
            km._views_path().unlink()
        except OSError:
            pass
        self.notices = []
        self._sync = km._sync_notice
        km._sync_notice = lambda text, ok=True: self.notices.append((text, ok))
        self.handler = object.__new__(km.Handler)
        self.sent = []
        self.client = {"app": "timeline", "wid": "w-dash", "alive": True,
                       "send": lambda s: self.sent.append(json.loads(s))}

    def tearDown(self):
        km._sync_notice = self._sync
        try:
            km._views_path().unlink()
        except OSError:
            pass

    def post(self, msg, client=None):
        """Dispatch one client frame; return the reply it produced on that socket (or None)."""
        c = client or self.client
        before = len(self.sent) if c is self.client else None
        km.Handler._dispatch_ws(self.handler, msg, c)
        if before is None:
            return None
        new = self.sent[before:]
        self.assertLessEqual(len(new), 1, "one write, at most one reply")
        return new[0] if new else None

    def seed(self):
        """Tag `web` holding SID1, written through the door so it is stamped (any earlier edit does this)."""
        ack = self.post({"type": "setTimelineViews", "writeId": "w0",
                         "views": {"active": "all", "tags": [dict(WEB)]}})
        self.assertEqual((ack["type"], ack["ok"], ack["refused"]), ("viewsAck", True, []))
        return ack["views"]


class TargetedTagEdits(_Wire):
    """The tagEdit message: {type, writeId, edit: {op, tid?, name?, newName?, color?, sid?|sids?}}.
    Every op but create addresses the tag by its stored id (the 2026-09-05 review, findings 3/5/7/9):
    a create's ack returns the kernel-minted `tid` and `name`; the op rides nested under `edit` so
    the message has no top-level `name` or `session` a federation router could read as an address."""

    def edit(self, write_id, edit, client=None):
        return self.post({"type": "tagEdit", "writeId": write_id, "edit": edit}, client=client)

    def test_the_users_burst_create_then_rename_then_assign_before_any_frame_all_land_and_each_is_acked(self):
        """The exact gesture sequence that was lost, as targeted ops: nothing waits for an echo, and
        the store ends up holding the typed name and the assigned sessions."""
        self.seed()
        a1 = self.edit("w1", {"op": "create", "color": "#1EA1EB"})
        self.assertEqual((a1["type"], a1["writeId"], a1["ok"]), ("tagEditAck", "w1", True))
        tid = a1["tid"]
        self.assertTrue(isinstance(tid, str) and tid.startswith("g"), "the KERNEL mints the id and the ack returns it")
        self.assertEqual(a1["name"], "tag 1", "…and the default name, minted unique in the store")
        self.assertEqual(store_tag("tag 1")["id"], tid)
        a2 = self.edit("w2", {"op": "rename", "tid": tid, "newName": "notes-api"})
        self.assertEqual((a2["writeId"], a2["ok"], a2["tid"], a2["name"]), ("w2", True, tid, "notes-api"))
        self.assertEqual(store_tag("notes-api")["id"], tid, "the rename typed before any echo LANDS")
        self.assertIsNone(store_tag("tag 1"))
        a3 = self.edit("w3", {"op": "addMember", "tid": tid, "sids": [SID2, SID3]})
        self.assertEqual((a3["writeId"], a3["ok"]), ("w3", True))
        self.assertEqual(sorted(m["sid"] for m in store_tag("notes-api")["members"]), sorted([SID2, SID3]),
                         "the assignment lands too — the second half of the report")
        self.assertEqual(self.notices, [], "a targeted edit is never judged stale: it is built from the store")
        # the ack carries the poster's NEW BASE: the rendered client blob, stamped, with the edit in it
        v = a3["views"]
        self.assertTrue(v.get("at"), "the ack blob carries the store's write stamp")
        t = next(x for x in v["tags"] if x["id"] == tid)
        self.assertEqual((t["name"], sorted(t["members"])), ("notes-api", sorted([SID2, SID3])))
        self.assertTrue(t.get("mtime"), "…and the per-tag mtime the guard reads")
        self.assertNotIn("error", a3)

    def test_a_create_is_named_around_a_leftover_default_named_tag(self):
        """The round trip the dialog's own "tag N" from a row count could not make: with a leftover
        "tag 1" (and a "tag 3") in the store, the kernel mints "tag 2", then "tag 4" — never a
        duplicate the create would be refused for."""
        self.seed()
        self.assertTrue(self.edit("w0", {"op": "create", "name": "tag 1", "color": "#000000"})["ok"])
        self.assertTrue(self.edit("w0b", {"op": "create", "name": "tag 3", "color": "#000000"})["ok"])
        a = self.edit("w1", {"op": "create", "color": "#1EA1EB"})
        self.assertEqual((a["ok"], a["name"]), (True, "tag 2"))
        b = self.edit("w2", {"op": "create", "color": "#1EA1EB"})
        self.assertEqual((b["ok"], b["name"]), (True, "tag 4"))
        self.assertNotEqual(a["tid"], b["tid"])
        self.assertEqual(next(t["name"] for t in b["views"]["tags"] if t["id"] == b["tid"]), "tag 4",
                         "the ack's blob carries the new row under the returned tid — the dialog opens its rename input there")
        self.assertEqual(store_tag("tag 2")["id"], a["tid"])

    def test_a_rename_to_an_existing_name_is_refused_and_no_gesture_in_the_refusal_window_reaches_the_other_tag(self):
        """Finding 7: addressed by NAME, a recolor queued behind a refused rename went looking for the
        name the rename would have given the tag — and found the OTHER tag that already had it."""
        self.seed()                                                        # web = gA, #3b82f6
        tid = self.edit("w1", {"op": "create", "name": "api", "color": "#54B204"})["tid"]
        r = self.edit("w2", {"op": "rename", "tid": tid, "newName": "web"})
        self.assertEqual((r["ok"], r["error"], r["tid"]), (False, 'a tag named "web" already exists', tid))
        c = self.edit("w3", {"op": "recolor", "tid": tid, "color": "#DD42FF"})   # the gesture queued behind the rename
        self.assertTrue(c["ok"])
        self.assertEqual(store_tag("api")["color"], "#DD42FF", "lands on the tag the user was editing")
        self.assertEqual(store_tag("web")["color"], "#3b82f6", "the tag that owns the refused name is untouched")
        m = self.edit("w4", {"op": "addMember", "tid": tid, "sids": [SID2]})
        self.assertTrue(m["ok"])
        self.assertEqual([x["sid"] for x in store_tag("web")["members"]], [SID1], "…by every op in the window")

    def test_recolor_remove_member_and_delete(self):
        self.seed()
        self.edit("w1", {"op": "addMember", "tid": "gA", "sid": SID2})
        self.assertEqual(len(store_tag("web")["members"]), 2, "a single `sid` spelling works beside `sids`")
        a = self.edit("w2", {"op": "recolor", "tid": "gA", "color": "#DD42FF"})
        self.assertTrue(a["ok"])
        self.assertEqual(store_tag("web")["color"], "#DD42FF")
        a = self.edit("w3", {"op": "removeMember", "tid": "gA", "sids": [SID1]})
        self.assertTrue(a["ok"])
        self.assertEqual([m["sid"] for m in store_tag("web")["members"]], [SID2])
        a = self.edit("w4", {"op": "delete", "tid": "gA"})
        self.assertEqual((a["ok"], a["views"]["tags"], a["tid"]), (True, [], "gA"))
        self.assertEqual(self.notices, [])

    def test_a_create_with_members_is_one_op_the_join_menus_new_tag_input(self):
        self.seed()
        a = self.edit("w1", {"op": "create", "name": "qa", "color": "#54B204", "sids": [SID2, SID3]})
        self.assertTrue(a["ok"])
        self.assertEqual((a["name"], store_tag("qa")["id"]), ("qa", a["tid"]))
        self.assertEqual(sorted(m["sid"] for m in store_tag("qa")["members"]), sorted([SID2, SID3]))

    def test_a_refused_edit_acks_a_plain_reason_and_changes_nothing(self):
        self.seed()
        api = self.edit("w1", {"op": "create", "name": "api", "color": "#54B204"})["tid"]
        before = json.dumps(km._timeline_views(), sort_keys=True)
        gone = "that tag no longer exists — it may have been deleted from another dashboard"
        cases = [
            ({"op": "rename", "tid": api, "newName": "web"}, 'a tag named "web" already exists'),
            ({"op": "rename", "tid": "gghost", "newName": "x"}, gone),
            ({"op": "create", "name": "web", "color": "#000000"}, 'a tag named "web" already exists'),
            ({"op": "addMember", "tid": "gghost", "sids": [SID2]}, gone),
            ({"op": "addMember", "tid": "gA", "sids": []}, "the edit named no session"),
            ({"op": "addMember", "sids": [SID2]}, "the edit named no tag"),
            ({"op": "recolor", "tid": "gA"}, "no color given"),
            ({"op": "rename", "tid": "gA", "newName": "   "}, "the new name is empty"),
            ({"op": "delete", "tid": "gghost"}, gone),
            ({"op": "explode", "tid": "gA"}, 'unknown tag edit "explode"'),
            (None, "the edit is missing"),
            ("web", "the edit is missing"),
        ]
        for i, (edit, why) in enumerate(cases):
            a = self.edit("r%d" % i, edit)
            self.assertEqual((a["type"], a["writeId"], a["ok"]), ("tagEditAck", "r%d" % i, False), edit)
            self.assertEqual(a["error"], why, edit)
            self.assertIn("views", a, "a refusal still carries the store's blob — the poster's revert base")
            self.assertEqual(json.dumps(km._timeline_views(), sort_keys=True), before, "a refused edit writes nothing")
        # a tag that no longer exists is REFUSED, never resurrected: the dialog's rename of a tag
        # another dashboard deleted must not quietly mint a new one under the old id
        self.assertIsNone(next((t for t in km._timeline_views()["tags"] if t["id"] == "gghost"), None))

    def test_the_message_carries_the_op_nested_under_edit_and_no_top_level_field_is_read(self):
        """The op's fields sit under `edit` so the message has no top-level `name` or `session`
        (federation routes those as a remote lane's address). A stray top-level field is ignored."""
        self.seed()
        a = self.post({"type": "tagEdit", "writeId": "w1", "name": "web", "session": SID2,
                       "edit": {"op": "create", "color": "#000000"}})
        self.assertEqual((a["ok"], a["name"]), (True, "tag 1"), "the create read nothing from the top level")
        self.assertEqual(store_tag("web")["members"], [{"host": "", "sid": SID1}], "…and touched no other tag")

    def test_a_handler_exception_is_acked_as_a_refusal_never_left_unanswered(self):
        """An unanswered write would pin the poster's optimistic copy: the arm acks the failure."""
        self.seed()
        real = km._apply_tag_edit

        def boom(e):
            raise RuntimeError("disk on fire")
        km._apply_tag_edit = boom
        try:
            a = self.edit("w1", {"op": "create", "color": "#000000"})
        finally:
            km._apply_tag_edit = real
        self.assertEqual((a["type"], a["writeId"], a["ok"]), ("tagEditAck", "w1", False))
        self.assertEqual(a["error"], "the edit failed on the kernel: disk on fire")
        self.assertIn("views", a)

    def test_the_ack_answers_the_posting_socket_only(self):
        self.seed()
        other_sent = []
        other = {"app": "timeline", "wid": "w-other", "alive": True, "send": lambda s: other_sent.append(json.loads(s))}
        n = len(self.sent)
        self.edit("w9", {"op": "create", "name": "api", "color": "#54B204"}, client=other)
        self.assertEqual([m["type"] for m in other_sent], ["tagEditAck"])
        self.assertEqual(len(self.sent), n, "no other socket sees the ack — their pushed frames are unchanged")
        # …and a send failure on the poster's socket never escapes the handler (the client is dead, not the kernel)
        def boom(s):
            raise OSError("client gone")
        dead = {"app": "timeline", "wid": "w-dead", "alive": True, "send": boom}
        self.edit("w10", {"op": "create", "name": "qa", "color": "#54B204"}, client=dead)
        self.assertIsNotNone(store_tag("qa"), "the edit landed even though the ack could not be delivered")

    def test_an_edit_without_a_write_id_is_still_acked_with_a_null_id(self):
        self.seed()
        a = self.post({"type": "tagEdit", "edit": {"op": "create", "name": "api", "color": "#54B204"}})
        self.assertEqual((a["ok"], a["writeId"]), (True, None))
        self.assertTrue(store_tag("api")["id"].startswith("g"), "the kernel mints the id, /tag's shape")

    def test_a_move_is_one_write_both_halves_or_neither(self):
        """The tab strip's "Move to <tag>" (the 2026-09-05 review, finding 14): off the home tag,
        onto the target, as ONE write under the lock — a refused destination leaves the source's
        membership exactly as it was, and the store moves its write sequence once per move."""
        self.seed()                                                        # web = gA holding SID1
        api = self.edit("w1", {"op": "create", "name": "api", "color": "#54B204"})["tid"]
        writes, real = [], km._set_timeline_views
        km._set_timeline_views = lambda blob: (writes.append(1), real(blob))[1]
        try:
            a = self.edit("w2", {"op": "move", "tid_from": "gA", "tid_to": api, "sid": SID1})
        finally:
            km._set_timeline_views = real
        self.assertEqual((a["ok"], a["tid"], a["name"]), (True, api, "api"))
        self.assertEqual(store_tag("web")["members"], [], "off the home tag…")
        self.assertEqual([m["sid"] for m in store_tag("api")["members"]], [SID1], "…onto the target")
        self.assertEqual(len(writes), 1, "ONE store write for the move, not one per half")
        # a refused DESTINATION: nothing moves — the source keeps the session
        before = json.dumps(km._timeline_views(), sort_keys=True)
        r = self.edit("w3", {"op": "move", "tid_from": api, "tid_to": "gghost", "sid": SID1})
        self.assertFalse(r["ok"])
        self.assertIn("move into", r["error"])
        self.assertEqual([m["sid"] for m in store_tag("api")["members"]], [SID1], "the source membership is intact")
        self.assertEqual(json.dumps(km._timeline_views(), sort_keys=True), before, "nothing was written")
        # a refused SOURCE, and the two malformed shapes
        r = self.edit("w4", {"op": "move", "tid_from": "gghost", "tid_to": "gA", "sid": SID1})
        self.assertEqual((r["ok"], "move out of" in r["error"]), (False, True))
        self.assertEqual(store_tag("web")["members"], [], "the destination is untouched")
        self.assertEqual(self.edit("w5", {"op": "move", "tid_from": api, "tid_to": "gA"})["error"], "the edit named no session")
        self.assertEqual(self.edit("w6", {"op": "move", "tid_to": "gA", "sid": SID1})["error"], "the edit named no tag")
        self.assertEqual(json.dumps(km._timeline_views(), sort_keys=True), before)
        # a move onto a tag already holding the session, off one that does not: still one clean write
        m = self.edit("w7", {"op": "move", "tid_from": "gA", "tid_to": api, "sids": [SID1]})
        self.assertTrue(m["ok"])
        self.assertEqual([x["sid"] for x in store_tag("api")["members"]], [SID1], "no duplicate member")
        self.assertEqual(self.notices, [], "a move is built from the store — never judged stale")

    def test_the_tag_route_still_addresses_by_name_and_creates_on_first_use(self):
        """_edit_tag's name path is unchanged for `romp tag`: a missing name is created on any
        edit, an existing one is edited, a duplicate name refuses rather than guesses."""
        self.seed()
        t, err = km._edit_tag("qa", add=[SID2])
        self.assertIsNone(err)
        self.assertEqual((t["name"], t["members"]), ("qa", [SID2]))
        t, err = km._edit_tag("qa", color="#DD42FF")
        self.assertEqual((err, t["color"]), (None, "#DD42FF"))


class WholeBlobAcks(_Wire):

    def test_a_clean_whole_blob_write_acks_ok_with_no_refusals(self):
        served = self.seed()
        nv = json.loads(json.dumps(served))
        nv["actives"] = {"timeline": {"tags": ["web"]}}                # a lens edit, built from the echo
        a = self.post({"type": "setTimelineViews", "writeId": "w1", "views": nv})
        self.assertEqual((a["type"], a["writeId"], a["ok"], a["refused"]), ("viewsAck", "w1", True, []))
        self.assertEqual(a["views"]["actives"]["timeline"], {"tags": ["web"]})
        self.assertNotIn("error", a)
        self.assertEqual(self.notices, [])

    def test_a_genuinely_stale_whole_blob_gets_a_refusal_ack_naming_the_tag_and_the_rest_lands(self):
        served = self.seed()
        stale = json.loads(json.dumps(served))                           # this dashboard's copy…
        time.sleep(1.1)                                                  # int-second stamps: land in a later second
        t, err = km._edit_tag("web", add=[SID2])                         # …then another writer adds a member
        self.assertIsNone(err)
        stale["actives"] = {"timeline": {"tags": ["web"]}}               # the stale dashboard changes its lens…
        stale["tags"][0]["members"] = []                                 # …and its copy of web has no members at all
        a = self.post({"type": "setTimelineViews", "writeId": "w2", "views": stale})
        self.assertEqual((a["type"], a["writeId"], a["ok"]), ("viewsAck", "w2", False))
        self.assertEqual([r["name"] for r in a["refused"]], ["web"])
        self.assertIn("predates", a["refused"][0]["reason"])
        self.assertIn('"web"', a["error"], "one plain sentence the dialog can show as-is")
        v = a["views"]
        self.assertEqual(sorted(next(x for x in v["tags"] if x["id"] == "gA")["members"]), sorted([SID1, SID2]),
                         "the store's newer members stand — the guard is unchanged")
        self.assertEqual(v["actives"]["timeline"], {"tags": ["web"]}, "the rest of the write (the lens) landed")
        # the guard's other two witnesses still fire — the ack is an addition, not a replacement
        self.assertEqual(len(self.notices), 1)
        self.assertFalse(self.notices[0][1])
        self.assertIn("stale dashboard write", self.notices[0][0])

    def test_a_refusal_on_a_tag_the_client_did_not_edit_is_ok_with_the_refusal_listed(self):
        """Finding 4: a lens change from a dashboard that had slept through another's tag edit was
        acked as a refusal and toasted — for a tag the user never touched. `edited` names the tag
        ids the write changed; a refusal outside them is a stale copy, not a lost edit."""
        served = self.seed()
        stale = json.loads(json.dumps(served))
        time.sleep(1.1)
        km._edit_tag("web", add=[SID2])                                   # another writer edits web
        stale["actives"] = {"timeline": {"tags": ["web"]}}                # this dashboard changes only its lens…
        stale["tags"][0]["members"] = []                                  # …carrying its stale copy of web
        a = self.post({"type": "setTimelineViews", "writeId": "w1", "views": stale, "edited": []})
        self.assertEqual((a["ok"], [r["tid"] for r in a["refused"]]), (True, ["gA"]),
                         "ok — nothing the user did was refused — with the kept tag listed")
        self.assertNotIn("error", a, "no one-line refusal to show: there is nothing to tell the user")
        self.assertEqual(a["views"]["actives"]["timeline"], {"tags": ["web"]}, "the lens landed")
        self.assertEqual(sorted(next(t for t in a["views"]["tags"] if t["id"] == "gA")["members"]), sorted([SID1, SID2]),
                         "…and the ack's blob carries the newer web the client adopts")
        # the same write naming web as EDITED is a lost edit: refused, with the reason
        b = self.post({"type": "setTimelineViews", "writeId": "w2", "views": stale, "edited": ["gA"]})
        self.assertFalse(b["ok"])
        self.assertIn('"web"', b["error"])
        # no `edited` at all (an older client): the strict reading stands
        c = self.post({"type": "setTimelineViews", "writeId": "w3", "views": stale})
        self.assertFalse(c["ok"])

    def test_the_notice_is_filed_only_when_the_poster_edited_the_kept_tag(self):
        """Round 3 of the 2026-09-05 review: the benign case — a kept tag outside `edited`, acked ok —
        still filed a red "reload that dashboard to resync" notice plus stderr for every kept tag.
        Now the notice follows the ack's verdict: a lost edit is loud; a stale copy of an untouched tag
        is one quiet stderr line and nothing on the dashboard."""
        import contextlib
        import io
        served = self.seed()
        stale = json.loads(json.dumps(served))
        time.sleep(1.1)
        km._edit_tag("web", add=[SID2])
        stale["actives"] = {"timeline": {"tags": ["web"]}}
        stale["tags"][0]["members"] = []
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            a = self.post({"type": "setTimelineViews", "writeId": "w1", "views": stale, "edited": []})
        self.assertEqual((a["ok"], [r["tid"] for r in a["refused"]]), (True, ["gA"]))
        self.assertEqual(self.notices, [], "nothing the user did was refused, so no notice")
        lines = [ln for ln in err.getvalue().splitlines() if ln.strip()]
        self.assertEqual(len(lines), 1, "one quiet stderr line is the whole record")
        self.assertIn('"web"', lines[0])
        self.assertNotIn("reload that dashboard", lines[0])
        # the same write naming web as edited: the lost-edit notice, as before
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            b = self.post({"type": "setTimelineViews", "writeId": "w2", "views": stale, "edited": ["gA"]})
        self.assertFalse(b["ok"])
        self.assertEqual(len(self.notices), 1)
        self.assertFalse(self.notices[0][1])
        self.assertIn('"web"', self.notices[0][0])
        self.assertIn("reload that dashboard", self.notices[0][0])
        # a mixed write — one kept tag edited, one not — names only the edited one on the dashboard
        self.notices.clear()
        self.assertTrue(self.post({"type": "tagEdit", "writeId": "w3", "edit": {"op": "create", "name": "api", "color": "#54B204", "sids": [SID3]}})["ok"])
        stale2 = json.loads(json.dumps(km._views_client()))
        time.sleep(1.1)
        km._edit_tag("web", color="#DD42FF")
        km._edit_tag("api", color="#DD42FF")
        for t in stale2["tags"]:
            t["color"] = "#000000"
        api_tid = next(t["id"] for t in stale2["tags"] if t["name"] == "api")
        with contextlib.redirect_stderr(io.StringIO()):
            c = self.post({"type": "setTimelineViews", "writeId": "w4", "views": stale2, "edited": [api_tid]})
        self.assertFalse(c["ok"])
        self.assertEqual(sorted(r["name"] for r in c["refused"]), ["api", "web"], "both kept; the ack lists both")
        self.assertEqual(len(self.notices), 1)
        self.assertIn('"api"', self.notices[0][0])
        self.assertNotIn('"web"', self.notices[0][0], "the untouched tag is not the user's problem")

    def test_the_refusal_names_the_tag_once_and_says_what_was_kept(self):
        """Finding 15: the reason carried the name and the client prefixed it again."""
        served = self.seed()
        stale = json.loads(json.dumps(served))
        time.sleep(1.1)
        km._edit_tag("web", add=[SID2])
        stale["tags"][0]["members"] = []
        a = self.post({"type": "setTimelineViews", "writeId": "w1", "views": stale, "edited": ["gA"]})
        row = a["refused"][0]
        self.assertNotIn("web", row["reason"], "the reason names no tag — the composer adds the name once")
        self.assertIn("newer state was kept", row["reason"], "…and says what was kept")
        self.assertIn("not applied", row["reason"], "…and what was refused")
        self.assertEqual(a["error"], '"web": %s' % row["reason"])
        self.assertEqual(a["error"].count("web"), 1, "the one-line form names the tag exactly once")
        stale["tags"] = []
        d = self.post({"type": "setTimelineViews", "writeId": "w2", "views": stale, "edited": ["gA"]})
        self.assertEqual(d["error"], '"web": it was edited after your copy was taken, so it was not deleted')

    def test_a_setter_exception_is_acked_as_a_refusal_never_left_unanswered(self):
        self.seed()
        real = km._set_timeline_views

        def boom(blob, **kw):
            raise RuntimeError("disk on fire")
        km._set_timeline_views = boom
        try:
            a = self.post({"type": "setTimelineViews", "writeId": "w1", "views": {"active": "all", "tags": []}})
        finally:
            km._set_timeline_views = real
        self.assertEqual((a["type"], a["ok"], a["error"]), ("viewsAck", False, "the write failed on the kernel: disk on fire"))

    def test_a_stale_deletion_is_named_as_such(self):
        served = self.seed()
        stale = json.loads(json.dumps(served))
        time.sleep(1.1)
        km._edit_tag("web", add=[SID2])
        stale["tags"] = []
        a = self.post({"type": "setTimelineViews", "writeId": "w3", "views": stale})
        self.assertFalse(a["ok"])
        self.assertEqual(len(a["refused"]), 1)
        self.assertEqual(a["refused"][0]["name"], "web")
        self.assertIn("not deleted", a["refused"][0]["reason"])
        self.assertEqual([t["name"] for t in a["views"]["tags"]], ["web"])

    def test_the_dialogs_old_burst_is_what_the_whole_blob_door_refuses(self):
        """The mechanism, pinned so the targeted op's reason for existing stays legible: a rename built
        from the client's un-echoed copy of its own create is refused as stale. (The dialog no longer
        posts this shape for tag edits; this is the door's behavior, and the ack now reports it.)"""
        S0 = self.seed()
        time.sleep(1.1)
        P1 = json.loads(json.dumps(S0))                                  # the pending copy: pre-burst `at`
        P1["tags"].append({"id": "gnew1", "name": "tag 2", "color": "#1EA1EB", "members": []})
        a1 = self.post({"type": "setTimelineViews", "writeId": "p1", "views": P1})
        self.assertTrue(a1["ok"], "a new id is never refused")
        P2 = json.loads(json.dumps(P1))                                  # built from the pending, not the echo
        P2["tags"][1]["name"] = "notes-api"
        a2 = self.post({"type": "setTimelineViews", "writeId": "p2", "views": P2})
        self.assertEqual((a2["ok"], [r["name"] for r in a2["refused"]]), (False, ["tag 2"]),
                         "judged stale against the client's OWN previous write — the reported loss")
        self.assertEqual(store_tag("tag 2")["name"], "tag 2")


class WriteSequence(_Wire):
    """The store's WRITE SEQUENCE (the 2026-09-05 review, findings 1/8/19): every accepted write
    moves `seq` forward, the blob carries it, so every frame that embeds the blob (the timeline
    skeleton, the feed frame, the tabOrder frames — all built from _views_client) and every ack
    carries the same number. A client adopts a blob only when its seq is at least the one it
    holds, so the order the socket delivered frames and acks in decides nothing: the pusher's
    warmed cache can predate a write whose ack already arrived, and the exact-echo heuristic could
    not tell that frame from the write's own echo."""

    def test_every_accepted_write_moves_the_seq_forward_and_a_refusal_does_not(self):
        served = self.seed()
        s0 = served.get("seq")
        self.assertIsInstance(s0, int, "the served blob carries the stamp")
        _, err = km._edit_tag("web", add=[SID2])                            # a targeted (RMW) write
        self.assertIsNone(err)
        s1 = km._timeline_views()["seq"]
        self.assertGreater(s1, s0, "a targeted write moves it")
        nv = json.loads(json.dumps(km._views_client()))
        nv["actives"] = {"timeline": {"tags": ["web"]}}
        a = self.post({"type": "setTimelineViews", "writeId": "w2", "views": nv})
        self.assertTrue(a["ok"])
        self.assertGreater(a["seq"], s1, "a whole-blob write moves it, and the ack returns the seq the write produced")
        self.assertEqual(a["seq"], a["views"]["seq"], "the ack's seq IS the blob's")
        self.assertEqual(a["seq"], km._timeline_views()["seq"])
        _, err = km._edit_tag("ghost", rename="x", exists=True)              # refused: no write
        self.assertTrue(err)
        self.assertEqual(km._timeline_views()["seq"], a["seq"], "a refused edit writes nothing, so it moves nothing")
        # a PARTIALLY refused whole-blob write still lands the rest of the write — so it moves
        stale = json.loads(json.dumps(served))
        time.sleep(1.1)
        km._edit_tag("web", color="#DD42FF")
        s2 = km._timeline_views()["seq"]
        stale["tags"][0]["members"] = []
        stale["actives"] = {"chat": {"tags": ["web"]}}
        b = self.post({"type": "setTimelineViews", "writeId": "w3", "views": stale})
        self.assertEqual([r["name"] for r in b["refused"]], ["web"])
        self.assertGreater(b["seq"], s2, "the lens landed, so the store moved")
        self.assertEqual(b["views"]["seq"], b["seq"])

    def test_the_seq_rides_every_frame_that_carries_the_blob_and_survives_the_normalizer(self):
        served = self.seed()
        self.assertEqual(km._views_client()["seq"], served["seq"],
                         "the rendered client blob every frame embeds carries it")
        self.assertEqual(km._norm_timeline_views(json.loads(json.dumps(served)))["seq"], served["seq"],
                         "clients echo the blob wholesale — the stamp survives the round trip")
        src = open(os.path.join(BIN, "romp-kernel")).read()
        self.assertGreaterEqual(src.count('"views": _views_client()'), 3,
                                "the timeline skeleton, the feed frame and the tabOrder frames all embed the "
                                "rendered blob — one carrier, so the seq rides every one of them")

    def test_a_store_recreated_from_nothing_starts_past_what_a_connected_client_holds(self):
        """The seq is seeded from the clock, then +1 per write: a deleted views file (or a new
        state dir) must not restart at 1 — a dashboard holding the old store's seq would then
        ignore every frame until it reloaded."""
        s0 = self.seed()["seq"]
        km._views_path().unlink()
        time.sleep(0.002)
        a = self.post({"type": "setTimelineViews", "writeId": "w9", "views": {"active": "all", "tags": []}})
        self.assertGreater(a["seq"], s0)
        b = self.post({"type": "setTimelineViews", "writeId": "w10", "views": a["views"]})
        self.assertGreater(b["seq"], a["seq"], "…and strictly increasing within a store, same-ms writes included")


class Capability(_Wire):
    """The kernel says what it can do (the 2026-09-05 review, findings 2/12): {type: "caps"} in
    reply to every `ready`, after the pushes; the same list on /version. A message no handler took
    is logged once per type and answered {type: "unknownOp", op, writeId?} on the poster's socket,
    so a client waiting on an ack learns the op is unsupported instead of pinning its copy."""

    def setUp(self):
        super().setUp()
        km._UNKNOWN_OPS_SEEN.clear()

    def test_ready_is_answered_with_the_caps_frame_after_the_pushes(self):
        self.handler._push_one = lambda c: self.sent.append({"type": "_pushed"})   # the connect push, in order
        self.client["ready"] = False                                                # held at accept (READY_GATE_CAP)
        km.Handler._dispatch_ws(self.handler, {"type": "ready"}, self.client)
        self.assertTrue(self.client["ready"])
        types = [m["type"] for m in self.sent]
        self.assertIn("caps", types)
        self.assertLess(types.index("_pushed"), types.index("caps"),
                        "after the pushes: the shim's stale banner clears on the first real frame after a "
                        "reconnect, which must stay the resync frame itself")
        caps = next(m for m in self.sent if m["type"] == "caps")
        self.assertEqual(caps, {"type": "caps", "caps": ["tagEdit"]})
        # a RE-SENT ready (the shim, on a reconnected socket) gets the caps again — the event a page
        # with writes in flight across the drop keys on
        n = len(self.sent)
        km.Handler._dispatch_ws(self.handler, {"type": "ready"}, self.client)
        self.assertEqual([m["type"] for m in self.sent[n:] if m["type"] == "caps"], ["caps"])

    def test_version_lists_the_same_caps(self):
        self.assertEqual(km._version_info()["caps"], list(km.KERNEL_WS_CAPS))
        self.assertIn("tagEdit", km.KERNEL_WS_CAPS)

    def test_an_unknown_op_is_answered_every_time_and_logged_once_per_type(self):
        import contextlib
        import io
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            a = self.post({"type": "noSuchOp", "writeId": "w1"})
            b = self.post({"type": "noSuchOp", "writeId": "w2"})
            c = self.post({"type": "noSuchOp"})
        self.assertEqual(a, {"type": "unknownOp", "op": "noSuchOp", "writeId": "w1"},
                         "the poster learns the op is unsupported — a client waiting on that writeId treats it as a refusal")
        self.assertEqual(b, {"type": "unknownOp", "op": "noSuchOp", "writeId": "w2"})
        self.assertEqual(c, {"type": "unknownOp", "op": "noSuchOp"}, "no writeId → none echoed")
        lines = [ln for ln in err.getvalue().splitlines() if "noSuchOp" in ln]
        self.assertEqual(len(lines), 1, "one line of version skew per type, not one per gesture")
        self.assertIn("unknownOp", lines[0])
        # a KNOWN op missing the field its arm requires falls to the same terminal arm
        with contextlib.redirect_stderr(io.StringIO()):
            d = self.post({"type": "setSessionFlag", "id": "", "flag": "eye"})
        self.assertEqual(d["type"], "unknownOp")
        self.assertEqual(d["op"], "setSessionFlag")

    def test_a_host_directed_op_and_an_undecodable_frame_are_neither_logged_nor_answered(self):
        import contextlib
        import io
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertIsNone(self.post({"type": "openLink", "href": "https://example.invalid/x"}),
                              "the browser shim has no host to consume it; it is not the kernel's to answer")
            self.assertIsNone(self.post({"type": "readClipboard"}))
            self.assertIsNone(self.post(None), "an undecodable frame was already reported by the recv loop")
            self.assertIsNone(self.post({"type": ""}))
        self.assertEqual(err.getvalue(), "")

    def test_the_inline_boot_routes_caps_and_unknown_op_to_the_panel(self):
        src = open(os.path.join(BIN, "romp-kernel")).read()
        self.assertIn('else if(m.type==="caps"&&panel.setCaps)panel.setCaps(m);', src)
        self.assertIn('else if(m.type==="unknownOp"&&panel.unknownOp)panel.unknownOp(m);', src)


class SetterReturnsRefusals(unittest.TestCase):
    """_set_timeline_views now RETURNS the refused rows (tid + name + plain reason); callers that
    ignored None keep ignoring a list."""

    def setUp(self):
        try:
            km._views_path().unlink()
        except OSError:
            pass
        self._sync = km._sync_notice
        km._sync_notice = lambda text, ok=True: None

    def tearDown(self):
        km._sync_notice = self._sync
        try:
            km._views_path().unlink()
        except OSError:
            pass

    def test_clean_writes_return_an_empty_list_and_stale_ones_the_rows(self):
        self.assertEqual(km._set_timeline_views({"active": "all", "tags": [dict(WEB)]}), [])
        stale = json.loads(json.dumps(km._timeline_views()))
        time.sleep(1.1)
        km._edit_tag("web", add=[SID2])
        stale["tags"][0]["members"] = []
        rows = km._set_timeline_views(stale)
        self.assertEqual([sorted(r.keys()) for r in rows], [["name", "reason", "tid"]])
        self.assertEqual((rows[0]["tid"], rows[0]["name"]), ("gA", "web"))


class ReadCacheAfterWrite(_Wire):
    """The views read cache is keyed on the file's (mtime_ns, size) and was never touched by a write
    (round 3 of the 2026-09-05 review). The kernel's file mtime clock is coarse (a few ms), so two
    same-size writes in one tick shared a key, and the second write's ack — built by reading the store
    — could serve the FIRST write's blob. Now the write itself refreshes the cache entry with the blob
    it wrote. This harness runs with the production cache (no clears): every ack in this file is
    served through it."""

    def test_the_cache_holds_the_blob_just_written_and_a_shared_stat_key_cannot_serve_the_older_one(self):
        self.seed()                                                          # web = #3b82f6
        p = km._views_path()
        st1 = p.stat()
        first = km._timeline_views()
        self.assertIs(km._flags_cache[str(p)][1], first, "the read warmed the cache")
        # a same-size write (a 7-char colour for a 7-char colour): the file's size does not change
        _, err = km._edit_tag("web", color="#54B204")
        self.assertIsNone(err)
        self.assertEqual(km._flags_cache[str(p)][1]["tags"][0]["color"], "#54B204",
                         "the write replaced the cache entry with what it wrote — no read needed")
        self.assertEqual(p.stat().st_size, st1.st_size, "(the write is the same size: the key's other half cannot tell them apart)")
        # the coarse-clock case, forced: give the second write the first's mtime, so the stat key is
        # exactly the one the first read was cached under
        os.utime(p, ns=(st1.st_mtime_ns, st1.st_mtime_ns))
        self.assertEqual(km._timeline_views()["tags"][0]["color"], "#54B204",
                         "the next read serves the newer write — never the older blob under a shared key")

    def test_a_targeted_edits_ack_is_fresh_through_the_production_cache(self):
        self.seed()
        a = self.post({"type": "tagEdit", "writeId": "w1", "edit": {"op": "recolor", "tid": "gA", "color": "#54B204"}})
        self.assertTrue(a["ok"])
        self.assertEqual(next(t for t in a["views"]["tags"] if t["id"] == "gA")["color"], "#54B204",
                         "the ack's blob is the post-write store, read through the cache the write refreshed")
        b = self.post({"type": "tagEdit", "writeId": "w2", "edit": {"op": "recolor", "tid": "gA", "color": "#DD42FF"}})
        self.assertEqual(next(t for t in b["views"]["tags"] if t["id"] == "gA")["color"], "#DD42FF")
        self.assertGreater(b["seq"], a["seq"])


class LegacyStoreStampedOnce(_Wire):
    """A store from before the write sequence (every install upgrading, round 3 of the 2026-09-05
    review): served seq-less, it left every client on the null rule — adopt anything — until the
    first write, so the seq gate could not protect that first write against a frame the pusher built
    before it. The first READ stamps it once, through the setter (one write); after that the file is
    left alone. A store that does not exist is NOT created: the null rule is right for a deleted or
    recreated store, whose first write starts past what any client holds."""

    def _writes(self):
        n = [0]
        real = km._atomic_write

        def counting(path, text, mode=None):
            n[0] += 1
            return real(path, text, mode)
        km._atomic_write = counting
        return n, lambda: setattr(km, "_atomic_write", real)

    def test_a_seq_less_file_is_stamped_on_its_first_read_and_only_then(self):
        p = km._views_path()
        legacy = {"active": "all", "tags": [{"id": "gL", "name": "legacy", "color": "#3b82f6",
                                              "members": [{"host": "", "sid": SID1}]}]}
        p.write_text(json.dumps(legacy))
        n, restore = self._writes()
        try:
            v = km._timeline_views()
            self.assertEqual(n[0], 1, "exactly one write: the stamp")
            self.assertIsInstance(v.get("seq"), int, "the served blob carries a seq from its first read")
            self.assertTrue(v["seq"] > 0)
            on_disk = json.loads(p.read_text())
            self.assertEqual(on_disk["seq"], v["seq"], "…and the file does too")
            self.assertEqual(on_disk["tags"][0]["members"], [{"host": "", "sid": SID1}], "nothing else changed")
            self.assertNotIn("mtime", on_disk["tags"][0], "an unchanged tag gets no edit stamp from the migration")
            self.assertEqual(self.notices, [], "a stamp is not a refusal: nothing is said")
            before = p.read_bytes()
            km._flags_cache.clear()                      # a cold cache (a restart): the stamped file is fine as-is
            v2 = km._timeline_views()
            self.assertEqual(n[0], 1, "the second read writes nothing")
            self.assertEqual(p.read_bytes(), before, "byte-identical")
            self.assertEqual(v2["seq"], v["seq"])
            self.assertEqual(km._views_client()["seq"], v["seq"], "every frame now carries it — the gate protects the first write")
            # …and that first write orders after it
            a = self.post({"type": "setTimelineViews", "writeId": "w1", "views": km._views_client()})
            self.assertGreater(a["seq"], v["seq"])
        finally:
            restore()

    def test_a_missing_store_is_served_seq_less_and_not_created(self):
        n, restore = self._writes()
        try:
            v = km._timeline_views()
            self.assertNotIn("seq", v, "no file → the null rule: a client adopts whatever the first write brings")
            self.assertEqual(n[0], 0)
            self.assertFalse(km._views_path().exists(), "reading does not create the store")
        finally:
            restore()

    def test_an_unreadable_file_is_served_empty_and_never_overwritten(self):
        p = km._views_path()
        p.write_text("{not json")
        n, restore = self._writes()
        try:
            self.assertEqual(km._timeline_views()["tags"], [])
            self.assertEqual(n[0], 0, "a corrupt file is left for a human — the stamp never replaces it with an empty store")
            self.assertEqual(p.read_text(), "{not json")
        finally:
            restore()


class ForeignWriteReStamped(_Wire):
    """A write to timeline-views.json OUTSIDE the kernel (round 3 of the 2026-09-05 review): the
    timeline's Electron branch writes the file itself with the seq it holds, so a panel holding an
    older frame publishes a seq lower than what every dashboard holds, and they all ignore the file
    until the next kernel write. The reader treats a changed file whose seq fell behind the last one
    served as such a write and re-stamps it through the setter: seq = max(last + 1, now), the content
    kept as written. A changed file whose seq is not behind is served as-is."""

    def test_a_file_whose_seq_fell_behind_is_re_stamped_past_the_last_served_seq(self):
        served = self.seed()
        s1 = served["seq"]
        self.assertEqual(km._timeline_views()["seq"], s1, "served: the cache holds it")
        p = km._views_path()
        # the panel's write: its held (older) blob with a lens change, seq behind the store's
        foreign = json.loads(p.read_text())
        foreign["seq"] = s1 - 5
        foreign["actives"] = {"timeline": {"tags": ["web"]}, "chat": {"all": True}, "outline": {"all": True}}
        time.sleep(0.01)                                  # a new mtime, so the file changes under the cache
        km._atomic_write(p, json.dumps(foreign))
        v = km._timeline_views()
        self.assertGreater(v["seq"], s1, "re-stamped past the last served seq — every dashboard adopts it")
        self.assertEqual(v["actives"]["timeline"], {"tags": ["web"]}, "the content is kept as written")
        on_disk = json.loads(p.read_text())
        self.assertEqual(on_disk["seq"], v["seq"], "…and the file carries the new seq: the next kernel read is a plain hit")
        self.assertEqual(self.notices, [], "ordering a file is not a refusal")
        self.assertEqual(km._views_client()["seq"], v["seq"])
        # a kernel write after it orders after the re-stamp
        a = self.post({"type": "tagEdit", "writeId": "w1", "edit": {"op": "recolor", "tid": "gA", "color": "#54B204"}})
        self.assertGreater(a["seq"], v["seq"])

    def test_a_changed_file_whose_seq_is_not_behind_is_served_as_is(self):
        served = self.seed()
        s1 = served["seq"]
        km._timeline_views()
        p = km._views_path()
        foreign = json.loads(p.read_text())                # a panel holding the NEWEST frame writes it back
        foreign["actives"] = {"timeline": {"tags": ["web"]}, "chat": {"all": True}, "outline": {"all": True}}
        time.sleep(0.01)
        km._atomic_write(p, json.dumps(foreign))
        before = p.read_bytes()
        v = km._timeline_views()
        self.assertEqual(v["seq"], s1, "an equal seq is not behind: no write")
        self.assertEqual(p.read_bytes(), before, "byte-identical")
        self.assertEqual(v["actives"]["timeline"], {"tags": ["web"]})
        ahead = json.loads(p.read_text()); ahead["seq"] = s1 + 100
        time.sleep(0.01)
        km._atomic_write(p, json.dumps(ahead))
        self.assertEqual(km._timeline_views()["seq"], s1 + 100, "a seq ahead of the last served is adopted as the new floor")


class WebBootWiring(unittest.TestCase):
    """The kernel-served timeline page: the inline _TIMELINE_BOOT twin of timeline-boot.ts exposes
    the targeted-edit bridge and routes both acks to the panel (timeline-boot.test.ts pins the two
    bridge sets equal)."""

    def test_the_bridge_and_the_ack_dispatch(self):
        src = open(os.path.join(BIN, "romp-kernel")).read()
        self.assertIn('window.__rompTimelineTagEdit=function(writeId,edit){post({type:"tagEdit",writeId:writeId,edit:edit});};', src)
        self.assertIn('window.__rompTimelineSetViews=function(views,writeId,edited){post({type:"setTimelineViews",views:views,writeId:writeId,edited:edited||[]});};', src)
        self.assertIn('else if((m.type==="tagEditAck"||m.type==="viewsAck")&&panel.viewsAck)panel.viewsAck(m);', src)


if __name__ == "__main__":
    raise SystemExit("run under pytest: ~/.venvs/romptest/bin/python -m pytest %s -q -p no:cacheprovider" % __file__)
