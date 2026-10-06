#!/usr/bin/env python3
"""A served driver's record reaches pytest whole through an 8 KiB non-blocking pipe (2026-10-06).

THE CLASS. A served driver hands its record to pytest. When it printed the record whole with one write to stdout, the
record arrived cut wherever the pipe ran out of room: loading playwright leaves the driver's stdout non-blocking, and a
user past fs.pipe-user-pages-soft gets 8 KiB pipes, so a record past 8 KiB lost its tail without a throw. Every served
driver now writes its record through tests/lab_result.cjs (the record to the file the Python side names, one short
RESULT: line on stdout) and every module reads it through tests/lab_result.py.

THE HARNESS. The driver's stdout is a pipe this test makes, shrunk to 8 KiB (F_SETPIPE_SZ) and set non-blocking before
node starts, the shape a loaded machine gives a driver once playwright has loaded; nothing reads it until the driver has
exited, so what it holds then is what the driver's writes put in.

THE PINS.
  1. A planted record of 96 KiB written through the helper comes back whole from lab_result.read, and the stdout it
     needed is under 1 KiB. Red before, in the same harness: the old form (the whole record on the RESULT: line, one
     fs.writeSync) leaves exactly the pipe's 8192 bytes, and the reader refuses the cut line.
  2. A pipe already full when the driver writes its line: the driver waits (alive, its file already written) until the
     reader drains, and the line then arrives whole behind the bytes that filled the pipe. A writer that gave up on
     EAGAIN would print no line, and the reader would refuse. The writer under the line, writeAll, also resumes each
     partial write: a text four times the pipe's size arrives whole while the reader drains (a non-blocking write past
     PIPE_BUF puts in what fits and returns the count). And the line starts its own line after a partial line
     another write left on stdout.
  3. The helper's own refusals, by execution: a target whose directory does not exist, no target at all, and a record
     JSON cannot serialize each print a line with resultWriteError and no file, and the reader refuses each with the
     error; a died reason rides on the line from the record or from opts; an array record round-trips; no temp file
     is left behind; writeLine prints a progress line and refuses the RESULT tag, a lower-case tag, a second line and
     a value past 200 characters.

Runs in CI's served job (the _served.py suffix), where ROMP_SERVED_TESTS_REQUIRE=1 turns a skip red: node is all it
needs (no browser, no kernel, no extension package). Linux only (F_SETPIPE_SZ). Synthetic records; files in a temp dir.
"""
import fcntl
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, HERE)
import lab_result                                   # noqa: E402

PIPE = 8192
F_SETPIPE_SZ = getattr(fcntl, "F_SETPIPE_SZ", 1031)
F_GETPIPE_SZ = getattr(fcntl, "F_GETPIPE_SZ", 1032)
PLANT_BYTES = 96 * 1024
NODE_TIMEOUT = 60

# one CommonJS driver for every case; LAB_LIB names the helper (a pin, not the recipe: a real argv driver reads
# require(JSON.parse(process.env.LAB_RESULT).resultLib)), and LAB_RESULT carries the target except where a case drops it
DRIVER = r"""
"use strict";
const lab = require(process.env.LAB_LIB);
const t = lab.targetFromEnv();
const c = process.env.CASE;
if (c === "big") lab.writeResult(t, { pad: "x".repeat(Number(process.env.PLANT_BYTES)), tail: "end" });
else if (c === "small") lab.writeResult(t, { ok: true });
else if (c === "died") lab.writeResult(t, { a: 1, died: "the tab strip never mounted" });
else if (c === "array") lab.writeResult(t, [{ engine: "chromium" }, { engine: "webkit" }], { died: "the webkit leg stopped" });
else if (c === "bigint") lab.writeResult(t, { n: 10n });
else if (c === "undefined") lab.writeResult(t, undefined);
else if (c === "writeall") { lab.writeAll(1, "w".repeat(4 * Number(process.env.PIPE_BYTES)) + "\n"); lab.writeResult(t, { ok: true }); }
else if (c === "partial") { lab.writeAll(1, "progress with no line feed"); lab.writeResult(t, { ok: true }); }
else if (c === "lines") {
  lab.writeLine("KPID", 4242);
  const refused = [];
  for (const [tag, v] of [["RESULT", "x"], ["kpid", "1"], ["KPID", "a\nb"], ["KPID", "y".repeat(201)]]) {
    try { lab.writeLine(tag, v); } catch (e) { refused.push([tag, v.length]); }
  }
  lab.writeResult(t, { refused });
}
else { console.error("unknown case " + c); process.exit(9); }
"""

# The class's red-before: the whole record on the RESULT: line through one fs.writeSync, the form most served drivers used.
# Kept here as the planted text the harness must cut; a source census over served drivers leaves this exact value out.
OLD_FORM = r"""
"use strict";
const fs = require("fs");
const record = { pad: "x".repeat(Number(process.env.PLANT_BYTES)), tail: "end" };
fs.writeSync(1, "RESULT:" + JSON.stringify(record) + "\n");
"""


def _drain(fd):
    chunks = []
    while True:
        b = os.read(fd, 65536)
        if not b:
            return b"".join(chunks)
        chunks.append(b)


@unittest.skipUnless(sys.platform.startswith("linux"), "the 8 KiB pipe needs F_SETPIPE_SZ (Linux)")
class EightKiBPipe(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.node = shutil.which("node")
        if not cls.node:
            raise unittest.SkipTest("no node on PATH: the result helper's pins run it (CI's served job has it)")

    def setUp(self):
        self.lab = tempfile.mkdtemp(prefix="lab-result-pipe-")
        self._fds = set()
        self.addCleanup(shutil.rmtree, self.lab, True)
        self.scripts = {}
        for name, text in (("driver.cjs", DRIVER), ("old-form.cjs", OLD_FORM)):
            path = os.path.join(self.lab, name)
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            self.scripts[name] = path

    def small_pipe(self):
        """A pipe of PIPE bytes whose write end is non-blocking; the read end stays blocking for the drain."""
        r, w = os.pipe()
        self._fds.update((r, w))
        self.addCleanup(self._close, r)
        self.addCleanup(self._close, w)
        fcntl.fcntl(w, F_SETPIPE_SZ, PIPE)
        fcntl.fcntl(w, fcntl.F_SETFL, fcntl.fcntl(w, fcntl.F_GETFL) | os.O_NONBLOCK)
        self.assertEqual(fcntl.fcntl(w, F_GETPIPE_SZ), PIPE, "the harness's pipe holds 8 KiB")
        self.assertTrue(fcntl.fcntl(w, fcntl.F_GETFL) & os.O_NONBLOCK, "the harness's pipe is non-blocking")
        return r, w

    def _close(self, fd):
        # each pipe end is closed once: a second close could hit a number the process has since handed to another file
        if fd in self._fds:
            self._fds.discard(fd)
            os.close(fd)

    def spawn(self, script, w, case=None, tgt=None):
        env = {k: v for k, v in os.environ.items() if k != "LAB_RESULT"}
        env.update(LAB_LIB=lab_result.LIB, PLANT_BYTES=str(PLANT_BYTES), PIPE_BYTES=str(PIPE))
        if case:
            env["CASE"] = case
        if tgt is not None:
            env.update(lab_result.env(tgt))
        err = tempfile.TemporaryFile()
        self.addCleanup(err.close)
        p = subprocess.Popen([self.node, self.scripts[script]], stdin=subprocess.DEVNULL, stdout=w, stderr=err, env=env)
        self.addCleanup(self._reap, p)
        self._close(w)   # the driver holds the only write end: the drain ends at its exit
        return p, err

    @staticmethod
    def _reap(p):
        if p.poll() is None:
            p.kill()
            p.wait()

    def run_after_exit(self, script, case=None, tgt=None):
        """The driver run to its exit with nobody reading its stdout, then the pipe drained: (exit status, stdout, stderr)."""
        r, w = self.small_pipe()
        p, err = self.spawn(script, w, case, tgt)
        try:
            rc = p.wait(timeout=NODE_TIMEOUT)
        except subprocess.TimeoutExpired:
            self.fail("the driver did not exit in %d s with its stdout unread (case %r)" % (NODE_TIMEOUT, case))
        out = _drain(r)
        err.seek(0)
        return rc, out.decode("utf-8", "replace"), err.read().decode("utf-8", "replace")

    def proc(self, out, err):
        return subprocess.CompletedProcess([], 0, out, err)

    # 1. the class, and its red-before
    def test_a_96_kib_record_comes_back_whole_through_the_helper(self):
        tgt = lab_result.target(self.lab, "big")
        rc, out, err = self.run_after_exit("driver.cjs", "big", tgt)
        self.assertEqual(rc, 0, err)
        rec = lab_result.read(self.proc(out, err), tgt)
        self.assertEqual(rec, {"pad": "x" * PLANT_BYTES, "tail": "end"}, "the record arrived whole")
        self.assertGreater(len(json.dumps(rec)), 8 * PIPE, "the planted record is far past the pipe's room")
        self.assertLess(len(out.encode()), 1024, "stdout carried the short line only: %r" % out[:300])

    def test_red_before_the_old_form_is_cut_at_the_pipe(self):
        tgt = lab_result.target(self.lab, "old")
        rc, out, err = self.run_after_exit("old-form.cjs", None, tgt)
        self.assertEqual(rc, 0, "the cut raises nothing in the driver: " + err)
        self.assertEqual(len(out.encode()), PIPE, "one write of the whole record put exactly the pipe's room into it")
        with self.assertRaises(lab_result.ResultError) as cm:
            lab_result.read(self.proc(out, err), tgt)
        self.assertIn("not a JSON object", str(cm.exception))

    # 2. a full pipe at the line's write
    def test_a_full_pipe_delays_the_line_and_never_cuts_it(self):
        tgt = lab_result.target(self.lab, "full")
        r, w = self.small_pipe()
        filler = (b"f" * 63 + b"\n") * (PIPE // 64)
        self.assertEqual(os.write(w, filler), PIPE)
        with self.assertRaises(BlockingIOError, msg="the pipe is full before the driver starts"):
            os.write(w, b"f")
        p, err = self.spawn("driver.cjs", w, "small", tgt)
        deadline = time.monotonic() + NODE_TIMEOUT
        while not os.path.exists(tgt["resultPath"]) and p.poll() is None and time.monotonic() < deadline:
            time.sleep(0.05)
        self.assertTrue(os.path.exists(tgt["resultPath"]), "the driver wrote its file before its line")
        time.sleep(0.5)
        self.assertIsNone(p.poll(), "with the pipe full the driver waits on its line instead of exiting")
        out = _drain(r).decode()
        self.assertEqual(p.wait(timeout=NODE_TIMEOUT), 0)
        err.seek(0)
        self.assertTrue(out.startswith(filler.decode()), "the bytes that filled the pipe come first, untouched")
        self.assertEqual(lab_result.read(self.proc(out, err.read().decode()), tgt), {"ok": True})

    def test_write_all_resumes_partial_writes_while_the_reader_drains(self):
        tgt = lab_result.target(self.lab, "writeall")
        r, w = self.small_pipe()
        p, err = self.spawn("driver.cjs", w, "writeall", tgt)
        out = _drain(r).decode()   # read while the driver writes: each write past the pipe's room is partial
        self.assertEqual(p.wait(timeout=NODE_TIMEOUT), 0)
        err.seek(0)
        lines = out.split("\n")
        self.assertEqual(lines[0], "w" * (4 * PIPE), "the text four times the pipe's size arrived whole")
        self.assertEqual(lab_result.read(self.proc(out, err.read().decode()), tgt), {"ok": True})

    def test_the_line_starts_its_own_line_after_a_partial_line(self):
        tgt = lab_result.target(self.lab, "partial")
        rc, out, err = self.run_after_exit("driver.cjs", "partial", tgt)
        self.assertEqual(rc, 0, err)
        self.assertTrue(out.startswith("progress with no line feed\n" + lab_result.PREFIX), out[:200])
        self.assertEqual(lab_result.read(self.proc(out, err), tgt), {"ok": True})

    # 3. the helper's refusals and its fields, by execution
    def refused(self, case, tgt, *needles):
        rc, out, err = self.run_after_exit("driver.cjs", case, tgt)
        self.assertEqual(rc, 0, err)
        with self.assertRaises(lab_result.ResultError) as cm:
            lab_result.read(self.proc(out, err), tgt if tgt is not None else lab_result.target(self.lab, "none"))
        for n in needles:
            self.assertIn(n, str(cm.exception))
        return out

    def test_a_target_in_a_missing_directory_is_a_write_error(self):
        tgt = lab_result.target(os.path.join(self.lab, "no-such-dir"), "x")
        self.refused("small", tgt, "could not write its record", "ENOENT")
        self.assertEqual(sorted(os.listdir(self.lab)), ["driver.cjs", "old-form.cjs"], "nothing written, no temp file")

    def test_no_target_is_a_write_error(self):
        out = self.refused("small", None, "could not write its record", "no resultPath or no resultNonce")
        self.assertIn('"resultPath":null', out)

    def test_a_record_json_cannot_serialize_is_a_write_error(self):
        for case, needle in (("bigint", "BigInt"), ("undefined", "does not serialize")):
            tgt = lab_result.target(self.lab, case)
            self.refused(case, tgt, "could not write its record", needle)
            self.assertFalse(os.path.exists(tgt["resultPath"]), case + ": no file")
        self.assertEqual(sorted(n for n in os.listdir(self.lab) if ".tmp-" in n), [], "no temp file left behind")

    def test_a_died_reason_rides_on_the_line(self):
        tgt = lab_result.target(self.lab, "died")
        rc, out, err = self.run_after_exit("driver.cjs", "died", tgt)
        self.assertEqual(rc, 0, err)
        head = json.loads(next(ln for ln in out.split("\n") if ln.startswith(lab_result.PREFIX))[len(lab_result.PREFIX):])
        self.assertEqual(head, {"resultPath": tgt["resultPath"], "nonce": tgt["resultNonce"], "died": "the tab strip never mounted"})
        self.assertEqual(lab_result.read(self.proc(out, err), tgt), {"a": 1, "died": "the tab strip never mounted"})
        self.assertEqual(sorted(os.listdir(self.lab)), ["driver.cjs", "old-form.cjs", "result-died.json"], "no temp file left behind")

    def test_an_array_record_round_trips_with_died_from_opts(self):
        tgt = lab_result.target(self.lab, "array")
        rc, out, err = self.run_after_exit("driver.cjs", "array", tgt)
        self.assertEqual(rc, 0, err)
        self.assertIn('"died":"the webkit leg stopped"', out)
        self.assertEqual(lab_result.read(self.proc(out, err), tgt), [{"engine": "chromium"}, {"engine": "webkit"}])

    def test_write_line_prints_a_progress_line_and_refuses_the_record_road(self):
        tgt = lab_result.target(self.lab, "lines")
        rc, out, err = self.run_after_exit("driver.cjs", "lines", tgt)
        self.assertEqual(rc, 0, err)
        self.assertIn("KPID:4242", out.split("\n"))
        self.assertEqual(lab_result.read(self.proc(out, err), tgt),
                         {"refused": [["RESULT", 1], ["kpid", 1], ["KPID", 3], ["KPID", 201]]})


if __name__ == "__main__":
    unittest.main()
