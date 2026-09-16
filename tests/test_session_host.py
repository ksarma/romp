#!/usr/bin/env python3
"""The per-session host (T315, stage 4 of the restart-surviving sessions program): the pure pieces
(frames, the journal, the parked table, the neutral hook answers) and the host as a real process driving
the fake CLI (tests/fixtures/fake_claude.py) while this test plays the kernel over the Unix socket.

Hermetic: a temp state root per test, the fake CLI on a temp path, no scopes (the host is a plain child
here), every process killed by the test, synthetic ids. The host runs on its built-in pipe transport when
the SDK is not importable (CI, the plain test venv); one test runs the SDK transport when the machine has
the SDK venv, and skips otherwise.
"""
import asyncio
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import types
import unittest
import uuid
from pathlib import Path
from unittest import mock
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()   # hermetic BEFORE the loads
os.environ.pop("ROMP_STATE_DIR", None)
sh = load_source("romp_session_host", os.path.join(ROOT, "kernel", "session_host.py"))
sb = load_source("romp_sdk_backend_host", os.path.join(BIN, "romp_sdk_backend.py"))
FAKE = os.path.join(HERE, "fixtures", "fake_claude.py")
SDK_SITE = next(iter(sorted(Path(os.path.expanduser("~/.local/state/romp/sdkvenv/lib")).glob(
    "python%d.%d/site-packages" % sys.version_info[:2]))), None) if os.path.isdir(os.path.expanduser("~/.local/state/romp/sdkvenv")) else None
SID = "11111111-2222-3333-4444-0000000000a1"          # the romp sid the lease is filed under
FSID = "11111111-2222-3333-4444-0000000000f1"         # the fake CLI's own conversation id (distinct on purpose)


class Frames(unittest.TestCase):
    def test_frames_round_trip_and_junk_is_dropped(self):
        fr = sh.FrameReader()
        a = sh.encode_frame({"t": "ping"}) + b"not json\n" + sh.encode_frame({"t": "in", "data": "x"})[:5]
        got = fr.feed(a)
        self.assertEqual(got, [{"t": "ping"}])
        got = fr.feed(sh.encode_frame({"t": "in", "data": "x"})[5:] + b"\n\n")
        self.assertEqual(got, [{"t": "in", "data": "x"}])


class SpawnSecrets(unittest.TestCase):
    """A key or login token lives in the process environment only, never in a file (the fork's rule, 2026-09-05):
    a stored login's CLAUDE_CODE_OAUTH_TOKEN leaves the spawn spec before hosts/<sid>/spawn.json is written and
    rides bin/romp-session-host's process environment instead (the pull-in review's item 1, 2026-09-16). Every
    assertion here is a presence check: no test output ever carries a token's value."""

    def setUp(self):
        self.state = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.state, True)
        self.tok = "synthetic-login-token-" + uuid.uuid4().hex

    def test_the_credential_names_leave_the_spec_env_and_are_returned_for_the_hosts_environment(self):
        spec = {"sid": SID, "env": {"ROMP_SID": SID, "CLAUDE_CODE_OAUTH_TOKEN": self.tok, "ANTHROPIC_AUTH_TOKEN": "synthetic-bearer"}}
        secrets = sb.split_spawn_secrets(spec)
        self.assertEqual(spec["env"], {"ROMP_SID": SID}, "every credential name is gone from the spec; the rest stays")
        self.assertEqual(sorted(secrets), ["ANTHROPIC_AUTH_TOKEN", "CLAUDE_CODE_OAUTH_TOKEN"])
        self.assertTrue(secrets["CLAUDE_CODE_OAUTH_TOKEN"] == self.tok, "the returned value is the login's token")
        for name in sb.AUTH_ENV_NAMES:
            self.assertNotIn(name, json.dumps(spec), "no credential name survives in the spec")
        self.assertEqual(sb.split_spawn_secrets({"sid": SID}), {}, "a spec with no env: nothing to move")
        plain = {"env": {"ROMP_SID": SID, "PATH": "/usr/bin"}}
        self.assertEqual(sb.split_spawn_secrets(plain), {})
        self.assertEqual(plain["env"], {"ROMP_SID": SID, "PATH": "/usr/bin"}, "a key-billed launch's overlay is untouched")

    def _spawn(self, cli_scope, secret_env, which=None):
        """_spawn_host with subprocess.Popen replaced: returns (argv, kwargs) of the one launch."""
        d = Path(self.state) / "hosts" / SID
        d.mkdir(parents=True, exist_ok=True)
        spec_path = d / "spawn.json"
        spec_path.write_text("{}")
        me = types.SimpleNamespace(cli_scope=cli_scope)
        sess = types.SimpleNamespace(sid=SID, name="web")
        seen = {}

        def fake_popen(argv, **kw):
            seen["argv"], seen["kw"] = list(argv), kw
            return types.SimpleNamespace(pid=4242, poll=lambda: None)
        with mock.patch.object(sb.subprocess, "Popen", fake_popen), \
             mock.patch.object(sb.shutil, "which", lambda name: which):
            sb.SdkBackend._spawn_host(me, sess, spec_path, secret_env)
        return seen["argv"], seen["kw"]

    def test_spawn_host_hands_the_token_to_the_host_through_its_environment_never_the_command_line(self):
        argv, kw = self._spawn(False, {"CLAUDE_CODE_OAUTH_TOKEN": self.tok})
        self.assertTrue(argv[1].endswith(os.path.join("bin", "romp-session-host")), "a plain child runs the launcher")
        self.assertIn("CLAUDE_CODE_OAUTH_TOKEN", kw["env"], "the token is in the host's environment")
        self.assertTrue(kw["env"]["CLAUDE_CODE_OAUTH_TOKEN"] == self.tok)
        self.assertIn("PATH", kw["env"], "the kernel's own environment is inherited beside it")
        self.assertFalse(any(self.tok in a for a in argv), "the token never rides the command line")
        self.assertTrue(kw.get("start_new_session") and kw.get("close_fds"), "the detached launch is unchanged")

    def test_a_scoped_launch_carries_the_environment_through_systemd_run(self):
        argv, kw = self._spawn(True, {"CLAUDE_CODE_OAUTH_TOKEN": self.tok}, which="/usr/bin/systemd-run")
        self.assertEqual(argv[0], "systemd-run")
        self.assertIn("--scope", argv, "a scope runs the command as systemd-run's own child, in its environment")
        self.assertIn("CLAUDE_CODE_OAUTH_TOKEN", kw["env"])
        self.assertFalse(any(self.tok in a for a in argv), "no --setenv, no value on the command line")

    def test_a_launch_with_no_secrets_hands_the_host_the_kernels_environment_and_no_bearer(self):
        with mock.patch.dict(os.environ, {"ROMP_TEST_MARKER": "1"}):
            for name in sb.AUTH_ENV_NAMES:
                os.environ.pop(name, None)
            argv, kw = self._spawn(False, None)
        self.assertEqual(kw["env"].get("ROMP_TEST_MARKER"), "1", "the kernel's environment, as a plain Popen inherited it")
        for name in sb.AUTH_ENV_NAMES:
            self.assertNotIn(name, kw["env"], "a key-billed launch's host gets no bearer to hand its CLI")

    def test_the_host_launch_writes_a_stored_login_spawn_json_without_the_token_and_hands_it_to_the_host(self):
        """The real _host_transport_for, on its spawn road, over a stub kernel: the login's token is in the options'
        env (the compose put it there, as for a kernel child), spawn.json on disk carries no credential name, and
        _spawn_host receives exactly the moved variables."""
        ht = sb._ht()
        handed = {}

        def spawn_host(sess, spec_path, secret_env=None):
            handed["secrets"] = dict(secret_env or {})
            handed["spec_path"] = Path(spec_path)
            ht.host_sock(self.state, SID).touch()                    # the launcher "served" its socket
            return types.SimpleNamespace(pid=4242, poll=lambda: None, returncode=None)
        me = types.SimpleNamespace(state_dir=self.state, code_version="abc12345", cli_scope=False,
                                   _host_recently_ended={}, _lock=__import__("threading").Lock(), _host_spawning=set(),
                                   _holder_ident=sb.SdkBackend._holder_ident, _spawn_host=spawn_host,
                                   _new_host_transport=lambda sess, sock, offset: ("transport", str(sock), offset),
                                   _log=lambda *a, **k: None)
        sess = types.SimpleNamespace(sid=SID, name="web", _options_login="login-rec-1", _host=None, _host_is_attach=False)
        opts = types.SimpleNamespace(cli_path="/x/romp-cli-scope", cwd=self.state,
                                     env={"ROMP_SID": SID, "CLAUDE_CODE_OAUTH_TOKEN": self.tok}, permission_mode="default")
        t = asyncio.run(sb.SdkBackend._host_transport_for(me, sess, opts, ()))
        self.assertEqual(t[0], "transport", "the spawn road handed back the new transport")
        written = json.loads(handed["spec_path"].read_text())
        self.assertEqual(handed["spec_path"], Path(self.state) / "hosts" / SID / "spawn.json")
        self.assertEqual(written["env"], {"ROMP_SID": SID}, "the file carries the overlay minus every credential name")
        self.assertEqual(written["login"], "login-rec-1", "the login IDENTIFIER stays in the file")
        self.assertNotIn(self.tok, handed["spec_path"].read_text(), "the token's value is nowhere in the file")
        self.assertEqual(sorted(handed["secrets"]), ["CLAUDE_CODE_OAUTH_TOKEN"], "the host gets the moved variable")
        self.assertTrue(handed["secrets"]["CLAUDE_CODE_OAUTH_TOKEN"] == self.tok)
        self.assertEqual(opts.env.get("CLAUDE_CODE_OAUTH_TOKEN"), self.tok, "the options object is untouched (spawn_spec copied)")


class JournalRules(unittest.TestCase):
    def test_offsets_are_ordinals_and_reads_start_anywhere(self):
        d = tempfile.mkdtemp(); j = sh.Journal(d)
        for i in range(5):
            self.assertEqual(j.append({"type": "assistant", "n": i}), i)
        self.assertEqual([o for o, _ in j.read_from(0)], [0, 1, 2, 3, 4])
        self.assertEqual([r["n"] for _, r in j.read_from(3)], [3, 4])
        self.assertEqual(list(j.read_from(5)), [])
        self.assertEqual([r["n"] for _, r in sh.read_journal_dir(d, 2)], [2, 3, 4], "the orphan reader agrees")

    def test_segments_rotate_at_a_turn_boundary_and_acked_ones_are_dropped(self):
        d = tempfile.mkdtemp(); j = sh.Journal(d, segment_bytes=200)
        for i in range(6):
            j.append({"type": "assistant", "pad": "x" * 60, "n": i})
        self.assertEqual(j.segments(), [0], "no rotation before a result record")
        j.append({"type": "result", "n": 6})
        self.assertEqual(j.segments(), [0, 7], "a result past the size starts a new segment, named by its first offset")
        self.assertTrue((Path(d) / "journal-7.jsonl").exists())
        for i in range(7, 10):
            j.append({"type": "assistant", "n": i})
        j.ack(6)                                    # everything in the first segment
        j.append({"type": "result", "n": 10})
        self.assertEqual(j.segments(), [7], "a fully acknowledged, non-current segment is deleted at the next boundary")
        self.assertEqual([r["n"] for _, r in j.read_from(7)], [7, 8, 9, 10], "the rest still reads")
        self.assertEqual([r["n"] for _, r in j.read_from(0)], [7, 8, 9, 10], "a read below the dropped segment skips it")
        # the ORPHAN reader numbers records from the surviving segment's first offset, not from zero (the
        # review's finding 1: an orphan replay after a deletion used to misnumber the very records it exists for)
        self.assertEqual([(o, r["n"]) for o, r in sh.read_journal_dir(d, 0)], [(7, 7), (8, 8), (9, 9), (10, 10)])
        self.assertEqual([o for o, _ in sh.read_journal_dir(d, 9)], [9, 10])

    def test_a_failed_raw_write_leaves_nothing_behind_and_the_numbering_holds(self):
        # the commit-5 review's finding a: a buffered handle kept a failed write's bytes and landed them later at a
        # stale position; the journal now writes unbuffered and truncates back to the last good position
        d = tempfile.mkdtemp(); j = sh.Journal(d)
        j.append({"type": "assistant", "n": 0})
        real = j._fh
        class Raw:
            def __init__(self): self.failed = False
            def write(self, b):
                if not self.failed:
                    self.failed = True
                    raise OSError(28, "no space left on device")
                return real.write(b)
            def fileno(self): return real.fileno()
            def seek(self, *a): return real.seek(*a)
            def tell(self): return real.tell()
            def close(self): return real.close()
        j._fh = Raw()
        size_before = os.path.getsize(j._path(0))
        with self.assertRaises(OSError):
            j.append({"type": "assistant", "n": 1})
        self.assertEqual((j.next_offset, len(j._index), os.path.getsize(j._path(0))), (1, 1, size_before), "nothing moved on the failure")
        j.append({"type": sh.GAP_TYPE, "offset": 1})          # the writer's gap marker takes offset 1
        j.append({"type": "assistant", "n": 2})
        self.assertEqual([(o, r["n"]) for o, r in j.read_from(0)], [(0, 0), (2, 2)], "the marker is skipped, the numbering holds")
        self.assertEqual([(o, r["n"]) for o, r in sh.read_journal_dir(d, 0)], [(0, 0), (2, 2)], "the orphan reader agrees")
        # finding b: a marker that fails too becomes a zero-length index entry; index and offsets stay in lockstep
        j.note_gap(3)
        j.append({"type": "result", "n": 4})
        self.assertEqual(j.next_offset, 5); self.assertEqual(len(j._index), 5)
        self.assertEqual([(o, r["n"]) for o, r in j.read_from(2)], [(2, 2), (4, 4)])
        self.assertEqual([(o, r["n"]) for o, r in j.read_from(3, 5)], [(4, 4)], "a replay spanning the hole reads past it")
        self.assertEqual([(o, r["n"]) for o, r in sh.read_journal_dir(d, 0)], [(0, 0), (2, 2), (4, 4)],
                         "the orphan reader, with no index, numbers past the unrecorded gap from gaps.json")

    def test_a_write_that_will_not_truncate_leaves_the_segment_behind_for_a_fresh_one(self):
        # the commit 6-7 review's item 11, untested until now: a partial write that ftruncate cannot undo makes the
        # segment's byte positions unreliable; a fresh segment starts at the failed offset and the numbering holds
        d = tempfile.mkdtemp(); j = sh.Journal(d)
        j.append({"type": "assistant", "n": 0})
        real = j._fh
        class Raw:
            def __init__(self): self.failed = False
            def write(self, b):
                if not self.failed:
                    self.failed = True
                    real.write(b[:5])                       # a partial line lands, then the disk is gone
                    raise OSError(28, "no space left on device")
                return real.write(b)
            def fileno(self): return real.fileno()
            def seek(self, *a): return real.seek(*a)
            def tell(self): return real.tell()
            def close(self): return real.close()
        j._fh = Raw()
        with mock.patch.object(sh.os, "ftruncate", side_effect=OSError(5, "input/output error")):
            with self.assertRaises(OSError):
                j.append({"type": "assistant", "n": 1})
        self.assertEqual(j._seg, 1, "a fresh segment, named by the failed offset")
        self.assertTrue(os.path.exists(j._path(1)))
        self.assertEqual(j.next_offset, 1, "nothing advanced")
        j.append({"type": sh.GAP_TYPE, "offset": 1})
        j.append({"type": "result", "n": 2})
        self.assertEqual([(o, r["n"]) for o, r in j.read_from(0)], [(0, 0), (2, 2)], "the old segment still serves record 0; the new one the rest")
        self.assertEqual([(o, r["n"]) for o, r in sh.read_journal_dir(d, 0)], [(0, 0), (2, 2)], "the orphan reader numbers across both")

    def test_the_gap_record_on_disk_survives_a_rewrite_that_fails(self):
        # item 2 (medium): gaps.json was rewritten in place; on the full disk that made the gap the truncation
        # succeeded and the write failed, erasing the record the orphan reader needs
        d = tempfile.mkdtemp(); j = sh.Journal(d)
        j.append({"type": "assistant", "n": 0})
        j.note_gap(1)
        self.assertEqual(json.loads(Path(d, "gaps.json").read_text()), [1])
        real_open = open
        class TruncatesThenFails:
            """the full disk's shape: the open (and its truncation) succeeds, the write does not"""
            def __init__(self, f): self.f = f
            def write(self, b): raise OSError(28, "no space left on device")
            def __enter__(self): return self
            def __exit__(self, *a): self.f.close(); return False
        def failing_open(p, *a, **kw):
            f = real_open(p, *a, **kw)
            return TruncatesThenFails(f) if (str(p).startswith(d) and "gaps" in str(p)) else f
        j.append({"type": "assistant", "n": 2})
        with mock.patch("builtins.open", failing_open):
            j.note_gap(3)                                   # the rewrite fails after its truncation; the previous record must stand
        self.assertEqual(json.loads(Path(d, "gaps.json").read_text()), [1], "the old record stands, not an empty file")
        self.assertEqual(sorted(p.name for p in Path(d).glob("gaps*")), ["gaps.json"], "no temp file left behind")
        j.append({"type": "result", "n": 4})
        self.assertEqual([(o, r["n"]) for o, r in j.read_from(0)], [(0, 0), (2, 2), (4, 4)])

    def test_a_replay_read_is_bounded_by_its_end(self):
        # finding 2: the replay covers the records that existed when the attach began; later ones follow from the
        # live backlog, so a drain that yields during the replay cannot send a record twice
        d = tempfile.mkdtemp(); j = sh.Journal(d)
        for i in range(5):
            j.append({"type": "assistant", "n": i})
        self.assertEqual([o for o, _ in j.read_from(0, 3)], [0, 1, 2])
        self.assertEqual([o for o, _ in j.read_from(2, 99)], [2, 3, 4], "an end past the journal reads to the end")
        self.assertEqual(list(j.read_from(3, 3)), [])


class ParkedRules(unittest.TestCase):
    def _req(self, rid, kind, event=None):
        req = {"subtype": kind}
        if kind == "hook_callback":
            req.update(callback_id="hook_0", input={"hook_event_name": event})
        return {"type": "control_request", "request_id": rid, "request": req}

    def test_park_cancel_answer_and_due_hooks(self):
        p = sh.Parked(self_answer_s=100)
        p.park(self._req("a", "can_use_tool"), 1, now=1000, attached=False)
        p.park(self._req("b", "hook_callback", "Stop"), 2, now=1000, attached=False)
        p.park(self._req("c", "hook_callback", "PostToolUse"), 3, now=1050, attached=False)
        self.assertEqual(p.ids(), ["a", "b", "c"])
        self.assertEqual([o for o, _ in p.records()], [1, 2, 3], "records in offset order, for the re-send on attach")
        self.assertEqual(p.due_hooks(1099), [])
        self.assertEqual(p.due_hooks(1100), ["b"], "a hook is due after the self-answer wait; a permission never is")
        self.assertEqual(p.due_hooks(1200), ["b", "c"])
        # a request delivered LIVE is tracked too (finding 4); its unattended clock starts only when the kernel leaves
        p.park(self._req("d", "hook_callback", "Stop"), 4, now=1000, attached=True)
        self.assertNotIn("d", p.due_hooks(5000), "attached: never self-answered")
        p.detached(now=5000)
        self.assertIn("d", p.due_hooks(5100), "unattended since the detach, due after the wait")
        p.attached()
        self.assertNotIn("d", p.due_hooks(9999), "a kernel is back: its answer is awaited")
        self.assertTrue(p.cancel("c")); self.assertFalse(p.cancel("c"))
        self.assertTrue(p.answer("b")); self.assertFalse(p.answer("b"), "a second answer is a late duplicate")
        self.assertEqual(p.ids(), ["a", "d"])
        self.assertEqual(sh.neutral_hook_response("b", "Stop"),
                         {"type": "control_response", "response": {"subtype": "success", "request_id": "b", "response": {}}})

    def test_every_hook_event_the_kernel_registers_has_a_neutral_answer(self):
        src = open(os.path.join(BIN, "romp_sdk_backend.py")).read()
        start = src.index("hooks={\"Stop\"")
        block = src[start:src.index('permission_mode=shape["mode"]', start)]
        events = set(__import__("re").findall(r'"([A-Z][A-Za-z]+)": \[HookMatcher', block))
        self.assertTrue(events, "the kernel's hook table was found")
        self.assertTrue(events <= set(sh.HOOK_NEUTRAL_OUTPUT), "missing neutral answers: %r" % (events - set(sh.HOOK_NEUTRAL_OUTPUT)))
        self.assertEqual(sh.LEASE_HEARTBEAT_S, sb.LEASE_HEARTBEAT_S, "the host beats at the stage 1 cadence")
        self.assertLess(sh.HOOK_SELF_ANSWER_S, sh.HOOK_TIMEOUT_S)
        self.assertLess(sh.HOOK_TIMEOUT_S, 600.0, "inside the CLI's default hook budget (the T303 probe)")


# ── the host as a process, this test as the kernel ─────────────────────────────────────────────
class KernelSide:
    """A tiny synchronous kernel stand-in over the host's socket."""

    def __init__(self, sock_path, timeout=10.0):
        self.s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.s.settimeout(timeout)
        self.s.connect(sock_path)
        self.fr = sh.FrameReader()
        self.frames = []

    def send(self, frame):
        self.s.sendall(sh.encode_frame(frame))

    def recv_until(self, pred, timeout=10.0):
        deadline = time.time() + timeout
        while time.time() < deadline:   # loop-ok: a bounded socket read
            for f in self.frames:
                if pred(f):
                    return f
            try:
                chunk = self.s.recv(65536)
            except socket.timeout:
                continue
            if not chunk:
                break
            self.frames.extend(self.fr.feed(chunk))
        for f in self.frames:
            if pred(f):
                return f
        raise AssertionError("no frame matched; got %r" % [f.get("t") for f in self.frames])

    def outs(self):
        return [f for f in self.frames if f.get("t") == "out"]

    def close(self):
        try:
            self.s.close()
        except OSError:
            pass


class HostProcess(unittest.TestCase):
    """Each test starts one host on the fake CLI in a private state root and kills everything after."""

    def setUp(self):
        self.state = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.state, True)
        self.fake_log = os.path.join(self.state, "fake-cli.log")
        self.tdir = os.path.join(self.state, "transcripts")

    def _spec(self, **over):
        d = Path(self.state) / "hosts" / SID
        d.mkdir(parents=True, mode=0o700)
        spec = {"sid": SID, "name": "web", "version": "abc12345", "state_dir": self.state, "protocol": 1,
                "cli_path": FAKE, "cwd": self.state, "permission_prompt_tool_name": "stdio", "permission_mode": "default",
                "env": {"FAKE_CLI_LOG": self.fake_log, "FAKE_CLI_TRANSCRIPT_DIR": self.tdir, "FAKE_CLI_SESSION_ID": FSID,
                        "ROMP_CANARY_SECRET": "canary-" + uuid.uuid4().hex},
                "max_buffer_size": 1024 * 1024, "hook_self_answer_s": 2, "unattached_grace_s": 3600}
        spec.update(over)
        p = d / "spawn.json"
        p.write_text(json.dumps(spec)); p.chmod(0o600)
        return str(p), spec

    def _start(self, sdk=False, host_env=None, **over):
        spec_path, spec = self._spec(**over)
        env = dict(os.environ, PYTHONUNBUFFERED="1")
        env.pop("ROMP_SDK_SITE", None)
        for name in sb.AUTH_ENV_NAMES:          # the host's environment carries a credential only when a test hands one
            env.pop(name, None)
        env.update(host_env or {})
        if sdk:
            env["ROMP_SDK_SITE"] = str(SDK_SITE)
        else:
            env["ROMP_SDK_SITE"] = os.path.join(self.state, "no-sdk-here")
        host = subprocess.Popen([sys.executable, os.path.join(BIN, "romp-session-host"), spec_path],
                                stdout=subprocess.DEVNULL, stderr=open(os.path.join(self.state, "host.stderr"), "w"), env=env,
                                start_new_session=True)
        self.addCleanup(self._kill_group, host)
        sock = Path(self.state) / "hosts" / (SID[:8] + ".sock")
        deadline = time.time() + 15
        while time.time() < deadline and not (sock.exists() and self._lease()):   # loop-ok: a bounded wait on two events
            if host.poll() is not None:
                break
            time.sleep(0.05)
        self.assertIsNone(host.poll(), "the host is running: " + open(os.path.join(self.state, "host.stderr")).read()[-800:])
        self.assertTrue(sock.exists(), "the socket exists")
        self.assertTrue(self._lease(), "the lease is written once the CLI has a pid")
        return host, str(sock), spec

    @staticmethod
    def _kill_group(proc):
        if proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.wait(timeout=10)

    def _lease(self):
        return sb.read_lease(self.state, SID)

    def _hostlog(self):
        p = Path(self.state) / "hosts" / SID / "host.log"
        return [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []

    def _attach(self, sock, ack=-1, pid=4242):
        k = KernelSide(sock)
        k.send({"t": "attach", "kernel": {"pid": pid, "start": "1", "version": "abc12345"}, "ack": ack})
        hello = k.recv_until(lambda f: f.get("t") == "hello")
        return k, hello

    def _user(self, text):
        return json.dumps({"type": "user", "message": {"role": "user", "content": text}})

    def test_the_lease_and_the_hello_carry_the_clis_spawn_time_once_and_the_specs_login(self):
        """The host is the authority for when ITS CLI spawned: the lease's spawnedAt is stamped once at the spawn and stands
        across the beats (before 2026-09-14 every beat rewrote it with the beat's time, so a kernel copying it would have
        moved the CLI's epoch at every attach), the hello's cli carries the same value, and cli.login echoes the spec's login
        identifier, so the kernel that first sees the CLI stamps its epoch and the login its launch billed."""
        host, sock, spec = self._start(login="login-rec-1")
        lease = self._lease()
        self.assertIsInstance(lease.get("spawnedAt"), int)
        k, hello = self._attach(sock)
        self.assertEqual((hello["cli"]["spawnedAt"], hello["cli"]["login"], hello["cli"]["pid"]),
                         (lease["spawnedAt"], "login-rec-1", lease["pid"]))
        deadline = time.time() + 3 * sh.LEASE_HEARTBEAT_S
        while time.time() < deadline and self._lease().get("t") == lease["t"]:   # loop-ok: a bounded wait on the next beat
            time.sleep(0.1)
        later = self._lease()
        self.assertNotEqual(later["t"], lease["t"], "a beat rewrote the lease")
        self.assertEqual(later["spawnedAt"], lease["spawnedAt"], "the spawn time stands across the beat")

    def test_a_turn_flows_through_the_host_and_is_journaled_under_a_host_held_lease(self):
        host, sock, spec = self._start()
        lease = self._lease()
        self.assertEqual((lease["holder"]["pid"], lease["holder"]["kind"], lease["version"]), (host.pid, "host", "abc12345"))
        self.assertEqual(sb.lease_state(lease, time.time()), "valid")
        k, hello = self._attach(sock)
        self.assertEqual((hello["cli"]["pid"], hello["journal"]["next"], hello["parked"], hello["inflight"]), (lease["pid"], 0, [], 0))
        k.send({"t": "in", "data": json.dumps({"type": "control_request", "request_id": "req_0_aaaa",
                                                 "request": {"subtype": "initialize", "hooks": {"Stop": [{"matcher": None, "hookCallbackIds": ["hook_0"], "timeout": 540}]}}})})
        resp = k.recv_until(lambda f: f.get("t") == "out" and f["data"].get("type") == "control_response")
        self.assertEqual(resp["data"]["response"]["request_id"], "req_0_aaaa")
        k.send({"t": "in", "data": self._user("hello sleep=0.3")})
        res = k.recv_until(lambda f: f.get("t") == "out" and f["data"].get("type") == "result")
        offsets = [f["offset"] for f in k.outs()]
        self.assertEqual(offsets, list(range(len(offsets))), "offsets are ordinals from zero")
        kinds = [f["data"]["type"] for f in k.outs()]
        self.assertEqual(kinds, ["control_response", "system", "assistant", "result"])
        journal = list(sh.read_journal_dir(os.path.join(self.state, "hosts", SID)))
        self.assertEqual([r["type"] for _, r in journal], kinds, "the journal holds every record the CLI emitted")
        self.assertEqual(self._lease()["fsid"], FSID, "the lease's conversation id follows the init (it started as the romp sid)")
        k.send({"t": "ack", "offset": res["offset"]})
        # secrets: the canary environment value appears nowhere the host writes or sends
        canary = spec["env"]["ROMP_CANARY_SECRET"]
        blob = json.dumps(self._hostlog()) + json.dumps([r for _, r in journal]) + json.dumps(k.frames)
        self.assertNotIn(canary, blob, "no environment value in host.log, the journal or a frame")
        self.assertNotIn("FAKE_CLI_LOG", json.dumps(self._hostlog()), "no spec content in host.log")
        k.close()

    def test_a_detached_kernel_reattaches_and_replays_from_its_ack_while_the_turn_kept_running(self):
        host, sock, spec = self._start()
        k, _ = self._attach(sock)
        k.send({"t": "in", "data": self._user("long sleep=2.5")})
        first = k.recv_until(lambda f: f.get("t") == "out" and f["data"].get("type") == "assistant")
        k.send({"t": "ack", "offset": first["offset"]})
        k.send({"t": "detach"}); k.close()
        time.sleep(0.5)
        self.assertIsNone(host.poll(), "the host keeps running the turn")
        self.assertEqual(sb.lease_state(self._lease(), time.time()), "valid", "and keeps the lease")
        k2, hello = self._attach(sock, ack=first["offset"], pid=4343)
        self.assertEqual(hello["inflight"], 1, "the host reports the open turn, so the new kernel knows it is mid-turn")
        res = k2.recv_until(lambda f: f.get("t") == "out" and f["data"].get("type") == "result", timeout=10)
        offs = [f["offset"] for f in k2.outs()]
        self.assertEqual(offs[0], first["offset"] + 1, "replay starts after the acknowledged offset")
        self.assertEqual(offs, list(range(offs[0], offs[0] + len(offs))), "replay then live, in order, no gap")
        self.assertEqual(res["data"]["result"], "done", "the turn the first kernel started finished under the second")
        log_kinds = [r["kind"] for r in self._hostlog()]
        self.assertIn("detached", log_kinds); self.assertEqual(log_kinds.count("attached"), 2)
        k2.close()

    def test_a_permission_request_parks_while_unattached_and_the_late_answer_reaches_the_cli(self):
        host, sock, spec = self._start()
        k, _ = self._attach(sock)
        k.send({"t": "in", "data": self._user("please ask=permission after=0.6 sleep=0.2")})
        k.recv_until(lambda f: f.get("t") == "out" and f["data"].get("type") == "assistant")
        k.send({"t": "detach"}); k.close()
        deadline = time.time() + 10
        while time.time() < deadline and not any(r["kind"] == "request-open" for r in self._hostlog()):   # loop-ok
            time.sleep(0.05)
        opened = [r for r in self._hostlog() if r["kind"] == "request-open"]
        self.assertEqual([r["attached"] for r in opened], [False], "the request opened while no kernel was attached")
        k2, hello = self._attach(sock, ack=-1)
        self.assertEqual(len(hello["parked"]), 1, "the parked request is named on attach")
        rid = hello["parked"][0]
        req = k2.recv_until(lambda f: f.get("t") == "out" and f["data"].get("type") == "control_request")
        self.assertEqual(req["data"]["request_id"], rid)
        k2.send({"t": "in", "data": json.dumps({"type": "control_response", "response": {"subtype": "success", "request_id": rid,
                                                                                            "response": {"behavior": "allow", "updatedInput": {}}}})})
        res = k2.recv_until(lambda f: f.get("t") == "out" and f["data"].get("type") == "result")
        texts = [c["text"] for f in k2.outs() if f["data"].get("type") == "assistant" for c in f["data"]["message"]["content"]]
        self.assertIn("permission answered", texts, "the late answer reached the CLI and the turn went on")
        # a second answer for the same id is a late duplicate the host drops
        k2.send({"t": "in", "data": json.dumps({"type": "control_response", "response": {"subtype": "success", "request_id": rid, "response": {}}})})
        k2.send({"t": "ping"}); k2.recv_until(lambda f: f.get("t") == "pong")
        self.assertIn("late-answer-dropped", [r["kind"] for r in self._hostlog()])
        k2.close()

    def test_a_parked_hook_is_answered_by_the_host_at_the_deadline_and_said_loudly(self):
        host, sock, spec = self._start(hook_self_answer_s=1)
        k, _ = self._attach(sock)
        k.send({"t": "in", "data": json.dumps({"type": "control_request", "request_id": "req_0_bbbb",
                                                 "request": {"subtype": "initialize", "hooks": {"Stop": [{"matcher": None, "hookCallbackIds": ["hook_3"], "timeout": 540}]}}})})
        k.recv_until(lambda f: f.get("t") == "out" and f["data"].get("type") == "control_response")
        k.send({"t": "in", "data": self._user("go hook=Stop after=0.6 sleep=0.1")})
        k.recv_until(lambda f: f.get("t") == "out" and f["data"].get("type") == "assistant")
        k.send({"t": "detach"}); k.close()
        deadline = time.time() + 10
        while time.time() < deadline and not any(r["kind"] == "hook-self-answered" for r in self._hostlog()):   # loop-ok
            time.sleep(0.1)
        rows = [r for r in self._hostlog() if r["kind"] == "hook-self-answered"]
        self.assertEqual(len(rows), 1, "the host answered the parked hook itself once")
        self.assertEqual((rows[0]["event"], rows[0]["callbackId"]), ("Stop", "hook_3"))
        self.assertGreaterEqual(rows[0]["parkedS"], 1.0)
        k2, hello = self._attach(sock)
        self.assertEqual(hello["parked"], [], "nothing left parked")
        k2.recv_until(lambda f: f.get("t") == "out" and f["data"].get("type") == "result")
        texts = [c["text"] for f in k2.outs() if f["data"].get("type") == "assistant" for c in f["data"]["message"]["content"]]
        self.assertIn("hook answered", texts, "the CLI took the neutral answer and went on")
        k2.close()

    def test_a_cancel_from_the_cli_drops_the_parked_request(self):
        host, sock, spec = self._start()
        k, _ = self._attach(sock)
        k.send({"t": "in", "data": self._user("go ask=permission after=0.6 cancel-after=0.5 sleep=0.1")})
        k.recv_until(lambda f: f.get("t") == "out" and f["data"].get("type") == "assistant")
        k.send({"t": "detach"}); k.close()
        deadline = time.time() + 10
        while time.time() < deadline and not any(r["kind"] == "request-cancelled" for r in self._hostlog()):   # loop-ok
            time.sleep(0.1)
        self.assertIn("request-cancelled", [r["kind"] for r in self._hostlog()])
        k2, hello = self._attach(sock)
        self.assertEqual(hello["parked"], [])
        k2.close()

    def test_end_closes_stdin_and_the_cli_exits_then_the_lease_goes(self):
        host, sock, spec = self._start()
        k, hello = self._attach(sock)
        k.send({"t": "in", "data": self._user("hi sleep=0.1")})
        k.recv_until(lambda f: f.get("t") == "out" and f["data"].get("type") == "result")
        k.send({"t": "end", "grace": 30})
        ex = k.recv_until(lambda f: f.get("t") == "exit")
        self.assertEqual((ex["cause"], ex["code"]), ("end", 0))
        host.wait(timeout=10)
        self.assertEqual(host.returncode, 0)
        self.assertIsNone(self._lease(), "the lease is removed when the host leaves")
        self.assertFalse(os.path.exists(sock), "the socket is removed")
        k.close()

    def test_end_with_a_short_grace_forces_a_cli_that_will_not_leave(self):
        host, sock, spec = self._start()
        k, hello = self._attach(sock)
        k.send({"t": "in", "data": self._user("slow sleep=30")})
        k.recv_until(lambda f: f.get("t") == "out" and f["data"].get("type") == "assistant")
        k.send({"t": "end", "grace": 1})
        ex = k.recv_until(lambda f: f.get("t") == "exit", timeout=15)
        self.assertEqual(ex["cause"], "end-forced")
        self.assertIn("end-forced", [r["kind"] for r in self._hostlog()])
        host.wait(timeout=10)
        k.close()

    def test_signal_reaches_the_cli_and_a_second_kernel_is_told_busy(self):
        host, sock, spec = self._start()
        k, hello = self._attach(sock)
        k.send({"t": "in", "data": self._user("slow sleep=30")})
        k.recv_until(lambda f: f.get("t") == "out" and f["data"].get("type") == "assistant")
        other = KernelSide(sock)
        other.send({"t": "attach", "kernel": {"pid": 9, "start": "1", "version": ""}, "ack": -1})
        self.assertEqual(other.recv_until(lambda f: f.get("t") == "busy")["kernel"]["pid"], 4242)
        other.close()
        k.send({"t": "signal", "sig": "INT"})
        res = k.recv_until(lambda f: f.get("t") == "out" and f["data"].get("type") == "result", timeout=10)
        self.assertEqual(res["data"]["result"], "interrupted")
        k.close()

    def test_an_unattached_idle_cli_is_ended_after_the_grace(self):
        host, sock, spec = self._start(unattached_grace_s=1)
        k, hello = self._attach(sock)
        k.send({"t": "in", "data": self._user("hi sleep=0.1")})
        k.recv_until(lambda f: f.get("t") == "out" and f["data"].get("type") == "result")
        k.send({"t": "detach"}); k.close()
        host.wait(timeout=15)
        kinds = [r["kind"] for r in self._hostlog()]
        self.assertIn("unattached-grace-expired", kinds)
        self.assertEqual(kinds[-1], "host-exited")
        self.assertIsNone(self._lease())

    def test_socket_loss_without_detach_is_a_kernel_death_the_host_survives(self):
        host, sock, spec = self._start()
        k, hello = self._attach(sock)
        k.send({"t": "in", "data": self._user("long sleep=2")})
        k.recv_until(lambda f: f.get("t") == "out" and f["data"].get("type") == "assistant")
        k.close()                                   # no detach: the kernel died
        time.sleep(0.5)
        self.assertIsNone(host.poll())
        self.assertIn("kernel-lost", [r["kind"] for r in self._hostlog()])
        k2, hello = self._attach(sock)
        res = k2.recv_until(lambda f: f.get("t") == "out" and f["data"].get("type") == "result", timeout=10)
        self.assertEqual(res["data"]["result"], "done")
        k2.close()

    def test_a_request_delivered_live_to_a_kernel_that_dies_is_still_open_and_re_sent_on_attach(self):
        # finding 4: the kernel RECEIVED the permission request (and acknowledged past it) but died before the
        # user answered; the next kernel must see the request again or the CLI hangs on it forever
        host, sock, spec = self._start()
        k, _ = self._attach(sock)
        k.send({"t": "in", "data": self._user("please ask=permission after=0.3 sleep=0.2")})
        req = k.recv_until(lambda f: f.get("t") == "out" and f["data"].get("type") == "control_request")
        k.send({"t": "ack", "offset": req["offset"]}); k.send({"t": "ping"}); k.recv_until(lambda f: f.get("t") == "pong")
        k.close()                                       # the kernel dies with the request unanswered
        k2, hello = self._attach(sock, ack=req["offset"], pid=4343)
        self.assertEqual(hello["parked"], [req["data"]["request_id"]], "still open, named on attach")
        again = k2.recv_until(lambda f: f.get("t") == "out" and f["data"].get("type") == "control_request")
        self.assertEqual(again["offset"], req["offset"], "re-sent with its original offset although acknowledged")
        rid = req["data"]["request_id"]
        k2.send({"t": "in", "data": json.dumps({"type": "control_response", "response": {"subtype": "success", "request_id": rid,
                                                                                            "response": {"behavior": "allow", "updatedInput": {}}}})})
        k2.recv_until(lambda f: f.get("t") == "out" and f["data"].get("type") == "result")
        texts = [c["text"] for f in k2.outs() if f["data"].get("type") == "assistant" for c in f["data"]["message"]["content"]]
        self.assertIn("permission answered", texts)
        k2.close()

    def test_a_journal_write_fault_is_a_fault_frame_not_the_clis_death(self):
        # finding 3: a failed journal write used to end the read loop and be reported as the CLI dying
        host, sock, spec = self._start(_test_journal_fault_at=1)
        k, _ = self._attach(sock)
        k.send({"t": "in", "data": self._user("hi sleep=0.2")})
        res = k.recv_until(lambda f: f.get("t") == "out" and f["data"].get("type") == "result")
        faults = [f for f in k.frames if f.get("t") == "fault"]
        self.assertEqual([f["kind"] for f in faults], ["journal-write-failed"])
        self.assertIsNone(host.poll(), "the host and its CLI are still running")
        kinds = [r["kind"] for r in self._hostlog()]
        self.assertIn("journal-write-failed", kinds); self.assertNotIn("cli-exited", kinds)
        # live delivery was complete (the kernel got every record) even though offset 1 is missing from the journal
        self.assertEqual([f["offset"] for f in k.outs()], list(range(len(k.outs()))))
        offs = [o for o, _ in sh.read_journal_dir(os.path.join(self.state, "hosts", SID))]
        self.assertNotIn(1, offs, "the failed record is a gap the readers skip")
        self.assertEqual(offs, [o for o in range(len(k.outs())) if o != 1], "the numbering around the gap holds")
        k.send({"t": "end", "grace": 10})
        ex = k.recv_until(lambda f: f.get("t") == "exit")
        self.assertEqual(ex["cause"], "end")
        k.close()

    def test_a_slow_journal_writer_raises_the_reader_behind_fault_and_the_reader_keeps_reading(self):
        # finding 5: the check used to be dead (the write ran on the reader's path); with the writer on its own
        # task, a throttled writer lets the reader run ahead and the fault fires once
        host, sock, spec = self._start(_test_journal_delay_s=0.4, reader_behind_records=1)
        k, _ = self._attach(sock)
        k.send({"t": "in", "data": self._user("one sleep=0.1")})
        k.send({"t": "in", "data": self._user("two sleep=0.1")})
        fault = k.recv_until(lambda f: f.get("t") == "fault" and f.get("kind") == "reader-behind", timeout=15)
        self.assertTrue(fault)
        first = k.recv_until(lambda f: f.get("t") == "out" and f["data"].get("type") == "result", timeout=15)
        k.recv_until(lambda f: f.get("t") == "out" and f["data"].get("type") == "result" and f is not first, timeout=15)
        self.assertEqual(sum(1 for f in k.outs() if f["data"].get("type") == "result"), 2,
                         "both turns' results reached the kernel live while the writer lagged")
        self.assertEqual([r["kind"] for r in self._hostlog()].count("reader-behind"), 1)
        k.close()

    def test_a_second_end_with_a_shorter_grace_pulls_the_deadline_in(self):
        # finding 8
        host, sock, spec = self._start()
        k, _ = self._attach(sock)
        k.send({"t": "in", "data": self._user("slow sleep=30")})
        k.recv_until(lambda f: f.get("t") == "out" and f["data"].get("type") == "assistant")
        k.send({"t": "end", "grace": 60})
        k.send({"t": "end", "grace": 1})
        t0 = time.time()
        ex = k.recv_until(lambda f: f.get("t") == "exit", timeout=15)
        self.assertEqual(ex["cause"], "end-forced")
        self.assertLess(time.time() - t0, 10, "the shorter grace won")
        self.assertIn("end-grace-shortened", [r["kind"] for r in self._hostlog()])
        k.close()

    def test_the_heartbeat_keeps_the_lease_valid_past_a_short_ttl(self):
        # finding 10: every other check happens within a beat of the write; this one waits past a TTL shorter
        # than the wait, so only real beats keep the lease valid
        host, sock, spec = self._start()
        with mock.patch.object(sb, "LEASE_TTL_S", 4.0):
            time.sleep(5.0)
            lease = self._lease()
            self.assertEqual(sb.lease_state(lease, time.time()), "valid", "beats kept it fresh: t=%r now=%r" % (lease.get("t"), time.time()))
        self.assertGreater(lease["t"], spec_t if (spec_t := 0) else 0)

    def test_a_double_journal_fault_never_breaks_a_later_attach(self):
        # finding b: an unrecorded gap used to leave the index short of the offsets; the next replay across it
        # raised inside the host's client loop and the kernel read a bare EOF
        host, sock, spec = self._start(_test_journal_fault_at=1, _test_journal_gap_fault=True)
        k, _ = self._attach(sock)
        k.send({"t": "in", "data": self._user("hi sleep=0.2")})
        k.recv_until(lambda f: f.get("t") == "out" and f["data"].get("type") == "result")
        k.send({"t": "detach"}); k.close()
        deadline = time.time() + 10
        while time.time() < deadline and not any(r["kind"] == "journal-gap-unrecorded" for r in self._hostlog()):   # loop-ok
            time.sleep(0.05)
        k2, hello = self._attach(sock, ack=-1, pid=4343)
        k2.send({"t": "ping"}); k2.recv_until(lambda f: f.get("t") == "pong")
        offs = [f["offset"] for f in k2.outs()]
        self.assertEqual(offs, [o for o in range(hello["journal"]["next"]) if o != 1], "everything but the hole replayed, no fault, no EOF")
        self.assertNotIn("client-loop-failed", [r["kind"] for r in self._hostlog()])
        self.assertIsNone(host.poll())
        k2.close()

    def test_an_attach_while_the_writer_lags_sends_the_unwritten_records_from_memory(self):
        # finding c: records read but not yet journaled were neither replayed nor backlogged. The shape that lost
        # them to a replay built from two snapshots (the journal as of the attach, then memory): more than two
        # hundred records landed when the kernel attaches, so the replay reaches its drain, a kernel not reading
        # yet and send buffers small enough (the seam) that the drain WAITS, and records the writer lands during
        # that wait, gone from memory before a second pass could read them. Only a replay that resolves each
        # offset at its own moment sends every record exactly once (the commit-8 review's item 9).
        turns = 160                                                       # 1 init + 160 (assistant, result) pairs
        total = 1 + 2 * turns
        host, sock, spec = self._start(_test_journal_delay_s=0.01, _test_socket_small_buffers=True)
        k, _ = self._attach(sock)
        for i in range(turns):
            k.send({"t": "in", "data": self._user("turn%d sleep=0" % i)})
        k.recv_until(lambda f: sum(1 for g in k.outs() if g["data"].get("type") == "result") == turns, timeout=60)
        k.send({"t": "detach"}); k.close()
        seg = Path(self.state) / "hosts" / SID / "journal-0.jsonl"
        landed = lambda: sum(1 for _ in open(seg, "rb")) if seg.exists() else 0
        deadline = time.time() + 30
        while time.time() < deadline and landed() < 210:                  # loop-ok: the event is the writer's 210th record on disk
            time.sleep(0.002)
        self.assertLess(landed(), total, "records are still unwritten when the second kernel attaches (else the shape is not exercised)")
        k2, hello = self._attach(sock, ack=-1, pid=4343)
        self.assertEqual(hello["journal"]["next"], total, "the hello counted every record read, landed or not")
        deadline = time.time() + 30
        while time.time() < deadline and landed() < total:                # loop-ok: the writer landing the last record, while the replay waits on us
            time.sleep(0.01)
        self.assertEqual(landed(), total)
        k2.recv_until(lambda f: sum(1 for g in k2.outs() if g["data"].get("type") == "result") == turns, timeout=60)
        k2.send({"t": "ping"}); k2.recv_until(lambda f: f.get("t") == "pong")
        offs = [f["offset"] for f in k2.outs()]
        self.assertEqual(offs, list(range(total)), "every record once, in order, whether from disk, memory or the backlog; host log: %r"
                         % [(r["kind"], r.get("at"), r.get("error")) for r in self._hostlog()][-8:])
        k2.close()

    def test_an_end_right_after_a_line_lets_the_line_reach_the_cli_first(self):
        # finding d: `end` used to close stdin ahead of lines still queued on the pump
        host, sock, spec = self._start()
        k, _ = self._attach(sock)
        # one socket write carrying both frames: the host reads them together and queues the line, then the end
        # sentinel, on the stdin pump; no sleep, no timing (the review's item 10)
        k.s.sendall(sh.encode_frame({"t": "in", "data": self._user("last words sleep=0.1")}) + sh.encode_frame({"t": "end", "grace": 20}))
        ex = k.recv_until(lambda f: f.get("t") == "exit", timeout=15)
        self.assertEqual(ex["cause"], "end")
        self.assertIn("last words", open(self.fake_log).read(), "the queued line reached the CLI before its stdin closed")
        self.assertEqual(sum(1 for f in k.outs() if f["data"].get("type") == "result"), 1, "and its turn ran to its result")
        k.close()

    def test_an_open_request_whose_journal_write_failed_is_still_re_sent_on_attach(self):
        # finding e: the re-send came from the journal, which skips a gap; it comes from the parked table now
        host, sock, spec = self._start(_test_journal_fault_at=2)      # 0 init, 1 assistant, 2 the permission request
        k, _ = self._attach(sock)
        k.send({"t": "in", "data": self._user("please ask=permission after=0.3 sleep=0.2")})
        req = k.recv_until(lambda f: f.get("t") == "out" and f["data"].get("type") == "control_request")
        self.assertEqual(req["offset"], 2)
        k.send({"t": "ack", "offset": 1}); k.send({"t": "ping"}); k.recv_until(lambda f: f.get("t") == "pong")
        k.close()
        k2, hello = self._attach(sock, ack=1, pid=4343)
        self.assertEqual(hello["parked"], [req["data"]["request_id"]])
        again = k2.recv_until(lambda f: f.get("t") == "out" and f["data"].get("type") == "control_request")
        self.assertEqual(again["data"]["request_id"], req["data"]["request_id"], "re-sent from the table although its journal write failed")
        k2.close()

    def _env_probe_cli(self):
        """A CLI stand-in that records whether CLAUDE_CODE_OAUTH_TOKEN is set in ITS environment (presence only,
        never the value) and then becomes the fake CLI. Returns (cli_path, the record's path)."""
        seen = os.path.join(self.state, "cli-env-seen")
        probe = os.path.join(self.state, "cli-env-probe.py")
        with open(probe, "w") as f:
            f.write("#!%s\nimport os, sys\n" % sys.executable)
            f.write("open(%r, 'w').write('present' if os.environ.get('CLAUDE_CODE_OAUTH_TOKEN') else 'absent')\n" % seen)
            f.write("os.execv(%r, [%r, %r] + sys.argv[1:])\n" % (sys.executable, sys.executable, FAKE))
        os.chmod(probe, 0o755)
        return probe, seen

    def _one_turn(self, sock):
        k, hello = self._attach(sock)
        k.send({"t": "in", "data": self._user("hi sleep=0.1")})
        k.recv_until(lambda f: f.get("t") == "out" and f["data"].get("type") == "result")
        return k

    def test_a_token_in_the_hosts_environment_reaches_the_cli_and_is_nowhere_the_host_writes(self):
        """The environment road under a host (the pull-in review's item 1): spawn.json carries no token, the host's
        process environment does, and the CLI the host spawns sees it, the way a kernel child sees the compose's env."""
        probe, seen = self._env_probe_cli()
        tok = "synthetic-login-token-" + uuid.uuid4().hex
        host, sock, spec = self._start(host_env={"CLAUDE_CODE_OAUTH_TOKEN": tok}, cli_path=probe)
        self.assertNotIn("CLAUDE_CODE_OAUTH_TOKEN", json.dumps(spec), "the spec the host read carries no token")
        k = self._one_turn(sock)
        self.assertEqual(open(seen).read(), "present", "the CLI inherited the token from the host's environment")
        journal = list(sh.read_journal_dir(os.path.join(self.state, "hosts", SID)))
        blob = json.dumps(self._hostlog()) + json.dumps([r for _, r in journal]) + json.dumps(k.frames)
        blob += (Path(self.state) / "hosts" / SID / "spawn.json").read_text() + sb.read_lease(self.state, SID).__repr__()
        self.assertNotIn(tok, blob, "the token's value is in no file the host writes, no frame, no lease")
        k.close()

    def test_without_a_token_in_the_hosts_environment_the_cli_gets_none(self):
        probe, seen = self._env_probe_cli()
        host, sock, spec = self._start(cli_path=probe)
        k = self._one_turn(sock)
        self.assertEqual(open(seen).read(), "absent", "no token anywhere: the probe reads the CLI's real environment")
        k.close()

    @unittest.skipUnless(SDK_SITE, "the SDK venv is not on this machine; the pipe transport covered the host")
    def test_the_sdk_transport_hands_the_hosts_environment_to_the_cli_too(self):
        """The road a real install takes: the SDK's SubprocessCLITransport merges the host's environment under the
        spec's overlay, so the token rides there as well."""
        probe, seen = self._env_probe_cli()
        tok = "synthetic-login-token-" + uuid.uuid4().hex
        host, sock, spec = self._start(sdk=True, host_env={"CLAUDE_CODE_OAUTH_TOKEN": tok}, cli_path=probe)
        k = self._one_turn(sock)
        self.assertEqual([r["transport"] for r in self._hostlog() if r["kind"] == "cli-spawned"], ["sdk"])
        self.assertEqual(open(seen).read(), "present")
        k.send({"t": "end", "grace": 10})
        k.recv_until(lambda f: f.get("t") == "exit")
        k.close()

    @unittest.skipUnless(SDK_SITE, "the SDK venv is not on this machine; the pipe transport covered the host")
    def test_the_sdk_transport_drives_the_fake_cli_the_same_way(self):
        host, sock, spec = self._start(sdk=True)
        k, hello = self._attach(sock)
        k.send({"t": "in", "data": self._user("hi sleep=0.1")})
        k.recv_until(lambda f: f.get("t") == "out" and f["data"].get("type") == "result")
        spawned = [r for r in self._hostlog() if r["kind"] == "cli-spawned"]
        self.assertEqual(spawned[0]["transport"], "sdk", "the SDK's own SubprocessCLITransport spawned the CLI")
        k.send({"t": "end", "grace": 10})
        k.recv_until(lambda f: f.get("t") == "exit")
        k.close()


if __name__ == "__main__":
    unittest.main()
