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

Round 1 of the review (2026-09-18) added the cases marked with their finding ids: the launch error's text over a
stale stderr tail (correctness-1, kernel-1), the ImportError verdict and the cause it carries (fresh-1), the
public-package names in host_transport.py (fresh-2), the ledger row for a refused launch (fresh-3), the drifted
signature's composed reason and its no-SDK control (regression-1), the `_process` guard at both versions (tests-2),
and the machine venv read from its own record (tests-3).
"""
import asyncio
import importlib.abc
import importlib.metadata
import json
import os
import re
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
SDKVENV = Path(os.path.expanduser("~/.local/state/romp/sdkvenv"))


def _venv_site(venv: Path):
    """The machine venv's site directory from the venv's OWN record (tests-3, round 1 of the review, 2026-09-18):
    pyvenv.cfg's version names lib/python3.X{t}, else the single lib/python3.* present. Until round 1 this
    looked for the RUNNER's python minor under lib/ and skipped, saying the venv was not on this machine,
    whenever the runner's minor differed from the venv's. None only when there is no venv at all."""
    if not venv.is_dir():
        return None
    ver = ""
    try:
        for line in (venv / "pyvenv.cfg").read_text().splitlines():
            key, _, val = line.partition("=")
            if key.strip() in ("version", "version_info"):
                ver = val.strip()
    except OSError:
        pass
    libs = sorted((venv / "lib").glob("python3.*")) if (venv / "lib").is_dir() else []
    m = re.match(r"(\d+)\.(\d+)", ver)
    if m:
        libs = [l for l in libs if l.name.rstrip("t") == "python%s.%s" % m.groups()] or libs
    return libs[0] / "site-packages" if libs else None


SDK_SITE = _venv_site(SDKVENV)
# The internals probe runs under a python of the venv's own tag, resolved the way tests/test_session_host_restart.py
# resolves KERNEL_PYTHON: the real site loads cpython-tagged binary extensions, so a runner on another minor would
# fail the probe spuriously rather than verify anything (the refuter's correction on tests-3, round 1, 2026-09-18).
_tags = sorted(p.name for p in (SDKVENV / "lib").glob("python3.*")) if (SDKVENV / "lib").is_dir() else []
VENV_PYTHON = next((shutil.which(t) for t in _tags if shutil.which(t)), None)
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


class _RaisingLeaf(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """A finder for the SDK's private leaf module whose import RAISES `exc` from inside the module body: what a
    broken dependency chain looks like from sdk_internals (the leaf exists, its own `import anyio` does not)."""

    def __init__(self, exc):
        self.exc = exc

    def find_spec(self, fullname, path=None, target=None):
        return ModuleSpec(fullname, self) if fullname == LEAF else None

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        raise self.exc


def _raising_leaf(case, exc):
    """Plant the leaf's parents and a finder that raises `exc` when the leaf itself imports; undone with `case`."""
    _plant(case, with_name=False, with_leaf=False)
    finder = _RaisingLeaf(exc)
    sys.meta_path.insert(0, finder)
    case.addCleanup(lambda: sys.meta_path.remove(finder) if finder in sys.meta_path else None)
    return finder


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

    # fresh-1 (round 1 of the review, 2026-09-18): on a version other than the pin, ANY ImportError raised from inside
    # the SDK's private module was read as a confident "this version has no <module>.<name>" verdict, and the real
    # error was dropped: a broken dependency chain (the leaf exists, its own `import anyio` fails) was reported as
    # drift, and the actual cause reached no log, no stderr and no card. The mismatch verdict is kept for an
    # AttributeError and for a ModuleNotFoundError naming the SDK's own module path; anything else re-raises onto the
    # cli-spawn-failed road. And the verdict's text carries the cause's type and message, bounded, so the real cause
    # travels with whichever verdict fires.
    def test_another_version_whose_private_module_fails_on_a_third_party_import_is_not_a_moved_internal(self):
        _raising_leaf(self, ModuleNotFoundError("No module named 'anyio_dep_zz'", name="anyio_dep_zz"))
        with self.assertRaises(ModuleNotFoundError) as cm:
            sh.sdk_internals(installed=OTHER, log=self.log)
        self.assertNotIsInstance(cm.exception, sh.SdkInternalsMismatch, "a missing third-party module is not a moved internal")
        self.assertEqual(cm.exception.name, "anyio_dep_zz", "the real error, re-raised whole")
        self.assertEqual(self.rows, [])

    def test_a_plain_import_error_from_inside_the_private_module_re_raises_too(self):
        _raising_leaf(self, ImportError("cannot import name 'thing' from 'some_dep'", name="some_dep"))
        with self.assertRaises(ImportError) as cm:
            sh.sdk_internals(installed=OTHER)
        self.assertNotIsInstance(cm.exception, sh.SdkInternalsMismatch)

    def test_a_module_not_found_naming_the_sdks_own_path_is_still_the_mismatch_and_carries_the_cause(self):
        _raising_leaf(self, ModuleNotFoundError("No module named %r" % LEAF, name=LEAF))
        with self.assertRaises(sh.SdkInternalsMismatch) as cm:
            sh.sdk_internals(installed=OTHER)
        msg = str(cm.exception)
        for needle in (OTHER, sh.SDK_TESTED_VERSION, sh.SDK_REPIN_COMMAND, "ModuleNotFoundError: No module named %r" % LEAF):
            self.assertIn(needle, msg)

    def test_the_mismatch_text_carries_the_causes_type_and_message_bounded_like_the_generic_road(self):
        _plant(self, with_name=False)                                   # the module is there, the class is not
        with self.assertRaises(sh.SdkInternalsMismatch) as cm:
            sh.sdk_internals(installed=OTHER)
        msg = str(cm.exception)
        self.assertIn("AttributeError: ", msg, "the cause's own type and message ride along")
        self.assertIn(NAME, msg.split("AttributeError: ", 1)[1])
        plain = sh.sdk_mismatch_text(OTHER, LEAF + "." + NAME)
        self.assertNotIn("AttributeError", plain, "no cause, no cause text")
        long = ModuleNotFoundError("x" * 1000, name=LEAF)
        text = sh.sdk_mismatch_text(OTHER, LEAF + "." + NAME, cause=long)
        cause_part = text[len(plain):]
        self.assertLessEqual(len(cause_part), sh.SDK_CAUSE_CAP + 8, "capped as the generic host-crashed row caps its line")
        self.assertIn("ModuleNotFoundError: xxx", cause_part)

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


def _fake_site(root, version: str, with_name: bool, body: str = None) -> Path:
    """A site directory holding a fake claude_agent_sdk at `version` (a dist-info importlib.metadata reads) whose
    private transport module has the class, or not; `body` replaces the private module's source (a class whose
    constructor drifted, one that connects without a `_process`). The package exports the ClaudeAgentOptions the
    host builds its options from, so a case that reaches the spawn gets there."""
    site = Path(root) / "site"
    pkg = site / "claude_agent_sdk"
    (pkg / "_internal" / "transport").mkdir(parents=True)
    (pkg / "__init__.py").write_text('__version__ = %r\n\n\nclass ClaudeAgentOptions:\n    def __init__(self, **kw):\n        self.kw = kw\n' % version)
    (pkg / "_internal" / "__init__.py").write_text("")
    (pkg / "_internal" / "transport" / "__init__.py").write_text("")
    if body is None:
        body = ("class %s:\n    pass\n" % NAME) if with_name else "# the class moved in this release\n"
    (pkg / "_internal" / "transport" / "subprocess_cli.py").write_text(body)
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
        plain = sh.sdk_mismatch_text(OTHER, LEAF + "." + NAME)
        self.assertTrue(crash.startswith(plain), "the record carries the text whole, untruncated: %r" % crash)
        self.assertIn("(AttributeError: ", crash[len(plain):], "and the import error behind it (fresh-1, round 1)")
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

    # regression-1 (round 1 of the review, 2026-09-18): the loud failure covered only a MISSING module or name. A
    # private class that is present but whose signature drifted died as a bare exception type name in the
    # cli-spawn-failed row, and the version context the host had just written (the sdk-version-untested row) was
    # shown to no one. The row keeps the type name (that field is a type name everywhere else and is splatted into
    # the problem row); host_exit_reason, which reads the whole log in one pass, composes the sentence from the
    # preceding untested row of the same run. The control below: a machine with no SDK at all fails the same arm
    # through the pipe transport and must not be given SDK-mismatch text.
    _DRIFTED = "class %s:\n    def __init__(self, cmd):\n        self.cmd = cmd\n" % NAME

    def test_a_spawn_failure_on_an_untested_sdk_reaches_the_launch_error_with_both_versions_and_the_remedy(self):
        code, _ = self._run_host(_fake_site(self.state, OTHER, with_name=True, body=self._DRIFTED))
        self.assertEqual(code, 1)
        rows = self._hostlog()
        kinds = [r["kind"] for r in rows]
        self.assertIn("sdk-version-untested", kinds)
        self.assertIn("cli-spawn-failed", kinds)
        self.assertNotIn("cli-spawned", kinds)
        self.assertEqual([r for r in rows if r["kind"] == "cli-spawn-failed"][0]["error"], "TypeError",
                         "the row's error field stays the type name")
        reason = ht.host_exit_reason(self.state, SID)
        self.assertTrue(reason.startswith("TypeError"), reason)
        for needle in (OTHER, sh.SDK_TESTED_VERSION, sh.SDK_REPIN_COMMAND, "newer"):
            self.assertIn(needle, reason)

    def test_a_spawn_failure_with_no_sdk_at_all_keeps_the_bare_type_name(self):
        # the control: the pipe transport's spawn of a CLI that is not there, with no SDK in the host's site
        spec = json.loads(self.spec_path.read_text())
        spec["cli_path"] = os.path.join(self.state, "no-such-cli")
        self.spec_path.write_text(json.dumps(spec))
        empty = Path(self.state, "nosite")
        empty.mkdir()
        code, _ = self._run_host(empty)
        self.assertEqual(code, 1)
        kinds = [r["kind"] for r in self._hostlog()]
        self.assertNotIn("sdk-version-untested", kinds)
        self.assertIn("cli-spawn-failed", kinds)
        self.assertEqual(ht.host_exit_reason(self.state, SID), "FileNotFoundError", "no SDK, no SDK text")

    def test_host_exit_reason_composes_from_the_untested_row_of_the_same_run_only(self):
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d, True)
        hd = ht.host_dir(d, SID); hd.mkdir(parents=True)
        rows = [{"t": 1, "kind": "host-started"},
                {"t": 2, "kind": "sdk-version-untested", "installed": OTHER, "tested": sh.SDK_TESTED_VERSION, "relation": "newer"},
                {"t": 3, "kind": "cli-spawn-failed", "error": "TypeError"}]
        (hd / "host.log").write_text("".join(json.dumps(r) + "\n" for r in rows))
        reason = ht.host_exit_reason(d, SID)
        self.assertTrue(reason.startswith("TypeError"), reason)
        for needle in (OTHER, sh.SDK_TESTED_VERSION, sh.SDK_REPIN_COMMAND, "newer"):
            self.assertIn(needle, reason)
        # a later run in the same log with no untested row of its own: the bare type name, never the stale context
        with open(hd / "host.log", "a") as f:
            f.write(json.dumps({"t": 4, "kind": "host-started"}) + "\n" + json.dumps({"t": 5, "kind": "cli-spawn-failed", "error": "FileNotFoundError"}) + "\n")
        self.assertEqual(ht.host_exit_reason(d, SID), "FileNotFoundError")
        # a version that does not parse: "other than", never "newer" or "older"
        (hd / "host.log").write_text("".join(json.dumps(r) + "\n" for r in [
            rows[0], dict(rows[1], installed="not-a-version", relation="different"), rows[2]]))
        reason = ht.host_exit_reason(d, SID)
        self.assertIn("not-a-version", reason)
        self.assertNotIn("newer", reason)

    # tests-2 (round 1 of the review, 2026-09-18): the guard for the SECOND private name the host reads (a transport
    # that connects without a `_process`) had no test, and at the tested version it claimed a version mismatch about
    # a matching version and offered a repin pip reports as already satisfied. Split the way sdk_internals splits: at
    # the tested version the install is broken (the attribute and the venv named); at another version the mismatch.
    _NO_PROCESS = ("class %s:\n    def __init__(self, **kw):\n        pass\n\n    async def connect(self):\n        pass\n\n"
                   "    async def close(self):\n        pass\n" % NAME)

    def test_a_transport_without_a_process_at_another_version_is_the_mismatch_naming_both_versions(self):
        code, stderr = self._run_host(_fake_site(self.state, OTHER, with_name=True, body=self._NO_PROCESS))
        self.assertEqual(code, 1)
        rows = self._hostlog()
        kinds = [r["kind"] for r in rows]
        self.assertIn("host-crashed", kinds)
        self.assertNotIn("cli-spawned", kinds)
        crash = [r for r in rows if r["kind"] == "host-crashed"][0]["error"]
        for needle in (OTHER, sh.SDK_TESTED_VERSION, sh.SDK_REPIN_COMMAND, "_process"):
            self.assertIn(needle, crash)
        self.assertIn(crash, stderr)

    def test_a_transport_without_a_process_at_the_tested_version_is_a_broken_install_not_a_mismatch(self):
        code, stderr = self._run_host(_fake_site(self.state, sh.SDK_TESTED_VERSION, with_name=True, body=self._NO_PROCESS))
        self.assertEqual(code, 1)
        rows = self._hostlog()
        kinds = [r["kind"] for r in rows]
        self.assertIn("host-crashed", kinds)
        self.assertNotIn("sdk-version-untested", kinds, "the tested version is not untested")
        self.assertNotIn("cli-spawned", kinds)
        crash = [r for r in rows if r["kind"] == "host-crashed"][0]["error"]
        self.assertIn("_process", crash)
        self.assertIn(sh.SDK_TESTED_VERSION, crash)
        self.assertIn("broken", crash)
        self.assertIn("venv", crash, "the venv to rebuild is named")
        self.assertNotIn("but the session host is written against", crash, "no version mismatch is claimed")
        self.assertNotIn("this version has no", crash)
        self.assertEqual(crash, sh.sdk_broken_install_text(sh.SDK_TESTED_VERSION, LEAF + "." + NAME + "._process"))
        self.assertIn(crash, stderr)

    # fresh-3 (round 1 of the review, 2026-09-18): the benign case (an untested version whose internals resolve) got a
    # durable ledger row, host.sdk-untested, while the fatal one filed nothing: no road files rows for a host that never
    # served its socket, so a refused launch left no session-events row and its only surface was the per-session card.
    # One row at the raise site, under its own kind (never host.spawn-failed, so one event is not counted twice), gated
    # on the event (the host exited before serving its socket), not on the reason text.
    def test_a_host_that_exits_before_its_socket_files_one_problem_row_per_refused_launch(self):
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d, True); logs = []
        be = sb.SdkBackend(d, "/bin/true", lambda *a, **k: None, log=lambda m, *a, **k: logs.append(m))
        Path(d, "session-hosts").write_text("on")
        sb.write_reg(Path(d), SID, {"sid": SID, "name": "web", "alive": True, "lastSid": SID})
        s = types.SimpleNamespace(sid=SID, name="web", _host_intent=True, _host=None, _host_is_attach=False,
                                  _options_login="", _seed_for_dead_cli=lambda cli: None)
        text = sh.sdk_mismatch_text(OTHER, LEAF + "." + NAME)
        spawned = []

        def fake_spawn(sess, spec_path, secret_env=None):
            spawned.append(1)
            with open(Path(spec_path).parent / "host.log", "a") as f:
                f.write(json.dumps({"t": 1, "kind": "host-started"}) + "\n" + json.dumps({"t": 2, "kind": "host-crashed", "error": text}) + "\n")
            return types.SimpleNamespace(poll=lambda: 1, returncode=1, pid=4242, terminate=lambda: None)

        def launch():
            with mock.patch.object(be, "_spawn_host", fake_spawn):
                with self.assertRaises(sb.CLIConnectionErrorLike):
                    asyncio.run(be._host_transport_for(s, types.SimpleNamespace(), (None, None, None)))

        def events():
            p = Path(d) / sb.SESSION_EVENTS_FILE
            return [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []
        launch()
        rows = events()
        self.assertEqual([r["kind"] for r in rows], ["host.exited-before-socket"], "one row, under its own kind")
        self.assertEqual((rows[0]["sid"], rows[0]["name"], rows[0]["code"]), (SID, "web", 1))
        for needle in (OTHER, sh.SDK_TESTED_VERSION, sh.SDK_REPIN_COMMAND, "web"):
            self.assertIn(needle, rows[0]["text"])
        self.assertTrue(any("exited before serving its socket" in l and sb.PROBLEM_ROW_MARK in l for l in logs), "and the log line")
        # a retry that is refused again is its own event: a second row, and still nothing under host.spawn-failed
        launch()
        self.assertEqual(len(spawned), 2)
        self.assertEqual([r["kind"] for r in events()], ["host.exited-before-socket"] * 2, "one row per refused launch")

    def test_a_host_that_exits_with_no_last_word_still_files_the_row_naming_the_log(self):
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d, True)
        be = sb.SdkBackend(d, "/bin/true", lambda *a, **k: None, log=lambda *a, **k: None)
        Path(d, "session-hosts").write_text("on")
        sb.write_reg(Path(d), SID, {"sid": SID, "name": "web", "alive": True, "lastSid": SID})
        s = types.SimpleNamespace(sid=SID, name="web", _host_intent=True, _host=None, _host_is_attach=False,
                                  _options_login="", _seed_for_dead_cli=lambda cli: None)
        fake = lambda sess, spec_path, secret_env=None: types.SimpleNamespace(poll=lambda: 3, returncode=3, pid=4242, terminate=lambda: None)
        with mock.patch.object(be, "_spawn_host", fake):
            with self.assertRaises(sb.CLIConnectionErrorLike) as cm:
                asyncio.run(be._host_transport_for(s, types.SimpleNamespace(), (None, None, None)))
        rows = [json.loads(l) for l in (Path(d) / sb.SESSION_EVENTS_FILE).read_text().splitlines()]
        self.assertEqual([r["kind"] for r in rows], ["host.exited-before-socket"], "gated on the event, not on a reason")
        self.assertEqual(rows[0]["code"], 3)
        self.assertIn("host.log", rows[0]["text"])
        self.assertIn("(code 3)", str(cm.exception))


class LaunchErrorCard(unittest.TestCase):
    """correctness-1 and kernel-1 (one defect; round 1 of the review, 2026-09-18): the mismatch reason the launch
    error carries never reached the session's card when the session's CLI had ever written a stderr line.
    launch_failure_text prefers the captured stderr tail over the exception's text, _record_launch_error handed it
    the tail, and the tail is never cleared for the life of the session object; so the card showed a stale stderr
    line and named neither version nor the repin command. A CLIConnectionErrorLike means no CLI of THIS launch ever
    started, so the tail belongs to the previous one and is excluded, as it already was for a missing dependency
    and for a CredentialError. Driven through _record_launch_error with a REAL session and a NON-EMPTY tail: a case
    on the exception's message alone passed before the fix and proved nothing."""

    def setUp(self):
        self.d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, self.d, True)
        Path(self.d, "session-hosts").write_text("off")
        self.logs = []
        self.be = sb.SdkBackend(self.d, "/bin/true", lambda *a, **k: None, log=lambda m, *a, **k: self.logs.append(m))
        sb.write_reg(Path(self.d), SID, {"sid": SID, "name": "web", "alive": True, "cwd": self.d})
        self.sess = sb.SdkSession(self.be, sb.read_reg(Path(self.d), SID))
        self.sess._on_cli_stderr("a line the previous CLI wrote before it died\n")
        self.assertTrue(self.sess.stderr_tail(), "the precondition: a non-empty tail")

    def _recorded(self):
        return (sb.read_reg(Path(self.d), SID) or {})["launchError"]

    def test_a_host_refusal_reaches_the_recorded_launch_error_over_a_stale_stderr_tail(self):
        reason = sh.sdk_mismatch_text(OTHER, LEAF + "." + NAME)
        exc = sb.CLIConnectionErrorLike("the session host exited before serving its socket (code 1); see hosts/%s/host.log: %s" % (SID, reason))
        self.be._record_launch_error(self.sess, exc)
        rec = self._recorded()
        for needle in (OTHER, sh.SDK_TESTED_VERSION, sh.SDK_REPIN_COMMAND):
            self.assertIn(needle, rec["text"])
        self.assertNotIn("previous CLI wrote", rec["text"], "the stale tail is not the card")
        self.assertFalse(rec["limit"]); self.assertFalse(rec["dep"])
        self.assertTrue(any(reason in l for l in self.logs), "the kernel log carries the reason too")
        self.assertFalse(any("claude CLI stderr (last" in l for l in self.logs), "no stale tail dumped as this launch's stderr")

    def test_an_ordinary_launch_failure_still_shows_what_the_cli_said(self):
        # the existing behaviour for a CLI of THIS launch that wrote and died: the tail is the card (test_sdk_launch_error.py)
        exc = RuntimeError("Command failed with exit code 1")
        exc.stderr = sb.SDK_STDERR_PLACEHOLDER
        self.be._record_launch_error(self.sess, exc)
        self.assertIn("previous CLI wrote", self._recorded()["text"])


class HostTransportNames(unittest.TestCase):
    """fresh-2 (round 1 of the review, 2026-09-18): kernel/host_transport.py read Transport, CLIConnectionError and
    ProcessError from the SDK's PRIVATE modules (_internal.transport, _errors) inside one try/except Exception that
    silently substituted stand-ins; all three are public exports at the pinned version. They are bound from the
    public package now, and the duck-typed fallback stays for a machine with no SDK at all (the hermetic tests,
    CI). Not added to SDK_INTERNALS: that check runs in the host process at spawn time, after this module has
    already bound its imports in the kernel process, so it would not protect this binding."""

    _NAMES = ("claude_agent_sdk", "claude_agent_sdk._internal", "claude_agent_sdk._internal.transport", "claude_agent_sdk._errors")

    def _restore_modules(self):
        saved = {n: sys.modules.get(n) for n in self._NAMES}

        def restore():
            for n, m in saved.items():
                if m is None:
                    sys.modules.pop(n, None)
                else:
                    sys.modules[n] = m
        self.addCleanup(restore)

    def _load(self, name):
        self.addCleanup(sys.modules.pop, name, None)
        return load_source(name, os.path.join(ROOT, "kernel", "host_transport.py"))

    def test_the_three_names_are_the_public_packages_not_the_private_modules(self):
        self._restore_modules()

        def module(n, package=False):
            m = types.ModuleType(n); m.__spec__ = ModuleSpec(n, loader=None)
            if package:
                m.__path__ = []
            sys.modules[n] = m
            return m
        pub = module("claude_agent_sdk", package=True)
        module("claude_agent_sdk._internal", package=True)
        priv_t = module("claude_agent_sdk._internal.transport")
        priv_e = module("claude_agent_sdk._errors")

        class Transport:
            pass

        class CLIConnectionError(Exception):
            pass

        class ProcessError(Exception):
            def __init__(self, message, exit_code=None, stderr=None):
                super().__init__(message); self.exit_code = exit_code; self.stderr = stderr
        pub.Transport, pub.CLIConnectionError, pub.ProcessError = Transport, CLIConnectionError, ProcessError
        priv_t.Transport = type("Transport", (), {})                          # the private spellings: other objects
        priv_e.CLIConnectionError = type("CLIConnectionError", (Exception,), {})
        priv_e.ProcessError = type("ProcessError", (Exception,), {})
        m = self._load("romp_host_transport_r1_public_names")
        self.assertIs(m._Base, pub.Transport, "the abstract base is the package's export")
        self.assertIs(m.CLIConnectionError, pub.CLIConnectionError)
        self.assertIs(m.ProcessError, pub.ProcessError)
        self.assertTrue(issubclass(m.HostTransport, pub.Transport))

    def test_with_no_sdk_the_duck_typed_stand_ins_still_exist(self):
        self._restore_modules()
        sys.modules["claude_agent_sdk"] = None                                # an import of it raises ModuleNotFoundError
        for n in self._NAMES[1:]:
            sys.modules.pop(n, None)
        m = self._load("romp_host_transport_r1_sdkless")
        self.assertTrue(issubclass(m.CLIConnectionError, Exception))
        e = m.ProcessError("the CLI left", exit_code=3, stderr="said so")
        self.assertEqual((e.exit_code, e.stderr, str(e)), (3, "said so", "the CLI left"))
        self.assertTrue(issubclass(m.HostTransport, m._Base))
        t = m.HostTransport("/nonexistent/host.sock", kernel={"pid": 1})
        self.assertFalse(t.is_ready())


class MachineVenv(unittest.TestCase):
    """The SDK venv on this machine, when there is one, holds the tested version and its internals resolve there:
    the SDK-transport cases in tests/test_session_host.py run the host against that venv, so a pin they did not
    verify is caught here rather than trusted. Two legs (tests-3, round 1 of the review, 2026-09-18): the metadata
    leg reads the site the venv's own record names and skips only with no venv at all; the internals probe runs
    under a python of the venv's own tag (VENV_PYTHON, resolved as tests/test_session_host_restart.py resolves the
    kernel's) and skips without one, since the real site loads cpython-tagged binary extensions that would fail
    spuriously under another minor."""

    def test_the_venv_site_is_read_from_the_venvs_own_record(self):
        d = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, d, True)
        self.assertIsNone(_venv_site(d / "none"), "no venv at all")
        (d / "lib" / "python3.11" / "site-packages").mkdir(parents=True)
        (d / "lib" / "python3.14t" / "site-packages").mkdir(parents=True)
        (d / "pyvenv.cfg").write_text("home = /usr/bin\nversion = 3.14.0\n")
        self.assertEqual(_venv_site(d), d / "lib" / "python3.14t" / "site-packages", "the cfg's version picks the lib, tag and all")
        (d / "pyvenv.cfg").write_text("home = /usr/bin\nversion_info = 3.11.2\n")
        self.assertEqual(_venv_site(d), d / "lib" / "python3.11" / "site-packages", "uv's spelling too")
        (d / "pyvenv.cfg").unlink()
        shutil.rmtree(d / "lib" / "python3.14t")
        self.assertEqual(_venv_site(d), d / "lib" / "python3.11" / "site-packages", "no record: the single lib present")

    @unittest.skipUnless(SDK_SITE, "no SDK venv on this machine")
    def test_the_machines_sdk_venv_holds_the_tested_version(self):
        dist = next(iter(importlib.metadata.Distribution.discover(name=sh.SDK_DIST, path=[str(SDK_SITE)])), None)
        self.assertIsNotNone(dist, "the venv has the package's metadata")
        self.assertEqual(dist.version, sh.SDK_TESTED_VERSION,
                         "the venv holds %s, the pin says %s: run %s (or move the pin after verifying the imports)"
                         % (dist.version, sh.SDK_TESTED_VERSION, sh.SDK_REPIN_COMMAND))

    @unittest.skipUnless(SDK_SITE and VENV_PYTHON, "no SDK venv on this machine, or no python of its tag on PATH for the probe")
    def test_the_internals_resolve_in_the_machines_venv_under_a_python_of_its_own_tag(self):
        probe = ("import importlib, json, sys\n"
                 "spec = %r\n"
                 "out = {}\n"
                 "for mod, name in spec:\n"
                 "    out[name] = hasattr(importlib.import_module(mod), name)\n"
                 "print(json.dumps(out))\n" % (list(sh.SDK_INTERNALS),))
        env = dict(os.environ, PYTHONPATH=str(SDK_SITE))
        got = subprocess.run([VENV_PYTHON, "-c", probe], env=env, capture_output=True, text=True, timeout=60)
        self.assertEqual(got.returncode, 0, got.stderr)
        self.assertEqual(json.loads(got.stdout), {name: True for _, name in sh.SDK_INTERNALS})


if __name__ == "__main__":
    unittest.main()
