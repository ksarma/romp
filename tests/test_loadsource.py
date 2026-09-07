#!/usr/bin/env python3
"""kernel/loadsource.py keeps the properties of SourceFileLoader.load_module() that the kernel and the
tests rely on (2026-09-06; Python 3.15 removes that call). Each property is a test here, against
throwaway modules written to a temp dir under a private name: nothing under test reads romp state.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
# Hermetic state BEFORE the loads — the ratchet counts every load_source call as a load; the modules
# loaded here are throwaway, and the floor costs two lines.
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor

NAME = "romp_loadsource_probe"           # private: no other module loads under it


class LoadSource(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.dir = Path(self.td.name)
        sys.modules.pop(NAME, None)

    def tearDown(self):
        sys.modules.pop(NAME, None)
        self.td.cleanup()

    def _write(self, name, body):
        p = self.dir / name
        p.write_text(body)
        return p

    def test_a_fresh_load_is_registered_before_it_executes(self):
        p = self._write("a.py", "import sys\nSELF = sys.modules.get(__name__)\nVALUE = 1\n")
        mod = load_source(NAME, p)
        self.assertIs(mod.SELF, mod, "the module saw itself in sys.modules while its own body ran")
        self.assertIs(sys.modules[NAME], mod)
        self.assertEqual(mod.__name__, NAME)
        self.assertEqual(mod.__file__, str(p))
        self.assertEqual(mod.__spec__.origin, str(p))
        self.assertEqual(mod.VALUE, 1)

    def test_a_second_load_under_the_same_name_reexecutes_the_same_object(self):
        # kernel.py and judge.py both load romp_event_model, and every test module loads romp_judge
        # before the kernel does: the second load must land in the FIRST module object (km.jd is jd),
        # with the module's own attributes saying where its code now comes from
        a = self._write("a.py", "VALUE = 1\n")
        b = self._write("b.py", "VALUE = 2\n")
        first = load_source(NAME, a)
        second = load_source(NAME, b)
        self.assertIs(second, first)
        self.assertIs(sys.modules[NAME], first)
        self.assertEqual(first.VALUE, 2, "re-executed from the new path")
        self.assertEqual(first.__file__, str(b))
        self.assertEqual(first.__spec__.origin, str(b))
        self.assertIs(first.__loader__, first.__spec__.loader)

    def test_a_failing_first_load_leaves_no_entry(self):
        p = self._write("bad.py", "import sys\nassert __name__ in sys.modules\nraise RuntimeError('boom')\n")
        with self.assertRaises(RuntimeError):
            load_source(NAME, p)
        self.assertNotIn(NAME, sys.modules, "a half-built module is never left behind")

    def test_a_failing_reload_keeps_the_existing_module_registered(self):
        # load_module()'s behaviour, kept: the re-executed object stays what it was, in sys.modules
        good = self._write("good.py", "VALUE = 1\n")
        bad = self._write("bad.py", "raise RuntimeError('boom')\n")
        mod = load_source(NAME, good)
        with self.assertRaises(RuntimeError):
            load_source(NAME, bad)
        self.assertIs(sys.modules[NAME], mod)

    def test_a_path_without_a_py_suffix_loads(self):
        # the bin/ names (romp-kernel, romp-judge) carry no suffix, which is why an explicit
        # SourceFileLoader is built rather than spec_from_file_location guessing one
        p = self._write("romp-probe", "VALUE = 3\n")
        self.assertEqual(load_source(NAME, p).VALUE, 3)


if __name__ == "__main__":
    unittest.main()
