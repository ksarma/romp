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
import asyncio
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
    cases from round 2, the same day). asyncio.start_unix_server binds AND
    listens at the umask's mode, and the old code's chmod one line later left the published path at that mode for the
    gap: the last member of the create-then-tighten class PR 789 closed for the kernel's credential files. A stat once
    the host is up passes on that code, so the mode cases capture the mode at CREATION: the mode the temp carries as
    os.rename moves it onto the published path, and which path os.chmod ever touched, under a permissive umask for the
    test's duration. Every case but two drives the real run() in this process, with a stub in place of the CLI transport
    (no CLI is spawned) and recording lease helpers, so the bind under test is run()'s own, not a helper's; the name case
    (test_the_temp_name_is_writer_unique_and_the_published_names_length) reads sock_names without run(), and the
    session-directory case constructs Journal and SessionHost, which refuse before run() could start."""

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

    def _run_host(self, ready=None):
        """The real run() until `ready()` (default: the published path exists) or run() ends, then the stop. Returns
        (the published path's mode at that moment, or None when it did not exist; run()'s exit code, or the OSError run()
        raised on the bind road). The host stays on self.host for the checks after; the spawn stub writes the lease the
        real _spawn writes at its end, so the lease-before-bind order run() has is the order under test."""
        ready = ready or self.pub.exists
        host = self.host = sh.SessionHost(str(self.sdir / "spawn.json"), lease_api=self.lease_api)

        async def _spawn():
            host.transport = self._NoCli(self)
            host.cli_pid, host.cli_start, host.cli_spawned_at = CLI_PID, "1", int(host.now())
            host._write_lease()
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

    def _assert_refused(self, rc, step, error, errno_=None, at="session_host.py:"):
        """The loud road, whole: the row names the step, nothing is bound or published, the lease the spawn wrote is
        gone, the CLI stand-in was closed, and no temp is left in hosts/. `at` is the file the row's frame names: the
        raiser's (_where reads the innermost frame), so session_host.py for the checks of our own, asyncio's
        unix_events.py for the bind's, and this file's for a failure a test's stand-in raised."""
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
        self.assertEqual(self.lease_calls, ["write", "remove"], "the lease written at the spawn is removed on the failure")
        self.assertEqual(self.leases, {}, "no lease is kept")
        self.assertTrue(self.host.transport.closed.is_set(), "the CLI was ended with the host")

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

    @unittest.skipUnless(len(os.fsencode("ü")) == 2, "the filesystem encoding is not UTF-8: no two-byte name character to separate bytes from characters")
    def test_the_budget_is_measured_in_bytes_a_multibyte_published_path_over_it_in_bytes_alone_is_refused(self):
        """The byte measure, pinned where it differs from the character count (the review's round 2, 2026-09-19: the owner's
        mutation pass set a str-length pathLen aside as equivalent, and it is not: both modules stayed green under it, and
        for a sid whose first eight characters are multibyte it publishes an unreachable socket with a socket-ready row,
        round 1's high back). A published path of SOCK_PATH_MAX + 1 bytes and fewer than SOCK_PATH_MAX characters: the
        check refuses it before the bind, the row's pathLen is the byte length, and the temp (13 bytes, shorter than this
        published name's 21) would have bound where the published path cannot be connected to."""
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

    @unittest.skipUnless(len(os.fsencode("ü")) == 2, "the filesystem encoding is not UTF-8: no two-byte name character to separate bytes from characters")
    def test_a_multibyte_published_path_at_the_budget_in_bytes_is_served_and_a_client_connects(self):
        """The mirror: exactly SOCK_PATH_MAX bytes (fewer characters), served 0600 and connectable, the ready row's pathLen
        the byte length. With the case above, the check is pinned to bytes in both directions."""
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
        start), gone (no start), and a pid the kernel reused (a different start)."""
        self.cli_outlives_close = True                  # close() returns; proc_start still reports the spawn's start for CLI_PID
        self._reroot(sh.SOCK_PATH_MAX + 1)
        mode, rc = self._run_host()
        self.assertIsInstance(rc, OSError)
        self.assertEqual(self.lease_calls, ["write"], "written at the spawn and NOT removed: the CLI is unconfirmed")
        self.assertEqual(self.leases[SID]["pid"], CLI_PID, "the lease still names the CLI the kernel's orphan road will wait on")
        kept = self.rows["lease-kept"]
        self.assertEqual(sorted(k for k in kept if k not in ("t", "kind")), ["cliPid"], "the kind and the CLI's pid, nothing else: no path")
        self.assertEqual(kept["cliPid"], CLI_PID)
        self.assertTrue(self.host.transport.closed.is_set(), "the CLI was still asked to end")
        self.assertNotIn("socket-ready", self.rows)
        self.assertEqual(self._temps(), [], "the loud road otherwise ran whole: no temp left")
        kinds = [r["kind"] for r in self.host_log]
        self.assertLess(kinds.index("socket-bind-failed"), kinds.index("lease-kept"))
        # a pid the kernel reused: proc_start answers a different start for CLI_PID, so the CLI is gone even though a process answers
        self.setUp()
        self.cli_outlives_close, self.cli_start_now = True, "2"
        self._reroot(sh.SOCK_PATH_MAX + 1)
        mode, rc = self._run_host()
        self._assert_refused(rc, "budget", "OSError", errno.ENAMETOOLONG)
        self.assertNotIn("lease-kept", self.rows)
        # gone for real: the default stand-in, whose close() leaves no process behind (the six refusal cases run this leg)
        self.setUp()
        self._reroot(sh.SOCK_PATH_MAX + 1)
        mode, rc = self._run_host()
        self._assert_refused(rc, "budget", "OSError", errno.ENAMETOOLONG)
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
        with the row's step hosts-dir, and its target's mode is not touched through the link."""
        hosts = self.pub.parent
        target = Path(self.root) / "elsewhere"
        os.rename(hosts, target)                        # the session directory and spec move with it; the spec path resolves through the link
        os.chmod(target, 0o755)
        hosts.symlink_to(target)
        mode, rc = self._run_host()
        self._assert_refused(rc, "hosts-dir", "OSError")
        self.assertTrue(hosts.is_symlink(), "the link is left, not replaced")
        self.assertEqual(stat.S_IMODE(os.stat(target).st_mode), 0o755, "the target's mode untouched: no chmod through the link")

    def test_a_tighten_of_hosts_that_does_not_take_is_refused_not_reported_as_done(self):
        """hosts_dir reads the mode back after its chmod (the precedent's second check, dropped by the first cut): with
        os.chmod a no-op, a loose hosts/ stays loose and the host refuses with the row instead of binding into it."""
        hosts = self.pub.parent
        self.assertEqual(stat.S_IMODE(os.stat(hosts).st_mode), 0o777, "setUp's shape under the 000 umask")
        with mock.patch.object(os, "chmod", lambda *a, **k: None):
            mode, rc = self._run_host()
        self._assert_refused(rc, "hosts-dir", "OSError")
        self.assertEqual(stat.S_IMODE(os.stat(hosts).st_mode), 0o777, "still loose, and the host said so rather than binding")

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
        self.assertLessEqual(len(os.fsencode(str(self.pub))), sh.SOCK_PATH_MAX, "within the budget, so the rename is the leg that fails")
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
        self.assertEqual(sorted(k for k in crashed if k not in ("t", "kind")), ["at", "error"], "the class and the frame, nothing else")
        self.assertEqual(self._temps(), [], "the bound temp was unlinked on the failure")
        self.assertTrue(self.pub.is_dir(), "the planted directory is left; the host removes only what it made")
        self.assertEqual(self.leases, {})
        self.assertTrue(stub.closed.is_set(), "the CLI was ended with the host")


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


class PaddedRoots(unittest.TestCase):
    """padded_root never skips (the review's round 2, 2026-09-19): the padded cases pin round 1's high, and round 1's
    helpers skipped once the run's private temp root was deep, so the module reported green with the high unpinned. Both
    directions: with the run's temp root as deep as a long TMPDIR under xdist makes it, the root is built under the
    system temp dir at the exact byte length; with the SYSTEM temp dir itself too deep, the helper FAILS, naming the
    remedy, rather than skipping."""

    def test_a_deep_run_root_does_not_stop_the_pad_and_a_deep_system_temp_dir_fails_rather_than_skips(self):
        tail = os.path.join("hosts", SID[:8] + ".sock")
        deep = os.path.join(tempfile.mkdtemp(), *(["d" * 9] * 8))     # a run root about 90 bytes deeper than the system temp dir
        os.makedirs(deep)
        self.addCleanup(shutil.rmtree, deep.split(os.sep + "d" * 9)[0], True)
        with mock.patch.object(tempfile, "tempdir", deep):
            self.assertEqual(tempfile.gettempdir(), deep, "the run's temp root is the deep one for this call")
            root = padded_root(self, sh.SOCK_PATH_MAX + 1, tail)
        self.assertEqual(len(os.fsencode(os.path.join(root, tail))), sh.SOCK_PATH_MAX + 1)
        self.assertEqual(os.path.commonpath([os.path.realpath(root), os.path.realpath(system_tmp())]), os.path.realpath(system_tmp()),
                         "built under the system temp dir, not the run's root")
        self.assertTrue(os.path.isdir(root))
        with mock.patch.dict(os.environ, {"ROMP_TESTS_SYSTEM_TMPDIR": deep}):
            with self.assertRaises(AssertionError) as cm:
                padded_root(self, sh.SOCK_PATH_MAX + 1, tail)
        self.assertIn("too deep", str(cm.exception))
        self.assertIn("shorter TMPDIR", str(cm.exception), "the remedy, in the failure, not a skip")


class KeptLease(unittest.TestCase):
    """What the kept lease buys on the kernel's side (the review's round 2, 2026-09-19): the connect loop's orphan road
    waits for a dead host's CLI by the lease's pid and start, and only the lease tells it there is a CLI to wait for.
    Driven on the real backend over a scratch state root with a real process standing in for the CLI: with the lease
    the host kept (its holder gone, the CLI alive) the next connect waits and spawns nothing until the CLI is gone; with
    the lease removed, round 1's failure arm, the same connect finds a lease-less leftover, waits for nothing and spawns
    a second CLI while the first is alive. _spawn_host is replaced by a recorder (no host process starts here; the
    recorded call IS the second CLI), so the state root's hosts setting is left on, which the road needs to reach it."""

    def setUp(self):
        self.state = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.state, True)
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
        connect raised; the code before failed the bind loudly and exited 1. Now: exit 1, the socket-bind-failed row
        (step budget, ENAMETOOLONG, the length and the limit) then host-crashed, no path in any row, no socket, no temp,
        no lease on disk, and the CLI the host spawned is gone."""
        budget = sh.SOCK_PATH_MAX
        self._pad_state_to(budget + 1)
        spec_path, spec = self._spec()
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
        self.assertIn("cli-spawned", kinds, kinds)
        self.assertNotIn("socket-ready", kinds, kinds)
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
        self.assertIsNone(self._lease(), "no lease is kept on disk")
        cli_pid = by["cli-spawned"]["cliPid"]
        with self.assertRaises(ProcessLookupError, msg="the CLI the host spawned is gone with it"):
            os.kill(cli_pid, 0)

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
