#!/usr/bin/env python3
"""The comments host's environment (plans/file-review.md, decision 49's test seam; the sidecar slice's
review, 2026-09-11): the kernel hands tools/file-comments-host.mjs its own environment minus
TRACKCHANGES_ROOT and every FILE_COMMENTS_* variable (_file_comments_host_env).

Why the prefix: the host reads its test seams from FILE_COMMENTS_* names. FILE_COMMENTS_HOME points "~"
at a scratch directory in its node tests; FILE_COMMENTS_TEST_PAUSE_MS holds a reject's or a save's write
open between the sidecar's rename and the file's (the race test's window). The kernel sets neither, but a
plain `dict(os.environ)` forwarded whatever the shell a kernel was started in exported, so a pause left
in that shell reached the host on every reject and save; at or past _FILE_COMMENTS_TIMEOUT the kernel's
kill then landed after the sidecar and the log were written and before the file was, and the rejected
text stood in the file with no pending change and no record. tests/test_file_comments.py pins
TRACKCHANGES_ROOT the same way; this module pins the prefix: against the kernel's function, against a
stub host that reports the environment it was handed, and against the real host, paused past the
deadline through the inherited variable, which must still answer at once.

Synthetic only: the notes-api demo world under a temp dir, a placeholder sid, a `.git/` directory as the
project landmark (store-io reads nothing from it).
"""
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import unittest
from romp_load import load_source
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
REPO = os.path.dirname(HERE)
BIN = os.path.join(REPO, "bin")
HOST = os.path.join(REPO, "tools", "file-comments-host.mjs")
TRACK_EDIT = os.path.join(REPO, "vendor", "track-changents", "cli", "track-edit.mjs")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the load: the kernel resolves its state root at import time, and only pytest
# runs conftest's floor (a bare script run would otherwise write REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)
km = load_source("romp_kernel_filecomments_hostenv", os.path.join(BIN, "romp-kernel"))

SID = "11111111-2222-3333-4444-555555555555"
NODE = shutil.which("node")
PREFIX = "FILE_COMMENTS_"
SEAMS = ("FILE_COMMENTS_HOME", "FILE_COMMENTS_TEST_PAUSE_MS")   # the two the host reads today
CONTROL = "NOTES_API_ENV_CONTROL"                               # a name the strip must leave alone
TEXT = "# Findings\n\nThe api session cut p95 latency by 40%.\n\nWe recommend shipping the cache in v1.2.\n"


def host_seam_names():
    """Every FILE_COMMENTS_* name the host's source reads from its environment, the list the strip
    must cover, taken from the source so a seam added later is on it the day it is read."""
    src = Path(HOST).read_text(encoding="utf-8")
    return set(re.findall(r"process\.env\.(FILE_COMMENTS_[A-Z0-9_]+)", src))


class _Env(unittest.TestCase):
    """os.environ edits scoped to one test: set `names`, restore what was there after."""

    def setUp(self):
        self._before = {}

    def tearDown(self):
        for k, v in self._before.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def export(self, **names):
        for k, v in names.items():
            self._before.setdefault(k, os.environ.get(k))
            os.environ[k] = v


class TheHostEnvironment(_Env):
    def test_every_seam_the_host_reads_is_stripped(self):
        names = host_seam_names()
        self.assertTrue(set(SEAMS) <= names, "the regex over the host's source found %r" % (names,))
        self.export(**{n: "set-by-the-shell" for n in names})
        env = km._file_comments_host_env()
        # key names only in every message here: the environment under test is this process's, keys included
        self.assertEqual(sorted(k for k in env if k in names), [])
        self.assertTrue(names <= set(os.environ), "the kernel's own environment is untouched")

    def test_the_strip_is_by_prefix_and_narrow(self):
        # a seam the host does not read yet is stripped the same way; TRACKCHANGES_ROOT still goes;
        # everything else the kernel holds reaches the host as it was
        self.export(FILE_COMMENTS_SOME_LATER_SEAM="1", TRACKCHANGES_ROOT=os.path.join(tempfile.gettempdir(), "elsewhere"),
                    **{CONTROL: "kept"})
        env = km._file_comments_host_env()
        expected = {k: v for k, v in os.environ.items() if not k.startswith(PREFIX) and k != "TRACKCHANGES_ROOT"}
        self.assertEqual(sorted(k for k in env if k.startswith(PREFIX) or k == "TRACKCHANGES_ROOT"), [])
        self.assertEqual(env.get(CONTROL), "kept")
        self.assertEqual(sorted(env), sorted(expected), "the same names, minus the stripped ones")
        self.assertEqual([k for k in expected if env[k] != expected[k]], [], "every value as it was")
        self.assertEqual(km._FILE_COMMENTS_ENV_PREFIX, PREFIX)

    def test_the_kernel_names_no_seam_and_sets_none(self):
        # the only quoted FILE_COMMENTS_ literal in the kernel is the prefix it strips: the kernel neither
        # names a seam (the host's node tests pin that for the pause by name) nor exports one
        src = Path(BIN, "romp-kernel").resolve().read_text(encoding="utf-8")
        self.assertEqual(sorted(set(re.findall(r'["\']FILE_COMMENTS_[A-Z0-9_]*["\']', src))), ['"FILE_COMMENTS_"'])
        self.assertNotRegex(src, r'os\.environ(\[|\.setdefault\(|\.update\()[^\n]*FILE_COMMENTS_')


@unittest.skipUnless(NODE, "node not installed on this machine")
class TheStubHostSeesNoSeam(_Env):
    """The kernel's spawn, end to end to the child's environment: a stub host that answers a status and
    writes down which FILE_COMMENTS_* names, TRACKCHANGES_ROOT and the control variable reached it."""

    STUB = """import fs from 'node:fs';
let raw = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', (d) => { raw += d; });
process.stdin.on('end', () => {
  fs.writeFileSync(process.argv[1] + '.seen.json', JSON.stringify({
    seams: Object.keys(process.env).filter((k) => k.startsWith('FILE_COMMENTS_')).sort(),
    hasRoot: Object.prototype.hasOwnProperty.call(process.env, 'TRACKCHANGES_ROOT'),
    control: process.env.NOTES_API_ENV_CONTROL || null,
    hasPath: typeof process.env.PATH === 'string' && process.env.PATH.length > 0,
  }));
  process.stdout.write(JSON.stringify({ ok: true, verb: 'status', root: null, storePath: null, trackedBy: null,
    agentTooling: 'absent', fileMtimeNs: '1', storeMtimeNs: null, configMtimeNs: null, store: null, hunks: [],
    unsent: { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null }, log: [], logTruncated: false }));
});
"""

    def setUp(self):
        super().setUp()
        self.tmp = tempfile.mkdtemp()
        self.fp = os.path.join(self.tmp, "report.md")
        Path(self.fp).write_text(TEXT)
        self.stub = os.path.join(self.tmp, "stub-host.mjs")
        Path(self.stub).write_text(self.STUB)
        self._host = km._FILE_COMMENTS_HOST
        km._FILE_COMMENTS_HOST = Path(self.stub)

    def tearDown(self):
        km._FILE_COMMENTS_HOST = self._host
        shutil.rmtree(self.tmp, ignore_errors=True)
        super().tearDown()

    def test_the_seams_and_the_root_stop_at_the_kernel_and_the_rest_passes(self):
        self.export(FILE_COMMENTS_HOME=os.path.join(self.tmp, "not-home"), FILE_COMMENTS_TEST_PAUSE_MS="20000",
                    TRACKCHANGES_ROOT=os.path.join(self.tmp, "elsewhere"), **{CONTROL: "kept"})
        out, err = km._file_comments_call(self.fp, "status")
        self.assertIsNone(err, err)
        self.assertTrue(out["ok"])
        seen = json.loads(Path(self.stub + ".seen.json").read_text())
        self.assertEqual(seen, {"seams": [], "hasRoot": False, "control": "kept", "hasPath": True})


@unittest.skipUnless(NODE, "node not installed on this machine")
class TheRealHostPausedFromTheShell(_Env):
    """The scenario the review measured, against the real host and the real track-edit: the pause seam
    exported in the kernel's environment at a value past the deadline, then a reject-all of a session's
    change. Before the strip the host slept at the file's rename, the kernel killed it at the deadline
    with the sidecar and the log written and the file still holding the change, and left a staged temp
    and the lock beside them; now the variable never reaches the host and the reject lands at once."""

    def setUp(self):
        super().setUp()
        self.tmp = tempfile.mkdtemp()
        self.root = Path(self.tmp, "notes-api")
        (self.root / ".git").mkdir(parents=True)
        (self.root / "docs").mkdir()
        self.fp = self.root / "docs" / "report.md"
        self.fp.write_text(TEXT)
        self._timeout = km._FILE_COMMENTS_TIMEOUT
        self.assertEqual(Path(km._FILE_COMMENTS_HOST), Path(HOST), "the real host, nothing stubbed")

    def tearDown(self):
        km._FILE_COMMENTS_TIMEOUT = self._timeout
        shutil.rmtree(self.tmp, ignore_errors=True)
        super().tearDown()

    def call(self, verb, args=None, fence=None):
        out, err = km._file_comments_call(str(self.fp), verb, args, fence)
        self.assertIsNone(err, "%s: %r" % (verb, err))
        return out

    @staticmethod
    def fence_of(status, file=False):
        f = {"storeMtimeNs": status["storeMtimeNs"] or "", "configMtimeNs": status["configMtimeNs"] or ""}
        if file:
            f["fileMtimeNs"] = status["fileMtimeNs"]
        return f

    def track_edit(self, old, new):
        env = dict(os.environ)
        env.pop("TRACKCHANGES_ROOT", None)
        env = {k: v for k, v in env.items() if not k.startswith(PREFIX)}
        env.update(ROMP_SESSION_NAME="web", ROMP_SID=SID)
        r = subprocess.run([NODE, TRACK_EDIT, "--file", str(self.fp), "--old", old, "--new", new],
                           capture_output=True, text=True, timeout=30, env=env)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_a_reject_all_lands_at_once_with_the_pause_exported_past_the_deadline(self):
        s0 = self.call("status")
        self.call("set-tracked", {"on": True, "scope": "file"}, self.fence_of(s0))
        self.track_edit("cut p95 latency by 40%", "cut p95 latency by 45%")
        self.assertIn("45%", self.fp.read_text())
        s = self.call("status")
        self.assertEqual([h["oldText"] for h in s["hunks"]], ["cut p95 latency by 40%"])
        # the shell's export, at four times the deadline; the deadline itself shortened so a regression
        # fails here in seconds as the host-error the review saw, not as a green test that took 20 s
        km._FILE_COMMENTS_TIMEOUT = 5
        self.export(FILE_COMMENTS_TEST_PAUSE_MS="20000")
        t0 = time.monotonic()
        out, err = km._file_comments_call(str(self.fp), "reject-all", {}, self.fence_of(s, file=True))
        took = time.monotonic() - t0
        self.assertIsNone(err, "the inherited pause reached the host and the kill landed between the sidecar's "
                               "rename and the file's: %r" % (err,))
        self.assertLess(took, km._FILE_COMMENTS_TIMEOUT)
        self.assertEqual(out["rejected"], [s["hunks"][0]["id"]])
        self.assertEqual(out["hunks"], [])
        self.assertEqual(self.fp.read_text(), TEXT, "the change's text is gone from the file")
        docs = sorted(p.name for p in self.fp.parent.iterdir())
        self.assertEqual(docs, ["report.md"], "no staged temp beside the file: %r" % (docs,))
        store = Path(s["storePath"])
        self.assertFalse(Path(str(store) + ".lock").exists(), "the lock was released")


if __name__ == "__main__":
    raise SystemExit("run under pytest: a bare run loads the kernel outside conftest's state floor")
