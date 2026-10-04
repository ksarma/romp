#!/usr/bin/env python3
"""The Log writes "Kernel connection lost" when a reconnect FAILS, never at the drop (iOS item 4b, 2026-10-03).

Every return to the app logged the entry for the chat and the Feed, with an unread digit on the Log control, although the
sockets came back at once: the shell's Log wrote it at each pane's up-to-down transition, and a return always makes one (the
shim puts a stale socket down before it redials; a thawed page receives the FIN of a socket the OS dropped). The entry now
waits in the Log's `lost` until the event that says the reconnect failed, a dial that closed without ever opening, and a
socket that reopens first drops it unwritten. A close the connect cut made (a timer) fails nothing while another socket of the
page is open (the review of item 4b, 2026-10-03: on a slow network the dials a return makes together wait in line for their
handshakes, and the last of them reached the cut while every handshake was succeeding), and a close the page's own unload made
fails nothing (review round 1, 2026-10-04: Firefox delivers those closes to the unloading page). Five pieces, each executed
here under node against the code as served:

  ShimFailureWord        kernel/kernel.py _shim: a dial that never opened posts {romp:'wsFail',app,cut} to the shell after
                         its down word, cut true when the watchdog's CONNECTING arm closed it and false for a refusal (at
                         the bound's edge: a close at 15000 ms is a refusal, at 15001 ms a cut); an opened socket's close,
                         the return's abandon() and a park post none. Through tests/test_pane_shim_return.py's harness.
  ShellLinkFailure       _LANDING_MOBILE_JS: the shell socket's close of a dial that never opened (refused, or its own
                         connect cut) calls window.__rompLinkFailed once, with true when its own cut timer or the tick's
                         backstop made the close (a close the browser made reads the clock: at 14999 ms a refusal, at
                         15000 ms a cut); an opened socket's close, the return's abandon and a superseded socket's late
                         close call nothing. Each dial and each open calls window.__rompNotLeaving (the Log's leaving
                         latch, below). Through tests/test_kernel_mobile.py's probe harness.
  LogWaitsForTheFailure  _LANDING_ERRS_JS: a drop alone writes nothing (the live red cue shows it); a failure word, or the
                         link's failure for every waiting pane, writes one entry per drop, and one pane's word that pane's
                         entry alone; an up drops the waiting entry; a pane not shown keeps waiting and is written once
                         shown; a parked pane, or a closed column, is dropped; a split column waits under its own key.
                         Through tests/test_error_center.py's DOM stub.
  ACutFailsNothingWhileASocketStands
                         _LANDING_ERRS_JS: a cut word, or the link's failure with true, writes nothing while the shell's link,
                         another pane's socket (a pane not shown included) or a column's stands; a refusal writes whatever
                         stands; with nothing open (a parked pane holds no socket) the cut writes. The same DOM stub.
  AnUnloadsClosesFailNothing
                         _LANDING_ERRS_JS: from a beforeunload, neither the link's failure nor a failure word writes; the
                         shell's next dial or open (window.__rompNotLeaving), a pane's or a column's open, and pageshow each
                         clear the latch, so a navigation that did not unload hides no later outage. The same DOM stub.

The composition in real engines (phone and desktop, healthy, slow and failing returns; reloads while a dial is connecting, and a
204 followed by an outage) is tests/test_conn_lost_log_served.py.
Synthetic only: no network, no real DOM, no real session data.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, HERE)
# Hermetic state before the imports below, each of which loads the kernel source at import: the state floor here, and the
# kernel's own switches (ROMP_KERNEL_NO_OPEN, ROMP_SERVE_TOKEN) are those modules' own writes, made before their loads.
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)
import test_error_center as _errc          # noqa: E402  the modules, not their classes: an imported TestCase would be collected twice
import test_kernel_mobile as _mob          # noqa: E402
import test_pane_shim_return as _shimret   # noqa: E402


# ---- the shim's failure word ----
WORDS = r"""function words(){return parentPosts.filter(function(p){return p.romp==="wsState"||p.romp==="wsFail";}).map(function(p){return p.romp==="wsFail"?(p.cut===true?"fail-cut":p.cut===false?"fail":"fail-unmarked"):p.state;});}
"""


class ShimFailureWord(unittest.TestCase):
    def test_a_refused_dial_posts_its_down_word_then_the_failure_word(self):
        r = _shimret._run(WORDS + r"""
sock().readyState=3;sock().onclose({code:1006,reason:"",wasClean:false});   // the boot dial never opened: refused
out({words:words(),app:parentPosts.filter(function(p){return p.romp==="wsFail";}).map(function(p){return p.app;})});""", app="feed")
        self.assertEqual(r["words"], ["down", "fail"], "the down word first (the shell's state), then the failure the Log waits for, "
                         "marked not cut: a refusal inside the connect bound")
        self.assertEqual(r["app"], ["feed"], "the word names the pane")

    def test_an_opened_socket_closing_and_the_returns_abandon_post_no_failure_word(self):
        r = _shimret._run(WORDS + r"""
open();recv({type:"ka"});sock().readyState=3;sock().onclose({code:1006,reason:"",wasClean:false});var afterClose=words();
var t=timers.filter(function(x){return x.live&&x.fn.name==="connect";});t.forEach(function(x){x.live=false;x.fn();});open();recv({type:"ka"});
hide();NOW+=46000;show();var afterReturn=words();   // the return's fast path puts the quiet socket down (abandon) and dials at once
open();var afterReopen=words();
out({afterClose:afterClose,afterReturn:afterReturn,afterReopen:afterReopen,dials:sockets.length});""")
        self.assertEqual(r["afterClose"], ["up", "down"], "an opened socket's close is a drop, not a failed reconnect")
        self.assertEqual(r["afterReturn"], ["up", "down", "up", "down"], "the return's put-down is a drop, not a failed reconnect")
        self.assertEqual(r["afterReopen"], ["up", "down", "up", "down", "up"], "the redial opened: no failure word anywhere")
        self.assertEqual(r["dials"], 3)

    def test_a_dial_cut_by_the_watchdog_posts_the_failure_word_when_its_close_lands(self):
        r = _shimret._run(WORDS + r"""
open();recv({type:"ka"});sock().readyState=3;sock().onclose({code:1006,reason:"",wasClean:false});
var t=timers.filter(function(x){return x.live&&x.fn.name==="connect";});t.forEach(function(x){x.live=false;x.fn();});   // the redial: CONNECTING, and the path hangs
var hung=sock();NOW+=16000;tick();var cut=hung.readyState;var beforeClose=words();   // past 15 s the watchdog closes it
hung.onclose({code:1006,reason:"",wasClean:false});   // the browser's close event for the cut dial
out({cut:cut,beforeClose:beforeClose,afterClose:words()});""")
        self.assertEqual(r["cut"], 3, "the watchdog's CONNECTING arm closed the hung dial")
        self.assertEqual(r["beforeClose"], ["up", "down"])
        self.assertEqual(r["afterClose"], ["up", "down", "down", "fail-cut"],
                         "the cut dial never opened: its close is the failure, marked cut (the Log does not count it while another socket stands)")

    def test_a_refusal_after_a_long_quiet_is_not_marked_cut(self):
        # the mark reads the dial's own age at its close, not the page's: a dial made long after the last open and refused at once
        r = _shimret._run(WORDS + r"""
open();recv({type:"ka"});NOW+=60000;sock().readyState=3;sock().onclose({code:1006,reason:"",wasClean:false});   // an opened socket's close, a minute in
var t=timers.filter(function(x){return x.live&&x.fn.name==="connect";});t.forEach(function(x){x.live=false;x.fn();});
NOW+=40;sock().readyState=3;sock().onclose({code:1006,reason:"",wasClean:false});   // the redial refused 40 ms after it was made
out({words:words()});""")
        self.assertEqual(r["words"], ["up", "down", "down", "fail"], "a refused redial is a failure the Log counts whatever stands")

    def test_the_cut_mark_at_the_bounds_edge(self):
        # review round 1 of item 4b (2026-10-04, tests-3): the mark is the watchdog arm's own test, a strict > 15000 on the dial's
        # age; a browser's close of the redial at exactly 15000 ms is a refusal and at 15001 ms a cut (no tick runs here)
        got = {}
        for ms in (15000, 15001):
            r = _shimret._run(WORDS + r"""
open();recv({type:"ka"});sock().readyState=3;sock().onclose({code:1006,reason:"",wasClean:false});
var t=timers.filter(function(x){return x.live&&x.fn.name==="connect";});t.forEach(function(x){x.live=false;x.fn();});   // the redial, made now
NOW+=%d;sock().readyState=3;sock().onclose({code:1006,reason:"",wasClean:false});   // the browser closes it, never opened
out({words:words()});""" % ms)
            got[ms] = r["words"]
        self.assertEqual(got[15000], ["up", "down", "down", "fail"], "at exactly 15 s the close is a refusal")
        self.assertEqual(got[15001], ["up", "down", "down", "fail-cut"], "past 15 s it is a cut")

    def test_a_park_posts_no_failure_word(self):
        r = _shimret._run(WORDS + r"""
open();recv({type:"ka"});park();out({words:words()});""")
        self.assertEqual(r["words"], ["up", "parked"], "a park is its own state, never a failure")


# ---- the shell link's failure ----
LINKFAIL = r"""var LF=0,LFC=[];window.__rompLinkFailed=function(c){LF++;LFC.push(c===true?"cut":c===false?"refused":"unmarked");};
"""


class ShellLinkFailure(unittest.TestCase):
    def test_a_refused_dial_calls_the_link_failure_and_an_opened_sockets_close_does_not(self):
        r = _mob._run_probe(LINKFAIL + r"""
shRefuseNow();var afterRefusal=LF;           // the boot dial refused
shFireDials();shOpen();shRecv({type:'ka'});var s=shSock();s.readyState=3;s.onclose({code:1006});var afterOpenedClose=LF;
shOut({afterRefusal:afterRefusal,afterOpenedClose:afterOpenedClose,how:LFC});""")
        self.assertEqual(r["afterRefusal"], 1, "a dial that never opened: the link failed to come back")
        self.assertEqual(r["how"], ["refused"], "a refusal is marked as one: the Log counts it whatever stands")
        self.assertEqual(r["afterOpenedClose"], 1, "an opened socket's close is a drop, not a failure")

    def test_the_returns_abandon_calls_nothing_and_its_redials_connect_cut_does(self):
        r = _mob._run_probe(LINKFAIL + r"""
shOpen();shRecv({type:'ka'});shHide();SHSOCKS[0].readyState=3;SHNOW+=100;shShow();var afterReturn=LF;   // abandon the dead socket, dial at once
var hung=shSock();shRunDue(SHNOW+15000);var cut=hung.readyState;var beforeClose=LF;   // the path hangs: the dial's own cut closes it at SH_CONNECT_MS
hung.onclose({code:1006});
shOut({afterReturn:afterReturn,cut:cut,beforeClose:beforeClose,afterClose:LF,how:LFC});""")
        self.assertEqual(r["afterReturn"], 0, "the return's put-down of a stale socket is no failure")
        self.assertEqual(r["cut"], 3, "the dial's own cut closed it")
        self.assertEqual(r["beforeClose"], 0)
        self.assertEqual(r["afterClose"], 1, "the cut dial never opened: its close is the failure")
        self.assertEqual(r["how"], ["cut"], "marked cut (shCutHere): the Log does not count it while a pane's socket stands")

    def test_a_cut_timer_that_fires_a_ms_short_of_the_bound_is_marked_cut_by_its_own_flag(self):
        # a timer can fire while the wall clock still reads a ms short of SH_CONNECT_MS (iOS item 1a's shCutHere): the mark reads
        # the cut's own flag, not the clock alone, or this close would count as a refusal whatever stands
        r = _mob._run_probe(LINKFAIL + r"""
shOpen();shRecv({type:'ka'});shHide();SHSOCKS[0].readyState=3;SHNOW+=100;shShow();
var hung=shSock();var own=SHTIMERS.filter(function(t){return t.live&&t.fn.name==='shCut';});
SHNOW+=14999;own.forEach(function(t){t.live=false;t.fn();});var cut=hung.readyState;   // the dial's own cut, early by the clock
hung.onclose({code:1006});
shOut({own:own.length,cut:cut,how:LFC});""")
        self.assertEqual(r["own"], 1)
        self.assertEqual(r["cut"], 3, "the dial's own cut timer closed it")
        self.assertEqual(r["how"], ["cut"], "marked cut by shCutHere although the clock reads 14999 ms")

    def test_the_links_cut_mark_at_the_bounds_edge(self):
        # review round 1 of item 4b (2026-10-04, tests-3): a browser's close of a dial the cut timer has not closed reads the clock,
        # the ladder's complement of a refusal: at SH_CONNECT_MS - 1 a refusal, at SH_CONNECT_MS a cut
        got = {}
        for ms in (14999, 15000):
            r = _mob._run_probe(LINKFAIL + r"""
shOpen();shRecv({type:'ka'});shHide();SHSOCKS[0].readyState=3;SHNOW+=100;shShow();   // the return dials at once
var d=shSock();SHNOW+=%d;d.readyState=3;d.onclose({code:1006});   // the browser's close; the dial's own cut timer has not run
shOut({how:LFC});""" % ms)
            got[ms] = r["how"]
        self.assertEqual(got[14999], ["refused"], "a ms under the bound the close is a refusal")
        self.assertEqual(got[15000], ["cut"], "at the bound it is a cut")

    def test_the_watchdogs_backstop_cut_is_marked_cut_too(self):
        r = _mob._run_probe(LINKFAIL + r"""
shOpen();shRecv({type:'ka'});shHide();SHSOCKS[0].readyState=3;SHNOW+=100;shShow();   // the return dials at once
var hung=shSock();var own=SHTIMERS.filter(function(t){return t.live&&t.fn.name==='shCut';});own.forEach(function(t){t.live=false;});   // the dial's own cut timer is lost
SHNOW+=15001;shTick();var cut=hung.readyState;   // the tick's CONNECTING arm closes it past SH_CONNECT_MS
hung.onclose({code:1006});
shOut({own:own.length,cut:cut,how:LFC});""")
        self.assertEqual(r["own"], 1, "the dial armed its own cut, which this case loses")
        self.assertEqual(r["cut"], 3, "the backstop closed the hung dial")
        self.assertEqual(r["how"], ["cut"], "a close the backstop made past SH_CONNECT_MS is a cut, the ladder's complement of a refusal")

    def test_each_dial_and_each_open_of_the_link_clears_the_logs_leaving_latch(self):
        # review round 1 of item 4b (2026-10-04): the shell's next dial and its open are two of the events that clear the Log's
        # leaving latch (a beforeunload that did not unload): the shell calls window.__rompNotLeaving at both
        r = _mob._run_probe(r"""
var NL=[];window.__rompNotLeaving=function(){var s=shSock();NL.push(SHSOCKS.length+':'+(s?s.readyState:-1));};
shOpen();var afterOpen=NL.slice();          // the boot dial opens
shRecv({type:'ka'});var s=shSock();s.readyState=3;s.onclose({code:1006});var afterClose=NL.slice();
shFireDials();                               // its redial
shOut({afterOpen:afterOpen,afterClose:afterClose,afterRedial:NL});""")
        self.assertEqual(r["afterOpen"], ["1:1"], "the open of the boot dial calls it, its socket OPEN")
        self.assertEqual(r["afterClose"], ["1:1"], "a close calls nothing")
        self.assertEqual(r["afterRedial"], ["1:1", "2:0"], "the redial calls it, its new socket CONNECTING")

    def test_a_superseded_sockets_late_close_calls_nothing(self):
        r = _mob._run_probe(LINKFAIL + r"""
var a=shSock();a.readyState=3;              // the boot dial closed; its close event is still queued
SHNOW+=9000;shTick();var dialed=SHSOCKS.length;   // the watchdog's CLOSED arm dials past SH_REDIAL_MS
a.onclose({code:1006});                     // the old socket's close lands after the newer dial
shOut({dialed:dialed,lf:LF});""")
        self.assertEqual(r["dialed"], 2, "the CLOSED arm dialed a newer socket")
        self.assertEqual(r["lf"], 0, "a close delivered after a newer dial fails nothing (the superseded-close return comes first)")


# ---- the Log waits for the failure ----
LOG_DRIVER = r"""
const out = {};
const realNotify = window.__rompNotify, CONN = [];
window.__rompNotify = function (kind, text) { if (kind === 'conn') CONN.push(String(text)); return realNotify.apply(this, arguments); };
window.__rompColOf = (src) => (src && src.col) || '';   // the shell's column lookup by the sender frame, stubbed
function postFrom(src, data) { (WL['message'] || []).forEach((f) => f({ data: data, source: src })); }
// the shell socket's call, read through a guard so a Log without the hook (the fork's main before this change) still runs every step
// and is read by the steps' own assertions; out.hook says whether the hook was there
function linkFailed() { out.hook = typeof window.__rompLinkFailed === 'function'; if (out.hook) window.__rompLinkFailed(); }
const snap = () => ({ texts: notes().map((n) => n.text), unread: notes().filter((n) => !n.seen).length, ns: notes().map((n) => n.n),
  conn: CONN.length, red: EL['merr']._cls.has('has'), num: EL['merr']._num.textContent });
post({ romp: 'wsState', app: 'chat', state: 'down' });
out.drop = snap();                                         // a drop alone
post({ romp: 'wsState', app: 'chat', state: 'up' });
out.back = snap();                                         // it reopened: nothing to write
post({ romp: 'wsState', app: 'chat', state: 'down' });
post({ romp: 'wsFail', app: 'chat' });
out.failed = snap();                                       // its reconnect failed
post({ romp: 'wsState', app: 'chat', state: 'down' });
post({ romp: 'wsFail', app: 'chat' });
out.failedAgain = snap();                                  // the same outage fails again: one entry
post({ romp: 'wsState', app: 'chat', state: 'up' });
out.recovered = snap();
EL['rerr-clear'].fire('click');
post({ romp: 'wsState', app: 'chat', state: 'down' });
post({ romp: 'wsState', app: 'feed', state: 'down' });
post({ romp: 'wsState', app: 'waiting', state: 'down' }); // not shown (no po-waiting class)
linkFailed();
out.link = snap();                                         // the shell's link failed: every waiting shown pane
BODY.add('po-waiting');
linkFailed();
out.shownLater = snap();                                   // the Waiting pane is shown now and still down: written at the next failure
post({ romp: 'wsState', app: 'timeline', state: 'down' });
post({ romp: 'wsState', app: 'timeline', state: 'parked' });
linkFailed();
out.parked = snap();                                       // a drop that became a park is dropped
post({ romp: 'wsState', app: 'timeline', state: 'down' });
post({ romp: 'wsFail', app: 'timeline' });
out.afterPark = snap();                                    // its later drop is a drop like any other
post({ romp: 'wsFail', app: 'files' });
out.noDrop = snap();                                       // a failure word for a pane that never dropped
post({ romp: 'wsState', app: 'feed', state: 'up' });
post({ romp: 'wsState', app: 'feed', state: 'down' });
post({ romp: 'wsState', app: 'feed', state: 'up' });
post({ romp: 'wsFail', app: 'feed' });
out.lateWord = snap();                                     // a failure word after the socket reopened
EL['rerr-clear'].fire('click');
postFrom({ col: '2' }, { romp: 'wsState', app: 'chat', state: 'down' });
out.colDrop = snap();
postFrom({ col: '2' }, { romp: 'wsFail', app: 'chat' });
out.colFailed = snap();                                    // a split column waits and is written under its own key
postFrom({ col: '3' }, { romp: 'wsState', app: 'chat', state: 'down' });
postFrom({ col: '3' }, { romp: 'wsState', app: 'chat', state: 'up' });
linkFailed();
out.colBack = snap();                                      // a column that reopened has nothing waiting
// review round 1 of item 4b (2026-10-04), keyed by pane: one pane's failure word writes that pane's waiting entry alone. Both
// panes are put up first (the chat is still down from the link step, and a down over a down records nothing), and the steps
// read the new writes, since the store coalesces an entry by its text.
post({ romp: 'wsState', app: 'chat', state: 'up' });
post({ romp: 'wsState', app: 'feed', state: 'up' });
post({ romp: 'wsState', app: 'chat', state: 'down' });
post({ romp: 'wsState', app: 'feed', state: 'down' });
const k0 = CONN.length;
post({ romp: 'wsFail', app: 'chat', cut: false });
out.oneWord = CONN.slice(k0);                              // the chat's word, the Feed's drop waiting too
post({ romp: 'wsState', app: 'feed', state: 'up' });
linkFailed();
out.oneWordThenLink = CONN.slice(k0);                      // the Feed reopened before any failure of its own
postFrom({ col: '2' }, { romp: 'wsState', app: 'chat', state: 'up' });
post({ romp: 'wsState', app: 'timeline', state: 'up' });
postFrom({ col: '2' }, { romp: 'wsState', app: 'chat', state: 'down' });
post({ romp: 'wsState', app: 'timeline', state: 'down' });
const k1 = CONN.length;
postFrom({ col: '2' }, { romp: 'wsFail', app: 'chat', cut: false });
out.oneColumnsWord = CONN.slice(k1);                       // a column's word, the Sessions pane's drop waiting too
// a column closed while its drop waits takes the drop with it (window.__rompColGone): a later failure writes nothing for it
post({ romp: 'wsState', app: 'timeline', state: 'up' });  // the Sessions pane reopens first, so nothing else is waiting
postFrom({ col: '4' }, { romp: 'wsState', app: 'chat', state: 'down' });
window.__rompColGone('4');
const k2 = CONN.length;
linkFailed();
out.colGone = CONN.slice(k2);
console.log(JSON.stringify(out));
"""


class LogWaitsForTheFailure(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        script = _errc.HARNESS + _errc.km._LANDING_ERRS_JS + LOG_DRIVER
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
            f.write(script)
            path = f.name
        try:
            r = subprocess.run(["node", path], capture_output=True, text=True, timeout=30)
        finally:
            os.unlink(path)
        assert r.returncode == 0, "the Log's JS threw: " + r.stderr[:800]
        cls.out = json.loads(r.stdout.strip().splitlines()[-1])

    CHAT = "Kernel connection lost: Chat pane (reconnecting)"

    def test_the_shell_has_a_door_for_its_links_failure(self):
        self.assertIs(self.out["hook"], True, "window.__rompLinkFailed is the Log's: the shell socket's close calls it")

    def test_a_drop_alone_writes_nothing_and_the_live_cue_shows_it(self):
        self.assertEqual(self.out["drop"], {"texts": [], "unread": 0, "ns": [], "conn": 0, "red": True, "num": "!"},
                         "nothing written, no digit; the red cue rides the live state")
        self.assertEqual(self.out["back"], {"texts": [], "unread": 0, "ns": [], "conn": 0, "red": False, "num": "!"},
                         "the socket reopened before any failure: nothing was lost, nothing is written")

    def test_a_failed_reconnect_writes_one_unread_entry_per_drop(self):
        self.assertEqual(self.out["failed"], {"texts": [self.CHAT], "unread": 1, "ns": [1], "conn": 1, "red": True, "num": "1"})
        self.assertEqual(self.out["failedAgain"], {"texts": [self.CHAT], "unread": 1, "ns": [1], "conn": 1, "red": True, "num": "1"},
                         "further failures of the same outage write nothing more")
        self.assertEqual(self.out["recovered"], {"texts": [self.CHAT], "unread": 1, "ns": [1], "conn": 1, "red": True, "num": "1"},
                         "the entry stays unread once the socket is back")

    def test_the_links_failure_writes_every_waiting_shown_pane_and_a_pane_shown_later_once_it_fails_again(self):
        self.assertEqual(self.out["link"]["texts"], [self.CHAT, "Kernel connection lost: Feed pane (reconnecting)"],
                         "the chat and the Feed, both shown; the Waiting pane is not shown")
        self.assertEqual(self.out["link"]["conn"], 3)
        self.assertEqual(self.out["shownLater"]["texts"][-1], "Kernel connection lost: Waiting pane (reconnecting)",
                         "a drop on a pane not shown keeps waiting and is written at a failure once the pane is shown")
        self.assertEqual(self.out["shownLater"]["conn"], 4, "and the chat and the Feed, already written, are not written again")

    def test_a_parked_pane_is_dropped_and_its_later_drop_counts(self):
        self.assertEqual(self.out["parked"]["conn"], 4, "a drop that became a park is not written at the link's failure")
        self.assertEqual(self.out["afterPark"]["texts"][-1], "Kernel connection lost: Sessions pane (reconnecting)")
        self.assertEqual(self.out["afterPark"]["conn"], 5)

    def test_a_failure_word_with_nothing_waiting_writes_nothing(self):
        self.assertEqual(self.out["noDrop"]["conn"], 5, "a pane that never dropped")
        self.assertEqual(self.out["lateWord"]["conn"], 5, "a failure word after the socket reopened")

    def test_one_panes_failure_word_writes_that_panes_entry_alone(self):
        # review round 1 of item 4b (2026-10-04, tests-1): with two panes down, the chat's word writes the chat's entry and leaves
        # the Feed's waiting, which its own reopening then drops; a column's word likewise leaves the Sessions pane's waiting
        self.assertEqual(self.out["oneWord"], [self.CHAT], "the chat's failure word writes the chat's entry, not the Feed's")
        self.assertEqual(self.out["oneWordThenLink"], [self.CHAT], "the Feed reopened before a failure of its own: never written")
        self.assertEqual(self.out["oneColumnsWord"], ["Kernel connection lost: chat split 2 (reconnecting)"],
                         "a column's failure word writes the column's entry, not the Sessions pane's")

    def test_a_column_closed_while_its_drop_waits_takes_the_drop_with_it(self):
        # review round 1 of item 4b (2026-10-04, tests-2): the column is shown (po-chat), so only the discard keeps it unwritten
        self.assertEqual(self.out["colGone"], [], "a closed column's waiting drop is discarded, never written at a later failure")

    def test_a_split_column_waits_under_its_own_key(self):
        self.assertEqual(self.out["colDrop"]["conn"], 5, "the column's drop alone writes nothing")
        self.assertEqual(self.out["colFailed"]["texts"], ["Kernel connection lost: chat split 2 (reconnecting)"])
        self.assertEqual(self.out["colBack"]["texts"], ["Kernel connection lost: chat split 2 (reconnecting)"],
                         "a column that reopened before the link failed has nothing waiting")


# ---- a connect cut fails nothing while another socket of the page stands ----
CUT_DRIVER = r"""
const out = {};
const realNotify = window.__rompNotify, CONN = [];
window.__rompNotify = function (kind, text) { if (kind === 'conn') CONN.push(String(text)); return realNotify.apply(this, arguments); };
window.__rompColOf = (src) => (src && src.col) || '';
let LINK = false;
window.__rompLink = () => ({ up: LINK, connT: 0 });   // the shell's publication (_LANDING_MOBILE_JS), stubbed
function postFrom(src, data) { (WL['message'] || []).forEach((f) => f({ data: data, source: src })); }
const snap = () => ({ conn: CONN.slice() });
post({ romp: 'wsState', app: 'chat', state: 'up' });
post({ romp: 'wsState', app: 'feed', state: 'down' });
post({ romp: 'wsFail', app: 'feed', cut: true });
out.cutWhileAPaneStands = snap();                          // the Feed's dial waited in line behind the chat's and was cut
post({ romp: 'wsFail', app: 'feed', cut: false });
out.refusedWhileAPaneStands = snap();                      // a refusal fails whatever stands
post({ romp: 'wsState', app: 'chat', state: 'down' });
post({ romp: 'wsFail', app: 'chat', cut: true });
out.cutWithNothingOpen = snap();                           // nothing open: a hung outage's cut writes
post({ romp: 'wsState', app: 'waiting', state: 'up' });   // the one socket open is a pane's the page does not show (no po-waiting)
post({ romp: 'wsState', app: 'timeline', state: 'down' });
post({ romp: 'wsFail', app: 'timeline', cut: true });
window.__rompLinkFailed(true);
out.cutWhileOnlyAHiddenPaneStands = snap();                // the kernel is answering that socket: neither cut writes
post({ romp: 'wsState', app: 'waiting', state: 'parked' }); // and it goes, so the steps below read the page as before
post({ romp: 'wsState', app: 'timeline', state: 'down' });
LINK = true;
post({ romp: 'wsFail', app: 'timeline', cut: true });
out.cutWhileTheLinkStands = snap();                        // the shell's link is open: the kernel answers
LINK = false;
postFrom({ col: '2' }, { romp: 'wsState', app: 'chat', state: 'up' });
window.__rompLinkFailed(true);
out.linkCutWhileAColumnStands = snap();                    // the shell's own dial waited behind a column's and was cut
window.__rompLinkFailed(false);
out.linkRefusedWhileAColumnStands = snap();                // the shell's dial refused: every waiting shown drop is written
postFrom({ col: '2' }, { romp: 'wsState', app: 'chat', state: 'down' });
post({ romp: 'wsState', app: 'files', state: 'up' });
post({ romp: 'wsState', app: 'files', state: 'parked' });
post({ romp: 'wsState', app: 'feed', state: 'up' });
post({ romp: 'wsState', app: 'feed', state: 'down' });
window.__rompLinkFailed(true);
out.linkCutWithOnlyAParkedPane = snap();                   // a parked pane holds no socket: nothing stands, the cut writes
console.log(JSON.stringify(out));
"""


class ACutFailsNothingWhileASocketStands(unittest.TestCase):
    """The review of item 4b (2026-10-03): on a slow network the dials a return makes together wait in line, since Chromium and
    Firefox hold each WebSocket handshake to a host until the one ahead of it is done, and the page's own 15 s connect cut closed
    the last of them while every handshake was succeeding. A close that cut made (the shim's word marked cut, the shell's call
    with true) now fails nothing while a socket of the page is open: the shell's link, a pane's or a column's. A refusal fails
    whatever stands, and with nothing open the cut writes as before. Through tests/test_error_center.py's DOM stub."""

    @classmethod
    def setUpClass(cls):
        script = _errc.HARNESS + _errc.km._LANDING_ERRS_JS + CUT_DRIVER
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
            f.write(script)
            path = f.name
        try:
            r = subprocess.run(["node", path], capture_output=True, text=True, timeout=30)
        finally:
            os.unlink(path)
        assert r.returncode == 0, "the Log's JS threw: " + r.stderr[:800]
        cls.out = json.loads(r.stdout.strip().splitlines()[-1])

    FEED = "Kernel connection lost: Feed pane (reconnecting)"
    CHAT = "Kernel connection lost: Chat pane (reconnecting)"
    SESSIONS = "Kernel connection lost: Sessions pane (reconnecting)"
    SPLIT = "Kernel connection lost: chat split 2 (reconnecting)"

    def test_a_panes_cut_while_another_pane_stands_writes_nothing_and_a_refusal_writes(self):
        self.assertEqual(self.out["cutWhileAPaneStands"]["conn"], [], "the chat's socket is open: the Feed's cut dial was waiting its turn")
        self.assertEqual(self.out["refusedWhileAPaneStands"]["conn"], [self.FEED], "the same drop's refused dial is a failure")

    def test_a_cut_with_nothing_open_writes(self):
        self.assertEqual(self.out["cutWithNothingOpen"]["conn"], [self.FEED, self.CHAT], "no socket of the page is open: the cut is the failure")

    def test_a_socket_of_a_pane_not_shown_stands_too(self):
        # review round 1 of item 4b (2026-10-04, tests-4): on the desktop the Outline, Waiting and Files panes are hidden by
        # default and their sockets open at boot; the kernel answering one of them is what stands() asks
        self.assertEqual(self.out["cutWhileOnlyAHiddenPaneStands"]["conn"], [self.FEED, self.CHAT],
                         "the Sessions pane's cut word and the link's cut write nothing while a hidden pane's socket is open")

    def test_the_shells_link_counts_as_a_socket_that_stands(self):
        self.assertEqual(self.out["cutWhileTheLinkStands"]["conn"], [self.FEED, self.CHAT], "the Sessions pane's cut while the link stands writes nothing")

    def test_the_shells_own_cut_fails_nothing_while_a_column_stands_and_its_refusal_fails_every_waiting_drop(self):
        self.assertEqual(self.out["linkCutWhileAColumnStands"]["conn"], [self.FEED, self.CHAT], "a split column's open socket stands too")
        self.assertEqual(self.out["linkRefusedWhileAColumnStands"]["conn"], [self.FEED, self.CHAT, self.SESSIONS],
                         "the refusal writes the drop still waiting (the Sessions pane's), and nothing twice")

    def test_a_parked_pane_is_not_a_socket_that_stands(self):
        self.assertEqual(self.out["linkCutWithOnlyAParkedPane"]["conn"], [self.FEED, self.CHAT, self.SESSIONS, self.SPLIT, self.FEED],
                         "the column's and the Feed's new drops are written at the shell's cut: the parked Files pane holds no socket")


# ---- a close the page's own unload makes fails nothing (review round 1 of item 4b, 2026-10-04) ----
LEAVE_DRIVER = r"""
const out = {};
const realNotify = window.__rompNotify, CONN = [];
window.__rompNotify = function (kind, text) { if (kind === 'conn') CONN.push(String(text)); return realNotify.apply(this, arguments); };
window.__rompColOf = (src) => (src && src.col) || '';
function postFrom(src, data) { (WL['message'] || []).forEach((f) => f({ data: data, source: src })); }
function fire(k) { (WL[k] || []).forEach((f) => f({})); }
const snap = () => CONN.slice();
out.door = typeof window.__rompNotLeaving === 'function';
// the unload: beforeunload, then the closes Firefox delivers to the page before its pagehide
post({ romp: 'wsState', app: 'chat', state: 'down' });
post({ romp: 'wsState', app: 'feed', state: 'down' });
postFrom({ col: '2' }, { romp: 'wsState', app: 'chat', state: 'down' });
fire('beforeunload');
window.__rompLinkFailed(false);
out.linkWhileLeaving = snap();                             // the shell's dial that never opened, closed by the unload
post({ romp: 'wsFail', app: 'feed', cut: false });
postFrom({ col: '2' }, { romp: 'wsFail', app: 'chat', cut: false });
out.wordWhileLeaving = snap();                             // a pane's and a column's, the same
// clear 1: the shell's next dial (window.__rompNotLeaving, which the shell calls at each dial and at its open)
window.__rompNotLeaving();
post({ romp: 'wsFail', app: 'feed', cut: false });
out.afterTheShellsDial = snap();                           // the page stayed: the Feed's refused dial is a failure
// clear 2: a pane's socket open (its up word)
fire('beforeunload');
window.__rompLinkFailed(false);
out.leavingAgain = snap();
post({ romp: 'wsState', app: 'timeline', state: 'up' });
window.__rompLinkFailed(false);
out.afterAPanesOpen = snap();                              // the chat and the split column, still waiting, are written
// clear 3: a column's socket open
postFrom({ col: '3' }, { romp: 'wsState', app: 'chat', state: 'down' });
fire('beforeunload');
window.__rompLinkFailed(false);
out.leavingThird = snap();
postFrom({ col: '4' }, { romp: 'wsState', app: 'chat', state: 'up' });
window.__rompLinkFailed(false);
out.afterAColumnsOpen = snap();
// clear 4: pageshow
post({ romp: 'wsState', app: 'timeline', state: 'down' });
fire('beforeunload');
post({ romp: 'wsFail', app: 'timeline', cut: false });
out.leavingFourth = snap();
fire('pageshow');
post({ romp: 'wsFail', app: 'timeline', cut: false });
out.afterPageshow = snap();
console.log(JSON.stringify(out));
"""


class AnUnloadsClosesFailNothing(unittest.TestCase):
    """Review round 1 of item 4b (2026-10-04): Firefox closes the page's dials that never opened after beforeunload and before
    pagehide and delivers their close events while the page still runs, so a reload during a return's redial or the boot dials
    wrote one unread entry per shown pane. The Log now holds a latch, `leaving`, set on beforeunload and read first by both
    failure doors (window.__rompLinkFailed and the wsFail listener), and cleared by the page's next real event, since
    beforeunload also fires for a navigation that does not unload (a 204, a download): the shell's next dial or its open
    (window.__rompNotLeaving), a pane's or a column's open, or pageshow. Each door and each clear is executed here; the real
    engines are tests/test_conn_lost_log_served.py's unload legs. Through tests/test_error_center.py's DOM stub."""

    @classmethod
    def setUpClass(cls):
        script = _errc.HARNESS + _errc.km._LANDING_ERRS_JS + LEAVE_DRIVER
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
            f.write(script)
            path = f.name
        try:
            r = subprocess.run(["node", path], capture_output=True, text=True, timeout=30)
        finally:
            os.unlink(path)
        assert r.returncode == 0, "the Log's JS threw: " + r.stderr[:800]
        cls.out = json.loads(r.stdout.strip().splitlines()[-1])

    CHAT = "Kernel connection lost: Chat pane (reconnecting)"
    FEED = "Kernel connection lost: Feed pane (reconnecting)"
    SESSIONS = "Kernel connection lost: Sessions pane (reconnecting)"
    SPLIT2 = "Kernel connection lost: chat split 2 (reconnecting)"
    SPLIT3 = "Kernel connection lost: chat split 3 (reconnecting)"

    def test_the_shell_has_a_door_to_clear_the_latch(self):
        self.assertIs(self.out["door"], True, "window.__rompNotLeaving is the Log's: the shell calls it at each dial and at its open")

    def test_the_links_failure_while_leaving_writes_nothing(self):
        self.assertEqual(self.out["linkWhileLeaving"], [], "the shell's close made by the unload: three drops waiting, none written")

    def test_a_panes_failure_word_while_leaving_writes_nothing(self):
        self.assertEqual(self.out["wordWhileLeaving"], [], "a pane's and a column's close made by the unload write nothing")

    def test_the_shells_next_dial_clears_the_latch(self):
        self.assertEqual(self.out["afterTheShellsDial"], [self.FEED], "the page stayed: the next failure is written")

    def test_a_panes_open_clears_the_latch(self):
        self.assertEqual(self.out["leavingAgain"], [self.FEED], "a second beforeunload sets it again")
        self.assertEqual(self.out["afterAPanesOpen"], [self.FEED, self.CHAT, self.SPLIT2],
                         "a pane's socket opened: the link's refusal writes the drops still waiting")

    def test_a_columns_open_clears_the_latch(self):
        self.assertEqual(self.out["leavingThird"], [self.FEED, self.CHAT, self.SPLIT2])
        self.assertEqual(self.out["afterAColumnsOpen"], [self.FEED, self.CHAT, self.SPLIT2, self.SPLIT3],
                         "a column's socket opened: the column still waiting is written")

    def test_pageshow_clears_the_latch(self):
        self.assertEqual(self.out["leavingFourth"], [self.FEED, self.CHAT, self.SPLIT2, self.SPLIT3])
        self.assertEqual(self.out["afterPageshow"], [self.FEED, self.CHAT, self.SPLIT2, self.SPLIT3, self.SESSIONS],
                         "the page is shown again (a back-forward restore): the Sessions pane's failure is written")


if __name__ == "__main__":
    unittest.main()
