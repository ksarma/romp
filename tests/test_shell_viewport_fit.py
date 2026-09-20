#!/usr/bin/env python3
"""The shell fits the VISIBLE viewport, on every browser (the user 2026-07-29).

Two reports, one root cause. On an iPad the whole bottom of the UI was cut off; in Firefox a strip along
the bottom sat over the rail. The shell sized its column with `100vh` while the body that CLIPS it
(overflow:hidden) was sized `height:100%`. Those are the same number only when no browser chrome is
moving: on iOS Safari `100vh` is the LARGE viewport, the one you get with the address bar collapsed, so
whenever a toolbar is on screen the column was taller than the box containing it and the rail fell out of
the bottom. Two height bases for one box is the bug.

Worse, the accurate measurement already existed and was thrown away: _LANDING_MOBILE_JS publishes the
live visualViewport height as --app-h, but only the MOBILE media query consumed it, and a landscape
tablet is too wide for both mobile breakpoints, so it took the desktop branch.

Verified in real Firefox before/after by forcing --app-h shorter than 100vh (the iOS toolbar case): the
rail measured 870..900 inside a 600px-tall body before, and 570..600 after.
"""
import os
import re
import sys
import tempfile
import unittest
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
km = load_source("romp_kernel_vhfit", os.path.join(BIN, "romp-kernel"))
sys.path.insert(0, HERE)
import served_css   # noqa: E402  the served page's parsed rules and scripts (loads no romp code)


# D1's fixed body (the mobile block; tests below)
_FIXED_BODY_RULE = "body{position:fixed;left:0;right:0;top:var(--app-top,0px);height:var(--app-h,100dvh)}"


class OneHeightBasis(unittest.TestCase):
    def setUp(self):
        self.html = km._landing()

    def test_the_column_is_measured_against_the_body_that_clips_it(self):
        self.assertIn(".col{display:flex;flex-direction:column;height:100%;box-sizing:border-box;", self.html)
        self.assertNotIn("height:100vh;box-sizing:border-box", self.html,
                         "the column must not carry a viewport unit of its own")

    def test_the_shell_height_chain_applies_at_every_width(self):
        # 100% → 100dvh → --app-h, last-wins, so an old browser still gets a full-height shell and a
        # modern one tracks chrome appearing and collapsing. NOT inside a media query any more: a
        # landscape tablet matches neither mobile breakpoint.
        self.assertIn("html,body{margin:0;height:100%;height:100dvh;height:var(--app-h,100dvh);"
                      "background:#1e1e1e;overflow:hidden}", self.html)

    def test_no_full_height_box_is_left_on_a_raw_viewport_unit(self):
        # every remaining 100vh in the shell would be a box that ignores the toolbars
        shell = self.html
        for frag in ("width:100vw;height:100vh", ".col{display:flex;flex-direction:column;height:100vh"):
            self.assertNotIn(frag, shell, frag)

    def test_a_lifted_pane_is_sized_by_its_insets_not_by_viewport_units(self):
        # inset:0 already IS the viewport box for a fixed element; the explicit 100vw/100vh overrode it.
        # (background:transparent rides the same rules: an opaque lifted iframe blacks out the window —
        # see test_kernel.test_settings_is_a_fullscreen_modal.)
        self.assertIn("body.settings-open #f-settings{display:block;position:fixed;inset:0;z-index:200;background:transparent}", self.html)
        # The PICKER lift is the one exception on the VERTICAL axis: its height follows --app-h (the
        # shell's live visible height) because the layout viewport ignores the phone keyboard — inset:0
        # left the picker's lower rows behind it — and the --app-h sizing is also what turns the keyboard
        # into an in-iframe resize event for the picker's short-window fold (the user 2026-08-10).
        # Horizontally it stays inset-sized (left:0;right:0), no 100vw.
        self.assertIn("body.picker-open iframe.lifted{display:block;position:fixed;left:0;right:0;top:0;"
                      "height:var(--app-h,100dvh);z-index:200;background:transparent}", self.html)

    def test_the_mobile_body_sits_at_the_visual_viewports_pan(self):
        # D1 (2026-09-19): inside the mobile media block, and only there, the body is FIXED at --app-top (the pan fit()
        # publishes) with the same height chain as the flex body rule before it, so under an iOS keyboard pan the body
        # covers exactly the visible band and no bare background shows between the composer and the keyboard. No
        # transform, filter or contain on the body, so the shell's fixed panels keep the viewport as their containing block:
        # test_no_html_or_body_rule_gives_the_fixed_panels_a_new_containing_block, over the served CSS.
        html = self.html
        rule = _FIXED_BODY_RULE
        self.assertEqual(html.count(rule), 1)
        mobile_at = html.index("@media " + km._MOBILE_MQ + "{")
        self.assertLess(mobile_at, html.index(rule), "the fixed body is a mobile rule")
        self.assertLess(html.index("body{display:flex;flex-direction:column;height:100vh;height:var(--app-h,100dvh)}"), html.index(rule),
                        "after the flex body rule it extends")
        # the only position:fixed body rule is the one inside the mobile block, so a document outside _MOBILE_MQ (a fine
        # pointer above 820 px, a coarse one above 1024 px) keeps its body in flow, and the base html,body chain
        # (test_the_shell_height_chain_applies_at_every_width) carries no top or position. Inside the block a fine pointer at
        # or under 820 px takes this fixed body too, at the 0px fit() writes off a coarse pointer (round 2, 2026-09-19:
        # test_kernel_mobile's finePointer scenario, and the populations legs in test_keyboard_gap_served)
        self.assertEqual(html.count("body{position:fixed"), 1)
        # round 4 (2026-09-20): the consumers of --app-top DERIVED by the parser over every served style element, through any
        # custom-property alias, rather than a substring over the page's prefix (which saw nothing after the block): exactly
        # the two rules the census below holds to the origin, both inside the mobile block, so the population claim in
        # fit()'s comment (a coarse document outside the block publishes a pan nothing consumes) rests on this. A new
        # consumer anywhere, inside the block or outside it, joins this list on purpose: a tripwire, not a defect. Inline
        # style attributes and script-inserted rules are outside the served CSS and outside this scan.
        rules = served_css.rules(html)
        app_top = served_css.closure(rules, "--app-top")
        consumers = sorted((r.at, r.selector) for r in rules if any(served_css.names_any(v, app_top) for _, v in r.decls))
        mobile = ("@media " + km._MOBILE_MQ,)
        self.assertEqual(consumers, [(mobile, "body"), (mobile, "body.picker-open iframe.lifted")],
                         "every consumer of --app-top is a census member's origin inside the mobile block")

    def test_no_html_or_body_rule_gives_the_fixed_panels_a_new_containing_block(self):
        # round 2 (2026-09-19): the first cut looped over the test's own literal for these properties, a guard no kernel.py could
        # fail. The invariant is page-wide: a transform (or one of its longhands translate, rotate and scale, or an
        # offset-path), a filter or backdrop-filter, a contain or content-visibility, a will-change or a perspective on html
        # or body makes THAT box the containing block of every position:fixed descendant, and the shell's fixed panels (the
        # tab bar glued to the true bottom above all) would move with the fixed body's pan. So the scan reads the served CSS,
        # every style element and every media block. The population is every rule whose selector has html, body or :root as
        # its SUBJECT (the last compound: 'body.picker-open iframe.lifted' names body as an ancestor, where a transform is
        # legitimate, and is out), and a property matches at a declaration boundary (text-transform is not transform, and
        # transform:scale(...) is a transform value, not a scale declaration). Round 3 (2026-09-19): the list was six; the
        # five added (translate, rotate, scale, content-visibility, offset-path) each displaced a fixed bottom:0 bar into the
        # body's box in Chromium and WebKit the way will-change:transform does, and the six-item scan stayed green for them.
        # Round 4 (2026-09-20): the property is read from the PARSED declaration, and an optional vendor prefix is allowed
        # (-webkit-transform and -webkit-filter create the containing block in Chromium and WebKit, -webkit-backdrop-filter
        # in WebKit; the unprefixed alternation stayed green for all three). The population is html, body and :root only:
        # the picker's lift sits four levels down the tree, and a containing-block property on an intermediate ancestor
        # (.pane, .col) would re-parent it too; that road is guarded by the served leg, tests/test_keyboard_gap_served.py,
        # which reads the lift's box against the body's in a real engine under the pan (a static scan cannot see a class
        # added at runtime or a script-inserted rule, so the engine leg is the instrument for the ancestors, not this one).
        rules = served_css.rules(self.html)
        subject = re.compile(r"^(html|body|:root)(?![\w-])")
        pop = [r for r in rules if any(subject.match(x) for x in served_css.subjects(r.selector))]
        self.assertGreaterEqual(len(pop), 4, "the html/body population is the base chain, the mobile chain, the flex body and the fixed body at least: %r"
                                % ([r.selector for r in pop],))
        self.assertIn(_FIXED_BODY_RULE, ["%s{%s}" % (r.selector, r.declarations) for r in pop], "the fixed body rule is in the population")
        prop = re.compile(r"^(?:-[a-z]+-)?(transform|translate|rotate|scale|filter|backdrop-filter|contain|content-visibility|will-change|perspective|offset-path)$")
        self.assertEqual([(r.at, r.selector, p, v) for r in pop for p, v in r.decls if prop.match(p)], [],
                         "a containing-block property on html or body moves every fixed panel with the fixed body's pan")

    def test_every_fixed_box_sized_by_the_shells_height_sits_at_its_pan(self):
        # D1 round 2 (2026-09-19): the pan gave the shell a second origin, and the first review found the ONE other fixed box
        # sized by --app-h, the new-session picker's lift (body.picker-open iframe.lifted, top:0), still at layout y 0 under
        # the pan, so the band the body rule removes from the composer survived under the picker; the comment over the body
        # rule had listed six fixed panels by hand and missed it. The consumers are DERIVED here from the served CSS, never
        # listed. Round 4 (2026-09-20): the derivation PARSES the sheet (tests/served_css.py) instead of substring-searching
        # it, which had four blind spots: a sizing keyed to --app-h through a custom property (resolved to a fixed point
        # here, so a chain of aliases is seen too), whitespace inside the var() call (a parsed declaration, not a substring),
        # an element whose position:fixed and whose sizing sit under two different selector STRINGS (the settings lift is
        # such an element: #f-settings{display:none} and body.settings-open #f-settings{...position:fixed...}), and a style
        # element carrying an attribute (every <style> is read, and the parse refuses when a tag opening was not consumed).
        # The join is per ELEMENT: keyed on the selector's subject compound, so both of the settings lift's rules land on
        # one key; two compounds that differ by a class on the same element (body and body.picker-open) stay separate keys,
        # a bound this static reading keeps. Each member sits at var(--app-top) in a rule inside the mobile block (the
        # lift's base rule is upstream's line and stays byte-identical; the mobile block re-tops it, so a coarse desktop
        # layout keeps the lift at the static body's origin), and the cascade is judged over EVERY rule whose subject can
        # match the member's element (a subset or superset of its simple selectors: iframe, .lifted, body.picker-open), by
        # specificity, then order, an !important winning outright, over every property that sets the top edge (top and the
        # inset, inset-block and inset-block-start shorthands, which the sheet uses fourteen times); within the origin rule
        # itself the origin is the last top-edge declaration. A selector sharing no simple selector with the member
        # (body.picker-open #f-chat) is outside this reading; the served leg reads the boxes themselves.
        rules = served_css.rules(self.html)
        self.assertGreater(len(rules), 100, "the parse read the served stylesheets: %d rules" % len(rules))
        by_el = {}
        for r in rules:
            for el in served_css.subjects(r.selector):
                by_el.setdefault(el, []).append(r)
        app_h = served_css.closure(rules, "--app-h")
        sized = lambda r: any(served_css.names_any(v, app_h) for _, v in r.decls)
        fixed_h = sorted(el for el, rs in by_el.items() if any(served_css.is_fixed(r) for r in rs) and any(sized(r) for r in rs))
        self.assertTrue(fixed_h, "derived population empty: no element both position:fixed and sized by --app-h in the served CSS")
        # the split-selector element the per-selector census could not see: the settings lift is position:fixed under one
        # selector string and hidden under another, and the join sees one element. It is NOT sized by --app-h today (inset:0
        # spans the whole layout viewport, so no bare band shows under it; moving it onto the band is a design change the
        # owner decides), so it is outside the census; a sizing by --app-h under EITHER of its selectors puts it in.
        settings = by_el.get("#f-settings", [])
        self.assertTrue(any(served_css.is_fixed(r) for r in settings) and len({r.selector for r in settings}) >= 2,
                        "the join unites the settings lift's rules on one element: %r" % ([(r.at, r.selector) for r in settings],))
        self.assertNotIn("#f-settings", fixed_h, "the settings lift is not sized by --app-h; when it is, it joins the census and takes the origin")
        # the census as of this change, in subject-compound form. A new fixed consumer of --app-h joins this list AND takes the
        # pan (the loop below), or the band opens again under whatever it covers.
        self.assertEqual(fixed_h, ["body", "iframe.lifted"])
        mobile = ("@media " + km._MOBILE_MQ,)
        app_top = served_css.closure(rules, "--app-top")
        is_origin = lambda p, v: p == "top" and served_css.names_any(v, app_top)
        top_edge = {"top", "inset", "inset-block", "inset-block-start"}
        for el in fixed_h:
            rs = by_el[el]
            origins = [r for r in rs if r.at == mobile and any(is_origin(p, v) for p, v in r.decls)]
            self.assertTrue(origins, "%s has no --app-top origin inside the mobile block: %r" % (el, [(r.at, r.declarations) for r in rs]))
            for r in origins:
                tops = [(p, v) for p, v in r.decls if p in top_edge]
                self.assertTrue(is_origin(*tops[-1]), "%s: the origin is not the last top-edge declaration of its own rule: %r" % (el, r.declarations))
                self.assertFalse(any("!important" in v for p, v in tops), "%s: the origin rule's top edge carries no !important: %r" % (el, r.declarations))
            spec = max(served_css.specificity(m) for r in origins for m in served_css.members(r.selector) if served_css.subject(m) == el)
            last = max(r.index for r in origins)
            winners = [(r.at, m, p, v) for r in rules for m in served_css.members(r.selector) if served_css.can_match(served_css.subject(m), el)
                       for p, v in r.decls if p in top_edge and not is_origin(p, v)
                       and ("!important" in v or served_css.specificity(m) > spec or (served_css.specificity(m) == spec and r.index > last))]
            self.assertEqual(winners, [], "%s: a rule that can match the element sets its top edge and wins the cascade over the --app-top origin" % el)

    def test_an_unpainted_pane_is_dark_not_white(self):
        # a pane whose document has not painted is a white rectangle in a dark frame (Firefox shows it
        # plainly) — which is exactly what "a white strip at the bottom" looks like
        self.assertIn("iframe{background:#1e1e1e}", self.html)


class RefitsWhenTheVisibleHeightChanges(unittest.TestCase):
    def setUp(self):
        self.js = km._LANDING_MOBILE_JS

    def test_it_drives_app_h_off_the_live_visual_viewport(self):
        # pinch-aware since 2026-08-19: desktop (fine pointer) reads innerHeight outright — pinch-immune
        # in every browser, no scale arithmetic (desktop Firefox does not reliably report vv.scale during
        # a pinch); the visual viewport drives the fit only on coarse-pointer devices, where the soft
        # keyboards and collapsing toolbars it exists for live, scale-guarded against mobile pinches.
        self.assertIn("var coarse=window.matchMedia&&matchMedia('(pointer: coarse)').matches;", self.js)
        self.assertIn("var h=(!coarse||!vv)?window.innerHeight:Math.round(vv.height*(vv.scale||1));", self.js)
        self.assertIn("setProperty('--app-h',h+'px')", self.js)
        # D1 (2026-09-19): the visual viewport's PAN rides beside the height. iOS reveals a focused input by moving the
        # visual viewport down the layout viewport (offsetTop > 0) with no document scroll to undo, so a body sized to
        # vv.height at layout y 0 left the bottom offsetTop pixels of the screen bare under the composer. fit() publishes
        # the pan as --app-top under the same coarse guard (a fine pointer writes 0px whatever the visual viewport says; the
        # consumer is gated on the layout query, a different population, see the fit() comment). Under a pinch (scale above 1.01) the last pan
        # holds, a zoom pans too and never re-lays the shell, CLAMPED AT USE to the layout viewport less the height the same
        # run publishes, so a keyboard dismissed while zoomed cannot leave the body hanging below the viewport (round 2,
        # 2026-09-19); the clamp bounds what is published and never writes back into the hold (round 4, 2026-09-20: it had,
        # so the hold decayed to 0 the first time the clamp bound and a keyboard raised again under the zoom reopened the
        # band), and the hold is the last value published on EVERY road, the 0px road included. Behaviour:
        # test_kernel_mobile.MobileFitExecutes.
        self.assertIn("\nvar lastPan=0;\nfunction fit(){", self.js)
        self.assertIn("if(!coarse||!vv)document.documentElement.style.setProperty('--app-top',(lastPan=0)+'px');", self.js)
        self.assertIn("else if((vv.scale||1)<=1.01)document.documentElement.style.setProperty('--app-top',(lastPan=Math.round(vv.offsetTop||0))+'px');\n"
                      "else document.documentElement.style.setProperty('--app-top',Math.min(lastPan,Math.max(0,window.innerHeight-h))+'px');", self.js)
        self.assertNotIn("lastPan=Math.min", self.js, "the clamp is at use: nothing writes its result back into the hold")
        # the write sits inside fit(), after the --app-h write and before the stray-scroll reset, so one frame publishes both
        self.assertLess(self.js.index("setProperty('--app-h',h+'px')"), self.js.index("setProperty('--app-top'"))
        self.assertLess(self.js.index("setProperty('--app-top'"), self.js.index("if(window.scrollY||document.documentElement.scrollTop)window.scrollTo(0,0);"))

    def test_the_bars_reservation_follows_the_bars_own_box(self):
        # D1 (2026-09-19): barfit is rebound rather than edited because fit() calls it by name; upstream's declaration stands,
        # saved as barfitVV, and upstream's kbOpen stands untouched beside it. The strip is the part of the bar's BOX inside
        # the band the same run PUBLISHED (--app-top to --app-top + --app-h, read back from the style object, so a pinch,
        # whose pan holds and whose height is upstream's scale arithmetic, is judged against the shell it laid out): 0 for a
        # bar starting at or below the band's bottom edge, the whole height wholly inside, the overlap between (round 4,
        # 2026-09-20: the reservation had been all-or-nothing on a visibility verdict, a bar-tall strip over a bar showing a
        # few pixels; and the pinch term had handed the verdict back to upstream's height difference, which collapsed the
        # strip at the 1.01 scale cut under a deep pan). Upstream's barfit stands only where the box or the band cannot be
        # read (no bar, no visualViewport, no getPropertyValue, a run before both variables are published). Behaviour:
        # test_kernel_mobile.MobileFitExecutes (the sweep across the pan range, the pinch over the deep pan).
        self.assertIn("function kbOpen(){var vv=window.visualViewport;return vv?(window.innerHeight-vv.height*(vv.scale||1)>120):false;}", self.js)
        self.assertIn("function barfit(){try{var bar=document.getElementById('mtabs');if(!bar)return;\n"
                      "document.documentElement.style.setProperty('--mtabs-h',(kbOpen()?0:(bar.offsetHeight||0))+'px');}catch(e){}}\n", self.js)
        self.assertIn("var barfitVV=barfit;\nbarfit=function(){try{var vv=window.visualViewport,bar=document.getElementById('mtabs'),st=document.documentElement.style;\n"
                      "if(!vv||!bar||typeof bar.getBoundingClientRect!=='function'||typeof st.getPropertyValue!=='function'){barfitVV();return;}\n"
                      "var top=parseFloat(st.getPropertyValue('--app-top')),h=parseFloat(st.getPropertyValue('--app-h'));\n"
                      "if(!(top>=0)||!(h>0)){barfitVV();return;}\n"
                      "st.setProperty('--mtabs-h',Math.max(0,Math.min(bar.offsetHeight||0,top+h-bar.getBoundingClientRect().top))+'px');}catch(e){}};", self.js)
        self.assertNotIn("kbOpen=function", self.js, "kbOpen is not rebound: the strip is barfit's own reading now")
        self.assertLess(self.js.index("barfit=function(){"), self.js.index("fit();window.addEventListener('resize',refit)"),
                        "rebound before the boot fit, so the first paint already reads the proportional strip")
        # the band is published before barfit reads it: both writes precede the barfit() call inside fit()
        self.assertLess(self.js.index("setProperty('--app-top'"), self.js.index("barfit();}catch(e){}}"))

    def test_it_refits_on_the_events_ios_actually_changes_the_height_on(self):
        # iOS collapses its toolbars AS YOU SCROLL, with no window resize; the visual viewport's own
        # scroll event is where that settles. pageshow covers a back/forward-cache restore. Since
        # 2026-09-08 every event binds `refit`, the one-frame coalescer, and the set also covers a
        # return from the background (visibilitychange, window focus) and a keyboard the composer's
        # blur dismissed (focusout) — the installed iPhone app came back keyboard-short otherwise.
        # Behavior is pinned by test_kernel_mobile.MobileFitExecutes; these are the wiring strings.
        for ev in ("'resize',refit", "'orientationchange',refit", "'pageshow',refit", "'focus',refit"):
            self.assertIn("window.addEventListener(" + ev, self.js)
        self.assertIn("document.addEventListener('visibilitychange',function(){if(document.visibilityState==='visible')refit();});", self.js)
        self.assertIn("document.addEventListener('focusout',refit);", self.js)
        self.assertIn("window.visualViewport.addEventListener('scroll',refit)", self.js)
        self.assertIn("window.visualViewport.addEventListener('resize',refit)", self.js)
        # one fit per animation frame, however many events a keyboard slide or a resume fires
        self.assertIn("fitRaf=window.requestAnimationFrame(function(){fitRaf=0;fit();});", self.js)

    def test_the_fit_runs_even_with_no_mobile_tab_bar(self):
        # it must apply on a desktop/tablet layout too, so the fit and its listeners come BEFORE the
        # #mtabs early return — that ordering is the whole reason a landscape tablet gets a real height
        fit_at = self.js.index("fit();window.addEventListener('resize',refit)")
        # the line-anchored form: barfit() looks the bar up the same way, guarded, BEFORE the wiring
        bar_at = self.js.index("\nvar bar=document.getElementById('mtabs');if(!bar)return;\n")
        self.assertLess(fit_at, bar_at)
        # the fork's layout probe __rompMobileOn (2026-09-04) sits ABOVE the lookup-and-return line, so a page
        # with no tab bar still defines it (it answers false there). The lookup and the early return became
        # one line on 2026-09-08 (barfit), so "between the lookup and the return" is no longer a place: the
        # probe precedes the line
        self.assertLess(self.js.index("window.__rompMobileOn=mobileOn;"), bar_at)


if __name__ == "__main__":
    unittest.main()
