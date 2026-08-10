#!/usr/bin/env python3
"""The chat tab strip speaks the SAME four-state pip language as the feed and the sessions pane.

The feed's .fwork-dot and the sessions pane's .fl-workdot were completed to a total four-state
partition on 2026-08-09 (gold = working, straw = awaiting-bg, hollow steel ring = ready/idle, gray
ring = state missing outright), but the tab strip kept the old two-state grammar: dots only for
working/awaiting-bg, with ready and unknown both rendered as a bare tab — the exact "known state
indistinguishable from a rendering hole" ambiguity the pane fix was written to kill, surviving on one
surface (the user 2026-08-10, who noticed the card pane and the strip no longer matched). Now the
strip renders all four; a bare tab means only a state with its own tab treatment (dashed blocked
ring, amber retrying, compacting bar, struck-through closed, opening dots).

Source-pinning, like the other chat-render tests (the renderer has no jsdom harness).
"""
import os
import re
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
RENDER = open(os.path.join(ROOT, "ui", "webview", "render.ts"), encoding="utf-8").read()
CSS = open(os.path.join(ROOT, "ui", "webview", "styles.css"), encoding="utf-8").read()
FEED_TS = open(os.path.join(ROOT, "ui", "webview", "feed.ts"), encoding="utf-8").read()
FEED_CSS = open(os.path.join(ROOT, "ui", "webview", "feed.css"), encoding="utf-8").read()
FLEET_CSS = open(os.path.join(ROOT, "ui", "webview", "fleet-pane.css"), encoding="utf-8").read()


class TabStripPips(unittest.TestCase):
    def test_the_strip_maps_all_four_states_to_a_dot(self):
        """The tab render must place a pip for working, awaitingBg, ready/idle AND a missing state —
        the same partition dotFor (feed.ts) and statusDot (fleet.ts) speak."""
        m = re.search(r"const dot: \[string, string\] \| null =.*?\n    if \(dot\)", RENDER, re.S)
        self.assertIsNotNone(m, "the tab strip's four-state dot mapping is gone")
        body = m.group(0)
        self.assertIn('st === "working"', body)
        self.assertIn('st === "awaitingBg"', body)
        self.assertIn('st === "ready" || st === "idle"', body)
        self.assertIn("!st ?", body, "a MISSING state must render an explicit unknown ring, not nothing")

    def test_states_with_their_own_tab_treatments_stay_undotted(self):
        """blocked/awaiting/retrying/compacting/closed carry border/bar/strike treatments; the dot
        mapping must fall through to null for them (no double-encoding)."""
        m = re.search(r"const dot: \[string, string\] \| null =(.*?)\n    if \(dot\)", RENDER, re.S)
        body = m.group(1)
        for st in ("blocked", "compacting", "closed", "retrying"):
            self.assertNotIn('"%s"' % st, body, "%s has its own tab treatment; no dot" % st)
        self.assertTrue(body.rstrip().endswith(": null;"), "the mapping must end in an explicit null fall-through")

    def test_the_pips_explain_themselves_on_hover_with_the_feeds_exact_titles(self):
        """One vocabulary, byte-identical: the strip's hover titles are the feed's DOT_TIP strings
        (the user 2026-07-22: learn the states from tooltips)."""
        tips = dict(re.findall(r'(work|await|ready|unknown): "([^"]+)"', FEED_TS))
        self.assertEqual(len(tips), 4, "feed.ts DOT_TIP not found")
        for tip in tips.values():
            self.assertIn('"%s"' % tip, RENDER, "tab strip title diverged from the feed's: %s" % tip)

    def test_ready_and_unknown_rings_match_the_other_sheets(self):
        """The ring styling is mirrored by hex across the three standalone sheets; a re-tint in one
        must not silently fork the language."""
        for cls, hexv in (("ready", "#2b7fb8"), ("unknown", "#8a8a8a")):
            pat = re.compile(r"\.tab-dot\.%s\s*\{[^}]*inset 0 0 0 1\.5px %s" % (cls, hexv))
            self.assertRegex(CSS, pat, "styles.css .tab-dot.%s ring missing or re-tinted" % cls)
            for sheet, name in ((FEED_CSS, "feed.css .fwork-dot"), (FLEET_CSS, "fleet-pane.css .fl-workdot")):
                self.assertIn("1.5px %s" % hexv, sheet, "%s no longer matches %s" % (name, hexv))

    def test_mobiles_tab_scrape_is_untouched_by_the_new_rings(self):
        """kernel.py's mobile view derives awaitbg from '.tab-dot.await' and working from the
        'tab-working' CLASS — neither matches a .ready/.unknown ring, so the rings must not have
        pushed it to a bare '.tab-dot' query (which WOULD now match idle sessions)."""
        kernel = open(os.path.join(ROOT, "kernel", "kernel.py"), encoding="utf-8").read()
        self.assertIn("awaitbg:!!t.querySelector('.tab-dot.await')", kernel)
        self.assertIn("working:t.classList.contains('tab-working')", kernel)


if __name__ == "__main__":
    unittest.main()
