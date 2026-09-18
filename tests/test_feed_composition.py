#!/usr/bin/env python3
"""memos.feedComposition on GET /perf (2026-09-18): what the feed frame is made of, and what each pane would receive if
it were sent only the fields it reads.

One feed frame (about 8.8 MB on a busy board) goes whole to every client that rides the feed slot: the feed pane, the
Outline (app `fleet`) and the Waiting-on-you pane (app `waiting`). feed.ts reads no ledgers, waiting.ts reads three of
the frame's fields, fleet.ts the ledgers and a few fields of each card, and nothing said how the frame's bytes divided.
The kernel now accounts for the frame at the pusher's per-entry encode (_feed_parts): the cards' and ledgers' strings as
the size estimate already summed them, and the remainder encoded per field and joined into the one sort_keys string it
always was, byte for byte, so every field's bytes come from the frame's own encode, with no second encode and no
change to any frame. Per consuming app the block projects the bytes of the fields FEED_APP_FIELDS says it reads, a
checked-in table pinned here against the bundles' source both ways, beside the whole frame it receives today.

Pinned here: (a) on a served kernel the block is on GET /perf, its parts sum to its frame figure exactly and that
figure sits under the frame the client received by no more than the stated tolerance (the tints, key names and
separators the estimate does not count), `wire` is the exact body once a whole frame went, and every key is an
identifier over integer leaves; (b) the per-app table matches the readers' source both ways, for the frame's fields,
for the Outline's card fields and for the field federation.ts consumes on a pane's behalf (clearedForeign, read off the
local frame by mergeHostFeeds; applyViewerClears rewrites the merged cards and the ledgers from it, so the two panes
that read those carry it), and the frame-fields list matches a built frame, the off frame and the views fault marker;
(c) a synthetic build with a known ledger share projects the expected bytes per app, a ledgers refill re-sizes only the
ledgers, and the lifetime sums accumulate; (d) the remainder's per-field encode is byte for byte the
whole sort_keys encode, and a build encodes each card, ledger and remainder field once and a refill no card; (e) the
`phoneFace` projection row (FEED_PROJECTIONS) beside the readers' rows sizes a frame that does not exist yet, a phone
client's feed slot carrying a face per active card (the address, the title, the state and the age: fields feed.ts
reads off a card today) plus one summary row per session with a card: on the 60-card fixture it sits far below the feed
row, a fixture with every card active projects more than one with none, and the reader pin skips the row, with no bundle
to pin it against.

Synthetic only: the notes-api demo world, TESTHOST, placeholder ids."""
import base64
import io
import json
import os
import re
import socket
import struct
import tempfile
import threading
import time
import unittest
import urllib.request
from contextlib import redirect_stderr
from http.server import ThreadingHTTPServer
from unittest import mock
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
WEBVIEW = os.path.join(ROOT, "ui", "webview")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the loads: the modules resolve their state root at import, and a root minted here is outside
# conftest's belt, so session hosts are switched off in it too.
_ROOT = tempfile.mkdtemp()
os.environ["XDG_STATE_HOME"] = _ROOT
os.environ.pop("ROMP_STATE_DIR", None)
os.makedirs(os.path.join(_ROOT, "romp"), exist_ok=True)
with open(os.path.join(_ROOT, "romp", "session-hosts"), "w") as _fh:
    _fh.write("off")
km = load_source("romp_kernel_feedcomp", os.path.join(BIN, "romp-kernel"))

SID = "11111111-2222-3333-4444-555555555555"
SID_B = "11111111-2222-3333-4444-666666666666"
NOW = 1781100000
# The frame's size estimate counts the per-card strings minus their tints, the per-ledger strings and the remainder;
# the served body adds the frame's key names and separators and a tint per card and per tree node (about 20 bytes
# each). The fixture card below is about 2 KB with seven tints, so the estimate sits 7 to 9 percent under the body;
# the live board's cards are larger and the gap smaller. The tolerance is the stated bound on that gap.
FRAME_TOLERANCE = 0.15
VOLATILE = {"type", "now", "buildId"}


def _card(i, now=NOW, provisional=False, **over):
    t = now - i * 60
    c = {"itemId": "%s:g%d" % (SID, i), "sid": SID, "name": "web", "color": {"bg": "#123456", "fg": "#ffffff"},
         "text": "Synthetic goal %d on the notes-api board" % i, "t": t, "live": True,
         "trgb": list(km.cm.age_rgb(now - t)), "turnId": "%s:g%d" % (SID, i), "column": "working",
         "summary": None if provisional else "s" * 400, "blockSummary": None,
         "background": None if provisional else "b" * 300, "notify": True,
         "tree": [] if provisional else [{"id": "%s:g%d.%d" % (SID, i, j), "text": "step %d" % j, "status": "done",
                                          "t": t, "last": t, "trgb": list(km.cm.age_rgb(now - t)), "children": []}
                                         for j in range(6)]}
    if provisional:
        c["provisional"] = True
    c.update(over)
    return c


def _ledger(sid=SID, name="web", tops=3):
    return {"sid": sid, "name": name, "color": None, "status": {"state": "working"},
            "ledger": {"tops": ["t" * 2000] * tops}}


def _feed(n=40, now=NOW, build_id=1, asks=None, ledgers=None, **top):
    f = {"type": "feed", "now": now, "buildId": build_id,
         "asks": asks if asks is not None else [_card(i, now=now, provisional=(i % 10 == 9)) for i in range(n)],
         "order": [SID, SID_B], "working": ["web"], "awaiting": ["api"], "stateUnknown": [], "bgServices": {},
         "sessions": [{"sid": SID, "name": "web", "color": None, "githubRepo": None},
                      {"sid": SID_B, "name": "api", "color": None, "githubRepo": "example/notes-api"}],
         "userTodos": {SID: 1},
         "userTodoRows": [{"sid": SID, "name": "web", "color": None,
                           "todos": [{"id": "ut-1", "text": "Decide the response shape", "createdT": now - 100}]}],
         "userTodosOn": True, "judgeLimit": None,
         "views": {"seq": 3, "tags": {"backend": ["web", "api"], "alpha": {"z": 1, "a": 2}}},
         "dismissedCount": 2, "showDismissed": False, "clearedForeign": [], "canUndoClear": True,
         "clearNotices": [], "sdkNotices": [], "syncNotices": [{"sig": "s1", "text": "pulled 3 commits"}],
         "selfHost": "TESTHOST"}
    f["ledgers"] = [_ledger(), _ledger(SID_B, "api", tops=1)] if ledgers is None else ledgers
    f.update(top)
    return f


def _rest_of(feed):
    return {k: v for k, v in feed.items() if k not in ("type", "asks", "ledgers") and k not in km._DEDUP_VOLATILE}


def _expected(feed):
    """The parts' sizes computed here, apart from the kernel: the tint-stripped cards, the ledgers and the remainder per
    field (its quoted name, the separators, its sort_keys value)."""
    cards = sum(len(json.dumps(km._strip_trgb(a))) for a in feed["asks"])
    leds = sum(len(json.dumps(l)) for l in feed.get("ledgers") or [])
    by = {k: len(json.dumps(k)) + 4 + len(json.dumps(v, sort_keys=True)) for k, v in _rest_of(feed).items()}
    return cards, leds, by


def _leaves(v, path=""):
    if isinstance(v, dict):
        for k, x in v.items():
            yield from _leaves(x, path + "." + str(k))
    elif isinstance(v, (list, tuple)):
        for x in v:
            yield from _leaves(x, path + "[]")
    else:
        yield path, v


def _connect(port, query):
    """A browser-style client socket to the kernel's /ws?`query`; returns (socket, leftover bytes)."""
    key = base64.b64encode(os.urandom(16)).decode()
    req = ("GET /ws?%s&token=%s HTTP/1.1\r\nHost: 127.0.0.1:%d\r\nOrigin: http://127.0.0.1:%d\r\n"
           "Upgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: %s\r\n"
           "Sec-WebSocket-Version: 13\r\n\r\n") % (query, km.TOKEN, port, port, key)
    s = socket.create_connection(("127.0.0.1", port), timeout=10)
    s.sendall(req.encode())
    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = s.recv(65536)
        if not chunk:
            raise RuntimeError("closed during the handshake")
        buf += chunk
    head, buf = buf.split(b"\r\n\r\n", 1)
    if not head.startswith(b"HTTP/1.1 101"):
        raise RuntimeError(head[:80])
    return s, buf


def _read_frame(s, buf):
    """One server frame (unmasked) -> (opcode, payload, leftover)."""
    def need(n):
        nonlocal buf
        while len(buf) < n:
            chunk = s.recv(1 << 20)
            if not chunk:
                raise RuntimeError("socket closed")
            buf += chunk
    need(2)
    ln = buf[1] & 0x7F
    off = 2
    if ln == 126:
        need(4)
        ln = struct.unpack(">H", buf[2:4])[0]
        off = 4
    elif ln == 127:
        need(10)
        ln = struct.unpack(">Q", buf[2:10])[0]
        off = 10
    need(off + ln)
    return buf[0] & 0x0F, buf[off:off + ln], buf[off + ln:]


def _registered(wid, deadline_s=5):
    deadline = time.time() + deadline_s
    while time.time() < deadline:
        with km._clients_lock:
            client = next((c for c in km._clients if c.get("wid") == wid), None)
        if client is not None:
            return client
        time.sleep(0.005)
    raise AssertionError("the socket %s was not registered" % wid)


class ServedBlock(unittest.TestCase):
    """(a): a served kernel, a feed page on a real socket, a pusher cycle, GET /perf."""

    def _get(self, port, path):
        req = urllib.request.Request("http://127.0.0.1:%d%s" % (port, path),
                                     headers={"X-Romp-Token": os.environ["ROMP_SERVE_TOKEN"]})
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read().decode())

    def test_the_block_is_served_and_its_parts_sum_to_the_frame_the_client_received(self):
        fixture = _feed(n=60)
        saved = (km.build_feed, km._feed_wire, list(km._built_feed))
        km.build_feed = lambda now, live: dict(fixture, now=now)
        km._feed_wire = None
        km._built_feed[:] = [None, None, 0.0, 0.0]
        srv = ThreadingHTTPServer(("127.0.0.1", 0), km.Handler)
        port = srv.server_address[1]
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        s = None
        passes0 = km._FEED_COMP.report()["passes"]
        try:
            s, buf = _connect(port, "app=feed&wid=wfc1&caps=feedDelta")
            _registered("wfc1")
            err = io.StringIO()
            with redirect_stderr(err):
                km._push_all()                                   # the pusher's cycle: the build, the per-entry pass, the send
            received = None
            deadline = time.time() + 10
            while received is None and time.time() < deadline:   # the caps and tab-order frames come first
                op, payload, buf = _read_frame(s, buf)
                if op != 0x1:
                    continue
                if payload.startswith(b'{"now": ') and b'"type": "feed"' in payload:
                    received = payload
            self.assertIsNotNone(received, "the page received a whole feed frame")
            frame = json.loads(received)
            self.assertEqual(frame["type"], "feed")
            self.assertEqual(len(frame["asks"]), 60)
            self.assertEqual(len(frame["ledgers"]), 2)
            status, snap = self._get(port, "/perf")
            self.assertEqual(status, 200)
            block = snap["memos"]["feedComposition"]            # fails before: no such block
            self.assertEqual(block["passes"], passes0 + 1, "one per-entry pass for the one build")
            self.assertEqual(block["failed"], 0)
            last = block["last"]
            self.assertEqual(last["cards"] + last["ledgers"] + last["rest"], last["frame"], "the parts sum to the frame figure")
            self.assertEqual(sum(last["by"].values()), last["rest"], "the remainder's fields sum to the remainder")
            self.assertEqual((last["cardCount"], last["ledgerCount"], last["ledgersAttached"]), (60, 2, 1))
            n = len(received)
            self.assertLessEqual(last["frame"], n, "the estimate never exceeds the frame")
            gap = (n - last["frame"]) / n
            self.assertLessEqual(gap, FRAME_TOLERANCE,
                                 "the frame figure sits under the received frame (%d B) by %.1f%%: the tints, key names "
                                 "and separators it does not count, bounded by %.0f%%" % (n, 100 * gap, 100 * FRAME_TOLERANCE))
            # `wire` is the served body's exact length: the received frame is the body with the clock spliced in front
            self.assertEqual(block["wire"]["exact"], 1, "a whole frame went, so the body is materialized")
            self.assertEqual(block["wire"]["bytes"], n - 9 - len(json.dumps(frame["now"])))
            self.assertGreaterEqual(block["wire"]["bytes"], last["frame"])
            for app in ("feed", "fleet", "waiting", "phoneFace"):
                self.assertEqual(last["apps"][app]["today"], last["frame"], app)
                self.assertLess(last["apps"][app]["projected"], last["frame"], app)
            # the projection row rides `apps` beside the readers' rows (fails before: no such row); its `today` is the
            # fleet row's, the whole frame a phone's Outline receives now (it dials as fleet on every layout, its feed
            # page as feed), so the row reads as the saving
            self.assertEqual(last["apps"]["phoneFace"]["today"], last["apps"]["fleet"]["today"])
            self.assertLess(last["apps"]["phoneFace"]["projected"], last["apps"]["fleet"]["projected"])
            self.assertLess(last["apps"]["waiting"]["projected"], last["rest"], "waiting reads three remainder fields")
            self.assertEqual(last["apps"]["feed"]["projected"], last["frame"] - last["ledgers"] - last["by"]["userTodoRows"]
                             - last["by"]["userTodosOn"],
                             "the feed pane reads everything but the ledgers and the Waiting-on-you pane's two fields")
            for k in block["lifetime"]:
                if k not in ("by", "apps"):
                    self.assertGreaterEqual(block["lifetime"][k], last[k], k)
            # paste-safe: identifier keys, integer leaves, and the whole snapshot serializes
            for path, leaf in _leaves(block):
                self.assertIsInstance(leaf, int, "%s = %r" % (path, leaf))
                self.assertNotIsInstance(leaf, bool, path)
            keys = set()

            def walk(v):
                if isinstance(v, dict):
                    for k, x in v.items():
                        keys.add(k)
                        walk(x)
            walk(block)
            bad = sorted(k for k in keys if not km._PERF_IDENT.fullmatch(k))
            self.assertEqual(bad, [], "every key of the block is an identifier")
            json.dumps(snap)
        finally:
            if s is not None:
                s.close()
            srv.shutdown()
            srv.server_close()
            km.build_feed, km._feed_wire = saved[0], saved[1]
            km._built_feed[:] = saved[2]
            with km._clients_lock:
                km._clients[:] = [c for c in km._clients if c.get("wid") != "wfc1"]


class AppTable(unittest.TestCase):
    """(b): the checked-in table against the bundles' source, both ways, and the frame-fields list against the frames."""

    READERS = {"feed": "feed.ts", "fleet": "fleet.ts", "waiting": "waiting.ts"}

    @staticmethod
    def _src(name):
        with open(os.path.join(WEBVIEW, name), encoding="utf-8") as fh:
            return fh.read()

    @staticmethod
    def _fn(src, head):
        """The text of the top-level function whose declaration starts with `head`, to its closing brace."""
        start = src.index(head)
        return src[start:src.index("\n}", start)]

    def test_the_table_names_every_frame_field_each_reader_reads_and_nothing_else(self):
        table = km.FEED_APP_FIELDS                               # fails before: no table
        self.assertEqual(set(table), set(self.READERS), "one row per app that rides the feed slot")
        # The projection rows are NOT in the readers' table, and the pin below skips them: a projection sizes a frame
        # no bundle reads yet (phoneFace, the phone's face frame, decided 2026-09-18 and not built), so there is no
        # reader source to pin it against; the day a bundle reads one, its row moves into the table and the pin reads
        # it there. What CAN be pinned is the face itself: its five fields are fields every card carries and feed.ts
        # reads off a card today (it.<field>), so the face is drawn from the frame as it is, not from a wished-for card.
        self.assertEqual(set(km.FEED_PROJECTIONS), {"phoneFace"}, "one projection row today")
        self.assertNotIn("phoneFace", table,
                         "phoneFace is a projection of a frame that does not exist yet: no reader, so no reader pin")
        self.assertFalse(set(km.FEED_PROJECTIONS) & set(table), "a projection is never also a reader row")
        for app in km.FEED_PROJECTIONS:
            self.assertNotIn(app, self.READERS, "%s has no bundle to read against; the reader pin skips it" % app)
        self.assertEqual(km.FEED_PHONE_FACE_FIELDS, ("itemId", "sid", "text", "column", "t"),
                         "the face: the address (itemId, sid), the title (text), the state (column) and the age (t)")
        feed_src = self._src("feed.ts")
        for f in km.FEED_PHONE_FACE_FIELDS:
            self.assertTrue(re.search(r"\bit\??\.%s\b" % re.escape(f), feed_src),
                            "%s: a card field feed.ts reads off a card today" % f)
        self.assertEqual(set(km.FEED_PHONE_FACE_ACTIVE), {"working", "needs_input"},
                         "active is the Working and Blocked columns; Completed is not")
        self.assertIn('column: "working" | "needs_input" | "completed"', feed_src, "the card's column values, as feed.ts types them")
        # federation.js loads on every feed-slot page ahead of the pane's bundle and hands it the merged frame. Most
        # fields it merges through, and the pane's own read counts them; the fields it CONSUMES on the pane's behalf
        # are the local frame's fields mergeHostFeeds reads by name (clearedForeign: applyViewerClears drops the remote
        # cards and strikes the remote ledger tops the local ledger cleared). A pane that reads a field the consumer
        # rewrites receives the consumed field's effect, so its row carries the field; a pane that reads none of the
        # rewritten fields does not (fails before: the feed and fleet rows lacked clearedForeign).
        fed = self._src("federation.ts")
        consumed = set(re.findall(r"\blocal\??\.(\w+)", self._fn(fed, "export function mergeHostFeeds("))) \
            & set(km.FEED_FRAME_FIELDS)
        clears = self._fn(fed, "export function applyViewerClears(")
        rewrites = set(re.findall(r"\bmerged\.(\w+) = ", clears)) & set(km.FEED_FRAME_FIELDS)
        if "ledgers[i] = " in clears:
            rewrites.add("ledgers")
        self.assertTrue(consumed, "mergeHostFeeds reads a frame field off the local frame by name")
        self.assertTrue(rewrites, "applyViewerClears rewrites a frame field of the merged frame")
        self.assertIn("clearedForeign", consumed)
        for app, fname in self.READERS.items():
            src = self._src(fname)
            reads = {f for f in km.FEED_FRAME_FIELDS if re.search(r"\bm\??\.%s\b" % re.escape(f), src)}
            via = consumed if reads & rewrites else set()
            top = {f.split(".", 1)[0] for f in table[app]}       # `asks.<field>` rows are a read of `asks`
            self.assertEqual(top, reads | via,
                             "%s: the table's top-level fields are exactly the frame fields %s reads off its frame "
                             "(m.<field>) plus the fields federation consumes for it (%s); table-only %s, "
                             "source-only %s"
                             % (app, fname, sorted(via), sorted(top - reads - via), sorted((reads | via) - top)))
            for f in top:
                self.assertIn(f, km.FEED_FRAME_FIELDS, "%s: %s names a frame field" % (app, f))
        # the Outline reads a few fields of each card (never the card): the provisional card's face in its frame handler
        # (a.<field>) and the goal card's distiller texts at the hover (ask.<field>, asksById)
        src = self._src("fleet.ts")
        start = src.index('if (m.type !== "feed") return;')
        handler = src[start:src.index("\n}));", start)]
        card_reads = set(re.findall(r"\ba\??\.(\w+)", handler)) | set(re.findall(r"\bask\??\.(\w+)", src))
        sub = {f[5:] for f in table["fleet"] if f.startswith("asks.")}
        self.assertEqual(sub, card_reads, "fleet: the table's card fields are the ones fleet.ts reads; table-only %s, "
                         "source-only %s" % (sorted(sub - card_reads), sorted(card_reads - sub)))
        self.assertNotIn("asks", table["fleet"], "the Outline never takes the cards whole")
        self.assertIn("asks", table["feed"], "the feed pane takes the cards whole")
        self.assertFalse(any(f.startswith("asks") for f in table["waiting"]), "waiting.ts reads no card")
        self.assertIsNone(re.search(r"\bm\??\.asks\b", self._src("waiting.ts")))

    def test_the_apps_are_the_send_stages_and_the_frame_fields_list_matches_the_frames(self):
        for app in km.FEED_APP_FIELDS:
            self.assertTrue(km._feed_audience([{"app": app}]), "%s rides the feed payload" % app)
        with open(os.path.join(BIN, "romp-kernel"), encoding="utf-8") as fh:
            ksrc = fh.read()
        stage = re.search(r'if c\["app"\] in \(([^)]*)\):\s*# the feed pane', ksrc)
        self.assertIsNotNone(stage, "the send stage's feed branch names its apps in one tuple")
        self.assertEqual(set(re.findall(r'"(\w+)"', stage.group(1))), set(km.FEED_APP_FIELDS),
                         "the table's apps are the send stage's")
        self.assertEqual(len(km.FEED_FRAME_FIELDS), len(set(km.FEED_FRAME_FIELDS)))
        err = io.StringIO()
        with redirect_stderr(err), mock.patch.object(km, "_alive_sessions", lambda now, tm: []), \
                mock.patch.object(km, "_warm_fleet_bg", lambda now: None), \
                mock.patch.object(km, "_sessions", lambda now, window=None, forks=True: []), \
                mock.patch.object(km, "_sdk", lambda: None):
            built = km.build_feed(NOW, {})
        self.assertEqual(sorted(set(built) - VOLATILE - set(km.FEED_FRAME_FIELDS)), [],
                         "every field of a built frame is in the list")
        off = km._feed_off_frame(NOW, {})
        self.assertIn("off", off)
        self.assertEqual(sorted(set(off) - VOLATILE - set(km._FEED_FRAME_LISTS) - set(km.FEED_FRAME_FIELDS)), [],
                         "every field of the off frame is in the list, its empty federation lists aside")
        with mock.patch.object(km, "_timeline_views_display", lambda: (None, RuntimeError("synthetic"))), \
                mock.patch.object(km, "_views_fault_text", lambda f: "tags unavailable: synthetic"):
            fault = km._views_payload()
        self.assertEqual(set(fault), {"viewsFault"})
        self.assertIn("viewsFault", km.FEED_FRAME_FIELDS)
        self.assertIn("ledgers", km.FEED_FRAME_FIELDS, "the pusher's attach")
        for f in km.FEED_FRAME_FIELDS:
            self.assertTrue(f in built or f in off or f == "viewsFault" or f == "ledgers", "%s is a frame field" % f)


class SyntheticBuild(unittest.TestCase):
    """(c) and (d): a synthetic build through the pusher's per-entry pass, in process."""

    def setUp(self):
        km._feed_cards_memo = None                               # a fresh build's pass: no memo from another test

    def test_a_synthetic_build_projects_the_expected_bytes_per_app(self):
        feed = _feed(n=40)
        cards, leds, by = _expected(feed)
        rep0 = km._feed_composition_report()                    # fails before: no report
        parts = km._feed_parts(feed)
        rep = km._feed_composition_report()
        last = rep["last"]
        self.assertEqual(rep["passes"], rep0["passes"] + 1)
        self.assertEqual(last["cards"], cards, "the cards' bytes: the tint-stripped per-card strings")
        self.assertEqual(last["ledgers"], leds, "the ledgers' bytes: the per-ledger strings, the known share")
        self.assertEqual(last["by"], by, "the remainder per field: quoted name, separators, sort_keys value")
        self.assertEqual(last["rest"], len(parts[3]))
        self.assertEqual(last["frame"], km._feed_est(parts), "the frame figure is the size estimate the wire uses")
        self.assertEqual(last["frame"], cards + leds + sum(by.values()))
        self.assertEqual((last["cardCount"], last["ledgerCount"], last["ledgersAttached"]), (40, 2, 1))
        apps = last["apps"]
        self.assertEqual(set(apps), {"feed", "fleet", "waiting", "phoneFace"}, "the readers' rows and the projection row")
        self.assertEqual(apps["phoneFace"], {"today": last["frame"], "projected": km._phone_face_est(feed["asks"])},
                         "the phone face projection: the whole frame today beside the face estimate over the build's cards")
        self.assertEqual(apps["waiting"], {"today": last["frame"],
                                           "projected": by["userTodoRows"] + by["userTodosOn"] + by["sessions"]},
                         "the Waiting-on-you pane reads its rows, the switch and the session list")
        self.assertEqual(apps["feed"]["projected"],
                         last["frame"] - leds - by["userTodoRows"] - by["userTodosOn"],
                         "the feed pane reads the cards and the remainder minus the two fields it never touches, no "
                         "ledgers; clearedForeign stays in, federation drops remote cards from it for the pane")
        fields = km._FEED_APP_ASK_FIELDS["fleet"]
        est = km._ask_fields_est(feed["asks"], fields)
        self.assertEqual(apps["fleet"]["projected"], leds + by["views"] + by["sessions"] + by["clearedForeign"] + est,
                         "the Outline reads the ledgers, the views, the session list, the viewer's foreign clears "
                         "(federation strikes remote ledger tops from them) and a few fields of each card")
        # the card-field estimate: the docstring's arithmetic, done again here over one goal card and one provisional
        # card, and bounded by the texts it counts and the cards it stands in for
        goal, prov = feed["asks"][0], feed["asks"][9]
        self.assertTrue(prov.get("provisional"))

        def one(card):
            n = 2
            for f in fields:
                if f not in card:
                    continue
                v = card[f]
                if isinstance(v, str):
                    n += len(f) + 8 + len(v)
                elif v is None:
                    n += len(f) + 6 + 4
                elif isinstance(v, bool):
                    n += len(f) + 6 + (4 if v else 5)
                else:
                    n += len(f) + 6 + len(repr(v))
            return n
        self.assertEqual(km._ask_fields_est([goal], fields), one(goal))
        self.assertEqual(km._ask_fields_est([prov], fields), one(prov))
        self.assertEqual(km._ask_fields_est([goal, prov, "not a card"], fields), one(goal) + one(prov))
        texts = sum(len(a[f]) for a in feed["asks"] for f in fields if isinstance(a.get(f), str))
        self.assertGreater(est, texts, "at least the texts it names")
        self.assertLess(est, cards, "and less than the cards whole")
        self.assertEqual(km._ask_fields_est([{"color": {"bg": "#123456", "fg": "#ffffff"}}], ("color",)),
                         2 + len("color") + 6 + len(json.dumps({"bg": "#123456", "fg": "#ffffff"})),
                         "a nested value at its repr's length, the JSON length for the frame's nested values")
        # a ledgers-only refill of the same build: the cards memo answers, the ledgers re-size, the projections move by
        # the ledgers alone, and the lifetime sums carry both passes
        refill = dict(feed)
        refill["ledgers"] = [_ledger(tops=5)]
        s0 = dict(km._wire_stats)
        km._feed_parts(refill)
        self.assertEqual(km._wire_stats["feed_cards_hit"], s0["feed_cards_hit"] + 1)
        rep2 = km._feed_composition_report()
        last2 = rep2["last"]
        leds2 = len(json.dumps(refill["ledgers"][0]))
        self.assertEqual((last2["cards"], last2["by"], last2["cardCount"]), (cards, by, 40))
        self.assertEqual((last2["ledgers"], last2["ledgerCount"]), (leds2, 1))
        self.assertEqual(last2["apps"]["fleet"]["projected"] - apps["fleet"]["projected"], leds2 - leds)
        self.assertEqual(last2["apps"]["waiting"]["projected"], apps["waiting"]["projected"])
        self.assertEqual(last2["apps"]["feed"]["projected"], apps["feed"]["projected"])
        self.assertEqual(last2["apps"]["phoneFace"]["projected"], apps["phoneFace"]["projected"],
                         "the face reads no ledger; its estimate is memoized with the cards, so a refill pays none of it")
        life, life0 = rep2["lifetime"], rep0["lifetime"]
        self.assertEqual(life["cards"] - life0["cards"], 2 * cards)
        self.assertEqual(life["ledgers"] - life0["ledgers"], leds + leds2)
        self.assertEqual(life["frame"] - life0["frame"], last["frame"] + last2["frame"])
        self.assertEqual(life["cardCount"] - life0["cardCount"], 80)
        for k, v in by.items():
            self.assertEqual(life["by"][k] - life0["by"].get(k, 0), 2 * v, k)
        for app in apps:
            self.assertEqual(life["apps"][app]["today"] - life0["apps"][app]["today"], last["frame"] + last2["frame"], app)
            self.assertEqual(life["apps"][app]["projected"] - life0["apps"][app]["projected"],
                             apps[app]["projected"] + last2["apps"][app]["projected"], app)
        # a build with no ledgers attached (a feed-only push): zero, said so, and no ledger bytes in any projection
        bare = _feed(n=3, build_id=3)
        del bare["ledgers"]
        km._feed_parts(bare)
        last3 = km._feed_composition_report()["last"]
        self.assertEqual((last3["ledgers"], last3["ledgerCount"], last3["ledgersAttached"]), (0, 0, 0))
        self.assertEqual(last3["frame"], last3["cards"] + last3["rest"])
        self.assertEqual(rep2["failed"], 0)

    def test_a_fresh_accumulator_reads_as_empty_dicts_and_zeros(self):
        fresh = km._FeedComposition()
        with mock.patch.object(km, "_feed_wire", None):
            rep = fresh.report()
        self.assertEqual(rep["passes"], 0)
        self.assertEqual(rep["failed"], 0)
        self.assertEqual(rep["last"], {})
        self.assertEqual(rep["wire"], {})
        self.assertEqual(rep["lifetime"]["by"], {})
        self.assertEqual(rep["lifetime"]["apps"],
                         {a: {"today": 0, "projected": 0} for a in (*km.FEED_APP_FIELDS, *km.FEED_PROJECTIONS)})
        for path, leaf in _leaves(rep):
            self.assertIsInstance(leaf, int, path)
        json.dumps(rep)
        # `wire` before any whole frame went: the estimate, said inexact
        feed = _feed(n=2)
        parts = km._feed_parts(feed)
        lazy = km._LazyWire(lambda: km._feed_body(feed), km._feed_est(parts), "feed_body")
        with mock.patch.object(km, "_feed_wire", (feed, feed["ledgers"], feed, lazy, km._feed_sig(parts), parts)):
            self.assertEqual(fresh.report()["wire"], {"bytes": km._feed_est(parts), "exact": 0})
            lazy.text()
            self.assertEqual(fresh.report()["wire"], {"bytes": len(km._feed_body(feed)), "exact": 1})

    def test_the_phone_face_projection_sits_far_below_the_feed_row_and_counts_the_active_cards(self):
        """(e): the 60-card, 2-ledger fixture (every card in the Working column, so every card active) against the
        feed row; the arithmetic done again here; the active set and the group rows on fixtures that move the column."""
        fields = km.FEED_PHONE_FACE_FIELDS
        feed = _feed(n=60)
        self.assertTrue(all(f in a for a in feed["asks"] for f in fields), "every fixture card carries the five face fields")
        km._feed_parts(feed)
        last = km._feed_composition_report()["last"]
        self.assertEqual((last["cardCount"], last["ledgerCount"]), (60, 2))
        face, full = last["apps"]["phoneFace"]["projected"], last["apps"]["feed"]["projected"]
        ratio = full / face
        self.assertGreaterEqual(ratio, 8,
                                "the face frame sits far below the feed row: %d B against the feed row's %d B (the "
                                "frame's %d B), a ratio of %.1f; bounded at 8" % (face, full, last["frame"], ratio))
        self.assertLess(face, last["apps"]["fleet"]["projected"], "and below the Outline's card fields plus ledgers")

        def one(card, fs):
            n = 2
            for f in fs:
                if f not in card:
                    continue
                v = card[f]
                n += len(f) + (8 + len(v) if isinstance(v, str) else 6 + len(repr(v)))
            return n
        # the arithmetic, done again here: a face per active card (five fields at their lengths), one summary row per
        # session with a card (its sid and the count of the cards it holds); the fixture's cards share one sid
        self.assertEqual(face, sum(one(a, fields) for a in feed["asks"]) + one({"sid": SID, "count": 60}, ("sid", "count")))
        # a fixture where every card is active projects more than one where none is: the same cards, the column moved
        # to completed, leave only the one summary row
        none = [_card(i, column="completed", provisional=(i % 10 == 9)) for i in range(60)]
        est_none = km._phone_face_est(none)
        self.assertEqual(est_none, one({"sid": SID, "count": 60}, ("sid", "count")), "no active card: the group row alone")
        self.assertGreater(km._phone_face_est(feed["asks"]), est_none)
        self.assertGreater(face, 50 * est_none, "sixty faces against one group row")
        # active is the Working and Blocked columns, whatever the card's kind; the groups are the sessions with a card
        mixed = ([_card(i, column="working") for i in range(10)]
                 + [_card(10 + i, column="needs_input", provisional=True) for i in range(5)]
                 + [_card(20 + i, column="completed") for i in range(20)]
                 + [_card(40 + i, sid=SID_B, column="completed" if i % 2 else "working") for i in range(4)])
        active = [a for a in mixed if a["column"] in ("working", "needs_input")]
        self.assertEqual(len(active), 17)
        self.assertEqual(km._phone_face_est(mixed),
                         sum(one(a, fields) for a in active)
                         + one({"sid": SID, "count": 35}, ("sid", "count")) + one({"sid": SID_B, "count": 4}, ("sid", "count")),
                         "seventeen faces and two group rows, every card counted in its group")
        self.assertEqual(km._phone_face_est([]), 0)
        self.assertEqual(km._phone_face_est(["not a card", 3]), 0)
        # the frame's own pips are session names, not card groups: moving a name between them moves no byte of the face
        moved = dict(feed, working=[], awaiting=["web"], stateUnknown=["api"])
        km._feed_cards_memo = None
        km._feed_parts(moved)
        self.assertEqual(km._feed_composition_report()["last"]["apps"]["phoneFace"]["projected"], face)

    def test_an_accounting_fault_is_counted_and_said_once_and_the_frame_is_unaffected(self):
        feed = _feed(n=2)
        err = io.StringIO()
        with mock.patch.object(km._FeedComposition, "record", side_effect=KeyError("synthetic")), redirect_stderr(err):
            parts = km._feed_parts(feed)
            failed = km._FEED_COMP.failed
            km._feed_parts(_feed(n=2, build_id=2))
        self.assertEqual(parts[3], json.dumps(_rest_of(feed), sort_keys=True), "the frame's remainder is the same bytes")
        self.assertEqual(km._FEED_COMP.failed - failed, 1)
        self.assertEqual(err.getvalue().count("feed composition: the accounting raised"), 1, "said once")

    def test_the_remainder_is_encoded_per_field_and_joined_byte_for_byte(self):
        odd = {"zeta": {"b": 1, "a": [3, 2, {"y": None, "x": True}]}, "alpha": "ünïcode ✓ \"quoted\" \\ back",
               "empty": {}, "none": None, "flt": 1.5, "neg": -7, "big": 10 ** 20, "lst": [], "t": True, "f": False,
               "nested": {"k2": {"z": 1, "a": 2}, "k1": ["a", {"b": 1}]}, "Upper": 1, "_under": 2, "a.dot": 3}
        for extra in (odd, {}, {"only": 1}):
            feed = _feed(n=2)
            for k in list(_rest_of(feed)):
                del feed[k]
            feed.update(extra)
            parts = km._feed_parts(feed)
            self.assertEqual(parts[3], json.dumps(extra, sort_keys=True), extra)
            self.assertEqual(parts[2], extra)
            last = km._feed_composition_report()["last"]
            self.assertEqual(last["rest"], len(parts[3]))
            self.assertEqual(sum(last["by"].values()), last["rest"] if extra else 0)
            self.assertEqual(set(last["by"]), set(extra))
        # a value json cannot encode meets the wire default once, as before, and its str() bytes are in the field
        feed = _feed(n=2)
        feed["extra"] = {"x"}
        s0 = dict(km._wire_stats)
        err = io.StringIO()
        with redirect_stderr(err):
            parts = km._feed_parts(feed)
        self.assertEqual(km._wire_stats["default_str"] - s0["default_str"], 1)
        self.assertEqual(parts[3], json.dumps(_rest_of(feed), sort_keys=True, default=str))
        self.assertEqual(km._feed_composition_report()["last"]["by"]["extra"], len('"extra": ') + len(json.dumps(str({"x"}))) + 2)
        # a key that is not a str (never the frame's case) takes the whole encode under one name: the same bytes for
        # keys json coerces, and the same TypeError the whole sort_keys encode always raised on keys it cannot order
        feed = _feed(n=2)
        for k in list(_rest_of(feed)):
            del feed[k]
        feed[7] = "seven"
        parts = km._feed_parts(feed)
        self.assertEqual(parts[3], json.dumps({7: "seven"}, sort_keys=True))
        self.assertEqual(km._feed_composition_report()["last"]["by"], {"other": len(parts[3])})
        mixed = _feed(n=2)
        mixed[7] = "seven"
        with self.assertRaises(TypeError):
            json.dumps(_rest_of(mixed), sort_keys=True)
        with self.assertRaises(TypeError):
            km._feed_parts(mixed)

    def test_a_build_encodes_each_part_once_and_a_refill_encodes_no_card(self):
        feed = _feed(n=12)
        real = km.json.dumps
        calls = []

        def counting(obj, *a, **kw):
            calls.append(obj)
            return real(obj, *a, **kw)
        with mock.patch.object(km.json, "dumps", side_effect=counting):
            km._feed_parts(feed)
        rest = _rest_of(feed)
        self.assertEqual(len(calls), 12 + len(feed["ledgers"]) + 2 * len(rest),
                         "one encode per card, per ledger, and per remainder field (its name and its value)")
        self.assertEqual(sum(1 for o in calls if isinstance(o, dict) and "itemId" in o), 12)
        calls.clear()
        refill = dict(feed)
        refill["ledgers"] = [_ledger(tops=1)]
        with mock.patch.object(km.json, "dumps", side_effect=counting):
            km._feed_parts(refill)
        self.assertEqual(len(calls), 1 + 2 * len(rest), "a refill encodes the ledgers and the remainder, no card")
        self.assertFalse(any(isinstance(o, dict) and "itemId" in o for o in calls))
        # the wire's signature and delta read the same strings as before
        self.assertEqual(km._feed_sig(km._feed_parts(feed))[0], json.dumps(rest, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
