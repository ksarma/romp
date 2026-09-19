#!/usr/bin/env python3
"""`romp perf export --public` (cli/perf_export.py, bin/romp-perf-export) and the public shape it shares with
`romp restart-metrics --json --public` and the served-snapshot invariant test (cli/perf_public.py), 2026-09-18.

The export writes one paste-safe copy of GET /perf: every key and string value folded to the browser's `ident`
grammar or `other` (the `http` block judged against the kernel's route register, the joined-identifier byte
tables against their own grammar), a denylist of key paths dropped, an envelope of `schema`, `exported_at` (a
UTC minute) and the kernel's abbreviated commit when the snapshot carries one, and a self-check (the invariant
walk plus a scan for the strings only this machine knows) that refuses to write rather than leak. Three
sources drive it here: a synthetic snapshot in an OLD kernel's shape carrying every leak the usage-data answer
names (a home path in the read table, the judges' done line with an exception message, sids in the chat rows
and the parse table, a glossary term, a scanner's path, a host and a home path in http keys, a client's own
text as an app name, a thread stack, a path as a stage key, the pid, the clock stamps and the split rows' wall-clock
stamps), the CLI run as a
subprocess over that snapshot (--from, --out, --usage, the refusals), and a kernel this module starts under
the suite's fixtures (the real Handler on a loopback port, the test_perf_stats.py PerfRoutes pattern) with the
same leaks planted through the collector's own writers. Nothing here reads a live kernel or a real state
directory: the state root is the suite's floor, the machine strings the scan learns are synthetic (HOME and USER
are set for the child, and socket.gethostname is pinned to TESTHOST.example in it; an in-process run of the verb or
of its check replaces machine_probes with SYNTHETIC_PROBES, so no real hostname, login or home is read by any test),
every id is a placeholder."""
import contextlib
import io
import json
import os
import re
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")

os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)
load_source("romp_event_model", os.path.join(BIN, "romp-event-model"))
load_source("romp_judge", os.path.join(BIN, "romp-judge"))
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "test-token-DO-NOT-USE")
km = load_source("romp_kernel_export", os.path.join(BIN, "romp-kernel"))
pp = load_source("romp_perf_public", os.path.join(ROOT, "cli", "perf_public.py"))
pe = load_source("romp_perf_export", os.path.join(BIN, "romp-perf-export"))

EXPORT = os.path.join(BIN, "romp-perf-export")
SID = "11111111-2222-3333-4444-555555555555"
SID2 = "22222222-3333-4444-5555-666666666666"
HOME = "/home/tester"                                       # a synthetic home; never this machine's
TERM = "Quarterly Roadmap"
APP = "<b>%s</b> %s" % (SID, HOME)
FIRST = "OSError: [Errno 2] No such file or directory: '%s/.claude/projects/-home-tester-code-notes-api/%s.jsonl'" % (HOME, SID)
SHA = "0123456789abcdef0123456789abcdef01234567"
PLANTED = (SID, SID[:8], SID2, SID2[:8], HOME, "tester", "TESTHOST", TERM, FIRST, APP, "-home-tester-code-notes-api")
STAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}Z$")
FILE_NAME = re.compile(r"^perf-export-\d{8}T\d{4}\.json$")
# One split row as the kernel's _split writes it (the boot's first cycle and first pass, each stage-ring row): `t` is
# the wall clock at the cycle's CLOSE, so the first cycle's is the kernel's start plus that cycle's length (under a
# second on a quick boot, up to the ten seconds the kernel flags as slow), constant for the life of the process; `s`,
# `stages` and `gc` are the split, measurements the public form keeps whole.
SPLIT = {"s": 0.5, "t": 900.5, "stages": {"jobs": {"ms": 300.0, "bytes": 1024, "hydrated": 0}}, "gc": {"n0": 1, "n1": 0, "n2": 0, "ms2": 0.0}}

# The ten memory-fraction bounds GET /perf serves, each a fixed fraction of the machine's MemTotal (the kernel's own
# formulas, floors included), planted at their served paths from a synthetic MemTotal that is not a power of two (a
# 125.5 GiB machine as /proc/meminfo spells it), with an occupancy beside each; the public form rounds every one UP to
# a power of two (round 3 of the export's review, 2026-09-18: recordCache.budgetBytes gave the machine's RAM to the
# kilobyte, and every export from one machine shared all ten exactly).
MEM_TOTAL = 131_572_192 * 1024
BOUND_PATHS = (("pusher", "stageRingMax"), ("heap", "hydrated", "capBytes"), ("checkpoints", "docMemo", "capBytes"),
               ("asmCheckpoint", "asmDocMemo", "capBytes"), ("asmIndex", "cap"), ("recordCache", "budgetBytes"),
               ("builds", "feed", "memo", "bound"), ("memos", "notices", "bound"), ("memos", "spendTree", "bound"),
               ("memos", "summaryAnchor", "bound"))


def bounds_snapshot(mem_total=MEM_TOTAL):
    return {
        "uptime_s": 100.5, "process": {}, "http": {},
        "pusher": {"stageRingMax": max(16, mem_total // (256 * 1024 * 1024)), "stageRingLen": 7},
        "heap": {"hydrated": {"entries": 12, "bytes": 5000, "capBytes": max(1024 ** 3, mem_total // 32)}},
        "checkpoints": {"docMemo": {"entries": 2, "bytes": 3000, "capBytes": max(64 * 1024 ** 2, mem_total // 512), "parseMultiple": 4.5}},
        "asmCheckpoint": {"asmDocMemo": {"entries": 1, "bytes": 200, "capBytes": max(64 * 1024 ** 2, mem_total // 512), "multiple": 10}},
        "asmIndex": {"resident": 40, "cap": max(500_000, mem_total // (32 * 1024))},
        "recordCache": {"entries": 9, "bytes": 123456, "budgetBytes": max(4 * 1024 ** 3, mem_total // 2), "countCap": 1024},
        "builds": {"feed": {"memo": {"entries": 3, "bytes": 777, "bound": mem_total // 64}}},
        "memos": {"notices": {"bytes": 10, "bound": mem_total // 256}, "spendTree": {"bytes": 11, "bound": mem_total // 64},
                  "summaryAnchor": {"bytes": 12, "bound": mem_total // 256}},
        "judge": {"child": {"recordCache": {"entries": 1, "bytes": 5, "budgetBytes": max(4 * 1024 ** 3, mem_total // 2)}}},
    }


def _at(doc, path):
    for k in path:
        doc = doc[k]
    return doc


def _numbers(doc):
    """[(path, value)] for every numeric leaf of `doc` (a bool is not a number)."""
    out = []

    def walk(node, where):
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, where + (k,))
        elif isinstance(node, (list, tuple)):
            for i, v in enumerate(node):
                walk(v, where + (i,))
        elif isinstance(node, (int, float)) and not isinstance(node, bool):
            out.append(("/".join(str(p) for p in where), node))
    walk(doc, ())
    return out


# A clock stamp is a number inside a PLAUSIBLE EPOCH WINDOW: the seconds from 2017 to 2033, or the same span in
# milliseconds. The stamp property is worded over these windows and not as "anything at or above 1.5e9" (round 5 of
# the export's review, 2026-09-18): the served kernel's glibc allocator figures, perf/process/malloc/arena and
# uordblks, were 2931437568 and 2731423520 on CI's runner and under 1.5e9 on the box that wrote the test, so a floor
# alone made the property depend on the host's memory. A large number outside the windows is a byte total or a count,
# a measurement the export keeps on purpose. No count, byte total or duration of the fixtures falls inside a window,
# and no power of two does either (2^30 and 2^31, 2^40 and 2^41 bracket them), so the served test's allowance for a
# coarsened bound inside a window states the rule and is not what passes it.
EPOCH_WINDOWS = ((1.5e9, 2.0e9), (1.5e12, 2.0e12))


def _stamps(doc):
    """The numeric leaves of `doc` that read as an absolute clock stamp: inside one of the EPOCH_WINDOWS."""
    return [(p, v) for p, v in _numbers(doc) if any(lo <= v <= hi for lo, hi in EPOCH_WINDOWS)]


def _epoch(node, key=None):
    """`node` with every stamp of the leak snapshot (`t`, `now`, `since`; the fixture's own are small numbers) moved into the
    seconds epoch window, so a survivor would stand out as a number inside one of the EPOCH_WINDOWS."""
    if isinstance(node, dict):
        return {k: _epoch(v, k) for k, v in node.items()}
    if isinstance(node, list):
        return [_epoch(v) for v in node]
    if key in ("t", "now", "since") and isinstance(node, (int, float)) and not isinstance(node, bool):
        return node + 1.7e9
    return node


def leak_snapshot():
    """A GET /perf snapshot in the shape of a kernel from BEFORE the served-leak fixes, so every leak the export
    must fold or drop is present at once; a few numbers ride beside them so the diagnosis they leave is checked."""
    return {
        "now": 1000.5, "since": 900.0, "uptime_s": 100.5, "log": True, "kernel_sha": SHA,
        "process": {"rss_kb": 409600, "threads": 40, "cpu_s": 60.0, "pid": 4242, "ppid": 4241, "managerPid": 4240, "source": "proc", "cwd": HOME},
        "pusher": {"cycles": 100, "cycle_ms_p50": 180.0, "idle_cycles": 40,
                   "connectPush": {"count": 4, "byApp": {"chat": {"count": 1}, APP: {"count": 2}, HOME: {"count": 1}}},
                   "clients": {"byApp": {"chat": {"frames": 3}, APP: {"frames": 1}}, "byKind": {"chrome": {"frames": 4}}},
                   "firstCycle": SPLIT, "stageRing": [SPLIT, dict(SPLIT, s=0.2, t=1000.4)], "stageRingLen": 2},
        "jobs": {"passes": 50, "pass_ms_max": 30.0, "firstPass": dict(SPLIT, s=1.5, t=905.0),
                 "stageRing": [dict(SPLIT, s=0.1, t=1000.1)], "stageRingLen": 1},
        "stages_ms": {"jobs": 5000.0, "push.chat": 15000.0, HOME + "/notes": 2.0, "push.chat.sig": float("nan")},
        "builds": {"chat": {"cached": 80, "built": 20, "ms": 800.0,
                            "bg_miss": {"transcript": 5, "names": 2, "host": 1, "cwd": 3, "cold": 1},
                            "bySession": [{"sid": SID, "n": 3, "max": 12.0, "first": 5.0, "last": 4.0},
                                          {"sid": SID2, "n": 1, "max": 3.0, "first": 3.0, "last": 3.0}]},
                   "feed": {"cached": 90, "built": 10, "ms": 5000.0}},
        "sends": {"full": {"chat": {"count": 10, "bytes": 1000000}}},
        "memos": {"chain": {"hit": 400, "miss": 40}, "sessionsListing": {"built": 3, "missBy": {"names": 4, "rows": 1, "first": 1}}},
        "judge": {"passes": 30, "ms_sum": 30000.0,
                  "child": {"op": "done", "seq": 7, "pid": 4343, "t": 999.0, "wallMs": 12.5,
                            "failures": {"count": 1, "first": FIRST}, "recovered": False, "line": "done seq 7 " + SID,
                            "recordCache": {"entries": 1, "wholeReads": {"leaf<-_parse": {"count": 1, "bytes": 5}},
                                            "wholeReadsByStage": {"push:leaf<-_parse": {"count": 1, "bytes": 5}}},
                            "asmCheckpoint": {"restored": 1, "hydratedBy": {"<lambda>": 10, "_unit_text<-build_session": 2}}}},
        "http": {"GET /perf": {"count": 5, "ms": 2.5}, "POST /send": {"count": 7, "ms": 7.0}, "POST /new": {"count": 2, "ms": 4.0},
                 "POST /tick": {"count": 50, "ms": 25.0}, "GET /feed": {"count": 3, "ms": 30.0}, "GET /dist/render.js": {"count": 9, "ms": 1.0},
                 "GET /glossary/" + TERM: {"count": 1, "ms": 1.0}, "GET /nope/" + SID: {"count": 2, "ms": 1.0},
                 "GET /remote/TESTHOST/sessions": {"count": 1, "ms": 1.0}, "GET /remote/TESTHOST": {"count": 1, "ms": 1.0},
                 "GET " + HOME: {"count": 3, "ms": 1.0}, "HEAD /file": {"count": 1, "ms": 0.5}, "OPTIONS /perf": {"count": 1, "ms": 0.1},
                 "GET /ws": {"count": 3, "ms": 0.0}},
        "parses": {"kernel": 12, "hits": 30, "bytes": 4096, "bySid": {SID: 3, SID2: 9}},
        "checkpoints": {"restored": 2, "readBytes": 8192, "lastDocument": SHA,
                        "readByPath": {HOME + "/.claude/projects/-home-tester-code-notes-api/%s.jsonl" % SID: 4096, HOME + "/notes/scratch.jsonl": 32},
                        "readByKind": {"leaf": {"files": 1, "bytes": 4096}, "other": {"files": 1, "bytes": 32}}},
        "recordCache": {"entries": 3, "wholeReads": {"leaf<-_parse": {"count": 2, "bytes": 10}},
                        "wholeReadsByStage": {"push:leaf<-_parse": {"count": 2, "bytes": 10}}},
        "asmIndex": {"materialized": 4, "materializedBy": {"<lambda>": 1, "build_session": 3}},
        "stacks": {"11 pusher": {"self": False, "stage": "jobs.autoNudge", "frames": ["_pusher (%s/kernel.py:100)" % HOME]}},
        "caches": {"session_stamp": {"entries": 31}, "jsonl": {"entries": 120}},
        "glossary": {"parses": 1, "termsBuilt": 40, "sample": TERM},
        "heap": {"tracing": False, "note": "a value longer than thirty-two characters is text", "host": "TESTHOST up"},
    }


HOSTNAME = "TESTHOST.example"                                # the child's hostname; never this machine's
# The child runs the verb's file under a pinned socket.gethostname: machine_probes reads it and no environment
# variable overrides it, so without the pin the Cli and ServedKernel cases would learn the real hostname of the
# machine running the suite (and a key spelled like it would refuse an export there and nowhere else).
CHILD = ("import runpy, socket, sys; socket.gethostname = lambda: %r; sys.argv = sys.argv[1:]; "
         "runpy.run_path(sys.argv[0], run_name='__main__')" % HOSTNAME)


# A finite cap on a child's virtual address space (RLIMIT_AS, bytes) for the refusable-input cases: 1.5 GiB. The closing
# re-run's reproduction used 768 MiB (ulimit -v 786432) when a listed 1e-1000000000 asked for a billion digits and the head
# died with a MemoryError, and 768 MiB is enough for the fixed child on 3.10, 3.12 and 3.13; the free-threaded 3.14t
# interpreter maps about 1 GiB of address space before any code runs (VmSize 1085112 kB, measured 2026-09-19) and died
# importing hashlib under 768 MiB. The cap must also stay UNDER what the billion-digit expansion needs, or the guard's
# removal no longer fails fast: under 2 GiB format(Decimal('1e-1000000000'), 'f') completes (1000000002 characters in
# 1.3 s, measured on 3.12 and 3.14t) and the child then grinds past the subprocess timeout; under 1.5 GiB it raises
# MemoryError in under a second on both (0.68 s and 0.64 s). One cap for every build, 1.5 GiB: room for 3.14t's baseline,
# none for the expansion.
ADDRESS_SPACE_CAP = 1536 * 1024 * 1024


def _run(args, env_extra=None, state=None, address_space=None):
    """bin/romp-perf-export as a child, hermetic: the suite's interpreter, a private state root, a synthetic
    HOME, USER and hostname (CHILD), no live kernel port and no token unless the caller says so. `address_space`, in
    bytes, caps the child's virtual address space (RLIMIT_AS), set by the CHILD ITSELF in its prelude before the verb's
    code runs, not through preexec_fn: a fork hook in a parent that may be running a kernel's threads (the ServedKernel
    cases can share a worker with these) is the documented deadlock hazard, and the cap lands on the same process either
    way."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("ROMP_") and k not in ("CLAUDE_CODE_SESSION_ID", "XDG_CONFIG_HOME")}
    state = state or tempfile.mkdtemp()      # no XDG_CONFIG_HOME: the child resolves the private list under its synthetic HOME, never this machine's
    env.update({"XDG_STATE_HOME": os.path.dirname(state) if os.path.basename(state) == "romp" else state,
                "HOME": HOME, "USER": "tester", "LOGNAME": "tester", "ROMP_KERNEL_PORT": "1"})
    env.update(env_extra or {})
    child = CHILD if address_space is None else "import resource; resource.setrlimit(resource.RLIMIT_AS, (%d, %d)); " % (address_space, address_space) + CHILD
    return subprocess.run([sys.executable, "-c", child, EXPORT] + list(args), capture_output=True, text=True, timeout=60, env=env)


SYNTHETIC_PROBES = [("hostname", "testhost"), ("username", "tester"), ("home directory", HOME)]


def _keys_named(doc, name):
    """The key paths (`a/b/0`) of every dict holding a key named `name`, at any depth of `doc`; empty when none does."""
    out = []

    def walk(node, where):
        if isinstance(node, dict):
            if name in node:
                out.append("/".join(str(p) for p in where))
            for k, v in node.items():
                walk(v, where + (k,))
        elif isinstance(node, (list, tuple)):
            for i, v in enumerate(node):
                walk(v, where + (i,))
    walk(doc, ())
    return out


def _hits(doc, probes, **kw):
    """The scan's findings as the refusal spells them: (kind, place)."""
    return [(h.kind, pp.place(h)) for h in pp.identifier_hits(doc, probes, **kw)]


def _kinds(doc, **kw):
    """The walk's findings by kind alone."""
    return [p.kind for p in pp.paste_problems(doc, **kw)]


def _lines(problems):
    return "%d leak(s):\n  %s" % (len(problems), "\n  ".join(map(str, problems)))


def _check(doc):
    """pe.check_document with the machine's own strings replaced by synthetic probes (the export module's import of
    perf_public is its own module object, so the patch lands there), so the verdict is the document's alone."""
    with mock.patch.object(pe.pp, "machine_probes", return_value=SYNTHETIC_PROBES):
        return pe.check_document(doc, pe.Path(tempfile.mkdtemp()))


def _state_root():
    """A state root the child resolves as <XDG>/romp; returns (xdg, state)."""
    xdg = tempfile.mkdtemp()
    state = os.path.join(xdg, "romp")
    os.makedirs(state)
    with open(os.path.join(state, "session-hosts"), "w") as fh:
        fh.write("off\n")
    return xdg, state


class FoldInvariant(unittest.TestCase):
    """The whole-document shape rule and the denylist over a snapshot carrying every leak shape."""

    def setUp(self):
        self.snap = leak_snapshot()
        self.doc = pe.export_document(self.snap, usage=True)
        self.perf = self.doc["perf"]

    def test_no_planted_text_id_or_path_survives_and_every_key_fits_its_grammar(self):
        problems = pp.paste_problems(self.doc, planted=PLANTED, skip=("schema",), under=("perf",))
        self.assertEqual(problems, [], _lines(problems))
        self.assertNotIn(HOME, json.dumps(self.doc))
        self.assertNotIn("TESTHOST", json.dumps(self.doc))

    def test_the_denylist_drops_the_by_path_by_sid_stack_pid_and_clock_entries(self):
        self.assertNotIn("readByPath", self.perf["checkpoints"])
        self.assertEqual(self.perf["checkpoints"]["readByKind"]["leaf"], {"files": 1, "bytes": 4096})
        self.assertNotIn("bySid", self.perf["parses"])
        self.assertEqual(self.perf["parses"]["kernel"], 12)
        for key in ("stacks", "log", "now", "since", "kernel_sha"):
            self.assertNotIn(key, self.perf, key)
        self.assertEqual(self.perf["process"], {"rss_kb": 409600, "threads": 40, "cpu_s": 60.0, "source": "proc"},
                         "the pid under every spelling and the working directory go; the gauges stay")
        self.assertEqual(self.perf["uptime_s"], 60, "uptime_s stays, rounded down to whole minutes (100.5 s)")

    def test_the_split_rows_lose_their_stamp_and_keep_the_split(self):
        # every split row (the boot's first cycle and first pass, each stage-ring row) carries `t`, the wall clock at
        # the cycle's CLOSE; the first's is the kernel's start plus the first cycle's length, constant for the life of
        # the process, an absolute clock stamp and so denied (the receiver's review, 2026-09-18). The split itself
        # (`s`, `stages`, `gc`) stays WHOLE, for firstCycle and firstPass too, by decision (round 3): the boot's stage
        # split is the data a reader wants (which stage a slow boot spent its time in), and though the two rows are set
        # once per process and served unchanged, a per-process fingerprint, the public form is paste-safe, not
        # unlinkable: it removes stamps, not measurements, and two exports from one kernel life stay linkable through
        # these rows and hundreds of other lifetime constants (restoreMs, the bySession firsts and maxima).
        rows = [self.perf["pusher"]["firstCycle"], self.perf["jobs"]["firstPass"]] + self.perf["pusher"]["stageRing"] + self.perf["jobs"]["stageRing"]
        self.assertEqual(len(rows), 5)
        for row in rows:
            self.assertNotIn("t", row, row)
            self.assertEqual(sorted(row), ["gc", "s", "stages"], "the split itself stays")
        self.assertEqual(self.perf["jobs"]["firstPass"]["s"], 1.5, "the first pass's length, a measurement, is kept whole")
        self.assertEqual(self.perf["pusher"]["firstCycle"]["gc"], SPLIT["gc"])
        self.assertEqual(self.perf["pusher"]["firstCycle"]["stages"], {"jobs": {"ms": 300.0, "bytes": 1024, "hydrated": 0}})
        self.assertEqual([r["s"] for r in self.perf["pusher"]["stageRing"]], [0.5, 0.2])
        self.assertEqual(self.perf["pusher"]["stageRingLen"], 2)
        self.assertEqual(_keys_named(self.doc, "t"), [], "no key named t at any depth of the document")

    def test_the_child_keeps_its_counts_and_blocks_and_loses_the_text(self):
        child = self.perf["judge"]["child"]
        self.assertEqual(child["failures"], {"count": 1})
        self.assertEqual(child["line"], "other", "a string value outside the grammar is the word")
        self.assertNotIn("pid", child)
        self.assertNotIn("t", child)
        self.assertEqual(child["recordCache"]["wholeReads"], {"leaf<-_parse": {"count": 1, "bytes": 5}})
        self.assertEqual(child["asmCheckpoint"]["hydratedBy"], {"<lambda>": 10, "_unit_text<-build_session": 2})
        self.assertEqual(child["wallMs"], 12.5)

    def test_per_session_rows_lose_the_sid_and_keep_the_numbers(self):
        rows = self.perf["builds"]["chat"]["bySession"]
        self.assertEqual(rows, [{"n": 3, "max": 12.0, "first": 5.0, "last": 4.0}, {"n": 1, "max": 3.0, "first": 3.0, "last": 3.0}])

    def test_keys_outside_the_grammar_fold_to_other_with_their_counts_summed(self):
        self.assertEqual(self.perf["pusher"]["connectPush"]["byApp"], {"chat": {"count": 1}, "other": {"count": 3}})
        self.assertEqual(self.perf["pusher"]["clients"]["byApp"], {"chat": {"frames": 3}, "other": {"frames": 1}})
        self.assertEqual(self.perf["stages_ms"], {"jobs": 5000.0, "push.chat": 15000.0, "other": 2.0, "push.chat.sig": None},
                         "a path as a stage key folds; a non-finite number is null")

    def test_http_keys_outside_the_route_register_fold_to_other(self):
        h = self.perf["http"]
        for key in h:
            self.assertTrue(pp.http_key_ok(key), key)
        self.assertEqual(h["other"], {"count": 5, "ms": 2.0}, "the sid path and the home path: %s" % sorted(h))
        # an OLD kernel counted the raw paths; the export collapses the families the way the kernel does now
        self.assertEqual(h["GET /remote/*/sessions"]["count"], 1)
        self.assertEqual(h["GET /remote/*"]["count"], 1, "a bare remote host is the family's own key")
        self.assertEqual(h["GET /glossary/*"]["count"], 1, "the term is gone, the lookup is counted")
        self.assertEqual(h["GET /dist/*"]["count"], 9)
        self.assertEqual(h["GET /ws"]["count"], 3)
        self.assertEqual(pp.fold({"http": {"GET /glossary/*": {"count": 2}, "GET /glossary/Term Two": {"count": 3}}}),
                         {"http": {"GET /glossary/*": {"count": 5}}}, "a current kernel's family key and an old one's raw path merge")
        self.assertEqual(pp.http_public_key("POST /remote/TESTHOST/send"), "POST /remote/*/send")
        self.assertEqual(pp.http_public_key("GET /remote/TESTHOST/" + SID), "other")
        self.assertEqual(pp.http_public_key("GET /media/logo.png"), "GET /media/*")
        self.assertEqual(pp.http_public_key("PUT /perf"), "other")
        self.assertEqual(pp.http_public_key("nonsense"), "other")
        self.assertEqual(pp.http_public_key("other"), "other")

    def test_string_values_outside_the_grammar_become_other(self):
        self.assertEqual(self.perf["glossary"], {"parses": 1, "termsBuilt": 40, "sample": "other"})
        self.assertEqual(self.perf["heap"], {"tracing": False, "note": "other"}, "a host under an identity key goes; long text folds")

    def test_a_40_hex_token_and_free_text_are_folded_by_the_export_and_refused_by_the_walk(self):
        # the served-leak review's two rules (2026-09-18) live in the shared module so the export applies them too: a
        # 40-hex token (a checkpoint document's name, a commit) and a string carrying whitespace (an exception message,
        # a URL, a bare host name) fold to `other` (the grammar's cap and character set), and the walk names either
        # one that survives, so the export's self-check refuses a document carrying them
        self.assertEqual(self.perf["checkpoints"]["lastDocument"], "other")
        self.assertEqual(pp.fold({"doc": SHA, "note": "a b", "term": TERM, "ok": "lt1h", "hex32": "a" * 32}),
                         {"doc": "other", "note": "other", "term": "other", "ok": "lt1h", "hex32": "a" * 32},
                         "the fold is the grammar: a 32-hex token fits it and is the walk's to catch")
        kinds = _kinds
        self.assertEqual(kinds({"a": {"doc": SHA}}), ["a 40-hex token"])
        self.assertEqual(kinds({"a": {"note": "a b"}}), ["free text"])
        self.assertEqual(kinds({"a": {"note": "tab\there"}}), ["free text"])
        self.assertEqual(kinds({"a": {"hex32": "a" * 32}}), ["a 32-hex token"])
        self.assertEqual(kinds({SHA: 1}), ["a 40-hex token", "outside the identifier grammar"], "a key is held to the same rule")
        self.assertEqual(kinds({"a b": 1}), ["outside the identifier grammar"], "a key with whitespace is a grammar failure already")
        self.assertEqual(kinds({"a": {"ok": "lt1h", "stamp": "2026-09-18T08:53Z", "n": 1}}), [])
        # the export's own check refuses a document that carries either, naming the key path and never the value
        doc = pe.export_document(leak_snapshot())
        doc["perf"]["checkpoints"]["lastDocument"] = SHA
        reason = _check(doc)
        self.assertIn("still fails the walk", reason)
        self.assertIn("(a 40-hex token, the value at perf/checkpoints/lastDocument)", reason)
        self.assertNotIn(SHA, reason)
        doc = pe.export_document(leak_snapshot())
        doc["perf"]["heap"]["note"] = "some words here"
        reason = _check(doc)
        self.assertIn("(free text, the value at perf/heap/note)", reason)
        self.assertNotIn("some words", reason)
        doc["perf"]["heap"]["note"] = "TESTHOST up"
        reason = _check(doc)
        self.assertEqual(reason, "a string this machine knows (hostname) survives as the value at perf/heap/note; nothing written",
                         "the scan and the walk find the same value: the tie goes to the scan, so the machine string is what is named")
        self.assertIsNone(_check(pe.export_document(leak_snapshot(), usage=True)))

    def test_the_walk_reports_structured_problems_and_the_refusal_never_carries_a_fragment_of_the_text(self):
        # the walk's finding is a tuple (the kind, key or value, the key path, the string), formatted by the caller:
        # the export's refusal prints the kind and the path alone. A caller that split a line at " at " printed
        # whatever followed the FIRST one, and a key or value that itself contains " at " put a fragment of the
        # flagged material (a hostname, a home path) into the refusal (the review's medium, 2026-09-18). A real
        # --from document cannot reach this (the fold keeps no whitespace), a doctored one can: the self-check
        # guards that road too
        problems = pp.paste_problems({"a": {"note": "TESTHOST at %s/x" % HOME}})
        self.assertEqual([(p.kind, p.is_key, p.path) for p in problems],
                         [("an absolute path", False, "a/note"), ("free text", False, "a/note")])
        self.assertEqual(problems[0].text, "TESTHOST at %s/x" % HOME, "the string rides in its own field, for a test's diagnostics")
        self.assertEqual(str(problems[1]), "free text: value 'TESTHOST at /home/tester/x' at a/note", "the line a test prints")
        problems = pp.paste_problems({"a": {"TESTHOST at %s/x" % HOME: 1}})
        self.assertEqual([(p.kind, p.is_key, p.path) for p in problems],
                         [("an absolute path", True, "a"), ("outside the identifier grammar", True, "a")],
                         "a key's path is the path of the dict holding it")
        self.assertEqual([(p.kind, p.is_key, p.path) for p in pp.paste_problems({"a b": 1})],
                         [("outside the identifier grammar", True, "")], "the root is the empty path")
        self.assertEqual([(p.kind, p.text) for p in pp.paste_problems({5: 1})], [("a non-string key", "5")])
        # a VALUE containing " at ": the refusal names the value's path and nothing of the value (a path no probe
        # knows, so the walk is the leg that refuses; the scan's leg is below)
        doc = pe.export_document(leak_snapshot())
        doc["perf"]["heap"]["note"] = "peer at /srv/data/x"
        reason = _check(doc)
        self.assertIn("(an absolute path, the value at perf/heap/note); nothing written", reason)
        for fragment in ("peer", "/srv", "/data", "/x", " at /"):
            self.assertNotIn(fragment, reason, reason)
        # a KEY containing " at ": the refusal names the dict holding it and nothing of the key
        doc = pe.export_document(leak_snapshot())
        doc["perf"]["heap"]["peer at /srv/data/x"] = 1
        reason = _check(doc)
        self.assertIn("(an absolute path, a key under perf/heap); nothing written", reason)
        for fragment in ("peer", "/srv", "/data", "/x", " at /"):
            self.assertNotIn(fragment, reason, reason)
        # the same two shapes carrying this machine's strings (a hostname, a home path): the scan refuses first, and
        # its report is the kind and the path, no fragment either
        for plant in ("TESTHOST at %s/x" % HOME, "%s at TESTHOST" % HOME):
            doc = pe.export_document(leak_snapshot())
            doc["perf"]["heap"]["note"] = plant
            reason = _check(doc)
            self.assertTrue(reason.endswith("survives as the value at perf/heap/note; nothing written"), reason)
            doc = pe.export_document(leak_snapshot())
            doc["perf"]["heap"][plant] = 1
            reason2 = _check(doc)
            self.assertTrue(reason2.endswith("survives as a key under perf/heap; nothing written"), reason2)
            for fragment in ("TESTHOST", HOME, "/x", "tester", " at /", " at T"):
                self.assertNotIn(fragment, reason, reason)
                self.assertNotIn(fragment, reason2, reason2)
        # a key at the export's root: "the root", as the identifier scan spells it
        doc = pe.export_document(leak_snapshot())
        doc["a b"] = 1
        self.assertIn("(outside the identifier grammar, a key under the root); nothing written", _check(doc))
        # the SHALLOWEST finding is named: a walk problem beneath a key spelling a machine string is reported as that
        # string (the scan's key finding, one level up), never as a key path that spells it (the walk's path would
        # read perf/memos/TESTHOST/note)
        doc = pe.export_document(leak_snapshot())
        doc["perf"]["memos"]["TESTHOST"] = {"note": "a b"}
        reason = _check(doc)
        self.assertEqual(reason, "a string this machine knows (hostname) survives as a key under perf/memos; nothing written")
        self.assertNotIn("TESTHOST", reason)

    def test_the_shallowest_finding_is_named_so_the_refusal_never_prints_a_component_the_walk_would_refuse(self):
        # round 1 ran the scan first and named ITS finding whatever its depth, so a machine string beneath a key that
        # fits the fold's grammar but fails the walk (a 32-hex token, the class the walk refuses to write) put that key
        # into the refusal as a path component; a walk-first order had the mirror problem (the test above). Both run
        # and the finding with the fewest path components wins (a key finding counts the dict holding it), the scan's
        # wording on a tie: every component of a printed path is a key above the finding, and a key either mechanism
        # would flag is a finding of its own one level shallower, so the printed path cannot carry one (round 2)
        token = "c" * 32
        for planted, what in (("TESTHOST", "a hostname-shaped value"), ({"TESTHOST": 1}, "a dict with a hostname key")):
            doc = pe.export_document(leak_snapshot())
            doc["perf"]["heap"][token] = planted
            reason = _check(doc)
            self.assertEqual(reason, "the public form still fails the walk (a 32-hex token, a key under perf/heap); nothing written", what)
            self.assertNotIn(token, reason, what)
            self.assertNotIn("TESTHOST", reason, what)
        # the same depth on both sides: the scan's wording (the pins above hold); a deeper walk finding loses to a
        # shallower scan finding and the other way round, whichever key is the one flagged
        doc = pe.export_document(leak_snapshot())
        doc["perf"]["heap"]["TESTHOST"] = {"a b": 1}
        self.assertEqual(_check(doc), "a string this machine knows (hostname) survives as a key under perf/heap; nothing written")
        doc = pe.export_document(leak_snapshot())
        doc["perf"]["heap"]["a b"] = {"TESTHOST": 1}
        self.assertEqual(_check(doc), "the public form still fails the walk (outside the identifier grammar, a key under perf/heap); nothing written")
        # the structured findings the rule is computed from: the scan's Hit is shaped like the walk's Problem, and
        # both count their depth at the finding (a key's is its dict's; the root is depth 0 and the empty path)
        hits = pp.identifier_hits({"a": {token: "TESTHOST", "TESTHOST": {"n": 1}}, "TESTHOST": 1}, SYNTHETIC_PROBES)
        self.assertEqual(hits, [("hostname", False, "a/" + token, 2, None), ("hostname", True, "a", 1, None), ("hostname", True, "", 0, None)],
                         "the fifth field is the list line a listed entry's Probe carries; a machine string has none")
        self.assertEqual([(h.kind, h.is_key, h.path, h.depth, h.line) for h in hits], hits)
        self.assertEqual([pp.place(h) for h in hits], ["the value at a/" + token, "a key under a", "a key under the root"])
        problems = pp.paste_problems({"a": {token: "x y"}, "GET /perf": {"c d": 1}})
        self.assertEqual([(p.kind, p.is_key, p.path, p.depth) for p in problems],
                         [("a 32-hex token", True, "a", 1), ("free text", False, "a/" + token, 2),
                          ("outside the identifier grammar", True, "", 0), ("outside the identifier grammar", True, "GET /perf", 1)],
                         "a key that contains the separator is one component, so the depth rides in its own field")


    def test_the_denylist_walk_is_the_third_source_and_a_fold_passes_it_by_construction(self):
        """`t` fits the identifier grammar and an uptime to the second is a number, so the walk passes both; the denylist
        walk (pp.denylist_problems) refuses what the fold would have dropped or rounded, which is what lets `romp perf
        upload`, running check_document over a file the user may have edited, refuse a `t` put back or an uptime typed
        to the second. Over a fold's own output it finds nothing, so the export's own write is unchanged (2026-09-18)."""
        doc = pe.export_document(leak_snapshot(), usage=True)
        self.assertEqual(pp.denylist_problems(doc, under=("perf",), skip=("schema",)), [], "a fold's output is the walk's fixed point")
        self.assertIsNone(_check(doc))
        # a split row's stamp put back: a key finding at the dict holding it (the walk is silent)
        doc["perf"]["pusher"]["firstCycle"]["t"] = 900.5
        self.assertEqual(pp.paste_problems(doc, skip=("schema",), under=("perf",)), [])
        self.assertEqual([(p.kind, p.is_key, p.path, p.depth) for p in pp.denylist_problems(doc, under=("perf",), skip=("schema",))],
                         [("a key the denylist drops", True, "perf/pusher/firstCycle", 3)])
        self.assertEqual(_check(doc), "the public form still fails the denylist (a key the denylist drops, a key under perf/pusher/firstCycle); nothing written")
        # an uptime off the grain: a value finding at its own path, the number in no printed field; on the grain it
        # passes, a float on the grain too (the fold's int compares equal), and what is not a number is left alone
        for raw, refused in ((3725, True), (59.9, True), (3720, False), (3720.0, False), (0, False), (None, False), (True, False)):
            doc = pe.export_document(leak_snapshot())
            doc["perf"]["uptime_s"] = raw
            problems = pp.denylist_problems(doc, under=("perf",), skip=("schema",))
            if refused:
                self.assertEqual([(p.kind, p.is_key, p.path, p.depth) for p in problems],
                                 [("an uptime not rounded to whole minutes", False, "perf/uptime_s", 2)], repr(raw))
                self.assertEqual(_check(doc), "the public form still fails the denylist (an uptime not rounded to whole minutes, "
                                              "the value at perf/uptime_s); nothing written", repr(raw))
            else:
                self.assertEqual(problems, [], repr(raw))
        # the rest of the denylist through the same walk: DENY_PATHS anchored at the snapshot's root (`perf`), a pid under
        # any spelling, an identity key over text (over a number it is a counter and stays), a denied key inside `usage`
        doc = pe.export_document(leak_snapshot(), usage=True)
        doc["perf"]["now"] = 1000.5
        doc["perf"]["process"]["cliPid"] = 4242
        doc["perf"]["heap"]["name"] = "x"
        doc["perf"]["heap"]["names"] = 3
        doc["usage"]["sid"] = 1
        self.assertEqual(sorted((p.kind, p.path) for p in pp.denylist_problems(doc, under=("perf",), skip=("schema",))),
                         sorted([("a key the denylist drops", "perf"), ("a key the denylist drops", "perf/process"),
                                 ("a key the denylist drops", "perf/heap"), ("a key the denylist drops", "usage")]))
        # the depth rule holds with the third source: a machine string beneath a denied key names the denied key's dict,
        # so the printed path never carries a key the denylist drops; a shallower scan finding wins over a deeper denied key
        doc = pe.export_document(leak_snapshot())
        doc["perf"]["heap"]["t"] = {"TESTHOST": {"a b": 1}}
        self.assertEqual(_check(doc), "the public form still fails the denylist (a key the denylist drops, a key under perf/heap); nothing written")
        doc = pe.export_document(leak_snapshot())
        doc["perf"]["heap"]["TESTHOST"] = {"t": 1}
        self.assertEqual(_check(doc), "a string this machine knows (hostname) survives as a key under perf/heap; nothing written")
        # on a tie: the scan's wording, then the walk's, then the denylist's
        doc = pe.export_document(leak_snapshot())
        doc["perf"]["heap"]["a b"] = 1
        doc["perf"]["heap"]["t"] = 1
        self.assertEqual(_check(doc), "the public form still fails the walk (outside the identifier grammar, a key under perf/heap); nothing written")

    def test_the_denylist_walk_refuses_a_bound_off_a_power_of_two_and_a_number_the_size_of_a_stamp_and_passes_every_fold(self):
        """The two findings added with the third review round's rules (2026-09-18), so the upload's re-check matches the
        fold's full fixed point: a memory-fraction bound (BOUND_KEYS) the fold would have rounded up to a power of two, a
        value finding at its own path; and a FLOAT leaf inside one of the STAMP_WINDOWS, 1.5e9 to 2.0e9 (an epoch second,
        2017 to 2033) or 1.5e12 to 2.0e12 (the same span in milliseconds), both ends in, anywhere outside a bound or a
        duration key on its path (test_a_float_under_a_duration_key_is_never_judged_against_the_stamp_windows), dict or list,
        which is round 3's property (no absolute clock stamp survives the fold under any key) turned into a check over a
        file. What is not a float inside a window is a measurement and exempt whatever its size: a time.time() value is a
        float, and the kernel's cumulative byte and count totals are integers that pass 1.5e9 within hours on a busy kernel
        (the ws tables' `bytes`, `parses.bytes`), so a fresh export from a long-lived kernel must pass its own belt (a rule
        over every number refused it, 2026-09-18); and a float OUTSIDE both windows tells no time (the export's fifth review
        round, the same day: glibc's allocator figures on a long-lived kernel, process.malloc.arena 2931437568 and uordblks
        2731423520, exceeded a floor at 1.5e9 in the served export's property test, and a float that large under a key the
        denylist does not know is a measurement kept on purpose; before the windows every float from 1.5e9 up was refused).
        The fixed point holds: a fold of every fixture at that round's head, the epoch-shifted leak snapshot and the ten
        real-sized bounds among them (budgetBytes floors at 4 GiB, above the seconds window; no power of two lies in either
        window), raises no finding."""
        for snap in (leak_snapshot(), _epoch(leak_snapshot()), bounds_snapshot(), bounds_snapshot(8 * 1024 ** 3)):
            for usage in (False, True):
                doc = pe.export_document(snap, usage=usage)
                self.assertEqual(pp.denylist_problems(doc, under=("perf",), skip=("schema",)), [], "a fold's output is the walk's fixed point")
                self.assertIsNone(_check(doc))
        doc = pe.export_document(bounds_snapshot())
        self.assertGreater(doc["perf"]["recordCache"]["budgetBytes"], pp.STAMP_WINDOWS[0][1], "a coarsened bound above the seconds window is the fold's own and passes")
        self.assertEqual(pp.STAMP_WINDOWS, ((1.5e9, 2.0e9), (1.5e12, 2.0e12)))
        for lo, hi in pp.STAMP_WINDOWS:
            self.assertFalse(any(lo <= (1 << k) <= hi for k in range(64)), "no power of two lies in a window: a coarsened bound is never the size of a stamp")
        # a bound off a power of two: a value finding at its own path, the number in no printed field; a power of two, however
        # large, and what is not a positive finite number pass, as public_bound leaves them
        for raw in (4_210_310_144, 3, 2.5, 501, 20000, 1.7e9):
            doc = pe.export_document(bounds_snapshot())
            doc["perf"]["heap"]["hydrated"]["capBytes"] = raw
            self.assertEqual([(p.kind, p.is_key, p.path, p.depth) for p in pp.denylist_problems(doc, under=("perf",), skip=("schema",))],
                             [("a bound not rounded to a power of two", False, "perf/heap/hydrated/capBytes", 4)], repr(raw))
            self.assertEqual(_check(doc), "the public form still fails the denylist (a bound not rounded to a power of two, "
                                          "the value at perf/heap/hydrated/capBytes); nothing written", repr(raw))
        for ok in (1, 2, 4096, 1 << 40, 4096.0, 0, -5, None, True, "other"):
            doc = pe.export_document(bounds_snapshot())
            doc["perf"]["heap"]["hydrated"]["capBytes"] = ok
            self.assertEqual(pp.denylist_problems(doc, under=("perf",), skip=("schema",)), [], repr(ok))
        # the windows: a FLOAT leaf inside the seconds window or the milliseconds window under a key the denylist does not
        # know, in a dict or a list, in `usage` too; a value at a window's floor or ceiling is refused, one past either passes
        for path, raw, where in (((("perf", "pusher", "startedAt"), 1.6e9, "perf/pusher/startedAt")),
                                 ((("perf", "heap", "marks"), [1, 1.5e9], "perf/heap/marks/1")),
                                 ((("usage", "firstSeen"), 1_700_000_000.0, "usage/firstSeen")),
                                 ((("perf", "pusher", "bootAt"), 1.6e12, "perf/pusher/bootAt")),
                                 ((("perf", "heap", "marks"), [2.5e12, 1.5e12], "perf/heap/marks/1")),
                                 ((("usage", "firstSeen"), 2.0e12, "usage/firstSeen"))):
            doc = pe.export_document(leak_snapshot(), usage=True)
            node = doc
            for k in path[:-1]:
                node = node[k]
            node[path[-1]] = raw
            self.assertEqual([(p.kind, p.is_key, p.path, p.depth) for p in pp.denylist_problems(doc, under=("perf",), skip=("schema",))],
                             [("a number the size of a clock stamp", False, where, where.count("/") + 1)], where)
            self.assertEqual(_check(doc), "the public form still fails the denylist (a number the size of a clock stamp, the value at %s); nothing written" % where)
        doc = pe.export_document(leak_snapshot())
        doc["perf"]["pusher"]["cycles"] = 1_499_999_999
        self.assertEqual(pp.denylist_problems(doc, under=("perf",), skip=("schema",)), [], "below the seconds window a number is a count")
        # OUTSIDE BOTH WINDOWS a float is a measurement, whatever its size and wherever it sits (fails before: each was the
        # stamp finding, and check_document named perf/process/malloc/arena): glibc's allocator figures on a long-lived
        # kernel (the fifth review round's numbers), above the seconds window; a float between the windows; one above the
        # milliseconds window; one just below the seconds window; in a list and in `usage` too
        doc = pe.export_document(leak_snapshot(), usage=True)
        self.assertNotIn("malloc", doc["perf"]["process"], "the fixture carries no allocator block; the case plants one")
        doc["perf"]["process"]["malloc"] = {"arena": 2931437568.0, "hblkhd": 3.5e9, "uordblks": 2731423520.0, "fordblks": 2_000_000_000.5}
        doc["perf"]["pusher"]["startedAt"] = 2.9e9
        doc["perf"]["heap"]["marks"] = [1, 2_000_000_001.0, 1.0e12, 2.5e12, 1e300]
        doc["perf"]["pusher"]["cycles"] = 1_499_999_999.5
        doc["usage"]["firstSeen"] = 2.5e12
        self.assertEqual(pp.denylist_problems(doc, under=("perf",), skip=("schema",)), [], "a float outside both windows is a measurement")
        self.assertIsNone(_check(doc))
        # the edges: both ends of each window in, the values just past them out
        for raw, stamp in ((1.5e9, True), (2.0e9, True), (1_499_999_999.9, False), (2_000_000_000.5, False),
                           (1.5e12, True), (2.0e12, True), (1_499_999_999_999.9, False), (2_000_000_000_000.5, False)):
            doc = pe.export_document(leak_snapshot())
            doc["perf"]["pusher"]["startedAt"] = raw
            self.assertEqual([p.kind for p in pp.denylist_problems(doc, under=("perf",), skip=("schema",))],
                             ["a number the size of a clock stamp"] if stamp else [], repr(raw))
        # an INTEGER inside a window is a count or a byte total, not a stamp, whatever its size and wherever it sits: under a
        # bytes-named key (the kernel's lifetime wire totals pass 2e9 within hours), under a key the denylist does not know,
        # in a list, in `usage`; the same value as a float, at the seconds window's ceiling, is the stamp finding (fails
        # before the integer exemption: every one refused)
        doc = pe.export_document(leak_snapshot(), usage=True)
        doc["perf"]["pusher"]["clients"]["byKind"]["chrome"]["bytes"] = 2_000_000_000
        doc["perf"]["pusher"]["clients"]["byApp"]["chat"]["bytes"] = 2_000_000_000
        doc["perf"]["parses"]["bytes"] = 2_000_000_000
        doc["perf"]["pusher"]["startedAt"] = 2_000_000_000
        doc["perf"]["heap"]["marks"] = [1, 2_000_000_000, 1 << 40]
        doc["usage"]["firstSeen"] = 1_700_000_000
        self.assertEqual(pp.denylist_problems(doc, under=("perf",), skip=("schema",)), [], "an integer past the floor is a total, not a stamp")
        self.assertIsNone(_check(doc))
        doc["perf"]["pusher"]["startedAt"] = 2_000_000_000.0
        self.assertEqual([(p.kind, p.path) for p in pp.denylist_problems(doc, under=("perf",), skip=("schema",))],
                         [("a number the size of a clock stamp", "perf/pusher/startedAt")], "the same value as a float is a stamp")
        # one finding per leaf: under an uptime key the grain is judged first (1.6e9 is off it), and on the grain the window
        # (1.5e9 is 25 million whole minutes) as a float; the same as an integer is what public_uptime writes and passes;
        # under a denied key nothing beneath is walked, so the key finding stands alone
        doc = pe.export_document(leak_snapshot())
        doc["perf"]["uptime_s"] = 1.6e9
        self.assertEqual([p.kind for p in pp.denylist_problems(doc, under=("perf",), skip=("schema",))], ["an uptime not rounded to whole minutes"])
        doc["perf"]["uptime_s"] = 1.5e9
        self.assertEqual([(p.kind, p.path) for p in pp.denylist_problems(doc, under=("perf",), skip=("schema",))], [("a number the size of a clock stamp", "perf/uptime_s")])
        doc["perf"]["uptime_s"] = 1_500_000_000
        self.assertEqual(pp.denylist_problems(doc, under=("perf",), skip=("schema",)), [], "an integer uptime on the grain is the fold's own")
        doc = pe.export_document(leak_snapshot())
        doc["perf"]["pusher"]["firstCycle"]["t"] = 1.7e9
        self.assertEqual([(p.kind, p.is_key, p.path) for p in pp.denylist_problems(doc, under=("perf",), skip=("schema",))],
                         [("a key the denylist drops", True, "perf/pusher/firstCycle")])
        # the depth rule with the new findings: a shallower key finding wins over a deeper value finding, and a value finding
        # at the root's child over a deeper key finding
        doc = pe.export_document(bounds_snapshot())
        doc["perf"]["heap"]["hydrated"]["capBytes"] = 3
        doc["perf"]["heap"]["t"] = 1
        self.assertEqual(_check(doc), "the public form still fails the denylist (a key the denylist drops, a key under perf/heap); nothing written")
        doc = pe.export_document(bounds_snapshot())
        doc["perf"]["startedAt"] = 1.7e9
        doc["perf"]["heap"]["hydrated"]["t"] = 1
        self.assertEqual(_check(doc), "the public form still fails the denylist (a number the size of a clock stamp, the value at perf/startedAt); nothing written")

    def test_a_bound_under_two_keys_that_fold_to_the_same_name_is_re_coarsened_after_the_merge(self):
        """Two sibling keys outside the grammar fold to one `other` and their subtrees merge, numbers summed; each side's
        bound had already been rounded up to a power of two, and a sum of two powers of two is one only when they are
        equal, so the fold's own output failed its denylist walk (a bound not rounded to a power of two) at every such
        collision and the export refused itself (the upload's second review round, 2026-09-18). The collision is always at
        an ancestor folded to `other` (two bound keys cannot collide in one dict), so the fix is in _merge, after the sum.
        The uptime needs none and is pinned as already closed: a sum of whole minutes is whole minutes. Fails before: 3072,
        and 12 for 3 and 5 (each coarsened to 4 and 8 before the sum), both refused as a bound not rounded to a power of
        two. The float variant, two measurement floats summed into a stamp window, is not closed here and is not claimed."""
        self.assertEqual(pp.fold({"memos": {"a table name": {"bound": 1024}, "another table name": {"bound": 2048}}}),
                         {"memos": {"other": {"bound": 4096}}})
        self.assertEqual(pp.fold({"heap": {"a b": {"capBytes": 3, "bytes": 1}, "c d": {"capBytes": 5, "bytes": 2}}}),
                         {"heap": {"other": {"capBytes": 16, "bytes": 3}}}, "3 and 5 coarsen to 4 and 8, sum to 12, coarsen to 16; the occupancy is summed")
        self.assertEqual(pp.fold({"x": {"a b": {"cap": 1}, "c d": {"cap": 1}}}), {"x": {"other": {"cap": 2}}}, "equal powers sum to a power")
        self.assertEqual(pp.fold({"x": {"a b": {"deep": {"bound": 6}}, "c d": {"deep": {"bound": 6}}}}), {"x": {"other": {"deep": {"bound": 16}}}},
                         "and at depth inside the merged subtrees")
        self.assertEqual(pp.fold({"memos": {"a k": {"uptime_s": 100}, "b k": {"uptime_s": 100}}}), {"memos": {"other": {"uptime_s": 120}}},
                         "the uptime is closed under the merge already")
        for snap in ({"memos": {"a table name": {"bound": 1024}, "another table name": {"bound": 2048}}},
                     {"heap": {"a b": {"capBytes": 3}, "c d": {"capBytes": 5}}},
                     {"memos": {"a k": {"uptime_s": 100}, "b k": {"uptime_s": 100}}}):
            self.assertEqual(pp.denylist_problems(pp.fold(snap)), [], repr(snap))
        # through the export: a snapshot with such a collision folds to a document that passes its own check (fails before:
        # refused as a bound not rounded to a power of two at perf/memos/other/bound)
        snap = leak_snapshot()
        snap["memos"]["a table name"] = {"bytes": 10, "bound": 1024}
        snap["memos"]["another table name"] = {"bytes": 11, "bound": 2048}
        doc = pe.export_document(snap, usage=True)
        self.assertEqual(doc["perf"]["memos"]["other"], {"bytes": 21, "bound": 4096})
        self.assertEqual(pp.denylist_problems(doc, under=("perf",), skip=("schema",)), [])
        self.assertIsNone(_check(doc))
        self.assertEqual(pp.fold(doc["perf"]), doc["perf"], "and the output is its own fold")

    def test_a_float_under_a_duration_key_is_never_judged_against_the_stamp_windows(self):
        """The kernel's millisecond totals are FLOATS and cumulative: pusher.cycle_cpu_ms_sum read 1,779,484.0 after one
        hour on a busy kernel, about 35 days to 1.5e9 and twelve more across the seconds window, and the other ms sums
        climb behind it, so a rule over every float refused a fresh export from a long-lived kernel by its own belt
        (2026-09-18). A float inside a STAMP_WINDOWS window under a DURATION key (duration_key: a name whose tokens, split
        on underscores and camelCase boundaries, carry `ms` in any case) is a total and never a finding; under every other
        key outside BOUND_KEYS it stays the stamp finding at its path, the type, the size and the key deciding together.
        The exemption reads the leaf's own key and every dict key
        above it (the ANCESTOR rule, the same day: stages_ms is a dict of lifetime millisecond sums keyed by stage names,
        push, jobs, push.chat, so its leaf keys carry no `ms` token while the parent does, and the sums climb like
        cycle_cpu_ms_sum), so a list element, which has no key of its own, passes under a duration key and is judged under
        any other, and a leaf whose own key is one passes whatever its parents (a stageRing row's `ms`). Fails before:
        cycle_cpu_ms_sum 2.0e9 and wallMs 1.6e9 were refused as stamps, and check_document named
        perf/pusher/cycle_cpu_ms_sum; with the leaf-only reading, perf/stages_ms/push at 2.0e9 was refused too."""
        # the tokenizer: underscores and camelCase boundaries, an uppercase run kept whole before a capitalized word; the
        # boundary and the token are the receiver's, read by name from here
        self.assertEqual(pp.KEY_TOKEN_BOUNDARY.pattern, r"_+|(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")
        self.assertEqual(pp.DURATION_TOKEN, "ms")
        self.assertEqual(pp.KEY_TOKEN_BOUNDARY.split("__msgs__"), ["", "msgs", ""])
        self.assertEqual(pp.key_tokens("cycle_cpu_ms_sum"), ["cycle", "cpu", "ms", "sum"])
        self.assertEqual(pp.key_tokens("tierCpuMs"), ["tier", "Cpu", "Ms"])
        self.assertEqual(pp.key_tokens("HTTPMs"), ["HTTP", "Ms"])
        self.assertEqual(pp.key_tokens("p95Ms"), ["p95", "Ms"])
        self.assertEqual(pp.key_tokens("__msgs__"), ["msgs"])
        self.assertEqual(pp.key_tokens("sendMax"), ["send", "Max"])
        self.assertEqual(pp.key_tokens("ms2"), ["ms2"])         # a digit joins its letters: the gc row's gen-2 time is one token
        self.assertEqual(pp.key_tokens(""), [])
        for name, ok in (("cycle_cpu_ms_sum", True), ("ms_sum", True), ("ms_max", True), ("wallMs", True), ("sendMs", True),
                         ("restoreMs", True), ("held_ms", True), ("tierCpuMs", True), ("ms", True), ("MS", True), ("Ms", True),
                         ("cpuMS", True), ("ms_bytes", True), ("stages_ms", True),
                         ("sendMax", False), ("startedAt", False), ("bytes", False), ("sigMsgs", False), ("promptMsgId", False),
                         ("msgs", False), ("items", False), ("ms2", False), ("terms", False), ("t", False), ("", False)):
            self.assertIs(pp.duration_key(name), ok, name)
        self.assertFalse(pp.duration_key(None))     # a list element's key
        self.assertFalse(pp.duration_key(3))
        # a float inside a window under a duration key passes, in the fold's own places and under a new one, in `usage` too,
        # in the milliseconds window too (every value here sits inside a window, so the exemption is what passes it; a float
        # outside both passes by its size alone); the fixed point over every fixture holds (the case above)
        doc = pe.export_document(leak_snapshot(), usage=True)
        doc["perf"]["pusher"]["cycle_cpu_ms_sum"] = 2.0e9
        doc["perf"]["judge"]["child"]["wallMs"] = 1.6e9
        doc["perf"]["judge"]["ms_sum"] = 1.5e9
        doc["perf"]["jobs"]["pass_ms_max"] = 1.7e9
        doc["perf"]["heap"]["tierCpuMs"] = 1.9e9
        doc["perf"]["pusher"]["held_ms"] = 1_600_000_000.5
        doc["perf"]["judge"]["wall_ms_sum"] = 1.6e12
        doc["usage"]["restoreMs"] = 1.6e9
        self.assertEqual(pp.denylist_problems(doc, under=("perf",), skip=("schema",)), [], "a millisecond total is a duration, not a stamp")
        self.assertIsNone(_check(doc))
        # the same float under a key that is not a duration by name is the stamp finding at its path, the number in no field
        for name in ("startedAt", "sendMax", "bytes", "sigMsgs"):
            doc = pe.export_document(leak_snapshot())
            doc["perf"]["pusher"][name] = 1.6e9
            self.assertEqual([(p.kind, p.is_key, p.path, p.depth) for p in pp.denylist_problems(doc, under=("perf",), skip=("schema",))],
                             [("a number the size of a clock stamp", False, "perf/pusher/" + name, 3)], name)
            self.assertEqual(_check(doc), "the public form still fails the denylist (a number the size of a clock stamp, "
                                          "the value at perf/pusher/%s); nothing written" % name)
        doc = pe.export_document(leak_snapshot())
        doc["perf"]["pusher"]["sendMax"] = 1.6e12
        self.assertEqual([(p.kind, p.path) for p in pp.denylist_problems(doc, under=("perf",), skip=("schema",))],
                         [("a number the size of a clock stamp", "perf/pusher/sendMax")], "a millisecond stamp under a key that is not a duration")
        # THE ANCESTOR RULE: a float passes when any key on its path is a duration key. stages_ms is keyed by stage names,
        # so the parent carries the token and the leaves do not, at any depth (a dotted seam's parts as a nested dict).
        # Fails before: perf/stages_ms/push was the stamp finding
        doc = pe.export_document(leak_snapshot(), usage=True)
        self.assertEqual(doc["perf"]["stages_ms"]["jobs"], 5000.0)
        doc["perf"]["stages_ms"]["push"] = 2.0e9
        doc["perf"]["stages_ms"]["jobs"] = {"autoNudge": 1.6e9, "parse": {"cold": 1.5e9}}
        self.assertEqual(pp.denylist_problems(doc, under=("perf",), skip=("schema",)), [], "a float below a duration key is a total")
        self.assertIsNone(_check(doc))
        # a list under a duration key: the element has no key of its own and passes by the ring's key above it (this pin
        # read the element's own key alone before the ancestor rule and refused perf/pusher/cycle_ms_ring/1); a list under
        # a key that is not one is judged as before, and the path carries the index
        doc = pe.export_document(leak_snapshot())
        doc["perf"]["pusher"]["cycle_ms_ring"] = [1.0, 1.6e9, [2.0e9]]
        self.assertEqual(pp.denylist_problems(doc, under=("perf",), skip=("schema",)), [], "an element of a list under a duration key")
        doc["perf"]["pusher"]["cycle_ring"] = [1.0, 1.6e9]
        self.assertEqual([(p.kind, p.path) for p in pp.denylist_problems(doc, under=("perf",), skip=("schema",))],
                         [("a number the size of a clock stamp", "perf/pusher/cycle_ring/1")])
        # the LEAF rule stands on its own: a stageRing row's stage split sits under keys none of which is a duration (jobs,
        # stageRing, the index, stages, jobs), its `ms` passes by its own key, and the row's `bytes` beside it, the same
        # float under the same parents, is the stamp finding at its depth; a key with no duration anywhere on its path is
        # refused as before
        doc = pe.export_document(leak_snapshot())
        row = doc["perf"]["jobs"]["stageRing"][0]["stages"]["jobs"]
        self.assertEqual(sorted(row), ["bytes", "hydrated", "ms"])
        row["ms"] = 1.6e9
        self.assertEqual(pp.denylist_problems(doc, under=("perf",), skip=("schema",)), [], "a leaf `ms` under parents that are not durations")
        row["bytes"] = 1.6e9
        self.assertEqual([(p.kind, p.is_key, p.path, p.depth) for p in pp.denylist_problems(doc, under=("perf",), skip=("schema",))],
                         [("a number the size of a clock stamp", False, "perf/jobs/stageRing/0/stages/jobs/bytes", 7)])
        doc = pe.export_document(leak_snapshot())
        doc["perf"]["pusher"]["startedAt"] = 1.6e9
        self.assertEqual([(p.kind, p.path) for p in pp.denylist_problems(doc, under=("perf",), skip=("schema",))],
                         [("a number the size of a clock stamp", "perf/pusher/startedAt")], "no duration key on the path")
        # a duration key exempts the stamp finding alone: an uptime or a bound is judged by its own coarsening first, as before
        doc = pe.export_document(leak_snapshot())
        doc["perf"]["uptime_s"] = 1.6e9
        self.assertEqual([p.kind for p in pp.denylist_problems(doc, under=("perf",), skip=("schema",))], ["an uptime not rounded to whole minutes"])
        # THE EXEMPTION IS BY NAME AT ANY DEPTH, on purpose (the upload's third review round, 2026-09-18): a float two levels
        # under an invented ancestor carrying the token (ms_x) is NOT a finding, and the same float under a plain ancestor (x)
        # at the same depth IS one. The belt catches a stamp typed under a new key by accident and is not an adversarial
        # control (an editor can spell a stamp as an integer or a quoted string under any key); a narrowing to the leaf's key
        # or its parent would not close that road, nor the finding's own case (a float directly under an invented ms-named
        # key, which is then the parent), and a checked-in list of duration parents would bring back the false refusals the
        # ancestor rule exists to avoid, so it is not taken (the kernel's stages_ms is a flat dict, so its leaves stay exempt
        # under either rule), and this pin documents the accepted case rather than leaving it to be rediscovered
        for ancestor, findings in (("ms_x", []), ("x", [("a number the size of a clock stamp", "perf/x/a/b")])):
            doc = pe.export_document(leak_snapshot())
            doc["perf"][ancestor] = {"a": {"b": 1.7e9}}
            self.assertEqual([(p.kind, p.path) for p in pp.denylist_problems(doc, under=("perf",), skip=("schema",))], findings, ancestor)

    def test_the_denylist_walk_refuses_what_the_fold_would_have_folded_a_string_outside_the_grammar_and_a_key_its_anchored_match_admits(self):
        """The two findings that make the re-check hold a file to the fold's own rule and not to the walk's (the upload's
        second review round, 2026-09-18). The walk judges a KEY by `.match` against a `$`-anchored grammar, which admits a
        trailing newline after a good name (and the joined grammar has no length cap there), and a string VALUE for a
        uuid, a hex token, a path and whitespace, so a 43-character token with none of them passed it; the fold's
        `_public_key` fullmatches and caps, and folds every string outside IDENT to `other`. So a file carrying either was
        changed after the export and would have been POSTed at the previous head. Each is one path-precise finding of the
        denylist walk: a key finding at the dict holding it (its value still walked), a value finding at its own path, in a
        dict or a list, under a bound key too (a string is judged by the grammar alone); check_document names them with the
        denylist wording and the token reaches no output. The schema line is not judged with the same skip the scan and the
        walk take (without it the envelope's slash would be the finding on every export). The fixed point still holds over
        every fixture and both usage settings, and every top-level block outside the envelope equals its own fold, which with
        the upload's top-level allowlist is the belt `romp perf upload` adds under the checks. Fails before: the walk reported
        [] for all of them."""
        token = "zz-planted-token-past-thirty-two-chars-zz"     # 41 characters, no whitespace, no hex run: silent to the walk
        self.assertIsNone(pp.IDENT.fullmatch(token))
        self.assertEqual(pp.fold(token), "other")
        doc = pe.export_document(leak_snapshot(), usage=True)
        doc["perf"]["heap"]["tok"] = token
        doc["perf"]["heap"]["list"] = ["ok", token]
        doc["perf"]["heap"]["capBytes"] = token
        doc["perf"]["pusher"]["cycles\n"] = 1
        doc["perf"]["recordCache"]["wholeReads"]["leaf<-_parse\n"] = {"count": 1, "bytes": 5}
        doc["perf"]["recordCache"]["wholeReadsByStage"]["x" * 97] = {"count": 1}
        for k in ("cycles\n", "leaf<-_parse\n", "x" * 97):
            self.assertIsNotNone(pp.IDENT.match(k) if k == "cycles\n" else pp.JOINED_KEY.match(k), "the walk's anchored match admits it")
            self.assertEqual(pp._public_key(k, () if k == "cycles\n" else ("recordCache", "wholeReads")), "other", "the fold does not")
        self.assertEqual(pp.paste_problems(doc, skip=("schema",), under=("perf",)), [], "the walk is silent on every one")
        self.assertEqual(sorted((p.kind, p.is_key, p.path, p.depth) for p in pp.denylist_problems(doc, under=("perf",), skip=("schema",))),
                         sorted([("a string the fold would have folded", False, "perf/heap/tok", 3),
                                 ("a string the fold would have folded", False, "perf/heap/list/1", 4),
                                 ("a string the fold would have folded", False, "perf/heap/capBytes", 3),
                                 ("a key the fold would have folded", True, "perf/pusher", 2),
                                 ("a key the fold would have folded", True, "perf/recordCache/wholeReads", 3),
                                 ("a key the fold would have folded", True, "perf/recordCache/wholeReadsByStage", 3)]))
        self.assertTrue(all(token not in str(p.kind) and token not in p.path for p in pp.denylist_problems(doc, under=("perf",), skip=("schema",))))
        # each alone through check_document: the denylist wording, the kind and the path, the token and the key in no output
        for plant, line in (((("perf", "heap", "tok"), token), "a string the fold would have folded, the value at perf/heap/tok"),
                            (((("perf", "heap", "list"), ["ok", token])), "a string the fold would have folded, the value at perf/heap/list/1"),
                            (((("perf", "pusher", "cycles\n"), 1)), "a key the fold would have folded, a key under perf/pusher"),
                            (((("perf", "recordCache", "wholeReads", "leaf<-_parse\n"), {"count": 1})), "a key the fold would have folded, a key under perf/recordCache/wholeReads"),
                            (((("extra",), {"note": token})), "a string the fold would have folded, the value at extra/note")):
            doc = pe.export_document(leak_snapshot(), usage=True)
            node = doc
            for k in plant[0][:-1]:
                node = node[k]
            node[plant[0][-1]] = plant[1]
            reason = _check(doc)
            self.assertEqual(reason, "the public form still fails the denylist (%s); nothing written" % line)
            self.assertNotIn(token, reason)
            self.assertNotIn("\n", reason)
        # the http block: a key outside the register's image is the walk's finding first and the fold's too (it collapses)
        doc = pe.export_document(leak_snapshot())
        doc["perf"]["http"]["GET /dist/render.js"] = {"count": 1}
        self.assertEqual([p.kind for p in pp.denylist_problems(doc, under=("perf",), skip=("schema",))], ["a key the fold would have folded"])
        self.assertEqual(_check(doc), "the public form still fails the walk (outside the image of the route register, a key under perf/http); nothing written")
        # the key finding leaves the value walked: a stamp beneath a folded key is named too
        doc = pe.export_document(leak_snapshot())
        doc["perf"]["pusher"]["ring\n"] = {"startedAt": 1.6e9}
        self.assertEqual([(p.kind, p.path) for p in pp.denylist_problems(doc, under=("perf",), skip=("schema",))],
                         [("a key the fold would have folded", "perf/pusher"), ("a number the size of a clock stamp", "perf/pusher/ring\n/startedAt")])
        # the schema line: judged without the skip (the envelope's slash), not judged with it, as the scan and the walk take it
        doc = pe.export_document(leak_snapshot())
        self.assertEqual([(p.kind, p.path) for p in pp.denylist_problems(doc, under=("perf",))], [("a string the fold would have folded", "schema")])
        self.assertEqual(pp.denylist_problems(doc, under=("perf",), skip=("schema",)), [])
        self.assertIsNone(_check(doc))
        # the fixed point, and the belt: every block outside the envelope is its own fold, on every fixture, both usage settings
        self.assertEqual(pe.ENVELOPE_KEYS, ("schema", "exported_at", "kernel_commit"))
        for snap in (leak_snapshot(), _epoch(leak_snapshot()), bounds_snapshot(), bounds_snapshot(8 * 1024 ** 3)):
            for usage in (False, True):
                doc = pe.export_document(snap, usage=usage)
                self.assertEqual(pp.denylist_problems(doc, under=("perf",), skip=("schema",)), [])
                self.assertEqual(set(doc) - {"perf", "usage"}, set(doc) & set(pe.ENVELOPE_KEYS), "the envelope and the blocks, nothing else")
                for k in doc:
                    if k not in pe.ENVELOPE_KEYS:
                        self.assertEqual(pp.fold(doc[k]), doc[k], k)
                        self.assertEqual(pp.fold(pp.fold(doc[k])), pp.fold(doc[k]), "and the fold is idempotent")

    def test_the_walk_holds_the_http_block_to_the_registers_image_and_the_stack_sample_to_its_grammars(self):
        # the walk's http check is membership in what the kernel's fold can return (http_key_ok), not a character grammar:
        # a path-shaped key the register never makes is named. The stack sample rides in a served snapshot under its
        # switch (the export drops it, DENY_KEYS): its keys are "<ident> <kind>" and its frames "function (file:line)"
        kinds = _kinds
        self.assertEqual(kinds({"http": {"GET /perf": {"count": 1}, "POST /remote/*/send": {"count": 1}, "GET /dist/*": {"count": 1}, "other": {"count": 1}}}), [])
        self.assertEqual(kinds({"http": {"GET /nope": {"count": 1}}}), ["outside the image of the route register"])
        self.assertEqual(kinds({"http": {"HEAD /perf": {"count": 1}}}), ["outside the image of the route register"], "a route of another method")
        self.assertEqual(kinds({"http": {"GET /remote/TESTHOST/sessions": {"count": 1}}}), ["outside the image of the route register"])
        self.assertEqual(kinds({"perf": {"http": {"GET /nope": 1}}}, under=("perf",)), ["outside the image of the route register"], "below the export's envelope")
        self.assertEqual(kinds({"http": {"GET /nope": 1}}, under=("perf",)), ["outside the identifier grammar"], "at the root of an export, http is a plain block")
        stacks = {"stacks": {"11 pusher": {"self": False, "stage": "http.GET.other",
                                           "frames": ["_pusher (kernel.py:100)", "<lambda> (kernel.py:7)", "<module> (<frozen importlib._bootstrap>:1)", "run (threading.py:1000)"]},
                             "12 ?": {"self": True, "stage": None, "frames": []}}}
        self.assertEqual(kinds(stacks), [])
        self.assertEqual(kinds({"stacks": {"pusher": {}}}), ["outside the stack sample's key grammar"], "no ident")
        self.assertEqual(kinds({"stacks": {"11 sdk:web": {}}}), ["outside the stack sample's key grammar"], "a thread name's payload")
        self.assertEqual(kinds({"stacks": {"11 pusher": {"frames": ["go (%s/kernel.py:3)" % HOME]}}}), ["an absolute path", "outside the frame grammar"])
        self.assertEqual(kinds({"stacks": {"11 pusher": {"frames": ["go kernel.py:3"]}}}), ["outside the frame grammar"], "free text in a frame slot is the frame rule's")
        self.assertEqual(kinds({"stacks": {"11 pusher": {"stage": "jobs auto"}}}), ["free text"], "a stage value is not a frame")
        self.assertEqual(kinds({"stacks": {"11 pusher": {"frames": ["_pusher (kernel.py:100)"]}}}, ident=re.compile(r"^[A-Za-z0-9_.-]+$")), [])
        # the module's stack-key grammar is the character one: the export drops the block and the cli never loads the
        # kernel, so it holds no copy of the kernel's register of thread kinds. A caller that does (the served walk in
        # tests/test_perf_stats.py) passes the register's grammar, under which a thread's name is not a kind
        reg = re.compile(r"^[0-9]+ (?:(?:judge-)*(?:%s)|other)$" % "|".join(sorted(map(re.escape, km._THREAD_KIND_WORDS))))
        rows = {"stacks": {"11 probe-thread": {}, "12 other": {}, "13 judge-index": {}, "14 pusher": {}}}
        self.assertEqual(kinds(rows), [], "the module's grammar admits any kind token")
        self.assertEqual(kinds(rows, stacks_key=reg), ["outside the stack sample's key grammar"], "the register's admits its words, judge- composites and other alone")
        self.assertEqual(kinds({"perf": rows}, under=("perf",), stacks_key=reg), ["outside the stack sample's key grammar"], "below the export's envelope too")
        self.assertEqual(kinds({"stacks": {"12 ?": {}}}, stacks_key=reg), ["outside the stack sample's key grammar"], "the pre-register token is outside the register's grammar")
        self.assertIn("stacks", pp.DENY_KEYS, "the export never carries the block; the grammars are for the served walk")
        self.assertNotIn("stacks", pe.export_document(leak_snapshot())["perf"])

    def test_the_envelope(self):
        self.assertEqual(self.doc["schema"], "romp-perf-export/1")
        self.assertRegex(self.doc["exported_at"], STAMP)
        self.assertEqual(self.doc["kernel_commit"], SHA[:12])
        self.assertEqual(sorted(self.doc), ["exported_at", "kernel_commit", "perf", "schema", "usage"])
        without = pe.export_document({"uptime_s": 1.0})
        self.assertNotIn("kernel_commit", without, "absent when the snapshot carries none")
        self.assertNotIn("usage", without, "usage is opt-in")
        self.assertNotIn("kernel_commit", pe.export_document({"kernel_sha": "not a sha"}))

    def test_the_fold_is_the_same_over_every_shape(self):
        self.assertEqual(pp.fold({"a b": 1, "c d": 2, "ok": 3}), {"other": 3, "ok": 3})
        self.assertEqual(pp.fold({"a b": {"x": 1, "y": [1]}, "c d": {"x": 2, "y": [2], "z": "q r"}}),
                         {"other": {"x": 3, "y": [1, 2], "z": "other"}})
        self.assertEqual(pp.fold({"a b": "one", "c d": "two"}), {"other": "other"}, "two folded strings that disagree")
        self.assertEqual(pp.fold({"a b": "same", "c d": "same"}), {"other": "same"})
        self.assertEqual(pp.fold({"a b": True, "c d": False}), {"other": "other"})
        self.assertEqual(pp.fold(["x y", "ok", 1.5, None, True]), ["other", "ok", 1.5, None, True])
        # a non-finite number is nulled before the merge, and null is the identity: the counter beside it stays a
        # number (it used to become the word `other`, a counter losing its type and its measurement), a dict a
        # dict, a bool a bool; two nulls are null
        nan = float("nan")
        self.assertEqual(pp.fold({"a b": nan, "c d": 2.0}), {"other": 2.0})
        self.assertEqual(pp.fold({"a b": 2.0, "c d": nan}), {"other": 2.0}, "either side")
        self.assertEqual(pp.fold({"a b": 3, "c d": float("inf"), "e f": 4}), {"other": 7})
        self.assertEqual(pp.fold({"a b": None, "c d": {"x": 1}}), {"other": {"x": 1}})
        self.assertEqual(pp.fold({"a b": None, "c d": True}), {"other": True}, "null beside a bool keeps the bool")
        self.assertEqual(pp.fold({"a b": None, "c d": None}), {"other": None})
        self.assertEqual(pp.fold({"a b": None, "c d": "ok"}), {"other": "ok"})
        self.assertEqual(pp._merge(None, 5), 5)
        self.assertEqual(pp._merge(False, None), False)
        self.assertEqual(pp.fold({"k" * 33: 1, "k" * 32: 2}), {"other": 1, "k" * 32: 2}, "the 32-character cap")
        self.assertEqual(pp.fold({"a:b": 1}), {"a:b": 1}, "the browser grammar keeps the colon")
        self.assertEqual(pp.fold({"sid": SID, "n": 1}), {"n": 1})
        self.assertEqual(pp.fold({"checkpoints": {"readByPath": {}, "restored": 1}}), {"checkpoints": {"restored": 1}})
        self.assertEqual(pp.fold({"x": {"readByPath": {"/a/b": 1}}}), {"x": {}}, "readByPath is dropped wherever it appears")

    def test_a_pid_under_any_spelling_goes_and_a_word_ending_in_pid_does_not(self):
        # the ledgers spell a process id pid, ppid, pids, cliPid, hostPid (a session host's attach row), managerPid
        # (the kernel's audit rows), hub_pid and boundary_pids; a rule over the spelling catches the next one too
        pids = {"pid": 1, "ppid": 2, "pids": "7,8", "cliPid": 3, "hostPid": 4, "managerPid": 5, "hub_pid": 6,
                "boundary_pids": [7], "leasePid": 8, "PID": 9}
        words = {"rapid": 10, "cupid": 11, "pidgin": 12, "spider": 13}
        self.assertEqual(pp.fold(dict(pids, **words)), words)
        self.assertEqual(pp.fold({"events": [{"kind": "host.attached", "hostPid": 20, "cliPid": 21, "boot": True}]}),
                         {"events": [{"kind": "host.attached", "boot": True}]})
        for k in pids:
            self.assertTrue(pp.denied(k, 1), k)
        for k in words:
            self.assertFalse(pp.denied(k, 1), k)

    def test_an_identity_key_over_a_count_is_a_counter_and_stays(self):
        # builds.chat.bg_miss has one integer per chat-signature label, three of them named names, host and cwd; the
        # listing's missBy has a `names` reason: a key that names an identity drops only a value that can carry text
        self.assertEqual(self.perf["builds"]["chat"]["bg_miss"], {"transcript": 5, "names": 2, "host": 1, "cwd": 3, "cold": 1})
        self.assertEqual(self.perf["memos"]["sessionsListing"], {"built": 3, "missBy": {"names": 4, "rows": 1, "first": 1}})
        self.assertEqual(pp.fold({"name": "web", "names": ["web"], "host": {"web": 1}, "cwd": "/x/y", "user": True, "label": 2.5, "unit": None}),
                         {"user": True, "label": 2.5, "unit": None}, "a string, a list or a dict under an identity key goes; a scalar that is no text stays")
        self.assertTrue(pp.denied("host", "TESTHOST"))
        self.assertFalse(pp.denied("host", 3))
        self.assertTrue(pp.denied("sid", 3), "a session id is never a count")
        self.assertTrue(pp.denied("started", 1000), "a stamp is a number and still goes")

    def test_the_ident_grammar_is_the_browsers(self):
        src = open(os.path.join(ROOT, "ui", "webview", "perf-telemetry.ts"), encoding="utf-8").read()
        m = re.search(r"function ident\(s: unknown\): string \{[^}]*?/(\^[^/]+\$)/\.test", src, re.S)
        self.assertIsNotNone(m, "perf-telemetry.ts's ident() regex")
        self.assertEqual(pp.IDENT.pattern, m.group(1))

    def test_the_denylist_names_every_path_the_answer_lists(self):
        self.assertIn(("checkpoints", "readByPath"), pp.DENY_PATHS)
        self.assertIn(("judge", "child", "failures", "first"), pp.DENY_PATHS)
        for key in ("bySid", "byPath", "readByPath", "stacks", "pid", "sid", "name", "cutSessions", "scope", "label", "path", "cwd", "host", "hostname", "user"):
            self.assertTrue(pp.denied(key, "text"), key)
        # the restart document's free-text fields: a session-events row's `text` (problem_row's prose), a cut row's
        # `drainError` and `reasonError` (exception messages). A message that is one token of at most 32 characters
        # passes the grammar, so the keys are denied whatever the value; none is ever a counter
        for key in ("text", "drainError", "reasonError"):
            self.assertIn(key, pp.DENY_KEYS, key)
            self.assertTrue(pp.denied(key, "boom"), key)
            self.assertTrue(pp.denied(key, 1), key)
        self.assertEqual(pp.fold({"events": [{"kind": "drain.unjoined", "text": "TESTHOST", "n": 1}],
                                  "restarts": [{"drainError": "boom", "reasonError": "TESTHOST", "stopped": 5}]}),
                         {"events": [{"kind": "drain.unjoined", "n": 1}], "restarts": [{"stopped": 5}]})
        self.assertFalse(pp.denied("first", "text"))
        self.assertNotIn("first", pp.DENY_KEYS | pp.IDENTITY_KEYS, "the chat rows' `first` timing is not an exception message")
        # `t` is a wall-clock stamp wherever GET /perf writes it (the split rows, the judge child's report) and never a
        # counter (checked against the kernel's snapshot builders, 2026-09-18), so it goes at any depth whatever the value
        self.assertIn("t", pp.DENY_KEYS)
        for value in (900.5, 1, None, "text"):
            self.assertTrue(pp.denied("t", value), repr(value))
        self.assertNotIn(("judge", "child", "t"), pp.DENY_PATHS, "the child's stamp is denied by its key now")
        self.assertEqual(pp.fold({"pusher": {"firstCycle": {"s": 0.5, "t": 900.5}, "stageRing": [{"s": 0.2, "t": 1000.4}]}}),
                         {"pusher": {"firstCycle": {"s": 0.5}, "stageRing": [{"s": 0.2}]}})
        # the rule (round 3): every ABSOLUTE clock stamp goes, whatever its key, the restart document's spellings included
        # (a quiet window's restartT is a restart row's t verbatim; firstServe minus the kept outageS is the cut's t);
        # `since` is a key now, not a root path (a quiet window's parked stamp sits at depth); durations stay
        for key in ("since", "until", "started", "generatedAt", "auditT", "firstServe", "reconcileDone", "restartT", "prevCutT", "port"):
            self.assertIn(key, pp.DENY_KEYS, key)
            self.assertTrue(pp.denied(key, 1.7e9), key)
        self.assertNotIn(("since",), pp.DENY_PATHS)
        self.assertIn(("now",), pp.DENY_PATHS)
        for key in ("outageS", "settleS", "waitedS", "uptimeS", "uptime_s", "s", "ms", "start", "end"):
            self.assertFalse(pp.denied(key, 2.5), key + " is a duration or a bucket bound and stays")
        self.assertEqual(pp.fold({"quietWindows": [{"t": 1.7e9, "since": 1.7e9 - 300, "waitedS": 297, "restartT": 1.7e9 + 3, "cutTurns": 2}],
                                  "restarts": [{"t": 1.7e9, "auditT": 1.7e9 - 2, "boot": {"t": 1.7e9 + 2, "firstServe": 1.7e9 + 2.5,
                                                                                            "reconcileDone": 1.7e9 + 2.7, "settleS": 0.2, "outageS": 2.5}}],
                                  "range": {"since": 1.7e9, "until": None}, "live": {"kernel": {"port": 29855, "uptimeS": 61}}}),
                         {"quietWindows": [{"waitedS": 297, "cutTurns": 2}], "restarts": [{"boot": {"settleS": 0.2, "outageS": 2.5}}],
                          "range": {}, "live": {"kernel": {"uptimeS": 60}}})

    def test_no_absolute_clock_stamp_survives_the_export(self):
        # the PROPERTY, not key names (round 3): with every stamp of the leak snapshot moved into the seconds epoch window
        # (the fixture's own are small numbers), no numeric leaf inside an epoch window survives anywhere in the export
        snap = _epoch(leak_snapshot())
        self.assertGreaterEqual(len(_stamps(snap)), 8, "the snapshot carries stamps: now, since, five split rows, the child's")
        doc = pe.export_document(snap, usage=True)
        survivors = _stamps(doc)
        self.assertEqual(survivors, [], "an absolute stamp survives:\n  %s" % "\n  ".join("%s = %r" % s for s in survivors))
        self.assertEqual(doc["perf"]["pusher"]["firstCycle"]["s"], 0.5, "the measurements beside the stamps stay")


class BoundCoarsening(unittest.TestCase):
    """The ten memory-fraction bounds (BOUND_PATHS) are kept and COARSENED (round 3 of the export's review, 2026-09-18): each
    is a fixed fraction of the machine's MemTotal, so every export from one machine shared all ten exactly and
    recordCache.budgetBytes (half of MemTotal) gave the machine's RAM to the kilobyte, a value derived from a machine fact.
    The fold rounds each UP to a power of two (BOUND_KEYS, public_bound), the key kept and the occupancy beside it
    untouched, so a bound that binds stays visible next to its bytes or entries; the machine's memory is not recoverable
    from the result. Fails before: all ten survived exact."""

    def test_the_ten_bounds_are_rounded_up_to_a_power_of_two_and_the_occupancy_beside_them_stays(self):
        snap = bounds_snapshot()
        perf = pe.export_document(snap)["perf"]
        for path in BOUND_PATHS:
            raw, pub = _at(snap, path), _at(perf, path)
            where = "/".join(path)
            self.assertIsInstance(pub, int, where)
            self.assertNotEqual(pub, raw, where + " survives exact")
            self.assertGreater(pub, raw, where + " is rounded UP")
            self.assertLess(pub, 2 * raw, where + " is the next power of two, not a coarser one")
            self.assertEqual(pub & (pub - 1), 0, where + " is a power of two")
        self.assertNotEqual(perf["recordCache"]["budgetBytes"] * 2, MEM_TOTAL, "MemTotal is not budgetBytes times two any more")
        self.assertNotEqual(perf["builds"]["feed"]["memo"]["bound"] * 64, MEM_TOTAL)
        self.assertEqual(perf["judge"]["child"]["recordCache"]["budgetBytes"], perf["recordCache"]["budgetBytes"],
                         "the child's copy of the table is coarsened the same way: the rule is keyed on the name, at any depth")
        # the occupancy and every neighbour stay exact
        self.assertEqual(perf["recordCache"]["bytes"], 123456)
        self.assertEqual(perf["recordCache"]["entries"], 9)
        self.assertEqual(perf["recordCache"]["countCap"], 1024, "a constant count cap is not a memory fraction")
        self.assertEqual(perf["heap"]["hydrated"]["bytes"], 5000)
        self.assertEqual(perf["checkpoints"]["docMemo"]["parseMultiple"], 4.5)
        self.assertEqual(perf["asmIndex"]["resident"], 40)
        self.assertEqual(perf["pusher"]["stageRingLen"], 7)
        self.assertEqual(perf["memos"]["summaryAnchor"]["bytes"], 12)
        self.assertEqual(pp.BOUND_KEYS, frozenset({"capBytes", "budgetBytes", "cap", "bound", "stageRingMax"}))

    def test_public_bound_is_the_next_power_of_two_at_or_above_the_value(self):
        for raw, want in ((1, 1), (2, 2), (3, 4), (4, 4), (5, 8), (1023, 1024), (1024, 1024), (1025, 2048), (2.5, 4), (16.0, 16),
                          (500_000, 524288), (4 * 1024 ** 3, 4 * 1024 ** 3), (4 * 1024 ** 3 + 1, 8 * 1024 ** 3)):
            got = pp.public_bound(raw)
            self.assertEqual(got, want, raw)
            self.assertIsInstance(got, int, raw)
        for same in (0, -5, True, False, None, "other", "a b"):
            self.assertIs(pp.public_bound(same), same, "not a positive number: kept as it is (%r)" % (same,))
        self.assertIsNone(pp.fold({"cap": float("nan")})["cap"], "a non-finite number is null, as before")
        self.assertEqual(pp.fold({"cap": "a b"})["cap"], "other", "a string takes the grammar")
        self.assertEqual(pp.fold({"memos": {"judgingBand": {"entries": 3, "bound": 20000}}}), {"memos": {"judgingBand": {"entries": 3, "bound": 32768}}},
                         "a constant under a bound key is coarsened too: the rule is keyed on the name and costs it nothing")
        self.assertEqual(pp.fold({"recordCache": {"budgetBytes": 4 * 1024 ** 3}}), {"recordCache": {"budgetBytes": 4 * 1024 ** 3}},
                         "a bound that IS a power of two (the floor on a small machine) reads the same, which a reader cannot tell from a rounded one")


class UptimeRounding(unittest.TestCase):
    """`uptime_s` stays (it is the span the lifetime totals cover) but rounded DOWN to whole minutes: to the second,
    beside the export minute (a stamp with no seconds), it placed the kernel's start within a minute, the same start the
    denied `t` carries and constant for the life of the process (the receiver's review, 2026-09-18). A whole-minute
    uptime beside a whole-minute export stamp places the start within two minutes, which the rule accepts: the public
    form is paste-safe, not unlinkable."""

    def test_uptime_is_rounded_down_to_whole_minutes_wherever_it_sits(self):
        self.assertEqual(pp.fold({"uptime_s": 3725}), {"uptime_s": 3720}, "62 min 5 s is 62 whole minutes")
        doc = pe.export_document({"uptime_s": 3725, "process": {}, "pusher": {}, "http": {}})
        self.assertEqual(doc["perf"]["uptime_s"], 3720)
        self.assertIsInstance(doc["perf"]["uptime_s"], int)
        for raw, rounded in ((100.5, 60), (59.999, 0), (0, 0), (3600, 3600), (3600.0, 3600), (7 * 86400 + 59, 7 * 86400)):
            got = pp.fold({"uptime_s": raw})["uptime_s"]
            self.assertEqual(got, rounded, raw)
            self.assertIsInstance(got, int, raw)
            self.assertEqual(got % 60, 0, raw)
        self.assertEqual(pp.fold({"process": {"uptime_s": 3725}}), {"process": {"uptime_s": 3720}}, "at any depth")
        self.assertEqual(pp.fold({"live": {"kernel": {"uptimeS": 100000.0}}}), {"live": {"kernel": {"uptimeS": 99960}}},
                         "the restart document's spelling (GET /version's uptime under live.kernel)")
        self.assertIsNone(pp.fold({"uptime_s": float("nan")})["uptime_s"], "a non-finite number is null, as before")
        self.assertEqual(pp.fold({"uptime_s": "a b"})["uptime_s"], "other", "a string is not an uptime and takes the grammar")
        self.assertIs(pp.fold({"uptime_s": True})["uptime_s"], True, "a bool is not a number here")
        self.assertEqual(pp.public_uptime(3725), 3720)
        self.assertEqual(pp.UPTIME_KEYS, frozenset({"uptime_s", "uptimeS"}))

    def test_the_usage_bucket_reads_the_raw_uptime_and_agrees_with_the_rounded_one(self):
        # usage_block reads the RAW snapshot's uptime_s (the block is built from the snapshot, before the fold); every
        # bucket bound is a whole number of minutes, so the raw value and its rounded form land in the same bucket at
        # every bound, and a bound that is not a whole minute fails here
        for bound, _name in pe.UPTIME_BUCKETS[:-1]:
            self.assertEqual(bound % 60, 0, bound)
        for raw in (3599.9, 3600, 3600.5, 86399.9, 86400, 7 * 86400 - 0.1, 7 * 86400, 3725):
            snap = {"uptime_s": raw, "process": {}, "pusher": {}, "http": {}}
            doc = pe.export_document(snap, usage=True)
            self.assertEqual(doc["usage"]["kernelUptime"], pe.usage_block(snap)["kernelUptime"], raw)
            self.assertEqual(doc["usage"]["kernelUptime"], pe.usage_block({"uptime_s": doc["perf"]["uptime_s"]})["kernelUptime"], raw)
        self.assertEqual(pe.usage_block({"uptime_s": 3599.9})["kernelUptime"], "lt1h")
        self.assertEqual(pe.usage_block({"uptime_s": 3600})["kernelUptime"], "1h-24h")


class Usage(unittest.TestCase):
    """The usage block: counts from keys the snapshot already carries, nothing else."""

    def test_session_counts_actions_views_and_the_uptime_bucket(self):
        u = pe.usage_block(leak_snapshot())
        self.assertEqual(u["sessions"], {"parsed": 2, "chatBuilt": 2, "stamped": 31}, "an old kernel's per-sid table is a count")
        self.assertEqual(u["actions"], {"send": 7, "new": 2}, "POST routes the user drives; /tick is the browser's clock")
        self.assertEqual(u["views"], {"feed": 3})
        self.assertEqual(u["kernelUptime"], "lt1h")
        new = {"parses": {"perSession": {"sessions": 5, "max": 9}}, "uptime_s": 2 * 86400,
               "http": {"POST /tunnels/start": {"count": 1, "ms": 1.0}, "GET /usage/fleet": {"count": 2, "ms": 1.0}, "GET /nope": {"count": 1}}}
        u = pe.usage_block(new)
        self.assertEqual(u["sessions"], {"parsed": 5})
        self.assertEqual(u["actions"], {"tunnels.start": 1})
        self.assertEqual(u["views"], {"usage.fleet": 2})
        self.assertEqual(u["kernelUptime"], "1d-7d")
        self.assertEqual(pe.usage_block({}), {"sessions": {}, "actions": {}, "views": {}})
        self.assertEqual(pp.paste_problems(pp.fold(pe.usage_block(leak_snapshot()))), [])

    def test_a_non_finite_uptime_fits_no_bucket_and_raises_nothing(self):
        # json.load accepts the NaN and Infinity literals, so a --from file can carry either; the bucket search used
        # to run off the end of UPTIME_BUCKETS on NaN (every comparison false) and raise StopIteration, and the verb
        # printed a traceback carrying the checkout's path instead of writing (the review, 2026-09-18)
        for up in (float("nan"), float("inf"), float("-inf")):
            u = pe.usage_block({"uptime_s": up, "http": {"POST /send": {"count": 1}}})
            self.assertNotIn("kernelUptime", u, repr(up))
            self.assertEqual(u["actions"], {"send": 1}, "the rest of the block is unaffected")
        self.assertEqual(pe.usage_block({"uptime_s": 0})["kernelUptime"], "lt1h")
        self.assertEqual(pe.usage_block({"uptime_s": 8 * 86400.0})["kernelUptime"], "gt7d")
        self.assertNotIn("kernelUptime", pe.usage_block({"uptime_s": "100"}), "a string is not an uptime")


class Cli(unittest.TestCase):
    """bin/romp-perf-export as a child over a saved snapshot: the refusal, the file, the envelope, the flags."""

    def setUp(self):
        self.xdg, self.state = _state_root()
        self.addCleanup(shutil.rmtree, self.xdg, True)
        self.src = os.path.join(self.xdg, "snap.json")
        with open(self.src, "w") as fh:
            json.dump(leak_snapshot(), fh)

    def test_without_public_the_verb_refuses_with_one_line_and_writes_nothing(self):
        r = _run(["--from", self.src], state=self.state)
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertEqual(r.stdout, "")
        self.assertEqual(len(r.stderr.strip().splitlines()), 1, r.stderr)
        self.assertIn("--public", r.stderr)
        self.assertIn("no raw mode", r.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.state, "perf-exports")))
        r = _run([], state=self.state)
        self.assertEqual(r.returncode, 2, "no source either: still the refusal, before any read")
        self.assertNotIn("not reachable", r.stderr)

    def test_public_from_a_snapshot_writes_the_default_file_and_prints_its_path_and_size(self):
        r = _run(["--public", "--from", self.src], state=self.state)
        self.assertEqual(r.returncode, 0, r.stderr)
        m = re.match(r"^(\S+) \((\d+) bytes\)\n$", r.stdout)
        self.assertIsNotNone(m, r.stdout)
        path, size = m.group(1), int(m.group(2))
        self.assertEqual(os.path.dirname(path), os.path.join(self.state, "perf-exports"))
        self.assertRegex(os.path.basename(path), FILE_NAME)
        self.assertEqual(os.path.getsize(path), size)
        self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600)
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
        self.assertEqual(doc["schema"], "romp-perf-export/1")
        self.assertRegex(doc["exported_at"], STAMP)
        self.assertEqual(doc["kernel_commit"], SHA[:12])
        self.assertNotIn("usage", doc)
        self.assertEqual(pp.paste_problems(doc, planted=PLANTED, skip=("schema",), under=("perf",)), [])
        self.assertEqual(r.stderr, "")

    def test_out_and_usage(self):
        out = os.path.join(self.xdg, "sub", "public.json")
        r = _run(["--public", "--from", self.src, "--usage", "--out", out], state=self.state)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, "%s (%d bytes)\n" % (out, os.path.getsize(out)))
        self.assertEqual(stat.S_IMODE(os.stat(out).st_mode), 0o600)
        with open(out, encoding="utf-8") as fh:
            doc = json.load(fh)
        self.assertEqual(doc["usage"]["actions"], {"send": 7, "new": 2})
        self.assertEqual(doc["usage"]["sessions"]["parsed"], 2)
        self.assertFalse(os.path.exists(os.path.join(self.state, "perf-exports")), "--out means no default file")

    def test_a_snapshot_with_a_nan_uptime_exports_under_usage_with_no_traceback(self):
        snap = leak_snapshot()
        snap["uptime_s"] = float("nan")
        with open(self.src, "w") as fh:
            json.dump(snap, fh)                       # json writes the NaN literal, which json.load reads back
        out = os.path.join(self.xdg, "nan.json")
        r = _run(["--public", "--from", self.src, "--usage", "--out", out], state=self.state)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stderr, "", "no traceback, no warning")
        self.assertNotIn("Traceback", r.stdout + r.stderr)
        with open(out, encoding="utf-8") as fh:
            doc = json.load(fh)
        self.assertNotIn("kernelUptime", doc["usage"])
        self.assertEqual(doc["usage"]["actions"], {"send": 7, "new": 2})
        self.assertIsNone(doc["perf"]["uptime_s"], "the fold nulls the non-finite number")

    def test_a_missing_or_unreadable_snapshot_is_said(self):
        r = _run(["--public", "--from", os.path.join(self.xdg, "none.json")], state=self.state)
        self.assertEqual(r.returncode, 1)
        self.assertIn("does not exist", r.stderr)
        bad = os.path.join(self.xdg, "bad.json")
        with open(bad, "w") as fh:
            fh.write("not json")
        r = _run(["--public", "--from", bad], state=self.state)
        self.assertEqual(r.returncode, 1)
        self.assertIn("is not JSON", r.stderr)
        with open(bad, "w") as fh:
            fh.write("[1, 2]")
        r = _run(["--public", "--from", bad], state=self.state)
        self.assertEqual(r.returncode, 1)
        self.assertIn("not a JSON object", r.stderr)
        # an object that is not GET /perf (a registry row, a sessions listing): its keys would pass the grammar and the
        # denylist knows none of them, so the shape is checked at the read and the file is refused before any fold
        out = os.path.join(self.xdg, "not-a-snapshot.json")
        with open(bad, "w") as fh:
            json.dump({"name": "web", "tags": ["acme-corp", "q3-launch"], "branch": "feature-acme-sso", "project": "acme-billing",
                       "remotes": {"peer-box-7": {"ok": True}}}, fh)
        r = _run(["--public", "--from", bad, "--out", out], state=self.state)
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn("not a GET /perf snapshot", r.stderr)
        self.assertNotIn("acme", r.stderr, "the file's contents are not echoed")
        self.assertFalse(os.path.exists(out))
        with open(bad, "w") as fh:
            json.dump({"uptime_s": 1.0, "process": {}, "pusher": {}}, fh)
        r = _run(["--public", "--from", bad, "--out", out], state=self.state)
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn("http", r.stderr, "the missing block is named")

    def test_a_dead_kernel_is_said_and_nothing_written(self):
        r = _run(["--public"], state=self.state, env_extra={"ROMP_KERNEL_PORT": "1"})
        self.assertEqual(r.returncode, 1)
        self.assertIn("kernel not reachable on :1", r.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.state, "perf-exports")))

    def test_a_kernel_port_that_is_not_a_number_is_refused_not_replaced(self):
        # bin/romp's perf verb uses ROMP_KERNEL_PORT as given and fails on a bad one; the export must not read a
        # kernel on 29855 instead and export whatever answers there
        r = _run(["--public"], state=self.state, env_extra={"ROMP_KERNEL_PORT": " 3000"})
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn("ROMP_KERNEL_PORT", r.stderr)
        self.assertNotIn("not reachable", r.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.state, "perf-exports")))
        r = _run(["--public"], state=self.state, env_extra={"ROMP_KERNEL_PORT": "70000"})
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn("ROMP_KERNEL_PORT", r.stderr)
        r = _run(["--public", "--from", self.src], state=self.state, env_extra={"ROMP_KERNEL_PORT": " 3000"})
        self.assertEqual(r.returncode, 0, "--from reads no kernel, so the port is not consulted: %s" % r.stderr)

    def test_out_over_an_existing_file_replaces_it_and_leaves_it_readable_by_the_owner_alone(self):
        out = os.path.join(self.xdg, "public.json")
        with open(out, "w") as fh:
            fh.write("stale text a reader must not find\n")
        os.chmod(out, 0o644)
        r = _run(["--public", "--from", self.src, "--out", out], state=self.state)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(stat.S_IMODE(os.stat(out).st_mode), 0o600, "a pre-existing world-readable file is fixed, not kept")
        with open(out, encoding="utf-8") as fh:
            text = fh.read()
        self.assertNotIn("stale", text)
        self.assertEqual(json.loads(text)["schema"], "romp-perf-export/1")
        self.assertEqual(r.stdout, "%s (%d bytes)\n" % (out, len(text.encode("utf-8"))))
        # the same minute's default name is one file: the second export replaces the first
        state = pe.Path(self.state)
        now = pe.datetime(2026, 9, 18, 8, 53, 7, tzinfo=pe.timezone.utc)
        path = pe.default_path(state, now)
        self.assertEqual(path, state / "perf-exports" / "perf-export-20260918T0853.json")
        self.assertEqual(pe.write_file(path, "one\n"), 4)
        os.chmod(path, 0o644)
        self.assertEqual(pe.write_file(path, "second\n"), 7)
        self.assertEqual((open(path).read(), stat.S_IMODE(os.stat(path).st_mode)), ("second\n", 0o600))

    def test_a_short_write_is_completed_and_a_write_that_makes_no_progress_is_an_error(self):
        # os.write may write fewer bytes than asked (a full disk, a size limit, an interruption); the writer used to
        # take one call's word for it and report the whole size over a truncated file (the review, 2026-09-18)
        path = os.path.join(self.xdg, "short.json")
        real = os.write
        calls = []

        def three_at_a_time(fd, data):
            calls.append(len(data))
            return real(fd, bytes(data[:3]))
        with mock.patch.object(pe.os, "write", side_effect=three_at_a_time):
            n = pe.write_file(pe.Path(path), "twelve bytes")
        self.assertEqual(n, 12)
        self.assertEqual(open(path).read(), "twelve bytes")
        self.assertEqual(calls, [12, 9, 6, 3], "each call is offered what is left")
        with mock.patch.object(pe.os, "write", return_value=0):
            with self.assertRaises(OSError) as cm:
                pe.write_file(pe.Path(path), "never lands")
        self.assertIn("short write", str(cm.exception))
        self.assertFalse(os.path.exists(path), "a write that fails leaves no file behind: the open truncated it, the failure removes it")
        # a write that fails midway (a full disk, a size limit): the bytes that landed are not left as a truncated
        # 0600 file at the target either (round 2). Not a temp file moved over the target: a replace would swap
        # out a symlink at --out, which the open below refuses to follow
        seen = []

        def three_then_fail(fd, data):
            if seen:
                raise OSError(28, "No space left on device")
            seen.append(len(data))
            return real(fd, bytes(data[:3]))
        with mock.patch.object(pe.os, "write", side_effect=three_then_fail):
            with self.assertRaises(OSError):
                pe.write_file(pe.Path(path), "twelve bytes")
        self.assertEqual(seen, [12])
        self.assertFalse(os.path.exists(path), "the three bytes that landed are gone with the file")
        # the verb: the same failure is one cannot-write line, exit 1, no size reported, no file; the verb's check runs
        # in this process, so its probes are the synthetic ones (never this machine's hostname, login or home)
        with mock.patch.object(pe.os, "write", return_value=0), mock.patch.object(pe.pp, "machine_probes", return_value=SYNTHETIC_PROBES), \
                mock.patch("sys.stdout", new_callable=lambda: __import__("io").StringIO()) as out, \
                mock.patch("sys.stderr", new_callable=lambda: __import__("io").StringIO()) as err:
            rc = pe.main(["--public", "--from", self.src, "--out", path])
        self.assertEqual(rc, 1)
        self.assertEqual(out.getvalue(), "")
        self.assertIn("cannot write %s (OSError)" % path, err.getvalue())
        self.assertFalse(os.path.exists(path))
        # a symlink where the file would go is not followed
        link = os.path.join(self.xdg, "link.json")
        os.symlink(os.path.join(self.xdg, "target.json"), link)
        r = _run(["--public", "--from", self.src, "--out", link], state=self.state)
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn("cannot write", r.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.xdg, "target.json")))

    def test_a_string_the_machine_knows_refuses_the_write_naming_the_key_path_never_the_value(self):
        # the sdk registry holds the session ids the scan learns; an eight-character sid prefix is an identifier
        # to the grammar, so only the scan can catch it as an app name a client declared
        os.makedirs(os.path.join(self.state, "sdk"))
        with open(os.path.join(self.state, "sdk", SID2 + ".json"), "w") as fh:
            json.dump({"sid": SID2, "name": "web", "lastSid": SID, "cwd": HOME + "/code/notes-api"}, fh)
        snap = leak_snapshot()
        snap["pusher"]["connectPush"]["byApp"][SID[:8]] = {"count": 1}
        with open(self.src, "w") as fh:
            json.dump(snap, fh)
        r = _run(["--public", "--from", self.src], state=self.state)
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn("refused", r.stderr)
        self.assertIn("session id", r.stderr)
        self.assertIn("a key under perf/pusher/connectPush/byApp;", r.stderr, r.stderr)
        self.assertNotIn(SID[:8], r.stderr, "the value is never printed")
        self.assertFalse(os.path.exists(os.path.join(self.state, "perf-exports")))
        # the machine's own strings: the child's USER is a probe, and an app named after it is refused too
        snap = leak_snapshot()
        snap["pusher"]["connectPush"]["byApp"]["tester-app"] = {"count": 1}
        with open(self.src, "w") as fh:
            json.dump(snap, fh)
        r = _run(["--public", "--from", self.src], state=self.state)
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn("username", r.stderr)
        self.assertNotIn("tester-app", r.stderr)
        # the child's hostname is the pinned one (CHILD), not this machine's: a key spelled like it is refused as
        # a hostname, and the snapshot's own TESTHOST strings (an http key, an identity value) are gone by then
        snap = leak_snapshot()
        snap["pusher"]["connectPush"]["byApp"]["TESTHOST"] = {"count": 1}
        with open(self.src, "w") as fh:
            json.dump(snap, fh)
        r = _run(["--public", "--from", self.src], state=self.state)
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn("(hostname) survives as a key under perf/pusher/connectPush/byApp", r.stderr)
        self.assertNotIn("TESTHOST", r.stderr)

    def test_a_key_the_walk_refuses_is_never_printed_when_a_machine_string_sits_beneath_it(self):
        # the round-2 medium, through the verb: a 32-hex token fits the fold's grammar (it survives --from) and fails
        # the walk; with a hostname-shaped value or a hostname key beneath it, the refusal named the token as a path
        # component. The shallowest finding is the walk's key finding one level up, so the refusal names perf/heap and
        # neither the token nor the hostname reaches stdout or stderr
        token = "c" * 32
        for planted, what in (("TESTHOST", "a hostname-shaped value"), ({"TESTHOST": 1}, "a dict with a hostname key")):
            snap = leak_snapshot()
            snap["heap"][token] = planted
            with open(self.src, "w") as fh:
                json.dump(snap, fh)
            r = _run(["--public", "--from", self.src], state=self.state)
            self.assertEqual(r.returncode, 1, what + "\n" + r.stderr)
            self.assertEqual(r.stdout, "", what)
            self.assertEqual(r.stderr, "romp perf export: refused: the public form still fails the walk (a 32-hex token, a key under perf/heap); nothing written\n", what)
            self.assertNotIn(token, r.stdout + r.stderr, what)
            self.assertNotIn("TESTHOST", r.stdout + r.stderr, what)
            self.assertFalse(os.path.exists(os.path.join(self.state, "perf-exports")), what)

    def test_the_probe_list_is_the_machines_strings_and_the_registrys_ids(self):
        os.makedirs(os.path.join(self.state, "sdk"))
        with open(os.path.join(self.state, "sdk", SID + ".json"), "w") as fh:
            json.dump({"sid": SID, "name": "chat", "lastSid": SID2, "cwd": HOME + "/code/notes-api"}, fh)
        with mock.patch.object(pp.socket, "gethostname", return_value="TESTHOST.example"):
            probes = pp.machine_probes(self.state, env={"HOME": HOME, "USER": "tester"})
        kinds = {}
        for kind, s in probes:
            kinds.setdefault(kind, set()).add(s)
        self.assertEqual(kinds["hostname"], {"testhost.example", "testhost"})
        self.assertEqual(kinds["username"], {"tester"})
        self.assertEqual(kinds["home directory"], {HOME})
        self.assertEqual(kinds["session id"], {SID, SID[:8], SID2, SID2[:8]})
        self.assertEqual(kinds["session directory"], {HOME + "/code/notes-api"})
        self.assertNotIn("chat", {s for _, s in probes}, "a session NAME is not a probe: it collides with romp's own identifiers")
        self.assertEqual(_hits({"a": {"TestHost": 1}, "schema": "testhost/1"}, probes, skip=("schema",)),
                         [("hostname", "a key under a")])
        self.assertEqual(_hits({"a": {"b": "x " + SID2[:8]}}, probes), [("session id", "the value at a/b")])
        self.assertEqual(_hits({"TESTHOST": 1}, probes), [("hostname", "a key under the root")])

    def test_a_number_is_scanned_by_its_wire_spelling_so_a_listed_digit_run_in_a_numeric_leaf_is_a_hit(self):
        """The identifier scan reads every NUMBER by its wire spelling, json.dumps(node), the spelling perf_export.document_text
        writes and `romp perf upload` sends (the upload's fourth review round, 2026-09-19, its lens over the final artifact:
        the private list may hold a digit run, and a listed run written as a number travelled unread while the same run in
        quotes was refused). A hit is a value finding at the number's path, whatever the file spelled: a plain integer, a
        float, a negative, a run embedded in a longer one, a fraction, an exponent form whose canonical spelling carries the
        run (4.242424242e9 is 4242424242.0), a listed float-shaped entry and its exponent respelling (1234.5678, eight digits, at
        the floor by digit count; the base's assertion, deleted by a086ced5a when the floor was computed as the longest run and
        restored by the closing delta), a list element. A
        number whose canonical spelling does not carry the run is no hit (4242424242e-3 is 4242424.242, and a float that
        merely rounds near it), nor are a bool or null under a probe that spells them, nor any number under the machine's
        word and path probes (a hostname, a login, a home directory, a session id, a working directory spell letters,
        slashes or dashes a number never carries). Fails before: every numeric leaf was skipped."""
        listed = [(pp.PRIVATE_KIND, "4242424242"), (pp.PRIVATE_KIND, "1234.5678")]      # the pointed entry: eight digits, at the floor by digit count
        for value, where in ((4242424242, "a/n"), (4242424242.0, "a/n"), (4242424242.5, "a/n"), (-4242424242, "a/n"), (14242424242, "a/n"),
                             (0.4242424242, "a/n"), (4.242424242e9, "a/n"), (1234.5678, "a/n"), (12345678e-4, "a/n"), ([1, 4242424242], "a/n/1")):
            self.assertEqual(_hits({"a": {"n": value}}, listed), [(pp.PRIVATE_KIND, "the value at %s" % where)], repr(value))
            self.assertIn(json.dumps(value if not isinstance(value, list) else value[1]).strip("-"), pe.document_text({"a": {"n": value}}),
                          "the spelling scanned is the spelling the writer puts in the file")
        for value in (4242424242e-3, 4242424241.9999, 42424242, True, False, None, "x"):
            self.assertEqual(_hits({"a": {"n": value}}, listed), [], repr(value))
        self.assertEqual(_hits({"a": {"n": True, "m": None}}, [(pp.PRIVATE_KIND, "true"), (pp.PRIVATE_KIND, "null")]), [],
                         "a bool and null are not scanned")
        with mock.patch.object(pp.socket, "gethostname", return_value="TESTHOST.example"):
            machine = pp.machine_probes(self.state, env={"HOME": HOME, "USER": "tester"})
        self.assertEqual(_hits({"a": {"n": 4242424242, "f": 1234.5678, "l": [1e100, -0.0, 1.5e12]}}, machine), [],
                         "the machine's words and paths are never spelled by a number")
        self.assertEqual(_hits({"a": {"n": 4242424242}}, [("session id", "11111111")]), [], "an all-digit id prefix elsewhere is no hit")
        self.assertEqual(_hits({"a": {"n": 911111111}}, [("session id", "11111111")]), [("session id", "the value at a/n")],
                         "an all-digit id prefix a counter carries is a hit, the rare cost the docstring names")

    def test_an_exponent_spelled_number_is_scanned_by_its_plain_decimal_spelling_too(self):
        """A float whose canonical spelling carries an exponent (at or above 1e16 or under 1e-4 in magnitude) is scanned by every
        spelling a reader recovers the value from (pp.number_spellings): the wire spelling and its plain decimal expansion
        (format(Decimal(text), 'f') of the TEXT: 1.234567e+16 is 12345670000000000, 1.5e-05 is 0.000015, 1e+23 is
        100000000000000000000000), and by NO third spelling: the exact integer of the double (int(1e+23) is
        99999999999999991611392) is binary noise nobody wrote, which a listed 9999999 would match; the closing delta's first cut
        scanned it and the verifier dropped it (E pins that a listed 99999999999999991611392 hits nothing, and a listed 9999999
        neither). A listed entry is expanded the same way and THE FLOOR IS DECIDED PER SPELLING (pp.numeric_probe over each of
        number_spellings' results), so a listed 1.234567e+16 is applied as 12345670000000000 and as itself, a listed 12345678e-4 as
        1234.5678 and as itself, and a listed 1.5e-05 (four digits as written, seven as 0.000015) is applied as its expansion
        alone: G hits the leaves 1.5e-05 and 0.000015, and machine_probes does not count it under the floor (the stderr test);
        the first cut decided the floor on the entry's text once, so a listed 1e+16 protected nothing while the line told the
        operator it carried too few digits (the closing delta's verifier). An expansion with fewer digits than the entry is not
        armed: a listed 1.0000000e+2 (nine digits) is armed as itself and as 100.00000, never as 100, so the leaves 100.5 and
        1000 travel (H). The closing check of 2026-09-19: a listed 12345670000000000 was refused when the leaf spelled the
        integer and travelled when the same value's canonical spelling was 1.234567e+16, repr's point after the first digit
        breaking the substring, while the module claimed a listed run was found however the file spelled it (the hole as old as
        the numeric scan, 431db9a60). A number yields at most ONE Hit, the first spelling that carries a probe, and the Hit
        never carries a spelling; the wire spelling is still what the writer puts in the file. Decimal of the text, not of the
        value: Decimal(value) is the double's exact binary expansion (Decimal(1e+23) is 99999999999999991611392, never the
        100000000000000000000000 a reader recovers from the text). An entry that underflows to zero (1000000e-400, seven
        digits, leading exponent -394) is outside pp.EXPANSION_EXPONENT_MAX and keeps its ONE spelling since the closing re-run
        of 2026-09-19 (the bound test beside this one), so it expands to no long plain fraction and to no bare 0, and refuses no
        number carrying a zero (the first cut's int() road spelled str(int(0.0))). Dropping the Decimal spelling reds A on
        1.234567e+16 (its first case), B on
        1.234567e-05, C on 1.5e-05 and F on 1e+23; the int() spelling back reds E and the 1e+23 pin; scanning a probe by its
        text alone reds D on the integer leaf and G on both leaves; Decimal of the value reds F on 1e+23 (and the
        number_spellings pins); a Hit per spelling reds the single-Hit assertion on D over 1.234567e+16 (both spellings carry a
        probe); a spelling in the Hit reds the digit-free reprs; the floor decided on the entry's text reds G's hits."""
        A = pp.Probe(pp.PRIVATE_KIND, "12345670000000000", 2)
        B = pp.Probe(pp.PRIVATE_KIND, "1234567", 3)
        C = pp.Probe(pp.PRIVATE_KIND, "0.000015", 4)
        D = pp.Probe(pp.PRIVATE_KIND, "1.234567e+16", 5)
        E = pp.Probe(pp.PRIVATE_KIND, "99999999999999991611392", 6)
        F = pp.Probe(pp.PRIVATE_KIND, "100000000000000000000000", 7)
        G = pp.Probe(pp.PRIVATE_KIND, "1.5e-05", 8)
        H = pp.Probe(pp.PRIVATE_KIND, "1.0000000e+2", 9)
        digits = re.compile(r"\d{4,}")
        for probe, value, where in ((A, 1.234567e+16, "a/n"), (A, -1.234567e+16, "a/n"), (A, [1, 1.234567e+16], "a/n/1"),
                                    (A, 12345670000000000, "a/n"), (B, 1.234567e-05, "a/n"), (B, 0.001234567, "a/n"), (B, 1.234567e+16, "a/n"),
                                    (C, 1.5e-05, "a/n"), (C, 0.000015, "a/n"), (D, 12345670000000000, "a/n"), (D, 1.234567e+16, "a/n"),
                                    (F, 1e+23, "a/n"), (G, 1.5e-05, "a/n"), (G, 0.000015, "a/n")):
            hits = pp.identifier_hits({"a": {"n": value}}, [probe])
            self.assertEqual(len(hits), 1, "one Hit per number, whatever its spellings: %r under line %d" % (value, probe.line))
            self.assertEqual(hits, [pp.Hit(pp.PRIVATE_KIND, False, where, len(where.split("/")), probe.line)], "%r under line %d" % (value, probe.line))
            self.assertIsNone(digits.search(repr(hits)), "the Hit carries no spelling: %r" % (hits,))
        for probe, value in ((A, 1.234568e+16), (A, 1e+16), (B, 1.234568e-05), (C, 1.5e-06), (E, 1e+23), (pp.Probe(pp.PRIVATE_KIND, "9999999", 6), 1e+23),
                             (G, 1.5e-06), (H, 100.5), (H, 1000), (H, 100), (pp.Probe(pp.PRIVATE_KIND, "1000000e-400", 10), 409600)):
            self.assertEqual(pp.identifier_hits({"a": {"n": value}}, [probe]), [], "no hit: %r under line %d" % (value, probe.line))
        self.assertEqual(_hits({"a": {"n": "x1.5e-05"}}, [G]), [(pp.PRIVATE_KIND, "the value at a/n")], "a four-digit entry is still checked in a string")
        for value in (1.234567e+16, -1.234567e+16, 1.234567e-05, 1.5e-05, 1e+23):
            self.assertIn("e", json.dumps(value), repr(value))
            self.assertIn(json.dumps(value), pe.document_text({"a": {"n": value}}), "the wire spelling is what the writer puts in the file")
        self.assertEqual(pp.number_spellings("1.234567e+16", 1.234567e+16), ("1.234567e+16", "12345670000000000"))
        self.assertEqual(pp.number_spellings("1.5e-05", 1.5e-05), ("1.5e-05", "0.000015"))
        self.assertEqual(pp.number_spellings("1.234567e-05", 1.234567e-05), ("1.234567e-05", "0.00001234567"))
        self.assertEqual(pp.number_spellings("-1.5e-05", -1.5e-05), ("-1.5e-05", "-0.000015"))
        self.assertEqual(pp.number_spellings("1e+23", 1e+23), ("1e+23", "100000000000000000000000"), "two spellings at most: never the double's exact integer")
        self.assertEqual(pp.number_spellings("1e+16", 1e+16), ("1e+16", "10000000000000000"))
        self.assertEqual(pp.number_spellings("1.000000e+5", 100000.0), ("1.000000e+5", "100000.0"))
        self.assertEqual(pp.number_spellings("1.0000000e+2", pp._number_value("1.0000000e+2")), ("1.0000000e+2", "100.00000"))
        self.assertEqual([pp.numeric_probe(s) for s in pp.number_spellings("1.5e-05", pp._number_value("1.5e-05"))], [False, True],
                         "a listed 1.5e-05 is armed as its expansion alone")
        self.assertEqual([pp.numeric_probe(s) for s in pp.number_spellings("1e+16", pp._number_value("1e+16"))], [False, True])
        self.assertEqual(pp._number_value("1000000e-400"), 0.0, "the entry underflows to a finite zero, so the finite check alone would expand it")
        self.assertEqual(pp.number_spellings("1000000e-400", pp._number_value("1000000e-400")), ("1000000e-400",),
                         "an entry that underflows to 0.0 has its leading exponent at -394, outside the bound, so it keeps its one spelling: no long "
                         "plain fraction (the head before the closing re-run expanded it) and never a bare 0")
        for value in (5000.0, 0.037, 2.5, 180.0, 1.37e11, 409600, 100.5, 0.0, 1234.5678, 12345678e-4, -4242424):
            self.assertEqual(pp.number_spellings(json.dumps(value), value), (json.dumps(value),), "no exponent, one spelling: %r" % (value,))
        for text in (".5678", "1234567.", "1e400", "12345670000000000", "1234567", "+4242424", "(12345678)", "1234 5678"):
            self.assertEqual(pp.number_spellings(text, pp._number_value(text)), (text,),
                             "a fragment, an overflow, a plus, an integer or a text json cannot read keeps its one spelling: %r" % (text,))
        self.assertEqual(pp.number_spellings("12345678e-4", pp._number_value("12345678e-4")), ("12345678e-4", "1234.5678"),
                         "a listed exponent form is applied as its plain spelling too")

    def test_the_plain_expansion_is_bounded_by_the_exponent_and_an_entry_beyond_any_double_keeps_its_one_spelling_said_once(self):
        """THE EXPANSION BOUND (the closing re-run of 2026-09-19, finding 5; the comment at pp.EXPANSION_EXPONENT_MAX).
        format(Decimal(text), 'f') writes about as many digits as the exponent, so the expansion's work is exponential in an
        ENTRY'S LENGTH while PRIVATE_STRINGS_MAX bounds only the file: a listed 1e-1000000000, thirteen characters, asked for a
        billion digits and took `romp perf export --public` and `romp perf upload` down with an uncaught MemoryError.
        number_spellings expands only when the leading digit's exponent, Decimal(text).adjusted(), has magnitude at most 324
        (pp.expansion_bounded), the bound derived from the double: 5e-324 is the smallest positive double (adjusted -324) and
        repr(sys.float_info.max) the largest (308), so every finite leaf's wire spelling is inside it, and an entry outside it
        is the spelling of no leaf and expands longer than any leaf's spelling, so skipping it loses no protection. Pinned at
        the edge with literals: 1e-324 (adjusted -324, inside; json reads it as 0.0) has two spellings and the second is 326
        characters, 0. then zeros then 1; 5e-324 and the largest double have two; 1e-325 (adjusted -325) has one; 1000000e-400
        (adjusted -394) has one. The bound is symmetric, 324 in magnitude, so on the positive side it admits exponents 309 to
        324 that no double reaches (1e+309 and 1e+324 expand, to at most 325 digits, harmless; 1e+325 does not). THE GUARD'S
        OWN LIMIT (the re-run's verification): the decimal module refuses to construct an exponent past decimal.MAX_EMAX,
        about 1e18, with InvalidOperation, while json reads the same text as 0.0, so 1e-10000000000000000000 (exponent 10**19,
        23 characters) and 1e- followed by sixty thousand nines (which the reader's 64 KiB admits) reached the guard and killed
        all three verbs with that traceback where the first cut asked Decimal(text).adjusted() bare; expansion_bounded reads
        the refusal as False and each keeps its one spelling with no exception. machine_probes says once which listed entries
        kept their one spelling for this reason (pp.LIST_EXPANSION_SKIPPED, by list line, never the text, never the path),
        BEFORE the under-floor line, since the skip explains why the entry has one spelling, which the floor line then judges:
        a list of the two MAX_EMAX entries gets the skip line, 2 of 2, list lines 1 and 2, and nothing else (each carries
        twenty-one or more digits as written, so it is armed as itself, not under the floor, and the probe is the entry as
        written); a list of 1e-400 alone gets the skip line and then the under-floor line (1 of 1, list line 1: its one
        spelling has four digits). The skip counts only an entry WRITTEN with an exponent: a plain decimal of 403 characters,
        0. then four hundred zeros then 1 (adjusted -401, no e), is armed by its 402 digits, is never expanded (no exponent in
        the text) and gets no line, so a long plain decimal is never reported as written with an exponent. An overflow (1e400,
        infinity) keeps the older silent road: _number_value is None, nothing expands, no skip line, and the floor line alone
        counts its four digits. THE BILLION-DIGIT ENTRY IS NOT FORMATTED IN THIS PROCESS: 1e-1000000000 stays in the
        expansion_bounded truth table (that call never formats) and in the three children under their address-space caps
        (the export and restart modules, and the upload module), where a removed guard fails fast with a MemoryError under the
        cap; an in-process number_spellings call on it would, with the guard removed, format a billion digits inside the
        pytest worker and then die building the diff (the re-run's verification saw the worker OOM-killed at 8 GB), a red by
        the process dying rather than by assertion. Dropping `and expansion_bounded(text)` from number_spellings' guard reds
        the one-spelling pin on 1e-325 (a 327-character second spelling), the MAX_EMAX pins (InvalidOperation out of format's
        Decimal) and the three children; the try/except removed from expansion_bounded reds the MAX_EMAX truth-table pins and
        the two-entry skip line with InvalidOperation in the message; a bound of 323 reds the two-spelling pins on 1e-324 and
        5e-324 (a real leaf excluded); a bound of 325 reds the one-spelling pin on 1e-325; dropping the skip line reds the
        stderr equalities; writing it after the under-floor line reds the 1e-400 order; dropping the `e` in the text from the
        skip's filter reds the long plain decimal's silence."""
        self.assertEqual(pp.number_spellings("1e-325", 0.0), ("1e-325",), "adjusted -325: outside the bound, one spelling")
        two = pp.number_spellings("1e-324", 0.0)
        self.assertEqual(len(two), 2, "adjusted -324: inside the bound, two spellings (a bound of 323 excludes the smallest double's exponent)")
        self.assertEqual((two[0], len(two[1]), two[1][:2], two[1][-1], set(two[1][2:-1])), ("1e-324", 326, "0.", "1", {"0"}),
                         "the expansion is 326 characters, 0. then zeros then 1")
        self.assertEqual(len(pp.number_spellings("5e-324", 5e-324)), 2, "the smallest positive double is expanded")
        self.assertEqual(len(pp.number_spellings("5e-324", 5e-324)[1]), 326, "the longest leaf expansion there is")
        self.assertEqual(len(pp.number_spellings(repr(sys.float_info.max), sys.float_info.max)), 2, "and the largest double")
        self.assertEqual(pp.number_spellings("1000000e-400", 0.0), ("1000000e-400",), "adjusted -394: one spelling")
        past = "1e-10000000000000000000"                                    # exponent 10**19, past decimal.MAX_EMAX: the constructor refuses it
        long_past = "1e-" + "9" * 60000                                     # 60003 characters, inside the reader's 64 KiB bound
        for text in (past, long_past):
            with self.assertRaises(pp.InvalidOperation, msg=text[:30]):
                pp.Decimal(text)
            self.assertEqual(pp._number_value(text), 0.0, "json reads it as a finite zero, so the finite check alone would reach the guard")
            self.assertIs(pp.expansion_bounded(text), False, "a construction the decimal module refuses is beyond the bound by construction")
            self.assertEqual(pp.number_spellings(text, 0.0), (text,), "one spelling, and no exception")
        for text, adjusted, bounded in (("1e-1000000000", -1000000000, False), ("1e-325", -325, False), ("1e-324", -324, True), ("5e-324", -324, True),
                                        (repr(sys.float_info.max), 308, True), ("1000000e-400", -394, False), ("1e-400", -400, False),
                                        ("1.5e-05", -5, True), ("1e+16", 16, True), ("1e+308", 308, True), ("1e+309", 309, True),
                                        ("1e+324", 324, True), ("1e+325", 325, False)):
            self.assertEqual(pp.Decimal(text).adjusted(), adjusted, text)
            self.assertIs(pp.expansion_bounded(text), bounded, text)
        skip = pp.LIST_EXPANSION_SKIPPED % (1, 1, "list line 1", 324) + "\n"
        self.assertEqual(skip, "romp: 1 of 1 private-strings entries (list line 1) are written with an exponent beyond 324, further than any number "
                               "in an export reaches, so each is checked by its own text and not by its plain decimal expansion\n",
                         "the literal the upload road pins, rendered from the module's template")
        listed = os.path.join(self.state, "list.txt")
        env = {"HOME": HOME, "USER": "tester", "ROMP_PRIVATE_STRINGS": listed}
        with open(listed, "w", encoding="utf-8") as fh:
            fh.write(past + "\n" + long_past + "\n")
        err = io.StringIO()
        with mock.patch.object(pp.socket, "gethostname", return_value="TESTHOST.example"), contextlib.redirect_stderr(err):
            probes = pp.machine_probes(None, env=env)
        self.assertEqual(err.getvalue(), pp.LIST_EXPANSION_SKIPPED % (2, 2, "list lines 1 and 2", 324) + "\n",
                         "the skip line and nothing else: twenty-one and sixty thousand digits as written, so each entry is armed as itself")
        self.assertEqual([(p.text, p.line) for p in probes if p.kind == pp.PRIVATE_KIND], [(past, 1), (long_past, 2)], "the probes are the entries as written")
        for word in (past, "InvalidOperation", "Traceback", listed):
            self.assertNotIn(word, err.getvalue(), "the line names no entry's text, no exception and not the list's path: %s" % word[:30])
        with open(listed, "w", encoding="utf-8") as fh:
            fh.write("1e-400\n")
        err = io.StringIO()
        with mock.patch.object(pp.socket, "gethostname", return_value="TESTHOST.example"), contextlib.redirect_stderr(err):
            pp.machine_probes(None, env=env)
        self.assertEqual(err.getvalue(), skip + pp.LIST_UNDER_NUMERIC_FLOOR % (1, 1, "list line 1", 7, 7) + "\n",
                         "skipped, then under the floor by its one spelling of four digits: two lines in that order")
        plain = "0." + "0" * 400 + "1"                                      # adjusted -401 and no exponent written: armed by 402 digits, never expanded
        with open(listed, "w", encoding="utf-8") as fh:
            fh.write(plain + "\n")
        err = io.StringIO()
        with mock.patch.object(pp.socket, "gethostname", return_value="TESTHOST.example"), contextlib.redirect_stderr(err):
            probes = pp.machine_probes(None, env=env)
        self.assertEqual(err.getvalue(), "", "a long plain decimal carries no exponent: not skipped, not under the floor, nothing said")
        self.assertEqual([(p.text, p.line) for p in probes if p.kind == pp.PRIVATE_KIND], [(plain, 1)], "and the probe is the entry as written")
        self.assertEqual(pp.number_spellings(plain, pp._number_value(plain)), (plain,), "one spelling: no exponent in the text, nothing to expand")
        with open(listed, "w", encoding="utf-8") as fh:
            fh.write("1e400\n")
        err = io.StringIO()
        with mock.patch.object(pp.socket, "gethostname", return_value="TESTHOST.example"), contextlib.redirect_stderr(err):
            pp.machine_probes(None, env=env)
        self.assertEqual(err.getvalue(), pp.LIST_UNDER_NUMERIC_FLOOR % (1, 1, "list line 1", 7, 7) + "\n",
                         "an overflow was never expanded: no skip line, the floor line alone")
        self.assertEqual(pp.EXPANSION_EXPONENT_MAX, 324, "the constant the edge pins above derive from, last so that a moved bound reds on behaviour first")

    def test_a_key_and_a_string_value_are_scanned_by_every_spelling_of_a_listed_entry_so_an_exponent_written_entry_protects_its_digits_there_too(self):
        """The closing re-run of 2026-09-19 (finding 1, taken as the fix): identifier_hits built the expanded spellings of a
        listed entry into the list applied to NUMBERS alone and scanned a key or a string value by the entry's own text, so a
        listed 1.5e-05 refused the number 1.5e-05 and sent the string 0.000015 and the key zz0.000015 (the report's executed
        table: rc 0, the digits POSTed), while docs/reference.md already promised the operator that a listed 1.5e-05 reaches the
        floor as 0.000015 with nothing scoping that to numbers. Now every spelling of a listed entry (pp.number_spellings: its
        text and its plain expansion) is applied to keys and string values, with no floor, as the entry's text always was: G, a
        listed 1.5e-05 on line 8, hits the string value 0.000015 at zzn and the key zz0.000015 under the root, each one Hit
        carrying line 8; H, a listed 1e+16 on line 2, hits the seventeen-digit string and key naming line 2; an expansion with
        fewer digits than the entry is applied too (a listed 1.0000000e+2 as 100.00000 against the string 100.00000: the key
        and string scan has no floor, so the expansion is applied on the same terms as the entry itself), and so is an
        expansion UNDER the floor, which never enters the numeric list (a listed 1e5 as 100000 against the string 100000 and
        the key zz100000, and not against the number 100000: the discriminating pin, since 100.00000 carries eight digits
        and is a numeric probe in its own right). Controls: the string
        x0.00015 is no hit for G (a different fraction), a listed 0.000015 still hits the string 0.000015 (the base's behaviour,
        unchanged), the number pins stay (G hits the leaf 1.5e-05 and the leaf 0.000015), and a word probe over a key is as
        before, a whole-token match. THE REVERSE DIRECTION IS NOT PROMISED AND IS PINNED AS THE BOUNDARY: the entry is
        expanded and never the document's string, so a listed plain 0.000015 refuses the number 1.5e-05 (the leaf is
        expanded) and not a string value spelled 1.5e-05 nor a key zz1.5e-05 (the re-run's verification executed the sending
        cases on all three roads; identifier_hits' docstring and docs/reference.md state the boundary where the promise is
        made). The cost on this machine's own list is nil, 0 of 11 entries gain a spelling (derived by
        running number_spellings over the list, counting only). Scanning a key or a string by `probes` instead of the spelled
        list reds the four spelled pins and both export-road pins while the number pins stay green (the hole exactly as
        filed); appending only the numeric spellings to the spelled list reds the 1e5 pins (and the four-digit entry's own
        text in the exponent test); dropping the line from the spelled Probe reds the line assertions."""
        G = pp.Probe(pp.PRIVATE_KIND, "1.5e-05", 8)
        H = pp.Probe(pp.PRIVATE_KIND, "1e+16", 2)
        self.assertEqual(pp.identifier_hits({"zzn": "0.000015"}, [G]), [pp.Hit(pp.PRIVATE_KIND, False, "zzn", 1, 8)], "the string value, by the expansion")
        self.assertEqual(pp.identifier_hits({"zz0.000015": 1}, [G]), [pp.Hit(pp.PRIVATE_KIND, True, "", 0, 8)], "the key, by the expansion")
        self.assertEqual(pp.identifier_hits({"zzn": "10000000000000000"}, [H]), [pp.Hit(pp.PRIVATE_KIND, False, "zzn", 1, 2)])
        self.assertEqual(pp.identifier_hits({"zz10000000000000000": 1}, [H]), [pp.Hit(pp.PRIVATE_KIND, True, "", 0, 2)])
        self.assertEqual(pp.identifier_hits({"zzn": "100.00000"}, [pp.Probe(pp.PRIVATE_KIND, "1.0000000e+2", 3)]), [pp.Hit(pp.PRIVATE_KIND, False, "zzn", 1, 3)],
                         "an expansion with fewer digits than the entry is applied to a string too: the key and string scan has no floor")
        short = pp.Probe(pp.PRIVATE_KIND, "1e5", 4)                        # its expansion 100000 has six digits: never a numeric probe, still a spelling
        self.assertEqual([pp.numeric_probe(s) for s in pp.number_spellings("1e5", pp._number_value("1e5"))], [False, False], "under the floor in both spellings")
        self.assertEqual(pp.identifier_hits({"zzn": "100000"}, [short]), [pp.Hit(pp.PRIVATE_KIND, False, "zzn", 1, 4)],
                         "an under-floor expansion is applied to a string: the same protection a listed 100000 has there")
        self.assertEqual(pp.identifier_hits({"zz100000": 1}, [short]), [pp.Hit(pp.PRIVATE_KIND, True, "", 0, 4)], "and to a key")
        self.assertEqual(pp.identifier_hits({"zzn": 100000}, [short]), [], "and not to the number: the floor is the numeric arm's alone")
        self.assertEqual(pp.identifier_hits({"zzn": "x0.00015"}, [G]), [], "a different fraction: no hit")
        self.assertEqual(pp.identifier_hits({"zzn": "0.000015"}, [pp.Probe(pp.PRIVATE_KIND, "0.000015", 1)]), [pp.Hit(pp.PRIVATE_KIND, False, "zzn", 1, 1)],
                         "the base's behaviour, unchanged")
        for value in (1.5e-05, 0.000015):
            self.assertEqual(pp.identifier_hits({"zzn": value}, [G]), [pp.Hit(pp.PRIVATE_KIND, False, "zzn", 1, 8)], "the number pins stay: %r" % (value,))
        plain = pp.Probe(pp.PRIVATE_KIND, "0.000015", 1)
        self.assertEqual(pp.identifier_hits({"zzn": 1.5e-05}, [plain]), [pp.Hit(pp.PRIVATE_KIND, False, "zzn", 1, 1)], "the leaf is expanded: refused")
        self.assertEqual(pp.identifier_hits({"zzn": "1.5e-05"}, [plain]), [], "the boundary: a string spelled with an exponent is never expanded")
        self.assertEqual(pp.identifier_hits({"zz1.5e-05": 1}, [plain]), [], "nor is a key")
        self.assertEqual(_hits({"testhost": 1}, [("hostname", "testhost")]), [("hostname", "a key under the root")], "a word probe over a key is as before")
        self.assertEqual(_hits({"zztesthost": 1}, [("hostname", "testhost")]), [], "and still a whole-token match")

    def test_a_listed_digit_run_under_seven_digits_is_not_applied_to_a_number_and_one_of_seven_is_with_its_list_line(self):
        """THE NUMERIC FLOOR (2026-09-19, the comment at pp.NUMERIC_PROBE_MIN_DIGITS; its predicate corrected by the closing delta
        the same day): identifier_hits applies a listed private string to a number's spellings only through a spelling of the
        entry that carries at least seven digits counted across the whole spelling (pp.digit_count, pp.numeric_probe), because
        a shorter listed value collides with some number of a real export by coincidence too often for a match to be evidence
        (measured on a real export of 3,770 numbers: a listed four-digit run matched some number about one export in four, a
        seven-digit run about one in 7,000). The quantity is the DIGIT COUNT, never the longest run, never the character length
        and never the alphabet: the first floor (a086ced5a) gated on the longest run and excluded a listed 1234.5678 (eight
        digits, longest run four) while it kept a bare 4242424, dropping a protection the base had; a length gate would admit
        1234.56 (seven characters, six digits); the closing delta's first cut required the entry to be spelled like a number
        (pp.number_shaped) and so dropped the base's token-run match of a listed (12345678), _12345678 or 12345678/ to the leaf
        12345678, three refusals turned into sends. The boundary is pinned by execution with literals, never the constant: a
        six-digit listed run is no hit in any number that carries it (whole, inside a longer one, as a float, a negative, an
        exponent spelling, a fraction, a list element) and stays a hit in a key and in a string value; a seven-digit listed run
        is a hit as an integer, a float, a negative, an exponent spelling that canonicalises to it, inside a longer run and as a
        fraction, at the value's path, and the Hit carries the entry's LIST LINE (Probe.line) and never its text; a listed
        1234.5678 (line 5) hits the leaves 1234.5678 and 12345678e-4 carrying line 5 (the restored assertion); a listed 1234.56
        hits no number carrying it and still hits the string and the key; a listed 12345678 does NOT hit the leaf 1234.5678 (the
        trap the first stderr line advised: that number's spelling carries no eight consecutive digits); a listed (12345678)
        (line 1) hits the leaf 12345678 by its token run and not the leaf 1234.5678, a listed 1234 5678 (line 2) hits 1234.5678
        and not 12345678 (the groups split differently), a listed _12345678 and 12345678/ hit 12345678, and a listed zz4242424 is
        armed and hits nothing (no number's token is zz4242424), all as the base at 5d1de45dc had them; abc12 is under the floor
        by its two digits. The truth tables of digit_count, number_shaped and numeric_probe pin the count, the alphabet the
        stderr line reads (the ASCII digits; a lone `e`, the empty string, a space and a comma are not shaped) and that the arm
        reads the count alone (zz4242424 and (12345678) are numeric probes, abc12 is not). A word probe keeps today's token-run
        match over numbers and an all-digit session-id prefix, eight digits, is above the floor, so the floor's one effect is on
        the list. A floor of eight turns the seven-digit assertions red; a floor of six turns the six-digit ones red; the longest
        run back turns the 1234.5678 hits red; a length gate turns the 1234.56 no-hits red; the alphabet back in the arm turns
        the token-run hits and the numeric_probe truth table red."""
        six = [pp.Probe(pp.PRIVATE_KIND, "424242", 4)]
        for value in (424242, 1424242, 424242.0, -424242, 4.24242e5, 0.424242, [424242]):
            self.assertEqual(pp.identifier_hits({"a": {"n": value}}, six), [], "a six-digit listed run is not applied to a number: %r" % (value,))
        self.assertEqual(_hits({"a": {"n": "x424242"}}, six), [(pp.PRIVATE_KIND, "the value at a/n")], "a string value is checked as before")
        self.assertEqual(_hits({"a": {"424242": 1}}, six), [(pp.PRIVATE_KIND, "a key under a")], "a key is checked as before")
        seven = [pp.Probe(pp.PRIVATE_KIND, "4242424", 3)]
        for value in (4242424, 4242424.0, -4242424, 4.242424e6, 14242424, 0.4242424, 4242424.5):
            self.assertEqual(json.dumps(value).count("4242424"), 1, repr(value))
            hits = pp.identifier_hits({"a": {"n": value}}, seven)
            self.assertEqual(hits, [pp.Hit(pp.PRIVATE_KIND, False, "a/n", 2, 3)], "a seven-digit listed run is a hit in a number: %r" % (value,))
            self.assertEqual(hits[0].line, 3, "the Hit carries the entry's list line")
            self.assertNotIn("4242424", repr(hits), "and never its text")
        self.assertEqual(pp.identifier_hits({"a": {"n": 4242424}}, [(pp.PRIVATE_KIND, "4242424")])[0].line, None, "a plain tuple probe has no line")
        pointed = [pp.Probe(pp.PRIVATE_KIND, "1234.5678", 5)]
        for value in (1234.5678, 12345678e-4, -1234.5678, 91234.5678, 1234.56789):
            hits = pp.identifier_hits({"a": {"n": value}}, pointed)
            self.assertEqual(hits, [pp.Hit(pp.PRIVATE_KIND, False, "a/n", 2, 5)], "a listed 1234.5678, eight digits, is applied to a number: %r" % (value,))
            self.assertNotIn("1234", repr(hits), "and never its text")
        six_pointed = [pp.Probe(pp.PRIVATE_KIND, "1234.56", 6)]
        for value in (1234.56, 91234.56, -1234.56):
            self.assertIn("1234.56", json.dumps(value), repr(value))
            self.assertEqual(pp.identifier_hits({"a": {"n": value}}, six_pointed), [],
                             "a listed 1234.56, seven characters and six digits, is applied to no number: %r" % (value,))
        self.assertEqual(_hits({"a": {"n": "x1234.56"}}, six_pointed), [(pp.PRIVATE_KIND, "the value at a/n")], "and stays a hit in a string value")
        self.assertEqual(_hits({"a": {"1234.56": 1}}, six_pointed), [(pp.PRIVATE_KIND, "a key under a")], "and in a key")
        self.assertEqual(pp.identifier_hits({"a": {"n": 1234.5678}}, [pp.Probe(pp.PRIVATE_KIND, "12345678", 7)]), [],
                         "a listed eight-digit run protects only a number whose spelling carries it, and 1234.5678 carries no eight consecutive digits")
        self.assertEqual([pp.digit_count(s) for s in ("1234.5678", "1234.56", "424242", "4242424", "1.5e-05", "12345670000000000", "0.000015", "abc12", "abc", "")],
                         [8, 6, 6, 7, 4, 17, 7, 2, 0, 0])
        self.assertEqual([pp.number_shaped(s) for s in ("1234.5678", "-4242424", "1.5e-05", ".5678", "4242424", "abc12", "zz4242424", "e", "", "1234 5678", "1,234")],
                         [True, True, True, True, True, False, False, False, False, False, False])
        self.assertEqual([pp.numeric_probe(s) for s in ("1234.5678", "4242424", "-4242424", "12345678e-4", "0.000015", "zz4242424", "(12345678)", "1234 5678",
                                                         "424242", "1234.56", "1.5e-05", "abc12")],
                         [True, True, True, True, True, True, True, True, False, False, False, False], "the arm reads the digit count and nothing else")
        # the alphabet is not asked of the arm: an entry carrying other characters is applied by its token run, as the base did
        for text, line, hit, miss in (("(12345678)", 1, 12345678, 1234.5678), ("1234 5678", 2, 1234.5678, 12345678),
                                      ("_12345678", 3, 12345678, 1234.5678), ("12345678/", 4, 12345678, 1234.5678)):
            probe = [pp.Probe(pp.PRIVATE_KIND, text, line)]
            hits = pp.identifier_hits({"a": {"n": hit}}, probe)
            self.assertEqual(hits, [pp.Hit(pp.PRIVATE_KIND, False, "a/n", 2, line)], "a listed %s is applied to the number %r by its token run" % (text, hit))
            self.assertNotIn("12345678", repr(hits) + repr(hits[0].line), "and never its text")
            self.assertEqual(pp.identifier_hits({"a": {"n": miss}}, probe), [], "the groups of %r split unlike %s" % (miss, text))
        self.assertEqual(pp.identifier_hits({"a": {"n": 4242424}}, [pp.Probe(pp.PRIVATE_KIND, "zz4242424", 5)]), [],
                         "an armed entry carrying a letter matches no number: no number's token is zz4242424")
        self.assertEqual(_hits({"a": {"n": 4242}}, [("hostname", "4242")]), [("hostname", "the value at a/n")], "a word probe over a number is as before")
        self.assertEqual(_hits({"a": {"n": 911111111}}, [("session id", "11111111")]), [("session id", "the value at a/n")],
                         "an eight-digit id prefix is above the floor")

    def test_the_stderr_line_counts_the_listed_entries_under_the_numeric_floor_once_by_their_list_lines_and_names_no_text(self):
        """machine_probes says once on stderr how many listed entries could match a number (pp.number_matchable: spelled like one,
        or a run of digit-only tokens; the closing re-run of 2026-09-19 widened the count from the alphabet alone) but carry
        fewer digits than the floor in every spelling (pp.LIST_UNDER_NUMERIC_FLOOR), WHICH by the line of the list each is on (list lines 3 and 6 here,
        pp.list_lines_phrase; never an entry's text and never the list's path, the review of 2026-09-19): those are checked in
        keys and string values and not in numbers, and the line says what does protect a number (an entry of seven or more digits, as written or as the plain decimal
        spelling of an entry written with an exponent, matched against the number's own spelling: a listed 1234.5678 protects the
        number 1234.5678, a listed 12345678 does not, and a listed entry of fewer digits protects no number), so that a reader
        whose private value is a short number knows the numeric arm does not protect it and that listing a longer bare run
        would silence this line without protecting the value (the trap the first line laid; the closing delta of 2026-09-19).
        Over a list of a comment, a word, a six-digit run, a word with two digits, a seven-digit run, 1234.56, 1.5e-05 and
        1234.5678: two of seven (424242 and 1234.56 are spelled like a number and under the floor; 1.5e-05 is four digits as
        written and seven as its expansion 0.000015, which is the spelling armed, so it is NOT counted, where the delta's first
        cut counted it and told the operator a value it protected was unprotected; abc12 carries letters, so no number can
        carry it and it is not counted, where the first trigger counted it; 4242424 and 1234.5678 are armed), the line's exact
        text, and each probe carries its file line, the comment counting. The line names no entry's TEXT: the two values it
        spells, 1234.5678 and 12345678, are the template's own worked example, there for every list; it points at the counted
        entries by list line, 3 and 6, with uncounted entries on lines 2, 4 and 5 around and between them, so a phrase built
        from the entries' positions in the count (1 and 2) or from every listed line reds here; and it names no path, the
        list's own (ROMP_PRIVATE_STRINGS here) least of all. The silent lists are the next
        test's, on their own so that a trigger change that keeps this count and fires for one of them reds by name. Removing
        the line turns this red; so does a floor of eight (four of seven: 4242424 and 0.000015 fall under it), a floor of six
        (the line silent: 424242 and 1234.56 reach it), the longest-run trigger (five of seven: abc12 and 1234.5678 counted,
        1.5e-05 by its run of two), an any-digit trigger (four of seven, abc12 counted), a length gate (one of seven: 1234.56
        and 1.5e-05 are seven characters), or the floor decided on the entry's text alone (three of seven, 1.5e-05 counted);
        naming the counted entries by their position in the count (list lines 1 and 2), spelling an entry's text in the line or
        adding the list's path reds the exact text and the named pin for each."""
        listed = os.path.join(self.state, "list.txt")
        with open(listed, "w", encoding="utf-8") as fh:
            fh.write("# a comment on line 1\nzzcoinedzz\n424242\nabc12\n4242424\n1234.56\n1.5e-05\n1234.5678\n")
        env = {"HOME": HOME, "USER": "tester", "ROMP_PRIVATE_STRINGS": listed}
        err = io.StringIO()
        with mock.patch.object(pp.socket, "gethostname", return_value="TESTHOST.example"), contextlib.redirect_stderr(err):
            probes = pp.machine_probes(None, env=env)
        self.assertEqual(err.getvalue(), ("romp: 2 of 7 private-strings entries (list lines 3 and 6) could match a number, by their spelling or by their digit "
                                          "groups, but carry fewer than 7 digits, "
                                          "so they are checked in keys and string values and not in numbers; a number is checked against a listed entry only "
                                          "when the entry, or the plain decimal spelling of an entry written with an exponent, carries 7 or more digits, and "
                                          "the match is against the number's own spelling: a listed 1234.5678 protects the number 1234.5678, a listed "
                                          "12345678 does not, and a listed entry of fewer digits protects no number\n"))
        self.assertEqual(err.getvalue().count("romp:"), 1, "said once")
        for entry in ("zzcoinedzz", "424242", "abc12", "4242424", "1.5e-05", "0.000015"):
            self.assertNotIn(entry, err.getvalue(), "the line names no entry")
        self.assertIn("(list lines 3 and 6)", err.getvalue(), "the counted entries by their list lines, in file order")
        self.assertNotIn("(list lines 1 and 2)", err.getvalue(), "not their positions in the count")
        self.assertNotIn(listed, err.getvalue(), "the line does not name the list's path")
        self.assertNotIn(self.state, err.getvalue(), "nor any part of it")
        self.assertIn("a listed 1234.5678 protects the number 1234.5678, a listed 12345678 does not", pp.LIST_UNDER_NUMERIC_FLOOR,
                      "the two values the line spells are the template's worked example, not the list's entries")
        self.assertEqual([(p.text, p.line) for p in probes if p.kind == pp.PRIVATE_KIND],
                         [("zzcoinedzz", 2), ("424242", 3), ("abc12", 4), ("4242424", 5), ("1234.56", 6), ("1.5e-05", 7), ("1234.5678", 8)],
                         "each probe carries the file's line, the comment counting")
        self.assertTrue(all(p.line is None for p in probes if p.kind != pp.PRIVATE_KIND), "a machine string has no line")

    def test_the_stderr_line_is_silent_for_a_list_with_nothing_spelled_like_a_number_under_the_floor(self):
        """The silent side of the line above, each list on its own so a trigger change that keeps the count and fires for one of
        these reds naming it: two words; two runs at or over the floor; the empty list; a word with digits beside a run with
        letters (abc12, zz424242: the construction that fired the first line on every run on this box's list, whose entries all
        carry a letter and appear in no number); a pointed value and a negative at the floor; an exponent-spelled 1.5e-05 and
        1e+16 (four and one digit as written, seven and seventeen as 0.000015 and 10000000000000000, the spellings the arm
        applies: an entry armed through its expansion is protected, and the line must not say otherwise, which the delta's
        first cut did); an IP-shaped 10.0.0.1 beside an eight-digit run (an arrangement no number spells but the alphabet admits:
        it is counted, the cost the comment at pp.NUMBER_CHARS names, so that list is the one loud case here, 1 of 2). Any of
        the first cut's triggers (the longest run, any digit, the entry's text alone) reds a case here by name."""
        listed = os.path.join(self.state, "list.txt")
        env = {"HOME": HOME, "USER": "tester", "ROMP_PRIVATE_STRINGS": listed}
        for content in ("zzcoinedzz\nsecond-coined\n", "4242424\n12345678\n", "", "abc12\nzz424242\n", "1234.5678\n-4242424\n", "1.5e-05\n1e+16\n"):
            with open(listed, "w", encoding="utf-8") as fh:
                fh.write(content)
            err = io.StringIO()
            with mock.patch.object(pp.socket, "gethostname", return_value="TESTHOST.example"), contextlib.redirect_stderr(err):
                pp.machine_probes(None, env=env)
            self.assertEqual(err.getvalue(), "", "nothing spelled like a number under the floor, nothing said: %r" % content)
        with open(listed, "w", encoding="utf-8") as fh:
            fh.write("10.0.0.1\n12345678\n")
        err = io.StringIO()
        with mock.patch.object(pp.socket, "gethostname", return_value="TESTHOST.example"), contextlib.redirect_stderr(err):
            pp.machine_probes(None, env=env)
        self.assertEqual(err.getvalue(), pp.LIST_UNDER_NUMERIC_FLOOR % (1, 2, "list line 1", 7, 7) + "\n",
                         "an IP-shaped entry is inside the alphabet and is counted, by its list line")

    def test_the_stderr_line_counts_an_under_floor_run_of_digit_only_tokens_too_and_not_an_entry_with_a_letter(self):
        """The widened count (the closing re-run of 2026-09-19, finding 3, ruled as widen): the line counts an under-floor entry
        that COULD MATCH A NUMBER (pp.number_matchable), spelled in the number alphabet (number_shaped) or a run of digit-only
        tokens, since the token-run arm applies such an entry at seven digits ((1234567), _1234567 and 1234567/ each refuse the
        leaf 1234567, executed here as literals), so the operator whose private value is an underscored or parenthesised
        six-digit id is told it is unprotected in numbers; the head at b3df460d5 counted the alphabet alone and said 2 of 6 over
        the report's six-shape list, justified by a clause execution falsified (an entry outside the alphabet was said to be
        matched by no number, so the remedy could not reach it), and that clause is gone from the module (the negative source
        pins here; the docs/reference.md side is the Docs class's, in the upload module). The truth table of number_matchable;
        the six-shape list gives 6 of 6, list lines 1 to 6, no entry's punctuated text in the line; abc12 and zz424242 stay
        silent (a letter in a token outside the number alphabet), while a listed 1e5 alone, in the alphabet and carrying the
        one letter a number spells, an exponent's e, IS counted, 1 of 1, list line 1 (the re-run's verification found the
        round's first wording, that no number's token carries a letter, false by that entry: TOKEN splits 1.5e-05 into 1, 5e
        and 05, and this test's own truth table has number_matchable("1e-5") True); (123456) against the leaf 123456 is no hit
        (under the floor, which is what the line is for). Reverting the count to number_shaped reds the six-shape pin (2 of 6); an
        any-digit predicate (cd3b4cfab's trigger) reds the abc12 silence and the truth table; the old template phrase reds the
        six-shape literal; the clause back in the module reds the source pin; the letter clause re-asserted in the module reds the
        negative source pin."""
        for text in ("(1234567)", "_1234567", "1234567/", "(123456)", "1 23456", "12-3456", "10.0.0.1", "1.5e-05", "1e-5", "4242424"):
            self.assertTrue(pp.number_matchable(text), text)
        for text in ("zz424242", "abc12", "e", "", "()", "_"):
            self.assertFalse(pp.number_matchable(text), text)
        for text in ("(1234567)", "_1234567", "1234567/"):
            self.assertEqual(pp.identifier_hits({"a": {"n": 1234567}}, [pp.Probe(pp.PRIVATE_KIND, text, 1)]), [pp.Hit(pp.PRIVATE_KIND, False, "a/n", 2, 1)],
                             "the token-run arm applies %s to the leaf 1234567: the remedy the line names reaches this entry" % text)
        self.assertEqual(pp.identifier_hits({"a": {"n": 123456}}, [pp.Probe(pp.PRIVATE_KIND, "(123456)", 1)]), [], "six digits: under the floor, no hit")
        listed = os.path.join(self.state, "list.txt")
        env = {"HOME": HOME, "USER": "tester", "ROMP_PRIVATE_STRINGS": listed}
        with open(listed, "w", encoding="utf-8") as fh:
            fh.write("(123456)\n_123456\n123456/\n1 23456\n12-3456\n123456\n")
        err = io.StringIO()
        with mock.patch.object(pp.socket, "gethostname", return_value="TESTHOST.example"), contextlib.redirect_stderr(err):
            pp.machine_probes(None, env=env)
        self.assertEqual(err.getvalue(), pp.LIST_UNDER_NUMERIC_FLOOR % (6, 6, "list lines 1, 2, 3, 4, 5 and 6", 7, 7) + "\n", "every shape is counted")
        self.assertIn("(list lines 1, 2, 3, 4, 5 and 6) could match a number, by their spelling or by their digit groups, but carry fewer than 7 digits",
                      err.getvalue())
        for entry in ("(123456)", "_123456", "123456/", "1 23456", "12-3456"):
            self.assertNotIn(entry, err.getvalue(), "no entry's text is in the line: %s" % entry)
        with open(listed, "w", encoding="utf-8") as fh:
            fh.write("abc12\nzz424242\n")
        err = io.StringIO()
        with mock.patch.object(pp.socket, "gethostname", return_value="TESTHOST.example"), contextlib.redirect_stderr(err):
            pp.machine_probes(None, env=env)
        self.assertEqual(err.getvalue(), "", "a letter in a token outside the number alphabet: nothing is counted")
        with open(listed, "w", encoding="utf-8") as fh:
            fh.write("1e5\n")
        err = io.StringIO()
        with mock.patch.object(pp.socket, "gethostname", return_value="TESTHOST.example"), contextlib.redirect_stderr(err):
            pp.machine_probes(None, env=env)
        self.assertEqual(err.getvalue(), pp.LIST_UNDER_NUMERIC_FLOOR % (1, 1, "list line 1", 7, 7) + "\n",
                         "the one letter a number spells, an exponent's e: in the alphabet, six digits as 100000, counted")
        with open(pp.__file__, encoding="utf-8") as fh:
            source = fh.read()
        for clause in ("substring of no number", "remedy cannot apply", "since no number's token carries"):
            self.assertNotIn(clause, source, "the falsified clause is gone from the module: %s" % clause)

    def test_the_stderr_line_names_the_counted_entries_by_list_line_in_file_order_and_never_their_text_or_the_path(self):
        """The review of 2026-09-19: the line points at each entry it counts by the ONE-BASED LINE of the list it is on
        (pp.list_lines_phrase: `list line 4`, `list lines 3 and 6`, `list lines 2, 5 and 9`), the number an editor shows and the
        number a refusal names, so the operator can find the entry without the line spelling its text (the list exists to keep
        those off every output, stderr included) and without the list's path (there is one location, the docs name it, and a
        home path on stderr every run is noise). Over a list of a comment, 4242 (line 2), a word, a blank, 98.76 (line 5),
        4242424 (armed, seven digits), abc12 (a letter, in no number), 1e+16 (armed through its expansion), -42.5 (line 9) and
        zz4242424 (a letter): eight entries, three counted, and the line is exactly the template with 3, 8, `list lines 2, 5 and
        9` and the floor twice, the uncounted entries on lines 3, 6, 7, 8 and 10 around and between the counted ones, so a
        phrase built from the entries' positions in the count (1, 2 and 3) or from every listed line reds here; no entry's text
        is in the line, and the list's path is not. A repeated entry is counted once per line (1234.56, 1234.56, 424242: 3 of 3,
        list lines 1, 2 and 3), machine_probes' docstring's own example. The phrase alone: one line, two, three and four, the
        last two joined by `and` and the rest by commas, one phrase inside the one line, and past pp.LIST_LINES_NAMED, six, the
        first six and `and N more` (the phrase alone here; the list-driven cases are the next test's). Removing the lines from
        the template, rendering them from the count's positions, spelling an entry's text in the line or adding the path each
        reds a pin here by name; so do the cap removed, a cap of five and a remainder off by one, on the phrase pins."""
        self.assertEqual(pp.list_lines_phrase([4]), "list line 4")
        self.assertEqual(pp.list_lines_phrase([3, 6]), "list lines 3 and 6")
        self.assertEqual(pp.list_lines_phrase([2, 5, 9]), "list lines 2, 5 and 9")
        self.assertEqual(pp.list_lines_phrase([2, 5, 9, 12]), "list lines 2, 5, 9 and 12")
        self.assertEqual(pp.list_lines_phrase([2, 5, 9, 12, 15, 18]), "list lines 2, 5, 9, 12, 15 and 18", "six: the plain list")
        self.assertEqual(pp.list_lines_phrase([2, 5, 9, 12, 15, 18, 21]), "list lines 2, 5, 9, 12, 15, 18 and 1 more", "seven: six and the rest counted")
        self.assertEqual(pp.list_lines_phrase([2, 5, 9, 12, 15, 18, 21, 24, 27]), "list lines 2, 5, 9, 12, 15, 18 and 3 more")
        listed = os.path.join(self.state, "list.txt")
        entries = ["# strings that must never be published", "4242", "zzcoinedzz", "", "98.76", "4242424", "abc12", "1e+16", "-42.5", "zz4242424"]
        with open(listed, "w", encoding="utf-8") as fh:
            fh.write("\n".join(entries) + "\n")
        env = {"HOME": HOME, "USER": "tester", "ROMP_PRIVATE_STRINGS": listed}
        err = io.StringIO()
        with mock.patch.object(pp.socket, "gethostname", return_value="TESTHOST.example"), contextlib.redirect_stderr(err):
            probes = pp.machine_probes(None, env=env)
        line = err.getvalue()
        self.assertEqual(line, pp.LIST_UNDER_NUMERIC_FLOOR % (3, 8, "list lines 2, 5 and 9", 7, 7) + "\n")
        self.assertEqual(line.count("romp:"), 1, "said once")
        self.assertIn("romp: 3 of 8 private-strings entries (list lines 2, 5 and 9) could match a number", line,
                      "the counted entries by the list lines they are on, in file order")
        for wrong in ("(list lines 1, 2 and 3)", "(list lines 2, 3, 5, 6, 7, 8, 9 and 10)"):
            self.assertNotIn(wrong, line, "not the positions in the count, not every listed line")
        for entry in entries[1:]:
            if entry:
                self.assertNotIn(entry, line, "no entry's text is in the line: %s" % entry)
        self.assertNotIn(listed, line, "the list's path is not in the line")
        self.assertNotIn(self.state, line, "nor any part of it")
        self.assertEqual([p.line for p in probes if p.kind == pp.PRIVATE_KIND], [2, 3, 5, 6, 7, 8, 9, 10], "every entry is a probe carrying its line")
        with open(listed, "w", encoding="utf-8") as fh:
            fh.write("1234.56\n1234.56\n424242\n")
        err = io.StringIO()
        with mock.patch.object(pp.socket, "gethostname", return_value="TESTHOST.example"), contextlib.redirect_stderr(err):
            pp.machine_probes(None, env=env)
        self.assertEqual(err.getvalue(), pp.LIST_UNDER_NUMERIC_FLOOR % (3, 3, "list lines 1, 2 and 3", 7, 7) + "\n",
                         "a repeated entry is counted once per line and named by each")

    def test_the_stderr_line_names_at_most_six_list_lines_in_file_order_and_counts_the_rest(self):
        """The cap on the enumeration (pp.LIST_LINES_NAMED, six; the review of 2026-09-19): an advisory that wraps is one nobody
        reads, so past six counted entries the line names the first six lines in file order and counts the rest, `and N more`,
        N the counted entries past the six. Over a list with nine counted entries on lines 2, 5, 9, 12, 15, 18, 21, 24 and 27
        and words and comments between them (25 entries): the line is exactly the template with 9, 25, `list lines 2, 5, 9, 12,
        15, 18 and 3 more` and the floor twice, one newline and it at the end, the counted set recomputed from the list through
        the module's own predicates (number_matchable, numeric_probe over number_spellings) equal to those nine lines, the
        remainder the three past six, and the lines past the cap absent by name. The same list cut to six counted entries (6 of
        17) renders all six and counts nothing as more, so every pin at or under six holds byte for byte. The cap removed
        (nine lines listed), a cap of five (`15 and 4 more` here, `15 and 1 more` at six) and a remainder off by one (`and 4
        more`) each red the exact line."""
        listed = os.path.join(self.state, "list.txt")
        env = {"HOME": HOME, "USER": "tester", "ROMP_PRIVATE_STRINGS": listed}
        counted_at = [2, 5, 9, 12, 15, 18, 21, 24, 27]                                   # nine counted entries, words and comments between
        values = ["4242", "98.76", "-42.5", "1.5", "777", "12.34", "0.5", "9999", "-1"]
        rows = [values[counted_at.index(n)] if n in counted_at else "# a comment on line %d" % n if n % 10 == 0
                else "zz" + "abcdefghijklmnopqrstuvwxyz"[n % 26] * 3 for n in range(1, 28)]
        with open(listed, "w", encoding="utf-8") as fh:
            fh.write("\n".join(rows) + "\n")
        err = io.StringIO()
        with mock.patch.object(pp.socket, "gethostname", return_value="TESTHOST.example"), contextlib.redirect_stderr(err):
            pp.machine_probes(None, env=env)
        line = err.getvalue()
        self.assertEqual(line, pp.LIST_UNDER_NUMERIC_FLOOR % (9, 25, "list lines 2, 5, 9, 12, 15, 18 and 3 more", 7, 7) + "\n",
                         "nine counted: the first six lines in file order, then the rest counted")
        self.assertIn("(list lines 2, 5, 9, 12, 15, 18 and 3 more) could match", line)
        self.assertEqual(line.count("\n"), 1, "one line: no newline inside it")
        self.assertTrue(line.endswith("\n"))
        self.assertEqual(len(rows) - sum(1 for r in rows if r.startswith("#")), 25, "the list's length is every entry")
        counted = [n for n, t in pp.private_entries(env) if pp.number_matchable(t.lower())
                   and not any(pp.numeric_probe(sp) for sp in pp.number_spellings(t.lower(), pp._number_value(t.lower())))]
        self.assertEqual(counted, counted_at, "the counted set is the counted set")
        self.assertEqual(len(counted) - 6, 3, "and the remainder is the counted entries past the six named")
        for absent in (", 21", ", 24", ", 27", "and 27", "and 9 more", "and 2 more", "and 4 more"):
            self.assertNotIn(absent, line, "the lines past the cap are counted, not named: %s" % absent)
        rows = rows[:18]                                                                  # six counted entries: no cap, no `more`
        with open(listed, "w", encoding="utf-8") as fh:
            fh.write("\n".join(rows) + "\n")
        err = io.StringIO()
        with mock.patch.object(pp.socket, "gethostname", return_value="TESTHOST.example"), contextlib.redirect_stderr(err):
            pp.machine_probes(None, env=env)
        self.assertEqual(err.getvalue(), pp.LIST_UNDER_NUMERIC_FLOOR % (6, 17, "list lines 2, 5, 9, 12, 15 and 18", 7, 7) + "\n",
                         "six counted: every line named, none counted")
        self.assertNotIn(" more) are", err.getvalue(), "at the cap nothing is counted as more (the template's own `or more digits` stays)")

    def test_the_private_strings_list_feeds_the_probes_when_present_and_is_a_no_op_absent(self):
        """The machine-local list the repository's pre-push hook reads (~/.config/romp/private-strings.txt: one string per
        line, `#` comments, blanks) is the maintainer's own list of what must never be published, a coined project nickname
        among them, which fits the identifier grammar and is neither the hostname nor the login, so no other probe knew it
        and a document carrying one passed all three checks (the upload's second review round, 2026-09-18). Each entry is a
        probe of kind `private string` (PRIVATE_KIND), lower-cased, PROBE_MIN NOT applied (the list is the maintainer's
        explicit choice, not the heuristic the floor exists for: the floor dropped a three-character entry silently and a
        document carrying it was sent, the third review round), matched as a SUBSTRING or a run of whole tokens, the union
        (the same round: the hook matches a plain substring, so a listed token glued to letters must be a hit here too, and
        the token run keeps a dotted entry found under another join, which the hook's substring grep misses); the path is
        resolved the way the hook resolves it (ROMP_PRIVATE_STRINGS, else XDG_CONFIG_HOME, else HOME/.config); no file is
        no probe, so a clone that never set one up is unchanged. The bound: PRIVATE_STRINGS_MAX + 1 bytes are read and a
        file over the bound is cut back to its last complete line, so no fragment of an entry becomes a probe (a 12-byte
        fragment did, falsely refused an unrelated document, and the entry it was cut from travelled), with one loud stderr
        line saying the entries past the bound are not checked; and a listed entry that did not become a probe is said on
        stderr the same way, so the list is never silently not in force. This widens the shared check: the export,
        restart-metrics --json --public and the upload all run it. Fails before: no such kind existed; then abc was dropped,
        the glued forms passed and the fragment was a probe."""
        home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home, True)
        env = {"HOME": home, "USER": "tester"}
        with mock.patch.object(pp.socket, "gethostname", return_value="TESTHOST.example"):
            self.assertEqual([p for p in pp.machine_probes(None, env=env) if p[0] == "private string"], [], "no file, no probe")
            self.assertEqual(pp.private_strings(env), [])
            self.assertEqual(pp.private_strings({}), [], "no HOME and no variable: no path at all, no traceback")
            os.makedirs(os.path.join(home, ".config", "romp"))
            with open(os.path.join(home, ".config", "romp", "private-strings.txt"), "w", encoding="utf-8") as fh:
                fh.write("# the list the pre-push hook reads\n\n   ZZCOINEDZZ   \nabc\nsecond-coined # trailing comment\n")
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                probes = pp.machine_probes(None, env=env)
            self.assertEqual([s for kind, s in probes if kind == "private string"], ["zzcoinedzz", "abc", "second-coined"],
                             "comments and blanks dropped, lower-cased, in file order; the three-character line KEPT, PROBE_MIN not applied to the list")
            self.assertEqual(err.getvalue(), "", "every entry became a probe: nothing to say")
            self.assertEqual(pp.private_strings(env), ["ZZCOINEDZZ", "abc", "second-coined"], "the raw entries, as the hook reads them")
            self.assertEqual(pp.PRIVATE_KIND, "private string")
            self.assertNotIn(pp.PRIVATE_KIND, pp.WORD_KINDS, "not a word probe alone: the union")
            self.assertEqual(pp.WORD_KINDS, frozenset({"hostname", "username"}))
            self.assertEqual(_hits({"a": {"b": "zzcoinedzz-app"}}, probes), [("private string", "the value at a/b")])
            self.assertEqual(_hits({"a": {"b": "app_ZZcoinedZZ"}}, probes), [("private string", "the value at a/b")], "case-insensitive")
            self.assertEqual(_hits({"a": {"zzcoinedzzs": 1}}, probes), [("private string", "a key under a")],
                             "a substring, as the hook's grep would find it (a whole-token match alone passed this)")
            self.assertEqual(_hits({"a": {"zzcoinedzzChat": 1}}, probes), [("private string", "a key under a")], "the token glued to letters, as a key")
            self.assertEqual(_hits({"a": {"b": "chatZzcoinedzz"}}, probes), [("private string", "the value at a/b")], "and as a value")
            self.assertEqual(_hits({"a": {"b": "abc"}}, probes), [("private string", "the value at a/b")], "the three-character entry is a probe")
            self.assertEqual(_hits({"a": {"b": "xabcx"}}, probes), [("private string", "the value at a/b")])
            self.assertEqual(_hits({"second": 1, "coined": 1}, probes), [], "the run must be contiguous")
            self.assertEqual(_hits({"a": {"second.coined": 1}}, probes), [("private string", "a key under a")])
            self.assertEqual(_hits({"a": {"second_coined": 1}}, probes), [("private string", "a key under a")],
                             "the token run: a dotted entry under another join, which the hook's substring grep misses and the union keeps")
            self.assertEqual(_hits({"a": {"b": "SECOND-COINED"}}, probes), [("private string", "the value at a/b")])
            self.assertEqual(_hits({"a": {"b": "secondcoined"}}, probes), [], "neither a substring nor the token run")
            # the loud line: an entry that did not become a probe (the reader returns no blank, so a blank stands in for a filter
            # a later change adds) is counted and said once on stderr; nothing is said when every entry became one
            err = io.StringIO()
            with mock.patch.object(pp, "private_entries", return_value=[(1, "zzcoinedzz"), (2, "   ")]), contextlib.redirect_stderr(err):
                self.assertEqual([s for k, s in pp.machine_probes(None, env=env) if k == "private string"], ["zzcoinedzz"])
            self.assertEqual(err.getvalue(), "romp: 1 of 2 private-strings entries did not become probes and are not checked; the list is not fully in force\n")
            err = io.StringIO()
            with mock.patch.object(pp, "private_entries", return_value=[(1, "zzcoinedzz"), (2, "abc"), (3, "ABC")]), contextlib.redirect_stderr(err):
                self.assertEqual([s for k, s in pp.machine_probes(None, env=env) if k == "private string"], ["zzcoinedzz", "abc"])
            self.assertEqual(err.getvalue(), "", "a repeated entry became the one probe it spells: nothing dropped, nothing said")
            # the path, the way the hook resolves it: the variable first, then XDG_CONFIG_HOME, then HOME/.config
            xdg = tempfile.mkdtemp()
            self.addCleanup(shutil.rmtree, xdg, True)
            os.makedirs(os.path.join(xdg, "romp"))
            with open(os.path.join(xdg, "romp", "private-strings.txt"), "w", encoding="utf-8") as fh:
                fh.write("xdgcoined\n")
            explicit = os.path.join(xdg, "explicit.txt")
            with open(explicit, "w", encoding="utf-8") as fh:
                fh.write("explicitcoined\n")
            self.assertEqual(pp.private_strings_path(env), os.path.join(home, ".config", "romp", "private-strings.txt"))
            self.assertEqual(pp.private_strings_path(dict(env, XDG_CONFIG_HOME=xdg)), os.path.join(xdg, "romp", "private-strings.txt"))
            self.assertEqual(pp.private_strings_path(dict(env, XDG_CONFIG_HOME=xdg, ROMP_PRIVATE_STRINGS=explicit)), explicit)
            self.assertEqual([s for k, s in pp.machine_probes(None, env=dict(env, XDG_CONFIG_HOME=xdg)) if k == "private string"], ["xdgcoined"])
            self.assertEqual([s for k, s in pp.machine_probes(None, env=dict(env, ROMP_PRIVATE_STRINGS=explicit)) if k == "private string"], ["explicitcoined"])
            # the bound: a large file costs PRIVATE_STRINGS_MAX and its tail is dropped, never a traceback; a line of bytes that are
            # not UTF-8 is not an entry and is said (the fourth review round, 2026-09-19: replaced, it was a probe that matched
            # nothing while the list read as in force)
            with open(explicit, "wb") as fh:
                fh.write(b"first\n" + b"\xff\xfe\n" + b"x" * pp.PRIVATE_STRINGS_MAX + b"\nlast\n")
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                got = pp.private_strings(dict(env, ROMP_PRIVATE_STRINGS=explicit))
            self.assertEqual(got, ["first"], "the good line is an entry, the undecodable one is not, the tail past the bound is cut")
            self.assertEqual(pp.PRIVATE_STRINGS_MAX, 64 * 1024)
            self.assertEqual(err.getvalue(), "romp: the private-strings list is over 65536 bytes; entries past the bound are not checked\n"
                                             "romp: 1 line(s) of the private-strings list at %s are not UTF-8 and are not checked\n" % explicit)
            # the cut falls back to the last complete line: a list built so the bound lands mid-line, the fragment is not an entry,
            # the last complete entry before the bound is, the entry past it is not, and the loud line is said once; a file exactly
            # at the bound is read whole and nothing is said (fails before: a 12-byte fragment of an entry was a probe of its own)
            whole = (pp.PRIVATE_STRINGS_MAX - 1) // 12                                          # 12-byte lines, as many as fit whole
            head = b"".join(b"entry%06d\n" % i for i in range(whole))
            straddle = b"straddle-entry-cut-by-the-bound\n"
            self.assertLess(len(head), pp.PRIVATE_STRINGS_MAX)
            self.assertGreater(len(head) + len(straddle), pp.PRIVATE_STRINGS_MAX, "the bound falls inside the straddling line")
            fragment = straddle[:pp.PRIVATE_STRINGS_MAX - len(head)].decode()                  # what a cut at the bound would leave of it
            self.assertEqual(fragment, "stra")
            with open(explicit, "wb") as fh:
                fh.write(head + straddle + b"pastbound\n")
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                got = pp.private_strings(dict(env, ROMP_PRIVATE_STRINGS=explicit))
            self.assertEqual(got[-1], "entry%06d" % (whole - 1), "the last complete entry inside the bound is the last entry")
            self.assertEqual(len(got), whole)
            self.assertNotIn(fragment, got, "the fragment the bound cut is not an entry")
            self.assertNotIn(straddle.strip().decode(), got, "the entry the bound cut is not checked (said on stderr), not a fragment of it")
            self.assertNotIn("pastbound", got)
            self.assertEqual(err.getvalue(), "romp: the private-strings list is over 65536 bytes; entries past the bound are not checked\n")
            with open(explicit, "wb") as fh:
                fh.write(b"a" * (pp.PRIVATE_STRINGS_MAX - 1) + b"\n")                          # exactly the bound: read whole, nothing said
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                got = pp.private_strings(dict(env, ROMP_PRIVATE_STRINGS=explicit))
            self.assertEqual(got, ["a" * (pp.PRIVATE_STRINGS_MAX - 1)])
            self.assertEqual(err.getvalue(), "")
        # through the export's own check, as a value and as a key, the kind and the path named and never the string
        probes = [pp.Probe("private string", "zzcoinedzz", 3)] + SYNTHETIC_PROBES      # the entry on line 3 of its list
        doc = pe.export_document(leak_snapshot())
        doc["perf"]["heap"]["note"] = "zzcoinedzz"
        with mock.patch.object(pe.pp, "machine_probes", return_value=probes):
            self.assertEqual(pe.check_document(doc, pe.Path(tempfile.mkdtemp())),
                             "a string this machine knows (private string) survives as the value at perf/heap/note; "
                             "edit line 3 of the private-strings list or that value; nothing written")
            doc = pe.export_document(leak_snapshot())
            doc["perf"]["heap"]["zzcoinedzz"] = 1
            self.assertEqual(pe.check_document(doc, pe.Path(tempfile.mkdtemp())),
                             "a string this machine knows (private string) survives as a key under perf/heap; "
                             "edit line 3 of the private-strings list or that key; nothing written")
            self.assertIsNone(pe.check_document(pe.export_document(leak_snapshot()), pe.Path(tempfile.mkdtemp())))

    def test_the_private_list_is_read_to_the_bound_plus_one_byte_and_never_whole(self):
        """The read bound on the private list, pinned where it is decided (tests-2, the third review round: replacing
        read(PRIVATE_STRINGS_MAX + 1) with read() left every case green, since the over-the-bound cases assert what the cut
        left, which is the same whether the bound or the whole file was read). open_regular is replaced by a recording file
        whose payload is far past the bound; the one read asked for is PRIVATE_STRINGS_MAX + 1 bytes, the over-the-bound line
        is said, and the entries are the whole lines inside the bound. The mutant reads the whole payload and records -1."""
        asked = []

        class Recording:
            payload = b"entry\n" * (pp.PRIVATE_STRINGS_MAX // 2)               # 6-byte lines, three times the bound

            def read(self, n=-1):
                asked.append(n)
                return self.payload if n is None or n < 0 else self.payload[:n]

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False
        err = io.StringIO()
        with mock.patch.object(pp, "open_regular", return_value=Recording()), contextlib.redirect_stderr(err):
            got = pp.private_strings({"ROMP_PRIVATE_STRINGS": "/no/such/list.txt"})
        self.assertEqual(asked, [pp.PRIVATE_STRINGS_MAX + 1], "one bounded read, never an unbounded one")
        self.assertEqual(err.getvalue(), pp.LIST_OVER_BOUND + "\n")
        self.assertEqual(got, ["entry"] * (pp.PRIVATE_STRINGS_MAX // 6), "the whole lines inside the bound, and no more")

    def test_a_short_listed_entry_is_checked_and_the_export_child_refuses_a_document_carrying_it(self):
        """The three-character entry the PROBE_MIN floor dropped is a probe (correctness-2, the third review round, 2026-09-18):
        the export child, with ROMP_PRIVATE_STRINGS naming a list that carries `abc`, refuses a snapshot whose app table
        carries the same string as a key, naming the kind and the path and never the string, and writes nothing; the same
        snapshot without the list exports. Fails before: the entry was dropped silently, exit 0, the file written."""
        listed = os.path.join(self.xdg, "private-strings.txt")
        with open(listed, "w", encoding="utf-8") as fh:
            fh.write("zzcoinedzz\nabc\n")
        snap = leak_snapshot()
        snap["pusher"]["connectPush"]["byApp"]["abc"] = {"count": 1}
        with open(self.src, "w") as fh:
            json.dump(snap, fh)
        r = _run(["--public", "--from", self.src], env_extra={"ROMP_PRIVATE_STRINGS": listed}, state=self.state)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertEqual(r.stderr, "romp perf export: refused: a string this machine knows (private string) survives as a key under "
                                   "perf/pusher/connectPush/byApp; edit line 2 of the private-strings list or that key; nothing written\n")
        self.assertNotIn("abc", r.stdout + r.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.state, "perf-exports")))
        r = _run(["--public", "--from", self.src], state=self.state)
        self.assertEqual(r.returncode, 0, r.stderr + " (without the list, abc is a grammar-fitting word)")

    def test_a_listed_digit_run_a_counter_spells_refuses_the_export_naming_the_value_path_and_never_the_number(self):
        """The scan over numbers (identifier_hits, the upload's fourth review round, 2026-09-19) is the shared check's, so the
        export child refuses a snapshot whose counter spells a listed digit run, an integer or a float, naming the kind and the
        value's path and never the number, and writes nothing; the same snapshot without the list exports, the counter a
        number like any other. This is the cost the reference states for a listed string that is romp vocabulary, and the
        remedy is the same, editing the list. Two roads the closing check of 2026-09-19 found open on this verb are refused
        here too. A listed 1234.5678 (eight digits, at the floor by digit count) as pusher.cycle_ms_p50, the shape that counter
        has on a real kernel: the base at 5d1de45dc refused it and a086ced5a's longest-run floor sent it; the digits are in no
        output, and the stderr line's own worked example, which spells 1234.5678, is not there either, since an armed entry is
        not under the floor and nothing else is listed. A listed 12345670000000000 as pusher.cycles, spelled 1.234567e+16 by
        json.dump (repr puts the point after the first digit) and spelled as the integer: both refused, the first by the
        plain decimal expansion. And the token run the closing delta's first cut dropped by gating the arm on the alphabet: a
        listed (12345678), characters no number spells around the run, with pusher.cycles carrying 12345678 is refused naming
        line 1, as the base did (the closing check's Refuted section measured that cut as three refusals turned into sends).
        The negative control the first stderr line's trap relied on: a listed 12345678 with the same 1234.5678 counter is the
        next test's. Fails before: exit 0 and the file written with the run in it (the first case); exit 0 and the value
        written (the closing check's two, and the token-run case under the first cut)."""
        listed = os.path.join(self.xdg, "private-strings.txt")
        refusal = ("romp perf export: refused: a string this machine knows (private string) survives as the value at "
                   "%s; edit line 1 of the private-strings list or that value; nothing written\n")
        with open(listed, "w", encoding="utf-8") as fh:
            fh.write("4242424242\n")
        for value in (4242424242, 4242424242.0, 4.242424242e9):
            snap = leak_snapshot()
            snap["pusher"]["cycles"] = value
            with open(self.src, "w") as fh:
                json.dump(snap, fh)
            r = _run(["--public", "--from", self.src], env_extra={"ROMP_PRIVATE_STRINGS": listed}, state=self.state)
            self.assertEqual(r.returncode, 1, repr(value) + "\n" + r.stdout + r.stderr)
            self.assertEqual(r.stderr, refusal % "perf/pusher/cycles", repr(value))
            self.assertNotIn("4242424242", r.stdout + r.stderr, repr(value))
            self.assertFalse(os.path.exists(os.path.join(self.state, "perf-exports")), repr(value))
        r = _run(["--public", "--from", self.src], state=self.state)
        self.assertEqual(r.returncode, 0, r.stderr + " (without the list, the counter is a number like any other)")
        shutil.rmtree(os.path.join(self.state, "perf-exports"))
        # the restored protection: a pointed value of eight digits, the shape pusher.cycle_ms_p50 has on a real kernel; the
        # fixture's sha abbreviates to 0123456789ab, a STRING value carrying the bare run 12345678, so it goes: this case and
        # its control are about the number
        with open(listed, "w", encoding="utf-8") as fh:
            fh.write("1234.5678\n")
        snap = leak_snapshot()
        snap.pop("kernel_sha")
        snap["pusher"]["cycle_ms_p50"] = 1234.5678
        with open(self.src, "w") as fh:
            json.dump(snap, fh)
        r = _run(["--public", "--from", self.src], env_extra={"ROMP_PRIVATE_STRINGS": listed}, state=self.state)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertEqual(r.stderr, refusal % "perf/pusher/cycle_ms_p50")
        for digits in ("1234.5678", "12345678"):
            self.assertNotIn(digits, r.stdout + r.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.state, "perf-exports")))
        # the exponent spelling: one value, as json.dump spells the float and as the integer
        with open(listed, "w", encoding="utf-8") as fh:
            fh.write("12345670000000000\n")
        for value in (1.234567e+16, 12345670000000000):
            snap = leak_snapshot()
            snap["pusher"]["cycles"] = value
            with open(self.src, "w") as fh:
                json.dump(snap, fh)
            with open(self.src, encoding="utf-8") as fh:
                self.assertIn('"cycles": ' + json.dumps(value), fh.read(), "the snapshot spells the value as json does: %r" % (value,))
            r = _run(["--public", "--from", self.src], env_extra={"ROMP_PRIVATE_STRINGS": listed}, state=self.state)
            self.assertEqual(r.returncode, 1, repr(value) + "\n" + r.stdout + r.stderr)
            self.assertEqual(r.stderr, refusal % "perf/pusher/cycles", repr(value))
            for digits in ("12345670000000000", "1.234567e+16", "1234567"):
                self.assertNotIn(digits, r.stdout + r.stderr, repr(value))
            self.assertFalse(os.path.exists(os.path.join(self.state, "perf-exports")), repr(value))
        # the token run: an entry carrying characters no number spells, applied by its whole-token run as the base did (the
        # closing delta's first cut gated the arm on the alphabet and sent this document); the sha string carries the bare run
        # and not the parenthesised entry, so it stays, and the refusal is the number's
        with open(listed, "w", encoding="utf-8") as fh:
            fh.write("(12345678)\n")
        snap = leak_snapshot()
        snap["pusher"]["cycles"] = 12345678
        with open(self.src, "w") as fh:
            json.dump(snap, fh)
        r = _run(["--public", "--from", self.src], env_extra={"ROMP_PRIVATE_STRINGS": listed}, state=self.state)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertEqual(r.stderr, refusal % "perf/pusher/cycles")
        self.assertNotIn("12345678", r.stdout + r.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.state, "perf-exports")))
        r = _run(["--public", "--from", self.src], state=self.state)
        self.assertEqual(r.returncode, 0, r.stderr + " (without the list, the counter is a number like any other)")

    def test_a_listed_bare_eight_digit_run_neither_protects_a_pointed_value_nor_is_said_to(self):
        """The negative control the first stderr line's trap relied on (the closing check of 2026-09-19): with 12345678 listed
        and pusher.cycle_ms_p50 carrying 1234.5678, the export is written, rc 0, the file carrying the value, and stderr is
        EMPTY. An eight-digit entry is above the floor, so it is applied to numbers and nothing is under the floor to be said;
        and it protects only a number whose spelling carries that run, which 1234.5678 does not (its longest run is four). The
        first line advised listing more of the value's digits, which produced exactly this: the line silenced and the value on
        the wire; the new line says what does protect a number instead, and the previous test pins that a listed 1234.5678
        refuses. The fixture's sha abbreviation, a string carrying the run, is dropped so the control is about the number. A
        floor of nine turns the empty-stderr assertion red (the entry falls under the floor and the line fires); an advisory
        that counts every number-shaped entry, floor ignored, turns it red the same way."""
        listed = os.path.join(self.xdg, "private-strings.txt")
        with open(listed, "w", encoding="utf-8") as fh:
            fh.write("12345678\n")
        snap = leak_snapshot()
        snap.pop("kernel_sha")
        snap["pusher"]["cycle_ms_p50"] = 1234.5678
        with open(self.src, "w") as fh:
            json.dump(snap, fh)
        r = _run(["--public", "--from", self.src], env_extra={"ROMP_PRIVATE_STRINGS": listed}, state=self.state)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(r.stderr, "", "an eight-digit entry is above the floor, so nothing is under it and nothing is said")
        written = os.listdir(os.path.join(self.state, "perf-exports"))
        self.assertEqual(len(written), 1)
        with open(os.path.join(self.state, "perf-exports", written[0]), encoding="utf-8") as fh:
            self.assertIn('"cycle_ms_p50": 1234.5678', fh.read(), "the value travels: a listed bare run protects only a number whose spelling carries it")

    def test_a_listed_six_digit_run_inside_a_byte_total_exports_with_the_stderr_line_and_a_seven_digit_run_refuses_naming_the_list_line(self):
        """The floor by the export child (2026-09-19). With a list of a comment, a word, a blank and a six-digit run (line 4), a
        snapshot whose rss_kb carries the run inside a byte total (9424242) exports, exit 0, the file written with the number
        in it, and stderr is exactly the one line saying 1 of 2 entries (list line 4: the entry by the line it is on, never its text
        or the list's path) could match a number but carry fewer than 7 digits, so they are checked in keys and string values
        and not in numbers, and what does protect a number (the closing delta's
        text, 2026-09-19: the first line advised listing more digits, which for a pointed value silenced the line and protected
        nothing); the same holds for the pointed 1234.56 (seven characters, six digits) listed on line 4 with pusher.cycle_ms_p50
        carrying it, the case the floor lets through by design, pinned green on purpose: the value travels and the line says so
        once; the same run as a KEY is refused as before, naming line 4, the loud line before the refusal. With the run
        lengthened to seven digits on the same line 4, a counter that spells it, as an integer, a float, a negative and an
        exponent spelling, and a byte total that carries it, is refused naming the kind, the value's path and line 4 of the
        list with the remedy, the run in no output, nothing written, and stderr is that one line, since no entry is under
        the floor. The boundary is by execution with literals: 424242 passes, 4242424 refuses. Fails before: the six-digit run
        refused the export, exit 1, and no refusal named a line."""
        listed = os.path.join(self.xdg, "private-strings.txt")
        loud = ("romp: 1 of 2 private-strings entries (list line 4) could match a number, by their spelling or by their digit groups, but carry fewer "
                "than 7 digits, so they are checked "
                "in keys and string values and not in numbers; a number is checked against a listed entry only when the entry, or the plain "
                "decimal spelling of an entry written with an exponent, carries 7 or more digits, and the match is against the number's own "
                "spelling: a listed 1234.5678 protects the number 1234.5678, a listed 12345678 does not, and a listed entry of fewer digits "
                "protects no number\n")
        self.assertEqual(loud, pp.LIST_UNDER_NUMERIC_FLOOR % (1, 2, pp.list_lines_phrase([4]), 7, 7) + "\n",
                         "the literal here is the module's line with its four numbers and the counted entry's list line")
        for entry, block, leaf, value, spelled in (("424242", "process", "rss_kb", 9424242, '"rss_kb": 9424242'),
                                                   ("1234.56", "pusher", "cycle_ms_p50", 1234.56, '"cycle_ms_p50": 1234.56')):
            with open(listed, "w", encoding="utf-8") as fh:
                fh.write("# strings that must never be published\nzzcoinedzz\n\n%s\n" % entry)
            snap = leak_snapshot()
            snap[block][leaf] = value
            with open(self.src, "w") as fh:
                json.dump(snap, fh)
            r = _run(["--public", "--from", self.src], env_extra={"ROMP_PRIVATE_STRINGS": listed}, state=self.state)
            self.assertEqual(r.returncode, 0, entry + "\n" + r.stdout + r.stderr)
            self.assertEqual(r.stderr, loud, entry)
            written = os.listdir(os.path.join(self.state, "perf-exports"))
            self.assertEqual(len(written), 1, entry)
            with open(os.path.join(self.state, "perf-exports", written[0]), encoding="utf-8") as fh:
                self.assertIn(spelled, fh.read(), "the number carrying the six-digit entry is written: %s" % entry)
            shutil.rmtree(os.path.join(self.state, "perf-exports"))
        with open(listed, "w", encoding="utf-8") as fh:
            fh.write("# strings that must never be published\nzzcoinedzz\n\n424242\n")
        snap = leak_snapshot()
        snap["pusher"]["connectPush"]["byApp"]["424242"] = {"count": 1}
        with open(self.src, "w") as fh:
            json.dump(snap, fh)
        r = _run(["--public", "--from", self.src], env_extra={"ROMP_PRIVATE_STRINGS": listed}, state=self.state)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertEqual(r.stderr, loud + "romp perf export: refused: a string this machine knows (private string) survives as a key under "
                                          "perf/pusher/connectPush/byApp; edit line 4 of the private-strings list or that key; nothing written\n")
        self.assertFalse(os.path.exists(os.path.join(self.state, "perf-exports")))
        with open(listed, "w", encoding="utf-8") as fh:
            fh.write("# strings that must never be published\nzzcoinedzz\n\n4242424\n")
        for plant, path in (({"pusher": {"cycles": 4242424}}, "perf/pusher/cycles"), ({"pusher": {"cycles": 4242424.0}}, "perf/pusher/cycles"),
                            ({"pusher": {"cycles": -4242424}}, "perf/pusher/cycles"), ({"pusher": {"cycles": 4.242424e6}}, "perf/pusher/cycles"),
                            ({"process": {"rss_kb": 94242424}}, "perf/process/rss_kb")):
            snap = leak_snapshot()
            for block, leaf in plant.items():
                snap[block].update(leaf)
            with open(self.src, "w") as fh:
                json.dump(snap, fh)
            r = _run(["--public", "--from", self.src], env_extra={"ROMP_PRIVATE_STRINGS": listed}, state=self.state)
            self.assertEqual(r.returncode, 1, repr(plant) + "\n" + r.stdout + r.stderr)
            self.assertEqual(r.stderr, "romp perf export: refused: a string this machine knows (private string) survives as the value at "
                                       "%s; edit line 4 of the private-strings list or that value; nothing written\n" % path, repr(plant))
            self.assertNotIn("4242424", r.stdout + r.stderr, repr(plant))
            self.assertFalse(os.path.exists(os.path.join(self.state, "perf-exports")), repr(plant))
        r = _run(["--public", "--from", self.src], state=self.state)
        self.assertEqual(r.returncode, 0, r.stderr + " (without the list, the counter is a number like any other)")

    def test_a_listed_entry_with_an_exponent_beyond_any_double_exports_under_a_finite_address_space_with_one_line_and_no_traceback(self):
        """The refusable input of the closing re-run (2026-09-19, finding 5) through the export child: ROMP_PRIVATE_STRINGS
        naming a list of 1e-1000000000, the entry whose plain decimal expansion asked for a billion digits and took the
        verb down with an uncaught MemoryError at b3df460d5 (rc 1, no file, a traceback ending in number_spellings' format
        call), while cd3b4cfab exported the same list with rc 0, and, on line 2, 1e-10000000000000000000, the entry whose
        exponent (10**19) the decimal module refuses to construct (past decimal.MAX_EMAX, about 1e18), which the first cut of
        the bound read bare and died on with an uncaught InvalidOperation out of expansion_bounded (the re-run's verification:
        rc 1 and a traceback from this verb, the upload and restart-metrics alike, on 3.10, 3.12, 3.13 and 3.14t). Now: rc 0,
        the file written, stdout the path and size line, and stderr EXACTLY the one skip line (pp.LIST_EXPANSION_SKIPPED: 2 of
        2, list lines 1 and 2, the bound 324), with Traceback, MemoryError and InvalidOperation in neither stream and neither
        entry's text in either. THE CHILD RUNS UNDER A FINITE ADDRESS-SPACE CAP
        (ADDRESS_SPACE_CAP, RLIMIT_AS of 1.5 GiB: the report's reproduction set 768 MiB with ulimit -v 786432, which the
        free-threaded 3.14t interpreter exceeds before any code runs, and 2 GiB lets the billion-digit expansion complete, so
        the cap is 1.5 GiB on every interpreter), so the refusable input fails fast under a bound, a MemoryError in under a
        second, rather than allocating without bound when the guard is removed. Dropping
        `and expansion_bounded(text)` from number_spellings' guard reds this with the MemoryError traceback under the cap; the
        try/except removed from expansion_bounded reds it with rc 1 and InvalidOperation in stderr."""
        listed = os.path.join(self.xdg, "private-strings.txt")
        with open(listed, "w", encoding="utf-8") as fh:
            fh.write("1e-1000000000\n1e-10000000000000000000\n")
        r = _run(["--public", "--from", self.src], env_extra={"ROMP_PRIVATE_STRINGS": listed}, state=self.state, address_space=ADDRESS_SPACE_CAP)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(r.stderr, pp.LIST_EXPANSION_SKIPPED % (2, 2, "list lines 1 and 2", 324) + "\n", "the skip line and nothing else")
        for word in ("Traceback", "MemoryError", "InvalidOperation", "1e-1000000000", "1e-10000000000000000000"):
            self.assertNotIn(word, r.stdout + r.stderr, word)
        m = re.match(r"^(\S+) \((\d+) bytes\)\n$", r.stdout)
        self.assertIsNotNone(m, r.stdout)
        self.assertEqual(os.path.dirname(m.group(1)), os.path.join(self.state, "perf-exports"))
        self.assertEqual(os.path.getsize(m.group(1)), int(m.group(2)), "the file is written")

    def test_a_listed_exponent_written_entry_refuses_the_export_when_its_plain_digits_sit_in_a_string_value_or_a_key(self):
        """The export road of the key and string fix (the closing re-run of 2026-09-19, finding 1): a list of 1.5e-05 alone and
        a snapshot carrying zzn: "0.000015" as a top-level string (IDENT admits it, so the fold keeps it and the walk passes
        it, and only the identifier scan can refuse) is refused, rc 1, stderr exactly the refusal naming the value at perf/zzn
        and line 1 of the list with the remedy, nothing written, nothing on stdout, the digits and the entry's text in no
        output; then the same digits as the KEY zz0.000015 with a count under it: refused naming a key under perf and line 1.
        Before the fix both exported with rc 0 (the report's executed table: the string and the key POSTed by the upload,
        which shares the check). Without the list both export. Scanning keys and strings by the entry's text alone reds both
        legs with rc 0."""
        listed = os.path.join(self.xdg, "private-strings.txt")
        with open(listed, "w", encoding="utf-8") as fh:
            fh.write("1.5e-05\n")
        for plant, spelled in (({"zzn": "0.000015"}, "the value at perf/zzn; edit line 1 of the private-strings list or that value"),
                               ({"zz0.000015": 1}, "a key under perf; edit line 1 of the private-strings list or that key")):
            snap = leak_snapshot()
            snap.update(plant)
            with open(self.src, "w") as fh:
                json.dump(snap, fh)
            r = _run(["--public", "--from", self.src], env_extra={"ROMP_PRIVATE_STRINGS": listed}, state=self.state)
            self.assertEqual(r.returncode, 1, repr(plant) + "\n" + r.stdout + r.stderr)
            self.assertEqual(r.stderr, "romp perf export: refused: a string this machine knows (private string) survives as %s; nothing written\n" % spelled,
                             repr(plant))
            self.assertEqual(r.stdout, "", repr(plant))
            for text in ("0.000015", "1.5e-05"):
                self.assertNotIn(text, r.stdout + r.stderr, repr(plant))
            self.assertFalse(os.path.exists(os.path.join(self.state, "perf-exports")), repr(plant))
            r = _run(["--public", "--from", self.src], state=self.state)
            self.assertEqual(r.returncode, 0, r.stderr + " (without the list, the digits are an identifier like any other)")
            shutil.rmtree(os.path.join(self.state, "perf-exports"))

    def test_a_fifo_at_the_private_strings_path_is_no_list_said_on_stderr_and_the_export_returns_at_once(self):
        """The private list must be a REGULAR file (pp.open_regular: opened O_NONBLOCK, fstat'ed, S_ISREG required); anything
        else is no list, [], AND IS SAID: one stderr line naming the path and what was there (pp.LIST_UNREADABLE, the
        fourth review round, 2026-09-19; until then the fifo disabled the whole list in silence and this case pinned the
        silence). A fifo at the path hung `romp perf export --public` and `romp restart-metrics --json --public`
        indefinitely: a plain open of a fifo blocks until a writer arrives, before any read the bound could cover (the
        upload's second review round, 2026-09-18). THE CHILD IS RUN UNDER A TIMEOUT AND HARD-KILLED WHEN IT EXPIRES, AND IT
        RUNS BEFORE THE UNIT CALL: the defect is a hang, so a plain wait, or the unit call first, would take the runner with
        it; subprocess.run kills the child on TimeoutExpired and the case fails instead. Do not simplify this back into
        _run's sixty-second wait or move the unit call above the child. Fails before: stderr was empty."""
        fifo = os.path.join(self.xdg, "private-strings.fifo")
        os.mkfifo(fifo)
        out = os.path.join(self.xdg, "public.json")
        env = {k: v for k, v in os.environ.items() if not k.startswith("ROMP_") and k not in ("CLAUDE_CODE_SESSION_ID", "XDG_CONFIG_HOME")}
        env.update({"XDG_STATE_HOME": self.xdg, "HOME": HOME, "USER": "tester", "LOGNAME": "tester", "ROMP_KERNEL_PORT": "1",
                    "ROMP_PRIVATE_STRINGS": fifo})
        try:
            r = subprocess.run([sys.executable, "-c", CHILD, EXPORT, "--public", "--from", self.src, "--out", out],
                               capture_output=True, text=True, timeout=8, env=env)
        except subprocess.TimeoutExpired:
            self.fail("the export child hung on the fifo at the private-strings path (killed after 8 s)")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(os.path.exists(out), "the export was written: a fifo adds no probe and blocks nothing")
        self.assertEqual(r.stderr, "romp: no private-strings list was read from %s (a fifo); no listed string is checked\n" % fifo,
                         "and the list turning itself off is said, naming the path and the reason")
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(pp.private_strings({"ROMP_PRIVATE_STRINGS": fifo}), [], "the unit, after the child proved the open returns: a fifo is no list")
        self.assertEqual(err.getvalue(), pp.LIST_UNREADABLE % (fifo, "a fifo") + "\n")
        self.assertIsNone(pp.open_regular(fifo))

    def test_every_road_to_no_list_but_the_derived_defaults_absence_is_said_on_stderr_naming_the_path_and_the_reason(self):
        """A private-strings path that EXISTS but yields no list (unreadable, a directory, a fifo, a device node, a socket)
        turned the WHOLE list off in silence, and the upload then sent a document carrying a listed string with nothing on
        stderr, while the two loud lines the third round added covered the over-the-bound case and a case the reader
        cannot produce (extra4-1, the upload's third review round, 2026-09-18). Now every road to [] but two writes
        pp.LIST_UNREADABLE once, the path and the reason: a directory, a fifo, a socket and a character device by kind, whether
        the fstat or the open itself found them (a socket is ENXIO at the open); an unreadable regular file and a parent that
        is not a directory by the error's class; a ROMP_PRIVATE_STRINGS that names
        a file that is not there as absent (the operator named it, so its absence is a typo, not a clone without a list); and
        a symbolic link whose target is gone, at the derived path or the named one, as a link whose target is absent (a list
        set up once and now pointing at nothing is the protection turning itself off, the fourth round's verifier: os.open
        follows the link and reports FileNotFoundError like a plain absence, so the derived road was silent until lstat told
        the two apart). The two silent roads: no path at all, and the DERIVED default PLAINLY absent, nothing at the path, the
        normal case of a clone that never set a list up, which stays silent so every export on such a clone does not nag. A
        readable list still reads with nothing said, and a line that is not UTF-8 is dropped and counted in pp.LIST_NOT_UTF8
        rather than replaced into a probe that matches nothing. Fails before: every one of these returned [] in silence, the
        dangling link at the derived path among them after the others were said."""
        home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, home, True)
        derived = os.path.join(home, ".config", "romp", "private-strings.txt")

        def read(env):
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                got = pp.private_strings(env)
            return got, err.getvalue()

        self.assertEqual(read({"HOME": home}), ([], ""), "the derived default plainly absent: a clone without a list, silent")
        self.assertEqual(read({}), ([], ""), "no path at all: silent")
        missing = os.path.join(home, "no-such-list.txt")
        self.assertEqual(read({"HOME": home, "ROMP_PRIVATE_STRINGS": missing}), ([], pp.LIST_UNREADABLE % (missing, "absent") + "\n"),
                         "a file the operator named and which is not there is said")
        os.makedirs(os.path.dirname(derived))
        os.symlink(os.path.join(home, "moved-away.txt"), derived)
        self.assertTrue(os.path.islink(derived) and not os.path.exists(derived))
        self.assertEqual(read({"HOME": home}), ([], pp.LIST_UNREADABLE % (derived, "a symbolic link whose target is absent") + "\n"),
                         "a dangling link at the DERIVED path is a list that was set up and points at nothing: said, where a plain absence is not")
        self.assertEqual(read({"HOME": home, "ROMP_PRIVATE_STRINGS": derived}),
                         ([], pp.LIST_UNREADABLE % (derived, "a symbolic link whose target is absent") + "\n"), "and the same link named by the operator")
        os.unlink(derived)
        os.rmdir(os.path.dirname(derived))
        for make, kind in ((os.mkdir, "a directory"), (os.mkfifo, "a fifo")):
            path = os.path.join(home, kind.split()[-1])
            make(path)
            self.assertEqual(read({"HOME": home, "ROMP_PRIVATE_STRINGS": path}), ([], pp.LIST_UNREADABLE % (path, kind) + "\n"), kind)
        sock_path = os.path.join(home, "sock")
        sock = socket.socket(socket.AF_UNIX)
        self.addCleanup(sock.close)
        sock.bind(sock_path)
        self.assertEqual(read({"HOME": home, "ROMP_PRIVATE_STRINGS": sock_path}), ([], pp.LIST_UNREADABLE % (sock_path, "a socket") + "\n"),
                         "a socket: the open itself fails with ENXIO, and the reason is the kind all the same")
        if os.path.exists("/dev/null"):
            self.assertEqual(read({"HOME": home, "ROMP_PRIVATE_STRINGS": "/dev/null"}), ([], pp.LIST_UNREADABLE % ("/dev/null", "a character device") + "\n"))
        os.makedirs(os.path.dirname(derived))
        with open(derived, "w", encoding="utf-8") as fh:
            fh.write("zzcoinedzz\n")
        self.assertEqual(read({"HOME": home}), (["zzcoinedzz"], ""), "a readable list at the derived path reads with nothing said")
        if os.geteuid() != 0:                    # root reads a mode-000 file, so the road does not exist for it
            os.chmod(derived, 0)
            self.assertEqual(read({"HOME": home}), ([], pp.LIST_UNREADABLE % (derived, "PermissionError") + "\n"),
                             "the derived path present and unreadable is said: only its absence is the normal case")
            os.chmod(derived, 0o600)
        with open(derived, "wb") as fh:
            fh.write(b"zzcoinedzz\n\xff\xfe\n\xc3\x28 # a truncated sequence\nabc\n")
        self.assertEqual(read({"HOME": home}), (["zzcoinedzz", "abc"], pp.LIST_NOT_UTF8 % (2, derived) + "\n"),
                         "two lines that are not UTF-8 are not entries and are counted once; the good lines stay in force")
        notdir = os.path.join(home, "file-as-parent")
        with open(notdir, "w") as fh:
            fh.write("x")
        inside = os.path.join(notdir, "list.txt")
        self.assertEqual(read({"HOME": home, "ROMP_PRIVATE_STRINGS": inside}), ([], pp.LIST_UNREADABLE % (inside, "NotADirectoryError") + "\n"),
                         "a parent that is a file: the open's own error, by class, never a claim that the path exists")
        for line in (pp.LIST_UNREADABLE % ("p", "r"), pp.LIST_NOT_UTF8 % (1, "p")):
            self.assertNotEqual(line, pp.LIST_OVER_BOUND)
            self.assertNotIn("not fully in force", line, "a third and a fourth loud line, distinct from the two the third round added")

    def test_a_name_probe_matches_whole_tokens_and_an_id_probe_matches_anywhere(self):
        # a hostname or a login is a word, and romp's own vocabulary contains common ones as substrings: a user named
        # mark, a machine named work or arch, must not refuse every export over intrMarks, cpu_ms_workers and archive
        names = [("username", "mark"), ("hostname", "work"), ("hostname", "arch"), ("hostname", "anchor"), ("username", "tester")]
        self.assertEqual(_hits({"memos": {"intrMarks": 1, "cpu_ms_workers": 2, "summaryAnchor": 4},
                                             "checkpoints": {"fallbacks": {"archive": 3}}, "goals": {"archive": 1}}, names), [])
        self.assertEqual(_hits({"a": {"summary-anchor": 1}}, names), [("hostname", "a key under a")], "a whole token, however joined")
        self.assertEqual(_hits({"a": {"b": "tester-app"}}, names), [("username", "the value at a/b")])
        self.assertEqual(_hits({"a": {"b": "app_Tester"}}, names), [("username", "the value at a/b")])
        self.assertEqual(_hits({"a": {"b": "testers"}}, names), [])
        two = [("hostname", "testhost.example")]
        self.assertEqual(_hits({"chat.testhost.example": 1}, two), [("hostname", "a key under the root")], "a dotted hostname is a run of tokens")
        self.assertEqual(_hits({"testhost": 1, "example": 1}, two), [], "the run must be contiguous")
        # an id or a directory is not a word: glued to letters it is still the id
        ids = [("session id", SID2[:8]), ("session directory", HOME + "/code/notes-api")]
        self.assertEqual(_hits({"a": "sid%sx" % SID2[:8]}, ids), [("session id", "the value at a")])
        self.assertEqual(_hits({"a": "in %s/code/notes-api/x" % HOME}, ids), [("session directory", "the value at a")])


class ServedKernel(unittest.TestCase):
    """The export over a kernel this module starts: the real Handler on a loopback port, the module-global
    collector planted through its own writers, the CLI reading GET /perf with the serve token."""

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
        self.xdg, self.state = _state_root()
        self.addCleanup(shutil.rmtree, self.xdg, True)
        self.home = os.path.join(tempfile.mkdtemp(), "home", "tester")
        self.addCleanup(shutil.rmtree, os.path.dirname(os.path.dirname(self.home)), True)
        self.leaf = os.path.join(self.home, ".claude", "projects", "-home-tester-code-notes-api", SID + ".jsonl")
        self.first = "OSError: [Errno 2] No such file or directory: '%s'" % self.leaf
        self.app = "<b>%s</b> %s" % (SID, self.home)
        self.planted = [SID, SID[:8], self.home, "TESTHOST", TERM, self.first, self.app, "-home-tester-code-notes-api"]
        st = km._PERF_STATS
        km.em._count_read(self.leaf, 4096)
        self.addCleanup(self._unplant)
        st.judge_child_done({"op": "done", "seq": 7, "wallMs": 12.5, "failures": {"count": 1, "first": self.first}, "recovered": False,
                             "recordCache": {"entries": 1, "wholeReads": {"leaf<-_parse": {"count": 1, "bytes": 5}}}}, pid=4242)
        st.build_chat(False, 0.100, active=True, sid=SID, nbytes=4096)
        st.parse(SID, 4096)
        for method, path in (("GET", "/glossary/" + TERM), ("GET", "/nope/" + SID), ("GET", "/remote/TESTHOST/sessions"),
                             ("GET", self.home), ("POST", "/send"), ("POST", "/new")):
            st.http_request(km._perf_http_key(method, path), 0.001)
        st.connect_push(self.app, 0.010)
        st.client_send(self.app, "Mozilla/5.0 " + self.home, 10, 0.001)
        st.stage(self.home + "/notes", 0.002)      # a stage key the kernel does not fold: the export's own rule must
        st.stage("push.chat", 0.010)

    def _unplant(self):
        with km.em._READ_BYTES_LOCK:
            km.em._READ_BYTES.pop(self.leaf, None)
        with km._PERF_STATS.lock:
            km._PERF_STATS.stages.pop(self.home + "/notes", None)

    def _export(self, *args, token=None):
        return _run(["--public"] + list(args), state=self.state,
                    env_extra={"ROMP_KERNEL_PORT": str(self.port), "ROMP_SERVE_TOKEN": token or km.TOKEN})

    # glibc's allocator figures as CI's Python 3.13 runner served them on 2026-09-18 (round 5 of the export's review): the
    # process block's perf/process/malloc/arena and uordblks passed 2.9e9 and 2.7e9 there while this module's kernel kept
    # them under 1.5e9 on the box that wrote the test, so the stamp property below is run over a served snapshot that
    # carries these figures, whatever the host's own allocator holds; the export keeps them, a measurement is not a stamp
    CI_MALLOC = {"arena": 2931437568, "hblkhd": 268435456, "uordblks": 2731423520, "fordblks": 200014048}

    def test_the_export_of_a_served_snapshot_is_paste_safe_and_keeps_the_diagnosis(self):
        with mock.patch.object(km, "_malloc_stats", return_value=dict(self.CI_MALLOC)):
            r = self._export("--usage")
        self.assertEqual(r.returncode, 0, r.stderr)
        m = re.match(r"^(\S+) \((\d+) bytes\)\n$", r.stdout)
        self.assertIsNotNone(m, r.stdout)
        path = m.group(1)
        self.assertRegex(os.path.basename(path), FILE_NAME)
        self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600)
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
        problems = pp.paste_problems(doc, planted=self.planted, skip=("schema",), under=("perf",))
        self.assertEqual(problems, [], _lines(problems))
        perf = doc["perf"]
        self.assertNotIn("stacks", perf)
        self.assertEqual(_keys_named(perf, "t"), [], "no split row's or child report's stamp survives")
        self.assertEqual(perf["uptime_s"] % 60, 0, perf["uptime_s"])
        # the stamp property over the served document: no numeric leaf inside an epoch window (EPOCH_WINDOWS) survives, the
        # one number allowed there a coarsened bound, a power of two; a number outside the windows, however large, is a
        # measurement (the planted allocator figures, this machine's byte bounds) and the export keeps it on purpose
        big = [(p, v) for p, v in _stamps(doc) if not (isinstance(v, int) and v & (v - 1) == 0)]
        self.assertEqual(big, [], "an absolute clock stamp survives the served export: a number inside an epoch window that is not a "
                                  "coarsened bound, a power of two (a large number OUTSIDE the windows, an allocator or byte figure, "
                                  "is a measurement the export keeps on purpose and is not listed here):\n  %s"
                                  % "\n  ".join("%s = %r" % s for s in big))
        for path in BOUND_PATHS:     # the register of memory-fraction bounds is the kernel's: each is served, and coarsened
            v = _at(perf, path)
            self.assertIsInstance(v, int, "/".join(path))
            self.assertTrue(v > 0 and v & (v - 1) == 0, "%s = %r is not a power of two" % ("/".join(path), v))
        self.assertEqual(perf["process"]["malloc"], self.CI_MALLOC, "the allocator figures are measurements the export keeps whole")
        self.assertNotIn("pid", perf["process"])
        self.assertNotIn("readByPath", perf["checkpoints"])
        self.assertIn("leaf", perf["checkpoints"]["readByKind"])
        self.assertEqual(perf["stages_ms"].get("other"), 2.0, "the planted stage key folded, its time kept: %s" % sorted(perf["stages_ms"]))
        self.assertGreaterEqual(perf["http"]["GET /glossary/*"]["count"], 1)
        self.assertGreaterEqual(perf["http"]["other"]["count"], 2)
        self.assertEqual((perf["judge"]["child"]["status"], perf["judge"]["child"]["failures"]), ("failed", 1))
        self.assertEqual(perf["parses"]["perSession"]["sessions"], 1)
        self.assertIn("other", perf["pusher"]["connectPush"]["byApp"])
        self.assertGreaterEqual(doc["usage"]["actions"]["send"], 1)
        self.assertGreaterEqual(doc["usage"]["sessions"]["parsed"], 1)
        # the envelope's commit is what the served kernel's own /version answers (git's short sha for the tree running
        # the suite, -dirty stripped), or absent when git did not answer; the next case pins the read with a known value
        sha = pe._commit_text(km._kernel_sha() or "")
        self.assertEqual(doc.get("kernel_commit"), sha[:12].lower() if sha else None)

    def test_the_kernels_commit_comes_from_get_version(self):
        # GET /perf has no commit key; the kernel's /version (auth-exempt) answers kernel_sha, git's short sha with
        # -dirty appended for a checkout with uncommitted edits. The verb reads it after /perf and the envelope carries
        # the abbreviation, the suffix stripped; without the read an export from a running kernel never named its
        # kernel (the review, 2026-09-18). _SHA is the kernel's resolved answer, pinned so the case does not depend on
        # what git says about the tree running the suite
        with mock.patch.object(km, "_SHA", "0123456789abcdef-dirty"):
            r = self._export()
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(r.stdout.split(" (")[0], encoding="utf-8") as fh:
            doc = json.load(fh)
        self.assertEqual(doc["kernel_commit"], "0123456789ab")
        self.assertNotIn("kernel_sha", doc["perf"])
        self.assertNotIn("0123456789abcdef", json.dumps(doc), "the whole sha is nowhere; the abbreviation alone")
        self.assertNotIn("-dirty", json.dumps(doc))
        self.assertIsNone(_check(doc))
        with mock.patch.object(km, "_SHA", "abc1234"):
            r = self._export()
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(r.stdout.split(" (")[0], encoding="utf-8") as fh:
            doc = json.load(fh)
        self.assertEqual(doc["kernel_commit"], "abc1234", "a short sha is carried whole")

    def test_a_refused_token_is_named_and_nothing_written(self):
        r = self._export(token="not-the-token")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("refused the serve token (HTTP 403)", r.stderr)
        self.assertNotIn("not reachable", r.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.state, "perf-exports")))


class PlainServer(unittest.TestCase):
    """The verb against a server that is not a kernel: the answer-shape refusals (a body that is not JSON, a JSON
    body that is not a GET /perf snapshot, an HTTP error), each one line with its exact wording, nothing of the
    served body on stderr, nothing written; and GET /version's failure modes, each leaving the export without a
    commit rather than failing it."""
    MARKER = "SERVED-BODY-MARKER-4242"

    @classmethod
    def setUpClass(cls):
        cls.answers = {}    # route -> (status, body)

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                status, body = cls.answers.get(self.path.split("?", 1)[0], (404, "no such route"))
                data = body if isinstance(body, bytes) else body.encode("utf-8")      # bytes pass through as they are
                self.send_response(status)
                self.send_header("Content-Type", "application/json" if data.startswith((b"{", b"[")) else "text/plain")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *a):
                pass
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def setUp(self):
        self.xdg, self.state = _state_root()
        self.addCleanup(shutil.rmtree, self.xdg, True)
        self.answers.clear()

    def _export(self, *args):
        return _run(["--public"] + list(args), state=self.state, env_extra={"ROMP_KERNEL_PORT": str(self.port), "ROMP_SERVE_TOKEN": "t"})

    def _refused(self, perf_answer, wording):
        self.answers["/perf"] = perf_answer
        r = self._export()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertEqual(r.stdout, "")
        self.assertEqual(r.stderr, "romp perf export: %s\n" % (wording % self.port), r.stderr)
        self.assertNotIn(self.MARKER, r.stderr, "the served body is not echoed")
        self.assertFalse(os.path.exists(os.path.join(self.state, "perf-exports")))

    def test_a_kernel_that_does_not_answer_json_is_refused_in_one_line(self):
        self._refused((200, "<html>%s</html>" % self.MARKER), "the kernel on :%d did not answer JSON on GET /perf")
        # bytes that are not UTF-8: the body is decoded where it is parsed, inside the same catch, so this is the
        # same one line and never a UnicodeDecodeError traceback naming the checkout (round 2)
        self._refused((200, b"\xff\xfe{" + self.MARKER.encode("utf-8") + b"\xff"), "the kernel on :%d did not answer JSON on GET /perf")

    def test_a_json_answer_that_is_not_a_snapshot_is_refused_naming_the_missing_blocks(self):
        self._refused((200, json.dumps({"name": self.MARKER, "uptime_s": 1, "process": {}})),
                      "the kernel's answer on :%d is not a GET /perf snapshot (no pusher, http)")
        self._refused((200, json.dumps([self.MARKER])), "the kernel's answer on :%d is not a JSON object (a `romp perf --json` snapshot)")

    def test_an_http_error_that_is_not_a_token_refusal_is_said_with_its_code(self):
        self._refused((500, self.MARKER), "the kernel on :%d answered HTTP 500")
        self._refused((404, self.MARKER), "the kernel on :%d answered HTTP 404")
        self._refused((401, self.MARKER), "the kernel on :%d refused the serve token (HTTP 401); is ROMP_KERNEL_PORT pointing at another kernel?")

    def _exported(self, version_answer):
        snap = leak_snapshot()
        del snap["kernel_sha"]
        self.answers["/perf"] = (200, json.dumps(snap))
        self.answers.pop("/version", None)
        if version_answer is not None:
            self.answers["/version"] = version_answer
        r = self._export()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stderr, "")
        with open(r.stdout.split(" (")[0], encoding="utf-8") as fh:
            return json.load(fh)

    def test_get_version_supplies_the_commit_and_its_failures_leave_the_export_without_one(self):
        self.assertEqual(self._exported((200, json.dumps({"kernel_sha": "0123456789abcdef-dirty", "pid": 4242})))["kernel_commit"],
                         "0123456789ab", "the suffix is stripped, the abbreviation is twelve characters")
        self.assertEqual(self._exported((200, json.dumps({"kernel_sha": "ABC1234"})))["kernel_commit"], "abc1234")
        for answer, why in ((None, "no route"), ((500, self.MARKER), "an error"), ((200, "<html>"), "not JSON"),
                            ((200, json.dumps(["x"])), "not an object"), ((200, json.dumps({"kernel_sha": "not a sha"})), "no hex sha"),
                            ((200, json.dumps({"kernel_sha": "-dirty"})), "the suffix alone"), ((200, json.dumps({"kernel_sha": 1234567})), "a number")):
            doc = self._exported(answer)
            self.assertNotIn("kernel_commit", doc, why)
            self.assertNotIn(self.MARKER, json.dumps(doc), why)
        self.assertIsNone(pe._commit_text("0123456789abcdef-dirty-dirty"), "one suffix, not two")
        self.assertEqual(pe._commit_text("0123456789abcdef-dirty"), "0123456789abcdef")


def _http(status, body):
    """A well-formed HTTP/1.1 answer as raw bytes, for RawServer."""
    return (b"HTTP/1.1 %d X\r\nContent-Type: application/json\r\nContent-Length: %d\r\nConnection: close\r\n\r\n"
            % (status, len(body))) + body


class RawServer(unittest.TestCase):
    """The verb against a loopback socket that answers raw bytes: the shapes BaseHTTPRequestHandler cannot emit (a
    status line that is not HTTP, a body shorter than its Content-Length, a header line past http.client's limit),
    each an http.client.HTTPException at the reader rather than a URLError or an OSError. On /version each leaves the
    export without a commit (exit 0, empty stderr); on /perf a status line that is not HTTP is the one-line
    not-reachable refusal, built from the port alone, so nothing the socket served reaches stderr (BadStatusLine's own
    text is the served line). Round 2: before it, each was a traceback naming the checkout's path."""
    MARKER = b"SERVED-LINE-MARKER-4242"

    @classmethod
    def setUpClass(cls):
        cls.answers = {}    # route -> raw bytes
        cls.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        cls.sock.bind(("127.0.0.1", 0))
        cls.sock.listen(8)
        cls.port = cls.sock.getsockname()[1]

        def serve():
            while True:
                try:
                    conn, _ = cls.sock.accept()
                except OSError:
                    return                         # the listening socket was closed: the class is done
                with conn:
                    conn.settimeout(5)
                    head = b""
                    try:
                        while b"\r\n\r\n" not in head:
                            chunk = conn.recv(4096)
                            if not chunk:
                                break
                            head += chunk
                        words = head.split(b"\r\n", 1)[0].split(b" ")
                        route = words[1].split(b"?", 1)[0].decode("latin-1") if len(words) > 1 else ""
                        conn.sendall(cls.answers.get(route, _http(404, b"no such route")))
                    except OSError:
                        continue
        cls.thread = threading.Thread(target=serve, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.sock.shutdown(socket.SHUT_RDWR)   # wakes the thread blocked in accept() (close alone does not, on Linux:
        except OSError:                           # the join waited its whole five seconds; round 3)
            pass
        cls.sock.close()
        cls.thread.join(5)
        assert not cls.thread.is_alive(), "the accept thread did not end"

    def setUp(self):
        self.xdg, self.state = _state_root()
        self.addCleanup(shutil.rmtree, self.xdg, True)
        self.answers.clear()
        snap = leak_snapshot()
        del snap["kernel_sha"]
        self.answers["/perf"] = _http(200, json.dumps(snap).encode("utf-8"))

    def _export(self):
        return _run(["--public"], state=self.state, env_extra={"ROMP_KERNEL_PORT": str(self.port), "ROMP_SERVE_TOKEN": "t"})

    def test_a_malformed_version_answer_leaves_the_export_without_a_commit(self):
        for raw, why in ((b"NOT HTTP " + self.MARKER + b"\r\n\r\n", "a status line that is not HTTP"),
                         (b"HTTP/1.1 200 X\r\nContent-Length: 500\r\n\r\n{\"kernel_sha\": \"", "a body shorter than its Content-Length"),
                         (b"HTTP/1.1 200 X\r\nX-Long: " + b"a" * 70000 + b"\r\n\r\n", "a header line past the reader's limit")):
            self.answers["/version"] = raw
            r = self._export()
            self.assertEqual(r.returncode, 0, why + "\n" + r.stderr)
            self.assertEqual(r.stderr, "", why)
            with open(r.stdout.split(" (")[0], encoding="utf-8") as fh:
                doc = json.load(fh)
            self.assertNotIn("kernel_commit", doc, why)
            self.assertEqual(doc["schema"], "romp-perf-export/1", why)
            self.assertNotIn(self.MARKER.decode("ascii"), json.dumps(doc) + r.stdout, why)

    def test_a_perf_answer_that_is_not_http_is_the_one_line_refusal_and_the_served_line_stays_off_stderr(self):
        self.answers["/perf"] = b"NOT HTTP " + self.MARKER + b"\r\n\r\n"
        r = self._export()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertEqual(r.stdout, "")
        self.assertEqual(r.stderr, "romp perf export: kernel not reachable on :%d (is romp running?)\n" % self.port)
        self.assertNotIn(self.MARKER.decode("ascii"), r.stderr, "the served line is not echoed")
        self.assertFalse(os.path.exists(os.path.join(self.state, "perf-exports")))


class RouteRegisterCopy(unittest.TestCase):
    """cli/perf_public.py's route register is a copy of the kernel's, held equal here."""

    def test_the_copy_equals_the_kernels_register(self):
        self.assertEqual({m: tuple(v) for m, v in pp.HTTP_ROUTES.items()}, {m: tuple(v) for m, v in km._PERF_HTTP_ROUTES.items()})
        self.assertEqual(pp.HTTP_FAMILIES, km._PERF_HTTP_FAMILIES)

    def test_every_key_the_kernel_can_produce_passes_and_nothing_else_does(self):
        for meth, routes in km._PERF_HTTP_ROUTES.items():
            for path in routes:
                self.assertTrue(pp.http_key_ok(km._perf_http_key(meth, path)), (meth, path))
                self.assertTrue(pp.http_key_ok(km._perf_http_key(meth, "/remote/TESTHOST" + path)), (meth, path))
        for fam in km._PERF_HTTP_FAMILIES:
            self.assertTrue(pp.http_key_ok("GET " + fam), fam)
        self.assertTrue(pp.http_key_ok("other"))
        for bad in ("GET /nope", "GET /remote/TESTHOST/sessions", "PUT /perf", "GET /glossary/" + TERM, "GET " + HOME,
                    "/perf", "GET", "", "GET /remote/*/nope", "HEAD /perf"):
            self.assertFalse(pp.http_key_ok(bad), bad)

    def test_the_membership_test_is_the_image_of_the_kernels_fold(self):
        # the set tests/test_perf_stats.py enumerates from the kernel's register (routes by method, the families per
        # method, the remote star form, other: 457 keys on the register of 2026-09-18) is exactly what http_key_ok
        # accepts, member by member, so the two walks hold the http block to one set
        image = {"other"}
        for method, routes in km._PERF_HTTP_ROUTES.items():
            image.update(method + " " + p for p in routes)
            image.update(method + " " + fam for fam in km._PERF_HTTP_FAMILIES)
            image.update(method + " /remote/*" + p for p in routes)
        self.assertGreaterEqual(len(image), 457, "the register shrank: %d keys" % len(image))
        self.assertEqual([k for k in sorted(image) if not pp.http_key_ok(k)], [])
        near = {k + "x" for k in image} | {k.replace(" /", " //") for k in image} | {k.lower() for k in image} | {"GET /remote/*//perf"}
        self.assertEqual([k for k in sorted(near - image) if pp.http_key_ok(k)], [], "a near miss is refused")

    def test_the_route_segment_rule_is_the_kernels_alone(self):
        """The kernel's _route_seg (the served-leak review, 2026-09-18) folds the stage mark a request handler carries to a
        segment the register holds a route under (_PERF_ROUTE_SEGMENTS), else `other`; the mark is served in the stack
        sample's `stage` values and in the joined `*ByStage` keys. The export needs no copy of that rule: the stack sample is
        dropped whole by the denylist, an http key never carries a route segment (it is the register's path through
        _perf_http_key, which http_public_key holds to the register), and a mark an OLDER kernel made from a requester's
        path in a `*ByStage` key names nothing the walk or the scan would not refuse (a session id is a uuid; this
        machine's host name is a probe)."""
        self.assertIn("stacks", pp.DENY_KEYS)
        self.assertFalse(hasattr(pp, "ROUTE_SEGMENTS"), "no segment register in the shared module, by decision")
        segs = {p.strip("/").split("/", 1)[0] for p in km._PERF_HTTP_ANY | set(km._PERF_HTTP_FAMILIES) if p.strip("/")}
        self.assertEqual(segs, km._PERF_ROUTE_SEGMENTS, "the kernel derives its segments from the register the copy mirrors")
        snap = {"uptime_s": 1, "process": {}, "pusher": {}, "http": {"GET /perf": {"count": 1}},
                "stacks": {"11 handler": {"self": False, "stage": "http.GET." + SID, "frames": []}},
                "recordCache": {"wholeReadsByStage": {"http.GET.%s:leaf<-_parse" % SID: {"count": 1, "bytes": 5},
                                                      "http.GET.other:leaf<-_parse": {"count": 1, "bytes": 5}}}}
        doc = pe.export_document(snap)
        self.assertNotIn("stacks", doc["perf"], "the old kernel's mark in the stack sample goes with the block")
        reason = _check(doc)
        self.assertIn("perf/recordCache/wholeReadsByStage", reason, "an old kernel's sid-bearing stage key: refused, not written")
        self.assertNotIn(SID, reason)
        del snap["recordCache"]["wholeReadsByStage"]["http.GET.%s:leaf<-_parse" % SID]
        self.assertIsNone(_check(pe.export_document(snap)), "the register's word passes")


if __name__ == "__main__":
    unittest.main()
