#!/usr/bin/env python3
"""The served drivers' one result reader refuses every record it cannot trust (2026-10-06).

tests/lab_result.py reads the record a served driver wrote through tests/lab_result.cjs: one RESULT: line on stdout
naming the drive's file and nonce, and the file holding {"nonce", "record"}. Each refusal is pinned here on synthetic
streams and files, so it runs in every Python job with no node and no browser: a line carrying another nonce, a file
carrying another nonce (a stale file an earlier drive left), a missing file, a write error the driver reported, a line
naming another file, no line, two lines, a line or a file that is not JSON, and a file with no record. Each refusal is
a ResultError, which is an AssertionError, and its message names the cause and carries both streams' tails. The happy
path returns the record whatever its JSON type (four drivers hand back arrays), from text or bytes streams.
The JS half writing what this reader reads is pinned by execution in tests/test_lab_result_pipe_served.py. And
tests/__init__.py registers the bare name lab_result, so a served module imports it at its top (a child interpreter).

Synthetic: no kernel, no browser, no node; the files live in a temp dir.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import types
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import lab_result                                   # noqa: E402


def proc(stdout, stderr=""):
    return types.SimpleNamespace(stdout=stdout, stderr=stderr)


def line(**fields):
    return "\n" + lab_result.PREFIX + json.dumps(fields) + "\n"


class ReaderRefusals(unittest.TestCase):
    def setUp(self):
        self.lab = tempfile.mkdtemp(prefix="lab-result-")
        self.addCleanup(shutil.rmtree, self.lab, True)
        self.tgt = lab_result.target(self.lab, "unit")

    def write_file(self, nonce, record=None, raw=None):
        with open(self.tgt["resultPath"], "w", encoding="utf-8") as f:
            f.write(raw if raw is not None else json.dumps({"nonce": nonce, "record": record}))

    def good_line(self, **extra):
        return line(resultPath=self.tgt["resultPath"], nonce=self.tgt["resultNonce"], **extra)

    def refused(self, p, *needles):
        with self.assertRaises(lab_result.ResultError) as cm:
            lab_result.read(p, self.tgt)
        msg = str(cm.exception)
        for n in needles:
            self.assertIn(n, msg)
        return msg

    def test_happy_path_returns_the_record(self):
        rec = {"ready": True, "rows": list(range(50)), "text": "a note for the api session"}
        self.write_file(self.tgt["resultNonce"], rec)
        self.assertEqual(lab_result.read(proc("progress\n" + self.good_line()), self.tgt), rec)

    def test_any_json_value_is_a_record(self):
        for rec in ([{"engine": "chromium"}, {"engine": "webkit"}], "ok", 0, None):
            self.write_file(self.tgt["resultNonce"], rec)
            self.assertEqual(lab_result.read(proc(self.good_line()), self.tgt), rec)

    def test_bytes_streams_read_the_same(self):
        self.write_file(self.tgt["resultNonce"], {"ok": 1})
        self.assertEqual(lab_result.read(proc(self.good_line().encode(), b"warn\n"), self.tgt), {"ok": 1})

    def test_a_died_record_is_returned_for_the_caller_to_judge(self):
        self.write_file(self.tgt["resultNonce"], {"died": "no tab for web"})
        r = lab_result.read(proc(self.good_line(died="no tab for web")), self.tgt)
        self.assertEqual(r, {"died": "no tab for web"})

    def test_a_line_with_another_nonce_is_refused(self):
        self.write_file(self.tgt["resultNonce"], {"ok": 1})
        p = proc(line(resultPath=self.tgt["resultPath"], nonce="0123456789abcdef"))
        self.refused(p, "carries nonce '0123456789abcdef'", self.tgt["resultNonce"])

    def test_a_line_with_no_nonce_is_refused(self):
        self.write_file(self.tgt["resultNonce"], {"ok": 1})
        self.refused(proc(line(resultPath=self.tgt["resultPath"])), "carries nonce None")

    def test_a_stale_file_is_refused(self):
        # the line is this drive's, and the file at the path is an earlier drive's: the nonce tells them apart
        self.write_file("0123456789abcdef", {"ok": "from the earlier drive"})
        self.refused(proc(self.good_line()), "a stale file", "'0123456789abcdef'")

    def test_a_missing_file_is_refused_with_the_died_reason(self):
        msg = self.refused(proc(self.good_line(died="browser closed"), "stack on stderr"), "wrote no result file",
                           self.tgt["resultPath"], "browser closed")
        self.assertIn("stack on stderr", msg, "the message carries the stderr tail")

    def test_a_write_error_is_refused(self):
        self.write_file(self.tgt["resultNonce"], {"ok": 1})   # even with a good file at the path: the driver said it failed
        p = proc(self.good_line(resultWriteError="ENOSPC: no space left on device", died="late"))
        self.refused(p, "could not write its record", "ENOSPC", "'late'")

    def test_a_line_naming_another_file_is_refused(self):
        self.write_file(self.tgt["resultNonce"], {"ok": 1})
        other = os.path.join(self.lab, "result-other.json")
        self.refused(proc(line(resultPath=other, nonce=self.tgt["resultNonce"])), "names %r" % other)

    def test_no_line_is_refused(self):
        self.write_file(self.tgt["resultNonce"], {"ok": 1})
        self.refused(proc("RESULT ok\nresult:{}\n", "boom"), "printed 0 RESULT: lines", "boom")

    def test_two_lines_are_refused(self):
        self.write_file(self.tgt["resultNonce"], {"ok": 1})
        self.refused(proc(self.good_line() + self.good_line()), "printed 2 RESULT: lines")

    def test_a_line_that_is_not_a_json_object_is_refused(self):
        self.write_file(self.tgt["resultNonce"], {"ok": 1})
        for bad in ("RESULT:{\"resultPath\": \"cut", "RESULT: ok", "RESULT:[1, 2]"):
            self.refused(proc(bad + "\n"), "not a JSON object")

    def test_a_record_cut_at_the_pipe_is_refused(self):
        # the class itself: a whole record printed on the line and cut where the pipe ran out of room
        whole = lab_result.PREFIX + json.dumps({"pad": "x" * 20000})
        self.refused(proc(whole[:8192]), "not a JSON object")

    def test_a_file_that_is_not_json_is_refused(self):
        self.write_file(None, raw='{"nonce": "%s", "record": {"cut' % self.tgt["resultNonce"])
        self.refused(proc(self.good_line()), "not readable JSON")

    def test_a_file_with_no_record_is_refused(self):
        self.write_file(None, raw=json.dumps({"nonce": self.tgt["resultNonce"]}))
        self.refused(proc(self.good_line()), "holds no record")

    def test_a_line_split_only_at_line_feeds(self):
        # U+2028 inside the line (JSON.stringify leaves it raw) keeps the line whole; str.splitlines would cut it
        self.write_file(self.tgt["resultNonce"], {"ok": 1})
        raw = "\n" + lab_result.PREFIX + json.dumps({"resultPath": self.tgt["resultPath"], "nonce": self.tgt["resultNonce"],
                                                     "died": "a\u2028b"}, ensure_ascii=False) + "\n"
        self.assertEqual(lab_result.read(proc(raw), self.tgt), {"ok": 1})

    def test_the_error_is_an_assertion_error(self):
        self.assertTrue(issubclass(lab_result.ResultError, AssertionError))


class Target(unittest.TestCase):
    def test_target_names_a_file_under_the_lab_a_fresh_nonce_and_the_helper(self):
        lab = tempfile.mkdtemp(prefix="lab-result-")
        self.addCleanup(shutil.rmtree, lab, True)
        a, b = lab_result.target(lab, "chromium-desk"), lab_result.target(lab, "chromium-desk")
        self.assertEqual(a["resultPath"], os.path.join(lab, "result-chromium-desk.json"))
        self.assertEqual(sorted(a), ["resultLib", "resultNonce", "resultPath"])
        self.assertNotEqual(a["resultNonce"], b["resultNonce"], "every drive mints its own nonce")
        self.assertRegex(a["resultNonce"], r"\A[0-9a-f]{16}\Z")
        self.assertTrue(os.path.isabs(a["resultLib"]) and os.path.isfile(a["resultLib"]), a["resultLib"])
        self.assertEqual(os.path.basename(a["resultLib"]), "lab_result.cjs")
        self.assertEqual(lab_result.target(lab)["resultPath"], os.path.join(lab, "result-result.json"))

    def test_a_name_that_is_not_a_plain_file_stem_is_refused(self):
        for bad in ("", "a/b", "..", "a b", None):
            with self.assertRaises(ValueError):
                lab_result.target("/nonexistent-lab", bad)

    def test_env_carries_the_target_as_json(self):
        tgt = lab_result.target("/nonexistent-lab", "argv")
        self.assertEqual(json.loads(lab_result.env(tgt)["LAB_RESULT"]), tgt)


class BareName(unittest.TestCase):
    def test_the_tests_package_registers_the_bare_name(self):
        """A served module imports lab_result at its top, beside lab_dist and lab_ports, before it puts tests/ on sys.path;
        under pytest and under `python -m unittest tests.test_x` the modules are members of the tests package, so the bare
        name resolves only because tests/__init__.py registers it (the shape of lab_ports' registration there, pinned the
        same way in tests/test_lab_ports.py). Without it a run that collected a served module before any module that puts
        tests/ on sys.path failed at that module's import. A child interpreter with tests/ off its path imports the package
        and then the bare name."""
        child = ("import os, sys\n"
                 "here = os.path.realpath(sys.argv[1])\n"
                 "sys.path[:] = [p for p in sys.path if os.path.realpath(p or '.') != here]\n"
                 "import tests\n"
                 "import lab_result\n"
                 "print(os.path.realpath(lab_result.__file__))\n"
                 "print(lab_result is sys.modules['tests.lab_result'])\n")
        p = subprocess.run([sys.executable, "-c", child, HERE], cwd=ROOT, capture_output=True, text=True, timeout=120)
        self.assertEqual(p.returncode, 0, p.stderr[-1500:])
        self.assertEqual(p.stdout.split(), [os.path.join(HERE, "lab_result.py"), "True"])


if __name__ == "__main__":
    unittest.main()
