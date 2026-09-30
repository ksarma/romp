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

THE STOPPING RULE, quoted verbatim as the coordinator's ruling of 2026-09-30 on PR 857's review orders (the docstring it names is
this one): "a round-label reader finding counts only if (a) a spelling the docstring states it reads or refuses passes silently or
is read in part, (b) a sentence claims more than the stated reach, or (c) a built refusal or read has no probe red under its
mutant. A spelling the docstring does not state is the stated outside, not a finding."

THE FORM SPACE. The reader reads in one direction, READ (the coordinator's ruling of 2026-09-29 on PR 857's review), over a STATED
REACH (the ruling of 2026-09-30, which restated that ruling's refusal of any other spelling of a numbered round to this reach):
each spelling this docstring states the reader reads is read into its values (digits, digit ordinals and the words of its
tables), each spelling it states the reader refuses is refused with its reason, and each unnumbered form it names passes unread;
a spelling this docstring does not state is the STATED OUTSIDE, on which the reader makes no claim, so it may be read in part or
pass silently (the connector words, the runs wider than the refusal runs, and an ordinal run or a number past the 400-character
look-back, named after the unnumbered forms below, are such).
forms() reads the WHOLE text, so a mention wrapped across a line break (the qualifier ending one line and the number starting the
next, a comment marker between) is one mention, reported at the line its first number sits on, and so is a list or a range
wrapped between two of its numbers (below). A number
is read in one of two places. AFTER the word: digits, or a CARDINAL word (CARDINALS, zero to nineteen; TENS, twenty to ninety; a
tens word joined by a hyphen to a word of UNITS, one to nine; any letter case; each read whole, so a longer word it begins is no
number word), the separator between the word and the number being nothing (before digits alone), spaces, hyphens, a newline, a
comment marker (`#`, `//`, and after a newline the `*` of a block comment's continuation line) or a hash. BEFORE the word: an
ORDINAL, digits with st, nd, rd or th or a word (ORDINALS, zeroth to nineteenth; ORDINAL_TENS, twentieth to ninetieth; a tens word
joined by a hyphen to a word of ORDINAL_UNITS, first to ninth), the separator between the ordinal and the word being one of the
same, but never nothing, and "review" allowed on either side of the ordinal. An ordinal is read whether or not a qualifier credits
it ("the maintainer's Nth round", "the author's Nth round", "in its Nth round"), and it is not read before another word the word
begins (glued to a letter, or to a hyphen and a letter, as in "a second round-trip"). Either place takes a list or a range, of
numbers after the word or of ordinals before it ("rounds N and M", "rounds N, M", "rounds N, M, and K" with a serial comma, "rounds
N to M", "rounds N-M", an en dash, a slash, "through", and "the Nth and Mth rounds" the same way): a list's every number judged,
and a range EXPANDED, N through M each judged, so a caller's set need not be contiguous. A list or a range reads across the WRAP a
comment line break puts between two of its numbers (the ruling of 2026-09-30), the wrap the separator takes: spaces, one
newline, then optional indentation and a comment marker (`#`, `//`, or a block comment's `*`), and spaces (a carriage return
before a newline counts as a space, so a CRLF line end reads as a newline), taken on either side of the list word, the range word
or the comma that joins the two, after the word and before it ("rounds N and" ending one comment line and "M found it" starting
the next is the list of N and M, and "the Nth and" then "Mth round" the same); a line break with
no list word, range word or comma beside it joins nothing ("round N" ending one line and "M tests" starting the next reads N
alone). A RANGE MARK, a hyphen or an en dash, that opens the next line, after its indentation and any comment marker, is a BULLET
and never the link that joins across the wrap, so after a first line that ends at the number it joins nothing in the same way
("round N" ending one comment line and "- M items" starting the next reads N alone, and "the Nth" then "- Mth round" reads M alone),
while a range mark that ends the first line joins ("round N -" ending one comment line and "M" starting the next is the range N to
M); between the word and its first number the separator still takes a hyphen after the line break, as stated above. The plural
reads a bare comma, and a comma
followed by a list word (the serial comma: ", and", ", or", ", &", ", /"). The singular takes the same continuations but the bare
comma and the serial comma: a count after a singular ("round N, M findings") is a continuation the list did not consume and is
refused as one, and the one comma the singular reads is a comma followed by "and", so "round N, and M" is read as the list of N and
M, while "round N, or M" is refused. No list or range reads "and/or", with or without a space on either side of its slash: a
number after it is refused as one the list did not consume ("round N and/or M", "round N and / or M", "the Nth and/or Mth
round"). Those refusals, of a further number after the list (or after the date, or the word of an ordinal form) and of a number
before an ordinal run, read the REFUSAL RUNS and nothing wider, each a run of punctuation and spaces: on one line, one to six
characters between the two numbers, or between the first number and a list word ("and", "or", "and/or") between them, and one to
three from that list word to the second number; and across the wrap when a LINK stands beside it, a comma, a list word ("and",
"or", "&", "/", "and/or") or a range mark (a hyphen, an en dash), where a slash that begins `//` or `/*` opens a comment and is no
link and no list word: either the link ends the first line, at most six characters after the number (at least one before a link
spelled in letters, "and", "or" or "and/or") and at most three after the link on its line (the spaces before the line break count
among the three, a carriage return with them, so a link followed by four or more spaces and then the break is a wider run), and the
next line holds the wrap, optionally a second link (a range mark may be that second link, since the link that ends the first line
has joined), at most three characters (at least one after a link spelled in letters) and the number ("round N," ending one comment
line and "M findings", "or M" or "- M findings" starting the next is refused, and so is "the Nth," then "Mth round"), or the first
line ends at the number, spaces aside, and the next holds the wrap, the link (never a range mark, which there is a bullet), at most
three characters (at least one after a link spelled in letters) and the number ("round N" then ", M findings"). So after a first
line that ends at the number, or at a sentence's end, a bullet on the next line joins nothing and refuses nothing ("round N" or
"round N." then "- M items"), and neither does a comment opener on the next line ("round N" then "/* M tests */"). A comment marker
with no line break before it is no wrap ("round N and // M" on one line holds four characters after the list word, a wider run).
The ordinal run is looked for within the 400 characters before the word (before()), and the number before an ordinal run within the
400 characters before that run (classify()). A number past a wider run, in either place, is the stated outside ("round N and/or"
then four spaces and "M" reads N alone, and so does "round N and // M"), and so is an ordinal run that starts more than 400
characters before the word, or a number that starts more than 400 characters before the ordinal run it would stand before. A
DATE after the number, after the list, or after the word of an ordinal form, is part of the form (DATE: a run of punctuation and
spaces, no letter, up to six characters, or the wrap beside a link spelled in punctuation, a comma, "&", "/", a hyphen or an en
dash, as the refusal runs take it but with no second link, a range mark opening the next line being a bullet there too, and then
YYYY-MM-DD, so "Review round N, YYYY-MM-DD", "round N (YYYY-MM-DD", "round N), YYYY-MM-DD" and the date straight after the number with
a space or a comma are correct prose, not a further number the list did not consume; the list never reads a date's year as a number of
its own; a list word spelled in letters, "and", "or" or "and/or", makes no DATE, on one line or as the link beside the wrap, so a year
after it, within the refusal runs, is a further number and refused, as in "round N and" ending one comment line and "YYYY-MM-DD"
starting the next); a further number after the date is refused as one the form did not consume.

Every spelling of the word is CLASSIFIED, over the numbers the reader knows: digits, digit ordinals and the words of its tables. A
numbered form is read, and classed by its plural and its separator (FORM_CLASSES, an ordinal form in classes of its own, one red and
one green probe per class in the pin, in digits and in words, the class with no separator in digits alone). An UNNUMBERED form has
no number the reader knows beside the word, and it is not read: after the word, no digit and no number word past the separator or
past a short run of punctuation, markup and spaces (up to six characters, on the word's line), and before it no ordinal past the
separator or past such a run. Those forms pass unread: Python's round(), the keyword-argument spelling "rounds=40",
"a typing round", "the round's own", "this round", "around", a COUNT before the word (a cardinal, in digits or a word: "in N
rounds", "the two-round convergence bound", which count rounds and name none), a word between the word and a number as in "a round
of 3 drives", a word other than "review" between an ordinal and the word as in "the Nth test round", a run of punctuation, markup
and spaces longer than six characters, or one across a line break, between the word and a number or between an ordinal and the word,
a longer word a number word begins or an ordinal ends ("round sevenfold", "a millisecond round"), the word glued to a letter,
another word before which no ordinal is read and after which no number is ("rounded", "roundsman", "round-trip"), and a number
spelled in a way the reader does not know, a Roman numeral among them, which no branch writes (the rule reads spellings of the word,
not sentences, and a bare referential form carries no number and so no credit). THE STATED OUTSIDE is every spelling this
docstring does not state (the ruling of 2026-09-30), and three kinds of it are named here, since the reader meets them beside a
number it reads: a CONNECTOR word between two numbers other than the list, range and run words the lists and the refusal runs
read ("then", "plus", "nor", "vs", "as well as", "up to", and a range word, "to", "through" or "thru", before a number the range
does not read, an ordinal after a cardinal or a cardinal before an ordinal run), or a joiner those words do not spell ("and-or",
"and|or"), which reads the number on the word's side of it and passes the other silently ("round N then M" reads N, "the Nth then
Mth round" reads M); a run wider than the refusal runs (four or more spaces after a link before the line break, and a comment
marker on the link's line with no line break before it, among them); and an ordinal run or a number past the 400-character
look-back (above). A form the classifier cannot place is REFUSED, keyed
on what it did not resolve: a number glued to a letter or an underscore ("round Nb", the lettered pass); a further number, digits,
a digit ordinal or a number word, after a refusal run the list did not consume that is not a date ("rounds N; M", "round N, M",
"round N, or M", "round N and/or M") or before an ordinal run the list did not consume ("the Nth, Mth round", in digits or in
words, "the Nth
and/or Mth round", a compound ordinal written with a space, an ordinal joined by a hyphen to a number other than a tens word, "one
hundred and first"); a number both before the word and after it; a plural that names one
number ("rounds N", "the Nth rounds"); a range that does not ascend ("rounds M-N" with M past N); a number word the reader does not
read beside the word (LARGE: hundred, thousand, million and billion after the word or after a number it read, and their ordinals
before it or after it; and any ordinal word after the word); punctuation or markup in that short run between the word and a number,
digits or a word ("round: N", "round (N)", "round **N**", "round `N`"), the one exemption being the keyword-argument spelling, the
word glued to `=`; and punctuation or markup in that short run between an ordinal, a LARGE one among them, and the word, "review"
allowed after the run with a run of its own ("the *Nth* round", "the `Nth` round", "the Nth (review) round", a comma after the
ordinal too), credited or not, but not before another word the word begins. Each form stated here as refused refuses with its
reason and never passes: widening the credit is not widening what passes unresolved.

THE CREDIT. A numbered round is credited to the reviewer when the qualifier before the word names that party, "the reviewer's round
N", "the maintainer's round N" or "the maintainer's Nth round" (CREDIT: one party under two names; the apostrophe ASCII or
typographic; "review" may stand between the qualifier and the word, and an ordinal run, "review" on either side of it; the
qualifier's gaps take the same wrap as the separator; a list or a range, every number judged), and it is credited to the reviewer
BY DEFAULT when no qualifier names a party ("review round N", "Review round N", a bare "round N", "rounds N and M", "the round-N
head", "in its Nth round"): rounds belong to the reviewer and the author's work between them is a pass, so an unqualified round is
the reviewer's by that convention, a default with this stated reason (DEFAULT), not a guess; credit() returns the reason beside the
party, so a caller can tell the default from an explicit qualifier, and the refusal of an unqualified round outside the caller's
set states the default it was read under. "the author's round N" and "the author's Nth round" credit a round to the author (AUTHOR)
and are refused. offences() returns every misattribution with its reason and the line it sits on: a round numbered outside the
caller's set (UNRULED: no ruling exists for it, an author's pass labelled a round or a round not yet held; the reason names the
caller's set and its author form so the writer knows what to write, and the date form for another review's round), a round credited
to the author (AUTHORS_ROUND), a numbered pass credited to the reviewer or the maintainer (PASS, WRONG_PARTY: the reason names the
wrong party; a pass is numbered by digits or a cardinal word after the word pass, with the separators and continuations of a round,
while an ordinal before the word pass is not read and neither is an unnumbered pass), and every form the classifier cannot place
(UNCLASSIFIABLE). No message of this module spells a numbered-round form of its own (the unclassifiable refusal quotes the text it
refused, and that quotation is the writer's), so a quoted refusal reads clean, and every spelling of the word in this module's text,
this docstring included, is one the reader passes unread, and the text holds no offence under a synthetic set, which the rule's test
pins by execution: a caller that censuses this module's text reads it clean."""
import re

# the word, then what follows it: a separator (nothing before digits, spaces, hyphens, a newline, a comment marker, a hash; after a
# newline the `*` of a block comment's continuation line), a number (digits or a cardinal word), an optional list or range
# continuation (each number judged; its joins take any whitespace or the wrap, _JOIN, on either side of the list word, the range
# word or the comma, and after a range mark, but spaces alone before a range mark, since one opening a line is a bullet, not a
# link; the bare comma and the serial comma are the plural's alone, since a singular followed by a
# comma and a number is a count and the list would bind the count as a round, and the singular's one comma is a comma followed by
# "and"; a number of the continuation is never a date's year, which the DATE form consumes), and the character after the last digit
# (a letter or an underscore glued to it makes the form unclassifiable; no letter may follow a number word)
WORD = re.compile(r"\bround(?P<plural>s?)", re.I)
_WRAP = r"(?:\n[ \t]*\*)?"
_SEP = r"[-\s#/]*" + _WRAP + r"[-\s#/]*"
# the wrap a list or a range takes across a comment line break, the one the separator takes: one newline, then optional
# indentation and a comment marker (`#`, `//`, or a block comment's `*`), then spaces
_BREAK = r"\n[^\S\n]*(?:#|//|\*)?[^\S\n]*"
# the space on either side of a list word, a range word or a comma that joins two numbers: any whitespace, the wrap among it
_JOIN = r"\s*(?:" + _BREAK + r")?"
# the number words the reader reads: a cardinal's or an ordinal's value is its place in CARDINALS or ORDINALS; a tens word's is
# twenty for the first of TENS or ORDINAL_TENS and ten more for each after it; a tens word joined by a hyphen to a word of UNITS
# or ORDINAL_UNITS is the sum of the two
CARDINALS = ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve", "thirteen",
             "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen")
ORDINALS = ("zeroth", "first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth", "eleventh",
            "twelfth", "thirteenth", "fourteenth", "fifteenth", "sixteenth", "seventeenth", "eighteenth", "nineteenth")
TENS = ("twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety")
ORDINAL_TENS = ("twentieth", "thirtieth", "fortieth", "fiftieth", "sixtieth", "seventieth", "eightieth", "ninetieth")
UNITS = ("one", "two", "three", "four", "five", "six", "seven", "eight", "nine")
ORDINAL_UNITS = ("first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth")
# the number words the reader does not read, each refused beside the word or beside a number it read (their ordinals before the
# word, where a cardinal is a count)
LARGE = ("hundred", "thousand", "million", "billion")
LARGE_ORDINALS = ("hundredth", "thousandth", "millionth", "billionth")
_WHOLE = r"(?![A-Za-z])"
_CARDINAL = r"(?:(?:%s)-(?:%s)|%s|%s)" % ("|".join(TENS), "|".join(UNITS), "|".join(TENS), "|".join(CARDINALS)) + _WHOLE
_ORDINAL_WORD = r"(?:(?:%s)-(?:%s)|%s|%s)" % ("|".join(TENS), "|".join(ORDINAL_UNITS), "|".join(ORDINAL_TENS), "|".join(ORDINALS)) + _WHOLE
_ORDINAL = r"(?:\d+(?:st|nd|rd|th)" + _WHOLE + "|" + _ORDINAL_WORD + ")"
_UNREAD = r"(?:%s|%s)" % ("|".join(LARGE), "|".join(LARGE_ORDINALS)) + _WHOLE
# any number word: a further one after a run the list consumed, or before an ordinal run, is refused
_ANY_WORD = r"(?<![A-Za-z])(?:%s|%s|%s)" % (_CARDINAL, _ORDINAL_WORD, _UNREAD)
_NUM = r"(?:\d+(?!\d|-\d\d-\d\d)|(?<![A-Za-z])" + _CARDINAL + ")"
# the range words and the range marks (a hyphen or an en dash); a range mark that opens a line, after its indentation and any
# comment marker, is a BULLET, never the link that joins across a line break, so after a first line that ends at the number it
# joins nothing, as a bare line break joins nothing: a list or an ordinal run takes spaces alone before a range mark, and the wrap
# FURTHER, FORE and DATE take never has a range mark as the link that starts the next line (_NO_BULLET); a range mark that ends a
# line joins across the wrap after it
_RANGE_WORD = r"to|through|thru"
_RANGE_MARK = r"[-\u2013]"
_RANGE = _RANGE_WORD + "|" + _RANGE_MARK
_NO_BULLET = r"(?!" + _RANGE_MARK + r")"
_LIST = r"and|or|&|/"
_NUMBERED = (r"(?P<sep>" + _SEP + r")(?P<num>\d+|(?<![A-Za-z])" + _CARDINAL + r")(?P<list>(?:(?:" + _JOIN + r"(?:%s)|[^\S\n]*" + _RANGE_MARK + r")" + _JOIN
             + r"#?" + _NUM + r")*)(?P<tail>[A-Za-z_]?)")
# the continuations but a range mark: the singular's (a range word, a list word, and a comma followed by "and") and the plural's
# (those, a bare comma, and a comma followed by any list word)
_CONTINUE = {False: _RANGE_WORD + "|" + _LIST + r"|," + _JOIN + "and", True: _RANGE_WORD + "|" + _LIST + r"|,(?:" + _JOIN + "(?:" + _LIST + "))?"}
NUMBERED = {p: re.compile(_NUMBERED % _CONTINUE[p], re.I) for p in (False, True)}
# one continuation of a run the list consumed, found by _numbers() with finditer over that run: the wrap is taken after the link
# (_JOIN); before the link, and between a comma and its list word, the search passes over what the list consumed, so it needs no
# bullet guard of its own (the list never consumes a bullet)
CONTINUATION_TOKEN = re.compile(r"\s*(?P<how>,\s*(?:%s)|%s|%s|,)" % (_LIST, _RANGE, _LIST) + _JOIN + r"#?(?P<num>\d+(?:st|nd|rd|th)?|%s|%s)" % (_ORDINAL_WORD, _CARDINAL),
                                re.I)
FIRST_TOKEN = re.compile(r"\d+(?:st|nd|rd|th)?|%s|%s" % (_ORDINAL_WORD, _CARDINAL), re.I)
RANGE_WORDS = re.compile(r"^(?:%s)$" % _RANGE, re.I)
DIGITS = re.compile(r"\d+")
# the list word a run the list did not consume may hold before a further number: "and" or "or", alone or joined by a slash to
# either ("and/or", and with a space on either side of the slash or both, "and / or"), which no list or range reads, so a number
# after "and/or" is refused as one the list did not consume
_RUN_WORD = r"(?:and|or)(?:\s*/\s*(?:and|or))?"
# the wrap FURTHER and FORE take (_WRAP_RUN): the wrap a list takes (_BREAK) beside a LINK, a comma, a list word or a range mark
# (_MARK, those spelled in punctuation: a comma, &, /, a hyphen or an en dash, a slash that begins `//` or `/*` being a comment's
# and no list word; or a list word of _RUN_WORD, glued to no letter before it and to no letter, digit or underscore after it).
# Either the link ends the first line (up to six characters of punctuation and spaces between the number and the link, up to three
# after it) and the next line holds the wrap, optionally a second link (a range mark may be one), up to three characters and the
# number; or the first line ends at the number, spaces aside, and the next holds the wrap, the link (never a range mark, which
# there is a bullet: _NO_BULLET), up to three characters and the number. A line break with no link beside it, or with only a bullet
# after it, is no continuation, so what follows it is not read. DATE takes the same wrap beside a link spelled in punctuation, with
# no second link (_DATE_WRAP), as its one-line run holds no letter.
_MARK = r"(?:[,&\-\u2013]|/(?![/*]))"
_LINK = r"(?:" + _MARK + r"|(?<![A-Za-z])" + _RUN_WORD + r"(?!\w))"
_WRAP_RUN = (r"(?:[^\w\n]{0,6}" + _LINK + r"[^\w\n]{0,3}" + _BREAK + r"(?:" + _LINK + r")?[^\w\n]{0,3}|[^\S\n]*" + _BREAK + _NO_BULLET + _LINK
             + r"[^\w\n]{0,3})")
_DATE_WRAP = r"(?:[^\w\n]{0,6}" + _MARK + r"[^\w\n]{0,3}" + _BREAK + r"[^\w\n]{0,3}|[^\S\n]*" + _BREAK + _NO_BULLET + _MARK + r"[^\w\n]{0,3})"
# after the last number the form consumed (or after the word of an ordinal form): a run of punctuation and spaces (no letter, no
# newline), optionally a list word (_RUN_WORD) and a shorter run, or the wrap beside a link (_WRAP_RUN), and then a number, digits
# or a number word, is a continuation
# the list did not resolve
FURTHER = re.compile(r"(?:[^\w\n]{1,6}(?:" + _RUN_WORD + r"[^\w\n]{1,3})?|" + _WRAP_RUN + r")(?:\d|" + _ANY_WORD + ")", re.I)
# after the word with no number read: a run of punctuation and spaces and then a number, digits or a number word, is punctuation or
# markup between the word and a number, unclassifiable unless the run is the keyword-argument spelling's `=`
GAP_NUMBER = re.compile(r"(?P<run>[^\w\n]{1,6})(?:\d|" + _ANY_WORD + ")", re.I)
# after the word with no number read: an ordinal word or a LARGE word, the separator between, is a number word the reader does not
# read after the word
UNREAD_AFTER = re.compile(_SEP + r"(?<![A-Za-z])(?P<num>" + _ORDINAL_WORD + "|" + _UNREAD + ")", re.I)
# a date after the number, the list or an ordinal form's word: the same run, or the wrap beside a link spelled in punctuation
# (_DATE_WRAP, where a bullet is no link either), and then YYYY-MM-DD, part of the form (a further
# number after it is refused)
DATE = re.compile(r"(?:[^\w\n]{1,6}|" + _DATE_WRAP + r")\d{4}-\d{2}-\d{2}(?!\d)")
GAP = r"[\s#/]*" + _WRAP + r"[\s#/]*"
# an ordinal run before the word, ending where the word starts: ordinals joined by the plural's or the singular's continuations (a
# range mark taking spaces alone before it, as in the list), the separator (never empty, since the word starts at a word boundary),
# and "review" allowed between it and the word; not glued to a letter, a digit or an underscore before it, so the end of another word
# ("millisecond") is no ordinal (a number and a hyphen before it are FORE's)
_ORDINAL_RUN = _ORDINAL + r"(?:(?:" + _JOIN + r"(?:%s)|[^\S\n]*" + _RANGE_MARK + r")" + _JOIN + _ORDINAL + r")*"
BEFORE = {p: re.compile(r"(?<!\w)(?P<run>" + (_ORDINAL_RUN % _CONTINUE[p]) + r")(?P<gap>" + _SEP + r")(?:review" + GAP + r")?\Z", re.I)
          for p in (False, True)}
# a LARGE word's ordinal before the word, the ordinal separator between: a number word the reader does not read before the word
UNREAD_BEFORE = re.compile(r"(?:%s)" % "|".join(LARGE_ORDINALS) + _WHOLE + _SEP + r"(?:review" + GAP + r")?\Z", re.I)
# an ordinal, a LARGE word's ordinal among them, then a run of punctuation, markup and spaces on its line (up to six characters),
# and "review" allowed after it with a run of its own: punctuation or markup between an ordinal and the word, read only where
# BEFORE and UNREAD_BEFORE read nothing, so a run that is the separator alone has already been read and what this finds holds a
# character the separator in its place does not take (the mirror of GAP_NUMBER after the word)
MARKUP_BEFORE = re.compile(r"(?<!\w)(?:" + _ORDINAL + "|(?:%s)" % "|".join(LARGE_ORDINALS) + _WHOLE + r")[^\w\n]{1,6}(?:review[^\w\n]{1,6})?\Z", re.I)
# before an ordinal run: a number, digits, a digit ordinal or a number word, then a run of punctuation and spaces, optionally a
# list word (_RUN_WORD) and a shorter run, or the wrap beside a link (_WRAP_RUN), is a number the run did not consume (looked for
# within the 400 characters before the run, by classify())
FORE = re.compile(r"(?:\d(?:st|nd|rd|th)?|" + _ANY_WORD + r")(?:[^\w\n]{1,6}(?:" + _RUN_WORD + r"[^\w\n]{1,3})?|" + _WRAP_RUN + r")\Z", re.I)
# the word glued to a letter, or to a hyphen and a letter ("rounded", "round-trip"): another word, before which an ordinal is not
# read
COMPOUND = re.compile(r"-?[A-Za-z]")
# the qualifier before the word, its gaps taking the same wrap as the separator, "review" allowed between it and the word, and an
# ordinal run allowed between them, "review" on either side of it: the reviewer's (or the maintainer's: one party under two names)
# is the explicit credit; the author's is a round credited to the author
_QUALIFIED = (r"\bthe" + GAP + r"%s['’]s" + GAP + r"(?:review" + GAP + r")?(?:" + (_ORDINAL_RUN % _CONTINUE[True]) + _SEP + r"(?:review" + GAP
              + r")?)?(?P<word>round)")
CREDIT = re.compile(_QUALIFIED % r"(?:maintainer|reviewer)", re.I)
AUTHOR = re.compile(_QUALIFIED % r"author", re.I)
# a pass credited to the reviewer or the maintainer: the qualifier, then the word pass with a number after it (NUMBERED, the same
# separators, numbers and continuations); an unnumbered pass ("the maintainer's pass over the tree") is not read, and neither is
# an ordinal before the word pass
PASS = re.compile(r"\bthe" + GAP + r"(?P<who>maintainer|reviewer)['’]s" + GAP + r"pass(?P<plural>es)?", re.I)
# the numbered form classes, by (plural, separator kind), an ordinal form's kind the separator between its ordinals and the word
# with "ordinal" before it, each with the separator its probes are spelled with; a caller requires every class its population uses
# to be one of these, and the pin holds a red and a green probe per class
FORM_CLASSES = {(False, "none"): "", (False, "space"): " ", (False, "hyphen"): "-", (False, "hash"): " #",
                (False, "wrap"): "\n    # ", (False, "star"): "\n * ", (True, "space"): " ", (True, "wrap"): "\n", (True, "star"): "\n * ",
                (False, "ordinal space"): " ", (False, "ordinal hyphen"): "-", (False, "ordinal wrap"): "\n    # ", (False, "ordinal star"): "\n * ",
                (True, "ordinal space"): " ", (True, "ordinal wrap"): "\n", (True, "ordinal star"): "\n * "}
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


def value(token):
    """The number one token spells: digits (an ordinal's suffix aside), a cardinal or an ordinal word, or a tens word joined by a
    hyphen to a unit, the sum of the two. A word the reader does not read raises (ValueError from the table's index)."""
    t = token.lower()
    d = DIGITS.match(t)
    if d is not None:
        return int(d.group())
    tens, _, unit = t.partition("-")
    return _word(tens) + _word(unit) if unit else _word(tens)


def _word(w):
    """The value of one number word of the reader's tables."""
    if w in TENS:
        return TENS.index(w) * 10 + 20
    if w in ORDINAL_TENS:
        return ORDINAL_TENS.index(w) * 10 + 20
    if w in ORDINALS:
        return ORDINALS.index(w)
    return CARDINALS.index(w)


def _numbers(run):
    """The numbers a run names (the numbers of a NUMBERED match from its first to its list's end, or an ordinal run), a list's each
    and a range's every number from its first to its last, or None with the reason when a range does not ascend."""
    first = FIRST_TOKEN.match(run)
    nums = [value(first.group())]
    for t in CONTINUATION_TOKEN.finditer(run, first.end()):
        x = value(t.group("num"))
        if RANGE_WORDS.match(t.group("how")):
            if x <= nums[-1]:
                return None, "a range that does not ascend (%d %s %d)" % (nums[-1], t.group("how"), x)
            nums += list(range(nums[-1] + 1, x + 1))
        else:
            nums.append(x)
    return nums, None


def dated(text, end):
    """Where the form ends: after the DATE form when one follows `end` (the end of the list, or the word of an ordinal form), else at
    `end`."""
    d = DATE.match(text, end)
    return end if d is None else d.end()


def before(text, w):
    """The ordinal run before the occurrence `w` of the word (a match of BEFORE, its group run the ordinals and its group gap the
    separator), or None: none is read before another word the word begins (COMPOUND), and none that starts more than 400 characters
    before the word is looked for."""
    if COMPOUND.match(text, w.end()):
        return None
    return BEFORE[bool(w.group("plural"))].search(text, w.start() - 400 if w.start() > 400 else 0, w.start())


def classify(text, w):
    """One occurrence `w` of the word in `text` (a match of WORD): (kind, offset, spelled, the numbers, why unclassifiable). Kind is
    "numbered" (every number of the list, the range or the ordinal run read; a date after them consumed), "unnumbered" (no number
    beside the word: not read) or "unclassifiable" (a number the rule cannot place, refused with the reason); the offset is where
    the first number sits (the word's, for a form with none), and spelled is the mention: from the word, or from the first ordinal,
    to the last number or the word, and for an unclassifiable form the text the reason quotes."""
    plural = bool(w.group("plural"))
    n = NUMBERED[plural].match(text, w.end())
    b = before(text, w)
    if b is not None:
        start = b.start("run")
        fore = FORE.search(text, start - 400 if start > 400 else 0, start)
        if fore is not None:
            why = "a further number before the ordinals the list did not consume: %r" % text[fore.start():w.end()]
            return "unclassifiable", start, text[fore.start():w.end()], [], why
        nums, why = _numbers(b.group("run"))
        if nums is None:
            return "unclassifiable", start, text[start:w.end()], [], "%s: %r" % (why, text[start:w.end()])
        if n is not None and DATE.match(text, w.end()) is None:
            return "unclassifiable", start, text[start:n.end()], [], "a number both before the word and after it: %r" % text[start:n.end()]
        more = FURTHER.match(text, dated(text, w.end()))
        if more is not None:
            return "unclassifiable", start, text[start:more.end()], [], "a further number after a run the list did not consume, and not a date: %r" % text[start:more.end()]
        if plural and len(nums) == 1:
            return "unclassifiable", start, text[start:w.end()], [], "a plural that names one number: %r" % text[start:w.end()]
        return "numbered", start, text[start:w.end()], nums, None
    unread = UNREAD_BEFORE.search(text, w.start() - 40 if w.start() > 40 else 0, w.start())
    if unread is not None:
        return "unclassifiable", unread.start(), text[unread.start():w.end()], [], "a number word the rule does not read, before the word: %r" % text[unread.start():w.end()]
    mark = None if COMPOUND.match(text, w.end()) else MARKUP_BEFORE.search(text, w.start() - 40 if w.start() > 40 else 0, w.start())
    if mark is not None:
        return "unclassifiable", mark.start(), text[mark.start():w.end()], [], "punctuation or markup between an ordinal and the word: %r" % text[mark.start():w.end()]
    if n is None:
        unread = UNREAD_AFTER.match(text, w.end())
        if unread is not None:
            return "unclassifiable", unread.start("num"), text[w.start():unread.end()], [], "a number word the rule does not read, after the word: %r" % text[w.start():unread.end()]
        gap = GAP_NUMBER.match(text, w.end())
        if gap is not None and gap.group("run") != "=":
            return "unclassifiable", w.start(), text[w.start():gap.end()], [], "punctuation or markup between the word and a number: %r" % text[w.start():gap.end()]
        return "unnumbered", w.start(), text[w.start():w.end()], [], None
    at = n.start("num")
    nums, why = _numbers(text[at:n.end("list")])
    if nums is None:
        return "unclassifiable", at, text[w.start():n.end()], [], "%s: %r" % (why, text[w.start():n.end("list")])
    if n.group("tail"):
        return "unclassifiable", at, text[w.start():n.end()], [], "a number glued to a letter or an underscore: %r" % text[w.start():n.end()]
    more = FURTHER.match(text, dated(text, n.end("list")))
    if more is not None:
        return "unclassifiable", at, text[w.start():n.end()], [], "a further number after a run the list did not consume, and not a date: %r" % text[w.start():more.end()]
    if plural and len(nums) == 1:
        return "unclassifiable", at, text[w.start():n.end()], [], "a plural that names one number: %r" % text[w.start():n.end("list")]
    return "numbered", at, text[w.start():n.end("list")], nums, None


def forms(text):
    """Every occurrence of the word in `text`, classified: (line, spelled, kind, numbers) with kind "numbered" (the numbers of
    the mention, a list's each and a range's every number; the spelling runs from the word, or from the first ordinal, to the last
    number or the word, a date after it consumed but not spelled), "unnumbered" (no number beside the word: not read) or
    "unclassifiable" (a number the rule cannot place: refused, since it cannot say whether the form is a credit or which rounds it
    names)."""
    out = []
    for w in WORD.finditer(text):
        kind, at, spelled, nums, _ = classify(text, w)
        out.append((text.count("\n", 0, at) + 1, spelled, kind, nums))
    return out


def form_class(spelled):
    """The class of a numbered form's spelling: (plural, separator kind) for a number after the word, the separator from the word to
    its first number; (plural, "ordinal " and the separator kind) for an ordinal run before it, the separator between the run and
    the word."""
    w = WORD.search(spelled)
    plural = bool(w.group("plural"))
    if w.start() == 0:
        return (plural, sep_kind(NUMBERED[plural].match(spelled, w.end()).group("sep")))
    return (plural, "ordinal " + sep_kind(BEFORE[plural].search(spelled, 0, w.start()).group("gap")))


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
        kind, at, spelled, _, _ = classify(text, w)
        if kind == "numbered":
            party, why = credit(text, w, qualified)
            out.append((text.count("\n", 0, at) + 1, spelled, party, why))
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
        kind, at, spelled, nums, why = classify(text, w)
        if kind == "unnumbered":
            continue
        line = text.count("\n", 0, at) + 1
        if kind == "unclassifiable":
            out.append((at, filename, line, spelled, UNCLASSIFIABLE % why))
            continue
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
