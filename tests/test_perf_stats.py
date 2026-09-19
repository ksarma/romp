#!/usr/bin/env python3
"""The kernel's always-on performance counters (`_PerfStats`, GET /perf, `romp perf`) and the runtime
switch for the romp-perf stderr log (POST /perf {"log": bool}).

Before this the only instrumentation was `_perf()`, gated on ROMP_PERF at process start, so turning it
on meant a kernel restart; and nothing reported rates, so an optimization was checked with a hand-run
profiler. The collector counts pusher cycles and wakes, cycle durations (a ring for percentiles) and
the pusher thread's CPU, per-stage time, build cache hits, bytes sent per slot kind, goal-store I/O,
judge passes with their threads' CPU, and HTTP requests per method and path, with a lock and dict
increments on the hot paths and no formatting until a read.

Drives the REAL Handler over HTTP and the REAL _push with stubbed builders (the test_color_route.py
and test_tab_meta_push.py patterns). Synthetic fixtures only: placeholder UUIDs, invented names."""
import base64
import collections
import concurrent.futures
import copy
import fcntl
import inspect
import io
import json
import os
import re
import sys
import tempfile
import tracemalloc
import threading
import time
import unittest
import shutil
import socket
import subprocess
import urllib.request
from unittest import mock
import contextlib
from contextlib import redirect_stderr
from http.server import ThreadingHTTPServer
from romp_load import load_source
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")

# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
load_source("romp_event_model", os.path.join(BIN, "romp-event-model"))
load_source("romp_judge", os.path.join(BIN, "romp-judge"))
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "test-token-DO-NOT-USE")
km = load_source("romp_kernel_perf", os.path.join(BIN, "romp-kernel"))
pp = load_source("romp_perf_public", os.path.join(os.path.dirname(HERE), "cli", "perf_public.py"))   # the paste-safe walk

SID = "11111111-2222-3333-4444-555555555555"
# A PRIVATE synthetic sid for the goal-store tests: load_goals replays the per-sid override journal,
# and node ids collide across test modules under the shared placeholder (CLAUDE.md, goal-store fixtures).
GOAL_SID = "77777777-8888-9999-aaaa-bbbbbbbbbbbb"
TOP_KEYS = {"now", "since", "uptime_s", "log", "process", "pusher", "jobs", "stages_ms", "builds", "sends",   # jobs: the jobs thread's passes
            "stagesForeign",                               # stagesForeign: a `jobs.<job>` stage from a thread owning neither loop, or a push stage from a
            #                                                  thread that neither owns the pusher's cycle nor carries a connect push's mark (2026-09-18)
            "heap",                                        # heap: where the resident size sits at the read, gauges over every content cache (2026-09-15)
            "gc",                                          # gc: the collector's pauses per generation, from the gc.callbacks hook (2026-09-16)
            "goals", "memos", "judge", "http", "parses",   # parses: cold event-model parses (T323 stage 1)
            "checkpoints",                                 # checkpoints: the folds' checkpoints (T323 stage 3)
            "asmCheckpoint",                               # asmCheckpoint: the assembly documents (T323 stage 4a)
            "asmIndex",                                    # asmIndex: the lazy index's built atoms, by caller (T323 stage 4c)
            "recordCache",                                 # recordCache: the shared reader's byte budget and evictions (2026-09-11)
            "chatPages",                                   # chatPages: the pre-floor history pages cache (T323 stage 4b)
            "skillLoadIndex",                              # skillLoadIndex: the judge's skill-load boot pass, its raw reads (T333)
            "fileSlice",                                   # fileSlice: the file preview popover's slice cache: hit / miss / bytes / warm (T351)
            "glossary",                                    # glossary: files parsed, frames / terms / bytes built per cycle, entries cut, files refused (T351 stage 2)
            "stacks",                                      # stacks: every thread's last frames under ROMP_PERF_STACKS, else None (T358)
            "caches"}                                      # caches: the declared caches' exact occupancy (M1-lite, perf round 4; this fork's)
PROCESS_KEYS = {"rss_kb", "threads", "cpu_s", "pid", "rss_anon_kb", "hwm_kb", "source", "allocated_blocks", "gc_gen2", "malloc"}
# The caches the `caches` block gauges (perf round 4, M1-lite): exact occupancy, a len() or a sum of len()s,
# nothing estimated. A cache added to the kernel, the judge or the event model is added here deliberately.
CACHE_NAMES = {"jsonl", "asm", "asm_keylocks", "trailing", "judge_parse", "judge_recon", "judge_chain", "parse",
               "built_chat", "judge_usage", "img", "path_links", "space_paths", "session_stamp", "task_seg", "session_tok"}


def _doc_row(doc, name):
    """The _PerfStats docstring row whose entry line starts with `name`: from that line to the next line at or above its
    indentation that begins an entry (a non-space after the indentation), or the docstring's end. The locator is RELATIVE
    to the entry line's own indentation on purpose: Python 3.13 and later strip a docstring's common leading whitespace at
    compile time, so a pin that counts leading spaces (the source's six before a row's name) passes on a 3.12 venv and
    finds nothing on the 3.13 and 3.14t CI cells. Do not simplify it back to a space count."""
    m = re.search(r"^( *)%s\s" % re.escape(name), doc, re.M)
    if m is None:
        raise ValueError("no docstring row starts with %r" % name)
    nxt = re.compile(r"^ {0,%d}\S" % len(m.group(1)), re.M).search(doc, m.end())
    return doc[m.start():nxt.start() if nxt else len(doc)]


_ONES = ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
         "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen")
_TENS = ("", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety")


def _number_word(n):
    """The English word for a count under one hundred, spelled as the docs spell one ("nineteen"): the docs' count of the
    pass jobs' rows is derived from len(_PerfStats.PASS_JOBS) through this, never typed a second time (2026-09-19 review),
    so a job added to the list turns the sentence that counts them red."""
    if not 0 <= n < 100:
        raise ValueError("no word for %r" % (n,))
    if n < 20:
        return _ONES[n]
    tens, ones = divmod(n, 10)
    return _TENS[tens] + ("-" + _ONES[ones] if ones else "")


# Wordings about the stage routing that a review round retired, assembled from parts so this file does not carry them as
# sentences (the sweep pin below reads this file too): a push stage is foreign unless its writer is the pusher within the
# open cycle (ownership outlives the cycle: kernel-1, round two); a bare _push in a test always has a cycle open before it
# (false of 21 modules: extra6-1, round two); a push stage from a thread that is not the pusher and not a connect push (a
# thread identity, not ownership: round one's wording); the pass jobs' rows keep their values because the housekeeping was
# the jobs thread's alone from the start (false of the part rows: round one); a bare _push is foreign because no cycle
# is open when it runs (openness, where the rule is the thread's registration as an owner, which cycle() leaves standing,
# so the pusher's own thread between two cycles writes the flat rows: PR 797's closing check).
RETIRED_WORDINGS = {"push-inside-cycle": "inside its " + "cycle",
                    "bare-push-opens-cycle": "_push in a test " + "opens a cycle first",
                    "pusher-identity": "neither the pusher " + "nor a connect push",
                    "housekeeping-already-alone": "already ran on the " + "jobs thread alone",
                    "bare-push-no-open-cycle": "_push with no " + "cycle open"}


def _burn_cpu(seconds):
    """Spin this thread for `seconds` of its own CPU time (thread_time, so a descheduled thread still burns
    the asked amount rather than merely waiting it out)."""
    t = time.thread_time()
    while time.thread_time() - t < seconds:
        pass


def _ws_dial(port, path, ua=None, timeout=3.0):
    """One raw WebSocket upgrade against the loopback server, the socket kept open: (status, socket). `ua` is a
    User-Agent line to carry, none by default (the shape of a relay's splice or a pipe). The key is minted at run
    time, as tests/test_ws_open_row.py mints its own."""
    key = base64.b64encode(os.urandom(16)).decode()
    lines = ["GET %s HTTP/1.1" % path, "Host: 127.0.0.1:%d" % port, "Upgrade: websocket", "Connection: Upgrade",
             "Sec-WebSocket-Key: %s" % key, "Sec-WebSocket-Version: 13"]
    if ua is not None:
        lines.append("User-Agent: %s" % ua)
    s = socket.create_connection(("127.0.0.1", port), timeout=timeout)
    s.sendall(("\r\n".join(lines) + "\r\n\r\n").encode())
    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = s.recv(4096)
        if not chunk:
            break
        buf += chunk
    first = buf.split(b"\r\n", 1)[0].decode("latin-1")
    parts = first.split(" ", 2)
    return (int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else -1), s


def _registered_clients(wids, want, deadline_s=5.0):
    """{wid: client} for the registered ws clients carrying these dashboard ids, read under the kernel's lock once
    their count reaches `want` or the deadline passes (the handshake registers after its 101 leaves, and the handler's
    finally retires at the socket's close, both on the handler thread)."""
    end = time.monotonic() + deadline_s
    while True:
        with km._clients_lock:
            got = {c.get("wid"): c for c in km._clients if c.get("wid") in wids}
        if len(got) == want or time.monotonic() >= end:
            return got
        time.sleep(0.02)


_STACK_FRAME = re.compile(r"\S+ \((.+):\d+\)")          # _thread_stacks' "function (file:line)" form
_STACK_FRAME_DIRS = (os.path.dirname(threading.__file__),   # where a sampled frame's file may live: the standard library, and
                     os.path.dirname(HERE), os.path.join(os.path.dirname(HERE), "kernel"), BIN,    # this repo (a kernel frame's
                     os.path.join(os.path.dirname(HERE), "cli"), HERE)                             # file is bin/romp-kernel, the
#                                                                                                    path load_source read it by)


def _assert_stack_sample(tc, row):
    """`row` is a stack sample of a live thread: at least one frame, each in _thread_stacks' "function (file:line)" form and
    naming a file the standard library or this repo ships. No frame is pinned by position or by function (2026-09-19): a
    thread parked on an Event is sampled at wait, at the lock acquire inside it (Condition.__enter__ on the way into
    Event.wait), at a helper wait calls (_release_save, _is_owned), or in run before wait, and the innermost-frame pins
    that stood in four tests here read `wait (` and went red on the free-threaded 3.14 build when the sampler caught
    __enter__ (3 module runs of 10)."""
    tc.assertTrue(row["frames"], row)
    for f in row["frames"]:
        m = _STACK_FRAME.fullmatch(f)
        tc.assertTrue(m, "function (file:line): %r" % f)
        tc.assertTrue(any(os.path.exists(os.path.join(d, m.group(1))) for d in _STACK_FRAME_DIRS),
                      "a file the standard library or this repo ships: %r" % f)


class _HttpWatch:
    """Wait for the HTTP wrapper's record instead of racing it. _perf_http_timed counts a request in its
    `finally`, AFTER the handler put the response on the wire, so a test that reads the snapshot as soon
    as urlopen returns can see the count land a moment later (it did, about one run in five). Patching
    the collector's http_request on the instance (the class method stays) makes every record observable:
    the real method runs, then the key is appended and an Event set, and wait_for blocks on the event
    until the key has been recorded `n` times or the bound passes."""

    def __enter__(self):
        st = km._PERF_STATS
        real = km._PerfStats.http_request
        self.keys, self.ev = [], threading.Event()

        def wrapped(key, dt):
            real(st, key, dt)
            self.keys.append(key)           # append BEFORE set: an observed set implies a visible append
            self.ev.set()
        st.http_request = wrapped
        return self

    def __exit__(self, *a):
        del km._PERF_STATS.http_request     # the instance attribute goes; the class method shows again

    def wait_for(self, key, n, timeout=2.0):
        deadline = time.monotonic() + timeout
        while self.keys.count(key) < n:
            left = deadline - time.monotonic()
            if left <= 0:
                return False
            self.ev.wait(left)
            self.ev.clear()
        return True


class Collector(unittest.TestCase):
    """_PerfStats on its own: every writer lands where the docstring says, and the read-time work
    (percentiles, the goals and judge reads, the process reads) produces the documented shape."""

    def setUp(self):
        self.st = km._PerfStats()

    def test_snapshot_has_the_documented_shape_and_starts_at_zero(self):
        snap = self.st.snapshot()
        self.assertEqual(set(snap), TOP_KEYS)
        p = snap["pusher"]
        self.assertEqual(p["cycles"], 0)
        for k in ("cycle_ms_p50", "cycle_ms_p90", "cycle_ms_ring_max", "cycle_ms_max", "cycle_cpu_ms_sum"):
            self.assertEqual(p[k], 0.0, k)
        self.assertEqual(p["ring_n"], 0)
        self.assertEqual(set(snap["stages_ms"]), set(km._PerfStats.STAGES))
        # the pusher's nine cycle jobs left stages_ms on 2026-09-18 (stage attribution): a `jobs.<job>` row there is the jobs
        # thread's own, the cycle jobs' rows are pusher.cycleJobsMs, seeded with the nine names, and a fresh snapshot has
        # no foreign write (a `jobs.` stage from a thread owning neither loop)
        self.assertFalse({"jobs." + j for j in km._PerfStats.CYCLE_JOBS} & set(snap["stages_ms"]), "no cycle job's row in stages_ms")
        self.assertTrue({"jobs." + j for j in km._PerfStats.PASS_JOBS} <= set(snap["stages_ms"]), "every pass job's row, at zero")
        self.assertEqual(p["cycleJobsMs"], {j: 0.0 for j in km._PerfStats.CYCLE_JOBS})
        self.assertEqual(snap["stagesForeign"], {})
        # the connect pushes' push.* stages (2026-09-18): no seed, so a fresh table is empty (a seeded push.warm or `push` row
        # would be one a connect push can never move); the block's counters start at zero beside it
        self.assertEqual(p["connectPush"]["stagesMs"], {})
        self.assertEqual((p["connectPush"]["count"], p["connectPush"]["ms_sum"]), (0, 0.0))
        self.assertEqual(set(snap["builds"]), {"chat", "feed", "timeline", "feedJson", "thread"})   # thread: the comment popover's build (2026-09-08)
        self.assertEqual(set(snap["builds"]["timeline"]), {"cached", "built", "ms"})
        self.assertEqual(set(snap["builds"]["chat"]), {"cached", "built", "ms", "active_built", "bg_built", "bg_miss", "moved",
                                                       "coldSkipped", "bySession"},
                         "the chat builder carries the active/background split, the miss attribution (round-4 P3), "
                         "the builds left uncached because their signature moved (P4), the skeleton-held tabs the cold-tab "
                         "gate skipped (coldSkipped, upstream #1659) and the per-session timer (bySession)")
        self.assertEqual(set(snap["builds"]["chat"]["bg_miss"]), set(km._PerfStats.CHAT_MISS))
        self.assertEqual(km._PerfStats.CHAT_MISS, km._CHAT_SIG_LABELS + ("cold", "nosig"),
                         "one counter per labelled signature component, plus the two no-signature cases")
        self.assertNotIn("judge_gen", km._PerfStats.CHAT_MISS)
        self.assertEqual(snap["builds"]["chat"]["moved"], 0)
        self.assertEqual(sum(snap["builds"]["chat"]["bg_miss"].values()), 0)
        self.assertEqual(set(snap["sends"]), {"full", "delta", "deduped"})
        self.assertEqual(snap["judge"]["ms_mean"], 0.0, "no passes: the mean is 0, not a division error")
        self.assertIn("cpu_ms_sum", snap["judge"])
        self.assertNotIn("cpu_ms_workers", snap["judge"],
                         "nothing armed this collector as judge.py's worker-CPU sink: the workers' share is ABSENT, never a 0.0 "
                         "that reads as measured; arm_judge_worker_sink opens the key (the review ruling, 2026-09-18)")
        self.assertEqual({k: snap["judge"][k] for k in ("wakes", "wakes_event", "wakes_backstop")},
                         {"wakes": 0, "wakes_event": 0, "wakes_backstop": 0},
                         "the producer's wake counters: present and zero on a fresh collector")
        tiers = snap["judge"]["tiers"]
        self.assertEqual(set(tiers), set(km.jd.GATED_TIERS) | {"stamps"},
                         "read through jd.tier_stats: the evidence gate's per-tier counters plus the stamps held")
        for t in km.jd.GATED_TIERS:
            self.assertEqual(set(tiers[t]), {"ran", "skipped", "stamped", "bypassed", "incomplete", "due_clock"}, t)
        self.assertIn("index", km.jd.GATED_TIERS,
                      "the index tier (captioner and archiver) is counted beside the triage tiers; its incomplete "
                      "counts sessions with work this pass or a voided read, and ran == stamped + bypassed + incomplete "
                      "holds for it as for the others")
        self.assertIsInstance(tiers["stamps"], int)
        self.assertNotIn("chain_memo", snap["judge"], "the chain memo's counters ride memos.chain now (review find, 2026-09-08)")
        self.assertEqual(set(snap["goals"]), {"loads", "loads_shared", "saves", "writes", "scans", "scan_hits", "scan_parses",
                                              "disk_hits", "disk_misses", "disk_seeds",
                                              "absent_hits", "absent_misses", "noop_hash_ms", "unreadable_stores",
                                              "lineage_reads"},
                         "read through jd.goal_io_stats (unreadable_stores is a gauge beside the counters)")
        # the three identity memos' readers land here (review find, 2026-09-08: they had no consumer)
        self.assertEqual(set(snap["memos"]), {"pass", "shared", "chain", "nudgeGate", "nudgeWalk", "convergeDeclined", "sessionsListing", "cleared", "courierSkip", "backref", "captions", "goalArchive", "plannerSkip", "ghostDropped",
                                              "bgTops", "liftGate", "intrMarks", "deadWait", "tickSeen", "statesOverlay", "lanes", "spendTree", "summaryAnchor",
                                              "judgingBand",   # the judging band's per-row memo and horizon cursor (2026-09-16)
                                              "subagentTree",   # the subagents directory walk memo (2026-09-16): served vs walked, roots held
                                              "chatMergeSets", "chatPostal", "chatLedger", "chatFoldTasks",   # the chat build's fixed-cost memos (2026-09-09)
                                              "outlineProvisional",   # the Outline's provisional-row ledger memo, parse-free (plans/outline-pane-provisional-row.md, 2026-09-15)
                                              "feedComposition",   # the feed frame's bytes by component and per consuming app (2026-09-18, tests/test_feed_composition.py)
                                              "notices",   # the notice files' parsed rows (T370, plans/notice-cards.md): bytes against their bound
                                              "wire", "sessions_scope", "caps", "thread_reg"},
                         "one block per memo the kernel keeps: the shared names spelled as upstream reports them "
                         "(camelCase; `notices` is T370's notice-file memo), plus this kernel's own memos (the wire caches, the discover scope, the _Caps "
                         "object memo, the SDK registry reader); `caps` is the _Caps object memo, renamed from "
                         "`captions` when the captions file-read memo took that key; the nudge walk reports as "
                         "upstream's nudgeWalk since the 2026-09-15 pull-in, and the feed's per-session memo as "
                         "builds.feed.memo (T368)")
        self.assertEqual(set(snap["memos"]["notices"]), {"entries", "bytes", "bound", "hit", "miss", "evicted"}, "the notice memo: occupancy against its bound, and its counters")
        self.assertEqual(set(snap["memos"]["outlineProvisional"]), {"hit", "miss", "bypass_hold", "bypass_empty", "entries"},
                         "the provisional ledger memo: hits and misses on the store object's identity, the two bypasses (a rewind hold, an empty store), and the occupancy")
        self.assertEqual(set(snap["memos"]["spendTree"]), {"entries", "bytes", "bound", "served", "dirStats", "fileStats", "entryStats", "listings", "loaded", "loadFailed", "written", "swept", "dropped", "dumpSkipped", "evicted", "writeFailed"}, "the spend guard's tree memos against their bound")
        self.assertEqual(snap["memos"]["spendTree"]["bound"], km.SPEND_GUARD_TREE_MEMO_BYTES)
        self.assertEqual(set(snap["memos"]["summaryAnchor"]), {"entries", "bytes", "bound", "hit", "miss", "evict", "fault"},
                         "the brief line's text-atom landings (T388): occupancy and counters against their bound")
        self.assertEqual(snap["memos"]["summaryAnchor"]["bound"], km.SUMMARY_ANCHOR_MEMO_BYTES)
        self.assertEqual(set(snap["memos"]["bgTops"]), {"hit", "miss", "resolve", "walk", "walk_neg", "idx_build", "entries"},
                         "the placed-launch memo (_bg_placed_tops): counters plus its occupancy")
        for k, v in snap["memos"]["bgTops"].items():
            self.assertIsInstance(v, int, k)
        self.assertEqual(set(snap["memos"]["liftGate"]), {"skip", "load", "shared", "writer", "noop", "entries"},
                         "the awaiting-lift gate: session-cycles skipped vs read, the probes the shared cache "
                         "answered, the writer loads and the ones that filed nothing, plus its occupancy")
        for k, v in snap["memos"]["liftGate"].items():
            self.assertIsInstance(v, int, k)
        # the two memos the interrupt tick trims to its alive set: the interrupt-marks memo and the awaiting
        # overlay's states-log fold, each with its counters and its occupancy
        self.assertEqual(set(snap["memos"]["intrMarks"]), {"hit", "miss", "evict", "entries", "restored", "refused", "computeMs", "persisted"},
                         "the identity memo's counters and the persisted memo's (T401 (3) target 3)")
        self.assertEqual(snap["memos"]["intrMarks"], km._intr_marks_memo_report())
        self.assertEqual(set(snap["memos"]["statesOverlay"]), {"hit", "append", "refold", "fail", "evict", "entries"})
        self.assertEqual(snap["memos"]["statesOverlay"], km._states_overlay_report())
        for blk in ("intrMarks", "statesOverlay"):
            for k, v in snap["memos"][blk].items():
                self.assertIsInstance(v, int, "%s.%s" % (blk, k))
        self.assertEqual(set(snap["memos"]["lanes"]), {"hit", "miss", "live_tail", "complain_skip", "unshared_skip", "evict", "entries",
                                                     "segs_hit", "segs_miss", "prefix_hit", "prefix_segs", "dead_serve", "dead_miss", "dead_failed_serve"},
                         "the timeline's per-lane segment memo: one outcome per live lane per bars build, the dead lanes beside")
        self.assertTrue(all(type(v) is int for v in snap["memos"]["lanes"].values()))
        self.assertEqual(set(snap["memos"]["chatMergeSets"]), {"hit", "miss", "entries", "floorAgeMaxS", "builtAboveFloor"})   # 5b's two
        self.assertEqual(set(snap["memos"]["chatPostal"]), {"gate", "hit", "commit_new"})
        self.assertEqual(set(snap["memos"]["chatLedger"]), {"hit", "miss", "bypass_live", "bypass_hold", "bypass_empty", "evict", "entries"})
        self.assertEqual(set(snap["memos"]["chatFoldTasks"]), {"hit", "miss", "entries"})
        self.assertEqual(set(snap["memos"]["plannerSkip"]), {"skipped", "planned", "recorded", "restored", "refused", "persisted", "mismatchByTerm"})   # T401 (5c)
        self.assertEqual(set(snap["memos"]["captions"]), {"served", "parsed", "unstatable"})
        self.assertEqual(set(snap["memos"]["goalArchive"]), {"served", "loaded"})
        self.assertEqual(set(snap["memos"]["backref"]), {"served", "built"},
                         "the sender-board walk behind the courier link repair: built once per input state (2026-09-09)")
        self.assertEqual(snap["memos"]["nudgeGate"], {"served": 0, "derived": 0, "failed": 0},
                         "the nudge walk's placement gate: served vs re-derived (2026-09-09)")
        self.assertEqual(set(snap["memos"]["cleared"]), {"served", "derived"},
                         "the clear set: parsed once per file state, served while it stands (2026-09-09)")
        self.assertEqual(snap["memos"]["courierSkip"], km.jd.courier_skip_stats(),
                         "the courier gate: sessions skipped, scanned, recorded (2026-09-09)")
        self.assertEqual(snap["memos"]["pass"], km._goals_memo_report())
        self.assertEqual(snap["memos"]["shared"], km.jd.shared_store_stats())
        self.assertEqual(snap["memos"]["chain"], km.jd.chain_memo_stats())
        self.assertEqual(set(snap["memos"]["chain"]), {"hit", "miss", "populate", "bypass"},
                         "read through jd.chain_memo_stats: the write-moment chain memo's counters")
        self.assertEqual(set(snap["builds"]["feed"]), {"cached", "built", "ms", "dirty", "memo"},
                         "the feed build also counts the rebuilds a kernel-side mutation forced past the view signature, "
                         "and carries T368's per-session card memo (test_the_feed_build_block_carries_the_per_session_card_memo)")
        self.assertEqual(snap["builds"]["feed"]["dirty"], 0)
        self.assertEqual(set(snap["memos"]["pass"]),
                         {"hit", "miss", "compare_miss", "fail", "evict", "punch", "skip", "live", "snap", "entries", "bytes", "unowned"},
                         "the judge pass's goal-store memo: counters plus its occupancy and the feed's serve branches, with upstream's "
                         "compare_miss (a stat that matched over other bytes, #1789), skip (the stores the sweep ruled unowned, stepped over) "
                         "and the unowned gauge (#1744)")
        for k, v in snap["memos"]["pass"].items():
            self.assertIsInstance(v, int, k)
        self.assertEqual(set(snap["memos"]["nudgeWalk"]), set(km._NUDGE_WALK_STATS),
                         "the auto-nudge walk's parse gate (upstream's nudgeWalk row, the successor of this fork's own walk "
                         "row since the 2026-09-15 pull-in): looks, skipped and paid parses, cold ones, deferred sessions, the "
                         "unbounded legs and their notes, clock-due and wake-only looks; the placement gate's own served / "
                         "derived / failed counters are memos.nudgeGate")
        self.assertEqual(set(snap["memos"]["shared"]),
                         {"hit", "miss", "compare_miss", "refuse", "dup", "absent", "corrupt", "unreadable_journal",
                          "evict", "fallback", "poisoned", "entries", "bytes", "off"},
                         "the shared read-only goal-store cache: counters plus its occupancy (jd.shared_store_stats)")
        for k, v in snap["memos"]["shared"].items():
            self.assertIsInstance(v, int, k)
        self.assertEqual(set(snap["memos"]["wire"]),
                         {"feed_cards_hit", "feed_cards_miss", "split_hit", "split_miss", "feed_body", "bars_body",
                          "feed_sig_fallback", "feed_first", "bars_sig_fallback", "default_str",
                          "entries_walked", "entries_encoded", "feed_slot_split"},   # the per-entry work itself (stage 1 of the
                         #                                                                incremental-push design, 2026-09-18): the
                         #                                                                entries the split walked and encoded, and
                         #                                                                the feed sends through the view-delta slot path
                         "the pusher's wire caches: the feed's per-card memo, the collection-split memo the bars and "
                         "the slot path share (_delta_split_memo), the whole frames actually made, the cards-first "
                         "connect frame (feed_first) and its one unkeyable path (feed_sig_fallback), the unkeyable bars "
                         "fallback, the values a wire encoder shipped as str()")
        for k, v in snap["memos"]["wire"].items():
            self.assertIsInstance(v, int, k)
        self.assertEqual(set(snap["memos"]["sessions_scope"]), {"hit", "miss", "wide_hit", "wide_miss"},
                         "the pusher cycle's discover memo: _sessions reads and the wide walk")
        for k, v in snap["memos"]["sessions_scope"].items():
            self.assertIsInstance(v, int, k)
        self.assertEqual(set(snap["memos"]["caps"]), {"hit", "miss", "fail", "evict", "entries"},
                         "the _Caps object memo (perf round 4, item C; memos.caps since the 2026-09-09 fold, when upstream's "
                         "captions file-read memo took `captions`): reads served against read, failed reads, entries "
                         "dropped, and its occupancy")
        self.assertEqual(set(snap["memos"]["thread_reg"]), {"hit", "miss", "fail", "evict", "entries"},
                         "the SDK registry reader's memo: the captions memo's shape")
        for blk in ("caps", "captions", "thread_reg"):
            for k, v in snap["memos"][blk].items():
                self.assertIsInstance(v, int, "%s.%s" % (blk, k))
        self.assertEqual(set(snap["process"]), PROCESS_KEYS | ({"rss_peak_kb"} if sys.platform == "darwin" else set()),
                         "rss_peak_kb is darwin's alone (2026-09-18); every other platform keeps its shape")
        self.assertGreater(snap["process"]["threads"], 0)
        self.assertGreaterEqual(snap["process"]["rss_kb"], 0)
        self.assertEqual(set(snap["caches"]), CACHE_NAMES, "one exact-occupancy block per declared cache (M1-lite)")
        self.assertGreaterEqual(snap["uptime_s"], 0)
        json.dumps(snap)                                     # the whole thing serializes as-is

    def test_every_memo_key_is_named_in_the_collectors_docstring(self):
        # the /perf reader's reference for a memo block is _PerfStats's own docstring (its `memos` rows): a memo
        # registered without a row there is a counter nobody can read about
        doc = km._PerfStats.__doc__
        for key in self.st.snapshot()["memos"]:
            self.assertTrue(re.search(r"\b%s\b" % re.escape(key), doc), "memos.%s has no docstring row" % key)

    def test_the_process_block_carries_the_memory_gauges(self):
        # M1-lite (perf round 4): the three-way RSS question (allocator retention, an object graph, one cache
        # growing) is answered from levels an hour apart, so the snapshot carries exact process gauges beside
        # rss_kb: the anonymous and peak resident sizes from /proc, the interpreter's live allocation count,
        # the gen-2 collection count, and glibc's malloc arena figures (the large-object half of the heap;
        # pymalloc's arenas are mmap'd and invisible to it). Where a source is absent the field is null and
        # `source` says so; a peak from ru_maxrss is never passed off as a current figure (on macOS it is
        # rss_peak_kb, and rss_kb is the current size from task_info or ps, since 2026-09-18).
        p = km._PERF_STATS.snapshot()["process"]
        self.assertIn(p["source"], ("proc", "task_info", "ps", "unavailable"), "the reader rss_kb came from")
        if p["source"] == "proc":
            self.assertGreater(p["rss_anon_kb"], 0)
            self.assertGreaterEqual(p["hwm_kb"], p["rss_kb"], "the high-water mark is at or above the current size")
        else:
            self.assertIsNone(p["rss_anon_kb"]); self.assertIsNone(p["hwm_kb"])
        self.assertGreater(p["allocated_blocks"], 0)
        self.assertGreaterEqual(p["gc_gen2"], 0)
        if p["malloc"] is not None:
            self.assertEqual(set(p["malloc"]), {"arena", "hblkhd", "uordblks", "fordblks"})
            for k, v in p["malloc"].items():
                self.assertIsInstance(v, int, k)
                self.assertGreaterEqual(v, 0, k)
            self.assertLessEqual(p["malloc"]["uordblks"] + p["malloc"]["fordblks"], p["malloc"]["arena"] + 1,
                                 "in-use plus free bytes account for the arena")
        if km._MALLINFO2 is not None:
            self.assertIsNotNone(p["malloc"], "glibc 2.33+ resolved mallinfo2 at import: the gauges must read")
        # the ctypes binding sets the struct as the return type: without it the call returns an int and a
        # field read segfaults the kernel on the first report (the refuted M1's crash)
        if km._MALLINFO2 is not None:
            self.assertIs(km._MALLINFO2.restype, km._MallInfo2)
        json.dumps(p)

    def test_the_caches_block_is_exact_occupancy(self):
        snap = km._PERF_STATS.snapshot()
        for name, blk in snap["caches"].items():
            for k, v in blk.items():
                self.assertIsInstance(v, int, "%s.%s" % (name, k))
        # a known insert shows up as exactly its count and bytes, and leaves again
        km._img_cache["x:1:2"] = "data:image/png;base64,QUJD"
        km._img_cache["y:1:2"] = None
        km._built_chat["11111111-2222-3333-4444-aaaaaaaaaaaa"] = ("sig", {}, "abcdef")
        km._built_chat["11111111-2222-3333-4444-bbbbbbbbbbbb"] = ("sig", {}, None)
        try:
            c = km._PERF_STATS.snapshot()["caches"]
            self.assertEqual(c["img"]["entries"], len(km._img_cache))
            self.assertEqual(c["img"]["bytes"], sum(len(v) for v in km._img_cache.values() if isinstance(v, str)))
            self.assertEqual(c["built_chat"]["entries"], len(km._built_chat))
            self.assertEqual(c["built_chat"]["ms_bytes"], sum(len(v[2]) for v in km._built_chat.values() if isinstance(v[2], str)))
        finally:
            for k in ("x:1:2", "y:1:2"):
                km._img_cache.pop(k, None)
            for k in ("11111111-2222-3333-4444-aaaaaaaaaaaa", "11111111-2222-3333-4444-bbbbbbbbbbbb"):
                km._built_chat.pop(k, None)
        # the event model's reader: a file read through it adds exactly its size and record count. Its LRU is
        # one dict for the whole process, so it holds whatever the modules run before this one in the same
        # worker left behind, and at its cap the insert evicts the oldest entry first and the count stays
        # flat (a two-worker sweep's half of the suite had filled it, and this read 0 != 1, 2026-09-10). The
        # delta is measured from an empty cache, which the reader's own eviction tests clear the same way.
        td = tempfile.mkdtemp()
        try:
            p = os.path.join(td, "rows.jsonl")
            with open(p, "w") as fh:
                for i in range(3):
                    fh.write(json.dumps({"t": i, "state": "idle"}) + "\n")
            with km.em._JSONL_CACHE_LOCK:
                km.em._JSONL_CACHE.clear()
            before = km._PERF_STATS.snapshot()["caches"]["jsonl"]
            self.assertEqual(len(km.em._read_jsonl_incremental(p)), 3)
            after = km._PERF_STATS.snapshot()["caches"]["jsonl"]
            self.assertEqual(after["entries"] - before["entries"], 1)
            self.assertEqual(after["file_bytes"] - before["file_bytes"], os.path.getsize(p))
            self.assertEqual(after["records"] - before["records"], 3)
        finally:
            with km.em._JSONL_CACHE_LOCK:
                km.em._JSONL_CACHE.pop(p, None)
            shutil.rmtree(td, ignore_errors=True)
        self.assertEqual(set(km.jd.cache_gauges()), {"judge_parse", "judge_recon", "judge_chain"})
        self.assertEqual(set(km.em.cache_gauges()), {"jsonl", "asm", "asm_keylocks", "trailing"})

    def test_the_goals_block_carries_the_unreadable_stores_gauge(self):
        # the store-fault episodes standing now (a gauge), read through jd.goal_io_stats: a goals file that
        # exists and cannot be READ (here a directory at its path) counts from the first fault the per-session
        # boundary (jd.load_goals_or_fault) files to its next good read through it, however many loads.
        # Unparseable bytes are not an episode: the loader moves them aside and the session starts fresh
        # (upstream #1019, adopted 2026-09-08), so the gauge stays at 0 for them.
        saved = km.jd.STATE
        td = tempfile.mkdtemp()
        km.jd._rebind_state(Path(td))
        try:
            km.jd.GOALDIR.mkdir(parents=True, exist_ok=True)
            km.jd.save_goals(GOAL_SID, km.jd.load_goals(GOAL_SID))          # a first mint: the file exists
            gp = km.jd.GOALDIR / (GOAL_SID + ".json")
            good = gp.read_text()
            self.assertEqual(km._PERF_STATS.snapshot()["goals"]["unreadable_stores"], 0)
            gp.write_text("{ not the store")
            with redirect_stderr(io.StringIO()):                          # the quarantine's one stderr line
                store, fault = km.jd.load_goals_or_fault(GOAL_SID)
            self.assertIsNone(fault, "bytes that do not parse are quarantined, not a read fault")
            self.assertIsNotNone(store)
            self.assertTrue([q for q in km.jd.GOALDIR.iterdir() if ".corrupt-" in q.name], "the bad bytes are kept aside")
            self.assertEqual(km._PERF_STATS.snapshot()["goals"]["unreadable_stores"], 0, "a quarantine is not an episode")
            if gp.exists():
                gp.unlink()
            gp.mkdir()                                                     # exists, and cannot be read as a file
            self.assertIsNotNone(km.jd.load_goals_or_fault(GOAL_SID)[1])
            self.assertIsNotNone(km.jd.load_goals_or_fault(GOAL_SID)[1])
            self.assertEqual(km._PERF_STATS.snapshot()["goals"]["unreadable_stores"], 1, "one episode, two loads")
            gp.rmdir()
            gp.write_text(good)
            self.assertIsNone(km.jd.load_goals_or_fault(GOAL_SID)[1])
            self.assertEqual(km._PERF_STATS.snapshot()["goals"]["unreadable_stores"], 0, "a good read ends it")
        finally:
            km.jd._rebind_state(saved)
            shutil.rmtree(td, ignore_errors=True)

    def test_the_asm_checkpoint_block_names_the_restore_parts(self):
        """1606 low 4: nothing pinned restoreMs on /perf. The block's restoreMs sub-keys: the four named parts and the total."""
        st = km.em.asm_checkpoint_stats()
        self.assertEqual(set(st["restoreMs"]), {"load", "verify", "index", "seed", "total"})
        self.assertTrue(all(isinstance(v, float) for v in st["restoreMs"].values()), st["restoreMs"])

    def test_the_asm_index_block_carries_the_documented_keys(self):
        """The lazy index's block (asmIndex): its keys pinned, the light-facts gauge among them (T401 (3) target 3, round three:
        the gauge was documented on /perf but never exposed)."""
        st = km.em.asm_index_stats()
        self.assertEqual(set(st), {"cap", "evictions", "materialized", "materializedBy", "materializedByStage", "resident", "restoredTurns",
                                   "rowDecodes", "userFacts", "released", "expired"})   # released, expired: the LRU's weak ownership
        #                                                                                   (measured 2026-09-15: superseded generations
        #                                                                                   sat resident at the cap)
        self.assertIsInstance(st["userFacts"], int); self.assertGreaterEqual(st["userFacts"], 0)

    def test_the_feed_build_block_carries_the_per_session_card_memo(self):
        """builds.feed gained `memo` (T368): the feed's per-session card memo beside the build counters, its hits and
        misses per session per build, the misses attributed to the key component that moved (plus `cold`), the
        evictions, and the resident set against its bound (a fraction of the machine's memory, or ROMP_FEED_MEMO_BYTES).
        The map is the memo's own report, copied per read; tests/test_feed_session_memo.py drives the values."""
        snap = self.st.snapshot()
        self.assertEqual(set(snap["builds"]["feed"]), {"cached", "built", "ms", "dirty", "memo"})   # dirty: this fork's forced-rebuild counter beside the memo
        memo = snap["builds"]["feed"]["memo"]
        self.assertEqual(set(memo), {"hit", "miss", "evict", "entries", "bytes", "bound", "derived", "miss_by",
                                     "failed", "failing"})   # failed: derivations that raised, cumulative; failing: sessions whose last one did (2026-09-17)
        # ...and the reference's builds.feed.memo paragraph names every counter the block serves, so a counter cannot
        # ship undocumented (2026-09-18: `failed` and `failing` arrived with the card-build containment and the paragraph
        # named the eight older ones only). The slice: from the paragraph's opening line to the next block's bullet.
        doc = Path(HERE).parent.joinpath("docs", "reference.md").read_text()
        para = doc[doc.index("`feed` also carries\n  `memo`"):]
        para = para[:para.index("\n- `sends`:")]
        for k in memo:
            self.assertIn("`%s`" % k, para, "builds.feed.memo `%s` is not named in the reference's memo paragraph" % k)
        self.assertEqual(set(memo["miss_by"]), set(km._FEED_MEMO_LABELS) | {"cold"})
        self.assertEqual(memo["bound"], km.FEED_MEMO_BYTES)
        self.assertEqual(memo, km._feed_memo_report())
        for k, v in memo.items():
            self.assertIsInstance(v, (int, dict), k)
        for k, v in memo["miss_by"].items():
            self.assertIsInstance(v, int, k)
        self.assertIsNot(memo, km._FEED_MEMO_STATS, "a copy per read, never the live counters")
        for kind in ("chat", "timeline", "feedJson", "thread"):
            self.assertEqual(set(snap["builds"][kind]) & {"memo"}, set(), "%s: only the feed carries the memo" % kind)

    def test_pusher_counters(self):
        self.st.wake(); self.st.wake(); self.st.wake()
        self.st.wake_kind(True); self.st.wake_kind(False); self.st.wake_kind(False)
        self.st.cycle(0.010, 0.004); self.st.cycle(0.030, 0.006); self.st.cycle(0.020)
        self.st.wake_live(); self.st.wake_live()
        self.st.hold(0.625); self.st.hold(0.375); self.st.exempt()
        p = self.st.snapshot()["pusher"]
        self.assertEqual(p["wakes"], 3)
        self.assertEqual((p["wakes_event"], p["wakes_backstop"]), (1, 2))
        self.assertEqual(p["wakes_live"], 2)
        self.assertEqual((p["held"], p["exempt"]), (2, 1))
        self.assertAlmostEqual(p["held_ms"], 1000.0)
        self.assertEqual(p["cycles"], 3)
        self.assertAlmostEqual(p["cycle_ms_sum"], 60.0)
        self.assertAlmostEqual(p["cycle_cpu_ms_sum"], 10.0, msg="the thread's own CPU rides beside the wall")
        self.assertAlmostEqual(p["cycle_ms_max"], 30.0)
        self.assertAlmostEqual(p["cycle_ms_last"], 20.0)
        self.assertEqual(p["ring_n"], 3)

    def test_ring_percentiles_and_max_come_from_the_last_256_cycles(self):
        self.st.cycle(5.0)                                   # one slow boot cycle: 5000 ms
        for i in range(300):                                 # 0..299 ms; the ring keeps 44..299
            self.st.cycle(i / 1000.0)
        p = self.st.snapshot()["pusher"]
        self.assertEqual(p["ring_n"], 256)
        self.assertEqual(p["cycles"], 301, "the count is lifetime; only the percentile window is bounded")
        self.assertAlmostEqual(p["cycle_ms_p50"], 44 + 128)  # sorted ring[int(0.5 * 256)]
        self.assertAlmostEqual(p["cycle_ms_p90"], 44 + 230)  # sorted ring[int(0.9 * 256)]
        self.assertAlmostEqual(p["cycle_ms_ring_max"], 299.0, msg="the window's max: the ring's largest")
        self.assertAlmostEqual(p["cycle_ms_max"], 5000.0, msg="the lifetime max keeps the boot cycle")

    def test_the_per_session_chat_build_timer_keeps_first_last_and_max_and_leaves_with_its_sessions_certified_death(self):
        """The process split's measure (2026-09-14): beside the aggregate, a row per session with the FIRST build after the
        boot (set once per process life), the last, the max, the counts and the leaf's bytes; sorted by max under
        builds.chat.bySession; a row leaves with its session's CERTIFIED death (_record_death drops it, whichever road
        recorded the death) and with nothing else; the aggregate is unchanged."""
        A, B, C = "aaaaaaaa-2222-4333-8444-0000000000a1", "bbbbbbbb-2222-4333-8444-0000000000b2", "cccccccc-2222-4333-8444-0000000000c3"
        self.st.build_chat(False, 0.100, active=True, sid=A, nbytes=1000)    # A: first 100 ms
        self.st.build_chat(False, 0.050, sid=A, nbytes=1200)                  # A: last 50, max stays 100
        self.st.build_chat(False, 0.020, sid=B, nbytes=50)                    # B: first 20
        self.st.build_chat(False, 0.300, sid=B, nbytes=60)                    # B: last 300, max 300
        self.st.build_chat(True, sid=C)                                       # C: cached only, never built
        self.st.build_chat(True, sid=A)
        self.st.build_chat(False, 0.010)                                      # no sid: the aggregate alone
        snap = self.st.snapshot()
        chat = snap["builds"]["chat"]
        self.assertEqual((chat["built"], chat["cached"]), (5, 2), "the aggregate counts every build as before")
        rows = chat["bySession"]                                              # served by RANK in max order, never by sid (2026-09-18)
        self.assertEqual([r["rank"] for r in rows], [1, 2, 3], "sorted by max, the largest first, ranked in that order")
        self.assertEqual(rows[0], {"rank": 1, "first": 20.0, "last": 300.0, "max": 300.0, "n": 2, "cached": 0, "bytes": 60})     # B
        self.assertEqual(rows[1], {"rank": 2, "first": 100.0, "last": 50.0, "max": 100.0, "n": 2, "cached": 1, "bytes": 1200})   # A
        self.assertEqual(rows[2], {"rank": 3, "first": None, "last": None, "max": 0.0, "n": 0, "cached": 1, "bytes": None})     # C
        self.assertEqual(self.st.chat_by_session[A], {"first": 100.0, "last": 50.0, "max": 100.0, "n": 2, "cached": 1, "bytes": 1200},
                         "the collector keeps the rows by sid; the snapshot does not")
        self.st.build_chat(False, 0.400, sid=A)
        rows = self.st.snapshot()["builds"]["chat"]["bySession"]
        self.assertEqual((rows[0]["first"], rows[0]["last"], rows[0]["max"]), (100.0, 400.0, 400.0),
                         "first is set once; last and max move, and A's row now ranks first")
        self.st.chat_row_drop(B)                                              # B's death was certified (_record_death calls this)
        self.assertEqual(sorted(self.st.chat_by_session), sorted([A, C]))
        self.assertEqual([r["rank"] for r in self.st.snapshot()["builds"]["chat"]["bySession"]], [1, 2], "ranks close up")
        self.st.chat_row_drop("no-such-sid")                                  # a death of a session never built: nothing to drop
        self.assertEqual(len(self.st.snapshot()["builds"]["chat"]["bySession"]), 2)
        # the certified death drives the drop through the real _record_death and the real death sweep's tick over three ticks
        # (tests/test_sdk_registry_blind.py, ChatBuildRowsLeaveWithTheCertifiedDeath); the call sites are executed, not read: PushStages below
        # drives the real _push and the real _push_session_now and reads the rows from the snapshot

    def test_per_session_rows_are_served_by_rank_and_parsed_sessions_as_a_count(self):
        """builds.chat.bySession named its session in every row and parses.bySid keyed the cold-parse table by the first
        eight characters of the sid (2026-09-18, a paste-safety review of the snapshot). The rows are served by rank in the
        block's own order (the largest max first) and the parse table as the number of sessions parsed with the largest
        per-session count; the collector keeps both by sid for its own bookkeeping (a row leaves with its session's death)."""
        A, B = "aaaaaaaa-2222-4333-8444-0000000000a1", "bbbbbbbb-2222-4333-8444-0000000000b2"
        self.st.build_chat(False, 0.100, sid=A, nbytes=10); self.st.build_chat(False, 0.300, sid=B, nbytes=20)
        self.st.parse(A, 100); self.st.parse(A, 100); self.st.parse(B, 50)
        snap = self.st.snapshot()
        text = json.dumps(snap["builds"]["chat"]) + json.dumps(snap["parses"])
        for probe in (A, B, A[:8], B[:8]):
            self.assertNotIn(probe, text, "a session id in the served block: %s" % text)
        self.assertEqual(snap["builds"]["chat"]["bySession"],
                         [{"rank": 1, "first": 300.0, "last": 300.0, "max": 300.0, "n": 1, "cached": 0, "bytes": 20},
                          {"rank": 2, "first": 100.0, "last": 100.0, "max": 100.0, "n": 1, "cached": 0, "bytes": 10}])
        self.assertEqual(snap["parses"]["perSession"], {"sessions": 2, "max": 2})
        self.assertNotIn("bySid", snap["parses"])
        self.assertEqual(sorted(self.st.chat_by_session), [A, B], "the collector's own rows stay by sid")
        self.assertEqual(self.st.parses["bySid"], {A[:8]: 2, B[:8]: 1})

    def test_stages_builds_judge(self):
        self.st.cycle_begin()                                  # this thread stands for the pusher: a push stage is credited to its
        #                                                        writer since 2026-09-18, and a thread owning no cycle, under no connect
        #                                                        mark, counts under stagesForeign instead (PushRowsByPurpose)
        self.st.stage("push.chat", 0.5); self.st.stage("push.chat", 0.25); self.st.stage("jobs", 0.1)
        self.st.build("chat", True); self.st.build("chat", False, 0.040); self.st.build("feed", False, 1.0)
        self.st.judge_pass(2.0); self.st.judge_pass(4.0); self.st.judge_cpu(0.25)
        snap = self.st.snapshot()
        self.assertAlmostEqual(snap["stages_ms"]["push.chat"], 750.0)
        self.assertAlmostEqual(snap["stages_ms"]["jobs"], 100.0)
        # chat also carries the watched/background split and the per-component attribution (2026-09-09); the
        # plain writer counts the build and attributes nothing
        self.assertEqual(snap["builds"]["chat"], {"cached": 1, "built": 1, "ms": 40.0, "active_built": 0, "bg_built": 0,
                                                  "moved": 0, "coldSkipped": 0, "bg_miss": {k: 0 for k in km._PerfStats.CHAT_MISS},
                                                  "bySession": []})                   # the per-session timer (2026-09-14): no sid handed in, no row
        self.assertEqual(snap["builds"]["feed"]["built"], 1)
        self.assertEqual(snap["builds"]["timeline"], {"cached": 0, "built": 0, "ms": 0.0})
        self.assertEqual(snap["judge"]["passes"], 2)
        self.assertAlmostEqual(snap["judge"]["ms_last"], 4000.0)
        self.assertAlmostEqual(snap["judge"]["ms_mean"], 3000.0)
        self.assertAlmostEqual(snap["judge"]["cpu_ms_sum"], 250.0,
                               msg="the tier threads' CPU alone: nothing armed this collector, so no pool workers' share is in the sum")
        self.assertNotIn("cpu_ms_workers", snap["judge"],
                         "and no workers' key stands beside it to be mistaken for a measured zero (the review ruling, 2026-09-18)")

    def test_judge_child_is_served_as_a_size_and_a_status_never_the_line(self):
        """judge.child stood as the judges' child's done line verbatim (2026-09-18, a paste-safety review of the snapshot):
        its failures.first is an exception message, which names paths and quotes session text. The served block is the
        line's length in characters, one of two fixed status tokens, the line's per-pass numbers and its four counter
        blocks as the child sent them (numbers are not a leak); the failures are a count; the line's text never reaches
        the snapshot."""
        home = "/home/tester/.claude/projects/-home-tester-code-notes-api/%s.jsonl" % SID
        first = "OSError: [Errno 2] No such file or directory: '%s'" % home
        blocks = {"recordCache": {"entries": 1, "wholeReads": {"leaf<-_parse": {"count": 1, "bytes": 5}}},
                  "asmCheckpoint": {"restored": 1, "hydratedBy": {"_unit_text<-build_session": 10}},
                  "parses": {"misses": 1, "hits": 0}, "goalIo": {"loads": 1}}
        done = {"op": "done", "seq": 7, "wallMs": 12.5, "tierStarts": 2, "tierCpuMs": 3.0, "workerCpuMs": 4.0,
                "failures": {"count": 2, "first": first}, "recovered": True, **blocks}
        self.st.judge_child_done(done, pid=4242)
        child = self.st.snapshot()["judge"]["child"]
        text = json.dumps(child)
        self.assertNotIn(SID, text, "the session id in the first failure's path: %s" % text)
        self.assertNotIn("/home/", text, "the path in the first failure: %s" % text)
        self.assertNotIn("first", text, "the failure text itself: %s" % text)
        t = child.pop("t")
        self.assertIsInstance(t, float)
        compact = len(json.dumps(done, separators=(",", ":")))
        self.assertEqual(child, {"seq": 7, "pid": 4242, "chars": compact, "status": "failed", "failures": 2, "recovered": True,
                                 "wallMs": 12.5, "tierStarts": 2, "tierCpuMs": 3.0, "workerCpuMs": 4.0, **blocks},
                         "no reader count given: the line re-encoded compactly is its size; the four blocks ride as sent")
        self.st.judge_child_done({"op": "done", "seq": 9, "recordCache": "not a block", "goalIo": {"loads": 2}}, pid=4242)
        child = self.st.snapshot()["judge"]["child"]
        self.assertEqual((child.get("recordCache"), child.get("goalIo"), "asmCheckpoint" in child), (None, {"loads": 2}, False),
                         "a block rides only as a dict, and only when sent")
        self.assertEqual(self.st.snapshot()["judge"]["cpu_ms_child_workers"], 4.0, "the CPU folds as before")
        self.assertNotIn("cpu_ms_workers", self.st.snapshot()["judge"],
                         "the child's report lands with no sink armed (the child road needs none) and opens no in-process "
                         "workers' key: only the arming, or an in-process future, creates it (the review ruling, 2026-09-18)")
        line = json.dumps(done) + "\n"
        self.st.judge_child_done(done, pid=4242, chars=len(line))
        self.assertEqual(self.st.snapshot()["judge"]["child"]["chars"], len(line), "the reader's own count when it has one")
        self.st.judge_child_done({"op": "done", "seq": 8, "wallMs": "12", "tierStarts": True, "failures": None}, pid=4242)
        child = self.st.snapshot()["judge"]["child"]
        self.assertEqual((child["status"], child["failures"], child["wallMs"], child["tierStarts"]), ("ok", 0, None, None),
                         "a non-number where a number belongs is served as null, never as itself")

    def test_sends_classify_by_kind_and_slot_name(self):
        self.st.send(("chat", SID), "full", 1000)            # a tuple dedup key: the slot is its first element
        self.st.send(("chat", SID), "full", 500)
        self.st.send(("chat", SID), "deduped", 1000)
        self.st.send("feed", "delta", 20)                    # a bare string key (the feed's own delta path)
        s = self.st.snapshot()["sends"]
        self.assertEqual(s["full"], {"chat": {"count": 2, "bytes": 1500}})
        self.assertEqual(s["deduped"], {"chat": {"count": 1, "bytes": 1000}})
        self.assertEqual(s["delta"], {"feed": {"count": 1, "bytes": 20}})

    def test_send_slots_are_capped(self):
        for i in range(40):
            self.st.send(("slot%d" % i,), "full", 1)
        d = self.st.snapshot()["sends"]["full"]
        self.assertEqual(len(d), km._PerfStats.SLOTS + 1)
        self.assertEqual(d["other"]["count"], 40 - km._PerfStats.SLOTS)

    def test_the_clients_block_starts_with_no_app_and_one_zero_row_per_kind(self):
        """pusher.clients (2026-09-18): what each client's sender thread wrote to its socket, by the app the client
        declared and by the browser kind its User-Agent header classed to. The kind rows are seeded from WS_UA_KINDS,
        so the served key set is fixed before any client dials and a header can never become a key."""
        self.assertEqual(km.WS_UA_KINDS, ("safari-ios", "safari-mac", "chrome", "firefox", "other", "none"))
        c = self.st.snapshot()["pusher"]["clients"]
        self.assertEqual(set(c), {"byApp", "byKind"})
        self.assertEqual(c["byApp"], {})
        self.assertEqual(set(c["byKind"]), set(km.WS_UA_KINDS))
        for kind, row in c["byKind"].items():
            self.assertEqual(row, {"frames": 0, "bytes": 0, "sendMs": 0.0, "sendMax": 0.0, "sends": 0}, kind)

    def test_client_sends_count_frames_and_bytes_by_app_and_the_write_time_by_kind(self):
        self.st.client_send("chat", "safari-ios", 1000, 0.002)
        self.st.client_send("chat", "safari-ios", 500, 0.006)
        self.st.client_send("feed", "chrome", 40, 0.001)
        snap = self.st.snapshot()["pusher"]
        c = snap["clients"]
        self.assertEqual(c["byApp"], {"chat": {"frames": 2, "bytes": 1500}, "feed": {"frames": 1, "bytes": 40}})
        ios, chrome = c["byKind"]["safari-ios"], c["byKind"]["chrome"]
        self.assertEqual((ios["frames"], ios["bytes"], ios["sends"]), (2, 1500, 2))
        self.assertAlmostEqual(ios["sendMs"], 8.0)
        self.assertAlmostEqual(ios["sendMax"], 6.0)
        self.assertAlmostEqual(ios["sendMs"] / ios["sends"], 4.0, msg="the mean is derivable from the sum and the count")
        self.assertEqual((chrome["frames"], chrome["bytes"], chrome["sends"]), (1, 40, 1))
        self.assertAlmostEqual(chrome["sendMs"], 1.0)
        for kind in ("safari-mac", "firefox", "other", "none"):
            self.assertEqual(c["byKind"][kind], {"frames": 0, "bytes": 0, "sendMs": 0.0, "sendMax": 0.0, "sends": 0}, kind)
        self.assertEqual(snap["sends"], 0, "a client's write is not a pusher payload: pusher.sends is the pusher's own count")
        self.assertEqual(self.st.snapshot()["sends"], {"full": {}, "delta": {}, "deduped": {}}, "nor a slot send")

    def test_client_app_keys_are_identifiers_capped_and_the_kind_is_one_of_the_list(self):
        """The app is the client's own text off its socket URL and the kind whatever the caller hands over, and a served
        key is a leak vector: an app outside _PERF_IDENT's grammar (a path, a space, 33 characters, a trailing newline,
        which the pattern's $ alone lets through) counts under other, no app under none while the table has room and
        under other past the cap, the table stops at APPS distinct names, and a kind outside WS_UA_KINDS counts under
        other."""
        self.st.client_send("/some/dir/x", "chrome", 1, 0.0)
        self.st.client_send("has space", "chrome", 1, 0.0)
        self.st.client_send("a" * 33, "chrome", 1, 0.0)
        self.st.client_send("chat\n", "chrome", 1, 0.0)   # $ matches before a trailing newline: the check is a fullmatch
        self.st.client_send(None, "chrome", 1, 0.0)
        self.st.client_send("", "chrome", 1, 0.0)
        self.st.client_send("chat", "Mozilla/5.0 (X11) Gecko", 1, 0.0)
        c = self.st.snapshot()["pusher"]["clients"]
        self.assertEqual(c["byApp"], {"other": {"frames": 4, "bytes": 4}, "none": {"frames": 2, "bytes": 2}, "chat": {"frames": 1, "bytes": 1}})
        self.assertNotIn("chat\n", c["byApp"], "a name ending in a newline is not a key")
        self.assertEqual(c["byKind"]["other"]["frames"], 1, "a kind outside the list counts under other, never as itself")
        self.assertEqual(c["byKind"]["chrome"]["frames"], 6)
        self.assertEqual(km._PerfStats.APPS, 16)
        self.assertEqual(km._PERF_IDENT.pattern, r"^[A-Za-z0-9_.-]{1,32}$")
        st = km._PerfStats()
        for i in range(40):
            st.client_send("app%d" % i, "chrome", 1, 0.0)
        by_app = st.snapshot()["pusher"]["clients"]["byApp"]
        self.assertEqual(len(by_app), km._PerfStats.APPS + 1)
        self.assertEqual(by_app["other"]["frames"], 40 - km._PerfStats.APPS)
        self.assertTrue(all(km._PERF_IDENT.fullmatch(a) for a in by_app), sorted(by_app))
        st.client_send(None, "chrome", 1, 0.0)                  # an app-less client past the cap: other, no none row seated
        by_app = st.snapshot()["pusher"]["clients"]["byApp"]
        self.assertNotIn("none", by_app)
        self.assertEqual(by_app["other"]["frames"], 41 - km._PerfStats.APPS, "none is a name like any other to the cap")

    def test_connect_push_keys_only_identifier_app_names_and_caps_them(self):
        """connectPush.byApp keyed a connect push by the app name the client DECLARED on its socket URL, verbatim and
        unbounded (2026-09-18, a paste-safety review of the snapshot): a client could put any text, a session id or a home
        path included, into a served key. A name is a key only when it fits the identifier grammar (_PERF_IDENT) and while
        the table holds fewer than APPS distinct names; everything else counts under `other`, a missing name under `none`
        while the table has room for that word and under `other` past the cap (the rule pusher.clients.byApp follows); the
        aggregate counts every push as before."""
        self.st.connect_push("chat", 0.010)
        self.st.connect_push("<b>%s</b> /home/tester" % SID, 0.020)
        self.st.connect_push("chat\n", 0.050)   # $ matches before a trailing newline: the check is a fullmatch (match let this through as a key)
        self.st.connect_push("", 0.030); self.st.connect_push(None, 0.040)
        by = self.st.snapshot()["pusher"]["connectPush"]["byApp"]
        self.assertNotIn(SID, json.dumps(by)); self.assertNotIn("/home/", json.dumps(by))
        self.assertNotIn("chat\n", by, "a name ending in a newline is not a key")
        self.assertEqual(sorted(by), ["chat", "none", "other"])
        self.assertEqual((by["other"]["count"], by["none"]["count"], by["chat"]["count"]), (2, 2, 1))
        self.assertAlmostEqual(by["other"]["ms_sum"], 70.0); self.assertAlmostEqual(by["none"]["ms_max"], 40.0)
        self.assertEqual(self.st.snapshot()["pusher"]["connectPush"]["count"], 5, "the aggregate counts every push")
        for i in range(km._PerfStats.APPS + 5):
            self.st.connect_push("app%d" % i, 0.001)
        by = self.st.snapshot()["pusher"]["connectPush"]["byApp"]
        self.assertEqual(len(by), km._PerfStats.APPS, "at most APPS names; other, already held, is one of them (the http table's rule)")
        self.assertEqual(by["other"]["count"], 2 + (km._PerfStats.APPS + 5) - (km._PerfStats.APPS - 3),
                         "the names past the cap join other (chat, none and other held three of the slots)")
        self.st.connect_push("chat", 0.001)
        self.assertEqual(self.st.snapshot()["pusher"]["connectPush"]["byApp"]["chat"]["count"], 2, "a held name still counts under itself")
        st = km._PerfStats()
        for i in range(km._PerfStats.APPS):
            st.connect_push("app%d" % i, 0.001)
        st.connect_push(None, 0.001)                            # an app-less client past the cap: other, no none row seated
        by = st.snapshot()["pusher"]["connectPush"]["byApp"]
        self.assertNotIn("none", by)
        self.assertEqual((len(by), by["other"]["count"]), (km._PerfStats.APPS + 1, 1), "none is a name like any other to the cap; other seats past it")

    def test_http_keys_are_capped_and_ws_adds_no_time(self):
        cap = km._PerfStats.HTTP_PATHS
        for i in range(cap + 36):
            self.st.http_request("GET /scan/%d" % i, 0.001)
        self.st.http_request("GET /ws", None)
        h = self.st.snapshot()["http"]
        self.assertEqual(len(h), cap + 1, "the cap's keys plus other")
        self.assertEqual(h["other"]["count"], 36 + 1,
                         "the 36 keys past the cap and /ws, which arrived after it")
        st2 = km._PerfStats()
        st2.http_request("GET /ws", None); st2.http_request("POST /tick", 0.002)
        h = st2.snapshot()["http"]
        self.assertEqual(h["GET /ws"], {"count": 1, "ms": 0.0}, "a socket's lifetime is not a request time")
        self.assertEqual(h["POST /tick"]["count"], 1)
        self.assertAlmostEqual(h["POST /tick"]["ms"], 2.0)

    def test_the_http_cap_clears_the_kernels_own_route_table(self):
        """HTTP_PATHS bounds the distinct keys for the kernel's LIFETIME (a scanner must not grow the dict), so it
        has to sit comfortably above the kernel's own fixed routes, or a real route that first arrives after
        the cap lands in "other" for good. The first cap, 64, was below the route table itself (88 literals
        on 2026-09-07). The count comes from the do_* dispatch source (`p == "/x"`, `u.path == "/x"` and the
        `in ("/x", "/y")` tuples; inspect.getsource unwraps the timing decorator), so this trips when routes
        outgrow the headroom: 1.5x the literal count, room for the collapsed /dist/*, /media/* and /remote/*/…
        families and an OPTIONS preflight per cross-origin POST route. The same source gives the register
        its two halves and this test holds both: the literal routes, equal to _PERF_HTTP_ROUTES method by
        method, and the `startswith` prefixes (`p.startswith("/x/")`, `u.path.startswith(...)`, a tuple of
        them), equal to _PERF_HTTP_FAMILIES and each folding in _perf_http_key, so a prefix-dispatched family
        added later without a family line and a fold branch fails here instead of counting under `other`
        (2026-09-18, the review's finding: the test held the literals alone while the register's comment
        claimed any unregistered route failed it)."""
        lit = re.compile(r'(?:\bp|u\.path) (?:==|in) (?:"(/[^"]*)"|\(((?:"/[^"]*"(?:, )?)+)\))')
        n = 0
        derived = {}
        for meth in ("do_GET", "do_HEAD", "do_OPTIONS", "do_POST"):
            src = inspect.getsource(getattr(km.Handler, meth))
            paths = set()
            for m in lit.finditer(src):
                paths.update([m.group(1)] if m.group(1) is not None else re.findall(r'"(/[^"]*)"', m.group(2)))
            n += len(paths)
            derived[meth[3:]] = paths
        self.assertGreaterEqual(n, 80, "the derivation lost the route table (did the dispatch shape change?)")
        self.assertGreaterEqual(km._PerfStats.HTTP_PATHS, int(n * 1.5),
                                "%d fixed routes: raise HTTP_PATHS, or routes land in other for the kernel's lifetime" % n)
        # the checked-in register equals the dispatches, method by method (2026-09-18): a route added to a do_* without a
        # line in _PERF_HTTP_ROUTES would count under `other` for the kernel's lifetime, and a line without a route would
        # admit a key the kernel never serves; either way this says which path
        self.assertEqual(derived["OPTIONS"], set(), "do_OPTIONS answers any route's preflight and dispatches on no path")
        for meth in ("GET", "HEAD", "POST"):
            self.assertEqual(set(km._PERF_HTTP_ROUTES[meth]), derived[meth],
                             "%s: the register and the dispatches differ by %s" % (meth, sorted(set(km._PERF_HTTP_ROUTES[meth]) ^ derived[meth])))
            self.assertEqual(list(km._PERF_HTTP_ROUTES[meth]), sorted(set(km._PERF_HTTP_ROUTES[meth])), "%s: sorted, no repeats" % meth)
        self.assertEqual(set(km._PERF_HTTP_ROUTES["OPTIONS"]), derived["GET"] | derived["HEAD"] | derived["POST"], "a preflight for any route")
        # the prefix families: a prefix-dispatched route (the shape /dist/, /media/, /glossary/ and /remote/ use; do_HEAD and
        # do_POST dispatch /remote/ on u.path) is neither a literal nor a register line, so the checks above would let one
        # fold to `other` silently. The prefixes come from the same source and equal the families, and each folds in
        # _perf_http_key ITSELF: a family line without an elif branch there passes the set comparison and still counts
        # under other
        pre = re.compile(r'(?:\bp|u\.path)\.startswith\((?:"(/[^"]*)"|\(((?:"/[^"]*"(?:, )?)+),?\))\)')
        prefixes = {}
        for meth in ("do_GET", "do_HEAD", "do_OPTIONS", "do_POST"):
            src = inspect.getsource(getattr(km.Handler, meth))
            found = set()
            for m in pre.finditer(src):
                found.update([m.group(1)] if m.group(1) is not None else re.findall(r'"(/[^"]*)"', m.group(2)))
            prefixes[meth[3:]] = found
        families = {fam[:-1] for fam in km._PERF_HTTP_FAMILIES}
        self.assertTrue(all(fam.endswith("/*") for fam in km._PERF_HTTP_FAMILIES), km._PERF_HTTP_FAMILIES)
        self.assertEqual(set().union(*prefixes.values()), families,
                         "the startswith prefixes in the dispatches and the collapsed families differ by %s"
                         % sorted(set().union(*prefixes.values()) ^ families))
        for meth, found in sorted(prefixes.items()):
            for prefix in sorted(found):
                self.assertEqual(km._perf_http_key(meth, prefix + "x"), "%s %s*" % (meth, prefix),
                                 "%s %s: a family the register names has to fold in _perf_http_key too" % (meth, prefix))

    def test_http_key_is_method_plus_normalized_path(self):
        key = km._perf_http_key
        self.assertEqual(key("GET", "/sessions"), "GET /sessions")
        self.assertEqual(key("POST", "/perf"), "POST /perf", "GET /perf and POST /perf are separate rows")
        self.assertEqual(key("GET", "/dist/render.js"), "GET /dist/*")
        self.assertEqual(key("GET", "/dist/fonts/a-b-c.woff2"), "GET /dist/*", "sixty font files: one key")
        self.assertEqual(key("GET", "/media/romp-app-192.png"), "GET /media/*")
        self.assertEqual(key("GET", "/glossary/Quarterly%20Roadmap"), "GET /glossary/*", "a glossary term is the user's text: the lookups count, the term does not")
        self.assertEqual(key("GET", "/glossary/"), "GET /glossary/*")
        self.assertEqual(key("GET", "/remote/TESTHOST/ws"), "GET /remote/*/ws", "no host name in a key")
        self.assertEqual(key("HEAD", "/remote/TESTHOST/file"), "HEAD /remote/*/file")
        self.assertEqual(key("GET", "/remote/TESTHOST"), "GET /remote/*")
        self.assertEqual(key("", "/version"), "/version", "a handler without a method: the path alone")

    def test_http_keys_outside_the_route_table_fold_to_other(self):
        """A request's path is the requester's text (2026-09-18, a paste-safety review of the snapshot): a scanner's probe, a
        session id or a home path typed into a URL, an attached host's op stood as keys in the served http table. Every key
        is now one of the checked-in routes (_PERF_HTTP_ROUTES, per method), a collapsed family, or `other`; a remote path
        keeps its op only when the op is a route of the same method; a CORS preflight is allowed any route."""
        key = km._perf_http_key
        self.assertEqual(key("GET", "/nope/" + SID), "other", "a path that is no route names nothing")
        self.assertEqual(key("GET", "/home/tester/.claude/projects/x/" + SID + ".jsonl"), "other")
        self.assertEqual(key("GET", "/remote/TESTHOST/" + SID), "other", "a remote path whose op is no route")
        self.assertEqual(key("GET", "/remote/TESTHOST/sessions"), "GET /remote/*/sessions", "a remote path whose op is a GET route")
        self.assertEqual(key("POST", "/remote/TESTHOST/send"), "POST /remote/*/send", "the relay: the op is a POST route")
        self.assertEqual(key("GET", "/remote/TESTHOST/send"), "other", "the same op under the wrong method")
        self.assertEqual(key("HEAD", "/file"), "HEAD /file")
        self.assertEqual(key("HEAD", "/version"), "other", "do_HEAD dispatches /file alone")
        self.assertEqual(key("POST", "/version"), "other", "a GET route asked with POST is no route")
        self.assertEqual(key("OPTIONS", "/perf"), "OPTIONS /perf", "a preflight for any route")
        self.assertEqual(key("OPTIONS", "/nope"), "other")
        self.assertEqual(key("GET", "/PERF"), "other", "the dispatches are case-sensitive, so is the register")
        self.assertEqual(key("GET", "//perf"), "other")
        self.assertEqual(key("GET", "/perf/"), "other")
        self.assertEqual(key("", "/nope"), "other", "a handler without a method is judged against every method's routes")
        self.assertEqual(key("GET", "/ws"), "GET /ws"); self.assertEqual(key("GET", "/"), "GET /")
        for meth in ("GET", "HEAD", "POST"):                   # every registered route is its own key under its method
            for path in km._PERF_HTTP_ROUTES[meth]:
                self.assertEqual(key(meth, path), "%s %s" % (meth, path))
        for fam in km._PERF_HTTP_FAMILIES:
            self.assertEqual(key("GET", fam), "GET " + fam, "a collapsed family is a key in its own right")

    def test_reset_starts_over_and_moves_since(self):
        self.st.cycle(0.1); self.st.http_request("GET /x", 0.1)
        self.st.stage("jobs.autoNudge.parse", 0.001)          # a `jobs.` write from this thread owning no cycle: stagesForeign
        self.st.cycle_begin(); self.st.stage("jobs.apiHealth", 0.002); self.st.stage("jobs", 0.002); self.st.cycle(0.002)   # and the pusher's
        km._stage_marked("connect")(lambda: self.st.stage("push.chat", 0.003))()   # and a connect push's stage (2026-09-18)
        self.assertEqual(self.st.snapshot()["stagesForeign"], {"jobs.autoNudge.parse": 1.0}, "premise: both blocks hold a row")
        self.assertEqual(self.st.snapshot()["pusher"]["cycleJobsMs"]["apiHealth"], 2.0)
        self.assertEqual(self.st.snapshot()["pusher"]["connectPush"]["stagesMs"], {"push.chat": 3.0}, "premise: the connect table holds a row")
        before = self.st.snapshot()["since"]
        time.sleep(0.01)
        self.st.reset()
        snap = self.st.snapshot()
        self.assertEqual(snap["pusher"]["cycles"], 0)
        self.assertEqual(snap["http"], {})
        self.assertGreater(snap["since"], before)
        # the two owner-routed blocks start over with the rest (2026-09-18): the foreign block empty, the pusher's the nine at zero
        self.assertEqual(snap["stagesForeign"], {})
        self.assertEqual(snap["pusher"]["cycleJobsMs"], {j: 0.0 for j in km._PerfStats.CYCLE_JOBS})
        self.assertEqual(snap["pusher"]["connectPush"]["stagesMs"], {}, "the connect table too")

    def test_writers_are_thread_safe(self):
        def hammer():
            for _ in range(2000):
                self.st.wake(); self.st.send(("chat", SID), "full", 1); self.st.http_request("GET /p", 0.0)
        ts = [threading.Thread(target=hammer) for _ in range(8)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        snap = self.st.snapshot()
        self.assertEqual(snap["pusher"]["wakes"], 16000)
        self.assertEqual(snap["sends"]["full"]["chat"]["count"], 16000)
        self.assertEqual(snap["http"]["GET /p"]["count"], 16000)


class JobRowsByOwner(unittest.TestCase):
    """A `jobs.<job>` stage is written from two threads under one prefix: nine jobs in _pusher_cycle_jobs on the pusher and
    nineteen in _jobs_pass on the jobs thread (plus a job's parts from _sub_stage). Until 2026-09-18 stage() added every
    writer's wall to the one flat row, so a row said which thread's time it held only by the lists in the source, and a
    job that changed lists, or a test driving both loops on one thread, merged the two silently. Now stage() routes a
    dotted `jobs.` write by the WRITER'S OWNER: the jobs thread's to the flat row (stages_ms), the pusher's to
    pusher.cycleJobsMs under the job's name (the nine seeded at zero), and a thread owning neither loop's to stagesForeign
    under the stage name, counted rather than dropped. No stage name, mark, split row or boot row changes; three call
    sites did: the nudge walk's looks computation, a per-thread parse tally since the flat parse row moves for the jobs
    owner alone, and the two loop bodies' owner guards, which open the loop's own cycle on a thread that owns the other
    loop's cycle. JOBS stays the census as CYCLE_JOBS + PASS_JOBS."""

    NAME = "jobs.persistCheckpoints"      # a cycle job's name, written here from all three kinds of thread

    def _three_writers(self, jobs_part=False):
        """The note's run: the pusher (this thread) writes the name for 2 ms, a jobs thread for 3 ms inside a 3 ms pass, and a
        thread with no cycle for 1 ms; then the pusher closes its `jobs` container and its cycle. With `jobs_part` the jobs
        thread also runs a job with a part inside its pass (jobs.autoNudge.parse 2 ms inside jobs.autoNudge 2 ms, the pass
        5 ms): a legitimate part row in the flat table. Returns the snapshot."""
        st = km._PerfStats()
        st.cycle_begin()                                              # this thread is the pusher
        st.stage(self.NAME, 0.002)
        written, release, foreign_done = threading.Event(), threading.Event(), threading.Event()
        pass_s = 0.005 if jobs_part else 0.003

        def jobs_thread():
            st.cycle_begin("jobs")
            st.stage(self.NAME, 0.003)
            if jobs_part:
                st.stage("jobs.autoNudge.parse", 0.002); st.stage("jobs.autoNudge", 0.002)
            st.stage("jobsPass", pass_s)
            st.jobs_pass(pass_s)
            written.set()
            release.wait(5)                                           # alive until the foreign write is in: the owner map holds
            #                                                           this thread's ident, and a thread started after its exit can
            #                                                           be handed the same ident and read as the jobs owner (the
            #                                                           loops never exit on a kernel, so only a test meets this)

        def foreign_thread():                                         # a handler thread's: it opened no cycle
            st.stage(self.NAME, 0.001)
            foreign_done.set()
        jt = threading.Thread(target=jobs_thread); jt.start()
        self.assertTrue(written.wait(5), "the jobs thread wrote")
        ft = threading.Thread(target=foreign_thread); ft.start(); ft.join(5)
        self.assertTrue(foreign_done.is_set(), "the foreign thread wrote")
        release.set(); jt.join(5)
        st.stage("jobs", 0.002)
        st.cycle(0.002)
        return st.snapshot()

    def test_one_name_from_three_threads_lands_by_each_writers_owner(self):
        snap = self._three_writers()
        self.assertAlmostEqual(snap["stages_ms"][self.NAME], 3.0, msg="the flat row is the jobs thread's 3 ms alone (6 ms before: every writer's)")
        self.assertAlmostEqual(snap["pusher"]["cycleJobsMs"]["persistCheckpoints"], 2.0, msg="the pusher's 2 ms, under the job's name")
        self.assertEqual(sorted(snap["stagesForeign"]), [self.NAME], "the thread with no cycle is counted, not merged")
        self.assertAlmostEqual(snap["stagesForeign"][self.NAME], 1.0)
        # the split rows keep the owners apart as before, and the foreign write reaches no split
        self.assertEqual(sorted(snap["pusher"]["firstCycle"]["stages"]), ["jobs", self.NAME])
        self.assertAlmostEqual(snap["pusher"]["firstCycle"]["stages"][self.NAME]["ms"], 2.0)
        self.assertEqual(sorted(snap["jobs"]["firstPass"]["stages"]), [self.NAME, "jobsPass"])
        self.assertAlmostEqual(snap["jobs"]["firstPass"]["stages"][self.NAME]["ms"], 3.0)
        self.assertAlmostEqual(snap["stages_ms"]["jobs"], 2.0, msg="the containers are not dotted: the flat row as before")
        self.assertAlmostEqual(snap["stages_ms"]["jobsPass"], 3.0)
        for j in km._PerfStats.CYCLE_JOBS:
            self.assertIn(j, snap["pusher"]["cycleJobsMs"], "the nine are always present: %s" % j)
        self.assertIn(self.NAME[len("jobs."):], km._PerfStats.CYCLE_JOBS, "premise: the name is a cycle job's")

    # The two roll-up sums take the JOB rows alone, by a dot-free key, whoever wrote them (2026-09-18 review). The documented
    # bounds are per family: a job's parts (jobs.<job>.<part>, from _sub_stage) sum to at most their job, and the jobs sum to
    # at most their container (the pass for the flat rows, the pusher's `jobs` for cycleJobsMs). A sum over every dotted key
    # counted a part beside its job and went red on a legitimate part with the routing correct (a real run of both loops
    # puts jobs.autoNudge.key, .looks and .snapshot in the flat table); a sum over PASS_JOBS or CYCLE_JOBS by name excluded a
    # cycle job's name the jobs thread wrote and read zero on a planted mis-credit under that name. The three-way test below
    # holds the sums to both.
    @staticmethod
    def _flat_jobs(stages_ms):
        """The flat `jobs.<job>` rows' sum: dot-free under the prefix, `jobs.prelude` (the jobs thread's opening, outside the
        pass) excluded."""
        return sum(v for k, v in stages_ms.items() if k.startswith("jobs.") and "." not in k[len("jobs."):] and k != "jobs.prelude")

    @staticmethod
    def _cycle_jobs(cycle_jobs_ms):
        """The pusher's job rows' sum under cycleJobsMs: the block takes a part's name as a key too, so dot-free here as well."""
        return sum(v for k, v in cycle_jobs_ms.items() if "." not in k)

    def test_the_flat_job_rows_roll_up_to_the_pass_and_the_cycle_jobs_to_the_jobs_container(self):
        """Over a run of both loops the flat `jobs.<job>` rows are the jobs thread's, so they sum to at most its pass (6 > 3
        before, when the pusher's and the foreign write sat in them), and the pusher's rows sum to at most its `jobs`
        container. `jobs.prelude` is the jobs thread's opening, outside the pass, so it is not in the sum."""
        snap = self._three_writers()
        flat = self._flat_jobs(snap["stages_ms"])
        self.assertLessEqual(flat, snap["stages_ms"]["jobsPass"] + 1e-9, "the flat job rows against the pass: %r" % flat)
        self.assertGreater(flat, 0.0, "the jobs thread's write is in them")
        self.assertLessEqual(self._cycle_jobs(snap["pusher"]["cycleJobsMs"]), snap["stages_ms"]["jobs"] + 1e-9)
        self.assertGreater(self._cycle_jobs(snap["pusher"]["cycleJobsMs"]), 0.0)

    def test_the_roll_up_sum_passes_a_legitimate_part_and_catches_a_planted_mis_credit(self):
        """The guard's sum, on three snapshots (2026-09-18 review): the clean run (3.0 against a 3 ms pass), the run with a
        legitimate part on the jobs thread (5.0 against a 5 ms pass: the part is not counted beside its job, where a sum over
        every dotted key read 7.0 and went red with the routing correct), and the clean run with the pusher's 2 ms and the
        foreign 1 ms planted into the flat row, what a collector merging every writer served (6.0 against 3.0: caught, where
        a sum over the PASS_JOBS names read 0.0, the name being a cycle job's, and passed the merge)."""
        every_dotted = lambda st: sum(v for k, v in st.items() if k.startswith("jobs.") and k != "jobs.prelude")      # rejected
        pass_names = lambda st: sum(st["jobs." + j] for j in km._PerfStats.PASS_JOBS)                                # rejected
        clean = self._three_writers()
        part = self._three_writers(jobs_part=True)
        planted = self._three_writers()
        planted["stages_ms"][self.NAME] += 2.0 + 1.0
        with self.subTest("clean"):
            self.assertAlmostEqual(self._flat_jobs(clean["stages_ms"]), 3.0)
            self.assertLessEqual(self._flat_jobs(clean["stages_ms"]), clean["stages_ms"]["jobsPass"] + 1e-9)
        with self.subTest("legitimate part"):
            self.assertAlmostEqual(part["stages_ms"]["jobs.autoNudge.parse"], 2.0, msg="premise: the part is in the flat table")
            self.assertAlmostEqual(part["stages_ms"]["jobs.autoNudge"], 2.0)
            self.assertAlmostEqual(self._flat_jobs(part["stages_ms"]), 5.0)
            self.assertLessEqual(self._flat_jobs(part["stages_ms"]), part["stages_ms"]["jobsPass"] + 1e-9, "the part is not counted beside its job")
            self.assertGreater(every_dotted(part["stages_ms"]), part["stages_ms"]["jobsPass"], "the rejected every-key sum reads red here: %r" % every_dotted(part["stages_ms"]))
            self.assertLessEqual(part["stages_ms"]["jobs.autoNudge.parse"], part["stages_ms"]["jobs.autoNudge"] + 1e-9, "the part against its job: the other family's bound")
        with self.subTest("planted mis-credit"):
            self.assertAlmostEqual(self._flat_jobs(planted["stages_ms"]), 6.0)
            self.assertGreater(self._flat_jobs(planted["stages_ms"]), planted["stages_ms"]["jobsPass"], "caught: the merged writers exceed the pass")
            self.assertEqual(pass_names(planted["stages_ms"]), 0.0, "the rejected name-list sum is blind to it")

    def test_a_bare_jobs_write_is_the_flat_rows_for_every_writer_under_every_mark(self):
        """The `jobs` container is not routed (2026-09-19 review, the cell bin/romp's share comment is checked against): stage()
        adds a bare `jobs` write to the flat row whoever wrote it and whatever mark the thread carries. The pusher's owner
        writes 2 ms, the jobs owner 3 ms inside its pass, and a thread owning neither loop 1 ms bare, 1 ms under the "push"
        mark and 1 ms under the "connect" mark: the flat row reads 8.0, nothing reaches cycleJobsMs, stagesForeign or the
        connect table. The row is the pusher's on a kernel because _pusher_cycle_jobs is its one writer (the census below),
        not because stage() sends it there."""
        st = km._PerfStats()
        st.cycle_begin()                                              # this thread is the pusher
        st.stage("jobs", 0.002)
        done = {}

        def jobs_thread():
            st.cycle_begin("jobs")
            st.stage("jobs", 0.003); st.stage("jobsPass", 0.003); st.jobs_pass(0.003)
            done["jobs"] = True

        def owns_nothing():
            st.stage("jobs", 0.001)
            km._stage_marked("push")(lambda: st.stage("jobs", 0.001))()
            km._stage_marked("connect")(lambda: st.stage("jobs", 0.001))()
            done["foreign"] = True
        for target in (jobs_thread, owns_nothing):
            th = threading.Thread(target=target); th.start(); th.join(5)
        self.assertEqual(done, {"jobs": True, "foreign": True}, "both threads wrote")
        st.cycle(0.002)
        snap = st.snapshot()
        self.assertAlmostEqual(snap["stages_ms"]["jobs"], 8.0, msg="every writer's `jobs`, under every mark, in the one flat row")
        self.assertEqual(snap["stagesForeign"], {}, "a bare `jobs` write is never foreign")
        self.assertEqual(snap["pusher"]["cycleJobsMs"], {j: 0.0 for j in km._PerfStats.CYCLE_JOBS}, "nor a cycle job")
        self.assertEqual(snap["pusher"]["connectPush"]["stagesMs"], {}, "nor a connect stage")
        # the census: the kernel closes the `jobs` container at exactly one call site, inside _pusher_cycle_jobs, so the flat
        # row is the pusher's by having one writer; a second writer anywhere would merge into it without a trace
        src = inspect.getsource(km)
        sites = re.findall(r'_PERF_STATS\.stage\("jobs",', src)
        self.assertEqual(len(sites), 1, "the `jobs` container has one writer in the kernel: %d found" % len(sites))
        self.assertEqual(len(re.findall(r'_PERF_STATS\.stage\("jobs",', inspect.getsource(km._pusher_cycle_jobs))), 1,
                         "and it is _pusher_cycle_jobs")

    def test_a_pusher_write_under_a_name_outside_the_nine_still_lands_in_its_block(self):
        """A job's part (jobs.autoNudge.snapshot, _sub_stage) or a job that moved lists, written by the pusher's owner: the
        block takes the name as it comes, so nothing is dropped and the seeded nine are not a filter."""
        st = km._PerfStats()
        st.cycle_begin()
        st.stage("jobs.autoNudge.snapshot", 0.001); st.stage("jobs.autoNudge", 0.004)
        st.stage("jobs", 0.004); st.cycle(0.004)
        snap = st.snapshot()
        self.assertAlmostEqual(snap["pusher"]["cycleJobsMs"]["autoNudge.snapshot"], 1.0)
        self.assertAlmostEqual(snap["pusher"]["cycleJobsMs"]["autoNudge"], 4.0)
        self.assertEqual(snap["stages_ms"]["jobs.autoNudge"], 0.0, "the flat row is the jobs thread's: untouched")
        self.assertEqual(snap["stagesForeign"], {})
        self.assertEqual(sorted(snap["pusher"]["firstCycle"]["stages"]), ["jobs", "jobs.autoNudge", "jobs.autoNudge.snapshot"],
                         "the split takes the pusher's rows as before")

    def test_the_census_is_the_two_lists_and_the_flat_seed_is_the_pass_list(self):
        P = km._PerfStats
        self.assertEqual(P.JOBS, P.CYCLE_JOBS + P.PASS_JOBS, "JOBS stays the census")
        self.assertEqual(len(P.CYCLE_JOBS), 9)
        self.assertFalse(set(P.CYCLE_JOBS) & set(P.PASS_JOBS), "no job on both lists")
        self.assertEqual(len(P.JOBS), len(set(P.JOBS)), "no name twice")
        self.assertTrue({"jobs." + j for j in P.PASS_JOBS} <= set(P.STAGES), "the flat seed lists every pass job")
        self.assertFalse({"jobs." + j for j in P.CYCLE_JOBS} & set(P.STAGES), "and no cycle job")
        self.assertIn("jobs.prelude", P.STAGES); self.assertIn("jobsPass", P.STAGES); self.assertIn("jobs", P.STAGES)
        self.assertEqual(set(km._PerfStats().pusher) & {"cycleJobsMs"}, set(),
                         "the block is its own attribute, copied into the served pusher block, never the live dict")

    def test_every_job_row_key_fits_the_paste_safe_grammar_and_the_export_keeps_it(self):
        """The two new blocks are keyed by the kernel's own literals: a job name from CYCLE_JOBS under cycleJobsMs and a stage
        name (`jobs.` + a _job_stage or _sub_stage literal) under stagesForeign; never a client's or a user's text, so
        every key fits _PERF_IDENT (the served grammar) and the export's IDENT, is neither denied nor coarsened by
        cli/perf_public.py, and the values are numbers. The sub-stage names are read from the kernel's source, so a part
        added later is held to the same grammar."""
        src = inspect.getsource(km)
        parts = set(re.findall(r'_sub_stage\("([A-Za-z0-9_.]+)"\)', src)) | set(re.findall(r'stage\("jobs\.([A-Za-z0-9_.]+)"', src))
        self.assertTrue({"autoNudge.key", "autoNudge.parse", "autoNudge.snapshot", "autoNudge.looks"} <= parts, sorted(parts))
        names = set(km._PerfStats.STAGES) | set(km._PerfStats.JOBS) | {"jobs." + j for j in km._PerfStats.JOBS} \
            | {"jobs." + p for p in parts} | set(parts) | {"cycleJobsMs", "stagesForeign"}
        for k in sorted(names):
            self.assertTrue(km._PERF_IDENT.fullmatch(k), "outside the served grammar: %s" % k)
            self.assertTrue(pp.IDENT.fullmatch(k), "outside the export's grammar: %s" % k)
            self.assertFalse(pp.denied(k, 0.0), "denied by the export: %s" % k)
            self.assertNotIn(k, pp.BOUND_KEYS, "coarsened by the export: %s" % k)
        snap = self._three_writers()
        block = {"pusher": {"cycleJobsMs": snap["pusher"]["cycleJobsMs"]}, "stagesForeign": snap["stagesForeign"]}
        self.assertEqual(pp.fold(block), block, "the export keeps every key and value as served")
        for v in list(snap["pusher"]["cycleJobsMs"].values()) + list(snap["stagesForeign"].values()):
            self.assertIsInstance(v, float)
        self.assertEqual(pp.paste_problems(block), [])

    def test_the_collectors_docstring_names_the_new_rows(self):
        doc = km._PerfStats.__doc__
        # each row is cut by _doc_row, relative to the row's own indentation: Python 3.13 and later strip a docstring's
        # common leading whitespace at compile time, so a slice between six-space literals passed on the 3.12 venv and
        # raised ValueError on the 3.13 and 3.14t CI cells; the stagesForeign check below is a line-start match for the
        # same reason
        pusher_row = _doc_row(doc, "pusher")
        self.assertIn("cycleJobsMs", pusher_row, "the pusher row names its cycle jobs' block")
        stages_row = _doc_row(doc, "stages_ms")
        self.assertIn("cycleJobsMs", stages_row, "the stages_ms row sends the reader to the pusher's block for the nine")
        self.assertRegex(stages_row, r"moved to pusher\.cycleJobsMs", "and says the nine MOVED there, so a reader of an older capture knows where the numbers went")
        # the jobs clause itself, not the bare word: the same row's push sentence also says "counts under stagesForeign",
        # so a bare assertIn stayed green with the jobs cross-reference dropped (2026-09-18 review). The row is joined and
        # split first, as the reference-doc test does, because the docstring wraps at 80 columns and the two words sit on
        # different lines; the colon in "owner:" is load bearing (a bare "owner" matches inside "ownership")
        self.assertRegex(" ".join(stages_row.split()), r"writer's owner:.{0,120}stagesForeign",
                         "the stages_ms row's jobs sentence sends a thread owning neither loop's write to stagesForeign")
        self.assertRegex(doc, r"(?m)^ *stagesForeign ", "the foreign block has a row of its own")



    def test_the_reference_names_the_new_rows_and_the_discontinuity(self):
        """docs/reference.md's stages_ms entry names the blocks and states both discontinuities by their load-bearing words,
        not one wording: the date, the word "moved", the prefix each family moved to (`pusher.cycleJobsMs` for the nine
        cycle jobs, `pusher.connectPush.stagesMs` for the connect pushes' part of the push.* rows), and that the moved
        rows do not compare across a capture pair spanning the change; the jobs entry sends the reader to
        pusher.cycleJobsMs; the pusher entry lists both tables; the foreign entry names both families."""
        doc = Path(HERE).parent.joinpath("docs", "reference.md").read_text()
        para = doc[doc.index("- `stages_ms`:"):]
        para = " ".join(para[:para.index("\n- `stagesForeign`:")].split())   # the reference wraps at 80 columns: one line
        self.assertIn("`pusher.cycleJobsMs`", para)
        self.assertIn("2026-09-18", para, "the day the meaning changed")
        self.assertIn("moved", para, "the rows MOVED: a reader of an older capture is told where the numbers went")
        self.assertRegex(para, r"moved.{0,120}`pusher\.cycleJobsMs", "the nine moved to the pusher's block (the word and the prefix, close together)")
        self.assertRegex(para, r"moved.{0,120}`pusher\.connectPush\.stagesMs", "the connect pushes' part of the push rows moved to the connect table")
        self.assertRegex(para, r"not compar(e|able)", "the discontinuity: the moved rows are not comparable across the change")
        self.assertNotIn("count every push", para, "the fold sentence is gone")
        for j in km._PerfStats.CYCLE_JOBS:
            self.assertIn("`%s`" % j, para, "the nine are named: %s" % j)
        # The rows that keep their values are the pass jobs' container rows, counted from PASS_JOBS, with the reason (the
        # act-now pass closes no `jobs.<job>` container) and the clause that a job's part rows narrow under stagesForeign
        # (2026-09-19 review: round one corrected the sentence and nothing held the correction; the unscoped wording,
        # every remaining `jobs.<job>` row keeping its value, is false of the part rows and is refused here by shape).
        n_pass = _number_word(len(km._PerfStats.PASS_JOBS))
        self.assertRegex(para, r"%s remaining `jobs\.<job>` container rows \(the pass jobs\) keep their names and their values" % n_pass,
                         "the rows that keep their values are the pass jobs' %s container rows" % n_pass)
        self.assertRegex(para, r"closes no `jobs\.<job>` container", "the reason: the act-now pass closes no job container")
        self.assertRegex(para, r"`jobs\.autoNudge\.<part>` rows shed.{0,80}`stagesForeign`", "and a job's part rows narrow, under stagesForeign")
        self.assertNotRegex(para, r"`jobs\.<job>` rows keep their names", "round one's unscoped sentence (no `container`) is gone")
        self.assertIn("- `stagesForeign`:", doc, "the foreign block is documented as a top-level block")
        foreign_para = doc[doc.index("- `stagesForeign`:"):]
        foreign_para = " ".join(foreign_para[:foreign_para.index("\n- `")].split())
        self.assertIn("`jobs.<job>`", foreign_para); self.assertIn("`push.*`", foreign_para)
        jobs_para = doc[doc.index("- `jobs`: the jobs thread"):]
        jobs_para = jobs_para[:jobs_para.index("\n- `")]
        self.assertIn("`pusher.cycleJobsMs`", jobs_para)
        pusher_para = doc[doc.index("- `pusher`: `cycles`"):]
        pusher_para = " ".join(pusher_para[:pusher_para.index("\n- `")].split())
        self.assertIn("`cycleJobsMs`", pusher_para)
        self.assertIn("`stagesMs`", pusher_para, "the connect table is listed under connectPush")
        self.assertIn("`pusher.connectPush.stagesMs`", pusher_para, "the firstCycle sentence sends a connect push there, not to stages_ms")

    def test_the_ledger_entry_gives_the_measured_reason_for_the_rows_that_keep_their_values(self):
        """upstream/2026-09-18-stage-attribution.md states the jobs rows' meaning change with the same load-bearing words as the
        reference: the pass jobs' container rows, counted from PASS_JOBS, keep their values because the act-now path closes no
        `jobs.<job>` container, and a job's part rows shed that pass's share under stagesForeign. Round one replaced the
        entry's reason (that the housekeeping was the jobs thread's alone from the start, which the act-now test in
        tests/test_jobs_thread_split.py falsifies) and nothing held the replacement (2026-09-19 review)."""
        entry = " ".join(Path(HERE).parent.joinpath("upstream", "2026-09-18-stage-attribution.md").read_text().split())
        n_pass = _number_word(len(km._PerfStats.PASS_JOBS))
        self.assertRegex(entry, r"the %s `jobs\.<job>` container rows keep their names and their values because" % n_pass,
                         "the rows that keep their values are the pass jobs' %s container rows, with a reason" % n_pass)
        self.assertRegex(entry, r"closes no `jobs\.<job>` container", "the reason: the act-now path closes no job container")
        self.assertRegex(entry, r"`jobs\.autoNudge\.<part>` rows shed.{0,60}`stagesForeign`", "the part rows narrow, under stagesForeign")
        self.assertNotIn(RETIRED_WORDINGS["housekeeping-already-alone"], entry, "round one's false reason is gone")
        self.assertNotRegex(entry, r"those rows keep their names and their values, since", "and its unscoped sentence with it")


class PushRowsByPurpose(unittest.TestCase):
    """The push stages (`push` and the push.* rows: push.chat and its seams, push.feed, push.timeline, push.send and its
    seams, push.warm, push.feedFirst) are closed by two kinds of thread through one set of calls in _push: the pusher's
    cycle, and a fresh client's full push on its HTTP handler thread (_push_one: _push(connect=True)). Until 2026-09-18
    stage() added both to the one flat row, so stages_ms.push.chat over a window held every browser reload's build beside
    the pusher's, and `romp perf` divided it by the pusher's cycle time (a chat share above the push share, or above one
    hundred percent, while pages reloaded). Now stage() routes a push stage by the writer's PURPOSE or OWNER: the
    "connect" stage mark (what _push's decorator sets for connect=True) to pusher.connectPush.stagesMs under the stage
    name; the pusher's cycle owner (its push.* under the "push" mark and the `push` container it closes outside the
    mark) to the flat row; any other writer to stagesForeign, a "push"-marked write from a thread owning no cycle included
    (the mark says what _push was called for, not whose cycle it ran in). No seed: the connect table lists the stages
    connect pushes ran. No stage name, mark, split row or boot row changes."""

    PUSHER = (("push.chat", 0.005), ("push.send", 0.001))                                # the pusher's push, under its mark
    CONNECT = (("push.chat", 20.0), ("push.send", 0.5), ("push.feedFirst", 0.25))        # a reload's full push on a handler thread
    FOREIGN = (("push.chat", 0.001), ("push", 0.02))                                     # a thread with no mark and no cycle; its
    #                                                                                      `push` wall exceeds the room left in the
    #                                                                                      8 ms cycle beside the pusher's 6 ms, so
    #                                                                                      a foreign write merged into the flat row
    #                                                                                      is red at the cycle bound (at 0.002 the
    #                                                                                      merged 8.0 sat exactly on the 8.0 cycle)

    def _three_writers(self):
        """The pusher (this thread, the cycle's owner) closes push.chat and push.send under the "push" mark and then its `push`
        container outside it, as _pusher_cycle_jobs does; a connect thread under the "connect" mark closes three stages and
        the whole-wall counter _push_one keeps; a thread with no mark and no cycle closes two. Returns the snapshot."""
        st = km._PerfStats()
        st.cycle_begin()                                              # this thread is the pusher

        @km._stage_marked("push")                                     # the mark _push carries when the pusher calls it
        def pushers_push():
            for name, dt in self.PUSHER:
                st.stage(name, dt)
        pushers_push()
        done = {}

        @km._stage_marked("connect")                                  # the mark _push carries for connect=True (_push_one)
        def connect_push():
            for name, dt in self.CONNECT:
                st.stage(name, dt)
            st.connect_push("chat", sum(dt for _, dt in self.CONNECT))   # _push_one's whole-wall counter, beside the stages
            done["connect"] = True

        def foreign_thread():                                         # no cycle_begin, no mark: a thread standing for neither
            for name, dt in self.FOREIGN:
                st.stage(name, dt)
            done["foreign"] = True
        for target in (connect_push, foreign_thread):
            th = threading.Thread(target=target); th.start(); th.join(5)
        self.assertEqual(done, {"connect": True, "foreign": True}, "both threads wrote")
        st.stage("push", 0.006)                                       # the container: the pusher closes it outside the mark
        st.cycle(0.008)
        return st.snapshot()

    def test_one_push_stage_from_three_threads_lands_by_each_writers_purpose(self):
        snap = self._three_writers()
        st = snap["stages_ms"]
        self.assertAlmostEqual(st["push.chat"], 5.0, msg="the flat row is the pusher's 5 ms alone (20006 ms before: every writer's)")
        self.assertAlmostEqual(st["push.send"], 1.0)
        self.assertAlmostEqual(st["push"], 6.0, msg="the container, closed outside the mark, is the pusher's by its ownership of the cycle")
        self.assertEqual(st["push.feedFirst"], 0.0, "the connect push's cards-first feed is not the pusher's")
        self.assertEqual(snap["pusher"]["connectPush"]["stagesMs"],
                         {"push.chat": 20000.0, "push.send": 500.0, "push.feedFirst": 250.0}, "the connect push's stages, under their names, apart")
        self.assertEqual(snap["pusher"]["connectPush"]["count"], 1)
        self.assertEqual(snap["stagesForeign"], {"push.chat": 1.0, "push": 20.0}, "the thread with no mark and no cycle is counted, not merged")
        # the split rows keep the pusher's alone as before, and neither other writer reaches a split
        self.assertEqual(sorted(snap["pusher"]["firstCycle"]["stages"]), ["push", "push.chat", "push.send"])
        self.assertAlmostEqual(snap["pusher"]["firstCycle"]["stages"]["push.chat"]["ms"], 5.0)
        self.assertEqual(snap["pusher"]["cycleJobsMs"], {j: 0.0 for j in km._PerfStats.CYCLE_JOBS}, "no `jobs.` write: the other routing untouched")

    def test_the_flat_push_rows_roll_up_to_the_pushers_cycle_time_and_the_connect_rows_to_the_connect_pushes_wall(self):
        """Over a run of both, the flat push.* rows are the pusher's, so the direct children of `push` sum to at most `push`,
        which fits the pusher's cycle time (20757 ms of children against an 8 ms cycle before); the connect rows sum to at
        most the connect pushes' whole wall, pusher.connectPush.ms_sum. A seam rolls up to its container, not to `push`.
        Each of the three mis-credits is red here: a connect push merged into the flat rows at the container bound, the
        pusher's writes sent to stagesForeign at the greater-than-zero bound, and the foreign thread's merged into the
        flat rows at the cycle bound (its 20 ms `push` beside the pusher's 6 ms in an 8 ms cycle: 26.0 against 8.0)."""
        snap = self._three_writers()
        st = snap["stages_ms"]
        children = sorted(k for k in st if k.startswith("push.") and k.count(".") == 1)
        self.assertEqual(children, ["push.chat", "push.feed", "push.feedFirst", "push.send", "push.timeline", "push.warm"])
        self.assertLessEqual(sum(st[k] for k in children), st["push"] + 1e-9, "the push.* rows against the container: %r" % {k: st[k] for k in children})
        self.assertLessEqual(st["push"], snap["pusher"]["cycle_ms_sum"] + 1e-9, "the pusher's push fits its cycles")
        self.assertGreater(sum(st[k] for k in children), 0.0, "the pusher's writes are in them")
        cst = snap["pusher"]["connectPush"]["stagesMs"]
        self.assertLessEqual(sum(v for k, v in cst.items() if k.count(".") == 1), snap["pusher"]["connectPush"]["ms_sum"] + 1e-9)
        self.assertGreater(sum(cst.values()), 0.0)

    def test_a_push_under_the_push_mark_with_no_cycle_is_foreign_not_the_pushers_row(self):
        """The "push" mark says what _push was called for, not whose cycle it ran in: a push stage under it from a thread
        owning no cycle is neither a connect push nor the cycle's owner, so it counts under stagesForeign beside the
        container the same thread closes with no mark, and the flat rows the CLI divides by the pusher's cycle time take
        nothing from it. The mark alone as the pusher's stand-in (this test's first meaning, 2026-09-18 review) let a
        _push(connect=False) from any other thread merge its walls into those rows: a push share above one hundred percent
        with stagesForeign empty. Latent on a kernel: _push_all's one caller opens the cycle first and _push_one passes
        connect=True, so no live caller takes this road."""
        st = km._PerfStats()
        out = {}

        def bare_thread():
            km._stage_marked("push")(lambda: st.stage("push.feed", 0.002))()
            st.stage("push", 0.002)
            out["done"] = True
        th = threading.Thread(target=bare_thread); th.start(); th.join(5)
        self.assertTrue(out.get("done"))
        snap = st.snapshot()
        self.assertEqual(snap["stages_ms"]["push.feed"], 0.0, "the flat row takes nothing from a thread owning no cycle, marked or not")
        self.assertEqual(snap["stages_ms"]["push"], 0.0)
        self.assertEqual(snap["stagesForeign"], {"push.feed": 2.0, "push": 2.0}, "both counted apart, under their names")
        self.assertEqual(snap["pusher"]["connectPush"]["stagesMs"], {})

    # The two cells below are what the routing sentences in the reference, the ledger entry, bin/romp and this module are
    # checked against (2026-09-19 review): ownership is a thread's registration in _owners, made by cycle_begin and left
    # standing by cycle(), not the interval a cycle is open, so the same push stage closed in the gap between two cycles
    # lands in the flat rows from the registered thread and under stagesForeign from a thread that registered nothing.
    def test_a_push_stage_the_pushers_thread_closes_between_two_cycles_is_the_flat_rows(self):
        """The pusher's thread opens a cycle, closes it, and then closes a push stage under _push's "push" mark and its `push`
        container outside it before the next cycle opens: both land in the flat rows, nothing under stagesForeign, and the
        gap's writes reach no split (the next cycle_begin empties the open split, so they belong to no cycle's rows)."""
        st = km._PerfStats()
        st.cycle_begin()                                              # this thread is the pusher
        km._stage_marked("push")(lambda: st.stage("push.chat", 0.005))()
        st.stage("push", 0.005); st.cycle(0.005)                     # the first cycle closes
        self.assertEqual(st._mine(), "pusher", "premise: the close of a cycle leaves the thread registered as the owner")
        km._stage_marked("push")(lambda: st.stage("push.feed", 0.003))()   # between the cycles, under _push's mark
        st.stage("push", 0.002)                                       # and outside it
        st.cycle_begin(); st.cycle(0.001)                             # the second cycle, with nothing written inside it
        snap = st.snapshot()
        self.assertAlmostEqual(snap["stages_ms"]["push.feed"], 3.0, msg="the gap's stage is the flat row's: the thread owns the pusher's cycle")
        self.assertAlmostEqual(snap["stages_ms"]["push"], 7.0, msg="the gap's container too")
        self.assertEqual(snap["stagesForeign"], {}, "nothing foreign: the writer is the registered owner")
        self.assertEqual(snap["pusher"]["connectPush"]["stagesMs"], {})
        ring = snap["pusher"]["stageRing"]
        self.assertEqual(len(ring), 2)
        self.assertEqual(sorted(ring[0]["stages"]), ["push", "push.chat"], "the first cycle's split holds its own writes")
        self.assertEqual(ring[1]["stages"], {}, "the gap's writes are in no split: the second opening emptied them")

    def test_a_push_stage_from_a_thread_owning_nothing_is_foreign_while_the_owner_sits_between_cycles(self):
        """At the same instant, the pusher's thread between two cycles and a thread that opened no cycle each close push.feed,
        the second under the "push" mark and bare: the owner's write is the flat row's and both of the other's count under
        stagesForeign. Neither writer is inside an open cycle; the registration is what separates them."""
        st = km._PerfStats()
        st.cycle_begin(); st.stage("push", 0.001); st.cycle(0.001)  # one cycle, closed: this thread stays registered
        done = {}

        def owns_nothing():
            km._stage_marked("push")(lambda: st.stage("push.feed", 0.004))()
            st.stage("push.feed", 0.001)
            done["written"] = True
        th = threading.Thread(target=owns_nothing); th.start(); th.join(5)
        self.assertTrue(done.get("written"))
        km._stage_marked("push")(lambda: st.stage("push.feed", 0.002))()   # the owner's, in the same gap
        snap = st.snapshot()
        self.assertEqual(snap["stagesForeign"], {"push.feed": 5.0}, "the thread owning nothing: counted apart, marked or not")
        self.assertAlmostEqual(snap["stages_ms"]["push.feed"], 2.0, msg="the flat row is the registered owner's write alone")
        self.assertEqual(snap["pusher"]["connectPush"]["stagesMs"], {})

    def test_a_fresh_snapshot_seeds_no_connect_stage_row_and_reset_empties_the_table(self):
        """No seed, and the docstring says so: a seeded push.warm or `push` row would be one a connect push can never move (the
        warm runs for the pusher alone, and _push_one closes no container), reading as time connect pushes never spend
        there. The table is its own attribute, copied into the served block; the live counters dict never holds it."""
        st = km._PerfStats()
        self.assertEqual(st.snapshot()["pusher"]["connectPush"]["stagesMs"], {})
        self.assertNotIn("stagesMs", st.connect_push_stats)
        km._stage_marked("connect")(lambda: st.stage("push.timeline", 0.004))()
        self.assertEqual(st.snapshot()["pusher"]["connectPush"]["stagesMs"], {"push.timeline": 4.0})
        st.reset()
        self.assertEqual(st.snapshot()["pusher"]["connectPush"]["stagesMs"], {})
        doc = km._PerfStats.__doc__
        # the row by _doc_row, relative to its own indentation: Python 3.13 and later strip a docstring's common leading
        # whitespace at compile time, so a slice between six-space literals raised ValueError on the 3.13 and 3.14t CI cells
        self.assertIn("No seed", _doc_row(doc, "pusher"), "the pusher row says the table is unseeded")

    def test_every_push_row_key_fits_the_paste_safe_grammar_and_the_export_keeps_it(self):
        """The connect table and the foreign block are keyed by the kernel's own stage literals (`push`, the push.* names in
        STAGES, and every `push.` name stage() is called with in the kernel's source), under the fixed keys connectPush and
        stagesMs; never a client's or a user's text. Every key fits _PERF_IDENT (the served grammar) and the export's IDENT,
        is neither denied nor coarsened by cli/perf_public.py (a denied key would drop the table from an export, a coarsened
        one would round it), and the values are numbers; the fold keeps the populated blocks byte for byte and the paste
        walk finds nothing. The stage names are read from the source, so a seam added later is held to the same grammar."""
        src = inspect.getsource(km)
        written = set(re.findall(r'_PERF_STATS\.stage\("(push(?:\.[A-Za-z0-9_.]+)?)"', src))
        self.assertTrue({"push", "push.chat", "push.chat.sig", "push.feedFirst", "push.send.compare", "push.warm"} <= written, sorted(written))
        names = written | {k for k in km._PerfStats.STAGES if k.startswith("push")} | {"connectPush", "stagesMs", "stagesForeign", "stages_ms"}
        for k in sorted(names):
            self.assertTrue(km._PERF_IDENT.fullmatch(k), "outside the served grammar: %s" % k)
            self.assertTrue(pp.IDENT.fullmatch(k), "outside the export's grammar: %s" % k)
            self.assertFalse(pp.denied(k, 0.0), "denied by the export: %s" % k)
            self.assertNotIn(k, pp.BOUND_KEYS, "coarsened by the export: %s" % k)
        snap = self._three_writers()
        tab = snap["pusher"]["connectPush"].get("stagesMs")           # the premise first: a kernel without the table fails here, by name
        self.assertEqual(sorted(tab or {}), ["push.chat", "push.feedFirst", "push.send"], "premise: the table is populated")
        block = {"pusher": {"connectPush": snap["pusher"]["connectPush"]}, "stagesForeign": snap["stagesForeign"],
                 "stages_ms": {k: v for k, v in snap["stages_ms"].items() if k.startswith("push")}}
        self.assertEqual(pp.fold(block), block, "the export keeps every key and value as served")
        for v in list(snap["pusher"]["connectPush"]["stagesMs"].values()) + list(snap["stagesForeign"].values()) + list(block["stages_ms"].values()):
            self.assertIsInstance(v, float)
        self.assertEqual(pp.paste_problems(block), [])

    def test_the_collectors_docstring_names_the_connect_table(self):
        doc = km._PerfStats.__doc__
        # each row is cut by _doc_row, relative to the row's own indentation: Python 3.13 and later strip a docstring's
        # common leading whitespace at compile time, so a slice between six-space literals raised ValueError on the 3.13
        # and 3.14t CI cells
        pusher_row = _doc_row(doc, "pusher")
        self.assertIn("connectPush", pusher_row, "the pusher row documents the block the table rides")
        self.assertIn("stagesMs", pusher_row)
        stages_row = _doc_row(doc, "stages_ms")
        self.assertIn("pusher.connectPush.stagesMs", stages_row, "the stages_ms row sends the reader to the connect table")
        self.assertRegex(stages_row, r"moved to pusher\.connectPush\.stagesMs", "and says the connect pushes' part moved there")
        self.assertIn("2026-09-18", stages_row)
        self.assertNotIn("EVERY caller", stages_row, "the fold sentence is gone")
        foreign_row = _doc_row(doc, "stagesForeign")
        self.assertIn("push", foreign_row, "the foreign block names the push stages as a second family")


# git's own wording for a tree with no repository above it; the one nonzero exit that is a skip (the constant
# tests/test_entrypoints_executable.py uses for the same call)
NOT_A_REPOSITORY = "not a git repository"


def _git_bytes(root, *args):
    """git's stdout, as bytes, for `git -C root args`. Skips the caller only when git is not installed or says `root`
    is not in a repository; any other failure is an AssertionError carrying git's stderr and exit code, never a skip
    (the shape of tests/test_entrypoints_executable.py's _index, whose docstring says why: a skip there would disarm
    the check while the run stays green). stdout stays bytes because a -z listing is split on NUL; stderr alone is
    decoded, with errors replaced, so git's words reach the message whatever their encoding."""
    try:
        proc = subprocess.run(["git", "-C", str(root), *args], capture_output=True, timeout=60)
    except FileNotFoundError:
        raise unittest.SkipTest("git is not installed; the routing sweep cannot list the tree")
    if proc.returncode != 0:
        stderr = proc.stderr.decode(errors="replace").strip()
        if NOT_A_REPOSITORY in stderr:
            raise unittest.SkipTest("not a git checkout (git %s exited %d: %s)" % (" ".join(args), proc.returncode, stderr))
        raise AssertionError("git %s exited %d in %s, so the routing sweep cannot list the tree and the check would be "
                             "disarmed; fix the checkout rather than skipping:\n%s" % (" ".join(args), proc.returncode, root, stderr))
    return proc.stdout


def _scratch_repo(test):
    """A git repository of its own under the run's temp root (removed with the test, and swept with the root either way)
    for a pin that needs a listed file the live tree must not hold: a file placed in it is untracked and unignored, so
    `git ls-files --others --exclude-standard` lists it and RoutingStatements._scan reads it, with no lock taken and no
    write into the checkout. Its git init runs with every GIT_* variable scrubbed but GIT_TEST_* and reads no global or
    system config (the ScratchCheckout shape in tests/test_entrypoints_executable.py, whose env() says why: a hook's
    GIT_INDEX_FILE would otherwise send the scratch repo's operations into this checkout's index)."""
    d = Path(tempfile.mkdtemp())
    test.addCleanup(shutil.rmtree, d, ignore_errors=True)
    env = {name: value for name, value in os.environ.items() if not name.startswith("GIT_") or name.startswith("GIT_TEST_")}
    env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
    subprocess.run(["git", "init", "-q", str(d)], env=env, check=True, capture_output=True, timeout=60)
    return d


class RoutingStatements(unittest.TestCase):
    """Every place in the tree that names a routed block (stagesForeign, pusher.cycleJobsMs, pusher.connectPush.stagesMs, or
    their attributes) is where a sentence about the routing can live, and two review rounds found such a sentence wrong
    in a way the code was not, each time in a file a hand-kept sweep had missed (2026-09-19 review). The sweep's scope is
    therefore derived here from the tree, not listed: the files that name a block are found by reading them, pinned as a
    set so a new one turns the test red until it is swept, and none of them may carry a wording a round retired
    (RETIRED_WORDINGS at the top of this module). The truth of what the files say is measured by the routing tests above
    (PushRowsByPurpose, JobRowsByOwner); this test holds only the scope and the retired wordings.

    The tree is every text file git tracks or would track (PR 797's closing check, 2026-09-19): `git ls-files --cached
    --others --exclude-standard` at the repo root, so an untracked file is swept before it is committed, no directory
    excluded, symlinks skipped (bin/romp-kernel points at the kernel), a file read as text when its first 8 KiB hold no
    NUL byte and it decodes as UTF-8. The eight-directory walk this replaced omitted the root files, plans/, claude/,
    hooks/, vscode-extension/ and ui/ outside ui/webview; none of them named a block, so the pin was complete by luck
    and would not have caught a statement added there. Measured at 639043a31 in a clean worktree: git lists 3109 paths,
    14 are symlinks, 41 hold a NUL in their first 8 KiB, none fails to decode, 3054 read as text, 71.8 MB (decimal) of
    them. The count moves with every file added, so it is only ever quoted with its head; no directory list is kept. An
    untracked file git does not ignore is read too: ui/out-tests, the webview test build's output, is not ignored, so
    its compiled files are read when it exists; no ui/webview source names a block today, so no copy there can, and a
    source that starts to would red this pin on a machine holding the build output before it did in CI. The scan
    takes a file lock shared and the plant test below takes it exclusive: pytest-xdist can run the tests on different
    workers at once, and a sibling's scan during the plant would read the plant and red. The lock is one file per
    checkout, in its git dir, so an xdist worker, a second pytest run, or a run under its own TMPDIR all wait on the
    same inode (the first version sat in the per-process temp root tests/__init__.py mints and serialised nothing).

    What PLACES counts, since PR 797's closing check asked for the derivation: one entry per text file in the tree
    above whose text matches BLOCKS at least once, however many times it matches, so the count the sweep holds is the
    size of PLACES, a set of files. `git ls-files -z --cached --others --exclude-standard | xargs -0 grep -I -l -E
    '<the BLOCKS pattern>'` at the repo root approximates it (at 639043a31 it lists the same files plus the bin/romp-kernel
    symlink the scan skips) and is not the scan's rule: grep -I drops a file when it meets a NUL byte in what it has read
    before the first match, so a NUL after the scan's 8 KiB probe hides a file the scan reads, and grep -I has no UTF-8
    requirement, so it lists a file the scan skips on a decode error; at 639043a31 no listed file is in either class. No
    count of statements is held anywhere: a statement has no unit a regex fixes (a line matching BLOCKS, an occurrence
    of it and a sentence give three different numbers over the same files), and the sweep needs the files to read, not
    a tally."""

    BLOCKS = re.compile(r"stagesForeign|cycleJobsMs|connectPush\.stagesMs|stages_foreign|cycle_jobs_ms|connect_stages_ms")
    # the places a routing sentence lives today; a file added here has been read against the measured cells
    PLACES = {"bin/romp", "docs/reference.md", "kernel/kernel.py", "tests/test_first_cycle_stage_split.py",
              "tests/test_jobs_thread_split.py", "tests/test_perf_stats.py", "upstream/2026-09-18-stage-attribution.md"}
    PROBE = 8192                                  # the bytes read first from every file; a NUL among them ends the read, so a png, a
    #                                               font or a recording costs its header and nothing more

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # A plant exists only while its owner holds the exclusive lock, so whatever the glob finds under that lock is a
        # dead run's leftover (pytest-timeout's os._exit, which CI's --timeout-method=thread uses, a SIGKILL, a scope
        # stop: none of them reaches the plant test's finally), and the glob matches no tracked file (git grep
        # routing-sweep-plant finds only this module). Safe ONLY because the lock is one file per checkout (the
        # previous commit): under a per-process lock this could delete a sibling's live plant.
        with cls._tree_lock(exclusive=True) as root:
            cls._remove_stale_plants(root)

    @classmethod
    def _remove_stale_plants(cls, root):
        for old in (root / "plans").glob("routing-sweep-plant-*.md"):
            old.unlink(missing_ok=True)

    @classmethod
    def _lock_path(cls, root):
        # The lock is a property of the CHECKOUT, not of the run: `git rev-parse --absolute-git-dir` is one path for
        # every process over this worktree (an xdist worker, a second pytest run, a run under its own TMPDIR), and in
        # a linked worktree it is <main>/.git/worktrees/<name>, so sibling worktrees lock apart. It is also OUTSIDE the
        # scanned tree, on purpose: a lock file anywhere inside the worktree, plans/ or the root, would be an untracked,
        # unignored file, and this scan reads exactly those. The first version sat in tempfile.gettempdir(), which
        # tests/__init__.py repoints to a private root per process, so every process locked a different inode and
        # nothing waited.
        return Path(os.fsdecode(_git_bytes(root, "rev-parse", "--absolute-git-dir").strip())) / "romp-routing-sweep.lock"

    @classmethod
    @contextlib.contextmanager
    def _tree_lock(cls, exclusive):
        """The repo root, held under a file lock that lives in the checkout's git dir (one per linked worktree), shared
        by every process over this tree whatever its TMPDIR, and outside the scanned tree; flock, so a process that
        dies drops it."""
        root = Path(HERE).parent
        lock = cls._lock_path(root)
        with open(lock, "a+") as fh:
            fcntl.flock(fh, fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
            try:
                yield root
            finally:
                fcntl.flock(fh, fcntl.LOCK_UN)

    def _scan(self, root):
        """{relative path: text} for every text file under `root` that git tracks or would track and that names a block."""
        listing = subprocess.run(["git", "-C", str(root), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                                 capture_output=True, check=True).stdout
        found = {}
        # A name git lists is bytes. fsdecode keeps an undecodable byte as a surrogate (surrogateescape on POSIX), so the
        # file is still read under its real name (os.fsencode gives the bytes back at the open) and a pin failure prints
        # it in a %r; never errors="ignore" or "replace", which would point at a path that does not exist and drop the
        # file silently. Decoded per entry, so any failure here stays bound to the entry it came from; the first version
        # decoded the joined listing strictly, and one such name errored every test here naming an offset and no file.
        for entry in listing.split(b"\0"):
            if not entry:
                continue
            rel = os.fsdecode(entry)
            path = root / rel
            if path.is_symlink():
                continue
            try:
                with open(path, "rb") as fh:
                    head = fh.read(self.PROBE)
                    if b"\0" in head:                 # a binary: its header is all that was read
                        continue
                    raw = head + fh.read()            # bytes, so a character straddling byte 8192 decodes whole below
            except OSError:                           # in the index, gone from the working tree (the open is what raises)
                continue
            try:
                text = raw.decode()
            except UnicodeDecodeError:
                continue
            if self.BLOCKS.search(text):
                found[rel] = text
        return found

    def _places(self):
        with self._tree_lock(exclusive=False) as root:
            return self._scan(root)

    def _pin_swept_set(self, found):
        # Direction-aware: the two sides of the set difference want different remedies, and one sentence for both sent a
        # contributor whose scratch note the scan had read to add it to PLACES, then red again once the note was deleted
        # (round 1). %r throughout, so a name holding a surrogate (a non-UTF-8 name, fsdecoded) prints.
        extra = sorted(set(found) - self.PLACES)
        gone = sorted(self.PLACES - set(found))
        parts = []
        if extra:
            parts.append("names a routed block and is not in PLACES: %r. The scan reads every text file git tracks or would "
                         "track, so an untracked, unignored file counts: your own scratch (a note, a saved diff, an editor "
                         "backup, a .orig or .rej) is removed from the tree or ignored (.git/info/exclude), a new source or "
                         "doc is read against the measured cells and then added to PLACES" % extra)
        if gone:
            parts.append("in PLACES and no longer names a routed block, or gone from the tree: %r. Remove it from PLACES (or "
                         "restore the file)" % gone)
        if parts:
            self.fail("; ".join(parts))

    def _pin_no_retired_wording(self, found):
        # One pattern per phrase: its words in order with any run of whitespace between them, newlines and tabs included,
        # which is what collapsing the text with " ".join(text.split()) matched before, at the cost of a second copy of
        # every matched file's words; the regex reads the text in place. re.escape keeps a phrase's punctuation literal
        # (one of them carries an underscore; the phrase itself is not written here, since this file is swept too).
        patterns = {key: re.compile(r"\s+".join(re.escape(word) for word in phrase.split())) for key, phrase in RETIRED_WORDINGS.items()}
        for rel, text in sorted(found.items()):
            for key, phrase in sorted(RETIRED_WORDINGS.items()):
                self.assertIsNone(patterns[key].search(text), "%s carries a wording a review round retired (%s): %r" % (rel, key, phrase))
                #                                                 not assertNotIn: its failure message would print the whole file

    def test_the_files_that_name_a_routed_block_are_the_swept_set(self):
        self._pin_swept_set(self._places())

    def test_no_swept_file_carries_a_retired_wording(self):
        self._pin_no_retired_wording(self._places())

    def test_the_file_set_is_read_from_the_tree_not_listed(self):
        """A file planted in plans/, a directory the replaced walk never entered, naming a block and carrying a retired
        wording, is found by the scan and reds both pins; without it both are green. Both states are measured in this one
        test under the exclusive lock, the plant removed in a finally, its name unique to this process. A plant a killed
        run left behind is removed by setUpClass before any test here scans, so a plant-named file in plans/ is a test
        artifact, never content."""
        with self._tree_lock(exclusive=True) as root:
            clean = self._scan(root)
            self._pin_swept_set(clean); self._pin_no_retired_wording(clean)                          # green without the plant
            missing = sorted(self.PLACES)[0]
            with self.assertRaises(AssertionError) as gone:                                          # the other direction, off the same scan
                self._pin_swept_set({k: v for k, v in clean.items() if k != missing})
            self.assertIn(missing, str(gone.exception), "a swept file that is gone is named")
            self.assertIn("Remove it from PLACES", str(gone.exception), "with its own remedy")
            self.assertNotIn("tracks or would track", str(gone.exception), "and not the extra clause")
            plant = root / "plans" / ("routing-sweep-plant-%d-%s.md" % (os.getpid(), os.urandom(4).hex()))
            rel = str(plant.relative_to(root))
            try:
                plant.write_text("A planted note naming stagesForeign, " + RETIRED_WORDINGS["push-inside-cycle"].replace(" ", "\n  ", 1) + ".\n")
                #                the phrase broken across a line, so the whitespace-flexible match is exercised, not only the single-space form
                planted = self._scan(root)
                self.assertIn(rel, sorted(planted), "the scan reads the tree, untracked files included: the plant is found")
                #                    the paths, not the dict: a failure would otherwise print seven files' text
                with self.assertRaises(AssertionError) as swept:
                    self._pin_swept_set(planted)
                self.assertIn(rel, str(swept.exception), "the swept-set pin names the plant")
                self.assertIn("tracks or would track", str(swept.exception), "and says the scan reads untracked files")
                self.assertNotIn("Remove it from PLACES", str(swept.exception), "the plant is an extra, so only that clause prints")
                with self.assertRaises(AssertionError) as worded:
                    self._pin_no_retired_wording(planted)
                self.assertIn(rel, str(worded.exception), "the wording pin names the plant")
                self.assertIn("push-inside-cycle", str(worded.exception), "and the wording it carries")
            finally:
                plant.unlink(missing_ok=True)
            after = self._scan(root)
            self.assertNotIn(rel, sorted(after), "the plant is gone")
            self._pin_swept_set(after); self._pin_no_retired_wording(after)                          # green again

    def test_a_plant_left_by_a_killed_run_is_removed_before_any_scan(self):
        """A plant with a pid that is never this process (1), the shape a run killed inside the plant window leaves, is
        removed by the healer setUpClass runs, and the tree scans green after it. The healer's placement is pinned on
        setUpClass's source: inside the plant test it would heal only from the second run, since the wording pin sorts
        first and reads the leftover (round 1's refuters measured '1 failed, 3 passed' there, '4 passed' here)."""
        with self._tree_lock(exclusive=True) as root:
            stale = root / "plans" / "routing-sweep-plant-1-stale0000.md"
            try:
                stale.write_text("A planted note naming stagesForeign, " + RETIRED_WORDINGS["push-inside-cycle"] + ".\n")
                self._remove_stale_plants(root)
                self.assertFalse(stale.exists(), "the healer removes a plant whose owner is not this process")
                after = self._scan(root)
                self.assertNotIn("plans/routing-sweep-plant-1-stale0000.md", sorted(after), "and the scan no longer sees it")
                self._pin_swept_set(after); self._pin_no_retired_wording(after)                      # green once healed
            finally:
                stale.unlink(missing_ok=True)
        source = inspect.getsource(RoutingStatements.setUpClass)
        self.assertIn("with cls._tree_lock(exclusive=True)", source, "the healer runs under the exclusive lock")
        self.assertIn("cls._remove_stale_plants(root)", source, "and is called from setUpClass, before any test here scans")
        #             the call forms, not the names: a comment in setUpClass naming the helper must not satisfy this pin

    def test_a_binary_file_is_rejected_on_its_first_bytes_not_read_whole(self):
        """A 64 MiB sparse file whose first bytes hold a NUL and a block name after it (a probe-less scan would list it)
        costs the scan its header and nothing more: the peak allocation during the scan stays under 16 x PROBE. Measured
        with tracemalloc per call, not ru_maxrss: that is a process high-water mark an earlier test can already have
        raised past 64 MiB, which would let a scan that reads the blob whole pass."""
        d = _scratch_repo(self)
        (d / "control.md").write_text("a control note naming stagesForeign\n")    # so the absence below cannot pass vacuously
        with open(d / "blob.bin", "wb") as fh:
            fh.write(b"\0" * 16 + b"stagesForeign")
            fh.truncate(64 * 2**20)
        tracing = tracemalloc.is_tracing()                                          # a tracer already running is used as is
        if not tracing:
            tracemalloc.start()
        try:
            tracemalloc.reset_peak()
            found = self._scan(d)
            peak = tracemalloc.get_traced_memory()[1]
        finally:
            if not tracing:
                tracemalloc.stop()
        listed = os.fsdecode(_git_bytes(d, "ls-files", "-z", "--others", "--exclude-standard")).split("\0")
        self.assertIn("blob.bin", listed, "git lists the blob, so the scan met it (a machine-wide ignore of .bin would hide it)")
        self.assertIn("control.md", sorted(found))
        self.assertNotIn("blob.bin", sorted(found), "a NUL in the first bytes rejects the file")
        #                            the paths, not the dict: a failure would otherwise print the decoded blob, 64 MiB of it
        self.assertLess(peak, 16 * self.PROBE, "the scan read the blob past its first bytes: peak %d" % peak)

    def test_a_path_whose_name_is_not_utf8_is_read_and_named(self):
        """One listed path whose NAME is not valid UTF-8 (git ls-files -z emits the raw bytes) used to error every test
        here with a UnicodeDecodeError naming an offset into the joined listing and no file. The file is read under its
        real name, and a pin failure names it, surrogate and all."""
        d = _scratch_repo(self)
        name = b"notes-caf\xe9.md"                                                # latin-1 e-acute, not UTF-8
        with open(os.path.join(os.fsencode(str(d)), name), "wb") as fh:
            fh.write(b"a note naming stagesForeign\n")
        found = self._scan(d)                                                     # must not raise
        rel = os.fsdecode(name)                                                   # 'notes-caf\udce9.md'
        self.assertIn(rel, sorted(found), "the file is read under its real name")
        with self.assertRaises(AssertionError) as swept:
            self._pin_swept_set(found)
        self.assertIn(repr(rel), str(swept.exception), "the failure names the file, surrogate and all")

    def test_the_lock_is_one_file_for_every_process_of_this_tree(self):
        """A second process over this checkout with its own TMPDIR and no record of this run's system temp dir (the
        two-sweep-slots case a run-keyed lock misses) computes the same lock path, and its exclusive hold is seen here:
        a non-blocking flock in either mode is refused while it holds, a shared waiter stays blocked until it lets go
        and gets in after. Event based, no sleep: the child says when it holds and is told when to release."""
        root = Path(HERE).parent
        holder = ("import sys\n"
                  "from tests.test_perf_stats import RoutingStatements as R\n"
                  "with R._tree_lock(exclusive=True) as root:\n"
                  "    print(R._lock_path(root), flush=True)\n"
                  "    sys.stdin.readline()\n")
        child_tmp = tempfile.mkdtemp()                                # under this process's run root, swept with it
        env = dict(os.environ, TMPDIR=child_tmp)
        env.pop("ROMP_TESTS_SYSTEM_TMPDIR", None)                     # so the child's tests/__init__.py records its own
        errlog = open(os.path.join(child_tmp, "holder-stderr.log"), "w+b")   # a file, not a pipe: the kernel load may talk
        child = subprocess.Popen([sys.executable, "-c", holder], cwd=root, env=env, stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE, stderr=errlog, text=True)
        entered = threading.Event()

        def waiter():
            with self._tree_lock(exclusive=False):
                entered.set()
        thread = threading.Thread(target=waiter, daemon=True)
        try:
            line = child.stdout.readline()
            if not line:
                errlog.seek(0)
                self.fail("the holder printed no lock path; its stderr:\n%s" % errlog.read().decode(errors="replace"))
            self.assertEqual(Path(line.strip()), self._lock_path(root),
                             "two processes with different TMPDIRs compute one lock path")
            with open(self._lock_path(root), "a+") as fh:
                with self.assertRaises(BlockingIOError, msg="the holder's exclusive lock refuses a shared try here"):
                    fcntl.flock(fh, fcntl.LOCK_SH | fcntl.LOCK_NB)
                with self.assertRaises(BlockingIOError, msg="and an exclusive try"):
                    fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
            thread.start()
            self.assertFalse(entered.wait(0.5), "a shared waiter is blocked while the holder holds")
            child.stdin.write("\n"); child.stdin.flush()               # the holder releases and exits
            self.assertTrue(entered.wait(30), "the waiter gets in once the holder lets go")
            self.assertEqual(child.wait(30), 0)
        finally:                                                      # a failing step never leaves a holder behind
            try:
                child.communicate(timeout=60)                         # closes its stdin, so the holder's readline ends
            except subprocess.TimeoutExpired:
                child.kill(); child.communicate()
            if thread.is_alive():
                thread.join(60)
            errlog.close()

    def test_this_modules_top_keys_comment_names_both_families(self):
        line = next(l for l in Path(__file__).read_text().splitlines() if l.strip().startswith('"stagesForeign",'))
        self.assertIn("push stage", line + " ", "the TOP_KEYS comment names the push family beside the jobs family")


class ProcessStatsFallback(unittest.TestCase):
    """_process_stats reads VmRSS from /proc/self/status. A platform without /proc gets ru_maxrss, which
    Linux reports in KB and macOS in bytes; on macOS that figure is the LIFETIME PEAK, so since 2026-09-18
    the darwin branch reads the CURRENT size from the Mach kernel's task_info through ctypes, else from a
    rate-limited `ps`, and keeps the peak beside it as rss_peak_kb. This box is Linux: /proc is made to
    fail, and the platform name, the rusage read and the two darwin readers are patched, so every figure
    is exact and no test assumes a Mac, except the one case that meets the real reader and skips anywhere
    else."""

    class _Usage:
        ru_maxrss = 2048 * 1024                              # bytes on darwin, KB on linux

    def setUp(self):
        self._reset()
        self.addCleanup(self._reset)

    @staticmethod
    def _reset():
        km._DARWIN_TASK_INFO.clear()
        km._DARWIN_PS_MEMO.update(t=None, kb=None)
        km._DARWIN_RSS_SAID.clear()

    @staticmethod
    def _ps(stdout):
        return mock.Mock(stdout=stdout, returncode=0)

    def _no_proc(self, platform):
        """/proc failing, sys.platform and ru_maxrss patched: the fallback branch on the named platform."""
        real_open = open

        def no_proc(path, *a, **kw):
            if path == "/proc/self/status":
                raise FileNotFoundError(path)
            return real_open(path, *a, **kw)
        import resource
        stack = contextlib.ExitStack()
        stack.enter_context(mock.patch("builtins.open", side_effect=no_proc))
        stack.enter_context(mock.patch.object(resource, "getrusage", return_value=self._Usage()))
        stack.enter_context(mock.patch.object(sys, "platform", platform))
        return stack

    def test_without_proc_rss_comes_from_ru_maxrss(self):
        # linux without /proc: ru_maxrss in KB as is, the darwin readers never consulted, no peak field;
        # the darwin reader is patched to RAISE (the call is outside every try), so a linux branch that
        # reached it would fail here rather than quietly return a figure
        with self._no_proc("linux"), \
                mock.patch.object(km, "_darwin_current_rss_kb", side_effect=AssertionError("darwin reader on linux")):
            st = km._process_stats()
        self.assertIsInstance(st["rss_kb"], int)
        self.assertEqual(st["rss_kb"], 2048 * 1024, "linux reports ru_maxrss in KB: taken as is")
        self.assertEqual(st["source"], "unavailable")
        self.assertNotIn("rss_peak_kb", st, "the peak field is darwin's; every other platform keeps its shape")
        for k in ("threads", "cpu_s", "pid"):
            self.assertIn(k, st)
        self.assertEqual(st["pid"], os.getpid())

    def test_on_darwin_rss_is_the_current_size_from_task_info_and_the_peak_moves_to_rss_peak_kb(self):
        # the Mach kernel says 300 MiB resident now, ru_maxrss (bytes on darwin) says the peak was 2 MiB: a
        # synthetic pair whose point is which field each figure lands in. Before 2026-09-18 rss_kb was the
        # peak (2048 here) and there was no rss_peak_kb, so a Mac's memory over uptime only ever climbed.
        ps = mock.Mock(side_effect=AssertionError("ps forked with task_info answering"))
        with self._no_proc("darwin"), \
                mock.patch.object(km, "_darwin_task_rss_bytes", return_value=300 * 1024 * 1024), \
                mock.patch.object(km.subprocess, "run", ps):
            st = km._process_stats()
        self.assertEqual(st["rss_kb"], 300 * 1024, "task_info's resident_size, bytes scaled to KB")
        self.assertEqual(st["source"], "task_info")
        self.assertEqual(st["rss_peak_kb"], 2048, "ru_maxrss // 1024: the old rss_kb, under its own name")
        self.assertIsNone(st["rss_anon_kb"]); self.assertIsNone(st["hwm_kb"])
        ps.assert_not_called()
        json.dumps(st)

    def test_on_darwin_a_failing_task_info_falls_to_ps_in_kb(self):
        ps = mock.Mock(return_value=self._ps(" 123456\n"))
        with self._no_proc("darwin"), \
                mock.patch.object(km, "_darwin_task_rss_bytes", side_effect=OSError("task_info: kern_return_t 4")), \
                mock.patch.object(km.subprocess, "run", ps):
            st = km._process_stats()
        self.assertEqual(st["rss_kb"], 123456, "ps -o rss= prints KB on darwin: taken as is")
        self.assertEqual(st["source"], "ps")
        self.assertEqual(st["rss_peak_kb"], 2048)
        ps.assert_called_once()
        args, kwargs = ps.call_args
        self.assertEqual(args[0], ["ps", "-o", "rss=", "-p", str(os.getpid())], "argv only, this process")
        self.assertFalse(kwargs.get("shell"), "no shell")
        self.assertLessEqual(kwargs.get("timeout"), 5, "a bounded run: a hung ps cannot hold the read")

    def test_the_ps_fallback_runs_at_most_once_per_ten_seconds(self):
        # ps is a fork, so the reader memoizes it on the monotonic clock: three reads inside 10 s are one
        # run, and the read at 10 s runs again
        ps = mock.Mock(side_effect=[self._ps("100\n"), self._ps("200\n")])
        with mock.patch.object(km.subprocess, "run", ps), \
                mock.patch.object(km, "_darwin_task_rss_bytes", side_effect=OSError("no ctypes")):
            self.assertEqual(km._darwin_current_rss_kb(now=1000.0), (100, "ps"))
            self.assertEqual(km._darwin_current_rss_kb(now=1005.0), (100, "ps"), "the memo serves the reads inside 10 s")
            self.assertEqual(km._darwin_current_rss_kb(now=1009.99), (100, "ps"))
            self.assertEqual(ps.call_count, 1)
            self.assertEqual(km._darwin_current_rss_kb(now=1010.0), (200, "ps"), "a second run once 10 s have passed")
            self.assertEqual(ps.call_count, 2)

    def test_a_failed_ps_is_not_retried_inside_the_window_and_the_peak_stands_in(self):
        # both current readers down: rss_kb keeps the peak, the way every no-/proc platform reports it, and
        # `source` says so; the failed fork is not retried until the 10 s pass. The clock is patched to a
        # constant so the two reads share one window whatever the box is doing (review round 1: the real
        # clock flaked the one-fork assertion under a stall of 10 s or more)
        ps = mock.Mock(side_effect=km.subprocess.CalledProcessError(1, "ps"))
        with self._no_proc("darwin"), \
                mock.patch.object(km, "_darwin_task_rss_bytes", side_effect=OSError("no ctypes")), \
                mock.patch.object(km.subprocess, "run", ps), \
                mock.patch.object(km.time, "monotonic", return_value=1000.0):
            st1 = km._process_stats()
            st2 = km._process_stats()
        self.assertEqual(ps.call_count, 1, "a failed fork is not retried before 10 s pass")
        for st in (st1, st2):
            self.assertEqual((st["rss_kb"], st["source"], st["rss_peak_kb"]), (2048, "unavailable", 2048),
                             "with no current reader the peak stands in, and source says so")

    def test_a_ps_run_that_fails_after_a_good_one_leaves_its_window_with_no_figure(self):
        # review round 1 (medium): a failing run used to leave the last figure in the memo, so the reader served
        # a stale number as source ps for as long as ps kept failing. A failed window serves None, and the caller
        # keeps the peak under unavailable; the next good run returns to ps
        ps = mock.Mock(side_effect=[self._ps("100\n"), km.subprocess.CalledProcessError(1, "ps"), self._ps("300\n")])
        with mock.patch.object(km.subprocess, "run", ps), \
                mock.patch.object(km, "_darwin_task_rss_bytes", side_effect=OSError("no ctypes")):
            self.assertEqual(km._darwin_current_rss_kb(now=1000.0), (100, "ps"))
            self.assertEqual(km._darwin_current_rss_kb(now=1010.0), (None, None), "the failed run's window has no figure")
            self.assertEqual(km._darwin_current_rss_kb(now=1015.0), (None, None), "and the figure before it is not served")
            self.assertEqual(ps.call_count, 2)
            self.assertEqual(km._darwin_current_rss_kb(now=1020.0), (300, "ps"), "the next good run answers again")

    def test_through_process_stats_a_failed_ps_window_keeps_the_peak_under_unavailable(self):
        ps = mock.Mock(side_effect=[self._ps("100\n"), km.subprocess.CalledProcessError(1, "ps")])
        clock = mock.Mock(return_value=1000.0)
        with self._no_proc("darwin"), \
                mock.patch.object(km, "_darwin_task_rss_bytes", side_effect=OSError("no ctypes")), \
                mock.patch.object(km.subprocess, "run", ps), \
                mock.patch.object(km.time, "monotonic", clock):
            st1 = km._process_stats()
            clock.return_value = 1010.0
            st2 = km._process_stats()
            st3 = km._process_stats()
        self.assertEqual((st1["rss_kb"], st1["source"], st1["rss_peak_kb"]), (100, "ps", 2048))
        for st in (st2, st3):
            self.assertEqual((st["rss_kb"], st["source"], st["rss_peak_kb"]), (2048, "unavailable", 2048),
                             "a failed window: the peak stands in and source says so, never the last ps figure")
        self.assertEqual(ps.call_count, 2)

    def test_a_non_numeric_ps_answer_is_a_failed_run(self):
        # ps exiting 0 with something other than a number (a header, an empty line) is a failed run like any other:
        # the window has no figure and the peak stands in; the answer is never read as a size
        ps = mock.Mock(side_effect=[self._ps("100\n"), self._ps("  RSS\n"), self._ps("\n"), self._ps("300\n")])
        with self._no_proc("darwin"), \
                mock.patch.object(km, "_darwin_task_rss_bytes", side_effect=OSError("no ctypes")), \
                mock.patch.object(km.subprocess, "run", ps):
            self.assertEqual(km._darwin_current_rss_kb(now=1000.0), (100, "ps"))
            self.assertEqual(km._darwin_current_rss_kb(now=1010.0), (None, None), "a header is not a figure")
            self.assertEqual(km._darwin_current_rss_kb(now=1020.0), (None, None), "an empty answer is not a figure")
            with mock.patch.object(km.time, "monotonic", return_value=1025.0):   # inside the empty answer's window
                st = km._process_stats()
            self.assertEqual(km._darwin_current_rss_kb(now=1030.0), (300, "ps"))
        self.assertEqual((st["rss_kb"], st["source"]), (2048, "unavailable"), "the peak stands in for that window")
        self.assertEqual(ps.call_count, 4)

    def test_the_exit_cut_row_never_forks_ps(self):
        # review round 1: on a Mac where task_info fails the dying process forked ps with a 2 s cap inside the
        # 0.5 s the exit's budgets leave. The cut row reads with fork False: the memo's figure while its window
        # is fresh, else the peak, and subprocess.run is never reached (it raises here if it is)
        ps = mock.Mock(side_effect=AssertionError("ps forked at exit"))
        clock = mock.Mock(return_value=1005.0)
        with self._no_proc("darwin"), \
                mock.patch.object(km, "_darwin_task_rss_bytes", side_effect=OSError("no ctypes")), \
                mock.patch.object(km.subprocess, "run", ps), \
                mock.patch.object(km.time, "monotonic", clock):
            cold = km._restart_cut_row({"cutTurns": []}, now=1)
            km._DARWIN_PS_MEMO.update(t=1000.0, kb=555)             # a run answered 5 s ago
            fresh = km._restart_cut_row({"cutTurns": []}, now=2)
            clock.return_value = 1010.0                             # the window has lapsed
            stale = km._restart_cut_row({"cutTurns": []}, now=3)
        ps.assert_not_called()
        self.assertEqual(cold["rssKb"], 2048, "no memo: the peak stands in")
        self.assertEqual(fresh["rssKb"], 555, "a fresh memo is served without a fork")
        self.assertEqual(stale["rssKb"], 2048, "a lapsed memo is not served: the peak, never an old figure")
        self.assertEqual(km._DARWIN_PS_MEMO, {"t": 1000.0, "kb": 555}, "a no-fork read claims no window and writes nothing")

    def test_without_fork_the_reader_serves_a_fresh_memo_only(self):
        ps = mock.Mock(side_effect=AssertionError("forked with fork=False"))
        with mock.patch.object(km.subprocess, "run", ps), \
                mock.patch.object(km, "_darwin_task_rss_bytes", side_effect=OSError("no ctypes")):
            self.assertEqual(km._darwin_current_rss_kb(now=1000.0, fork=False), (None, None), "nothing memoized: None, no fork")
            km._DARWIN_PS_MEMO.update(t=1000.0, kb=100)
            self.assertEqual(km._darwin_current_rss_kb(now=1009.0, fork=False), (100, "ps"))
            self.assertEqual(km._darwin_current_rss_kb(now=1010.0, fork=False), (None, None), "the window lapsed: None, no fork")
        ps.assert_not_called()

    def test_the_boot_row_and_every_other_caller_still_fork(self):
        # only the cut row passes fork False; the boot row is not time-critical and reads like GET /perf and the
        # kernel sample do, so a Mac on its ps fallback gets a figure there. The clock is a constant so the two
        # reads share one window whatever the box is doing (review round 2: the real clock flaked the one-fork
        # assertion under a stall of 10 s or more, the shape round 1 fixed in the failed-window case above)
        ps = mock.Mock(return_value=self._ps("777\n"))
        with self._no_proc("darwin"), \
                mock.patch.object(km, "_darwin_task_rss_bytes", side_effect=OSError("no ctypes")), \
                mock.patch.object(km.subprocess, "run", ps), \
                mock.patch.object(km.time, "monotonic", return_value=1000.0):
            self.assertEqual(km._kernel_process_sample()["rssKb"], 777, "the boot row's read, the default")
            self.assertEqual(km._process_stats()["rss_kb"], 777)
        ps.assert_called_once()

    def test_each_readers_first_fall_is_said_once_on_stderr(self):
        # review round 1: neither fallback left a log line, so nothing anywhere marked that a reader was down.
        # One line per process at the first fall of each reader (the heap gauges' and the gc hook's pattern);
        # later falls are silent, and a working ps says nothing about itself
        ticks = iter(range(1000, 100000, 10))
        ps = mock.Mock(side_effect=km.subprocess.CalledProcessError(1, "ps"))
        err = io.StringIO()
        with self._no_proc("darwin"), \
                mock.patch.object(km, "_darwin_task_rss_bytes", side_effect=OSError("task_info: kern_return_t 4")), \
                mock.patch.object(km.subprocess, "run", ps), \
                mock.patch.object(km.time, "monotonic", lambda: float(next(ticks))), redirect_stderr(err):
            for _ in range(3):
                km._process_stats()
        self.assertEqual(ps.call_count, 3, "three windows, three falls")
        lines = err.getvalue().splitlines()
        self.assertEqual(len(lines), 2, lines)
        self.assertTrue(lines[0].startswith("perf: process.rss_kb: task_info unavailable: OSError: task_info: kern_return_t 4; "), lines[0])
        self.assertTrue(lines[1].startswith("perf: process.rss_kb: ps unavailable: CalledProcessError: "), lines[1])
        self._reset()
        err = io.StringIO()
        with self._no_proc("darwin"), \
                mock.patch.object(km, "_darwin_task_rss_bytes", side_effect=OSError("no ctypes")), \
                mock.patch.object(km.subprocess, "run", mock.Mock(return_value=self._ps("100\n"))), redirect_stderr(err):
            self.assertEqual(km._process_stats()["source"], "ps")
        self.assertEqual(err.getvalue().count("\n"), 1, "task_info's fall alone; a working ps is not news")
        self.assertIn("task_info unavailable", err.getvalue())

    def test_a_reader_arriving_during_a_claimed_window_serves_the_memo_and_does_not_fork(self):
        # review round 1 (a free-threaded-only race): the window is claimed under the lock BEFORE the fork, so a
        # second reader that arrives while ps is out serves the memo (the figure before, or None) rather than
        # forking too; the lock is not held across the run (a GET /perf handler must not queue behind a 2 s
        # fork). Simulated from inside the run itself: the stand-in ps reads the memo the way a peer thread would.
        # Review round 2: the memo is a stand-in that asserts the lock is held at every read and write (the check,
        # the claim, the write), so the case is red with the lock blocks removed; the behaviour assertions alone
        # passed without the lock, since the stand-in ps runs on the test's own thread
        inner = []
        test = self

        class _LockedMemo(dict):
            def __getitem__(self, key):
                test.assertTrue(km._DARWIN_PS_LOCK.locked(), "memo read outside the lock: %s" % key)
                return dict.__getitem__(self, key)

            def __setitem__(self, key, value):
                test.assertTrue(km._DARWIN_PS_LOCK.locked(), "memo write outside the lock: %s" % key)
                dict.__setitem__(self, key, value)

        def slow_ps(*a, **kw):
            self.assertTrue(km._DARWIN_PS_LOCK.acquire(blocking=False), "the lock is not held across the run")
            km._DARWIN_PS_LOCK.release()
            inner.append(km._darwin_ps_rss_kb(now=1000.5))       # a peer arriving mid-run
            return self._ps("100\n")
        ps = mock.Mock(side_effect=slow_ps)
        with mock.patch.object(km.subprocess, "run", ps), \
                mock.patch.object(km, "_DARWIN_PS_MEMO", _LockedMemo(t=None, kb=None)):
            self.assertEqual(km._darwin_ps_rss_kb(now=1000.0), 100)
            self.assertEqual(km._darwin_ps_rss_kb(now=1001.0), 100)
        self.assertEqual(ps.call_count, 1, "one fork for the window, the peer's read included")
        self.assertEqual(inner, [None], "the peer served the memo as it stood (nothing yet), not a second fork")

    @unittest.skipUnless(sys.platform == "darwin", "the real Mach reader answers on a Mac only")
    def test_on_a_real_mac_the_task_info_reader_answers_with_a_plausible_current_size(self):
        # the one case that meets the REAL reader, with no patches (the weekly macOS cell, or a dispatch); setUp
        # cleared the cached handle so the setup runs here too. Every other assertion in this module accepts ps or
        # unavailable and rss_kb >= 0, so a ctypes path failing silently, or a wrong struct layout answering a
        # garbage figure, passed the Mac cell before this (review round 1). The peak is read AFTER the call, so a
        # page touched between the two reads cannot flake the bound (XNU fills ru_maxrss from the same struct);
        # ps is a bounded argv run, no shell; the second call after a 50 MB allocate-and-free proves the cached
        # handle's second trap does not raise
        import resource
        import subprocess
        st = km._process_stats()
        peak_after = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024)
        self.assertEqual(st["source"], "task_info")
        self.assertGreater(st["rss_kb"], 0)
        self.assertGreater(st["rss_peak_kb"], 0)
        self.assertLessEqual(st["rss_kb"], peak_after, "the current size is at or under the peak read after it")
        ps_kb = int(subprocess.run(["ps", "-o", "rss=", "-p", str(os.getpid())], capture_output=True, text=True,
                                   timeout=5, check=True).stdout.strip())
        self.assertGreaterEqual(st["rss_kb"] * 2, ps_kb, "within a factor of 2 of ps (rss %d KB, ps %d KB)" % (st["rss_kb"], ps_kb))
        self.assertLessEqual(st["rss_kb"], ps_kb * 2, "within a factor of 2 of ps (rss %d KB, ps %d KB)" % (st["rss_kb"], ps_kb))
        blob = bytearray(50 * 1024 * 1024)
        blob[::4096] = b"x" * len(blob[::4096])                 # touch every page so the allocation is resident
        del blob
        st2 = km._process_stats()
        self.assertEqual(st2["source"], "task_info", "the handle is resolved once; the second trap must not raise")
        self.assertGreater(st2["rss_kb"], 0)

    @staticmethod
    def _task_info_proto():
        """The header's signature as a ctypes prototype: kern_return_t task_info(task_name_t, task_flavor_t,
        task_info_t, mach_msg_type_number_t *). A stand-in built over it is a real function pointer, so the
        reader's call goes through ctypes marshalling under its declared restype and argtypes (a wrong argtypes
        entry raises ArgumentError here, where a plain Python function accepted anything: review round 1)."""
        import ctypes
        return ctypes.CFUNCTYPE(ctypes.c_int32, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32))

    def _lib(self, kr, resident, seen, task_self=0x103):
        """A stand-in libSystem: task_info over the prototype writing `resident` through the out pointer and
        returning `kr`; mach_task_self a c_uint32 function pointer, or absent (None) so the reader falls to the
        mach_task_self_ variable."""
        import ctypes, types

        def task_info(task, flavor, info_p, count_p):
            seen.update(task=task, flavor=flavor, count=count_p.contents.value)
            ctypes.cast(info_p, ctypes.POINTER(km._MachTaskBasicInfo)).contents.resident_size = resident
            return kr
        lib = types.SimpleNamespace(task_info=self._task_info_proto()(task_info))
        if task_self is not None:
            lib.mach_task_self = ctypes.CFUNCTYPE(ctypes.c_uint32)(lambda: task_self)
        return lib

    def test_the_task_info_reader_reads_resident_size_from_the_mach_struct(self):
        # the ctypes plumbing against a stand-in libSystem whose functions are real function pointers (CFUNCTYPE
        # over the header's signature, so the arguments are marshalled under the reader's argtypes): the task
        # port, the flavor (MACH_TASK_BASIC_INFO, 20), the count (MACH_TASK_BASIC_INFO_COUNT, 12 natural_t for
        # the 48-byte struct), the struct written through the out pointer and read back in bytes, the setup done
        # once per process, and a non-zero kern_return_t raised rather than read as a size
        import ctypes
        self.assertEqual(ctypes.sizeof(km._MachTaskBasicInfo), 48, "struct mach_task_basic_info")
        seen = {}
        factory = mock.Mock(return_value=self._lib(0, 77 * 1024 * 1024, seen))
        with mock.patch.object(km, "_darwin_libsystem", factory):
            self.assertEqual(km._darwin_task_rss_bytes(), 77 * 1024 * 1024)
            self.assertEqual(km._darwin_task_rss_bytes(), 77 * 1024 * 1024)
        factory.assert_called_once()                         # the handle and the port are resolved once
        self.assertEqual((seen["task"], seen["flavor"], seen["count"]), (0x103, 20, 12))
        fn, task = km._DARWIN_TASK_INFO[0]
        self.assertEqual(fn.argtypes, [ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32)],
                         "the header's argument types, set on the function pointer")
        self.assertIs(fn.restype, ctypes.c_int32, "kern_return_t")
        self._reset()
        with mock.patch.object(km, "_darwin_libsystem", return_value=self._lib(4, 1, {})):   # KERN_INVALID_ARGUMENT
            with self.assertRaises(OSError):
                km._darwin_task_rss_bytes()

    def test_the_task_port_comes_from_the_mach_task_self_variable_when_the_function_is_absent(self):
        # newer SDKs make mach_task_self() a macro over the variable mach_task_self_, so a library with no such
        # function symbol (ctypes raises AttributeError) has the port read with c_uint32.in_dll(lib, "mach_task_self_")
        import ctypes
        seen = {}
        lib = self._lib(0, 5 * 1024 * 1024, seen, task_self=None)
        in_dll = mock.Mock(return_value=ctypes.c_uint32(0x207))
        with mock.patch.object(km, "_darwin_libsystem", return_value=lib), \
                mock.patch.object(ctypes.c_uint32, "in_dll", in_dll):
            self.assertEqual(km._darwin_task_rss_bytes(), 5 * 1024 * 1024)
        in_dll.assert_called_once_with(lib, "mach_task_self_")
        self.assertEqual(seen["task"], 0x207, "the variable's value is the task port")
        self.assertEqual(km._DARWIN_TASK_INFO[0][1], 0x207)

    def test_with_proc_present_the_fallback_is_not_used(self):
        import resource
        with mock.patch.object(resource, "getrusage", side_effect=AssertionError("fallback taken")), \
                mock.patch.object(km, "_darwin_current_rss_kb", side_effect=AssertionError("darwin reader with /proc")):
            try:
                with open("/proc/self/status"):
                    pass
            except OSError:
                self.skipTest("no /proc on this platform")
            st = km._process_stats()
        self.assertGreater(st["rss_kb"], 0, "VmRSS read from /proc")
        self.assertEqual(st["source"], "proc")
        self.assertNotIn("rss_peak_kb", st, "linux's block is unchanged")


class WakeCounting(unittest.TestCase):
    """_pusher_wake is a threading.Event whose set() counts: every existing call site — including the
    bound-method callbacks the backends hold — counts a wake without being touched."""

    def test_the_pusher_wake_counts_sets(self):
        self.assertIsInstance(km._pusher_wake, threading.Event)
        self.assertIsInstance(km._pusher_wake, km._CountedEvent)
        was_set = km._pusher_wake.is_set()
        before = km._PERF_STATS.snapshot()["pusher"]["wakes"]
        km._pusher_wake.set()
        cb = km._pusher_wake.set                             # the shape the backends are handed (push=_pusher_wake.set)
        cb()
        self.assertTrue(km._pusher_wake.is_set())
        self.assertEqual(km._PERF_STATS.snapshot()["pusher"]["wakes"], before + 2)
        if not was_set:
            km._pusher_wake.clear()

    def test_wake_helpers_still_set_the_event(self):
        km._pusher_wake.clear()
        km._push_soon()
        self.assertTrue(km._pusher_wake.is_set())
        km._pusher_wake.clear()

    def test_the_producer_wake_counts_sets_under_judge_and_classifies_the_wait(self):
        # the producer's twin (P4 of the judge perf plan): every _producer_wake.set() lands in judge.wakes,
        # and the loop's wait outcome lands in wakes_event / wakes_backstop through judge_wake_kind
        self.assertIsInstance(km._producer_wake, km._CountedEvent)
        was_set = km._producer_wake.is_set()
        before = km._PERF_STATS.snapshot()["judge"]
        km._producer_wake.set(); km._producer_wake.set(); km._producer_wake.set()
        self.assertTrue(km._producer_wake.is_set())
        km._PERF_STATS.judge_wake_kind(True); km._PERF_STATS.judge_wake_kind(False)
        after = km._PERF_STATS.snapshot()["judge"]
        self.assertEqual(after["wakes"] - before["wakes"], 3)
        self.assertEqual((after["wakes_event"] - before["wakes_event"], after["wakes_backstop"] - before["wakes_backstop"]), (1, 1))
        if not was_set:
            km._producer_wake.clear()

    def test_the_producer_wake_counts_at_call_time_and_sets_before_counting(self):
        # the counter is resolved when set() runs, not captured at import: an instance patch on the
        # collector sees every set; and the flag is set BEFORE the count, so a counter that raises never
        # loses a wake
        was_set = km._producer_wake.is_set()
        km._producer_wake.clear()
        seen = []
        km._PERF_STATS.judge_wake = lambda: seen.append(1)
        try:
            km._producer_wake.set()
            self.assertEqual(seen, [1], "the patched collector saw the set")
            km._producer_wake.clear()

            def boom():
                raise RuntimeError("counter down")
            km._PERF_STATS.judge_wake = boom
            with self.assertRaises(RuntimeError):
                km._producer_wake.set()
            self.assertTrue(km._producer_wake.is_set(), "the wake landed before the counter raised")
        finally:
            del km._PERF_STATS.judge_wake
            if was_set:
                km._producer_wake.set()
            else:
                km._producer_wake.clear()


class PerfLogToggle(unittest.TestCase):
    """_perf() writes only when the switch is on, and the switch flips at runtime."""

    def setUp(self):
        self.saved = km._PERF
        km._set_perf_log(False)

    def tearDown(self):
        km._set_perf_log(self.saved)

    def test_off_writes_nothing_on_writes_one_line(self):
        buf = io.StringIO()
        with redirect_stderr(buf):
            km._perf("probe", b=2, a=1)
        self.assertEqual(buf.getvalue(), "")
        self.assertTrue(km._set_perf_log(True))
        buf = io.StringIO()
        with redirect_stderr(buf):
            km._perf("probe", b=2, a=1)
        self.assertEqual(buf.getvalue(), "romp-perf probe a=1 b=2\n")
        km._set_perf_log(False)
        buf = io.StringIO()
        with redirect_stderr(buf):
            km._perf("probe", b=2, a=1)
        self.assertEqual(buf.getvalue(), "", "off again: nothing")

    def test_the_off_path_reads_one_module_global(self):
        src = inspect.getsource(km._perf)
        self.assertIn("if not _PERF:\n        return", src, "the hot path stays a name lookup and a return")


class GoalIoCounters(unittest.TestCase):
    """judge.load_goals / save_goals count calls and disk writes; the kernel reads them via goal_io_stats."""

    def setUp(self):
        self.jd = km.jd
        self.jd.GOALDIR.mkdir(parents=True, exist_ok=True)
        self.addCleanup(self._clean)

    def _clean(self):
        for p in (self.jd.GOALDIR / (GOAL_SID + ".json"), self.jd.STATE / "overrides" / (GOAL_SID + ".jsonl")):
            try:
                p.unlink()
            except OSError:
                pass

    def test_loads_saves_and_writes(self):
        before = self.jd.goal_io_stats()
        store = self.jd.load_goals(GOAL_SID)                 # no file yet: a fresh store, still one load
        after = self.jd.goal_io_stats()
        self.assertEqual(after["loads"], before["loads"] + 1)
        self.jd.save_goals(GOAL_SID, store)                  # the first publish writes the file
        after = self.jd.goal_io_stats()
        self.assertEqual(after["saves"], before["saves"] + 1)
        self.assertEqual(after["writes"], before["writes"] + 1)
        store = self.jd.load_goals(GOAL_SID)
        self.jd.save_goals(GOAL_SID, store)                  # byte-identical: a save, not a write
        after2 = self.jd.goal_io_stats()
        self.assertEqual(after2["saves"], after["saves"] + 1)
        self.assertEqual(after2["writes"], after["writes"], "the no-op republish skip is visible as saves without writes")
        self.assertGreater(after2["noop_hash_ms"], after["noop_hash_ms"],
                           "the no-op check's serialization is timed (the cost a conditional tail save would remove)")
        self.assertEqual(km._PERF_STATS.snapshot()["goals"], after2, "the kernel's snapshot carries the judge counters")
        # the no-op check's disk-side memo: the first publish seeded it from its own temp, so the check
        # above was a hit; a foreign rewrite of the file is a miss
        self.assertEqual(after2["disk_seeds"], before["disk_seeds"] + 1)
        self.assertEqual(after2["disk_hits"], before["disk_hits"] + 1)
        self.assertEqual(after2["disk_misses"], before["disk_misses"])
        p = self.jd.GOALDIR / (GOAL_SID + ".json")
        tmp = p.with_suffix(".json.foreign")
        tmp.write_text(p.read_text())
        st = os.stat(p)
        os.utime(tmp, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000_000))
        os.replace(tmp, p)
        self.jd.save_goals(GOAL_SID, store)
        after3 = self.jd.goal_io_stats()
        self.assertEqual(after3["disk_misses"], after2["disk_misses"] + 1, "a new file identity is parsed once")
        self.assertEqual(after3["writes"], after2["writes"], "same content under a new identity: still no write")

    def test_the_getter_returns_a_copy(self):
        d = self.jd.goal_io_stats()
        d["loads"] = -1
        self.assertNotEqual(self.jd.goal_io_stats()["loads"], -1)

    def test_the_reference_doc_describes_memos_and_routes_the_pushers_loads_there(self):
        # docs/reference.md read `goals.loads` as every store read; the pusher's loads moved to the shared cache
        # with this PR, so the doc names the memos section and sends the reader there (review find, 2026-09-08)
        doc = Path(HERE).parent.joinpath("docs", "reference.md").read_text()
        self.assertIn("- `memos`:", doc)
        for k in ("`pass`", "`shared`", "`chain`", "`intrMarks`", "`statesOverlay`", "`deadWait`"):
            self.assertIn(k, doc)
        self.assertIn("`memos.shared`", doc)
        self.assertIn("- `heap`:", doc, "the heap block is a documented top-level block (tests/test_perf_heap_block.py pins its keys)")

    def test_the_reference_doc_names_the_shared_memos_by_their_camelcase_keys(self):
        # the memo keys upstream also reports are spelled one way in GET /perf and in the doc (bgTops, liftGate,
        # intrMarks, statesOverlay, chatMergeSets, chatPostal, chatLedger, chatFoldTasks); the older snake_case
        # spellings of the same memos must not survive in the reference as backticked names
        doc = Path(HERE).parent.joinpath("docs", "reference.md").read_text()
        for k in ("bgTops", "liftGate", "intrMarks", "statesOverlay", "chatMergeSets", "chatPostal", "chatLedger", "chatFoldTasks"):
            self.assertIn("`%s`" % k, doc, k)
            snake = re.sub(r"[A-Z]", lambda m: "_" + m.group(0).lower(), k)   # the retired spelling of the same memo
            self.assertNotIn("`%s`" % snake, doc, "the retired spelling of a shared memo: %s" % snake)

    def test_the_pushers_shared_loads_count_under_memos_shared_not_under_goals_loads(self):
        # `goals.loads` is the writer's loader alone; the pusher's read-only loads ride load_goals_shared and
        # show under memos.shared (review find, 2026-09-08: nine pusher sites left `loads` with the move to the
        # shared cache, and the doc still read it as every store read). A fill is a miss, a re-read a hit.
        self.jd.save_goals(GOAL_SID, self.jd.load_goals(GOAL_SID))
        before, snap0 = self.jd.goal_io_stats(), km._PERF_STATS.snapshot()["memos"]["shared"]
        self.jd.load_goals_shared(GOAL_SID)
        self.jd.load_goals_shared(GOAL_SID)
        after, snap = self.jd.goal_io_stats(), km._PERF_STATS.snapshot()["memos"]["shared"]
        self.assertEqual(after["loads"], before["loads"], "two shared loads: no writer-side load counted")
        self.assertEqual((snap["miss"] - snap0["miss"], snap["hit"] - snap0["hit"]), (1, 1),
                         "...the fill and the hit are the shared cache's, on the snapshot")


class JudgeCpu(unittest.TestCase):
    """The judge's CPU is attributed from two places: the tier threads (_run_tier) and every future the
    tiers submit to judge.py's pools (_TimedPool, bound to the module's ThreadPoolExecutor name). The workers'
    share reaches the kernel's LIVE counters as each future ends, through the sink the kernel installs at load
    (jd.set_worker_cpu_sink(_PERF_STATS.judge_worker_cpu)), so a live read of the stats dict and a snapshot()
    read agree and a delta may take either, on the collector that holds the sink (a served block carries
    cpu_ms_workers exactly then, review round 1, 2026-09-19); judge.py's own counter (judge_worker_cpu_ms) stays for the serve
    child, whose module object no kernel ever loads. Until 2026-09-18 snapshot() added that module counter to
    its COPY at read time and the live dict never carried it: two readings of one key disagreed by the whole
    total, and a delta from one of each was wrong (tests/test_judges_process.py paid, f5ba16832)."""

    def _arm(self, stats):
        """Point judge.py's sink at `stats` for this test, recording every delta it is handed. judge.py is one module
        object for every kernel a test process loads and the LAST load holds the sink, so a test that asserts on its
        own kernel's counters arms them itself; the previous sink comes back at cleanup. The recording wrapper is laid
        over judge_worker_cpu ON THE INSTANCE (the class method stays, the _HttpWatch shape) BEFORE the arming, so the
        collector's own road (arm_judge_worker_sink, which opens cpu_ms_workers at 0.0 as the kernel's load does)
        installs the wrapper itself and holds_judge_worker_sink stays true under the harness: a wrapper installed
        beside the collector's method would read as a displacement and the served block would drop the key (review
        round 1, 2026-09-19: presence follows who holds the sink, and a closure over the method is not the method)."""
        jd = km.jd
        received = []
        real = km._PerfStats.judge_worker_cpu

        def sink(ms):
            received.append(ms)
            real(stats, ms)
        stats.judge_worker_cpu = sink
        self.addCleanup(lambda: stats.__dict__.pop("judge_worker_cpu", None))   # the instance attribute goes; the method shows again
        prev = stats.arm_judge_worker_sink()
        self.addCleanup(jd.set_worker_cpu_sink, prev)
        return received

    @staticmethod
    def _live(stats):
        with stats.lock:
            return dict(stats.judge)

    def test_pool_workers_account_their_cpu(self):
        jd = km.jd
        self.assertTrue(issubclass(jd.ThreadPoolExecutor, concurrent.futures.ThreadPoolExecutor),
                        "every pool in judge.py is a real executor that also accounts")
        received = self._arm(km._PERF_STATS)
        before = jd.judge_worker_cpu_ms()
        live0 = self._live(km._PERF_STATS)
        with jd.ThreadPoolExecutor(max_workers=2) as ex:
            self.assertEqual(ex.submit(lambda a, b=1: a + b, 2, b=3).result(), 5, "args and kwargs pass through")
            ex.submit(_burn_cpu, 0.005).result()
        grew = jd.judge_worker_cpu_ms() - before
        self.assertGreaterEqual(grew, 4.0, "about 5 ms of a worker's CPU landed")
        self.assertLess(grew, 500.0)
        self.assertAlmostEqual(sum(received), grew, places=6, msg="the sink is handed the same deltas the module counter takes")
        snap = km._PERF_STATS.snapshot()["judge"]
        self.assertAlmostEqual(snap["cpu_ms_workers"] - live0["cpu_ms_workers"], sum(received), places=6,
                               msg="the snapshot's cpu_ms_workers is what the sink received, copied from the live dict")
        self.assertAlmostEqual(snap["cpu_ms_sum"] - live0["cpu_ms_sum"], sum(received), places=6,
                               msg="and cpu_ms_sum grew by the same: the workers' share is in the sum at write time")

    def test_a_live_read_and_a_snapshot_agree_on_cpu_ms_sum_after_pool_work(self):
        """(i) One source. A private collector takes the sink; after real pool work its live dict and its snapshot carry
        the same cpu_ms_sum and cpu_ms_workers, and the snapshot reads NOTHING from judge.py's counter (that counter is
        stubbed to a billion for one read and the snapshot does not move). Red before 2026-09-18 on the first
        assertion: the snapshot added judge_worker_cpu_ms() to its copy, the live dict had no workers' share."""
        jd = km.jd
        st = km._PerfStats()
        received = self._arm(st)
        with jd.ThreadPoolExecutor(max_workers=1) as ex:
            ex.submit(_burn_cpu, 0.005).result()
        self.assertGreaterEqual(sum(received), 4.0, "about 5 ms of a worker's CPU went through the sink")
        live = self._live(st)
        snap = st.snapshot()["judge"]
        self.assertEqual(snap["cpu_ms_sum"], live["cpu_ms_sum"], "the snapshot copies the live sum and adds nothing at read time")
        self.assertEqual(snap["cpu_ms_workers"], live["cpu_ms_workers"], "the workers' share is a live counter, copied")
        self.assertAlmostEqual(live["cpu_ms_workers"], sum(received), places=6)
        self.assertAlmostEqual(live["cpu_ms_sum"], sum(received), places=6, msg="no tier ran: the sum is the workers' share alone")
        with mock.patch.object(jd, "judge_worker_cpu_ms", return_value=1e9):
            again = st.snapshot()["judge"]
        self.assertEqual(again["cpu_ms_sum"], live["cpu_ms_sum"], "judge.py's module counter is not an input to the snapshot")
        self.assertEqual(again["cpu_ms_workers"], live["cpu_ms_workers"])

    def test_with_no_sink_the_module_counter_alone_accumulates_and_the_kernels_dict_stands_still(self):
        """(iii) The sink is optional: judge.py with none set (the serve child's process, a standalone romp-judge run)
        keeps its own counter, which _serve_pass reads for workerCpuMs, and writes to no kernel."""
        jd = km.jd
        prev = jd.set_worker_cpu_sink(None)
        self.addCleanup(jd.set_worker_cpu_sink, prev)
        live0 = self._live(km._PERF_STATS)
        before = jd.judge_worker_cpu_ms()
        with jd.ThreadPoolExecutor(max_workers=1) as ex:
            ex.submit(_burn_cpu, 0.005).result()
        self.assertGreaterEqual(jd.judge_worker_cpu_ms() - before, 4.0, "the module counter took the worker's CPU")
        live1 = self._live(km._PERF_STATS)
        self.assertEqual((live1["cpu_ms_workers"], live1["cpu_ms_sum"]), (live0["cpu_ms_workers"], live0["cpu_ms_sum"]),
                         "no sink, no write to the kernel's counters")

    def test_an_unarmed_collector_serves_no_workers_key_and_the_arming_opens_it_at_a_genuine_zero(self):
        """(ii) The review ruling on the write-time fold (2026-09-18): an unarmed sink must be distinguishable from a
        genuine zero. A collector nothing armed has no cpu_ms_workers in its live dict or its snapshot (red before: the
        constructor opened the key at 0.0, the reading a process that never armed the sink would have served as fact);
        arm_judge_worker_sink opens it at 0.0 with no pool future yet run, a genuine zero, and installs this collector's
        writer; pool work then moves it; and a write through judge_worker_cpu on a collector that does not hold the sink
        is a record, not a report: the live dict takes the key and the served block, what the user reads, drops it while
        its cpu_ms_sum carries the write (review round 2, 2026-09-19: this cell had asserted the live dict alone and
        called the write the evidence of reporting). cpu_ms_sum is served in every case: the tier threads' and the child's
        CPU."""
        jd = km.jd
        st = km._PerfStats()
        self.assertNotIn("cpu_ms_workers", self._live(st), "unarmed: no key in the live dict")
        self.assertNotIn("cpu_ms_workers", st.snapshot()["judge"], "the snapshot copies the live dict: no key, not a zero")
        self.assertEqual(st.snapshot()["judge"]["cpu_ms_sum"], 0.0, "cpu_ms_sum is served regardless")
        prev = st.arm_judge_worker_sink()
        self.addCleanup(jd.set_worker_cpu_sink, prev)
        self.assertEqual(self._live(st).get("cpu_ms_workers"), 0.0, "armed, no future yet: a genuine zero, present")
        self.assertEqual(st.snapshot()["judge"]["cpu_ms_workers"], 0.0)
        installed = jd.set_worker_cpu_sink(None)
        self.assertIs(getattr(installed, "__self__", None), st, "the arming installed this collector's writer: %r" % (installed,))
        self.assertEqual(installed.__name__, "judge_worker_cpu")
        st.arm_judge_worker_sink()
        with jd.ThreadPoolExecutor(max_workers=1) as ex:
            ex.submit(_burn_cpu, 0.005).result()
        snap = st.snapshot()["judge"]
        self.assertGreaterEqual(snap["cpu_ms_workers"], 4.0, "the value, once a future ran: %r" % snap["cpu_ms_workers"])
        self.assertEqual(snap["cpu_ms_sum"], snap["cpu_ms_workers"], "no tier ran: the sum is the workers' share")
        bare = km._PerfStats()
        bare.judge_worker_cpu(2.5)
        served = bare.snapshot()["judge"]
        self.assertNotIn("cpu_ms_workers", served, "a write on a collector that does not hold the sink is a record, not a "
                         "report: the served block drops the key (review round 2, 2026-09-19)")
        self.assertEqual(served["cpu_ms_sum"], 2.5, "while cpu_ms_sum carries the write")
        self.assertEqual(self._live(bare).get("cpu_ms_workers"), 2.5, "the live dict holds the record")

    def test_the_reference_and_the_docstring_say_the_key_is_absent_until_the_sink_is_armed(self):
        """(e) The two places PR 788 wrote its interim one-source sentence, the _PerfStats docstring's judge entry and
        docs/reference.md's judge bullet, now describe the write-time fold and the unarmed shape: the arming creates
        cpu_ms_workers, a block without it is from a collector nothing armed, and neither still says a delta comes from
        one source, never one of each (the review ruling, 2026-09-18)."""
        doc = km._PerfStats.__doc__ or ""
        ref = Path(HERE).parent.joinpath("docs", "reference.md").read_text(encoding="utf-8")
        for name, text in (("the _PerfStats docstring", doc), ("docs/reference.md", ref)):
            text = re.sub(r"\s+", " ", text)      # a re-wrap is not a change of meaning (review round 2, 2026-09-19: the gap
            #                                         bound below counted the docstring's indentation, 56 of its 60)
            self.assertRegex(text, r"the arming is what creates\s+`?cpu_ms_workers`?", name)
            self.assertRegex(text, r"straddles the displacement", "%s carries the hedge: a keyless block cannot say how much of a "
                             "window's figure is the workers' (review round 2, 2026-09-19)" % name)
            self.assertRegex(text, r"collector nothing armed", name)
            self.assertRegex(text, r"workers' share not\s+reported", "%s names the CLI's wording for the absent key" % name)
            self.assertNotRegex(text, r"one source,\s+never\s+one\s+of\s+each", "%s: PR 788's interim sentence is gone" % name)
            self.assertRegex(text, r"later kernel load[\s\S]{0,60}displaced", "%s names the displaced collector as a keyless shape "
                             "(review round 1, 2026-09-19: it was listed as one and served the key frozen)" % name)
            self.assertNotRegex(text, r"earlier kernel load\s+in a test process after a later load re-armed",
                                "%s: the sentence round 1 found false is gone" % name)
        # the two CLI copies of the same predicate, bin/romp's comment over the "not reported" note and the bats test's,
        # read with their comment markers stripped and whitespace normalised: each names the displaced collector and
        # carries the hedge, and neither says the share is absent from the figure (review round 2, 2026-09-19: bin/romp's
        # copy had dropped the hedge its siblings carry, and the bats copy still stated the closed rule from before round 1)
        top = Path(HERE).parent
        for name, path in (("bin/romp", top / "bin" / "romp"), ("tests/romp-perf.bats", top / "tests" / "romp-perf.bats")):
            text = re.sub(r"\s+", " ", re.sub(r"(?m)^[ \t]*#", " ", path.read_text(encoding="utf-8")))
            self.assertRegex(text, r"later kernel load[\s\S]{0,60}displaced", "%s names the displaced collector" % name)
            self.assertRegex(text, r"not reported", name)
            self.assertRegex(text, r"straddles", "%s carries the hedge: a window that straddles the displacement carries the share" % name)
            self.assertNotRegex(text, r"share is not in the window's figure", "%s: the share may be in the figure; the note says the "
                                "block cannot split it" % name)
            self.assertNotRegex(text, r"has no pool workers' share in it", "%s: the closed rule from before round 1 is gone" % name)

    def test_judge_worker_cpus_docstring_states_a_write_as_a_record_and_presence_by_who_holds_the_sink(self):
        """The writer's own docstring follows the serving rule round 1 installed (review round 2, 2026-09-19: it still said a
        write was itself the evidence that the share is reported, while snapshot() pops the key from any collector that
        does not hold the sink, so a wrapper installed beside the method records and reports nothing, the opposite of the
        promise). Whitespace is normalised first, so a re-wrap cannot red it. Kept apart from the class-docstring pin above
        on purpose: this method's docstring carries none of that text."""
        doc = re.sub(r"\s+", " ", km._PerfStats.judge_worker_cpu.__doc__ or "")
        self.assertNotRegex(doc, r"write is itself the evidence", "the retired rule is gone")
        self.assertRegex(doc, r"a served block carries the key only while this collector is the sink judge\.py holds",
                         "the serving rule, in the writer's own words")
        self.assertRegex(doc, r"holds_judge_worker_sink", "and it names the question snapshot() asks")
        self.assertRegex(doc, r"RECORD, not a report", "a write is a record")

    def test_judge_pys_pool_site_line_is_the_ast_walks_enumeration(self):
        """kernel/judge.py carries ONE machine-readable line under the _TimedPool rebind, `# POOL SITES: run_pass -> ... |
        main only -> ...`, and this test derives that line from the file and compares (review round 2, 2026-09-19: PR
        792's rationale had enumerated the sites by hand, ten where the file has eleven, in place of a parenthetical
        that claimed a check and was false; a written list is the same artifact with more words, so the list is derived
        here and a new site reds this test until the line names it). THE PREDICATE. A pool site is an ast.Call whose
        callee is the bare name ThreadPoolExecutor or _TimedPool: after the rebind every such construction builds
        _TimedPool, whose submit wrapper feeds the sink. An attribute-form construction (concurrent.futures.
        ThreadPoolExecutor(...)) would bypass the rebind and is asserted absent. A site is named by the module-level def
        whose span holds it, in source order, one name per construction. run_pass REACHES a site when a walk from run_pass
        over the Name loads of module-level functions inside each function's body reaches its owner: an over-approximation
        of calls (a function passed as a value counts as reached), so "main only" is what the walk proves: no name road
        from run_pass at all, and main the one module-level function that reaches the owner. Every owner is reached from
        main (its subcommand dispatch)."""
        import ast
        path = Path(HERE).parent / "kernel" / "judge.py"
        src = path.read_text(encoding="utf-8")
        tree = ast.parse(src)
        top = {n.name: n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}

        def owner_of(lineno):
            for name, node in top.items():
                if node.lineno <= lineno <= node.end_lineno:
                    return name
            return "<module>"
        sites, bypass = [], []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            f = node.func
            if isinstance(f, ast.Name) and f.id in ("ThreadPoolExecutor", "_TimedPool"):
                sites.append((node.lineno, owner_of(node.lineno)))
            elif isinstance(f, ast.Attribute) and f.attr in ("ThreadPoolExecutor", "_TimedPool"):
                bypass.append((node.lineno, owner_of(node.lineno)))
        sites.sort()
        self.assertEqual(bypass, [], "a pool built past the rebind would feed no sink: %r" % (bypass,))
        self.assertNotIn("<module>", [o for _, o in sites], "every pool site sits inside a module-level def: %r" % (sites,))
        refs = {}
        for name, node in top.items():
            refs[name] = {n.id for n in ast.walk(node) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id in top}

        def reach(start):
            seen, stack = set(), [start]
            while stack:
                x = stack.pop()
                if x not in seen:
                    seen.add(x); stack.extend(refs.get(x, ()))
            return seen
        from_pass, from_main = reach("run_pass"), reach("main")
        owners = [o for _, o in sites]
        self.assertEqual([o for o in owners if o not in from_main], [], "every pool site is reached from main")
        for owner in sorted({o for o in owners if o not in from_pass}):
            who = sorted(f for f in top if f != owner and owner in reach(f))
            self.assertEqual(who, ["main"], "%s is reached from main alone, which is what the line's 'main only' claims" % owner)
        derived = "# POOL SITES: run_pass -> %s | main only -> %s" % (" ".join(o for o in owners if o in from_pass),
                                                                      " ".join(o for o in owners if o not in from_pass))
        written = [ln for ln in src.splitlines() if ln.startswith("# POOL SITES: ")]
        self.assertEqual(len(written), 1, "exactly one POOL SITES line in kernel/judge.py: %r" % (written,))
        self.assertEqual(written[0], derived, "kernel/judge.py's POOL SITES line is the AST walk's enumeration; the walk found %d "
                         "constructions at lines %s. Update the line to the derived text, and if a site moved between the two "
                         "groups, read what the kernel's arming rests on (the rebind's comment)" % (len(sites), [ln for ln, _ in sites]))

    def test_the_kernel_arms_the_sink_at_load(self):
        """A kernel load installs its collector's judge_worker_cpu as judge.py's sink and opens judge.cpu_ms_workers at
        0.0 (armed, no pool future yet: a genuine zero, present), and a judge module no kernel has loaded has none, as a
        collector built beside the kernel's has no key. Observed in a child process: judge.py is one module object per
        process and every kernel load re-arms it, so only a load this test controls can show the state before and after."""
        state = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, state, True)
        env = dict(os.environ)
        env["ROMP_STATE_DIR"] = state
        env["ROMP_KERNEL_NO_OPEN"] = "1"
        env.setdefault("ROMP_SERVE_TOKEN", "test-token-DO-NOT-USE")
        code = ("import sys; sys.path.insert(0, %r)\n"
                "from romp_load import load_source\n"
                "load_source('romp_event_model', %r)\n"
                "jd = load_source('romp_judge', %r)\n"
                "assert jd.set_worker_cpu_sink(None) is None, 'no kernel loaded: no sink'\n"
                "km = load_source('romp_kernel', %r)\n"
                "sink = jd.set_worker_cpu_sink(None); jd.set_worker_cpu_sink(sink)\n"   # read and put back: a cleared sink drops the key
                "assert getattr(sink, '__self__', None) is km._PERF_STATS, sink\n"
                "assert sink.__name__ == 'judge_worker_cpu', sink\n"
                "snap = km._PERF_STATS.snapshot()['judge']\n"
                "assert snap.get('cpu_ms_workers') == 0.0, snap.get('cpu_ms_workers')\n"
                "assert 'cpu_ms_workers' not in km._PerfStats().snapshot()['judge'], 'a collector nothing armed: no key'\n"
                # a SECOND kernel load in the same process, the test-suite shape (review round 1, 2026-09-19): it re-executes
                # judge.py and arms its own collector; the first collector is displaced and its served block drops the key,
                # while its live dict keeps the frozen record; the pool work that follows lands in the second collector only.
                # The displaced collector's block is asserted first, so a run on the code before this round fails on it.
                "km2 = load_source('romp_kernel_second_load', %r)\n"
                "first, second = km._PERF_STATS, km2._PERF_STATS\n"
                "assert 'cpu_ms_workers' not in first.snapshot()['judge'], 'displaced: no key, never the frozen 0.0: %%r' %% first.snapshot()['judge'].get('cpu_ms_workers')\n"
                "assert first.judge.get('cpu_ms_workers') == 0.0, 'the live dict keeps the record it took while armed'\n"
                "assert second.snapshot()['judge']['cpu_ms_workers'] == 0.0\n"
                "assert jd.worker_cpu_sink() == second.judge_worker_cpu, jd.worker_cpu_sink()\n"
                "assert second.holds_judge_worker_sink() and not first.holds_judge_worker_sink()\n"
                "import time\n"
                "def burn(s):\n"
                "    t = time.thread_time()\n"
                "    while time.thread_time() - t < s: pass\n"
                "with jd.ThreadPoolExecutor(max_workers=1) as ex: ex.submit(burn, 0.005).result()\n"
                "assert second.snapshot()['judge']['cpu_ms_workers'] >= 4.0, second.snapshot()['judge']\n"
                "assert 'cpu_ms_workers' not in first.snapshot()['judge'], 'still none on the displaced collector'\n"
                "assert first.judge.get('cpu_ms_workers') == 0.0, 'nothing lands in a displaced collector'\n"
                "print('armed')\n"
                % (HERE, os.path.join(BIN, "romp-event-model"), os.path.join(BIN, "romp-judge"), os.path.join(BIN, "romp-kernel"),
                   os.path.join(BIN, "romp-kernel")))
        r = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, timeout=300)
        self.assertEqual(r.returncode, 0, "stderr:\n%s" % r.stderr[-3000:])
        self.assertIn("armed", r.stdout)

    def _sink_saved(self):
        """Restore whatever sink judge.py holds now at cleanup (read by a set-and-put-back, so this also runs on the code
        before round 1, which had no worker_cpu_sink getter: the behavioral assertion is what goes red there)."""
        jd = km.jd
        prev = jd.set_worker_cpu_sink(None)
        jd.set_worker_cpu_sink(prev)
        self.addCleanup(jd.set_worker_cpu_sink, prev)

    def test_a_collector_a_later_arming_displaced_serves_no_workers_key(self):
        """The presence invariant, FORWARD (review round 1, 2026-09-19): a collector a later arming displaced (what a later
        kernel load does through judge.py's re-execution) keeps its live key frozen at what it took, and its served block
        drops the key, so `romp perf` says "not reported" over such a pair instead of reading the frozen figure as a
        measurement. Red before on the first assertNotIn: the displaced block carried the key at 0.0."""
        jd = km.jd
        self._sink_saved()
        first = km._PerfStats()
        first.arm_judge_worker_sink()
        self.assertEqual(first.snapshot()["judge"]["cpu_ms_workers"], 0.0, "armed, no future yet: present at a genuine zero")
        second = km._PerfStats()
        second.arm_judge_worker_sink()                                   # displaces `first`, as a later kernel load does
        self.assertNotIn("cpu_ms_workers", first.snapshot()["judge"], "displaced: the served block has no key, never the frozen 0.0")
        self.assertEqual(self._live(first).get("cpu_ms_workers"), 0.0, "the live dict keeps the record it took while armed")
        with jd.ThreadPoolExecutor(max_workers=1) as ex:
            ex.submit(_burn_cpu, 0.005).result()
        self.assertGreaterEqual(second.snapshot()["judge"]["cpu_ms_workers"], 4.0, "the pool work landed in the collector that holds the sink")
        self.assertNotIn("cpu_ms_workers", first.snapshot()["judge"], "and still none on the displaced one")
        self.assertEqual(self._live(first)["cpu_ms_workers"], 0.0, "frozen: nothing lands in a displaced collector")
        first.reset()
        self.assertNotIn("cpu_ms_workers", self._live(first), "a reset on a displaced collector re-creates nothing")
        self.assertFalse(first.holds_judge_worker_sink()); self.assertTrue(second.holds_judge_worker_sink())

    def test_a_reset_on_the_collector_that_holds_the_sink_keeps_the_key(self):
        """The presence invariant, REVERSE (review round 1, 2026-09-19): reset() on the collector that holds the sink keeps
        cpu_ms_workers, at a genuine zero, and the next future lands in it. Red before on the first assertEqual: the
        literal reset() rebuilds the dict from omitted the key, so an armed collector read "nothing armed me" while it was
        the one reporting."""
        jd = km.jd
        self._sink_saved()
        st = km._PerfStats()
        st.arm_judge_worker_sink()
        with jd.ThreadPoolExecutor(max_workers=1) as ex:
            ex.submit(_burn_cpu, 0.005).result()
        self.assertGreaterEqual(self._live(st)["cpu_ms_workers"], 4.0, "premise: armed and reporting")
        st.reset()
        self.assertEqual(self._live(st).get("cpu_ms_workers"), 0.0, "reset on the collector that holds the sink keeps the key at 0.0")
        self.assertEqual(st.snapshot()["judge"]["cpu_ms_workers"], 0.0)
        with jd.ThreadPoolExecutor(max_workers=1) as ex:
            ex.submit(_burn_cpu, 0.005).result()
        snap = st.snapshot()["judge"]
        self.assertGreaterEqual(snap["cpu_ms_workers"], 4.0, "and the next future lands in the kept key")
        self.assertEqual(snap["cpu_ms_sum"], snap["cpu_ms_workers"], "no tier ran: the sum is the workers' share")
        self.assertTrue(st.holds_judge_worker_sink())

    def test_a_cleared_sink_drops_the_key_from_the_served_block_and_a_bare_sink_serves_it(self):
        """Two more faces of the one invariant (review round 1, 2026-09-19). A jd.set_worker_cpu_sink(None) leaves nobody
        holding the sink, so the armed collector's served block drops the key while its live record stands (red before:
        the block kept serving the frozen figure). And a collector installed by a direct set_worker_cpu_sink with no
        arming call IS the one reporting, so its served block carries the key at 0.0 though its live dict has none yet."""
        jd = km.jd
        self._sink_saved()
        st = km._PerfStats()
        st.arm_judge_worker_sink()
        with jd.ThreadPoolExecutor(max_workers=1) as ex:
            ex.submit(_burn_cpu, 0.005).result()
        jd.set_worker_cpu_sink(None)
        self.assertNotIn("cpu_ms_workers", st.snapshot()["judge"], "a cleared sink: nobody holds it, the key leaves the served block")
        self.assertGreaterEqual(self._live(st)["cpu_ms_workers"], 4.0, "the live record stands")
        self.assertFalse(st.holds_judge_worker_sink())
        bare = km._PerfStats()
        jd.set_worker_cpu_sink(bare.judge_worker_cpu)                    # no arming call, the sink alone
        self.assertNotIn("cpu_ms_workers", self._live(bare), "no arming: the live dict has no key yet")
        self.assertEqual(bare.snapshot()["judge"]["cpu_ms_workers"], 0.0, "but it IS reporting: the served block carries the key at 0.0")
        self.assertTrue(bare.holds_judge_worker_sink())

    def test_a_raising_sink_still_restores_the_workers_stage_mark_and_its_raise_propagates(self):
        """_TimedPool's finally restores the worker's previous stage mark BEFORE it runs the accounting, so a sink that
        raises cannot skip the restore (review round 1, 2026-09-19: the sink ran first, and a raising one left the
        submitter's mark on the pool thread for every later future to inherit as its own "previous"; red before on the raw
        read of the worker's mark). The raise still propagates as the future's error: no try/except around the sink, a
        perf path that ate its own errors would publish numbers nobody could trust. The mark is read RAW on the worker,
        through the base class's submit, which bypasses the wrapper that would set and restore it."""
        jd = km.jd
        em = jd.em                                                          # the module object _TimedPool's wrapper calls into
        # this kernel's provider pair for the test's duration: a private judge or event-model load by another test module
        # in the same process re-executes event_model.py and clears both hooks, so the pair cannot be assumed installed
        saved = (em._SET_STAGE_FN[0], em._READ_STAGE_FN[0])
        em.set_stage_provider(km._set_stage); em.set_read_stage_provider(km._current_read_stage)
        self.addCleanup(em.set_stage_provider, saved[0]); self.addCleanup(em.set_read_stage_provider, saved[1])

        def boom(ms):
            raise RuntimeError("sink died")
        prev = jd.set_worker_cpu_sink(boom)
        self.addCleanup(jd.set_worker_cpu_sink, prev)
        raw_submit = concurrent.futures.ThreadPoolExecutor.submit           # the base class's: no mark, no accounting
        em._set_stage_mark("judge.test")                                    # the submitter's mark, carried into the worker
        self.addCleanup(em._set_stage_mark, None)
        self.assertEqual(em._read_stage(), "judge.test", "premise: the stage provider pair is installed")
        with jd.ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(lambda: "the future's own result")
            with self.assertRaises(RuntimeError, msg="the sink's raise stands in for the future's result: nothing swallows it"):
                fut.result(10)
            self.assertIsNone(raw_submit(ex, em._read_stage).result(10),
                              "the worker's previous mark (none) is restored though the sink raised")
            em._set_stage_mark(None)
            self.assertIsNone(raw_submit(ex, em._read_stage).result(10), "and a later future from an unmarked thread leaves it clear")

    def test_a_pool_future_from_a_thread_outside_the_producer_lands_under_cpu_ms_workers(self):
        """The sink is per future and reads no thread: a future submitted from a plain Thread, the shape of the kernel's
        boot roads (threading.Thread(target=_rewind_migration_bg), which calls jd.run_rewound_reconcile), lands in the
        armed collector's cpu_ms_sum and cpu_ms_workers like one from a tier thread under _producer. The boot road submits
        no pool future today (tests/test_kernel_rewind.py pins that by running the real migration over a discoverable
        session with a recording sink); this pins what the design does if a later change makes it submit one (review
        round 1, 2026-09-19: the body's rationale had claimed kernel.py calls no jd.run_* outside _producer)."""
        jd = km.jd
        st = km._PerfStats()
        received = self._arm(st)

        def boot_road():
            with jd.ThreadPoolExecutor(max_workers=1) as ex:
                ex.submit(_burn_cpu, 0.005).result()
        th = threading.Thread(target=boot_road, name="boot-road")
        th.start(); th.join(30)
        self.assertFalse(th.is_alive())
        snap = st.snapshot()["judge"]
        self.assertGreaterEqual(snap["cpu_ms_workers"], 4.0, "the plain thread's pool future landed: %r" % snap["cpu_ms_workers"])
        self.assertEqual(snap["cpu_ms_sum"], snap["cpu_ms_workers"], "no tier ran: the sum is the workers' share")
        self.assertAlmostEqual(sum(received), snap["cpu_ms_workers"], places=6, msg="through the sink, once")

    def test_run_tier_accounts_the_tier_threads_cpu(self):
        """The shared tier runner (judge.py _run_tier, stage three round two) lands the thread's own CPU in the pass's
        accounting record under its lock, a raising tier included (the finally); the producer feeds the record's total to
        /perf's judge.cpu_ms_sum (a source pin on the call)."""
        jd = km.jd
        acc = jd._pass_acc()
        jd._run_tier(lambda: _burn_cpu(0.005), "index", acc)
        self.assertGreaterEqual(acc["cpuS"] * 1000.0, 4.0); self.assertEqual(acc["failures"], [])
        before = acc["cpuS"]
        with redirect_stderr(io.StringIO()):
            jd._run_tier(lambda: (_burn_cpu(0.005), (_ for _ in ()).throw(RuntimeError("tier died"))), "triage", acc)
        self.assertGreaterEqual((acc["cpuS"] - before) * 1000.0, 4.0, "a raising tier still accounts (the finally)")
        self.assertEqual(len(acc["failures"]), 1); self.assertIn("RuntimeError: tier died", acc["failures"][0])
        import inspect
        self.assertIn('_PERF_STATS.judge_cpu(res["tierCpuS"])', inspect.getsource(km._producer), "the producer feeds the total")
        self.assertIn('with acc["lock"]:', inspect.getsource(jd._run_tier), "the accumulation takes the lock")
        before = km._PERF_STATS.snapshot()["judge"]["cpu_ms_sum"]
        km._PERF_STATS.judge_cpu(0.005)
        self.assertAlmostEqual(km._PERF_STATS.snapshot()["judge"]["cpu_ms_sum"] - before, 5.0, places=3)


class PusherRecords(unittest.TestCase):
    """The pusher's seams record into _PERF_STATS: a cycle lands in the ring with its thread's CPU, the
    cycle jobs split into push and jobs, the cached and rebuilt feed/timeline paths count, and the
    send paths classify full / delta / deduped for whole-frame, delta-capable and chat-tail clients."""

    # _refresh_parked_parses is not a cycle job since the 2026-09-07 upstream fold: the per-sid refresh runs
    # in the locked drain, not in _pusher_cycle_jobs (upstream's removal adopted: the refresh belongs under the drain's lock).
    JOBS = ("_apply_pending_ops", "_lift_spent_awaiting", "_death_sweep_tick",
            "_end_on_idle_sweep", "_deferral_sweep_tick", "_auto_nudge_tick", "_interrupt_block_tick",
            "_auto_pause_on_limit", "_usage_poll_tick", "_auto_pause_on_spend_limit", "_auto_resume_retry",
            "_auto_resume_session_retry", "_auto_retry_tick", "_idle_queue_drive_tick",
            "_clear_done_working_notes", "_spend_guard_tick", "_push_all",
            "_api_health_frame", "_api_health_push",   # the bottom bar's API cell; the spend guard (T350, "_converge_checkpoints")
            "_turn_notify_tick")                       # upstream's turn-end notification pass

    def setUp(self):
        # The real _pusher_cycle the tests below drive opens the pusher's cycle on this thread: cycle_begin registers the thread
        # in _PERF_STATS._owners and cycle() leaves the registration standing, so until this cleanup every class run after
        # this one in the module inherited the main thread as the pusher's owner (the leak PushStages's real-push test was
        # green through; 2026-09-19 review). Registered before anything else in setUp, so a raising setUp cannot skip it.
        owners, cycle_state = dict(km._PERF_STATS._owners), copy.deepcopy(km._PERF_STATS._cycle_state)

        def restore_cycle_owner():
            km._PERF_STATS._owners.clear(); km._PERF_STATS._owners.update(owners)
            km._PERF_STATS._cycle_state.clear(); km._PERF_STATS._cycle_state.update(cycle_state)
        self.addCleanup(restore_cycle_owner)
        self.td = tempfile.TemporaryDirectory()
        names = Path(self.td.name) / "names"
        names.mkdir()
        self.saved = (km.NAMES, km._live_map, km._pusher_cycle_jobs, list(km._built_feed),
                      list(km._built_timeline), km.build_feed, km.build_timeline, km._needs_you_count,
                      km._feed_notifications, km._badge_push, km._views_dirty[0])
        self.saved_jobs = {nm: getattr(km, nm) for nm in self.JOBS}
        km.NAMES = names
        km._live_map = lambda: {}
        self.addCleanup(self._restore)
        self.addCleanup(self.td.cleanup)

    def _restore(self):
        (km.NAMES, km._live_map, km._pusher_cycle_jobs, bf, bt, km.build_feed, km.build_timeline,
         km._needs_you_count, km._feed_notifications, km._badge_push, vd) = self.saved
        km._built_feed[:] = bf
        km._built_timeline[:] = bt
        km._views_dirty[0] = vd
        for nm, fn in self.saved_jobs.items():
            setattr(km, nm, fn)

    def _pusher(self):
        return km._PERF_STATS.snapshot()["pusher"]

    def test_an_idle_cycle_is_one_that_set_no_wake_sent_nothing_and_saved_nothing(self):
        # IDLE CYCLES (2026-09-09): the loop re-enters after a fixed 0.5 s backstop whether or not anything
        # changed; the idle share is what a cadence change is judged on. A cycle whose jobs set no wake,
        # sent no client payload and saved no goal store counts as idle, with its wall and CPU.
        km._pusher_cycle_jobs = lambda now, live_map, any_client: time.sleep(0.003)
        before = self._pusher()
        km._pusher_cycle()
        after = self._pusher()
        self.assertEqual(after["idle_cycles"], before["idle_cycles"] + 1)
        self.assertGreaterEqual(after["idle_ms_sum"] - before["idle_ms_sum"], 3.0)
        self.assertGreaterEqual(after["idle_cpu_ms_sum"], before["idle_cpu_ms_sum"])
        self.assertEqual(after["cycles"], before["cycles"] + 1, "an idle cycle is still a cycle")

    def test_a_cycle_that_sends_a_payload_is_not_idle(self):
        km._pusher_cycle_jobs = lambda now, live_map, any_client: km._PERF_STATS.send(("chat", "s1"), "full", 10)
        before = self._pusher()
        km._pusher_cycle()
        after = self._pusher()
        self.assertEqual(after["idle_cycles"], before["idle_cycles"])
        self.assertEqual(after["sends"], before["sends"] + 1)

    def test_a_deduped_frame_does_not_break_an_idle_cycle(self):
        # with a dashboard connected the push builds and compares the per-cycle chat frames every cycle; a
        # frame the client already holds is reported as "deduped" and is not a payload that went out
        km._pusher_cycle_jobs = lambda now, live_map, any_client: km._PERF_STATS.send(("chat", "taborder"), "deduped", 10)
        before = self._pusher()
        km._pusher_cycle()
        after = self._pusher()
        self.assertEqual(after["idle_cycles"], before["idle_cycles"] + 1, "still idle")
        self.assertEqual(after["sends"], before["sends"], "a deduped frame is not a send")

    def test_a_cycle_that_sets_the_wake_is_not_idle(self):
        km._pusher_cycle_jobs = lambda now, live_map, any_client: km._pusher_wake.set()
        before = self._pusher()
        km._pusher_cycle()
        km._pusher_wake.clear()
        self.assertEqual(self._pusher()["idle_cycles"], before["idle_cycles"])

    def test_a_cycle_that_saves_a_goal_store_is_not_idle(self):
        km._pusher_cycle_jobs = lambda now, live_map, any_client: km.jd._goal_io_bump("saves")
        before = self._pusher()
        km._pusher_cycle()
        self.assertEqual(self._pusher()["idle_cycles"], before["idle_cycles"])
        km._pusher_cycle_jobs = lambda now, live_map, any_client: km.jd._goal_io_bump("writes")
        km._pusher_cycle()
        self.assertEqual(self._pusher()["idle_cycles"], before["idle_cycles"])

    def test_a_cycle_is_counted_and_timed(self):
        km._pusher_cycle_jobs = lambda now, live_map, any_client: time.sleep(0.005)
        before = self._pusher()
        km._pusher_cycle()
        after = self._pusher()
        self.assertEqual(after["cycles"], before["cycles"] + 1)
        self.assertGreaterEqual(after["cycle_ms_last"], 5.0)
        self.assertEqual(after["ring_n"], min(before["ring_n"] + 1, km._PerfStats.RING))

    def test_a_cycle_records_its_threads_cpu_not_its_waits(self):
        km._pusher_cycle_jobs = lambda now, live_map, any_client: time.sleep(0.020)   # a wait, no CPU
        before = self._pusher()
        km._pusher_cycle()
        after = self._pusher()
        self.assertGreaterEqual(after["cycle_ms_last"], 20.0)
        self.assertLess(after["cycle_cpu_ms_sum"] - before["cycle_cpu_ms_sum"], 15.0,
                        "a sleeping cycle adds far less CPU than wall")
        km._pusher_cycle_jobs = lambda now, live_map, any_client: _burn_cpu(0.005)     # CPU, no wait
        before = self._pusher()
        km._pusher_cycle()
        after = self._pusher()
        self.assertGreaterEqual(after["cycle_cpu_ms_sum"] - before["cycle_cpu_ms_sum"], 4.0,
                                "a spinning cycle's CPU lands in cycle_cpu_ms_sum")

    def test_a_raising_cycle_is_still_counted(self):
        km._pusher_cycle_jobs = lambda now, live_map, any_client: (_ for _ in ()).throw(RuntimeError("job died"))
        before = self._pusher()["cycles"]
        with self.assertRaises(RuntimeError):
            km._pusher_cycle()
        self.assertEqual(self._pusher()["cycles"], before + 1)

    def test_cycle_jobs_split_into_push_and_jobs(self):
        # the REAL _pusher_cycle_jobs with every tick job a no-op and _push_all a stub that reads the clock ONCE,
        # under a stubbed time.monotonic that steps 1 ms per read: `push` is the _push_all call (the read inside
        # the stub plus the read that closes it: 2 ms exactly), `jobs` the rest of the function (the reads outside
        # the push: a count of clock reads, never negative). A wall-clock ratio here (push >= a 5 ms sleep, jobs
        # below two pushes) was green alone and a coin toss under the suite (2026-09-12, 2026-09-14); a stubbed
        # clock makes both stages counts
        for nm in self.JOBS:
            setattr(km, nm, lambda *a, **k: None)
        km._push_all = lambda live_map=None: time.monotonic()
        reads = [0]
        def _clock():
            reads[0] += 1
            return reads[0] * 0.001
        with mock.patch.object(km.time, "monotonic", _clock):
            before = km._PERF_STATS.snapshot()["stages_ms"]
            km._pusher_cycle_jobs(int(time.time()), {}, True)
            after = km._PERF_STATS.snapshot()["stages_ms"]
            push, jobs = after["push"] - before["push"], after["jobs"] - before["jobs"]
            n_first = reads[0]
            self.assertAlmostEqual(push, 2.0, places=6, msg="the push stage spans the stub's read and the closing read")
            self.assertGreaterEqual(jobs, 0.0, "jobs is the function minus the push, never negative")
            self.assertAlmostEqual(push + jobs, (n_first - 1) * 1.0, places=6, msg="push plus jobs is the function's whole span: every read but the first")
            before = km._PERF_STATS.snapshot()["stages_ms"]
            km._pusher_cycle_jobs(int(time.time()), {}, False)   # no client: no push, the jobs still run
            after = km._PERF_STATS.snapshot()["stages_ms"]
            self.assertEqual(after["push"], before["push"])
            self.assertAlmostEqual(after["jobs"] - before["jobs"], (reads[0] - n_first - 1) * 1.0, places=6, msg="the no-client cycle's jobs span every read but its first")

    def test_a_connect_serves_the_build_it_tested_when_the_cache_is_replaced_between_its_reads(self):
        # _cached_timeline tested the cached payload and returned it as two reads of the shared list while the
        # pusher thread assigns _built_timeline[:] on a rebuild; a connect on the handler thread whose two reads
        # straddled that assignment returned the replacement build, not the one its freshness test saw. One read.
        class Swapped(list):
            """_built_timeline with the pusher's `_built_timeline[:] = [...]` landing between two reads of the
            payload slot: the first read answers the build, every later one the replacement."""
            def __init__(self, entry, later):
                super().__init__(entry)
                self.reads, self.later = 0, later

            def __getitem__(self, i):
                if i == 1:
                    self.reads += 1
                    if self.reads > 1:
                        return self.later
                return list.__getitem__(self, i)
        built = {"type": "timeline", "now": 1.0, "turns": {}, "judging": {}, "messages": []}
        replacement = {"type": "timeline", "now": 2.0, "turns": {}, "judging": {}, "messages": []}
        real = km._built_timeline
        km._built_timeline = Swapped(["sig-a", built, 5.0, 4.0], replacement)   # the pusher replaced the build between the two reads
        self.addCleanup(setattr, km, "_built_timeline", real)
        km.build_timeline = lambda *a, **k: (_ for _ in ()).throw(AssertionError("a connect never rebuilds"))
        served = km._VIEW_STATS["tlServe"]
        self.assertIs(km._cached_timeline(int(time.time()), {}, "sig-b", connect=True), built,
                      "the connect gets the build its freshness test saw, not the replacement that landed under it")
        self.assertEqual(km._VIEW_STATS["tlServe"], served + 1)

    def test_feed_and_timeline_builds_count_cached_and_rebuilt(self):
        km.build_feed = lambda now, live_map: {"working": [], "items": []}
        km.build_timeline = lambda now, live_map, **kw: {"turns": [], "judging": [], "messages": [], "now": now}
        km._needs_you_count = lambda feed: 0
        km._feed_notifications = lambda feed: []
        km._badge_push = lambda n: None
        km._views_dirty[0] = 0.0
        km._built_feed[:] = [None, None, 0.0, 0.0]
        km._built_timeline[:] = [None, None, 0.0, 0.0]
        b0 = km._PERF_STATS.snapshot()["builds"]
        now = int(time.time())
        km._cached_feed(now, {}, "sig-a")                    # nothing warmed: a rebuild
        km._cached_feed(now, {}, "sig-a")                    # unchanged sig: served from the cache
        km._cached_timeline(now, {}, "sig-a")
        km._cached_timeline(now, {}, "sig-a", connect=True)  # a connecting page never rebuilds
        b1 = km._PERF_STATS.snapshot()["builds"]
        self.assertEqual(b1["feed"]["built"] - b0["feed"]["built"], 1)
        self.assertEqual(b1["feed"]["cached"] - b0["feed"]["cached"], 1)
        self.assertGreaterEqual(b1["feed"]["ms"], b0["feed"]["ms"])
        self.assertEqual(b1["timeline"]["built"] - b0["timeline"]["built"], 1)
        self.assertEqual(b1["timeline"]["cached"] - b0["timeline"]["cached"], 1)

    @staticmethod
    def _sends():
        s = km._PERF_STATS.snapshot()["sends"]
        return {(kind, slot): e["count"] for kind, d in s.items() for slot, e in d.items()}

    def test_a_whole_frame_client_counts_full_then_deduped(self):
        sent = []
        c = {"app": "chat", "alive": True, "send": sent.append, "sent": {}}
        s0 = self._sends()
        km._send_client(c, ("working", SID), {"type": "working", "names": ["web"]})
        km._send_client(c, ("working", SID), {"type": "working", "names": ["web"]})
        s1 = self._sends()
        self.assertEqual(len(sent), 1, "the second identical frame was deduped")
        self.assertEqual(s1[("full", "working")] - s0.get(("full", "working"), 0), 1)
        self.assertEqual(s1[("deduped", "working")] - s0.get(("deduped", "working"), 0), 1)
        bytes_full = km._PERF_STATS.snapshot()["sends"]["full"]["working"]["bytes"]
        self.assertGreaterEqual(bytes_full, len(sent[0]))

    def test_a_delta_client_counts_the_suppressed_bars_frame_as_deduped(self):
        # every browser pane connects with delta=1, so the bars slot's dedup happens in _send_slot_delta's
        # unchanged path, not in _send_client — it must count there too, or deduped.timelinebars stays 0
        sent = []
        c = {"app": "timeline", "alive": True, "send": sent.append, "sent": {}, "delta": True}
        bars = {"type": "bars", "turns": {"lane": [{"id": "t1", "a": 1}]}, "judging": [], "messages": [],
                "now": 1, "warming": False}
        pre = json.dumps(bars)
        sig = km._dedup_sig(bars, pre)
        s0 = self._sends()
        km._send_slot(c, "bars", bars, pre, sig)
        km._send_slot(c, "bars", bars, pre, sig)
        s1 = self._sends()
        self.assertEqual(len(sent), 1, "the keyed full went once; the unchanged repeat sent nothing")
        self.assertEqual(s1[("full", "timelinebars")] - s0.get(("full", "timelinebars"), 0), 1)
        self.assertEqual(s1[("deduped", "timelinebars")] - s0.get(("deduped", "timelinebars"), 0), 1)
        self.assertEqual(s1.get(("delta", "timelinebars"), 0) - s0.get(("delta", "timelinebars"), 0), 0)

    def test_a_delta_client_counts_a_changed_bars_frame_as_delta_with_the_slot_on_the_client(self):
        # the delta frame goes through _client_send like every other frame (2026-09-06): the slot key sits on the
        # client while it goes — what _note_ws_drop and the bench harness read — and the delta class counts it;
        # the same payload object pushed again is the identity short-circuit, counted as deduped
        sent = []
        c = {"app": "timeline", "alive": True, "sent": {}, "delta": True}
        c["send"] = lambda s: sent.append((c.get("curSlot"), s))
        frac = km._DELTA_MAX_FRACTION
        km._DELTA_MAX_FRACTION = 10.0        # synthetic payloads are tiny: the size guard would send the whole instead
        self.addCleanup(setattr, km, "_DELTA_MAX_FRACTION", frac)
        # judging is a per-lane dict on the wire since T278c (upstream #1154, folded 2026-09-09): a list is an
        # unkeyable payload and the slot falls back to whole frames
        b1 = {"type": "bars", "turns": {"lane": [{"id": "t1", "a": 1}]}, "judging": {}, "messages": [],
              "now": 1, "warming": False}
        b2 = {"type": "bars", "turns": {"lane": [{"id": "t1", "a": 1}, {"id": "t2", "a": 2}]}, "judging": {},
              "messages": [], "now": 2, "warming": False}
        s0 = self._sends()
        for b in (b1, b2, b2):
            pre = json.dumps(b)
            km._send_slot(c, "bars", b, pre, km._dedup_sig(b, pre))
        s1 = self._sends()
        self.assertEqual([json.loads(s)["type"] for _k, s in sent], ["bars", "delta"])
        self.assertEqual([k for k, _s in sent], [("timelinebars",), ("timelinebars",)], "both frames went with the slot on the client")
        self.assertEqual(s1[("full", "timelinebars")] - s0.get(("full", "timelinebars"), 0), 1)
        self.assertEqual(s1[("delta", "timelinebars")] - s0.get(("delta", "timelinebars"), 0), 1)
        self.assertEqual(s1[("deduped", "timelinebars")] - s0.get(("deduped", "timelinebars"), 0), 1, "the same object again: deduped, not sent")
        self.assertGreaterEqual(km._PERF_STATS.snapshot()["sends"]["delta"]["timelinebars"]["bytes"], len(sent[1][1]))

    def test_a_caught_up_chat_client_counts_its_tail_as_delta(self):
        sent = []
        c = {"app": "chat", "alive": True, "send": sent.append, "sent": {}}
        m1 = {"type": "session", "id": SID, "name": "web", "events": [{"uuid": "e1", "type": "user"}],
              "status": {"state": "working"}}                # the shape build_session returns: a {type: session} frame
        m2 = {"type": "session", "id": SID, "name": "web", "events": m1["events"] + [{"uuid": "e2", "type": "assistant"}],
              "status": {"state": "waiting"}}
        s0 = self._sends()
        km._send_chat(c, m1, None, 0, False)                # nothing held: the whole session
        km._send_chat(c, m2, None, 1, False)                # caught up through e1: the suffix from 1
        s1 = self._sends()
        self.assertEqual([json.loads(x)["type"] for x in sent], ["session", "chatTail"])
        self.assertEqual(s1[("full", "chat")] - s0.get(("full", "chat"), 0), 1)
        self.assertEqual(s1[("delta", "chat")] - s0.get(("delta", "chat"), 0), 1, "the tail is the chat's delta")


class PushStages(unittest.TestCase):
    """_push driven for real (the test_tab_meta_push.py pattern) with builders stubbed to sleep 5 ms
    each: every push.* stage grows by at least its builder's sleep, the chat build counts as built on
    the first push and as cached on the second (same transcript, background tab), and the timeline
    client's bars go out in the send stage. setUp opens the pusher's cycle on the module collector
    first (2026-09-18): stage() credits a push stage to the thread that owns the pusher's cycle, and
    the "push" mark _push carries is no owner, so a bare _push from a thread that opened no cycle,
    and so was never registered as an owner, counts under stagesForeign and the flat rows read zero.
    Before that line the real-push test was green only
    through a leak: PusherRecords drove the real _pusher_cycle, whose cycle_begin registered this
    thread as the pusher's owner, and never restored the owner map, so the registration reached
    every class after it (red with this class run alone). That leak is closed at its source, a
    cleanup in PusherRecords.setUp; this class opens its own cycle because its _push needs an owner,
    not because a sibling leaves one. tearDown puts the owner map and the split state back so no
    later test inherits this class's cycle."""

    STUBS = ("NAMES", "_live_map", "_live_names", "_chat_tab_sessions", "build_session",
             "_cached_feed", "_cached_timeline", "build_timeline", "_fleet_view_sig", "_comments_frame",
             "_retry_parked_creates")

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        names = Path(self.tmp) / "names"
        names.mkdir()
        (names / SID).write_text("web\t/proj/TESTHOST/app\t#1EA1EB\twhite\n")
        self.transcript = Path(self.tmp) / (SID + ".jsonl")
        self.transcript.write_text('{"type": "user"}\n')       # exists → _chat_build_sig is a real signature
        self.saved = {nm: getattr(km, nm) for nm in self.STUBS}
        self.saved_state = (km.jd.STATE, dict(km._built_chat), dict(km._prev_chat_events),
                            dict(km._prev_chat_ledger), list(km._last_tab_order))
        km.NAMES = names
        km.jd.STATE = Path(self.tmp) / "state"
        km.jd.STATE.mkdir(parents=True, exist_ok=True)
        km._live_map = lambda: {}
        km._live_names = lambda tm: {"web": SID}
        km._chat_tab_sessions = lambda now, live_map: [{"sid": SID, "name": "web", "path": str(self.transcript),
                                                    "anchor": SID}]
        km.build_session = self._build_session
        km._cached_feed = lambda now, live_map, sig, connect=False: self._slow({"working": [], "awaiting": [], "now": now})
        km._cached_timeline = lambda now, live_map, sig, connect=False: self._slow(
            {"turns": {}, "judging": [], "messages": [], "now": now})
        km.build_timeline = lambda now, live_map, **kw: {"lanes": [], "now": now}
        km._fleet_view_sig = lambda now, live_map: {"probe": 1}
        km._comments_frame = lambda sid, live_map: None
        km._retry_parked_creates = lambda: None
        km._built_chat.clear(); km._prev_chat_events.clear(); km._prev_chat_ledger.clear()
        self.builds = 0
        self.chat_frames, self.tl_frames = [], []
        self.chat = {"app": "chat", "alive": True, "sent": {}, "send": lambda s: self.chat_frames.append(json.loads(s))}
        self.tl = {"app": "timeline", "alive": True, "sent": {}, "send": lambda s: self.tl_frames.append(json.loads(s))}
        self.saved_cycle = (dict(km._PERF_STATS._owners), dict(km._PERF_STATS._cycle_state))
        km._PERF_STATS.cycle_begin()          # this thread is the pusher: its _push below is the cycle owner's (the class docstring)

    def tearDown(self):
        owners, cycle_state = self.saved_cycle
        km._PERF_STATS._owners.clear(); km._PERF_STATS._owners.update(owners)
        km._PERF_STATS._cycle_state.clear(); km._PERF_STATS._cycle_state.update(cycle_state)
        for nm, v in self.saved.items():
            setattr(km, nm, v)
        st, bc, pe, pl, lo = self.saved_state
        km.jd.STATE = st
        km._built_chat.clear(); km._built_chat.update(bc)
        km._prev_chat_events.clear(); km._prev_chat_events.update(pe)
        km._prev_chat_ledger.clear(); km._prev_chat_ledger.update(pl)
        km._last_tab_order[:] = lo

    @staticmethod
    def _slow(value):
        time.sleep(0.005)
        return value

    def _build_session(self, sid, now, live_map):
        self.builds += 1
        return self._slow({"type": "session", "id": sid, "name": "web", "events": [{"uuid": "e1", "type": "user"}],
                           "ledger": None, "status": {"state": "waiting"}, "color": None})

    def test_stages_and_chat_builds_are_recorded_by_the_real_push(self):
        snap0 = km._PERF_STATS.snapshot()
        km._push([self.chat, self.tl])
        snap1 = km._PERF_STATS.snapshot()
        self.assertEqual(self.builds, 1)
        d = {k: snap1["stages_ms"][k] - snap0["stages_ms"][k] for k in snap0["stages_ms"]}
        self.assertGreaterEqual(d["push.chat"], 5.0, "the build_session sleep lands in the chat stage")
        self.assertGreaterEqual(d["push.feed"], 5.0, "the _cached_feed sleep lands in the feed stage")
        self.assertGreaterEqual(d["push.timeline"], 5.0, "the _cached_timeline sleep lands in the timeline stage")
        self.assertGreater(d["push.send"], 0.0, "the bars serialization and send took time")
        self.assertEqual(d["jobs"], 0.0, "a bare _push is not a cycle: jobs and push stay")
        self.assertEqual(d["push"], 0.0)
        self.assertEqual(snap1["builds"]["chat"]["built"] - snap0["builds"]["chat"]["built"], 1)
        self.assertEqual(snap1["builds"]["chat"]["cached"] - snap0["builds"]["chat"]["cached"], 0)
        self.assertGreaterEqual(snap1["builds"]["chat"]["ms"] - snap0["builds"]["chat"]["ms"], 5.0)
        self.assertIn("session", [f["type"] for f in self.chat_frames])
        self.assertIn("bars", [f["type"] for f in self.tl_frames])
        # the same transcript again: the background tab's build is served from the cache
        km._push([self.chat, self.tl])
        snap2 = km._PERF_STATS.snapshot()
        self.assertEqual(self.builds, 1, "no rebuild")
        self.assertEqual(snap2["builds"]["chat"]["cached"] - snap1["builds"]["chat"]["cached"], 1)
        self.assertEqual(snap2["builds"]["chat"]["built"] - snap1["builds"]["chat"]["built"], 0)
        self.assertLess(snap2["stages_ms"]["push.chat"] - snap1["stages_ms"]["push.chat"], 5.0,
                        "a cached tab costs the chat stage no build")

    def test_the_per_session_row_is_fed_by_the_real_push_with_the_leafs_bytes_and_a_cached_second_push(self):
        # round three, low 2: the wiring executed instead of a regex over the kernel source: the built site hands the sid and
        # the leaf's byte size, the cached site hands the sid; a second push over the same transcript raises `cached` and leaves n
        km._PERF_STATS.chat_by_session.pop(SID, None)
        km._push([self.chat, self.tl])
        rows = km._PERF_STATS.chat_by_session                  # the collector's rows by sid: the served list ranks them (2026-09-18)
        self.assertIn(SID, rows, "the built site hands the sid: %s" % sorted(rows))
        row = dict(rows[SID])
        self.assertEqual((row["n"], row["cached"], row["bytes"]), (1, 0, os.path.getsize(self.transcript)), row)
        self.assertGreaterEqual(row["first"], 5.0, "the build's sleep is the first build's ms"); self.assertEqual((row["last"], row["max"]), (row["first"], row["first"]))
        served = km._PERF_STATS.snapshot()["builds"]["chat"]["bySession"]
        self.assertIn(row, [{k: v for k, v in r.items() if k != "rank"} for r in served], "the same row rides the served list, by rank")
        self.assertFalse([r for r in served if "sid" in r], "no row names its session")
        km._push([self.chat, self.tl])
        row2 = km._PERF_STATS.chat_by_session[SID]
        self.assertEqual((row2["n"], row2["cached"], row2["first"]), (1, 1, row["first"]), "the cached site hands the sid; n and first stand")

    def test_the_targeted_push_records_its_build_in_the_row_and_the_aggregate(self):
        # round three, low 1: _push_session_now built through build_session and recorded nothing, so the row's first (the number
        # the timer exists to read) could be a build over a cache an unrecorded handshake push had warmed; it records under the
        # label `targeted` now and still caches nothing (no dependency record: a stored entry would have no signature)
        km._PERF_STATS.chat_by_session.pop(SID, None)
        saved = (list(km._clients), km._PERF_STATS.snapshot()["builds"]["chat"])
        with km._clients_lock:
            km._clients[:] = [self.chat]
        try:
            km._push_session_now(SID)
        finally:
            with km._clients_lock:
                km._clients[:] = saved[0]
        self.assertEqual(self.builds, 1, "the targeted push built the session")
        snap = km._PERF_STATS.snapshot()["builds"]["chat"]
        row = km._PERF_STATS.chat_by_session.get(SID)          # the collector's row by sid; the served list ranks it (2026-09-18)
        self.assertIsNotNone(row, "the targeted push feeds the per-session row")
        self.assertIn(dict(row), [{k: v for k, v in r.items() if k != "rank"} for r in snap["bySession"]], "and the served list carries it")
        self.assertEqual((row["n"], row["cached"], row["bytes"]), (1, 0, os.path.getsize(self.transcript)), row)
        self.assertGreaterEqual(row["first"], 5.0)
        self.assertEqual(snap["built"] - saved[1]["built"], 1, "and the aggregate")
        self.assertEqual(snap["bg_miss"].get("targeted", 0) - saved[1]["bg_miss"].get("targeted", 0), 1, "attributed to the push, not a signature component")
        self.assertNotIn(SID, km._built_chat, "still not cached: the build ran with no dependency record")
        self.assertIn("session", [f["type"] for f in self.chat_frames])
        # round four, low b: the watched tab's handshake build lands under active_built, read from the target client's active sid
        self.chat["active"] = SID
        km._PERF_STATS.chat_by_session.pop(SID, None)
        before = km._PERF_STATS.snapshot()["builds"]["chat"]
        with km._clients_lock:
            km._clients[:] = [self.chat]
        try:
            km._push_session_now(SID)
        finally:
            with km._clients_lock:
                km._clients[:] = saved[0]
        after = km._PERF_STATS.snapshot()["builds"]["chat"]
        self.assertEqual((after["active_built"] - before["active_built"], after["bg_built"] - before["bg_built"]), (1, 0),
                         "the watched tab's build counts as active, not background")
        self.assertEqual(after["bg_miss"].get("targeted", 0), before["bg_miss"].get("targeted", 0), "no background attribution for the watched tab")

    def test_the_seams_stay_where_the_stages_are_defined(self):
        # the order of the four stage records in _push is the definition of the split; pinned beside the
        # behavioural test above so a re-ordering is caught even when every stage still grows
        push = inspect.getsource(km._push)
        idx = [push.index('_PERF_STATS.stage("%s"' % st) for st in ("push.chat", "push.feed", "push.timeline", "push.send")]
        self.assertEqual(idx, sorted(idx))
        self.assertIn("_PERF_STATS.judge_pass(", inspect.getsource(km._producer))
        loop = inspect.getsource(km._pusher)
        self.assertIn("_woke = wake.wait(PUSH_BACKSTOP_S)", loop)
        self.assertIn("_PERF_STATS.wake_kind(_woke)", loop)
        self.assertIn("_PERF_STATS.hold(clock() - due)", loop)     # the interval's counters ride the same loop
        self.assertIn("_PERF_STATS.exempt()", loop)


class PerfRoutes(unittest.TestCase):
    """GET /perf and POST /perf through the real Handler: token-gated, the documented shape, the toggle,
    and every request method counted under METHOD /path."""

    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), km.Handler)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def setUp(self):
        self.saved_log = km._PERF
        km._set_perf_log(False)

    def tearDown(self):
        km._set_perf_log(self.saved_log)

    def _req(self, method, path, body=None, token=True):
        headers = {"Content-Type": "application/json"}
        if token:
            # km.TOKEN, not os.environ: under xdist every worker imports every test module at
            # collection, and a later module's import-time ROMP_SERVE_TOKEN write changes the env
            # after this module's kernel captured its token (the test_kernel_attach_on_behalf pattern)
            headers["X-Romp-Token"] = km.TOKEN
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request("http://127.0.0.1:%d%s" % (self.port, path), data=data,
                                     headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                raw = r.read().decode()
                return r.status, (json.loads(raw) if raw.startswith(("{", "[")) else raw)
        except urllib.error.HTTPError as e:
            raw = e.read().decode()
            return e.code, (json.loads(raw) if raw.startswith(("{", "[")) else raw)

    @staticmethod
    def _http(key):
        return km._PERF_STATS.snapshot()["http"].get(key, {"count": 0, "ms": 0.0})

    def test_get_perf_serves_the_snapshot(self):
        with _HttpWatch() as w:
            st, snap = self._req("GET", "/perf")
            self.assertEqual(st, 200)
            self.assertEqual(set(snap), TOP_KEYS)
            self.assertIs(snap["log"], False)
            self.assertEqual(snap["process"]["pid"], os.getpid())
            self.assertTrue(w.wait_for("GET /perf", 1), "the request's own record lands after the response")
            st, snap2 = self._req("GET", "/perf?x=1")
        self.assertEqual(st, 200)
        self.assertGreaterEqual(snap2["http"]["GET /perf"]["count"], 1, "counted under METHOD /path, query stripped")
        self.assertFalse([k for k in snap2["http"] if "?" in k])

    def test_get_perf_requires_the_token(self):
        st, body = self._req("GET", "/perf", token=False)
        self.assertEqual(st, 403)
        self.assertNotIn("cycles", str(body))
        st, body = self._req("GET", "/perf?stacks=1", token=False)
        self.assertEqual(st, 403, "the stack sample is token-gated like the snapshot")
        self.assertNotIn("frames", str(body))

    def test_get_perf_stacks_carries_one_frame_list_per_thread_with_its_stage_mark(self):
        """T401 (2)'s proof instrument: `?stacks=1` adds one row per live thread (name, ident, self, stage, frames innermost
        last); a thread inside a tick job shows `jobs.<job>` and its own frames under the launcher, outermost first; the plain
        snapshot carries no `stacks`; the registry row is gone once the job returns. No wait frame is pinned or looked for
        (2026-09-19): a thread parked on an Event is sampled at wait, at the lock acquire inside it, or before it enters wait,
        so the row is pinned on the probe function's own frame, on the stack from its entry to its exit whatever it is inside,
        under the launcher's frame, and on being a stack sample."""
        ev = threading.Event(); inside = threading.Event()
        def probe():
            inside.set(); ev.wait(10)
        th = threading.Thread(target=lambda: km._job_stage("probe", probe), name="probe-thread", daemon=True)
        th.start(); self.assertTrue(inside.wait(5))
        try:
            st, snap = self._req("GET", "/perf?stacks=1")
        finally:
            ev.set(); th.join(5)
        self.assertEqual(st, 200)
        rows = snap["stacks"]
        self.assertIsInstance(rows, dict, "?stacks=1 fills the slot the plain snapshot leaves null")
        self.assertTrue(rows and all(set(r) == {"self", "stage", "frames"} for r in rows.values()), list(rows.items())[:1])
        key = "%d other" % th.ident                                         # a test-only name is outside the register: the kind
        self.assertIn(key, rows, sorted(rows))                              #  reads other, the ident finds the row (T358's case)
        mine = rows[key]
        self.assertEqual(mine["stage"], "jobs.probe", mine)
        self.assertTrue(any(f.startswith("probe (") for f in mine["frames"]), mine["frames"])       # the thread's own function,
        #                                                                                                on the stack since inside.set()
        self.assertTrue(any(f.startswith("_job_stage (") for f in mine["frames"]), mine["frames"])   # the kernel's file name is
        #                                                                                                the launcher's here
        self.assertLess(next(i for i, f in enumerate(mine["frames"]) if f.startswith("_job_stage (")),
                        next(i for i, f in enumerate(mine["frames"]) if f.startswith("probe (")),
                        "outermost first: the launcher is outer to the function it runs")
        self.assertIs(mine["self"], False, mine)
        _assert_stack_sample(self, mine)
        self.assertEqual(sum(1 for r in rows.values() if r["self"]), 1, "the answering handler thread is marked once")
        self.assertTrue(all(len(r["frames"]) <= 40 for r in rows.values()))
        self.assertTrue(any(k.endswith(" handler") and rows[k]["self"] for k in rows), "the answering thread's kind is handler: %s" % sorted(rows))
        self.assertNotIn(th.ident, km._STAGE_BY_TID, "the registry row is gone once the job returns")
        st, plain = self._req("GET", "/perf")
        self.assertIsNone(plain["stacks"], "the plain snapshot carries the slot empty, as before")

    def test_the_sample_keys_threads_by_kind_never_by_a_session_name(self):
        """Round one, medium 1: an SDK session thread is named "sdk:<session name>", and the sample's key carried it where
        the reference promised no session content. Keys are "<ident> <kind>", the kind _thread_kind's: a word from the register
        beside _PERF_ROUTE_SEGMENTS (a registered prefix before the convention's separator, a registered constant name, the fixed
        forms for Python's default names, the HTTP server's threads and the main thread) or `other` (2026-09-18)."""
        gate = threading.Event()
        th = threading.Thread(target=gate.wait, name="sdk:notes-api-web", daemon=True); th.start()
        try:
            rows = km._thread_stacks()
        finally:
            gate.set(); th.join(5)
        self.assertIn("%d sdk" % th.ident, rows, sorted(rows))
        self.assertNotIn("notes-api-web", json.dumps(rows), "no session name anywhere in the sample")
        self.assertEqual((km._thread_kind("sdk-intr:web"), km._thread_kind("Thread-12 (process_request_thread)"), km._thread_kind("pusher"),
                          km._thread_kind("MainThread"), km._thread_kind(None)), ("sdk-intr", "handler", "pusher", "main", "other"))
        # round two: every identity-bearing worker follows kind:payload; the register (2026-09-18): a default name reads thread,
        # its target function being the row's own fourth frame, and a judge pool's worker carries the kind of the thread that
        # built the pool, a nested pool and one built on a request handler included
        self.assertEqual((km._thread_kind("codex:notes-api-web"), km._thread_kind("end-host:11111111"), km._thread_kind("peer:TESTHOST")),
                         ("codex", "end-host", "peer"))
        self.assertEqual((km._thread_kind("Thread-7 (_ask_poll)"), km._thread_kind("Thread-9 (serve_forever)"), km._thread_kind("Thread-3")),
                         ("thread", "thread", "thread"), "a default name is the register's word for it, never the target's text")
        self.assertEqual((km._thread_kind("judge-index_2"), km._thread_kind("ThreadPoolExecutor-0_4"), km._thread_kind("judge-jobs_0"),
                          km._thread_kind("judge-judge-index_2_0"), km._thread_kind("judge-Thread-4 (process_request_thread)_1")),
                         ("judge-index", "pool", "judge-jobs", "judge-judge-index", "judge-handler"))
        # outside the register: a prefix the convention never named, a session name spelled without the separator, a pool
        # built on an unregistered thread, a library's watchdog named with a test path, the empty name
        self.assertEqual((km._thread_kind("watchdog:notes-api-web"), km._thread_kind("notes-api-web"), km._thread_kind("judge-nope_0"),
                          km._thread_kind("pytest_timeout tests/test_perf_stats.py::Case::test"), km._thread_kind("")),
                         ("other",) * 5, "a name outside the register reads other")
        gate = threading.Event()
        th = threading.Thread(target=gate.wait, daemon=True); th.start()   # unnamed: Python's "Thread-N (wait)"
        try:
            rows = km._thread_stacks()
        finally:
            gate.set(); th.join(5)
        self.assertIn("%d thread" % th.ident, rows, sorted(rows))

    def test_every_named_thread_site_maps_to_a_kind_without_an_identity(self):
        """Round two, medium 1, and round three's medium 1: a census of every thread and pool construction site in the kernel,
        every module the kernel loads in-process (the backends, the judge, the credentials helper) and the postal service,
        walked with the ast module (a regex could not cross a newline and missed five named sites, the Codex worker's among
        them). The register beside _PERF_ROUTE_SEGMENTS is held equal to the census both ways (2026-09-18, after a library's
        watchdog thread reached CI's served sample by name): a constant name must be a word of _THREAD_KINDS, so a new kernel
        thread kind the sample would read as `other` is caught here, and every word there must be a name some site starts, so a
        retired thread leaves no dead word; a name with a dynamic part (a session name, a sid, a host) must carry it after the
        convention's separator with a prefix in _THREAD_KIND_PREFIXES, held equal to the census the same way, so _thread_kind
        keeps the prefix and drops the payload. A Thread renamed after construction (`<thread>.name = "..."`, the Codex handshake
        clock) is a site too when the name is a constant; a dynamic rename cannot be told from a session object's name field
        statically and is left to the fold, which reads it `other`. A name built any other way fails, and so does a name the
        census cannot see: a Thread's positional name (its third positional argument), a Timer with a positional beyond its
        interval and function, keywords passed through **kwargs, or an aliased constructor (an assignment whose value is one of
        the constructors; ctor_of resolves Name and Attribute spellings only, so an alias would hide every site built through
        it). Every kind family the census derives must appear in the reference's kind list, so a new kind cannot ship
        undocumented."""
        import ast, re
        root = os.path.dirname(BIN)
        files = [os.path.join(root, "kernel", f) for f in ("kernel.py", "sdk_backend.py", "codex_backend.py", "session_host.py",
                                                            "judge.py", "credentials.py")] + \
                [os.path.join(root, "postal", "postal_service.py")]
        CTORS = {"Thread", "Timer", "ThreadPoolExecutor", "_TimedPool"}
        def ctor_of(call):
            f = call.func
            n = f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else None)
            return n if n in CTORS else None
        def static_prefix(v):
            """(the constant text before any dynamic part, whether the name has a dynamic part), or None for an unreadable expression."""
            if isinstance(v, ast.Constant) and isinstance(v.value, str):
                return v.value, False
            if isinstance(v, ast.JoinedStr):
                first = v.values[0] if v.values else None
                return (first.value if isinstance(first, ast.Constant) else ""), any(isinstance(p, ast.FormattedValue) for p in v.values)
            if isinstance(v, ast.BinOp) and isinstance(v.op, (ast.Mod, ast.Add)) and isinstance(v.left, ast.Constant) and isinstance(v.left.value, str):
                return v.left.value.split("%")[0], True
            if isinstance(v, ast.Call) and isinstance(v.func, ast.Attribute) and v.func.attr == "format" and isinstance(v.func.value, ast.Constant):
                return v.func.value.value.split("{")[0], True
            return None, None
        sites, named, bad, dyn_kinds, consts, per_file = 0, [], [], set(), set(), {}
        for f in files:
            src = open(f, encoding="utf-8").read()
            tree = ast.parse(src)
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module == "threading" and any(a.name in CTORS and a.asname for a in node.names):
                    bad.append(("%s:%d" % (os.path.basename(f), node.lineno), "a constructor imported under an alias the census cannot follow", ""))
                if isinstance(node, ast.Import) and any(a.name == "threading" and a.asname for a in node.names):
                    bad.append(("%s:%d" % (os.path.basename(f), node.lineno), "the threading module imported under an alias the census cannot follow", ""))
                if isinstance(node, ast.Assign) and isinstance(node.value, (ast.Name, ast.Attribute)) and ctor_of(ast.Call(func=node.value, args=[], keywords=[])) \
                        and not all(isinstance(tg, ast.Name) and tg.id in CTORS for tg in node.targets):   # judge.py rebinds ThreadPoolExecutor
                    bad.append(("%s:%d" % (os.path.basename(f), node.lineno), "a constructor aliased into a name the census cannot follow", ast.dump(node.value)[:60]))   # to its timed subclass: both names are constructors, so every site stays visible
                if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Attribute) \
                        and node.targets[0].attr == "name" and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                    label = "%s:%d" % (os.path.basename(f), node.lineno)    # a Thread renamed after construction with a constant
                    named.append(label); consts.add(node.value.value)        #  (the Codex handshake clock): a register word too
                    if km._thread_kind(node.value.value) != node.value.value:
                        bad.append((label, "a constant rename outside the register (_THREAD_KINDS): the sample would read it other", node.value.value))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call) or ctor_of(node) is None:
                    continue
                sites += 1; per_file[os.path.basename(f)] = per_file.get(os.path.basename(f), 0) + 1
                label = "%s:%d" % (os.path.basename(f), node.lineno)
                if ctor_of(node) == "Thread" and len(node.args) >= 3:
                    bad.append((label, "a positional name the census cannot read: pass name= as a keyword", "")); continue
                if ctor_of(node) == "Timer" and len(node.args) > 2:
                    bad.append((label, "a Timer with a positional beyond its interval and function: spell args, kwargs and any name as keywords", "")); continue
                if any(k.arg is None for k in node.keywords):
                    bad.append((label, "keywords through **kwargs may carry a name the census cannot read: spell them", "")); continue
                kw = next((k for k in node.keywords if k.arg in ("name", "thread_name_prefix")), None)
                if kw is None:
                    continue                                     # a default name: the rule keeps the target function
                static, dynamic = static_prefix(kw.value)
                named.append(label)
                if static is None:
                    bad.append((label, "a name built from an expression the census cannot read", ast.dump(kw.value)[:80])); continue
                if dynamic:
                    if not static.endswith(km._THREAD_NAME_SEP):
                        bad.append((label, "a dynamic part without the kind:payload separator", static)); continue
                    kind = km._thread_kind(static + "notes-api-web")
                    if kind != static[:-1] or "notes" in kind:
                        bad.append((label, "the payload survives", kind))
                    dyn_kinds.add(kind)                          # a kind with a payload is a documented family (sdk, codex, ...)
                else:
                    kind = km._thread_kind(static if kw.arg == "name" else static + "_0")   # a pool prefix names its workers <prefix>_N
                    if kw.arg == "name":
                        consts.add(static)
                    if kind != static or re.search(r"[/\\]|[0-9a-f]{8}-", static):
                        bad.append((label, "a constant name outside the register (_THREAD_KINDS): the sample would read it other", kind))
        self.assertGreaterEqual(sites, 60, "the census walked the construction sites: %d" % sites)
        self.assertGreaterEqual(len(named), 23, "the census found every named site, the multi-line ones included: %r" % named)
        self.assertTrue(any(l.startswith("codex_backend.py:") for l in named), "the Codex worker's site is walked: %r" % named)
        self.assertGreaterEqual(per_file.get("credentials.py", 0), 1, "the credentials helper's Timer is a construction site the census walked: %r" % per_file)
        self.assertGreaterEqual(per_file.get("judge.py", 0), 7, "the judge tiers' pools are construction sites the census walked: %r" % per_file)
        self.assertEqual(bad, [], "every named thread maps to a register word with no identity in it")
        self.assertEqual(sorted(km._THREAD_KINDS - consts), [], "every register word is a constant name some site starts: a retired thread leaves no dead word")
        self.assertEqual(sorted(km._THREAD_KIND_PREFIXES - dyn_kinds), [], "every registered prefix is a kind some site spells with a payload")
        self.assertEqual(sorted(dyn_kinds - km._THREAD_KIND_PREFIXES), [], "every kind spelled with a payload is a registered prefix")
        self.assertTrue(km._THREAD_KINDS.isdisjoint(km._THREAD_KIND_PREFIXES) and km._THREAD_KIND_FIXED.isdisjoint(km._THREAD_KINDS | km._THREAD_KIND_PREFIXES)
                        and "other" not in km._THREAD_KIND_WORDS, "the register's three parts are disjoint, and other is the fold's word alone")
        ref = open(os.path.join(root, "docs", "reference.md"), encoding="utf-8").read()
        para = ref[ref.index("- `stacks`: every live thread's stack"):]
        para = para[:para.index("\n- ", 10)]
        undocumented = sorted(k for k in dyn_kinds if "`%s`" % k not in para)
        self.assertEqual(undocumented, [], "every kind family with a payload (sdk, codex, end-host, peer, ...) is in the reference's kind list; a constant name is its own kind")
        self.assertGreaterEqual(len(dyn_kinds), 5, sorted(dyn_kinds))

    def test_the_judge_pools_workers_carry_their_tier(self):
        """Round three, low 2: the pin on the pool prefix was a substring check on the source; the behaviour is pinned instead:
        a _TimedPool built on a thread named like a tier gives its workers names whose kind is judge-<tier>."""
        jd = km.jd
        out = []
        def tier():
            with jd._TimedPool(max_workers=1) as ex:
                out.append(ex.submit(lambda: threading.current_thread().name).result(5))
        th = threading.Thread(target=tier, name="index"); th.start(); th.join(10)
        self.assertEqual(len(out), 1, out)
        self.assertEqual(km._thread_kind(out[0]), "judge-index", out[0])

    def test_the_sample_never_reads_source_through_linecache(self):
        """Round one, low 1: extract_stack read and cached every source file in every stack (4 MB of kernel) for line text
        the sample never prints; the frame walk touches no file."""
        import linecache
        linecache.clearcache()
        km._thread_stacks()
        self.assertEqual([k for k in linecache.cache if k.endswith(("romp-kernel", "kernel.py", "threading.py"))], [],
                         "the sample loaded source it does not print")

    def test_the_stage_registry_follows_the_marks(self):
        """`_set_stage` writes the thread-local the readers consult and the by-ident row the sample reads, and clears the row at
        None; the push decorator and the job thunk both go through it."""
        tid = threading.get_ident()
        km._set_stage(None)
        self.assertNotIn(tid, km._STAGE_BY_TID)
        km._job_stage("probe", lambda: self.assertEqual((km._current_read_stage(), km._STAGE_BY_TID.get(tid)), ("jobs.probe", "jobs.probe")))
        self.assertEqual((km._current_read_stage(), km._STAGE_BY_TID.get(tid)), (None, None))
        km._stage_marked("marked")(lambda: self.assertEqual(km._STAGE_BY_TID.get(tid), "marked"))()
        self.assertNotIn(tid, km._STAGE_BY_TID)

    def test_post_perf_requires_the_token(self):
        st, body = self._req("POST", "/perf", {"log": True}, token=False)
        self.assertEqual(st, 403)
        self.assertFalse(km._PERF, "a refused POST flips nothing")

    def test_post_perf_flips_the_log_and_perf_emits_only_after(self):
        buf = io.StringIO()
        with redirect_stderr(buf):
            km._perf("probe", n=1)
        self.assertEqual(buf.getvalue(), "", "off before the POST")
        with redirect_stderr(io.StringIO()):                 # the route's own "log on" notice goes to stderr
            st, r = self._req("POST", "/perf", {"log": True})
        self.assertEqual((st, r), (200, {"ok": True, "log": True}))
        self.assertTrue(km._PERF)
        buf = io.StringIO()
        with redirect_stderr(buf):
            km._perf("probe", n=1)
        self.assertEqual(buf.getvalue(), "romp-perf probe n=1\n", "on after the POST, no restart")
        st, snap = self._req("GET", "/perf")
        self.assertIs(snap["log"], True, "the snapshot reports the switch")
        with redirect_stderr(io.StringIO()):
            st, r = self._req("POST", "/perf", {"log": False})
        self.assertEqual((st, r), (200, {"ok": True, "log": False}))
        buf = io.StringIO()
        with redirect_stderr(buf):
            km._perf("probe", n=1)
        self.assertEqual(buf.getvalue(), "")

    def test_post_perf_refuses_a_malformed_body(self):
        for body in ({}, {"log": "yes"}, {"log": 1}, [], "log"):
            st, r = self._req("POST", "/perf", body)
            self.assertEqual(st, 400, body)
            self.assertFalse(r["ok"])
        self.assertFalse(km._PERF)

    def test_the_routes_sit_after_the_gate_in_the_source(self):
        get = inspect.getsource(km.Handler.do_GET)
        gate = "ok, self._set_cookie, why = self._authorize(q)"
        self.assertEqual(get.count(gate), 1)
        self.assertGreater(get.index('p == "/perf"'), get.index(gate))
        post = inspect.getsource(km.Handler.do_POST)
        self.assertEqual(post.count(gate), 1)
        self.assertGreater(post.index('u.path == "/perf"'), post.index(gate))

    def test_every_request_is_timed_per_method_and_path(self):
        before = self._http("GET /version")
        with _HttpWatch() as w:
            self._req("GET", "/version?probe=1", token=False)   # an exempt route counts too
            self._req("GET", "/version", token=False)
            self.assertTrue(w.wait_for("GET /version", 2), "both records landed (waited on, not raced)")
        after = self._http("GET /version")
        self.assertEqual(after["count"], before["count"] + 2)
        self.assertGreater(after["ms"], before["ms"])

    def test_head_and_options_are_counted_too(self):
        head0, opt0, other0 = self._http("HEAD /file"), self._http("OPTIONS /perf"), self._http("other")
        with _HttpWatch() as w:
            self._req("HEAD", "/file")                          # do_HEAD's one route (the PDF chip's existence probe)
            self._req("HEAD", "/version", token=False)          # no HEAD route: counted, under `other` (2026-09-18)
            self._req("OPTIONS", "/perf")
            self.assertTrue(w.wait_for("HEAD /file", 1))
            self.assertTrue(w.wait_for("other", other0["count"] + 1))
            self.assertTrue(w.wait_for("OPTIONS /perf", 1))
        self.assertEqual(self._http("HEAD /file")["count"], head0["count"] + 1, "a /file probe storm is visible")
        self.assertEqual(self._http("other")["count"], other0["count"] + 1, "a HEAD of a route do_HEAD does not serve counts as other")
        self.assertEqual(self._http("OPTIONS /perf")["count"], opt0["count"] + 1, "a preflight burst is visible")

    def test_a_ws_upgrade_is_counted_when_it_arrives(self):
        # the wrapper on a stand-in handler: for a /ws path the count is taken BEFORE the handler runs,
        # since do_GET returns only when the socket closes, and no time is added after
        seen = {}

        class H:
            path = "/ws?token=x"
            command = "GET"

            @km._perf_http_timed
            def do_GET(self):
                seen["during"] = PerfRoutes._http("GET /ws")["count"]
        before = self._http("GET /ws")
        H().do_GET()
        after = self._http("GET /ws")
        self.assertEqual(seen["during"], before["count"] + 1, "counted at arrival, not at socket close")
        self.assertEqual(after["count"], before["count"] + 1, "and not a second time in the finally")
        self.assertEqual(after["ms"], before["ms"], "a socket's lifetime is not a request time")



class StacksField(unittest.TestCase):
    """The perf route's `stacks` (T358, a debugging aid behind ROMP_PERF_STACKS; T401's sample): every thread's frames, keyed by
    the thread's ident WITH its kind, so two workers sharing a kind stay two entries (the duplicate-worker case the aid is for),
    two threads outside the register, both `other`, included; None without the switch."""
    def test_two_threads_sharing_a_name_are_two_entries(self):
        """The innermost frame is not pinned (2026-09-19): a thread parked on an Event is sampled at wait or at the lock acquire
        inside it, so each row need only be a stack sample of a live thread (_assert_stack_sample)."""
        import threading
        from unittest import mock
        gate = threading.Event()
        ths = [threading.Thread(target=gate.wait, name="ws-send", daemon=True) for _ in range(2)]   # a register kind, shared
        for t in ths:
            t.start()
        try:
            with mock.patch.dict(os.environ, {"ROMP_PERF_STACKS": "1"}):
                snap = km._PerfStats().snapshot()
            idents = {t.ident for t in ths}
            keys = [k for k in (snap.get("stacks") or {}) if int(k.split()[0]) in idents]
            self.assertEqual(len(keys), 2, "one entry per thread: %s" % sorted(snap.get("stacks") or {}))
            self.assertTrue(all(k.endswith(" ws-send") for k in keys), "the kind carried: %s" % keys)
            self.assertEqual(len(set(keys)), 2, "keyed by ident: distinct")
            self.assertTrue(all(str(t.ident) in k for t, k in zip(sorted(ths, key=lambda t: t.ident), sorted(keys, key=lambda k: int(k.split()[0])))))
            for k in keys:                                                   # the value shape (T401): the row the served
                row = snap["stacks"][k]                                      #  boot diagnostic and romp perf stacks read
                self.assertEqual(set(row), {"self", "stage", "frames"}, row)
                self.assertIs(row["self"], False); self.assertIsNone(row["stage"])
                _assert_stack_sample(self, row)
        finally:
            gate.set()
            for t in ths:
                t.join(timeout=5)
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ROMP_PERF_STACKS", None)
            self.assertIsNone(km._PerfStats().snapshot()["stacks"], "None without the switch")

    def test_two_threads_outside_the_register_are_two_entries_keyed_other(self):
        """2026-09-18: two threads whose names the register does not hold (a library's watchdog named with a test path, a worker
        named with an id) both read `other` and stay two rows, the ident half of the key keeping them apart; neither name
        reaches the sample. No frame is pinned (2026-09-19): a thread parked on an Event is sampled at wait, at the lock acquire
        inside it (Condition.__enter__ on the way into Event.wait), at a helper wait calls (_release_save, _is_owned), or in run
        before wait, and the test never waits for the threads to reach any of them. The pin that stood here read the innermost
        frame as `wait (` and went red on the free-threaded 3.14 build in three module runs of ten. What each row must show is
        that it is a stack sample of a live thread other than the sampler: at least one frame, each in the sampler's
        "function (file:line)" form, every file one the standard library or this repo ships (_assert_stack_sample), self false
        and no stage mark."""
        gate = threading.Event()
        names = ("pytest_timeout tests/test_perf_stats.py::StacksField::test_x", "worker 11111111-2222-3333-4444-555555555555")
        ths = [threading.Thread(target=gate.wait, name=n, daemon=True) for n in names]
        for t in ths:
            t.start()
        try:
            rows = km._thread_stacks()
        finally:
            gate.set()
            for t in ths:
                t.join(timeout=5)
        idents = {str(t.ident) for t in ths}
        keys = sorted(k for k in rows if k.split()[0] in idents)                     # the entries whose ident half is a planted thread's
        self.assertEqual(len(keys), 2, "two threads, two entries: %s" % sorted(rows))
        self.assertEqual(keys, sorted("%s other" % i for i in idents), "each keyed by its own ident and `other`")
        for k in keys:
            row = rows[k]
            self.assertIs(row["self"], False, row); self.assertIsNone(row["stage"], row)
            _assert_stack_sample(self, row)
        text = json.dumps(rows)
        self.assertFalse(any(n in text for n in names), "no planted name in the sample")

class UserAgentKind(unittest.TestCase):
    """_ua_kind: the browser kind of a dial's User-Agent header, one of WS_UA_KINDS, never the header and never a version
    (pusher.clients.byKind, 2026-09-18). The strings below are invented in the shape each browser publishes (the public
    User-Agent templates), never recorded headers."""

    IPHONE = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
    IPAD = "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
    IPHONE_CHROME = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/120.0.0.0 Mobile/15E148 Safari/604.1"
    IPHONE_FIREFOX = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) FxiOS/120.0 Mobile/15E148 Safari/605.1.15"
    MAC_SAFARI = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
    MAC_CHROME = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    MAC_FIREFOX = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0"
    WINDOWS_CHROME = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    WINDOWS_EDGE = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
    ANDROID_CHROME = "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
    ANDROID_FIREFOX = "Mozilla/5.0 (Android 14; Mobile; rv:120.0) Gecko/120.0 Firefox/120.0"
    LINUX_FIREFOX = "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0"
    CURL = "curl/8.5.0"
    WSLIB = "Python/3.12 websockets/12.0"

    def test_each_shape_reads_its_kind(self):
        cases = {self.IPHONE: "safari-ios", self.IPAD: "safari-ios",
                 self.IPHONE_CHROME: "safari-ios", self.IPHONE_FIREFOX: "safari-ios",   # every iOS browser is WebKit: the device token wins
                 self.MAC_SAFARI: "safari-mac", self.MAC_CHROME: "chrome", self.MAC_FIREFOX: "firefox",
                 self.WINDOWS_CHROME: "chrome", self.WINDOWS_EDGE: "chrome", self.ANDROID_CHROME: "chrome",
                 self.ANDROID_FIREFOX: "firefox", self.LINUX_FIREFOX: "firefox",
                 self.CURL: "other", self.WSLIB: "other"}
        for ua, kind in cases.items():
            self.assertEqual(km._ua_kind(ua), kind, ua)

    def test_no_header_is_none_and_every_answer_is_in_the_fixed_list(self):
        self.assertEqual(km._ua_kind(None), "none")
        self.assertEqual(km._ua_kind(""), "none")
        for ua in (self.IPHONE, self.MAC_SAFARI, self.MAC_CHROME, self.LINUX_FIREFOX, self.CURL, "", None,
                   "anything/1.0 (with; tokens) at all", "Chrome", "Safari/605.1.15"):
            self.assertIn(km._ua_kind(ua), km.WS_UA_KINDS, repr(ua))
        self.assertEqual(km._ua_kind("Safari/605.1.15"), "other", "a Safari token with no Macintosh is not a Mac's Safari")

    def test_the_header_and_its_version_never_reach_the_kind(self):
        """A served key is a leak vector: the classification is a fixed word, never a slice of the header."""
        for ua in (self.MAC_CHROME, self.IPHONE, self.CURL, self.WINDOWS_EDGE):
            kind = km._ua_kind(ua)
            self.assertNotIn("/", kind)
            self.assertNotIn(".", kind)
            self.assertFalse(any(tok in kind for tok in ua.split()), "a header token in the served kind: %r" % kind)
        self.assertEqual(km._ua_kind("Chrome/120.0.0.0"), "chrome", "a version-bearing token names a kind, no version")

    def test_the_safari_ios_rule_is_the_browsers_own(self):
        """The kernel's first rule mirrors ui/webview/perf-telemetry.ts uaClass (an iPhone, iPad or iPod token), so a frame
        counted under safari-ios is one the browser's own telemetry classes the same; the browser also reads an iPad's
        desktop-mode Macintosh header from its touch points, which a header alone cannot, so that iPad reads safari-mac
        here, the documented limit."""
        ts = open(os.path.join(os.path.dirname(HERE), "ui", "webview", "perf-telemetry.ts"), encoding="utf-8").read()
        m = re.search(r'if \(/(iPhone\|iPad\|iPod)/\.test\(ua\)[^\n]*return "safari-ios";', ts)
        self.assertIsNotNone(m, "the browser's safari-ios rule moved: re-mirror it")
        rx, kind = km._UA_KIND_RULES[0]
        self.assertEqual((rx.pattern, kind), (m.group(1), "safari-ios"))
        self.assertEqual(km._ua_kind(self.MAC_SAFARI), "safari-mac")

    def test_a_client_carries_the_kind_and_not_the_header(self):
        client, _q, _lock = km._new_ws_client("chat", "w1", object(), start_sender=False, ua=self.IPHONE)
        self.assertEqual(client["uaKind"], "safari-ios")
        self.assertFalse(any(isinstance(v, str) and "AppleWebKit" in v for v in client.values()), "the header is not kept")
        bare, _q, _lock = km._new_ws_client("chat", "w1", object(), start_sender=False)
        self.assertEqual(bare["uaKind"], "none", "no header given: none, the same word a relay's splice or a pipe reads")

    def test_the_handshake_hands_the_header_to_the_client(self):
        """Executed, not read as source: two real upgrades through the Handler on a loopback server, one carrying an
        iPhone's User-Agent line and one bare. The client each handshake registers reads safari-ios, and none, and no
        value of either record carries the header's text (a served key is a leak vector, and the record is what /perf
        and the client-diag rows read from). The sender thread's count of what it wrote is executed in
        tests/test_wire_once_per_build.py (PerClientWireCounters)."""
        srv = ThreadingHTTPServer(("127.0.0.1", 0), km.Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        port = srv.server_address[1]
        tag = os.urandom(4).hex()
        w_ios, w_bare = "ua-ios-" + tag, "ua-bare-" + tag
        socks = []
        try:
            for wid, ua in ((w_ios, self.IPHONE), (w_bare, None)):
                status, s = _ws_dial(port, "/ws?app=chat&wid=%s&token=%s" % (wid, km.TOKEN), ua=ua)
                socks.append(s)
                self.assertEqual(status, 101, "the upgrade is accepted: " + wid)
            clients = _registered_clients({w_ios, w_bare}, want=2)   # registered after the 101 leaves, on the handler thread
            self.assertEqual(set(clients), {w_ios, w_bare}, "both handshakes registered their client")
            self.assertEqual(clients[w_ios]["uaKind"], "safari-ios", "the dial's User-Agent classed at the handshake")
            self.assertEqual(clients[w_bare]["uaKind"], "none", "no header: the word a relay's splice or a pipe reads")
            for wid, client in clients.items():
                strs = [v for v in client.values() if isinstance(v, str)]
                for needle in (self.IPHONE, "Mozilla", "AppleWebKit", "Safari/", "Version/", "iPhone"):
                    self.assertFalse(any(needle in v for v in strs), "the header's text in the %s record: %r" % (wid, strs))
        finally:
            for s in socks:
                try:
                    s.close()
                except OSError:
                    pass
            gone = _registered_clients({w_ios, w_bare}, want=0)   # the handler's finally retires each client at its socket's close
            srv.shutdown()
            srv.server_close()
        self.assertEqual(gone, {}, "both clients retired from _clients once their sockets closed")


class ServedSnapshotIsPasteSafe(unittest.TestCase):
    """The served GET /perf snapshot carries no absolute path, no session id (a uuid or a 32-hex token) and no
    verbatim session text, in any key or string value, so a copy of it can be pasted in public (an issue, a chat)
    and still read as diagnosis (2026-09-18). Every leak this test plants goes in through a writer the collector
    takes from the machine or from a client: the JSONL reader's per-path byte table (a transcript under a home
    directory), the judges' child's done line (an exception message naming that path), the per-session chat timer
    and the cold-parse table (sids), the http table (a glossary term, a scanner's path with a sid in it, an
    attached host's name, a home path), a client's declared app name, on its connect push and on a frame its
    sender wrote, and the stack sample's stage mark (a request handler's, made from the in-flight URL through
    _route_seg, with the sample switched on so the `stacks` block rides in the walk and no served block sits outside
    it). Keys are the leak vectors, so every dict
    key must fit an identifier grammar (letters, digits, underscore, dot, dash) except inside the blocks named
    below: `http` (a member of the image of _perf_http_key: METHOD /path over the checked-in route list, the
    families, the remote star form, or `other`; a character grammar stood here first and admitted any path-shaped
    key), `stacks` (an ident and a kind), and the tables whose keys join fixed
    identifiers with `:` and `<-` (JOINED_KEY_BLOCKS: a stage mark, a reader kind and a calling function in the byte
    tables; a phase and a reason code in the assembly counters; the same tables again under judge.child). A string
    value is held to the same rules and to two more: no free text (whitespace) outside the frame strings of the
    stack sample, which have their own grammar, and no 40-hex token (a checkpoint document's name). The walk
    runs over a fresh collector's snapshot(), the same function the route serves, so the module-global counters other
    test modules filled in this process are walked too; the planted reads are removed after."""

    # The served snapshot's key grammar is the kernel's own (_PERF_IDENT without the cap): no colon, so it is
    # STRICTER than the export's browser grammar (cli/perf_public.py IDENT, which allows `:`). The walk itself is the
    # shared module's (perf_public.paste_problems), which `romp perf export --public` runs over its own output: the
    # http check (membership in the register's image, perf_public.http_key_ok over the module's checked-in copy of the
    # register, so the walk runs the same against any kernel tree), the stack sample's key and frame grammars, the
    # joined-key grammar, and the leak detectors (a uuid, a 32-hex and a 40-hex token, an absolute path, free text,
    # the planted strings). This test hands it the stricter ident and the stack sample's key grammar built from the
    # kernel's register: the module's own is a character grammar, because the export drops the block (DENY_KEYS) and
    # the cli never loads the kernel; the served walk is where the register's words are the only kinds allowed.
    IDENT = re.compile(r"^[A-Za-z0-9_.-]+$")
    STACKS_KEY = re.compile(r"^[0-9]+ (?:(?:judge-)*(?:%s)|other)$" % "|".join(sorted(map(re.escape, km._THREAD_KIND_WORDS))))
    #                                                              the stack sample's "<ident> <kind>" (_thread_stacks): a word of
    #                                                              the kernel's register (a judge pool's worker composes one
    #                                                              with judge-) or other, nothing else: a thread's name is never
    #                                                              a key (2026-09-18: a library's watchdog named with a test path
    #                                                              reached CI's sample verbatim)
    JOINED_KEY_BLOCKS = pp.JOINED_KEY_BLOCKS

    def _paste_problems(self, doc):
        """The shared walk with this class's grammars: the stricter ident, the register's stack keys, the planted strings.
        Each finding is a perf_public.Problem (kind, is_key, path, text, depth); str(problem) is the line a failure prints."""
        return pp.paste_problems(doc, planted=self.planted, ident=self.IDENT, stacks_key=self.STACKS_KEY)

    @staticmethod
    def _http_keys():
        """The image of _perf_http_key over the register: "METHOD /path" for every method's routes (OPTIONS, the union,
        included), "METHOD /family" for the collapsed families, "METHOD /remote/*<op>" for the same method's routes, and
        `other`. The fold returns nothing else (its last line spells a method and one of those paths, or `other`), and
        test_the_http_key_set_is_the_image_of_the_fold reaches every member with one request and holds every member to
        the shared module's membership test (perf_public.http_key_ok, over its checked-in copy of the register), so the
        walk's http check is exact: no path-shaped key the fold never makes passes it."""
        keys = {"other"}
        for method, routes in km._PERF_HTTP_ROUTES.items():
            keys.update(method + " " + p for p in routes)
            keys.update(method + " " + fam for fam in km._PERF_HTTP_FAMILIES)
            keys.update(method + " /remote/*" + p for p in routes)
        return keys

    def setUp(self):
        self.st = km._PerfStats()
        self.em = km.em
        self.home = os.path.join(tempfile.mkdtemp(), "home", "tester")          # an absolute home path under a temp dir
        self.addCleanup(shutil.rmtree, os.path.dirname(os.path.dirname(self.home)), True)
        proj = os.path.join(self.home, ".claude", "projects", "-home-tester-code-notes-api")
        state = km.jd.STATE
        self.reads = {os.path.join(proj, SID + ".jsonl"): 4096,                                       # the leaf
                      os.path.join(proj, SID, "subagents", "agent-%s.jsonl" % SID[:8]): 512,          # a subagent's
                      str(state / "states" / (SID + ".jsonl")): 256,                                  # its states log
                      str(state.parent / "timeline" / "messages.jsonl"): 128,                          # the postal log
                      str(state / "checkpoints" / ("a" * 40 + ".json")): 64,                           # a checkpoint document
                      os.path.join(self.home, "notes", "scratch.jsonl"): 32}                           # anything else
        self.term = "Quarterly Roadmap"
        self.app = "<b>%s</b> %s" % (SID, self.home)
        self.first = "OSError: [Errno 2] No such file or directory: '%s'" % next(iter(self.reads))
        self.planted = [SID, SID[:8], self.home, "TESTHOST", self.term, self.first, self.app, "-home-tester-code-notes-api"]

    def _plant(self):
        by_kind = getattr(self.em, "read_bytes_by_kind", None)   # the process's other reads (a peer module's, under xdist): deltas
        self.reads_before = by_kind() if by_kind else collections.defaultdict(lambda: {"bytes": 0})   # below. A tree before the
        #                                                        fix has no per-kind table: a zeroed one, so the walk runs first
        #                                                        and the failure names every leaking site, not this attribute
        for path, n in self.reads.items():
            self.em._count_read(path, n)
        self.addCleanup(self._unplant_reads)
        st = self.st
        st.judge_child_done({"op": "done", "seq": 7, "wallMs": 12.5, "tierStarts": 2, "tierCpuMs": 3.0, "workerCpuMs": 4.0,
                             "failures": {"count": 1, "first": self.first}, "recovered": False,
                             "recordCache": {"entries": 1, "wholeReads": {"leaf<-_parse": {"count": 1, "bytes": 5}},
                                             "wholeReadsByStage": {"push:leaf<-_parse": {"count": 1, "bytes": 5}}},
                             "asmCheckpoint": {"restored": 1, "hydratedBy": {"_unit_text<-build_session": 10},
                                               "hydratedByStage": {"push:_unit_text<-build_session": 10}},
                             "parses": {"misses": 1, "hits": 0}, "goalIo": {"loads": 1}}, pid=4242)
        st.build_chat(False, 0.100, active=True, sid=SID, nbytes=4096)
        st.build_chat(True, sid=SID)
        st.parse(SID, 4096)
        for method, path in (("GET", "/glossary/" + self.term), ("GET", "/nope/" + SID), ("GET", "/remote/TESTHOST/sessions"),
                             ("GET", "/remote/TESTHOST/" + SID), ("GET", "/dist/render.js"), ("GET", "/perf"), ("POST", "/send"),
                             ("GET", self.home), ("HEAD", "/file"), ("OPTIONS", "/perf")):
            st.http_request(km._perf_http_key(method, path), 0.001)
        st.http_request(km._perf_http_key("GET", "/ws"), None)
        st.connect_push("chat", 0.010)
        st.connect_push(self.app, 0.010)
        st.client_send("chat", "chrome", 10, 0.001)
        st.client_send(self.app, "Mozilla/5.0 " + self.home, 10, 0.001)   # the kind arrives classed; a header here reads other
        st.send(("chat", SID), "full", 10)
        st.send(("status", SID), "delta", 5)
        st.cycle(0.050)
        # the push stages by their writer (2026-09-18), all three routes populated so the walk covers them: a write under a
        # request handler's route mark from this thread while it owns no cycle, neither a connect push nor the cycle's
        # owner, to stagesForeign; a connect push's, under the "connect" mark, to pusher.connectPush.stagesMs; and the
        # pusher's, under the "push" mark _push carries when the pusher calls it, from this thread once it owns the
        # pusher's cycle (below: the mark alone is no owner), to the flat row. Every key is a stage literal spelled in the
        # kernel's source: stage() is never called with a client's or a user's text, so no planted string can reach any of
        # the three; the walk holds them to the grammar anyway
        km._stage_marked("http.GET.other")(lambda: st.stage("push.feed", 0.004))()
        km._stage_marked("connect")(lambda: (st.stage("push.chat", 0.003), st.stage("push.send.compare", 0.002)))()
        # the two owner-routed blocks (2026-09-18), populated so the walk covers them: a `jobs.` stage from this thread
        # while it owns no cycle lands in stagesForeign, then the same thread as the pusher's owner writes a cycle job
        # into pusher.cycleJobsMs and its push.chat into the flat row. Both keys are the kernel's own literals (a stage
        # name from the STAGES vocabulary, a job name from CYCLE_JOBS), never a client's or a user's text: stage() is
        # called with names spelled in the kernel's source alone, so no planted string can reach either block; the walk
        # holds them to the grammar anyway
        st.stage("jobs.autoNudge.parse", 0.001)
        st.cycle_begin()
        st.stage("jobs.persistCheckpoints", 0.002)
        km._stage_marked("push")(lambda: st.stage("push.chat", 0.010))()

    def _unplant_reads(self):
        with self.em._READ_BYTES_LOCK:
            for path in self.reads:
                self.em._READ_BYTES.pop(path, None)

    def _snapshot_under_a_request(self, path):
        """The snapshot taken while this thread handles a request for `path`: the read runs under the stage-mark decorator
        the do_* methods carry (tests/test_stage_marks.py pins its text on each of the four), over a stand-in with the one
        attribute the route lambda reads, so the mark rides in through _route_seg the way an in-flight request's does; the
        sample's switch is set so `stacks` fills its slot and this thread's row carries the mark."""
        st = self.st
        read = km._stage_marked(lambda req: "http.GET." + km._route_seg(req.path))(lambda req: st.snapshot(ring_all=True))
        with mock.patch.dict(os.environ, {"ROMP_PERF_STACKS": "1"}):
            return read(type("Request", (), {"path": path})())

    def _my_stacks_key(self):
        return "%s %s" % (threading.get_ident(), km._thread_kind(threading.current_thread().name))

    def test_a_thread_named_with_a_path_and_an_id_is_keyed_other_and_the_walk_stays_clean(self):
        """2026-09-18, CI red on every Python cell: pytest-timeout names its watchdog "pytest_timeout <node id>" (the running
        test's path, then ::Class::test), and the sample's colon rule kept the name up to the first "::", so the served key
        read "<ident> pytest_timeout tests/test_perf_stats.py", outside the key grammar; a thread named with a path, a uuid or
        free text by any library reached the snapshot the same way. The kind is a word from the kernel's register or `other`,
        the ident keeping the row its own; the planted name, a node id with a session id and a home path appended, is nowhere
        in the snapshot, and the whole walk stays clean with the thread alive. The frame is not pinned (2026-09-19): a thread
        parked on an Event is sampled at wait or at the lock acquire inside it, so the row is the planted thread's by its key,
        its self false and its empty stage mark, and need only be a stack sample."""
        gate = threading.Event()
        name = "pytest_timeout tests/test_perf_stats.py::ServedSnapshotIsPasteSafe::test_x %s %s" % (SID, self.home)
        th = threading.Thread(target=gate.wait, name=name, daemon=True); th.start()
        try:
            self._plant()
            snap = self._snapshot_under_a_request("/" + SID + "?stacks=1")
        finally:
            gate.set(); th.join(5)
        key = "%d other" % th.ident
        self.assertIn(key, snap["stacks"] or {}, sorted(snap["stacks"] or {}))
        row = snap["stacks"][key]                                            # the planted thread's row, not the sampler's: not
        self.assertIs(row["self"], False, row); self.assertIsNone(row["stage"], row)   # self, no stage mark (this thread's row
        _assert_stack_sample(self, row)                                      #  carries the request's), and a stack sample
        self.assertNotIn(name, json.dumps(snap), "the name is nowhere in the snapshot")
        self.problems = self._paste_problems(snap)
        self.assertEqual(self.problems, [], "%d leak(s) in the served snapshot:\n  %s" % (len(self.problems), "\n  ".join(map(str, self.problems))))
        # the grammar the walk applied is the register's, not the shared module's character one: the planted name as a
        # kind, which the module's own grammar admits, is refused here
        self.assertEqual([p.kind for p in self._paste_problems({"stacks": {"%d probe-thread" % th.ident: {}}})],
                         ["outside the stack sample's key grammar"], "a thread's name is not a kind under the served walk")
        self.assertEqual(pp.paste_problems({"stacks": {"%d probe-thread" % th.ident: {}}}), [], "the module's default admits the token")

    def test_no_key_or_string_in_the_served_snapshot_carries_a_path_an_id_or_planted_text(self):
        self._plant()
        snap = self._snapshot_under_a_request("/" + SID + "?stacks=1")   # a session id as the in-flight URL, the sample on
        self.assertEqual(set(snap), TOP_KEYS, "the walk covers the whole served shape")
        me = self._my_stacks_key()
        self.assertIn(me, snap["stacks"] or {}, "the stack sample rides in the walk under its switch, this thread's row among the rest")
        self.problems = self._paste_problems(snap)
        self.assertEqual(self.problems, [], "%d leak(s) in the served snapshot:\n  %s" % (len(self.problems), "\n  ".join(map(str, self.problems))))
        self.assertEqual(snap["stacks"][me]["stage"], "http.GET.other", "the request's mark carries the fold's word, not the path's")
        # the diagnosis the folds keep: the reads per holder kind, the child's line as a size and a status, the per-session
        # rows by rank, the sessions parsed as a count, the glossary lookups and the remote route as counts
        ck = snap["checkpoints"]
        self.assertEqual({k: v["bytes"] - self.reads_before[k]["bytes"] for k, v in ck["readByKind"].items()},
                         {"leaf": 4096, "agent": 512, "states": 256, "postal": 128, "checkpoint": 64, "other": 32})
        self.assertEqual((snap["judge"]["child"]["status"], snap["judge"]["child"]["failures"]), ("failed", 1))
        self.assertEqual([r["rank"] for r in snap["builds"]["chat"]["bySession"]], [1])
        self.assertEqual(snap["parses"]["perSession"], {"sessions": 1, "max": 1})
        h = snap["http"]
        self.assertEqual(h["GET /glossary/*"]["count"], 1)
        self.assertEqual(h["GET /remote/*/sessions"]["count"], 1)
        self.assertEqual(h["other"]["count"], 3, "the scanner's path, the remote path with a sid and the home path: %s" % sorted(h))
        self.assertEqual(sorted(snap["pusher"]["connectPush"]["byApp"]), ["chat", "other"])
        self.assertEqual(sorted(snap["pusher"]["clients"]["byApp"]), ["chat", "other"], "the per-client wire table follows the same rule")
        self.assertEqual(snap["pusher"]["clients"]["byKind"]["other"]["frames"], 1)
        self.assertEqual(snap["stagesForeign"], {"jobs.autoNudge.parse": 1.0, "push.feed": 4.0}, "the two foreign writes rode in the walk")
        self.assertEqual(snap["pusher"]["cycleJobsMs"]["persistCheckpoints"], 2.0, "and the pusher's cycle job")
        self.assertEqual(snap["pusher"]["connectPush"]["stagesMs"], {"push.chat": 3.0, "push.send.compare": 2.0}, "and the connect push's stages")
        self.assertEqual(snap["stages_ms"]["push.chat"], 10.0, "the pusher's push.chat alone in the flat row")

    def test_the_route_mark_is_the_registers_word_never_the_requesters(self):
        """_route_seg (2026-09-18): GET /perf?stacks=1 and ROMP_PERF_STACKS serve each thread's stage mark, and a handler's is
        made from the in-flight URL, so the segment it keeps is one the register (every method's routes and the families)
        holds a path under, the second segment under /push, /tunnels and /usage only when the two-segment path is itself a
        route, and `other` for everything else: a session id, a host name, a scanner's probe."""
        seg = km._route_seg
        self.assertEqual(seg("/" + SID), "other", "a session id as the path")
        self.assertEqual(seg("/" + SID + "/sessions"), "other")
        self.assertEqual(seg("/nope/" + SID), "other", "a scanner's probe")
        self.assertEqual(seg("/TESTHOST"), "other", "a host name")
        self.assertEqual(seg("/tunnels/" + SID), "other", "a two-segment prefix whose second segment is no route: the whole mark folds")
        self.assertEqual(seg("/push/relay?x=1"), "push.relay"); self.assertEqual(seg("/push"), "push", "the prefix alone: a route sits under it")
        self.assertEqual(seg("/remote/TESTHOST/ws"), "remote", "the family keeps its name and the host stays out")
        self.assertEqual(seg("/"), "root"); self.assertEqual(seg(""), "root")
        for method, routes in km._PERF_HTTP_ROUTES.items():   # every registered route keeps its first segment, or its two
            for p in routes:
                parts = p.strip("/").split("/")
                want = ".".join(parts[:2]) if parts[0] in km._ROUTE_TWO_SEGMENTS else (parts[0] or "root")
                self.assertEqual(seg(p), want, "%s %s" % (method, p))
        for fam in km._PERF_HTTP_FAMILIES:
            self.assertEqual(seg(fam[:-1] + "x"), fam[1:-2], fam)

    def test_the_http_key_set_is_the_image_of_the_fold(self):
        """The set the walk holds the http table to is what _perf_http_key can return, and nothing else (2026-09-18, the
        review's finding: a character grammar stood here and admitted any path-shaped key). Its size is the register's
        arithmetic (routes twice, once plain and once behind /remote/*, the families per method, and other: 457 on the
        register of 2026-09-18), so no key is counted twice, and one request reaches every member, so the check has no
        false positives; the fold's other direction is its source, whose last line spells one of these or `other`. The
        walk's check is the shared module's membership test over its copy of the register (perf_public.http_key_ok), so
        every member must pass it and the walk's own rejects must fail it."""
        keys = self._http_keys()
        routes = sum(len(r) for r in km._PERF_HTTP_ROUTES.values())
        self.assertEqual(len(keys), 1 + 2 * routes + len(km._PERF_HTTP_ROUTES) * len(km._PERF_HTTP_FAMILIES), sorted(keys))
        self.assertGreaterEqual(len(keys), 457, "the register shrank: %d keys" % len(keys))
        for k in sorted(keys - {"other"}):
            method, path = k.split(" ", 1)
            asked = path.replace("/remote/*", "/remote/TESTHOST").replace("/*", "/x")
            self.assertEqual(km._perf_http_key(method, asked), k, "%s %s reaches %s" % (method, asked, k))
            self.assertTrue(pp.http_key_ok(k), "%s: in the kernel's image and refused by the shared module's check" % k)
        self.assertEqual(km._perf_http_key("GET", "/nope/" + SID), "other")
        for k in ("GET /nope/" + SID, "GET /glossary/Quarterly Roadmap", "GET /remote/TESTHOST/sessions", "HEAD /perf", "PUT /perf"):
            self.assertFalse(pp.http_key_ok(k), k)
            self.assertEqual(pp.paste_problems({"http": {k: {"count": 1}}}, ident=self.IDENT)[-1].kind,
                             "outside the image of the route register", k)

if __name__ == "__main__":
    unittest.main()
