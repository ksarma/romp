"""Per-session identity color override (the user 2026-06-29) + the selectable palette (the user
2026-07-12): a right-click tab menu picks a color from the ACTIVE identity palette; the kernel persists
it to the names registry (bg + fg word, preserving name + cwd) and re-broadcasts. The gear's Session
colors picker switches the whole SET (STATE/palette): the kernel remaps every stored color to the same
slot in the new set, rewrites the shell launcher's STATE/palette-colors mirror, and pushes. SYNTHETIC
fixtures only (placeholder uuids, invented paths)."""
import inspect
import os
import tempfile
import unittest
from pathlib import Path
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
km = load_source("romp_kernel", os.path.join(BIN, "romp-kernel"))

SID = "11111111-2222-3333-4444-555555555555"
SID2 = "22222222-3333-4444-5555-666666666666"


class SessionColor(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.names = Path(self.tmp) / "names"
        self.names.mkdir()
        self._orig = km.NAMES
        km.NAMES = self.names
        self._state = km.jd.STATE
        km.jd.STATE = Path(self.tmp) / "state"      # _set_palette persists STATE/palette + the shell mirror
        km._pal_cache.update({"name": km.pal.DEFAULT, "mt": None})   # drop the mtime cache between sandboxes

    def tearDown(self):
        km.NAMES = self._orig
        km.jd.STATE = self._state
        km._pal_cache.update({"name": km.pal.DEFAULT, "mt": None})

    def test_active_palette_shape_and_the_rose_slot(self):
        # the SAME set the tmux launcher / SDK backend assign from — romp_palette is the single
        # source. The romp set grows APPEND-ONLY (slot 9 = rose #E0629C, the user 2026-08-28), so
        # the pin is shape + the stable prefix, never a fixed nine.
        bgs, fgs = km.pal.colors(km._palette_name()), km.pal.fgs(km._palette_name())
        self.assertEqual(len(bgs), len(fgs))
        self.assertGreaterEqual(len(bgs), 9)
        self.assertTrue(all(f in ("black", "white") for f in fgs))
        self.assertEqual(bgs[:2], ["#1EA1EB", "#54B204"], "existing assignments never shift")
        self.assertEqual((bgs[9], fgs[9]), ("#E0629C", "white"))
        self.assertEqual((bgs[10], fgs[10]), ("#B585B6", "black"),
                         "dusty mauve: white sits AT the 3.0 floor; black clears 7.0")
        self.assertEqual((bgs[11], fgs[11]), ("#B69513", "black"),
                         "dark gold: white FAILS the 3.0 floor (2.9); black clears 7.3")
        # the fg contrast floor the set's whites all clear: WCAG relative-luminance contrast >= 3.0
        r, g, b = (int("E0629C"[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
        lin = lambda c: c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
        L = 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)
        self.assertGreaterEqual((1.0 + 0.05) / (L + 0.05), 3.0, "white text clears the set's floor")
        self.assertIn("#1EA1EB", bgs)

    def test_set_color_rewrites_bg_and_fg_preserving_name_and_cwd(self):
        (self.names / SID).write_text("mysess\t/proj/TESTHOST/app\t#1EA1EB\twhite\n")
        self.assertTrue(km._set_session_color(SID, "#54B204"))
        parts = (self.names / SID).read_text().rstrip("\n").split("\t")
        self.assertEqual(parts[0], "mysess", "name preserved")
        self.assertEqual(parts[1], "/proj/TESTHOST/app", "cwd preserved")
        self.assertEqual(parts[2], "#54B204", "new bg written")
        self.assertEqual(parts[3], "black", "the palette's fg word for green")
        # _name_color reads it back (fg is always white on the dashboard)
        self.assertEqual(km._name_color(SID), {"bg": "#54B204", "fg": "#ffffff"})

    def test_set_color_accepts_a_swatch_from_any_known_palette(self):
        # a right-click menu rendered just before a palette switch still lands its click — the value
        # is validated against EVERY set, and the owning set supplies the fg word
        (self.names / SID).write_text("s\t/d\t#1EA1EB\twhite\n")
        phase0 = km.pal.PALETTES["phase"]["bg"][0]
        self.assertTrue(km._set_session_color(SID, phase0))
        parts = (self.names / SID).read_text().rstrip("\n").split("\t")
        self.assertEqual(parts[2], phase0)
        self.assertEqual(parts[3], km.pal.PALETTES["phase"]["fg"][0])

    def test_rejects_a_color_outside_every_palette(self):
        (self.names / SID).write_text("s\t/d\t#1EA1EB\twhite\n")
        self.assertFalse(km._set_session_color(SID, "#abcdef"))
        self.assertEqual((self.names / SID).read_text().split("\t")[2], "#1EA1EB", "unchanged")

    def test_missing_names_file_is_a_safe_noop(self):
        self.assertFalse(km._set_session_color("00000000-0000-0000-0000-000000000000", "#1EA1EB"))

    def test_set_palette_remaps_the_fleet_slot_for_slot(self):
        # sessions on romp slots 0 and 3, plus one color no palette owns (must be left alone)
        (self.names / SID).write_text("a\t/d\t#1EA1EB\twhite\n")
        (self.names / SID2).write_text("b\t/d\t#DD42FF\twhite\n")
        (self.names / "custom").write_text("c\t/d\t#ABCDEF\twhite\n")
        self.assertTrue(km._set_palette("phase"))
        pb, pf = km.pal.PALETTES["phase"]["bg"], km.pal.PALETTES["phase"]["fg"]
        self.assertEqual((self.names / SID).read_text().rstrip("\n").split("\t")[2:], [pb[0], pf[0]])
        self.assertEqual((self.names / SID2).read_text().rstrip("\n").split("\t")[2:], [pb[3], pf[3]])
        self.assertEqual((self.names / "custom").read_text().rstrip("\n").split("\t")[2],
                         "#ABCDEF", "an unowned color is not remapped")
        self.assertEqual((km.jd.STATE / "palette").read_text(), "phase", "the choice persists")
        self.assertEqual(km._palette_name(), "phase")
        # the shell launcher's mirror carries the ACTIVE set (bg<TAB>fg per line)
        lines = (km.jd.STATE / "palette-colors").read_text().rstrip("\n").split("\n")
        self.assertEqual([ln.split("\t") for ln in lines], [[b, f] for b, f in zip(pb, pf)])

    def test_set_palette_round_trip_restores_original_colors(self):
        (self.names / SID).write_text("a\t/d\t#4EA8A9\twhite\n")   # romp slot 2
        self.assertTrue(km._set_palette("romaO"))
        self.assertEqual((self.names / SID).read_text().split("\t")[2],
                         km.pal.PALETTES["romaO"]["bg"][2])
        self.assertTrue(km._set_palette("romp"))
        self.assertEqual((self.names / SID).read_text().split("\t")[2], "#4EA8A9",
                         "slot identity survives a switch there and back")

    def test_set_palette_rejects_an_unknown_name(self):
        (self.names / SID).write_text("a\t/d\t#1EA1EB\twhite\n")
        self.assertFalse(km._set_palette("neon-vaporwave"))
        self.assertEqual(km._palette_name(), "romp")
        self.assertEqual((self.names / SID).read_text().split("\t")[2], "#1EA1EB")

    def test_get_serves_palette_choices_and_ws_handles_the_pick(self):
        # /palette serves the ACTIVE swatches + every choosable set + the active name (the gear's picker
        # and the tab menu both read it — the client holds no color literals)
        get_src = inspect.getsource(km.Handler.do_GET)
        self.assertIn('p == "/palette"', get_src)
        self.assertIn('"palettes":', get_src)
        self.assertIn('"active":', get_src)
        # the WS branches: setSessionColor recolors one session; setPalette switches the set
        ksrc = Path(BIN, "romp-kernel").read_text()
        self.assertIn('msg.get("type") == "setSessionColor"', ksrc)
        self.assertIn("_set_session_color(str(msg[\"id\"]), str(msg[\"bg\"]))", ksrc)
        self.assertIn('msg.get("type") == "setPalette"', ksrc)
        self.assertIn('_set_palette(str(msg["name"]))', ksrc)

    def test_set_palette_rebroadcasts_and_boot_heals_the_mirror(self):
        src = inspect.getsource(km._set_palette)
        self.assertIn('_send_to_app("chat", {"type": "palette"', src, "open tab menus get fresh swatches")
        self.assertIn("_mark_views_dirty()", src, "tabs/cards/lanes repaint in the new colors")
        self.assertIn("_write_palette_mirror()", inspect.getsource(km.main),
                      "boot rewrites the shell mirror so bin/romp can never assign from a stale set")

    def test_gear_offers_the_session_colors_picker(self):
        html = _gear_src()
        self.assertIn(">Session colors<", html)
        self.assertIn("id=rs-pal-btn", html)
        self.assertIn("id=rs-pal-list", html)
        self.assertIn("{ type: 'setPalette', name: name }", _gear_src())
        self.assertIn("plFill(); fill(); }", _gear_src(),
                      "gear open re-reads the server-authoritative choice from /palette")


class HighSlotSwitches(SessionColor):
    """The T164 length-mismatch sweep, executed: sessions ON slots 9/10/11 survive palette switches
    in both directions. All built-in sets are 12 now (equalized), so the equal-length path maps
    slot-for-slot; the modulo wrap is exercised against a SYNTHETIC short set so the guard stays
    proven for future drift (a 13th romp color reopens the gap silently otherwise)."""

    def _seed(self, slot, sid):
        bg = km.pal.PALETTES["romp"]["bg"][slot]
        fg = km.pal.PALETTES["romp"]["fg"][slot]
        (self.names / sid).write_text("s%d\t/proj/TESTHOST/app\t%s\t%s\n" % (slot, bg, fg))

    def test_equal_length_switch_maps_high_slots_straight_across(self):
        sids = ["%08d-2222-3333-4444-555555555555" % i for i in range(4)]
        for slot, sid in zip((0, 9, 10, 11), sids):
            self._seed(slot, sid)
        self.assertTrue(km._set_palette("phase"))
        for slot, sid in zip((0, 9, 10, 11), sids):
            parts = (self.names / sid).read_text().rstrip("\n").split("\t")
            self.assertEqual(parts[2], km.pal.PALETTES["phase"]["bg"][slot], "slot %d" % slot)
            self.assertEqual(parts[3], km.pal.PALETTES["phase"]["fg"][slot])
        self.assertTrue(km._set_palette("romp"))
        for slot, sid in zip((0, 9, 10, 11), sids):
            parts = (self.names / sid).read_text().rstrip("\n").split("\t")
            self.assertEqual(parts[2], km.pal.PALETTES["romp"]["bg"][slot],
                             "equal-length round trip restores every high slot")

    def test_a_shorter_set_wraps_high_slots_modulo_without_crashing(self):
        km.pal.PALETTES["tiny"] = {"label": "tiny", "bg": ["#101010", "#202020", "#303030"],
                                   "fg": ["white", "white", "white"]}
        try:
            sids = ["%08d-2222-3333-4444-555555555555" % i for i in range(4)]
            for slot, sid in zip((0, 9, 10, 11), sids):
                self._seed(slot, sid)
            self.assertTrue(km._set_palette("tiny"))
            got = {}
            for slot, sid in zip((0, 9, 10, 11), sids):
                parts = (self.names / sid).read_text().rstrip("\n").split("\t")
                got[slot] = parts[2]
            self.assertEqual(got[9], "#101010", "slot 9 wraps to 0 — and COLLIDES with slot 0")
            self.assertEqual(got[0], "#101010")
            self.assertEqual(got[10], "#202020")
            self.assertEqual(got[11], "#303030")
            # the documented-lossy round trip: wrapped slots come back as their wrap targets
            self.assertTrue(km._set_palette("romp"))
            parts9 = (self.names / sids[1]).read_text().rstrip("\n").split("\t")
            self.assertEqual(parts9[2], km.pal.PALETTES["romp"]["bg"][0],
                             "a round trip through a shorter set is lossy for high slots, by design")
        finally:
            km.pal.PALETTES.pop("tiny", None)
            km._set_palette("romp")

    def test_the_mirror_writes_every_slot_with_both_fields(self):
        km._set_palette("romp")
        lines = (km.jd.STATE / "palette-colors").read_text().splitlines()
        self.assertEqual(len(lines), len(km.pal.PALETTES["romp"]["bg"]),
                         "the launcher mirror carries EVERY slot — zip truncation would drop tails")
        for ln in lines:
            self.assertEqual(len(ln.split("\t")), 2)

    def test_identity_picks_pair_bg_and_fg_past_slot_nine(self):
        # the SDK picker: find a sid hashing into 9..11 and assert the paired read holds
        import zlib
        bgs, fgs = km.pal.colors("romp"), km.pal.fgs("romp")
        sid = next("%08x-2222-3333-4444-555555555555" % i
                   for i in range(4096)
                   if zlib.crc32(("%08x-2222-3333-4444-555555555555" % i).encode()) % len(bgs) >= 9)
        import importlib
        sdk = km.sdk_backend if hasattr(km, "sdk_backend") else None
        if sdk is None:
            sdk = load_source("romp_sdk_pal", os.path.join(os.path.dirname(HERE), "kernel", "sdk_backend.py"))
        bg, fg = sdk.pick_identity_color(sid)
        i = zlib.crc32(sid.encode()) % len(bgs)
        self.assertGreaterEqual(i, 9)
        self.assertEqual((bg, fg), (bgs[i], fgs[i]), "the paired index holds past the old nine")


if __name__ == "__main__":
    unittest.main()


# The gear moved from kernel-inline strings into the shared feed bundle
# (2026-07-13): ui/webview/gear.js is the single source both hosts render, so
# the gear pins read THAT file (and feed.css for its styling).
def _gear_src():
    import pathlib
    return (pathlib.Path(__file__).resolve().parent.parent / "ui" / "webview" / "gear.js").read_text()


def _gear_css_src():
    import pathlib
    return (pathlib.Path(__file__).resolve().parent.parent / "ui" / "webview" / "gear.css").read_text()
