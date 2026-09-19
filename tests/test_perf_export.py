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


def _run(args, env_extra=None, state=None):
    """bin/romp-perf-export as a child, hermetic: the suite's interpreter, a private state root, a synthetic
    HOME, USER and hostname (CHILD), no live kernel port and no token unless the caller says so."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("ROMP_") and k not in ("CLAUDE_CODE_SESSION_ID", "XDG_CONFIG_HOME")}
    state = state or tempfile.mkdtemp()      # no XDG_CONFIG_HOME: the child resolves the private list under its synthetic HOME, never this machine's
    env.update({"XDG_STATE_HOME": os.path.dirname(state) if os.path.basename(state) == "romp" else state,
                "HOME": HOME, "USER": "tester", "LOGNAME": "tester", "ROMP_KERNEL_PORT": "1"})
    env.update(env_extra or {})
    return subprocess.run([sys.executable, "-c", CHILD, EXPORT] + list(args), capture_output=True, text=True, timeout=60, env=env)


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
        run (4.242424242e9 is 4242424242.0), a listed float-shaped entry and its exponent respelling, a list element. A
        number whose canonical spelling does not carry the run is no hit (4242424242e-3 is 4242424.242, and a float that
        merely rounds near it), nor are a bool or null under a probe that spells them, nor any number under the machine's
        word and path probes (a hostname, a login, a home directory, a session id, a working directory spell letters,
        slashes or dashes a number never carries). Fails before: every numeric leaf was skipped."""
        listed = [(pp.PRIVATE_KIND, "4242424242"), (pp.PRIVATE_KIND, "1234567.8")]      # a float-shaped entry carries a seven-digit run: at the floor
        for value, where in ((4242424242, "a/n"), (4242424242.0, "a/n"), (4242424242.5, "a/n"), (-4242424242, "a/n"), (14242424242, "a/n"),
                             (0.4242424242, "a/n"), (4.242424242e9, "a/n"), (1234567.8, "a/n"), (12345678e-1, "a/n"), ([1, 4242424242], "a/n/1")):
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
        remedy is the same, editing the list. Fails before: exit 0, the file written with the run in it."""
        listed = os.path.join(self.xdg, "private-strings.txt")
        with open(listed, "w", encoding="utf-8") as fh:
            fh.write("4242424242\n")
        for value in (4242424242, 4242424242.0, 4.242424242e9):
            snap = leak_snapshot()
            snap["pusher"]["cycles"] = value
            with open(self.src, "w") as fh:
                json.dump(snap, fh)
            r = _run(["--public", "--from", self.src], env_extra={"ROMP_PRIVATE_STRINGS": listed}, state=self.state)
            self.assertEqual(r.returncode, 1, repr(value) + "\n" + r.stdout + r.stderr)
            self.assertEqual(r.stderr, "romp perf export: refused: a string this machine knows (private string) survives as the value at "
                                       "perf/pusher/cycles; edit line 1 of the private-strings list or that value; nothing written\n", repr(value))
            self.assertNotIn("4242424242", r.stdout + r.stderr, repr(value))
            self.assertFalse(os.path.exists(os.path.join(self.state, "perf-exports")), repr(value))
        r = _run(["--public", "--from", self.src], state=self.state)
        self.assertEqual(r.returncode, 0, r.stderr + " (without the list, the counter is a number like any other)")

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
