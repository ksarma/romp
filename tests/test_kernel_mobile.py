#!/usr/bin/env python3
"""Mobile shell: the combined landing page collapses to a one-pane-at-a-time tab switcher on a
narrow/touch viewport, and the kernel tells the shell to switch to Chat when a feed/timeline tap
brings the chat forward. Pure-HTML + routing asserts; no real session data.
"""
import json
import math
import os
import re
import shutil
import subprocess
import sys
import unittest
from romp_load import load_source
import tempfile

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
km = load_source("romp_kernel_mobile", os.path.join(BIN, "romp-kernel"))
sys.path.insert(0, HERE)
from test_pane_shim_return import HARNESS as _PANE_HARNESS, _run as _run_pane   # noqa: E402  the pane shim's node fakes and its pane-only runner (never its TestCases), for the linked runs below
import served_css   # noqa: E402  the served page's parsed rules (loads no romp code)


# The page-to-kernel keys the lazy panes' three client-diag rows posted (pane-load-failed and pane-load-unmarked on the shell's socket,
# reveal-dropped from the feed), WITHHELD: the reviewer's round-7 ruling on regression-1 found none of the seven needed by the feature (no
# page state moves without them, and no reader in kernel/, bin/, cli/ or ui/ read the rows back), so the rows and the keys were dropped and
# none went to the owner. A new field a page posts to the kernel is the owner's to approve, field by field (tests/test_client_diag_allowlist.py),
# so this is written to revert: the owner's yes moves a pair from _DIAG_KEYS_WITHHELD into _DIAG_KEYS_APPROVED with its date, and the pin
# then holds the pair present. It keys on (surface, key) pairs, so it cannot see a re-route under a key another surface already admits
# (`n` and `sid` are chat's; `why` is chat's, federation's, pane-shim's and shell's); the writer pins catch that: LazyPanes' unfiltered
# clientDiag read in tests/test_pane_state_broadcast.py and the posted list in ui/webview/feed-hidden-paint.test.ts.
_DIAG_KEYS_WITHHELD = (("shell", "pane"), ("shell", "n"),
                       ("feed", "itemId"), ("feed", "sid"), ("feed", "why"), ("feed", "key"), ("feed", "painted"))
_DIAG_KEYS_APPROVED = ()   # (surface, key, the owner's date) for a pair moved out of _DIAG_KEYS_WITHHELD on the owner's word


def _mobile_js():
    """The phone shell script AS THE PAGE RUNS IT: the served template itself. _landing() splices the layout probe's
    media query inline when the template is built (json.dumps(_MOBILE_MQ) in the template string), so there is no
    placeholder left for an executor to fill and the harness runs the template as served. Kept as the ONE door every
    executor class reads the script through, so a future splice is a one-line adoption here and nowhere else."""
    return km._LANDING_MOBILE_JS


def _viewport_meta_tokens(html):
    """The viewport META's content attribute as its comma-separated tokens, read from the ONE live meta element through the
    parser (served_css.meta_content; the standalone flip rewrites the attribute from script and serves no second tag). A pin
    over these reads the element it pins: the fit script's served comments spell the same tokens in prose, and a substring
    assertion over the whole page was satisfied by a comment after the meta had lost the token it exists to pin (D1, the maintainer's round 1,
    2026-09-19). The author's pass 9 (2026-09-20, the maintainer's round 5 ruling): the helper had found the meta by a regular expression
    over the RAW page, so a meta written inside an HTML comment read as the live one, the exact case it existed to stop; the
    element layer reads a commented meta as comment text and a live one whatever its attribute order or quoting."""
    return (served_css.meta_content(html, "viewport") or "").split(",")


def _live_scripts(html):
    """[(element, code)] for every live script element of a served page, in document order: the element as the parser reads it
    (served_css.elements: its offsets, its attributes, the elements open at its start tag) and its content through
    served_css.js_code, the code with its comments blanked and its offsets kept, so `element.content_start + code.index(x)` is x's
    offset in the page. The parser road for a read of a script's text in this module (the landing merge of main, 2026-09-30: the
    lazy panes' tests, fork PR 821, had searched the raw page for a script constant's text and for the layout probe's, and the census
    in tests/test_served_pins_read_elements.py fails such a read in a module that imports served_css); a script inside an HTML
    comment is comment text and no element."""
    by_start = {el.content_start: el for el in served_css.elements(html) if el.kind == "script"}
    return [(by_start[s], served_css.js_code(html[s:e])) for s, e, kind in served_css.element_spans(html) if kind == "script"]


def _head_code(scripts):
    """The code of the head script among a page's live scripts (_live_scripts): the one live script element inside <head>, which
    the notified-session seed's cells execute and read. Refuses a head with no script, or with more than one."""
    heads = [code for el, code in scripts if "head" in el.stack]
    assert len(heads) == 1, "one live script element in the head, found %d" % len(heads)
    return heads[0]


class ViewportMetaReader(unittest.TestCase):
    """The viewport meta helper reads the ELEMENT (the author's pass 9, 2026-09-20, the maintainer's round 5 ruling): it had matched a regular
    expression over the raw page, so a meta written inside an HTML comment read as the live one, the exact case the helper existed
    to stop, and it pinned one attribute order and one quoting. Each case here was green under the regex where it should have
    refused, or refused where it should have read. The reader feeds the whole page to the tokenizer in one call, so a tag split
    across a chunk boundary is not a state it can be in (no chunked case)."""
    LIVE = "<meta name=viewport content='a=1,b=2'>"

    def test_a_meta_inside_a_comment_or_a_script_string_is_not_the_live_meta(self):
        commented = "<!-- <meta name=viewport content='x=9'> -->"
        self.assertEqual(_viewport_meta_tokens("<head>%s%s</head>" % (commented, self.LIVE)), ["a=1", "b=2"], "the live meta beside a commented copy")
        with self.assertRaises(AssertionError) as cm:
            _viewport_meta_tokens("<head>%s</head>" % commented)
        self.assertIn("found 0", str(cm.exception), "a commented meta alone is no meta: the helper refuses loudly")
        self.assertEqual(_viewport_meta_tokens("<head><script>var s=\"<meta name=viewport content='x=9'>\";</script>%s</head>" % self.LIVE), ["a=1", "b=2"])

    def test_the_live_meta_is_read_whatever_its_spelling(self):
        for meta in ("<META NAME=Viewport CONTENT='a=1,b=2'>", '<meta content="a=1,b=2" name="viewport">', "<meta content=a=1,b=2 name=viewport>",
                     "<meta charset=utf-8 name=viewport content='a=1,b=2'/>"):
            self.assertEqual(_viewport_meta_tokens("<head>%s</head>" % meta), ["a=1", "b=2"], meta)
        with self.assertRaises(AssertionError):
            _viewport_meta_tokens("<head><meta name=' viewport ' content='a=1'></head>")   # the name is compared as written: not this meta
        with self.assertRaises(AssertionError) as cm:
            _viewport_meta_tokens("<head>%s%s</head>" % (self.LIVE, self.LIVE))
        self.assertIn("found 2", str(cm.exception))
        self.assertEqual(_viewport_meta_tokens("<head><meta name=viewport></head>"), [""], "a meta with no content has no tokens, and a pin over the tokens fails on it")


class LandingShell(unittest.TestCase):
    def test_three_panes_are_addressable_iframes(self):
        html = km._landing()
        for fid in ("id=f-chat", "id=f-feed", "id=f-timeline"):
            self.assertIn(fid, html)

    def test_mobile_tabbar_one_button_per_pane(self):
        html = km._landing()
        self.assertIn("id=mtabs", html)
        for pane in ("data-pane=chat", "data-pane=fleet", "data-pane=feed", "data-pane=timeline"):
            self.assertIn(pane, html)

    def test_outline_is_a_mobile_tab_not_desktop_only(self):
        # the user 2026-07-11, who couldn't access the outline view in the mobile UI — the fleet pane was
        # explicitly desktop-only (#fleet-pane display:none!important, no tab, no switcher entry).
        html = km._landing()
        self.assertIn(">Outline</button>", html)                       # the tab exists, labeled Outline
        self.assertIn("#f-chat.m-on,#f-fleet.m-on,#f-feed.m-on,#f-waiting.m-on,#f-files.m-on{display:block}", html)   # ...and shows as the active pane
        self.assertNotIn("#fleet-pane{display:none!important}", html)  # the desktop-only exclusion is gone
        self.assertIn("fleet:document.getElementById('f-fleet')", km._LANDING_MOBILE_JS)
        # the chat header's Fleet pill / the fleet's back-to-chat (toggleFleet) is a tab switch on mobile
        self.assertIn("'toggleFleet'", km._LANDING_MOBILE_JS)

    def test_rail_actions_reachable_on_mobile(self):
        # the user 2026-07-11: settings / the network panel / usage stats were rail-only (the rail is
        # hidden on mobile). data-act buttons on the bar; each routes to the existing machinery.
        html = km._landing()
        for act in ("data-act=settings", "data-act=net", "data-act=usage", "data-act=restart"):
            self.assertIn(act, html)
        # ICONS, not words (the user 2026-07-11): settings wears the desktop rail's own gear glyph, net its
        # network-tree SVG; usage gets the theme's own motif — two stacked fill bars at different levels
        # the settings icon is the SAME gear the desktop rail uses (U+26ED ⛭), not the outlined star it had
        self.assertIn("data-act=settings data-keycmd=settings.open aria-label=Settings title=Settings>⛭</button>", html)
        self.assertIn("id=rail-gear data-keycmd=settings.open title=Settings aria-label=Settings>⛭</div>", html)  # matches the rail
        self.assertNotIn("&#9885;", html)                               # the old outlined-star glyph is gone
        self.assertIn("data-act=net data-keycmd=net.open aria-label='Remote kernels'", html)
        self.assertIn("<rect x='1' y='3' width='9' height='4' rx='1' fill='currentColor'/>", html)   # the used-bar fill
        self.assertNotIn(">Gear</button>", html)
        self.assertIn("window.__rompOpenSettings&&window.__rompOpenSettings();", km._LANDING_MOBILE_JS)   # same path as the desktop gear: the settings iframe
        self.assertIn("__rompOpenNet", km._LANDING_MOBILE_JS)           # opens the shell's remotes panel
        self.assertIn("window.__rompOpenNet=open", km._LANDING_REMOTES_JS)
        self.assertIn("__rompUsagePanel", km._LANDING_MOBILE_JS)        # the tooltip's bars as a modal
        self.assertIn("window.__rompUsagePanel=function", km._LANDING_USAGE_JS)
        self.assertIn("#ru-tip.ru-modal", html)                         # centered placement for the panel
        # the lifted-fullscreen settings iframe must override the mobile display:none
        self.assertIn("body.settings-open #f-settings{display:block;position:fixed", html)

    def test_mobile_restart_button_reuses_the_rail_refresh_kernel_restart(self):
        # the user 2026-07-22: there was no restart-kernel affordance on mobile (the rail's own ↻ is hidden
        # there). Add a bar button that fires the SAME restart the rail does — factored to window.__rompRestart
        # (POST /restart, poll /healthz, reload) so both surfaces share one path, not a copy.
        html = km._landing()
        # …and it wears the SAME browser-style reload svg as the rail (the ↻ text glyph is gone, 2026-07-27)
        self.assertIn("data-act=restart data-keycmd=kernel.restart aria-label='Restart kernel' title='Restart kernel'>" + km._REFRESH_SVG + "</button>", html)
        self.assertIn("window.__rompRestart=function", km._LANDING_SETTINGS_JS)   # the shared restart path
        self.assertIn("fetch('/restart',{method:'POST'})", km._LANDING_SETTINGS_JS)
        self.assertIn("rf.onclick=function(){rf.style.pointerEvents='none';rf.style.opacity='0.5';window.__rompRestart();}", km._LANDING_SETTINGS_JS)
        self.assertIn("restart:function(){try{window.__rompRestart", km._LANDING_MOBILE_JS)   # the bar routes to it

    def test_mobile_bar_reservation_collapses_while_the_keyboard_is_open(self):
        # the user 2026-07-22: focusing the composer opened the keyboard and left a dead black band between
        # the box and the keyboard — the fixed bar's reserved height (--mtabs-h) showing through while the
        # bar itself was hidden behind the keyboard. Collapse the reservation to 0 when the keyboard is open
        # (visual viewport much shorter than the layout viewport), restore it when the keyboard closes.
        # The author's pass 6 (2026-09-20): these are source pins on upstream's lines, and since D1 rebound barfit the
        # write pinned last runs only on the FALLBACK road (no bar, no visualViewport, a style object without
        # getPropertyValue, a run before fit() published the band; reached through barfitVV), so this test no
        # longer decides the phone's strip: a rebound write reserving the bar's whole height while the keyboard
        # hides it keeps every line here green. The behaviour for the 2026-07-22 report is held by
        # MobileFitExecutes (test_the_2026_07_22_dead_band_the_strip_collapses_while_the_keyboard_hides_the_bar,
        # the keyboard legs and the sweep), which execute the served script; the rebound write's own bytes are
        # pinned once, in test_shell_viewport_fit.
        js = km._LANDING_MOBILE_JS
        # scale-aware (the user 2026-08-19): a desktop pinch shrinks vv.height by the zoom factor; height*scale
        # recovers the layout height, so a pinch never reads as "keyboard open" (or re-fits --app-h smaller)
        self.assertIn("function kbOpen(){var vv=window.visualViewport;return vv?(window.innerHeight-vv.height*(vv.scale||1)>120):false;}", js)
        # the fine-pointer road: upstream's line reads innerHeight (its premise, "pinch-immune in every browser", and the fork's
        # contrary engine model both live in kernel.py's fit() comment, the one home, with their evidence status; the author's pass 8,
        # 2026-09-20), and the fork lines after it read the layout viewport once, as documentElement.clientHeight, for every
        # road (the author's pass 9, 2026-09-20) and take it as this road's height; the visual viewport drives the fit only on
        # coarse-pointer devices, where keyboards/toolbars live
        self.assertIn("var coarse=window.matchMedia&&matchMedia('(pointer: coarse)').matches;", js)
        self.assertIn("var h=(!coarse||!vv)?window.innerHeight:Math.round(vv.height*(vv.scale||1));", js)
        self.assertIn("var L=document.documentElement.clientHeight||window.innerHeight;\nif(!coarse||!vv)h=L;", js)   # the fork's re-read of the layout viewport (the author's pass 8; one read for every road, the author's pass 9)
        self.assertIn("--mtabs-h',(kbOpen()?0:(bar.offsetHeight||0))+'px'", js)   # upstream's write: the fallback road's own pin

    def test_usage_modal_dismisses_via_a_real_backdrop_not_a_document_click(self):
        # the user 2026-07-22: on mobile the Usage panel got STUCK — an outside tap landed on a content
        # iframe (a different document), so the shell's document-level click listener never fired and the
        # modal never closed. Fix: a real full-screen backdrop in the SHELL document (like the net panel's
        # #rnet-back) catches the tap, so any tap over it dismisses. The #ru-tip is pointer-events:none, so
        # a tap that visually lands on the panel still reaches the backdrop underneath and closes it.
        html, js = km._landing(), served_css.js_code(km._LANDING_USAGE_JS)   # the code, comments blanked (a comment names the backdrop too)
        self.assertIn("ru-back", js)                              # the backdrop element is created
        self.assertIn("back.onclick=off", js)                    # a tap on the backdrop closes the modal
        self.assertIn("back.classList.add('on')", js)            # ...shown when the panel opens
        self.assertIn("#ru-back{position:fixed;inset:0", html)   # full-screen, in the shell document
        self.assertIn("#ru-back.on{display:block}", html)
        # the old broken mechanism (a document-level capture click listener) is gone
        self.assertNotIn("addEventListener('click',off,true)", js)

    def test_desktop_unchanged_tabbar_hidden_until_breakpoint(self):
        html = km._landing()
        self.assertIn("#mtabs{display:none}", html)   # hidden by default (desktop)
        self.assertIn("@media", html)                 # a breakpoint reveals it + collapses to one pane
        self.assertIn(".m-on{display:block}", html)   # the single active pane on mobile
        # the desktop shell is the flex pane row (chat | fleet | feed | timeline)
        self.assertIn(".col{display:flex", html)
        self.assertIn("src=/chat", html)
        self.assertIn("data-src=/feed", html)   # optional panes load from data-src (the Panes setting)
        self.assertIn("data-src=/timeline", html)

    def test_the_shell_leaves_a_hair_of_slack_down_the_right_edge(self):
        # The panes tiled flush to the window, so whatever sat hard right inside one — a feed card's
        # controls, the timeline's lock padlock at the now-edge, the rail's right-pinned actions — was
        # pressed against the frame or clipped by it (the user 2026-07-23). .col is the one wrapper that
        # covers the pane row, the timeline band and the bottom rail together.
        html = km._landing()
        # height:100%, not 100vh: the body is what clips, and on iOS 100vh is the address-bar-collapsed
        # viewport, which pushed the rail out of the bottom (the user 2026-07-29)
        self.assertIn(".col{display:flex;flex-direction:column;height:100%;box-sizing:border-box;padding-right:3px}", html)
        # border-box, or the strip ADDS to the 100vh box and the shell overflows instead of insetting
        self.assertIn("box-sizing:border-box;padding-right:3px", html)

    def test_the_right_edge_strip_is_desktop_only(self):
        # One pane fills a phone screen, so a 3px sliver of backdrop down its edge reads as a rendering
        # fault, not as slack. The desktop longhand survives the media query unless it is named there.
        html = km._landing()
        # the .col rule inside the mobile block, read as a parsed rule (the author's pass 9, 2026-09-20: a 2000-character window of raw page
        # text after the query's first spelling had stood for the block)
        mobile = ("@media " + km._MOBILE_MQ,)
        col = [(p, v) for r in served_css.rules(html) if r.at == mobile and ".col" in served_css.subjects(r.selector) for p, v in r.decls]
        self.assertIn(("padding-right", "0"), col, "the mobile .col must cancel the desktop strip: %r" % (col,))

    def test_mobile_pane_has_explicit_height_not_auto(self):
        # regression: the mobile pane was sized with height:auto + bottom offset; mobile browsers read
        # height:auto on an iframe as "size to content" and collapse it (chat shrank to its tab bar).
        html = km._landing()
        # the unit read from the parsed declarations (a served comment spells 100dvh too; a page-text pin was satisfiable by it)
        self.assertTrue(any("100dvh" in v for r in served_css.rules(html) for _, v in r.decls), "explicit, address-bar-aware viewport height")
        self.assertNotIn("height:auto;display:none", html)     # the collapsing iframe rule is gone

    def test_shell_reserves_the_bar_height_so_it_cannot_cover_the_pane(self):
        # regression: a position:fixed bar overlapped the chat composer (which is why flex briefly replaced
        # it). The bar is fixed again — glued to the viewport bottom so no dead space can sit below it — but
        # now .col RESERVES the bar's measured height (--mtabs-h) as padding-bottom, so the iframes tile
        # ABOVE the bar and it can't cover the composer. One pane shows at a time, keyed off body[data-tab].
        html = km._landing()
        self.assertIn("padding-bottom:var(--mtabs-h", html)    # .col reserves the bar's height
        self.assertIn("--mtabs-h", served_css.js_code(km._LANDING_MOBILE_JS))      # ...measured from the live bar (offsetHeight); the code, comments blanked
        self.assertIn("#f-timeline.m-on{display:block}", html) # timeline is a mobile tab pane (it lives in the row now)
        self.assertIn("data-tab", served_css.js_code(km._LANDING_MOBILE_JS))       # show() marks the active pane on <body>; the code, comments blanked (a comment of the lazy panes spells it)

    def test_lazy_panes_markup_loader_and_the_promotions_place_in_show(self):
        # stage 0 (2026-09-18): the Waiting and Files panes are served with data-src (_LANDING_DESKTOP_PANES_JS promotes them at boot on
        # the desktop, the mobile script on their first tap on the phone; the Files line is the one upstream markup token this fork changes); the
        # chat keeps its src (the reveal landing reads its document). The shell's loader for a loading pane is one
        # element, painted for the shown tab by body.pane-loading inside the phone media block, in _pane_spin's dress.
        html = km._landing()
        js = km._LANDING_MOBILE_JS
        self.assertIn("<iframe id=f-waiting data-src=/waiting>", html)
        self.assertIn("<iframe id=f-chat class=m-on src=/chat>", html)
        self.assertIn("<iframe id=f-files data-src=/files>", html)
        self.assertNotIn("<iframe id=f-files src=", html)
        self.assertEqual(html.count("<div id=pane-load>"), 1)
        # tests-2 (review round 1, 2026-09-19): the element CARRIES the romp loader (ui/CLAUDE.md's wait-state rule), as the boot splash's pin
        # does (tests/test_kernel_refresh_button.py), its first content; the failed-load message is its second child (HIGH 2)
        self.assertIn("<div id=pane-load>" + km._loader_inner() + "<div id=pane-load-msg role=alert></div><button id=pane-load-retry type=button hidden>Try again</button></div>", html,
                      "the shell's pane loader is the romp loader first, then the failed-load message (announced: role=alert), then the retry button, hidden until the failed paint (review round 3, ui-1)")
        self.assertIn("#pane-load-retry[hidden]{display:none}", html)
        self.assertIn("#pane-load-retry:focus-visible{outline:2px solid var(--accent,#9cd2ff);outline-offset:2px}", html, "the keyboard focus ring")
        self.assertIn("body.theme-light #pane-load-retry{border-color:rgba(0,0,0,0.3);color:#222}", html)
        self.assertIn("var rb=document.getElementById('pane-load-retry');if(rb){rb.hidden=!bad;if(bad&&RFOC){RFOC=false;try{rb.focus();}catch(e){}}}", js, "paintLoading shows the button in the failed state alone, and puts the keyboard's focus back on it after its own retry (review round 4, ui-1)")
        self.assertIn("if(prb)prb.addEventListener('click',function(ev){try{ev.stopPropagation();}catch(e){}retry();RFOC=true;});", js, "the button's click retries (a real button: Enter and Space run it natively)")
        self.assertLess(html.index("<div id=romp-boot>"), html.index("<div id=pane-load>"))
        self.assertIn("#pane-load{display:none}", html)
        self.assertIn("#pane-load-msg{display:none;", html)
        self.assertIn("body.pane-failed #pane-load{display:flex;flex-direction:column;gap:14px;cursor:pointer}", html, "the failed state keeps the element up (a tap on it retries)")
        self.assertIn("body.pane-failed #pane-load>.rl-in{display:none}", html, "…with the loader down and the message in its place")
        self.assertIn("body.pane-failed #pane-load-msg{display:block}", html)
        # where a pane-load rule sits, read as parsed rules (served_css.rules; the landing merge of main, 2026-09-30: the raw page's first
        # spelling of the phone query had stood for the media block, a read the census fails in a module on the parser road)
        mobile = ("@media " + km._MOBILE_MQ,)
        placed = lambda sel, decl: [r.at for r in served_css.rules(html) if r.selector == sel and decl in r.decls]
        self.assertEqual(placed("body.pane-failed #pane-load", ("display", "flex")), [mobile], "the failed paint lives inside the phone media block too")
        self.assertIn("#pane-load{position:fixed;left:0;right:0;top:0;bottom:var(--mtabs-h,2.6em);z-index:15;align-items:center;justify-content:center;background:#1e1e1e}", html)
        self.assertIn("body.pane-loading #pane-load{display:flex}", html)
        self.assertIn("body.theme-light #pane-load{background:#F1EAE2}", html)
        self.assertEqual(placed("body.pane-loading #pane-load", ("display", "flex")), [mobile], "the paint lives inside the phone media block")
        self.assertEqual(placed("#pane-load", ("display", "none")), [()], "hidden by default, outside it")
        self.assertEqual(html.count("<script>"), 22, "+1 2026-09-19: the desktop promotion of the Waiting and Files panes (_LANDING_DESKTOP_PANES_JS), its own script so a throw in the mobile script cannot strand a desktop pane (review round 1); the mobile script carries the lazy panes")
        # D7 (review round 1, regression-5): the desktop promotion is its own element, spliced BEFORE the mobile script, reading the media query itself
        # read as live script elements, each one's code through served_css.js_code (_live_scripts; the landing merge of main, 2026-09-30:
        # the raw page's spelling of the constant had stood for the element)
        desk = served_css.js_code(km._LANDING_DESKTOP_PANES_JS)
        own = [el for el, code in _live_scripts(html) if code == desk and not el.attrs]
        self.assertEqual(len(own), 1, "one live <script> element, with no attribute, whose code is the desktop promotion's: %r" % ([el.content_start for el in own],))
        self.assertLess(own[0].content_start, html.index("var LAZY='data-lazy-src'"), "the desktop promotion runs before the mobile script")
        self.assertIn("matchMedia(" + json.dumps(km._MOBILE_MQ) + ")", km._LANDING_DESKTOP_PANES_JS, "it reads the layout from the shared media query, not from the mobile script's probe")
        self.assertNotIn("__rompMobileOn", km._LANDING_DESKTOP_PANES_JS)
        self.assertIn("['f-waiting','f-files'].forEach(", km._LANDING_DESKTOP_PANES_JS)
        self.assertNotIn("else{promote('waiting');promote('files');}", js, "the mobile script's boot block no longer carries the desktop promotion")
        # show(): the promotion sits between the persist and the re-tell (upstream's lines on both sides), so the pane hears the word on its load
        self.assertIn("try{localStorage.setItem(KT,p);}catch(e){}\ntry{if(mobileOn()){promote(p);paintLoading();}}catch(e){}", js)
        # D3 (review round 2, 2026-09-19): the shown pane's synchronous show hook, inserted right after the m-on toggle (upstream's line) and before the button loop
        self.assertIn("F[k].classList.toggle('m-on',k===p);   // a pane this shell lacks is skipped, never a TypeError\ntry{var pw=F[p]&&F[p].contentWindow;if(mobileOn()&&pw&&pw.__rompPaneShown)pw.__rompPaneShown();}catch(e){}", js)
        self.assertLess(js.index("pw.__rompPaneShown();"), js.index("try{localStorage.setItem(KT,p);}catch(e){}"), "…ahead of the persist, the promotion and the re-tell")
        self.assertLess(js.index("try{if(mobileOn()){promote(p);paintLoading();}}catch(e){}"), js.index("try{window.__rompPanesTell&&window.__rompPanesTell();}catch(e){}}\nwindow.__rompMobileTab=show;"))
        # the boot: the parking of data-src runs before the boot show, whose line is upstream's text
        self.assertLess(js.index("lf.setAttribute(LAZY,lu);lf.removeAttribute('data-src');"), js.index("var last='chat';try{var s=localStorage.getItem(KT);if(s&&F[s])last=s;}catch(e){}show(last);"))
        self.assertIn("var LAZY='data-lazy-src',LOAD_MS=30000,URLS={},EPI={},TOK={},PEND={},DEAD={};", js)   # + the promoted urls, the failure count per episode (review round 3; the page-life count left with its row in the reviewer's round 7), and the promotion tokens (HIGH 2, review round 1)
        self.assertNotIn("__rompPanePromote", js, "no window export of promote() (review round 3, fresh-3): no production code called it; the three promotion roads (show(), the boot block, the lazyFlip listener) call the local promote() directly, and a re-add would be an unused seam commented as a road")
        self.assertIn("if(en){if(f&&!f.getAttribute('src')&&f.getAttribute('data-src'))f.setAttribute('src',f.getAttribute('data-src'));", km._LANDING_COLLAPSE_JS, "the controller's promotion line is untouched")

    def test_the_seven_lazy_pane_diag_keys_are_withheld_from_the_allowlist(self):
        # the absence pin of the reviewer's round-7 ruling on regression-1 (_DIAG_KEYS_WITHHELD above says why and how it reverts)
        self.assertEqual(len(_DIAG_KEYS_WITHHELD) + len(_DIAG_KEYS_APPROVED), 7, "the seven pairs the three rows posted, each in exactly one table")
        self.assertEqual({(s, k) for s, k, _ in _DIAG_KEYS_APPROVED} & set(_DIAG_KEYS_WITHHELD), set(), "a pair is withheld or approved, never both")
        for surface, key in _DIAG_KEYS_WITHHELD:
            with self.subTest(withheld=(surface, key)):
                self.assertNotIn(key, km.CLIENT_DIAG_KEYS[surface], "%s's %r is withheld: no page-to-kernel key lands without the owner's word" % (surface, key))
        for surface, key, date in _DIAG_KEYS_APPROVED:
            with self.subTest(approved=(surface, key, date)):
                self.assertIn(key, km.CLIENT_DIAG_KEYS[surface], "%s's %r was approved by the owner on %s" % (surface, key, date))
        self.assertIn("via", km.CLIENT_DIAG_KEYS["shell"], "the shell's `via` is main's key (reveal-post, deeplink, tap-pending), not one of the seven")

    def test_shell_reveal_listener_wired(self):
        html = km._landing()
        self.assertIn("app=shell", html)              # shell WS catches kernel reveals (feed/timeline tap)
        self.assertIn("'reveal'", html)               # ...and window reveals (timeline deep-link)

    def test_timeline_iframe_is_the_fourth_pane(self):
        # the timeline is its own rail-toggled pane now (the user 2026-06-24), not a bottom band: the iframe
        # carries id=f-timeline inside #tl-pane, and the old stale-id splitter bug must not regress.
        html = km._landing()
        self.assertIn("id=f-timeline", html)                      # the iframe carries this id
        # data-src, not src (the user 2026-09-10): the band is an optional pane, loaded by the pane controller
        # only where this browser's gear shows it (tests/test_pane_state_broadcast.py OptionalPanes)
        self.assertIn("<div class=pane id=tl-pane><iframe id=f-timeline data-src=/timeline></iframe></div>", html)
        self.assertNotIn("getElementById('t')", km._LANDING_JS)   # the stale id is gone

    def test_mobile_switcher_is_isolated_in_its_own_script(self):
        # the switcher runs in a separate <script> so a splitter throw can't disable the tab bar. Each shell
        # behaviour gets its own isolated <script>: boot-splash + connection-status banner + rail-usage +
        # splitter + focus-ring + fleet-toggle + settings-fullscreen + mobile switcher + viewport-pin +
        # per-pane collapse handles + the build-staleness banner + the remote-drift push banner = 12
        # (the user 2026-06-23; + boot-splash + rail-usage 2026-06-26; + connection-status banner
        # 2026-06-27; + the visible-viewport pin; + the remote-drift banner 2026-07-04; + the head's
        # ios-standalone viewport flip and the push bell 2026-08-07, plans/ios-app.md; + the shared
        # Escape-closes-the-topmost-modal block 2026-08-09; + the release-update banner 2026-08-09).
        html = km._landing()
        # +1 2026-08-28: the theme reader right after <body>; +1 2026-09-06: the notification-tap landing
        # script (_LANDING_REVEAL_JS) — its own script so a throw in the bell's cannot strand a tap;
        # +1 2026-09-08: the reload core (T265, _reload_core) ahead of the build-staleness banner script, which
        # registers as its refused fallback — its own script so a banner throw cannot take the reload with it
        # +1: the bottom bar's API health cell (_LANDING_APIH_JS), after the usage script whose backdrop it shares
        # +1 2026-09-08: the chat split columns (_LANDING_SPLIT_JS), after the pane controller it leans on
        # +1 2026-09-19: the desktop promotion of the Waiting and Files panes (_LANDING_DESKTOP_PANES_JS), its own script so a
        # throw in the mobile script cannot strand a desktop pane (review round 1 of the lazy panes)
        # the count is of live script ELEMENTS with no attributes, the isolated blocks (the author's pass 9, 2026-09-20: a raw count of the
        # tag's spelling over the page had stood for it); the bundles' <script src=...> elements are outside it
        self.assertEqual(len([e for e in served_css.elements(html) if e.kind == "script" and not e.attrs]), 22)

    def test_bottom_bar_is_text_only_and_compact(self):
        html = km._landing()
        self.assertNotIn("class=ic", html)                       # no icon spans — text labels only
        self.assertIn(">Chat</button>", html)                    # plain text label, no icon child
        self.assertIn("#mtabs{display:flex;position:fixed", html)  # glued to the viewport bottom; height still = its text + padding (no fixed height)

    def test_bottom_bar_is_fixed_to_viewport_so_no_dead_space_below_it(self):
        # The recurring bug (the user, through 2026-06-19): the bar was flex-placed at the bottom of a body
        # whose height is only a viewport ESTIMATE (100dvh, then --app-h); when the estimate under-shot the
        # painted area on Android Chrome, a dead slab appeared BELOW the Chat/Feed/Timeline labels. Gluing
        # the bar to the visible viewport bottom (position:fixed;bottom:0) makes "below the bar" impossible
        # by construction, whatever the height math does. .col reserves --mtabs-h so it can't cover content.
        html = km._landing()
        self.assertIn("#mtabs{display:flex;position:fixed;left:0;right:0;bottom:0", html)
        self.assertIn("padding-bottom:var(--mtabs-h", html)
        self.assertNotIn("#mtabs{flex:", html)                   # the bar is NOT itself a flex child anymore
        # the reservation is measured from the live bar, so it tracks the gesture-area inset exactly
        code = served_css.js_code(km._LANDING_MOBILE_JS)   # the code, comments blanked: the barfit comment spells offsetHeight too (the author's pass 6, 2026-09-20)
        self.assertIn("setProperty('--mtabs-h'", code)
        self.assertIn("bar.offsetHeight", code)

    def test_landing_disables_browser_pinch_zoom(self):
        # the top document governs pinch-zoom for the whole visual viewport (incl. the timeline iframe), so
        # it must disable page zoom or iOS page-zooms on a timeline pinch instead of running the gesture.
        # read from the meta's own content attribute, never the page text (_viewport_meta_tokens: a served comment names
        # these tokens too)
        tokens = _viewport_meta_tokens(km._landing())
        self.assertIn("user-scalable=no", tokens)
        self.assertIn("maximum-scale=1", tokens)

    def test_landing_avoids_viewport_fit_cover(self):
        # regression (the user 2026-06-17): viewport-fit=cover made Android Chrome report a non-zero
        # env(safe-area-inset-bottom) even though the viewport already sits above the nav bar, so #mtabs's
        # safe-area padding-bottom rendered as a dead slab below the Chat/Feed/Timeline labels (and cover
        # clipped the top under the status bar). The default viewport auto-insets clear of system UI and
        # zeroes env() on Chrome, so the STATIC meta must NOT request cover.
        #
        # Narrowed, not repealed, for the installable app (plans/ios-app.md; the user 2026-08-07): an iOS
        # home-screen app has no browser chrome keeping #mtabs off the home indicator, and iOS only
        # populates env() under cover — so the head script flips cover on AT RUNTIME, gated on
        # navigator.standalone, which is iOS-only and standalone-only. No Android browser can ever take
        # that branch, so the 2026-06-17 regression cannot recur through it.
        html = km._landing()
        # the static meta's content, read from the element (the author's pass 9, 2026-09-20: it had been a substring of the page): no cover
        self.assertEqual(served_css.meta_content(html, "viewport"),
                         "width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no,interactive-widget=resizes-content")
        # exactly the runtime flip, in the code of one live script (comments removed), behind the iOS-standalone gate, and the token
        # in no markup (the author's pass 9: a count and an ordering over the raw page had stood for these)
        scripts = served_css.scripts(html)
        flips = [js for js in scripts if "viewport-fit=cover" in js]
        self.assertEqual(sum(js.count("viewport-fit=cover") for js in scripts), 1)
        self.assertEqual(len(flips), 1)
        self.assertLess(flips[0].index("if(navigator.standalone)"), flips[0].index("viewport-fit=cover"))
        self.assertNotIn("viewport-fit=cover", served_css._blank(html, [(s, e) for s, e, _ in served_css.element_spans(html)]), "the token is in no markup")
        self.assertTrue(any("100dvh" in v for r in served_css.rules(html) for _, v in r.decls), "still address-bar-aware (a parsed declaration, not page text)")
        self.assertIn("user-scalable=no", _viewport_meta_tokens(html))  # pinch-zoom governance preserved alongside the change, read from the meta

    def test_keyboard_shrinks_content_and_never_strands_a_scroll(self):
        """The composer tap used to scroll the whole shell up behind the soft keyboard (the user
        2026-09-02): the viewport's default mode is resizes-visual — the keyboard PANS the visual
        viewport while innerHeight stands still, the UA slides the page up to reveal the input, and
        fit() re-lays the shrunken --app-h top-anchored into a window whose visible band starts a
        keyboard-height down; the composer sat off-screen until dragged back. Two halves, both
        pinned: interactive-widget=resizes-content makes engines that honor it (Android Chrome)
        SHRINK the layout viewport instead of panning, and fit() undoes the stray page offset iOS
        still forces (a UA input-reveal scroll bypasses overflow:hidden)."""
        self.assertIn("interactive-widget=resizes-content", _viewport_meta_tokens(km._landing()))   # the meta's token, not a comment's
        self.assertIn("if(window.scrollY||document.documentElement.scrollTop)window.scrollTo(0,0);",
                      km._LANDING_MOBILE_JS)

    def test_bottom_bar_has_no_safe_area_padding(self):
        # The user 2026-06-19 (Firefox/Android): the bar showed a dead slab below the labels in PORTRAIT
        # only. The Android nav bar is at the BOTTOM in portrait (env(safe-area-inset-bottom) > 0) and on
        # the SIDE in landscape (inset = 0), and Firefox — unlike Chrome — does NOT zero that inset without
        # viewport-fit=cover, so #mtabs's padding-bottom:env(safe-area-inset-bottom) rendered as a
        # portrait-only slab. Without cover the viewport already clears the nav bar, so the padding is
        # redundant on the BROWSER bar, which stays inset-free.
        #
        # The one sanctioned exception (plans/ios-app.md; the user 2026-08-07): installed on an iOS home
        # screen the browser chrome is gone and the bar must clear the home indicator, so a single rule
        # keyed on html.ios-standalone — a class set only under navigator.standalone, which no Android
        # browser exposes — reclaims the inset there and nowhere else.
        html = km._landing()
        # exactly the standalone rule below, as a parsed declaration (the author's pass 9, 2026-09-20: a raw count over the page had stood for it)
        insets = [(r.selector, p) for r in served_css.rules(html) for p, v in r.decls if "env(safe-area-inset" in v]
        self.assertEqual(insets, [("html.ios-standalone #mtabs", "padding-bottom")])
        self.assertIn("html.ios-standalone #mtabs{padding-bottom:env(safe-area-inset-bottom,0px)}", html)
        self.assertIn("#mtabs{display:flex;position:fixed;left:0;right:0;bottom:0", html)

    def test_the_shell_forwards_a_quote_seed_from_a_composerless_pane_into_the_chat(self):
        # A passage selected in the file viewer hosted by the FEED pane (the file browser's document)
        # has no composer in its own document; file-view.ts posts the editorSelection message up to the
        # shell, which forwards it whole into the chat iframe, whose existing handler seeds the labeled
        # quote chip for m.sid. The arm sits in the same listener as the browseFiles relay, and the chat
        # iframe carries the id it keys on.
        js = km._LANDING_SETTINGS_JS
        self.assertIn("if(m.type==='editorSelection'&&typeof m.text==='string'){var fc=document.getElementById('f-chat');", js)
        self.assertIn("try{fc&&fc.contentWindow&&fc.contentWindow.postMessage(m,'*');}catch(e){}}", js)
        self.assertIn("<iframe id=f-chat class=m-on src=/chat>", km._landing())


class TimelineTouchSurface(unittest.TestCase):
    def test_timeline_fits_svg_and_drops_overflow_scroller_on_touch(self):
        # regression: the view forces a >=640px SVG; on a ~390px phone the default overflow-x:auto turned
        # that into a native horizontal scroller that beat the one-finger pan gesture. On a touch device the
        # SVG must fit the screen (width:100%) with no overflow scroller, so the gesture owns horizontal pan.
        # The wrapper styles moved to ui/webview/timeline-pane.css (shared with the VS Code view); the
        # kernel reads that file live, so pin the served page rather than a constant. The declarations are read from
        # the PARSED rule (the author's pass 4, 2026-09-20): two served script comments spell touch-action:pan-y, so a page-text pin
        # was satisfied with the declaration gone. The runtime authority for the gesture is the inline style the view
        # sets unconditionally when it builds the wrap (ui/romp-timeline-view.js, `this.wrap.style.touchAction = 'pan-y'`
        # in the constructor that creates .romp-tl-wrap); this rule is the sheet's copy for a wrap before or without it.
        page = km._timeline_page()
        coarse = [r for r in served_css.rules(page) if r.at == ("@media (pointer:coarse)",)]
        self.assertTrue(coarse, "the coarse-pointer media block is in the served timeline page")
        wrap = [dict(r.decls) for r in coarse if r.selector == ".romp-tl-wrap"]
        self.assertEqual(wrap, [{"overflow-x": "hidden", "touch-action": "pan-y"}], "the wrap's coarse-pointer declarations")
        self.assertEqual([dict(r.decls).get("width") for r in coarse if r.selector == ".romp-tl-wrap svg"], ["100%"], "the SVG fits the screen")


class ChatSessionPicker(unittest.TestCase):
    def test_chat_page_collapses_tabs_into_a_header_on_mobile(self):
        chat = km._chat_page()
        self.assertIn("#mhdr", chat)                        # the compact header replaces the tab strip
        self.assertIn("#tabbar #tabs{display:none}", chat)  # the wrapping multi-row tab strip is hidden
        self.assertIn("id='mcur'", km._CHAT_MOBILE_JS)      # current-session button that opens the list
        self.assertIn("id='mlist'", km._CHAT_MOBILE_JS)     # the dropdown list of sessions

    def test_desktop_hides_the_mobile_header_and_list(self):
        # regression: #mlist (a #tabbar sibling, not inside #mhdr) had no desktop rule, so on desktop it
        # rendered the session rows as plain text in the tab bar. Both must be hidden off-mobile.
        self.assertIn("#mhdr,#mlist{display:none}", km._CHAT_MOBILE_CSS)

    def test_picker_is_custom_colored_not_native_select(self):
        # a native <select> can't render the per-session identity colors, so the picker is our own element
        js, css = km._CHAT_MOBILE_JS, km._CHAT_MOBILE_CSS
        self.assertNotIn("createElement('select')", js)   # not native
        self.assertIn("--chip-bg", js)                    # reads each session's identity color
        self.assertIn("#mcur.colored", css)               # the current button wears that color

    def test_a_remote_sessions_host_prefix_stays_quiet_metadata(self):
        # the user 2026-07-30, on a phone: "host:name" came through the picker painted whole in the
        # session's identity colour at full weight, where desktop renders the "host:" as quiet metadata
        # (host-prefix.ts: dim, italic, never bold, a step smaller). The cause was textContent flattening
        # the desktop label — which already carries a <span class="host-prefix"> — so the fix CLONES the
        # label's child nodes instead of re-deriving the split, keeping ONE definition of the treatment.
        js = km._CHAT_MOBILE_JS
        self.assertIn("function fillName(elm,s){", js)
        self.assertIn("s.lab.cloneNode(true).childNodes", js, "the nodes are cloned, not flattened")
        # ...and the clone's childNodes are SLICED before the walk: appending straight off that live
        # NodeList removes each node as it goes and skips every second one, which dropped the session
        # name and left a row reading just "host:" (caught in a browser, not by a source pin)
        self.assertIn("[].slice.call(s.lab.cloneNode(true).childNodes).forEach(", js)
        self.assertIn("lab:lab,", js, "read() carries the label element through")
        self.assertIn("fillName(nm,act);", js, "the current-session button too, not just the rows")
        self.assertNotIn("nm.textContent=act.name", js)
        self.assertNotIn("lbl.textContent=s.name", js)
        # the treatment itself is NOT re-declared here: the cloned span brings its class, and the chat
        # page loads the sheet that styles it (a second spelling would eventually disagree with desktop)
        self.assertNotIn("host-prefix", km._CHAT_MOBILE_CSS)
        self.assertIn("<link href=/dist/styles.css", km._chat_page())

    def test_picker_rows_match_desktop_colored_name_plus_status_dot(self):
        # the user 2026-07-22: on mobile the picker painted a per-session identity DOT (grey #666 when the
        # session had no color, and confusingly the identity color when it did) — desktop has no such dot.
        # Match desktop: the identity color tints the NAME text (inline, like the Fleet list / colored tab
        # label), and the dot MIRRORS the tab's own status dot — gold when working, GREEN when awaitingBg
        # (idle-waiting-on-bg-work, the .tab-dot.await), none otherwise.
        js, css = km._CHAT_MOBILE_JS, km._CHAT_MOBILE_CSS
        self.assertIn("fillName(lbl,s);lbl.style.color=s.bg||'';", js)   # identity color on the NAME (in-place form also CLEARS a dropped color)
        self.assertIn("if(!wd){wd=document.createElement('span');wd.className='workdot';", js)   # in-place form: one dot node, created once, classes toggled (2026-08-19)  # gold dot when working
        # awaitingBg is read off the desktop tab's own green dot (no tab-working class on an awaiting tab)
        self.assertIn("awaitbg:!!t.querySelector('.tab-dot.await')", js)
        # the ASK RING (2026-09-13; a widget with a switch since 2026-09-14): the desktop tab's ring-waiting-on-you class
        # (something of the session's is waiting on you) is scraped beside the dots, and the picker paints it on the row (a
        # yellow bar at the left edge) and the current chip (its border goes dashed yellow), off the same status token the
        # desktop ring wears — so the phone's list says which sessions need you without a tap through each, and a ring
        # switched off in the settings (no class on the tab) leaves the phone plain too
        self.assertIn("ask:t.classList.contains('ring-waiting-on-you'),", js)
        self.assertNotIn("'tab-ask'", js)
        self.assertIn("row.classList.toggle('ask',!!s.ask);", js)
        self.assertIn("cur.classList.toggle('ask',!!(act&&act.ask));", js)
        self.assertIn("wd.classList.toggle('await',!s.working&&!!s.awaitbg);", js)  # green dot when awaiting (in-place toggle form, 2026-08-19)
        self.assertNotIn(".mrow .dot{", css)              # the old identity/grey dot is gone
        self.assertNotIn("dot.style.background=s.bg", js)  # ...and nothing paints identity onto a dot
        # the dots are the SAME status colors desktop uses (styles.css --st-working-bg gold, --st-awaitbg-bg green)
        self.assertIn(".mrow .workdot{flex:0 0 auto;width:7px;height:7px;border-radius:50%;background:var(--st-working-bg,#e0b020)}", css)
        self.assertIn(".mrow .workdot.await{background:var(--st-awaitbg-bg,#54B204)}", css)
        self.assertIn(".mrow.ask{border-left:3px solid var(--st-ask-bg,#f5d33f);padding-left:9px}", css)   # the ask ring's mark on a row (2026-09-13)
        self.assertIn("#mcur.ask{border-color:var(--st-ask-bg,#f5d33f);border-style:dashed}", css)
        self.assertLess(css.index("#mcur.colored{"), css.index("#mcur.ask{"), "the ring's border wins over the identity colour: declared after")
        self.assertNotIn("'• ')+s.name", js)              # the '• ' text-bullet prefix on rows is gone
        # the current-session header uses the same gold/green status dot, not the text bullet either
        self.assertIn("#mcur .wd{flex:0 0 auto;width:7px;height:7px;border-radius:50%;background:var(--st-working-bg,#e0b020)}", css)
        self.assertIn("#mcur .wd.await{background:var(--st-awaitbg-bg,#54B204)}", css)
        self.assertIn("wd.style.display=(act&&(act.working||act.awaitbg))?'':'none'", js)
        self.assertIn("wd.classList.toggle('await',!!(act&&act.awaitbg&&!act.working))", js)
        self.assertNotIn("(act.working?'• ':'')", js)

    def test_current_session_title_is_bold_color_on_the_grey_chip(self):
        # the user 2026-07-22: the mobile current-session title reads as the identity color in BOLD on the
        # SAME grey chip as the +/madd button, with a hairline color border, not the color as a fill.
        # (The chip grey rides --btn-bg since 2026-09-02 — dark value byte-identical to the old #2a2a2a
        # literal, and the light theme re-skins it; see test_kernel_mobile_picker's token test.)
        css = km._CHAT_MOBILE_CSS
        self.assertIn("#mcur.colored{background:var(--btn-bg,#2a2a2a);color:var(--cbg);border-color:var(--cbg)}", css)
        self.assertIn("#madd{flex:0 0 auto", css)                    # ...and the + button is that same grey
        self.assertIn("background:var(--btn-bg,#2a2a2a);color:#bbbbbb", css)   # (the shared chip grey)
        self.assertIn("white-space:nowrap;font-weight:700}", css)   # the .nm name span is bold

    def test_no_pane_focus_ring_on_mobile(self):
        # the user 2026-07-22: only one pane shows at a time on mobile, so the "which pane is focused" ring
        # is meaningless — it just draws a blue border around the whole view. It's suppressed in the mobile
        # media query while the desktop grid (many panes at once) keeps it.
        html = km._landing()
        self.assertIn(".pane.pane-focused::after{display:none}", html)   # killed on mobile
        # the desktop ring itself still exists (outside the media query)
        self.assertIn(".pane.pane-focused::after{content:'';", html)

    def test_picker_is_gated_on_touch_not_pane_width(self):
        # regression: the chat iframe is one of three desktop panes, so it's ALWAYS narrow. A bare
        # max-width breakpoint matched that narrow pane and swapped the mobile picker in on desktop,
        # replacing the real tab strip. The picker must trigger only on a touch device (pointer:coarse).
        css = km._CHAT_MOBILE_CSS
        self.assertIn("@media (pointer:coarse) and (max-width:1024px){", css)
        self.assertNotIn("(max-width:820px),", css)   # the width-only OR-clause that leaked onto desktop is gone

    def test_picker_routes_a_pick_and_wires_new_session(self):
        js, css = km._CHAT_MOBILE_JS, km._CHAT_MOBILE_CSS
        self.assertIn(".tab[data-id", js)             # a row tap clicks the real tab (render.js focuses it)
        self.assertIn("MutationObserver", js)         # re-syncs as tabs change
        self.assertIn(".tab-add", js)                 # + → open / new session
        # the dead "Toggle summary" button (#mcoll → .tab-collapse) is GONE (the user 2026-07-22): the
        # ledger/summary strip it toggled was retired, so .tab-collapse never existed in the DOM produced
        # by render.ts and the button did nothing. Nothing left to rewire it to, so it was removed.
        self.assertNotIn("mcoll", js)
        self.assertNotIn(".tab-collapse", js)
        self.assertNotIn("#mcoll", css)

    def test_picker_rows_have_an_end_session_control(self):
        # the user 2026-07-22: the mobile picker had no way to end a session (desktop has the tab x). Add a
        # per-row x that clicks the hidden desktop tab's own .tab-close, reusing its confirm dialog
        # (Close tab / End session / Cancel) + the endSession/closeTab plumbing — no new backend.
        js, css = km._CHAT_MOBILE_JS, km._CHAT_MOBILE_CSS
        self.assertIn("x.className='mclose'", js)
        self.assertIn("x.title='End session'", js)
        # it triggers the real tab's close x, and stops propagation so it doesn't also switch sessions
        self.assertIn("var rtc=realTab(id);var c=rtc&&rtc.querySelector('.tab-close');if(c)c.click();", js)   # delegated form (2026-08-19 click-safe rewrite)
        self.assertIn("e.stopPropagation();hide();", js)
        self.assertIn(".mrow .mclose{", css)


class RevealRouting(unittest.TestCase):
    def test_a_reveal_focuses_the_askers_chat_and_nudges_its_shell(self):
        # the chat focus + the shell's switch-to-Chat travel as a pair, both addressed to the asker's wid
        sent = []
        orig = km._send_to_view
        km._send_to_view = lambda app, msg, wid: sent.append((app, wid, msg))
        try:
            km._reveal_chat_for({"app": "feed", "wid": "win-A"}, {"type": "focus", "id": "s1"})
        finally:
            km._send_to_view = orig
        self.assertEqual([(a, w) for a, w, _ in sent], [("chat", "win-A"), ("shell", "win-A")],
                         "chat focus AND mobile-shell nudge, the asker's window only")
        chat_msg = next(m for a, _, m in sent if a == "chat")
        shell_msg = next(m for a, _, m in sent if a == "shell")
        self.assertEqual(chat_msg["id"], "s1")        # the original focus payload is preserved verbatim
        self.assertEqual(shell_msg, {"type": "reveal", "pane": "chat"})


# A node stand-in for the phone: the shell's mobile script runs against a stub window whose visual
# viewport the driver shrinks and grows by hand, so the fit's INPUTS are exact and its OUTPUT (the
# --app-h / --mtabs-h it publishes) is read back. Same shape as test_kernel_webpush's reveal harness.
_FIT_HARNESS = r"""
'use strict';
const PROPS = {}, SETS = [], RAF = [], WIN = {}, DOC = {}, VV = {}, CHAT = {}, LOADS = [];
const on = (book) => (k, f) => { (book[k] = book[k] || []).push(f); };
global.window = global;
global.innerHeight = 844; global.innerWidth = 390; global.scrollY = 0;
global.scrollTo = () => {};
global.matchMedia = () => ({ matches: true });                 // a coarse pointer: the phone
global.requestAnimationFrame = (f) => { RAF.push(f); return RAF.length; };
global.setInterval = () => 0;   // D3 (2026-09-18): the shell socket's watchdog tick; a no-op here so node exits (ShellLinkProbe drives its own)
global.addEventListener = on(WIN);
global.visualViewport = { height: 844, scale: 1, offsetTop: 0, addEventListener: on(VV) };   // offsetTop: the pan (D1, 2026-09-19)
const pane = (id) => ({ id, classList: { toggle() {} }, contentDocument: {},
  contentWindow: { addEventListener: on(id === 'f-chat' ? CHAT : {}) },
  addEventListener: (k) => { if (k === 'load') LOADS.push(id); } });
const PANES = { 'f-chat': pane('f-chat'), 'f-fleet': pane('f-fleet'), 'f-feed': pane('f-feed'), 'f-timeline': pane('f-timeline') };
// the LAYOUT viewport's height (the author's pass 7, 2026-09-20): document.documentElement.clientHeight, what the pinch road's clamp and (the author's pass 8)
// the fine-pointer road read. It is innerHeight unless a scenario parts the two (LAYOUT.h), the engine model kernel.py's fit()
// comment states with its evidence status (the one home): the stub models it, and a model is not a measurement
const LAYOUT = { h: null };
const layoutH = () => (LAYOUT.h === null ? global.innerHeight : LAYOUT.h);
// the bar's BOX (D1, 2026-09-19): a fixed bottom:0 bar sits at the layout viewport's bottom, its height above layoutH(), unless a
// scenario leaves it elsewhere (BAR.top: an engine that shrank innerHeight but kept the bar at the old bottom)
const BAR = { offsetHeight: 44, querySelectorAll: () => [], top: null,
  getBoundingClientRect() { const top = BAR.top === null ? layoutH() - BAR.offsetHeight : BAR.top; return { top, bottom: top + BAR.offsetHeight, left: 0, right: 390 }; } };
global.document = {
  visibilityState: 'visible',
  addEventListener: on(DOC),
  documentElement: { scrollTop: 0, get clientHeight() { return layoutH(); },   // the layout viewport (the author's pass 7, 2026-09-20)
    style: { setProperty: (k, v) => { PROPS[k] = v; SETS.push(k); }, getPropertyValue: (k) => PROPS[k] || '' } },   // the published band, read back by barfit (the author's pass 4, 2026-09-20)
  body: { setAttribute() {} },
  getElementById: (id) => (id === 'mtabs' ? BAR : (PANES[id] || null)),
};
global.localStorage = { getItem: () => null, setItem() {} };
"""
_FIT_DRIVER = r"""
const fire = (book, k) => (book[k] || []).forEach((f) => f({}));
const flush = () => { RAF.splice(0).forEach((f) => f(0)); };            // one frame: run what this frame queued
const appH = () => PROPS['--app-h'], barH = () => PROPS['--mtabs-h'];
const fits = () => SETS.filter((k) => k === '--app-h').length;
const out = {};
out.bound = { win: Object.keys(WIN).sort(), doc: Object.keys(DOC).sort(), vv: Object.keys(VV).sort(),
  chat: Object.keys(CHAT).sort(), loads: LOADS.slice().sort() };
out.boot = { appH: appH(), barH: barH(), rafPending: RAF.length };
// the keyboard slides up: iOS shrinks the visual viewport while innerHeight stands still
visualViewport.height = 460; fire(VV, 'resize'); flush();
out.kbUp = { appH: appH(), barH: barH() };
// the keyboard goes away and NO viewport event arrives: the composer's blur is the only word
visualViewport.height = 844; fire(CHAT, 'focusout');
out.blurBeforeFrame = appH();
flush();
out.kbDown = { appH: appH(), barH: barH() };
// resume: backgrounded with the keyboard up; iOS dropped it while the page was frozen, no event delivered
visualViewport.height = 460; fire(VV, 'resize'); flush();
document.visibilityState = 'hidden'; fire(DOC, 'visibilitychange');
const beforeHidden = fits(); flush(); out.hiddenFits = fits() - beforeHidden;
visualViewport.height = 844; document.visibilityState = 'visible'; fire(DOC, 'visibilitychange'); flush();
out.resume = { appH: appH(), barH: barH() };
// resume where iOS reports the FINAL geometry a beat late: the fit at visible reads the stale height,
// and the visual-viewport resize that follows is what corrects it
visualViewport.height = 460; fire(VV, 'resize'); flush();
document.visibilityState = 'hidden'; fire(DOC, 'visibilitychange'); flush();
document.visibilityState = 'visible'; fire(DOC, 'visibilitychange'); flush();
out.resumeStale = appH();
visualViewport.height = 844; fire(VV, 'resize'); flush();
out.resumeSettled = appH();
// a burst of events fits ONCE, on the next frame
const before = fits();
fire(VV, 'resize'); fire(VV, 'scroll'); fire(WIN, 'resize'); fire(WIN, 'focus'); fire(WIN, 'pageshow'); fire(DOC, 'focusout');
out.burst = { beforeFlush: fits() - before, pendingRafs: RAF.length };
flush();
out.burst.afterFlush = fits() - before;
// every bound event refits on its own, reading the geometry fresh each time
const each = {};
for (const [book, k, tag] of [[WIN, 'focus', ''], [WIN, 'pageshow', ''], [WIN, 'orientationchange', ''], [WIN, 'resize', ''],
                              [VV, 'scroll', '@vv'], [VV, 'resize', '@vv'], [DOC, 'focusout', '@doc']]) {
  visualViewport.height = 700; fire(book, k); flush(); const a = appH();
  visualViewport.height = 844; fire(book, k); flush(); each[k + tag] = [a, appH()];
}
out.each = each;
// a page offset the UA forced (iOS's input reveal) is undone on the same frame
global.scrollY = 120; let scrolled = null; global.scrollTo = (x, y) => { scrolled = [x, y]; global.scrollY = 0; };
fire(VV, 'scroll'); flush(); out.scrollReset = scrolled;
// D1 (2026-09-19), the PAN: iOS moves the visual viewport down the layout viewport to reveal the focused composer while
// innerHeight stands still; vv.height shrinks, offsetTop grows, and the visual viewport's scroll event is where the pan lands
const appTop = () => PROPS['--app-top'];
out.restTop = appTop();
visualViewport.height = 460; visualViewport.offsetTop = 83; fire(VV, 'resize'); fire(VV, 'scroll'); flush();
out.pan = { appTop: appTop(), appH: appH(), barH: barH() };
// the author's pass 8 (2026-09-20): the measured road's rounding (panPx, the one reading both writing roads share): 0.4 rounds to no pixel and
// 0.5 up to one; the 0px road's flips below drive the same two values on its side
visualViewport.offsetTop = 0.4; fire(VV, 'scroll'); flush(); out.subPixelMeasured = appTop();
visualViewport.offsetTop = 0.5; fire(VV, 'scroll'); flush(); out.halfPixelMeasured = appTop();
visualViewport.offsetTop = 83; fire(VV, 'scroll'); flush();
// the author's pass 8 (2026-09-20): the pinch CUT, derived from the measured road's rounding: a zoom at scale s pans the visual viewport by at
// most L(1 - 1/s) with no keyboard behind it, L the LAYOUT viewport the visual viewport's top ranges over, and the measured road
// stores round(offsetTop), so the cut is the scale at which that largest zoom pan reaches the half pixel that rounds up,
// s = L/(L - 0.5): 1.00059 at L 844. The author's pass 9 (2026-09-20): these cells had taken the cut at the coarse road's h of 460, the band's
// height with the keyboard up, which is not the height a zoom pans over; both roads take it at L now (kernel.py, beside pinched).
// Below the cut (1.0005: the largest zoom pan 0.42 px, no pixel) the measured road stores the pan it reads, 90 from 90.4; at or
// above it (1.0007: 0.59 px, one pixel) the report is a pinch and the road publishes the pan LESS the zoom's pixel, 97 from 97.6,
// not the hold (90) and not the raw reading (98). The author's pass 8 had held 90 there (driven at 1.0012 with the same reading); the
// maintainer's round 5 ruling re-ruled it: refusing the pan cost the whole keyboard pan where the zoom's share was a pixel
visualViewport.scale = 1.0005; visualViewport.height = 459.77; visualViewport.offsetTop = 90.4; fire(VV, 'resize'); fire(VV, 'scroll'); flush();
out.cutBelow = { appTop: appTop(), appH: appH(), zoomShare: 844 * (1 - 1 / 1.0005) };
visualViewport.scale = 1.0007; visualViewport.height = 459.68; visualViewport.offsetTop = 97.6; fire(VV, 'resize'); fire(VV, 'scroll'); flush();
out.cutAbove = { appTop: appTop(), appH: appH(), zoomShare: 844 * (1 - 1 / 1.0007) };
visualViewport.scale = 1; visualViewport.height = 460; visualViewport.offsetTop = 83; fire(VV, 'resize'); fire(VV, 'scroll'); flush();
// the author's pass 9 (2026-09-20): the state the author's pass 8's cut REGRESSED (the maintainer's round 5 ruling): the keyboard raised under a LIGHT zoom,
// a scale between the cut and the 1.01 the literal had allowed, with NO hold standing. From rest at scale 1 the measured road
// stores 0, so the hold is 0; the keyboard then comes up at scale 1.003 (h 460: the visual viewport 458.62 tall, panned 83.7).
// The author's pass 8's road read the report as a pinch and fell to the hold, 0px, the band under the composer this change exists to close.
// The measured road now publishes the pan a pure zoom CANNOT explain: the measured pixels (84) less the zoom's share at that
// scale, 844(1 - 1/1.003) = 2.52 px, 3 in pixels: 81px, within the share plus a pixel below the keyboard's own pan and a pixel above
// it, and never 0
visualViewport.scale = 1; visualViewport.height = 844; visualViewport.offsetTop = 0; fire(VV, 'resize'); fire(VV, 'scroll'); flush();
out.restBeforeLightZoom = appTop();
visualViewport.scale = 1.003; visualViewport.height = 458.62; visualViewport.offsetTop = 83.7; fire(VV, 'resize'); fire(VV, 'scroll'); flush();
out.kbUpLightZoomNoHold = { appTop: appTop(), appH: appH(), zoomShare: 844 * (1 - 1 / 1.003) };
// the two states that must not regress with it. A REAL pinch with no keyboard publishes no band, driven at the deepest pan a pure
// zoom of the layout viewport can reach (scale 2: the visual viewport 422 tall at offsetTop 422, exactly the zoom's share, so the
// bound is tight and nothing is left over for a keyboard); the hold stands at 0
visualViewport.scale = 1; visualViewport.height = 844; visualViewport.offsetTop = 0; fire(VV, 'resize'); fire(VV, 'scroll'); flush();
visualViewport.scale = 2; visualViewport.height = 422; visualViewport.offsetTop = 422; fire(VV, 'resize'); fire(VV, 'scroll'); flush();
out.zoomDeepestNoHold = { appTop: appTop(), appH: appH() };
// a keyboard raised UNDER a real pinch with no hold: its pan (83) is inside the zoom's share (422), so the road cannot tell it from a
// zoom's and publishes the hold, 0 (the outcome before the author's pass 9 too, kept: the band shows until the zoom ends or the keyboard is
// raised at scale 1, where the measured road stores its pan); a keyboard raised BEFORE the pinch is the pinchPanned pin below
visualViewport.scale = 1; visualViewport.height = 844; visualViewport.offsetTop = 0; fire(VV, 'resize'); fire(VV, 'scroll'); flush();
visualViewport.scale = 2; visualViewport.height = 230; visualViewport.offsetTop = 83; fire(VV, 'resize'); fire(VV, 'scroll'); flush();
out.kbUnderZoomNoHold = { appTop: appTop(), appH: appH() };
// the visual viewport dragged LOWER under that pinch than a pure zoom could put it (offsetTop 500 against a share of 422; the band
// 500..730 lies inside the layout viewport): the excess, 78, is a keyboard's, published and stored; dragged back to 83 the hold road
// publishes that 78 (the excess became the hold, an estimate of the keyboard's pan within the zoom's share; disclosed)
visualViewport.offsetTop = 500; fire(VV, 'scroll'); flush();
out.kbUnderZoomDragged = { appTop: appTop(), appH: appH() };
visualViewport.offsetTop = 83; fire(VV, 'scroll'); flush();
out.kbUnderZoomDraggedBack = { appTop: appTop(), appH: appH() };
// the fixer pass of the author's pass 9: the bound's SHAPE and the derivation's DOMAIN, by execution. (a) The published value is an
// integer from two roundings (panPx and zoomPx), so it lies within the share plus a pixel BELOW the keyboard's own pan and a pixel
// ABOVE it, never one-sided: a reading of 86.5 at scale 1.002959 (share 2.49 px, 2 in pixels) publishes 85 (87 less 2), a pixel above
// a keyboard pan of 84.01 if the zoom panned its whole share; a reading of 84 at scale 1.02 (share 16.55, 17 in pixels) publishes 67,
// 17 below a keyboard pan of 84 if the zoom panned nothing, more than the share. Each cell starts from rest (the hold 0)
visualViewport.scale = 1; visualViewport.height = 844; visualViewport.offsetTop = 0; fire(VV, 'resize'); fire(VV, 'scroll'); flush();
visualViewport.scale = 1.002959; visualViewport.height = 458.64; visualViewport.offsetTop = 86.5; fire(VV, 'resize'); fire(VV, 'scroll'); flush();
out.roundedUp = { appTop: appTop(), appH: appH(), offsetTop: 86.5, zoomShare: 844 * (1 - 1 / 1.002959) };
visualViewport.scale = 1; visualViewport.height = 844; visualViewport.offsetTop = 0; fire(VV, 'resize'); fire(VV, 'scroll'); flush();
visualViewport.scale = 1.02; visualViewport.height = 450.98; visualViewport.offsetTop = 84; fire(VV, 'resize'); fire(VV, 'scroll'); flush();
out.roundedDown = { appTop: appTop(), appH: appH(), offsetTop: 84, zoomShare: 844 * (1 - 1 / 1.02) };
// (b) a scale BELOW 1 (a zoom-out, or a pinch-out bounce; whether iOS reports one is unverified): the visual viewport is the taller
// and its top sits at or above the layout viewport's, so a pure zoom-out's share is 0, never the negative L(1 - 1/s). With no
// keyboard nothing is published and the hold stays 0 (the head kernel published 94 at scale 0.9 and stored it); the centred
// report, a negative offsetTop, the same; a keyboard's pan under it is published whole (the share is 0 below scale 1)
visualViewport.scale = 1; visualViewport.height = 844; visualViewport.offsetTop = 0; fire(VV, 'resize'); fire(VV, 'scroll'); flush();
visualViewport.scale = 0.9; visualViewport.height = 937.78; visualViewport.offsetTop = 0; fire(VV, 'resize'); fire(VV, 'scroll'); flush();
out.zoomOutNoKb = { appTop: appTop(), appH: appH() };
visualViewport.offsetTop = -46.89; fire(VV, 'scroll'); flush();
out.zoomOutCentred = { appTop: appTop(), appH: appH() };
visualViewport.scale = 2; visualViewport.height = 230; visualViewport.offsetTop = 83; fire(VV, 'resize'); fire(VV, 'scroll'); flush();
out.zoomOutHold = appTop();   // the hold road under a real pinch publishes the hold: what the zoom-out cells left in it
visualViewport.scale = 1; visualViewport.height = 844; visualViewport.offsetTop = 0; fire(VV, 'resize'); fire(VV, 'scroll'); flush();
visualViewport.scale = 0.9; visualViewport.height = 511.11; visualViewport.offsetTop = 84; fire(VV, 'resize'); fire(VV, 'scroll'); flush();
out.zoomOutKb = { appTop: appTop(), appH: appH() };
// (c) the premise test to the pixel: a visual viewport FLUSH at the layout viewport's bottom with the keyboard up under a real pinch,
// its two values as an engine hands them over (float32, Math.fround), sums to L plus an ulp in doubles; an exact offsetTop + height
// <= L read it as outside the layout viewport and sent it to the hold road (0px with no hold), where the measured road publishes the
// keyboard's pan: 512 less the share's 235, 277
visualViewport.scale = 1; visualViewport.height = 844; visualViewport.offsetTop = 0; fire(VV, 'resize'); fire(VV, 'scroll'); flush();
{ const s = 1.38562, h = Math.fround(460 / s), ot = Math.fround(844 - 460 / s);
  visualViewport.scale = s; visualViewport.height = h; visualViewport.offsetTop = ot; fire(VV, 'resize'); fire(VV, 'scroll'); flush();
  out.flushBottomFloat32 = { appTop: appTop(), appH: appH(), offsetTop: ot, height: h, sumMinusL: ot + h - 844, zoomShare: 844 * (1 - 1 / s) }; }
visualViewport.scale = 1; visualViewport.height = 844; visualViewport.offsetTop = 0; fire(VV, 'resize'); fire(VV, 'scroll'); flush();
visualViewport.height = 460; visualViewport.offsetTop = 83; fire(VV, 'resize'); fire(VV, 'scroll'); flush();
// the author's pass 4 (2026-09-20): a height report the run REFUSES (h 0) publishes no pan either. The pan belongs to the height it was
// measured with, so a report of height 0 with offsetTop 300 leaves --app-top and --app-h where the last valid run put them
// (83 and 460); publishing the pan alone had moved the fixed body 300 px down under a height that never followed
visualViewport.height = 0; visualViewport.offsetTop = 300; fire(VV, 'resize'); fire(VV, 'scroll'); flush();
out.refusedHeight = { appTop: appTop(), appH: appH(), barH: barH() };
// the keyboard goes: the visual viewport grows back and the pan with it
visualViewport.height = 844; visualViewport.offsetTop = 0; fire(VV, 'resize'); flush();
out.panDown = { appTop: appTop(), appH: appH(), barH: barH() };
// a keyboard that shrinks the LAYOUT viewport too (an engine honouring interactive-widget=resizes-content): innerHeight,
// vv.height and --app-h agree, so the height difference says no keyboard. The reservation follows the bar's BOX: left at
// the old bottom, below the visible band, the bar is hidden and reserves nothing; riding the shrunken bottom (Android
// Chrome) it shows above the keyboard and keeps its strip, so it never covers the composer
global.innerHeight = 460; visualViewport.height = 460; visualViewport.offsetTop = 0; BAR.top = 800; fire(WIN, 'resize'); flush();
out.shrunkHidden = { appH: appH(), barH: barH(), appTop: appTop() };
BAR.top = null; fire(WIN, 'resize'); flush();   // fixed bottom:0 at innerHeight 460: the box starts at 416, inside the band
out.shrunkVisible = { appH: appH(), barH: barH() };
global.innerHeight = 844; visualViewport.height = 844; fire(WIN, 'resize'); flush();
out.shrunkBack = { appH: appH(), barH: barH() };
// a PINCH (scale above 1) pans and shortens the visual viewport with no keyboard behind it: --app-h holds (upstream's
// scale arithmetic), the pan is not published, and the bar's strip stays reserved though its box is outside the zoomed band
visualViewport.scale = 2; visualViewport.height = 422; visualViewport.offsetTop = 200; fire(VV, 'resize'); fire(VV, 'scroll'); flush();
out.pinch = { appTop: appTop(), appH: appH(), barH: barH() };
visualViewport.scale = 1; visualViewport.height = 844; visualViewport.offsetTop = 0; fire(VV, 'resize'); flush();
out.pinchBack = { appTop: appTop(), appH: appH(), barH: barH() };
// the author's pass 2 (2026-09-19): a pinch taken WHILE the keyboard is up holds the pan (the hold, from a state where --app-top is NOT
// already 0px), and a keyboard dismissed while still zoomed cannot leave that pan behind: --app-h returns to the full height
// on the same run, and a held 83 would place the body at 83..927 in an 844 viewport with the composer row below it, so the
// held value is clamped to the layout viewport's height less h (the author's pass 7, 2026-09-20: read from documentElement.clientHeight, not innerHeight)
visualViewport.scale = 1; visualViewport.height = 460; visualViewport.offsetTop = 83; fire(VV, 'resize'); fire(VV, 'scroll'); flush();
out.panAgain = { appTop: appTop(), appH: appH(), barH: barH() };
visualViewport.scale = 2; visualViewport.height = 230; visualViewport.offsetTop = 83; fire(VV, 'resize'); fire(VV, 'scroll'); flush();
out.pinchPanned = { appTop: appTop(), appH: appH(), barH: barH() };
visualViewport.height = 422; visualViewport.offsetTop = 200; fire(VV, 'resize'); fire(VV, 'scroll'); flush();
out.kbDownZoomed = { appTop: appTop(), appH: appH(), barH: barH() };
// the author's pass 6 (2026-09-20): a height report the run refuses (0) UNDER the zoom: the pinch road publishes no pan either (the guard's
// other half, held by source text alone before), so --app-top and --app-h stay where the run above put them
visualViewport.height = 0; visualViewport.offsetTop = 200; fire(VV, 'resize'); fire(VV, 'scroll'); flush();
out.refusedZoomed = { appTop: appTop(), appH: appH(), barH: barH() };
// the author's pass 4 (2026-09-20): the keyboard raised AGAIN while the zoom still holds. The clamp bounded what the run above published
// and left the hold standing, so this run publishes the pan the keyboard was measured with (83, slack under the clamp:
// 844 - 460). A clamp that wrote its result back had lowered the hold to 0 and laid the shell out at pan 0 under a
// keyboard-sized --app-h, the band reopened for as long as the zoom held
visualViewport.height = 230; visualViewport.offsetTop = 83; fire(VV, 'resize'); fire(VV, 'scroll'); flush();
out.kbUpAgainZoomed = { appTop: appTop(), appH: appH(), barH: barH() };
visualViewport.scale = 1; visualViewport.height = 844; visualViewport.offsetTop = 0; fire(VV, 'resize'); fire(VV, 'scroll'); flush();
out.zoomBack = { appTop: appTop(), appH: appH(), barH: barH() };
// the author's pass 2 (2026-09-19): the geometric reading's EDGE. The bar is hidden when its box STARTS at or below the visible band's
// bottom edge (>=): a bar whose top is exactly offsetTop + vv.height has no pixel inside the band. innerHeight 460 with
// vv.height 460 reads no keyboard by the height difference, so the bar's box alone decides
global.innerHeight = 460; visualViewport.height = 460; visualViewport.offsetTop = 0; BAR.top = 460; fire(WIN, 'resize'); flush();
out.barAtTheEdge = { appH: appH(), barH: barH() };
BAR.top = 459; fire(WIN, 'resize'); flush();   // one pixel inside the band: visible, reserved
out.barOnePxIn = { appH: appH(), barH: barH() };
BAR.top = null; global.innerHeight = 844; visualViewport.height = 844; fire(WIN, 'resize'); flush();
out.barEdgeBack = { appH: appH(), barH: barH() };
// the author's pass 3 (2026-09-19): the bar INSIDE the band under a pan. The keyboard up (vv.height 460 in an 844 layout viewport) and the
// visual viewport dragged down the layout viewport until the fixed bottom:0 bar (800..844) is in the visible band: the fixed
// body follows the pan, so the composer rides at the band's bottom edge and would meet the bar. The bar's box decides
// whenever it can be read: at offsetTop 340 the band ends at 800 and the bar is hidden (no strip); at 341 its top pixel is
// in the band and the strip is reserved; at 384 (the band 384..844, the bar wholly inside) too. The first cut took upstream's
// height difference first (844 - 460 > 120: a keyboard) and collapsed the strip over the composer in the last two
visualViewport.height = 460; visualViewport.offsetTop = 340; fire(VV, 'resize'); fire(VV, 'scroll'); flush();
out.barUnderTheBand = { appTop: appTop(), appH: appH(), barH: barH() };
visualViewport.offsetTop = 341; fire(VV, 'scroll'); flush();
out.barEntersTheBand = { appTop: appTop(), appH: appH(), barH: barH() };
visualViewport.offsetTop = 384; fire(VV, 'scroll'); flush();
out.barInTheBand = { appTop: appTop(), appH: appH(), barH: barH() };
// the author's pass 4 (2026-09-20): a PINCH over the deep pan. The band the shell published stands (the pan holds at 384, --app-h is
// upstream's 230 * 2) and the bar is wholly inside it, so the strip stands too. The author's pass 3 reading handed a pinch back to
// upstream's height difference (844 - 460 > 120: a keyboard), which collapsed the strip and put the bar over the composer
// for as long as the zoom held
visualViewport.scale = 2; visualViewport.height = 230; visualViewport.offsetTop = 384; fire(VV, 'resize'); fire(VV, 'scroll'); flush();
out.barInTheBandZoomed = { appTop: appTop(), appH: appH(), barH: barH() };
visualViewport.scale = 1; visualViewport.height = 844; visualViewport.offsetTop = 0; fire(VV, 'resize'); flush();
out.barInTheBandBack = { appTop: appTop(), appH: appH(), barH: barH() };
// the author's pass 4 (2026-09-20): the strip is PROPORTIONAL. The keyboard up (vv.height 460) and the pan swept across one bar height:
// the band ends at offsetTop + 460 and the fixed bottom:0 bar is 800..844, so the strip is the part of the bar inside the
// band, offsetTop - 340 clamped to 0..44: nothing at 340 and below, one pixel at 341, the whole bar at 384 and beyond. The
// all-or-nothing strip reserved 44 px from 341 up, a bar-tall band over a bar showing a few pixels.
// The author's pass 6 (2026-09-20): BOTH edges. The first proportional form read the band's bottom edge only (clamp(bandBottom - bar.top,
// 0, height)), so a band whose top sat below the bar's top reserved pixels above the band: the whole bar over a bar with no
// pixel inside it, more than a short band holds. The sweep drives every state where a variable of the overlap changes which
// operand min or max takes: the band's top passing the bar's top (800) and the bar's bottom (844); the bar's bottom passing
// the band's top (BAR.top 296, 320, 339, 340 against a band from 340) and a bar wholly above the band (BAR.top 100); a short
// band (vv.height 60) panned deep; the band a refused height report leaves standing after a rotation (innerHeight 390 puts
// the bar at 346..390 while the last published band, 384..844, stands); a band shorter than the bar (vv.height 30: the first
// form reserved more than the band holds); and the deep pan (384), the CONTROL: the test asserts both forms agree on it and
// on every state whose band top is not below the bar's top, and differ on every state whose band top is (the author's pass 8, 2026-09-20).
// Each record carries the bar's box and the band the shell published, so the test derives the overlap from the geometry
// it reads back, not from a formula of its own.
const sweep = [];
const box = () => { const b = BAR.getBoundingClientRect(); return { top: b.top, bottom: b.bottom }; };
const step = (label, vvH, ot, barTop) => {
  BAR.top = barTop === undefined ? null : barTop; visualViewport.height = vvH; visualViewport.offsetTop = ot;
  fire(VV, 'resize'); fire(VV, 'scroll'); flush();
  sweep.push({ label, innerHeight: global.innerHeight, vvHeight: vvH, ot, bar: box(), appTop: appTop(), appH: appH(), barH: barH() });
};
for (const ot of [336, 340, 341, 345, 351, 362, 373, 380, 383, 384, 388]) step('ot' + ot, 460, ot);
for (const ot of [799, 800, 801, 810, 822, 843, 844, 845]) step('top' + ot, 460, ot);    // the band's top passes the bar's box
for (const bt of [100, 296, 320, 339, 340]) step('bar' + bt, 460, 340, bt);               // the bar's bottom passes the band's top
step('short810', 60, 810);                                                                  // a short band panned deep
step('short30', 30, 810);                                                                   // a band shorter than the bar: 810..840
step('deep384', 460, 384);
// the stale band: a rotation moves the bar's box (innerHeight 390, the bar 346..390) and the height report is refused (0), so
// the band last published (384..844) stands and the bar's pixels inside it are 384..390
global.innerHeight = 390; visualViewport.height = 0; visualViewport.offsetTop = 0; fire(WIN, 'resize'); fire(VV, 'resize'); flush();
sweep.push({ label: 'staleAfterRotation', innerHeight: 390, vvHeight: 0, ot: 0, bar: box(), appTop: appTop(), appH: appH(), barH: barH() });
global.innerHeight = 844; BAR.top = null;
out.sweep = sweep;
visualViewport.height = 844; visualViewport.offsetTop = 0; fire(VV, 'resize'); flush();
// the author's pass 2 (2026-09-19): the writer's other population. fit() publishes a pan only off a coarse pointer; a FINE pointer writes
// 0px whatever the visual viewport says (no soft keyboard to pan for), so a fine-pointer window the mobile query still
// matches by width alone (at or under 820 px) takes the fixed body at top 0. From a panned state, the pointer turns fine
// (the stub answers the coarse probe; the layout query object was captured at parse and is not re-read). The stub is a
// module-scope global, restored before the next step. --mtabs-h IS read here (the author's pass 6, 2026-09-20): on the fine-pointer road
// the published band is 0 to the layout viewport (clientHeight; the author's pass 9, 2026-09-20: it had said innerHeight, the fallback only)
// whatever the visual viewport says, the bar's box (800..844) is wholly inside it, and
// the strip is the bar's whole height, 44. That is a behaviour change from upstream's pointer-ungated kbOpen, which read
// 844 - 460 > 120 as a keyboard and collapsed the strip, the bar over the composer, on a fine pointer whose visual viewport
// was shorter than the layout viewport (a desktop zoom reported at scale 1).
visualViewport.height = 460; visualViewport.offsetTop = 83; fire(VV, 'resize'); fire(VV, 'scroll'); flush();
const savedMatchMedia = global.matchMedia; global.matchMedia = () => ({ matches: false });
fire(WIN, 'resize'); flush();
out.finePointer = { appTop: appTop(), appH: appH(), barH: barH() };
global.matchMedia = savedMatchMedia;
visualViewport.height = 844; visualViewport.offsetTop = 0; fire(VV, 'resize'); flush();
out.finePointerBack = { appTop: appTop(), appH: appH(), barH: barH() };
// the author's pass 4 (2026-09-20): the 0px road and the hold. From a pan (83) the pointer turns fine (0px published) with the keyboard
// still up and its pan standing, then coarse again under a zoom whose clamp is slack (230 * 2 = 460, so 844 - 460 leaves room
// for 83). The author's pass 6 (2026-09-20): the hold STANDS across that flip, so the pinch road publishes the keyboard's pan, 83; the author's pass 4
// had the 0px road write the hold on every fine run, so this state published 0px under a keyboard-sized --app-h, the band
// reopened for as long as the zoom held (and the leg pinned that value as right)
visualViewport.height = 460; visualViewport.offsetTop = 83; fire(VV, 'resize'); fire(VV, 'scroll'); flush();
global.matchMedia = () => ({ matches: false }); fire(WIN, 'resize'); flush();
out.fineFromPan = appTop();
global.matchMedia = savedMatchMedia;
visualViewport.scale = 2; visualViewport.height = 230; visualViewport.offsetTop = 83; fire(VV, 'resize'); fire(VV, 'scroll'); flush();
out.coarseAgainZoomed = { appTop: appTop(), appH: appH() };
visualViewport.scale = 1; visualViewport.height = 844; visualViewport.offsetTop = 0; fire(VV, 'resize'); flush();
out.coarseAgainBack = { appTop: appTop(), appH: appH(), barH: barH() };
// the author's pass 6 (2026-09-20): the 0px road's CONDITION, both sides of every variable in it. The road clears the hold only in a true
// no-pan state, one the measured road would store as 0: no visual viewport, or one under the cut (pinched: L/(L - 0.5), the scale
// at which a zoom's own pan can round to a pixel, 1.0006 at the layout viewport L of 844, the height both roads take the cut at
// since the author's pass 9, 2026-09-20, when the coarse road had taken it at its own h; the cut itself is a pinch, so the hold stands there) whose
// offsetTop rounds to no positive pixel, the reading the measured road stores (panPx; the author's pass 8, 2026-09-20:
// the road had read the raw offsetTop, so 0.4 kept the hold here and stored 0 there) (the keyboard gone in the same run the
// pointer turned fine, the kernel-4 case); a
// standing pan (one pixel) or a standing zoom (scale 1.02) leaves it. Each state: the hold from a pan (83), the pointer turns
// fine in the given visual-viewport state (one run), coarse again under the slack zoom so the pinch road publishes the hold
const flips = {};
const flip = (label, vvState) => {
  visualViewport.scale = 1; visualViewport.height = 460; visualViewport.offsetTop = 83; fire(VV, 'resize'); fire(VV, 'scroll'); flush();
  const saved = global.visualViewport;
  if (vvState === null) global.visualViewport = null; else Object.assign(visualViewport, vvState);
  global.matchMedia = () => ({ matches: false }); fire(WIN, 'resize'); flush();
  const fine = { appTop: appTop(), appH: appH() };
  global.visualViewport = saved; global.matchMedia = savedMatchMedia;
  visualViewport.scale = 2; visualViewport.height = 230; visualViewport.offsetTop = 83; fire(VV, 'resize'); fire(VV, 'scroll'); flush();
  flips[label] = { fine, coarseAgainZoomed: { appTop: appTop(), appH: appH() } };
  visualViewport.scale = 1; visualViewport.height = 844; visualViewport.offsetTop = 0; fire(VV, 'resize'); fire(VV, 'scroll'); flush();
};
flip('noVV', null);                                             // no visual viewport: no pan is possible, cleared
flip('atRest', { height: 844, offsetTop: 0, scale: 1 });        // the keyboard gone in the flip's own run: cleared
flip('scaleUnderCut', { height: 843.578, offsetTop: 0, scale: 1.0005 }); // under the cut (a zoom pan of at most 0.42 px), unzoomed: cleared (the author's pass 8)
flip('scaleOverCut', { height: 843.41, offsetTop: 0, scale: 1.0007 });   // over the cut (0.59 px could round to a pixel): a pinch, the hold stands (the author's pass 8)
flip('scaleAtCut', { height: 843.5, offsetTop: 0, scale: 844 / 843.5 });  // AT the cut, the same double the helper computes: a pinch, the hold stands (the author's pass 8, the fixer pass)
flip('scaleAboveCut', { height: 844, offsetTop: 0, scale: 1.02 }); // a standing zoom: the hold stands
flip('onePixelPan', { height: 460, offsetTop: 1, scale: 1 });   // a standing pan of one pixel: the hold stands
flip('subPixelPan', { height: 460, offsetTop: 0.4, scale: 1 }); // rounds to no pixel, the measured road would have stored 0: cleared (the author's pass 8)
flip('halfPixelPan', { height: 460, offsetTop: 0.5, scale: 1 }); // rounds up to one pixel, a pan on both roads: the hold stands (the author's pass 8)
flip('zoomedTop', { height: 422, offsetTop: 0, scale: 2 });     // zoomed with the keyboard gone, at the top: the hold stands
flip('zoomPan', { height: 422, offsetTop: 200, scale: 2 });     // a zoom pan with the keyboard gone: the hold stands
out.flips = flips;
// the author's pass 8 (2026-09-20, the fixer pass): the fine road with NO layout height (h 0: innerHeight 0 and the document element's
// clientHeight 0, LAYOUT.h null). The cut L/(L - 0.5) is undefined there and pinched() counts the report as a pinch, so the hold
// stands where a resting visual viewport at h 844 (the atRest flip) clears it; the --app-h write is skipped (h 0) and --app-top
// is written 0px. A cell on the helper's third outcome: the item-1 kernel cleared the hold here and nothing drove it
visualViewport.scale = 1; visualViewport.height = 460; visualViewport.offsetTop = 83; fire(VV, 'resize'); fire(VV, 'scroll'); flush();
global.innerHeight = 0; Object.assign(visualViewport, { height: 844, offsetTop: 0, scale: 1 });
global.matchMedia = () => ({ matches: false }); fire(WIN, 'resize'); flush();
out.h0Fine = { appTop: appTop(), appH: appH(), innerHeight: global.innerHeight, clientHeight: document.documentElement.clientHeight };
global.innerHeight = 844; global.matchMedia = savedMatchMedia;
visualViewport.scale = 2; visualViewport.height = 230; visualViewport.offsetTop = 83; fire(VV, 'resize'); fire(VV, 'scroll'); flush();
out.h0CoarseAgainZoomed = { appTop: appTop(), appH: appH() };
visualViewport.scale = 1; visualViewport.height = 844; visualViewport.offsetTop = 0; fire(VV, 'resize'); fire(VV, 'scroll'); flush();
// the author's pass 7 (2026-09-20): the ENGINE MODEL of innerHeight under a pinch, and every sign of the clamp's difference. The model (Chromium
// keeps window.innerHeight at the layout viewport's height under a pinch, WebKit shrinks it to the visual viewport's) and the
// reachability of a pinch on iOS Safari are the two premises kernel.py's fit() comment states, with their evidence status, in one
// place; this block drives the model, it does not verify it. A clamp reading innerHeight saw a difference below 0 on every zoomed
// run under it and published 0px whatever the hold, the band under the composer reopened for as long as the zoom held; every
// step above kept innerHeight at 844 through the pinch, the Chromium model. The clamp reads
// document.documentElement.clientHeight, the layout viewport in both models, and the stub parts the two here: LAYOUT.h holds
// the layout height while innerHeight tracks vv.height, and the bar's box stays at the layout viewport's bottom (800..844), as a
// fixed bottom:0 box does under a WebKit pinch. The difference's three states: SLACK (844 - 460: the hold, 83, is published),
// ZERO (844 - 844, the keyboard gone under the zoom: 0px), and NEGATIVE (a rotation under the standing zoom: the layout
// viewport is 390 while the visual viewport's last report still says 422 at scale 2, h 844, so max(0, 390 - 844) binds at 0 and
// the road publishes 0px, never -454px). Each record carries innerHeight and clientHeight, so the test derives the model and
// the sign from what it reads back.
visualViewport.scale = 1; visualViewport.height = 460; visualViewport.offsetTop = 83; fire(VV, 'resize'); fire(VV, 'scroll'); flush();
const clientHeight = () => document.documentElement.clientHeight;
LAYOUT.h = 844; BAR.top = 800;
global.innerHeight = 230; visualViewport.scale = 2; visualViewport.height = 230; visualViewport.offsetTop = 83; fire(WIN, 'resize'); fire(VV, 'resize'); fire(VV, 'scroll'); flush();
out.webkitPinchPanned = { appTop: appTop(), appH: appH(), barH: barH(), innerHeight: global.innerHeight, clientHeight: clientHeight() };
global.innerHeight = 422; visualViewport.height = 422; visualViewport.offsetTop = 200; fire(WIN, 'resize'); fire(VV, 'resize'); fire(VV, 'scroll'); flush();
out.webkitKbDownZoomed = { appTop: appTop(), appH: appH(), barH: barH(), innerHeight: global.innerHeight, clientHeight: clientHeight() };
// the rotation under the zoom: the layout viewport is 390 (the fixed bar rides its bottom, 346..390) and the visual viewport's
// report is still the one above (422 at scale 2), so h is 844 against a layout height of 390
LAYOUT.h = 390; BAR.top = null; fire(WIN, 'resize'); flush();
out.rotatedUnderZoom = { appTop: appTop(), appH: appH(), barH: barH(), innerHeight: global.innerHeight, clientHeight: clientHeight(),
  vvBottom: Math.round(visualViewport.offsetTop + visualViewport.height) };   // the stale report's bottom edge, what inside() compares
// the author's pass 8 (2026-09-20): the FINE-POINTER road under the same model. The pointer turns fine while the zoom stands and the layout
// viewport (844) is parted from innerHeight (422 at scale 2): the road reads the layout viewport (clientHeight, the fork line after
// upstream's h assignment), so the published band is 0..844 and the bar (800..844) is wholly inside it, the strip its whole height.
// It had read innerHeight and published a 422 px band with the bar outside it (appH 422px, barH 0px). Then the same parting with
// no visualViewport at all (the other population of that road; barfit falls to upstream's reading there, which reserves the bar)
LAYOUT.h = 844; BAR.top = 800; global.innerHeight = 422; visualViewport.scale = 2; visualViewport.height = 422; visualViewport.offsetTop = 0;
global.matchMedia = () => ({ matches: false }); fire(WIN, 'resize'); flush();
out.finePointerWebKit = { appTop: appTop(), appH: appH(), barH: barH(), innerHeight: global.innerHeight, clientHeight: clientHeight() };
global.matchMedia = savedMatchMedia;
const savedVV = global.visualViewport; global.visualViewport = null; fire(WIN, 'resize'); flush();
out.noVVWebKit = { appTop: appTop(), appH: appH(), barH: barH(), innerHeight: global.innerHeight, clientHeight: clientHeight() };
global.visualViewport = savedVV;
LAYOUT.h = null; BAR.top = null; global.innerHeight = 844; visualViewport.scale = 1; visualViewport.height = 844; visualViewport.offsetTop = 0; fire(WIN, 'resize'); fire(VV, 'resize'); fire(VV, 'scroll'); flush();
out.webkitBack = { appTop: appTop(), appH: appH(), barH: barH(), innerHeight: global.innerHeight, clientHeight: clientHeight() };
// the maintainer's round 6 ruling (2026-09-29): the pinch road's HOLD across a drag, a continuous pinch and a keyboard raised again
// under a zoom, in families that each start from rest (the measured road stores 0 there and clears the flag). The keyboard's band
// is 508 unzoomed, so a report at scale s with the keyboard up is 508/s tall and one with it down 844/s. Every step records the
// report it drove and what the shell published, so the test derives the reading's interval from the geometry it drove (the
// reading less the zoom's share, both in pixels, up to the reading) and never from the kernel's own arithmetic. The families then
// run a second time with each report fired twice, a refit with nothing new after every step (fit() runs again on ordinary events),
// into out.r6refit, each step recording what its second run published beside its first (refit). That pass is its own sequence (a
// refit can change what fit() keeps, kz after a raise below the cut, for one), so the values the tests read come from the first.
const r6 = {}, r6d = {};
let r6double = false;
const r6step = (fam, tag, height, offsetTop, scale) => {
  visualViewport.scale = scale; visualViewport.height = height; visualViewport.offsetTop = offsetTop;
  fire(VV, 'resize'); fire(VV, 'scroll'); flush();
  const row = { tag, height, offsetTop, scale, appTop: appTop(), appH: appH() }, book = r6double ? r6d : r6;
  if (r6double) { fire(VV, 'resize'); flush(); row.refit = appTop(); }
  (book[fam] = book[fam] || []).push(row);
};
const r6share = (s) => 844 * (1 - 1 / s);
const r6rest = (fam) => r6step(fam, 'rest', 844, 0, 1);
const r6families = () => {
// ui-1: a real pinch (scale 2) over a hold of 83, the visual viewport dragged to o (one pixel past the share, well past it, and
// past the hold plus the share), dragged back, then the keyboard down and raised again under the zoom
for (const o of [423, 500, 590]) {
  const f = 'drag' + o; r6rest(f);
  r6step(f, 'kbUp', 508, 83, 1); r6step(f, 'pinch2', 254, 83, 2); r6step(f, 'drag', 254, o, 2); r6step(f, 'back', 254, 83, 2);
  r6step(f, 'kbDownZ', 422, 200, 2); r6step(f, 'reRaiseZ', 254, 83, 2);
}
// ui-1's wider face: a continuous pinch from the hold (83) with the keyboard up, about the band's top, centre and bottom
for (const fp of [0, 0.5, 1]) {
  const f = 'pinch' + fp; r6rest(f); r6step(f, 'kbUp', 508, 83, 1);
  for (const s of [1.0007, 1.003, 1.01, 1.02, 1.05, 1.1, 1.2, 1.5, 2]) r6step(f, 's' + s, 508 / s, 83 + fp * 508 * (1 - 1 / s), s);
  r6step(f, 'kbDownZ', 422, 200, 2); r6step(f, 'reRaiseZ', 254, 83, 2);
}
// a hold of 0 (the keyboard up at scale 1 with no pan) under a pinch: dragged past the share, back, the keyboard down and up again
for (const [s, deep] of [[1.05, false], [2, true]]) {
  const f = 'hold0-' + s; r6rest(f); r6step(f, 'kbUp0', 508, 0, 1); r6step(f, 'pinchC', 508 / s, 0.5 * 508 * (1 - 1 / s), s);
  r6step(f, 'drag', 508 / s, deep ? 844 - 508 / s : r6share(s) + 40, s); r6step(f, 'back0', 508 / s, 0, s);
  r6step(f, 'down', 844 / s, 0, s); r6step(f, 'reNoPan', 508 / s, 0, s);
}
// extra10-1: the light-zoom window with no hold (the keyboard's first raise stores the reading less the share), the keyboard
// down, up with no pan, a pan inside the share, down, and up with its pan again; from the cut itself (844/843.5) up
for (const s of [844 / 843.5, 1.0007, 1.003, 1.008, 1.01, 1.05]) {
  const f = 'lz' + (+s.toFixed(5)); r6rest(f);
  r6step(f, 'A1-kbUpPan', 508 / s, 83, s); r6step(f, 'A2-kbDown', 844 / s, 0, s); r6step(f, 'A3-kbUpNoPan', 508 / s, 0, s);
  r6step(f, 'A4-kbUpPanInShare', 508 / s, r6share(s), s); r6step(f, 'A5-kbDown', 844 / s, 0, s); r6step(f, 'A6-kbUpPanAgain', 508 / s, 83, s);
}
// a hold from scale 1 (83), then the light zoom: the keyboard down, up with no pan, a pan of 2; and the no-pan report under the
// zoom with no keyboard-down run between
for (const s of [1.003, 1.01, 1.05]) {
  let f = 'hold83-lz' + s; r6rest(f); r6step(f, 'E1-kbUp', 508, 83, 1);
  r6step(f, 'E2-kbDownLZ', 844 / s, 0, s); r6step(f, 'E3-kbUpNoPanLZ', 508 / s, 0, s); r6step(f, 'E4-kbUpPan2LZ', 508 / s, 2, s);
  f = 'hold83-direct' + s; r6rest(f); r6step(f, 'E1-kbUp', 508, 83, 1); r6step(f, 'E3b-noPanLZ', 508 / s, 0, s);
}
// no hold, the keyboard raised at the light zoom (the first raise stores the reading less the share), then dragged up
for (const s of [1.003, 1.01]) {
  const f = 'lzdrag' + s; r6rest(f); r6step(f, 'G1-kbUpPan', 508 / s, 83, s);
  for (const o of [0, 2, 40]) r6step(f, 'G-dragTo' + o, 508 / s, o, s);
}
// a small hold (1: a no-hold drag one pixel past the share at scale 2), then the keyboard at the light zoom, with and without a pan
{ const f = 'smallHold'; r6rest(f); r6step(f, 'S1-kbUpZ423', 254, 423, 2); r6step(f, 'S2-kbDownZ', 422, 200, 2);
  r6step(f, 'S3-lzKbUpPan', 508 / 1.003, 83.7, 1.003); r6step(f, 'S4-lzKbUpNoPan', 508 / 1.003, 0, 1.003); }
// a hold of p at scale 1, a pinch about the band's centre to s, then the keyboard down and raised again under the zoom: with no
// pan, with a pan inside the share, and the first field again (its own pan p, the zoom unpanned). The holds sit at or under the
// zoom's share (30 under 40 at 1.05; 83 under 141 at 1.2 and 422 at 2), and three scales put the share exactly one pixel under,
// at and over a hold of 83 (82, 83, 84: s = 844/(844 - z))
for (const [p, s, tag] of [[30, 1.05, 'p30-s1.05'], [83, 1.2, 'p83-s1.2'], [83, 2, 'p83-s2'],
                           [83, 844 / 762, 'share82'], [83, 844 / 761, 'share83'], [83, 844 / 760, 'share84']]) {
  const f = 'reraise-' + tag, o = p + 0.5 * 508 * (1 - 1 / s), down = (t) => r6step(f, t, 844 / s, Math.min(o, r6share(s)), s);
  r6rest(f); r6step(f, 'kbUp1', 508, p, 1); r6step(f, 'pinchC', 508 / s, o, s);
  down('down1'); r6step(f, 'reNoPan', 508 / s, 0, s);
  down('down2'); r6step(f, 'reInShare', 508 / s, r6share(s) / 2, s);
  down('down3'); r6step(f, 'reSameP', 508 / s, p, s);
}
// the real-pinch stance: a hold of 83, a pinch to 2 at 200, dragged up to 40 and to 0 (the shell stays at the hold); and no
// hold under the pinch, the keyboard raised there, dragged past the share (the excess is stored: no hold was held), back, up
{ const f = 'stance'; r6rest(f); r6step(f, 'P1-kbUp', 508, 83, 1); r6step(f, 'P2-at200', 254, 200, 2);
  r6step(f, 'P3-up40', 254, 40, 2); r6step(f, 'P4-at0', 254, 0, 2); }
{ const f = 'nohold'; r6rest(f); r6step(f, 'Z1-kbUpZ', 230, 83, 2); r6step(f, 'Z2-drag500', 230, 500, 2);
  r6step(f, 'Z3-back83', 230, 83, 2); r6step(f, 'Z4-to10', 230, 10, 2); }
// a pan of a keyboard raised at this zoom where the zoom's share reaches the value: a hold measured at the light zoom (1.05,
// the zoom unpanned: the reading 60 less the share's 40, 20) and the same keyboard's pan dragged to the top
{ const s = 1.05, f = 'lzhold20'; r6rest(f); r6step(f, 'zoom', 844 / s, r6share(s) / 2, s);
  r6step(f, 'kbUpLZ', 508 / s, Math.round(r6share(s)) + 20, s); r6step(f, 'dragTo0', 508 / s, 0, s); }
// the same hold, then a zoom alone to 1.1 and back to 1.05 with the keyboard up (the band 508 throughout, so no keyboard event),
// then the same drag to the top: the zoom's scale is the one the raise wrote at again, but a zoom alone came since
{ const s = 1.05, f = 'zoomBack'; r6rest(f); r6step(f, 'zoom', 844 / s, r6share(s) / 2, s);
  r6step(f, 'kbUpLZ', 508 / s, Math.round(r6share(s)) + 20, s); r6step(f, 'zoomAway', 508 / 1.1, 60, 1.1);
  r6step(f, 'zoomBackTo1.05', 508 / s, 60, s); r6step(f, 'dragTo0', 508 / s, 0, s); }
// a zoom alone after a pan the rule re-bounded (disclosed in the fit() comment): the rule's value is published and not stored, so
// the zoom alone publishes from the value in force, here the re-raise bound 0. No hold, the keyboard raised at 1.05, down, up with
// no pan, the pan to the share (40), then a zoom alone to 1.1 about the band's centre, and back to 1.05 at the same pan
{ const s = 1.05, f = 'zoomAfterPan'; r6rest(f);
  r6step(f, 'A1-kbUpPan', 508 / s, 83, s); r6step(f, 'A2-kbDown', 844 / s, 0, s); r6step(f, 'A3-kbUpNoPan', 508 / s, 0, s);
  r6step(f, 'A4-kbUpPanInShare', 508 / s, r6share(s), s);
  r6step(f, 'zoomAlone1.1', 508 / 1.1, r6share(s) + 0.5 * 508 * (1 / s - 1 / 1.1), 1.1); r6step(f, 'zoomBack1.05', 508 / s, r6share(s), s); }
// a hold of 83 raised at scale 1, then ONE report that pinches to 2 as a taller keyboard comes in (the band 508 to 460: no zoom
// alone, since h changed, and no raise, since no keyboard-down run came between), then that keyboard's pan up to 40
{ const f = 'swapZoom'; r6rest(f); r6step(f, 'kbUp', 508, 83, 1); r6step(f, 'swapPinch2', 230, 200, 2); r6step(f, 'up40', 230, 40, 2); }
// a pan after a re-raise bound above the hold (the maintainer's round 6 ruling, 2026-09-29): a hold of 83 at scale 1, the keyboard
// down under a zoom, raised again with the visual viewport deep (the re-raise bound, the reading less the share, above the hold),
// then that keyboard panned back up. The pan rule re-bounds from the larger of the hold and the value in force, here the re-raise
// bound; from the hold alone it had published 83 and opened a band under the composer
for (const [s, deep, pan] of [[2, 590, 422], [1.5, 495.2, 281.33], [1.1, 250, 150]]) {
  const f = 'reraiseDeep' + s; r6rest(f); r6step(f, 'E1-kbUp', 508, 83, 1); r6step(f, 'E2-kbDownZ', 844 / s, 0, s);
  r6step(f, 'E3-reRaiseDeep', 508 / s, deep, s); r6step(f, 'P-panUp', 508 / s, pan, s);
}
// the pan rule's scope (the maintainer's round 6 ruling, 2026-09-29, on its focused re-check): the 508 px keyboard raised at 2 with
// the visual viewport at 500 (the reading less the share, 78, written with kz the scale), then a stale report at the same scale
// whose visual viewport does not fit inside the layout viewport (at 700, its bottom at 868 over 844)
{ const f = 'staleOutside2'; r6rest(f); r6step(f, 'raiseZ', 336 / 2, 500, 2); r6step(f, 'staleOutside', 336 / 2, 700, 2); }
// a keyboard of another height swapped in at the zoom of the raise that wrote the value in force, then the same report again (the
// maintainer's round 6 ruling, 2026-09-29): the rule does not ask for the band's height to be unchanged, so the swap's own run
// is a pan and takes the pan rule, and a refit at the same geometry publishes the same value (with the height in the test the
// swap's run took the stance and the refit the rule, so a refit with nothing new moved --app-top). At 2, a 471 px keyboard (band
// 373) raised at the layout viewport's bottom, then the 508 px keyboard (band 336) at 40; at 1.5, the 508 px keyboard at 555.74,
// then the 471 px keyboard at 83
{ const f = 'swapRefit2'; r6rest(f); r6step(f, 'kb471up', 373 / 2, 657.5, 2);
  for (const t of ['swap508', 'refit', 'refit2']) r6step(f, t, 336 / 2, 40, 2); }
{ const f = 'swapRefit1.5'; r6rest(f); r6step(f, 'kb508up', 336 / 1.5, 555.74, 1.5);
  for (const t of ['swap471', 'refit']) r6step(f, t, 373 / 1.5, 83, 1.5); }
// the corner where a refit had moved --app-top, closed by the maintainer's round 6 ruling (2026-09-29: any change of scale between
// runs on the measured or hold road clears kz, the zoom of the raise that wrote the value in force; a fine pointer's runs record no
// scale, so a change only they saw does not). While only a zoom alone cleared it, kz stood through a report that changed
// the scale and h together, and a later such report back at kz's zoom was no pan on its own run (the scale changed since the
// previous run) and took the stance, while its refit, the same report again, was a pan at kz's zoom and took the pan rule. Each
// family raises the 508 px keyboard under a zoom of s0 with no hold (the measured road writes the reading less the share, and kz is
// s0), then drives ONE report at s1 that changes h too, then ONE report back to s0 with the 508 px keyboard, then the refit. The
// report at s1 takes one of three measured roads: the 471 px keyboard comes in (swapZoomBack), the same keyboard's band rounds a
// pixel over, a visual viewport 336.6/s1 tall and h 337 (roundFlip), or the keyboard goes down with the visual viewport outside the
// layout viewport, a report the keyboard-down run does not read, so the return is no re-raise (downOutside)
for (const [s0, s1, o0, o2, od] of [[2, 1.5, 500, 40, 300], [1.5, 1.2, 400, 100, 200]]) {
  let f = 'swapZoomBack' + s0; r6rest(f); r6step(f, 'raiseZ', 336 / s0, o0, s0);
  r6step(f, 'zoomSwap', 373 / s1, 100, s1); r6step(f, 'zoomSwapBack', 336 / s0, o2, s0); r6step(f, 'refit', 336 / s0, o2, s0);
  f = 'roundFlip' + s0; r6rest(f); r6step(f, 'raiseZ', 336 / s0, o0, s0);
  r6step(f, 'zoomRound', 336.6 / s1, 100, s1); r6step(f, 'zoomRoundBack', 336 / s0, o2, s0); r6step(f, 'refit', 336 / s0, o2, s0);
  f = 'downOutside' + s0; r6rest(f); r6step(f, 'raiseZ', 336 / s0, o0, s0);
  r6step(f, 'zoomDown', 844 / s1, od, s1); r6step(f, 'zoomUpBack', 336 / s0, o2, s0); r6step(f, 'refit', 336 / s0, o2, s0);
}
// the measured road's value past the clamp, where a refit had moved --app-top by a pixel, closed by the maintainer's round 6 ruling
// (2026-09-29: under a pinch the measured road clamps what it publishes at use, at L - h, and still writes kbPx). It had published
// kbPx unclamped and written the hold, and the refit took the hold road, which clamps at L - h. Rounding can put kbPx a pixel above
// L - h where the visual viewport sits within half a pixel of the layout viewport's bottom and the zoom's share of the band's
// shortfall is under a pixel. From rest, one such report, then the refit: h 843 (L - h 1) under a zoom of 1.00155 and h 694
// (L - h 150) under 1.00169; the two cells the fit() comment cites for the case's reach, h 309 (L - h 535, a share of 0.95 px) under
// 1.00178 and h 843 (L - h 1) under 1.9976; and the same rounding at scale 1, under the cut, where the clamp does not apply: the visual
// viewport 760.6 tall at 83.6, h 761 (L - h 83), the reading 84. Then what the measured road writes under that clamp: from rest, a
// report under 1.005 with no keyboard (h 844, L - h 0) and the visual viewport 839.5 tall at 4.6, at the layout viewport's bottom (the
// reading 5 less the share's 4, kbPx 1, published as the clamp's 0), then the 471 px band at the same zoom with the visual viewport at
// 4, a reading the share explains (kbPx 0), so the hold road publishes from the value the measured road wrote
{ let f = 'clampFace1'; r6rest(f); r6step(f, 'lightPinch', 841.3459, 2.6541, 1.00155); r6step(f, 'refit', 841.3459, 2.6541, 1.00155);
  f = 'clampFace150'; r6rest(f); r6step(f, 'lightPinch', 692.4298, 151.5702, 1.00169); r6step(f, 'refit', 692.4298, 151.5702, 1.00169);
  f = 'clampFace535'; r6rest(f); r6step(f, 'lightPinch', 307.976, 536.5, 1.00178); r6step(f, 'refit', 307.976, 536.5, 1.00178);
  f = 'clampFaceDeep'; r6rest(f); r6step(f, 'deepPinch', 421.76, 422.73, 1.9976); r6step(f, 'refit', 421.76, 422.73, 1.9976);
  f = 'clampFaceS1'; r6rest(f); r6step(f, 'lightPinch', 760.6, 83.6, 1); r6step(f, 'refit', 760.6, 83.6, 1);
  f = 'clampThenKbUp'; r6rest(f); r6step(f, 'pinchAtBottom', 839.5, 4.6, 1.005); r6step(f, 'kbUpSameZoom', 471 / 1.005, 4, 1.005); }
// the stance's third cost (disclosed in the fit() comment): a keyboard re-raised with no pan under a light zoom s0 (the value in
// force its re-raise bound, 0), a zoom alone to s1 about the band's top, then that keyboard panned down to s1's share. With no
// hold (the keyboard's first raise at s0 stores the reading less the share) and with a hold of 83 from scale 1
for (const [s0, s1] of [[1.05, 1.1], [1.05, 1.06], [1.01, 1.02], [1.003, 1.01]]) {
  let f = 'zoomThenPanDown-' + s0 + '-' + s1; r6rest(f);
  r6step(f, 'A1-kbUpPan', 508 / s0, 83, s0); r6step(f, 'A2-kbDown', 844 / s0, 0, s0); r6step(f, 'A3-kbUpNoPan', 508 / s0, 0, s0);
  r6step(f, 'Z-zoomAlone', 508 / s1, 0, s1); r6step(f, 'P-panDown', 508 / s1, r6share(s1), s1);
  f = 'zoomThenPanDown-hold83-' + s0 + '-' + s1; r6rest(f); r6step(f, 'E1-kbUp', 508, 83, 1);
  r6step(f, 'E2-kbDownLZ', 844 / s0, 0, s0); r6step(f, 'E3-kbUpNoPanLZ', 508 / s0, 0, s0);
  r6step(f, 'Z-zoomAlone', 508 / s1, 0, s1); r6step(f, 'P-panDown', 508 / s1, r6share(s1), s1);
}
// the 0px road clears the written-hold flag where it clears the hold (the maintainer's round 6 ruling, 2026-09-29, the flag's
// clearing rule): a hold of 83 at scale 1 (the band 460, the flag set), the pointer fine with the visual viewport at rest (the 0px
// road clears the hold and the flag), then coarse again under a real pinch with the same keyboard up, the nohold family's three
// reports from there: dragged past the zoom's share and back. With the flag cleared no hold is held, so the drag's excess is
// written as the nohold family's is and the drag back publishes it; a flag left standing over the cleared hold of 0 reads as a
// hold held, so the excess is published unwritten and the drag back publishes 0
{ const f = 'fineClear'; r6rest(f); r6step(f, 'kbUp', 460, 83, 1);
  global.matchMedia = () => ({ matches: false }); r6step(f, 'fineRest', 844, 0, 1); global.matchMedia = savedMatchMedia;
  r6step(f, 'Z1-kbUpZ', 230, 83, 2); r6step(f, 'Z2-drag500', 230, 500, 2); r6step(f, 'Z3-back83', 230, 83, 2); }
// and the rule's other half, the flag left where the hold is: the same hold, the pointer fine with the keyboard's pan standing
// (the 0px road leaves the hold and the flag), then the same three reports. The hold stands held, so the drag past the share
// writes nothing and publishes the larger of the hold and the excess, and the drag back publishes the hold; a 0px road that
// cleared the flag on every run would leave the hold unheld, and the drag would write its excess over it
{ const f = 'fineKeep'; r6rest(f); r6step(f, 'kbUp', 460, 83, 1);
  global.matchMedia = () => ({ matches: false }); r6step(f, 'finePan', 460, 83, 1); global.matchMedia = savedMatchMedia;
  r6step(f, 'Z1-kbUpZ', 230, 83, 2); r6step(f, 'Z2-drag500', 230, 500, 2); r6step(f, 'Z3-back83', 230, 83, 2); }
// the STANCE cells of round 6's extended families (its H1, H2, H4 and H6, first driven by a checker kept outside the tree), so the
// tree reads the published value of every one: a report under a pinch that no keyboard raised at that zoom governs. Each carries
// the family's hold, the value the stance keeps. x1: a hold of p at scale 1 pinched about the band's centre to s; x2: a hold of 0
// pinched, dragged past the share (by 1, by 40, and to the layout viewport's bottom), back to the top and to half the share; x4: a
// continuous pinch in to 3 and out again about the band's top, centre and bottom; x6: a hold of 83 pinched, dragged to the bottom
// and back to half the share (the cell the ungated pan rule moved at 1.2, 83 to 70), then the keyboard down and the first field again
const r6x = (fam, tag, height, offsetTop, scale, hold) => { r6step(fam, tag, height, offsetTop, scale); const b = r6double ? r6d : r6; b[fam][b[fam].length - 1].hold = hold; };
for (const p of [5, 10, 20, 30, 40, 60, 83, 120]) for (const s of [1.0007, 1.003, 1.01, 1.02, 1.05, 1.08, 1.1, 1.11, 1.2, 1.5, 2]) {
  const f = 'x1-p' + p + '-s' + s; r6rest(f); r6step(f, 'kbUp1', 508, p, 1); r6x(f, 'pinchC', 508 / s, p + 0.5 * 508 * (1 - 1 / s), s, p);
}
for (const s of [1.01, 1.05, 1.2, 2]) for (const o of ['share+1', 'share+40', 'deep']) {
  const f = 'x2-hold0-s' + s + '-' + o; r6rest(f); r6step(f, 'kbUp0', 508, 0, 1); r6x(f, 'pinchC', 508 / s, 0.5 * 508 * (1 - 1 / s), s, 0);
  r6x(f, 'drag', 508 / s, o === 'deep' ? 844 - 508 / s : Math.min(r6share(s) + (o === 'share+1' ? 1 : 40), 844 - 508 / s), s, 0);
  r6x(f, 'back0', 508 / s, 0, s, 0); r6x(f, 'backHalf', 508 / s, r6share(s) / 2, s, 0);
}
{ const sc = [1.0007, 1.002, 1.005, 1.01, 1.02, 1.05, 1.1, 1.2, 1.5, 2, 3];
  for (const p of [10, 40, 83, 200]) for (const fp of [0, 0.5, 1]) {
    const f = 'x4-p' + p + '-f' + fp; r6rest(f); r6step(f, 'kbUp1', 508, p, 1);
    sc.forEach((s) => r6x(f, 'in' + s, 508 / s, p + fp * 508 * (1 - 1 / s), s, p));
    sc.slice(0, -1).reverse().forEach((s) => r6x(f, 'out' + s, 508 / s, p + fp * 508 * (1 - 1 / s), s, p));
  } }
for (const s of [1.2, 1.5, 2, 3]) {
  const f = 'x6-deep-s' + s; r6rest(f); r6step(f, 'kbUp1', 508, 83, 1);
  r6x(f, 'pinchC', 508 / s, 83 + 0.5 * 508 * (1 - 1 / s), s, 83); r6x(f, 'deep', 508 / s, 844 - 508 / s, s, 83);
  r6x(f, 'backHalf', 508 / s, r6share(s) / 2, s, 83); r6step(f, 'down', 844 / s, 0, s); r6step(f, 'reSame', 508 / s, 83, s);
}
};
r6families(); r6double = true; r6families(); r6double = false;
out.r6 = r6; out.r6refit = r6d;
// extra6-1 (the maintainer's round 6 ruling, 2026-09-29): the coarse road takes the pinch cut at the layout viewport L, not at its
// own h. A hold of 83 (the keyboard up at scale 1, h 460), then a report BETWEEN the two cuts (scale 1.0008: at or over L/(L - 0.5),
// 1.00059 at L 844, and under h/(h - 0.5), 1.00109 at h 460) with the same keyboard (h 460 again) and a reading that rounds to no
// pixel (offsetTop 0.4), then a real pinch with the keyboard up. At L the report is a pinch: the hold road publishes the reading's
// 0 and writes nothing, so the pinch after it publishes the hold, 83. Taken at h the report is no pinch, and the measured road
// writes its 0 into the hold, so the pinch after it publishes 0: the first step reads 0 either way, the second tells the cuts apart
visualViewport.scale = 1; visualViewport.height = 460; visualViewport.offsetTop = 83; fire(VV, 'resize'); fire(VV, 'scroll'); flush();
const cutHold = appTop();
visualViewport.scale = 1.0008; visualViewport.height = 459.6; visualViewport.offsetTop = 0.4; fire(VV, 'resize'); fire(VV, 'scroll'); flush();
const cutBetween = { appTop: appTop(), appH: appH() };
visualViewport.scale = 2; visualViewport.height = 230; visualViewport.offsetTop = 83; fire(VV, 'resize'); fire(VV, 'scroll'); flush();
out.cutBetween = { hold: cutHold, between: cutBetween, pinchAfter: { appTop: appTop(), appH: appH() } };
// the property the maintainer's round 6 ruling (2026-09-29) pins: fit() is idempotent at an unchanged report, so a refit with nothing
// new never moves --app-top. The round's doubled-step fuzz, carried into the tree: 4000 seeded report sequences (mulberry32, seed
// 21) of 12 steps. Each sequence starts at rest (the pointer fine with the visual viewport at rest clears the hold, then coarse
// again); each step is a pan only, a zoom with the keyboard kept, a keyboard event at the zoom (a raise, a drop, or a swap between
// the 508 and 471 px keyboards), a zoom and a keyboard event in one report, a stale report outside the layout viewport, or now and
// then a pointer flip; then the same report fires again. A step whose second run publishes another --app-top than its first is
// counted, and the first ten are listed with their sequence up to that step, as (coarse, scale, keyboard, offsetTop, first run, refit)
{ let seed = 21, coarse = true, steps = 0, swapsAtZoom = 0, movedSteps = 0;
  const rnd = () => { seed |= 0; seed = seed + 0x6D2B79F5 | 0; let t = Math.imul(seed ^ seed >>> 15, 1 | seed); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
  const pick = (a) => a[Math.floor(rnd() * a.length)];
  const SC = [1, 1, 1.0003, 844 / 843.5, 1.0007, 1.003, 1.008, 1.01, 1.05, 1.1, 1.2, 1.5, 2, 3], KBS = [0, 508, 508, 508, 471], Lh = 844;
  const kinds = { pan: 0, zoom: 0, keyboard: 0, both: 0, outside: 0, flip: 0 }, moved = [];
  global.matchMedia = () => ({ matches: coarse });
  for (let q = 0; q < 4000; q++) {
    coarse = false; visualViewport.scale = 1; visualViewport.height = Lh; visualViewport.offsetTop = 0; fire(VV, 'resize'); flush();
    coarse = true; fire(VV, 'resize'); flush();
    let s = 1, kb = 0, o = 0; const seq = [];
    for (let i = 0; i < 12; i++) {
      const r = rnd(), kb0 = kb;
      if (r < 0.06) { coarse = !coarse; kinds.flip++; }
      else if (r < 0.40) {
        const hgt = (Lh - kb) / s; o = Math.max(0, Math.min(Lh - hgt, o + (rnd() - 0.5) * 300));
        if (rnd() < 0.3) o = pick([0, Math.max(0, Lh * (1 - 1 / s)) / 2, Math.max(0, Lh * (1 - 1 / s)), 83, 40, 2, Lh - hgt]);
        o = Math.max(0, Math.min(Lh - hgt, o)); kinds.pan++;
      } else if (r < 0.65) {
        s = pick(SC); const hgt = (Lh - kb) / s; o = Math.max(0, Math.min(Lh - hgt, o + (rnd() - 0.5) * 100)); kinds.zoom++;
      } else if (r < 0.92) {
        kb = pick(KBS); const hgt = (Lh - kb) / s; o = pick([0, 83, 40, 2, Math.max(0, Lh * (1 - 1 / s)), o]); o = Math.max(0, Math.min(Lh - hgt, o));
        kinds.keyboard++; if (kb0 && kb && kb !== kb0 && s >= Lh / (Lh - 0.5)) swapsAtZoom++;
      } else if (r < 0.97) {
        s = pick(SC); kb = pick(KBS); const hgt = (Lh - kb) / s; o = Math.max(0, Math.min(Lh - hgt, rnd() * (Lh - hgt))); kinds.both++;
      } else { o = Lh - (Lh - kb) / s + 50; kinds.outside++; }
      visualViewport.scale = s; visualViewport.height = (Lh - kb) / s; visualViewport.offsetTop = o;
      fire(VV, 'resize'); fire(VV, 'scroll'); flush();
      const first = appTop();
      fire(VV, 'resize'); flush(); steps++;
      seq.push([coarse ? 1 : 0, s, kb, +o.toFixed(3), first, appTop()]);
      if (appTop() !== first) { movedSteps++; if (moved.length < 10) moved.push(seq.slice()); }
    }
  }
  global.matchMedia = savedMatchMedia;
  out.idem = { steps, kinds, swapsAtZoom, movedSteps, moved };
}
visualViewport.scale = 1; visualViewport.height = 844; visualViewport.offsetTop = 0; fire(VV, 'resize'); fire(VV, 'scroll'); flush();
console.log(JSON.stringify(out));
"""


class MobileFitExecutes(unittest.TestCase):
    """The installed iPhone app came back from the background with the chat pane filling only the
    top ~60% of the screen: the composer mid-screen, a keyboard-tall blank band under it, the tab
    bar at the very bottom (the user 2026-09-08). --app-h had been measured while the keyboard was
    up and nothing re-measured it: the keyboard fell while the page was frozen, so the visual
    viewport's resize (the only keyboard event the fit listened to) never arrived, and on iOS the
    same resize sometimes fails to fire for a keyboard the composer's blur dismissed. The fix binds
    the fit to every event that moves the real viewport (visibilitychange, window focus, the
    composer's focusout heard through the same-origin pane window, alongside the resize / scroll /
    orientationchange / pageshow it already had), coalesces a burst to one fit per animation frame,
    and always recomputes from scratch, so a viewport that grows back is never left short."""

    @classmethod
    def setUpClass(cls):
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
            f.write(_FIT_HARNESS + _mobile_js() + _FIT_DRIVER)
            path = f.name
        try:
            r = subprocess.run(["node", path], capture_output=True, text=True, timeout=30)
        finally:
            os.unlink(path)
        # The harness runs the template as the page serves it (_mobile_js above: no placeholder is left to splice).
        assert r.returncode == 0, "the mobile script threw: " + r.stderr[:800]
        cls.out = json.loads(r.stdout.strip().splitlines()[-1])

    def test_the_fit_is_bound_to_every_event_that_moves_the_real_viewport(self):
        b = self.out["bound"]
        for ev in ("resize", "orientationchange", "pageshow", "focus"):
            self.assertIn(ev, b["win"], ev)
        for ev in ("visibilitychange", "focusout"):
            self.assertIn(ev, b["doc"], ev)
        self.assertEqual(b["vv"], ["resize", "scroll"])
        # the composer lives in the chat pane's document: its blur (keyboard dismissal) is heard
        # through the same-origin pane window, wired now and again on every (re)load
        self.assertEqual(b["chat"], ["focusout"])
        self.assertIn("f-chat", b["loads"])

    def test_boot_fits_at_once_from_the_visual_viewport(self):
        # the first paint is right without waiting a frame; the bar's reservation is measured too
        self.assertEqual(self.out["boot"], {"appH": "844px", "barH": "44px", "rafPending": 0})

    def test_the_2026_07_22_dead_band_the_strip_collapses_while_the_keyboard_hides_the_bar(self):
        # the user 2026-07-22: the fixed bar's reserved strip showed as a dead band between the composer and the keyboard
        # while the bar itself was hidden behind it. LandingShell's pin on upstream's write no longer decides the phone
        # (barfit is rebound; upstream's line is the fallback road's), so the report's behaviour is held here, executed: with
        # the keyboard up and the bar's box below the band, the strip is 0, in every sweep state with the bar wholly below
        # the band (derived from the box and the band each record carries, and there must be such states)
        self.assertEqual(self.out["kbUp"]["barH"], "0px", "the keyboard up: the bar hidden behind it reserves nothing")
        self.assertEqual(self.out["pan"]["barH"], "0px", "under iOS's pan too")
        px = lambda v: int(v[:-2])
        below = [r for r in self.out["sweep"] if r["bar"]["top"] >= px(r["appTop"]) + px(r["appH"])]
        self.assertGreaterEqual(len(below), 2, "sweep states with the bar wholly below the band")
        self.assertEqual({r["label"]: r["barH"] for r in below}, {r["label"]: "0px" for r in below})

    def test_the_keyboard_shrinks_the_shell_and_the_composers_blur_alone_grows_it_back(self):
        self.assertEqual(self.out["kbUp"], {"appH": "460px", "barH": "0px"})
        self.assertEqual(self.out["blurBeforeFrame"], "460px", "events schedule a frame; they do not fit inline")
        self.assertEqual(self.out["kbDown"], {"appH": "844px", "barH": "44px"})

    def test_coming_back_to_the_foreground_refits_a_keyboard_that_fell_while_hidden(self):
        self.assertEqual(self.out["hiddenFits"], 0, "going hidden is not new geometry")
        self.assertEqual(self.out["resume"], {"appH": "844px", "barH": "44px"})

    def test_a_resume_whose_final_geometry_lands_late_is_fitted_twice(self):
        # belt and braces: the fit at visible reads what iOS reports then; the visual-viewport resize
        # that follows a beat later is bound permanently, so it is the second fit — no timer
        self.assertEqual(self.out["resumeStale"], "460px")
        self.assertEqual(self.out["resumeSettled"], "844px")

    def test_a_burst_of_viewport_events_fits_once_per_frame(self):
        self.assertEqual(self.out["burst"], {"beforeFlush": 0, "pendingRafs": 1, "afterFlush": 1})

    def test_each_bound_event_refits_from_scratch_on_its_own(self):
        for ev, seen in self.out["each"].items():
            self.assertEqual(seen, ["700px", "844px"], ev)

    def test_a_ua_forced_page_offset_is_undone_on_the_same_frame(self):
        self.assertEqual(self.out["scrollReset"], [0, 0])

    # D1 (2026-09-19): the empty band between the composer and the keyboard on the installed iPhone app (the user
    # 2026-09-18 and 2026-09-19, with a screenshot). Two causes, both closed: the visual viewport's PAN, which fit() now
    # publishes as --app-top for the mobile body rule to sit at; and the bar's reservation surviving a keyboard that
    # shrinks the layout viewport too, which the rebound barfit now reads from the bar's own box against the band the shell published (upstream's kbOpen untouched).
    def test_the_visual_viewports_pan_is_published_for_the_body_to_sit_at(self):
        self.assertEqual(self.out["restTop"], "0px", "no pan at rest")
        self.assertEqual(self.out["pan"], {"appTop": "83px", "appH": "460px", "barH": "0px"})
        # the author's pass 4 (2026-09-20): the pan is published under the height's validity guard (the maintainer's round 1's fresh-3, landing here). A
        # report of height 0 with offsetTop 300 is refused whole: --app-h keeps 460 as before, and --app-top keeps 83 rather
        # than moving the fixed body by a pan measured against no height (the base tree published 300px).
        self.assertEqual(self.out["refusedHeight"], {"appTop": "83px", "appH": "460px", "barH": "0px"}, "a refused height report publishes no pan")
        self.assertEqual(self.out["panDown"], {"appTop": "0px", "appH": "844px", "barH": "44px"})

    def test_a_keyboard_that_shrinks_the_layout_viewport_collapses_the_reservation_only_for_a_hidden_bar(self):
        # innerHeight, vv.height and --app-h agree (an engine honouring resizes-content), so the height difference is
        # 0: the bar's box decides. Left below the visible band it is hidden and reserves nothing (the empty band);
        # riding the shrunken bottom it is visible above the keyboard and keeps its strip (Android Chrome today), so
        # the fixed bar never lands on the composer
        self.assertEqual(self.out["shrunkHidden"], {"appH": "460px", "barH": "0px", "appTop": "0px"})
        self.assertEqual(self.out["shrunkVisible"], {"appH": "460px", "barH": "44px"})
        self.assertEqual(self.out["shrunkBack"], {"appH": "844px", "barH": "44px"})

    def test_a_pinch_publishes_no_pan_and_keeps_the_bars_strip(self):
        # a pinch pans the visual viewport too, with no keyboard behind it: nothing about the shell's layout may move
        # under a pinch (the pinch-aware fit, 2026-08-19)
        self.assertEqual(self.out["pinch"], {"appTop": "0px", "appH": "844px", "barH": "44px"})
        self.assertEqual(self.out["pinchBack"], {"appTop": "0px", "appH": "844px", "barH": "44px"})

    def test_a_pan_held_through_a_pinch_cannot_outlive_the_height_it_was_measured_with(self):
        # the author's pass 2 (2026-09-19). The hold, from a PANNED state (the pinch pin above starts from --app-top already 0px, which the
        # opposite stance, zero on a pinch, satisfies identically): zoomed with the keyboard still up, the pan stands and --app-h
        # keeps upstream's scale arithmetic (230 * 2). Then the keyboard goes while the zoom holds: --app-h returns to the full
        # height on the same run and the held pan is clamped to the layout viewport's height less h, 0 here, so the body stays inside the layout
        # viewport. The base tree kept 83px and hung the body's bottom 83 px, the composer row, below the viewport.
        self.assertEqual(self.out["panAgain"], {"appTop": "83px", "appH": "460px", "barH": "0px"})
        self.assertEqual(self.out["pinchPanned"], {"appTop": "83px", "appH": "460px", "barH": "0px"}, "the hold, from a pan")
        self.assertEqual(self.out["kbDownZoomed"], {"appTop": "0px", "appH": "844px", "barH": "44px"}, "the clamp")
        # the author's pass 6 (2026-09-20): the validity guard's pinch half. A height report of 0 under the zoom publishes no pan: the
        # values stand where the clamp put them (a pinch road without the guard published min(83, 844 - 0) = 83px here)
        self.assertEqual(self.out["refusedZoomed"], {"appTop": "0px", "appH": "844px", "barH": "44px"}, "a refused height report under the zoom publishes no pan")
        # the author's pass 4 (2026-09-20): the clamp bounds what is published and leaves the hold standing, so the same field raised
        # again under the same zoom, at its own pan (83), finds its hold: since round 6 a keyboard raised again after going down
        # under the zoom is bounded from the hold into the reading's interval, and 83 lies inside it here (one raised with no pan
        # publishes what the reading allows, not the hold: test_a_keyboard_raised_again_under_a_zoom_publishes_what_the_reading_allows).
        # A clamp that wrote its result back (the author's pass 2 shape) had lowered the hold to 0 the first time it bound, and this
        # run then published 0px under a keyboard-sized --app-h.
        self.assertEqual(self.out["kbUpAgainZoomed"], {"appTop": "83px", "appH": "460px", "barH": "0px"}, "the hold survives the clamp")
        self.assertEqual(self.out["zoomBack"], {"appTop": "0px", "appH": "844px", "barH": "44px"})

    def test_a_bar_whose_box_starts_exactly_at_the_bands_bottom_edge_is_hidden(self):
        # the author's pass 2 (2026-09-19): the edge of the geometric reading, held by source text alone before. At exactly offsetTop +
        # vv.height the bar has no pixel inside the band and reserves nothing; one pixel higher, one pixel of it is inside the
        # band and the strip is that one pixel (the author's pass 4, 2026-09-20: the strip follows the pixels; it had reserved the whole bar)
        self.assertEqual(self.out["barAtTheEdge"], {"appH": "460px", "barH": "0px"})
        self.assertEqual(self.out["barOnePxIn"], {"appH": "460px", "barH": "1px"})
        self.assertEqual(self.out["barEdgeBack"], {"appH": "844px", "barH": "44px"})

    def test_a_bar_inside_the_band_under_a_pan_keeps_its_strip_whatever_the_height_difference_says(self):
        # the author's pass 3 (2026-09-19): the first cut read upstream's height difference FIRST and the bar's box only when that said no
        # keyboard, so with the keyboard up (844 - 460 > 120) and the visual viewport dragged down the layout viewport until
        # the fixed bar was inside the visible band, the strip still collapsed while the fixed body, following the pan, put
        # the composer at the band's bottom edge under the bar. The box decides whenever it can be read: hidden with the band
        # ending at the bar's top (offsetTop 340), one pixel inside one pixel further (341) and wholly inside (384). The first
        # cut gave 0px in all three; the author's pass 3 strip gave 44px at 341, a bar-tall strip over one pixel of bar (the author's pass 4,
        # 2026-09-20: the strip is the part of the bar inside the band, the sweep test below)
        self.assertEqual(self.out["barUnderTheBand"], {"appTop": "340px", "appH": "460px", "barH": "0px"})
        self.assertEqual(self.out["barEntersTheBand"], {"appTop": "341px", "appH": "460px", "barH": "1px"}, "one pixel of the bar in the band")
        self.assertEqual(self.out["barInTheBand"], {"appTop": "384px", "appH": "460px", "barH": "44px"}, "the bar wholly inside the band")
        self.assertEqual(self.out["barInTheBandBack"], {"appTop": "0px", "appH": "844px", "barH": "44px"})

    def test_the_strip_is_the_part_of_the_bar_inside_the_band_across_the_pan_range(self):
        # the author's pass 4 (2026-09-20): pinning an endpoint does not pin a range. With the keyboard up (vv.height 460 in an 844 layout
        # viewport) and the fixed bottom:0 bar at 800..844, the band ends at offsetTop + 460, so the bar's pixels inside the
        # band are offsetTop - 340 clamped to 0..44, and --mtabs-h is exactly that at every position: the composer then sits
        # flush above the bar's visible part and no strip stands over bar the keyboard hides. The author's pass 3 strip was the
        # visibility verdict times the whole height, 44px at every interior position from 341 up: over a bar showing 1 to 43
        # pixels the shell reserved 44, a dark band of up to 43 px between the composer and the keyboard, the artifact this
        # change exists to close. The author's pass 6 (2026-09-20): the strip is the overlap of two INTERVALS, the bar's box and the band
        # the shell published, and the expectation is derived from the geometry each record carries (the box read back from
        # the stub, the band from the published variables), never from a formula of the test's own: the author's pass 4 expectation
        # was the one-edge formula itself (offsetTop - 340 clamped), so it agreed with the shell in every state it swept and
        # could not see that a band whose top sat below the bar's top reserved pixels above the band (the whole bar over a
        # bar with no pixel inside it; more than a short band holds). The sweep must cover every state where a variable
        # changes which operand min or max takes, both edges of each interval, or the derivation proves nothing.
        sweep = self.out["sweep"]
        self.assertGreaterEqual(len(sweep), 20, "the sweep: %r" % ([r["label"] for r in sweep],))
        px = lambda v: int(v[:-2])
        band = {r["label"]: (px(r["appTop"]), px(r["appTop"]) + px(r["appH"])) for r in sweep}
        bar = {r["label"]: (r["bar"]["top"], r["bar"]["bottom"]) for r in sweep}
        heights = {b - t for t, b in bar.values()}
        self.assertEqual(len(heights), 1, "one bar height across the sweep: %r" % (heights,))
        bar_h = heights.pop()
        expected = {k: "%dpx" % max(0, min(bar[k][1], band[k][1]) - max(bar[k][0], band[k][0])) for k in band}
        self.assertEqual({r["label"]: r["barH"] for r in sweep}, expected, "the strip is the part of the bar's box inside the band")
        # the states the sweep must reach, each derived from the geometry and failing on an empty sweep
        interior = [k for k, v in expected.items() if 0 < px(v) < bar_h]
        self.assertGreaterEqual(len(interior), 6, "interior positions, the strip between 0 and the bar's height: %r" % (expected,))
        top_below = [k for k in band if band[k][0] > bar[k][0]]
        self.assertGreaterEqual(len(top_below), 6, "the band's top below the bar's top, the states the one-edge form over-counted: %r" % (top_below,))
        self.assertTrue([k for k in top_below if px(expected[k]) == 0] and [k for k in top_below if 0 < px(expected[k]) < bar_h],
                        "with the band's top below the bar's top: a bar wholly above the band and a bar straddling its top: %r" % ({k: expected[k] for k in top_below},))
        self.assertTrue([k for k in band if bar[k][1] <= band[k][0]], "a bar wholly above the band (its bottom at or above the band's top)")
        self.assertTrue([k for k in band if bar[k][0] >= band[k][1]], "a bar wholly below the band (its top at or below the band's bottom)")
        self.assertTrue([k for k in band if band[k][1] - band[k][0] < bar_h], "a band shorter than the bar")
        for edge, hit in (("band top = bar top", lambda k: band[k][0] == bar[k][0]), ("band top = bar bottom", lambda k: band[k][0] == bar[k][1]),
                          ("band bottom = bar top", lambda k: band[k][1] == bar[k][0]), ("band bottom = bar bottom", lambda k: band[k][1] == bar[k][1])):
            self.assertTrue([k for k in band if hit(k)], "the sweep reaches the edge " + edge)
        # the author's pass 8 (2026-09-20): the fifth outcome of the formula, the band wholly INSIDE the bar (min takes the band's bottom and max
        # its top), was reached by one state and guarded by proxy only: the length guard above accepts a short band disjoint from
        # the bar. Beside it, the three outcomes the ties and the C states had satisfied on their behalf: the clamp firing (a
        # strictly negative difference, the bar wholly above or below the band with a gap), the bar straddling the band's BOTTOM
        # edge (the author's pass 4 case), and the bar strictly inside the band. Each derived from the geometry, each failing on an empty
        # sweep, each red once by dropping its states.
        self.assertTrue([k for k in band if bar[k][0] < band[k][0] and band[k][1] < bar[k][1]],
                        "a band wholly inside the bar: min takes the band's bottom and max its top")
        self.assertTrue([k for k in band if bar[k][1] < band[k][0]], "the clamp fires: a bar wholly above the band with a gap")
        self.assertTrue([k for k in band if bar[k][0] > band[k][1]], "the clamp fires: a bar wholly below the band with a gap")
        self.assertTrue([k for k in band if band[k][0] < bar[k][0] < band[k][1] < bar[k][1]], "the bar straddles the band's bottom edge")
        self.assertTrue([k for k in band if band[k][0] < bar[k][0] and bar[k][1] < band[k][1]], "the bar strictly inside the band")
        stale = [r for r in sweep if r["vvHeight"] == 0]
        self.assertEqual(len(stale), 1, "the stale band after a refused height report following a rotation is one state")
        self.assertEqual((band[stale[0]["label"]], stale[0]["innerHeight"]), ((384, 844), 390), "the band last published stands while the layout viewport changed")
        # the band the shell published at each position: the pan and the height it was measured with (the stale state keeps the last)
        self.assertEqual({r["label"]: (r["appTop"], r["appH"]) for r in sweep if r["vvHeight"]},
                         {r["label"]: ("%dpx" % r["ot"], "%dpx" % r["vvHeight"]) for r in sweep if r["vvHeight"]})

    def test_the_deep_pan_is_the_control_on_which_both_forms_agree_and_the_sweep_discriminates_elsewhere(self):
        # the author's pass 8 (2026-09-20): the deep pan (384) had been called the control in a comment and in the body, and no test computed
        # the one-edge form or asserted agreement; every guard stayed green without it. The one-edge form the author's pass 6 replaced,
        # clamp(bandBottom - barTop, 0, barHeight), is computed here beside the two-interval form: the two agree exactly where the
        # band's top is at or above the bar's top and differ everywhere else, so the sweep's discriminating half is exactly the
        # top_below states. The recorded strip equals BOTH forms on every agreeing state (deep384 among them, the control) and
        # differs from the one-edge form on every discriminating state, so the shell computes the two-interval form and the sweep
        # can tell (a shell writing the one-edge form reds this by name, not only the derived expectation above).
        sweep = self.out["sweep"]
        px = lambda v: int(v[:-2])
        band = {r["label"]: (px(r["appTop"]), px(r["appTop"]) + px(r["appH"])) for r in sweep}
        bar = {r["label"]: (r["bar"]["top"], r["bar"]["bottom"]) for r in sweep}
        strip = {r["label"]: px(r["barH"]) for r in sweep}
        bar_h = {b - t for t, b in bar.values()}.pop()
        two_edge = {k: max(0, min(bar[k][1], band[k][1]) - max(bar[k][0], band[k][0])) for k in band}
        one_edge = {k: max(0, min(bar_h, band[k][1] - bar[k][0])) for k in band}
        top_below = [k for k in band if band[k][0] > bar[k][0]]
        agree = [k for k in band if k not in top_below]
        self.assertTrue(agree and top_below, "both halves of the sweep: %r / %r" % (agree, top_below))
        self.assertIn("deep384", agree, "the deep pan is an agreeing state: %r" % (agree,))
        self.assertEqual({k: two_edge[k] for k in agree}, {k: one_edge[k] for k in agree}, "the two forms agree where the band's top is not below the bar's top")
        self.assertEqual({k: strip[k] for k in agree}, {k: one_edge[k] for k in agree}, "the recorded strip equals both forms on the agreeing states: the control")
        self.assertEqual([k for k in top_below if one_edge[k] == two_edge[k]], [], "the two forms differ on every state whose band top is below the bar's top")
        self.assertEqual([k for k in top_below if strip[k] == one_edge[k]], [], "the shell's strip is never the one-edge form on a discriminating state")
        self.assertEqual({k: strip[k] for k in top_below}, {k: two_edge[k] for k in top_below}, "and is the two-interval form there")

    def test_a_pinch_over_a_deep_pan_keeps_the_strip_the_published_band_gives(self):
        # the author's pass 4 (2026-09-20): the bar wholly inside the band under a deep pan (384: the band 384..844), then a pinch (scale 2,
        # vv.height 230). The shell publishes the same band (the pan holds, --app-h is 230 * 2), so the bar is still inside it
        # and the strip stands. The author's pass 3 reading handed a pinch back to upstream's height difference (844 - 460 > 120: a
        # keyboard), so crossing the pinch cut (then the literal 1.01) flipped the strip from 44px to 0 and the bar painted over the composer's bottom
        # while the zoom held. kbDownZoomed (the clamp test above) is unchanged by this: with the keyboard gone under the zoom
        # the published band is the whole layout viewport and the bar is inside it there too.
        self.assertEqual(self.out["barInTheBandZoomed"], {"appTop": "384px", "appH": "460px", "barH": "44px"}, "the strip under the zoom")

    def test_a_fine_pointer_writes_no_pan_whatever_the_visual_viewport_says(self):
        # the author's pass 2 (2026-09-19): the writer is gated on the pointer and the fixed body on the layout query, two populations. A
        # fine-pointer window at or under 820 px takes the fixed body and gets the 0px this branch writes (from a panned state,
        # so a held or stale value would show), with the height read from the layout viewport (documentElement.clientHeight, innerHeight
        # only where the document element has none; the author's pass 9, 2026-09-20); the served populations leg drives the
        # real query at 800 px. The base tree's only pin on this branch was its source text.
        # the author's pass 6 (2026-09-20): the strip too. The band a fine pointer publishes is 0 to the layout viewport, so the bar is wholly
        # inside it and the strip is its whole height; upstream's pointer-ungated kbOpen read the short visual viewport as a
        # keyboard and collapsed the strip over the composer (0px at the base tree), a behaviour change disclosed here
        self.assertEqual(self.out["finePointer"], {"appTop": "0px", "appH": "844px", "barH": "44px"})
        self.assertEqual(self.out["finePointerBack"], {"appTop": "0px", "appH": "844px", "barH": "44px"})

    def test_the_0px_road_clears_the_hold_only_where_no_pan_stands(self):
        # the author's pass 6 (2026-09-20). The author's pass 4 had the 0px road write the hold on every fine run (a pointer that turns fine and coarse
        # again under a zoom then published the 0 the fine window laid out), and that reopened this change's own band: with
        # the keyboard up and its pan standing the pinch road published 0px under a keyboard-sized --app-h. The road now clears
        # the hold only in a true no-pan state, one the measured road would store as 0 (no visual viewport, or one under the
        # cut, taken at the layout viewport L on both roads since the author's pass 9, 2026-09-20, whose offsetTop rounds to no positive
        # pixel); with a pan standing, or under a standing zoom, the hold stands for the keyboard it
        # was measured with. Every writing road writes the value it publishes (the measured road before the clamp at use it applies
        # under a pinch); the hold road writes nothing into the hold. The
        # author's pass 8 (2026-09-20): the no-pan test reads the value the measured road stores under the cut, one helper (panPx)
        # for both roads, so a sub-pixel offsetTop is the same answer on both: 0.4 is no pan (cleared here, 0px stored there) and
        # 0.5 a pan (the hold stands here, 1px stored there); the road had read the raw offsetTop, so 0.4 kept the hold the measured road
        # would have zeroed.
        self.assertEqual(self.out["fineFromPan"], "0px", "the fine pointer published 0px from the pan")
        self.assertEqual(self.out["coarseAgainZoomed"], {"appTop": "83px", "appH": "460px"}, "the hold stands across a flip with the keyboard's pan standing")
        self.assertEqual(self.out["coarseAgainBack"], {"appTop": "0px", "appH": "844px", "barH": "44px"})
        flips = self.out["flips"]
        self.assertEqual({k: v["fine"] for k, v in flips.items()}, {k: {"appTop": "0px", "appH": "844px"} for k in flips}, "the fine pointer publishes 0px and the layout viewport's height in every state")
        self.assertEqual({k: v["coarseAgainZoomed"] for k, v in flips.items()},
                         {"noVV": {"appTop": "0px", "appH": "460px"}, "atRest": {"appTop": "0px", "appH": "460px"}, "scaleUnderCut": {"appTop": "0px", "appH": "460px"},
                          "scaleOverCut": {"appTop": "83px", "appH": "460px"}, "scaleAtCut": {"appTop": "83px", "appH": "460px"},
                          "scaleAboveCut": {"appTop": "83px", "appH": "460px"}, "onePixelPan": {"appTop": "83px", "appH": "460px"},
                          "subPixelPan": {"appTop": "0px", "appH": "460px"}, "halfPixelPan": {"appTop": "83px", "appH": "460px"},
                          "zoomedTop": {"appTop": "83px", "appH": "460px"}, "zoomPan": {"appTop": "83px", "appH": "460px"}},
                         "cleared where no pan stands and the viewport is unzoomed; kept under a standing pan or zoom")
        self.assertEqual((self.out["subPixelMeasured"], self.out["halfPixelMeasured"]), ("0px", "1px"),
                         "the measured road stores the same reading: 0.4 rounds to no pixel, 0.5 up to one")

    def test_the_pinch_cut_is_the_scale_at_which_a_zooms_own_pan_can_round_to_a_pixel(self):
        # the author's pass 8 (2026-09-20): the cut between an unzoomed report and a pinch had been the literal 1.01, undriven inside (1, 1.01)
        # and derived nowhere (its origin commit said only "above 1"). It is derived from the measured road's own rounding: a zoom
        # at scale s pans by at most L(1 - 1/s) with no keyboard behind it, L the layout viewport the visual viewport's top ranges
        # over, and the measured road stores round(offsetTop), so the cut is s = L/(L - 0.5), the scale at which the largest zoom
        # pan reaches the half pixel that rounds up (1.00059 at L 844). The author's pass 9 (2026-09-20, the maintainer's round 5 ruling): both
        # roads take the cut at L (the cells had taken it at the coarse road's h of 460, the band's height with the keyboard up, a
        # height no zoom pans over), and at or over the cut the measured road no longer stands down: it publishes the measured
        # pixels less the zoom's share in pixels (the author's pass 8 held the hold there, which with no hold standing was the band). Cells on
        # both sides on both roads: under the cut the zoom's share is no pixel and the road stores the pan it reads (90 from 90.4 at
        # 1.0005); at or over it the share is one pixel and the road publishes 97 from 97.6 (not the hold, 90; not the raw 98); the
        # 0px road's flips clear under the cut (1.0005 at 844) and keep the hold over it (1.0007). The shares are derived here from
        # the driven scales, so the pixel the cell subtracts is the cell's own arithmetic. The coarse road's cut at L rather than at
        # its own h, and the hold surviving a report between the two, is the next test's cell (the maintainer's round 6 ruling,
        # extra6-1: test_a_report_between_the_two_cuts_is_a_pinch_at_the_layout_viewport_and_the_hold_survives_it).
        below, above = self.out["cutBelow"], self.out["cutAbove"]
        self.assertEqual((round(below["zoomShare"]), round(above["zoomShare"])), (0, 1), "the zoom's share in pixels on each side of the cut: %r %r" % (below, above))
        self.assertEqual({k: below[k] for k in ("appTop", "appH")}, {"appTop": "90px", "appH": "460px"}, "under the cut the measured road stores its reading")
        self.assertEqual({k: above[k] for k in ("appTop", "appH")}, {"appTop": "%dpx" % (98 - round(above["zoomShare"])), "appH": "460px"},
                         "at or over the cut the road publishes the reading less the zoom's pixel: not the hold (90), not the raw reading (98)")
        flips = self.out["flips"]
        self.assertEqual((flips["scaleUnderCut"]["coarseAgainZoomed"]["appTop"], flips["scaleAtCut"]["coarseAgainZoomed"]["appTop"], flips["scaleOverCut"]["coarseAgainZoomed"]["appTop"]),
                         ("0px", "83px", "83px"), "the 0px road clears under the cut and keeps the hold at it and over it (the fixer pass: the cut is a pinch)")
        # the fixer pass: the helper's third outcome, no layout height (h 0), where the cut is undefined and the report counts as a pinch:
        # the fine run writes 0px and skips --app-h, and the hold stands (the item-1 kernel cleared it here; nothing had driven the state)
        h0 = self.out["h0Fine"]
        self.assertEqual((h0["innerHeight"], h0["clientHeight"]), (0, 0), "the state driven is h 0 on both reads: %r" % (h0,))
        self.assertEqual({k: h0[k] for k in ("appTop", "appH")}, {"appTop": "0px", "appH": "460px"}, "0px written, the height write skipped at h 0")
        self.assertEqual(self.out["h0CoarseAgainZoomed"], {"appTop": "83px", "appH": "460px"}, "the hold stands across a fine run with no layout height")

    def test_a_report_between_the_two_cuts_is_a_pinch_at_the_layout_viewport_and_the_hold_survives_it(self):
        # extra6-1 (the maintainer's round 6 ruling, 2026-09-29): guards the ruled cut at the layout viewport L on the coarse road
        # (the author's pass 9: it had been taken at the road's own h, the band's height with the keyboard up) and the hold
        # surviving a report between the two cuts. Before round 6's fixes only a source-spelling pin in test_shell_viewport_fit read
        # the cut, and a cut at h left every executed cell green. Since those fixes the continuous-pinch cells of
        # test_a_pinch_reading_never_overwrites_a_standing_hold red a cut at h too (the reading less the share, 82, written into
        # the hold at 1.0007, where the hold is 83), and this cell is the ruled pin beside them. The first step publishes 0 under
        # either cut (the reading, 0.4, rounds to no pan: extra10-1's reading, so it cannot tell a cut at h apart); the pinch after
        # it is the pin: the hold, 83, where a cut at h has written the reading's 0 into it and publishes 0.
        c = self.out["cutBetween"]
        L, h, s = 844, 460, 1.0008
        self.assertTrue(L / (L - 0.5) <= s < h / (h - 0.5), "the cell's premise: the scale sits at or over the cut at L and under the cut at h")
        self.assertEqual(round(459.6 * s), h, "the cell's premise: the same keyboard, the band's unzoomed height still %d" % h)
        self.assertEqual(c["hold"], "83px", "the hold, measured at scale 1: %r" % (c,))
        self.assertEqual(c["between"], {"appTop": "0px", "appH": "460px"}, "between the cuts: a pinch at L, the reading no pan, 0 published and nothing written: %r" % (c,))
        self.assertEqual(c["pinchAfter"], {"appTop": "83px", "appH": "460px"}, "the pinch after it publishes the hold: the cut at L left it standing (a cut at h writes 0 into it): %r" % (c,))

    def test_a_keyboard_raised_under_a_light_zoom_with_no_hold_publishes_its_pan(self):
        # the author's pass 9 (2026-09-20), the maintainer's round 5 ruling: the author's pass 8's derived cut (1.0006 at 844) had every scale between it and
        # the literal 1.01 it replaced fall to the hold road, and with no hold standing (the state after any rest at scale 1) the hold
        # road publishes 0px: a keyboard raised while a light zoom held left the band under the composer bare, the defect D1 exists to
        # close. The measured road publishes the pan a pure zoom cannot explain, the measured pixels less the zoom's share L(1 - 1/s)
        # in pixels (kbPx in kernel.py, derived beside it): 81px here (84 less 3), never 0, and the error against the keyboard's own
        # pan is bounded by the share plus the two roundings (a pixel below, a pixel above; the fixer pass: it had read one-sided and at
        # most the share, and the two roundings deny both, the cells below). The share is derived from the driven scale, so the bound
        # the cell checks is the cell's own arithmetic, not a figure copied from the kernel.
        r = self.out["kbUpLightZoomNoHold"]
        px = lambda v: int(v[:-2])
        self.assertEqual(self.out["restBeforeLightZoom"], "0px", "the hold is 0: the measured road stored 0 at rest")
        share = round(r["zoomShare"])
        self.assertTrue(0 < share <= 8, "a light zoom's share, between a pixel and the 8 px of the old 1.01 literal: %r" % (r,))
        self.assertEqual({k: r[k] for k in ("appTop", "appH")}, {"appTop": "%dpx" % (84 - share), "appH": "460px"},
                         "the keyboard's pan less the zoom's share, not the hold (0): %r" % (r,))
        # the keyboard's own pan is the reading (83.7) less whatever part the zoom took, in [83.7 - share, 83.7]; the derived bound puts
        # the published integer within the share plus a pixel below it and a pixel above it (two roundings; the fixer pass)
        lo, hi = 83.7 - r["zoomShare"], 83.7
        self.assertTrue(lo - r["zoomShare"] - 1 <= px(r["appTop"]) <= hi + 1, "within the share plus a pixel of the keyboard's own pan: %r" % (r,))
        # the two states that must not regress with it
        self.assertEqual(self.out["zoomDeepestNoHold"], {"appTop": "0px", "appH": "844px"}, "a real pinch at the deepest pan a pure zoom can reach: the share is tight, nothing is published")
        self.assertEqual(self.out["kbUnderZoomNoHold"], {"appTop": "0px", "appH": "460px"}, "a keyboard under a real pinch with no hold: its pan is inside the zoom's share, the hold (0) is published")
        self.assertEqual(self.out["kbUnderZoomDragged"], {"appTop": "78px", "appH": "460px"}, "dragged below the zoom's share under the pinch: the excess is a keyboard's and is published")
        self.assertEqual(self.out["kbUnderZoomDraggedBack"], {"appTop": "78px", "appH": "460px"}, "the excess became the hold")

    def test_the_published_pan_lies_within_the_share_plus_a_pixel_below_and_a_pixel_above_the_keyboards_own(self):
        # the fixer pass of the author's pass 9 (unruled): the kernel's, the harness's and the body's statement of the bound had read
        # "one-sided and at most the share", and the formula rounds twice (panPx, zoomPx), each at most half a pixel off, so the
        # published integer lies within the share plus a pixel BELOW the keyboard's own pan and a pixel ABOVE it. Both sides driven:
        # a reading of 86.5 at a share of 2.49 publishes 85 (87 less 2), above a keyboard pan of 84.01 (the zoom panned its whole
        # share) by 0.99; a reading of 84 at a share of 16.55 publishes 67 (84 less 17), below a keyboard pan of 84 (the zoom panned
        # nothing) by 17, more than the share. A single rounding of the unrounded difference would publish 84 in the first cell and
        # break the reading the 0px road shares below the cut (kbPx equals panPx there only with the share rounded on its own)
        up, down = self.out["roundedUp"], self.out["roundedDown"]
        px = lambda v: int(v[:-2])
        self.assertEqual((round(up["zoomShare"]), round(down["zoomShare"])), (2, 17), "the shares in pixels, from the driven scales: %r %r" % (up, down))
        self.assertEqual({k: up[k] for k in ("appTop", "appH")}, {"appTop": "85px", "appH": "460px"}, "87 less 2: %r" % (up,))
        kb_low = up["offsetTop"] - up["zoomShare"]   # the keyboard's own pan when the zoom panned its whole share
        self.assertGreater(px(up["appTop"]), kb_low, "the published pan exceeds the keyboard's own: the error is not one-sided: %r" % (up,))
        self.assertLessEqual(px(up["appTop"]) - kb_low, 1, "and by at most a pixel: %r" % (up,))
        self.assertEqual({k: down[k] for k in ("appTop", "appH")}, {"appTop": "67px", "appH": "460px"}, "84 less 17: %r" % (down,))
        short = down["offsetTop"] - px(down["appTop"])   # below the keyboard's own pan when the zoom panned nothing
        self.assertGreater(short, down["zoomShare"], "the published pan falls short of the keyboard's own by more than the share: %r" % (down,))
        self.assertLessEqual(short, down["zoomShare"] + 1, "and by at most the share plus a pixel: %r" % (down,))

    def test_a_scale_below_one_has_no_share_and_a_flush_report_is_inside_to_the_pixel(self):
        # the fixer pass of the author's pass 9 (unruled), two cells on the derivation's premises. (b) Its domain is a scale of 1 or
        # more; below 1 the visual viewport is the taller and a pure zoom-out pans nothing downward, so the share is 0: the head kernel
        # returned the negative L(1 - 1/s) and published the reading PLUS it, 94px at scale 0.9 with no keyboard, stored as the hold.
        # Nothing is published, the hold stays 0, and a keyboard's pan under a zoom-out is published whole. (c) The premise test
        # (inside) compares the report's bottom edge to the pixel: float32 values flush at the layout viewport's bottom sum to L plus
        # an ulp in doubles, which an exact test read as outside, so a keyboard flush at the bottom under a real pinch fell to the hold
        # road and published 0 where the measured road publishes 277 (512 less the share's 235)
        self.assertEqual(self.out["zoomOutNoKb"], {"appTop": "0px", "appH": "844px"}, "a zoom-out with no keyboard publishes no pan (the head: 94px)")
        self.assertEqual(self.out["zoomOutCentred"], {"appTop": "0px", "appH": "844px"}, "the centred report (a negative offsetTop) the same")
        self.assertEqual(self.out["zoomOutHold"], "0px", "the hold stayed 0 through the zoom-out cells")
        self.assertEqual(self.out["zoomOutKb"], {"appTop": "84px", "appH": "460px"}, "a keyboard's pan under a zoom-out is published whole: the share is 0")
        f = self.out["flushBottomFloat32"]
        self.assertTrue(0 < f["sumMinusL"] < 0.5, "the premise of the cell: the float32 report's bottom edge sums past L by an ulp, under the half pixel: %r" % (f,))
        self.assertEqual({k: f[k] for k in ("appTop", "appH")}, {"appTop": "%dpx" % (round(f["offsetTop"]) - round(f["zoomShare"])), "appH": "460px"},
                         "the reading less the share, 277, not the hold (0): the report is inside to the pixel: %r" % (f,))

    def test_the_clamp_reads_the_layout_viewport_in_both_engine_models_and_binds_only_below_zero(self):
        # the author's pass 7 (2026-09-20). The clamp had read window.innerHeight as the layout viewport's height, which holds in Chromium
        # and not in WebKit under the engine model kernel.py's fit() comment states with its evidence status (the one home; this
        # comment points there and restates nothing, the fixer pass of the author's pass 8): there every zoomed run had
        # innerHeight - h below 0 and the pinch road published 0px whatever the hold (the band under the composer, back for as
        # long as the zoom held), while every step above kept innerHeight at 844 through the pinch and could not see it. The clamp
        # reads document.documentElement.clientHeight, the layout viewport in both models. The records carry both readings, so
        # the stub's model (innerHeight parted from clientHeight) and the sign of the difference are derived, not assumed.
        px = lambda v: int(v[:-2])
        wp, wd, rot, back = (self.out[k] for k in ("webkitPinchPanned", "webkitKbDownZoomed", "rotatedUnderZoom", "webkitBack"))
        self.assertLess(wp["innerHeight"], wp["clientHeight"], "the WebKit model: innerHeight shrunk to the visual viewport under the pinch: %r" % (wp,))
        self.assertEqual({k: wp[k] for k in ("appTop", "appH", "barH")}, {"appTop": "83px", "appH": "460px", "barH": "0px"},
                         "the hold is published under a WebKit pinch (innerHeight 230 - 460 would have bound at 0)")
        self.assertEqual({k: wd[k] for k in ("appTop", "appH", "barH")}, {"appTop": "0px", "appH": "844px", "barH": "44px"}, "the keyboard gone under the zoom: the clamp binds at zero slack")
        self.assertEqual({k: rot[k] for k in ("appTop", "appH", "barH")}, {"appTop": "0px", "appH": "844px", "barH": "44px"},
                         "a rotation under the zoom with a stale visual-viewport report: the difference is negative and the max binds at 0, no negative pan")
        # the close of the author's pass 9: the stale report's bottom edge against the layout height, the overshoot inside() refuses, is
        # the figure the kernel's kbPx comment names (232: offsetTop 200 plus height 422 against 390; it had said 654, the coarse road's
        # h of 844 substituted for the visual viewport's height, a number inside() never reads)
        self.assertEqual((rot["vvBottom"], rot["clientHeight"], rot["vvBottom"] - rot["clientHeight"]), (622, 390, 232),
                         "the stale report is outside the layout viewport by inside()'s own operands: %r" % (rot,))
        signs = {k: (r["clientHeight"] - px(r["appH"]) > 0) - (r["clientHeight"] - px(r["appH"]) < 0) for k, r in (("slack", wp), ("zero", wd), ("negative", rot))}
        self.assertEqual(signs, {"slack": 1, "zero": 0, "negative": -1}, "the clamp's difference driven at both signs and zero: %r" % (signs,))
        self.assertEqual({k: back[k] for k in ("appTop", "appH", "barH")}, {"appTop": "0px", "appH": "844px", "barH": "44px"})
        self.assertEqual(back["innerHeight"], back["clientHeight"], "the models rejoin at scale 1")

    def test_the_fine_pointer_road_reads_the_layout_viewport_in_both_engine_models(self):
        # the author's pass 8 (2026-09-20): the sibling read. The fine-pointer road, and the road with no visualViewport, had taken innerHeight
        # as the layout height, licensed by upstream's "pinch-immune in every browser" premise, which the fork's engine-model
        # premise contradicts (both live in kernel.py's fit() comment, the one home, with their evidence status); the road reads
        # document.documentElement.clientHeight too, a no-op wherever innerHeight was right. Driven here with the two parted: the
        # published band is the layout viewport and the bar inside it keeps its strip (the head kernel gave 422px and 0px on the
        # fine pointer, and a 422 px band with no visualViewport).
        fp, nv = self.out["finePointerWebKit"], self.out["noVVWebKit"]
        for r in (fp, nv):
            self.assertLess(r["innerHeight"], r["clientHeight"], "the model parted on this road: %r" % (r,))
        self.assertEqual({k: fp[k] for k in ("appTop", "appH", "barH")}, {"appTop": "0px", "appH": "844px", "barH": "44px"},
                         "a fine pointer under the WebKit model publishes the layout viewport, and the bar inside it keeps its strip")
        self.assertEqual({k: nv[k] for k in ("appTop", "appH", "barH")}, {"appTop": "0px", "appH": "844px", "barH": "44px"},
                         "no visualViewport under the WebKit model: the layout viewport, and upstream's reading reserves the bar")

    # The maintainer's round 6 ruling (2026-09-29): what the pinch road publishes from its hold. The reading's interval is derived
    # here from the report each step drove, not from the kernel: a pure zoom at scale s pans the visual viewport by at most its
    # share, L(1 - 1/s) over the layout viewport L of 844, so a keyboard's own pan lies between the reading less the share (the
    # zoom panned all of it) and the reading (the zoom panned none), both in whole pixels as the engine rounds them (half up), with
    # a pixel of slack each side for the two roundings (the bound kernel.py states beside kbPx).
    @staticmethod
    def _r6_px(v):
        return int(v[:-2])

    @staticmethod
    def _r6_interval(st):
        half_up = lambda x: int(math.floor(x + 0.5))
        share = 844 * (1 - 1 / st["scale"]) if st["scale"] > 1 else 0
        pan = half_up(st["offsetTop"])
        return max(0, pan - half_up(share)) - 1, pan + 1

    def _r6(self, fam):
        return {st["tag"]: st for st in self.out["r6"][fam]}

    def test_a_pinch_reading_never_overwrites_a_standing_hold(self):
        # ui-1: under a real pinch with a hold standing, the measured road had stored any reading past the zoom's share, so a drag
        # one pixel past it dropped a hold of 83 to 1, a continuous pinch lowered it at every step, and a keyboard raised again
        # under the zoom was laid out at the decayed value. It now writes under a pinch only where no hold is held, and the flag is
        # kept apart from the value, so a hold of 0 counts too (keyed on the value, a hold of 0 read as none and a drag past the
        # share overwrote it). A drag past the hold plus the share publishes the excess and stores nothing: the drag back and the
        # keyboard raised again find the hold (it had stored 168 from a drag to 590 and laid the re-raise out there). Every
        # cell is checked before the test fails, so a red names all of them.
        px, bad = self._r6_px, []

        def expect(fam, tag, want):
            got = px(self._r6(fam)[tag]["appTop"])
            if got != want:
                bad.append("%s %s: %d, not %d" % (fam, tag, got, want))

        for o in (423, 500, 590):
            fam = "drag%d" % o
            excess = self._r6_interval(self._r6(fam)["drag"])[0] + 1   # the reading less the share, 422 at scale 2
            for tag, want in (("kbUp", 83), ("pinch2", 83), ("drag", max(83, excess)), ("back", 83), ("kbDownZ", 0), ("reRaiseZ", 83)):
                expect(fam, tag, want)
        for fp in ("0", "0.5", "1"):
            fam = "pinch" + fp
            zoomed = [st["tag"] for st in self.out["r6"][fam] if st["tag"].startswith("s")]
            self.assertEqual(len(zoomed), 9, "the family drove its nine scales: %r" % (zoomed,))
            for tag in zoomed + ["reRaiseZ"]:
                expect(fam, tag, 83)
            expect(fam, "kbDownZ", 0)
        for s in ("1.05", "2"):
            fam = "hold0-" + s
            excess = self._r6_interval(self._r6(fam)["drag"])[0] + 1
            self.assertGreater(excess, 0, "the cell's premise: the drag passes the share, so the reading leaves an excess: %r" % (self._r6(fam)["drag"],))
            for tag, want in (("kbUp0", 0), ("pinchC", 0), ("drag", excess), ("back0", 0), ("down", 0), ("reNoPan", 0)):
                expect(fam, tag, want)
        if bad:
            self.fail("a drag, a continuous pinch or a hold of 0 under a real pinch: the hold stands, the excess is published unstored; %d cells:\n%s" % (len(bad), "\n".join(bad)))

    def test_a_keyboard_raised_again_under_a_zoom_publishes_what_the_reading_allows(self):
        # extra10-1: with a hold standing, a keyboard raised with no pan, or with a pan inside the zoom's share, had published the
        # stale hold (80 px under the light zoom of 1.003, the composer 81.5 px below the visible band's bottom; a hold of 83 at
        # scales 1.2 and 2). The hold road's keyboard-down run marks the held keyboard gone, and the next keyboard-up run bounds the
        # hold into the reading's interval and keeps that bound apart from the hold, so a later re-raise of the first field still
        # finds the hold (a bound written into the hold lost it: 0 at scale 2 where the field's own pan is 83). The share=hold
        # cells put the share one pixel under, at and over a hold of 83, where the boundary between bounding and keeping sits.
        # Every cell is checked before the test fails, so a red names all of them.
        px, bad, checked = self._r6_px, [], []

        def inside(fam, tag):
            st = self._r6(fam)[tag]
            lo, hi = self._r6_interval(st)
            checked.append((fam, tag))
            if not lo <= px(st["appTop"]) <= hi:
                bad.append("%s %s: %s, outside the reading's interval [%d, %d]" % (fam, tag, st["appTop"], lo, hi))

        def expect(fam, tag, want):
            got = px(self._r6(fam)[tag]["appTop"])
            if got != want:
                bad.append("%s %s: %d, not %d" % (fam, tag, got, want))

        for s in ("1.00059", "1.0007", "1.003", "1.008", "1.01", "1.05"):
            fam = "lz" + s
            for tag in ("A1-kbUpPan", "A3-kbUpNoPan", "A4-kbUpPanInShare", "A6-kbUpPanAgain"):
                inside(fam, tag)
            expect(fam, "A2-kbDown", 0)
            expect(fam, "A5-kbDown", 0)
        for s in ("1.003", "1.01", "1.05"):
            expect("hold83-lz" + s, "E1-kbUp", 83)
            expect("hold83-lz" + s, "E2-kbDownLZ", 0)
            inside("hold83-lz" + s, "E3-kbUpNoPanLZ")
            inside("hold83-lz" + s, "E4-kbUpPan2LZ")
            inside("hold83-direct" + s, "E3b-noPanLZ")
        for s in ("1.003", "1.01"):
            for tag in ("G1-kbUpPan", "G-dragTo0", "G-dragTo2", "G-dragTo40"):
                inside("lzdrag" + s, tag)
        expect("smallHold", "S1-kbUpZ423", 1)   # the excess stored where no hold was held
        expect("smallHold", "S2-kbDownZ", 0)
        inside("smallHold", "S3-lzKbUpPan")
        inside("smallHold", "S4-lzKbUpNoPan")
        for tag, p in (("p30-s1.05", 30), ("p83-s1.2", 83), ("p83-s2", 83), ("share82", 83), ("share83", 83), ("share84", 83)):
            fam = "reraise-" + tag
            share = 844 * (1 - 1 / self._r6(fam)["pinchC"]["scale"])
            self.assertGreaterEqual(round(share), p - 1, "the cell's premise: the zoom's share is at, just under or over the hold: %s %r" % (fam, share))
            for step, want in (("kbUp1", p), ("pinchC", p), ("down1", 0), ("down2", 0), ("down3", 0), ("reNoPan", 0), ("reSameP", p)):
                expect(fam, step, want)   # reNoPan: no pan, not the hold; reSameP: the first field again finds the hold
            inside(fam, "reInShare")
        self.assertEqual(len(checked), 49, "every step named above was checked")
        if bad:
            self.fail("a keyboard raised again under a zoom: inside the reading's interval, and the first field finds its hold; %d cells:\n%s" % (len(bad), "\n".join(bad)))

    def test_a_pan_of_a_keyboard_raised_at_this_zoom_follows_the_reading(self):
        # the maintainer's round 6 ruling (2026-09-29): the reading governs a pan of a keyboard raised at this zoom. Where a raise or
        # a re-raise wrote the value in force under the current zoom, with no change of scale between runs on the measured or hold road
        # since (a fine pointer's runs record no scale, so a change only they saw does not count), the hold road re-bounds the larger of
        # the hold and the value in force into the reading's interval; a pan of that keyboard (a keyboard up and the scale unchanged since
        # the previous run on those roads, a keyboard swapped in at the same zoom included) is such a report, and the rule makes no test
        # of a pan of its own (the same ruling, on its focused re-check: that test did no work). Keeping the value there had left the composer 44 px
        # below the visible band's bottom for a light-zoom hold of 20 dragged to the top (lzhold20), and a pan to the share after a
        # no-pan re-raise under a light zoom had opened a band under the composer (the A4 cells: 2.67 px at 1.008, 3.33 px at 1.01, 16
        # px at 1.05). The rule's value is derived here from the geometry each step drove: the hold (in these cells the larger of the
        # two, the value in force being the hold itself or a re-raise bound of 0) bounded into the reading's interval (the reading
        # less the share, up to the reading); re-bounded from the value in force alone, the A4 and E4 cells publish the re-raise
        # bound's 0. Each keyboard event that arms the rule has a cell a mutant turns red: the raise (lzhold20's dragTo0 stays at 20
        # when a raise's write is no keyboard event) and the re-raise (the E4 cells, a hold from scale 1 re-raised under the zoom:
        # they keep the re-raise bound, 0, when the re-raise is no keyboard event). Every cell is checked before the test fails.
        px, bad = self._r6_px, []

        def rule(st, hold):
            lo, hi = self._r6_interval(st)
            return max(lo + 1, min(hold, hi - 1))

        def band(st):   # how far the composer's bottom sits above the visible band's bottom: the band under the composer
            return (st["offsetTop"] + st["height"]) - (px(st["appTop"]) + px(st["appH"]))

        def expect(fam, tag, hold):
            st = self._r6(fam)[tag]
            want = rule(st, hold)
            if px(st["appTop"]) != want:
                bad.append("%s %s: %s, not %dpx (the hold %d bounded into the reading's interval)" % (fam, tag, st["appTop"], want, hold))
            if round(band(st), 2) > 1:
                bad.append("%s %s: a band of %.2f px under the composer" % (fam, tag, band(st)))
            return want

        for s in ("1.00059", "1.0007", "1.003", "1.008", "1.01", "1.05"):
            t = self._r6("lz" + s)
            expect("lz" + s, "A4-kbUpPanInShare", px(t["A1-kbUpPan"]["appTop"]))   # the raise stored the reading less the share
        for s in ("1.003", "1.01", "1.05"):
            st = self._r6("hold83-lz" + s)["E4-kbUpPan2LZ"]
            self.assertEqual(rule(st, 83), 2, "the cell's premise: the pan of 2 lies inside the reading's interval: %r" % (st,))
            expect("hold83-lz" + s, "E4-kbUpPan2LZ", 83)
        t = self._r6("lzhold20")
        self.assertEqual(px(t["kbUpLZ"]["appTop"]), 20, "the keyboard raised at the light zoom with no hold stores the reading less the share: %r" % (t,))
        self.assertEqual(self._r6_interval(t["dragTo0"]), (-1, 1), "the cell's premise: the drag reaches the top, where the reading allows no pan")
        expect("lzhold20", "dragTo0", 20)
        if bad:
            self.fail("a pan of a keyboard raised at this zoom: the hold bounded into the reading's interval, no band; %d cells:\n%s" % (len(bad), "\n".join(bad)))

    def test_a_pan_after_a_zoom_alone_or_over_a_drags_write_keeps_the_value_where_the_share_reaches_it(self):
        # a GUARD of the stance (the maintainer's round 6 ruling, 2026-09-29: the stance governs a zoom alone and what follows it).
        # Bounding every pan under a pinch by the reading re-lays the shell under a real pinch dragged above the value (40 and 0 here,
        # where the stance keeps 83; 10 where no hold was held and the drag's excess, 78, became the value), and every ungated form of
        # the pan rule did. Where the zoom's share reaches the value the hold road keeps it through a pan unless a raise or a re-raise
        # wrote it under the current zoom with no change of scale between runs on the measured or hold road since (a fine pointer's runs
        # record no scale). Each gate has its cell, the rule's value (derived from the
        # geometry) differing from the stance's in each: stance (a hold raised at scale 1 and pinched to 2, a zoom alone since); nohold
        # (the value a drag wrote, no keyboard event: a drag's write counted as one publishes 10 at Z4); zoomBack (a zoom alone away and
        # back to the scale the raise wrote at: without the clearing at a change of scale the drag publishes 0); swapZoom (the scale
        # changed in the same report as the band's height, so no zoom alone: the clearing at a change of scale between those runs refuses it, since the
        # maintainer's round 6 ruling, 2026-09-29, and so does the rule's test that kz is the current scale, redundant with that clearing
        # here (kz 1, the scale 2); with the clearing dropped and the test read as kz standing, the pan publishes 40). The stance's cost, stated in the fit() comment: the composer below the band's
        # bottom by the drag, 83 px where the reading allows 0.
        px = self._r6_px

        def rule(st, hold):
            lo, hi = self._r6_interval(st)
            return max(lo + 1, min(hold, hi - 1))

        t = self._r6("stance")
        self.assertEqual([px(t[k]["appTop"]) for k in ("P1-kbUp", "P2-at200", "P3-up40", "P4-at0")], [83, 83, 83, 83],
                         "a zoom alone and a pan under a real pinch keep the hold: %r" % (t,))
        self.assertEqual((rule(t["P3-up40"], 83), rule(t["P4-at0"], 83)), (40, 0), "the cells' premise: the rule would follow the pan")
        t = self._r6("nohold")
        self.assertEqual([px(t[k]["appTop"]) for k in ("Z1-kbUpZ", "Z2-drag500", "Z3-back83", "Z4-to10")], [0, 78, 78, 78],
                         "no hold under the pinch: the drag's excess is stored and kept: %r" % (t,))
        self.assertEqual(rule(t["Z4-to10"], 78), 10, "the cell's premise: the rule would follow the pan to 10")
        t = self._r6("zoomBack")
        self.assertEqual(t["zoomBackTo1.05"]["scale"], t["kbUpLZ"]["scale"], "the cell's premise: the zoom came back to the raise's own scale")
        self.assertEqual({round(t[k]["height"] * t[k]["scale"]) for k in ("kbUpLZ", "zoomAway", "zoomBackTo1.05", "dragTo0")}, {508},
                         "the cell's premise: the same keyboard throughout, so the zooms are zooms alone")
        self.assertEqual(rule(t["dragTo0"], 20), 0, "the cell's premise: the rule would follow the drag to the top")
        self.assertEqual([px(t[k]["appTop"]) for k in ("kbUpLZ", "zoomAway", "zoomBackTo1.05", "dragTo0")], [20, 20, 20, 20],
                         "a zoom alone since the raise, even one that came back to its scale: the pan keeps the value: %r" % (t,))
        t = self._r6("swapZoom")
        self.assertEqual([round(t[k]["height"] * t[k]["scale"]) for k in ("kbUp", "swapPinch2", "up40")], [508, 460, 460],
                         "the cell's premise: the band's height changed in the pinch's own report, and not in the pan's")
        self.assertEqual(rule(t["up40"], 83), 40, "the cell's premise: the rule would follow the pan to 40")
        self.assertEqual([px(t[k]["appTop"]) for k in ("kbUp", "swapPinch2", "up40")], [83, 83, 83],
                         "a scale that changed with the band's height is not the zoom the raise wrote at: the pan keeps the value: %r" % (t,))

    def test_a_zoom_alone_after_a_pan_the_rule_re_bounded_publishes_from_the_value_in_force(self):
        # DISCLOSED, and this cell is its witness (the fit() comment names it): the pan rule publishes its value and stores nothing, so
        # a zoom alone after a pan it re-bounded publishes by the stance from the value in force (here the re-raise bound, 0) and the
        # shell moves by the difference. The pan to the share at 1.05 publishes 40; a zoom alone to 1.1 about the band's centre then
        # publishes 0, a band of 5 px under the composer, and the zoom back to 1.05 at the same pan 0 again, the 16 px band the rule had
        # closed. Storing the rule's value would keep 40 through both; that is a design call not taken here, and this cell pins the
        # built behaviour so a change to it is made on purpose.
        px, t = self._r6_px, self._r6("zoomAfterPan")

        def band(st):
            return round((st["offsetTop"] + st["height"]) - (px(st["appTop"]) + px(st["appH"])), 2)

        self.assertEqual({round(t[k]["height"] * t[k]["scale"]) for k in ("A4-kbUpPanInShare", "zoomAlone1.1", "zoomBack1.05")}, {508},
                         "the cell's premise: the same keyboard up throughout, so both zooms are zooms alone")
        self.assertEqual([px(t[k]["appTop"]) for k in ("A1-kbUpPan", "A3-kbUpNoPan", "A4-kbUpPanInShare", "zoomAlone1.1", "zoomBack1.05")],
                         [43, 0, 40, 0, 0], "the rule's pan, then the zooms alone publish from the re-raise bound: %r" % (t,))
        self.assertEqual([band(t[k]) for k in ("A4-kbUpPanInShare", "zoomAlone1.1", "zoomBack1.05")], [-24.0, 5.0, 16.0],
                         "the band under the composer: none after the rule's pan, 5 px after the zoom alone, 16 px after the zoom back")

    def test_a_pan_after_a_re_raise_bound_above_the_hold_re_bounds_from_the_re_raise_bound(self):
        # the maintainer's round 6 ruling (2026-09-29): the pan rule re-bounds from the larger of the hold and the value in force,
        # capped at the reading. A hold of 83 at scale 1, the keyboard down under the zoom and raised again with the visual viewport
        # deep, so the re-raise bound (the reading less the share) is above the hold: 168 at scale 2, 214 at 1.5, 173 at 1.1. Then
        # that keyboard panned back up, a pan by the test: the rule re-bounds from the re-raise bound and publishes 168, 214 and 150
        # (the reading caps it at 1.1), and no band opens under the composer. Re-bounded from the hold alone it published 83 there,
        # and a band opened (85, 29 and 20.82 px). The rule's value is derived from the geometry each step drove.
        px = self._r6_px

        def band(st):   # how far the composer's bottom sits above the visible band's bottom: the band under the composer
            return round((st["offsetTop"] + st["height"]) - (px(st["appTop"]) + px(st["appH"])), 2)

        for s, rp in (("2", 168), ("1.5", 214), ("1.1", 173)):
            t = self._r6("reraiseDeep" + s)
            self.assertEqual({round(t[k]["height"] * t[k]["scale"]) for k in ("E3-reRaiseDeep", "P-panUp")}, {508},
                             "the cell's premise: the same keyboard raised again and panned, so the pan is a pan: %r" % (t,))
            self.assertEqual(t["E3-reRaiseDeep"]["scale"], t["P-panUp"]["scale"], "the cell's premise: no zoom between the re-raise and the pan")
            self.assertEqual([px(t[k]["appTop"]) for k in ("E1-kbUp", "E2-kbDownZ", "E3-reRaiseDeep")], [83, 0, rp],
                             "the hold, the keyboard down, then the re-raise bound above the hold: %r" % (t,))
            p = t["P-panUp"]
            lo, hi = self._r6_interval(p)
            want = max(lo + 1, min(max(83, rp), hi - 1))
            self.assertGreater(want, 83, "the cell's premise: the re-raise bound, capped at the reading, is above the hold: %r" % (p,))
            self.assertEqual(px(p["appTop"]), want, "the pan re-bounded from the larger of the hold (83) and the re-raise bound (%d): %r" % (rp, t))
            self.assertLessEqual(band(p), 1, "no band under the composer after the pan: %r" % (p,))

    def test_the_pan_rule_leaves_a_stale_report_outside_the_layout_viewport_to_the_value_in_force(self):
        # the pan rule's scope (the maintainer's round 6 ruling, 2026-09-29, on its focused re-check, which found no executed cell for
        # it): the rule reads only a report whose visual viewport lies inside the layout viewport, the premise the zoom's share rests on
        # (kernel.py, beside kbPx), so a stale report outside it (the one a rotation leaves until the visual viewport re-reports)
        # publishes the value in force, clamped at use, even where kz is the current scale. The 508 px keyboard raised at scale 2 with
        # the visual viewport at 500 writes the reading less the share, 78, and sets kz to 2; the stale report at the same scale, at 700
        # (its bottom at 868 over a layout viewport of 844), publishes 78. With the rule's arm read ahead of the inside test the stale
        # report publishes the rule's value, the reading less the share, 278.
        px = self._r6_px
        t = self._r6("staleOutside2")
        st = t["staleOutside"]
        self.assertEqual(t["raiseZ"]["scale"], st["scale"], "the cell's premise: no zoom between the raise and the stale report")
        self.assertEqual({round(t[k]["height"] * t[k]["scale"]) for k in ("raiseZ", "staleOutside")}, {336},
                         "the cell's premise: the same keyboard throughout: %r" % (t,))
        self.assertGreater(round(st["offsetTop"] + st["height"]), 844, "the cell's premise: the visual viewport ends below the layout viewport: %r" % (st,))
        lo, hi = self._r6_interval(st)
        self.assertEqual(max(lo + 1, min(78, hi - 1)), 278, "the cell's premise: the rule's value differs there, the reading less the share: %r" % (st,))
        self.assertEqual([px(t[k]["appTop"]) for k in ("raiseZ", "staleOutside")], [78, 78],
                         "the raise writes the reading less the share, and the stale report outside the layout viewport publishes it: %r" % (t,))

    def test_a_refit_at_an_unchanged_report_never_moves_app_top(self):
        # the maintainer's round 6 ruling (2026-09-29): fit() is idempotent at an unchanged report, so a refit with nothing new never
        # moves --app-top (the shell may not move without new information, and fit() runs again on ordinary events: a visual
        # viewport resize or scroll, a window resize, focus and focusout among them). Three reads, each checked before the test fails.
        # The swap cells: a keyboard of another height swapped in at the zoom of the raise that wrote the value in force is a pan on its
        # own run, so the swap publishes the pan rule's value and the refits the same (the swap's run had taken the stance, 236 at
        # scale 2 and 275 at 1.5, and the refit the rule, 40 and 83). The designed families, driven again with every report fired
        # twice (out.r6refit), publish on each second run what the first did, every family read: the corner's swapZoomBack, roundFlip and
        # downOutside cells and the clamp's clampFace cells among them, closed by the same ruling (any change of scale between runs on
        # the measured or hold road clears kz, and under a pinch the measured road clamps what it publishes at use), each with its own
        # test below. And the seeded doubled-step
        # fuzz (4000 report sequences of 12 steps, each step fired twice) moves it at no step; while the pan rule asked for the band's
        # height to be unchanged too, it moved at 29 steps of these 48000, all keyboard swaps. That generator reaches neither the
        # corner's reports nor the clamp's; the designed cells above do.
        px, idem, bad = self._r6_px, self.out["idem"], []

        def below(st):   # how far the composer's bottom sits below the visible band's bottom
            return round((px(st["appTop"]) + px(st["appH"])) - (st["offsetTop"] + st["height"]), 2)

        for fam, raise_, repeats, want, gaps in (("swapRefit2", "kb471up", ("swap508", "refit", "refit2"), [236, 40, 40, 40], [168.0, 168.0, 168.0]),
                                                 ("swapRefit1.5", "kb508up", ("swap471", "refit"), [275, 83, 83], [124.33, 124.33])):
            t = self._r6(fam)
            self.assertEqual(len({(t[k]["height"], t[k]["offsetTop"], t[k]["scale"]) for k in repeats}), 1,
                             "the cell's premise: the refits repeat the swap's own report: %r" % (t,))
            self.assertEqual(t[raise_]["scale"], t[repeats[0]]["scale"], "the cell's premise: the swap at the raise's own zoom")
            self.assertNotEqual(px(t[raise_]["appH"]), px(t[repeats[0]]["appH"]), "the cell's premise: a keyboard of another height")
            lo, hi = self._r6_interval(t[repeats[0]])
            self.assertEqual(max(lo + 1, min(px(t[raise_]["appTop"]), hi - 1)), want[1],
                             "the cell's premise: the raise's value bounded into the swapped keyboard's reading is the value asserted: %r" % (t,))
            got = [px(t[k]["appTop"]) for k in (raise_,) + repeats]
            if got != want:
                bad.append("%s: %r, not %r (the raise, then the swap's own run and the refits at the same report by the pan rule)" % (fam, got, want))
            elif [below(t[k]) for k in repeats] != gaps:
                bad.append("%s: the composer below the visible band's bottom by %r, not %r" % (fam, [below(t[k]) for k in repeats], gaps))
        self.assertEqual({fam: [st["tag"] for st in steps] for fam, steps in self.out["r6refit"].items()},
                         {fam: [st["tag"] for st in steps] for fam, steps in self.out["r6"].items()}, "the second pass drove every designed step again")
        cells = [(fam, st) for fam, steps in self.out["r6refit"].items() for st in steps]
        self.assertGreater(len(cells), 800, "the designed cells were driven")
        closed = ({road + s0 for road in ("swapZoomBack", "roundFlip", "downOutside") for s0 in ("2", "1.5")}
                  | {"clampFace1", "clampFace150", "clampFace535", "clampFaceDeep", "clampFaceS1"})
        self.assertLessEqual(closed, {fam for fam, _ in cells}, "the corner's and the clamp's families are read here too")
        bad += ["%s %s: %s, then %s on its refit" % (fam, st["tag"], st["appTop"], st["refit"]) for fam, st in cells if st["refit"] != st["appTop"]]
        self.assertEqual(idem["steps"], 48000, "the fuzz drove every step: %r" % ({k: v for k, v in idem.items() if k != "moved"},))
        for kind, floor in (("pan", 10000), ("zoom", 8000), ("keyboard", 8000), ("both", 1500), ("outside", 1000), ("flip", 2000)):
            self.assertGreater(idem["kinds"][kind], floor, "the fuzz's premise: it drove each kind of report: %r" % (idem["kinds"],))
        self.assertGreater(idem["swapsAtZoom"], 1000, "the fuzz's premise: keyboard swaps under a zoom, the reports that had moved: %r" % (idem["swapsAtZoom"],))
        if idem["movedSteps"]:
            bad.append("the doubled-step fuzz: a refit moved --app-top at %d of %d steps; the first sequences up to that step, as (coarse, "
                       "scale, keyboard, offsetTop, first run, refit):\n%s" % (idem["movedSteps"], idem["steps"], "\n".join(map(repr, idem["moved"]))))
        if bad:
            self.fail("a refit at an unchanged report moved --app-top; %d findings:\n%s" % (len(bad), "\n".join(bad)))

    def test_a_refit_after_reports_that_changed_the_zoom_and_the_bands_height_together_publishes_what_the_report_did(self):
        # the maintainer's round 6 ruling (2026-09-29): any change of scale between runs on the measured or hold road clears kz, the zoom
        # of the raise that wrote the value in force (any zoom disarms the rule; a fine pointer's runs record no scale, so a change only
        # they saw does not), so fit() stays idempotent at the report back. While only a zoom alone (the scale changed
        # with h unchanged) cleared it, kz stood through a report that changed the scale and h together, and a later such report back
        # at kz's zoom was no pan on its own run (the scale changed since the previous run) and took the stance, while its refit, the
        # same report again, was a pan at kz's zoom and took the pan rule, so a refit with nothing new moved --app-top. Three of the
        # roads to the report away, a family each: the 471 px keyboard swapped in (swapZoomBack), the same keyboard with h rounding a
        # pixel over (roundFlip), and the keyboard down with the visual viewport outside the layout viewport, a report the
        # keyboard-down run does not read, so the return is no re-raise (downOutside). The 508 px keyboard raised at 2 with the visual
        # viewport at 500 (78), one report at 1.5 by each road, then back at 2 with the 508 px keyboard at 40: 78 on that report's run
        # and on its refit, where the pan rule's 40 had been published; at 1.5 by way of 1.2, 119 on both, where the refit had given
        # 100. The refit pin above reads these families' doubled pass too. Since the pan test was dropped (the same ruling, on its
        # focused re-check), a clearing only at a zoom alone no longer moves a refit here: the report back takes the pan rule on its
        # own run too, 40 on both runs at 2 and 100 at 1.5, a zoom that did not disarm the rule, so these cells red it on the value.
        # Every road is checked before the test fails.
        px = self._r6_px
        roads = (("swapZoomBack", "zoomSwap", "zoomSwapBack", 373), ("roundFlip", "zoomRound", "zoomRoundBack", 337),
                 ("downOutside", "zoomDown", "zoomUpBack", 844))
        for road, away, back, band_away in roads:
            for s0, raised, rule in (("2", 78, 40), ("1.5", 119, 100)):
                with self.subTest(road=road, s0=s0):
                    t = self._r6(road + s0)
                    self.assertEqual([round(t[k]["height"] * t[k]["scale"]) for k in ("raiseZ", away, back)], [336, band_away, 336],
                                     "the cell's premise: h changes in both reports, so neither is a zoom alone: %r" % (t,))
                    if road == "roundFlip":
                        self.assertLess(abs(t[away]["height"] * t[away]["scale"] - 336), 1, "the cell's premise: the same keyboard, h rounding a pixel over")
                    if road == "downOutside":
                        self.assertGreater(round(t[away]["offsetTop"] + t[away]["height"]), 844, "the cell's premise: the report away lies outside the layout viewport")
                    self.assertEqual(t["raiseZ"]["scale"], t[back]["scale"], "the cell's premise: the second report comes back to the raise's zoom")
                    self.assertNotEqual(t["raiseZ"]["scale"], t[away]["scale"], "the cell's premise: the first report zooms away")
                    self.assertEqual([t["refit"][k] for k in ("height", "offsetTop", "scale")], [t[back][k] for k in ("height", "offsetTop", "scale")],
                                     "the cell's premise: the refit repeats the report back")
                    self.assertEqual([px(t[k]["appTop"]) for k in ("raiseZ", away, back)], [raised, 0 if road == "downOutside" else raised, raised],
                                     "the raise, then the two reports by the stance (the keyboard down publishes the clamp, 0): %r" % (t,))
                    lo, hi = self._r6_interval(t[back])
                    self.assertEqual(max(lo + 1, min(raised, hi - 1)), rule, "the cell's premise: the pan rule's value differs from the stance's: %r" % (t,))
                    self.assertEqual(px(t["refit"]["appTop"]), raised,
                                     "the refit at the report back publishes what its run did, the stance's %d, not the pan rule's %d: %r" % (raised, rule, t))

    def test_under_a_pinch_the_measured_road_clamps_at_use_so_its_refit_publishes_the_same(self):
        # the maintainer's round 6 ruling (2026-09-29): under a pinch the measured road clamps what it publishes at use, at L less the
        # band's height, as the hold road does, and still writes kbPx, the reading less the zoom's share, into the hold. It had
        # published kbPx unclamped, and the refit at the same report, on the hold road once the hold was written, clamps at L - h, so
        # where rounding put kbPx a pixel above L - h (the visual viewport within half a pixel of the layout viewport's bottom, and the
        # zoom's share of the band's shortfall, (L - h)(1 - 1/s), under a pixel) the refit published a pixel less: h 843
        # under a zoom of 1.00155, 2 px and then 1; h 694 under 1.00169, 151 and then 150; and the two cells the fit() comment cites for
        # the case's reach, a light zoom with a long shortfall and a deep zoom with a short one: h 309 under 1.00178 (a shortfall of 535
        # px, a share of 0.95 px), 536 and then 535 (clampFace535), and h 843 under 1.9976 (a share of 0.50 px), 2 and then 1
        # (clampFaceDeep). Both runs now publish L - h. The clamp is the
        # pinch's only, as ruled: under the cut the measured road publishes its reading unclamped, as before, and its refit takes the
        # same road, so it publishes the same (clampFaceS1, the same rounding at scale 1: the reading 84 over a shortfall of 83 on both
        # runs; a clamp there too publishes 83). The values are derived from the geometry each step drove.
        px = self._r6_px
        for fam, tag, shortfall, pinch in (("clampFace1", "lightPinch", 1, True), ("clampFace150", "lightPinch", 150, True),
                                           ("clampFace535", "lightPinch", 535, True), ("clampFaceDeep", "deepPinch", 1, True),
                                           ("clampFaceS1", "lightPinch", 83, False)):
            with self.subTest(fam=fam):
                t = self._r6(fam)
                st, rf = t[tag], t["refit"]
                h = round(st["height"] * st["scale"])
                self.assertEqual(px(t["rest"]["appTop"]), 0, "the cell's premise: from rest, where no hold is held: %r" % (t,))
                if pinch:
                    self.assertGreaterEqual(st["scale"], 844 / (844 - 0.5), "the cell's premise: a pinch, at or above the cut")
                    self.assertLess((844 - h) * (1 - 1 / st["scale"]), 1,
                                    "the cell's premise: the zoom's share of the band's shortfall, (L - h)(1 - 1/s), under a pixel: %r" % (st,))
                else:
                    self.assertEqual(st["scale"], 1, "the cell's premise: scale 1, under the cut")
                self.assertEqual(844 - h, shortfall, "the cell's premise: the band's shortfall, L - h")
                self.assertLessEqual(abs(844 - (st["offsetTop"] + st["height"])), 0.5, "the cell's premise: the visual viewport at the layout viewport's bottom")
                self.assertEqual([rf[k] for k in ("height", "offsetTop", "scale")], [st[k] for k in ("height", "offsetTop", "scale")],
                                 "the cell's premise: the refit repeats the report")
                kb = self._r6_interval(st)[0] + 1   # the reading less the zoom's share, in pixels
                self.assertEqual(kb, shortfall + 1, "the cell's premise: rounding puts kbPx a pixel above L - h: %r" % (st,))
                self.assertEqual(px(st["appH"]), h, "the cell's premise: the band published at h")
                want = 844 - h if pinch else kb
                self.assertEqual([px(st["appTop"]), px(rf["appTop"])], [want, want],
                                 ("under a pinch the measured road publishes kbPx clamped at L - h, and its refit the same: %r" if pinch else
                                  "under the cut the measured road publishes its reading unclamped, and its refit the same: %r") % (t,))

    def test_the_clamp_at_use_leaves_the_written_value_whole_for_a_later_report(self):
        # the maintainer's round 6 ruling (2026-09-29): under a pinch the measured road clamps what it publishes at use and still writes
        # kbPx, never its clamp, so nothing adjusts the hold in place (the author's pass 4). The clamp belongs to the run's own band: a
        # report whose band is not short of the layout viewport clamps at 0 (L - h 0), and rounding can leave kbPx a pixel above that.
        # Under 1.005 with no keyboard, the visual viewport 839.5 tall at 4.6, its bottom within half a pixel of the layout viewport's:
        # the reading 5 less the share's 4, kbPx 1, published as 0. The 471 px band then comes up at the same zoom with the visual
        # viewport at 4, a reading the share explains (kbPx 0), so the hold road runs and publishes from the value in force: the 1 the
        # measured road wrote, the composer 0.66 px above the visible band's bottom. Written as its clamp, the value in force is 0 and
        # the report publishes 0, a band of 1.66 px under the composer (stored as well as published, the clamp opened bands over 1 px,
        # up to 1.98, in a fuzz out of the tree, at steps where the built form leaves none; at each recorded one the built form
        # publishes 1 and the stored clamp 0). The values are derived from the geometry each step drove.
        px, t = self._r6_px, self._r6("clampThenKbUp")
        st, up = t["pinchAtBottom"], t["kbUpSameZoom"]
        h = round(st["height"] * st["scale"])

        def band(s):   # how far the composer's bottom sits above the visible band's bottom: the band under the composer
            return round((s["offsetTop"] + s["height"]) - (px(s["appTop"]) + px(s["appH"])), 2)

        self.assertEqual(px(t["rest"]["appTop"]), 0, "the cell's premise: from rest, where no hold is held: %r" % (t,))
        self.assertGreaterEqual(st["scale"], 844 / (844 - 0.5), "the cell's premise: a pinch, at or above the cut")
        self.assertEqual(844 - h, 0, "the cell's premise: no keyboard, the band not short of the layout viewport (L - h 0): %r" % (st,))
        self.assertLessEqual(abs(844 - (st["offsetTop"] + st["height"])), 0.5, "the cell's premise: the visual viewport at the layout viewport's bottom")
        kb = self._r6_interval(st)[0] + 1   # the reading less the zoom's share, in pixels
        self.assertEqual(kb, 1, "the cell's premise: rounding puts kbPx a pixel above L - h: %r" % (st,))
        self.assertEqual(px(st["appTop"]), 844 - h, "the cell's premise: the measured road publishes kbPx clamped at use, at L - h: %r" % (st,))
        self.assertEqual(up["scale"], st["scale"], "the cell's premise: the keyboard comes up at the same zoom")
        self.assertEqual(round(up["height"] * up["scale"]), 471, "the cell's premise: the 471 px band: %r" % (up,))
        self.assertEqual(self._r6_interval(up)[0] + 1, 0, "the cell's premise: a reading the zoom's share explains, kbPx 0, so the hold road runs: %r" % (up,))
        self.assertEqual(px(up["appTop"]), kb,
                         "the report after publishes the value the measured road wrote, kbPx %d, not the clamp it published, %d: %r" % (kb, 844 - h, t))
        self.assertLessEqual(band(up), 1, "no band under the composer once the keyboard is up: %r" % (up,))

    def test_a_pan_down_after_a_zoom_alone_keeps_the_value_and_opens_a_band(self):
        # DISCLOSED, the stance's third cost, and these cells are its witness (the fit() comment names them): the pan rule governs a
        # pan of a keyboard raised at the current zoom, and a zoom alone ends that, so a pan of the same keyboard down inside the new
        # zoom's share takes the stance and keeps the value, and at the share a band opens under the composer. The keyboard
        # re-raised with no pan under a light zoom (the value in force its re-raise bound, 0), a zoom alone about the band's top,
        # then the pan down to the new zoom's share: 30.55 px from 1.05 to 1.1, 19.02 from 1.05 to 1.06, 6.59 from 1.01 to 1.02 and
        # 3.33 from 1.003 to 1.01, the same with no hold and with a hold of 83 from scale 1. The rule governing a pan after a zoom
        # alone over a re-raise bound was measured and not built (the maintainer's round 6 ruling, 2026-09-29, built it only if no
        # refit moved --app-top): it closes these bands, but the zoom alone's own run takes the stance and its refit is a pan, so the
        # refit publishes the rule's value, and a refit with nothing new moved --app-top in the doubled-step fuzz. These cells pin the
        # built behaviour so a change to it is made on purpose.
        px = self._r6_px

        def band(st):   # how far the composer's bottom sits above the visible band's bottom: the band under the composer
            return round((st["offsetTop"] + st["height"]) - (px(st["appTop"]) + px(st["appH"])), 2)

        for s0, s1, gap in (("1.05", "1.1", 30.55), ("1.05", "1.06", 19.02), ("1.01", "1.02", 6.59), ("1.003", "1.01", 3.33)):
            for fam, reraise in (("zoomThenPanDown-%s-%s" % (s0, s1), "A3-kbUpNoPan"), ("zoomThenPanDown-hold83-%s-%s" % (s0, s1), "E3-kbUpNoPanLZ")):
                t = self._r6(fam)
                z, p = t["Z-zoomAlone"], t["P-panDown"]
                self.assertEqual({round(t[k]["height"] * t[k]["scale"]) for k in (reraise, "Z-zoomAlone", "P-panDown")}, {508},
                                 "the cell's premise: the same keyboard throughout, so the zoom is a zoom alone and the pan a pan: %r" % (t,))
                self.assertNotEqual(z["scale"], t[reraise]["scale"], "the cell's premise: the zoom changed the scale")
                self.assertEqual(p["scale"], z["scale"], "the cell's premise: the pan at the new zoom")
                self.assertEqual(self._r6_interval(p)[0], -1, "the cell's premise: the pan lies inside the new zoom's share: %r" % (p,))
                self.assertEqual([px(t[k]["appTop"]) for k in (reraise, "Z-zoomAlone", "P-panDown")], [0, 0, 0],
                                 "the re-raise bound, kept through the zoom alone and the pan: %r" % (t,))
                self.assertEqual(band(p), gap, "the band under the composer after the pan down: %r" % (p,))

    def test_every_stance_cell_of_the_extended_families_publishes_the_stance_value(self):
        # round 6's extended families' stance cells (the maintainer's round 6 ruling, 2026-09-29), ported into the driver so the tree
        # reads the published value of every one: the round's first checker read these cells for a hold overwrite only, and so missed
        # the one cell every ungated pan rule moved (x6 at 1.2, backHalf: 83 to 70). The stance's value is derived from the geometry
        # each step drove and the family's hold T alone: where the zoom's share in pixels reaches T, the larger of T and the reading
        # less the share; where it is below T, T bounded into the reading's interval; clamped at use to L less the band's height.
        px, bad, fams = self._r6_px, [], {}
        cells = [(fam, st) for fam, steps in self.out["r6"].items() for st in steps if "hold" in st]
        for fam, _ in cells:
            fams[fam.split("-")[0]] = fams.get(fam.split("-")[0], 0) + 1
        self.assertEqual(fams, {"x1": 88, "x2": 48, "x4": 252, "x6": 12}, "every stance cell of the four families was driven")
        for fam, st in cells:
            lo, hi = self._r6_interval(st)
            kb, pan, T = lo + 1, hi - 1, st["hold"]
            share = int(math.floor(844 * (1 - 1 / st["scale"]) + 0.5)) if st["scale"] > 1 else 0
            want = min(max(T, kb) if share >= T else max(kb, min(T, pan)), max(0, 844 - px(st["appH"])))
            if px(st["appTop"]) != want:
                bad.append("%s %s: %s, not %dpx (the hold %d, the share %d, the reading's interval [%d, %d])" % (fam, st["tag"], st["appTop"], want, T, share, kb, pan))
        if bad:
            self.fail("a stance cell under a pinch: the value the stance keeps; %d of %d cells:\n%s" % (len(bad), len(cells), "\n".join(bad)))

    def test_the_0px_road_clears_the_written_hold_flag_with_the_hold(self):
        # the maintainer's round 6 ruling (2026-09-29), the flag's clearing rule: every measured-road write sets the flag held to
        # L - h > 0, and the 0px road clears it where it clears the hold. A hold of 83, then the pointer fine with the visual
        # viewport at rest, clears both, so coarse again under a real pinch with the keyboard up no hold is held: the reports from
        # there are the nohold family's, and so are the values, the drag's excess written and published again on the drag back.
        # The source pin in test_shell_viewport_fit reads the clearing's spelling only; this cell executes it: a 0px road that clears
        # the hold and leaves the flag reads the cleared hold of 0 as a hold held, publishes the excess unwritten and 0 on the drag back.
        px = self._r6_px
        t, n = self._r6("fineClear"), self._r6("nohold")
        after = ("Z1-kbUpZ", "Z2-drag500", "Z3-back83")
        self.assertEqual([(t[k]["height"], t[k]["offsetTop"], t[k]["scale"]) for k in after],
                         [(n[k]["height"], n[k]["offsetTop"], n[k]["scale"]) for k in after],
                         "the cell's premise: after the flip the reports are the nohold family's")
        self.assertEqual((px(t["kbUp"]["appTop"]), px(t["fineRest"]["appTop"]), px(t["Z1-kbUpZ"]["appTop"])), (83, 0, 0),
                         "the hold (83), the fine pointer at rest (0px), and coarse again under the pinch the cleared hold (0, not 83): %r" % (t,))
        excess = self._r6_interval(t["Z2-drag500"])[0] + 1   # the reading less the share, 500 - 422
        self.assertGreater(excess, 0, "the cell's premise: the drag passes the share: %r" % (t["Z2-drag500"],))
        self.assertEqual([px(t[k]["appTop"]) for k in after], [0, excess, excess],
                         "the flag cleared with the hold: no hold is held, so the drag's excess is written and the drag back publishes it "
                         "(a flag left standing publishes 0 there): %r" % (t,))
        self.assertEqual([px(t[k]["appTop"]) for k in after], [px(n[k]["appTop"]) for k in after],
                         "the flip at rest leaves the no-hold state: the nohold family's values: %r %r" % (t, n))

    def test_the_0px_road_leaves_the_written_hold_flag_where_it_leaves_the_hold(self):
        # the flag's clearing rule, its other half: the 0px road clears the flag only where it clears the hold. The same hold and
        # the same three reports under the pinch as the cell above, with the pointer turned fine while the keyboard's pan stands
        # (the 0px road leaves the hold, test_the_0px_road_clears_the_hold_only_where_no_pan_stands): the hold stays held, so the
        # drag past the share writes nothing and publishes the larger of the hold and the excess, and the drag back publishes the
        # hold. The source pin in test_shell_viewport_fit reads the clearing's spelling only; a 0px road that cleared the flag on
        # every run leaves the hold unheld, and the drag writes its excess over it (the excess on the drag and on the drag back).
        px = self._r6_px
        t, c = self._r6("fineKeep"), self._r6("fineClear")
        after = ("Z1-kbUpZ", "Z2-drag500", "Z3-back83")
        self.assertEqual([(t[k]["height"], t[k]["offsetTop"], t[k]["scale"]) for k in ("kbUp",) + after],
                         [(c[k]["height"], c[k]["offsetTop"], c[k]["scale"]) for k in ("kbUp",) + after],
                         "the cell's premise: the reports before and after the flip are the cell above's; only the flip's own report differs")
        self.assertEqual((t["finePan"]["offsetTop"], t["finePan"]["scale"]), (83, 1), "the cell's premise: the flip with the keyboard's pan standing")
        excess = self._r6_interval(t["Z2-drag500"])[0] + 1   # the reading less the share, 500 - 422
        self.assertTrue(0 < excess < 83, "the cell's premise: the drag passes the share and leaves an excess under the hold: %r" % (t["Z2-drag500"],))
        self.assertEqual((px(t["kbUp"]["appTop"]), px(t["finePan"]["appTop"])), (83, 0), "the hold, then the fine pointer: %r" % (t,))
        self.assertEqual([px(t[k]["appTop"]) for k in after], [83, 83, 83],
                         "the flag left with the hold: the hold stays held, the drag publishes the larger of it and the excess, the drag back "
                         "the hold (a flag cleared on every run gives the excess on the drag and on the drag back): %r" % (t,))


# A node stand-in for the installed phone app with a REAL class list: the shell's mobile script and
# its bell script run in the shell's own order against a stub DOM whose elements keep classes,
# attributes and listeners, so the bell's `.on` (the slash rule keys on its absence) is state read
# back after each transition — a tab tap, a reveal, the kernel's notifyAll frame, the popover's own
# switches — not a pin on the source text. Same shape as the fit harness above.
_BELL_HARNESS = r"""
'use strict';
class El {
  constructor(tag, attrs) { this.tag = tag; this.attrs = Object.assign({}, attrs || {}); this.children = []; this.parentNode = null;
    this.hidden = false; this.style = {}; this.textContent = ''; this.disabled = false; this.L = {}; this.contentDocument = null;
    const cls = new Set((this.attrs['class'] || '').split(/\s+/).filter(Boolean));
    this.classList = { add: (c) => cls.add(c), remove: (c) => cls.delete(c), contains: (c) => cls.has(c),
      toggle: (c, f) => { const on = f === undefined ? !cls.has(c) : !!f; if (on) cls.add(c); else cls.delete(c); return on; } }; }
  get id() { return this.attrs.id || ''; }
  append(...k) { k.forEach((c) => { c.parentNode = this; this.children.push(c); }); return this; }
  getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }
  setAttribute(k, v) { this.attrs[k] = String(v); }
  addEventListener(k, f) { (this.L[k] = this.L[k] || []).push(f); }
  fire(k, ev) { const e = Object.assign({ target: this }, ev || {}); for (let n = this; n; n = n.parentNode) (n.L[k] || []).forEach((f) => f(e)); }
  all() { return this.children.flatMap((c) => [c, ...c.all()]); }
  matches(sel) {                                   // one compound selector: tag, #id, .class, [attr], [attr=val]
    const m = sel.match(/^([a-z]*)((?:[#.][\w-]+|\[[\w-]+(?:=[\w-]+)?\])*)$/); if (!m) throw new Error('selector ' + sel);
    if (m[1] && m[1] !== this.tag) return false;
    for (const p of m[2].match(/[#.][\w-]+|\[[^\]]+\]/g) || []) {
      if (p[0] === '#') { if (this.id !== p.slice(1)) return false; }
      else if (p[0] === '.') { if (!this.classList.contains(p.slice(1))) return false; }
      else { const [k, v] = p.slice(1, -1).split('='); if (!(k in this.attrs) || (v !== undefined && this.attrs[k] !== v)) return false; } }
    return true; }
  querySelectorAll(sel) { const parts = sel.split(',').map((s) => s.trim()); return this.all().filter((e) => parts.some((p) => e.matches(p))); }
  querySelector(sel) { return this.querySelectorAll(sel)[0] || null; }
  getBoundingClientRect() { return { top: 800, right: 380, bottom: 844, left: 340 }; }
}
// the shell's markup, reduced to the nodes the two scripts touch
const root = new El('html'), body = new El('body'); root.append(body);
['f-chat', 'f-fleet', 'f-feed', 'f-timeline'].forEach((id) => { const p = new El('iframe', { id }); p.contentWindow = { addEventListener() {} }; body.append(p); });
const railBell = new El('div', { class: 'rail-act', id: 'rail-bell' }); railBell.hidden = true;
body.append(new El('div', { class: 'rail-acts' }).append(railBell));
const bar = new El('nav', { id: 'mtabs' }); bar.offsetHeight = 44;
['chat', 'fleet', 'feed', 'timeline'].forEach((k) => bar.append(new El('button', k === 'chat' ? { 'data-pane': k, class: 'on' } : { 'data-pane': k })));
bar.append(new El('span', { class: 'mtabs-div' }));
['usage', 'net', 'restart', 'errs'].forEach((a) => bar.append(new El('button', { class: 'mact', 'data-act': a })));
const mbell = new El('button', { class: 'mact', id: 'mbell' }); mbell.hidden = true; bar.append(mbell);
bar.append(new El('button', { class: 'mact', 'data-act': 'settings' }));
body.append(bar);
const back = new El('div', { id: 'rbell-back' }); back.hidden = true;
const pop = new El('div', { id: 'rbell-pop' }), rows = {};
['all', 'dev', 'turns'].forEach((a) => { rows[a] = new El('div', { class: 'rbp-row', 'data-act': a }).append(new El('span', { class: 'rbp-sw' })); pop.append(rows[a]); });
pop.append(new El('div', { id: 'rbp-dev-sub' }), new El('button', { id: 'rbp-test', 'data-act': 'test' }), new El('div', { id: 'rbp-test-out' }));
back.append(pop); body.append(back);
// the window: a coarse pointer, a live shell socket the driver feeds frames into
const WIN = {}, WSS = [], POSTS = [];
const on = (book) => (k, f) => { (book[k] = book[k] || []).push(f); };
global.window = global;
global.innerHeight = 844; global.innerWidth = 390; global.scrollY = 0; global.scrollTo = () => {};
global.matchMedia = () => ({ matches: true });
global.requestAnimationFrame = () => 1;
global.setInterval = () => 0;   // D3 (2026-09-18): the shell socket's watchdog tick, a no-op here so node exits
global.addEventListener = on(WIN);
global.visualViewport = { height: 844, scale: 1, addEventListener() {} };
global.document = { visibilityState: 'visible', addEventListener() {}, body,
  documentElement: { scrollTop: 0, style: { setProperty() {} } },
  getElementById: (id) => root.querySelector('#' + id),
  querySelectorAll: (s) => root.querySelectorAll(s), querySelector: (s) => root.querySelector(s) };
global.localStorage = { getItem: () => null, setItem() {} };
global.location = { protocol: 'https:', host: 'TESTHOST' };
global.WebSocket = class { constructor(u) { this.url = u; WSS.push(this); } send() {} };
// the Push API: this browser holds a subscription at boot; the popover's row can drop and re-take it
let SUB = null;
const mkSub = (n) => ({ endpoint: 'https://push.example/dev-' + n, unsubscribe() { SUB = null; return Promise.resolve(true); }, toJSON() { return { endpoint: this.endpoint }; } });
SUB = mkSub(1);
const REG = { pushManager: { getSubscription: () => Promise.resolve(SUB), subscribe: () => { SUB = mkSub(2); return Promise.resolve(SUB); } } };
Object.defineProperty(global, 'navigator', { configurable: true, value:   // node 22's own navigator is a getter-only global
  { serviceWorker: { getRegistration: () => Promise.resolve(REG), register: () => Promise.resolve(REG), ready: Promise.resolve(REG) } } });
global.PushManager = function () {};
global.Notification = { permission: 'granted', requestPermission: () => Promise.resolve('granted') };
const GETS = { '/notify-all': { on: true }, '/notify-turns': { on: false }, '/push/vapid-key': { key: 'BAAA' } };
global.fetch = (path, init) => { const post = !!(init && init.method === 'POST'); if (post) POSTS.push([path, JSON.parse(init.body)]);
  const b = post ? { ok: true } : (GETS[path] || {});
  return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(b), text: () => Promise.resolve(JSON.stringify(b)) }); };
"""
_BELL_DRIVER = r"""
const settle = async () => { for (let i = 0; i < 40; i++) await new Promise((r) => setImmediate(r)); };
const sw = (k) => rows[k].querySelector('.rbp-sw').classList.contains('on');
const state = () => ({ mbell: mbell.classList.contains('on'), rail: railBell.classList.contains('on'),
  title: [mbell.getAttribute('title'), railBell.getAttribute('title')], rows: { all: sw('all'), dev: sw('dev') },
  tabs: bar.querySelectorAll('button[data-pane]').filter((b) => b.classList.contains('on')).map((b) => b.getAttribute('data-pane')) });
const ws = () => WSS[WSS.length - 1];
const frame = (m) => ws().onmessage({ data: JSON.stringify(m) });
const post = (m) => (WIN.message || []).forEach((f) => f({ data: m }));
(async () => {
  const out = {};
  (0, eval)(MOBILE_JS); (0, eval)(PUSH_JS);          // the shell's order: the tab bar's script parses first, the bell's after it
  out.revealed = { mbell: !mbell.hidden, rail: !railBell.hidden };
  await settle();
  out.boot = state();                                // master on + subscribed: lit, and no popover was opened
  bar.querySelector('button[data-pane=feed]').fire('click'); out.tabTap = state();
  post({ romp: 'reveal', pane: 'chat' });            out.revealMsg = state();
  frame({ type: 'reveal', pane: 'timeline' });       out.revealFrame = state();
  post({ romp: 'toggleFleet', to: 'fleet' });        out.listJump = state();   // the chat header's jump to the sessions list
  frame({ type: 'notifyAll', on: false }); out.masterOffFrame = state();
  frame({ type: 'notifyAll', on: true });  out.masterOnFrame = state();
  rows.dev.fire('click'); await settle(); out.devOff = state();          // the popover's This-device row: unsubscribes
  bar.querySelector('button[data-pane=chat]').fire('click'); out.devOffTabTap = state();
  rows.dev.fire('click'); await settle(); out.devOn = state();           // …and re-subscribes
  rows.all.fire('click'); await settle(); out.masterOffRow = state();    // the master row itself
  rows.all.fire('click'); await settle(); out.masterOnRow = state();
  bar.querySelector('button[data-pane=feed]').fire('click'); out.finalTabTap = state();
  out.posts = POSTS.map((p) => p[0]);
  console.log(JSON.stringify(out));
})().catch((e) => { console.error(e && e.stack || e); process.exit(1); });
"""


class MobileBellExecutes(unittest.TestCase):
    """The installed iPhone app, light theme (the user 2026-09-08): the bell popover showed all three
    switches on — Notifications, This device, the turn-finished one — while the tab bar's bell wore
    the OFF slash. The bell script paints `.on` on both bells from the master + this device's
    subscription and was right at boot; then the tab bar's switcher took it away. `show(p)` ran over
    EVERY button in #mtabs — the pane tabs, the action buttons and the bell among them — toggling
    `.on` to `data-pane===p`, which for the bell (no data-pane) is always off. So every pane switch
    (a tab tap, a notification's reveal, the chat header's jump to the sessions list) slashed a subscribed bell until the next
    paint event, while the popover's rows, painted from the same state, still said on. The switcher
    now owns only the pane tabs (`button[data-pane]`); the bell's class is the bell script's alone."""

    @classmethod
    def setUpClass(cls):
        src = "const MOBILE_JS=%s;const PUSH_JS=%s;" % (json.dumps(_mobile_js()), json.dumps(km._LANDING_PUSH_JS))
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
            f.write(_BELL_HARNESS + src + _BELL_DRIVER)
            path = f.name
        try:
            r = subprocess.run(["node", path], capture_output=True, text=True, timeout=30)
        finally:
            os.unlink(path)
        # The template as the page serves it (_mobile_js above).
        assert r.returncode == 0, "the shell scripts threw: " + r.stderr[:1200]
        cls.out = json.loads(r.stdout.strip().splitlines()[-1])

    LIT = "Notifications on — tap for options"

    def _lit(self, s, where):
        self.assertEqual((s["mbell"], s["rail"]), (True, True), where + ": both bells lit")
        self.assertEqual(s["title"], [self.LIT, self.LIT], where)

    def test_boot_lights_a_subscribed_device_without_opening_the_popover(self):
        self.assertEqual(self.out["revealed"], {"mbell": True, "rail": True}, "the Push API exists here: both bells show")
        s = self.out["boot"]
        self._lit(s, "boot")
        self.assertEqual(s["rows"], {"all": True, "dev": True})
        self.assertEqual(s["tabs"], ["chat"])

    def test_a_pane_switch_leaves_the_bell_alone(self):
        # the bug: a tab tap (and every other route into show()) stripped `.on` from the bell while
        # the popover's rows still said on — the glyph and the popover disagreed
        for where in ("tabTap", "revealMsg", "revealFrame", "listJump"):
            s = self.out[where]
            self._lit(s, where)
            self.assertEqual(s["rows"], {"all": True, "dev": True}, where)
        self.assertEqual(self.out["tabTap"]["tabs"], ["feed"], "the tap still switches the pane")
        self.assertEqual(self.out["revealMsg"]["tabs"], ["chat"])
        self.assertEqual(self.out["revealFrame"]["tabs"], ["timeline"])
        self.assertEqual(self.out["listJump"]["tabs"], ["fleet"])

    def test_the_kernels_master_frame_repaints_both_bells(self):
        off = self.out["masterOffFrame"]
        self.assertEqual((off["mbell"], off["rail"]), (False, False))
        self.assertEqual(off["title"], ["Notifications off for all devices"] * 2)
        self.assertEqual(off["rows"], {"all": False, "dev": True}, "the device row keeps its own truth")
        self._lit(self.out["masterOnFrame"], "masterOnFrame")

    def test_this_devices_switch_slashes_and_relights_both_bells_and_a_tab_tap_keeps_the_slash(self):
        off = self.out["devOff"]
        self.assertEqual((off["mbell"], off["rail"]), (False, False))
        self.assertEqual(off["title"], ["Notifications off on this device"] * 2)
        self.assertEqual(off["rows"], {"all": True, "dev": False})
        # a pane switch with the device off must not light it either: the switcher paints nothing on the bell
        tap = self.out["devOffTabTap"]
        self.assertEqual((tap["mbell"], tap["rail"], tap["tabs"]), (False, False, ["chat"]))
        self.assertEqual(tap["title"], ["Notifications off on this device"] * 2)
        self._lit(self.out["devOn"], "devOn")
        self.assertEqual(self.out["devOn"]["rows"], {"all": True, "dev": True})

    def test_the_master_row_and_a_final_tab_tap(self):
        off = self.out["masterOffRow"]
        self.assertEqual((off["mbell"], off["rail"]), (False, False))
        self.assertEqual(off["title"], ["Notifications off for all devices"] * 2)
        self._lit(self.out["masterOnRow"], "masterOnRow")
        self._lit(self.out["finalTabTap"], "finalTabTap")
        self.assertEqual(self.out["finalTabTap"]["tabs"], ["feed"])
        self.assertEqual(self.out["posts"], ["/push/unsubscribe", "/push/subscribe", "/notify-all", "/notify-all"])

    def test_the_switcher_selects_only_the_pane_tabs(self):
        js = km._LANDING_MOBILE_JS
        self.assertIn("var B=bar.querySelectorAll('button[data-pane]')", js)
        self.assertNotIn("bar.querySelectorAll('button'),", js)


# A node stand-in for the phone with the shell socket in view: the fit harness's window plus a mutable copy of the
# gear's store, a location to dial, and a WebSocket class that records what the shell sends. The driver flips the
# store between rows and reads the rows that reached the socket; diagQ is a local of the script's IIFE, so the queue
# is observed only through what the socket's open flush sends.
_SHELL_DIAG_HARNESS = r"""
let STORE = null;                                                                        // 'romp:settings' as the gear wrote it, or nothing
global.localStorage = { getItem: (k) => (k === 'romp:settings' ? STORE : null), setItem() {} };
global.location = { protocol: 'https:', host: 'TESTHOST' };
const WSS = [], SENT = [];
global.WebSocket = class { constructor(u) { this.url = u; this.readyState = 0; WSS.push(this); } send(s) { SENT.push(JSON.parse(s)); } close() {} };
"""
_SHELL_DIAG_DRIVER = r"""
const out = {};
const diag = (what, data) => window.__rompShellDiag(what, data);
const since = (n) => SENT.slice(n).filter((m) => m.type === 'clientDiag').map((m) => m.what);   // the clientDiag whats the socket saw after row n
out.dial = { sockets: WSS.length, url: WSS[0].url, readyState: WSS[0].readyState, sentBeforeOpen: SENT.length, poster: typeof window.__rompShellDiag };
// a. the socket is still down: a muted row is never queued, an unmuted one waits in the queue; muted again at the
// open, the flush re-reads the switch and holds the waiting row (the leg the old flush fails: it sent probe-b)
STORE = '{"perfMute":true}';  diag('probe-a', {});
STORE = '{"perfMute":false}'; diag('probe-b', {});
STORE = '{"perfMute":true}';
WSS[0].readyState = 1; WSS[0].onopen();
out.a = { types: SENT.map((m) => m.type), whats: since(0) };
let n = SENT.length;
// b. still muted with the socket open: dropped at the row
diag('probe-c', {});
out.b = since(n); n = SENT.length;
// c. unmuted: the row goes out whole
STORE = '{"perfMute":false}'; diag('probe-d', { x: 1 });
out.c = { whats: since(n), rows: SENT.slice(n) }; n = SENT.length;
// d. the literal true alone mutes: a string, a missing store and unparsable JSON each read as off
STORE = '{"perfMute":"yes"}'; diag('probe-e', {});
STORE = null;                 diag('probe-f', {});
STORE = 'not json';           diag('probe-g', {});
out.d = since(n); n = SENT.length;
// e. on, then off again, the socket open throughout: the switch is read at each row, never cached
STORE = '{"perfMute":true}';  diag('probe-h', {});
STORE = '{"perfMute":false}'; diag('probe-i', {});
out.e = since(n);
console.log(JSON.stringify(out));
"""


class MobileShellDiagExecutes(unittest.TestCase):
    """The beacon extension's kill switch in the shell (2026-09-18): the gear's perfMute, off by default and on for the
    literal true alone (a string value, a missing store and unparsable JSON all read as off), stops the shell's own
    clientDiag rows the way it stops the panes'. A review found the shell's switch pinned by source text only
    (tests/test_perf_beacon_shim.py) although this file already runs the whole shell script under node, and found
    that the shell socket's open flush did not re-read the switch: a mute flipped on while the socket was down
    released the rows queued before it, where the pane shim's flush re-read it and held them. This harness runs the
    script against the fit harness's window plus a mutable store, a location and a fake WebSocket class, flips the
    store between rows and reads what reached the socket: diagQ is a local of the script's IIFE, so the queue is
    observed only through what the open flush sends. Leg a is the one the old flush fails."""

    @classmethod
    def setUpClass(cls):
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
            f.write(_FIT_HARNESS + _SHELL_DIAG_HARNESS + _mobile_js() + _SHELL_DIAG_DRIVER)
            path = f.name
        try:
            r = subprocess.run(["node", path], capture_output=True, text=True, timeout=30)
        finally:
            os.unlink(path)
        # The template as the page serves it (_mobile_js above).
        assert r.returncode == 0, "the mobile script threw: " + r.stderr[:800]
        cls.out = json.loads(r.stdout.strip().splitlines()[-1])

    def test_the_shell_dials_one_socket_with_the_dashboards_wid_and_publishes_the_poster(self):
        d = self.out["dial"]
        self.assertEqual(d["sockets"], 1)
        self.assertTrue(d["url"].startswith("wss://TESTHOST/ws?app=shell&wid="), d["url"])
        self.assertEqual((d["readyState"], d["sentBeforeOpen"]), (0, 0), "nothing reaches a socket that has not opened")
        self.assertEqual(d["poster"], "function", "window.__rompShellDiag, the door the bell and tap-landing scripts post through")

    def test_a_mute_flipped_on_while_the_socket_was_down_holds_the_rows_queued_before_it(self):
        # probe-a was muted at its row and never queued; probe-b was queued unmuted; the open's flush re-read the switch
        # and held it, so the socket saw the ready alone
        self.assertEqual(self.out["a"], {"types": ["ready"], "whats": []})

    def test_a_muted_row_on_an_open_socket_is_dropped(self):
        self.assertEqual(self.out["b"], [])

    def test_an_unmuted_row_is_sent_whole(self):
        c = self.out["c"]
        self.assertEqual(c["whats"], ["probe-d"])
        self.assertEqual(c["rows"], [{"type": "clientDiag", "surface": "shell", "what": "probe-d", "data": {"x": 1}}])

    def test_the_literal_true_alone_mutes(self):
        self.assertEqual(self.out["d"], ["probe-e", "probe-f", "probe-g"])

    def test_the_switch_is_read_at_each_row(self):
        self.assertEqual(self.out["e"], ["probe-i"])


# ── the shell socket as the page's link probe (D3, 2026-09-18) ──────────────────────────────────────
# The shell script runs under node against the fit harness's window plus controllable timers, a fake WebSocket
# and a mutable clock (the pattern MobileShellDiagExecutes uses at PR 762's head). D3 makes the shell socket the
# page's ONE link probe: one attempt in flight, a 15 s connect cut (SH_CONNECT_MS), the refused ladder 1/2/4/4 s
# reset by an open, a return-probe row filed per return, and window.__rompLink for the panes to follow.
_SHELL_PROBE_HARNESS = r"""
var SHNOW=1000000;Date.now=function(){return SHNOW;};
var SHTIMERS=[];global.setTimeout=function(fn,ms){SHTIMERS.push({fn:fn,ms:ms,live:true,at:SHNOW+ms});return SHTIMERS.length;};   // at: when the timer is due on the fake clock (shRunRefused walks them in order)
global.clearTimeout=function(id){if(id&&SHTIMERS[id-1])SHTIMERS[id-1].live=false;};
var SHINTERVALS=[];global.setInterval=function(fn,ms){SHINTERVALS.push({fn:fn,ms:ms});return SHINTERVALS.length;};
global.location={protocol:'https:',host:'TESTHOST',search:''};
global.sessionStorage={getItem:function(k){return k==='romp:wid'?'W1':'';}};
var SHSOCKS=[];global.WebSocket=function(u){this.url=u;this.readyState=0;this.sent=[];SHSOCKS.push(this);};
global.WebSocket.prototype.send=function(s){this.sent.push(s);};global.WebSocket.prototype.close=function(){this.readyState=3;};
var TELLS=0,TELLLINKS=[];window.__rompPanesTell=function(){TELLS++;TELLLINKS.push(window.__rompLink().up);};   // count the shell's re-tells of the panes word (D3: open/close/abandon) and record the link each tell reads (review round 1: the publication order, the link reads up before the open's word)
var LOST=0;window.__rompApiSocketLost=function(){LOST++;};   // the API health detail's hook: a press pending on the socket cannot be answered (review round 1: an abandon tells it too)
function shSock(){return SHSOCKS[SHSOCKS.length-1];}
function shOpen(){var s=shSock();s.readyState=1;s.onopen();return s;}
function shRecv(m){shSock().onmessage({data:JSON.stringify(m)});}
function shTick(){SHINTERVALS.forEach(function(iv){iv.fn();});}
function shFireDoc(t){(DOC[t]||[]).forEach(function(f){f({type:t});});}
function shHide(){document.visibilityState='hidden';shFireDoc('visibilitychange');}
function shShow(){document.visibilityState='visible';shFireDoc('visibilitychange');}
function shProbeRows(){var all=[];SHSOCKS.forEach(function(s){s.sent.forEach(function(x){var m=JSON.parse(x);if(m.type==='clientDiag'&&m.surface==='shell'&&m.what==='return-probe')all.push(m.data);});});return all;}
function shDialTimers(){return SHTIMERS.filter(function(t){return t.live&&t.fn.name==='shellWS';});}
function shFireDials(){shDialTimers().forEach(function(t){t.live=false;t.fn();});}
// walk the fake clock timer by timer until `until`, refusing every dial the moment it is made (a fast-refusing path);
// returns the most live shellWS timers seen at any moment (one chain reads 1; a doubled chain 2)
function shRunRefused(until){var maxLive=0;function peek(){var n=shDialTimers().length;if(n>maxLive)maxLive=n;}
peek();for(var guard=0;guard<1000;guard++){var live=shDialTimers();if(!live.length)break;
var next=live[0];live.forEach(function(t){if(t.at<next.at)next=t;});if(next.at>until)break;
SHNOW=Math.max(SHNOW,next.at);next.live=false;next.fn();var s=shSock();if(s.readyState===0){s.readyState=3;s.onclose({code:1006});}peek();}
return maxLive;}
function shRefuseNow(){var s=shSock();if(s.readyState===0){s.readyState=3;s.onclose({code:1006});}}
function shOut(o){process.stdout.write(JSON.stringify(o));}
"""


def _run_probe(scenario, pre=""):
    """`pre` runs after the shell harness and BEFORE the shell script (the reconnect cue's Log fakes, _CUE_PRE)."""
    node = shutil.which("node")
    if not node:
        raise unittest.SkipTest("node not installed")
    fx = tempfile.mkdtemp()
    path = os.path.join(fx, "run.js")
    with open(path, "w") as f:
        f.write(_FIT_HARNESS + _SHELL_PROBE_HARNESS + pre + _mobile_js() + "\n" + scenario)
    r = subprocess.run([node, path], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise AssertionError("node failed:\n" + r.stderr)
    return json.loads(r.stdout.strip().splitlines()[-1])


# The shell script AND one pane's shim in one node process on one fake clock (review round 3, 2026-09-18): the pane's
# parentLink() reads the window.__rompLink the shell really publishes, and the shell's tell hands the pane the panes
# word broadcastAll builds (panesMsg's link field, up or down), so a case asserts the PANE's response to the shell's
# stamp (a link-backstop row and a dial, or neither) rather than a connT number alone. The shell runs first, at module
# scope against the global fakes, exactly as _run_probe runs it; the pane harness and the shim core run inside a
# function scope, so their `var window`, `var document`, `var setInterval` and `function WebSocket` shadow nothing the
# shell reads. From the scenario the shell's helpers (shOpen, shRecv, shTick, shHide, shShow, shSock, SHSOCKS,
# shDialTimers) and the pane's (open, recv, tick, hide, show, sock, rows, sockets, awaitLink) are both in reach; the
# shell's own publication is global.__rompLink(). One clock: advance NOW only (the glue points both at it).
_LINK_GLUE = r"""
SHNOW=NOW;Date.now=function(){return NOW;};   // one clock for the page (the shell's boot dial ran at SHNOW, the same 1,000,000)
Object.defineProperty(window.parent,"__rompLink",{configurable:true,get:function(){return global.__rompLink;}});   // the pane reads the shell's real publication
var shellTell=global.__rompPanesTell;global.__rompPanesTell=function(){shellTell();fireWin("message",{romp:"panes",on:{},link:global.__rompLink().up?"up":"down"});};   // the shell's tell reaches the pane as the panes word broadcastAll builds
"""


def _run_linked(scenario, app="test", pre="", before=""):
    """`app` reaches km._shim_core_js as a served page's would (the chat's diet line and the feed's park exemption key on it).
    `pre` runs after the shell harness and BEFORE the shell script (element fakes with attributes, the lazy panes). `before`
    runs inside the pane scope after the pane harness and BEFORE the shim core: the pane's document loading after a shell
    event (a tap that promotes a lazy pane), where the default runs the shim at the shell's boot as every case before did."""
    node = shutil.which("node")
    if not node:
        raise unittest.SkipTest("node not installed")
    fx = tempfile.mkdtemp()
    path = os.path.join(fx, "run.js")
    with open(path, "w") as f:
        f.write(_FIT_HARNESS + _SHELL_PROBE_HARNESS + pre + _mobile_js() + "\n(function(){\n" + _PANE_HARNESS + before + km._shim_core_js(app) + "\n" + _LINK_GLUE + scenario + "\n})();\n")
    r = subprocess.run([node, path], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise AssertionError("node failed:\n" + r.stderr)
    return json.loads(r.stdout.strip().splitlines()[-1])


class ShellLinkProbe(unittest.TestCase):
    """D3 (2026-09-18): the shell socket is the page's one link probe. It gets the shim's liveness rules with the
    shell's OWN copy of the constants (romp-manager's ruling; tests/test_kernel_ws_heartbeat.py pins the two copies to
    agree), files ONE return-probe row per return, and publishes window.__rompLink for the panes to follow. Run under
    node against a fake WebSocket and controllable timers, the way MobileShellDiagExecutes runs the shell script.

    Review round 1 (2026-09-18) added the executed cases the refuters found missing: the one-live-attempt guard, the
    standing socket that files no probe, the watchdog's OPEN-quiet arm with the freeze and resume stamps, the two 250 ms
    cadences, the publication order, the probe row's integers; and the three shell fixes of that round: one pending
    redial timer (a dial clears it), the CLOSED arm that can fire (onclose keeps shWs), and the abandon that tells the
    API health detail.

    Review round 3 (2026-09-18) added the two linked cases at the tail (_run_linked: the shell script and one pane's shim
    in one node process, the pane reading the shell's real publication), the loop-alive stamp's two halves, each pinned
    by the pane's own response."""

    def test_the_shell_dials_one_socket_with_the_dashboards_wid_and_publishes_the_link(self):
        r = _run_probe(r"""
var before=window.__rompLink();var tell0=TELLS;
shOpen();var atOpen=window.__rompLink();var tellOnOpen=TELLS-tell0;
shRecv({type:'ka'});
SHNOW+=40000;var whenStale=window.__rompLink();   // no frame for >SH_STALE_MS: link reads down though the socket is OPEN
shOut({socks:SHSOCKS.length,url:SHSOCKS[0].url,before:before,atOpen:atOpen,whenStale:whenStale,tellOnOpen:tellOnOpen});""")
        self.assertEqual(r["socks"], 1, "one shell socket dialed at load (one live attempt)")
        self.assertTrue(r["url"].startswith("wss://TESTHOST/ws?app=shell&wid="), r["url"])
        self.assertIs(r["before"]["up"], False, "no link before the socket opens")
        self.assertIs(r["atOpen"]["up"], True, "the socket open publishes the link up")
        self.assertGreaterEqual(r["tellOnOpen"], 1, "the open re-tells the panes word")
        self.assertIs(r["whenStale"]["up"], False, "__rompLink reads up only for an OPEN socket fresh within SH_STALE_MS")

    def test_the_visibility_fast_path_probes_the_path_and_files_one_return_probe_row(self):
        r = _run_probe(r"""
shOpen();shRecv({type:'ka'});
shHide();SHSOCKS[0].readyState=3;   // the socket died while the app was in the background
SHNOW+=100;shShow();
var dialedAtReturn=SHSOCKS.length;   // the fast path abandoned the dead socket and dialed a fresh one
shOpen();   // the fresh socket opens: the return-probe row files at its open
shOut({dialedAtReturn:dialedAtReturn,probe:shProbeRows()});""")
        self.assertEqual(r["dialedAtReturn"], 2, "the fast path put the dead socket down and dialed at once")
        self.assertEqual(len(r["probe"]), 1, "ONE shell return-probe row per return")
        self.assertEqual(sorted(r["probe"][0].keys()), sorted(["decision", "hiddenMs", "quietMs", "attempts", "firstFailMs", "ms"]))
        self.assertEqual(r["probe"][0]["decision"], "redial-closed", "a dead socket at the return")

    def test_a_hung_attempt_is_cut_at_15s_and_one_attempt_is_in_flight(self):
        r = _run_probe(r"""
shOpen();shRecv({type:'ka'});
shHide();SHSOCKS[0].readyState=3;SHNOW+=100;shShow();   // dial a fresh socket; the path hangs, so it stays CONNECTING
var dialed=SHSOCKS.length;
SHNOW+=5000;shTick();var beforeCut=SHSOCKS.length;      // <15 s: no cut, still ONE attempt in flight
SHNOW+=11000;shTick();var cutRs=SHSOCKS[1].readyState;  // >15 s since the dial: the tick closes the CONNECTING socket
SHSOCKS[1].onclose({code:1006});var armedAfterCut=SHSOCKS.length;   // the browser's onclose then arms the redial
shFireDials();var afterRedial=SHSOCKS.length;
shOut({dialed:dialed,beforeCut:beforeCut,cutRs:cutRs,armedAfterCut:armedAfterCut,afterRedial:afterRedial});""")
        self.assertEqual(r["dialed"], 2, "one fresh attempt at the return")
        self.assertEqual(r["beforeCut"], 2, "the tick does not dial a second while one attempt is in flight and young")
        self.assertEqual(r["cutRs"], 3, "the 15 s connect cut closes the hung CONNECTING socket")
        self.assertEqual(r["armedAfterCut"], 2, "its onclose arms a redial, no new socket yet")
        self.assertEqual(r["afterRedial"], 3, "the redial dials the next single attempt")

    def test_one_live_attempt_a_late_timer_calling_in_on_a_connecting_or_open_socket_dials_nothing(self):
        # review round 1 (tests-2): the guard at the top of shellWS, exercised directly. A refused attempt arms the
        # ladder timer; a return then dials at once and clears it (one chain), but a browser that had already queued
        # the timer's callback can still call in late: with an attempt CONNECTING, and again with it OPEN, the guard
        # dials nothing. Without the guard the same calls dial a second and a third concurrent socket.
        r = _run_probe(r"""
shOpen();shRecv({type:'ka'});
shHide();SHSOCKS[0].readyState=3;SHNOW+=100;shShow();   // the fast path dials socket 2
shRefuseNow();                                          // refused: the ladder timer arms (1 s)
var late=shDialTimers()[0];                             // the callback a browser could still deliver late
shHide();SHNOW+=100;shShow();                           // a second return: the fast path dials socket 3 (CONNECTING) and clears the timer
var afterReturn=SHSOCKS.length,timerLive=late.live;
late.fn();var afterLateCall=SHSOCKS.length;             // the late call finds one attempt CONNECTING: nothing
shOpen();late.fn();shTick();var afterOpen=SHSOCKS.length;   // and OPEN: nothing (the tick's arms leave a fresh OPEN socket alone too)
shOut({afterReturn:afterReturn,timerLive:timerLive,afterLateCall:afterLateCall,afterOpen:afterOpen});""")
        self.assertEqual(r["afterReturn"], 3, "the second return dialed one fresh attempt")
        self.assertIs(r["timerLive"], False, "the return's dial cleared the pending ladder timer (one chain)")
        self.assertEqual(r["afterLateCall"], 3, "a late call into shellWS with an attempt CONNECTING dials nothing: one live attempt")
        self.assertEqual(r["afterOpen"], 3, "...and with it OPEN, nothing")

    def test_a_standing_socket_at_the_return_is_kept_and_files_no_return_probe(self):
        # review round 1 (tests-3): the body's claim that `keep` never posts. The socket is OPEN and fresh at the
        # return, so the fast path keeps it: no dial, no row. Reading the rows at the return alone would be vacuous (a
        # probe files on the NEXT open), so a wrongly dialed socket is given the open that would file its row.
        r = _run_probe(r"""
shOpen();shRecv({type:'ka'});
shHide();SHNOW+=100;shShow();                           // a short background with the socket standing
var socks=SHSOCKS.length,rs=SHSOCKS[0].readyState;
if(SHSOCKS.length>1)shOpen();                           // a socket the return should not have dialed gets its open
shOut({socks:socks,rs:rs,rows:shProbeRows()});""")
        self.assertEqual(r["socks"], 1, "the standing socket is kept: no dial at the return")
        self.assertEqual(r["rs"], 1)
        self.assertEqual(r["rows"], [], "and no return-probe row: a keep never posts")

    def test_the_return_probe_row_carries_the_ladders_integers_with_the_clock_advanced(self):
        # review round 1 (tests-7): the row's integers, asserted with the fake clock moving (with it still, firstFailMs
        # and ms both read 0 and a kernel that hard-coded them would pass). Four refusals 500 ms apart, then the open.
        r = _run_probe(r"""
shOpen();shRecv({type:'ka'});SHNOW+=300;
shHide();SHSOCKS[0].readyState=3;SHNOW+=100;shShow();   // hidden 100 ms, quiet 400 ms (review round 2: two gaps that differ, so no constant satisfies both); the fast path dials at once
function refuse(){SHNOW+=500;shRefuseNow();shFireDials();}
refuse();refuse();refuse();refuse();                    // four refusals: the ladder, each 500 ms after its dial
SHNOW+=500;shOpen();                                    // the fifth attempt opens 2500 ms after the foreground
shOut({probe:shProbeRows()});""")
        self.assertEqual(len(r["probe"]), 1)
        self.assertEqual(r["probe"][0], {"decision": "redial-closed", "hiddenMs": 100, "quietMs": 400, "attempts": 4, "firstFailMs": 2000, "ms": 2500},
                         "hiddenMs and quietMs from the return, attempts the refusals, firstFailMs from the first refusal, ms foreground to open")

    def test_a_refused_attempt_backs_off_on_the_1_2_4_4s_ladder_reset_by_an_open(self):
        r = _run_probe(r"""
shOpen();shRecv({type:'ka'});
shHide();SHSOCKS[0].readyState=3;SHNOW+=100;shShow();
var delays=[];
function refuse(){var s=shSock();s.readyState=3;s.onclose({code:1006});delays.push(SHTIMERS[SHTIMERS.length-1].ms);shFireDials();}
refuse();refuse();refuse();refuse();   // four fast refusals within the connect cut: the ladder
var laddered=delays.slice();
shOpen();   // an open resets the rung
var s=shSock();s.readyState=3;s.onclose({code:1006});shFireDials();   // the opened socket drops (not a refusal): arms and redials
var fresh=shSock();fresh.readyState=3;fresh.onclose({code:1006});   // the fresh dial is refused: rung reset to 1000
var afterReset=SHTIMERS[SHTIMERS.length-1].ms;
shOut({laddered:laddered,afterReset:afterReset});""")
        self.assertEqual(r["laddered"], [1000, 2000, 4000, 4000], "the refused ladder 1/2/4/4 s")
        self.assertEqual(r["afterReset"], 1000, "an open resets the rung, so the next refusal is 1 s again")

    def test_rompLink_reads_up_only_for_an_open_socket_fresh_within_stale_ms(self):
        r = _run_probe(r"""
shOpen();shRecv({type:'ka'});var open1=window.__rompLink().up;
SHNOW+=40000;var stale1=window.__rompLink().up;
shRecv({type:'ka'});var fresh=window.__rompLink().up;
shSock().readyState=3;var closed=window.__rompLink().up;
shOut({open1:open1,stale1:stale1,fresh:fresh,closed:closed});""")
        self.assertEqual([r["open1"], r["stale1"], r["fresh"], r["closed"]], [True, False, True, False])

    def test_the_open_and_close_re_tell_the_panes_word_and_the_word_reads_the_link_as_it_stands(self):
        # review round 1 (tests-5): the publication order. The open stamps shLastRecv BEFORE it re-tells, so the word
        # the panes hear at the open reads the link up (a tell ahead of the stamp would read a stale clock: down); the
        # close's tell reads down. The stale-return shape, the phone's case: hide, the socket dies, a long gap, the
        # return abandons (a tell reading down) and the fresh open tells up.
        r = _run_probe(r"""
var n0=TELLLINKS.length;shOpen();var atOpen=TELLLINKS.slice(n0);
var n1=TELLLINKS.length;SHSOCKS[0].readyState=3;SHSOCKS[0].onclose({code:1006});var atClose=TELLLINKS.slice(n1);
shFireDials();shOpen();shRecv({type:'ka'});             // the blind redial opens
shHide();shSock().readyState=3;SHNOW+=100000;           // dead while hidden, a long gap
var n2=TELLLINKS.length;shShow();var atReturn=TELLLINKS.slice(n2);   // the abandon's tell
var n3=TELLLINKS.length;shOpen();var atFreshOpen=TELLLINKS.slice(n3);
shOut({atOpen:atOpen,atClose:atClose,atReturn:atReturn,atFreshOpen:atFreshOpen});""")
        self.assertEqual(r["atOpen"], [True], "the socket open re-tells the panes word once, and the word reads the link UP (the stamp lands before the tell)")
        self.assertEqual(r["atClose"], [False], "the socket close re-tells it once, reading down")
        self.assertEqual(r["atReturn"], [False], "the return's abandon re-tells it, reading down")
        self.assertEqual(r["atFreshOpen"], [True], "the fresh open after a stale return tells up")

    # ---- review round 1 (tests-4): the watchdog's OPEN-quiet arm, the freeze and resume stamps, the two 250 ms cadences,
    # all executed (the source-text pin in tests/test_kernel_ws_heartbeat.py is the parity check alone)
    def test_the_watchdogs_open_quiet_arm_abandons_and_redials_a_socket_quiet_past_stale_ms(self):
        r = _run_probe(r"""
shOpen();shRecv({type:'ka'});var t0=TELLS,l0=LOST;
SHNOW+=29000;shTick();var before=SHSOCKS.length;        // quiet 29 s: inside the bound, kept
SHNOW+=2000;shTick();                                   // quiet 31 s: past SH_STALE_MS
shOut({before:before,socks:SHSOCKS.length,rs0:SHSOCKS[0].readyState,tells:TELLS-t0,lost:LOST-l0});""")
        self.assertEqual(r["before"], 1, "quiet inside the bound: kept")
        self.assertEqual(r["socks"], 2, "quiet past SH_STALE_MS: the arm abandons the socket and redials at once")
        self.assertEqual(r["rs0"], 3, "the quiet socket was closed by the abandon")
        self.assertGreaterEqual(r["tells"], 1, "the abandon re-told the panes (link down)")
        self.assertEqual(r["lost"], 1, "and told the API health detail once (a press pending on it cannot be answered)")

    def test_a_resume_stamps_a_fresh_open_socket_and_the_kept_socket_runs_at_the_provisional_bound(self):
        # the freeze/resume window sits strictly inside the stale bound (10 s frozen, 26 s since the last frame at the
        # deciding tick), so the redial can come from the resume stamp's PROVISIONAL bound alone: 14 s after the stamp
        # nothing, 16 s after it the abandon. Without the stamp the socket reads 26 s quiet under the 30 s bound: kept.
        r = _run_probe(r"""
shOpen();shRecv({type:'ka'});
shFireDoc('freeze');SHNOW+=10000;shFireDoc('resume');   // a Chromium thaw: the OPEN socket is stamped, provisionally
SHNOW+=14000;shTick();var at14=SHSOCKS.length;
SHNOW+=2000;shTick();var at16=SHSOCKS.length;
shOut({at14:at14,at16:at16});""")
        self.assertEqual(r["at14"], 1, "14 s after the resume stamp: inside SH_PROVISIONAL_MS, kept")
        self.assertEqual(r["at16"], 2, "16 s after it: the provisional keep no frame confirmed is abandoned and redialed")

    def test_a_socket_already_stale_at_the_freeze_is_not_re_stamped_by_the_resume(self):
        r = _run_probe(r"""
shOpen();shRecv({type:'ka'});
SHNOW+=35000;shFireDoc('freeze');                       // 35 s quiet when the tab froze: already past SH_STALE_MS
SHNOW+=5000;shFireDoc('resume');shTick();               // the thaw must not make it fresh
shOut({socks:SHSOCKS.length});""")
        self.assertEqual(r["socks"], 2, "a socket 30 s overdue when the tab froze is not stamped: the tick abandons and redials it")

    def test_an_announced_restart_keeps_the_250ms_redial(self):
        r = _run_probe(r"""
shOpen();shRecv({type:'ka'});shRecv({type:'restarting',boot:'1'});
SHNOW+=100;shSock().readyState=3;shSock().onclose({code:1006});
var t=SHTIMERS[SHTIMERS.length-1];
shOut({fn:t.fn.name,ms:t.ms,live:t.live});""")
        self.assertEqual([r["fn"], r["ms"], r["live"]], ["shellWS", 250, True], "the kernel's own word: a tight redial")

    def test_a_hung_attempt_cut_inside_the_return_window_redials_at_250ms(self):
        r = _run_probe(r"""
shOpen();shRecv({type:'ka'});
shHide();SHSOCKS[0].readyState=3;SHNOW+=100;shShow();   // the fast path dials; the path hangs
SHNOW+=16000;shTick();var cut=SHSOCKS[1].readyState;    // past the 15 s cut: the tick closes it
SHSOCKS[1].onclose({code:1006});var t=SHTIMERS[SHTIMERS.length-1];   // the browser's onclose, 16 s into the return window
shOut({cut:cut,fn:t.fn.name,ms:t.ms});""")
        self.assertEqual(r["cut"], 3)
        self.assertEqual([r["fn"], r["ms"]], ["shellWS", 250], "a hung attempt the cut paced, inside the window: the prompt 250 ms redial")

    # ---- review round 1: the three shell fixes of that round
    def test_a_return_during_an_outage_makes_one_redial_chain_the_dial_clears_the_pending_blind_timer(self):
        # fresh-1: the pre-return close's blind 2 s timer is still pending when the page returns (a page whose timers
        # keep running while hidden: this harness, a desktop tab, Android Chrome before its throttle). The return's
        # direct dial must cancel it, or two chains run the ladder side by side for the whole outage (before the fix:
        # two live timers after the return and eighteen dials in 30 s of refusals; after: one and about ten).
        r = _run_probe(r"""
shOpen();shRecv({type:'ka'});
shHide();var held=SHSOCKS[0];held.readyState=3;held.onclose({code:1006});   // the held socket's close reaches the page while hidden: the blind redial arms
var timersBeforeReturn=shDialTimers().length;
SHNOW+=100;shShow();shRefuseNow();                      // the return dials at once; the path refuses it
var liveAfterReturn=shDialTimers().length;
var maxLive=shRunRefused(SHNOW+30000);                  // 30 s of refusals on the fake clock
shOut({timersBeforeReturn:timersBeforeReturn,liveAfterReturn:liveAfterReturn,maxLive:maxLive,dials:SHSOCKS.length-1});""")
        self.assertEqual(r["timersBeforeReturn"], 1, "the close while hidden armed the blind redial")
        self.assertEqual(r["liveAfterReturn"], 1, "the return's dial cleared it: the refusal's ladder timer is the ONE pending timer")
        self.assertEqual(r["maxLive"], 1, "at no moment in 30 s of refusals is more than one redial timer live: one chain")
        self.assertLessEqual(r["dials"], 10, "about ten dials from the return in 30 s on the ladder (a doubled chain made eighteen)")
        self.assertGreaterEqual(r["dials"], 8)

    def test_the_watchdogs_closed_arm_recovers_a_lost_redial_timer(self):
        # correctness-2: a CLOSED socket whose redial timer the browser lost. onclose keeps shWs (it nulled it before,
        # so the tick returned on !shWs and this arm could never fire).
        r = _run_probe(r"""
shOpen();shRecv({type:'ka'});
SHNOW+=100;shSock().readyState=3;shSock().onclose({code:1006});   // an ordinary drop: the blind redial arms
var armed=shDialTimers().length,armedMs=shDialTimers()[0].ms,linkAfterClose=window.__rompLink().up;
SHNOW+=8001;shTick();                                   // the timer never fired; SH_REDIAL_MS (8 s) past the dial, the CLOSED arm dials
var dialed=SHSOCKS.length,liveAfter=shDialTimers().length;
shOut({armed:armed,armedMs:armedMs,linkAfterClose:linkAfterClose,dialed:dialed,liveAfter:liveAfter});""")
        self.assertEqual(r["armed"], 1)
        self.assertEqual(r["armedMs"], 2000, "the blind redial after an ordinary drop outside any window is SH_BLIND_MS (2 s), the cadence the pane's 25 s backstop derivation rests on (review round 2: pinned by text alone before)")
        self.assertIs(r["linkAfterClose"], False, "a CLOSED shWs publishes the link down")
        self.assertEqual(r["dialed"], 2, "the CLOSED arm dials once the redial bound has passed")
        self.assertEqual(r["liveAfter"], 0, "and its dial cleared the lost timer, so no second chain follows")

    def test_an_abandon_tells_the_api_health_detail_once_as_a_browser_reported_close_does(self):
        # regression-1 / kernel-1: shAbandon detaches onclose, so the detail's hook (window.__rompApiSocketLost) was
        # never called on the return's abandon or the watchdog's; a pause press pending on that socket stayed
        # acknowledged through the redial. Now each abandon of the socket the detail rides tells it, once.
        r = _run_probe(r"""
shOpen();shRecv({type:'ka'});var l0=LOST;
shHide();SHSOCKS[0].readyState=3;SHNOW+=100;shShow();   // the return's abandon of a socket the browser never reported closed
var onReturnAbandon=LOST-l0;
shOpen();shRecv({type:'ka'});var l1=LOST;
SHNOW+=31000;shTick();                                  // the watchdog's OPEN-quiet abandon
var onWatchdogAbandon=LOST-l1;
shOpen();shRecv({type:'ka'});var l2=LOST;
SHNOW+=100;shSock().readyState=3;shSock().onclose({code:1006});   // a browser-reported close, for comparison
var onBrowserClose=LOST-l2;
shOut({onReturnAbandon:onReturnAbandon,onWatchdogAbandon:onWatchdogAbandon,onBrowserClose:onBrowserClose});""")
        self.assertEqual(r["onReturnAbandon"], 1, "the return's abandon tells the detail once")
        self.assertEqual(r["onWatchdogAbandon"], 1, "the watchdog's abandon tells it once")
        self.assertEqual(r["onBrowserClose"], 1, "as a browser-reported close always did")

    # ---- review round 2 (2026-09-18): the three shell fixes of that round
    def test_a_long_standing_open_socket_crossing_the_quiet_bound_publishes_the_tick_stamp_as_connT_not_the_dial_time(self):
        # regression-1: connT is the loop-alive stamp, the later of the last dial and the watchdog's last tick with a socket
        # to watch. An OPEN socket that dialed an hour ago and then goes quiet past SH_STALE_MS reads down for up to one tick
        # before the watchdog puts it down; in that tick the pane's backstop read the DIAL time, 3,631,000 ms stale, called
        # the shell's loop dead and dialed on its own. Now it reads the last tick, 1 s old.
        r = _run_probe(r"""
shOpen();shRecv({type:'ka'});
for(var i=0;i<720;i++){SHNOW+=5000;shRecv({type:'ka'});shTick();}   // an hour of frames and ticks on the one socket
for(var j=0;j<6;j++){SHNOW+=5000;shTick();}                        // 30 s quiet with the tick running: at the bound, kept
SHNOW+=1000;                                                        // 31 s quiet: the link reads down, the tick not yet run
var L=window.__rompLink();
var before={up:L.up,stale:SHNOW-L.connT,socks:SHSOCKS.length};
shTick();                                                           // the OPEN-quiet arm puts the socket down and redials
var after=window.__rompLink();
shOut({before:before,socks:SHSOCKS.length,afterStale:SHNOW-after.connT});""")
        self.assertIs(r["before"]["up"], False, "31 s quiet: the link reads down")
        self.assertEqual(r["before"]["socks"], 1, "...before the tick puts the socket down")
        self.assertLess(r["before"]["stale"], 25000, "connT is the loop-alive stamp: under the pane's 25 s bound while the tick runs (the dial time alone read 3,631,000 ms stale here)")
        self.assertEqual(r["before"]["stale"], 1000, "the last tick, one second ago")
        self.assertEqual(r["socks"], 2, "the tick abandons the quiet socket and redials")
        self.assertEqual(r["afterStale"], 0, "the redial stamps connT afresh")

    def test_a_page_loaded_hidden_keeps_its_boot_dial_at_its_first_foreground_and_files_no_probe(self):
        # kernel-1: the shim's not-yet-connected guard, in the shell's fast path. A dashboard opened in a background tab has
        # its boot dial CONNECTING when it first comes to the foreground; the fast path read that as a dead socket, abandoned
        # the boot dial, dialed a second socket and filed a return-probe row (hiddenMs -1, quietMs -1) for a return that
        # never happened. The guard sits after the foreground stamp and the ring reset, as the shim's does, so a drop after
        # the foreground still redials at the in-window cadence.
        r = _run_probe(r"""
var boot={socks:SHSOCKS.length,rs:SHSOCKS[0].readyState};           // the boot dial, CONNECTING; the page was never hidden
var t0=TELLS,l0=LOST;
shShow();                                                            // the first foreground, before the boot dial opened
var atShow={socks:SHSOCKS.length,rs:SHSOCKS[0].readyState,tells:TELLS-t0,lost:LOST-l0};
shOpen();                                                            // the boot dial opens
var rows=shProbeRows();
SHNOW+=100;shSock().readyState=3;shSock().onclose({code:1006});     // a drop 100 ms after the foreground: inside the window
var t=SHTIMERS[SHTIMERS.length-1];
shOut({boot:boot,atShow:atShow,rows:rows,drop:{fn:t.fn.name,ms:t.ms}});""")
        self.assertEqual(r["boot"], {"socks": 1, "rs": 0})
        self.assertEqual(r["atShow"], {"socks": 1, "rs": 0, "tells": 0, "lost": 0}, "the foreground leaves the CONNECTING boot dial alone: no abandon, no second socket, no tell")
        self.assertEqual(r["rows"], [], "no return-probe row: there was no return")
        self.assertEqual([r["drop"]["fn"], r["drop"]["ms"]], ["shellWS", 250], "the foreground was stamped before the guard: a drop inside the window redials at the in-window cadence")

    def test_a_return_whose_probe_never_opened_before_the_next_return_files_its_row_at_that_return(self):
        # fresh-3: the fast path overwrote a pending probe and reset the failure counters, so a return the path outlasted
        # left no row and read-side.md's one row per return overstated. The pending row is filed at the next return (queued
        # until the open) with ms and firstFailMs at the row's -1 sentinels and the attempts as they stand.
        r = _run_probe(r"""
shOpen();shRecv({type:'ka'});
shHide();SHSOCKS[0].readyState=3;SHNOW+=100;shShow();                // return 1: the fast path dials
SHNOW+=500;shRefuseNow();                                            // refused once: attempts 1, the ladder timer arms
shHide();SHNOW+=100;shShow();                                        // return 2 before any open
var socks=SHSOCKS.length;
SHNOW+=200;shOpen();                                                 // return 2's dial opens: both rows flush onto it
shOut({socks:socks,rows:shProbeRows()});""")
        self.assertEqual(r["socks"], 3, "return 2 dialed afresh (the refused socket is CLOSED, so the guard lets it)")
        self.assertEqual(len(r["rows"]), 2, "one row per return: the first filed at the second")
        self.assertEqual(r["rows"][0], {"decision": "redial-closed", "hiddenMs": 100, "quietMs": 100, "attempts": 1, "firstFailMs": -1, "ms": -1},
                         "return 1's row: its decision and gaps, the one refusal, ms and firstFailMs -1 (the next return came before the open)")
        self.assertEqual(r["rows"][1], {"decision": "redial-closed", "hiddenMs": 100, "quietMs": 700, "attempts": 0, "firstFailMs": -1, "ms": 200},
                         "return 2's row: its own gaps and counters, reset at the return")

    # ---- review round 3 (2026-09-18): the loop-alive stamp's two halves, the pane following the shell's real publication
    def test_a_shell_whose_loop_died_with_no_socket_goes_stale_and_the_panes_backstop_dials_with_its_row(self):
        # tests-1 and kernel-1: the half of the stamp that keeps a DEAD shell from reading alive. The stamp sits AFTER the
        # tick's no-socket guard (round 2, item 2), so a shell left with no socket at all stops renewing connT and the
        # pane's 25 s link-backstop can call its loop dead. The phone's shape: both sockets quiet in the background; at
        # the return the path is so broken that the WebSocket constructor itself throws, so the shell's abandon dials
        # nothing and arms nothing (no socket, no timer: a dead loop). The pane, its socket dead and the link down,
        # awaits; each tick the shell's watchdog runs first (a no-op with no socket) and the pane's poll follows. connT
        # ages 5 s a tick; at 30 s the pane dials on its own and files its link-backstop row. With the stamp one line up,
        # before the guard, every tick renews connT with no socket to watch: the walk reads 0 for good and the backstop
        # never fires, a dead shell reading alive forever.
        r = _run_linked(r"""
shOpen();shRecv({type:'ka'});open();recv({type:"ka"});               // the shell's socket and the pane's, both OPEN and fresh
NOW+=5000;shTick();tick();                                            // one tick each with a socket: the shell's stamp is set once
shHide();hide();                                                      // the phone goes to the background (no ticks run while hidden)
NOW+=40000;sock().readyState=3;                                       // 45 s quiet: the pane's socket dead, the shell's quiet past the bound
global.WebSocket=function(){throw new Error('no socket');};         // the shell's redial cannot even construct a socket
shShow();                                                             // the shell's fast path: redial-stale, abandon, the dial throws
var shell={socks:SHSOCKS.length,timers:shDialTimers().length,up:global.__rompLink().up,stale:NOW-global.__rompLink().connT};
show();                                                               // the pane's return: its socket dead, the link down: await
var pane={sockets:sockets.length,awaiting:awaitLink};
var walk=[];
for(var i=0;i<6;i++){NOW+=5000;shTick();tick();walk.push({stale:NOW-global.__rompLink().connT,sockets:sockets.length,awaiting:awaitLink});}
if(sockets.length>1)open();                                           // the backstop's socket opens: its queued link-backstop row flushes onto it
out({shell:shell,pane:pane,walk:walk,backstop:rows(sock(),"link-backstop").length});""")
        self.assertEqual(r["shell"], {"socks": 1, "timers": 0, "up": False, "stale": 0},
                         "the shell's loop is dead: no socket, no pending redial, the link down, connT the abandon's dial time")
        self.assertEqual(r["pane"], {"sockets": 1, "awaiting": True}, "the pane awaits the link")
        self.assertEqual([w["stale"] for w in r["walk"]], [5000, 10000, 15000, 20000, 25000, 30000],
                         "with no socket to watch the tick does not renew connT: the stamp sits after the no-socket guard")
        self.assertEqual([w["sockets"] for w in r["walk"]], [1, 1, 1, 1, 1, 2], "at the bound (25,000 ms) no dial; past it the pane's backstop dials on its own")
        self.assertIs(r["walk"][5]["awaiting"], False)
        self.assertEqual(r["backstop"], 1, "...and files its loud link-backstop row")

    def test_a_shell_whose_loop_is_alive_publishes_its_fresh_dial_as_connT_and_the_pane_files_no_backstop(self):
        # tests-1: the dial half of the published maximum, connT: Math.max(shConnT, shTickT). Two reads where the halves
        # differ: the boot dial before any tick (the stamp unset: connT is the dial's age, 0), and the phone's return after
        # an hour in the background with no ticks (the stamp an hour old, the return's dial fresh). The pane returns in the
        # same dispatch, finds the link down (the shell's dial is CONNECTING) and awaits; its 5 s poll lands before the
        # shell's own watchdog has ticked since the return, a phase the two intervals can take, and reads connT 5 s old: no
        # backstop, no dial. The shell's socket then opens, the tell hands the pane the link-up word, and the pane dials
        # once on it (linkUpMs 5000) with no link-backstop row. With the dial half dropped (connT: shTickT) the boot read
        # is the unset stamp (1,000,000 ms) and the return read the hour-old tick: the pane's first poll files a false
        # link-backstop row and dials while the shell's loop is alive and dialing.
        r = _run_linked(r"""
var boot={stale:NOW-global.__rompLink().connT,socks:SHSOCKS.length,rs:SHSOCKS[0].readyState};   // the boot dial, CONNECTING, before any tick
shOpen();shRecv({type:'ka'});open();recv({type:"ka"});
for(var i=0;i<3;i++){NOW+=5000;shRecv({type:'ka'});recv({type:"ka"});shTick();tick();}   // 15 s of frames and ticks on both sockets: the stamp is set
shHide();hide();                                                      // the phone goes to the background: no ticks run while hidden
NOW+=3600000;SHSOCKS[0].readyState=3;sock().readyState=3;            // an hour later both sockets are dead
shShow();                                                             // the shell's fast path: redial-closed, a fresh dial (CONNECTING)
var atReturn={socks:SHSOCKS.length,rs:shSock().readyState,up:global.__rompLink().up,stale:NOW-global.__rompLink().connT};
show();                                                               // the pane's return: the link down, so it awaits
var pane={sockets:sockets.length,awaiting:awaitLink};
NOW+=5000;tick();                                                     // the pane's poll, before the shell's watchdog has ticked since the return
var afterPoll={sockets:sockets.length,awaiting:awaitLink,stale:NOW-global.__rompLink().connT};
shTick();                                                             // the shell's tick: its dial 5 s in, under the cut, kept
shOpen();                                                             // the shell's socket opens: the tell hands the pane the link-up word
var afterOpen={sockets:sockets.length,awaiting:awaitLink,up:global.__rompLink().up};
open();NOW+=50;recv({type:"feed",asks:[]});                           // the pane's socket opens; its return-fresh files on the first real frame
out({boot:boot,atReturn:atReturn,pane:pane,afterPoll:afterPoll,afterOpen:afterOpen,backstop:rows(sock(),"link-backstop").length,
rf:rows(sock(),"return-fresh").map(function(x){return x.data;})});""")
        self.assertEqual(r["boot"], {"stale": 0, "socks": 1, "rs": 0}, "before the first tick connT is the boot dial's age (the dial half of the max), not the unset stamp")
        self.assertEqual(r["atReturn"], {"socks": 2, "rs": 0, "up": False, "stale": 0}, "the return's fresh dial is connT, not the hour-old tick stamp")
        self.assertEqual(r["pane"], {"sockets": 1, "awaiting": True}, "the pane awaits the link (the shell's dial is CONNECTING)")
        self.assertEqual(r["afterPoll"], {"sockets": 1, "awaiting": True, "stale": 5000}, "the pane's poll reads the shell's dial 5 s old: the loop is alive, no backstop dial")
        self.assertEqual(r["afterOpen"], {"sockets": 2, "awaiting": False, "up": True}, "the link-up word dials the pane once")
        self.assertEqual(r["backstop"], 0, "no link-backstop row: the shell's loop was alive throughout")
        self.assertEqual(len(r["rf"]), 1)
        self.assertEqual(r["rf"][0]["linkUpMs"], 5000, "the word's time")


# ── the reconnect cue (iOS item 4, 2026-10-02): its detail line in the Log, and the glance composed with the shell ─────
# The detail is a live line the shell inserts before #rerr-list (so the Log's own re-render, which empties the list, leaves
# it alone). The fit harness's document answers no Log, so _CUE_PRE hands the shell a Log panel holding the list and an
# element factory; cueLine() reads the live line back: shown, its text, its place before the list, its role.
_CUE_PRE = r"""
const CUEPANEL = { children: [], insertBefore(n, ref) { const i = this.children.indexOf(ref); this.children.splice(i < 0 ? this.children.length : i, 0, n); n.parentNode = this; return n; } };
const cueEl = (tag) => { const e = { tagName: tag, id: '', className: '', src: '', alt: null, style: {}, attrs: {}, children: [], parentNode: null, textContent: '',
  setAttribute(k, v) { this.attrs[k] = String(v); }, appendChild(c) { this.children.push(c); c.parentNode = this; return c; } };
  Object.defineProperty(e, 'lastChild', { get() { return e.children.length ? e.children[e.children.length - 1] : null; } }); return e; };
const CUELIST = cueEl('div'); CUELIST.id = 'rerr-list'; CUEPANEL.children.push(CUELIST); CUELIST.parentNode = CUEPANEL;
const cueFitGet = global.document.getElementById;
global.document.getElementById = (id) => (id === 'rerr-list' ? CUELIST : cueFitGet(id));
global.document.createElement = (tag) => cueEl(tag);
global.cueLine = () => { const el = CUEPANEL.children.find((c) => c.id === 'rerr-live'); if (!el) return null;
  return { shown: el.style.display !== 'none', text: el.lastChild ? el.lastChild.textContent : null,
    beforeList: CUEPANEL.children.indexOf(el) < CUEPANEL.children.indexOf(CUELIST), role: el.attrs.role || null, cls: el.className,
    glyph: el.children[0] && el.children[0].children[0] ? el.children[0].children[0].className : null }; };
global.cueText = () => { const c = cueLine(); return c ? c.text : null; };   // null where no line was ever inserted (a head without the cue)
"""
# Nothing in the Log line runs on a timer (iOS item 4): each read of the line also samples the shell's live timers other than its
# redial (shellWS) and its interval count, and the shell's output carries the samples with the count at the case's start (CUEIV0, set
# by ReconnectCueDetail._run), so a clearing timer of any length armed at a cue event is caught at the next read, not only one short
# enough to fire inside a case. Runs after _CUE_PRE (it wraps cueLine; cueText reads through it).
_CUE_TIMERS = r"""
var CUETIMERS=[];
var cueLine0=global.cueLine;global.cueLine=function(){CUETIMERS.push({others:SHTIMERS.filter(function(t){return t.live&&t.fn.name!=='shellWS';}).map(function(t){return t.ms;}),intervals:SHINTERVALS.length});return cueLine0();};
var shOut0=shOut;shOut=function(o){o.cueTimers=CUETIMERS;o.cueIv0=CUEIV0;shOut0(o);};
"""
_CUE_WAIT = "Waiting for the kernel to respond. The dashboard updates on its own when it does."
_CUE_HUNG1 = "Trying again: the first try got no response."
_CUE_REFUSED1 = "Trying again: the first try could not connect to the kernel."


class ReconnectCueDetail(unittest.TestCase):
    """iOS item 4 (2026-10-02): the reconnect cue's detail, one tap from the glance (the Log's live first line). Shown while the
    shell's socket is down after it once opened, cleared at the next open with no success line, its every change keyed on the
    shell's own events (abandon, close, open). The two states a user sees after a return are pinned: the first try in flight
    (the wait line, no count) and, after the watchdog cuts it, the retry line that names the cause once. Refusals take the
    connect line, counted from the second. Run under node against the shell harness's fake socket and clock (ShellLinkProbe's)."""

    def _run(self, scenario):
        """Nothing in the line runs on a timer, at any length: every read of the line (cueLine, cueText) also samples the shell's
        live timers other than its redial (shellWS) and its interval count (_CUE_TIMERS), and every sample, one after each cue event
        a case reads, must show no such timer and the intervals the shell had when the case began (its watchdog tick)."""
        r = _run_probe("var CUEIV0=SHINTERVALS.length;\n" + scenario, pre=_CUE_PRE + _CUE_TIMERS)
        self.assertTrue(r["cueTimers"], "the line was read at least once, so the timers were sampled")
        self.assertEqual([c for c in r["cueTimers"] if c["others"] or c["intervals"] != r["cueIv0"]], [],
                         "no live timer but the shell's redial, and no new interval, after any cue event (a clearing timer of any length shows here)")
        return r

    def test_no_line_before_the_first_open_and_none_for_a_boot_dial_that_never_opened(self):
        r = self._run(r"""
var boot=cueLine();
shRefuseNow();var refused=cueLine();      // the boot dial refused: the page never had a link, the boot splash covers it
shFireDials();shOpen();var opened=cueLine();
shOut({boot:boot,refused:refused,opened:opened});""")
        self.assertIsNone(r["boot"], "nothing inserted before any socket event")
        self.assertEqual((r["refused"]["shown"], r["refused"]["text"]), (False, ""), "a boot dial that never opened is not a reconnect")
        self.assertEqual((r["opened"]["shown"], r["opened"]["text"]), (False, ""))

    def test_the_two_states_after_a_return_the_wait_then_the_cut_and_the_open_clears_it(self):
        r = self._run(r"""
shOpen();shRecv({type:'ka'});
shHide();SHSOCKS[0].readyState=3;SHNOW+=100;shShow();       // a return to a dead socket: the fast path abandons it and dials
var s1=cueLine();
SHNOW+=5000;shTick();var s1later=cueLine();                  // 5 s on, the first try still in flight: unchanged
SHNOW+=11000;shTick();var cutRs=SHSOCKS[1].readyState;       // past the 15 s cut: the watchdog closes the hung dial
SHSOCKS[1].onclose({code:1006});var s2=cueLine();            // its close: the retry line
shFireDials();var s2redial=cueLine();                        // the next try dials: the line stands
shOpen();var up=cueLine();                                   // the link is up: the line goes, with no success line
shOut({s1:s1,s1later:s1later,cutRs:cutRs,s2:s2,s2redial:s2redial,up:up,socks:SHSOCKS.length});""")
        self.assertEqual(r["s1"], {"shown": True, "text": _CUE_WAIT, "beforeList": True, "role": "status", "cls": "rerr-row", "glyph": "rnet-spin"},
                         "S1, the first state a user sees: the wait line, no count, at the top of the Log above its list, announced (role status), the romp swirl beside it")
        self.assertEqual(r["s1later"], r["s1"], "no change without an event: the shell's tick moves nothing")
        self.assertEqual(r["cutRs"], 3)
        self.assertEqual((r["s2"]["shown"], r["s2"]["text"]), (True, _CUE_HUNG1),
                         "S2, the second state: after the watchdog cut, the retry line naming the cause once")
        self.assertEqual(r["s2redial"], r["s2"])
        self.assertEqual((r["up"]["shown"], r["up"]["text"]), (False, ""), "the open clears it")
        self.assertEqual(r["socks"], 3)

    def test_refusals_take_the_connect_line_and_count_from_the_second(self):
        r = self._run(r"""
shOpen();shRecv({type:'ka'});
shHide();SHSOCKS[0].readyState=3;SHNOW+=100;shShow();
var lines=[cueText()];
for(var i=0;i<3;i++){shRefuseNow();lines.push(cueText());SHNOW+=1000;shFireDials();}
SHNOW+=16000;shTick();shSock().onclose({code:1006});lines.push(cueText());   // a cut after refusals: still the connect line
shFireDials();shOpen();
shOut({lines:lines,up:cueLine()});""")
        self.assertEqual(r["lines"], [_CUE_WAIT, _CUE_REFUSED1,
                                      "Trying again: 2 tries could not connect to the kernel.",
                                      "Trying again: 3 tries could not connect to the kernel.",
                                      "Trying again: 4 tries could not connect to the kernel."],
                         "a refused try names a connect failure; the count climbs from the second, and a mix keeps the connect line")
        self.assertEqual((r["up"]["shown"], r["up"]["text"]), (False, ""))

    def test_two_cuts_count_on_the_no_response_line(self):
        r = self._run(r"""
shOpen();shRecv({type:'ka'});
shHide();SHSOCKS[0].readyState=3;SHNOW+=100;shShow();
var lines=[];
for(var i=0;i<2;i++){SHNOW+=16000;shTick();shSock().onclose({code:1006});lines.push(cueText());shFireDials();}
shOut({lines:lines});""")
        self.assertEqual(r["lines"], [_CUE_HUNG1, "Trying again: 2 tries got no response."])

    def test_a_new_return_counts_from_zero(self):
        r = self._run(r"""
shOpen();shRecv({type:'ka'});
shHide();SHSOCKS[0].readyState=3;SHNOW+=100;shShow();
SHNOW+=16000;shTick();shSock().onclose({code:1006});var s2=cueText();
shFireDials();
shHide();SHNOW+=100;shShow();                                  // the page goes away and comes back while the next try hangs
shOut({s2:s2,again:cueText()});""")
        self.assertEqual(r["s2"], _CUE_HUNG1)
        self.assertEqual(r["again"], _CUE_WAIT, "the new return's fast path dials afresh: its first try, no count")

    def test_a_link_that_opens_drops_and_opens_again_moves_the_line_only_at_those_events(self):
        r = self._run(r"""
shOpen();shRecv({type:'ka'});
shHide();SHSOCKS[0].readyState=3;SHNOW+=100;shShow();
var seq=[];function at(k){var c=cueLine();seq.push(c?[k,c.shown,c.text]:[k,null,null]);}
at('return');SHNOW+=2000;shTick();at('tick');
shOpen();at('open');SHNOW+=5000;shRecv({type:'ka'});shTick();at('tick');
shSock().readyState=3;shSock().onclose({code:1006});at('drop');   // the opened socket drops: a new wait, its own count
SHNOW+=1000;shTick();at('tick');
shFireDials();shRefuseNow();at('refused');
SHNOW+=1000;shFireDials();shOpen();at('open');SHNOW+=5000;shRecv({type:'ka'});shTick();at('tick');
shOut({seq:seq});""")
        self.assertEqual(r["seq"], [["return", True, _CUE_WAIT], ["tick", True, _CUE_WAIT],
                                    ["open", False, ""], ["tick", False, ""],
                                    ["drop", True, _CUE_WAIT], ["tick", True, _CUE_WAIT],
                                    ["refused", True, _CUE_REFUSED1],
                                    ["open", False, ""], ["tick", False, ""]],
                         "each change at a link event (abandon, close, open); every tick between leaves the line as it was")

    # tests-2 of round 1: the count is zeroed whenever the line is off (shCue's reset), which covers two readers. A try counted
    # before an open must not carry into the wait after that socket drops: the refused try of a return, and the refused BOOT dial
    # (counted while the page had never opened, when the line cannot show), each followed by an open and a drop of the open socket
    def test_a_return_refused_then_opened_counts_the_next_drop_from_zero(self):
        r = self._run(r"""
shOpen();shRecv({type:'ka'});
shHide();SHSOCKS[0].readyState=3;SHNOW+=100;shShow();       // a return to a dead socket: the fast path dials
shRefuseNow();var refused=cueText();                         // the return's first try is refused: one try counted
SHNOW+=1000;shFireDials();shOpen();var opened=cueLine();     // the next try opens: the line goes, and its count with it
SHNOW+=5000;shRecv({type:'ka'});
shSock().readyState=3;shSock().onclose({code:1006});         // the opened socket drops: a new wait
shOut({refused:refused,opened:opened,drop:cueText()});""")
        self.assertEqual(r["refused"], _CUE_REFUSED1)
        self.assertEqual((r["opened"]["shown"], r["opened"]["text"]), (False, ""))
        self.assertEqual(r["drop"], _CUE_WAIT, "the drop after the open is a new wait with no tries yet (a stale count read 'the first try could not connect')")

    def test_a_refused_boot_dial_counts_nothing_toward_the_first_drop_after_the_open(self):
        r = self._run(r"""
shRefuseNow();                                               // the boot dial is refused: the page has never had a link
SHNOW+=1000;shFireDials();shOpen();                          // the next boot dial opens
SHNOW+=5000;shRecv({type:'ka'});
shSock().readyState=3;shSock().onclose({code:1006});         // the first drop after that open
shOut({drop:cueText()});""")
        self.assertEqual(r["drop"], _CUE_WAIT, "the boot's refused dial is not counted into the first wait after the open")

    # tests-4 of round 1: the cut's boundary. shCueCuts counts a never-opened close at least SH_CONNECT_MS after its dial, the
    # complement of the redial ladder's refused test, so both readers agree on a close at exactly the cut (delivered directly: the
    # watchdog's own close comes only past the cut) and on one a millisecond sooner
    def test_a_close_at_exactly_the_connect_cut_is_a_cut_and_one_a_millisecond_sooner_is_a_refusal(self):
        js = _mobile_js()
        cut = int(re.search(r"SH_CONNECT_MS=(\d+)", js).group(1))
        rung = int(re.search(r"SH_LADDER=\[(\d+)", js).group(1))
        got = {}
        for k, dt in (("sooner", cut - 1), ("at", cut)):
            got[k] = self._run(r"""
shOpen();shRecv({type:'ka'});
shHide();SHSOCKS[0].readyState=3;SHNOW+=100;shShow();       // the return: the fast path dials now
var T=SHNOW,s=shSock();
SHNOW=T+%d;s.readyState=3;s.onclose({code:1006});            // that dial's close, %d ms after it
shOut({line:cueText(),redial:shDialTimers().map(function(t){return t.ms;})});""" % (dt, dt))
        self.assertEqual(got["sooner"]["line"], _CUE_REFUSED1, "a close inside the cut is a refusal")
        self.assertEqual(got["at"]["line"], _CUE_HUNG1, "a close at exactly the cut is the cut's: 'got no response'")
        self.assertEqual(got["sooner"]["redial"], [rung], "the ladder reads the sooner close as a refusal too: its first rung")
        self.assertEqual(len(got["at"]["redial"]), 1)
        self.assertNotEqual(got["at"]["redial"], [rung], "...and the close at the cut as a cut, off the ladder: the two readers agree")

    def test_the_lines_are_the_drafted_copy_and_the_count_never_reaches_the_glance(self):
        js = _mobile_js()
        for text in (_CUE_WAIT, _CUE_HUNG1, _CUE_REFUSED1, "' tries got no response.'", "' tries could not connect to the kernel.'"):
            self.assertIn(text, js)
        spin = km._pane_spin("content", "live-ask")
        self.assertNotIn("shCue", spin, "the pane's badge reads nothing of the count")
        self.assertIn("reconnecting…</div>", spin)
        for dash in ("\u2014", "\u2013"):   # the em and en dash, as escapes
            for text in (_CUE_WAIT, _CUE_HUNG1, _CUE_REFUSED1):
                self.assertNotIn(dash, text, "no em or en dash in the copy")


# The glance composed with the shell (one node process, one clock): the shell script, one pane's shim and the pane's
# _pane_spin loader script, so the badge a case reads is driven by the shim's real wsdown, wsup and wsfresh and by the panes
# word the shell's real tell builds (_LINK_GLUE). The pane harness's dispatchEvent only records; here it also runs the
# listeners (the loader's), and the pane's document answers the loader's three elements: its sheet, its badge, and a content
# container with one thread (a drop over content raises the badge, not the sheet). snap(k) records the badge and the line.
_SPIN_BEFORE = r"""
var SPB=new Set(),SPS=new Set();
function spCls(S){return {add:function(c){S.add(c);},remove:function(c){S.delete(c);},contains:function(c){return S.has(c);},toggle:function(c,on){if(on)S.add(c);else S.delete(c);return !!on;}};}
var SPEL={"pane-spin":{classList:spCls(SPS)},"pane-reconn":{classList:spCls(SPB)},"content":{children:[{id:"thread-1"}]}};
// the glance carries no count: any write to the badge's text or children, from the pane's script or from the shell's, is recorded
// and every case asserts there was none (badgeWrites). The shell reaches the pane's document as a real page's would, through
// its iframe (document.querySelectorAll or getElementsByTagName), so a shell that wrote a count into the badge is caught here too.
var BADGEW=[];var SPRB=SPEL["pane-reconn"];
function spTrap(name){var n={};["nodeValue","textContent","data","innerHTML"].forEach(function(k){Object.defineProperty(n,k,{get:function(){return "reconnecting";},set:function(v){BADGEW.push(name+"."+k+"="+String(v));}});});return n;}
var SPKIDS=[spTrap("img"),spTrap("text")];
["textContent","innerHTML","innerText","outerHTML"].forEach(function(k){Object.defineProperty(SPRB,k,{get:function(){return "reconnecting";},set:function(v){BADGEW.push(k+"="+String(v));}});});
["appendChild","append","prepend","insertBefore","replaceChild","replaceChildren","replaceWith","insertAdjacentHTML","insertAdjacentText","insertAdjacentElement","removeChild","remove","before","after"].forEach(function(k){SPRB[k]=function(){BADGEW.push(k+"("+Array.prototype.map.call(arguments,String).join(",")+")");};});
[["childNodes",SPKIDS],["children",[SPKIDS[0]]],["firstChild",SPKIDS[0]],["lastChild",SPKIDS[1]],["firstElementChild",SPKIDS[0]],["lastElementChild",SPKIDS[0]]].forEach(function(kv){Object.defineProperty(SPRB,kv[0],{get:function(){return kv[1];}});});
var SPFRAME={id:"f-test",tagName:"IFRAME",contentDocument:document,contentWindow:window,getAttribute:function(){return null;}};
global.document.querySelectorAll=function(sel){return /iframe/i.test(String(sel))?[SPFRAME]:[];};
global.document.getElementsByTagName=function(t){return String(t).toLowerCase()==="iframe"?[SPFRAME]:[];};
document.getElementById=function(id){return SPEL[id]||null;};
window.dispatchEvent=function(e){winEvents.push(e.type);(winL[e.type]||[]).forEach(function(f){f(e);});return true;};
var SNAPS=[];function snap(k){var c=global.cueLine();SNAPS.push({k:k,badge:SPB.has("on"),line:c&&c.shown?c.text:""});}
function fireNamed(test){var n=0;timers.forEach(function(t){if(t.live&&test(t)){t.live=false;t.fn();n++;}});return n;}
function holdFires(){return fireNamed(function(t){return t.fn.name==="rpaint";});}
function failsafeFires(){return fireNamed(function(t){return t.ms===30000&&String(t.fn).indexOf("badge(false)")>=0;});}
function liveHolds(){return timers.filter(function(t){return t.live&&t.fn.name==="rpaint";}).length;}
"""


def _spin_script():
    js = km._pane_spin("content", "live-ask")
    return js[js.index("<script>") + len("<script>"):js.index("</script>")]


class ReconnectCueLinked(unittest.TestCase):
    """iOS item 4 (2026-10-02): the glance (the pane's badge) and the detail (the shell's Log line) across a whole return, on one
    clock, with the pane's loader script listening to the shim's real events and the shell's real link word. Pins the
    composition: the badge waits out the hold, stays up through the shell's cut and past 30 s while the link is down, and
    clears on the pane's first fresh frame after the link comes up; a healthy return paints nothing; a link that opens and
    drops again before any fresh frame keeps the badge up throughout."""

    def _run(self, scenario):
        r = _run_linked(_spin_script() + "\n" + scenario + "\nout({snaps:SNAPS,holds:liveHolds(),badgeWrites:BADGEW});", pre=_CUE_PRE, before=_SPIN_BEFORE)
        self.assertEqual(r["badgeWrites"], [], "nothing, the pane's script or the shell's, writes the badge's text or children: the glance carries no count")
        return r

    def test_a_hung_return_shows_the_cue_through_the_cut_and_past_30s_and_clears_after_link_up(self):
        r = self._run(r"""
shOpen();shRecv({type:'ka'});open();recv({type:"ka"});
shHide();hide();NOW+=40000;SHSOCKS[0].readyState=3;sock().readyState=3;
shShow();show();snap('return');                        // the shell dials (it hangs); the pane, link down, awaits it
holdFires();snap('hold');                              // the hold passes with no fresh frame: S1 painted
NOW+=16000;shTick();shSock().onclose({code:1006});snap('cut');   // the watchdog cuts the hung first try: S2
shFireDials();snap('redial');
NOW+=20000;failsafeFires();snap('past30');             // 36 s on: no failsafe stood armed, the badge stays
shOpen();snap('linkup');                               // the shell's socket opens: the link word dials the pane
open();snap('paneopen');
NOW+=50;recv({type:"feed",asks:[]});snap('fresh');""")
        self.assertEqual(r["snaps"], [
            {"k": "return", "badge": False, "line": _CUE_WAIT},
            {"k": "hold", "badge": True, "line": _CUE_WAIT},
            {"k": "cut", "badge": True, "line": _CUE_HUNG1},
            {"k": "redial", "badge": True, "line": _CUE_HUNG1},
            {"k": "past30", "badge": True, "line": _CUE_HUNG1},
            {"k": "linkup", "badge": True, "line": ""},
            {"k": "paneopen", "badge": True, "line": ""},
            {"k": "fresh", "badge": False, "line": ""}],
            "glance: held at the return, painted at the hold through the cut and past 30 s, cleared by the fresh frame; detail: "
            "the wait line, the cut line, gone at the link-up")
        self.assertEqual(r["holds"], 0)

    def test_a_healthy_return_paints_nothing(self):
        r = self._run(r"""
shOpen();shRecv({type:'ka'});open();recv({type:"ka"});
shHide();hide();NOW+=40000;SHSOCKS[0].readyState=3;sock().readyState=3;
shShow();show();snap('return');
NOW+=150;shOpen();snap('linkup');                      // the shell's dial opens at once, inside the hold
NOW+=100;open();NOW+=100;recv({type:"feed",asks:[]});snap('fresh');   // the pane dials, opens and gets its first frame
""")
        self.assertEqual([s["badge"] for s in r["snaps"]], [False, False, False], "no badge at any point of a return that links inside the hold")
        self.assertEqual([s["line"] for s in r["snaps"]], [_CUE_WAIT, "", ""], "the Log line lived from the return to the link-up")
        self.assertEqual(r["holds"], 0, "the fresh frame cancelled the hold")

    # ruling B of round 1 (2026-10-03), composed: in a pane that hears the real shell's link word, neither the link-up word nor the
    # pane's own reopen arms a failsafe, so a painted badge waits for the pane's first fresh frame however long it takes
    def test_after_the_link_up_and_the_panes_reopen_the_badge_waits_for_the_fresh_frame_however_long(self):
        r = self._run(r"""
shOpen();shRecv({type:'ka'});open();recv({type:"ka"});
shHide();hide();NOW+=40000;SHSOCKS[0].readyState=3;sock().readyState=3;
shShow();show();holdFires();snap('hold');               // painted at the hold
NOW+=3000;shOpen();snap('linkup');                     // the shell's socket opens: its link word reaches the pane
open();snap('paneopen');                               // the pane's own socket opens, and no frame comes yet
NOW+=40000;failsafeFires();snap('later');              // 40 s on: a failsafe armed at either event would fire here
NOW+=50;recv({type:"feed",asks:[]});snap('fresh');""")
        self.assertEqual([s["badge"] for s in r["snaps"]], [True, True, True, True, False],
                         "painted from the hold through the link-up and the reopen and 40 s past them; the fresh frame clears it")

    # fresh-1 of round 1, composed: a quick switch away and back with both sockets standing goes through the shim's and the shell's
    # keep paths, which dispatch no drop; the loader's visibility listener sees the page turn visible and must hold nothing
    def test_a_quick_switch_over_standing_sockets_paints_nothing(self):
        r = self._run(r"""
shOpen();shRecv({type:'ka'});open();recv({type:"ka"});
shHide();hide();NOW+=2000;shShow();show();snap('return');   // a quick switch: both sockets stand, the fast paths keep them
holdFires();snap('hold');
NOW+=40000;failsafeFires();snap('later');""")
        self.assertEqual([s["badge"] for s in r["snaps"]], [False, False, False], "no badge at the return, at a hold or later")
        self.assertEqual(r["holds"], 0)
        self.assertEqual([s["line"] for s in r["snaps"]], ["", "", ""], "and no Log line: the link never went down")

    def test_a_link_that_opens_and_drops_before_any_fresh_frame_keeps_the_badge_up_without_a_flap(self):
        r = self._run(r"""
shOpen();shRecv({type:'ka'});open();recv({type:"ka"});
shHide();hide();NOW+=40000;SHSOCKS[0].readyState=3;sock().readyState=3;
shShow();show();holdFires();snap('hold');
NOW+=3000;shOpen();open();snap('linked');              // the link and the pane's socket open, no fresh frame yet
NOW+=500;shSock().readyState=3;shSock().onclose({code:1006});snap('shelldrop');
sock().readyState=3;sock().onclose({code:1006});snap('panedrop');   // inside the return window, link down: the pane awaits
holdFires();snap('nohold');                            // nothing pending: a painted badge is never re-held by a drop
NOW+=2000;shFireDials();shOpen();snap('linkagain');
open();NOW+=50;recv({type:"feed",asks:[]});snap('fresh');""")
        self.assertEqual([s["badge"] for s in r["snaps"]], [True, True, True, True, True, True, False],
                         "painted from the hold to the fresh frame, through the open, both drops and the second link")
        self.assertEqual([s["line"] for s in r["snaps"]], [_CUE_WAIT, "", _CUE_WAIT, _CUE_WAIT, _CUE_WAIT, "", ""],
                         "the detail follows the shell's link at its own events")


# ── the lazy panes and the phone's skeleton first dial, shell + shim (stage 0, 2026-09-18) ────────────────────────
# The fit harness's element fakes carry no attributes, so the lazy-pane cases hand the shell richer ones (`pre`): six pane
# iframes with the served markup's src or data-src, a .pane parent each and a body that keeps data-tab. The pane's shim
# then runs where the document would load: after the tap (`before`), for a lazy pane; at the shell's boot, for the chat.
_LAZY_PRE = r"""
const ATTRS = {}, SRCSETS = [], DIVCLS = {}, LOADFNS = {};   // LOADFNS: the load listeners per frame, kept as functions so a case can fire the frame's load (review round 3, tests-3; LOADS keeps the ids as before)
const mk = (id) => { const k = id.slice(2), a = (k === 'chat') ? { src: '/' + k } : { 'data-src': '/' + k }; ATTRS[id] = a; DIVCLS[id] = new Set();   // the served markup: the chat alone ships src
  const dc = DIVCLS[id];
  return { id, parentNode: { classList: { add: (c) => dc.add(c), remove: (c) => dc.delete(c), contains: (c) => dc.has(c) } },
    classList: { toggle() {} }, contentDocument: {}, contentWindow: { addEventListener: () => {} },
    getAttribute: (x) => (x in a ? a[x] : null), setAttribute: (x, v) => { a[x] = v; if (x === 'src') SRCSETS.push(id); }, removeAttribute: (x) => { delete a[x]; },
    addEventListener: (x, f) => { if (x === 'load') { LOADS.push(id); (LOADFNS[id] = LOADFNS[id] || []).push(f); } } }; };
['f-chat', 'f-fleet', 'f-feed', 'f-timeline', 'f-waiting', 'f-files'].forEach((id) => { PANES[id] = mk(id); });
let TABNOW = null; const BODYCLS = new Set();
global.document.body = { setAttribute: (x, v) => { if (x === 'data-tab') TABNOW = v; }, getAttribute: (x) => (x === 'data-tab' ? TABNOW : null),
  classList: { toggle: (c, on) => { if (on) BODYCLS.add(c); else BODYCLS.delete(c); }, contains: (c) => BODYCLS.has(c) } };
global.__rompPaneEnabled = () => true;   // the head script's reader: every pane shown
global.lazySnap = () => ({ src: Object.fromEntries(Object.keys(ATTRS).map((id) => [id, ATTRS[id].src || null])), lazy: Object.fromEntries(Object.keys(ATTRS).map((id) => [id, ATTRS[id]['data-lazy-src'] || null])), sets: SRCSETS.slice() });
"""
# the pane reads the shell's REAL layout probe (as _LINK_GLUE points it at the shell's real link)
_MOBILE_GLUE = r"""Object.defineProperty(window.parent,"__rompMobileOn",{configurable:true,get:function(){return global.__rompMobileOn;}});
"""


class LazyPaneLinked(unittest.TestCase):
    """T1 (stage 0), shell + shim: a lazy pane has no src, so no document and no socket, until its tap; the tap sets the src once
    and the pane's shim, loading after it, dials one socket and hears the panes word saying it is on screen; from then on it is a
    pane like any other, parking at a return off screen (D2) and dialing on its tab (the linked harness of PR 768: one node
    process, one fake clock, the pane reading the shell's real publications). And the phone's first chat dial carries skeleton=1
    (the kernel's one-full-plus-statuses shape), where a standalone page, the VS Code webview or a desktop shell does not."""

    def test_a_lazy_pane_dials_nothing_until_its_tap_then_one_socket_and_parks_like_any_pane_after(self):
        r = _run_linked(app="waiting", pre=_LAZY_PRE, before=_MOBILE_GLUE + r"""
var t_boot=global.lazySnap();   // the shell booted (show('chat')): read before the tap
global.__rompMobileTab('waiting');   // the tap: the src is set, the document starts loading; the shim below is that document's
var t_afterTap={src:PANES['f-waiting'].getAttribute('src'),lazy:PANES['f-waiting'].getAttribute('data-lazy-src'),sets:SRCSETS.slice(),loading:DIVCLS['f-waiting'].has('loading'),bodyLoading:global.document.body.classList.contains('pane-loading')};
""", scenario=r"""
global.__rompPanesTell=function(){shellTell();fireWin("message",{romp:"panes",on:{waiting:global.document.body.getAttribute('data-tab')==='waiting'},link:global.__rompLink().up?"up":"down"});};   // the shell's tell carries the real on-screen word for this pane
var t_atLoad={sockets:sockets.length,url:sock().url,onScreen:onScreen};
shOpen();shRecv({type:'ka'});   // the shell's link is up
open();recv({type:"ka"});   // the pane's socket opens on the kernel
global.__rompPanesTell();    // the controller's load hook: the word on the pane's own load (the harness has no controller; the tell stands in)
var t_told={onScreen:onScreen,states:states().slice()};
global.__rompMobileTab('chat');   // the person goes back to the chat: the pane is off screen now
var t_away={onScreen:onScreen};
hide();NOW+=40000;sock().readyState=3;show();   // a return from the background with the socket dead: D2 parks a pane off screen on the phone
var t_parked={states:states().slice(),sockets:sockets.length};
shRecv({type:'ka'});   // the shell's own socket stands and is fresh (its return redial is ShellLinkProbe's business): the link reads up at the tap
global.__rompMobileTab('waiting');   // its tab again: the word shows it, it dials
var t_dialed=sockets.length;open();   // the kernel accepts the redial
var t_back={dialed:t_dialed,sockets:sockets.length,states:states().slice()};
out({boot:t_boot,afterTap:t_afterTap,atLoad:t_atLoad,told:t_told,away:t_away,parked:t_parked,back:t_back});   // t_ prefixed: the scenario shares the shim core's function scope, whose own `parked` a bare name would shadow""")
        self.assertEqual(r["boot"]["src"], {"f-chat": "/chat", "f-files": None, "f-feed": "/feed", "f-fleet": None, "f-timeline": None, "f-waiting": None},
                         "at the shell's boot on the phone the Waiting pane has no src (nor the Files pane): no document, no shim, no socket")
        self.assertEqual(r["boot"]["lazy"]["f-waiting"], "/waiting", "its data-src is parked for the tap")
        self.assertEqual(r["boot"]["sets"], ["f-feed"], "one src set at boot, the exempt feed's")
        self.assertEqual(r["afterTap"]["src"], "/waiting", "the tap sets it")
        self.assertIsNone(r["afterTap"]["lazy"])
        self.assertEqual(r["afterTap"]["sets"], ["f-feed", "f-waiting"], "exactly once")
        self.assertTrue(r["afterTap"]["loading"] and r["afterTap"]["bodyLoading"], "the shell paints its loader over the shown, loading pane")
        self.assertEqual(r["atLoad"]["sockets"], 1, "the document's shim dials one socket at its load")
        self.assertIn("app=waiting", r["atLoad"]["url"])
        self.assertIs(r["told"]["onScreen"], True, "the word on its load says the pane is on screen")
        self.assertEqual(r["told"]["states"], ["up"])
        self.assertIs(r["away"]["onScreen"], False, "the switch back to the chat re-tells: off screen")
        self.assertEqual(r["parked"], {"states": ["up", "parked"], "sockets": 1}, "a return off screen parks the pane (D2): no dial, one parked word")
        self.assertEqual(r["back"], {"dialed": 2, "sockets": 2, "states": ["up", "parked", "up"]}, "its tab shows it and it dials once, the shell's link being up; the open says up again")

    def test_the_shells_reader_and_the_real_shims_marker_agree_the_tapped_documents_load_is_the_panes_own(self):
        # tests-3 (review round 3, 2026-09-19): the shell's docState() decides a lazy pane loaded by the marker the pane shim sets in its window
        # (window.__rompApp), and before this nothing in a fast tier coupled the two: renaming the marker on either side left every Python and
        # webview test green and reddened the 80 s served Chromium leg alone. Here the REAL shim core runs in the pane scope after the tap, its
        # window glued in as the shell frame's contentWindow, and the shell's own promotion listener reads it on the frame's load.
        r = _run_linked(app="waiting", pre=_LAZY_PRE, before=_MOBILE_GLUE + r"""
global.__rompMobileTab('waiting');   // the tap: the src is set, the promotion listener armed; the shim below is that document's
PANES['f-waiting'].contentWindow=window;   // the pane's window IS the frame's contentWindow (before this glue the frame carried a bare fake)
PANES['f-waiting'].contentDocument={URL:'https://TESTHOST/waiting'};   // its document, committed at the pane's url
""", scenario=r"""
shOpen();shRecv({type:'ka'});   // the shell's socket is open: a clientDiag message would go out at once, so the read below sees any
var t_marker={type:typeof window.__rompApp,value:window.__rompApp};   // what the REAL shim set at its parse
var t_before={loading:DIVCLS['f-waiting'].has('loading'),failed:DIVCLS['f-waiting'].has('failed')};
(LOADFNS['f-waiting']||[]).forEach(function(f){f({type:'load'});});   // the frame's load event: the shell's listener reads the document
function diagAll(){var all=[];SHSOCKS.forEach(function(s){s.sent.forEach(function(x){var m=JSON.parse(x);if(m&&m.type==='clientDiag')all.push(m);});});return all;}   // every clientDiag message, any surface, any what
out({marker:t_marker,before:t_before,after:{loading:DIVCLS['f-waiting'].has('loading'),failed:DIVCLS['f-waiting'].has('failed')},
diag:diagAll(),listeners:(LOADFNS['f-waiting']||[]).length});""")
        self.assertEqual(r["marker"], {"type": "string", "value": "waiting"}, "the real shim set the marker on the pane's window at its parse (APP)")
        self.assertEqual(r["before"], {"loading": True, "failed": False}, "after the tap the pane is loading")
        self.assertGreaterEqual(r["listeners"], 1, "the shell's promotion listener is on the frame (a case over no listener would witness nothing)")
        self.assertEqual(r["after"], {"loading": False, "failed": False}, "the load: the shell read the pane's OWN document (docState 'app') and ended the loading state, no failure (a renamed marker on either side reads 'other' here, since this document carries no 200 stamp, and fails the pane: the red this pin exists for)")
        self.assertEqual(r["diag"], [], "no clientDiag message of any surface or what (the lazy panes post none since the reviewer's round 7)")
        # the belt beside the executed case: the two literals, so a rename that keeps the pair in step still shows up in a diff review
        self.assertIn("window.__rompApp=APP;", km._shim_core_js("waiting"), "the shim's marker line")
        self.assertIn("if(w&&typeof w.__rompApp==='string')return 'app';", km._LANDING_MOBILE_JS, "the shell's read of the same name (review round 4: the marker is read first, the kernel's 200 stamp tells doc from other after it)")

    def test_the_gears_tap_time_read_and_the_real_settings_shims_marker_agree_so_a_second_tap_toggles_the_live_page_and_fetches_nothing(self):
        # the author's pass-4 verify (2026-09-19, kernel-2's coupling): the gear's tap-time check reads window.__rompApp on the settings frame's
        # window, the marker the settings page's REAL shim sets (APP "settings"). The gear harness in tests/test_pane_state_broadcast.py
        # stubs the marker under whatever name the gear reads, and the linked case above couples the shim to the PANES' reader (docState),
        # not the gear's, so a rename kept in step on the shim and in docState and missed in the gear's read left every fast tier green
        # while every second gear tap on the real dashboard judged the live page not-live and fetched it again. Here the real settings
        # shim runs in the pane scope as the gear frame's contentWindow after the first tap's promotion, and the second tap reads it.
        settings_js = km._LANDING_SETTINGS_JS.replace("__ROMP_BOOT__", json.dumps("boot-1")).replace("__ROMP_LOADER__", json.dumps(""))
        r = _run_linked(app="settings", pre=_LAZY_PRE + "PANES['f-settings'] = mk('f-settings');\n" + settings_js + "\n", before=_MOBILE_GLUE + r"""
var GEARPOSTS=[];var gearListeners=function(){return (LOADFNS['f-settings']||[]).length;};var l0=gearListeners();   // the shell's panes-word hook is on the gear frame already (the mobile script wires the seven frames)
global.__rompOpenSettings();   // tap 1: the frame has no src, so the src is set once, the opener's one load listener armed, the ask pending
var t_tap1={src:ATTRS['f-settings'].src,sets:SRCSETS.filter(function(id){return id==='f-settings';}).length,armed:gearListeners()-l0};
PANES['f-settings'].contentWindow=window;   // the pane's window IS the gear frame's contentWindow; the shim below is the settings page's own
PANES['f-settings'].contentDocument={URL:'https://TESTHOST/settings'};   // its document, committed at the gear's url
window.postMessage=function(m){GEARPOSTS.push(JSON.parse(JSON.stringify(m)));};   // what the shell posts into the page
""", scenario=r"""
var t_marker={type:typeof window.__rompApp,value:window.__rompApp};   // what the REAL shim set at its parse
(LOADFNS['f-settings']||[]).forEach(function(f){f({type:'load'});});   // the page's load: the pending ask posts
var gearSets=function(){return SRCSETS.filter(function(id){return id==='f-settings';}).length;};
var t_loaded={posts:GEARPOSTS.slice(),sets:gearSets()};
global.__rompOpenSettings();   // tap 2 over the real, marked page: live, so no re-fetch; the ask posts (the page's own opener toggles)
var t_tap2={posts:GEARPOSTS.slice(),sets:gearSets(),src:ATTRS['f-settings'].src,armed:gearListeners()-l0};
out({tap1:t_tap1,marker:t_marker,loaded:t_loaded,tap2:t_tap2});""")
        self.assertEqual(r["tap1"], {"src": "/settings", "sets": 1, "armed": 1}, "the first tap promotes the gear frame once and arms the opener's one load listener (beside the shell's panes-word hook, wired at boot)")
        self.assertEqual(r["marker"], {"type": "string", "value": "settings"}, "the real shim set the marker on the settings page's window at its parse (APP)")
        self.assertEqual(r["loaded"], {"posts": [{"romp": "openSettings"}], "sets": 1}, "the page's load delivers the pending ask into the page")
        self.assertEqual(r["tap2"], {"posts": [{"romp": "openSettings"}, {"romp": "openSettings"}], "sets": 1, "src": "/settings", "armed": 1}, "the second tap reads the real page as live: zero more src sets (a re-fetch drops and sets it), the ask posts; a marker renamed on the shim alone, or in the gear's read alone, re-fetches here")
        # the belt beside the executed case: the two literals, so a rename that keeps the pair in step still shows up in a diff review
        self.assertIn("window.__rompApp=APP;", km._shim_core_js("settings"), "the shim's marker line")
        self.assertIn("typeof f.contentWindow.__rompApp==='string'", km._LANDING_SETTINGS_JS, "the gear's read of the same name (review round 4, kernel-2)")

    def test_the_phones_first_chat_dial_carries_skeleton_1_and_a_redial_or_another_layout_does_not(self):
        r = _run_linked(app="chat", pre=_LAZY_PRE, before=_MOBILE_GLUE, scenario=r"""
var first=sock().url;
open();recv({type:"ka"});sock().readyState=3;sock().onclose({code:1006});fireTimers();   // the socket dies before the bundle's ready was answered: the redial dials as a fresh page (the reload diet's rule)
var redial=sock().url;
out({first:first,redial:redial,sockets:sockets.length,mobile:parentMobile()});""")
        self.assertIs(r["mobile"], True, "the pane reads the shell's real layout probe (the fit harness's media query matches)")
        self.assertIn("app=chat&", r["first"])
        self.assertIn("&skeleton=1", r["first"], "the phone's first chat dial takes the skeleton diet: one full for the shown tab, a status per other tab")
        self.assertNotIn("reconnect=1", r["first"])
        self.assertEqual(r["sockets"], 2)
        self.assertNotIn("&skeleton=1", r["redial"], "a redial after a socket that died before the ready was answered dials as a fresh page, as the reload diet does (everConnected)")
        # the other layouts, pane-only, the shell's probe stubbed AFTER the harness (its `before` seam: the harness declares parentMobileVal
        # itself, so a `pre` write is reset; review round 1, 2026-09-19): a desktop shell says false, a standalone page or the VS Code webview
        # has none. The probe the core read at its load is asserted, so the desktop iteration is known to run a desktop shell.
        for before, mobile, why in (("parentMobileVal=false;", False, "a desktop shell"), ("", None, "no shell (standalone, VS Code)")):
            d = _run_pane('out({url:sock().url,mobile:(parentMobile()===undefined?null:parentMobile())});', before=before, app="chat")
            self.assertIs(d["mobile"], mobile, why + ": the probe the core read at its load")
            self.assertNotIn("skeleton=1", d["url"], why + ": the whole push, as before")
        js = km._shim_core_js("chat")
        self.assertIn('if(APP==="chat"&&!COL&&!SKEL&&parentMobile()===true)RESTART_DIET=true;', js, "the fork line sets the reload diet's flag; the dial line is upstream's text")
        self.assertLess(js.index("function parentMobile()"), js.index('RESTART_DIET=true;'), "after the probe it reads")
        self.assertLess(js.index('RESTART_DIET=true;'), js.index('?"&skeleton=1":""'), "before the dial line reads the flag")
        html = km._landing()
        probe = "window.__rompMobileOn=function(){try{return !!(window.matchMedia&&matchMedia(" + json.dumps(km._MOBILE_MQ) + ").matches);}catch(e){return false;}};"
        # read in the live scripts' code, through served_css.js_code (_live_scripts; the landing merge of main, 2026-09-30: the raw page's
        # spelling had stood for the definition, a read the census fails in a module on the parser road)
        held = [(el, code) for el, code in _live_scripts(html) if probe in code]
        self.assertEqual([code.count(probe) for el, code in held], [1], "the page defines the layout probe once: one live script holds it, once")
        at = held[0][0].content_start + held[0][1].index(probe)   # its offset in the page (js_code keeps offsets)
        self.assertLess(at, html.index("<iframe"), "…before any iframe, so a pane's shim can read it at its own load (the wid mint's race)")
        self.assertLess(at, html.index("window.__rompMobileOn=mobileOn;"), "…and the mobile script's cached-list version replaces it when the body's scripts run")


# The head's notified-session seed (review round 3, 2026-09-19, fresh-1), executed: the shell's head <script> under the auth
# test's harness (its stubs of the few browser globals the head touches) plus a Map-backed localStorage of this module's own.
from test_kernel_auth_hardening import _HEAD_HARNESS as _AUTH_HEAD_HARNESS   # noqa: E402  the harness, never its TestCases (the head script is read through the parser: _head_code)

_SEED_SID_A = "aaaaaaaa-1111-2222-3333-444444444444"   # web: the tab the phone was on when it buzzed
_SEED_SID_B = "bbbbbbbb-1111-2222-3333-444444444444"   # api: the session that buzzed
_SEED_KEY = "romp-vscode-state-chat"
_SEED_STORE = r"""
const STORE = new Map(); const SETS = [];
if (process.env.ROMP_TEST_BLOB) STORE.set(%s, process.env.ROMP_TEST_BLOB);
global.localStorage = {
  getItem: (k) => { if (process.env.ROMP_TEST_LS_THROWS) throw new Error("storage refused"); return STORE.has(k) ? STORE.get(k) : null; },
  setItem: (k, v) => { if (process.env.ROMP_TEST_LS_THROWS) throw new Error("storage refused"); SETS.push(k); STORE.set(k, String(v)); },
};
const QUERIES = [];   // the media queries the head's layout probe asked, in order
if (process.env.ROMP_TEST_LAYOUT !== "none") global.matchMedia = (q) => { QUERIES.push(q); return { matches: process.env.ROMP_TEST_LAYOUT === "phone", media: q }; };   // the layout the cell names (the harness's window is node's global)
""" % json.dumps(_SEED_KEY)
_SEED_DRIVER = "\nconsole.log(JSON.stringify({ replaced: REPLACED, blob: STORE.has(%s) ? STORE.get(%s) : null, sets: SETS, queries: QUERIES }));\n" % (json.dumps(_SEED_KEY), json.dumps(_SEED_KEY))


class NotifiedSessionSeed(unittest.TestCase):
    """A push notification's cold open lands on a URL carrying ?push-reveal=<sid>. The chat pane's shim dials at its own parse,
    before any body script, with the chat blob's activeId as the dial's hint (the LAST-SHOWN tab), and on the phone that first
    dial takes the skeleton diet: before this seed the kernel's one full went to the last-shown tab and the notified session
    arrived as a skeleton, one round trip later. The head script now seeds the blob with the notified session before the parser
    reaches the chat iframe, so the first dial names it. The seed runs on the phone layout alone (the reviewer's round-7 finding
    fresh-2: on a split desktop it moved the first column off its stored tab), so every cell names its layout: matchMedia answers the
    phone (the default), the desktop, or is absent. Executed here under node with a Map-backed store; the served legs
    (tests/test_notification_tap_resume_browser.py, the link road on the phone and on the desktop) read the dial off the wire."""

    def _run(self, href, blob=None, throws=False, layout="phone"):
        env = dict(os.environ, ROMP_TEST_HREF=href, ROMP_TEST_LAYOUT=layout)
        if blob is not None:
            env["ROMP_TEST_BLOB"] = json.dumps(blob)
        if throws:
            env["ROMP_TEST_LS_THROWS"] = "1"
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
            f.write(_AUTH_HEAD_HARNESS + _SEED_STORE + _head_code(_live_scripts(km._landing())) + _SEED_DRIVER)
            path = f.name
        try:
            r = subprocess.run(["node", path], capture_output=True, text=True, timeout=30, env=env)
        finally:
            os.unlink(path)
        self.assertEqual(r.returncode, 0, "the head script threw: " + r.stderr[:800])
        out = json.loads(r.stdout.strip().splitlines()[-1])
        out["blob"] = json.loads(out["blob"]) if out["blob"] is not None else None
        return out

    def test_a_deep_link_seeds_the_chat_blob_with_the_notified_session_before_the_token_scrub(self):
        was = {"activeId": _SEED_SID_A, "activeName": "web"}
        o = self._run("http://localhost:7777/?token=t&push-reveal=" + _SEED_SID_B, blob=was)
        self.assertEqual(o["blob"], {"activeId": _SEED_SID_B, "activeName": ""}, "the notified session is the stored tab now, its name unknown here (persistActive's shape): %r" % (o,))
        self.assertEqual(o["sets"], [_SEED_KEY], "one write, the chat blob's")
        self.assertEqual(o["replaced"], ["/?push-reveal=" + _SEED_SID_B], "the token scrub still ran after the seed, and the param stays for the reveal script")
        # a blob with other keys keeps them; a missing blob is minted; a host-prefixed id (a relayed remote event's sid) passes the shape
        o = self._run("http://localhost:7777/?push-reveal=" + _SEED_SID_B, blob={"activeId": _SEED_SID_A, "activeName": "web", "compact": True})
        self.assertEqual(o["blob"], {"activeId": _SEED_SID_B, "activeName": "", "compact": True})
        o = self._run("http://localhost:7777/?push-reveal=" + _SEED_SID_B)
        self.assertEqual(o["blob"], {"activeId": _SEED_SID_B, "activeName": ""}, "a first-ever open: the blob is minted with the notified session")
        o = self._run("http://localhost:7777/?push-reveal=TESTHOST:" + _SEED_SID_B, blob=was)
        self.assertEqual(o["blob"]["activeId"], "TESTHOST:" + _SEED_SID_B, "a host-prefixed id, as the dashboard carries a remote session")
        # a corrupt store reads as an empty blob and is rewritten with the notified session
        o = self._run("http://localhost:7777/?push-reveal=" + _SEED_SID_B, blob=[1, 2])
        self.assertEqual(o["blob"], {"activeId": _SEED_SID_B, "activeName": ""})

    def test_no_param_a_blob_already_naming_the_session_and_a_refused_value_write_nothing(self):
        was = {"activeId": _SEED_SID_A, "activeName": "web"}
        o = self._run("http://localhost:7777/?token=t&keep=1", blob=was)
        self.assertEqual((o["blob"], o["sets"], o["replaced"]), (was, [], ["/?keep=1"]), "no deep link: the blob is untouched")
        o = self._run("http://localhost:7777/?push-reveal=" + _SEED_SID_A, blob=was)
        self.assertEqual((o["blob"], o["sets"]), (was, []), "the blob already names the notified session: no write")
        # the refused inputs, recorded: a value outside push-card's shape (a quote), and one over 128 characters
        for bad in ("a%22b", "x" * 200, "a%20b", ""):
            o = self._run("http://localhost:7777/?token=t&push-reveal=" + bad, blob=was)
            self.assertEqual((o["blob"], o["sets"]), (was, []), "refused input %r left the blob alone: %r" % (bad, o))
            self.assertEqual(len(o["replaced"]), 1, "…and the token scrub still ran: %r" % (o,))

    def test_on_the_desktop_layout_a_deep_link_writes_nothing_to_the_chat_blob(self):
        # pin B(e) of the reviewer's round-7 ruling on fresh-2: the seed is gated on the head's layout probe, so a desktop cold open on
        # the link leaves the stored tab where it was (the first dial is main's) and the reveal lands the focus as it always did
        was = {"activeId": _SEED_SID_A, "activeName": "web"}
        o = self._run("http://localhost:7777/?token=t&push-reveal=" + _SEED_SID_B, blob=was, layout="desktop")
        self.assertEqual((o["blob"], o["sets"]), (was, []), "the desktop: no write, the stored tab stands: %r" % (o,))
        self.assertEqual(o["replaced"], ["/?push-reveal=" + _SEED_SID_B], "the token scrub still ran, and the param stays for the reveal script")
        self.assertEqual(o["queries"], [km._MOBILE_MQ], "the gate asked the layout probe, the shared media query, once: %r" % (o["queries"],))
        o = self._run("http://localhost:7777/?push-reveal=" + _SEED_SID_B, layout="desktop")
        self.assertEqual((o["blob"], o["sets"]), (None, []), "a first-ever desktop open mints no blob")
        o = self._run("http://localhost:7777/?push-reveal=" + _SEED_SID_B, blob=was, layout="none")
        self.assertEqual((o["blob"], o["sets"]), (was, []), "no matchMedia at all: the probe answers the desktop, and nothing is written")
        o = self._run("http://localhost:7777/?push-reveal=" + _SEED_SID_B, blob=was)
        self.assertEqual(o["blob"], {"activeId": _SEED_SID_B, "activeName": ""}, "the same link on the phone seeds as before (the control)")

    def test_a_storage_that_throws_leaves_the_token_scrub_standing(self):
        # a storage that refuses every call (the auth test's harness defines no localStorage at all, a ReferenceError; a browser
        # with storage blocked throws a SecurityError): the seed's own try/catch swallows it and the scrub after it still runs
        o = self._run("http://localhost:7777/?token=t&push-reveal=" + _SEED_SID_B, throws=True)
        self.assertEqual(o["replaced"], ["/?push-reveal=" + _SEED_SID_B], "the seed's own try/catch swallowed the throw and the scrub after it ran")
        self.assertEqual(o["sets"], [], "nothing was written through a refusing store")

    def test_the_seed_sits_in_the_head_after_the_layout_probe_and_before_the_standalone_flip(self):
        html = km._landing()
        head = _head_code(_live_scripts(html))
        seed = head.index("searchParams.get('push-reveal')")
        self.assertLess(head.index("window.__rompMobileOn=function(){"), seed, "after the layout probe (tests/test_per_viewer_focus.py pins the wid mint as the head's first statement)")
        self.assertLess(seed, head.index("if(navigator.standalone){"), "before the standalone flip")
        self.assertLess(seed, head.index("searchParams['delete']('token')"), "before the token scrub, as a statement of its own")
        self.assertEqual(html.count("<script>"), 22, "no new script element: the seed is a statement of the head script")
        self.assertLess(html.index("searchParams.get('push-reveal')"), html.index("<iframe"), "ahead of the first pane iframe, whose shim reads the blob at its parse")


if __name__ == "__main__":
    unittest.main()
