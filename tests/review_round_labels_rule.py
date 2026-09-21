"""The round-label rule, held once: which spellings are a numbered-round mention, and what credits one (the author's pass 11 on
PR 857, 2026-09-21, the maintainer's ruling of that day on the three per-branch guards).

A reviewed branch's comments, docstrings and messages meet two numberings. The MAINTAINER's rounds are the rulings the reviewer
filed on the PR; the AUTHOR's passes are the build-and-verify passes between them, mapped from the pipeline's commit labels by
the PR body's convention paragraph. A numbered round is a credit to the reviewer who held it, so in a branch's own lines it is
written "the maintainer's round N" with N a round that reviewer held on that PR; the author's own work is a pass, spelled as the
PR body maps it; a round of another review (an earlier cut's) is named by that review and its date, with no number. Three
branches each wrote a guard for this convention, and the three disagreed on the spellings they read and on what credited one,
so the RULE lives here once and each branch's guard is a caller: it derives its own POPULATION (the lines it vetted, which is
why a guard is deleted at landing, its job done) and supplies its own ROUNDS (the rulings filed on its PR, a constant of its
tree) and its own AUTHOR FORM (how its PR body spells the author's pass). This module holds none of those: no population, no
git, no skip, no round set of any PR, and it reads no file, no environment and no path (`import re` alone; the pin is
tests/test_review_round_labels_rule.py, by resolution over this source). A caller whose derivation is unavailable skips with
its reason and never substitutes a population (the maintainer's rule of 2026-09-21, from PR 860's guard).

THE FORM SPACE. forms() reads the WHOLE text, so a mention wrapped across a line break (the qualifier ending one line and the
number starting the next, a comment marker between) is one mention, reported at the line its number sits on. Between the word
and the number the separator may be nothing, spaces, hyphens, a newline, a comment marker (`#`, `//`, and after a newline the
`*` of a block comment's continuation line) or a hash; the plural takes a list or a range ("rounds N and M", "rounds N, M",
"rounds N to M", "rounds N-M", an en dash, a slash, "through": a list's every number judged, and a range EXPANDED, N through M
each judged, so a caller's set need not be contiguous); the singular takes the same continuations but the comma, which is the
plural's alone, so a count after a singular ("round N, M findings") is a continuation the list did not consume and is refused as
one. Every spelling of the word is CLASSIFIED: a numbered form by its plural and its separator (FORM_CLASSES, one red and one
green probe per class in the pin); an unnumbered one (Python's round(), the keyword-argument spelling "rounds=40", "a typing
round", "the two-round convergence bound", "in its second round", "the round's own", "around", a word between the word and a
number as in "a round of 3 drives": the rule reads spellings of the word, not sentences, and a bare referential form carries no
number and so no credit) not read; and a form the classifier cannot place REFUSED, keyed on what it did not resolve: a number
glued to a letter or an underscore ("round Nb", the lettered pass), a further number after a run the list did not consume
("rounds N; M", "round N, M"), a plural that names one number ("rounds N"), a range that does not ascend ("rounds M-N" with M
past N), and punctuation or markup between the word and a number ("round: N", "round (N)", "round **N**", "round `N`"), the one
exemption being the keyword-argument spelling, the word glued to `=`. The qualifier's apostrophe may be typographic (CREDIT
reads either). THE CREDIT is "the maintainer's round N" (or "the maintainer's rounds N and M", a list or a range, every
number judged), the qualifier's gaps taking the same wrap as the separator; nothing else credits: not "review round N", not
"the reviewer's round N", not an artifact after a bare round ("the round-N fixlist"), so a branch that wrote those rewords them
to the maintainer's form or to the author's pass. offences() returns every refusal with its reason and the line it sits on; the
reason for an uncredited round names the caller's author form and the date form for another review, so the writer knows what
to write, and no message of this module spells a numbered-round form of its own (the unclassifiable refusal quotes the text it
refused, and that quotation is the writer's), so a quoted refusal reads clean. No digit follows the word in this docstring: a
caller that censuses this module's text reads it clean."""
import re

# the word, then what follows it: a separator (nothing, spaces, hyphens, a newline, a comment marker, a hash; after a newline
# the `*` of a block comment's continuation line), a number, an optional list or range continuation (each number judged; the
# comma is the plural's alone, since a singular followed by a comma and a number is a count and the list would bind the count as
# a round), and the character after the last digit (a letter or an underscore glued to it makes the form unclassifiable)
WORD = re.compile(r"\bround(?P<plural>s?)", re.I)
_WRAP = r"(?:\n[ \t]*\*)?"
_SEP = r"[-\s#/]*" + _WRAP + r"[-\s#/]*"
_NUMBERED = r"(?P<sep>" + _SEP + r")(?P<num>\d+)(?P<list>(?:\s*(?:%s)\s*#?\d+)*)(?P<tail>[A-Za-z_]?)"
_RANGE = r"to|through|thru|[-–]"
_LIST = r"and|or|&|/"
NUMBERED = {False: re.compile(_NUMBERED % (_RANGE + "|" + _LIST)), True: re.compile(_NUMBERED % (_RANGE + "|" + _LIST + "|,"))}
CONTINUATION_TOKEN = re.compile(r"\s*(?P<how>%s|%s|,)\s*#?(?P<num>\d+)" % (_RANGE, _LIST))
RANGE_WORDS = re.compile(r"^(?:%s)$" % _RANGE)
# after the last digit the list consumed: a run of punctuation and spaces (no letter, no newline) and then a digit is a
# continuation the list did not resolve; after the word with no number read: the same run and then a digit is punctuation or
# markup between the word and a number, unclassifiable unless the run is the keyword-argument spelling's `=`
CONTINUATION = re.compile(r"[^\w\n]{1,6}\d")
GAP = r"[\s#/]*" + _WRAP + r"[\s#/]*"
CREDIT = re.compile(r"\bthe" + GAP + r"maintainer['’]s" + GAP + r"round(?P<plural>s?)(?P<sep>" + _SEP + r")(?P<num>\d+)", re.I)
# the numbered form classes, by (plural, separator kind), each with the separator its probes are spelled with; a caller requires
# every class its population uses to be one of these, and the pin holds a red and a green probe per class
FORM_CLASSES = {(False, "none"): "", (False, "space"): " ", (False, "hyphen"): "-", (False, "hash"): " #",
                (False, "wrap"): "\n    # ", (False, "star"): "\n * ", (True, "space"): " ", (True, "wrap"): "\n", (True, "star"): "\n * "}
UNCLASSIFIABLE = "a form the rule cannot classify (%s): write \"the maintainer's round N\" or the author's pass"
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


def classify(text, w):
    """One occurrence `w` of the word in `text` (a match of WORD): (kind, the match of NUMBERED or None, the numbers, why
    unclassifiable). Kind is "numbered" (every number of the list or range read), "unnumbered" (no number follows: not read) or
    "unclassifiable" (a number the rule cannot place, refused with the reason)."""
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
    if CONTINUATION.match(text, n.end("list")) is not None:
        return "unclassifiable", n, nums, "a further number after a run the list did not consume: %r" % text[w.start():CONTINUATION.match(text, n.end("list")).end()]
    if w.group("plural") and len(nums) == 1:
        return "unclassifiable", n, nums, "a plural that names one number: %r" % text[w.start():n.end("list")]
    return "numbered", n, nums, None


def forms(text):
    """Every occurrence of the word in `text`, classified: (line, spelled, kind, numbers) with kind "numbered" (the numbers of
    the mention, a list's each and a range's every number), "unnumbered" (no number follows: not read) or "unclassifiable" (a
    number the rule cannot place: refused, since it cannot say whether the form is a credit or which rounds it names)."""
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


def offences(text, rounds, filename="", author=AUTHOR_FORM):
    """(filename, line number, the mention, why) for every numbered round in `text` that is not "the maintainer's round N" (or a
    credited list or range) with every N in `rounds`, the caller's set of the rounds the maintainer held on its PR, and for every
    form the classifier cannot place. `author` is the caller's spelling of the author's own work, named in the reason for an
    uncredited round. Read over the whole text: a credit split by a line break is one credit."""
    credited = {m.start("num") for m in CREDIT.finditer(text)}
    out = []
    for w in WORD.finditer(text):
        kind, n, nums, why = classify(text, w)
        if kind == "unnumbered":
            continue
        line = text.count("\n", 0, w.start() if n is None else n.start("num")) + 1
        if kind == "unclassifiable":
            out.append((filename, line, text[w.start():n.end()] if n is not None else text[w.start():w.end()], UNCLASSIFIABLE % why))
            continue
        spelled = text[w.start():n.end("list")]
        if n.start("num") not in credited:
            out.append((filename, line, spelled, "a numbered round is a credit to the maintainer: write \"the maintainer's round N\" for a round "
                                                 "that reviewer held, %s for the author's own work, or another review's round by that review "
                                                 "and its date with no number" % author))
        else:
            unruled = [x for x in nums if x not in rounds]
            if unruled:
                out.append((filename, line, spelled, "no ruling exists for a maintainer round numbered %s; the rulings the caller holds are numbered %s"
                            % (", ".join(str(x) for x in unruled), ", ".join(str(x) for x in sorted(rounds)))))
    return out
