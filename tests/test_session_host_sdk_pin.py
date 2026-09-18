#!/usr/bin/env python3
"""The SDK pin behind the session host's private imports (2026-09-18; the box admin's hazard review of the merged
pull-in, 2026-09-16). kernel/session_host.py drives claude_agent_sdk._internal.transport.subprocess_cli's
SubprocessCLITransport and reads its _process attribute, neither public, and bin/romp-sdk-setup used to upgrade the
package unpinned: a release that moved one would have failed every hosted session launch with the install step none
the wiser. Now one constant, SDK_TESTED_VERSION in the host module, names the version those imports were verified
against; the setup script installs exactly it (tests/install-optional-deps.bats holds that side); and the host compares
the installed package to it before the import. The tested version imports directly. Another version resolves each
name inside a try and, when one is gone, fails LOUDLY through the host-crashed record with both versions and the repin
command, which the kernel's launch error carries (host_transport.host_exit_reason); a version whose internals still
resolve runs with one host.log row saying newer or older, which the kernel files as a problem row. Never a degraded
transport: the pipe transport is for machines with no SDK at all.

Hermetic: fake SDK modules planted in sys.modules and restored after each case; a fake site directory with a
dist-info handed to a REAL host process over ROMP_SDK_SITE; temp state roots; synthetic ids; no real SDK is needed.
The last class reads the machine's SDK venv and skips without it.
"""
import asyncio
import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
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
sb = load_source("romp_sdk_backend", os.path.join(BIN, "romp_sdk_backend.py"))
ht = sb._ht()
SDK_SITE = next(iter(sorted(Path(os.path.expanduser("~/.local/state/romp/sdkvenv/lib")).glob(
    "python%d.%d/site-packages" % sys.version_info[:2]))), None) if os.path.isdir(os.path.expanduser("~/.local/state/romp/sdkvenv")) else None
SID = "11111111-2222-3333-4444-0000000000c1"
LEAF, NAME = sh.SDK_INTERNALS[0]
OTHER = "9.9.9"                                      # a version that is not the tested one, whatever the pin says


def _plant(case, with_name: bool, with_leaf: bool = True):
    """Fake SDK modules under the real dotted names, restored when `case` ends. `with_name` gives the leaf the
    class; `with_leaf` False leaves the leaf out, so its import is a ModuleNotFoundError (an ImportError)."""
    names = []
    parts = LEAF.split(".")
    for i in range(1, len(parts) + 1):
        names.append(".".join(parts[:i]))
    if not with_leaf:
        names = names[:-1]
    saved = {n: sys.modules.get(n) for n in names + [LEAF]}

    def restore():
        for n, m in saved.items():
            if m is None:
                sys.modules.pop(n, None)
            else:
                sys.modules[n] = m
    case.addCleanup(restore)
    cls = type(NAME, (), {})
    for n in names:
        m = types.ModuleType(n)
        m.__spec__ = ModuleSpec(n, loader=None)
        if n != LEAF:
            m.__path__ = []                          # a package with no files: a child not planted is not found
        sys.modules[n] = m
    if not with_leaf:
        sys.modules.pop(LEAF, None)
    elif with_name:
        setattr(sys.modules[LEAF], NAME, cls)
    return cls


class VersionCheck(unittest.TestCase):
    """sdk_internals(): the tested version imports directly; another version fails loudly or proceeds with one row."""

    def setUp(self):
        self.rows = []
        self.log = lambda kind, **f: self.rows.append((kind, f))

    def test_the_pin_is_one_bare_version_string_the_setup_script_can_read(self):
        # bin/romp-sdk-setup reads the declaration with a sed over the line; the bats test reads it the same way.
        # Hold the shape here so a rewrite of the line (a tuple, a computed value) is caught before the script
        # reads an empty pin and refuses to install.
        src = Path(ROOT, "kernel", "session_host.py").read_text().splitlines()
        lines = [l for l in src if l.startswith("SDK_TESTED_VERSION = ")]
        self.assertEqual(len(lines), 1, "exactly one declaration line")
        self.assertRegex(lines[0], r'^SDK_TESTED_VERSION = "\d+\.\d+\.\d+"(\s+#.*)?$')
        self.assertEqual(lines[0].split('"')[1], sh.SDK_TESTED_VERSION)
        self.assertEqual(sh.SDK_REPIN_COMMAND, "bin/romp-sdk-setup")
        self.assertTrue(os.access(os.path.join(ROOT, sh.SDK_REPIN_COMMAND), os.X_OK), "the remedy names a real script")

    def test_the_tested_version_imports_directly_and_logs_nothing(self):
        cls = _plant(self, with_name=True)
        got = sh.sdk_internals(installed=sh.SDK_TESTED_VERSION, log=self.log)
        self.assertIs(got[NAME], cls)
        self.assertEqual(self.rows, [])

    def test_the_tested_version_with_a_broken_install_raises_the_raw_error_not_a_mismatch(self):
        # a missing name at the tested version is a broken install, not a version drift: it surfaces as today
        _plant(self, with_name=False)
        with self.assertRaises((ImportError, AttributeError)) as cm:
            sh.sdk_internals(installed=sh.SDK_TESTED_VERSION, log=self.log)
        self.assertNotIsInstance(cm.exception, sh.SdkInternalsMismatch)
        self.assertEqual(self.rows, [])

    def test_another_version_missing_the_name_fails_loudly_naming_both_versions_and_the_remedy(self):
        _plant(self, with_name=False)
        with self.assertRaises(sh.SdkInternalsMismatch) as cm:
            sh.sdk_internals(installed=OTHER, log=self.log)
        msg = str(cm.exception)
        self.assertIn(OTHER, msg)                                      # the installed version
        self.assertIn(sh.SDK_TESTED_VERSION, msg)                      # the tested one
        self.assertIn(sh.SDK_REPIN_COMMAND, msg)                       # the command that repins
        self.assertIn(LEAF + "." + NAME, msg)                          # what is gone
        self.assertIn("claude-agent-sdk", msg)
        self.assertIsInstance(cm.exception.__cause__, (ImportError, AttributeError))
        self.assertEqual(self.rows, [], "the failure is the message, not a row and a degraded run")

    def test_another_version_missing_the_whole_module_is_the_same_loud_failure(self):
        _plant(self, with_name=False, with_leaf=False)
        with self.assertRaises(sh.SdkInternalsMismatch) as cm:
            sh.sdk_internals(installed=OTHER)
        self.assertIsInstance(cm.exception.__cause__, ImportError)
        self.assertIn(OTHER, str(cm.exception))

    def test_another_version_whose_internals_resolve_proceeds_with_one_row_saying_newer_or_older(self):
        cls = _plant(self, with_name=True)
        got = sh.sdk_internals(installed=OTHER, log=self.log)
        self.assertIs(got[NAME], cls)
        self.assertEqual(self.rows, [("sdk-version-untested", {"installed": OTHER, "tested": sh.SDK_TESTED_VERSION, "relation": "newer"})])
        self.rows.clear()
        sh.sdk_internals(installed="0.0.1", log=self.log)
        self.assertEqual(self.rows[0][1]["relation"], "older")
        self.rows.clear()
        sh.sdk_internals(installed="not-a-version", log=self.log)
        self.assertEqual(self.rows[0][1]["relation"], "different")
        self.rows.clear()
        with mock.patch.object(sh, "installed_sdk_version", return_value=None):   # importable, no package metadata
            sh.sdk_internals(log=self.log)                                           # (None as the argument means: read it)
        self.assertEqual(self.rows[0][1], {"installed": "unknown", "tested": sh.SDK_TESTED_VERSION, "relation": "different"})
        self.assertEqual(sh.sdk_internals(installed=OTHER), {NAME: cls}, "no log callback: still proceeds")

    def test_the_installed_version_is_the_package_metadata_and_none_without_it(self):
        with mock.patch.object(sh.importlib.metadata, "version", return_value="1.2.3") as v:
            self.assertEqual(sh.installed_sdk_version(), "1.2.3")
        v.assert_called_once_with(sh.SDK_DIST)
        with mock.patch.object(sh.importlib.metadata, "version", side_effect=importlib.metadata.PackageNotFoundError(sh.SDK_DIST)):
            self.assertIsNone(sh.installed_sdk_version())
        # and with no version handed in, sdk_internals reads it from there
        _plant(self, with_name=False)
        with mock.patch.object(sh, "installed_sdk_version", return_value=OTHER):
            with self.assertRaises(sh.SdkInternalsMismatch) as cm:
                sh.sdk_internals()
        self.assertIn(OTHER, str(cm.exception))


def _fake_site(root, version: str, with_name: bool) -> Path:
    """A site directory holding a fake claude_agent_sdk at `version` (a dist-info importlib.metadata reads) whose
    private transport module has the class, or not."""
    site = Path(root) / "site"
    pkg = site / "claude_agent_sdk"
    (pkg / "_internal" / "transport").mkdir(parents=True)
    (pkg / "__init__.py").write_text('__version__ = %r\n' % version)
    (pkg / "_internal" / "__init__.py").write_text("")
    (pkg / "_internal" / "transport" / "__init__.py").write_text("")
    (pkg / "_internal" / "transport" / "subprocess_cli.py").write_text(
        ("class %s:\n    pass\n" % NAME) if with_name else "# the class moved in this release\n")
    di = site / ("claude_agent_sdk-%s.dist-info" % version)
    di.mkdir()
    (di / "METADATA").write_text("Metadata-Version: 2.1\nName: claude-agent-sdk\nVersion: %s\n" % version)
    return site


class HostProcess(unittest.TestCase):
    """The real bin/romp-session-host over a fake SDK site: the mismatch leaves the host through the host-crashed
    record, and the kernel's launch error reads that record."""

    def setUp(self):
        self.state = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.state, True)
        Path(self.state, "session-hosts").write_text("off")       # the belt for a state root a test mints (2026-09-11)
        d = Path(self.state) / "hosts" / SID
        d.mkdir(parents=True, mode=0o700)
        spec = {"sid": SID, "name": "web", "version": "abc12345", "state_dir": self.state, "protocol": 1,
                "cli_path": "/bin/true", "cwd": self.state, "permission_prompt_tool_name": "stdio", "permission_mode": "default",
                "env": {}, "max_buffer_size": 1024 * 1024, "hook_self_answer_s": 2, "unattached_grace_s": 3600}
        self.spec_path = d / "spawn.json"
        self.spec_path.write_text(json.dumps(spec)); self.spec_path.chmod(0o600)
        self.hostdir = d

    def _run_host(self, site: Path):
        env = dict(os.environ, PYTHONUNBUFFERED="1", ROMP_SDK_SITE=str(site), PYTHONPATH=str(site))
        # PYTHONPATH too: an interpreter that has the real SDK would otherwise import it ahead of the fake
        for name in sb.AUTH_ENV_NAMES:
            env.pop(name, None)
        err = self.hostdir / "host.stderr"
        with open(err, "w") as f:
            proc = subprocess.run([sys.executable, os.path.join(BIN, "romp-session-host"), str(self.spec_path)],
                                  stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=f, env=env, timeout=60)
        return proc.returncode, err.read_text()

    def _hostlog(self):
        p = self.hostdir / "host.log"
        return [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []

    def test_a_mismatched_sdk_ends_the_host_through_the_crash_record_before_any_cli_or_socket(self):
        code, stderr = self._run_host(_fake_site(self.state, OTHER, with_name=False))
        self.assertEqual(code, 1)
        rows = self._hostlog()
        kinds = [r["kind"] for r in rows]
        self.assertIn("host-started", kinds)
        self.assertIn("host-crashed", kinds)
        self.assertNotIn("cli-spawned", kinds, "no CLI was started on the untested SDK")
        self.assertNotIn("cli-spawn-failed", kinds, "the mismatch is not filed as a generic spawn failure with a bare type name")
        self.assertNotIn("socket-ready", kinds)
        self.assertFalse(list(Path(self.state, "hosts").glob("*.sock")), "no socket was served")
        crash = [r for r in rows if r["kind"] == "host-crashed"][0]["error"]
        for needle in (OTHER, sh.SDK_TESTED_VERSION, sh.SDK_REPIN_COMMAND, LEAF + "." + NAME):
            self.assertIn(needle, crash)
        self.assertEqual(crash, sh.sdk_mismatch_text(OTHER, LEAF + "." + NAME), "the record carries the text whole, untruncated")
        self.assertIn(crash, stderr, "and the host's stderr file says the same")
        # the kernel's side reads that row for its launch error
        self.assertEqual(ht.host_exit_reason(self.state, SID), crash)

    def test_the_kernels_launch_error_carries_the_hosts_last_word(self):
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d, True)
        be = sb.SdkBackend(d, "/bin/true", lambda *a, **k: None, log=lambda *a, **k: None)
        Path(d, "session-hosts").write_text("on")
        sb.write_reg(Path(d), SID, {"sid": SID, "name": "web", "alive": True, "lastSid": SID})
        s = types.SimpleNamespace(sid=SID, name="web", _host_intent=True, _host=None, _host_is_attach=False,
                                  _options_login="", _seed_for_dead_cli=lambda cli: None)
        text = sh.sdk_mismatch_text(OTHER, LEAF + "." + NAME)

        def fake_spawn(sess, spec_path, secret_env=None):
            # the host died at once and left its record, as the case above shows a real one does
            with open(Path(spec_path).parent / "host.log", "a") as f:
                f.write(json.dumps({"t": 1, "kind": "host-started"}) + "\n" + json.dumps({"t": 2, "kind": "host-crashed", "error": text}) + "\n")
            return types.SimpleNamespace(poll=lambda: 1, returncode=1, pid=4242, terminate=lambda: None)
        with mock.patch.object(be, "_spawn_host", fake_spawn):
            with self.assertRaises(sb.CLIConnectionErrorLike) as cm:
                asyncio.run(be._host_transport_for(s, types.SimpleNamespace(), (None, None, None)))
        msg = str(cm.exception)
        self.assertIn("exited before serving its socket (code 1)", msg)
        self.assertIn(text, msg, "the card names the versions and the command, not just the log to read")
        for needle in (OTHER, sh.SDK_TESTED_VERSION, sh.SDK_REPIN_COMMAND):
            self.assertIn(needle, msg)

    def test_host_exit_reason_reads_the_last_crash_or_spawn_row_and_is_empty_otherwise(self):
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d, True)
        self.assertEqual(ht.host_exit_reason(d, SID), "", "no log yet")
        hd = ht.host_dir(d, SID); hd.mkdir(parents=True)
        (hd / "host.log").write_text(json.dumps({"t": 1, "kind": "host-started"}) + "\n")
        self.assertEqual(ht.host_exit_reason(d, SID), "", "a log with no failing row")
        with open(hd / "host.log", "a") as f:
            f.write(json.dumps({"t": 2, "kind": "cli-spawn-failed", "error": "FileNotFoundError"}) + "\nnot json\n")
        self.assertEqual(ht.host_exit_reason(d, SID), "FileNotFoundError")
        with open(hd / "host.log", "a") as f:
            f.write(json.dumps({"t": 3, "kind": "host-crashed", "error": "later"}) + "\n")
        self.assertEqual(ht.host_exit_reason(d, SID), "later", "the last such row wins")

    def test_an_untested_but_working_sdk_is_filed_as_a_problem_row_naming_the_versions_and_the_remedy(self):
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d, True); logs = []
        be = sb.SdkBackend(d, "/bin/true", lambda *a, **k: None, log=logs.append)
        sess = types.SimpleNamespace(sid=SID, name="web", _host=None)
        hd = ht.host_dir(d, SID); hd.mkdir(parents=True)
        (hd / "host.log").write_text(json.dumps({"t": 1, "kind": "host-started"}) + "\n"
                                     + json.dumps({"t": 2, "kind": "sdk-version-untested", "installed": OTHER,
                                                   "tested": sh.SDK_TESTED_VERSION, "relation": "newer"}) + "\n")
        be._file_host_log_rows(sess)
        rows = [json.loads(l) for l in (Path(d) / sb.SESSION_EVENTS_FILE).read_text().splitlines()]
        self.assertEqual([r["kind"] for r in rows], ["host.sdk-untested"])
        self.assertEqual((rows[0]["installed"], rows[0]["tested"], rows[0]["relation"]), (OTHER, sh.SDK_TESTED_VERSION, "newer"))
        prose = rows[0]["text"]
        for needle in (OTHER, sh.SDK_TESTED_VERSION, "newer", sh.SDK_REPIN_COMMAND, "web"):
            self.assertIn(needle, prose)


class MachineVenv(unittest.TestCase):
    """The SDK venv on this machine, when there is one, holds the tested version and its internals resolve there:
    the SDK-transport cases in tests/test_session_host.py run the host against that venv, so a pin they did not
    verify is caught here rather than trusted."""

    @unittest.skipUnless(SDK_SITE, "the SDK venv is not on this machine")
    def test_the_machines_sdk_venv_holds_the_tested_version_and_the_internals_resolve(self):
        dist = next(iter(importlib.metadata.Distribution.discover(name=sh.SDK_DIST, path=[str(SDK_SITE)])), None)
        self.assertIsNotNone(dist, "the venv has the package's metadata")
        self.assertEqual(dist.version, sh.SDK_TESTED_VERSION,
                         "the venv holds %s, the pin says %s: run %s (or move the pin after verifying the imports)"
                         % (dist.version, sh.SDK_TESTED_VERSION, sh.SDK_REPIN_COMMAND))
        probe = ("import importlib, json, sys\n"
                 "spec = %r\n"
                 "out = {}\n"
                 "for mod, name in spec:\n"
                 "    out[name] = hasattr(importlib.import_module(mod), name)\n"
                 "print(json.dumps(out))\n" % (list(sh.SDK_INTERNALS),))
        env = dict(os.environ, PYTHONPATH=str(SDK_SITE))
        got = subprocess.run([sys.executable, "-c", probe], env=env, capture_output=True, text=True, timeout=60)
        self.assertEqual(got.returncode, 0, got.stderr)
        self.assertEqual(json.loads(got.stdout), {name: True for _, name in sh.SDK_INTERNALS})


if __name__ == "__main__":
    unittest.main()
