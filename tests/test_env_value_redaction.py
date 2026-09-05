#!/usr/bin/env python3
"""tests/conftest.py's report redaction (2026-09-05): no test report may print a value from the
process environment, or a credential-shaped token from anywhere.

The assertion rule the suite follows (never render an environment mapping, never compare a
credential's value in a message) is what keeps a live key off a terminal; the hook is the safety net
for the assertion nobody wrote that way. Pinned here:
  RedactionRule: the value set (16 characters or more; path-valued shell names exempt unless the
    name is credential-shaped) and the replacement (every occurrence, longest value first, and each
    whitespace-separated chunk of a value that is 16 characters or more, because pprint renders a
    value with spaces as adjacent literals on separate lines and a whole-value replace misses them).
  WriteTimeCapture: a value is noted the moment it is written into os.environ (a plain assignment,
    update, setdefault, os.putenv, os.environb, mock.patch.dict), so a value present only between the
    per-test samples is redacted too.
  CredentialPattern: the second net, independent of provenance: credential-shaped tokens by pattern
    (tests/credential_patterns.py) in any report.
  ReportShapes: the hook's work on a report object of each outcome (a failure's longrepr, a skip's
    tuple, a passed test's sections).
  HookEndToEnd: subprocess pytest runs against a copy of the conftest. A test that fails with a probe
    value in its message and on its stdout prints the marker, never the value; the same for a value
    set inside mock.patch.dict and gone before the assertion, a header-shaped value split by
    assertDictEqual, a pattern-shaped token with no provenance, a passed test's captured output
    under -rA, and a collection error.

Every probe value is synthetic and assembled at run time ("romp-test-fixture-" + a uuid; a
pattern-shaped probe is a public key prefix joined to uuids), so no literal in this file is a
credential.
"""
import json
import os
import pprint
import shutil
import subprocess
import sys
import tempfile
import unittest
import uuid
from types import SimpleNamespace
from unittest import mock

HERE = os.path.dirname(os.path.realpath(__file__))
CONFTEST = os.path.join(HERE, "conftest.py")
PATTERNS = os.path.join(HERE, "credential_patterns.py")


def _conftest():
    """The loaded conftest module, whatever name pytest gave it; None under a bare unittest run."""
    for m in list(sys.modules.values()):
        f = getattr(m, "__file__", None)
        if f and os.path.realpath(f) == CONFTEST:
            return m
    return None


def probe_value(tag=""):
    return "romp-test-fixture-%s%s" % (tag + "-" if tag else "", uuid.uuid4().hex)


def patterned_probe(prefix="sk-ant-api03-"):
    """A token of a public key format, assembled at run time: a prefix and two uuids of tail."""
    return prefix + uuid.uuid4().hex + uuid.uuid4().hex


def _copy_hook(d):
    """The conftest and the pattern module it loads by path, as a subprocess pytest run sees them."""
    shutil.copy(CONFTEST, os.path.join(d, "conftest.py"))
    shutil.copy(PATTERNS, os.path.join(d, "credential_patterns.py"))


class _WithConftest(unittest.TestCase):
    def setUp(self):
        self.cf = _conftest()
        if self.cf is None:
            self.skipTest("the redaction hook lives in the pytest conftest")


class RedactionRule(_WithConftest):
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
        env = {"PWD": p, "HOME": p, "XDG_STATE_HOME": p, "PATH": p, "CLAUDE_CONFIG_DIR": p,
               "ROMP_TESTS_REAL_CLAUDE_CONFIG_DIR": p, "ROMP_CREDENTIAL_SELECTOR_FILE": p}
        self.assertEqual(self.cf.env_values_to_redact(env), set(), "a traceback quotes these paths")
        env = {"PWD_TOKEN": p, "ANTHROPIC_PWD": p, "MY_SECRET_PATH": p}
        self.assertEqual(self.cf.env_values_to_redact(env), {p}, "a credential-shaped name is never exempt")
        self.assertTrue(self.cf.env_value_qualifies("SOME_TOKEN", p))
        self.assertFalse(self.cf.env_value_qualifies("ROMP_TESTS_REAL_CLAUDE_CONFIG_DIR", p),
                         "the pre-floor settings dir is a path the live test's skip reason quotes")

    def test_the_replacement_covers_every_occurrence_longest_first(self):
        a = probe_value("a")
        b = a + "-suffix"                       # contains a: replaced whole, not as a + "-suffix"
        text = "first %s then %s and %s again; short ok" % (a, b, a)
        red = self.cf.redact_env_values(text, {a, b})
        self.assertFalse(a in red, "the value is gone from the text")
        self.assertEqual(red.count(self.cf.ENV_VALUE_REDACTED), 3)
        self.assertEqual(red, "first %s then %s and %s again; short ok" % ((self.cf.ENV_VALUE_REDACTED,) * 3))
        self.assertEqual(self.cf.redact_env_values("nothing here", {a, ""}), "nothing here")

    def test_a_value_with_whitespace_is_also_redacted_chunk_by_chunk(self):
        # pprint (assertDictEqual, assertEqual on long containers) renders a value with spaces as
        # adjacent string literals on separate lines, so the whole value is never contiguous in the
        # report and a whole-value replace leaves the token half standing
        tok = probe_value("bearer")
        v = "Authorization: Bearer " + tok
        text = pprint.pformat({"h": v}, width=40)
        self.assertFalse(v in text, "pprint split the value across lines (the case this covers)")
        self.assertTrue(tok in text)
        red = self.cf.redact_env_values(text, {v})
        self.assertFalse(tok in red, "the token chunk is gone")
        self.assertTrue(self.cf.ENV_VALUE_REDACTED in red)
        self.assertTrue("Authorization:" in red, "a chunk under the floor is no secret and stays")
        self.assertTrue("Bearer" in red)
        # the same value contiguous is still replaced whole, once
        self.assertEqual(self.cf.redact_env_values("h=" + v + ";", {v}), "h=" + self.cf.ENV_VALUE_REDACTED + ";")
        # a value without whitespace gains no chunks; a short chunk of a long value is not a value
        self.assertEqual(self.cf.redact_env_values("keep ab cd", {"ab cd " + tok}), "keep ab cd")

    def test_the_process_environment_is_what_the_hook_reads_by_default(self):
        v = probe_value("live")
        os.environ["ROMP_TEST_REDACTION_PROBE"] = v
        try:
            self.assertTrue(v in self.cf.env_values_to_redact(), "the default is os.environ")
        finally:
            os.environ.pop("ROMP_TEST_REDACTION_PROBE", None)


class WriteTimeCapture(_WithConftest):
    """A value present only between the per-test samples (set inside mock.patch.dict, or exported and
    popped in a try/finally) used to escape the set; it is noted at the write now."""

    def _gone(self, name):
        self.assertFalse(name in os.environ, "%s present" % name)

    def test_a_value_set_inside_patch_dict_and_gone_before_the_assertion_is_noted(self):
        v = probe_value("patchdict")
        with mock.patch.dict(os.environ, {"ROMP_TEST_REDACTION_PD": v}):
            self.assertTrue(v in self.cf._ENV_VALUES_SEEN, "noted at the write, inside the block")
        self._gone("ROMP_TEST_REDACTION_PD")
        self.assertTrue(v in self.cf._ENV_VALUES_SEEN, "gone from the environment, still redacted")
        self.assertTrue(v not in self.cf.redact_env_values("x " + v, self.cf._ENV_VALUES_SEEN))

    def test_every_write_path_is_noted(self):
        vals = {}
        vals["set"] = probe_value("setitem")
        os.environ["ROMP_TEST_REDACTION_W1"] = vals["set"]
        vals["update"] = probe_value("update")
        os.environ.update({"ROMP_TEST_REDACTION_W2": vals["update"]})
        vals["setdefault"] = probe_value("setdefault")
        os.environ.setdefault("ROMP_TEST_REDACTION_W3", vals["setdefault"])
        vals["putenv"] = probe_value("putenv")
        os.putenv("ROMP_TEST_REDACTION_W4", vals["putenv"])          # bypasses os.environ entirely
        vals["bytes"] = probe_value("bytes")
        os.environb[b"ROMP_TEST_REDACTION_W5"] = vals["bytes"].encode()
        try:
            for how, v in vals.items():
                self.assertTrue(v in self.cf._ENV_VALUES_SEEN, how)
        finally:
            for n in ("W1", "W2", "W3", "W5"):
                os.environ.pop("ROMP_TEST_REDACTION_" + n, None)
            os.unsetenv("ROMP_TEST_REDACTION_W4")

    def test_the_write_hook_applies_the_same_rule_as_the_sampler(self):
        short = "short-val"
        os.environ["ROMP_TEST_REDACTION_SHORT"] = short
        p = "/a/path/long/enough/to/qualify/by/length"
        was = os.environ.get("LS_COLORS")
        os.environ["LS_COLORS"] = p                                  # a path-valued shell name: exempt
        try:
            self.assertFalse(short in self.cf._ENV_VALUES_SEEN, "under the floor")
            self.assertFalse(p in self.cf._ENV_VALUES_SEEN, "a path-valued name is exempt at the write too")
        finally:
            os.environ.pop("ROMP_TEST_REDACTION_SHORT", None)
            if was is None:
                os.environ.pop("LS_COLORS", None)
            else:
                os.environ["LS_COLORS"] = was
        self.assertTrue(self.cf.note_env_value("A_TOKEN", probe_value("direct")))
        self.assertFalse(self.cf.note_env_value("A_TOKEN", "tiny"))
        self.assertFalse(self.cf.note_env_value(b"PWD", b"/x/y/z/long/enough/to/count/twice"))
        self.assertFalse(self.cf.note_env_value(3, None))

    def test_the_hook_is_installed_once(self):
        self.assertTrue(getattr(os._Environ.__setitem__, "_romp_notes_values", False))
        self.assertTrue(getattr(os.putenv, "_romp_notes_values", False))
        before = (os._Environ.__setitem__, os.putenv)
        self.cf._install_env_write_hook()
        self.assertEqual((os._Environ.__setitem__, os.putenv), before, "a second install stacks no wrapper")


class CredentialPattern(_WithConftest):
    def test_credential_shaped_tokens_are_redacted_by_pattern_whatever_their_provenance(self):
        for prefix in ("sk-ant-api03-", "sk-or-v1-", "sk-proj-", "hf_", "AIza", "rpa_"):
            tok = patterned_probe(prefix)
            text = "the child said %s and moved on" % tok
            red = self.cf.redact_credential_tokens(text)
            self.assertFalse(tok in red, prefix)
            self.assertEqual(red, "the child said %s and moved on" % self.cf.CREDENTIAL_REDACTED, prefix)

    def test_a_long_token_where_a_value_sits_is_redacted_and_ordinary_text_is_not(self):
        tok = uuid.uuid4().hex + uuid.uuid4().hex                   # 64 characters, no known prefix
        for text in ("KEY=%s" % tok, "Authorization: Bearer %s" % tok, "{'X_TOKEN': '%s'}" % tok,
                     'header: "%s"' % tok, "x-api-key:%s" % tok):
            red = self.cf.redact_credential_tokens(text)
            self.assertFalse(tok in red, text[:12])
            self.assertTrue(self.cf.CREDENTIAL_REDACTED in red)
        for text in ("sha256:1a2b3c1a2b3c", "XDG_STATE_HOME=/tmp/romp-tests-state-%s/floor" % tok,
                     "the word %s alone" % tok, "at: 1700000000", "n=%s" % uuid.uuid4().hex[:31],
                     "testMethod=test_a_long_descriptive_name_without_a_digit_in_it_stays_readable"):
            self.assertEqual(self.cf.redact_credential_tokens(text), text, text[:20])
        self.assertEqual(self.cf.redact_credential_tokens(None), None)

    def test_the_two_nets_are_applied_in_order_and_share_one_pattern_list(self):
        v = probe_value("env")
        tok = patterned_probe()
        text = "env %s and token %s" % (v, tok)
        red = self.cf.redact_report_text(text, {v})
        self.assertEqual(red, "env %s and token %s" % (self.cf.ENV_VALUE_REDACTED, self.cf.CREDENTIAL_REDACTED))
        self.assertEqual(self.cf.CREDENTIAL_REDACTED, "[REDACTED-CREDENTIAL]")
        self.assertEqual(os.path.realpath(self.cf._credpat.__file__), PATTERNS, "the conftest loads this file")
        self.assertIs(self.cf.redact_credential_tokens("x"), "x")


class ReportShapes(_WithConftest):
    """_redact_report on report objects of each outcome: the values it knows are gone from every text."""

    def _seen(self, v):
        self.cf._ENV_VALUES_SEEN.add(v)

    def test_a_failures_longrepr_and_sections_are_redacted(self):
        v = probe_value("fail")
        self._seen(v)
        rep = SimpleNamespace(failed=True, longrepr="AssertionError: got " + v,
                              sections=[("Captured stdout call", "printed " + v + "\n")])
        self.cf._redact_report(rep)
        self.assertEqual(rep.longrepr, "AssertionError: got " + self.cf.ENV_VALUE_REDACTED)
        self.assertEqual(rep.sections, [("Captured stdout call", "printed " + self.cf.ENV_VALUE_REDACTED + "\n")])

    def test_a_passed_tests_sections_are_redacted_too(self):
        v = probe_value("pass")
        self._seen(v)
        rep = SimpleNamespace(failed=False, longrepr=None, sections=[("Captured stderr call", v)])
        self.cf._redact_report(rep)
        self.assertEqual(rep.sections, [("Captured stderr call", self.cf.ENV_VALUE_REDACTED)], "-rA shows these")
        self.assertIsNone(rep.longrepr)

    def test_a_skips_reason_tuple_keeps_its_shape(self):
        v = probe_value("skip")
        self._seen(v)
        rep = SimpleNamespace(failed=False, longrepr=("tests/test_x.py", 12, "Skipped: no auth for " + v), sections=[])
        self.cf._redact_report(rep)
        self.assertEqual(rep.longrepr, ("tests/test_x.py", 12, "Skipped: no auth for " + self.cf.ENV_VALUE_REDACTED))
        rep = SimpleNamespace(failed=False, longrepr=("tests/test_x.py", 12, "Skipped: fine"), sections=[])
        self.cf._redact_report(rep)
        self.assertEqual(rep.longrepr, ("tests/test_x.py", 12, "Skipped: fine"), "unchanged when nothing matched")

    def test_an_unchanged_longrepr_object_is_left_as_pytests_own(self):
        obj = object()
        rep = SimpleNamespace(failed=True, longrepr=obj, sections=[])
        self.cf._redact_report(rep)
        self.assertIs(rep.longrepr, obj, "no match: pytest's rich rendering is kept")
        tok = patterned_probe()
        rep = SimpleNamespace(failed=True, longrepr="the child printed " + tok, sections=[])
        self.cf._redact_report(rep)
        self.assertEqual(rep.longrepr, "the child printed " + self.cf.CREDENTIAL_REDACTED, "the pattern net runs here too")

    def test_both_hooks_are_declared(self):
        self.assertTrue(callable(getattr(self.cf, "pytest_runtest_makereport", None)))
        self.assertTrue(callable(getattr(self.cf, "pytest_collectreport", None)))


class HookEndToEnd(unittest.TestCase):
    def _run(self, d, *args):
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--rootdir", d] + list(args),
                           cwd=d, capture_output=True, text=True, timeout=180)
        return r.returncode, r.stdout + r.stderr

    def test_a_failing_test_that_renders_an_environment_value_prints_the_marker(self):
        d = tempfile.mkdtemp()
        try:
            _copy_hook(d)
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

    def test_a_patch_dict_value_a_split_header_and_a_patterned_token_all_print_markers(self):
        # three leaks the first hook missed, one run: a value set inside mock.patch.dict and gone
        # before the assertion (never in the environment at a sample); a header-shaped value that
        # assertDictEqual's pprint splits so the token half stands alone; a pattern-shaped token
        # that never touched the environment at all (read from a file)
        d = tempfile.mkdtemp()
        try:
            _copy_hook(d)
            probes = {"pd": probe_value("patchdict"), "hdr_tok": probe_value("header"), "pat": patterned_probe()}
            with open(os.path.join(d, "probes.json"), "w") as fh:
                json.dump(probes, fh)
            with open(os.path.join(d, "test_probe_three.py"), "w") as fh:
                fh.write("import json, os, unittest\n"
                         "from unittest import mock\n"
                         "P = json.load(open(os.path.join(os.path.dirname(__file__), 'probes.json')))\n\n"
                         "def test_patch_dict():\n"
                         "    with mock.patch.dict(os.environ, {'ROMP_TEST_PROBE_PD': P['pd']}):\n"
                         "        pass\n"
                         "    assert 'ROMP_TEST_PROBE_PD' not in os.environ\n"
                         "    assert P['pd'] == 'something else', 'the message carries ' + P['pd']\n\n"
                         "class Header(unittest.TestCase):\n"
                         "    def test_header(self):\n"
                         "        os.environ['ROMP_TEST_PROBE_HDR'] = 'Authorization: Bearer ' + P['hdr_tok']\n"
                         "        self.assertDictEqual({'Authorization': 'Bearer ' + P['hdr_tok']},\n"
                         "                             {'Authorization': 'Bearer other'})\n\n"
                         "def test_pattern():\n"
                         "    assert P['pat'] == 'something else', 'the message carries ' + P['pat']\n")
            rc, out = self._run(d, "test_probe_three.py")
            self.assertNotEqual(rc, 0)
            self.assertTrue("3 failed" in out, out[-600:])
            for name, v in probes.items():
                self.assertFalse(v in out, "%s reached the report" % name)
            self.assertGreaterEqual(out.count("[REDACTED-ENV-VALUE]"), 2, "the patch.dict message and the header chunk")
            self.assertGreaterEqual(out.count("[REDACTED-CREDENTIAL]"), 1, "the patterned token, with no provenance")
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_a_passed_tests_output_under_rA_and_a_collection_error_print_the_marker(self):
        d = tempfile.mkdtemp()
        try:
            _copy_hook(d)
            with open(os.path.join(d, "test_probe_pass.py"), "w") as fh:
                fh.write("import os\n\n"
                         "def test_pass():\n"
                         "    print('a passing test prints ' + os.environ['ROMP_TEST_REDACTION_PROBE'])\n")
            with open(os.path.join(d, "test_probe_broken.py"), "w") as fh:
                fh.write("import os\n"
                         "raise RuntimeError('collection carries ' + os.environ['ROMP_TEST_REDACTION_PROBE'])\n")
            v = probe_value("outcomes")
            env = dict(os.environ, ROMP_TEST_REDACTION_PROBE=v)
            r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-rA", "-p", "no:cacheprovider", "--rootdir", d,
                                "--continue-on-collection-errors", "test_probe_pass.py", "test_probe_broken.py"],
                               cwd=d, env=env, capture_output=True, text=True, timeout=180)
            out = r.stdout + r.stderr
            self.assertNotEqual(r.returncode, 0, "the collection error fails the run")
            self.assertTrue("1 passed" in out and "1 error" in out, out[-600:])
            self.assertFalse(v in out, "neither the passed test's captured stdout nor the collection error shows the value")
            self.assertGreaterEqual(out.count("[REDACTED-ENV-VALUE]"), 2)
        finally:
            shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
