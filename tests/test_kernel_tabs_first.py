"""TABS-FIRST (the user 2026-06-26): the tabOrder push carries name+color per tab so the client can paint the
WHOLE strip as placeholders up front (no one-by-one pop-in). The one emit site — the periodic/connect _push,
through the _tab_list_tmux collapse guard — sends a `tabs` list of {id, name, color} alongside the sid `order`.
The WS 'ready' handler used to send a second tabOrder from a raw liveness read; it is gone (2026-09-03: the
shim re-sends `ready` on a reconnect once the bundle has sent its own, and an omitted id is an authoritative
teardown on the client), so a fresh chat client's strip comes from the connect push's guarded frame.
"""
import inspect
import os
import unittest
from romp_load import load_source
import tempfile

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
KPATH = os.path.join(BIN, "romp-kernel")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
km = load_source("romp_kernel", KPATH)


class TabsFirst(unittest.TestCase):
    def test_push_taborder_carries_name_and_color_per_tab(self):
        src = inspect.getsource(km._push)
        self.assertIn('tab_meta = [{"id": s["sid"], "name": s.get("name", ""), "color": _name_color(s["sid"]),\n'
                      '                             "emoji": _name_emoji(s["sid"])} for s in chat_list]', src,
                      "the periodic push builds a name+color+emoji list per tab")
        self.assertIn('_send_client(c, ("taborder",), _tab_order_frame(tab_order, tab_meta))', src,
                      "and ships it as the tabs field alongside the sid order, in the frame's one spelling")

    def test_every_tab_order_frame_names_this_kernels_own_host(self):
        # the chat reads a postal card's sender host against the viewing kernel's own name (its
        # postalSenderHost); the session frame carries the name, but only a LOCAL session's frame teaches
        # it, so a dashboard whose kernel runs no sessions of its own never learned it until the + picker
        # opened, and a remote card stamped with this kernel's name stayed plain text (review find,
        # 2026-09-06). The tabOrder frame is the one every chat receives, first of all on connect.
        frame = km._tab_order_frame(["11111111-2222-3333-4444-555555555555"], [{"id": "11111111-2222-3333-4444-555555555555", "name": "web", "color": None}])
        self.assertEqual(frame["type"], "tabOrder")
        self.assertEqual(frame["selfHost"], km._self_host())
        self.assertEqual(sorted(frame), ["order", "selfHost", "tabs", "type", "views"])
        # the three senders share the one spelling: the pusher's tabs-first send, the off-cycle session push,
        # and the close confirmation — a fourth inline dict would drop the field again
        text = open(KPATH).read()
        self.assertEqual(text.count('_send_client(c, ("taborder",), _tab_order_frame(tab_order, tab_meta))'), 2)
        self.assertEqual(text.count("frame = _tab_order_frame(tab_order, tab_meta)"), 1)
        self.assertEqual(text.count('{"type": "tabOrder"'), 1, "the literal lives in _tab_order_frame alone")
        self.assertIn("_tab_order_frame(tab_order, tab_meta)", inspect.getsource(km._push_session_now))
        self.assertIn("_tab_order_frame(tab_order, tab_meta)", inspect.getsource(km._confirm_close_now))

    def test_connect_ready_handler_sends_no_tab_order_of_its_own(self):
        # the connect push (_push_one → _push, guarded) is the ONLY tabOrder source; the handler's own,
        # unguarded frame is gone (tests/test_feed_delta.py ReadyHandshake runs the handler)
        text = open(KPATH).read()
        self.assertNotIn('{"type": "tabOrder", "order": _o, "tabs": _tabs, "views": _views_client()}', text)
        i = text.index('if msg and msg.get("type") == "ready":')
        handler = text[i:text.index("_consume_pending_reveal(client)", i)]   # the handler's body, up to the parked-reveal step
        self.assertNotIn('"tabOrder"', handler, "no frame of that type from the handler itself (the comment may name it)")
        self.assertIn("self._push_one(client)", handler, "the guarded push still runs on `ready`")

    def test_name_color_shape_matches_the_client_color_type(self):
        # _name_color returns {bg,fg} or None — exactly the render.ts Color the placeholder applies.
        # A sid with no names entry → None (no color), which the client tolerates.
        self.assertIsNone(km._name_color("11111111-2222-3333-4444-555555555555"))


if __name__ == "__main__":
    unittest.main()
