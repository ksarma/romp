#!/usr/bin/env python3
"""client-diag.jsonl is bounded (2026-09-06): the pane bundles post a performance row per pane per active minute
(ui/webview/perf-telemetry.ts), about 1 KB each, into a file that used to hold rare breadcrumbs and that nothing
pruned. The kernel's clientDiag handler now rotates it past CLIENT_DIAG_MAX_BYTES: the file is renamed to
client-diag.jsonl.1 (replacing the previous .1) and a new file starts, so at most two files are ever kept, and
`romp perf client` reads both.

Drives the REAL Handler's WS dispatch (_dispatch_ws with a clientDiag message, the way the pane shim delivers
one) against a hermetic state directory, with the cap lowered for the test. Synthetic fixtures only: a
placeholder dashboard id, invented numbers."""
import json
import os
import tempfile
import unittest
from importlib.machinery import SourceFileLoader

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")

# Hermetic state BEFORE the loads — they resolve their state root at import time, and only pytest runs
# conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
SourceFileLoader("romp_event_model", os.path.join(BIN, "romp-event-model")).load_module()
SourceFileLoader("romp_judge", os.path.join(BIN, "romp-judge")).load_module()
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "test-token-DO-NOT-USE")
km = SourceFileLoader("romp_kernel_cdiag", os.path.join(BIN, "romp-kernel")).load_module()

WID = "11111111-2222-3333-4444-555555555555"


class ClientDiagRotationTest(unittest.TestCase):
    def setUp(self):
        self.fp = km.jd.STATE / "client-diag.jsonl"
        self.fp1 = km.jd.STATE / "client-diag.jsonl.1"
        for f in (self.fp, self.fp1):
            if f.exists():
                f.unlink()
        self.cap = km.CLIENT_DIAG_MAX_BYTES
        km.CLIENT_DIAG_MAX_BYTES = 600           # a handful of rows; the production value is asserted below

    def tearDown(self):
        km.CLIENT_DIAG_MAX_BYTES = self.cap
        for f in (self.fp, self.fp1):
            if f.exists():
                f.unlink()

    def post(self, i):
        """One breadcrumb through the real dispatch: what the shim sends for a pane's minute row."""
        km.Handler._dispatch_ws(None, {"type": "clientDiag", "surface": "perf", "what": "minute",
                                       "data": {"app": "feed", "i": i, "frames": {"feed": {"n": i}}}},
                                {"wid": WID})

    @staticmethod
    def rows(path):
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def test_a_row_lands_with_the_kernel_stamp(self):
        self.post(1)
        rows = self.rows(self.fp)
        self.assertEqual(len(rows), 1)
        self.assertEqual(sorted(rows[0]), ["data", "surface", "t", "what", "wid"])
        self.assertEqual(rows[0]["wid"], WID)
        self.assertEqual(rows[0]["surface"], "perf")
        self.assertEqual(rows[0]["what"], "minute")
        self.assertEqual(rows[0]["data"]["i"], 1)
        self.assertFalse(self.fp1.exists())

    def test_past_the_cap_the_file_rotates_to_dot_one_and_a_second_rotation_replaces_it(self):
        i = 0
        while not self.fp1.exists():
            i += 1
            self.post(i)
            self.assertLess(i, 100, "the cap never tripped")
        first = self.rows(self.fp1)
        self.assertGreaterEqual(sum(len(json.dumps(r)) + 1 for r in first), km.CLIENT_DIAG_MAX_BYTES,
                                "the rename happens only once the file is at the cap")
        self.assertEqual([r["data"]["i"] for r in first], list(range(1, i)), "the older rows moved whole")
        self.assertEqual([r["data"]["i"] for r in self.rows(self.fp)], [i], "the row that tripped it starts the new file")
        # keep going: the second rotation REPLACES .1 rather than stacking a .2
        n1 = i
        while self.rows(self.fp1)[0]["data"]["i"] == 1:
            i += 1
            self.post(i)
            self.assertLess(i, 200, "the second rotation never happened")
        second = self.rows(self.fp1)
        self.assertEqual(second[0]["data"]["i"], n1, "the .1 file is now the second run")
        self.assertEqual(self.rows(self.fp)[0]["data"]["i"], i)
        self.assertFalse((km.jd.STATE / "client-diag.jsonl.2").exists())
        # nothing is lost between the two files at any moment: every row is in exactly one
        seen = [r["data"]["i"] for r in second] + [r["data"]["i"] for r in self.rows(self.fp)]
        self.assertEqual(seen, list(range(n1, i + 1)))

    def test_the_production_cap_is_eight_megabytes(self):
        self.assertEqual(self.cap, 8 * 1024 * 1024)

    def test_a_rename_failure_still_appends(self):
        self.post(1)
        real = os.replace
        km.CLIENT_DIAG_MAX_BYTES = 1

        def refuse(*a, **k):
            raise OSError("read-only")
        os.replace = refuse
        try:
            self.post(2)
        finally:
            os.replace = real
        self.assertEqual([r["data"]["i"] for r in self.rows(self.fp)], [1, 2])
        self.assertFalse(self.fp1.exists())


if __name__ == "__main__":
    unittest.main()
