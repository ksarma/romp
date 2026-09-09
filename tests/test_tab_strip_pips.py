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

Since the 2026-09-09 fold (upstream's T262g, their PR #1108) the state → dot-class rule is `tabDotClass` and
the hover-title rule `tabDotTitle`, side by side in ui/webview/tab-state.ts; render.ts only wires them
onto the tab. Every tab carries the dot's SLOT in every state (a state with no dot gets the hidden
"tab-dot none", so a tab's width never depends on its state), and the pins below read the rule where
it lives.

Source-pinning, like the other chat-render tests (the renderer has no jsdom harness).
"""
import os
import re
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
RENDER = open(os.path.join(ROOT, "ui", "webview", "render.ts"), encoding="utf-8").read()
TAB_STATE = open(os.path.join(ROOT, "ui", "webview", "tab-state.ts"), encoding="utf-8").read()
CSS = open(os.path.join(ROOT, "ui", "webview", "styles.css"), encoding="utf-8").read()
FEED_TS = open(os.path.join(ROOT, "ui", "webview", "feed.ts"), encoding="utf-8").read()
FEED_CSS = open(os.path.join(ROOT, "ui", "webview", "feed.css"), encoding="utf-8").read()
FLEET_CSS = open(os.path.join(ROOT, "ui", "webview", "fleet-pane.css"), encoding="utf-8").read()


def _fn_body(src, name):
    """The body of the exported `name` function in tab-state.ts (one-line-per-branch rules)."""
    m = re.search(r"export function %s\([^)]*\)[^{]*\{(.*?)\n\}" % re.escape(name), src, re.S)
    assert m is not None, "tab-state.ts %s is gone" % name
    return m.group(1)


class TabStripPips(unittest.TestCase):
    def test_the_strip_marks_activity_and_the_unreadable_state(self):
        """The dot rule must place a pip for working, awaitingBg and a MISSING state, the same
        language dotFor (feed.ts) and statusDot (fleet.ts) speak, and none for a quiet session; and
        render.ts must put the classed slot on the tab."""
        body = _fn_body(TAB_STATE, "tabDotClass")
        self.assertIn('st === "working"', body)
        self.assertIn('st === "awaitingBg"', body)
        self.assertRegex(body, r'if \(!st\) return "tab-dot unknown";',
                         "a MISSING state must render an explicit unknown ring, not nothing")
        self.assertNotIn('st === "ready"', body, "a healthy idle session gets NO pip — a blank says it")
        self.assertNotIn('"tab-dot ready"', TAB_STATE, "a healthy idle session gets NO pip: a blank says it")
        for src, name in ((TAB_STATE, "tab-state.ts"), (RENDER, "render.ts")):
            self.assertNotIn('"idle — nothing running', src, "%s: the ready tooltip went with the ready pip" % name)
        # the wiring: render.ts reads the rule, never a dot ladder of its own
        self.assertIn("const dotCls = tabDotClass(st);", RENDER, "the tab render must class its dot by tabDotClass")
        self.assertIn('if (dotCls) tab.appendChild(el("span", dotCls));', RENDER, "the classed slot goes on the tab")
        self.assertNotRegex(RENDER, r"const dot: \[string, string\] \| null =",
                            "render.ts grew a dot ladder of its own beside tab-state.ts's rule")

    def test_states_with_their_own_tab_treatments_stay_undotted(self):
        """blocked/awaiting/retrying/compacting/closed carry border/bar/strike treatments; the dot
        rule must give them no visible dot (no double-encoding): compacting is named and returns null
        (its animated bar takes the slot), the rest fall through to the hidden slot, "tab-dot none",
        which the sheet hides."""
        body = _fn_body(TAB_STATE, "tabDotClass")
        for st in ("blocked", "closed", "retrying", "awaiting", "needsInput"):
            self.assertNotIn('"%s"' % st, body, "%s has its own tab treatment; no dot" % st)
        self.assertRegex(body, r'if \(st === "compacting"\) return null;',
                         "compacting's bar takes the slot: the rule must return null for it, not a dot")
        self.assertTrue(body.rstrip().endswith('return "tab-dot none";'),
                        "the rule must end in the hidden slot as its explicit fall-through")
        self.assertRegex(CSS, r"\.tab-dot\.none\s*\{[^}]*visibility:\s*hidden",
                         "styles.css must hide the .tab-dot.none slot, or every quiet tab wears a working dot")

    def test_the_pips_explain_themselves_on_hover_with_the_feeds_exact_titles(self):
        """One vocabulary, byte-identical: the strip's hover titles are the feed's DOT_TIP strings
        (the user 2026-07-22: learn the states from tooltips). They live in tabDotTitle, beside the
        class rule; render.ts sets the slot's title from it."""
        tips = dict(re.findall(r'(work|await|unknown): "([^"]+)"', FEED_TS))
        self.assertEqual(len(tips), 3, "feed.ts DOT_TIP not found")
        body = _fn_body(TAB_STATE, "tabDotTitle")
        for tip in tips.values():
            self.assertIn('"%s"' % tip, body, "tab strip title diverged from the feed's: %s" % tip)
        # each titled state is one the class rule dots: working, awaitingBg, a missing state, opening
        self.assertRegex(body, r'if \(st === "working"\) return "%s";' % re.escape(tips["work"]))
        self.assertRegex(body, r'if \(st === "awaitingBg"\) return "%s";' % re.escape(tips["await"]))
        self.assertRegex(body, r'if \(!st\) return "%s";' % re.escape(tips["unknown"]))
        self.assertRegex(body, r'if \(st === "opening"\) return "opening — ')
        self.assertIn("const dotTip = dotCls ? tabDotTitle(st) : null;", RENDER,
                      "render.ts must take the slot's title from tabDotTitle")
        self.assertIn("(tab.lastElementChild as HTMLElement).title = dotTip;", RENDER,
                      "the title must land on the slot tabDotClass classed")

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
