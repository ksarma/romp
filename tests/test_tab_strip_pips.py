#!/usr/bin/env python3
"""The chat tab strip speaks the SAME pip language as the feed and the sessions pane.

A pip marks something HAPPENING (gold working, straw awaiting-bg, the accent opening pulse) or
something WRONG (a gray ring when the live state could not be read). A healthy idle session gets no
pip, so a bare tab means only that — or a state carrying its own tab treatment (dashed blocked ring,
amber retrying, compacting bar, struck-through closed).

The strip used to render dots for working/awaiting-bg only, so an unreadable state was a bare tab
too, indistinguishable from a quiet one (the user 2026-08-10, who noticed the card pane and the
strip no longer matched). The hollow READY ring the first fix added here was dropped when the fork
converged with upstream (2026-08-14): a blank is the honest rendering of "alive and quiet", and only
the unreadable case needed a mark of its own.

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
    def test_the_strip_marks_activity_and_the_unreadable_state(self):
        """The tab render must place a pip for working, awaitingBg and a MISSING state — the same
        language dotFor (feed.ts) and statusDot (fleet.ts) speak — and none for a quiet session."""
        m = re.search(r"const dot: \[string, string\] \| null =.*?\n    if \(dot\)", RENDER, re.S)
        self.assertIsNotNone(m, "the tab strip's dot mapping is gone")
        body = m.group(0)
        self.assertIn('st === "working"', body)
        self.assertIn('st === "awaitingBg"', body)
        self.assertIn("!st ?", body, "a MISSING state must render an explicit unknown ring, not nothing")
        self.assertNotIn('st === "ready"', body, "a healthy idle session gets NO pip — a blank says it")
        self.assertNotIn('"idle — nothing running', body, "the ready tooltip went with the ready pip")

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
        tips = dict(re.findall(r'(work|await|unknown): "([^"]+)"', FEED_TS))
        self.assertEqual(len(tips), 3, "feed.ts DOT_TIP not found")
        for tip in tips.values():
            self.assertIn('"%s"' % tip, RENDER, "tab strip title diverged from the feed's: %s" % tip)

    def test_the_unknown_ring_matches_the_other_sheets(self):
        """The ring styling is mirrored by hex across the three standalone sheets; a re-tint in one
        must not silently fork the language. No .ready ring exists on any of them any more."""
        for sheet, name in ((CSS, "styles.css"), (FEED_CSS, "feed.css"), (FLEET_CSS, "fleet-pane.css")):
            self.assertNotRegex(sheet, r"\.(tab-dot|fwork-dot|fl-workdot)\.ready",
                                "%s still styles a ready pip" % name)
        for cls, hexv in (("unknown", "#8a8a8a"),):
            pat = re.compile(r"\.tab-dot\.%s\s*\{[^}]*inset 0 0 0 1\.5px %s" % (cls, hexv))
            self.assertRegex(CSS, pat, "styles.css .tab-dot.%s ring missing or re-tinted" % cls)
            for sheet, name in ((FEED_CSS, "feed.css .fwork-dot"), (FLEET_CSS, "fleet-pane.css .fl-workdot")):
                self.assertIn("1.5px %s" % hexv, sheet, "%s no longer matches %s" % (name, hexv))

    def test_mobiles_tab_scrape_is_untouched_by_the_new_rings(self):
        """kernel.py's mobile view derives awaitbg from '.tab-dot.await' and working from the
        'tab-working' CLASS — neither matches a .unknown ring, so the ring must not have
        pushed it to a bare '.tab-dot' query (which WOULD now match idle sessions)."""
        kernel = open(os.path.join(ROOT, "kernel", "kernel.py"), encoding="utf-8").read()
        self.assertIn("awaitbg:!!t.querySelector('.tab-dot.await')", kernel)
        self.assertIn("working:t.classList.contains('tab-working')", kernel)


if __name__ == "__main__":
    unittest.main()
