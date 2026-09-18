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
are set for the child), every id is a placeholder."""
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
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
        "process": {"rss_kb": 409600, "threads": 40, "cpu_s": 60.0, "pid": 4242, "source": "proc", "cwd": HOME},
        "pusher": {"cycles": 100, "cycle_ms_p50": 180.0, "idle_cycles": 40,
                   "connectPush": {"count": 4, "byApp": {"chat": {"count": 1}, APP: {"count": 2}, HOME: {"count": 1}}},
                   "clients": {"byApp": {"chat": {"frames": 3}, APP: {"frames": 1}}, "byKind": {"chrome": {"frames": 4}}}},
        "stages_ms": {"jobs": 5000.0, "push.chat": 15000.0, HOME + "/notes": 2.0, "push.chat.sig": float("nan")},
        "builds": {"chat": {"cached": 80, "built": 20, "ms": 800.0,
                            "bySession": [{"sid": SID, "n": 3, "max": 12.0, "first": 5.0, "last": 4.0},
                                          {"sid": SID2, "n": 1, "max": 3.0, "first": 3.0, "last": 3.0}]},
                   "feed": {"cached": 90, "built": 10, "ms": 5000.0}},
        "sends": {"full": {"chat": {"count": 10, "bytes": 1000000}}},
        "memos": {"chain": {"hit": 400, "miss": 40}},
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
        "checkpoints": {"restored": 2, "readBytes": 8192,
                        "readByPath": {HOME + "/.claude/projects/-home-tester-code-notes-api/%s.jsonl" % SID: 4096, HOME + "/notes/scratch.jsonl": 32},
                        "readByKind": {"leaf": {"files": 1, "bytes": 4096}, "other": {"files": 1, "bytes": 32}}},
        "recordCache": {"entries": 3, "wholeReads": {"leaf<-_parse": {"count": 2, "bytes": 10}},
                        "wholeReadsByStage": {"push:leaf<-_parse": {"count": 2, "bytes": 10}}},
        "asmIndex": {"materialized": 4, "materializedBy": {"<lambda>": 1, "build_session": 3}},
        "stacks": {"11 pusher": {"self": False, "stage": "jobs.autoNudge", "frames": ["_pusher (%s/kernel.py:100)" % HOME]}},
        "caches": {"session_stamp": {"entries": 31}, "jsonl": {"entries": 120}},
        "glossary": {"parses": 1, "termsBuilt": 40, "sample": TERM},
        "heap": {"tracing": False, "note": "a value longer than thirty-two characters is text"},
    }


def _run(args, env_extra=None, state=None):
    """bin/romp-perf-export as a child, hermetic: the suite's interpreter, a private state root, a synthetic
    HOME and USER, no live kernel port and no token unless the caller says so."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("ROMP_") and k != "CLAUDE_CODE_SESSION_ID"}
    state = state or tempfile.mkdtemp()
    env.update({"XDG_STATE_HOME": os.path.dirname(state) if os.path.basename(state) == "romp" else state,
                "HOME": HOME, "USER": "tester", "LOGNAME": "tester", "ROMP_KERNEL_PORT": "1"})
    env.update(env_extra or {})
    return subprocess.run([sys.executable, EXPORT] + list(args), capture_output=True, text=True, timeout=60, env=env)


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
        self.assertEqual(problems, [], "%d leak(s):\n  %s" % (len(problems), "\n  ".join(problems)))
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
                         "the pid and the working directory go; the gauges stay")
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
        self.assertEqual(self.perf["heap"], {"tracing": False, "note": "other"})

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
        self.assertEqual(pp.fold({"k" * 33: 1, "k" * 32: 2}), {"other": 1, "k" * 32: 2}, "the 32-character cap")
        self.assertEqual(pp.fold({"a:b": 1}), {"a:b": 1}, "the browser grammar keeps the colon")
        self.assertEqual(pp.fold({"sid": SID, "n": 1}), {"n": 1})
        self.assertEqual(pp.fold({"checkpoints": {"readByPath": {}, "restored": 1}}), {"checkpoints": {"restored": 1}})
        self.assertEqual(pp.fold({"x": {"readByPath": {"/a/b": 1}}}), {"x": {}}, "readByPath is dropped wherever it appears")

    def test_the_ident_grammar_is_the_browsers(self):
        src = open(os.path.join(ROOT, "ui", "webview", "perf-telemetry.ts"), encoding="utf-8").read()
        m = re.search(r"function ident\(s: unknown\): string \{[^}]*?/(\^[^/]+\$)/\.test", src, re.S)
        self.assertIsNotNone(m, "perf-telemetry.ts's ident() regex")
        self.assertEqual(pp.IDENT.pattern, m.group(1))

    def test_the_denylist_names_every_path_the_answer_lists(self):
        self.assertIn(("checkpoints", "readByPath"), pp.DENY_PATHS)
        self.assertIn(("judge", "child", "failures", "first"), pp.DENY_PATHS)
        for key in ("bySid", "byPath", "readByPath", "stacks", "pid", "sid", "name", "cutSessions", "scope", "label", "path", "cwd", "host", "hostname", "user"):
            self.assertIn(key, pp.DENY_KEYS, key)
        self.assertNotIn("first", pp.DENY_KEYS, "the chat rows' `first` timing is not an exception message")
        self.assertNotIn("t", pp.DENY_KEYS, "an event's stamp is the measurement")


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

    def test_a_dead_kernel_is_said_and_nothing_written(self):
        r = _run(["--public"], state=self.state, env_extra={"ROMP_KERNEL_PORT": "1"})
        self.assertEqual(r.returncode, 1)
        self.assertIn("kernel not reachable on :1", r.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.state, "perf-exports")))

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
        self.assertEqual(pp.identifier_hits({"a": {"TestHost": 1}, "schema": "testhost/1"}, probes, skip=("schema",)),
                         [("hostname", "a key under a")])
        self.assertEqual(pp.identifier_hits({"a": {"b": "x " + SID2[:8]}}, probes), [("session id", "the value at a/b")])
        self.assertEqual(pp.identifier_hits({"TESTHOST": 1}, probes), [("hostname", "a key under the root")])


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
        self.assertEqual(problems, [], "%d leak(s) in the export:\n  %s" % (len(problems), "\n  ".join(problems)))
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
        self.assertNotIn("kernel_commit", doc, "GET /perf carries no commit today")

    def test_a_refused_token_is_named_and_nothing_written(self):
        r = self._export(token="not-the-token")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("refused the serve token (HTTP 403)", r.stderr)
        self.assertNotIn("not reachable", r.stderr)
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


if __name__ == "__main__":
    unittest.main()
