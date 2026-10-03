#!/usr/bin/env python3
"""The Log writes "Kernel connection lost" when a reconnect FAILS, never at the drop (iOS item 4b, 2026-10-03).

Every return to the app logged the entry for the chat and the Feed, with an unread digit on the Log control, although the
sockets came back at once: the shell's Log wrote it at each pane's up-to-down transition, and a return always makes one (the
shim puts a stale socket down before it redials; a thawed page receives the FIN of a socket the OS dropped). The entry now
waits in the Log's `lost` until the event that says the reconnect failed, a dial that closed without ever opening, and a
socket that reopens first drops it unwritten. Three pieces, each executed here under node against the code as served:

  ShimFailureWord        kernel/kernel.py _shim: a dial that never opened posts {romp:'wsFail',app} to the shell after its
                         down word (refused, or cut by the watchdog's CONNECTING arm); an opened socket's close, the
                         return's abandon() and a park post none. Through tests/test_pane_shim_return.py's harness.
  ShellLinkFailure       _LANDING_MOBILE_JS: the shell socket's close of a dial that never opened (refused, or its own
                         connect cut) calls window.__rompLinkFailed once; an opened socket's close, the return's abandon and
                         a superseded socket's late close call nothing. Through tests/test_kernel_mobile.py's probe harness.
  LogWaitsForTheFailure  _LANDING_ERRS_JS: a drop alone writes nothing (the live red cue shows it); a failure word, or the
                         link's failure for every waiting pane, writes one entry per drop; an up drops the waiting entry; a
                         pane not shown keeps waiting and is written once shown; a parked pane is dropped; a split column
                         waits under its own key. Through tests/test_error_center.py's DOM stub.

The composition in real engines (phone and desktop, healthy and failing returns) is tests/test_conn_lost_log_served.py.
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
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)
import test_error_center as _errc          # noqa: E402  the modules, not their classes: an imported TestCase would be collected twice
import test_kernel_mobile as _mob          # noqa: E402
import test_pane_shim_return as _shimret   # noqa: E402


# ---- the shim's failure word ----
WORDS = r"""function words(){return parentPosts.filter(function(p){return p.romp==="wsState"||p.romp==="wsFail";}).map(function(p){return p.romp==="wsFail"?"fail":p.state;});}
"""


class ShimFailureWord(unittest.TestCase):
    def test_a_refused_dial_posts_its_down_word_then_the_failure_word(self):
        r = _shimret._run(WORDS + r"""
sock().readyState=3;sock().onclose({code:1006,reason:"",wasClean:false});   // the boot dial never opened: refused
out({words:words(),app:parentPosts.filter(function(p){return p.romp==="wsFail";}).map(function(p){return p.app;})});""", app="feed")
        self.assertEqual(r["words"], ["down", "fail"], "the down word first (the shell's state), then the failure the Log waits for")
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
        self.assertEqual(r["afterClose"], ["up", "down", "down", "fail"], "the cut dial never opened: its close is the failure")

    def test_a_park_posts_no_failure_word(self):
        r = _shimret._run(WORDS + r"""
open();recv({type:"ka"});park();out({words:words()});""")
        self.assertEqual(r["words"], ["up", "parked"], "a park is its own state, never a failure")


# ---- the shell link's failure ----
LINKFAIL = r"""var LF=0;window.__rompLinkFailed=function(){LF++;};
"""


class ShellLinkFailure(unittest.TestCase):
    def test_a_refused_dial_calls_the_link_failure_and_an_opened_sockets_close_does_not(self):
        r = _mob._run_probe(LINKFAIL + r"""
shRefuseNow();var afterRefusal=LF;           // the boot dial refused
shFireDials();shOpen();shRecv({type:'ka'});var s=shSock();s.readyState=3;s.onclose({code:1006});var afterOpenedClose=LF;
shOut({afterRefusal:afterRefusal,afterOpenedClose:afterOpenedClose});""")
        self.assertEqual(r["afterRefusal"], 1, "a dial that never opened: the link failed to come back")
        self.assertEqual(r["afterOpenedClose"], 1, "an opened socket's close is a drop, not a failure")

    def test_the_returns_abandon_calls_nothing_and_its_redials_connect_cut_does(self):
        r = _mob._run_probe(LINKFAIL + r"""
shOpen();shRecv({type:'ka'});shHide();SHSOCKS[0].readyState=3;SHNOW+=100;shShow();var afterReturn=LF;   // abandon the dead socket, dial at once
var hung=shSock();shRunDue(SHNOW+15000);var cut=hung.readyState;var beforeClose=LF;   // the path hangs: the dial's own cut closes it at SH_CONNECT_MS
hung.onclose({code:1006});
shOut({afterReturn:afterReturn,cut:cut,beforeClose:beforeClose,afterClose:LF});""")
        self.assertEqual(r["afterReturn"], 0, "the return's put-down of a stale socket is no failure")
        self.assertEqual(r["cut"], 3, "the dial's own cut closed it")
        self.assertEqual(r["beforeClose"], 0)
        self.assertEqual(r["afterClose"], 1, "the cut dial never opened: its close is the failure")

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
window.__rompLinkFailed();
out.link = snap();                                         // the shell's link failed: every waiting shown pane
BODY.add('po-waiting');
window.__rompLinkFailed();
out.shownLater = snap();                                   // the Waiting pane is shown now and still down: written at the next failure
post({ romp: 'wsState', app: 'timeline', state: 'down' });
post({ romp: 'wsState', app: 'timeline', state: 'parked' });
window.__rompLinkFailed();
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
window.__rompLinkFailed();
out.colBack = snap();                                      // a column that reopened has nothing waiting
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

    def test_a_split_column_waits_under_its_own_key(self):
        self.assertEqual(self.out["colDrop"]["conn"], 5, "the column's drop alone writes nothing")
        self.assertEqual(self.out["colFailed"]["texts"], ["Kernel connection lost: chat split 2 (reconnecting)"])
        self.assertEqual(self.out["colBack"]["texts"], ["Kernel connection lost: chat split 2 (reconnecting)"],
                         "a column that reopened before the link failed has nothing waiting")


if __name__ == "__main__":
    unittest.main()
