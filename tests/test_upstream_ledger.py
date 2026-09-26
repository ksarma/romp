#!/usr/bin/env python3
"""The upstream ledger: one file per candidate under `upstream/`, UPSTREAM.md prose only (2026-09-06).

UPSTREAM.md used to be one Markdown table, and every branch that landed something upstream-worthy
appended a row. Any two such PRs conflicted, a conflicting PR got no CI, and the merges that resolved
the conflicts duplicated rows (main carried one row three times on 2026-09-06). Now each candidate is
`upstream/<YYYY-MM-DD>-<slug>.md` with a strict `key: value` header, UPSTREAM.md holds prose only,
and `scripts/upstream-ledger.py render` prints the table on demand (CI publishes it to the job
summary; nothing is committed).

This module guards eight things, each a pure function over text with synthetic fixtures, the real
tree last:
1. every `upstream/*.md` parses: `---` delimiters, `key: value` lines, the required keys, no unknown
   keys, `status` in the vocabulary, ISO dates, `pr` blank or an integer, the filename shape, the
   filename date equal to `added`, no conflict markers; messages name the file and the key;
2. no two entries share the first 60 characters of `title` (one candidate written twice, imported
   twice, or one entry in two versions after a merge);
3. UPSTREAM.md holds no table row and no conflict marker (the message names the line and the
   `import --row` command) and still holds the `When offering:` paragraph;
4. UPSTREAM.md documents every status value the parser accepts, and only those;
5. `render` is deterministic, orders `approved` first and collapses the closed statuses, cuts the
   Notes cell at 200 characters, links every title to a file that exists, and every table it emits
   passes `problems()` below (moved here from the retired `tests/test_upstream_md.py`: one header
   per table, four cells a row, no blank line inside a table);
6. `set` rewrites one header line and leaves the body byte-identical; `import --row` turns a
   synthetic row into an entry that parses and round-trips its cells, sees an existing entry whether
   or not it parses, keeps the entry's header values under `--replace` and takes the row's under
   `--force`, and names every value it kept or changed;
7. the real tree: `check()` over `upstream/` and UPSTREAM.md returns no problems;
8. `stale` reads every `offered` entry's PR through one injectable gh runner and reports each whose
   PR is merged or closed (or whose offered field names no PR number), exit 1; exit 0 when every
   such PR is open; exit 2 when the clone has no `upstream` remote or gh fails. `check` validates
   the status word and ties it to nothing, so two entries read `offered` for two days after their
   PRs merged (2026-09-19 to 2026-09-21); this is the check that would have caught them.
"""
import contextlib
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

# The ledger script reads no state root, but every test module that loads romp code through a
# loader isolates the state root first (tests/test_state_isolation_order.py enforces the order).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "upstream-ledger.py"


def _load():
    spec = importlib.util.spec_from_file_location("upstream_ledger", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


L = _load()

# ---------------------------------------------------------------- the table checker (moved)

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
    """Every way `text` fails to be prose + ONE four-column table + optional prose, as messages.

    This guards what `render` emits: each of its tables, checked on its own, must be one header with
    the separator right under it, rows with four cells, no blank line inside the table, and no row in
    two versions."""
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
    """A synthetic table document: prose, header, separator, the given row lines, tail."""
    return head + HEADER + "\n" + SEPARATOR + "\n" + "\n".join(rows) + "\n" + tail


ROW_A = "| A thing | `a/b.py` | candidate | Notes. |"
ROW_B = "| Another thing | `c/d.py` (`fn`) | offered | More notes. |"


class Checker(unittest.TestCase):
    """Each rule of the table checker fires on a synthetic document that breaks it, with the line
    number and the quote. The checker guards `render`'s tables (see Render below)."""

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


# ---------------------------------------------------------------- synthetic entries

def _header(name="2026-09-06-alpha.md", **over):
    h = {"title": "A synthetic thing the fork fixed", "status": "candidate", "where": "`kernel/x.py` (`fn`)",
         "added": name[:10], "pr": "", "tier": "", "offered": "", "closed": ""}
    h.update(over)
    return h


def _entry(name="2026-09-06-alpha.md", body="Why upstream wants it.\n", **over):
    return L.format_entry(_header(name, **over), body)


def _parse(name, text):
    return L.parse_entry(name, text)


class EntryRules(unittest.TestCase):
    """Check 1: the parser's rules, each on a synthetic entry, each message naming the file and key."""

    def test_a_clean_entry_parses_with_its_header_and_body(self):
        e, got = _parse("2026-09-06-alpha.md", _entry())
        self.assertEqual(got, [])
        self.assertEqual(e.get("title"), "A synthetic thing the fork fixed")
        self.assertEqual(e.notes, "Why upstream wants it.")
        self.assertEqual(e.slug, "alpha")

    def test_the_eight_line_header_written_by_new_is_what_the_plan_shows(self):
        text = _entry(pr="199", tier="feature")
        head = text.split("---\n")[1].split("\n")
        self.assertEqual([l.split(":")[0] for l in head if l], ["title", "status", "where", "added", "pr", "tier", "offered", "closed"])
        self.assertIn("offered:\n", text)  # blank optional keys are written as `key:` with no trailing space

    def test_missing_delimiters_are_named(self):
        _, got = _parse("2026-09-06-alpha.md", "title: x\nstatus: candidate\n")
        self.assertEqual(got, ["2026-09-06-alpha.md: line 1: expected the opening `---`"])
        _, got = _parse("2026-09-06-alpha.md", "---\ntitle: x\n")
        self.assertEqual(got, ["2026-09-06-alpha.md: no closing `---` after the header"])

    def test_a_header_line_that_is_not_key_value_names_its_line(self):
        _, got = _parse("2026-09-06-alpha.md", _entry().replace("status: candidate", "status:candidate"))
        self.assertEqual(len(got), 2, got)
        self.assertIn("2026-09-06-alpha.md:3: header line is not `key: value`: 'status:candidate'", got[0])
        self.assertIn("missing required key `status`", got[1])

    def test_nested_or_multi_line_values_are_refused(self):
        _, got = _parse("2026-09-06-alpha.md", _entry().replace("where: `kernel/x.py` (`fn`)", "where:\n  - `kernel/x.py`"))
        self.assertTrue(any("header line is not `key: value`" in m for m in got), got)

    def test_each_missing_required_key_is_named(self):
        text = "---\ntitle: x\n---\nbody\n"
        _, got = _parse("2026-09-06-alpha.md", text)
        self.assertEqual(got, [f"2026-09-06-alpha.md: missing required key `{k}`" for k in ("status", "where", "added")])

    def test_a_blank_required_key_is_named(self):
        _, got = _parse("2026-09-06-alpha.md", _entry(where=""))
        self.assertEqual(got, ["2026-09-06-alpha.md: required key `where` is blank"])

    def test_unknown_keys_fail(self):
        _, got = _parse("2026-09-06-alpha.md", _entry().replace("offered:", "labels: fix\noffered:"))
        self.assertEqual(len(got), 1, got)
        self.assertIn("2026-09-06-alpha.md: unknown key `labels`", got[0])

    def test_a_repeated_key_fails(self):
        _, got = _parse("2026-09-06-alpha.md", _entry().replace("pr:", "status: merged\npr:"))
        self.assertEqual(got, ["2026-09-06-alpha.md: key `status` appears twice"])

    def test_status_outside_the_vocabulary_fails_naming_the_vocabulary(self):
        _, got = _parse("2026-09-06-alpha.md", _entry(status="shipped"))
        self.assertEqual(len(got), 1, got)
        self.assertIn("2026-09-06-alpha.md: status 'shipped' is not one of approved, candidate", got[0])
        for s in L.STATUSES:
            self.assertEqual(_parse("2026-09-06-alpha.md", _entry(status=s))[1], [], s)
        self.assertIn("approved", L.STATUSES)

    def test_added_and_closed_must_be_iso_dates(self):
        _, got = _parse("2026-09-06-alpha.md", _entry(closed="Sept 6"))
        self.assertEqual(got, ["2026-09-06-alpha.md: closed must be an ISO date (YYYY-MM-DD), got 'Sept 6'"])
        _, got = _parse("2026-09-06-alpha.md", _entry(added="06/09/2026"))
        self.assertEqual(got, ["2026-09-06-alpha.md: added must be an ISO date (YYYY-MM-DD), got '06/09/2026'"])

    def test_dates_must_name_a_real_day(self):
        _, got = _parse("2026-09-06-alpha.md", _entry(closed="2026-02-30"))
        self.assertEqual(got, ["2026-09-06-alpha.md: closed 2026-02-30 is not a calendar date"])
        _, got = _parse("2026-13-45-alpha.md", _entry(added="2026-13-45"))
        self.assertEqual(got, ["2026-13-45-alpha.md: added 2026-13-45 is not a calendar date",
                               "2026-13-45-alpha.md: the filename date 2026-13-45 is not a calendar date"])
        self.assertEqual(_parse("2028-02-29-alpha.md", _entry(added="2028-02-29", closed="2026-12-31"))[1], [])   # a leap day is real

    def test_pr_is_blank_or_an_integer(self):
        self.assertEqual(_parse("2026-09-06-alpha.md", _entry(pr="199"))[1], [])
        self.assertEqual(_parse("2026-09-06-alpha.md", _entry(pr=""))[1], [])
        _, got = _parse("2026-09-06-alpha.md", _entry(pr="#199"))
        self.assertEqual(got, ["2026-09-06-alpha.md: pr must be blank or an integer, got '#199'"])

    def test_tier_is_one_of_the_fork_labels(self):
        # `docs` is upstream's name for tier 0 (renamed from tests-only on 2026-09-08; the old spelling stays accepted)
        for tier in ("fix", "tests-only", "docs", "feature", "major-feature"):
            self.assertEqual(_parse("2026-09-06-alpha.md", _entry(tier=tier))[1], [], tier)
        _, got = _parse("2026-09-06-alpha.md", _entry(tier="huge"))
        self.assertEqual(got, ["2026-09-06-alpha.md: tier 'huge' is not one of fix, tests-only, docs, feature, major-feature"])

    def test_filename_shape(self):
        for bad in ("alpha.md", "2026-09-06-Alpha.md", "2026-09-06-ab.md", "2026-09-06-" + "a" * 61 + ".md", "2026-09-06-alpha.txt"):
            _, got = _parse(bad, _entry(added=bad[:10] if bad[:4].isdigit() else "2026-09-06"))
            self.assertTrue(got and got[0].startswith(f"{bad}: filename must match"), (bad, got))

    def test_filename_date_must_equal_added(self):
        _, got = _parse("2026-09-06-alpha.md", _entry(added="2026-09-05"))
        self.assertEqual(got, ["2026-09-06-alpha.md: added 2026-09-05 does not match the filename date 2026-09-06"])

    def test_conflict_markers_are_named_with_their_line(self):
        text = _entry(body="<<<<<<< HEAD\nours\n=======\ntheirs\n>>>>>>> main\n")
        _, got = _parse("2026-09-06-alpha.md", text)
        self.assertEqual([m.split(":")[1] for m in got if "conflict marker" in m], ["11", "13", "15"], got)

    def test_load_entries_refuses_files_that_are_not_entries(self):
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d)
        (d / "2026-09-06-alpha.md").write_text(_entry(), encoding="utf-8")
        (d / "README.md").write_text("# not an entry\n", encoding="utf-8")
        (d / "notes.txt").write_text("x\n", encoding="utf-8")
        entries, got = L.load_entries(d)
        self.assertEqual([e.name for e in entries], ["2026-09-06-alpha.md"])
        self.assertTrue(any(m.startswith("README.md: filename must match") for m in got), got)
        self.assertTrue(any(m.startswith("notes.txt: only YYYY-MM-DD-<slug>.md entry files") for m in got), got)


class DuplicateTitles(unittest.TestCase):
    """Check 2: two entries whose titles agree on their first 60 characters are one entry twice."""

    def _entries(self, *titles):
        out = []
        for i, t in enumerate(titles):
            e, got = _parse(f"2026-09-0{i + 1}-entry-{i}.md", _entry(f"2026-09-0{i + 1}-entry-{i}.md", title=t))
            self.assertEqual(got, [])
            out.append(e)
        return out

    def test_a_title_written_twice_is_flagged_naming_both_files(self):
        t = "The tags dialog's edits are targeted ops with acked writes, so a late pane cannot revert them"
        got = L.duplicate_problems(self._entries(t, "Unrelated", t + " (rewritten)"))
        self.assertEqual(len(got), 1, got)
        self.assertIn("2026-09-03-entry-2.md: title shares its first 60 characters with 2026-09-01-entry-0.md", got[0])

    def test_titles_that_merely_start_alike_pass(self):
        got = L.duplicate_problems(self._entries(
            "The feed pane repaints only the cards whose inputs changed",
            "The feed pane repaints on every push, twice a second"))
        self.assertEqual(got, [])


FRONT_OK = """# Upstream candidates

Prose about the queue.

Status meanings: """ + " · ".join(f"**{s}**" for s in L.STATUSES) + """.

When offering: work from a branch cut off the upstream default.
"""


class FrontPage(unittest.TestCase):
    """Checks 3 and 4: UPSTREAM.md is prose; it documents the vocabulary exactly."""

    def test_clean_prose_passes(self):
        self.assertEqual(L.front_problems(FRONT_OK), [])

    def test_a_table_row_names_the_line_and_the_import_row_command(self):
        text = FRONT_OK + "\n| A straggler | `x.py` | candidate | appended by a branch cut before the migration |\n"
        got = L.front_problems(text)
        self.assertEqual(len(got), 1, got)
        self.assertTrue(got[0].startswith("UPSTREAM.md:9: a table row; entries live in upstream/ now: run scripts/upstream-ledger.py import --row"), got[0])
        self.assertIn("A straggler", got[0])
        self.assertTrue(got[0].endswith("branch cu…\""), got[0])   # the row is quoted to 60 characters, then an ellipsis
        got = L.front_problems(FRONT_OK + "\n| A straggler — with an em dash | `x.py` | candidate | appended by a branch cut before the migration |\n")
        self.assertIn("A straggler — with an em dash", got[0])     # the em dash and the ellipsis print as themselves,
        self.assertNotIn("\\u", got[0])                            # not as JSON escapes
        short = "| Short | `x.py` | candidate | notes |"
        got = L.front_problems(FRONT_OK + "\n" + short + "\n")
        self.assertTrue(got[0].endswith(f"import --row \"{short}\""), got[0])   # a short row is quoted whole

    def test_a_conflict_marker_is_flagged(self):
        got = L.front_problems(FRONT_OK.replace("Prose about the queue.", "<<<<<<< HEAD\nProse.\n=======\nProse!\n>>>>>>> main"))
        self.assertEqual([m.split(":")[1] for m in got], ["3", "5", "7"], got)

    def test_the_offering_paragraph_must_survive(self):
        got = L.front_problems(FRONT_OK.replace("When offering:", "To offer:"))
        self.assertEqual(got, ["UPSTREAM.md: the `When offering:` paragraph is gone; the offering guidance lives here"])

    def test_an_undocumented_status_is_named(self):
        got = L.front_problems(FRONT_OK.replace("**approved**", "**approved-ish**"))
        self.assertEqual(got, ["UPSTREAM.md: statuses the parser accepts but the prose does not document: approved",
                               "UPSTREAM.md: statuses the prose documents but the parser refuses: approved-ish"])

    def test_a_missing_vocabulary_paragraph_is_named(self):
        got = L.front_problems(FRONT_OK.replace("Status meanings:", "Statuses:"))
        self.assertEqual(got, ["UPSTREAM.md: no `Status meanings:` paragraph with bold status words"])


def _write_set(d):
    """A synthetic ledger covering every rendering rule; returns the loaded entries."""
    long_notes = "N" * 150 + " " + "M" * 100   # 251 characters: the cut lands on the space
    files = {
        "2026-09-01-old-candidate.md": _entry("2026-09-01-old-candidate.md", title="Old candidate"),
        "2026-09-05-new-candidate.md": _entry("2026-09-05-new-candidate.md", title="New candidate", body=long_notes + "\n\nMore.\n"),
        "2026-09-02-the-approved-one.md": _entry("2026-09-02-the-approved-one.md", title="Approved one", status="approved", tier="fix"),
        "2026-09-03-waiting-one.md": _entry("2026-09-03-waiting-one.md", title="Waiting one", status="waiting"),
        "2026-09-03-follow-up-one.md": _entry("2026-09-03-follow-up-one.md", title="Follow-up one", status="follow-up"),
        "2026-09-04-offered-one.md": _entry("2026-09-04-offered-one.md", title="Offered one", status="offered", offered="their PR #960"),
        "2026-09-04-divergent.md": _entry("2026-09-04-divergent.md", title="Divergent one", status="divergence"),
        "2026-09-04-private.md": _entry("2026-09-04-private.md", title="Private one", status="keep-private"),
        "2026-08-20-merged-one.md": _entry("2026-08-20-merged-one.md", title="Merged one", status="merged", offered="their PR #900", closed="2026-08-30"),
        "2026-08-21-landed-one.md": _entry("2026-08-21-landed-one.md", title="Landed one", status="landed"),
        "2026-08-22-resolved-one.md": _entry("2026-08-22-resolved-one.md", title="Resolved one", status="resolved-upstream", closed="2026-08-25"),
        "2026-08-23-declined-one.md": _entry("2026-08-23-declined-one.md", title="Declined one", status="declined"),
        "2026-09-05-piped.md": _entry("2026-09-05-piped.md", title="Toggle `on|off` [bracketed]", where="a `k|v` pair", body="delegate|coordinate\n"),
    }
    for name, text in files.items():
        (d / name).write_text(text, encoding="utf-8")
    entries, got = L.load_entries(d)
    assert got == [], got
    return entries


def _title_of(row):
    """The title text of a rendered row: `[title](upstream/f.md)` or `title ([entry](upstream/f.md))`."""
    c = L.row_cells(row)[0]
    m = re.match(r"^\[(.*)\]\(upstream/[^)]+\)$", c)
    return m.group(1) if m else re.sub(r" \(\[entry\]\(upstream/[^)]+\)\)$", "", c)


def _tables(rendered):
    """The table blocks of a rendering: runs of consecutive `|` lines."""
    out, cur = [], []
    for line in rendered.split("\n"):
        if line.startswith("|"):
            cur.append(line)
        elif cur:
            out.append("\n".join(cur) + "\n")
            cur = []
    if cur:
        out.append("\n".join(cur) + "\n")
    return out


class Render(unittest.TestCase):
    """Check 5: deterministic, ordered, cut, linked, and every table passes the checker."""

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.d)
        self.entries = _write_set(self.d)
        self.rendered = L.render(self.entries)

    def test_two_renders_are_byte_identical(self):
        self.assertEqual(self.rendered, L.render(list(reversed(self.entries))))

    def test_open_table_order_approved_then_candidates_newest_first_then_waiting_follow_up_offered(self):
        open_table = _tables(self.rendered)[0]
        titles = [_title_of(row) for row in open_table.split("\n")[2:] if row]
        # the two 2026-09-05 candidates tie on `added`; the filename breaks the tie (descending)
        self.assertEqual(titles, ["Approved one", "Toggle `on\\|off` [bracketed]", "New candidate", "Old candidate",
                                  "Waiting one", "Follow-up one", "Offered one"])

    def test_closed_statuses_are_collapsed_and_side_statuses_get_their_own_table(self):
        parts = self.rendered.split("<details>")
        self.assertEqual(len(parts), 2, self.rendered)
        self.assertIn("Closed (4): merged, landed, resolved-upstream, declined", parts[1])
        self.assertIn("## Divergence and keep-private (2)", parts[0])
        for t in ("Merged one", "Landed one", "Resolved one", "Declined one"):
            self.assertIn(t, parts[1])
            self.assertNotIn(t, parts[0])
        self.assertIn("| merged — their PR #900 (2026-08-30) |", parts[1])
        self.assertIn("| resolved-upstream (2026-08-25) |", parts[1])
        self.assertIn("| offered — their PR #960 |", parts[0])
        self.assertIn("| approved, fix |", parts[0])

    def test_notes_cell_is_cut_at_200_characters_on_a_word_boundary(self):
        row = next(r for r in self.rendered.split("\n") if "New candidate" in r)
        notes = cells(row)[3].strip()
        self.assertTrue(notes.endswith("…"), notes[-10:])
        self.assertLessEqual(len(notes), 201)
        self.assertEqual(notes, "N" * 150 + "…")

    def test_title_and_where_cells_are_cut_like_notes_and_the_link_survives_the_cut(self):
        long_title = "Long title " + "[bracket] " * 30   # the cut can strip a closing bracket; the link must not break
        (self.d / "2026-09-06-long.md").write_text(_entry("2026-09-06-long.md", title=long_title, where="W" * 300), encoding="utf-8")
        entries, got = L.load_entries(self.d)
        self.assertEqual(got, [])
        row = next(r for r in L.render(entries).split("\n") if "2026-09-06-long.md" in r)
        title, where = L.row_cells(row)[:2]
        self.assertTrue(title.endswith("… ([entry](upstream/2026-09-06-long.md))"), title)
        self.assertLessEqual(len(title), 201 + len(" ([entry](upstream/2026-09-06-long.md))"))
        self.assertEqual(where, "W" * 200 + "…")
        self.assertEqual(problems(_tables(L.render(entries))[0]), [])

    def test_a_cut_never_lands_inside_a_code_span(self):
        text = "word " * 38 + "`a long code span that the cut would otherwise split in two` tail"
        got = L.cut(text)
        self.assertTrue(got.endswith("…"))
        self.assertEqual(got.count("`") % 2, 0, got)
        self.assertLess(len(got), 201)

    def test_every_title_links_to_a_file_that_exists(self):
        links = re.findall(r"\]\(upstream/([^)]+)\)", self.rendered)
        self.assertEqual(len(links), len(self.entries))
        for name in links:
            self.assertTrue((self.d / name).exists(), name)
        with_base = L.render(self.entries, link_base="https://example.invalid/o/r/blob/abc/")
        self.assertIn("](https://example.invalid/o/r/blob/abc/upstream/2026-09-02-the-approved-one.md)", with_base)
        self.assertEqual(L.render(self.entries, link_base="https://example.invalid/o/r/blob/abc"), with_base)   # a missing slash is supplied

    def test_pipes_in_cells_are_escaped_so_every_row_has_four_cells(self):
        row = next(r for r in self.rendered.split("\n") if "bracketed" in r)
        self.assertEqual(len(cells(row)), 4, row)
        self.assertIn("delegate\\|coordinate", row)

    def test_html_in_a_cell_is_escaped_outside_code_spans(self):
        title = "Chains on `logicalParentUuid:<pre-compact leaf>`, a <placeholder> & an ampersand"
        (self.d / "2026-09-06-html.md").write_text(_entry("2026-09-06-html.md", title=title, where="a <b> & `c <d>`"), encoding="utf-8")
        entries, got = L.load_entries(self.d)
        self.assertEqual(got, [])
        row = next(r for r in L.render(entries).split("\n") if "2026-09-06-html.md" in r)
        cell_title, cell_where = L.row_cells(row)[:2]
        self.assertEqual(cell_title, "[Chains on `logicalParentUuid:<pre-compact leaf>`, a &lt;placeholder> &amp; an ampersand](upstream/2026-09-06-html.md)")
        self.assertEqual(cell_where, "a &lt;b> &amp; `c <d>`")
        self.assertEqual(L.escape_cell("x|y `a|b` <c>"), "x\\|y `a\\|b` &lt;c>")

    def test_each_rendered_table_passes_the_checker(self):
        tables = _tables(self.rendered)
        self.assertEqual(len(tables), 3)
        for t in tables:
            self.assertEqual(problems(t), [], t[:200])

    def test_active_prints_the_open_table_only(self):
        active = L.render(self.entries, active=True)
        self.assertEqual(len(_tables(active)), 1)
        self.assertNotIn("<details>", active)
        self.assertNotIn("Merged one", active)

    def test_an_empty_group_renders_none_not_a_header_only_table(self):
        only_open = [e for e in self.entries if e.get("status") in L.OPEN]
        rendered = L.render(only_open)
        self.assertEqual(len(_tables(rendered)), 1)
        self.assertEqual(rendered.count("(none)"), 2)


class SetAndImport(unittest.TestCase):
    """Check 6: `set` touches one header line; `import --row` round-trips a synthetic row."""

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.d)
        self.body = "First paragraph.\n\nSecond paragraph with a `pipe|inside`.\n\n2026-09-06: a dated line.\n"
        self.path = self.d / "2026-09-06-alpha.md"
        self.path.write_text(_entry(body=self.body), encoding="utf-8")

    def test_set_rewrites_one_header_line_and_leaves_the_body_byte_identical(self):
        before = self.path.read_text(encoding="utf-8")
        L.set_key(self.path, "status", "offered")
        after = self.path.read_text(encoding="utf-8")
        diff = [(a, b) for a, b in zip(before.split("\n"), after.split("\n")) if a != b]
        self.assertEqual(diff, [("status: candidate", "status: offered")])
        self.assertTrue(after.endswith("---\n" + self.body))

    def test_set_adds_a_key_the_header_lacks(self):
        self.path.write_text("---\ntitle: T\nstatus: candidate\nwhere: W\nadded: 2026-09-06\n---\n" + self.body, encoding="utf-8")
        L.set_key(self.path, "offered", "their PR #960")
        text = self.path.read_text(encoding="utf-8")
        self.assertIn("added: 2026-09-06\noffered: their PR #960\n---\n", text)
        self.assertTrue(text.endswith("---\n" + self.body))

    def test_set_refuses_unknown_keys_bad_values_and_added(self):
        with self.assertRaises(SystemExit) as cm:
            L.set_key(self.path, "label", "fix")
        self.assertIn("unknown key `label`", str(cm.exception))
        with self.assertRaises(SystemExit) as cm:
            L.set_key(self.path, "status", "shipped")
        self.assertIn("status 'shipped' is not one of", str(cm.exception))
        with self.assertRaises(SystemExit) as cm:
            L.set_key(self.path, "added", "2026-09-07")
        self.assertIn("rename the file", str(cm.exception))
        self.assertEqual(self.path.read_text(encoding="utf-8"), _entry(body=self.body))  # nothing written

    def test_resolve_takes_a_slug_a_filename_or_a_path_and_refuses_an_ambiguous_slug(self):
        self.assertEqual(L.resolve(self.d, "alpha"), self.path)
        self.assertEqual(L.resolve(self.d, "2026-09-06-alpha.md"), self.path)
        self.assertEqual(L.resolve(self.d, str(self.path)), self.path)
        (self.d / "2026-09-07-alpha.md").write_text(_entry("2026-09-07-alpha.md", title="Another alpha"), encoding="utf-8")
        with self.assertRaises(SystemExit) as cm:
            L.resolve(self.d, "alpha")
        self.assertIn("names 2 entries; use the filename: 2026-09-06-alpha.md, 2026-09-07-alpha.md", str(cm.exception))
        with self.assertRaises(SystemExit) as cm:
            L.resolve(self.d, "omega")
        self.assertIn("no entry 'omega'", str(cm.exception))

    ROW = ("| Toggle `on\\|off` on the tab strip | fork PR #321 (`tabtoggle`): `ui/webview/tabs.ts` "
           "| **offered** — their PR #961 (2026-09-06), label `fix` | One paragraph of why, with a `k\\|v` pair. |")

    def test_import_row_produces_an_entry_that_parses_and_round_trips_its_cells(self):
        report, path, ok = L.import_row(self.ROW, self.d, self.d)
        self.assertTrue(ok)
        e, got = L.parse_entry(path.name, path.read_text(encoding="utf-8"), path)
        self.assertEqual(got, [])
        what, where, status, notes = L.entry_cells(self.ROW)
        self.assertEqual((e.get("title"), e.get("where"), e.status_detail, e.notes), (what, where, status, notes))
        self.assertEqual(what, "Toggle `on|off` on the tab strip")   # the table's `\\|` is a bare pipe in the file
        self.assertTrue(notes.endswith("with a `k|v` pair."), notes)
        self.assertNotIn("\\|", path.read_text(encoding="utf-8"))
        row = next(r for r in L.render([e]).split("\n") if "tab strip" in r)
        self.assertEqual(len(L.row_cells(row)), 4, row)   # and the render escapes it again
        self.assertIn("`on\\|off`", row)
        self.assertEqual(e.get("status"), "offered")
        self.assertEqual(e.get("offered"), "their PR #961")
        self.assertEqual(e.get("tier"), "fix")
        self.assertEqual(e.get("pr"), "321")
        self.assertEqual(e.get("closed"), "")   # not terminal
        self.assertTrue(path.name.endswith("-toggle-on-off-on-the-tab-strip.md"), path.name)
        self.assertIn("round-trip: 1 rows, 1 migrated files, diff empty", "\n".join(report))

    def test_import_row_force_is_re_runnable_keyed_on_the_title(self):
        _, first, _ = L.import_row(self.ROW, self.d, self.d)
        os.rename(first, self.d / (first.name[:10] + "-tab-toggle.md"))   # the plan's step 4: a slug renamed once
        L.set_key(self.d / (first.name[:10] + "-tab-toggle.md"), "status", "merged")
        report, second, ok = L.import_row(self.ROW, self.d, self.d, force=True)
        self.assertTrue(ok)
        self.assertEqual(second.name, first.name[:10] + "-tab-toggle.md")
        self.assertEqual(sorted(p.name for p in self.d.glob("*.md")), ["2026-09-06-alpha.md", second.name])
        e, _ = L.parse_entry(second.name, second.read_text(encoding="utf-8"))
        self.assertEqual(e.get("status"), "offered")   # the migration's rule: the cell derives a status, so the cell wins
        self.assertIn("rewrote the existing entry; changed status merged -> offered", report[0])

    def test_import_row_refuses_an_existing_entry_and_names_it(self):
        _, first, _ = L.import_row(self.ROW, self.d, self.d)
        L.set_key(first, "status", "approved")
        before = first.read_text(encoding="utf-8")
        with self.assertRaises(SystemExit) as cm:
            L.import_row(self.ROW.replace("**offered**", "**candidate**"), self.d, self.d)
        msg = str(cm.exception)
        self.assertIn(f"upstream/{first.name} already holds this entry", msg)
        self.assertIn(f"`set {first.stem[11:]} <key> <value>`", msg)
        self.assertIn("--replace", msg)
        self.assertEqual(first.read_text(encoding="utf-8"), before)   # nothing written

    def _entry_someone_acted_on(self):
        """An imported entry the maintainer approved and the upstream session offered, with a dated body line."""
        _, path, _ = L.import_row(self.ROW.replace("**offered** — their PR #961 (2026-09-06), label `fix`", "**candidate**"), self.d, self.d)
        L.set_key(path, "status", "approved")
        L.set_key(path, "offered", "their PR #970")
        with open(path, "a", encoding="utf-8") as f:
            f.write("\n2026-09-08: offered as their PR #970 (branch `tabtoggle-offer`).\n")
        return path

    def test_import_row_replace_keeps_the_set_status_and_the_appended_lines(self):
        path = self._entry_someone_acted_on()
        stale = self.ROW.replace("**offered** — their PR #961 (2026-09-06), label `fix`", "**candidate**").replace("One paragraph of why", "A reworded paragraph")
        report, again, ok = L.import_row(stale, self.d, self.d, replace=True)
        self.assertTrue(ok, report)
        self.assertEqual(again, path)
        e, got = L.parse_entry(path.name, path.read_text(encoding="utf-8"))
        self.assertEqual(got, [])
        self.assertEqual(e.get("status"), "approved")            # the row's `candidate` does not take it back
        self.assertEqual(e.get("offered"), "their PR #970")     # the cell derives none, so the file's stands
        self.assertTrue(e.notes.startswith("A reworded paragraph"), e.notes)   # the first paragraph is the row's
        self.assertEqual(e.status_detail, "**candidate**")
        self.assertIn("\n2026-09-08: offered as their PR #970 (branch `tabtoggle-offer`).\n", e.body)
        self.assertIn("rewrote the existing entry; kept status approved (row: candidate); kept 1 appended body lines", report[0])
        self.assertNotIn("changed", report[0])   # nothing in the header moved

    def test_import_row_force_rewrites_the_entry_from_the_row(self):
        path = self._entry_someone_acted_on()
        stale = self.ROW.replace("**offered** — their PR #961 (2026-09-06), label `fix`", "**candidate**")
        _, again, ok = L.import_row(stale, self.d, self.d, force=True)
        self.assertTrue(ok)
        e, _ = L.parse_entry(path.name, path.read_text(encoding="utf-8"))
        self.assertEqual(e.get("status"), "candidate")
        self.assertNotIn("2026-09-08", e.body)

    def test_a_re_import_keeps_hand_set_header_values_the_cells_do_not_derive(self):
        row = "| Thing | `x.py` | candidate | Notes. |"
        _, path, _ = L.import_row(row, self.d, self.d)
        L.set_key(path, "tier", "tests-only")
        L.set_key(path, "offered", "their PR #970")
        L.set_key(path, "supersedes", "2026-09-01-old.md")
        L.import_row(row, self.d, self.d, force=True)
        e, _ = L.parse_entry(path.name, path.read_text(encoding="utf-8"))
        self.assertEqual((e.get("tier"), e.get("offered"), e.get("supersedes")), ("tests-only", "their PR #970", "2026-09-01-old.md"))
        L.import_row(row.replace("| candidate |", "| **offered** — their PR #971, label `fix` |"), self.d, self.d, force=True)
        e, _ = L.parse_entry(path.name, path.read_text(encoding="utf-8"))
        self.assertEqual((e.get("tier"), e.get("offered")), ("fix", "their PR #971"))   # the cells say, so the cells win

    def test_body_tail_is_what_a_person_appended(self):
        self.assertEqual(L.body_tail("Notes.\n\nStatus detail (migrated from the table): x\n"), "")
        self.assertEqual(L.body_tail("Notes.\n\nStatus detail (migrated from the table): x\n\n2026-09-08: dated.\nMore.\n"), "2026-09-08: dated.\nMore.")
        self.assertEqual(L.body_tail("Status detail (migrated from the table): x\n\n2026-09-08: dated.\n"), "2026-09-08: dated.")
        self.assertEqual(L.body_tail("First.\n\nSecond paragraph.\n"), "Second paragraph.")

    def test_import_row_round_trip_is_scoped_to_the_entry_it_wrote(self):
        neighbour = "| A migrated neighbour | `n.py` | candidate | Its notes. |"
        L.import_row(neighbour, self.d, self.d)   # a migrated-shape entry with a Status detail line
        report, _, ok = L.import_row(self.ROW, self.d, self.d)
        self.assertTrue(ok)
        self.assertIn("round-trip: 1 rows, 1 migrated files, diff empty", report)
        self.assertFalse([l for l in report if "only in the files" in l], report)

    def test_import_row_with_no_status_keyword_is_not_ok_and_the_command_exits_1(self):
        row = "| Thing | `x.py` | **keep as-is — deliberate** | Notes. |"
        report, path, ok = L.import_row(row, self.d, self.d)
        self.assertFalse(ok)
        self.assertTrue(any("required key `status` is blank" in l for l in report), report)
        self.assertTrue(any(l.startswith("the Status cell matched no keyword: run `set thing status <value>`") for l in report), report)
        path.unlink()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = L.main(["--root", str(self.d), "import", "--row", row])
        self.assertEqual(rc, 1, out.getvalue())
        self.assertTrue((self.d / "upstream" / path.name).exists())   # no PATH: the root's upstream/
        with contextlib.redirect_stdout(out):
            rc = L.main(["--root", str(self.d), "import", "--row", "| Fine | `x.py` | candidate | Notes. |"])
        self.assertEqual(rc, 0, out.getvalue())

    def test_import_row_writes_into_the_named_directory_and_refuses_a_second_path(self):
        """`import --row '<row>' <dir>` once bound <dir> to the migration's `source` and wrote under the
        root's upstream/ without a word (2026-09-06)."""
        row = "| Fine | `x.py` | candidate | Notes. |"
        elsewhere = self.d / "elsewhere"
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = L.main(["--root", str(self.d), "import", "--row", row, str(elsewhere)])
        self.assertEqual(rc, 0, out.getvalue())
        self.assertEqual([p.name for p in elsewhere.glob("*.md")], [f"{L.today()}-fine.md"])
        self.assertFalse((self.d / "upstream").exists())
        for argv, want in ((["import", "--row", row, str(elsewhere), str(self.d)], "import --row takes at most one PATH, the entry directory; got 2"),
                           (["import", str(self.d / "UPSTREAM.md")], "import needs <UPSTREAM.md> <dir>, or --row '<row text>' [<dir>]; got 1 PATH"),
                           (["import"], "got 0 PATHs"),
                           (["import", "--replace", str(self.d / "UPSTREAM.md"), str(elsewhere)], "--replace and --force need --row")):
            with self.subTest(argv=argv):
                with contextlib.redirect_stderr(err), self.assertRaises(SystemExit) as cm:
                    L.main(["--root", str(self.d), *argv])
                self.assertEqual(cm.exception.code, 2)
                self.assertIn(want, err.getvalue())
        self.assertEqual([p.name for p in elsewhere.glob("*.md")], [f"{L.today()}-fine.md"])   # the refusals wrote nothing

    NO_KEYWORD_ROW = "| Thing on the strip | `x.py` | **keep as-is — deliberate** | Notes. |"

    def test_a_re_run_after_a_blank_status_is_refused_and_replace_rewrites_in_place(self):
        """A no-keyword row leaves `status` blank, so the entry does not parse. The refusal and the
        rewrite must see it anyway: read strictly it vanished, and a re-run wrote `<slug>-2.md` beside
        it with exit 0 and 'diff empty' (2026-09-06)."""
        _, first, ok = L.import_row(self.NO_KEYWORD_ROW, self.d, self.d)
        self.assertFalse(ok)
        fixed = self.NO_KEYWORD_ROW.replace("**keep as-is — deliberate**", "keep-private — deliberate")
        with self.assertRaises(SystemExit) as cm:
            L.import_row(fixed, self.d, self.d)
        self.assertIn(f"upstream/{first.name} already holds this entry", str(cm.exception))
        self.assertEqual(sorted(p.name for p in self.d.glob("*.md")), ["2026-09-06-alpha.md", first.name])   # nothing written
        report, again, ok = L.import_row(fixed, self.d, self.d, replace=True)
        self.assertTrue(ok, report)
        self.assertEqual(again, first)
        self.assertEqual(sorted(p.name for p in self.d.glob("*.md")), ["2026-09-06-alpha.md", first.name])
        e, got = L.parse_entry(first.name, first.read_text(encoding="utf-8"))
        self.assertEqual(got, [])
        self.assertEqual(e.get("status"), "keep-private")   # the file's was blank, so the row's fills it
        self.assertIn("rewrote the existing entry; changed status (blank) -> keep-private", report[0])
        self.assertFalse([l for l in report if "matched no keyword" in l], report)

    def test_a_migration_re_run_rewrites_a_blank_status_entry_in_place(self):
        (self.d / "UPSTREAM.md").write_text(_doc([self.NO_KEYWORD_ROW]), encoding="utf-8")
        entries = self.d / "upstream"
        name = f"{L.today()}-thing-on-the-strip.md"
        for _ in range(2):   # a first run, and a re-run before anyone set the status
            report, ok = L.import_file(self.d / "UPSTREAM.md", entries, self.d)
            self.assertFalse(ok)
            self.assertEqual([p.name for p in entries.glob("*.md")], [name])
        self.assertTrue(any("rewrote the existing entry" in l and "SET BY HAND" in l for l in report), report)
        self.assertTrue(any(l.endswith("(status blank until set by hand; a re-run rewrites the file in place and keeps the status once set)") for l in report), report)
        L.set_key(entries / name, "status", "keep-private")
        report, ok = L.import_file(self.d / "UPSTREAM.md", entries, self.d)
        self.assertTrue(ok, report)
        self.assertEqual([p.name for p in entries.glob("*.md")], [name])
        self.assertTrue(any("no keyword; kept the file's hand-set keep-private" in l for l in report), report)

    def test_new_and_check_see_a_title_a_broken_entry_carries(self):
        t = "A title the broken entry carries, long enough for the sixty-character prefix rule"
        root = self.d / "root"
        entries = root / "upstream"
        entries.mkdir(parents=True)
        (root / "UPSTREAM.md").write_text(FRONT_OK, encoding="utf-8")
        (entries / "2026-09-05-broken.md").write_text(_entry("2026-09-05-broken.md", title=t, status=""), encoding="utf-8")
        with self.assertRaises(SystemExit) as cm:
            L.new_entry(entries, "again", t + " (rewritten)", "x", added="2026-09-06")
        self.assertIn("upstream/2026-09-05-broken.md already carries this title", str(cm.exception))
        self.assertEqual([p.name for p in entries.glob("*.md")], ["2026-09-05-broken.md"])
        (entries / "2026-09-06-twin.md").write_text(_entry("2026-09-06-twin.md", title=t), encoding="utf-8")
        _, got = L.check(root)
        self.assertEqual(got, ["2026-09-05-broken.md: required key `status` is blank",
                               "2026-09-06-twin.md: title shares its first 60 characters with 2026-09-05-broken.md (one entry in two versions?)"])

    def test_replace_over_a_hand_set_status_with_a_no_keyword_row_gives_no_set_hint(self):
        _, path, _ = L.import_row(self.NO_KEYWORD_ROW, self.d, self.d)
        L.set_key(path, "status", "keep-private")
        report, again, ok = L.import_row(self.NO_KEYWORD_ROW, self.d, self.d, replace=True)
        self.assertTrue(ok, report)
        self.assertEqual(again, path)
        self.assertIn("no keyword; kept the file's hand-set keep-private", report[0])
        self.assertFalse([l for l in report if "before `check` will pass" in l], report)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = L.main(["--root", str(self.d), "import", "--row", self.NO_KEYWORD_ROW, str(self.d), "--replace"])
        self.assertEqual(rc, 0, out.getvalue())
        self.assertNotIn("before `check` will pass", out.getvalue())

    CANDIDATE_ROW = ROW.replace("**offered** — their PR #961 (2026-09-06), label `fix`", "**candidate**")
    TERMINAL_ROW = ROW.replace("**offered** — their PR #961 (2026-09-06), label `fix`", "**merged** — their PR #961 (2026-09-06), label `fix`")

    def test_replace_keeps_every_header_value_the_file_carries_and_force_takes_the_rows(self):
        """The matrix {entry same, entry differs} x {--replace, --force} x {candidate row, terminal row}.
        --replace once protected only `status`: the row's derived offered, closed, tier and pr overwrote
        the file's hand-set values, and the report named the new values without saying one changed, so
        an approved entry ended with a closed date and the wrong upstream PR (2026-09-06)."""
        hand = {"status": "approved", "offered": "their PR #970", "pr": "999", "closed": "2026-09-10", "tier": "tests-only"}
        from_candidate = {"status": "candidate", "offered": "", "pr": "321", "closed": "", "tier": ""}
        from_terminal = {"status": "merged", "offered": "their PR #961", "pr": "321", "closed": "2026-09-06", "tier": "fix"}
        for differs in (False, True):
            for row_name, row, derived in (("candidate", self.CANDIDATE_ROW, from_candidate), ("terminal", self.TERMINAL_ROW, from_terminal)):
                for mode in ("replace", "force"):
                    with self.subTest(entry="differs" if differs else "same", row=row_name, mode=mode):
                        d = Path(tempfile.mkdtemp())
                        self.addCleanup(shutil.rmtree, d)
                        _, path, _ = L.import_row(self.CANDIDATE_ROW, d, d)
                        if differs:
                            for key, value in hand.items():
                                L.set_key(path, key, value)
                            with open(path, "a", encoding="utf-8") as f:
                                f.write("\n2026-09-08: offered as their PR #970 (branch `tabtoggle-offer`).\n")
                        before = hand if differs else from_candidate
                        report, again, ok = L.import_row(row, d, d, **{mode: True})
                        self.assertTrue(ok, report)
                        self.assertEqual(again, path)
                        e, got = L.parse_entry(path.name, path.read_text(encoding="utf-8"))
                        self.assertEqual(got, [])
                        line = report[0]
                        for key in hand:
                            file_value, row_value = before[key], derived[key]
                            if mode == "force":
                                want = row_value or file_value   # the row wins wherever it says something
                            else:
                                want = file_value or row_value   # the file's value stands; the row fills blanks
                            self.assertEqual(e.get(key), want, (key, line))
                            if mode == "replace" and file_value and row_value and file_value != row_value:
                                self.assertIn(f"kept {key} {file_value} (row: {row_value})", line)
                            else:
                                self.assertNotIn(f"kept {key} ", line)
                            if want != file_value:
                                self.assertIn(f"changed {key} {file_value or '(blank)'} -> {want}", line)
                            else:
                                self.assertNotIn(f"changed {key} ", line)
                        if differs:
                            self.assertEqual("2026-09-08: offered" in e.body, mode == "replace")
                            self.assertIn("kept 1 appended body lines" if mode == "replace" else "dropped 1 appended body lines", line)
                        else:
                            self.assertNotIn("appended body lines", line)

    def test_the_rewrite_line_names_each_header_value_it_changed(self):
        """The migration's two documented resets (a pr, a closed date) and any --force rewrite read
        exactly like a rewrite that changed nothing until the line said old -> new (2026-09-06)."""
        _, path, _ = L.import_row(self.ROW, self.d, self.d)
        L.set_key(path, "pr", "143")
        moved = self.ROW.replace("fork PR #321 (`tabtoggle`)", "fork PR #140 (`tabtoggle`)")
        report, _, ok = L.import_row(moved, self.d, self.d, force=True)
        self.assertTrue(ok, report)
        self.assertIn("changed where fork PR #321 (`tabtoggle`): `ui/webview/tabs.ts` -> fork PR #140 (`tabtoggle`): `ui/webview/tabs.ts`", report[0])
        self.assertIn("changed pr 143 -> 140", report[0])
        report, _, _ = L.import_row(moved, self.d, self.d, force=True)
        self.assertIn("(rewrote the existing entry)", report[0])   # a rewrite that changes nothing names nothing
        self.assertNotIn("changed", report[0])

    def test_a_terminal_status_takes_the_first_date_as_closed(self):
        row = "| Thing | `x.py` | ✅ **merged** — their PR #544, 2026-08-22 (merge `782c617a`); came home 2026-08-23 | Notes. |"
        _, path, _ = L.import_row(row, self.d, self.d)
        e, _ = L.parse_entry(path.name, path.read_text(encoding="utf-8"))
        self.assertEqual((e.get("status"), e.get("offered"), e.get("closed")), ("merged", "their PR #544", "2026-08-22"))

    def test_status_derivation_takes_the_earliest_keyword_and_reports_the_plan_order(self):
        self.assertEqual(L.derive_status("**waiting**: gated on the slices above being offered first"), ("waiting", "offered"))
        self.assertEqual(L.derive_status("**landed** — their PR #255 MERGED 2026-08-10"), ("landed", "merged"))
        self.assertEqual(L.derive_status("✅ **CLOSED — all 8 MERGED upstream** (2026-08-15)"), ("merged", "merged"))
        self.assertEqual(L.derive_status("resolved upstream"), ("resolved-upstream", "resolved-upstream"))
        self.assertEqual(L.derive_status("candidate (partial)"), ("candidate", "candidate"))
        self.assertEqual(L.derive_status("**keep as-is — deliberate**"), (None, None))

    def test_a_tier_is_derived_from_the_label_form_so_docs_as_a_word_is_not_one(self):
        # `docs` is both a tier (upstream's name for tier 0, renamed from tests-only) and an ordinary word in a status
        # cell; only the `label \`docs\`` form names the tier, as for fix and feature.
        header, _, _ = L.derive("t", "w", "**offered**, their PR #971, label `docs`", "")
        self.assertEqual((header["status"], header["tier"]), ("offered", "docs"))
        header, _, _ = L.derive("t", "w", "**candidate**: the docs have to land first", "")
        self.assertEqual((header["status"], header["tier"]), ("candidate", ""))

    def test_a_row_with_no_status_keyword_leaves_status_blank_and_says_set_by_hand(self):
        row = "| Thing | `x.py` | **keep as-is — deliberate** | Notes. |"
        report = []
        written, unmatched, _, _ = L.import_rows([(1, row)], self.d, self.d, report)
        self.assertEqual(unmatched, [1])
        self.assertIn("SET BY HAND", report[0])
        _, got = L.parse_entry(written[0].name, written[0].read_text(encoding="utf-8"))
        self.assertEqual(got, [f"{written[0].name}: required key `status` is blank"])

    def test_new_and_set_title_refuse_a_title_an_entry_already_carries(self):
        t = "The tags dialog's edits are targeted ops with acked writes, so a late pane cannot revert them"
        L.new_entry(self.d, "tags-dialog", t, "`ui/webview/tags.ts`", added="2026-09-05")
        with self.assertRaises(SystemExit) as cm:
            L.new_entry(self.d, "tags-again", t + " (rewritten)", "`ui/webview/tags.ts`", added="2026-09-06")
        self.assertIn("upstream/2026-09-05-tags-dialog.md already carries this title", str(cm.exception))
        self.assertIn("`set tags-dialog <key> <value>`", str(cm.exception))
        self.assertFalse((self.d / "2026-09-06-tags-again.md").exists())
        with self.assertRaises(SystemExit) as cm:
            L.set_key(self.path, "title", t + " (second version)")
        self.assertIn("upstream/2026-09-05-tags-dialog.md already carries this title", str(cm.exception))
        self.assertEqual(self.path.read_text(encoding="utf-8"), _entry(body=self.body))   # nothing written
        L.set_key(self.d / "2026-09-05-tags-dialog.md", "title", t + " (its own retitle)")   # an entry may retitle itself
        L.new_entry(self.d, "feed-repaint", "The feed pane repaints on every push, twice a second", "x", added="2026-09-06")   # merely alike passes

    def test_list_refuses_an_unknown_status_naming_the_vocabulary(self):
        (self.d / "upstream").mkdir()
        (self.d / "upstream" / "2026-09-06-alpha.md").write_text(_entry(status="approved"), encoding="utf-8")
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = L.main(["--root", str(self.d), "list", "--status", "aproved"])
        self.assertEqual(rc, 2)
        self.assertEqual(out.getvalue(), "")
        self.assertIn("list: unknown status 'aproved' (known: approved, candidate", err.getvalue())
        with contextlib.redirect_stdout(out):
            rc = L.main(["--root", str(self.d), "list", "--status", "approved,candidate"])
        self.assertEqual(rc, 0)
        self.assertIn('"status": "approved"', out.getvalue())

    def test_new_writes_the_file_and_refuses_a_bad_slug_or_a_second_write(self):
        p = L.new_entry(self.d, "romp-perf", "Kernel perf counters", "`kernel/kernel.py`", pr="199", tier="feature", notes="Why.", added="2026-09-06")
        self.assertEqual(p.name, "2026-09-06-romp-perf.md")
        e, got = L.parse_entry(p.name, p.read_text(encoding="utf-8"))
        self.assertEqual(got, [])
        self.assertEqual((e.get("pr"), e.get("tier"), e.notes), ("199", "feature", "Why."))
        with self.assertRaises(SystemExit):
            L.new_entry(self.d, "romp-perf", "again", "x", added="2026-09-06")
        with self.assertRaises(SystemExit):
            L.new_entry(self.d, "Romp_Perf", "t", "x", added="2026-09-06")


def _git(repo, *args, date=None, check=True):
    """git in a throwaway repository: no user or system config, a fixed identity, an optional fixed date."""
    env = {**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_NOSYSTEM": "1",
           "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid"}
    if date:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = date
    return subprocess.run(["git", "-C", str(repo), *args], check=check, capture_output=True, text=True, env=env)


class AddedDate(unittest.TestCase):
    """`added` is the author date of the first commit whose diff introduced the row; a row first
    written while resolving a merge is found too (`-m`), and a row no commit introduced says so."""

    ROW_D = "| Fourth thing, written in the merge | `d.py` | candidate | Notes. |"

    def _repo(self):
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d)
        front = d / "UPSTREAM.md"
        _git(d, "init", "-q", "-b", "main")

        def commit(rows, msg, date):
            front.write_text(_doc(rows), encoding="utf-8")
            _git(d, "add", "UPSTREAM.md")
            _git(d, "commit", "-q", "-m", msg, date=date)

        commit([ROW_A], "a", "2026-01-10T12:00:00+00:00")
        _git(d, "checkout", "-q", "-b", "side")
        commit([ROW_A, ROW_B], "b", "2026-01-11T12:00:00+00:00")
        _git(d, "checkout", "-q", "main")
        third = ROW_A.replace("A thing", "Third thing")
        commit([ROW_A, third], "c", "2026-01-12T12:00:00+00:00")
        _git(d, "merge", "--no-commit", "--no-ff", "side", check=False)   # conflicts on the appended rows
        commit([ROW_A, ROW_B, third, self.ROW_D], "merge, and a row written only in the resolution", "2026-01-15T12:00:00+00:00")
        return d

    def test_a_plain_commit_a_merge_resolution_and_a_row_git_never_saw(self):
        d = self._repo()
        self.assertEqual(L.added_date(d, ROW_A), ("2026-01-10", "git"))
        self.assertEqual(L.added_date(d, ROW_B), ("2026-01-11", "git"))
        self.assertEqual(L.added_date(d, self.ROW_D), ("2026-01-15", "git"))   # the pickaxe needs -m for this one
        when, how = L.added_date(d, "| Never committed | `n.py` | candidate | Notes. |")
        self.assertEqual(when, L.today())
        self.assertIn("no commit introduced this row", how)

    def test_the_derivation_line_and_the_summary_say_when_the_date_was_guessed(self):
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d)
        (d / "UPSTREAM.md").write_text(_doc([ROW_A, ROW_B]), encoding="utf-8")
        report, ok = L.import_file(d / "UPSTREAM.md", d / "upstream", d)   # d is not a repository: no commit introduced anything
        self.assertTrue(ok, report)
        lines = [l for l in report if l.startswith("000")]
        self.assertEqual(len(lines), 2)
        for l in lines:
            self.assertIn("added = today (no commit introduced this row)", l)
        self.assertIn("2 rows whose first commit the pickaxe could not find (added = today; set the date by hand): 0001, 0002", report)


def _run_git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)


def _is_entry(path):
    return path.startswith("upstream/") and path.endswith(".md")


def _names(where, path):
    """Whether the where: line names the path as a whole token (tests/README.md does not name tests/README.md.bak)."""
    return re.search(r"(?<![\w./-])" + re.escape(path) + r"(?![\w./-])", where or "") is not None


def _where_of(root, entry):
    e, _ = L.parse_entry(Path(entry).name, (Path(root) / entry).read_text(encoding="utf-8"))
    return (e or {}).get("where") or ""


def _touching_commits(root, base, head="HEAD"):
    """{entry: [(commit, subject, [files changed])]} over base..head, for every entry file one of those commits changed and that
    exists at head (a merge commit lists no files of its own, so a batch merge attributes nothing)."""
    touched = {}
    for line in _run_git(root, "log", "--format=%H %s", "%s..%s" % (base, head)).stdout.splitlines():
        sha, _, subject = line.partition(" ")
        files = _run_git(root, "show", "--name-only", "--format=", sha).stdout.split()
        for f in files:
            if _is_entry(f) and (Path(root) / f).exists():
                touched.setdefault(f, []).append((sha, subject, files))
    return touched


def where_line_omissions(root, base, head="HEAD"):
    """[(entry, [files])]: for each entry a commit in base..head touches, the files those commits changed (entries and UPSTREAM.md
    aside) that the entry's where: line does not name as a whole token; then, unless HEAD is main or detached at origin/main, the
    working tree's uncommitted changes (staged, unstaged and untracked: a created test module is the omission round 7 filed twice)
    against the entries it modifies, under one `working tree (...)` row."""
    out = []
    for entry, commits in sorted(_touching_commits(root, base, head).items()):
        where = _where_of(root, entry)
        owed = sorted({f for _, _, files in commits for f in files if not _is_entry(f) and f != "UPSTREAM.md"})
        missing = [f for f in owed if not _names(where, f)]
        if missing:
            out.append((entry, missing))
    branch = _run_git(root, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    on_main = branch == "main" or (branch == "HEAD" and _run_git(root, "rev-parse", "HEAD").stdout == _run_git(root, "rev-parse", "origin/main").stdout)
    if not on_main:
        changed = [l[3:].split(" -> ")[-1] for l in _run_git(root, "status", "--porcelain", "-uall").stdout.splitlines()]
        entries = [c for c in changed if _is_entry(c) and (Path(root) / c).exists()]
        if entries:
            named = " ".join(_where_of(root, e) for e in entries)
            missing = sorted(c for c in changed if not _is_entry(c) and c != "UPSTREAM.md" and not _names(named, c))
            if missing:
                out.append(("working tree (%s)" % ", ".join(entries), missing))
    return out


def round_currency_omissions(root, base, head="HEAD"):
    """[(entry, N)]: for each entry a commit in base..head touches, the highest N among `Review round N` in those commits' subjects
    that the entry's body does not name as `Round N`; an entry whose commits carry no such subject owes nothing."""
    out = []
    for entry, commits in sorted(_touching_commits(root, base, head).items()):
        rounds = [int(m.group(1)) for _, subject, _ in commits for m in re.finditer(r"[Rr]eview round (\d+)", subject)]
        if not rounds:
            continue
        n = max(rounds)
        text = (Path(root) / entry).read_text(encoding="utf-8")
        if not re.search(r"\bRound %d\b" % n, text):
            out.append((entry, n))
    return out


def _answer(state, merged_at=None, closed_at=None, sha=None):
    """What `gh pr view --json state,mergedAt,closedAt,mergeCommit` prints for one PR, as an object."""
    return {"state": state, "mergedAt": merged_at, "closedAt": closed_at,
            "mergeCommit": {"oid": sha} if sha else None}


class FakeGh:
    """The injected runner: answers `gh pr view N -R repo --json ...` from a table and records every
    command it was handed, so a test asserts both the answers' effect and the reads' shape and count."""

    def __init__(self, answers):
        self.answers = answers   # PR number -> the object, or an Exception instance to raise
        self.calls = []

    def __call__(self, cmd):
        self.calls.append(list(cmd))
        n = int(cmd[3])
        a = self.answers[n]
        if isinstance(a, Exception):
            raise a
        return json.dumps(a)


class Stale(unittest.TestCase):
    """Check 8: `stale` reports every offered entry whose PR is no longer open, and nothing else."""

    FOUR = {
        "2026-09-01-open-offer.md": dict(title="Open offer", status="offered", offered="their PR #10"),
        "2026-09-02-merged-offer.md": dict(title="Merged offer", status="offered", offered="their PR #11"),
        "2026-09-03-closed-offer.md": dict(title="Closed offer", status="offered", offered="their PR #12"),
        "2026-09-04-merged-entry.md": dict(title="Merged entry", status="merged", offered="their PR #13", closed="2026-09-05"),
    }
    ANSWERS = {
        10: _answer("OPEN"),
        11: _answer("MERGED", merged_at="2026-09-19T10:09:44Z", closed_at="2026-09-19T10:09:44Z", sha="0123456789abcdef0123456789abcdef01234567"),
        12: _answer("CLOSED", closed_at="2026-09-20T23:04:42Z"),
        13: _answer("MERGED", merged_at="2026-09-05T00:00:00Z", closed_at="2026-09-05T00:00:00Z", sha="fedcba9876543210fedcba9876543210fedcba98"),
    }

    def _entries(self, files):
        out = []
        for name, over in files.items():
            e, got = _parse(name, _entry(name, **over))
            self.assertEqual(got, [], name)
            out.append(e)
        return out

    def test_the_pure_decision_returns_the_merged_and_the_closed_offer_with_their_wording_and_nothing_else(self):
        got = L.stale_rows(self._entries(self.FOUR), self.ANSWERS)
        self.assertEqual(got, [
            "upstream/2026-09-02-merged-offer.md: their PR #11 merged 2026-09-19T10:09:44Z as 012345678, entry still offered",
            "upstream/2026-09-03-closed-offer.md: their PR #12 closed 2026-09-20T23:04:42Z unmerged, entry still offered",
        ])
        # the merged ENTRY names a merged PR and is right to; the open offer is not a row
        self.assertFalse([l for l in got if "merged-entry" in l or "open-offer" in l], got)

    def test_an_offered_field_with_no_pr_number_is_reported_not_skipped(self):
        files = {"2026-09-01-no-number.md": dict(title="No number", status="offered", offered="the maintainer took it onto a branch")}
        got = L.stale_rows(self._entries(files), {})   # nothing was read for it, and nothing had to be
        self.assertEqual(len(got), 1, got)
        self.assertTrue(got[0].startswith("upstream/2026-09-01-no-number.md: stale-unparseable: offered 'the maintainer took it onto a branch' names no PR number"), got[0])
        self.assertTrue(got[0].endswith(", entry still offered"), got[0])
        blank = {"2026-09-01-blank.md": dict(title="Blank", status="offered", offered="")}
        got = L.stale_rows(self._entries(blank), {})
        self.assertEqual(len(got), 1, got)
        self.assertIn("stale-unparseable", got[0])

    def test_a_state_that_is_neither_open_nor_merged_nor_closed_is_stale_too(self):
        files = {"2026-09-01-odd.md": dict(title="Odd", status="offered", offered="their PR #14")}
        got = L.stale_rows(self._entries(files), {14: _answer("DRAFTISH")})
        self.assertEqual(got, ["upstream/2026-09-01-odd.md: their PR #14 state 'DRAFTISH' is not OPEN, entry still offered"])

    def test_offered_number_reads_the_forms_the_entries_use(self):
        for field, want in (("their PR #1883", 1883),
                            ("their PR #994 (commit b40df67a, slice 1)", 994),   # a tail after the number
                            ("their #12", 12),
                            ("", None),
                            ("fork PR #323", None),                                # a fork PR is not an upstream one
                            ("PR 994", None)):
            with self.subTest(field=field):
                e, got = _parse("2026-09-01-field.md", _entry("2026-09-01-field.md", status="offered", offered=field))
                self.assertEqual(got, [])
                self.assertEqual(L.offered_number(e), want)

    def test_repo_from_url_reads_every_spelling_git_uses(self):
        for url in ("https://github.com/example-owner/example-repo.git", "https://github.com/example-owner/example-repo",
                    "https://github.com/example-owner/example-repo/", "git@github.com:example-owner/example-repo.git",
                    "ssh://git@github.com/example-owner/example-repo.git", "  https://github.com/example-owner/example-repo.git\n"):
            with self.subTest(url=url):
                self.assertEqual(L.repo_from_url(url), "example-owner/example-repo")
        self.assertIsNone(L.repo_from_url("no-push://upstream-is-fetch-only"))   # the fork's push sentinel names no repository
        self.assertIsNone(L.repo_from_url(""))

    def _root(self, files, remote="https://github.com/example-owner/example-repo.git"):
        """A ledger root that is a git repository, with an `upstream` remote unless remote is None."""
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d)
        (d / "upstream").mkdir()
        for name, over in files.items():
            (d / "upstream" / name).write_text(_entry(name, **over), encoding="utf-8")
        _git(d, "init", "-q", "-b", "main")
        if remote:
            _git(d, "remote", "add", "upstream", remote)
        return d

    def _run(self, root, runner):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = L.main(["--root", str(root), "stale"], run=runner)
        return rc, out.getvalue(), err.getvalue()

    def test_the_command_exits_1_with_stale_rows_and_reads_each_pr_once(self):
        files = dict(self.FOUR)
        files["2026-09-05-second-closed-offer.md"] = dict(title="Second closed offer", status="offered", offered="their PR #12 (slice 2)")
        d = self._root(files)
        gh = FakeGh(self.ANSWERS)
        rc, out, err = self._run(d, gh)
        self.assertEqual(rc, 1, (out, err))
        lines = out.rstrip("\n").split("\n")
        self.assertEqual(lines[:-1], [
            "upstream/2026-09-02-merged-offer.md: their PR #11 merged 2026-09-19T10:09:44Z as 012345678, entry still offered",
            "upstream/2026-09-03-closed-offer.md: their PR #12 closed 2026-09-20T23:04:42Z unmerged, entry still offered",
            "upstream/2026-09-05-second-closed-offer.md: their PR #12 closed 2026-09-20T23:04:42Z unmerged, entry still offered",
        ])
        self.assertEqual(lines[-1], "stale: 3 stale of 4 offered entries; 3 distinct PRs read from example-owner/example-repo")
        # one read per distinct PR (two entries name #12), none for the merged entry's #13, in the shape gh takes
        self.assertEqual([c[3] for c in gh.calls], ["10", "11", "12"])
        for c in gh.calls:
            self.assertEqual(c[0], L.gh_binary())
            self.assertEqual(c[1:3] + c[4:], ["pr", "view", "-R", "example-owner/example-repo", "--json", "state,mergedAt,closedAt,mergeCommit"])

    def test_the_command_exits_0_when_every_offered_pr_is_open_and_still_prints_the_denominators(self):
        d = self._root(self.FOUR)
        gh = FakeGh({10: _answer("OPEN"), 11: _answer("OPEN"), 12: _answer("OPEN")})
        rc, out, err = self._run(d, gh)
        self.assertEqual(rc, 0, (out, err))
        self.assertEqual(out, "stale: 0 stale of 3 offered entries; 3 distinct PRs read from example-owner/example-repo\n")
        self.assertEqual(err, "")

    def test_the_summary_counts_one_entry_and_one_pr_in_the_singular(self):
        one = {"2026-09-01-lone-offer.md": dict(title="Lone offer", status="offered", offered="their PR #12")}
        rc, out, err = self._run(self._root(one), FakeGh(self.ANSWERS))
        self.assertEqual(rc, 1, (out, err))
        self.assertEqual(out.rstrip("\n").split("\n")[-1], "stale: 1 stale of 1 offered entry; 1 distinct PR read from example-owner/example-repo")
        rc, out, err = self._run(self._root(one), FakeGh({12: _answer("OPEN")}))
        self.assertEqual(rc, 0, (out, err))
        self.assertEqual(out, "stale: 0 stale of 1 offered entry; 1 distinct PR read from example-owner/example-repo\n")

    def test_the_command_exits_2_with_no_upstream_remote_and_reads_nothing(self):
        for remote in (None, "no-push://upstream-is-fetch-only"):
            with self.subTest(remote=remote):
                d = self._root(self.FOUR, remote=remote)
                gh = FakeGh(self.ANSWERS)
                rc, out, err = self._run(d, gh)
                self.assertEqual(rc, 2, (out, err))
                self.assertEqual(out, "")
                self.assertIn("no git remote named `upstream`", err)
                self.assertEqual(gh.calls, [])

    def test_a_gh_failure_exits_2_naming_the_pr_rather_than_passing_it_as_open(self):
        d = self._root(self.FOUR)
        gh = FakeGh({10: _answer("OPEN"), 11: L.GhError("`gh pr view 11` exited 1: could not resolve to a PullRequest"), 12: _answer("OPEN")})
        rc, out, err = self._run(d, gh)
        self.assertEqual(rc, 2, (out, err))
        self.assertEqual(out, "")
        self.assertIn("stale: could not read their PR #11 of example-owner/example-repo: `gh pr view 11` exited 1", err)

    def test_the_command_exits_2_when_the_ledger_does_not_parse(self):
        d = self._root({"2026-09-01-broken.md": dict(title="Broken", status="shipped")})
        gh = FakeGh({})
        rc, out, err = self._run(d, gh)
        self.assertEqual(rc, 2, (out, err))
        self.assertIn("status 'shipped' is not one of", err)
        self.assertIn("fix what `check` reports first", err)
        self.assertEqual(gh.calls, [])

    def test_the_parser_knows_stale_and_its_help_names_gh_and_the_network(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(SystemExit) as cm:
            L.main(["stale", "--help"])
        self.assertEqual(cm.exception.code, 0)
        help_text = out.getvalue()
        self.assertIn("gh", help_text)
        self.assertIn("network", help_text)
        self.assertIn("not part of `check`", help_text)
        with contextlib.redirect_stdout(out), self.assertRaises(SystemExit) as cm:
            L.main(["--help"])
        self.assertIn("stale", out.getvalue())

    def test_run_gh_raises_gh_error_on_a_missing_binary_and_a_non_zero_exit(self):
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d)
        with self.assertRaises(L.GhError) as cm:
            L.run_gh([str(d / "no-such-gh"), "pr", "view", "1"])
        self.assertIn("no-such-gh", str(cm.exception))
        with self.assertRaises(L.GhError) as cm:
            L.run_gh(["sh", "-c", "echo boom >&2; exit 3"])
        self.assertIn("exited 3: boom", str(cm.exception))
        self.assertEqual(L.run_gh(["sh", "-c", "printf ok"]), "ok")


class RealTree(unittest.TestCase):
    """Check 7: the repository's own ledger passes every rule, and its rendering passes the checker."""

    def test_check_returns_no_problems(self):
        entries, got = L.check(ROOT)
        self.assertEqual(got, [], "\n  ".join([""] + got))
        self.assertGreater(len(entries), 100)

    def test_every_rendered_link_targets_an_existing_entry_and_each_table_passes_the_checker(self):
        entries, _ = L.check(ROOT)
        rendered = L.render(entries)
        links = re.findall(r"\]\(upstream/([^)]+)\)", rendered)
        self.assertEqual(len(links), len(entries))
        for name in links:
            self.assertTrue((ROOT / "upstream" / name).exists(), name)
        for t in _tables(rendered):
            self.assertEqual(problems(t), [], t[:200])

    def test_the_repointed_sentence_lives_in_its_entry(self):
        # tests/test_new_session_dir.py asserts this sentence from the entry file; keep the two in step.
        text = (ROOT / "upstream" / "2026-09-04-tab-groups-on-tags.md").read_text(encoding="utf-8")
        self.assertIn("a name that already runs: `/new` re-asserts an explicit `--in`, the picker's op warns instead", text)

    def _base(self):
        for ref in ("origin/main", "main"):
            r = _run_git(ROOT, "merge-base", "HEAD", ref)
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout.strip()
        self.skipTest("no merge base with origin/main or main: the branch's diff is not derivable in this checkout")

    def test_the_where_line_of_an_entry_this_branch_touches_names_every_file_its_commits_change(self):
        """The where: line is DERIVED from the branch's diff (round 7 of fork PR #778, rules-2 and regression-4: the line omitted a test
        module the chain had created, the second such omission on one entry; round 4 ruled the derivation and nothing ran it), scoped to
        the entry (round 8, regression-1): for each entry a commit in base..HEAD touches, the files changed by the commits that touched
        THAT entry must be named on its where: line, so a batch branch's other members, a stacked branch's earlier PR and a peer
        branch's files are never attributed to it (the round-7 form demanded every file of the whole diff be named by some touched
        entry, and would have gone red at the batch head, which is where every fork PR lands). The base is HEAD's merge base with the
        fork's main (origin/main, else main). The working tree is read too, so a run before the commit reads its own edits (every
        uncommitted non-entry change must be named by an entry the tree modifies), except on main or detached at origin/main, where
        uncommitted edits carry no entry to attribute to. With no base (a shallow checkout) the test skips saying so; the local runs
        every round makes are where it holds. A branch that touches no entry has nothing to derive against and passes.

        What the scoping DROPS, disclosed and not widened (round 8 of fork PR #778, correctness-3, ruled in round 9): this pin no longer
        catches the round-7 case that created it. A file created or changed only by commits of this branch that do not themselves touch
        the entry is owed by no where: line, so an entry omitting a test module the chain created in an entry-less commit, the rules-2 and
        regression-4 omission above, passes green here; the shape it misses is a module-only commit beside an entry-only commit, in either
        order, which reads [] (reproduced synthetically and at the head where those findings were filed). The widening proposed with the
        finding (union in the branch's entry-less commits when the branch touches one entry) is not taken: against the fixtures below it
        reds the batch and the stacked branch, since a batch member's non-entry commit is itself in base..HEAD, and correct coverage needs
        reachability from other refs, which a plain checkout does not have. The pin's presence is not the coverage it had at round 7."""
        omissions = where_line_omissions(ROOT, self._base())
        self.assertEqual(omissions, [], "files an entry's own commits change that its where: line does not name (derive the line from "
                         "those commits: git log --format=%H <base>..HEAD -- <entry>, then git show --name-only --format= <commit>):\n"
                         + "\n".join("  %s: %s" % (e, ", ".join(files)) for e, files in omissions))

    def test_the_body_of_an_entry_this_branch_touches_names_its_latest_review_round(self):
        """The entry's prose is derived too (round 8 of fork PR #778, extra7-2: the round-7 paragraph could be deleted with the suite
        green, since the derivation covered the where: line alone): when the subjects of the commits that touched an entry carry
        `Review round N`, the entry's body must name the highest such N as `Round N`. A proxy for currency (the numeral, not the
        paragraph's content); commits whose subjects carry no such token assert nothing, which the synthetic case below pins."""
        omissions = round_currency_omissions(ROOT, self._base())
        self.assertEqual(omissions, [], "entries whose body does not name the latest review round of the commits that touched them:\n"
                         + "\n".join("  %s: the commits say Review round %d, the body never says Round %d" % (e, n, n) for e, n in omissions))


class WhereLineDerivation(unittest.TestCase):
    """The two derivations over a synthetic two-entry repository (round 8 of fork PR #778, regression-1 and extra7-2): a batch of two
    member branches and a stacked branch are green, an omission on one entry's own commit is red and blames that entry, a path is a whole
    token (tests/README.md does not name tests/README.md.bak, and tests/README.md.bak does not name tests/README.md), the working tree
    is read on a branch and not on main, the round numeral is owed only where a commit's subject carries one and is the highest such
    numeral, and an entry deleted at head is not attributed (the round-8 addendum's three cases, from the mutation lens)."""

    ENTRY = "---\ntitle: %s\nstatus: candidate\nwhere: %s\nadded: 2026-01-0%d\n---\n%s\n"

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="romp-ledger-derive-")
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.env = dict(os.environ, GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_NOSYSTEM="1", GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.invalid",
                        GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid", HOME=self.dir)
        self.git("init", "-q")
        self.git("symbolic-ref", "HEAD", "refs/heads/main")
        os.makedirs(os.path.join(self.dir, "upstream"))
        self.write("upstream/2026-01-01-alpha.md", self.ENTRY % ("alpha", "tests/README.md", 1, "Alpha's body."))
        self.write("upstream/2026-01-02-beta.md", self.ENTRY % ("beta", "", 2, "Beta's body."))
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "start")
        self.main = self.git("rev-parse", "HEAD").strip()

    def git(self, *args):
        r = subprocess.run(["git", "-C", self.dir, *args], capture_output=True, text=True, env=self.env)
        self.assertEqual(r.returncode, 0, " ".join(args) + ": " + r.stderr)
        return r.stdout

    def write(self, rel, text):
        path = os.path.join(self.dir, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

    def commit(self, subject, files):
        for rel, text in files.items():
            self.write(rel, text)
        self.git("add", "-A")
        self.git("commit", "-q", "-m", subject)

    def test_a_batch_of_two_members_and_a_stacked_branch_are_green_and_an_omission_blames_its_own_entry(self):
        # member a: names its file; member b: a test module and no entry (round 7's union form blamed alpha for b's file)
        self.git("checkout", "-q", "-b", "a", self.main)
        self.commit("Review round 2: alpha names a.py", {"a.py": "", "upstream/2026-01-01-alpha.md": self.ENTRY % ("alpha", "tests/README.md, a.py", 1, "Alpha's body. Round 2 (a).")})
        self.git("checkout", "-q", "-b", "b", self.main)
        self.commit("member b adds a test", {"tests/test_member.py": ""})
        self.git("checkout", "-q", "-b", "batch/x", self.main)
        self.git("merge", "-q", "--no-ff", "-m", "merge a", "a")
        self.git("merge", "-q", "--no-ff", "-m", "merge b", "b")
        self.assertEqual(where_line_omissions(self.dir, self.main), [])
        self.assertEqual(round_currency_omissions(self.dir, self.main), [])
        # stacked on a: a docs file and no entry
        self.git("checkout", "-q", "-b", "stacked", "a")
        self.commit("a docs follow-up", {"docs/x.md": ""})
        self.assertEqual(where_line_omissions(self.dir, self.main), [])
        # an omission on alpha's own commit is red and names alpha; beta, untouched, is not blamed; a path is a whole token
        self.git("checkout", "-q", "-b", "d", self.main)
        self.commit("Review round 3: alpha grows", {"d.py": "", "tests/README.md.bak": "",
                                                    "upstream/2026-01-01-alpha.md": self.ENTRY % ("alpha", "tests/README.md", 1, "Alpha's body, longer.")})
        self.assertEqual(where_line_omissions(self.dir, self.main), [("upstream/2026-01-01-alpha.md", ["d.py", "tests/README.md.bak"])])
        # and the round numeral: owed on d (Review round 3, the body says nothing), not on b (no such subject)
        self.assertEqual(round_currency_omissions(self.dir, self.main), [("upstream/2026-01-01-alpha.md", 3)])
        self.commit("Review round 3: the body says so", {"upstream/2026-01-01-alpha.md": self.ENTRY % ("alpha", "tests/README.md, d.py, tests/README.md.bak", 1, "Alpha's body. Round 3 (d).")})
        self.assertEqual(where_line_omissions(self.dir, self.main), [])
        self.assertEqual(round_currency_omissions(self.dir, self.main), [])
        self.git("checkout", "-q", "b")
        self.assertEqual(round_currency_omissions(self.dir, self.main), [])

    def test_a_path_is_a_whole_token_in_the_direction_that_matters(self):
        # round 8 addendum (the mutation lens, row 64): the batch fixture above tests the direction a substring check already gets right
        # (where names the shorter path, the commit changes the longer); the filed direction is the reverse, where names
        # tests/README.md.bak and the commit changes tests/README.md, which a substring check reads as named (red under the mutant: [])
        self.git("checkout", "-q", "-b", "tok", self.main)
        self.commit("Review round 2: alpha names the longer path", {"tests/README.md": "changed",
                                                                     "upstream/2026-01-01-alpha.md": self.ENTRY % ("alpha", "tests/README.md.bak", 1, "Alpha's body. Round 2.")})
        self.assertEqual(where_line_omissions(self.dir, self.main), [("upstream/2026-01-01-alpha.md", ["tests/README.md"])])
        self.commit("Review round 2: both named", {"upstream/2026-01-01-alpha.md": self.ENTRY % ("alpha", "tests/README.md.bak, tests/README.md", 1, "Alpha's body. Round 2.")})
        self.assertEqual(where_line_omissions(self.dir, self.main), [])

    def test_the_body_must_name_the_highest_round_of_the_commits_that_touched_the_entry(self):
        # round 8 addendum (the mutation lens, row 68): the batch fixture carries one round per touching set, so highest and any were not
        # told apart; two rounds on one entry, the body naming the lower (red under a `min` mutant and under an any-`Round N` mutant: [])
        self.git("checkout", "-q", "-b", "rounds", self.main)
        self.commit("Review round 2: alpha", {"upstream/2026-01-01-alpha.md": self.ENTRY % ("alpha", "tests/README.md", 1, "Alpha's body. Round 2 (a).")})
        self.commit("Review round 5: alpha again", {"upstream/2026-01-01-alpha.md": self.ENTRY % ("alpha", "tests/README.md", 1, "Alpha's body. Round 2 (a), more.")})
        self.assertEqual(round_currency_omissions(self.dir, self.main), [("upstream/2026-01-01-alpha.md", 5)])
        self.commit("Review round 5: the body says so", {"upstream/2026-01-01-alpha.md": self.ENTRY % ("alpha", "tests/README.md", 1, "Alpha's body. Round 2 (a). Round 5 (b).")})
        self.assertEqual(round_currency_omissions(self.dir, self.main), [])

    def test_an_entry_deleted_at_head_is_not_attributed(self):
        # round 8 addendum (the mutation lens, row 69): a commit that deletes an entry and adds a file blames nothing on the deleted
        # entry, whose where: line no longer exists to read (red under the mutant: the read of a missing file)
        self.git("checkout", "-q", "-b", "gone", self.main)
        self.git("rm", "-q", "upstream/2026-01-02-beta.md")
        self.write("z.py", "")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "Review round 2: beta withdrawn, z added")
        self.assertEqual(where_line_omissions(self.dir, self.main), [])
        self.assertEqual(round_currency_omissions(self.dir, self.main), [])

    def test_the_working_tree_is_read_on_a_branch_and_not_on_main(self):
        self.git("checkout", "-q", "-b", "fresh", self.main)
        self.write("e.py", "")
        self.write("upstream/2026-01-02-beta.md", self.ENTRY % ("beta", "", 2, "Beta's body, edited."))
        self.assertEqual(where_line_omissions(self.dir, self.main), [("working tree (upstream/2026-01-02-beta.md)", ["e.py"])])
        self.write("upstream/2026-01-02-beta.md", self.ENTRY % ("beta", "e.py", 2, "Beta's body, edited."))
        self.assertEqual(where_line_omissions(self.dir, self.main), [])
        self.git("checkout", "-q", "main")
        self.write("upstream/2026-01-02-beta.md", self.ENTRY % ("beta", "", 2, "Beta's body, edited on main."))
        self.assertEqual(where_line_omissions(self.dir, self.main), [], "on main uncommitted edits carry no entry to derive against")


class HostSocketModeWhereLine(unittest.TestCase):
    """upstream/2026-09-18-host-socket-mode.md's `where:` line against the tree and against the PR's diff (round 4 of
    fork PR #814's review, 2026-09-20: regression-3, kernel-6 and regression-2 found the line naming a pin its class no
    longer had, a constant the round then withdrew, and one function twice, the third PR of the night with the same
    defect; the round ruled the line DERIVED from the branch's diff). The line is generated: for each file the diff
    touches, `path (name, name, ...)`, the names being the defs and classes whose bodies the -U0 hunks fall in (a
    `Class.method` when a hunk lies inside one method, the class when it spans more; `text` for a non-Python file),
    segments joined by `; `. Two rules hold it. Every file the PR's diff touches is named: the list below is
    `git diff --name-only <merge-base>..HEAD` at the commit applying round 4's rulings, pasted, since the merge-base is
    not derivable once the branch lands (a later PR that edits the entry re-derives it). And every name the line gives
    for a Python file resolves to a def or class in that file at this head, by ast, so a withdrawn or renamed name reds
    here where the ledger's own `check` (a format check) cannot see it."""

    ENTRY = "upstream/2026-09-18-host-socket-mode.md"
    FILES = ("docs/reference.md", "kernel/host_transport.py", "kernel/judge.py", "kernel/sdk_backend.py", "kernel/session_host.py",
             "tests/README.md", "tests/test_host_transport.py", "tests/test_hosts_path_census.py", "tests/test_judge_scratch_private.py",
             "tests/test_session_host.py", "tests/test_session_host_sdk_pin.py", "tests/test_tempdir_hygiene.py",
             "tests/test_upstream_ledger.py", "upstream/2026-09-18-host-socket-mode.md")
    SEGMENT = re.compile(r"(?P<path>[A-Za-z0-9_./-]+\.(?:py|md)) \((?P<names>[^)]*)\)")

    def _segments(self):
        entry, problems = L.parse_entry(Path(self.ENTRY).name, (ROOT / self.ENTRY).read_text(encoding="utf-8"))
        self.assertEqual(problems, [], problems)
        where = entry.header["where"]
        segs = {m.group("path"): [n.strip() for n in m.group("names").split(",") if n.strip()] for m in self.SEGMENT.finditer(where)}
        self.assertGreater(len(segs), 0, "the where: line has the generated shape: `path (names)` segments")
        return where, segs

    def test_every_file_the_diff_touches_is_named_once(self):
        where, segs = self._segments()
        self.assertEqual(sorted(segs), sorted(self.FILES), "the files the PR's diff touches, each named once, and no other")
        for path in self.FILES:
            self.assertEqual(where.count(path + " ("), 1, "%s named once" % path)

    def test_every_name_the_line_gives_resolves_in_its_file_at_this_head(self):
        import ast
        _, segs = self._segments()
        for path, names in segs.items():
            self.assertTrue((ROOT / path).exists(), path)
            if not path.endswith(".py"):
                self.assertEqual(names, ["text"], "%s: a non-Python file's segment says text" % path)
                continue
            tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
            top = {n.name: n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
            for name in names:
                if name == "module level":
                    continue
                head, _, tail = name.partition(".")
                self.assertIn(head, top, "%s names %s, which %s does not define at top level" % (self.ENTRY, name, path))
                if tail:
                    kids = {c.name for c in top[head].body if isinstance(c, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
                    self.assertIn(tail, kids, "%s names %s, which %s.%s does not define" % (self.ENTRY, name, path, head))
            self.assertEqual(len(names), len(set(names)), "%s: no name twice" % path)


if __name__ == "__main__":
    unittest.main()
