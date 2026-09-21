"""The round-label rule, held once: which spellings are a numbered-round mention, whom each credits, and what the rule refuses (the
author's pass 11 on PR 857, 2026-09-21: the maintainer's ruling of that day on the three per-branch guards, and the reviewer's
further ruling of the same day that the rule keys on MISATTRIBUTION, not on the absence of a qualifier).

THE CONVENTION. A reviewed branch's comments, docstrings and messages meet two numberings. The REVIEWER's rounds (the reviewer is
whom this project's PR bodies call the maintainer: one party under two names) are the rulings filed on the PR; the AUTHOR's passes
are the build-and-verify passes between them, mapped from the pipeline's commit labels by the PR body's convention paragraph. Rounds
belong to the reviewer and the author's work between them is a pass. So a numbered round is a credit to the reviewer who held it,
and it is MISATTRIBUTED when it names a round that reviewer never held (an author's pass labelled a round, or a round not yet held:
a number outside the caller's set) or when it credits the round to the author ("the author's round N", "the author's review round
N"); a numbered pass is the author's, and it is misattributed when it is credited to the reviewer or the maintainer ("the reviewer's
pass N", "the maintainer's pass N"). A round of another review (an earlier cut's) is named by that review and its date, with no
number. Three branches each wrote a guard for this convention, and the three disagreed on the spellings they read and on what
credited one, so the RULE lives here once and each branch's guard is a caller: it derives its own POPULATION (the lines it vetted,
which is why a guard is deleted at landing, its job done) and supplies its own ROUNDS (the rulings filed on its PR, a constant of
its tree) and its own AUTHOR FORM (how its PR body spells the author's pass). This module holds none of those: no population, no
git, no skip, no round set of any PR, and it reads no file, no environment and no path (`import re` alone; the pin is
tests/test_review_round_labels_rule.py, by resolution over this source). A caller whose derivation is unavailable skips with its
reason and never substitutes a population (the maintainer's rule of 2026-09-21, from PR 860's guard).

THE FORM SPACE. forms() reads the WHOLE text, so a mention wrapped across a line break (the qualifier ending one line and the
number starting the next, a comment marker between) is one mention, reported at the line its number sits on. Between the word
and the number the separator may be nothing, spaces, hyphens, a newline, a comment marker (`#`, `//`, and after a newline the
`*` of a block comment's continuation line) or a hash; the plural takes a list or a range ("rounds N and M", "rounds N, M",
"rounds N to M", "rounds N-M", an en dash, a slash, "through": a list's every number judged, and a range EXPANDED, N through M
each judged, so a caller's set need not be contiguous); the singular takes the same continuations but the comma, which is the
plural's alone, so a count after a singular ("round N, M findings") is a continuation the list did not consume and is refused as
one. A DATE after the number, or after the list, is part of the form (DATE: a run of punctuation and spaces, no letter, and then
YYYY-MM-DD, so "Review round N, YYYY-MM-DD", "round N (YYYY-MM-DD", "round N), YYYY-MM-DD" and the date straight after the number
with a space or a comma are correct prose, not a further number the list did not consume; the list never reads a date's year as a
number of its own); a further number after the date is refused as one the form did not consume. Every spelling of the word is
CLASSIFIED: a numbered form by its plural and its separator (FORM_CLASSES, one red and one green probe per class in the pin); an
unnumbered one (Python's round(), the keyword-argument spelling "rounds=40", "a typing round", "the two-round convergence bound",
"in its second round", "the round's own", "around", a word between the word and a number as in "a round of 3 drives": the rule
reads spellings of the word, not sentences, and a bare referential form carries no number and so no credit) not read; and a form
the classifier cannot place REFUSED, keyed on what it did not resolve: a number glued to a letter or an underscore ("round Nb", the
lettered pass), a further number after a run the list did not consume that is not a date ("rounds N; M", "round N, M"), a plural
that names one number ("rounds N"), a range that does not ascend ("rounds M-N" with M past N), and punctuation or markup between
the word and a number ("round: N", "round (N)", "round **N**", "round `N`"), the one exemption being the keyword-argument
spelling, the word glued to `=`. An unresolvable form refuses with its reason and never passes: widening the credit is not
widening what passes unresolved.

THE CREDIT. A numbered round is credited to the reviewer when the qualifier before the word names that party, "the reviewer's
round N" or "the maintainer's round N" (CREDIT: one party under two names; the apostrophe ASCII or typographic; "review" may stand
between the qualifier and the word; the qualifier's gaps take the same wrap as the separator; a list or a range, every number
judged), and it is credited to the reviewer BY DEFAULT when no qualifier names a party ("review round N", "Review round N", a bare
"round N", "rounds N and M", "the round-N head"): rounds belong to the reviewer and the author's work between them is a pass, so
an unqualified round is the reviewer's by that convention, a default with this stated reason (DEFAULT), not a guess; credit()
returns the reason beside the party, so a caller can tell the default from an explicit qualifier, and the refusal of an
unqualified round outside the caller's set states the default it was read under. "the author's round N" credits a round to the
author (AUTHOR) and is refused. offences() returns every misattribution with its reason and the line it sits on: a round numbered
outside the caller's set (UNRULED: no ruling exists for it, an author's pass labelled a round or a round not yet held; the reason
names the caller's set and its author form so the writer knows what to write, and the date form for another review's round), a
round credited to the author (AUTHORS_ROUND), a numbered pass credited to the reviewer or the maintainer (PASS, WRONG_PARTY: the
reason names the wrong party), and every form the classifier cannot place (UNCLASSIFIABLE). No message of this module spells a
numbered-round form of its own (the unclassifiable refusal quotes the text it refused, and that quotation is the writer's), so a
quoted refusal reads clean, and no digit follows the word in this docstring: a caller that censuses this module's text reads it
clean."""
import re

# the word, then what follows it: a separator (nothing, spaces, hyphens, a newline, a comment marker, a hash; after a newline
# the `*` of a block comment's continuation line), a number, an optional list or range continuation (each number judged; the
# comma is the plural's alone, since a singular followed by a comma and a number is a count and the list would bind the count as
# a round; a number of the continuation is never a date's year, which the DATE form consumes), and the character after the last
# digit (a letter or an underscore glued to it makes the form unclassifiable)
WORD = re.compile(r"\bround(?P<plural>s?)", re.I)
_WRAP = r"(?:\n[ \t]*\*)?"
_SEP = r"[-\s#/]*" + _WRAP + r"[-\s#/]*"
_NUM = r"\d+(?!\d|-\d\d-\d\d)"
_NUMBERED = r"(?P<sep>" + _SEP + r")(?P<num>\d+)(?P<list>(?:\s*(?:%s)\s*#?" + _NUM + r")*)(?P<tail>[A-Za-z_]?)"
_RANGE = r"to|through|thru|[-–]"
_LIST = r"and|or|&|/"
NUMBERED = {False: re.compile(_NUMBERED % (_RANGE + "|" + _LIST)), True: re.compile(_NUMBERED % (_RANGE + "|" + _LIST + "|,"))}
CONTINUATION_TOKEN = re.compile(r"\s*(?P<how>%s|%s|,)\s*#?(?P<num>\d+)" % (_RANGE, _LIST))
RANGE_WORDS = re.compile(r"^(?:%s)$" % _RANGE)
# after the last digit the form consumed: a run of punctuation and spaces (no letter, no newline) and then a digit is a
# continuation the list did not resolve; after the word with no number read: the same run and then a digit is punctuation or
# markup between the word and a number, unclassifiable unless the run is the keyword-argument spelling's `=`
CONTINUATION = re.compile(r"[^\w\n]{1,6}\d")
# a date after the number or the list: the same run and then YYYY-MM-DD, part of the form (a further number after it is refused)
DATE = re.compile(r"[^\w\n]{1,6}\d{4}-\d{2}-\d{2}(?!\d)")
GAP = r"[\s#/]*" + _WRAP + r"[\s#/]*"
# the qualifier before the word, its gaps taking the same wrap as the separator, "review" allowed between it and the word: the
# reviewer's (or the maintainer's: one party under two names) is the explicit credit; the author's is a round credited to the author
_QUALIFIED = r"\bthe" + GAP + r"%s['’]s" + GAP + r"(?:review" + GAP + r")?(?P<word>round)"
CREDIT = re.compile(_QUALIFIED % r"(?:maintainer|reviewer)", re.I)
AUTHOR = re.compile(_QUALIFIED % r"author", re.I)
# a pass credited to the reviewer or the maintainer: the qualifier, then the word pass with a number after it (NUMBERED, the same
# separators and continuations); an unnumbered pass ("the maintainer's pass over the tree") is not read
PASS = re.compile(r"\bthe" + GAP + r"(?P<who>maintainer|reviewer)['’]s" + GAP + r"pass(?P<plural>es)?", re.I)
# the numbered form classes, by (plural, separator kind), each with the separator its probes are spelled with; a caller requires
# every class its population uses to be one of these, and the pin holds a red and a green probe per class
FORM_CLASSES = {(False, "none"): "", (False, "space"): " ", (False, "hyphen"): "-", (False, "hash"): " #",
                (False, "wrap"): "\n    # ", (False, "star"): "\n * ", (True, "space"): " ", (True, "wrap"): "\n", (True, "star"): "\n * "}
# the reasons; none spells a numbered-round form of its own (the writer's quoted text aside)
DEFAULT = ("rounds belong to the reviewer and the author's work between them is a pass, so an unqualified round is the reviewer's by that "
           "convention: a default with this stated reason, not a guess")
UNCLASSIFIABLE = "a form the rule cannot classify (%s): write \"the reviewer's round N\" for a round that reviewer held, or the author's pass"
UNRULED = ("no ruling exists for a round numbered %s: an author's pass labelled a round, or a round not yet held; the rulings the caller holds "
           "are numbered %s; write %s for the author's own work, \"the reviewer's round N\" for a round that reviewer held, or another review's "
           "round by that review and its date with no number%s")
BY_DEFAULT = " (this form names no party, so it is read as the reviewer's: %s)"
AUTHORS_ROUND = ("a round credited to the author: a round is the reviewer's ruling and the author's work between rounds is a pass, so write %s "
                 "for the author's own work, or \"the reviewer's round N\" for a round that reviewer held")
WRONG_PARTY = ("a pass credited to the %s: a pass is the author's work and the %s's work on a PR is a round, so write %s for the author's own "
               "work, or \"the reviewer's round N\" for a round that reviewer held")
AUTHOR_FORM = "\"pass P\""


def sep_kind(sep):
    """The class of a separator: a block comment's continuation marker after a newline makes it a star, another newline a wrap,
    whatever else either holds; a comment marker or a hash a hash, a hyphen a hyphen, spaces a space, nothing none."""
    if "*" in sep:
        return "star"
    if "\n" in sep:
        return "wrap"
    if "#" in sep or "/" in sep:
        return "hash"
    if "-" in sep:
        return "hyphen"
    return "space" if sep else "none"


def _numbers(n):
    """The numbers a NUMBERED match names, a list's each and a range's every number from its first to its last, or None with
    the reason when a range does not ascend."""
    nums = [int(n.group("num"))]
    for t in CONTINUATION_TOKEN.finditer(n.group("list")):
        x = int(t.group("num"))
        if RANGE_WORDS.match(t.group("how")):
            if x <= nums[-1]:
                return None, "a range that does not ascend (%d %s %d)" % (nums[-1], t.group("how"), x)
            nums += list(range(nums[-1] + 1, x + 1))
        else:
            nums.append(x)
    return nums, None


def dated(text, n):
    """Where the form ends: after the DATE form when one follows the numbers of `n` (a match of NUMBERED), else at the list's end."""
    d = DATE.match(text, n.end("list"))
    return n.end("list") if d is None else d.end()


def classify(text, w):
    """One occurrence `w` of the word in `text` (a match of WORD): (kind, the match of NUMBERED or None, the numbers, why
    unclassifiable). Kind is "numbered" (every number of the list or range read; a date after them consumed), "unnumbered" (no
    number follows: not read) or "unclassifiable" (a number the rule cannot place, refused with the reason)."""
    n = NUMBERED[bool(w.group("plural"))].match(text, w.end())
    if n is None:
        gap = CONTINUATION.match(text, w.end())
        if gap is not None and gap.group()[:-1] != "=":
            return "unclassifiable", None, [], "punctuation or markup between the word and a number: %r" % text[w.start():gap.end()]
        return "unnumbered", None, [], None
    nums, why = _numbers(n)
    if nums is None:
        return "unclassifiable", n, [], "%s: %r" % (why, text[w.start():n.end("list")])
    if n.group("tail"):
        return "unclassifiable", n, nums, "a number glued to a letter or an underscore: %r" % text[w.start():n.end()]
    more = CONTINUATION.match(text, dated(text, n))
    if more is not None:
        return "unclassifiable", n, nums, "a further number after a run the list did not consume, and not a date: %r" % text[w.start():more.end()]
    if w.group("plural") and len(nums) == 1:
        return "unclassifiable", n, nums, "a plural that names one number: %r" % text[w.start():n.end("list")]
    return "numbered", n, nums, None


def forms(text):
    """Every occurrence of the word in `text`, classified: (line, spelled, kind, numbers) with kind "numbered" (the numbers of
    the mention, a list's each and a range's every number; the spelling runs from the word to the last number, a date after it
    consumed but not spelled), "unnumbered" (no number follows: not read) or "unclassifiable" (a number the rule cannot place:
    refused, since it cannot say whether the form is a credit or which rounds it names)."""
    out = []
    for w in WORD.finditer(text):
        kind, n, nums, _ = classify(text, w)
        if kind == "unnumbered" or n is None:
            out.append((text.count("\n", 0, w.start()) + 1, text[w.start():w.end()], kind, []))
        elif kind == "unclassifiable":
            out.append((text.count("\n", 0, n.start("num")) + 1, text[w.start():n.end()], kind, []))
        else:
            out.append((text.count("\n", 0, n.start("num")) + 1, text[w.start():n.end("list")], kind, nums))
    return out


def form_class(spelled):
    """The (plural, separator kind) class of a numbered form's spelling, from the word to its first digit."""
    w = WORD.match(spelled)
    n = NUMBERED[bool(w.group("plural"))].match(spelled, w.end())
    return (bool(w.group("plural")), sep_kind(n.group("sep")))


def mentions(text):
    """The numbered forms of `text`, as spelled."""
    return [spelled for _, spelled, kind, _ in forms(text) if kind == "numbered"]


def qualifiers(text):
    """{the word's offset: the party the qualifier before it names} for every qualified form of `text`: "reviewer" for "the
    reviewer's" or "the maintainer's" (one party under two names), "author" for "the author's"."""
    out = {m.start("word"): "reviewer" for m in CREDIT.finditer(text)}
    out.update({m.start("word"): "author" for m in AUTHOR.finditer(text)})
    return out


def credit(text, w, qualified=None):
    """(party, why) for the form at `w` (a match of WORD): the party the qualifier before it names, why None; or, for an unqualified
    form, ("reviewer", DEFAULT): the default, with its stated reason. `qualified` is qualifiers(text), passed by a caller that
    computed it once over the whole text."""
    party = (qualifiers(text) if qualified is None else qualified).get(w.start())
    return (party, None) if party else ("reviewer", DEFAULT)


def credits(text):
    """(line, spelled, party, why) for every numbered form of `text`: the party it credits, and for an unqualified form the default's
    stated reason (None for an explicit qualifier)."""
    qualified = qualifiers(text)
    out = []
    for w in WORD.finditer(text):
        kind, n, _, _ = classify(text, w)
        if kind == "numbered":
            party, why = credit(text, w, qualified)
            out.append((text.count("\n", 0, n.start("num")) + 1, text[w.start():n.end("list")], party, why))
    return out


def offences(text, rounds, filename="", author=AUTHOR_FORM):
    """(filename, line number, the mention, why) for every MISATTRIBUTION in `text`: a numbered round that names a round outside
    `rounds` (the caller's set of the rounds the reviewer held on its PR; an unqualified round is the reviewer's by default, and the
    reason says so), a round credited to the author, a numbered pass credited to the reviewer or the maintainer, and every form the
    classifier cannot place. `author` is the caller's spelling of the author's own work, named in each reason so the writer knows
    what to write. Read over the whole text: a credit split by a line break is one credit; the offences come in text order."""
    qualified = qualifiers(text)
    out = []
    for w in WORD.finditer(text):
        kind, n, nums, why = classify(text, w)
        if kind == "unnumbered":
            continue
        at = w.start() if n is None else n.start("num")
        line = text.count("\n", 0, at) + 1
        if kind == "unclassifiable":
            out.append((at, filename, line, text[w.start():n.end()] if n is not None else text[w.start():w.end()], UNCLASSIFIABLE % why))
            continue
        spelled = text[w.start():n.end("list")]
        party, how = credit(text, w, qualified)
        if party == "author":
            out.append((at, filename, line, spelled, AUTHORS_ROUND % author))
            continue
        unruled = [x for x in nums if x not in rounds]
        if unruled:
            out.append((at, filename, line, spelled, UNRULED % (", ".join(str(x) for x in unruled), ", ".join(str(x) for x in sorted(rounds)), author,
                                                            "" if how is None else BY_DEFAULT % how)))
    for p in PASS.finditer(text):
        n = NUMBERED[bool(p.group("plural"))].match(text, p.end())
        if n is not None:
            who = p.group("who").lower()
            out.append((n.start("num"), filename, text.count("\n", 0, n.start("num")) + 1, text[p.start():n.end("list")], WRONG_PARTY % (who, who, author)))
    return [o[1:] for o in sorted(out)]
