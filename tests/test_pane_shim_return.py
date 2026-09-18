#!/usr/bin/env python3
"""Returning to the dashboard's browser tab must not freeze it (the user 2026-09-07, whose dashboard locked up
after its tab sat in the background).

Each pane iframe rides the kernel's inline WS shim (kernel.py _shim). Before this change a return did three
expensive things at once: the visibility fast-path read `lastRecv` — which only measures how long JS did not
RUN — as "the socket is dead" and redialed a healthy socket (a full resync per pane); every frame the browser
had queued while the tab was hidden or frozen was parsed AND fully rendered in its own task (eight feed
renders, sixteen timeline draws for one newest state); and a redial waited out the blind 1.5s cadence. Now the
Page Lifecycle `resume` event stamps `lastRecv` when the socket is OPEN, the handoff to the bundle rides ONE
ordered FIFO per socket flushed in a single MessageChannel task (a newer whole-state frame replaces the older
one of its type at the END position), a close within STALE_MS of a foreground redials in 250 ms, and every
return leaves a clientDiag breadcrumb naming the regime it landed in. The pane's corner "reconnecting" badge
comes down on the first FRESH frame (romp:wsfresh), not on the socket opening.

The shim's decision code runs here for REAL: km._shim_core_js() returns the IIFE body between its
/*shim-core*/ anchors, and node executes it at module scope with fakes for Date.now, document, WebSocket,
MessageChannel and the timers — the same pattern test_view_deltas.py uses for the delta reassembler, minus the
regex. Synthetic data only: no real session content, TESTHOST as the host.
"""
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)
km = load_source("romp_kernel_shimreturn", os.path.join(BIN, "romp-kernel"))

# The browser the shim thinks it runs in. `var` at module scope shadows node's own WebSocket / MessageChannel /
# setTimeout for the core that follows in the same file, so nothing here touches a real socket or clock.
HARNESS = r"""
var NOW=1000000;Date.now=function(){return NOW;};
var timers=[];var setTimeout=function(fn,ms){timers.push({fn:fn,ms:ms,live:true});return timers.length;};
var clearTimeout=function(id){if(id&&timers[id-1])timers[id-1].live=false;};
var intervals=[];var setInterval=function(fn,ms){intervals.push({fn:fn,ms:ms});return intervals.length;};
var docL={};var document={visibilityState:"visible",wasDiscarded:false,
addEventListener:function(t,f){(docL[t]=docL[t]||[]).push(f);},getElementById:function(){return null;}};
function fire(t){(docL[t]||[]).forEach(function(f){f({type:t});});}
var parentPosts=[],winEvents=[],delivered=[],winL={};
// D3: the fake SHELL the pane sits in publishes a link through window.parent.__rompLink; parentLinkVal is the
// {up,connT} it returns, undefined by default so every pre-D3 test runs the upstream (standalone) fast path unchanged.
var parentLinkVal=undefined;
var window={innerWidth:800,innerHeight:600,
parent:{postMessage:function(m){parentPosts.push(m);},get __rompLink(){return parentLinkVal===undefined?undefined:function(){return parentLinkVal;};}},
addEventListener:function(t,f){(winL[t]=winL[t]||[]).push(f);},
dispatchEvent:function(e){winEvents.push(e.type);return true;},sessionStorage:{getItem:function(){return "";}},
__rompFed:{inbound:function(h,m){delivered.push(m);}}};
function fireWin(t,data){(winL[t]||[]).forEach(function(f){f({data:data});});}   // D3: hand the pane a window message (the shell's panes word)
var location={protocol:"http:",host:"TESTHOST",search:""};
var localStorage={getItem:function(){return null;},setItem:function(){}};
var sockets=[];function WebSocket(url){this.url=url;this.readyState=0;this.sent=[];sockets.push(this);}
WebSocket.prototype.send=function(s){this.sent.push(s);};WebSocket.prototype.close=function(){this.readyState=3;};
var flushes=[];function MessageChannel(){var self=this;this.port1={onmessage:null};
this.port2={postMessage:function(d){flushes.push(function(){self.port1.onmessage({data:d});});}};}
function runFlushes(){var f=flushes;flushes=[];for(var i=0;i<f.length;i++)f[i]();}
function sock(){return sockets[sockets.length-1];}
function open(){var s=sock();s.readyState=1;s.onopen();return s;}
function recv(m){sock().onmessage({data:JSON.stringify(m)});}
function caps(){recv({type:"caps",caps:["tagEdit"],viewsSeq:null});}   // the kernel's answer to a ready it processed (_send_caps), in the shape it sends
function tick(){for(var i=0;i<intervals.length;i++)intervals[i].fn();}
function rows(s,what){return s.sent.map(function(x){return JSON.parse(x);}).filter(function(m){return m.type==="clientDiag"&&(!what||m.what===what);});}
function hide(){document.visibilityState="hidden";fire("visibilitychange");}
function show(){document.visibilityState="visible";fire("visibilitychange");}
function liveTimers(){return timers.filter(function(t){return t.live;}).map(function(t){return {ms:t.ms,fn:t.fn.name};});}
function redials(){return liveTimers().filter(function(t){return t.fn==="connect";});}
function count(list,x){return list.filter(function(e){return e===x;}).length;}
function out(o){process.stdout.write(JSON.stringify(o));}
"""


def _run(scenario, pre=""):
    node = shutil.which("node")
    if not node:
        raise unittest.SkipTest("node not installed")
    fx = tempfile.mkdtemp()
    path = os.path.join(fx, "run.js")
    with open(path, "w") as f:
        f.write(pre + HARNESS + km._shim_core_js() + "\n" + scenario)
    r = subprocess.run([node, path], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise AssertionError("node failed:\n" + r.stderr)
    return json.loads(r.stdout)


class TheSeam(unittest.TestCase):
    def test_the_core_is_the_iife_body_and_fails_loudly_without_anchors(self):
        core = km._shim_core_js()
        self.assertIn("function connect()", core)
        self.assertIn("function enqueue(m)", core)
        self.assertIn('document.addEventListener("visibilitychange"', core)
        self.assertNotIn("/*shim-core*/", core)
        full = km._shim("feed", 3)
        self.assertTrue(full.count("/*shim-core*/") == 1 and full.count("/*end-shim-core*/") == 1)
        self.assertLess(full.index("/*shim-core*/"), full.index("/*end-shim-core*/"))
        # formatted: no python placeholder survives into the runnable core
        self.assertIn('var APP="test";', core)
        self.assertNotIn("%s", core)


class ResumeAwareLiveness(unittest.TestCase):
    """§1.1: `resume` is the event 'lastRecv is stale' was approximating."""

    def test_a_45s_gap_with_a_resume_keeps_the_socket_and_the_watchdog_tick_does_not_abandon(self):
        r = _run(r"""
open();recv({type:"ka"});hide();NOW+=1000;fire("freeze");NOW+=45000;fire("resume");show();tick();
out({sockets:sockets.length,ready:sock().readyState,wsdown:count(winEvents,"romp:wsdown"),
ret:rows(sockets[0],"return"),timers:liveTimers(),lastRecv:lastRecv,now:NOW});""")
        self.assertEqual(r["sockets"], 1, "no redial: the thawed socket is kept")
        self.assertEqual(r["ready"], 1)
        self.assertEqual(r["wsdown"], 0, "the queued watchdog tick saw a fresh lastRecv and did not abandon")
        self.assertEqual(r["lastRecv"], r["now"], "resume stamped the clock")
        self.assertEqual([t for t in r["timers"] if t["ms"] == 1000], [], "no stale prompt armed")
        self.assertEqual(len(r["ret"]), 1)
        d = r["ret"][0]["data"]
        self.assertEqual(d["decision"], "keep")
        self.assertTrue(d["resumed"])
        self.assertEqual(d["frozenMs"], 45000)
        self.assertEqual(d["hiddenMs"], 46000)
        self.assertEqual(d["quietAtResumeMs"], 46000, "the pre-stamp silence is kept for the diagnosis")
        self.assertEqual(d["quietMs"], 0)
        self.assertEqual(d["ready"], 1)

    def test_the_same_gap_without_a_resume_abandons_and_redials_at_once(self):
        r = _run(r"""
open();recv({type:"ka"});hide();NOW+=46000;show();
var afterShow={sockets:sockets.length,oldReady:sockets[0].readyState,oldOnclose:sockets[0].onclose,wsdown:count(winEvents,"romp:wsdown"),timers:liveTimers(),why:pendingWhy};
tick();NOW+=300;open();
out({afterShow:afterShow,afterTick:sockets.length,ret:rows(sock(),"return"),retOnOld:rows(sockets[0],"return").length,newReady:sock().readyState});""")
        a = r["afterShow"]
        self.assertEqual(a["sockets"], 2, "abandon + connect in the same handler — today's behaviour, unchanged")
        self.assertEqual(a["oldReady"], 3)
        self.assertIsNone(a["oldOnclose"], "the abandoned socket's handlers are disowned")
        self.assertEqual(a["wsdown"], 1)
        self.assertEqual(a["why"], "foreground", "the redial is handed its reason: its onopen arms the stale prompt as 'foreground'")
        self.assertEqual(a["timers"], [], "no timer stands in for that event")
        self.assertEqual(r["afterTick"], 2, "the watchdog tick does not dial a third socket over a fresh CONNECTING one")
        # the row is filed AFTER the redial, so it queued for the NEW socket instead of vanishing into the dead one
        self.assertEqual(r["retOnOld"], 0)
        self.assertEqual(len(r["ret"]), 1)
        d = r["ret"][0]["data"]
        self.assertEqual(d["decision"], "redial-stale")
        self.assertFalse(d["resumed"])
        self.assertEqual(d["frozenMs"], 0)
        self.assertEqual(d["quietMs"], 46000)
        self.assertEqual(d["quietAtResumeMs"], -1)

    def test_a_resume_on_a_closed_socket_does_not_stamp_and_the_return_redials_closed(self):
        r = _run(r"""
open();recv({type:"ka"});var stamped=lastRecv;hide();sock().readyState=3;NOW+=45000;fire("resume");show();
out({lastRecvUnchanged:lastRecv===stamped,sockets:sockets.length,decision:null});
""")
        self.assertTrue(r["lastRecvUnchanged"], "only an OPEN socket earns the stamp")
        self.assertEqual(r["sockets"], 2, "a CLOSED socket at return is redialed")

    def test_a_return_that_redials_closed_names_it(self):
        r = _run(r"""
open();recv({type:"ka"});hide();sock().readyState=3;NOW+=45000;show();NOW+=100;open();
out({ret:rows(sock(),"return")});""")
        self.assertEqual(r["ret"][0]["data"]["decision"], "redial-closed")
        self.assertEqual(r["ret"][0]["data"]["ready"], 3)

    # A resumed keep is PROVISIONAL (review find, 2026-09-08): the stamp re-bases the watchdog, it does not vouch
    # for the far end. A peer that died without a FIN reaching the browser (a laptop sleep across a network change,
    # a tunnel whose local end stays open) leaves the socket OPEN at the thaw, so the stamp made the return say
    # `keep` and the old content sat with no badge until the 5 s watchdog crossed STALE_MS, 30 to 35 s later,
    # where the pre-stamp shim redialed at once. Now the kernel's next frame confirms the keep, and until one
    # lands the watchdog runs at PROVISIONAL_MS (1.5 keepalive periods) instead of STALE_MS.
    def test_a_resumed_keep_that_no_frame_confirms_is_put_down_at_the_provisional_bound_and_the_row_re_filed(self):
        r = _run(r"""
open();recv({type:"ka"});hide();NOW+=1000;fire("freeze");NOW+=45000;fire("resume");show();
var kept=sockets.length;NOW+=10000;tick();var at10=sockets.length;   // 10 s of silence since the stamp: inside the bound
NOW+=5001;tick();   // past PROVISIONAL_MS with no beat from the kernel: the kept socket was dead all along
var at15={sockets:sockets.length,oldReady:sockets[0].readyState,wsdown:count(winEvents,"romp:wsdown")};
open();NOW+=200;recv({type:"feed",asks:[]});
out({kept:kept,at10:at10,at15:at15,bound:PROVISIONAL_MS,wdOld:rows(sockets[0],"watchdog-close").length,wdNew:rows(sock(),"watchdog-close").length,
retOld:rows(sockets[0],"return").map(function(x){return x.data;}),retNew:rows(sock(),"return").map(function(x){return x.data;}),
rf:rows(sock(),"return-fresh").map(function(x){return x.data;}),held:returnRow,prov:resumeProvisional});""")
        self.assertEqual(r["kept"], 1, "the thaw itself still keeps the socket: the healthy case pays nothing")
        self.assertEqual(r["at10"], 1, "inside the provisional bound the socket stands")
        self.assertEqual(r["bound"], 15000, "1.5 kernel keepalive periods (KEEPALIVE_S is 10 s): one beat may be in flight, two missing is silence")
        self.assertEqual(r["at15"]["sockets"], 2, "past the bound the watchdog puts it down and redials, not at 30 to 35 s")
        self.assertEqual(r["at15"]["oldReady"], 3)
        self.assertEqual(r["at15"]["wsdown"], 1)
        self.assertEqual((r["wdOld"], r["wdNew"]), (1, 0), "one watchdog-close row, sent down the quiet socket before the abandon")
        self.assertEqual(len(r["retOld"]), 1)
        self.assertEqual(r["retOld"][0]["decision"], "keep")
        self.assertEqual(len(r["retNew"]), 1, "the keep row is re-filed onto the redial: the kept socket proved dead")
        self.assertEqual((r["retNew"][0]["decision"], r["retNew"][0]["resent"]), ("keep", True))
        self.assertIsNone(r["held"], "the held row is spent")
        self.assertEqual(len(r["rf"]), 1)
        self.assertTrue(r["rf"][0]["redialed"], "the return-fresh row on the redial says a dial got in the way")
        self.assertEqual(r["rf"][0]["ms"], 15201, "measured from the foreground, as on any return")
        self.assertEqual(r["prov"], 0, "the redial's frame confirmed the new socket")

    def test_a_resumed_keep_that_a_frame_confirms_lives_to_stale_ms(self):
        r = _run(r"""
open();recv({type:"ka"});hide();NOW+=1000;fire("freeze");NOW+=45000;fire("resume");show();var provAtKeep=resumeProvisional;
NOW+=2000;recv({type:"ka"});var provAfterKa=resumeProvisional;   // the kernel's beat confirms the keep: a keepalive is enough
NOW+=20000;tick();var at22=sockets.length;   // 20 s since that frame: past the provisional bound, inside STALE_MS
NOW+=10001;tick();var at32=sockets.length;   // 30 s since the frame: the ordinary watchdog, as before
out({provAtKeep:provAtKeep,provAfterKa:provAfterKa,at22:at22,at32:at32,wd:rows(sockets[0],"watchdog-close").length});""")
        self.assertEqual(r["provAtKeep"], 1000000 + 46000, "the keep records the stamp it rests on")
        self.assertEqual(r["provAfterKa"], 0, "any frame confirms, the keepalive included")
        self.assertEqual(r["at22"], 1, "confirmed: the shorter bound no longer applies")
        self.assertEqual(r["at32"], 2, "real silence after the confirmation is still put down at STALE_MS")
        self.assertEqual(r["wd"], 1)

    def test_a_socket_already_overdue_before_the_freeze_is_not_stamped_and_redials_at_the_return(self):
        r = _run(r"""
open();recv({type:"ka"});var stamped=lastRecv;hide();NOW+=31000;fire("freeze");NOW+=45000;fire("resume");show();
var afterShow={sockets:sockets.length,lastRecvUnchanged:lastRecv===stamped,prov:resumeProvisional};NOW+=300;open();
out({afterShow:afterShow,ret:rows(sock(),"return").map(function(x){return x.data;})});""")
        a = r["afterShow"]
        self.assertTrue(a["lastRecvUnchanged"], "31 s of silence before the freeze: the far end was gone while JS still ran, the resume vouches for nothing")
        self.assertEqual(a["prov"], 0)
        self.assertEqual(a["sockets"], 2, "the return redials at once, as before the stamp existed")
        self.assertEqual(len(r["ret"]), 1)
        self.assertEqual((r["ret"][0]["decision"], r["ret"][0]["resumed"]), ("redial-stale", True))
        self.assertEqual(r["ret"][0]["quietAtResumeMs"], 76000)


class EagerRedialAfterForeground(unittest.TestCase):
    """§1.1: a close landing within STALE_MS of a foreground is the FIN a frozen tab thawed into — redial now."""

    def test_onclose_within_stale_ms_of_a_foreground_redials_now_else_1500_and_announced_stays_250(self):
        r = _run(r"""
open();recv({type:"ka"});hide();NOW+=5000;show();
sock().readyState=3;sock().onclose();var afterForeground=redials();
timers.length=0;NOW+=60000;connect();open();sock().readyState=3;sock().onclose();var late=redials();
timers.length=0;connect();open();recv({type:"restarting"});sock().readyState=3;sock().onclose();var announced=redials();
out({afterForeground:afterForeground,late:late,announced:announced});""")
        self.assertEqual(r["afterForeground"], [{"ms": 0, "fn": "connect"}], "the first close after a foreground: the close IS the event, redial now")
        self.assertEqual(r["late"], [{"ms": 1500, "fn": "connect"}], "the blind cadence stays for a close nobody foregrounded into")
        self.assertEqual(r["announced"], [{"ms": 250, "fn": "connect"}], "T217's announced-death branch is unchanged")


class OrderedDispatchFifo(unittest.TestCase):
    """§1.2: one FIFO per socket; whole-state frames coalesce at the END position; chained kinds never drop."""

    KEY = 'function k(m){return m.type+(m.n||"")+(m.id?":"+m.id:"");}'

    def test_a_closed_between_two_taborders_lands_before_the_second(self):
        r = _run(self.KEY + r"""
open();recv({type:"tabOrder",order:["a","x"],n:1});recv({type:"closed",id:"x"});recv({type:"tabOrder",order:["a"],n:2});
var before=delivered.length,armed=flushes.length;runFlushes();
out({before:before,armed:armed,got:delivered.map(k),armedAfter:flushes.length});""")
        self.assertEqual(r["before"], 0, "nothing is handed to the bundle synchronously")
        self.assertEqual(r["armed"], 1, "one flush per burst")
        self.assertEqual(r["got"], ["closed:x", "tabOrder2"])
        self.assertEqual(r["armedAfter"], 0)

    def test_three_feeds_collapse_to_the_last(self):
        r = _run(self.KEY + r"""
open();recv({type:"feed",n:1});recv({type:"feed",n:2});recv({type:"feed",n:3});runFlushes();out({got:delivered.map(k)});""")
        self.assertEqual(r["got"], ["feed3"])

    def test_chained_chat_frames_keep_their_places_around_a_coalesced_feed(self):
        r = _run(self.KEY + r"""
open();recv({type:"session",n:1});recv({type:"feed",n:1});recv({type:"chatTail",n:1});recv({type:"feed",n:2});runFlushes();out({got:delivered.map(k)});""")
        self.assertEqual(r["got"], ["session1", "chatTail1", "feed2"])

    def test_skeleton_and_bars_pairs_collapse_to_the_last_of_each_in_order(self):
        r = _run(self.KEY + r"""
open();recv({type:"data",n:1});recv({type:"bars",n:1});recv({type:"data",n:2});recv({type:"bars",n:2});runFlushes();out({got:delivered.map(k)});""")
        self.assertEqual(r["got"], ["data2", "bars2"])

    def test_a_failed_delta_sends_needslot_synchronously_and_enqueues_nothing(self):
        r = _run(r"""
open();recv({type:"delta",slot:"bars",base:7,rev:8,coll:{}});
out({sent:sock().sent.map(function(x){return JSON.parse(x);}).filter(function(m){return m.type==="needSlot";}),fifo:FIFO.length,armed:flushes.length,delivered:delivered.length});""")
        self.assertEqual(r["sent"], [{"type": "needSlot", "slot": "bars"}])
        self.assertEqual(r["fifo"], 0)
        self.assertEqual(r["armed"], 0)
        self.assertEqual(r["delivered"], 0)

    def test_ka_and_restarting_never_enter_the_fifo(self):
        r = _run(r"""
open();recv({type:"ka"});recv({type:"restarting"});out({fifo:FIFO.length,armed:flushes.length,announced:restartAnnounced>0});""")
        self.assertEqual(r["fifo"], 0)
        self.assertEqual(r["armed"], 0)
        self.assertTrue(r["announced"], "restarting is still latched synchronously at receipt")

    def test_abandon_does_not_clear_the_fifo(self):
        r = _run(self.KEY + r"""
open();recv({type:"feed",n:1});recv({type:"session",n:1});abandon();connect();open();recv({type:"chatTail",n:2});runFlushes();out({got:delivered.map(k)});""")
        self.assertEqual(r["got"], ["feed1", "session1", "wsup", "chatTail2"],
                         "the old socket's frames are the newest state; the reconnect's own marker frame enters "
                         "behind them, and the new socket's frames behind that")

    def test_the_hop_is_a_message_channel_and_the_shim_has_no_raf(self):
        js = km._shim("chat", 1)
        self.assertIn("var ch=new MessageChannel();ch.port1.onmessage=flush;", js)
        self.assertIn("ch.port2.postMessage(0);", js)
        self.assertNotIn("requestAnimationFrame", js, "rAF is held while hidden and in display:none frames — state would be withheld")
        self.assertIn("enqueue(msg);};", js, "the handoff line is the one deferred step")
        self.assertIn("WHOLE={feed:1,bars:1,data:1,tabOrder:1,working:1,globalRetryPaused:1}", js)


class FreshCue(unittest.TestCase):
    """§1.4: the pane's reconnecting badge ends on the first FRESH frame, not on the socket opening."""

    def test_wsfresh_fires_at_clearstale_and_the_return_fresh_row_follows_the_first_real_frame(self):
        r = _run(r"""
open();recv({type:"ka"});hide();NOW+=46000;show();NOW+=300;open();
var atOpen={wsup:count(winEvents,"romp:wsup"),wsfresh:count(winEvents,"romp:wsfresh")};
NOW+=700;recv({type:"ka"});
var afterKa={wsfresh:count(winEvents,"romp:wsfresh"),rf:rows(sock(),"return-fresh").length};
NOW+=500;recv({type:"feed",asks:[]});
out({atOpen:atOpen,afterKa:afterKa,wsfresh:count(winEvents,"romp:wsfresh"),parentFresh:parentPosts.filter(function(p){return p.romp==="wsFresh";}).length,
rf:rows(sock(),"return-fresh"),bytes:JSON.stringify({type:"ka"}).length+JSON.stringify({type:"feed",asks:[]}).length,staleLive:liveTimers().filter(function(t){return t.ms===1000;}).length});""")
        self.assertEqual(r["atOpen"], {"wsup": 1, "wsfresh": 0}, "the socket opening is not fresh data")
        self.assertEqual(r["afterKa"], {"wsfresh": 0, "rf": 0}, "a keepalive is not fresh data either")
        self.assertEqual(r["wsfresh"], 1)
        self.assertEqual(r["parentFresh"], 1, "the shell's wsFresh still rides along")
        self.assertEqual(r["staleLive"], 0, "the armed stale prompt was disarmed by the resync")
        self.assertEqual(len(r["rf"]), 1)
        d = r["rf"][0]["data"]
        self.assertEqual(d["ms"], 1500)
        self.assertEqual(d["bytesSince"], r["bytes"])
        self.assertTrue(d["redialed"])

    def test_a_kept_socket_reports_return_fresh_without_a_redial(self):
        r = _run(r"""
open();recv({type:"ka"});hide();NOW+=1000;fire("freeze");NOW+=45000;fire("resume");show();NOW+=40;recv({type:"bars",turns:{}});
out({rf:rows(sock(),"return-fresh"),sockets:sockets.length});""")
        self.assertEqual(r["sockets"], 1)
        self.assertEqual(r["rf"][0]["data"]["ms"], 40)
        self.assertFalse(r["rf"][0]["data"]["redialed"])

    def test_a_kept_socket_whose_fin_thaws_in_the_burst_reports_the_redial(self):
        # the FIN a frozen tab thawed into: decision keep, then onclose in the same burst → 250ms redial. The keep
        # row was written into a socket that was already dead (readyState still 1 until the queued close runs), so
        # the close RE-FILES it marked resent onto the redial, and the return-fresh row on the new socket says
        # redialed:true (review find 2026-09-07: the frozen-then-dropped regime otherwise left no trace)
        r = _run(r"""
open();recv({type:"ka"});hide();NOW+=45000;fire("resume");show();sock().readyState=3;sock().onclose();
var t=liveTimers();NOW+=0;timers[timers.length-1].fn();open();recv({type:"feed",asks:[]});
out({t:t,dead:rows(sockets[0],"return").map(function(x){return x.data;}),fresh:rows(sock(),"return").map(function(x){return x.data;}),
rf:rows(sock(),"return-fresh").map(function(x){return x.data;})});""")
        self.assertEqual(r["t"], [{"ms": 0, "fn": "connect"}], "the first close after a foreground redials NOW")
        self.assertEqual(len(r["dead"]), 1, "the first copy went into the dead socket (nothing can know that yet)")
        self.assertEqual(r["dead"][0]["decision"], "keep")
        self.assertEqual(len(r["fresh"]), 1, "…and the close re-filed it onto the redial")
        self.assertEqual((r["fresh"][0]["decision"], r["fresh"][0]["resent"]), ("keep", True))
        self.assertEqual(len(r["rf"]), 1)
        self.assertTrue(r["rf"][0]["redialed"])
        self.assertEqual(r["rf"][0]["ms"], 0, "the redial was immediate, the first frame followed in the same instant here")

    def test_frames_then_fin_in_the_burst_re_file_both_rows_on_the_redial(self):
        # the common shape: the kernel pushed frames before it gave up, so the thaw burst is [frames…, FIN]. The
        # stale frames land on the dead socket first (readyState still 1) and would file return-fresh there; the
        # close then re-files the return row AND re-opens the return-fresh window, so the new socket carries both
        r = _run(r"""
open();recv({type:"ka"});hide();NOW+=45000;fire("resume");show();recv({type:"feed",asks:[]});recv({type:"bars",turns:{}});
sock().readyState=3;sock().onclose();timers[timers.length-1].fn();open();NOW+=30;recv({type:"feed",asks:[]});
out({fresh:rows(sock(),"return").map(function(x){return x.data;}),rf:rows(sock(),"return-fresh").map(function(x){return x.data;}),held:returnRow});""")
        self.assertEqual(len(r["fresh"]), 1)
        self.assertTrue(r["fresh"][0]["resent"])
        self.assertEqual(len(r["rf"]), 1, "return-fresh re-measured on the socket that delivers")
        self.assertTrue(r["rf"][0]["redialed"])
        self.assertEqual(r["rf"][0]["ms"], 30, "measured from the foreground, not from the dead socket's stale frame")
        self.assertIsNone(r["held"], "the held row is spent")

    def test_a_second_close_inside_the_same_return_window_waits_250ms(self):
        # the immediate redial is spent once per foreground; a kernel that is down answers the redial with another
        # close, and that one waits 250 ms — no tight loop
        r = _run(r"""
open();recv({type:"ka"});hide();NOW+=45000;fire("resume");show();sock().readyState=3;sock().onclose();
var first=liveTimers();timers[timers.length-1].fn();sock().readyState=3;sock().onclose();var second=liveTimers().slice(-1);
out({first:first,second:second});""")
        self.assertEqual(r["first"], [{"ms": 0, "fn": "connect"}])
        self.assertEqual(r["second"], [{"ms": 250, "fn": "connect"}])

    def test_a_close_long_after_the_return_does_not_re_file(self):
        r = _run(r"""
open();recv({type:"ka"});hide();NOW+=45000;fire("resume");show();recv({type:"feed",asks:[]});NOW+=60000;
sock().readyState=3;sock().onclose();NOW+=1500;timers[timers.length-1].fn();open();
out({fresh:rows(sock(),"return").length,delay:liveTimers()});""")
        self.assertEqual(r["fresh"], 0, "a close outside the return window is an ordinary drop: no resend")

    def test_pane_spin_drops_the_badge_on_wsfresh_with_its_own_failsafe_and_no_longer_on_wsup(self):
        for spin in (km._pane_spin("content", "live-ask"), km._pane_spin("feed-list"), km._pane_spin("fleet-list")):
            self.assertIn("window.addEventListener('romp:wsfresh',function(){badge(false);});", spin)
            self.assertIn("window.addEventListener('romp:wsup',function(){hide();});", spin, "wsup still ends the empty-pane sheet")
            self.assertNotIn("window.addEventListener('romp:wsup',function(){badge(false);hide();});", spin,
                             "the socket opening no longer ends 'reconnecting' for a pane with content")
            self.assertIn("function badge(on){if(rb)rb.classList.toggle('on',!!on);clearTimeout(bfail);"
                          "if(on)bfail=setTimeout(function(){badge(false);},30000);}", spin,
                          "the badge's failsafe is armed per show (loader rule) and cleared on hide")
            self.assertIn("window.addEventListener('romp:wsdown',function(){if(ready()){badge(true);}else{show();}});", spin)
        for page in (km._chat_page(), km._feed_page(), km._fleet_page(), km._timeline_page()):
            self.assertIn('new Event("romp:wsfresh")', page, "every pane's shim can fire it")
        self.assertNotIn("romp:wsfresh',function(){badge(false);", km._timeline_page(), "the timeline owns no _pane_spin")


class HeldReturnRow(unittest.TestCase):
    """The keep-decision row is held for ONE reason: a FIN queued in the same thaw burst proves the kept socket was
    already dead, and the close re-files the row onto the redial. Held past that it is a liability (review find,
    2026-09-08): a fresh frame filed return-fresh and zeroed returnAt but left the row, so an ordinary close within
    STALE_MS of the foreground (a kernel restart 5 s after a healthy return) re-filed it `resent` and a second,
    contradictory return-fresh followed. Every return now starts with no held row, and the flush retires a row
    whose return-fresh has filed, once the burst that carried the frame has drained."""

    def test_keep_then_frame_then_an_ordinary_close_files_no_resent_row_and_no_second_return_fresh(self):
        r = _run(r"""
open();recv({type:"ka"});hide();NOW+=1000;fire("freeze");NOW+=45000;fire("resume");show();NOW+=40;recv({type:"feed",asks:[]});runFlushes();
var afterFresh={held:returnRow,rf:rows(sock(),"return-fresh").length,returnAt:returnAt};
NOW+=5000;sock().readyState=3;sock().onclose();var d=liveTimers().slice(-1);timers[timers.length-1].fn();open();NOW+=100;recv({type:"feed",asks:[]});
out({afterFresh:afterFresh,d:d,retNew:rows(sock(),"return").length,rfOld:rows(sockets[0],"return-fresh").length,rfNew:rows(sock(),"return-fresh").length});""")
        self.assertEqual(r["afterFresh"]["rf"], 1)
        self.assertEqual(r["afterFresh"]["returnAt"], 0)
        self.assertIsNone(r["afterFresh"]["held"], "the frame answered the return; once its burst drained, nothing is held")
        self.assertEqual(r["d"], [{"ms": 0, "fn": "connect"}], "the close still redials at once: that rule is the foreground's, not the row's")
        self.assertEqual(r["retNew"], 0, "no resent copy: the kept socket delivered, it did not prove dead")
        self.assertEqual((r["rfOld"], r["rfNew"]), (1, 0), "one return-fresh per return")

    def test_a_row_is_retired_only_once_its_burst_drained_so_a_same_burst_fin_still_re_files(self):
        # the frames-then-FIN thaw (FreshCue above) needs the row to survive the frame that files return-fresh: the
        # hop to the flush runs AFTER every task the thaw queued, a FIN included, so the close still finds the row
        # and it is gone right after
        r = _run(r"""
open();recv({type:"ka"});hide();NOW+=45000;fire("resume");show();recv({type:"feed",asks:[]});
var heldAfterFrame=!!returnRow;runFlushes();var heldAfterFlush=returnRow;
out({heldAfterFrame:heldAfterFrame,heldAfterFlush:heldAfterFlush,fifo:FIFO.length});""")
        self.assertTrue(r["heldAfterFrame"], "the frame alone does not retire the row (a FIN may still be queued behind it)")
        self.assertIsNone(r["heldAfterFlush"])
        self.assertEqual(r["fifo"], 0)

    def test_a_later_return_that_decides_stale_holds_nothing(self):
        r = _run(r"""
open();recv({type:"ka"});hide();NOW+=2000;show();var firstHeld=!!returnRow;   // a keep no frame ever answered
hide();NOW+=46000;show();var held=returnRow;NOW+=300;open();
out({firstHeld:firstHeld,held:held,ret:rows(sock(),"return").map(function(x){return x.data;})});""")
        self.assertTrue(r["firstHeld"])
        self.assertIsNone(r["held"], "every return starts with no held row")
        self.assertEqual(len(r["ret"]), 1, "the stale return files its own row, and nothing older rides the redial")
        self.assertEqual(r["ret"][0]["decision"], "redial-stale")
        self.assertNotIn("resent", r["ret"][0])


class ReturnBreadcrumbs(unittest.TestCase):
    """§1.0: the rows that name the regime on the user's own machine."""

    def test_a_plain_navigation_files_no_page_load_row(self):
        # the row exists for a DISCARDED-and-reloaded tab (the return is a cold load: no visibilitychange, so no
        # `return` row) or a reload/back-forward arrival; a plain navigation has nothing to say and files nothing
        # (four rows per dashboard open would be noise, and they share the queued-breadcrumb cap with real rows)
        r = _run(r"""open();out({sent:sockets[0].sent.map(function(x){return JSON.parse(x).what||JSON.parse(x).type;})});""")
        self.assertNotIn("page-load", r["sent"])

    def test_a_reload_arrival_files_the_page_load_row(self):
        r = _run(r"""open();out({first:JSON.parse(sockets[0].sent[0])});""",
                 pre='var performance={getEntriesByType:function(){return [{type:"reload"}];}};\n')
        self.assertEqual(r["first"], {"type": "clientDiag", "surface": "pane-shim", "what": "page-load",
                                      "data": {"wasDiscarded": False, "nav": "reload", "app": "test"}})

    def test_a_discarded_load_is_flagged(self):
        # the flag is read at load, so the fake document must carry it before the core runs
        script = HARNESS.replace("wasDiscarded:false", "wasDiscarded:true")
        node = shutil.which("node")
        if not node:
            self.skipTest("node not installed")
        fx = tempfile.mkdtemp()
        with open(os.path.join(fx, "run.js"), "w") as f:
            f.write(script + km._shim_core_js() + "\nopen();out({first:JSON.parse(sockets[0].sent[0])});")
        res = subprocess.run([node, os.path.join(fx, "run.js")], capture_output=True, text=True, timeout=60)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertTrue(json.loads(res.stdout)["first"]["data"]["wasDiscarded"])

    def test_return_row_shape(self):
        r = _run(r"""open();recv({type:"ka"});hide();NOW+=2000;show();out({row:rows(sock(),"return")[0]});""")
        row = r["row"]
        self.assertEqual(row["type"], "clientDiag")
        self.assertEqual(row["surface"], "pane-shim")
        self.assertEqual(row["what"], "return")
        self.assertEqual(sorted(row["data"].keys()),
                         sorted(["decision", "resumed", "hiddenMs", "frozenMs", "quietMs", "quietAtResumeMs", "ready", "app"]))
        self.assertEqual(row["data"]["decision"], "keep")
        self.assertEqual(row["data"]["hiddenMs"], 2000)

    def test_return_fresh_row_shape(self):
        r = _run(r"""open();recv({type:"ka"});hide();NOW+=2000;show();NOW+=10;recv({type:"feed",asks:[]});out({row:rows(sock(),"return-fresh")[0]});""")
        self.assertEqual(r["row"]["what"], "return-fresh")
        self.assertEqual(sorted(r["row"]["data"].keys()), sorted(["ms", "bytesSince", "redialed", "app"]))

    def test_no_return_row_before_the_first_connect_and_none_while_going_hidden(self):
        r = _run(r"""hide();show();var pre=sockets[0].sent.length;open();
out({pre:pre,ret:rows(sock(),"return").length,kinds:rows(sock()).map(function(m){return m.what;})});""")
        self.assertEqual(r["pre"], 0, "nothing is sent on a socket that has not opened")
        self.assertEqual(r["ret"], 0, "a return before everConnected has nothing to say")
        self.assertEqual(r["kinds"], [], "…and a plain load files no page-load row either")

    def test_the_kernel_writes_the_rows_to_client_diag(self):
        # the receiving half: the clientDiag branch records `data` through the surface's allowlist (CLIENT_DIAG_KEYS,
        # 2026-09-18), and every key the rows above carry is admitted (tests/test_client_diag_allowlist.py), so the
        # shape above is what lands
        src = open(os.path.join(BIN, "romp-kernel"), encoding="utf-8").read()
        self.assertIn('elif msg and msg.get("type") == "clientDiag":', src)
        self.assertIn('surface = str(msg.get("surface") or "")[:CLIENT_DIAG_STR_MAX]', src)   # cut once, for the row, the lookup and the stderr latch (2026-09-18)
        self.assertIn('"data": _client_diag_admit(surface, msg.get("data"))}', src)
        # #1009 routes the append through _client_diag_append (rotation at the cap); the pin follows the call, whose line
        # _client_diag_line renders (the row cap, 2026-09-18)
        self.assertIn('_client_diag_append(jd.STATE / "client-diag.jsonl", _client_diag_line(rec))', src)


class TimeSlicedFlush(unittest.TestCase):
    """The burst after a thaw is delivered in SLICES (2026-09-07): a flush that has spent its budget re-arms the
    port and the rest of the queue follows in the next task, in order, with the whole-state dedup still in force."""

    def test_a_slow_burst_is_split_across_tasks_in_order_and_nothing_is_lost(self):
        r = _run("""
open();
// every deliver costs 5 ms of fake clock: two frames spend the 8 ms budget, so a 6-frame burst takes 3 tasks
window.__rompFed={inbound:function(h,m){delivered.push(m);NOW+=5;}};
for(var i=1;i<=6;i++)recv({type:"chatTail",id:"s"+i,from:0,events:[]});
var firstArmed=flushes.length;var seen=[];
while(flushes.length){var f=flushes.shift();f();seen.push(delivered.length);}
out({firstArmed:firstArmed,seen:seen,got:delivered.map(function(m){return m.id;}),fifo:FIFO.length});""")
        self.assertEqual(r["firstArmed"], 1, "one flush armed for the burst")
        self.assertEqual(r["got"], ["s1", "s2", "s3", "s4", "s5", "s6"], "wire order, nothing dropped or duplicated")
        self.assertEqual(r["seen"], [2, 4, 6], "two frames per slice at 5 ms each against an 8 ms budget")
        self.assertEqual(r["fifo"], 0)

    def test_a_newer_whole_state_frame_arriving_mid_burst_replaces_its_queued_twin(self):
        r = _run("""
open();
window.__rompFed={inbound:function(h,m){delivered.push(m);NOW+=9;}};   // one frame per slice
recv({type:"chatTail",id:"a",from:0,events:[]});recv({type:"feed",asks:[],v:1});recv({type:"chatTail",id:"b",from:0,events:[]});
flushes.shift()();                                   // slice 1: delivers the first tail, re-arms
recv({type:"feed",asks:[],v:2});                     // arrives between slices: the queued v1 feed is superseded
while(flushes.length){flushes.shift()();}
out({got:delivered.map(function(m){return m.type+":"+(m.id||m.v);})});""")
        self.assertEqual(r["got"], ["chatTail:a", "chatTail:b", "feed:2"], "the older feed left the queue; the newer took the end")

    def test_a_fast_burst_is_one_task_as_before(self):
        r = _run("""
open();
for(var i=1;i<=5;i++)recv({type:"chatTail",id:"s"+i,from:0,events:[]});
var armed=flushes.length;runFlushes();
out({armed:armed,n:delivered.length,armedAfter:flushes.length});""")
        self.assertEqual((r["armed"], r["n"], r["armedAfter"]), (1, 5, 0), "no clock spent → one slice, no re-arm")

    def test_a_frame_whose_handler_throws_does_not_eat_the_rest_of_the_burst_and_its_error_still_surfaces(self):
        # the isolation branch, run (review find, 2026-09-08: it had no test): the bundle throws on the second of
        # three frames; the first and third still land in order, the queue is drained, the port is not left armed,
        # and the error reaches the task's caller (the console, in a browser) instead of vanishing
        r = _run(r"""
open();var n=0;window.__rompFed={inbound:function(h,m){n++;if(n===2)throw new Error("bad frame");delivered.push(m);}};
recv({type:"chatTail",id:"a",from:0,events:[]});recv({type:"chatTail",id:"b",from:0,events:[]});recv({type:"chatTail",id:"c",from:0,events:[]});
var err="";try{runFlushes();}catch(e){err=String(e&&e.message);}
out({got:delivered.map(function(m){return m.id;}),fifo:FIFO.length,armed:flushArmed,rearmed:flushes.length,err:err});""")
        self.assertEqual(r["got"], ["a", "c"], "the bad frame alone is lost; its neighbours are delivered in order")
        self.assertEqual(r["fifo"], 0)
        self.assertFalse(r["armed"])
        self.assertEqual(r["rearmed"], 0, "nothing left to flush, so no re-arm")
        self.assertEqual(r["err"], "bad frame", "the first error is rethrown after the drain")

    def test_source_pin_the_budget_and_the_re_arm(self):
        js = km._shim_core_js()
        self.assertIn("var FLUSH_MS=8;", js)
        self.assertIn("if(FIFO.length&&Date.now()-t0>=FLUSH_MS){flushArmed=true;ch.port2.postMessage(0);break;}", js)
        self.assertIn("while(FIFO.length){var m=FIFO.shift();", js, "drained from the head, in order")


class ReconnectFlag(unittest.TestCase):
    """The redial declares itself (2026-09-07). A redial's URL ends with &reconnect=1&proto=N when THIS page has opened a
    socket before AND its bundle has said ready AND the kernel's caps frame has answered that ready AND the ready is
    not still waiting in the shim's queue for the open (`everConnected&&bundleReady&&readyAcked&&!readyQueued`): the
    one party that knows it holds the sessions the kernel served it, which it can reload lazily, so the kernel
    skeletons the tabs the page is not looking at (tests/test_chat_skeleton_reconnect.py).
    The FIRST dial never carries it: a fresh page holds nothing and must get everything, as today. Nor does a redial
    after a first socket that opened and died before the bundle's ready (2026-09-10): the page held nothing on that
    socket, and with the flag the kernel would serve the skeleton strip, the active tab in full and a status frame
    per tab into a document with no listener yet, all redone whole once the bundle's ready is processed (the kernel
    pops the set at `ready`). Nor does a redial whose bundle said ready while the socket was down:
    that ready sits in the queue (readyQueued) and flushes onto the redial socket as the bundle's own, so the dial
    keys on the queue bit too. A ready posted while the FIRST socket is still CONNECTING (the bundle evaluated before
    the handshake finished) queues the same way: send() sees readyState 0, sets the bit and queues the ready, that
    socket's onopen flushes it exactly once and clears the bit. Nor does a redial after a ready that left on an OPEN
    socket which then died before the kernel answered it: the kernel's ready arm pops the skeleton set, serves the
    page whole and only then sends its caps frame (_send_caps, the one sender), so that frame is the kernel's word
    that the page was served, and the shim latches it (readyAcked) for the page's life. A keepalive back is no
    answer, and neither is a pushed view frame: the pusher serves a socket from its registration at accept, ahead
    of the ready's processing. A page whose caps frame never comes (the socket died between the pushes and the
    frame) dials fresh for its life, since the bundle posts ready once and no later socket carries one: every
    redial of it is served whole, the cost before 2026-09-07, never a false skeleton. The twin-retire at
    registration was rejected as the signal: it misses a socket the kernel already dropped."""

    def test_the_first_dial_has_no_flag_and_a_redial_after_the_kernel_answered_the_bundles_ready_carries_it_after_iid_and_active(self):
        r = _run(r"""
function redial(){var live=timers.filter(function(t){return t.live&&t.fn.name==="connect";});live[live.length-1].fn();}
var first=sockets[0].url;
localStorage.getItem=function(){return JSON.stringify({activeId:"S1"});};   // the page persisted its active tab before the drop
open();window.__rompLocalSend({type:"ready"});caps();recv({type:"ka"});sock().readyState=3;sock().onclose();redial();var second=sock().url;   // the bundle said ready on the first socket and the kernel answered it: the page holds sessions
localStorage.getItem=function(){return null;};                              // a page with no hint still says it reconnected
open();recv({type:"ka"});sock().readyState=3;sock().onclose();redial();var third=sock().url;
out({first:first,second:second,third:third,n:sockets.length});""")
        self.assertEqual(r["n"], 3)
        self.assertNotIn("reconnect", r["first"], "a fresh page holds nothing: no flag on the first dial")
        self.assertTrue(r["first"].startswith("ws://TESTHOST/ws?app=test&delta=1&iid="), r["first"])
        self.assertTrue(r["second"].startswith("ws://TESTHOST/ws?app=test&delta=1&iid="), r["second"])
        self.assertTrue(r["second"].endswith("&active=S1&reconnect=1&proto=1"),
                        "the flag is APPENDED after the active hint, so the kernel's active-first build is untouched: " + r["second"])
        self.assertTrue(r["third"].endswith("&reconnect=1&proto=1") and "active=" not in r["third"],
                        "no hint → the kernel sends everything, but the page still names itself a reconnect (the kernel's answer stands for the page's life; no later socket carries a ready): " + r["third"])
        self.assertEqual(r["third"].count("&reconnect=1"), 1)

    def test_the_redial_carries_the_protocol_the_bundles_ready_declared(self):
        """T323 stage 4b, round 3: a redial posts no ready of its own, so the dial term carries the chat wire the bundle's
        ready declared (proto 2: uuid frames; an older bundle's bare ready: 1), and the kernel's registration reads it."""
        r = _run(r"""
function redial(){var live=timers.filter(function(t){return t.live&&t.fn.name==="connect";});live[live.length-1].fn();}
localStorage.getItem=function(){return JSON.stringify({activeId:"S1"});};
open();window.__rompLocalSend({type:"ready",proto:2});caps();recv({type:"ka"});sock().readyState=3;sock().onclose();redial();var second=sock().url;
out({second:second,readyProto:readyProto});""")
        self.assertTrue(r["second"].endswith("&active=S1&reconnect=1&proto=2"), "the proto-2 page's redial says so: " + r["second"])
        self.assertEqual(r["readyProto"], 2)

    def test_a_ready_the_kernel_never_answered_is_posted_again_on_the_fresh_dial(self):
        """Round 3, C: the socket died between the kernel's pushes and its caps frame. The page dials fresh (no flag), and
        that dial posts the bundle's ready AGAIN, so the kernel processes it (the page served whole, the protocol
        recorded), answers with its caps frame, and the redials after carry the flag. A ready that flushed from the
        queue on this open is not doubled."""
        r = _run(r"""
function redial(){var live=timers.filter(function(t){return t.live&&t.fn.name==="connect";});live[live.length-1].fn();}
function readys(s){return s.sent.map(function(x){return JSON.parse(x);}).filter(function(m){return m.type==="ready";});}
localStorage.getItem=function(){return JSON.stringify({activeId:"S1"});};
open();window.__rompLocalSend({type:"ready",proto:2});recv({type:"ka"});                  // the ready left; no caps frame came back
sock().readyState=3;sock().onclose();redial();var fresh=sock().url;var s2=sock();open();     // the fresh dial: no flag…
var reposted=readys(s2);
caps();recv({type:"ka"});sock().readyState=3;sock().onclose();redial();var designed=sock().url;   // …the kernel answers on THIS socket: the next redial declares itself
var s3=sock();open();var reposted3=readys(s3);
// a ready QUEUED while the socket was down flushes once on the open and is not posted a second time
sock().readyState=3;sock().onclose();window.__rompLocalSend({type:"ready",proto:2});redial();var s4=sock();open();var flushed4=readys(s4);
out({fresh:fresh,reposted:reposted,designed:designed,reposted3:reposted3,flushed4:flushed4});""")
        self.assertNotIn("reconnect", r["fresh"], "unanswered: the page dials fresh")
        self.assertEqual(r["reposted"], [{"type": "ready", "proto": 2}], "…and posts its ready again on that socket")
        self.assertTrue(r["designed"].endswith("&active=S1&reconnect=1&proto=2"), "answered on the second socket: the third redial declares itself: " + r["designed"])
        self.assertEqual(r["reposted3"], [], "an answered ready is not posted again")
        self.assertEqual(len(r["flushed4"]), 1, "a queued ready flushes once and is not doubled by the re-post")

    def test_a_first_socket_that_died_before_the_bundles_ready_redials_without_the_flag(self):
        # the mid-load drop: the shim dials during HTML parse while the bundle is still downloading or evaluating
        # (the kernel's `ready` handler comment), so a first socket can open and die before the bundle says ready.
        # The page has opened a socket, so everConnected is true, but its bundle has not said ready, so it holds
        # nothing. The redial must dial as a fresh page: with the flag, the kernel would serve the skeleton strip,
        # the active tab in full and a status frame per tab into a document with no listener yet, and redo them all
        # whole once the bundle's ready arrives.
        r = _run(r"""
function redial(){var live=timers.filter(function(t){return t.live&&t.fn.name==="connect";});live[live.length-1].fn();}
function readys(s){return s.sent.filter(function(x){return JSON.parse(x).type==="ready";}).length;}
localStorage.getItem=function(){return JSON.stringify({activeId:"S1"});};
open();recv({type:"ka"});sock().readyState=3;sock().onclose();redial();var midLoad=sock().url;    // opened, died, no bundle yet
open();recv({type:"ka"});sock().readyState=3;sock().onclose();redial();var midLoad2=sock().url;   // and again: still no bundle
open();window.__rompLocalSend({type:"ready"});caps();recv({type:"ka"});                         // the bundle says ready on the third socket and the kernel answers it
var readySent=readys(sock());
sock().readyState=3;sock().onclose();redial();var designed=sock().url;                         // the designed redial: the page held sessions
out({midLoad:midLoad,midLoad2:midLoad2,readySent:readySent,designed:designed,n:sockets.length});""")
        self.assertEqual(r["n"], 4)
        self.assertNotIn("reconnect", r["midLoad"], "opened and died before the bundle's ready: no flag, the page holds nothing: " + r["midLoad"])
        self.assertTrue(r["midLoad"].endswith("&active=S1"), "the active hint still rides: " + r["midLoad"])
        self.assertNotIn("reconnect", r["midLoad2"], "however many sockets died before the bundle: " + r["midLoad2"])
        self.assertEqual(r["readySent"], 1, "the bundle's own ready went out on the third socket")
        self.assertTrue(r["designed"].endswith("&active=S1&reconnect=1&proto=1"),
                        "once the kernel has answered the bundle's ready, a redial declares itself: " + r["designed"])

    def test_a_ready_that_queued_while_the_socket_was_down_redials_without_the_flag_and_goes_out_once_on_the_redial(self):
        # the first socket opened and died before the bundle's ready; the bundle says ready WHILE the socket is down,
        # so send() sets bundleReady and queues it. Keyed on everConnected alone (or on everConnected&&bundleReady)
        # the redial would declare itself and the flushed ready, the bundle's first, would reach the kernel on a
        # socket flagged as a redial. The dial keys on !readyQueued too: no flag, and the queued ready is the ONE
        # ready on the redial socket (the flush carries it; onopen adds nothing). Once that ready has left on a
        # socket and the kernel has answered it, the next redial is the designed one and declares itself.
        r = _run(r"""
function redial(){var live=timers.filter(function(t){return t.live&&t.fn.name==="connect";});live[live.length-1].fn();}
function readys(s){return s.sent.filter(function(x){return JSON.parse(x).type==="ready";}).length;}
localStorage.getItem=function(){return JSON.stringify({activeId:"S1"});};
open();recv({type:"ka"});sock().readyState=3;sock().onclose();                 // opened, died, no bundle yet
window.__rompLocalSend({type:"ready"});var onDead=readys(sockets[0]);           // the bundle says ready while the socket is down: queued
redial();var queued=sock().url;
open();var flushed=readys(sock());caps();                                       // the redial opens: the flush carries the ready, and the kernel answers it
recv({type:"ka"});sock().readyState=3;sock().onclose();redial();var designed=sock().url;   // the page holds what the kernel served on that socket: the designed redial
out({onDead:onDead,queued:queued,flushed:flushed,designed:designed,n:sockets.length});""")
        self.assertEqual(r["n"], 3)
        self.assertEqual(r["onDead"], 0, "nothing goes out on a dead socket: the ready waits in the queue")
        self.assertNotIn("reconnect", r["queued"], "the bundle's ready is still queued: no flag, the page holds nothing: " + r["queued"])
        self.assertTrue(r["queued"].endswith("&active=S1"), "the active hint still rides: " + r["queued"])
        self.assertEqual(r["flushed"], 1, "the queued ready goes out on the redial socket, once: the flush carries it")
        self.assertTrue(r["designed"].endswith("&active=S1&reconnect=1&proto=1"),
                        "the ready has left on a socket and the kernel answered it: the next redial declares itself: " + r["designed"])

    def test_a_ready_posted_while_the_first_socket_is_still_connecting_queues_flushes_once_at_its_open_and_the_next_redial_declares_itself(self):
        # the bundle evaluates before the first socket's handshake finishes: the shim dialled during HTML parse, so
        # the socket is CONNECTING (readyState 0) when the bundle posts ready. send() cannot put it on a socket that
        # is not open, so the ready queues with readyQueued set; the first onopen flushes it exactly once and clears
        # the bit (on the FIRST open too, not only on a reconnect's); the next redial then declares itself. The bits
        # are read by name (readyQueued, bundleReady, queue: the shim's own variables at the harness's module scope,
        # the way SocketFlipMarker reads FIFO), because while a socket is CONNECTING no dial runs, so no URL can show
        # what the queue bit held at that moment.
        r = _run(r"""
function redial(){var live=timers.filter(function(t){return t.live&&t.fn.name==="connect";});live[live.length-1].fn();}
function readys(s){return s.sent.filter(function(x){return JSON.parse(x).type==="ready";}).length;}
function queuedReadys(){return queue.filter(function(x){return JSON.parse(x).type==="ready";}).length;}
localStorage.getItem=function(){return JSON.stringify({activeId:"S1"});};
var first=sockets[0].url,firstState=sockets[0].readyState;
window.__rompLocalSend({type:"ready"});                                                    // the bundle says ready while the first socket is still connecting
var connecting={sent:readys(sockets[0]),readyQueued:readyQueued,bundleReady:bundleReady,inQueue:queuedReadys()};
open();                                                                                     // the first socket opens: the flush carries the ready
var opened={sent:readys(sockets[0]),readyQueued:readyQueued,inQueue:queuedReadys()};
caps();recv({type:"ka"});sock().readyState=3;sock().onclose();redial();var designed=sock().url;   // the kernel answered the flushed ready: the designed redial
open();                                                                                     // the redial opens: nothing left to flush
out({first:first,firstState:firstState,connecting:connecting,opened:opened,designed:designed,onFirst:readys(sockets[0]),onRedial:readys(sockets[1]),n:sockets.length});""")
        self.assertEqual(r["n"], 2)
        self.assertEqual(r["firstState"], 0, "the harness's first socket is CONNECTING until open()")
        self.assertNotIn("reconnect", r["first"], "the first dial never carries the flag: " + r["first"])
        self.assertEqual(r["connecting"]["sent"], 0, "nothing goes out on a socket that has not opened")
        self.assertTrue(r["connecting"]["bundleReady"], "send() has seen the bundle's ready (bundleReady, read by name)")
        self.assertTrue(r["connecting"]["readyQueued"], "the ready waits for the open (readyQueued, read by name), on a CONNECTING socket as on a closed one")
        self.assertEqual(r["connecting"]["inQueue"], 1, "the ready sits in the shim's queue (queue, read by name)")
        self.assertEqual(r["opened"]["sent"], 1, "the first open flushes the queued ready onto its socket, once")
        self.assertFalse(r["opened"]["readyQueued"], "the flush clears the queue bit on the FIRST open, not only on a reconnect's")
        self.assertEqual(r["opened"]["inQueue"], 0, "the flush emptied the queue: no second copy waits for a later open")
        self.assertTrue(r["designed"].endswith("&active=S1&reconnect=1&proto=1"),
                        "the ready has left on a socket, none is queued and the kernel answered it: the next redial declares itself: " + r["designed"])
        self.assertEqual(r["designed"].count("&reconnect=1"), 1)
        self.assertEqual((r["onFirst"], r["onRedial"]), (1, 0), "one ready on the first socket, none on the redial's: the bundle's ready went out exactly once")

    def test_a_ready_the_kernel_never_answered_redials_without_the_flag_and_the_page_dials_fresh_until_a_caps_frame_arrives(self):
        # the residual the queue bit left open: the bundle's ready left on an OPEN socket (bundleReady set, readyQueued
        # not), and the socket died before the kernel processed it, a keepalive the only frame back. Keyed on
        # everConnected&&bundleReady&&!readyQueued the redial declared itself and was served skeletons for sessions the
        # page had never received. The kernel's ready arm answers every ready it processes with a caps frame, sent
        # after its pushes (_send_caps, the one sender), so the shim latches on that frame (readyAcked): no caps, no
        # flag. Once set the latch holds for the page's life; never set, it stays clear for the page's life, since
        # the bundle posts ready once and no later socket carries one: every redial of such a page is served whole.
        r = _run(r"""
function redial(){var live=timers.filter(function(t){return t.live&&t.fn.name==="connect";});live[live.length-1].fn();}
localStorage.getItem=function(){return JSON.stringify({activeId:"S1"});};
open();window.__rompLocalSend({type:"ready"});recv({type:"ka"});sock().readyState=3;sock().onclose();redial();var unanswered=sock().url;   // the ready left on an open socket; a keepalive came back, never the caps frame, and the socket died
open();recv({type:"ka"});sock().readyState=3;sock().onclose();redial();var stillFresh=sock().url;                                    // no later socket carries a ready, so no caps frame comes: the page keeps dialling fresh
open();caps();sock().readyState=3;sock().onclose();redial();var answered=sock().url;                                                 // harness only (a kernel answers no socket that carried no ready): the frame, and the frame alone, arms the gate
out({unanswered:unanswered,stillFresh:stillFresh,answered:answered,n:sockets.length});""")
        self.assertEqual(r["n"], 4)
        self.assertNotIn("reconnect", r["unanswered"],
                         "the kernel never answered the ready, so it never served the page: the redial dials as a fresh page: " + r["unanswered"])
        self.assertTrue(r["unanswered"].endswith("&active=S1"), "the active hint still rides: " + r["unanswered"])
        self.assertNotIn("reconnect", r["stillFresh"],
                         "no later socket carries a ready and no caps frame comes: the page dials fresh for its life: " + r["stillFresh"])
        self.assertTrue(r["answered"].endswith("&active=S1&reconnect=1&proto=1"),
                        "the caps frame is the latch, on whichever socket of the page it arrives: " + r["answered"])

    def test_a_pushed_view_frame_after_the_ready_is_not_the_kernels_answer_only_the_caps_frame_is(self):
        # the pusher serves a client from its registration at accept, on its own cycle or the reconnect wake, so a
        # view frame can land after the bundle's ready left and before the ready arm processed it: the first frame
        # after the ready is no evidence the ready was processed, and the latch is the caps frame alone.
        r = _run(r"""
function redial(){var live=timers.filter(function(t){return t.live&&t.fn.name==="connect";});live[live.length-1].fn();}
localStorage.getItem=function(){return JSON.stringify({activeId:"S1"});};
open();window.__rompLocalSend({type:"ready"});recv({type:"feed",asks:[]});recv({type:"ka"});sock().readyState=3;sock().onclose();redial();var pushed=sock().url;
out({pushed:pushed,n:sockets.length});""")
        self.assertEqual(r["n"], 2)
        self.assertNotIn("reconnect", r["pushed"], "a pushed view frame is the pusher's, not the ready arm's answer: no flag: " + r["pushed"])
        self.assertTrue(r["pushed"].endswith("&active=S1"), r["pushed"])

    def test_a_caps_frame_arms_nothing_on_its_own_neither_before_the_bundles_ready_nor_while_that_ready_is_still_queued(self):
        # the kernel answers only a ready it processed, so in production a caps frame implies the bundle's ready has
        # left and is not queued; the term keeps bundleReady and !readyQueued as the shim-local facts all the same
        # (four events in order, no one bit standing in for the rest). Harness only, both legs: a caps frame before
        # any ready from this bundle arms nothing, and with the frame on record a ready that then queues on a
        # CONNECTING redial (send() sees readyState 0) holds the gate through that redial's failure until a later
        # open's flush has carried it.
        r = _run(r"""
function redial(){var live=timers.filter(function(t){return t.live&&t.fn.name==="connect";});live[live.length-1].fn();}
function readys(s){return s.sent.filter(function(x){return JSON.parse(x).type==="ready";}).length;}
localStorage.getItem=function(){return JSON.stringify({activeId:"S1"});};
open();caps();recv({type:"ka"});sock().readyState=3;sock().onclose();redial();var noReady=sock().url;   // a caps frame before any ready from this bundle
window.__rompLocalSend({type:"ready"});var onConnecting=readys(sock());                                  // the bundle says ready while the redial is still connecting: queued
sock().readyState=3;sock().onclose();redial();var queued=sock().url;                                    // that redial never opened (a failed connect): the next dials with the ready still queued
open();var flushed=readys(sock());caps();sock().readyState=3;sock().onclose();redial();var designed=sock().url;
out({noReady:noReady,onConnecting:onConnecting,queued:queued,flushed:flushed,designed:designed,n:sockets.length});""")
        self.assertEqual(r["n"], 4)
        self.assertNotIn("reconnect", r["noReady"], "no ready from this bundle: the frame alone arms nothing: " + r["noReady"])
        self.assertEqual(r["onConnecting"], 0, "nothing goes out on a socket that has not opened")
        self.assertNotIn("reconnect", r["queued"], "the ready is still queued: the frame on record does not stand in for its flush: " + r["queued"])
        self.assertEqual(r["flushed"], 1, "the flush carries the queued ready onto the socket that opened, once")
        self.assertTrue(r["designed"].endswith("&active=S1&reconnect=1&proto=1"), "ready, flush and answer all on record: the redial declares itself: " + r["designed"])


class SocketFlipMarker(unittest.TestCase):
    """The socket flip reaches the bundle as a FRAME ({type:"wsup"}) through the FIFO, in order with the frames — a
    bundle that scopes 'loaded on this socket' must not learn the flip at onopen while the dead socket's last frames
    are still draining (review find 2026-09-07). A first open sends none."""

    def test_a_reconnect_open_enqueues_the_marker_first_and_a_first_open_does_not(self):
        r = _run(r"""
open();var first=FIFO.length;recv({type:"ka"});sock().readyState=3;sock().onclose();timers[timers.length-1].fn();open();
var afterRedial=FIFO.map(function(m){return m.type;});runFlushes();
out({first:first,afterRedial:afterRedial,delivered:delivered.map(function(m){return m.type;})});""")
        self.assertEqual(r["first"], 0, "a first open is not a flip")
        self.assertEqual(r["afterRedial"], ["wsup"], "the redial's open enqueues the marker, before any frame of the new socket")
        self.assertEqual(r["delivered"], ["wsup"])


class LocalUpFlag(unittest.TestCase):
    """The shim publishes its socket's state as window.__rompLocalUp beside the wsState post to the shell (2026-09-18):
    federation.ts, in the same document, gates its relay dial on it. The relay is this same kernel's /remote/<host>/ws on
    this origin, so a relay dial while the local socket is down hangs until the relay watchdog's 15 s cut and is dialed
    again (55 such rows in 23 minutes on the user's phone). Undefined until the socket first opens or closes, so a page
    without the shim and a fresh page dial as before; true while it is OPEN; false after onclose, an opened socket's or a
    refused dial's, and after abandon(). The flag moves with the wsState post, never apart from it."""

    RUN_REDIAL = r"""function runRedial(){var t=timers.filter(function(x){return x.live&&x.fn.name==="connect";});t.forEach(function(x){x.live=false;x.fn();});return t.length;}
"""

    def test_undefined_before_any_event_true_at_open_false_at_close_and_at_abandon(self):
        r = _run(self.RUN_REDIAL + r"""
var before=("__rompLocalUp" in window);
open();var atOpen=window.__rompLocalUp;
recv({type:"ka"});sock().readyState=3;sock().onclose({code:1006,reason:"",wasClean:false});var atClose=window.__rompLocalUp;
var ran=runRedial();var atRedial=window.__rompLocalUp;   // the onclose timer's connect(): a CONNECTING socket is not up
open();var atReopen=window.__rompLocalUp;
abandon();var atAbandon=window.__rompLocalUp;
out({before:before,atOpen:atOpen,atClose:atClose,ran:ran,atRedial:atRedial,atReopen:atReopen,atAbandon:atAbandon,nulled:ws===null,
posts:parentPosts.filter(function(p){return p.romp==="wsState";}).map(function(p){return p.state;})});""")
        self.assertFalse(r["before"], "no flag before the first socket event: a page whose socket has not spoken dials its relay as today")
        self.assertIs(r["atOpen"], True)
        self.assertIs(r["atClose"], False, "onclose puts it down with the wsState post")
        self.assertEqual(r["ran"], 1)
        self.assertIs(r["atRedial"], False, "a redial in flight is not up until it opens")
        self.assertIs(r["atReopen"], True)
        self.assertIs(r["atAbandon"], False, "abandon() puts it down too: the disowned socket's onclose never runs")
        self.assertTrue(r["nulled"])
        self.assertEqual(r["posts"], ["up", "down", "up", "down"], "the flag and the shell's wsState post move together")

    def test_a_refused_first_dial_reads_down_and_the_first_open_reads_up_without_a_wsup(self):
        r = _run(self.RUN_REDIAL + r"""
sock().readyState=3;sock().onclose({code:1006,reason:"",wasClean:false});var atRefusal=window.__rompLocalUp;
runRedial();open();var atOpen=window.__rompLocalUp;
out({atRefusal:atRefusal,atOpen:atOpen,wsup:count(winEvents,"romp:wsup")});""")
        self.assertIs(r["atRefusal"], False, "a dial the kernel refused: the socket is down, opened before or not")
        self.assertIs(r["atOpen"], True)
        self.assertEqual(r["wsup"], 0, "a FIRST open dispatches no romp:wsup (the loader waits for content): the relay's road back here is federation's 4 s poll, which reads the flag")

    def test_the_foreground_fast_path_abandon_puts_it_down_and_the_redials_open_puts_it_up_with_the_wsup(self):
        # the order is asserted where federation relies on it: the harness window's dispatchEvent is wrapped before the
        # redial's open() to record the flag as each romp:wsup finds it, so a shim that flipped it after the dispatch
        # reads false HERE (reading the flag and the count after onopen returned proves nothing about the order)
        r = _run(r"""
open();recv({type:"ka"});hide();NOW+=46000;show();var atReturn=window.__rompLocalUp;var dialed=sockets.length;
var flagAtWsup=[];var dispatch=window.dispatchEvent;
window.dispatchEvent=function(e){if(e.type==="romp:wsup")flagAtWsup.push(window.__rompLocalUp);return dispatch(e);};
NOW+=300;open();var atReopen=window.__rompLocalUp;
out({atReturn:atReturn,dialed:dialed,atReopen:atReopen,wsup:count(winEvents,"romp:wsup"),flagAtWsup:flagAtWsup});""")
        self.assertIs(r["atReturn"], False, "the return's abandon: down, with a fresh dial CONNECTING")
        self.assertEqual(r["dialed"], 2)
        self.assertIs(r["atReopen"], True)
        self.assertEqual(r["wsup"], 1, "the reconnect open dispatches one romp:wsup")
        self.assertEqual(r["flagAtWsup"], [True], "…AFTER the flag flipped: the listener federation installs (localUp) reads true inside the dispatch")


class ShellLedReturn(unittest.TestCase):
    """D3 (2026-09-18): the shell leads the visible pane's redial. A pane that sits in a shell publishing a link
    (window.parent.__rompLink) puts its socket down on a stale return and dials only when the link is up: at once if it
    already is, else on the shell's link-up word (a panes word with link:'up'), recording linkUpMs on its return-fresh;
    a loud link-backstop dials anyway when the shell's connT, its loop-alive stamp (the later of its last dial and its
    watchdog's last tick with a socket to watch, review round 2), is 25 s stale: the shell's tick has stopped (the bound
    is derived from the shell's whole alive cycle on a hung path, tests/test_kernel_ws_heartbeat.py pins it). A standalone
    page (no __rompLink) runs the upstream path unchanged. Independent of PR 3 (hidden panes park): here every pane awaits
    the link.

    parentLinkVal is the shell's {up,connT}; fireWin("message",{romp:'panes',link:...}) hands the pane the shell's word
    as a pane frame hears it, fireWin("message",{romp:'link',link:...}) as the settings frame or a split chat column
    hears it (review round 1, 2026-09-18: a link word of its own, since a panes word would replace those frames' set)."""

    def test_await_with_the_link_down_puts_the_socket_down_and_dials_nothing_across_two_ticks(self):
        r = _run(r"""
open();recv({type:"ka"});hide();NOW+=46000;sock().readyState=3;   // the phone's case: the socket is dead on return
parentLinkVal={up:false,connT:NOW};   // the shell's link is down but its loop is alive (connT fresh): the pane waits
show();
var atReturn={sockets:sockets.length,nulled:ws===null,awaiting:awaitLink};
tick();NOW+=5000;tick();              // the tick re-reads the link: down and young, so no dial
var afterTicks=sockets.length;
parentLinkVal={up:true,connT:NOW};fireWin("message",{romp:"panes",on:{},link:"up"});open();   // end the await to flush the queued return row
out({atReturn:atReturn,afterTicks:afterTicks,ret:rows(sock(),"return").map(function(x){return x.data;})});""")
        self.assertEqual(r["atReturn"]["sockets"], 1, "the down link: no dial at the return")
        self.assertTrue(r["atReturn"]["nulled"], "the socket is put down (abandon nulls ws), so the watchdog tick is inert")
        self.assertIs(r["atReturn"]["awaiting"], True)
        self.assertEqual(r["afterTicks"], 1, "no dial while the link stays down and its loop alive")
        self.assertEqual(len(r["ret"]), 1)
        self.assertEqual(r["ret"][0]["decision"], "redial-closed")
        self.assertIs(r["ret"][0]["awaitLink"], True, "the return row says it is waiting for the link")

    def test_the_link_up_word_dials_once_and_the_return_fresh_carries_linkUpMs(self):
        r = _run(r"""
open();recv({type:"ka"});hide();NOW+=46000;
parentLinkVal={up:false,connT:NOW};show();
var dialedAtReturn=sockets.length;
NOW+=4000;parentLinkVal={up:true,connT:NOW};fireWin("message",{romp:"panes",on:{},link:"up"});
var dialedAfterWord=sockets.length;
NOW+=200;open();NOW+=50;recv({type:"feed",asks:[]});
out({dialedAtReturn:dialedAtReturn,dialedAfterWord:dialedAfterWord,
rf:rows(sock(),"return-fresh").map(function(x){return x.data;})});""")
        self.assertEqual(r["dialedAtReturn"], 1, "no dial while awaiting")
        self.assertEqual(r["dialedAfterWord"], 2, "the link-up word dials exactly once")
        self.assertEqual(len(r["rf"]), 1)
        self.assertEqual(r["rf"][0]["linkUpMs"], 4000, "linkUpMs is foreground->link-up: the path's own recovery")
        self.assertTrue(r["rf"][0]["redialed"])

    def test_the_shells_link_word_ends_the_await_at_the_words_time_not_the_backstop_ticks(self):
        # review round 1 (correctness-1): the settings frame and a split chat column are shim-bearing iframes the panes
        # word never reached, so they ended a shell-led await only on the 5 s backstop poll and their linkUpMs absorbed
        # it. The shell now tells them a link word of their own ({romp:'link',link}); the shim ends its await on it.
        r = _run(r"""
open();recv({type:"ka"});hide();NOW+=46000;
parentLinkVal={up:false,connT:NOW};show();
var dialedAtReturn=sockets.length;
NOW+=300;parentLinkVal={up:true,connT:NOW};fireWin("message",{romp:"link",link:"up"});   // the word a split column or the settings frame hears: no pane set on it
var dialedAfterWord=sockets.length,awaitingAfterWord=awaitLink;
NOW+=200;open();NOW+=50;recv({type:"feed",asks:[]});
out({dialedAtReturn:dialedAtReturn,dialedAfterWord:dialedAfterWord,awaitingAfterWord:awaitingAfterWord,
rf:rows(sock(),"return-fresh").map(function(x){return x.data;})});""")
        self.assertEqual(r["dialedAtReturn"], 1, "no dial while awaiting")
        self.assertEqual(r["dialedAfterWord"], 2, "the link word dials at once, as the panes word does")
        self.assertIs(r["awaitingAfterWord"], False)
        self.assertEqual(r["rf"][0]["linkUpMs"], 300, "linkUpMs is the word's time, not the 5 s backstop tick's")

    def test_the_link_up_at_the_decision_dials_at_once_with_awaitLink_false(self):
        r = _run(r"""
parentLinkVal={up:true,connT:NOW};
open();recv({type:"ka"});hide();NOW+=46000;show();
var dialed=sockets.length;
NOW+=100;open();NOW+=10;recv({type:"feed",asks:[]});
out({dialed:dialed,ret:rows(sock(),"return").map(function(x){return x.data;}),
rf:rows(sock(),"return-fresh").map(function(x){return x.data;})});""")
        self.assertEqual(r["dialed"], 2, "the path is up at the decision: dial at once")
        self.assertIs(r["ret"][0]["awaitLink"], False)
        self.assertEqual(r["rf"][0]["linkUpMs"], 0, "the whole return-fresh.ms is the code-owned wait when the path was already up")

    def test_a_keep_return_in_a_linked_pane_dials_nothing_and_its_rows_carry_no_awaitLink_and_no_linkUpMs(self):
        # review round 2 (tests-1): the per-return reset (awaitLink false, linkUpMs -1) had no test that fails without it,
        # and neither did the body's claim that a tab whose socket stood sees no change. An awaited return whose return-fresh
        # carries linkUpMs 4000, then a short background with the socket standing: the second return is a keep in a pane
        # whose shell publishes a link, so it dials nothing, its return row has no awaitLink (the link-led block never ran)
        # and its return-fresh no linkUpMs (the stamp is per return, not sticky). Rows are read across every socket.
        r = _run(r"""
function allRows(what){var a=[];sockets.forEach(function(s){rows(s,what).forEach(function(x){a.push(x.data);});});return a;}
open();recv({type:"ka"});hide();NOW+=46000;
parentLinkVal={up:false,connT:NOW};show();                          // an awaited return
NOW+=4000;parentLinkVal={up:true,connT:NOW};fireWin("message",{romp:"panes",on:{},link:"up"});   // the word: one dial
open();NOW+=50;recv({type:"feed",asks:[]});                          // its return-fresh files: linkUpMs 4000
var afterFirst=sockets.length;
hide();NOW+=1000;show();                                             // a short background, the socket standing: keep
recv({type:"feed",asks:[]});                                         // the keep's return-fresh files on the first real frame
out({afterFirst:afterFirst,afterSecond:sockets.length,awaiting:awaitLink,ret:allRows("return"),rf:allRows("return-fresh")});""")
        self.assertEqual(r["afterFirst"], 2)
        self.assertEqual(r["afterSecond"], 2, "a keep dials nothing, in a linked pane as in a standalone one")
        self.assertIs(r["awaiting"], False)
        self.assertEqual([x["decision"] for x in r["ret"]], ["redial-stale", "keep"], "the awaited return found its socket OPEN but 46 s quiet; the second return found it standing")
        self.assertIs(r["ret"][0]["awaitLink"], True)
        self.assertNotIn("awaitLink", r["ret"][1], "the keep's return row has no awaitLink: the link-led block never ran")
        self.assertEqual(len(r["rf"]), 2)
        self.assertEqual(r["rf"][0]["linkUpMs"], 4000)
        self.assertNotIn("linkUpMs", r["rf"][1], "the keep's return-fresh has no linkUpMs: the stamp is reset at every return")

    def test_a_standalone_page_with_no_shell_link_dials_at_once_as_today(self):
        r = _run(r"""
open();recv({type:"ka"});hide();NOW+=46000;show();
var dialed=sockets.length;
NOW+=100;open();
out({dialed:dialed,ret:rows(sock(),"return").map(function(x){return x.data;})});""")
        self.assertEqual(r["dialed"], 2, "no __rompLink (standalone / VS Code): the upstream fast path dials at once")
        self.assertNotIn("awaitLink", r["ret"][0], "the standalone return row has no awaitLink field")

    def test_an_in_window_close_cadence_by_link_state(self):
        # link up at the close: today's 0/250 in-window cadence (the upstream lines, a proven path); link down: no
        # blind timer, re-await (the link-up word is the redial's event) and the socket put down so the tick is inert
        r = _run(r"""
function connectTimers(){return timers.filter(function(t){return t.live&&t.fn.name==="connect";});}
function fireConnects(){connectTimers().forEach(function(t){t.live=false;t.fn();});}
parentLinkVal={up:true,connT:NOW};
open();recv({type:"ka"});hide();NOW+=46000;show();                 // link up: dials at once
open();                                                             // the dialed socket opens
NOW+=100;sock().readyState=3;sock().onclose({code:1006});          // an in-window close, link still up
var up={armed:connectTimers().length,delays:connectTimers().map(function(t){return t.ms;})};
fireConnects();open();                                              // the armed redial opens a fresh socket
parentLinkVal={up:false,connT:NOW};                                 // now the link is down
NOW+=100;sock().readyState=3;sock().onclose({code:1006});          // an in-window close with the link down
var down={armed:connectTimers().length,awaiting:awaitLink,nulled:ws===null};
out({up:up,down:down});""")
        self.assertGreaterEqual(r["up"]["armed"], 1, "an in-window close with the link up arms the upstream 0/250 redial")
        self.assertIn(r["up"]["delays"][-1], [0, 250], "...at the 0/250 in-window cadence")
        self.assertEqual(r["down"]["armed"], 0, "an in-window close with the link down arms no blind timer")
        self.assertIs(r["down"]["awaiting"], True, "...it re-awaits the link-up word instead")
        self.assertTrue(r["down"]["nulled"], "...and puts the socket down so the tick is inert")

    def test_a_restarting_frame_keeps_its_250ms_redial_with_the_link_down(self):
        # review round 1 (tests-1): the close must land INSIDE a return window, or the D3 onclose line is never reached
        # (inWin false: the 250 came from the upstream clause and the test passed with the guard's restart exception
        # removed). So: a stale return with the link up (dials at once), one in-window close with the link up (the
        # upstream cadence, redialed and open), then the announced restart, the link going down with it, and the close.
        r = _run(r"""
function connectTimers(){return timers.filter(function(t){return t.live&&t.fn.name==="connect";});}
function fireConnects(){connectTimers().forEach(function(t){t.live=false;t.fn();});}
parentLinkVal={up:true,connT:NOW};
open();recv({type:"ka"});hide();NOW+=46000;show();open();           // a stale return with the link up: dials at once, opens
NOW+=100;sock().readyState=3;sock().onclose({code:1006});fireConnects();open();   // one in-window close with the link up: the upstream 0/250 redial, open again
recv({type:"restarting",boot:"1"});                                 // the kernel announces its death
parentLinkVal={up:false,connT:NOW};                                 // and the shell's link goes down with it
NOW+=100;sock().readyState=3;sock().onclose({code:1006});          // the in-window close with the link down and a restart announced
out({delays:connectTimers().map(function(t){return t.ms;}),awaiting:awaitLink,wsNull:ws===null});""")
        self.assertEqual(r["delays"], [250], "an announced restart keeps its tight 250 ms redial even with the link down, inside the window")
        self.assertIs(r["awaiting"], False, "...and does not re-await: the announce is the kernel's own word")
        self.assertFalse(r["wsNull"], "...and the socket is not put down (the re-await path is the one that nulls it)")

    def test_the_link_backstop_brackets_the_shells_whole_alive_cycle_no_dial_at_24999ms_a_dial_at_25001ms(self):
        # review round 1 (kernel-2, tests-6): the bound is the shell's whole alive cycle on a hung path, from its named
        # constants (the 15 s cut, the tick that performs it, the 2 s blind redial: 22 s, rounded up to the next tick,
        # 25 s; tests/test_kernel_ws_heartbeat.py pins the sum). The 20 s bound omitted the redial, so a pane tick landing
        # in the loop's last two seconds called an alive loop dead. Two-sided: nothing at the cycle's worst case (22 s)
        # nor at 24,999 ms; a dial and a link-backstop row at 25,001 ms.
        r = _run(r"""
open();recv({type:"ka"});hide();NOW+=46000;
parentLinkVal={up:false,connT:NOW};show();                         // connT fresh at the return: the shell's loop is alive
var awaiting=awaitLink,dialedAtReturn=sockets.length;
tick();var afterFirstTick=sockets.length;                          // link down and young: no dial
NOW+=22000;tick();var at22000=sockets.length;                      // the alive cycle's worst case: still the shell's loop
NOW+=2999;tick();var at24999=sockets.length;
NOW+=2;tick();var at25001=sockets.length;                          // the shell's connT unrenewed past the whole cycle: its loop is dead
open();                                                             // the fresh socket opens: the queued link-backstop row flushes onto it
out({awaiting:awaiting,dialedAtReturn:dialedAtReturn,afterFirstTick:afterFirstTick,at22000:at22000,at24999:at24999,at25001:at25001,
backstop:rows(sock(),"link-backstop").length});""")
        self.assertIs(r["awaiting"], True)
        self.assertEqual(r["dialedAtReturn"], 1, "no dial at the return while the link is down")
        self.assertEqual(r["afterFirstTick"], 1, "no dial while the link is down and its loop young")
        self.assertEqual(r["at22000"], 1, "no dial at 22 s stale: the shell's loop can still be alive there (cut + tick + blind redial)")
        self.assertEqual(r["at24999"], 1, "no dial one ms under the bound")
        self.assertEqual(r["at25001"], 2, "the backstop dials anyway once the shell's connT is stale past the whole cycle")
        self.assertEqual(r["backstop"], 1, "...and files a loud link-backstop diag row")

    def test_a_refused_backstop_dial_re_awaits_and_the_backstop_redials_each_tick_inside_the_window_then_the_blind_cadence(self):
        # review round 1 (tests-6): the cadence after a backstop dial the path refuses, stated as intended. The shell's
        # loop is dead, so the link-up word will never come: the refusal re-awaits (the D3 onclose line, inside the
        # window) and the backstop's next 5 s tick dials again with another loud row, until the return window ends (30 s
        # from the foreground); a refusal outside the window arms the upstream blind 1.5 s redial and awaits nothing.
        # A bounded 5 s cadence with a row per dial is the fault's own signal, not a storm.
        r = _run(r"""
function refuseIfDialed(){var s=sock();if(s.readyState===0){s.readyState=3;s.onclose({code:1006});}}
open();recv({type:"ka"});hide();NOW+=46000;
parentLinkVal={up:false,connT:NOW-10001};show();                   // the shell's connT already 10 s stale at the return
var log=[];
for(var t=5000;t<=30000;t+=5000){NOW+=5000;tick();var d=sockets.length;refuseIfDialed();
log.push({t:t,dialed:d,awaiting:awaitLink,blind:redials().map(function(x){return x.ms;})});}
timers.filter(function(x){return x.live&&x.fn.name==="connect";}).forEach(function(x){x.live=false;x.fn();});open();   // the blind redial opens: the queued rows flush onto it
out({log:log,backstops:rows(sock(),"link-backstop").length});""")
        by_t = {e["t"]: e for e in r["log"]}
        self.assertEqual([by_t[5000]["dialed"], by_t[10000]["dialed"]], [1, 1], "connT 15 s and 20 s stale: inside the bound, no dial")
        self.assertEqual(by_t[15000], {"t": 15000, "dialed": 2, "awaiting": True, "blind": []}, "25,001 ms stale: the backstop dials; the refusal re-awaits (in the window), no blind timer")
        self.assertEqual(by_t[20000], {"t": 20000, "dialed": 3, "awaiting": True, "blind": []}, "the next tick dials again, and re-awaits again")
        self.assertEqual(by_t[25000], {"t": 25000, "dialed": 4, "awaiting": True, "blind": []})
        self.assertEqual(by_t[30000], {"t": 30000, "dialed": 5, "awaiting": False, "blind": [1500]}, "at the window's end the refusal arms the upstream blind 1.5 s redial and awaits nothing")
        self.assertEqual(r["backstops"], 4, "one loud link-backstop row per backstop dial")

    # ---- review round 2 (2026-09-18)
    def test_a_stray_pre_return_blind_redial_timer_is_refused_while_the_return_awaits_the_link(self):
        # fresh-1: the pane's own blind 1.5 s redial, armed by a close the page saw while hidden, survived the fast path's
        # abandon and dialed during the shell-led await (the pane-side twin of the shell defect round 1 fixed). While that
        # stray socket stood, the link listener and the backstop were inert (both need no socket) and the return-fresh
        # carried no linkUpMs though the return row said awaitLink true. connect() now refuses a caller while awaitLink is
        # set; every legitimate caller clears it first, so only the stray timer is refused.
        r = _run(r"""
open();recv({type:"ka"});hide();
NOW+=1000;sock().readyState=3;sock().onclose({code:1006});          // the close reaches the page while hidden, no return window open: the upstream blind 1.5 s redial arms
var armed=redials().map(function(t){return t.ms;});
NOW+=45000;parentLinkVal={up:false,connT:NOW};show();               // the return: the link is down, the pane awaits
var atReturn={sockets:sockets.length,awaiting:awaitLink};
timers.filter(function(t){return t.live&&t.fn.name==="connect";}).forEach(function(t){t.live=false;t.fn();});   // the pending timer fires during the await
var afterTimer={sockets:sockets.length,awaiting:awaitLink,nulled:ws===null};
NOW+=4000;parentLinkVal={up:true,connT:NOW};fireWin("message",{romp:"panes",on:{},link:"up"});   // the link-up word
var afterWord=sockets.length;
open();NOW+=50;recv({type:"feed",asks:[]});
out({armed:armed,atReturn:atReturn,afterTimer:afterTimer,afterWord:afterWord,rf:rows(sock(),"return-fresh").map(function(x){return x.data;})});""")
        self.assertEqual(r["armed"], [1500], "the close while hidden armed the upstream blind redial")
        self.assertEqual(r["atReturn"], {"sockets": 1, "awaiting": True})
        self.assertEqual(r["afterTimer"], {"sockets": 1, "awaiting": True, "nulled": True}, "the stray timer dials nothing: the await stands and the socket stays down")
        self.assertEqual(r["afterWord"], 2, "the link-up word is the one dial")
        self.assertEqual(r["rf"][0]["linkUpMs"], 4000, "...and the return-fresh carries linkUpMs")

    def test_the_backstops_up_arm_dials_at_the_next_tick_when_this_pane_missed_the_link_up_word(self):
        # tests-2: the backstop's other arm, unexecuted before. The link came up but no word reached this pane: the next
        # 5 s tick reads the link up and dials, with no link-backstop row (the loop is alive; this is the poll, not the loud
        # arm), and linkUpMs is the tick's time, foreground to link-up as this pane learned it.
        r = _run(r"""
open();recv({type:"ka"});hide();NOW+=46000;
parentLinkVal={up:false,connT:NOW};show();
NOW+=5000;parentLinkVal={up:true,connT:NOW-5000};                   // the link came up; no word reaches this pane
var beforeTick=sockets.length;
tick();
var afterTick={sockets:sockets.length,awaiting:awaitLink};
open();NOW+=50;recv({type:"feed",asks:[]});
out({beforeTick:beforeTick,afterTick:afterTick,backstop:rows(sock(),"link-backstop").length,rf:rows(sock(),"return-fresh").map(function(x){return x.data;})});""")
        self.assertEqual(r["beforeTick"], 1)
        self.assertEqual(r["afterTick"], {"sockets": 2, "awaiting": False}, "the tick reads the link up and dials")
        self.assertEqual(r["backstop"], 0, "no link-backstop row: the up arm is the poll, not the loud arm")
        self.assertEqual(r["rf"][0]["linkUpMs"], 5000, "linkUpMs is the tick's time")

    def test_a_fresh_tick_stamp_with_an_hours_old_dial_time_is_an_alive_loop_no_backstop_dial(self):
        # regression-1, the pane's side: the shell's connT is a loop-alive stamp, the later of its last dial and its
        # watchdog's last tick with a socket to watch (kernel.py _LANDING_MOBILE_JS __rompLink; the shell's side runs in
        # tests/test_kernel_mobile.py ShellLinkProbe). The case the stamp exists for: the shell's OPEN socket, dialed an hour
        # ago, crosses the quiet bound and reads down for the tick before the shell puts it down; a pane whose in-window
        # close lands in that tick re-awaits and must not call the loop dead on the dial time. The fake shell here publishes
        # the max the shell does; the pane dials no backstop while the stamp is fresh and does once it is 25 s stale.
        r = _run(r"""
var shellDialT=NOW-3600000,shellTickT=NOW;                            // the shell's model: an OPEN socket dialed an hour ago, its tick alive
function shellLink(up){return {up:up,connT:Math.max(shellDialT,shellTickT)};}
parentLinkVal=shellLink(true);
open();recv({type:"ka"});hide();NOW+=46000;shellTickT=NOW;show();open();   // a stale return with the link up: dials at once, opens
NOW+=100;parentLinkVal=shellLink(false);                             // the shell's socket crosses the quiet bound: the link reads down, its tick not yet run
sock().readyState=3;sock().onclose({code:1006});                    // an in-window close with the link down: re-await
var awaiting=awaitLink;
NOW+=5000;shellTickT=NOW;parentLinkVal=shellLink(false);tick();      // the shell's tick stamped: connT fresh, so no backstop dial
var afterAliveTick=sockets.length;
NOW+=25001;parentLinkVal=shellLink(false);tick();                    // the stamp 25 s stale (the shell's tick stopped): the loud arm
out({awaiting:awaiting,afterAliveTick:afterAliveTick,afterDeadTick:sockets.length});""")
        self.assertIs(r["awaiting"], True)
        self.assertEqual(r["afterAliveTick"], 2, "a fresh tick stamp with an hours-old dial time: the loop is alive, no backstop dial")
        self.assertEqual(r["afterDeadTick"], 3, "the stamp 25 s stale: the backstop dials")


if __name__ == "__main__":
    unittest.main()
