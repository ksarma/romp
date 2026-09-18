#!/usr/bin/env python3
"""Mobile shell: the combined landing page collapses to a one-pane-at-a-time tab switcher on a
narrow/touch viewport, and the kernel tells the shell to switch to Chat when a feed/timeline tap
brings the chat forward. Pure-HTML + routing asserts; no real session data.
"""
import json
import os
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


def _mobile_js():
    """The phone shell script AS THE PAGE RUNS IT: the served template itself. _landing() splices the layout probe's
    media query inline when the template is built (json.dumps(_MOBILE_MQ) in the template string), so there is no
    placeholder left for an executor to fill and the harness runs the template as served. Kept as the ONE door every
    executor class reads the script through, so a future splice is a one-line adoption here and nowhere else."""
    return km._LANDING_MOBILE_JS


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
        js = km._LANDING_MOBILE_JS
        # scale-aware (the user 2026-08-19): a desktop pinch shrinks vv.height by the zoom factor; height*scale
        # recovers the layout height, so a pinch never reads as "keyboard open" (or re-fits --app-h smaller)
        self.assertIn("function kbOpen(){var vv=window.visualViewport;return vv?(window.innerHeight-vv.height*(vv.scale||1)>120):false;}", js)
        # desktop (fine pointer) uses innerHeight outright — pinch-immune in every browser, no scale
        # arithmetic (desktop Firefox does not reliably report vv.scale during a pinch); the visual
        # viewport drives the fit only on coarse-pointer devices, where keyboards/toolbars live
        self.assertIn("var coarse=window.matchMedia&&matchMedia('(pointer: coarse)').matches;", js)
        self.assertIn("var h=(!coarse||!vv)?window.innerHeight:Math.round(vv.height*(vv.scale||1));", js)
        self.assertIn("--mtabs-h',(kbOpen()?0:(bar.offsetHeight||0))+'px'", js)

    def test_usage_modal_dismisses_via_a_real_backdrop_not_a_document_click(self):
        # the user 2026-07-22: on mobile the Usage panel got STUCK — an outside tap landed on a content
        # iframe (a different document), so the shell's document-level click listener never fired and the
        # modal never closed. Fix: a real full-screen backdrop in the SHELL document (like the net panel's
        # #rnet-back) catches the tap, so any tap over it dismisses. The #ru-tip is pointer-events:none, so
        # a tap that visually lands on the panel still reaches the backdrop underneath and closes it.
        html, js = km._landing(), km._LANDING_USAGE_JS
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
        i = html.index("@media (max-width:820px),(pointer:coarse)")
        mobile = html[i:i + 2000]
        self.assertIn("padding-right:0", mobile, "the mobile .col must cancel the desktop strip")

    def test_mobile_pane_has_explicit_height_not_auto(self):
        # regression: the mobile pane was sized with height:auto + bottom offset; mobile browsers read
        # height:auto on an iframe as "size to content" and collapse it (chat shrank to its tab bar).
        html = km._landing()
        self.assertIn("100dvh", html)                          # explicit, address-bar-aware viewport height
        self.assertNotIn("height:auto;display:none", html)     # the collapsing iframe rule is gone

    def test_shell_reserves_the_bar_height_so_it_cannot_cover_the_pane(self):
        # regression: a position:fixed bar overlapped the chat composer (which is why flex briefly replaced
        # it). The bar is fixed again — glued to the viewport bottom so no dead space can sit below it — but
        # now .col RESERVES the bar's measured height (--mtabs-h) as padding-bottom, so the iframes tile
        # ABOVE the bar and it can't cover the composer. One pane shows at a time, keyed off body[data-tab].
        html = km._landing()
        self.assertIn("padding-bottom:var(--mtabs-h", html)    # .col reserves the bar's height
        self.assertIn("--mtabs-h", km._LANDING_MOBILE_JS)      # ...measured from the live bar (offsetHeight)
        self.assertIn("#f-timeline.m-on{display:block}", html) # timeline is a mobile tab pane (it lives in the row now)
        self.assertIn("data-tab", km._LANDING_MOBILE_JS)       # show() marks the active pane on <body>

    def test_lazy_panes_markup_loader_and_the_promotions_place_in_show(self):
        # stage 0 (2026-09-18): the Waiting and Files panes are served with data-src (the mobile script promotes them: at boot on
        # the desktop, on their first tap on the phone; the Files line is the one upstream markup token this fork changes); the
        # chat keeps its src (the reveal landing reads its document). The shell's loader for a loading pane is one
        # element, painted for the shown tab by body.pane-loading inside the phone media block, in _pane_spin's dress.
        html = km._landing()
        js = km._LANDING_MOBILE_JS
        self.assertIn("<iframe id=f-waiting data-src=/waiting>", html)
        self.assertIn("<iframe id=f-chat class=m-on src=/chat>", html)
        self.assertIn("<iframe id=f-files data-src=/files>", html)
        self.assertNotIn("<iframe id=f-files src=", html)
        self.assertEqual(html.count("<div id=pane-load>"), 1)
        self.assertLess(html.index("<div id=romp-boot>"), html.index("<div id=pane-load>"))
        self.assertIn("#pane-load{display:none}", html)
        self.assertIn("#pane-load{position:fixed;left:0;right:0;top:0;bottom:var(--mtabs-h,2.6em);z-index:15;align-items:center;justify-content:center;background:#1e1e1e}", html)
        self.assertIn("body.pane-loading #pane-load{display:flex}", html)
        self.assertIn("body.theme-light #pane-load{background:#F1EAE2}", html)
        self.assertLess(html.index("@media " + km._MOBILE_MQ + "{"), html.index("body.pane-loading #pane-load{display:flex}"), "the paint lives inside the phone media block")
        self.assertLess(html.index("#pane-load{display:none}"), html.index("@media " + km._MOBILE_MQ + "{"), "hidden by default, outside it")
        self.assertEqual(html.count("<script>"), 21, "no new script element: the mobile script carries the lazy panes")
        # show(): the promotion sits between the persist and the re-tell (upstream's lines on both sides), so the pane hears the word on its load
        self.assertIn("try{localStorage.setItem(KT,p);}catch(e){}\ntry{if(mobileOn()){promote(p);paintLoading();}}catch(e){}", js)
        self.assertLess(js.index("try{if(mobileOn()){promote(p);paintLoading();}}catch(e){}"), js.index("try{window.__rompPanesTell&&window.__rompPanesTell();}catch(e){}}\nwindow.__rompMobileTab=show;"))
        # the boot: the parking of data-src runs before the boot show, whose line is upstream's text
        self.assertLess(js.index("lf.setAttribute(LAZY,lu);lf.removeAttribute('data-src');"), js.index("var last='chat';try{var s=localStorage.getItem(KT);if(s&&F[s])last=s;}catch(e){}show(last);"))
        self.assertIn("var LAZY='data-lazy-src',LOAD_MS=30000;", js)
        self.assertIn("window.__rompPanePromote=promote;", js)
        self.assertIn("if(en){if(f&&!f.getAttribute('src')&&f.getAttribute('data-src'))f.setAttribute('src',f.getAttribute('data-src'));", km._LANDING_COLLAPSE_JS, "the controller's promotion line is untouched")

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
        self.assertEqual(html.count("<script>"), 21)

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
        self.assertIn("setProperty('--mtabs-h'", km._LANDING_MOBILE_JS)
        self.assertIn("offsetHeight", km._LANDING_MOBILE_JS)

    def test_landing_disables_browser_pinch_zoom(self):
        # the top document governs pinch-zoom for the whole visual viewport (incl. the timeline iframe), so
        # it must disable page zoom or iOS page-zooms on a timeline pinch instead of running the gesture.
        html = km._landing()
        self.assertIn("user-scalable=no", html)
        self.assertIn("maximum-scale=1", html)

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
        self.assertIn("<meta name=viewport content='width=device-width,initial-scale=1,"
                      "maximum-scale=1,user-scalable=no,interactive-widget=resizes-content'>", html)   # the static meta: no cover
        self.assertEqual(html.count("viewport-fit=cover"), 1)         # exactly the runtime flip…
        self.assertIn("if(navigator.standalone)", html)               # …behind the iOS-standalone gate
        self.assertLess(html.index("if(navigator.standalone)"), html.index("viewport-fit=cover"))
        self.assertIn("100dvh", html)            # still address-bar-aware
        self.assertIn("user-scalable=no", html)  # pinch-zoom governance preserved alongside the change

    def test_keyboard_shrinks_content_and_never_strands_a_scroll(self):
        """The composer tap used to scroll the whole shell up behind the soft keyboard (the user
        2026-09-02): the viewport's default mode is resizes-visual — the keyboard PANS the visual
        viewport while innerHeight stands still, the UA slides the page up to reveal the input, and
        fit() re-lays the shrunken --app-h top-anchored into a window whose visible band starts a
        keyboard-height down; the composer sat off-screen until dragged back. Two halves, both
        pinned: interactive-widget=resizes-content makes engines that honor it (Android Chrome)
        SHRINK the layout viewport instead of panning, and fit() undoes the stray page offset iOS
        still forces (a UA input-reveal scroll bypasses overflow:hidden)."""
        self.assertIn("interactive-widget=resizes-content", km._landing())
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
        self.assertEqual(html.count("env(safe-area-inset"), 1)        # exactly the standalone rule below
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
        # kernel reads that file live, so pin the served page rather than a constant.
        css = km._timeline_page()
        self.assertIn("@media (pointer:coarse)", css)
        self.assertIn("overflow-x:hidden", css)
        self.assertIn("touch-action:pan-y", css)
        self.assertIn(".romp-tl-wrap svg{width:100%", css)


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
global.visualViewport = { height: 844, scale: 1, addEventListener: on(VV) };
const pane = (id) => ({ id, classList: { toggle() {} }, contentDocument: {},
  contentWindow: { addEventListener: on(id === 'f-chat' ? CHAT : {}) },
  addEventListener: (k) => { if (k === 'load') LOADS.push(id); } });
const PANES = { 'f-chat': pane('f-chat'), 'f-fleet': pane('f-fleet'), 'f-feed': pane('f-feed'), 'f-timeline': pane('f-timeline') };
const BAR = { offsetHeight: 44, querySelectorAll: () => [] };
global.document = {
  visibilityState: 'visible',
  addEventListener: on(DOC),
  documentElement: { scrollTop: 0, style: { setProperty: (k, v) => { PROPS[k] = v; SETS.push(k); } } },
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


def _run_probe(scenario):
    node = shutil.which("node")
    if not node:
        raise unittest.SkipTest("node not installed")
    fx = tempfile.mkdtemp()
    path = os.path.join(fx, "run.js")
    with open(path, "w") as f:
        f.write(_FIT_HARNESS + _SHELL_PROBE_HARNESS + _mobile_js() + "\n" + scenario)
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


# ── the lazy panes and the phone's skeleton first dial, shell + shim (stage 0, 2026-09-18) ────────────────────────
# The fit harness's element fakes carry no attributes, so the lazy-pane cases hand the shell richer ones (`pre`): six pane
# iframes with the served markup's src or data-src, a .pane parent each and a body that keeps data-tab. The pane's shim
# then runs where the document would load: after the tap (`before`), for a lazy pane; at the shell's boot, for the chat.
_LAZY_PRE = r"""
const ATTRS = {}, SRCSETS = [], DIVCLS = {};
const mk = (id) => { const k = id.slice(2), a = (k === 'chat') ? { src: '/' + k } : { 'data-src': '/' + k }; ATTRS[id] = a; DIVCLS[id] = new Set();   // the served markup: the chat alone ships src
  const dc = DIVCLS[id];
  return { id, parentNode: { classList: { add: (c) => dc.add(c), remove: (c) => dc.delete(c), contains: (c) => dc.has(c) } },
    classList: { toggle() {} }, contentDocument: {}, contentWindow: { addEventListener: () => {} },
    getAttribute: (x) => (x in a ? a[x] : null), setAttribute: (x, v) => { a[x] = v; if (x === 'src') SRCSETS.push(id); }, removeAttribute: (x) => { delete a[x]; },
    addEventListener: (x, f) => { if (x === 'load') LOADS.push(id); } }; };
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
        # the other layouts, pane-only (the shell's probe stubbed): a desktop shell says false, a standalone page or the VS Code webview has none
        for pre, why in (("parentMobileVal=false;", "a desktop shell"), ("", "no shell (standalone, VS Code)")):
            d = _run_pane('out({url:sock().url});', pre=pre, app="chat")
            self.assertNotIn("skeleton=1", d["url"], why + ": the whole push, as before")
        js = km._shim_core_js("chat")
        self.assertIn('if(APP==="chat"&&!COL&&!SKEL&&parentMobile()===true)RESTART_DIET=true;', js, "the fork line sets the reload diet's flag; the dial line is upstream's text")
        self.assertLess(js.index("function parentMobile()"), js.index('RESTART_DIET=true;'), "after the probe it reads")
        self.assertLess(js.index('RESTART_DIET=true;'), js.index('?"&skeleton=1":""'), "before the dial line reads the flag")
        html = km._landing()
        probe = "window.__rompMobileOn=function(){try{return !!(window.matchMedia&&matchMedia(" + json.dumps(km._MOBILE_MQ) + ").matches);}catch(e){return false;}};"
        self.assertEqual(html.count(probe), 1, "the head defines the layout probe once")
        self.assertLess(html.index(probe), html.index("<iframe"), "…before any iframe, so a pane's shim can read it at its own load (the wid mint's race)")
        self.assertLess(html.index(probe), html.index("window.__rompMobileOn=mobileOn;"), "…and the mobile script's cached-list version replaces it when the body's scripts run")


if __name__ == "__main__":
    unittest.main()
