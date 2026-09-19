"""Diff-based delta-send for the chat (the user 2026-06-25, who wanted to stop re-sending what didn't change).

The chat pusher used to send the FULL events array on every change (~8MB for a big transcript). Now the
whole transcript stays resident in the browser (instant scrollback), but a caught-up client receives only
the CHANGED SUFFIX as {type:"chatTail", from, events}. The suffix is found by DIFFING the freshly-built
events against the previous build — robust to _hydrate_postal turning one event into several cards mid-array,
which a fixed window would mishandle. A fresh connect / fork / behind-the-change client still gets the full
{type:"session"} so it always renders from a correct base. Source-level + behavioural pins.
"""
import ast
import hashlib
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
        self.dirent_by_dir = {}                            # DirEntry stats by the entry's directory: a channel's own count
        self.paths = {}                                    # os.stat and os.lstat calls by path: which files a signature read

    @property
    def total(self):
        return self.stat + self.posix_stat + self.lstat + self.dirent

    def _wrap(self, real, field):
        def counting(path, *a, **kw):
            if getattr(self.tl, "active", False):          # getattr: the first cut's plain thread-local had no default
                setattr(self, field, getattr(self, field) + 1)
                key = os.fspath(path) if isinstance(path, (str, bytes, os.PathLike)) else path   # an fd stays an int
                self.paths[key] = self.paths.get(key, 0) + 1
            return real(path, *a, **kw)
        counting.__wrapped__ = real
        tl = getattr(real, "_romp_sig_counting", None)   # the kernel's thread-local rides its wrapper by attribute, and the
        if tl is not None:                                 # _entry_stat twins in judge.py, event_model.py and sdk_backend.py read
            counting._romp_sig_counting = tl               # it off os.stat: carried here, or they count nothing under interception
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
                    d = os.path.dirname(self._e.path)
                    me.dirent_by_dir[d] = me.dirent_by_dir.get(d, 0) + 1
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
        and the two counts they lean on returned: (cached, built). pre = cached + built - targetedBuilds + failedBuilds at rest
        (the reads here are between pushes; a tab in flight puts pre one ahead, its note folded before the tab's build_chat
        record); post = built - targetedBuilds - nosig over a window with failedBuilds 0, and otherwise post exceeds
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
        s0 = ps.snapshot()
        before, b0 = km._chat_sig_stats_report(), s0["builds"]["chat"]
        with p1, p2, _StatInterceptor(km._CHAT_SIG_TL) as ic:
            _wire, calls, _rows = self._run(km._chat_diff, perf=ps)
        self.assertEqual(calls, [False, True, False, True, False, True], "premise: rebuilt, served, alternating")
        s1 = ps.snapshot()
        after, b1 = km._chat_sig_stats_report(), s1["builds"]["chat"]
        d = {k: after[k] - before[k] for k in after}
        rows, n_sigs = self._sig_rows(s0, s1), d["pre"] + d["post"] + d["thread"]
        print("[live] bare: counted=%d intercepted=%d signatures=%d per_signature=%.1f sig_cpu_ms_per_sig=%s sig_wall_ms_per_sig=%.3f"
              % (d["stats"], ic.total, n_sigs, (ic.total / n_sigs) if n_sigs else float("nan"),
                 "n/a" if rows["cpu_ms"] is None else "%.3f" % (rows["cpu_ms"] / n_sigs if n_sigs else float("nan")),
                 (rows["wall_ms"] / n_sigs) if n_sigs else float("nan")))
        cached, built = self._identities(d, b0, b1)
        self.assertEqual((cached, built), (3, 3))
        self.assertEqual((d["nosig"], d["failedBuilds"], d["targetedBuilds"]), (0, 0, 0))
        self.assertEqual(d["pre"], 6, "one pre-build signature per tab per push"); self.assertEqual(d["post"], 3)
        self.assertEqual(d["pushes"], 6, "one per push that ran the chat tab loop")
        # compares counts every cache READ that met an entry with a signature in hand: the pre-flight read of each of the
        # three served cycles (1, 3, 5), and for each of the two warm rebuilds (cycles 2 and 4) its pre-flight read AND its
        # re-read under the claim, both meeting the stale entry; the cold first cycle meets nothing. 3 + 2 * 2 = 7. The final
        # compare re-evaluates the last read's operands and is not a read, so it counts nothing (counting it would read 12 here: these
        # seven plus the five final compares of cycles 1 to 5, each of which met an entry; the cold cycle 0's met none).
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

    def test_the_per_tab_counts_the_cost_derivation_uses_hold_by_execution(self):
        """The kernel's stages_cpu_ms block comment derives the instrumentation's cost from counts per tab and per push (the
        microsecond figures live in docs/reference.md alone); this pins the counts, so the derivation cannot go stale
        (2026-09-19 review: the measured figures sat in four hand-maintained copies). Over one tab through six cycles,
        rebuilt and served alternately, per cycle: a served tab opens one signature scope, folds one per-tab note whose
        pre-flight read is its one compare, calls no re-read note, and reads the thread clock 8 times (the chat
        container's pair, the signature seam's, the deps sub-seam's and the send seam's); a rebuilt tab opens two scopes
        (the pre-build and the post-build signature), folds the note and one claim re-read note, counts two compares when
        the entry it met was cached (the cold first cycle met none, so its note and its re-read note counted nothing), and
        reads the clock 12 times (the build seam's pair and the post-build signature's pair more). The spies wrap the
        kernel's own callables under their module names, which is how _chat_build_sig, the seams and _cpu_delta reach
        them; an extra clock read at any seam or a second re-read note on the claim road moves a count and reds this."""
        ps = km._PERF_STATS
        calls = {"scope": 0, "note": 0, "compare": 0, "clock": 0}
        real = {"scope": km._chat_sig_scope, "note": km._chat_sig_note_pre, "compare": km._chat_sig_note_compare,
                "clock": km._thread_cpu}

        def spy(name):
            def wrapped(*a, **kw):
                calls[name] += 1
                return real[name](*a, **kw)
            return wrapped
        marks = []                                      # the counters as each cycle opens; the run's end closes the last

        def mark(_i):
            marks.append((dict(calls), km._chat_sig_stats_report()))
        with mock.patch.object(km, "_chat_sig_scope", spy("scope")), mock.patch.object(km, "_chat_sig_note_pre", spy("note")), \
                mock.patch.object(km, "_chat_sig_note_compare", spy("compare")), mock.patch.object(km, "_thread_cpu", spy("clock")):
            _wire, same, _rows = self._run(km._chat_diff, perf=ps, between=mark)
            marks.append((dict(calls), km._chat_sig_stats_report()))
        self.assertEqual(same, [False, True, False, True, False, True], "premise: rebuilt, served, alternating")
        self.assertEqual(len(marks), 7, "a mark before each of the six cycles and one at the end")
        per_cycle = [dict({k: c1[k] - c0[k] for k in calls}, **{k: r1[k] - r0[k] for k in ("pre", "post", "compares")})
                     for (c0, r0), (c1, r1) in zip(marks, marks[1:])]
        served = {"scope": 1, "note": 1, "compare": 0, "clock": 8, "pre": 1, "post": 0, "compares": 1}
        rebuilt = {"scope": 2, "note": 1, "compare": 1, "clock": 12, "pre": 1, "post": 1, "compares": 2}
        cold = dict(rebuilt, compares=0)
        self.assertEqual(per_cycle, [cold, served, rebuilt, served, rebuilt, served],
                         "the derivation's counts per cycle kind: cold rebuild, served, warm rebuild, served, warm rebuild, served")
        self.assertEqual(calls["clock"], 3 * 12 + 3 * 8, "the fake-clock test's 60 reads, counted here through _thread_cpu itself")

    def _connected(self, **kw):
        """A connected chat client (in km._clients) that the targeted push may send to: ready, proto 2, a send sink."""
        frames = []
        c = dict({"app": "chat", "alive": True, "sent": {}, "skeleton": set(), "proto": 2, "ready": True, "handshake": True,
                  "send": lambda s: frames.append(json.loads(s)), "_frames": frames}, **kw)
        return c

    @staticmethod
    def _sig_rows(s0, s1):
        """The push.chat.sig row's wall and thread-CPU deltas in ms between two _PerfStats snapshots, for the [live] lines
        the PR body quotes (the cost paragraph's per-signature CPU and wall are these divided by the signature count); the
        CPU is None where the platform has no per-thread rusage (km._RUSAGE_THREAD None: the block is served empty)."""
        wall = s1["stages_ms"].get("push.chat.sig", 0.0) - s0["stages_ms"].get("push.chat.sig", 0.0)
        if km._RUSAGE_THREAD is None:
            return {"wall_ms": wall, "cpu_ms": None}
        zero = {"user": 0.0, "sys": 0.0}
        c0, c1 = s0["stages_cpu_ms"].get("push.chat.sig", zero), s1["stages_cpu_ms"].get("push.chat.sig", zero)
        return {"wall_ms": wall, "cpu_ms": (c1["user"] - c0["user"]) + (c1["sys"] - c0["sys"])}

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

    def test_the_identities_hold_when_the_targeted_pushs_build_raises(self):
        """Window (5) (2026-09-19 review, extra5-1): a targeted push whose build_session raises. _push_session_now records
        build_chat and bumps targetedBuilds only after build_session returned, both inside its try, so a raising targeted
        build counts under neither builds.chat built nor targetedBuilds, and not under failedBuilds either, which is the
        push loop's fault branch alone; the identities hold on the loop's own numbers: cached 3, built 3, pre 6, post 3,
        targetedBuilds 0, failedBuilds 0. Bumping failedBuilds on the targeted push's failure road too reads pre 6 != 7;
        bumping targetedBuilds before build_session reads 6 != 5. Neither mutation reds windows (1) to (4)."""
        c = self._connected()
        raising = []

        def build(frame):
            if raising:
                raise RuntimeError("synthetic targeted build failure")
            return dict(frame)

        def between(i):
            if i == 5:
                raising.append(True)
                try:
                    km._push_session_now(self.SID)
                finally:
                    del raising[:]
        with mock.patch.object(km, "_clients", [c]):
            d, b0, b1, calls = self._window(build=build, between=between, tolerate=("push-session-now",))
        self.assertEqual(calls, [False, True, False, True, False, True], "the loop's cycles are unchanged")
        cached, built = self._identities(d, b0, b1)
        self.assertEqual((cached, built), (3, 3), "the raising targeted build is under neither")
        self.assertEqual((d["pre"], d["post"], d["targetedBuilds"], d["failedBuilds"], d["nosig"]), (6, 3, 0, 0, 0))
        self.assertEqual([f for f in c["_frames"] if f["type"] == "session"], [], "no frame from the raising targeted build")

    def test_post_counts_a_rebuild_whose_post_build_signature_raised(self):
        """The wider-direction pin for post (2026-09-19 review, the two-direction lens): post counts every rebuild that had
        a pre-build signature, one whose post-build signature RAISED included (the loop bumps post after the try that takes
        it), and such a build is never cached, so the tab rebuilds every cycle. With _chat_build_sig raising on its
        deps=False call alone (the post-build one) and every build succeeding: six rebuilds, pre 6, post 6, built 6,
        cached 0, no nosig and no failedBuilds, and the identities hold. Counting post only when the post-build signature
        was taken reads 0 here, and the post identity 0 != 6."""
        real = km._chat_build_sig

        def sig(*a, **kw):
            if kw.get("deps") is False:
                raise RuntimeError("synthetic post-build signature failure")
            return real(*a, **kw)
        with mock.patch.object(km, "_chat_build_sig", sig):
            d, b0, b1, _calls = self._window()
        cached, built = self._identities(d, b0, b1)
        self.assertEqual((cached, built), (0, 6), "never cached: the tab is rebuilt every cycle")
        self.assertEqual((d["pre"], d["post"], d["nosig"], d["failedBuilds"], d["targetedBuilds"]), (6, 6, 0, 0, 0))

    def _stats_world(self):
        """The stats exactness test's furnished world (its docstring names what the world holds), run once through the
        six-cycle harness under the outside interception, for that test and for the two constructed premise cases:
        returns (the memos.chatSig delta d, the interceptor ic, regs_present, n_sigs, the registry directory sdk, the
        CLAUDE_CONFIG_DIR cfg, the imports list, the diff's same-object calls, the builds.chat snapshots (b0, b1), and
        the push.chat.sig row's wall and thread-CPU deltas over the run, for the [live] line). n_sigs is pre + post +
        thread as counted, never a literal. The signature consults the kernel's own backend singleton (_be = _sdk() in
        _chat_build_sig; its fork_children is the registry scan), and this world asserts two PREMISES about it rather
        than binding it (the round-2 ruling, 2026-09-19: a binding makes the test pass whether or not the world is sane,
        the class of mistake the original made; the cause is fixed at its source, tests/test_kernel.py ViewBuilder
        restoring the singleton with its sandbox). Premise 1, before the run: the singleton's state_dir is this world's
        state root. The singleton keeps the jd.STATE of its construction, so a peer module that sandboxed jd.STATE,
        reached km._sdk() under it and removed the sandbox leaves one over a removed root, whose fork_children answers
        {} on the OSError and reaches list_regs never: the registry channel would run over nothing, the counter would
        correctly count none of it, and a count assertion would be the first to say so, with a number and no reason
        (the round-2 review's prefix run). Premise 2, after the run and before any count: the registry
        channel RAN. A recording spy on romp_sdk_backend.list_regs (fork_children's scan) notes each call's root and
        whether a signature was open on the thread; the calls inside a signature number one per cycle (the reg written
        before each cycle moves sdk/'s mtime, so the pre-build signature's fork_children memo misses and the post-build
        one's hits), every one over this root. Every file furnish() writes into the shared state roots goes through
        write_restoring, which puts the prior bytes back or unlinks at cleanup (jd.MESSAGES, the shared postal store,
        included: the harness once truncated it and left six more artifacts behind, the round-2 review's tests-1); the
        cleanups run after the measurement, so the counts are unchanged by them, and a directory the world made is
        removed if still empty. Premise 3, after the run and before any count: the furnished channels ran (the files
        stand until cleanup, the cwd resolved to the worktree, the worktree top, the task store and the postal store
        were read inside a signature, the names and registry reads landed), since a thinner world keeps the equality.
        Premise 4, before the run, in two halves: the kernel's counting wrappers stand on os.stat, os.lstat, posix.stat
        and posix.lstat (each carries this kernel's thread-local), and each COUNTS (one call on an existing str path
        inside a forced-open signature moves the accumulator by exactly 1: one call shape, a sample). The second half is
        there because functools.wraps copies the marker with __dict__, so a marker proves only that a wrapper rides on
        the kernel's, not that it counts: a marker-carrying wrapper that delegates to the builtin, or one that counts
        twice, passes the marker half and would red the equality with two numbers and no reason (the closing check,
        2026-09-19). A peer module that displaced one and never restored it, or restored the builtin, leaves the kernel
        counting a subset of what
        the interceptor sees: with os.stat, os.lstat or posix.stat displaced by its builtin the equality would be the
        first to say so, reading the kernel's count short of the interceptor's, two numbers and no reason; with
        posix.lstat displaced the count does not move (observed at the closing check, three repeats), so for it this
        premise is the only detector and the equality would say nothing."""
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
            if not imports:                              # once, inside the first signature: its stats go through posix.stat
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
        # the registry channel (the road the first exactness test could not see, 2026-09-19 review, regression-1): the
        # signature's fork component calls the backend's fork_children, memoized on the sdk/ directory's mtime, and on a
        # miss list_regs stats EVERY reg through a DirEntry (sdk_backend's _entry_stat twin). Every reg write is an
        # os.replace into sdk/, which moves that mtime, so on a production root most pre-build signatures miss. Three
        # peers' regs are written before any push and one more before every cycle (no forkedFrom: the tab's own fork
        # component stays None, so no rebuild), and the regs present at each cycle are recorded for the derivation below.
        sdk = km.jd.STATE / "sdk"                         # the backend's registry directory (its state_dir is jd.STATE)
        peers = self.REG_PEERS
        regs_present = []
        if not sdk.exists():                              # made here: removed at cleanup if still empty (after the regs go)
            self.addCleanup(lambda: sdk.is_dir() and not any(sdk.iterdir()) and sdk.rmdir())
        self.addCleanup(lambda: [os.unlink(sdk / (p + ".json")) for p in peers if (sdk / (p + ".json")).exists()])

        def write_reg(i):
            sdk.mkdir(parents=True, exist_ok=True)
            tmp = sdk / (peers[i] + ".json.tmp")            # write_reg's shape: a temp name list_regs skips, then os.replace
            tmp.write_text(json.dumps({"sid": peers[i], "name": "api%d" % i, "state": "idle", "pid": 0}))
            os.replace(tmp, sdk / (peers[i] + ".json"))
        bumped = [0]

        def between(i):
            write_reg(3 + i)
            # the memo miss is a property of the world and not of the clock: a directory's mtime comes from the coarse clock
            # on kernels without multigrain timestamps (one tick, 1 to 4 ms), so a whole cycle inside one tick would leave the
            # post-build memo hitting on the next pre-build signature, one scan short of premise 2 on a sane world (the
            # round-3 review, 2026-09-19); sdk/'s mtime is moved a whole second past its last value instead
            bumped[0] = max(os.stat(sdk).st_mtime_ns, bumped[0]) + 1_000_000_000
            os.utime(sdk, ns=(bumped[0], bumped[0]))
            regs_present.append(len([n for n in os.listdir(sdk) if n.endswith(".json")]))

        furnished, world = [], {}                         # the files furnish() wrote, and the worktree and task store it made

        def write_restoring(path, text):
            """Write `text` to `path` and, at cleanup, put back what was there: the prior bytes, or nothing (unlinked)."""
            path = pathlib.Path(path)
            furnished.append(path)
            prior = path.read_bytes() if path.exists() else None

            def restore():
                if prior is None:
                    try:
                        path.unlink()
                    except FileNotFoundError:
                        pass
                else:
                    path.write_bytes(prior)
            self.addCleanup(restore)
            path.write_text(text)

        def furnish(td, path, sess):
            jd = km.jd
            for i in range(3):
                write_reg(i)
            # seven files in the shared roots, every one restored at cleanup: five under the judge's root (jd.*) and two
            # under the kernel's (km.WORKING_DIR and km.NAMES bind at kernel import, with no rebind hook), which is why the
            # cleanup is by path and not a jd._rebind_state; a directory made here is removed at cleanup if still empty
            for d in (jd.STATESDIR, jd.GOALDIR, jd.GOALARCHDIR, jd._overrides_dir(), km.WORKING_DIR, km.NAMES, jd.MESSAGES.parent):
                if not d.exists():
                    self.addCleanup(lambda d=d: d.is_dir() and not any(d.iterdir()) and d.rmdir())
                d.mkdir(parents=True, exist_ok=True)
            write_restoring(jd.STATESDIR / (self.SID + ".jsonl"), json.dumps({"t": self.NOW - 30, "state": "idle"}) + "\n")
            write_restoring(jd.GOALDIR / (self.SID + ".json"), json.dumps({"rompUuid": self.SID, "nodes": {}, "status": {}}))
            write_restoring(jd._overrides_dir() / (self.SID + ".jsonl"), "")     # the goal-store rule's journal cleanup
            write_restoring(jd.GOALARCHDIR / (self.SID + ".json"), json.dumps({"rompUuid": self.SID, "nodes": {}}))
            write_restoring(km.WORKING_DIR / self.SID, "the notes-api web tier\n")
            # THROUGH jd.MESSAGES, the shared postal store the signature's postal readers stat, never a path rebuilt from
            # jd.STATE: a plain write here once truncated the store a sibling module had seeded
            write_restoring(jd.MESSAGES, json.dumps(
                {"ev": "sent", "id": "m1", "from": "api", "from_id": self.SIDS_PEER, "to": "web", "to_id": self.SID,
                 "body": "hello", "kind": "coordinate", "t": self.NOW}) + "\n")
            main, wt = _plain_repo_and_worktree(td)
            with open(os.path.join(wt, "CLAUDE.md"), "w") as f:
                f.write("# notes-api\n")
            write_restoring(km.NAMES / self.SID, "web\t%s\t#abcdef\n" % wt)
            tasks = os.path.join(cfg.name, "tasks", self.SID); os.makedirs(tasks)
            world["wt"], world["tasks"] = wt, tasks
            with open(os.path.join(tasks, "1.json"), "w") as f:
                f.write(json.dumps({"id": "1", "subject": "write the notes-api docs", "status": "pending"}))
        self.assertTrue(km._sdk(), "premise: the SDK backend module loads (its list_regs is the registry scan)")
        be = km._sdk()                                    # the kernel's lazily built singleton, the one _chat_build_sig consults
        self.assertEqual(pathlib.Path(be.state_dir), pathlib.Path(km.jd.STATE),
                         "premise: the backend the signature consults (km._sdk(), the kernel's lazily built singleton, read "
                         "as _be = _sdk() in _chat_build_sig) is over this world's state root. A peer module that sandboxed "
                         "jd.STATE, reached km._sdk() under it and removed the sandbox leaves a singleton over a removed root, "
                         "whose fork_children answers {} on the OSError and reaches list_regs never, so the registry channel "
                         "would run over nothing; this test refuses to run over that world rather than bind the singleton "
                         "(the cause is fixed at its source: tests/test_kernel.py ViewBuilder restores the singleton with its "
                         "sandbox): backend over %r, this world at %r" % (str(be.state_dir), str(km.jd.STATE)))
        tl = km._CHAT_SIG_TL
        for name, fn in (("os.stat", os.stat), ("os.lstat", os.lstat), ("posix.stat", posix.stat), ("posix.lstat", posix.lstat)):
            self.assertIs(getattr(fn, "_romp_sig_counting", None), tl,
                          "premise: the kernel's counting wrapper stands on %s (a peer that displaced it and never restored it "
                          "leaves the kernel counting a subset of what the interceptor sees; for os.stat, os.lstat and posix.stat "
                          "the equality would be the first to say so, with two numbers and no reason, and for posix.lstat nothing "
                          "would, since the count does not move when it is displaced, so this premise is its only detector): %r"
                          % (name, fn))
            # the second half: the marker rides any functools.wraps copy, so one counted call is the proof that it counts
            was_active, was_stats = tl.active, tl.stats
            tl.active = True
            try:
                fn(cfg.name)                              # an existing path for the world's life; restoring stats is hygiene
                moved = tl.stats - was_stats              # only: _chat_sig_scope zeroes the accumulator at every signature open
            finally:
                tl.active, tl.stats = was_active, was_stats
            self.assertEqual(moved, 1,
                             "premise: the kernel's counting wrapper on %s counts: one call inside a forced-open signature moved the "
                             "accumulator by %d, not 1 (a marker-carrying wrapper that delegates without counting, since "
                             "functools.wraps copies the marker with __dict__, or one that counts twice, passes the marker check "
                             "above and would red the equality with two numbers and no reason)" % (name, moved))
        sbmod = sys.modules["romp_sdk_backend"]
        real_list_regs = sbmod.list_regs
        scans = []                                        # (the root scanned, a signature open on this thread) per list_regs call

        def list_regs_spy(state_dir):
            scans.append((pathlib.Path(state_dir), bool(getattr(km._CHAT_SIG_TL, "active", False))))
            return real_list_regs(state_dir)
        s0 = ps.snapshot()
        before, b0 = km._chat_sig_stats_report(), s0["builds"]["chat"]
        with mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": cfg.name}), mock.patch.object(km, "_pinned_notes_fp", pins_and_one_import), \
                mock.patch.object(sbmod, "list_regs", list_regs_spy), _StatInterceptor(km._CHAT_SIG_TL) as ic:
            _wire, calls, _rows = self._run(km._chat_diff, perf=ps, furnish=furnish, script=script, between=between)
        s1 = ps.snapshot()
        after, b1 = km._chat_sig_stats_report(), s1["builds"]["chat"]
        d = {k: after[k] - before[k] for k in after}
        inside = [root for root, active in scans if active]
        self.assertEqual(len(inside), len(regs_present),
                         "premise: the registry channel ran: fork_children reached list_regs inside a signature once per cycle "
                         "(the reg written before each cycle moves sdk/'s mtime, so the pre-build signature's memo misses and the "
                         "post-build one's hits); zero means the signature's backend scanned no registry. Scans (root, inside a "
                         "signature): %r" % ([(str(r), a) for r, a in scans],))
        self.assertTrue(all(root == pathlib.Path(km.jd.STATE) for root in inside),
                        "premise: every registry scan inside a signature read this world's root: %r" % ([str(r) for r in inside],))
        # premise 3, before any count too: the furnished channels RAN over this world (the round-3 review, 2026-09-19: with
        # the furnished files gone before the run the equality still held over a third of the stats, and the twenty-stats
        # floor and the registry derivation absorbed it). Read before the cleanups: every furnished file still stands, the
        # names row resolved the session's cwd to the worktree, the worktree was read inside a signature (the repo index's
        # tree and index stats and the CLAUDE.md chain are path stats: the tree has no subdirectory, so no DirEntry stat is
        # made under it), the task store was scanned there (a DirEntry stat per task file, through _entry_stat), the postal
        # store was stat'ed there (_chat_postal_key, in the tail), and the names and registry reads landed
        for p in furnished:
            self.assertTrue(p.exists(), "premise: the furnished file stands until cleanup: %s" % p)
        self.assertEqual(km._cwd_of(self.SID), world["wt"], "premise: the names row resolved the session's cwd to the worktree")
        tops = {world["wt"], os.path.realpath(world["wt"])}
        under = sorted(k for k in ic.paths if isinstance(k, str) and any(k == t or k.startswith(t + os.sep) for t in tops))
        self.assertTrue(under, "premise: the worktree was read inside a signature (the repo index, the CLAUDE.md chain): paths stat'ed %r"
                        % (sorted(k for k in ic.paths if isinstance(k, str)),))
        self.assertIn(world["tasks"], ic.dirent_by_dir,
                      "premise: the task store was scanned inside a signature: %r" % (sorted(ic.dirent_by_dir),))
        self.assertIn(str(km.jd.STATE / "timeline" / "messages.jsonl"), ic.paths,
                      "premise: the postal store was stat'ed inside a signature (the tail's postal key)")
        self.assertGreater(d["namesReads"], 0, "premise: the names channel ran")
        self.assertGreater(d["regReads"], 0, "premise: the registry read channel ran")
        return (d, ic, regs_present, d["pre"] + d["post"] + d["thread"], sdk, cfg, imports, calls, (b0, b1),
                self._sig_rows(s0, s1))

    def test_stats_counts_every_stat_a_signature_makes_by_execution(self):
        """The exactness test (2026-09-19 review, regression-1: the first cut's per-site count saw 7 of about 23 stats per
        signature and named a closed exclusion list that omitted six paths). memos.chatSig.stats must equal, over a real
        push, an OUTSIDE count of every os.stat, os.lstat and DirEntry.stat made while a signature was open (_StatInterceptor:
        wrappers around the kernel's own on the os and posix modules, a counting os.scandir; nothing of the kernel mocked),
        over a world furnished so every channel runs: a transcript, a states file, the store triple, a working note, a git
        worktree as the session's cwd with a CLAUDE.md on its chain (the cwd memos, _repo_index_key and _claudemd_key stat),
        a task store directory with one task file (a DirEntry.stat through _entry_stat), a messages.jsonl and a postal card
        (the postal key stats in the tail), the transcript's checkpoint path (a realpath: lstats), and registry files with
        one more written before every cycle, read by the kernel's own backend singleton, which _stats_world asserts is over
        this root and asserts scanned the registry inside a signature once per cycle before any count is compared (its
        docstring names the four premises and the round-2 ruling behind them). One fresh module import is forced inside the
        first signature: importlib stats through the posix module, so the equality holds only with the posix wrap in
        place. Pinned: the equality, at least twenty stats per signature, and each channel seen (lstat, DirEntry, posix).
        At the first cut this read 63 counted against about 200 intercepted over the six-cycle window; restoring per-site
        counting alone (narrower) or re-adding one site count (wider) reds it. The signature count is DERIVED from the
        window (thread 0 with no comments store, one pre-build signature per cycle, one post-build per build), never a
        literal: a literal moved with sibling state (the round-2 review's extra5-2: a peer's leftover dependency record
        forced one more rebuild), which the derivation absorbs: one more build is one more post-build signature, the
        equality and the channel derivations hold over it, and the alternation premise cannot see it, because the
        harness's build returns a shallow copy whose events list is the served frame's own, so the diff meets one object
        on both sides (probed with such a leftover on 2026-09-19: one more build, one more post-build signature,
        green). The counter counts every stat that
        occurs, and the per-channel derivations pin that the world made them: the registry channel's count is a property
        of the world (every reg present at each pre-build signature), not of the counter; a signature whose backend reads
        no registry makes no registry stat and the counter counts none, which is why the world asserts the channel ran
        (the round-2 review's prefix run met exactly that, and the constructed cases below drive it). The
        [live] line prints the counts the PR body quotes, so no figure there is copied by hand."""
        d, ic, regs_present, n_sigs, sdk, cfg, imports, calls, (b0, b1), rows = self._stats_world()
        self.assertEqual(calls, [False, True, False, True, False, True], "premise: rebuilt, served, alternating")
        self.assertEqual(len(imports), 1, "the fresh import ran once, inside the first signature")
        self.assertEqual(d["thread"], 0, "premise: no comments store in this world, no thread signature")
        self.assertEqual(d["pre"], len(calls), "one pre-build signature per cycle")
        self.assertEqual(d["post"], b1["built"] - b0["built"], "one post-build signature per build")
        seen = {"stat": ic.stat, "posix": ic.posix_stat, "lstat": ic.lstat, "dirent": ic.dirent, "dirent_by_dir": ic.dirent_by_dir}
        channels = {"stat": ic.stat, "posix": ic.posix_stat, "lstat": ic.lstat, "dirent": ic.dirent}
        print("[live] exactness: counted=%d intercepted=%d signatures=%d per_signature=%.1f registry=%d sig_cpu_ms_per_sig=%s "
              "sig_wall_ms_per_sig=%.3f channels=%r"
              % (d["stats"], ic.total, n_sigs, (ic.total / n_sigs) if n_sigs else float("nan"), ic.dirent_by_dir.get(str(sdk), 0),
                 "n/a" if rows["cpu_ms"] is None else "%.3f" % (rows["cpu_ms"] / n_sigs if n_sigs else float("nan")),
                 (rows["wall_ms"] / n_sigs) if n_sigs else float("nan"), channels))
        self.assertEqual(d["stats"], ic.total, "memos.chatSig.stats equals every stat intercepted inside the %d signatures: %r" % (n_sigs, seen))
        self._identities(d, b0, b1)
        self.assertGreaterEqual(ic.total / n_sigs, 20, "the world is not empty: at least twenty stats per signature (%r)" % (seen,))
        self.assertGreater(ic.lstat, 0, "the lstat channel ran (a realpath's per-component lstats)")
        self.assertGreater(ic.dirent, 0, "the DirEntry channel ran (the task store's one file, through _entry_stat)")
        # the DirEntry channel by directory, each count derived: the task store's one file is one DirEntry stat per signature
        # (_task_store_fp); the registry's regs are stat'ed by list_regs on every signature whose fork_children memo missed,
        # which is each cycle's PRE-build one (the reg written before the cycle moved sdk/'s mtime) over the regs then present,
        # and not the post-build one (nothing moved sdk/ during the build, so the memo hit). Without sdk_backend's _entry_stat
        # twin the equality above is short by exactly this sum (the pre-fix gap on any root with registry files).
        self.assertEqual(regs_present, [4, 5, 6, 7, 8, 9], "premise: three regs before any push, one more before each cycle")
        self.assertEqual(ic.dirent_by_dir.get(os.path.join(cfg.name, "tasks", self.SID), 0), n_sigs,
                         "the task store's file: one DirEntry stat per signature (%r)" % (ic.dirent_by_dir,))
        self.assertEqual(ic.dirent_by_dir.get(str(sdk), 0), sum(regs_present),
                         "the registry's regs: every reg present at each pre-build signature, none at a post-build one (%r)" % (ic.dirent_by_dir,))
        self.assertGreater(sum(regs_present), n_sigs, "the registry channel outnumbers the task store's: the uncounted road was the larger one")
        self.assertGreater(ic.posix_stat, 0, "the posix-module channel ran (the fresh import's path finder)")
        self.assertEqual(d["regReads"], n_sigs, "one registry read per signature")

    def test_a_stale_backend_singleton_fails_the_premise_not_a_count(self):
        """Constructed case 1 for the world's first premise (the round-2 ruling, 2026-09-19). The contamination the
        alphabetical order exposed: the kernel's backend singleton is built lazily over jd.STATE as it stands and keeps
        that root, so a peer module that sandboxed jd.STATE and reached km._sdk() under it (tests/test_kernel.py
        ViewBuilder, before it restored the singleton with its sandbox) left a backend over a removed root; its
        fork_children answers {} on the OSError and calls list_regs never, so the signature made no registry stat, the
        counter correctly counted none, and the registry derivation was the first assertion to fail, with a count and no
        reason (the round-2 review's prefix run). Reproduced in-process: a backend over a directory that is
        then removed is installed as the singleton. The world now refuses to run over it: the failure is an
        AssertionError naming the premise (the singleton is over this world's state root), raised before any signature
        runs, and not a count mismatch. The remedy this replaces bound the singleton to the world's root for the run,
        which passes whether or not the world is sane, the class of mistake the original made; the test fails loudly on
        the premise instead."""
        self.assertTrue(km._sdk(), "premise: the SDK backend module loads")
        gone = tempfile.mkdtemp()
        stale = sys.modules["romp_sdk_backend"].SdkBackend(gone, "/bin/true", lambda *a, **k: None)
        shutil.rmtree(gone)
        saved = km._sdk_backend
        km._sdk_backend = stale
        self.addCleanup(setattr, km, "_sdk_backend", saved)
        self.assertIs(km._sdk(), stale, "premise: the singleton the signature would consult is the stale one")
        self.assertFalse(os.path.isdir(gone), "premise: its registry root is gone")
        self.assertEqual(stale.fork_children(), {}, "premise: over a removed root fork_children answers {} and scans nothing")
        with self.assertRaises(AssertionError) as cm:
            self._stats_world()
        msg = str(cm.exception)
        self.assertIn("premise", msg, "the world fails on a premise: %s" % msg)
        self.assertIn("over this world's state root", msg, "the failure names the missing premise, the singleton's root: %s" % msg)
        self.assertNotIn("!= 39", msg, "not a count mismatch")
        self.assertNotIn("equals every stat intercepted", msg, "not the equality")

    def test_a_backend_that_scans_no_registry_fails_the_premise_not_a_count(self):
        """Constructed case 2 for the world's second premise: the singleton is over this root (premise 1 holds), and ITS
        fork_children is patched, on the instance, to answer {} for the run, so no signature reaches list_regs. The world
        runs to its end and then refuses: an AssertionError naming that the registry channel did not run, raised before
        any count is compared, and not the count mismatch a world that scanned no registry once produced (every reg
        present at each pre-build signature against none). Same ruling as case 1: a binding would make the counts come
        out whether or not the channel ran; the premise fails loudly instead. The patch is on the singleton instance and
        not on SdkBackend, so a world that bound a fresh backend of its own would scan the registry through it and this
        case would red on the AssertionError never raised: the mutation that restores the binding reds both cases."""
        be = km._sdk()
        self.assertTrue(be, "premise: the SDK backend module loads")
        self.assertEqual(pathlib.Path(be.state_dir), pathlib.Path(km.jd.STATE), "premise: the singleton is over this root (premise 1 holds here)")
        with mock.patch.object(be, "fork_children", lambda: {}):
            with self.assertRaises(AssertionError) as cm:
                self._stats_world()
        msg = str(cm.exception)
        self.assertIn("the registry channel ran", msg, "the failure names the missing premise, the channel that did not run: %s" % msg)
        self.assertNotIn("!= 39", msg, "not a count mismatch")
        self.assertNotIn("equals every stat intercepted", msg, "not the equality")


    def test_a_displaced_stat_wrapper_fails_the_premise_not_a_count(self):
        """Constructed case 3, for the world's fourth premise (the closing check on the exactness world, 2026-09-19): the
        kernel's counting wrappers stand on os.stat, os.lstat, posix.stat and posix.lstat. A peer module that patched one
        and never restored it, or restored the builtin, leaves the kernel counting a subset of what the interceptor
        sees: with os.stat, os.lstat or posix.stat displaced by its builtin the equality reads the kernel's count short
        of the interceptor's, two numbers and no reason; with posix.lstat displaced the count does not move (observed at
        the closing check over three repeats, and reproduced when this docstring was written: with the premise loop
        removed and posix.lstat displaced, the exactness test stays green), so for it the premise is the only detector
        and the equality would say nothing. The world refuses to run over such a process: an AssertionError naming the
        displaced wrapper, raised before any signature runs, and not the equality. Removing the premise loop from
        _stats_world reds every leg here with no AssertionError raised: the world runs to its end and returns, since the
        equality lives in the exactness test and not in the world (the main test would then red on the equality for the
        first three, two numbers and no reason, and stay green with posix.lstat displaced)."""
        for mod, name in ((os, "stat"), (os, "lstat"), (posix, "stat"), (posix, "lstat")):
            with self.subTest(wrapper="%s.%s" % (mod.__name__, name)):
                builtin = getattr(mod, name).__wrapped__
                with mock.patch.object(mod, name, builtin):
                    with self.assertRaises(AssertionError) as cm:
                        self._stats_world()
                msg = str(cm.exception)
                self.assertIn("premise: the kernel's counting wrapper stands on %s.%s" % (mod.__name__, name), msg,
                              "the failure names the displaced wrapper: %s" % msg)
                self.assertNotIn("equals every stat intercepted", msg, "not the equality")

    def test_a_marker_carrying_wrapper_that_does_not_count_once_fails_the_premise_not_a_count(self):
        """Constructed case 4, for the fourth premise's second half (the closing check on the exactness world, 2026-09-19).
        The marker half alone has a blind family: functools.wraps copies __dict__, so any wraps copy of the kernel's
        wrapper carries _romp_sig_counting and passes the marker check whether or not it counts, and a class attribute
        holding the thread-local passes it on a callable that is no function at all. Three such worlds on each of the
        four wrappers: a wraps spy delegating to the builtin (the marker rides, the count does not move), a wraps copy
        that counts once itself and then calls the kernel's wrapper (the count moves by 2), and a callable instance
        whose class holds the marker and whose call delegates to the builtin (the count does not move). Each is refused
        by the counted-call half before any signature runs, with the wrapper's name and the count that moved, and not
        by the equality, which with the marker half alone read two numbers and no reason for the first two kinds on
        os.stat at the closing check. Closed on all four wrappers, posix.lstat included, where the equality alone would
        detect nothing (its count does not move when it is displaced). The accept case beside them: an equivalent
        wrapper, a wraps copy that delegates to the kernel's wrapper itself, the shape a _StatInterceptor wrapper left
        behind would have, moves the accumulator by exactly 1 and the world runs to its end (the exactness equality is
        the exactness test's and is not asserted here). Three neighbours are separate premises this test does not build.
        A wrapper that counts once but stands on the WRONG builtin (os.stat delegating to lstat; a world built for it
        must pass follow_symlinks through or drop it, since pathlib hands os.stat that keyword and the builtin lstat
        refuses it, so the naive world errors inside the run instead of showing the gap). A wrapper that counts
        CONDITIONALLY, on str paths only or on its first call only: the counted-call half proves one str call and no
        more, so such a wrapper can pass both halves and red the equality with two numbers and no reason, short by the
        calls it skipped (os.stat counting str paths alone did, at the follow-up verification of the closing check,
        2026-09-19; whether the first-call kind reaches the equality depends on which calls the world makes before the
        probe). And the DirEntry doors (_entry_stat and its twins). Deleting the counted-call assertion from
        _stats_world reds the twelve refuse legs here with no AssertionError raised (the world runs to its end and
        returns, since the equality lives in the exactness test) while the four displaced legs and the accept leg stay
        green."""
        import functools
        tl = km._CHAT_SIG_TL

        def spy_of(fn):                                    # a wraps copy over the builtin: the marker rides, nothing counts
            builtin = fn.__wrapped__

            @functools.wraps(fn)
            def spy(path, *a, **kw):
                return builtin(path, *a, **kw)
            return spy

        def twice_of(fn):                                  # counts once itself, then the kernel's wrapper counts again
            @functools.wraps(fn)
            def twice(path, *a, **kw):
                if tl.active:
                    tl.stats += 1
                return fn(path, *a, **kw)
            return twice

        class Marked:                                      # the marker as a class attribute on a callable instance
            _romp_sig_counting = tl

            def __init__(self, builtin):
                self.builtin = builtin

            def __call__(self, path, *a, **kw):
                return self.builtin(path, *a, **kw)

        def equivalent_of(fn):                             # the accept case: a wraps copy delegating to the kernel's wrapper
            @functools.wraps(fn)
            def same(path, *a, **kw):
                return fn(path, *a, **kw)
            return same
        kinds = (("a wraps spy over the builtin", spy_of), ("a wraps copy that counts twice", twice_of),
                 ("the marker on a class attribute", lambda fn: Marked(fn.__wrapped__)))
        for mod, name in ((os, "stat"), (os, "lstat"), (posix, "stat"), (posix, "lstat")):
            for kind, make in kinds:
                with self.subTest(wrapper="%s.%s" % (mod.__name__, name), kind=kind):
                    fn = getattr(mod, name)
                    self.assertIs(getattr(fn, "_romp_sig_counting", None), tl, "premise: the kernel's wrapper is in place before the plant")
                    with mock.patch.object(mod, name, make(fn)):
                        with self.assertRaises(AssertionError) as cm:
                            self._stats_world()
                    msg = str(cm.exception)
                    self.assertIn("premise: the kernel's counting wrapper on %s.%s counts" % (mod.__name__, name), msg,
                                  "the failure names the wrapper that did not count once: %s" % msg)
                    self.assertNotIn("equals every stat intercepted", msg, "not the equality")
        with self.subTest(wrapper="os.stat", kind="an equivalent wrapper, accepted"):
            with mock.patch.object(os, "stat", equivalent_of(os.stat)):
                self._stats_world()                        # returns: both halves of premise 4 hold, and the world runs

    REG_PEERS = ["11111111-2222-4333-8444-0000000009%02d" % i for i in range(20, 30)]   # the stats world's registry peers

    def _world_files(self):
        """The seven files furnish() writes into the shared state roots, by path (jd.MESSAGES last)."""
        jd = km.jd
        return (jd.STATESDIR / (self.SID + ".jsonl"), jd.GOALDIR / (self.SID + ".json"), jd._overrides_dir() / (self.SID + ".jsonl"),
                jd.GOALARCHDIR / (self.SID + ".json"), km.WORKING_DIR / self.SID, km.NAMES / self.SID, jd.MESSAGES)

    def _world_regs(self):
        """The registry regs the world writes (three before any push, one more before each cycle), by path."""
        return tuple(km.jd.STATE / "sdk" / (p + ".json") for p in self.REG_PEERS)

    @staticmethod
    def _root_files():
        """Every file under the shared state roots (the judge's jd.STATE and the kernel's two, bound at its import), by path,
        with a digest of its bytes: the outside picture a world must leave as it found it, whatever it writes."""
        seen = {}
        for root in (km.jd.STATE, km.WORKING_DIR.parent, km.NAMES.parent):
            root = pathlib.Path(root)
            if root.is_dir():
                for p in root.rglob("*"):
                    if p.is_file():
                        seen[str(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
        return seen

    def test_the_stats_world_leaves_no_artifact_in_the_shared_state_roots_and_restores_the_postal_store(self):
        """The world's furnish() writes seven files into the shared state roots (five under the judge's: the states atom,
        the goal store, its override journal, the goal archive, the postal store jd.MESSAGES; two under the kernel's, bound
        at its import: the working note, the names row) and nine registry regs, which at run time are a SIBLING module's
        roots, and it once left the seven behind and TRUNCATED the postal store (the round-2 review's tests-1). Every write
        goes through write_restoring now: at cleanup the prior bytes come back, or the file is unlinked. Pinned from
        OUTSIDE the world over a seeded postal store: every file under the three roots is listed with a digest before the
        world and after its cleanups, and the two pictures are the same (nothing added, the regs included; nothing removed;
        nothing changed), with the store holding the seed byte for byte. A premise refuses a leftover of the six other
        files before the run, since a prior read from the live root would make an artifact its own prior (the round-3
        review, 2026-09-19: the first version passed over a plain write of the working note whenever the exactness test
        had run first in the process). The unlink edge is pinned here over files that were absent; the sibling test below
        pins the prior-bytes edge over every file. Cleanup by path rather than jd._rebind_state, because km.WORKING_DIR and
        km.NAMES bind at kernel import with no rebind hook, so the two families can sit in different roots."""
        jd = km.jd
        files = self._world_files()
        leftovers = [str(p) for p in files[:-1] + self._world_regs() if p.exists()]
        self.assertEqual(leftovers, [], "premise: no file the world writes is there before it runs, the regs included (a leftover of a "
                                        "sibling, or of this world's earlier run in the process, would stand in for a missing unlink)")
        orig = jd.MESSAGES.read_bytes() if jd.MESSAGES.exists() else None
        seed = b"".join(json.dumps({"ev": "sent", "id": "seed%d" % i, "from": "api", "from_id": self.SIDS_PEER, "to": "web",
                                    "to_id": self.SID, "body": "seed row %d" % i, "kind": "coordinate", "t": self.NOW - i}).encode() + b"\n"
                        for i in (1, 2))
        jd.MESSAGES.parent.mkdir(parents=True, exist_ok=True)
        jd.MESSAGES.write_bytes(seed)
        try:
            before = self._root_files()
            self._stats_world()
            self.doCleanups()
            after = self._root_files()
            self.assertEqual(jd.MESSAGES.read_bytes(), seed, "the postal store holds the seed, byte for byte")
            self.assertEqual(sorted(set(after) - set(before)), [], "files the world added to a shared root and left there")
            self.assertEqual(sorted(set(before) - set(after)), [], "files of a shared root the world removed")
            self.assertEqual(sorted(p for p in before if p in after and after[p] != before[p]), [],
                             "files of a shared root the world changed")
        finally:
            if orig is None:
                try:
                    jd.MESSAGES.unlink()
                except FileNotFoundError:
                    pass
            else:
                jd.MESSAGES.write_bytes(orig)

    def test_the_stats_world_puts_back_the_prior_bytes_of_every_file_it_overwrites(self):
        """The prior-bytes edge of write_restoring, for every one of the seven files and not the postal store alone: each is
        seeded with bytes of its own before the world runs, and after the world and its cleanups each holds its seed, so a
        restore that unlinks, writes empty bytes or writes another path's bytes reds by name. The sibling test above pins
        the unlink edge over files that were absent (the round-3 review, 2026-09-19: the first version read each path's
        prior from the live root, so in the module's order an artifact the exactness test had left with the same bytes was
        its own prior, and the edge held only when the test ran first in its process)."""
        files = self._world_files()
        leftovers = [str(p) for p in files[:-1] + self._world_regs() if p.exists()]
        self.assertEqual(leftovers, [], "premise: no file the world writes is there before it runs, the regs included")
        orig = {p: (p.read_bytes() if p.exists() else None) for p in files}
        seeds = {p: ("seed %d for %s\n" % (i, p.name)).encode() for i, p in enumerate(files)}
        for p, b in seeds.items():
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b)
        try:
            self._stats_world()
            self.doCleanups()
            for p, b in seeds.items():
                self.assertEqual(p.read_bytes() if p.exists() else None, b, "the prior bytes came back: %s" % p)
        finally:
            for p, b in orig.items():
                if b is None:
                    try:
                        p.unlink()
                    except FileNotFoundError:
                        pass
                else:
                    p.write_bytes(b)

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

    def test_a_thread_signature_outside_a_push_counts_the_shared_components_and_one_under_a_pushs_scope_does_not(self):
        """The block comment's shared-components gloss by execution (2026-09-19 review, the meaning lens): inside a push the
        components every tab shares (_chat_sig_shared) are read once before the loop, on no signature's count; a signature
        taken OUTSIDE a push (a comments frame's thread signature, the WS comment routes) reads them inside its own scope,
        so they count on it. The same thread signature under _live_scope.chat_shared set as a push sets it and under None:
        the difference in stats is exactly what _chat_sig_shared alone stats inside a scope (the memos it rests on are
        warmed first, so cold and warm do not mix), the same for the names read, and every count equals the outside
        interception."""
        tsid = self.SIDS_PEER
        td = tempfile.TemporaryDirectory(); self.addCleanup(td.cleanup)
        path = os.path.join(td.name, tsid + ".jsonl")
        with open(path, "w") as f:
            f.write("{}\n")
        sess = {"sid": tsid, "name": "api", "anchor": None, "path": path, "mtime": self.NOW}
        saved = dict(km._built_thread)
        self.addCleanup(lambda: (km._built_thread.clear(), km._built_thread.update(saved), km._thread_fold_keep[1].discard(tsid)))

        def take(shared):
            km._built_thread.pop(tsid, None)
            with mock.patch.object(km._live_scope, "chat_shared", shared, create=True), mock.patch.object(km._live_scope, "names", None, create=True):
                before = km._chat_sig_stats_report()
                with _StatInterceptor(km._CHAT_SIG_TL) as ic:
                    km._thread_events(tsid, None, self.NOW, {})
                after = km._chat_sig_stats_report()
            d = {k: after[k] - before[k] for k in after}
            self.assertEqual((d["thread"], d["stats"]), (1, ic.total), "one thread signature, its stats what ran: %r" % (d,))
            return d
        with mock.patch.object(km, "_thread_reg", lambda t: {}), mock.patch.object(km, "_sdk_sess", lambda sid, now: dict(sess)), \
                mock.patch.object(km, "build_session", lambda sid, now, live_map=None, **kw: {"type": "session", "id": sid, "events": []}):
            take(km._chat_sig_shared())                    # warms every memo the signature and the shared components rest on
            inside = take(km._chat_sig_shared())           # as a push leaves the components for its loop
            outside = take(None)                           # as a comments frame takes it outside a push
            again = take(km._chat_sig_shared())
            before = km._chat_sig_stats_report()
            with _StatInterceptor(km._CHAT_SIG_TL) as ic, km._chat_sig_scope():
                km._chat_sig_shared()                      # the components alone, inside a scope, warm
            own = {k: v - before[k] for k, v in km._chat_sig_stats_report().items()}
        self.assertEqual(own["stats"], ic.total)
        self.assertGreater(own["stats"], 0, "the shared components stat (the flags file, the cards file, the cleared log, the names)")
        self.assertEqual(inside["stats"], again["stats"], "premise: warm, the same count twice under a push's scope")
        self.assertEqual(outside["stats"] - inside["stats"], own["stats"],
                         "outside a push the signature pays the shared components' stats: %d against %d" % (outside["stats"], inside["stats"]))
        self.assertEqual(outside["namesReads"] - inside["namesReads"], own["namesReads"], "...and their names read, the same way")

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
            tl = km._CHAT_SIG_TL
            tl_reads = (getattr(tl, "namesReads", 0), getattr(tl, "switchReads", 0))
            km._sdk_transcript_path(self.SID); km._user_todos_on(); sb.read_reg(km.jd.STATE, self.SID); km._chat_ident(path)
            self.assertEqual(km._chat_sig_stats_report(), before, "outside a signature the readers count nothing")
            self.assertEqual((getattr(tl, "namesReads", 0), getattr(tl, "switchReads", 0)), tl_reads,
                             "...and the thread-local itself did not move: _chat_sig_count is gated on the open scope (2026-09-19 review, "
                             "the two-direction lens: the table alone could not tell, since the next scope zeroes the thread-local)")
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

    @staticmethod
    def _thread_rusage_fake():
        """(reads, fake): a getrusage that records and fakes the THREAD reads alone (who 11, the patched _RUSAGE_THREAD),
        advancing one ms of user and half a ms of system time per read, and hands any other `who` (RUSAGE_SELF from
        _process_stats on a platform without /proc) to the real getrusage, so only thread reads move the fake clock."""
        reads = []
        real = km.resource.getrusage

        def fake(who):
            if who != 11:
                return real(who)
            reads.append(who)
            return types.SimpleNamespace(ru_utime=0.001 * len(reads), ru_stime=0.0005 * len(reads), ru_maxrss=0)
        return reads, fake

    def test_the_chat_seams_record_their_thread_cpu_from_a_bounded_number_of_rusage_reads(self):
        """Stage 1 of the chat-signature design (2026-09-18): the chat loop reads getrusage(RUSAGE_THREAD) at each seam's
        open and close and stages_cpu_ms carries the delta beside the wall. Under a fake clock that advances one ms of
        user and half a ms of system time per read: every signature seam moves the sig row by at least one read's worth,
        the send row moves too, the container's CPU covers its seams, and the reads per cycle stay within the stated
        bound (two per mark: the container, the signature and its deps sub-seam, the send; a rebuild adds the build seam
        and the post-build signature: 12 reads on a rebuilt cycle, 8 on a served one, 60 over the six)."""
        ps = km._PERF_STATS
        reads, fake = self._thread_rusage_fake()
        # `before` is read INSIDE the patch (2026-09-19 review, tests-1): with the platform's own _RUSAGE_THREAD None (macOS) the
        # snapshot's block is empty and the before/after join raised KeyError where the two test_perf_stats siblings skip;
        # under the patch the block is populated on every platform. The fake counts only the seams' thread reads (who 11)
        # and delegates any other `who` to the real getrusage, because _process_stats falls back to getrusage(RUSAGE_SELF)
        # where /proc is absent (the same macOS shape): one per cycle's kernelSample, between the cycles, plus two from the
        # harness's snapshots. Faked too, they landed in `reads` as RUSAGE_SELF and failed the former "every read asked for the
        # thread's rusage" assertion; they fall between the seams' pairs, so the 21/6/15 arithmetic and the count bound held
        # (67 of 96). The dispatch keeps only thread reads on the fake clock, so the arithmetic stays exact should a
        # process-stats read ever land inside a seam, and the exact read count and the process block below pin the dispatch.
        with mock.patch.object(km, "_RUSAGE_THREAD", 11), mock.patch.object(km.resource, "getrusage", fake):
            before = ps.snapshot()["stages_cpu_ms"]
            del reads[:]
            _wire, calls, rows = self._run(km._chat_diff, perf=ps)
            snap = ps.snapshot()
            after = snap["stages_cpu_ms"]
        self.assertEqual(calls, [False, True, False, True, False, True], "premise: rebuilt, served, alternating")
        self.assertLessEqual(len(reads), 6 * 16, "at most sixteen thread reads per cycle: %d over six" % len(reads))
        # the dispatch pinned in both directions: exactly the thread reads (a rebuilt cycle reads twice each for the container,
        # the signature, its deps tail, the build, the post-build signature and the send, 12; a served cycle twice each for the
        # container, the signature, the deps tail and the send, 8; three of each), which a fake recording every `who` exceeds
        # (67 under the macOS shape); and the process block of the in-patch snapshot is the real clock's (rss_kb above 0),
        # which a fake answering RUSAGE_SELF itself with zeros fails where /proc is absent
        self.assertEqual(len(reads), 3 * 12 + 3 * 8, "the thread reads alone: %d" % len(reads))
        self.assertGreater(snap["process"]["rss_kb"], 0, "the process block was read from the real clock, not the fake")
        d = {k: {c: after[k][c] - before[k][c] for c in ("user", "sys")} for k in after if k in before}
        self.assertGreaterEqual(d["push.chat.sig"]["user"], 9 * 1.0 - 1e-6, "nine signatures, each at least one read apart")
        self.assertAlmostEqual(d["push.chat.sig"]["sys"], d["push.chat.sig"]["user"] / 2.0, msg="the fake's ratio survives the fold")
        self.assertGreater(d["push.chat.send"]["user"], 0.0)
        self.assertGreater(d["push.chat.build"]["user"], 0.0)
        self.assertGreaterEqual(d["push.chat"]["user"] + 1e-6, sum(d[k]["user"] for k in ("push.chat.sig", "push.chat.build", "push.chat.send")),
                                "the container's CPU covers its seams")
        # ...and is a SUPERSET of them, not their sum (2026-09-19 review, extra5-3: the glue between the seams has no CPU row of
        # its own). Under the fake clock every read advances the clock one ms of user, so a container's delta is the reads
        # inside it plus one: a rebuilt cycle has ten reads inside push.chat (the signature's four, the build's two, the
        # post-build signature's two, the send's two) and a served one six, so over three of each push.chat reads
        # 3 * 11 + 3 * 7 = 54 against seams of 21 + 3 + 6 = 30; the 24 of glue are the seams' own opening and closing reads
        self.assertAlmostEqual(d["push.chat"]["user"], 54.0, places=6, msg="the container: its reads plus one, per cycle")
        self.assertAlmostEqual(sum(d[k]["user"] for k in ("push.chat.sig", "push.chat.build", "push.chat.send")), 30.0, places=6,
                               msg="the seams: the signature's 21, the build's 3, the send's 6")
        self.assertGreater(d["push.chat"]["user"], 30.0, "a superset, not a sum")
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

    def test_a_deps_tail_whose_cpu_read_failed_leaves_the_static_row_without_cpu_and_the_seam_with_its_own(self):
        """kernel-1 (the round-2 review, 2026-09-19; latent): a stage's CPU follows its wall exactly, and a row whose CPU
        cannot follow records its wall alone. The static sub-seam's wall excludes the deps tail's, so when the tail RAN but
        its CPU read failed (deps_cpu None beside deps_ran True) the static row's CPU is unknown too and it records none,
        while the seam's own row keeps the CPU it read. Before this, _chat_sig_seam_close handed the static row the WHOLE
        seam's CPU beside a wall that excluded the tail, so that row's documented wall minus user minus sys read low or
        negative. Driven under the fake thread clock (one ms of user and half a ms of system per read): a spy on
        _chat_sig_deps arms a one-shot on its first call, and a wrapper on _cpu_delta, once armed, disarms and answers None
        WITHOUT reading, so exactly the first pre-build signature's deps close read is dropped: 59 reads over the six
        cycles, one fewer than the rusage test's 60. That seam is then two reads apart with a deps CPU of None, so over
        the window: sig 20 (the other five pre-build seams three reads each, the three post-build ones one each), deps 5
        (the five tails whose read succeeded), static 13 (five at two, three at one), in ms of user, half that in sys.
        The seam close before the fix read static 15, that seam's 2 folded into static; an over-fix that drops the seam's
        own CPU too reads sig 18. The wall rows of all three moved on every cycle whatever the CPU read did. The jobs
        container's twin (a push that ran with no CPU reading leaves the jobs row without CPU) is pinned in
        tests/test_perf_stats.py, which owns the _pusher_cycle_jobs driver."""
        ps = km._PERF_STATS
        reads, fake = self._thread_rusage_fake()
        drop, tails = [False], [0]
        real_deps, real_delta = km._chat_sig_deps, km._cpu_delta

        def deps_spy(sid, deps):
            tails[0] += 1
            if tails[0] == 1:                            # the first tail: its close read, the next _cpu_delta call, is dropped
                drop[0] = True
            return real_deps(sid, deps)

        def delta(c0):
            if drop[0]:
                drop[0] = False
                return None                              # the read that failed: no getrusage call, so the fake clock does not move
            return real_delta(c0)
        with mock.patch.object(km, "_RUSAGE_THREAD", 11), mock.patch.object(km.resource, "getrusage", fake), \
                mock.patch.object(km, "_chat_sig_deps", deps_spy), mock.patch.object(km, "_cpu_delta", delta):
            s0 = ps.snapshot()
            del reads[:]
            _wire, calls, _rows = self._run(km._chat_diff, perf=ps)
            s1 = ps.snapshot()
        self.assertEqual(calls, [False, True, False, True, False, True], "premise: rebuilt, served, alternating")
        self.assertEqual(tails[0], 6, "premise: the tail ran once per cycle, in the pre-build signature")
        self.assertFalse(drop[0], "premise: the one-shot fired (the first tail's close read was dropped)")
        self.assertEqual(len(reads), 3 * 12 + 3 * 8 - 1, "one thread read fewer than the rusage test's 60: the dropped deps close")
        d = {k: {c: s1["stages_cpu_ms"][k][c] - s0["stages_cpu_ms"][k][c] for c in ("user", "sys")}
             for k in s1["stages_cpu_ms"] if k in s0["stages_cpu_ms"]}
        for c, per_read in (("user", 1.0), ("sys", 0.5)):
            self.assertAlmostEqual(d["push.chat.sig"][c], 20 * per_read, places=6,
                                   msg="%s: the seam keeps its own CPU; the seam with the dropped read is two reads apart" % c)
            self.assertAlmostEqual(d["push.chat.sig.deps"][c], 5 * per_read, places=6, msg="%s: the five tails whose read succeeded" % c)
            self.assertAlmostEqual(d["push.chat.sig.static"][c], 13 * per_read, places=6,
                                   msg="%s: the static row without that seam's CPU (15 before the fix: the whole seam folded in)" % c)
        for k in ("push.chat.sig", "push.chat.sig.deps", "push.chat.sig.static"):
            self.assertGreater(s1["stages_ms"].get(k, 0.0) - s0["stages_ms"].get(k, 0.0), 0.0,
                               "%s: the wall row moved over the six cycles whatever the CPU read did" % k)

    def test_the_chat_stage_is_split_into_its_seams(self):
        """Stage 1 of the incremental-push design (2026-09-18): push.chat is a container of three seams in stages_ms
        and in the cycle's split: sig (the tab's signature, every tab past the cold gate every cycle, the post-build one included),
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
        reads, fake = self._thread_rusage_fake()          # thread reads alone: RUSAGE_SELF (a /proc-less platform's) goes to the real clock
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
                    print("[live] repo_index_key %s %s: counted=%d body=%d intercepted=%r" % (label, memo, n, body, seen))
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

    def test_the_door_and_its_twins_count_one_direntry_stat_each_inside_a_scope_none_outside_and_a_raising_one_as_attempted(self):
        """The doors by execution (2026-09-19 review, the two-direction lens: no signature in the suite reached judge.py's or
        event_model.py's twin, so a twin counting nothing, or two per call, was green; the source pin holds the shape, not
        the count). One real scandir entry, inside km._chat_sig_scope() under the outside interception: km._entry_stat and
        its twins in judge.py, event_model.py and sdk_backend.py each fold exactly one stat, and the interception agrees;
        outside a scope each moves the thread-local not at all. And a door's stat that RAISES (the file unlinked between
        the scandir and the stat) counts as attempted, like a missing file's os.stat: one counted, one intercepted, the
        FileNotFoundError re-raised. Counting after the call (success only) reads 0 there."""
        sb = self._reg_reader()
        td = tempfile.TemporaryDirectory(); self.addCleanup(td.cleanup)
        p = os.path.join(td.name, "f")
        with open(p, "w") as f:
            f.write("x")

        def entry():
            with os.scandir(td.name) as it:
                return next(it)                          # a fresh DirEntry each time: a DirEntry caches its stat answer
        for name, door in (("kernel", km._entry_stat), ("judge", km.jd._entry_stat), ("event_model", km.em._entry_stat),
                           ("sdk_backend", sb._entry_stat)):
            with self.subTest(door=name):
                with _StatInterceptor(km._CHAT_SIG_TL) as ic:
                    e = entry()
                    before = km._chat_sig_stats_report()["stats"]
                    with km._chat_sig_scope():
                        st = door(e)
                    self.assertEqual(st.st_size, 1, "the entry's own stat answered")
                    self.assertEqual((km._chat_sig_stats_report()["stats"] - before, ic.dirent, ic.total), (1, 1, 1),
                                     "one DirEntry stat: folded once, intercepted once, and nothing else")
                    e2 = entry()
                    tl_stats = km._CHAT_SIG_TL.stats
                    door(e2)
                    self.assertEqual(km._CHAT_SIG_TL.stats, tl_stats, "outside a scope the door moves the thread-local not at all")
                    self.assertEqual(ic.dirent, 1, "...and the interception, gated the same way, saw nothing new")
        with _StatInterceptor(km._CHAT_SIG_TL) as ic:      # the entry is taken under the interception, whose scandir counts its stats
            e = entry()
            os.unlink(p)
            before = km._chat_sig_stats_report()["stats"]
            with km._chat_sig_scope():
                with self.assertRaises(FileNotFoundError):
                    km._entry_stat(e)
        self.assertEqual((km._chat_sig_stats_report()["stats"] - before, ic.dirent), (1, 1), "the syscall was made: counted as attempted")

    def test_the_per_thread_accumulators_count_only_the_owning_threads_reads(self):
        """Both per-thread accumulators (the kernel's _CHAT_SIG_TL and sdk_backend's _REG_READ_TL) are thread-locals: a scope
        open on one thread sees none of another thread's reads (2026-09-19 review, tests-3; both passed every test when
        replaced by objects shared across threads). Event-gated: thread one opens the scope and waits; thread two, outside
        any scope, makes three stats, two registry reads and a names-read count; thread one then makes one stat and one
        registry read and closes. Asserted: the fold reads (stats, regReads, namesReads) = (1, 1, 0), the scope's own
        thread's reads alone. Each shared replacement reds that pin by construction: a kernel accumulator shared across
        threads folds thread two's three stats and its names count too (and any stat the test process makes in the
        background, so its stats reading is not a fixed number), and a shared backend counter folds thread two's two
        registry reads, so regReads reads 3. The stats are real calls through the kernel's os.stat wrapper, under the
        outside interception, whose rule agrees."""
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


def _direntry_stat_sites(source):
    """(offenders, doors, routed) for one module's source, each a list of (line, entry name, enclosing def): the DirEntry
    stat sites, derived from the AST rather than matched by spelling. Per def (and the module body outside any def): a
    LISTING is a name bound to an expression containing a scandir call or naming an earlier listing (`entries =
    list(os.scandir(d))`, `sorted(...)`, `with os.scandir(d) as it: entries = list(it)`); an ENTRY is the target of a for
    or a comprehension whose iterable contains a scandir call or names a listing. A `.stat(` call on an entry is an offender, unless the def is named _entry_stat, whose `.stat(` on
    its first parameter is a door; an `_entry_stat(<entry>)` call is a routed site. The kernel pin below asserts no
    offender, one door per kernel module that carries one, and the routed sites it names."""
    tree = ast.parse(source)

    def scandir_in(node):
        return any(isinstance(n, ast.Call) and (getattr(n.func, "attr", None) == "scandir" or getattr(n.func, "id", None) == "scandir")
                   for n in ast.walk(node))

    def names_of(target):
        if isinstance(target, ast.Name):
            return [target.id]
        if isinstance(target, (ast.Tuple, ast.List)):
            return [n for t in target.elts for n in names_of(t)]
        return []

    def refs(node, names):
        return any(isinstance(x, ast.Name) and x.id in names for x in ast.walk(node))

    def own(node):                                        # the scope's own nodes: no descent into a nested def, which is its own scope
        for child in ast.iter_child_nodes(node):
            yield child
            if not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                yield from own(child)
    scopes = [tree] + [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    offenders, doors, routed = [], [], []
    for scope in scopes:
        where = scope.name if isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef)) else "<module>"
        nodes = list(own(scope))
        listings, grew = set(), True
        while grew:                                       # to a fixpoint: `with os.scandir(d) as it: entries = list(it)` binds two
            grew = False
            for n in nodes:
                bound = None
                if isinstance(n, ast.Assign) and (scandir_in(n.value) or refs(n.value, listings)):
                    bound = [x for t in n.targets for x in names_of(t)]
                elif isinstance(n, ast.withitem) and n.optional_vars is not None and (scandir_in(n.context_expr) or refs(n.context_expr, listings)):
                    bound = names_of(n.optional_vars)
                if bound and not set(bound) <= listings:
                    listings.update(bound); grew = True
        entries = set()
        for n in nodes:
            if isinstance(n, (ast.For, ast.comprehension)) and (scandir_in(n.iter) or refs(n.iter, listings)):
                entries.update(names_of(n.target))
        if where == "_entry_stat" and scope.args.args:
            entries.add(scope.args.args[0].arg)
        if not entries:
            continue
        for n in nodes:
            if not isinstance(n, ast.Call):
                continue
            if isinstance(n.func, ast.Attribute) and n.func.attr == "stat" and isinstance(n.func.value, ast.Name) and n.func.value.id in entries:
                (doors if where == "_entry_stat" else offenders).append((n.lineno, n.func.value.id, where))
            elif isinstance(n.func, ast.Name) and n.func.id == "_entry_stat" and n.args and isinstance(n.args[0], ast.Name) and n.args[0].id in entries:
                routed.append((n.lineno, n.args[0].id, where))
    return offenders, doors, routed


class StatCountingInstall(unittest.TestCase):
    """The stat interception the stats counter rests on (2026-09-19 review, regression-1): installed once per process at
    kernel import, shared by every kernel load, and the doors for a DirEntry's stat in kernel/ (_entry_stat and its twins)."""

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

    def test_the_wrappers_keep_the_builtins_membership_in_the_os_capability_sets(self):
        """regression-1 (the round-2 review, 2026-09-19): rebinding os.stat and os.lstat to the wrappers took them out of
        the os.supports_* sets (os.py builds the four at import, keyed by the builtin function objects), so for the life of
        any process that loaded the kernel every capability probe on the two answered unsupported: pytest's tmpdir guard
        (`False if os.stat in os.supports_follow_symlinks else True`) and shutil.copystat's lookup among them. The install
        carries the membership now: wherever the builtin is a member the wrapper is too, and where it is not (os.stat in
        supports_effective_ids; os.lstat in supports_follow_symlinks; os.lstat in supports_dir_fd below 3.13) the wrapper
        is not either, so a probe reads the same answer through the wrapper as through the builtin. Pinned by equality
        per set and function (the platform-derived edges included), by the three memberships the builtin stat holds on
        Linux (red at HEAD before the carry), by a consumer executed (shutil.copystat over two symlinks with
        follow_symlinks=False takes the lookup road that asks the set and answered a no-op stat before the carry: None
        has no st_mode), by pytest's guard expression reading False, and across a second kernel load (the early return
        installs nothing and disturbs nothing). NOT under a _StatInterceptor, which re-patches os.stat for its window with
        wrappers of its own that are in no set."""
        sets = ("supports_dir_fd", "supports_effective_ids", "supports_fd", "supports_follow_symlinks")
        for fn in (os.stat, os.lstat):
            for name in sets:
                s = getattr(os, name)
                self.assertEqual(fn in s, fn.__wrapped__ in s, "%s: the wrapper's membership equals the builtin's (%s)" % (name, fn.__name__))
        three = ("supports_follow_symlinks", "supports_dir_fd", "supports_fd")
        if sys.platform.startswith("linux"):
            for name in three:
                self.assertIn(os.stat.__wrapped__, getattr(os, name), "premise: the builtin stat is a member of %s on Linux" % name)
        for name in three:
            if os.stat.__wrapped__ in getattr(os, name):
                self.assertIn(os.stat, getattr(os, name), "%s: the wrapper is a member where the builtin is (HEAD before the carry: not)" % name)
        with tempfile.TemporaryDirectory() as td:
            a, b = os.path.join(td, "a"), os.path.join(td, "b")
            for p in (a, b):
                with open(p, "w") as f:
                    f.write("x\n")
            la, lb = os.path.join(td, "la"), os.path.join(td, "lb")
            os.symlink(a, la); os.symlink(b, lb)
            shutil.copystat(la, lb, follow_symlinks=False)     # the consumer: its lookup asks os.supports_follow_symlinks about os.stat
        self.assertFalse(False if os.stat in os.supports_follow_symlinks else True,
                         "pytest's tmpdir guard expression reads False: the root's stat may refuse to follow a symlink")
        km2 = load_source("romp_kernel_second_load_for_the_membership_pin", os.path.join(BIN, "romp-kernel"))
        self.assertIs(km2._CHAT_SIG_TL, km._CHAT_SIG_TL, "premise: the second load took the early return")
        for fn in (os.stat, os.lstat):
            for name in sets:
                s = getattr(os, name)
                self.assertEqual(fn in s, fn.__wrapped__ in s, "%s after a second kernel load (%s)" % (name, fn.__name__))
        self.assertIn(os.stat, os.supports_follow_symlinks, "membership intact after a second load")

    def test_a_stdlib_class_that_bound_the_builtin_at_import_reaches_the_wrapper_inside_a_signature(self):
        """regression-1's round-3 finding (2026-09-19): 3.13's glob._StringGlobber binds os.lstat into its class dict at
        import (pathlib imports glob, before the kernel loads), so Path.glob over a literal trailing part called the
        builtin past the wrapper and a signature counted none of its stats, while os.path.lexists beside it counted one;
        the install patches that binding the way it patches 3.10's pathlib accessor. Pinned by execution on every
        interpreter: a literal glob over an existing file inside a signature counts at least one stat (the versions differ
        in how many stats a glob makes, so the count is not pinned exactly), and where the class carries the attribute it
        holds the kernel's wrapper. Red on 3.13 before the patch (0 counted), green on 3.10, 3.12 and 3.14t before it."""
        tl = km._CHAT_SIG_TL
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, "a"), "w") as f:
                f.write("x\n")
            with km._chat_sig_scope():
                found = list(pathlib.Path(td).glob("a"))
                n = tl.stats
        self.assertEqual([p.name for p in found], ["a"], "premise: the literal glob found the file")
        self.assertGreaterEqual(n, 1, "the glob's stat reached the counting wrapper inside the signature (3.13 before the patch: 0)")
        globber = getattr(sys.modules.get("glob"), "_StringGlobber", None)
        held = globber.__dict__.get("lstat") if globber is not None else None
        if held is not None:
            self.assertIs(held.__func__, os.lstat, "the globber's bound lstat is the kernel's wrapper, not the builtin")

    def test_the_direntry_stat_scanner_derives_entry_names_and_flags_a_stat_on_one_outside_the_door_in_both_directions(self):
        """The pin below is only as good as its derivation, so the scanner is checked on synthetic modules in both directions:
        a `.stat(` on a name bound as a scandir entry through each spelling the kernel uses (a for over a listing bound by
        assignment, over sorted(os.scandir()), over a `with ... as it`, over a list bound from that `it`, a comprehension) is an
        offender whatever the name; a
        `.stat(` inside a def named _entry_stat on its entry parameter is a door; a `.stat(` on a name NOT bound from a
        scandir, a routed `_entry_stat(e)` call and an entry's other methods are none of these."""
        cases = (
            ("def f(d):\n    entries = list(os.scandir(d))\n    for de in entries:\n        st = de.stat()\n", [(4, "de", "f")], [], []),
            ("def f(d):\n    for e in sorted(os.scandir(d), key=lambda e: e.name):\n        e.stat()\n", [(3, "e", "f")], [], []),
            ("def f(d):\n    with os.scandir(d) as it:\n        for ent in it:\n            ent.stat(follow_symlinks=False)\n", [(4, "ent", "f")], [], []),
            ("def f(d):\n    return [x.stat() for x in os.scandir(d)]\n", [(2, "x", "f")], [], []),
            ("def f(d):\n    with os.scandir(d) as it:\n        entries = list(it)\n    for e in entries:\n        e.stat(follow_symlinks=False)\n", [(5, "e", "f")], [], []),
            ("def _entry_stat(e, **kw):\n    return e.stat(**kw)\n", [], [(2, "e", "_entry_stat")], []),
            ("def f(d):\n    for e in os.scandir(d):\n        e.is_dir()\n    for f in items:\n        f.stat()\n", [], [], []),
            ("def f(d):\n    for e in os.scandir(d):\n        st = _entry_stat(e)\n", [], [], [(3, "e", "f")]),
        )
        for src, offenders, doors, routed in cases:
            self.assertEqual(_direntry_stat_sites(src), (offenders, doors, routed), src)

    def test_every_direntry_stat_in_kernel_goes_through_the_entry_stat_door(self):
        """A DirEntry stats in C and reaches no os.stat wrapper, so kernel/ has doors for it: _entry_stat (kernel.py) and its
        same-bodied twins in judge.py, event_model.py and sdk_backend.py. Source pin, DERIVED rather than spelled: for every
        kernel/*.py, _direntry_stat_sites reads the AST for every name bound as a scandir entry (the target of a for or a
        comprehension over a scandir call or over a listing bound from one) and flags a `.stat(` on such a name outside a
        def named _entry_stat. The first pin matched the spellings `e.stat(` and `entry.stat(` and was green over two
        `de.stat(` sites, _reported_model_ids (kernel.py) and list_regs (sdk_backend.py), the second of which a signature
        reaches on every fork_children memo miss (2026-09-19 review, regression-1); both are routed now and named among
        the routed sites so a revert of either reds this by name as well as by the exactness test."""
        root = os.path.join(os.path.dirname(HERE), "kernel")
        offenders, doors, routed = {}, {}, {}
        for fn in sorted(os.listdir(root)):
            if not fn.endswith(".py"):
                continue
            with open(os.path.join(root, fn), encoding="utf-8") as f:
                o, d, r = _direntry_stat_sites(f.read())
            if o:
                offenders[fn] = o
            if d:
                doors[fn] = d
            if r:
                routed[fn] = r
        self.assertEqual(offenders, {}, "a DirEntry.stat outside _entry_stat: not counted under memos.chatSig.stats")
        self.assertEqual({fn: len(d) for fn, d in doors.items()}, {"kernel.py": 1, "judge.py": 1, "event_model.py": 1, "sdk_backend.py": 1},
                         "the door and its three twins, one stat each")
        by_fn = {(fn, where) for fn, sites in routed.items() for _ln, _name, where in sites}
        self.assertTrue({("kernel.py", "_reported_model_ids"), ("sdk_backend.py", "list_regs"), ("kernel.py", "_task_store_fp")} <= by_fn,
                        "the two sites routed this round and the task store's are among the routed scandir sites: %r" % sorted(by_fn))
        self.assertGreaterEqual(sum(len(r) for r in routed.values()), 16, "the derivation saw the kernel's scandir sites: %r" % sorted(by_fn))


class WrapperDifferential(unittest.TestCase):
    """The install docstring's list of what still differs from the builtin is DERIVED here, on the interpreter under test,
    rather than copied from a reading (the closing check on the install docstring, 2026-09-19: the list stood on a run
    over two adjacent interpreters with no command kept, and two adjacent interpreters cannot establish that the set is
    version-independent; 3.10 and 3.11 lack __type_params__, so it is not). The differential is the closing check's,
    ported in-process. Its predicate, in the reviewer's words: an observation is a named, deterministic procedure of one
    argument, the function object, rendered as text with memory addresses and paths normalized, a raise rendered as its
    type plus normalized message, timing excluded; both arms run in one process, the same procedure on the counting
    wrapper at os.stat and on the builtin it holds in __wrapped__; an observation counts as a difference iff the two
    renderings differ. Every observation of the probe is ported, with these adaptations: the recursion observation sets
    the limit relative to the current frame depth (the probe's absolute limit under pytest's deeper stack would read the
    same sentinel on both arms and silently stop differing); the settrace and setprofile observations save and restore
    the prior hooks; the audit-hook observation is NOT ported (sys.addaudithook is permanent for the process, and it
    read the same on both arms in every saved run of the probe); the probe's second target pair, os.lstat, is not run
    (reported separately there, never in its count); and one observation is ADDED from the reviewer's pickle-cross
    probe, the unnamed second half of the pickling difference: the pickle of the wrapper, unpickled in a subprocess
    that never loaded the kernel, is that process's builtin os.stat with no marker, where the builtin arm does not
    pickle at all. Premises first (the object at os.stat carries the kernel's thread-local, its __wrapped__ is a builtin,
    which an interceptor's is not, posix.stat is the same object, no signature is open); then every differing
    observation must have a class in CLASS_OF, every class's token from TOKEN_OF_CLASS must appear in the docstring
    (whitespace-normalized; for the attribute class the token is the attribute's own name), every key of CLASS_OF must
    be a real observation name, the __type_params__ attribute must differ exactly from 3.12 up and __annotate__ exactly
    from 3.14 up (the closing check's probe ran no 3.14 attribute the builtin lacks; the follow-up verification found
    this one, so the population here is one attribute wider than the reviewer's), the docstring must name
    this test and not the two-interpreter reading, and functools.WRAPPER_ASSIGNMENTS is recomputed: the names that read
    the same on both arms are exactly __module__, __name__, __qualname__ and __doc__, and the docstring carries that
    number in words. The counts are printed on the [live] line and asserted nowhere: they are recomputed, never copied,
    and the ported subset's count is the probe's own on the same interpreter (one more from 3.14, the __annotate__
    attribute the probe never read), the added observation one more. The
    population is the reviewer's: a difference outside these observations is not seen here, and a new observation that
    differs reds until it is mapped and, if its class is new, named."""

    ATTRIBUTES = ("__name__", "__qualname__", "__module__", "__self__", "__text_signature__", "__code__", "__globals__",
                  "__closure__", "__defaults__", "__kwdefaults__", "__dict__", "__annotations__", "__get__", "__wrapped__",
                  "_romp_sig_counting", "__type_params__", "__builtins__", "__annotate__", "__call__", "__hash__")
    # the class of a difference -> the token _stat_counting_install's docstring carries for it, verbatim; the attribute
    # class has no single token, its token is the attribute's own name
    TOKEN_OF_CLASS = {
        "type": "a Python function, not builtin_function_or_method",
        "signature": "read (path, *a, **kw)",
        "vars and dir": "vars() and dir()",
        "mutability": "the wrapper is mutable",      # a phrase: the bare word is a substring of its negation, "immutable"
        "size": "sys.getsizeof",
        "referents": "gc.get_referents",
        "pickling": "pickling by name resolves to posix.stat",
        "reduce": "__reduce__",
        "process boundary": "a process that never loaded this module",
        "identity": "identity, since `is` against a reference",
        "mocking": "autospec",
        "missing argument": "TypeError text on a missing argument",
        "path given twice": "multiple values for argument",
        "stack": "one more frame on a traceback",
        "descriptor": "makes the wrapper a descriptor",
        "counting": "counts on the thread-local",
    }
    # every observation that differs, by class. An observation reading the same on both arms needs no entry; one that
    # differs with no entry reds the test until it is mapped here and, if its class is new, named in the docstring
    CLASS_OF = dict(
        [(n, "type") for n in ("type name", "isinstance types.FunctionType", "isinstance types.BuiltinFunctionType",
                               "inspect.isbuiltin", "inspect.isfunction", "repr", "str", "pydoc header line",
                               "inspect.getfile", "inspect.getsourcefile", "dis.dis")]
        + [(n, "signature") for n in ("inspect.signature follow_wrapped=False", "inspect.getfullargspec",
                                      "Signature.bind with follow_symlinks")]
        + [("attribute %s" % a, "attribute") for a in ("__self__", "__text_signature__", "__code__", "__globals__", "__closure__",
                                                     "__defaults__", "__kwdefaults__", "__dict__", "__annotations__", "__get__",
                                                     "__wrapped__", "_romp_sig_counting", "__type_params__", "__builtins__",
                                                     "__annotate__")]
        + [("dir()", "vars and dir"), ("vars()", "vars and dir"),
           ("set then delete an attribute", "mutability"), ("assign __name__", "mutability"),
           ("sys.getsizeof", "size"), ("gc.get_referents types", "referents"),
           ("pickle.dumps", "pickling"), ("pickle round trip is f", "pickling"), ("__reduce__", "reduce"),
           ("unpickled in a process that never loaded the kernel", "process boundary"),
           ("is the captured builtin os.stat", "identity"), ("is the current os.stat", "identity"),
           ("is the current posix.stat", "identity"), ("equals the captured builtin", "identity"),
           ("mock.create_autospec type", "mocking"),
           ("call with no arguments", "missing argument"), ("call with only keywords, no path", "missing argument"),
           ("call with path given twice", "path given twice"),
           ("traceback frames through the call", "stack"), ("sys.settrace events during one call", "stack"),
           ("sys.setprofile events during one call", "stack"), ("deepest recursion at which the call still runs", "stack"),
           ("as a class attribute, what the instance attribute is", "descriptor"),
           ("as a class attribute, calling it with a path", "descriptor"),
           ("does a call move the kernel's accumulator", "counting")])
    ADDED = "unpickled in a process that never loaded the kernel"

    def _observations(self, scratch, tmpfile, tmplink, captured):
        """The probe's observations as (name, procedure of the function object), the audit-hook one left out and the
        process-boundary one added; `captured` is the builtin arm, the reference the probe took before its install ran."""
        import copy, dis, functools, gc, inspect, pickle, pydoc, traceback, typing, weakref
        obs = []

        def add(name):
            def deco(fn):
                obs.append((name, fn))
                return fn
            return deco
        # type and kind
        add("type name")(lambda f: type(f).__name__)
        add("isinstance types.FunctionType")(lambda f: isinstance(f, types.FunctionType))
        add("isinstance types.BuiltinFunctionType")(lambda f: isinstance(f, types.BuiltinFunctionType))
        add("inspect.isbuiltin")(lambda f: inspect.isbuiltin(f))
        add("inspect.isfunction")(lambda f: inspect.isfunction(f))
        add("inspect.isroutine")(lambda f: inspect.isroutine(f))
        add("inspect.ismethod")(lambda f: inspect.ismethod(f))
        add("inspect.ismethoddescriptor")(lambda f: inspect.ismethoddescriptor(f))
        add("inspect.iscoroutinefunction")(lambda f: inspect.iscoroutinefunction(f))
        add("callable")(lambda f: callable(f))
        add("repr")(lambda f: repr(f))
        add("str")(lambda f: str(f))
        add("pydoc header line")(lambda f: pydoc.render_doc(f).splitlines()[0])
        add("pydoc body line 2")(lambda f: (pydoc.render_doc(f).splitlines() + [""] * 3)[2])
        # signature and source introspection
        add("inspect.signature (default)")(lambda f: str(inspect.signature(f)))
        add("inspect.signature follow_wrapped=False")(lambda f: str(inspect.signature(f, follow_wrapped=False)))
        add("inspect.getfullargspec")(lambda f: str(inspect.getfullargspec(f)))
        add("inspect.getfile")(lambda f: inspect.getfile(f))
        add("inspect.getsourcefile")(lambda f: str(inspect.getsourcefile(f)))
        add("inspect.getsourcelines length")(lambda f: len(inspect.getsourcelines(f)[0]))

        @add("dis.dis")
        def _dis(f):
            buf = io.StringIO()
            dis.dis(f, file=buf)
            return "dis bytes=%d" % len(buf.getvalue())
        add("inspect.getmodule")(lambda f: getattr(inspect.getmodule(f), "__name__", None))
        add("inspect.getdoc first line")(lambda f: (inspect.getdoc(f) or "").splitlines()[0])
        add("inspect.unwrap is the captured builtin")(lambda f: inspect.unwrap(f) is captured)
        # attributes
        for a in self.ATTRIBUTES:
            def read(f, a=a):
                if not hasattr(f, a):
                    return "absent"
                v = getattr(f, a)
                return "present=%r" % (v,) if a in ("__name__", "__qualname__", "__module__") else "present type=%s" % type(v).__name__
            add("attribute %s" % a)(read)
        add("dir()")(lambda f: ",".join(sorted(dir(f))))
        add("vars()")(lambda f: ",".join(sorted(vars(f))))

        @add("set then delete an attribute")
        def _setattr(f):
            f.__probe_tmp__ = 1
            del f.__probe_tmp__
            return "attribute set and deleted"

        @add("assign __name__")
        def _rename(f):
            old = f.__name__
            try:
                f.__name__ = "renamed"
                return "renamed ok"
            finally:
                try:
                    f.__name__ = old
                except Exception:
                    pass
        add("weakref.ref")(lambda f: type(weakref.ref(f)).__name__)
        add("sys.getsizeof")(lambda f: sys.getsizeof(f))
        add("gc.is_tracked")(lambda f: gc.is_tracked(f))
        add("copy.deepcopy is f")(lambda f: copy.deepcopy(f) is f)
        add("pickle.dumps")(lambda f: "ok len=%d" % len(pickle.dumps(f)))
        add("pickle round trip is f")(lambda f: pickle.loads(pickle.dumps(f)) is f)
        add("__reduce__")(lambda f: str(f.__reduce__()))

        @add(self.ADDED)
        def _unpickled_elsewhere(f):
            blob = pickle.dumps(f)                        # the builtin arm raises here: posix.stat names the wrapper, not it
            code = ("import os, pickle, sys\n"
                    "f = pickle.loads(sys.stdin.buffer.read())\n"
                    "print('is that process os.stat:', f is os.stat, '; carries the marker:', hasattr(f, '_romp_sig_counting'),"
                    " '; a kernel loaded there:', any(m.startswith('romp_kernel') for m in sys.modules))\n")
            r = subprocess.run([sys.executable, "-c", code], input=blob, capture_output=True, timeout=120)
            return (r.stdout.decode() + r.stderr.decode()).strip()
        # identity and registries
        add("is the captured builtin os.stat")(lambda f: f is captured)
        add("is the current os.stat")(lambda f: f is os.stat)
        add("is the current posix.stat")(lambda f: f is posix.stat)
        add("equals the captured builtin")(lambda f: f == captured)
        for s in ("supports_dir_fd", "supports_effective_ids", "supports_fd", "supports_follow_symlinks"):
            add("member of os.%s" % s)(lambda f, s=s: f in getattr(os, s))
        # mock and typing
        add("mock.create_autospec type")(lambda f: type(mock.create_autospec(f)).__name__)
        add("typing.get_type_hints")(lambda f: str(typing.get_type_hints(f)))
        # calling behaviour (the arms agree here; the denominator's honest half)
        add("call on a regular file (mode,size)")(lambda f: "%o %d" % (f(tmpfile).st_mode, f(tmpfile).st_size))
        add("return type")(lambda f: type(f(tmpfile)).__name__)
        add("call with a pathlib.Path")(lambda f: "%o" % f(pathlib.Path(tmpfile)).st_mode)
        add("call with a bytes path")(lambda f: "%o" % f(os.fsencode(tmpfile)).st_mode)

        @add("call with an open fd")
        def _open_fd(f):
            fd = os.open(tmpfile, os.O_RDONLY)
            try:
                return "%o" % f(fd).st_mode
            finally:
                os.close(fd)
        add("call with follow_symlinks=False on a symlink")(lambda f: "islink=%s" % ((f(tmplink, follow_symlinks=False).st_mode & 0o170000) == 0o120000))

        @add("call with dir_fd")
        def _dir_fd(f):
            fd = os.open(scratch, os.O_RDONLY)
            try:
                return "%o" % f(os.path.basename(tmpfile), dir_fd=fd).st_mode
            finally:
                os.close(fd)
        add("call on a missing path")(lambda f: f(os.path.join(scratch, "nope")))
        add("call on None")(lambda f: f(None))
        add("call via functools.partial")(lambda f: "%o" % functools.partial(f, tmpfile)().st_mode)
        add("call keyword-only path")(lambda f: "%o" % f(path=tmpfile).st_mode)
        # arity and error text
        add("call with no arguments")(lambda f: f())
        add("call with three positional arguments")(lambda f: f(tmpfile, None, True))
        add("call with an unknown keyword")(lambda f: f(tmpfile, bogus=1))
        add("call with path given twice")(lambda f: f(tmpfile, path=tmpfile))
        add("call with only keywords, no path")(lambda f: f(follow_symlinks=True))

        # stack, tracing, recursion
        @add("traceback frames through the call")
        def _tb_frames(f):
            try:
                f(os.path.join(scratch, "nope"))
            except FileNotFoundError:
                return "traceback frames=%d" % len(traceback.extract_tb(sys.exc_info()[2]))

        @add("sys.settrace events during one call")
        def _trace(f):
            ev = []

            def tr(frame, event, arg):
                ev.append(event)
                return tr
            prev = sys.gettrace()                          # saved and put back: the probe set None, which would drop a prior hook
            sys.settrace(tr)
            try:
                f(tmpfile)
            finally:
                sys.settrace(prev)
            return "settrace events=%s n=%d" % (sorted(set(ev)), len(ev))

        @add("sys.setprofile events during one call")
        def _profile(f):
            ev = []

            def pr(frame, event, arg):
                ev.append(event)
            prev = sys.getprofile()
            sys.setprofile(pr)
            try:
                f(tmpfile)
            finally:
                sys.setprofile(prev)
            return "setprofile events=%s" % sorted(set(ev))

        @add("deepest recursion at which the call still runs")
        def _recursion(f):
            depth, fr = 0, sys._getframe()
            while fr is not None:
                depth, fr = depth + 1, fr.f_back
            old = sys.getrecursionlimit()
            sys.setrecursionlimit(depth + 300)             # relative to the frames under this test, not the probe's absolute limit

            def go(n):
                if n <= 0:
                    return f(tmpfile)
                return go(n - 1)
            try:
                best, lo, hi = -1, 0, 600
                while lo <= hi:
                    mid = (lo + hi) // 2
                    try:
                        go(mid)
                        best, lo = mid, mid + 1
                    except RecursionError:
                        hi = mid - 1
                return "deepest call depth=%d" % best
            finally:
                sys.setrecursionlimit(old)

        # descriptor binding
        @add("as a class attribute, what the instance attribute is")
        def _class_attribute(f):
            b = type("C", (), {"m": f})().m
            return "instance attribute type=%s, is f: %s" % (type(b).__name__, b is f)
        add("as a class attribute, calling it with a path")(lambda f: type(type("C", (), {"m": f})().m(tmpfile)).__name__)
        add("as a staticmethod class attribute, calling it with a path")(lambda f: type(type("C", (), {"m": staticmethod(f)})().m(tmpfile)).__name__)
        add("gc.get_referents types")(lambda f: ",".join(sorted({type(x).__name__ for x in gc.get_referents(f)})))
        add("Signature.bind with follow_symlinks")(lambda f: str(inspect.signature(f, follow_wrapped=False).bind(tmpfile, follow_symlinks=False)))

        # the counting side effect itself
        @add("does a call move the kernel's accumulator")
        def _counts(f):
            acc = getattr(f, "_romp_sig_counting", None)
            if acc is None:
                return "no accumulator"
            was_active, was_stats = acc.active, acc.stats
            acc.active = True
            try:
                f(tmpfile)
                moved = acc.stats - was_stats
            finally:
                acc.active, acc.stats = was_active, was_stats
            return "accumulator moved by %d" % moved
        return obs

    @staticmethod
    def _render(fn, f, norm):
        """One arm: the procedure's result as normalized text, a raise as its type and normalized message."""
        try:
            v = fn(f)
            return norm(v if isinstance(v, str) else repr(v))
        except Exception as e:
            return norm("<%s: %s>" % (type(e).__name__, e))

    def test_every_difference_the_differential_finds_is_named_in_the_install_docstring(self):
        import functools, inspect
        W, tl = os.stat, km._CHAT_SIG_TL
        self.assertIs(getattr(W, "_romp_sig_counting", None), tl, "premise: the object at os.stat is the kernel's counting wrapper: %r" % (W,))
        B = getattr(W, "__wrapped__", None)
        self.assertTrue(inspect.isbuiltin(B), "premise: the wrapper holds the builtin in __wrapped__ (a _StatInterceptor's holds the "
                                              "kernel's function, so an interceptor left installed fails here): %r" % (B,))
        self.assertIs(posix.stat, W, "premise: posix.stat is the same wrapper object (no interceptor or displacement on the posix module)")
        self.assertFalse(tl.active, "premise: no signature is open on this thread")
        scratch = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, scratch, True)
        tmpfile, tmplink = os.path.join(scratch, "f"), os.path.join(scratch, "l")
        with open(tmpfile, "w") as fh:
            fh.write("x")
        os.symlink(tmpfile, tmplink)
        code_file = W.__code__.co_filename
        kernel_paths = sorted({code_file, os.path.realpath(code_file), getattr(km, "__file__", None) or code_file}, key=len, reverse=True)
        addr = re.compile(r"0x[0-9a-fA-F]{6,}")

        def norm(s):
            s = addr.sub("0xADDR", str(s))
            for p in kernel_paths:
                s = s.replace(p, "KERNEL")
            s = s.replace(os.path.realpath(scratch), "SCRATCH").replace(scratch, "SCRATCH")
            return re.sub(r"\s+", " ", s).strip()
        observations = self._observations(scratch, tmpfile, tmplink, B)
        names = [n for n, _ in observations]
        self.assertEqual(len(set(names)), len(names), "premise: observation names are unique")
        rows = {n: (self._render(fn, B, norm), self._render(fn, W, norm)) for n, fn in observations}
        differing = [n for n in names if rows[n][0] != rows[n][1]]
        unclassified = [n for n in differing if n not in self.CLASS_OF]
        self.assertEqual(unclassified, [], "an observation this test cannot classify: %r; add it to the map and, if the docstring does "
                                           "not name its class, name it there. Renderings (builtin, wrapper): %r"
                                           % (unclassified, {n: rows[n] for n in unclassified}))
        self.assertEqual(sorted(set(self.CLASS_OF) - set(names)), [], "a CLASS_OF key that is no observation name (a typo, or a renamed observation)")
        self.assertEqual(sorted(set(self.CLASS_OF.values()) - set(self.TOKEN_OF_CLASS) - {"attribute"}), [], "a class with no token")
        self.assertEqual("attribute __type_params__" in differing, sys.version_info >= (3, 12),
                         "__type_params__ is a function attribute from 3.12: the docstring's version clause rests on this")
        self.assertEqual("attribute __annotate__" in differing, sys.version_info >= (3, 14),
                         "__annotate__ is a function attribute from 3.14: the docstring's version clause rests on this")
        doc = " ".join(km._stat_counting_install.__doc__.split())
        same = sorted(n for n in functools.WRAPPER_ASSIGNMENTS
                      if self._render(lambda f, n=n: getattr(f, n, "absent"), B, norm) == self._render(lambda f, n=n: getattr(f, n, "absent"), W, norm))
        self.assertEqual(same, ["__doc__", "__module__", "__name__", "__qualname__"],
                         "the functools.WRAPPER_ASSIGNMENTS names that read the same on both arms, recomputed (of %r)" % (functools.WRAPPER_ASSIGNMENTS,))
        tokens = []
        for n in differing:
            cls = self.CLASS_OF[n]
            tok = n[len("attribute "):] if cls == "attribute" else self.TOKEN_OF_CLASS[cls]
            if tok not in tokens:
                tokens.append(tok)
        tokens += ["WrapperDifferential", "those %s read the same" % {4: "four"}[len(same)]]
        unnamed = [t for t in tokens if t not in doc]
        if "which agree" in doc:
            unnamed.append("the reading over two interpreters is still cited: 'which agree'")
        ported = [n for n in differing if n != self.ADDED]
        print("[live] differential: python=%s observations=%d differences=%d ported=%d/%d added=%d/1 unnamed=%r"
              % (sys.version.split()[0], len(rows), len(differing), len(ported), len(names) - 1, len(differing) - len(ported), unnamed))
        self.assertEqual(unnamed, [], "the install docstring does not name every class of difference the differential found on this "
                                      "interpreter, or cites the reading it replaced: %r (CLASS_OF says which observation each class covers; "
                                      "name the class in _stat_counting_install's docstring with the token verbatim)" % (unnamed,))


if __name__ == "__main__":
    unittest.main()
