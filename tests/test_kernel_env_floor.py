#!/usr/bin/env python3
"""The suite-wide CLI-binary floor (tests/conftest.py: ROMP_CLAUDE_BIN=/bin/false) holds for every test, in both halves the
cli-scope floor has (tests/test_cli_scope_floor.py): set at import, and re-asserted per test by an autouse fixture, because a
test module's module-level write executes at COLLECTION and holds for every test after it. The case that wrote this
(2026-09-16): tests/test_login_flow.py set its login mock as the CLI at module level, so under a whole run every lab kernel
(kernel_env passes ROMP_CLAUDE_BIN through) ran its judges against the mock, whose answers the planner's coerce floor turned
into goals; the auto-nudge fired into sessions no CLI could run, and the nudge walk read the parked nudges as the user's
queued input for both boots of tests/test_fold_checkpoints_served.py, one red only under a whole suite, green alone.

Until 2026-09-22 a second pin here walked every test module for a module-level assignment of the name, top level only,
the subscript shape only, test_*.py only. That walk is retired (the reviewer's ruling on fork PR #813's finding: one
definition of a module-level environment write in this repo): the property is held by tests/test_hermetic_kernel_postal.py
for EVERY name, every write shape, module-level if/try/for/with bodies included, every .py under tests/, as an equality
against a licensed set that ROMP_CLAUDE_BIN is not in, so a module-level write of it in a test module reds there, naming
the module and the line. Retiring lost nothing the wider pin does not hold; the message a reader of that fault needs (a
module-level CLI write reaches every lab kernel of the run) lives beside the floor in tests/conftest.py. What stays here
is the property specific to the floor: an autouse fixture re-asserts the value, and the value holds while a test runs.
Synthetic throughout: the inputs are the test files' text."""
import ast
import os
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
CONFTEST = os.path.join(HERE, "conftest.py")
NAME = "ROMP_CLAUDE_BIN"


def _assigns_env(stmt, name):
    """Is `stmt` an assignment os.environ[name] = ...?"""
    if not isinstance(stmt, ast.Assign):
        return False
    for t in stmt.targets:
        if (isinstance(t, ast.Subscript) and isinstance(t.value, ast.Attribute) and t.value.attr == "environ"
                and isinstance(t.slice, ast.Constant) and t.slice.value == name):
            return True
    return False


def _is_autouse_fixture(fn):
    for d in fn.decorator_list:
        if not (isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute) and d.func.attr == "fixture"):
            continue
        for kw in d.keywords:
            if kw.arg == "autouse" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                return True
    return False


class CliBinaryFloor(unittest.TestCase):
    def setUp(self):
        with open(CONFTEST) as f:
            self.body = ast.parse(f.read(), filename=CONFTEST).body

    def test_an_autouse_fixture_re_asserts_the_binary_floor_per_test(self):
        fixtures = [fn for fn in self.body if isinstance(fn, ast.FunctionDef) and _is_autouse_fixture(fn)]
        self.assertTrue(fixtures, "tests/conftest.py has no autouse fixtures at all")
        self.assertTrue(any(any(_assigns_env(stmt, NAME) for stmt in fn.body) for fn in fixtures),
                        "no autouse fixture in tests/conftest.py sets os.environ[%r]: one test module's import-time write would "
                        "hold for every lab kernel after it (the served checkpoint lab's judges answered by a login mock)" % NAME)

    def test_the_module_level_write_rule_for_this_name_is_the_repo_wide_pins(self):
        """The name is outside the licensed set of tests/test_hermetic_kernel_postal.py, so a test module writing it at
        module level reds there; this pin says where the rule lives so a reader does not look for the retired walk here."""
        from tests.test_hermetic_kernel_postal import LICENSED_MODULE_LEVEL_WRITES, FLOOR_MODULES
        self.assertNotIn(NAME, LICENSED_MODULE_LEVEL_WRITES, "a module-level %s in a test module is a leak the repo-wide pin reds on" % NAME)
        self.assertIn("conftest.py", FLOOR_MODULES, "conftest's own write of the floor is the licensed one")

    def test_the_value_holds_while_this_test_runs(self):
        self.assertEqual(os.environ.get(NAME), "/bin/false", "the floor, re-asserted by the fixture before this test")


if __name__ == "__main__":
    unittest.main()
