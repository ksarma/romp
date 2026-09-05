#!/usr/bin/env python3
"""tests/conftest.py's failure-report redaction (2026-09-05): no failed test may print a value from
the process environment.

The assertion rule the suite follows — never render an environment mapping, never compare a
credential's value in a message — is what keeps a live key off a terminal; this hook is the safety
net for the assertion nobody wrote that way. Pinned here:
  RedactionRule — the value set (16 characters or more; path-valued shell names exempt unless the
    name is credential-shaped) and the replacement (every occurrence, longest value first).
  HookEndToEnd — a subprocess pytest run against a copy of the conftest: a test that fails with
    the probe value in its assertion message and on its stdout prints the marker, never the value.

The probe value is synthetic ("romp-test-fixture-" + a uuid), assembled at run time.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import uuid

HERE = os.path.dirname(os.path.realpath(__file__))
CONFTEST = os.path.join(HERE, "conftest.py")


def _conftest():
    """The loaded conftest module, whatever name pytest gave it; None under a bare unittest run."""
    for m in list(sys.modules.values()):
        f = getattr(m, "__file__", None)
        if f and os.path.realpath(f) == CONFTEST:
            return m
    return None


def probe_value(tag=""):
    return "romp-test-fixture-%s%s" % (tag + "-" if tag else "", uuid.uuid4().hex)


class RedactionRule(unittest.TestCase):
    def setUp(self):
        self.cf = _conftest()
        if self.cf is None:
            self.skipTest("the redaction hook lives in the pytest conftest")

    def test_values_of_sixteen_or_more_characters_are_collected(self):
        long_v, short_v = probe_value("long"), "short-value"
        env = {"SOME_TOKEN": long_v, "PLAIN": short_v, "OTHER": "x" * 16, "EMPTY": ""}
        got = self.cf.env_values_to_redact(env)
        self.assertTrue(long_v in got, "a long value is collected")
        self.assertTrue("x" * 16 in got, "sixteen characters is the floor")
        self.assertFalse(short_v in got, "a value under the floor is not")
        self.assertFalse("" in got)
        self.assertEqual(self.cf.ENV_VALUE_MIN_LEN, 16)

    def test_path_valued_shell_names_are_exempt_unless_credential_shaped(self):
        p = "/some/where/deep/enough/to/count"
        env = {"PWD": p, "HOME": p, "XDG_STATE_HOME": p, "PATH": p, "CLAUDE_CONFIG_DIR": p}
        self.assertEqual(self.cf.env_values_to_redact(env), set(), "a traceback quotes these paths")
        env = {"PWD_TOKEN": p, "ANTHROPIC_PWD": p, "MY_SECRET_PATH": p}
        self.assertEqual(self.cf.env_values_to_redact(env), {p}, "a credential-shaped name is never exempt")

    def test_the_replacement_covers_every_occurrence_longest_first(self):
        a = probe_value("a")
        b = a + "-suffix"                       # contains a: replaced whole, not as a + "-suffix"
        text = "first %s then %s and %s again; short ok" % (a, b, a)
        red = self.cf.redact_env_values(text, {a, b})
        self.assertFalse(a in red, "the value is gone from the text")
        self.assertEqual(red.count(self.cf.ENV_VALUE_REDACTED), 3)
        self.assertEqual(red, "first %s then %s and %s again; short ok" % ((self.cf.ENV_VALUE_REDACTED,) * 3))
        self.assertEqual(self.cf.redact_env_values("nothing here", {a, ""}), "nothing here")

    def test_the_process_environment_is_what_the_hook_reads_by_default(self):
        v = probe_value("live")
        os.environ["ROMP_TEST_REDACTION_PROBE"] = v
        try:
            self.assertTrue(v in self.cf.env_values_to_redact(), "the default is os.environ")
        finally:
            os.environ.pop("ROMP_TEST_REDACTION_PROBE", None)


class HookEndToEnd(unittest.TestCase):
    def test_a_failing_test_that_renders_an_environment_value_prints_the_marker(self):
        d = tempfile.mkdtemp()
        try:
            shutil.copy(CONFTEST, os.path.join(d, "conftest.py"))
            with open(os.path.join(d, "test_probe_leak.py"), "w") as fh:
                fh.write("import os\n\n"
                         "def test_leak():\n"
                         "    v = os.environ['ROMP_TEST_REDACTION_PROBE']\n"
                         "    print('stdout carries ' + v)\n"
                         "    assert v == 'something else', 'the message carries ' + v\n")
            v = probe_value("probe")
            env = dict(os.environ, ROMP_TEST_REDACTION_PROBE=v)
            r = subprocess.run([sys.executable, "-m", "pytest", "test_probe_leak.py", "-q", "-p", "no:cacheprovider",
                                "--rootdir", d], cwd=d, env=env, capture_output=True, text=True, timeout=120)
            out = r.stdout + r.stderr
            self.assertNotEqual(r.returncode, 0, "the probe test fails by design")
            self.assertTrue("1 failed" in out, "the run reports the failure")
            self.assertFalse(v in out, "the probe value reached no line of the report")
            self.assertGreaterEqual(out.count("[REDACTED-ENV-VALUE]"), 2, "the message and the captured stdout both show the marker")
        finally:
            shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
