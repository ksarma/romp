#!/usr/bin/env python3
"""The "Waiting on you" pane (app=waiting): every session's open USER TODOS across every attached
machine, in one place, with Reply / Dismiss / open-session per row. Kernel side, pinned here:

- build_feed ships the rows: `userTodoRows` = [{sid, name, color, todos:[{id, text, createdT,
  detail?}]}] sorted by sid, built in the SAME loop as the `userTodos` count map (badge and pane
  agree by construction), behind the same ended / mute / switch gates, store values only (byte-
  stable across builds — _send_client dedups on the bytes); and `userTodosOn`, THIS kernel's
  switch, so the pane can tell "off here" from "nothing waiting" (both ship [] rows). Both ride
  _feed_parts' `rest`, so a delta client gets them under `top` with no delta-side change.
- the app=waiting plumbing: the feed send set, the send loop, the `ready` serve + the feed-only
  connect-push skip, the conserve-memory viewer list, the /waiting page and its shim caps.
- the shell: a fifth pane after Feed, default OFF, with its gutter, grow var, focus/Esc/mobile
  wiring and the PN/_PANE_ORDER label "Waiting on you".

SYNTHETIC fixtures only: placeholder UUIDs (private to this module — see CLAUDE.md, goal-store
fixtures), the notes-api demo world.
"""
import json
import os
import tempfile
import unittest
from romp_load import load_source
from pathlib import Path
from unittest import mock

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
load_source("romp_event_model_wpane", os.path.join(BIN, "romp-event-model"))
load_source("romp_judge_wpane", os.path.join(BIN, "romp-judge"))
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ["ROMP_SERVE_TOKEN"] = "testtok"
km = load_source("romp_kernel_wpane", os.path.join(BIN, "romp-kernel"))
jd = km.jd
SRC = open(os.path.join(BIN, "romp-kernel")).read()

# private synthetic sids for this module (never the shared 11111111-2222-… placeholder)
SID = "77777777-8888-9999-aaaa-bbbbbbbbbbbb"
SID2 = "66666666-7777-8888-9999-aaaaaaaaaaaa"
NOW = 1781200000


class _Sandbox(unittest.TestCase):
    """Per-test STATE sandbox + cache reset (test_user_todos.py's _StoreSandbox idiom), switch ON."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.saved = jd.STATE
        jd.STATE = Path(self.td.name)
        km._user_todos_cache.clear()
        km._user_todos_bad.clear()
        km._flags_cache.clear()
        km._set_user_todos(True)

    def tearDown(self):
        jd.STATE = self.saved
        self.td.cleanup()
        km._user_todos_cache.clear()
        km._user_todos_bad.clear()
        km._flags_cache.clear()

    def feed_env(self, sids):
        """Patch build_feed's session inputs to a synthetic alive set (no parse — the cold-start shape)."""
        sessions = [{"sid": s, "name": n, "path": "/nonexistent/%s.jsonl" % s, "anchor": 0, "mtime": 0}
                    for s, n in sids]
        for p in (mock.patch.object(km, "_alive_sessions", lambda now, tmux: list(sessions)),
                  mock.patch.object(km, "_warm_fleet_bg", lambda now: None)):
            p.start()
            self.addCleanup(p.stop)


class FeedRows(_Sandbox):
    def test_rows_carry_each_sessions_open_todos_sorted_by_sid(self):
        km._add_user_todo(SID, "Need the auth-scheme decision to wire login", "OAuth vs cookie")
        km._add_user_todo(SID, "Need a staging credential for the tests")
        tid = km._add_user_todo(SID2, "Need your pick of the two route layouts")
        km._resolve_user_todo(SID2, tid, "withdrawn")
        self.feed_env([(SID, "web"), (SID2, "api")])
        feed = km.build_feed(NOW, {})
        rows = feed.get("userTodoRows")
        self.assertIsInstance(rows, list)
        self.assertEqual([r["sid"] for r in rows], [SID], "open rows only; a resolved-only sid has no row")
        row = rows[0]
        self.assertEqual(set(row), {"sid", "name", "color", "todos"})
        self.assertEqual(row["name"], "web")
        self.assertEqual(row["todos"], km._open_user_todos(SID), "the exact chat-payload row shape, oldest first")
        by_text = {t["text"]: t for t in row["todos"]}
        self.assertEqual(set(by_text["Need the auth-scheme decision to wire login"]), {"id", "text", "createdT", "detail"})
        self.assertEqual(set(by_text["Need a staging credential for the tests"]), {"id", "text", "createdT"},
                         "detail key only when non-blank")
        self.assertIsInstance(by_text["Need a staging credential for the tests"]["createdT"], int)   # epoch SECONDS
        self.assertIs(feed.get("userTodosOn"), True)

    def test_rows_are_sorted_by_sid_across_sessions(self):
        km._add_user_todo(SID, "web: need the staging port")
        km._add_user_todo(SID2, "api: need the auth decision")
        self.feed_env([(SID, "web"), (SID2, "api")])
        rows = km.build_feed(NOW, {}).get("userTodoRows")
        self.assertEqual([r["sid"] for r in rows], sorted([SID, SID2]))

    def test_rows_and_the_count_map_agree_by_construction(self):
        km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        km._add_user_todo(SID, "Need a staging credential for the tests")
        km._add_user_todo(SID2, "Need your pick of the two route layouts")
        self.feed_env([(SID, "web"), (SID2, "api")])
        feed = km.build_feed(NOW, {})
        self.assertEqual({r["sid"]: len(r["todos"]) for r in feed["userTodoRows"]}, feed["userTodos"])
        self.assertEqual(feed["userTodos"], {SID: 2, SID2: 1})

    def test_an_ended_session_contributes_no_row(self):
        km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        (jd.STATE / "gone").mkdir(parents=True, exist_ok=True)
        (jd.STATE / "gone" / (SID + ".json")).write_text(json.dumps({"t": NOW, "by": "gone"}))
        self.feed_env([(SID, "web")])
        feed = km.build_feed(NOW, {})
        self.assertEqual(feed.get("userTodoRows"), [], "hidden, not cleared — a revive brings it back")
        self.assertEqual(feed.get("userTodos"), {})
        self.assertTrue(km._open_user_todos(SID), "the store still holds the open ask")

    def test_a_muted_session_contributes_no_row(self):
        km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        (jd.STATE / "session-flags.json").write_text(json.dumps({SID: {"hideFromFeed": True}}))
        km._flags_cache.clear()
        self.feed_env([(SID, "web")])
        feed = km.build_feed(NOW, {})
        self.assertEqual(feed.get("userTodoRows"), [], "muted from the feed → absent from its aggregates")

    def test_off_ships_no_rows_and_says_so(self):
        km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        km._set_user_todos(False)
        self.feed_env([(SID, "web")])
        feed = km.build_feed(NOW, {})
        self.assertEqual(feed.get("userTodoRows"), [])
        self.assertIs(feed.get("userTodosOn"), False, "the pane tells 'off here' from 'nothing waiting' by this")
        km._set_user_todos(True)
        feed = km.build_feed(NOW, {})
        self.assertEqual([r["sid"] for r in feed["userTodoRows"]], [SID], "the store kept the row for the flip back")
        self.assertIs(feed.get("userTodosOn"), True)

    def test_rows_serialize_stably_across_builds(self):
        # the feed payload is dedup-compared serialized (_send_client) — same store, same bytes;
        # so no `now`, no age, nothing per-build may enter a row
        km._add_user_todo(SID2, "api: need the auth decision", "the two layouts are in the plan")
        km._add_user_todo(SID, "web: need the staging port")
        self.feed_env([(SID, "web"), (SID2, "api")])
        a = json.dumps(km.build_feed(NOW, {}).get("userTodoRows"))
        b = json.dumps(km.build_feed(NOW + 600, {}).get("userTodoRows"))
        self.assertEqual(a, b)

    def test_rows_and_the_switch_ride_the_delta_top(self):
        # _feed_parts puts every non-keyed field in `rest` → feedDelta.top; a delta client
        # (the pane announces FEED_DELTA_CAP) needs no delta-side change to receive them
        km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        self.feed_env([(SID, "web")])
        feed = km.build_feed(NOW, {})
        _cards, _leds, rest, rest_ms = km._feed_parts(feed)
        self.assertIn("userTodoRows", rest)
        self.assertIn("userTodosOn", rest)
        self.assertEqual(json.loads(rest_ms)["userTodoRows"], feed["userTodoRows"])

    def test_rows_are_built_in_the_count_maps_loop(self):
        # the mechanism behind "agree by construction": one read, appended beside the count
        src = SRC
        self.assertIn('_ut_map[fsid] = len(_ut_open)\n'
                      '            _ut_rows.append({"sid": fsid, "name": name, "color": color, "todos": _ut_open})', src)
        self.assertIn('"userTodoRows": sorted(_ut_rows, key=lambda r: r["sid"])', src)
        self.assertIn('"userTodosOn": _user_todos_on()', src)


class Plumbing(unittest.TestCase):
    """app=waiting is a feed client to the kernel: it is in the feed send set, the send loop, the `ready`
    serve (and, needing no ledgers, the feed-only connect-push skip) and the conserve-memory viewer list
    (or an open Waiting-on-you pane alone would read as a closed dashboard and park every session)."""

    def test_waiting_is_in_the_feed_send_set_and_loop(self):
        self.assertIn('want_feed = any(c["app"] in ("feed", "fleet", "waiting", "chat") for c in targets)', SRC)
        self.assertIn('if c["app"] in ("feed", "fleet", "waiting"):', SRC)

    def test_ready_serves_the_cached_frame_and_skips_the_ledgerless_connect_push(self):
        self.assertIn('served = client.get("app") in ("feed", "fleet", "waiting") and _send_feed_now(client)', SRC)
        self.assertIn('if not (served and client.get("app") in ("feed", "waiting")):', SRC)

    def test_an_open_waiting_pane_counts_as_a_viewer_for_conserve_memory(self):
        self.assertIn('c.get("app") in ("chat", "fleet", "timeline", "feed", "waiting", "files")', SRC)

    def test_the_page_rides_the_feed_pane_caps_and_the_shared_dress(self):
        page = km._waiting_page()
        self.assertIn('_shim("waiting", v, caps=FEED_DELTA_CAP + "," + READY_GATE_CAP)', SRC)
        self.assertIn("app=waiting", page)
        self.assertIn("/dist/styles.css", page)                     # the split card's .ut-* dress
        self.assertIn("<div id=waiting-head></div><div id=waiting-list></div>", page)
        self.assertIn("/dist/federation.js", page)
        self.assertIn("/dist/waiting.js", page)
        self.assertLess(page.index("/dist/federation.js"), page.index("/dist/waiting.js"), "manager before the bundle")
        self.assertIn('_pane_spin("waiting-list")', SRC)
        self.assertIn('if p == "/waiting":', SRC)
        self.assertIn("_waiting_page()", SRC)
        # the sheet is read live, like fleet-pane.css; a missing one fails loudly on the page, never blank
        css = (Path(BIN).parent / "ui" / "webview" / "waiting-pane.css").read_text()
        self.assertIn(css.splitlines()[-1], page)
        with mock.patch.object(Path, "read_text", side_effect=OSError("gone")):
            self.assertIn("needs the ui/ modules", km._waiting_page())


class Shell(unittest.TestCase):
    """The dashboard grows a fifth pane: the far-right column after Feed, OFF by default (the feature it
    shows is off by default), with its own gutter, grow var, and every hand-written pane list in the
    landing JS extended — focus ring, Alt+Arrow columns, Esc wiring, the Log's pane names, the mobile
    tab map, the pane controller. One label, "Waiting on you", from _PANE_ORDER (parity test)."""

    def setUp(self):
        self.html = km._landing()

    def test_the_pane_is_in_the_one_ordering_after_feed(self):
        self.assertEqual(km._PANE_ORDER[-2], ("waiting", "Waiting"))   # the Files pane (2026-09-03) sits after it
        self.assertIn("<div class=rail-btn data-pane=waiting>Waiting</div>", self.html)
        self.assertIn("<button data-pane=waiting>Waiting</button>", self.html)

    def test_the_column_sits_after_feed_with_its_gutter_and_grow_var(self):
        self.assertIn('<div class=gv id=gv-c></div><div class=pane id=waiting-pane><iframe id=f-waiting src=/waiting></iframe></div>',
                      self.html.replace('"\n            "', ""))
        self.assertLess(self.html.index("id=feed-pane"), self.html.index("id=gv-c"))
        self.assertLess(self.html.index("id=gv-c"), self.html.index("id=waiting-pane"))
        self.assertLess(self.html.index("id=waiting-pane"), self.html.index("id=gh"), "before the timeline band")
        self.assertIn("#waiting-pane{flex:var(--g-waiting,34) 1 0}", self.html)
        self.assertIn("body:not(.po-waiting) #waiting-pane{display:none}", self.html)
        self.assertIn("body:not(.po-waiting) #gv-c,body:not(.po-chat):not(.po-fleet):not(.po-feed) #gv-c{display:none}", self.html)

    def test_off_by_default_and_toggled_by_the_controller(self):
        self.assertIn("<body class='po-chat po-feed po-timeline'>", self.html)   # not po-waiting
        self.assertIn("po={chat:true,fleet:false,feed:true,timeline:true,waiting:false,files:false}", self.html)
        self.assertIn("po={chat:false,fleet:false,feed:false,timeline:false,waiting:false,files:false}", self.html)   # the ?panes= reset
        self.assertIn("document.body.classList.toggle('po-waiting',!!po.waiting)", self.html)
        self.assertIn("waiting:'Waiting pane'", self.html)   # the rail tooltip's words

    def test_every_pane_list_in_the_landing_js_names_it(self):
        self.assertIn("'f-waiting':'waiting-pane'", km._LANDING_FOCUS_JS)
        self.assertIn("var COLS=['f-chat','f-fleet','f-feed','f-waiting','f-files']", km._LANDING_FOCUS_JS)
        self.assertIn("['f-chat','f-fleet','f-feed','f-waiting','f-files','f-timeline'].forEach", self.html)   # Esc wiring
        self.assertIn("waiting:'Waiting'", km._LANDING_ERRS_JS)   # the Log's connection-lost label
        self.assertIn("waiting:document.getElementById('f-waiting')", km._LANDING_MOBILE_JS)
        self.assertIn("var PANES=['chat-pane','fleet-pane','feed-pane','waiting-pane','files-pane'];", self.html)
        self.assertIn("grow={chat:60,fleet:34,feed:40,waiting:34,files:40}", self.html)
        self.assertIn("id==='feed-pane'?'feed':id==='waiting-pane'?'waiting':'files'", self.html)
        self.assertIn("gutter('gv-c',", self.html)

    def test_mobile_tab_and_the_palette_command(self):
        self.assertIn("#chat-pane,#fleet-pane,#feed-pane,#waiting-pane,#files-pane,#tl-pane{display:contents!important}", self.html)
        self.assertIn("#f-chat.m-on,#f-fleet.m-on,#f-feed.m-on,#f-waiting.m-on,#f-files.m-on{display:block}", self.html)
        pal = (Path(BIN).parent / "ui" / "webview" / "palette-main.ts").read_text()
        self.assertIn('["waiting", "waiting", "Waiting"]', pal)
        self.assertIn('"f-waiting"', pal)


if __name__ == "__main__":
    unittest.main()
