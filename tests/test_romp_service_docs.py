#!/usr/bin/env python3
"""The two documents that enumerate `romp-service rewrite`'s exit 5 name the plutil refusal (round 8 of fork PR #778, regression-3).

The round-7 addendum added a refusal class the reference documented nowhere: a plutil whose line end the reader cannot tell from a
value's own is refused for EVERY plist read through it, exit 5, on a file that is fine, and bin/README.md's exit-5 clause had two
disjuncts (a compared value differs; the file's form) covering neither. Round 8 added the type refusal to the same class. Each pin
asserts the sentence by its text, not by a bare grep for ROMP_PLUTIL, which a code comment would satisfy."""
import os
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)


def _read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


class ExitFiveDocs(unittest.TestCase):
    def test_bin_readme_names_the_plutil_the_reader_runs_among_the_exit_5_disjuncts(self):
        text = _read("bin/README.md")
        self.assertIn("or when the plutil the reader runs cannot be read through (its line end on a raw extract cannot be told from a "
                      "value's own, or it renders an entry that is not a string; every plist read through such a plutil is refused, and "
                      "the text names another plutil in `ROMP_PLUTIL` or a fresh `romp-service install` as the ways out", text)

    def test_the_reference_says_how_plutil_is_classified_and_the_two_ways_out(self):
        text = _read("docs/reference.md").replace("\n", " ")
        for sentence in ("Through `plutil` the reader first learns the tool's line end on a scratch plist of its own",
                         "checks it on the file (every extract must end as the scratch said, each value is read with and without `-n` "
                         "where the tool honours that switch, and each value is echoed through the scratch and must read back as it did "
                         "on the file), reads `<string>` entries alone, and refuses every plist read through a plutil it cannot classify, "
                         "or that renders an entry of another type, with exit 5 and nothing written, naming the two ways out: another "
                         "plutil in `ROMP_PLUTIL`, or `romp-service install` from the owning shell and clone, which reads no plist."):
            self.assertIn(sentence, text)


if __name__ == "__main__":
    unittest.main()
