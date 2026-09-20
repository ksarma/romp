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
        # or under 820 px takes this fixed body too, at the 0px fit() writes whenever the pointer is not coarse (round 2, 2026-09-19:
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
        # The join is per ELEMENT. Round 5 (2026-09-20): it had been keyed on the subject compound's exact string, so a box
        # whose position:fixed and whose sizing sat under two compounds that select one element but differ by a simple
        # selector (iframe#f-x and #f-x; #f-x and #f-x.big; .ovl and iframe.ovl) landed on two keys, neither both fixed
        # and sized, and was outside the population. A member is now a PAIR of a fixed compound and a sized compound that
        # can select one element (served_css.can_match: one's restricting selectors are a subset of the other's, so a
        # compound is paired with itself too), the element known by the union of the two compounds' simple selectors and
        # named by the canonical compound of that set (served_css.compound: body, iframe.lifted). Pairs, not a union-find
        # over the whole sheet: through a bare `iframe` rule a class join unites every iframe compound, so a second fixed
        # iframe sized by --app-h would have been one member with the lift and the lift's origin would have answered for it.
        # Each member sits at var(--app-top) in a rule inside the mobile block (the lift's base rule is upstream's line and
        # stays byte-identical; the mobile block re-tops it, so a coarse desktop layout keeps the lift at the static body's
        # origin); the origin's rule must SURELY select the element (served_css.surely: its subject's restricting selectors
        # all among the element's, none selecting by a state the sheet cannot show), and its top must BE the pan (a bare var(--app-top) or an alias declared as one,
        # served_css.bare_var and aliases; round 5: a mention had counted, so top:calc(var(--app-top) - 40px) read as the
        # origin), the last top-edge declaration of its own rule, without !important. The cascade is judged over EVERY rule
        # whose subject CAN match the element (a subset or superset of its restricting selectors: iframe, .lifted, `*`,
        # iframe[id], iframe:not(.x); round 5: `*`, attribute selectors and functional pseudo-classes had been read as
        # selectors the element must carry), by specificity, then order, an !important winning outright however spaced
        # (served_css.important), over every property that sets the top edge (top and the inset, inset-block and
        # inset-block-start shorthands, which the sheet uses fourteen times, and `all`, the one shorthand that resets the
        # position and the top edge together; round 6, 2026-09-20). A selector sharing no restricting selector with the
        # member (body.picker-open #f-chat) is outside this reading; the served leg reads the boxes themselves. Round 6
        # closed four more holes the plants had not covered: an origin's rule must carry no attribute selector or functional
        # pseudo-class (served_css.surely refuses them: body:not(.picker-open) cannot be known to select the body, and the
        # reading had dropped them as can_match rightly does); position:fixed is read through a custom-property indirection
        # as the sizing is (served_css.is_fixed with the sheet); the alias table is per member (served_css.aliases with the
        # element: a name a rule that can select the member re-declares to a constant is no alias of the pan there); and
        # the page must link no external stylesheet and import none, or the parse refuses (the population claim below is
        # over the rules the parse returns, and a linked or imported sheet adds or re-tops rules it never sees).
        self.assertEqual(served_css.linked_sheets(self.html), [], "the landing links no external stylesheet (a link whose rel set carries the token, the parser's own predicate): every rule the census judges is in a style element it parses")
        rules = served_css.rules(self.html)
        self.assertGreater(len(rules), 100, "the parse read the served stylesheets: %d rules" % len(rules))
        app_h = served_css.closure(rules, "--app-h")
        sized = lambda r: any(served_css.names_any(v, app_h) for _, v in r.decls)
        fixed_c = sorted({c for r in rules if served_css.is_fixed(r, rules) for c in served_css.subjects(r.selector)})
        sized_c = sorted({c for r in rules if sized(r) for c in served_css.subjects(r.selector)})
        self.assertTrue(fixed_c and sized_c, "derived population empty: fixed compounds %r, --app-h sized compounds %r" % (fixed_c, sized_c))
        known = {}   # canonical compound -> the element's known simple selectors
        for f in fixed_c:
            for sz in sized_c:
                if served_css.can_match(f, sz):
                    k = served_css.restricting(f) | served_css.restricting(sz)
                    known.setdefault(served_css.compound(k), frozenset(k))
        fixed_h = sorted(known)
        self.assertTrue(fixed_h, "derived population empty: no element both position:fixed and sized by --app-h in the served CSS: fixed %r, sized %r"
                        % (fixed_c, sized_c))
        # the split-selector element the per-selector census could not see: the settings lift is position:fixed under one
        # selector string and hidden under another, and the join sees one element. It is NOT sized by --app-h today (inset:0
        # spans the whole layout viewport, so no bare band shows under it; moving it onto the band is a design change the
        # owner decides), so it is outside the census; a sizing by --app-h under EITHER of its selectors puts it in.
        settings = [r for r in rules if "#f-settings" in served_css.subjects(r.selector)]
        self.assertTrue(any(served_css.is_fixed(r, rules) for r in settings) and len({r.selector for r in settings}) >= 2,
                        "the settings lift's rules sit under two selector strings with one subject: %r" % ([(r.at, r.selector) for r in settings],))
        self.assertIn("#f-settings", fixed_c)
        self.assertNotIn("#f-settings", fixed_h, "the settings lift is not sized by --app-h; when it is, it joins the census and takes the origin")
        # the census as of this change, each member named by its canonical compound. A new fixed consumer of --app-h joins
        # this list AND takes the pan (the loop below), or the band opens again under whatever it covers.
        self.assertEqual(fixed_h, ["body", "iframe.lifted"])
        mobile = ("@media " + km._MOBILE_MQ,)
        top_edge = {"top", "inset", "inset-block", "inset-block-start", "all"}
        for el in fixed_h:
            k = known[el]
            app_top = served_css.aliases(rules, "--app-top", el)   # the pan's aliases FOR THIS ELEMENT (round 6)
            is_origin = lambda p, v, names=app_top: p == "top" and served_css.bare_var(v) in names
            sure = [r for r in rules if any(served_css.surely(served_css.subject(m), k) for m in served_css.members(r.selector))]
            may = [r for r in rules if any(served_css.can_match(served_css.subject(m), el) for m in served_css.members(r.selector))]
            origins = [r for r in sure if r.at == mobile and any(is_origin(p, v) for p, v in r.decls)]
            self.assertTrue(origins, "%s has no --app-top origin inside the mobile block in a rule that surely selects it: %r"
                            % (el, [(r.at, r.selector, r.declarations) for r in sure]))
            # the origin is INSIDE the mobile block only (round 4, 2026-09-20, tests-1): outside it, on a coarse desktop layout
            # wider than the query, the body stays in flow at layout y 0, and a lift moved to the pan there would part from
            # the pane rect render.ts placeLifted measures for the transcript backing. The kernel comment over the lift's
            # origin states that condition; this is the assertion that holds it (over every rule that CAN select the element).
            self.assertEqual([(r.at, r.selector, r.declarations) for r in may if r.at != mobile and any(is_origin(p, v) for p, v in r.decls)], [],
                             "%s: a --app-top origin outside the mobile block would move the box on a coarse desktop layout" % el)
            for r in origins:
                tops = [(p, v) for p, v in r.decls if p in top_edge]
                self.assertTrue(is_origin(*tops[-1]), "%s: the origin is not the last top-edge declaration of its own rule: %r" % (el, r.declarations))
                self.assertFalse(any(served_css.important(v) for p, v in tops), "%s: the origin rule's top edge carries no !important: %r" % (el, r.declarations))
            spec = max(served_css.specificity(m) for r in origins for m in served_css.members(r.selector) if served_css.surely(served_css.subject(m), k))
            last = max(r.index for r in origins)
            winners = [(r.at, m, p, v) for r in rules for m in served_css.members(r.selector) if served_css.can_match(served_css.subject(m), el)
                       for p, v in r.decls if p in top_edge and not is_origin(p, v)
                       and (served_css.important(v) or served_css.specificity(m) > spec or (served_css.specificity(m) == spec and r.index > last))]
            self.assertEqual(winners, [], "%s: a rule that can match the element sets its top edge and wins the cascade over the --app-top origin" % el)

    def test_an_unpainted_pane_is_dark_not_white(self):
        # a pane whose document has not painted is a white rectangle in a dark frame (Firefox shows it
        # plainly) — which is exactly what "a white strip at the bottom" looks like
        self.assertIn("iframe{background:#1e1e1e}", self.html)


class ParsedSheetReads(unittest.TestCase):
    """The instrument the census reads through (tests/served_css.py), pinned on the forms round 5 (2026-09-20) found it
    misreading: each case was green under the reading it replaces and is red once against it."""

    def test_a_style_or_script_inside_an_html_comment_is_not_an_element(self):
        # the census had accepted an origin that existed only in commented-out markup, and a pin over scripts() was
        # satisfiable by a commented-out script; the tag-opening count guard counted the commented opening too
        self.assertEqual(served_css.rules("<!-- <style>#x{top:0}</style> -->"), [])
        self.assertEqual(served_css.scripts("<!-- <script>var y=1;</script> -->"), [])
        self.assertEqual(served_css.style_blocks("<!-- <style>#x{top:0}</style> -->"), [])
        page = "<style>#a{top:0}</style><!-- <style>#x{top:0}</style> --><script>var a=1;</script><!-- <script>var y=1;</script> -->"
        self.assertEqual([r.selector for r in served_css.rules(page)], ["#a"])
        self.assertEqual(served_css.scripts(page), ["var a=1;"])
        # the commented markup is comment text to the pins census, and code() blanks it
        self.assertEqual([page[s:e] for s, e in served_css.comment_spans(page)],
                         ["<!-- <style>#x{top:0}</style> -->", "<!-- <script>var y=1;</script> -->"])
        self.assertNotIn("#x", served_css.code(page))
        # a <!-- inside a live script is script text, not a comment: the served timeline script spells one in a regular
        # expression and in its own comments, and a comment opened there would swallow the element's end
        page = '<script>x="<!--";</script><!-- c --><script>y="-->";</script>'
        self.assertEqual(served_css.scripts(page), ['x="<!--";', 'y="-->";'])
        self.assertEqual([page[s:e] for s, e in served_css.comment_spans(page)], ["<!-- c -->"])

    def test_a_statement_at_rule_is_consumed_and_the_rule_after_it_is_read(self):
        # a statement at-rule had accumulated into the next rule's prelude, which then began with @ and was dropped with its
        # declarations as a nested at-rule, silently (round 6, 2026-09-20: the case had used @import, which refuses now)
        sheet = '<style>@charset "utf-8";#planted{position:fixed;height:var(--app-h)}#q{color:red}</style>'
        self.assertEqual([r.selector for r in served_css.rules(sheet)], ["#planted", "#q"])
        sheet = "<style>#a{top:0}@layer base;#planted{position:fixed;height:var(--app-h)}</style>"
        self.assertEqual([r.selector for r in served_css.rules(sheet)], ["#a", "#planted"])
        with self.assertRaises(AssertionError):   # a ; that ends no statement at-rule is refused, not folded
            served_css.rules("<style>#a{top:0};#b{top:0}</style>")

    def test_css_the_parser_cannot_read_refuses_the_way_an_unconsumed_style_tag_does(self):
        # round 6 (2026-09-20): the parse refused an unconsumed <style opening and passed a <link rel=stylesheet> and an
        # @import in silence, though the sheet either names is outside every rule it returns; the census then judged a
        # population an external file could add to or re-top unseen. Both refuse now, unless the caller says the page links
        # its stylesheets by design and wants the style elements alone
        with self.assertRaises(AssertionError) as cm:
            served_css.rules("<link rel=stylesheet href=x.css><style>#a{top:0}</style>")
        self.assertIn("links 1 external stylesheet", str(cm.exception))
        with self.assertRaises(AssertionError):
            served_css.rules("<link href=x.css rel='stylesheet'><style>#a{top:0}</style>")
        with self.assertRaises(AssertionError) as cm:
            served_css.rules("<style>@import url(x.css);#a{top:0}</style>")
        self.assertIn("@import", str(cm.exception))
        with self.assertRaises(AssertionError):
            served_css.rules('<style>@IMPORT "x.css";#a{top:0}</style>')
        self.assertEqual([r.selector for r in served_css.rules("<link rel=stylesheet href=x.css><style>#a{top:0}</style>", linked=True)], ["#a"])
        # a link inside a script string or an HTML comment is not a link element
        self.assertEqual([r.selector for r in served_css.rules('<script>x="<link rel=stylesheet>";</script><!-- <link rel=stylesheet href=y.css> --><style>#a{top:0}</style>')], ["#a"])
        # round 7 (2026-09-20): rel is a SET of tokens and the keyword applies wherever it sits; the token after another had
        # passed in silence while the same sheet under rel=stylesheet refused. linked_sheets is the predicate both the parse
        # and the census's pin read
        for rel in ("'preload stylesheet'", '"stylesheet preload"', "'alternate stylesheet'", "StyleSheet", "'a stylesheet b'"):
            page = "<link rel=%s href=x.css><style>#a{top:0}</style>" % rel
            with self.assertRaises(AssertionError, msg=rel) as cm:
                served_css.rules(page)
            self.assertIn("links 1 external stylesheet", str(cm.exception), rel)
            self.assertEqual(len(served_css.linked_sheets(page)), 1, rel)
        for rel in ("'preload'", '"stylesheets"', "'my-stylesheet'", "icon"):   # no stylesheet token in the set
            page = "<link rel=%s href=x.css><style>#a{top:0}</style>" % rel
            self.assertEqual([r.selector for r in served_css.rules(page)], ["#a"], rel)
            self.assertEqual(served_css.linked_sheets(page), [], rel)
        # round 7 (2026-09-20): a statement at-rule ends at the end of the element as well as at a `;` (CSS Syntax), so a
        # style element that is one `@import` with no semicolon loads the sheet in every engine; the parse had read it as an
        # empty element and refused nothing, and `#a{top:0}@import url(x.css)` returned the #a rule alone
        for sheet in ("<style>@import url(x.css)</style>", "<style>@import 'x.css'</style>", "<style>#a{top:0}@import url(x.css)</style>", "<style>@import url(x.css)\n</style>"):
            with self.assertRaises(AssertionError, msg=sheet) as cm:
                served_css.rules(sheet)
            self.assertIn("@import", str(cm.exception), sheet)
        self.assertEqual(served_css.rules("<style>@charset 'utf-8'</style>"), [], "a trailing statement at-rule that is no import is consumed")
        self.assertEqual([r.selector for r in served_css.rules("<style>#a{top:0}@layer base</style>")], ["#a"])
        with self.assertRaises(AssertionError):   # trailing text that is no at-rule is a parse the instrument cannot account for
            served_css.rules("<style>#a{top:0}#b</style>")

    def test_surely_refuses_a_selector_that_selects_by_a_state_the_sheet_cannot_show(self):
        # round 6 (2026-09-20): surely() had dropped attribute selectors and functional pseudo-classes the way can_match
        # rightly does, so body:not(.picker-open){top:var(--app-top)} was accepted as the body's origin: a rule that may not
        # select the member at all. can_match keeps its reading (a MAY predicate)
        for c in ("body:not(.picker-open)", ":is(#f-chat)", "body[data-x]", "body:where(.a)", "body:nth-child(2)", "[hidden]"):
            self.assertFalse(served_css.surely(c, {"body"}), c)
            self.assertTrue(served_css.can_match(c, "body"), c)
        self.assertTrue(served_css.surely("body", {"body"}) and served_css.surely("*", {"body"}) and served_css.surely("body:hover", {"body", ":hover"}))
        self.assertFalse(served_css.surely("body:hover", {"body"}))

    def test_position_fixed_is_read_through_a_custom_property_as_the_sizing_is(self):
        # round 6 (2026-09-20): is_fixed read the literal keyword while the sizing half of the census resolved var() to a
        # fixed point, so a box whose position came through a var was never in the population. With the sheet, a bare var()
        # resolves against every declaration of the name and against its fallback when undeclared
        rules = served_css.rules("<style>:root{--pos:fixed;--abs:absolute;--via:var(--pos)}#p{position:var(--pos)}#q{position:var(--nope,fixed)}"
                                 "#r{position:var(--abs)}#s{position:var(--via) !important}#t{position:var(--nope,var(--pos))}#u{position:var(--loop)}:root{--loop:var(--loop)}</style>")
        by = {r.selector: r for r in rules if r.selector != ":root"}
        self.assertTrue(served_css.is_fixed(by["#p"], rules))
        self.assertTrue(served_css.is_fixed(by["#q"], rules), "the fallback text when the name is undeclared")
        self.assertFalse(served_css.is_fixed(by["#r"], rules))
        self.assertTrue(served_css.is_fixed(by["#s"], rules), "two levels of indirection, with !important")
        self.assertTrue(served_css.is_fixed(by["#t"], rules), "a fallback that is itself a var()")
        self.assertFalse(served_css.is_fixed(by["#u"], rules), "a self-referential name ends")
        self.assertFalse(served_css.is_fixed(by["#p"]), "with no sheet the keyword alone is read")
        # a name redeclared per element counts if ANY declaration reads fixed (over-inclusive by design)
        rules = served_css.rules("<style>#a{--pos:fixed}#b{--pos:static}#c{position:var(--pos)}</style>")
        self.assertTrue(served_css.is_fixed(rules[2], rules))

    def test_an_alias_a_rule_that_can_select_the_member_redeclares_is_no_alias_for_it(self):
        # round 6 (2026-09-20): aliases() read the sheet globally, so --x:var(--app-top) declared on the lift's own origin
        # rule made top:var(--x) the pan even though the next rule re-declared --x:0 on the same element, and the whole
        # census stayed green while the lift sat at layout y 0 under the pan
        sheet = ("<style>@media (x){body.picker-open iframe.lifted{--x:var(--app-top);top:var(--x)}iframe.lifted{--x:0}"
                 "#f-chat{--y:0}:root{--y:var(--app-top)}}</style>")
        rules = served_css.rules(sheet)
        self.assertEqual(sorted(served_css.aliases(rules, "--app-top")), ["--app-top", "--x", "--y"], "the sheet-global table")
        self.assertEqual(sorted(served_css.aliases(rules, "--app-top", "iframe.lifted")), ["--app-top", "--y"],
                         "--x is re-declared by a rule that can select the lift; --y only by #f-chat, which cannot")
        self.assertEqual(sorted(served_css.aliases(rules, "--app-top", "#f-chat")), ["--app-top", "--x"])
        # round 7 (2026-09-20): the refusal follows the CHAIN on the member's rules. --y declared on the lift's own rule as a
        # bare var() of --x, which the same rule re-declares to 0: the engine computes --y on the lift from the lift's own --x,
        # 0, so top:var(--y) is no origin; the one-pass refusal had kept --y (its value named --x, then still in the set)
        rules = served_css.rules("<style>:root{--x:var(--app-top)}iframe.lifted{--y:var(--x);--x:0;top:var(--y)}</style>")
        self.assertEqual(sorted(served_css.aliases(rules, "--app-top", "iframe.lifted")), ["--app-top"], "--y follows --x out of the table")
        self.assertEqual(sorted(served_css.aliases(rules, "--app-top")), ["--app-top", "--x", "--y"], "the sheet-global table still lists both")
        # ...and stays where the chain's link is declared on :root: the root computes --y as the pan and the lift inherits it,
        # whatever the lift's own --x says
        rules = served_css.rules("<style>:root{--x:var(--app-top);--y:var(--x)}iframe.lifted{--x:0;top:var(--y)}</style>")
        self.assertEqual(sorted(served_css.aliases(rules, "--app-top", "iframe.lifted")), ["--app-top", "--y"])
        # a longer chain on the member's rules empties the same way
        rules = served_css.rules("<style>:root{--x:var(--app-top)}iframe.lifted{--z:var(--y);--y:var(--x);--x:0;top:var(--z)}</style>")
        self.assertEqual(sorted(served_css.aliases(rules, "--app-top", "iframe.lifted")), ["--app-top"])

    def test_can_match_reads_only_the_selectors_that_tell_elements_apart(self):
        # `*`, an attribute selector and a functional pseudo-class had been read as selectors the other compound must also
        # carry, so `*{top:0!important}` was no competitor for the lift's origin
        for other in ("*", "iframe[id]", "iframe:not(.foo)", "iframe:nth-child(2)", "[hidden]", ":is(.a,.b)"):
            self.assertTrue(served_css.can_match(other, "iframe.lifted"), other)
            self.assertTrue(served_css.can_match("iframe.lifted", other), other)
        self.assertEqual(served_css.restricting("iframe:not(.foo)[id]"), {"iframe"})
        self.assertEqual(served_css.restricting("*"), set())
        # what a static reading still cannot unite: a different id, a pseudo-element's own box, a keyframe step
        self.assertFalse(served_css.can_match("#f-chat", "iframe.lifted"))
        self.assertFalse(served_css.can_match("iframe::before", "iframe.lifted"))
        self.assertFalse(served_css.can_match("0%", "iframe"))
        self.assertTrue(served_css.can_match("iframe.lifted::before", "iframe::before"))
        # the element join's two readings: surely (an origin's rule) and the canonical name
        known = served_css.restricting("iframe#f-x") | served_css.restricting("#f-x")
        self.assertEqual(served_css.compound(known), "iframe#f-x")
        self.assertEqual(served_css.compound({".ovl", "iframe"}), "iframe.ovl")
        self.assertEqual(served_css.compound({"#planted", ".big"}), "#planted.big")
        self.assertEqual(served_css.compound(set()), "*")
        self.assertTrue(served_css.surely("#f-x", known) and served_css.surely("iframe", known) and served_css.surely("*", known))
        self.assertFalse(served_css.surely("iframe#f-x.big", known))
        self.assertFalse(served_css.surely("0%", known))

    def test_keywords_functions_and_important_are_read_as_css_reads_them(self):
        # case-insensitive keywords and function names; a custom property's NAME stays case-sensitive
        self.assertTrue(served_css.is_fixed(served_css.Rule(0, (), "#p", "", (("position", "FIXED"),))))
        self.assertTrue(served_css.is_fixed(served_css.Rule(0, (), "#p", "", (("position", "fixed !important"),))))
        self.assertFalse(served_css.is_fixed(served_css.Rule(0, (), "#p", "", (("position", "absolute"),))))
        self.assertEqual(served_css.var_names("VAR(--app-h)"), {"--app-h"})
        self.assertEqual(served_css.var_names("var( --App-h )"), {"--App-h"})
        self.assertEqual(served_css.declarations("--App-h:1px;Position:FIXED"), [("--App-h", "1px"), ("position", "FIXED")])
        for v in ("0!important", "0 ! important", "0!IMPORTANT", "var(--x) !important"):
            self.assertTrue(served_css.important(v), v)
        self.assertFalse(served_css.important("0"))
        self.assertFalse(served_css.important("important"))

    def test_a_bare_var_is_the_value_and_a_mention_is_not(self):
        # the origin must BE the pan: top:calc(var(--app-top) - 40px) names it and sits 40 px off it
        for v in ("var(--app-top,0px)", "var(--app-top)", " var( --app-top , calc(1px + 2px) ) ", "VAR(--app-top)!important"):
            self.assertEqual(served_css.bare_var(v), "--app-top", v)
        for v in ("calc(var(--app-top,0px) - 40px)", "var(--app-top,0px) - 40px", "var(--a,0px) + var(--b)", "var(--a) var(--b)", "0px"):
            self.assertIsNone(served_css.bare_var(v), v)
        rules = served_css.rules("<style>:root{--x:var(--app-top)}:root{--y:calc(var(--x) - 4px)}:root{--z:var(--y,1px)}</style>")
        self.assertEqual(sorted(served_css.closure(rules, "--app-top")), ["--app-top", "--x", "--y", "--z"], "every mention, for the consumers tripwire")
        self.assertEqual(sorted(served_css.aliases(rules, "--app-top")), ["--app-top", "--x"], "the names whose value IS the pan, for the origin")
        self.assertEqual(sorted(served_css.aliases(rules, "--app-top", "body")), ["--app-top", "--x"], "no rule re-declares --x: the member form agrees")


class RefitsWhenTheVisibleHeightChanges(unittest.TestCase):
    def setUp(self):
        self.js = km._LANDING_MOBILE_JS

    def test_it_drives_app_h_off_the_live_visual_viewport(self):
        # pinch-aware since 2026-08-19: the fine-pointer road reads innerHeight on upstream's line (its premise, "pinch-immune in
        # every browser", and the fork's contrary engine model both live in the fit() comment, the one home, with their evidence
        # status), and the fork line after it re-reads the layout viewport as documentElement.clientHeight before the --app-h
        # write (round 8, 2026-09-20; a no-op wherever innerHeight was right, standards mode pinned and the page overflow:hidden);
        # the visual viewport drives the fit only on coarse-pointer devices, where the soft keyboards and collapsing toolbars it
        # exists for live, scale-guarded against mobile pinches. Behaviour: test_kernel_mobile.MobileFitExecutes drives that road
        # with innerHeight parted from clientHeight.
        self.assertIn("var coarse=window.matchMedia&&matchMedia('(pointer: coarse)').matches;", self.js)
        self.assertIn("var h=(!coarse||!vv)?window.innerHeight:Math.round(vv.height*(vv.scale||1));", self.js)
        self.assertIn("if(!coarse||!vv)h=document.documentElement.clientHeight||h;\nif(h)document.documentElement.style.setProperty('--app-h',h+'px');", self.js,
                      "the fork's re-read of the layout viewport on the fine-pointer road, right before the --app-h write")
        self.assertIn("setProperty('--app-h',h+'px')", self.js)
        # D1 (2026-09-19): the visual viewport's PAN rides beside the height. iOS reveals a focused input by moving the
        # visual viewport down the layout viewport (offsetTop > 0) with no document scroll to undo, so a body sized to
        # vv.height at layout y 0 left the bottom offsetTop pixels of the screen bare under the composer. fit() publishes
        # the pan as --app-top under the same coarse guard (a fine pointer writes 0px whatever the visual viewport says; the
        # consumer is gated on the layout query, a different population, see the fit() comment). Under a pinch (scale above 1.01) the last pan
        # holds, a zoom pans too and never re-lays the shell, CLAMPED AT USE to the layout viewport less the height the same
        # run publishes, so a keyboard dismissed while zoomed cannot leave the body hanging below the viewport (round 2,
        # 2026-09-19); the layout viewport is document.documentElement.clientHeight, the same height in both engine models
        # (round 7, 2026-09-20: it had read window.innerHeight, which WebKit shrinks to the visual viewport's height under a
        # pinch under the engine model the fit() comment states, the one home, holding by WebKit's source and a Chromium run
        # with the on-device read as the only real-engine confirmation, so there the difference was below 0 on every zoomed
        # run and the road published 0px whatever the hold; the harness drives both models); the clamp bounds what is published and never writes back into the hold (round 4, 2026-09-20: it had,
        # so the hold decayed to 0 the first time the clamp bound and a keyboard raised again under the zoom reopened the
        # band). Every road that WRITES the hold writes the value it publishes: the measured road its measurement, the 0px
        # road a zero, and that only in a true no-pan state (no visual viewport, or one at or under the pinch road's cut, scale
        # 1.01, whose offsetTop rounds to no positive pixel, panPx, the one reading the measured road stores too, so a sub-pixel
        # pan is the same answer on both roads, round 8, 2026-09-20; round 6, 2026-09-20: written on every fine run, the zero had reopened the band after a pointer flip under a keyboard or a
        # zoom); the clamp road publishes a bound of the hold and stores nothing, so --app-top can sit below the hold until a
        # writing road runs next (round 6: this comment had said the hold is the last value published on every road, which
        # the clamp road contradicts whenever it binds, and the harness asserts that state). Both coarse branches sit under
        # the height's own validity guard (h truthy, the `if(h)` of the --app-h write above them): a refused height report
        # publishes no pan either, so the prior pan stands beside the prior height (round 4, 2026-09-20, as round 1
        # confirmed it); the 0px road has no height to belong to and publishes unconditionally. Behaviour:
        # test_kernel_mobile.MobileFitExecutes.
        self.assertIn("\nvar lastPan=0;\n", self.js)
        self.assertIn("\nfunction panPx(vv){return Math.round(vv.offsetTop||0);}\nfunction fit(){", self.js, "the one reading of the pan, declared before fit()")
        self.assertIn("if(!coarse||!vv){if(!vv||((vv.scale||1)<=1.01&&!(panPx(vv)>0)))lastPan=0;document.documentElement.style.setProperty('--app-top','0px');}", self.js)
        self.assertNotIn("vv.offsetTop>0", self.js, "the 0px road reads the shared rounding, never the raw offsetTop")
        self.assertIn("else if(h&&(vv.scale||1)<=1.01)document.documentElement.style.setProperty('--app-top',(lastPan=panPx(vv))+'px');\n"
                      "else if(h)document.documentElement.style.setProperty('--app-top',Math.min(lastPan,Math.max(0,document.documentElement.clientHeight-h))+'px');", self.js)
        self.assertNotIn("innerHeight-h", self.js, "the clamp reads the layout viewport (clientHeight), not innerHeight, which WebKit shrinks under a pinch")
        self.assertNotIn("lastPan=Math.min", self.js, "the clamp is at use: nothing writes its result back into the hold")
        # the write sits inside fit(), after the --app-h write and before the stray-scroll reset, so one frame publishes both
        self.assertLess(self.js.index("setProperty('--app-h',h+'px')"), self.js.index("setProperty('--app-top'"))
        self.assertLess(self.js.index("setProperty('--app-top'"), self.js.index("if(window.scrollY||document.documentElement.scrollTop)window.scrollTo(0,0);"))

    def test_the_bars_reservation_follows_the_bars_own_box(self):
        # D1 (2026-09-19): barfit is rebound rather than edited because fit() calls it by name; upstream's declaration stands,
        # saved as barfitVV, and upstream's kbOpen stands untouched beside it. The strip is the part of the bar's BOX inside
        # the band the same run PUBLISHED (--app-top to --app-top + --app-h, read back from the style object, so a pinch,
        # whose pan holds and whose height is upstream's scale arithmetic, is judged against the shell it laid out): the
        # overlap of the two intervals, max(0, min(bar.bottom, bandBottom) - max(bar.top, bandTop)): 0 for a bar starting at
        # or below the band's bottom edge or ending at or above its top edge, the whole height wholly inside, the overlap
        # between (round 4, 2026-09-20: the reservation had been all-or-nothing on a visibility verdict, a bar-tall strip
        # over a bar showing a few pixels; and the pinch term had handed the verdict back to upstream's height difference,
        # which collapsed the strip at the 1.01 scale cut under a deep pan; round 6, 2026-09-20: the first proportional
        # form read the bottom edge only, so a band whose top sat below the bar's top reserved pixels above the band, the
        # whole bar over a bar with no pixel inside it). Upstream's barfit stands only where the box or the band cannot be
        # read (no bar, no visualViewport, no getPropertyValue, a run before both variables are published). Behaviour:
        # test_kernel_mobile.MobileFitExecutes (the sweep across the pan range, the pinch over the deep pan).
        self.assertIn("function kbOpen(){var vv=window.visualViewport;return vv?(window.innerHeight-vv.height*(vv.scale||1)>120):false;}", self.js)
        self.assertIn("function barfit(){try{var bar=document.getElementById('mtabs');if(!bar)return;\n"
                      "document.documentElement.style.setProperty('--mtabs-h',(kbOpen()?0:(bar.offsetHeight||0))+'px');}catch(e){}}\n", self.js)
        self.assertIn("var barfitVV=barfit;\nbarfit=function(){try{var vv=window.visualViewport,bar=document.getElementById('mtabs'),st=document.documentElement.style;\n"
                      "if(!vv||!bar||typeof bar.getBoundingClientRect!=='function'||typeof st.getPropertyValue!=='function'){barfitVV();return;}\n"
                      "var top=parseFloat(st.getPropertyValue('--app-top')),h=parseFloat(st.getPropertyValue('--app-h'));\n"
                      "if(!(top>=0)||!(h>0)){barfitVV();return;}\n"
                      "var r=bar.getBoundingClientRect().top;st.setProperty('--mtabs-h',Math.max(0,Math.min(r+(bar.offsetHeight||0),top+h)-Math.max(r,top))+'px');}catch(e){}};", self.js)
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
