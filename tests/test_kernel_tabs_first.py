"""TABS-FIRST (the user 2026-06-26): the tabOrder push carries name+color per tab so the client can paint the
WHOLE strip as placeholders up front (no one-by-one pop-in). The one emit site — the periodic/connect _push,
through the _tab_list_tmux collapse guard — sends a `tabs` list of {id, name, color} alongside the sid `order`,
plus the `live` sids the guard's map affirms for the cycle (T258: the pane keeps a live sid the order omits).
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
        # 2026-09-07: the frame itself moved into _tab_order_frame — the ONE builder (T258: it carries the
        # affirmed-live sids; and a reconnecting client's skeleton list) — so the pusher hands its order + meta
        # + liveness to _send_tab_order, which builds the frame per client. The liveness it hands over is the
        # frame's `live` set (T258), fed from the collapse guard's map the whole chat block trusts this cycle
        # (chat_tmux): on a carried cycle it lists the carried sids as live, consistent with `order`
        self.assertIn('_send_tab_order(c, tab_order, tab_meta, chat_tmux)', src,
                      "and ships it as the tabs field alongside the sid order, through the one strip builder")
        self.assertIn('fr = {"type": "tabOrder", "order": list(order), "tabs": tabs, "selfHost": _self_host(),\n'
                      '          **_views_payload(), "live": sorted({str(x) for x in live})}',
                      inspect.getsource(km._tab_order_frame), "the builder's frame keeps today's shape")

    def test_every_tab_order_frame_names_this_kernels_own_host(self):
        # the chat reads a postal card's sender host against the viewing kernel's own name (its
        # postalSenderHost); the session frame carries the name, but only a LOCAL session's frame teaches
        # it, so a dashboard whose kernel runs no sessions of its own never learned it until the + picker
        # opened, and a remote card stamped with this kernel's name stayed plain text (review find,
        # 2026-09-06). The tabOrder frame is the one every chat receives, first of all on connect.
        frame = km._tab_order_frame(["11111111-2222-3333-4444-555555555555"],
                                    [{"id": "11111111-2222-3333-4444-555555555555", "name": "web", "color": None}],
                                    {"11111111-2222-3333-4444-555555555555"})
        self.assertEqual(frame["type"], "tabOrder")
        self.assertEqual(frame["selfHost"], km._self_host())
        self.assertEqual(frame["live"], ["11111111-2222-3333-4444-555555555555"], "the live set rides the same frame (T258)")
        self.assertEqual(sorted(frame), ["live", "order", "selfHost", "tabs", "type", "views"])
        # the three senders share the one spelling: the pusher's tabs-first send, the off-cycle session push
        # and the close confirmation all hand their order + meta + liveness to _send_tab_order, the builder's
        # ONE caller (2026-09-07: it builds the frame per client, so a reconnecting client's skeleton list can
        # ride it); the WS 'ready' handler sends no strip of its own (2026-09-03, kept under #1017 by the
        # 2026-09-09 ruling), so a fourth inline dict would drop the field again
        text = open(KPATH).read()
        self.assertEqual(text.count('_send_client(c, ("taborder",), _tab_order_frame(tab_order, tab_meta, live, c))'), 1)
        self.assertEqual(text.count("_tab_order_frame(tab_order, tab_meta, live, c)"), 1, "the builder's one caller: _send_tab_order")
        # ...the three call sites each naming the liveness map its sender trusted: the pusher's guarded map for
        # the cycle (chat_tmux), the off-cycle push's guarded read (tmux), the close confirmation's guarded read
        # (guarded); never a raw _tmux_sessions(). The prefix count includes the def line, hence the 4
        self.assertEqual(text.count("def _send_tab_order(c, tab_order, tab_meta, live):"), 1)
        self.assertEqual(text.count("_send_tab_order(c, tab_order, tab_meta, "), 4, "the def line and the three call sites")
        self.assertEqual(text.count("_send_tab_order(c, tab_order, tab_meta, chat_tmux)"), 1)
        self.assertEqual(text.count("_send_tab_order(c, tab_order, tab_meta, tmux)"), 1)
        self.assertEqual(text.count("_send_tab_order(c, tab_order, tab_meta, guarded)"), 1)
        self.assertEqual(text.count("_send_tab_order(client, _o, _tabs, _tm)"), 0,
                         "the WS 'ready' handler sends no strip of its own (2026-09-03; kept under #1017 by the 2026-09-09 "
                         "ruling): the guarded push is the only tabOrder source, so upstream's connect-time hand-off has no home here")
        self.assertEqual(text.count('{"type": "tabOrder"'), 1, "the literal lives in _tab_order_frame alone")
        self.assertIn("_send_tab_order(c, tab_order, tab_meta, ", inspect.getsource(km._push_session_now))
        self.assertIn("_send_tab_order(c, tab_order, tab_meta, tmux)", inspect.getsource(km._push_session_now),
                      "the off-cycle push hands the builder its own guarded read")
        self.assertIn("_send_tab_order(c, tab_order, tab_meta, ", inspect.getsource(km._confirm_close_now))
        self.assertIn("_send_tab_order(c, tab_order, tab_meta, guarded)", inspect.getsource(km._confirm_close_now),
                      "the close confirmation hands the builder its own guarded read")

    def test_connect_ready_handler_sends_no_tab_order_of_its_own(self):
        # the connect push (_push_one → _push, guarded) is the ONLY tabOrder source; the handler's own,
        # unguarded frame is gone (tests/test_feed_delta.py ReadyHandshake runs the handler). Upstream's
        # T258 spelled that frame through the builder (`_frame = _tab_order_frame(_o, _tabs, _tm)`) and #1017
        # respelled it as a hand-off (`_send_tab_order(client, _o, _tabs, _tm)`, 2026-09-07); the fork removed
        # the block on 2026-09-03 and the 2026-09-09 ruling on skeleton tabs under READY_GATE_CAP keeps it out
        # (a redial's skeleton set is resolved by the pusher's strip: tests/test_chat_skeleton_reconnect_gate.py),
        # so none of the spellings has a home here
        text = open(KPATH).read()
        self.assertNotIn('{"type": "tabOrder", "order": _o, "tabs": _tabs, "views": _views_client()}', text)
        self.assertNotIn('_frame = _tab_order_frame(_o, _tabs, _tm)', text)
        self.assertNotIn('_send_tab_order(client, _o, _tabs, _tm)', text,
                         "#1017's respelling of that frame (2026-09-07) has no home here either: the 2026-09-09 ruling keeps "
                         "the fork's handler strip-less, and the pusher's _resolve_reconnect fills a redial's skeleton set")
        self.assertNotIn('_tabs = [{"id": s["sid"], "name": s.get("name", ""), "color": _name_color(s["sid"])}', text,
                         "no tab_meta list is built in the handler")
        i = text.index('if msg and msg.get("type") == "ready":')
        handler = text[i:text.index("_consume_pending_reveal(client)", i)]   # the handler's body, up to the parked-reveal step
        self.assertNotIn('"tabOrder"', handler, "no frame of that type from the handler itself (the comment may name it)")
        self.assertNotIn("_send_tab_order(", handler, "...and no hand-off to the strip builder")
        self.assertNotIn("_resolve_reconnect(", handler, "...nor a resolve: the pusher's strip resolves a redial's set")
        self.assertIn("self._push_one(client)", handler, "the guarded push still runs on `ready`")

    def test_name_color_shape_matches_the_client_color_type(self):
        # _name_color returns {bg,fg} or None — exactly the render.ts Color the placeholder applies.
        # A sid with no names entry → None (no color), which the client tolerates.
        self.assertIsNone(km._name_color("11111111-2222-3333-4444-555555555555"))


if __name__ == "__main__":
    unittest.main()
