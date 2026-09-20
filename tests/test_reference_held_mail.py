#!/usr/bin/env python3
"""docs/reference.md's held-mail clause states the readers' rule and cites it, instead of listing shapes.

The state-files paragraph of the reference has one clause on the held-mail store, the one store with two
readers (the kernel's, which builds the cards, and the bus's, which serves `GET /quarantine` and the summary
peers see). The states a reader of a store meets are stated once, in the kernel's `_note_read_fault_once`
docstring, and every reader cites that statement rather than restating it; the reference's clause is held to
the same rule here. The clause the second review round replaced (2026-09-20) enumerated the shapes the kernel
moves aside in a parenthetical, so the next shape added to the code would have falsified it again, and it said
a record the kernel "cannot read" is left in place, which the `.json` link with nothing behind it falsifies:
that link is moved aside by its own name, as the one labelled exception. These pins hold the clause to the rule:
it names the statement, carries no enumeration of the move-aside shapes, qualifies the read-fault state the way
the statement does (a stat or read fault on bytes that exist), names the link as the exception, states the
refusal of a store none of whose records could be served while one could not be read (one record alone
included), and gives a type-wrong `at` the build's time instead of a move aside.

Text only: this module reads docs/reference.md and kernel/kernel.py as text and loads no romp code, so it
needs no hermetic-state preamble. Over a git archive of the reviewed head (085e08deb) it is red at the phrase
pins the clause exists for (the citation absent, the enumeration present), never on a symbol or a signature.
"""
import os
import re
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def _flat(text):
    """Collapse hard wraps so a phrase that spans a line break in the doc still compares."""
    return re.sub(r"\s+", " ", text)


REFERENCE = _flat(_read("docs", "reference.md"))
DOC = "docs/reference.md"
KERNEL = _read("kernel", "kernel.py")

CLAUSE_HEAD = "The held-mail store is the exception to the first of those sentences"
CLAUSE_TAIL = "The sidecars are yours to inspect or delete."
STATEMENT = "_note_read_fault_once"


def _clause():
    """The held-mail clause of the state-files paragraph: from its opening sentence to the paragraph's end."""
    start = REFERENCE.find(CLAUSE_HEAD)
    end = REFERENCE.find(CLAUSE_TAIL, start)
    if start < 0 or end < 0:
        raise AssertionError("%s no longer carries the held-mail clause between %r and %r" % (DOC, CLAUSE_HEAD, CLAUSE_TAIL))
    return REFERENCE[start:end]


class _Pins(unittest.TestCase):
    def assertQuoted(self, needle, haystack, where, msg=""):
        # a bare assertIn would print the whole clause on a miss; name the missing text and the file instead
        self.assertTrue(needle in haystack, "%s does not carry %r%s" % (where, needle, (": " + msg) if msg else ""))

    def assertNotQuoted(self, needle, haystack, where, msg=""):
        self.assertFalse(needle in haystack, "%s still carries %r%s" % (where, needle, (": " + msg) if msg else ""))


class TheHeldMailClauseStatesTheRuleAndCitesIt(_Pins):
    """The clause names the one statement and enumerates nothing the statement owns."""

    def test_the_clause_cites_the_statement_by_name(self):
        clause = _clause()
        self.assertQuoted("`%s`" % STATEMENT, clause, DOC,
                          "the readers' rule is stated once in the kernel and the reference cites it, as every reader does")
        self.assertQuoted("statement of the states a reader of a store meets", clause, DOC)

    def test_the_citation_names_a_function_the_kernel_defines(self):
        # read as text, not loaded: a rename of the statement's home reddens here before the reference goes stale
        self.assertQuoted("def %s(" % STATEMENT, KERNEL, "kernel/kernel.py",
                          "the reference cites a function by name; the name must exist")

    def test_the_clause_enumerates_no_move_aside_shape(self):
        clause = _clause()
        self.assertNotQuoted("not an object, no message id", clause, DOC,
                             "the shapes the kernel moves aside are the code's statement to list; a list here went stale "
                             "on the next shape added")
        self.assertIsNone(re.search(r"parse or take \(", clause),
                          "%s opens a parenthetical after 'parse or take': an enumeration of the move-aside shapes" % DOC)
        self.assertQuoted("listed in that statement, not here", clause, DOC, "the clause points at the statement for the shapes")

    def test_the_read_fault_state_is_qualified_as_the_statement_qualifies_it(self):
        clause = _clause()
        self.assertQuoted("a stat or read fault on bytes that exist", clause, DOC,
                          "a bare 'cannot read' is what the dangling link falsifies; the state is a fault on bytes that exist")
        self.assertQuoted("never reported absent", clause, DOC)
        self.assertNotQuoted("skips and leaves in place a record it cannot read", clause, DOC,
                             "the unqualified clause the link with nothing behind it falsifies")

    def test_the_link_with_nothing_behind_it_is_named_as_the_exception(self):
        clause = _clause()
        # sentences split on a period followed by a space, so the `.json` in the link's name splits nothing
        sentences = [t for t in re.split(r"(?<=\.) ", clause) if "link with nothing behind it" in t]
        self.assertTrue(sentences, "%s does not name the link with nothing behind it" % DOC)
        self.assertIn("exception", sentences[0], "the link is named as the exception to the never-rename side, in its own sentence")
        self.assertQuoted("moves the link itself aside by its own name", clause, DOC)
        self.assertQuoted("the bus skips it", clause, DOC, "the bus renames nothing, the link included")

    def test_a_store_none_of_whose_records_could_be_served_is_refused_one_record_included(self):
        clause = _clause()
        self.assertQuoted("one record alone included", clause, DOC,
                          "a lone unreadable record had answered nothing held; the store is refused whatever the count")
        self.assertQuoted("`GET /quarantine` answers 503", clause, DOC)
        self.assertQuoted("sees a fault row", clause, DOC, "the viewing machine sees the holder's fault, not a vanished section")

    def test_a_type_wrong_at_keeps_its_card_at_the_builds_time(self):
        clause = _clause()
        self.assertQuoted("an `at` that is not an integer gives the card the build's time", clause, DOC,
                          "a field's type never moves a record aside; the card takes the build's clock")
        self.assertQuoted("the bus sorts such a record as the oldest", clause, DOC)


if __name__ == "__main__":
    unittest.main()
