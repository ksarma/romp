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
included), and gives an `at` the reader cannot read as a whole number, or that is empty or zero, the build's time
instead of a move aside.
The third review round (2026-09-20) added three properties: the clause says how a record left unread beside
records that were read is reported on every reader of the held wire (the route, the summary peers see and the
viewing panel), so the never-reported-absent sentence is true of the mixed case and not only of the refused
store; its `at` sentence says what the reader keys on (a value it cannot read as a whole number, or that is
empty or zero, takes the build's time; any other value it reads as a whole number is read as its value by both
readers) instead of the false predicate `not an integer`, which a string of digits or a decimal number
falsified; and its rename-back advice is the error center's for the record it names, carrying the road for an
id the bus cannot decide, instead of the unconditional rename back or delete that looped on such a file. The
fourth review round (2026-09-20) widened the `at` sentence to the scope the third round's ruling had stated: a
zero or empty `at` (0, 0.0, false, an empty string, none at all) takes the build's time on the kernel and the
oldest place on the bus, the same as a value the reader cannot read, where the third round's sentence had read
every value that reads as a whole number as its value; and the pin on that sentence keys on its properties (the
two classes named before the build's time, the bus's oldest place, the read-as-its-value class qualified as any
other value) rather than on its words, since the quoted literals it had carried went red on any rewording.

Text only: this module reads docs/reference.md and kernel/kernel.py as text and loads no romp code, so it
needs no hermetic-state preamble. Over a git archive of the reviewed head (085e08deb) it is red at the phrase
pins the clause exists for (the citation absent, the enumeration present), never on a symbol or a signature;
the three round-3 pins are red over a git archive of f418f75e9 at their own assertions (the mixed-case sentence
absent, the `not an integer` predicate present, the unconditional rename-back present); the re-keyed `at` pin of
the fourth round is red over a git archive of 806804242 at its empty-or-zero assertion (that head's sentence names
one class before the build's time) and green here.
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
    """The clause names the one statement and enumerates nothing the statement owns; since the third round it also says
    how the mixed store is reported, keys its `at` sentence on what the reader can read, and gives the rename-back
    advice by the record's class (the module docstring says which archive each pin is red over)."""

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
        # the property, not the spelling (the fourth round re-keyed this pin: its quoted literals went red on any
        # rewording, and the sentence they quoted gave its value to EVERY `at` the reader reads as a whole number,
        # false for zero, which reads as a whole number and takes the build's time on the kernel and the oldest place
        # on the bus, as an empty one does). The sentence keyed on what the reader can read as a whole number names
        # TWO classes before the disposition they share, a value the reader cannot read as a whole number and a value
        # that is empty or zero, both taking the build's time; names the bus's oldest place for such a record; and
        # qualifies the read-as-its-value class as any OTHER value the reader reads as a whole number. In doc voice:
        # never `not an integer` (a string of digits and a decimal number are not integers and both readers read them
        # as their value) and never the Python builtin's name. Never keyed on `reads as zero` either: the string "0"
        # reads as zero and IS read as its value by both readers.
        clause = _clause()
        self.assertNotQuoted("`at` that is not an integer", clause, DOC,
                             "the false predicate: a digit string and a float are not integers and are read as their value")
        sentences = [s for s in re.split(r"(?<=\.) ", clause) if "whole number" in s]
        self.assertTrue(sentences, "%s no longer keys the `at` handling on what the reader can read as a whole number" % DOC)
        s = sentences[0]
        m = re.search(r"cannot read as a whole number\b(.*?)the build's time", s)
        self.assertIsNotNone(m, "%s: a value the reader cannot read as a whole number takes the build's time" % DOC)
        self.assertRegex(m.group(1), r"\bempty\b.*\bzero\b|\bzero\b.*\bempty\b",
                         "%s: a value written empty or zero takes the build's time too, named beside the value the reader "
                         "cannot read (0, 0.0, false, an empty string and an absent `at` give the kernel's card the build's "
                         "clock and the bus's sort the oldest place, exactly as a value the reader cannot read does); the "
                         "third round's sentence gave every value that reads as a whole number its value" % DOC)
        self.assertQuoted("the oldest", s, DOC, "the bus's place for such a record is named beside the kernel's")
        self.assertIsNotNone(re.search(r"\bany other\b[^.;]*?\breads as a whole number\b[^.;]*?\bread as its value by both readers", s),
                             "%s: the read-as-its-value class is qualified as any OTHER value the reader reads as a whole "
                             "number, so zero, which reads as one, is not given its value" % DOC)
        self.assertNotQuoted("int()", clause, DOC, "doc voice: the reader's rule, not the builtin's name")

    def test_a_record_left_unread_beside_served_ones_is_named_on_every_reader_of_the_wire(self):
        # the property: the clause names the unread beside what was served on the route, the summary and the panel,
        # so `never reported absent` holds of the mixed store and not only of the refused one (the third round's
        # correctness-2: until it, a record left unread beside served ones was dropped from GET /quarantine's
        # `held` under a 200 and from the summary rows with nothing on the wire saying it existed)
        clause = _clause()
        self.assertQuoted("never reported absent", clause, DOC)
        sentences = [s for s in re.split(r"(?<=\.) ", clause) if "left unread" in s]
        self.assertTrue(sentences, "%s does not say how a record left unread beside records that were read is reported" % DOC)
        s = sentences[0]
        for needle, why in (("`GET /quarantine`", "the route lists the unread beside `held`"),
                            ("`held`", "beside what was served, never in place of it"),
                            ("summary peers see", "the summary carries a marker beside the message rows"),
                            ("Held for approval elsewhere", "the viewing panel shows the partial listing"),
                            ("could not be read", "the panel's line names how many could not be read")):
            self.assertQuoted(needle, s, DOC, why)
        self.assertQuoted("beside the count of messages held", s, DOC, "the unread are never counted as messages")

    def test_the_rename_back_advice_is_the_error_centers_for_the_record_it_names(self):
        # the property: the advice is qualified by the record's class and carries the id road, never an unconditional
        # `until you rename the file back ... or delete it` (the second round stopped giving that advice for an aside
        # whose de-suffixed stem the bus cannot decide, since renaming such a file back has it refused again; the
        # clause's own rule is that the shapes are listed in the statement, so both classes ride one sentence)
        clause = _clause()
        self.assertIsNone(re.search(r"until you rename the file back", clause),
                          "%s gives the unconditional rename-back advice; the advice is the error center's, by class" % DOC)
        sentences = [s for s in re.split(r"(?<=\.) ", clause) if "`.corrupt-` suffix to try the record again" in s]
        self.assertTrue(sentences, "%s no longer carries the rename-back road for a torn record" % DOC)
        s = sentences[0]
        self.assertQuoted("carries the advice for the record it names", s, DOC, "the advice is the error center's, for that record")
        self.assertQuoted("the bus cannot decide", s, DOC, "the id road: an aside from a name the bus cannot decide")
        self.assertQuoted("matching message id", s, DOC, "such a file needs a decidable name and a matching message id")


if __name__ == "__main__":
    unittest.main()
