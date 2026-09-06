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
        ids the write changed; a refusal outside them is a stale copy, not a lost edit. Round 5: a
        lens write (`edited` empty) changes no tag at all, so its stale copy is not even judged —
        the ack is clean and its blob carries the store's web; a write naming ANOTHER tag as edited
        still lists the untouched tag's kept copy."""
        served = self.seed()
        stale = json.loads(json.dumps(served))
        time.sleep(1.1)
        km._edit_tag("web", add=[SID2])                                   # another writer edits web
        stale["actives"] = {"timeline": {"tags": ["web"]}}                # this dashboard changes only its lens…
        stale["tags"][0]["members"] = []                                  # …carrying its stale copy of web
        a = self.post({"type": "setTimelineViews", "writeId": "w1", "views": stale, "edited": []})
        self.assertEqual((a["ok"], a["refused"]), (True, []),
                         "ok, nothing listed: a lens write changes no tag, so there is nothing to refuse")
        self.assertNotIn("error", a, "no one-line refusal to show: there is nothing to tell the user")
        self.assertEqual(a["views"]["actives"]["timeline"], {"tags": ["web"]}, "the lens landed")
        self.assertEqual(sorted(next(t for t in a["views"]["tags"] if t["id"] == "gA")["members"]), sorted([SID1, SID2]),
                         "…and the ack's blob carries the newer web the client adopts")
        # the same stale copy of web riding a write that edits a DIFFERENT tag: web is kept, listed, ok
        c0 = self.post({"type": "tagEdit", "writeId": "w1b", "edit": {"op": "create", "name": "api", "color": "#54B204"}})
        w = json.loads(json.dumps(c0["views"]))                                  # a fresh copy (its `at` is the store's)…
        next(t for t in w["tags"] if t["id"] == "gA")["members"] = []            # …whose web differs from the store's anyway
        next(t for t in w["tags"] if t["id"] == c0["tid"])["color"] = "#000000"  # this write recolors api
        a2 = self.post({"type": "setTimelineViews", "writeId": "w1c", "views": w, "edited": [c0["tid"]]})
        self.assertEqual((a2["ok"], [r["tid"] for r in a2["refused"]]), (True, ["gA"]),
                         "ok — nothing the user did was refused — with the kept tag listed")
        self.assertIn("did not edit it", a2["refused"][0]["reason"])
        self.assertNotIn("error", a2)
        self.assertEqual(store_tag("api")["color"], "#000000", "the edited tag landed")
        self.assertEqual(sorted(m["sid"] for m in store_tag("web")["members"]), sorted([SID1, SID2]),
                         "the untouched tag was kept, whatever the stamps say (the copy is not stale by them)")
        self.assertIsNone(km._edit_tag(tid=c0["tid"], delete=True)[1])
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
        is one quiet stderr line and nothing on the dashboard. Round 5: a lens write (`edited` empty)
        changes no tag and logs nothing at all — the quiet line is for a write that names other tags."""
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
        self.assertEqual((a["ok"], a["refused"]), (True, []))
        self.assertEqual(self.notices, [], "nothing the user did was refused, so no notice")
        self.assertEqual([ln for ln in err.getvalue().splitlines() if ln.strip()], [],
                         "a lens write is the normal path: nothing is logged")
        # the same stale web riding a write that edits another tag: one quiet stderr line, no notice
        c0 = self.post({"type": "tagEdit", "writeId": "w1b", "edit": {"op": "create", "name": "api", "color": "#54B204"}})
        w = json.loads(json.dumps(c0["views"]))
        next(t for t in w["tags"] if t["id"] == "gA")["members"] = []
        next(t for t in w["tags"] if t["id"] == c0["tid"])["color"] = "#000000"
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            a2 = self.post({"type": "setTimelineViews", "writeId": "w1c", "views": w, "edited": [c0["tid"]]})
        self.assertEqual((a2["ok"], [r["tid"] for r in a2["refused"]]), (True, ["gA"]))
        self.assertEqual(self.notices, [], "nothing the user did was refused, so no notice")
        lines = [ln for ln in err.getvalue().splitlines() if ln.strip()]
        self.assertEqual(len(lines), 1, "one quiet stderr line is the whole record")
        self.assertIn('"web"', lines[0])
        self.assertNotIn("reload that dashboard", lines[0])
        self.assertIsNone(km._edit_tag(tid=c0["tid"], delete=True)[1])
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

    def test_a_stale_copy_cannot_resurrect_a_tag_deleted_elsewhere_but_a_named_create_lands(self):
        """Round 3 of the 2026-09-05 review, a pre-existing hole: the guard refused a stale DELETION
        (a tag absent from the copy) but not a stale RESURRECTION (a tag absent from the store) — an
        incoming unknown tag was always kept as new. With `edited`, the two creates a whole-blob write
        can carry are distinguishable: a tag the client did not name as edited is something another
        dashboard deleted after the copy was taken, and is kept out; a tag it did name is a genuine
        create (the legacy path's client-minted id); a write without `edited` keeps the old reading.
        Round 5: a lens write (`edited` empty) changes no tag, so the deleted tag is not even judged —
        the re-creation refusal is for a write that names OTHER tags as edited."""
        import contextlib
        import io
        self.seed()
        c = self.post({"type": "tagEdit", "writeId": "w1", "edit": {"op": "create", "name": "api", "color": "#54B204", "sids": [SID2]}})
        api_tid = c["tid"]
        stale = json.loads(json.dumps(c["views"]))                  # this dashboard's copy: web and api
        self.assertIsNone(km._edit_tag(tid=api_tid, delete=True)[1])   # another dashboard deletes api
        self.assertIsNone(store_tag("api"))
        # a lens change from the stale copy changes no tag: api stays deleted, nothing is listed or logged
        stale["actives"] = {"timeline": {"tags": ["web"]}, "chat": {"all": True}, "outline": {"all": True}}
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            a = self.post({"type": "setTimelineViews", "writeId": "w2", "views": stale, "edited": []})
        self.assertEqual((a["ok"], a["refused"]), (True, []), "nothing the user did was refused, and no tag was judged")
        self.assertNotIn("error", a)
        self.assertIsNone(store_tag("api"), "the deleted tag stays deleted")
        self.assertEqual([t["name"] for t in a["views"]["tags"]], ["web"], "…and the ack's blob, which the client adopts, has no api")
        self.assertEqual(a["views"]["actives"]["timeline"], {"tags": ["web"]}, "the lens landed")
        self.assertEqual(self.notices, [], "a stale copy of a deleted tag is not the user's problem")
        self.assertEqual([ln for ln in err.getvalue().splitlines() if ln.strip()], [], "nothing logged")
        # the same stale copy riding a write that edits web (a recolor): api is kept OUT with a reason, the write is ok
        stale_w = json.loads(json.dumps(stale))
        next(t for t in stale_w["tags"] if t["id"] == "gA")["color"] = "#000000"
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            a2 = self.post({"type": "setTimelineViews", "writeId": "w2b", "views": stale_w, "edited": ["gA"]})
        self.assertTrue(a2["ok"], "nothing the user did was refused")
        self.assertEqual([(r["tid"], r["name"]) for r in a2["refused"]], [(api_tid, "api")])
        self.assertEqual(a2["refused"][0]["reason"], "it was deleted after your copy was taken, so it was not re-created")
        self.assertNotIn("error", a2)
        self.assertIsNone(store_tag("api"), "the deleted tag stays deleted")
        self.assertEqual(store_tag("web")["color"], "#000000", "the edited tag landed")
        self.assertEqual(self.notices, [], "a stale copy of a deleted tag is not the user's problem")
        self.assertEqual(len([ln for ln in err.getvalue().splitlines() if ln.strip()]), 1, "one quiet line")
        # the same api, on a copy of the store, named as EDITED: a create (the legacy path's client-minted id), it lands
        api_row = next(t for t in stale["tags"] if t["id"] == api_tid)
        fresh = json.loads(json.dumps(km._views_client()))
        fresh["tags"].append(dict(api_row))
        b = self.post({"type": "setTimelineViews", "writeId": "w3", "views": fresh, "edited": [api_tid]})
        self.assertEqual((b["ok"], b["refused"]), (True, []))
        self.assertEqual(store_tag("api")["id"], api_tid)
        self.assertTrue(store_tag("api").get("mtime"), "a created tag is stamped like any edit")
        # no `edited` at all (an older client): every unknown tag is new, as before
        self.assertIsNone(km._edit_tag(tid=api_tid, delete=True)[1])
        fresh = json.loads(json.dumps(km._views_client()))
        fresh["tags"].append(dict(api_row))
        d = self.post({"type": "setTimelineViews", "writeId": "w4", "views": fresh})
        self.assertEqual((d["ok"], d["refused"]), (True, []))
        self.assertEqual(store_tag("api")["id"], api_tid, "the old reading stands for a client that cannot say")

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


class EditedBoundsTheWrite(_Wire):
    """Round 5 of the 2026-09-05 review (the HIGH finding): a lens or order write carries `edited: []`
    and is built from the store's blob the client last adopted, and the door still applied its tag
    set as a whole-blob replacement judged by the guard's second-resolution stamps — so a targeted
    edit that landed in the SAME second as that blob's `at` (its mtime equal to the writer's
    evidence, not newer by the guard's clock) was silently reverted by the next lens change: a rename
    undone, a create deleted, a member lost. Now `edited` bounds what a write may change: an empty
    list changes no tag; a list of ids changes those tags only, a differing copy of any other tag
    kept from the store quietly; no `edited` at all keeps the round-4 legacy reading."""

    def test_the_reproduction_a_same_second_targeted_edit_survives_a_lens_write(self):
        served = self.seed()                                           # the dashboard's adopted copy: web[SID1]
        lens = json.loads(json.dumps(served))
        # three targeted edits from another surface, landing right after the copy was taken
        self.assertIsNone(km._edit_tag(tid="gA", rename="api")[1])
        self.assertIsNone(km._edit_tag(tid="gA", add=[SID2])[1])
        d, err = km._edit_tag("docs", add=[SID3])
        self.assertIsNone(err)
        store = km._timeline_views()
        # the same-second case made exact rather than left to the test's timing: by the guard's clock
        # the copy's evidence equals the edits' stamps, so nothing about it reads as stale
        lens["at"] = max(t["mtime"] for t in store["tags"])
        lens["actives"] = {"timeline": {"tags": ["api"]}, "chat": {"all": True}, "outline": {"all": True}}
        lens["tagOrder"] = ["docs", "api"]
        a = self.post({"type": "setTimelineViews", "writeId": "w1", "views": lens, "edited": []})
        self.assertEqual((a["ok"], a["refused"]), (True, []))
        self.assertNotIn("error", a)
        web = next(t for t in km._timeline_views()["tags"] if t["id"] == "gA")
        self.assertEqual(web["name"], "api", "the rename survives the lens write")
        self.assertEqual(sorted(m["sid"] for m in web["members"]), sorted([SID1, SID2]), "the member survives")
        self.assertEqual(store_tag("docs")["id"], d["id"], "the create survives")
        self.assertEqual(km._timeline_views()["actives"]["timeline"], {"tags": ["api"]}, "the lens landed")
        self.assertEqual(km._timeline_views()["tagOrder"], ["docs", "api"], "…and the order")
        self.assertEqual([t["id"] for t in a["views"]["tags"]], [t["id"] for t in store["tags"]],
                         "the ack's blob is the store's tag set")
        self.assertEqual(self.notices, [], "the normal lens path: nothing said")
        self.assertGreater(a["seq"], store["seq"], "the write moved the store")

    def test_a_write_naming_its_edited_tags_changes_those_only(self):
        self.seed()
        c = self.post({"type": "tagEdit", "writeId": "w1", "edit": {"op": "create", "name": "api", "color": "#54B204"}})
        b_tid = c["tid"]
        w = json.loads(json.dumps(c["views"]))                          # a fresh copy: not stale by any stamp
        for t in w["tags"]:
            t["color"] = "#000000"                                       # …recoloring BOTH tags…
        a = self.post({"type": "setTimelineViews", "writeId": "w2", "views": w, "edited": [b_tid]})   # …claiming only B
        self.assertEqual((a["ok"], [r["tid"] for r in a["refused"]]), (True, ["gA"]))
        self.assertNotIn("error", a)
        self.assertEqual(store_tag("api")["color"], "#000000", "B, the edited tag, is applied")
        self.assertEqual(store_tag("web")["color"], "#3b82f6", "A is kept from the store, whatever the copy says")
        self.assertEqual(self.notices, [], "a kept tag outside `edited` is nobody's lost edit: quiet")
        # a tag omitted by a write that did not edit it is not deleted either
        w2 = json.loads(json.dumps(a["views"]))
        w2["tags"] = [t for t in w2["tags"] if t["id"] == b_tid]
        w2["tags"][0]["color"] = "#DD42FF"
        a2 = self.post({"type": "setTimelineViews", "writeId": "w3", "views": w2, "edited": [b_tid]})
        self.assertEqual((a2["ok"], [(r["tid"], r["reason"]) for r in a2["refused"]]),
                         (True, [("gA", "this write did not edit it, so it was not deleted")]))
        self.assertEqual(sorted(t["name"] for t in km._timeline_views()["tags"]), ["api", "web"])
        self.assertEqual(store_tag("api")["color"], "#DD42FF")
        self.assertEqual(self.notices, [])

    def test_a_write_without_edited_keeps_the_legacy_reading(self):
        served = self.seed()
        w = json.loads(json.dumps(served))
        w["tags"][0]["name"] = "api"                                    # a fresh copy renames web…
        w["tags"].append({"id": "gnew", "name": "docs", "color": "#DD42FF", "members": [SID2]})   # …and creates docs
        a = self.post({"type": "setTimelineViews", "writeId": "w1", "views": w})
        self.assertEqual((a["ok"], a["refused"]), (True, []), "a fresh whole-blob write lands whole, as before")
        self.assertEqual(store_tag("api")["id"], "gA")
        self.assertEqual(store_tag("docs")["id"], "gnew")
        # …and a stale one is judged by the stamps alone, loudly
        stale = json.loads(json.dumps(served))
        time.sleep(1.1)
        self.assertIsNone(km._edit_tag(tid="gA", add=[SID3])[1])
        b = self.post({"type": "setTimelineViews", "writeId": "w2", "views": stale})
        self.assertFalse(b["ok"])
        self.assertIn("gA", [r["tid"] for r in b["refused"]])
        self.assertTrue(self.notices and not self.notices[0][1], "loud, as before")


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
            self.assertTrue(on_disk["tags"][0].get("mtime"), "every tag is given an mtime by the stamp (round 5): "
                            "the mark that tells a tag a store once held from a client's own create")
            self.assertLessEqual(on_disk["tags"][0]["mtime"], on_disk["at"], "a file without `at`: the stamp's own time")
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


class LegacyTagsStampedOnFirstRead(_Wire):
    """Round 5 of the 2026-09-05 review: the write door stamps an mtime on a tag only when it changes,
    and the first-read stamp changes nothing, so a tag from before the per-tag stamp never got one —
    and the foreign-file rule (an unknown tag WITH an mtime existed in a store once and is not
    re-created; one without is the writer's own create) let a deleted legacy tag come back through
    a file written outside the kernel. The first-read stamp (and the migration) now give every tag
    an mtime: the file's `at`, else the time of the stamp."""

    def test_every_legacy_tag_gets_an_mtime_so_a_deleted_one_cannot_come_back_through_a_foreign_file(self):
        p = km._views_path()
        legacy = {"active": "all", "at": 1700000000, "tags": [
            {"id": "gL1", "name": "web", "color": "#3b82f6", "members": [{"host": "", "sid": SID1}]},
            {"id": "gL2", "name": "api", "color": "#54B204", "members": [{"host": "", "sid": SID2}]}]}
        p.write_text(json.dumps(legacy))
        v = km._timeline_views()                                       # the first read: the stamp
        self.assertEqual([t.get("mtime") for t in v["tags"]], [1700000000, 1700000000], "every tag carries the file's `at`")
        self.assertEqual([t["mtime"] for t in json.loads(p.read_text())["tags"]], [1700000000, 1700000000], "…on disk too")
        self.assertEqual(self.notices, [], "a stamp is not a refusal")
        panel = json.loads(p.read_text())                              # a panel's copy, taken after the stamp
        time.sleep(1.1)
        self.assertIsNone(km._edit_tag(tid="gL2", delete=True)[1])    # api deleted since
        s_served = km._timeline_views()["seq"]
        foreign = json.loads(json.dumps(panel))                        # the panel writes its copy: seq behind, judged
        foreign["actives"] = {"timeline": {"tags": ["web"]}, "chat": {"all": True}, "outline": {"all": True}}
        time.sleep(0.01)
        km._atomic_write(p, json.dumps(foreign))
        v2 = km._timeline_views()
        self.assertGreater(v2["seq"], s_served)
        self.assertEqual([t["id"] for t in v2["tags"]], ["gL1"],
                         "the deleted legacy tag does not come back: its mtime says a store once held it")
        self.assertEqual(v2["actives"]["timeline"], {"tags": ["web"]}, "the panel's lens change lands")
        self.assertTrue(self.notices and not self.notices[0][1])
        self.assertIn('"api" (re-creation)', self.notices[0][0])
        # a legacy file without `at`: the stamp's own time
        p.unlink()
        self.assertEqual(km._timeline_views()["tags"], [])
        p.write_text(json.dumps({"active": "all", "tags": [{"id": "gL3", "name": "docs", "color": "", "members": []}]}))
        before = int(time.time())
        v3 = km._timeline_views()
        self.assertGreaterEqual(v3["tags"][0]["mtime"], before)
        self.assertLessEqual(v3["tags"][0]["mtime"], v3["at"])


class SeqFloorOutlivesTheCacheEntry(_Wire):
    """Round 5 of the 2026-09-05 review: a store read as missing forgets its cache entry (rightly: a
    file that then appears must not be judged against a store that no longer exists), and with it
    forgot the seq floor — so a file restored from an older copy was served under its old seq, and
    every dashboard holding a higher one ignored it until the next kernel write. The floor is kept
    apart from the entry now (_VIEWS_SEQ_FLOOR): the restored file is re-stamped past it, as written,
    and every write orders past it."""

    def test_a_store_deleted_and_recreated_with_an_older_seq_is_restamped_past_the_floor(self):
        served = self.seed()
        s1 = served["seq"]
        p = km._views_path()
        content = json.loads(p.read_text())
        p.unlink()
        self.assertEqual(km._timeline_views()["tags"], [], "read as missing: the cache entry is forgotten")
        self.assertNotIn(str(p), km._flags_cache)
        self.assertGreaterEqual(km._views_seq_floor(), s1, "…the floor is not")
        restored = json.loads(json.dumps(content))
        restored["seq"] = s1 - 5                                       # a restore from an older copy
        km._atomic_write(p, json.dumps(restored))
        v = km._timeline_views()
        self.assertGreater(v["seq"], s1, "re-stamped past the last served seq: a dashboard holding s1 adopts it")
        self.assertEqual([t["name"] for t in v["tags"]], ["web"], "kept as written: nothing served to judge it against")
        self.assertEqual(json.loads(p.read_text())["seq"], v["seq"], "…and the file carries the new seq")
        self.assertEqual(self.notices, [], "ordering a file is not a refusal")
        # a restored file at or past the floor is left alone
        p.unlink()
        self.assertEqual(km._timeline_views()["tags"], [])
        ahead = json.loads(json.dumps(content))
        ahead["seq"] = v["seq"] + 100
        km._atomic_write(p, json.dumps(ahead))
        before = p.read_bytes()
        self.assertEqual(km._timeline_views()["seq"], v["seq"] + 100)
        self.assertEqual(p.read_bytes(), before, "byte-identical")
        # a write after a delete orders past the floor too, not just past the (empty) previous blob
        p.unlink()
        self.assertEqual(km._timeline_views()["tags"], [])
        a = self.post({"type": "setTimelineViews", "writeId": "w1", "views": {"active": "all", "tags": []}})
        self.assertGreater(a["seq"], v["seq"] + 100)

    def test_the_floor_is_per_store_so_two_state_dirs_in_one_process_do_not_share_one(self):
        """Round 6 of the 2026-09-05 review: the floor was one module-wide number keyed on nothing,
        while the read cache beside it is keyed by path — so a process serving two state dirs (a test
        suite; a kernel rebound to another root) re-stamped a cold read of a small-seq file in the
        fresh dir past the OTHER store's seq: a write on read, ordered against a store it never held."""
        from pathlib import Path
        s1 = self.seed()["seq"]
        home = km.jd.STATE
        self.assertGreaterEqual(km._views_seq_floor(), s1, "the first store's floor is raised by its own writes")
        other = tempfile.mkdtemp()
        km.jd.STATE = Path(other)
        p2 = km._views_path()
        try:
            km._atomic_write(p2, json.dumps({"active": "all", "tags": [dict(WEB)], "seq": 5, "at": 100}))
            before = p2.read_bytes()
            v = km._timeline_views()
            self.assertEqual(v["seq"], 5, "served as written: this store has no floor of its own")
            self.assertEqual(p2.read_bytes(), before, "…and the file is not rewritten")
            self.assertEqual(km._views_seq_floor(), 5, "the read raised THIS store's floor…")
            self.assertGreaterEqual(km._views_seq_floor(home / "timeline-views.json"), s1, "…and left the other's alone")
            self.assertEqual(self.notices, [])
        finally:
            km.jd.STATE = home
            km._flags_cache.pop(str(p2), None)
            km._VIEWS_SEQ_FLOOR.pop(str(p2), None)


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


class MigrationStampsTheArchivedTag(_Wire):
    """Round 4 of the 2026-09-05 review: the hidden-to-archived migration built its diff base from the
    same tag dicts it mutated (the archived tag's dict was aliased, and the dict copy was shallow), so
    the base already carried the migration and an EXISTING archived tag gained its members with no
    fresh mtime. A dashboard holding the pre-migration copy could then post the whole blob and strip
    the migrated members with no refusal. The migration now works on a deep copy: the moved members
    stamp the tag, and the guard refuses the stale copy."""

    def test_an_existing_archived_tag_is_stamped_by_the_migration_and_a_stale_copy_cannot_strip_it(self):
        p = km._views_path()
        pre = {"active": "all", "tags": [dict(WEB), {"id": "archived", "name": "archived", "color": "#6b7280",
                                                     "members": [SID2]}], "hidden": [SID3]}
        p.write_text(json.dumps(pre))
        v = km._timeline_views()
        arch = next(t for t in v["tags"] if t["name"] == "archived")
        self.assertEqual([m["sid"] for m in arch["members"]], sorted([SID2, SID3]), "the hidden entry joined the existing tag")
        self.assertTrue(arch.get("mtime"), "the migrated tag carries a FRESH edit stamp: its members changed")
        self.assertTrue(next(t for t in v["tags"] if t["id"] == "gA").get("mtime"),
                        "an untouched tag is given one too (round 5): every tag a migrated store holds carries an mtime")
        self.assertNotIn("hidden", json.loads(p.read_text()))
        # the pre-migration dashboard posts its whole copy (no `at`, no mtimes): the guard refuses
        # the archived hunk — the migrated members stand — and the ack says so
        stale = {"active": "all", "tags": [dict(WEB), {"id": "archived", "name": "archived", "color": "#6b7280", "members": [SID2]}]}
        a = self.post({"type": "setTimelineViews", "writeId": "w1", "views": stale, "edited": ["archived"]})
        self.assertFalse(a["ok"])
        self.assertEqual([r["tid"] for r in a["refused"]], ["archived"])
        self.assertEqual(sorted(m["sid"] for m in store_tag("archived")["members"]), sorted([SID2, SID3]),
                         "the migrated members survive the stale copy")
        self.assertTrue(self.notices and not self.notices[0][1], "and the refusal is loud")


class ReaderRestampUnwritable(_Wire):
    """Round 4 of the 2026-09-05 review: the reader's re-stamp write had no error handling, so an
    unwritable or full state dir made every READ raise, and the feed's build aborted with it. Now an
    OSError on that write is logged once per distinct error, the file is served as read (normalized)
    and cached under its own key so reads stop retrying the write, and the next successful write
    clears the note so a recurrence is logged again."""

    def setUp(self):
        super().setUp()
        km._VIEWS_RESTAMP_ERR[0] = None

    def test_a_read_only_state_dir_is_served_not_raised_and_logged_once(self):
        import contextlib
        import io
        if os.geteuid() == 0:
            self.skipTest("root ignores directory permissions")
        p = km._views_path()
        d = p.parent
        legacy = {"active": "all", "tags": [dict(WEB)]}                # seq-less: the first read wants to stamp it
        p.write_text(json.dumps(legacy))
        n = [0]
        real = km._atomic_write

        def counting(path, text, mode=None):
            n[0] += 1
            return real(path, text, mode)
        km._atomic_write = counting
        os.chmod(d, 0o555)
        try:
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                v = km._timeline_views()                                # does not raise
                self.assertEqual([t["name"] for t in v["tags"]], ["web"], "the file is served as read")
                self.assertNotIn("seq", v, "…unstamped: the write did not land")
                self.assertEqual(n[0], 1, "one write attempted")
                v2 = km._timeline_views()
                self.assertIs(v2, v, "the second read is a cache hit under the file's key")
                self.assertEqual(n[0], 1, "…and does not retry the write")
                km._flags_cache.clear()                                # a cold cache retries…
                km._timeline_views()
                self.assertEqual(n[0], 2)
            lines = [ln for ln in err.getvalue().splitlines() if "could not be re-stamped" in ln]
            self.assertEqual(len(lines), 1, "one stderr line for one distinct error, however many reads")
            self.assertIn("PermissionError", lines[0])
            self.assertEqual(p.read_text(), json.dumps(legacy), "the file is untouched")
            self.assertEqual(self.notices, [], "an unwritable store is a log line, not a refusal notice")
            # writable again: a kernel write succeeds and clears the note, so the next failure logs afresh
            os.chmod(d, 0o755)
            km._flags_cache.clear()
            a = self.post({"type": "tagEdit", "writeId": "w1", "edit": {"op": "recolor", "tid": "gA", "color": "#54B204"}})
            self.assertTrue(a["ok"])
            self.assertIsNone(km._VIEWS_RESTAMP_ERR[0], "a successful write clears the note")
            p.write_text(json.dumps(legacy))                           # seq-less again, then unwritable again
            km._flags_cache.clear()
            os.chmod(d, 0o555)
            err2 = io.StringIO()
            with contextlib.redirect_stderr(err2):
                km._timeline_views()
            self.assertEqual(len([ln for ln in err2.getvalue().splitlines() if "could not be re-stamped" in ln]), 1,
                             "the same error logs again after a write cleared the note")
        finally:
            os.chmod(d, 0o755)
            km._atomic_write = real
            km._VIEWS_RESTAMP_ERR[0] = None

    def test_a_judged_foreign_file_on_an_unwritable_store_is_served_judged_and_the_next_write_persists_it(self):
        """Round 5 of the 2026-09-05 review: the OSError branch served and cached the file AS READ in
        every case — in the judged case that is the foreign copy the judgment had just refused, so an
        unwritable store served the deleted tag back and the newer member gone, and the next RMW write,
        built from that cache, persisted them. The judgment is now a step apart from the write, and
        the judged blob is what an unwritable store serves and caches."""
        import contextlib
        import io
        if os.geteuid() == 0:
            self.skipTest("root ignores directory permissions")
        self.seed()
        c = self.post({"type": "tagEdit", "writeId": "w1", "edit": {"op": "create", "name": "api", "color": "#54B204", "sids": [SID2]}})
        api_tid = c["tid"]
        p = km._views_path()
        d = p.parent
        panel = json.loads(p.read_text())                              # the panel's copy: web[SID1], api
        time.sleep(1.1)
        self.assertIsNone(km._edit_tag(tid="gA", add=[SID3])[1])       # a member added since
        self.assertIsNone(km._edit_tag(tid=api_tid, delete=True)[1])   # a tag deleted since
        s_served = km._timeline_views()["seq"]
        foreign = json.loads(json.dumps(panel))                        # seq behind: judged on read
        foreign["actives"] = {"timeline": {"tags": ["web"]}, "chat": {"all": True}, "outline": {"all": True}}
        time.sleep(0.01)
        km._atomic_write(p, json.dumps(foreign))
        os.chmod(d, 0o555)
        try:
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                v = km._timeline_views()
                web = next(t for t in v["tags"] if t["id"] == "gA")
                self.assertEqual(sorted(m["sid"] for m in web["members"]), sorted([SID1, SID3]), "the newer member is served")
                self.assertNotIn("api", [t["name"] for t in v["tags"]], "the deleted tag stays absent")
                self.assertEqual(v["actives"]["timeline"], {"tags": ["web"]}, "the panel's lens change is served")
                self.assertGreater(v["seq"], s_served, "…under a seq past the last served, so dashboards adopt it")
                self.assertIs(km._timeline_views(), v, "cached: the judged blob, under the file's key")
            lines = [ln for ln in err.getvalue().splitlines() if "could not be re-stamped" in ln]
            self.assertEqual(len(lines), 1)
            self.assertIn("the judged blob", lines[0])
            self.assertEqual(json.loads(p.read_text())["tags"], foreign["tags"], "the file is still the foreign copy: nothing landed")
            self.assertEqual(len(self.notices), 1, "the judgment's refusals are reported once")
            self.assertFalse(self.notices[0][1])
            # writable again: the next write is built from the judged cache and persists the judged state
            os.chmod(d, 0o755)
            a = self.post({"type": "tagEdit", "writeId": "w2", "edit": {"op": "recolor", "tid": "gA", "color": "#DD42FF"}})
            self.assertTrue(a["ok"])
            on_disk = json.loads(p.read_text())
            web_disk = next(t for t in on_disk["tags"] if t["id"] == "gA")
            self.assertEqual(sorted(m["sid"] for m in web_disk["members"]), sorted([SID1, SID3]), "the newer member persists")
            self.assertEqual([t["name"] for t in on_disk["tags"]], ["web"], "the deleted tag does not come back")
            self.assertEqual(web_disk["color"], "#DD42FF")
            self.assertEqual(on_disk["actives"]["timeline"], {"tags": ["web"]})
            self.assertGreater(on_disk["seq"], v["seq"])
        finally:
            os.chmod(d, 0o755)
            km._VIEWS_RESTAMP_ERR[0] = None


class ForeignWriteJudged(_Wire):
    """Round 4 of the 2026-09-05 review: the re-stamp of a file written outside the kernel whose seq
    fell behind used the file's own content as the guard's base, so a stale Electron blob was blessed
    wholesale — a tag deleted since came back, a member added since was lost, silently. The writer's
    own seq says it held an older copy, so the file is now judged against the LAST SERVED blob: the
    refused hunks are kept from it, the writer's own creates land, and the refusals are reported
    through the sync notice naming each tag. With no served blob (a fresh kernel; a store read as
    missing) there is nothing to judge against and the file is ordered as written, as before."""

    def test_a_seq_behind_file_is_judged_against_the_last_served_blob(self):
        self.seed()
        c = self.post({"type": "tagEdit", "writeId": "w1", "edit": {"op": "create", "name": "api", "color": "#54B204", "sids": [SID2]}})
        api_tid = c["tid"]
        p = km._views_path()
        panel = json.loads(p.read_text())                              # the panel's copy: web[SID1], api, this seq and `at`
        time.sleep(1.1)
        self.assertIsNone(km._edit_tag(tid="gA", add=[SID3])[1])       # a member added since
        self.assertIsNone(km._edit_tag(tid=api_tid, delete=True)[1])   # a tag deleted since
        served = km._timeline_views()
        s_served = served["seq"]
        # the panel writes the file itself: its stale copy plus a lens change, plus a tag it created
        # (a client-minted id, no mtime — the one mark a kernel puts on a tag)
        foreign = json.loads(json.dumps(panel))
        foreign["actives"] = {"timeline": {"tags": ["web"]}, "chat": {"all": True}, "outline": {"all": True}}
        foreign["tags"].append({"id": "gdocs", "name": "docs", "color": "#DD42FF", "members": [SID2]})
        time.sleep(0.01)
        km._atomic_write(p, json.dumps(foreign))
        v = km._timeline_views()
        self.assertGreater(v["seq"], s_served, "re-stamped past the last served seq")
        web = next(t for t in v["tags"] if t["id"] == "gA")
        self.assertEqual(sorted(m["sid"] for m in web["members"]), sorted([SID1, SID3]), "the member added since is KEPT")
        self.assertIsNone(store_tag("api"), "the tag deleted since is not brought back")
        self.assertEqual(store_tag("docs")["id"], "gdocs", "the panel's own create lands")
        self.assertEqual(v["actives"]["timeline"], {"tags": ["web"]}, "the lens change lands")
        self.assertEqual(json.loads(p.read_text())["tags"], v["tags"], "the file holds the judged result")
        self.assertEqual(len(self.notices), 1)
        text, ok = self.notices[0]
        self.assertFalse(ok, "the refusals are loud")
        self.assertIn("outside the kernel", text)
        self.assertIn('"web"', text)
        self.assertIn('"api" (re-creation)', text, "…naming each tag")
        # no served blob: a store read as missing forgets what was served, and a file that then
        # appears is kept as written — nothing to judge it against — but ORDERED past the last
        # served seq, which outlives the entry (round 5; SeqFloorOutlivesTheCacheEntry)
        p.unlink()
        self.assertEqual(km._timeline_views()["tags"], [])
        recreated = json.loads(json.dumps(foreign))
        recreated["seq"] = 5
        km._atomic_write(p, json.dumps(recreated))
        v2 = km._timeline_views()
        self.assertEqual(sorted(t["name"] for t in v2["tags"]), ["api", "docs", "web"], "kept as written")
        self.assertGreater(v2["seq"], v["seq"], "re-stamped past the last served seq")
        self.assertEqual(len(self.notices), 1, "no second notice")


class WholeBlobNameCollisions(_Wire):
    """Round 4 of the 2026-09-05 review (the verifier's reproduction): a rename the targeted op refused
    as a duplicate landed anyway through a whole-blob lens write the dialog built from its PENDING
    copy, and neither the whole-blob door nor the normalizer deduped names — two tags with one name,
    which every name-keyed surface shows as one. The door now refuses a renamed or new tag whose name
    another tag in the resulting set holds, with a reason naming the collision, and the normalizer
    drops a second entry under one id."""

    def test_the_reproduction_a_refused_rename_cannot_land_through_a_lens_write(self):
        self.seed()
        c = self.post({"type": "tagEdit", "writeId": "w1", "edit": {"op": "create", "name": "api", "color": "#54B204", "sids": [SID2]}})
        api_tid = c["tid"]
        r = self.post({"type": "tagEdit", "writeId": "w2", "edit": {"op": "rename", "tid": api_tid, "newName": "web"}})
        self.assertEqual((r["ok"], r["error"]), (False, 'a tag named "web" already exists'))
        pending = json.loads(json.dumps(c["views"]))                    # the dialog's pending copy still carries the rename
        next(t for t in pending["tags"] if t["id"] == api_tid)["name"] = "web"
        pending["actives"] = {"timeline": {"tags": ["web"]}, "chat": {"all": True}, "outline": {"all": True}}
        a = self.post({"type": "setTimelineViews", "writeId": "w3", "views": pending, "edited": []})
        self.assertEqual((a["ok"], a["refused"]), (True, []),
                         "a lens write changes no tag (round 5), so the pending rename is not even judged")
        self.assertEqual(sorted(t["name"] for t in km._timeline_views()["tags"]), ["api", "web"], "ONE tag per name")
        self.assertEqual(km._timeline_views()["actives"]["timeline"], {"tags": ["web"]}, "the lens landed")
        self.assertEqual(self.notices, [], "nothing the user did in THIS write was refused")
        # the same pending copy riding a write that edits web (a recolor): the rename is a tag this
        # write did not claim to edit — kept as the store has it, listed with the collision's reason
        pending_w = json.loads(json.dumps(pending))
        next(t for t in pending_w["tags"] if t["id"] == "gA")["color"] = "#000000"
        a2 = self.post({"type": "setTimelineViews", "writeId": "w3b", "views": pending_w, "edited": ["gA"]})
        self.assertTrue(a2["ok"], "the refused hunk is a tag this write did not claim to edit")
        self.assertEqual([(x["tid"], x["name"]) for x in a2["refused"]], [(api_tid, "api")])
        self.assertIn("did not edit it", a2["refused"][0]["reason"])
        self.assertEqual(sorted(t["name"] for t in km._timeline_views()["tags"]), ["api", "web"], "ONE tag per name")
        self.assertEqual(store_tag("web")["color"], "#000000", "the recolor landed")
        self.assertEqual(self.notices, [], "nothing the user did in THIS write was refused")
        # the rename on a copy of the store, naming the tag as edited (an older client's whole-blob rename): refused, loud
        pending2 = json.loads(json.dumps(km._views_client()))
        next(t for t in pending2["tags"] if t["id"] == api_tid)["name"] = "web"
        b = self.post({"type": "setTimelineViews", "writeId": "w4", "views": pending2, "edited": [api_tid]})
        self.assertFalse(b["ok"])
        self.assertEqual(b["error"], '"api": a tag named "web" already exists, so it was not renamed to it')
        self.assertEqual(sorted(t["name"] for t in km._timeline_views()["tags"]), ["api", "web"])
        self.assertTrue(self.notices and not self.notices[0][1])
        self.assertIn('"api" (name collision)', self.notices[0][0])

    def test_a_new_tag_under_a_taken_name_is_kept_out_and_a_swap_of_two_names_lands(self):
        served = self.seed()
        blob = json.loads(json.dumps(served))
        blob["tags"].append({"id": "gnew", "name": "web", "color": "#000000", "members": []})
        a = self.post({"type": "setTimelineViews", "writeId": "w1", "views": blob, "edited": ["gnew"]})
        self.assertEqual((a["ok"], a["refused"][0]["tid"]), (False, "gnew"))
        self.assertEqual(a["refused"][0]["reason"], 'a tag named "web" already exists, so it was not created')
        self.assertEqual([t["id"] for t in km._timeline_views()["tags"]], ["gA"])
        # two tags trading names in one write collide with nothing: both changed, neither name is held
        c = self.post({"type": "tagEdit", "writeId": "w2", "edit": {"op": "create", "name": "api", "color": "#54B204"}})
        swap = json.loads(json.dumps(c["views"]))
        for t in swap["tags"]:
            t["name"] = "api" if t["id"] == "gA" else "web"
        b = self.post({"type": "setTimelineViews", "writeId": "w3", "views": swap, "edited": ["gA", c["tid"]]})
        self.assertEqual((b["ok"], b["refused"]), (True, []))
        self.assertEqual(store_tag("api")["id"], "gA")
        self.assertEqual(store_tag("web")["id"], c["tid"])

    def test_a_refused_rename_settles_its_stored_name_so_a_new_tag_under_it_is_refused_too(self):
        """Round 5 of the 2026-09-05 review: B (api → web, refused against A = web) stood as "api" but
        never claimed it, so a new C named "api" in the same write landed beside it — twins under the
        kept name. The pass now runs to a fixpoint: a refused rename settles its stored name and the
        takers are re-checked, in either array order, with or without `edited`."""
        for order, named in (("ABC", True), ("ACB", True), ("ABC", False), ("ACB", False)):
            with self.subTest(order=order, edited=named):
                try:
                    km._views_path().unlink()                              # a fresh store per case
                except OSError:
                    pass
                self.notices.clear()
                self.seed()
                c = self.post({"type": "tagEdit", "writeId": "w1", "edit": {"op": "create", "name": "api", "color": "#54B204"}})
                b_tid = c["tid"]
                blob = json.loads(json.dumps(c["views"]))
                a_row = next(t for t in blob["tags"] if t["id"] == "gA")
                b_row = next(t for t in blob["tags"] if t["id"] == b_tid)
                b_row["name"] = "web"                                       # B renamed to A's name
                c_row = {"id": "gC", "name": "api", "color": "#DD42FF", "members": []}   # C created under B's stored name
                blob["tags"] = [a_row, b_row, c_row] if order == "ABC" else [a_row, c_row, b_row]
                msg = {"type": "setTimelineViews", "writeId": "w2", "views": blob}
                if named:
                    msg["edited"] = [b_tid, "gC"]
                a = self.post(msg)
                self.assertFalse(a["ok"])
                self.assertEqual(sorted((r["tid"], r["name"]) for r in a["refused"]), sorted([(b_tid, "api"), ("gC", "api")]))
                reasons = {r["tid"]: r["reason"] for r in a["refused"]}
                self.assertEqual(reasons[b_tid], 'a tag named "web" already exists, so it was not renamed to it')
                self.assertEqual(reasons["gC"], 'a tag named "api" already exists, so it was not created')
                self.assertEqual(sorted((t["id"], t["name"]) for t in km._timeline_views()["tags"]),
                                 sorted([("gA", "web"), (b_tid, "api")]), "one tag per name: B kept under api, C kept out")
                self.assertTrue(self.notices and not self.notices[0][1], "both refusals are the poster's: loud")
                self.assertIn('"api" (name collision)', self.notices[0][0])

    def test_names_are_stripped_at_the_door_so_a_padded_spelling_is_the_same_name(self):
        """Round 5 of the 2026-09-05 review: the targeted door stripped a rename, the whole-blob door
        stripped nothing, so "web " beside "web" passed the collision pass as two names. Names are
        now clamped and stripped in the normalizer — the first step of every write and every read —
        and the targeted door's lookup uses the same basis."""
        served = self.seed()
        blob = json.loads(json.dumps(served))
        blob["tags"].append({"id": "gpad", "name": "web ", "color": "#000000", "members": []})
        a = self.post({"type": "setTimelineViews", "writeId": "w1", "views": blob, "edited": ["gpad"]})
        self.assertEqual((a["ok"], [r["tid"] for r in a["refused"]]), (False, ["gpad"]))
        self.assertEqual(a["refused"][0]["reason"], 'a tag named "web" already exists, so it was not created')
        self.assertEqual([t["name"] for t in km._timeline_views()["tags"]], ["web"], "no padded twin")
        blob["tags"][-1]["name"] = "  api  "
        b = self.post({"type": "setTimelineViews", "writeId": "w2", "views": blob, "edited": ["gpad"]})
        self.assertEqual((b["ok"], b["refused"]), (True, []))
        self.assertEqual(store_tag("api")["id"], "gpad", "stored stripped")
        self.assertEqual(next(t for t in b["views"]["tags"] if t["id"] == "gpad")["name"], "api", "…and served stripped")
        # the targeted door addresses the stored spelling from a padded one, rather than minting a twin
        t, err = km._edit_tag(" web ", add=[SID2])
        self.assertIsNone(err)
        self.assertEqual(t["id"], "gA")
        self.assertEqual(sorted(t["name"] for t in km._timeline_views()["tags"]), ["api", "web"])
        # a name that is only padding is no name: the whole-blob door stores the default, the targeted door mints one
        blob2 = json.loads(json.dumps(km._views_client()))
        blob2["tags"].append({"id": "gblank", "name": "   ", "color": "", "members": []})
        c = self.post({"type": "setTimelineViews", "writeId": "w3", "views": blob2, "edited": ["gblank"]})
        self.assertTrue(c["ok"])
        self.assertEqual(store_tag("tag")["id"], "gblank")
        t2, err = km._edit_tag("   ", add=[SID3])
        self.assertIsNone(err)
        self.assertTrue(t2["name"].strip() and t2["id"] not in ("gA", "gpad", "gblank"), "a create with no name takes the default")

    def test_the_normalizer_drops_a_second_entry_under_one_id(self):
        v = km._norm_timeline_views({"active": "all", "tags": [
            {"id": "g1", "name": "web", "members": [SID1]}, {"id": "g1", "name": "web", "members": [SID2]},
            {"id": "g2", "name": "api", "members": []}]})
        self.assertEqual([t["id"] for t in v["tags"]], ["g1", "g2"])
        self.assertEqual([m["sid"] for m in v["tags"][0]["members"]], [SID1], "the first entry is the one kept")


class CapNeverDropsAKeptStoreTag(_Wire):
    """Round 6 of the 2026-09-05 review (the MEDIUM finding): the door assembled the set that stands
    as the blob's tags first and the store's kept copies after, then sliced it to _VIEWS_MAX_TAGS —
    so when a stale client's tags plus the store's keeps exceeded the cap, the tag dropped was
    exactly the one the ack had just said was kept ("this write did not edit it, so it was not
    deleted"), and the client's own create took its place under an ok ack. Now a kept store tag
    always survives: the write's creates are refused instead, with a reason naming the cap, the same
    way _edit_tag refuses a 33rd."""

    def _seed_many(self, n):
        tags = [{"id": "g%d" % i, "name": "t%d" % i, "color": "", "members": []} for i in range(n)]
        ack = self.post({"type": "setTimelineViews", "writeId": "w0", "views": {"active": "all", "tags": tags}})
        self.assertEqual((ack["ok"], ack["refused"], len(ack["views"]["tags"])), (True, [], n))
        return ack["views"]

    def test_edited_path_a_create_over_the_cap_is_refused_and_the_quietly_kept_tag_survives(self):
        served = self._seed_many(km._VIEWS_MAX_TAGS)                       # the store is full
        stale = json.loads(json.dumps(served))
        stale["tags"] = [t for t in stale["tags"] if t["id"] != "g31"]      # a copy from before the 32nd…
        stale["tags"].append({"id": "gnew", "name": "mine", "color": "#DD42FF", "members": [SID1]})   # …plus a create
        a = self.post({"type": "setTimelineViews", "writeId": "w1", "views": stale, "edited": ["gnew"]})
        self.assertFalse(a["ok"], "the client's own create was refused, so the ack is not ok")
        rows = {r["tid"]: r["reason"] for r in a["refused"]}
        self.assertEqual(rows, {"gnew": "the views blob caps at 32 tags, so it was not created",
                                "g31": "this write did not edit it, so it was not deleted"})
        ids = [t["id"] for t in km._timeline_views()["tags"]]
        self.assertEqual(len(ids), km._VIEWS_MAX_TAGS)
        self.assertIn("g31", ids, "the kept tag the ack names is in the store")
        self.assertNotIn("gnew", ids, "the create is not")
        self.assertEqual([t["id"] for t in a["views"]["tags"]], ids, "the ack's blob is the store")
        self.assertEqual(len(self.notices), 1, "a refused create is the poster's lost edit: loud")
        self.assertIn('"mine" (over the cap)', self.notices[0][0])
        self.assertIn("32-tag cap", self.notices[0][0])

    def test_edited_less_path_the_loudly_kept_tag_survives_and_the_create_is_refused(self):
        served = self._seed_many(km._VIEWS_MAX_TAGS - 1)                   # 31 in the store
        t31, err = km._edit_tag("t31", add=[SID2])                         # another surface's create: 32
        self.assertIsNone(err)
        stale = json.loads(json.dumps(served))                             # an older client's copy of the 31…
        stale["at"] -= 10                                                  # …with evidence older than the create
        for t in stale["tags"]:
            t["mtime"] -= 10
        stale["tags"].append({"id": "gnew", "name": "mine", "color": "", "members": []})
        a = self.post({"type": "setTimelineViews", "writeId": "w1", "views": stale})   # no `edited`: the legacy reading
        self.assertFalse(a["ok"])
        rows = {r["tid"]: r["reason"] for r in a["refused"]}
        self.assertEqual(rows, {"gnew": "the views blob caps at 32 tags, so it was not created",
                                t31["id"]: "it was edited after your copy was taken, so it was not deleted"})
        ids = [t["id"] for t in km._timeline_views()["tags"]]
        self.assertEqual(len(ids), km._VIEWS_MAX_TAGS)
        self.assertIn(t31["id"], ids, "the store's newer tag stands, as the notice says it does")
        self.assertNotIn("gnew", ids)
        self.assertEqual(len(self.notices), 1)
        self.assertIn('"t31" (deletion)', self.notices[0][0])
        self.assertIn('"mine" (over the cap)', self.notices[0][0])

    def test_creates_that_fit_land_and_only_the_excess_is_refused_last_first(self):
        served = self._seed_many(km._VIEWS_MAX_TAGS - 2)                   # room for two
        w = json.loads(json.dumps(served))
        w["tags"] += [{"id": "gx", "name": "x", "color": "", "members": []},
                      {"id": "gy", "name": "y", "color": "", "members": []}]
        a = self.post({"type": "setTimelineViews", "writeId": "w1", "views": w, "edited": ["gx", "gy"]})
        self.assertEqual((a["ok"], a["refused"]), (True, []), "both creates fit")
        self.assertEqual(len(km._timeline_views()["tags"]), km._VIEWS_MAX_TAGS)
        w2 = json.loads(json.dumps(a["views"]))
        w2["tags"].append({"id": "gz", "name": "z", "color": "", "members": []})
        b = self.post({"type": "setTimelineViews", "writeId": "w2", "views": w2, "edited": ["gz"]})
        self.assertEqual((b["ok"], [(r["tid"], r["reason"]) for r in b["refused"]]),
                         (False, [("gz", "the views blob caps at 32 tags, so it was not created")]))
        self.assertEqual(len(km._timeline_views()["tags"]), km._VIEWS_MAX_TAGS)
        self.assertIsNone(store_tag("z"))
        self.assertEqual(self.notices[-1][1], False)
        # two creates where only one fits: the later one in array order is the one refused
        w3 = json.loads(json.dumps(served))
        w3["tags"] += [{"id": "ga", "name": "a", "color": "", "members": []},
                       {"id": "gb", "name": "b", "color": "", "members": []},
                       {"id": "gc", "name": "c", "color": "", "members": []}]
        try:
            km._views_path().unlink()
        except OSError:
            pass
        self._seed_many(km._VIEWS_MAX_TAGS - 2)
        c = self.post({"type": "setTimelineViews", "writeId": "w3", "views": w3, "edited": ["ga", "gb", "gc"]})
        self.assertEqual([r["tid"] for r in c["refused"]], ["gc"])
        self.assertEqual(sorted(t["name"] for t in km._timeline_views()["tags"] if t["id"] in ("ga", "gb", "gc")), ["a", "b"])

    def test_a_posted_33rd_tag_reaches_the_door_and_is_refused_not_sliced_off_by_the_normalizer(self):
        """The normalizer bounds a blob to the cap on every read, and the door read the posted blob
        through it — so a client's 33rd tag was gone before the judge saw it, no row, no notice. The
        door reads under a wider bound and its cap pass refuses the excess; disk reads keep the cap."""
        many = [{"id": "g%d" % i, "name": "t%d" % i, "color": "", "members": []} for i in range(km._VIEWS_MAX_TAGS + 1)]
        self.assertEqual(len(km._norm_timeline_views({"tags": many})["tags"]), km._VIEWS_MAX_TAGS, "a read is bounded, as before")
        a = self.post({"type": "setTimelineViews", "writeId": "w1", "views": {"active": "all", "tags": many}})
        self.assertEqual((a["ok"], [(r["tid"], r["reason"]) for r in a["refused"]]),
                         (False, [("g32", "the views blob caps at 32 tags, so it was not created")]))
        self.assertEqual(len(km._timeline_views()["tags"]), km._VIEWS_MAX_TAGS)


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
