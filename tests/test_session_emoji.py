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
import tempfile
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
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


class Validator(unittest.TestCase):
    """The one validator: exactly one emoji as a person picks it, nothing textual, empty clears."""

    ACCEPTED = [MOON, THUMBS_TONE, FAMILY, HEART_FIRE, HEART_FIRE_MIN, KEYCAP, KEYCAP_MIN, FLAG, ENGLAND,
                KISS, COPYRIGHT_EMOJI, SMILEY_EMOJI, HAIR,
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
        for s in ("", " ", "\t", "\n", None, 7):
            with self.subTest(s=repr(s)):
                self.assertEqual(km._emoji_check(s), ("", None))

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

    def test_a_short_record_is_padded_not_misaligned(self):
        (self.names / SID).write_text("web\t/proj/TESTHOST/app\n")      # a pre-color record: two fields
        self.assertTrue(km._set_session_emoji(SID, MOON))
        self.assertEqual(self._line().rstrip("\n").split("\t"), ["web", "/proj/TESTHOST/app", "", "", MOON])
        self.assertEqual(km._identity_of(SID), ("", ""))

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
        src = Path(os.path.join(os.path.dirname(HERE), "kernel", "codex_backend.py")).read_text()
        self.assertIn('emoji = old[4] if len(old) > 4 else ""', src)
        self.assertIn('("\\t" + emoji) if emoji else ""', src)


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
                       km._host_for_sid, km._remote_forward)
        km.NAMES = self.names
        km.jd.STATE = Path(self.tmp) / "state"
        km._tmux_sessions = lambda: {}
        km._live_names = lambda tm: {"web": SID}
        km._host_for_sid = lambda sid: None
        self.dirty = []
        km._mark_views_dirty = lambda: self.dirty.append(1)

    def tearDown(self):
        (km.NAMES, km.jd.STATE, km._tmux_sessions, km._live_names, km._mark_views_dirty,
         km._host_for_sid, km._remote_forward) = self._saved

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
        km._remote_forward = lambda r, path, body: (forwarded.append((r["host"], path, body)),
                                                   {"ok": False, "error": "one emoji only"})[1]
        st, r = self._post({"target": SID2, "emoji": MOON})
        self.assertEqual(forwarded, [("gpu1", "/emoji", {"target": SID2, "emoji": MOON})])
        self.assertEqual(r, {"ok": False, "error": "one emoji only"}, "the remote's own verdict rides back")
        km._remote_forward = lambda r, path, body: None
        st, r = self._post({"target": SID2, "emoji": MOON})
        self.assertFalse(r.get("ok"))
        self.assertIn("did not answer", r.get("error") or "")


if __name__ == "__main__":
    unittest.main()
