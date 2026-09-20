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

Round 2 (2026-09-18) added: the cli-spawn-failed row carries the chain of types behind the failure (fresh-1); the
reason composer reads this run's rows only (correctness-1, kernel-1); and the untested-version problem row is filed
once per kernel life per version pair, not once per launch (fresh-2).

The closing check (2026-09-18) ruled on round 2's shapes and added the cases marked with it: the reason is read past
the spawn watermark the kernel takes before the host exists (host_log_mark), not back to the last host-started row,
so a host that died writing NOTHING inherits no previous host's reason (correctness-1, kernel-1, through the real
spawn road over a stale lease); the drift fact is filed as its own host.sdk-untested row on the refused roads and the
failure's reason states the version beside every spawn failure alike, never the remedy, with the type-name allowlist
gone (fresh-1); the deadline road files its own row (kernel-2); the relation guard of the reason composer is pinned,
with the field-absent case on both guards (tests-2); and the pin reads the version of the module the host imports,
falling back to the metadata (a copy ahead of the tested site, with the metadata still saying tested).

Round 3 (2026-09-19) added the pins the closing check's fix lacked, each proved by mutation (the case is red with the
watermark dropped to the file's start and green with it): the exited road's drift row in the NEXT kernel life over a
surviving log (correctness-1, extra7-1, tests-2, kernel-1), the deadline road's reason for a host that wedges after a
failing row (tests-1, correctness-2) and for one that wrote nothing over a previous host's rows (tests-1, extra7-2,
kernel-1); the once-per-kernel-life memo across two sessions (tests-3, extra8-2); the non-object JSON lines the row
reader skips (tests-4); a refused launch's rows not filed again by the next host that serves (regression-1); and the
machine venv read the way the host reads it (extra7-3, extra8-1; the installer's own leg is in the bats file).

The mutation pass after round 3 (2026-09-19) pinned the claims that had survived a code mutation with the suite green,
each proved the same way (red under the mutation, green restored): the reason composer's guard on a failing row's
error field, its early return for a host-crashed row after an untested row, its `rows[:i]` bound on the fact it
states, the `_process` guard's close before its raise, and host_transport.py's ImportError-only fallback. The exit
road's drop of hostLogPos is pinned in tests/test_host_transport.py, and the installer's refusal of a version-less
SDK in the bats file.

Round 4 (2026-09-19) added ONE case, and it pins a KNOWN-WRONG behaviour, not a wanted one (correctness-1 of that
round): test_the_pinned_residual_a_previous_hosts_unfiled_row_vanishes_after_a_refused_launch, under the round-3
banner of HostProcess, seeds a previous host's host-started, reader-behind and end-forced rows, refuses one launch and
asserts that the host that serves in the next kernel life files none of them, with a refusal-free control over the
same seed that files both. The position a refused launch records is host.log's WHOLE line count at the refusal, so the
served road skips every line present then, a previous host's unfiled row included, and that row VANISHES with no
problem row anywhere; the case records that defect so it cannot change unseen. It is green by design at 1f2042164 (no
fails-before exists: it describes the behaviour that head already had). The wanted behaviour is fixed in the queued
served-road change, which bounds the served road on the spawn watermark; this case changes with it, so a later red
here is the pin doing its job. Round 4 also corrected two case comments, prose only: the tests-4 comment states the
reverse scan the code has (the non-object lines before the last failing row are never reached), and the regression-1
comment says the recorded count is the whole file's.
"""
import asyncio
import contextlib
import importlib.abc
import importlib.metadata
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import types
import unittest
from importlib.machinery import ModuleSpec
from pathlib import Path
from unittest import mock
from romp_load import load_source
import sdk_blocker   # noqa: E402  the shared test helper, registered by name in tests/__init__.py like romp_load

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()   # hermetic BEFORE the loads
os.environ.pop("ROMP_STATE_DIR", None)
sh = load_source("romp_session_host", os.path.join(ROOT, "kernel", "session_host.py"))
sb = load_source("romp_sdk_backend", os.path.join(BIN, "romp_sdk_backend.py"))
# A PRIVATE copy of kernel/host_transport.py for the pure functions this module calls (host_exit_reason, host_dir),
# never `sb._ht()` at import (round 1 addendum, 2026-09-18). The shared `romp_host_transport` entry is bound once per
# process by the first load_source of that name and is then reused by every later _ht() without re-executing; its
# Transport base is whatever `claude_agent_sdk` resolved to at that moment. tests/test_host_transport.py puts the
# machine's SDK venv on sys.path BEFORE it binds that entry and pins HostTransport as a subclass of the SDK's
# Transport, so a module collected earlier in the same worker that binds the entry with no SDK on the path (this
# one did, through sb._ht()) leaves the pin reading a duck-typed base for the whole run. The one shared binder stays
# tests/test_host_transport.py; test_spend_rebill.py takes the same private-copy road.
ht = load_source("romp_host_transport_sdk_pin", os.path.join(ROOT, "kernel", "host_transport.py"))
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
SID2 = "11111111-2222-3333-4444-0000000000c2"         # a second session on the same box (the memo is per box, not per session)
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
    broken dependency chain looks like from sdk_internals (the leaf exists, its own `import anyio` does not).
    `name` is the module it answers for: the leaf by default, the package itself for an SDK whose own import
    raises (the mutation pass after round 3, 2026-09-19)."""

    def __init__(self, exc, name=None):
        self.exc = exc
        self.name = name or LEAF

    def find_spec(self, fullname, path=None, target=None):
        return ModuleSpec(fullname, self) if fullname == self.name else None

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

    # The closing check of the review (2026-09-18): the pin exists to know WHICH CODE IS RUNNING, and until then
    # installed_sdk_version() read importlib.metadata alone, which describes what was INSTALLED. A copy of the package
    # ahead of the tested site on sys.path with no dist-info of its own imports at its version while the metadata still
    # says the tested one, so the pin did not fire and a moved internal died as a bare AttributeError with no version
    # anywhere (the real-host case is in HostProcess). The imported module's __version__ is the authoritative source;
    # the metadata is the fallback for a package that exports none.
    def test_the_installed_version_is_the_imported_modules_and_the_metadata_only_without_one(self):
        _plant(self, with_name=True)                             # a claude_agent_sdk in sys.modules with no __version__ yet
        pkg = sys.modules[sh.SDK_PACKAGE]
        self.assertFalse(hasattr(pkg, "__version__"))
        with mock.patch.object(sh.importlib.metadata, "version", return_value="1.2.3") as v:
            self.assertEqual(sh.installed_sdk_version(), "1.2.3", "no __version__ on the module: the metadata")
            v.assert_called_once_with(sh.SDK_DIST)
            pkg.__version__ = "7.7.7"
            self.assertEqual(sh.installed_sdk_version(), "7.7.7", "the module that runs wins over the metadata")
            self.assertEqual(v.call_count, 1, "and the metadata is not consulted for it")
            pkg.__version__ = ""
            self.assertEqual(sh.installed_sdk_version(), "1.2.3", "an empty __version__ is no version")
            pkg.__version__ = None
            self.assertEqual(sh.installed_sdk_version(), "1.2.3")
        del pkg.__version__
        with mock.patch.object(sh.importlib.metadata, "version", side_effect=importlib.metadata.PackageNotFoundError(sh.SDK_DIST)):
            self.assertIsNone(sh.installed_sdk_version(), "neither the module nor the metadata says: None")
        sys.modules[sh.SDK_PACKAGE] = None                        # an import of it raises: the metadata road, as before
        with mock.patch.object(sh.importlib.metadata, "version", return_value="1.2.3"):
            self.assertEqual(sh.installed_sdk_version(), "1.2.3", "no package importable at all: the metadata, and no error of its own")
        # and with no version handed in, sdk_internals reads it from there
        _plant(self, with_name=False)
        with mock.patch.object(sh, "installed_sdk_version", return_value=OTHER):
            with self.assertRaises(sh.SdkInternalsMismatch) as cm:
                sh.sdk_internals()
        self.assertIn(OTHER, str(cm.exception))
        # the whole road, unpatched: a planted package at another version than the pin, missing the name, is the mismatch
        # at the MODULE's version, whatever the process's metadata says
        _plant(self, with_name=False)
        sys.modules[sh.SDK_PACKAGE].__version__ = "8.8.8"
        with self.assertRaises(sh.SdkInternalsMismatch) as cm:
            sh.sdk_internals()
        self.assertIn("8.8.8", str(cm.exception))

    def test_error_chain_is_the_chained_type_names_only_never_a_message(self):
        # fresh-1 (round 2 of the review, 2026-09-18): the cli-spawn-failed row carries the types BEHIND the failure,
        # so a reader of the row sees what the SDK's connect() wrapped as a connection error (a TypeError, a
        # FileNotFoundError). A recorded fact since the closing check, read by no gate. Type names only: a message
        # could carry a line of the CLI's output.
        self.assertEqual(sh.error_chain(None), "")
        self.assertEqual(sh.error_chain(FileNotFoundError("/no/such/cli")), "", "a bare exception: no chain")
        try:
            try:
                raise TypeError("__init__() got an unexpected keyword argument 'prompt'")
            except TypeError as inner:
                raise ConnectionError("Failed to start Claude Code: %s" % inner) from inner
        except ConnectionError as e:
            chain = sh.error_chain(e)
        self.assertEqual(chain, "TypeError", "an explicit `from`: the cause's type")
        self.assertNotIn("prompt", chain)
        try:
            try:
                raise KeyError("k")
            except KeyError:
                raise AttributeError("no _process")
        except AttributeError as e:
            self.assertEqual(sh.error_chain(e), "KeyError", "an implicit chain: the context's type")
        try:
            try:
                raise KeyError("k")
            except KeyError:
                raise AttributeError("no _process") from None
        except AttributeError as e:
            self.assertEqual(sh.error_chain(e), "", "`from None` suppresses the context, as the traceback module prints it")
        e = ValueError("v")
        for depth in range(10):
            nxt = ValueError("v%d" % depth)
            nxt.__cause__ = e
            e = nxt
        self.assertEqual(len(sh.error_chain(e).split(",")), sh.ERROR_CHAIN_CAP, "bounded")
        a, b = OSError("a"), OSError("b")
        a.__cause__, b.__cause__ = b, a
        self.assertEqual(sh.error_chain(a), "OSError", "a cycle ends the walk")


def _fake_site(root, version: str, with_name: bool, body: str = None, module_version: str = None) -> Path:
    """A site directory holding a fake claude_agent_sdk at `version` (a dist-info importlib.metadata reads) whose
    private transport module has the class, or not; `body` replaces the private module's source (a class whose
    constructor drifted, one that connects without a `_process`). The package exports the ClaudeAgentOptions the
    host builds its options from, so a case that reaches the spawn gets there. `module_version` is the package's
    own `__version__` when it should differ from the dist-info (a copy imported ahead of its metadata; the closing
    check, 2026-09-18); the dist-info's version otherwise."""
    site = Path(root) / "site"
    pkg = site / "claude_agent_sdk"
    (pkg / "_internal" / "transport").mkdir(parents=True)
    (pkg / "__init__.py").write_text('__version__ = %r\n\n\nclass ClaudeAgentOptions:\n    def __init__(self, **kw):\n        self.kw = kw\n'
                                     % (module_version or version))
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

    def _run_host(self, site: Path, no_sdk: bool = False):
        """The real host over `site`, handed as ROMP_SDK_SITE and as PYTHONPATH. PYTHONPATH does two jobs, both
        because the launcher's _sdk_on_path takes an SDK its interpreter imports before it reads ROMP_SDK_SITE. A
        fake claude_agent_sdk package in `site` shadows a real SDK the interpreter has. And `no_sdk` (2026-09-20)
        writes a sitecustomize.py into `site` that sets sys.modules["claude_agent_sdk"] = None before the host
        imports anything, which hides a real SDK from the child (find_spec None, the import raises
        ModuleNotFoundError); an empty site did not, so under an interpreter that has the SDK installed (every CI
        cell since the workflow installs the pinned SDK; a venv built the same way on a box) the no-SDK control ran
        the SDK transport and read CLINotFoundError for a missing CLI where the pipe transport reads
        FileNotFoundError. The blocker witnesses its own run (tests/sdk_blocker.py) and the control asserts the witness:
        without it, an interpreter with no SDK passed the control whatever the blocker did, the pipe transport being its
        only road."""
        if no_sdk:
            site.mkdir(parents=True, exist_ok=True)
            (site / "sitecustomize.py").write_text(sdk_blocker.SITECUSTOMIZE)
        env = dict(os.environ, PYTHONUNBUFFERED="1", ROMP_SDK_SITE=str(site), PYTHONPATH=str(site))
        if no_sdk:
            env[sdk_blocker.WITNESS_ENV] = str(self.hostdir / "blocker-witness")
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
        # tests-4 (round 3 of the review, 2026-09-19; the mechanism corrected in round 4): a line that parses as JSON
        # but is not an object (null, a list, a number) is skipped by host_log_rows like the unparseable one, so
        # host_exit_reason never sees one at this head; that is what the guard buys. The three lines sit BEFORE the
        # later failing row as fixture context only: the scan runs in REVERSE and returns at that row, the last line,
        # so it never reaches them, and the 'later' assertion below holds with the guard dropped too. The guard is
        # pinned by two legs, each independent (execution stops at the first failure, so the second is reached only
        # with the first removed): the row reader's kinds list (with the guard dropped to a bare append, a TypeError
        # in this case's own comprehension, `r["kind"]` on a None row), and a non-object LAST line (an AttributeError
        # from the scan's own `.get`; a non-object reaches that `.get` only after the row the scan returns at, or
        # when no row returns at all, or, for a cli-spawn-failed row, in the composer's walk over the rows before it).
        with open(hd / "host.log", "a") as f:
            f.write("null\n[1, 2]\n42\n" + json.dumps({"t": 3, "kind": "host-crashed", "error": "later"}) + "\n")
        self.assertEqual(ht.host_exit_reason(d, SID), "later", "the last such row wins")
        self.assertEqual([r["kind"] for r in ht.host_log_rows(d, SID)], ["host-started", "cli-spawn-failed", "host-crashed"],
                         "the row reader returns objects only")
        (hd / "host.log").write_text(json.dumps({"t": 1, "kind": "cli-spawn-failed", "error": "OSError"}) + "\nnull\n")
        self.assertEqual(ht.host_exit_reason(d, SID), "OSError", "a non-object LAST line is skipped by the row reader too")

    # The mutation pass after round 3 (2026-09-19): the composer's guard on the error field (`or not row.get("error")`)
    # was held by no case, so with it dropped the suite stayed green. A failing-kind row that carries no error, an
    # empty one or a null one says nothing: it is stepped over, the scan goes on to an earlier row that does say, and
    # a log with no row that says is "". Without the guard a row with no field is a KeyError out of the launch road,
    # a null one reads "None", and an empty cli-spawn-failed row after an untested row composes the version fact
    # around no failure at all.
    def test_a_failing_row_with_no_error_an_empty_one_or_a_null_one_says_nothing_and_is_stepped_over(self):
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d, True)
        hd = ht.host_dir(d, SID); hd.mkdir(parents=True)
        started = {"t": 1, "kind": "host-started"}
        untested = {"t": 2, "kind": "sdk-version-untested", "installed": OTHER, "tested": sh.SDK_TESTED_VERSION, "relation": "newer"}

        def reason(rows):
            (hd / "host.log").write_text("".join(json.dumps(r) + "\n" for r in rows))
            return ht.host_exit_reason(d, SID)
        for kind in ("host-crashed", "cli-spawn-failed"):
            for silent in ({"t": 3, "kind": kind}, {"t": 3, "kind": kind, "error": ""}, {"t": 3, "kind": kind, "error": None}):
                self.assertEqual(reason([started, silent]), "", silent)
                self.assertEqual(reason([started, untested, silent]), "", ("no failure to state the fact beside", silent))
                self.assertEqual(reason([started, {"t": 2, "kind": kind, "error": "FileNotFoundError"}, silent]), "FileNotFoundError",
                                 ("stepped over, to the row that says", silent))

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

    # fresh-2 (round 2 of the review, 2026-09-18): the venv's version is a machine condition, the same for every host
    # on the box, and the row was filed per launch through a path that passes no ring key, so every relaunch appended a
    # byte-identical error-centre entry and bumped problem_seq, the feed's cache key. Reported once per kernel life per
    # version pair, like the missing-wrapper fallback; a repeat is one plain kernel-log line naming the session.
    def test_an_untested_sdk_is_filed_once_per_kernel_life_not_once_per_launch(self):
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d, True); logs = []
        be = sb.SdkBackend(d, "/bin/true", lambda *a, **k: None, log=logs.append)
        sb.write_reg(Path(d), SID, {"sid": SID, "name": "web", "alive": True, "lastSid": SID})
        hd = ht.host_dir(d, SID); hd.mkdir(parents=True)

        def launch(pid, installed=OTHER, relation="newer"):
            # a new host each time: its own identity (hostLogPos is keyed by it, so its log is read from zero) and a
            # fresh host.log holding the run's two rows, as a relaunch of the session writes; relation None leaves
            # the field out
            row = {"t": 2, "kind": "sdk-version-untested", "installed": installed, "tested": sh.SDK_TESTED_VERSION}
            if relation is not None:
                row["relation"] = relation
            (hd / "host.log").write_text(json.dumps({"t": 1, "kind": "host-started"}) + "\n" + json.dumps(row) + "\n")
            sess = types.SimpleNamespace(sid=SID, name="web", _host=types.SimpleNamespace(hello={"host": {"pid": pid, "start": "s%d" % pid}}))
            be._file_host_log_rows(sess)

        def events():
            p = Path(d) / sb.SESSION_EVENTS_FILE
            return [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []
        base = be.problem_seq()                                # the constructor's own boot probes may have filed
        launch(101)
        self.assertEqual([r["kind"] for r in events()], ["host.sdk-untested"])
        self.assertEqual(be.problem_seq(), base + 1)
        launch(102)
        self.assertEqual([r["kind"] for r in events()], ["host.sdk-untested"], "the second launch under the same condition files no second row")
        self.assertEqual(len([p for p in be.problems() if OTHER in p["text"]]), 1, "one error-centre entry")
        self.assertEqual(be.problem_seq(), base + 1, "the feed's cache key did not move")
        self.assertTrue(any("web" in l and OTHER in l and sb.PROBLEM_ROW_MARK not in l and "once" in l for l in logs),
                        "the repeat is one plain kernel-log line naming the session: %r" % logs)
        # another version is another condition: reported anew, and a relation that does not parse says "other than"
        launch(103, installed="not-a-version", relation="different")
        rows = events()
        self.assertEqual([r["kind"] for r in rows], ["host.sdk-untested"] * 2)
        self.assertEqual(be.problem_seq(), base + 2)
        self.assertIn("other than", rows[1]["text"])
        self.assertNotIn("different than", rows[1]["text"])
        self.assertNotIn("None", rows[1]["text"])
        # the field absent (tests-2, finished at the closing check, 2026-09-18): "other than", never "None than"
        launch(104, installed="0.0.0.0", relation=None)
        rows = events()
        self.assertEqual(len(rows), 3)
        self.assertNotIn("relation", rows[2])
        self.assertIn("0.0.0.0, other than the %s" % sh.SDK_TESTED_VERSION, rows[2]["text"])
        self.assertNotIn("None", rows[2]["text"])

    # regression-1 (round 1 of the review, 2026-09-18): the loud failure covered only a MISSING module or name. A
    # private class that is present but whose signature drifted died as a bare exception type name in the
    # cli-spawn-failed row, and the version context the host had just written (the sdk-version-untested row) was
    # shown to no one. The row keeps the type name (that field is a type name everywhere else and is splatted into
    # the problem row); host_exit_reason states the version this host ran beside it, from the untested row of the
    # same run, as a fact and not a remedy (the closing check, 2026-09-18: the remedy rides with the fact's own
    # problem row). The control below: a machine with no SDK at all fails the same arm through the pipe transport
    # and must not be given SDK text.
    _DRIFTED = "class %s:\n    def __init__(self, cmd):\n        self.cmd = cmd\n" % NAME

    def test_a_spawn_failure_on_an_untested_sdk_reaches_the_launch_error_with_the_version_it_ran_beside_the_type(self):
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
        self.assertTrue(reason.startswith("TypeError (this host ran "), reason)
        for needle in (OTHER, sh.SDK_TESTED_VERSION, "newer than"):
            self.assertIn(needle, reason)
        self.assertNotIn(sh.SDK_REPIN_COMMAND, reason, "a fact beside the failure, never its remedy (the closing check)")

    def test_a_spawn_failure_with_no_sdk_at_all_keeps_the_bare_type_name(self):
        # the control: the pipe transport's spawn of a CLI that is not there, with no SDK importable by the host
        # (no_sdk: the site hides one the interpreter has; an empty site alone left this control on the SDK transport)
        spec = json.loads(self.spec_path.read_text())
        spec["cli_path"] = os.path.join(self.state, "no-such-cli")
        self.spec_path.write_text(json.dumps(spec))
        empty = Path(self.state, "nosite")
        empty.mkdir()
        code, _ = self._run_host(empty, no_sdk=True)
        self.assertEqual(code, 1)
        sdk_blocker.assert_witnessed(self, str(self.hostdir / "blocker-witness"), sdk_blocker.interpreter_imports_sdk())
        kinds = [r["kind"] for r in self._hostlog()]
        self.assertNotIn("sdk-version-untested", kinds)
        self.assertIn("cli-spawn-failed", kinds)
        self.assertEqual(ht.host_exit_reason(self.state, SID), "FileNotFoundError", "no SDK, no SDK text")

    def test_host_exit_reason_states_the_version_from_the_untested_row_of_this_run_only(self):
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d, True)
        hd = ht.host_dir(d, SID); hd.mkdir(parents=True)
        rows = [{"t": 1, "kind": "host-started"},
                {"t": 2, "kind": "sdk-version-untested", "installed": OTHER, "tested": sh.SDK_TESTED_VERSION, "relation": "newer"},
                {"t": 3, "kind": "cli-spawn-failed", "error": "TypeError"}]
        (hd / "host.log").write_text("".join(json.dumps(r) + "\n" for r in rows))
        reason = ht.host_exit_reason(d, SID)
        self.assertEqual(reason, "TypeError (this host ran %s %s, newer than the %s the session host is written against)"
                         % (sh.SDK_DIST, OTHER, sh.SDK_TESTED_VERSION))
        # a later run in the same log with no untested row of its own, read from ITS spawn watermark: the bare type
        # name, never the first run's fact (the closing check, 2026-09-18: the mark, not the marker, is the bound)
        mark = ht.host_log_mark(d, SID)
        with open(hd / "host.log", "a") as f:
            f.write(json.dumps({"t": 4, "kind": "host-started"}) + "\n" + json.dumps({"t": 5, "kind": "cli-spawn-failed", "error": "FileNotFoundError"}) + "\n")
        self.assertEqual(ht.host_exit_reason(d, SID, since=mark), "FileNotFoundError")

    # The mutation pass after round 3 (2026-09-19): the composer's `rows[:i]` was held by no case; with the fact read
    # from every row in the window, an untested row AFTER the failing row counted too, and the suite stayed green. The
    # fact stated beside a failure is one this host wrote before it: in a run the untested row precedes the spawn, so
    # a row after the failing row belongs to a later host (a caller reading the whole file over two runs, the first
    # run's failure and the second run's untested row from a host still running) and is not that failure's version.
    def test_an_untested_row_written_after_the_failing_row_is_not_that_failures_fact(self):
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d, True)
        hd = ht.host_dir(d, SID); hd.mkdir(parents=True)
        failed = {"t": 2, "kind": "cli-spawn-failed", "error": "FileNotFoundError"}
        untested = {"t": 4, "kind": "sdk-version-untested", "installed": OTHER, "tested": sh.SDK_TESTED_VERSION, "relation": "newer"}

        def reason(rows):
            (hd / "host.log").write_text("".join(json.dumps(r) + "\n" for r in rows))
            return ht.host_exit_reason(d, SID)
        self.assertEqual(reason([{"t": 1, "kind": "host-started"}, failed, {"t": 3, "kind": "host-started"}, untested]), "FileNotFoundError",
                         "the second run's fact, read over the whole file, is not the first run's")
        self.assertEqual(reason([{"t": 1, "kind": "host-started"}, failed, untested]), "FileNotFoundError",
                         "a row after the failure with no marker between is still after it")
        self.assertEqual(reason([{"t": 1, "kind": "host-started"}, dict(untested, t=1), failed]),
                         "FileNotFoundError (this host ran %s %s, newer than the %s the session host is written against)"
                         % (sh.SDK_DIST, OTHER, sh.SDK_TESTED_VERSION), "the order the host writes: a fact before the failure counts")

    # tests-2 (round 2 of the review, finished at the closing check, 2026-09-18): the relation guard in this composer
    # ("newer than", "older than", else "other than") had no test that reddened it (the round-2 case asserted only
    # that "newer" was absent for an unparsed relation), and the field-absent case was tested in neither this guard
    # nor its twin in the backend's problem-row prose. With the guard dropped to a bare format the two rows below read
    # "different than" and "None than"; this case fails on either.
    def test_host_exit_reason_says_other_than_for_a_relation_that_is_not_newer_or_older_or_is_absent(self):
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d, True)
        hd = ht.host_dir(d, SID); hd.mkdir(parents=True)
        for extra in ({"relation": "different"}, {}, {"relation": "same"}):
            rows = [{"t": 1, "kind": "host-started"},
                    dict({"t": 2, "kind": "sdk-version-untested", "installed": "not-a-version", "tested": sh.SDK_TESTED_VERSION}, **extra),
                    {"t": 3, "kind": "cli-spawn-failed", "error": "ValueError"}]
            (hd / "host.log").write_text("".join(json.dumps(r) + "\n" for r in rows))
            got = ht.host_exit_reason(d, SID)
            self.assertEqual(got, "ValueError (this host ran %s not-a-version, other than the %s the session host is written against)"
                             % (sh.SDK_DIST, sh.SDK_TESTED_VERSION), (extra, got))
            for bad in ("different than", "same than", "None", "newer", "older"):
                self.assertNotIn(bad, got, (extra, got))
        for relation in ("newer", "older"):
            rows[1]["relation"] = relation
            (hd / "host.log").write_text("".join(json.dumps(r) + "\n" for r in rows))
            self.assertIn(", %s than the %s " % (relation, sh.SDK_TESTED_VERSION), ht.host_exit_reason(d, SID))

    # fresh-1 (round 2 of the review; the closing check's ruling on round 2's fix, 2026-09-18): round 1 attached the
    # version sentence and the repin remedy to every spawn failure after an untested row, so a missing binary was told
    # to reinstall the SDK; round 2 gated it on an allowlist of type names, wrong in both directions at 0.2.156 (a
    # ValueError from option validation is drift and got no context; a TypeError from a dependency's signature is not
    # and got the remedy). Now the type name leads, the version this host ran follows as a fact in parentheses for
    # EVERY spawn failure alike, and the remedy is in none of them: it rides with the fact's own problem row
    # (host.sdk-untested, filed on the refused road too). No untested row in this run, no fact.
    def test_host_exit_reason_states_the_version_beside_every_spawn_failure_alike_and_never_the_remedy(self):
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d, True)
        hd = ht.host_dir(d, SID); hd.mkdir(parents=True)

        def reason(error, causes=None, untested=True):
            row = {"t": 3, "kind": "cli-spawn-failed", "error": error}
            if causes:
                row["causes"] = causes
            rows = [{"t": 1, "kind": "host-started"}] + ([
                {"t": 2, "kind": "sdk-version-untested", "installed": OTHER, "tested": sh.SDK_TESTED_VERSION, "relation": "newer"}] if untested else []) + [row]
            (hd / "host.log").write_text("".join(json.dumps(r) + "\n" for r in rows))
            return ht.host_exit_reason(d, SID)
        fact = " (this host ran %s %s, newer than the %s the session host is written against)" % (sh.SDK_DIST, OTHER, sh.SDK_TESTED_VERSION)
        for error, causes in (("FileNotFoundError", None), ("PermissionError", None), ("CLINotFoundError", "FileNotFoundError"),
                              ("CLIConnectionError", "FileNotFoundError"), ("CLIConnectionError", None), ("OSError", None),
                              ("ValueError", None), ("TypeError", None), ("AttributeError", None), ("ModuleNotFoundError", None),
                              ("ImportError", None), ("CLIConnectionError", "TypeError"), ("CLIConnectionError", "RuntimeError,AttributeError")):
            got = reason(error, causes)
            self.assertEqual(got, error + fact, (error, causes, got))
            self.assertNotIn(sh.SDK_REPIN_COMMAND, got, "the remedy rides with the fact's own row, never with a failure")
            self.assertNotIn("run ", got)
            self.assertNotIn(":", got.split(" (", 1)[0], "the type name is the first word, unpunctuated")
        for error in ("TypeError", "FileNotFoundError", "CLIConnectionError"):
            self.assertEqual(reason(error, untested=False), error, "no untested row in this run: the bare type name")
        self.assertFalse(hasattr(sh, "SDK_DRIFT_ERRORS"), "the type-name allowlist is gone with the gate")

    _MISSING_BINARY = ("class %s:\n    def __init__(self, **kw):\n        pass\n\n    async def connect(self):\n"
                       "        raise FileNotFoundError(2, 'No such file or directory', '/no/such/claude')\n" % NAME)
    _WRAPPED_DRIFT = ("class CLIConnectionError(Exception):\n    pass\n\n\nclass %s:\n    def __init__(self, **kw):\n        pass\n\n"
                      "    async def connect(self):\n        try:\n            raise TypeError('_build_command() takes 1 positional argument')\n"
                      "        except TypeError as e:\n            raise CLIConnectionError('Failed to start Claude Code: %%s' %% e) from e\n" % NAME)

    def test_a_missing_binary_on_an_untested_sdk_is_the_bare_type_with_the_version_beside_it_through_the_real_host(self):
        code, _ = self._run_host(_fake_site(self.state, OTHER, with_name=True, body=self._MISSING_BINARY))
        self.assertEqual(code, 1)
        rows = self._hostlog()
        self.assertIn("sdk-version-untested", [r["kind"] for r in rows], "the untested row IS there: the fact is stated")
        failed = [r for r in rows if r["kind"] == "cli-spawn-failed"]
        self.assertEqual(len(failed), 1)
        self.assertEqual(failed[0]["error"], "FileNotFoundError")
        self.assertNotIn("causes", failed[0], "a bare exception carries no chain")
        reason = ht.host_exit_reason(self.state, SID)
        self.assertTrue(reason.startswith("FileNotFoundError (this host ran "), reason)
        self.assertIn(OTHER, reason)
        self.assertNotIn(sh.SDK_REPIN_COMMAND, reason, "a missing binary is never told to reinstall the SDK")

    def test_a_drift_the_sdk_wrapped_as_a_connection_error_carries_the_chain_on_its_row(self):
        code, _ = self._run_host(_fake_site(self.state, OTHER, with_name=True, body=self._WRAPPED_DRIFT))
        self.assertEqual(code, 1)
        failed = [r for r in self._hostlog() if r["kind"] == "cli-spawn-failed"]
        self.assertEqual((failed[0]["error"], failed[0]["causes"]), ("CLIConnectionError", "TypeError"), "the row records what the wrap hid")
        self.assertNotIn("_build_command", json.dumps(failed), "type names only, never the message")
        reason = ht.host_exit_reason(self.state, SID)
        self.assertTrue(reason.startswith("CLIConnectionError (this host ran "), reason)
        for needle in (OTHER, sh.SDK_TESTED_VERSION, "newer than"):
            self.assertIn(needle, reason)
        self.assertNotIn(sh.SDK_REPIN_COMMAND, reason, "the same fact, the same absence of a remedy, whatever the type")

    # The closing check of the review (2026-09-18): the pin read importlib.metadata, which describes what was
    # installed, not what runs. A package whose own __version__ is another version than its dist-info (a copy ahead of
    # the tested site on the path with no metadata of its own) imported at ITS version while the metadata said tested,
    # so the direct-import road ran and a moved internal died as a bare AttributeError on the cli-spawn-failed row with
    # no version anywhere. The module is the authority; the host names the version that runs.
    def test_a_copy_of_the_sdk_imported_ahead_of_its_metadata_is_pinned_at_the_version_that_runs(self):
        code, stderr = self._run_host(_fake_site(self.state, sh.SDK_TESTED_VERSION, with_name=False, module_version=OTHER))
        self.assertEqual(code, 1)
        rows = self._hostlog()
        kinds = [r["kind"] for r in rows]
        self.assertIn("host-crashed", kinds, "the mismatch verdict, not a bare spawn failure: %r" % kinds)
        self.assertNotIn("cli-spawn-failed", kinds)
        crash = [r for r in rows if r["kind"] == "host-crashed"][0]["error"]
        self.assertTrue(crash.startswith(sh.sdk_mismatch_text(OTHER, LEAF + "." + NAME)), crash)
        for needle in (OTHER, sh.SDK_TESTED_VERSION, sh.SDK_REPIN_COMMAND):
            self.assertIn(needle, crash)
        self.assertNotIn("broken", crash, "another version, not the tested one with a broken install")
        self.assertIn(crash, stderr)

    # correctness-1 and kernel-1 (round 2 of the review; the closing check's ruling, 2026-09-18): the reason is read
    # past the spawn watermark the kernel takes before the host exists (host_log_mark, host.log's size), not back to
    # the last host-started row. Round 2 bounded on the marker, and the marker is the host's own claim to have run: a
    # host that died writing NOTHING (an OOM, a refused scope) left none, so that launch read back into the previous
    # host's run and carried its reason and remedy onto the card and into the ledger. The spawn is the event itself.
    def test_host_exit_reason_reads_past_the_spawn_watermark_never_a_previous_hosts_last_word(self):
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d, True)
        hd = ht.host_dir(d, SID); hd.mkdir(parents=True)
        self.assertEqual(ht.host_log_mark(d, SID), 0, "no log yet: the mark is the start")
        self.assertEqual(ht.host_log_rows(d, SID), [])
        first = [{"t": 1, "kind": "host-started"},
                 {"t": 2, "kind": "sdk-version-untested", "installed": OTHER, "tested": sh.SDK_TESTED_VERSION, "relation": "newer"},
                 {"t": 3, "kind": "cli-spawn-failed", "error": "TypeError"}]
        (hd / "host.log").write_text("".join(json.dumps(r) + "\n" for r in first))
        self.assertIn(OTHER, ht.host_exit_reason(d, SID, since=0), "the first run's reason, read from its own mark")
        mark = ht.host_log_mark(d, SID)
        self.assertEqual(mark, (hd / "host.log").stat().st_size, "the mark is the file's size before the next host")
        # the second host wrote NOTHING, the case round 2 left broken: past its mark there is no row, so no reason
        self.assertEqual(ht.host_exit_reason(d, SID, since=mark), "", "nothing from the first run: the launch error falls back to the log's path")
        self.assertEqual(ht.host_log_rows(d, SID, since=mark), [])
        # a second host that wrote only its marker, or rows that are not failures, says nothing either
        with open(hd / "host.log", "a") as f:
            f.write(json.dumps({"t": 4, "kind": "host-started", "hostPid": 4242}) + "\n" + json.dumps({"t": 5, "kind": "attached"}) + "\n")
        self.assertEqual(ht.host_exit_reason(d, SID, since=mark), "")
        self.assertEqual([r["kind"] for r in ht.host_log_rows(d, SID, since=mark)], ["host-started", "attached"])
        # a second host's own failure is read, and the FIRST host's untested row is not its fact
        with open(hd / "host.log", "a") as f:
            f.write(json.dumps({"t": 6, "kind": "cli-spawn-failed", "error": "FileNotFoundError"}) + "\n")
        self.assertEqual(ht.host_exit_reason(d, SID, since=mark), "FileNotFoundError")
        # the same for a crash row: a previous host's whole-text verdict is not this launch's either
        crash = [{"t": 1, "kind": "host-started"}, {"t": 2, "kind": "host-crashed", "error": sh.sdk_mismatch_text(OTHER, LEAF + "." + NAME)}]
        (hd / "host.log").write_text("".join(json.dumps(r) + "\n" for r in crash))
        mark = ht.host_log_mark(d, SID)
        self.assertEqual(ht.host_exit_reason(d, SID, since=mark), "")
        self.assertIn(OTHER, ht.host_exit_reason(d, SID), "a caller with no mark reads the whole file")
        # the mark is bytes, not lines: a line a dying host left unterminated stays with its run and the next row parses whole
        (hd / "host.log").write_text(json.dumps({"t": 1, "kind": "host-started"}) + "\n" + '{"t": 2, "kind": "host-cra')
        mark = ht.host_log_mark(d, SID)
        with open(hd / "host.log", "a") as f:
            f.write(json.dumps({"t": 3, "kind": "host-crashed", "error": "OSError: AF_UNIX path too long"}) + "\n")
        self.assertEqual(ht.host_exit_reason(d, SID, since=mark), "OSError: AF_UNIX path too long")
        self.assertEqual(ht.host_exit_reason(d, SID), "", "a line count would have merged the fragment into the row")
        self.assertEqual(ht.host_exit_reason(d, SID, since=10 ** 6), "", "a mark past the end reads nothing and raises nothing")

    def test_a_launch_whose_host_wrote_nothing_inherits_no_previous_hosts_reason_through_the_real_spawn_road(self):
        # the checker's reproduction, executed: a stale KERNEL-held lease on disk keeps hosts/<sid> across launches (with
        # no lease the leftover directory is cleared before a spawn; a valid one refuses the launch; a kernel-held one
        # that no longer holds takes neither road, so the spawn runs over the previous host's log). The first host
        # writes its crash record; the second dies writing nothing; the second launch's error and ledger row must
        # carry nothing of the first's.
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d, True); logs = []
        be = sb.SdkBackend(d, "/bin/true", lambda *a, **k: None, log=lambda m, *a, **k: logs.append(m))
        Path(d, "session-hosts").write_text("on")
        sb.write_reg(Path(d), SID, {"sid": SID, "name": "web", "alive": True, "lastSid": SID})
        stale = {"sid": SID, "pid": 2 ** 22 - 1, "start": "gone", "t": 0, "holder": {"kind": "kernel", "pid": 2 ** 22 - 2, "start": "gone"}}
        sb.write_lease(d, stale)
        self.assertEqual(sb.lease_state(sb.read_lease(d, SID), time.time()), "no-live-process", "the precondition: a lease that does not hold, held by no host")
        s = types.SimpleNamespace(sid=SID, name="web", _host_intent=True, _host=None, _host_is_attach=False,
                                  _options_login="", _seed_for_dead_cli=lambda cli: None)
        text = sh.sdk_mismatch_text(OTHER, LEAF + "." + NAME)
        writes = [[{"t": 1, "kind": "host-started"}, {"t": 2, "kind": "host-crashed", "error": text}], []]

        def fake_spawn(sess, spec_path, secret_env=None):
            with open(Path(spec_path).parent / "host.log", "a") as f:
                for row in writes.pop(0):
                    f.write(json.dumps(row) + "\n")
            return types.SimpleNamespace(poll=lambda: 1, returncode=1, pid=4242, terminate=lambda: None)

        def launch():
            with mock.patch.object(be, "_spawn_host", fake_spawn):
                with self.assertRaises(sb.CLIConnectionErrorLike) as cm:
                    asyncio.run(be._host_transport_for(s, types.SimpleNamespace(), (None, None, None)))
            return str(cm.exception)
        first = launch()
        self.assertIn(text, first, "the first host's own reason")
        self.assertEqual([json.loads(l)["kind"] for l in (ht.host_dir(d, SID) / "host.log").read_text().splitlines()],
                         ["host-started", "host-crashed"], "the log survived the launch: the stale lease kept the directory")
        second = launch()
        self.assertEqual(writes, [], "both hosts ran")
        self.assertNotIn(text, second, "the second host wrote nothing, so nothing is its reason")
        for needle in (OTHER, sh.SDK_REPIN_COMMAND, "written against"):
            self.assertNotIn(needle, second)
        self.assertTrue(second.endswith("see hosts/%s/host.log" % SID), second)
        rows = [json.loads(l) for l in (Path(d) / sb.SESSION_EVENTS_FILE).read_text().splitlines()]
        self.assertEqual([r["kind"] for r in rows], ["host.exited-before-socket"] * 2)
        self.assertIn(text, rows[0]["text"])
        self.assertNotIn(text, rows[1]["text"], "nor is it the second launch's ledger row")
        self.assertNotIn(OTHER, rows[1]["text"])

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

    # The mutation pass after round 3 (2026-09-19): the early return that carries a host-crashed row WHOLE was held by
    # no case, so with it dropped a crash row after an untested row had the version fact composed onto the host's own
    # prose and the suite stayed green. The composed fact is for a cli-spawn-failed row, whose error is a bare type
    # name; a host-crashed row is the host's own text (the mismatch verdict names both versions itself, a traceback's
    # last line names its error) and gets nothing appended. The real road for the pair is the `_process` guard at
    # another version, whose host writes its untested row and then its crash record in one run.
    def test_a_crash_row_after_an_untested_row_is_carried_whole_with_no_version_fact_composed_onto_it(self):
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d, True)
        hd = ht.host_dir(d, SID); hd.mkdir(parents=True)
        for text in ("OSError: AF_UNIX path too long", sh.sdk_mismatch_text(OTHER, LEAF + "." + NAME + "._process")):
            rows = [{"t": 1, "kind": "host-started"},
                    {"t": 2, "kind": "sdk-version-untested", "installed": OTHER, "tested": sh.SDK_TESTED_VERSION, "relation": "newer"},
                    {"t": 3, "kind": "host-crashed", "error": text}]
            (hd / "host.log").write_text("".join(json.dumps(r) + "\n" for r in rows))
            got = ht.host_exit_reason(d, SID)
            self.assertEqual(got, text)
            self.assertNotIn("this host ran", got)
        code, _ = self._run_host(_fake_site(self.state, OTHER, with_name=True, body=self._NO_PROCESS))
        self.assertEqual(code, 1)
        rows = self._hostlog()
        kinds = [r["kind"] for r in rows]
        self.assertLess(kinds.index("sdk-version-untested"), kinds.index("host-crashed"), "the pair, in the order the host writes it: %r" % kinds)
        crash = [r for r in rows if r["kind"] == "host-crashed"][0]["error"]
        self.assertEqual(ht.host_exit_reason(self.state, SID), crash, "the kernel's launch error carries the verdict whole")

    # The mutation pass after round 3 (2026-09-19): the guard's close() before its raise (tests-2, round 1) was held by
    # no case; with it removed the suite stayed green. A transport that connected and exposes no `_process` may have
    # started a CLI under another name all the same; the host closes it before it refuses, so a refused launch leaves
    # no CLI of its own running. The fake transport records its close in a file the case names, at both versions.
    def test_the_process_guard_closes_the_transport_it_refuses_before_it_raises(self):
        for version, root in ((OTHER, Path(self.state)), (sh.SDK_TESTED_VERSION, Path(self.state, "tested"))):
            root.mkdir(exist_ok=True)
            mark = root / "closed.mark"
            body = ("class %s:\n    def __init__(self, **kw):\n        pass\n\n    async def connect(self):\n        pass\n\n"
                    "    async def close(self):\n        open(%r, 'w').write('closed')\n" % (NAME, str(mark)))
            code, _ = self._run_host(_fake_site(root, version, with_name=True, body=body))
            self.assertEqual(code, 1, version)
            kinds = [r["kind"] for r in self._hostlog()]
            self.assertIn("host-crashed", kinds, version)
            self.assertNotIn("cli-spawned", kinds, version)
            self.assertTrue(mark.exists(), "close() ran before the refusal at %s: %r" % (version, kinds))
            (self.hostdir / "host.log").unlink()

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

    def _refusing_backend(self):
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d, True); logs = []
        be = sb.SdkBackend(d, "/bin/true", lambda *a, **k: None, log=lambda m, *a, **k: logs.append(m))
        Path(d, "session-hosts").write_text("on")
        sb.write_reg(Path(d), SID, {"sid": SID, "name": "web", "alive": True, "lastSid": SID})
        s = types.SimpleNamespace(sid=SID, name="web", _host_intent=True, _host=None, _host_is_attach=False,
                                  _options_login="", _seed_for_dead_cli=lambda cli: None)

        def events():
            p = Path(d) / sb.SESSION_EVENTS_FILE
            return [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []
        return d, be, s, logs, events

    # fresh-1 (round 2 of the review; the closing check's ruling, 2026-09-18): the drift fact is filed on its own row on
    # the refused road, whatever the failure was, and the failure's row keeps the failure's own type with the version
    # beside it and no remedy. Until then a refused launch's only trace of the drift was a sentence composed into the
    # failure's reason behind an allowlist of type names (host.sdk-untested is filed from _file_host_log_rows at the
    # hello and the exit, which a host that never served reaches neither of).
    def test_a_refused_launch_on_an_untested_sdk_files_the_drift_fact_on_its_own_row_and_the_failure_bare(self):
        d, be, s, logs, events = self._refusing_backend()
        untested = {"t": 2, "kind": "sdk-version-untested", "installed": OTHER, "tested": sh.SDK_TESTED_VERSION, "relation": "newer"}
        writes = [[{"t": 1, "kind": "host-started"}, untested, {"t": 3, "kind": "cli-spawn-failed", "error": "TypeError"}],
                  [{"t": 4, "kind": "host-started"}, untested, {"t": 5, "kind": "cli-spawn-failed", "error": "CLIConnectionError", "causes": "FileNotFoundError"}]]

        def fake_spawn(sess, spec_path, secret_env=None):
            with open(Path(spec_path).parent / "host.log", "a") as f:
                for row in writes.pop(0):
                    f.write(json.dumps(row) + "\n")
            return types.SimpleNamespace(poll=lambda: 1, returncode=1, pid=4242, terminate=lambda: None)

        def launch():
            with mock.patch.object(be, "_spawn_host", fake_spawn):
                with self.assertRaises(sb.CLIConnectionErrorLike) as cm:
                    asyncio.run(be._host_transport_for(s, types.SimpleNamespace(), (None, None, None)))
            return str(cm.exception)
        first = launch()
        rows = events()
        self.assertEqual([r["kind"] for r in rows], ["host.sdk-untested", "host.exited-before-socket"], "the fact on its own row, then the failure")
        self.assertEqual((rows[0]["sid"], rows[0]["installed"], rows[0]["tested"], rows[0]["relation"]), (SID, OTHER, sh.SDK_TESTED_VERSION, "newer"))
        for needle in (OTHER, sh.SDK_TESTED_VERSION, "newer than", sh.SDK_REPIN_COMMAND, "web"):
            self.assertIn(needle, rows[0]["text"], "the fact's row carries the remedy")
        self.assertIn("host.log: TypeError (this host ran %s %s, newer than" % (sh.SDK_DIST, OTHER), rows[1]["text"])
        self.assertNotIn(sh.SDK_REPIN_COMMAND, rows[1]["text"], "the failure's row carries no remedy")
        self.assertIn("TypeError (this host ran", first)
        self.assertNotIn(sh.SDK_REPIN_COMMAND, first, "nor does the card")
        # a missing binary the SDK wrapped, under the same pair: the same fact, already filed this kernel life, so one
        # plain log line and no second fact row; its own failure row, bare type first, the version beside it, no remedy
        second = launch()
        rows = events()
        self.assertEqual([r["kind"] for r in rows], ["host.sdk-untested", "host.exited-before-socket", "host.exited-before-socket"])
        self.assertIn("host.log: CLIConnectionError (this host ran", rows[2]["text"])
        self.assertNotIn(sh.SDK_REPIN_COMMAND, rows[2]["text"])
        self.assertNotIn(sh.SDK_REPIN_COMMAND, second)
        self.assertTrue(any("web" in l and OTHER in l and "once" in l and sb.PROBLEM_ROW_MARK not in l for l in logs), logs)
        self.assertEqual(sum(1 for l in logs if "host.sdk-untested" in l and sb.PROBLEM_ROW_MARK in l), 1, "one problem-row line for the fact")

    # kernel-2 (round 2 of the review, ruled MISSING by the closing check, 2026-09-18): the deadline road (SOCKET_WAIT_S
    # elapsed, no socket, the host ended) filed no row at all, while the comment over the exited road read as covering
    # every refused launch; the checker verified it with the wait patched short against a stub that never serves and
    # an empty session-events.jsonl. Its own kind: this host was ended rather than exited and has no return code.
    def test_a_host_that_never_serves_its_socket_files_one_row_of_its_own_kind_at_the_deadline(self):
        d, be, s, logs, events = self._refusing_backend()
        ended = []

        def fake_spawn(sess, spec_path, secret_env=None):
            with open(Path(spec_path).parent / "host.log", "a") as f:
                f.write(json.dumps({"t": 1, "kind": "host-started"}) + "\n")
            return types.SimpleNamespace(poll=lambda: None, returncode=None, pid=4242, terminate=lambda: ended.append(1))
        with mock.patch.object(sb._ht(), "SOCKET_WAIT_S", 0.3), mock.patch.object(be, "_spawn_host", fake_spawn):
            with self.assertRaises(sb.CLIConnectionErrorLike) as cm:
                asyncio.run(be._host_transport_for(s, types.SimpleNamespace(), (None, None, None)))
        self.assertEqual(ended, [1], "the host was ended")
        rows = events()
        self.assertEqual([r["kind"] for r in rows], ["host.never-served-socket"], "exactly one row, under its own kind")
        self.assertEqual((rows[0]["sid"], rows[0]["name"], rows[0]["waitS"]), (SID, "web", 0.3))
        self.assertNotIn("code", rows[0], "ended, not exited: no return code to record")
        self.assertIn("did not serve its socket", rows[0]["text"])
        self.assertTrue(any("did not serve its socket" in l and sb.PROBLEM_ROW_MARK in l for l in logs), "and the log line")
        msg = str(cm.exception)
        self.assertIn("did not serve its socket within 0 s; it was ended", msg)
        self.assertTrue(msg.endswith("see hosts/%s/host.log" % SID), msg)

    def test_a_host_that_wrote_its_untested_row_and_then_wedged_has_that_fact_filed_at_the_deadline_too(self):
        d, be, s, logs, events = self._refusing_backend()

        def fake_spawn(sess, spec_path, secret_env=None):
            with open(Path(spec_path).parent / "host.log", "a") as f:
                f.write(json.dumps({"t": 1, "kind": "host-started"}) + "\n"
                        + json.dumps({"t": 2, "kind": "sdk-version-untested", "installed": OTHER, "tested": sh.SDK_TESTED_VERSION, "relation": "newer"}) + "\n")
            return types.SimpleNamespace(poll=lambda: None, returncode=None, pid=4242, terminate=lambda: None)
        with mock.patch.object(sb._ht(), "SOCKET_WAIT_S", 0.3), mock.patch.object(be, "_spawn_host", fake_spawn):
            with self.assertRaises(sb.CLIConnectionErrorLike) as cm:
                asyncio.run(be._host_transport_for(s, types.SimpleNamespace(), (None, None, None)))
        rows = events()
        self.assertEqual([r["kind"] for r in rows], ["host.sdk-untested", "host.never-served-socket"])
        self.assertIn(sh.SDK_REPIN_COMMAND, rows[0]["text"])
        self.assertTrue(rows[1]["text"].endswith("see hosts/%s/host.log" % SID), "no failing row, so no reason: the log's path alone")
        self.assertNotIn(OTHER, str(cm.exception), "a wedged host wrote no failure to state the version beside")

    # ── round 3 of the review (2026-09-19): the spawn watermark, pinned by mutation ──────────────────────────────
    # The closing check's fix (the reason and the drift row read past host_log_mark, host.log's size before the spawn)
    # was held by no test: dropping any of its four reads to the file's start (since=0 in _file_refused_launch_context,
    # a 0 for the mark at either of its call sites, since=0 on the deadline road's reason read) or replacing the
    # deadline road's reason with "" left the whole suite green, and under each a refused launch filed a FALSE
    # host.sdk-untested row carrying a previous host's version and the repin remedy. The cases below each go red under
    # the mutation they name and green with the read as written; a case green under the mutation is not a pin. Every
    # one needs the stale KERNEL-held lease: with no lease the leftover directory is cleared before the spawn and no
    # seeded row survives, so a lease-less version of these cases pins nothing (the refuters verified that both ways).
    _STALE = {"pid": 2 ** 22 - 1, "start": "gone", "t": 0, "holder": {"kind": "kernel", "pid": 2 ** 22 - 2, "start": "gone"}}
    _UNTESTED = {"t": 2, "kind": "sdk-version-untested", "installed": OTHER, "tested": sh.SDK_TESTED_VERSION, "relation": "newer"}

    def _stale_lease_root(self, sids=((SID, "web"),)):
        """A state root with hosts on and, for each (sid, name), a registry entry and a stale kernel-held lease (a
        crashed kernel's leftover: a holder of kind kernel with no live process), which keeps hosts/<sid> and its
        host.log across launches. Returns the root and its session-events reader; backends are minted by the case,
        since a kernel life is one backend and the memo lives in it."""
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d, True)
        Path(d, "session-hosts").write_text("on")
        for sid, name in sids:
            sb.write_reg(Path(d), sid, {"sid": sid, "name": name, "alive": True, "lastSid": sid, "cwd": d})
            sb.write_lease(d, dict(self._STALE, sid=sid))
            self.assertEqual(sb.lease_state(sb.read_lease(d, sid), time.time()), "no-live-process", "the precondition")

        def events():
            p = Path(d) / sb.SESSION_EVENTS_FILE
            return [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []
        return d, events

    @staticmethod
    def _backend(d, logs):
        return sb.SdkBackend(d, "/bin/true", lambda *a, **k: None, log=lambda m, *a, **k: logs.append(m))

    @staticmethod
    def _sess(sid=SID, name="web"):
        return types.SimpleNamespace(sid=sid, name=name, _host_intent=True, _host=None, _host_is_attach=False,
                                     _options_login="", _seed_for_dead_cli=lambda cli: None)

    @staticmethod
    def _exiting(rows, code=1):
        """A fake _spawn_host whose host appends `rows` to host.log and has exited (poll() gives `code`)."""
        def spawn(sess, spec_path, secret_env=None):
            with open(Path(spec_path).parent / "host.log", "a") as f:
                for row in rows:
                    f.write(json.dumps(row) + "\n")
            return types.SimpleNamespace(poll=lambda: code, returncode=code, pid=4242, terminate=lambda: None)
        return spawn

    @staticmethod
    def _wedging(rows, ended=None):
        """A fake _spawn_host whose host appends `rows` and then never exits (poll() stays None): the deadline road."""
        def spawn(sess, spec_path, secret_env=None):
            with open(Path(spec_path).parent / "host.log", "a") as f:
                for row in rows:
                    f.write(json.dumps(row) + "\n")
            return types.SimpleNamespace(poll=lambda: None, returncode=None, pid=4343,
                                         terminate=lambda: ended.append(1) if ended is not None else None)
        return spawn

    def _launch(self, be, sess, spawn, wait=None):
        """One _host_transport_for through `spawn`, refused: the exception. `wait` shortens SOCKET_WAIT_S for the
        deadline road."""
        with contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch.object(be, "_spawn_host", spawn))
            if wait is not None:
                stack.enter_context(mock.patch.object(sb._ht(), "SOCKET_WAIT_S", wait))
            with self.assertRaises(sb.CLIConnectionErrorLike) as cm:
                asyncio.run(be._host_transport_for(sess, types.SimpleNamespace(), (None, None, None)))
        return cm.exception

    # correctness-1, extra7-1, tests-2 and kernel-1 (the exited road): red with `since=0` in _file_refused_launch_context
    # or a 0 for the mark at the exited road's call. A SECOND backend is the discriminating part: it is the next kernel
    # life, with an empty memo, over the same surviving log; one backend with one more launch is absorbed by the memo.
    def test_the_next_kernel_life_files_no_drift_row_from_a_previous_hosts_untested_row_when_its_host_wrote_nothing(self):
        d, events = self._stale_lease_root()
        first_logs, second_logs = [], []
        be1 = self._backend(d, first_logs)
        self._launch(be1, self._sess(), self._exiting([{"t": 1, "kind": "host-started"}, self._UNTESTED,
                                                       {"t": 3, "kind": "cli-spawn-failed", "error": "TypeError"}]))
        self.assertEqual([r["kind"] for r in events()], ["host.sdk-untested", "host.exited-before-socket"], "the first life: the fact, then the failure")
        self.assertEqual(len((ht.host_dir(d, SID) / "host.log").read_text().splitlines()), 3, "the log survived: the stale lease kept the directory")
        # the next kernel life: a fresh backend (an empty memo), whose host dies writing nothing
        be2 = self._backend(d, second_logs)
        second = str(self._launch(be2, self._sess(), self._exiting([])))
        rows = events()
        self.assertEqual([r["kind"] for r in rows], ["host.sdk-untested", "host.exited-before-socket", "host.exited-before-socket"],
                         "no second drift row: the first host's fact is not this launch's")
        self.assertTrue(second.endswith("see hosts/%s/host.log" % SID), second)
        for needle in (OTHER, sh.SDK_REPIN_COMMAND, "written against", "this host ran"):
            self.assertNotIn(needle, second)
            self.assertNotIn(needle, rows[2]["text"])
        self.assertFalse(any(OTHER in l for l in second_logs), "nor a kernel-log line about it in the second life: %r" % second_logs)
        # and a host of the second life that failed on its own has its own bare type, never the first host's fact beside it
        third = str(self._launch(be2, self._sess(), self._exiting([{"t": 4, "kind": "host-started"},
                                                                    {"t": 5, "kind": "cli-spawn-failed", "error": "FileNotFoundError"}])))
        rows = events()
        self.assertEqual(len(rows), 4)
        self.assertTrue(third.endswith("host.log: FileNotFoundError"), third)
        self.assertTrue(rows[3]["text"].endswith("host.log: FileNotFoundError"), rows[3]["text"])
        self.assertEqual([r["kind"] for r in rows].count("host.sdk-untested"), 1)

    # tests-1 (leg 1) and correctness-2 (the deadline road's reason): red with the read replaced by `reason = ""`. A
    # real host leaves some 16 to 19 ms between a failing row and its exit, so this read answers for a host that wedges
    # AFTER failing (a non-daemon worker thread can hold a process open), a reachable shape and not ordinary failure.
    def test_a_host_that_wedges_after_a_failing_row_has_that_row_read_at_the_deadline(self):
        d, be, s, logs, events = self._refusing_backend()
        ended = []
        exc = str(self._launch(be, s, self._wedging([{"t": 1, "kind": "host-started"}, self._UNTESTED,
                                                     {"t": 3, "kind": "cli-spawn-failed", "error": "TypeError"}], ended), wait=0.3))
        self.assertEqual(ended, [1], "the wedged host was ended")
        rows = events()
        self.assertEqual([r["kind"] for r in rows], ["host.sdk-untested", "host.never-served-socket"])
        fact = "host.log: TypeError (this host ran %s %s, newer than" % (sh.SDK_DIST, OTHER)
        self.assertIn(fact, exc, "the card carries the failing row's type with the version beside it")
        self.assertIn(fact, rows[1]["text"], "and so does the ledger row")
        self.assertNotIn(sh.SDK_REPIN_COMMAND, exc); self.assertNotIn(sh.SDK_REPIN_COMMAND, rows[1]["text"])
        self.assertIn(sh.SDK_REPIN_COMMAND, rows[0]["text"], "the remedy rides with the fact's own row")
        # the same road with no untested row: the bare type, and the reason still read
        d2, be2, s2, logs2, events2 = self._refusing_backend()
        exc2 = str(self._launch(be2, s2, self._wedging([{"t": 1, "kind": "host-started"},
                                                        {"t": 2, "kind": "cli-spawn-failed", "error": "FileNotFoundError"}]), wait=0.3))
        rows2 = events2()
        self.assertEqual([r["kind"] for r in rows2], ["host.never-served-socket"])
        self.assertTrue(exc2.endswith("host.log: FileNotFoundError"), exc2)
        self.assertTrue(rows2[0]["text"].endswith("host.log: FileNotFoundError"), rows2[0]["text"])

    # tests-1 (leg 2), extra7-2 and kernel-1 (the deadline road's watermark): red with `since=0` on the deadline road's
    # reason read, or a 0 for the mark at its _file_refused_launch_context call, or `since=0` inside that function.
    # The previous host's rows are seeded before the spawn (a host of an earlier kernel life whose crash record and
    # untested row survived under the stale lease); this launch's host wedges writing nothing.
    def test_a_wedged_host_that_wrote_nothing_inherits_no_previous_hosts_reason_or_drift_row_at_the_deadline(self):
        d, events = self._stale_lease_root()
        hd = ht.host_dir(d, SID); hd.mkdir(parents=True)
        previous = [{"t": 1, "kind": "host-started"}, self._UNTESTED, {"t": 3, "kind": "cli-spawn-failed", "error": "TypeError"},
                    {"t": 4, "kind": "host-started"}, {"t": 5, "kind": "host-crashed", "error": sh.sdk_mismatch_text(OTHER, LEAF + "." + NAME)}]
        (hd / "host.log").write_text("".join(json.dumps(r) + "\n" for r in previous))
        logs = []
        be = self._backend(d, logs)                          # a new kernel life: nothing in the memo
        ended = []
        exc = self._launch(be, self._sess(), self._wedging([], ended), wait=0.3)
        self.assertEqual(ended, [1])
        text = str(exc)
        rows = events()
        self.assertEqual([r["kind"] for r in rows], ["host.never-served-socket"], "no drift row: the untested row in the file is a previous host's")
        self.assertTrue(text.endswith("did not serve its socket within 0 s; it was ended; see hosts/%s/host.log" % SID), text)
        self.assertTrue(rows[0]["text"].endswith("see hosts/%s/host.log" % SID), rows[0]["text"])
        # the recorded launch error, the card's source, ends there too
        real = sb.SdkSession(be, sb.read_reg(Path(d), SID))
        be._record_launch_error(real, exc)
        recorded = (sb.read_reg(Path(d), SID) or {})["launchError"]["text"]
        self.assertTrue(recorded.endswith("see hosts/%s/host.log" % SID), recorded)
        for needle in (OTHER, sh.SDK_TESTED_VERSION, sh.SDK_REPIN_COMMAND, "written against", "TypeError", "this host ran"):
            for where, s in (("the exception", text), ("the ledger row", rows[0]["text"]), ("the recorded launch error", recorded)):
                self.assertNotIn(needle, s, "%s carries a previous host's %r" % (where, needle))
        self.assertFalse(any(OTHER in l for l in logs), "no kernel-log line about the previous host's version either")
        self.assertEqual(len((hd / "host.log").read_text().splitlines()), len(previous), "the wedged host wrote nothing and the file is intact")

    # regression-1 (round 3 of the review, 2026-09-19): a refused launch was reported twice over a surviving log,
    # host.exited-before-socket at the refusal and then host.spawn-failed for the SAME cli-spawn-failed row at the
    # next host's hello, because the served road starts an identity it has not seen at line zero and the refused roads
    # recorded no position. Now they record host.log's line count at the refusal (hostLogPos under
    # HOST_LOG_POS_REFUSED) and the served road starts the next host, whatever its identity, past it. Red on the tree
    # before the fix. The count is the whole file's; what that does to a previous host's unfiled row is the next case's.
    def test_a_refused_launchs_rows_are_not_filed_again_when_a_later_host_serves_over_the_surviving_log(self):
        d, events = self._stale_lease_root()
        be1 = self._backend(d, [])
        self._launch(be1, self._sess(), self._exiting([{"t": 1, "kind": "host-started"}, self._UNTESTED,
                                                       {"t": 3, "kind": "cli-spawn-failed", "error": "TypeError"}]))
        self.assertEqual([r["kind"] for r in events()], ["host.sdk-untested", "host.exited-before-socket"])
        # the next kernel life (an empty memo): a host SERVES over the surviving log, and its hello files the log's rows
        logs = []
        be2 = self._backend(d, logs)
        served = types.SimpleNamespace(sid=SID, name="web", _host=types.SimpleNamespace(hello={"host": {"pid": 77, "start": "s77"}}))
        be2._file_host_log_rows(served)
        kinds = [r["kind"] for r in events()]
        self.assertNotIn("host.spawn-failed", kinds, "the refused launch's failure row is not a second report: %r" % kinds)
        self.assertEqual(kinds, ["host.sdk-untested", "host.exited-before-socket"], "nor its untested row a second drift row")
        self.assertFalse(any(OTHER in l for l in logs), "and no kernel-log line for it in this life: %r" % logs)
        # the served host's own rows are still filed, once
        with open(ht.host_dir(d, SID) / "host.log", "a") as f:
            f.write(json.dumps({"t": 9, "kind": "reader-behind"}) + "\n")
        be2._file_host_log_rows(served)
        self.assertEqual([r["kind"] for r in events()], ["host.sdk-untested", "host.exited-before-socket", "host.reader-behind"])
        be2._file_host_log_rows(served)
        self.assertEqual(len(events()), 3, "no line is filed twice")
        kept = (sb.read_reg(Path(d), SID) or {})["hostLogPos"]
        self.assertEqual(kept, {"host": "77:s77", "pos": 4}, "the position now belongs to the served host")
        # the mechanism: both refused roads record the file's line count at the refusal, under a host that is no identity
        d2, events2 = self._stale_lease_root()
        be3 = self._backend(d2, [])
        self._launch(be3, self._sess(), self._exiting([{"t": 1, "kind": "host-started"}, {"t": 2, "kind": "cli-spawn-failed", "error": "OSError"}]))
        self.assertEqual((sb.read_reg(Path(d2), SID) or {})["hostLogPos"], {"host": sb.HOST_LOG_POS_REFUSED, "pos": 2})
        self._launch(be3, self._sess(), self._wedging([{"t": 3, "kind": "host-started"}]), wait=0.3)
        self.assertEqual((sb.read_reg(Path(d2), SID) or {})["hostLogPos"], {"host": sb.HOST_LOG_POS_REFUSED, "pos": 3}, "the deadline road too")
        self.assertEqual([r["kind"] for r in events2()], ["host.exited-before-socket", "host.never-served-socket"])
        # a kernel restart attaching to the SAME served host still continues from its own position (the identity key)
        sb.write_reg(Path(d2), SID, dict(sb.read_reg(Path(d2), SID), hostLogPos={"host": "77:s77", "pos": 3}))
        with open(ht.host_dir(d2, SID) / "host.log", "a") as f:
            f.write(json.dumps({"t": 4, "kind": "end-forced", "cliPid": 5}) + "\n")
        be3._file_host_log_rows(types.SimpleNamespace(sid=SID, name="web", _host=types.SimpleNamespace(hello={"host": {"pid": 77, "start": "s77"}})))
        self.assertEqual([r["kind"] for r in events2()], ["host.exited-before-socket", "host.never-served-socket", "host.end-forced"])

    # correctness-1 (round 4 of the review, 2026-09-19): the position a refused launch records is host.log's WHOLE line
    # count, not the extent of what the refusal filed, so the served road's bound also skips a previous host's row
    # that no road had filed. THIS CASE PINS THE RESIDUAL, NOT THE WANTED BEHAVIOUR: after a refused launch such a
    # row (a reader-behind, an end-forced from a host of an earlier kernel life, kept under the stale lease) is filed
    # by no road and vanishes; on the round-3 base, before the position existed, the next serving host filed it as
    # its own, misattributed. A single prefix position cannot keep the rows before the spawn watermark and skip the
    # rows after it (the refuters executed both spellings), so the behaviour is fixed in the queued served-road
    # change, and this case changes with it; until then it catches a silent change of the drop. The control beside
    # it, the same seed with no refusal, is what makes the drop the refusal's doing.
    def test_the_pinned_residual_a_previous_hosts_unfiled_row_vanishes_after_a_refused_launch(self):
        seed = [{"t": 1, "kind": "host-started"}, {"t": 2, "kind": "reader-behind"}, {"t": 3, "kind": "end-forced", "cliPid": 9}]
        d, events = self._stale_lease_root()
        hd = ht.host_dir(d, SID); hd.mkdir(parents=True)
        (hd / "host.log").write_text("".join(json.dumps(r) + "\n" for r in seed))
        self._launch(self._backend(d, []), self._sess(),
                     self._exiting([{"t": 4, "kind": "host-started"}, {"t": 5, "kind": "cli-spawn-failed", "error": "OSError"}]))
        self.assertEqual([r["kind"] for r in events()], ["host.exited-before-socket"], "the refusal files its own row and none of the previous host's")
        self.assertEqual((sb.read_reg(Path(d), SID) or {})["hostLogPos"], {"host": sb.HOST_LOG_POS_REFUSED, "pos": 5},
                         "the recorded position is the whole file's line count: the three seeded lines and this launch's two")
        served = types.SimpleNamespace(sid=SID, name="web", _host=types.SimpleNamespace(hello={"host": {"pid": 88, "start": "s88"}}))
        be2 = self._backend(d, [])                            # the next kernel life: a host serves over the surviving log
        be2._file_host_log_rows(served)
        kinds = [r["kind"] for r in events()]
        self.assertEqual(kinds, ["host.exited-before-socket"], "the residual: the seeded reader-behind and end-forced rows are filed by no road")
        self.assertNotIn("host.spawn-failed", kinds, "and the refusal is still counted once")
        # the served host's OWN row of the same kind is filed, so the drop is the bound's doing and not the kind's
        with open(hd / "host.log", "a") as f:
            f.write(json.dumps({"t": 6, "kind": "reader-behind"}) + "\n")
        be2._file_host_log_rows(served)
        self.assertEqual([r["kind"] for r in events()], ["host.exited-before-socket", "host.reader-behind"])
        self.assertEqual((sb.read_reg(Path(d), SID) or {})["hostLogPos"], {"host": "88:s88", "pos": 6})
        # the control: the same seed and no refused launch before the serving host; the served road files both rows,
        # under the new host's name (the other half of the residual, stated in round 3)
        d2, events2 = self._stale_lease_root()
        hd2 = ht.host_dir(d2, SID); hd2.mkdir(parents=True)
        (hd2 / "host.log").write_text("".join(json.dumps(r) + "\n" for r in seed))
        self._backend(d2, [])._file_host_log_rows(served)
        self.assertEqual([r["kind"] for r in events2()], ["host.reader-behind", "host.end-forced"], "without the refusal the rows are filed")

    # tests-3 and extra8-2 (round 3 of the review, 2026-09-19): the memo's key is the (installed, tested) pair and NOT
    # the sid, so a second SESSION under the same pair files no row and gets the plain kernel-log line; the comment, the
    # docstring, both docs and the ledger say so, and no test held it (a sid in the key left every case green). Red
    # with the sid added to the key, in either spelling.
    def test_the_untested_row_is_once_per_kernel_life_across_sessions_not_once_per_session(self):
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d, True); logs = []
        be = sb.SdkBackend(d, "/bin/true", lambda *a, **k: None, log=logs.append)

        def events():
            p = Path(d) / sb.SESSION_EVENTS_FILE
            return [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []
        base = be.problem_seq()
        for sid, name, pid in ((SID, "web", 101), (SID2, "api", 202)):
            sb.write_reg(Path(d), sid, {"sid": sid, "name": name, "alive": True, "lastSid": sid})
            hd = ht.host_dir(d, sid); hd.mkdir(parents=True)
            (hd / "host.log").write_text(json.dumps({"t": 1, "kind": "host-started"}) + "\n" + json.dumps(self._UNTESTED) + "\n")
            sess = types.SimpleNamespace(sid=sid, name=name, _host=types.SimpleNamespace(hello={"host": {"pid": pid, "start": "s%d" % pid}}))
            be._file_host_log_rows(sess)
        rows = events()
        self.assertEqual([r["kind"] for r in rows], ["host.sdk-untested"], "one row for the box, whichever session met it first")
        self.assertEqual((rows[0]["sid"], rows[0]["name"]), (SID, "web"))
        self.assertEqual(len([p for p in be.problems() if OTHER in p["text"]]), 1, "one error-centre entry")
        self.assertEqual(be.problem_seq(), base + 1)
        self.assertTrue(any("api" in l and OTHER in l and "once" in l and sb.PROBLEM_ROW_MARK not in l for l in logs),
                        "the second session is one plain kernel-log line naming it: %r" % logs)
        self.assertEqual(sum(1 for l in logs if "host.sdk-untested" in l and sb.PROBLEM_ROW_MARK in l), 1)
        self.assertEqual(be._sdk_untested_reported, {(OTHER, sh.SDK_TESTED_VERSION)}, "the key is the pair alone")


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

    # The mutation pass after round 3 (2026-09-19): round 1's narrowing of the fallback's catch from a bare Exception
    # to ImportError (fresh-2) was held by no case, so widened back the suite stayed green. The fallback is for a
    # machine with no SDK, and absence is an ImportError; an SDK that is present and fails to import for any other
    # reason (a module body that raises at import, a half-written install) is the loud failure the pin exists for,
    # not a silent duck-typed stand-in that the first host launch would then contradict.
    def test_an_sdk_that_is_present_and_fails_to_import_for_another_reason_raises_out_of_the_load(self):
        self._restore_modules()
        for n in self._NAMES:
            sys.modules.pop(n, None)
        finder = _RaisingLeaf(RuntimeError("the package's import-time check failed"), name="claude_agent_sdk")
        sys.meta_path.insert(0, finder)
        self.addCleanup(lambda: sys.meta_path.remove(finder) if finder in sys.meta_path else None)
        with self.assertRaises(RuntimeError):
            self._load("romp_host_transport_mutation_raising_sdk")
        self.assertNotIn("romp_host_transport_mutation_raising_sdk", sys.modules, "a load that raised bound nothing")
        sys.meta_path.remove(finder)
        sys.modules["claude_agent_sdk"] = None                                # the control: absence, the ImportError the fallback is for
        m = self._load("romp_host_transport_mutation_absent_sdk")
        self.assertTrue(issubclass(m.HostTransport, m._Base))


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

    # extra7-3 and extra8-1 (round 3 of the review, 2026-09-19): the metadata leg above reads what was INSTALLED; the
    # host reads what RUNS (installed_sdk_version: the imported module's __version__, the metadata as the fallback),
    # and bin/romp-sdk-setup's verify step now calls that same function by path under the venv's python. This leg
    # reads the machine's venv the way both of them do, under a python of the venv's tag, so a site whose module
    # and dist-info disagree fails here the way it fails at a launch; the installer's own case, over a fixture that
    # plants that disagreement, is in tests/install-optional-deps.bats.
    @unittest.skipUnless(SDK_SITE and VENV_PYTHON, "no SDK venv on this machine, or no python of its tag on PATH for the probe")
    def test_the_machines_sdk_venv_reads_the_tested_version_the_way_the_host_and_the_installer_read_it(self):
        probe = ("import importlib.util, json\n"
                 "spec = importlib.util.spec_from_file_location('romp_session_host_probe', %r)\n"
                 "m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)\n"
                 "import claude_agent_sdk as sdk\n"
                 "print(json.dumps({'have': m.installed_sdk_version(), 'module': getattr(sdk, '__version__', None), 'pin': m.SDK_TESTED_VERSION}))\n"
                 % os.path.join(ROOT, "kernel", "session_host.py"))
        env = dict(os.environ, PYTHONPATH=str(SDK_SITE))
        got = subprocess.run([VENV_PYTHON, "-c", probe], env=env, capture_output=True, text=True, timeout=60)
        self.assertEqual(got.returncode, 0, got.stderr)
        out = json.loads(got.stdout)
        self.assertEqual(out["have"], sh.SDK_TESTED_VERSION,
                         "the venv's module reads %s, the pin says %s: run %s (or move the pin after verifying the imports)"
                         % (out["have"], sh.SDK_TESTED_VERSION, sh.SDK_REPIN_COMMAND))
        self.assertEqual(out["module"], out["have"], "the module's own __version__ is what the read returns when the module exports one")

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
