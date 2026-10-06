#!/usr/bin/env python3
"""A pane page standing alone (opened by itself, outside the dashboard shell) takes the pane set's revision from GET /panes, the
records `romp pane list` reads and the read the shell builds its custom panes from: the pages the route table renders bake no
revision (tests/test_pane_records_one_source.py reads every one byte for byte), so the shim reads the revision once, with a bare
same-origin fetch the page-key script keys, and hands it to the reload core (adoptPanes) and to its keepalive gate (LOADEDPV). A
keepalive carrying that revision offers nothing; one carrying another offers the reload. A failed read is said on the page's one
bar, never taken for no change; a refusal that asks for a new sign-in says nothing more, since the page-key script is taking the
top frame to /login. Inside the dashboard the shell's own read decides and the page reads nothing, and a state-root page keeps the
revision its route baked.

The page's REAL code runs here: the reload core the page carries and the shim's decision code (km._shim_core_js's anchors), at
module scope under node with fakes for the clock, the socket, fetch and the bar's elements (the harness tests/test_pane_shim_return.py
runs the shim under, copied, plus those). Synthetic data only (TESTHOST)."""
import json
import os
import shutil
import subprocess
import tempfile
import unittest

from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)
km = load_source("romp_kernel_panesetrev", os.path.join(BIN, "romp-kernel"))

# tests/test_pane_shim_return.py's harness (the browser the shim thinks it runs in), copied
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
// D2: the fake shell's layout probe (window.parent.__rompMobileOn), parentMobileVal its answer; undefined by default so every
// pre-D2 test runs off a shell that parks nothing
var parentMobileVal=undefined;
var window={innerWidth:800,innerHeight:600,
parent:{postMessage:function(m){parentPosts.push(m);},get __rompLink(){return parentLinkVal===undefined?undefined:function(){return parentLinkVal;};},
get __rompMobileOn(){return parentMobileVal===undefined?undefined:function(){return parentMobileVal;};}},
addEventListener:function(t,f){(winL[t]=winL[t]||[]).push(f);},
dispatchEvent:function(e){winEvents.push(e.type);return true;},sessionStorage:{getItem:function(){return "";}},
__rompFed:{inbound:function(h,m){delivered.push(m);}}};
function fireWin(t,data){(winL[t]||[]).forEach(function(f){f({data:data});});}   // D3: hand the pane a window message (the shell's panes word)
function word(on,link){fireWin("message",{romp:"panes",on:on,avail:{files:false},link:link||"up"});}   // D2: the shell's panes word (on[k] per pane, the link)
function states(){return parentPosts.filter(function(p){return p.romp==="wsState";}).map(function(p){return p.state;});}   // the wsState words this pane told the shell, in order
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
function queued(what){return queue.map(function(x){return JSON.parse(x);}).filter(function(m){return m.type==="clientDiag"&&(!what||m.what===what);});}   // D2: the rows waiting in the shim's queue for a socket (a parked pane's, until its tap)
function fireTimers(){var n=0;timers.forEach(function(t){if(t.live){t.live=false;t.fn();n++;}});return n;}   // every pending timer fires once
function hide(){document.visibilityState="hidden";fire("visibilitychange");}
function show(){document.visibilityState="visible";fire("visibilitychange");}
function liveTimers(){return timers.filter(function(t){return t.live;}).map(function(t){return {ms:t.ms,fn:t.fn.name};});}
function redials(){return liveTimers().filter(function(t){return t.fn==="connect";});}
function count(list,x){return list.filter(function(e){return e===x;}).length;}
function out(o){process.stdout.write(JSON.stringify(o));}
"""

# ...plus GET /panes (ANSWER: the response a scenario's `before` sets; FETCHES: each request) and the bar's elements (BARS: the
# page's bars as selfBar appends them)
PAGE = r"""
var FETCHES=[],ANSWER=null,BARS=[];
var fetch=function(u,o){FETCHES.push({url:u,cache:(o&&o.cache)||""});return ANSWER?Promise.resolve(ANSWER):new Promise(function(){});};
function el(tag){return {tagName:tag,dataset:{},style:{},children:[],firstChild:null,id:"",textContent:"",
appendChild:function(c){this.children.push(c);if(!this.firstChild)this.firstChild=c;return c;},
remove:function(){var i=BARS.indexOf(this);if(i>=0)BARS.splice(i,1);},addEventListener:function(){}};}
document.createElement=el;document.body={appendChild:function(b){BARS.push(b);return b;}};
document.getElementById=function(id){for(var i=0;i<BARS.length;i++)if(BARS[i].id===id)return BARS[i];return null;};
function bars(){return BARS.map(function(b){return {kind:b.dataset.kind,text:b.firstChild?b.firstChild.textContent:""};});}
function answer(status,body,reauth){ANSWER={ok:status>=200&&status<300,status:status,headers:{get:function(k){return (reauth&&k==="X-Romp-Reauth")?"1":null;}},
json:function(){return Promise.resolve(body);}};}
function later(f){globalThis.setTimeout(f,0);}   // after the read's promise chain has run (the harness's setTimeout is the fake)
"""


def _page_js(**shim_kw):
    """The page's script as served, split at the shim core: the reload core it carries, then the shim's decision code."""
    js = km._shim("test", 5, **shim_kw)
    i = js.index("(function(){/*shim-core*/")
    j = js.index("/*end-shim-core*/")
    return js[:i], js[i + len("(function(){/*shim-core*/"):j]


def _run(scenario, before="", **shim_kw):
    node = shutil.which("node")
    if not node:
        raise unittest.SkipTest("node not installed")
    core, shim = _page_js(**shim_kw)
    fx = tempfile.mkdtemp()
    try:
        path = os.path.join(fx, "run.js")
        with open(path, "w") as f:
            f.write(HARNESS + PAGE + before + "\n" + core + "\n" + shim + "\n" + scenario)
        r = subprocess.run([node, path], capture_output=True, text=True, timeout=60)
    finally:
        shutil.rmtree(fx, ignore_errors=True)
    if r.returncode != 0:
        raise AssertionError("node failed:\n" + r.stderr[-2000:])
    return json.loads(r.stdout)


# the keepalives after the read: the revision the page read, then another
_KEEPALIVES = r"""
later(function(){var R=window.__rompReload,o={fetches:FETCHES,loaded:LOADEDPV,afterRead:bars()};
open();recv({type:"ka",dv:5,pv:"P1"});o.same=bars();o.sameOffer=R.offered();
recv({type:"ka",dv:5,pv:"P2"});o.moved=bars();o.movedOffer=R.offered();out(o);});
"""
_READ = [{"url": "/panes", "cache": "no-store"}]
_FAILED = "Couldn't read the panes defined at the kernel (%s), so this page can't offer a reload when they change. Reload to try again."


class APageStandingAloneReadsItsRevision(unittest.TestCase):
    def test_a_page_standing_alone_reads_the_revision_from_get_panes_and_offers_a_reload_only_when_it_moves(self):
        r = _run(_KEEPALIVES, before='answer(200,{panes:[],rev:"P1"});')
        self.assertEqual(r["fetches"], _READ, "the page reads GET /panes once, a bare same-origin read the page-key script keys: %r" % r["fetches"])
        self.assertEqual((r["loaded"], r["afterRead"]), ("P1", []), "the read's revision is the page's, and nothing is said")
        self.assertEqual((r["same"], r["sameOffer"]), ([], None), "a keepalive carrying the revision the page read offers nothing")
        self.assertEqual([b["kind"] for b in r["moved"]], ["offer"], "another revision offers the reload: %r" % r["moved"])
        self.assertEqual((r["moved"][0]["text"], (r["movedOffer"] or {}).get("pv")), (km.RELOAD_OFFER_PANES_MSG, "P2"))

    def test_a_failed_read_is_shown_on_the_page_never_taken_for_no_change(self):
        r = _run(_KEEPALIVES, before="answer(500,{});")
        self.assertEqual(r["fetches"], _READ)
        self.assertEqual(r["afterRead"], [{"kind": "warn", "text": _FAILED % "/panes answered HTTP 500"}], "the failure is said on the page's bar: %r" % r["afterRead"])
        self.assertEqual(r["loaded"], "", "no revision is assumed")
        self.assertEqual((r["moved"], r["movedOffer"]), (r["afterRead"], None), "the bar stands; with no revision read, nothing is compared")

    def test_an_answer_with_no_revision_is_a_failed_read(self):
        r = _run(_KEEPALIVES, before="answer(200,{panes:[]});")
        self.assertEqual(r["fetches"], _READ)
        self.assertEqual(r["afterRead"], [{"kind": "warn", "text": _FAILED % "the answer carried no pane-set revision"}], r["afterRead"])

    def test_a_refusal_that_asks_for_a_new_sign_in_says_nothing_more(self):
        r = _run(_KEEPALIVES, before="answer(403,{},true);")
        self.assertEqual(r["fetches"], _READ)
        self.assertEqual((r["afterRead"], r["loaded"]), ([], ""), "the page-key script is taking the top frame to /login: no bar")

    def test_a_page_inside_the_dashboard_reads_nothing_itself(self):
        # the shell's head read (its state object) exists before any pane frame does: the shell's read and its own socket decide
        r = _run(_KEEPALIVES, before='answer(200,{panes:[],rev:"P1"});window.parent.__rompPaneRecords={state:"loading",done:[]};')
        self.assertEqual((r["fetches"], r["loaded"]), ([], ""), "no read of its own")
        self.assertEqual((r["moved"], r["movedOffer"]), ([], None), "and its keepalive gate relays nothing")

    def test_a_state_root_page_keeps_its_routes_revision_and_reads_nothing(self):
        r = _run(_KEEPALIVES.replace('pv:"P1"', 'pv:"P0"'), before='answer(200,{panes:[],rev:"P1"});', pv="P0", data={})
        self.assertEqual((r["fetches"], r["loaded"]), ([], "P0"), "the route's baked revision; no read")
        self.assertEqual((r["same"], r["sameOffer"]), ([], None))
        self.assertEqual([b["kind"] for b in r["moved"]], ["offer"], r["moved"])


if __name__ == "__main__":
    unittest.main()
