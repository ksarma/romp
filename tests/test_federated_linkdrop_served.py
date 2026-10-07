"""A remote link that drops and comes back MID-SESSION, driven for real against the federated relay (2026-09-19): what
a hub's pages do when the socket to a remote closes under them and a fresh one opens, and again when the pages' own
LOCAL socket goes with the hub kernel and returns.

PR 815 keeps its view-delta state per remote CONNECTION: the receiver (Conn.viewDeltas) is re-minted per dial inside
connect(), the raw feed base (Conn.feedRaw) is cleared there and re-seeded by the next whole frame, and the delta
breadcrumbs' latch is the conn's. A link that drops and redials is where per-connection state could strand (a patch
applied onto the dead socket's base) or double-initialise (a second receiver, a second ready), and no other lab drives
that road: the corners lab (tests/test_federated_capability_corners_served.py) holds one socket per page for its
whole drive. The question that asked for this lab was the reviewer's (2026-09-19): with that state re-minted per
dial, a relay link that drops and returns mid-session is where it could strand or double-initialise, and whether a
redial ENDED or RESTARTED the old bundle's storm was unknown, since nothing had driven the road on either hub bundle.

Two hermetic kernels (a hub owning no session, a checked-in TESTHOST owning eight) and a TCP splice between them in
the test process, standing in for the hub's ssh -L forward: the check-in names the splice's port as the peer's
kernelPort, so the hub's relay (kernel.py _remote_ws) and its supervisor's probes (_port_open, /sessions) go through
it. Dropping the link = closing the splice's listener and every spliced pair: the hub's upstream reads EOF, shuts the
browser's side (an unclean close, no close frame, code 1006), refuses the page's 2 s redials at create_connection
(_demand_redial "refused" wakes the supervisor, whose pass reads the port closed and marks the row down, and the
page's 4 s /tunnels poll then stops dialing: live false), and nothing reaches the page until the listener is back and
a supervisor pass reads the row up again. The LOCAL drop is a hub kernel restart (SIGTERM, HUB_DOWN_S down, the same
port, state root and dist): the pages' local sockets and every relay splice die together, the relay's 2 s retry runs
under the shim's local-down word (window.__rompLocalUp false: one dial-deferred row per conn), and the shim's reopen
(romp:wsup) is what dials the relay again. The driver (one Chromium, the hub's Waiting, Outline and feed pages) records
every socket each page dials (URL, dial and open and close stamps, close code, the local-up word at the dial, every
non-keepalive frame type on a relay socket) and every needSlot, needFullFeed and ready it sends with the socket it
left on; it drives the phases through a control door the test process serves (drop, resume, restart-hub, change).

Three phases, each ending in the same change bundle on the remote (NOTICES_PER_PHASE completed notice cards a second
apart, one user todo, one closed transcript pair appended for "api", so each page has a visible of its own: the card
on the feed page, the todo's text on the Waiting page, the swap of api's provisional row on the Outline): A before the
drop (the corners lab's baseline), B on the socket the link's return dialed, C on the socket the hub's restart dialed.
A fourth bundle, D, is posted WHILE THE LINK IS DOWN, once the hub's row has gone down: the control door reaches the
remote's real port, not the splice, so a patch is due to every page with nothing to carry it. That is the gate's
discriminating case (the maintainer's round 1 found the down window otherwise idle, so its zero rows could not tell "the link gates the
patches" from "no patch was due"): D is absent from every page while the link is down, no frame crosses, no row files,
the link's return serves each redial ONE whole frame that carries D (no patch between the return and phase B's first
change), and phase B's patches file rows again on the old bundle.
Recorded over the whole drive and asserted: the redial's terms (reconnect=1&proto, the page's caps and delta), the new
socket's first feed-family frame (a whole keyed feed, never a patch or a feedDelta: the remote's client dict is per
socket, kernel.py's accept), the frames the change crossed as, the hub's client-diag rows by kind and phase (outline
delta-unapplied, feedDelta-unapplied, feedDelta-nobase, delta-unknown-slot, delta-unkeyed-base: zero at 815's head),
the asks and their destination (zero), the dial-deferred rows (one per page at the restart), the relay dials after the
local return (one per page), and whether every phase's changes show on every page at the end. The remote's own wsopen
rows (kind relay, reconnect false then true) are the second record of each dial's terms, as the remote read them.

What this lab cannot make red, said plainly: three of PR 815's per-connection guards. The per-dial receiver re-mint
and the per-dial clear of the raw feed base, both in connect(), are latent here for one reason: every kernel in this
repo serves a fresh socket a whole frame first (dstate is per connection), so a stale receiver or a stale base is
re-seeded before any patch reaches it. The per-connection delta latch (sayDeltaOnce over Conn.saidDelta) is never
consulted, because the drive files no delta-unknown-slot or delta-unkeyed-base breadcrumb. With the feed-base clear
removed, or the latch made one set for the whole manager, LinkDropBothNew stays green (the maintainer's round 7,
extra6-1). The node tests are where the three are proven, each red with its guard removed (measured on 2026-09-29):
the receiver re-mint by the redial tests of ui/webview/federation-remote-view-delta.test.ts, the feed-base clear by
the same-conn redial test of ui/webview/federation-remote-feed-delta.test.ts, and the latch by the per-host and
per-event breadcrumb tests of federation-remote-view-delta.test.ts. The mutations that DO make this lab red are recorded in its report: the redial term stripped from remoteDialUrl, the whole-frame base
write dropped from the feed arm, the local-down gate dropped from connect(), and the old hub bundle in place of this
one (ROMP_LINKDROP_HUB_ROOT, the base-hub lever).

Knobs. LinkDropBothNew needs none: it runs wherever this checkout's served labs run, CI's served job included (about
a minute and a half: two supervisor waits, the 42 s down dwell and a hub restart; 82.5 s for its setUpClass in each of
the two drives of 2026-09-20 at this code, clean trees at the commits before these figures were written in
(`ROMP_LINKDROP_LAB=1 ROMP_LINKDROP_OLD_HUB_BUILD=1 pytest tests/test_federated_linkdrop_served.py --durations=20`, the
builder's `r5/lab-head1.log` and `r5/lab-head2.log` outside the repo). ROMP_LINKDROP_HUB_ROOT boots its hub from another
checkout with its
PREBUILT vscode-extension/dist (the fails-before lever for the new-hub class). The old-hub class, the storm's own
witness (the pre-815 half), runs under ROMP_LINKDROP_LAB=1 (about 140 s more: 138.6 and 137.5 s for its setUpClass, the mint and
its build included, in the drives of 2026-09-28 once the splice kept quiet pairs and each link-up phase's card wait ran to
its cap, the module whole at 230 and 228 s, `build857z/wip1-lab-knobs.log` and `build857z/c1-lab-knobs-2.log` outside the
repo;
skipped as optional without it, and the skip
reason names what then goes unexecuted and where the mechanisms PR 815 fixed are pinned) with one of two
hub knobs: ROMP_CORNER_OLD_HUB_ROOT (the corners lab's knob: a checkout of a hub kernel and prebuilt bundle from
before PR 815) boots the hub from that checkout as it is; ROMP_LINKDROP_OLD_HUB_BUILD=1 makes the class mint its own
private clone of this repository under its scratch directory, checked out detached at OLD_HUB_SHA (a main before PR
815; the objects are borrowed and nothing is written under this clone's .git), build the bundle there over this
checkout's node_modules, boot the hub from it and let the scratch's removal take it at teardown (the mint needs that
sha in the clone's history and the extension's node deps, so CI's served job skips the class as optional).
A hub a knob asked for is an error when its bundle cannot be made ready: lab_dist raises SkipTest when a build fails
(every served lab's stance for an environment that cannot build), and for this checkout's own bundle that skip stands,
but under ROMP_LINKDROP_OLD_HUB_BUILD=1, ROMP_CORNER_OLD_HUB_ROOT or ROMP_LINKDROP_HUB_ROOT the class re-raises it as
a RuntimeError carrying the build's words (_ready_dist), and a root one of those knobs names that holds no bin/romp-kernel
is the same error from _boot's kernel check (a mistyped root must not skip the class green), so a mint that succeeds and a
build that fails cannot leave a green run with the class skipped; ROMP_SERVED_TESTS_REQUIRE=1 still turns every remaining
skip into a failure, as on
CI's served step. ROMP_CORNER_REPORT_DIR gets one JSON per class with everything recorded.

What the old hub showed (2026-09-19, the bundle at 01d4fbe43): the old bundle dials no caps and decodes no patch, so
its Outline files one delta-unapplied row per remote feed patch. That correspondence is what the class pins: in each
window and over the whole drive, the rows equal, by rev, the feed slot patches the Outline's own relay sockets
received (the hook records a delta frame's rev; the row files the same rev). The count is one drive's, not a
property of the bundle: 3 / 0 / 3 / 3 across phase A, the link down, phase B and phase C in most recorded drives
(ROMP_LINKDROP_LAB=1 ROMP_LINKDROP_OLD_HUB_BUILD=1 pytest tests/test_federated_linkdrop_served.py). One reviewer
drive at the head the maintainer's round 1 ruled gave 3 / 0 / 1 / 3 (two relay sockets closed inside phase B and their retries' whole frames
absorbed two notices: no patch, so no row, and the equality held at 7 / 7), as did one verifier drive at the pass-2 head
whose hook was mutated for a red (its hub rows are real); and three builder drives gave 0 / 0 / 3 / 3 (the Outline's
relay socket closed 0.7 s into phase A and its retry's whole frame absorbed all three notices: phase A 0 rows to 0
patches, the drive 6 / 6 by rev): one at the pass-3 head, RED there on the per-phase at-least-one-patch floors of the
storm test and the phase-A drops test with the correspondence intact; one at the 30 s dwell on 2026-09-20, red on the
margin pin with its floors green; and one at this code the same day, green (`r5/lab-head2.log`). Those are the data
behind the allowance keyed on those closes (_outline_caught_up_whole: an empty phase is excused only when one of its notice posts
found the Outline holding no open relay socket that had received its first feed-family frame, and then only by a whole
keyed feed frame the Outline received there after the bundle's last notice could have been posted; in all three the
socket closed 0.7 s into phase A, between the first and second posts (the first, 0.01 s in, found it open and served;
the second and third, at 1.01 and 2.01 s, found no open socket, so the gap held at those two), and the frames came about
0.8 s after the last, 2.87, 2.83 and 2.86 s into phase A against a last notice posted from 2.01 s, so all three are green
on the floors under it). The population is counted as of that last drive, since any later drive can add either shape: the
builder's cache then held 18 old-hub records of the unmutated module (the builder's earlier drives at three pre-PR
vintages among them, two with a hand-built old hub), 15 at 3 / 0 / 3 / 3 and those 3 at 0 / 0 / 3 / 3, and the
reviewers' further drives at the head the maintainer's round 1 ruled gave 3 / 0 / 3 / 3 (the per-window table over the report JSONs outside the
repo, `python3 analyse.py <report.json>...`, with _rows_in's 1.5 s pad; analyse.py is a tool outside the repo that the PR body
names, so these counts cannot be re-checked from the tree). ZERO while the link was down in every recorded
drive. The storm
is gated on remote patches arriving, which is gated on the link: with phase D due while the link was down, no row
filed until the link returned, the return's whole frame carried D and filed no row for it, and the next patch (phase
B's) filed a row again. A relay redial does not end the storm but restarts it: each redial's one whole frame catches
the old page up once and the next patch freezes it again, so on a hub whose link comes and goes the storm pauses and
resumes with the link and looks intermittent and self-healing when it is neither. That is why the old-hub class
stays in this lab: a lab that only proves the fixed behaviour loses the evidence of what was fixed, and a reader in
three months must be able to learn that a redial used to restart the storm, and that without one the old page showed no
change. The new bundle files zero such rows across the same drive, and the three mutations recorded in the report (the
redial term stripped, the whole-frame base write dropped, the local-down gate dropped) each turn one of its assertions
red, so a zero here is a zero the drive can see through for those three mechanisms; it says nothing of the three latent
guards named above, which the drive cannot make red.

Every relay-socket close those records hold outside the drop and the restart, the closes in the shapes above included,
was the lab's own and not the old bundle's. LinkProxy, the splice, kept create_connection's 5 s timeout on its upstream
socket until it cleared it after the connect, as kernel.py _remote_ws clears the relay's, so a pair whose remote side sent
nothing for 5 s was shut, 5 to 10 s after the last frame other than a keepalive under the remote kernel's 10 s keepalive.
A census shows this (`python3 oldhub_closes.py <report.json>...`, a tool outside the repo that the PR body names, run on
2026-09-28 over one copy of each distinct old-hub report that the caches of this PR's review drives held at 20:01Z: 55
LinkDropOldLocal.json files by content, 167 with the copies; neither the tool nor the reports are in the tree, so the
census's figures below cannot be re-checked from it). The 41 made while the splice kept that timeout, at heads through 1fa8cfd4d, the earliest two PR 815's last commit and its
merge with the lab not yet committed (four heads since rewritten, several with uncommitted edits: mutated and
in-progress trees) and at f3094c4b7 with the timeout put back, hold 358 relay-socket closes outside the drop and the
restart, every one 4.95 to 10.01 s after its socket's last recorded frame and 345 of them on all three pages at one
instant. The 14 made with the timeout cleared, at fbd7b3ad0, fd38417e6 and f3094c4b7 and at 1fa8cfd4d with the clear
applied, hold none. Each cut was a redial, and its whole frame caught the old page up, so the drives made under the
cut recorded the old page catching up 6 to 19 s after each change, and one drive ran phase B's card wait to its 20 s
cap: a cut can come up to 10 s after the last frame, and late frames inside that phase put it past the wait. With the timeout
cleared the old page shows no change on a socket it holds. In every link-up phase the card wait runs to its cap with no
card shown, phase B's on the socket the link's return dialed, and only a redial's whole frame catches the page up
(phase A's cards after the return, phase B's after the restart). That freeze is the defect PR 815 fixed, and the
old-hub class asserts it. No socket closes inside a phase now, so the allowance above no longer fires, and a close
there reds the freeze test. The allowance is also overridden: the old class's margin yardstick needs a
card-carrying patch at the Outline in every link-up phase, so the storm and gate tests red on any phase the allowance
would excuse, whatever it returns, and only the phase-A drops test can still pass on it.

The driver ends before CI does. CI's served job runs every served lab in one pytest process under pytest-timeout's
600 s per-test cap (thread method: it ends the whole process), and the drive runs in setUpClass, so the node driver's
subprocess timeout sits under that cap with room for the boot around it (DRIVER_TIMEOUT_S), and every wait the driver
places draws on one shared budget (driver_budget_ms, BUDGET_JS) sized so the driver's worst case sits under the
subprocess timeout (driver_worst_case_s): a wait that never comes spends the budget once, every later wait returns at
once and is recorded as expired, and a degraded drive is this class's failure naming the wait, not a thread dump in
place of every served lab collected after this one. tests/test_federated_linkdrop_driver_bound.py pins the arithmetic
and the budget.

This lab boots subprocess kernels and drives Chromium; it loads no romp code in-process, so it carries no in-process
state-isolation preamble and is not scanned by tests/test_state_isolation_order.py (as its siblings). Synthetic
only: placeholder uuids, hostname TESTHOST, the notes-api demo's session names, invented card and todo text.
"""
import errno
import http.server
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
import uuid
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import lab_dist
import lab_ports

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
EXT = os.path.join(ROOT, "vscode-extension")
KERNEL_BIN = os.path.join("bin", "romp-kernel")   # a checkout's kernel entry point, relative: what _boot requires of every root it boots from
sys.path.insert(0, HERE)
import test_federated_dial_terms_served as _dial                   # noqa: E402  the two-kernel boot and check-in (the module)
import test_federated_capability_corners_served as _corners        # noqa: E402  the corners lab's constants and diag readers (the module)
import test_ship_reship_served as _lab                             # noqa: E402  the lab kernel's environment (the hub's respawn)

SID_R0, SID_R1, EXTRA, HOST, WID = _corners.SID_R0, _corners.SID_R1, _corners.EXTRA, _corners.HOST, _corners.WID
PROV_SEL, TODOS_ON = _corners.PROV_SEL, _corners.TODOS_ON
NOTICE_KEY = "linkdrop"                                                       # the card key's stem: linkdrop-<phase>-<n>
NOTICE_TITLE = "the notes-api index rebuild (%s, part %d) finished on TESTHOST"
TODO_TEXT = "check the notes-api ranking weights before rebuild %s"
APPEND_PROMPT = "rebuild %s: did the notes-api index rebuild finish?"
APPEND_REPLY = "Rebuild %s finished; the stemmer table is cached now."
NOTICES_PER_PHASE = 3        # cards per phase, a second apart: several patches per socket where a page decodes none
# A main before PR 815 (the merge of PR 818): its bundle reassembles remote feed slot patches with no per-connection state
# and dials no caps, so a remote at this checkout serves it slot patches it drops. The old-hub class mints a private clone
# checked out detached here under ROMP_LINKDROP_OLD_HUB_BUILD=1; ROMP_CORNER_OLD_HUB_ROOT names a built checkout of it (or
# of any other pre-815 main) instead. The sha is an ancestor of the fork's main (`git merge-base --is-ancestor <sha>
# origin/main` exits 0, 2026-09-20), so the objects the private clone borrows through its alternates file stay reachable
# in the clone it borrows from and no `git gc` there can prune them from under the checkout.
OLD_HUB_SHA = "01d4fbe43eed1226a1a3615c74f8d2ece79e5252"
NOTICE_GAP_S = 1.0
HUB_DOWN_S = 3.0             # the hub stays down this long before its respawn: past the relay's 2 s onclose retry, so that
#                              retry runs under the shim's local-down word (a boot faster than the retry would dial straight)
# a hub's client-diag rows that say a frame reached a pane raw or a delta found no base (the corners lab's list, plus the
# federation layer's own delta breadcrumbs by ev)
BAD_ROWS = _corners.BAD_ROWS
BAD_EVS = ("delta-unknown-slot", "delta-unkeyed-base")

# ---- the driver's bound ----
# CI's served job runs one pytest process over every served lab with pytest-timeout at 600 s per test, thread method
# (.github/workflows/ci.yml, the served step): a test that outlives it ends the WHOLE process, so a drive that hung here
# would take every served lab collected after this module with it and leave no summary. The drive runs in setUpClass, so
# the node driver's subprocess timeout sits under that cap with room for the boot around it (two kernels and the dist copy
# before the drive, the readers after; the module docstring's Knobs paragraph gives LinkDropBothNew's setUpClass as
# measured, with the date of the drives it was measured in), and the driver's own worst case
# (driver_worst_case_s: its wait budget plus the bounded work between the waits) sits under the subprocess timeout, so a
# degraded drive returns through its wait budget with the expired waits recorded or, for a hang in the control door,
# through driver_error ("driver timed out"), and the labs after this one still run.
# tests/test_federated_linkdrop_driver_bound.py pins the arithmetic, the budget and the bytes sent; the premise that every
# wait the driver places draws on the budget or is a fixed dwell the arithmetic counts is pinned there by regular expressions
# over the driver text and in tests/test_federated_linkdrop_driver_parsed_served.py over the compiler's parse (every receiver
# call allow-listed, every wait capped, by type), each module's docstring naming what it checks and the class it cannot see.
CI_TEST_TIMEOUT_S = 600      # pytest --timeout on CI's served step
BOOT_ROOM_S = 120            # setUpClass outside the drive: the kernels' boots, the dist copy, the readers after the drive
PROBE_TIMEOUT_S = BOOT_ROOM_S // 4   # _boot's playwright-browser probe (node resolving the browser's path), the one subprocess of setUpClass that had
#                              no timeout (the maintainer's round 6, extra4-3): a probe past it is an error naming the bound, never the no-browser skip
DRIVER_TIMEOUT_S = 480       # the node driver's subprocess timeout: CI_TEST_TIMEOUT_S - BOOT_ROOM_S
LAUNCH_TIMEOUT_S = 30        # playwright's default launch timeout: chromium.launch is handed no timeout option (the parsed module's config cell pins that
#                              the lab writes no `launch` key), so a launch that never comes ends there, then exit 3
DRIVER_FIXED_S = LAUNCH_TIMEOUT_S + 10   # the driver's work outside its waits and the control door: the launch, carried as a fixed term at its own bound
#                              (load-bearing against the headroom under DRIVER_TIMEOUT_S, which the arithmetic pin in
#                              tests/test_federated_linkdrop_driver_bound.py reports and holds this term at least the launch's; the maintainer's
#                              round 6, extra4-1: a sentence called the launch a wait the arithmetic does not count), and 10 s for the work between
#                              the waits: the visible reads (locator.count, which does not auto-wait), the marks, the JSON. The snapshots and the
#                              provisional-row read (page.evaluate, which takes no timeout option) are bounded reads that race against what is left
#                              of the budget (budget.bounded, BUDGET_JS), so their time is the budget's, not this term's.
POST_TIMEOUT_S = 5           # one control-door post to the remote (a notice, a todo); measured in milliseconds
HUB_TERM_WAIT_S = 10         # _restart_hub waits this long for SIGTERM to end the hub before SIGKILL
HUB_SPAWN_TRIES = 40         # _spawn_hub's /healthz tries, a 1 s probe and a 0.5 s pause each (the respawn answers in about a second)
PHASE_SETTLE_MS = 1500       # phase() lets the panes' rows land on the hub before marking the phase's end
DOWN_WINDOW_MARGIN = 2.0     # the while-down read comes this many of the drive's slowest link-up deliveries after phase D's post
#                              (_assert_the_down_window_outlasts_the_drives_slowest_delivery; down_dwell_ms is sized for it)
DOWN_READ_ROOM_MS = 2000     # the room down_dwell_ms holds past DOWN_WINDOW_MARGIN x wait_ms: a phase's delivery (seen.waitedMs) is stamped
#                              AFTER visible()'s reads (waitVisible), so a wait that resolved at the cap's edge is stamped past the cap by the
#                              reads' duration; without the room the margin pin could red on a drive whose link-up waits all resolved and
#                              showed. A phase whose wait ran to its cap is refused by the margin leg itself (seen.expired, pass 6), never
#                              measured against the room, so the room is for the reads after a wait that RESOLVED. The reads alone take
#                              6 to 22 ms where the wait had nothing left to wait for (D.seenAfterReturn.waitedMs over 34 recorded drives
#                              as of 2026-09-20, `python3 reads_census.py <report.json>...`, a tool outside the repo that the PR body
#                              names); over every unmutated recorded
#                              drive that carries the reading (the same command over the population as of 2026-09-20; the count is dated by
#                              drive elsewhere, since a drive at any head moves it) it runs 6 to 125 ms, the 125 ms one new-bundle drive's
#                              (`r6-margin/lab-head2.log`) where a wait still had a render to wait for, so the reading is an upper bound on
#                              the reads. Neither figure can be re-checked from the tree, since the tool and the reports are outside it.
#                              The room the reads get, this constant over DOWN_WINDOW_MARGIN (1 s: the relation pin divides
#                              through by the margin), is a floor far above them, not a fit.
#                              tests/test_federated_linkdrop_driver_bound.py pins down_dwell_ms >= DOWN_WINDOW_MARGIN x wait_ms + this
QUIET_TRIES, QUIET_STEP_MS = 7, 2000   # quiet(): up to QUIET_TRIES windows of QUIET_STEP_MS with no new relay frame on any page


def hub_restart_bound_s():
    """The control door's /restart-hub at its worst: the SIGTERM wait, the held-down spell, every /healthz try."""
    return HUB_TERM_WAIT_S + HUB_DOWN_S + HUB_SPAWN_TRIES * 1.5


def change_bundle_bound_s(changes):
    """One /change at its worst: the gaps between the notices and every post at POST_TIMEOUT_S (the append is a file write)."""
    posts = (NOTICES_PER_PHASE if "notice" in changes else 0) + (1 if "todo" in changes else 0)
    return (NOTICES_PER_PHASE - 1) * NOTICE_GAP_S + posts * POST_TIMEOUT_S


def driver_worst_case_s(cls):
    """The longest the class's driver can run: its wait budget (every wait it places draws on it, BUDGET_JS; the snapshots
    and the provisional-row read race against what is left of it, budget.bounded, so they are inside this term) plus the
    work between the waits that the budget does not cover, each at its own bound: the down dwell, the hub restart, the
    change bundles (A, D, B and, with the local drop, C), the phases' settles, and DRIVER_FIXED_S (the launch at
    playwright's default timeout and the work between the waits). The browser's close after the RESULT line is outside
    this sum: it discards no measurement (_drive keeps a RESULT the kill left whole). Pinned under DRIVER_TIMEOUT_S by
    tests/test_federated_linkdrop_driver_bound.py, which reports the headroom."""
    phases = 3 if cls.local_drop else 2
    restart = hub_restart_bound_s() if cls.local_drop else 0.0
    return ((cls.driver_budget_ms + cls.down_dwell_ms + phases * PHASE_SETTLE_MS) / 1000.0 + restart
            + (phases + 1) * change_bundle_bound_s(cls.changes) + DRIVER_FIXED_S)


def _root_knob(name):
    return _corners._root_knob(name)


def _post(port, token, route, body):
    req = urllib.request.Request("http://127.0.0.1:%d%s?token=%s" % (port, route, token), data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=POST_TIMEOUT_S) as resp:
        return json.loads(resp.read().decode())


def _pair(sid, cwd, prompt, reply, parent, now=None):
    """One CLOSED user/assistant pair for `sid` chained to `parent` (the seed's last assistant row, or the previous
    append's), as _dial.change_pair mints one; returns (jsonl text, the assistant row's uuid) so the next phase's
    append chains to this one and the transcript stays one line, not a fork."""
    now = time.time() if now is None else now
    u, a = str(uuid.uuid4()), str(uuid.uuid4())
    rows = [{"type": "user", "uuid": u, "parentUuid": parent, "sessionId": sid, "cwd": cwd,
             "timestamp": _dial._stamp(now - _dial.CHANGE_USER_AGO_S), "promptSource": "typed",
             "message": {"role": "user", "content": prompt}},
            {"type": "assistant", "uuid": a, "parentUuid": u, "sessionId": sid, "cwd": cwd,
             "timestamp": _dial._stamp(now - _dial.CHANGE_REPLY_AGO_S),
             "message": {"role": "assistant", "model": "claude-opus-5", "stop_reason": "end_turn",
                         "content": [{"type": "text", "text": reply}]}}]
    return "".join(json.dumps(r) + "\n" for r in rows), a


class LinkProxy:
    """A TCP splice on one fixed port to the remote kernel's port, in the test process: the lab's stand-in for the hub's
    ssh -L forward, so the link can be dropped and restored while both kernels stay up. listen() listens and splices each
    accepted connection to the target; drop() closes the listener (a dial is refused, as at a dead -L listener), shuts
    every spliced pair (both ends read EOF: the hub's upstream, the remote's client) and returns once the listener's
    accept loop has ended; resume() listens again on the same port; stop() drops the link, joins every thread the splice
    started, fails naming any still alive at its bound and releases the port. Every transition is stamped for the record.

    The port is the splice's from construction until stop(): a socket bound to it that never listens holds it, so no socket
    that binds without SO_REUSEPORT can take it before listen() or between a drop() and its resume() (a socket of the same
    user that sets SO_REUSEPORT still can), and each listener binds it beside that socket through SO_REUSEPORT. The splice took its port from a free-port probe that closed its socket, and the port
    was then free for anyone to take until listen() bound it, and again across every drop. On Linux, where the served job
    runs this lab, a dial to a port that is bound and not listening is refused, so a dial while the link is dropped is
    refused as before, as at a dead -L listener, which is the refusal the hub's relay starts its redial road from (the
    module docstring). That holds from the moment drop() returns, because drop() waits for the accept loop of the listener
    it closed: on Linux a closed listener that a select is waiting on keeps listening until that select returns (within
    the loop's 0.2 s), so without the wait a dial straight after drop() connected to it and was reset, and a resume()
    straight after drop() bound a second listener beside it through SO_REUSEPORT, and the system could hand a dial to the
    closed one, which reset it the same way (the maintainer's round 7, correctness-2). None of this was measured on
    another system: LinkProxyEnds also runs on macOS, in a macOS Python cell, which only a manual dispatch of CI with its
    macos input on starts, and requires there only that such a dial does not connect. LinkProxyEnds holds the port bound
    from construction until stop().

    The upstream socket's timeout is cleared once it connects, as the kernel's own relay clears it (kernel.py _remote_ws:
    create_connection's timeout would otherwise cut the long-lived splice), so a pair stays up however long its remote side
    is quiet, as it does through an ssh -L forward. Before that line the splice kept create_connection's 5 s timeout: the
    pump reading the remote timed out after 5 s with no bytes and shut the pair, and under the remote kernel's 10 s
    keepalive (KEEPALIVE_S, which no lab kernel changes) that cut came 5 to 10 s after the last frame other than a
    keepalive. Every relay-socket close the old-hub records show outside the drop and the restart was that cut, and not
    the old bundle (the module docstring gives the census): each cut was a redial whose whole frame caught the old page
    up, which is how the old-hub class then passed the visibility waits it now asserts run out. A cut coming up to 10 s
    after the last frame is also the cause of the phase-B expiry recorded once at 20 s: late frames inside the phase put
    the cut that would have caught the page up past the 20 s wait. LinkProxyEnds holds that a pair quiet for longer than
    5 s is kept.

    The splice owns its threads and ends them in stop(), which tearDownClass calls on every exit path. The thread-stop
    census on main (tests/test_thread_stop_census.py) reads each start here as object-owned through stop() by any call in
    stop() whose name is on its list of stop verbs, and stop() makes three: the thread joins, the message's str.join, and
    the holder's close in its finally (since 327b2c39a), any one of which is enough. So the census would read the starts the
    same with the drop() call gone, though drop() is what makes the threads return, and with every join gone as well; so
    LinkProxyEnds runs stop() over a live pair and holds that every thread has ended when it returns, and stop() itself
    fails naming any thread its joins did not end. The opener is named listen() and not start() because that census
    reads every `.start()` call as a thread start and cannot resolve an instance of this class, which is not a Thread."""

    STOP_BOUND_S = 10.0   # the bound on drop()'s wait for the accept loop and stop()'s one bound over every join; LinkProxyEnds shortens it on an instance to reach the failure

    def __init__(self, target_port):
        self.target = int(target_port)
        # the holder: bound to the port here, never listening, closed by stop() (the class docstring says why)
        self._hold = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._hold.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        self._hold.bind(("127.0.0.1", 0))
        self.port = self._hold.getsockname()[1]
        self._lsock = None
        self._acceptor = None   # the accept loop of the live listener, which drop() waits for once it closes that listener
        self._down = True
        self._pairs = set()
        self._lock = threading.Lock()
        self._threads = []   # every accept and pump thread started, for stop() to join
        self.events = []

    def listen(self):
        if self._lsock is not None:
            # SO_REUSEPORT would let a second listener bind beside the first, and a dial the system handed to the listener
            # no accept loop reads would sit in its backlog, never spliced. Before SO_REUSEPORT the bind refused a second
            # listener both while one was up and while a dropped one was still listening (the class docstring says when):
            # the first is refused here, and drop() outlasts the second by waiting for that listener's accept loop
            raise RuntimeError("the splice is already listening on port %d (resume() follows a drop())" % self.port)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)   # the port the holder has bound since construction
        s.bind(("127.0.0.1", self.port))
        s.listen(64)
        s.setblocking(False)
        self._lsock = s
        self._down = False
        t = threading.Thread(target=self._accept, args=(s,), daemon=True, name="linkproxy-accept")
        self._acceptor = t
        with self._lock:
            self._threads.append(t)
        t.start()
        self.events.append({"ev": "up", "t": time.time()})
        return {"port": self.port}

    def _accept(self, s):
        # select with a short timeout, not a blocking accept: drop() closing the listener from another thread does not
        # reliably wake a blocked accept(), and a connection already in the backlog when the listener closed could be
        # spliced onto the live remote AFTER a drop (a stray frame crossing a "dropped" link, seen in run 1). This loop
        # owns the one socket it was started with and exits the instant that socket is no longer the live listener or
        # _down is set, re-checks _down after every accept, and checks again, under the lock where it registers the pair,
        # that its socket is still the live listener: the connect to the target sits between the first check and the
        # registration, and a drop there (stop()'s own included) clears _lsock and sweeps the pairs without this one; so
        # no connection is ever spliced past a drop. drop() then waits for this loop to return, and on Linux that is also
        # when the closed listener stops listening (a select waiting on it holds it open until the select returns), so no
        # dial reaches the closed listener after drop() returns, and a resume() after it listens alone.
        import select
        while s is self._lsock and not self._down:
            try:
                r, _, _ = select.select([s], [], [], 0.2)
            except (OSError, ValueError):
                # the listener closed between the loop's check and this select (drop() runs on another thread): a closed
                # socket's descriptor reads -1, which select refuses with a ValueError, or the descriptor went away inside
                # the call (OSError, EBADF); either is this loop's end, not a failure of its thread
                return
            if not r:
                continue
            try:
                c, _ = s.accept()
            except (OSError, BlockingIOError):
                continue
            if self._down or s is not self._lsock:
                try:
                    c.close()
                except OSError:
                    pass
                return
            c.setblocking(True)
            try:
                u = socket.create_connection(("127.0.0.1", self.target), timeout=5)
            except OSError:
                c.close()
                continue
            u.settimeout(None)   # create_connection's timeout would otherwise cut a pair whose remote side is quiet for 5 s (kernel.py _remote_ws clears it too)
            pair = (c, u)
            with self._lock:   # drop() clears _lsock and then sweeps _pairs under this lock: a pair it did not sweep sees it here
                late = s is not self._lsock
                if not late:
                    self._pairs.add(pair)
            if late:
                for x in pair:
                    try:
                        x.close()
                    except OSError:
                        pass
                return
            for a, b in ((c, u), (u, c)):
                t = threading.Thread(target=self._pump, args=(a, b, pair), daemon=True, name="linkproxy-pump")
                with self._lock:
                    self._threads.append(t)
                t.start()

    def _pump(self, a, b, pair):
        try:
            while True:
                d = a.recv(65536)
                if not d:
                    break
                b.sendall(d)
        except OSError:
            pass
        finally:
            for s in pair:
                try:
                    s.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
            with self._lock:
                self._pairs.discard(pair)

    def drop(self):
        t = time.time()
        self._down = True
        s, self._lsock = self._lsock, None
        if s is not None:
            try:
                s.close()
            except OSError:
                pass
        with self._lock:
            pairs = list(self._pairs)
            self._pairs.clear()
        for pair in pairs:
            for s in pair:
                try:
                    s.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                try:
                    s.close()
                except OSError:
                    pass
        self.events.append({"ev": "down", "t": t, "spliced": len(pairs)})
        loop, self._acceptor = self._acceptor, None
        if loop is not None:
            # the closed listener keeps listening while the loop's select waits on it (the class docstring), so drop()
            # returns only once the loop has, within STOP_BOUND_S, and past that fails naming it, as stop() does
            loop.join(self.STOP_BOUND_S)
            if loop.is_alive():
                raise AssertionError("the dropped listener's accept loop outlived drop()'s %.1f s bound: %s" % (self.STOP_BOUND_S, loop.name))
        return {"port": self.port, "spliced": len(pairs)}

    def resume(self):
        return self.listen()

    def stop(self):
        """End the splice for good, and fail if it did not end. drop() is the release. It sets _down and closes the
        listener, so the accept loop returns by its next select: the loop's check sees the drop, or the select on the
        closed listener raises and the loop takes that as its end, or a select already waiting returns within its 0.2 s
        and the check follows (a connection accepted just before the drop is closed at the check after the accept, or
        where its pair would have been registered). And it shuts every spliced pair, so both pumps of each read EOF and
        return. drop() waits for that accept loop itself, within STOP_BOUND_S, and raises naming it past that bound. Every
        thread the splice started is then joined, all of them within one bound (STOP_BOUND_S) counted from drop()'s
        return, the list re-read after each round of joins so that a thread recorded while this was joining (a pump of a
        pair the drop had just swept, which ends at once, or the accept thread of a listen() that raced the teardown,
        which does not) is joined too or named. A thread still alive at the bound fails the teardown with an AssertionError naming it,
        where a timed join that returned in silence would let a splice that never ended pass (tearDownClass still kills
        the kernels and removes the lab when this raises). The held port is closed last, whether or not this raises."""
        try:
            self.drop()
            deadline = time.monotonic() + self.STOP_BOUND_S
            while True:
                with self._lock:
                    live = [t for t in self._threads if t.is_alive()]
                if not live or time.monotonic() >= deadline:
                    break
                for t in live:
                    t.join(max(0.0, deadline - time.monotonic()))
            if live:
                raise AssertionError("the link splice's threads outlived stop()'s %.1f s bound: %s"
                                     % (self.STOP_BOUND_S, ", ".join(sorted(t.name for t in live))))
        finally:
            self._hold.close()


class _Control(threading.Thread):
    """The driver's door into the test process, one small HTTP server: POST /drop and /resume move the link, POST
    /restart-hub restarts the hub kernel, POST /change {phase} makes the phase's change bundle on the remote. Every
    answer is JSON with `ok`; an op that raises answers 500 with the message, so the driver records it instead of
    hanging. The driver calls it from node (not from a page), so no CORS is involved."""

    def __init__(self, lab):
        super().__init__(daemon=True, name="linkdrop-control")
        self.lab = lab
        self.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), self._handler())
        self.port = self.srv.server_address[1]

    def _handler(self):
        lab = self.lab

        class H(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _reply(self, code, obj):
                b = json.dumps(obj).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(b)))
                self.end_headers()
                self.wfile.write(b)

            def do_POST(self):
                n = int(self.headers.get("Content-Length") or 0)
                try:
                    body = json.loads(self.rfile.read(n).decode() or "{}") if n else {}
                except ValueError:
                    body = {}
                op = self.path.split("?")[0].strip("/")
                try:
                    if op == "drop":
                        ans = lab.proxy.drop()
                    elif op == "resume":
                        ans = lab.proxy.resume()
                    elif op == "restart-hub":
                        ans = lab._restart_hub()
                    elif op == "change":
                        ans = lab._change(str(body.get("phase") or ""))
                    else:
                        return self._reply(404, {"ok": False, "error": "no such op %r" % op})
                except Exception as e:   # the driver records the failure; a hang here would hide it
                    return self._reply(500, {"ok": False, "error": str(e)[:300]})
                ans = dict(ans or {})
                ans["ok"] = True
                ans["t"] = time.time()
                self._reply(200, ans)
        return H

    def run(self):
        self.srv.serve_forever()

    def stop(self):
        try:
            self.srv.shutdown()
            self.srv.server_close()
        except Exception:
            pass


# The driver's waits share ONE budget (cfg.driverBudgetMs, the class's driver_budget_ms): every timeout the driver hands
# playwright and every poll loop of its own is capped at what is left of it, so a wait that never comes spends the budget
# once, every later wait returns at once and is recorded as expired, and the driver ends inside its subprocess timeout
# (DRIVER_TIMEOUT_S) instead of pytest-timeout ending the whole served pytest process at CI's per-test cap. A page read with
# no timeout of its own (page.evaluate takes no timeout option and waits on the page's promise with no default bound: the
# snapshots, the provisional-row read) goes through `bounded`, a race against what is left of the budget that records an
# expiry and returns the caller's fallback (the maintainer's round 6, extra4-2: those reads were allow-listed as calls known
# not to wait). Pure in `now` and `sleep`, so tests/test_federated_linkdrop_driver_bound.py runs it under node with a clock
# of its own; DRIVER opens with it.
BUDGET_JS = r"""
const makeBudget = ({ budgetMs, now, sleep, out }) => {
  const t0 = now();
  const left = () => Math.max(0, t0 + budgetMs - now());
  const capped = (ms) => Math.max(1, Math.min(ms, left()));   // playwright reads a timeout of 0 as NO timeout: never 0
  const waitFor = async (fn, timeout, what) => {              // poll fn every 250 ms until it holds or the capped timeout ends
    const cap = capped(timeout), s = now();
    while (now() - s < cap) { if (await fn()) return true; await sleep(capped(250)); }
    out.timeouts.push(what + (left() === 0 ? " (the driver's wait budget was spent)" : "")); return false;
  };
  const expired = {};                                          // the race's own token: no page read returns it
  const bounded = async (p, what, fallback) => {              // a read with no timeout of its own, raced against what is left of the budget
    const v = await Promise.race([p, sleep(capped(left())).then(() => expired)]);
    if (v !== expired) return v;
    out.timeouts.push(what + " expired" + (left() === 0 ? " (the driver's wait budget was spent)" : "")); return fallback;
  };
  return { left, capped, waitFor, bounded };
};
"""

# The Chromium driver (the corners lab's hook, per SOCKET): every WebSocket a page dials is recorded with its URL, its
# kind (relay: the /remote/<host>/ws path), its dial, open and close stamps, the close code and cleanliness, the shim's
# local-up word at the dial, and, on a relay socket, every non-keepalive frame's type, slot and size; every needSlot,
# needFullFeed and ready the page sends is recorded with the socket it left on. The phases run in node against the
# control door (cfg.ctl) and the hub's /tunnels; marks stamp every transition for the Python side's windows.
DRIVER = BUDGET_JS + r"""
import { createRequire } from "node:module";
import fs from "node:fs";
const require = createRequire(process.env.EXT_PKG);
const { chromium } = require("playwright");
const cfg = JSON.parse(fs.readFileSync(process.env.CFG, "utf8"));
let browser;
try { browser = await chromium.launch(cfg.launch || {}); }
catch (e) { console.error("browser-launch-failed: " + e); process.exit(3); }
const context = await browser.newContext({ viewport: { width: 1200, height: 700 } });
const out = { pages: {}, marks: {}, phases: {}, tunnels: [], ctl: {}, timeouts: [], quietGaveUp: [], console: [], provBefore: null, died: null, budget: null };
// the sleep's timer is unref'd: every bounded read leaves one pending for what was left of the budget, and a pending timer must not
// hold the node process open after the drive (the browser connection holds it open through the drive, so the timer still fires on time)
const budget = makeBudget({ budgetMs: cfg.driverBudgetMs, now: Date.now, sleep: (ms) => new Promise((r) => setTimeout(r, ms).unref()), out });
const hook = (o) => {
  window.__socks = []; window.__sends = []; const W = window.WebSocket;
  const strip = (u) => o.stripCaps && u.indexOf("/remote/") !== -1 ? u.replace(/([?&])caps=[^&]*&?/, (m, sep) => sep).replace(/[?&]$/, "") : u;
  window.WebSocket = function (url, protos) {
    const u = strip(String(url));
    const relay = u.indexOf("/remote/") !== -1;
    const rec = { i: window.__socks.length, url: u, relay, dialedAt: Date.now(), localUpAtDial: window.__rompLocalUp === undefined ? null : window.__rompLocalUp,
                  openAt: null, closeAt: null, code: null, clean: null, frames: [], local: 0 };
    window.__socks.push(rec);
    const w = protos === undefined ? new W(u) : new W(u, protos);
    w.addEventListener("open", () => { rec.openAt = Date.now(); });
    w.addEventListener("close", (ev) => { rec.closeAt = Date.now(); rec.code = ev.code; rec.clean = !!ev.wasClean; });
    w.addEventListener("message", (ev) => {
      try {
        const m = JSON.parse(ev.data);
        if (!m || m.type === "ka") return;
        if (!relay) { rec.local++; return; }
        const f = { t: String(m.type), slot: m.slot ? String(m.slot) : "", len: String(ev.data).length, at: Date.now() };
        if (m.type === "feed" || m.type === "feedDelta") { f.asks = Array.isArray(m.asks) ? m.asks.length : null; f.buildId = m.buildId; }
        if (m.type === "delta") { f.coll = Object.keys(m.coll || {}); f.restAll = !!m.restAll; f.rev = m.rev; }
        rec.frames.push(f);
      } catch (e) {}
    });
    const send = w.send.bind(w);
    w.send = (d) => {
      try { const m = JSON.parse(d); if (m && (m.type === "needSlot" || m.type === "needFullFeed" || m.type === "ready")) window.__sends.push({ sock: rec.i, kind: relay ? "relay" : "local", type: m.type, slot: m.slot ? String(m.slot) : "", at: Date.now() }); } catch (e) {}
      return send(d);
    };
    return w;
  };
  window.WebSocket.prototype = W.prototype; window.WebSocket.CONNECTING = 0; window.WebSocket.OPEN = 1; window.WebSocket.CLOSING = 2; window.WebSocket.CLOSED = 3;
};
const pages = {};
const APPS = cfg.apps;
const mark = (k) => { out.marks[k] = Date.now(); };
// a snapshot is a page.evaluate, a read with no timeout option: bounded by the budget (an expired snapshot is recorded in out.timeouts and reads as empty)
const snap = async (page) => budget.bounded(page.evaluate(() => ({ socks: (window.__socks || []).map((s) => Object.assign({}, s, { frames: s.frames.slice() })), sends: (window.__sends || []).slice(), localUp: window.__rompLocalUp === undefined ? null : window.__rompLocalUp })), "snap", { socks: [], sends: [], localUp: null });
const ctl = async (op, body) => {
  const r = await fetch(cfg.ctl + "/" + op, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) });
  const j = await r.json(); out.ctl[op + (body && body.phase ? ":" + body.phase : "")] = j; return j;
};
const tunnelsStatus = async () => {
  let st = "error";
  try { const r = await fetch(cfg.tunnelsUrl, { cache: "no-store" }); const j = await r.json(); const row = (j.tunnels || []).find((t) => t.host === cfg.host); st = row ? String(row.status) : "absent"; } catch (e) {}
  out.tunnels.push({ at: Date.now(), status: st }); return st;
};
const waitFor = budget.waitFor;
const relayFramesTotal = async () => { let n = 0; for (const app of APPS) { const s = await snap(pages[app]); for (const k of s.socks) if (k.relay) n += k.frames.length; } return n; };
// cfg.quietStepMs with no new relay frame on any page, up to cfg.quietTries tries; a give-up is recorded (out.quietGaveUp),
// not fatal: a page whose relay socket keeps being replaced keeps frames coming, and the phase still runs; a spent budget
// is a give-up too
const quiet = async (what) => {
  for (let i = 0; i < cfg.quietTries; i++) {
    if (budget.left() === 0) { out.quietGaveUp.push(what + " (the driver's wait budget was spent)"); return; }
    const a = await relayFramesTotal(); await pages[APPS[0]].waitForTimeout(budget.capped(cfg.quietStepMs)); if (await relayFramesTotal() === a) return;
  }
  out.quietGaveUp.push(what);
};
const provText = () => pages.fleet ? budget.bounded(pages.fleet.evaluate((sel) => { const e = document.querySelector(sel); return e ? e.textContent : null; }, cfg.provSel), "provText", null) : Promise.resolve(null);
// a card's id on the hub's feed page: a remote NOTICE card's id wears its host (federation.ts prefixNoticeId, the project's PR 1831,
// taken in fold 4), and the old hub bundle shows the bare id; either form is the card, so a read that the card is absent (phase D
// while the link is down, the old bundle's frozen phases) still reads the form the page's bundle mints
const cardSel = (ch, n) => { const bare = 'notice:' + cfg.sid + ':' + ch.noticeKeys[n] + ':' + ch.noticeRevs[n];
  return '[data-key="a:' + cfg.host + ':' + bare + '"], [data-key="a:' + bare + '"]'; };
const visible = async (ch) => {
  const v = { cards: [] };
  for (let n = 0; n < ch.noticeKeys.length; n++) v.cards.push((await pages.feed.locator(cardSel(ch, n)).count()) > 0);
  if (pages.waiting && ch.todoText) v.todo = (await pages.waiting.locator(".ut-text", { hasText: ch.todoText }).count()) > 0;
  if (pages.fleet && ch.prompt) v.prov = await provText();
  return v;
};
// the phase's visibles, waited for CONCURRENTLY (three pages, three waiters), so the point is bounded by ms, not three
// times it, and each waiter's timeout draws on the budget. Each wait's OUTCOME is recorded, never swallowed (pass 6): a
// wait that expires names itself in v.expired and in out.timeouts with the phase, because waitedMs alone cannot tell a
// delivery at the cap from a wait that ran to its cap with nothing delivered, and the gate legs read waitedMs as this
// drive's delivery (_assert_the_down_window_outlasts_the_drives_slowest_delivery requires v.expired empty before it does)
const waitVisible = async (ch, ms, what) => {
  const t0 = Date.now();
  const last = ch.noticeKeys.length - 1;
  const expired = [];
  const outcome = (name, p) => p.then(() => true, (e) => {
    expired.push(name);
    out.timeouts.push(what + ": the " + name + " wait expired" + (budget.left() === 0 ? " (the driver's wait budget was spent)" : "") + ": " + String(e).split("\n")[0].slice(0, 160));
    return false;
  });
  const waits = [outcome("card", pages.feed.locator(cardSel(ch, last)).first().waitFor({ state: "attached", timeout: budget.capped(ms) }))];
  if (pages.waiting && ch.todoText) waits.push(outcome("todo", pages.waiting.locator(".ut-text", { hasText: ch.todoText }).first().waitFor({ timeout: budget.capped(ms) })));
  if (pages.fleet && ch.prompt) waits.push(outcome("prompt", pages.fleet.waitForFunction(([sel, t]) => { const e = document.querySelector(sel); return !!e && e.textContent === t; }, [cfg.provSel, ch.prompt], { timeout: budget.capped(ms) })));
  await Promise.all(waits);
  const v = await visible(ch); v.waitedMs = Date.now() - t0; v.expired = expired; return v;
};
const freshRelayWithFeed = async (sinceKey) => { for (const app of APPS) { const s = await snap(pages[app]); if (!s.socks.some((k) => k.relay && k.dialedAt >= out.marks[sinceKey] && k.frames.some((f) => f.t === "feed"))) return false; } return true; };
const phase = async (name) => {
  await quiet("before phase " + name);
  mark(name + "0");
  const ch = await ctl("change", { phase: name });
  const rec = { change: ch, seen: await waitVisible(ch, cfg.waitMs, "phase " + name) };
  await pages.feed.waitForTimeout(cfg.phaseSettleMs);   // let the panes' rows land on the hub
  mark(name + "1");
  for (const app of APPS) rec[app] = await snap(pages[app]);
  out.phases[name] = rec;
  return ch;
};
try {
  for (const app of APPS) {
    const page = await context.newPage();
    page.on("pageerror", () => {});
    page.on("console", (msg) => { const t = msg.text(); if (t.indexOf("federation:") === 0) out.console.push({ app, at: Date.now(), text: t.slice(0, 300) }); });
    await page.addInitScript(hook, { stripCaps: !!cfg.stripCaps });
    await page.goto(cfg.urls[app], { timeout: budget.capped(cfg.pageWaitMs) });
    pages[app] = page;
  }
  for (const app of APPS) {   // the start's waits draw on the budget too; one that expires throws, and the driver ends (out.died)
    await pages[app].waitForFunction(() => (window.__socks || []).some((s) => s.relay), null, { timeout: budget.capped(cfg.pageWaitMs) });
    await pages[app].waitForFunction(() => (window.__socks || []).some((s) => s.relay && s.frames.some((f) => f.t === "feed")), null, { timeout: budget.capped(cfg.pageWaitMs) });
  }
  mark("ready");
  out.provBefore = await provText();
  const chA = await phase("A");
  // (2) the link drops: the splice's listener and every spliced pair close. First the precondition the drop leg reads, made a
  // designed guarantee (pass 5): every page holds exactly ONE open relay socket. In the old-hub drives the splice's former
  // 5 s idle cut closed a page's socket for its 2 s retry every few seconds, and before this wait the drop landed 0.58 to
  // 0.80 s after the pages' redials reopened in ten of the sixteen recorded old-hub drives
  // (`python3 held_census.py <report.json>...`, a tool outside the repo that the PR body names, so the count cannot be
  // re-checked from the tree): the feed page's redial-to-visible latency plus the settle against the retry, a coincidence
  // and not a guarantee. `held` is the snapshot that
  // satisfied the wait (or the last poll's, when it expired and the wait is recorded), so the drop leg reads what the wait saw.
  const heldNow = async () => { const h = {}; for (const app of APPS) { const s = await snap(pages[app]); h[app] = s.socks.filter((k) => k.relay && k.openAt && !k.closeAt).map((k) => k.i); } return h; };
  let held = await heldNow();
  await waitFor(async () => { held = await heldNow(); return APPS.every((app) => held[app].length === 1); }, cfg.waitsMs.held, "every page holds one open relay socket before the drop");
  mark("drop");
  await ctl("drop");
  out.phases.drop = { held };
  await waitFor(async () => { for (const app of APPS) { const s = await snap(pages[app]); if (held[app].some((i) => !s.socks[i].closeAt)) return false; } return true; }, cfg.waitsMs.closed, "every held relay socket closes after the drop");
  mark("closed");
  await waitFor(async () => (await tunnelsStatus()) !== "up", cfg.waitsMs.rowDown, "the hub's row leaves up");
  mark("rowDown");
  out.phases.drop.rowStatus = await tunnelsStatus();
  // (2b) a change is DUE while the link is down: phase D's bundle goes to the remote's real port through the control door
  // (not through the splice), so every page is owed a patch and nothing can carry it; the pages must not see it until
  // the link returns, and the return must carry it in the redial's whole frame, not as a replayed patch
  mark("D0");
  const chD = await ctl("change", { phase: "D" });
  mark("D1");
  await pages.feed.waitForTimeout(cfg.downDwellMs);   // dwell with the row down: dialing ceases once the poll reads it
  mark("settled");
  for (const app of APPS) out.phases.drop[app] = await snap(pages[app]);
  out.phases.D = { change: chD, seenWhileDown: await visible(chD) };
  // (3) the link returns: the supervisor reads the row up, the pages' polls dial again
  mark("resume");
  await ctl("resume");
  await waitFor(async () => (await tunnelsStatus()) === "up", cfg.waitsMs.rowUp, "the hub's row returns to up");
  mark("rowUp");
  await waitFor(() => freshRelayWithFeed("resume"), cfg.waitsMs.redialed, "a fresh relay socket per page holds the remote's full frame after the link's return");
  mark("redialed");
  out.phases.D.seenAfterReturn = await waitVisible(chD, cfg.waitMs, "phase D after the link's return");   // the redial's whole frame carries the change made while the link was down
  const chB = await phase("B");
  out.phases.B.seenA = await visible(chA);
  out.phases.B.seenD = await visible(chD);
  // (5) the LOCAL socket: the hub kernel restarts, the pages' own sockets and every relay splice die together
  if (cfg.localDrop) {
    mark("restart");
    await ctl("restart-hub");
    mark("restarted");
    await waitFor(async () => { for (const app of APPS) { const s = await snap(pages[app]); if (!s.socks.some((k) => !k.relay && k.dialedAt >= out.marks.restart && k.openAt)) return false; } return true; }, cfg.waitsMs.localUp, "the pages' local sockets reopen");
    mark("localUp");
    await waitFor(() => freshRelayWithFeed("restart"), cfg.waitsMs.redialed2, "a fresh relay socket per page holds the remote's full frame after the local return");
    mark("redialed2");
    const chC = await phase("C");
    out.phases.C.seenA = await visible(chA);
    out.phases.C.seenB = await visible(chB);
    out.phases.C.seenD = await visible(chD);
  }
  mark("end");
  out.budget = { ms: cfg.driverBudgetMs, leftMs: budget.left() };   // how much of the wait budget a drive leaves: the record's margin
  for (const app of APPS) out.pages[app] = await snap(pages[app]);
} catch (e) {
  out.died = String(e).slice(0, 400);
  for (const app of Object.keys(pages)) { try { out.pages[app] = await snap(pages[app]); } catch (e2) {} }
}
console.log("RESULT:" + JSON.stringify(out));
await browser.close();
"""


class _LinkDrop(unittest.TestCase):
    """One drive: the roots (None = this checkout), whether the page strips the caps term, which changes make the
    bundle, whether the local drop runs, the waits."""
    maxDiff = None
    hub_root = None            # the hub kernel's checkout (bin/) and, when not None, its PREBUILT vscode-extension/dist
    hub_knob = None            # the environment knob that named hub_root, when one did: the runner ASKED for that hub, so its
    #                            bundle failing to come ready is an error with the build's words, not a skip (_boot)
    remote_root = None         # the remote kernel's checkout (bin/)
    old_hub_build = False      # _boot mints hub_root as a private clone checked out at OLD_HUB_SHA under the lab (the old-hub class's second knob)
    old_hub_wt = None          # that checkout's path while it exists: under cls.lab, so the lab's rmtree takes it down
    strip_caps = False
    caps = True                # the hub bundle dials caps=feedDelta: DECLARED per class, never derived from the roots, so the
    #                            fails-before lever (an old hub named by ROMP_LINKDROP_HUB_ROOT) turns the new class red instead of adapting it
    changes = ("notice", "todo", "append")
    local_drop = True
    wait_ms = 20000           # each point's visibles after a change (the card, the todo, the provisional row), waited for concurrently
    # The driver's waitFor caps by the mark each wait ends at: each a floor set well above the slowest wait recorded, not a
    # ratio of it (against the upper bounds in the table below the ratios run from 5.8x for rowDown to 870x for held, worked
    # from this comment's own figures), with driver_budget_ms as the binding bound (BUDGET_JS: every wait draws on it). The
    # spans are ONE derivation with the excuse and attach figures (`population_drive.py`, the tool
    # _outline_caught_up_whole's docstring names, which reads every counted record's marks, prints the sentence below whole
    # and under --check reads this comment for it, the markers folded; pass 10, the maintainer's round 5 extra8-3, after
    # this paragraph and the delivery sentence below were hand-kept copies of a population dated one drive apart). The tool
    # and the records are outside the repo, the tool named in the PR body, so the spans cannot be re-checked from the tree.
    # The table below counts ONE drive, made at the landing head with both knobs set, and its records alone (the
    # coordinator's ruling G on the maintainer's round 7: no record made under the splice's former idle cut is mixed in), so
    # each span's bounds are that drive's and nothing before or after it. The pastes before it counted every unmutated drive
    # in the builder's cache as of a named drive, the old-hub ones made under the cut (the repo's history holds those
    # pastes), and any drive may move a bound, so the caps are floors far above every bound, not fits.
    # The spans by mark pair over the 2 unmutated records of the drive at `landing/lab-final.log` (2026-09-29; 1 new-bundle
    # and 1 old-hub, the only drive counted): closed, drop -> closed, 0.017 to 0.148 s; rowDown, closed -> rowDown, 0.515 to
    # 6.84 s; rowUp, resume -> rowUp, 1.02 to 1.02 s; redialed, rowUp -> redialed, 1.54 to 3.31 s; localUp, restarted ->
    # localUp, 0.014 to 0.276 s; redialed2, localUp -> redialed2, 0.271 to 0.791 s; held, A1 -> drop, 18 to 23 ms over the 2
    # records that carry the held wait.
    # rowDown is the supervisor's silent-poll window (longest, in the pastes before this one, under the old-hub drives'
    # relay churn, the splice's former idle cut); rowUp a quarter-second pass inside the supervisor's fast window and its
    # steady 15 s pass outside it; localUp the
    # reopen alone (the restart itself, SIGTERM and the 3 s held down, is the control door's and not this wait's). held,
    # A1 -> drop (every page holding one open relay socket
    # before the drop), is new in pass 5 and has no recorded span before it: every drive since carries it (`out.phases.drop.held`
    # in the record), and its span is the snapshot's own time with every page already holding one socket; its cap is closed's,
    # a floor well above the mechanism's worst (a page lacks an open socket for the relay's 2 s retry plus the open, once per
    # close of its socket, which the splice's former idle cut made every few seconds), not a fit to those spans.
    waits_ms = {"held": 20000, "closed": 20000, "rowDown": 40000, "rowUp": 40000, "redialed": 30000, "localUp": 30000, "redialed2": 30000}
    page_wait_ms = 30000      # the start, per page: its load, its first relay socket, that socket's whole frame
    driver_budget_ms = 225000  # every wait the driver places draws on this one budget. The budget is a DEADLINE, not a meter of the
    #                            waits: makeBudget fixes t0 at the driver's start, capped(ms) is min(ms, what is left to the deadline), and
    #                            the fixed dwells and the control-door calls run to their own bounds whether or not it has passed (their
    #                            time before it draws it down too). So the budget less the record's budget.leftMs is the drive's WALL
    #                            CLOCK from the launch to the end mark, the 42 s dwell and the settles included, not a sum of its waits:
    #                            78.4 s on the new bundle in the drive of 2026-09-20 (225000 less budget.leftMs in
    #                            `r6-margin/lab-head1.log`'s reports, the builder's lab logs outside the repo), and 133.0 and 132.4 s on
    #                            the old in the drives of 2026-09-28 once the splice kept quiet pairs (the reports of
    #                            `build857z/wip1-lab-knobs.log` and `build857z/c1-lab-knobs-2.log`): the old page shows no change on a
    #                            socket it holds, so each link-up phase's card wait runs its full wait_ms and its drives run longer.
    #                            225 s, not 240, so the worst case holds the 42 s dwell under DRIVER_TIMEOUT_S.
    # The row stays down this long after phase D's post, and the gate DEPENDS on it (the maintainer's round 2's ruling): the while-down read of D
    # comes DOWN_WINDOW_MARGIN times the drive's own slowest link-up delivery after the post, asserted by both classes' gate legs
    # (_assert_the_down_window_outlasts_the_drives_slowest_delivery). The dwell is sized against the lab's own cap on that
    # delivery, not against the drives seen: on this checkout's bundle a phase's delivery is seen.waitedMs, and waitVisible caps every wait it holds at
    # wait_ms and records each wait's outcome (seen.expired), so the margin leg itself refuses a phase whose wait ran to its cap
    # (pass 6), beside the visibility legs, and every delivery it measures is a wait that RESOLVED, before its cap; the dwell is
    # DOWN_WINDOW_MARGIN x wait_ms plus DOWN_READ_ROOM_MS of room for the reads that follow the wait, so the pin holds for every
    # drive whose link-up waits all resolved and showed, the reads inside the room, and reds only for a window shorter than that
    # (tests/test_federated_linkdrop_driver_bound.py pins the relation). In the old-hub records made under the splice's
    # former idle cut, a redial every few seconds caught the frozen old page up with its whole frame, and a change whose
    # three notices straddled a cut waited for the frame after that, so the slowest delivery those records held was the old
    # bundle's (the pastes before the landing head carried it; the repo's history holds them). With the cut gone the old
    # page shows no change inside the cap at all: over the 2 unmutated records of both classes of the drive at
    # `landing/lab-final.log` (2026-09-29), the only drive counted, the slowest delivery recorded is the new bundle's, 1,296
    # ms over its 3 link-up phases whose waits resolved, the maximum of their seen.waitedMs; on the old bundle the card wait
    # of each of its 3 link-up phases ran to its cap (seen.expired), the longest 20,007 ms, so it showed no card inside the
    # cap (one derivation with the waits paragraph above, `population_drive.py`, which prints this sentence whole and checks
    # it here, reading seen.expired so that a wait that ran to its cap is not counted as a delivery; a tool outside the repo
    # that the PR body names, so the figures cannot be re-checked from the tree). The old-hub class times its gate by the
    # Outline's patch instead (LinkDropOldLocal._link_up_delivery_ms), under a second in its drives, so the new
    # bundle's cap is what sizes the dwell.
    # A dwell of 30 s, sized at twice the 12.9 s
    # then recorded, redded on the very next drive (19.0 s): a threshold fitted to the data at hand is no threshold, which is
    # why the cap sizes it. driver_worst_case_s stays under DRIVER_TIMEOUT_S with the budget at driver_budget_ms (472.5 s for
    # the new class, 452.5 s for the old-hub class). It is also a quiescent tail well past one 4 s /tunnels poll.
    down_dwell_ms = 42000
    quiet_tail_ms = 6000      # no relay dial in this window before resume: the poll read the row down and connect() gated on live=false
    apps = ("waiting", "fleet", "feed")

    @classmethod
    def setUpClass(cls):
        if cls is _LinkDrop:
            raise unittest.SkipTest("the base class")
        cls.procs, cls.proxy, cls.ctl = [], None, None
        try:
            cls._boot()
        except BaseException:
            cls.tearDownClass()
            raise

    @classmethod
    def _knobs(cls):
        """Subclasses resolve their roots here; a missing knob skips the class. The base gates nothing: the new-bundle
        class needs nothing this checkout's served labs lack, so it runs wherever they run, CI's served job included
        (the maintainer's round 1: a lab gated whole was the one served lab of 94 with no executing test in CI, and it guards PR 815)."""
        return None

    @classmethod
    def _boot(cls):
        if not os.path.isdir(os.path.join(EXT, "node_modules", "playwright")):
            raise unittest.SkipTest("extension deps absent (npm ci not run here), the served lab needs them")
        try:
            probe = subprocess.run(["node", "-e", "const p=require(process.argv[1]);process.stdout.write(p.chromium.executablePath())",
                                    os.path.join(EXT, "node_modules", "playwright")], capture_output=True, text=True, timeout=PROBE_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            raise AssertionError("the playwright browser probe (node resolving chromium's executable path) did not finish in %d s (PROBE_TIMEOUT_S, a quarter of "
                                 "BOOT_ROOM_S): a wedged node, not a missing browser, so an error and no skip" % PROBE_TIMEOUT_S)
        if probe.returncode != 0 or not os.path.exists(probe.stdout.strip()):
            raise unittest.SkipTest("no playwright browser on this box, the served lab needs one (CI installs none)")
        cls._knobs()
        if cls.hub_root is None and not cls.old_hub_build:
            cls.hub_root = _root_knob("ROMP_LINKDROP_HUB_ROOT")   # the base-hub lever, for a class that names no hub of its own
            if cls.hub_root:
                cls.hub_knob = "ROMP_LINKDROP_HUB_ROOT"
        for route in ("/notice", "/usertodo"):
            if not _corners._serves(cls.remote_root, route):
                raise unittest.SkipTest("the remote kernel at %s serves no %s: this lab's change bundle needs it" % (cls.remote_root or ROOT, route))
        cls.lab = tempfile.mkdtemp(prefix="federated-linkdrop-")
        if cls.old_hub_build:
            cls.hub_root = cls._mint_old_hub()
        for root in (cls.hub_root, cls.remote_root):
            if root and not os.path.isfile(os.path.join(root, KERNEL_BIN)):
                if root == cls.hub_root and cls._asked():   # _ready_dist's rule, one statement earlier: a hub the runner asked for is an error, not a skip
                    raise RuntimeError("%s asked for the hub at %s and it has no %s (a root the runner named and mistyped must not skip the class)"
                                       % (cls._asked(), root, KERNEL_BIN))
                raise unittest.SkipTest("no %s under %s" % (KERNEL_BIN, root))
        cls._ready_dist()
        for name in ("testhost", "hub"):
            root = os.path.join(cls.lab, name, "xdg", "romp")
            os.makedirs(root, exist_ok=True)
            Path(root, "user-todos-enabled.json").write_text(TODOS_ON)
            Path(root, "update-mode.json").write_text(json.dumps({"mode": "off"}))
        cls.rport, cls.rtoken = lab_ports.reserve(cls.lab), "testtok-remote-ld"
        cls.hport, cls.htoken = lab_ports.reserve(cls.lab), "testtok-hub-ld"
        rp, cls.rlog = _dial._kernel(cls.lab, "testhost", cls.rport, cls.rtoken, [(SID_R0, "api", 1), (SID_R1, "worker", 2)] + EXTRA,
                                     bin_dir=os.path.join(cls.remote_root or ROOT, "bin"))
        cls.procs.append(rp)
        cls.proxy = LinkProxy(cls.rport)
        cls.proxy.listen()
        cls.hub_proc, cls.hlog = _dial._kernel(cls.lab, "hub", cls.hport, cls.htoken, [], bin_dir=os.path.join(cls.hub_root or ROOT, "bin"))
        cls.procs.append(cls.hub_proc)
        cls.hub_restarts = []
        _dial.checkin(cls.hport, cls.htoken, cls.proxy.port, cls.rtoken, lab=cls.lab)   # the peer's kernelPort IS the splice: the relay and the probes go through it
        cls.transcript = cls._transcript_path()
        cls.append_parent = _dial.seed_uuid(1, _dial.SEED_PAIRS - 1, "a")   # api's seed tag is 1: the first append chains to its last reply
        cls.changes_made = []
        cls.ctl = _Control(cls)
        cls.ctl.start()
        cls.result, cls.driver_error, cls.driver_note = None, None, None
        cls._drive()
        cls.hub_row = cls._hub_tunnels_row()
        cls.remote_sha = (cls.hub_row or {}).get("kernelSha") or ""
        cls.remote_wire = cls._remote_wire_memos()
        cls.hub_diag_rows = _corners.read_hub_diag_rows(cls.lab)
        cls.remote_wsopen = cls._remote_wsopen_rows()
        cls._report()

    @classmethod
    def _asked(cls):
        """The knob that asked for the hub, when one did (ROMP_LINKDROP_OLD_HUB_BUILD=1 minting it, or the knob hub_knob records
        as naming hub_root), else None. A hub the runner asked for that cannot boot is an error carrying the cause, never a
        skip: _boot's kernel check and _ready_dist share this one rule (the maintainer's round 1's tests-3; pass 5 found the kernel check
        outside it, so a mistyped root skipped the class green)."""
        return "ROMP_LINKDROP_OLD_HUB_BUILD=1" if cls.old_hub_build else cls.hub_knob

    @classmethod
    def _ready_dist(cls):
        """The hub's bundle, serve-ready under the lab: the minted checkout's, built by the harness bound to THAT checkout
        (its own dist, lock and marker, its own config's inputs) and copied, as copy_dist does for this checkout's; a
        knob-named checkout's PREBUILT dist copied; else this checkout's own. lab_dist answers an environment that cannot
        build with unittest.SkipTest (esbuild failing, node finding no package: every served lab's stance), and for this
        checkout's own bundle that skip stands, as in every other served lab. When a knob ASKED for the hub
        (ROMP_LINKDROP_OLD_HUB_BUILD=1 minting it, or ROMP_CORNER_OLD_HUB_ROOT or ROMP_LINKDROP_HUB_ROOT naming it:
        hub_knob) the same skip is re-raised as a RuntimeError carrying the build's words, because a mint that succeeds and
        a build that fails otherwise skip the class and the run reports green (the maintainer's round 1's tests-3, ruled twice), while the
        mint's own failure raises by design; the WHOLE statement is wrapped, the constructor included, since DistBuild's
        default inputs can skip through esbuild_exports before copy_to runs. tests/test_federated_linkdrop_driver_bound.py
        pins both arms against a stub build, and the kernel check in _boot (a knob-named root with no
        bin/romp-kernel) under the same rule."""
        asked = cls._asked()
        try:
            if cls.old_hub_wt:
                lab_dist.DistBuild(ext=os.path.join(cls.old_hub_wt, "vscode-extension"), root=cls.old_hub_wt).copy_to(os.path.join(cls.lab, "dist"))
            elif cls.hub_root:
                src = os.path.join(cls.hub_root, "vscode-extension", "dist")
                if not os.path.isfile(os.path.join(src, "federation.js")):
                    raise unittest.SkipTest("no prebuilt dist under %s (build the extension there first)" % cls.hub_root)
                lab_dist.copy_prebuilt(src, os.path.join(cls.lab, "dist"))
            else:
                lab_dist.copy_dist(os.path.join(cls.lab, "dist"))
        except unittest.SkipTest as e:
            if not asked:
                raise
            raise RuntimeError("%s asked for the hub at %s and its bundle could not be made ready (a skip in every other served lab, an "
                               "error here because the runner asked): %s" % (asked, cls.old_hub_wt or cls.hub_root, e)) from e

    @classmethod
    def _mint_old_hub(cls):
        """A private checkout of this repository at OLD_HUB_SHA under the lab's scratch: the old hub's kernel (bin/) and
        the source of its bundle, for a box with no such checkout at hand. It is a CLONE that borrows this clone's
        objects (git clone --shared --no-checkout writes an alternates file in the new clone and nothing under this
        clone's .git), then checks the sha out detached. Never a worktree of this clone, which every session on the box
        shares: a worktree add registers a record there, an interrupted add leaves that record locked where no remove
        of ours may reach it, and a repo-wide clearing of stale records at teardown is not a test's to run (the maintainer's round 1).
        Everything the mint makes lives under cls.lab, so teardown is the lab's rmtree, and no git command of this
        class names this clone as its -C target (tests/test_federated_linkdrop_mint.py pins that against a scratch
        repository). The checkout's vscode-extension/node_modules is a symlink to THIS checkout's (the old config's own
        inputs are all in its tree; a hand-built checkout for ROMP_CORNER_OLD_HUB_ROOT is built the same way), and
        _boot builds its bundle through lab_dist bound to the checkout, so the build has the harness's lock and marker
        inside the checkout's own dist and the lab's copy is serve-ready. The runner asked for the mint by setting the
        knob, so a clone that fails or a sha this clone does not hold is an error with git's words, never a skip."""
        wt = os.path.join(cls.lab, "oldhub")
        clone = subprocess.run(["git", "clone", "--quiet", "--shared", "--no-checkout", ROOT, wt], capture_output=True, text=True, timeout=300)
        if clone.returncode != 0:
            raise RuntimeError("ROMP_LINKDROP_OLD_HUB_BUILD=1: this clone could not be cloned under the lab for the checkout at %s: %s"
                               % (OLD_HUB_SHA, (clone.stderr or clone.stdout).strip()[-400:]))
        co = subprocess.run(["git", "-C", wt, "checkout", "--quiet", "--detach", OLD_HUB_SHA], capture_output=True, text=True, timeout=300)
        if co.returncode != 0:
            raise RuntimeError("ROMP_LINKDROP_OLD_HUB_BUILD=1: the private clone could not check out %s: %s" % (OLD_HUB_SHA, (co.stderr or co.stdout).strip()[-400:]))
        cls.old_hub_wt = wt
        os.symlink(os.path.realpath(os.path.join(EXT, "node_modules")), os.path.join(wt, "vscode-extension", "node_modules"))
        return wt

    @classmethod
    def _transcript_path(cls):
        proj = os.path.join(cls.lab, "testhost", "claude", "projects")
        cands = [p for p in Path(proj).rglob(SID_R0 + ".jsonl")]
        if not cands:
            raise unittest.SkipTest("no transcript for the api session under %s" % proj)
        return str(cands[0])

    @classmethod
    def _spawn_hub(cls):
        """The hub kernel again on its port, state root and dist (the respawn of _dial._kernel's boot, without the seeding
        that boot did: the state is on disk, remotes.json and client-diag.jsonl included); the log appends."""
        lab_hub = os.path.join(cls.lab, "hub")
        env = _lab.kernel_env(lab_hub, os.path.join(lab_hub, "claude"), os.path.join(cls.lab, "dist"), cls.hport, cls.htoken, ROMP_HOST_NAME="HUB")
        proc = subprocess.Popen([os.path.join(cls.hub_root or ROOT, "bin", "romp-kernel")], stdout=open(cls.hlog, "a"), stderr=subprocess.STDOUT, env=env)
        why = lab_ports.wait_owned(proc, env, tries=HUB_SPAWN_TRIES)   # a 1 s probe and a 0.5 s pause each: hub_restart_bound_s counts them
        if not why:
            return proc
        proc.kill()
        proc.wait()
        raise RuntimeError("the respawned hub kernel never served /healthz: " + why)

    @classmethod
    def _restart_hub(cls):
        """The LOCAL drop: SIGTERM the hub kernel, keep it down HUB_DOWN_S (past the relay's 2 s onclose retry, so that retry
        runs under the shim's local-down word), respawn it. The pages' local sockets and every relay splice die with the
        process; nothing else is touched."""
        t0 = time.time()
        p = cls.hub_proc
        p.terminate()
        try:
            p.wait(timeout=HUB_TERM_WAIT_S)
        except subprocess.TimeoutExpired:
            p.kill()
            p.wait()
        t_dead = time.time()
        time.sleep(HUB_DOWN_S)
        cls.hub_proc = cls._spawn_hub()
        cls.procs.append(cls.hub_proc)
        rec = {"downAt": t0, "deadAfterS": round(t_dead - t0, 2), "heldDownS": HUB_DOWN_S, "upAt": time.time(), "exit": p.returncode}
        cls.hub_restarts.append(rec)
        return rec

    @classmethod
    def _change(cls, phase):
        """The phase's change bundle on the remote: NOTICES_PER_PHASE completed notice cards a second apart (keys
        linkdrop-<phase>-<n>), one user todo, one closed pair appended to api's transcript; each named by the phase so
        the pages' visibles tell the phases apart. Returns what was posted and the remote's answers."""
        rec = {"phase": phase, "t0": time.time(), "noticeKeys": [], "noticeRevs": [], "notices": []}
        if "notice" in cls.changes:
            for n in range(NOTICES_PER_PHASE):
                if n:
                    time.sleep(NOTICE_GAP_S)
                key = "%s-%s-%d" % (NOTICE_KEY, phase.lower(), n + 1)
                ans = _post(cls.rport, cls.rtoken, "/notice", {"id": SID_R0, "key": key, "title": NOTICE_TITLE % (phase, n + 1), "needsYou": False, "producer": "lab"})
                rec["noticeKeys"].append(key)
                rec["noticeRevs"].append((ans.get("notice") or {}).get("rev"))
                rec["notices"].append(ans)
        if "todo" in cls.changes:
            rec["todoText"] = TODO_TEXT % phase
            rec["todo"] = _post(cls.rport, cls.rtoken, "/usertodo", {"id": SID_R0, "text": rec["todoText"]})
        if "append" in cls.changes:
            rec["prompt"] = APPEND_PROMPT % phase
            text, cls.append_parent = _pair(SID_R0, os.path.join(cls.lab, "testhost", "proj"), rec["prompt"], APPEND_REPLY % phase, cls.append_parent)
            with open(cls.transcript, "a") as fh:
                fh.write(text)
            rec["appended"] = len(text)
        rec["t1"] = time.time()
        cls.changes_made.append(rec)
        return rec

    @classmethod
    def _drive(cls):
        cfg = os.path.join(cls.lab, "cfg.json")
        conf = {"urls": {app: "http://127.0.0.1:%d/%s?wid=%s&token=%s" % (cls.hport, app, WID, cls.htoken) for app in cls.apps},
                "tunnelsUrl": "http://127.0.0.1:%d/tunnels?token=%s" % (cls.hport, cls.htoken),
                "ctl": "http://127.0.0.1:%d" % cls.ctl.port, "host": HOST, "sid": SID_R0,
                "stripCaps": cls.strip_caps, "localDrop": cls.local_drop, "waitMs": cls.wait_ms, "downDwellMs": cls.down_dwell_ms, "apps": list(cls.apps), "provSel": PROV_SEL,
                "waitsMs": dict(cls.waits_ms), "pageWaitMs": cls.page_wait_ms, "driverBudgetMs": cls.driver_budget_ms,
                "phaseSettleMs": PHASE_SETTLE_MS, "quietTries": QUIET_TRIES, "quietStepMs": QUIET_STEP_MS}
        with open(cfg, "w") as f:
            json.dump(conf, f)
        driver = os.path.join(cls.lab, "driver.mjs")
        with open(driver, "w") as f:
            f.write(DRIVER)
        try:
            # DRIVER_TIMEOUT_S sits under CI's per-test cap (CI_TEST_TIMEOUT_S, pytest-timeout on the served step) with
            # BOOT_ROOM_S for the rest of setUpClass, and above driver_worst_case_s(cls), so a drive that outlives it is a
            # hang in the control door and ends here as this class's driver_error, not as pytest-timeout ending the process
            p = subprocess.run(["node", driver], capture_output=True, text=True, timeout=DRIVER_TIMEOUT_S,
                               env=dict(os.environ, EXT_PKG=os.path.join(EXT, "package.json"), CFG=cfg))
        except subprocess.TimeoutExpired as e:
            # the driver prints its RESULT line before `await browser.close()`, so a kill at DRIVER_TIMEOUT_S can land in the close
            # with the record whole in the partial output: that record is HELD, since a discarded measurement is not a hang (the
            # maintainer's round 6, extra4-4); a RESULT line the kill truncated stays driver_error, and the kill is noted either way
            so = e.stdout if isinstance(e.stdout, str) else (e.stdout or b"").decode()
            line = next((ln for ln in so.splitlines() if ln.startswith("RESULT:")), None)
            if line is None:
                cls.driver_error = "driver timed out; partial output:\n%s" % so
                return
            try:
                cls.result = json.loads(line[len("RESULT:"):])
            except ValueError as err:
                cls.driver_error = "driver timed out after printing a RESULT line the kill left truncated (%s); partial output:\n%s" % (err, so)
                return
            cls.driver_note = ("the driver outlived DRIVER_TIMEOUT_S (%d s) after printing its RESULT line and was killed in its close; the record is held whole "
                               "(the browser's close is outside the arithmetic: it comes after the last mark and discards no measurement)" % DRIVER_TIMEOUT_S)
            return
        if p.returncode == 3:
            raise unittest.SkipTest("no playwright browser on this box, the served leg needs one (CI installs none)")
        if p.returncode != 0:
            cls.driver_error = "driver failed:\n" + p.stdout[-3000:] + p.stderr[-3000:]
            return
        line = next((ln for ln in p.stdout.splitlines() if ln.startswith("RESULT:")), None)
        if line is None:
            cls.driver_error = "driver printed no result:\n" + p.stdout[-3000:] + p.stderr[-3000:]
            return
        cls.result = json.loads(line[len("RESULT:"):])

    @classmethod
    def _hub_tunnels_row(cls):
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d/tunnels?token=%s" % (cls.hport, cls.htoken), timeout=5) as r:
                rows = json.loads(r.read().decode()).get("tunnels") or []
        except Exception:
            return None
        return next((t for t in rows if t.get("host") == HOST), None)

    @classmethod
    def _remote_wire_memos(cls):
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d/perf?token=%s" % (cls.rport, cls.rtoken), timeout=5) as r:
                perf = json.loads(r.read().decode())
            cls.remote_sends = perf.get("sends") if isinstance(perf.get("sends"), dict) else {}
            return ((perf.get("memos") or {}).get("wire")) or {}
        except Exception as e:
            cls.remote_sends = {}
            return {"error": str(e)}

    @classmethod
    def _remote_wsopen_rows(cls):
        """The remote's own record of every relay dial it accepted (kernel.py _note_ws_open: surface kernel, what wsopen,
        data.kind relay, data.reconnect the dial's term), in file order."""
        path = os.path.join(cls.lab, "testhost", "xdg", "romp", "client-diag.jsonl")
        rows = []
        try:
            with open(path) as fh:
                for ln in fh:
                    try:
                        r = json.loads(ln)
                    except ValueError:
                        continue
                    if r.get("surface") == "kernel" and r.get("what") == "wsopen" and (r.get("data") or {}).get("kind") == "relay":
                        rows.append({"t": r.get("t"), "app": (r.get("data") or {}).get("app"), "reconnect": bool((r.get("data") or {}).get("reconnect"))})
        except OSError:
            pass
        return rows

    @classmethod
    def _report(cls):
        d = (os.environ.get("ROMP_CORNER_REPORT_DIR") or "").strip()
        if not d:
            return
        os.makedirs(d, exist_ok=True)
        by_kind = {}
        for r in cls.hub_diag_rows:
            k = "%s/%s" % (r.get("surface"), r.get("what"))
            if r.get("surface") == "federation" and r.get("what") == "hostconn":
                k += ":" + str((r.get("data") or {}).get("ev"))
            by_kind[k] = by_kind.get(k, 0) + 1
        rec = {"lab": cls.__name__, "hub_root": cls.hub_root, "remote_root": cls.remote_root, "strip_caps": cls.strip_caps, "changes": list(cls.changes),
               "remote_sha": cls.remote_sha, "driver_error": cls.driver_error, "driver_note": cls.driver_note, "result": cls.result, "remote_wire": cls.remote_wire,
               "remote_sends": getattr(cls, "remote_sends", {}), "hub_diag_by_kind": by_kind, "hub_diag_rows": cls.hub_diag_rows,
               "remote_wsopen_relay": cls.remote_wsopen, "proxy_events": cls.proxy.events if cls.proxy else [], "hub_restarts": cls.hub_restarts,
               "changes_made": cls.changes_made}
        Path(d, cls.__name__ + ".json").write_text(json.dumps(rec, indent=1, sort_keys=True))

    @classmethod
    def tearDownClass(cls):
        try:
            if getattr(cls, "ctl", None):
                cls.ctl.stop()
            if getattr(cls, "proxy", None):
                cls.proxy.stop()   # raises naming any splice thread still alive at its bound; the kernels end below regardless
        finally:
            for p in getattr(cls, "procs", []):
                try:
                    p.kill()
                    p.wait()
                except Exception:
                    pass
            lab_ports.release(getattr(cls, "lab", ""))
            shutil.rmtree(getattr(cls, "lab", ""), ignore_errors=True)   # the minted checkout, if any, is under the lab

    # ---- the readers ----
    def _driver_ran(self):
        if getattr(type(self), "driver_error", None):
            self.fail(type(self).driver_error)
        if getattr(type(self), "result", None) is None:
            raise unittest.SkipTest("the driver produced no result")
        if self.result.get("died"):
            self.fail("the driver died: %s (timeouts: %r)" % (self.result["died"], self.result.get("timeouts")))

    def _marks(self):
        self._driver_ran()
        m = self.result.get("marks") or {}
        self.assertIn("end", m, "the driver ran every phase (marks %r, timeouts %r)" % (sorted(m), self.result.get("timeouts")))
        return m

    def _page(self, app):
        self._driver_ran()
        rec = (self.result.get("pages") or {}).get(app)
        self.assertTrue(rec, "the %s page reported its sockets and sends" % app)
        return rec

    def _relay_socks(self, app, k0=None, k1=None):
        """The app's relay sockets, in dial order, those dialed in [k0, k1) when marks are given."""
        m = self._marks()
        socks = [s for s in self._page(app)["socks"] if s["relay"]]
        if k0:
            socks = [s for s in socks if s["dialedAt"] >= m[k0]]
        if k1:
            socks = [s for s in socks if s["dialedAt"] < m[k1]]
        return socks

    def _kinds(self, sock, since_ms=0):
        return [(f["t"], f["slot"]) for f in sock["frames"] if f["at"] >= since_ms]

    def _first_feed_family(self, sock):
        for f in sock["frames"]:
            if f["t"] in ("feed", "feedDelta", "delta"):
                return f
        return None

    def _sends(self, app, kind, typ, k0=None, k1=None):
        m = self._marks()
        out = [s for s in self._page(app)["sends"] if s["kind"] == kind and s["type"] == typ]
        if k0:
            out = [s for s in out if s["at"] >= m[k0]]
        if k1:
            out = [s for s in out if s["at"] < m[k1]]
        return out

    def _rows_in(self, k0, k1, slack_s=1.5):
        """The hub's client-diag rows stamped inside the marks' window, padded by slack_s on BOTH sides (the kernel stamps
        a row at receipt, in whole seconds; a row the shim queued while its socket was down is stamped at the flush). The
        pad is symmetric on purpose: the kernel's stamp is a whole-second floor, so a row an event just after a mark
        caused can carry a second that precedes the mark (a zero left pad dropped a real phase-A row in one measured
        run), and a row lands after the closing mark by the flush's lag. Adjacent marks (A1 and drop are milliseconds
        apart) therefore give overlapping windows; the down window's exact zero holds because phase() waits 1500 ms
        after the visibles before A1, so phase A's last row is stamped before the down window's padded start, a
        separation the numbers give rather than a designed guarantee. The residual no pad tuning removes: a row queued
        while a page's local socket was down and flushed late lands anywhere in the down window (the maintainer's round 1, tests-6)."""
        m = self._marks()
        t0, t1 = m[k0] / 1000.0 - slack_s, m[k1] / 1000.0 + slack_s
        return [r for r in self.hub_diag_rows if t0 <= float(r.get("t") or 0) <= t1]

    def _hostconn(self, ev, rows=None):
        rows = self.hub_diag_rows if rows is None else rows
        return [r for r in rows if _corners.is_page_federation_row(r) and (r.get("data") or {}).get("ev") == ev]

    def _bad_rows(self, rows=None):
        rows = self.hub_diag_rows if rows is None else rows
        bad = [(r.get("surface"), r.get("what"), r.get("data")) for r in rows if (r.get("surface"), r.get("what")) in BAD_ROWS]
        bad += [("federation", "hostconn", r.get("data")) for r in rows if _corners.is_page_federation_row(r) and (r.get("data") or {}).get("ev") in BAD_EVS]
        return bad

    def _outline_unapplied(self, rows=None):
        rows = self.hub_diag_rows if rows is None else rows
        return [r.get("data") for r in rows if (r.get("surface"), r.get("what")) == ("outline", "delta-unapplied")]

    def _outline_feed_patches(self, k0=None, k1=None, slack_s=1.5):
        """The feed slot patches ({type: delta, slot: feed}) the OUTLINE page's own relay sockets received, stamped by the
        hook at receipt (the browser's clock), inside the marks' window padded as _rows_in pads rows; the whole drive
        without marks. The Outline is the page that files outline/delta-unapplied on the old bundle, one row per such
        patch carrying the patch's rev, so these are the rows' other side."""
        frames = [f for s in self._page("fleet")["socks"] if s["relay"] for f in s["frames"] if f["t"] == "delta" and f["slot"] == "feed"]
        if k0 or k1:
            m = self._marks()
            t0 = m[k0] - slack_s * 1000 if k0 else float("-inf")
            t1 = m[k1] + slack_s * 1000 if k1 else float("inf")
            frames = [f for f in frames if t0 <= f["at"] <= t1]
        return frames

    def _outline_served_at(self, socks, t_ms):
        """Whether at t_ms (the browser's clock, the hook's stamps) one of the sockets was OPEN and already SERVED: its openAt at
        or before t_ms, its closeAt None or at or after t_ms, and its first feed-family frame (_first_feed_family) at or before
        t_ms. A socket with no openAt never opened (a churn's dial that never connected; a synthetic socket recording no open)
        and serves nothing: that reading is deliberate, a frame on a socket that never opened is not a frame the page held."""
        for s in socks:
            if s.get("openAt") and s["openAt"] <= t_ms and (s.get("closeAt") is None or s["closeAt"] >= t_ms):
                first = self._first_feed_family(s)
                if first and first["at"] <= t_ms:
                    return True
        return False

    def _outline_caught_up_whole(self, k0, k1, slack_s=1.5):
        """The excuse for an empty phase window, keyed on the GAP that could have swallowed the notices and then on the frame
        that caught the page up: the whole keyed feed frames that reached the Outline's relay sockets after the bundle's LAST
        notice could have been posted and before k1 + slack_s, returned ONLY when at least one of the phase's notice posts
        happened while the Outline held no open relay socket that had already received its first feed-family frame
        (_outline_served_at at each derived post time; every post served means nothing could have swallowed a notice, so no
        later frame excuses the window). The mechanism excused: a relay socket closing inside the phase (the 2 s retry
        redials, the remote serves the new socket a whole frame), whose whole frame absorbs the notices posted while the
        socket was down, so that phase's change crosses as no patch and files no row. In the old-hub records every such close
        was the splice's idle cut, every few seconds until LinkProxy cleared its upstream timeout, not the old bundle; with
        the cut gone no phase holds such a gap, and a close inside a phase reds
        test_without_a_redial_the_old_page_does_not_show_the_change. The allowance is overridden as well as unused: a
        phase it excuses holds no card-carrying patch at the Outline, and LinkDropOldLocal._link_up_delivery_ms, the margin
        leg's yardstick on the old bundle, fails any such phase, so the storm test and the gate test red on it whatever
        this returns; only the phase-A drops test (test_the_old_bundle_drops_every_remote_patch_and_asks_the_local_kernel)
        can still pass on it. The
        distinguishing datum an empty window needs (the maintainer's round 2's ruling on correctness-1: the allowance is keyed on this EVENT,
        read from the hook's frames, never a dropped requirement). Pass 8 added the gap (the maintainer's round 3, extra6-1)
        because the frame alone was no key: in the records made under the splice's idle cut, a redial produced a whole frame
        after the phase's notices were already delivered as patches, so the frame-only excuse was available in windows that
        held patches and a planted gating miss (a phase's patches and rows removed from the record) stayed green at both
        floors, while keyed on the gap it was available only in windows with no patch and the planted miss reds (the pastes
        before the landing head counted this over those records; the repo's history holds them). A real gating miss during
        such a close is indistinguishable from the close in the record, the excuse's remaining hole and the price of
        excusing the close at all. The figures here count ONE drive, made at the landing head with the cut gone, and its
        records alone (the coordinator's ruling G on the maintainer's round 7): the frame-only excuse was available in 0 of
        the 3 phase windows (A, B, C) over the 1 unmutated old-hub record of the drive at `landing/lab-final.log`
        (2026-09-29), the only drive counted, so load-bearing (a window with no patch) in none; keyed on the gap it is
        available in 0 of those 3 and load-bearing in none. Over all 3 windows the planted miss (the phase's feed patches
        and rows removed, every frame kept) reds the floor in 3 and stays excused in 0. Every figure in this paragraph, the
        population, its drive and the counts, is
        ONE derivation (the maintainer's round 4: a hand-kept pair of a count and a drive drifted apart twice, one drive behind each time),
        made by tools outside the repo that the PR body names (population_drive.py, population6.py, excuse_census.py and
        census_module.py) over records outside it, so no figure in this paragraph can be re-checked from the tree:
        `population_drive.py --check <tests_dir> <pass-7 head tests_dir>` in the builder's cache outside the repo lists the
        records by `population6.py` and names the drive whose reports directory holds the NEWEST counted record by the
        record's own end mark (the maximum by end mark then path: two records of one drive sharing an end mark take the
        lexically greatest path, and a tie across reports directories, a copied record, is refused, since nothing dates it;
        the maintainer's round 6, extra9-5: max() over a set of paths made the drive a coin flip), so the count and the date are
        one read of one listing and a complete record landing after the named drive moves the date with it (pass 10; pass 9
        dated by the newest log's header stamp, which a unit run logged like a drive made unreachable). It refuses to print
        anything when the two can disagree: a complete unmutated record the listing does not hold; a newest record in a
        directory with no headered lab log; that log with no end line (a drive in flight); a record of the DATING drive ending
        more than a second after that drive's end stamp (the log's whole seconds against the record's milliseconds; an older
        drive's records are not held to their own stamp); a record of the dating drive outside the listing; a HEADERED lab drive
        newer than the dating one that is in flight or ended with no class record (a log whose pytest target is another module,
        named in its header or read from its body's test ids, is no lab drive and is skipped with a note). Headered is the key
        throughout (the maintainer's round 6, extra8-3): a log's first line, written by the lab's run script, carries the start
        stamp newness is decided by, the pytest target that tells a lab drive from another module's run and, with its end line,
        completion; a log with no header is invisible to every reader of the tool, dated by nothing and refused by nothing, so a
        drive another script logged without the header is outside this derivation by construction. A counted record beside no
        headered lab log (a copy of an older record, a drive another script logged) is counted by the listing, dates nothing and
        is named to stderr, refused only when it is the newest: the count can hold records no drive dates while the date stays
        on the newest dated one. Then it runs this helper over each record's windows
        (`excuse_census.py`, the pass-7 head's module's copy for the frame-only key) and the floor over each window with the miss
        planted (`census_module.py`), prints the figure-bearing spans of this paragraph (three, two of them in one sentence),
        of _minus_attach_rows' docstring and of the waits and delivery comments WHOLE, and under --check reads this module for
        them, whitespace and comment markers folded, so a retyped figure is its exit 3, not a paste; a bare --check after a
        later drive has landed exits 3 too, since the newest record moved the date, and that is staleness, re-derived by
        `--as-of <log>` (a paste dated to an earlier drive stays derivable after later drives) and repaired by a re-paste as of
        the newest drive (the maintainer's round 6, correctness-4: the paste is re-derived at the final head). At the
        landing head the cache it read held that one drive alone and its listing read the same cache; where every counted
        record is the dating drive's, its sentences name that drive and not the cache as of it, it counts a phase wait that
        ran to its cap (seen.expired) apart from the deliveries, and on a population of more than one drive it refuses such
        a wait rather than print it as a delivery (the PR body names these changes, made outside the repo, and they cannot
        be re-checked from the tree). The post times
        are DERIVED from the change record (its t0 plus i x NOTICE_GAP_S, _change's own sleeps between the posts, on the
        poster's clock at millisecond resolution); each notice's answer in the record carries the remote kernel's own stamp
        for the notice too (`at`, `t`), but in whole seconds and on the other clock, too coarse for a millisecond gap check,
        so it is not read here. The
        frame key is after the bundle's last notice, not in the window: the left edge is the later of the window's mark and
        the earliest the last notice's post could have started, because a frame before that carries at most the earlier
        notices and cannot explain the later ones reaching the Outline as nothing (pass 5: a frame anywhere in the window's
        first two seconds excused a stripped phase). No pad on that edge, on purpose: the ready-time whole frame before A0
        must not excuse an empty phase A; the right pad is _rows_in's, for a retry's frame landing just past the settle. The
        phase's change record must exist (the window is a phase's), else this fails rather than widening."""
        m = self._marks()
        made = [c for c in self.changes_made if c.get("phase") == k0[0]]   # the phase's bundle, by the mark's letter (A0 -> A)
        self.assertEqual(len(made), 1, "the control door made phase %s's change bundle once (the allowance is keyed on its posts): %r"
                         % (k0[0], [c.get("phase") for c in self.changes_made]))
        posts_ms = [(made[0]["t0"] + i * NOTICE_GAP_S) * 1000 for i in range(NOTICES_PER_PHASE)]
        socks = [s for s in self._page("fleet")["socks"] if s["relay"]]
        if all(self._outline_served_at(socks, t) for t in posts_ms):
            return []   # every post found the Outline on an open, served socket: no gap, so no frame excuses the window
        t0, t1 = max(m[k0], posts_ms[-1]), m[k1] + slack_s * 1000
        return [f for s in socks for f in s["frames"] if f["t"] == "feed" and f.get("asks") is not None and t0 <= f["at"] <= t1]

    def _assert_one_row_per_outline_feed_patch(self, k0=None, k1=None, patches_due=True, attach_after=None):
        """The old bundle's storm as an invariant, not a count: in the window (padded on both sides as _rows_in pads,
        the whole drive without marks) the outline/delta-unapplied rows correspond one to one, by rev, with the feed
        slot patches the Outline's own relay sockets received there, and every such row names the feed slot. With
        patches_due the window must hold at least one patch OR the churn excuse (_outline_caught_up_whole: a notice post found
        the Outline without an open, served relay socket AND a whole keyed feed frame reached it there after the bundle's last
        notice could have been posted: a closed socket's retry absorbs the notices into one whole frame and files no row, so
        a count is one drive's, and a window with neither a patch nor that excuse is a change that reached the Outline as
        nothing, not the storm); without, both sides are empty. With attach_after (a mark) the return window's allowance
        reaches into this window's right pad: a card-less feed-family patch at or after that mark is the connect push's
        ledgers attach, by design and with no card in it, and it and the row the old bundle files for it (matched to the
        ATTACH, _minus_attach_rows: at most one row per attach, naming the feed slot, carrying the attach's rev and stamped at or
        after the attach's floored second with a second of slack; the maintainer's round 3: a rev is no identity, since the Outline's feed patch
        revs restart at 1 on every relay socket, and a set of revs let every row of a colliding rev through where this message
        promised one) are the return's, not this window's. Returns the row count, for the record."""
        stamped = self._outline_unapplied_stamped(self._rows_in(k0, k1) if k0 and k1 else None)
        rows = [d for d, _ in stamped]
        patches = self._outline_feed_patches(k0, k1)
        where = "[%s, %s)" % (k0, k1) if k0 and k1 else "the whole drive"
        self.assertTrue(all("rev" in f for f in patches), "every recorded feed patch carries its rev (the hook records m.rev on a delta frame): %r" % (patches,))
        self.assertTrue(all(isinstance(d, dict) and "rev" in d for d in rows), "every outline/delta-unapplied row carries the patch's rev: %r" % (rows,))
        if attach_after:
            since = self._marks()[attach_after]
            patches = [f for f in patches if not (f["at"] >= since and not self._carries_cards(f))]
            rows = self._minus_attach_rows(stamped, since)
        feed_rows = [d for d in rows if d.get("slot") == "feed"]
        self.assertEqual(len(feed_rows), len(rows), "every outline/delta-unapplied row in %s names the feed slot: %r" % (where, rows))
        self.assertEqual(sorted(int(d["rev"]) for d in feed_rows), sorted(int(f["rev"]) for f in patches),
                         "one outline/delta-unapplied row per feed slot patch the Outline received in %s, by rev (rows %r; patches %r)"
                         % (where, [(d.get("slot"), d.get("rev")) for d in rows], [(f.get("rev"), f["at"]) for f in patches]))
        if patches_due:
            wholes = self._outline_caught_up_whole(k0, k1) if k0 and k1 else []
            self.assertTrue(patches or wholes, "the Outline received a feed slot patch in %s (the storm has a patch to file a row for), or a notice post found "
                                               "it without an open, served relay socket and a whole keyed feed frame caught it up there after the bundle's last "
                                               "notice could have been posted (a relay socket closed inside the phase, as the splice's former idle cut closed them: the retry's whole frame absorbs the notices posted "
                                               "while the socket was down, so no patch and no row; a frame before the last notice explains nothing, and a frame "
                                               "while every post found an open, served socket explains nothing); neither happened" % where)
        else:
            self.assertEqual(patches, [], "no feed slot patch reached the Outline in %s: %r" % (where, patches))
        return len(rows)

    def _control(self):
        self._driver_ran()
        control = [r for r in self.hub_diag_rows if _corners.is_page_federation_row(r)]
        self.assertTrue(control, "the hub's client-diag carries the pages' federation rows about TESTHOST (the posting road is live); "
                                 "by (surface, what): %r" % (sorted({(r.get("surface"), r.get("what")) for r in self.hub_diag_rows}),))

    def _phase(self, name):
        self._driver_ran()
        rec = (self.result.get("phases") or {}).get(name)
        self.assertTrue(rec, "the driver ran phase %s (phases %r, timeouts %r)" % (name, sorted(self.result.get("phases") or {}), self.result.get("timeouts")))
        return rec

    def _rows_by_kind(self, rows):
        out = {}
        for r in rows:
            k = "%s/%s" % (r.get("surface"), r.get("what"))
            if _corners.is_page_federation_row(r):
                k += ":" + str((r.get("data") or {}).get("ev"))
            out[k] = out.get(k, 0) + 1
        return dict(sorted(out.items()))

    # ---- the shared assertions ----
    def _assert_dial_terms(self, url, app, caps, redial):
        qs = parse_qs(urlsplit(url).query)
        self.assertEqual(qs.get("app"), [app])
        self.assertEqual(qs.get("delta"), ["1"], "the page's delta term rides the %s relay dial: %r" % (app, url))
        self.assertEqual(qs.get("caps"), (["feedDelta"] if caps else None), "the %s relay dial's caps term: %r" % (app, url))
        if redial:
            self.assertEqual(qs.get("reconnect"), ["1"], "the %s page's redial states reconnect=1 (its earlier socket opened and the remote's caps frame acked its ready): %r" % (app, url))
            self.assertIn(qs.get("proto"), (["1"], ["2"]), "…and names the chat wire the page speaks: %r" % (url,))
        else:
            self.assertIsNone(qs.get("reconnect"), "a first dial states no reconnect: %r" % (url,))

    def _assert_link_dropped_and_the_row_went_down(self):
        """The drop: every held relay socket closes uncleanly, the hub's supervisor marks the row down, NO feed-family
        frame crosses the dropped link, the down-window dials are all redials (reconnect=1, not first dials), and the
        churn is BOUNDED. Dialing ceases once the browser's /tunnels poll reads the row down (a quiescent tail with no
        new relay dial before resume). This is the answer to "the storm is gated on the link's state": no link, no
        frames, no rows."""
        m = self._marks()
        drop = self._phase("drop")
        for app in self.apps:
            held = drop["held"].get(app) or []
            self.assertEqual(len(held), 1, "the %s page held ONE open relay socket at the drop (the driver waits for that before it drops, waitsMs.held, so this "
                                           "reads a designed precondition and not the drop's timing against the old-hub drives' relay churn, the splice's former idle cut): %r" % (app, held))
            s = self._page(app)["socks"][held[0]]
            self.assertIsNotNone(s["closeAt"], "the %s page's relay socket closed after the drop (the hub's splice lost its upstream): %r" % (app, {k: s[k] for k in ("url", "openAt", "closeAt", "code")}))
            self.assertGreaterEqual(s["closeAt"], m["drop"], "…after the drop, not before")
            self.assertFalse(s["clean"], "…and uncleanly (no close frame crossed: a FIN): code %r" % (s["code"],))
        self.assertIn(drop.get("rowStatus"), ("down", "no-kernel"), "the hub's supervisor read the peer's port closed and the row went down (it read %r)" % (drop.get("rowStatus"),))
        for app in self.apps:
            # nothing crossed the dropped link: no relay socket dialed in [drop, resume) received a feed-family frame
            down_socks = self._relay_socks(app, "drop", "resume")
            crossed = [(s["i"], self._kinds(s)) for s in down_socks if self._first_feed_family(s) is not None]
            self.assertEqual(crossed, [], "no feed-family frame crossed the dropped link on the %s page (a frame here is a stray splice past the drop, or the link never went down): %r" % (app, crossed))
            # every down-window dial is a REDIAL (reconnect=1): the conn opened before the drop, so its retry states the term
            for s in down_socks:
                self._assert_dial_terms(s["url"], app, caps=self.caps, redial=True)
            # bounded: no new relay dial in the quiet tail before resume (the poll read the row down; connect() gates on live)
            tail = [s for s in down_socks if s["dialedAt"] >= m["resume"] - self.quiet_tail_ms]
            self.assertEqual(tail, [], "the %s page kept dialing into the quiet tail before resume (dialing did not cease when the row went down): %r"
                             % (app, [self._kinds(s) or s["url"] for s in tail]))

    def _assert_redialed_once_and_served_whole(self, k0, k1, caps):
        """ONE relay socket per page dialed in [k0, k1), a redial by its terms, that opened and received a WHOLE keyed feed
        as its first feed-family frame (the remote's client dict is per socket: it holds nothing to patch). One on either
        bundle: the extra sockets the old-hub drives once showed here were the splice's 5 s idle cut (LinkProxy), not the
        old bundle."""
        for app in self.apps:
            fresh = self._relay_socks(app, k0, k1)
            opened = [s for s in fresh if s["openAt"]]
            self.assertTrue(opened, "the %s page dialed a relay socket that opened between %s and %s: %r" % (app, k0, k1, [(s["url"], s["openAt"], s["closeAt"], s["code"]) for s in fresh]))
            self.assertEqual(len(fresh), 1, "the %s page dialed ONE relay socket between %s and %s: %r" % (app, k0, k1, [(s["url"], s["openAt"], s["closeAt"], s["code"]) for s in fresh]))
            s = opened[0]
            self._assert_dial_terms(s["url"], app, caps=caps, redial=True)
            f = self._first_feed_family(s)
            self.assertIsNotNone(f, "the new %s relay socket received a feed-family frame: %r" % (app, self._kinds(s)))
            self.assertEqual(f["t"], "feed", "the new %s relay socket's first feed-family frame is the remote's WHOLE feed, never a patch or a feedDelta onto a base this socket never held: %r" % (app, self._kinds(s)))
            self.assertIsNotNone(f.get("asks"), "…keyed (an asks list rides it): %r" % (f,))

    def _assert_every_opened_relay_socket_was_served_whole_first(self):
        """Every relay socket that OPENED at any point in the drive, the two lab-caused redials and any spontaneous churn
        alike, received a whole keyed feed as its first feed-family frame (the remote's client dict is per socket: it
        holds nothing to patch, so a patch first would be a patch onto a base the socket never held). A socket that
        opened and had received no feed-family frame when the record ended (a churned socket closing at once, the last
        socket at the drive's end) is counted, not judged. Derived: every page opened at least one socket that received
        a frame (the maintainer's round 1, fresh-2)."""
        for app in self.apps:
            opened = [s for s in self._relay_socks(app) if s["openAt"]]
            with_frame = [(s, self._first_feed_family(s)) for s in opened if self._first_feed_family(s) is not None]
            self.assertTrue(with_frame, "the %s page opened a relay socket that received a feed-family frame: %r" % (app, [(s["i"], s["openAt"], self._kinds(s)) for s in opened]))
            bad = [(s["i"], f["t"], f["slot"], self._kinds(s)) for s, f in with_frame if not (f["t"] == "feed" and f.get("asks") is not None)]
            self.assertEqual(bad, [], "every relay socket the %s page opened was served a WHOLE keyed feed first (%d opened, %d received a frame; a patch "
                                      "or feedDelta first is a patch onto a base the socket never held): %r" % (app, len(opened), len(with_frame), bad))

    def _assert_every_wait_was_met(self, frozen=()):
        """Every wait the driver placed (waitFor: the held sockets closing, the row leaving and returning to up, a fresh
        relay socket per page holding a whole frame, the local sockets reopening; and every visibility wait, waitVisible:
        a phase's card, todo and provisional row, and phase D's after the return) was met inside its timeout. An
        expired wait means a phase ran on an unmet precondition and the record shows a partial drive that every other
        assertion may still pass (the maintainer's round 1, fresh-3: a forced timeout gave 3 / 0 / 3 / 2 and five green tests). The
        visibility waits' expiries were swallowed until pass 6, so a phase whose cards never came left only a waitedMs
        at about the cap, which the gate legs read as a delivery; the driver now names each in out.timeouts with its
        phase and in the phase's seen.expired. The driver records quiet()'s give-ups separately and they are not fatal.
        `frozen` names the phases whose card wait must instead have run to its cap, once each and with budget left (the
        old page's freeze, LinkDropOldLocal): every other wait was met, and a card wait of those phases that resolved reds
        here as the change showing."""
        self._driver_ran()
        timeouts = self.result.get("timeouts")
        self.assertIsInstance(timeouts, list, "the driver recorded the waits that expired (out.timeouts): %r" % (timeouts,))
        heads = ["phase %s: the card wait expired: " % p for p in frozen]   # waitVisible's entry; with the budget spent it reads otherwise
        self.assertEqual([len([t for t in timeouts if t.startswith(h)]) for h in heads], [1] * len(heads),
                         "the card wait of each of phases %r ran to its cap once, with budget left (the old page shows no change on a socket "
                         "it holds, so a card wait that resolved is the change showing); the expired waits: %r" % (list(frozen), timeouts))
        self.assertEqual([t for t in timeouts if not any(t.startswith(h) for h in heads)], [], "every %swait the driver placed was met; the expired ones: %r (quiet gave up: %r)"
                         % ("other " if frozen else "", timeouts, self.result.get("quietGaveUp")))

    def _assert_seen(self, seen, want_cards, todo=None, prompt=None, what="", waited=False, expired=()):
        """The visibles a read found. With `waited` the record is one waitVisible produced (a phase's seen, D's seenAfterReturn)
        and its expired list must be present and empty: the driver names there each visibility wait that ran to its cap (pass
        6), and a missing list is refused rather than read as empty, since an older driver's record cannot establish the
        outcome. Scoped to the waited reads (the maintainer's round 3, tests-1: phase D's after-return read was the one waitVisible record no
        reader checked, so a wait that expired with the read catching the cards and nothing in out.timeouts passed every test);
        a visible() record (seenWhileDown, seenA, seenB, seenD) records no wait and carries no such list. `expired` names the
        waits a waited read must have run to their cap, and no others: the old page's freeze, whose card wait runs out with no
        card shown (LinkDropOldLocal), so a wait that resolved there reds as the change showing."""
        if waited and expired:
            self.assertEqual(seen.get("expired"), list(expired), "%s: the visibility waits behind this read that ran to their cap are the %s wait and no other (a "
                                                                 "wait that resolved is the change showing; a record with no expired list cannot say which it was): %r"
                                                                 % (what, " and ".join(expired), seen))
        elif waited:
            self.assertEqual(seen.get("expired"), [], "%s: the visibility waits behind this read all resolved before their cap (the driver records each wait that "
                                                      "expired in seen.expired; a record with no expired list cannot say which it was): %r" % (what, seen))
        self.assertEqual(seen.get("cards"), [want_cards] * len(seen.get("cards") or []), "%s: the notice cards on the hub's feed page (per card, in posting order): %r" % (what, seen))
        self.assertTrue(seen.get("cards"), "%s: cards were posted" % what)
        if todo is not None:
            self.assertEqual(bool(seen.get("todo")), todo, "%s: the todo's text on the hub's Waiting page: %r" % (what, seen))
        if prompt is not None:
            self.assertEqual(seen.get("prov"), prompt, "%s: api's provisional row on the hub's Outline reads the phase's prompt: %r" % (what, seen))

    def _assert_nothing_stranded(self):
        self._control()
        self.assertEqual(self._bad_rows(), [], "no frame reached a pane raw and no delta found a missing or unkeyed base, over the whole drive; rows by kind: %r" % (self._rows_by_kind(self.hub_diag_rows),))
        for app in self.apps:
            self.assertEqual(self._sends(app, "local", "needSlot"), [], "the %s page asked the LOCAL kernel for no slot" % app)
            self.assertEqual(self._sends(app, "relay", "needSlot"), [], "…and the remote for no slot")
            self.assertEqual(self._sends(app, "relay", "needFullFeed") + self._sends(app, "local", "needFullFeed"), [], "…and nobody for a full feed: every feedDelta found its base on the socket it arrived on")

    def _carries_cards(self, f):
        """Whether a recorded relay frame carries a card upsert: a feedDelta with an `asks` list (the hook records its
        length, None when the frame had none) or a feed slot patch whose `coll` names asks. A feed-family patch with
        neither is the connect push's LEDGERS ATTACH, by design and with no card in it: the `ready`-time whole frame is
        the cached, ledger-less one and the push that follows sends the ledgers as a delta (kernel.py _send_feed_now), a
        feedDelta on a page that announced the cap, a feed slot patch on one that did not. The head drive's record holds
        one, a second after the Waiting page's restart whole frame (the author's pass 3, finding 1)."""
        if f["t"] == "feedDelta":
            return f.get("asks") is not None
        if f["t"] == "delta" and f["slot"] == "feed":
            return "asks" in (f.get("coll") or [])
        return False

    def _attaches_since(self, since_ms):
        """One (rev, floored second) per card-less feed slot patch (the connect push's ledgers attach, _carries_cards) the Outline
        received from `since_ms` to phase B's first change, in order, read over the drive's record and not a window's: the
        kernel floors a row's stamp to the second, so the row the old bundle files for an attach can sit inside a window whose
        patch pad the attach itself is past by tens of milliseconds (the maintainer's round 2, regression-3: a 40 ms gap on a recorded drive).
        Every reader of an attach matches rows to it through _minus_attach_rows (the two down-window sites since pass 8, the
        return window since pass 8's fixer pass, when its own set of revs went); no reader keeps a set of revs."""
        m = self._marks()
        return sorted((int(f["rev"]), int(f["at"] // 1000)) for f in self._outline_feed_patches() if since_ms <= f["at"] < m["B0"] and not self._carries_cards(f))

    def _outline_unapplied_stamped(self, rows=None):
        """(data, stamp) per outline/delta-unapplied row: _outline_unapplied with the kernel's whole-second stamp kept beside it."""
        rows = self.hub_diag_rows if rows is None else rows
        return [(r.get("data"), float(r.get("t") or 0)) for r in rows if (r.get("surface"), r.get("what")) == ("outline", "delta-unapplied")]

    def _minus_attach_rows(self, stamped, since_ms, slack_s=1.0):
        """The rows left once every ledgers attach since `since_ms` has taken AT MOST ONE row as its own: a row naming the feed
        slot, carrying the attach's rev and stamped at or after the attach's floored second less slack_s (the kernel stamps a
        row at receipt in whole seconds, and its clock and the browser hook's can differ by up to a second on a recorded
        drive), and with NO upper bound on the row's stamp: a row of the attach's rev stamped any time later inside the
        reader's window is the attach's (the kernel stamps a row at the flush, and a row queued while the page's local socket
        was down lands late, _rows_in's flush-lag residual), so the match is closed a second below the floored second and
        open above it, to the window's end; the pin's return-late cell states the choice. A multiset difference matched to
        the ATTACH, not a set of revs (pass 8): the Outline's feed patch revs
        restart at 1 on every relay socket, so a rev is no identity over a drive, and a set of revs let every row of a
        colliding rev through where the assertions' messages promise one row per attach. The exemption fires nowhere in the
        one drive counted, made at the landing head (the coordinator's ruling G on the maintainer's round 7: its records
        alone): over the 2 unmutated records of both classes of the drive at `landing/lab-final.log` (2026-09-29), the only
        drive counted, the down windows hold 0 rows and 0 attaches and the return window holds 0 rows, so 0 rows are
        exempted at the storm site, 0 at the gate leg's read and 0 in the return window, by this match; the pin over a
        synthetic record in tests/test_federated_linkdrop_driver_bound.py is where the match is
        exercised. The count and its drive are one derivation, `population_drive.py --check` in the builder's cache outside
        the repo, whose population, dating rule and refusals are stated once in _outline_caught_up_whole's docstring (the maintainer's round 5, extra7-4:
        this docstring restated three of them and omitted the one that fired); over each record it runs these helpers
        (`attach_census.py`), prints the sentence before this one whole and reads this docstring for it under --check (the maintainer's round 4:
        the pair was retyped one drive behind, twice; pass 9's fixer pass found the tool printed fragments and the figures were
        transcribed). Both tools and the records are outside the repo, the tools named in the PR body, so the count cannot be
        re-checked from the tree. Returns the rows' data, _outline_unapplied's shape."""
        pool = list(self._attaches_since(since_ms))
        out = []
        for d, t in stamped:
            rev = d.get("rev") if isinstance(d, dict) else None
            hit = next((a for a in pool if rev is not None and int(rev) == a[0] and t >= a[1] - slack_s and d.get("slot") == "feed"), None)
            if hit is not None:
                pool.remove(hit)
            else:
                out.append(d)
        return out

    def _rows_down_minus_attaches(self):
        """The gate leg's down-window read: the outline/delta-unapplied rows stamped in [drop, resume] (padded as _rows_in pads)
        less one row per ledgers attach the Outline received from 1.5 s BEFORE the resume (the attach can sit in the window's
        right pad by the kernel's whole-second floor, and its own stamp before the mark's second); the storm test's site reads
        attaches from the mark itself. The read is a helper so the since it passes is the one the pin in
        tests/test_federated_linkdrop_driver_bound.py reads (pass 8's fixer pass: the leg's inline since was reached by no test,
        and a mutation moving it to the resume stayed green while the helpers were pinned at both values)."""
        return self._minus_attach_rows(self._outline_unapplied_stamped(self._rows_in("drop", "resume")), self._marks()["resume"] - 1500)

    def _return_window_stray(self):
        """The rows filed between the link's return and phase B's first change beyond one per ledgers attach the Outline received
        there: the outline/delta-unapplied rows stamped in [resume - 1.5 s, B0 - 1 s] (padded on the left as _rows_in pads, the
        kernel's whole-second floor; closed a second before B0, since phase B's first row is stamped at a floor no earlier than
        B0 - 1 s, B0 being marked before the change is posted) less one row per attach from 1.5 s before the resume, matched to
        the attach as the down window's are (_minus_attach_rows). Pass 8's fixer pass: this reader kept a set of revs after the
        two down-window sites moved to the match, so two rows of one attach's rev both passed a filter whose message promised one
        per attach; the switch moves no recorded verdict, since the recorded population holds no row and no attach in this
        window (the census, its population and its drive are in _minus_attach_rows's docstring, one derivation, and are not
        repeated here). Returns (the stray rows' data, the attaches)."""
        m = self._marks()
        t0, t1 = m["resume"] / 1000.0 - 1.5, m["B0"] / 1000.0 - 1.0
        stamped = self._outline_unapplied_stamped([r for r in self.hub_diag_rows if t0 <= float(r.get("t") or 0) <= t1])
        return self._minus_attach_rows(stamped, m["resume"] - 1500), self._attaches_since(m["resume"] - 1500)

    def _link_up_phases(self):
        return ("A", "B", "C") if self.local_drop else ("A", "B")

    def _link_up_delivery_ms(self, p):
        """Phase p's delivery with the link up, the margin leg's yardstick, on this checkout's bundle: the driver's seen.waitedMs,
        from the change's post returning to the last of its visibles on the pages (waited for concurrently). A phase's waitedMs
        is a delivery only when every wait behind it RESOLVED: a wait that ran to its cap leaves waitedMs at about wait_ms with
        the visible absent, and taking that as the yardstick makes the margin pin `dwell >= DOWN_WINDOW_MARGIN x cap`, true by
        the relation pin's arithmetic and saying nothing about the drive (pass 6: the driver swallowed those timeouts and the
        leg passed at 42 >= 40). So the phase must record an empty seen.expired (the driver's per-wait outcomes; a record with
        none cannot establish them and is refused) and show its visibles on every page before its waitedMs is taken; a
        resolved wait ended before its cap, so a delivery at the cap is then impossible by construction and DOWN_READ_ROOM_MS
        covers the reads alone. LinkDropOldLocal measures its own (the old page shows nothing on a socket it holds)."""
        rec = self._phase(p)
        seen = rec.get("seen") or {}
        self.assertEqual(seen.get("expired"), [], "phase %s's visibility waits all resolved before their cap (the driver records each wait that expired in "
                                                  "seen.expired; a wait that ran to its cap is not a delivery, and a record with no expired list cannot say which "
                                                  "it was), so its waitedMs is a delivery the down window can be measured against: %r" % (p, seen))
        self._assert_seen(seen, True, todo=("todo" in self.changes) or None, prompt=((rec.get("change") or {}).get("prompt") if "append" in self.changes else None),
                          what="phase %s's changes on every page (the delivery the down window is measured against)" % p, waited=True)
        return seen.get("waitedMs")

    def _assert_the_down_window_outlasts_the_drives_slowest_delivery(self):
        """The gate's control in TIME (the maintainer's round 2's ruling): the while-down read of phase D came at least DOWN_WINDOW_MARGIN times
        this drive's own slowest link-up delivery after D's post ended. A phase's delivery is the class's _link_up_delivery_ms
        (the visibles' seen.waitedMs on this checkout's bundle; the Outline's feed patch on the old one, whose page shows no
        change without a redial), taken over EVERY link-up phase (A, B and C with the local drop; which is slowest moves from
        drive to drive, so no one phase stands for the rest), so the yardstick is this drive's and this bundle's. Without
        this pin the two temporal pins hold for a post at the END of the dwell (an 18 ms window, both of the maintainer's round-2 voters), and
        "absent while down" cannot be told from "no time passed". The span is read to `settled`, the mark the while-down read
        follows (resume is some 20 ms later). Returns (span_s, deliveries) for the record."""
        m = self._marks()
        made = [c for c in self.changes_made if c.get("phase") == "D"]
        self.assertEqual(len(made), 1, "the control door made phase D's change bundle once: %r" % ([c.get("phase") for c in self.changes_made],))
        deliveries = {p: self._link_up_delivery_ms(p) for p in self._link_up_phases()}
        self.assertTrue(deliveries and all(isinstance(v, int) and not isinstance(v, bool) and v >= 0 for v in deliveries.values()),
                        "every link-up phase recorded its delivery: %r" % (deliveries,))
        slowest = max(deliveries, key=deliveries.get)
        slowest_s = deliveries[slowest] / 1000.0
        span_s = m["settled"] / 1000.0 - made[0]["t1"]
        self.assertGreaterEqual(span_s, DOWN_WINDOW_MARGIN * slowest_s,
                                "the down window's observation span (phase D's post end to the while-down read at settled: %.3f s; resume %d ms "
                                "later) holds %g times this drive's slowest link-up delivery (%.3f s in phase %s; per phase %r): a change that "
                                "took that long with the link up had %g times that long to arrive while it was down, so its absence is the "
                                "link's and not the window's; widen down_dwell_ms, never the margin"
                                % (span_s, m["resume"] - m["settled"], DOWN_WINDOW_MARGIN, slowest_s, slowest, deliveries, DOWN_WINDOW_MARGIN))
        return span_s, deliveries

    def _assert_change_due_while_down_crossed_nothing_and_the_return_carried_it_whole(self):
        """The gate, established rather than exhibited (the maintainer's round 1): phase D's change bundle was posted to the remote's real
        port after the hub's row went down and before the dwell ended, so a patch was DUE with the link down, and the dwell
        after the post outlasted this drive's slowest link-up delivery by DOWN_WINDOW_MARGIN (the control in time). While down
        the change is absent from every page (the card, and on the new bundle the todo and the provisional row), no
        outline/delta-unapplied row files, and the link's return serves each page ONE whole frame that carries it: the
        change is visible after the return, no patch carrying a card reaches any page between the return and phase B's
        first change (the ledgers attach that can follow the whole frame carries none, _carries_cards), no row files in
        that window beyond the one the old bundle files for such an attach, and the change stays visible after phase B
        and at the end. The whole frame's precedence on its socket is the redial pins' (every opened socket's first
        feed-family frame is a whole feed)."""
        m = self._marks()
        D = self._phase("D")
        made = [c for c in self.changes_made if c.get("phase") == "D"]
        self.assertEqual(len(made), 1, "the control door made phase D's change bundle once: %r" % ([c.get("phase") for c in self.changes_made],))
        ch = made[0]
        self.assertEqual(len(ch.get("noticeKeys") or []), NOTICES_PER_PHASE, "phase D posted its notice cards: %r" % (ch,))
        self.assertGreaterEqual(ch["t0"], m["rowDown"] / 1000.0, "phase D was posted after the hub's row went down (t0 %r, rowDown %r)" % (ch["t0"], m["rowDown"] / 1000.0))
        self.assertLessEqual(ch["t1"], m["settled"] / 1000.0, "…and finished inside the down dwell (t1 %r, settled %r)" % (ch["t1"], m["settled"] / 1000.0))
        self._assert_the_down_window_outlasts_the_drives_slowest_delivery()   # …and the dwell after it outlasted this drive's slowest delivery
        todo = ("todo" in self.changes) or None
        prompt = ch.get("prompt") if "append" in self.changes else None
        self._assert_seen(D["seenWhileDown"], False, todo=(False if todo else None), what="phase D while the link was down (a change due, nothing to carry it)")
        if prompt is not None:
            self.assertNotEqual(D["seenWhileDown"].get("prov"), prompt, "api's provisional row did not read phase D's prompt while the link was down: %r" % (D["seenWhileDown"],))
        down = self._rows_down_minus_attaches()   # one row per ledgers attach from 1.5 s before the resume, matched to it
        self.assertEqual(down, [], "no outline/delta-unapplied row filed while the link was down with phase D due (the one row the old bundle files for a "
                                   "ledgers attach the Outline received from 1.5 s BEFORE the resume, the reader's since, since the kernel's whole-second floor can "
                                   "put the attach's row a second before the mark, is the return's, in this window's right pad: it names the feed slot, carries the "
                                   "attach's rev and is stamped no more than one second, slack_s, below the attach's floored second, with no upper bound on its "
                                   "stamp inside the window): %r" % (down,))
        self._assert_seen(D["seenAfterReturn"], True, todo=todo, prompt=prompt, what="phase D after the link's return (the redial's whole frame carried it)", waited=True)
        for app in self.apps:
            window = [(s, f) for s in self._relay_socks(app) for f in s["frames"] if m["resume"] <= f["at"] < m["B0"]]
            carrying = [(s["i"], f["t"], f["slot"], f.get("asks") if f["t"] == "feedDelta" else f.get("coll"), round((f["at"] - m["resume"]) / 1000.0, 2))
                        for s, f in window if self._carries_cards(f)]
            self.assertEqual(carrying, [], "no patch carrying a card reached the %s page between the link's return and phase B's first change (the "
                                           "catch-up is one whole frame, never a replayed patch; a ledgers attach after the whole frame carries no card): %r" % (app, carrying))
            wholes = [f for s, f in window if f["t"] == "feed"]
            self.assertTrue(wholes, "…and a whole feed frame did reach the %s page in that window: %r" % (app, [self._kinds(s) for s in self._relay_socks(app, "resume", "B0")]))
        # the rows, read over the return window itself (the author's pass 3, finding 2; the down window's zero above ends 1.5 s
        # after resume and reaches none of the return's whole frames, which arrive 1 to 5 s after it): no outline/
        # delta-unapplied row for the return's whole frame or for a replayed patch (_return_window_stray: the window's bounds,
        # and the one row allowed per ledgers attach the Outline received from 1.5 s before the resume, matched to the attach as
        # the down window's are: the feed slot, the attach's rev, a stamp no more than one second below its floored second and
        # any later inside the window)
        stray, attaches = self._return_window_stray()
        self.assertEqual(stray, [], "no outline/delta-unapplied row filed between the link's return and phase B's first change beyond one per ledgers attach the "
                                    "Outline received from 1.5 s before the resume, the reader's since (a row here is a row for the return's whole frame or for a "
                                    "replayed patch; the attach's row names the feed slot, carries its rev and is stamped no more than one second, slack_s, below "
                                    "its floored second, any later inside the window): stray %r, attaches (rev, floored second) %r" % (stray, attaches))
        self._assert_seen(self._phase("B")["seenD"], True, todo=todo, what="phase D's changes after phase B")
        if self.local_drop:
            self._assert_seen(self._phase("C")["seenD"], True, todo=todo, what="phase D's changes at the end")


class LinkDropBothNew(_LinkDrop):
    """Both new (this checkout on both sides): the remote honours the cap and serves feedDelta frames; the hub's pages
    hold their bases per conn. The link drops and returns (a redial with reconnect=1, served whole, then feedDeltas onto
    that whole frame), then the hub restarts (the relay dial deferred under the local-down word, one dial at the local
    return, served whole again). Every phase's changes show on every page at the end; no row, no ask."""
    caps = True

    def test_the_link_dropped_and_the_pages_stopped_dialing_while_the_row_was_down(self):
        self._assert_link_dropped_and_the_row_went_down()

    def test_the_first_dials_were_first_dials(self):
        for app in self.apps:
            first = self._relay_socks(app)[0]
            self._assert_dial_terms(first["url"], app, caps=True, redial=False)
            self.assertIsNotNone(first["openAt"])
        firsts = [r for r in self.remote_wsopen if not r["reconnect"]]
        self.assertEqual(sorted(r["app"] for r in firsts), sorted(self.apps), "the remote's wsopen rows name one first relay dial per page: %r" % (self.remote_wsopen,))

    def test_the_links_return_redialed_once_with_reconnect_and_was_served_whole(self):
        self._assert_redialed_once_and_served_whole("resume", "restart" if self.local_drop else "end", caps=True)
        # the remote read the same term: one relay accept per page with reconnect true inside the window
        m = self._marks()
        redials = [r for r in self.remote_wsopen if r["reconnect"] and m["resume"] / 1000.0 - 1 <= float(r["t"] or 0) <= m["B1"] / 1000.0 + 1]
        self.assertEqual(sorted(r["app"] for r in redials), sorted(self.apps), "the remote accepted ONE reconnect=1 relay dial per page after the link's return: %r" % (self.remote_wsopen,))

    def test_the_change_after_the_redial_crossed_as_feed_deltas_onto_the_new_sockets_base(self):
        m = self._marks()
        for app in self.apps:
            s = self._relay_socks(app, "resume", "restart" if self.local_drop else "end")[0]
            after = self._kinds(s, m["B0"])
            self.assertIn(("feedDelta", ""), after, "the change crossed the new %s relay socket as a feedDelta (applied onto the whole frame that socket received first): %r" % (app, self._kinds(s)))
            self.assertEqual([k for k in self._kinds(s) if k[0] == "delta"], [], "no slot patch on the new %s relay socket: %r" % (app, self._kinds(s)))

    def test_every_phases_changes_show_on_every_page(self):
        A, B = self._phase("A"), self._phase("B")
        self.assertEqual(self.result.get("provBefore"), _corners.SEED_LAST_PROMPT, "the Outline drew api's provisional row with the seed's last prompt before any change")
        self._assert_seen(A["seen"], True, todo=True, prompt=A["change"]["prompt"], what="phase A (before the drop)", waited=True)
        self._assert_seen(B["seen"], True, todo=True, prompt=B["change"]["prompt"], what="phase B (on the redialed socket)", waited=True)
        self._assert_seen(B["seenA"], True, todo=True, what="phase A's changes after the redial (the whole frame carried them)")
        if self.local_drop:
            C = self._phase("C")
            self._assert_seen(C["seen"], True, todo=True, prompt=C["change"]["prompt"], what="phase C (after the local return)", waited=True)
            self._assert_seen(C["seenA"], True, todo=True, what="phase A's changes at the end")
            self._assert_seen(C["seenB"], True, todo=True, what="phase B's changes at the end")

    def test_nothing_stranded_no_row_no_ask(self):
        self._assert_nothing_stranded()
        self.assertEqual(self.remote_wire.get("feed_slot_split"), 0, "the remote never re-encoded through the slot path: %r" % (self.remote_wire,))

    def test_every_relay_socket_that_opened_was_served_whole_first(self):
        self._assert_every_opened_relay_socket_was_served_whole_first()

    def test_every_wait_the_driver_placed_was_met(self):
        self._assert_every_wait_was_met()

    def test_a_change_due_while_the_link_was_down_crossed_nothing_and_the_return_carried_it_whole(self):
        """Phase D (cards, a todo, an appended pair) posted with the row down: absent from every page while down, no row,
        then the return's whole frame carries all of it (card, todo text, the provisional row's prompt) with no patch
        carrying a card before phase B's first change (a ledgers attach after the whole frame is allowed, and carries
        none)."""
        self._assert_change_due_while_down_crossed_nothing_and_the_return_carried_it_whole()

    def test_the_local_drop_deferred_the_relay_dial_once_and_the_return_dialed_once(self):
        if not self.local_drop:
            self.skipTest("optional: this class runs no local drop")
        m = self._marks()
        window = self._rows_in("restart", "C1")
        deferred = self._hostconn("dial-deferred", window)
        self.assertEqual(sorted(str((r.get("data") or {}).get("why")) for r in deferred), ["local-down"] * len(self.apps),
                         "one dial-deferred row per page for TESTHOST while the hub was down (the relay's onclose retry ran under the shim's local-down word); hostconn rows in the window: %r"
                         % ([(r.get("wid"), (r.get("data") or {}).get("ev"), (r.get("data") or {}).get("why")) for r in window if _corners.is_page_federation_row(r)],))
        self.assertEqual(len(self._hostconn("dial-deferred")), len(self.apps), "…and no other dial was ever deferred (the link drop happened with the local socket up)")
        self._assert_redialed_once_and_served_whole("restart", "end", caps=True)
        for app in self.apps:
            s = self._relay_socks(app, "restart", "end")[0]
            self.assertIs(s["localUpAtDial"], True, "the %s page's relay dial after the restart ran with the local socket UP (romp:wsup dialed it): %r" % (app, s["localUpAtDial"]))
            local = [k for k in self._page(app)["socks"] if not k["relay"] and k["dialedAt"] >= m["restart"] and k["openAt"]]
            self.assertTrue(local, "the %s page's local socket reopened after the restart" % app)
            self.assertLessEqual(local[0]["openAt"], s["dialedAt"], "…before the relay dial")
        self.assertEqual([len([r for r in self.remote_wsopen if r["reconnect"] and float(r["t"] or 0) >= m["restart"] / 1000.0 - 1 and r["app"] == app]) for app in self.apps], [1] * len(self.apps),
                         "the remote accepted one reconnect=1 relay dial per page after the local return: %r" % (self.remote_wsopen,))


class LinkDropOldLocal(_LinkDrop):
    """OLD local (a hub kernel and prebuilt bundle from before PR 815: a built checkout named by ROMP_CORNER_OLD_HUB_ROOT,
    or the private clone this class mints at OLD_HUB_SHA under ROMP_LINKDROP_OLD_HUB_BUILD=1), a new remote (this
    checkout): the storm's own witness, the pre-815 half. The mint borrows this clone's objects through an alternates
    file, which is safe while OLD_HUB_SHA is reachable there: it is an ancestor of the fork's main (the merge of PR 818),
    so a `git gc` of the shared clone keeps every object the checkout needs. The old bundle dials no caps (verified from
    the dial URL, not a grep of the minified dist) and has no per-conn view-delta receiver, so the remote serves the feed as
    {type:delta, slot:feed} patches and the old Outline DROPS each one, filing a delta-unapplied row and posting a
    needSlot to the LOCAL kernel (the corners lab's CornerOldLocal freeze, pinned against this same checkout). The
    change bundle is completed notice cards ALONE (no todo, no needs-you): a todo moves the frame's remainder and the
    size guard would send a whole frame, catching the old page up and hiding the freeze (the corners lab's docstring).

    The freeze, across the link's events: on a relay socket the page holds, the old feed page shows no change. Each
    link-up phase's cards (A before the drop, B on the socket the link's return dialed, C on the socket the restart's
    redial dialed) do not show within wait_ms: the card wait runs to its cap with no card on the page, and no relay socket
    closes or is dialed inside the phase. Only a redial's whole frame catches the page up: phase A's cards show after the
    return's redial, phase B's after the restart's, phase D's after the return. A card that shows on a held socket reds
    the class. Until the splice's upstream timeout was cleared (LinkProxy) the lab cut every quiet pair after 5 s, each
    cut a redial whose whole frame caught the old page up 6 to 19 s after a change, and this class asserted those
    deliveries; they were the lab's cut, not the bundle's behaviour, and the extra relay sockets its records show are
    that cut too.

    The delta-unapplied rows are the old bundle's storm. This lab reads it across the mid-session events: it is one
    row PER remote feed patch, it STOPS while the link is down (no patch arrives, so no row: the storm is gated on the
    link, established by phase D, a change due while the link was down that crossed as no frame and filed no row until
    the return's whole frame carried it, the while-down read coming DOWN_WINDOW_MARGIN times this drive's slowest link-up
    patch delivery after the post; on this page a card's absence while down is also the freeze's, so here the gate is
    read on the frames and the rows), and it RESUMES after each redial's whole frame (the whole frame catches the page
    up once; the next patch freezes it again). The class pins the correspondence, not a count: per window and over the
    whole drive, the rows equal the Outline's own feed slot patches by rev, non-empty in every phase unless a notice post
    found the Outline without an open, served relay socket and a whole keyed feed frame then caught it up inside the phase
    after the bundle's last notice could have been posted (the allowance _outline_caught_up_whole keys on that gap and
    that frame; the splice's idle cut made such gaps, and with it gone a socket closing inside a phase reds the freeze
    test; the margin yardstick, _link_up_delivery_ms, fails any phase the allowance would excuse, so only the phase-A
    drops test can still pass on it) and empty while the link was down. One drive's count on the bundle at 01d4fbe43 (2026-09-19, the pass-2
    head): 3 / 0 / 3 / 3 across phase A, the link down, phase B and phase C; a reviewer's drive at the head the maintainer's round 1 ruled gave
    3 / 0 / 1 / 3 when the splice's idle cut inside phase B absorbed two notices into whole frames (the module docstring
    gives the recorded population). A relay redial does not end the storm but restarts it, so with a link that comes and
    goes the storm looks intermittent and self-healing when it is neither; this class keeps that evidence beside the new
    bundle's zero. The freeze with no link event at all is the corners lab's; the storm (the rows) and the freeze across
    the link's events are this lab's observables, and the new bundle (LinkDropBothNew) files ZERO rows and shows every
    phase's change across the same drive."""
    changes = ("notice",)
    caps = False               # the old bundle dials no caps (read from the dial URL)

    # What a skip of this class leaves unexecuted, and what still runs in CI (in this class's job, served-pages, or in
    # the vscode-extension job): the skip reasons carry it, so a runner reading "skipped" knows which claim went untested
    # (the maintainer's round 1, tests-4).
    UNEXECUTED = ("the old bundle's freeze across the link's events (no change shown on a socket the page holds until a redial's "
                  "whole frame) and its storm evidence (one delta-unapplied row per feed slot patch the Outline received, none "
                  "with a change due while the link was down, restarted by each redial's whole frame) go unexecuted; the "
                  "mechanisms PR 815 fixed are pinned by ui/webview/federation-remote-view-delta.test.ts, "
                  "federation-remote-feed-delta.test.ts and federation-reconnect.test.ts (npm test, which CI runs in the "
                  "vscode-extension job), and LinkDropBothNew, which CI runs in this class's job (served-pages), drives the "
                  "link drop and the hub restart against this checkout")

    @classmethod
    def _knobs(cls):
        super()._knobs()
        if (os.environ.get("ROMP_LINKDROP_LAB") or "").strip() != "1":
            raise unittest.SkipTest("optional: ROMP_LINKDROP_LAB unset: the old-hub class waits out the hub's supervisor twice and restarts its "
                                    "hub kernel against a pre-815 bundle (about 140 s, the mint and its build included), so %s; set it to 1 "
                                    "with one of the hub knobs to run" % cls.UNEXECUTED)
        cls.hub_root = _root_knob("ROMP_CORNER_OLD_HUB_ROOT")
        if cls.hub_root:
            cls.hub_knob = "ROMP_CORNER_OLD_HUB_ROOT"
            return
        if (os.environ.get("ROMP_LINKDROP_OLD_HUB_BUILD") or "").strip() == "1":
            cls.old_hub_build = True    # _boot mints the checkout under the lab's scratch once that exists
            return
        raise unittest.SkipTest("optional: ROMP_CORNER_OLD_HUB_ROOT and ROMP_LINKDROP_OLD_HUB_BUILD both unset: the old-local half needs a hub "
                                "from before PR 815, a built checkout named by the first knob or the private clone this class mints at %s under the "
                                "second, so %s" % (OLD_HUB_SHA[:9], cls.UNEXECUTED))

    def _link_up_delivery_ms(self, p):
        """Phase p's delivery with the link up on the old bundle, the margin leg's yardstick: from the change's post returning
        (the change record's t1) to the LAST feed slot patch carrying a card (_carries_cards) that the Outline's relay
        sockets received in the phase's window (_outline_feed_patches, padded as it pads), floored at 0 (the remote can push
        a patch before the post's answer reaches the control door). The old page shows no change on a socket it holds
        (test_without_a_redial_the_old_page_does_not_show_the_change), so no visible has a link-up delivery here to measure:
        what the link carries to this page is the patch, the one each storm row is filed for, and phase D crossing as no
        frame and filing no row while the link was down is the gate this yardstick times. A phase with no such patch fails
        naming it."""
        made = [c for c in self.changes_made if c.get("phase") == p]
        self.assertEqual(len(made), 1, "the control door made phase %s's change bundle once: %r" % (p, [c.get("phase") for c in self.changes_made]))
        patches = [f for f in self._outline_feed_patches(p + "0", p + "1") if self._carries_cards(f)]
        self.assertTrue(patches, "phase %s: a feed slot patch carrying a card reached the Outline's relay socket (the link-up delivery the down window is measured "
                                 "against on the old bundle); the Outline's relay frames: %r"
                                 % (p, [(f["t"], f["slot"], f.get("coll"), f["at"]) for s in self._page("fleet")["socks"] if s["relay"] for f in s["frames"]]))
        return max(0, int(round(max(f["at"] for f in patches) - made[0]["t1"] * 1000)))

    def test_the_link_dropped_and_the_pages_stopped_dialing_while_the_row_was_down(self):
        self._assert_link_dropped_and_the_row_went_down()

    def test_dials_carry_no_caps_and_the_redial_is_served_whole(self):
        for app in self.apps:
            self._assert_dial_terms(self._relay_socks(app)[0]["url"], app, caps=False, redial=False)
        # the return's redial is one relay socket per page, and its first feed-family frame is a whole keyed feed (the
        # whole-frame road the old page depends on)
        self._assert_redialed_once_and_served_whole("resume", "restart" if self.local_drop else "end", caps=False)
        if self.local_drop:
            # …and the local restart's redial the same: one socket between the restart and phase C's first change, served
            # whole (the maintainer's round 1, fresh-3: a partial return in that window went unread)
            self._assert_redialed_once_and_served_whole("restart", "C0", caps=False)

    def test_every_wait_was_met_but_each_phases_card_wait_which_ran_to_its_cap(self):
        """Every wait the driver placed was met (_assert_every_wait_was_met) but one per link-up phase: that phase's card
        wait, which runs to its cap once, with budget left, because the old page shows no change on a socket it holds
        (test_without_a_redial_the_old_page_does_not_show_the_change reads the same freeze on the page). A card wait that
        resolved reds here as the change showing."""
        self._assert_every_wait_was_met(frozen=self._link_up_phases())

    def test_without_a_redial_the_old_page_does_not_show_the_change(self):
        """The pre-815 defect, exhibited: each link-up phase's cards were posted while every page held one relay socket, which
        stayed open through the phase with no relay socket dialed inside it, and the old feed page showed none of them: the
        card wait ran to its cap (seen.expired names it) and no card was on the page at the read. The change reached that
        page all the same: in each phase the feed page's held socket received a frame carrying a card (_carries_cards), so
        the missing cards are a change the page was sent and did not show. Phase B's is the change after the link's return,
        on the socket the return dialed; phase A's came before the drop and phase C's after the restart's redial. A card
        that showed or a card wait that resolved reds here, and so does a relay socket closed or dialed inside a phase (the
        splice's former 5 s idle cut did both, and its redials caught the page up: LinkProxy), and so does a phase whose
        cards never reached the feed page's held socket. The catch-up is
        test_each_redials_whole_frame_caught_the_old_page_up's."""
        m = self._marks()
        for p in self._link_up_phases():
            t0, t1 = m[p + "0"], m[p + "1"]
            for app in self.apps:
                socks = self._relay_socks(app)
                held = [s["i"] for s in socks if s["openAt"] and s["openAt"] <= t0 and (s["closeAt"] is None or s["closeAt"] >= t1)]
                inside = [s["i"] for s in socks if t0 <= s["dialedAt"] <= t1]
                self.assertEqual((len(held), inside), (1, []), "phase %s on the %s page: one relay socket open from the phase's first change to its end and none "
                                 "dialed inside it, so no redial could catch the page up (held %r, dialed inside %r): %r"
                                 % (p, app, held, inside, [(s["i"], s["dialedAt"], s["openAt"], s["closeAt"]) for s in socks]))
                if app == "feed":
                    frames = [f for s in socks if s["i"] in held for f in s["frames"]]
                    self.assertTrue([f for f in frames if t0 <= f["at"] <= t1 and self._carries_cards(f)],
                                    "phase %s: the change reached the old feed page: the relay socket it held received a frame carrying a card inside the "
                                    "phase (_carries_cards), so the absent cards are a change the page was sent and did not show; that socket's frames: %r"
                                    % (p, [(f["t"], f.get("slot"), f.get("coll"), f["at"]) for f in frames]))
        self._assert_seen(self._phase("A")["seen"], False, what="phase A's cards on the old feed page before the drop, on the socket it held", waited=True, expired=("card",))
        self._assert_seen(self._phase("B")["seen"], False, what="phase B's cards on the old feed page after the link's return, on the socket the return dialed", waited=True, expired=("card",))
        if self.local_drop:
            self._assert_seen(self._phase("C")["seen"], False, what="phase C's cards on the old feed page after the restart, on the socket its redial dialed", waited=True, expired=("card",))

    def test_the_old_bundle_drops_every_remote_patch_and_asks_the_local_kernel(self):
        """The freeze signature the corners lab pins, read here in phase A (steady, link up): one outline/delta-unapplied
        row per remote feed patch, a needSlot to the LOCAL kernel (which cannot repair a remote slot), and nothing asked
        of the remote (the old bundle has no per-conn receiver and no host to route by)."""
        self._control()
        A = self._rows_in("A0", "A1")
        ua = self._outline_unapplied(A)
        self.assertTrue(len(ua) >= 1 or self._outline_caught_up_whole("A0", "A1"),
                        "the old Outline filed a delta-unapplied row for the remote feed patches in phase A, or a notice post found it without an open, "
                        "served relay socket and a whole keyed feed frame caught it up there after the bundle's last notice could have been posted (a "
                        "socket closed inside the phase and its retry's whole frame absorbing the notices, as the splice's former idle cut did; a frame "
                        "before that, the ready-time frame included, does not count, nor does one while every post found an open, served socket); rows "
                        "by kind: %r" % (self._rows_by_kind(A),))
        self.assertTrue(all((d or {}).get("slot") == "feed" for d in ua), "…each naming the feed slot: %r" % (ua,))
        self.assertTrue(self._sends("fleet", "local", "needSlot"), "…and posted its needSlot to the LOCAL kernel")
        # the remote served that page through the slot path (the corners lab's pin on its old-local class); the counter
        # counts slot-path sends, deduped no-ops included, so its value is one drive's and only its sign is pinned
        self.assertGreater(self.remote_wire.get("feed_slot_split") or 0, 0, "the remote re-encoded the feed through the slot path for the old page: %r" % (self.remote_wire,))

    def test_the_storm_resumes_after_each_redial_and_is_gated_on_the_link(self):
        """The experiment's verdict: the delta-unapplied storm is one row per remote feed patch, pinned as the rows' rev
        multiset equalling the Outline's received feed slot patches per window and over the drive; it STOPS while the link
        is down (no patch arrives, so no row; phase D, due while the link was down, is the gate's own leg in
        test_a_change_due_while_the_link_was_down_crossed_nothing_and_the_return_carried_it_whole) and RESUMES after
        each redial's whole frame (the whole frame catches the page up once; the next patch freezes again). So a pause
        in the storm says no patch arrived, not that the page recovered. The new bundle files ZERO such rows across the
        same drive."""
        self._driver_ran()
        perA = self._assert_one_row_per_outline_feed_patch("A0", "A1", patches_due=True)     # the link up: a patch per notice, a row per patch
        down = self._assert_one_row_per_outline_feed_patch("drop", "resume", patches_due=False, attach_after="resume")   # the link down, phase D due: no patch, no row (the return's attach excepted)
        self.assertEqual(down, 0, "no delta-unapplied row while the link was down: no patch arrived, so no row (the storm is gated on the link); rows in the down window: %r" % (self._rows_by_kind(self._rows_in("drop", "resume")),))
        self._assert_the_down_window_outlasts_the_drives_slowest_delivery()   # the same zero, the same control in time as the gate leg's
        perB = self._assert_one_row_per_outline_feed_patch("B0", "B1", patches_due=True)     # the storm RESUMED on the return's socket
        perC = self._assert_one_row_per_outline_feed_patch("C0", "C1", patches_due=True) if self.local_drop else None   # …and after the local restart
        total = self._assert_one_row_per_outline_feed_patch()                                  # and over the whole drive, by rev
        self.assertGreaterEqual(total, perA + perB + (perC or 0), "the windows' rows are among the drive's: %r" % ((perA, down, perB, perC, total),))

    def test_nothing_was_asked_of_the_remote(self):
        for app in self.apps:
            self.assertEqual(self._sends(app, "relay", "needSlot"), [], "the old bundle has no host to route a needSlot by: nothing asked of the remote on the %s socket" % app)
            self.assertEqual(self._sends(app, "relay", "needFullFeed"), [])

    def test_each_redials_whole_frame_caught_the_old_page_up(self):
        """The catch-up half (the maintainer's round 1, extra7-3): the whole frame each redial is served shows the old feed
        page the cards its held socket froze, so the old page freezes on patches and is caught up by whole frames, not
        frozen for good. Phase A's cards, which did not show on the socket held before the drop, show after the link's
        return redial; phase B's, which did not show on the socket that redial dialed, show after the local restart's
        redial, phase A's still with them; phase D's, posted while the link was down, show after the return (the gate
        leg's waited read) and still after the restart's redial. Phase C's have no redial after them and stay frozen
        (test_without_a_redial_the_old_page_does_not_show_the_change)."""
        self._assert_seen(self._phase("B")["seenA"], True, what="phase A's cards on the old feed page after the link's return redial")
        if self.local_drop:
            C = self._phase("C")
            self._assert_seen(C["seenB"], True, what="phase B's cards on the old feed page after the local restart's redial")
            self._assert_seen(C["seenA"], True, what="phase A's cards still shown after the local restart's redial")
            self._assert_seen(C["seenD"], True, what="phase D's cards still shown after the local restart's redial")

    def test_every_relay_socket_that_opened_was_served_whole_first(self):
        """Every relay socket that opened, the first dials and the two lab-caused redials, was served a whole keyed feed
        first (the further sockets of the old-hub records made before the splice's upstream timeout was cleared were its
        idle cut's redials, served whole too)."""
        self._assert_every_opened_relay_socket_was_served_whole_first()

    def test_a_change_due_while_the_link_was_down_crossed_nothing_and_the_return_carried_it_whole(self):
        """The gate's own leg on the old bundle: phase D's cards, posted with the row down, cross as no frame and file no row
        while the link is down, the while-down read taken DOWN_WINDOW_MARGIN times this drive's slowest link-up patch
        delivery after the post (_link_up_delivery_ms: on this page a card's absence while down is also the freeze's, so the
        gate is read on the frames and the rows and timed by the Outline's patch, not by a visible); the return's whole frame
        carries them (visible after the return, no patch carrying a card and no row for one between the return and phase B's
        first change; a ledgers attach and the row this bundle files for it are allowed), and phase B's patches then file
        rows again (the storm test's phase B equality). A pause in the storm with a change due is the link, not the page."""
        self._assert_change_due_while_down_crossed_nothing_and_the_return_carried_it_whole()


class LinkProxyEnds(unittest.TestCase):
    """The splice's own ends, driven with no kernel and no browser: the target is a listening socket whose backlog completes
    the splice's connect with nobody accepting, so these run wherever the module is collected, CI's Python cells included.
    stop() is held to end every thread the splice started, drop() being the call that releases them (main's thread-stop
    census reads any call in stop() named as one of its stop verbs, the thread joins, the message's str.join or the
    holder's close, and would read the starts the same with the drop() call gone, or with the joins gone too, so it does
    not hold this), and to fail naming any
    thread still alive at its bound; a pair is held to stay up through a quiet spell longer than the 5 s timeout its
    upstream connect is handed; the port the splice reports is held to be bound from its construction until stop();
    drop() is held to return only once the accept loop of the listener it closed has ended, and to fail naming that loop
    if it outlives drop()'s bound; a dial straight after a drop() is held to be refused on Linux and not to connect
    elsewhere; and a resume() straight after a drop() is held to leave one socket listening, a count read on Linux only,
    and to splice every dial, on every system."""

    QUIET_S = 6.0   # a quiet spell longer than the 5 s timeout the splice's upstream connect is handed
    CYCLES = 5   # drop cycles per window pin: a drop that lands just before the accept loop enters its select misses the window
    DIALS = 10   # dials after each resume in the co-listen pin

    def _target(self):
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.addCleanup(srv.close)
        srv.bind(("127.0.0.1", 0))
        srv.listen(8)
        return srv

    def _proxy(self, srv):
        """A splice to the target whose held port is closed when the test ends: stop() closes it, and this cleanup, which
        runs after every cleanup the test registers later, covers a test that never calls stop() or fails before it
        reaches it."""
        p = LinkProxy(srv.getsockname()[1])
        self.addCleanup(p._hold.close)
        return p

    @staticmethod
    def _bind_errno(port):
        """None when a fresh socket binds 127.0.0.1:port, else the errno it failed with. The probe sets SO_REUSEADDR, as
        the splice's listener does, so a closed pair's TIME_WAIT on the port does not refuse it; a socket bound to the port
        without SO_REUSEADDR (the holder) or listening on it (the listener) still does."""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("127.0.0.1", port))
            return None
        except OSError as e:
            return e.errno
        finally:
            s.close()

    @staticmethod
    def _dial(port):
        """How a dial to 127.0.0.1:port ends: "connected", "refused", "timed out", or the error it failed with."""
        c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        c.settimeout(5)
        try:
            c.connect(("127.0.0.1", port))
            return "connected"
        except ConnectionRefusedError:
            return "refused"
        except TimeoutError:
            return "timed out"
        except OSError as e:
            return repr(e)
        finally:
            c.close()

    def _select_watch(self):
        """An Event set each time the splice's accept loop calls select, so a test drops the link while the loop waits in its
        select by that event and not by a sleep. select.select is replaced for the test's length and restored by its
        cleanup; a call from any other thread passes through unchanged."""
        import select
        real = select.select
        entered = threading.Event()

        def watched(*args):
            if threading.current_thread().name == "linkproxy-accept":
                entered.set()
            return real(*args)

        def restore():
            select.select = real
        select.select = watched
        self.addCleanup(restore)
        return entered

    @staticmethod
    def _listeners(port):
        """How many sockets listen on 127.0.0.1:port, read from /proc/net/tcp (Linux only: the state 0A rows)."""
        n = 0
        with open("/proc/net/tcp") as f:
            for line in f.readlines()[1:]:
                fields = line.split()
                if fields[3] == "0A" and int(fields[1].rsplit(":", 1)[1], 16) == port:
                    n += 1
        return n

    def _carries(self, p, srv):
        """One dial through the splice carrying a byte each way, as _spliced makes it, reporting how the dial ended instead
        of failing on it: "spliced", or what the client saw ("refused", "reset", "closed", or "neither end moved" within
        5 s). It waits on the event that decides it, the target's accept or the client's socket becoming readable."""
        import select
        c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.addCleanup(c.close)
        c.settimeout(5)
        try:
            c.connect(("127.0.0.1", p.port))
            c.sendall(b"x")
        except ConnectionRefusedError:
            return "refused"
        except OSError as e:
            return repr(e)
        ready, _, _ = select.select([srv, c], [], [], 5)
        if srv in ready:
            u, _ = srv.accept()
            self.addCleanup(u.close)
            u.settimeout(5)
            if u.recv(1) != b"x":
                return "spliced, but the client's byte did not cross"
            u.sendall(b"y")
            return "spliced" if c.recv(1) == b"y" else "spliced, but the target's byte did not cross"
        if c in ready:
            try:
                return "closed" if c.recv(1) == b"" else "a byte nobody sent"
            except ConnectionResetError:
                return "reset"
        return "neither end moved"

    def _spliced(self, p, srv):
        """Dial the splice and carry one byte each way, so the pair is registered and both of its pumps run."""
        c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.addCleanup(c.close)
        c.settimeout(5)
        c.connect(("127.0.0.1", p.port))
        srv.settimeout(5)
        u, _ = srv.accept()
        self.addCleanup(u.close)
        u.settimeout(5)
        c.sendall(b"x")
        self.assertEqual(u.recv(1), b"x")
        u.sendall(b"y")
        self.assertEqual(c.recv(1), b"y")
        return c, u

    def test_stop_ends_the_accept_loop_and_both_pumps_of_a_live_pair(self):
        """A pair spliced and carrying bytes both ways, then stop(): every thread the splice started has ended when it
        returns, and the client reads EOF. A stop() that joins without calling drop() first leaves the accept loop
        running, and fails here at its bound."""
        srv = self._target()
        p = self._proxy(srv)
        self.addCleanup(p.drop)
        p.listen()
        c, _ = self._spliced(p, srv)
        with p._lock:
            threads = list(p._threads)
        self.assertEqual(sorted(t.name for t in threads), ["linkproxy-accept", "linkproxy-pump", "linkproxy-pump"])
        p.stop()
        self.assertEqual([t.name for t in threads if t.is_alive()], [], "stop() returned with splice threads alive")
        self.assertEqual(c.recv(1), b"", "the client's end of the pair reads EOF after stop()")

    def test_a_pair_whose_remote_side_is_quiet_past_five_seconds_is_kept(self):
        """The lab's idle cut, held absent: a pair spliced and carrying bytes both ways, then QUIET_S with nothing from either
        side, and the pair is still registered and carries a byte each way. The splice's upstream socket kept
        create_connection's 5 s timeout until it was cleared after the connect, as kernel.py _remote_ws clears the relay's,
        and with it the pump reading the remote timed out and shut the pair after 5 s of silence; in the old-hub drives that
        cut made every relay-socket close outside the drop and the restart, and its redials caught the old page up."""
        srv = self._target()
        p = self._proxy(srv)
        self.addCleanup(p.stop)
        p.listen()
        c, u = self._spliced(p, srv)
        with p._lock:
            ups = [pair[1].gettimeout() for pair in p._pairs]
        self.assertEqual(ups, [None], "the spliced pair's upstream socket carries no timeout once connected")
        time.sleep(self.QUIET_S)
        with p._lock:
            pairs = len(p._pairs)
        self.assertEqual(pairs, 1, "the pair is still spliced after %.1f s with nothing from its remote side (an idle cut shut it)" % self.QUIET_S)
        u.sendall(b"z")
        self.assertEqual(c.recv(1), b"z", "the remote side's byte crosses after the quiet spell")
        c.sendall(b"w")
        self.assertEqual(u.recv(1), b"w", "the client's byte crosses after the quiet spell")

    def test_the_port_it_reports_is_bound_from_construction_until_stop(self):
        """The port the splice reports is a port it has bound, and it stays bound from construction until stop(): a
        fresh socket cannot bind it before listen(), while the link is up, or between a drop() and its resume(), and can
        once stop() returns. listen() and resume() listen on that port, and a dial while the link is dropped is refused on
        Linux, as at a dead -L listener, and elsewhere does not connect (the class docstring says why the two differ). The
        splice took its port from a free-port probe that closed its socket, so the port was free for anyone to take between
        the probe and listen(), and again between each drop() and its resume()."""
        srv = self._target()
        from unittest import mock
        with mock.patch.object(lab_ports, "reserve", side_effect=AssertionError("LinkProxy took its port from the lab's reservations")):
            p = LinkProxy(srv.getsockname()[1])   # the constructor binds port 0 and reads it: no probe, so no window before the bind
        self.addCleanup(p.stop)   # stop() closes the held port too; not self._proxy, whose cleanup reads the holder, so this test runs to its assertions over a splice that has none
        self.assertEqual(self._bind_errno(p.port), errno.EADDRINUSE, "constructed and not yet listening: the reported port is bound")
        p.listen()
        self.assertEqual(p._lsock.getsockname(), ("127.0.0.1", p.port), "listen() listens on the reported port")
        self._spliced(p, srv)
        self.assertEqual(self._bind_errno(p.port), errno.EADDRINUSE, "the link up: the reported port is bound")
        with p._lock:
            accept = [t for t in p._threads if t.name == "linkproxy-accept"]
        p.drop()
        self.assertEqual([t.name for t in accept if t.is_alive()], [], "drop() returned with the accept loop alive (the class docstring says why it waits)")
        self.assertEqual(self._bind_errno(p.port), errno.EADDRINUSE, "the link dropped: the reported port is still bound")
        if sys.platform.startswith("linux"):   # where the lab runs, and the hub's relay starts its redial road from the refusal
            self.assertEqual(self._dial(p.port), "refused", "the link dropped: a dial is refused")
        else:
            self.assertNotEqual(self._dial(p.port), "connected", "the link dropped: a dial does not connect")
        p.resume()
        self.assertEqual(p._lsock.getsockname(), ("127.0.0.1", p.port), "resume() listens on the reported port again")
        self._spliced(p, srv)
        p.stop()
        self.assertIsNone(self._bind_errno(p.port), "after stop() the port is released")

    def test_a_second_listen_while_the_link_is_up_is_refused(self):
        """listen() while a listener is up raises, and the first listener stays the only one and still splices. Each
        listener binds beside the holder through SO_REUSEPORT, which would let a second listener bind beside the first
        too, and a dial handed to the listener whose accept loop has ended would sit in its backlog, never spliced."""
        srv = self._target()
        p = LinkProxy(srv.getsockname()[1])
        self.addCleanup(p.stop)   # as in the test above, so this one also runs over a splice with no holder
        p.listen()
        first = p._lsock
        with self.assertRaises((RuntimeError, OSError)):   # the guard's refusal, or a bind's
            p.listen()
        self.assertIs(p._lsock, first, "the first listener is still the live one")
        with p._lock:
            accepts = [t.name for t in p._threads if t.name == "linkproxy-accept"]
        self.assertEqual(accepts, ["linkproxy-accept"], "one accept loop was started")
        self._spliced(p, srv)

    def test_a_dial_straight_after_a_drop_is_refused(self):
        """A dial made the moment drop() returns, the drop landing while the accept loop waits in its select (the watch's
        event, not a sleep): refused on Linux, as at a dead -L listener, and elsewhere it does not connect. Before drop()
        waited for the loop, the closed listener was still listening at that moment, so the dial connected and was reset
        when the loop's select returned, where the hub's relay starts its redial road from a refusal (the class docstring).
        The cycle runs CYCLES times, a resume() between cycles."""
        srv = self._target()
        p = self._proxy(srv)
        self.addCleanup(p.stop)
        in_select = self._select_watch()
        p.listen()
        for cycle in range(self.CYCLES):
            self.assertTrue(in_select.wait(5), "cycle %d: the accept loop reached its select" % cycle)
            p.drop()
            end = self._dial(p.port)
            if sys.platform.startswith("linux"):   # where the lab runs, as the port pin gates it
                self.assertEqual(end, "refused", "cycle %d: a dial straight after drop() is refused" % cycle)
            else:
                self.assertNotEqual(end, "connected", "cycle %d: a dial straight after drop() does not connect" % cycle)
            in_select.clear()
            p.resume()

    def test_a_resume_straight_after_a_drop_listens_alone_and_splices_every_dial(self):
        """drop() and then resume() at once, the drop landing while the accept loop waits in its select (the watch's
        event): when resume() returns one socket listens on the port (read on Linux alone, from /proc/net/tcp), and each
        of DIALS dials after it is spliced and carries a byte each way, on every system. Before drop() waited for the
        loop, the closed listener was still listening when resume() bound the new one beside it through SO_REUSEPORT, and
        the system handed a dial to the closed one, which connected and was reset when its select returned. The cycle runs
        CYCLES times."""
        srv = self._target()
        p = self._proxy(srv)
        self.addCleanup(p.stop)
        in_select = self._select_watch()
        p.listen()
        for cycle in range(self.CYCLES):
            self.assertTrue(in_select.wait(5), "cycle %d: the accept loop reached its select" % cycle)
            p.drop()
            in_select.clear()
            p.resume()
            if sys.platform.startswith("linux"):
                self.assertEqual(self._listeners(p.port), 1, "cycle %d: one socket listens on the port when resume() returns" % cycle)
            ends = [self._carries(p, srv) for _ in range(self.DIALS)]
            self.assertEqual(ends, ["spliced"] * self.DIALS, "cycle %d: every dial after the resume is spliced" % cycle)

    def test_stop_fails_naming_every_thread_alive_at_its_bound(self):
        """With the release skipped (drop() made a no-op on this instance), the accept loop never sees a drop and outlives
        the joins: stop() raises at its bound naming the thread, where a timed join that returned in silence would let the
        teardown pass with the splice still running."""
        srv = self._target()
        p = self._proxy(srv)
        self.addCleanup(LinkProxy.drop, p)   # the real release, once the test is done
        p.listen()
        p.STOP_BOUND_S = 0.5
        p.drop = lambda: None
        with self.assertRaises(AssertionError) as cm:
            p.stop()
        self.assertIn("linkproxy-accept", str(cm.exception))

    def test_drop_fails_naming_the_accept_loop_alive_at_its_bound(self):
        """drop() waits for the accept loop of the listener it closed, within STOP_BOUND_S, and past that bound raises
        naming the loop, as stop() does. Here the loop holds a connection it accepted at the lock where it registers the
        pair (the gate, which opens only once the test is done), so it outlives drop()'s bound. A timed join that returned
        in silence would let drop() return with the loop still running, and nothing would say so."""
        srv = self._target()
        p = self._proxy(srv)
        at_lock, go = threading.Event(), threading.Event()
        p._lock = _GatedLock(at_lock, go)
        self.addCleanup(p.stop)
        self.addCleanup(go.set)   # before stop(): the loop, let through, sees the drop at the registration and returns
        p.listen()
        c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.addCleanup(c.close)
        c.settimeout(5)
        c.connect(("127.0.0.1", p.port))
        self.assertTrue(at_lock.wait(5), "the accept loop reached the lock where it registers the pair")
        p.STOP_BOUND_S = 0.5   # inside the gate's 5 s wait, so the loop is still held when drop()'s bound comes
        with self.assertRaises(AssertionError, msg="drop() returned in silence with the accept loop alive past its bound") as cm:
            p.drop()
        self.assertIn("linkproxy-accept", str(cm.exception))
        del p.STOP_BOUND_S   # stop(), in the cleanup, joins within the class's bound

    def test_a_pair_accepted_across_the_drop_is_closed_by_the_accept_loop(self):
        """The accept loop has passed its drop check with a connection in hand when stop()'s drop() sweeps the pairs, and
        only then registers the pair: the gate holds the loop at the lock where it registers until drop()'s hold of that
        lock for the sweep ends, the event the window needs. (The gate opened on drop()'s return until drop() began to wait
        for the loop; with that wait, drop() and the loop would each wait on the other until drop()'s bound.) The loop must
        see the drop there and close the pair itself, since no sweep will. Registered anyway, the pair's two pumps run on
        sockets nobody shuts, and stop() fails at its bound naming them."""
        srv = self._target()
        p = self._proxy(srv)
        self.addCleanup(LinkProxy.drop, p)
        p.STOP_BOUND_S = 2.0   # the failure this test exists to catch comes at the bound: a late pair's pumps block on sockets nobody shuts
        at_lock, swept = threading.Event(), threading.Event()
        after = []   # whether drop() had cleared the listener when the loop registered the pair: the window this test holds open
        p._lock = _GatedLock(at_lock, swept, released=swept, registering=lambda: after.append(p._lsock is None))
        p.listen()
        c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.addCleanup(c.close)
        c.settimeout(5)
        c.connect(("127.0.0.1", p.port))
        self.assertTrue(at_lock.wait(5), "the accept loop reached the lock where it registers the pair")
        p.stop()
        self.assertEqual(after, [True], "the loop registered the pair after drop() had cleared the listener, the window this test holds open")
        self.assertEqual(c.recv(1), b"", "the client's end of the pair accepted across the drop reads EOF")

    def test_a_pair_accepted_before_a_drop_is_closed_before_the_resume_listens(self):
        """The same window across drop() and resume(): the loop took the connection on the listener a drop then closes, and
        is held at the lock where it registers the pair until someone waits for the loop (the gate opens when the loop's
        thread is joined, which drop() does once it has swept the pairs). drop() returns only once the loop has closed the
        pair, so no listener is live when the loop decides the pair's fate, and a resume() after the drop cannot have it
        spliced across (the stray frame the accept loop's comment names). Before drop() waited for the loop, a resume()
        straight after the drop bound a new listener while the loop still held the pair, and only the registration's
        identity check closed it: without that wait this test's own wait for the loop, after its resume(), opens the gate,
        and a listener is live at the registration. The client's read is bounded at 2 s: spliced, the pair would carry
        nothing and the read would time out rather than read EOF."""
        srv = self._target()
        p = self._proxy(srv)
        self.addCleanup(p.stop)
        at_lock, go = threading.Event(), threading.Event()
        live = []   # whether a listener was live when the loop registered the pair
        p._lock = _GatedLock(at_lock, go, registering=lambda: live.append(p._lsock is not None))
        p.listen()
        with p._lock:
            loop = [t for t in p._threads if t.name == "linkproxy-accept"][0]
        join = loop.join

        def joined(timeout=None):   # the gate opens when anyone waits for the loop: drop(), or failing that the wait below
            go.set()
            return join(timeout)
        loop.join = joined
        c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.addCleanup(c.close)
        c.settimeout(5)
        c.connect(("127.0.0.1", p.port))
        self.assertTrue(at_lock.wait(5), "the accept loop reached the lock where it registers the pair")
        p.drop()
        p.resume()
        loop.join(10)
        self.assertFalse(loop.is_alive(), "the dropped listener's accept loop ended")
        self.assertEqual(live, [False], "no listener was live when the loop registered the pair it took on the dropped listener (drop() returned before the loop did)")
        c.settimeout(2)
        self.assertEqual(c.recv(1), b"", "the client's end of the pair accepted before the drop reads EOF")

    def test_the_accept_loop_ends_when_its_listener_closes_before_the_select(self):
        """A drop that closes the listener after the loop's check and before its select: the select on the closed socket
        raises, and the loop returns rather than dying of the exception in its thread. The state the loop sees across
        that interleaving is set directly: its socket still the live listener, no drop set, and the socket closed, whose
        descriptor then reads -1."""
        srv = self._target()
        p = self._proxy(srv)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.close()
        p._lsock, p._down = s, False
        self.assertIsNone(p._accept(s))


class _GatedLock:
    """A stand-in for LinkProxy._lock: the accept thread's first entry signals `arrived` and waits for `go` before it takes
    the lock, so a test can run drop() between the accept loop's drop check and the registration of the pair it
    accepted. `released`, when given, is set when a hold of the lock ends after that arrival: the accept thread holds none
    while it waits at the gate, and in these tests the first such hold is drop()'s sweep of the pairs, so a gate whose
    `go` is `released` opens once the sweep is done. `registering`, when given, is called by the accept thread as soon as it holds the lock on that entry, where the
    loop reads whether its listener is still the live one."""

    def __init__(self, arrived, go, released=None, registering=None):
        self._lock = threading.Lock()
        self._arrived, self._go = arrived, go
        self._released, self._registering = released, registering
        self._gated = False

    def __enter__(self):
        gate = not self._gated and threading.current_thread().name == "linkproxy-accept"
        if gate:
            self._gated = True
            self._arrived.set()
            self._go.wait(5)
        self._lock.acquire()
        if gate and self._registering is not None:
            self._registering()
        return self

    def __exit__(self, *exc):
        self._lock.release()
        if self._released is not None and self._gated:
            self._released.set()
        return False


if __name__ == "__main__":
    unittest.main()
