#!/usr/bin/env python3
"""The phone layout's bottom bar (#mtabs) keeps every control on screen and under a finger at every phone width, in one
row from 360 to 430px, with Usage, Remote kernels and Restart kernel one tap away in the settings card (iOS item 4g,
2026-10-04 and 10-05).

THE BUG. The bar is one flex row: the pane tabs (each flex:1, never narrower than its label, 8px apart) and then the action
cluster, a divider and buttons that never shrink, each a glyph in 7px of side padding, 28 to 32px wide. There were six
(Usage, Remote kernels, Restart, the Log's triangle, the push bell and Settings), and the bell is not capability-gated (the
shell's push script reveals it on every page since it became the master switch), so it is always one of them. With the
default tabs (Chat, Sessions, Outline, Feed, Waiting) the row needed 418px in Chromium and 413px in WebKit and Firefox
(454 and 448px with the Files tab on), nothing in it could shrink or wrap, and the bar does not scroll (overflow visible,
in the shell's overflow:hidden body), so on a narrower window the cluster ran past the right edge of the screen out of
reach: at 390px Settings, at 360 the bell too, at 320 the Log's triangle as well, in all three engines.

THE FIX (kernel/kernel.py, the shell's markup and its phone media block; ui/webview/gear.js and gear.css, the settings
card). Two parts, as romp-manager ruled before round 1 (2026-10-05): keep ONE ROW where it can fit by moving actions, and
wrap only where it still cannot.
- The move. Usage, Remote kernels and Restart kernel left the bar. Usage and Remote kernels are its two panels about the
  machinery (spend and limits, other machines' kernels), not about the sessions; moving those two is the smallest move that
  gives one row from 375 to 430px in all three engines (measured at the wrap-only head by hiding each set of actions in the
  served bar: either one alone leaves 386px in Chromium; the two leave 354px in Chromium and 349 to 350px in WebKit and
  Firefox, and 390 and 384 to 385px with the Files tab on). Restart followed them (romp-manager's call 3, 2026-10-05): the
  kernel's restart is machinery too, rarely used and costly to hit by accident, and with it gone the default row needs 322px
  in Chromium and 318px in WebKit and Firefox (358 and 353px with the Files tab on), so the bar is one row at every phone
  width from 360px with the Files tab on or off. The bell stays on the bar. The three now sit in the settings card, a row of
  buttons under its title, above the tabs (so whichever tab the card opens at shows them), shown only on the phone layout
  and only where the shell publishes the marker beside the listener that runs them (window.__rompPhoneActs), so a phone
  shell still running a build from before the move, which has the three on its bar, gets no row whose taps run nothing.
  One click on the bar's Settings opens the card, one click on the button closes the card and runs the handler the bar's
  button ran (the shell's A-map, reached by a phoneAct message from the settings document, whose accepted acts are exactly
  the three), so Usage opens its modal, Remote kernels its panel and Restart kernel the kernel's restart (POST /restart), as
  before. They are buttons in a card, so they wear the card's button vocabulary, the dress of its other word buttons
  (Customize shortcuts' rules, copied), not the menu vocabulary of a dropdown's rows. The Remote kernels glyph keeps its
  live state there: the shell's /tunnels poll paints the card's copy as it painted the bar's (connected, attaching, each
  node's colour, the drop flash), and the card's opening brings it in step with the rail's glyph (the rail icon's live
  classes and the last poll's node colours; tests/test_remotes_panel_render.py holds that the opening paints nothing on the
  rail, so an Attach in flight keeps its busy there and the card shows it too). The drop flash plays only where the
  card is open at the drop: a closed card runs no animation, so the class a drop left on its copy is cleared when the card
  opens, where it would otherwise play the flash late. Usage explains rather than hides when it has nothing to show
  (romp-manager's call 6): the shell's usage panel opens only over a reading, so with none the card shows Usage disabled
  with the line "No reading yet" under its name, and a tap on it leaves the card open; with a reading, Usage is enabled and
  opens the panel. The card reads the source the panel's opener reads: each opening asks the shell for a fresh pull
  (window.__rompUsagePull, the usage script's own fetch of its readings), Usage shows the romp loader and takes no tap until it ends, and
  then the card asks the usage script's own test over its readings (window.__rompUsageReading, the check the panel's opener
  makes); the shell's renderRows, the one writer of those readings, tells an open card on every change, so a reading that
  lands while the card is open shows at once; a shell that cannot be asked leaves Usage enabled with no line, as its bar button was. The Remote kernels glyph wears the accent while a host is connected or attaching, on the glyph
  alone as on the rail, and the button's label keeps the card's text colour (PR 976's round 1, ui-3). The glyph sits on its
  button's own fill, which the button keeps on hover, its border and label still turning accent (round 1, extra6-2), and
  every colour it wears reads at 3:1 or more (a graphic, romp-manager's call 7) on the card and on that fill, at rest and
  hovered, in both themes: in the light theme its dialing grey and
  needs-you red are darker than the shell's (feed.css's --rn-wait and --rn-warn, #777777 and #db3d5a where the shell has
  #8a8a8a and #e5484d, which read 2.59 and 2.94:1 on that theme's button fill, #e7ded2). The red is turned in hue too,
  from the shell's 23 degrees to 15 in OKLCH, so it stays as far from the connected node's clay (#c2410c) as the shell's
  red is: 9.04 in OKLab distance x100, where the shell's has 8.94 (romp-manager's call 1 at round 1).
- The fallback. The action cluster is one element (.mtabs-acts) and the bar may wrap: where the tabs and the three actions
  left do not fit one row (below 322px in Chromium and 318px in WebKit and Firefox, so at 320px in Chromium and not in the
  other two; below 358px in Chromium and 353px in WebKit and Firefox with the Files tab on, so at 320px in all three), the
  cluster moves whole to a second row under the tabs, at the right edge, and the tabs take the full first row at the single
  row's height. A wrapped bar is taller, and its height can change
  with no resize at all (the Files tab turned on in the gear), so the shell re-measures the strip the panes leave for it
  whenever the bar's box changes (a ResizeObserver on the bar, beside the resize events that already re-measure it).
The desktop is untouched: the bar is display:none outside the phone media block, and the rail keeps its actions.

WHAT IS MEASURED, in the pages the kernel serves, in a real engine (tests/mtabs_fit_browser.mjs): the iPhone 14 descriptor
(Firefox without isMobile, which Playwright does not support there) at 320, 360, 375, 390, 414 and 430px wide in portrait
and the same phones in landscape, on the default tab set and with the Files tab on. Wherever the phone layout applies, for
every control the bar shows: its box wholly inside the window, the element at its centre is that control, no two controls
overlap, a tab's label fits inside it, every control keeps at least its natural width (its width in the unsqueezed row) and
the single row's height, the bar spans the window at its bottom edge and nothing in it overflows, and the strip the panes
leave (--mtabs-h) equals the bar's height with the shown pane ending above it. The bar shows three action buttons (the Log's
triangle, the bell, Settings) and no Usage, Remote kernels or Restart kernel. In portrait the bar IS one row on the default
set at 360, 375, 390, 414 and 430px and on the Files set at 375 to 430px (ONE_ROW: its natural width fits, every control on
it, the bar one control tall, so the panes keep all but that one row), and IS the fallback on the Files set at 320px
(FALLBACK: the natural row does not fit, the tabs fill the first row and the cluster sits together on the second at the
right edge). Elsewhere the bar is one row exactly where its natural one-row width (the bar laid out at max-content without
wrapping) fits. Then the Files tab turned on with no resize, at 340px where the default set fits one row and the Files set
does not: the bar wraps and the strip follows it. Then the moved actions, at 390px: the bar's Settings clicked at its centre
opens the card; its row of three buttons shows, each wholly in the window and the card and hit at its centre, and each
wearing Customize shortcuts' dress at rest (its computed fill, hairline, radius, text colour, padding, font and press
transition equal #rs-keys-btn's, the Remote kernels button's text colour too while the poll lights its glyph, read once
Usage's colour transition ends), Usage enabled with its line hidden (the lab's reading); the Remote kernels glyph wears the
state the shell's poll painted on the rail's glyph (the shell's own GET /tunnels answers two synthetic hosts, one connected
and one with no kernel: the glyph on, its nodes needs you and connected, the same classes, colours and fills as the rail's);
the shell's next poll is held until after the first opening, so the card's paint is the opening's own, and when it is
released with both hosts connected the card's copy follows it; then one click on Usage closes the card and opens the Usage
modal (the lab's usage.json makes it a spend reading, so the panel has something to show), and after the bar's Settings
again, one click on Remote kernels closes the card and opens the Remote kernels panel, and after it again, one click on
Restart kernel closes the card and makes the shell's one POST /restart (the driver answers it with a refusal in the
manager's shape, RESTART_REFUSAL, so the lab kernel stays up, and the shell's handler takes it: its splash down, the
refusal's words on the rail's restart button); no click but that one makes a POST /restart. Then the drop cue (TUNNELS_DROP,
a host that was up answering with no kernel): with the card closed the poll drops the host, and at the card's next opening
its glyph carries no flash; then the host comes back and drops again with the card open, and the glyph's flash runs; then
the host comes back again, the Token usage panel opens over the card (#ra-open, which hides the card with no message to the
shell), the host drops while the panel is up, the panel closes (#ra-close), and two frames after the card shows again its
glyph carries no flash. Then
Usage with no reading, on a page whose shell's usage pull (its GET under /usage/) answers no rows (the rail's readout, which
renders over the readings, read empty as the leg's premise): the card opened from the bar's Settings shows Usage disabled
with the line USAGE_NONE once the opening's ask for a fresh reading has ended; a click at its centre leaves the card open,
opens no Usage modal and posts no phoneAct (read after a settle: an absence has no event to wait on), and the line still
shows; then, the card still open, a reading arrives (the lab's own GET /usage payload posted to the shell as the timeline
posts it, the shell's later pulls let through), and the open card shows Usage enabled with no line; the readings emptied (a
payload with no window and no spend, posted the same way) show it disabled with its line in the open card, filled again
enabled with no line; and one click closes the card, posts phoneAct usage and opens the Usage modal. Then a reading the kernel holds and the shell has not pulled, on a page
of its own at 390px: the shell's boot pull answers no rows and every later pull reaches the lab, with the Sessions pane
unloaded so no timeline forwards a reading (both read as the premise); the card's opening asks the shell for a pull (a GET
under /usage/ after the opening), and while that request is held Usage shows the romp loader in its sub-line's place (the
swirl spinning, the wordmark, the dots pulsing), disabled and busy, with no line; let through, the ask ends with Usage
enabled, no line and no loader, and one click closes the card, posts phoneAct usage and opens the Usage modal. Then the
deploy skew, on a page of its own at 390px: the shell publishes its marker (window.__rompPhoneActs) and the card opened
from the bar's Settings shows its row; with the marker deleted (the phone layout and no marker, as a shell from before the
move has) the card opened shows no row (not displayed, its buttons boxless); and with the marker back and the usage script's
two names deleted (__rompUsageReading and __rompUsagePull, a shell that cannot be asked) the card's Usage is enabled with no
line. Then the row following the layout while the card is open, on a page of its own in a plain context (a fine pointer, so
the layout turns at 820px), the shell's poll answering both hosts up: the card opened at 390px shows its row; the window
widened to WIDE with the card open hides it (not displayed, its buttons boxless), a host drops there (the class left on the
hidden glyph, the premise), and the window narrowed to 390px again shows the row, its glyph carrying no flash two frames on,
and Usage enabled with no line once the ask the row's return makes has ended. Then the
Remote kernels glyph's colours in the dark and the light theme (THEMES), each on a page of its own at 390px: in the card
opened from the bar's Settings, every colour the glyph can wear (GLYPH: the glyph lit and attaching, read on its svg, a node connected,
dialing and needs you) reads at GLYPH_FLOOR or more against the card's background and against the button's fill, each
colour read with its class set and the element's transitions off; and again with the pointer moved onto the button (its
transitions off), against the fill it wears hovered, :hover read as the premise; and the needs-you red stays
SEPARATION_FLOOR or more from the connected node's colour in OKLab. Then a desktop window, where the bar is hidden, and the desktop rail at 821 and 1100px, whose actions (restart, Remote kernels, the bell,
the gear) and their boxes equal af7d18250's (RAIL_AF7 below), and where the settings card, opened from the rail's gear
clicked at its centre, shows no row of moved actions (not displayed, its buttons boxless: the rail has its own).
MTABS_FIT_DUMP, a directory, keeps each engine's raw readings there.

Red at the wrap-only head, in all three engines: its bar shows six actions, it wraps where one row is owed (at 375 and
390px, and at 414 in Chromium; its row fits 414 in WebKit and Firefox and 430 in all three), and its card has no row of
moved actions. Red at the two-action move (Usage and Remote kernels moved, Restart still on the bar), in all three engines:
its bar shows Restart, its Files set wraps at 375px, and its card has no Restart kernel button. The phoneAct pin is red
under the listener's old accepted set (net and usage alone): the card's Restart kernel closes the card and no POST /restart
follows. The button dress's pin is red at the menu dress the row wore before (the menu card's fill, a 6px radius, 5px 10px
of padding, 12px text), and where the accent lights the whole Remote kernels button, its label too (the rule before round
1's ui-3). The no-reading pins are red at the card without that state (Usage enabled with no reading, and its
tap closing the card to open nothing); the reading landing in the open card is red where the card reads the state only when
it opens, and the emptying where the shell's renderRows tells the card only as it fills its readings; the unpulled reading is red where the card answers from the shell's cached readings without a pull (Usage
disabled with its line, no loader, the tap opening nothing). The fallback's pin is red under the old rule restored (no wrap), and the
rail's under the move applied to the rail as well; the desktop card's under a mutant that shows the row on every layout
(romp-manager's call 8). The drop cue's pin is red at the commit before its fix, where a drop that came while the card was
closed flashed the glyph at the card's next opening; the Token usage panel's is red without the panel close's clear of the
class (gear.js raHide), where the glyph flashed as the panel closed. The deploy skew's pins are red where the shell
publishes no marker, where the card reads the layout alone (its row shown with no marker), and where a shell that cannot be
asked reads as one with no reading (Usage disabled with its line). The layout leg is red where the card reads the layout
only when it opens (the row still shown in the widened window), and its glyph line red without the clear of the drop's class
when the row shows again (the flash then plays at the narrowing). The contrast pin is red at the shell's literals in the light theme, in
all three engines: the dialing grey #8a8a8a reads 2.59:1 and the needs-you red #e5484d 2.94:1 on the button's fill; its
hovered half is red where the button takes the row's accent wash on hover, on which the dark needs-you red reads 2.95:1;
and the separation's pin is red at the darker red the light theme had at the shell's hue, #dc3f46, 7.10 from the clay. Runs in the "Browser-backed served-page tests (pytest)" step of the
served-pages job, "Served pages (pytest, ubuntu-latest)" (ci.yml, ROMP_SERVED_TESTS_REQUIRE=1: a skip here is a failure), in
Chromium; the WebKit and Firefox legs are `optional:` skips where that engine is absent or not declared in
ROMP_SERVED_TESTS_ENGINES (CI declares chromium; a developer's box runs all three).

The lab: one kernel from test_ship_reship_served.kernel_env (a private XDG root, `session-hosts` floored off,
ROMP_MANAGER_PORT=1, no catalog or update fetch, a hermetic postal bus), its port from tests/lab_ports.py and proved its own
there, a private dist (lab_dist.copy_dist), no sessions, and a usage.json that marks the machine as an API-key one (the
Usage modal's spend reading, zeros). The driver asserts /healthz on the lab's port before any request. Synthetic throughout.
"""
import json
import lab_dist
import lab_ports
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
EXT = os.path.join(ROOT, "vscode-extension")
sys.path.insert(0, HERE)
import test_ship_reship_served as _lab   # noqa: E402  (kernel_env: every lab kernel's environment; the module, not its classes)

# Hermetic state BEFORE anything: this module loads no romp code in-process (the kernel is a subprocess under kernel_env's
# roots), but the floor costs two lines and a later edit that adds a load must not write real state.
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
os.makedirs(os.path.join(os.environ["XDG_STATE_HOME"], "romp"), exist_ok=True)
Path(os.environ["XDG_STATE_HOME"], "romp", "session-hosts").write_text("off\n")   # the Testing rule for a test that mints its own root

DRIVER = os.path.join(HERE, "mtabs_fit_browser.mjs")
# the phones: width by height in portrait (320 the narrowest, 430 the widest), and the same phones turned to landscape
PORTRAIT = ((320, 568), (360, 640), (375, 667), (390, 844), (414, 896), (430, 932))
LANDSCAPE = tuple((h, w) for w, h in PORTRAIT)
# the portrait widths where each tab set is ONE row in every engine: the ruling's 375 to 430px, and 360 for the default set,
# whose row needs 322px at most (measured in the three engines); the Files set needs 358px at most, 2px inside 360, so 360 is
# a measured figure for it and not a pin (the gear's glyph is a fallback font's, whose width can differ between machines)
ONE_ROW = {"default": (360, 375, 390, 414, 430), "files": (375, 390, 414, 430)}
FALLBACK = {"files": 320}   # ...and the two-row fallback, owed in every engine: the Files set at 320px (the default set's row
                            # fits 320 in WebKit and Firefox and not in Chromium, so its shape there is held by the natural row)
DYNAMIC = (340, 640)   # the default tabs fit one row here and the Files set does not (asserted, so the leg proves a wrap)
ACTS = (390, 844)      # the phone the moved actions are clicked on
MOVED = ("usage", "net", "restart")        # the three actions that left the bar for the settings card, in the card's order
BAR_ACTS = ("merr", "mbell", "settings")   # the three left on it, in their order
# the lab's answer to the shell's POST /restart in the moved-actions leg (the driver answers it; the kernel never sees it): the
# manager's refusal shape, so the shell's restart handler runs to its end (splash down, these words on the rail's button)
RESTART_REFUSAL = "synthetic refusal: the lab kernel stays up"
USAGE_NONE = "No reading yet"   # the card's line under a disabled Usage (gear.js), the words a person reads
# the themes the Remote kernels glyph's colours are measured in, by the gear's theme ids: the dark default and the light theme
# (no rule in feed.css or gear.css reads the Yatharth dark theme's class, so the default stands for both dark themes)
THEMES = (("dark", "classic"), ("light", "yatharth-light"))
GLYPH = ("lit", "attaching", "connected", "dialing", "needs you")   # every colour the glyph can wear, as the driver names them
GLYPH_FLOOR = 3.0   # the contrast a graphic needs (WCAG's non-text 3:1), against the card's background and the button's fill
# ...and how far the needs-you red stays from the connected node's colour, as OKLab distance x100 (romp-manager's call 1 at
# PR 976's round 1): at least the separation the shell's own pair has in the light theme, #e5484d from the clay #c2410c,
# 8.94, so the light card's darker red tells the two states apart no worse than the shell does (the same red darker at the
# shell's hue was 7.10)
SEPARATION_FLOOR = 8.9
DESKTOP = (1280, 800)
WIDE = (900, 844)   # the window the layout leg widens to with the card open: past the phone query's 820px, in a fine-pointer context
RAIL = ((821, 800), (1100, 800))   # the desktop rail: just past the phone query's 820px, and a laptop
# the shell's own /tunnels poll in the moved-actions leg: two synthetic hosts, one connected and one with no kernel (the glyph
# on, its nodes the worst two: needs you, connected), then both connected (every node connected)
TUNNELS = {"tunnels": [{"host": "TESTHOST", "status": "up"}, {"host": "PEERHOST", "status": "no-kernel"}],
           "peersMode": False, "autoUpdate": False, "local": {"host": "", "ver": "", "sha": ""}}
TUNNELS2 = {"tunnels": [{"host": "TESTHOST", "status": "up"}, {"host": "PEERHOST", "status": "up"}],
            "peersMode": False, "autoUpdate": False, "local": {"host": "", "ver": "", "sha": ""}}
# ...and the drop: PEERHOST, up in TUNNELS2, answers with no kernel, so that poll is a host dropping (the glyph's flash)
TUNNELS_DROP = {"tunnels": [{"host": "TESTHOST", "status": "up"}, {"host": "PEERHOST", "status": "no-kernel"}],
                "peersMode": False, "autoUpdate": False, "local": {"host": "", "ver": "", "sha": ""}}
# The desktop rail at af7d18250 (fork main, before this PR), read by this module's driver against that tree in this lab: the
# shown actions in order, each with its width, height and top, and its left and right edges as offsets from the gear's left
# edge; for the gear itself its right edge as an offset from the window's right edge, its top and height. The gear is a text
# glyph (U+26ED) that Inter does not carry, so its width is a fallback font's and differs between engines (15, 15.2 and
# 15.37px) and can differ between machines; holding the others from its left edge keeps every other quantity exact. The
# values were the same in Chromium, WebKit and Firefox and at both widths (821x800 and 1100x800).
RAIL_AF7 = (
    {"id": "rail-refresh", "w": 18, "h": 26, "top": 772.5, "left": -96, "right": -78},
    {"id": "rail-net", "w": 18, "h": 26, "top": 772.5, "left": -64, "right": -46},
    {"id": "rail-bell", "w": 18, "h": 26, "top": 772.5, "left": -32, "right": -14},
    {"id": "rail-gear", "h": 27, "top": 772, "right": -19},
)
DUMP = os.environ.get("MTABS_FIT_DUMP", "")   # a directory: each engine's raw readings are copied there (evidence for a run)
EPS = 0.5


def _px(v):
    """'31px' -> 31.0; an empty or malformed value is a failure, not a zero."""
    v = (v or "").strip()
    assert v.endswith("px"), "not a px value: %r" % (v,)
    return float(v[:-2])


def _problems(where, row):
    """Every way the bar fails one reading, as lines naming the controls; empty when the bar holds."""
    out = []
    vw, vh, bar, cs = row["vw"], row["vh"], row["bar"], row["controls"]
    past = [c["key"] for c in cs if c["left"] < -EPS or c["right"] > vw + EPS]
    if past:
        out.append("%s: past the window's edge (%dpx): %s (rights %s)" % (
            where, vw, ", ".join(past), ", ".join("%g" % c["right"] for c in cs if c["key"] in past)))
    missed = [c["key"] for c in cs if not c["hit"]]
    if missed:
        out.append("%s: the element at the centre is not the control: %s" % (where, ", ".join(missed)))
    for i, a in enumerate(cs):
        for b in cs[i + 1:]:
            if min(a["right"], b["right"]) - max(a["left"], b["left"]) > EPS and min(a["bottom"], b["bottom"]) - max(a["top"], b["top"]) > EPS:
                out.append("%s: %s and %s overlap" % (where, a["key"], b["key"]))
    clipped = [c["key"] for c in cs if c["tab"] and not c["labelFits"]]
    if clipped:
        out.append("%s: a tab's label is wider than the tab: %s" % (where, ", ".join(clipped)))
    if abs(bar["left"]) > EPS or abs(bar["right"] - vw) > EPS or abs(bar["bottom"] - vh) > EPS:
        out.append("%s: the bar does not span the window at its bottom edge: %r" % (where, bar))
    if bar["scrollW"] > bar["clientW"] + EPS:
        out.append("%s: the bar's content overflows it (scrollWidth %s, clientWidth %s)" % (where, bar["scrollW"], bar["clientW"]))
    if row["docScrollW"] > vw + EPS:
        out.append("%s: the document is wider than the window (%s)" % (where, row["docScrollW"]))
    acts = [c for c in cs if not c["tab"]]
    one_h = max((c["h"] for c in acts), default=0)
    narrow = ["%s (%g, natural %g)" % (c["key"], c["w"], c["naturalW"]) for c in cs if c["w"] < c["naturalW"] - EPS]
    if narrow:
        out.append("%s: narrower than its natural width: %s" % (where, ", ".join(narrow)))
    short = [c["key"] for c in cs if c["h"] < one_h - EPS]
    if short:
        out.append("%s: shorter than the single row's %gpx: %s" % (where, one_h, ", ".join(short)))
    try:
        reserved = _px(row["mtabsH"])
        if abs(reserved - bar["offsetH"]) > EPS:
            out.append("%s: the panes' strip (--mtabs-h %s) is not the bar's height (%s)" % (where, row["mtabsH"], bar["offsetH"]))
    except AssertionError as e:
        out.append("%s: --mtabs-h unreadable: %s" % (where, e))
    if not row["pane"] or row["pane"]["bottom"] > bar["top"] + EPS:
        out.append("%s: the shown pane runs under the bar: %r against the bar's top %s" % (where, row["pane"], bar["top"]))
    out += _shape(where, row, "one" if row["natural"] <= vw + EPS else "two")
    return out


def _shape(where, row, rows):
    """The bar's shape: rows='one', the single row it is wherever its natural row fits, every control on it and the bar one
    control tall (the panes keep everything above that one row); rows='two', the fallback, the tabs filling the first row and
    the cluster together on the second at the right edge."""
    out = []
    vw, bar, cs = row["vw"], row["bar"], row["controls"]
    tabs = [c for c in cs if c["tab"]]
    acts = [c for c in cs if not c["tab"]]
    one_h = max((c["h"] for c in acts), default=0)
    if rows == "one":
        if row["natural"] > vw + EPS:
            out.append("%s: one row is owed here, yet the natural row (%gpx) is wider than the window" % (where, row["natural"]))
        if max(c["top"] for c in cs) - min(c["top"] for c in cs) > EPS:
            out.append("%s: one row is owed here, yet the controls are not on one row (tops %s)" % (
                where, ", ".join("%s %g" % (c["key"], c["top"]) for c in cs)))
        if abs(bar["offsetH"] - (one_h + bar["borderTop"] + bar["padBottom"])) > EPS:
            out.append("%s: one row is owed here, yet the bar is %spx tall, not one row of %gpx" % (where, bar["offsetH"], one_h))
    else:
        if row["natural"] <= vw + EPS:
            out.append("%s: the fallback is owed here, yet the natural row (%gpx) fits the window" % (where, row["natural"]))
        if tabs and max(c["top"] for c in tabs) - min(c["top"] for c in tabs) > EPS:
            out.append("%s: the tabs are not on one row" % where)
        if acts and max(c["top"] for c in acts) - min(c["top"] for c in acts) > EPS:
            out.append("%s: the action buttons are not on one row" % where)
        if tabs and acts and min(c["top"] for c in acts) < max(c["bottom"] for c in tabs) - EPS:
            out.append("%s: the natural row (%gpx) does not fit, yet the actions are not on a row under the tabs" % (where, row["natural"]))
        if acts and abs(acts[-1]["right"] - vw) > EPS:
            out.append("%s: the last action button does not sit at the right edge (%s)" % (where, acts[-1]["right"]))
        if any(abs(b["left"] - a["right"]) > EPS for a, b in zip(acts, acts[1:])):
            out.append("%s: the action buttons are not side by side" % where)
    return out


def _acts_problems(engine, acts):
    """The moved actions: each one click from the bar's Settings, doing what its bar button did, its glyph's state kept."""
    out = []
    where = "%s moved actions at %dx%d" % (engine, acts["vp"][0], acts["vp"][1])
    keys = [c["key"] for c in acts["bar"]["controls"] if not c["tab"]]
    if keys != list(BAR_ACTS):
        out.append("%s: the bar's actions are %s, not %s" % (where, keys, list(BAR_ACTS)))
    for act in MOVED:
        run = acts["runs"].get(act) or {}
        w = "%s, %s" % (where, act)
        card = run.get("card") or {}
        if not card.get("rowShown"):
            out.append("%s: the card's row of panel buttons is not shown on the phone" % w)
        btn = next((b for b in card.get("buttons", []) if b["act"] == act), None)
        if not btn:
            out.append("%s: no %s button in the card: %r" % (w, act, card.get("buttons")))
            continue
        c, vw, vh = card.get("card") or {}, acts["vp"][0], acts["vp"][1]
        if btn["left"] < -EPS or btn["right"] > vw + EPS or btn["top"] < -EPS or btn["bottom"] > vh + EPS:
            out.append("%s: the button is not wholly in the window: %r" % (w, btn))
        if not c or btn["left"] < c["left"] - EPS or btn["right"] > c["right"] + EPS or btn["top"] < c["top"] - EPS or btn["bottom"] > c["bottom"] + EPS:
            out.append("%s: the button is not wholly in the card: %r in %r" % (w, btn, c))
        if not btn["hit"]:
            out.append("%s: the element at the button's centre is not the button" % w)
        what = {"usage": "open the Usage modal", "net": "open the Remote kernels panel",
                "restart": "run the kernel's restart (the shell's handler taking the lab's refusal)"}[act]
        if not run.get("opened"):
            out.append("%s: one click on the card's button did not %s: %r" % (w, what, run.get("after")))
        # the restart's request: none before the click, exactly one after it, from the shell (the bar's handler's own POST)
        want_posts = ["shell"] if act == "restart" else []
        if run.get("restartsBefore") != [] or run.get("restarts") != want_posts:
            out.append("%s: POST /restart before the click %r and after it %r, not [] and %r" % (
                w, run.get("restartsBefore"), run.get("restarts"), want_posts))
        after = run.get("after") or {}
        if after.get("settingsOpen") or not run.get("cardHidden"):
            out.append("%s: the card is still open after the click: %r, card hidden %r" % (w, after, run.get("cardHidden")))
        if act != "net" and after.get("net"):
            out.append("%s: the click opened the Remote kernels panel" % w)
        if act != "usage" and after.get("usage"):
            out.append("%s: the click opened the Usage modal" % w)
    # the card's button vocabulary: each moved action wears Customize shortcuts' dress (#rs-keys-btn, the card's word button
    # the row's rules copy) at rest, its fill, hairline, radius, text, padding and press transition. The Remote kernels button
    # is read while the shell's poll lights it, and its text colour is the card's too: the accent goes on its glyph alone (PR
    # 976's round 1, ui-3; the glyph's colour is read on its svg below)
    dress = ((acts["runs"].get("usage") or {}).get("card") or {}).get("dress") or {}
    ref = dress.get("ref")
    if not ref:
        out.append("%s: no Customize shortcuts button to read the card's button dress from: %r" % (where, dress))
    else:
        got = {b["act"]: b for b in dress.get("acts", [])}
        for act in MOVED:
            b = got.get(act)
            if not b:
                continue   # its absence is listed above
            off = sorted(k for k in ref if b["dress"].get(k) != ref[k])
            if off:
                out.append("%s: the %s button does not wear the card's button dress: %s" % (
                    where, act, ", ".join("%s %r, not %r" % (k, b["dress"].get(k), ref[k]) for k in off)))
    # Usage with a reading (the lab's usage.json): enabled at the opening, its no-reading line not shown (and the click above
    # opened the Usage modal)
    u = ((acts["runs"].get("usage") or {}).get("card") or {}).get("usage")
    if not u or u.get("disabled") is not False or not u.get("line") or u["line"].get("shown") is not False:
        out.append("%s: with a reading, Usage is not enabled with its no-reading line hidden: %r" % (where, u))
    # the Remote kernels glyph in the card: at the first opening the state the shell's first poll painted on the rail (the
    # next poll held, so the card's paint is the opening's own); after the release the state of the second answer
    first, rel = (acts["runs"].get("usage") or {}).get("card", {}).get("glyph"), acts.get("released") or {}
    want = ["rn-me rn-ok", "rn-a rn-warn", "rn-b rn-ok"]
    rail = (acts["runs"].get("usage") or {}).get("rail") or {}
    if not first:
        out.append("%s: no Remote kernels glyph in the card" % where)
    else:
        if "on" not in (first["cls"] or "").split():
            out.append("%s: the card's Remote kernels glyph is not lit at the opening though a host is connected: %r" % (where, first))
        if [n and n["cls"] for n in first["nodes"]] != want:
            out.append("%s: the card's glyph nodes at the opening are %r, not %r" % (where, [n and n["cls"] for n in first["nodes"]], want))
        if [n and n["cls"] for n in rail.get("nodes", [])] != want:
            out.append("%s: the rail's glyph nodes are %r, not %r (the poll's premise)" % (where, [n and n["cls"] for n in rail.get("nodes", [])], want))
        if first["color"] != rail.get("color") or [n and n["fill"] for n in first["nodes"]] != [n and n["fill"] for n in rail.get("nodes", [])]:
            out.append("%s: the card's glyph does not wear the rail glyph's colours: %r against %r" % (where, first, rail))
    if rel.get("card") != ["rn-me rn-ok", "rn-a rn-ok", "rn-b rn-ok"]:
        out.append("%s: after the poll answered both hosts connected, the card's glyph nodes are %r" % (where, rel.get("card")))
    second = (acts["runs"].get("net") or {}).get("card", {}).get("glyph")
    if not second or [n and n["cls"] for n in second["nodes"]] != ["rn-me rn-ok", "rn-a rn-ok", "rn-b rn-ok"]:
        out.append("%s: at the second opening the card's glyph nodes are %r" % (where, second and [n and n["cls"] for n in second["nodes"]]))
    # the drop cue on the card's glyph: a drop that came while the card was closed plays no flash when the card next opens
    # (on the bar the flash played at the drop; a closed card shows nothing then, and the colours carry the state after it),
    # and a drop while the card is open flashes it
    drop = acts.get("drop") or {}
    if not drop.get("closedPolled"):
        out.append("%s: the poll that drops a host never reached the rail's glyph (the drop leg's premise): %r" % (where, drop))
    if not (drop.get("closed") or {}).get("cardHidden"):
        out.append("%s: the card was not closed when the host dropped (the drop leg's premise): %r" % (where, drop.get("closed")))
    re_ = drop.get("reopened")
    if not re_ or "rn-drop" in (re_["cls"] or "").split() or any(a.startswith("rs-pact-drop:") for a in (re_["anims"] or [])):
        out.append("%s: a host dropped while the card was closed, and the card's next opening plays its flash: %r" % (where, re_))
    if not drop.get("backUp"):
        out.append("%s: the host never came back on the rail's glyph before the second drop (its premise): %r" % (where, drop))
    live = drop.get("openDrop")
    if not live or "rs-pact-drop:running" not in (live["anims"] or []):
        out.append("%s: a host dropping while the card is open does not flash the card's glyph: %r" % (where, live))
    # the Token usage panel over the card (PR 976's round 1, fresh-1): it hides the card with no settings message, so a drop
    # while it is up must not flash the card's glyph when the panel closes and the card shows again
    ra = drop.get("analytics") or {}
    if not ra.get("backUp") or not ra.get("opened") or not ra.get("dropped") or not (ra.get("during") or {}).get("cardHidden"):
        out.append("%s: the Token usage panel leg's premise (the host back up, the panel opened over the card and hiding it, "
                   "the host dropping while it was up): %r" % (where, ra))
    ra_after = ra.get("after")
    if not ra.get("closed") or not ra_after or ra_after.get("cardHidden") or "rn-drop" in (ra_after["cls"] or "").split() \
            or any(a.startswith("rs-pact-drop:") for a in (ra_after["anims"] or [])):
        out.append("%s: a host dropped while the Token usage panel hid the card, and the card's glyph flashes when the panel "
                   "closes: %r" % (where, ra))
    return out


def _no_reading_problems(engine, nr):
    """Usage with no reading: disabled with its line once the opening's ask has ended, a tap leaving the card open and posting
    nothing; then a reading landing while the card is still open enables Usage there with no line (the shell tells the open
    card), the readings emptying disable it with its line again and filling enable it again, and one click opens the Usage
    modal."""
    out = []
    where = "%s Usage with no reading at %dx%d" % (engine, nr["vp"][0], nr["vp"][1])
    pre = nr.get("premise") or {}
    if pre.get("pulls", 0) < 1 or pre.get("readout") != "":
        out.append("%s: the shell holds a reading before the card opens (the leg's premise): %r" % (where, pre))
    if not nr.get("firstAsked"):
        out.append("%s: the opening's ask for a fresh reading never ended (the romp loader still up): %r" % (where, nr.get("first")))
    first = nr.get("first")
    if not first or first.get("disabled") is not True or not first.get("line") or first["line"].get("shown") is not True \
            or first["line"].get("text") != USAGE_NONE:
        out.append("%s: Usage is not disabled with the line %r: %r" % (where, USAGE_NONE, first))
    tap = nr.get("tapped") or {}
    if not tap.get("settingsOpen") or tap.get("cardHidden") is not False:
        out.append("%s: a tap on Usage closed the card: %r" % (where, tap))
    if tap.get("usage") or tap.get("acts") != []:
        out.append("%s: a tap on Usage reached the shell (the Usage modal %r, phoneAct %r)" % (where, tap.get("usage"), tap.get("acts")))
    after = nr.get("afterTap")
    if not after or not after.get("line") or after["line"].get("shown") is not True:
        out.append("%s: after the tap the line saying there is no reading yet is not shown: %r" % (where, after))
    if not nr.get("arrived"):
        out.append("%s: the reading never reached the shell's readout (the second half's premise)" % where)
    still = nr.get("stillOpen") or {}
    if not still.get("settingsOpen") or still.get("cardHidden") is not False:
        out.append("%s: the card was not open when the reading landed (the second half's premise): %r" % (where, still))
    second = nr.get("second")
    if not second or second.get("disabled") is not False or not second.get("line") or second["line"].get("shown") is not False:
        out.append("%s: a reading landed while the card was open, and the open card does not show Usage enabled without its line: %r" % (where, second))
    if not nr.get("emptiedReadout") or not nr.get("refilledReadout"):
        out.append("%s: the shell's readout did not follow the emptying and the refilling (their premise): %r, %r" % (
            where, nr.get("emptiedReadout"), nr.get("refilledReadout")))
    emptied = nr.get("emptied")
    if not emptied or emptied.get("disabled") is not True or not emptied.get("line") or emptied["line"].get("shown") is not True:
        out.append("%s: the readings emptied while the card was open, and the open card does not show Usage disabled with its line: %r" % (where, emptied))
    refilled = nr.get("refilled")
    if not refilled or refilled.get("disabled") is not False or not refilled.get("line") or refilled["line"].get("shown") is not False:
        out.append("%s: the readings filled again while the card was open, and the open card does not show Usage enabled without its line: %r" % (where, refilled))
    clicked = nr.get("clicked") or {}
    if not nr.get("opened") or clicked.get("settingsOpen") or clicked.get("cardHidden") is not True or clicked.get("acts") != ["usage"]:
        out.append("%s: with the reading, one click on Usage did not close the card and open the Usage modal: opened %r, %r" % (
            where, nr.get("opened"), clicked))
    return out


def _unpulled_problems(engine, up):
    """A reading the kernel holds and the shell has not pulled: the card's opening asks the shell for a fresh pull, shows the
    romp loader on Usage while it is in flight (the button disabled, no line), and once it ends shows Usage enabled with no
    line; one click opens the Usage modal (PR 976's round 1, correctness-1 and extra6-1)."""
    out = []
    where = "%s Usage over an unpulled reading at %dx%d" % (engine, up["vp"][0], up["vp"][1])
    pre = up.get("premise") or {}
    if pre.get("boots", 0) < 1 or pre.get("readout") != "" or pre.get("sessionsLoaded") is not False:
        out.append("%s: the leg's premise (the boot pull answered no rows, the readout empty, the Sessions pane unloaded): %r" % (where, pre))
    if not up.get("asked"):
        out.append("%s: the card's opening asks the shell for no fresh reading (no pull under /usage/ after the opening)" % where)
    d = up.get("during")
    if not d or d.get("disabled") is not True or d.get("busy") != "true" or not d.get("line") or d["line"].get("shown") is not False \
            or not d.get("wait") or d["wait"].get("shown") is not True or d["wait"].get("text") != "romp" \
            or not {"fask-swirl-spin", "fileview-pulse"} <= set(d["wait"].get("anims") or []):
        out.append("%s: while the opening's pull is in flight, Usage does not show the romp loader (spinning, its dots pulsing), "
                   "disabled and busy, with no line: %r" % (where, d))
    if not up.get("ended") or not up.get("readout"):
        out.append("%s: the opening's pull did not land (the ask ended %r, the readout filled %r)" % (where, up.get("ended"), up.get("readout")))
    a = up.get("after")
    if not a or a.get("disabled") is not False or a.get("busy") is not None or not a.get("line") or a["line"].get("shown") is not False \
            or (a.get("wait") or {}).get("shown") is not False:
        out.append("%s: after the opening's pull, Usage is not enabled with no line and no loader: %r" % (where, a))
    clicked = up.get("clicked") or {}
    if not up.get("opened") or clicked.get("settingsOpen") or clicked.get("cardHidden") is not True or clicked.get("acts") != ["usage"]:
        out.append("%s: one click on Usage did not close the card and open the Usage modal: opened %r, %r" % (where, up.get("opened"), clicked))
    return out


def _skew_problems(engine, sk):
    """The deploy skew (PR 976's round 1, kernel-1): the shell publishes its marker beside the phoneAct listener, the card shows
    its row where the marker is and not where it is missing (a shell from before the move, with the phone layout and the three
    still on its bar), and a shell that cannot be asked for a reading leaves Usage as its bar button was, enabled with no line."""
    out = []
    where = "%s deploy skew at %dx%d" % (engine, sk["vp"][0], sk["vp"][1])
    if sk.get("marker") is not True:
        out.append("%s: the shell publishes no marker beside its phoneAct listener (window.__rompPhoneActs %r)" % (where, sk.get("marker")))
    head = sk.get("head") or {}
    if not head.get("rowShown"):
        out.append("%s: with the shell's marker, the card's row of moved actions is not shown: %r" % (where, head))
    older = sk.get("older") or {}
    if older.get("rowShown") is not False or any(w > 0 or h > 0 for w, h in older.get("boxes", [])):
        out.append("%s: with the phone layout and no marker (a shell from before the move), the card shows the row: %r" % (where, older))
    ca = sk.get("cannotAsk") or {}
    u = ca.get("usage")
    if not ca.get("rowShown") or not u or u.get("disabled") is not False or not u.get("line") or u["line"].get("shown") is not False:
        out.append("%s: where the shell cannot be asked for a reading, Usage is not enabled with no line, as its bar button was: %r" % (where, ca))
    return out


def _follow_problems(engine, fl):
    """The row follows the layout while the card is open (PR 976's round 1, correctness-2 and ui-1): opened on the phone layout
    with its row, the window widened past 820px hides the row in the open card, and narrowed back shows it again; the row shown
    again carries no flash for a drop that came while it was hidden, and Usage's state is asked afresh (the lab's reading:
    enabled, no line)."""
    out = []
    where = "%s the row following the layout, %dx%d and %dx%d" % (engine, fl["vp"][0], fl["vp"][1], (fl.get("wide") or WIDE)[0], (fl.get("wide") or WIDE)[1])
    ph = fl.get("phone") or {}
    if ph.get("mobile") is not True or not ph.get("open") or not ph.get("rowShown"):
        out.append("%s: the leg's premise (the card open on the phone layout with its row shown): %r" % (where, ph))
    wr = fl.get("wideRow") or {}
    if wr.get("mobile") is not False or not wr.get("open"):
        out.append("%s: the widened window's premise (the desktop layout, the card still open): %r" % (where, wr))
    if not fl.get("hid") or wr.get("rowShown") is not False or any(w > 0 or h > 0 for w, h in wr.get("boxes", [])):
        out.append("%s: the window widened past the phone layout with the card open, and the row stays shown: %r" % (where, wr))
    if not fl.get("dropped") or "rn-drop" not in (fl.get("dropCls") or "").split():
        out.append("%s: the drop's premise (the host dropping on the rail's glyph while the window was wide, its class left on the "
                   "card's hidden glyph): dropped %r, the glyph's class %r" % (where, fl.get("dropped"), fl.get("dropCls")))
    nr = fl.get("narrowRow") or {}
    if nr.get("mobile") is not True or not nr.get("open"):
        out.append("%s: the narrowed window's premise (the phone layout, the card still open): %r" % (where, nr))
    if not fl.get("showed") or not nr.get("rowShown"):
        out.append("%s: the window narrowed to the phone layout with the card open, and the row stays hidden: %r" % (where, nr))
    g = fl.get("glyph")
    if not g or "rn-drop" in (g["cls"] or "").split() or any(a.startswith("rs-pact-drop:") for a in (g["anims"] or [])):
        out.append("%s: a host dropped while the row was hidden, and the row shown again flashes its glyph: %r" % (where, g))
    u = fl.get("usage")
    if not fl.get("asked") or not u or u.get("disabled") is not False or not u.get("line") or u["line"].get("shown") is not False:
        out.append("%s: the row shown again does not show Usage enabled with no line once its ask has ended (the lab's reading): %r" % (where, u))
    return out


def _rail_problems(engine, rail):
    """The desktop rail equals af7d18250's at each width (RAIL_AF7), every action on screen and hit at its centre."""
    out = []
    for r in rail:
        w, h = r["vp"]
        where = "%s desktop rail %dx%d" % (engine, w, h)
        want = RAIL_AF7
        if r["mobile"] is not False:
            out.append("%s: the window is on the phone layout: %r" % (where, r))
        ids = [a["id"] for a in r["acts"]]
        if ids != [a["id"] for a in want]:
            out.append("%s: the rail's actions are %s, not af7d18250's %s" % (where, ids, [a["id"] for a in want]))
            continue
        # the settings card opened from the rail's gear: the phone's row of moved actions is not displayed (the rail has its own)
        card = (r.get("card") or {}).get("card")
        if not (r.get("card") or {}).get("opened") or not card or not card.get("row"):
            out.append("%s: the settings card did not open from the rail's gear with its row in it: %r" % (where, r.get("card")))
        elif card.get("display") != "none" or any(w > 0 or h > 0 for w, h in card.get("boxes", [])):
            out.append("%s: the settings card shows the phone's row of moved actions on the desktop: %r" % (where, card))
        vw, gear = r["vw"], r["acts"][-1]
        for a, b in zip(r["acts"], want):
            if a["left"] < -EPS or a["right"] > vw + EPS or not a["hit"]:
                out.append("%s: %s is not wholly on screen and hit at its centre: %r" % (where, a["id"], a))
            got = {"top": a["top"], "h": a["h"]}
            if a is gear:
                got["right"] = round(a["right"] - vw, 2)
            else:
                got.update(w=a["w"], left=round(a["left"] - gear["left"], 2), right=round(a["right"] - gear["left"], 2))
            for k, v in got.items():
                if abs(v - b[k]) > EPS:
                    out.append("%s: %s %s is %g, af7d18250's %g" % (where, a["id"], k, v, b[k]))
    return out


def _rgba(v):
    """A computed colour, 'rgb(r, g, b)' or 'rgba(r, g, b, a)' (commas or the spaced form), -> (r, g, b, a); anything else is a
    failure, not a guess."""
    m = re.fullmatch(r"rgba?\(\s*([\d.]+)[\s,]+([\d.]+)[\s,]+([\d.]+)(?:\s*[,/]\s*([\d.]+)(%?))?\s*\)", (v or "").strip())
    assert m, "not an rgb() colour: %r" % (v,)
    a = 1.0 if m.group(4) is None else float(m.group(4)) / (100.0 if m.group(5) else 1.0)
    return (float(m.group(1)), float(m.group(2)), float(m.group(3)), a)


def _over(fg, bg):
    """fg composited over the opaque bg."""
    return tuple(fg[i] * fg[3] + bg[i] * (1 - fg[3]) for i in range(3)) + (1.0,)


def _contrast(a, b):
    """WCAG's contrast ratio of two opaque colours."""
    def lum(c):
        ch = [x / 255.0 for x in c[:3]]
        ch = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in ch]
        return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2]
    x, y = lum(a), lum(b)
    return (max(x, y) + 0.05) / (min(x, y) + 0.05)


def _hex(c):
    return "#" + "".join("%02x" % int(round(x)) for x in c[:3])


def _oklab_distance(a, b):
    """The Euclidean distance between two opaque sRGB colours in OKLab (Ottosson's matrices), x100."""
    def lab(c):
        r, g, bl = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in (v / 255.0 for v in c[:3])]
        lms = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * bl,
               0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * bl,
               0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * bl)
        l_, m_, s_ = [v ** (1.0 / 3.0) for v in lms]
        return (0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
                1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
                0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_)
    return 100.0 * sum((p - q) ** 2 for p, q in zip(lab(a), lab(b))) ** 0.5


def _contrast_problems(engine, contrast):
    """Each colour the Remote kernels glyph wears reads at GLYPH_FLOOR or more against the card's background and against the
    button's own fill (the glyph sits on the button), at rest and with the pointer on the button (PR 976's round 1,
    extra6-2: the hovered fill is a fill the glyph sits on too), in the dark and the light theme; and the needs-you red stays
    SEPARATION_FLOOR or more from the connected node's colour in OKLab."""
    out = []
    for name, theme in THEMES:
        where = "%s Remote kernels glyph, %s theme (%s)" % (engine, name, theme)
        t = contrast.get(name)
        if not t:
            out.append("%s: not read" % where)
            continue
        if t.get("light") is not (name == "light"):
            out.append("%s: the settings document's theme-light class is %r (the leg's premise)" % (where, t.get("light")))
        if not t.get("rowShown"):
            out.append("%s: the card's row of moved actions is not shown (the leg's premise)" % where)
        try:
            card = _rgba(t.get("card"))
            if card[3] != 1:
                out.append("%s: the card's background is not opaque (%r), so what lies under it is unmeasured" % (where, t.get("card")))
                continue
            fill = _over(_rgba(t.get("fill")), card)
            for k in GLYPH:
                col = _rgba((t.get("colours") or {}).get(k))
                on_card, on_fill = _contrast(_over(col, card), card), _contrast(_over(col, fill), fill)
                if on_card < GLYPH_FLOOR or on_fill < GLYPH_FLOOR:
                    out.append("%s: %s, %s, reads %.2f:1 on the card (%s) and %.2f:1 on the button's fill (%s), under %g:1" % (
                        where, k, _hex(_over(col, fill)), on_card, _hex(card), on_fill, _hex(fill), GLYPH_FLOOR))
            ok, warn = (_over(_rgba((t.get("colours") or {}).get(k)), fill) for k in ("connected", "needs you"))
            apart = _oklab_distance(ok, warn)
            if apart < SEPARATION_FLOOR:
                out.append("%s: the needs-you red %s is %.2f from the connected node's %s (OKLab distance x100), under %g" % (
                    where, _hex(warn), apart, _hex(ok), SEPARATION_FLOOR))
            hv = t.get("hover") or {}
            if hv.get("hovered") is not True:
                out.append("%s: the pointer on the Remote kernels button does not hover it (the hovered fill's premise): %r" % (where, hv))
            else:
                hfill = _over(_rgba(hv.get("fill")), card)
                for k in GLYPH:
                    col = _rgba((hv.get("colours") or {}).get(k))
                    on_hover = _contrast(_over(col, hfill), hfill)
                    if on_hover < GLYPH_FLOOR:
                        out.append("%s: %s, %s, reads %.2f:1 on the hovered button's fill (%s), under %g:1" % (
                            where, k, _hex(_over(col, hfill)), on_hover, _hex(hfill), GLYPH_FLOOR))
        except AssertionError as e:
            out.append("%s: unreadable: %s" % (where, e))
    return out


class MtabsFit(unittest.TestCase):
    """One lab kernel for every leg (setUpClass); each leg is one driver run in one engine."""
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        if not os.path.isdir(os.path.join(EXT, "node_modules", "playwright")):
            raise unittest.SkipTest("extension deps absent (npm ci not run here): the served leg needs them")
        cls.lab = tempfile.mkdtemp(prefix="mtabs-fit-")
        cls.addClassCleanup(lab_ports.release, cls.lab)   # runs on a failed setUpClass too, which skips tearDownClass
        dist = os.path.join(cls.lab, "dist")
        lab_dist.copy_dist(dist)   # the checkout's ONE build of the bundles, copied under its lock (tests/lab_dist.py)
        os.makedirs(os.path.join(cls.lab, "xdg", "romp"), exist_ok=True)
        # an API-key machine's usage reading (spend windows, zeros): the Usage modal opens only over a reading
        Path(cls.lab, "xdg", "romp", "usage.json").write_text(json.dumps({"apiKey": True}))
        cls.port, cls.token = lab_ports.reserve(cls.lab), "testtok-mtabsfit"
        cls.env = _lab.kernel_env(cls.lab, os.path.join(cls.lab, "claude"), dist, cls.port, cls.token)
        cls.klog = os.path.join(cls.lab, "kernel.log")
        cls.kernel = subprocess.Popen([os.path.join(BIN, "romp-kernel")], stdout=open(cls.klog, "w"),
                                      stderr=subprocess.STDOUT, env=cls.env)
        why = lab_ports.wait_owned(cls.kernel, cls.env)
        if why:
            cls.kernel.kill()
            cls.kernel.wait()
            raise unittest.SkipTest("hermetic kernel never served /healthz here: " + why)

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "kernel", None):
            cls.kernel.kill()
            cls.kernel.wait()
        lab_ports.release(getattr(cls, "lab", ""))
        shutil.rmtree(getattr(cls, "lab", ""), ignore_errors=True)

    def _drive(self, engine):
        declared = os.environ.get("ROMP_SERVED_TESTS_ENGINES", "")
        if engine != "chromium" and declared and engine not in [e.strip() for e in declared.split(",")]:
            self.skipTest("optional: this runner declares no %s (ROMP_SERVED_TESTS_ENGINES=%s)" % (engine, declared))
        cfg = {"engine": engine, "url": "http://127.0.0.1:%d/?token=%s" % (self.port, self.token),
               "healthz": "http://127.0.0.1:%d/healthz" % self.port, "settleMs": 100,
               "viewports": [list(v) for v in PORTRAIT + LANDSCAPE], "dynamicViewport": list(DYNAMIC),
               "actsViewport": list(ACTS), "moved": list(MOVED), "restartRefusal": RESTART_REFUSAL,
               "tunnels": TUNNELS, "tunnels2": TUNNELS2, "tunnelsDrop": TUNNELS_DROP, "themes": [list(t) for t in THEMES],
               "desktopViewport": list(DESKTOP), "railViewports": [list(v) for v in RAIL], "wideViewport": list(WIDE),
               "result": os.path.join(self.lab, "result-%s.json" % engine)}
        cfg_path = os.path.join(self.lab, "cfg-%s.json" % engine)
        Path(cfg_path).write_text(json.dumps(cfg))
        try:
            p = subprocess.run(["node", DRIVER], capture_output=True, text=True, timeout=420,
                               env=dict(os.environ, EXT_PKG=os.path.join(EXT, "package.json"), CFG=cfg_path))
        except subprocess.TimeoutExpired as e:
            so = e.stdout if isinstance(e.stdout, str) else (e.stdout or b"").decode()
            self.fail("driver timed out; partial output:\n%s" % so[-3000:])
        if p.returncode == 3:
            if engine == "chromium":
                self.skipTest("no playwright chromium on this box: the served leg needs one (CI installs it)")
            self.skipTest("optional: no playwright %s on this machine: %s" % (engine, p.stderr.strip()[-300:]))
        self.assertEqual(p.returncode, 0, "driver failed:\n" + p.stdout[-3000:] + p.stderr[-3000:])
        line = next((ln for ln in p.stdout.splitlines() if ln.startswith("RESULT-FILE:")), None)
        self.assertIsNotNone(line, "driver printed no result:\n" + p.stdout[-3000:] + p.stderr[-3000:])
        self.assertEqual(line[len("RESULT-FILE:"):], cfg["result"], "the driver wrote the file it was given")
        raw = Path(cfg["result"]).read_text()
        if DUMP:
            os.makedirs(DUMP, exist_ok=True)
            Path(DUMP, engine + ".json").write_text(raw)
        r = json.loads(raw)
        self.assertNotIn("died", r, "driver aborted early: %r (kernel log tail: %s)" % (r.get("died"), Path(self.klog).read_text()[-800:]))
        self.assertEqual(r.get("errors"), [], "page errors")
        return r

    def _leg(self, engine):
        r = self._drive(engine)
        problems, phones = [], 0
        for name in ("default", "files"):
            rows = r["sets"][name]
            self.assertEqual([tuple(x["vp"]) for x in rows], list(PORTRAIT + LANDSCAPE), engine + ": every phone was read")
            for row in rows:
                where = "%s %s %dx%d" % (engine, name, row["vp"][0], row["vp"][1])
                if not row["mobile"]:
                    # only a landscape phone wider than the query's 820px, in an engine whose emulation gives no coarse pointer
                    self.assertGreater(row["vw"], 820, where + ": the phone layout is off only past 820px: %r" % (row,))
                    self.assertEqual(row["display"], "none", where + ": no phone layout, no bar")
                    continue
                phones += 1
                self.assertTrue(row["fonts"], where + ": the webfont is in, so the labels have their served widths")
                self.assertEqual((row["bell"] or {}).get("hidden"), False, where + ": the bell shows (the shell reveals it on every page): %r" % (row["bell"],))
                keys = [c["key"] for c in row["controls"] if not c["tab"]]
                if keys != list(BAR_ACTS):
                    problems.append("%s: the bar's actions are %s, not %s (Usage, Remote kernels and Restart kernel live in the settings card)" % (where, keys, list(BAR_ACTS)))
                self.assertEqual(len([c for c in row["controls"] if c["tab"]]), 6 if name == "files" else 5, where + ": the tab set")
                problems += _problems(where, row)
                if row["vp"][1] > row["vp"][0]:
                    if row["vp"][0] in ONE_ROW[name]:
                        problems += _shape(where + " (one row owed)", row, "one")
                    if row["vp"][0] == FALLBACK.get(name):
                        problems += _shape(where + " (the fallback owed)", row, "two")
        self.assertGreaterEqual(phones, 2 * len(PORTRAIT), engine + ": every portrait phone was read on the phone layout")
        d = r["dynamic"]
        where = "%s files turned on at %dx%d" % (engine, d["vp"][0], d["vp"][1])
        # the leg's premises, listed with the rest (a red run names every failing reading, not the first)
        if d["before"]["natural"] > d["before"]["vw"] + EPS:
            problems.append("%s: the default set does not fit one row here (the leg's premise): natural %g" % (where, d["before"]["natural"]))
        if d["after"]["natural"] <= d["after"]["vw"] + EPS:
            problems.append("%s: the Files set fits one row here (the leg's premise): natural %g" % (where, d["after"]["natural"]))
        problems += _problems(where + " (before)", d["before"])
        problems += _problems(where, d["after"])
        problems += _acts_problems(engine, r["acts"])
        problems += _no_reading_problems(engine, r.get("noReading") or {"vp": list(ACTS)})
        problems += _unpulled_problems(engine, r.get("unpulled") or {"vp": list(ACTS)})
        problems += _skew_problems(engine, r.get("skew") or {"vp": list(ACTS)})
        problems += _follow_problems(engine, r.get("follow") or {"vp": list(ACTS), "wide": list(WIDE)})
        problems += _contrast_problems(engine, r.get("contrast") or {})
        self.assertEqual([tuple(x["vp"]) for x in r["rail"]], list(RAIL), engine + ": every rail width was read")
        problems += _rail_problems(engine, r["rail"])
        self.assertEqual(r["desktop"]["display"], "none", engine + ": the desktop shows no phone bar: %r" % (r["desktop"],))
        self.assertIs(r["desktop"]["mobile"], False, engine + ": the desktop window is not the phone layout: %r" % (r["desktop"],))
        self.assertEqual(problems, [], "\n".join(problems))

    def test_chromium_every_control_on_screen_at_every_phone_width(self):
        self._leg("chromium")

    # WebKit is Safari's engine and Firefox the third; `optional:` skips where the browser is absent (CI installs Chromium alone)
    def test_webkit_every_control_on_screen_at_every_phone_width(self):
        self._leg("webkit")

    def test_firefox_every_control_on_screen_at_every_phone_width(self):
        self._leg("firefox")


if __name__ == "__main__":
    unittest.main()
