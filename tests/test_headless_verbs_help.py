#!/usr/bin/env python3
"""The four surfaces that describe `romp send`, `romp interrupt` and `romp end` agree: the verb's own
`--help`, the no-argument misuse line, the `romp help` row, and the docs/reference.md command table spell
one invocation, name the same flags (`self`, `--now`, `--when-idle`, `--tag`) and the three prose surfaces
each say that an unknown session is refused with the kernel's reason and exit 1. The per-verb help was
added with the 404 refusal (2026-09-09) and was the only surface that named `self` and the two `end`
flags; the row and the reference were the bare forms (review find, rules-2), and the no-argument line
kept a bare form of its own with a trailing space (review round 2). The precedent is
tests/test_keyswap_refusal.py's HelpAndDocsAgree.

`romp <verb> --help` and the bare `romp <verb>` are rendered by running the script hermetically (no kernel:
ROMP_KERNEL_PORT=1, a temp HOME); the row and the reference are read from the source. Synthetic env only,
nothing is posted."""
import os
import re
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
ROMP = os.path.join(ROOT, "bin", "romp")

VERBS = ("send", "interrupt", "end")
FLAG = re.compile(r"(?<![\w-])(--[a-z][a-z-]*|self)(?![\w-])")
REFUSAL_ROW = "an unknown session is refused with the kernel's reason, exit 1"
REFUSAL_DOC = "An unknown session is refused with the kernel's reason and exit 1"
REFUSAL_HELP = "An unknown session name exits 1 with the kernel's reason."


def _read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


def _run(*args):
    home = tempfile.mkdtemp()
    env = {"HOME": home, "PATH": os.environ.get("PATH", "/usr/bin:/bin"), "ROMP_KERNEL_PORT": "1",
           "XDG_STATE_HOME": os.path.join(home, "state"), "XDG_CONFIG_HOME": os.path.join(home, "config")}
    return subprocess.run(["bash", ROMP, *args], env=env, capture_output=True, text=True, timeout=30)


def _verb_help(verb):
    return _run(verb, "--help")


def _verb_bare(verb):
    """The verb with no session argument: the misuse line on stderr, exit 2, nothing on stdout."""
    return _run(verb)


def _flags(text):
    return set(FLAG.findall(text))


class HelpSurfacesAgree(unittest.TestCase):

    def setUp(self):
        self.src = _read("bin/romp")
        self.ref = _read("docs/reference.md")

    def _usage_form(self, verb):
        out = _verb_help(verb)
        self.assertEqual(out.returncode, 0, out.stderr)
        first = out.stdout.splitlines()[0]
        self.assertTrue(first.startswith("usage: romp %s " % verb), first)
        return first[len("usage: "):], out.stdout

    def _help_row(self, verb):
        m = re.search(r'_romp_cmd "(romp %s [^"]*)"\s+-\s+"([^"]*)"' % verb, self.src)
        self.assertIsNotNone(m, "romp help has a row for %s" % verb)
        return m.group(1), m.group(2)

    def _reference_row(self, form):
        cell = "| `%s` |" % form.replace("|", "\\|")            # a table cell escapes the pipe
        i = self.ref.find(cell)
        self.assertGreaterEqual(i, 0, "docs/reference.md has the row %s" % cell)
        return self.ref[i:self.ref.find("\n", i)]

    def test_each_verb_spells_one_invocation_on_all_three_surfaces(self):
        for verb in VERBS:
            form, _ = self._usage_form(verb)
            row_form, _ = self._help_row(verb)
            self.assertEqual(row_form, form, "%s: the romp help row spells the --help form" % verb)
            self._reference_row(form)                          # asserts the reference carries the same form

    def test_each_verb_names_the_same_flags_everywhere(self):
        for verb in VERBS:
            form, rendered = self._usage_form(verb)
            row_form, row_desc = self._help_row(verb)
            ref_row = self._reference_row(form)
            expect = _flags(form)
            self.assertEqual(_flags(rendered), expect, "%s --help names no flag its usage line lacks" % verb)
            self.assertEqual(_flags(row_form) | (_flags(row_desc) & expect), expect, verb)
            self.assertTrue(expect <= _flags(ref_row), "%s: the reference row names %s" % (verb, sorted(expect)))

    def test_end_names_self_and_both_timing_flags(self):
        form, _ = self._usage_form("end")
        self.assertEqual(_flags(form), {"self", "--now", "--when-idle"})
        self.assertEqual(_flags(self._usage_form("send")[0]), {"--tag"})
        self.assertEqual(_flags(self._usage_form("interrupt")[0]), set())

    def test_the_bare_verb_prints_the_help_usage_line(self):
        # the no-argument call is a fourth surface: it printed `usage: romp end <session> ` (the bare
        # form, with a trailing space from an empty substitution) while --help spelled the full form, so
        # each verb had two usage strings. One string per verb now, set once and echoed from every misuse
        # arm and from --help (review round 2, 2026-09-09)
        for verb in VERBS:
            form, _ = self._usage_form(verb)
            out = _verb_bare(verb)
            self.assertEqual(out.returncode, 2, verb)
            self.assertEqual(out.stdout, "", "%s: misuse speaks on stderr only" % verb)
            self.assertEqual(out.stderr.splitlines()[0], "usage: " + form, verb)

    def test_every_surface_states_the_unknown_session_contract(self):
        for verb in VERBS:
            form, rendered = self._usage_form(verb)
            self.assertIn(REFUSAL_HELP, rendered, verb)
            self.assertIn(REFUSAL_ROW, self._help_row(verb)[1], verb)
            self.assertIn(REFUSAL_DOC, self._reference_row(form), verb)


if __name__ == "__main__":
    unittest.main()
