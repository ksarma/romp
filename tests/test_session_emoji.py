#!/usr/bin/env python3
"""A session's tab emoji (the user 2026-09-06): one emoji before the name on the tab, stored as the names
registry's FIFTH tab field beside the name and identity color, validated by ONE kernel helper
(_emoji_check) and written by ONE store write (_set_session_emoji) that three doors share — the tab
menu's setSessionEmoji WS op, POST /emoji (the postal set_emoji tool and `romp emoji`). Synthetic only:
placeholder uuids, TESTHOST paths. The route test drives the REAL Handler over HTTP (the
test_color_route.py pattern)."""
import inspect
import json
import os
import socket
import tempfile
import threading
import time
import types
import unicodedata
import unittest
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.machinery import SourceFileLoader
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")

# Hermetic state BEFORE the loads — they resolve their state root at import time, and only pytest
# runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
SourceFileLoader("romp_event_model", os.path.join(BIN, "romp-event-model")).load_module()
SourceFileLoader("romp_judge", os.path.join(BIN, "romp-judge")).load_module()
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "test-token-DO-NOT-USE")
km = SourceFileLoader("romp_kernel_emoji", os.path.join(BIN, "romp-kernel")).load_module()

# a PRIVATE synthetic sid (the goal-store fixtures rule): still synthetic, never shared with other modules
SID = "3e3e3e3e-0e0e-4e4e-8e8e-e0e0e0e0e0e1"
SID2 = "3e3e3e3e-0e0e-4e4e-8e8e-e0e0e0e0e0e2"

MOON = "\U0001F319"                                  # 🌙 an emoji-presentation code point
THUMBS_TONE = "\U0001F44D\U0001F3FD"                 # 👍🏽 base + skin tone
FAMILY = "\U0001F468‍\U0001F469‍\U0001F467‍\U0001F466"   # 👨‍👩‍👧‍👦 ZWJ sequence
HEART_FIRE = "❤️‍\U0001F525"          # ❤️‍🔥 text-default base + selector + ZWJ
HEART_FIRE_MIN = "❤‍\U0001F525"            # ❤‍🔥 minimally qualified (no selector) — the joiner forces emoji presentation
KEYCAP = "3️⃣"                             # 3️⃣
KEYCAP_MIN = "#⃣"                               # #⃣ minimally qualified keycap
FLAG = "\U0001F1FA\U0001F1F8"                        # 🇺🇸 two regional indicators
ENGLAND = "\U0001F3F4\U000E0067\U000E0062\U000E0065\U000E006E\U000E0067\U000E007F"   # 🏴󠁧󠁢󠁥󠁮󠁧󠁿 tag sequence
KISS = "\U0001F9D1\U0001F3FB‍❤️‍\U0001F48B‍\U0001F9D1\U0001F3FC"   # the longest RGI sequence, 35 bytes
COPYRIGHT_EMOJI = "©️"                     # ©️
SMILEY_EMOJI = "☺️"                        # ☺️
HAIR = "\U0001F9D1‍\U0001F9B0"                  # 🧑‍🦰 a hair component after a joiner
POINT_TONE = "\u261D\U0001F3FD"                     # ☝🏽 a TEXT-default modifier base with a tone (no selector: UTS #51's form)
SCOTLAND = "\U0001F3F4\U000E0067\U000E0062\U000E0073\U000E0063\U000E0074\U000E007F"   # 🏴󠁧󠁢󠁳󠁣󠁴󠁿 the other tag flag
TAGS_GB = "\U000E0067\U000E0062\U000E007F"          # a well-formed tag run + cancel, minus its base


class Validator(unittest.TestCase):
    """The one validator: exactly one emoji as a person picks it, nothing textual, empty clears."""

    ACCEPTED = [MOON, THUMBS_TONE, FAMILY, HEART_FIRE, HEART_FIRE_MIN, KEYCAP, KEYCAP_MIN, FLAG, ENGLAND,
                KISS, COPYRIGHT_EMOJI, SMILEY_EMOJI, HAIR, POINT_TONE, SCOTLAND,
                MOON + "‍" + MOON + "‍" + MOON + "‍" + MOON,   # four joined moons: well-formed, RGI unknown to the tables
                "✅",              # ✅ an emoji-presentation code point in the Dingbats block
                "⌚",              # ⌚ emoji presentation in Misc Technical
                "\U0001FAE9",          # 🫩 Unicode 16.0's newest block row
                "\U0001F9B0"]          # 🦰 a hair component renders as a glyph on its own

    REFUSED = [
        ("a", "not an emoji"),
        ("moon", "not an emoji"),
        ("?", "not an emoji"),
        ("3", "keycap"),                                  # a digit alone is text
        ("#", "keycap"),
        ("©", "text symbol"),                        # © without the emoji selector renders as text
        ("☺", "text symbol"),                        # ☺ likewise
        ("♥", "text symbol"),                        # ♥ likewise
        (MOON + MOON, "one emoji only"),
        (FLAG + FLAG, "one emoji only"),
        (MOON + "x", "not an emoji"),                     # trailing letter
        ("x" + MOON, "not an emoji"),                     # leading letter
        (MOON + " " + MOON, "not an emoji"),              # whitespace inside
        ("\U0001F1FA", "two regional-indicator"),         # half a flag
        ("\U0001F3FD", "skin tone"),                      # a lone skin tone
        ("‍", "not an emoji"),                       # a lone joiner
        ("️", "not an emoji"),                       # a lone selector
        (MOON + "‍", "joiner with nothing after"),
        ("\U0001F3F4\U000E0067\U000E0062", "cancel tag"), # a tag sequence that never ends
        ("\x01", "not an emoji"),
        ("\U0001F600" * 13, "too long"),                  # 52 bytes: over the cap before any parse
        ("\U0001F6D8", "not an emoji"),                   # an unassigned code point inside an emoji block
        # UTS #51, as far as the property tables reach (review 2026-09-06): a tone only on a modifier
        # base and right after it, tags only on the black flag, at most four parts to a ZWJ sequence
        (MOON + "\U0001F3FD", "does not take a skin tone"),          # a tone on a moon: two glyphs
        ("\U0001F680\U0001F3FD", "does not take a skin tone"),      # a tone on a rocket
        ("\U0001F44D\uFE0F\U0001F3FD", "no emoji selector"),       # VS16 between base and tone
        ("\U0001F600" + TAGS_GB, "black flag"),                      # a tag run on a grin
        ("\u2764" + TAGS_GB, "black flag"),                          # a tag run on a text-default heart
        ("‍".join(["\U0001F600"] * 7), "at most 4 parts"),         # seven joined grins, 46 bytes, under the cap
        ("‍".join([MOON] * 5), "at most 4 parts"),
        # a Unicode 16.0 emoji beside junk: the reason quotes the emoji and names the junk, on every
        # interpreter — Python 3.12/3.13's Unicode database (15.0/15.1) calls U+1FAE9 unassigned, and
        # the validator's invisibility test used to defer to it (review round 2, 2026-09-06)
        ("\U0001FAE9x", 'not an emoji: "\U0001FAE9x"'),
        ("x\U0001FADC", 'not an emoji: "x\U0001FADC"'),
        ("\U0001FAE9\U0001F3FD", "does not take a skin tone"),   # a tone on a face with bags under its eyes
        (MOON + "\U0001FAE9", "one emoji only"),
        ("\U0001FAE9" + MOON, "one emoji only"),
        ("\uFEFF\U0001FAE9", 'comes before "\U0001FAE9"'),      # the BOM is the stray, not the emoji
    ]

    def test_accepted_table(self):
        for s in self.ACCEPTED:
            with self.subTest(s=s.encode("unicode_escape").decode()):
                self.assertEqual(km._emoji_check(s), (s, None))

    def test_refused_table_gives_a_one_line_reason(self):
        for s, frag in self.REFUSED:
            with self.subTest(s=s.encode("unicode_escape").decode()):
                v, err = km._emoji_check(s)
                self.assertEqual(v, "", "a refusal stores nothing")
                self.assertIsInstance(err, str)
                self.assertIn(frag, err)
                self.assertNotIn("\n", err, "one line")

    def test_empty_and_whitespace_clear(self):
        for s in ("", " ", "\t", "\n"):
            with self.subTest(s=repr(s)):
                self.assertEqual(km._emoji_check(s), ("", None))

    def test_a_non_string_is_refused_never_a_clear(self):
        # a present-but-null key (json.dumps(None), a JS null), a number, a list: none of them can mean
        # "clear" — only "" does — so the validator names the type instead of coercing (review 2026-09-06)
        for v, kind in ((None, "null"), (7, "a number"), (7.5, "a number"), (True, "a boolean"),
                        (["x"], "a list"), ({"a": 1}, "an object")):
            with self.subTest(v=repr(v)):
                stored, err = km._emoji_check(v)
                self.assertEqual(stored, "")
                self.assertIn("must be text", err or "")
                self.assertIn(kind, err or "")

    def test_an_unpaired_surrogate_is_a_refusal_not_an_exception(self):
        # json.loads('"\\ud83c"') is a str holding a lone surrogate; strict UTF-8 refuses to encode it,
        # and the validator's byte cap encodes — unguarded, POST /emoji answered 500 with a traceback
        for s in ("\ud83c", "\udcf0\udc9f", MOON + "\ud83c", " \ud83cx"):
            with self.subTest(s=s.encode("unicode_escape").decode()):
                stored, err = km._emoji_check(s)
                self.assertEqual(stored, "")
                self.assertIn("not valid text", err)
                self.assertIn("unpaired surrogate", err)
                self.assertRegex(err, r"U\+D[89A-F][0-9A-F]{2}", "the reason names the surrogate code point")
                self.assertNotIn("\n", err)
                err.encode("utf-8")   # the reason itself is sendable

    def test_a_stray_invisible_character_is_named_not_the_emoji(self):
        # a valid emoji plus one invisible neighbor used to be refused as `not an emoji: "😀"` — the
        # visible part quoted as the culprit; the reason now names the stray code point
        grin = "\U0001F600"
        for s, stray in ((grin + "\uFE0E", "U+FE0E"),          # a text-presentation selector (a paste from a document)
                         (grin + "\uFE0F\uFE0F", "U+FE0F"),    # a doubled emoji selector
                         ("\u2764\uFE0F\uFE0F", "U+FE0F"),   # the red heart with a doubled selector
                         (grin + "\u200B", "U+200B"),          # a zero-width space
                         (grin + "\x00", "U+0000"),            # a NUL (reachable through JSON)
                         ("\u200D" + grin, "U+200D"),          # a leading joiner
                         ("\uFEFF" + grin, "U+FEFF")):         # a BOM
            with self.subTest(s=s.encode("unicode_escape").decode()):
                stored, err = km._emoji_check(s)
                self.assertEqual(stored, "")
                self.assertIn("invisible character", err)
                self.assertIn(stray, err, "the stray is named by code point")
                self.assertNotIn("not an emoji", err, "the emoji the user typed is not the culprit")
                self.assertIn("remove it", err)
        self.assertIn("not an emoji", km._emoji_check(grin + "x")[1], "visible junk is still visible junk")

    def test_table_code_points_are_never_invisible_whatever_the_interpreters_unicode_database(self):
        # invisible() fell through to str.isprintable(), which follows the Python release's own Unicode
        # tables (3.12: 15.0, 3.13: 15.1; only 3.14 has 16.0); every Unicode 16.0 emoji the kernel's
        # tables accept was unassigned there, so U+1FAE9 + "x" was refused as 'an invisible character
        # (U+1FAE9) comes before "x"' and no reason ever quoted the emoji. The tables decide: a code
        # point in them is never invisible, so the reason for any of them beside a letter is the same.
        cps = [cp for table in (km._EMOJI_PRESENTATION, km._EMOJI_TEXT_DEFAULT)
               for lo, hi in table for cp in range(lo, hi + 1)]
        self.assertGreater(len(cps), 1000, "the two tables together")
        for cp in cps:
            ch = chr(cp)
            self.assertEqual(km._emoji_check(ch + "x"), ("", 'not an emoji: "%sx"' % ch), "U+%04X" % cp)
        unassigned_here = sorted(cp for cp in cps if not chr(cp).isprintable())
        db = tuple(int(x) for x in unicodedata.unidata_version.split(".")[:2])
        if db < (16, 0):
            self.assertTrue(unassigned_here, "this interpreter's Unicode database (%s) predates the tables, "
                            "so the sweep above exercised the rule" % unicodedata.unidata_version)
        if db[0] == 15:
            self.assertEqual(unassigned_here, [0x1FA89, 0x1FA8F, 0x1FABE, 0x1FAC6, 0x1FADC, 0x1FADF, 0x1FAE9],
                             "the seven emoji code points Unicode 16.0 added are the ones a 15.x database lacks")

    def test_surrounding_whitespace_is_trimmed_not_refused(self):
        self.assertEqual(km._emoji_check(" " + MOON + "\n"), (MOON, None))

    def test_the_stored_value_can_never_carry_a_tab_or_newline(self):
        # the names registry is tab-delimited, one record per line: the grammar admits neither
        self.assertEqual(km._emoji_check(MOON + "\t" + MOON)[0], "")
        self.assertEqual(km._emoji_check(MOON + "\n" + MOON)[0], "")

    def test_the_byte_cap_is_hard_and_covers_every_rgi_sequence(self):
        self.assertEqual(len(KISS.encode("utf-8")), 35, "the longest RGI sequence (Unicode 16.0 emoji-test.txt)")
        self.assertGreaterEqual(km.EMOJI_MAX_BYTES, 35)
        self.assertLessEqual(km.EMOJI_MAX_BYTES, 64)
        over = "\U0001F600" * (km.EMOJI_MAX_BYTES // 4 + 1)
        self.assertIn("too long", km._emoji_check(over)[1])

    def test_refusals_never_echo_an_invisible_character(self):
        for s in ("‍", "️", "\x01", "\U000E0067"):
            with self.subTest(s=s.encode("unicode_escape").decode()):
                err = km._emoji_check(s)[1]
                self.assertIn("an invisible character", err)
                self.assertNotIn(s, err)


class Store(unittest.TestCase):
    """The fifth tab field: written only while set, preserved by every other writer of the record."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.names = Path(self.tmp) / "names"
        self.names.mkdir()
        self._saved = (km.NAMES, km.jd.STATE)
        km.NAMES = self.names
        km.jd.STATE = Path(self.tmp) / "state"
        km._pal_cache.update({"name": km.pal.DEFAULT, "mt": None})

    def tearDown(self):
        km.NAMES, km.jd.STATE = self._saved
        km._pal_cache.update({"name": km.pal.DEFAULT, "mt": None})

    def _line(self, sid=SID):
        return (self.names / sid).read_text()

    def test_set_writes_the_fifth_field_and_clear_drops_it(self):
        (self.names / SID).write_text("web\t/proj/TESTHOST/app\t#1EA1EB\twhite\n")
        self.assertTrue(km._set_session_emoji(SID, MOON))
        self.assertEqual(self._line(), "web\t/proj/TESTHOST/app\t#1EA1EB\twhite\t" + MOON + "\n")
        self.assertEqual(km._name_emoji(SID), MOON)
        self.assertEqual(km._name_of(SID), "web")
        self.assertEqual(km._name_color(SID), {"bg": "#1EA1EB", "fg": "#ffffff"})
        self.assertTrue(km._set_session_emoji(SID, ""))
        self.assertEqual(self._line(), "web\t/proj/TESTHOST/app\t#1EA1EB\twhite\n",
                         "a cleared record is byte-identical to the four-field shape")
        self.assertEqual(km._name_emoji(SID), "")

    def test_a_colorless_record_gets_a_color_before_its_emoji(self):
        # the contract (review 2026-09-06): a FIVE-field record always carries all four identity fields —
        # `name\tcwd\t\t\t<emoji>` is a shape bash's IFS-tab reads folded into bg=<emoji>. A record with
        # no color (a pre-color two-field entry, a Codex launch-error entry) is colored the way a launch
        # would color it, through the kernel's own picker, before the fifth field is added.
        picked = []
        saved = km._pick_identity_color
        km._pick_identity_color = lambda: (picked.append(1), ("#1EA1EB", "white"))[1]
        try:
            (self.names / SID).write_text("web\t/proj/TESTHOST/app\n")      # a pre-color record: two fields
            self.assertTrue(km._set_session_emoji(SID, MOON))
            self.assertEqual(self._line().rstrip("\n").split("\t"), ["web", "/proj/TESTHOST/app", "#1EA1EB", "white", MOON])
            self.assertEqual(km._identity_of(SID), ("#1EA1EB", "white"))
            self.assertEqual(len(picked), 1)
            (self.names / SID2).write_text("api\t/proj/TESTHOST/svc\t\t\n")   # a Codex launch-error record
            self.assertTrue(km._set_session_emoji(SID2, FLAG))
            self.assertEqual(self._line(SID2).rstrip("\n").split("\t"), ["api", "/proj/TESTHOST/svc", "#1EA1EB", "white", FLAG])
            # a colored record keeps its color; a clear on a colorless record picks none
            self.assertTrue(km._set_session_emoji(SID2, ""))
            (self.names / SID).write_text("web\t/proj/TESTHOST/app\n")
            self.assertTrue(km._set_session_emoji(SID, ""))
            self.assertEqual(self._line().rstrip("\n").split("\t"), ["web", "/proj/TESTHOST/app", "", ""])
            self.assertEqual(len(picked), 2, "the picker runs only when an emoji lands on a colorless record")
        finally:
            km._pick_identity_color = saved

    def test_a_rename_racing_an_emoji_set_loses_neither(self):
        # four kernel writers read-edit-publish names/<sid> on independent threads; without one lock the
        # loser's whole-line write erased the winner's field (a rename undone by set_emoji, or the emoji
        # gone). Force the interleave: the rename's publish is held open while the emoji set starts.
        (self.names / SID).write_text("web\t/proj/TESTHOST/app\t#1EA1EB\twhite\n")
        real_write = km._atomic_write
        renaming = threading.Event()
        rename_thread = []

        def slow_write(path, text, mode=None):
            if threading.get_ident() in rename_thread:
                renaming.set()          # the emoji set starts NOW, inside the rename's span
                time.sleep(0.3)
            return real_write(path, text, mode)

        km._atomic_write = slow_write
        try:
            def rename():
                rename_thread.append(threading.get_ident())
                km._set_name(SID, "api")
            t1 = threading.Thread(target=rename)
            t2 = threading.Thread(target=lambda: (renaming.wait(5), km._set_session_emoji(SID, MOON)))
            t1.start(); t2.start(); t1.join(10); t2.join(10)
        finally:
            km._atomic_write = real_write
        self.assertTrue(renaming.is_set(), "the interleave was forced")
        self.assertEqual(self._line().rstrip("\n").split("\t"), ["api", "/proj/TESTHOST/app", "#1EA1EB", "white", MOON],
                         "both writes survive: the second waited for the first's span to close")
        self.assertIsInstance(km._NAMES_LOCK, type(threading.RLock()))

    def test_missing_record_is_false(self):
        self.assertFalse(km._set_session_emoji(SID2, MOON))
        self.assertFalse((self.names / SID2).exists(), "nothing is minted for an unknown session")

    def test_no_emoji_reads_as_empty(self):
        (self.names / SID).write_text("web\t/proj/TESTHOST/app\t#1EA1EB\twhite\n")
        self.assertEqual(km._name_emoji(SID), "")
        self.assertEqual(km._name_emoji(SID2), "", "no record at all")

    def test_recolor_preserves_the_emoji(self):
        (self.names / SID).write_text("web\t/proj/TESTHOST/app\t#1EA1EB\twhite\t" + MOON + "\n")
        self.assertTrue(km._set_session_color(SID, "#54B204"))
        self.assertEqual(self._line().rstrip("\n").split("\t"),
                         ["web", "/proj/TESTHOST/app", "#54B204", "black", MOON])

    def test_dead_tab_rename_preserves_the_emoji(self):
        (self.names / SID).write_text("web\t/proj/TESTHOST/app\t#1EA1EB\twhite\t" + MOON + "\n")
        km._set_name(SID, "api")
        self.assertEqual(self._line().rstrip("\n").split("\t"),
                         ["api", "/proj/TESTHOST/app", "#1EA1EB", "white", MOON])

    def test_palette_switch_preserves_the_emoji(self):
        pb, pf = km.pal.colors("romp"), km.pal.fgs("romp")
        (self.names / SID).write_text("web\t/proj/TESTHOST/app\t%s\t%s\t%s\n" % (pb[0], pf[0], MOON))
        (self.names / SID2).write_text("api\t/proj/TESTHOST/svc\t%s\t%s\n" % (pb[1], pf[1]))
        saved = (km._send_to_app, km._mark_views_dirty, km._write_palette_mirror)
        km._send_to_app = lambda *a, **k: None
        km._mark_views_dirty = lambda: None
        km._write_palette_mirror = lambda: None
        try:
            self.assertTrue(km._set_palette("phase"))
        finally:
            km._send_to_app, km._mark_views_dirty, km._write_palette_mirror = saved
        nb, nf = km.pal.colors("phase"), km.pal.fgs("phase")
        self.assertEqual(self._line().rstrip("\n").split("\t"), ["web", "/proj/TESTHOST/app", nb[0], nf[0], MOON])
        self.assertEqual(self._line(SID2).rstrip("\n").split("\t"), ["api", "/proj/TESTHOST/svc", nb[1], nf[1]],
                         "a record without an emoji keeps four fields")

    def test_the_four_field_line_helper_never_emits_a_trailing_empty_field(self):
        self.assertEqual(km._names_line(["a", "b", "c", "d", ""]), "a\tb\tc\td\n")
        self.assertEqual(km._names_line(["a", "b"]), "a\tb\t\t\n")
        self.assertEqual(km._names_line(["a", "b", "c", "d", MOON]), "a\tb\tc\td\t" + MOON + "\n")


class BackendWritersCarryTheField(unittest.TestCase):
    """The two backend-side writers of names/<sid> (an SDK rename/move/revive, a Codex rename) rewrite
    the first four fields; the fifth must ride along by default."""

    def test_sdk_write_name_carries_an_existing_emoji_and_can_clear_it(self):
        import sys
        sb = sys.modules.get("romp_sdk_backend") or SourceFileLoader(
            "romp_sdk_backend_emoji", os.path.join(BIN, "romp_sdk_backend.py")).load_module()
        d = Path(tempfile.mkdtemp())
        sb.write_name(d, SID, "web", "/proj/TESTHOST/app", "#1EA1EB", "white")
        self.assertEqual((d / "names" / SID).read_text(), "web\t/proj/TESTHOST/app\t#1EA1EB\twhite\n")
        sb.write_name(d, SID, "web", "/proj/TESTHOST/app", "#1EA1EB", "white", emoji=MOON)
        self.assertEqual((d / "names" / SID).read_text(), "web\t/proj/TESTHOST/app\t#1EA1EB\twhite\t" + MOON + "\n")
        sb.write_name(d, SID, "api", "/proj/TESTHOST/app", "#1EA1EB", "white")     # a rename: no emoji arg
        self.assertEqual((d / "names" / SID).read_text(), "api\t/proj/TESTHOST/app\t#1EA1EB\twhite\t" + MOON + "\n",
                         "the default carries the stored emoji forward")
        sb.write_name(d, SID, "api", "/proj/TESTHOST/app", "#1EA1EB", "white", emoji="")
        self.assertEqual((d / "names" / SID).read_text(), "api\t/proj/TESTHOST/app\t#1EA1EB\twhite\n",
                         "an explicit empty string clears")

    def test_codex_write_name_carries_an_existing_emoji(self):
        import sys
        cb = sys.modules.get("romp_codex_backend") or SourceFileLoader(
            "romp_codex_backend_emoji", os.path.join(os.path.dirname(HERE), "kernel", "codex_backend.py")).load_module()
        tmp = Path(tempfile.mkdtemp())
        be = cb.CodexBackend(tmp, client_factory=lambda: None, log=lambda m: None)
        (tmp / "names").mkdir(exist_ok=True)
        (tmp / "names" / SID).write_text("web\t/proj/TESTHOST/app\t#1EA1EB\twhite\t" + MOON + "\n")
        s = cb._Session(SID, "thread-1111", "api", "/proj/TESTHOST/app")
        be._write_name(s)                                  # a rename's rewrite: colors from the record
        self.assertEqual((tmp / "names" / SID).read_text(), "api\t/proj/TESTHOST/app\t#1EA1EB\twhite\t" + MOON + "\n")
        be._write_name(s, "#54B204", "black")              # a recolor's rewrite
        self.assertEqual((tmp / "names" / SID).read_text(), "api\t/proj/TESTHOST/app\t#54B204\tblack\t" + MOON + "\n")
        (tmp / "names" / SID).write_text("web\t/proj/TESTHOST/app\t#1EA1EB\twhite\n")
        be._write_name(s)
        self.assertEqual((tmp / "names" / SID).read_text(), "api\t/proj/TESTHOST/app\t#1EA1EB\twhite\n",
                         "a record without an emoji keeps four fields")
        self.assertEqual(sorted(f.name for f in (tmp / "names").iterdir()), [SID], "no staging file leaks")


class Frames(unittest.TestCase):
    """The emoji reaches every dashboard on the pushes the name and color already ride."""

    def test_tab_meta_and_the_session_frame_carry_it(self):
        ksrc = Path(BIN, "romp-kernel").read_text()
        self.assertEqual(ksrc.count('"emoji": _name_emoji(s["sid"])'), 3,
                         "all three tab_meta builders (the pusher, the per-session push, the tabOrder frame)")
        self.assertIn('"emoji": _name_emoji(sid),', inspect.getsource(km.build_session))
        self.assertIn('"emoji": _name_emoji(sid),', inspect.getsource(km._session_rows),
                      "GET /sessions rows carry it for `romp emoji <session>`")

    def test_the_ws_op_confirms_or_warns_through_the_one_validator(self):
        ksrc = Path(BIN, "romp-kernel").read_text()
        self.assertIn('msg.get("type") == "setSessionEmoji" and msg.get("id") and "emoji" in msg', ksrc)
        i = ksrc.index('msg.get("type") == "setSessionEmoji"')
        block = ksrc[i:i + 1400]
        self.assertIn('emoji, err = _emoji_check(msg.get("emoji"))', block)
        self.assertIn('{"type": "emojiSet", "id": str(msg["id"]), "emoji": emoji}', block)
        self.assertIn('{"type": "warn", "text": err}', block)
        self.assertIn("_mark_views_dirty()", block)


    def test_the_intent_and_doc_surfaces_name_the_op(self):
        root = Path(os.path.dirname(HERE))
        self.assertIn('"setSessionEmoji"', (root / "vscode-extension" / "src" / "pipe-intent.ts").read_text(),
                      "the VS Code pipe holds it across a reconnect like setSessionColor")
        self.assertIn("setSessionEmoji", (root / "docs" / "reference.md").read_text())
        self.assertIn("set_emoji", (root / "docs" / "reference.md").read_text())
        self.assertIn("romp emoji", (root / "docs" / "guide.md").read_text())

class EmojiRoute(unittest.TestCase):
    """POST /emoji: the door `romp emoji` and the postal set_emoji tool share."""

    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), km.Handler)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.names = Path(self.tmp) / "names"
        self.names.mkdir()
        self._saved = (km.NAMES, km.jd.STATE, km._tmux_sessions, km._live_names, km._mark_views_dirty,
                       km._host_for_sid, km._remote_forward_status, km._demand_redial)
        km.NAMES = self.names
        km.jd.STATE = Path(self.tmp) / "state"
        km._tmux_sessions = lambda: {}
        km._live_names = lambda tm: {"web": SID}
        km._host_for_sid = lambda sid: None
        self.dirty = []
        km._mark_views_dirty = lambda: self.dirty.append(1)
        self.redials = []
        km._demand_redial = lambda host, kind: self.redials.append((host, kind))

    def tearDown(self):
        (km.NAMES, km.jd.STATE, km._tmux_sessions, km._live_names, km._mark_views_dirty,
         km._host_for_sid, km._remote_forward_status, km._demand_redial) = self._saved

    def _post(self, body):
        # km.TOKEN, not os.environ (test_color_route.py has the collection-order story)
        req = urllib.request.Request(
            "http://127.0.0.1:%d/emoji" % self.port, data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json", "X-Romp-Token": km.TOKEN})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode() or "{}")

    def test_live_name_sets_the_fifth_field_and_marks_views_dirty(self):
        (self.names / SID).write_text("web\t/proj/TESTHOST/app\t#1EA1EB\twhite\n")
        st, r = self._post({"target": "web", "emoji": MOON})
        self.assertEqual(st, 200)
        self.assertEqual(r, {"ok": True, "id": SID, "emoji": MOON})
        self.assertEqual((self.names / SID).read_text(), "web\t/proj/TESTHOST/app\t#1EA1EB\twhite\t" + MOON + "\n")
        self.assertTrue(self.dirty, "the dashboards' repaint signal — the strip follows the push, no polling")

    def test_a_sid_target_labels_a_dormant_session(self):
        (self.names / SID2).write_text("worker\t/proj/TESTHOST/svc\t#1EA1EB\twhite\n")
        st, r = self._post({"target": SID2, "emoji": FLAG})
        self.assertEqual(r, {"ok": True, "id": SID2, "emoji": FLAG})
        self.assertEqual(km._name_emoji(SID2), FLAG)

    def test_the_value_is_trimmed_before_it_is_stored(self):
        (self.names / SID).write_text("web\t/proj/TESTHOST/app\t#1EA1EB\twhite\n")
        st, r = self._post({"target": "web", "emoji": " " + MOON + " "})
        self.assertEqual(r.get("emoji"), MOON)
        self.assertEqual(km._name_emoji(SID), MOON)

    def test_empty_clears_and_a_missing_key_is_a_400_never_a_silent_clear(self):
        (self.names / SID).write_text("web\t/proj/TESTHOST/app\t#1EA1EB\twhite\t" + MOON + "\n")
        st, r = self._post({"target": "web"})
        self.assertEqual(st, 400)
        self.assertEqual(km._name_emoji(SID), MOON, "a body without the key changes nothing")
        st, r = self._post({"target": "web", "emoji": ""})
        self.assertEqual(r, {"ok": True, "id": SID, "emoji": ""})
        self.assertEqual((self.names / SID).read_text(), "web\t/proj/TESTHOST/app\t#1EA1EB\twhite\n")
        self.assertEqual(len(self.dirty), 1)

    def test_a_refusal_carries_the_validators_reason_and_writes_nothing(self):
        (self.names / SID).write_text("web\t/proj/TESTHOST/app\t#1EA1EB\twhite\t" + MOON + "\n")
        for bad, frag in (("moon", "not an emoji"), (MOON + MOON, "one emoji only"), ("©", "text symbol")):
            with self.subTest(bad=bad):
                st, r = self._post({"target": "web", "emoji": bad})
                self.assertEqual(st, 200)
                self.assertFalse(r.get("ok"))
                self.assertIn(frag, r.get("error") or "")
        self.assertEqual(km._name_emoji(SID), MOON, "the old value stands")
        self.assertFalse(self.dirty, "a refusal repaints nothing")

    def test_an_unknown_target_and_a_missing_record_are_loud(self):
        st, r = self._post({"target": "ghost", "emoji": MOON})
        self.assertFalse(r.get("ok"))
        self.assertIn("no live session named", r.get("error") or "")
        st, r = self._post({"target": SID2, "emoji": MOON})       # a sid nobody has a record for
        self.assertFalse(r.get("ok"))
        self.assertIn("no names record", r.get("error") or "")
        st, r = self._post({"emoji": MOON})
        self.assertEqual(st, 400)

    def test_a_remote_sid_forwards_to_its_own_kernel_and_relays_the_verdict(self):
        forwarded = []
        km._host_for_sid = lambda sid: {"host": "gpu1", "local_port": 1, "token": "t"} if sid == SID2 else None
        km._remote_forward_status = lambda r, path, body: (forwarded.append((r["host"], path, body)),
                                                          (200, {"ok": False, "error": "one emoji only"}))[1]
        st, r = self._post({"target": SID2, "emoji": MOON})
        self.assertEqual(forwarded, [("gpu1", "/emoji", {"target": SID2, "emoji": MOON})])
        self.assertEqual(r, {"ok": False, "error": "one emoji only"}, "the remote's own verdict rides back")
        km._remote_forward_status = lambda r, path, body: (0, None)
        st, r = self._post({"target": SID2, "emoji": MOON})
        self.assertFalse(r.get("ok"))
        self.assertIn("did not answer", r.get("error") or "")
        self.assertIn("gpu1", r.get("error") or "", "the message names the host, like its /send and /end siblings")

    def test_an_older_remote_kernel_without_the_route_is_named_as_version_skew(self):
        # a remote on a release before this route answers POST /emoji with do_POST's 404 fallthrough: it
        # ANSWERED, so "did not answer" sent the user to check a healthy tunnel (review 2026-09-06). The
        # REAL forward runs here against a fake old remote; only the remotes map is stubbed.
        seen = []

        class OldRemote(BaseHTTPRequestHandler):
            def do_POST(self):
                seen.append((self.path, self.rfile.read(int(self.headers.get("Content-Length") or 0))))
                body = b"not found"
                self.send_response(404); self.send_header("Content-Type", "text/plain")
                self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

            def log_message(self, *a):
                pass

        old = ThreadingHTTPServer(("127.0.0.1", 0), OldRemote)
        threading.Thread(target=old.serve_forever, daemon=True).start()
        try:
            km._host_for_sid = lambda sid: {"host": "gpu1", "local_port": old.server_address[1], "token": "t"} if sid == SID2 else None
            st, r = self._post({"target": SID2, "emoji": MOON})
        finally:
            old.shutdown()
        self.assertEqual(st, 200)
        self.assertFalse(r.get("ok"))
        self.assertIn("predates tab emoji", r.get("error") or "")
        self.assertIn("gpu1", r.get("error") or "")
        self.assertNotIn("did not answer", r.get("error") or "")
        self.assertEqual([p for p, _ in seen], ["/emoji?token=t"], "the old kernel received the call")
        self.assertEqual(json.loads(seen[0][1]), {"target": SID2, "emoji": MOON})
        self.assertEqual(self.redials, [], "an answer is never a tunnel fault")
        # a DEAD port is the other case, and stays the other message — with a redial demanded
        s = socket.socket(); s.bind(("127.0.0.1", 0)); dead_port = s.getsockname()[1]; s.close()
        km._host_for_sid = lambda sid: {"host": "gpu1", "local_port": dead_port, "token": "t"} if sid == SID2 else None
        st, r = self._post({"target": SID2, "emoji": MOON})
        self.assertIn("did not answer", r.get("error") or "")
        self.assertIn("gpu1", r.get("error") or "")
        self.assertEqual(self.redials, [("gpu1", "refused")])

    def test_a_non_string_emoji_is_a_400_never_a_clear(self):
        # a present-but-null key is a malformed body; before this it cleared and answered ok (review)
        (self.names / SID).write_text("web\t/proj/TESTHOST/app\t#1EA1EB\twhite\t" + MOON + "\n")
        for v in (None, 5, ["x"], {"a": 1}, True):
            with self.subTest(v=repr(v)):
                st, r = self._post({"target": "web", "emoji": v})
                self.assertEqual(st, 400)
                self.assertFalse(r.get("ok"))
                self.assertIn("must be a string", r.get("error") or "")
        self.assertEqual(km._name_emoji(SID), MOON, "nothing changed")
        self.assertFalse(self.dirty)

    def test_an_unpaired_surrogate_is_a_refusal_with_a_reason_not_a_500(self):
        (self.names / SID).write_text("web\t/proj/TESTHOST/app\t#1EA1EB\twhite\t" + MOON + "\n")
        st, r = self._post({"target": "web", "emoji": "\ud83c"})   # json.dumps escapes it as \ud83c
        self.assertEqual(st, 200)
        self.assertEqual(r.get("ok"), False)
        self.assertIn("unpaired surrogate", r.get("error") or "")
        self.assertEqual(km._name_emoji(SID), MOON, "the old value stands")
        self.assertFalse(self.dirty)


class WsOp(unittest.TestCase):
    """The tab menu's setSessionEmoji op: every refusal is a warn the dialog can show — never silence."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.names = Path(self.tmp) / "names"
        self.names.mkdir()
        self._saved = (km.NAMES, km.jd.STATE, km._mark_views_dirty)
        km.NAMES = self.names
        km.jd.STATE = Path(self.tmp) / "state"
        self.dirty = []
        km._mark_views_dirty = lambda: self.dirty.append(1)
        self.sent = []
        self.client = {"send": lambda frame: self.sent.append(json.loads(frame))}

    def tearDown(self):
        km.NAMES, km.jd.STATE, km._mark_views_dirty = self._saved

    def _op(self, emoji):
        km.Handler._dispatch_ws(types.SimpleNamespace(), {"type": "setSessionEmoji", "id": SID, "emoji": emoji}, self.client)

    def test_a_valid_emoji_is_confirmed_and_a_refusal_is_a_warn(self):
        (self.names / SID).write_text("web\t/proj/TESTHOST/app\t#1EA1EB\twhite\n")
        self._op(MOON)
        self.assertEqual(self.sent, [{"type": "emojiSet", "id": SID, "emoji": MOON}])
        self.assertEqual(km._name_emoji(SID), MOON)
        self.assertEqual(len(self.dirty), 1)
        self._op("moon")
        self.assertEqual(self.sent[-1]["type"], "warn")
        self.assertIn("not an emoji", self.sent[-1]["text"])

    def test_an_unpaired_surrogate_and_a_non_string_each_warn_instead_of_dropping_the_reply(self):
        # both used to raise inside the op (a UnicodeEncodeError) or coerce to a clear; the dialog had
        # already closed as the click's acknowledgement, so the user saw nothing happen and no reason
        (self.names / SID).write_text("web\t/proj/TESTHOST/app\t#1EA1EB\twhite\t" + MOON + "\n")
        self._op("\ud83c")
        self.assertEqual(len(self.sent), 1, "exactly one frame came back")
        self.assertEqual(self.sent[0]["type"], "warn")
        self.assertIn("unpaired surrogate", self.sent[0]["text"])
        for v in (None, 7, ["x"]):
            with self.subTest(v=repr(v)):
                self.sent.clear()
                self._op(v)
                self.assertEqual([f["type"] for f in self.sent], ["warn"])
                self.assertIn("must be text", self.sent[0]["text"])
        self.assertEqual(km._name_emoji(SID), MOON, "nothing was cleared")
        self.assertFalse(self.dirty)


if __name__ == "__main__":
    unittest.main()
