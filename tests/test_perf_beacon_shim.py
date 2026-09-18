#!/usr/bin/env python3
"""The beacon extension's hooks in the pane shim and the shell script (2026-09-18): the marks object the page's collector
reads (window.__rompPerfMarks: the first socket open, the bundle's ready and the first delivered frame, each stamped once;
a running count of received characters; the dist token), and the kill switch the gear's perfMute holds, read from the
store at each row by the shim's send() and by the shell's shellDiag ahead of any send or queue, and again by each open
flush (the shim's onopen and the shell socket's onopen) for the rows that waited in its queue. Source pins over the
rendered shim (km._shim) and the shell script, the way tests/test_kernel_disconnect_banner.py pins the breadcrumb lines;
ui/webview/pane-shim-stale.test.ts runs the shim and exercises both, and tests/test_kernel_mobile.py
(MobileShellDiagExecutes) executes the shell's switch under node, its open flush included. Nothing here starts a kernel."""
import os
import tempfile
import unittest
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")

os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)
load_source("romp_event_model", os.path.join(BIN, "romp-event-model"))
load_source("romp_judge", os.path.join(BIN, "romp-judge"))
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
km = load_source("romp_kernel_beacon_shim", os.path.join(BIN, "romp-kernel"))

READER = "function diagMuted(){try{var st=JSON.parse(localStorage.getItem('romp:settings')||'null');return !!(st&&st.perfMute===true);}catch(e){return false;}}"


class PerfBeaconShimTest(unittest.TestCase):
    def test_the_shim_publishes_the_marks_and_stamps_each_once(self):
        js = km._shim("feed", 1757100000)
        self.assertIn("var PM=window.__rompPerfMarks={wsBytes:0,dv:LOADEDV};", js)
        self.assertIn("var LOADEDV=1757100000;", js, "the dist token the page was served with")
        self.assertLess(js.index("var LOADEDV="), js.index("var PM=window.__rompPerfMarks="), "the token is defined before the marks name it")
        self.assertIn("function pnow(){try{return Math.round(performance.now());}catch(e){return -1;}}", js)
        # the stamps sit on the lines other tests pin, after their pinned prefixes, and fire once (undefined, not falsy: 0 ms is a figure)
        self.assertIn('ws.onopen=function(){lastRecv=Date.now();openT=lastRecv;openSock=this;netState("up");if(PM.wsOpen===undefined)PM.wsOpen=pnow();', js)
        self.assertIn("function deliver(m){if(PM.firstFrame===undefined)PM.firstFrame=pnow();", js)
        self.assertIn('if(m&&m.type==="ready"&&PM.bundleReady===undefined)PM.bundleReady=pnow();', js)
        # every received text frame counts, keepalives included, before the return window's own counter
        self.assertIn("ws.onmessage=function(ev){lastRecv=Date.now();resumeProvisional=0;PM.wsBytes+=(ev.data&&ev.data.length)||0;if(returnAt)returnBytes+=", js)
        self.assertEqual(js.count("__rompPerfMarks"), 1, "one publication")

    def test_the_kill_switch_gates_every_clientDiag_row_before_the_send_and_the_queue(self):
        js = km._shim("feed")
        self.assertIn(READER, js)
        gate = 'if(m&&m.type==="clientDiag"&&diagMuted())return;'
        self.assertIn(gate, js)
        at = js.index(gate)
        send = js.index("function send(m){var s=JSON.stringify(m);")
        self.assertLess(send, at, "inside send(), the one funnel every row of the page passes (the shim's, the reload core's door, a bundle's postMessage)")
        self.assertLess(at, js.index("if(ws&&ws.readyState===1){ws.send(s);return;}", send), "ahead of the socket send")
        self.assertLess(at, js.index('if(m&&m.type==="clientDiag"){if(queuedDiag>=DIAG_QUEUE_MAX)return;queuedDiag++;}', send), "and ahead of the queue")
        # the pinned lines around it are as the other tests know them
        self.assertIn('if(m&&m.type==="ready"){bundleReady=true;readyProto=(m.proto===2?2:1);readyMsg=s;}', js)
        self.assertIn('send({type:"clientDiag",surface:"pane-shim",what:what,', js)
        # the queue's flush at the open re-reads the switch for the clientDiag rows it holds: a mute flipped on while the
        # socket was down would otherwise release the rows queued before it (review find, 2026-09-18)
        self.assertIn('function queuedDiagRow(s){try{var o=JSON.parse(s);return !!(o&&o.type==="clientDiag");}catch(e){return false;}}', js)
        flush = 'var mu=diagMuted();for(var i=0;i<queue.length;i++){if(mu&&queuedDiagRow(queue[i]))continue;ws.send(queue[i]);}'
        self.assertIn(flush, js)
        self.assertLess(js.index("ws.onopen=function(){"), js.index(flush), "inside onopen")
        self.assertLess(js.index(flush), js.index("if(bundleReady&&!readyAcked&&!readyQueued&&readyMsg)ws.send(readyMsg);"), "ahead of the ready's send, which is never a diag row")
        self.assertNotIn("for(var i=0;i<queue.length;i++)ws.send(queue[i]);", js, "no ungated flush remains")

    def test_the_shell_poster_reads_the_same_switch_ahead_of_its_send_and_its_queue(self):
        js = km._LANDING_MOBILE_JS
        self.assertIn(READER, js)
        self.assertIn("function shellDiag(what,data){var m={type:'clientDiag',surface:'shell',what:what,data:data};\nif(diagMuted())return;\n", js)
        self.assertLess(js.index("function diagMuted()"), js.index("function shellDiag("), "defined first")
        self.assertLess(js.index("if(diagMuted())return;"), js.index("if(shellSock&&shellSock.readyState===1){try{shellSock.send(JSON.stringify(m));}catch(e){}}"))
        self.assertLess(js.index("if(diagMuted())return;"), js.index("else if(diagQ.length<DIAGQ_MAX)diagQ.push(m);"))
        # the shell socket's open flush re-reads the switch for the rows it holds: the shim's flush did, the shell's did not (review find, 2026-09-18)
        self.assertIn("shellSock=ws;var q=diagQ;diagQ=[];if(!diagMuted())q.forEach(function(m){try{ws.send(JSON.stringify(m));}catch(e){}});", js)
        self.assertNotIn("diagQ=[];q.forEach(", js, "no ungated flush remains")
        html = km._landing()
        self.assertEqual(html.count(READER), 1, "the shell page carries the reader once (the panes carry their own in the shim)")

    def test_the_kernel_never_reads_the_share_switch(self):
        kernel = open(os.path.join(os.path.dirname(HERE), "kernel", "kernel.py"), encoding="utf-8").read()
        self.assertNotIn("perfShare", kernel, "the share switch is the collector's to read, per page (perf-telemetry.ts)")
        self.assertEqual(kernel.count(READER), 2, "the pane shim's and the shell's readers, byte for byte the same")


if __name__ == "__main__":
    unittest.main()
