#!/usr/bin/env python3
"""The per-session host (T315, stage 4 of the restart-surviving sessions program): the pure pieces
(frames, the journal, the parked table, the neutral hook answers) and the host as a real process driving
the fake CLI (tests/fixtures/fake_claude.py) while this test plays the kernel over the Unix socket; one case
(HostProcess's pick case) lets the REAL backend loop play the kernel instead, for a settings pick on the hosted road.

Hermetic: a temp state root per test, the fake CLI on a temp path, no scopes (the host is a plain child
here), every process killed by the test, synthetic ids. The host runs on its built-in pipe transport when
the SDK is not importable (CI, the plain test venv); one test runs the SDK transport when the machine has
the SDK venv, and skips otherwise.
"""
import ast
import asyncio
import contextlib
import errno
import json
import os
import shutil
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import time
import types
import unittest
import uuid
from importlib.machinery import ModuleSpec
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
CLI_PID = 4194305       # the stand-in CLI's pid in the in-process classes: above Linux's pid_max (2^22), so it names no
#                         process, and the stub lease API those classes hand the host answers proc_start for it


def system_tmp() -> str:
    """The temp dir this RUN was handed, before tests/conftest.py redirected TMPDIR into the run's private root
    (ROMP_TESTS_SYSTEM_TMPDIR, recorded by tests/__init__.py with setdefault, so an xdist worker keeps the controller's
    record rather than its own, one level deeper): the sanctioned way out of the root, for an AF_UNIX path that has to
    fit sun_path or be built to an exact length (tests/test_host_transport.py's two socket dirs take the same road)."""
    return os.environ.get("ROMP_TESTS_SYSTEM_TMPDIR") or tempfile.gettempdir()


def padded_root(case, total, tail):
    """A directory whose path plus `/` plus `tail` (the socket's path below the root, `hosts/<sid8>.sock`) is exactly
    `total` BYTES (os.fsencode: the measure the host's budget check and the bind take, and not the character count, which
    a multibyte component separates from it), made under the system temp dir (system_tmp) and removed with the case.
    NEVER A SKIP (the review of the socket-mode fix, round 2, 2026-09-19): round 1's padded cases were rooted in the run's
    private temp root and skipped once that root was deep (the sweep's xdist nesting, a long TMPDIR), so the module
    reported green with the high they pin unpinned. A system temp dir too deep for the pad is a FAILURE naming the remedy,
    so a green module means the padded cases ran (PaddedRoots pins both directions)."""
    base = tempfile.mkdtemp(prefix="pad-", dir=system_tmp())
    case.addCleanup(shutil.rmtree, base, True)
    pad = total - len(os.fsencode(os.path.join(base, "p", tail))) + 1          # "p" stands for the padding component
    if pad < 1:
        case.fail("the system temp dir %s is too deep to build a %d-byte socket path under it: run the suite under a shorter "
                  "TMPDIR (the padded cases fail rather than skip, so a green module means they ran)" % (system_tmp(), total))
    root = os.path.join(base, "p" * pad)
    os.mkdir(root)
    case.assertEqual(len(os.fsencode(os.path.join(root, tail))), total, root)
    return root


def require_utf8_names(case):
    """The multibyte cases' precondition, asserted and NEVER skipped (review round 3, 2026-09-19, M3): the two multibyte
    cases are the only pins on the byte measure, the mutant that reinstates round 1's high, and through round 2 they
    sat behind a skipUnless with nothing asserting they ran, so a runner whose filesystem encoding is not UTF-8 reported
    the module green with that high unpinned. Like padded_root, a runner that cannot separate bytes from characters is a
    FAILURE naming the remedy, so a green module means the cases ran (PaddedRoots pins this against its refusable
    input)."""
    n = len(os.fsencode("\u00fc"))
    case.assertEqual(n, 2, "the filesystem encoding %s is not UTF-8 (%r encodes to %d byte(s), not 2), so the multibyte cases "
                     "cannot separate bytes from characters here: run the suite under a UTF-8 locale (LC_CTYPE=C.UTF-8). They "
                     "fail rather than skip, so a green module means they ran" % (sys.getfilesystemencoding(), "\u00fc", n))


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
        (Path(self.state) / "hosts").mkdir(mode=0o700, exist_ok=True)   # the layout write_spawn_spec leaves: both directories
        d.mkdir(mode=0o700, exist_ok=True)                                 # 0700, which the launcher's descent verifies (round 4)
        spec_path = d / "spawn.json"
        spec_path.write_text("{}")
        me = types.SimpleNamespace(cli_scope=cli_scope, state_dir=self.state)
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

    def test_every_credential_shaped_name_leaves_the_spec_env_not_only_the_three(self):
        """The box admin's hazard review of the pull-in (2026-09-16): the first cut moved AUTH_ENV_NAMES alone, so a
        credential-shaped variable of any OTHER name in the overlay was written to spawn.json. Every name
        env_credential_names would flag over the overlay itself leaves it now (spawn_env_secret_names): the two
        suffixes and 1Password's names. Synthetic names, values built at run time (never a real key's shape)."""
        val = "synthetic-notes-token-" + uuid.uuid4().hex
        key = "synthetic-notes-key-" + uuid.uuid4().hex
        op = "synthetic-op-session-" + uuid.uuid4().hex
        spec = {"sid": SID, "env": {"ROMP_SID": SID, "NOTES_ENDPOINT": "http://notes.test", "NOTES_API_TOKEN": val,
                                    "NOTES_API_KEY": key, "OP_SESSION_notes": op, "EMPTY_TOKEN": ""}}
        secrets = sb.split_spawn_secrets(spec)
        self.assertEqual(spec["env"], {"ROMP_SID": SID, "NOTES_ENDPOINT": "http://notes.test", "EMPTY_TOKEN": ""},
                         "a plain name stays; an empty credential-shaped value holds no secret and stays the unset it means")
        self.assertEqual(sorted(secrets), ["NOTES_API_KEY", "NOTES_API_TOKEN", "OP_SESSION_notes"])
        self.assertTrue(secrets["NOTES_API_TOKEN"] == val and secrets["NOTES_API_KEY"] == key and secrets["OP_SESSION_notes"] == op,
                        "the returned values are the overlay's")
        text = json.dumps(spec)
        for v in (val, key, op):
            self.assertNotIn(v, text, "no moved value survives in the spec")
        self.assertEqual(sb.spawn_env_secret_names({"ROMP_SID": SID, "NOTES_ENDPOINT": "x"}), [], "nothing credential-shaped: nothing to move")
        self.assertEqual(sb.spawn_env_secret_names({"ANTHROPIC_API_KEY": ""}), ["ANTHROPIC_API_KEY"], "the three leave whatever their value")
        self.assertEqual(sb.spawn_env_secret_names(None), [], "no overlay: nothing to move")

    def test_spawn_host_hands_every_moved_name_to_the_host_through_its_environment(self):
        """The road a moved name takes is the login token's (_spawn_host): the host's process environment, laid over
        the kernel's own, so the overlay's value outranks an inherited one exactly as options.env does for a kernel
        child, and never the command line. Green on the base tree by design (review round 1's addendum, 2026-09-18):
        this hands _spawn_host the dict itself and pins its merge, a base leg the change newly leans on, not the
        split; the kernel's road for a name beyond the three is pinned by the spawn-road case below and, end to end
        through a real host, by HostProcess's moved-name case, which derives the host's environment from the split."""
        val = "synthetic-notes-token-" + uuid.uuid4().hex
        with mock.patch.dict(os.environ, {"NOTES_API_TOKEN": "inherited-" + uuid.uuid4().hex}):
            argv, kw = self._spawn(False, {"NOTES_API_TOKEN": val})
        self.assertTrue(kw["env"]["NOTES_API_TOKEN"] == val, "the overlay's value rides the host's environment, over the kernel's")
        self.assertFalse(any(val in a for a in argv), "the value never rides the command line")

    def _spawn_road(self, env, login=""):
        """The real _host_transport_for on its spawn road over a stub kernel (review round 1, 2026-09-18, shared by the
        round's cases): hosts/ is cleared first, since a lease-less leftover hosts/<sid> from an earlier spawn in the
        same state root sends the call down _host_orphan_recover, which this stub does not provide. Returns the
        spawn.json written, what _spawn_host was handed, and every _log call as (message, kwargs)."""
        ht = sb._ht()
        shutil.rmtree(Path(self.state) / "hosts", ignore_errors=True)
        handed, logged = {}, []

        def spawn_host(sess, spec_path, secret_env=None):
            handed["secrets"] = dict(secret_env or {})
            ht.host_sock(self.state, SID).touch()                    # the launcher "served" its socket
            return types.SimpleNamespace(pid=4242, poll=lambda: None, returncode=None)
        me = types.SimpleNamespace(state_dir=self.state, code_version="abc12345", cli_scope=False,
                                   _host_recently_ended={}, _lock=threading.Lock(), _host_spawning=set(),
                                   _holder_ident=sb.SdkBackend._holder_ident, _spawn_host=spawn_host,
                                   _new_host_transport=lambda sess, sock, offset: ("transport", str(sock), offset),
                                   _log=lambda m, *a, **k: logged.append((str(m), k)))
        sess = types.SimpleNamespace(sid=SID, name="web", _options_login=login, _host=None, _host_is_attach=False)
        opts = types.SimpleNamespace(cli_path="/x/romp-cli-scope", cwd=self.state, env=dict(env), permission_mode="default")
        t = asyncio.run(sb.SdkBackend._host_transport_for(me, sess, opts, ()))
        self.assertEqual(t[0], "transport", "the spawn road handed back the new transport")
        written = json.loads((Path(self.state) / "hosts" / SID / "spawn.json").read_text())
        return written, handed, logged

    def test_the_host_launch_writes_spawn_json_without_any_credential_shaped_name_and_hands_them_to_the_host(self):
        """The real _host_transport_for, spawn road, over a stub kernel, with an overlay carrying a credential-shaped
        name beyond the three (the box admin's hazard review of the pull-in, 2026-09-16): the file keeps the plain
        name, the value is in no file under hosts/, _spawn_host receives exactly the moved variable for the host's
        environment, and the log names what moved without its value. Review round 1 (2026-09-18) pinned the line's
        two deliberate details, which survived mutation with the suite green: its problem=False classification, by
        identity (assertFalse(None) passes, and None is exactly what a dropped kwarg records), and the login names'
        silence (a second spawn, a login token alone in the overlay, says nothing)."""
        ht = sb._ht()
        handed, logged = {}, []
        val = "synthetic-notes-token-" + uuid.uuid4().hex

        def spawn_host(sess, spec_path, secret_env=None):
            handed["secrets"] = dict(secret_env or {})
            ht.host_sock(self.state, SID).touch()                    # the launcher "served" its socket
            return types.SimpleNamespace(pid=4242, poll=lambda: None, returncode=None)
        me = types.SimpleNamespace(state_dir=self.state, code_version="abc12345", cli_scope=False,
                                   _host_recently_ended={}, _lock=__import__("threading").Lock(), _host_spawning=set(),
                                   _holder_ident=sb.SdkBackend._holder_ident, _spawn_host=spawn_host,
                                   _new_host_transport=lambda sess, sock, offset: ("transport", str(sock), offset),
                                   _log=lambda m, *a, **k: logged.append((str(m), k)))
        sess = types.SimpleNamespace(sid=SID, name="web", _options_login="", _host=None, _host_is_attach=False)
        opts = types.SimpleNamespace(cli_path="/x/romp-cli-scope", cwd=self.state,
                                     env={"ROMP_SID": SID, "NOTES_ENDPOINT": "http://notes.test", "NOTES_API_TOKEN": val},
                                     permission_mode="default")
        t = asyncio.run(sb.SdkBackend._host_transport_for(me, sess, opts, ()))
        self.assertEqual(t[0], "transport", "the spawn road handed back the new transport")
        written = json.loads((Path(self.state) / "hosts" / SID / "spawn.json").read_text())
        self.assertEqual(written["env"], {"ROMP_SID": SID, "NOTES_ENDPOINT": "http://notes.test"},
                         "the plain name stays in the file; the credential-shaped one is gone")
        under_hosts = [q for q in (Path(self.state) / "hosts").rglob("*") if q.is_file()]
        self.assertTrue(under_hosts, "the write left files to check")
        for q in under_hosts:
            self.assertNotIn(val, q.read_bytes().decode("utf-8", "replace"), "the value is in no file under hosts/")
        self.assertEqual(handed["secrets"], {"NOTES_API_TOKEN": val}, "the host's environment gets exactly the moved variable")
        self.assertEqual(opts.env["NOTES_API_TOKEN"], val, "the options object is untouched (spawn_spec copied)")
        said = [(m, k) for m, k in logged if "NOTES_API_TOKEN" in m]
        self.assertEqual(len(said), 1, "the log names the moved variable, once")
        self.assertNotIn(val, "".join(m for m, _ in logged), "and never its value")
        self.assertIs(said[0][1].get("problem"), False, "a routine line, never a problem row: filed as False explicitly")
        # the three login names are routine (every login launch moves one) and go unsaid
        written, handed, logged = self._spawn_road({"ROMP_SID": SID, "CLAUDE_CODE_OAUTH_TOKEN": self.tok})
        self.assertEqual(written["env"], {"ROMP_SID": SID})
        self.assertEqual(handed["secrets"], {"CLAUDE_CODE_OAUTH_TOKEN": self.tok}, "the login token still moves")
        self.assertEqual([m for m, _ in logged if "credential-shaped" in m], [], "a login name alone: nothing said")

    def test_a_non_string_value_anywhere_in_the_overlay_does_not_abort_the_split(self):
        """Review round 1 (2026-09-18): the first cut judged the shape rule over the raw overlay, and
        env_credential_names strips every value it is handed, so ONE non-string value anywhere in the overlay raised
        AttributeError out of split_spawn_secrets, where the base tree launched the session (a total function became
        partial). The rule is judged over a coerced view now (_overlay_text, for the NAME decision only): nothing
        raises, and a credential-shaped name whose value is not a string still leaves the spec, as the text the
        host's environment carries (filtering the overlay to string values first would have written it into the file).

        What this pins about a non-string value under a PLAIN name is BASE behaviour, not correctness (review round
        2, 2026-09-18): it stays in the spec as it always did, and a spec holding one cannot launch a real CLI. The
        host's SDK transport, which every real install runs, merges the overlay as it is and a subprocess
        environment refuses a non-string value; only the pipe transport of the SDK-less tests converts per value.
        Pre-existing, unchanged here, out of scope for a fix-tier change, and no writer of options.env produces such
        a value today; written down so the assertion is not read as support for the state (split_spawn_secrets'
        docstring carries the same note)."""
        spec = {"sid": SID, "env": {"ROMP_SID": SID, "X_COUNT": 5, "X_FLAG": True}}
        self.assertEqual(sb.split_spawn_secrets(spec), {}, "nothing credential-shaped: nothing moves, nothing raises")
        self.assertEqual(spec["env"], {"ROMP_SID": SID, "X_COUNT": 5, "X_FLAG": True}, "the plain values stay as they were")
        num = 10 ** 12 + uuid.uuid4().int % 10 ** 12
        spec = {"sid": SID, "env": {"ROMP_SID": SID, "NOTES_API_TOKEN": num, "NOTES_API_KEY": ["a", "b"], "X_FLAG": True}}
        secrets = sb.split_spawn_secrets(spec)
        self.assertEqual(secrets, {"NOTES_API_TOKEN": str(num), "NOTES_API_KEY": str(["a", "b"])},
                         "a credential-shaped name moves whatever its value's type, as text for the host's environment")
        self.assertEqual(spec["env"], {"ROMP_SID": SID, "X_FLAG": True})
        self.assertNotIn(str(num), json.dumps(spec), "the value is gone from the spec")
        self.assertEqual(sb.split_spawn_secrets({"env": {"CLAUDE_CODE_OAUTH_TOKEN": None}}), {"CLAUDE_CODE_OAUTH_TOKEN": ""},
                         "a login name moves whatever its value; None rides as the empty string, never the word None")
        spec = {"env": {"EMPTY_TOKEN": None}}
        self.assertEqual(sb.split_spawn_secrets(spec), {}, "None under another credential-shaped name holds no secret and stays")
        self.assertEqual(spec["env"], {"EMPTY_TOKEN": None})
        for v in (5, True, 1.5, ["a"], {"k": "v"}, 0, False, None, "", []):
            self.assertEqual(sb.spawn_env_secret_names({"X_VALUE": v}), [], "total over every JSON-native value: %r" % (v,))

    def test_the_host_launch_proceeds_with_a_non_string_value_and_still_omits_the_credential_under_one(self):
        """The real _host_transport_for spawn road (review round 1, 2026-09-18): an overlay holding an integer under a
        plain name and one under a credential-shaped name. The first cut aborted this launch before the file was
        written; now the file is written, the credential-shaped name's value is in no file under hosts/, and the host
        receives it as text. The plain integer staying in the file is BASE behaviour, pinned as such and not as a
        supported state (review round 2, 2026-09-18): the SDK transport a real install's host runs cannot spawn a CLI
        from a spec whose overlay holds a non-string value; pre-existing, unchanged here, see split_spawn_secrets."""
        num = 10 ** 12 + uuid.uuid4().int % 10 ** 12
        written, handed, logged = self._spawn_road({"ROMP_SID": SID, "X_COUNT": 5, "NOTES_API_TOKEN": num})
        self.assertEqual(written["env"], {"ROMP_SID": SID, "X_COUNT": 5}, "the plain integer stays in the file as it was")
        under_hosts = [q for q in (Path(self.state) / "hosts").rglob("*") if q.is_file()]
        self.assertTrue(under_hosts, "the write left files to check")
        for q in under_hosts:
            self.assertNotIn(str(num), q.read_bytes().decode("utf-8", "replace"), "the value is in no file under hosts/")
        self.assertEqual(handed["secrets"], {"NOTES_API_TOKEN": str(num)}, "the host's environment gets it as text")
        said = [m for m, _ in logged if "NOTES_API_TOKEN" in m]
        self.assertEqual(len(said), 1, "the log names the moved variable, once")
        self.assertNotIn(str(num), "".join(m for m, _ in logged), "and never its value")

    def test_a_lowercase_credential_shaped_name_leaves_the_spec_env_too(self):
        """Review round 1 (2026-09-18): the shape rule was an exact, case-sensitive suffix, so notes_api_token was never
        moved and would have been written to spawn.json with its value. The suffixes are compared on the upper-cased
        name now (in env_credential_names, so the boot notice folds case too); an empty value still stays whatever
        its case, and a name whose suffix only begins with the shape stays."""
        val = "synthetic-notes-token-" + uuid.uuid4().hex
        key = "synthetic-notes-key-" + uuid.uuid4().hex
        spec = {"sid": SID, "env": {"ROMP_SID": SID, "notes_api_token": val, "Notes_Api_Key": key, "empty_token": "",
                                    "editor_tokenizer": "x"}}
        secrets = sb.split_spawn_secrets(spec)
        self.assertEqual(secrets, {"notes_api_token": val, "Notes_Api_Key": key}, "moved under their own spelling, values byte for byte")
        self.assertEqual(spec["env"], {"ROMP_SID": SID, "empty_token": "", "editor_tokenizer": "x"})
        self.assertNotIn(val, json.dumps(spec)); self.assertNotIn(key, json.dumps(spec))
        written, handed, _ = self._spawn_road({"ROMP_SID": SID, "notes_api_token": val})
        self.assertEqual(written["env"], {"ROMP_SID": SID}, "the file omits the lowercase name")
        self.assertNotIn(val, (Path(self.state) / "hosts" / SID / "spawn.json").read_text())
        self.assertEqual(handed["secrets"], {"notes_api_token": val})


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


class _PickSdk:
    """A claude_agent_sdk stand-in for HostProcess's pick case: the REAL backend loop runs against a REAL host, and
    this client drives the REAL HostTransport the loop hands it the way ClaudeSDKClient does (the plain test venv has
    no SDK package). Its connect is the attach and the hello (the kernel's handler runs inside it); the initialize the
    fake CLI answers clears the transport's initialize gate, so the transport's close sends `end`, not the `detach` a
    connect that never completed sends; the loop's queued turns go out as `in` frames; the host's records come back as
    the message classes the loop dispatches on (system, assistant, result; every other record type is dropped)."""

    class Options:
        def __init__(self, **kw):
            self.session_id = self.resume = None
            for k, v in kw.items():
                setattr(self, k, v)

    class HookMatcher:
        def __init__(self, **kw):
            self.timeout = None                  # _options sets it on every matcher under a host; a dict stand-in refuses that
            self.__dict__.update(kw)

    class TextBlock:
        def __init__(self, text):
            self.text = text

    class SystemMessage:
        def __init__(self, data):
            self.subtype, self.data, self.uuid = data.get("subtype"), data, data.get("uuid") or str(uuid.uuid4())

    class AssistantMessage:
        def __init__(self, data):
            m = data.get("message") or {}
            self.content = [_PickSdk.TextBlock(str(c.get("text", ""))) for c in (m.get("content") or [])
                            if isinstance(c, dict) and c.get("type") == "text"]
            self.model = m.get("model") or "fake-model"
            self.uuid = data.get("uuid") or str(uuid.uuid4())
            self.parent_tool_use_id = data.get("parent_tool_use_id")
            self.stop_reason, self.error = m.get("stop_reason") or "end_turn", None

    class ResultMessage:
        def __init__(self, data):
            self.uuid = data.get("uuid") or str(uuid.uuid4())
            self.subtype, self.is_error = data.get("subtype") or "success", bool(data.get("is_error"))
            self.num_turns, self.session_id = int(data.get("num_turns") or 1), data.get("session_id")
            self.duration_ms, self.duration_api_ms = int(data.get("duration_ms") or 0), int(data.get("duration_api_ms") or 0)
            self.total_cost_usd, self.usage = float(data.get("total_cost_usd") or 0.0), data.get("usage") or {}
            self.result, self.parent_tool_use_id = data.get("result"), None
            self.model_usage = self.api_error_status = self.rate_limit_info = None

    class PermissionResultAllow:
        def __init__(self, behavior="allow", **kw):
            self.behavior = behavior

    class PermissionResultDeny:
        def __init__(self, behavior="deny", **kw):
            self.behavior = behavior

    class ClaudeSDKClient:
        instances = []

        def __init__(self, options=None, transport=None):
            self.options, self.transport = options, transport
            self.torn_down = False
            self._records = None
            type(self).instances.append(self)

        async def __aenter__(self):
            t = self.transport
            await t.connect()                    # the attach; the hello reaches the kernel's handler in here
            rid = "init-" + uuid.uuid4().hex[:8]
            await t.write(json.dumps({"type": "control_request", "request_id": rid,
                                      "request": {"subtype": "initialize", "hooks": {}}}) + "\n")
            self._records = t.read_messages()    # ONE reader for the transport's life: the generator resumes below
            async for data in self._records:
                if isinstance(data, dict) and data.get("type") == "control_response" \
                        and str((data.get("response") or {}).get("request_id")) == rid:
                    break                        # the initialize's answer: the gate the transport's close reads is open
            return self

        async def __aexit__(self, *a):
            self.torn_down = True
            await self.transport.close()         # `end` after a completed handshake, `detach` otherwise
            return False

        async def query(self, prompt, session_id="default"):
            async for turn in prompt:
                await self.transport.write(json.dumps(turn) + "\n")

        async def interrupt(self):
            pass

        async def get_context_usage(self):
            return {"percentage": 1, "model": "fake-model"}

        async def get_server_info(self):
            return {}

        async def receive_messages(self):
            kinds = {"system": _PickSdk.SystemMessage, "assistant": _PickSdk.AssistantMessage, "result": _PickSdk.ResultMessage}
            async for data in self._records:
                cls = kinds.get(data.get("type")) if isinstance(data, dict) else None
                if cls is not None:
                    yield cls(data)

    @classmethod
    def install(cls):
        """Put the stand-in where the loop imports claude_agent_sdk from; returns the module it displaced (or None)."""
        m = types.ModuleType("claude_agent_sdk")
        m.__spec__ = ModuleSpec("claude_agent_sdk", loader=None)
        for name in ("ClaudeSDKClient", "HookMatcher", "TextBlock", "SystemMessage", "AssistantMessage", "ResultMessage",
                     "PermissionResultAllow", "PermissionResultDeny"):
            setattr(m, name, getattr(cls, name))
        m.ClaudeAgentOptions = cls.Options
        saved = sys.modules.get("claude_agent_sdk")
        sys.modules["claude_agent_sdk"] = m
        return saved


class SocketMode(unittest.TestCase):
    """The control socket is owner-only from the moment `hosts/<sid8>.sock` exists, and a host that cannot publish it
    serves nothing and keeps nothing (2026-09-18, split out of PR 789's round 1, finding fresh-5, as its own fix; the
    budget, umask, sweep and refusal cases from its own round 1, 2026-09-19, the creation-moment, sweep-arm, bind-leg
    and close-on-failure cases from that round's mutation pass, and the byte-measure, kept-lease and session-directory
    cases from round 2, the same day, the bind-moment, step-order, no-identity and journal-close cases from that
    round's mutation pass, and round 3's reorder cases: the reviewer's ruling of 2026-09-19 moved the socket road's
    prelude, `hosts/` made ours, the budget check, the dead socket's unlink and the stale-temp sweep, out of
    _serve_socket and ahead of the CLI's spawn (sh.SessionHost._prepare_socket), so after the lease only the bind, the
    chmod and the rename run, and a prelude refusal starts no CLI and writes no lease; the ordering pins, the two
    refusal classes and the re-pointed post-spawn cases below are that round's). asyncio.start_unix_server binds AND
    listens at the umask's mode, and the old code's chmod one line later left the published path at that mode for the
    gap: the last member of the create-then-tighten class PR 789 closed for the kernel's credential files. A stat once
    the host is up passes on that code, so the mode cases capture the mode at CREATION: the mode the temp carries as
    os.rename moves it onto the published path, and which path os.chmod ever touched, under a permissive umask for the
    test's duration. Every case but two drives the real run() in this process, with a stub in place of the CLI transport
    (no CLI is spawned) and recording lease helpers, so the bind under test is run()'s own, not a helper's; the name case
    (test_the_temp_name_is_writer_unique_and_the_published_names_length) reads sock_names without run(), and the two
    constructor cases (a symlinked hosts/<sid>/, and since round 3 a symlinked hosts/ too: kernel-2) construct Journal
    and SessionHost, which refuse before run() could start."""

    def setUp(self):
        self.addCleanup(os.umask, os.umask(0o000))      # permissive on purpose: the mode the bind gives is the question
        self.state = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.state, True)
        self._spec_at(self.state)
        self.host_log = []
        self.leases, self.lease_calls = {}, []
        # the stand-in CLI's identity as the stub proc_start reports it for CLI_PID: "1" while the CLI lives (the start
        # recorded at the spawn), None once it is gone, another string once the pid names a different process. The
        # _NoCli stand-in's close() marks the CLI gone, as the real transport's close returns only once the CLI is dead,
        # unless the case sets cli_outlives_close (the kept-lease case): a close that RETURNED with the CLI alive
        self.cli_start_now, self.cli_outlives_close = "1", False
        self.spawn_calls = 0                            # how many times run() reached the spawn stub (a prelude refusal: none)
        self.lease_api = {"write_lease": lambda sd, lease: (self.lease_calls.append("write"), self.leases.__setitem__(lease["sid"], dict(lease))),
                          "remove_lease": lambda sd, sid: (self.lease_calls.append("remove"), self.leases.pop(sid, None)) and True,
                          "proc_start": lambda pid: self.cli_start_now if pid == CLI_PID else "1"}

    def _spec_at(self, root, sid=SID):
        """hosts/<sid>/spawn.json under `root` as the kernel writes it (the session directory 0700); hosts/ itself at the
        umask's mode here (0777 under the setUp umask), the shape an old install's kernel left: the host tightens it.
        `sid` is SID except in the bind-leg case, whose short sid gives the temp a name longer than the published one."""
        self.root = root
        self.sdir = Path(root) / "hosts" / sid
        self.sdir.mkdir(parents=True, mode=0o700)
        spec = {"sid": sid, "name": "web", "version": "abc12345", "state_dir": root, "protocol": 1,
                "cli_path": FAKE, "cwd": root, "unattached_grace_s": 3600}
        (self.sdir / "spawn.json").write_text(json.dumps(spec))
        (self.sdir / "spawn.json").chmod(0o600)
        self.pub = Path(root) / "hosts" / (sid[:8] + ".sock")

    def _reroot(self, total, sid=SID):
        """Move the state root to a padded directory so hosts/<sid8>.sock is exactly `total` BYTES long (padded_root: under
        the system temp dir, never a skip; a byte count, so a multibyte sid pads to the budget the bind measures)."""
        root = padded_root(self, total, os.path.join("hosts", sid[:8] + ".sock"))
        self._spec_at(root, sid)
        self.assertEqual(len(os.fsencode(str(self.pub))), total, str(self.pub))

    class _NoCli:
        """The CLI transport's stand-in: a CLI that never speaks and never exits until closed. close() marks the case's
        stand-in CLI gone (cli_start_now None), the way the real transport's close returns only once the CLI is dead, unless
        the case set cli_outlives_close: then close() returns and the CLI is still there, the case run()'s failure arm has
        to tell apart from the first without any word from the transport."""

        def __init__(self, case=None):
            self.closed = asyncio.Event()
            self.case = case

        async def read_messages(self):
            await self.closed.wait()
            return
            yield                                        # an async generator with no records

        async def write(self, data):
            pass

        async def end_input(self):
            pass

        async def close(self):
            self.closed.set()
            if self.case is not None and not self.case.cli_outlives_close:
                self.case.cli_start_now = None

    class _Limit(int):
        """SOCK_PATH_MAX's stand-in for the ordering pins: an int that reports each comparison the budget check makes.
        `n > SOCK_PATH_MAX` in _prepare_socket reaches this type's __lt__ first, since Python gives the reflected method
        of an int SUBCLASS on the right priority over int's own on the left, so the moment the budget is read is
        observable without a seam in the module; the value compares, prints and serialises as the int it wraps (a row's
        `limit` field is unchanged)."""

        def __new__(cls, value, on_compare):
            self = super().__new__(cls, value)
            self.on_compare = on_compare
            return self

        def __lt__(self, other):
            self.on_compare()
            return int(self) < other

        def __gt__(self, other):
            self.on_compare()
            return int(self) > other

    def _lease_on_disk(self):
        """Wire the recording lease stubs to the real lease FILE too (sb.write_lease and sb.remove_lease under the state
        root the host was given), so a pin can read the lease path, the thing the kernel's lease readers stat, and not
        only the stubs' record. Returns a callable giving that path for a sid (the root moves with _reroot)."""
        write, remove = self.lease_api["write_lease"], self.lease_api["remove_lease"]
        self.lease_api["write_lease"] = lambda sd, lease: (write(sd, lease), sb.write_lease(sd, lease))
        self.lease_api["remove_lease"] = lambda sd, sid: (remove(sd, sid), sb.remove_lease(sd, sid))
        return lambda sid=SID: sb.lease_path(self.root, sid)

    def _run_host(self, ready=None, cli_start="1", plant=None):
        """The real run() until `ready()` (default: the published path exists) or run() ends, then the stop. Returns
        (the published path's mode at that moment, or None when it did not exist; run()'s exit code, or the OSError run()
        raised on the bind road). The host stays on self.host for the checks after; the spawn stub writes the lease the
        real _spawn writes at its end, so the order run() has, the prelude (_prepare_socket) before the spawn and its
        lease, and the lease before the bind, is the order under test. `cli_start` is the identity the stub records for
        the stand-in CLI (None: proc_start read nothing, so no lease is written). `plant` runs AFTER the constructor and
        before run(): since round 3 (kernel-2, 2026-09-19) the constructor guards hosts/ before it opens the journal, so
        a case about the PRELUDE's guard (the row's step hosts-dir) plants its bad hosts/ here, between the two guards;
        a case that plants before construction is refused by the constructor and never reaches run()."""
        ready = ready or self.pub.exists
        host = self.host = sh.SessionHost(str(self.sdir / "spawn.json"), lease_api=self.lease_api)
        if plant is not None:
            plant()

        async def _spawn():
            self.spawn_calls += 1
            host.transport = self._NoCli(self)
            host.cli_pid, host.cli_start, host.cli_spawned_at = CLI_PID, cli_start, int(host.now())
            host.log("cli-spawned", transport="stand-in", cliPid=host.cli_pid)      # the row the real _spawn writes, so the
            host._write_lease()                                                      # rows' order is the real host's
        host._spawn = _spawn

        async def go():
            task = asyncio.ensure_future(host.run())
            deadline = time.time() + 10
            while not ready() and not task.done() and time.time() < deadline:   # loop-ok: a bounded wait on the socket appearing
                await asyncio.sleep(0.005)
            mode = stat.S_IMODE(os.stat(self.pub).st_mode) if self.pub.exists() else None
            if host._stop is not None:
                host._stop.set()
            try:
                return mode, await asyncio.wait_for(task, 15)
            except OSError as e:
                return mode, e
        with mock.patch.object(sh, "EXIT_FLUSH_S", 0.05):          # no attached kernel to flush to
            mode, rc = asyncio.run(go())
        self._read_log()
        return mode, rc

    def _read_log(self):
        log = self.sdir / "host.log"
        self.host_log = [json.loads(l) for l in log.read_text().splitlines()] if log.exists() else []
        self.rows = {r["kind"]: r for r in self.host_log}

    def _temps(self):
        return sorted(p.name for p in self.pub.parent.glob("*.tmp"))

    def _assert_temp_name(self, name):
        self.assertEqual(sh.temp_owner_pid(name), os.getpid(), "the temp embeds this process's pid: %s" % name)
        self.assertEqual(len(name), len(self.pub.name), "and is exactly the published name's length: %s" % name)

    def test_the_socket_is_owner_only_before_it_is_published(self):
        """The creation-mode pin: the temp the host binds is already 0600 as os.rename publishes it."""
        moves = []
        real_rename = os.rename

        def rename(src, dst, *a, **k):
            moves.append((Path(src), Path(dst), stat.S_IMODE(os.stat(src).st_mode)))
            return real_rename(src, dst, *a, **k)
        with mock.patch.object(os, "rename", rename):
            mode, rc = self._run_host()
        self.assertEqual(rc, 0, self.host_log[-3:])
        self.assertEqual(len(moves), 1, "the host binds a temp and renames it onto hosts/<sid8>.sock; a host that bound the "
                         "published path itself served it at the umask's mode until its chmod (the code before 2026-09-18)")
        src, dst, at_move = moves[0]
        self.assertEqual(dst, self.pub)
        self.assertEqual(src.parent, self.pub.parent, "the temp is the published name's sibling in hosts/")
        self._assert_temp_name(src.name)
        self.assertEqual(at_move, 0o600, "the mode the published path is born with, under a 000 umask")
        self.assertEqual(mode, 0o600, "and the mode at the first sighting of the published path")
        self.assertFalse(src.exists(), "the temp name is gone once published")
        self.assertFalse(self.pub.exists(), "run()'s exit unlinks the published path as before (asyncio's close never did)")
        self.assertEqual(self.lease_calls, ["write", "remove"], "the lease written at the spawn, removed at the exit")

    def test_the_published_path_is_born_0600_and_no_chmod_ever_touches_it(self):
        tightened = []
        real_chmod = os.chmod

        def chmod(path, mode, *a, **k):
            tightened.append((Path(path), mode))
            return real_chmod(path, mode, *a, **k)
        with mock.patch.object(os, "chmod", chmod):
            mode, rc = self._run_host()
        self.assertEqual(rc, 0, self.host_log[-3:])
        self.assertNotIn(self.pub, [p for p, _ in tightened],
                         "no chmod on the published path: a tightening after the bind is the window itself")
        socks = [t for t in tightened if t[0] != self.pub.parent]
        self.assertEqual(len(socks), 1, ("one chmod of a socket path, the temp beside the published name", tightened))
        self.assertEqual((socks[0][0].parent, socks[0][1]), (self.pub.parent, 0o600))
        self._assert_temp_name(socks[0][0].name)
        self.assertEqual([t for t in tightened if t[0] == self.pub.parent], [(self.pub.parent, 0o700)],
                         "and one of hosts/ itself, to 0700 from the 0777 setUp left it at (hosts_dir, before the bind)")
        self.assertLess(tightened.index((self.pub.parent, 0o700)), tightened.index(socks[0]),
                        "the directory is owner-only before anything is bound in it")
        self.assertEqual(mode, 0o600, "0600 at the first sighting of hosts/<sid8>.sock, under a 000 umask")
        self.assertIn("socket-ready", self.rows)
        self.assertNotIn("socket-bind-failed", self.rows)
        ready = self.rows["socket-ready"]
        self.assertEqual((ready["sock"], ready["pathLen"]), (self.pub.name, len(os.fsencode(str(self.pub)))))
        self._assert_temp_name(ready["tmp"])

    def test_the_published_path_first_exists_at_the_rename_and_not_before_the_bind(self):
        """The mode cases read the published path at its first SIGHTING, a poll between the loop's turns, so a placeholder
        the prelude left at the published path (a touch, 0666 under this umask) from before the bind until the rename
        replaced it passed every one of them: the rename lands in the same turn as the bind's one yield, ahead of the poll
        (the mutation pass of round 1, 2026-09-19). Pinned at the two calls instead: nothing stands at the published path
        when start_unix_server is called, and nothing stands there when os.rename is called, so the rename is the first
        thing to put a path there, after the listen and at 0600, and the exists-before-listen gap the spawning kernel's
        poll would otherwise fall into stays closed."""
        seen = []
        real_rename, real_start = os.rename, asyncio.start_unix_server

        def rename(src, dst, *a, **k):
            if Path(dst) == self.pub:
                seen.append(("rename", os.path.lexists(dst)))
            return real_rename(src, dst, *a, **k)

        async def start(*a, **k):
            seen.append(("bind", os.path.lexists(self.pub)))
            return await real_start(*a, **k)
        with mock.patch.object(os, "rename", rename), mock.patch.object(asyncio, "start_unix_server", start):
            mode, rc = self._run_host()
        self.assertEqual(rc, 0, self.host_log[-3:])
        self.assertEqual(seen, [("bind", False), ("rename", False)],
                         "nothing at the published name at the bind and nothing at the rename: the rename creates it")
        self.assertEqual(mode, 0o600, "and 0600 at the first sighting")

    def _temp_mode_at_its_chmod(self):
        """Run the host under the umask already set and return (the temp's mode as stat read it the instant before its
        chmod, the published path's mode at its first sighting): the measured facts, not the calls made."""
        before = []
        real_chmod = os.chmod

        def chmod(path, mode, *a, **k):
            before.append((Path(path), stat.S_IMODE(os.lstat(path).st_mode), mode))
            return real_chmod(path, mode, *a, **k)
        with mock.patch.object(os, "chmod", chmod):
            mode, rc = self._run_host()
        self.assertEqual(rc, 0, self.host_log[-3:])
        temps = [b for b in before if b[0].parent == self.pub.parent and b[0] != self.pub and b[0].name.endswith(".tmp")]
        self.assertEqual(len(temps), 1, before)
        self.assertEqual(temps[0][2], 0o600)
        return temps[0][1], mode

    def test_under_the_umask_the_live_host_runs_at_the_temp_is_group_writable_until_its_chmod(self):
        """The bind gives the temp the umask's mode, and the live session hosts on this box run at umask 002 (three pids
        read from /proc, 2026-09-19), so the temp stands GROUP-WRITABLE, 0775, from the bind to the chmod; the write bit
        is the permission an AF_UNIX connect needs. The first cut's docstring named the umask as a guard on that window,
        saying that either 002 or 022 already masks the group and other write bits a connect needs; that holds for 022
        and fails for 002, the umask we run, so the window rests on the mode of hosts/ alone. Measured by stat at the chmod, never inferred
        from the call having been made (the review of this fix, 2026-09-19)."""
        os.umask(0o002)                                 # setUp's cleanup restores the process umask
        at_chmod, published = self._temp_mode_at_its_chmod()
        self.assertEqual(at_chmod, 0o775, "under umask 002 the temp is group-writable until its chmod")
        self.assertEqual(published, 0o600, "and the published path is 0600 at its first sighting regardless")

    def test_under_umask_022_the_temp_has_no_group_or_other_write_but_is_group_and_other_readable(self):
        """The companion measurement: 022 masks both write bits, so the first cut's claim held for that umask and for
        that one only. Neither umask is the guard; hosts/ is."""
        os.umask(0o022)
        at_chmod, published = self._temp_mode_at_its_chmod()
        self.assertEqual(at_chmod, 0o755)
        self.assertEqual(published, 0o600)

    def test_a_stale_published_path_and_a_dead_hosts_temp_are_replaced_and_a_live_hosts_temp_is_left(self):
        """A socket file an earlier host left at the published path (its process gone) is replaced, not served: the stale
        handling the bind had before the temp-and-rename shape, kept. Temps are writer-unique now, so the prelude sweeps
        by owner instead of unlinking one fixed name: a temp whose embedded pid is gone is unlinked (a host killed between
        its bind and its rename), one whose pid is alive is another host's mid-bind and is left alone, and a name whose
        form this code did not mint is not touched (the review of this fix, 2026-09-19, the shared-name hazard)."""
        self.pub.parent.mkdir(parents=True, exist_ok=True)
        stale = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        stale.bind(str(self.pub))
        stale.close()
        stale_ino = os.stat(self.pub).st_ino
        gone = subprocess.Popen([sys.executable, "-c", "pass"])
        gone.wait(timeout=30)                           # reaped: its pid names no process
        live = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"])
        self.addCleanup(live.wait, 30)
        self.addCleanup(live.kill)
        dead_temp = sh._b32(gone.pid, 5) + "0000.tmp"
        live_temp = sh._b32(live.pid, 5) + "0000.tmp"
        for name in (dead_temp, live_temp, "stray.tmp"):
            (self.pub.parent / name).write_text("a temp")
        self.assertEqual((sh.temp_owner_pid(dead_temp), sh.temp_owner_pid(live_temp), sh.temp_owner_pid("stray.tmp")),
                         (gone.pid, live.pid, None))
        mode, rc = self._run_host(ready=lambda: self.pub.exists() and os.stat(self.pub).st_ino != stale_ino)
        self.assertEqual(rc, 0, self.host_log[-3:])
        self.assertEqual(mode, 0o600, "the new socket, born 0600, stands at the published path")
        self.assertEqual(self._temps(), sorted([live_temp, "stray.tmp"]),
                         "the dead owner's temp is swept; a live owner's and a foreign name are left")
        self.assertFalse(self.pub.exists(), "and run()'s exit removed the published path")

    def test_a_dead_hosts_published_socket_is_gone_at_the_bind_and_not_left_standing_by_a_refusal(self):
        """The prelude's unlink of a dead host's published socket, pinned where it acts (the mutation pass of round 1,
        2026-09-19: on the success road the rename replaces a stale socket whether or not the prelude removed it, so the
        replacement case above held with the unlink deleted). Two moments the rename cannot supply. At the bind, the
        published path is already clear. And when the publish fails after the prelude (here the temp's chmod, refused with
        EACCES, which also names the `chmod` step in the row), the refusal leaves nothing at the published path: not this
        host's socket, which it never published, and not the dead host's, which a kernel probing the path would otherwise
        find there refusing every connect."""
        stale = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        stale.bind(str(self.pub))
        stale.close()
        at_bind = []
        real_start, real_chmod = asyncio.start_unix_server, os.chmod

        async def start(*a, **k):
            at_bind.append(os.path.lexists(self.pub))
            return await real_start(*a, **k)

        def chmod(path, mode, *a, **k):
            if Path(path).parent == self.pub.parent and Path(path).name.endswith(".tmp"):
                raise PermissionError(errno.EACCES, "the temp's chmod, refused for the test")
            return real_chmod(path, mode, *a, **k)
        with mock.patch.object(asyncio, "start_unix_server", start), mock.patch.object(os, "chmod", chmod):
            mode, rc = self._run_host(ready=lambda: False)
        self.assertEqual(at_bind, [False], "the dead host's socket is gone before the bind")
        self._assert_refused(rc, "chmod", "PermissionError", errno.EACCES, at="test_session_host.py:")
        self.assertFalse(os.path.lexists(self.pub), "the refusal leaves the published path clear: the dead host's socket is not left standing")

    def test_a_temp_whose_live_owner_is_another_uids_process_is_left_alone(self):
        """The sweep's third arm (the mutation pass of round 1, 2026-09-19: the dead, live and stray cases above leave it
        unreached). Signal 0 at a live process of another uid is refused with EPERM, a PermissionError and not a
        ProcessLookupError, and a temp whose owner answers that way is not ours to judge: the owner is alive, mid-bind for
        all this host can tell, so the temp is left. The probe is real: pid 1 is the process every pid namespace has, and
        below root it refuses our signal 0 (a run as root, where it does not, skips)."""
        try:
            os.kill(1, 0)
        except PermissionError:
            pass
        else:
            self.skipTest("pid 1 takes this process's signal 0 (running as root?): no live owner of another uid to probe with")
        foreign = sh._b32(1, 5) + "0000.tmp"
        (self.pub.parent / foreign).write_text("a temp")
        self.assertEqual(sh.temp_owner_pid(foreign), 1)
        mode, rc = self._run_host()
        self.assertEqual(rc, 0, self.host_log[-3:])
        self.assertEqual(mode, 0o600, "the host published regardless")
        self.assertEqual(self._temps(), [foreign], "the foreign owner's temp is left: alive, and not ours to judge")

    def test_two_hundred_dead_owner_temps_are_swept_in_one_launch_so_the_sweep_has_no_per_launch_cap(self):
        """The sweep's stated non-behaviour, pinned (the mutation pass of round 3, 2026-09-19: _sweep_stale_temps's
        docstring says there is no per-launch cap on the sweep, and no test could red a cap, since no case planted more
        than three temps). Two hundred temps whose owners are gone, the count the docstring's cost figure was measured
        at, are all swept by the one launch, so a cap below that count leaves the rest standing and reds here. The
        owners are pids above 2^22, Linux's largest pid_max (and far above macOS's), so each names no process, which the
        case checks with the sweep's own probe before the run. The glob that reads hosts/ is shown reading it by counting
        the two hundred back before the launch: an empty listing after it is the sweep's work, not an unreadable
        directory's answer (glob returns nothing for a directory it cannot read)."""
        pids = range(2 ** 22 + 1, 2 ** 22 + 201)
        for pid in pids:
            with self.assertRaises(ProcessLookupError, msg="pid %d names a process: not a dead owner" % pid):
                os.kill(pid, 0)
        names = sorted(sh._b32(pid, 5) + "0000.tmp" for pid in pids)
        self.assertEqual(len(names), 200)
        for name in names:
            (self.pub.parent / name).write_text("a temp")
        self.assertEqual(self._temps(), names, "two hundred dead owners' temps stand in hosts/, and the listing reads them all")
        mode, rc = self._run_host()
        self.assertEqual(rc, 0, self.host_log[-3:])
        self.assertEqual(mode, 0o600, "the host published regardless")
        self.assertEqual(self._temps(), [], "every dead owner's temp is gone after the one launch: no per-launch cap")

    def test_the_temp_name_is_writer_unique_and_the_published_names_length(self):
        """The length proof and the identity proof (the review of this fix, 2026-09-18 and 2026-09-19): the socket path
        budget is sun_path (SOCK_PATH_MAX, 107 usable bytes on Linux), the published path IS that budget on the sweep's
        deepest xdist root, so the temp is never longer than the published name; and the temp embeds this process's pid
        and random digits, so two hosts never share a temp name and a rename can only publish the socket its own host
        bound. Two earlier shapes were longer (a temp inside hosts/<sid>/, then a 0700 directory beside the socket) and
        failed the bind at the budget; the first cut's fixed `<sid8>.tmp` was the shared name."""
        for sid in ("12345678", SID, "web.1.x.y", "f" * 40):        # every sid of at least 8 characters, the kernel's uuids among them
            pub, tmp = sh.sock_names(sid)
            self.assertEqual(pub, sid[:8] + ".sock", "the published name the kernel's host_sock builds too")
            self.assertEqual(len(tmp), len(pub), (sid, pub, tmp))
            self.assertEqual(os.path.dirname(tmp), os.path.dirname(pub), "the same directory: no extra component")
            self.assertEqual(sh.temp_owner_pid(tmp), os.getpid(), tmp)
        # Writer-uniqueness BY CONSTRUCTION, not by sample (the review's round 2, 2026-09-19: the first pin drew 64 random
        # 20-bit fields and asserted them all distinct, which the birthday bound makes false about one run in 520, a test
        # that reds with no code change). Across processes the pid digits differ: five base-32 digits hold 2^25 values,
        # every pid up to pid_max (2^22) maps to its own string and parses back. Within one process the random field is
        # read fresh from os.urandom on every call: with urandom returning 64 distinct top-20-bit values (the code drops
        # the low nibble of three bytes, so the values differ above that nibble) the 64 names are the 64 expected ones,
        # and a cached or dropped read would collapse them, deterministically.
        for a, b in ((1, 2), (4194303, 4194304), (os.getpid(), os.getpid() + 1)):
            self.assertNotEqual(sh._b32(a, 5), sh._b32(b, 5), "distinct pids, distinct digits")
            self.assertEqual((int(sh._b32(a, 5), 32), int(sh._b32(b, 5), 32)), (a, b), "and each parses back")
        self.assertEqual(sh._b32(4194304, 5), "40000", "pid_max's largest pid fits the five digits")
        draws = iter((i << 4).to_bytes(3, "big") for i in range(64))
        with mock.patch.object(os, "urandom", lambda n: next(draws)):
            names = [sh.sock_names(SID)[1] for _ in range(64)]
        self.assertEqual(names, [sh._b32(os.getpid(), 5) + sh._b32(i, 4) + ".tmp" for i in range(64)],
                         "the random field is read fresh on every call and lands in the four digits after the pid's")
        self.assertEqual(len(set(names)), 64)
        self.assertTrue(all(n[:5] == sh._b32(os.getpid(), 5) and n.endswith(".tmp") and len(n) == 13 for n in names), names)
        for raw, digits in ((b"\xff\xff\xff", "vvvv"), (b"\x00\x00\x00", "0000"), (b"\xff\xff\xf0", "vvvv"), (b"\x00\x00\x0f", "0000")):
            with mock.patch.object(os, "urandom", lambda n, raw=raw: raw):
                self.assertEqual(sh.sock_names(SID)[1], sh._b32(os.getpid(), 5) + digits + ".tmp",
                                 "20 bits exactly: the largest field fills four digits and never a fifth, and the low nibble is dropped")
        pub, tmp = sh.sock_names(SID)
        root = "/" + "r" * (sh.SOCK_PATH_MAX - len(os.path.join(os.sep, "hosts", pub)) - 1)     # the longest root the published path allows
        full_pub, full_tmp = os.path.join(root, "hosts", pub), os.path.join(root, "hosts", tmp)
        self.assertEqual(len(full_pub), sh.SOCK_PATH_MAX, "the published path at the budget")
        self.assertLessEqual(len(full_tmp), len(full_pub), "and the temp within it")
        host = sh.SessionHost(str(self.sdir / "spawn.json"), lease_api=self.lease_api)
        self.addCleanup(host.journal.close)
        self.assertEqual(host.sock_path.name, pub, "the host publishes this name")
        self._assert_temp_name(host.sock_tmp.name)
        self.assertEqual(host.sock_tmp.parent, host.sock_path.parent)

    def test_hosts_is_owner_only_once_the_host_binds(self):
        """The guard on the temp during its life at the umask's mode is `hosts/`, the directory it is bound in, and that
        directory's mode is set by code (sh.hosts_dir), not by the umask of whoever created it (the pre-round of this fix,
        2026-09-19). The host's road: a `hosts/` planted at 0755 (an old install's, made by a kernel before the fix) is
        0700 once the host has bound its socket, under the 000 umask setUp installs. The kernel's road is pinned by
        tests/test_host_transport.py SpawnSpec.test_hosts_is_owner_only_by_code_and_a_loose_one_is_tightened."""
        hosts = self.pub.parent
        os.chmod(hosts, 0o755)
        self.assertEqual(stat.S_IMODE(os.stat(hosts).st_mode), 0o755, "planted loose")
        seen = []
        mode, rc = self._run_host(ready=lambda: self.pub.exists() and not seen.append(stat.S_IMODE(os.stat(hosts).st_mode)))
        self.assertEqual(rc, 0, self.host_log[-3:])
        self.assertEqual(mode, 0o600)
        self.assertEqual(seen[:1], [0o700], "hosts/ is 0700 by the time the published path exists")
        self.assertEqual(stat.S_IMODE(os.stat(hosts).st_mode), 0o700, "and stays so after the host's exit")
        self.assertEqual(stat.S_IMODE(os.stat(self.sdir).st_mode), 0o700, "hosts/<sid>/ untouched at 0700")

    PRELUDE_STEPS = ("hosts-dir", "budget", "prelude")     # _prepare_socket's steps, run before the CLI is spawned
    SERVE_STEPS = ("bind-hosts", "bind", "chmod", "rename")  # _serve_socket's, run after the spawn and its lease (bind-hosts:
    #                                                          round 4's lstat of hosts/ immediately before the bind, 2026-09-20)

    def _assert_refused(self, rc, step, error, errno_=None, at="session_host.py:"):
        """The loud road, whole: the row names the step, nothing is bound or published, no temp is left in hosts/, no
        lease is kept and the journal is closed. TWO REFUSAL CLASSES since round 3 (the reviewer's reorder ruling,
        2026-09-19), told apart by the step the row names, so a case cannot claim one class and be satisfied by the
        other's bookkeeping: a PRELUDE refusal (hosts-dir, budget, prelude: _prepare_socket, which run() calls before
        the CLI is spawned) has started nothing, so no lease was ever written (lease_calls []), there is no transport
        and no cli-spawned row; a refusal AFTER the spawn (bind, chmod, rename: _serve_socket) ran with the spawn's lease
        on disk, so that lease is removed once the stand-in CLI's close marks it gone (lease_calls ["write", "remove"])
        and the CLI stand-in was closed. Through round 2 every refusal was of the second class, since the whole road ran
        after the spawn; the seven prelude cases re-pointed here read [] where they used to read ["write", "remove"].
        `at` is the file the row's frame names: the raiser's (_where reads the innermost frame), so session_host.py for
        the checks of our own, asyncio's unix_events.py for the bind's, and this file's for a failure a test's stand-in
        raised."""
        self.assertIsInstance(rc, OSError, (rc, self.host_log[-3:]))
        self.assertIn("socket-bind-failed", self.rows, self.host_log)
        row = self.rows["socket-bind-failed"]
        self.assertEqual((row["step"], row["error"], row.get("errno")), (step, error, errno_), row)
        self.assertEqual((row["pathLen"], row["limit"]), (len(os.fsencode(str(self.pub))), sh.SOCK_PATH_MAX), row)
        self.assertTrue(row["at"].startswith(at), row)
        self.assertNotIn("text", row, "the error's text, which carries the path, is never logged")
        self.assertNotIn("socket-ready", self.rows)
        self.assertFalse(self.pub.exists() and not self.pub.is_dir(), "no socket at the published path")
        self.assertEqual(self._temps(), [], "no temp left in hosts/")
        self.assertIn(step, self.PRELUDE_STEPS + self.SERVE_STEPS, "every step of the road belongs to one half of it")
        if step in self.PRELUDE_STEPS:
            self.assertEqual(self.lease_calls, [], "a prelude refusal precedes the spawn: no lease was ever written")
            self.assertIsNone(self.host.transport, "and no CLI was started: there is no transport")
            self.assertIsNone(self.host.cli_pid, "no CLI identity was recorded")
            self.assertNotIn("cli-spawned", self.rows, "and no cli-spawned row was written")
        else:
            self.assertEqual(self.lease_calls, ["write", "remove"], "the lease written at the spawn is removed on the failure")
            self.assertTrue(self.host.transport.closed.is_set(), "the CLI was ended with the host")
        self.assertEqual(self.leases, {}, "no lease is kept")
        self.assertIsNone(self.host.journal._fh, "and the journal is closed with it (run()'s failure arm for this half of the road)")

    def _bind_refused_root(self):
        """A root where the BIND refuses, for real, after the spawn and its lease: the published path at exactly the
        budget with a three-character sid, so sock_names gives a temp (13 bytes) longer than the published name
        (`web.sock`, 8) and over the budget; the prelude passes (the published path fits), the spawn runs, and
        start_unix_server raises CPython's "AF_UNIX path too long" at the temp (the shape
        test_a_temp_over_the_budget_fails_the_bind_and_the_row_names_that_step pins). The post-spawn failure cases moved
        here in round 3 from the budget refusal they used, which precedes the spawn now. Returns the sid."""
        self._reroot(sh.SOCK_PATH_MAX, sid="web")
        return "web"

    def _refused_by(self, fact, plant, restore, rc, step, error, errno_, at):
        """One class-specific fact _assert_refused reads, falsified ALONE in the case's or the host's bookkeeping by
        `plant`: the helper fails and its message names the fact; `restore` puts the bookkeeping back and the helper
        passes again (the accept twin, in the same subtest)."""
        with self.subTest(fact=fact):
            plant()
            try:
                with self.assertRaises(AssertionError, msg="the helper is satisfied with this fact false") as ctx:
                    self._assert_refused(rc, step, error, errno_, at=at)
            finally:
                restore()
            self.assertIn(fact, str(ctx.exception), "the helper names the fact it failed on")
            self._assert_refused(rc, step, error, errno_, at=at)

    def test_a_prelude_refusal_is_not_satisfied_by_the_post_spawn_classs_bookkeeping_on_any_fact_the_helper_reads(self):
        """_assert_refused against its refusable inputs, the prelude class (the mutation pass of round 3, 2026-09-19:
        the helper's docstring says a case cannot claim one refusal class and be satisfied by the other's bookkeeping,
        and no test held it to that, so its prelude branch replaced by `pass` left the module green while the seven
        prelude cases that assert through it alone lost their no-lease, no-transport, no-identity and no-cli-spawned
        checks). A real budget refusal, then each of the four facts the prelude branch reads falsified alone, in the
        recording stubs or on the host: the helper fails naming that fact, and passes once it is restored."""
        self._reroot(sh.SOCK_PATH_MAX + 1)
        mode, rc = self._run_host()
        self.assertIsNone(mode)
        prelude = (rc, "budget", "OSError", errno.ENAMETOOLONG, "session_host.py:")
        self._assert_refused(*prelude[:4], at=prelude[4])
        host = self.host
        self._refused_by("no lease was ever written", lambda: self.lease_calls.extend(["write", "remove"]), self.lease_calls.clear, *prelude)
        self._refused_by("no CLI was started", lambda: setattr(host, "transport", self._NoCli()), lambda: setattr(host, "transport", None), *prelude)
        self._refused_by("no CLI identity was recorded", lambda: setattr(host, "cli_pid", CLI_PID), lambda: setattr(host, "cli_pid", None), *prelude)
        self._refused_by("no cli-spawned row", lambda: self.rows.__setitem__("cli-spawned", {"kind": "cli-spawned"}),
                         lambda: self.rows.pop("cli-spawned"), *prelude)

    def test_a_post_spawn_refusal_is_not_satisfied_by_the_prelude_classs_bookkeeping_on_either_fact_the_helper_reads(self):
        """The other class (the same pass): a real bind refusal after the spawn and its lease, then the two facts the
        post-spawn branch reads falsified alone, the lease's removal (the calls read as a prelude refusal's, nothing
        written) and the CLI stand-in's close: the helper fails naming each, and passes once it is restored."""
        self._bind_refused_root()
        mode, rc = self._run_host()
        self.assertIsNone(mode)
        served = (rc, "bind", "OSError", None, "unix_events.py:")
        self._assert_refused(*served[:4], at=served[4])
        host = self.host
        self._refused_by("the lease written at the spawn is removed", self.lease_calls.clear,
                         lambda: self.lease_calls.extend(["write", "remove"]), *served)
        self._refused_by("the CLI was ended with the host", host.transport.closed.clear, host.transport.closed.set, *served)

    def test_a_published_path_one_byte_over_the_budget_is_refused_before_anything_is_bound(self):
        """The high of round 1 (2026-09-19): binding a temp moved the bind's sun_path check onto the temp's name, so at a
        published path of exactly SOCK_PATH_MAX + 1 bytes (108 on Linux) the first cut bound the temp, renamed it onto
        the over-budget published path, logged socket-ready and kept its lease and its CLI while nothing could ever
        connect, where the code before failed the bind loudly. Now the published path's length is checked first and the
        loud road runs whole: the socket-bind-failed row (step budget, ENAMETOOLONG, the length and the limit), no bind
        at all, no socket, no temp, no lease, no CLI."""
        self._reroot(sh.SOCK_PATH_MAX + 1)
        binds = []
        real = asyncio.start_unix_server

        async def start(*a, **k):
            binds.append(k.get("path"))
            return await real(*a, **k)
        with mock.patch.object(asyncio, "start_unix_server", start):
            mode, rc = self._run_host()
        self.assertEqual(binds, [], "nothing was bound: the check comes before the bind")
        self.assertIsNone(mode)
        self._assert_refused(rc, "budget", "OSError", errno.ENAMETOOLONG)
        self.assertEqual(self.rows["socket-bind-failed"]["pathLen"], sh.SOCK_PATH_MAX + 1)
        self.assertEqual(rc.errno, errno.ENAMETOOLONG)

    def test_a_published_path_at_exactly_the_budget_is_served_and_a_client_connects(self):
        """The other direction of the same pin, in-process: at SOCK_PATH_MAX bytes exactly (the sweep's deepest root) the
        host binds its temp (which is the same length), publishes 0600, logs socket-ready with both names, and a client
        connect through the published path completes."""
        self._reroot(sh.SOCK_PATH_MAX)
        connected = []

        def ready():
            if not self.pub.exists():
                return False
            c = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                c.connect(str(self.pub))                # completes against the listen backlog without an accept
                connected.append(stat.S_IMODE(os.stat(self.pub).st_mode))
            finally:
                c.close()
            return True
        mode, rc = self._run_host(ready=ready)
        self.assertEqual(rc, 0, self.host_log[-3:])
        self.assertEqual((mode, connected), (0o600, [0o600]), "served 0600 and connectable at the budget")
        ready_row = self.rows["socket-ready"]
        self.assertEqual(ready_row["pathLen"], sh.SOCK_PATH_MAX)
        self.assertLessEqual(len(ready_row["tmp"]), len(ready_row["sock"]), ready_row)
        self.assertNotIn("socket-bind-failed", self.rows)

    MB_SID = "ü" * 8 + "-2222-3333-4444-0000000000b1"      # eight two-byte characters first: 13 characters, 21 bytes of name

    def _connects(self):
        """A ready() for _run_host that connects through the published path once it exists and records the mode it read."""
        connected = []

        def ready():
            if not self.pub.exists():
                return False
            c = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                c.connect(str(self.pub))
                connected.append(stat.S_IMODE(os.stat(self.pub).st_mode))
            finally:
                c.close()
            return True
        return ready, connected

    def test_the_budget_is_measured_in_bytes_a_multibyte_published_path_over_it_in_bytes_alone_is_refused(self):
        """The byte measure, pinned where it differs from the character count (the review's round 2, 2026-09-19: the owner's
        mutation pass set a str-length pathLen aside as equivalent, and it is not: both modules stayed green under it, and
        for a sid whose first eight characters are multibyte it publishes an unreachable socket with a socket-ready row,
        round 1's high back). A published path of SOCK_PATH_MAX + 1 bytes and fewer than SOCK_PATH_MAX characters: the
        check refuses it before the bind, the row's pathLen is the byte length, and the temp (13 bytes, shorter than this
        published name's 21) would have bound where the published path cannot be connected to. The UTF-8 precondition is
        ASSERTED (require_utf8_names), not a skip: through round 2 both multibyte cases sat behind a skipUnless, so a
        runner without a two-byte name character reported the module green with the byte measure, this PR's only pin on
        round 1's high, unpinned (round 3, M3)."""
        require_utf8_names(self)
        self._reroot(sh.SOCK_PATH_MAX + 1, sid=self.MB_SID)
        self.assertLess(len(str(self.pub)), sh.SOCK_PATH_MAX, "fewer characters than the budget, more bytes: the separating case")
        binds = []
        real = asyncio.start_unix_server

        async def start(*a, **k):
            binds.append(k.get("path"))
            return await real(*a, **k)
        with mock.patch.object(asyncio, "start_unix_server", start):
            mode, rc = self._run_host()
        self.assertEqual(binds, [], "nothing was bound: the byte length is what the check reads")
        self.assertIsNone(mode)
        self._assert_refused(rc, "budget", "OSError", errno.ENAMETOOLONG)
        self.assertEqual(self.rows["socket-bind-failed"]["pathLen"], len(os.fsencode(str(self.pub))))
        self.assertEqual(self.rows["socket-bind-failed"]["pathLen"], sh.SOCK_PATH_MAX + 1)

    def test_a_multibyte_published_path_at_the_budget_in_bytes_is_served_and_a_client_connects(self):
        """The mirror: exactly SOCK_PATH_MAX bytes (fewer characters), served 0600 and connectable, the ready row's pathLen
        the byte length. With the case above, the check is pinned to bytes in both directions; the UTF-8 precondition is
        asserted, never skipped (require_utf8_names, round 3)."""
        require_utf8_names(self)
        self._reroot(sh.SOCK_PATH_MAX, sid=self.MB_SID)
        self.assertLess(len(str(self.pub)), sh.SOCK_PATH_MAX)
        ready, connected = self._connects()
        mode, rc = self._run_host(ready=ready)
        self.assertEqual(rc, 0, self.host_log[-3:])
        self.assertEqual((mode, connected), (0o600, [0o600]), "served 0600 and connectable at the budget in bytes")
        self.assertEqual(self.rows["socket-ready"]["pathLen"], sh.SOCK_PATH_MAX)
        self.assertNotIn("socket-bind-failed", self.rows)

    def test_the_lease_stays_when_close_returns_with_the_cli_alive_and_goes_once_the_cli_is_confirmed_gone(self):
        """run()'s failure arm and the lease (the review's round 2, 2026-09-19): round 1 removed the lease as soon as
        transport.close() returned, and a returning close is not proof the CLI is gone (nor is the transport's word: the SDK
        transport has no returncode attribute, so the module's _cli_alive reads a live SDK CLI as gone). The lease is what
        the kernel's orphan road waits on, so it goes only once the CLI is confirmed gone by pid and start-time identity
        (proc_start, the lease's own reader). Three stand-ins for the CLI after close() returned: still there (the same
        start), gone (no start), and a pid the kernel reused (a different start). The trigger is a BIND refusal
        (_bind_refused_root) since round 3: through round 2 this case reached the failure arm through the budget
        refusal, and the budget check precedes the spawn now, so a budget refusal has no CLI and no lease to decide
        about; the lease-kept logic this case protects is unchanged and applies to the bind, the chmod and the rename,
        the steps that still run after the lease (the reviewer's reorder ruling, 2026-09-19)."""
        self.cli_outlives_close = True                  # close() returns; proc_start still reports the spawn's start for CLI_PID
        sid = self._bind_refused_root()
        mode, rc = self._run_host()
        self.assertIsInstance(rc, OSError)
        self.assertEqual(self.rows["socket-bind-failed"]["step"], "bind", "the bind refused, after the spawn and its lease")
        self.assertEqual(self.lease_calls, ["write"], "written at the spawn and NOT removed: the CLI is unconfirmed")
        self.assertEqual(self.leases[sid]["pid"], CLI_PID, "the lease still names the CLI the kernel's orphan road will wait on")
        kept = self.rows["lease-kept"]
        self.assertEqual(sorted(k for k in kept if k not in ("t", "kind")), ["cliPid"], "the kind and the CLI's pid, nothing else: no path")
        self.assertEqual(kept["cliPid"], CLI_PID)
        self.assertTrue(self.host.transport.closed.is_set(), "the CLI was still asked to end")
        self.assertNotIn("socket-ready", self.rows)
        self.assertEqual(self._temps(), [], "the loud road otherwise ran whole: no temp left")
        kinds = [r["kind"] for r in self.host_log]
        self.assertLess(kinds.index("cli-spawned"), kinds.index("socket-bind-failed"), "the CLI was spawned before the refusal")
        self.assertLess(kinds.index("socket-bind-failed"), kinds.index("lease-kept"))
        # a pid the kernel reused: proc_start answers a different start for CLI_PID, so the CLI is gone even though a process answers
        self.setUp()
        self.cli_outlives_close, self.cli_start_now = True, "2"
        self._bind_refused_root()
        mode, rc = self._run_host()
        self._assert_refused(rc, "bind", "OSError", None, at="unix_events.py:")
        self.assertNotIn("lease-kept", self.rows)
        # gone for real: the default stand-in, whose close() leaves no process behind (the post-spawn refusal cases run this leg)
        self.setUp()
        self._bind_refused_root()
        mode, rc = self._run_host()
        self._assert_refused(rc, "bind", "OSError", None, at="unix_events.py:")
        self.assertIsNone(self.cli_start_now, "the stand-in's close marked the CLI gone before the lease decision")
        self.assertNotIn("lease-kept", self.rows)

    def test_a_symlink_at_the_session_directory_is_refused_by_the_journal_and_by_the_host_before_anything_is_written(self):
        """The host's own creator of hosts/<sid>/ (the review's round 2, 2026-09-19: round 1 put the checks on hosts/ and
        left this directory, made one line below by the kernel and again here by Journal.__init__, with a bare mkdir that
        followed a planted symlink and wrote the journal, host.log and identity.json through it). Journal(path) over a
        symlink raises and opens no segment through the link; SessionHost over a spec that resolves through such a link
        raises in its constructor, before host.log, identity.json or a journal exist in the target, so main() never runs a
        host over it. A regular directory beside it is unaffected."""
        target = Path(self.root) / "elsewhere"
        os.rename(self.sdir, target)                     # the spec moves with it; hosts/<sid>/ becomes a link to it
        self.sdir.symlink_to(target)
        before = sorted(p.name for p in target.iterdir())
        with self.assertRaises(OSError) as cm:
            sh.Journal(self.sdir)
        self.assertIn("host directory", str(cm.exception))
        self.assertIn("not a directory", str(cm.exception))
        with self.assertRaises(OSError) as cm:
            sh.SessionHost(str(self.sdir / "spawn.json"), lease_api=self.lease_api)
        self.assertIn("not a directory", str(cm.exception))
        self.assertEqual(sorted(p.name for p in target.iterdir()), before, "nothing written through the link: no journal, no host.log, no identity")
        self.assertEqual(before, ["spawn.json"])
        self.assertTrue(self.sdir.is_symlink(), "the link is left, not replaced")
        ok = Path(self.root) / "hosts" / "22222222-2222-3333-4444-0000000000a2"
        ok.mkdir(mode=0o700)
        j = sh.Journal(ok)
        self.addCleanup(j.close)
        self.assertEqual(stat.S_IMODE(os.lstat(ok).st_mode), 0o700, "a directory of ours is taken, and kept owner-only")

    def test_a_symlinked_hosts_is_refused_in_the_constructor_before_the_journal_host_log_or_identity_exist(self):
        """kernel-2 (review round 3, 2026-09-19): the host's first guard of hosts/ is in its constructor, above the
        journal, so a hosts/ that is a symlink is refused before the journal opens a segment, before run() writes host.log
        and identity.json, and before any CLI is spawned. Through round 2 that guard ran only at the socket road, and a
        host over a symlinked hosts/ wrote all three files through the link and spawned a real CLI before it refused at
        the bind, about 660 ms later; the kernel's write_spawn_spec guards the same directory before its first write, and
        the host was the outlier. Both plants, hosts/ and hosts/<sid>/, driven the same way: planted BEFORE construction,
        the constructor raises naming the directory by its noun, and the link's target holds exactly what was there
        before, the planted spawn.json: no journal-0.jsonl, no host.log, no identity.json, no lease, nothing bound. The
        refusal is the road the PR already shipped for a symlinked hosts/<sid>/: a constructor raise, which main() does
        not catch, so the process exits 1 with the traceback on its captured stderr and no host.log row (HostProcess
        drives the real process; PreludeRefusalRead reads that exit from the kernel's side)."""
        for shape in ("hosts", "session-dir"):
            with self.subTest(shape=shape):
                if shape != "hosts":
                    self.setUp()
                target = Path(self.root) / "elsewhere"
                if shape == "hosts":
                    hosts = self.pub.parent
                    os.rename(hosts, target)
                    hosts.symlink_to(target)
                    inside, noun = target / SID, "hosts directory"
                else:
                    os.rename(self.sdir, target)
                    self.sdir.symlink_to(target)
                    inside, noun = target, "host directory"
                self.assertEqual(sorted(p.name for p in inside.iterdir()), ["spawn.json"], "the planted shape: the spec alone")
                with self.assertRaises(OSError) as cm:
                    sh.SessionHost(str(self.sdir / "spawn.json"), lease_api=self.lease_api)
                self.assertIn(noun, str(cm.exception), "refused by the guard on that directory, by its noun")
                self.assertIn("is not a directory", str(cm.exception))
                self.assertEqual(sorted(p.name for p in inside.iterdir()), ["spawn.json"],
                                 "nothing written through the link: no journal segment, no host.log, no identity.json")
                self.assertEqual(sorted(p.name for p in target.rglob("*.jsonl")), [], "no segment anywhere under the target")
                self.assertEqual(self.lease_calls, [], "no lease: no CLI was ever spawned")
                self.assertEqual(self.spawn_calls, 0)
                self.assertFalse(self.pub.exists() and not self.pub.is_dir(), "nothing published")
                self.assertEqual(self._temps(), [], "nothing bound")

    def test_a_temp_over_the_budget_fails_the_bind_and_the_row_names_that_step(self):
        """The bind's own failure, reached for real, and the step the row names for it (the mutation pass of round 1,
        2026-09-19: every refusal case failed before the bind or after it, so a bind failure reported under the prelude's
        name passed them all). sock_names gives a sid shorter than eight characters a temp longer than its published
        name (13 bytes against `web.sock`'s 8; not a shape the kernel mints, as its docstring says), so with the published
        path at exactly SOCK_PATH_MAX the budget check passes and the bind refuses the temp: CPython's "AF_UNIX path too
        long", an OSError with no errno. The row says `bind` with the published path's length within the limit, which is
        what tells a reader the temp overran and not the path the kernel connects to; the loud road runs whole."""
        self._reroot(sh.SOCK_PATH_MAX, sid="web")
        binds = []
        real = asyncio.start_unix_server

        async def start(*a, **k):
            binds.append(k.get("path"))
            return await real(*a, **k)
        with mock.patch.object(asyncio, "start_unix_server", start):
            mode, rc = self._run_host()
        self.assertIsNone(mode)
        self.assertEqual(len(binds), 1, "the bind was attempted: the published path passed the budget check")
        tmp = Path(binds[0])
        self.assertEqual((tmp.parent, sh.temp_owner_pid(tmp.name)), (self.pub.parent, os.getpid()), tmp)
        self.assertGreater(len(os.fsencode(str(tmp))), sh.SOCK_PATH_MAX, "the temp overran the budget; the published path did not")
        self._assert_refused(rc, "bind", "OSError", None, at="unix_events.py:")
        self.assertIn("too long", str(rc), "the bind's own refusal, not a check of ours")
        self.assertIn("create_unix_server", self.rows["socket-bind-failed"]["at"], "the frame is asyncio's bind, a basename and no path")

    def test_a_hosts_that_is_a_symlink_is_refused_before_the_bind(self):
        """hosts_dir's lstat (the judge scratch precedent, taken whole in round 1): a symlink planted at hosts/ is refused
        with the row's step hosts-dir, and its target's mode is not touched through the link. The link is planted AFTER
        the constructor (round 3, kernel-2: the constructor guards hosts/ too, and a link planted before it is refused
        there with no row, the case below), so this case pins the prelude's guard, the one that catches a hosts/
        re-pointed while the host runs."""
        hosts = self.pub.parent
        target = Path(self.root) / "elsewhere"

        def plant():
            os.rename(hosts, target)                    # the session directory and spec move with it; the spec path resolves through the link
            os.chmod(target, 0o755)
            hosts.symlink_to(target)
        mode, rc = self._run_host(plant=plant)
        self._assert_refused(rc, "hosts-dir", "OSError")
        self.assertTrue(hosts.is_symlink(), "the link is left, not replaced")
        self.assertEqual(stat.S_IMODE(os.stat(target).st_mode), 0o755, "the target's mode untouched: no chmod through the link")

    def test_a_tighten_of_hosts_that_does_not_take_is_refused_not_reported_as_done(self):
        """hosts_dir reads the mode back after its chmod (the precedent's second check, dropped by the first cut): with
        os.chmod a no-op, a loose hosts/ stays loose and the host refuses with the row instead of binding into it."""
        hosts = self.pub.parent
        self.assertEqual(stat.S_IMODE(os.stat(hosts).st_mode), 0o777, "setUp's shape under the 000 umask")
        real_chmod = os.chmod

        def plant():                                     # after the constructor's own tighten (round 3): loose again, and the
            real_chmod(hosts, 0o777)                     # chmod a no-op from here on, so the PRELUDE's read-back is what refuses
            patcher = mock.patch.object(os, "chmod", lambda *a, **k: None)
            patcher.start()
            self.addCleanup(patcher.stop)
        mode, rc = self._run_host(plant=plant)
        self._assert_refused(rc, "hosts-dir", "OSError")
        self.assertEqual(stat.S_IMODE(os.stat(hosts).st_mode), 0o777, "still loose, and the host said so rather than binding")

    def test_a_hosts_re_pointed_after_the_lease_and_before_the_bind_is_refused_at_the_bind_and_the_target_gets_no_socket(self):
        """extra6-1 (round 4 of the review, 2026-09-20): round 3 moved every hosts/ check ahead of the CLI's spawn, which
        put the spawn between the last check and the bind (about 1.1 s on the production road against 0.4 ms through
        round 2, both by strace in that round's review), so a hosts/ re-pointed in that stretch was followed by the bind
        where round 2's road refused it. _serve_socket now lstat's hosts/ immediately before start_unix_server. Planted at
        the last moment the sequence allows from outside, the lease write (the step before _serve_socket): hosts/ is
        renamed aside and a symlink put in its place pointing at the moved directory (so the host's own writes by path,
        its rows, still land where the case reads them). The bind is refused with step bind-hosts and errno ELOOP under
        the post-spawn class's bookkeeping (the lease written and removed, the CLI stand-in closed), start_unix_server is
        never called, and the link's target holds no socket and no temp. Red on the head before the guard: the bind
        followed the link, the socket was published in the target and the case read a served host. What remains is the
        bind's own window between this lstat and the bind, stated in _serve_socket's docstring."""
        hosts, target = self.pub.parent, Path(self.root) / "elsewhere"
        binds = []
        real_start = asyncio.start_unix_server

        async def start(*a, **k):
            binds.append(k.get("path"))
            return await real_start(*a, **k)
        write = self.lease_api["write_lease"]

        def plant(sd, lease):
            write(sd, lease)
            os.rename(hosts, target)                    # the session directory moves with it; the host's paths resolve through the link
            hosts.symlink_to(target)
        self.lease_api["write_lease"] = plant
        with mock.patch.object(asyncio, "start_unix_server", start):
            mode, rc = self._run_host()
        self.assertIsNone(mode, "nothing was published")
        self._assert_refused(rc, "bind-hosts", "OSError", errno.ELOOP)
        self.assertEqual(binds, [], "start_unix_server was never called: the lstat refused first")
        self.assertTrue(hosts.is_symlink(), "the link is left, not replaced")
        self.assertEqual(sorted(p.name for p in target.iterdir() if p.name.endswith((".sock", ".tmp"))), [], "the target holds no socket and no temp")
        self.assertEqual(self.lease_calls, ["write", "remove"], "the lease was written at the spawn and removed on the failure")

    def test_the_bind_guard_refuses_a_non_directory_a_foreign_uid_and_a_group_world_hosts(self):
        """extra6-1's guard at the bind has four refusals (kernel/session_host.py _serve_socket, step
        bind-hosts): a symlink (ELOOP), a non-directory (ENOTDIR), another uid's (EPERM) and a
        group/world-accessible one (EPERM). The re-pointed case above drives the symlink arm; the other
        three were held by no case (the mutation lens's F1 on round 5 of the review, 2026-09-20). Each arm
        here doctors os.lstat's ANSWER for hosts/ at the bind alone, the shape StateRootByHostsDir uses,
        armed at the lease write so the prelude's own hosts_dir check has already passed on the real
        directory: the guard reads a regular file, a foreign uid, or a 0755 directory, refuses with step
        bind-hosts and the arm's errno, and start_unix_server is never called. The doctored value is read
        BACK from the object the guard stats (the lstat's return), never asserted from a picture. Red with
        the matching arm deleted from the guard: the doctored value passes and the socket is published."""
        for arm, doctor, errcls, err in (
            # OSError(errno, msg) is constructed as the errno's subclass, so ENOTDIR reads as NotADirectoryError
            # and EPERM as PermissionError; ELOOP (the re-pointed case above) has no subclass and stays OSError
            ("not-a-directory", lambda st: os.stat_result((stat.S_IFREG | 0o700,) + tuple(st)[1:]), "NotADirectoryError", errno.ENOTDIR),
            ("foreign-uid", lambda st: os.stat_result(tuple(st)[:4] + (st.st_uid + 1,) + tuple(st)[5:]), "PermissionError", errno.EPERM),
            ("group-world", lambda st: os.stat_result((stat.S_IFDIR | 0o755,) + tuple(st)[1:]), "PermissionError", errno.EPERM),
        ):
            with self.subTest(arm=arm):
                self.setUp()
                hosts = self.pub.parent
                binds, armed = [], []
                real_start, real_lstat = asyncio.start_unix_server, os.lstat

                async def start(*a, **k):
                    binds.append(k.get("path"))
                    return await real_start(*a, **k)

                def lstat(path, *a, _doctor=doctor, **k):
                    st = real_lstat(path, *a, **k)
                    if armed and not isinstance(path, int) and os.fspath(path) == os.fspath(hosts):
                        return _doctor(st)                       # the guard's own lstat of hosts/, and only that
                    return st
                write = self.lease_api["write_lease"]

                def plant(sd, lease, _write=write):
                    _write(sd, lease)
                    armed.append(True)                           # from the lease write on: the prelude has already passed
                self.lease_api["write_lease"] = plant
                with mock.patch.object(asyncio, "start_unix_server", start), mock.patch.object(os, "lstat", lstat):
                    mode, rc = self._run_host()
                self.assertIsNone(mode, "nothing was published")
                self._assert_refused(rc, "bind-hosts", errcls, err)
                self.assertEqual(binds, [], "start_unix_server was never called: the guard refused first")

    def test_a_failed_publish_closes_the_listening_socket_it_bound(self):
        """The except arm's server.close() (the mutation pass of round 1, 2026-09-19: the rename-failure case below checks
        the rows, the temp, the lease and the CLI, and a listening socket left open behind an unlinked temp is invisible
        to all four). The server is captured as start_unix_server returns it, the rename is made to fail (a non-empty
        directory at the published path, that case's shape), and afterwards the server is not serving and its listening
        descriptor is closed: a host that could not publish holds no socket, not even one bound to a name that is gone."""
        self.pub.mkdir()
        (self.pub / "keep").write_text("not a socket")
        servers = []
        real = asyncio.start_unix_server

        async def start(*a, **k):
            server = await real(*a, **k)
            servers.append((server, server.sockets[0]))          # the listening descriptor, held so its close can be read
            return server
        with mock.patch.object(asyncio, "start_unix_server", start):
            mode, rc = self._run_host(ready=lambda: False)
        self.assertEqual(len(servers), 1)
        server, listening = servers[0]
        self.assertFalse(server.is_serving(), "the server the bind returned is closed on the failure")
        self.assertEqual(listening.fileno(), -1, "and its listening descriptor with it")
        self._assert_refused(rc, "rename", "IsADirectoryError", errno.EISDIR)
        self.assertTrue(self.pub.is_dir(), "the planted directory is left")

    def test_a_bind_failure_writes_no_path_into_host_log_through_either_row(self):
        """host.log carries no spec field, and the state root is one: the first cut's socket-bind-failed row logged the
        error's text, and an OSError's text carries the path it failed on, so a rename that failed wrote the root's
        absolute path into the log; main()'s host-crashed row did the same through the traceback's last line (the review
        of this fix, 2026-09-19). Both rows now carry the class, the frame and the numbers only. Driven through the real
        main() so the host-crashed row is the one main writes, over a root whose path carries a marker, with a non-empty
        directory planted at the published path so the rename is the leg that fails (the prelude's unlink cannot remove a
        directory, and asyncio's own bind removes only a socket)."""
        marker = "m4rk3r" + uuid.uuid4().hex[:6]
        # under the system temp dir (system_tmp), not the run's private root: the case exists to force the RENAME leg, and
        # a published path over the budget (a deep run root plus this marker) is refused at the budget check before it,
        # so the leg never ran on a long-temp runner (the review's round 2, 2026-09-19)
        root = tempfile.mkdtemp(prefix=marker + "-", dir=system_tmp())
        self.addCleanup(shutil.rmtree, root, True)
        self._spec_at(root)
        self.assertLessEqual(len(os.fsencode(str(self.pub))), sh.SOCK_PATH_MAX,
                             "within the budget, so the rename is the leg that fails; the system temp dir %s is too deep: run the suite "
                             "under a shorter TMPDIR (a failure, not a skip, so a green module means this ran)" % system_tmp())
        self.pub.mkdir()
        (self.pub / "keep").write_text("not a socket")
        stub = self._NoCli(self)

        async def _spawn(host):
            host.transport = stub
            host.cli_pid, host.cli_start, host.cli_spawned_at = CLI_PID, "1", int(host.now())
            host._write_lease()
        with mock.patch.object(sh.SessionHost, "_spawn", _spawn), mock.patch.object(sh, "_lease_api", lambda: self.lease_api):
            rc = sh.main([str(self.sdir / "spawn.json")])
        self.assertEqual(rc, 1)
        self._read_log()
        text = (self.sdir / "host.log").read_text()
        self.assertNotIn(marker, text, "no row carries the root's path")
        self.assertNotIn(root, text)
        row = self.rows["socket-bind-failed"]
        self.assertEqual((row["step"], row["error"], row["errno"]), ("rename", "IsADirectoryError", errno.EISDIR), row)
        self.assertNotIn("text", row)
        crashed = self.rows["host-crashed"]
        self.assertEqual(crashed["error"], "IsADirectoryError", crashed)
        self.assertTrue(crashed["at"].startswith("session_host.py:"), crashed)
        # the errno rides too since round 3 (fresh-1: the base carried it and round 1's redaction dropped it). The privacy
        # invariant is that no spec field and no error TEXT reaches the log; an integer errno is neither, so the key set
        # widens by exactly that one field, and the case below pins that only an int ever fills it
        self.assertEqual(crashed["errno"], errno.EISDIR, crashed)
        self.assertEqual(sorted(k for k in crashed if k not in ("t", "kind")), ["at", "errno", "error"], "the class, the errno and the frame, nothing else")
        self.assertEqual(self._temps(), [], "the bound temp was unlinked on the failure")
        self.assertTrue(self.pub.is_dir(), "the planted directory is left; the host removes only what it made")
        self.assertEqual(self.leases, {})
        self.assertTrue(stub.closed.is_set(), "the CLI was ended with the host")

    def test_the_host_crashed_row_carries_an_integer_errno_only_and_never_a_path_valued_one(self):
        """main()'s errno guard against its refusable inputs (round 3, fresh-1, 2026-09-19). Three exceptions out of run(),
        each through the real main(): an OSError with an integer errno, which the row carries (ENOSPC here); an exception
        that is not an OSError but carries an .errno attribute holding a path, which is never read (the field is absent
        and the path is nowhere in the log); and an OSError built with two positional arguments, OSError(path, text),
        whose .errno IS the path (CPython's constructor puts the first argument there), which the int check keeps out:
        a guard typed on the exception alone would have logged that path, since log() passes a str through, and the
        privacy pin above would not have seen it (its rename failure carries an int). The row's other fields are the
        class and the frame as before."""
        marker = "m4rk3r" + uuid.uuid4().hex[:6]

        class Odd(Exception):
            pass
        odd = Odd("not an OSError")
        odd.errno = "/%s/an-attribute-that-happens-to-be-called-errno" % marker
        shapes = (("an OSError with an int errno", OSError(errno.ENOSPC, "no space left"), errno.ENOSPC),
                  ("a non-OSError with a path-valued .errno", odd, None),
                  ("a two-argument OSError whose .errno is the path", OSError("/%s/the-path" % marker, "text"), None))
        for name, exc, want in shapes:
            with self.subTest(shape=name):
                if exc is not shapes[0][1]:
                    self.setUp()

                async def run(host, exc=exc):        # out of run(), into main()'s except arm; the journal closed as run()'s arms do
                    host.journal.close()
                    raise exc
                with mock.patch.object(sh.SessionHost, "run", run), mock.patch.object(sh, "_lease_api", lambda: self.lease_api):
                    rc = sh.main([str(self.sdir / "spawn.json")])
                self.assertEqual(rc, 1)
                self._read_log()
                crashed = self.rows["host-crashed"]
                self.assertEqual(crashed["error"], type(exc).__name__, crashed)
                self.assertEqual(crashed.get("errno"), want, crashed)
                self.assertEqual(sorted(k for k in crashed if k not in ("t", "kind")), ["at", "errno", "error"] if want is not None else ["at", "error"], crashed)
                text = (self.sdir / "host.log").read_text()
                self.assertNotIn(marker, text, "no path reaches the log through the errno field")
                self.assertNotIn("text", crashed)

    def test_hosts_is_0700_and_ours_at_the_instant_of_the_bind_and_a_refused_hosts_is_never_bound_into(self):
        """The one guard on the temp during its window is the mode of hosts/, so hosts/ is 0700 and ours BEFORE anything
        is bound in it (the mutation pass of round 2, 2026-09-19: with hosts_dir moved to after the bind and before the
        temp's chmod, its step label kept, every case stayed green, the chmod-order pin included, since hosts/ was still
        tightened ahead of the temp's chmod). Two legs, both at exactly the budget under the system temp dir, so the bind
        runs wherever the run's root is. At the start_unix_server call, hosts/ (planted 0777, setUp's shape) already
        reads 0700, a directory, ours. And a hosts/ the guard refuses (a symlink) is never bound into: no
        start_unix_server call at all, the row's step hosts-dir."""
        self._reroot(sh.SOCK_PATH_MAX)
        hosts = self.pub.parent
        self.assertEqual(stat.S_IMODE(os.lstat(hosts).st_mode), 0o777, "planted loose, the shape an old install's kernel left")
        at_bind, binds = [], []
        real = asyncio.start_unix_server

        async def start(*a, **k):
            st = os.lstat(hosts)
            at_bind.append((stat.S_IMODE(st.st_mode), stat.S_ISDIR(st.st_mode), st.st_uid == os.geteuid()))
            binds.append(k.get("path"))
            return await real(*a, **k)
        with mock.patch.object(asyncio, "start_unix_server", start):
            mode, rc = self._run_host()
        self.assertEqual(rc, 0, self.host_log[-3:])
        self.assertEqual(len(binds), 1, "the bind ran, at the budget")
        self.assertEqual(at_bind, [(0o700, True, True)], "hosts/ is 0700, a directory and ours as the bind is called")
        self.assertEqual(mode, 0o600)
        self.assertIn("socket-ready", self.rows)
        # a hosts/ the guard refuses is never bound into (the closure reads the names rebound below); planted after the
        # constructor, whose own guard would otherwise refuse it first (round 3, kernel-2)
        self.setUp()
        self._reroot(sh.SOCK_PATH_MAX)
        hosts = self.pub.parent
        target = Path(self.root) / "elsewhere"

        def plant():
            os.rename(hosts, target)
            hosts.symlink_to(target)
        at_bind, binds = [], []
        with mock.patch.object(asyncio, "start_unix_server", start):
            mode, rc = self._run_host(plant=plant)
        self.assertEqual(binds, [], "nothing was bound: the guard refused before the bind")
        self._assert_refused(rc, "hosts-dir", "OSError")
        self.assertEqual(sorted(p.name for p in target.iterdir()), [SID], "nothing reached the link's target but the planted session directory")

    def test_hosts_is_made_ours_before_the_budget_is_read_so_the_directorys_refusal_outranks_the_budgets(self):
        """The road's step order, hosts-dir then budget (the mutation pass of round 2, 2026-09-19: with hosts_dir moved
        to after the budget check every case stayed green, the over-budget cases refusing at the budget as before and
        the hosts/ cases binding within it). The directory is the guard on everything below it, so it is made ours
        first, and the row names the first fault on the road. Two legs, both one byte over the budget under the system
        temp dir: a loose hosts/ (0777, setUp's shape) is 0700 once the budget has refused, tightened before the check
        read the length; and a hosts/ the guard refuses (a symlink) makes the row say hosts-dir, not budget."""
        self._reroot(sh.SOCK_PATH_MAX + 1)
        hosts = self.pub.parent
        self.assertEqual(stat.S_IMODE(os.lstat(hosts).st_mode), 0o777, "planted loose")
        # loosened again after the constructor's own tighten (round 3, kernel-2), so the 0700 read after the refusal is
        # the PRELUDE's doing, ahead of its budget check
        mode, rc = self._run_host(plant=lambda: os.chmod(hosts, 0o777))
        self._assert_refused(rc, "budget", "OSError", errno.ENAMETOOLONG)
        self.assertEqual(stat.S_IMODE(os.lstat(hosts).st_mode), 0o700, "tightened before the budget check refused")
        self.setUp()
        self._reroot(sh.SOCK_PATH_MAX + 1)
        hosts = self.pub.parent
        target = Path(self.root) / "elsewhere"

        def plant():
            os.rename(hosts, target)
            hosts.symlink_to(target)
        mode, rc = self._run_host(plant=plant)
        self._assert_refused(rc, "hosts-dir", "OSError")
        self.assertEqual(self.rows["socket-bind-failed"]["pathLen"], sh.SOCK_PATH_MAX + 1,
                         "over the budget too, and the directory's refusal is the one the row names")

    def test_with_no_cli_identity_recorded_the_cli_reads_as_gone_and_the_failure_arm_keeps_no_lease(self):
        """_cli_gone's no-identity arm (the mutation pass of round 2, 2026-09-19: every failure case records the stand-in's
        identity at the spawn, so an arm answering False for a missing one was never reached). With no CLI pid, or a pid
        whose start time proc_start could not read, _write_lease wrote no lease, so there is nothing for the kernel's
        orphan road to wait on and nothing to keep: the CLI reads as gone. Direct, over each shape of the missing identity
        and the three recorded ones; then through run()'s post-spawn failure arm (a bind refusal, _bind_refused_root: the
        budget refusal this leg used through round 2 precedes the spawn since round 3, so it never records an identity
        at all) with a spawn stub whose proc_start read nothing and a stand-in CLI that outlives its close: no lease was
        written, none is reported kept, no lease-kept row."""
        host = sh.SessionHost(str(self.sdir / "spawn.json"), lease_api=self.lease_api)
        self.addCleanup(host.journal.close)
        for pid, start in ((None, None), (None, "1"), (CLI_PID, None), (CLI_PID, "")):
            host.cli_pid, host.cli_start = pid, start
            self.assertTrue(host._cli_gone(), (pid, start))
        for pid, start in ((None, None), (None, "1"), (CLI_PID, None)):    # proc_start answers a string or None, never ""
            host.cli_pid, host.cli_start = pid, start
            host._write_lease()
        self.assertEqual(self.lease_calls, [], "no identity, no lease: _write_lease writes none")
        # the two methods test the identity with the SAME predicate, `is None` (round 3, correctness-5: _cli_gone read
        # `not self.cli_start`, which agreed with _write_lease only because proc_start never answers ""). A start of "" is
        # an identity to both: _write_lease writes a lease naming it, and _cli_gone compares it with what proc_start
        # answers instead of reading it as "no identity", so with the identity still matching the CLI is NOT confirmed
        # gone, and the lease-kept arm never removes a lease _write_lease wrote
        host.cli_pid, host.cli_start = CLI_PID, ""
        self.cli_start_now = ""
        self.assertFalse(host._cli_gone(), "a start the identity still matches is not gone, whatever its truth value")
        host._write_lease()
        self.assertEqual(self.lease_calls, ["write"], "and _write_lease wrote a lease for that same identity: one predicate at both sites")
        self.assertEqual(self.leases[SID]["start"], "")
        self.lease_calls.clear()
        self.leases.clear()
        self.cli_start_now = "1"
        host.cli_pid, host.cli_start = CLI_PID, "1"
        self.assertFalse(host._cli_gone(), "the recorded start still names the process: alive")
        self.cli_start_now = "2"
        self.assertTrue(host._cli_gone(), "a different start: the pid was reused, the CLI is gone")
        self.cli_start_now = None
        self.assertTrue(host._cli_gone(), "no process at the pid: gone")
        self.cli_start_now, self.cli_outlives_close = "1", True
        self._bind_refused_root()
        mode, rc = self._run_host(cli_start=None)
        self.assertIsInstance(rc, OSError)
        self.assertEqual(self.rows["socket-bind-failed"]["step"], "bind", "a refusal after the spawn: the arm that reads the identity")
        self.assertIn("cli-spawned", self.rows, "the CLI was spawned before the refusal")
        self.assertNotIn("write", self.lease_calls, "no identity at the spawn, so no lease was written")
        self.assertNotIn("lease-kept", self.rows, "and none is reported kept: there is nothing for the orphan road to wait on")
        self.assertEqual(self.leases, {})
        self.assertTrue(self.host.transport.closed.is_set(), "the CLI was still asked to end")
        self.assertEqual(self._temps(), [])

    def test_the_failure_arm_closes_the_journal_before_the_error_leaves_run(self):
        """run()'s failure arms close the journal the constructor opened (the mutation pass of round 2, 2026-09-19: with
        that close removed every refusal case stayed green, an open segment descriptor being invisible to the rows, the
        temps, the lease and the CLI). After the refusal the journal holds no descriptor, the descriptor it held is closed,
        and no descriptor of this process names the segment file (read from /proc where there is one): a host that could
        not publish leaves no open file behind. Every refusal case reads the same fact through _assert_refused since this
        pin. Two legs since round 3, one per failure arm: the prelude's (a budget refusal, before the CLI) and the
        post-spawn one (a bind refusal, _bind_refused_root), since the reorder gave run() two arms and a close dropped
        from either would leave the descriptor open on that half of the road."""
        for arm, plant, step, error, errno_, at in (("prelude", lambda: self._reroot(sh.SOCK_PATH_MAX + 1), "budget", "OSError", errno.ENAMETOOLONG, "session_host.py:"),
                                                   ("post-spawn", self._bind_refused_root, "bind", "OSError", None, "unix_events.py:")):
            with self.subTest(arm=arm):
                if arm != "prelude":
                    self.setUp()
                plant()
                held = []
                mode, rc = self._run_host(ready=lambda: held.append(self.host.journal._fh) and False)
                self._assert_refused(rc, step, error, errno_, at=at)
                self.assertTrue(held and held[0] is not None, "the journal held an open segment while run() ran")
                self.assertTrue(held[0].closed, "and that descriptor is closed")
                self.assertIsNone(self.host.journal._fh)
                if os.path.isdir("/proc/self/fd"):
                    seg = os.path.realpath(self.sdir / "journal-0.jsonl")
                    named = []
                    for fd in os.listdir("/proc/self/fd"):
                        try:
                            named.append(os.readlink(os.path.join("/proc/self/fd", fd)))
                        except OSError:
                            pass
                    self.assertNotIn(seg, named, "no descriptor of this process names the segment")

    def test_no_lease_exists_at_any_prelude_step_and_the_prelude_runs_before_the_spawn(self):
        """The reorder's first half, pinned at the moments (round 3, the reviewer's ruling of 2026-09-19): at the instant
        each prelude step runs, hosts_dir, the budget compare, the dead socket's unlink and the stale-temp sweep, no lease
        exists anywhere (the stubs' record empty, the lease FILE absent, read_lease None) and no CLI has been started (no
        transport, no pid), and the four run in that order before the lease write, which precedes the bind; at the bind
        the lease is on disk and a CLI stands behind it (the CLI-before-socket order, kept). Through round 2 the same four
        steps ran with the spawn's lease on disk, inside _serve_socket. Interposed, not read: sh.hosts_dir and
        _sweep_stale_temps are wrapped, the published path's unlink is caught at Path.unlink and at os.unlink (one snapshot
        whichever way this Python's pathlib reaches os.unlink: 3.10 bound it in its accessor at import, so a patched
        os.unlink alone never saw the kernel's Path.unlink there and CI's 3.10 cell was red on this step while 3.11 to
        3.13 were green; the glob wrapper of the next case documents the same class for os.scandir), and the budget
        compare is caught by an int subclass standing in for SOCK_PATH_MAX (_Limit). The constructor's own hosts_dir call (kernel-2,
        the same round) is the first snapshot, taken before self.host exists and labelled so. Red under the mutation that
        calls _prepare_socket after _spawn (round 2's order): every prelude snapshot then shows the lease and the CLI."""
        lease_file = self._lease_on_disk()
        seen, depth = [], [0]

        def snap(step):
            host = getattr(self, "host", None)          # None inside the constructor: the guard runs before the host is bound
            seen.append((step, list(self.lease_calls), dict(self.leases), lease_file().exists(),
                         sb.read_lease(self.root, SID), host.transport if host else None, host.cli_pid if host else None))
        real_hosts_dir, real_sweep, real_unlink, real_start = sh.hosts_dir, sh.SessionHost._sweep_stale_temps, os.unlink, asyncio.start_unix_server
        real_path_unlink = Path.unlink

        def hosts_dir(state_dir):
            snap("hosts-dir" if getattr(self, "host", None) is not None else "hosts-dir-constructor")
            return real_hosts_dir(state_dir)

        def sweep(host):
            snap("sweep")
            return real_sweep(host)

        def unlink(path, *a, **k):
            if depth[0] == 0 and Path(path) == self.pub:      # a direct os.unlink; one inside Path.unlink was snapped there
                snap("unlink-published")
            return real_unlink(path, *a, **k)

        def path_unlink(p, *a, **k):
            # pathlib's shape, interposed on the class beside os.unlink so the kernel's `self.sock_path.unlink()` is ONE
            # snapshot on every interpreter: Python 3.10's pathlib bound `unlink = os.unlink` in its accessor at import,
            # so a patched os.unlink never sees a Path.unlink there, where 3.11 and later look os.unlink up at call time.
            # The depth guard is the glob wrapper's: the call-time os.unlink inside this one is not snapped a second time.
            if Path(p) == self.pub:
                snap("unlink-published")
            depth[0] += 1
            try:
                return real_path_unlink(p, *a, **k)
            finally:
                depth[0] -= 1

        async def start(*a, **k):
            snap("bind")
            return await real_start(*a, **k)
        write = self.lease_api["write_lease"]
        self.lease_api["write_lease"] = lambda sd, lease: (write(sd, lease), snap("lease-write"))
        with mock.patch.object(sh, "hosts_dir", hosts_dir), mock.patch.object(sh.SessionHost, "_sweep_stale_temps", sweep), \
                mock.patch.object(os, "unlink", unlink), mock.patch.object(Path, "unlink", path_unlink), \
                mock.patch.object(asyncio, "start_unix_server", start), \
                mock.patch.object(sh, "SOCK_PATH_MAX", self._Limit(sh.SOCK_PATH_MAX, lambda: snap("budget"))):
            mode, rc = self._run_host()
        self.assertEqual(rc, 0, self.host_log[-3:])
        self.assertEqual(mode, 0o600)
        steps = [x[0] for x in seen]
        self.assertEqual(steps[:7], ["hosts-dir-constructor", "hosts-dir", "budget", "unlink-published", "sweep", "lease-write", "bind"],
                         "the constructor's guard, the four prelude steps, then the lease, then the bind: %r" % steps)
        for step, calls, leases, on_disk, read, transport, pid in seen[:5]:
            self.assertEqual((calls, leases, on_disk, read), ([], {}, False, None), "no lease anywhere at the %s step" % step)
            self.assertIsNone(transport, "and no CLI started at the %s step" % step)
            self.assertIsNone(pid)
        step, calls, leases, on_disk, read, transport, pid = seen[6]
        self.assertEqual((step, calls, on_disk, pid), ("bind", ["write"], True, CLI_PID), "at the bind the lease is on disk")
        self.assertEqual(read["pid"], CLI_PID, "and names the CLI")
        self.assertIsNotNone(transport, "which stands behind the socket the bind is about to serve")
        self.assertEqual(self.lease_calls, ["write", "remove"], "the success road's lease life is as before")

    def test_after_the_lease_write_only_the_bind_the_chmod_and_the_rename_run_and_hosts_is_listed_once(self):
        """The reorder's second half, the interval itself (round 3, the reviewer's ruling of 2026-09-19): between the lease
        write and the rename that publishes the socket, the interval the kernel's lease-keyed attach roads race, exactly
        two things happen, the bind of the temp and its chmod to 0600; in particular NO directory listing (os.scandir,
        os.listdir, Path.glob, Path.iterdir, of any directory), no prelude step (hosts_dir, the sweep, the published
        path's unlink) and no other chmod runs there. And hosts/ is listed exactly ONCE per launch overall, by the
        sweep's glob, before the lease. Through round 2 the glob sat inside that interval, which is what made the
        interval proportional to the entries in hosts/. Path.glob is wrapped to materialise its listing inside the
        wrapped call, so the os-level reads it makes (one os.scandir on a Python whose pathlib looks scandir up at call
        time; none visible where pathlib bound it at import) are attributed to it and counted as one listing. Path.unlink
        is wrapped the same way beside os.unlink, so each unlink the kernel makes through pathlib (the dead published
        socket's, a stale temp's, the failed bind's temp) is ONE event whichever way this Python's Path.unlink reaches
        os.unlink: 3.10 bound it at import, and with os.unlink patched alone the dead socket's unlink was invisible there
        (CI's 3.10 cell red on this case's last assertion, 3.11 to 3.13 green). Red under the mutation that puts a second
        sweep at the top of _serve_socket (a listing in the interval, two listings overall), under the one that calls
        _prepare_socket after _spawn (the prelude in the interval) and, on every interpreter, under the one that drops
        the prelude's dead-socket unlink."""
        events, depth, hosts = [], [0], self.pub.parent
        real = dict(glob=Path.glob, iterdir=Path.iterdir, scandir=os.scandir, listdir=os.listdir, chmod=os.chmod, rename=os.rename,
                    unlink=os.unlink, path_unlink=Path.unlink, hosts_dir=sh.hosts_dir, sweep=sh.SessionHost._sweep_stale_temps,
                    start=asyncio.start_unix_server)

        def glob(path, pattern, *a, **k):
            depth[0] += 1
            try:
                items = list(real["glob"](path, pattern, *a, **k))
            finally:
                depth[0] -= 1
            events.append(("list", "glob", Path(path)))
            return items

        def iterdir(path):
            events.append(("list", "iterdir", Path(path)))
            return real["iterdir"](path)

        def scandir(path=".", *a, **k):
            if depth[0] == 0:
                events.append(("list", "scandir", Path(path)))
            return real["scandir"](path, *a, **k)

        def listdir(path=".", *a, **k):
            if depth[0] == 0:
                events.append(("list", "listdir", Path(path)))
            return real["listdir"](path, *a, **k)

        def hosts_dir(state_dir):
            events.append(("prelude", "hosts-dir", None))
            return real["hosts_dir"](state_dir)

        def sweep(host):
            events.append(("prelude", "sweep", None))
            return real["sweep"](host)

        def unlink(path, *a, **k):
            if depth[0] == 0:                         # a direct os.unlink; one inside Path.unlink is that wrapper's event
                events.append(("unlink", "unlink", Path(path)))
            return real["unlink"](path, *a, **k)

        def path_unlink(p, *a, **k):
            # pathlib's shape, one event on every interpreter, under the glob wrapper's depth guard and for the reason it
            # gives for os.scandir: 3.10's pathlib bound os.unlink in its accessor at import, so a patched os.unlink never
            # sees a Path.unlink there, and 3.11 and later reach os.unlink at call time, which the guard keeps to one event
            events.append(("unlink", "unlink", Path(p)))
            depth[0] += 1
            try:
                return real["path_unlink"](p, *a, **k)
            finally:
                depth[0] -= 1

        async def start(*a, **k):
            events.append(("serve", "bind", Path(k.get("path"))))
            return await real["start"](*a, **k)

        def chmod(path, mode, *a, **k):
            temp = Path(path).parent == hosts and Path(path).name.endswith(".tmp")
            events.append(("serve" if temp else "chmod", "chmod", Path(path)))
            return real["chmod"](path, mode, *a, **k)

        def rename(src, dst, *a, **k):
            events.append(("serve", "rename", Path(dst)))
            return real["rename"](src, dst, *a, **k)
        write = self.lease_api["write_lease"]
        self.lease_api["write_lease"] = lambda sd, lease: (write(sd, lease), events.append(("lease", "write", None)))
        with mock.patch.object(Path, "glob", glob), mock.patch.object(Path, "iterdir", iterdir), \
                mock.patch.object(os, "scandir", scandir), mock.patch.object(os, "listdir", listdir), \
                mock.patch.object(os, "chmod", chmod), mock.patch.object(os, "rename", rename), mock.patch.object(os, "unlink", unlink), \
                mock.patch.object(Path, "unlink", path_unlink), \
                mock.patch.object(sh, "hosts_dir", hosts_dir), mock.patch.object(sh.SessionHost, "_sweep_stale_temps", sweep), \
                mock.patch.object(asyncio, "start_unix_server", start):
            mode, rc = self._run_host()
        self.assertEqual(rc, 0, self.host_log[-3:])
        self.assertEqual(mode, 0o600)
        write_i = events.index(("lease", "write", None))
        rename_i = next(i for i, e in enumerate(events) if e[:2] == ("serve", "rename") and e[2] == self.pub)
        self.assertLess(write_i, rename_i, "the lease precedes the publish")
        between = events[write_i + 1:rename_i]
        self.assertEqual([(k, w) for k, w, _ in between], [("serve", "bind"), ("serve", "chmod")],
                         "between the lease write and the publish: the bind and the temp's chmod, nothing else: %r" % (between,))
        self.assertEqual(len([e for e in between if e[0] in ("list", "prelude")]), 0, "no listing and no prelude step in the interval")
        listings = [e for e in events if e[0] == "list" and e[2] == hosts]
        self.assertEqual(len(listings), 1, "hosts/ is listed exactly once per launch: %r" % (listings,))
        self.assertEqual(listings[0][1], "glob", "by the sweep's glob")
        self.assertLess(events.index(listings[0]), write_i, "and before the lease")
        prelude = [i for i, e in enumerate(events) if e[0] == "prelude"]
        self.assertEqual([events[i][1] for i in prelude], ["hosts-dir", "hosts-dir", "sweep"],
                         "the constructor's guard (kernel-2), the prelude's, and the sweep: the wrapped steps, and no other")
        self.assertTrue(all(i < write_i for i in prelude), "all before the lease write")
        self.assertTrue(any(e[0] == "unlink" and e[2] == self.pub for e in events[:write_i]), "the dead socket's unlink too")

    def test_a_prelude_refusal_starts_no_cli_and_writes_no_lease(self):
        """What a refusal before the CLI leaves behind (round 3, the reviewer's ruling of 2026-09-19): over the budget and
        at a symlinked hosts/, run() raises out of _prepare_socket with the socket-bind-failed row naming the step, the
        spawn never ran (the stub was never called: no transport, no CLI identity, no cli-spawned row), no lease was ever
        written (the stubs' record empty and the lease FILE absent, so the kernel's orphan road finds nothing to wait on
        and nothing to recover), nothing is bound, no temp is left and the journal is closed. Through round 2 the same
        refusals came after the spawn: they ended a CLI and removed a lease that need never have existed. The kernel's
        spawn wait reading the exit this raise becomes is pinned over the real host process by PreludeRefusalRead. Red
        under the mutation that calls _prepare_socket after _spawn."""
        for shape in ("budget", "hosts-dir"):
            with self.subTest(shape=shape):
                if shape != "budget":
                    self.setUp()
                lease_file = self._lease_on_disk()
                plant = None
                if shape == "budget":
                    self._reroot(sh.SOCK_PATH_MAX + 1)
                else:
                    hosts, target = self.pub.parent, Path(self.root) / "elsewhere"

                    def plant(hosts=hosts, target=target):   # after the constructor's guard (round 3, kernel-2): the prelude's refusal
                        os.rename(hosts, target)
                        hosts.symlink_to(target)
                mode, rc = self._run_host(plant=plant)
                self.assertIsNone(mode, "nothing was published")
                if shape == "budget":
                    self._assert_refused(rc, "budget", "OSError", errno.ENAMETOOLONG)
                else:
                    self._assert_refused(rc, "hosts-dir", "OSError")
                self.assertEqual(self.spawn_calls, 0, "the spawn was never reached")
                self.assertIsNone(self.host.transport)
                self.assertEqual((self.host.cli_pid, self.host.cli_start, self.host.cli_spawned_at), (None, None, None), "no CLI identity")
                self.assertEqual(self.lease_calls, [], "no lease was ever written")
                self.assertFalse(lease_file().exists(), "and none is on disk")
                self.assertIsNone(sb.read_lease(self.root, SID))
                self.assertEqual([r["kind"] for r in self.host_log], ["host-started", "socket-bind-failed"],
                                 "the rows: started, refused, nothing about a CLI or a lease")


class SocketBudget(unittest.TestCase):
    def test_the_budget_is_derived_by_binding_and_the_connect_side_shares_it(self):
        """sh.SOCK_PATH_MAX is a documented number (sun_path less its NUL: 107 on Linux, 103 on macOS); this derives it by
        execution so the host's check is measured against the limit the kernel's connect actually hits (the review of this
        fix, 2026-09-19): a throwaway socket binds at every length from two under the constant to two over, the constant
        is the last length that binds, and a client connect at one over refuses before it reaches any server."""
        d = tempfile.mkdtemp(prefix="sb-", dir=system_tmp())     # the system temp dir, outside the run's private root: the
        self.addCleanup(shutil.rmtree, d, True)                  # lengths around the budget must be buildable on any runner
        shortest = len(os.fsencode(os.path.join(d, "p", "s")))
        self.assertLessEqual(shortest, sh.SOCK_PATH_MAX - 2, "the system temp dir %s is too deep to build paths around the "
                             "budget: run the suite under a shorter TMPDIR (a failure, not a skip, so a green module means this ran)" % system_tmp())

        def path_of(n):
            sub = os.path.join(d, "p" * (n - shortest + 1))
            os.makedirs(sub, exist_ok=True)
            p = os.path.join(sub, "s")
            self.assertEqual(len(os.fsencode(p)), n)
            return p
        binds = {}
        for n in range(sh.SOCK_PATH_MAX - 2, sh.SOCK_PATH_MAX + 3):
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                s.bind(path_of(n))
                binds[n] = True
            except OSError:
                binds[n] = False
            finally:
                s.close()
        self.assertEqual(binds, {sh.SOCK_PATH_MAX - 2: True, sh.SOCK_PATH_MAX - 1: True, sh.SOCK_PATH_MAX: True,
                                 sh.SOCK_PATH_MAX + 1: False, sh.SOCK_PATH_MAX + 2: False}, binds)
        c = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.addCleanup(c.close)
        with self.assertRaises(OSError) as cm:
            c.connect(path_of(sh.SOCK_PATH_MAX + 1))
        self.assertIn("too long", str(cm.exception), "the kernel side's connect refuses the same length")

    def test_the_budget_is_103_on_macos_by_the_expression_the_module_evaluates(self):
        """The platform arm (the mutation pass of round 2, 2026-09-19: with the darwin branch dropped, SOCK_PATH_MAX 107
        everywhere, this module stays green on Linux, where 107 is the measured limit, and only the macOS cell's run of
        the derivation above would say so). The assignment's own expression is taken from the module source and evaluated
        under each platform name: darwin gives 103 (sun_path is 104 bytes there, less its NUL), linux 107, and under this
        process's platform it gives the constant the module holds, so the expression read is the one in force."""
        src = Path(sh.__file__).read_text()
        node = next(n for n in ast.parse(src).body if isinstance(n, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == "SOCK_PATH_MAX" for t in n.targets))
        expr = compile(ast.Expression(body=node.value), sh.__file__, "eval")

        def under(platform):
            with mock.patch.object(sys, "platform", platform):
                return eval(expr, {"sys": sys})
        self.assertEqual(under("darwin"), 103, "macOS: sun_path is 104 bytes, 103 usable")
        self.assertEqual(under("linux"), 107, "Linux: sun_path is 108 bytes, 107 usable")
        self.assertEqual(under(sys.platform), sh.SOCK_PATH_MAX, "the expression read is the one the module evaluated")


class StateRootByHostsDir(unittest.TestCase):
    """kernel-7 (round 5 of the review, 2026-09-19; fixed at round 6; the tighten moved onto a descriptor at round 4 of the
    review of this head, 2026-09-20): the state root's mode when hosts_dir's parents=True makes it, READ BACK under five
    umasks (the runner's, 002, 022, 077 and 000) and never assumed. pathlib's Path.mkdir applies `mode` to the leaf alone
    and makes a missing parent with its default 0777 masked by the umask, so before the fix the root landed at the umask's
    mode (0775 under 002, 0755 under 022, 0700 under 077, 0777 under 000) while hosts/ below it was 0700 in every case;
    round 5 filed that as a finding and this class read the umask's mode back. The fix (hosts_dir's docstring) tightens
    the root this call made to 0700, on the create road alone: an lstat with owner_only_dir's three refusals, then the
    root OPENED O_DIRECTORY|O_NOFOLLOW, its fstat repeating the directory and uid refusals on the object opened, fchmod on
    that descriptor, and the read-back an fstat on the same descriptor. Pinned here: the root reads 0700 under every
    umask when hosts_dir made it, hosts/ 0700 below it, and the ancestor the parents mkdir made on the way keeps the
    umask's mode (the rejected alternative, tightening every missing ancestor, would red that read); a root pre-existing
    at 0755 or 0777 stays as planted with hosts/ 0700 below it, and no chmod and no fchmod names it (the create-only
    scope); a live symlink at the root's path takes the pre-existing road (exists() follows it, hosts/ is made 0700 under
    its target, the target is never read or tightened) while a link swapped in after the exists() read is refused at the
    lstat as not a directory with its target's MODE untouched (an empty hosts/ of ours, 0700, is made through the link
    by the parents mkdir before the lstat refuses, as the case below reads back); a link swapped in BETWEEN the lstat and the open (kernel-4,
    round 4) fails the open and is refused with its target's mode unchanged, where the chmod by path through round 6
    tightened the target first; a root another uid owns is refused before any mode call, whether the lstat or the
    descriptor's fstat reads the uid (regression-1 and kernel-2, round 4: the refusal was held by no test); the read-back
    is an fstat on the descriptor, so a stat or an lstat by path that disagrees is inert; and a read-back that disagrees
    is refused with the mode read and the remedy. Every mode here is read back from the object it was set on (lstat on the
    path, fstat on the descriptor), never asserted from a picture. Refusable, each run on a scratch copy: the fchmod
    removed reds the 002, 022 and 000 arms (077 stays green, the umask's mode being the code's there); an fchmod that does
    not take, or a stubbed fstat answering 0755 on the read-back, fires the refusal; the lstat's foreign-uid refusal
    deleted reds that case's lstat arm; the open's O_NOFOLLOW dropped reds the swapped-link case on the target's mode
    (the load-bearing refusal there); the tighten put back on the path (os.chmod for the fchmod) leaves that case GREEN,
    since the O_NOFOLLOW open refuses before any tighten runs, and reds the read-back and tightened-object cases instead
    through the fchmod spies (the round-5 modes lens, 2026-09-20, F3: the earlier wording conflated the two mutations)."""

    def _made_under(self, umask, root=None):
        """hosts_dir over a root not yet on disk, under `umask` (restored); the root's and hosts/'s modes as read back.
        The restore is try/finally around the one call and not addCleanup: the case below sets four umasks in one test
        and each must be back before the next is set and before the read-back, where addCleanup runs once, at the test's
        end (the lens's note on round 5, 2026-09-19; the raising road is pinned by the case after it). `root` names a
        root whose parent a case has planted; by default a fresh one under a fresh parent."""
        if root is None:
            base = tempfile.mkdtemp(prefix="sr-")
            self.addCleanup(shutil.rmtree, base, True)
            root = Path(base) / "state"
        # load-bearing (the lens's mutation M5 on round 5): a root already on disk at 0755 reads back 0755 under 022 too,
        # so without this line the 022 subtest cannot tell a root this call made from one that was there; the pin is
        # about creation, and this is what says the call created it (bypassed, the 022 subtest is blind; M4 shows it fires)
        self.assertFalse(root.exists())
        old = os.umask(umask)
        try:
            self.assertEqual(sh.hosts_dir(root), root / "hosts")
        finally:
            os.umask(old)
        return stat.S_IMODE(os.lstat(root).st_mode), stat.S_IMODE(os.lstat(root / "hosts").st_mode)

    @staticmethod
    def _ident(path, real_lstat=os.lstat):
        """(st_dev, st_ino) of the object at `path`, by the lstat given (the real one when a case has patched os.lstat)."""
        st = real_lstat(path)
        return (st.st_dev, st.st_ino)

    @contextlib.contextmanager
    def _mode_spies(self):
        """Every mode-setting call this class watches, recorded and performed: os.chmod by path as (path, mode) and
        os.fchmod by descriptor as ((st_dev, st_ino) of the descriptor's object, mode), so a case says WHICH object a mode
        went onto by identity, and a tighten that moved back onto a path, or onto the wrong object, is read as such."""
        chmods, fchmods = [], []
        real_chmod, real_fchmod, real_fstat = os.chmod, os.fchmod, os.fstat

        def chmod(path, mode, *a, **k):
            chmods.append((os.fspath(path), mode))
            return real_chmod(path, mode, *a, **k)

        def fchmod(fd, mode):
            st = real_fstat(fd)
            fchmods.append(((st.st_dev, st.st_ino), mode))
            return real_fchmod(fd, mode)
        with mock.patch.object(os, "chmod", chmod), mock.patch.object(os, "fchmod", fchmod):
            yield chmods, fchmods

    def test_the_umask_is_put_back_when_hosts_dir_raises(self):
        """The restore on the raising road, by execution (round 5's addendum, 2026-09-19): a parent that is a regular
        file makes owner_only_dir's mkdir raise (NotADirectoryError, an OSError) before any mode exists to read back,
        and the umask the case found is the one it has afterwards. Refusable: the finally replaced by a restore on the
        line after the call leaves 077 in place, and this reds."""
        base = tempfile.mkdtemp(prefix="sr-")
        self.addCleanup(shutil.rmtree, base, True)
        blocker = Path(base) / "blocker"
        blocker.write_text("")
        current = os.umask(0)
        os.umask(current)
        with self.assertRaises(OSError):
            self._made_under(0o077, root=blocker / "state")
        self.assertEqual(os.umask(current), current, "the umask is the one the case found, after the raise")

    def test_the_root_hosts_dir_makes_on_the_way_is_0700_under_every_umask_and_hosts_below_it_is_0700(self):
        """The fix's pin (round 6): the root this call made reads 0700 under each umask, where round 5 read the umask's
        mode; hosts/ 0700 as before. The 000 arm is the one the mkdir alone can never give (0777 there); 077 is the one
        arm the mkdir gives 0700 by itself, so it is the arm the fchmod's removal leaves green."""
        current = os.umask(0)                           # the runner's own umask, read and put back
        os.umask(current)
        for umask in (current, 0o002, 0o022, 0o077, 0o000):
            with self.subTest(umask="%03o" % umask):
                root_mode, hosts_mode = self._made_under(umask)
                self.assertEqual(root_mode, 0o700, "the root's mode read back under umask %03o: the code's, not the umask's" % umask)
                self.assertEqual(hosts_mode, 0o700, "hosts/ below it: the leaf carries the mode")
        self.assertEqual(os.umask(current), current, "the umask is the one the case found")

    def test_only_the_root_is_tightened_and_the_ancestor_made_on_the_way_keeps_the_umasks_mode(self):
        """The rejected alternative would tighten every directory the parents mkdir made; the fix touches the root alone.
        A root two levels under a fresh base: the intermediate the mkdir made on the way reads the umask's mode (0755
        under 022), the root 0700, hosts/ 0700, and the one mode call the road made is an fchmod on a descriptor whose
        object is the root (by identity), with no chmod by path at all: hosts/ is born 0700 by its mkdir, and the root's
        tighten goes through the descriptor since round 4."""
        base = tempfile.mkdtemp(prefix="sr-")
        self.addCleanup(shutil.rmtree, base, True)
        between = Path(base) / "xdg"
        root = between / "state"
        self.assertFalse(between.exists())
        with self._mode_spies() as (chmods, fchmods):
            root_mode, hosts_mode = self._made_under(0o022, root=root)
        self.assertEqual(stat.S_IMODE(os.lstat(between).st_mode), 0o755, "the ancestor made on the way: the umask's mode, untouched")
        self.assertEqual((root_mode, hosts_mode), (0o700, 0o700))
        self.assertEqual(chmods, [], "no chmod by path: the root's tighten is an fchmod, and hosts/ (born 0700) needs none")
        self.assertEqual(fchmods, [(self._ident(root), 0o700)], "one fchmod, on the descriptor whose object is the root; the ancestor and hosts/ are not named")

    def test_a_root_already_on_disk_is_left_as_it_is_and_hosts_below_it_is_0700(self):
        """The create-only scope, by execution: a root planted before the call keeps its mode (its creator's business,
        kernel/judge.py's on every install), hosts/ under it is 0700, and no chmod and no fchmod names the root. Two
        arms, 0755 and 0777 (the addendum to round 6 added 0777, the loosest mode and the one the fix's 0700 would change
        the most), both under 022, the umask that would leave a made root at 0755, so neither read can be the umask's
        doing."""
        base = tempfile.mkdtemp(prefix="sr-")
        self.addCleanup(shutil.rmtree, base, True)
        for planted in (0o755, 0o777):
            with self.subTest(planted="%04o" % planted):
                root = Path(base) / ("state-%04o" % planted)
                root.mkdir(mode=planted)
                os.chmod(root, planted)                 # the mkdir's mode is masked by the runner's umask; this is not
                self.assertEqual(stat.S_IMODE(os.lstat(root).st_mode), planted, "planted")
                old = os.umask(0o022)
                try:
                    with self._mode_spies() as (chmods, fchmods):
                        self.assertEqual(sh.hosts_dir(root), root / "hosts")
                finally:
                    os.umask(old)
                self.assertEqual(stat.S_IMODE(os.lstat(root).st_mode), planted, "a pre-existing root keeps its mode")
                self.assertEqual(stat.S_IMODE(os.lstat(root / "hosts").st_mode), 0o700, "hosts/ below it is 0700")
                self.assertNotIn(os.fspath(root), [c[0] for c in chmods], "no chmod named the pre-existing root")
                self.assertEqual(fchmods, [], "and no fchmod at all: the create road was not taken")

    def test_a_live_symlink_at_the_roots_path_is_a_root_on_disk_and_one_swapped_in_after_the_read_is_refused(self):
        """Two symlink arms (the addendum to round 6; HostsDir pins a symlink at hosts/, these are at the root). (1) A live
        symlink at the root's path, pointing at a directory that exists, takes the pre-existing road: exists() follows
        the link and answers True, hosts/ is made under the target and is 0700, and the target (planted 0755) is never
        read back or tightened; no chmod and no fchmod names the root or the target, and the link is still a link
        afterwards, as it was under the parent's hosts_dir (the create-only scope). (2) The race the docstring names: a
        link swapped in AFTER exists() said False (a Path.exists that plants the link as it answers False for this root)
        is refused by the create road's lstat as not a directory, the text carrying the root's path, and the target is not
        tightened on the link's behalf: its mode is still 0755, and the hosts/ under it, made through the link by the
        parents mkdir before the refusal, is 0700, ours. Refusable: that lstat swapped for a stat sees the target's
        directory and passes, and the road then opens the root O_NOFOLLOW and refuses the link there (round 4's open);
        through round 6 it chmodded the target to 0700, which reds (2) on the target's mode. The interleaving after the
        lstat is the next case's."""
        base = tempfile.mkdtemp(prefix="sr-")
        self.addCleanup(shutil.rmtree, base, True)

        def plant(name):
            target = Path(base) / (name + "-target")
            target.mkdir(mode=0o755)
            os.chmod(target, 0o755)
            return target, Path(base) / name
        # (1) the live link, on disk before the call
        target, root = plant("live")
        os.symlink(target, root)
        self.assertTrue(root.exists(), "exists() follows the link: a root on disk, to this call")
        old = os.umask(0o022)
        try:
            with self._mode_spies() as (chmods, fchmods):
                self.assertEqual(sh.hosts_dir(root), root / "hosts")
        finally:
            os.umask(old)
        self.assertTrue(stat.S_ISLNK(os.lstat(root).st_mode), "the link is still a link")
        self.assertEqual(stat.S_IMODE(os.lstat(target).st_mode), 0o755, "the target is neither read back nor tightened")
        self.assertEqual(stat.S_IMODE(os.lstat(target / "hosts").st_mode), 0o700, "hosts/ under the target, 0700")
        self.assertEqual((chmods, fchmods), ([], []), "no chmod, no fchmod: not the root, not the target (hosts/ is born 0700)")
        # (2) the link swapped in after exists() said False
        target2, root2 = plant("swapped")
        real_exists = Path.exists

        def exists(self_path, *a, **k):
            if os.fspath(self_path) == os.fspath(root2) and not os.path.lexists(root2):
                os.symlink(target2, root2)              # the swap, between the read and the mkdir
                return False                            # what the read said
            return real_exists(self_path, *a, **k)
        old = os.umask(0o022)
        try:
            with mock.patch.object(Path, "exists", exists), self._mode_spies() as (chmods, fchmods), \
                    self.assertRaises(OSError) as cm:
                sh.hosts_dir(root2)
        finally:
            os.umask(old)
        self.assertIn("is not a directory", str(cm.exception))
        self.assertIn(os.fspath(root2), str(cm.exception))
        self.assertTrue(stat.S_ISLNK(os.lstat(root2).st_mode), "the swapped-in link stands")
        self.assertEqual(stat.S_IMODE(os.lstat(target2).st_mode), 0o755, "not tightened on the link's behalf")
        self.assertEqual(stat.S_IMODE(os.lstat(target2 / "hosts").st_mode), 0o700,
                         "made through the link by the parents mkdir, before the refusal; 0700, ours")
        self.assertEqual((chmods, fchmods), ([], []), "no mode call on either arm")

    def test_a_link_swapped_in_between_the_lstat_and_the_open_is_refused_and_its_target_keeps_its_mode(self):
        """kernel-4 (round 4 of the review, 2026-09-20), the interleaving the case above does not reach: the link lands
        AFTER the create road's lstat has read a real directory and BEFORE the tighten. Through round 6 the tighten was
        os.chmod by path, so it followed the link and set 0700 on whatever the link pointed at (a directory of ours here;
        the round's refuters read a file of ours tightened the same way), and the call refused only at the read-back and
        for the wrong reason (the link's own mode); the uid check never read the swapped target, having decided on the
        pre-swap root. Now the root is opened O_DIRECTORY|O_NOFOLLOW right after the lstat: the open fails on the link
        (ENOTDIR on Linux under O_DIRECTORY|O_NOFOLLOW, ELOOP elsewhere), hosts_dir refuses naming the root and the swap,
        and the target's mode is what it was. Interposed on
        os.lstat, a direct call in hosts_dir (so the plant is seen on every interpreter, 3.10 included): the first lstat
        of the root's path answers the truth and then performs the swap (the root renamed aside with the hosts/ already
        made under it, a symlink to a 0755 directory put in its place). Read back from the objects: the target by lstat,
        still 0755; the moved root's hosts/ 0700; no chmod and no fchmod recorded. Red on the head before this fix: the
        target reads 0700 and the chmod spy names the root's path."""
        base = tempfile.mkdtemp(prefix="sr-")
        self.addCleanup(shutil.rmtree, base, True)
        root, moved, target = Path(base) / "state", Path(base) / "moved", Path(base) / "target"
        target.mkdir(mode=0o755)
        os.chmod(target, 0o755)
        real_lstat, swapped = os.lstat, []

        def lstat(path, *a, **k):
            st = real_lstat(path, *a, **k)
            if not swapped and not isinstance(path, int) and os.fspath(path) == os.fspath(root) and stat.S_ISDIR(st.st_mode):
                os.rename(root, moved)                  # the swap: after the read that decided the root is a directory of ours
                os.symlink(target, root)
                swapped.append(True)
            return st
        old = os.umask(0o022)
        try:
            with self._mode_spies() as (chmods, fchmods), mock.patch.object(os, "lstat", lstat), self.assertRaises(OSError) as cm:
                sh.hosts_dir(root)
        finally:
            os.umask(old)
        self.assertEqual(swapped, [True], "the swap landed after the lstat")
        self.assertEqual(stat.S_IMODE(real_lstat(target).st_mode), 0o755, "the target's mode, read back: untouched by the refused tighten")
        self.assertEqual((chmods, fchmods), ([], []), "no mode call reached anything")
        msg = str(cm.exception)
        self.assertIn(os.fspath(root), msg)
        self.assertIn("not a directory", msg)
        self.assertTrue(stat.S_ISLNK(real_lstat(root).st_mode), "the swapped-in link stands")
        self.assertEqual(stat.S_IMODE(real_lstat(moved / "hosts").st_mode), 0o700, "hosts/ was made 0700 under the real root before the swap")

    def test_a_root_another_uid_owns_is_refused_before_any_mode_is_set(self):
        """regression-1 and kernel-2 (round 4 of the review, 2026-09-20): the create road's foreign-uid refusal was held by
        no test, while the two refusals beside it each red a case. Two arms. (1) os.lstat answers st_uid + 1 for the
        root's path alone (an int argument, a descriptor, is left to the real call; owner_only_dir's own reads are of
        hosts/, never the root, so they read the truth): hosts_dir raises OSError carrying "belongs to uid" and the root's
        path, no chmod and no fchmod was made, and the root's real mode read back by the unpatched lstat is the umask's,
        0755 under 022, so the refusal came BEFORE the tighten (under 077 the mkdir alone gives 0700 and that read would
        say nothing: the umask is the discriminating choice, as the round's refuters noted). (2) The lstat truthful and
        os.fstat answering st_uid + 1 for the root's descriptor: the shape of a foreign DIRECTORY renamed onto the root's
        path between the lstat and the open (O_NOFOLLOW refuses a link there, not a directory); the descriptor's check
        refuses the same way, before the fchmod. The reachable shape is a directory another uid wins into the root's path
        between hosts_dir's exists() read and the parents mkdir, the race window the swapped-link case pins. The
        refusal is outcome-bearing at euid 0 or with CAP_FOWNER: an ordinary euid's chmod of a foreign directory raises
        EPERM by itself, so for an ordinary euid this pin holds the clear message and that no mode call is made at all.
        Refusable: the lstat's uid refusal deleted reds arm (1) with OSError not raised; the fstat's reds arm (2)."""
        real_lstat, real_fstat = os.lstat, os.fstat

        def foreign(st):
            fields = list(st)
            fields[4] = st.st_uid + 1                   # st_uid: someone else's directory at our path
            return os.stat_result(fields)
        for arm in ("lstat", "fstat"):
            with self.subTest(arm=arm):
                base = tempfile.mkdtemp(prefix="sr-")
                self.addCleanup(shutil.rmtree, base, True)
                root = Path(base) / "state"

                def lstat(path, *a, **k):
                    st = real_lstat(path, *a, **k)
                    if arm == "lstat" and not isinstance(path, int) and os.fspath(path) == os.fspath(root):
                        return foreign(st)
                    return st

                def fstat(fd):
                    st = real_fstat(fd)
                    if arm == "fstat" and stat.S_ISDIR(st.st_mode) and (st.st_dev, st.st_ino) == self._ident(root, real_lstat):
                        return foreign(st)
                    return st
                old = os.umask(0o022)
                try:
                    with self._mode_spies() as (chmods, fchmods), mock.patch.object(os, "lstat", lstat), \
                            mock.patch.object(os, "fstat", fstat), self.assertRaises(OSError) as cm:
                        sh.hosts_dir(root)
                finally:
                    os.umask(old)
                msg = str(cm.exception)
                self.assertTrue(msg.startswith("state root "), msg)
                self.assertIn("belongs to uid %d, not to us (uid %d)" % (os.geteuid() + 1, os.geteuid()), msg)
                self.assertIn(os.fspath(root), msg)
                self.assertEqual((chmods, fchmods), ([], []), "refused before any mode call")
                self.assertEqual(stat.S_IMODE(real_lstat(root).st_mode), 0o755, "the root still reads the umask's mode by the real lstat: not tightened")
                self.assertEqual(stat.S_IMODE(real_lstat(root / "hosts").st_mode), 0o700, "hosts/ under it was made 0700 before the refusal")

    def test_the_read_back_is_an_fstat_on_the_descriptor_so_a_stat_or_lstat_by_path_that_disagrees_is_inert(self):
        """The read-back reads the root back by os.fstat on the descriptor the fchmod acted on, not by any path (round 4
        of the review, 2026-09-20; the addendum to round 6 pinned an lstat read-back against a lying os.stat, and this
        case pins the descriptor read-back against both path readers). Once the fchmod has run, stubbed os.stat and
        os.lstat both answer S_IFDIR|0755 for the root's path (an int argument is left to the real call); hosts_dir returns
        normally, the fchmod ran once, and the root reads 0700 by the unpatched lstat. Refusable: the read-back swapped
        for os.lstat(root) or os.stat(root) makes the stub's 0755 the mode read, and the refusal fires where this asserts
        a return."""
        base = tempfile.mkdtemp(prefix="sr-")
        self.addCleanup(shutil.rmtree, base, True)
        root = Path(base) / "state"
        real_stat, real_lstat, real_fchmod = os.stat, os.lstat, os.fchmod
        fchmodded = []

        def fchmod(fd, mode):
            fchmodded.append(mode)
            return real_fchmod(fd, mode)

        def lying(real):
            def read(path, *a, **k):
                st = real(path, *a, **k)
                if not isinstance(path, int) and os.fspath(path) == os.fspath(root) and fchmodded:
                    return os.stat_result((stat.S_IFDIR | 0o755,) + tuple(st)[1:])
                return st
            return read
        old = os.umask(0o022)
        try:
            with mock.patch.object(os, "fchmod", fchmod), mock.patch.object(os, "stat", lying(real_stat)), \
                    mock.patch.object(os, "lstat", lying(real_lstat)):
                self.assertEqual(sh.hosts_dir(root), root / "hosts")
        finally:
            os.umask(old)
        self.assertEqual(fchmodded, [0o700], "the fchmod ran once")
        self.assertEqual(stat.S_IMODE(real_lstat(root).st_mode), 0o700, "the real mode, by the unpatched lstat")

    def test_a_read_back_that_disagrees_is_refused_with_the_mode_and_the_remedy(self):
        """The read-back's disagreement arm, driven by a stubbed fstat: after the real fchmod, the fstat that reads the
        root's descriptor back answers 0755 (the stub is keyed on the descriptor's inode, the root's, and answers only
        once the fchmod has run, so the uid check's fstat before it is the real one), and hosts_dir raises an OSError
        naming the root, the mode read (0755) and the remedy (chmod 700). The same arm fires for an fchmod that does not
        take (os.fchmod stubbed to a no-op): the real fstat reads the umask's 0755, the same refusal, the root left at
        0755."""
        base = tempfile.mkdtemp(prefix="sr-")
        self.addCleanup(shutil.rmtree, base, True)
        root = Path(base) / "state"
        real_fstat, real_fchmod, real_lstat = os.fstat, os.fchmod, os.lstat
        fchmodded = []

        def fchmod(fd, mode):
            fchmodded.append(real_fstat(fd).st_ino)
            return real_fchmod(fd, mode)

        def fstat(fd):
            st = real_fstat(fd)
            if fchmodded and st.st_ino == fchmodded[0]:                 # the read-back, after the fchmod, on the root's descriptor
                return os.stat_result((stat.S_IFDIR | 0o755,) + tuple(st)[1:])
            return st
        old = os.umask(0o022)
        try:
            with mock.patch.object(os, "fchmod", fchmod), mock.patch.object(os, "fstat", fstat), \
                    self.assertRaises(OSError) as cm:
                sh.hosts_dir(root)
        finally:
            os.umask(old)
        msg = str(cm.exception)
        self.assertIn(os.fspath(root), msg)
        self.assertIn("0755", msg, "the mode as read back")
        self.assertIn("chmod 700", msg, "the one-step remedy")
        self.assertEqual(fchmodded, [real_lstat(root).st_ino], "the fchmod ran once, on the root's descriptor, before the read-back disagreed")
        self.assertEqual(stat.S_IMODE(real_lstat(root).st_mode), 0o700, "the real mode: the stub, not the fchmod, disagreed")
        # the no-op fchmod arm: the root stays at the umask's mode, the real read-back disagrees, the same refusal
        other = Path(base) / "state2"
        old = os.umask(0o022)
        try:
            with mock.patch.object(os, "fchmod", lambda *a, **k: None), self.assertRaises(OSError) as cm2:
                sh.hosts_dir(other)
        finally:
            os.umask(old)
        self.assertIn("0755", str(cm2.exception))
        self.assertEqual(stat.S_IMODE(os.lstat(other).st_mode), 0o755, "left at the umask's mode by the fchmod that did not take")

class HostsDir(unittest.TestCase):
    """sh.hosts_dir called directly, the checks it takes whole from kernel/judge.py's _ensure_judge_scratch (the review of
    the socket-mode fix, 2026-09-19: the first cut named that precedent and kept half of it). Under a 000 umask so the
    modes are the code's doing."""

    def setUp(self):
        self.addCleanup(os.umask, os.umask(0o000))
        self.root = tempfile.mkdtemp(prefix="hd-")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.hosts = Path(self.root) / "hosts"

    def test_a_fresh_hosts_is_0700_and_a_loose_one_is_tightened_and_read_back(self):
        self.assertEqual(sh.hosts_dir(self.root), self.hosts)
        self.assertEqual(stat.S_IMODE(os.lstat(self.hosts).st_mode), 0o700)
        os.chmod(self.hosts, 0o775)                     # the mode every live host's hosts/ had before the fix (umask 002)
        reads = []
        real_lstat = os.lstat

        def lstat(p, *a, **k):
            st = real_lstat(p, *a, **k)
            if Path(p) == self.hosts:
                reads.append(stat.S_IMODE(st.st_mode))
            return st
        with mock.patch.object(os, "lstat", lstat):
            sh.hosts_dir(self.root)
        self.assertEqual(reads, [0o775, 0o700], "the mode read before the chmod and read back after it")

    def test_a_fresh_hosts_is_0700_by_its_mkdir_and_no_chmod_is_needed(self):
        """The creation mode is the mkdir's own (the mutation pass of round 1, 2026-09-19: with the mode dropped from the
        mkdir, a fresh hosts/ under a 000 umask was born 0777 and repaired to 0700 by the chmod a line later, and every
        case that read the final mode passed; that create-then-tighten window is the shape this fix closes for the socket,
        so the directory is pinned at its creation too). Read where it shows: the first lstat after the mkdir reads 0700,
        no chmod is made, and on a second fresh root with os.chmod a no-op the directory is still made and still 0700."""
        chmods, reads = [], []
        real_chmod, real_lstat = os.chmod, os.lstat

        def chmod(p, mode, *a, **k):
            chmods.append((Path(p), mode))
            return real_chmod(p, mode, *a, **k)

        def lstat(p, *a, **k):
            st = real_lstat(p, *a, **k)
            if Path(p) == self.hosts:
                reads.append(stat.S_IMODE(st.st_mode))
            return st
        with mock.patch.object(os, "chmod", chmod), mock.patch.object(os, "lstat", lstat):
            self.assertEqual(sh.hosts_dir(self.root), self.hosts)
        self.assertEqual(reads, [0o700], "0700 at the first read after the mkdir, under a 000 umask: the mkdir's mode")
        self.assertEqual(chmods, [], "nothing to repair on a directory born owner-only")
        other = tempfile.mkdtemp(prefix="hd-")
        self.addCleanup(shutil.rmtree, other, True)
        with mock.patch.object(os, "chmod", lambda *a, **k: None):
            self.assertEqual(sh.hosts_dir(other), Path(other) / "hosts")
        self.assertEqual(stat.S_IMODE(os.lstat(Path(other) / "hosts").st_mode), 0o700, "made 0700 with no chmod to lean on")

    def test_an_owner_only_hosts_is_read_and_left_and_only_a_loose_one_is_chmodded(self):
        """chmod only when loose (the mutation pass of round 1, 2026-09-19: a chmod on every call reads back the same
        mode, so nothing pinned the condition). hosts_dir runs on every host's bind and every kernel spawn, over the one
        directory every session's socket lives in; a 0700 hosts/ we own is read and left as it is, and the chmod is the
        repair for a loose one, made once and read back."""
        sh.hosts_dir(self.root)
        self.assertEqual(stat.S_IMODE(os.lstat(self.hosts).st_mode), 0o700)
        chmods = []
        real_chmod = os.chmod

        def chmod(p, mode, *a, **k):
            chmods.append((Path(p), mode))
            return real_chmod(p, mode, *a, **k)
        with mock.patch.object(os, "chmod", chmod):
            sh.hosts_dir(self.root)
            sh.hosts_dir(self.root)
        self.assertEqual(chmods, [], "two calls over an owner-only hosts/: no chmod")
        os.chmod(self.hosts, 0o750)                     # loose by the group's read and search bits alone
        with mock.patch.object(os, "chmod", chmod):
            sh.hosts_dir(self.root)
            sh.hosts_dir(self.root)
        self.assertEqual(chmods, [(self.hosts, 0o700)], "one chmod, for the loose one, and none on the call after it")
        self.assertEqual(stat.S_IMODE(os.lstat(self.hosts).st_mode), 0o700)

    def test_a_symlink_at_hosts_is_refused_and_its_target_untouched(self):
        target = Path(self.root) / "elsewhere"
        target.mkdir(mode=0o755)
        self.hosts.symlink_to(target)
        with self.assertRaises(OSError) as cm:
            sh.hosts_dir(self.root)
        self.assertIn("not a directory", str(cm.exception))
        self.assertTrue(self.hosts.is_symlink())
        self.assertEqual(stat.S_IMODE(os.stat(target).st_mode), 0o755, "no chmod through the link (the first cut stat'd through it)")

    def test_a_tighten_that_does_not_take_raises(self):
        self.hosts.mkdir(mode=0o755)
        with mock.patch.object(os, "chmod", lambda *a, **k: None):
            with self.assertRaises(OSError) as cm:
                sh.hosts_dir(self.root)
        self.assertIn("stays group/world-accessible", str(cm.exception))
        self.assertEqual(stat.S_IMODE(os.lstat(self.hosts).st_mode), 0o755)

    def test_a_hosts_another_uid_owns_is_refused(self):
        self.hosts.mkdir(mode=0o700)
        real_lstat = os.lstat

        def lstat(p, *a, **k):
            st = real_lstat(p, *a, **k)
            if Path(p) == self.hosts:
                fields = list(st)
                fields[4] = st.st_uid + 1               # st_uid: someone else's directory at our path
                return os.stat_result(fields)
            return st
        with mock.patch.object(os, "lstat", lstat):
            with self.assertRaises(OSError) as cm:
                sh.hosts_dir(self.root)
        self.assertIn("belongs to uid", str(cm.exception))

    def test_the_session_directory_takes_the_same_helper_born_0700_by_its_mkdir_and_a_symlink_there_refused(self):
        """The sibling one line below (the review's round 2, 2026-09-19: round 1 installed the checks on hosts/ and left
        hosts/<sid>/ on a bare mkdir and a chmod never read back). owner_only_dir is hosts_dir's shape for any path: the
        mode is read at the FIRST lstat after the mkdir (0700 under a 000 umask, the mkdir's own, not the chmod's a line
        later: every earlier assertion read the final mode, which a following chmod supplies whatever the mkdir did), no
        chmod is made on a directory born owner-only, a no-op chmod on a second fresh root still leaves 0700, a symlink
        at the path is refused with the noun the caller gave and its target untouched, and a missing parent is NOT made
        (parents=False: an intermediate directory would take the umask's mode, the shape hosts_dir exists to close)."""
        sh.hosts_dir(self.root)
        sdir = self.hosts / SID
        chmods, reads = [], []
        real_chmod, real_lstat = os.chmod, os.lstat

        def chmod(p, mode, *a, **k):
            chmods.append((Path(p), mode))
            return real_chmod(p, mode, *a, **k)

        def lstat(p, *a, **k):
            st = real_lstat(p, *a, **k)
            if Path(p) == sdir:
                reads.append(stat.S_IMODE(st.st_mode))
            return st
        with mock.patch.object(os, "chmod", chmod), mock.patch.object(os, "lstat", lstat):
            self.assertEqual(sh.owner_only_dir(sdir, "host directory"), sdir)
        self.assertEqual(reads, [0o700], "0700 at the first read after the mkdir, under a 000 umask: the mkdir's mode")
        self.assertEqual(chmods, [], "nothing to repair on a directory born owner-only")
        other = tempfile.mkdtemp(prefix="hd-")
        self.addCleanup(shutil.rmtree, other, True)
        with mock.patch.object(os, "chmod", lambda *a, **k: None):
            self.assertEqual(sh.owner_only_dir(Path(other) / "s"), Path(other) / "s")
        self.assertEqual(stat.S_IMODE(os.lstat(Path(other) / "s").st_mode), 0o700, "made 0700 with no chmod to lean on")
        target = Path(self.root) / "elsewhere"
        target.mkdir(mode=0o755)
        link = self.hosts / "22222222-2222-3333-4444-0000000000a2"
        link.symlink_to(target)
        with self.assertRaises(OSError) as cm:
            sh.owner_only_dir(link, "host directory")
        self.assertTrue(str(cm.exception).startswith("host directory "), str(cm.exception))
        self.assertIn("not a directory", str(cm.exception))
        self.assertTrue(link.is_symlink())
        self.assertEqual(stat.S_IMODE(os.stat(target).st_mode), 0o755, "no chmod through the link")
        with self.assertRaises(FileNotFoundError):
            sh.owner_only_dir(Path(self.root) / "missing" / "s")
        self.assertFalse((Path(self.root) / "missing").exists(), "no parent made at the umask's mode")
        loose = self.hosts / "33333333-2222-3333-4444-0000000000a3"
        loose.mkdir(mode=0o755)
        with mock.patch.object(os, "chmod", lambda *a, **k: None):
            with self.assertRaises(OSError) as cm:
                sh.owner_only_dir(loose, "host directory")
        self.assertIn("stays group/world-accessible", str(cm.exception))
        self.assertEqual(sh.owner_only_dir(loose, "host directory"), loose)
        self.assertEqual(stat.S_IMODE(os.lstat(loose).st_mode), 0o700, "a loose one of ours is tightened and read back")

    def test_a_state_root_not_yet_on_disk_is_made_on_the_way_and_hosts_below_it_is_still_born_0700(self):
        """hosts_dir passes parents=True, for the state root alone (the mutation pass of round 2, 2026-09-19: every case
        handed it a root that existed, so parents=False passed them all). Every install has its root (kernel/judge.py
        makes it 0700 at import), and a caller over one not yet on disk gets hosts/ made, 0700 by its mkdir, with the root
        made on the way rather than a FileNotFoundError; the helper's own default stays False (the session-directory case
        above pins a missing parent NOT made), since an intermediate directory mkdir creates takes the umask's mode."""
        root = Path(self.root) / "state"
        self.assertFalse(root.exists())
        self.assertEqual(sh.hosts_dir(root), root / "hosts")
        self.assertTrue(root.is_dir(), "the root was made on the way")
        self.assertEqual(stat.S_IMODE(os.lstat(root / "hosts").st_mode), 0o700, "and hosts/ below it is 0700 by its mkdir")
        with self.assertRaises(FileNotFoundError):
            sh.owner_only_dir(Path(self.root) / "other" / "hosts", "hosts directory")
        self.assertFalse((Path(self.root) / "other").exists(), "the helper's default makes no parent")

    def test_every_refusal_names_the_hosts_directory_by_that_noun_and_its_path(self):
        """The noun in the refusals (the mutation pass of round 2, 2026-09-19: the cases above read the refusal's reason,
        not a directory, belongs to uid, stays group/world-accessible, and stayed green with the noun changed to the
        helper's bare default). A launch error or a traceback says WHICH directory it was: each of hosts_dir's three
        refusals begins `hosts directory <path>`, where owner_only_dir's default begins `directory <path>` and the
        session directory's `host directory <path>` (pinned above and in tests/test_host_transport.py)."""
        target = Path(self.root) / "elsewhere"
        target.mkdir(mode=0o755)
        self.hosts.symlink_to(target)
        with self.assertRaises(OSError) as cm:
            sh.hosts_dir(self.root)
        self.assertEqual(str(cm.exception), "hosts directory %s is not a directory" % self.hosts)
        self.hosts.unlink()
        self.hosts.mkdir(mode=0o755)
        with mock.patch.object(os, "chmod", lambda *a, **k: None):
            with self.assertRaises(OSError) as cm:
                sh.hosts_dir(self.root)
        self.assertEqual(str(cm.exception), "hosts directory %s stays group/world-accessible" % self.hosts)
        os.chmod(self.hosts, 0o700)
        real_lstat = os.lstat

        def lstat(p, *a, **k):
            st = real_lstat(p, *a, **k)
            if Path(p) == self.hosts:
                fields = list(st)
                fields[4] = st.st_uid + 1               # st_uid: someone else's directory at our path
                return os.stat_result(fields)
            return st
        with mock.patch.object(os, "lstat", lstat):
            with self.assertRaises(OSError) as cm:
                sh.hosts_dir(self.root)
        self.assertEqual(str(cm.exception), "hosts directory %s belongs to uid %d, not to us (uid %d)"
                         % (self.hosts, os.geteuid() + 1, os.geteuid()))
        link = Path(self.root) / "link"
        link.symlink_to(target)
        with self.assertRaises(OSError) as cm:
            sh.owner_only_dir(link)
        self.assertEqual(str(cm.exception), "directory %s is not a directory" % link, "the helper's own default noun, which hosts_dir does not use")


class PaddedRoots(unittest.TestCase):
    """The no-skip helpers never skip (the review's round 2, 2026-09-19, and its round 3): the padded cases pin round 1's
    high, and round 1's helpers skipped once the run's private temp root was deep, so the module reported green with the
    high unpinned. Both directions: with the run's temp root as deep as a long TMPDIR under xdist makes it, the root is
    built under the system temp dir at the exact byte length; with the SYSTEM temp dir itself too deep, the helper FAILS,
    naming the remedy, rather than skipping. Round 3 (M2) made the pin itself unable to skip: unittest.SkipTest is not an
    AssertionError, so through round 2 a skipTest restored inside padded_root made this pin report SKIPPED, not red, on
    exactly its own subject; both padded_root calls now turn a SkipTest into a failure, and the pin is run against that
    refusable input below. The same round's M1 made the deep root's cleanup delete only the directory the test made
    (through round 2 it recovered its target by splitting the deep path on the literal nine-d component, so under a
    TMPDIR carrying such a component it removed a directory the test never created), and M3 asserted the multibyte
    cases' UTF-8 precondition instead of skipping on it; both are pinned here against their refusable inputs too."""

    DEEP_CASE = "test_a_deep_run_root_does_not_stop_the_pad_and_a_deep_system_temp_dir_fails_rather_than_skips"

    def test_a_deep_run_root_does_not_stop_the_pad_and_a_deep_system_temp_dir_fails_rather_than_skips(self):
        tail = os.path.join("hosts", SID[:8] + ".sock")
        base = tempfile.mkdtemp()                                      # the one directory this case makes: the one it removes
        self.addCleanup(shutil.rmtree, base, True)
        deep = os.path.join(base, *(["d" * 9] * 8))                    # a run root about 90 bytes deeper than the system temp dir
        os.makedirs(deep)
        with mock.patch.object(tempfile, "tempdir", deep):
            self.assertEqual(tempfile.gettempdir(), deep, "the run's temp root is the deep one for this call")
            try:
                root = padded_root(self, sh.SOCK_PATH_MAX + 1, tail)
            except unittest.SkipTest as e:
                self.fail("padded_root skipped rather than built the root under a deep run root: %s" % e)
        self.assertEqual(len(os.fsencode(os.path.join(root, tail))), sh.SOCK_PATH_MAX + 1)
        self.assertEqual(os.path.commonpath([os.path.realpath(root), os.path.realpath(system_tmp())]), os.path.realpath(system_tmp()),
                         "built under the system temp dir, not the run's root")
        self.assertTrue(os.path.isdir(root))
        with mock.patch.dict(os.environ, {"ROMP_TESTS_SYSTEM_TMPDIR": deep}):
            try:
                padded_root(self, sh.SOCK_PATH_MAX + 1, tail)
            except unittest.SkipTest as e:
                self.fail("padded_root skipped rather than failed on a system temp dir too deep for the pad: %s" % e)
            except AssertionError as e:
                msg = str(e)
            else:
                self.fail("padded_root built a root under a system temp dir too deep for the pad")
        self.assertIn("too deep", msg)
        self.assertIn("shorter TMPDIR", msg, "the remedy, in the failure, not a skip")

    def test_the_no_skip_pin_reds_rather_than_skips_when_padded_root_skips_on_either_arm(self):
        """The pin above against its own refusable input (round 3, M2): with padded_root restored to a helper that
        SKIPS, on the first call (a deep run root) or on the second (a deep system temp dir), the pin FAILS, naming the
        skip, and reports no skip; with the real helper it passes. Run as a nested case so the skip is read from the
        result the runner would see, not inferred."""
        mod = sys.modules[__name__]
        real = padded_root

        def skips_at_once(case, total, tail):
            raise unittest.SkipTest("this run's temp root is already deeper than %d allows" % total)

        def skips_on_the_deep_system_dir(case, total, tail):
            if "d" * 9 in system_tmp():
                raise unittest.SkipTest("the system temp dir is too deep for a %d-byte path" % total)
            return real(case, total, tail)
        for arm, stand_in in (("first call", skips_at_once), ("second call", skips_on_the_deep_system_dir)):
            with self.subTest(arm=arm):
                result = unittest.TestResult()
                with mock.patch.object(mod, "padded_root", stand_in):
                    PaddedRoots(self.DEEP_CASE).run(result)
                self.assertEqual((len(result.skipped), len(result.errors)), (0, 0), (result.skipped, result.errors))
                self.assertEqual(len(result.failures), 1, "the pin FAILS when its subject skips")
                self.assertIn("skipped rather than", result.failures[0][1])
        result = unittest.TestResult()
        PaddedRoots(self.DEEP_CASE).run(result)
        self.assertTrue(result.wasSuccessful(), (result.failures, result.errors, result.skipped))
        self.assertEqual(result.skipped, [], "and the real helper skips nothing")

    def test_the_deep_root_cleanup_removes_only_what_it_made_under_a_temp_dir_named_with_nine_d(self):
        """The deep-root case's cleanup against the input that made it dangerous (round 3, M1): the case run under a temp
        dir whose name carries nine consecutive d. Through round 2 the cleanup recovered its target as
        deep.split(os.sep + "d" * 9)[0], which under such a TMPDIR is a SHORTER prefix than the directory the test made,
        the handed temp dir's own parent here (with TMPDIR=/tmp/ddddddddd-foo it was /tmp itself). Now the case keeps the
        directory it made and removes that: the handed dir, a neighbour file in it and its parent all survive the run,
        and the case's own mkdtemp is gone."""
        outer = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, outer, True)
        handed = os.path.join(outer, "d" * 9 + "-tmp")
        os.mkdir(handed)
        keep = os.path.join(handed, "keep")
        open(keep, "w").close()
        result = unittest.TestResult()
        with mock.patch.object(tempfile, "tempdir", handed):
            PaddedRoots(self.DEEP_CASE).run(result)
        self.assertTrue(result.wasSuccessful(), (result.failures, result.errors, result.skipped))
        self.assertTrue(os.path.isdir(outer), "the handed temp dir's parent survives the cleanup")
        self.assertTrue(os.path.isdir(handed), "and the handed temp dir itself")
        self.assertTrue(os.path.exists(keep), "and a neighbour in it")
        self.assertEqual(os.listdir(handed), ["keep"], "the cleanup removed exactly the directory the case made, and nothing beside it")

    def test_the_multibyte_cases_fail_naming_the_remedy_rather_than_skip_on_a_single_byte_encoding(self):
        """require_utf8_names against its refusable input (round 3, M3): with os.fsencode answering one byte for a
        two-byte character, the shape of a runner whose filesystem encoding is single-byte, the guard FAILS (an
        AssertionError naming the encoding and the remedy), never skips; unpatched, on this runner, it passes."""
        with mock.patch.object(os, "fsencode", lambda name: str(name).encode("latin-1")):
            try:
                require_utf8_names(self)
            except unittest.SkipTest as e:
                self.fail("the guard skipped rather than failed: %s" % e)
            except AssertionError as e:
                msg = str(e)
            else:
                self.fail("a single-byte encoding passed the guard")
        self.assertIn("is not UTF-8", msg)
        self.assertIn("UTF-8 locale", msg, "the remedy, in the failure")
        self.assertIn("fail rather than skip", msg)
        require_utf8_names(self)

    MULTIBYTE_CASES = ("test_the_budget_is_measured_in_bytes_a_multibyte_published_path_over_it_in_bytes_alone_is_refused",
                       "test_a_multibyte_published_path_at_the_budget_in_bytes_is_served_and_a_client_connects")

    def test_the_multibyte_cases_themselves_fail_naming_the_remedy_on_a_single_byte_encoding_and_carry_no_skip(self):
        """The two multibyte CASES against the refusable runner, not only their helper (the mutation pass of round 3,
        2026-09-19: the pin above holds require_utf8_names to failing, and nothing held the cases to CALLING it, so both
        calls removed, or round 2's skipUnless put back on both, left the module green on this UTF-8 runner while a
        single-byte runner would again skip the byte measure's only pins). Each case is run as a nested case with
        os.fsencode answering one byte for a two-byte character: exactly one failure, carrying the encoding's name and
        the remedy, no skip and no error; and neither carries a skip decorator."""
        for name in self.MULTIBYTE_CASES:
            with self.subTest(case=name):
                case = SocketMode(name)
                self.assertFalse(getattr(getattr(case, name), "__unittest_skip__", False), "no skip decorator on the case")
                result = unittest.TestResult()
                with mock.patch.object(os, "fsencode", lambda n: str(n).encode("latin-1")):
                    case.run(result)
                self.assertEqual((len(result.skipped), len(result.errors)), (0, 0), (result.skipped, result.errors))
                self.assertEqual(len(result.failures), 1, "the case FAILS on a single-byte runner: %r" % (result.failures,))
                self.assertIn("is not UTF-8", result.failures[0][1])
                self.assertIn("UTF-8 locale", result.failures[0][1], "the remedy, in the failure")


class KeptLease(unittest.TestCase):
    """What the kept lease buys on the kernel's side (the review's round 2, 2026-09-19): the connect loop's orphan road
    waits for a dead host's CLI by the lease's pid and start, and only the lease tells it there is a CLI to wait for.
    Driven on the real backend over a scratch state root with a real process standing in for the CLI: with the lease
    the host kept (its holder gone, the CLI alive) the next connect waits and spawns nothing until the CLI is gone; with
    the lease removed, round 1's failure arm, the same connect finds a lease-less leftover, waits for nothing and spawns
    a second CLI while the first is alive. _spawn_host is replaced by a recorder (no host process starts here; the
    recorded call IS the second CLI), and the state root declares the host road it drives (`on` in session-hosts, the
    standing rule for a test that mints its own root; `off` reds both cases). A CHARACTERISATION PIN (review round 3,
    2026-09-19): both cases pass unchanged at the pre-fix head, because they describe the kernel's orphan road, which
    this PR does not change, and what the host's kept lease buys on it; they are not red-before evidence for the kept
    lease, whose change SocketMode's lease-stays case pins red-before (round 2)."""

    def setUp(self):
        self.state = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.state, True)
        Path(self.state, "session-hosts").write_text("on")   # this root means the host road (tests/conftest.py floors the run's root off)
        self.cli = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"])
        self.addCleanup(self.cli.wait, 30)
        self.addCleanup(self.cli.kill)
        gone = subprocess.Popen([sys.executable, "-c", "pass"])
        gone.wait(timeout=30)                           # reaped: the dead host's pid
        start = sb.proc_start(self.cli.pid)
        self.assertTrue(start, "the stand-in CLI has a start-time identity")
        self.lease = {"sid": SID, "fsid": FSID, "name": "web", "pid": self.cli.pid, "start": start,
                      "holder": {"pid": gone.pid, "start": "1", "kind": "host"}, "version": "abc12345", "spawnedAt": int(time.time()),
                      "t": time.time()}
        sb.write_lease(self.state, self.lease)
        sb.write_reg(Path(self.state), SID, {"sid": SID, "name": "web", "alive": True, "lastSid": SID})
        sd = Path(self.state) / "hosts" / SID
        sd.mkdir(parents=True, mode=0o700)
        (sd / "identity.json").write_text(json.dumps({"pid": gone.pid, "start": "1"}))
        self.logs = []
        self.be = sb.SdkBackend(self.state, "/bin/true", lambda *a, **k: None, log=self.logs.append)
        self.spawns = []

        def spawn_host(sess, spec_path, secret_env=None):
            self.spawns.append((time.time(), self.cli.poll()))
            return types.SimpleNamespace(pid=1, poll=lambda: 1, returncode=1, terminate=lambda: None)   # a host that exited at once
        self.be._spawn_host = spawn_host
        self.sess = types.SimpleNamespace(sid=SID, name="web", _host_intent=True, _host=None, _host_is_attach=False,
                                          _seed_for_dead_cli=lambda cli: None, _options_login="", _host_end_grace=None,
                                          _on_cli_stderr=lambda line: None)

    def _connect(self):
        return self.be._host_transport_for(self.sess, types.SimpleNamespace(), (None, None, None))

    def test_the_kept_lease_makes_the_next_connect_wait_for_the_cli_and_without_it_a_second_cli_starts(self):
        self.assertEqual(sb._ht().host_lease_state(sb.read_lease(self.state, SID), time.time()), "orphan",
                         "the lease the host kept reads as an orphan's: a host-held lease whose holder is gone")

        async def kept():
            task = asyncio.ensure_future(self._connect())
            done, _ = await asyncio.wait({task}, timeout=1.5)         # loop-ok: a bounded look at a road that is waiting
            self.assertEqual(done, set(), "the connect is still waiting: the CLI the lease names is alive")
            self.assertEqual(self.spawns, [], "and nothing was spawned while it lived")
            self.assertIsNotNone(sb.read_lease(self.state, SID), "the lease stands while the wait runs")
            self.cli.kill()
            killed = time.time()
            self.cli.wait(30)
            with self.assertRaises(Exception) as cm:                 # the recorder's host exited at once, so the road raises
                await asyncio.wait_for(task, 30)
            self.assertIn("exited before serving its socket", str(cm.exception))
            return killed
        killed = asyncio.run(kept())
        self.assertEqual(len(self.spawns), 1, "one spawn, after the CLI's exit")
        self.assertGreaterEqual(self.spawns[0][0], killed)
        self.assertIsNotNone(self.spawns[0][1], "the CLI was gone when the spawn came")
        self.assertIsNone(sb.read_lease(self.state, SID), "the orphan road cleared the dead host's lease once its CLI was gone")
        self.assertTrue(any("host.died" in l for l in (Path(self.state) / sb.SESSION_EVENTS_FILE).read_text().splitlines()))

    def test_without_the_lease_the_next_connect_waits_for_nothing_and_spawns_while_the_cli_lives(self):
        sb.remove_lease(self.state, SID)                 # round 1's failure arm: the lease gone, the CLI alive, the directory left
        self.assertIsNone(self.cli.poll(), "the CLI is alive")
        with self.assertRaises(Exception) as cm:
            asyncio.run(asyncio.wait_for(self._connect(), 30))
        self.assertIn("exited before serving its socket", str(cm.exception))
        self.assertEqual(len(self.spawns), 1, "a spawn with no wait")
        self.assertIsNone(self.spawns[0][1], "while the first CLI was still running: the second CLI on the same transcript")


class PreludeRefusalRead(unittest.TestCase):
    """The kernel's side of a refusal before the socket, on the PRODUCTION road: the real backend's spawn road
    (_host_transport_for: write the spec, descend to hosts/<sid>/ by descriptors, start the host through the real
    _spawn_host, poll for the published path while the host lives) over the real bin/romp-session-host. Since round 4
    of the review (2026-09-20) nothing in the launcher is replaced: the harness observes subprocess.Popen (to kill and
    count what it starts) and gives the host the environment the launcher inherits, this process's minus the credential
    names, with ROMP_SDK_SITE naming no directory, so the host runs the built-in pipe transport over a marker CLI that
    records its start and lives to EOF. Through round 3 the class replaced _spawn_host with a launcher of its own that
    sent the host's stderr OUTSIDE the state root, and its symlinked-hosts/ case passed a "nothing written through the
    link" assertion the production launcher failed: that launcher opened hosts/<sid>/host.stderr by PATH before Popen,
    so a hosts/ swapped for a symlink after the spec was written had that file, carrying the host's traceback with the
    absolute state root in it, written into the link's target (the round's high). The cases here drive the production
    road and read the link's target. Each root the class mints declares the host road it drives (`on` in session-hosts,
    the standing rule)."""

    def setUp(self):
        self.scratch = tempfile.mkdtemp()               # the marker CLI and its mark: not under any state root
        self.addCleanup(shutil.rmtree, self.scratch, True)
        self.marker = os.path.join(self.scratch, "cli-started")
        self.cli = os.path.join(self.scratch, "marker_cli.py")
        Path(self.cli).write_text("#!%s\nimport sys\nopen(%r, 'w').close()\nsys.stdin.read()\n" % (sys.executable, self.marker))   # marks its start, lives to EOF
        os.chmod(self.cli, 0o700)
        self.logs, self.hosts = [], []
        self.before_popen = []                          # plants run inside the Popen wrapper, after the kernel's descents and before the process exists
        self.host_env = {"PYTHONUNBUFFERED": "1", "ROMP_SDK_SITE": os.path.join(self.scratch, "no-sdk-here")}

    def _harness(self, state):
        """The real backend over `state`; the launcher is the production one (a plain new-session child: cli_scope off,
        since the scoped arm needs a user systemd)."""
        self.state = state
        Path(state, "session-hosts").write_text("on")   # this root means the host road (tests/conftest.py floors the run's root off)
        self.be = sb.SdkBackend(self.state, "/bin/true", lambda *a, **k: None, log=self.logs.append)
        self.be.cli_scope = False
        self.sess = types.SimpleNamespace(sid=SID, name="web", _host_intent=True, _host=None, _host_is_attach=False,
                                          _seed_for_dead_cli=lambda cli: None, _options_login="", _host_end_grace=None,
                                          _on_cli_stderr=lambda line: None)
        self.opts = types.SimpleNamespace(cli_path=self.cli, cwd=self.scratch, permission_prompt_tool_name="stdio",
                                          permission_mode="default", max_buffer_size=1024 * 1024, env={})

    def _connect(self, timeout=60):
        """The kernel's connect road once, through the production launcher; returns the launch error's text (the road
        raises on every refusal here). subprocess.Popen is wrapped, not replaced: the plants in before_popen run, the real
        Popen runs with the launcher's own arguments, and the process is recorded and killed at teardown."""
        real_popen = subprocess.Popen

        def popen(argv, **kw):
            for plant in self.before_popen:
                plant()
            proc = real_popen(argv, **kw)
            self.addCleanup(HostProcess._kill_group, proc)
            self.hosts.append(proc)
            return proc
        with mock.patch.dict(os.environ, self.host_env), mock.patch.object(sb.subprocess, "Popen", popen):
            for name in sb.AUTH_ENV_NAMES:
                os.environ.pop(name, None)
            with self.assertRaises(Exception) as cm:
                asyncio.run(asyncio.wait_for(self.be._host_transport_for(self.sess, self.opts, (None, None, None)), timeout))
        self.last_exc = cm.exception                    # the exception itself, for a case that reads its class or its errno
        return str(cm.exception)

    def _connect_outcome(self, timeout=60):
        """The connect road once, as _connect runs it, returning (what the road returned, the exception it raised): for a
        case whose red-before is a road that did NOT raise and handed back a transport (the round-7 second addendum's
        poll case), so the red lands on the case's own assertion and not on _connect's assertRaises."""
        real_popen = subprocess.Popen

        def popen(argv, **kw):
            for plant in self.before_popen:
                plant()
            proc = real_popen(argv, **kw)
            self.addCleanup(HostProcess._kill_group, proc)
            self.hosts.append(proc)
            return proc
        with mock.patch.dict(os.environ, self.host_env), mock.patch.object(sb.subprocess, "Popen", popen):
            for name in sb.AUTH_ENV_NAMES:
                os.environ.pop(name, None)
            try:
                return asyncio.run(asyncio.wait_for(self.be._host_transport_for(self.sess, self.opts, (None, None, None)), timeout)), None
            except Exception as e:
                return None, e

    def _events(self):
        p = Path(self.state) / sb.SESSION_EVENTS_FILE
        return [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []

    @staticmethod
    def _texts_under(d):
        """Every regular file under `d` as text, by relative path: what a directory received, for the no-traceback read."""
        return {str(p.relative_to(d)): p.read_text(errors="replace") for p in Path(d).rglob("*") if p.is_file()}

    def test_the_spawn_wait_names_host_stderr_for_a_host_refused_before_its_first_row(self):
        """regression-2 (round 3), on the production road since round 4: hosts/ is renamed aside and a symlink put in its
        place pointing at the moved directory, planted AFTER the kernel's descents have opened host.stderr by descriptor
        and before the host process exists (inside the Popen wrapper). The host reads the spec through the link, its
        constructor's hosts_dir refuses the link (kernel-2), and the process exits 1 before its journal, host.log or
        identity.json exist and before any CLI is spawned; its traceback goes to the descriptor it inherited, the file in
        the moved directory. The kernel's wait reads that exit through the descriptors it holds (the moved directory:
        host.log absent, host.stderr grown past the mark), so the message names the exit code, host.stderr under the
        condition, then the host.log tail. The moved directory holds exactly the spec and host.stderr, the file the
        kernel opened by descriptor before the swap, 0600 read back, which moved with the directory: the host wrote
        nothing (no host.log, no identity.json, no journal segment, no socket, no temp, no lease) and nothing reached that
        directory by way of the link. Round 3's version of this case asserted the spec alone, which held only because its
        own launcher redirected stderr out of the state root."""
        state = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, state, True)
        self._harness(state)
        hosts, target = Path(state) / "hosts", Path(state) / "elsewhere"

        def plant():
            os.rename(hosts, target)
            hosts.symlink_to(target)
        self.before_popen.append(plant)
        msg = self._connect()
        self.assertIn("exited before serving its socket (code 1)", msg, "the spawn wait read the host's exit")
        self.assertIn("see hosts/%s/host.stderr when host.log is missing or has no row from this launch, else see hosts/%s/host.log" % (SID, SID),
                      msg, "host.stderr grew past the mark, so it is named under the condition, then the host.log tail")
        self.assertEqual(len(self.hosts), 1, "one host was started")
        self.assertEqual(self.hosts[0].wait(10), 1)
        self.assertTrue(hosts.is_symlink(), "the link is left, not replaced")
        self.assertFalse((target / SID / "host.log").exists(), "no host.log exists for this refusal: a message naming it alone points at nothing")
        self.assertEqual(sorted(p.name for p in (target / SID).iterdir()), ["host.stderr", "spawn.json"],
                         "the spec, and the file the kernel opened by descriptor before the swap; nothing the host writes")
        err_path = target / SID / "host.stderr"
        self.assertEqual(stat.S_IMODE(os.lstat(err_path).st_mode), 0o600, "opened 0600 by the kernel, read back off the file")
        err = err_path.read_text()
        self.assertIn("hosts directory", err, err[-800:])
        self.assertIn("is not a directory", err)
        self.assertFalse(os.path.exists(self.marker), "the CLI never started: its marker is absent")
        self.assertIsNone(sb.read_lease(state, SID), "no lease was ever written")
        self.assertEqual(sorted(p.name for p in target.glob("*.tmp")) + sorted(p.name for p in target.glob("*.sock")), [], "nothing bound, nothing published")
        self.assertEqual([r["kind"] for r in self._events()], ["host.exited-before-socket"])

    def test_a_hosts_swapped_for_a_link_to_a_peers_directory_is_refused_and_the_peers_directory_receives_nothing(self):
        """THE ROUND'S HIGH (tests-1 with extra5-3 and extra8-2, round 4 of the review, 2026-09-20), driven on the production
        road at every point the sequence allows from outside. The swap is what a peer with write on a non-0700 state root
        can make: hosts/ renamed aside (hosts.moved, still ours) and a symlink put at hosts/ pointing at a directory of the
        peer's own, holding an empty <sid>/ the peer made. Four plant points, each over a fresh root: before the spec
        write; after write_spawn_spec returns and before the kernel's descent; after that descent and before the
        launcher's own (the real _spawn_host wrapped to plant, then delegate); and after both descents, before the host
        process exists (inside the Popen wrapper). At the first three the launch is refused before any process starts:
        the launch error and a host.directory-refused row name the link's path and the remedy, subprocess.Popen is never
        called, and the peer's directory receives NOTHING (its <sid>/ lists empty). At the fourth the host starts holding
        the descriptor the kernel opened before the swap, reads the spec through the link (absent in the peer's
        directory) and exits 1 with its traceback in hosts.moved/<sid>/host.stderr, ours; the peer's directory still
        receives nothing, and the kernel's message, read through the held descriptors, names host.stderr. No file under
        the peer's directory and no line of the kernel's log carries a traceback, at any point. Red on the head before
        this fix at the second and third points: the launcher's open(<path>, "ab") resolved through the link and the
        peer's <sid>/ listed host.stderr, a traceback naming the state root; red at the first point on the peer's <sid>/
        itself, deleted through the link by the leftover arm's rmtree; green at the fourth, where that launcher's open
        ran before Popen, so a swap inside the Popen wrapper landed after it (the run pasted in the PR body)."""
        for point in ("before-spec", "after-spec", "before-launcher", "before-popen"):
            with self.subTest(point=point):
                self.setUp()
                state = tempfile.mkdtemp()
                self.addCleanup(shutil.rmtree, state, True)
                self._harness(state)
                hosts, moved = Path(state) / "hosts", Path(state) / "hosts.moved"
                peer = Path(self.scratch) / "peer"
                (peer / SID).mkdir(parents=True, mode=0o755)

                def swap(hosts=hosts, moved=moved, peer=peer):
                    if os.path.lexists(hosts):
                        os.rename(hosts, moved)
                    hosts.symlink_to(peer)
                ht = sb._ht()
                real_write, real_spawn = ht.write_spawn_spec, self.be._spawn_host
                with contextlib.ExitStack() as stack:
                    if point == "before-spec":
                        swap()
                    elif point == "after-spec":
                        def write_then_swap(*a, **k):
                            p = real_write(*a, **k)
                            swap()
                            return p
                        stack.enter_context(mock.patch.object(ht, "write_spawn_spec", write_then_swap))
                    elif point == "before-launcher":
                        def swap_then_launch(sess, spec_path, secret_env=None):
                            swap()
                            return real_spawn(sess, spec_path, secret_env)
                        self.be._spawn_host = swap_then_launch
                    else:
                        self.before_popen.append(swap)
                    msg = self._connect()
                # what the peer's directory received, at every point: nothing
                self.assertTrue(hosts.is_symlink(), "the link is left, not replaced")
                self.assertEqual(sorted(os.listdir(peer)), [SID], "the peer's directory holds what the peer put there")
                self.assertEqual(os.listdir(peer / SID), [], "and its <sid>/ received nothing: no host.stderr, no spec, no row")
                self.assertEqual(self._texts_under(peer), {}, "no file anywhere under the peer's directory")
                self.assertNotIn("Traceback", "\n".join(str(l) for l in self.logs), "no traceback in the kernel's log")
                self.assertNotIn("Traceback", msg, "nor in the launch error")
                events = self._events()
                if point != "before-popen":
                    self.assertEqual(self.hosts, [], "no host process was started: the launch was refused before Popen")
                    # the descent's open refuses the link at every point: before the spec write it is the connect road's
                    # leftover trigger (the round-7 second addendum, 2026-09-20: through round 7 the
                    # trigger read `hdir.exists()` by path, the peer's <sid>/ entered the orphan road through the link and
                    # hosts_dir's lstat refused the link only afterwards, reading "is not a directory"), after it the
                    # road's own descent or the launcher's
                    self.assertTrue(msg.startswith("the session host was not started: hosts directory %s is a symlink, not a directory" % hosts), msg)
                    self.assertIn("ROMP_STATE_DIR", msg, "the remedy rides with the reason")
                    self.assertEqual([r["kind"] for r in events], ["host.directory-refused"], "one row, its own kind")
                    self.assertIn(os.fspath(hosts), events[0]["text"], "the row names the link")
                    self.assertFalse((moved / SID / "host.stderr").exists() if moved.exists() else False, "no launch, no host.stderr anywhere")
                else:
                    self.assertEqual(len(self.hosts), 1, "the host started with the descriptor the kernel opened before the swap")
                    self.assertEqual(self.hosts[0].wait(10), 1)
                    self.assertIn("exited before serving its socket (code 1)", msg)
                    self.assertIn("see hosts/%s/host.stderr when host.log is missing" % SID, msg, "host.stderr grew: named, read through the held descriptor")
                    err = (moved / SID / "host.stderr").read_text()
                    self.assertIn("Traceback", err, "the host's traceback landed in the directory the kernel verified, moved aside")
                    self.assertEqual([r["kind"] for r in events], ["host.exited-before-socket"])
                self.assertFalse(os.path.exists(self.marker), "the CLI never started: its marker is absent")
                self.assertIsNone(sb.read_lease(state, SID), "no lease was ever written")

    def test_the_launchers_descent_refuses_a_foreign_uid_or_a_loose_session_directory_and_starts_nothing(self):
        """tests-1 (round 5 of the review, 2026-09-20), on the production road: the descent's two fstat refusals at the
        launcher's own open_host_dirs (_spawn_host), which the PR body had waived as redundant with the O_NOFOLLOW open
        or unreachable. Neither arm is a link. Both are planted inside the real _spawn_host (wrapped to plant, then
        delegate), after write_spawn_spec's helpers have made and tightened the directories and after the kernel's own
        descent: `uid`, os.fstat answering st_uid + 1 for the descriptor whose (st_dev, st_ino) is hosts/<sid>/'s and
        truthfully for every other, the shape of a foreign directory renamed into place; `mode`, hosts/<sid>/ renamed
        aside and a real 0775 directory of ours made at its name (umask 002, the live host's). Each: the launch is
        refused before Popen, the launch error and one host.directory-refused row carry the arm's reason, the
        component's path and the remedy, and the directory the launcher would have opened host.stderr in holds no
        such file. Red with the arm deleted from _open_dir_nofollow: Popen runs and host.stderr is created inside the
        planted directory (on the uid arm a real host starts over it)."""
        real_fstat = os.fstat

        def foreign(st):
            fields = list(st)
            fields[4] = st.st_uid + 1
            return os.stat_result(fields)
        for arm in ("uid", "mode"):
            with self.subTest(arm=arm):
                self.setUp()
                self.addCleanup(os.umask, os.umask(0o002))
                state = tempfile.mkdtemp()
                self.addCleanup(shutil.rmtree, state, True)
                self._harness(state)
                sdir = Path(state) / "hosts" / SID
                real_spawn = self.be._spawn_host

                def plant_then_launch(sess, spec_path, secret_env=None, arm=arm, sdir=sdir, real_spawn=real_spawn):
                    if arm == "mode":
                        os.rename(sdir, sdir.parent / "moved")
                        os.mkdir(sdir, 0o775)                       # ours and loose, made at the name after the helpers ran
                        return real_spawn(sess, spec_path, secret_env)
                    st = os.lstat(sdir)
                    ident = (st.st_dev, st.st_ino)

                    def fstat(fd):
                        st = real_fstat(fd)
                        if isinstance(fd, int) and stat.S_ISDIR(st.st_mode) and (st.st_dev, st.st_ino) == ident:
                            return foreign(st)
                        return st
                    with mock.patch.object(os, "fstat", fstat):
                        return real_spawn(sess, spec_path, secret_env)
                self.be._spawn_host = plant_then_launch
                msg = self._connect()
                reason = ("belongs to uid %d, not to us (uid %d)" % (os.geteuid() + 1, os.geteuid()) if arm == "uid"
                          else "is group/world-accessible (mode 0775)")
                self.assertTrue(msg.startswith("the session host was not started: host directory %s %s" % (sdir, reason)), msg)
                self.assertIn("ROMP_STATE_DIR", msg, "the remedy rides with the reason")
                self.assertEqual(self.hosts, [], "no host process was started: the launcher's descent refused before Popen")
                events = self._events()
                self.assertEqual([r["kind"] for r in events], ["host.directory-refused"], "one row, its own kind")
                self.assertIn(reason, events[0]["text"])
                self.assertEqual(sorted(os.listdir(sdir)), ["spawn.json"] if arm == "uid" else [],
                                 "no host.stderr in the directory the launcher would have opened it in")
                self.assertFalse(os.path.exists(self.marker), "the CLI never started: its marker is absent")
                self.assertIsNone(sb.read_lease(state, SID), "no lease was ever written")

    def test_a_symlink_planted_at_spawn_json_or_host_stderr_is_filed_as_a_refusal_with_the_files_remedy_and_starts_nothing(self):
        """kernel-2 (round 5 of the review, 2026-09-20), on the production road: through round 4 the two file-level
        O_NOFOLLOW opens raised a bare OSError for a link at the name, so a spawn.json or host.stderr planted as a
        symlink under a verified hosts/<sid>/ escaped the refusal class: no problem row, no remedy, and the launch
        error composed over a stale stderr tail. A stale kernel-held lease keeps the directory across the launch (the
        live deployment's shape, where every session's directory survives between launches). Each arm: the launch
        error starts with the refusal naming the file and the directory, carries the file's remedy (remove the link),
        one host.directory-refused row, no Popen, and the link's target byte-identical at its old mode. Red before
        the change: the error is the bare OSError's text (`[Errno 40] Too many levels of symbolic links`) and no row
        is filed."""
        for name in ("spawn.json", "host.stderr"):
            with self.subTest(file=name):
                self.setUp()
                state = tempfile.mkdtemp()
                self.addCleanup(shutil.rmtree, state, True)
                self._harness(state)
                sdir = Path(state) / "hosts" / SID
                sdir.mkdir(parents=True, mode=0o700)
                sdir.parent.chmod(0o700)
                target = Path(self.scratch) / ("theirs-%s.txt" % name)
                target.write_text("the peer's own bytes")
                os.chmod(target, 0o644)
                (sdir / name).symlink_to(target)
                sb.write_lease(state, dict(SpawnWaitMessageArms._STALE_LEASE, sid=SID))
                msg = self._connect()
                self.assertTrue(msg.startswith("the session host was not started: %s in host directory %s is a symlink, not a regular file. "
                                               % (name, sdir)), msg)
                self.assertIn("A %s under hosts/<sid>/ that is a symlink is refused; remove the link, or point the state root elsewhere "
                              "(ROMP_STATE_DIR or XDG_STATE_HOME)" % name, msg, "the file's remedy, not the directory's")
                self.assertEqual(self.hosts, [], "no host process was started")
                events = self._events()
                self.assertEqual([r["kind"] for r in events], ["host.directory-refused"], "one row, the refusal class's kind")
                self.assertIn("%s in host directory" % name, events[0]["text"])
                self.assertTrue((sdir / name).is_symlink(), "the link is left, not replaced")
                self.assertEqual(target.read_text(), "the peer's own bytes", "nothing written through the link")
                self.assertEqual(stat.S_IMODE(os.lstat(target).st_mode), 0o644, "the target's mode untouched")
                self.assertFalse(os.path.exists(self.marker), "the CLI never started")

    def test_a_full_disk_at_the_spec_write_is_the_launch_error_with_its_errno_and_neither_a_refusal_nor_a_stale_tail(self):
        """regression-1 and kernel-4 (round 5 of the review, 2026-09-20), on the production road: a filesystem failure
        at write_spawn_spec's second directory helper (ENOSPC, then EROFS, raised by sh.owner_only_dir for hosts/<sid>/
        as os.mkdir would) is not a refusal. Through round 4 the wrap made it one: the card and the row read
        host.directory-refused with the directory remedy, false for a full disk. Now it is the launch error under its
        own text, `[Errno 28] No space left on device` and the path, errno on the exception, no remedy, no
        host.directory-refused row, no Popen; and _record_launch_error, handed that exception on a session whose CLI
        had once written a stderr line, persists the error's text and not that stale tail (the road a bare OSError
        takes, driven at this round's build). Red before the change: the message carried the directory remedy and a
        host.directory-refused row was filed."""
        for arm, code in (("ENOSPC", errno.ENOSPC), ("EROFS", errno.EROFS)):
            with self.subTest(arm=arm):
                self.setUp()
                state = tempfile.mkdtemp()
                self.addCleanup(shutil.rmtree, state, True)
                self._harness(state)
                self.sess.stderr_tail = lambda: "a STALE stderr tail from a previous CLI"
                self.sess._stderr_tail = ["a STALE stderr tail from a previous CLI"]
                real = sh.owner_only_dir

                def fail(path, what="directory", parents=False, code=code):
                    if what == "host directory":
                        raise OSError(code, os.strerror(code), os.fspath(path))
                    return real(path, what, parents)
                with mock.patch.object(sh, "owner_only_dir", fail):
                    msg = self._connect()
                self.assertTrue(msg.startswith("the session host was not started: [Errno %d] %s: " % (code, os.strerror(code))), msg)
                self.assertIn(os.fspath(Path(state) / "hosts" / SID), msg, "the error's own text, path included")
                self.assertNotIn("replace it with a directory", msg, "no directory remedy for a full disk")
                self.assertIsInstance(self.last_exc, sb.CLIConnectionErrorLike, repr(self.last_exc))
                self.assertEqual(getattr(self.last_exc, "errno", None), code, "the errno rides on the launch error")
                self.assertEqual([r["kind"] for r in self._events() if r["kind"] == "host.directory-refused"], [], "not filed as a refusal")
                self.assertEqual(self.hosts, [], "no host process was started")
                self.be._record_launch_error(self.sess, self.last_exc)
                rec = (sb.read_reg(Path(state), SID) or {}).get("launchError") or {}
                self.assertIn("[Errno %d] %s" % (code, os.strerror(code)), rec.get("text", ""), "the card reads the error, not the stale tail: %r" % (rec,))
                self.assertNotIn("STALE", rec.get("text", ""))

    _DIRECTORY_REMEDY = ("A hosts/ or hosts/<sid>/ that is not a directory this user owns at 0700 is refused; replace it with a "
                         "directory, or point the state root elsewhere (ROMP_STATE_DIR or XDG_STATE_HOME)")

    def _plant_shape(self, target, shape):
        peer = Path(self.scratch) / "peer"
        peer.mkdir(exist_ok=True)
        if shape == "regular file":
            target.write_text("")
        elif shape == "fifo":
            os.mkfifo(target)
        elif shape == "symlink to a file":
            (peer / "theirs.txt").write_text("the peer's own bytes")
            target.symlink_to(peer / "theirs.txt")
        else:
            target.symlink_to(peer / "nowhere")

    def test_a_non_directory_at_hosts_or_at_the_session_directory_is_filed_as_a_refusal_with_the_directory_remedy_and_starts_nothing(self):
        """Round 7 of the review (2026-09-20; the round-6 rulings' C), on the production road: a regular file, a FIFO, a
        symlink to a file or a dangling symlink at hosts/ or at hosts/<sid>/ is a directory-shape refusal, filed as one:
        the launch error names the component and "is not a directory" with the directory remedy, one
        host.directory-refused row, errno None on the exception, no Popen, the plant standing. Round 5's `errno is None`
        key filed none of these (the card read "[Errno 17] File exists", no row, no remedy), where round 4's head filed
        all of them; the wrap now keys on the errno set of the shape class. Red at the round-6 head on every arm: a
        CLIConnectionErrorLike with errno 17 and no row. Since the round-7 second addendum (2026-09-20) the connect road's
        leftover trigger runs the read roads' descent BEFORE the spawn road, so a shape standing at either component when
        the connect starts is refused there, by that descent's O_DIRECTORY|O_NOFOLLOW open, and never reaches the
        helpers: a regular file or a FIFO is worded "is not a directory" as the wrap words EEXIST, and the two links are
        worded as the descent words a link, "is a symlink, not a directory". Everything else the case reads holds
        unchanged (the directory remedy, one row, errno None, no Popen, the plant standing). The wrap's errno-set key
        stays driven at function level (tests/test_host_transport.py SpawnSpec) and on this road by the re-pointed case
        below, whose plant lands after the trigger."""
        for where in ("hosts", "hosts/<sid>"):
            for shape in ("regular file", "fifo", "symlink to a file", "dangling symlink"):
                with self.subTest(where=where, shape=shape):
                    self.setUp()
                    state = tempfile.mkdtemp()
                    self.addCleanup(shutil.rmtree, state, True)
                    self._harness(state)
                    if where == "hosts/<sid>":
                        sh.hosts_dir(state)
                        target, what = Path(state) / "hosts" / SID, "host directory"
                    else:
                        target, what = Path(state) / "hosts", "hosts directory"
                    self._plant_shape(target, shape)
                    before = os.lstat(target)
                    msg = self._connect()
                    why = "is a symlink, not a directory" if "symlink" in shape else "is not a directory"
                    self.assertTrue(msg.startswith("the session host was not started: %s %s %s. " % (what, target, why)), msg)
                    self.assertIn(self._DIRECTORY_REMEDY, msg)
                    self.assertIsInstance(self.last_exc, sb.CLIConnectionErrorLike, repr(self.last_exc))
                    self.assertIsNone(getattr(self.last_exc, "errno", None), "a refusal carries no errno")
                    events = self._events()
                    self.assertEqual([r["kind"] for r in events], ["host.directory-refused"], "one row, the refusal class's kind")
                    self.assertIn("%s %s %s" % (what, target, why), events[0]["text"])
                    self.assertEqual(self.hosts, [], "no host process was started")
                    self.assertFalse(os.path.exists(self.marker), "the CLI never started")
                    self.assertEqual(os.lstat(target)[:2], before[:2], "the plant stands as planted")

    def test_a_hosts_re_pointed_between_the_helpers_to_a_dangling_link_is_refused_and_to_an_unwritable_directory_is_the_launch_error_with_its_errno(self):
        """The two decisions of round 7 (the round-6 rulings' C) on the production road, planted in the window condition 1
        states (sh.hosts_dir wrapped to re-point hosts/ after it returns, before sh.owner_only_dir's mkdir): a DANGLING
        link is refused under the class with the directory remedy and one host.directory-refused row (ENOENT joins the
        class: the descent's own open already words it "does not exist", and a peer plants it with one syscall); a link
        to a directory this uid cannot write is the launch error with errno 13 and no row (EACCES stays a filesystem
        failure by the ruling, though a peer can cause it too), the error-centre line naming the spec-write arm. Neither
        starts a process, and the unwritable target receives nothing."""
        ht = sb._ht()
        real_hosts_dir = ht.sh.hosts_dir
        for arm in ("dangling", "unwritable"):
            with self.subTest(arm=arm):
                self.setUp()
                state = tempfile.mkdtemp()
                self.addCleanup(shutil.rmtree, state, True)
                self._harness(state)
                if arm == "dangling":
                    target = Path(self.scratch) / "nowhere"
                else:
                    target = Path(self.scratch) / "readonly"
                    target.mkdir(mode=0o500)
                    self.addCleanup(os.chmod, target, 0o700)

                def repoint(state_dir, target=target):
                    r = real_hosts_dir(state_dir)
                    os.rename(r, str(r) + ".aside")
                    os.symlink(target, r)
                    return r
                with mock.patch.object(ht.sh, "hosts_dir", repoint):
                    msg = self._connect()
                leaf = Path(state) / "hosts" / SID
                self.assertIsInstance(self.last_exc, sb.CLIConnectionErrorLike, repr(self.last_exc))
                self.assertEqual(self.hosts, [], "no host process was started")
                if arm == "dangling":
                    self.assertTrue(msg.startswith("the session host was not started: host directory %s does not exist (a component is missing, or a symlink there dangles). " % leaf), msg)
                    self.assertIn(self._DIRECTORY_REMEDY, msg)
                    self.assertIsNone(getattr(self.last_exc, "errno", None))
                    self.assertEqual([r["kind"] for r in self._events()], ["host.directory-refused"])
                else:
                    self.assertTrue(msg.startswith("the session host was not started: [Errno %d] %s: " % (errno.EACCES, os.strerror(errno.EACCES))), msg)
                    self.assertNotIn("replace it with a directory", msg)
                    self.assertEqual(getattr(self.last_exc, "errno", None), errno.EACCES)
                    self.assertEqual([r["kind"] for r in self._events()], [], "no row: a filesystem failure is not a refusal")
                    self.assertTrue(any("the spawn specification could not be written: [Errno %d]" % errno.EACCES in m for m in self.logs), self.logs)
                    self.assertEqual(sorted(os.listdir(target)), [], "the unwritable target received nothing")

    def test_a_filesystem_failure_at_the_launchers_descent_or_its_host_stderr_open_is_the_launch_error_with_its_errno_and_no_stale_tail(self):
        """kernel-2, tests-1 and regression-2 (round 6 of the review, 2026-09-20), on the production road: through round 6
        the launcher's call site caught HostDirRefused alone, so an OSError from its descent, its host.stderr open, the
        fchmod after it or Popen itself propagated bare to _record_launch_error, whose text prefers the session's stale
        stderr tail, and the card read a PREVIOUS CLI's line with no row and no errno. Four arms, each on a session whose
        CLI once wrote a stderr line: a real directory standing at hosts/<sid>/host.stderr (EISDIR from the open, no stub);
        ENOSPC interposed at ht.host_stderr_open; EPERM interposed at os.fchmod inside the launcher alone, with os.open and
        os.close recorded to hold host_stderr_open's close-and-reraise on the road (tests-3); and Popen itself raising
        (a launcher that cannot be started, folded in on purpose). Each: CLIConnectionErrorLike with the errno, the error's
        own text, no host.directory-refused row, no process, the error-centre line naming the launcher's arm, and
        _record_launch_error persisting the errno text and not the stale tail. Red at the round-6 head: a bare OSError
        out of the road and the stale tail persisted, on every arm."""
        ht = sb._ht()
        for arm, code in (("directory-at-host.stderr", errno.EISDIR), ("enospc-at-open", errno.ENOSPC),
                          ("eperm-at-fchmod", errno.EPERM), ("popen-raises", errno.ENOENT)):
            with self.subTest(arm=arm):
                self.setUp()
                state = tempfile.mkdtemp()
                self.addCleanup(shutil.rmtree, state, True)
                self._harness(state)
                self.sess.stderr_tail = lambda: "a STALE stderr tail from a previous CLI"
                self.sess._stderr_tail = ["a STALE stderr tail from a previous CLI"]
                sdir = Path(state) / "hosts" / SID
                sdir.mkdir(parents=True, mode=0o700)
                sdir.parent.chmod(0o700)
                sb.write_lease(state, dict(SpawnWaitMessageArms._STALE_LEASE, sid=SID))    # keeps the directory across the launch
                real_spawn = self.be._spawn_host
                opened, closed = [], []
                real_open, real_close, real_fchmod = os.open, os.close, os.fchmod

                def launch(sess, spec_path, secret_env=None, arm=arm):
                    if arm == "directory-at-host.stderr":
                        (sdir / "host.stderr").mkdir(mode=0o700)
                        return real_spawn(sess, spec_path, secret_env)
                    if arm == "enospc-at-open":
                        def full(dirs):
                            raise OSError(errno.ENOSPC, os.strerror(errno.ENOSPC), "host.stderr")
                        with mock.patch.object(ht, "host_stderr_open", full):
                            return real_spawn(sess, spec_path, secret_env)
                    if arm == "eperm-at-fchmod":
                        def open_probe(*a, **k):
                            fd = real_open(*a, **k)
                            opened.append(fd)
                            return fd

                        def close_probe(fd):
                            closed.append(fd)
                            return real_close(fd)

                        def refused(fd, mode):
                            raise PermissionError(errno.EPERM, "fchmod refused (interposed)")
                        with mock.patch.object(os, "open", open_probe), mock.patch.object(os, "close", close_probe), \
                                mock.patch.object(os, "fchmod", refused):
                            return real_spawn(sess, spec_path, secret_env)
                    with mock.patch.object(sb.subprocess, "Popen", side_effect=FileNotFoundError(errno.ENOENT, "no such launcher", "romp-session-host")):
                        return real_spawn(sess, spec_path, secret_env)
                self.be._spawn_host = launch
                msg = self._connect()
                self.assertIsInstance(self.last_exc, sb.CLIConnectionErrorLike, "the launch error class, not a bare %r" % (self.last_exc,))
                self.assertEqual(getattr(self.last_exc, "errno", None), code, "the errno rides on the launch error")
                self.assertTrue(msg.startswith("the session host was not started: [Errno %d] " % code), msg)
                self.assertNotIn("STALE", msg)
                self.assertNotIn("replace it with a directory", msg, "no directory remedy: nothing was refused")
                self.assertEqual([r["kind"] for r in self._events()], [], "no session-events row: a filesystem failure is not a refusal")
                self.assertEqual(self.hosts, [], "no host process was started")
                self.assertFalse(os.path.exists(self.marker), "the CLI never started")
                self.assertTrue(any("the host process could not be started (its directory descent, its host.stderr open or the process start failed): [Errno %d]" % code in m
                                    for m in self.logs), "the error-centre line names the launcher's arm: %r" % (self.logs,))
                if arm == "eperm-at-fchmod":
                    self.assertEqual(len(opened), 3, "hosts/, hosts/<sid>/ and host.stderr's descriptors: %r" % (opened,))
                    self.assertEqual(sorted(closed), sorted(opened), "every descriptor the launcher opened was closed on the failure road")
                self.be._record_launch_error(self.sess, self.last_exc)
                rec = (sb.read_reg(Path(state), SID) or {}).get("launchError") or {}
                self.assertIn("[Errno %d]" % code, rec.get("text", ""), "the card reads the error, not the stale tail: %r" % (rec,))
                self.assertNotIn("STALE", rec.get("text", ""))

    def test_each_arm_of_the_spawn_road_names_itself_in_the_error_centre_line(self):
        """correctness-4 and kernel-3 (round 6 of the review, 2026-09-20): the handler's one line said the specification
        could not be written on the arm that runs AFTER the specification is on disk (the road's own descent), and the
        launcher's arm had no handler. Three arms, one injected failure each: ENOSPC at the spec write's second helper,
        EACCES at the road's descent (the second open_host_dirs of the connect; the first is write_spawn_spec's own, so
        spawn.json is on disk when this one fails, which the case reads), ENOSPC at the launcher's host.stderr open. Each
        line names its arm; each launch error carries the errno; nothing is refused and no process starts."""
        ht = sb._ht()
        real_owner = ht.sh.owner_only_dir
        real_descend = ht.open_host_dirs
        real_stderr_open = ht.host_stderr_open
        arms = (("spec", errno.ENOSPC, "the spawn specification could not be written"),
                ("descent", errno.EACCES, "the descent to the host directory failed after the specification was written"),
                ("launcher", errno.ENOSPC, "the host process could not be started (its directory descent, its host.stderr open or the process start failed)"))
        for arm, code, sentence in arms:
            with self.subTest(arm=arm):
                self.setUp()
                state = tempfile.mkdtemp()
                self.addCleanup(shutil.rmtree, state, True)
                self._harness(state)
                calls = []

                def owner(path, what="directory", parents=False):
                    if what == "host directory":
                        raise OSError(code, os.strerror(code), os.fspath(path))
                    return real_owner(path, what, parents)

                def descend(state_dir, sid):
                    calls.append(1)
                    if len(calls) == 2:
                        raise OSError(code, os.strerror(code), os.fspath(Path(state_dir) / "hosts"))
                    return real_descend(state_dir, sid)

                def stderr_open(dirs):
                    raise OSError(code, os.strerror(code), "host.stderr")
                with contextlib.ExitStack() as stack:
                    if arm == "spec":
                        stack.enter_context(mock.patch.object(ht.sh, "owner_only_dir", owner))
                    elif arm == "descent":
                        stack.enter_context(mock.patch.object(ht, "open_host_dirs", descend))
                    else:
                        stack.enter_context(mock.patch.object(ht, "host_stderr_open", stderr_open))
                    msg = self._connect()
                self.assertIsInstance(self.last_exc, sb.CLIConnectionErrorLike, repr(self.last_exc))
                self.assertEqual(getattr(self.last_exc, "errno", None), code)
                self.assertTrue(msg.startswith("the session host was not started: [Errno %d] " % code), msg)
                lines = [m for m in self.logs if "%s: [Errno %d]" % (sentence, code) in m]
                self.assertEqual(len(lines), 1, "the error-centre line names this arm once: %r" % (self.logs,))
                for other, _, other_sentence in arms:
                    if other != arm:
                        self.assertFalse(any(other_sentence in m for m in self.logs), "no other arm's sentence: %r" % (self.logs,))
                self.assertEqual([r["kind"] for r in self._events()], [], "nothing refused")
                self.assertEqual(self.hosts, [], "no process")
                self.assertEqual((Path(state) / "hosts" / SID / "spawn.json").exists(), arm != "spec",
                                 "the spec is on disk on the arms after its write, absent on the write arm")

    def test_a_hosts_swapped_after_the_roads_descent_leaves_the_peers_file_at_the_published_name_and_the_launcher_refuses(self):
        """tests-2 (round 5 of the review, 2026-09-20): the published socket's unlink takes a NAME relative to the held
        hosts/ descriptor, which no case held (moved back onto the path, the recipe stayed green). The fifth plant
        point the peer-swap case above lacks: after the road's own descent and before the unlink, planted on the road's
        own call between the two (ht.host_sock, wrapped to swap then delegate; write_spawn_spec's descent runs earlier,
        and a swap on that one reproduces the after-spec refusal instead). The peer's directory holds an empty <sid>/
        and a regular file of the peer's at the published name, <sid8>.sock. The unlink, by name under the verified
        hosts/ (renamed aside, ours), removes nothing of the peer's, and the launcher's own descent then refuses the
        link before Popen. Red with the unlink moved back onto the path: the peer's file at the published name is
        deleted through the link."""
        state = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, state, True)
        self._harness(state)
        hosts, moved = Path(state) / "hosts", Path(state) / "hosts.moved"
        peer = Path(self.scratch) / "peer"
        (peer / SID).mkdir(parents=True, mode=0o755)
        published = peer / sh.sock_names(SID)[0]
        published.write_text("the peer's own file at the published name")
        ht = sb._ht()
        real_sock = ht.host_sock
        calls = []

        def swap_then_name(state_dir, sid):
            calls.append(1)
            if len(calls) == 1:                          # the road's one call between its descent and the unlink
                os.rename(hosts, moved)
                hosts.symlink_to(peer)
            return real_sock(state_dir, sid)
        with mock.patch.object(ht, "host_sock", swap_then_name):
            msg = self._connect()
        self.assertEqual(len(calls), 1, "one call on this road, between the descent and the unlink")
        self.assertTrue(hosts.is_symlink(), "the link is left, not replaced")
        self.assertTrue(published.exists(), "the peer's file at the published name survives: the unlink took a name under the verified hosts/")
        self.assertEqual(published.read_text(), "the peer's own file at the published name")
        self.assertEqual(sorted(os.listdir(peer)), sorted([SID, published.name]), "the peer's directory holds what the peer put there")
        self.assertEqual(os.listdir(peer / SID), [], "and its <sid>/ received nothing")
        self.assertEqual(self.hosts, [], "no host process was started: the launcher's descent refused the link")
        self.assertTrue(msg.startswith("the session host was not started: hosts directory %s is a symlink, not a directory" % hosts), msg)
        self.assertEqual([r["kind"] for r in self._events()], ["host.directory-refused"])
        self.assertFalse((moved / published.name).exists(), "nothing of ours stood at the published name: the unlink found nothing")

    def test_a_peer_planted_host_log_behind_a_swap_after_both_descents_reaches_no_message_no_row_and_no_registry_position(self):
        """tests-2 (round 5 of the review, 2026-09-20): the refused roads' three reads of host.log (host_exit_reason for
        the reason, _file_refused_launch_context for the untested-version row, _record_refused_launch_position for
        hostLogPos) take a name relative to the held descriptor (_open_host_log's dir_fd then; the held HostDirs since the
        round-7 seventh addendum, 2026-09-20, which also asks the owner question of the entry), which no case held. The
        before-popen plant of the peer-swap case above, with the peer's <sid>/ holding a host.log of the peer's: a
        host-started row, an sdk-version-untested row and a host-crashed row naming a reason of the peer's. The host
        starts holding the kernel's descriptor, exits 1 (its spec is absent through the link), and every read the
        kernel then makes goes to the directory it verified, moved aside, where no host.log exists: the message names
        host.stderr under the condition and carries no reason of the peer's, the rows are the one
        host.exited-before-socket row and no host.sdk-untested row, and the registry keeps no hostLogPos. Red with
        _open_host_log moved back onto the path: the peer's reason is the card's, the peer's untested-version row is
        filed, and hostLogPos reads the peer's line count."""
        state = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, state, True)
        self._harness(state)
        hosts, moved = Path(state) / "hosts", Path(state) / "hosts.moved"
        peer = Path(self.scratch) / "peer"
        (peer / SID).mkdir(parents=True, mode=0o755)
        rows = [{"t": 1, "kind": "host-started"},
                {"t": 2, "kind": "sdk-version-untested", "installed": "9.9.9", "tested": "0.0.1", "relation": "newer"},
                {"t": 3, "kind": "host-crashed", "error": "PeerPlantedError", "errno": 99, "at": "peer.py:1"}]
        planted = "".join(json.dumps(r) + "\n" for r in rows)
        (peer / SID / "host.log").write_text(planted)

        def swap():
            os.rename(hosts, moved)
            hosts.symlink_to(peer)
        self.before_popen.append(swap)
        msg = self._connect()
        self.assertEqual(len(self.hosts), 1, "the host started with the descriptor the kernel opened before the swap")
        self.assertEqual(self.hosts[0].wait(10), 1)
        self.assertIn("exited before serving its socket (code 1)", msg)
        self.assertIn("see hosts/%s/host.stderr when host.log is missing" % SID, msg, "host.stderr grew, read through the held descriptor")
        self.assertNotIn("PeerPlantedError", msg, "the peer's reason is not this launch's: the read took the held descriptor")
        events = self._events()
        self.assertEqual([r["kind"] for r in events], ["host.exited-before-socket"], "no host.sdk-untested row from the peer's file")
        self.assertNotIn("PeerPlantedError", json.dumps(events))
        self.assertNotIn("9.9.9", json.dumps(events))
        reg = sb.read_reg(Path(state), SID) or {}
        self.assertIsNone(reg.get("hostLogPos"), "no host.log in the verified directory: no position recorded")
        self.assertEqual((peer / SID / "host.log").read_text(), planted, "the peer's file untouched")

    def test_the_spawn_waits_poll_reads_the_published_name_under_the_held_hosts_so_a_peers_entry_behind_a_swap_does_not_end_the_wait(self):
        """The spawn wait's poll through the descent (the round-7 second addendum of the review, 2026-09-20), on the
        production road: hosts/ is renamed aside and a symlink put in its place pointing at a directory of the peer's,
        planted after both descents and before the host process exists (inside the Popen wrapper); the peer's directory
        holds an empty <sid>/ and a regular file of the peer's at the published name, <sid8>.sock. Through round 7 the
        poll was `sock.exists()`, by PATH: it read the peer's entry through the link, the wait ended at once and the road
        handed back a transport aimed at the published path, which the connect would then have followed through the link
        to whatever the peer put at the name. Now the poll stats the published NAME under the hosts/ descriptor the road
        holds (host_sock_present), the directory the spec was written in, where nothing is published: the wait runs on,
        reads the host's exit (its spec is absent through the link, so it exits 1 with its traceback on the descriptor the
        launcher opened before the swap), and the road raises the exited-before-socket error with its row; the peer's
        entry stands untouched and no transport is built. Red before: the road returned a HostTransport."""
        state = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, state, True)
        self._harness(state)
        hosts, moved = Path(state) / "hosts", Path(state) / "hosts.moved"
        peer = Path(self.scratch) / "peer"
        (peer / SID).mkdir(parents=True, mode=0o755)
        published = peer / sh.sock_names(SID)[0]
        published.write_text("the peer's entry at the published name")

        def swap():
            os.rename(hosts, moved)
            hosts.symlink_to(peer)
        self.before_popen.append(swap)
        out, exc = self._connect_outcome()
        self.assertIsNone(out, "the wait ended on the peer's entry at the published name, read through the link, and handed back a transport: %r" % (out,))
        self.assertIsInstance(exc, sb.CLIConnectionErrorLike, repr(exc))
        msg = str(exc)
        self.assertIn("exited before serving its socket (code 1)", msg, "the wait ran on past the peer's entry and read the host's exit")
        self.assertIn("see hosts/%s/host.stderr when host.log is missing" % SID, msg, "host.stderr grew: read through the held descriptor")
        self.assertEqual(len(self.hosts), 1, "one host was started, holding the descriptor the kernel opened before the swap")
        self.assertEqual(self.hosts[0].wait(10), 1)
        self.assertTrue(hosts.is_symlink(), "the link is left, not replaced")
        self.assertEqual(published.read_text(), "the peer's entry at the published name", "the peer's entry untouched")
        self.assertEqual(sorted(os.listdir(peer)), sorted([SID, published.name]), "the peer's directory holds what the peer put there")
        self.assertEqual(os.listdir(peer / SID), [], "and its <sid>/ received nothing")
        self.assertFalse((moved / published.name).exists(), "nothing was published in the directory the kernel verified")
        self.assertEqual([r["kind"] for r in self._events()], ["host.exited-before-socket"])
        self.assertFalse(os.path.exists(self.marker), "the CLI never started: its marker is absent")
        self.assertIsNone(sb.read_lease(state, SID), "no lease was ever written")

    def test_the_spawn_wait_reads_the_exit_of_a_host_refused_before_its_cli_and_finds_no_lease_and_no_cli(self):
        self._harness(padded_root(self, sh.SOCK_PATH_MAX + 1, os.path.join("hosts", SID[:8] + ".sock")))
        msg = self._connect()
        self.assertIn("exited before serving its socket (code 1)", msg, "the spawn wait read the host's exit")
        self.assertEqual(len(self.hosts), 1, "one host was started")
        self.assertEqual(self.hosts[0].wait(10), 1, (Path(self.state) / "hosts" / SID / "host.stderr").read_text()[-800:])
        rows = [json.loads(l) for l in (Path(self.state) / "hosts" / SID / "host.log").read_text().splitlines()]
        self.assertEqual([r["kind"] for r in rows], ["host-started", "socket-bind-failed", "host-crashed"], rows)
        # the reason arm on a real host (round 5's addendum, 2026-09-19): this refusal wrote its rows, so the kernel read
        # the host-crashed row's error past its mark and the message names host.log alone, that error its tail; host.stderr,
        # the file of the class that wrote no row, is not named in this arm (SpawnWaitMessageArms reads every arm whole)
        self.assertTrue(msg.endswith("; see hosts/%s/host.log: %s" % (SID, rows[2]["error"])), msg)
        self.assertNotIn("host.stderr", msg, "a host that wrote a failing row wrote host.log: the other file is not named")
        row = rows[1]
        self.assertEqual((row["step"], row["error"], row["errno"], row["pathLen"], row["limit"]),
                         ("budget", "OSError", errno.ENAMETOOLONG, sh.SOCK_PATH_MAX + 1, sh.SOCK_PATH_MAX), row)
        self.assertNotIn(self.state, json.dumps(rows), "no row carries the state root")
        self.assertFalse(os.path.exists(self.marker), "the CLI never started: its marker is absent")
        self.assertIsNone(sb.read_lease(self.state, SID), "no lease was ever written")
        self.assertFalse(sb.lease_path(self.state, SID).exists())
        hosts = Path(self.state) / "hosts"
        self.assertFalse((hosts / (SID[:8] + ".sock")).exists(), "nothing published")
        self.assertEqual(sorted(p.name for p in hosts.glob("*.tmp")), [], "no temp left")

    def test_a_host_that_stalls_before_its_socket_is_ended_at_the_deadline_and_the_message_says_it_left_no_traceback(self):
        """kernel-5 (round 4 of the review, 2026-09-20), the deadline arm by execution on a real host: a fake
        claude_agent_sdk whose import sleeps stands where the SDK would be (ROMP_SDK_SITE and PYTHONPATH name its site),
        so the host writes its host-started row, runs the prelude, and stalls in _spawn's import before any CLI, lease or
        socket exists. With the kernel's wait patched short the deadline arm ends it: terminate(), SIGTERM, rc -15. What
        is true of that class, read back: host.stderr is 0 bytes (a host ended this way writes no traceback, so the
        exited arm's clause would have sent the operator to an empty file), host.log holds host-started and no failing
        row, no lease, no marker. The message says so: ended, which leaves no traceback, host.stderr carries nothing from
        this launch, then the host.log tail main's pins hold; the row is host.never-served-socket. Through round 3 the
        arm said "see host.log" alone for the class."""
        site = Path(self.scratch) / "stall-sdk"
        (site / "claude_agent_sdk").mkdir(parents=True)
        (site / "claude_agent_sdk" / "__init__.py").write_text("import time\ntime.sleep(600)\n")
        self.host_env = {"PYTHONUNBUFFERED": "1", "ROMP_SDK_SITE": str(site), "PYTHONPATH": str(site)}
        state = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, state, True)
        self._harness(state)
        with mock.patch.object(sb._ht(), "SOCKET_WAIT_S", 5.0):
            msg = self._connect()
        self.assertEqual(len(self.hosts), 1, "one host was started")
        self.assertEqual(self.hosts[0].wait(10), -signal.SIGTERM, "ended by terminate() at the deadline, not exited")
        err = Path(state) / "hosts" / SID / "host.stderr"
        self.assertEqual(os.stat(err).st_size, 0, "no traceback: the host was ended, it did not fail")
        rows = [json.loads(l) for l in (Path(state) / "hosts" / SID / "host.log").read_text().splitlines()]
        self.assertEqual([r["kind"] for r in rows], ["host-started"], "the host got past its start and stalled before the CLI")
        self.assertEqual(msg, "the session host did not serve its socket within 5 s; it was ended, which leaves no traceback; "
                              "hosts/%s/host.stderr carries nothing from this launch; see hosts/%s/host.log" % (SID, SID))
        self.assertEqual([r["kind"] for r in self._events()], ["host.never-served-socket"])
        self.assertFalse(os.path.exists(self.marker), "the CLI never started: its marker is absent")
        self.assertIsNone(sb.read_lease(state, SID), "no lease was ever written")


class SpawnWaitMessageArms(unittest.TestCase):
    """The spawn wait's message, composed per arm (round 5's addendum, 2026-09-19, closing the lens's two notes on round
    5's one string: with a reason in hand the kernel had already resolved "when it wrote no host.log", and over a
    host.log a previous host left that clause was false; round 4 of the review, 2026-09-20, split the no-reason arm on
    host.stderr's watermark, kernel-1 and correctness-1, and gave the deadline arm the same treatment, kernel-5). The
    real backend's two refused roads (_host_transport_for: the proc.poll() is not None arm, and the deadline arm with
    SOCKET_WAIT_S patched short) over a fake _spawn_host, the harness tests/test_session_host_sdk_pin.py HostProcess uses;
    the WHOLE message is read on each arm, the launch error and the error centre's row alike, never a substring alone. The
    shapes: a host that wrote a failing row (what happened, then the one file that holds the reason, the reason as its
    tail, and host.stderr not named); a host that wrote nothing anywhere (host.stderr named as carrying nothing from this
    launch, then the host.log tail main's pins hold); a host that wrote nothing over a host.log a previous host left,
    which a stale kernel-held lease keeps across launches (the same message as the second, read against a file that
    exists on disk with a stale row only and a previous reason the message does not carry); a host that wrote nothing
    over a host.stderr a PREVIOUS launch left (the same again: the previous traceback is not this launch's reason, which
    is what the watermark is for); a host that wrote to host.stderr through the kernel's own open (named under the
    condition the operator can read off host.log); and the deadline arm's three shapes. Each root declares the host road
    (`on` in session-hosts)."""

    _STALE_LEASE = {"pid": 2 ** 22 - 1, "start": "gone", "t": 0, "holder": {"kind": "kernel", "pid": 2 ** 22 - 2, "start": "gone"}}
    _HAPPENED = "the session host exited before serving its socket (code 1)"
    _NO_REASON_QUIET = _HAPPENED + "; hosts/%s/host.stderr carries nothing from this launch; see hosts/%s/host.log" % (SID, SID)
    _NO_REASON_STDERR = _HAPPENED + ("; see hosts/%s/host.stderr when host.log is missing or has no row from this launch, else see "
                                     "hosts/%s/host.log" % (SID, SID))
    _ENDED = "the session host did not serve its socket within 0 s; it was ended"
    _ENDED_QUIET = _ENDED + ", which leaves no traceback; hosts/%s/host.stderr carries nothing from this launch; see hosts/%s/host.log" % (SID, SID)
    _ENDED_STDERR = _ENDED + "; hosts/%s/host.stderr carries what it wrote before it stalled; see hosts/%s/host.log" % (SID, SID)

    def _root(self):
        d = tempfile.mkdtemp(prefix="swm-")
        self.addCleanup(shutil.rmtree, d, True)
        Path(d, "session-hosts").write_text("on")
        sb.write_reg(Path(d), SID, {"sid": SID, "name": "web", "alive": True, "lastSid": SID, "cwd": d})
        return d

    def _launch(self, d, rows, code=1, stderr=None, stall=None):
        """One connect through a host that appended `rows` to host.log (opening the file only when there is a row to
        write, so a host that wrote nothing leaves no file), wrote `stderr` (bytes) to host.stderr through the KERNEL'S
        own open (open_host_dirs and host_stderr_open, so the file's existence follows the launcher's road and is not the
        test's doing) and exited `code`; or, with `stall` (a list), a host that never exits: poll() stays None,
        SOCKET_WAIT_S is patched to 0.3 s and terminate() appends to the list. Returns the launch error's text and the
        error centre's rows."""
        be = sb.SdkBackend(d, "/bin/true", lambda *a, **k: None, log=lambda m, *a, **k: None)
        sess = types.SimpleNamespace(sid=SID, name="web", _host_intent=True, _host=None, _host_is_attach=False,
                                     _options_login="", _seed_for_dead_cli=lambda cli: None)

        def spawn(s, spec_path, secret_env=None):
            if rows:
                with open(Path(spec_path).parent / "host.log", "a") as f:
                    for row in rows:
                        f.write(json.dumps(row) + "\n")
            if stderr is not None:
                ht = sb._ht()
                with ht.open_host_dirs(d, SID) as dirs:
                    fd = ht.host_stderr_open(dirs)
                try:
                    os.write(fd, stderr)
                finally:
                    os.close(fd)
            if stall is not None:
                return types.SimpleNamespace(poll=lambda: None, returncode=None, pid=4242, terminate=lambda: stall.append(1))
            return types.SimpleNamespace(poll=lambda: code, returncode=code, pid=4242, terminate=lambda: None)
        with contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch.object(be, "_spawn_host", spawn))
            if stall is not None:
                stack.enter_context(mock.patch.object(sb._ht(), "SOCKET_WAIT_S", 0.3))
            with self.assertRaises(sb.CLIConnectionErrorLike) as cm:
                asyncio.run(be._host_transport_for(sess, types.SimpleNamespace(), (None, None, None)))
        p = Path(d) / sb.SESSION_EVENTS_FILE
        return str(cm.exception), [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []

    def test_a_host_that_wrote_a_failing_row_is_sent_to_host_log_alone_with_the_reason_as_the_tail(self):
        d = self._root()
        msg, events = self._launch(d, [{"t": 1, "kind": "host-started"}, {"t": 2, "kind": "cli-spawn-failed", "error": "TypeError"}])
        self.assertEqual(msg, self._HAPPENED + "; see hosts/%s/host.log: TypeError" % SID)
        self.assertEqual([(r["kind"], r["code"], r["text"]) for r in events],
                         [("host.exited-before-socket", 1, "the session host for web " + msg[len("the session host "):])],
                         "the error centre's row carries the same sentence")

    def test_a_host_that_left_no_host_log_and_wrote_nothing_to_host_stderr_gets_host_stderr_named_as_empty_and_the_host_log_tail(self):
        d = self._root()
        msg, events = self._launch(d, [])
        hd = sb._ht().host_dir(d, SID)
        self.assertFalse((hd / "host.log").exists(), "the shape: no host.log exists for this launch")
        self.assertFalse((hd / "host.stderr").exists(), "and no host.stderr either: the kernel's watermark is a stat, it creates nothing")
        self.assertEqual(msg, self._NO_REASON_QUIET)
        self.assertEqual([(r["kind"], r["code"], r["text"]) for r in events],
                         [("host.exited-before-socket", 1, "the session host for web " + msg[len("the session host "):])])

    def test_a_host_that_wrote_nothing_over_a_previous_hosts_log_gets_the_same_message_and_none_of_that_hosts_reason(self):
        """The shape round 5's clause was false for: host.log exists on disk, left by a previous host and kept by a stale
        kernel-held lease, and this launch's host added nothing to it. The previous host's reason is not this launch's,
        and host.stderr, unchanged, is named as carrying nothing from this launch."""
        d = self._root()
        hd = sb._ht().host_dir(d, SID)
        hd.mkdir(parents=True)
        stale = [{"t": 1, "kind": "host-started"}, {"t": 2, "kind": "host-crashed", "error": "OSError: a previous launch's reason"}]
        (hd / "host.log").write_text("".join(json.dumps(r) + "\n" for r in stale))
        sb.write_lease(d, dict(self._STALE_LEASE, sid=SID))
        self.assertEqual(sb.lease_state(sb.read_lease(d, SID), time.time()), "no-live-process", "the precondition: a stale kernel-held lease")
        msg, events = self._launch(d, [])
        self.assertTrue((hd / "host.log").exists(), "the shape: a host.log exists, and it is the previous host's")
        self.assertEqual([json.loads(l)["t"] for l in (hd / "host.log").read_text().splitlines()], [1, 2], "this launch's host added no row")
        self.assertEqual(msg, self._NO_REASON_QUIET)
        self.assertNotIn("previous launch", msg, "the previous host's reason is not this launch's")
        self.assertEqual([(r["kind"], r["code"]) for r in events], [("host.exited-before-socket", 1)])
        self.assertNotIn("previous launch", events[0]["text"])

    def test_a_host_that_wrote_nothing_over_a_previous_launchs_host_stderr_is_not_sent_to_that_traceback(self):
        """kernel-1 and correctness-1 (round 4 of the review, 2026-09-20): host.stderr is opened append-only by the launcher
        and a refused launch clears nothing, so under a stale kernel-held lease (which keeps the directory) a previous
        launch's traceback sits in the file when the next host runs. Through round 3 the no-reason arm named host.stderr
        whatever the file held, so the operator read that traceback as this launch's reason, the misattribution the kernel
        already prevents for host.log with its watermark. Now the kernel takes host.stderr's size beside host_log_mark,
        through the descriptor it holds, and a host that appended nothing gets the message that says so: host.stderr
        carries nothing from this launch, then the host.log tail; the planted traceback's text is in neither the launch
        error nor the row, and the file is byte-identical after the launch. Red on the head before the fix: the message
        named host.stderr under its condition."""
        d = self._root()
        hd = sb._ht().host_dir(d, SID)
        hd.mkdir(parents=True)
        previous = b"Traceback (most recent call last):\n  File \"session_host.py\", line 1, in <module>\nOSError: a previous launch's reason\n"
        (hd / "host.stderr").write_bytes(previous)
        sb.write_lease(d, dict(self._STALE_LEASE, sid=SID))
        self.assertEqual(sb.lease_state(sb.read_lease(d, SID), time.time()), "no-live-process", "the precondition: a stale kernel-held lease")
        msg, events = self._launch(d, [])
        self.assertEqual((hd / "host.stderr").read_bytes(), previous, "this launch's host appended nothing")
        self.assertEqual(msg, self._NO_REASON_QUIET)
        self.assertNotIn("see hosts/%s/host.stderr" % SID, msg, "the operator is not sent to the previous launch's traceback")
        self.assertNotIn("previous launch", msg)
        self.assertEqual([(r["kind"], r["code"]) for r in events], [("host.exited-before-socket", 1)])
        self.assertNotIn("previous launch", events[0]["text"])
        self.assertNotIn("see hosts/%s/host.stderr" % SID, events[0]["text"])

    def test_a_host_that_wrote_to_host_stderr_and_no_host_log_is_sent_to_host_stderr_under_the_condition(self):
        """The grown arm: the host wrote to host.stderr (through the kernel's own open, the launcher's road) and no host.log,
        the constructor-refusal class PreludeRefusalRead drives on a real host. The watermark shows the growth, so
        host.stderr is named under the condition the operator can read off host.log, then the host.log tail; the file is
        0600, read back."""
        d = self._root()
        msg, events = self._launch(d, [], stderr=b"Traceback (most recent call last):\nOSError: this launch's reason\n")
        hd = sb._ht().host_dir(d, SID)
        self.assertFalse((hd / "host.log").exists())
        self.assertEqual(stat.S_IMODE(os.lstat(hd / "host.stderr").st_mode), 0o600, "opened 0600 through the descent, read back")
        self.assertEqual(msg, self._NO_REASON_STDERR)
        self.assertEqual([(r["kind"], r["code"], r["text"]) for r in events],
                         [("host.exited-before-socket", 1, "the session host for web " + msg[len("the session host "):])])

    def test_the_deadline_arm_says_an_ended_host_left_no_traceback_and_names_host_stderr_only_when_it_wrote_there(self):
        """kernel-5 (round 4 of the review, 2026-09-20): the deadline arm, three shapes over a fake host that never exits
        (SOCKET_WAIT_S 0.3 s; terminate() recorded). A host that wrote nothing: ended, which leaves no traceback,
        host.stderr carries nothing from this launch, then the host.log tail main's pins hold. A host that wrote to
        host.stderr before it stalled: that file named for what it wrote, then the tail. A host that wrote a failing row
        and then wedged: host.log alone, the reason as the tail. Never the exited arm's clause (a traceback in
        host.stderr), which is false for a host ended by terminate(); PreludeRefusalRead drives the first shape on a real
        stalled host and reads host.stderr at 0 bytes."""
        for shape, rows, stderr, want in (
                ("wrote nothing", [], None, self._ENDED_QUIET),
                ("wrote to host.stderr", [], b"a warning line before the stall\n", self._ENDED_STDERR),
                ("wrote a failing row", [{"t": 1, "kind": "host-started"}, {"t": 2, "kind": "cli-spawn-failed", "error": "TypeError"}], None,
                 self._ENDED + "; see hosts/%s/host.log: TypeError" % SID)):
            with self.subTest(shape=shape):
                d = self._root()
                ended = []
                msg, events = self._launch(d, rows, stderr=stderr, stall=ended)
                self.assertEqual(ended, [1], "the host was ended")
                self.assertEqual(msg, want)
                self.assertEqual([(r["kind"], r["text"]) for r in events],
                                 [("host.never-served-socket", "the session host for web " + msg[len("the session host "):])])
                self.assertNotIn("code", events[0], "ended, not exited: no return code to record")

    def test_the_spawn_watermark_is_read_through_the_descriptor_so_a_hosts_swapped_at_the_mark_hides_no_reason_of_this_host(self):
        """tests-2 (round 5 of the review, 2026-09-20): host_log_mark's dir_fd (the held HostDirs since the round-7 seventh
        addendum, 2026-09-20), which no case held. The mark is taken
        after the road's descent and before the spawn; a hosts/ swapped for a link to a peer's directory holding a
        LONGER host.log at that moment and put back before the launch (ht.host_log_mark wrapped: swap, delegate,
        restore) would, by path, read the peer's size as the mark, past which this host's own failing row never lands,
        so the reason would not reach the operator. Through the descriptor the mark is the real file's, and the reason
        does. Red with host_log_mark moved back onto the path: the message says host.stderr carries nothing from this
        launch and names host.log with no reason."""
        d = self._root()
        hd = sb._ht().host_dir(d, SID)
        hd.mkdir(parents=True)
        (hd / "host.log").write_text(json.dumps({"t": 1, "kind": "host-started"}) + "\n")
        sb.write_lease(d, dict(self._STALE_LEASE, sid=SID))
        peer = Path(tempfile.mkdtemp(prefix="swm-peer-"))
        self.addCleanup(shutil.rmtree, peer, True)
        (peer / SID).mkdir(mode=0o755)
        (peer / SID / "host.log").write_text("".join(json.dumps({"t": i, "kind": "host-started"}) + "\n" for i in range(40)))
        self.assertGreater((peer / SID / "host.log").stat().st_size, 10 * (hd / "host.log").stat().st_size, "the peer's file is the longer one")
        hosts, moved = Path(d) / "hosts", Path(d) / "hosts.moved"
        ht = sb._ht()
        real_mark = ht.host_log_mark

        def mark_over_a_swap(dirs):
            os.rename(hosts, moved)
            hosts.symlink_to(peer)
            try:
                return real_mark(dirs)
            finally:
                os.unlink(hosts)
                os.rename(moved, hosts)
        with mock.patch.object(ht, "host_log_mark", mark_over_a_swap):
            msg, events = self._launch(d, [{"t": 2, "kind": "cli-spawn-failed", "error": "TypeError"}])
        self.assertEqual(msg, self._HAPPENED + "; see hosts/%s/host.log: TypeError" % SID, "this host's reason reached the operator")
        self.assertEqual([(r["kind"], r["code"]) for r in events], [("host.exited-before-socket", 1)])

    def test_a_host_that_appends_to_a_previous_launchs_host_stderr_is_sent_to_it_and_the_previous_bytes_still_head_the_file(self):
        """tests-3 (round 5 of the review, 2026-09-20): host.stderr's O_APPEND, the mechanism the watermark rests on,
        composed and pinned: under a stale kernel-held lease a previous launch's traceback, many times longer than
        what this launch writes, sits in the file, and this launch's host writes 30 bytes through the kernel's own
        open. The grown arm names host.stderr under the condition, and the file is the previous bytes then this
        launch's, both kept. Both assertions are needed: with O_TRUNC and a longer new write the size alone would still
        pass the mark. Red with O_APPEND replaced by O_TRUNC: the file holds this launch's bytes alone, below the mark,
        and the message says host.stderr carries nothing from this launch."""
        d = self._root()
        hd = sb._ht().host_dir(d, SID)
        hd.mkdir(parents=True)
        previous = (b"Traceback (most recent call last):\n" + b"  File \"session_host.py\", line 1, in <module>\n" * 20
                    + b"OSError: a previous launch's reason\n")
        (hd / "host.stderr").write_bytes(previous)
        sb.write_lease(d, dict(self._STALE_LEASE, sid=SID))
        this = b"OSError: this launch's reason\n"
        self.assertEqual(len(this), 30)
        self.assertGreater(len(previous), 10 * len(this))
        msg, events = self._launch(d, [], stderr=this)
        self.assertEqual((hd / "host.stderr").read_bytes(), previous + this, "appended: the previous bytes head the file, this launch's follow")
        self.assertEqual(msg, self._NO_REASON_STDERR)
        self.assertEqual([(r["kind"], r["code"]) for r in events], [("host.exited-before-socket", 1)])

    def test_a_host_stderr_a_previous_launch_left_at_0664_is_tightened_to_0600_when_this_launch_opens_it(self):
        """kernel-1 (round 5 of the review, 2026-09-20): host_stderr_open created the file at 0600 and never fchmod'd
        it, so a host.stderr a previous launch left at 0664 (every launch before round 4 opened it under the 002 umask;
        all nine on the live deployment read 0664) kept that mode, while spawn.json in the same directory pays
        os.fchmod for exactly that reason. Planted at 0664 under a stale kernel-held lease and opened by this launch
        through the kernel's own open: 0600 read back off the file, the previous bytes still heading it. Red before the
        change: 0664 stays."""
        d = self._root()
        hd = sb._ht().host_dir(d, SID)
        hd.mkdir(parents=True)
        previous = b"OSError: a previous launch's reason\n"
        (hd / "host.stderr").write_bytes(previous)
        os.chmod(hd / "host.stderr", 0o664)
        self.assertEqual(stat.S_IMODE(os.lstat(hd / "host.stderr").st_mode), 0o664, "the plant, read back")
        sb.write_lease(d, dict(self._STALE_LEASE, sid=SID))
        msg, events = self._launch(d, [], stderr=b"OSError: this launch's reason\n")
        self.assertEqual(stat.S_IMODE(os.lstat(hd / "host.stderr").st_mode), 0o600, "tightened on the descriptor by this launch's open, read back off the file")
        self.assertTrue((hd / "host.stderr").read_bytes().startswith(previous), "and appended, not replaced")
        self.assertEqual(msg, self._NO_REASON_STDERR)
        self.assertEqual([(r["kind"], r["code"]) for r in events], [("host.exited-before-socket", 1)])

class SocketFchmod(unittest.TestCase):
    def test_fchmod_on_a_bound_socket_descriptor_leaves_the_path_mode_alone(self):
        """Why _serve_socket tightens the temp by PATH: on Linux the listening descriptor is the socket, not the file
        the bind created, so fchmod on it changes the socket inode and the path's mode reads back unchanged; os.chmod
        on the path is what moves it (the pre-round of the socket-mode fix, 2026-09-19, pinning what the fix's docstring
        states from a probe). Under a 000 umask so the bind's own mode is unmistakable."""
        if not sys.platform.startswith("linux"):
            self.skipTest("the no-op is Linux's; other platforms may refuse the fchmod outright")
        self.addCleanup(os.umask, os.umask(0o000))
        d = tempfile.mkdtemp(prefix="fch-")
        self.addCleanup(shutil.rmtree, d, True)
        path = os.path.join(d, "s.sock")
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.addCleanup(s.close)
        s.bind(path)
        s.listen(1)
        self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o777, "the bind gives the umask's mode")
        os.fchmod(s.fileno(), 0o600)
        self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o777, "fchmod on the descriptor: the path's mode is unchanged")
        os.chmod(path, 0o600)
        self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600, "chmod on the path is the one that takes")


class HostProcess(unittest.TestCase):
    """Each test starts one host on the fake CLI in a private state root and kills everything after (one exception: the
    never-lands pin on _journal_landed writes the journal directory itself and starts no host)."""

    def setUp(self):
        self.state = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.state, True)
        self.fake_log = os.path.join(self.state, "fake-cli.log")
        self.tdir = os.path.join(self.state, "transcripts")

    def _overlay(self):
        """The spec's env overlay as a compose builds one for the fake CLI: its log, transcript dir and conversation id,
        and a canary value no test hands the CLI by another road (the secrets case reads it back to check it appears
        nowhere the host writes or sends). Its own method since review round 1's addendum (2026-09-18), so a case that
        builds the overlay itself and runs the kernel's split over it starts from the same one."""
        return {"FAKE_CLI_LOG": self.fake_log, "FAKE_CLI_TRANSCRIPT_DIR": self.tdir, "FAKE_CLI_SESSION_ID": FSID,
                "ROMP_CANARY_SECRET": "canary-" + uuid.uuid4().hex}

    def _spec(self, **over):
        d = Path(self.state) / "hosts" / SID
        d.mkdir(parents=True, mode=0o700)
        spec = {"sid": SID, "name": "web", "version": "abc12345", "state_dir": self.state, "protocol": 1,
                "cli_path": FAKE, "cwd": self.state, "permission_prompt_tool_name": "stdio", "permission_mode": "default",
                "env": self._overlay(),
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

    def _journal_landed(self, n, timeout=15):
        """The journal once the writer has landed `n` records: the host forwards a record to the kernel at once and
        journals it on its own writer task, so a frame on the socket says nothing about the disk yet (the writer may
        lag by design, and a slow runner's disk shows it: the macOS cell read three records where the socket had four,
        2026-09-16). The event waited on is the n-th record on disk, never a fixed pause.

        On the deadline the wait FAILS, naming what it saw (2026-09-19, the reviewer's ruling on the journal-fault
        test's wait: a read that cannot tell a late landing from one that never happens must not report never). It used
        to return the short list silently, so a record that never landed failed the caller's assertion as a numbering
        mismatch, `[0] != [0, 2]`, fifteen seconds later: the very message the wait exists to eliminate. The failure now
        reads as the writer's, with the count waited for, the count found, the offsets found and the timeout in
        seconds. `timeout` is that deadline, so a test can pin the failure quickly (the never-lands test below, at 0.3 s).
        Shared by the turn test, the lagging-writer test and the journal-fault test, whose deadlines now fail this way."""
        d = os.path.join(self.state, "hosts", SID)
        deadline = time.time() + timeout
        journal = list(sh.read_journal_dir(d))
        while time.time() < deadline and len(journal) < n:                # loop-ok: the event is the writer's n-th record on disk
            time.sleep(0.005)
            journal = list(sh.read_journal_dir(d))
        if len(journal) < n:
            self.fail("the journal writer never landed %d records within %g s: %d found, at offsets %r"
                      % (n, timeout, len(journal), [o for o, _ in journal]))
        return journal

    def test_the_journal_wait_fails_naming_what_it_saw_when_the_records_never_land(self):
        """_journal_landed against its refusable input: a journal directory that never reaches the waited count (one
        record on disk and no host to land another). On the deadline the helper fails, and the message carries the four
        facts that tell a writer fault from a numbering mismatch: the count waited for, the count found, the offsets
        found and the timeout in seconds. Red on the helper before 2026-09-19, which returned the one record silently."""
        d = os.path.join(self.state, "hosts", SID)
        os.makedirs(d, mode=0o700)      # made here: Journal makes no parent since the socket-mode fix's round 2 (owner_only_dir,
        #                                 2026-09-19), the host's directory existing before a host opens its journal; this case is
        #                                 about the wait's message, not the directory
        j = sh.Journal(d)
        j.append({"type": "assistant", "n": 0}); j.close()
        t0 = time.time()
        with self.assertRaises(AssertionError) as cm:
            self._journal_landed(2, timeout=0.3)
        self.assertLess(time.time() - t0, 10, "the deadline is the argument, not the 15 s default")
        msg = str(cm.exception)
        for fact in ("never landed 2 records", "1 found", "offsets [0]", "within 0.3 s"):
            self.assertIn(fact, msg, "the failure names " + fact)
    def test_the_served_socket_is_owner_only_and_the_kernel_side_attaches_through_it(self):
        """The real host over a scratch state root, spawned under a 000 umask (2026-09-18, the socket-mode fix split out
        of PR 789's round 1): hosts/<sid8>.sock is 0600 once served, the temp name the host bound at is gone,
        and the kernel's own HostTransport connects through the published name and gets hello. A rename keeps the
        listening socket (AF_UNIX resolves a path to its inode); SocketMode's in-process cases do not prove that.
        This case is the rename-keeps-a-serveable-socket guard, not a creation-mode pin: its mode leg is a stat once
        the host is up, which the old code's chmod-after-bind satisfied too, so it is green on the base (round 1,
        2026-09-19); the creation mode is pinned by SocketMode's interposed cases."""
        self.addCleanup(os.umask, os.umask(0o000))      # the child inherits it: the mode below is the host's doing alone
        host, sock, spec = self._start()
        self.assertEqual(stat.S_IMODE(os.stat(sock).st_mode), 0o600)
        kinds = [r["kind"] for r in self._hostlog()]
        self.assertIn("socket-ready", kinds)
        self.assertNotIn("socket-bind-failed", kinds)
        self.assertEqual(sorted(p.name for p in (Path(self.state) / "hosts").glob("*.tmp")), [], "no temp left in hosts/")

        ht = sb._ht()       # the kernel's own loader, at test time: a module-level load_source here ran at collection,
        #                     before test_host_transport.py put the SDK on sys.path, and left HostTransport on the plain
        #                     base for that module's pins (the same worker, 2026-09-18)

        async def go():
            t = ht.HostTransport(sock, kernel={"pid": 4242, "start": "1", "version": "abc12345"}, ack=-1)
            await asyncio.wait_for(t.connect(), 10)
            hello = t.hello
            await t.close()                              # the initialize unanswered: a detach, and the host keeps its CLI
            return hello
        hello = asyncio.run(go())
        self.assertEqual((hello or {}).get("t"), "hello", hello)
        self.assertIsNone(host.poll(), "the host lives on after the detach")

    def test_the_socket_is_served_where_the_published_path_is_exactly_the_budget(self):
        """The real host under a state root padded so hosts/<sid8>.sock is exactly sun_path's usable length (107 bytes on
        Linux, 103 on macOS): the sweep's xdist nesting puts a served state root there (2026-09-18), and the bind must
        succeed with the socket 0600 and the kernel side attaching. This is the length bound on the temp name, tested by
        execution; SocketMode's unit case computes it."""
        budget = sh.SOCK_PATH_MAX
        self._pad_state_to(budget)
        host, sock, spec = self._start()
        self.assertEqual(len(sock), budget, sock)
        self.assertEqual(stat.S_IMODE(os.stat(sock).st_mode), 0o600)
        rows = {r["kind"]: r for r in self._hostlog()}
        self.assertNotIn("socket-bind-failed", rows)
        ready = rows["socket-ready"]
        self.assertEqual((ready["sock"], ready["pathLen"]), (os.path.basename(sock), budget), ready)
        self.assertLessEqual(len(ready["tmp"]), len(ready["sock"]), ("the temp the host bound is no longer than the published name", ready))
        self.assertEqual(sh.temp_owner_pid(ready["tmp"]), host.pid, "and it embeds the host's own pid")
        k, hello = self._attach(sock)
        self.assertEqual(hello.get("t"), "hello", hello)
        k.s.close()

    def _pad_state_to(self, total):
        """Move the state root to a padded directory so hosts/<sid8>.sock is exactly `total` bytes (padded_root: under the
        system temp dir, never a skip). The fake CLI's log and transcript dir stay under the root setUp made."""
        self.state = padded_root(self, total, os.path.join("hosts", sh.sock_names(SID)[0]))

    def test_a_published_path_one_byte_over_the_budget_ends_the_real_host_loudly_with_nothing_kept(self):
        """The high of round 1 (2026-09-19) as the kernel would meet it: the real bin/romp-session-host under a state root
        padded so hosts/<sid8>.sock is SOCK_PATH_MAX + 1 bytes (108 on Linux). The first cut bound its shorter temp,
        renamed it onto the over-budget path, logged socket-ready and kept its lease and its CLI while every kernel
        connect raised; the code before failed the bind loudly and exited 1. Now: exit 1, and host.log reads
        host-started, the socket-bind-failed row (step budget, ENAMETOOLONG, the length and the limit) and host-crashed
        and NOTHING ELSE: no cli-spawned row, because since round 3 (the reviewer's reorder ruling, 2026-09-19) the
        budget is read before the CLI is spawned, so no CLI was ever started and no lease ever written. Through round 2
        this case read a cli-spawned row and asserted that CLI gone and the lease removed; a refusal that starts nothing
        is the stronger property. The CLI the spec names is a marker script that records its start, so the claim is read
        from the marker's absence as well as the rows. No path in any row, no socket, no temp, no lease on disk."""
        budget = sh.SOCK_PATH_MAX
        marker = os.path.join(self.state, "cli-started")
        cli = os.path.join(self.state, "marker_cli.py")
        Path(cli).write_text("#!%s\nimport sys\nopen(%r, 'w').close()\nsys.stdin.read()\n" % (sys.executable, marker))   # marks its start, lives to EOF
        os.chmod(cli, 0o700)
        self._pad_state_to(budget + 1)
        spec_path, spec = self._spec(cli_path=cli)
        env = dict(os.environ, PYTHONUNBUFFERED="1", ROMP_SDK_SITE=os.path.join(self.state, "no-sdk-here"))
        for name in sb.AUTH_ENV_NAMES:
            env.pop(name, None)
        host = subprocess.Popen([sys.executable, os.path.join(BIN, "romp-session-host"), spec_path],
                                stdout=subprocess.DEVNULL, stderr=open(os.path.join(self.state, "host.stderr"), "w"), env=env,
                                start_new_session=True)
        self.addCleanup(self._kill_group, host)
        rc = host.wait(timeout=30)
        self.assertEqual(rc, 1, open(os.path.join(self.state, "host.stderr")).read()[-800:])
        rows = self._hostlog()
        kinds = [r["kind"] for r in rows]
        self.assertEqual(kinds, ["host-started", "socket-bind-failed", "host-crashed"],
                         "started, refused before the CLI, crashed: no cli-spawned, no socket-ready, no lease-kept")
        self.assertFalse(os.path.exists(marker), "the CLI never started: its marker is absent")
        by = {r["kind"]: r for r in rows}
        row = by["socket-bind-failed"]
        self.assertEqual((row["step"], row["error"], row["errno"], row["pathLen"], row["limit"]),
                         ("budget", "OSError", errno.ENAMETOOLONG, budget + 1, budget), row)
        crashed = by["host-crashed"]
        self.assertEqual(crashed["error"], "OSError", crashed)
        self.assertTrue(crashed["at"].startswith("session_host.py:"), crashed)
        self.assertNotIn(self.state, json.dumps(rows), "no row carries the state root")
        self.assertLess(kinds.index("socket-bind-failed"), kinds.index("host-crashed"))
        sock = Path(self.state) / "hosts" / sh.sock_names(SID)[0]
        self.assertEqual(len(str(sock)), budget + 1)
        self.assertFalse(sock.exists(), "nothing published")
        self.assertEqual(sorted(p.name for p in (Path(self.state) / "hosts").glob("*.tmp")), [], "no temp left")
        self.assertIsNone(self._lease(), "no lease was ever written")
        self.assertFalse(sb.lease_path(self.state, SID).exists())

    def test_a_real_host_leaves_hosts_owner_only(self):
        """The real bin/romp-session-host, spawned under a 000 umask over a state root whose `hosts/` _spec left at that
        umask's mode (0777, the parents=True mkdir): once the host serves its socket, `hosts/` is 0700, the directory's
        mode set by the host's own code (sh.hosts_dir) and not by any umask (the pre-round of this fix, 2026-09-19). The
        in-process SocketMode case pins the same road through run(); this one pins it for the process the kernel starts."""
        self.addCleanup(os.umask, os.umask(0o000))
        hosts = Path(self.state) / "hosts"
        host, sock, spec = self._start()
        self.assertEqual(stat.S_IMODE(os.stat(hosts).st_mode), 0o700, "hosts/ is owner-only once the socket is served")
        self.assertEqual(stat.S_IMODE(os.stat(sock).st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(os.stat(hosts / SID).st_mode), 0o700)
        self.assertNotIn("socket-bind-failed", [r["kind"] for r in self._hostlog()])

    def test_a_real_host_over_a_symlinked_session_directory_exits_and_writes_nothing_through_the_link(self):
        """The host's creator of hosts/<sid>/, as the kernel would meet it (the review's round 2, 2026-09-19): the real
        bin/romp-session-host started over a spec whose hosts/<sid>/ is a symlink to a directory elsewhere. Round 1's host
        wrote host.log, identity.json and the journal through the link and served its socket; now the constructor's
        owner-only check refuses the directory before any of them, the process exits 1 with the refusal on its stderr
        (the traceback names the directory, which is the operator's own state root), nothing new lands in the target, no
        socket is published and no lease is written."""
        spec_path, spec = self._spec()
        sdir = Path(spec_path).parent
        target = Path(self.state) / "elsewhere"
        os.rename(sdir, target)
        sdir.symlink_to(target)
        before = sorted(p.name for p in target.iterdir())
        env = dict(os.environ, PYTHONUNBUFFERED="1", ROMP_SDK_SITE=os.path.join(self.state, "no-sdk-here"))
        for name in sb.AUTH_ENV_NAMES:
            env.pop(name, None)
        host = subprocess.Popen([sys.executable, os.path.join(BIN, "romp-session-host"), spec_path],
                                stdout=subprocess.DEVNULL, stderr=open(os.path.join(self.state, "host.stderr"), "w"), env=env,
                                start_new_session=True)
        self.addCleanup(self._kill_group, host)
        rc = host.wait(timeout=30)
        err = open(os.path.join(self.state, "host.stderr")).read()
        self.assertEqual(rc, 1, err[-800:])
        self.assertIn("host directory", err)
        self.assertIn("is not a directory", err)
        self.assertEqual(sorted(p.name for p in target.iterdir()), before, "nothing written through the link")
        self.assertEqual(before, ["spawn.json"])
        self.assertTrue(sdir.is_symlink(), "the link is left, not replaced")
        self.assertFalse((Path(self.state) / "hosts" / sh.sock_names(SID)[0]).exists(), "no socket published")
        self.assertEqual(sorted(p.name for p in (Path(self.state) / "hosts").glob("*.tmp")), [], "no temp bound")
        self.assertIsNone(self._lease(), "no lease written: no CLI was spawned")

    def test_a_real_host_over_a_symlinked_hosts_exits_before_its_first_row_writes_nothing_through_the_link_and_starts_no_cli(self):
        """The twin of the case above for hosts/ itself (review round 3, 2026-09-19, kernel-2): the real
        bin/romp-session-host started over a spec whose hosts/ is a symlink to a directory elsewhere, with a marker
        script as the CLI. Through round 2 the host's guard of hosts/ ran only at the socket road: this launch wrote
        host.log, identity.json and journal-0.jsonl through the link and spawned a real CLI, and refused at the bind
        about 660 ms later. Now the constructor guards hosts/ before it opens the journal: exit 1 with the refusal on
        the host's captured stderr (the traceback names the directory, the operator's own state root), the link's target
        holds exactly what it held before (the session directory and its spawn.json), NO host.log row exists (the shape
        the kernel's spawn-wait message names host.stderr for), the marker never appears, no socket, no temp, no lease."""
        marker = os.path.join(self.state, "cli-started")
        cli = os.path.join(self.state, "marker_cli.py")
        Path(cli).write_text("#!%s\nimport sys\nopen(%r, 'w').close()\nsys.stdin.read()\n" % (sys.executable, marker))   # marks its start, lives to EOF
        os.chmod(cli, 0o700)
        spec_path, spec = self._spec(cli_path=cli)
        hosts = Path(self.state) / "hosts"
        target = Path(self.state) / "elsewhere"
        os.rename(hosts, target)
        hosts.symlink_to(target)
        before = sorted(str(p.relative_to(target)) for p in target.rglob("*"))
        self.assertEqual(before, [SID, os.path.join(SID, "spawn.json")], "the planted shape: the session directory and its spec")
        env = dict(os.environ, PYTHONUNBUFFERED="1", ROMP_SDK_SITE=os.path.join(self.state, "no-sdk-here"))
        for name in sb.AUTH_ENV_NAMES:
            env.pop(name, None)
        host = subprocess.Popen([sys.executable, os.path.join(BIN, "romp-session-host"), spec_path],
                                stdout=subprocess.DEVNULL, stderr=open(os.path.join(self.state, "host.stderr"), "w"), env=env,
                                start_new_session=True)
        self.addCleanup(self._kill_group, host)
        rc = host.wait(timeout=30)
        err = open(os.path.join(self.state, "host.stderr")).read()
        self.assertEqual(rc, 1, err[-800:])
        self.assertIn("hosts directory", err, "refused by the guard on hosts/, by its noun")
        self.assertIn("is not a directory", err)
        self.assertEqual(sorted(str(p.relative_to(target)) for p in target.rglob("*")), before,
                         "nothing written through the link: no host.log, no identity.json, no journal segment")
        self.assertEqual(self._hostlog(), [], "no host.log row exists for this refusal")
        self.assertFalse(os.path.exists(marker), "the CLI never started: its marker is absent")
        self.assertTrue(hosts.is_symlink(), "the link is left, not replaced")
        self.assertFalse((target / sh.sock_names(SID)[0]).exists(), "no socket published")
        self.assertEqual(sorted(p.name for p in target.glob("*.tmp")), [], "no temp bound")
        self.assertIsNone(self._lease(), "no lease written: no CLI was spawned")

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
        journal = self._journal_landed(len(kinds))                        # the writer lands them behind the socket, by design
        self.assertEqual([r["type"] for _, r in journal], kinds, "the journal holds every record the CLI emitted, in order")
        self.assertEqual(self._lease()["fsid"], FSID, "the lease's conversation id follows the init (it started as the romp sid)")
        k.send({"t": "ack", "offset": res["offset"]})
        # secrets: the canary environment value appears nowhere the host writes or sends
        canary = spec["env"]["ROMP_CANARY_SECRET"]
        blob = json.dumps(self._hostlog()) + json.dumps([r for _, r in journal]) + json.dumps(k.frames)
        self.assertNotIn(canary, blob, "no environment value in host.log, the journal or a frame")
        self.assertNotIn("FAKE_CLI_LOG", json.dumps(self._hostlog()), "no spec content in host.log")
        k.close()

    def test_the_journal_lands_every_record_behind_the_socket_when_the_writer_lags(self):
        """The reorder forced through the host's own seam: a writer that lands each record 0.4 s late. The socket
        delivers the whole turn first (the host never pauses the reader for the disk); a journal read at that instant
        holds fewer records than the socket did (the macOS cell's failure, 2026-09-16, with no seam: a slower disk), and
        the journal holds them all, in order, once the writer has landed them. The test reads the journal at the frame
        and again at the event, so the ordering the host promises (every record, in order, eventually) is what is pinned,
        never the instant the disk catches up."""
        host, sock, spec = self._start(_test_journal_delay_s=0.4)
        k, _ = self._attach(sock)
        k.send({"t": "in", "data": self._user("hello sleep=0")})
        k.recv_until(lambda f: f.get("t") == "out" and f["data"].get("type") == "result", timeout=15)
        kinds = [f["data"]["type"] for f in k.outs()]
        self.assertEqual(kinds[-1], "result")
        at_the_frame = list(sh.read_journal_dir(os.path.join(self.state, "hosts", SID)))
        self.assertLess(len(at_the_frame), len(kinds), "with the writer lagging, the disk trails the socket at the frame (the shape the assertion must not read)")
        journal = self._journal_landed(len(kinds), timeout=20)
        self.assertEqual([r["type"] for _, r in journal], kinds, "and holds every record, in the socket's order, once the writer landed them")
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
        # The journal read below waits for the records to land (2026-09-19): the host sends a record's `out` frame one
        # event-loop turn BEFORE its writer task appends it (publication precedes durability, by design: the module
        # docstring of kernel/session_host.py), so a read at the result frame can see [0] where [0, 2] land a moment later,
        # as a loaded full-suite run did. The wait is _journal_landed, the turn test's precedent (4ec6da845); the writer
        # delay makes the late landing certain instead of a matter of scheduling. Of the two sibling tests that wait, the
        # lagging-writer one carries the delay knob (at 0.4 s) and the turn test does not.
        host, sock, spec = self._start(_test_journal_fault_at=1, _test_journal_delay_s=0.05)
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
        landed = [o for o in range(len(k.outs())) if o != 1]               # every live offset but the faulted one
        offs = [o for o, _ in self._journal_landed(len(landed))]          # readers skip the gap marker, so the count is theirs
        self.assertNotIn(1, offs, "the failed record is a gap the readers skip")
        self.assertEqual(offs, landed, "the numbering around the gap holds")
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

    def _env_probe_cli(self, name="CLAUDE_CODE_OAUTH_TOKEN"):
        """A CLI stand-in that records whether `name` (the login token by default) is set in ITS environment
        (presence only, never the value) and then becomes the fake CLI. Returns (cli_path, the record's path)."""
        seen = os.path.join(self.state, "cli-env-seen")
        probe = os.path.join(self.state, "cli-env-probe.py")
        with open(probe, "w") as f:
            f.write("#!%s\nimport os, sys\n" % sys.executable)
            f.write("open(%r, 'w').write('present' if os.environ.get(%r) else 'absent')\n" % (seen, name))
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

    def test_a_moved_name_in_the_hosts_environment_reaches_the_cli_the_same_way(self):
        """A name of spawn_env_secret_names' shape beyond the three login names (a synthetic _TOKEN here) takes the login
        token's road since 2026-09-18 (the box admin's hazard review of the pull-in, 2026-09-16): out of the spec, into
        the host's process environment, and from there into the CLI. The host's environment is DERIVED from the kernel's
        split here, never handed over by the test: the overlay is built with the name, split_spawn_secrets moves it out
        of a spec holder as _host_transport_for does before the write, the split overlay is the spec the host reads, and
        the returned dict is the host's environment (review round 1's addendum, 2026-09-18: the first cut put the
        variable in host_env by hand, so it passed on the base tree, whose split moved the three login names alone, and
        pinned nothing of the kernel's road).

        The discriminating assertions are the spec's contents and the absence of the value under hosts/, NOT the CLI
        probe: on the base tree the CLI reads the variable present anyway, because the host lays the spec's overlay over
        its own environment, so the probe leg is true on both trees and only the file assertions turn this red before
        the change (the refuter's caveat, kept here so nobody strengthens the wrong leg)."""
        probe, seen = self._env_probe_cli("NOTES_API_TOKEN")
        val = "synthetic-notes-token-" + uuid.uuid4().hex
        holder = {"sid": SID, "env": dict(self._overlay(), NOTES_ENDPOINT="http://notes.test", NOTES_API_TOKEN=val)}
        secrets = sb.split_spawn_secrets(holder)          # the kernel's split over the overlay, the spec's env its remainder
        host, sock, spec = self._start(host_env=secrets, cli_path=probe, env=holder["env"])
        self.assertNotIn("NOTES_API_TOKEN", json.dumps(spec), "the spec the host read carries no such name: the split moved it")
        self.assertEqual(spec["env"].get("NOTES_ENDPOINT"), "http://notes.test", "the plain name stays in the spec")
        blob = "".join(q.read_bytes().decode("utf-8", "replace") for q in (Path(self.state) / "hosts").rglob("*") if q.is_file())
        self.assertNotIn(val, blob, "the value is in no file under hosts/")
        self.assertEqual(sorted(secrets), ["NOTES_API_TOKEN"], "the split's return is the host's whole credential environment")
        self.assertTrue(secrets["NOTES_API_TOKEN"] == val)
        k = self._one_turn(sock)
        # true on the base tree too (the host lays the spec's overlay over its environment): not the discriminating leg
        self.assertEqual(open(seen).read(), "present", "the CLI inherited the variable from the host's environment")
        blob = "".join(q.read_bytes().decode("utf-8", "replace") for q in (Path(self.state) / "hosts").rglob("*") if q.is_file())
        self.assertNotIn(val, blob + json.dumps(k.frames), "after a turn: the value is in no file under hosts/ and no frame")
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

    def test_a_pick_held_for_live_work_asks_the_host_to_end_its_cli_at_the_settle_and_a_fresh_host_lands_it(self):
        """The settings-pick hold on the HOSTED road, end to end (the pull-in review's fresh-2, 2026-09-16: no hold case
        ran with hosts on, the default every deployed session runs). The real backend loop, hosts on, spawns a real
        host with this file's fake CLI behind it through _host_transport_for, and _PickSdk's client drives the real
        HostTransport. A live subagent holds an effort pick; the settle of a turn that finds the sets empty arms the
        reconnect; the teardown's close asks the host to END its CLI (the exit frame's cause is `end`; the host removes
        its lease and leaves: never a detach, which would keep the old CLI running beside the new one); the next connect
        spawns a fresh host and lands the pick there. Not asserted: that the hello landed the shape (the connect-landed
        call stamps it after the handshake, on both roads). A private synthetic sid; every process the backend starts is
        ended by the test and killed by its cleanup if it is not."""
        sid = "7c0e5d1a-3b2f-4e6d-9a8b-000000000315"
        saved_site = os.environ.get("ROMP_SDK_SITE")
        os.environ["ROMP_SDK_SITE"] = os.path.join(self.state, "no-sdk-here")   # the spawned host inherits it: the pipe transport

        def restore_site():
            if saved_site is None:
                os.environ.pop("ROMP_SDK_SITE", None)
            else:
                os.environ["ROMP_SDK_SITE"] = saved_site
        self.addCleanup(restore_site)
        saved_sdk = _PickSdk.install()
        self.addCleanup(lambda: sys.modules.__setitem__("claude_agent_sdk", saved_sdk) if saved_sdk is not None
                        else sys.modules.pop("claude_agent_sdk", None))
        _PickSdk.ClaudeSDKClient.instances = []
        saved_refresh = sb.SdkSession._do_refresh_usage

        async def _noop_refresh(self_):
            pass
        sb.SdkSession._do_refresh_usage = _noop_refresh
        self.addCleanup(setattr, sb.SdkSession, "_do_refresh_usage", saved_refresh)
        journal = Path(os.environ["XDG_STATE_HOME"]) / "romp" / "overrides" / (sid + ".jsonl")   # the pick's override
        self.addCleanup(lambda: journal.unlink(missing_ok=True))
        Path(self.state, "session-hosts").write_text("on")
        cwd = os.path.join(self.state, "proj")
        os.makedirs(cwd)
        lines = []
        be = sb.SdkBackend(self.state, FAKE, lambda *a, **k: None, log=lambda m, **k: lines.append(str(m)))
        procs = []
        real_spawn = be._spawn_host

        def spawn(sess, spec_path, secret_env=None):
            p = real_spawn(sess, spec_path, secret_env)
            procs.append(p)
            return p
        be._spawn_host = spawn
        self.addCleanup(lambda: [self._kill_group(p) for p in procs])
        reg = {"sid": sid, "name": "web", "mode": "default", "effort": "high", "alive": True, "cwd": cwd}
        sb.write_reg(self.state, sid, reg)
        s = sb.SdkSession(be, dict(reg))
        be.sessions[sid] = s

        def stop():
            if s.thread.is_alive():
                s.shutdown()
            if s.thread.ident is not None:
                s.thread.join(timeout=30)
        self.addCleanup(stop)

        def wait(pred, what, timeout=45.0):
            end = time.time() + timeout
            while time.time() < end:   # loop-ok: a bounded poll
                if pred():
                    return
                time.sleep(0.02)
            self.fail("timed out waiting for %s; hosts %d; log tail %r" % (what, len(procs), lines[-10:]))

        def settled(what):
            done = threading.Event()   # a barrier behind the loop's current step (the pick class's _settled says why)
            s.loop.call_soon_threadsafe(done.set)
            self.assertTrue(done.wait(10.0), "timed out at the barrier for %s; log tail %r" % (what, lines[-10:]))

        def cli_of(client):
            c = client.transport.hello["cli"]
            return "%s:%s" % (c["pid"], c["start"])
        clients = _PickSdk.ClaudeSDKClient.instances
        s.start()
        wait(lambda: s.client is not None and s._launched_effort is not None, "the first connect landed on a host")
        settled("the first landing")
        self.assertEqual(len(procs), 1, "one host, spawned by the backend")
        t1 = clients[0].transport
        self.assertIsInstance(t1, sb._ht().HostTransport, "the real transport over the host's socket")
        self.assertEqual(sb.read_reg(self.state, sid).get("spawnedAtCli"), cli_of(clients[0]), "the hello stamped the fresh CLI")
        self.assertEqual(((sb.read_lease(self.state, sid) or {}).get("holder") or {}).get("pid"), procs[0].pid, "the host holds the lease")
        asyncio.run(s._subagent_start_hook({"agent_id": "a1", "agent_type": "general-purpose"}, None, None))
        self.assertTrue(be.set_effort(sid, "low"))
        wait(lambda: s._reconnect_when_idle, "the request ran on the loop")
        self.assertTrue(s._reconnect_held_for_work)
        self.assertEqual(s.snapshot()["pickHeld"]["surfaces"], ["effort"])
        time.sleep(0.3)
        self.assertIsNone(t1.exit_info, "the host was not asked to end while the work lives")
        self.assertIsNone(procs[0].poll())
        asyncio.run(s._subagent_stop_hook({"agent_id": "a1", "agent_type": "general-purpose"}, None, None))
        be.send(sid, "carry on sleep=0.1")     # a turn through the host to the fake CLI: its settle finds no live work and arms
        wait(lambda: len(clients) == 2 and clients[1] is s.client and s._launching is None and s._effort_pending == "",
             "the reconnect landed on a fresh host")
        settled("the second landing")
        self.assertEqual((t1.exit_info or {}).get("cause"), "end", "the teardown asked the host to end its CLI: its exit frame says so")
        self.assertTrue(clients[0].torn_down)
        self.assertEqual(procs[0].wait(timeout=15), 0, "the ended host left")
        self.assertTrue(any("the CLI exited (end, code 0)" in l for l in lines), lines[-10:])
        self.assertEqual(len(procs), 2, "a fresh host for the reconnect")
        self.assertIsNone(procs[1].poll())
        self.assertEqual(((sb.read_lease(self.state, sid) or {}).get("holder") or {}).get("pid"), procs[1].pid, "the fresh host holds the lease")
        self.assertNotEqual(cli_of(clients[1]), cli_of(clients[0]), "a fresh CLI under the fresh host")
        self.assertEqual(sb.read_reg(self.state, sid).get("spawnedAtCli"), cli_of(clients[1]), "the fresh host's hello stamped it")
        self.assertEqual(clients[1].options.effort, "low", "the fresh host was spawned with the pick")
        self.assertEqual(s._launched_effort, ("low", False), "stamped by the landing, after the handshake")
        states = Path(self.state, "states", sid + ".jsonl")
        self.assertEqual([json.loads(l)["effortApplied"] for l in states.read_text().splitlines() if "effortApplied" in l], ["low"],
                         "the applied record, once, at the landing")
        self.assertIsNone(s.snapshot()["pickHeld"])
        self.assertEqual([l for l in lines if "in a handler on a" in l], [], "every record the host relayed was handled")
        # the session's end takes the same close in end mode: the fresh host ends its CLI and leaves too
        s.shutdown()
        s.thread.join(timeout=30)
        self.assertFalse(s.thread.is_alive(), "the session thread ended")
        self.assertEqual(procs[1].wait(timeout=20), 0, "the fresh host ended with the session")
        self.assertIsNone(sb.read_lease(self.state, sid), "no lease left behind")


if __name__ == "__main__":
    unittest.main()
