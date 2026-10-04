"""The machinery the text censuses of tests/test_origin_main_readers.py (the tests that read the checkout's origin/main,
round 1 of PR 959, ruling D) and tests/test_branch_name_readers.py (the tests that read the name of the checkout's
current branch, the 22:25Z ruling of 2026-10-03 on PR 959, item 2) share: the listing of the tracked files, the lines of
each that a census reads, the scan of each line and of runs of consecutive lines for a census's spellings, the
comparison of each file's hit lines with its judged lines, line by line, and the findings over a whole tree. Each census
module holds its own spellings, classification, readers and fixture (Census), and the docstring that says what it
counts, why, and what it cannot see; the rules below are the same for both.

A census reads every tracked file (`git ls-files` at the repository root) that is text (no NUL in its first 8000 bytes,
git's own test), whatever directory it is in, since a test runs code from tests/, scripts/, .githooks/, bin/, kernel/,
tools/, ui/ and more; of a Markdown file only the lines inside fenced code blocks, at any indent, in a list item or a
blockquote too, since a test runs a fenced block (tests/test_env_credential_names.py runs one of docs/reference.md's)
and never the prose around one; and none of CENSUS_FILES, the census modules, this one and their fixtures, which run
`git ls-files` and nothing else, or run nothing, and whose texts hold every spelling the censuses look for. A line is
a hit when it carries one of the census's spellings; a run of two up to WINDOW consecutive lines is a hit too when its
text, the lines joined, carries one of the census's spellings made of more than one word that none of its lines, and
no shorter run inside it, carries alone (split_hits).

Every hit file is classified (the census's CLASSIFIED: the kinds of its hits and why) and pinned by its text (the
census's fixture: each classified file's judged hit lines, stripped, as many times as each appears, each standalone run
of seven or more hex digits written as HEX_RUN). census_problems names each finding: a hit in a file CLASSIFIED does
not name; a hit line in a classified file the fixture does not hold, or a judged line no longer there (a line changed,
added or gone, a second copy of a judged line among them, compared line by line, never by count); a READERS line no hit
carries any longer; a CLASSIFIED file with no hit left; a file in one of CLASSIFIED and the fixture and not the other;
and a file whose kinds and READERS disagree. An empty scan is each census module's own tree-level pin.
"""
import json
import os
import re
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# The census modules, this machinery and their fixtures: no census reads any of them (the module docstring).
CENSUS_FILES = ("tests/ref_reader_census.py",
                "tests/test_origin_main_readers.py", "tests/fixtures/origin-main-hits.json",
                "tests/test_branch_name_readers.py", "tests/fixtures/branch-name-hits.json")
# A run of seven or more lowercase hex digits standing alone, which pinned_text writes as HEX_RUN, so the judged lines
# carry no commit id that a hit line quotes (tools/viewer-resize-summarize.mjs names two trees by theirs); a change to
# such a run alone is not a change a census judges.
_HEX_RUN = re.compile(r"(?<![0-9A-Za-z])[0-9a-f]{7,}(?![0-9A-Za-z])")
HEX_RUN = "<hex>"
# A fence opens at the first run of three or more backticks or tildes anywhere on a line, as the test that runs a fenced
# block finds one (an unanchored search), so a fence in a list item or a blockquote, at any indent, is read; it closes on
# a line holding only a run of the same character, at least as long, after any indent or quote marks.
_FENCE_OPEN = re.compile(r"`{3,}|~{3,}")
_FENCE_CLOSE = re.compile(r"[ \t>]*(`{3,}|~{3,})[ \t]*")
# The kinds a hit file's hits are, as each census names them: a read of the census's subject in the checkout the test
# runs in (its own READS text), a read of a repository the test or the code under test builds, and no read.
SYNTHETIC = "a repository the test builds"
NOT_A_READ = "not a read"


def tracked_files(root=ROOT):
    """The tracked paths of the repository at `root`, from `git ls-files -z` there with no GIT_* variable of the caller's
    (one naming another repository would list that one). A failure to list is the test's own error, in git's words,
    never an empty census."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    r = subprocess.run(["git", "ls-files", "-z"], cwd=str(root), env=env, capture_output=True, timeout=120)
    if r.returncode != 0:
        raise AssertionError("git ls-files failed in %s (exit %d): %s"
                             % (root, r.returncode, r.stderr.decode("utf-8", "replace").strip()))
    rels = sorted(x.decode("utf-8", "surrogateescape") for x in r.stdout.split(b"\0") if x)
    if not rels:
        raise AssertionError("git ls-files listed nothing in %s" % root)
    return rels


def scanned_lines(rel, text):
    """(line number, line) for every line of `text` a census reads: all of them, but for a Markdown file only those
    inside a fenced code block (a fence opens at the first run of three or more backticks or tildes on a line, at any
    indent, in a list item or a blockquote, and closes on a line of the same character, at least as many, and nothing
    else but indent and quote marks)."""
    lines = text.splitlines()
    if not rel.endswith(".md"):
        return list(enumerate(lines, 1))
    out, fence = [], None
    for n, line in enumerate(lines, 1):
        if fence is None:
            m = _FENCE_OPEN.search(line)
            if m:
                fence = m.group(0)
            continue
        m = _FENCE_CLOSE.fullmatch(line)
        if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence):
            fence = None
            continue
        out.append((n, line))
    return out


def pinned_text(line):
    """A stripped hit line as a fixture holds it: each standalone run of seven or more hex digits written as HEX_RUN."""
    return _HEX_RUN.sub(HEX_RUN, line)


def unpinned(lines, pinned):
    """(the lines beyond the pinned texts, the pinned texts beyond the lines): `lines` the stripped hit lines a file has
    now and `pinned` the texts judged for it, each matched as often as it appears, so a second copy of a judged line is
    named as one beyond them."""
    left = Counter(pinned)
    added = []
    for line in lines:
        if left[line] > 0:
            left[line] -= 1
        else:
            added.append(line)
    return added, sorted(left.elements())


def judged(root, hits):
    """The fixture `hits` (a path under `root`) as {path: [text]}; a missing or unreadable file is the test's own
    error."""
    with open(os.path.join(str(root), hits), encoding="ascii") as f:
        return json.load(f)


def _listing(lines):
    return "\n".join("    %d: %s" % (n, line[:200]) for n, line in lines)


class Census:
    """One census's spellings and its words: `spellings`, (what it is, the pattern) for each spelling looked for in a
    line; `candidate`, a pattern every line a spelling can match holds (a line without it is not matched against
    `spellings`); `split_spellings`, the spellings made of more than one word, which a line break can split, and
    `split_candidate`, a word one of them holds, which a run of lines must hold before it is joined; `window`, the most
    consecutive lines a run joins; `hits`, the fixture's path; `reads`, the kind a reader's hits are; `subject`, what a
    reader reads, as the findings name it ("the origin/main of the checkout the test runs in"); and `spelling`, what a
    spelling spells ("origin/main")."""

    def __init__(self, spellings, candidate, split_spellings, split_candidate, window, hits, reads, subject, spelling):
        self.spellings, self.candidate = spellings, candidate
        self.split_spellings, self.split_candidate, self.window = split_spellings, split_candidate, window
        self.hits, self.reads, self.subject, self.spelling = hits, reads, subject, spelling

    def spelled(self, line):
        """The spellings `line` carries, by what each is."""
        if not self.candidate.search(line):
            return []
        return [what for what, rx in self.spellings if rx.search(line)]

    def census(self, root=ROOT, rels=None):
        """{path: [(line number, the line stripped)]}: every hit, by file, over the tracked text files at `root` (all
        but CENSUS_FILES)."""
        hits = {}
        for rel in tracked_files(root) if rels is None else rels:
            if rel in CENSUS_FILES:
                continue
            path = os.path.join(str(root), rel)
            if os.path.islink(path) or not os.path.isfile(path):
                continue
            data = Path(path).read_bytes()
            if b"\0" in data[:8000]:
                continue
            text = data.decode("utf-8", errors="replace")
            if not self.candidate.search(text):
                continue
            scanned = scanned_lines(rel, text)
            each = [set(self.spelled(line)) for _n, line in scanned]
            for (n, line), kinds in zip(scanned, each):
                if kinds:
                    hits.setdefault(rel, []).append((n, line.strip()))
            for n, joined in self.split_hits(scanned, each):
                hits.setdefault(rel, []).append((n, joined))
        return hits

    def split_hits(self, scanned, each=None):
        """(the first line's number, the lines joined by a space, each stripped) for every run of two up to `window`
        consecutive lines of `scanned` (scanned_lines' pairs) whose joined text carries a spelling that none of its
        lines, and no shorter run inside it, carries alone: a spelling split across lines (an argument list split over
        lines, a backslash continuation), which a scan of each line alone does not see. Only the spellings a line break
        can split are read across lines, and only in a run that holds a word of one (`split_candidate`). `each` holds
        each line's own spellings when the caller has them (census)."""
        hold = [bool(self.split_candidate.search(line)) for _n, line in scanned]
        seen = {} if each is None else {(i, 1): kinds for i, kinds in enumerate(each)}

        def kinds(i, k):
            if (i, k) not in seen:
                if k == 1:
                    seen[(i, k)] = set(self.spelled(scanned[i][1]))
                else:
                    text = " ".join(line.strip() for _n, line in scanned[i:i + k])
                    seen[(i, k)] = {what for what, rx in self.split_spellings if rx.search(text)}
            return seen[(i, k)]
        out = []
        for i in range(len(scanned)):
            for k in range(2, self.window + 1):
                if i + k > len(scanned) or scanned[i + k - 1][0] - scanned[i][0] != k - 1:
                    break
                if not any(hold[i:i + k]):
                    continue
                inner = set()
                for size in range(1, k):
                    for j in range(i, i + k - size + 1):
                        inner |= kinds(j, size)
                if kinds(i, k) - inner:
                    out.append((scanned[i][0], " ".join(line.strip() for _n, line in scanned[i:i + k])))
        return out

    def census_problems(self, hits, judged, classified, readers):
        """Every finding of the census over `hits` (census's {path: [(line number, line)]}) against `judged` (the
        fixture, as judged() reads it), `classified` and `readers`, each a text naming the file and what to do: a hit
        in a file `classified` does not name; each file's hit lines against its judged lines, line by line, each matched
        as often as it appears (unpinned), never by their count; a classified file with no hit left; a file in one of
        `classified` and the fixture and not the other; a `readers` line no hit carries; and a file whose kinds and
        `readers` disagree."""
        problems = []
        question = "does it, or code it runs, read %s?" % self.subject
        for path, lines in sorted(hits.items()):
            entry = classified.get(path)
            if entry is None:
                problems.append("%s: %d line(s) no entry of CLASSIFIED covers; judge each (%s), then add the file to "
                                "CLASSIFIED, and each line that does read it to READERS:\n%s"
                                % (path, len(lines), question, _listing(lines)))
            else:
                added, gone = unpinned([pinned_text(line) for _n, line in lines], judged.get(path, ()))
                if added or gone:
                    new = [(n, line) for n, line in lines if pinned_text(line) in added]
                    problems.append("%s: hit lines not judged in %s (added or changed):\n%s\nand judged lines no longer "
                                    "there (gone or changed):\n%s\njudge each (%s), then set the file's lines in %s, "
                                    "and each line that reads it in READERS"
                                    % (path, self.hits, _listing(new) or "    none",
                                       "\n".join("    %s" % line[:200] for line in gone) or "    none", question,
                                       self.hits))
        for path in sorted(set(classified) - set(hits)):
            problems.append("%s: in CLASSIFIED, and no line there carries a spelling of %s now; remove the entry"
                            % (path, self.spelling))
        for path in sorted(set(classified) ^ set(judged)):
            problems.append("%s: in %s and not in %s; each classified file has its judged lines, and no other file "
                            "does" % ((path, "CLASSIFIED", self.hits) if path in classified
                                      else (path, self.hits, "CLASSIFIED")))
        for path, text, _why in readers:
            if not any(text in line for _n, line in hits.get(path, ())):
                problems.append("%s: READERS lists a read of %s on the line holding %r, and no line there holds it "
                                "now: that reader no longer reads, or moved; judge it and update READERS"
                                % (path, self.subject, text))
        for path, (kinds, _why) in sorted(classified.items()):
            listed = any(p == path for p, _t, _w in readers)
            if (self.reads in kinds) != listed:
                problems.append("%s: CLASSIFIED %s READS, and READERS %s it; make the two agree" % (
                    path, "names" if self.reads in kinds else "does not name", "lists" if listed else "does not list"))
        return problems
