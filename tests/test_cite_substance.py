#!/usr/bin/env python3
"""T218, arm 1 + the span protocol's kernel half (the manager's 87-pair study, 2026-09-01): summary
deep links landed on ANNOUNCEMENTS because only assistant prose was ever citable — when the substance
was a postal ready-report or a PR link, the model could cite only the message that said the work was
starting. Substantive non-prose atoms now take [mN] labels too: a PEER postal report at the same
substantive-prose floor, and a tool result carrying a PR/commit link (the link IS the substance).
And the SOURCE protocol grows a supporting-span half: the model may return a short verbatim QUOTE of
its supporting sentence; _split_source parses it and _locate_quote finds it in the cited atom's text
(exact, then whitespace/case-normalized; unfindable → None, never a guess). Synthetic fixtures only."""
import os
import tempfile
import unittest
from importlib.machinery import SourceFileLoader

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)
jd = SourceFileLoader("romp_judge_t218", os.path.join(BIN, "romp-judge")).load_module()

LONG = " it took three passes over the synthetic corpus and the verdicts held up end to end."


def _atom(uuid, typ, author, text, blocks=None):
    content = ([{"type": "text", "text": text}] if text else []) + (blocks or [])
    return {"type": typ, "uuid": uuid, "author": author, "message": {"content": content}}


class SubstantiveAtomsAreCitable(unittest.TestCase):
    def test_peer_report_and_pr_result_take_labels(self):
        marks = jd._CiteMarks()
        atoms = [
            _atom("u-ask", "user", "human", "please ship the widget fix"),
            # the announcement — assistant prose, citable as before
            _atom("a-announce", "assistant", None, "Committing and shipping the widget fix now —" + LONG),
            # the SUBSTANCE, previously invisible to citation:
            _atom("u-peer", "user", {"peer": "22222222-3333-4444-5555-666666666666", "mid": "m.1", "kind": "coordinate"},
                  "ready: the widget fix landed, suite green, follow-ups filed —" + LONG),
            _atom("u-pr", "user", None, "", blocks=[{"type": "tool_result",
                  "content": [{"type": "text", "text": "https://github.com/notes-api/web/pull/4242\nauto-merge armed"}]}]),
        ]
        jd._unit_text(atoms, marker=marks)
        cited = set(marks.map.values())
        self.assertIn("a-announce", cited, "assistant prose keeps its label")
        self.assertIn("u-peer", cited, "a substantive PEER report is citable — the study's postal class")
        self.assertIn("u-pr", cited, "a PR-link tool result is citable — the link IS the substance")

    def test_floors_hold_stubs_and_plain_tool_noise_stay_uncitable(self):
        marks = jd._CiteMarks()
        atoms = [
            _atom("u-peer-stub", "user", {"peer": "22222222-3333-4444-5555-666666666666", "mid": "m.2", "kind": "coordinate"},
                  "on it"),                                       # sub-floor peer ping
            _atom("u-plain-tool", "user", None, "", blocks=[{"type": "tool_result",
                  "content": [{"type": "text", "text": "total 12\ndrwxr-xr-x 2 tests tests 4096 ."}]}]),
        ]
        jd._unit_text(atoms, marker=marks)
        self.assertEqual(marks.map, {}, "stubs and linkless tool output stay uncitable by construction")


class SupportingSpan(unittest.TestCase):
    def test_split_source_parses_the_optional_quote(self):
        body, src, quote = jd._split_source(
            'The fix landed and the suite is green.\nSOURCE: m3\nQUOTE: "the suite is green end to end"')
        self.assertEqual(src, "m3")
        self.assertEqual(quote, "the suite is green end to end")
        self.assertNotIn("QUOTE", body)
        body2, src2, quote2 = jd._split_source("Take.\nSOURCE: m2")
        self.assertEqual((src2, quote2), ("m2", None), "the quote is optional — absent stays today's shape")
        body3, src3, quote3 = jd._split_source("Take with no citation at all.")
        self.assertEqual((src3, quote3), (None, None))

    def test_locate_quote_exact_then_normalized_then_honestly_none(self):
        atom_text = "Multi-topic wrap.  The   Suite is GREEN end to end.\nAnd more topics follow."
        self.assertEqual(jd._locate_quote(atom_text, "Suite is GREEN"),
                         (atom_text.index("Suite is GREEN"), "Suite is GREEN"))
        off, span = jd._locate_quote(atom_text, "the suite is green end to end")
        self.assertEqual(span, "The   Suite is GREEN end to end",
                         "normalized match maps back to the atom's RAW span")
        self.assertEqual(off, atom_text.index("The   Suite"))
        self.assertEqual(jd._locate_quote(atom_text, "never said this"), (None, None),
                         "unfindable → None, never a guess (the honest-fallback rule)")
        self.assertEqual(jd._locate_quote(atom_text, ""), (None, None))


if __name__ == "__main__":
    unittest.main()
