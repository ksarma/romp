"""T418's screenshots stay inside the run's own state root, and are off unless asked for (2026-10-03).

tests/test_tool_rows_vocab_browser.py drives the chat page in a browser and can save six screenshots. Until this date it saved them
by default, to a drops folder built from the home directory (~/.local/state/romp/drops) whenever that folder's parent existed, so a
full test run on a machine running romp wrote into that machine's live state root. The module now saves them only under
T418_SHOTS=1, into drops/ under the run's state root: ROMP_STATE_DIR, else <XDG_STATE_HOME>/romp, read when _result runs.

Pinned by execution through the module's own code, except the driver's half, which the last test reads from its source. Every
other test points HOME at a private temp home that holds a romp state root (as a machine running romp does) and ROMP_STATE_DIR and
XDG_STATE_HOME into a separate private temp tree, loads the browser module afresh under a private name, and calls
ToolRowsVocab._result, the method that picks the directory, creates it and hands it to the browser driver. Only the driver is
stubbed: the stub saves one file per shot the driver takes into the directory the driver was handed, and hands its record back
the way tests/lab_result.cjs does (the record to the drive's result file, one RESULT: line naming it), so _result's read
through tests/lab_result.py passes. Those tests compare every file and directory under the temp home and the temp tree before
the load and after the call. _result's own config and driver files, and the stub's result file, go to a third directory, its
lab, which no assertion reads.

The last test holds DRIVER to the stub's behaviour by reading it: its one page.screenshot call writes at cfg.drops, a slash and a
file name, inside `if (cfg.drops)`. That is a read of the source, not an execution. No test in CI runs the real driver with shots
on (the browser module runs with T418_SHOTS unset); only a real-browser run of that module with T418_SHOTS=1 executes the path.

No browser, kernel or extension deps, so this runs in every cell. No root minted here is handed to a kernel or a backend. The roots
the tests name, under the temp tree, carry session-hosts off all the same (CLAUDE.md, Testing); the temp home's root and the XDG
floor below carry no such file, and neither is handed to anything that could start a host."""
import json
import os
import re
import shutil
import sys
import tempfile
import types
import unittest
from unittest import mock
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
TARGET = os.path.join(HERE, "test_tool_rows_vocab_browser.py")
PRIVATE_NAME = "t418_shots_root_target"   # a private module name, so the collected module's class is never the one changed

# Hermetic state BEFORE the loads below (tests/test_state_isolation_order.py): only pytest runs conftest's floor.
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor

SWITCHES = ("T418_SHOTS", "ROMP_STATE_DIR", "XDG_STATE_HOME")
SOURCE_READ = ("(a read of DRIVER's source, not an execution: no CI test runs the driver with shots on; only a real-browser run of "
               "tests/test_tool_rows_vocab_browser.py with T418_SHOTS=1 does)")


def _tree(root):
    """Every directory and every file under `root`, as root-relative paths: (dirs, files)."""
    dirs, files = set(), set()
    for d, dn, fn in os.walk(root):
        dirs.update(os.path.relpath(os.path.join(d, n), root) for n in dn)
        files.update(os.path.relpath(os.path.join(d, n), root) for n in fn)
    return dirs, files


class ShotsStayInTheStateRoot(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.base = tempfile.mkdtemp(prefix="t418-shots-")
        self.addCleanup(shutil.rmtree, self.base, True)
        self.home = os.path.join(self.base, "home")
        self.tree = os.path.join(self.base, "tree")   # every state root these tests name lives here
        self.lab = os.path.join(self.base, "lab")
        os.makedirs(os.path.join(self.home, ".local", "state", "romp"))   # the live root a machine running romp has
        os.makedirs(self.tree)
        os.makedirs(self.lab)
        saved_path = list(sys.path)
        self.addCleanup(sys.path.__setitem__, slice(None), saved_path)   # the module's load prepends tests/ and the checkout
        self.addCleanup(sys.modules.pop, PRIVATE_NAME, None)
        self.handed = []   # the drops value each driver run was handed
        self.saved = []    # every file the stub driver saved

    def _root(self, *parts):
        """A private state root under the tree, carrying session-hosts off."""
        root = os.path.join(self.tree, *parts)
        os.makedirs(root, exist_ok=True)
        with open(os.path.join(root, "session-hosts"), "w") as f:
            f.write("off\n")
        return root

    def _env(self, **names):
        """For this test: HOME is the temp home, and of SWITCHES exactly `names` are set (a None value, or a name left out, is
        unset). patch.dict puts the whole environment back at cleanup."""
        p = mock.patch.dict(os.environ, {"HOME": self.home})
        p.start()
        self.addCleanup(p.stop)
        for name in SWITCHES:
            if names.get(name) is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = names[name]

    def _snap(self):
        return _tree(self.home), _tree(self.tree)

    def _new(self, before):
        """What appeared since `before`: ((dirs, files) under the home, (dirs, files) under the tree)."""
        after = self._snap()
        return tuple((a[0] - b[0], a[1] - b[1]) for a, b in zip(after, before))

    def _load(self):
        """The browser module, loaded afresh under the environment set so far, with its driver stubbed: (module, the number of
        shots the driver takes per run, read from DRIVER)."""
        mod = load_source(PRIVATE_NAME, TARGET)
        themes = re.findall(r'await run\("([^"]+)"\)', mod.DRIVER)
        shots = re.findall(r'await shot\("([^"]+)" \+ theme\)', mod.DRIVER)
        self.assertTrue(themes and shots, "the driver's themes and shot calls were read from DRIVER: %r %r" % (themes, shots))

        def driver(argv, **kw):
            with open(kw["env"]["CFG"]) as f:
                cfg = json.load(f)
            self.handed.append(cfg.get("drops"))
            if cfg.get("drops"):   # the driver's shot(): `if (cfg.drops)`, then page.screenshot at cfg.drops + "/" + a name
                for theme in themes:
                    for shot in shots:
                        path = os.path.join(cfg["drops"], "%s%s.png" % (shot, theme))
                        with open(path, "wb") as f:
                            f.write(b"synthetic png")
                        self.saved.append(path)
            # the shared helper's protocol (tests/lab_result.cjs writeResult): the record, with the drive's nonce, to the
            # result file the cfg names, then one RESULT: line naming the file and the nonce
            with open(cfg["resultPath"], "w") as f:
                json.dump({"nonce": cfg["resultNonce"], "record": {}}, f)
            line = {"resultPath": cfg["resultPath"], "nonce": cfg["resultNonce"]}
            return types.SimpleNamespace(returncode=0, stdout="\nRESULT:" + json.dumps(line) + "\n", stderr="")

        mod.subprocess = types.SimpleNamespace(run=driver)   # the private module's own binding, nobody else's
        return mod, len(themes) * len(shots)

    def _run(self, mod):
        """ToolRowsVocab._result of a module from _load, under the environment as it is now."""
        cls = mod.ToolRowsVocab
        cls.lab, cls.port, cls.token, cls._r = self.lab, 1, "synthetic-token", None
        cls()._result()

    def _shots_land_in(self, drops, rel, between=None):
        """Load the module, call `between` if given, then run _result: the run hands the driver `drops`, every shot lands there
        and only there, and nothing appears under the home."""
        before = self._snap()
        mod, n = self._load()
        if between:
            between()
        self._run(mod)
        home_new, tree_new = self._new(before)
        self.assertEqual(home_new, (set(), set()), "nothing may appear under the home directory: %r" % (home_new,))
        self.assertEqual(self.handed, [drops], "the driver was handed drops/ under the state root")
        self.assertEqual(len(self.saved), n, "the stub saved one file per shot the driver takes: %r" % self.saved)
        self.assertEqual(tree_new, ({rel}, {os.path.join(rel, os.path.basename(p)) for p in self.saved}),
                         "the drops directory and the shots, and nothing else, appeared under the tree")

    def test_shots_on_land_in_drops_under_ROMP_STATE_DIR_which_outranks_XDG(self):
        state = self._root("state")
        self._root("xdg", "romp")
        self._env(T418_SHOTS="1", ROMP_STATE_DIR=state, XDG_STATE_HOME=os.path.join(self.tree, "xdg"))
        self._shots_land_in(os.path.join(state, "drops"), os.path.join("state", "drops"))

    def test_shots_on_without_ROMP_STATE_DIR_land_in_drops_under_the_xdg_root(self):
        root = self._root("xdg", "romp")
        self._env(T418_SHOTS="1", XDG_STATE_HOME=os.path.join(self.tree, "xdg"))
        self._shots_land_in(os.path.join(root, "drops"), os.path.join("xdg", "romp", "drops"))

    def test_the_switch_and_the_state_root_are_read_when_the_shots_are_taken_not_when_the_module_loads(self):
        """The module loads with T418_SHOTS unset and ROMP_STATE_DIR at one root; both then change, and the shots follow the
        environment _result runs under. A switch copied at import would take no shots, and a root copied at import would put
        them under the first root."""
        first = self._root("at-load")
        later = self._root("later")
        self._env(ROMP_STATE_DIR=first)
        self._shots_land_in(os.path.join(later, "drops"), os.path.join("later", "drops"),
                            between=lambda: self._env(T418_SHOTS="1", ROMP_STATE_DIR=later))

    def test_shots_are_off_unless_T418_SHOTS_is_1_and_then_nothing_is_written(self):
        state = self._root("state")
        self._root("xdg", "romp")
        for value in (None, "", "0", "true", "yes"):
            with self.subTest(T418_SHOTS=value):
                self.handed, self.saved = [], []
                self._env(T418_SHOTS=value, ROMP_STATE_DIR=state, XDG_STATE_HOME=os.path.join(self.tree, "xdg"))
                before = self._snap()
                self._run(self._load()[0])
                home_new, tree_new = self._new(before)
                self.assertEqual(home_new, (set(), set()), "nothing may appear under the home directory: %r" % (home_new,))
                self.assertEqual(tree_new, (set(), set()), "nothing may appear under the state roots: %r" % (tree_new,))
                self.assertEqual(self.saved, [], "the driver saved no shot")
                self.assertEqual(self.handed, [""], "the driver was handed no drops directory")

    def test_shots_on_with_no_state_root_named_fail_and_write_nothing(self):
        self._env(T418_SHOTS="1")
        before = self._snap()
        mod, _ = self._load()
        try:
            self._run(mod)
            raised = None
        except AssertionError as e:
            raised = e
        home_new, tree_new = self._new(before)
        self.assertEqual(home_new, (set(), set()), "nothing may appear under the home directory: %r" % (home_new,))
        self.assertEqual(tree_new, (set(), set()), tree_new)
        self.assertEqual(self.saved, [], "the driver saved no shot")
        self.assertIsNotNone(raised, "asked for shots with no state root named, the run must fail rather than pick a directory")
        for name in SWITCHES:
            self.assertIn(name, str(raised), "the refusal names the switch and both state-root names: %s" % raised)
        self.assertEqual(self.handed, [], "the refusal comes before the driver runs")

    def test_DRIVER_source_writes_each_shot_into_the_directory_it_was_handed(self):
        """The half the stub stands in for, held by a read of DRIVER's source, not an execution. Its one page.screenshot call
        writes at cfg.drops + "/" + a file name, inside `if (cfg.drops)`; every shot() call has the form the stub reads; and no
        shot name or theme carries a slash. So a shot lands in the directory _result handed the driver, and nowhere when it was
        handed none. No CI test runs the driver with shots on (the browser module runs with T418_SHOTS unset); only a
        real-browser run of tests/test_tool_rows_vocab_browser.py with T418_SHOTS=1 executes this path."""
        src = load_source(PRIVATE_NAME, TARGET).DRIVER
        self.assertEqual(src.count("page.screenshot("), 1, "one screenshot call in the driver " + SOURCE_READ)
        self.assertEqual(len(re.findall(r'page\.screenshot\(\{ path: cfg\.drops \+ "/[^"/]*" \+ name \+ "[^"/]*" \}\)', src)), 1,
                         "the screenshot path is cfg.drops, a slash, then the shot's name between literals with no slash in them "
                         + SOURCE_READ)
        self.assertRegex(src, r'const shot = async \(name\) => \{ if \(cfg\.drops\) \{ try \{ await page\.screenshot\(',
                         "the screenshot runs only when the driver was handed a drops directory " + SOURCE_READ)
        names = re.findall(r'await shot\("([^"]*)" \+ theme\)', src)
        themes = re.findall(r'await run\("([^"]+)"\)', src)
        self.assertEqual(len(re.findall(r'\bshot\(', src)), len(names),
                         "every shot() call is `await shot(\"<literal>\" + theme)`, the form the stub reads: %r " % names
                         + SOURCE_READ)
        self.assertTrue(names and themes, "the shot names and themes were read from DRIVER: %r %r" % (names, themes))
        self.assertEqual([x for x in names + themes if "/" in x], [],
                         "no shot name or theme carries a slash, so a file lands in cfg.drops itself " + SOURCE_READ)


if __name__ == "__main__":
    unittest.main()
