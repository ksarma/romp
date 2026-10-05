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
  machinery (spend and limits, other machines' kernels), not about the sessions; moving those two is the smallest move
  that gives one row from 375 to 430px in all three engines (measured at the wrap-only head by hiding each set of actions
  in the served bar: either one alone leaves 386px in Chromium; the two leave 354px in Chromium and 349 to 350px in WebKit
  and Firefox, and 390 and 384 to 385px with the Files tab on). Restart followed them (romp-manager's call 3, 2026-10-05):
  the kernel's restart is machinery too, rarely used and costly to hit by accident, and with it gone the default row needs
  322px in Chromium and 318px in WebKit and Firefox (358 and 353px with the Files tab on), so the bar is one row at every
  phone width from 360px with the Files tab on or off. The bell stays on the bar. The three now sit in the settings card, a
  row of buttons under its title, above the tabs (so whichever tab the card opens at shows them), shown only on the phone
  layout. One click on the bar's Settings opens the card, one click on the button closes the card and runs the handler the
  bar's button ran (the shell's A-map, reached by a phoneAct message from the settings document, whose accepted acts are
  exactly the three), so Usage opens its modal, Remote kernels its panel and Restart kernel the kernel's restart (POST
  /restart), as before. The Remote kernels glyph keeps its live state there:
  the shell's /tunnels poll paints the card's copy as it painted the bar's (connected, attaching, each node's colour, the
  drop flash), and the card's opening paints it from the last poll. The drop flash plays only where the card is open at
  the drop: a closed card runs no animation, so the class a drop left on its copy is cleared when the card opens, where
  it would otherwise play the flash late.
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
overlap, a tab's label fits inside it, every control keeps at least its natural width (its width in the unsqueezed row)
and the single row's height, the bar spans the window at its bottom edge and nothing in it overflows, and the strip the
panes leave (--mtabs-h) equals the bar's height with the shown pane ending above it. The bar shows three action buttons
(the Log's triangle, the bell, Settings) and no Usage, Remote kernels or Restart kernel. In portrait the bar IS one row on
the default set at 360, 375, 390, 414 and 430px and on the Files set at 375 to 430px (ONE_ROW: its natural width fits,
every control on it, the bar one control tall, so the panes keep all but that one row), and IS the fallback on the Files
set at 320px (FALLBACK: the natural row does not fit, the tabs fill the first row and the cluster sits together on the
second at the right edge). Elsewhere the bar is one row exactly where its natural one-row width (the bar laid out at
max-content without wrapping) fits. Then the Files tab turned on with no resize, at 340px where the default set fits one
row and the Files set does not: the bar wraps and the strip follows it. Then the moved actions, at 390px: the bar's
Settings clicked at its centre opens the card; its row of three buttons shows, each wholly in the window and the card and
hit at its centre; the Remote kernels glyph wears the state the shell's poll painted on the rail's glyph (the
shell's own GET /tunnels answers two synthetic hosts, one connected and one with no kernel: the glyph on, its nodes needs
you and connected, the same classes, colours and fills as the rail's); the shell's next poll is held until after the first
opening, so the card's paint is the opening's own, and when it is released with both hosts connected the card's copy
follows it; then one click on Usage closes the card and opens the Usage modal (the lab's usage.json makes it a spend
reading, so the panel has something to show), and after the bar's Settings again, one click on Remote kernels closes the
card and opens the Remote kernels panel, and after it again, one click on Restart kernel closes the card and makes the
shell's one POST /restart (the driver answers it with a refusal in the manager's shape, RESTART_REFUSAL, so the lab kernel
stays up, and the shell's handler takes it: its splash down, the refusal's words on the rail's restart button); no click
but that one makes a POST /restart. Then the drop cue (TUNNELS_DROP, a host that was up answering with no kernel):
with the card closed the poll drops the host, and at the card's next opening its glyph carries no flash; then the host
comes back and drops again with the card open, and the glyph's flash runs. Then a desktop window, where the bar is hidden, and the desktop rail at 821 and
1100px, whose actions (restart, Remote kernels, the bell, the gear) and their boxes equal af7d18250's (RAIL_AF7 below).
MTABS_FIT_DUMP, a directory, keeps each engine's raw readings there.

Red at the wrap-only head, in all three engines: its bar shows six actions, it wraps where one row is owed (at 375 and
390px, and at 414 in Chromium; its row fits 414 in WebKit and Firefox and 430 in all three), and its card has no row of
moved actions. Red at the two-action move (Usage and Remote kernels moved, Restart still on the bar), in all three engines:
its bar shows Restart, its Files set wraps at 375px, and its card has no Restart kernel button. The phoneAct pin
is red under the listener's old accepted set (net and usage alone): the card's Restart kernel closes the card and no
POST /restart follows. The fallback's pin is red under the old rule restored (no wrap), and the rail's under the move
applied to the rail as well. The drop cue's pin is red at the commit before its fix, where a drop that came while the card
was closed flashed the glyph at the card's next opening. Runs in the "Browser-backed served-page tests (pytest)" step of
the served-pages job, "Served pages (pytest, ubuntu-latest)" (ci.yml, ROMP_SERVED_TESTS_REQUIRE=1: a skip here is a
failure), in Chromium; the WebKit and Firefox legs are `optional:` skips where that engine is absent or not declared in
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
DESKTOP = (1280, 800)
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
               "tunnels": TUNNELS, "tunnels2": TUNNELS2, "tunnelsDrop": TUNNELS_DROP,
               "desktopViewport": list(DESKTOP), "railViewports": [list(v) for v in RAIL],
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
