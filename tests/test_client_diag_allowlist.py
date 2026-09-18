#!/usr/bin/env python3
"""The clientDiag handler admits each surface's known top-level data keys and bounds the row (2026-09-18, the beacon
extension). The file used to take whatever a page posted, of any shape and size. Now: a key outside the surface's
allowlist (CLIENT_DIAG_KEYS) is dropped and said once on stderr per surface and key; a data that is not an object is
stored as null; every string value is cut at CLIENT_DIAG_STR_MAX characters at any depth; a row whose JSON runs past
CLIENT_DIAG_ROW_MAX bytes keeps its surface and what and carries {"capped": true, "bytes": N} as its data; the surface
and what strings are cut too. Today's rows (the collector's minute and slowframe, the shim's return, close and stale
rows) pass whole, so the desktop readers keep every key they depend on.

Drives the REAL Handler's WS dispatch (_dispatch_ws with a clientDiag message, the way the pane shim delivers one)
against a hermetic state directory. Synthetic fixtures only: a placeholder dashboard id, invented numbers."""
import contextlib
import io
import json
import os
import pathlib
import tempfile
import unittest
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")

# Hermetic state BEFORE the loads — they resolve their state root at import time, and only pytest runs
# conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
load_source("romp_event_model", os.path.join(BIN, "romp-event-model"))
load_source("romp_judge", os.path.join(BIN, "romp-judge"))
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
km = load_source("romp_kernel_cdiag_allow", os.path.join(BIN, "romp-kernel"))

WID = "11111111-2222-3333-4444-555555555555"

# a minute row as ui/webview/perf-telemetry.ts builds it today (perf-telemetry.test.ts pins the same keys)
MINUTE = {"app": "chat", "since": 1700000000000, "span_ms": 60000,
          "frames": {"session": {"n": 12, "ms_sum": 340.5, "ms_max": 88.1, "n16": 5, "n100": 0, "hist": [0] * 14}},
          "free": {"n": 3, "p50": 12.5, "p90": 40, "max": 41.2},
          "loaf": {"n": 1, "blocking_ms": 60, "worst_ms": 110, "top": [{"k": "render.js:paintAll@9000", "ms": 90, "n": 1, "inv": "WebSocket.onmessage"}], "src": "loaf"},
          "slow": {"sent": 1, "suppressed": 0, "suppressed_worst_ms": 0},
          "dom": 53306, "visible": True, "hidden_pane": False, "ua": "safari-ios", "heap_mb": 210.4}
# the shared fields the same row carries when the gear's share switch is on
SHARED = {"nav": {"type": "reload", "responseEnd": 210, "domContentLoaded": 656, "loadEventEnd": 0},
          "res": {"feed.js": {"transferSize": 120000, "encodedBodySize": 119700, "duration": 88}, "other": {"transferSize": 600, "encodedBodySize": 400, "duration": 45}},
          "marks": {"wsOpen": 121, "bundleReady": 300, "firstFrame": 455, "fp": 388, "fcp": 402},
          "env": {"standalone": True, "iosMajor": 17, "touch": True, "vw": 390, "vh": 664, "dpr": 3, "entryTypes": ["paint", "resource", "navigation"], "ric": False, "dv": 1757100000},
          "vis": {"hiddenN": 1, "visibleN": 1, "hiddenMs": 30000}, "wsBytes": 12345, "rafGap": {"n": 2, "worst": 120}}


class ClientDiagAllowlistTest(unittest.TestCase):
    def setUp(self):
        # A private state root (T282): km.jd is the judge module every test module shares, and its STATE is whatever
        # the last module left. A minted state root pins per-session hosts off (the repo rule of 2026-09-11).
        self._saved_state = km.jd.STATE
        self._td = tempfile.TemporaryDirectory()
        root = pathlib.Path(self._td.name)
        (root / "session-hosts").write_text("off\n", encoding="utf-8")
        km.jd._rebind_state(root)
        self.fp = km.jd.STATE / "client-diag.jsonl"
        km._client_diag_said.clear()    # the once-per-kernel stderr latch: each test is its own kernel

    def tearDown(self):
        km._client_diag_said.clear()
        km.jd._rebind_state(self._saved_state)
        self._td.cleanup()

    def post(self, surface, what, data):
        """One row through the real dispatch, the way a pane's shim delivers it; returns what the kernel said on stderr."""
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            km.Handler._dispatch_ws(None, {"type": "clientDiag", "surface": surface, "what": what, "data": data}, {"wid": WID})
        return err.getvalue()

    def rows(self):
        return [json.loads(line) for line in self.fp.read_text(encoding="utf-8").splitlines() if line.strip()]

    def test_the_constants_and_the_table(self):
        self.assertEqual(km.CLIENT_DIAG_STR_MAX, 64)
        self.assertEqual(km.CLIENT_DIAG_ROW_MAX, 8 * 1024)
        self.assertEqual(sorted(km.CLIENT_DIAG_KEYS), ["chat", "federation", "feed", "kernel", "outline", "pane-shim", "perf", "reload-core", "shell", "strip", "waiting"])
        for surface, keys in km.CLIENT_DIAG_KEYS.items():
            self.assertIsInstance(keys, frozenset, surface)
            self.assertTrue(all(isinstance(k, str) and k for k in keys), surface)
        self.assertTrue(set(MINUTE) <= km.CLIENT_DIAG_KEYS["perf"], "every key of today's minute row is admitted")
        self.assertTrue(set(SHARED) <= km.CLIENT_DIAG_KEYS["perf"], "and every shared field")
        self.assertTrue({"app", "type", "ms", "dom", "loaf"} <= km.CLIENT_DIAG_KEYS["perf"], "the slowframe row's keys")

    def test_todays_rows_pass_whole_and_quietly(self):
        err = self.post("perf", "minute", MINUTE)
        err += self.post("perf", "slowframe", {"app": "chat", "type": "session", "ms": 150.2, "dom": 53306, "loaf": {"ms": 160, "blocking_ms": 110, "top": []}})
        err += self.post("pane-shim", "wsclose", {"app": "feed", "code": 1006, "reason": "", "wasClean": False, "sinceOpenMs": 5000, "quietMs": 31000, "everConnected": True, "bundleReady": True})
        err += self.post("pane-shim", "return", {"decision": "redial-closed", "resumed": False, "hiddenMs": 29000, "frozenMs": 0, "quietMs": 29500, "quietAtResumeMs": -1, "ready": 3, "app": "chat", "resent": True})
        err += self.post("pane-shim", "return-fresh", {"ms": 5600, "bytesSince": 40000, "redialed": True, "app": "chat"})
        err += self.post("pane-shim", "wsconnfail", {"app": "chat", "attempts": 3, "firstFailMs": 30000})
        err += self.post("pane-shim", "page-load", {"wasDiscarded": True, "nav": "reload", "app": "feed"})
        err += self.post("pane-shim", "watchdog-close", {"app": "feed", "why": "quiet", "ready": 1, "quietMs": 31000, "hidden": False})
        err += self.post("reload-core", "held", {"reason": "fresh", "detail": "", "hold": "fresh", "ageMs": 61000})
        self.assertEqual(err, "", "nothing dropped, nothing said")
        rows = self.rows()
        self.assertEqual(len(rows), 9)
        self.assertEqual(sorted(rows[0]), ["data", "reconnect", "surface", "t", "what", "wid"], "the row's own shape is unchanged")
        self.assertEqual(rows[0]["data"], MINUTE)
        self.assertEqual(rows[2]["data"]["reason"], "")
        self.assertEqual(rows[3]["data"]["resent"], True)

    def test_every_surface_in_the_table_admits_every_key_it_names(self):
        for surface, keys in sorted(km.CLIENT_DIAG_KEYS.items()):
            data = {k: i for i, k in enumerate(sorted(keys))}
            err = self.post(surface, "probe", data)
            self.assertEqual(err, "", surface)
            self.assertEqual(self.rows()[-1]["data"], data, surface)

    def test_the_shared_fields_pass_and_an_unknown_key_is_dropped_and_said_once(self):
        data = dict(MINUTE, **SHARED)
        data["typed"] = "what the user wrote"
        data["sid"] = "11111111-2222-3333-4444-555555555555"
        err = self.post("perf", "minute", data)
        row = self.rows()[0]["data"]
        self.assertEqual(row, dict(MINUTE, **SHARED), "the admitted keys, the shared fields among them; the two foreign keys gone")
        lines = [l for l in err.splitlines() if l]
        self.assertEqual(len(lines), 2, err)
        self.assertTrue(any("'typed'" in l and "'perf'" in l for l in lines), err)
        self.assertTrue(any("'sid'" in l for l in lines), err)
        self.assertTrue(all(l.startswith("[client-diag] dropping a key the surface's allowlist does not admit") for l in lines), err)
        # the same keys again, from another minute: said already
        self.assertEqual(self.post("perf", "minute", data), "")
        # a different foreign key: its own line, once
        self.assertEqual(len(self.post("perf", "minute", dict(MINUTE, other_thing=1)).splitlines()), 1)
        self.assertEqual(self.post("perf", "minute", dict(MINUTE, other_thing=2)), "")
        self.assertEqual(len(self.rows()), 4)

    def test_strings_are_cut_at_the_cap_at_any_depth(self):
        long = "x" * 200
        self.post("pane-shim", "wsclose", {"app": "feed", "code": 1006, "reason": long, "wasClean": False, "sinceOpenMs": 1, "quietMs": 1, "everConnected": True, "bundleReady": True})
        row = self.rows()[-1]["data"]
        self.assertEqual(row["reason"], "x" * 64)
        self.assertEqual(row["code"], 1006)
        self.assertIs(row["wasClean"], False)
        nested = dict(MINUTE, loaf={"n": 1, "blocking_ms": 1, "worst_ms": 1, "src": "loaf",
                                    "top": [{"k": "a" * 100, "ms": 1, "n": 1, "inv": "b" * 70}]})
        self.post("perf", "minute", nested)
        top = self.rows()[-1]["data"]["loaf"]["top"][0]
        self.assertEqual(top["k"], "a" * 64)
        self.assertEqual(top["inv"], "b" * 64)
        self.assertEqual(top["ms"], 1)
        # the dict's own keys are not values and stay whole (the row cap bounds them); null stays null
        self.post("perf", "minute", dict(MINUTE, frames={"k" * 70: {"n": 1}}, free=None))
        d = self.rows()[-1]["data"]
        self.assertEqual(list(d["frames"]), ["k" * 70])
        self.assertIsNone(d["free"])

    def test_nesting_past_the_depth_cap_reads_null(self):
        deep = 1
        for _ in range(20):
            deep = [deep]
        self.post("perf", "minute", dict(MINUTE, frames=deep))
        v = self.rows()[-1]["data"]["frames"]
        depth = 0
        while isinstance(v, list):
            v = v[0]
            depth += 1
        self.assertIsNone(v)
        self.assertEqual(depth, km.CLIENT_DIAG_DEPTH_MAX, "lists at depths 0 to the cap less one, then null")

    def test_a_row_over_the_cap_is_stored_capped_with_its_surface_and_what_and_said_once(self):
        big = dict(MINUTE, frames={"type%03d" % i: {"n": i, "ms_sum": 1.5, "ms_max": 2.5, "n16": 0, "n100": 0, "hist": [0] * 14} for i in range(200)})
        self.assertGreater(len(json.dumps(big)), km.CLIENT_DIAG_ROW_MAX)
        err = self.post("perf", "minute", big)
        self.assertEqual(len(err.splitlines()), 1, err)
        self.assertIn("is stored capped", err)
        row = self.rows()[-1]
        self.assertEqual(row["surface"], "perf")
        self.assertEqual(row["what"], "minute")
        self.assertEqual(row["wid"], WID)
        self.assertIn("reconnect", row)
        self.assertEqual(sorted(row["data"]), ["bytes", "capped"])
        self.assertIs(row["data"]["capped"], True)
        self.assertGreater(row["data"]["bytes"], km.CLIENT_DIAG_ROW_MAX)
        self.assertLess(len(json.dumps(row)), 400, "the stored row is small")
        self.assertEqual(self.post("perf", "minute", big), "", "said once per surface and what")
        self.assertEqual(len(self.post("perf", "slowframe", dict(big, type="x", ms=1)).splitlines()), 1, "another what: its own line")
        # a row just under the cap passes whole
        near = dict(MINUTE, frames={"type%03d" % i: {"n": i, "hist": [0] * 14} for i in range(90)})
        line = json.dumps({"t": 1700000000, "wid": WID, "surface": "perf", "what": "minute", "reconnect": False, "data": near})
        self.assertLess(len(line), km.CLIENT_DIAG_ROW_MAX)
        self.assertEqual(self.post("perf", "minute", near), "")
        self.assertEqual(self.rows()[-1]["data"], near)

    def test_data_that_is_not_an_object_reads_null_and_an_unknown_surface_keeps_no_key(self):
        err = self.post("perf", "minute", "a string where an object goes")
        self.assertIsNone(self.rows()[-1]["data"])
        self.assertEqual(len(err.splitlines()), 1, err)
        self.assertIn("not an object", err)
        self.assertEqual(self.post("perf", "minute", ["a", "list"]), "", "said once per surface")
        self.assertIsNone(self.rows()[-1]["data"])
        self.assertEqual(self.post("perf", "minute", None), "", "a missing data is stored as null and is nothing to say")
        self.assertIsNone(self.rows()[-1]["data"])
        err = self.post("mystery", "probe", {"a": 1, "b": "two"})
        self.assertEqual(self.rows()[-1]["data"], {})
        lines = err.splitlines()
        self.assertEqual(len(lines), 2, err)
        self.assertTrue(all("a surface no allowlist names" in l and "'mystery'" in l for l in lines), err)
        self.assertEqual(self.post("mystery", "probe", {"a": 3}), "", "said once per surface and key")

    def test_the_surface_and_what_strings_are_cut_too(self):
        self.post("s" * 100, "w" * 100, {"a": 1})
        row = self.rows()[-1]
        self.assertEqual(row["surface"], "s" * 64)
        self.assertEqual(row["what"], "w" * 64)
        self.assertEqual(row["data"], {})


if __name__ == "__main__":
    unittest.main()
