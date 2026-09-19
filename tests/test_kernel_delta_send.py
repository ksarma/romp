"""Diff-based delta-send for the chat (the user 2026-06-25, who wanted to stop re-sending what didn't change).

The chat pusher used to send the FULL events array on every change (~8MB for a big transcript). Now the
whole transcript stays resident in the browser (instant scrollback), but a caught-up client receives only
the CHANGED SUFFIX as {type:"chatTail", from, events}. The suffix is found by DIFFING the freshly-built
events against the previous build — robust to _hydrate_postal turning one event into several cards mid-array,
which a fixed window would mishandle. A fresh connect / fork / behind-the-change client still gets the full
{type:"session"} so it always renders from a correct base. Source-level + behavioural pins.
"""
import importlib
import io
import json
import os
import pathlib
import posix
import re
import shutil
import subprocess
import sys
import threading
import time
import types
import unittest
from romp_load import load_source
from unittest import mock
import tempfile

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
km = load_source("romp_kernel", os.path.join(BIN, "romp-kernel"))


def _client():
    sent = []
    return {"send": sent.append, "sent": {}}, sent


def _last(sent):
    return json.loads(sent[-1])


class ChatDiffTest(unittest.TestCase):
    def test_diff_finds_the_exact_changed_suffix(self):
        a = [{"uuid": "1", "x": 1}, {"uuid": "2", "x": 2}]
        self.assertEqual(km._chat_diff([], a), 0, "no prior build → full (from 0)")
        self.assertEqual(km._chat_diff(a, a + [{"uuid": "3"}]), 2, "append → from = old length")
        # a tool output filling an EARLIER card changes that card in place → from = its index
        filled = [{"uuid": "1", "x": 1}, {"uuid": "2", "x": 2, "output": "done"}, {"uuid": "3"}]
        self.assertEqual(km._chat_diff(a + [{"uuid": "3"}], filled), 1, "in-place fill → from = that index")
        self.assertEqual(km._chat_diff(a, list(a)), len(a), "no change → from = length (empty suffix)")

    def test_the_same_list_object_is_answered_without_a_walk(self):
        """The served-tab case: _push re-stores the same events list as the baseline (the cache hit keeps the
        payload, and the non-connect push writes m["events"] back into _prev_chat_events), so the next cycle's
        diff receives ONE object as both arguments. The answer is fixed (len, the empty suffix) and the walk
        that found it visited every event of every served tab per cycle (the design's stage 1 exact return,
        2026-09-18). A list that counts its reads proves the walk is gone: zero reads, where the loop read
        both sides of every index."""
        class Counting(list):
            reads = 0

            def __getitem__(self, i):
                Counting.reads += 1
                return list.__getitem__(self, i)
        same = Counting({"uuid": str(i), "x": i} for i in range(50))
        self.assertEqual(km._chat_diff(same, same), 50, "the empty suffix: from = the length")
        self.assertEqual(Counting.reads, 0, "the same object on both sides is answered without reading an event")
        # the walk stands for everything else: an equal copy is read (identity fails, values compare), and the
        # answer is unchanged
        copy = Counting(same)
        Counting.reads = 0
        self.assertEqual(km._chat_diff(same, copy), 50)
        self.assertEqual(Counting.reads, 100, "a distinct list is still walked, both sides of every index")
        empty = Counting()
        self.assertEqual(km._chat_diff(empty, empty), 0, "no prior build: a full send, as before")


class SendChatTest(unittest.TestCase):
    def _m(self, sid, events):
        return {"type": "session", "id": sid, "name": sid, "events": events,
                "status": {"state": "working"}, "ledger": None, "color": None}

    def test_new_client_gets_the_full_session_then_appends_arrive_as_a_tail(self):
        a = [{"uuid": "1"}, {"uuid": "2"}]
        c, sent = _client()
        km._send_chat(c, self._m("S", a), None, 0, False)             # first send → full
        self.assertEqual(_last(sent)["type"], "session")
        b = a + [{"uuid": "3"}]
        km._send_chat(c, self._m("S", b), None, 2, False)             # caught up, appended → tail from 2
        tail = _last(sent)
        self.assertEqual(tail["type"], "chatTail")
        self.assertEqual(tail["from"], 2)
        self.assertEqual([e["uuid"] for e in tail["events"]], ["3"])
        self.assertEqual(tail["total"], 3)
        self.assertIn("status", tail)                          # the chip rides along on the delta

    def test_a_tool_fill_re_sends_from_that_cards_index(self):
        b = [{"uuid": "1"}, {"uuid": "2"}, {"uuid": "3"}]
        c, sent = _client()
        km._send_chat(c, self._m("S", b), None, 0, False)             # full
        filled = [{"uuid": "1"}, {"uuid": "2", "output": "done"}, {"uuid": "3"}]
        km._send_chat(c, self._m("S", filled), None, 1, False)        # card #2 filled → tail FROM 1
        tail = _last(sent)
        self.assertEqual(tail["type"], "chatTail")
        self.assertEqual(tail["from"], 1)
        self.assertEqual([e.get("output") for e in tail["events"]], ["done", None])

    def test_a_flag_only_change_rides_an_empty_tail_carrying_the_flags(self):
        # the user 2026-09-11: a bell flipped in one split column reached the other only with its next FULL frame.
        # Unchanged events diff to len(prev) → an empty suffix; the flags ride it as the status does
        c, sent = _client()
        a = [{"uuid": "1"}, {"uuid": "2"}]
        km._send_chat(c, self._m("S", a), None, 0, False)             # full
        m2 = dict(self._m("S", a), notify=True, hideFromFeed=False, postalServiceOff=True)
        km._send_chat(c, m2, None, km._chat_diff(a, a), False)
        t = _last(sent)
        self.assertEqual((t["type"], t["from"], t["events"]), ("chatTail", 2, []), "an empty suffix: nothing in the events changed")
        self.assertEqual((t["notify"], t["hideFromFeed"], t["postalServiceOff"]), (True, False, True), "the flags ride the tail")
        n = len(sent)
        km._send_chat(c, dict(m2, notify=False), None, km._chat_diff(a, a), False)
        self.assertEqual((len(sent), _last(sent)["notify"]), (n + 1, False), "the flip alone is a new frame: the dedup signature reads the flags")

    def test_a_flag_only_change_reaches_an_index_client_on_its_uuid_anchored_tail_too(self):
        # the shell's pages speak the uuid-anchored wire (proto 2, T323): the same flip has to ride THAT delta, or another
        # window on the same kernel learns a bell only with the session's next full frame (2026-09-13, found by the served
        # split story's second window)
        c, sent = _client(); c["proto"] = 2
        a = [{"uuid": "1"}, {"uuid": "2"}]
        km._send_chat(c, self._m("S", a), None, 0, False)             # the full frame: the client's base is {first, last}
        self.assertEqual((_last(sent)["type"], _last(sent)["proto"]), ("session", 2))
        m2 = dict(self._m("S", a), notify=True, hideFromFeed=False, postalServiceOff=True)
        km._send_chat(c, m2, None, km._chat_diff(a, a), False)
        t = _last(sent)
        self.assertEqual((t["type"], t["afterUuid"], t["events"]), ("chatTail", "2", []), "an empty suffix after the newest held event")
        self.assertEqual((t["notify"], t["hideFromFeed"], t["postalServiceOff"]), (True, False, True), "the flags ride the uuid-anchored tail")
        n = len(sent)
        km._send_chat(c, dict(m2, notify=False), None, km._chat_diff(a, a), False)
        self.assertEqual((len(sent), _last(sent)["notify"]), (n + 1, False), "the flip alone is a new frame here too")

    def test_a_fork_new_head_uuid_forces_a_full_resend(self):
        c, sent = _client()
        km._send_chat(c, self._m("S", [{"uuid": "1"}, {"uuid": "2"}]), None, 0, False)   # full
        # the tab re-pointed onto a NEW transcript (a /clear-style fork) → first event uuid changes
        km._send_chat(c, self._m("S", [{"uuid": "9"}, {"uuid": "10"}]), None, 0, False)
        self.assertEqual(_last(sent)["type"], "session", "a fork must full-resend, never a tail onto a wrong base")

    def test_a_change_below_the_clients_loaded_tail_forces_a_full(self):
        # the client holds a TAIL starting at headFrom=2 (echat = (tail_head_uuid, headFrom)). A change at
        # index 1 is BELOW its loaded tail → it lacks [1,2) → must full-resend, not tail.
        c, sent = _client()
        evs = [{"uuid": "1"}, {"uuid": "2"}, {"uuid": "3"}, {"uuid": "4"}]
        c["echat"] = {"S": ("3", 2)}                           # holds the tail [2,4): head '3' at index 2
        km._send_chat(c, self._m("S", evs), None, 1, False)           # change_from 1 < headFrom 2 → full
        self.assertEqual(_last(sent)["type"], "session")

    def test_a_big_session_full_send_is_trimmed_to_the_tail_with_an_offset(self):
        evs = [{"uuid": str(i)} for i in range(km.WIRE_TAIL + 50)]    # bigger than the wire tail
        c, sent = _client()
        km._send_chat(c, self._m("S", evs), None, 0, False)
        full = _last(sent)
        self.assertEqual(full["type"], "session")
        self.assertEqual(len(full["events"]), km.WIRE_TAIL, "ship only the last WIRE_TAIL events")
        self.assertEqual(full["headFrom"], 50, "offset = total - WIRE_TAIL (older history lives before it)")
        self.assertEqual(full["headTotal"], km.WIRE_TAIL + 50)
        self.assertEqual(full["events"][0]["uuid"], "50", "the tail starts at headFrom")
        # echat now tracks (tail_head_uuid, headFrom) → a later append delta uses the GLOBAL index
        evs2 = evs + [{"uuid": "NEW"}]
        km._send_chat(c, self._m("S", evs2), None, len(evs), False)   # appended at global index = old total
        tail = _last(sent)
        self.assertEqual(tail["type"], "chatTail")
        self.assertEqual(tail["from"], len(evs), "the tail's `from` is the GLOBAL index, mapped by the browser")
        self.assertEqual([e["uuid"] for e in tail["events"]], ["NEW"])

    def test_the_top_level_git_branch_survives_the_tail_trim(self):
        # Regression (the user 2026-06-30): the status-bar branch + tab tooltip read a TOP-LEVEL gitBranch field,
        # never the head system event. The system event lives at events[0]; a >WIRE_TAIL session ships only the
        # last WIRE_TAIL events, so that head event (and its branch) fell off the wire → the branch vanished on
        # every long session. A top-level field is not part of the windowed events, so it must always ride along.
        evs = [{"uuid": str(i)} for i in range(km.WIRE_TAIL + 50)]    # bigger than the wire tail
        m = self._m("S", evs); m["gitBranch"] = "main"
        c, sent = _client()
        km._send_chat(c, m, None, 0, False)
        full = _last(sent)
        self.assertEqual(len(full["events"]), km.WIRE_TAIL, "events are still trimmed to the tail")
        self.assertEqual(full.get("gitBranch"), "main", "the top-level branch rides along even when trimmed")

    def test_a_small_session_under_the_tail_is_sent_whole(self):
        evs = [{"uuid": "1"}, {"uuid": "2"}]
        c, sent = _client()
        km._send_chat(c, self._m("S", evs), None, 0, False)
        full = _last(sent)
        self.assertEqual(full["type"], "session")
        self.assertNotIn("headFrom", full, "a session that fits under WIRE_TAIL is sent whole, no offset")

    def test_the_ledger_rides_the_tail_only_when_it_changed(self):
        # the ledger (goal tree, tens of KB) only changes on a judge pass, so it must NOT ride every 0.5s delta
        a = [{"uuid": "1"}, {"uuid": "2"}]
        c, sent = _client()
        km._send_chat(c, self._m("S", a), None, 0, False)                  # full → carries the ledger
        km._send_chat(c, self._m("S", a + [{"uuid": "3"}]), None, 2, False)   # only an event appended
        self.assertEqual(_last(sent)["type"], "chatTail")
        self.assertNotIn("ledger", _last(sent), "an unchanged ledger does NOT ride every delta")
        km._send_chat(c, self._m("S", a + [{"uuid": "3"}, {"uuid": "4"}]), None, 3, True)   # judge pass
        self.assertIn("ledger", _last(sent), "a changed ledger DOES ride the delta")


class RenderHandlesTheTail(unittest.TestCase):
    def _render(self):
        import pathlib
        return (pathlib.Path(BIN).parent / "ui" / "webview" / "render.ts").read_text()

    def test_render_truncates_to_from_appends_and_repaints_from_the_changed_point(self):
        r = self._render()
        self.assertIn('else if (m.type === "chatTail") chatTail(m);', r)       # dispatched
        self.assertIn("from = (msg.from | 0) - (s.headFrom || 0);", r)   # GLOBAL index → resident-tail local
        # The two rejection cases split on 2026-07-28. Below the loaded head → still a quiet return (the
        # resident tail is fine). A GAP (from past what we hold) → ask for a full session: "wait for the
        # next full" was a promise nothing kept, and the tab froze there until its socket dropped.
        self.assertIn("if (from < 0) return;", r)
        # the gap check runs in KERNEL coordinates — the client's injected optimistic tail is not part
        # of the kernel's index space, and counting it masked genuine gaps (the user 2026-08-09)
        self.assertIn("if (from > kernelLen) {", r)
        self.assertIn('requestFullSession(msg.id, "gap");', r)   # 2026-09-07: the ask names its reason (skeleton tabs)
        self.assertIn("s.events.length = from;", r)                            # truncate the superseded tail
        self.assertIn("for (const e of (msg.events || [])) s.events.push(e);", r)  # append the suffix
        self.assertIn("v.rendered = Math.min(v.rendered, from);", r)           # repaint from the exact change

    def test_render_handles_a_partial_session_and_streams_older_in(self):
        r = self._render()
        # upsert records the wire offset → s.events is the tail [headFrom, headTotal); an empty frame for a held
        # transcript keeps the resident window instead (T249b, frame-merge.ts)
        self.assertIn("headFrom: kept && prev ? prev.headFrom : (msg.headFrom ?? 0),", r)
        # scroll to the top of the resident tail with older on the server → request the previous chunk
        self.assertIn('vscodeApi?.postMessage({ type: "loadOlder", id: sid, before: s.proto === 2 ? s.firstUuid : s.headFrom });', r)
        # …only on an upward or unchanged move of the view (T366: a downward flick inside the estimate's top band never asks)
        self.assertIn("if (gesture) v.edgeUp = olderRequestAllowed(v.edgeTop, st);", r)
        self.assertIn("const upward = v.edgeUp !== false;", r)
        self.assertIn("if (moreOnServer && (v.winStart ?? 0) === 0 && st < topH + edgePx && upward) { requestOlder(", r)
        # chatHead PREPENDS the chunk + lowers headFrom + re-anchors
        self.assertIn('else if (m.type === "chatHead") chatHead(m);', r)
        self.assertIn("if (older.length) s.events = older.concat(s.events);", r)
        self.assertIn("s.headFrom = from;", r)


class _StatInterceptor:
    """Counts, from OUTSIDE the kernel, every os.stat, os.lstat and DirEntry.stat made on the calling thread while the
    kernel's chat signature is open (km._CHAT_SIG_TL.active), so a test can assert memos.chatSig.stats equals what ran:
    counting wrappers around whatever os.stat and os.lstat currently are (the kernel's own wrappers), set on the os
    module and the posix module as two distinct objects (so a stat that reached the kernel only through the posix module,
    importlib's, is told apart: `posix_stat`), on pathlib's accessor where Python 3.10 has one, and an os.scandir whose
    entries count their .stat() before delegating (a DirEntry stats in C and reaches no wrapper; the kernel's door for it
    is _entry_stat). Nothing of the kernel is mocked: the wrappers see exactly the calls the kernel's do, and a hit is
    recorded only while the signature is open on the calling thread, so the harness's own stats outside a signature are
    not counted. A context manager; everything is restored on exit (the regression-1 exactness rule, 2026-09-19)."""

    def __init__(self, tl):
        self.tl = tl
        self.stat = self.posix_stat = self.lstat = self.dirent = 0

    @property
    def total(self):
        return self.stat + self.posix_stat + self.lstat + self.dirent

    def _wrap(self, real, field):
        def counting(path, *a, **kw):
            if getattr(self.tl, "active", False):          # getattr: the first cut's plain thread-local had no default
                setattr(self, field, getattr(self, field) + 1)
            return real(path, *a, **kw)
        counting.__wrapped__ = real
        return counting

    def __enter__(self):
        self.saved = (os.stat, os.lstat, posix.stat, posix.lstat, os.scandir)
        self.acc = getattr(pathlib, "_NormalAccessor", None)
        if self.acc is not None:
            self.saved_acc = (self.acc.__dict__.get("stat"), self.acc.__dict__.get("lstat"))
        st, lst = self._wrap(os.stat, "stat"), self._wrap(os.lstat, "lstat")
        os.stat, os.lstat = st, lst
        posix.stat, posix.lstat = self._wrap(posix.stat, "posix_stat"), self._wrap(posix.lstat, "lstat")
        if self.acc is not None:
            self.acc.stat, self.acc.lstat = staticmethod(st), staticmethod(lst)
        real_scandir, me = self.saved[4], self

        class Entry:
            def __init__(self, e):
                self._e = e

            def stat(self, **kw):
                if getattr(me.tl, "active", False):
                    me.dirent += 1
                return self._e.stat(**kw)

            def __getattr__(self, name):
                return getattr(self._e, name)

            def __fspath__(self):
                return self._e.path

        class Scan:
            def __init__(self, it):
                self._it = it

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return self._it.__exit__(*a)

            def __iter__(self):
                return self

            def __next__(self):
                return Entry(next(self._it))

            def close(self):
                self._it.close()
        os.scandir = lambda *a, **kw: Scan(real_scandir(*a, **kw))
        return self

    def __exit__(self, *a):
        os.stat, os.lstat, posix.stat, posix.lstat, os.scandir = self.saved
        if self.acc is not None:
            for name, val in zip(("stat", "lstat"), self.saved_acc):
                if val is None:
                    delattr(self.acc, name)
                else:
                    setattr(self.acc, name, val)
        return False


def _git(*args, cwd=None):
    """A git call for a fixture repository, hermetic of the machine's identity and config."""
    env = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_AUTHOR_NAME="tester",
               GIT_AUTHOR_EMAIL="tester@example.com", GIT_COMMITTER_NAME="tester", GIT_COMMITTER_EMAIL="tester@example.com")
    subprocess.run(["git", "-c", "init.defaultBranch=main"] + list(args), cwd=cwd, env=env, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _plain_repo_and_worktree(td):
    """(main clone, worktree) made by git under `td`: a committed plain repository and a worktree branched off it, each
    with two immediate subdirectories, so _repo_index_key has DirEntry stats to make and _tree_of both shapes to verdict."""
    main, wt = os.path.join(td, "main"), os.path.join(td, "wt")
    os.mkdir(main)
    _git("init", "-q", cwd=main)
    with open(os.path.join(main, "notes.txt"), "w") as f:
        f.write("x\n")
    _git("add", "notes.txt", cwd=main)
    _git("commit", "-q", "-m", "first", cwd=main)
    _git("worktree", "add", "-q", "-b", "side", wt, cwd=main)
    for top in (main, wt):
        for d in ("src", "docs"):
            os.mkdir(os.path.join(top, d))
    return main, wt


class ByteIdenticalFrames(unittest.TestCase):
    """The stage 1 exact return in _chat_diff (2026-09-18) may skip work only where the output is unchanged: this
    runs the same six pusher cycles twice, once with a verbatim copy of the walk it replaced and once with the
    kernel's own, and compares the raw wire strings every client received. Chat, feed and timeline clients
    together, so the feed's card order and columns are in the comparison too (the cards rule). Synthetic only:
    placeholder ids, the notes-api demo world, TESTHOST."""

    SID = "11111111-2222-4333-8444-000000000918"
    NOW = 1781400000

    @staticmethod
    def _chat_diff_reference(prev, cur):
        # the walk as it stood before the exact return, verbatim
        if not prev:
            return 0
        n = min(len(prev), len(cur))
        i = 0
        while i < n:
            a, b = prev[i], cur[i]
            if a is not b and a != b:
                break
            i += 1
        return i

    def _ev(self, i, output=None):
        e = {"kind": "assistant", "uuid": "11111111-2222-4333-8444-00000000b%03d" % i, "md": "reply %d" % i}
        if output is not None:
            e["output"] = output
        return e

    def _session(self, events):
        return {"type": "session", "id": self.SID, "name": "web", "color": None, "events": events,
                "status": {"state": "ready"}, "ledger": None}

    def _card(self, i, text=None):
        t = self.NOW - i * 60
        return {"itemId": "%s:g%d" % (self.SID, i), "sid": self.SID, "name": "web", "color": None,
                "text": text or "Synthetic goal %d on the notes-api board" % i, "t": t, "live": True,
                "trgb": [10, 20, 30], "column": "working", "summary": "s" * 40, "tree": []}

    def _feed(self, build_id, asks):
        return {"type": "feed", "asks": asks, "now": self.NOW, "buildId": build_id, "order": [self.SID],
                "working": ["web"], "awaiting": [], "sessions": [{"sid": self.SID, "name": "web", "color": None}],
                "userTodos": {}, "views": {}, "clearNotices": [], "syncNotices": [], "sdkNotices": [],
                "selfHost": "TESTHOST"}

    def _timeline(self, nbars, now):
        turns = {self.SID: [{"id": "b%d" % i, "t": i, "end": i + 1, "open": False} for i in range(nbars)]}
        return {"type": "timeline", "sessions": [{"id": self.SID, "name": "web"}], "turns": turns,
                "judging": {}, "messages": [], "now": now}

    def _script(self):
        """(build_session frame, feed, timeline) per cycle. The SAME session frame object twice in a row is the
        served tab: _push writes its events list back as the baseline, so the next diff sees one object on both
        sides (the exact return's case); a new list is a rebuild with an appended tail, then an in-place fill."""
        e1, e2, e3 = self._ev(1), self._ev(2), self._ev(3)
        a = self._session([e1, e2])
        b = self._session([e1, e2, e3])
        c = self._session([e1, self._ev(2, output="done"), e3])
        asks1 = [self._card(i) for i in range(4)]
        asks2 = [self._card(i, text="changed" if i == 2 else None) for i in range(4)]
        f1, f2 = self._feed(1, asks1), self._feed(2, asks2)
        t1, t2 = self._timeline(2, 1), self._timeline(3, 2)
        return [(a, f1, t1), (a, f1, t1), (b, f1, t1), (b, f1, t1), (c, f1, t1), (c, f2, t2)]

    def _run(self, diff, perf=None, build=None, tolerate=(), between=None, furnish=None, live_rows=True, script=None):
        """Six cycles; returns (the raw wire strings per client, whether the diff met one object on both sides per
        cycle, and with `perf` a _PerfStats each cycle's stage split, the cycle opened and closed on this thread).
        `build` replaces build_session's body (frame -> the session dict, or a raise); `tolerate` names stderr lines
        the run expects (a failed build's own report); `between`, when given, is called with the cycle's index before
        each cycle's push (the census tests move a client's skeleton set between cycles); `furnish`, when given, is
        called with (the temp dir, the transcript path, the session row) once the transcript exists and before any
        push, to build the world a signature reads (the stats exactness test); `live_rows` False hands the push an
        EMPTY liveness map (a tab with no live row: the census's no-live-row case); `script` replaces _script()."""
        sid = self.SID
        td = tempfile.TemporaryDirectory(); self.addCleanup(td.cleanup)
        path = os.path.join(td.name, sid + ".jsonl")
        with open(path, "w") as f:
            f.write("{}\n")
        sess = {"sid": sid, "name": "web", "anchor": None, "path": path, "mtime": self.NOW}
        live = {sid: {"state": "waiting", "color": "#888888", "since": self.NOW - 60, "model": "", "effort": "",
                      "context": None, "backend": "sdk"}} if live_rows else {}
        if furnish is not None:
            furnish(td.name, path, sess)
        wire = {"chat": [], "feed": [], "timeline": []}
        clients = [{"app": app, "alive": True, "sent": {}, "delta": app != "chat", "caps": set(),
                    "send": (lambda s, app=app: wire[app].append(s))} for app in ("chat", "feed", "timeline")]
        # the same cold module state for both runs
        for d in (km._prev_chat_events, km._prev_chat_ledger, km._built_chat):
            d.pop(sid, None)
        km._EMPTY_BUILD_NOTED.discard(sid)
        km._last_tab_order[:] = []
        saved = (km._feed_wire, km._bars_wire, km._skel_wire, dict(km._delta_parts_cache), dict(km._delta_split_memo),
                 km._feed_cards_memo, list(km._built_timeline))
        km._feed_wire = km._bars_wire = km._skel_wire = None
        km._delta_parts_cache.clear(); km._delta_split_memo.clear(); km._feed_cards_memo = None

        def restore():
            km._feed_wire, km._bars_wire, km._skel_wire = saved[:3]
            km._delta_parts_cache.clear(); km._delta_parts_cache.update(saved[3])
            km._delta_split_memo.clear(); km._delta_split_memo.update(saved[4])
            km._feed_cards_memo = saved[5]; km._built_timeline[:] = saved[6]
            for d in (km._prev_chat_events, km._prev_chat_ledger, km._built_chat):
                d.pop(sid, None)
        self.addCleanup(restore)
        same_object_calls = []

        def spy(prev, cur):
            same_object_calls.append(prev is not None and prev is cur)
            return diff(prev, cur)
        world = {}
        err = io.StringIO()
        with mock.patch.object(km, "_chat_diff", spy), \
                mock.patch.object(km, "_alive_sessions", lambda now, tm: [dict(sess)]), \
                mock.patch.object(km, "_chat_tab_sessions", lambda now, tm: [dict(sess)]), \
                mock.patch.object(km, "_warm_fleet_bg", lambda now: None), \
                mock.patch.object(km, "_live_map", lambda: dict(live)), \
                mock.patch.object(km, "build_session", lambda sid, now, live_map=None, **kw: (build or dict)(world["frame"])), \
                mock.patch.object(km, "_cached_feed", lambda now, live_map, sig, connect=False: world["feed"]), \
                mock.patch.object(km, "_cached_timeline", lambda now, live_map, sig, connect=False: world["timeline"]), \
                mock.patch.object(km, "build_timeline", lambda now, live_map, with_bars=True, live_only=False: world["timeline"]), \
                mock.patch.object(km, "_fleet_view_sig", lambda now, live_map: ("sig",)), \
                mock.patch.object(km, "_DELTA_MAX_FRACTION", 10.0), \
                mock.patch.object(sys, "stderr", err):
            builds, rows = [], []
            for i, (frame, feed, timeline) in enumerate(script if script is not None else self._script()):
                if between is not None:
                    between(i)
                if not builds or builds[-1] is not frame:      # a new frame is a rebuild: the transcript's stat moves,
                    builds.append(frame)                        # so the tab's signature misses and build_session runs;
                    os.utime(path, (self.NOW, self.NOW + len(builds)))   # a repeat is the served tab (the cache hit)
                world.update(frame=frame, feed=feed, timeline=timeline)
                km._built_timeline[:] = [None, timeline, time.time(), time.time()]
                if perf is not None:
                    perf.cycle_begin()
                t0 = time.monotonic()
                km._push(clients, live_map=live)
                if perf is not None:
                    perf.cycle(time.monotonic() - t0)
                    rows.append(perf.snapshot()["pusher"]["stageRing"][-1]["stages"])
        for line in err.getvalue().splitlines():
            if any(t in line for t in tolerate):
                continue
            self.assertNotIn("push build:", line, "a cycle raised: %s" % err.getvalue())
            self.assertNotIn("push send", line, "a send raised: %s" % err.getvalue())
        return wire, same_object_calls, rows

    def test_the_frames_every_client_receives_are_byte_identical_with_and_without_the_exact_return(self):
        before, calls_before, _ = self._run(self._chat_diff_reference)
        after, calls_after, _ = self._run(km._chat_diff)
        self.assertEqual(after, before, "the same wire strings, per client, across the six cycles")
        self.assertEqual(calls_after, calls_before, "the diff met the same arguments in the same order")
        self.assertEqual(calls_after, [False, True, False, True, False, True],
                         "the served-tab case (one list on both sides) on every repeat cycle, a walk on every rebuild")
        types = lambda strings: [json.loads(s)["type"] for s in strings]
        chat = types(after["chat"])
        self.assertEqual(chat.count("session"), 1, "the full session went once, to the fresh client: %r" % chat)
        tails = [json.loads(s) for s in after["chat"] if json.loads(s)["type"] == "chatTail"]
        self.assertEqual([(t["from"], len(t["events"])) for t in tails], [(2, 0), (2, 1), (3, 0), (1, 2), (3, 0)],
                         "the served tab's empty suffix after the full, the appended event, the served tab again, the "
                         "in-place fill's two, the served tab once more")
        self.assertIn("feed", types(after["feed"]))
        self.assertIn("delta", types(after["feed"]), "the changed card crossed as a delta, so the card path is in the comparison")
        self.assertIn("bars", types(after["timeline"]))
        self.assertIn("delta", types(after["timeline"]), "the appended bar crossed as a delta")
        feed_frames = [json.loads(s) for s in after["feed"]]
        first = [f for f in feed_frames if f["type"] == "feed"][0]
        self.assertEqual([a["column"] for a in first["asks"]], ["working"] * 4, "no card moved column")
        self.assertEqual([a["itemId"] for a in first["asks"]], ["%s:g%d" % (self.SID, i) for i in range(4)], "nor order")

    def _identities(self, d, b0, b1):
        """The two reconciliation identities the block comment, the docstring row and docs/reference.md state, checked from
        the payload alone over a window (`d` the memos.chatSig deltas, `b0` and `b1` the builds.chat blocks at its ends),
        and the two counts they lean on returned: (cached, built). pre = cached + built - targetedBuilds + failedBuilds over
        any window; post = built - targetedBuilds - nosig over a window with failedBuilds 0, and otherwise post exceeds
        that by at most failedBuilds (the failed builds whose signature was also None: nosig counts those tabs, built does
        not)."""
        cached, built = b1["cached"] - b0["cached"], b1["built"] - b0["built"]
        self.assertEqual(d["pre"], cached + built - d["targetedBuilds"] + d["failedBuilds"],
                         "pre = builds.chat cached + built - targetedBuilds + failedBuilds: %r" % (d,))
        residual = d["post"] - (built - d["targetedBuilds"] - d["nosig"])
        if d["failedBuilds"] == 0:
            self.assertEqual(residual, 0, "post = built - targetedBuilds - nosig over a window with no failed build: %r" % (d,))
        else:
            self.assertGreaterEqual(residual, 0)
            self.assertLessEqual(residual, d["failedBuilds"], "post exceeds built - targetedBuilds - nosig by at most failedBuilds: %r" % (d,))
        return cached, built

    def _spy_compares(self, pairs):
        """Patches the three counted reads' notes to record each compare's two operands (the cached signature and the fresh
        one) in `pairs`, for the operand-derived identical-components expectation; returns the patch contexts."""
        real_note, real_cmp = km._chat_sig_note_pre, km._chat_sig_note_compare

        def note(sid, sig, hit, watched, held_live, tabs):
            if hit is not None and sig is not None:
                pairs.append((hit[0], sig))
            return real_note(sid, sig, hit, watched, held_live, tabs)

        def cmp_(hit, sig):
            if hit is not None and sig is not None:
                pairs.append((hit[0], sig))
            return real_cmp(hit, sig)
        return mock.patch.object(km, "_chat_sig_note_pre", note), mock.patch.object(km, "_chat_sig_note_compare", cmp_)

    def test_the_signature_counters_move_with_the_push_loop(self):
        """Stage 1 of the chat-signature design (2026-09-18): memos.chatSig counts what the push loop does. Six cycles over
        one tab, rebuilt and served alternately: pre = the six pre-build signatures, post = the three post-build ones,
        the two identities checked from the payload alone (_identities: no targeted push, no failed build, no nosig),
        pushes = 6 (one per push that ran the chat loop), compares = 7 (derived below), stats equal to an outside count of
        the stats the signatures made (the exactness rule; the furnished-world test holds the wider claim), one registry
        read per signature, and no census count with no chat client registered (the harness's clients are the push's
        targets, not connected clients). The identical-components count is pinned from the compares' own operands, not
        from a fixed label set: whether the two empty tails are one object between two signatures differs by CPython
        version (3.10 no, 3.12 and 3.13 yes; the comment at the pin says why), so only the four values every CPython keeps
        as one object are pinned by label."""
        ps = km._PERF_STATS
        pairs = []
        p1, p2 = self._spy_compares(pairs)
        before, b0 = km._chat_sig_stats_report(), ps.snapshot()["builds"]["chat"]
        with p1, p2, _StatInterceptor(km._CHAT_SIG_TL) as ic:
            _wire, calls, _rows = self._run(km._chat_diff, perf=ps)
        self.assertEqual(calls, [False, True, False, True, False, True], "premise: rebuilt, served, alternating")
        after, b1 = km._chat_sig_stats_report(), ps.snapshot()["builds"]["chat"]
        d = {k: after[k] - before[k] for k in after}
        cached, built = self._identities(d, b0, b1)
        self.assertEqual((cached, built), (3, 3))
        self.assertEqual((d["nosig"], d["failedBuilds"], d["targetedBuilds"]), (0, 0, 0))
        self.assertEqual(d["pre"], 6, "one pre-build signature per tab per push"); self.assertEqual(d["post"], 3)
        self.assertEqual(d["pushes"], 6, "one per push that ran the chat tab loop")
        # compares counts every cache READ that met an entry with a signature in hand: the pre-flight read of each of the
        # three served cycles (1, 3, 5), and for each of the two warm rebuilds (cycles 2 and 4) its pre-flight read AND its
        # re-read under the claim, both meeting the stale entry; the cold first cycle meets nothing. 3 + 2 * 2 = 7. The final
        # compare re-evaluates the last read's operands and is not a read, so it counts nothing (counting it would read 10 here).
        self.assertEqual(d["compares"], 3 + 2 * 2, "three served pre-flight reads plus two per warm rebuild (pre-flight and the claim re-read)")
        self.assertGreater(d["compares"], cached, "compares can exceed the served count (a rebuild counts two)")
        # compareIdenticalComponents is the count the reads' operands give, pinned from them (2026-09-18 review, medium 7): the
        # components the two signatures hold as ONE object against those rebuilt per signature (a fresh stat pair, a tuple
        # of them), at every position whether or not the tuple compare reached it (a rebuild's operands differ at position 0,
        # the transcript, with identical components after it, so a count that stopped at the first unequal position would
        # read short). Pinned by label below are only the four values every CPython keeps as one object: the two bools
        # (needs, floor), the None postal and the small-int downtime. The two empty tails (taskout, pathlink) are NOT
        # pinned: each is built by tuple() over a generator on exactly one side of the compare (pl_at in _chat_build_deps
        # on the cached side, touts in _chat_sig_deps on the fresh side), and tuple() over an empty generator returns a
        # fresh empty tuple on CPython 3.10 and the shared empty tuple on 3.12 and 3.13 (measured 2026-09-19).
        self.assertEqual(len(pairs), 7, "the note spies saw one operand pair per counted read")
        expected = sum(sum(1 for a, b in zip(old, new) if a is b) for old, new in pairs)
        self.assertEqual(d["compareIdenticalComponents"], expected)
        self.assertGreater(expected, 0)
        self.assertLessEqual(d["compareIdenticalComponents"], d["compares"] * len(km._CHAT_SIG_LABELS),
                             "the share's denominator: compares * len(_CHAT_SIG_LABELS), both operands full-length")
        share = d["compareIdenticalComponents"] / (d["compares"] * len(km._CHAT_SIG_LABELS))
        self.assertTrue(0.0 < share < 1.0, "the derived share is a fraction: %r" % share)
        for old, new in pairs:
            self.assertEqual((len(old), len(new)), (len(km._CHAT_SIG_LABELS),) * 2, "both operands are full-length signatures")
            same = {lab for lab, a, b in zip(km._CHAT_SIG_LABELS, old, new) if a is b}
            self.assertTrue({"needs", "floor", "postal", "downtime"} <= same,
                            "the two bools, the None postal and the small-int downtime are one object: %r" % sorted(same))
            self.assertFalse({"transcript", "states"} & same, "a stat pair is built per signature, never the same object")
        # stats is what the signatures made, counted from outside by execution (the exactness rule, 2026-09-19): every os.stat,
        # os.lstat and DirEntry.stat while a signature was open, whoever made it; the furnished-world test below exercises
        # every channel, this bare world holds the equality on the loop's own signatures
        self.assertEqual(d["stats"], ic.total, "memos.chatSig.stats equals the stats intercepted inside the nine signatures: %r"
                         % {"stat": ic.stat, "posix": ic.posix_stat, "lstat": ic.lstat, "dirent": ic.dirent})
        self.assertGreaterEqual(d["stats"], 7 * (d["pre"] + d["post"]), "at least the seven stats the first cut counted per signature")
        self.assertEqual(d["regReads"], d["pre"] + d["post"], "one registry read per signature")
        self.assertEqual(d["thread"], 0, "no comments store: no thread signature")
        self.assertEqual(d["waited"], 0)
        self.assertEqual((d["warmEligible"], d["warmBlockedByOutline"], d["heldBody"]), (0, 0, 0), "no connected chat client: no census")

    def _connected(self, **kw):
        """A connected chat client (in km._clients) that the targeted push may send to: ready, proto 2, a send sink."""
        frames = []
        c = dict({"app": "chat", "alive": True, "sent": {}, "skeleton": set(), "proto": 2, "ready": True, "handshake": True,
                  "send": lambda s: frames.append(json.loads(s)), "_frames": frames}, **kw)
        return c

    def _window(self, **kw):
        """One six-cycle run with the memos.chatSig and builds.chat deltas returned as (d, b0, b1)."""
        ps = km._PERF_STATS
        before, b0 = km._chat_sig_stats_report(), ps.snapshot()["builds"]["chat"]
        _wire, calls, _rows = self._run(km._chat_diff, perf=ps, **kw)
        after, b1 = km._chat_sig_stats_report(), ps.snapshot()["builds"]["chat"]
        return {k: after[k] - before[k] for k in after}, b0, b1, calls

    def test_the_identities_hold_across_a_targeted_push_watched_and_unwatched(self):
        """Window (2) of the identities (2026-09-19 review, extra5-1): the targeted push (_push_session_now) builds without a
        signature, so its build counts under builds.chat built and under targetedBuilds, the term both identities subtract.
        builds.chat labels it `targeted` only when the tab is unwatched (a watched tab's targeted build lands in active_built
        with no label), which is why targetedBuilds is published: without it the identity would ask the reader to subtract
        a number /perf does not publish for the watched case. Driven from `between` at cycle 5 with one connected chat
        client, once unwatched and once watching the tab: targetedBuilds 1 either way, pre 6 = 3 + 4 - 1 + 0, post 3 = 4 - 1 - 0."""
        for watched in (False, True):
            with self.subTest(watched=watched):
                c = self._connected(**({"active": self.SID} if watched else {}))

                def between(i, c=c):
                    if i == 5:
                        km._push_session_now(self.SID)
                with mock.patch.object(km, "_clients", [c]):
                    d, b0, b1, calls = self._window(between=between)
                self.assertEqual(calls, [False, True, False, True, False, True], "the targeted push caches nothing: the loop's cycles are unchanged")
                cached, built = self._identities(d, b0, b1)
                self.assertEqual((cached, built), (3, 4), "three loop rebuilds and the targeted push's build")
                self.assertEqual((d["targetedBuilds"], d["failedBuilds"], d["nosig"]), (1, 0, 0))
                self.assertEqual((d["pre"], d["post"]), (6, 3))
                self.assertEqual(b1["bg_miss"].get("targeted", 0) - b0["bg_miss"].get("targeted", 0), 0 if watched else 1,
                                 "builds.chat labels the targeted build only when the tab is unwatched (the label appears at its first use)")
                self.assertEqual(b1["active_built"] - b0["active_built"], 1 if watched else 0,
                                 "a watched tab's targeted build lands in active_built with no label")
                self.assertIn(self.SID, {f["id"] for f in c["_frames"] if f["type"] == "session"}, "the targeted push sent the tab")

    def test_the_identities_hold_when_every_build_raises(self):
        """Window (3): a build that raises past its pre-build signature is counted under neither builds.chat cached nor
        built, and before failedBuilds the pre identity was short by every such build (6 against 0 here). failedBuilds 6,
        pre 6 = 0 + 0 - 0 + 6, post 0."""
        saved = dict(km._chat_build_faults)
        self.addCleanup(lambda: (km._chat_build_faults.clear(), km._chat_build_faults.update(saved)))
        km._chat_build_faults.pop(self.SID, None)

        def build(frame):
            raise RuntimeError("synthetic build failure")
        d, b0, b1, calls = self._window(build=build, tolerate=("push build: chat ",))
        self.assertEqual(calls, [], "no build ever stored")
        cached, built = self._identities(d, b0, b1)
        self.assertEqual((cached, built), (0, 0), "a raised build is under neither")
        self.assertEqual((d["pre"], d["post"], d["nosig"], d["failedBuilds"], d["targetedBuilds"]), (6, 0, 0, 6, 0))

    def test_the_post_identity_bound_holds_when_the_signature_and_the_build_raise(self):
        """Window (4): the signature raises (nosig, the tab built uncached) AND the build raises (failedBuilds). built is 0
        and nosig 6, so built - targetedBuilds - nosig reads -6 against a post of 0: the identity is stated over a window
        with failedBuilds 0, and otherwise as a bound, post exceeding it by at most failedBuilds. Here the excess is exactly
        6, the failed builds whose signature was also None."""
        saved = (dict(km._chat_build_faults), dict(km._chat_sig_faults))
        self.addCleanup(lambda: (km._chat_build_faults.clear(), km._chat_build_faults.update(saved[0]),
                                 km._chat_sig_faults.clear(), km._chat_sig_faults.update(saved[1])))
        km._chat_build_faults.pop(self.SID, None); km._chat_sig_faults.pop(self.SID, None)

        def build(frame):
            raise RuntimeError("synthetic build failure")

        def sig(*a, **kw):
            raise RuntimeError("synthetic signature failure")
        with mock.patch.object(km, "_chat_build_sig", sig):
            d, b0, b1, calls = self._window(build=build, tolerate=("push build: chat",))
        cached, built = self._identities(d, b0, b1)
        self.assertEqual((cached, built), (0, 0))
        self.assertEqual((d["pre"], d["post"], d["nosig"], d["failedBuilds"], d["targetedBuilds"]), (6, 0, 6, 6, 0))
        self.assertEqual(d["post"] - (built - d["targetedBuilds"] - d["nosig"]), 6, "the stated excess: the failed builds whose signature was None")

    def test_stats_counts_every_stat_a_signature_makes_by_execution(self):
        """The exactness test (2026-09-19 review, regression-1: the first cut's per-site count saw 7 of about 23 stats per
        signature and named a closed exclusion list that omitted six paths). memos.chatSig.stats must equal, over a real
        push, an OUTSIDE count of every os.stat, os.lstat and DirEntry.stat made while a signature was open (_StatInterceptor:
        wrappers around the kernel's own on the os and posix modules, a counting os.scandir; nothing of the kernel mocked),
        over a world furnished so every channel runs: a transcript, a states file, the store triple, a working note, a git
        worktree as the session's cwd with a CLAUDE.md on its chain (the cwd memos, _repo_index_key and _claudemd_key stat),
        a task store directory with one task file (a DirEntry.stat through _entry_stat), a messages.jsonl and a postal card
        (the postal key stats in the tail), and the transcript's checkpoint path (a realpath: lstats). One fresh module
        import is forced inside the first signature: importlib stats through the posix module, so the equality holds only
        with the posix wrap in place. Pinned: the equality, at least twenty stats per signature, and each channel seen
        (lstat, DirEntry, posix). At the first cut this read 63 counted against about 200 intercepted over nine
        signatures; restoring per-site counting alone (narrower) or re-adding one site count (wider) reds it."""
        ps = km._PERF_STATS
        cfg = tempfile.TemporaryDirectory(); self.addCleanup(cfg.cleanup)
        if shutil.which("git") is None:
            self.skipTest("the furnished world needs git for the worktree cwd")
        mod_dir = os.path.join(cfg.name, "mods"); os.mkdir(mod_dir)
        mod_name = "romp_probe_fresh_import_%d_%d" % (os.getpid(), threading.get_ident())
        with open(os.path.join(mod_dir, mod_name + ".py"), "w") as f:
            f.write("x = 1\n")
        self.addCleanup(lambda: sys.modules.pop(mod_name, None))
        imports = []
        real_pins = km._pinned_notes_fp

        def pins_and_one_import(sid):
            if not imports:                              # once, inside the first signature: eight stats through posix.stat
                sys.path.insert(0, mod_dir)
                try:
                    imports.append(importlib.import_module(mod_name))
                finally:
                    sys.path.remove(mod_dir)
            return real_pins(sid)
        card = {"kind": "postal-service", "uuid": "11111111-2222-4333-8444-00000000c001", "md": "a note from api"}
        with_card = {}

        def carded(fr):                                  # the same frame OBJECT stays one object: the served-tab premise
            if id(fr) not in with_card:
                with_card[id(fr)] = dict(fr, events=list(fr["events"]) + [card])
            return with_card[id(fr)]
        script = [(carded(fr), feed, tl) for fr, feed, tl in self._script()]

        def furnish(td, path, sess):
            jd = km.jd
            for d in (jd.STATESDIR, jd.GOALDIR, jd.GOALARCHDIR, jd._overrides_dir(), km.WORKING_DIR, km.NAMES, jd.STATE / "timeline"):
                d.mkdir(parents=True, exist_ok=True)
            (jd.STATESDIR / (self.SID + ".jsonl")).write_text(json.dumps({"t": self.NOW - 30, "state": "idle"}) + "\n")
            (jd.GOALDIR / (self.SID + ".json")).write_text(json.dumps({"rompUuid": self.SID, "nodes": {}, "status": {}}))
            (jd._overrides_dir() / (self.SID + ".jsonl")).write_text("")
            (jd.GOALARCHDIR / (self.SID + ".json")).write_text(json.dumps({"rompUuid": self.SID, "nodes": {}}))
            (km.WORKING_DIR / self.SID).write_text("the notes-api web tier\n")
            (jd.STATE / "timeline" / "messages.jsonl").write_text(json.dumps(
                {"ev": "sent", "id": "m1", "from": "api", "from_id": self.SIDS_PEER, "to": "web", "to_id": self.SID,
                 "body": "hello", "kind": "coordinate", "t": self.NOW}) + "\n")
            main, wt = _plain_repo_and_worktree(td)
            with open(os.path.join(wt, "CLAUDE.md"), "w") as f:
                f.write("# notes-api\n")
            (km.NAMES / self.SID).write_text("web\t%s\t#abcdef\n" % wt)
            tasks = os.path.join(cfg.name, "tasks", self.SID); os.makedirs(tasks)
            with open(os.path.join(tasks, "1.json"), "w") as f:
                f.write(json.dumps({"id": "1", "subject": "write the notes-api docs", "status": "pending"}))
        before, b0 = km._chat_sig_stats_report(), ps.snapshot()["builds"]["chat"]
        with mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": cfg.name}), mock.patch.object(km, "_pinned_notes_fp", pins_and_one_import), \
                _StatInterceptor(km._CHAT_SIG_TL) as ic:
            _wire, calls, _rows = self._run(km._chat_diff, perf=ps, furnish=furnish, script=script)
        after, b1 = km._chat_sig_stats_report(), ps.snapshot()["builds"]["chat"]
        d = {k: after[k] - before[k] for k in after}
        self.assertEqual(calls, [False, True, False, True, False, True], "premise: rebuilt, served, alternating")
        self.assertEqual(len(imports), 1, "the fresh import ran once, inside the first signature")
        n_sigs = d["pre"] + d["post"] + d["thread"]
        self.assertEqual(n_sigs, 9, "six pre-build and three post-build signatures, no thread")
        seen = {"stat": ic.stat, "posix": ic.posix_stat, "lstat": ic.lstat, "dirent": ic.dirent}
        self.assertEqual(d["stats"], ic.total, "memos.chatSig.stats equals every stat intercepted inside the %d signatures: %r" % (n_sigs, seen))
        self._identities(d, b0, b1)
        self.assertGreaterEqual(ic.total / n_sigs, 20, "the world is not empty: at least twenty stats per signature (%r)" % (seen,))
        self.assertGreater(ic.lstat, 0, "the lstat channel ran (a realpath's per-component lstats)")
        self.assertGreater(ic.dirent, 0, "the DirEntry channel ran (the task store's one file, through _entry_stat)")
        self.assertGreater(ic.posix_stat, 0, "the posix-module channel ran (the fresh import's path finder)")
        self.assertEqual(d["regReads"], n_sigs, "one registry read per signature")

    SIDS_PEER = "11111111-2222-4333-8444-000000000919"

    def test_a_comment_threads_signature_counts_its_stats_by_the_same_rule(self):
        """The third caller of _chat_build_sig (_thread_events, deps=False) folds its stats through the same scope: the
        thread signature's count equals the outside count, and it is a thread signature (thread 1), not a loop count."""
        tsid = self.SIDS_PEER
        td = tempfile.TemporaryDirectory(); self.addCleanup(td.cleanup)
        path = os.path.join(td.name, tsid + ".jsonl")
        with open(path, "w") as f:
            f.write("{}\n")
        sess = {"sid": tsid, "name": "api", "anchor": None, "path": path, "mtime": self.NOW}
        saved = dict(km._built_thread)
        self.addCleanup(lambda: (km._built_thread.clear(), km._built_thread.update(saved), km._thread_fold_keep[1].discard(tsid)))
        km._built_thread.pop(tsid, None)
        with mock.patch.object(km, "_thread_reg", lambda t: {}), mock.patch.object(km, "_sdk_sess", lambda sid, now: dict(sess)), \
                mock.patch.object(km, "build_session", lambda sid, now, live_map=None, **kw: {"type": "session", "id": sid, "events": []}):
            before = km._chat_sig_stats_report()
            with _StatInterceptor(km._CHAT_SIG_TL) as ic:
                evs = km._thread_events(tsid, None, self.NOW, {})
            after = km._chat_sig_stats_report()
        self.assertEqual(evs, [])
        d = {k: after[k] - before[k] for k in after}
        self.assertEqual(d["thread"], 1, "one thread signature")
        self.assertEqual(d["stats"], ic.total, "its stats, whoever made them: %r" % {"stat": ic.stat, "posix": ic.posix_stat, "lstat": ic.lstat, "dirent": ic.dirent})
        self.assertGreaterEqual(d["stats"], 7)
        self.assertEqual((d["pre"], d["post"], d["pushes"], d["compares"]), (0, 0, 0, 0), "not a loop count")

    def test_the_warm_tab_census_counts_by_what_the_connected_clients_hold(self):
        """The census the warm-tab gate question needs (the design's dropped alternative, kept as a count): a cached tab
        every connected chat client holds as a skeleton and no client watches is warmEligible; the same tab with a plain
        Outline pane connected is warmBlockedByOutline; a tab a client holds as a body (the watched tab included) is
        heldBody. The first cycle builds the tab while the client still holds it whole (else the cold gate would skip it
        and it would never be warm); the client's skeleton set gains the sid before the second."""
        ps = km._PERF_STATS
        keys = ("warmEligible", "warmBlockedByOutline", "heldBody")

        def scenario(clients, between=None):
            before, c0 = km._chat_sig_stats_report(), ps.snapshot()["builds"]["chat"]["coldSkipped"]
            with mock.patch.object(km, "_clients", clients):
                _wire, calls, _rows = self._run(km._chat_diff, perf=ps, between=between)
            self.assertEqual(calls, [False, True, False, True, False, True], "the census changes no build: rebuilt, served, alternating")
            self.assertEqual(ps.snapshot()["builds"]["chat"]["coldSkipped"], c0, "no tab was cold-skipped")
            after = km._chat_sig_stats_report()
            return tuple(after[k] - before[k] for k in keys)

        def client(**kw):
            return dict({"app": "chat", "alive": True, "sent": {}, "skeleton": set(), "proto": 2, "ready": True, "handshake": True}, **kw)
        held = client()
        def skeleton_from_cycle_1(i):
            if i == 1:
                held["skeleton"] = {self.SID}
        self.assertEqual(scenario([held], skeleton_from_cycle_1), (5, 0, 1),
                         "warm from cycle 1 on and held as a skeleton: eligible five times; held as a body on cycle 0")
        held = client()
        self.assertEqual(scenario([held, {"app": "fleet", "alive": True, "sent": {}}], skeleton_from_cycle_1), (0, 5, 1),
                         "a plain Outline pane blocks the gate: the same five count under warmBlockedByOutline")
        self.assertEqual(scenario([client(active=self.SID)]), (0, 0, 6), "a watched tab is a body every cycle")

    def test_the_census_counts_a_warm_skeleton_tab_with_no_live_row_which_the_gate_would_not_skip(self):
        """The warmEligible gloss (2026-09-19 review, regression-4): the census is the cold gate's predicate with its
        not-yet-built clause negated and WITHOUT the gate's live-row clause. The gate skips only a tab whose liveness row
        exists (no row: no status to state, so it builds); the census counts a cached skeleton tab with no row too. With the
        live map EMPTY and the connected page holding the tab as a skeleton from cycle 1, the tab is never cold-skipped and
        warmEligible reads 5: the excess the wording names (a dead session reopened read-only). Adding the live-row term to
        the census predicate reads 0 here."""
        ps = km._PERF_STATS
        held = {"app": "chat", "alive": True, "sent": {}, "skeleton": set(), "proto": 2, "ready": True, "handshake": True}

        def skeleton_from_cycle_1(i):
            if i == 1:
                held["skeleton"] = {self.SID}
        before, c0 = km._chat_sig_stats_report(), ps.snapshot()["builds"]["chat"]["coldSkipped"]
        with mock.patch.object(km, "_clients", [held]):
            _wire, calls, _rows = self._run(km._chat_diff, perf=ps, between=skeleton_from_cycle_1, live_rows=False)
        after = km._chat_sig_stats_report()
        self.assertEqual(calls, [False, True, False, True, False, True], "no live row: built as before, then served")
        self.assertEqual(ps.snapshot()["builds"]["chat"]["coldSkipped"], c0, "the gate never skipped it: it has no live row to state")
        self.assertEqual(after["warmEligible"] - before["warmEligible"], 5, "the census counts it warm on every cached cycle, live row or none")
        self.assertEqual(after["heldBody"] - before["heldBody"], 1, "a body on the first cycle, before the page held it")

    def test_the_census_reads_each_clients_skeleton_set_once_per_push_not_once_per_tab(self):
        """The census's skeleton question is answered from one read of every connected chat client per push
        (_skeleton_census, after the tab loop), not by asking _held_as_skeleton_by_all per tab as the first cut did: over
        six pushes with one connected page the by-all walk runs once, for the cold gate on the first cycle (the tab not
        yet built), and the census helper once per push, over the tabs the gate did not walk (2026-09-18 review, low 2;
        the four-tab pin that tells once-per-push from once-per-tab lives in tests/test_cold_tab_gate.py)."""
        ps = km._PERF_STATS
        by_all, census = [], []
        real_by_all, real_census = km._held_as_skeleton_by_all, km._skeleton_census

        def spy_by_all(sid, clients):
            by_all.append(sid); return real_by_all(sid, clients)

        def spy_census(sids, clients):
            census.append(list(sids)); return real_census(sids, clients)
        held = {"app": "chat", "alive": True, "sent": {}, "skeleton": set(), "proto": 2, "ready": True, "handshake": True}

        def skeleton_from_cycle_1(i):
            if i == 1:
                held["skeleton"] = {self.SID}
        before = km._chat_sig_stats_report()
        with mock.patch.object(km, "_clients", [held]), mock.patch.object(km, "_held_as_skeleton_by_all", spy_by_all), \
                mock.patch.object(km, "_skeleton_census", spy_census):
            _wire, calls, _rows = self._run(km._chat_diff, perf=ps, between=skeleton_from_cycle_1)
        after = km._chat_sig_stats_report()
        self.assertEqual(calls, [False, True, False, True, False, True], "premise: rebuilt, served, alternating")
        self.assertEqual(by_all, [self.SID], "the by-all walk ran once: the cold gate's, on the first cycle, before the tab was built")
        self.assertEqual(census, [[]] + [[self.SID]] * 5,
                         "the census helper ran once per push, over the tabs the gate did not walk: none on the cold first cycle "
                         "(the gate asked), the tab on the five warm ones (kernel-3, 2026-09-19: the question is asked once per tab per push)")
        self.assertEqual(tuple(after[k] - before[k] for k in ("warmEligible", "warmBlockedByOutline", "heldBody")), (5, 0, 1),
                         "...and the census reads the same as before the change")

    def test_reads_inside_a_signature_are_counted_and_the_same_reads_outside_one_are_not(self):
        """The read counters are gated to a signature (the thread-local scope _chat_build_sig opens): the names read in
        _sdk_transcript_path, the switch read in _user_todos_on and sdk_backend.read_reg count inside one and not
        outside, and regReads equals the read_reg calls the signature made (a dead tab's queue fallbacks included)."""
        td = tempfile.TemporaryDirectory(); self.addCleanup(td.cleanup)
        path = os.path.join(td.name, self.SID + ".jsonl")
        with open(path, "w") as f:
            f.write("{}\n")
        sess = {"sid": self.SID, "name": "web", "anchor": None, "path": path, "mtime": self.NOW}
        self.assertTrue(km._sdk(), "premise: the SDK backend module loads (its read_reg is the counted reader)")
        sb = sys.modules["romp_sdk_backend"]
        real_read_reg = sb.read_reg
        reg_calls = []

        def read_reg(state_dir, sid):
            reg_calls.append(sid); return real_read_reg(state_dir, sid)
        empty_stamp = ((None, None, None, None, ()), frozenset(), ())

        def stamp(sid):
            km._sdk_transcript_path(sid); return empty_stamp

        def todo_fp(sid):
            km._user_todos_on(); return None

        def launch(sid, be=None):
            sb.read_reg(km.jd.STATE, str(sid)); return None
        with mock.patch.object(sb, "read_reg", read_reg), mock.patch.object(km, "_session_stamp_read", stamp), \
                mock.patch.object(km, "_user_todo_fp", todo_fp), mock.patch.object(km, "_launch_error", launch), \
                mock.patch.object(km._live_scope, "names", {}, create=True):   # a names snapshot: _names_parts reads no file
            before = km._chat_sig_stats_report()
            km._sdk_transcript_path(self.SID); km._user_todos_on(); sb.read_reg(km.jd.STATE, self.SID); km._chat_ident(path)
            self.assertEqual(km._chat_sig_stats_report(), before, "outside a signature the readers count nothing")
            del reg_calls[:]
            with _StatInterceptor(km._CHAT_SIG_TL) as ic:
                sig = km._chat_build_sig(sess, None, self.NOW, live_map={})
            after = km._chat_sig_stats_report()
            first_reg = list(reg_calls)                     # the first signature's read_reg calls (the next signature adds its own)
            with mock.patch.object(km._live_scope, "names", None):   # no snapshot on the thread: _names_parts reads the file
                b2 = km._chat_sig_stats_report()
                km._chat_build_sig(sess, None, self.NOW, live_map={})
                a2 = km._chat_sig_stats_report()
        self.assertEqual(a2["namesReads"] - b2["namesReads"], 2,
                         "with no names snapshot: the stamp's read and _names_parts's fallback read (2026-09-18 review, low 14)")
        self.assertIsNotNone(sig)
        d = {k: after[k] - before[k] for k in after}
        self.assertEqual(d["namesReads"], 1, "the stamp read's names read, and no other")
        self.assertEqual(d["switchReads"], 1)
        self.assertEqual(d["regReads"], len(first_reg), "every read_reg the signature made: %r" % (first_reg,))
        self.assertGreaterEqual(d["regReads"], 1)
        # stats is every stat the signature made, counted from outside by execution (2026-09-19 review, regression-1): the first
        # cut's literal ten (the transcript, the states file, the archive, episodes and gone identities, the working note's,
        # one CLAUDE.md on the chain and the three shared identities outside a push) named the sites this file owned and
        # missed the helpers' (the store identity's three, the task store's, the registry's), so the pin is the equality
        self.assertEqual(d["stats"], ic.total, "every stat the signature made, whoever made it: %r"
                         % {"stat": ic.stat, "posix": ic.posix_stat, "lstat": ic.lstat, "dirent": ic.dirent})
        self.assertGreaterEqual(d["stats"], 10, "at least the ten the first cut counted")
        self.assertEqual((d["pre"], d["post"], d["compares"], d["pushes"]), (0, 0, 0, 0), "a signature outside the push loop is not a loop count")

    def test_the_frames_are_byte_identical_with_the_signature_counters_disabled(self):
        """The counters are measurement: with every counting site a no-op and the thread-CPU clock absent the six cycles
        produce the same wire strings for every client (the stage 1 invariant: no frame or read changes)."""
        live, calls_live, _ = self._run(km._chat_diff)
        noop = lambda *a, **k: None
        with mock.patch.object(km, "_chat_sig_count", noop), mock.patch.object(km, "_chat_sig_bump", noop), \
                mock.patch.object(km, "_chat_sig_note_pre", noop), mock.patch.object(km, "_chat_sig_note_compare", noop), \
                mock.patch.object(km, "_chat_sig_note_census", noop), mock.patch.object(km, "_thread_cpu", lambda: None):
            off, calls_off, _ = self._run(km._chat_diff)
        self.assertEqual(off, live, "the same wire strings, per client, with the counters off")
        self.assertEqual(calls_off, calls_live)
        # the census branch (2026-09-18 review, low 13): the same comparison with a connected chat page that holds the tab as
        # a skeleton from the second cycle on (the branch the run above never reaches with no connected client), the census
        # read switched off with the counters
        held = {"app": "chat", "alive": True, "sent": {}, "skeleton": set(), "proto": 2, "ready": True, "handshake": True}

        def between(i):
            held["skeleton"] = {self.SID} if i >= 1 else set()
        with mock.patch.object(km, "_clients", [held]):
            live2, calls_live2, _ = self._run(km._chat_diff, between=between)
            with mock.patch.object(km, "_chat_sig_count", noop), mock.patch.object(km, "_chat_sig_bump", noop), \
                    mock.patch.object(km, "_chat_sig_note_pre", noop), mock.patch.object(km, "_chat_sig_note_compare", noop), \
                    mock.patch.object(km, "_chat_sig_note_census", noop), mock.patch.object(km, "_thread_cpu", lambda: None), \
                    mock.patch.object(km, "_skeleton_census", lambda sids, clients: None):
                off2, calls_off2, _ = self._run(km._chat_diff, between=between)
        self.assertEqual(calls_live2, [False, True, False, True, False, True], "the census changed no build")
        self.assertEqual(off2, live2, "...and the same wire strings with a connected page whose skeleton set the census reads")
        self.assertEqual(calls_off2, calls_live2)

    def test_the_signature_seam_is_split_into_its_static_and_deps_sub_seams(self):
        """Stage 1 of the chat-signature design (2026-09-18): push.chat.sig is a container of push.chat.sig.static (the
        signature less its dependency tail) and push.chat.sig.deps (the tail _chat_sig_deps evaluates), in stages_ms, in
        stages_cpu_ms and in the cycle's split. Every pre-build signature records both (a cold tab's tail runs and answers
        empty); the post-build one, deps=False, records static alone: a served tab closes static once and deps once, a
        rebuilt tab static twice and deps once, and per row the two sum to the seam within rounding."""
        ps = km._PERF_STATS
        names = []
        real_stage = ps.stage

        def stage(name, dt, cpu=None):
            names.append(name); return real_stage(name, dt, cpu=cpu)
        before = ps.snapshot()
        with mock.patch.object(ps, "stage", stage):
            _wire, calls, rows = self._run(km._chat_diff, perf=ps)
        after = ps.snapshot()
        self.assertEqual(calls, [False, True, False, True, False, True], "premise: rebuilt, served, alternating")
        for k in ("push.chat.sig.static", "push.chat.sig.deps"):
            self.assertIn(k, before["stages_ms"], "%s is listed at zero from the start" % k)
            self.assertGreater(after["stages_ms"][k], before["stages_ms"][k], "%s moved" % k)
            self.assertIn(k, after["stages_cpu_ms"] or {k: None}, "%s has a CPU row where the platform has the clock" % k)
        self.assertAlmostEqual(after["stages_ms"]["push.chat.sig"] - before["stages_ms"]["push.chat.sig"],
                               sum(after["stages_ms"][k] - before["stages_ms"][k] for k in ("push.chat.sig.static", "push.chat.sig.deps")),
                               places=6, msg="the two sub-seams are the seam, cumulatively")
        for i, row in enumerate(rows):
            self.assertIn("push.chat.sig.static", row, "cycle %d" % i); self.assertIn("push.chat.sig.deps", row, "cycle %d" % i)
            self.assertLessEqual(abs(row["push.chat.sig"]["ms"] - row["push.chat.sig.static"]["ms"] - row["push.chat.sig.deps"]["ms"]), 0.2,
                                 "cycle %d: the split's rows sum within their rounding (%r)" % (i, {k: v["ms"] for k, v in row.items() if k.startswith("push.chat.sig")}))
        # the closes per cycle, in the order the seam close records them
        cycles, cur = [], []
        for n in names:
            if n == "push.chat":
                cycles.append(cur); cur = []
            elif n.startswith("push.chat.sig"):
                cur.append(n)
        self.assertEqual(len(cycles), 6)
        for i, seen in enumerate(cycles):
            served = calls[i]
            self.assertEqual(seen.count("push.chat.sig.static"), 1 if served else 2, "cycle %d: %r" % (i, seen))
            self.assertEqual(seen.count("push.chat.sig.deps"), 1, "cycle %d: the tail runs once, in the pre-build signature: %r" % (i, seen))
            self.assertEqual(seen[:3], ["push.chat.sig.static", "push.chat.sig.deps", "push.chat.sig"], "cycle %d: the sub-seams close before the seam: %r" % (i, seen))

    def test_the_chat_seams_record_their_thread_cpu_from_a_bounded_number_of_rusage_reads(self):
        """Stage 1 of the chat-signature design (2026-09-18): the chat loop reads getrusage(RUSAGE_THREAD) at each seam's
        open and close and stages_cpu_ms carries the delta beside the wall. Under a fake clock that advances one ms of
        user and half a ms of system time per read: every signature seam moves the sig row by at least one read's worth,
        the send row moves too, the container's CPU covers its seams, and the reads per cycle stay within the stated
        bound (two per mark: the container, the signature and its deps sub-seam, the send; a rebuild adds the build seam
        and the post-build signature; the harness's own snapshot may add one)."""
        ps = km._PERF_STATS
        reads = []

        def fake(who):
            reads.append(who)
            return types.SimpleNamespace(ru_utime=0.001 * len(reads), ru_stime=0.0005 * len(reads), ru_maxrss=0)
        before = ps.snapshot()["stages_cpu_ms"]
        with mock.patch.object(km, "_RUSAGE_THREAD", 11), mock.patch.object(km.resource, "getrusage", fake):
            _wire, calls, rows = self._run(km._chat_diff, perf=ps)
            after = ps.snapshot()["stages_cpu_ms"]
        self.assertEqual(calls, [False, True, False, True, False, True], "premise: rebuilt, served, alternating")
        self.assertEqual(reads, [11] * len(reads), "every read asked for the thread's rusage")
        self.assertLessEqual(len(reads), 6 * 16, "at most sixteen reads per cycle: %d over six" % len(reads))
        d = {k: {c: after[k][c] - before[k][c] for c in ("user", "sys")} for k in after if k in before}
        self.assertGreaterEqual(d["push.chat.sig"]["user"], 9 * 1.0 - 1e-6, "nine signatures, each at least one read apart")
        self.assertAlmostEqual(d["push.chat.sig"]["sys"], d["push.chat.sig"]["user"] / 2.0, msg="the fake's ratio survives the fold")
        self.assertGreater(d["push.chat.send"]["user"], 0.0)
        self.assertGreater(d["push.chat.build"]["user"], 0.0)
        self.assertGreaterEqual(d["push.chat"]["user"] + 1e-6, sum(d[k]["user"] for k in ("push.chat.sig", "push.chat.build", "push.chat.send")),
                                "the container's CPU covers its seams")
        # the sub-seams' CPU (2026-09-18 review, low 12): static is the seam's CPU net of the deps tail, so the two sum to the
        # seam exactly. Under the fake clock a pre-build signature is three reads apart (the tail's pair inside the seam's
        # pair) and a post-build one a single read, so over six pre and three post: sig 21, deps 6, static 15, in ms of user
        for c, per_read in (("user", 1.0), ("sys", 0.5)):
            self.assertAlmostEqual(d["push.chat.sig.static"][c] + d["push.chat.sig.deps"][c], d["push.chat.sig"][c], places=6,
                                   msg="%s: static plus deps is the seam" % c)
            self.assertAlmostEqual(d["push.chat.sig"][c], 21 * per_read, places=6, msg=c)
            self.assertAlmostEqual(d["push.chat.sig.deps"][c], 6 * per_read, places=6, msg=c)
            self.assertAlmostEqual(d["push.chat.sig.static"][c], 15 * per_read, places=6, msg=c)
        for row in rows:
            self.assertEqual(set(row["push.chat.sig"]), {"ms", "bytes", "hydrated"}, "the split's rows carry no CPU column")

    def test_the_chat_stage_is_split_into_its_seams(self):
        """Stage 1 of the incremental-push design (2026-09-18): push.chat is a container of three seams in stages_ms
        and in the cycle's split: sig (the tab's signature, every tab every cycle, the post-build one included),
        build (build_session, a rebuild only) and send (the diff and the per-client sends). A served tab records
        sig and send and no build."""
        ps = km._PERF_STATS
        seams = ("push.chat.sig", "push.chat.build", "push.chat.send")
        before = ps.snapshot()["stages_ms"]
        for k in seams:
            self.assertIn(k, before, "%s is listed at zero from the start" % k)
        _wire, calls, rows = self._run(km._chat_diff, perf=ps)
        self.assertEqual(calls, [False, True, False, True, False, True], "premise: rebuilt, served, rebuilt, served, rebuilt, served")
        for i, row in enumerate(rows):
            chat = sorted(k for k in row if k.startswith("push.chat"))
            if calls[i]:
                self.assertNotIn("push.chat.build", chat, "cycle %d served the tab: no build seam (%r)" % (i, chat))
                self.assertIn("push.chat.sig", chat); self.assertIn("push.chat.send", chat)
            else:
                self.assertEqual([k for k in chat if k in seams], sorted(seams), "cycle %d rebuilt: every seam (%r)" % (i, chat))
            self.assertIn("push.chat", chat, "the container closes every cycle")
        after = ps.snapshot()["stages_ms"]
        for k in seams:
            self.assertGreater(after[k], before[k], "%s moved" % k)
        self.assertGreaterEqual(after["push.chat"] - before["push.chat"] + 1e-6, sum(after[k] - before[k] for k in seams),
                                "the seams sit inside the container's wall time")

    def test_a_build_that_raises_records_its_build_seam_and_no_send(self):
        """A build_session that raises is build time too: the tab's per-build guard records push.chat.build before it
        skips the tab, beside the signature it took; no frame, so no send seam (2026-09-18 review, medium 6)."""
        ps = km._PERF_STATS
        saved = dict(km._chat_build_faults)
        self.addCleanup(lambda: (km._chat_build_faults.clear(), km._chat_build_faults.update(saved)))
        km._chat_build_faults.pop(self.SID, None)

        def build(frame):
            raise RuntimeError("synthetic build failure")
        reads = []

        def fake(who):
            reads.append(who)
            return types.SimpleNamespace(ru_utime=0.001 * len(reads), ru_stime=0.0005 * len(reads), ru_maxrss=0)
        before = ps.snapshot()["stages_ms"]
        with mock.patch.object(km, "_RUSAGE_THREAD", 11), mock.patch.object(km.resource, "getrusage", fake):
            before_cpu = ps.snapshot()["stages_cpu_ms"]["push.chat.build"]
            wire, calls, rows = self._run(km._chat_diff, perf=ps, build=build, tolerate=("push build: chat ",))
            after_cpu = ps.snapshot()["stages_cpu_ms"]["push.chat.build"]
        self.assertAlmostEqual(after_cpu["user"] - before_cpu["user"], 6.0, places=6,
                               msg="the failed build's CPU is build CPU too (2026-09-18 review, low 15): one read pair per failed build, six cycles")
        self.assertAlmostEqual(after_cpu["sys"] - before_cpu["sys"], 3.0, places=6)
        self.assertEqual(calls, [], "no build ever stored: the diff never ran")
        self.assertEqual(len(rows), 6)
        for i, row in enumerate(rows):
            chat = sorted(k for k in row if k.startswith("push.chat"))
            self.assertIn("push.chat.sig", chat, "cycle %d: the signature was taken (%r)" % (i, chat))
            self.assertIn("push.chat.build", chat, "cycle %d: the failed build's time is build time (%r)" % (i, chat))
            self.assertNotIn("push.chat.send", chat, "cycle %d: no frame, no send (%r)" % (i, chat))
            self.assertIn("push.chat", chat)
        after = ps.snapshot()["stages_ms"]
        self.assertGreater(after["push.chat.build"], before["push.chat.build"])
        kinds = [json.loads(s)["type"] for s in wire["chat"]]
        self.assertNotIn("session", kinds); self.assertNotIn("chatTail", kinds)

    def test_a_rebuild_closes_the_sig_seam_twice_and_a_served_tab_once(self):
        """The post-build signature (the check that the static components held across the build) is signature time
        too: a rebuilt tab closes push.chat.sig twice, before and after build_session, a served tab once
        (2026-09-18 review, medium 6: the seams test alone could not tell the two apart)."""
        ps = km._PERF_STATS
        names = []
        real_stage, real_begin = ps.stage, ps.cycle_begin

        def stage(name, dt, cpu=None):
            names.append(name); return real_stage(name, dt, cpu=cpu)   # cpu: the seams' thread-CPU delta (stages_cpu_ms, 2026-09-18)

        def begin(*a, **kw):
            names.append(None); return real_begin(*a, **kw)
        with mock.patch.object(ps, "stage", stage), mock.patch.object(ps, "cycle_begin", begin):
            _wire, calls, rows = self._run(km._chat_diff, perf=ps)
        self.assertEqual(calls, [False, True, False, True, False, True], "premise: rebuilt, served, alternating")
        cycles, cur = [], None
        for n in names:
            if n is None:
                cur = []; cycles.append(cur)
            else:
                cur.append(n)
        self.assertEqual(len(cycles), 6)
        for i, seen in enumerate(cycles):
            served = calls[i]
            self.assertEqual(seen.count("push.chat.sig"), 1 if served else 2,
                             "cycle %d (%s): the pre-build signature, and the post-build one on a rebuild (%r)"
                             % (i, "served" if served else "rebuilt", seen))
            self.assertEqual(seen.count("push.chat.build"), 0 if served else 1)
            self.assertEqual(seen.count("push.chat.send"), 1)
            self.assertEqual(seen.count("push.chat"), 1)


class _CountingLock:
    """Stands in for a client's slot RLock (`dlock`, what _client_lock returns): counts the holds."""

    def __init__(self):
        self.holds = 0

    def __enter__(self):
        self.holds += 1

    def __exit__(self, *a):
        return False


class ChatSigHelpers(unittest.TestCase):
    """memos.chatSig's pieces on their own (stage 1 of the chat-signature design): the warm-tab census's once-per-push
    skeleton read, the per-tab note's clauses, and a stat site's count. Synthetic ids only."""

    SIDS = ["11111111-2222-4333-8444-0000000009%02d" % i for i in range(6)]

    def _client(self, **kw):
        return dict({"app": "chat", "alive": True, "sent": {}, "dlock": _CountingLock()}, **kw)

    def test_the_skeleton_census_answers_the_by_all_question_per_tab_from_one_hold_per_client(self):
        """_skeleton_census(sids, clients) is {sid for which _held_as_skeleton_by_all(sid, clients)} over the same client
        shapes (a set holder, a reconnecting page with a watched tab, a relay diet page with none, a page whose echat
        already holds a tab), taking each client's slot lock ONCE for any number of tabs; None with no client, so the
        note can tell "no connected chat client" from "held by none"."""
        s = self.SIDS
        clients = [self._client(skeleton={s[0], s[1], s[2], s[3]}),
                   self._client(reconnect=True, active=s[0], echat={s[3]: 1}),          # holds every tab but its watched one and the one it has
                   self._client(skeletonOnReady=True, dietSkeleton=True, kind="relay")]  # a relay diet page with no watched tab: every tab
        expected = {x for x in s if km._held_as_skeleton_by_all(x, clients)}
        self.assertEqual(expected, {s[1], s[2]}, "premise: the by-all walk's own answer over these clients")
        for c in clients:
            c["dlock"].holds = 0
        self.assertEqual(km._skeleton_census(s, clients), expected)
        self.assertEqual([c["dlock"].holds for c in clients], [1, 1, 1], "one hold per client for six tabs")
        self.assertIsNone(km._skeleton_census(s, []), "no connected chat client: None, not an empty set")
        self.assertEqual(km._skeleton_census(s, [self._client()]), set(), "a page with no diet holds nothing as a skeleton")
        self.assertEqual(km._skeleton_census([], clients), set())

    def test_the_note_and_the_census_count_a_cached_skeleton_tab_as_warm_only_while_its_transcript_exists(self):
        """The warm-tab gate's clauses, on the per-tab note (_chat_sig_note_pre: pre, nosig, the compare, the tab's row) and
        the once-per-push fold (_chat_sig_note_census: warmEligible, warmBlockedByOutline, heldBody), the same eight rows the
        note carried alone before the census moved after the loop (kernel-3, 2026-09-19): a cached tab every page holds as a
        skeleton counts under warmEligible when the signature's transcript component is a stat pair, and under neither
        warmEligible nor heldBody when it is None (the file is gone: the cold gate's os.path.exists clause, read off the
        signature instead of a second stat). A watched tab is a body whatever the set says; with no connected chat client
        the census counts nothing (2026-09-18 review, low 16). Two more rows: where the cold gate walked the tab, its live
        answer stands and the census is not asked about that tab."""
        sid = self.SIDS[0]
        n = len(km._CHAT_SIG_LABELS)
        with_file = ((1.0, 3),) + (None,) * (n - 1)
        no_file = (None,) * n
        hit = (with_file, {"events": []}, None, None)
        keys = ("pre", "nosig", "compares", "warmEligible", "warmBlockedByOutline", "heldBody")
        asked = []
        real_census = km._skeleton_census

        def spy(sids, clients):
            asked.append(list(sids)); return real_census(sids, clients)

        def delta(sig, hit, watched, clients, plain_outline=False, held_live=None):
            tabs = []
            before = km._chat_sig_stats_report()
            with mock.patch.object(km, "_skeleton_census", spy):
                km._chat_sig_note_pre(sid, sig, hit, watched, held_live, tabs)
                km._chat_sig_note_census(tabs, clients, plain_outline)
            after = km._chat_sig_stats_report()
            return tuple(after[k] - before[k] for k in keys)
        holder = [self._client(skeleton={sid})]
        self.assertEqual(delta(with_file, hit, False, holder), (1, 0, 1, 1, 0, 0), "cached, unwatched, held, with a transcript: warm")
        self.assertEqual(delta(no_file, hit, False, holder), (1, 0, 1, 0, 0, 0), "the transcript gone: neither warm nor a body")
        self.assertEqual(delta(with_file, hit, False, holder, True), (1, 0, 1, 0, 1, 0), "a plain Outline connected: blocked, not eligible")
        self.assertEqual(delta(with_file, hit, True, holder), (1, 0, 1, 0, 0, 1), "watched: a body, whatever the set says")
        self.assertEqual(delta(with_file, hit, False, [self._client()]), (1, 0, 1, 0, 0, 1), "held by none of the connected pages: a body")
        self.assertEqual(delta(with_file, hit, False, []), (1, 0, 1, 0, 0, 0), "no connected chat client: no census count")
        self.assertEqual(delta(with_file, None, False, holder), (1, 0, 0, 0, 0, 0), "no cached build: cold, not warm, and no compare")
        self.assertEqual(delta(None, hit, False, holder), (1, 1, 0, 0, 0, 0), "no signature: nosig, no compare, not warm")
        self.assertEqual(asked, [[sid]] * 8, "the gate walked none of these (held_live None): the census asked about the tab each time")
        del asked[:]
        self.assertEqual(delta(with_file, None, False, [self._client()], held_live=True), (1, 0, 0, 0, 0, 0),
                         "the gate found every page holding it: a skeleton, so not a body, and not warm (the gate walks only unbuilt tabs)")
        self.assertEqual(delta(with_file, hit, False, holder, held_live=False), (1, 0, 1, 0, 0, 1),
                         "the gate found a page not holding it: a body, though the set holds it by the time of the fold")
        self.assertEqual(asked, [[], []], "the census is asked about nothing the gate walked")

    def test_the_repo_index_key_counts_its_own_bodys_stats_exactly(self):
        """_repo_index_key's OWN body's share of memos.chatSig.stats, with the tree helpers (_tree_of, _git_head_file)
        STUBBED so only the body runs: each stat counted as it is attempted (a stat of a missing file is a syscall too),
        one per immediate subdirectory (a DirEntry stat, through _entry_stat), one for the tree's own mtime, and one for
        the git index only when the tree has a git dir to hold one. The first cut counted the subdirectories plus two
        whatever `gi` said, a phantom stat per signature for a tree with no git dir (2026-09-18 review, low 4). The
        helpers' own stats are counted too, by the wrapper wherever they run; the real-helper case below holds that
        (2026-09-19 review, extra5-2: this test's stubs could not see them)."""
        td = tempfile.TemporaryDirectory(); self.addCleanup(td.cleanup)
        for d in ("a", "b"):
            os.mkdir(os.path.join(td.name, d))
        with open(os.path.join(td.name, "notes.txt"), "w") as f:
            f.write("x\n")

        def key_and_stats(head):
            with mock.patch.object(km, "_tree_of", lambda d: (td.name, "main")), \
                    mock.patch.object(km, "_git_head_file", lambda tree: head):
                before = km._chat_sig_stats_report()["stats"]
                with km._chat_sig_scope():
                    key = km._repo_index_key(td.name)
                return key, km._chat_sig_stats_report()["stats"] - before
        key, n = key_and_stats("")
        self.assertEqual(n, 3, "two subdirectory stats and the tree's mtime: no git dir, no index stat")
        self.assertIsNone(key[0]); self.assertEqual([s[0] for s in key[2]], ["a", "b"])
        gitdir = os.path.join(td.name, ".git")
        os.mkdir(gitdir)
        open(os.path.join(gitdir, "index"), "w").close()
        key, n = key_and_stats(os.path.join(gitdir, "HEAD"))
        self.assertEqual(n, 4, "...plus the index's mtime when the tree has a git dir (.git itself is not a counted subdirectory)")
        self.assertIsNotNone(key[0])
        # a stat that raises is a stat that was attempted: the HEAD path names a git dir that is not there, so the index's
        # getmtime raises for real (no mock: a mocked getmtime makes no syscall and the wrapper rightly counts nothing)
        key, n = key_and_stats(os.path.join(td.name, "elsewhere", ".git", "HEAD"))
        self.assertIsNone(key, "a stat that raises: no key")
        self.assertEqual(n, 3, "the two subdirectory stats and the raising index stat: attempted, so it counts, like a missing file's")

    def test_the_repo_index_key_counts_the_tree_memos_stats_through_the_real_helpers(self):
        """The case the stubbed test could not see (2026-09-19 review, extra5-2): with the REAL _tree_of and _git_head_file
        over a git-made plain repository and a worktree, cold memos and then warm, the count equals the outside
        interception (os.stat, os.lstat and DirEntry.stat while the scope is open) and exceeds the body's own stats (the
        subdirectories, the tree's mtime, the index's) by the tree memos' stats: _dotgit_on_chain's chain walk,
        _verdict_key's isdir on a worktree pointer, _pointer_mtime's getmtime, and on the cold path git's own. Removing
        _entry_stat at the subdirectory stat reds it (short by one per subdirectory); a stray site count in a helper reds
        it the other way."""
        if shutil.which("git") is None:
            self.skipTest("no git on this machine")
        td = tempfile.TemporaryDirectory(); self.addCleanup(td.cleanup)
        main, wt = _plain_repo_and_worktree(td.name)
        for label, cwd in (("plain", main), ("worktree", wt)):
            with self.subTest(tree=label):
                counts = []
                for memo in ("cold", "warm"):
                    before = km._chat_sig_stats_report()["stats"]
                    with _StatInterceptor(km._CHAT_SIG_TL) as ic, km._chat_sig_scope():
                        key = km._repo_index_key(cwd)
                    n = km._chat_sig_stats_report()["stats"] - before
                    self.assertIsNotNone(key, "%s %s: a key" % (label, memo))
                    self.assertEqual([x[0] for x in key[2]], ["docs", "src"], "the two subdirectories")
                    self.assertIsNotNone(key[0], "the index's mtime: the tree has a git dir")
                    body = len(key[2]) + 2                   # the subdirectories, the tree's mtime, the index's
                    seen = {"stat": ic.stat, "posix": ic.posix_stat, "lstat": ic.lstat, "dirent": ic.dirent}
                    self.assertEqual(n, ic.total, "%s %s memos: the count is what ran, helpers included: %r" % (label, memo, seen))
                    self.assertEqual(ic.dirent, len(key[2]), "the subdirectories' stats are DirEntry stats through _entry_stat")
                    self.assertGreater(n, body, "%s %s memos: the tree memos' stats are in the count beyond the body's own %d: %r"
                                       % (label, memo, body, seen))
                    counts.append(n)
                self.assertGreaterEqual(counts[0], counts[1], "a cold verdict costs at least what the warm path costs")

    def test_the_dependency_tail_counts_every_stat_it_makes_through_its_real_caller(self):
        """The tail's two stat sites, driven through their real caller (2026-09-19 review, tests-2): _chat_sig_deps over a
        record naming an existing task output and a missing one, with a postal dependency, inside the scope, counts
        exactly the stats the outside interception saw, at least three (one per recorded task output, the missing one
        included, plus the postal log's); the helper-level three calls hold the same equality and read exactly three; an
        empty record counts zero."""
        td = tempfile.TemporaryDirectory(); self.addCleanup(td.cleanup)
        existing, missing = os.path.join(td.name, "out.txt"), os.path.join(td.name, "gone.txt")
        with open(existing, "w") as f:
            f.write("x\n")
        deps = {"task_outs": [(existing, (1.0, 2)), (missing, None)], "pl_pending": [], "pl_at": (), "pl_check": None,
                "postal_any": True, "postal_cards": [], "at_build": ((), (), None)}
        before = km._chat_sig_stats_report()["stats"]
        with _StatInterceptor(km._CHAT_SIG_TL) as ic, km._chat_sig_scope():
            touts, pl, postal = km._chat_sig_deps(self.SIDS[0], deps)
        n = km._chat_sig_stats_report()["stats"] - before
        self.assertEqual([k is None for _of, k in touts], [False, True], "the existing output keyed, the missing one None")
        self.assertEqual(pl, ())
        self.assertEqual(n, ic.total, "the tail's stats, whoever made them: %r" % {"stat": ic.stat, "lstat": ic.lstat, "dirent": ic.dirent})
        self.assertGreaterEqual(n, 3, "one per recorded task output, the missing one included, plus the postal log's")
        before = km._chat_sig_stats_report()["stats"]
        with _StatInterceptor(km._CHAT_SIG_TL) as ic2, km._chat_sig_scope():
            km._chat_stat_key(existing); km._chat_stat_key(missing); km._chat_postal_key()
        self.assertEqual(km._chat_sig_stats_report()["stats"] - before, ic2.total)
        self.assertEqual(ic2.total, 3, "each attempt counted, a missing file's included")
        before = km._chat_sig_stats_report()["stats"]
        with _StatInterceptor(km._CHAT_SIG_TL) as ic3, km._chat_sig_scope():
            self.assertEqual(km._chat_sig_deps(self.SIDS[0], None), ((), (), None))
        self.assertEqual((km._chat_sig_stats_report()["stats"] - before, ic3.total), (0, 0), "an empty record stats nothing")

    def _reg_reader(self):
        self.assertTrue(km._sdk(), "premise: the SDK backend module loads (its read_reg is the counted reader)")
        return sys.modules["romp_sdk_backend"]

    def test_the_per_thread_accumulators_count_only_the_owning_threads_reads(self):
        """Both per-thread accumulators (the kernel's _CHAT_SIG_TL and sdk_backend's _REG_READ_TL) are thread-locals: a scope
        open on one thread sees none of another thread's reads (2026-09-19 review, tests-3; both passed every test when
        replaced by objects shared across threads). Event-gated: thread one opens the scope and waits; thread two, outside
        any scope, makes three stats, two registry reads and a names-read count; thread one then makes one stat and one
        registry read and closes. The fold reads stats 1, regReads 1, namesReads 0 (shared objects read 4, 3, 1). The
        stats are real calls through the kernel's os.stat wrapper, under the outside interception, whose rule agrees."""
        sb = self._reg_reader()
        td = tempfile.TemporaryDirectory(); self.addCleanup(td.cleanup)
        p = os.path.join(td.name, "f")
        with open(p, "w") as f:
            f.write("x")
        opened, done = threading.Event(), threading.Event()
        failures = []

        def one():
            try:
                with km._chat_sig_scope():
                    opened.set()
                    if not done.wait(10):
                        failures.append("thread two never finished")
                    os.stat(p); sb.read_reg(km.jd.STATE, self.SIDS[0])
            except Exception as e:
                failures.append(repr(e))

        def two():
            try:
                if not opened.wait(10):
                    failures.append("thread one never opened its scope")
                for _ in range(3):
                    os.stat(p)
                sb.read_reg(km.jd.STATE, self.SIDS[1]); sb.read_reg(km.jd.STATE, self.SIDS[1])
                km._chat_sig_count("namesReads")
            except Exception as e:
                failures.append(repr(e))
            finally:
                done.set()
        before = km._chat_sig_stats_report()
        with _StatInterceptor(km._CHAT_SIG_TL) as ic:
            ths = [threading.Thread(target=one), threading.Thread(target=two)]
            for t in ths:
                t.start()
            for t in ths:
                t.join(15)
        after = km._chat_sig_stats_report()
        self.assertEqual(failures, [])
        d = {k: after[k] - before[k] for k in after}
        self.assertEqual((d["stats"], d["regReads"], d["namesReads"]), (1, 1, 0), "the fold sees the scope's own thread's reads alone")
        self.assertEqual(ic.total, 1, "the outside rule agrees: only the thread with the open scope")

    def test_two_scopes_open_at_once_each_fold_their_own_threads_reads(self):
        """The mirror case: two threads open scopes at once, read different amounts (two stats and one registry read; three
        and two) and close, each fold pinned to its own thread's reads through a spy on the fold (_chat_sig_bump, keyed by
        the folding thread). A shared accumulator folds the sum, or the other thread's reads, on at least one of them."""
        sb = self._reg_reader()
        td = tempfile.TemporaryDirectory(); self.addCleanup(td.cleanup)
        p = os.path.join(td.name, "f")
        with open(p, "w") as f:
            f.write("x")
        both_open, both_read = threading.Barrier(2), threading.Barrier(2)
        folds, idents, failures = {}, {}, []
        real_bump = km._chat_sig_bump

        def bump(**counts):
            if "stats" in counts:
                folds[threading.get_ident()] = dict(counts)
            return real_bump(**counts)

        def worker(name, n_stat, n_reg):
            try:
                idents[name] = threading.get_ident()
                with km._chat_sig_scope():
                    both_open.wait(10)
                    for _ in range(n_stat):
                        os.stat(p)
                    for _ in range(n_reg):
                        sb.read_reg(km.jd.STATE, self.SIDS[2])
                    both_read.wait(10)
            except Exception as e:
                failures.append(repr(e))
        with mock.patch.object(km, "_chat_sig_bump", bump):
            ths = [threading.Thread(target=worker, args=("a", 2, 1)), threading.Thread(target=worker, args=("b", 3, 2))]
            for t in ths:
                t.start()
            for t in ths:
                t.join(15)
        self.assertEqual(failures, [])
        self.assertEqual((folds[idents["a"]]["stats"], folds[idents["a"]]["regReads"]), (2, 1), "thread a's fold is its own reads")
        self.assertEqual((folds[idents["b"]]["stats"], folds[idents["b"]]["regReads"]), (3, 2), "thread b's fold is its own reads")


class StatCountingInstall(unittest.TestCase):
    """The stat interception the stats counter rests on (2026-09-19 review, regression-1): installed once per process at
    kernel import, shared by every kernel load, and the one door for a DirEntry's stat in kernel/."""

    def test_the_wrappers_are_installed_once_per_process_and_shared_by_every_kernel_load(self):
        """os.stat and os.lstat are the kernel's counting wrappers around the builtins, the same objects on the posix module
        (importlib's path), one deep: a second load of the kernel under another name finds them installed, installs
        nothing and binds the SAME thread-local, so the chain never grows and every load folds into one accumulator. The
        wrapper counts only while the calling thread's signature is open."""
        real_stat, real_lstat = os.stat.__wrapped__, os.lstat.__wrapped__
        for real in (real_stat, real_lstat):
            self.assertEqual(type(real).__name__, "builtin_function_or_method", "the wrapped function is the builtin")
            self.assertFalse(hasattr(real, "__wrapped__"), "chain length one")
        self.assertIs(os.stat._romp_sig_counting, km._CHAT_SIG_TL, "the thread-local lives on the wrapper")
        self.assertIs(posix.stat, os.stat); self.assertIs(posix.lstat, os.lstat)
        acc = getattr(pathlib, "_NormalAccessor", None)
        if acc is not None:                              # Python 3.10: the accessor bound os.stat at import and is patched too
            self.assertIs(acc.__dict__["stat"].__func__, os.stat); self.assertIs(acc.__dict__["lstat"].__func__, os.lstat)
        km2 = load_source("romp_kernel_second_load_for_the_stat_wrapper_pin", os.path.join(BIN, "romp-kernel"))
        self.assertIs(os.stat.__wrapped__, real_stat, "a second load installs nothing: the chain stays one deep")
        self.assertIs(os.lstat.__wrapped__, real_lstat)
        self.assertIs(km2._CHAT_SIG_TL, km._CHAT_SIG_TL, "both loads share one thread-local")
        self.assertIs(km2._stat_counting_install(), km._CHAT_SIG_TL, "and a repeated install returns it")
        tl = km._CHAT_SIG_TL
        self.assertFalse(tl.active)
        n0 = tl.stats
        os.stat(BIN); os.lstat(BIN); pathlib.Path(BIN).exists()
        self.assertEqual(tl.stats, n0, "outside a signature the wrapper counts nothing")
        with km._chat_sig_scope():
            os.stat(BIN); os.lstat(BIN); pathlib.Path(BIN).exists(); os.path.isdir(BIN)
            self.assertEqual(tl.stats, 4, "inside one: os.stat, os.lstat, pathlib and os.path alike, one each")
        self.assertFalse(tl.active)

    def test_every_direntry_stat_in_kernel_goes_through_the_entry_stat_door(self):
        """A DirEntry stats in C and reaches no os.stat wrapper, so kernel/ has one door for it: _entry_stat (kernel.py) and
        its two-line twins in judge.py and event_model.py. Source pin: every `e.stat(` or `entry.stat(` under kernel/*.py
        sits inside a def named _entry_stat; a new scandir site that stats its entry directly is not counted and reds
        this."""
        root = os.path.join(os.path.dirname(HERE), "kernel")
        pat = re.compile(r"\be\.stat\(|entry\.stat\(")
        offenders, helpers = [], set()
        for fn in sorted(os.listdir(root)):
            if not fn.endswith(".py"):
                continue
            cur = None
            with open(os.path.join(root, fn), encoding="utf-8") as f:
                for i, line in enumerate(f, 1):
                    m = re.match(r"^\s*def (\w+)\(", line)
                    if m:
                        cur = m.group(1)
                    if pat.search(line):
                        if cur == "_entry_stat":
                            helpers.add(fn)
                        else:
                            offenders.append("%s:%d: %s" % (fn, i, line.strip()))
        self.assertEqual(offenders, [], "a DirEntry.stat outside _entry_stat: not counted under memos.chatSig.stats")
        self.assertEqual(helpers, {"kernel.py", "judge.py", "event_model.py"}, "the door and its twins")


if __name__ == "__main__":
    unittest.main()
