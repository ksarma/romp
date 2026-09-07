#!/usr/bin/env python3
"""kernel/envsource.py: the credential set a configured command prints, handed to each child at
launch and never written to the kernel's environment or to a file.

The source is the KeySource keysource selected (kind "command"); this module decides nothing about
the mode. What these pin, in the order the module is used:
  Config: the three tuning settings (ROMP_CREDENTIAL_SELECTOR_FILE, _NAMES, _TIMEOUT_S) resolve from the
    process environment first, then the same line in the manager's env file, so a terminal outside the
    manager tree reads what the kernel reads; the defaults; junk timeouts. The command line itself is
    keysource's to select.
  Runner: /bin/sh -c with the selector as $1, stdin closed, a nonzero exit or a deadline is a reason
    with counts and exit codes only, a timed-out command's whole process group is killed, and the
    deadline is on the PROCESS: a command that exits 0 but leaves a child holding stdout succeeds,
    and one that hands both pipes back and runs on is held to the deadline all the same.
  Parser: keysource's line rule generalised to every name (pinned equal to keysource.parse_key for
    the key line): last wins, one layer of quotes, blank and # lines skipped, ROMP_* names dropped
    and named, lines that are not NAME=VALUE counted, empty values dropped; newlines are the only
    separators, a NUL makes a bad line, and the command's output may say `export NAME=VALUE`.
  CacheAndCoalescing: one successful run serves every read until invalidate() or a selector-file
    edit; concurrent callers coalesce on one run; a failed run keeps the previous set, says so, and
    the NEXT caller re-runs (one run per caller); a first failure is an empty set; an invalidation
    during a run makes the next caller run again; take() reads record and values together; an
    authentication failure invalidates once per credential, a success re-arms it, and a refusal
    stamped with a credential that is not the current one (a session still on the set from before
    a rotation) invalidates nothing; the record's setSeq (the set's identity within a generation)
    moves only when a run hands back another set.
  Selector: the one-token file: missing is "no selector", a non-token is an error carrying a byte
    count, an undeclared name is refused before anything runs, a name is rendered only when it is
    declared (else by length), the write is atomic, 0600 and through a symlink.
  SourceIdentity: the cache identity is (generation, the source's fingerprint, the selector file's
    stat identity): another command text re-runs from an empty set, None or a source of another kind
    is an empty set with no run, an invalid text is a reason with no run, the record carries the
    source's fingerprint and never its text, the source keysource selects from the environment door
    is the one run, and resolve_key answers the set's key (or "") without ever raising for a failed
    run, through keysource.COMMAND_RESOLVER.
  HelperFingerprint: the configured apiKeyHelper (the user settings.json alone; a settings.local.json
    is a project-level file and is not read) is run with the same runner, in a session CLI's
    environment (role variables merged, ROMP_SID absent), and hashed inside the function; the bytes
    never leave it; one token expected; cached until invalidate(), under the generation of the set
    it ran with (the run's own read, or the generation handed in beside a set a connect took), so
    an invalidation before or during the run leaves the entry stale; a caller that already holds
    the set hands it in so the command is not run twice. The entry is for (generation, setSeq): a
    set that changed under one generation (a recovery after a failed run, a selector hand edit)
    gets a fresh fingerprint and an unchanged one keeps its entry; and an entry is never written
    over a newer one, so a late connect's older run cannot hide a refusal on the current output.
  NothingLeaks: no fixture value in any status field or reason, whatever the command does with it.
  Floor: conftest's floor: the three command variables absent and the selector file pointed at a
    path that does not exist, at import and per test; this module's own import leaves the selector
    floored; a module that pops it at import fails collection loudly.

Synthetic throughout: every value is "romp-test-fixture-" + a uuid, assembled at run time (no
credential-shaped literal in the file); fake commands are scripts written into a temp dir; a temp
CLAUDE_CONFIG_DIR carries the fake settings.json. conftest pops the three command variables and
floors the selector file before every test; this module does the same at import (a pop there would
undo conftest's floor for every module collected after it); the classes below set what they need in
setUp and restore the world after.
"""
import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import uuid
from importlib.machinery import SourceFileLoader

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
# Hermetic state BEFORE the loads: they resolve their state root at import time, and only pytest runs
# conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
_NO_ENV = os.path.join(os.environ["XDG_STATE_HOME"], "no-such-service.env")
os.environ["ROMP_SERVICE_ENV_FILE"] = _NO_ENV
os.environ["ROMP_SERVICE_ENV"] = _NO_ENV
for _v in ("ROMP_CREDENTIAL_COMMAND", "ROMP_CREDENTIAL_NAMES", "ROMP_CREDENTIAL_TIMEOUT_S"):
    os.environ.pop(_v, None)
# The selector file is FLOORED, never popped (conftest's rule): absent means the default under HOME, and
# a pop here ran during collection, leaving that default in force for every module collected after this
# one. A path under this module's own state root that is never created, as conftest floors it.
os.environ["ROMP_CREDENTIAL_SELECTOR_FILE"] = os.path.join(os.environ["XDG_STATE_HOME"], "no-such-credential-selector")
_SELECTOR_AT_IMPORT = os.environ["ROMP_CREDENTIAL_SELECTOR_FILE"]   # what this import left for the modules after it

es = SourceFileLoader("romp_envsource", os.path.join(ROOT, "kernel", "envsource.py")).load_module()
ks = es._keysrc


def fixture_value(tag=""):
    """A synthetic value, never key-shaped: assembled at run time so no literal in this file can
    look like a credential to the scanner."""
    return "romp-test-fixture-%s%s" % (tag + "-" if tag else "", uuid.uuid4().hex)


# The developer's shell may carry a key, the CLI's login tokens and a session id (a suite run from inside
# a romp session does): none may reach a helper run or an assertion message here, so each is popped per
# test and restored after.
_POPPED_VARS = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "CLAUDE_CODE_OAUTH_TOKEN", "ROMP_SID")
_SAVED_VARS = es.CONFIG_VARS + ("CLAUDE_CONFIG_DIR", "XDG_CONFIG_HOME",
                                "ROMP_SERVICE_ENV_FILE", "ROMP_SERVICE_ENV") + _POPPED_VARS


def _count(marker):
    """How many times a fixture script appended a line to `marker`: a run count the module's own counter
    cannot fake (0 for a file no run created)."""
    try:
        with open(marker) as fh:
            return sum(1 for _ in fh)
    except FileNotFoundError:
        return 0


class _Lab(unittest.TestCase):
    """A temp dir for scripts, the env file and the selector; the module's cache reset around each test.
    `self.src` is the KeySource under test: None until configure() builds a command source."""

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self._before = {v: os.environ.get(v) for v in _SAVED_VARS}
        for v in es.CONFIG_VARS + _POPPED_VARS:
            os.environ.pop(v, None)
        os.environ["CLAUDE_CONFIG_DIR"] = os.path.join(self.d, "claude-config")   # no settings.json: no helper
        os.environ["ROMP_CREDENTIAL_SELECTOR_FILE"] = os.path.join(self.d, "selector")
        self.src = None
        es._reset()

    def tearDown(self):
        for v, was in self._before.items():
            if was is None:
                os.environ.pop(v, None)
            else:
                os.environ[v] = was
        es._reset()

    def script(self, body, name="cmd.sh"):
        p = os.path.join(self.d, name)
        with open(p, "w") as fh:
            fh.write("#!/bin/sh\n" + body + "\n")
        os.chmod(p, 0o700)
        return p

    def printing(self, values, name="cmd.sh", extra=""):
        """A command that prints the given {NAME: value} set (and `extra` shell lines first)."""
        lines = [extra] if extra else []
        lines += ["echo '%s=%s'" % (k, v) for k, v in values.items()]
        return self.script("\n".join(lines), name)

    def configure(self, cmd, names=None, timeout=None):
        """The command source keysource would select for `cmd`, held as self.src; the tuning values
        in the environment. Nothing is written to ROMP_CREDENTIAL_COMMAND: the module reads the source
        it is handed, not the variable."""
        self.src = ks.KeySource("command", cmd)
        if names is not None:
            os.environ["ROMP_CREDENTIAL_NAMES"] = names
        if timeout is not None:
            os.environ["ROMP_CREDENTIAL_TIMEOUT_S"] = str(timeout)
        return self.src

    def select(self, token):
        with open(os.environ["ROMP_CREDENTIAL_SELECTOR_FILE"], "w") as fh:
            fh.write(token)

    def edit_selector(self, token, bump_s=1):
        """A hand edit: the token written and the mtime moved `bump_s` seconds past now, so the
        file's stat identity changes even when two edits land within one clock tick."""
        p = os.environ["ROMP_CREDENTIAL_SELECTOR_FILE"]
        with open(p, "w") as fh:
            fh.write(token + "\n")
        t = time.time_ns() + bump_s * 10**9
        os.utime(p, ns=(t, t))

    def helper(self, body, config_dir=None):
        """A fake settings.json naming a fake apiKeyHelper script; returns the helper's path."""
        d = config_dir or os.environ["CLAUDE_CONFIG_DIR"]
        os.makedirs(d, exist_ok=True)
        h = self.script(body, "helper.sh")
        with open(os.path.join(d, "settings.json"), "w") as fh:
            json.dump({"apiKeyHelper": h}, fh)
        return h


class Config(_Lab):
    def test_no_command_source_is_an_empty_set_with_no_run(self):
        self.assertEqual(es.injection(None), {})
        snap = es.current(None)
        self.assertFalse(snap["configured"])
        self.assertIsNone(snap["ok"])
        self.assertEqual(snap["runs"], 0)
        self.assertEqual(snap["sourceFp"], "")
        self.assertEqual(es._runs, 0, "nothing runs when no command source is selected")

    def test_the_environment_wins_over_the_env_file_which_wins_over_nothing(self):
        p = os.path.join(self.d, "service.env")
        file_selector = os.path.join(self.d, "file-selector")
        with open(p, "w") as fh:
            fh.write("ROMP_PERF=1\nROMP_CREDENTIAL_COMMAND=\"from-the-file --flag\"\n"
                     "ROMP_CREDENTIAL_NAMES=hp, lp\nROMP_CREDENTIAL_TIMEOUT_S=7\n"
                     "ROMP_CREDENTIAL_SELECTOR_FILE='%s'\n" % file_selector)
        os.environ["ROMP_SERVICE_ENV_FILE"] = p
        os.environ["ROMP_SERVICE_ENV"] = p
        os.environ.pop("ROMP_CREDENTIAL_SELECTOR_FILE")
        self.assertEqual(es.names(), ["hp", "lp"])
        self.assertEqual(es.timeout_s(), 7.0)
        self.assertEqual(es.selector_path(), file_selector, "one layer of quotes, like the launchers")
        self.assertEqual(es.config_value("ROMP_CREDENTIAL_COMMAND"), "from-the-file --flag")
        self.assertEqual(ks.read_source(p).kind, "command", "the command line itself is keysource's to select")
        os.environ["ROMP_CREDENTIAL_NAMES"] = "from-the-environment"
        self.assertEqual(es.names(), ["from-the-environment"])
        # a rewrite is picked up by the file's own stat identity
        os.environ.pop("ROMP_CREDENTIAL_NAMES")
        with open(p, "w") as fh:
            fh.write("ROMP_CREDENTIAL_NAMES=solo\n")
        os.utime(p, ns=(time.time_ns() + 5_000_000_000, time.time_ns() + 5_000_000_000))
        self.assertEqual(es.names(), ["solo"])

    def test_the_service_env_path_is_keysources(self):
        self.assertEqual(es.service_env_path(), ks.service_env_path())
        os.environ["ROMP_SERVICE_ENV_FILE"] = os.path.join(self.d, "elsewhere.env")
        self.assertEqual(es.service_env_path(), ks.service_env_path())

    def test_the_command_variable_is_keysources_and_the_module_reads_no_other_source_switch(self):
        self.assertEqual(es.COMMAND_VAR, ks.CMD_VAR)
        self.assertEqual(es.COMMAND_VAR, "ROMP_CREDENTIAL_COMMAND")
        self.assertEqual(es.CONFIG_VARS, (es.COMMAND_VAR, es.SELECTOR_FILE_VAR, es.NAMES_VAR, es.TIMEOUT_VAR))
        for gone in ("command", "configured", "pin_mode", "_MODE_PIN"):
            self.assertFalse(hasattr(es, gone), "%s decides the mode; the module must not" % gone)

    def test_the_file_cache_holds_the_tuning_names_only(self):
        # config_value reads CONFIG_VARS and nothing else, so nothing else from the file is kept in this module's
        # memory: a credential value the file carries (a key line, op's token) is never in a dict here
        p = os.path.join(self.d, "service.env")
        with open(p, "w") as fh:
            fh.write("ANTHROPIC_API_KEY=fixture-not-a-key\nOP_SERVICE_ACCOUNT_TOKEN=fixture-not-a-token\n"
                     "ROMP_CREDENTIAL_NAMES=hp\nROMP_PERF=1\n")
        os.environ["ROMP_SERVICE_ENV_FILE"] = p
        self.assertEqual(es.names(), ["hp"])
        self.assertEqual(set(es._file_config()), {"ROMP_CREDENTIAL_NAMES"})
        self.assertEqual(set(es._FILE_CFG[1]), {"ROMP_CREDENTIAL_NAMES"}, "the cached dict itself, not a view of it")
        # Not a tuning name: refused before the environment or the file is read (until 2026-09-07 the
        # environment WAS read for any name asked, and this assertion, comparing against "", printed the
        # developer's own ambient key on a failing run). The fixture key stands in for that ambient key,
        # so the refusal is exercised whatever the shell running the suite carries.
        os.environ["ANTHROPIC_API_KEY"] = fixture_value("ambient")       # restored by tearDown
        for name in ("ANTHROPIC_API_KEY", "OP_SERVICE_ACCOUNT_TOKEN", "ROMP_PERF"):
            with self.assertRaises(ValueError):
                es.config_value(name)
        self.assertEqual(es.config_value("ROMP_CREDENTIAL_NAMES"), "hp", "a tuning name still answers")

    def test_names_split_strip_and_dedupe(self):
        os.environ["ROMP_CREDENTIAL_NAMES"] = " hp ,lp,,hp, batch "
        self.assertEqual(es.names(), ["hp", "lp", "batch"])
        os.environ.pop("ROMP_CREDENTIAL_NAMES")
        self.assertEqual(es.names(), [])

    def test_the_timeout_defaults_and_refuses_junk(self):
        self.assertEqual(es.timeout_s(), es.DEFAULT_TIMEOUT_S)
        self.assertEqual(es.DEFAULT_TIMEOUT_S, 15.0)
        self.assertEqual(es.timeout_problem(), "", "unset: the default, no problem")
        for junk in ("abc", "0", "-3", "inf", "-inf", "nan", "301", "1e9"):
            os.environ["ROMP_CREDENTIAL_TIMEOUT_S"] = junk
            self.assertEqual(es.timeout_s(), es.DEFAULT_TIMEOUT_S, repr(junk))
            problem = es.timeout_problem()
            self.assertIn("ROMP_CREDENTIAL_TIMEOUT_S is not a number of seconds between 0 and 300", problem, repr(junk))
            self.assertIn("the default 15s holds", problem)
            self.assertNotIn(junk, problem.replace("300", "").replace("15s", "").replace(" 0 ", " "),
                             "the problem names the variable, never its text")
        os.environ["ROMP_CREDENTIAL_TIMEOUT_S"] = ""
        self.assertEqual((es.timeout_s(), es.timeout_problem()), (es.DEFAULT_TIMEOUT_S, ""), "blank is unset")
        os.environ["ROMP_CREDENTIAL_TIMEOUT_S"] = "2.5"
        self.assertEqual((es.timeout_s(), es.timeout_problem()), (2.5, ""))
        os.environ["ROMP_CREDENTIAL_TIMEOUT_S"] = "300"
        self.assertEqual(es.timeout_s(), 300.0, "the ceiling itself is accepted")
        self.assertEqual(es.MAX_TIMEOUT_S, 300.0)

    def test_a_bad_timeout_rides_the_record_as_a_problem_and_the_run_uses_the_default(self):
        self.configure(self.printing({"A_TOKEN": fixture_value()}), timeout="nan")
        snap = es.status(self.src)
        self.assertTrue(snap["ok"])
        self.assertIn("ROMP_CREDENTIAL_TIMEOUT_S", snap["timeoutProblem"])
        self.assertEqual(snap["timeoutS"], es.DEFAULT_TIMEOUT_S)
        os.environ["ROMP_CREDENTIAL_TIMEOUT_S"] = "4"
        es.invalidate()
        self.assertEqual(es.current(self.src)["timeoutProblem"], "", "fixed: nothing to say")

    def test_the_selector_path_defaults_under_the_config_home(self):
        os.environ.pop("ROMP_CREDENTIAL_SELECTOR_FILE")
        os.environ["XDG_CONFIG_HOME"] = os.path.join(self.d, "xdg")
        self.assertEqual(es.selector_path(), os.path.join(self.d, "xdg", "romp", "credential-selector"))
        os.environ["ROMP_CREDENTIAL_SELECTOR_FILE"] = "~/somewhere/mode"
        self.assertEqual(es.selector_path(), os.path.expanduser("~/somewhere/mode"))

    def test_an_explicit_environ_stands_in_for_the_process_environment(self):
        os.environ["ROMP_CREDENTIAL_NAMES"] = "process"
        os.environ["ROMP_CREDENTIAL_TIMEOUT_S"] = "9"
        self.assertEqual(es.names({"ROMP_CREDENTIAL_NAMES": "given"}), ["given"])
        self.assertEqual(es.names({}), [], "an empty environ (and no file line) declares nothing")
        self.assertEqual(es.timeout_s({"ROMP_CREDENTIAL_TIMEOUT_S": "3"}), 3.0)
        self.assertEqual(es.timeout_s({}), es.DEFAULT_TIMEOUT_S)
        self.assertEqual(es.selector_path({"ROMP_CREDENTIAL_SELECTOR_FILE": os.path.join(self.d, "given")}),
                         os.path.join(self.d, "given"))


class Runner(_Lab):
    def test_success_hands_stdout_to_the_parser_only(self):
        v = fixture_value()
        r = es.run_command(self.printing({"A_TOKEN": v}), "hp", 5)
        self.assertTrue(r.ok)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.reason(5), "")
        self.assertEqual(es.parse_set(r.stdout)["values"], {"A_TOKEN": v})

    def test_a_nonzero_exit_is_a_reason_with_counts_and_the_code_never_the_bytes(self):
        v = fixture_value("stderr")
        r = es.run_command(self.script("echo '%s' >&2\nexit 3" % v), "hp", 5)
        self.assertFalse(r.ok)
        reason = r.reason(5)
        self.assertTrue(reason.startswith("exited 3 after "), reason)
        self.assertIn("stderr %d bytes" % (len(v) + 1), reason)
        self.assertNotIn(v, reason)
        self.assertNotIn("fixture", reason)

    def test_a_missing_command_is_the_shells_127(self):
        r = es.run_command(os.path.join(self.d, "no-such-command"), "hp", 5)
        self.assertEqual(r.returncode, 127)
        self.assertIn("exited 127", r.reason(5))

    def test_the_selector_is_dollar_one_of_the_command_string(self):
        # the COMMAND STRING receives $1 (the /bin/sh -c contract): a command that wants the selector
        # forwards it, `credential-cmd "$1"`, and one that ignores $1 never sees it
        s = self.script('echo "SEL=$1"\necho "ARGC=$#"')
        vals = es.parse_set(es.run_command(s + ' "$1"', "lp", 5).stdout)["values"]
        self.assertEqual(vals, {"SEL": "lp", "ARGC": "1"})
        vals = es.parse_set(es.run_command(s + ' "$@"', None, 5).stdout)["values"]
        self.assertEqual(vals, {"ARGC": "0"}, "no selector: no $1 at all (SEL= is empty and dropped)")
        vals = es.parse_set(es.run_command(s + ' "$@"', "", 5).stdout)["values"]
        self.assertEqual(vals, {"ARGC": "1"}, "an empty selector file still passes an empty $1")
        vals = es.parse_set(es.run_command(s, "lp", 5).stdout)["values"]
        self.assertEqual(vals, {"ARGC": "0"}, "a command that does not name $1 is handed nothing")

    def test_stdin_is_closed_so_a_command_that_reads_it_does_not_hang(self):
        r = es.run_command(self.script("cat\necho DONE=1"), "hp", 5)
        self.assertTrue(r.ok)
        self.assertLess(r.duration_s, 4)
        self.assertEqual(es.parse_set(r.stdout)["values"], {"DONE": "1"})

    def test_a_timeout_kills_the_whole_process_group(self):
        pgfile = os.path.join(self.d, "pgid")
        s = self.script("ps -o pgid= -p $$ | tr -d ' ' > %s\nsleep 30 &\nsleep 30" % pgfile)
        t0 = time.monotonic()
        r = es.run_command(s, "hp", 0.5)
        self.assertLess(time.monotonic() - t0, 10, "the deadline held; the reap did not wait for the sleeps")
        self.assertTrue(r.timed_out)
        self.assertFalse(r.ok)
        self.assertEqual(r.reason(0.5), "timed out after 0.5s (killed with its process group)")
        with open(pgfile) as fh:
            pgid = int(fh.read().strip())
        deadline = time.monotonic() + 5
        alive = True
        while alive and time.monotonic() < deadline:
            try:
                os.killpg(pgid, 0)
                time.sleep(0.05)
            except ProcessLookupError:
                alive = False
        self.assertFalse(alive, "the background `sleep 30 &` must die with its group, not linger under the kernel")

    def _wait_group_gone(self, pgfile):
        with open(pgfile) as fh:
            pgid = int(fh.read().strip())
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            try:
                os.killpg(pgid, 0)
                time.sleep(0.05)
            except ProcessLookupError:
                return True
        return False

    def test_the_deadline_is_on_the_process_not_on_the_pipe_a_leftover_child_holds(self):
        # the command exits 0 with a complete set but forked `sleep 30 &` without redirecting its
        # stdout: communicate() would wait for that child's EOF and call the run timed out; the
        # runner reads until the process is gone and nothing more arrives, then kills the leftovers
        v = fixture_value()
        pgfile = os.path.join(self.d, "pgid")
        s = self.script("ps -o pgid= -p $$ | tr -d ' ' > %s\nsleep 30 &\necho 'A_TOKEN=%s'\nexit 0" % (pgfile, v))
        t0 = time.monotonic()
        r = es.run_command(s, "hp", 5)
        self.assertLess(time.monotonic() - t0, 3, "the run returned when the command exited, not at the deadline")
        self.assertTrue(r.ok, r.reason(5))
        self.assertFalse(r.timed_out)
        self.assertEqual(r.returncode, 0)
        self.assertLess(r.duration_s, 3)
        self.assertEqual(es.parse_set(r.stdout)["values"], {"A_TOKEN": v}, "the set it printed is complete")
        self.assertTrue(self._wait_group_gone(pgfile), "the leftover `sleep 30 &` dies with the group")

    def test_a_leftover_that_keeps_printing_is_read_until_it_goes_quiet_then_killed(self):
        # a child that prints after the command exited: what arrives within the grace is read; the
        # exit code is the command's own
        v = fixture_value()
        s = self.script("(sleep 0.05; echo 'B_TOKEN=%s') &\necho 'A_TOKEN=%s'\nexit 0" % (v, v))
        r = es.run_command(s, "hp", 5)
        self.assertTrue(r.ok)
        self.assertEqual(es.parse_set(r.stdout)["values"], {"A_TOKEN": v, "B_TOKEN": v})

    def test_a_nonzero_exit_with_a_leftover_is_still_the_exit_codes_failure(self):
        s = self.script("sleep 30 &\nexit 4")
        r = es.run_command(s, "hp", 5)
        self.assertFalse(r.ok)
        self.assertFalse(r.timed_out)
        self.assertTrue(r.reason(5).startswith("exited 4 after "), r.reason(5))

    def test_a_leftover_that_never_stops_writing_cannot_hold_the_read_open(self):
        # the command exits 0 and leaves a child that writes to stdout without pause: the grace is a
        # window after the exit, not a quiet period, so the read ends when the window does and the
        # writer dies with the group. Before this the loop waited for `grace` seconds of silence,
        # which never came, under the module lock, so every connect behind it blocked for as long
        # as the writer lived.
        v = fixture_value()
        pgfile = os.path.join(self.d, "pgid")
        s = self.script("ps -o pgid= -p $$ | tr -d ' ' > %s\n(while :; do echo 'B_TOKEN=%s'; done) &\n"
                        "echo 'A_TOKEN=%s'\nexit 0" % (pgfile, v, v))
        t0 = time.monotonic()
        r = es.run_command(s, "hp", 5)
        self.assertLess(time.monotonic() - t0, 2, "the read ended with the grace window, not at the deadline or never")
        self.assertTrue(r.ok, r.reason(5))
        self.assertFalse(r.timed_out)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(es.parse_set(r.stdout)["values"]["A_TOKEN"], v)
        self.assertTrue(self._wait_group_gone(pgfile), "the writer dies with the group")

    def test_the_deadline_holds_while_a_leftover_is_drained_and_is_not_a_timeout_then(self):
        # the grace window is longer than what is left of the deadline: reading stops at the
        # deadline. The command itself had exited, so that is not a timeout; the run is its exit code
        v = fixture_value()
        s = self.script("(while :; do echo 'B_TOKEN=%s'; done) &\necho 'A_TOKEN=%s'\nexit 0" % (v, v))
        t0 = time.monotonic()
        r = es.run_command(s, "hp", 0.4, grace=30)
        self.assertLess(time.monotonic() - t0, 2, "the deadline held in the drained state too")
        self.assertTrue(r.ok, r.reason(0.4))
        self.assertFalse(r.timed_out, "the command had exited; only a command still running at the deadline times out")
        self.assertEqual(es.parse_set(r.stdout)["values"]["A_TOKEN"], v)
        # the command itself still running at the deadline, with the same writer behind it: a timeout
        s = self.script("(while :; do echo 'B_TOKEN=%s'; done) &\nsleep 30" % v)
        t0 = time.monotonic()
        r = es.run_command(s, "hp", 0.4)
        self.assertLess(time.monotonic() - t0, 3)
        self.assertTrue(r.timed_out)
        self.assertEqual(r.reason(0.4), "timed out after 0.4s (killed with its process group)")

    def test_a_command_that_hands_its_pipes_back_and_runs_on_is_held_to_the_deadline(self):
        # `exec >/dev/null 2>&1` in the command string returns both pipes with the command still
        # running: the read loop ends at EOF, and the deadline has to hold on the wait for the exit
        # that follows. Before this that wait was a fixed 5 s, so such a run was misclassified:
        # killed by the fallback and reported `exited -9`, or a success when it exited within the
        # 5 s but past the deadline. The redirect is in the shell the runner spawned, on purpose: a
        # script doing the same behind `sh -c <path>` leaves the outer shell holding the pipes.
        pgfile = os.path.join(self.d, "pgid")
        cmd = "ps -o pgid= -p $$ | tr -d ' ' > %s; echo A=x; exec >/dev/null 2>&1; sleep 30" % pgfile
        t0 = time.monotonic()
        r = es.run_command(cmd, "hp", 0.5)
        self.assertLess(time.monotonic() - t0, 3, "the deadline held; the wait was not the fallback's 5 s")
        self.assertTrue(r.timed_out, "still running at the deadline: a timeout, not an exit code")
        self.assertFalse(r.ok)
        self.assertEqual(r.reason(0.5), "timed out after 0.5s (killed with its process group)")
        self.assertEqual(sorted(es.parse_set(r.stdout)["values"]), ["A"], "what it printed first was read")
        self.assertTrue(self._wait_group_gone(pgfile), "the sleep dies with the group")
        # the variant that exits on its own 2 s later: past the deadline all the same, not a success
        t0 = time.monotonic()
        r = es.run_command("echo A=x; exec >/dev/null 2>&1; sleep 2", "hp", 0.5)
        self.assertLess(time.monotonic() - t0, 1.5, "not waited for past the deadline")
        self.assertTrue(r.timed_out, "the command was still running at the deadline")
        self.assertFalse(r.ok)
        # exiting BEFORE the deadline with the pipes handed back is the exit code, at the exit
        t0 = time.monotonic()
        r = es.run_command("echo A=x; exec >/dev/null 2>&1; sleep 0.2; exit 0", "hp", 5)
        self.assertLess(time.monotonic() - t0, 3, "the run returned at the exit, not at the deadline")
        self.assertTrue(r.ok, r.reason(5))
        self.assertFalse(r.timed_out)
        self.assertEqual(sorted(es.parse_set(r.stdout)["values"]), ["A"])
        r = es.run_command("echo A=x; exec >/dev/null 2>&1; sleep 0.2; exit 4", "hp", 5)
        self.assertFalse(r.ok)
        self.assertFalse(r.timed_out)
        self.assertEqual(r.reason_key(5), "exited 4")

    def test_the_reason_key_is_the_failures_kind_with_nothing_per_run(self):
        # `reason` carries the run's duration and stderr byte count; `reason_key` does not, so two
        # runs of the same failure compare equal to a change-only guard
        v = fixture_value("stderr")
        a = es.run_command(self.script("echo '%s' >&2\nexit 3" % v), "hp", 5)
        b = es.run_command(self.script("echo '%s%s' >&2\nsleep 0.15\nexit 3" % (v, v)), "hp", 5)
        self.assertNotEqual(a.reason(5), b.reason(5), "the stderr counts differ")
        self.assertEqual(a.reason_key(5), "exited 3")
        self.assertEqual(b.reason_key(5), "exited 3")
        t = es.run_command(self.script("sleep 30"), "hp", 0.3)
        self.assertEqual(t.reason_key(0.3), t.reason(0.3), "a timeout names the configured deadline, nothing per run")
        self.assertEqual(es.run_command(self.script("true"), "hp", 5).reason_key(5), "")
        r = es.RunResult(None, b"", 0, 0.01, start_error=OSError(2, "no such file"))
        self.assertEqual(r.reason_key(5), r.reason(5))
        self.assertEqual(r.reason_key(5), "could not start (errno 2)")


class Parser(_Lab):
    def test_last_wins_quotes_stripped_blank_and_comment_lines_skipped(self):
        a, b = fixture_value("a"), fixture_value("b")
        vals, bad, empty = es.parse_lines("# a comment\n\nX=%s\n  Y = '%s'  \nX=\"%s\"\n" % (a, b, b))
        self.assertEqual(vals, {"X": b, "Y": b})
        self.assertEqual((bad, empty), (0, 0))

    def test_the_rule_is_keysources_rule_for_the_key_line(self):
        v = fixture_value()
        for body in ("ANTHROPIC_API_KEY=%s\n" % v,
                     "ANTHROPIC_API_KEY='%s'\n" % v,
                     "ANTHROPIC_API_KEY=\"%s\n" % v,                 # unmatched quote: kept as part of the value
                     "ANTHROPIC_API_KEY=first\nANTHROPIC_API_KEY=%s\n" % v,
                     "ANTHROPIC_API_KEY=\n",
                     "ANTHROPIC_API_KEY=%s\nANTHROPIC_API_KEY=\n" % v,   # a later empty assignment unsets
                     "# ANTHROPIC_API_KEY=%s\n" % v,
                     "export ANTHROPIC_API_KEY=%s\n" % v,           # the file parsers take no `export`; parse_set does
                     "ANTHROPIC_API_KEY2=%s\n" % v,
                     "ANTHROPIC_API_KEY=%s=with=equals\n" % v,
                     "ANTHROPIC_API_KEY=''\n"):
            self.assertEqual(es.parse_lines(body)[0].get("ANTHROPIC_API_KEY", ""), ks.parse_key(body), repr(body))

    def test_the_commands_output_may_say_export_the_env_file_may_not(self):
        v = fixture_value()
        body = "export A_TOKEN=%s\nexport\tB_TOKEN='%s'\nexport C_TOKEN\nexportD_TOKEN=%s\n" % (v, v, v)
        out = es.parse_set(body.encode())
        self.assertEqual(out["values"], {"A_TOKEN": v, "B_TOKEN": v, "exportD_TOKEN": v},
                         "romp's own contract for the command's output; a run-together word is a plain name")
        self.assertEqual(out["bad"], 1, "`export C_TOKEN` assigns nothing")
        vals, bad, _ = es.parse_lines(body)
        self.assertEqual(vals, {"exportD_TOKEN": v}, "the env file keeps the plain form the launchers and systemd read")
        self.assertEqual(bad, 3)

    def test_lines_split_on_newlines_only_and_a_nul_is_a_bad_line(self):
        v = fixture_value()
        # CRLF is normalised; the other characters str.splitlines() would split on are part of a value
        vals, bad, _ = es.parse_lines("A=%s\r\nB=x\x0by\nC=p\x1cq\nD=m\x85n\nE=u w\n" % v)
        self.assertEqual(vals, {"A": v, "B": "x\x0by", "C": "p\x1cq", "D": "m\x85n", "E": "u w"})
        self.assertEqual(bad, 0)
        vals, bad, _ = es.parse_lines("A=%s\nB=with\x00nul\nC\x00=x\n" % v)
        self.assertEqual(vals, {"A": v}, "a value no environment can carry is never injected")
        self.assertEqual(bad, 2)

    def test_romp_names_are_dropped_and_named_not_kept(self):
        v = fixture_value()
        out = es.parse_set(("ROMP_SID=abc\nROMP_PERF=1\nA_TOKEN=%s\n" % v).encode())
        self.assertEqual(out["values"], {"A_TOKEN": v})
        self.assertEqual(out["dropped"], ["ROMP_PERF", "ROMP_SID"])
        self.assertEqual(out["droppedAuth"], [])

    def test_the_clis_own_auth_and_endpoint_names_are_dropped_and_named(self):
        # a set carrying one of these would re-route or re-bill every session behind the one door the
        # module keeps for the key; the key itself and the direct-call key are not among them
        v = fixture_value()
        body = ("ANTHROPIC_AUTH_TOKEN=%s\nCLAUDE_CODE_OAUTH_TOKEN=%s\nANTHROPIC_BASE_URL=https://example.invalid\n"
                "ANTHROPIC_CUSTOM_HEADERS=x: y\nANTHROPIC_API_KEY=%s\nANTHROPIC_LP_API_KEY=%s\nA_TOKEN=%s\n") % (v, v, v, v, v)
        out = es.parse_set(body.encode())
        self.assertEqual(out["values"], {"ANTHROPIC_API_KEY": v, "ANTHROPIC_LP_API_KEY": v, "A_TOKEN": v})
        self.assertEqual(out["droppedAuth"], ["ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL", "ANTHROPIC_CUSTOM_HEADERS",
                                              "CLAUDE_CODE_OAUTH_TOKEN"])
        self.assertEqual(out["dropped"], [])
        self.assertEqual(set(es.AUTH_NAMES), set(out["droppedAuth"]))
        self.configure(self.script("printf '%s'" % body.replace("\n", "\\n")))
        snap = es.current(self.src)
        self.assertTrue(snap["ok"])
        self.assertEqual(snap["droppedAuth"], out["droppedAuth"])
        self.assertEqual(sorted(es.injection(self.src)), ["ANTHROPIC_API_KEY", "ANTHROPIC_LP_API_KEY", "A_TOKEN"])
        self.assertNotIn(v, json.dumps(snap))

    def test_lines_that_are_not_assignments_and_empty_values_are_counted(self):
        v = fixture_value()
        out = es.parse_set("just a bare value line\n1BAD=x\nA-B=x\nEMPTY=\nQ=\"\"\nGOOD=%s\n" % v)
        self.assertEqual(out["values"], {"GOOD": v})
        self.assertEqual(out["bad"], 3)
        self.assertEqual(out["empty"], 2)

    def test_names_are_the_shell_identifier_alphabet(self):
        vals, bad, _ = es.parse_lines("_ok=1\nOK_2=2\nok.no=3\n=4\n")
        self.assertEqual(vals, {"_ok": "1", "OK_2": "2"})
        self.assertEqual(bad, 2)

    def test_fingerprints_are_twelve_hex_and_the_set_fingerprint_is_order_free(self):
        v = fixture_value()
        self.assertEqual(es.fingerprint(v), ks.fingerprint(v), "the same rule as the file source")
        self.assertRegex(es.fingerprint(v), r"^[0-9a-f]{12}$")
        self.assertEqual(es.fingerprint(""), "")
        self.assertEqual(es.set_fingerprint({}), "")
        a = es.set_fingerprint({"A": "1", "B": "2"})
        self.assertEqual(a, es.set_fingerprint({"B": "2", "A": "1"}))
        self.assertNotEqual(a, es.set_fingerprint({"A": "1", "B": "3"}))
        self.assertNotEqual(a, es.set_fingerprint({"A": "1"}))
        self.assertRegex(a, r"^[0-9a-f]{12}$")


class CacheAndCoalescing(_Lab):
    def test_one_run_serves_every_read_until_invalidated(self):
        v = fixture_value()
        self.configure(self.printing({"A_TOKEN": v, "ANTHROPIC_LP_API_KEY": fixture_value("lp")}))
        for _ in range(10):
            self.assertEqual(es.injection(self.src)["A_TOKEN"], v)
            snap = es.current(self.src)
        self.assertEqual(es._runs, 1, "the cache is event-keyed: no timer, no per-read run")
        self.assertTrue(snap["ok"])
        self.assertEqual(snap["names"], ["ANTHROPIC_LP_API_KEY", "A_TOKEN"])
        self.assertFalse(snap["hasKey"])
        self.assertEqual(snap["keyFp"], "")
        self.assertEqual(snap["setFp"], es.set_fingerprint(es.injection(self.src)))
        self.assertEqual(snap["exitCode"], 0)
        self.assertFalse(snap["stale"])
        es.invalidate("a test")
        es.injection(self.src)
        self.assertEqual(es._runs, 2, "exactly one new run per invalidation")
        es.injection(self.src)
        self.assertEqual(es._runs, 2)

    def test_the_key_is_fingerprinted_when_the_set_carries_it(self):
        k = fixture_value("key")
        self.configure(self.printing({"ANTHROPIC_API_KEY": k}))
        snap = es.current(self.src)
        self.assertTrue(snap["hasKey"])
        self.assertEqual(snap["keyFp"], es.fingerprint(k))
        self.assertEqual(es.injection(self.src)["ANTHROPIC_API_KEY"], k)

    def test_concurrent_callers_coalesce_on_one_run(self):
        v = fixture_value()
        self.configure(self.printing({"A_TOKEN": v}, extra="sleep 0.3"))
        got = []

        def read():
            got.append(es.injection(self.src).get("A_TOKEN"))

        ts = [threading.Thread(target=read) for _ in range(8)]
        for t in ts:
            t.start()
        for t in ts:
            t.join(10)
        self.assertEqual(got, [v] * 8, "every caller took the one fresh result")
        self.assertEqual(es._runs, 1, "a boot that revives many sessions runs the command once")

    def test_an_invalidation_during_a_run_makes_the_next_caller_run_again(self):
        v = fixture_value()
        self.configure(self.printing({"A_TOKEN": v}, extra="sleep 0.4"))
        seen = {}

        def read():
            seen["snap"] = es.current(self.src)

        t = threading.Thread(target=read)
        t.start()
        time.sleep(0.15)                 # the run is under way
        es.invalidate("mid-run")
        t.join(10)
        self.assertEqual(es._runs, 1)
        self.assertNotEqual(seen["snap"]["generation"], es._gen, "the result is stale on completion")
        es.current(self.src)
        self.assertEqual(es._runs, 2, "the next caller re-runs; invalidate never waited behind the run")

    def test_a_failed_run_keeps_the_previous_set_and_says_so(self):
        v = fixture_value()
        s = self.printing({"A_TOKEN": v})
        self.configure(s)
        self.assertEqual(es.injection(self.src), {"A_TOKEN": v})
        # the command now fails (the secret store is unreachable): the previous set stands, loudly
        w = fixture_value("wrong")
        self.script("echo '%s' >&2\necho 'A_TOKEN=%s'\nexit 2" % (w, w))
        es.invalidate()
        snap = es.current(self.src)
        self.assertFalse(snap["ok"])
        self.assertTrue(snap["stale"], "a failed run stands on the previous set")
        self.assertEqual(snap["names"], ["A_TOKEN"])
        self.assertEqual(snap["failures"], 1)
        self.assertTrue(snap["reason"].startswith("exited 2 after "), snap["reason"])
        self.assertEqual(es.injection(self.src), {"A_TOKEN": v}, "a failing command's stdout is never trusted")
        self.assertEqual(es._runs, 3, "the injection() after a failed run ran the command again: one run per caller")
        self.assertEqual(es.current(self.src)["failures"], 3)
        self.assertEqual(es._runs, 4)
        # recovery: the command works again, and nobody had to call invalidate() for it
        self.printing({"A_TOKEN": w})
        snap = es.current(self.src)
        self.assertTrue(snap["ok"], "the next caller after a failure re-runs and finds the store back")
        self.assertFalse(snap["stale"])
        self.assertEqual(snap["failures"], 0)
        self.assertEqual(es.injection(self.src), {"A_TOKEN": w})
        self.assertEqual(es._runs, 5)
        es.injection(self.src)
        self.assertEqual(es._runs, 5, "a successful run is cached again")

    def test_a_failed_run_is_not_served_like_a_good_one_but_concurrent_callers_still_coalesce(self):
        v = fixture_value()
        self.configure(self.printing({"A_TOKEN": v}))
        self.assertEqual(es.injection(self.src), {"A_TOKEN": v})
        self.script("sleep 0.3\nexit 2")
        es.invalidate()
        got = []

        def read():
            got.append(es.current(self.src)["ok"])

        ts = [threading.Thread(target=read) for _ in range(6)]
        for t in ts:
            t.start()
        for t in ts:
            t.join(10)
        self.assertEqual(got, [False] * 6, "every caller saw the failure")
        self.assertEqual(es._runs, 2, "the callers that waited behind the run took its result, failed or not")
        es.current(self.src)
        self.assertEqual(es._runs, 3, "a caller arriving after the failed run completed runs again")
        self.assertEqual(es.injection(self.src), {"A_TOKEN": v}, "the previous set stands throughout")

    def test_a_reader_that_declines_to_retry_takes_the_record_that_stands_with_no_run(self):
        # retry_failed=False: the kernel's non-launch readers (the judges' overlay, the resolver behind
        # work_api_key, the status reads, a cycle's rows) take the record that stands after a failed run,
        # a failure on the last good set, and run nothing; a launch (the default) re-runs. With a hung
        # store (a 15 s timeout) every one of those readers used to wait behind its own fresh run
        # (review find, 2026-09-07). Runs are counted two ways: the module's counter and a marker line
        # the fixture script appends per execution.
        v = fixture_value()
        marker = os.path.join(self.d, "ran")
        self.configure(self.printing({"A_TOKEN": v}, extra="echo x >> '%s'" % marker))
        self.assertEqual(es.injection(self.src), {"A_TOKEN": v})
        self.script("echo x >> '%s'\nexit 2" % marker)
        es.invalidate()
        snap = es.current(self.src)                            # the invalidation's run: the failure
        self.assertEqual((snap["ok"], snap["stale"]), (False, True))
        runs, n = es._runs, _count(marker)
        self.assertEqual(n, runs)
        for _ in range(5):
            snap2, vals = es.take(self.src, retry_failed=False)
            self.assertEqual((snap2["ok"], snap2["attempt"], vals), (False, snap["attempt"], {"A_TOKEN": v}))
            self.assertEqual(es.current(self.src, retry_failed=False)["attempt"], snap["attempt"])
            self.assertEqual(es.injection(self.src, retry_failed=False), {"A_TOKEN": v})
            self.assertEqual(es.resolve_key(self.src, retry_failed=False), "")
            self.assertEqual(es.status(self.src, retry_failed=False)["ok"], False)
        self.assertEqual((es._runs, _count(marker)), (runs, n), "a reader that declines to retry runs nothing")
        snap3, _vals = es.take(self.src)
        self.assertEqual((es._runs, _count(marker)), (runs + 1, n + 1), "the default re-runs")
        self.assertEqual(snap3["attempt"], snap["attempt"] + 1)
        # the events that re-run whatever the reader says: an invalidation (and, as elsewhere, a selector
        # edit or another source), since those are new information, not a retry
        es.invalidate()
        self.assertEqual(es.current(self.src, retry_failed=False)["attempt"], snap3["attempt"] + 1)
        self.assertEqual(es._runs, runs + 2)
        # recovery is found by a caller that re-runs, and then served to every reader
        self.printing({"A_TOKEN": v}, extra="echo x >> '%s'" % marker)
        self.assertFalse(es.current(self.src, retry_failed=False)["ok"], "still the record that stands")
        self.assertEqual(es._runs, runs + 2)
        self.assertTrue(es.take(self.src)[0]["ok"])
        self.assertTrue(es.current(self.src, retry_failed=False)["ok"])
        self.assertEqual((es._runs, _count(marker)), (runs + 3, n + 3))

    def test_last_ok_at_survives_failures_and_moves_on_recovery(self):
        v = fixture_value()
        self.configure(self.printing({"A_TOKEN": v}))
        ok_at = es.current(self.src)["lastOkAt"]
        self.assertIsNotNone(ok_at)
        self.assertEqual(ok_at, es.current(self.src)["at"])
        self.script("exit 2")
        es.invalidate()
        snap = es.current(self.src)
        self.assertFalse(snap["ok"])
        self.assertEqual(snap["lastOkAt"], ok_at, "the last success is remembered through failures")
        self.assertGreater(snap["at"], 0)
        time.sleep(0.01)
        self.printing({"A_TOKEN": v})
        snap = es.current(self.src)
        self.assertTrue(snap["ok"])
        self.assertGreaterEqual(snap["lastOkAt"], ok_at)
        self.assertEqual(snap["lastOkAt"], snap["at"])

    def test_take_hands_record_and_values_from_one_read(self):
        v = fixture_value()
        self.configure(self.printing({"A_TOKEN": v, "ANTHROPIC_API_KEY": fixture_value("key")}))
        snap, vals = es.take(self.src)
        self.assertEqual(es._runs, 1)
        self.assertEqual(sorted(vals), snap["names"])
        self.assertEqual(es.set_fingerprint(vals), snap["setFp"])
        self.assertEqual(es.fingerprint(vals["ANTHROPIC_API_KEY"]), snap["keyFp"])
        vals["A_TOKEN"] = "changed by a caller"
        self.assertEqual(es.take(self.src)[1]["A_TOKEN"], v, "callers get a copy")
        self.assertEqual(es._runs, 1)

    def test_the_record_carries_the_sets_identity_which_moves_only_when_a_run_hands_back_another_set(self):
        # setSeq: the set's identity within a generation, what the helper's fingerprint is cached
        # under beside the generation. invalidate() moves the generation and not this; a run that
        # hands back the same set leaves it; a run that hands back another set moves it; a failed
        # run keeps the set and so moves nothing.
        v = fixture_value()
        self.configure(self.printing({"A_TOKEN": v}))
        s0 = es.current(self.src)
        seq0 = s0["setSeq"]
        es.invalidate()
        s1 = es.current(self.src)
        self.assertEqual((s1["generation"], s1["setSeq"]), (s0["generation"] + 1, seq0),
                         "the same set again: the generation moved, the identity did not")
        self.script("exit 2")
        es.invalidate()
        s2 = es.current(self.src)
        self.assertEqual((s2["ok"], s2["stale"], s2["setSeq"]), (False, True, seq0), "a failed run keeps the set")
        self.printing({"A_TOKEN": fixture_value("rotated")})
        s3 = es.current(self.src)
        self.assertEqual((s3["ok"], s3["generation"], s3["setSeq"]), (True, s2["generation"], seq0 + 1),
                         "the retry handed back another set under the same generation")
        self.printing({"A_TOKEN": v, "B_TOKEN": fixture_value()})
        es.invalidate()
        s4 = es.current(self.src)
        self.assertEqual((s4["setSeq"], sorted(s4["names"])), (seq0 + 2, ["A_TOKEN", "B_TOKEN"]))
        self.assertEqual(es.status(self.src)["setSeq"], seq0 + 2, "status() carries it too")
        self.assertEqual(es.take(self.src)[0]["setSeq"], seq0 + 2, "and take()'s record")

    def test_a_hand_edit_of_the_selector_file_re_runs_the_command(self):
        # the selector file may be one an apiKeyHelper already reads and an operator edits by hand:
        # its stat identity is part of the cache identity, so the edit is an event, not a wait
        self.configure(self.script('echo "SEL=${1:-none}"') + ' "$1"', names="hp,lp")
        self.assertEqual(es.injection(self.src), {"SEL": "none"})
        self.select("hp")
        self.assertEqual(es.injection(self.src), {"SEL": "hp"}, "the file appeared: a run")
        self.assertEqual(es._runs, 2)
        es.injection(self.src)
        self.assertEqual(es._runs, 2, "unchanged file, no run")
        with open(os.environ["ROMP_CREDENTIAL_SELECTOR_FILE"], "w") as fh:
            fh.write("lp\n")
        os.utime(os.environ["ROMP_CREDENTIAL_SELECTOR_FILE"], ns=(time.time_ns() + 10**9, time.time_ns() + 10**9))
        self.assertEqual(es.injection(self.src), {"SEL": "lp"}, "the edit re-ran the command")
        self.assertEqual(es._runs, 3)
        os.unlink(os.environ["ROMP_CREDENTIAL_SELECTOR_FILE"])
        self.assertEqual(es.injection(self.src), {"SEL": "none"}, "and its removal")
        self.assertEqual(es._runs, 4)

    def test_an_authentication_failure_invalidates_once_per_credential(self):
        # a revoked credential: the store keeps handing back the same set, and every judge call and
        # launch reports a refusal. The first re-runs the command, the rest are not new information
        v = fixture_value()
        self.configure(self.printing({"ANTHROPIC_API_KEY": v}))
        self.assertEqual(es.injection(self.src)["ANTHROPIC_API_KEY"], v)
        self.assertTrue(es.invalidate_for_auth_failure("a 401"), "the first refusal fires")
        self.assertEqual(es.injection(self.src)["ANTHROPIC_API_KEY"], v)
        self.assertEqual(es._runs, 2, "and the next caller re-runs")
        for _ in range(5):
            self.assertFalse(es.invalidate_for_auth_failure("another 401"), "the same set again: not new information")
            es.injection(self.src)
        self.assertEqual(es._runs, 2, "a burst of refusals is one run")
        # a rotation the re-run reveals is new information
        w = fixture_value("rotated")
        self.printing({"ANTHROPIC_API_KEY": w})
        es.invalidate("operator refresh")                  # an operator's invalidation re-arms the path
        self.assertEqual(es.injection(self.src)["ANTHROPIC_API_KEY"], w)
        self.assertEqual(es._runs, 3)
        self.assertTrue(es.invalidate_for_auth_failure("a 401 on the new set"), "a different set: fires once")
        es.injection(self.src)
        self.assertEqual(es._runs, 4)
        self.assertFalse(es.invalidate_for_auth_failure("and again"))
        es.injection(self.src)
        self.assertEqual(es._runs, 4)

    def test_a_helper_rotation_re_arms_the_authentication_failure_path(self):
        self.configure(self.printing({"A_TOKEN": fixture_value()}))
        a, b = fixture_value("a"), fixture_value("b")
        self.helper("echo '%s'" % a)
        es.current(self.src)
        es.helper_fingerprint(source=self.src)
        self.assertTrue(es.invalidate_for_auth_failure("401"))
        self.assertFalse(es.invalidate_for_auth_failure("401"), "same set, same helper output as last fingerprinted")
        self.helper("echo '%s'" % b)
        es.helper_fingerprint(source=self.src)               # the invalidation above made this a fresh run: b
        self.assertTrue(es.invalidate_for_auth_failure("401"), "the helper now prints another credential")

    def test_a_success_on_the_refused_credential_re_arms_the_authentication_failure_path(self):
        # 401, run, same set, a later success, a later 401: the second refusal is new information
        # again (a rotation may have landed behind the same name between the two), so it re-runs.
        # Without the success the suppression held for the life of an unchanged set, and a refusal
        # hours later never re-ran the command. Keyed on the credential: a success on another
        # fingerprint (a session still on the set from before a rotation) re-arms nothing.
        k, role = fixture_value("key"), fixture_value("role")
        self.configure(self.printing({"ANTHROPIC_API_KEY": k, "A_TOKEN": role}))
        es.injection(self.src)
        self.assertFalse(es.credential_auth_ok(es.fingerprint(k)), "nothing to re-arm before a refusal")
        self.assertTrue(es.invalidate_for_auth_failure("401"))
        es.injection(self.src)
        self.assertEqual(es._runs, 2)
        self.assertFalse(es.invalidate_for_auth_failure("401 again"), "the same set: suppressed")
        self.assertFalse(es.credential_auth_ok(es.fingerprint(fixture_value("other"))),
                         "a success on another credential says nothing about this set")
        self.assertFalse(es.invalidate_for_auth_failure("401 again"), "still suppressed")
        self.assertTrue(es.credential_auth_ok(es.fingerprint(k)), "a success on the refused key re-arms")
        self.assertFalse(es.credential_auth_ok(es.fingerprint(k)), "and there is nothing to re-arm twice")
        self.assertTrue(es.invalidate_for_auth_failure("401 later"), "so the later refusal fires")
        es.injection(self.src)
        self.assertEqual(es._runs, 3, "and the command runs again")
        # a success on the set as a whole (a judge call, whose environment is the set) re-arms too,
        # and so does one on any value of the set (a role variable's fingerprint)
        self.assertFalse(es.invalidate_for_auth_failure("401"))
        self.assertTrue(es.credential_auth_ok())
        self.assertTrue(es.invalidate_for_auth_failure("401"))
        es.injection(self.src)
        self.assertEqual(es._runs, 4)
        self.assertFalse(es.invalidate_for_auth_failure("401"))
        self.assertTrue(es.credential_auth_ok(es.fingerprint(role)))
        self.assertTrue(es.invalidate_for_auth_failure("401"))
        es.injection(self.src)
        self.assertEqual(es._runs, 5)
        self.assertNotIn(k, str(es.current(self.src)))

    def test_a_success_through_the_helper_re_arms_the_path_the_helper_is_part_of(self):
        h = fixture_value("helper")
        self.configure(self.printing({"A_TOKEN": fixture_value()}))
        self.helper("echo '%s'" % h)
        es.current(self.src)
        es.helper_fingerprint(source=self.src)
        self.assertTrue(es.invalidate_for_auth_failure("401"))
        es.helper_fingerprint(source=self.src)
        self.assertFalse(es.invalidate_for_auth_failure("401"))
        self.assertTrue(es.credential_auth_ok(es.fingerprint(h)), "the helper's credential is the one the refusal was for")
        self.assertTrue(es.invalidate_for_auth_failure("401"))

    def test_a_refusal_of_a_credential_that_is_not_the_current_one_invalidates_nothing(self):
        # the reproduction: a session still running on the key from before a rotation is refused on
        # every turn, and sessions on the current key complete turns between. Before this each such
        # refusal invalidated the CURRENT set and each success re-armed the path, so the uncycled
        # session cost one command run and one helper run per turn for as long as it was left.
        old, new, h = fixture_value("old"), fixture_value("new"), fixture_value("helper")
        self.configure(self.printing({"ANTHROPIC_API_KEY": old}))
        self.helper("echo '%s'" % h)
        old_fp = es.current(self.src)["keyFp"]                 # the stamp of a session launched now
        self.assertEqual(old_fp, es.fingerprint(old))
        self.printing({"ANTHROPIC_API_KEY": new})
        es.invalidate("the operator's refresh after the rotation")
        new_fp = es.current(self.src)["keyFp"]
        self.assertEqual(new_fp, es.fingerprint(new))
        es.helper_fingerprint(source=self.src)
        runs, hruns = es._runs, es.helper_runs()
        for _ in range(5):
            self.assertFalse(es.invalidate_for_auth_failure("401 on a turn", old_fp),
                             "neither a value of the current set nor the helper's output: nothing to re-run for")
            es.current(self.src)
            es.helper_fingerprint(source=self.src)
            self.assertFalse(es.credential_auth_ok(new_fp), "nothing was armed for the success to re-arm")
        self.assertEqual((es._runs, es.helper_runs()), (runs, hruns), "no command run and no helper run for the burst")
        # a refusal of the CURRENT key still fires, once
        self.assertTrue(es.invalidate_for_auth_failure("401", new_fp))
        es.current(self.src)
        es.helper_fingerprint(source=self.src)
        self.assertEqual((es._runs, es.helper_runs()), (runs + 1, hruns + 1))
        self.assertFalse(es.invalidate_for_auth_failure("401", new_fp), "the same set again: suppressed")
        self.assertFalse(es.invalidate_for_auth_failure("401", old_fp), "and the stale stamp still says nothing")
        self.assertTrue(es.credential_auth_ok(new_fp), "the success on the refused key re-arms")
        # no stamp (a judge call: the set as a whole) keys on the set and helper fingerprints alone
        self.assertTrue(es.invalidate_for_auth_failure("401"))
        es.current(self.src)
        self.assertEqual(es._runs, runs + 2)
        self.assertNotIn(old, str(es.current(self.src)))
        self.assertNotIn(new, str(es.current(self.src)))

    def test_a_refusal_stamped_with_a_pre_rotation_helper_output_invalidates_nothing_either(self):
        # the helper-billed shape of the same: a session stamped with the helper's output from
        # before a rotation behind the helper, refused on every turn
        a, b = fixture_value("a"), fixture_value("b")
        self.configure(self.printing({"A_TOKEN": fixture_value("role")}))
        self.helper("echo '%s'" % a)
        es.current(self.src)
        old_fp = es.helper_fingerprint(source=self.src)[0]
        self.assertEqual(old_fp, es.fingerprint(a))
        self.helper("echo '%s'" % b)
        es.invalidate("refresh")
        es.current(self.src)
        self.assertEqual(es.helper_fingerprint(source=self.src)[0], es.fingerprint(b))
        runs, hruns = es._runs, es.helper_runs()
        for _ in range(3):
            self.assertFalse(es.invalidate_for_auth_failure("401", old_fp))
            es.current(self.src)
            es.helper_fingerprint(source=self.src)
        self.assertEqual((es._runs, es.helper_runs()), (runs, hruns))
        self.assertTrue(es.invalidate_for_auth_failure("401", es.fingerprint(b)), "the current helper output: fires once")
        es.current(self.src)
        es.helper_fingerprint(source=self.src)
        self.assertEqual((es._runs, es.helper_runs()), (runs + 1, hruns + 1))
        self.assertFalse(es.invalidate_for_auth_failure("401", es.fingerprint(b)))

    def test_the_record_carries_the_failures_kind_beside_the_full_reason(self):
        # reason: the run's detail (duration, stderr bytes), for api-health's lastRun and the reports;
        # reasonKey: the kind alone, for a change-only log guard
        v = fixture_value("stderr")
        self.configure(self.script("echo '%s' >&2\nexit 3" % v))
        snap = es.current(self.src)
        self.assertTrue(snap["reason"].startswith("exited 3 after "), snap["reason"])
        self.assertIn("stderr %d bytes" % (len(v) + 1), snap["reason"])
        self.assertEqual(snap["reasonKey"], "exited 3")
        for body, key in (("true", "printed nothing"),
                          ("echo 'a bare value line'\necho 'and another'", "printed lines, none NAME=VALUE"),
                          ("echo '# only a comment'", "printed no usable NAME=VALUE line")):
            es._reset()
            self.configure(self.script(body))
            snap = es.current(self.src)
            self.assertEqual(snap["reasonKey"], key, body)
            self.assertTrue(snap["reason"].startswith("printed "), (body, snap["reason"]))
        es._reset()
        self.configure(self.script("sleep 30"), timeout=0.5)
        snap = es.current(self.src)
        self.assertEqual(snap["reasonKey"], snap["reason"])
        es._reset()
        self.select("zz")
        self.configure(self.script("true"), names="hp,lp")
        snap = es.current(self.src)
        self.assertEqual(snap["reasonKey"], snap["reason"], "a selector reason carries nothing per run")
        self.assertIn("outside", snap["reason"])
        es._reset()
        os.unlink(os.environ["ROMP_CREDENTIAL_SELECTOR_FILE"])
        os.environ.pop("ROMP_CREDENTIAL_NAMES")
        self.configure(self.printing({"A_TOKEN": fixture_value()}))
        snap = es.current(self.src)
        self.assertTrue(snap["ok"])
        self.assertEqual((snap["reason"], snap["reasonKey"]), ("", ""))
        self.assertNotIn(v, json.dumps(snap))

    def test_a_first_failure_is_an_empty_set_with_a_reason(self):
        for body, reason in (("exit 5", "exited 5 after "),
                             ("true", "printed nothing"),
                             ("echo 'a bare value line'\necho 'and another'", "printed 2 lines, none NAME=VALUE"),
                             ("echo '# only a comment'", "printed no usable NAME=VALUE line"),
                             ("echo 'ROMP_ONLY=x'", "printed no usable NAME=VALUE line")):
            es._reset()
            self.configure(self.script(body))
            snap = es.current(self.src)
            self.assertFalse(snap["ok"], body)
            self.assertTrue(snap["reason"].startswith(reason), (body, snap["reason"]))
            self.assertFalse(snap["stale"])
            self.assertEqual(es.injection(self.src), {}, body)

    def test_a_timeout_through_the_cache_is_a_reason_too(self):
        self.configure(self.script("sleep 30"), timeout=0.5)
        snap = es.current(self.src)
        self.assertFalse(snap["ok"])
        self.assertTrue(snap["timedOut"])
        self.assertEqual(snap["reason"], "timed out after 0.5s (killed with its process group)")

    def test_dropped_romp_names_are_reported_by_name_and_the_rest_kept(self):
        v = fixture_value()
        self.configure(self.printing({"ROMP_SID": "forged", "ROMP_STATE_DIR": "/nonexistent/x", "A_TOKEN": v}))
        snap = es.current(self.src)
        self.assertTrue(snap["ok"])
        self.assertEqual(snap["dropped"], ["ROMP_SID", "ROMP_STATE_DIR"])
        self.assertEqual(es.injection(self.src), {"A_TOKEN": v})

    def test_status_adds_the_configuration_and_stays_value_free(self):
        v = fixture_value()
        self.configure(self.printing({"A_TOKEN": v}), names="hp,lp", timeout=9)
        st = es.status(self.src)
        self.assertEqual(st["declaredNames"], ["hp", "lp"])
        self.assertEqual(st["timeoutS"], 9.0)
        self.assertEqual(st["selectorFile"], os.environ["ROMP_CREDENTIAL_SELECTOR_FILE"])
        self.assertNotIn(v, json.dumps(st))


class Selector(_Lab):
    def test_a_missing_file_is_no_selector_and_the_command_gets_an_empty_dollar_one(self):
        self.assertEqual(es.read_selector(), ("", ""))
        self.configure(self.script('echo "SEL=${1:-unset}"') + ' "$1"')
        self.assertEqual(es.injection(self.src), {"SEL": "unset"})
        self.assertEqual(es.current(self.src)["selector"], "")

    def test_the_token_is_read_and_passed_as_dollar_one(self):
        self.select("  hp\n")
        self.assertEqual(es.read_selector(), ("hp", ""))
        self.configure(self.script('echo "SEL=$1"') + ' "$1"', names="hp,lp")
        self.assertEqual(es.injection(self.src), {"SEL": "hp"})
        snap = es.current(self.src)
        self.assertEqual(snap["selector"], "hp", "declared: rendered by name")
        self.assertEqual(snap["selectorNote"], "")
        self.assertEqual(es.selector_label(snap), "hp")

    def test_an_undeclared_token_is_rendered_by_length_only(self):
        # with no names declared the command still gets the token as $1, but nothing renders it: an
        # undeclared token could be anything, a pasted secret included
        v = fixture_value("pasted")
        self.select(v)
        self.configure(self.script('echo "SEL=$1"') + ' "$1"')
        self.assertEqual(es.injection(self.src), {"SEL": v})
        snap = es.current(self.src)
        self.assertEqual(snap["selector"], "")
        self.assertEqual(snap["selectorNote"], "(undeclared, %d chars)" % len(v))
        self.assertEqual(es.selector_label(snap), "(undeclared, %d chars)" % len(v))
        self.assertNotIn(v, json.dumps(snap))
        self.assertEqual(es.selector_label({}), "")
        self.assertEqual(es.selector_label({"selector": "", "selectorNote": ""}), "")

    def test_a_non_token_is_an_error_carrying_a_byte_count_never_the_content(self):
        v = fixture_value("pasted")
        self.select(v + " with spaces\n")
        tok, err = es.read_selector()
        self.assertEqual(tok, "")
        self.assertEqual(err, "the selector file holds something that is not a name (%d bytes)" % (len(v) + 13))
        self.assertNotIn(v, err)
        self.configure(self.script("echo A=1"))
        snap = es.current(self.src)
        self.assertFalse(snap["ok"])
        self.assertEqual(snap["reason"], err)
        self.assertEqual(es._runs, 0, "nothing runs on a bad selector")

    def test_an_undeclared_name_is_refused_before_the_command_runs(self):
        self.select("other")
        self.configure(self.script("echo A=1"), names="hp,lp")
        snap = es.current(self.src)
        self.assertFalse(snap["ok"])
        self.assertEqual(snap["reason"], "the selector file holds a name outside ROMP_CREDENTIAL_NAMES")
        self.assertNotIn("other", snap["reason"])
        self.assertEqual(es._runs, 0)
        self.assertEqual(es.injection(self.src), {})
        self.select("lp")
        es.invalidate()
        self.assertEqual(es.injection(self.src), {"A": "1"})
        self.assertEqual(es._runs, 1)

    def test_with_no_names_declared_the_kernel_still_passes_the_token_but_no_switch_may_select_one(self):
        self.select("anything.goes-1")
        self.configure(self.script('echo "SEL=$1"') + ' "$1"')
        self.assertEqual(es.injection(self.src), {"SEL": "anything.goes-1"})
        self.assertFalse(es.selector_allowed("anything.goes-1"), "nothing declared: `romp keyswap <name>` has nothing to check against")

    def test_validity_is_the_one_token_regex(self):
        for ok in ("hp", "a", "a.b-c_d", "A" * 64, "x1", "1x"):
            self.assertTrue(es.valid_selector(ok), ok)
        for bad in ("", "-x", ".x", "_x", "A" * 65, "a b", "a/b", "a\n", "a=b", None, 3):
            self.assertFalse(es.valid_selector(bad), repr(bad))

    def test_selector_allowed_requires_a_declaration(self):
        self.assertFalse(es.selector_allowed("hp"), "undeclared: refused")
        os.environ["ROMP_CREDENTIAL_NAMES"] = "hp,lp"
        self.assertTrue(es.selector_allowed("hp"))
        self.assertTrue(es.selector_allowed("lp"))
        self.assertFalse(es.selector_allowed("other"))
        self.assertFalse(es.selector_allowed("a b"))

    def test_the_write_is_atomic_0600_creates_the_directory_and_leaves_no_temp_file(self):
        p = os.path.join(self.d, "deep", "er", "selector")
        os.environ["ROMP_CREDENTIAL_SELECTOR_FILE"] = p
        r = es.write_selector("hp")
        self.assertEqual(r, {"path": p, "target": p, "old": "", "new": "hp"})
        with open(p) as fh:
            self.assertEqual(fh.read(), "hp\n")
        self.assertEqual(stat.S_IMODE(os.stat(p).st_mode), 0o600)
        self.assertEqual(os.listdir(os.path.dirname(p)), ["selector"], "no temp file left behind")
        r = es.write_selector("lp")
        self.assertEqual((r["old"], r["new"]), ("hp", "lp"))
        self.assertEqual(es.read_selector(), ("lp", ""))

    def test_the_write_goes_through_a_symlink(self):
        target = os.path.join(self.d, "helper-mode")
        with open(target, "w") as fh:
            fh.write("hp\n")
        link = os.path.join(self.d, "selector")
        os.symlink(target, link)
        r = es.write_selector("lp", link)
        self.assertEqual(r["target"], target)
        self.assertTrue(os.path.islink(link), "the link survives: a dotfiles-managed selector stays managed")
        with open(target) as fh:
            self.assertEqual(fh.read(), "lp\n")

    def test_the_write_refuses_a_non_token_and_touches_nothing(self):
        self.select("hp")
        for bad in ("", "two words", fixture_value() + " " + fixture_value(), "a/b", "x" * 65):
            with self.assertRaises(ValueError):
                es.write_selector(bad)
        self.assertEqual(es.read_selector(), ("hp", ""))


class SourceIdentity(_Lab):
    """The source is the KeySource keysource selected. The cache identity is (generation, the source's
    fingerprint, the selector file's stat identity), so a swap to another command or to the reference
    re-runs or empties by construction, with no mode switch of the module's own."""

    def test_none_and_a_source_of_another_kind_are_an_empty_set_with_no_run(self):
        others = (None, ks.KeySource("none"), ks.KeySource("file", fixture_value("key")),
                  ks.KeySource("environment", fixture_value("key")),
                  ks.KeySource("op", "op://vault/item/field"), ks.KeySource("error", error="unreadable"))
        for src in others:
            label = src.kind if src is not None else "None"
            self.assertEqual(es.injection(src), {}, label)
            snap = es.current(src)
            self.assertFalse(snap["configured"], label)
            self.assertIsNone(snap["ok"], label)
            self.assertEqual(snap["sourceFp"], "", label)
            self.assertEqual(snap["names"], [], label)
            self.assertEqual(es.take(src)[1], {}, label)
            self.assertEqual(es.resolve_key(src), "", label)
        self.assertEqual(es._runs, 0, "nothing runs for a source that is not a command")

    def test_another_command_text_re_runs_from_an_empty_set_by_construction(self):
        a, b = fixture_value("a"), fixture_value("b")
        src_a = ks.KeySource("command", self.printing({"A_TOKEN": a}, name="a.sh"))
        src_b = ks.KeySource("command", self.printing({"A_TOKEN": b}, name="b.sh"))
        self.assertNotEqual(src_a.fingerprint(), src_b.fingerprint())
        self.assertEqual(es.injection(src_a), {"A_TOKEN": a})
        self.assertEqual(es.current(src_a)["sourceFp"], src_a.fingerprint())
        self.assertEqual(es._runs, 1)
        self.assertEqual(es.injection(src_b), {"A_TOKEN": b}, "another text: a run, with no invalidate()")
        self.assertEqual(es._runs, 2)
        self.assertEqual(es.current(src_b)["sourceFp"], src_b.fingerprint())
        self.assertEqual(es._runs, 2, "the same source again is served from the cache")
        self.assertEqual(es.injection(src_a), {"A_TOKEN": a}, "back again: a run; nothing of the other set is kept")
        self.assertEqual(es._runs, 3)
        # a failing command under a new text stands on nothing: keep-last-good is per source
        src_f = ks.KeySource("command", self.script("exit 2", name="f.sh"))
        snap, vals = es.take(src_f)
        self.assertEqual((snap["ok"], snap["stale"], vals), (False, False, {}),
                         "the previous source's set does not stand in for a new source's failed run")
        self.assertEqual(snap["names"], [])
        self.assertEqual(es._runs, 4)
        self.assertNotIn(a, json.dumps(snap) + json.dumps(vals))

    def test_none_after_a_command_empties_the_set_without_a_run(self):
        v = fixture_value()
        self.configure(self.printing({"A_TOKEN": v}))
        self.assertEqual(es.injection(self.src), {"A_TOKEN": v})
        self.assertEqual(es.injection(None), {}, "the source is no longer a command: an empty set")
        self.assertEqual(es._runs, 1, "and no run")
        snap = es.current(None)
        self.assertFalse(snap["configured"])
        self.assertEqual((snap["names"], snap["setFp"], snap["stale"]), ([], "", False))
        self.assertEqual(es.injection(self.src), {"A_TOKEN": v}, "the command again: it runs again")
        self.assertEqual(es._runs, 2)

    def test_a_reader_that_selected_another_kind_releases_the_set_without_a_run(self):
        # the kernel's readers gate on the kind and never reach take() with a source of another kind, so
        # after a swap from the command to the reference or a key line the last set stayed resident for
        # the process's life (review find, 2026-09-07): release_for is their door, and it runs nothing
        v = fixture_value()
        self.configure(self.printing({"A_TOKEN": v}))
        self.assertEqual(es.injection(self.src), {"A_TOKEN": v})
        self.assertFalse(es.release_for(self.src), "the command itself: nothing to release")
        self.assertEqual(es._values, {"A_TOKEN": v})
        self.assertTrue(es.release_for(ks.KeySource("file", fixture_value("key"))))
        self.assertEqual(es._values, {}, "no credential of a source no longer selected stays resident")
        self.assertFalse(es._snap["configured"])
        self.assertEqual(es._runs, 1, "no run")
        self.assertFalse(es.release_for(ks.KeySource("op", "op://vault/item/field")), "already released")
        self.assertFalse(es.release_for(None))
        self.assertEqual(es.injection(self.src), {"A_TOKEN": v}, "the command again: it runs again")
        self.assertEqual(es._runs, 2)

    def test_an_invalid_command_text_is_a_reason_and_nothing_runs(self):
        for bad in ("", "   ", "echo A=1\necho B=2", "echo A=1\r", "x" * (ks.CMD_MAX_BYTES + 1)):
            es._reset()
            src = ks.KeySource("command", bad)
            snap = es.current(src)
            self.assertTrue(snap["configured"], repr(bad[:20]))
            self.assertFalse(snap["ok"], repr(bad[:20]))
            self.assertIn("ROMP_CREDENTIAL_COMMAND must be one non-empty line", snap["reason"], repr(bad[:20]))
            self.assertEqual(snap["reasonKey"], snap["reason"], "a configuration reason carries nothing per run")
            self.assertEqual(snap["sourceFp"], src.fingerprint())
            self.assertEqual(es.injection(src), {})
            self.assertEqual(es.resolve_key(src), "", "never raised: the launch injects nothing")
        self.assertEqual(es._runs, 0)

    def test_the_record_carries_the_source_fingerprint_and_never_the_text(self):
        marker = fixture_value("in-the-command-text")
        cmd = self.printing({"A_TOKEN": fixture_value()}) + " # " + marker
        src = ks.KeySource("command", cmd)
        snap = es.status(src)
        self.assertTrue(snap["ok"])
        self.assertEqual(snap["sourceFp"], src.fingerprint())
        self.assertEqual(snap["sourceFp"], ks.fingerprint("command:" + cmd), "keysource's rule for the command kind")
        self.assertEqual(snap["sourceFp"], es.take(src)[0]["sourceFp"])
        self.assertNotIn(marker, json.dumps(snap) + repr(es._snap))
        self.assertNotIn("cmd.sh", json.dumps(snap) + repr(es._snap), "not even the script's path")

    def test_the_source_keysource_selects_from_the_environment_door_is_the_one_run(self):
        # a foreground manager with ROMP_CREDENTIAL_COMMAND in its environment: keysource selects the
        # command kind, and the source it hands back is what this module runs
        v = fixture_value()
        os.environ["ROMP_CREDENTIAL_COMMAND"] = self.printing({"A_TOKEN": v})
        try:
            src = ks.select_source()
            self.assertEqual(src.kind, "command")
            self.assertEqual(es.injection(src), {"A_TOKEN": v})
            self.assertEqual(es.current(src)["sourceFp"], src.fingerprint())
            self.assertEqual(es._runs, 1)
        finally:
            os.environ.pop("ROMP_CREDENTIAL_COMMAND", None)
            ks._ENV_PROVIDER_PATHS.clear()
            ks._AUTHORITATIVE_PATHS.clear()
            ks._CACHE = ((), "")
        # the reference, keysource's built-in default command, runs nothing here: the op kind reads per
        # operation through KeySource.resolve, and this module holds no set for it
        self.assertEqual(es.injection(ks.KeySource("op", "op://vault/item/field")), {})
        self.assertEqual(es._runs, 1)

    def test_resolve_key_is_the_sets_key_or_empty_and_never_raises_on_a_failed_run(self):
        k = fixture_value("key")
        self.configure(self.printing({"ANTHROPIC_API_KEY": k, "A_TOKEN": fixture_value("role")}))
        self.assertEqual(es.resolve_key(self.src), k)
        self.assertEqual(es._runs, 1)
        self.assertEqual(es.resolve_key(self.src), k)
        self.assertEqual(es._runs, 1, "cached like every other reader")
        self.script("exit 3")
        es.invalidate()
        self.assertEqual(es.resolve_key(self.src), k, "a failed run: the last good set's key, no exception")
        self.assertFalse(es.current(self.src)["ok"])
        role_only = ks.KeySource("command", self.printing({"A_TOKEN": fixture_value()}, name="role.sh"))
        self.assertEqual(es.resolve_key(role_only), "", "no key in the set: the apiKeyHelper or the login bills")
        never = ks.KeySource("command", self.script("exit 5", name="never.sh"))
        self.assertEqual(es.resolve_key(never), "", "a command that never succeeded: nothing to inject")
        self.assertEqual(es.resolve_key(None), "")

    def test_keysource_resolve_for_the_command_kind_goes_through_the_resolver_hook(self):
        # the seam: keysource never loads this module; KeySource.resolve dispatches the command kind to
        # COMMAND_RESOLVER, which the kernel wires to resolve_key at import. Unwired, it raises.
        k = fixture_value("key")
        self.configure(self.printing({"ANTHROPIC_API_KEY": k}))
        was = ks.COMMAND_RESOLVER
        ks.COMMAND_RESOLVER = None
        try:
            with self.assertRaises(ks.KeySourceError) as cm:
                self.src.resolve()
            self.assertIn("resolved by the kernel's command source", str(cm.exception))
            self.assertEqual(es._runs, 0, "unwired: nothing ran")
            ks.COMMAND_RESOLVER = es.resolve_key
            self.assertEqual(self.src.resolve(), k)
            self.assertEqual(es._runs, 1)
            self.script("exit 3")
            es.invalidate()
            self.assertEqual(self.src.resolve(), k, "the hook never raises for a failed run either")
        finally:
            ks.COMMAND_RESOLVER = was


class HelperFingerprint(_Lab):
    def test_no_settings_json_is_no_fingerprint_with_a_reason(self):
        fp, reason = es.helper_fingerprint()
        self.assertEqual(fp, "")
        self.assertTrue(reason.startswith("no apiKeyHelper in "), reason)
        self.assertIn(os.environ["CLAUDE_CONFIG_DIR"], reason)
        self.assertEqual(es.helper_command(), "")
        self.assertEqual(es.helper_runs(), 0)

    def test_a_settings_json_without_the_key_or_with_junk_is_no_helper(self):
        d = os.environ["CLAUDE_CONFIG_DIR"]
        os.makedirs(d)
        for body in ("{}", '{"apiKeyHelper": 3}', '{"apiKeyHelper": ""}', "not json", "[]"):
            with open(os.path.join(d, "settings.json"), "w") as fh:
                fh.write(body)
            self.assertEqual(es.helper_command(), "", body)

    def test_the_helper_is_run_hashed_inside_and_cached(self):
        v = fixture_value("helper")
        self.helper("echo '%s'" % v)
        fp, reason = es.helper_fingerprint()
        self.assertEqual(fp, es.fingerprint(v))
        self.assertEqual(reason, "")
        self.assertEqual(es.helper_runs(), 1)
        self.assertEqual(es.helper_fingerprint(), (fp, ""))
        self.assertEqual(es.helper_runs(), 1, "cached until an invalidation")
        es.invalidate()
        self.assertEqual(es.helper_fingerprint(), (fp, ""))
        self.assertEqual(es.helper_runs(), 2)

    def test_a_rotation_behind_the_helper_is_a_new_fingerprint(self):
        a, b = fixture_value("a"), fixture_value("b")
        self.helper("echo '%s'" % a)
        fa, _ = es.helper_fingerprint()
        self.helper("echo '%s'" % b)
        self.assertEqual(es.helper_fingerprint()[0], fa, "cached: the rotation shows on the next invalidation")
        es.invalidate()
        fb, _ = es.helper_fingerprint()
        self.assertNotEqual(fa, fb)
        self.assertEqual(fb, es.fingerprint(b))

    def test_output_that_is_not_one_token_is_refused_with_a_count(self):
        v = fixture_value()
        self.helper("echo 'A=%s'\necho 'B=%s'" % (v, v))
        fp, reason = es.helper_fingerprint()
        self.assertEqual(fp, "")
        self.assertEqual(reason, "printed 2 non-empty lines (one token expected)")
        self.assertNotIn(v, reason)
        es.invalidate()
        self.helper("echo 'two words'")
        fp, reason = es.helper_fingerprint()
        self.assertEqual(fp, "")
        self.assertEqual(reason, "printed something that is not a printable token (9 bytes)")
        es.invalidate()
        self.helper("true")
        self.assertEqual(es.helper_fingerprint(), ("", "printed 0 non-empty lines (one token expected)"))

    def test_a_failing_or_slow_helper_is_a_reason_with_counts(self):
        v = fixture_value()
        self.helper("echo '%s' >&2\nexit 4" % v)
        fp, reason = es.helper_fingerprint()
        self.assertEqual(fp, "")
        self.assertTrue(reason.startswith("exited 4 after "), reason)
        self.assertNotIn(v, reason)
        es.invalidate()
        self.helper("sleep 30")
        fp, reason = es.helper_fingerprint(timeout=0.5)
        self.assertEqual(fp, "")
        self.assertIn("timed out after 0.5s", reason)

    def test_a_settings_local_json_beside_the_user_file_is_not_read(self):
        # Claude Code has no user-level local settings file: settings.local.json is a PROJECT layer
        # (a repository's .claude/), and one placed under CLAUDE_CONFIG_DIR is read by nothing, so a
        # fingerprint taken from it would be of a credential no session bills
        a, b = fixture_value("a"), fixture_value("b")
        d = os.environ["CLAUDE_CONFIG_DIR"]
        self.helper("echo '%s'" % a)
        local = self.script("echo '%s'" % b, "local-helper.sh")
        with open(os.path.join(d, "settings.local.json"), "w") as fh:
            json.dump({"apiKeyHelper": local}, fh)
        self.assertTrue(es.helper_command().endswith("helper.sh"), "the user settings.json alone")
        self.assertEqual(es.helper_fingerprint()[0], es.fingerprint(a))
        os.unlink(os.path.join(d, "settings.json"))
        self.assertEqual(es.helper_command(), "", "a local file alone is no helper")
        es.invalidate()
        fp, reason = es.helper_fingerprint()
        self.assertEqual(fp, "")
        self.assertEqual(reason, "no apiKeyHelper in %s" % os.path.join(d, "settings.json"))
        self.assertEqual(es.HELPER_SETTINGS_FILES, ("settings.json",))

    def test_an_invalidation_during_the_helper_run_makes_the_next_caller_run_again(self):
        # the result is stored under the generation the run STARTED in: an invalidate() while the
        # helper runs (a refresh, a switch, a refusal) leaves that result stale, and the next caller
        # runs the helper again. Before this it was stored under the generation at completion, so a
        # pre-invalidation fingerprint was served as current.
        v = fixture_value("helper")
        self.helper("sleep 0.4\necho '%s'" % v)
        seen = {}

        def read():
            seen["fp"] = es.helper_fingerprint()

        t = threading.Thread(target=read)
        t.start()
        time.sleep(0.15)                 # the helper is running
        es.invalidate("mid-run")
        t.join(10)
        self.assertEqual(seen["fp"], (es.fingerprint(v), ""), "the caller under way takes its own run's result")
        self.assertEqual(es.helper_runs(), 1)
        self.assertNotEqual(es._helper["gen"], es._gen, "stored under the generation the run started in: stale")
        self.assertEqual(es.helper_fingerprint(), (es.fingerprint(v), ""))
        self.assertEqual(es.helper_runs(), 2, "the next caller runs the helper again; invalidate never waited")

    def test_a_caller_that_took_the_set_hands_it_in_so_a_failing_command_is_not_run_twice(self):
        # a connect takes the set (one run: a failed run is re-run per caller) and then asks for the
        # helper's fingerprint; with the set handed in, the fingerprint's own read is not a second run
        h, role = fixture_value("helper"), fixture_value("role")
        self.helper('echo "%s-${A_TOKEN:-none}"' % h)
        self.configure(self.script("exit 3"))
        snap, vals = es.take(self.src)
        self.assertFalse(snap["ok"])
        self.assertEqual((vals, es._runs), ({}, 1))
        fp, reason = es.helper_fingerprint(values=vals)
        self.assertEqual((fp, reason), (es.fingerprint(h + "-none"), ""))
        self.assertEqual(es._runs, 1, "the set handed in is used; the command did not run again")
        self.assertEqual(es.helper_runs(), 1)
        es.invalidate()
        es.helper_fingerprint(source=self.src)
        self.assertEqual(es._runs, 2, "with no set handed in the fingerprint reads, and on a failing command runs, itself")
        es.invalidate()
        fp, _reason = es.helper_fingerprint(values={"A_TOKEN": role, "ANTHROPIC_API_KEY": fixture_value("key")})
        self.assertEqual(fp, es.fingerprint("%s-%s" % (h, role)), "the helper's environment is built from the set handed in, minus the key")
        self.assertEqual(es._runs, 2)

    def test_an_invalidation_between_take_and_the_fingerprint_stores_the_entry_under_the_sets_generation(self):
        # a connect takes the set, an invalidate lands (a refresh, a refusal), and the connect asks
        # for the helper's fingerprint with the set it took: the run is FOR that set's generation
        # and is stored under it, stale. Before this the generation was read under the helper lock
        # after the overlay was built, so the pre-invalidation overlay's fingerprint was stored under
        # the post-invalidation generation and served as current to every caller after.
        h, role_a, role_b = fixture_value("helper"), fixture_value("role-a"), fixture_value("role-b")
        self.helper('echo "%s-${A_TOKEN:-none}"' % h)
        self.configure(self.printing({"A_TOKEN": role_a}))
        snap, vals = es.take(self.src)
        self.assertEqual(snap["generation"], es._gen, "the record names the generation it was served under")
        self.printing({"A_TOKEN": role_b})
        es.invalidate("a refresh between the connect's take and its helper fingerprint")
        fp, reason = es.helper_fingerprint(values=vals, generation=snap["generation"])
        self.assertEqual((fp, reason), (es.fingerprint("%s-%s" % (h, role_a)), ""),
                         "the connect's own set: the fingerprint of the credential its CLI bills")
        self.assertEqual(es.helper_runs(), 1)
        self.assertNotEqual(es._helper["gen"], es._gen, "stored under the generation the set was taken in: stale")
        fp2, reason2 = es.helper_fingerprint(source=self.src)
        self.assertEqual(es.helper_runs(), 2, "the next caller runs the helper again, on the current set")
        self.assertEqual((fp2, reason2), (es.fingerprint("%s-%s" % (h, role_b)), ""))
        self.assertEqual(es._helper["gen"], es._gen)
        self.assertEqual(es.helper_fingerprint(source=self.src)[0], fp2)
        self.assertEqual(es.helper_runs(), 2, "and that one is current: cached")
        # values handed in with no generation: the run is for the current generation (the caller did not say)
        es.invalidate("again")
        es.helper_fingerprint(values={"A_TOKEN": role_b})
        self.assertEqual(es._helper["gen"], es._gen)
        self.assertEqual(es.helper_runs(), 3)

    def test_a_late_connect_carrying_an_older_generation_does_not_overwrite_the_current_entry(self):
        # connect X takes the set at generation G; a refresh lands and connect Y takes the set at G+1
        # and stores the helper's fingerprint under it; X, late, asks for the helper's fingerprint
        # with the generation and set it took. X's run is for its own set and X gets that fingerprint
        # (the credential its CLI bills), but the slot keeps Y's entry. Before this X's run overwrote
        # the slot with an entry for G, and until the next reader healed it a refusal on a session
        # stamped with Y's fingerprint was not a refusal of the helper's output as far as
        # invalidate_for_auth_failure could see, so it invalidated nothing.
        h, role_x, role_y = fixture_value("helper"), fixture_value("role-x"), fixture_value("role-y")
        self.helper('echo "%s-${A_TOKEN:-none}"' % h)
        self.configure(self.printing({"A_TOKEN": role_x}))
        snap_x, vals_x = es.take(self.src)
        self.printing({"A_TOKEN": role_y})
        es.invalidate("a refresh between X's take and its helper fingerprint")
        snap_y, vals_y = es.take(self.src)
        self.assertEqual(snap_y["generation"], snap_x["generation"] + 1)
        fp_y, _reason = es.helper_fingerprint(values=vals_y, generation=snap_y["generation"], set_seq=snap_y["setSeq"])
        self.assertEqual(fp_y, es.fingerprint("%s-%s" % (h, role_y)))
        self.assertEqual((es._helper["gen"], es._helper["fp"]), (snap_y["generation"], fp_y))
        fp_x, reason_x = es.helper_fingerprint(values=vals_x, generation=snap_x["generation"], set_seq=snap_x["setSeq"])
        self.assertEqual((fp_x, reason_x), (es.fingerprint("%s-%s" % (h, role_x)), ""),
                         "X gets the fingerprint of its own run: the credential its CLI bills")
        self.assertEqual(es.helper_runs(), 2)
        self.assertEqual((es._helper["gen"], es._helper["fp"]), (snap_y["generation"], fp_y),
                         "the slot keeps the current entry; X's older one is not written over it")
        self.assertTrue(es.invalidate_for_auth_failure("401", fp_y), "a refusal on the current helper output fires")
        self.assertFalse(es.invalidate_for_auth_failure("401", fp_y), "once")
        self.assertEqual(es.helper_fingerprint(source=self.src), (fp_y, ""), "the next read runs the helper on the current set")
        self.assertEqual(es.helper_runs(), 3)

    def test_a_recovery_that_hands_back_another_set_under_one_generation_is_a_fresh_fingerprint(self):
        # the store is unreachable for one run and back at the next, handing back a rotated role
        # variable: the retry after a failed run moves no generation, so an entry keyed on the
        # generation alone served the OLD overlay's fingerprint for the new set, and a connect on the
        # new set was stamped with it (cycle_key then read that session as current). The set's
        # identity (setSeq) rides beside the generation now.
        h, role_a, role_b = fixture_value("helper"), fixture_value("role-a"), fixture_value("role-b")
        self.helper('echo "%s-${A_TOKEN:-none}"' % h)
        self.configure(self.printing({"A_TOKEN": role_a}))
        snap_a, vals_a = es.take(self.src)
        fp_a = es.helper_fingerprint(values=vals_a, generation=snap_a["generation"], set_seq=snap_a["setSeq"])[0]
        self.assertEqual(fp_a, es.fingerprint("%s-%s" % (h, role_a)))
        self.script("exit 2")
        es.invalidate("a refresh while the store is unreachable")
        snap_f, vals_f = es.take(self.src)
        self.assertEqual((snap_f["ok"], snap_f["stale"]), (False, True))
        self.assertEqual(snap_f["setSeq"], snap_a["setSeq"], "a failed run keeps the set: its identity holds")
        fp_f = es.helper_fingerprint(values=vals_f, generation=snap_f["generation"], set_seq=snap_f["setSeq"])[0]
        self.assertEqual((fp_f, es.helper_runs()), (fp_a, 2), "the generation moved: a run, on the same overlay")
        self.printing({"A_TOKEN": role_b})                    # the store is back, with a rotated role variable
        snap_b, vals_b = es.take(self.src)
        self.assertTrue(snap_b["ok"])
        self.assertEqual(snap_b["generation"], snap_f["generation"], "the retry after a failure moves no generation")
        self.assertEqual(snap_b["setSeq"], snap_f["setSeq"] + 1, "but the set changed: its identity moved")
        fp_b, reason_b = es.helper_fingerprint(values=vals_b, generation=snap_b["generation"], set_seq=snap_b["setSeq"])
        self.assertEqual((fp_b, reason_b), (es.fingerprint("%s-%s" % (h, role_b)), ""),
                         "the new set's own fingerprint, not the previous set's cached one")
        self.assertEqual(es.helper_runs(), 3)
        self.assertEqual(es.helper_fingerprint(source=self.src), (fp_b, ""), "the current read agrees")
        self.assertEqual(es.helper_runs(), 3, "an unchanged set keeps the entry")
        self.assertEqual(es.helper_fingerprint(values=vals_b, generation=snap_b["generation"]), (fp_b, ""),
                         "values and a generation with no set identity: the current one, as with the generation")
        self.assertEqual((es.helper_runs(), es._runs), (3, 3))

    def test_a_selector_hand_edit_that_changes_the_set_is_a_fresh_fingerprint_and_one_that_does_not_keeps_it(self):
        # the selector file may be one the operator edits by hand: the edit re-runs the command with
        # no invalidate(), so the set can change under one generation
        h = fixture_value("helper")
        self.helper('echo "%s-${SEL:-none}"' % h)
        self.configure(self.script('echo "SEL=${1:-none}"') + ' "$1"', names="hp,lp")
        self.select("hp")
        snap_hp, vals_hp = es.take(self.src)
        self.assertEqual(snap_hp["selector"], "hp")
        fp_hp = es.helper_fingerprint(values=vals_hp, generation=snap_hp["generation"], set_seq=snap_hp["setSeq"])[0]
        self.assertEqual(fp_hp, es.fingerprint(h + "-hp"))
        self.edit_selector("lp")
        snap_lp, vals_lp = es.take(self.src)
        self.assertEqual((snap_lp["selector"], es._runs), ("lp", 2), "the edit re-ran the command")
        self.assertEqual(snap_lp["generation"], snap_hp["generation"], "with no invalidation")
        self.assertEqual(snap_lp["setSeq"], snap_hp["setSeq"] + 1, "and another set came back")
        fp_lp, reason_lp = es.helper_fingerprint(values=vals_lp, generation=snap_lp["generation"], set_seq=snap_lp["setSeq"])
        self.assertEqual((fp_lp, reason_lp, es.helper_runs()), (es.fingerprint(h + "-lp"), "", 2),
                         "the new set's own fingerprint")
        self.assertEqual(es.helper_fingerprint(source=self.src), (fp_lp, ""))
        self.assertEqual(es.helper_runs(), 2, "the current read is served the entry")
        # an edit the command answers with the same set: the file rewritten with the same token. The
        # selector's identity is part of the set's identity (a helper may read the selector file itself;
        # the test below), so the identity moves ONCE for the edit, and the helper runs again, printing
        # the same thing here.
        self.edit_selector("lp", bump_s=2)
        snap_same, vals_same = es.take(self.src)
        self.assertEqual(es._runs, 3, "the stat identity moved: a run")
        self.assertEqual((snap_same["generation"], snap_same["setSeq"]), (snap_lp["generation"], snap_lp["setSeq"] + 1),
                         "the same set came back under an edited selector: the identity moved once, not twice")
        self.assertEqual(es.helper_fingerprint(values=vals_same, generation=snap_same["generation"],
                                               set_seq=snap_same["setSeq"]), (fp_lp, ""))
        self.assertEqual(es.helper_runs(), 3, "the helper ran again for the edited selector: the same fingerprint")

    def test_a_selector_edit_the_command_ignores_still_re_fingerprints_a_helper_that_reads_the_file(self):
        # the command does not read $1 (one set whatever the selector says) while the apiKeyHelper reads
        # the selector file itself, the shape the selector exists for (one switch moves the injected key
        # and the helper-billed sessions). The edit re-runs the command and the set is unchanged, so the
        # helper's entry, keyed on (generation, setSeq), kept being served for the new selector and stamped
        # on new connects until an invalidate() (review find, 2026-09-07). The selector's identity now
        # moves setSeq too.
        sel = os.environ["ROMP_CREDENTIAL_SELECTOR_FILE"]
        self.helper("cat '%s'" % sel)
        self.configure(self.printing({"A_TOKEN": fixture_value()}), names="hp,lp")
        self.select("hp")
        snap_hp, vals_hp = es.take(self.src)
        fp_hp = es.helper_fingerprint(values=vals_hp, generation=snap_hp["generation"], set_seq=snap_hp["setSeq"])[0]
        self.assertEqual(fp_hp, es.fingerprint("hp"))
        self.edit_selector("lp")
        snap_lp, vals_lp = es.take(self.src)
        self.assertEqual((snap_lp["selector"], vals_lp, es._runs), ("lp", vals_hp, 2),
                         "the edit re-ran the command, which handed back the same set")
        self.assertEqual(snap_lp["generation"], snap_hp["generation"], "with no invalidate()")
        self.assertEqual(snap_lp["setSeq"], snap_hp["setSeq"] + 1, "the selector's identity moved the set's")
        fp_lp, reason = es.helper_fingerprint(values=vals_lp, generation=snap_lp["generation"], set_seq=snap_lp["setSeq"])
        self.assertEqual((fp_lp, reason), (es.fingerprint("lp"), ""), "the helper's fingerprint follows the edit")
        self.assertEqual(es.helper_fingerprint(source=self.src), (fp_lp, ""), "the current read agrees")
        self.assertEqual(es.helper_runs(), 2)
        self.assertEqual(es.take(self.src)[0]["setSeq"], snap_lp["setSeq"], "an unchanged selector moves nothing")

    def test_a_late_connect_on_the_set_from_before_a_selector_edit_does_not_overwrite_the_entry_either(self):
        # the same ordering within one generation: X took the set before a hand edit, Y after; Y
        # stores its entry first; X's run, for the older set, is handed back to X and not written
        # over Y's. The set's identity orders the two where the generation alone could not.
        h = fixture_value("helper")
        self.helper('echo "%s-${SEL:-none}"' % h)
        self.configure(self.script('echo "SEL=${1:-none}"') + ' "$1"', names="hp,lp")
        self.select("hp")
        snap_x, vals_x = es.take(self.src)
        self.edit_selector("lp")
        snap_y, vals_y = es.take(self.src)
        self.assertEqual(snap_y["generation"], snap_x["generation"])
        self.assertGreater(snap_y["setSeq"], snap_x["setSeq"])
        fp_y = es.helper_fingerprint(values=vals_y, generation=snap_y["generation"], set_seq=snap_y["setSeq"])[0]
        fp_x = es.helper_fingerprint(values=vals_x, generation=snap_x["generation"], set_seq=snap_x["setSeq"])[0]
        self.assertEqual((fp_x, fp_y), (es.fingerprint(h + "-hp"), es.fingerprint(h + "-lp")))
        self.assertEqual((es._helper["seq"], es._helper["fp"]), (snap_y["setSeq"], fp_y), "the slot keeps Y's entry")
        self.assertTrue(es.invalidate_for_auth_failure("401", fp_y), "a refusal on the current helper output fires")

    def test_the_helper_runs_in_a_session_clis_environment_role_variables_merged_romp_sid_absent(self):
        # a helper that picks its store by a role variable, and one that would see a session identity
        # if the kernel had been started from inside a session's tool shell
        role = fixture_value("role")
        self.configure(self.printing({"A_TOKEN": role, "ANTHROPIC_API_KEY": fixture_value("key")}))
        self.helper('echo "${A_TOKEN}-${ROMP_SID:-nosid}-${ANTHROPIC_API_KEY:-nokey}"')
        os.environ["ROMP_SID"] = "11111111-2222-3333-4444-555555555555"
        try:
            fp, reason = es.helper_fingerprint(source=self.src)
        finally:
            os.environ.pop("ROMP_SID", None)
        self.assertEqual(reason, "")
        self.assertEqual(fp, es.fingerprint("%s-nosid-nokey" % role),
                         "the role variables reach the helper, ROMP_SID and the set's own key do not")

    def test_the_config_dir_argument_and_the_environment_variable_name_the_same_file(self):
        v = fixture_value()
        other = os.path.join(self.d, "other-config")
        self.helper("echo '%s'" % v, config_dir=other)
        self.assertEqual(es.helper_command(), "", "the environment's dir has no settings.json")
        self.assertEqual(es.helper_command(other), es.helper_command(config_dir=other))
        self.assertTrue(es.helper_command(other).endswith("helper.sh"))
        os.environ["CLAUDE_CONFIG_DIR"] = other
        self.assertEqual(es.helper_fingerprint()[0], es.fingerprint(v))


class NothingLeaks(_Lab):
    def test_no_value_reaches_any_status_field_or_reason(self):
        values = {"ANTHROPIC_API_KEY": fixture_value("key"), "ANTHROPIC_LP_API_KEY": fixture_value("lp"),
                  "A_TOKEN": fixture_value("role")}
        loud = "\n".join("echo '%s' >&2" % v for v in values.values())
        scenarios = (
            self.printing(values, extra=loud),                                   # success, values on stderr too
            self.script(loud + "\n" + "\n".join("echo '%s'" % v for v in values.values()) + "\nexit 1"),  # failure
            self.script("\n".join("echo '%s'" % v for v in values.values())),   # bare values: no NAME=
        )
        for s in scenarios:
            es._reset()
            self.configure(s)
            blob = json.dumps(es.status(self.src)) + json.dumps(es.current(self.src)) + repr(es._snap)
            for v in values.values():
                self.assertNotIn(v, blob, s)
            self.assertNotIn("fixture", blob, s)
        # and the helper's
        v = fixture_value("helper")
        self.helper("echo '%s' >&2\necho '%s'" % (v, v))
        fp, reason = es.helper_fingerprint(source=self.src)
        self.assertEqual(fp, es.fingerprint(v))
        self.assertNotIn(v, reason + repr(es._helper))

    def test_the_values_live_in_one_private_dict_and_never_in_the_environment(self):
        v = fixture_value()
        environ_before = dict(os.environ)
        self.configure(self.printing({"A_TOKEN": v, "ANTHROPIC_API_KEY": fixture_value("key")}))
        es.injection(self.src)
        es.current(self.src)
        es.take(self.src)
        es.status(self.src)
        es.resolve_key(self.src)
        self.assertEqual(dict(os.environ), environ_before, "no reader writes the environment")
        self.assertFalse("A_TOKEN" in os.environ, "A_TOKEN present")
        self.assertFalse(v in os.environ.values())
        self.assertEqual(sorted(es._values), ["ANTHROPIC_API_KEY", "A_TOKEN"])
        got = es.injection(self.src)
        got["A_TOKEN"] = "changed by a caller"
        self.assertEqual(es.injection(self.src)["A_TOKEN"], v, "callers get a copy")


class Floor(unittest.TestCase):
    """conftest's import-time and per-test floor: no test starts with a credential command configured, and
    none reads the selector file under the real HOME. ROMP_CREDENTIAL_SELECTOR_FILE is floored to a path
    that does not exist (popped before, which meant the default under HOME). The import-time half holds
    only if no module undoes it during collection: this module's own import leaves the floor in place, and
    conftest refuses a collection that ends without the floor, naming the fix: a UsageError serially, and
    under xdist a failure per item, or the controller's Interrupted when nothing was selected."""

    REAL_DEFAULT = os.path.realpath(os.path.join(os.path.expanduser("~"), ".config", "romp", "credential-selector"))

    def test_this_modules_import_left_the_selector_floored(self):
        self.assertTrue(_SELECTOR_AT_IMPORT, "this module's import left %s absent" % es.SELECTOR_FILE_VAR)
        self.assertFalse(os.path.exists(_SELECTOR_AT_IMPORT), "the floor this module left points at a file that exists")
        self.assertNotEqual(os.path.realpath(_SELECTOR_AT_IMPORT), self.REAL_DEFAULT)

    REFUSAL = "ROMP_CREDENTIAL_SELECTOR_FILE is absent after collection"
    THE_FIX = "path that does not exist"

    def scratch_suite(self):
        """A copy of conftest beside three modules: one whose top level pops the variable (collection runs
        it), one that floors it to a path that does not exist as this module does, and a plain one with two
        tests, so a run has items to spread over xdist workers."""
        d = tempfile.mkdtemp()
        shutil.copy(os.path.join(HERE, "conftest.py"), os.path.join(d, "conftest.py"))
        with open(os.path.join(d, "test_popper.py"), "w") as fh:
            fh.write("import os\nos.environ.pop('ROMP_CREDENTIAL_SELECTOR_FILE', None)\n\n\n"
                     "def test_nothing():\n    pass\n")
        with open(os.path.join(d, "test_floorer.py"), "w") as fh:
            fh.write("import os\nos.environ['ROMP_CREDENTIAL_SELECTOR_FILE'] = os.path.join(%r, 'no-such-selector')\n\n\n"
                     "def test_nothing():\n    pass\n" % d)
        with open(os.path.join(d, "test_plain.py"), "w") as fh:
            fh.write("def test_a():\n    pass\n\n\ndef test_b():\n    pass\n")
        return d

    @staticmethod
    def run_pytest(d, *args):
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--rootdir", d] + list(args),
                           cwd=d, capture_output=True, text=True, timeout=180)
        return r.returncode, r.stdout + r.stderr

    def test_a_module_that_pops_the_selector_variable_at_import_fails_collection_loudly(self):
        # conftest's pytest_collection_finish, in a subprocess against a copy of conftest: a module whose top
        # level pops the variable (collection runs it) is refused with the fix named, under --collect-only,
        # in a serial run, and in a serial run whose -k deselects everything (nothing runs, and the refusal
        # is still the one line said); one that floors it to a path that does not exist, as this module
        # does, collects and runs.
        d = self.scratch_suite()
        try:
            rc, out = self.run_pytest(d, "--collect-only", "test_popper.py")
            self.assertNotEqual(rc, 0, out[-800:])
            self.assertIn(self.REFUSAL, out, out[-800:])
            self.assertIn(self.THE_FIX, out, "the refusal names the fix")
            rc, out = self.run_pytest(d, "--collect-only", "test_floorer.py")
            self.assertEqual(rc, 0, out[-800:])
            self.assertIn("1 test collected", out, out[-800:])
            for args in (("test_popper.py", "test_plain.py"), ("test_popper.py", "test_plain.py", "-k", "zzz_nothing")):
                rc, out = self.run_pytest(d, *args)
                self.assertEqual(rc, 4, (args, out[-800:]))                       # pytest's usage-error exit
                self.assertEqual(out.count(self.REFUSAL), 1, (args, out[-800:]))
                self.assertIn(self.THE_FIX, out, args)
                self.assertNotIn("passed", out, (args, "nothing ran"))
            rc, out = self.run_pytest(d, "test_floorer.py", "test_plain.py")
            self.assertEqual(rc, 0, out[-800:])
            self.assertIn("3 passed", out, out[-800:])
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_under_xdist_every_item_fails_with_the_refusal_and_the_controller_reports_it(self):
        # the same popper under `pytest -n 2`: the controller does not collect, so the hook runs in the
        # workers, where a UsageError died with the worker and the controller printed forty lines of
        # INTERNALERROR naming neither the variable nor the fix. Now the worker holds the refusal and every
        # item fails at setup with it, so the controller's report carries the message once per item and no
        # internal error; the floorer runs clean under the same runner.
        if importlib.util.find_spec("xdist") is None:
            self.skipTest("pytest-xdist is not installed")
        d = self.scratch_suite()
        try:
            rc, out = self.run_pytest(d, "-n", "2", "test_popper.py", "test_plain.py")
            self.assertEqual(rc, 1, out[-1200:])
            self.assertNotIn("INTERNALERROR", out, out[-1200:])
            self.assertGreaterEqual(out.count(self.REFUSAL), 3, ("one per item", out[-1200:]))
            self.assertIn(self.THE_FIX, out)
            self.assertNotIn("passed", out, "nothing ran")
            rc, out = self.run_pytest(d, "-n", "2", "test_floorer.py", "test_plain.py")
            self.assertEqual(rc, 0, out[-800:])
            self.assertIn("3 passed", out, out[-800:])
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_under_xdist_with_nothing_selected_the_controller_stops_with_the_refusal(self):
        # the popper under `pytest -n 2 -k <nothing>`: no item is selected, so no setup carries the held
        # refusal, and the run ended `no tests ran` (exit status 5) with the refusal said nowhere. Now a worker
        # whose session.items is empty sets session.shouldfail with it, which xdist carries to the controller
        # at the worker's finish, and the controller ends the run as Interrupted with the message, once,
        # exit status 2; the floorer under the same -k is a plain empty run
        if importlib.util.find_spec("xdist") is None:
            self.skipTest("pytest-xdist is not installed")
        d = self.scratch_suite()
        try:
            rc, out = self.run_pytest(d, "-n", "2", "test_popper.py", "test_plain.py", "-k", "zzz_nothing")
            self.assertEqual(rc, 2, out[-1200:])                                  # pytest's interrupted exit
            self.assertNotIn("INTERNALERROR", out, out[-1200:])
            self.assertEqual(out.count(self.REFUSAL), 1, out[-1200:])
            self.assertIn("Interrupted: " + self.REFUSAL, out, out[-1200:])
            self.assertIn(self.THE_FIX, out)
            self.assertIn("no tests ran", out, "nothing ran")
            self.assertNotIn("passed", out)
            rc, out = self.run_pytest(d, "-n", "2", "test_floorer.py", "test_plain.py", "-k", "zzz_nothing")
            self.assertEqual(rc, 5, out[-800:])                                   # no tests collected, no refusal
            self.assertNotIn(self.REFUSAL, out, out[-800:])
            self.assertNotIn("Interrupted", out, out[-800:])
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_the_command_names_and_timeout_are_absent_at_test_start(self):
        for v in (es.COMMAND_VAR, es.NAMES_VAR, es.TIMEOUT_VAR):
            self.assertFalse(v in os.environ, v)
        self.assertEqual(es.COMMAND_VAR, ks.CMD_VAR)
        self.assertFalse(es.current()["configured"], "no source handed in: no command source")

    def test_the_selector_file_is_floored_to_a_path_that_does_not_exist(self):
        p = os.environ.get(es.SELECTOR_FILE_VAR) or ""
        self.assertTrue(p, "%s is not floored" % es.SELECTOR_FILE_VAR)
        self.assertFalse(os.path.exists(p), "the floor points at a file that exists")
        self.assertEqual(es.selector_path(), p)
        self.assertNotEqual(os.path.realpath(p), self.REAL_DEFAULT, "the floor is this machine's default selector file")
        self.assertEqual(es.read_selector(), ("", ""), "no file: no selector and no error, an empty `$1`")
        self.assertEqual(es._selector_ident()[1], "absent")

    def test_a_decoy_selector_at_the_default_location_under_a_private_home_is_not_read(self):
        # a command-source test that builds its fake command and forgets the selector variable: the
        # floor, not the default under HOME, is what the run reads, proven against a decoy at that default
        d = tempfile.mkdtemp()
        before = {v: os.environ.get(v) for v in ("HOME", "XDG_CONFIG_HOME", es.NAMES_VAR)}
        try:
            os.environ["HOME"] = d
            os.environ.pop("XDG_CONFIG_HOME", None)
            decoy = os.path.join(d, ".config", "romp", "credential-selector")
            os.makedirs(os.path.dirname(decoy))
            with open(decoy, "w") as fh:
                fh.write("hp\n")
            self.assertEqual(os.path.join(os.path.expanduser("~"), ".config", "romp", "credential-selector"), decoy,
                             "the decoy is at the default location for this process")
            self.assertEqual(es.selector_path(), os.environ[es.SELECTOR_FILE_VAR], "the floor names the file, not the default")
            self.assertEqual(es.read_selector(), ("", ""))
            script = os.path.join(d, "cmd.sh")
            with open(script, "w") as fh:
                fh.write("#!/bin/sh\necho 'A_TOKEN=%s'\n" % fixture_value())
            os.chmod(script, 0o700)
            os.environ[es.NAMES_VAR] = "hp"
            es._reset()
            snap = es.current(ks.KeySource("command", script + ' "$1"'))
            self.assertTrue(snap["ok"])
            self.assertEqual((snap["selector"], snap["selectorNote"]), ("", ""), "the decoy's token was not read as `$1`")
        finally:
            for v, was in before.items():
                if was is None:
                    os.environ.pop(v, None)
                else:
                    os.environ[v] = was
            es._reset()


if __name__ == "__main__":
    unittest.main()
