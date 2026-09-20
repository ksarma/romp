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
discriminating case (round 1 found the down window otherwise idle, so its zero rows could not tell "the link gates the
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

What this lab cannot make red, said plainly: the per-dial receiver reset in connect(). Every kernel in this repo
serves a fresh socket a whole frame first (dstate is per connection), so a stale receiver is re-seeded before any
patch reaches it and the reset is latent here; the node test that removes it and sends a patch first
(ui/webview/federation-remote-view-delta.test.ts, the redial tests) is where that guard is proven. The mutations that
DO make this lab red are recorded in its report: the redial term stripped from remoteDialUrl, the whole-frame base
write dropped from the feed arm, the local-down gate dropped from connect(), and the old hub bundle in place of this
one (ROMP_LINKDROP_HUB_ROOT, the base-hub lever).

Knobs. LinkDropBothNew needs none: it runs wherever this checkout's served labs run, CI's served job included (about
a minute and a half: two supervisor waits, the 42 s down dwell and a hub restart; 82.5 s for its setUpClass in each of
the two drives of 2026-09-20 at this code, clean trees at the commits before these figures were written in
(`ROMP_LINKDROP_LAB=1 ROMP_LINKDROP_OLD_HUB_BUILD=1 pytest tests/test_federated_linkdrop_served.py --durations=20`, the
builder's `r5/lab-head1.log` and `r5/lab-head2.log` outside the repo). ROMP_LINKDROP_HUB_ROOT boots its hub from another
checkout with its
PREBUILT vscode-extension/dist (the fails-before lever for the new-hub class). The old-hub class, the storm's own
witness (the pre-815 half), runs under ROMP_LINKDROP_LAB=1 (a minute and three quarters to two minutes more: 120.3 and
102.0 s for its setUpClass, the mint and its build included, in those two drives, the module whole at 203 and 185 s;
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
drive at round 1's head gave 3 / 0 / 1 / 3 (two relay sockets churned inside phase B and absorbed two notices into
whole frames: no patch, so no row, and the equality held at 7 / 7), as did one verifier drive at the round-2 head
whose hook was mutated for a red (its hub rows are real); and three builder drives gave 0 / 0 / 3 / 3 (the Outline's
relay socket churned 0.7 s into phase A and its retry's whole frame absorbed all three notices: phase A 0 rows to 0
patches, the drive 6 / 6 by rev): one at the round-3 head, RED there on the per-phase at-least-one-patch floors of the
storm test and the phase-A drops test with the correspondence intact; one at the 30 s dwell on 2026-09-20, red on the
margin pin with its floors green; and one at this code the same day, green (`r5/lab-head2.log`). Those are the data
behind the churn-keyed allowance (_outline_caught_up_whole: an empty phase is excused only when one of its notice posts
found the Outline holding no open relay socket that had received its first feed-family frame, and then only by a whole
keyed feed frame the Outline received there after the bundle's last notice could have been posted; in all three the
socket closed 0.7 s into phase A, between the first and second posts (the first, 0.01 s in, found it open and served;
the second and third, at 1.01 and 2.01 s, found no open socket, so the gap held at those two), and the frames came about
0.8 s after the last, 2.87, 2.83 and 2.86 s into phase A against a last notice posted from 2.01 s, so all three are green
on the floors under it). The population is counted as of that last drive, since any later drive can add either shape: the
builder's cache then held 18 old-hub records of the unmutated module (the builder's earlier drives at three pre-PR
vintages among them, two with a hand-built old hub), 15 at 3 / 0 / 3 / 3 and those 3 at 0 / 0 / 3 / 3, and the
reviewers' further drives at round 1's head gave 3 / 0 / 3 / 3 (the per-window table over the report JSONs outside the
repo, `python3 analyse.py <report.json>...`, with _rows_in's 1.5 s pad). ZERO while the link was down in every recorded
drive. The storm
is gated on remote patches arriving, which is gated on the link: with phase D due while the link was down, no row
filed until the link returned, the return's whole frame carried D and filed no row for it, and the next patch (phase
B's) filed a row again. A relay redial does not end the storm but restarts it: each redial's one whole frame catches
the old page up once and the next patch freezes it again, so on a hub whose link comes and goes the storm pauses and
resumes with the link and looks intermittent and self-healing when it is neither. That is why the old-hub class
stays in this lab: a lab that only proves the fixed behaviour loses the evidence of what was fixed, and a reader in
three months must be able to learn that a redial used to restart the storm. The new bundle files zero such rows
across the same drive, and the three mutations recorded in the report (the redial term stripped, the whole-frame
base write dropped, the local-down gate dropped) each turn one of its assertions red, so a zero here is a zero the
drive can see through.

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
# before the drive, the readers after: 55 s measured for the whole setUpClass), and the driver's own worst case
# (driver_worst_case_s: its wait budget plus the bounded work between the waits) sits under the subprocess timeout, so a
# degraded drive returns through its wait budget with the expired waits recorded or, for a hang in the control door,
# through driver_error ("driver timed out"), and the labs after this one still run.
# tests/test_federated_linkdrop_driver_bound.py pins the arithmetic, the budget, the bytes sent and the premise that every
# wait the driver places draws on the budget or is a fixed dwell the arithmetic counts.
CI_TEST_TIMEOUT_S = 600      # pytest --timeout on CI's served step
BOOT_ROOM_S = 120            # setUpClass outside the drive: the kernels' boots, the dist copy, the readers after the drive
DRIVER_TIMEOUT_S = 480       # the node driver's subprocess timeout: CI_TEST_TIMEOUT_S - BOOT_ROOM_S
DRIVER_FIXED_S = 40          # the driver's work outside its waits and the control door: the browser launch (playwright's own
#                              30 s cap, then exit 3), the snapshots and the visible reads
POST_TIMEOUT_S = 5           # one control-door post to the remote (a notice, a todo); measured in milliseconds
HUB_TERM_WAIT_S = 10         # _restart_hub waits this long for SIGTERM to end the hub before SIGKILL
HUB_SPAWN_TRIES = 40         # _spawn_hub's /healthz tries, a 1 s probe and a 0.5 s pause each (the respawn answers in about a second)
PHASE_SETTLE_MS = 1500       # phase() lets the panes' rows land on the hub before marking the phase's end
DOWN_WINDOW_MARGIN = 2.0     # the while-down read comes this many of the drive's slowest link-up deliveries after phase D's post
#                              (_assert_the_down_window_outlasts_the_drives_slowest_delivery; down_dwell_ms is sized for it)
DOWN_READ_ROOM_MS = 2000     # the room down_dwell_ms holds past DOWN_WINDOW_MARGIN x wait_ms: a phase's delivery (seen.waitedMs) is stamped
#                              AFTER visible()'s reads (waitVisible), so a wait that resolved at the cap's edge is stamped past the cap by the
#                              reads' duration; without the room the margin pin could red on a drive whose link-up waits all resolved and
#                              showed. A phase whose wait ran to its cap is refused by the margin leg itself (seen.expired, round 5), never
#                              measured against the room, so the room is for the reads after a wait that RESOLVED. The reads alone take
#                              6 to 22 ms where the wait had nothing left to wait for (D.seenAfterReturn.waitedMs over 34 recorded drives
#                              as of 2026-09-20, `python3 reads_census.py <report.json>...` outside the repo); over every unmutated recorded
#                              drive that carries the reading (the same command over the population as of 2026-09-20; the count is dated by
#                              drive elsewhere, since a drive at any head moves it) it runs 6 to 125 ms, the 125 ms one new-bundle drive's
#                              (`r6-margin/lab-head2.log`) where a wait still had a render to wait for, so the reading is an upper bound on
#                              the reads. The room the reads get, this constant over DOWN_WINDOW_MARGIN (1 s: the relation pin divides
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
    """The longest the class's driver can run: its wait budget (every wait it places draws on it, BUDGET_JS) plus the
    work between the waits that the budget does not cover, each at its own bound: the down dwell, the hub restart, the
    change bundles (A, D, B and, with the local drop, C), the phases' settles, the launch and the snapshots. Pinned
    under DRIVER_TIMEOUT_S by tests/test_federated_linkdrop_driver_bound.py."""
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
    ssh -L forward, so the link can be dropped and restored while both kernels stay up. start() listens and splices each
    accepted connection to the target; drop() closes the listener (a dial is refused, as at a dead -L listener) and
    shuts every spliced pair (both ends read EOF: the hub's upstream, the remote's client); resume() listens again on
    the same port. Every transition is stamped for the record."""

    def __init__(self, target_port):
        self.target = int(target_port)
        self.port = _dial._free_port()
        self._lsock = None
        self._down = True
        self._pairs = set()
        self._lock = threading.Lock()
        self.events = []

    def start(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("127.0.0.1", self.port))
        s.listen(64)
        s.setblocking(False)
        self._lsock = s
        self._down = False
        threading.Thread(target=self._accept, args=(s,), daemon=True, name="linkproxy-accept").start()
        self.events.append({"ev": "up", "t": time.time()})
        return {"port": self.port}

    def _accept(self, s):
        # select with a short timeout, not a blocking accept: drop() closing the listener from another thread does not
        # reliably wake a blocked accept(), and a connection already in the backlog when the listener closed could be
        # spliced onto the live remote AFTER a drop (a stray frame crossing a "dropped" link, seen in run 1). This loop
        # owns the one socket it was started with and exits the instant that socket is no longer the live listener or
        # _down is set, and re-checks _down after every accept, so no connection is ever spliced past a drop.
        import select
        while s is self._lsock and not self._down:
            try:
                r, _, _ = select.select([s], [], [], 0.2)
            except OSError:
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
            pair = (c, u)
            with self._lock:
                self._pairs.add(pair)
            for a, b in ((c, u), (u, c)):
                threading.Thread(target=self._pump, args=(a, b, pair), daemon=True, name="linkproxy-pump").start()

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
        return {"port": self.port, "spliced": len(pairs)}

    def resume(self):
        return self.start()

    def stop(self):
        self.drop()


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
# (DRIVER_TIMEOUT_S) instead of pytest-timeout ending the whole served pytest process at CI's per-test cap. Pure in `now`
# and `sleep`, so tests/test_federated_linkdrop_driver_bound.py runs it under node with a clock of its own; DRIVER opens
# with it.
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
  return { left, capped, waitFor };
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
const budget = makeBudget({ budgetMs: cfg.driverBudgetMs, now: Date.now, sleep: (ms) => new Promise((r) => setTimeout(r, ms)), out });
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
const snap = async (page) => page.evaluate(() => ({ socks: (window.__socks || []).map((s) => Object.assign({}, s, { frames: s.frames.slice() })), sends: (window.__sends || []).slice(), localUp: window.__rompLocalUp === undefined ? null : window.__rompLocalUp }));
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
// not fatal: the old bundle's socket churn can keep frames coming, and the phase still runs; a spent budget is a give-up too
const quiet = async (what) => {
  for (let i = 0; i < cfg.quietTries; i++) {
    if (budget.left() === 0) { out.quietGaveUp.push(what + " (the driver's wait budget was spent)"); return; }
    const a = await relayFramesTotal(); await pages[APPS[0]].waitForTimeout(budget.capped(cfg.quietStepMs)); if (await relayFramesTotal() === a) return;
  }
  out.quietGaveUp.push(what);
};
const provText = () => pages.fleet ? pages.fleet.evaluate((sel) => { const e = document.querySelector(sel); return e ? e.textContent : null; }, cfg.provSel) : Promise.resolve(null);
const cardSel = (ch, n) => '[data-key="a:notice:' + cfg.sid + ':' + ch.noticeKeys[n] + ':' + ch.noticeRevs[n] + '"]';
const visible = async (ch) => {
  const v = { cards: [] };
  for (let n = 0; n < ch.noticeKeys.length; n++) v.cards.push((await pages.feed.locator(cardSel(ch, n)).count()) > 0);
  if (pages.waiting && ch.todoText) v.todo = (await pages.waiting.locator(".ut-text", { hasText: ch.todoText }).count()) > 0;
  if (pages.fleet && ch.prompt) v.prov = await provText();
  return v;
};
// the phase's visibles, waited for CONCURRENTLY (three pages, three waiters), so the point is bounded by ms, not three
// times it, and each waiter's timeout draws on the budget. Each wait's OUTCOME is recorded, never swallowed (round 5): a
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
  // designed guarantee (round 3): every page holds exactly ONE open relay socket. The old bundle's churn closes a page's socket
  // for its 2 s retry every few seconds, and before this wait the drop landed 0.58 to 0.80 s after the pages' redials reopened
  // in ten of the sixteen recorded old-hub drives (`python3 held_census.py <report.json>...` outside the repo): the feed page's
  // redial-to-visible latency plus the settle against the retry, a coincidence and not a guarantee. `held` is the snapshot that
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
    # ratio of it (the ratios run from 2.8x to over 600x), with driver_budget_ms as the binding bound (BUDGET_JS: every wait
    # draws on it). The spans by mark pair over every unmutated recorded drive as of the CI-shaped drive of 2026-09-20 at the
    # round-5 code (`r5/lab-ci2.log`, the drive after `r5/lab-head2.log`, whose own record is the 45th; 45 drives, 27
    # new-bundle and 18 old-hub; `python3 waits_census.py <report.json>...` over the builder's reports outside the repo; a census over a growing record is dated by construction: the 25-drive census
    # quoted here before missed three bounds later drives moved, redialed2's maximum from 0.81 to 1.04 s, rowDown's minimum
    # from 4.6 to 4.3 s and closed's maximum from 0.030 to 0.27 s, so a later drive may move one again and the caps are
    # floors far above every bound, not fits): closed, drop -> closed, 0.008 to 0.27 s; rowDown, closed -> rowDown, 4.3 to
    # 14.5 s (the supervisor's silent-poll window, longest under the old bundle's churn); rowUp, resume -> rowUp, 0.8 to
    # 13.2 s (a quarter-second pass inside the supervisor's fast window, its steady 15 s pass outside it); redialed, rowUp ->
    # redialed, 0.8 to 4.6 s; localUp, restarted -> localUp, 0.013 to 0.30 s (the restart itself, SIGTERM and the 3 s held
    # down, is the control door's and not this wait's); redialed2, localUp -> redialed2, 0.011 to 1.04 s. held, A1 -> drop
    # (every page holding one open relay socket before the drop), is new in round 3 and has no recorded span before it: the
    # snapshot alone took 9 to 35 ms there, and in the five drives at this code the wait took 16 to 21 ms with every page
    # already holding one; its cap is closed's, a floor well above the mechanism's worst (a page lacks an open socket for the relay's
    # 2 s retry plus the open, once per churn of the old bundle's socket), not a fit to those spans.
    waits_ms = {"held": 20000, "closed": 20000, "rowDown": 40000, "rowUp": 40000, "redialed": 30000, "localUp": 30000, "redialed2": 30000}
    page_wait_ms = 30000      # the start, per page: its load, its first relay socket, that socket's whole frame
    driver_budget_ms = 225000  # every wait the driver places draws on this one budget. The budget is a DEADLINE, not a meter of the
    #                            waits: makeBudget fixes t0 at the driver's start, capped(ms) is min(ms, what is left to the deadline), and
    #                            the fixed dwells and the control-door calls run to their own bounds whether or not it has passed (their
    #                            time before it draws it down too). So the budget less the record's budget.leftMs is the drive's WALL
    #                            CLOCK from the launch to the end mark, the 42 s dwell and the settles included, not a sum of its waits:
    #                            78.4 s on the new bundle and 97.2 s on the old in the drive of 2026-09-20 at this code (225000 less
    #                            budget.leftMs in `r6-margin/lab-head1.log`'s reports, the builder's lab logs outside the repo; the old
    #                            bundle's frozen feed page shows a phase's cards only at the next churned socket's whole frame, so its
    #                            drives run longer). 225 s, not 240, so the worst case holds the 42 s dwell under DRIVER_TIMEOUT_S.
    # The row stays down this long after phase D's post, and the gate DEPENDS on it (round 2's ruling): the while-down read of D
    # comes DOWN_WINDOW_MARGIN times the drive's own slowest link-up delivery after the post, asserted by both classes' gate legs
    # (_assert_the_down_window_outlasts_the_drives_slowest_delivery). The dwell is sized against the lab's own cap on that
    # delivery, not against the drives seen: a phase's delivery is seen.waitedMs, and waitVisible caps every wait it holds at
    # wait_ms and records each wait's outcome (seen.expired), so the margin leg itself refuses a phase whose wait ran to its cap
    # (round 5), beside the visibility legs, and every delivery it measures is a wait that RESOLVED, before its cap; the dwell is
    # DOWN_WINDOW_MARGIN x wait_ms plus DOWN_READ_ROOM_MS of room for the reads that follow the wait, so the pin holds for every
    # drive whose link-up waits all resolved and showed, the reads inside the room, and reds only for a window shorter than that
    # (tests/test_federated_linkdrop_driver_bound.py pins the relation). The slowest delivery recorded is the old bundle's, whose frozen feed page shows a change only at the next
    # churned socket's whole frame, and a change whose three notices straddle a churn waits for the frame after that: 19,013 ms
    # over eighteen recorded unmutated old-hub drives as of the drive at `r5/lab-ci2.log` (2026-09-20, the round-5 code, the
    # drive the waits census above is dated to; `python3 population.py old | xargs python3 analyse.py`, the builder's scripts
    # over the report JSONs outside the repo, max of the phases' seen.waitedMs; the new bundle's is 1.35 s at most over the
    # twenty-seven as of that drive). A dwell of 30 s, sized at twice the 12.9 s
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
        (round 1: a lab gated whole was the one served lab of 94 with no executing test in CI, and it guards PR 815)."""
        return None

    @classmethod
    def _boot(cls):
        if not os.path.isdir(os.path.join(EXT, "node_modules", "playwright")):
            raise unittest.SkipTest("extension deps absent (npm ci not run here), the served lab needs them")
        probe = subprocess.run(["node", "-e", "const p=require(process.argv[1]);process.stdout.write(p.chromium.executablePath())",
                                os.path.join(EXT, "node_modules", "playwright")], capture_output=True, text=True)
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
        cls.rport, cls.rtoken = _dial._free_port(), "testtok-remote-ld"
        cls.hport, cls.htoken = _dial._free_port(), "testtok-hub-ld"
        rp, cls.rlog = _dial._kernel(cls.lab, "testhost", cls.rport, cls.rtoken, [(SID_R0, "api", 1), (SID_R1, "worker", 2)] + EXTRA,
                                     bin_dir=os.path.join(cls.remote_root or ROOT, "bin"))
        cls.procs.append(rp)
        cls.proxy = LinkProxy(cls.rport)
        cls.proxy.start()
        cls.hub_proc, cls.hlog = _dial._kernel(cls.lab, "hub", cls.hport, cls.htoken, [], bin_dir=os.path.join(cls.hub_root or ROOT, "bin"))
        cls.procs.append(cls.hub_proc)
        cls.hub_restarts = []
        _dial.checkin(cls.hport, cls.htoken, cls.proxy.port, cls.rtoken)   # the peer's kernelPort IS the splice: the relay and the probes go through it
        cls.transcript = cls._transcript_path()
        cls.append_parent = _dial.seed_uuid(1, _dial.SEED_PAIRS - 1, "a")   # api's seed tag is 1: the first append chains to its last reply
        cls.changes_made = []
        cls.ctl = _Control(cls)
        cls.ctl.start()
        cls.result, cls.driver_error = None, None
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
        skip: _boot's kernel check and _ready_dist share this one rule (round 1's tests-3; round 3 found the kernel check
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
        a build that fails otherwise skip the class and the run reports green (round 1's tests-3, ruled twice), while the
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
        of ours may reach it, and a repo-wide clearing of stale records at teardown is not a test's to run (round 1).
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
        for _ in range(HUB_SPAWN_TRIES):   # a 1 s probe and a 0.5 s pause each: hub_restart_bound_s counts them
            try:
                urllib.request.urlopen("http://127.0.0.1:%d/healthz" % cls.hport, timeout=1)
                return proc
            except Exception:
                time.sleep(0.5)
        proc.kill()
        proc.wait()
        raise RuntimeError("the respawned hub kernel never served /healthz")

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
            so = e.stdout if isinstance(e.stdout, str) else (e.stdout or b"").decode()
            cls.driver_error = "driver timed out; partial output:\n%s" % so
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
               "remote_sha": cls.remote_sha, "driver_error": cls.driver_error, "result": cls.result, "remote_wire": cls.remote_wire,
               "remote_sends": getattr(cls, "remote_sends", {}), "hub_diag_by_kind": by_kind, "hub_diag_rows": cls.hub_diag_rows,
               "remote_wsopen_relay": cls.remote_wsopen, "proxy_events": cls.proxy.events if cls.proxy else [], "hub_restarts": cls.hub_restarts,
               "changes_made": cls.changes_made}
        Path(d, cls.__name__ + ".json").write_text(json.dumps(rec, indent=1, sort_keys=True))

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "ctl", None):
            cls.ctl.stop()
        if getattr(cls, "proxy", None):
            cls.proxy.stop()
        for p in getattr(cls, "procs", []):
            try:
                p.kill()
                p.wait()
            except Exception:
                pass
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
        while a page's local socket was down and flushed late lands anywhere in the down window (round 1, tests-6)."""
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
        later frame excuses the window). The mechanism excused: the old bundle's socket churn (its relay socket closes every
        few seconds, the 2 s retry redials, the remote serves the new socket a whole frame), whose whole frame absorbs the
        notices posted while the socket was down, so that phase's change crosses as no patch and files no row. The
        distinguishing datum an empty window needs (round 2's ruling on correctness-1: the allowance is keyed on this EVENT,
        read from the hook's frames, never a dropped requirement). Round 4 added the gap because the frame alone was no key:
        on the old bundle a routine redial produces a whole frame after the phase's notices were already delivered as
        patches, so the frame-only excuse was available in 47 of the 75 phase windows (A, B, C) over the 25 unmutated
        old-hub records in the builder's cache as of the drive at `r6-margin/lab-head5.log` (2026-09-20; `python3
        population6.py old | xargs python3 excuse_census.py <tests_dir>`, this helper over each record's windows, outside the
        repo), load-bearing in 5, and a planted gating miss (a phase's patches and rows removed from the record) stayed green
        at both floors; keyed on the gap it is available in 5 of those 75, the phase-A windows of the five drives whose
        Outline socket churned inside phase A (the same command at this module), and the planted miss reds. Over all 75
        windows the planted miss (the phase's feed patches and rows removed, every frame kept) reds the floor in 70 and stays
        excused in those 5 (`python3 population6.py old | xargs python3 census_module.py <tests_dir>`, the floor itself over
        each window, outside the repo, as of the same drive): a real gating miss during a churn is indistinguishable from the
        churn in the record, the excuse's remaining hole and the price of excusing the churn at all. The post times
        are DERIVED from the change record (its t0 plus i x NOTICE_GAP_S, _change's own sleeps between the posts, on the
        poster's clock at millisecond resolution); each notice's answer in the record carries the remote kernel's own stamp
        for the notice too (`at`, `t`), but in whole seconds and on the other clock, too coarse for a millisecond gap check,
        so it is not read here. The
        frame key is after the bundle's last notice, not in the window: the left edge is the later of the window's mark and
        the earliest the last notice's post could have started, because a frame before that carries at most the earlier
        notices and cannot explain the later ones reaching the Outline as nothing (round 3: a frame anywhere in the window's
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
        notice could have been posted: a churned socket's retry absorbs the notices into one whole frame and files no row, so
        a count is one drive's, and a window with neither a patch nor that excuse is a change that reached the Outline as
        nothing, not the storm); without, both sides are empty. With attach_after (a mark) the return window's allowance
        reaches into this window's right pad: a card-less feed-family patch at or after that mark is the connect push's
        ledgers attach, by design and with no card in it, and it and the row the old bundle files for it (matched to the
        ATTACH, _minus_attach_rows: at most one row per attach, naming the feed slot, carrying the attach's rev and stamped at or
        after the attach's floored second with a second of slack; round 4: a rev is no identity, since the Outline's feed patch
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
                                               "notice could have been posted (the old bundle's socket churn: the retry's whole frame absorbs the notices posted "
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
                                           "reads a designed precondition and not the drop's timing against the old bundle's churn): %r" % (app, held))
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

    def _assert_redialed_once_and_served_whole(self, k0, k1, caps, exactly=True):
        """A relay socket per page dialed in [k0, k1), a redial by its terms, that opened and received a WHOLE keyed feed
        as its first feed-family frame (the remote's client dict is per socket: it holds nothing to patch). `exactly`
        pins ONE such socket (the new bundle's clean redial); False allows the old bundle's socket churn but still
        pins that the FIRST socket that opened was served whole."""
        for app in self.apps:
            fresh = self._relay_socks(app, k0, k1)
            opened = [s for s in fresh if s["openAt"]]
            self.assertTrue(opened, "the %s page dialed a relay socket that opened between %s and %s: %r" % (app, k0, k1, [(s["url"], s["openAt"], s["closeAt"], s["code"]) for s in fresh]))
            if exactly:
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
        a frame (round 1, fresh-2)."""
        for app in self.apps:
            opened = [s for s in self._relay_socks(app) if s["openAt"]]
            with_frame = [(s, self._first_feed_family(s)) for s in opened if self._first_feed_family(s) is not None]
            self.assertTrue(with_frame, "the %s page opened a relay socket that received a feed-family frame: %r" % (app, [(s["i"], s["openAt"], self._kinds(s)) for s in opened]))
            bad = [(s["i"], f["t"], f["slot"], self._kinds(s)) for s, f in with_frame if not (f["t"] == "feed" and f.get("asks") is not None)]
            self.assertEqual(bad, [], "every relay socket the %s page opened was served a WHOLE keyed feed first (%d opened, %d received a frame; a patch "
                                      "or feedDelta first is a patch onto a base the socket never held): %r" % (app, len(opened), len(with_frame), bad))

    def _assert_every_wait_was_met(self):
        """Every wait the driver placed (waitFor: the held sockets closing, the row leaving and returning to up, a fresh
        relay socket per page holding a whole frame, the local sockets reopening; and every visibility wait, waitVisible:
        a phase's card, todo and provisional row, and phase D's after the return) was met inside its timeout. An
        expired wait means a phase ran on an unmet precondition and the record shows a partial drive that every other
        assertion may still pass (round 1, fresh-3: a forced timeout gave 3 / 0 / 3 / 2 and five green tests). The
        visibility waits' expiries were swallowed until round 5, so a phase whose cards never came left only a waitedMs
        at about the cap, which the gate legs read as a delivery; the driver now names each in out.timeouts with its
        phase and in the phase's seen.expired. The driver records quiet()'s give-ups separately and they are not fatal."""
        self._driver_ran()
        self.assertEqual(self.result.get("timeouts"), [], "every wait the driver placed was met; the expired ones: %r (quiet gave up: %r)"
                         % (self.result.get("timeouts"), self.result.get("quietGaveUp")))

    def _assert_seen(self, seen, want_cards, todo=None, prompt=None, what="", waited=False):
        """The visibles a read found. With `waited` the record is one waitVisible produced (a phase's seen, D's seenAfterReturn)
        and its expired list must be present and empty: the driver names there each visibility wait that ran to its cap (round
        5), and a missing list is refused rather than read as empty, since an older driver's record cannot establish the
        outcome. Scoped to the waited reads (round 4, tests-1: phase D's after-return read was the one waitVisible record no
        reader checked, so a wait that expired with the read catching the cards and nothing in out.timeouts passed every test);
        a visible() record (seenWhileDown, seenA, seenB, seenD) records no wait and carries no such list."""
        if waited:
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
        one, a second after the Waiting page's restart whole frame (round 2's review, finding 1)."""
        if f["t"] == "feedDelta":
            return f.get("asks") is not None
        if f["t"] == "delta" and f["slot"] == "feed":
            return "asks" in (f.get("coll") or [])
        return False

    def _attaches_since(self, since_ms):
        """One (rev, floored second) per card-less feed slot patch (the connect push's ledgers attach, _carries_cards) the Outline
        received from `since_ms` to phase B's first change, in order, read over the drive's record and not a window's: the
        kernel floors a row's stamp to the second, so the row the old bundle files for an attach can sit inside a window whose
        patch pad the attach itself is past by tens of milliseconds (round 2, regression-3: a 40 ms gap on a recorded drive).
        Every reader of an attach matches rows to it through _minus_attach_rows (the two down-window sites since round 4, the
        return window since that round's fixer pass, when its own set of revs went); no reader keeps a set of revs."""
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
        drive). A multiset difference matched to the ATTACH, not a set of revs (round 4): the Outline's feed patch revs
        restart at 1 on every relay socket, so a rev is no identity over a drive, and a set of revs let every row of a
        colliding rev through where the assertions' messages promise one row per attach. The exemption fires on no recorded
        drive: over the 65 unmutated records of both classes in the builder's cache as of the drive at
        `r6-margin/lab-head5.log` (2026-09-20; `python3 population6.py old|new | xargs python3 attach_census.py <tests_dir>`,
        these helpers over each record, outside the repo) the down windows hold 0 rows and 0 attaches, so 0 rows are exempted
        at either site, by the set before round 4 and by this match after it; the pin over a synthetic record in
        tests/test_federated_linkdrop_driver_bound.py is where it is exercised. Returns the rows' data, _outline_unapplied's shape."""
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
        tests/test_federated_linkdrop_driver_bound.py reads (round 4's fixer pass: the leg's inline since was reached by no test,
        and a mutation moving it to the resume stayed green while the helpers were pinned at both values)."""
        return self._minus_attach_rows(self._outline_unapplied_stamped(self._rows_in("drop", "resume")), self._marks()["resume"] - 1500)

    def _return_window_stray(self):
        """The rows filed between the link's return and phase B's first change beyond one per ledgers attach the Outline received
        there: the outline/delta-unapplied rows stamped in [resume - 1.5 s, B0 - 1 s] (padded on the left as _rows_in pads, the
        kernel's whole-second floor; closed a second before B0, since phase B's first row is stamped at a floor no earlier than
        B0 - 1 s, B0 being marked before the change is posted) less one row per attach from 1.5 s before the resume, matched to
        the attach as the down window's are (_minus_attach_rows). Round 4's fixer pass: this reader kept a set of revs after the
        two down-window sites moved to the match, so two rows of one attach's rev both passed a filter whose message promised one
        per attach (over the 65 recorded records of both classes the window holds 0 rows and 0 attaches, so the switch moves no
        recorded verdict; the census is in _minus_attach_rows's docstring). Returns (the stray rows' data, the attaches)."""
        m = self._marks()
        t0, t1 = m["resume"] / 1000.0 - 1.5, m["B0"] / 1000.0 - 1.0
        stamped = self._outline_unapplied_stamped([r for r in self.hub_diag_rows if t0 <= float(r.get("t") or 0) <= t1])
        return self._minus_attach_rows(stamped, m["resume"] - 1500), self._attaches_since(m["resume"] - 1500)

    def _link_up_phases(self):
        return ("A", "B", "C") if self.local_drop else ("A", "B")

    def _assert_the_down_window_outlasts_the_drives_slowest_delivery(self):
        """The gate's control in TIME (round 2's ruling): the while-down read of phase D came at least DOWN_WINDOW_MARGIN times
        this drive's own slowest link-up delivery after D's post ended. A phase's delivery is the driver's seen.waitedMs, from
        the change's post returning to the last of its visibles on the pages (waited for concurrently), taken over EVERY
        link-up phase (A, B and C with the local drop; which is slowest moves from drive to drive with the churn's timing against
        the notices, so no one phase stands for the rest), so the yardstick is this drive's
        and this bundle's: on the old bundle a change shows only at the next churned socket's whole frame, 6 to 19 s. Without
        this pin the two temporal pins hold for a post at the END of the dwell (an 18 ms window, both round-2 voters), and
        "absent while down" cannot be told from "no time passed". The span is read to `settled`, the mark the while-down read
        follows (resume is some 20 ms later). A phase's waitedMs is a delivery only when every wait behind it RESOLVED: a
        wait that ran to its cap leaves waitedMs at about wait_ms with the visible absent, and taking that as the yardstick
        makes this pin `dwell >= DOWN_WINDOW_MARGIN x cap`, true by the relation pin's arithmetic and saying nothing about the
        drive (round 5: the driver swallowed those timeouts and the leg passed at 42 >= 40). So every phase read here must
        record an empty seen.expired (the driver's per-wait outcomes; a record with none cannot establish them and is
        refused) and show the phase's visibles on every page, both classes, before its waitedMs is taken; a resolved wait
        ended before its cap, so a delivery at the cap is then impossible by construction and DOWN_READ_ROOM_MS covers the
        reads alone. On the old-hub class this is also where phase A's visibles are asserted, which no test did before.
        Returns (span_s, deliveries) for the record."""
        m = self._marks()
        made = [c for c in self.changes_made if c.get("phase") == "D"]
        self.assertEqual(len(made), 1, "the control door made phase D's change bundle once: %r" % ([c.get("phase") for c in self.changes_made],))
        todo = ("todo" in self.changes) or None
        for p in self._link_up_phases():
            rec = self._phase(p)
            seen = rec.get("seen") or {}
            self.assertEqual(seen.get("expired"), [], "phase %s's visibility waits all resolved before their cap (the driver records each wait that expired in "
                                                      "seen.expired; a wait that ran to its cap is not a delivery, and a record with no expired list cannot say which "
                                                      "it was), so its waitedMs is a delivery the down window can be measured against: %r" % (p, seen))
            self._assert_seen(seen, True, todo=todo, prompt=((rec.get("change") or {}).get("prompt") if "append" in self.changes else None),
                              what="phase %s's changes on every page (the delivery the down window is measured against)" % p, waited=True)
        deliveries = {p: (self._phase(p).get("seen") or {}).get("waitedMs") for p in self._link_up_phases()}
        self.assertTrue(deliveries and all(isinstance(v, int) and not isinstance(v, bool) and v >= 0 for v in deliveries.values()),
                        "every link-up phase recorded its delivery (seen.waitedMs): %r" % (deliveries,))
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
        """The gate, established rather than exhibited (round 1): phase D's change bundle was posted to the remote's real
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
                                   "ledgers attach the Outline received after the resume is the return's, in this window's right pad by the kernel's whole-second "
                                   "floor: it names the feed slot, carries the attach's rev and is stamped at or after the attach's floored second): %r" % (down,))
        self._assert_seen(D["seenAfterReturn"], True, todo=todo, prompt=prompt, what="phase D after the link's return (the redial's whole frame carried it)", waited=True)
        for app in self.apps:
            window = [(s, f) for s in self._relay_socks(app) for f in s["frames"] if m["resume"] <= f["at"] < m["B0"]]
            carrying = [(s["i"], f["t"], f["slot"], f.get("asks") if f["t"] == "feedDelta" else f.get("coll"), round((f["at"] - m["resume"]) / 1000.0, 2))
                        for s, f in window if self._carries_cards(f)]
            self.assertEqual(carrying, [], "no patch carrying a card reached the %s page between the link's return and phase B's first change (the "
                                           "catch-up is one whole frame, never a replayed patch; a ledgers attach after the whole frame carries no card): %r" % (app, carrying))
            wholes = [f for s, f in window if f["t"] == "feed"]
            self.assertTrue(wholes, "…and a whole feed frame did reach the %s page in that window: %r" % (app, [self._kinds(s) for s in self._relay_socks(app, "resume", "B0")]))
        # the rows, read over the return window itself (round 2's review, finding 2; the down window's zero above ends 1.5 s
        # after resume and reaches none of the return's whole frames, which arrive 1 to 5 s after it): no outline/
        # delta-unapplied row for the return's whole frame or for a replayed patch (_return_window_stray: the window's bounds,
        # and the one row allowed per ledgers attach the Outline received there, matched to the attach as the down window's are)
        stray, attaches = self._return_window_stray()
        self.assertEqual(stray, [], "no outline/delta-unapplied row filed between the link's return and phase B's first change beyond one per ledgers attach the "
                                    "Outline received there (a row here is a row for the return's whole frame or for a replayed patch; the attach's row names the feed "
                                    "slot, carries its rev and is stamped at or after its floored second): stray %r, attaches (rev, floored second) %r" % (stray, attaches))
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

    The delta-unapplied rows are the old bundle's storm. This lab reads it across the mid-session events: it is one
    row PER remote feed patch, it STOPS while the link is down (no patch arrives, so no row: the storm is gated on the
    link, established by phase D, a change due while the link was down that reached no page, crossed as no frame and
    filed no row until the return's whole frame carried it, the while-down read coming DOWN_WINDOW_MARGIN times this
    drive's slowest link-up delivery after the post, so the old bundle's own 6 to 19 s catch-up latency cannot pass for
    the gate), and it RESUMES after each redial's whole frame (the whole
    frame catches the page up once; the next patch freezes again). The class pins the correspondence, not a count: per
    window and over the whole drive, the rows equal the Outline's own feed slot patches by rev, non-empty in every
    phase unless a notice post found the Outline without an open, served relay socket and a whole keyed feed frame then
    caught it up inside the phase after the bundle's last notice could have been posted (the old bundle's socket churn
    absorbing the phase's notices: no patch, so no row; the allowance is keyed on that gap and that frame,
    _outline_caught_up_whole) and empty while the link was down. One drive's count on the bundle at 01d4fbe43 (2026-09-19, the round-2
    head): 3 / 0 / 3 / 3 across phase A, the link down, phase B and phase C; a reviewer's drive at round 1's head gave
    3 / 0 / 1 / 3 when socket churn inside phase B absorbed two notices into whole frames (the module docstring gives
    the recorded population). A relay redial does not end the storm but restarts it, so with a link that comes and goes
    the storm looks intermittent and self-healing when it is neither; this class keeps that evidence beside the new
    bundle's zero. The catch-up half IS asserted on the old feed
    page: phase B's cards show after the link's return redial and still show after the local restart's, phase C's show
    after that redial, and phase D's (posted while the link was down) show after the return, so a redial's whole frame
    catches the old page up and the next patch freezes it again. The steady-state freeze itself (a card that never
    shows while one socket holds) is the corners lab's job; the storm (the rows) is this lab's observable, and the new
    bundle (LinkDropBothNew) files ZERO of them across the same drive. The redial helper runs with exactly=False for
    the old bundle's socket churn."""
    changes = ("notice",)
    caps = False               # the old bundle dials no caps (read from the dial URL)

    # What a skip of this class leaves unexecuted, and what still runs in the same CI job: the skip reasons carry it, so a
    # runner reading "skipped" knows which claim went untested (round 1, tests-4).
    UNEXECUTED = ("the old bundle's storm evidence (one delta-unapplied row per feed slot patch the Outline received, none "
                  "with a change due while the link was down, restarted by each redial's whole frame) goes unexecuted; the "
                  "mechanisms PR 815 fixed are pinned in the same CI job by ui/webview/federation-remote-view-delta.test.ts, "
                  "federation-remote-feed-delta.test.ts and federation-reconnect.test.ts (npm test), and LinkDropBothNew "
                  "drives the link drop and the hub restart against this checkout")

    @classmethod
    def _knobs(cls):
        super()._knobs()
        if (os.environ.get("ROMP_LINKDROP_LAB") or "").strip() != "1":
            raise unittest.SkipTest("optional: ROMP_LINKDROP_LAB unset: the old-hub class waits out the hub's supervisor twice and restarts its "
                                    "hub kernel against a pre-815 bundle (about two minutes, the mint and its build included), so %s; set it to 1 "
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

    def test_the_link_dropped_and_the_pages_stopped_dialing_while_the_row_was_down(self):
        self._assert_link_dropped_and_the_row_went_down()

    def test_dials_carry_no_caps_and_the_redial_is_served_whole(self):
        for app in self.apps:
            self._assert_dial_terms(self._relay_socks(app)[0]["url"], app, caps=False, redial=False)
        # the old bundle churns its remote socket, so the return's redial is one of several sockets in the window; the
        # FIRST that opened was served a whole keyed feed (the whole-frame road the old page depends on)
        self._assert_redialed_once_and_served_whole("resume", "restart" if self.local_drop else "end", caps=False, exactly=False)
        if self.local_drop:
            # …and the local restart's redial the same: the first socket that opened between the restart and phase C's
            # first change was served whole (round 1, fresh-3: a partial return in that window went unread)
            self._assert_redialed_once_and_served_whole("restart", "C0", caps=False, exactly=False)

    def test_every_wait_the_driver_placed_was_met(self):
        self._assert_every_wait_was_met()

    def test_the_old_bundle_drops_every_remote_patch_and_asks_the_local_kernel(self):
        """The freeze signature the corners lab pins, read here in phase A (steady, link up): one outline/delta-unapplied
        row per remote feed patch, a needSlot to the LOCAL kernel (which cannot repair a remote slot), and nothing asked
        of the remote (the old bundle has no per-conn receiver and no host to route by)."""
        self._control()
        A = self._rows_in("A0", "A1")
        ua = self._outline_unapplied(A)
        self.assertTrue(len(ua) >= 1 or self._outline_caught_up_whole("A0", "A1"),
                        "the old Outline filed a delta-unapplied row for the remote feed patches in phase A, or a notice post found it without an open, "
                        "served relay socket and a whole keyed feed frame caught it up there after the bundle's last notice could have been posted (the "
                        "old bundle's socket churn absorbing the notices; a frame before that, the ready-time frame included, does not count, nor does "
                        "one while every post found an open, served socket); rows by kind: %r"
                        % (self._rows_by_kind(A),))
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
        """The catch-up half of the headline, asserted (round 1, extra7-3): the whole frame each redial is served shows the
        old feed page the cards, so the old page freezes on patches and is caught up by whole frames, not frozen for
        good. Phase B's own cards after the link's return redial, still there after the local restart's redial, and
        phase C's after that one (phase A's would have rendered before the drop, so they say nothing about a redial)."""
        self._assert_seen(self._phase("B")["seen"], True, what="phase B's cards on the old feed page after the link's return redial", waited=True)
        if self.local_drop:
            C = self._phase("C")
            self._assert_seen(C["seenB"], True, what="phase B's cards still shown after the local restart's redial")
            self._assert_seen(C["seen"], True, what="phase C's cards after the local restart's redial", waited=True)

    def test_every_relay_socket_that_opened_was_served_whole_first(self):
        """The old bundle churns its remote socket every few seconds; every socket that opened, churned or lab-caused, was
        served a whole keyed feed first."""
        self._assert_every_opened_relay_socket_was_served_whole_first()

    def test_a_change_due_while_the_link_was_down_crossed_nothing_and_the_return_carried_it_whole(self):
        """The gate's own leg on the old bundle: phase D's cards, posted with the row down, reach no page and file no row
        while the link is down, read DOWN_WINDOW_MARGIN times this drive's slowest link-up delivery after the post (the old
        bundle shows a change only at the next churned socket's whole frame, 6 to 19 s, so a shorter read would be the
        page's latency, not the gate); the return's whole frame carries them (visible after the return, no patch carrying a
        card and no row for one between the return and phase B's first change; a ledgers attach and the row this bundle
        files for it are allowed), and phase B's patches then file rows again (the storm test's phase B equality). A
        pause in the storm with a change due is the link, not the page."""
        self._assert_change_due_while_down_crossed_nothing_and_the_return_carried_it_whole()


if __name__ == "__main__":
    unittest.main()
