#!/usr/bin/env python3
"""The judge scratch cwd is private, and romp refuses to judge without one.

JUDGE_SCRATCH used to be the literal "/tmp/romp-judge", created with `os.makedirs(..., exist_ok=True)`.
/tmp is world-writable and that name is guessable, so on any machine with a second local account someone
could create the path first — as a directory with permissions of their choosing, or as a SYMLINK — and
`exist_ok=True` would accept whatever they left there. Two things then follow, neither of them subtle:

  * `prune_judge_scratch` runs at every kernel boot, realpaths the scratch through `_proj_dir`, and
    unlinks every `*.jsonl` older than a day in the project dir that name derives to. Point the symlink
    at a directory you actually work in and romp's own housekeeping deletes YOUR Claude Code transcripts.
  * It is the cwd of a `claude -p` subprocess, and a cwd someone else controls is a cwd they can plant a
    `.claude/` in. `_judge_cmd`'s `--safe-mode` is what closes that today; the cwd should not be relying
    on it alone.

Nothing is written INTO the scratch — it is a bare cwd, and the transcripts land under ~/.claude/projects
— so this is about who controls the directory, not about what is stored in it.

So: the scratch lives under the 0700 state root, is created 0700, and a directory that cannot be made
private makes the judge call FAIL LOUDLY (an error row + a stderr line) rather than run from somewhere
anyone can write. All fixtures SYNTHETIC.
"""
import json
import os
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from romp_load import load_source
from pathlib import Path
from unittest import mock

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()   # hermetic BEFORE any romp code loads
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
jd = load_source("romp_judge_scratch", os.path.join(BIN, "romp-judge"))

SID = "11111111-2222-3333-4444-555555555555"

# The bindings as PRODUCTION sees them, captured before any test rebinds the state root — a test's own
# tempdir usually sits in /tmp, so only these can answer "is the scratch in /tmp?"
IMPORT_STATE, IMPORT_SCRATCH = jd.STATE, jd.JUDGE_SCRATCH


class JudgeScratchPrivate(unittest.TestCase):
    def setUp(self):
        self._saved = jd.STATE
        self.td = tempfile.TemporaryDirectory()
        jd._rebind_state(Path(self.td.name))

    def tearDown(self):
        jd._rebind_state(self._saved)
        self.td.cleanup()

    def _mode(self, p):
        return stat.S_IMODE(os.lstat(p).st_mode)

    # ── where it lives ───────────────────────────────────────────────────────
    def test_scratch_is_under_the_state_root_not_tmp(self):
        self.assertEqual(Path(IMPORT_SCRATCH).parent, IMPORT_STATE,
                         "judge scratch belongs under the 0700 state root")
        self.assertNotEqual(IMPORT_SCRATCH, "/tmp/romp-judge",
                            "the world-writable, guessable path is the bug this test guards")
        # ...and the root it sits under is the private one, so no other account can even traverse to it.
        # (The suite's own root is a tempdir — conftest.py — hence the check on the root, not on "/tmp".)
        self.assertEqual(stat.S_IMODE(os.lstat(IMPORT_STATE).st_mode), 0o700)

    def test_rebind_moves_the_scratch_with_the_rest_of_the_state(self):
        """_rebind_state is how tests isolate a state root; a scratch left behind writes into the LIVE one."""
        self.assertTrue(str(jd.JUDGE_SCRATCH).startswith(self.td.name))

    # ── how it is created ────────────────────────────────────────────────────
    def test_created_0700(self):
        d = jd._ensure_judge_scratch()
        self.assertEqual(d, jd.JUDGE_SCRATCH)
        self.assertTrue(os.path.isdir(d))
        self.assertEqual(self._mode(d), 0o700, "owner-only, like the state root above it")

    def test_created_0700_whatever_the_umask(self):
        old = os.umask(0o000)                      # a permissive umask must not widen the scratch
        try:
            jd._ensure_judge_scratch()
        finally:
            os.umask(old)
        self.assertEqual(self._mode(jd.JUDGE_SCRATCH), 0o700)

    def test_existing_loose_directory_is_tightened(self):
        """Ours but group/world-readable — a pre-move install, a stray umask. We own it, so repair it."""
        os.makedirs(jd.JUDGE_SCRATCH, exist_ok=True)
        os.chmod(jd.JUDGE_SCRATCH, 0o755)
        jd._ensure_judge_scratch()
        self.assertEqual(self._mode(jd.JUDGE_SCRATCH), 0o700)

    def test_directory_owned_by_someone_else_is_refused(self):
        """The pre-create attack: another local account owns the path when romp gets there."""
        os.makedirs(jd.JUDGE_SCRATCH, exist_ok=True)
        theirs = os.lstat(jd.JUDGE_SCRATCH).st_uid + 1
        with mock.patch("os.geteuid", return_value=theirs):
            with self.assertRaises(OSError) as cm:
                jd._ensure_judge_scratch()
        self.assertIn("judge scratch", str(cm.exception))

    def test_symlink_in_place_of_the_scratch_is_refused(self):
        """makedirs(exist_ok=True) is happy with a symlink to a directory; the check must not be. This is
        the shape that turns prune_judge_scratch — which realpaths the scratch — into a delete of whatever
        the link points at."""
        elsewhere = os.path.join(self.td.name, "elsewhere")
        os.makedirs(elsewhere, 0o777)
        os.symlink(elsewhere, jd.JUDGE_SCRATCH)
        with self.assertRaises(OSError):
            jd._ensure_judge_scratch()

    # ── what happens when it can't be made private ───────────────────────────
    def test_unsafe_scratch_skips_the_judge_call_and_logs_it(self):
        """Fail loudly: no private cwd → no judge call. Running it from /tmp or $HOME anyway would hand the
        subprocess a working directory someone else can plant in, and a silent downgrade hides exactly the
        breakage we need to see."""
        os.symlink(self.td.name, jd.JUDGE_SCRATCH)       # unsafe, by the check above
        jd._SCRATCH_FAIL_LOGGED.clear()
        with mock.patch.object(jd.subprocess, "run", side_effect=AssertionError("judge call must not run")):
            out = jd._judge_run("haiku", "you are a test", "summarize this synthetic unit",
                                judge="captioner", tier="index")
        self.assertEqual(out, "", "callers see a failed call, not a partial one")
        rows = [json.loads(l) for l in Path(jd.ERRORS).read_text().splitlines() if l.strip()]
        self.assertTrue(any(r["err"] == "scratch" and r["judge"] == "captioner" for r in rows),
                        "the refusal is surfaced as an error row (`romp judges`), not swallowed")
        # A scratch refusal is NOT the model's fault, so it must ride the same paused flag the rate gate
        # and retry-pause set: a "" that means "skipped, try again" — NOT one that counts toward
        # DISTILL_FAIL_CAP. Without the flag, three refusals in a row blank the card's summary to the ""
        # sentinel (the distiller/briefer/staller each read _judge_ctx.paused to skip the count), which is
        # irreversible content loss from a directory-permission hiccup.
        self.assertTrue(getattr(jd._judge_ctx, "paused", False),
                        "the give-up counters must treat a scratch-skip as a pause, not a failure")

    # ── the age-based cleanup follows the new location ───────────────────────
    def test_prune_sweeps_the_new_scratch_project_dir(self):
        jd.PROJECTS = Path(self.td.name) / "projects"    # not derived from STATE — bind it by hand
        proj = jd._proj_dir(jd._ensure_judge_scratch())
        proj.mkdir(parents=True, exist_ok=True)
        now = time.time()
        old = proj / ("%s.jsonl" % SID)
        new = proj / "22222222-3333-4444-5555-666666666666.jsonl"
        for f in (old, new):
            f.write_text('{"synthetic": "judge call"}\n')
        os.utime(old, (now - 48 * 3600, now - 48 * 3600))
        self.assertEqual(jd.prune_judge_scratch(now=now), 1)
        self.assertFalse(old.exists())
        self.assertTrue(new.exists(), "a fresh transcript (a call still in flight) is left alone")


class TheStateRootModeIsChecked(unittest.TestCase):
    """The state root's 0700 is the premise behind this repo's no-heal rule for credential files (a registry or a
    parked-ops mirror this uid wrote at a looser mode is not exposed because the root is owner-only; PR 789, review
    round 1). kernel/judge.py makes the root 0700 at import, best-effort: the mkdir and the chmod sit in
    `except OSError: pass`, and until review round 2 of PR 789 (2026-09-19) nothing read the mode back, so the premise
    could be false with no signal. Now the mode is read after the attempt and, when it is not 0700, said once on stderr,
    naming the path and the mode read. Not a heal: nothing here changes a mode (the round-1 ruling stands: files tighten
    on their next write). The import road runs in a child so the planted root and the refused chmod stay out of this
    process."""

    def test_a_0700_root_produces_no_line(self):
        d = tempfile.mkdtemp()                                   # mkdtemp creates 0700
        self.assertIsNone(jd._state_root_mode_line(Path(d)))
        self.assertIsNone(jd._STATE_ROOT_MODE_LINE, "the suite's own root is 0700, so the import said nothing")

    def test_a_root_the_chmod_left_looser_produces_one_line_naming_the_path_and_the_mode(self):
        d = tempfile.mkdtemp()
        os.chmod(d, 0o755)
        line = jd._state_root_mode_line(Path(d))
        self.assertIsNotNone(line)
        self.assertIn(d, line, "names the path")
        self.assertIn("0755", line, "names the mode read")
        self.assertIn("0700", line, "and the mode expected")
        self.assertNotIn("\n", line, "one line")
        self.assertEqual(stat.S_IMODE(os.stat(d).st_mode), 0o755, "read, not healed")

    def test_a_root_that_cannot_be_read_produces_a_line_naming_the_path(self):
        d = Path(tempfile.mkdtemp()) / "never-made"
        line = jd._state_root_mode_line(d)
        self.assertIsNotNone(line)
        self.assertIn(str(d), line)

    def _import_in_a_child(self, plant_loose):
        """Load kernel/judge.py in a child with ROMP_STATE_DIR at a fresh root. With `plant_loose` the root is planted
        0755 first and os.chmod refuses to touch it, the shape a root this uid cannot tighten takes; without it the
        import makes the root itself. Returns (root, the child's stderr)."""
        root = os.path.join(tempfile.mkdtemp(), "romp")
        env = dict(os.environ)
        env["ROMP_STATE_DIR"] = root
        code = ("import os, sys\n"
                "sys.path.insert(0, %r)\n"                      # the tests dir, where romp_load lives
                "from romp_load import load_source\n"
                "root = %r\n"
                "if %r:\n"
                "    os.mkdir(root)\n"
                "    os.chmod(root, 0o755)\n"
                "    real = os.chmod\n"
                "    def refuse(path, mode, *a, **k):\n"
                "        if os.path.realpath(str(path)) == os.path.realpath(root):\n"
                "            raise PermissionError(1, 'chmod refused (interposed)')\n"
                "        return real(path, mode, *a, **k)\n"
                "    os.chmod = refuse\n"
                "load_source('romp_judge_child', %r)\n"
                % (HERE, root, plant_loose, os.path.join(BIN, "romp-judge")))
        r = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, timeout=180)
        self.assertEqual(r.returncode, 0, r.stderr)
        return root, r.stderr

    def test_the_import_says_it_once_on_stderr_when_the_chmod_could_not_tighten_the_root(self):
        root, err = self._import_in_a_child(plant_loose=True)
        lines = [l for l in err.splitlines() if "state root" in l]
        self.assertEqual(len(lines), 1, "exactly one line:\n" + err)
        self.assertIn(root, lines[0], "names the path")
        self.assertIn("0755", lines[0], "names the mode read")
        self.assertEqual(stat.S_IMODE(os.stat(root).st_mode), 0o755, "read, not healed")

    def test_the_import_says_nothing_for_a_root_it_made_0700(self):
        root, err = self._import_in_a_child(plant_loose=False)
        self.assertEqual([l for l in err.splitlines() if "state root" in l], [], err)
        self.assertEqual(stat.S_IMODE(os.stat(root).st_mode), 0o700)


if __name__ == "__main__":
    unittest.main()
