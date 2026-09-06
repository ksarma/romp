#!/usr/bin/env python3
"""UPSTREAM.md stays ONE renderable Markdown table (2026-09-06).

UPSTREAM.md is the fork's queue of upstream-worthy changes: some prose, then one table with the
header `| What | Where it lives here | Status | Notes |`, then a short prose tail. Markdown ends a
table at the first blank line, so a blank line between two rows turns every row after it into a
header-less fragment that GitHub renders as a paragraph of pipes. By 2026-09-06 hand edits and
merge resolutions across several sessions had left FIFTEEN such blank lines in the table (the first
at line 66 of a 140-line file), and one row was present twice: a review-fix commit appended a
rewritten copy of a row instead of replacing the checkpoint copy, and the two copies differed in
text. Nothing failed; the file just stopped rendering as a table.

This test reads the file and checks:
- no git conflict marker line (`<<<<<<< `, `=======`, `>>>>>>> `);
- exactly one header line, with the `|---|---|---|---|` separator right under it, and no second
  separator anywhere;
- from the separator on, every line is a row (starts and ends with `|`) until the table ends at a
  BLANK line or the end of the file; a row after that point is a stranded fragment, and the message
  names the blank line that stranded it and quotes the row. A non-blank, non-row line directly under
  a row is flagged too: Markdown folds it into the table as a one-cell row;
- prose after the table's end is allowed (the file has a tail about how to offer and about security
  items), so long as it holds no row;
- every row has exactly four cells once escaped pipes (`\\|`) and pipes inside backtick code spans
  are masked (three rows carry `\\|` today, one of them outside a code span);
- no two rows are byte-identical, and no two rows share their first 60 characters: a merge that
  keeps both sides of a conflicted row leaves one row in two versions (the 2026-09-06 duplicate,
  and six stale 'candidate' copies a branch merge kept beside main's 'offered' versions the same
  day), and the two versions agree on how they start.

Every message names the offending line number and quotes the line's first 80 characters. The
checker is a pure function over the text so the synthetic cases below exercise each rule; the real
file is checked last. Synthetic fixtures only.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM_MD = ROOT / "UPSTREAM.md"

HEADER = "| What | Where it lives here | Status | Notes |"
SEPARATOR = "|---|---|---|---|"
CELLS = 4
PREFIX = 60   # two versions of one row agree on how they start; unrelated rows diverge well before this

_ESCAPED_PIPE = re.compile(r"\\\|")
_CODE_SPAN = re.compile(r"`[^`]*`")
_CONFLICT = re.compile(r"^(?:<{7}|>{7})(?: |$)|^={7}$")


def _q(line):
    """The first 80 characters of a line, repr-quoted, for a failure message."""
    return repr(line[:80])


def _is_row(line):
    s = line.rstrip()
    return s.startswith("|") and s.endswith("|") and len(s) >= 2


def _mask(row):
    """Hide pipes that are not cell separators: `\\|` escapes, then anything inside a code span."""
    masked = _ESCAPED_PIPE.sub("__", row)
    return _CODE_SPAN.sub(lambda m: "`" + "_" * (len(m.group()) - 2) + "`", masked)


def cells(row):
    """The cells of a table row, with escaped and code-span pipes ignored."""
    return _mask(row).strip()[1:-1].split("|")


def problems(text):
    """Every way `text` fails to be prose + ONE four-column table + optional prose, as messages."""
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()  # the trailing newline is not a line
    out = []
    for n, line in enumerate(lines, 1):
        if _CONFLICT.match(line):
            out.append(f"line {n}: git conflict marker: {_q(line)}")

    headers = [n for n, line in enumerate(lines, 1) if line.rstrip() == HEADER]
    if len(headers) != 1:
        where = ", ".join(f"line {n}: {_q(lines[n - 1])}" for n in headers) or "none"
        out.append(f"expected exactly one table header {HEADER!r}, found {len(headers)} ({where})")
        return out
    head = headers[0]
    separators = [n for n, line in enumerate(lines, 1) if line.rstrip() == SEPARATOR]
    if separators != [head + 1]:
        got = lines[head] if head < len(lines) else ""
        if head + 1 not in separators:
            out.append(f"line {head + 1}: expected the separator {SEPARATOR!r} right under the header, got {_q(got)}")
        for n in separators:
            if n != head + 1:
                out.append(f"line {n}: a second table separator: {_q(lines[n - 1])}")
        return out

    first_row = head + 2
    rows = []
    n = first_row
    while n <= len(lines) and _is_row(lines[n - 1]):
        rows.append((n, lines[n - 1]))
        n += 1
    table_end = n  # first line that is not a row, or len(lines) + 1 at end of file
    if not rows:
        out.append(f"line {first_row}: no table rows under the separator, got {_q(lines[first_row - 1]) if first_row <= len(lines) else 'end of file'}")

    if table_end <= len(lines) and lines[table_end - 1].strip():
        out.append(f"line {table_end}: not a row, but directly under one; Markdown folds it into the table as a one-cell row: {_q(lines[table_end - 1])}")

    # Anything shaped like a row after the table's end is a stranded fragment. Report each break
    # once: the line that ended the table (or the blank run) and the first row after it.
    gap_start = table_end
    in_gap = True
    for n in range(table_end, len(lines) + 1):
        line = lines[n - 1]
        if _is_row(line):
            if in_gap:
                out.append(f"line {gap_start}: {_q(lines[gap_start - 1])} ends the table, so the row at line {n} is a header-less fragment: {_q(line)}")
                in_gap = False
        elif not in_gap:
            in_gap = True
            gap_start = n

    for n, row in rows:
        got = cells(row)
        if len(got) != CELLS:
            out.append(f"line {n}: {len(got)} cells, expected {CELLS} (escaped and code-span pipes ignored): {_q(row)}")

    seen = {}
    heads = {}
    for n, row in rows:
        if row in seen:
            out.append(f"line {n}: byte-identical to the row at line {seen[row]}: {_q(row)}")
            continue
        seen[row] = n
        head = row[:PREFIX]
        if head in heads:
            out.append(f"line {n}: same first {PREFIX} characters as the row at line {heads[head]} (one row in two versions): {_q(row)}")
        else:
            heads[head] = n
    return out


def _doc(rows, head="# Title\n\nSome prose.\n\n", tail=""):
    """A synthetic UPSTREAM.md-shaped document: prose, header, separator, the given row lines, tail."""
    return head + HEADER + "\n" + SEPARATOR + "\n" + "\n".join(rows) + "\n" + tail


ROW_A = "| A thing | `a/b.py` | candidate | Notes. |"
ROW_B = "| Another thing | `c/d.py` (`fn`) | offered | More notes. |"


class Checker(unittest.TestCase):
    """Each rule fires on a synthetic document that breaks it, with the line number and the quote."""

    def test_clean_table_to_end_of_file_passes(self):
        self.assertEqual(problems(_doc([ROW_A, ROW_B])), [])

    def test_clean_table_with_prose_tail_passes(self):
        self.assertEqual(problems(_doc([ROW_A, ROW_B], tail="\nHow to offer: from a clean branch.\n")), [])

    def test_blank_line_between_rows_names_the_blank_and_quotes_the_stranded_row(self):
        got = problems(_doc([ROW_A, "", ROW_B]))
        self.assertEqual(len(got), 1, got)
        self.assertIn("line 8: '' ends the table", got[0])
        self.assertIn("line 9 is a header-less fragment", got[0])
        self.assertIn(repr(ROW_B[:80]), got[0])

    def test_each_break_is_reported_once(self):
        got = problems(_doc([ROW_A, "", "", ROW_B, ROW_A.replace("A thing", "Third"), "", ROW_B.replace("Another", "Fourth")]))
        self.assertEqual(len(got), 2, got)
        self.assertTrue(got[0].startswith("line 8:"), got[0])
        self.assertTrue(got[1].startswith("line 12:"), got[1])

    def test_prose_directly_under_a_row_is_flagged(self):
        got = problems(_doc([ROW_A], tail="This sentence has no blank line above it.\n"))
        self.assertEqual(len(got), 1, got)
        self.assertIn("line 8: not a row, but directly under one", got[0])
        self.assertIn("'This sentence has no blank line above it.'", got[0])

    def test_wrong_cell_count_names_the_row(self):
        got = problems(_doc([ROW_A, "| only | three | cells |"]))
        self.assertEqual(len(got), 1, got)
        self.assertIn("line 8: 3 cells, expected 4", got[0])
        self.assertIn("'| only | three | cells |'", got[0])

    def test_pipes_in_code_spans_and_escaped_pipes_do_not_count(self):
        rows = [
            "| Toggle `on|off` | `x.py` | candidate | a `k|v` pair |",
            "| Toggle on\\|off | `x.py` | candidate | (delegate\\|coordinate\\|question) |",
            "| Both `on\\|off` | `x.py` | candidate | none |",
        ]
        self.assertEqual(problems(_doc(rows)), [])
        got = cells(rows[1])
        self.assertEqual(len(got), 4, got)
        self.assertEqual(got[3], " (delegate__coordinate__question) ")  # cells() returns the masked text

    def test_byte_identical_rows_are_flagged_with_both_line_numbers(self):
        got = problems(_doc([ROW_A, ROW_B, ROW_A]))
        self.assertEqual(len(got), 1, got)
        self.assertIn("line 9: byte-identical to the row at line 7", got[0])

    def test_two_versions_of_one_row_are_flagged(self):
        v1 = "| The tags dialog's edits are targeted ops with acked writes, so a late pane cannot revert them | ui/webview/tags.ts | candidate | one review round |"
        v2 = v1.replace("candidate | one review round", "offered as their PR #999 | ten review rounds")
        got = problems(_doc([v1, ROW_B, v2]))
        self.assertEqual(len(got), 1, got)
        self.assertIn(f"line 9: same first {PREFIX} characters as the row at line 7 (one row in two versions)", got[0])

    def test_rows_that_merely_start_alike_are_not_versions_of_one_row(self):
        a = "| The feed pane repaints only the cards whose inputs changed | ui/webview/feed.ts | candidate | one |"
        b = "| The feed pane repaints on every push, twice a second | ui/webview/feed.ts | candidate | two |"
        self.assertEqual(problems(_doc([a, b])), [])

    def test_conflict_markers_are_flagged(self):
        got = problems(_doc([ROW_A, "<<<<<<< HEAD", ROW_B, "=======", ROW_B.replace("More", "Other"), ">>>>>>> theirs"]))
        markers = [m for m in got if "conflict marker" in m]
        self.assertEqual([m.split(":")[0] for m in markers], ["line 8", "line 10", "line 12"], got)
        self.assertIn("'<<<<<<< HEAD'", markers[0])

    def test_missing_or_doubled_header_is_flagged(self):
        self.assertIn("found 0", problems("# Title\n\n| a | b |\n|---|---|\n| 1 | 2 |\n")[0])
        got = problems(_doc([ROW_A], tail="\n" + HEADER + "\n" + SEPARATOR + "\n" + ROW_B + "\n"))
        self.assertEqual(len(got), 1, got)
        self.assertIn("found 2 (line 5:", got[0])
        self.assertIn("line 9:", got[0])

    def test_separator_must_sit_under_the_header(self):
        got = problems("# T\n\n" + HEADER + "\n" + ROW_A + "\n" + SEPARATOR + "\n")
        self.assertEqual(len(got), 2, got)
        self.assertIn("line 4: expected the separator", got[0])
        self.assertIn("line 5: a second table separator", got[1])


class RealFile(unittest.TestCase):
    def test_upstream_md_is_one_table(self):
        text = UPSTREAM_MD.read_text(encoding="utf-8")
        got = problems(text)
        self.assertEqual(got, [], "UPSTREAM.md is not one renderable table:\n  " + "\n  ".join(got))

    def test_upstream_md_has_the_prose_tail_the_checker_allows(self):
        """The checker allows prose after the table because the file has some today (offering
        guidance and the security-items note). If that tail goes, tighten `problems` to
        table-to-the-end rather than leaving the allowance unexercised."""
        lines = UPSTREAM_MD.read_text(encoding="utf-8").split("\n")
        last_row = max(n for n, line in enumerate(lines, 1) if _is_row(line))
        tail = [line for line in lines[last_row:] if line.strip()]
        self.assertTrue(tail, "UPSTREAM.md is table-to-the-end now; drop the prose-tail allowance in problems()")
        self.assertTrue(tail[0].startswith("When offering:"), tail[0][:80])


if __name__ == "__main__":
    unittest.main()
