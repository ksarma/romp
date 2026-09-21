#!/usr/bin/env python3
"""The card boards, phase two (plans/card-boards.md): the kernel's board table (_CODE_BOARDS) holds the feed in the one schema
the renderer's ui/webview/board-def.ts holds, checked by _board_check at import; every card the kernel builds carries its
board and its category beside its column; the bell, the phone and the badge read the board's notification set and badge
category instead of a literal. Synthetic fixtures only (the notes-api demo world)."""
import ast
import inspect
import json
from unittest import mock
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
_XDG = tempfile.mkdtemp()
os.environ["XDG_STATE_HOME"] = _XDG
os.environ.pop("ROMP_STATE_DIR", None)
os.makedirs(os.path.join(_XDG, "romp"), exist_ok=True)
open(os.path.join(_XDG, "romp", "session-hosts"), "w").write("off\n")
km = load_source("romp_kernel_card_boards", os.path.join(BIN, "romp-kernel"))
KSRC = open(os.path.join(BIN, "romp-kernel")).read()
TSRC = open(os.path.join(ROOT, "ui", "webview", "board-def.ts")).read()

SID = "11111111-2222-3333-4444-555555555555"     # web


def _feed_def():
    return km._CODE_BOARDS["feed"]


def _card_literals(src=None):
    """The card PRODUCERS, derived from the kernel's source (the fold 3 review, 2026-09-21: a pin that counted the compliant
    STAMPS was green with this fork's eighth family unstamped and turned red on the fix, so the pin is keyed on the producers
    now): every dict literal in kernel.py carrying both an `itemId` key and a `column` key, the two constants every card the
    kernel builds by hand has. Both keys, because either alone sweeps in a non-card: the _notify_prev snapshot entries carry
    a column and no itemId (the notification diary's rows, legitimately without a board), and the app messages (a
    dropCitation, a detailFailed) and the log rows carry an itemId and no column. Returns [(line, the enclosing function's
    name, the literal's constant keys)] in source order; `src` is the kernel's text (KSRC unless a probe hands another)."""
    out, stack = [], [(ast.parse(KSRC if src is None else src), None)]
    while stack:
        node, fn = stack.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            fn = node.name
        if isinstance(node, ast.Dict):
            keys = {k.value for k in node.keys if isinstance(k, ast.Constant) and isinstance(k.value, str)}
            if "itemId" in keys and "column" in keys:
                out.append((node.lineno, fn, keys))
        stack.extend((child, fn) for child in ast.iter_child_nodes(node))
    return sorted(out)


class BoardTable(unittest.TestCase):
    def test_the_feed_entry_is_in_the_schema_and_carries_todays_literals(self):
        d, err = km._board_check(_feed_def(), allow_reserved=True)
        self.assertIsNone(err)
        self.assertEqual([c["id"] for c in d["categories"]], ["working", "needs_input", "completed"])
        self.assertEqual([(c["title"], c["chip"]) for c in d["categories"]], [("Working", "working"), ("Blocked", "blocked"), ("Completed", "completed")])
        self.assertEqual((d["defaultCategory"], d["sort"], d["groupBy"], d["needsYou"]), ("working", {"key": "t", "dir": "asc"}, "session", "needs_input"))
        self.assertEqual(d["notify"], ["needs_input", "completed"])
        self.assertEqual(km._NOTIFY_COLUMNS, ("needs_input", "completed"), "the notify set the snapshot entries are checked against is the table's")
        self.assertIn('_NOTIFY_COLUMNS = tuple(_CODE_BOARDS["feed"]["notify"])', KSRC)

    def test_the_renderer_constant_and_the_kernel_table_name_the_same_feed(self):
        # ui/webview/board-def.ts FEED_BOARD, EVERY member (the 1837 read, low 3: a compare of seven members let id, title,
        # rules, subSorts and order drift, and a kernel-side order of ownerRank passed both suites), read from the source
        # (no TypeScript runtime here): the object literal's comments stripped, its keys quoted, its trailing commas dropped,
        # then json.loads, so the two copies of the one definition are compared as values
        ts = TSRC[TSRC.index("export const FEED_BOARD: Board = {") + len("export const FEED_BOARD: Board = "):]
        ts = ts[:ts.index("\n};") + 2]
        lit = re.sub(r"//[^\n]*", "", ts)                                  # the line comments
        lit = re.sub(r"(?m)^(\s*)([A-Za-z_]\w*)\s*:", r'\1"\2":', lit)       # keys at a line's start
        lit = re.sub(r"([{,]\s*)([A-Za-z_]\w*)\s*:", r'\1"\2":', lit)      # keys inside one-line objects
        lit = re.sub(r",(\s*[}\]])", r"\1", lit)                          # trailing commas
        renderer = json.loads(lit)
        self.assertEqual(sorted(renderer), sorted(_feed_def()), "the same twelve members on both sides")
        self.assertEqual(renderer, _feed_def(), "the renderer's FEED_BOARD and the kernel's _CODE_BOARDS['feed'], member for member")

    def test_the_check_refuses_a_copy_with_one_member_changed_naming_it(self):
        def refused(mut, want):
            d = json.loads(json.dumps(_feed_def()))
            mut(d)
            _, err = km._board_check(d, allow_reserved=True)
            self.assertIsNotNone(err, want)
            self.assertRegex(err, want)
        refused(lambda d: d["categories"][1].__setitem__("chip", "red"), r"chip must be one of working, blocked, completed, neutral")
        refused(lambda d: d["categories"].extend({"id": "c%d" % i, "title": "C", "chip": "neutral"} for i in range(6)), r"1 to 8")
        refused(lambda d: d["categories"][2].__setitem__("id", "working"), r"repeats")
        refused(lambda d: d.__setitem__("defaultCategory", "done"), r"defaultCategory must name")
        refused(lambda d: d.__setitem__("rules", [{"when": {"needsYou": True}, "category": "done"}]), r"rule's category must name")
        refused(lambda d: d.__setitem__("rules", [{"when": {"owner": "x"}, "category": "working"}]), r"predicate has an unknown member 'owner'")
        refused(lambda d: d.__setitem__("sort", {"key": "age", "dir": "asc"}), r"sort\.key must be one of t, session, owner, title")
        refused(lambda d: d.__setitem__("groupBy", "owner"), r'groupBy must be "session" or null')
        refused(lambda d: d.__setitem__("order", ["newestPinned"]), r"order rules must be from ownerRank")
        refused(lambda d: d.__setitem__("notify", ["done"]), r"notify names a category the board does not have")
        refused(lambda d: d.__setitem__("needsYou", "done"), r"needsYou must be one of")
        refused(lambda d: d.__setitem__("kinds", ["card"]), r"kinds must be from")
        refused(lambda d: d.__setitem__("colour", "blue"), r"unknown member 'colour'")
        refused(lambda d: d.__setitem__("id", "Feed"), r"id must match")
        self.assertEqual(km._board_check("feed"), (None, "a board definition must be a JSON object"))
        # the door refuses the reserved id; the constants pass it
        self.assertRegex(km._board_check(_feed_def())[1], r"code-defined board")
        self.assertIn("raise RuntimeError(\"code-defined board", KSRC, "a drifted constant fails at import")

    def test_the_helpers_read_the_board_a_card_names_and_fall_to_the_feed(self):
        self.assertEqual(km._board_notify("feed"), ("needs_input", "completed"))
        self.assertEqual(km._board_notify(None), ("needs_input", "completed"), "a card naming no board is the feed's")
        self.assertEqual(km._board_notify("notes"), ("needs_input", "completed"), "an id this kernel does not know reads as the feed's until phase three's store")
        self.assertEqual(km._board_needs_you("feed"), "needs_input")


class CardsCarryTheirBoard(unittest.TestCase):
    # the card families by their source: each carries "board": "feed" and a category equal to its column literal. Eight in
    # this fork, upstream's seven and the user-todo placeholder (plans/user-todos.md): the fold 3 review (2026-09-21) found
    # the roster adopted from upstream missed the fork's own family, and the pin that counted the seven stamps green with
    # it unstamped, so the roster is checked against the producers the source holds (_card_literals) below
    FAMS = {"_feed_session_entry": '"board": "feed", "category": column,',
            "_provisional_card": '"column": "working", "board": "feed", "category": "working",',
            "_awaiting_card": '"column": "working", "board": "feed", "category": "working",',
            "_blocked_placeholder": '"column": "needs_input", "board": "feed", "category": "needs_input",',
            "_user_todo_placeholder": '"column": "needs_input", "board": "feed", "category": "needs_input",',   # this fork's goal-less todo placeholder
            "build_feed": '"column": "needs_input", "board": "feed", "category": "needs_input",',   # the parked handoff
            "_quarantine_cards": '"column": "needs_input", "board": "feed", "category": "needs_input",',
            "_notice_cards": '"board": "feed", "category": "needs_input" if r.get("needsYou") else "completed",'}

    def test_every_card_family_stamps_board_and_category_beside_column(self):
        for fn, lit in self.FAMS.items():
            self.assertIn(lit, inspect.getsource(getattr(km, fn)), fn)
        # the column expression itself is untouched: the record of the 2026-06-29 and 2026-07-07 rulings its pins hold
        self.assertIn('column = ("needs_input" if (api_block or nid == jauth_top or nid == perm_top', inspect.getsource(km._feed_session_entry))

    def test_every_card_producer_in_the_source_stamps_a_board_and_a_category(self):
        # the census over the PRODUCERS, not over the compliant stamps (a count of what complies cannot see what is missing):
        # a card literal without its board and category fails here by function and line, and the producers the source holds
        # must be the families the table names, one literal each, so a new producer enters the table and a table entry has
        # its producer
        cards = _card_literals()
        unstamped = [(fn, line) for line, fn, keys in cards if not {"board", "category"} <= keys]
        self.assertEqual(unstamped, [], "a card built by hand without its board and category (kernel.py function, line): %r" % unstamped)
        self.assertEqual(sorted(fn for _line, fn, _keys in cards), sorted(self.FAMS),
                         "the card producers in the source and the families the table names differ: %r" % sorted(fn for _l, fn, _k in cards))
        # the shape is known to be able to fail: the same census over a copy of the source with the user-todo placeholder's
        # stamp removed names that function, and over a copy with the stamp on a snapshot entry counts no new producer
        src = KSRC.replace('"what": _USER_TODO_BLOCK_WHAT},\n            "column": "needs_input", "board": "feed", "category": "needs_input",',
                           '"what": _USER_TODO_BLOCK_WHAT},\n            "column": "needs_input",', 1)   # the todo placeholder's own stamp: its `what` precedes it
        self.assertNotEqual(src, KSRC)
        self.assertEqual([fn for _l, fn, keys in _card_literals(src) if not {"board", "category"} <= keys], ["_user_todo_placeholder"])
        self.assertEqual(len(_card_literals(KSRC.replace('"sid": ent["sid"], "column": col,', '"sid": ent["sid"], "column": col, "board": "feed",', 1))), len(cards),
                         "a snapshot entry (no itemId) is not a card, stamped or not")

    def test_the_two_goal_less_placeholders_carry_the_feed_board_executed(self):
        # built, not read: this fork's user-todo placeholder, the family the fold 3 review found unstamped, and its permission
        # twin (a session whose only frontier is what it asked the user for, with no goal to floor)
        s = {"sid": SID, "path": "/nonexistent"}
        ph = km._user_todo_placeholder(s, "web", None, SID, True, 1000,
                                       [{"id": "ut-11111111", "text": "Need the auth-scheme decision", "createdT": 700}])
        self.assertEqual((ph["board"], ph["category"], ph["column"]), ("feed", "needs_input", "needs_input"))
        self.assertEqual(ph["itemId"], "usertodo:" + SID)
        bl = km._blocked_placeholder(s, "web", None, SID, True, 1000, "permission", 900)
        self.assertEqual((bl["board"], bl["category"], bl["column"]), ("feed", "needs_input", "needs_input"))
        self.assertEqual(bl["itemId"], "blocked:" + SID)

    def test_a_notice_card_carries_the_feed_board_and_its_category_executed(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        cwd = root / "notes-api"; cwd.mkdir()
        orig_state, orig_names = km.jd.STATE, km.NAMES
        km.jd._rebind_state(root / "state")
        (km.jd.STATE / "session-hosts").parent.mkdir(parents=True, exist_ok=True)
        (km.jd.STATE / "session-hosts").write_text("off\n")
        km.jd.NAMES.mkdir(parents=True, exist_ok=True)
        (km.jd.NAMES / SID).write_text("web\t%s\t#1EA1EB\t#ffffff\n" % cwd)
        km.NAMES = km.jd.NAMES
        saved = (km._live_map, km._cwd_of, km._mark_views_dirty, km._push_soon)
        km._live_map = lambda: {}
        km._cwd_of = lambda sid: str(cwd) if sid == SID else None
        km._mark_views_dirty = lambda: None
        km._push_soon = lambda: None
        km._NOTICE_MEMO.clear(); km._NOTICE_SWEPT.clear()
        try:
            _, err = km.post_notice(SID, "figure", "A new version of the accuracy figure is ready", producer="figure", now=100)
            self.assertIsNone(err)
            _, err = km.post_notice(SID, "ask", "Pick the retry policy", producer="cli", needs_you=True, now=200)
            self.assertIsNone(err)
            cards = {c["notice"]["key"]: c for c in km._notice_cards(300, set())}
            self.assertEqual((cards["figure"]["board"], cards["figure"]["category"], cards["figure"]["column"]), ("feed", "completed", "completed"))
            self.assertEqual((cards["ask"]["board"], cards["ask"]["category"], cards["ask"]["column"]), ("feed", "needs_input", "needs_input"))
        finally:
            (km._live_map, km._cwd_of, km._mark_views_dirty, km._push_soon) = saved
            km.jd._rebind_state(orig_state); km.NAMES = orig_names
            km._NOTICE_MEMO.clear(); km._NOTICE_SWEPT.clear()
            td.cleanup()


class BellAndBadgeReadTheBoard(unittest.TestCase):
    def test_the_badge_counts_the_boards_needs_you_category_and_falls_to_column_for_an_older_card(self):
        feed = {"asks": [
            {"itemId": "a", "board": "feed", "category": "needs_input", "column": "needs_input"},
            {"itemId": "b", "board": "feed", "category": "needs_input", "column": "needs_input", "provisional": True},   # placeholder churn
            {"itemId": "c", "board": "feed", "category": "working", "column": "working"},
            {"itemId": "d", "board": "feed", "category": "completed", "column": "completed"},
            {"itemId": "e", "column": "needs_input"},                                                                     # an older card: column alone
        ]}
        self.assertEqual(km._needs_you_count(feed), 2)
        src_count = inspect.getsource(km._needs_you_count)
        self.assertTrue('a.get("category", a.get("column")) == _board_needs_you(a.get("board"))' in src_count or ('_ny = _board_needs_you(a.get("board"))' in src_count and 'a.get("category", a.get("column")) != _ny' in src_count), "the count reads the category with the column as the fallback against the board's badge category, in either spelling (this fork binds the helper first and skips with !=)")
        # a board whose badge category is None counts nothing, a key-less card included (the 1837 read, low 2: None == None
        # counted a card carrying neither field); the table has no such board yet, so the helper stands in for one
        keyless = {"asks": [{"itemId": "k", "board": "notes"}, {"itemId": "a", "board": "notes", "category": "needs_input"}]}
        with mock.patch.object(km, "_board_needs_you", lambda board: None):
            self.assertEqual(km._needs_you_count(keyless), 0)
        self.assertEqual(km._needs_you_count(keyless), 1, "the same cards under the feed's fallback: the category-carrying one counts")

    def test_the_notifications_diff_reads_the_boards_notify_set(self):
        src = inspect.getsource(km._feed_notifications_diff)
        self.assertIn('col, sid, ent = a.get("category", a.get("column")), str(a.get("sid") or ""), prev.get(iid)', src,
                      "the diff reads the category with the column as the fallback, the same read as the badge (the 1837 read, low 1)")
        self.assertIn('if col in _board_notify(a.get("board")):', src)
        self.assertIn('needs_you = col == _board_needs_you(a.get("board"))', src, "the notification's words come from the board's badge category, never a literal")
        self.assertNotIn('needs_you = col == "needs_input"', src, "the line 1837 replaced; this fork's todo-floor latch (_ut_floor, the userTodos dedup) keeps its literal, a fork-only presentation of the feed board")
        self.assertNotIn("col in _NOTIFY_COLUMNS", src, "no literal set in the diff; the snapshot's entry check keeps _NOTIFY_COLUMNS")
        self.assertIn("_NOTIFY_COLUMNS", inspect.getsource(km._notify_prev_entry), "the stored snapshot's entries are still checked against the feed's set")


if __name__ == "__main__":
    unittest.main()
