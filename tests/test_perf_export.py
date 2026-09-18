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
text as an app name, a thread stack, a path as a stage key, the pid and the clock stamps), the CLI run as a
subprocess over that snapshot (--from, --out, --usage, the refusals), and a kernel this module starts under
the suite's fixtures (the real Handler on a loopback port, the test_perf_stats.py PerfRoutes pattern) with the
same leaks planted through the collector's own writers. Nothing here reads a live kernel or a real state
directory: the state root is the suite's floor, the machine strings the scan learns are synthetic (HOME and USER
are set for the child, and socket.gethostname is pinned to TESTHOST.example in it; an in-process run of the verb or
of its check replaces machine_probes with SYNTHETIC_PROBES, so no real hostname, login or home is read by any test),
every id is a placeholder."""
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


def leak_snapshot():
    """A GET /perf snapshot in the shape of a kernel from BEFORE the served-leak fixes, so every leak the export
    must fold or drop is present at once; a few numbers ride beside them so the diagnosis they leave is checked."""
    return {
        "now": 1000.5, "since": 900.0, "uptime_s": 100.5, "log": True, "kernel_sha": SHA,
        "process": {"rss_kb": 409600, "threads": 40, "cpu_s": 60.0, "pid": 4242, "ppid": 4241, "managerPid": 4240, "source": "proc", "cwd": HOME},
        "pusher": {"cycles": 100, "cycle_ms_p50": 180.0, "idle_cycles": 40,
                   "connectPush": {"count": 4, "byApp": {"chat": {"count": 1}, APP: {"count": 2}, HOME: {"count": 1}}},
                   "clients": {"byApp": {"chat": {"frames": 3}, APP: {"frames": 1}}, "byKind": {"chrome": {"frames": 4}}}},
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
    env = {k: v for k, v in os.environ.items() if not k.startswith("ROMP_") and k != "CLAUDE_CODE_SESSION_ID"}
    state = state or tempfile.mkdtemp()
    env.update({"XDG_STATE_HOME": os.path.dirname(state) if os.path.basename(state) == "romp" else state,
                "HOME": HOME, "USER": "tester", "LOGNAME": "tester", "ROMP_KERNEL_PORT": "1"})
    env.update(env_extra or {})
    return subprocess.run([sys.executable, "-c", CHILD, EXPORT] + list(args), capture_output=True, text=True, timeout=60, env=env)


SYNTHETIC_PROBES = [("hostname", "testhost"), ("username", "tester"), ("home directory", HOME)]


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
        self.assertEqual(self.perf["uptime_s"], 100.5)

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
        self.assertEqual(hits, [("hostname", False, "a/" + token, 2), ("hostname", True, "a", 1), ("hostname", True, "", 0)])
        self.assertEqual([(h.kind, h.is_key, h.path, h.depth) for h in hits], hits)
        self.assertEqual([pp.place(h) for h in hits], ["the value at a/" + token, "a key under a", "a key under the root"])
        problems = pp.paste_problems({"a": {token: "x y"}, "GET /perf": {"c d": 1}})
        self.assertEqual([(p.kind, p.is_key, p.path, p.depth) for p in problems],
                         [("a 32-hex token", True, "a", 1), ("free text", False, "a/" + token, 2),
                          ("outside the identifier grammar", True, "", 0), ("outside the identifier grammar", True, "GET /perf", 1)],
                         "a key that contains the separator is one component, so the depth rides in its own field")

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
        for key in ("first", "t"):
            self.assertFalse(pp.denied(key, "text"), key)
        self.assertNotIn("first", pp.DENY_KEYS | pp.IDENTITY_KEYS, "the chat rows' `first` timing is not an exception message")
        self.assertNotIn("t", pp.DENY_KEYS | pp.IDENTITY_KEYS, "an event's stamp is the measurement")


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

    def test_the_export_of_a_served_snapshot_is_paste_safe_and_keeps_the_diagnosis(self):
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
        cls.sock.close()
        cls.thread.join(5)

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
