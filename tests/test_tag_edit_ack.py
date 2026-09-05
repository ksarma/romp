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
        km._flags_cache.clear()
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
        km._flags_cache.clear()

    def post(self, msg, client=None):
        """Dispatch one client frame; return the reply it produced on that socket (or None)."""
        c = client or self.client
        before = len(self.sent) if c is self.client else None
        km.Handler._dispatch_ws(self.handler, msg, c)
        km._flags_cache.clear()
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

    def test_the_users_burst_create_then_rename_then_assign_before_any_frame_all_land_and_each_is_acked(self):
        """The exact gesture sequence that was lost, as targeted ops: nothing waits for an echo, and
        the store ends up holding the typed name and the assigned sessions."""
        self.seed()
        a1 = self.post({"type": "tagEdit", "writeId": "w1", "op": "create", "name": "tag 2",
                        "color": "#1EA1EB", "id": "gnew1"})
        self.assertEqual((a1["type"], a1["writeId"], a1["ok"]), ("tagEditAck", "w1", True))
        self.assertEqual(store_tag("tag 2")["id"], "gnew1", "the dialog's own id is honored, so its rows keep addressing the tag")
        a2 = self.post({"type": "tagEdit", "writeId": "w2", "op": "rename", "name": "tag 2", "newName": "notes-api"})
        self.assertEqual((a2["writeId"], a2["ok"]), ("w2", True))
        self.assertEqual(store_tag("notes-api")["id"], "gnew1", "the rename typed before any echo LANDS")
        self.assertIsNone(store_tag("tag 2"))
        a3 = self.post({"type": "tagEdit", "writeId": "w3", "op": "addMember", "name": "notes-api", "sids": [SID2, SID3]})
        self.assertEqual((a3["writeId"], a3["ok"]), ("w3", True))
        self.assertEqual(sorted(m["sid"] for m in store_tag("notes-api")["members"]), sorted([SID2, SID3]),
                         "the assignment lands too — the second half of the report")
        self.assertEqual(self.notices, [], "a targeted edit is never judged stale: it is built from the store")
        # the ack carries the poster's NEW BASE: the rendered client blob, stamped, with the edit in it
        v = a3["views"]
        self.assertTrue(v.get("at"), "the ack blob carries the store's write stamp")
        t = next(x for x in v["tags"] if x["id"] == "gnew1")
        self.assertEqual((t["name"], sorted(t["members"])), ("notes-api", sorted([SID2, SID3])))
        self.assertTrue(t.get("mtime"), "…and the per-tag mtime the guard reads")
        self.assertNotIn("error", a3)

    def test_recolor_remove_member_and_delete(self):
        self.seed()
        self.post({"type": "tagEdit", "writeId": "w1", "op": "addMember", "name": "web", "sid": SID2})
        self.assertEqual(len(store_tag("web")["members"]), 2, "a single `sid` spelling works beside `sids`")
        a = self.post({"type": "tagEdit", "writeId": "w2", "op": "recolor", "name": "web", "color": "#DD42FF"})
        self.assertTrue(a["ok"])
        self.assertEqual(store_tag("web")["color"], "#DD42FF")
        a = self.post({"type": "tagEdit", "writeId": "w3", "op": "removeMember", "name": "web", "sids": [SID1]})
        self.assertTrue(a["ok"])
        self.assertEqual([m["sid"] for m in store_tag("web")["members"]], [SID2])
        a = self.post({"type": "tagEdit", "writeId": "w4", "op": "delete", "name": "web"})
        self.assertEqual((a["ok"], a["views"]["tags"]), (True, []))
        self.assertEqual(self.notices, [])

    def test_a_create_with_members_is_one_op_the_join_menus_new_tag_input(self):
        self.seed()
        a = self.post({"type": "tagEdit", "writeId": "w1", "op": "create", "name": "qa", "color": "#54B204",
                       "id": "gq1", "sids": [SID2, SID3]})
        self.assertTrue(a["ok"])
        self.assertEqual(sorted(m["sid"] for m in store_tag("qa")["members"]), sorted([SID2, SID3]))

    def test_a_refused_edit_acks_a_plain_reason_and_changes_nothing(self):
        self.seed()
        self.post({"type": "tagEdit", "writeId": "w1", "op": "create", "name": "api", "color": "#54B204", "id": "gb1"})
        before = json.dumps(km._timeline_views(), sort_keys=True)
        cases = [
            ({"op": "rename", "name": "api", "newName": "web"}, 'a tag named "web" already exists'),
            ({"op": "rename", "name": "ghost", "newName": "x"}, 'no tag named "ghost"'),
            ({"op": "create", "name": "web", "color": "#000000", "id": "gc1"}, 'a tag named "web" already exists'),
            ({"op": "addMember", "name": "ghost", "sids": [SID2]}, 'no tag named "ghost"'),
            ({"op": "addMember", "name": "web", "sids": []}, "no session named"),
            ({"op": "recolor", "name": "web"}, "no color given"),
            ({"op": "rename", "name": "web", "newName": "   "}, "the new name is empty"),
            ({"op": "delete", "name": "ghost"}, 'no tag named "ghost"'),
            ({"op": "explode", "name": "web"}, 'unknown tag edit "explode"'),
            ({"op": "rename", "name": "", "newName": "x"}, "the tag name is empty"),
        ]
        for i, (edit, why) in enumerate(cases):
            a = self.post(dict(edit, type="tagEdit", writeId="r%d" % i))
            self.assertEqual((a["type"], a["writeId"], a["ok"]), ("tagEditAck", "r%d" % i, False), edit)
            self.assertEqual(a["error"], why, edit)
            self.assertIn("views", a, "a refusal still carries the store's blob — the poster's revert base")
            self.assertEqual(json.dumps(km._timeline_views(), sort_keys=True), before, "a refused edit writes nothing")
        # a tag that no longer exists is REFUSED, never resurrected: the dialog's rename of a tag
        # another dashboard deleted must not quietly mint a new one under the old name
        self.assertIsNone(store_tag("ghost"))

    def test_the_ack_answers_the_posting_socket_only(self):
        self.seed()
        other_sent = []
        other = {"app": "timeline", "wid": "w-other", "alive": True, "send": lambda s: other_sent.append(json.loads(s))}
        n = len(self.sent)
        self.post({"type": "tagEdit", "writeId": "w9", "op": "create", "name": "api", "color": "#54B204", "id": "gb1"}, client=other)
        self.assertEqual([m["type"] for m in other_sent], ["tagEditAck"])
        self.assertEqual(len(self.sent), n, "no other socket sees the ack — their pushed frames are unchanged")
        # …and a send failure on the poster's socket never escapes the handler (the client is dead, not the kernel)
        def boom(s):
            raise OSError("client gone")
        dead = {"app": "timeline", "wid": "w-dead", "alive": True, "send": boom}
        self.post({"type": "tagEdit", "writeId": "w10", "op": "create", "name": "qa", "color": "#54B204", "id": "gc1"}, client=dead)
        self.assertIsNotNone(store_tag("qa"), "the edit landed even though the ack could not be delivered")

    def test_an_edit_without_a_write_id_is_still_acked_with_a_null_id(self):
        self.seed()
        a = self.post({"type": "tagEdit", "op": "create", "name": "api", "color": "#54B204"})
        self.assertEqual((a["ok"], a["writeId"]), (True, None))
        self.assertTrue(store_tag("api")["id"].startswith("g"), "no client id → the kernel mints one, /tag's shape")


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
        km._flags_cache.clear()
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

    def test_a_stale_deletion_is_named_as_such(self):
        served = self.seed()
        stale = json.loads(json.dumps(served))
        time.sleep(1.1)
        km._edit_tag("web", add=[SID2])
        km._flags_cache.clear()
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


class SetterReturnsRefusals(unittest.TestCase):
    """_set_timeline_views now RETURNS the refused rows (name + plain reason); callers that ignored
    None keep ignoring a list."""

    def setUp(self):
        try:
            km._views_path().unlink()
        except OSError:
            pass
        km._flags_cache.clear()
        self._sync = km._sync_notice
        km._sync_notice = lambda text, ok=True: None

    def tearDown(self):
        km._sync_notice = self._sync
        try:
            km._views_path().unlink()
        except OSError:
            pass
        km._flags_cache.clear()

    def test_clean_writes_return_an_empty_list_and_stale_ones_the_rows(self):
        self.assertEqual(km._set_timeline_views({"active": "all", "tags": [dict(WEB)]}), [])
        km._flags_cache.clear()
        stale = json.loads(json.dumps(km._timeline_views()))
        time.sleep(1.1)
        km._edit_tag("web", add=[SID2])
        km._flags_cache.clear()
        stale["tags"][0]["members"] = []
        rows = km._set_timeline_views(stale)
        self.assertEqual([sorted(r.keys()) for r in rows], [["name", "reason"]])
        self.assertEqual(rows[0]["name"], "web")


class WebBootWiring(unittest.TestCase):
    """The kernel-served timeline page: the inline _TIMELINE_BOOT twin of timeline-boot.ts exposes
    the targeted-edit bridge and routes both acks to the panel (timeline-boot.test.ts pins the two
    bridge sets equal)."""

    def test_the_bridge_and_the_ack_dispatch(self):
        src = open(os.path.join(BIN, "romp-kernel")).read()
        self.assertIn('window.__rompTimelineTagEdit=function(edit){post(Object.assign({type:"tagEdit"},edit));};', src)
        self.assertIn('window.__rompTimelineSetViews=function(views,writeId){post({type:"setTimelineViews",views:views,writeId:writeId});};', src)
        self.assertIn('else if((m.type==="tagEditAck"||m.type==="viewsAck")&&panel.viewsAck)panel.viewsAck(m);', src)


if __name__ == "__main__":
    raise SystemExit("run under pytest: ~/.venvs/romptest/bin/python -m pytest %s -q -p no:cacheprovider" % __file__)
