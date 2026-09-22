#!/usr/bin/env python3
"""The kernel's side of the per-session host (T315, stage 4 of #1317): the HostTransport over a fake host
socket and over an orphan journal, the settings, the spawn specification, the host scopes in the sweep,
the six-method Transport pin, the spec-tracks-the-SDK pin, and the backend wiring pins.

Hermetic: temp state roots, a fake host server inside the test (an asyncio Unix server speaking the
frame protocol), synthetic ids, no real CLI. Tests needing the SDK skip without it.

Two effects on the rest of a pytest process, both from the import block below that puts romp's SDK venv on
sys.path when claude_agent_sdk is not already importable (the kernel's own _ensure_sdk_on_path idiom; CI has no
venv and the SDK-gated cases skip). (1) The cases that build the SDK's options with a can_use_tool callback raise
claude_agent_sdk.types.CanUseToolShadowedWarning, a UserWarning subclass the SDK emits when the callback is set
beside a permission mode or an allowed_tools entry that auto-approves a tool before the callback is consulted.
Under pytest-xdist the worker ships that warning to the controller, whose venv cannot import the class: xdist's
unserialize_warning_message raises ModuleNotFoundError, the node goes down and the run ends in INTERNALERROR.
tests/conftest.py's pytest_configure ignores the warning by message prefix, so an -n run no longer needs
-p no:warnings. (2) Every module the same xdist worker collects after this one sees claude_agent_sdk importable:
tests/test_sdk_backend.py's _HAVE_SDK gate opens and its SDK-gated cases run instead of skipping. Five of them
(OptionsAssembly, FastModeReportedState, ApiRetryState twice, ReconnectReconcilesInflight) were red against the
installed SDK that way until 2026-09-16 (stale pins, a missing event loop, a fake's init timing and one real defect
in the api_retry detail, all fixed then); they pass both ways now. Judge either module by itself: `python3 -m pytest tests/test_host_transport.py -q`,
`python3 -m pytest tests/test_sdk_backend.py -q`.
"""
import asyncio
import contextlib
import fcntl
import importlib.util
import inspect
import json
import os
import re
import shutil
import stat
import sys
import tempfile
import threading
import time
import types
import unittest
from pathlib import Path
from unittest import mock
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)
os.environ["ROMP_CLI_SCOPE"] = "0"          # no scopes: a test's children sit in the tester's own scope
# the SDK, when this machine has the venv bin/romp-sdk-setup builds (the kernel's own _ensure_sdk_on_path
# does the same at boot); CI has none and the SDK-gated tests skip there
if importlib.util.find_spec("claude_agent_sdk") is None:
    _tag = "python%d.%d" % sys.version_info[:2]
    for _sp in sorted(Path(os.path.expanduser("~/.local/state/romp/sdkvenv/lib")).glob(_tag + "/site-packages")):
        sys.path.insert(0, str(_sp))
sb = load_source("romp_sdk_backend", os.path.join(BIN, "romp_sdk_backend.py"))
ht = sb._ht()
sh = ht.sh
SDK = importlib.util.find_spec("claude_agent_sdk") is not None
SID = "11111111-2222-3333-4444-0000000000b1"
SIDS = ("11111111-2222-3333-4444-0000000000c1", "11111111-2222-3333-4444-0000000000c2", "11111111-2222-3333-4444-0000000000c3")
#   three sessions' synthetic sids for the shared-subject pins (fork PR #884's fifth commit): the rows' subject is one hosts/


def foreign_uid(path, delta=1):
    """The DESCRIPTOR-ONLY foreign owner: `st_uid + delta` (1 unless a pin needs a second foreign owner, the fork PR that
    follows #814: a changed observed state is a new row) for the ONE object at `path` (keyed on its (st_dev, st_ino), so
    every other object answers as before) from os.fstat of a descriptor on it and from os.stat or os.lstat of its name
    with `dir_fd` given (a fstatat under a directory descriptor), and NOT from a stat by path. A PATH-form stat of the
    object (os.stat or os.lstat on a path resolving to it, and through them Path.stat, Path.lstat, Path.exists and
    Path.is_file) answers the real owner and is COUNTED on `.path_stats` (`.path_stat_calls` names each), and every
    behavioural pin that uses this stub asserts the count is 0: the round-7 fifth addendum of fork PR #814's review
    (2026-09-20). Through the fourth addendum the stub swapped the owner on the path form too, so the pins could not tell
    the descriptor fstat from a path stat: the verifier's mutation that made read_host_file's owner check a path stat
    left this module green and only the source census red. The way the fstat pins simulate another uid's file, since this
    user cannot chown to one (the fourth addendum; the removal road's and the read descent's foreign-uid pins key their
    stubs the same way). A context manager; use it as `with foreign_uid(p) as fu:` and read `fu.path_stats` after."""
    import pathlib
    st = os.lstat(path)
    ident, real_fstat, real_stat, real_lstat = (st.st_dev, st.st_ino), os.fstat, os.stat, os.lstat

    class _Stub:
        path_stats = 0

        def __init__(self):
            self.path_stat_calls = []

        def _swap(self, r):
            if (r.st_dev, r.st_ino) != ident:
                return r
            fields = list(r); fields[4] = r.st_uid + delta
            return os.stat_result(fields)

        def _answer(self, fn, real, target, a, k):
            r = real(target, *a, **k)
            if isinstance(target, int) or k.get("dir_fd") is not None:
                return self._swap(r)                       # a descriptor, or a name under one: the foreign owner
            if (r.st_dev, r.st_ino) == ident:              # the path form on the planted object: counted, the real owner
                self.path_stats += 1
                self.path_stat_calls.append((fn, os.fspath(target)))
            return r

        def __enter__(self):
            stub = self
            fstat = lambda fd: stub._swap(real_fstat(fd))
            stat_ = lambda target, *a, **k: stub._answer("os.stat", real_stat, target, a, k)
            lstat_ = lambda target, *a, **k: stub._answer("os.lstat", real_lstat, target, a, k)
            self._patches = [mock.patch.object(os, "fstat", fstat), mock.patch.object(os, "stat", stat_),
                             mock.patch.object(os, "lstat", lstat_)]
            if hasattr(pathlib, "_NormalAccessor"):        # 3.10 binds os.stat into the accessor at import; 3.11+ calls os.stat
                self._patches += [mock.patch.object(pathlib._NormalAccessor, "stat", staticmethod(stat_)),
                                  mock.patch.object(pathlib._NormalAccessor, "lstat", staticmethod(lstat_))]
            for p in self._patches:
                p.start()
            return self

        def __exit__(self, *exc):
            for p in reversed(self._patches):
                p.stop()
            return False
    return _Stub()


def bind_unix_socket(path):
    """A UNIX socket file bound at `path` and left there (closing the socket unlinks nothing): the shape a peer's
    server leaves at a name. Bound by the absolute path when it fits sun_path, else by its basename from the parent
    (a chdir and back, this test process's own cwd), since a state root under a long TMPDIR puts the name past the
    108-byte budget and a rename in from a short directory would fail across filesystems."""
    import socket
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        try:
            s.bind(str(path))
        except OSError:                                    # AF_UNIX path too long
            cwd = os.getcwd()
            os.chdir(os.path.dirname(str(path)))
            try:
                s.bind(os.path.basename(str(path)))
            finally:
                os.chdir(cwd)
    finally:
        s.close()
    assert stat.S_ISSOCK(os.lstat(path).st_mode), path


# THE SHAPE TABLE (the round-7 fifth addendum of fork PR #814's review, 2026-09-20): every kind of entry a peer can put
# at identity.json or host.log under a loose `hosts/<sid>/` of ours, by owner, and the answer each of the two readers
# gives (host_transport.host_file_exists, host_transport.read_host_file) and each of the three read roads files
# (kernel/sdk_backend.py: _host_lease_applies over identity.json's existence, _host_orphan_recover over identity.json's
# bytes, _file_host_log_rows over host.log's bytes). The population: the kinds mknod-free code can create (absent, a
# regular file, a symlink to a file, a dangling symlink, a directory, a FIFO, a UNIX socket) times the owner (ours,
# another uid's by the foreign_uid stub; `absent` has no owner), 13 rows; times the two readers, 26 cells; times the
# three roads, 39; and, since the round-7 seventh addendum (2026-09-20), the SPAWN road's three host.log readers
# (host_log_mark, host_log_rows, host_exit_reason, under a 0700 <sid>/ of ours) answer the `read` column too, 39 more
# cells at function level (ReadDescent), the absent answer being 0, [] and "" there and a foreign entry a refusal of the
# launch at the mark or one row on a refused arm (BackendHostRules). A device node is EXCLUDED: mknod of one needs CAP_MKNOD, which no peer here has, and it would take
# the non-regular arm (`False`/`None`, nothing opened) as a FIFO does. The answers: `absent` is the reader's absent
# answer (False, None); `ours` is the file read as ours (True, its bytes); `foreign` is HostFileForeign (one
# host.directory-refused row with `file` and `uid`, then the road's absent answer); `link` is the file-shape
# HostDirRefused (the row with `file` and no `uid`; the orphan road's refused arm replays nothing); `not-file` is the
# non-regular answer, False or None with NOTHING OPENED (through the fourth addendum a socket of another uid was
# answered absent on the orphan and served roads with no row: open(2)'s ENXIO never reached the owner fstat).
SHAPE_TABLE = (
    # kind               owner      exists      read
    ("absent",           None,      "absent",   "absent"),
    ("regular",          "ours",    "ours",     "ours"),
    ("regular",          "foreign", "foreign",  "foreign"),
    ("symlink-to-file",  "ours",    "link",     "link"),
    ("symlink-to-file",  "foreign", "foreign",  "foreign"),
    ("symlink-dangling", "ours",    "link",     "link"),
    ("symlink-dangling", "foreign", "foreign",  "foreign"),
    ("directory",        "ours",    "not-file", "not-file"),
    ("directory",        "foreign", "foreign",  "foreign"),
    ("fifo",             "ours",    "not-file", "not-file"),
    ("fifo",             "foreign", "foreign",  "foreign"),
    ("socket",           "ours",    "not-file", "not-file"),
    ("socket",           "foreign", "foreign",  "foreign"),
)


def plant_shape(sdir, name, kind, content, elsewhere):
    """The entry of `kind` at `sdir / name` (`content` for a regular file; `elsewhere` a directory outside sdir for a
    link's target). Nothing for `absent`."""
    p = Path(sdir) / name
    if kind == "regular":
        p.write_text(content)
    elif kind == "symlink-to-file":
        (Path(elsewhere) / name).write_text(content)
        p.symlink_to(Path(elsewhere) / name)
    elif kind == "symlink-dangling":
        p.symlink_to(Path(elsewhere) / "nowhere" / name)
    elif kind == "directory":
        p.mkdir()
    elif kind == "fifo":
        os.mkfifo(p)
    elif kind == "socket":
        bind_unix_socket(p)
    else:
        assert kind == "absent", kind


@contextlib.contextmanager
def path_ops(*targets):
    """Every PATH-form syscall on one of `targets`, counted: os.stat, os.lstat, os.open, os.scandir and os.listdir called
    with a str or Path (no descriptor, no dir_fd) naming one of them, as (function, path) pairs on the yielded list. The
    recorder the #814 verifiers used against the readers, here for the journal reads and the write opens (the fork PR
    that follows #814): a cell plants an object and asserts it was never stat'd, opened or listed BY PATH, its directory
    included, so a read moved back onto a path (a glob over the directory, an open by the path it yields) reds the cell
    and not only the census. A name under a descriptor and a descriptor are not counted: those are the roads. Construct
    foreign_uid BEFORE entering this (its keying lstat is the test's own, not the code's) and enter it inside, so its
    stat stubs wrap these."""
    names = {os.fspath(t) for t in targets}
    calls = []
    real = {n: getattr(os, n) for n in ("stat", "lstat", "open", "scandir", "listdir")}

    def wrap(n):
        fn = real[n]

        def w(*a, **k):
            target = a[0] if a else k.get("path")
            if target is not None and not isinstance(target, int) and k.get("dir_fd") is None and os.fspath(target) in names:
                calls.append((n, os.fspath(target)))
            return fn(*a, **k)
        return w
    patches = [mock.patch.object(os, n, wrap(n)) for n in real]
    for p in patches:
        p.start()
    try:
        yield calls
    finally:
        for p in reversed(patches):
            p.stop()


def name_opens(name):
    """os.open calls of `name` under a dir_fd, counted (the open the readers and the write opener make of a regular
    file of ours, and of nothing else): a context manager yielding the list."""
    return _name_opens(name)


@contextlib.contextmanager
def _name_opens(name):
    calls, real_open = [], os.open

    def spy(path, *a, **k):
        if not isinstance(path, int) and k.get("dir_fd") is not None and os.fspath(path) == name:
            calls.append(os.fspath(path))
        return real_open(path, *a, **k)
    with mock.patch.object(os, "open", spy):
        yield calls


def write_segment(path, n, first=0, **tag):
    """A journal segment of `n` records at `path`, numbered from `first` (`n` in each record is its offset), assistant
    and result records alternating, `tag` folded into each (a `peer=True` marks a segment a peer wrote)."""
    with open(path, "w") as f:
        for i in range(first, first + n):
            f.write(json.dumps(dict({"type": "assistant" if i % 2 == 0 else "result", "n": i}, **tag)) + "\n")


class Settings(unittest.TestCase):
    def test_hosts_default_on_and_the_file_is_the_toggle(self):
        """T348 (the user 2026-09-11): hosts are on for everyone on this version; the file turns them off per machine."""
        d = tempfile.mkdtemp()
        self.assertTrue(ht.session_hosts_on(d), "a machine with no file is on")
        for word in ("off", "0", "false", "no", " Off\n", "OFF"):
            Path(d, "session-hosts").write_text(word)
            self.assertFalse(ht.session_hosts_on(d), "the toggle: a file saying %r is off" % word)
        for word in ("on", "1", "true", "yes", "On\n"):
            Path(d, "session-hosts").write_text(word)
            self.assertTrue(ht.session_hosts_on(d), "a file saying %r stays on" % word)
        for blank in ("", "  \n\t"):
            Path(d, "session-hosts").write_text(blank)
            self.assertTrue(ht.session_hosts_on(d), "an empty file, or one holding only whitespace, is the default: on")
        Path(d, "session-hosts").write_text("maybe")
        self.assertFalse(ht.session_hosts_on(d), "a word that is not one of the on words is off, as before")
        self.assertEqual(ht.session_hosts_read(d), (False, "maybe"), "one read hands the branch its verdict and the log the value")
        self.assertEqual(ht.session_hosts_read(tempfile.mkdtemp()), (True, ""), "…and (on, nothing) for a machine with no file")
        src = inspect.getsource(ht.session_hosts_read)
        self.assertIn("(True if not value else value.lower() in SESSION_HOSTS_ON_WORDS), value", src, "the default is on: no file, or an empty one")
        self.assertEqual(ht.SESSION_HOSTS_ON_WORDS, ("on", "1", "true", "yes"))

    def test_the_default_is_stated_where_the_reader_and_the_docs_speak_of_it(self):
        """Every place that states the default says on (T348): the reader's comment, the backend's log line for the
        off branch, and the reference's paragraph on session hosts."""
        # the pins compare whitespace-FLATTENED text (comment continuations joined, line breaks folded), so a re-wrap
        # or a re-aligned comment column leaves them standing; only the statements themselves are held
        flat = lambda s: " ".join(re.sub(r"\n\s*#", "", s).split())
        src = flat(open(os.path.join(ROOT, "kernel", "host_transport.py")).read())
        self.assertIn("leaves them on (on by default since T348", src, "the setting's comment names the default and its origin")
        bsrc = open(os.path.join(ROOT, "kernel", "sdk_backend.py")).read()
        self.assertIn("the session-hosts file reads %r, not an on word; running the CLI as a kernel child", bsrc,
                      "the off branch names what the file holds: any content that is not an on word, not only off")
        self.assertIn("hosts_on, hosts_value = _ht().session_hosts_read(self.state_dir)", bsrc,
                      "ONE read for the branch and its log: a flip between two reads cannot log a value the branch did not decide on")
        self.assertIn('if state == "none" and not hosts_on:', bsrc)
        self.assertIn("% (sess.name, hosts_value))", bsrc, "the log names the value the branch read")
        self.assertNotIn("session_hosts_value(", bsrc, "no second read of the file on that road")
        self.assertNotIn("session-hosts is off;", bsrc, "the old line, which read as the default, is gone")
        doc = open(os.path.join(ROOT, "docs", "reference.md")).read()
        i = doc.index("A session can outlive the kernel that started it.")
        para = flat(doc[i:i + 1200])
        self.assertIn("By default, on every machine on this version, a new session's CLI runs under a small per-session host process", para)
        self.assertIn("Write `off` to it to run a machine's sessions as plain kernel children again", para)
        self.assertIn("`on`, `1`, `true` and `yes` read as on; an empty file, or one holding only whitespace, is the default, on; any other content reads as off", para,
                      "the accepted words, the empty file and the stray word, all three stated")
        self.assertIn("becomes hosted at its next respawn, whatever prompts it", para, "the rollout: a respawn of any kind")
        self.assertNotIn("off by default", para, "the reference no longer says off by default")
        self.assertNotIn("the devbox opts in first", para, "the rollout wording went with the opt-in")

    def test_the_runners_floored_state_root_reads_hosts_off(self):
        """The belt (T348): tests/conftest.py writes `off` into the state root it floors for the run and re-asserts it per
        test, so no test spawns a real host by omission under the new default. Skipped outside that runner."""
        root = os.path.join(os.environ.get("XDG_STATE_HOME", ""), "romp")
        marker = os.path.join(root, "session-hosts")
        if not os.path.exists(marker):
            self.skipTest("the runner's floor (tests/conftest.py) is not in play")
        self.assertEqual(Path(marker).read_text().strip(), "off")
        self.assertEqual(ht.session_hosts_read(root), (False, "off"), "a fresh floored root reads hosts off")
        # The other half on a root of this test's own, not by removing the floored file (until 2026-09-21 this unlinked it and
        # relied on the per-test re-floor): a removal reads as on, so tests/test_tempdir_hygiene.py's ledger counts it as a
        # hosts-on turn in the floored root, whose shape (romp-tests-state-XXXXXXXX/romp) is no mkdtemp the reader can follow.
        self.assertTrue(ht.session_hosts_on(tempfile.mkdtemp()), "…and a bare root is on, which is exactly what the belt prevents")

    def test_the_grace_default_and_its_file(self):
        d = tempfile.mkdtemp()
        self.assertEqual(ht.session_host_grace_s(d), sh.UNATTACHED_GRACE_DEFAULT_S)
        Path(d, "session-host-grace").write_text("120")
        self.assertEqual(ht.session_host_grace_s(d), 120.0)
        Path(d, "session-host-grace").write_text("junk")
        self.assertEqual(ht.session_host_grace_s(d), sh.UNATTACHED_GRACE_DEFAULT_S, "junk falls back, loudly enough by being the default")


class SpawnSpec(unittest.TestCase):
    def test_the_spec_carries_the_plain_fields_and_the_permission_tool_and_never_callables(self):
        opts = types.SimpleNamespace(cli_path="/x/romp-cli-scope", cwd=Path("/tmp/proj"), env={"ROMP_SID": SID, "ROMP_CLI_REAL": "/x/claude"},
                                     permission_mode="default", resume=SID, extra_args={"resume-session-at": "u1"},
                                     mcp_servers="/x/postal.json", system_prompt={"type": "preset", "preset": "claude_code", "append": "hi"},
                                     model="m", effort="high", include_partial_messages=False, enable_file_checkpointing=True,
                                     max_buffer_size=100, can_use_tool=lambda *a: None, hooks={"Stop": []}, stderr=lambda l: None,
                                     permission_prompt_tool_name=None, session_id=None)
        spec = ht.spawn_spec(opts, SID, "web", "/state", "abc12345", 900)
        self.assertEqual(spec["permission_prompt_tool_name"], "stdio", "the callback's presence becomes the flag")
        self.assertEqual((spec["cwd"], spec["resume"], spec["extra_args"], spec["sid"], spec["version"]),
                         ("/tmp/proj", SID, {"resume-session-at": "u1"}, SID, "abc12345"))
        self.assertNotIn("hooks", spec); self.assertNotIn("stderr", spec); self.assertNotIn("can_use_tool", spec)
        self.assertEqual(spec["hook_timeout_s"], sh.HOOK_TIMEOUT_S)
        d = tempfile.mkdtemp()
        p = ht.write_spawn_spec(d, SID, spec)
        self.assertEqual(oct(os.stat(p).st_mode & 0o777), "0o600")
        self.assertEqual(oct(os.stat(p.parent).st_mode & 0o777), "0o700")
        self.assertEqual(json.loads(p.read_text())["env"]["ROMP_SID"], SID)

    def test_hosts_is_owner_only_by_code_and_a_loose_one_is_tightened(self):
        """The guard on the host's socket temp name is the mode of the directory it is bound in, `hosts/`, so that mode
        is set by code, not by the umask of whichever process created it (the pre-round of the socket-mode fix,
        2026-09-19). This is the kernel's road, the one that creates `hosts/` on a fresh state root: write_spawn_spec
        used to mkdir `hosts/<sid>/` with parents=True and leave `hosts/` itself at the umask's mode (0777 under the
        000 umask this test runs under). An existing loose `hosts/` (every install before the fix made one at the
        umask's mode) is tightened on the next spawn, since it is ours."""
        self.addCleanup(os.umask, os.umask(0o000))      # permissive on purpose: whatever mode results is the code's doing
        spec = {"sid": SID, "name": "web", "version": "abc12345", "state_dir": "/state", "protocol": 1}
        fresh = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, fresh, True)
        p = ht.write_spawn_spec(fresh, SID, spec)
        hosts = Path(fresh) / "hosts"
        self.assertEqual(stat.S_IMODE(os.stat(hosts).st_mode), 0o700, "hosts/ is 0700 by code under a 000 umask")
        self.assertEqual(stat.S_IMODE(os.stat(p.parent).st_mode), 0o700, "and hosts/<sid>/ as before")
        self.assertEqual(stat.S_IMODE(os.stat(p).st_mode), 0o600)
        loose = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, loose, True)
        (Path(loose) / "hosts").mkdir()
        os.chmod(Path(loose) / "hosts", 0o755)
        self.assertEqual(stat.S_IMODE(os.stat(Path(loose) / "hosts").st_mode), 0o755, "planted loose, an old install's shape")
        ht.write_spawn_spec(loose, SID, spec)
        self.assertEqual(stat.S_IMODE(os.stat(Path(loose) / "hosts").st_mode), 0o700, "tightened by the next spawn's write")
        self.assertEqual(sh.hosts_dir(loose), Path(loose) / "hosts", "the helper both creators call, idempotent")
        self.assertEqual(stat.S_IMODE(os.stat(Path(loose) / "hosts").st_mode), 0o700)

    def test_a_symlink_at_hosts_or_a_tighten_that_does_not_take_fails_the_spawn(self):
        """hosts_dir takes the judge scratch precedent whole (the socket-mode fix's round 1, 2026-09-19: the first cut
        stat'd through a symlink and never read the mode back after its chmod). The kernel's road: a symlink planted at
        hosts/ fails write_spawn_spec with OSError before any spec is written, and the link's target is not chmod'd
        through it; a chmod that does not take (a no-op os.chmod over a loose hosts/) fails it too instead of returning
        with the directory still loose."""
        self.addCleanup(os.umask, os.umask(0o000))
        spec = {"sid": SID, "name": "web", "version": "abc12345", "state_dir": "/state", "protocol": 1}
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root, True)
        target = Path(root) / "elsewhere"
        target.mkdir(mode=0o755)
        (Path(root) / "hosts").symlink_to(target)
        with self.assertRaises(OSError) as cm:
            ht.write_spawn_spec(root, SID, spec)
        self.assertIn("not a directory", str(cm.exception))
        self.assertTrue(str(cm.exception).startswith("hosts directory "), str(cm.exception))   # the launch error names WHICH directory
        #                                                                                    (the mutation pass of round 2, 2026-09-19)
        self.assertEqual(sorted(p.name for p in target.iterdir()), [], "no spec written through the link")
        self.assertEqual(stat.S_IMODE(os.stat(target).st_mode), 0o755, "the target's mode untouched")
        loose = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, loose, True)
        (Path(loose) / "hosts").mkdir(mode=0o755)
        with mock.patch.object(os, "chmod", lambda *a, **k: None):
            with self.assertRaises(OSError) as cm:
                ht.write_spawn_spec(loose, SID, spec)
        self.assertIn("stays group/world-accessible", str(cm.exception))
        self.assertTrue(str(cm.exception).startswith("hosts directory "), str(cm.exception))
        self.assertEqual(stat.S_IMODE(os.lstat(Path(loose) / "hosts").st_mode), 0o755)
        self.assertFalse((Path(loose) / "hosts" / SID).exists(), "the spawn stopped at the directory")

    def test_a_symlink_at_the_session_directory_fails_the_spawn_and_the_directory_is_born_0700_by_its_mkdir(self):
        """The sibling one line below hosts/ (the socket-mode fix's round 2, 2026-09-19): round 1 put lstat, the
        foreign-owner refusal and the chmod read-back on hosts/ and left hosts/<sid>/ on a bare mkdir and a chmod never
        read back, so a symlink planted there was followed and the spec written through it. Now the same helper
        (sh.owner_only_dir) makes both. The kernel's road: a symlink at hosts/<sid>/ fails write_spawn_spec with OSError
        naming the host directory, nothing is written through the link and the target's mode is untouched; a loose
        hosts/<sid>/ of ours is tightened and read back, and a tighten that does not take fails the spawn with no spec
        written. And the creation mode is the mkdir's own, read at the FIRST lstat after it (0700 under a 000 umask, no
        chmod made), since every earlier assertion read the final mode, which the chmod a line later supplied whatever
        the mkdir did; on a second fresh root with os.chmod a no-op the directory is still 0700 and the spec lands."""
        self.addCleanup(os.umask, os.umask(0o000))
        spec = {"sid": SID, "name": "web", "version": "abc12345", "state_dir": "/state", "protocol": 1}
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root, True)
        sh.hosts_dir(root)
        target = Path(root) / "elsewhere"
        target.mkdir(mode=0o755)
        sdir = Path(root) / "hosts" / SID
        sdir.symlink_to(target)
        with self.assertRaises(OSError) as cm:
            ht.write_spawn_spec(root, SID, spec)
        self.assertTrue(str(cm.exception).startswith("host directory "), str(cm.exception))
        self.assertIn("not a directory", str(cm.exception))
        self.assertEqual(sorted(p.name for p in target.iterdir()), [], "no spec written through the link")
        self.assertEqual(stat.S_IMODE(os.stat(target).st_mode), 0o755, "the target's mode untouched")
        self.assertTrue(sdir.is_symlink(), "the link is left, not replaced")
        fresh = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, fresh, True)
        sdir = Path(fresh) / "hosts" / SID
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
            p = ht.write_spawn_spec(fresh, SID, spec)
        self.assertEqual(reads, [0o700], "hosts/<sid>/ is 0700 at the first read after its mkdir: the mkdir's own mode")
        self.assertEqual([c for c in chmods if c[0] == sdir], [], "no chmod on a directory born owner-only")
        self.assertEqual(stat.S_IMODE(os.stat(p).st_mode), 0o600)
        noop = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, noop, True)
        with mock.patch.object(os, "chmod", lambda *a, **k: None):
            p = ht.write_spawn_spec(noop, SID, spec)
        self.assertEqual(stat.S_IMODE(os.lstat(p.parent).st_mode), 0o700, "0700 with no chmod to lean on, on either directory")
        self.assertEqual(stat.S_IMODE(os.lstat(p.parent.parent).st_mode), 0o700)
        self.assertTrue(p.exists())
        loose = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, loose, True)
        sh.hosts_dir(loose)
        (Path(loose) / "hosts" / SID).mkdir(mode=0o755)
        with mock.patch.object(os, "chmod", lambda *a, **k: None):
            with self.assertRaises(OSError) as cm:
                ht.write_spawn_spec(loose, SID, spec)
        self.assertIn("stays group/world-accessible", str(cm.exception))
        self.assertTrue(str(cm.exception).startswith("host directory "), str(cm.exception))
        self.assertFalse((Path(loose) / "hosts" / SID / "spawn.json").exists(), "the spawn stopped at the directory")
        p = ht.write_spawn_spec(loose, SID, spec)
        self.assertEqual(stat.S_IMODE(os.lstat(p.parent).st_mode), 0o700, "a loose one of ours is tightened, read back, and the spec lands")

    def test_the_reference_states_the_sockets_contract_and_the_directory_refusal(self):
        """The docs paragraph that states the user-facing contract of the socket-mode fix, pinned sentence by sentence
        (the fix's round 2, 2026-09-19: the existing flattened-paragraph pin above stops short of these sentences, and a
        set-aside called a docs paragraph untestable when the same test file pins prose from the same paragraph by exact
        substring). The paragraph is sliced from its socket anchor to the next blank line, so a re-wrap leaves the pin
        standing and a deleted sentence fails it. A doc pin guards the doc against drifting from a contract the code
        still keeps; the code itself is pinned by tests/test_session_host.py and the SpawnSpec cases above."""
        flat = lambda s: " ".join(s.split())
        doc = open(os.path.join(ROOT, "docs", "reference.md")).read()
        i = doc.index("serves one Unix socket (`hosts/<sid8>.sock`")
        para = flat(doc[i:doc.index("\n\n", i)])
        self.assertIn("mode 0600 from the moment the path exists", para)
        self.assertIn("a published path longer than the socket path budget, 107 bytes on Linux, is refused before anything is bound and the host exits", para)
        self.assertIn("`hosts/` itself is made 0700 when the kernel writes a host's spawn specification and when a host starts, "
                      "before it spawns its CLI or binds its socket", para,
                      "the host's road runs at its start, ahead of the CLI, since round 3 of the fix (the reorder ruling, 2026-09-19)")
        self.assertIn("the host exits, having started no CLI and written no lease", para, "and a refusal there starts nothing")
        self.assertIn("after the lease only one check of `hosts/`, the bind, the tightening and the rename run", para,
                      "the interval the lease readers race, stated (the check is round 4's lstat at the bind, 2026-09-20)")
        self.assertIn("each `hosts/<sid>/` when the specification is written and when the host opens its journal", para,
                      "the sibling directory is named with its two creators")
        self.assertIn("one that is a symlink, that belongs to another user, or that stays loose after the tightening is refused on every one of them.", para,
                      "the refusal is stated where the tightening is: a symlinked hosts/ worked before and hard-fails every spawn now")
        # what the operator SEES is stated per road since round 3 (2026-09-19, correctness-6): through round 2 the paragraph
        # promised a launch error naming the directory on all four roads, and on the host's two (hosts/ or hosts/<sid>/
        # re-pointed after the spec is written) the launch error names only the exit; this pin replaces the one that
        # held the overstatement
        self.assertIn("When the kernel meets it, writing the specification, the spawn fails with a launch error naming the directory", para,
                      "the kernel's roads: the error names the directory")
        self.assertIn("when the host meets it first, the host exits before serving its socket and the launch error names its exit code and where the reason is: "
                      "`hosts/<sid>/host.log` when the host wrote a row (its `socket-bind-failed` row names the step), `host.stderr` beside the specification "
                      "when it refused before its first row", para,
                      "the host's roads: the exit code, and the file that exists for each refusal class (the constructor's leaves no host.log row)")
        self.assertNotIn("refused on every one of them: the spawn fails with a launch error naming the directory", para,
                         "the overstatement is gone: the host's roads never named the directory in the launch error")
        self.assertIn("point the state root there, `ROMP_STATE_DIR` or `XDG_STATE_HOME`", para, "and the operator's remedy beside it")

    def test_a_pre_existing_looser_spawn_json_is_tightened_before_the_overlay_lands_in_it(self):
        # Until 2026-09-18 the writer opened spawn.json O_CREAT|O_TRUNC at 0600 and chmod'd it AFTER the write: a
        # fresh file was born 0600, but a pre-existing looser one kept its mode through the truncating open, took
        # the environment overlay at that mode, and tightened only afterwards. The mode now goes onto the descriptor
        # before the write (PR 789, review round 1: the same write-then-tighten window the reg and the parked-ops
        # mirror lost). The FILE's chmod is interposed and NOT performed, so the old order leaves it at 0644 and the
        # case reads the descriptor's mode alone; the directory's 0700 chmod stays a real one.
        d = tempfile.mkdtemp()
        p = ht.host_dir(d, SID) / "spawn.json"
        p.parent.mkdir(parents=True)
        p.write_text("{}")
        os.chmod(p, 0o644)
        fchmods, chmods = [], []
        real_fchmod, real_chmod = os.fchmod, os.chmod

        def fchmod_probe(fd, mode):
            fchmods.append((mode, os.fstat(fd).st_size))         # 0 bytes at that moment: before the first write
            return real_fchmod(fd, mode)

        def chmod_probe(path, mode, *a, **k):
            if Path(path) == p:
                chmods.append(mode)                              # the file's chmod: recorded, not performed
                return None
            return real_chmod(path, mode, *a, **k)
        with mock.patch.object(os, "fchmod", fchmod_probe), mock.patch.object(os, "chmod", chmod_probe):
            out = ht.write_spawn_spec(d, SID, {"env": {"FEATURE_FLAG": "1"}, "sid": SID})
        self.assertEqual(out, p)
        self.assertEqual(os.stat(p).st_mode & 0o777, 0o600, "tightened before the write, with no file chmod performed")
        self.assertEqual(fchmods, [(0o600, 0)], "one fchmod on the descriptor while the file is still empty")
        self.assertEqual(chmods, [], "no chmod on the file after the write")
        self.assertEqual(os.stat(p.parent).st_mode & 0o777, 0o700, "the directory's chmod is unchanged")
        self.assertEqual(json.loads(p.read_text())["env"]["FEATURE_FLAG"], "1", "and the overlay landed")

    def test_a_raising_fchmod_closes_the_descriptor(self):
        # Review round 2 of PR 789 (2026-09-19): round 1 put the fchmod between os.open and os.fdopen with nothing closing
        # the descriptor when it raised; os.fdopen was the only close. The error propagates (this writer has no swallow
        # road), the descriptor os.open returned reaches os.close (a real close, recorded), and the directory's chmod
        # stays real.
        import errno
        d = tempfile.mkdtemp()
        opened, closed = [], []
        real_open, real_close = os.open, os.close

        def open_probe(*a, **k):
            fd = real_open(*a, **k)
            opened.append(fd)
            return fd

        def fchmod_refused(fd, mode):
            raise PermissionError(errno.EPERM, "fchmod refused (interposed)")

        def close_probe(fd):
            closed.append(fd)
            return real_close(fd)
        with mock.patch.object(os, "open", open_probe), mock.patch.object(os, "fchmod", fchmod_refused), \
                mock.patch.object(os, "close", close_probe), self.assertRaises(PermissionError):
            ht.write_spawn_spec(d, SID, {"env": {"FEATURE_FLAG": "1"}, "sid": SID})
        # three descriptors since round 4 of the socket-mode fix (2026-09-20): the descent's two directory descriptors
        # (hosts/, then hosts/<sid>/ relative to it) and spawn.json's, opened relative to the second; all three closed
        self.assertEqual(len(opened), 3, "hosts/, hosts/<sid>/ and spawn.json's descriptors: %r" % (opened,))
        self.assertEqual(sorted(closed), sorted(opened), "every descriptor closed on the failure road")
        self.assertEqual(os.stat(ht.host_dir(d, SID)).st_mode & 0o777, 0o700, "the directory's chmod ran")
        # host_stderr_open's fchmod, the same shape (tests-3, round 6 of the review, 2026-09-20: kernel-1's fchmod landed
        # with a close-and-reraise nothing held; with it removed, one descriptor leaked per refused launch). The count is
        # read after the open_host_dirs context has exited, since its two directory descriptors close at that exit.
        sh.hosts_dir(d)
        ht.host_dir(d, SID).mkdir(exist_ok=True)
        opened.clear(); closed.clear()
        with mock.patch.object(os, "open", open_probe), mock.patch.object(os, "fchmod", fchmod_refused), \
                mock.patch.object(os, "close", close_probe), self.assertRaises(PermissionError):
            with ht.open_host_dirs(d, SID) as dirs:
                ht.host_stderr_open(dirs)
        self.assertEqual(len(opened), 3, "hosts/, hosts/<sid>/ and host.stderr's descriptors: %r" % (opened,))
        self.assertEqual(sorted(closed), sorted(opened), "every descriptor closed on host_stderr_open's failure road")

    def test_the_spec_is_opened_through_descriptors_so_a_link_swapped_in_after_the_directory_checks_is_refused(self):
        """The round's high, on the kernel's spec write (round 4 of the socket-mode fix, 2026-09-20): through round 3
        write_spawn_spec checked hosts/ and hosts/<sid>/ by path and then opened spawn.json by PATH, so a hosts/ or
        hosts/<sid>/ swapped for a symlink between the helper's read-back and the open had the specification, the
        launch's environment overlay in it, written into the link's target (the TOCTOU residual owner_only_dir's
        docstring stated). Now the file is opened by name relative to a descriptor on hosts/<sid>/ reached through
        O_DIRECTORY|O_NOFOLLOW opens of each component (open_host_dirs): a link at either fails its open. Interposed on
        sh.owner_only_dir, a module attribute both helpers reach (so the plant is seen on every interpreter, 3.10
        included): after the session directory's call returns, hosts/ (arm 1) or hosts/<sid>/ (arm 2) is renamed aside
        and a symlink to a directory of a peer's put in its place, holding an empty <sid>/ where the spec would land.
        write_spawn_spec raises HostDirRefused naming the link as a symlink and its path, and the peer's directory
        receives nothing (its listing, empty). Red on the head before the fix: the spec landed in the peer's directory
        (['spawn.json'] listed there)."""
        self.addCleanup(os.umask, os.umask(0o022))
        spec = {"sid": SID, "name": "web", "version": "abc12345", "state_dir": "/state", "protocol": 1, "env": {"FEATURE_FLAG": "1"}}
        real = sh.owner_only_dir
        for arm, noun in (("hosts", "hosts directory"), ("session-dir", "host directory")):
            with self.subTest(arm=arm):
                root = tempfile.mkdtemp()
                self.addCleanup(shutil.rmtree, root, True)
                peer = Path(root) / "peer"
                (peer / SID).mkdir(parents=True, mode=0o755)
                hosts, sdir = Path(root) / "hosts", Path(root) / "hosts" / SID
                link = hosts if arm == "hosts" else sdir
                target = peer if arm == "hosts" else peer / SID

                def swap_after(path, what="directory", parents=False, link=link, target=target):
                    d = real(path, what, parents)
                    if what == "host directory":                 # the last check before the open: the swap lands here
                        os.rename(link, Path(root) / "moved")
                        link.symlink_to(target)
                    return d
                with mock.patch.object(sh, "owner_only_dir", swap_after), self.assertRaises(ht.HostDirRefused) as cm:
                    ht.write_spawn_spec(root, SID, spec)
                msg = str(cm.exception)
                self.assertTrue(msg.startswith(noun + " "), msg)
                self.assertIn("is a symlink, not a directory", msg)
                self.assertIn(os.fspath(link), msg)
                self.assertTrue(link.is_symlink(), "the link is left, not replaced")
                self.assertEqual(sorted(p.name for p in (peer / SID).iterdir()), [], "the peer's directory received nothing")
                self.assertEqual(sorted(str(p.relative_to(peer)) for p in peer.rglob("*")), [SID], "nothing anywhere under it")
                moved = Path(root) / "moved"
                self.assertFalse((moved / (SID if arm == "hosts" else "") / "spawn.json").exists(), "and no spec was written anywhere: the open was refused")

    def test_the_descents_foreign_uid_arm_refuses_a_directory_renamed_into_place_at_hosts_and_at_the_session_directory(self):
        """open_host_dirs' foreign-uid arm, driven with a stub keyed on the object (tests-1, round 5 of the review,
        2026-09-20: the descent's two fstat refusals, this one and the mode arm below, were held by no case, and the PR
        body had waived them as redundant with the road's O_NOFOLLOW open, which is false for this arm: a foreign
        DIRECTORY renamed into place is not a link, and O_NOFOLLOW admits it). Real directories of ours at hosts/ and
        hosts/<sid>/; os.fstat answers st_uid + 1 for the descriptor whose (st_dev, st_ino) is the planted component's,
        read by the real lstat before the patch, and truthfully for every other descriptor (the sibling component's
        among them, so the refusal is the planted component's own). write_spawn_spec's descent raises HostDirRefused
        carrying `belongs to uid` and the component's path, and no spawn.json is written anywhere under the root. Red
        with the uid arm deleted from _open_dir_nofollow: the descent admits the directory and the spec lands in it."""
        spec = {"sid": SID, "name": "web", "version": "abc12345", "state_dir": "/state", "protocol": 1, "env": {"FEATURE_FLAG": "1"}}
        real_fstat = os.fstat

        def foreign(st):
            fields = list(st)
            fields[4] = st.st_uid + 1                   # st_uid: someone else's directory at the component
            return os.stat_result(fields)
        for arm, noun in (("hosts", "hosts directory"), ("session-dir", "host directory")):
            with self.subTest(arm=arm):
                root = tempfile.mkdtemp()
                self.addCleanup(shutil.rmtree, root, True)
                sh.hosts_dir(root)
                sdir = ht.host_dir(root, SID)
                sdir.mkdir(mode=0o700)
                planted = Path(root) / "hosts" if arm == "hosts" else sdir
                st = os.lstat(planted)
                ident = (st.st_dev, st.st_ino)

                def fstat(fd, ident=ident):
                    st = real_fstat(fd)
                    if isinstance(fd, int) and stat.S_ISDIR(st.st_mode) and (st.st_dev, st.st_ino) == ident:
                        return foreign(st)
                    return st
                with mock.patch.object(os, "fstat", fstat):
                    with self.assertRaises(OSError) as cm:
                        ht.write_spawn_spec(root, SID, spec)
                self.assertIsInstance(cm.exception, ht.HostDirRefused, repr(cm.exception))
                msg = str(cm.exception)
                self.assertTrue(msg.startswith(noun + " "), msg)
                self.assertIn("belongs to uid %d, not to us (uid %d)" % (os.geteuid() + 1, os.geteuid()), msg)
                self.assertIn(os.fspath(planted), msg)
                self.assertEqual([str(q) for q in Path(root).rglob("spawn.json")], [], "no spec written anywhere: the descent refused")

    def test_the_descents_mode_arm_refuses_a_loose_directory_renamed_into_place_after_the_helpers_tighten(self):
        """open_host_dirs' group/world arm, driven with no stub (tests-1, round 5 of the review, 2026-09-20; the PR body
        had said this arm too needed a stub keyed on the object, which is not so): under the live host's umask, 002,
        the component is renamed aside after sh.owner_only_dir's last check returns and a real directory of ours at 0775
        made at its name (with a 0700 <sid>/ inside it for the hosts/ arm, so nothing but the mode stands between the
        descent and the spec). The descent's fstat reads the loose mode and refuses with `is group/world-accessible
        (mode 0775)` and the component's path; nothing is written under the loose directory. Red with the mode arm
        deleted: the descent admits the directory and spawn.json lands under it."""
        self.addCleanup(os.umask, os.umask(0o002))
        spec = {"sid": SID, "name": "web", "version": "abc12345", "state_dir": "/state", "protocol": 1, "env": {"FEATURE_FLAG": "1"}}
        real = sh.owner_only_dir
        for arm, noun in (("hosts", "hosts directory"), ("session-dir", "host directory")):
            with self.subTest(arm=arm):
                root = tempfile.mkdtemp()
                self.addCleanup(shutil.rmtree, root, True)
                hosts, sdir = Path(root) / "hosts", Path(root) / "hosts" / SID
                loose = hosts if arm == "hosts" else sdir

                def swap_in_loose(path, what="directory", parents=False, loose=loose, arm=arm):
                    d = real(path, what, parents)
                    if what == "host directory":             # the last check before the descent: the swap lands here
                        os.rename(loose, Path(root) / "moved")
                        os.mkdir(loose, 0o775)                # ours and loose; under 002 the mode lands as 0775
                        if arm == "hosts":
                            os.mkdir(loose / SID, 0o700)
                    return d
                with mock.patch.object(sh, "owner_only_dir", swap_in_loose):
                    with self.assertRaises(OSError) as cm:
                        ht.write_spawn_spec(root, SID, spec)
                self.assertIsInstance(cm.exception, ht.HostDirRefused, repr(cm.exception))
                msg = str(cm.exception)
                self.assertTrue(msg.startswith(noun + " "), msg)
                self.assertIn("is group/world-accessible (mode 0775)", msg)
                self.assertIn(os.fspath(loose), msg)
                self.assertEqual(stat.S_IMODE(os.lstat(loose).st_mode), 0o775, "the loose directory as planted, read back")
                self.assertEqual([str(q) for q in loose.rglob("*") if q.is_file()], [], "nothing written under the loose directory")

    def test_a_filesystem_failure_at_a_directory_helper_is_the_oserror_it_is_and_a_decided_refusal_is_the_class(self):
        """The wrap around write_spawn_spec's two path-taking helpers keys on the refusal, not on OSError (regression-1
        and kernel-4, round 5 of the review, 2026-09-20: round 4's wrap folded every OSError of the helpers into
        HostDirRefused, so a full disk at the mkdir reached the operator as host.directory-refused with a remedy that
        was false for it, and the errno left the class). Interposed on sh.owner_only_dir, the module attribute both
        helpers reach: a full disk (ENOSPC), a read-only filesystem (EROFS) and an unwritable target (EACCES, which a
        peer can cause with hosts/ re-pointed to a directory this uid cannot write; the round-6 ruling keeps it on this
        road) at hosts/<sid>/'s mkdir each reach the caller as the OSError raised, errno and text intact, and not as
        HostDirRefused; a refusal the helper decides (a single-argument OSError, errno None) is HostDirRefused, errno
        None. The errnos of the SHAPE class (EEXIST, ENOTDIR, ELOOP, ENOENT) are the class too, pinned by the two cases
        below with real plants and no stub (round 7 of the review, 2026-09-20: round 5's `errno is None` key threw them
        out). Red before the change: the ENOSPC and EROFS arms arrived as HostDirRefused."""
        import errno as _errno
        spec = {"sid": SID, "name": "web", "version": "abc12345", "state_dir": "/state", "protocol": 1, "env": {"FEATURE_FLAG": "1"}}
        real = sh.owner_only_dir
        for arm, code in (("ENOSPC", _errno.ENOSPC), ("EROFS", _errno.EROFS), ("EACCES", _errno.EACCES)):
            with self.subTest(arm=arm):
                root = tempfile.mkdtemp()
                self.addCleanup(shutil.rmtree, root, True)

                def fail(path, what="directory", parents=False, code=code):
                    if what == "host directory":
                        raise OSError(code, os.strerror(code), os.fspath(path))
                    return real(path, what, parents)
                with mock.patch.object(sh, "owner_only_dir", fail):
                    with self.assertRaises(OSError) as cm:
                        ht.write_spawn_spec(root, SID, spec)
                self.assertNotIsInstance(cm.exception, ht.HostDirRefused, "a filesystem failure is not a refusal: %r" % (cm.exception,))
                self.assertEqual(cm.exception.errno, code, "the errno rides on the exception")
                self.assertTrue(str(cm.exception).startswith("[Errno %d] " % code), str(cm.exception))
                self.assertFalse((Path(root) / "hosts" / SID / "spawn.json").exists())
        with self.subTest(arm="decided-refusal"):
            root = tempfile.mkdtemp()
            self.addCleanup(shutil.rmtree, root, True)

            def refuse(path, what="directory", parents=False):
                if what == "host directory":
                    raise OSError("%s %s is not a directory" % (what, path))
                return real(path, what, parents)
            with mock.patch.object(sh, "owner_only_dir", refuse):
                with self.assertRaises(OSError) as cm:
                    ht.write_spawn_spec(root, SID, spec)
            self.assertIsInstance(cm.exception, ht.HostDirRefused, repr(cm.exception))
            self.assertIsNone(cm.exception.errno, "the class is built from one text argument, so it carries no errno")

    def test_a_non_directory_at_hosts_or_at_the_session_directory_is_refused_under_the_class_by_the_real_helpers(self):
        """Round 7 of the review (2026-09-20; the round-6 rulings' C, correctness-1, regression-1, kernel-1, extra6-1,
        extra7-1): a regular file, a FIFO, a symlink to a file or a DANGLING symlink standing at hosts/ or at hosts/<sid>/
        when write_spawn_spec runs never reaches owner_only_dir's own lstat, because pathlib's mkdir(exist_ok=True)
        re-raises FileExistsError (17) first; round 5's wrap, keyed on `errno is None`, let that out of the class, so a
        peer's one-syscall plant read "[Errno 17] File exists" with no problem row and no remedy where round 4's head
        filed both. The wrap now keys on the errno set of the shape class (host_transport.HELPER_SHAPE_ERRNOS). Eight
        arms over the REAL helpers, no stub, plus a symlink that names itself standing AT hosts/: each is HostDirRefused,
        errno None, worded as the helpers word a non-directory (`<what> <path> is not a directory`), no spawn.json
        written anywhere, and the plant left standing. The self-link arm exercises EEXIST, not ELOOP (the round-7
        addendum, 2026-09-20, after a verifier found the arm's startswith accepting either wording): os.mkdir on a name
        that is a self-link reports the name taken (17), and pathlib's mkdir(exist_ok=True) then asks is_dir(), whose
        stat meets ELOOP and swallows it (_ignore_error), so the EEXIST re-raises and the wrap words it as a
        non-directory; the arm pins the cause's errno and the exact wording. ELOOP itself is reached by re-pointing
        hosts/ to a self-link BETWEEN the helpers, the `loop` arm of the re-pointed case below. Red at the round-6
        head: FileExistsError, errno 17, not the class, on every arm."""
        spec = {"sid": SID, "name": "web", "version": "abc12345", "state_dir": "/state", "protocol": 1, "env": {"FEATURE_FLAG": "1"}}
        shapes = ("regular file", "fifo", "symlink to a file", "dangling symlink")
        for where in ("hosts", "hosts/<sid>"):
            for shape in shapes:
                with self.subTest(where=where, shape=shape):
                    root = tempfile.mkdtemp()
                    self.addCleanup(shutil.rmtree, root, True)
                    if where == "hosts/<sid>":
                        sh.hosts_dir(root)
                        target, what = ht.host_dir(root, SID), "host directory"
                    else:
                        target, what = Path(root) / "hosts", "hosts directory"
                    peer = Path(root) / "peer"
                    peer.mkdir(mode=0o755)
                    if shape == "regular file":
                        target.write_text("")
                    elif shape == "fifo":
                        os.mkfifo(target)
                    elif shape == "symlink to a file":
                        (peer / "theirs.txt").write_text("the peer's own bytes")
                        target.symlink_to(peer / "theirs.txt")
                    else:
                        target.symlink_to(peer / "nowhere")
                    before = os.lstat(target)
                    with self.assertRaises(OSError) as cm:
                        ht.write_spawn_spec(root, SID, spec)
                    self.assertIsInstance(cm.exception, ht.HostDirRefused, "the shape class, not %r" % (cm.exception,))
                    self.assertIsNone(cm.exception.errno)
                    self.assertEqual(str(cm.exception), "%s %s is not a directory" % (what, target))
                    self.assertEqual(os.lstat(target)[:2], before[:2], "the plant stands as planted")
                    self.assertEqual([str(p) for p in Path(root).rglob("spawn.json")], [], "no spawn.json anywhere under the root")
        with self.subTest(where="hosts", shape="self-link (EEXIST, not ELOOP)"):
            import errno as _errno
            root = tempfile.mkdtemp()
            self.addCleanup(shutil.rmtree, root, True)
            (Path(root) / "hosts").symlink_to(Path(root) / "hosts")
            with self.assertRaises(ht.HostDirRefused) as cm:
                ht.write_spawn_spec(root, SID, spec)
            self.assertIsNone(cm.exception.errno)
            self.assertEqual(str(cm.exception), "hosts directory %s is not a directory" % (Path(root) / "hosts"),
                             "the EEXIST wording, with no loop clause: this arm never reaches ELOOP")
            self.assertIsInstance(cm.exception.__cause__, FileExistsError)
            self.assertEqual(cm.exception.__cause__.errno, _errno.EEXIST, "pathlib re-raised os.mkdir's EEXIST; the loop's ELOOP was is_dir()'s to swallow")
            self.assertTrue((Path(root) / "hosts").is_symlink(), "the self-link stands")

    def test_a_hosts_re_pointed_between_the_helpers_is_refused_for_a_dangling_or_file_target_and_is_the_errno_for_an_unwritable_one(self):
        """The two decisions the round-6 rulings asked for in code (C), driven through the window condition 1 states:
        sh.hosts_dir wrapped to re-point hosts/ after it returns and before sh.owner_only_dir's mkdir. ENOENT (a DANGLING
        link, a peer's one-syscall plant) joins the shape class: the descent's own open already words ENOENT as "does
        not exist", and the peer causes it. ENOTDIR (a link to a regular FILE) joins it, as does a state root that is
        itself a plain file (ENOTDIR at the first helper, which only the operator can cause and which the class's
        remedy, point the state root elsewhere, fits). EACCES (a link to a directory this uid cannot write) stays the
        launch error's OSError with errno 13, by the ruling, though a peer can cause it too. The read-only target
        receives nothing on any arm. ELOOP (the `loop` arm, the round-7 addendum, 2026-09-20): hosts/ re-pointed to a
        link that names ITSELF, so the second helper's os.mkdir of hosts/<sid> fails resolving hosts/ with ELOOP (40)
        and pathlib's is_dir() reads False through the same loop, the one arm in this file that reaches the class by
        ELOOP; the shapes case's self-link AT hosts/ is EEXIST (its docstring says why). And the component named (the
        addendum, after a verifier read `host directory <root> is not a directory` for a dangling-link STATE ROOT):
        helper_shape_refusal names the component the errno's filename is, so a state root that is a dangling symlink
        (the create road: root.exists() False, then parents=True meets the root itself by path and pathlib re-raises
        EEXIST with the root as the filename) reads `state root <root> is not a directory`, the noun hosts_dir's own
        refusals use for it. Red at the round-6 head: FileNotFoundError 2 and NotADirectoryError 20 outside the class;
        the EACCES arm green there and pinned here so the decision cannot move unseen; red at the merged head on the
        loop arm (a bare OSError 40, not the class) and at the round-7 commit on the dangling-root arm (`host
        directory` for the root)."""
        import errno as _errno
        spec = {"sid": SID, "name": "web", "version": "abc12345", "state_dir": "/state", "protocol": 1, "env": {"FEATURE_FLAG": "1"}}
        real_hosts_dir = sh.hosts_dir

        def repoint(target):
            def wrapped(state_dir):
                r = real_hosts_dir(state_dir)
                os.rename(r, str(r) + ".aside")
                os.symlink(target, r)
                return r
            return wrapped
        for arm in ("dangling", "file", "unwritable", "loop"):
            with self.subTest(arm=arm):
                root = tempfile.mkdtemp()
                self.addCleanup(shutil.rmtree, root, True)
                if arm == "dangling":
                    target = Path(root) / "nowhere"
                elif arm == "file":
                    target = Path(root) / "a-file.txt"
                    target.write_text("")
                elif arm == "loop":
                    target = Path(root) / "hosts"           # the link names itself: hosts/ -> hosts/
                else:
                    target = Path(root) / "readonly"
                    target.mkdir(mode=0o500)
                    self.addCleanup(os.chmod, target, 0o700)
                leaf = ht.host_dir(root, SID)
                with mock.patch.object(sh, "hosts_dir", repoint(target)):
                    with self.assertRaises(OSError) as cm:
                        ht.write_spawn_spec(root, SID, spec)
                if arm == "unwritable":
                    self.assertNotIsInstance(cm.exception, ht.HostDirRefused, repr(cm.exception))
                    self.assertEqual(cm.exception.errno, _errno.EACCES)
                    self.assertEqual(sorted(os.listdir(target)), [], "the unwritable target received nothing")
                else:
                    self.assertIsInstance(cm.exception, ht.HostDirRefused, repr(cm.exception))
                    self.assertIsNone(cm.exception.errno)
                    why = {"dangling": "does not exist (a component is missing, or a symlink there dangles)",
                           "file": "is not a directory, or a directory above it is not",
                           "loop": "is not a directory (a symlink loop)"}[arm]
                    self.assertEqual(str(cm.exception), "host directory %s %s" % (leaf, why))
                    if arm == "loop":
                        self.assertEqual(cm.exception.__cause__.errno, _errno.ELOOP, "the cause is the mkdir's ELOOP, the class's one loop road")
                        self.assertEqual(os.readlink(Path(root) / "hosts"), str(target), "the self-link stands")
                self.assertEqual([str(p) for p in Path(root).rglob("spawn.json")], [], "no spawn.json anywhere under the root")
        with self.subTest(arm="plain-file state root"):
            scratch = tempfile.mkdtemp()
            self.addCleanup(shutil.rmtree, scratch, True)
            root = Path(scratch) / "root-is-a-file"
            root.write_text("")
            with self.assertRaises(ht.HostDirRefused) as cm:
                ht.write_spawn_spec(root, SID, spec)
            self.assertIsNone(cm.exception.errno)
            self.assertEqual(str(cm.exception), "hosts directory %s is not a directory, or a directory above it is not" % (root / "hosts"))
        with self.subTest(arm="dangling-link state root"):
            scratch = tempfile.mkdtemp()
            self.addCleanup(shutil.rmtree, scratch, True)
            root = Path(scratch) / "root"
            root.symlink_to(Path(scratch) / "nowhere")
            with self.assertRaises(ht.HostDirRefused) as cm:
                ht.write_spawn_spec(root, SID, spec)
            self.assertIsNone(cm.exception.errno)
            self.assertEqual(str(cm.exception), "state root %s is not a directory" % root,
                             "the component the errno's filename names, in hosts_dir's own noun for it")
            self.assertEqual(cm.exception.__cause__.errno, _errno.EEXIST, "pathlib's parents=True mkdir met the dangling root by path")
            self.assertTrue(root.is_symlink() and not root.exists(), "the dangling link stands, nothing made through it")
            self.assertEqual(sorted(os.listdir(scratch)), ["root"], "nothing made beside it")

    def test_an_unwritable_file_of_ours_at_spawn_json_or_host_stderr_is_the_opens_own_error_with_eacces_and_not_a_refusal(self):
        """tests-2 (round 6 of the review, 2026-09-20): _open_file_nofollow narrows the class to ELOOP alone, every other
        OSError of the open propagating with its errno, and nothing held that narrowing (the ELOOP test mutated to
        `if True` left every module green). Through #814 this pin planted a DIRECTORY at the name and read EISDIR out of
        the open; since the fork PR that follows #814 (2026-09-21) a directory of ours at either name is a refusal
        naming the kind BEFORE any open (the write side's shape question, _open_host_file_for_write; WriteOpens pins that
        cell), so the errno that still reaches the open from a real object is a regular file OF OURS with no write bit
        (0400): the shape question passes it as the file, the open raises PermissionError, errno EACCES, its own text,
        not HostDirRefused, at spawn.json through write_spawn_spec and at host.stderr through open_host_dirs and
        host_stderr_open, and the file's bytes and mode stand. Red with the narrowing widened to every OSError: both
        arms arrive as HostDirRefused. Root ignores the write bit and is skipped."""
        import errno as _errno
        if os.geteuid() == 0:
            self.skipTest("root bypasses the write bit")
        spec = {"sid": SID, "name": "web", "version": "abc12345", "state_dir": "/state", "protocol": 1, "env": {"FEATURE_FLAG": "1"}}
        for name in ("spawn.json", "host.stderr"):
            with self.subTest(file=name):
                root = tempfile.mkdtemp()
                self.addCleanup(shutil.rmtree, root, True)
                sh.hosts_dir(root)
                sdir = ht.host_dir(root, SID)
                sdir.mkdir(mode=0o700)
                (sdir / name).write_text("a previous launch's bytes")
                os.chmod(sdir / name, 0o400)
                with self.assertRaises(OSError) as cm:
                    if name == "spawn.json":
                        ht.write_spawn_spec(root, SID, spec)
                    else:
                        with ht.open_host_dirs(root, SID) as dirs:
                            os.close(ht.host_stderr_open(dirs))
                self.assertNotIsInstance(cm.exception, ht.HostDirRefused, repr(cm.exception))
                self.assertEqual(cm.exception.errno, _errno.EACCES)
                self.assertTrue(str(cm.exception).startswith("[Errno %d] %s" % (_errno.EACCES, os.strerror(_errno.EACCES))), str(cm.exception))
                self.assertNotIn("symlink", str(cm.exception))
                self.assertEqual((sdir / name).read_text(), "a previous launch's bytes", "nothing written, nothing truncated")
                self.assertEqual(stat.S_IMODE(os.lstat(sdir / name).st_mode), 0o400, "the mode untouched: the fchmod runs after an open that never returned")

    def test_a_symlink_at_spawn_json_or_host_stderr_is_refused_under_the_class_naming_the_file_and_the_target_is_untouched(self):
        """kernel-2 (round 5 of the review, 2026-09-20): the descent's two FILE-level O_NOFOLLOW opens raised a bare
        OSError (ELOOP) for a symlink at the name, outside the class the two call sites catch, so a link planted at
        spawn.json or host.stderr got no problem row and no remedy. Now _open_file_nofollow raises HostDirRefused
        naming the file and the directory, with `file` set. Two arms over a verified hosts/<sid>/ of ours: spawn.json a
        link to a file of a peer's (write_spawn_spec), host.stderr the same (open_host_dirs, then host_stderr_open).
        Each: the class, its `file`, the message, the link left standing, the peer's file byte-identical at its old
        mode: nothing followed, nothing written. Red before the change: OSError, not the class, at both arms."""
        spec = {"sid": SID, "name": "web", "version": "abc12345", "state_dir": "/state", "protocol": 1, "env": {"FEATURE_FLAG": "1"}}
        for name in ("spawn.json", "host.stderr"):
            with self.subTest(file=name):
                root = tempfile.mkdtemp()
                self.addCleanup(shutil.rmtree, root, True)
                sh.hosts_dir(root)
                sdir = ht.host_dir(root, SID)
                sdir.mkdir(mode=0o700)
                peer = Path(root) / "peer"
                peer.mkdir(mode=0o755)
                target = peer / "theirs.txt"
                target.write_text("the peer's own bytes")
                os.chmod(target, 0o644)
                (sdir / name).symlink_to(target)
                with self.assertRaises(OSError) as cm:
                    if name == "spawn.json":
                        ht.write_spawn_spec(root, SID, spec)
                    else:
                        with ht.open_host_dirs(root, SID) as dirs:
                            os.close(ht.host_stderr_open(dirs))
                self.assertIsInstance(cm.exception, ht.HostDirRefused, repr(cm.exception))
                self.assertEqual(getattr(cm.exception, "file", None), name, "the refusal names its file")
                self.assertEqual(str(cm.exception), "%s in host directory %s is a symlink, not a regular file" % (name, sdir))
                self.assertTrue((sdir / name).is_symlink(), "the link is left, not replaced")
                self.assertEqual(target.read_text(), "the peer's own bytes", "nothing written through the link")
                self.assertEqual(stat.S_IMODE(os.lstat(target).st_mode), 0o644, "the target's mode untouched")

    @unittest.skipUnless(SDK, "the SDK is not importable here")
    def test_the_spec_fields_track_what_the_sdk_transport_reads(self):
        import claude_agent_sdk._internal.transport.subprocess_cli as scli
        import inspect
        src = inspect.getsource(scli.SubprocessCLITransport._build_command) + inspect.getsource(scli.SubprocessCLITransport.connect)
        read = set(re.findall(r"self\._options\.([a-z_]+)", src)) | {"cwd"}
        callables_or_sdk_side = {"stderr", "user", "session_store", "sandbox", "task_budget", "max_budget_usd", "betas",
                                 "plugins", "agents", "output_format", "tools",
                                 "include_hook_events", "strict_mcp_config", "resume_drops_turn", "permission_prompt_tool_name"}
        self.assertIn("thinking", sh.SPEC_FIELDS, "the thinking-summaries toggle reaches a hosted CLI")
        missing = read - set(sh.SPEC_FIELDS) - callables_or_sdk_side
        self.assertEqual(missing, set(), "fields the SDK reads that the spec does not carry: %r" % sorted(missing))


class HostScopes(unittest.TestCase):
    def test_host_scope_units_match_our_sessions_only(self):
        u = ht.host_scope_unit(SID, 1757374800000)
        self.assertEqual(u, "romp-host-11111111-1757374800000")
        listing = ["%s.scope loaded active running x" % u, "romp-host-99999999-1.scope loaded active running y",
                   "romp-session-11111111-4242-1.scope loaded active running z"]
        self.assertEqual(ht.host_scope_units(listing, [SID]), {u + ".scope": "11111111"})

    def test_the_sweep_stops_a_host_scope_whose_lease_does_not_hold_and_spares_a_live_one(self):
        d = tempfile.mkdtemp(); be = sb.SdkBackend(d, "/bin/true", lambda *a, **k: None)
        live, dead = SID, "22222222-2222-3333-4444-0000000000b2"
        sb.write_lease(d, {"sid": live, "fsid": live, "pid": 999999999, "start": "1", "holder": {"pid": 999999998, "start": "2", "kind": "host"}, "version": "", "t": time.time()})
        sb.write_lease(d, {"sid": dead, "fsid": dead, "pid": 999999997, "start": "1", "holder": {"pid": 999999996, "start": "2", "kind": "host"}, "version": "", "t": time.time()})
        starts = {999999999: "1", 999999998: "2"}      # the live pair is alive; the dead host's pids are gone
        listing = "romp-host-11111111-1.scope loaded active running a\nromp-host-22222222-2.scope loaded active running b\n"
        runs = []
        def run(argv, **kw):
            runs.append(list(argv)); return mock.Mock(stdout=listing if argv == sb.HOST_SCOPE_LIST_ARGV else "", returncode=0)
        with mock.patch.object(sb, "proc_start", lambda p, run=None: starts.get(p)):
            n = be._stop_leftover_scopes([live, dead], run=run)
        stops = [a[-1] for a in runs if a[:3] == ["systemctl", "--user", "stop"]]
        self.assertEqual((n, stops), (1, ["romp-host-22222222-2.scope"]))


class LeaseClassification(unittest.TestCase):
    def test_attach_orphan_none(self):
        now = 1000.0
        st = lambda starts: (lambda p: starts.get(p))
        host_lease = {"sid": SID, "pid": 5, "start": "a", "holder": {"pid": 6, "start": "b", "kind": "host"}, "t": now}
        self.assertEqual(ht.host_lease_state(host_lease, now, st({5: "a", 6: "b"})), "attach")
        self.assertEqual(ht.host_lease_state(host_lease, now, st({5: "a"})), "orphan", "the host is gone")
        self.assertEqual(ht.host_lease_state(dict(host_lease, t=now - 100), now, st({5: "a", 6: "b"})), "orphan", "a stale beat")
        kernel_lease = dict(host_lease, holder={"pid": 6, "start": "b"})
        self.assertEqual(ht.host_lease_state(kernel_lease, now, st({5: "a", 6: "b"})), "none")
        self.assertEqual(ht.host_lease_state(None, now), "none")


# ── the transport against a fake host ──────────────────────────────────────────────────────────
class FakeHost:
    """An asyncio Unix server speaking the host's frames from a scripted journal. `echo_turns`: the CLI behind it runs
    a one-step turn per fed user text (its own user record back, then the turn's result), the frames the backend's
    one-fed-text-at-a-time hold (SdkSession._untaken, 2026-09-08) releases on; a host that echoes nothing holds every
    text after the first for good."""

    def __init__(self, path, records, busy=False, exit_after=None, answer_init=None, echo_turns=False):
        self.path, self.records, self.busy, self.exit_after = path, records, busy, exit_after
        self.answer_init = answer_init      # None: every control request answered; else answer_init(attach_no) -> bool
        self.echo_turns = echo_turns
        self.next_offset = len(records)     # the journal position of the next record this host writes (echo_turns)
        self.attaches = 0
        self.got = []
        self.server = None

    async def start(self):
        self.server = await asyncio.start_unix_server(self._client, path=self.path)

    async def _client(self, reader, writer):
        fr = sh.FrameReader()
        try:
            while True:
                chunk = await reader.read(65536)
                if not chunk:
                    return
                for f in fr.feed(chunk):
                    self.got.append(f)
                    if f["t"] == "attach":
                        if self.busy:
                            writer.write(sh.encode_frame({"t": "busy", "kernel": {"pid": 7}})); await writer.drain(); continue
                        self.attaches += 1
                        answering = self.answer_init is None or self.answer_init(self.attaches)
                        writer.write(sh.encode_frame({"t": "hello", "protocol": 1, "host": {"pid": 10, "start": "h", "version": "v"},
                                                      "cli": {"pid": 11, "start": "c", "fsid": SID}, "journal": {"next": len(self.records)}, "parked": []}))
                        for off, rec in enumerate(self.records):
                            if off > int(f.get("ack", -1)):
                                writer.write(sh.encode_frame({"t": "out", "offset": off, "data": rec}))
                        writer.write(sh.encode_frame({"t": "stderr", "line": "a stderr line"}))
                        if self.exit_after is not None:
                            writer.write(sh.encode_frame({"t": "exit", "code": self.exit_after, "cause": "died"}))
                        await writer.drain()
                    elif f["t"] == "end":
                        writer.write(sh.encode_frame({"t": "exit", "code": 0, "cause": "end"})); await writer.drain()
                    elif f["t"] == "in":
                        obj = json.loads(f["data"])
                        if obj.get("type") == "control_request" and answering:
                            writer.write(sh.encode_frame({"t": "out", "offset": len(self.records), "data": {
                                "type": "control_response", "response": {"subtype": "success", "request_id": obj["request_id"], "response": {}}}}))
                            await writer.drain()
                        elif obj.get("type") == "user" and self.echo_turns:
                            # the CLI took the text and ran its turn: its user record back, then the result (the SDK
                            # parser's required fields, nothing spent), each at its own journal offset
                            for rec in (obj, {"type": "result", "subtype": "success", "duration_ms": 1, "duration_api_ms": 1,
                                              "is_error": False, "num_turns": 1, "session_id": SID}):
                                writer.write(sh.encode_frame({"t": "out", "offset": self.next_offset, "data": rec}))
                                self.next_offset += 1
                            await writer.drain()
                    elif f["t"] == "ping":
                        writer.write(sh.encode_frame({"t": "pong"})); await writer.drain()
        except (ConnectionResetError, asyncio.IncompleteReadError):
            return

    def close(self):
        if self.server:
            self.server.close()


def run(coro):
    return asyncio.run(coro)


class TransportOverSocket(unittest.TestCase):
    def _path(self):
        # under the system temp dir the tests package recorded (ROMP_TESTS_SYSTEM_TMPDIR), outside the run's private
        # root, so the AF_UNIX path fits sun_path under a long TMPDIR (a root costs 20 bytes; two levels under xdist
        # before 2026-09-21); outside the root is outside the exit sweep's
        # scope too, so the dir is removed here, when its test is (six per run leaked before this cleanup)
        d = tempfile.mkdtemp(dir=os.environ.get("ROMP_TESTS_SYSTEM_TMPDIR") or None)
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        return os.path.join(d, "h.sock")

    def test_attach_replays_from_the_ack_then_acks_and_side_frames_reach_their_callbacks(self):
        recs = [{"type": "system", "subtype": "init", "session_id": SID}, {"type": "assistant", "n": 1}, {"type": "result", "n": 2}]
        async def go():
            fh = FakeHost(self._path(), recs); await fh.start()
            acks, stderr, hellos = [], [], []
            t = ht.HostTransport(fh.path, kernel={"pid": 1, "start": "k", "version": "v"}, ack=0, on_ack=acks.append,
                                 on_stderr=stderr.append, on_hello=hellos.append)
            await t.connect()
            self.assertTrue(t.is_ready()); self.assertEqual(hellos[0]["cli"]["pid"], 11)
            got = []
            async def read():
                async for m in t.read_messages():
                    got.append(m)
                    if len(got) == 3:
                        break
            # the Query's shape: the reader is started, then the initialize is written; the records are held until
            # its answer has been handed over, then follow in order
            reader = asyncio.ensure_future(read())
            await asyncio.sleep(0.05)
            await t.write(json.dumps({"type": "control_request", "request_id": "req_1_x", "request": {"subtype": "initialize"}}))
            await asyncio.wait_for(reader, 5)
            self.assertEqual(got[0]["type"], "control_response", "the initialize's answer comes first, ahead of the replay")
            self.assertEqual([m.get("n") for m in got[1:]], [1, 2], "then the replay, from after the acknowledged offset 0")
            self.assertEqual(stderr, ["a stderr line"])
            self.assertEqual(acks[-1], 2, "the held records' offsets were acknowledged as consumed; the answer's (3) waits for the stream to move on")
            t.detach_mode = True
            await t.end_input()                       # detach mode: no `end` goes out
            await t.close()
            await asyncio.sleep(0.1)
            kinds = [f["t"] for f in fh.got]
            self.assertIn("detach", kinds); self.assertNotIn("end", kinds)
            self.assertEqual(fh.got[0]["ack"], 0)
            fh.close()
        run(go())

    def test_a_replay_of_three_hundred_records_still_answers_the_initialize_first(self):
        # the commit 2-3 review's second finding: the SDK's message stream buffers 100 records before its reader
        # blocks, and the initialize's answer used to sit behind the whole replay in the one ordered stream
        recs = [{"type": "assistant", "n": i} for i in range(300)]
        async def go():
            fh = FakeHost(self._path(), recs); await fh.start()
            acks = []
            t = ht.HostTransport(fh.path, kernel={"pid": 1}, on_ack=acks.append)
            await t.connect()
            got = []
            async def read():
                async for m in t.read_messages():
                    got.append(m)
                    if len(got) == 301:
                        break
            reader = asyncio.ensure_future(read())
            await asyncio.sleep(0.1)                     # the replay is already flowing (and held)
            await t.write(json.dumps({"type": "control_request", "request_id": "req_0_init", "request": {"subtype": "initialize"}}))
            await asyncio.wait_for(reader, 10)
            self.assertEqual(got[0]["type"], "control_response")
            self.assertEqual([m["n"] for m in got[1:]], list(range(300)), "every replayed record, in order, after the answer")
            # the answer's own offset (300) is acknowledged only when the stream moves on past the held records;
            # a reader that stopped here has acknowledged exactly what it consumed, nothing beyond
            self.assertEqual(t.ack_offset, 299)
            self.assertEqual((acks[0], acks[-1]), (0, 299), "the ack advanced with each held record, never jumping to the answer's offset first")
            self.assertEqual(acks, sorted(acks))
            fh.close()
        run(go())

    def test_a_connect_that_never_completed_detaches_on_close_and_never_ends_the_cli(self):
        async def go():
            fh = FakeHost(self._path(), [{"type": "assistant"}]); await fh.start()
            t = ht.HostTransport(fh.path, kernel={"pid": 1}, end_grace=7)
            await t.connect()                            # attached, but no initialize answered yet
            await t.close()
            await asyncio.sleep(0.1)
            kinds = [f["t"] for f in fh.got]
            self.assertIn("detach", kinds); self.assertNotIn("end", kinds, "a failed attach must not end the turn it failed to join")
            fh.close()
        run(go())

    def test_busy_refuses_and_a_non_zero_exit_raises_like_the_subprocess_transport(self):
        async def go():
            fh = FakeHost(self._path(), [], busy=True); await fh.start()
            t = ht.HostTransport(fh.path, kernel={"pid": 1})
            with self.assertRaises(ht.CLIConnectionError):
                await t.connect()
            fh.close()
            fh2 = FakeHost(self._path(), [{"type": "assistant"}], exit_after=3); await fh2.start()
            t2 = ht.HostTransport(fh2.path, kernel={"pid": 1})
            await t2.connect()
            got = []
            with self.assertRaises(ht.ProcessError):
                async for m in t2.read_messages():
                    got.append(m)
            self.assertEqual(len(got), 1); self.assertEqual(t2.exit_info["code"], 3)
            fh2.close()
        run(go())

    def test_end_input_and_close_send_end_with_the_grace_when_not_detaching(self):
        async def go():
            fh = FakeHost(self._path(), []); await fh.start()
            t = ht.HostTransport(fh.path, kernel={"pid": 1}, end_grace=7)
            await t.connect()
            await t.end_input()
            await asyncio.sleep(0.1)
            ends = [f for f in fh.got if f["t"] == "end"]
            self.assertEqual(ends[0]["grace"], 7)
            await t.signal("INT")
            await asyncio.sleep(0.1)
            self.assertIn({"t": "signal", "sig": "INT"}, fh.got)
            fh.close()
        run(go())


def journal_dirs(d):
    """A HostDirs over a bare journal directory outside hosts/ (the descriptor opened here, closed by the `with` the caller
    puts it in): what host_transport.read_journal_dir and HostTransport.from_journal take since the fork PR that follows
    #814 (a directory PATH through #814). Production callers hand the read descent's own HostDirs."""
    return ht.HostDirs(None, os.open(d, os.O_RDONLY | os.O_DIRECTORY), Path(d))


class TransportOverJournal(unittest.TestCase):
    def test_the_replay_answers_the_initialize_and_yields_the_journal_then_ends(self):
        d = tempfile.mkdtemp(); j = sh.Journal(d)
        self.addCleanup(shutil.rmtree, d, True)
        for rec in ({"type": "system", "subtype": "init"}, {"type": "assistant", "n": 1}, {"type": "result", "n": 2}):
            j.append(rec)
        j.close()
        dirs = journal_dirs(d)
        self.addCleanup(dirs.close)
        async def go():
            acks = []
            t = ht.HostTransport.from_journal(dirs, ack=0, on_ack=acks.append)
            await t.connect()
            got = []
            async def read():
                async for m in t.read_messages():
                    got.append(m)
            reader = asyncio.ensure_future(read())
            await asyncio.sleep(0.05)
            await t.write(json.dumps({"type": "control_request", "request_id": "req_0_i", "request": {"subtype": "initialize"}}))
            await t.write(json.dumps({"type": "user", "message": {"role": "user", "content": "x"}}))   # dropped, counted
            await asyncio.wait_for(reader, 10)
            kinds = [m["type"] for m in got]
            self.assertEqual(kinds, ["assistant", "result", "control_response"])
            self.assertEqual(got[2]["response"]["request_id"], "req_0_i")
            self.assertEqual(acks, [1, 2]); self.assertEqual(t.dropped_writes, 1)
            self.assertEqual(t.exit_info["cause"], "replay-end")
            await t.close()
        run(go())


class JournalReads(unittest.TestCase):
    """The orphan journal BY DESCRIPTOR at function level (host_transport.journal_segments, read_journal_dir,
    journal_has_tail, HostTransport.from_journal; the fork PR that follows #814, 2026-09-21, building the item "the
    journal reads descend by descriptor"): the listing off the held <sid> descriptor, each file the owner question by
    name under it through the one reader, the answers from SHAPE_TABLE, and the swap the descriptor closes. Through
    #814 the reader (sh.read_journal_dir) took the directory's PATH: a glob over it, gaps.json by its path, each segment
    by the path the glob yielded; none of these cases could be written against it, since a path has no held descriptor
    to list off, which is what the production cases in BackendHostRules drive against the base's roads."""

    def _root(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        return Path(d)

    def _sid_dir(self, root, sid_mode=0o775):
        sdir = root / "hosts" / SID
        sdir.mkdir(parents=True); os.chmod(root / "hosts", 0o700); os.chmod(sdir, sid_mode)
        return sdir

    def test_the_listing_runs_on_the_held_descriptor_so_a_sid_relinked_after_the_descent_is_never_read(self):
        """THE SWAP: a peer renames our <sid>/ away and links theirs into its place between the read road's descent and
        the listing (a rename in hosts/, so a group-writable hosts/ under a traversable root, #814's weaker precondition).
        The listing is a scandir off the descriptor the descent holds, so it reads the directory the descent verified
        (our three records, moved aside) and never the link's target (the peer's three, tagged); nothing of the peer's
        and nothing at the path is stat'd, opened or listed BY PATH (path_ops: 0), the link is left standing, and by
        path the peer's segment answers a glob, the read the predecessor made. journal_segments and journal_has_tail
        answer off the same descriptor."""
        root = self._root()
        sdir = self._sid_dir(root)
        write_segment(sdir / "journal-0.jsonl", 3)
        peer = self._root() / "peer" / SID
        peer.mkdir(parents=True, mode=0o755)
        write_segment(peer / "journal-0.jsonl", 3, peer=True)
        link = root / "hosts" / SID
        with ht.open_host_dirs_if_present(root, SID) as dirs, path_ops(peer, peer / "journal-0.jsonl", link, link / "journal-0.jsonl") as ops:
            os.rename(sdir, root / "hosts" / (SID + ".moved"))            # the swap, after the descent and before the listing
            link.symlink_to(peer)
            got = list(ht.read_journal_dir(dirs))
            self.assertEqual([(o, r["n"], r.get("peer")) for o, r in got], [(0, 0, None), (1, 1, None), (2, 2, None)],
                             "the directory the descent verified, not the link's target")
            self.assertEqual(ht.journal_segments(dirs), [(0, "journal-0.jsonl")])
            self.assertTrue(ht.journal_has_tail(dirs, 2)); self.assertFalse(ht.journal_has_tail(dirs, 3))
        self.assertEqual(ops, [], "nothing of the peer's, and nothing at the path, was stat'd, opened or listed by path: %r" % (ops,))
        self.assertTrue(link.is_symlink(), "the link is left, not replaced")
        self.assertEqual([json.loads(l).get("peer") for l in (link / "journal-0.jsonl").read_text().splitlines()], [True] * 3,
                         "by PATH the peer's segment stands at the name: the read the predecessor's glob made")

    def test_every_shape_at_a_segment_or_at_gaps_json_is_answered_from_the_table_by_the_reader(self):
        """THE TABLE at function level: SHAPE_TABLE's 13 (kind, owner) rows planted at a segment's name (journal-0.jsonl,
        beside a segment of ours at journal-3.jsonl holding offsets 3 and 4) and at gaps.json (beside a segment of ours at
        journal-0.jsonl holding 0, 1 and 2; a regular gaps.json names offset 1), 26 cells, put to read_journal_dir with a
        recording `refused`. The answers, from the readers' table: `absent` and `not-file`, the file skipped with nothing
        opened, the records of ours alone (a FIFO at a segment's name never blocks: nothing opens it); `ours`, read (the
        planted segment's three records ahead of ours; the gaps file's offset skipped in the numbering, 0, 2, 3); `foreign`,
        ONE HostFileForeign handed to `refused` naming the file and the uid and the file skipped as absent (a peer's
        gaps.json: the numbering proceeds as with none); `link`, the file-shape HostDirRefused RAISED naming the file (the
        reader is refused, as the roads are by a link at identity.json). Beside the answer: the only open by name is a
        regular file of ours (name_opens), nothing is stat'd, opened or listed by PATH (path_ops: 0, the directory
        included), the stub's path-stat count is 0, the mode is unchanged and a link's target untouched."""
        euid = os.geteuid()
        for name in ("journal-0.jsonl", "gaps.json"):
            for kind, owner, _, expect in SHAPE_TABLE:
                with self.subTest(name=name, kind=kind, owner=owner):
                    root = self._root()
                    sdir = self._sid_dir(root)
                    elsewhere = self._root()
                    if name == "gaps.json":
                        write_segment(sdir / "journal-0.jsonl", 3)
                        content = "[1]"
                    else:
                        write_segment(sdir / "journal-3.jsonl", 2, first=3)
                        content = "".join(json.dumps({"type": "assistant", "n": i}) + "\n" for i in range(3))
                    plant_shape(sdir, name, kind, content, elsewhere)
                    target = (elsewhere / name).read_text() if kind == "symlink-to-file" else None
                    refused = []
                    ctx = foreign_uid(sdir / name) if owner == "foreign" else contextlib.nullcontext()   # its own lstat, before the recorder
                    with path_ops(sdir, sdir / name) as ops:
                        with ht.open_host_dirs_if_present(root, SID) as dirs, ctx as fu, name_opens(name) as opened:
                            try:
                                got = ("value", [(o, r["n"]) for o, r in ht.read_journal_dir(dirs, 0, refused.append)])
                            except ht.HostFileForeign as e:
                                got = ("raised-foreign", e.file, e.uid)
                            except ht.HostDirRefused as e:
                                got = ("link", e.file, getattr(e, "uid", None), str(e))
                    ours = [(3, 3), (4, 4)] if name == "journal-0.jsonl" else [(0, 0), (1, 1), (2, 2)]
                    if expect in ("absent", "not-file"):
                        self.assertEqual(got, ("value", ours), "%s/%s at %s: the records of ours alone" % (kind, owner, name))
                        self.assertEqual(refused, [])
                        self.assertEqual(opened, [], "nothing opened at the name")
                    elif expect == "ours":
                        self.assertEqual(got, ("value", [(0, 0), (1, 1), (2, 2), (3, 3), (4, 4)] if name == "journal-0.jsonl" else [(0, 0), (2, 1), (3, 2)]),
                                         "%s at %s: the planted file of ours is read (a gaps file's offset skipped in the numbering)" % (kind, name))
                        self.assertEqual(refused, [])
                        self.assertEqual(opened, [name], "the one open by name")
                    elif expect == "foreign":
                        self.assertEqual(got, ("value", ours), "%s/%s at %s: skipped as absent after the refusal" % (kind, owner, name))
                        self.assertEqual([(type(e).__name__, e.file, e.uid) for e in refused], [("HostFileForeign", name, euid + 1)],
                                         "one refusal handed to the caller, naming the file and the owner")
                        self.assertIn("%s in host directory %s belongs to uid %d, not to us (uid %d)" % (name, sdir, euid + 1, euid), str(refused[0]))
                        self.assertEqual(opened, [], "a peer's entry is never opened")
                    else:
                        self.assertEqual(got[:3], ("link", name, None), "%s/%s at %s: the file-shape refusal, raised" % (kind, owner, name))
                        self.assertIn("%s in host directory %s is a symlink, not a regular file" % (name, sdir), got[3])
                        self.assertEqual(refused, [])
                        self.assertEqual(opened, [], "nothing behind the link is opened")
                    self.assertEqual(ops, [], "%s/%s at %s: stat'd, opened or listed by PATH: %r" % (kind, owner, name, ops))
                    if fu is not None:
                        self.assertEqual(fu.path_stats, 0, "the owner check took a path stat: %r" % (fu.path_stat_calls,))
                    self.assertEqual(stat.S_IMODE(os.lstat(sdir).st_mode), 0o775, "the read changed no mode")
                    if target is not None:
                        self.assertEqual((elsewhere / name).read_text(), target, "nothing behind the link was touched")

    def test_a_foreign_entry_with_no_row_to_file_raises_out_of_the_reader(self):
        """`refused` None: a caller with no row to file gets the refusal itself, never a silent skip (the repo's rule that
        an unavailable authoritative source surfaces an error). The listing, the reader, the tail check, AND THE REPLAY
        TRANSPORT built without `on_refused` (the review fix-up of this PR, on the drives verifier's finding: through
        the PR's first commit HostTransport._read_journal swallowed the refusal when the callback was None, so a peer's
        segment beside ours ended the stream replay-end with nothing raised, nothing filed and none of our records
        replayed, the listing having raised before the first record). RED BEFORE at the PR's first commit, the
        transport arm: `HostFileForeign not raised`, the stream ended with exit cause replay-end and the initialize's
        answer alone. Now read_messages raises the refusal out of its read loop and the stream has no exit."""
        root = self._root()
        sdir = self._sid_dir(root)
        write_segment(sdir / "journal-0.jsonl", 3)
        with ht.open_host_dirs_if_present(root, SID) as dirs, foreign_uid(sdir / "journal-0.jsonl") as fu:
            with self.assertRaises(ht.HostFileForeign) as cm:
                ht.journal_segments(dirs)
            self.assertEqual((cm.exception.file, cm.exception.uid), ("journal-0.jsonl", os.geteuid() + 1))
            with self.assertRaises(ht.HostFileForeign):
                list(ht.read_journal_dir(dirs))
            with self.assertRaises(ht.HostFileForeign):
                ht.journal_has_tail(dirs, 0)
        self.assertEqual(fu.path_stats, 0)
        # the replay transport with no on_refused: a peer's segment beside ours
        root = self._root()
        sdir = self._sid_dir(root)
        write_segment(sdir / "journal-0.jsonl", 3)
        write_segment(sdir / "journal-100.jsonl", 3, first=100, peer=True)
        got = []

        async def go(dirs):
            t = ht.HostTransport.from_journal(dirs, ack=-1)
            await t.connect()
            try:
                async for m in t.read_messages():
                    got.append(m)
            finally:
                await t.close()
            return t
        with ht.open_host_dirs_if_present(root, SID) as dirs, foreign_uid(sdir / "journal-100.jsonl") as fu:
            with self.assertRaises(ht.HostFileForeign) as cm:
                run(go(dirs))
        self.assertEqual((cm.exception.file, cm.exception.uid), ("journal-100.jsonl", os.geteuid() + 1))
        self.assertEqual(got, [], "the listing raised before the first record")
        self.assertEqual(fu.path_stats, 0)

    def test_a_link_swapped_onto_a_segment_between_the_stat_and_the_open_is_refused_and_never_followed(self):
        """THE OPEN'S OWN GUARD: the listing's owner question saw a regular file of ours at journal-0.jsonl; a link of ours
        to a file elsewhere (three records tagged) is swapped onto the name INSIDE the open (os.open wrapped: after the
        stat by name, before the real open), so only O_NOFOLLOW stands between the reader and the target. The open fails
        ELOOP, the file-shape refusal is raised naming the file, and the target is never opened by path or by name
        (path_ops: 0; its bytes stand). This is the cell the mutation "open without O_NOFOLLOW" reds: with the flag off
        the open follows the link, the fstat reads a regular file of ours and the tagged records are yielded. The cells
        that plant a link BEFORE the read cannot see that mutation, because the stat by name refuses the link first."""
        root = self._root()
        sdir = self._sid_dir(root)
        write_segment(sdir / "journal-0.jsonl", 3)
        elsewhere = self._root()
        write_segment(elsewhere / "journal-0.jsonl", 3, behind=True)
        real_open, swapped = os.open, []

        def open_and_swap(path, *a, **k):
            if os.fspath(path) == "journal-0.jsonl" and k.get("dir_fd") is not None and not swapped:
                os.unlink(sdir / "journal-0.jsonl")
                (sdir / "journal-0.jsonl").symlink_to(elsewhere / "journal-0.jsonl")
                swapped.append(True)
            return real_open(path, *a, **k)
        with path_ops(elsewhere / "journal-0.jsonl") as ops, ht.open_host_dirs_if_present(root, SID) as dirs, \
             mock.patch.object(os, "open", open_and_swap):
            with self.assertRaises(ht.HostDirRefused) as cm:
                list(ht.read_journal_dir(dirs))
        self.assertEqual(swapped, [True], "the swap landed inside the open, after the stat by name")
        self.assertNotIsInstance(cm.exception, ht.HostFileForeign)
        self.assertEqual(cm.exception.file, "journal-0.jsonl")
        self.assertIn("journal-0.jsonl in host directory %s is a symlink, not a regular file" % sdir, str(cm.exception))
        self.assertEqual(ops, [], "the target was never opened by path: %r" % (ops,))
        self.assertEqual([json.loads(l)["behind"] for l in (elsewhere / "journal-0.jsonl").read_text().splitlines()], [True] * 3, "the target's bytes stand")

    def test_the_replay_transport_reads_through_the_descriptor_files_a_peers_file_and_ends_on_a_link(self):
        """HostTransport.from_journal takes the HostDirs and an `on_refused`: a peer's segment beside ours (journal-3.jsonl,
        foreign by the stub) is one refusal handed to the callback and skipped, our three records replayed and acked, the
        stream ending replay-end as before; a link of ours at gaps.json is the file-shape refusal handed to the callback
        and the stream ENDS after it (no records, the initialize answered, replay-end), never a raise out of the read loop.
        The transport borrows the descriptor: it is open before and after."""
        for arm in ("a peer's segment beside ours", "a link of ours at gaps.json"):
            with self.subTest(arm=arm):
                root = self._root()
                sdir = self._sid_dir(root)
                write_segment(sdir / "journal-0.jsonl", 3)
                if arm == "a peer's segment beside ours":
                    write_segment(sdir / "journal-3.jsonl", 2, first=3, peer=True)
                    stub, name = foreign_uid(sdir / "journal-3.jsonl"), "journal-3.jsonl"
                else:
                    (sdir / "gaps.json").symlink_to(self._root() / "gaps.json")
                    stub, name = contextlib.nullcontext(), "gaps.json"
                acks, refused = [], []

                async def go(dirs):
                    t = ht.HostTransport.from_journal(dirs, ack=-1, on_ack=acks.append, on_refused=refused.append)
                    self.assertIs(t.journal_dirs, dirs); self.assertEqual(t.journal_dir, str(sdir), "the replay flag, the directory's path for wording")
                    await t.connect()
                    got = []

                    async def read():
                        async for m in t.read_messages():
                            got.append(m)
                    reader = asyncio.ensure_future(read())
                    await asyncio.sleep(0.05)
                    await t.write(json.dumps({"type": "control_request", "request_id": "req_0_i", "request": {"subtype": "initialize"}}))
                    await asyncio.wait_for(reader, 10)
                    await t.close()
                    return got, t
                with ht.open_host_dirs_if_present(root, SID) as dirs, stub as fu:
                    got, t = run(go(dirs))
                    os.fstat(dirs.dir)                                   # the descriptor is the caller's to close: still open
                if arm == "a peer's segment beside ours":
                    self.assertEqual([m.get("n") for m in got if m["type"] != "control_response"], [0, 1, 2], "our records, none of the peer's")
                    self.assertEqual(acks, [0, 1, 2])
                    self.assertEqual([(type(e).__name__, e.file) for e in refused], [("HostFileForeign", name)])
                    self.assertEqual(fu.path_stats, 0)
                else:
                    self.assertEqual([m["type"] for m in got], ["control_response"], "no record replayed past the refusal; the initialize answered")
                    self.assertEqual(acks, [])
                    self.assertEqual([(type(e).__name__, e.file, getattr(e, "uid", None)) for e in refused], [("HostDirRefused", name, None)])
                self.assertEqual(t.exit_info["cause"], "replay-end")


class BackendHostRules(unittest.TestCase):
    """The backend's host rules driven, not pinned by source: the drain's intent latch, the hello's open-turn
    adoption and slot release, a thread attached at boot, a hosted thread's notices, an ended host's lease race,
    the ack that a dead host must not get, and the kill switch after an orphan."""

    def _be(self, short=False):
        # short: the state dir under the system temp dir (tests/README.md's ROMP_TESTS_SYSTEM_TMPDIR), so a fake host's
        # AF_UNIX socket path under it stays inside sun_path's 104 bytes on every platform and under a long TMPDIR. A short
        # dir is outside the run's private root and so outside the exit sweep's scope: removed here, when its test is
        d = tempfile.mkdtemp(dir=(os.environ.get("ROMP_TESTS_SYSTEM_TMPDIR") or None) if short else None); logs = []
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        be = sb.SdkBackend(d, "/bin/true", lambda *a, **k: None, log=logs.append); be._test_logs = logs
        return d, be

    def _serve_fake_host(self, d, silent=False):
        """A FakeHost (or a server that accepts and never writes hello, `silent`) on the backend's host socket, on a
        loop thread of its own; returns (host, stop)."""
        import threading
        sock = str(ht.host_sock(d, SID))
        os.makedirs(os.path.dirname(sock), exist_ok=True)   # the host's directory, which a real spawn creates
        host = FakeHost(sock, [])
        loop = asyncio.new_event_loop()
        started = threading.Event()
        async def mute(reader, writer):
            await asyncio.Event().wait()                     # accepts, never writes hello
        async def start():
            if silent:
                host.server = await asyncio.start_unix_server(mute, path=sock)
            else:
                await host.start()
        def serve():
            asyncio.set_event_loop(loop)
            loop.run_until_complete(start()); started.set()
            loop.run_forever()
        threading.Thread(target=serve, daemon=True).start()
        self.assertTrue(started.wait(5), "the fake host serves its socket")
        def stop():
            loop.call_soon_threadsafe(host.close); loop.call_soon_threadsafe(loop.stop)
        return host, stop

    def test_the_drain_latches_a_session_mid_attach_by_intent(self):
        d, be = self._be()
        s = types.SimpleNamespace(sid=SID, name="web", inflight=1, ended=False, thread=None, _host=None, _host_intent=True,
                                  detached=False, shutdown=lambda: None)
        be.sessions[SID] = s
        res = be.drain(timeout=1)
        self.assertEqual(res["cutTurns"], [], "a session mid-attach is detached, never cut")
        self.assertTrue(s.detached)

    def test_hello_adopts_the_hosts_open_turns_and_releases_the_slot_only_for_an_attach(self):
        d, be = self._be()
        fired = []
        t = types.SimpleNamespace(hello={"host": {"pid": 1, "start": "a"}, "cli": {"pid": 2, "start": "b"}}, ack_offset=5)
        s = types.SimpleNamespace(sid=SID, name="web", inflight=0, _host=t, _host_is_attach=True, _fire_boot_settled=lambda: fired.append(1))
        be._on_host_hello(s, {"host": {"pid": 1, "start": "a"}, "cli": {"pid": 2, "start": "b"}, "journal": {"next": 6}, "parked": [], "inflight": 1})
        self.assertEqual((s.inflight, fired), (1, [1]), "mid-turn adopted; the boot slot released for an attach")
        s2 = types.SimpleNamespace(sid=SID, name="web", inflight=1, _inflight_texts=["a fed text"], _host=t, _host_is_attach=False,
                                   _fire_boot_settled=lambda: fired.append(2))
        be._on_host_hello(s2, {"host": {"pid": 1, "start": "a"}, "cli": {}, "journal": {"next": 0}, "parked": [], "inflight": 0})
        self.assertEqual((s2.inflight, s2._inflight_texts, fired), (0, [], [1]),
                         "the host's count is adopted EXACTLY, down as well as up: a stale count on our side never survives an attach "
                         "(the base kept the higher of the two and read Working for two days); a spawn's hello leaves the slot to the init record")

    def test_the_hello_decides_the_fresh_cli_by_identity_and_tolerates_older_shapes(self):
        """The fresh-CLI decision at the hello (the connect loop's pins drive it through the loop; this one drives the handler):
        the hello's cli.pid:cli.start against the reg's spawnedAtCli. Equal: nothing. Different with a spawn time: the block
        with the host's value and the launch login from cli.login (the options' login when the hello lacks it). Different
        without a spawn time (older host code): the identity recorded, nothing else. No identity at all: nothing stamped,
        a log line, never a raise."""
        d, be = self._be()
        sb.write_reg(Path(d), SID, {"sid": SID, "name": "web", "cwd": d, "spawnedAt": 1700000000, "spawnedAtCli": "2:b"})
        s = sb.SdkSession(be, sb.read_reg(Path(d), SID)); s._launched_login = "kept"
        base = {"host": {"pid": 1, "start": "a"}, "journal": {"next": 0}, "parked": [], "inflight": 0}
        def reg():
            r = sb.read_reg(Path(d), SID)
            return (r.get("spawnedAt"), r.get("spawnedAtCli"), s._launched_login)
        for c in (None, {}, {"fsid": SID}, {"pid": 5}, {"start": "x"}, "not a dict"):
            h = dict(base)
            if c is not None:
                h["cli"] = c
            be._on_host_hello(s, h)
        self.assertEqual(reg(), (1700000000, "2:b", "kept"), "no identity: nothing moves")
        self.assertEqual(sum("names no CLI identity" in m for m in be._test_logs), 6)
        be._on_host_hello(s, dict(base, cli={"pid": 2, "start": "b", "spawnedAt": 1700009999, "login": "other"}))
        self.assertEqual(reg(), (1700000000, "2:b", "kept"), "the CLI the reg names: nothing, whatever the hello says")
        be._on_host_hello(s, dict(base, cli={"pid": 3, "start": "c"}))
        self.assertEqual(reg(), (1700000000, "3:c", "kept"), "older host code: the identity recorded, the epoch and login stand")
        self.assertTrue(any("recorded, nothing stamped" in m for m in be._test_logs))
        be._on_host_hello(s, dict(base, cli={"pid": 4, "start": "d", "spawnedAt": 1700005000, "login": "launch-login"}))
        self.assertEqual(reg(), (1700005000, "4:d", "launch-login"), "a fresh CLI: the host's spawn time and the launch's login")
        self.assertEqual(sb.read_reg(Path(d), SID).get("launchedLogin"), "launch-login")
        s._options_login = "opts-login"
        be._on_host_hello(s, dict(base, cli={"pid": 5, "start": "e", "spawnedAt": 1700006000}))
        self.assertEqual(reg(), (1700006000, "5:e", "opts-login"), "a hello without cli.login: the options' login")
        be._on_host_hello(s, dict(base, cli={"pid": 6, "start": "f", "spawnedAt": True, "login": "x"}))
        self.assertEqual(reg(), (1700006000, "6:f", "opts-login"), "a bool spawn time reads as absent")
        be._on_host_hello(s, dict(base, cli={"pid": 7, "start": "g", "spawnedAt": "1700007000", "login": "x"}))
        self.assertEqual(reg(), (1700006000, "7:g", "opts-login"), "a string spawn time reads as absent")
        # the empty-login reading (the follow-up's read, low 3): "" IS an identifier, the machine's own login, stamped as the
        # host echoes what the launch billed; only an ABSENT field falls to the options' login
        be._on_host_hello(s, dict(base, cli={"pid": 8, "start": "h", "spawnedAt": 1700008000, "login": ""}))
        self.assertEqual(reg(), (1700008000, "8:h", ""), "an empty cli.login stamps the machine's own login, not the options'")
        self.assertEqual(sb.read_reg(Path(d), SID).get("launchedLogin"), "")

    def test_a_hosted_comment_thread_attaches_at_boot_and_gets_no_dead_life_notices(self):
        d, be = self._be()
        tsid = "33333333-2222-3333-4444-0000000000b3"
        reg = {"sid": tsid, "name": "t1", "cwd": d, "mode": "default", "effort": "high", "lastSid": tsid, "alive": True,
               "threadOf": SID, "bgTasks": [{"id": "x", "desc": "a task"}], "pendingAsk": True, "spawnedAt": 1}
        sb.write_reg(Path(d), tsid, reg)
        sb.write_lease(d, {"sid": tsid, "fsid": tsid, "pid": 999999999, "start": "1", "holder": {"pid": 999999998, "start": "2", "kind": "host"}, "version": "", "t": time.time()})
        starts = {999999999: "1", 999999998: "2"}
        started = []
        with mock.patch.object(sb, "proc_start", lambda p, run=None: starts.get(p)), \
             mock.patch.object(sb.SdkSession, "start", lambda self: started.append(self.sid)):
            be._boot_reconcile([dict(reg)])
            self.assertIn(tsid, be._boot_attach_sids, "a thread with a live host attaches at boot (the attach check runs before the thread skip)")
            be._ensure(tsid)
        queue = (sb.read_reg(Path(d), tsid) or {}).get("queue") or []
        self.assertEqual(queue, [], "no killed-question or dead-task notice for a thread whose host kept it alive")

    def test_a_host_this_kernel_ended_is_ended_not_died_and_its_stale_ack_is_never_written(self):
        d, be = self._be()
        t = types.SimpleNamespace(hello={"host": {"pid": 7, "start": "h"}, "cli": {"pid": 8, "start": "c"}}, ack_offset=3, exit_info=None)
        s = types.SimpleNamespace(sid=SID, name="web", _host=t, _host_ack_t=0.0)
        sb.write_reg(Path(d), SID, {"sid": SID, "name": "web", "alive": True})
        be._host_ended(s, {"t": "exit", "code": 0, "cause": "end"})
        self.assertEqual(be._host_recently_ended[SID], "7:h")
        lease = {"sid": SID, "holder": {"pid": 7, "start": "h", "kind": "host"}}
        self.assertEqual(be._holder_ident(lease), "7:h", "the ended host is recognized by identity, so its lease race is a wait, not a host.died")
        t.exit_info = {"t": "exit", "code": 0}
        be._write_host_ack(s, force=True)
        self.assertNotIn("hostAck", sb.read_reg(Path(d), SID) or {}, "no ack written for a host that reported its exit")

    # The mutation pass after round 3 of the SDK pin review (2026-09-19): _record_refused_launch_position's docstring
    # says every road that clears the host's directory drops hostLogPos with it, and the orphan road's drop has its
    # case below (the setting-off replay); _host_ended's had none, so with hostLogPos left out of its drop the suite
    # stayed green and a refused launch's line count outlived the file it counted. The three causes that clear the
    # directory (end, end-forced, eof-grace) drop both keys; a death keeps the directory and the position for the
    # orphan road to read.
    def test_an_end_that_clears_the_hosts_directory_drops_host_log_pos_with_host_ack(self):
        d, be = self._be()
        hd = ht.host_dir(d, SID)

        def seed():
            hd.mkdir(parents=True, exist_ok=True)
            (hd / "host.log").write_text(json.dumps({"t": 1, "kind": "host-started"}) + "\n")
            sb.write_reg(Path(d), SID, {"sid": SID, "name": "web", "alive": True,
                                         "hostAck": {"host": "7:h", "cli": "8:c", "offset": 3},
                                         "hostLogPos": {"host": sb.HOST_LOG_POS_REFUSED, "pos": 1}})
            t = types.SimpleNamespace(hello={"host": {"pid": 7, "start": "h"}, "cli": {"pid": 8, "start": "c"}}, ack_offset=3, exit_info=None)
            return types.SimpleNamespace(sid=SID, name="web", _host=t, _host_ack_t=0.0)
        for cause in ("end", "end-forced", "eof-grace"):
            be._host_ended(seed(), {"t": "exit", "code": 0, "cause": cause})
            reg = sb.read_reg(Path(d), SID) or {}
            self.assertFalse(hd.exists(), cause)
            self.assertNotIn("hostAck", reg, cause)
            self.assertNotIn("hostLogPos", reg, cause)
        be._host_ended(seed(), {"t": "exit", "code": 1, "cause": "died"})
        reg = sb.read_reg(Path(d), SID) or {}
        self.assertTrue(hd.exists(), "a death keeps the directory for the orphan road")
        self.assertIn("hostAck", reg)
        self.assertEqual(reg.get("hostLogPos"), {"host": sb.HOST_LOG_POS_REFUSED, "pos": 1}, "and the position with it")

    def test_a_symlinked_sid_on_the_removal_road_is_refused_and_the_targets_file_is_not_walked(self):
        """The removal road's <sid>-level O_NOFOLLOW, driven (the mutation lens on round 5 of the review,
        2026-09-20, found it held by no case: remove_host_dir's docstring and the PR body say _rmtree_at
        refuses a link at any level, but only the hosts/ level was driven, so a link at hosts/<sid> was
        unpinned). hosts/<sid> is a symlink to a peer's directory holding a file of the peer's; _host_ended
        for an end this kernel asked for reaches remove_host_dir, whose _rmtree_at opens <sid>
        O_DIRECTORY|O_NOFOLLOW off the verified hosts/ descriptor, so the open fails on the link, the walk
        never descends, the peer's file stands and the link is left. A delete onto an attacker-chosen target
        is this PR's standing class. Red with O_NOFOLLOW dropped from _rmtree_at's open: the link is followed
        and the peer's file is unlinked before the trailing rmdir on the link raises."""
        d, be = self._be()
        hosts = ht.host_dir(d, SID).parent
        hosts.mkdir(parents=True, mode=0o700)
        peer = Path(d) / "peer" / SID
        peer.mkdir(parents=True, mode=0o700)
        (peer / "keep").write_text("the peer's own file")
        (hosts / SID).symlink_to(peer)                          # hosts/<sid> -> a directory the peer owns
        sb.write_reg(Path(d), SID, {"sid": SID, "name": "web", "alive": True})
        t = types.SimpleNamespace(hello={"host": {"pid": 7, "start": "h"}, "cli": {"pid": 8, "start": "c"}}, ack_offset=3, exit_info=None)
        s = types.SimpleNamespace(sid=SID, name="web", _host=t, _host_ack_t=0.0)
        be._host_ended(s, {"t": "exit", "code": 0, "cause": "end"})
        self.assertTrue((hosts / SID).is_symlink(), "the link is left, not walked")
        self.assertTrue((peer / "keep").exists(), "the peer's file was not deleted through the link")
        self.assertEqual((peer / "keep").read_text(), "the peer's own file")
        self.assertTrue(any("not cleared" in l for l in be._test_logs), "remove_host_dir logged the refusal")

    def test_a_foreign_uid_directory_on_the_removal_road_is_refused_by_the_fstat_of_the_object_opened(self):
        """_rmtree_at's foreign-uid arm, driven with a stub keyed on the object (the residual-conditions commit of fork
        PR #814, 2026-09-20: round 5's mutation lens left this arm green, the one green mutation with a refusal behind
        it, and the reviewer's condition was a pin that pays the stub's cost rather than a sentence calling the arm
        impossible to drive). Two arms; each plants real directories of ours under hosts/ and lies about ONE of them:
        os.fstat answers st_uid + 1 for the descriptor whose (st_dev, st_ino) is the planted directory's, read by the
        real lstat before the patch, and answers truthfully for every other descriptor (the descent's own fstat of
        hosts/ among them, so the refusal is _rmtree_at's and not _open_dir_nofollow's). Arm `sid`: hosts/<sid>/ itself
        reads as another uid's: the walk never starts, the directory and both files in it stand, and the refusal names
        the entry and both uids. Arm `nested`: hosts/<sid>/theirs/ reads as another uid's under our verified <sid>/:
        the walk stops at it with that directory and its file untouched and <sid>/ still standing (the trailing rmdir
        never runs), the shape remove_host_dir's docstring states for a nested refusal (a sibling scandir had already
        yielded may be gone, so this arm reads nothing about it). Both: exactly one `not cleared` line is logged, with
        `belongs to uid`, and _host_ended returns without raising. An ordinary euid cannot plant a foreign directory
        under its own 0700 hosts/<sid>/, so the stub is the one way to drive the arm; the refusal is outcome-bearing at
        euid 0 or with CAP_FOWNER, where the unlinks under a foreign directory would succeed. Red with the uid arm
        deleted from _rmtree_at: both arms lose <sid>/ whole, the file under `theirs` with it."""
        real_fstat = os.fstat

        def foreign(st):
            fields = list(st)
            fields[4] = st.st_uid + 1                   # st_uid: someone else's directory at our entry
            return os.stat_result(fields)
        for arm in ("sid", "nested"):
            with self.subTest(arm=arm):
                d, be = self._be()
                sid_dir = ht.host_dir(d, SID)
                sid_dir.mkdir(parents=True, mode=0o700)
                sid_dir.parent.chmod(0o700)
                theirs = sid_dir / "theirs"
                theirs.mkdir(mode=0o700)
                (theirs / "keep").write_text("a file under the directory the stub calls another uid's")
                (sid_dir / "ours").write_text("a file of ours beside it")
                st = os.lstat(sid_dir if arm == "sid" else theirs)
                ident = (st.st_dev, st.st_ino)

                def fstat(fd):
                    st = real_fstat(fd)
                    if isinstance(fd, int) and stat.S_ISDIR(st.st_mode) and (st.st_dev, st.st_ino) == ident:
                        return foreign(st)
                    return st
                sb.write_reg(Path(d), SID, {"sid": SID, "name": "web", "alive": True})
                t = types.SimpleNamespace(hello={"host": {"pid": 7, "start": "h"}, "cli": {"pid": 8, "start": "c"}}, ack_offset=3, exit_info=None)
                s = types.SimpleNamespace(sid=SID, name="web", _host=t, _host_ack_t=0.0)
                with mock.patch.object(os, "fstat", fstat):
                    be._host_ended(s, {"t": "exit", "code": 0, "cause": "end"})
                self.assertTrue(sid_dir.is_dir(), "hosts/<sid>/ stands: the trailing rmdir never ran")
                self.assertTrue(theirs.is_dir(), "the directory the stub calls another uid's stands")
                self.assertEqual((theirs / "keep").read_text(), "a file under the directory the stub calls another uid's")
                if arm == "sid":
                    self.assertTrue((sid_dir / "ours").exists(), "a refusal at <sid> deletes nothing")
                logs = [l for l in be._test_logs if "not cleared" in l]
                self.assertEqual(len(logs), 1, be._test_logs)
                self.assertIn("belongs to uid %d, not to us (uid %d)" % (os.geteuid() + 1, os.geteuid()), logs[0])
                self.assertIn("directory %s belongs" % (SID if arm == "sid" else "theirs"), logs[0])

    def test_an_entry_that_vanishes_during_the_removal_walk_is_skipped_and_the_report_says_what_stands(self):
        """kernel-3 (round 5 of the review, 2026-09-20): remove_host_dir's `except FileNotFoundError: return True` was
        written for a hosts/<sid>/ already absent and also caught one raised INSIDE the walk, so a concurrent unlink
        under the directory (a live host still rotating its journal) had the call report "cleared" with the directory
        standing and its remaining entries in it, nothing logged, where the shutil.rmtree(ignore_errors=True) it
        replaced carried on past the missing entry. Three arms on remove_host_dir itself (both kernel callers discard
        its answer, so the answer and the log line are the contract). `vanished`: os.scandir hands the walk a listing
        one entry of which is unlinked after the listing, the stale-listing shape of the race (deterministic, where a
        real thread race needs thousands of entries): the walk skips it, the rest is removed, the directory is gone,
        the answer is True and nothing is logged. `rmdir-lies`: the trailing rmdir of <sid> reports it absent while it
        stands (os.rmdir stubbed for that one name): the answer is False and the log says the directory still stands,
        decided by a stat off the hosts/ descriptor and not by the exception. `absent`: no hosts/<sid>/ at all: True,
        nothing logged, the arm the clause was written for, pinned so the stat cannot swallow it. Red before the
        change: `vanished` answers True with the directory standing and three entries left in it; `rmdir-lies`
        answers True with nothing logged."""
        import contextlib
        import errno as _errno
        real_scandir, real_rmdir = os.scandir, os.rmdir
        for arm in ("vanished", "rmdir-lies", "absent"):
            with self.subTest(arm=arm):
                d = tempfile.mkdtemp()
                self.addCleanup(shutil.rmtree, d, True)
                logs = []
                sid_dir = ht.host_dir(d, SID)
                if arm == "absent":
                    sid_dir.parent.mkdir(parents=True, mode=0o700)
                    ident = None
                else:
                    sid_dir.mkdir(parents=True, mode=0o700)
                    sid_dir.parent.chmod(0o700)
                    for name in ("host.log", "identity.json", "journal-1.jsonl", "journal-2.jsonl"):
                        (sid_dir / name).write_text("x")
                    st = os.lstat(sid_dir)
                    ident = (st.st_dev, st.st_ino)

                def scandir(fd, ident=ident):
                    with real_scandir(fd) as it:
                        entries = list(it)
                    if isinstance(fd, int):
                        st = os.fstat(fd)
                        if (st.st_dev, st.st_ino) == ident:
                            os.unlink(entries[0].name, dir_fd=fd)     # gone between the listing and the walk
                    return contextlib.nullcontext(iter(entries))

                def rmdir(name, *a, dir_fd=None, **k):
                    if dir_fd is not None and name == SID:
                        raise FileNotFoundError(_errno.ENOENT, os.strerror(_errno.ENOENT), name)
                    return real_rmdir(name, *a, dir_fd=dir_fd, **k)
                with contextlib.ExitStack() as stack:
                    if arm == "vanished":
                        stack.enter_context(mock.patch.object(os, "scandir", scandir))
                    if arm == "rmdir-lies":
                        stack.enter_context(mock.patch.object(os, "rmdir", rmdir))
                    rv = ht.remove_host_dir(d, SID, log=logs.append)
                if arm == "vanished":
                    self.assertFalse(sid_dir.exists(), "the directory is gone: the vanished entry was skipped and the rest removed")
                    self.assertTrue(rv, "and the answer is cleared")
                    self.assertEqual(logs, [])
                elif arm == "rmdir-lies":
                    self.assertFalse(rv, "not cleared: the directory stands, whatever the rmdir said")
                    self.assertTrue(sid_dir.is_dir())
                    self.assertEqual(len(logs), 1, logs)
                    self.assertIn("not cleared", logs[0])
                    self.assertIn("still stands", logs[0])
                else:
                    self.assertTrue(rv, "already absent counts as cleared")
                    self.assertEqual(logs, [])

    def test_with_the_setting_off_an_orphan_lease_is_recovered_and_no_host_is_spawned(self):
        d, be = self._be()
        Path(d, "session-hosts").write_text("off")
        sb.write_reg(Path(d), SID, {"sid": SID, "name": "web", "alive": True, "lastSid": SID})
        sb.write_lease(d, {"sid": SID, "fsid": SID, "pid": 999999997, "start": "1", "holder": {"pid": 999999996, "start": "2", "kind": "host"}, "version": "", "t": time.time()})
        s = types.SimpleNamespace(sid=SID, name="web", _host_intent=True, _host=None, _host_is_attach=False,
                                _seed_for_dead_cli=lambda cli: None)   # the replay's watermark seed (T354): a no-op on this stand-in
        with mock.patch.object(sb, "proc_start", lambda p, run=None: None):
            out = asyncio.run(be._host_transport_for(s, types.SimpleNamespace(), (None, None, None)))
        self.assertIsNone(out, "the kill switch holds after the orphan road: a plain SDK subprocess, no new host")
        self.assertFalse(s._host_intent)
        self.assertIsNone(sb.read_lease(d, SID), "the dead host's lease is cleared")
        kinds = [json.loads(l)["kind"] for l in (Path(d) / sb.SESSION_EVENTS_FILE).read_text().splitlines()]
        self.assertIn("host.died", kinds)

    # ── the fifth review fold (commit 10) ──
    def _sdk_stub(self):
        """claude_agent_sdk with a ClaudeSDKClient that is an async context manager and nothing else: the orphan
        road imports it for the replay client; the replay itself is observed through from_journal and _replay_drain."""
        mod = types.ModuleType("claude_agent_sdk")
        class ClaudeSDKClient:
            def __init__(self, options=None, transport=None): self.transport = transport
            async def __aenter__(self): return self
            async def __aexit__(self, *a): return False
        mod.ClaudeSDKClient = ClaudeSDKClient
        return mod

    def _leftover(self, d, ident="5:h", records=3):
        hd = ht.host_dir(d, SID); hd.mkdir(parents=True, exist_ok=True)
        pid, start = ident.split(":")
        (hd / "identity.json").write_text(json.dumps({"pid": int(pid), "start": start}))
        with open(hd / "journal-0.jsonl", "w") as f:
            for i in range(records):
                f.write(json.dumps({"type": "assistant" if i % 2 == 0 else "result", "n": i}) + "\n")
        return hd

    def _kinds(self, d):
        p = Path(d) / sb.SESSION_EVENTS_FILE
        return [json.loads(l)["kind"] for l in p.read_text().splitlines()] if p.exists() else []

    def test_with_the_setting_off_a_lease_less_leftover_is_replayed_and_cleared(self):
        # item 1 (medium): the connect guard keyed on the lease alone, so a host that ended unattended (its lease
        # removed) left its unconsumed tail and its directory behind for good with the setting off
        d, be = self._be()
        Path(d, "session-hosts").write_text("off")
        sb.write_reg(Path(d), SID, {"sid": SID, "name": "web", "alive": True, "lastSid": SID,
                                     "hostAck": {"host": "5:h", "cli": "6:c", "offset": 0}, "hostLogPos": 3})
        hd = self._leftover(d, "5:h", records=3)
        s = types.SimpleNamespace(sid=SID, name="web", _host_intent=True, _host=None, _host_is_attach=False,
                                _seed_for_dead_cli=lambda cli: None)   # the replay's watermark seed (T354): a no-op on this stand-in
        self.assertTrue(be._host_lease_applies(s), "a leftover directory is a host that held this session: the road runs whatever the setting")
        acks, drained = [], []
        async def drain(sess, client, msg_classes): drained.append(client.transport)
        with mock.patch.dict(sys.modules, {"claude_agent_sdk": self._sdk_stub()}), \
             mock.patch.object(ht.HostTransport, "from_journal", classmethod(lambda cls, hdir, ack=-1, **kw: acks.append(ack) or types.SimpleNamespace(hdir=hdir))), \
             mock.patch.object(be, "_replay_drain", drain):
            out = asyncio.run(be._host_transport_for(s, types.SimpleNamespace(), (None, None, None)))
        self.assertIsNone(out, "the kill switch still holds: a plain SDK subprocess after the replay")
        self.assertEqual(acks, [0], "the tail past the ack this host's identity vouches for was replayed")
        self.assertEqual(len(drained), 1)
        self.assertIn("host.tail-replayed", self._kinds(d))
        self.assertFalse(hd.exists(), "the directory is cleared after the replay")
        reg = sb.read_reg(Path(d), SID) or {}
        self.assertNotIn("hostAck", reg); self.assertNotIn("hostLogPos", reg)
        s2 = types.SimpleNamespace(sid=SID, name="web")
        self.assertFalse(be._host_lease_applies(s2), "and nothing is left to apply")

    def test_a_leftover_with_nothing_past_the_ack_files_no_tail_replayed_row(self):
        # item 4: a failed spawn's leftovers (an empty journal, an identity, no lease) are cleared quietly
        d, be = self._be()
        sb.write_reg(Path(d), SID, {"sid": SID, "name": "web", "alive": True, "lastSid": SID,
                                     "hostAck": {"host": "5:h", "cli": "6:c", "offset": 2}})
        hd = self._leftover(d, "5:h", records=3)          # offsets 0..2, all acknowledged
        s = types.SimpleNamespace(sid=SID, name="web", _host_intent=True, _host=None, _host_is_attach=False,
                                _seed_for_dead_cli=lambda cli: None)   # the replay's watermark seed (T354): a no-op on this stand-in
        with mock.patch.dict(sys.modules, {"claude_agent_sdk": self._sdk_stub()}), \
             mock.patch.object(be, "_replay_drain", mock.AsyncMock()):
            asyncio.run(be._host_orphan_recover(s, types.SimpleNamespace(), None, (None, None, None), died=False))
        self.assertNotIn("host.tail-replayed", self._kinds(d), "nothing to replay, no row")
        self.assertFalse(hd.exists())
        (hd2 := self._leftover(d, "5:h", records=0))
        with mock.patch.dict(sys.modules, {"claude_agent_sdk": self._sdk_stub()}), \
             mock.patch.object(be, "_replay_drain", mock.AsyncMock()):
            asyncio.run(be._host_orphan_recover(s, types.SimpleNamespace(), None, (None, None, None), died=False))
        self.assertNotIn("host.tail-replayed", self._kinds(d), "an empty journal: no row either")
        self.assertFalse(hd2.exists())

    def test_the_orphan_road_trusts_hostack_only_for_the_host_that_wrote_the_identity(self):
        # item 7: host A's acknowledged offset must not seed host B's replay
        d, be = self._be()
        sb.write_reg(Path(d), SID, {"sid": SID, "name": "web", "alive": True, "lastSid": SID,
                                     "hostAck": {"host": "1:a", "cli": "2:c", "offset": 1}})
        self._leftover(d, "9:b", records=3)
        seeds = []
        s = types.SimpleNamespace(sid=SID, name="web", _host_intent=True, _host=None, _host_is_attach=False,
                                _seed_for_dead_cli=seeds.append)   # the replay's watermark seed (T354): recorded here
        acks = []
        capture = classmethod(lambda cls, hdir, ack=-1, **kw: acks.append(ack) or types.SimpleNamespace(hdir=hdir))
        with mock.patch.dict(sys.modules, {"claude_agent_sdk": self._sdk_stub()}), \
             mock.patch.object(ht.HostTransport, "from_journal", capture), mock.patch.object(be, "_replay_drain", mock.AsyncMock()):
            asyncio.run(be._host_orphan_recover(s, types.SimpleNamespace(), None, (None, None, None), died=False))
        self.assertEqual(acks, [-1], "another host's ack: the whole journal is replayed")
        sb.write_reg(Path(d), SID, {"sid": SID, "name": "web", "alive": True, "lastSid": SID,
                                     "hostAck": {"host": "9:b", "cli": "2:c", "offset": 1}})
        self._leftover(d, "9:b", records=3)
        with mock.patch.dict(sys.modules, {"claude_agent_sdk": self._sdk_stub()}), \
             mock.patch.object(ht.HostTransport, "from_journal", capture), mock.patch.object(be, "_replay_drain", mock.AsyncMock()):
            asyncio.run(be._host_orphan_recover(s, types.SimpleNamespace(), None, (None, None, None), died=False))
        self.assertEqual(acks, [-1, 1], "this host's ack: the replay starts past it")
        self.assertEqual(seeds, ["", "2:c"], "the watermark seed runs before each replay (T354 M7), the CLI named by hostAck only when the ack is this host's")

    def test_a_host_this_kernel_ended_gets_a_bounded_wait_for_its_lease_and_no_host_died_row(self):
        # item 6: the behaviour, not the bookkeeping: an `end` this kernel asked for races the reconnect; the stale
        # lease is waited out (bounded), never walked as a death
        d, be = self._be()
        Path(d, "session-hosts").write_text("off")
        sb.write_reg(Path(d), SID, {"sid": SID, "name": "web", "alive": True, "lastSid": SID})
        sb.write_lease(d, {"sid": SID, "fsid": SID, "pid": 999999997, "start": "1", "holder": {"pid": 999999996, "start": "2", "kind": "host"}, "version": "", "t": time.time()})
        be._host_recently_ended[SID] = "999999996:2"
        s = types.SimpleNamespace(sid=SID, name="web", _host_intent=True, _host=None, _host_is_attach=False,
                                _seed_for_dead_cli=lambda cli: None)   # the replay's watermark seed (T354): a no-op on this stand-in
        import threading
        remover = threading.Timer(0.4, lambda: sb.remove_lease(d, SID)); remover.start()
        try:
            t0 = time.time()
            with mock.patch.object(sb, "proc_start", lambda p, run=None: None), \
                 mock.patch.object(be, "_host_orphan_recover", mock.AsyncMock()) as rec:
                out = asyncio.run(be._host_transport_for(s, types.SimpleNamespace(), (None, None, None)))
        finally:
            remover.cancel()
        self.assertIsNone(out)
        self.assertGreaterEqual(time.time() - t0, 0.35, "the connect waited for the lease's removal")
        self.assertIsNone(sb.read_lease(d, SID), "the host removed its lease; nothing of ours reaped it")
        self.assertFalse(rec.called, "no orphan road: the host ended, it did not die")
        self.assertNotIn("host.died", self._kinds(d))
        self.assertNotIn(SID, be._host_recently_ended)

    def test_an_attach_that_never_completes_stands_the_session_down_instead_of_the_crash_heal(self):
        # item 3: past the retry bound on a wedged live host the failure used to run crash.heal then crash.loop and
        # queue the crash-resume nudge for a CLI that never died
        d, be = self._be()
        sb.write_reg(Path(d), SID, {"sid": SID, "name": "web", "alive": True, "lastSid": SID, "queue": ["kept"]})
        s = types.SimpleNamespace(sid=SID, name="web", backend=be, inflight=1, detached=False, _reconnect=True,
                                  _host_attach_retries=4, _host=types.SimpleNamespace(hello={"host": {"pid": 5, "start": "h"}}))
        sb.SdkSession._host_stand_down(s, TimeoutError("initialize"))
        self.assertTrue(s.detached, "detached: the session-gone path settles nothing and heals nothing")
        self.assertFalse(s._reconnect); self.assertEqual((s.inflight, s._host_attach_retries), (0, 0))
        kinds = self._kinds(d)
        self.assertIn("host.attach-failed", kinds); self.assertNotIn("crash.heal", kinds)
        rows = [json.loads(l) for l in (Path(d) / "states" / (SID + ".jsonl")).read_text().splitlines()]
        self.assertEqual(rows[-1]["state"], "waiting", "waiting on its host; the next send tries the attach again")
        self.assertEqual((sb.read_reg(Path(d), SID) or {}).get("queue"), ["kept"], "no crash-resume nudge")

    def _marked(self, d, holder="999999996:2", **reg):
        base = {"sid": SID, "name": "web", "alive": True, "lastSid": SID, "hostAttachFailed": {"host": holder, "t": 1.0, "tries": 4}}
        base.update(reg)
        sb.write_reg(Path(d), SID, base)

    def _host_lease(self, d, cli=999999997, host=999999996, t=None):
        sb.write_lease(d, {"sid": SID, "fsid": SID, "pid": cli, "start": "1", "holder": {"pid": host, "start": "2", "kind": "host"},
                           "version": "", "t": time.time() if t is None else t})

    _LEASE_CASES = [
        # name, lease (None = absent), live pids, holds
        ("attach by the marked host", dict(cli=999999997, host=999999996), {999999997: "1", 999999996: "2"}, True),
        ("attach by another host", dict(cli=999999997, host=999999995), {999999997: "1", 999999995: "2"}, False),
        ("the host is gone (holder-gone)", dict(cli=999999997, host=999999996), {999999997: "1"}, False),
        ("the CLI is gone (no-live-process)", dict(cli=999999997, host=999999996), {999999996: "2"}, False),
        ("a stale beat", dict(cli=999999997, host=999999996, t=time.time() - 100), {999999997: "1", 999999996: "2"}, False),
        ("no lease at all", None, {999999997: "1", 999999996: "2"}, False),
    ]

    def test_the_stand_down_marker_holds_only_for_a_live_lease_by_the_very_host(self):
        # the commit-12 review's first item: the guard compared identities with no liveness check, so a killed host's
        # stale lease kept every automatic ensure standing down and the orphan road never ran. _ensure is driven on a
        # FRESH marker per state (the commit-13 review's fifth item: a helper call first had already dropped it)
        for name, lease, starts, holds in self._LEASE_CASES:
            with self.subTest("ensure: " + name):
                d, be = self._be()
                self._marked(d)
                if lease:
                    self._host_lease(d, **lease)
                started = []
                with mock.patch.object(sb, "proc_start", lambda p, run=None, st=starts: st.get(p)), \
                     mock.patch.object(sb.SdkSession, "start", lambda self: started.append(self.sid)):
                    out = be._ensure(SID)
                reg = sb.read_reg(Path(d), SID) or {}
                if holds:
                    self.assertIsNone(out, "stands down"); self.assertIn("hostAttachFailed", reg, "the marker stays")
                    self.assertEqual(started, [])
                else:
                    self.assertIsNotNone(out, "new information: the session starts (the orphan road or a fresh spawn runs in its thread)")
                    self.assertNotIn("hostAttachFailed", reg, "the marker is dropped on the way in")
                    self.assertEqual(started, [SID])
        for name, lease, starts, holds in self._LEASE_CASES:
            with self.subTest("helper: " + name):
                d, be = self._be()
                self._marked(d)
                if lease:
                    self._host_lease(d, **lease)
                with mock.patch.object(sb, "proc_start", lambda p, run=None, st=starts: st.get(p)):
                    self.assertEqual(be._attach_stand_down_holds(SID), holds)
                self.assertEqual("hostAttachFailed" in (sb.read_reg(Path(d), SID) or {}), holds, "the helper drops a marker that no longer holds")

    def test_a_stand_down_with_no_live_attach_lease_writes_no_marker(self):
        # the fifth item: a host that left in the window before the stand-down read its lease made a marker naming
        # 'None:None', which every later lease-less ensure matched forever
        for lease_state, lease, starts in (("none", None, {}), ("orphan", dict(cli=999999997, host=999999996), {})):
            with self.subTest(lease_state):
                d, be = self._be()
                sb.write_reg(Path(d), SID, {"sid": SID, "name": "web", "alive": True, "lastSid": SID})
                if lease:
                    self._host_lease(d, **lease)
                s = types.SimpleNamespace(sid=SID, name="web", backend=be, inflight=1, detached=False, _reconnect=True,
                                          _host_attach_retries=4, _host=types.SimpleNamespace(hello={"host": {"pid": 5, "start": "h"}}))
                with mock.patch.object(sb, "proc_start", lambda p, run=None, st=starts: st.get(p)):
                    sb.SdkSession._host_stand_down(s, TimeoutError("initialize"))
                reg = sb.read_reg(Path(d), SID) or {}
                self.assertNotIn("hostAttachFailed", reg, "no marker without a live host lease: the next connect walks the orphan road")
                self.assertTrue(s.detached)
        # and WITH a live attach lease the marker names the lease holder
        d, be = self._be()
        sb.write_reg(Path(d), SID, {"sid": SID, "name": "web", "alive": True, "lastSid": SID})
        self._host_lease(d)
        s = types.SimpleNamespace(sid=SID, name="web", backend=be, inflight=1, detached=False, _reconnect=True,
                                  _host_attach_retries=4, _host=types.SimpleNamespace(hello={"host": {"pid": 5, "start": "h"}}))
        with mock.patch.object(sb, "proc_start", lambda p, run=None: {999999997: "1", 999999996: "2"}.get(p)):
            sb.SdkSession._host_stand_down(s, TimeoutError("initialize"))
        self.assertEqual(((sb.read_reg(Path(d), SID) or {}).get("hostAttachFailed") or {}).get("host"), "999999996:2")

    def test_an_automatic_send_is_queued_behind_the_stand_down_and_the_users_send_lifts_it(self):
        # the commit-12 review's second item (only the user's message lifts) and the commit-13 review's first (a refused
        # automatic message was DROPPED after its sender's ledger row had said fired): the stand-down refuses the
        # attach, never the message: an automatic send lands in the persisted queue mirror and rides the attach the
        # user's next message makes, in order
        d, be = self._be()
        self._marked(d); self._host_lease(d)
        started = []
        with mock.patch.object(sb, "proc_start", lambda p, run=None: {999999997: "1", 999999996: "2"}.get(p)), \
             mock.patch.object(sb.SdkSession, "start", lambda self: started.append(self.sid)):
            self.assertTrue(be.send(SID, "<!-- romp-injected --><!-- romp-auto --> a nudge"), "accepted: queued, not dropped")
            self.assertTrue(be.send(SID, "a watch notice <!-- romp-tag: watch -->"))
            reg = sb.read_reg(Path(d), SID) or {}
            self.assertEqual(reg.get("queue"), ["<!-- romp-injected --><!-- romp-auto --> a nudge", "a watch notice <!-- romp-tag: watch -->"])
            self.assertEqual([m["text"] for m in reg.get("queueMeta")], reg["queue"], "the mirror's meta aligns with the queue")
            self.assertIn("hostAttachFailed", reg, "the marker stands"); self.assertEqual(started, [], "no thread, no attach")
            self.assertEqual([q["md"] for q in be.pending_queued_meta(SID)], reg["queue"], "the chat shows them queued")
            self.assertFalse(be.deliver(SID, "peer mail"), "postal mail is refused as before (the bus keeps its copy)")
            self.assertTrue(be.send(SID, "the user's words", user=True))
        reg = sb.read_reg(Path(d), SID) or {}
        self.assertNotIn("hostAttachFailed", reg, "the user's message lifts the marker before the ensure")
        self.assertEqual(started, [SID], "one start, for the user's send")
        s = be.sessions[SID]
        self.assertEqual(s._pending[:2], ["<!-- romp-injected --><!-- romp-auto --> a nudge", "a watch notice <!-- romp-tag: watch -->"],
                         "the session seeds the queued automatic messages first, then the user's")
        self.assertEqual(s._pending[2], "the user's words")

    def test_a_queued_send_that_races_a_lift_lands_in_the_live_session(self):
        # the commit-14 review's first item: the queue-behind appended to the mirror after an unlocked check; a user's
        # send lifting the marker in that window started a session whose queue seed had already been read, and the
        # next _persist_queue erased the automatic text. The re-check under _reg_lock declines and send() falls through.
        d, be = self._be()
        self._marked(d); self._host_lease(d)
        got = []
        live = types.SimpleNamespace(sid=SID, thread=types.SimpleNamespace(is_alive=lambda: True),
                                     enqueue=lambda t, qid=None, qts=None: got.append(t))
        real_holds = be._attach_stand_down_holds
        def holds_then_lift(sid, reg=None):
            r = real_holds(sid, reg)
            be._lift_attach_stand_down(sid)            # the user's send wins the race: marker gone, session live
            be.sessions[sid] = live
            return r
        with mock.patch.object(sb, "proc_start", lambda p, run=None: {999999997: "1", 999999996: "2"}.get(p)), \
             mock.patch.object(be, "_attach_stand_down_holds", holds_then_lift):
            self.assertTrue(be.send(SID, "<!-- romp-injected --> a nudge"))
        self.assertEqual(got, ["<!-- romp-injected --> a nudge"], "enqueued on the live session, not landed in a mirror")
        self.assertEqual((sb.read_reg(Path(d), SID) or {}).get("queue") or [], [], "nothing written to the mirror")

    def test_a_dead_session_refuses_an_automatic_send_before_the_stand_down_is_consulted(self):
        # the second item: the alive check lived inside _ensure, unreachable while the marker held, so a stood-down
        # session the user had ended kept accepting automatic messages into a dead reg's mirror
        d, be = self._be()
        self._marked(d, alive=False); self._host_lease(d)
        with mock.patch.object(sb, "proc_start", lambda p, run=None: {999999997: "1", 999999996: "2"}.get(p)):
            self.assertFalse(be.send(SID, "<!-- romp-injected --> a nudge"), "refused, as e030cd45 did: the watch row retries")
        self.assertEqual((sb.read_reg(Path(d), SID) or {}).get("queue") or [], [])

    def test_kill_drops_the_marker_and_ends_the_host_a_stood_down_session_left_running(self):
        # the second item's other half: kill() on a stood-down session with no object flipped alive and left the
        # host and its CLI running under a live lease; now it drops the marker and ends the host through its lease
        d, be = self._be()
        self._marked(d); self._host_lease(d)
        ended = []
        with mock.patch.object(sb, "proc_start", lambda p, run=None: {999999997: "1", 999999996: "2"}.get(p)), \
             mock.patch.object(be, "_end_host_by_lease", lambda sid: ended.append(sid) or True):
            self.assertTrue(be.kill(SID))
        reg = sb.read_reg(Path(d), SID) or {}
        self.assertFalse(reg.get("alive")); self.assertNotIn("hostAttachFailed", reg)
        self.assertEqual(ended, [SID], "the live host is ended through its lease")
        # and the real helper declines when no live host lease holds
        d2, be2 = self._be()
        sb.write_reg(Path(d2), SID, {"sid": SID, "name": "web", "alive": True})
        self.assertFalse(be2._end_host_by_lease(SID))

    def test_two_automatic_messages_with_the_same_words_are_both_queued(self):
        # the fourth item: a by-text dedupe dropped a legitimately repeated notice and reported it accepted
        d, be = self._be()
        self._marked(d); self._host_lease(d)
        with mock.patch.object(sb, "proc_start", lambda p, run=None: {999999997: "1", 999999996: "2"}.get(p)):
            self.assertTrue(be.send(SID, "romp watch: the condition holds"))
            self.assertTrue(be.send(SID, "romp watch: the condition holds"))
        self.assertEqual((sb.read_reg(Path(d), SID) or {}).get("queue"), ["romp watch: the condition holds"] * 2)

    def test_kill_sends_end_to_the_stood_down_host_and_concurrent_ends_start_one_thread(self):
        # the commit-15 review's first item: the end-by-lease connected and closed with no request written, and a
        # transport whose initialize was never answered DETACHES on close (the host kept its CLI); it sends `end`
        # with the kill bound now. And the commit-17 review's first item: two Ends for one sid at once (the
        # dashboard's and `romp end`) opened two sockets; check, create, register and start run under one lock
        d, be = self._be(short=True)
        self._marked(d); self._host_lease(d)
        host, stop = self._serve_fake_host(d)
        import threading
        try:
            with mock.patch.object(sb, "proc_start", lambda p, run=None: {999999997: "1", 999999996: "2", 999999995: "3", 999999994: "4"}.get(p)):
                self.assertEqual(ht.host_lease_state(sb.read_lease(d, SID), time.time()), "attach")
                self.assertTrue(be.kill(SID))
                th = be._end_threads[SID]
                th.join(10)
                self.assertFalse(th.is_alive(), "the end thread finishes: the fake host answers `end` with an exit frame")
                kinds = [f.get("t") for f in host.got]
                self.assertIn("end", kinds, "the host receives END, not a detach: %r; log: %r" % (kinds, be._test_logs[-6:]))
                self.assertNotIn("detach", kinds)
                self.assertEqual(next(f for f in host.got if f.get("t") == "end")["grace"], sh.END_GRACE_KILL_S)
                self.assertNotIn("hostAttachFailed", sb.read_reg(Path(d), SID) or {})
                # the end thread is STARTED under the backend's lock (an unstarted thread reads as not alive to a
                # concurrent checker, so check, create, register and start share one acquisition)
                class Held:
                    def __init__(self, lock): self.lock, self.depth = lock, 0
                    def __enter__(self): self.lock.__enter__(); self.depth += 1; return self
                    def __exit__(self, *a): self.depth -= 1; return self.lock.__exit__(*a)
                held = be._lock = Held(be._lock)
                starts = []
                real_start = threading.Thread.start
                def start_recording(thread):
                    if thread.name.startswith("end-host:"):
                        starts.append(held.depth > 0)
                    return real_start(thread)
                # a NEW host holds the lease (the first was told to end and a later End for it opens no socket): its End starts a thread
                lease = sb.read_lease(d, SID); lease["holder"] = dict(lease["holder"], pid=999999995, start="3"); sb.write_lease(d, lease)
                with mock.patch.object(threading.Thread, "start", start_recording):
                    self.assertTrue(be._end_host_by_lease(SID))
                    be._end_threads[SID].join(10)
                self.assertEqual(starts, [True], "the end thread starts while the lock is held")
                # two concurrent Ends for a host not yet told to end: one thread, one socket
                lease = sb.read_lease(d, SID); lease["holder"] = dict(lease["holder"], pid=999999994, start="4"); sb.write_lease(d, lease)
                host.got.clear()
                results = []
                racers = [threading.Thread(target=lambda: results.append(be._end_host_by_lease(SID))) for _ in range(2)]
                for r in racers: r.start()
                for r in racers: r.join(5)
                be._end_threads[SID].join(10)
                self.assertEqual(results, [True, True])
                self.assertEqual(sum(1 for f in host.got if f.get("t") == "attach"), 1, "one socket for two concurrent Ends: %r" % [f.get("t") for f in host.got])
                self.assertEqual(sum(1 for l in be._test_logs if "already under way" in l or "already told to end" in l), 1,
                                 "the second End was refused a socket whether the first thread was still alive or had finished: %r" % be._test_logs[-4:])
        finally:
            stop()

    def test_a_second_end_after_the_first_finished_opens_no_socket_and_a_new_holder_ends_normally(self):
        # main's Python 3.11 job (2026-09-12): two concurrent Ends opened two sockets ("attach, end, attach, end") when the
        # first thread had already finished; the guard remembers the lease holder it told to end
        d, be = self._be(short=True)
        self._marked(d); self._host_lease(d)
        host, stop = self._serve_fake_host(d)
        try:
            with mock.patch.object(sb, "proc_start", lambda p, run=None: {999999997: "1", 999999996: "2", 999999995: "3"}.get(p)):
                self.assertTrue(be._end_host_by_lease(SID))
                be._end_threads[SID].join(10)
                self.assertEqual([f.get("t") for f in host.got], ["attach", "end"])
                self.assertTrue(be._end_host_by_lease(SID), "a later End for the same host is a no-op that reports done")
                self.assertEqual([f.get("t") for f in host.got], ["attach", "end"], "no second socket to a host already told to end")
                self.assertEqual(sum(1 for l in be._test_logs if "already told to end" in l), 1)
                # a NEW host took the lease under the same sid: it is a different holder and ends normally
                lease = sb.read_lease(d, SID)
                lease["holder"] = dict(lease["holder"], pid=999999995, start="3")
                sb.write_lease(d, lease)
                self.assertTrue(be._end_host_by_lease(SID))
                be._end_threads[SID].join(10)
                self.assertEqual([f.get("t") for f in host.got], ["attach", "end", "attach", "end"], "the new holder is ended")
        finally:
            stop()

    def test_an_end_by_lease_gives_up_on_a_host_that_never_says_hello_and_a_later_end_is_not_blocked(self):
        # the commit-17 review's third item: the 5 s bound on hello had no test
        d, be = self._be(short=True)
        self._marked(d); self._host_lease(d)
        host, stop = self._serve_fake_host(d, silent=True)
        try:
            with mock.patch.object(sb, "proc_start", lambda p, run=None: {999999997: "1", 999999996: "2"}.get(p)):
                self.assertTrue(be._end_host_by_lease(SID))
                first = be._end_threads[SID]
                first.join(12)
                self.assertFalse(first.is_alive(), "the thread gives up on the silent host and exits")
                self.assertTrue(any("no hello within" in l for l in be._test_logs), "the timeout is logged: %r" % be._test_logs[-4:])
                self.assertTrue(be._end_host_by_lease(SID))
                self.assertIsNot(be._end_threads[SID], first, "a later End starts a fresh thread: no stuck 'already under way'")
                be._end_threads[SID].join(12)
        finally:
            stop()

    def test_a_message_queued_between_the_ensure_read_and_the_insert_reaches_the_live_session(self):
        # the third item: _ensure seeded the SdkSession from a reg dict read before the insert; a queue-behind on
        # _reg_lock alone could append in between (no session yet), and the seed missed it. The seed is re-read
        # under _reg_lock after the insert.
        d, be = self._be()
        sb.write_reg(Path(d), SID, {"sid": SID, "name": "web", "alive": True, "lastSid": SID, "cwd": d, "queue": ["first"]})
        late, qid = "<!-- romp-injected --> a nudge", "echo:" + "b" * 32
        def move_between(sid, reg=None):
            with be._reg_lock:                          # what a racing writer does after _ensure's read: a queue-behind
                cur = sb.read_reg(Path(d), sid)         # APPENDS with an identity; the boot reconcile PREPENDS its nudge
                cur["queue"] = [sb.CRASH_RESUME_NUDGE] + (cur.get("queue") or []) + [late]
                cur["queueMeta"] = [{"text": late, "qid": qid, "qts": 5}]
                sb.write_reg(Path(d), sid, cur)
            return False
        with mock.patch.object(be, "_attach_stand_down_holds", move_between), \
             mock.patch.object(sb.SdkSession, "start", lambda self: None):
            s = be._ensure(SID)
        self.assertIsNotNone(s)
        self.assertEqual(list(s._pending), [sb.CRASH_RESUME_NUDGE, "first", late], "the live list is the mirror, in mirror order (a prepend and an append)")
        self.assertEqual([m and m.get("qid") for m in s._pending_meta], [None, None, qid], "the late text's identity lands on it, not on a seed copy")

    def test_a_boot_leaves_a_stood_down_session_alone_and_counts_no_attach(self):
        # the fourth item: the boot counted an attach, added the sid to the boot set and wrote the reconcile.boot row
        # before the stagger's ensure refused; the attach a later send made then filed host.attached with boot=True
        d, be = self._be()
        self._marked(d, cwd=d, mode="default", effort="high")
        self._host_lease(d)
        started = []
        with mock.patch.object(sb, "proc_start", lambda p, run=None: {999999997: "1", 999999996: "2"}.get(p)), \
             mock.patch.object(sb.SdkSession, "start", lambda self: started.append(self.sid)):
            be._boot_reconcile([sb.read_reg(Path(d), SID)])
        self.assertNotIn(SID, be._boot_attach_sids, "no boot-attach entry for a session the boot stood down from")
        self.assertEqual(started, [], "not started at boot")
        self.assertIn("hostAttachFailed", sb.read_reg(Path(d), SID) or {}, "a boot is not new information; the marker stays")
        self.assertTrue(any("stays stood down" in l for l in be._test_logs), "the boot says so")

    # ── the read roads through the descent (the round-7 second addendum of fork PR #814's review, 2026-09-20) ──
    # Each case plants the swap the reviewer's ruling names: hosts/ is a symlink to a directory of a peer's that holds a
    # forged <sid>/ (identity.json, a journal, host.log), and the kernel's read on one road runs. Red at the addendum's
    # head, where each read took a PATH and so read the peer's content through the link; green once the read takes a
    # name under the descriptors of open_host_dirs_if_present, which refuses the link before anything under it is read
    # and files one host.directory-refused row with the remedy.

    def _peer(self, d, identity=None, journal=0, host_log=()):
        """A peer's directory outside hosts/ with a forged <sid>/ in it, and hosts/ swapped for a symlink to it."""
        peer = Path(d) / "peer"
        (peer / SID).mkdir(parents=True, mode=0o755)
        if identity is not None:
            (peer / SID / "identity.json").write_text(json.dumps(identity))
        if journal:
            with open(peer / SID / "journal-0.jsonl", "w") as f:
                for i in range(journal):
                    f.write(json.dumps({"type": "assistant" if i % 2 == 0 else "result", "n": i, "peer": True}) + "\n")
        if host_log:
            (peer / SID / "host.log").write_text("".join(json.dumps(r) + "\n" for r in host_log))
        hosts = Path(d) / "hosts"
        self.assertFalse(hosts.exists(), "a fresh root: nothing of ours at hosts/")
        hosts.symlink_to(peer)
        return peer, hosts

    def _refusal_rows(self, d):
        p = Path(d) / sb.SESSION_EVENTS_FILE
        rows = [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []
        return [r for r in rows if r["kind"] == "host.directory-refused"]

    def test_the_lease_applies_read_refuses_a_swapped_hosts_and_vouches_for_no_host(self):
        """The connect road with hosts OFF: _host_lease_applies asks whether a host held the session by identity.json's
        existence. Through the addendum's head that was `(hdir / "identity.json").exists()`, by path, so the peer's
        identity.json behind the link answered True and the session took the host road over the peer's directory. Now
        the read takes a name under the read roads' descent, which refuses the link: False, one host.directory-refused
        row naming the link with the read roads' remedy (no 0700 clause: the mode is not that descent's condition), and
        the session runs as the kernel child the setting asks for. Red before: `True is not False`."""
        d, be = self._be()
        Path(d, "session-hosts").write_text("off")
        peer, hosts = self._peer(d, identity={"pid": 7, "start": "p"})
        applies = be._host_lease_applies(types.SimpleNamespace(sid=SID, name="web"))
        self.assertIs(applies, False, "a directory the descent refuses vouches for no host; through the link the peer's identity.json said True")
        rows = self._refusal_rows(d)
        self.assertEqual(len(rows), 1, self._kinds(d))
        self.assertEqual(self._kinds(d), ["host.directory-refused"])
        self.assertTrue(rows[0]["text"].startswith("the session host for web may have left records this kernel does not read: hosts directory %s is a symlink, not a directory. " % hosts), rows[0]["text"])
        self.assertIn("A hosts/ or hosts/<sid>/ that is not a directory this user owns is refused; replace it with a directory, or point the state root elsewhere (ROMP_STATE_DIR or XDG_STATE_HOME)", rows[0]["text"])
        self.assertNotIn("at 0700", rows[0]["text"], "the read roads' descent does not check the mode, so its remedy does not ask for it")
        self.assertTrue(hosts.is_symlink(), "the link is left, not replaced")
        self.assertEqual((peer / SID / "identity.json").read_text(), json.dumps({"pid": 7, "start": "p"}), "the peer's file untouched")

    def test_the_leftover_trigger_refuses_a_swapped_hosts_before_the_spawn_and_replays_nothing_of_the_peers(self):
        """The connect road with hosts ON and no lease: the leftover trigger asks whether hosts/<sid>/ stands. Through
        the addendum's head that was `hdir.exists()`, by path, so the peer's <sid>/ behind the link put the peer's
        leftover on the orphan road, whose reads (identity.json, the journal glob, the replay transport) took the link
        and replayed the peer's journal into the session before the spawn road's own helper refused the link. Now the
        trigger's descent refuses the link first: the launch is refused as the spawn road refuses its own (one
        host.directory-refused row with the directory remedy, the launch error), the replay transport is never built,
        no spawn runs. Red before: the replay transport was built over the peer's directory (`[-1] != []`), and a
        host.tail-replayed row stood beside the refusal."""
        d, be = self._be()
        peer, hosts = self._peer(d, identity={"pid": 7, "start": "p"}, journal=3)
        sb.write_reg(Path(d), SID, {"sid": SID, "name": "web", "alive": True, "lastSid": SID})
        s = types.SimpleNamespace(sid=SID, name="web", _host_intent=True, _host=None, _host_is_attach=False,
                                  _seed_for_dead_cli=lambda cli: None, _options_login="", _host_end_grace=None,
                                  _on_cli_stderr=lambda line: None)
        acks, spawned = [], []
        with mock.patch.dict(sys.modules, {"claude_agent_sdk": self._sdk_stub()}), \
             mock.patch.object(ht.HostTransport, "from_journal", classmethod(lambda cls, hdir, ack=-1, **kw: acks.append(ack) or types.SimpleNamespace(hdir=hdir))), \
             mock.patch.object(be, "_replay_drain", mock.AsyncMock()), \
             mock.patch.object(be, "_spawn_host", lambda *a, **k: spawned.append(a) or types.SimpleNamespace(poll=lambda: 1, returncode=1, pid=1)):
            with self.assertRaises(sb.CLIConnectionErrorLike) as cm:
                asyncio.run(be._host_transport_for(s, types.SimpleNamespace(), (None, None, None)))
        self.assertEqual(acks, [], "nothing of the peer's is replayed: the replay transport was never built")
        self.assertEqual(spawned, [], "no spawn: the launch is refused at the trigger")
        self.assertEqual(self._kinds(d), ["host.directory-refused"], "one row, the refusal's kind, no host.tail-replayed")
        msg = str(cm.exception)
        self.assertTrue(msg.startswith("the session host was not started: hosts directory %s is a symlink, not a directory. A hosts/ or hosts/<sid>/ that is not a directory this user owns at 0700 is refused" % hosts), msg)
        self.assertTrue(hosts.is_symlink(), "the link is left, not replaced")
        self.assertEqual(sorted(os.listdir(peer / SID)), ["identity.json", "journal-0.jsonl"], "the peer's directory holds what the peer put there")

    def test_the_orphan_road_refuses_a_swapped_hosts_and_replays_nothing_of_the_peers(self):
        """The orphan road itself (_host_orphan_recover, the lease-less leftover arm): it reads identity.json to decide
        whether the registry's hostAck names the host that wrote it, then replays the journal past that offset. Through
        the addendum's head both took a path: the peer's identity.json, forged to the registry's hostAck, vouched for
        the offset, and the peer's journal was replayed from it into the session. Now identity.json is read by name
        under the read roads' descent, which refuses the link: one host.directory-refused row saying the journal is not
        replayed, no replay transport, no watermark seed for the peer's CLI, and the road still clears the lease and
        the registry's ack and asks the removal road, which refuses the same link on its own descent and logs it. Red
        before: `[1] != []`, the peer's journal replayed from the offset the peer's identity vouched for."""
        d, be = self._be()
        sb.write_reg(Path(d), SID, {"sid": SID, "name": "web", "alive": True, "lastSid": SID,
                                     "hostAck": {"host": "7:p", "cli": "8:c", "offset": 1}})
        peer, hosts = self._peer(d, identity={"pid": 7, "start": "p"}, journal=3)
        seeds, acks = [], []
        s = types.SimpleNamespace(sid=SID, name="web", _host_intent=True, _host=None, _host_is_attach=False, _seed_for_dead_cli=seeds.append)
        capture = classmethod(lambda cls, hdir, ack=-1, **kw: acks.append(ack) or types.SimpleNamespace(hdir=hdir))
        with mock.patch.dict(sys.modules, {"claude_agent_sdk": self._sdk_stub()}), \
             mock.patch.object(ht.HostTransport, "from_journal", capture), mock.patch.object(be, "_replay_drain", mock.AsyncMock()):
            asyncio.run(be._host_orphan_recover(s, types.SimpleNamespace(), None, (None, None, None), died=False))
        self.assertEqual(acks, [], "nothing of the peer's is replayed: the replay transport was never built")
        self.assertEqual(seeds, [], "no watermark seed for a CLI the peer's identity named")
        self.assertEqual(self._kinds(d), ["host.directory-refused"], "one row, the refusal's kind; no host.tail-replayed")
        text = self._refusal_rows(d)[0]["text"]
        self.assertTrue(text.startswith("the session host for web is gone, and its journal is not replayed: hosts directory %s is a symlink, not a directory. " % hosts), text)
        self.assertIn("this user owns is refused", text)
        self.assertTrue(any("not cleared" in l for l in be._test_logs), "the removal road refused the same link and said so")
        reg = sb.read_reg(Path(d), SID) or {}
        self.assertNotIn("hostAck", reg, "the road still drops the ack it could not vouch for")
        self.assertTrue(hosts.is_symlink(), "the link is left, not replaced")
        self.assertEqual(sorted(os.listdir(peer / SID)), ["identity.json", "journal-0.jsonl"], "the peer's directory holds what the peer put there")

    def test_the_served_road_refuses_a_swapped_hosts_and_files_none_of_the_peers_rows(self):
        """The served road (_file_host_log_rows, at the host's hello and at its exit): host.log's unfiled lines become
        problem rows. Through the addendum's head the file was read by path, after the spawn road's descriptors were
        closed, so a peer-authored host.log behind the link had its rows filed as this session's problem rows
        (host.end-forced, host.hook-self-answered) and its line count kept as the registry's position. Now the file is
        read by name under the read roads' descent, which refuses the link: one host.directory-refused row, none of the
        peer's rows, no position. Red before: `'host.end-forced' unexpectedly found in [...]`."""
        d, be = self._be()
        rows = [{"t": 1, "kind": "end-forced", "cliPid": 5},
                {"t": 2, "kind": "hook-self-answered", "event": "Stop", "callbackId": "hook_0", "parkedS": 480}]
        peer, hosts = self._peer(d, host_log=rows)
        sb.write_reg(Path(d), SID, {"sid": SID, "name": "web", "alive": True})
        be._file_host_log_rows(types.SimpleNamespace(sid=SID, name="web", _host=None))
        kinds = self._kinds(d)
        self.assertNotIn("host.end-forced", kinds, "the peer's row was filed as this session's: the read took the link")
        self.assertNotIn("host.hook-self-answered", kinds)
        self.assertEqual(kinds, ["host.directory-refused"], "one row, the refusal's kind")
        text = self._refusal_rows(d)[0]["text"]
        self.assertTrue(text.startswith("the session host for web wrote a log this kernel does not read: hosts directory %s is a symlink, not a directory. " % hosts), text)
        self.assertIsNone((sb.read_reg(Path(d), SID) or {}).get("hostLogPos"), "no position from a file that was not read")
        self.assertTrue(hosts.is_symlink(), "the link is left, not replaced")
        self.assertEqual((peer / SID / "host.log").read_text(), "".join(json.dumps(r) + "\n" for r in rows), "the peer's file untouched")

    def _loose_sid(self, d, hosts_mode=0o700, sid_mode=0o775, identity=None, journal=0, host_log=()):
        """hosts/<sid>/ of ours at `sid_mode` under hosts/ at `hosts_mode` (a loose <sid>/ is the fourth addendum's
        scenario: the read descent does not check the mode, so a peer's file can stand in it), with what the arm plants."""
        sdir = Path(d) / "hosts" / SID
        sdir.mkdir(parents=True)
        os.chmod(Path(d) / "hosts", hosts_mode); os.chmod(sdir, sid_mode)
        if identity is not None:
            (sdir / "identity.json").write_text(json.dumps(identity))
        if journal:
            with open(sdir / "journal-0.jsonl", "w") as f:
                for i in range(journal):
                    f.write(json.dumps({"type": "assistant" if i % 2 == 0 else "result", "n": i}) + "\n")
        if host_log:
            (sdir / "host.log").write_text("".join(json.dumps(r) + "\n" for r in host_log))
        return sdir

    def _rows(self, d, kind):
        p = Path(d) / sb.SESSION_EVENTS_FILE
        rows = [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []
        return [r for r in rows if r["kind"] == kind]

    def _modes(self, d):
        return (stat.S_IMODE(os.lstat(Path(d) / "hosts").st_mode), stat.S_IMODE(os.lstat(Path(d) / "hosts" / SID).st_mode))

    def test_a_file_another_uid_owns_under_a_loose_directory_of_ours_is_a_row_and_the_answer_absent_gets_on_each_read_road(self):
        """THE OWNER CHECK on the three read roads (the round-7 fourth addendum, 2026-09-20, the reviewer's ruling of
        19:12Z): a <sid>/ of ours left 0775 admits a file a peer planted at identity.json or host.log, and the read
        descent does not check the mode (it would refuse every install whose hosts/ was made at the umask), so through
        the third addendum each road read the peer's file as ours. Now the reader fstats the object it holds (the
        descriptor read_host_file opened; the name under the <sid> descriptor for host_file_exists), and a foreign owner
        is an ANSWER: one host.directory-refused row naming the file, its directory and the owning uid, with the owner's
        remedy, and then what an absent file gets on that road. The foreign uid is simulated by the stat result the
        reader sees (foreign_uid: st_uid + 1 for that one object, from a descriptor or a name under one and NEVER from a
        path, which the stub counts instead; the count is asserted 0 on every arm since the fifth addendum, so an owner
        check moved onto a path stat reds here and not only in the census), since no file of another uid is
        constructible here; the loose <sid>/ itself is filed as one host.directory-loose row beside it, once per connect
        episode (the fifth addendum: the lease-applies arm reads twice on one backend with no new episode between, so
        one loose row where the fourth addendum's one-per-descent filed two; the next cases pin that row on its own).
        Per road, before (the peer's content read) and after: lease-applies, `True` (the peer's
        identity.json vouched for a host) to `False` (the row, then the journal listing, which finds nothing); the orphan
        road, `[1]` (the peer's identity vouched for the registry's ack and the replay started at its offset) to `[-1]`
        (no identity vouches, the offset is -1, and the journal listing that follows is by path until the follow-up
        lands: the tail is replayed from the start, the answer an absent identity.json always got); the served road,
        `['host.end-forced', 'host.hook-self-answered']` filed as this session's to none, no position kept. Red before,
        the three arms at the third addendum's head: `True is not False`, `[1] != [-1]`, `'host.end-forced'
        unexpectedly found`."""
        remedy = "A identity.json under hosts/<sid>/ that another user owns is not read; remove it, or point the state root elsewhere (ROMP_STATE_DIR or XDG_STATE_HOME)"
        with self.subTest(road="lease-applies"):
            d, be = self._be()
            Path(d, "session-hosts").write_text("off")
            sdir = self._loose_sid(d, identity={"pid": 7, "start": "p"})
            s = types.SimpleNamespace(sid=SID, name="web")
            self.assertIs(be._host_lease_applies(s), True, "before the stub: our file vouches")
            with foreign_uid(sdir / "identity.json") as fu:
                self.assertIs(be._host_lease_applies(s), False, "a peer's identity.json vouches for no host: the answer an absent one gets")
            self.assertEqual(fu.path_stats, 0, "the owner check took a path stat: %r" % (fu.path_stat_calls,))
            kinds = self._kinds(d)
            self.assertEqual([k for k in kinds if k != "host.directory-loose"], ["host.directory-refused"], "the owner row, and no refusal for the read of our own file")
            self.assertEqual(kinds, ["host.directory-loose", "host.directory-refused"], "the loose row once for the episode (two descents, one mode), then the owner row")
            row = self._rows(d, "host.directory-refused")[0]
            self.assertEqual(row["text"], "the session host for web may have left records this kernel does not read: identity.json in host directory %s belongs to uid %d, not to us (uid %d). %s" % (sdir, os.geteuid() + 1, os.geteuid(), remedy))
            self.assertEqual((row["file"], row["uid"]), ("identity.json", os.geteuid() + 1), "the row's fields name the file and the owner")
            self.assertEqual(self._modes(d), (0o700, 0o775), "the read changed no mode")
        with self.subTest(road="orphan"):
            for stub, expect_acks in ((True, [-1]), (False, [1])):        # the stubbed run first: its assertion is the pin
                d, be = self._be()
                sb.write_reg(Path(d), SID, {"sid": SID, "name": "web", "alive": True, "lastSid": SID,
                                             "hostAck": {"host": "7:p", "cli": "8:c", "offset": 1}})
                sdir = self._loose_sid(d, identity={"pid": 7, "start": "p"}, journal=3)
                acks = []
                s = types.SimpleNamespace(sid=SID, name="web", _host_intent=True, _host=None, _host_is_attach=False, _seed_for_dead_cli=lambda cli: None)
                capture = classmethod(lambda cls, hdir, ack=-1, **kw: acks.append(ack) or types.SimpleNamespace(hdir=hdir))
                ctx = foreign_uid(sdir / "identity.json") if stub else contextlib.nullcontext()
                with mock.patch.dict(sys.modules, {"claude_agent_sdk": self._sdk_stub()}), ctx as fu, \
                     mock.patch.object(ht.HostTransport, "from_journal", capture), mock.patch.object(be, "_replay_drain", mock.AsyncMock()):
                    asyncio.run(be._host_orphan_recover(s, types.SimpleNamespace(), None, (None, None, None), died=False))
                self.assertEqual(acks, expect_acks, "stub=%s: the replay's offset (the peer's identity vouched for 1; a foreign one vouches for nothing, -1)" % stub)
                if stub:
                    self.assertEqual(fu.path_stats, 0, "the owner check took a path stat: %r" % (fu.path_stat_calls,))
                    self.assertEqual(self._kinds(d), ["host.directory-loose", "host.directory-refused", "host.tail-replayed"],
                                     "the loose row, the owner row, then the tail replayed from the start: the journal reads are by path until the follow-up lands")
                    row = self._rows(d, "host.directory-refused")[0]
                    self.assertEqual(row["text"], "the session host for web is gone, and left a file this kernel does not read: identity.json in host directory %s belongs to uid %d, not to us (uid %d). %s" % (sdir, os.geteuid() + 1, os.geteuid(), remedy))
                else:
                    self.assertEqual(self._kinds(d), ["host.directory-loose", "host.tail-replayed"])
                self.assertFalse(sdir.exists(), "the road still clears the directory after the replay (remove_host_dir)")
        with self.subTest(road="served"):
            rows = [{"t": 1, "kind": "end-forced", "cliPid": 5},
                    {"t": 2, "kind": "hook-self-answered", "event": "Stop", "callbackId": "hook_0", "parkedS": 480}]
            for stub in (True, False):                                      # the stubbed run first: its assertion is the pin
                d, be = self._be()
                sdir = self._loose_sid(d, host_log=rows)
                sb.write_reg(Path(d), SID, {"sid": SID, "name": "web", "alive": True})
                ctx = foreign_uid(sdir / "host.log") if stub else contextlib.nullcontext()
                with ctx as fu:
                    be._file_host_log_rows(types.SimpleNamespace(sid=SID, name="web", _host=None))
                kinds = self._kinds(d)
                if stub:
                    self.assertEqual(fu.path_stats, 0, "the owner check took a path stat: %r" % (fu.path_stat_calls,))
                    self.assertNotIn("host.end-forced", kinds, "the peer's row was filed as this session's: the file was read as ours")
                    self.assertEqual(kinds, ["host.directory-loose", "host.directory-refused"], "the loose row and the owner row; none of the file's rows")
                    row = self._rows(d, "host.directory-refused")[0]
                    self.assertTrue(row["text"].startswith("the session host for web wrote a log this kernel does not read: host.log in host directory %s belongs to uid %d, not to us (uid %d). A host.log under hosts/<sid>/ that another user owns is not read;" % (sdir, os.geteuid() + 1, os.geteuid())), row["text"])
                    self.assertIsNone((sb.read_reg(Path(d), SID) or {}).get("hostLogPos"), "no position from a file that was not read")
                else:
                    self.assertEqual(kinds, ["host.directory-loose", "host.end-forced", "host.hook-self-answered"], "our own file: its rows filed, after the loose row")
                self.assertEqual((sdir / "host.log").read_text(), "".join(json.dumps(r) + "\n" for r in rows), "the file untouched")
                self.assertEqual(self._modes(d), (0o700, 0o775), "the read changed no mode")

    def test_a_loose_directory_of_ours_on_each_read_road_is_one_row_per_component_and_the_read_proceeds_with_the_mode_unchanged(self):
        """THE MODE ROW (the fourth addendum): on each read road's descent the mode of hosts/ and <sid>/ is read from the
        descent's own fstat and a loose one (group or other bits) is filed as one host.directory-loose row per component,
        the mode in octal and the remedy naming the spawn road's repair; the read then PROCEEDS (nothing is
        refused: a 0700 condition would deny every session's first connect on an install whose hosts/ was made at the
        umask) and the road chmods nothing (a read road stays a read road; the repair is the spawn road's helpers').
        Each road here runs once on a fresh backend, one descent in one connect episode, so one row per component; how
        often the row is filed across the descents of one episode is the next case's subject (the fifth addendum: once
        per episode per mode observed). Both components 0775 here, so two rows. Modes pasted before and after each road: `(0o775, 0o775)`
        both times on the three pure read roads; at the leftover trigger the road is stopped right after its descent (the
        orphan road it hands to raises a sentinel), so its own descent is what is measured. Mutation (over a scratch copy):
        an fchmod added to the descent's loose arm reds the mode assertions on every arm."""
        class StopRoad(Exception):
            pass
        for road in ("lease-applies", "leftover-trigger", "orphan", "served"):
            with self.subTest(road=road):
                d, be = self._be()
                rows = [{"t": 1, "kind": "end-forced", "cliPid": 5}]
                sdir = self._loose_sid(d, hosts_mode=0o775, sid_mode=0o775, identity={"pid": 7, "start": "p"}, journal=3, host_log=rows)
                sb.write_reg(Path(d), SID, {"sid": SID, "name": "web", "alive": True, "lastSid": SID})
                self.assertEqual(self._modes(d), (0o775, 0o775))
                s = types.SimpleNamespace(sid=SID, name="web", _host_intent=True, _host=None, _host_is_attach=False,
                                          _seed_for_dead_cli=lambda cli: None, _options_login="", _host_end_grace=None,
                                          _on_cli_stderr=lambda line: None)
                if road == "lease-applies":
                    Path(d, "session-hosts").write_text("off")
                    self.assertIs(be._host_lease_applies(s), True, "the read proceeds: our identity.json vouches")
                    kinds = self._kinds(d)
                elif road == "leftover-trigger":
                    with mock.patch.object(be, "_host_orphan_recover", mock.AsyncMock(side_effect=StopRoad())), self.assertRaises(StopRoad):
                        asyncio.run(be._host_transport_for(s, types.SimpleNamespace(), (None, None, None)))
                    kinds = self._kinds(d)
                elif road == "orphan":
                    acks = []
                    capture = classmethod(lambda cls, hdir, ack=-1, **kw: acks.append(ack) or types.SimpleNamespace(hdir=hdir))
                    with mock.patch.dict(sys.modules, {"claude_agent_sdk": self._sdk_stub()}), \
                         mock.patch.object(ht.HostTransport, "from_journal", capture), mock.patch.object(be, "_replay_drain", mock.AsyncMock()), \
                         mock.patch.object(ht, "remove_host_dir", lambda *a, **k: True):      # the removal is not this pin's subject: the directory stays for the mode read
                        asyncio.run(be._host_orphan_recover(s, types.SimpleNamespace(), None, (None, None, None), died=False))
                    self.assertEqual(acks, [-1], "the read proceeds: the tail is replayed")
                    kinds = [k for k in self._kinds(d) if k != "host.tail-replayed"]
                else:
                    be._file_host_log_rows(types.SimpleNamespace(sid=SID, name="web", _host=None))
                    kinds = [k for k in self._kinds(d) if k != "host.end-forced"]
                    self.assertIn("host.end-forced", self._kinds(d), "the read proceeds: the file's row is filed")
                self.assertEqual(kinds, ["host.directory-loose", "host.directory-loose"], "%s: one row per loose component per descent, no refusal" % road)
                loose = self._rows(d, "host.directory-loose")
                self.assertEqual([(r["path"], r["mode"]) for r in loose], [(str(Path(d) / "hosts"), "0775"), (str(sdir), "0775")])
                self.assertEqual(loose[0]["text"], "the hosts directory %s for web is group/world-accessible (mode 0775); this read changed nothing, and the next session-host launch tightens it to 0700 (the spawn road's helpers, hosts_dir and owner_only_dir)" % (Path(d) / "hosts"))
                self.assertEqual(loose[1]["text"], "the host directory %s for web is group/world-accessible (mode 0775); this read changed nothing, and the next session-host launch tightens it to 0700 (the spawn road's helpers, hosts_dir and owner_only_dir)" % sdir)
                self.assertEqual(self._modes(d), (0o775, 0o775), "%s: the read road changed no mode" % road)

    def test_a_symlink_at_the_read_file_is_the_file_remedy_row_on_all_three_read_roads(self):
        """THE SYMLINK ROW (the fourth addendum): a link planted at identity.json (the lease-applies and orphan roads) or
        host.log (the served road) under a verified <sid>/ of ours is refused naming the file, with the file remedy, on
        ALL THREE roads. Through the third addendum the orphan and served roads filed that row (read_host_file's
        O_NOFOLLOW open) and the lease-applies road answered False with no row (host_file_exists stat'd the name and
        said the link was not the file). Kinds pasted per road: `['host.directory-refused']` on each; nothing behind the
        link is opened. Red before, the lease-applies arm at the third addendum's head: `[] != ['host.directory-refused']`."""
        elsewhere = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, elsewhere, True)
        (elsewhere / "identity.json").write_text(json.dumps({"pid": 7, "start": "p"}))
        (elsewhere / "host.log").write_text(json.dumps({"t": 1, "kind": "end-forced", "cliPid": 5}) + "\n")
        remedy = "under hosts/<sid>/ that is a symlink is refused; remove the link, or point the state root elsewhere (ROMP_STATE_DIR or XDG_STATE_HOME)"
        for road in ("lease-applies", "orphan", "served"):
            with self.subTest(road=road):
                d, be = self._be()
                sdir = self._loose_sid(d, sid_mode=0o700)
                name = "host.log" if road == "served" else "identity.json"
                (sdir / name).symlink_to(elsewhere / name)
                sb.write_reg(Path(d), SID, {"sid": SID, "name": "web", "alive": True, "lastSid": SID,
                                             "hostAck": {"host": "7:p", "cli": "8:c", "offset": 1}})
                s = types.SimpleNamespace(sid=SID, name="web", _host_intent=True, _host=None, _host_is_attach=False, _seed_for_dead_cli=lambda cli: None)
                if road == "lease-applies":
                    Path(d, "session-hosts").write_text("off")
                    self.assertIs(be._host_lease_applies(s), False, "a link at identity.json vouches for no host")
                    did = "may have left records this kernel does not read"
                elif road == "orphan":
                    acks = []
                    capture = classmethod(lambda cls, hdir, ack=-1, **kw: acks.append(ack) or types.SimpleNamespace(hdir=hdir))
                    with mock.patch.dict(sys.modules, {"claude_agent_sdk": self._sdk_stub()}), \
                         mock.patch.object(ht.HostTransport, "from_journal", capture), mock.patch.object(be, "_replay_drain", mock.AsyncMock()):
                        asyncio.run(be._host_orphan_recover(s, types.SimpleNamespace(), None, (None, None, None), died=False))
                    self.assertEqual(acks, [], "the refused arm: nothing replayed")
                    did = "is gone, and its journal is not replayed"
                else:
                    be._file_host_log_rows(types.SimpleNamespace(sid=SID, name="web", _host=None))
                    did = "wrote a log this kernel does not read"
                self.assertEqual(self._kinds(d), ["host.directory-refused"], road)
                row = self._rows(d, "host.directory-refused")[0]
                self.assertEqual(row["text"], "the session host for web %s: %s in host directory %s is a symlink, not a regular file. A %s %s" % (did, name, sdir, name, remedy))
                self.assertEqual(row["file"], name)
                self.assertNotIn("uid", row, "a link is not the owner shape")
                self.assertEqual((elsewhere / name).read_text(), (elsewhere / name).read_text(), "the target is untouched")
                self.assertTrue((sdir / name).is_symlink() or not sdir.exists(), "the link is left where the road did not clear the directory")

    def _refused(self, d):
        return [(r["kind"], r.get("file"), r.get("uid")) for r in self._rows(d, "host.directory-refused")]

    def test_every_shape_a_peer_can_put_at_the_read_file_is_answered_from_the_table_on_each_read_road(self):
        """THE SHAPE TABLE on the three read roads (SHAPE_TABLE, module level; the round-7 fifth addendum, 2026-09-20):
        the 13 (kind, owner) rows times the three roads, 39 cells, each planted under a loose <sid>/ of ours (0775 under
        a 0700 hosts/) and driven through the production road on a fresh backend: _host_lease_applies with hosts off
        (identity.json's existence), _host_orphan_recover's lease-less arm (identity.json's bytes, the registry's ack
        naming the identity of ours), _file_host_log_rows (host.log's bytes). Per cell: the road's answer, the refusal
        rows filed as (kind, `file`, `uid`), the loose row once, the mode unchanged where the directory stands, the
        stub's path-stat count 0 on a foreign cell, and a link's target untouched. The answers by road: lease-applies,
        `ours` True; `absent` and `not-file` False with no refusal row (the journal listing then finds nothing);
        `foreign` False after one host.directory-refused row with `file` and `uid`; `link` False after the file-shape row
        (`file`, no `uid`). Orphan, read as the replay's offset: `ours` [1] (the identity vouches for the ack); `absent`
        and `not-file` [-1] (the tail replayed from the start, no refusal row); `foreign` [-1] after the owner row;
        `link` [] after the file row (the refused arm replays nothing). Served: `ours` the file's row (`host.end-forced`);
        `absent` and `not-file` none; `foreign` the owner row, none of the file's, no position; `link` the file row. Red
        before, the module copied onto a scratch worktree at the fourth addendum's commit: the foreign-socket cells on the
        orphan and served roads filed NO owner row (open(2) answered ENXIO before the owner fstat and the roads' OSError
        arms swallowed it), `Lists differ: [] != [('host.directory-refused', 'identity.json', <uid>)]` and the same for
        host.log; the foreign-symlink cells answered the link row, `uid` None, on all three roads; function level, the
        foreign socket raised `OSError: [Errno 6] No such device or address` out of read_host_file."""
        euid = os.geteuid()
        identity = json.dumps({"pid": 7, "start": "p"})
        log_rows = "".join(json.dumps(r) + "\n" for r in [{"t": 1, "kind": "end-forced", "cliPid": 5}])
        for road in ("lease-applies", "orphan", "served"):
            for kind, owner, expect_exists, expect_read in SHAPE_TABLE:
                expect = expect_exists if road == "lease-applies" else expect_read
                with self.subTest(road=road, kind=kind, owner=owner):
                    d, be = self._be()
                    elsewhere = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, elsewhere, True)
                    name = "host.log" if road == "served" else "identity.json"
                    sdir = self._loose_sid(d, journal=3 if road == "orphan" else 0)
                    plant_shape(sdir, name, kind, log_rows if road == "served" else identity, elsewhere)
                    target = (elsewhere / name).read_text() if kind == "symlink-to-file" else None
                    ctx = foreign_uid(sdir / name) if owner == "foreign" else contextlib.nullcontext()
                    s = types.SimpleNamespace(sid=SID, name="web", _host_intent=True, _host=None, _host_is_attach=False, _seed_for_dead_cli=lambda cli: None)
                    if road == "lease-applies":
                        Path(d, "session-hosts").write_text("off")
                        with ctx as fu:
                            answer = be._host_lease_applies(s)
                        self.assertIs(answer, expect == "ours", "%s: the lease-applies answer" % expect)
                    elif road == "orphan":
                        sb.write_reg(Path(d), SID, {"sid": SID, "name": "web", "alive": True, "lastSid": SID,
                                                     "hostAck": {"host": "7:p", "cli": "8:c", "offset": 1}})
                        acks = []
                        capture = classmethod(lambda cls, hdir, ack=-1, **kw: acks.append(ack) or types.SimpleNamespace(hdir=hdir))
                        with mock.patch.dict(sys.modules, {"claude_agent_sdk": self._sdk_stub()}), ctx as fu, \
                             mock.patch.object(ht.HostTransport, "from_journal", capture), mock.patch.object(be, "_replay_drain", mock.AsyncMock()):
                            asyncio.run(be._host_orphan_recover(s, types.SimpleNamespace(), None, (None, None, None), died=False))
                        self.assertEqual(acks, {"ours": [1], "link": []}.get(expect, [-1]), "%s: the replay's offset" % expect)
                        self.assertEqual("host.tail-replayed" in self._kinds(d), expect != "link", "%s: the tail is replayed unless the road was refused" % expect)
                    else:
                        sb.write_reg(Path(d), SID, {"sid": SID, "name": "web", "alive": True})
                        with ctx as fu:
                            be._file_host_log_rows(types.SimpleNamespace(sid=SID, name="web", _host=None))
                        self.assertEqual("host.end-forced" in self._kinds(d), expect == "ours", "%s: the file's rows are filed only for a file of ours" % expect)
                        if expect != "ours":
                            self.assertIsNone((sb.read_reg(Path(d), SID) or {}).get("hostLogPos"), "no position from a file that was not read")
                    refused = self._refused(d)
                    if expect == "foreign":
                        self.assertEqual(refused, [("host.directory-refused", name, euid + 1)], "%s/%s: the owner row, with the file and the uid" % (kind, owner))
                        self.assertIn("%s in host directory %s belongs to uid %d, not to us (uid %d)" % (name, sdir, euid + 1, euid), self._rows(d, "host.directory-refused")[0]["text"])
                        self.assertEqual(fu.path_stats, 0, "the owner check took a path stat: %r" % (fu.path_stat_calls,))
                    elif expect == "link":
                        self.assertEqual(refused, [("host.directory-refused", name, None)], "%s/%s: the file-shape row, no uid" % (kind, owner))
                        self.assertIn("%s in host directory %s is a symlink, not a regular file" % (name, sdir), self._rows(d, "host.directory-refused")[0]["text"])
                    else:
                        self.assertEqual(refused, [], "%s/%s: no refusal row for %s" % (kind, owner, expect))
                    self.assertEqual([(r["path"], r["mode"]) for r in self._rows(d, "host.directory-loose")], [(str(sdir), "0775")], "the loose <sid>/, once")
                    if sdir.exists():
                        self.assertEqual(self._modes(d), (0o700, 0o775), "the read changed no mode")
                    if target is not None:
                        self.assertEqual((elsewhere / name).read_text(), target, "nothing behind the link was touched")

    def test_a_loose_directory_is_one_row_per_connect_episode_per_mode_observed_however_many_descents(self):
        """THE LOOSE ROW ACROSS THE DESCENTS OF ONE SESSION (the name is the round-7 fifth addendum's, the reviewer's
        ruling of 2026-09-20 20:40Z, kept because fork PR #814's ledger entry cites it; THE RULE it pins is the 07:19Z
        ruling's at _file_loose_directory_rows since fork PR #884's fifth commit: one row per observed state of the row's
        subject, hosts/ shared by every session and hosts/<sid>/ one session's, so the per-episode footing this case was
        written on holds for <sid>/ alone; the shared-subject cases follow this one). Three arms, each on one backend (a
        fresh backend stands at the start of its first episode; a later episode is opened the way the connect loop opens
        it, _loose_rows_new_episode, whose loop-top placement the next case pins). (1) THREE DESCENTS, ONE EPISODE: hosts
        off, both directories 0775, a leftover tail; the lease-applies read (descent one), then _host_transport_for, whose
        leftover trigger (two) hands the orphan road (three), the descents counted through open_host_dirs_if_present: the
        rows are one per component, `[(hosts, '0775'), (<sid>, '0775')]`. (2) A MODE CHANGE MID-EPISODE: the same, with
        <sid>/ chmod'd 0770 by the test between the lease-applies read and the connect: a third row naming 0770 and no
        fourth for the orphan road's descent, which observes 0770 again. (3) A NEW EPISODE FILES THE SESSION'S OWN
        DIRECTORY AGAIN AND NOT THE SHARED ONE, AND A TRANSITION IS NEW INFORMATION: the lease-applies read twice in one
        episode, two rows; a new episode and the read, three (<sid>/ again; hosts/ stands, its mode last observed 0775);
        <sid>/ tightened to 0700 and read, still three (a tight mode is observed and not filed); loosened back to 0775
        and read, four (the mode changed since it was last observed, so the same mode as before is a row again). Red
        before at the fourth addendum's commit, one row per descent: (1) `Lists differ: [(hosts, '0775'), (<sid>,
        '0775'), (hosts, '0775'), (<sid>, '0775'), (hosts, '0775'), (<sid>, '0775')] != [(hosts, '0775'), (<sid>,
        '0775')]`, six for two; (2) six for three; (3) four for two at the first step. Arm (3) red at #884's fourth
        commit, hosts/ re-filed at the new episode: `[(hosts, '0775'), (<sid>, '0775'), (hosts, '0775'), (<sid>,
        '0775')] != [(hosts, '0775'), (<sid>, '0775'), (<sid>, '0775')]`."""
        def session():
            return types.SimpleNamespace(sid=SID, name="web", _host_intent=True, _host=None, _host_is_attach=False,
                                         _seed_for_dead_cli=lambda cli: None, _options_login="", _host_end_grace=None,
                                         _on_cli_stderr=lambda line: None)

        def loose(d):
            return [(r["path"], r["mode"]) for r in self._rows(d, "host.directory-loose")]

        def connect(be, s):
            """_host_transport_for with hosts off over a leftover: the trigger's descent, the orphan road's descent and
            its replay, then the kernel-child answer (None)."""
            capture = classmethod(lambda cls, hdir, ack=-1, **kw: types.SimpleNamespace(hdir=hdir))
            with mock.patch.dict(sys.modules, {"claude_agent_sdk": self._sdk_stub()}), \
                 mock.patch.object(ht.HostTransport, "from_journal", capture), mock.patch.object(be, "_replay_drain", mock.AsyncMock()):
                return asyncio.run(be._host_transport_for(s, types.SimpleNamespace(), (None, None, None)))

        for arm in ("three descents, one episode", "a mode change mid-episode"):
            with self.subTest(arm=arm):
                d, be = self._be()
                Path(d, "session-hosts").write_text("off")
                sdir = self._loose_sid(d, hosts_mode=0o775, sid_mode=0o775, identity={"pid": 7, "start": "p"}, journal=3)
                hosts = str(Path(d) / "hosts")
                sb.write_reg(Path(d), SID, {"sid": SID, "name": "web", "alive": True, "lastSid": SID})
                s = session()
                descents, real = [], ht.open_host_dirs_if_present
                with mock.patch.object(ht, "open_host_dirs_if_present", lambda *a, **k: descents.append(a[1]) or real(*a, **k)):
                    self.assertIs(be._host_lease_applies(s), True, "descent one: our identity.json vouches")
                    if arm == "a mode change mid-episode":
                        os.chmod(sdir, 0o770)
                    self.assertIsNone(connect(be, s), "hosts off: the kernel child after the leftover's replay")
                self.assertEqual(descents, [SID, SID, SID], "three descents in the one episode: lease-applies, the leftover trigger, the orphan road")
                if arm == "three descents, one episode":
                    self.assertEqual(loose(d), [(hosts, "0775"), (str(sdir), "0775")], "one row per component for the episode, not per descent")
                else:
                    self.assertEqual(loose(d), [(hosts, "0775"), (str(sdir), "0775"), (str(sdir), "0770")],
                                     "the mode that changed between two descents is a row naming the new mode, once")
                self.assertIn("host.tail-replayed", self._kinds(d), "the read roads proceeded: the tail was replayed")
        with self.subTest(arm="a new episode files the session's own directory again, and a transition is new information"):
            d, be = self._be()
            Path(d, "session-hosts").write_text("off")
            sdir = self._loose_sid(d, hosts_mode=0o775, sid_mode=0o775, identity={"pid": 7, "start": "p"})
            hosts = str(Path(d) / "hosts")
            s = session()
            self.assertIs(be._host_lease_applies(s), True); self.assertIs(be._host_lease_applies(s), True)
            self.assertEqual(loose(d), [(hosts, "0775"), (str(sdir), "0775")], "two reads in one episode: the rows once")
            be._loose_rows_new_episode(s)
            self.assertIs(be._host_lease_applies(s), True)
            self.assertEqual(loose(d), [(hosts, "0775"), (str(sdir), "0775"), (str(sdir), "0775")],
                             "a new episode: the session's own still-loose directory is filed again; hosts/, shared, stands")
            os.chmod(sdir, 0o700)
            self.assertIs(be._host_lease_applies(s), True)
            self.assertEqual(len(loose(d)), 3, "a tight mode is observed and files nothing")
            os.chmod(sdir, 0o775)
            self.assertIs(be._host_lease_applies(s), True)
            self.assertEqual(loose(d), [(hosts, "0775"), (str(sdir), "0775")] + [(str(sdir), "0775")] * 2,
                             "loosened again within the episode: the transition is filed, though the mode was filed before")
            self.assertEqual(self._modes(d), (0o775, 0o775), "the read roads changed no mode")

    def _sid_dir(self, d, sid, hosts_mode=0o775, sid_mode=0o700, identity=None):
        """hosts/<sid>/ for one of SIDS (the shared-subject pins connect several sessions over one hosts/), hosts/ at
        `hosts_mode`, the directory at `sid_mode`, identity.json of ours when given."""
        sdir = Path(d) / "hosts" / sid
        sdir.mkdir(parents=True, exist_ok=True)
        os.chmod(Path(d) / "hosts", hosts_mode); os.chmod(sdir, sid_mode)
        if identity is not None:
            (sdir / "identity.json").write_text(json.dumps(identity))
        return sdir

    def _session_for(self, sid, name):
        return types.SimpleNamespace(sid=sid, name=name, _host_intent=True, _host=None, _host_is_attach=False,
                                     _seed_for_dead_cli=lambda cli: None, _options_login="", _host_end_grace=None,
                                     _on_cli_stderr=lambda line: None)

    def _loose(self, d):
        return [(r["path"], r["mode"]) for r in self._rows(d, "host.directory-loose")]

    def test_one_loose_hosts_directory_observed_by_three_sids_connects_is_one_row_for_it_and_none_for_their_tight_directories(self):
        """THE SHARED SUBJECT (the reviewer's ruling of 2026-09-21 07:19Z; THE RULE at _file_loose_directory_rows): hosts/
        at 0775 is ONE directory whoever descends through it, so three sessions' connect episodes over it (each opened the
        way the connect loop opens one, _loose_rows_new_episode, then the lease-applies read with hosts off, each on its
        own SdkSession-shaped object) file ONE host.directory-loose row for hosts/, the first observer's, and none for
        their 0700 <sid>/ directories, which are tight. The reads change no mode. Red before at fork PR #884's fourth
        commit, the latch keyed on the sid and its episode: one row per session, `Lists differ: [(hosts, '0775'),
        (hosts, '0775'), (hosts, '0775')] != [(hosts, '0775')]`, the production shape (nine sessions at one restart,
        nine rows for one directory). Mutation (a scratch copy, python -B): the owner put back to the observing sid
        for every component reds here the same way."""
        d, be = self._be()
        Path(d, "session-hosts").write_text("off")
        for sid in SIDS:
            self._sid_dir(d, sid, hosts_mode=0o775, sid_mode=0o700, identity={"pid": 7, "start": "p"})
        hosts = str(Path(d) / "hosts")
        for i, sid in enumerate(SIDS):
            s = self._session_for(sid, "web%d" % i)
            be._loose_rows_new_episode(s)
            self.assertIs(be._host_lease_applies(s), True, "%s: the read proceeds, its identity.json vouches" % s.name)
        self.assertEqual(self._loose(d), [(hosts, "0775")],
                         "one row for the one shared directory, whichever session observed it first; none for the tight <sid>/ directories")
        self.assertEqual(self._rows(d, "host.directory-loose")[0]["sid"], SIDS[0], "the first observer's row")
        self.assertEqual(stat.S_IMODE(os.lstat(hosts).st_mode), 0o775, "the reads changed no mode")

    def test_each_sids_own_loose_directory_is_its_own_row_and_a_new_episode_of_one_sid_files_its_own_again_and_not_hosts(self):
        """THE PER-SID SUBJECT beside the shared one: hosts/ 0775 and each of three <sid>/ at 0775; three sessions'
        connects file one row for hosts/ and one per <sid>/, four; a new episode of the first session (the connect
        loop's top, _loose_rows_new_episode) forgets ITS subjects and no other's, so its read files its own <sid>/ again,
        five, and NOT hosts/, which stands for the kernel's life, and the other two sessions' directories are untouched.
        The 20:40Z ruling's once per connect episode, unchanged where the subject and the episode coincide. Red before
        at fork PR #884's fourth commit: hosts/ again at the new episode, six rows."""
        d, be = self._be()
        Path(d, "session-hosts").write_text("off")
        dirs = {sid: self._sid_dir(d, sid, hosts_mode=0o775, sid_mode=0o775, identity={"pid": 7, "start": "p"}) for sid in SIDS}
        hosts = str(Path(d) / "hosts")
        sessions = [self._session_for(sid, "web%d" % i) for i, sid in enumerate(SIDS)]
        for s in sessions:
            be._loose_rows_new_episode(s)
            self.assertIs(be._host_lease_applies(s), True)
        expect = [(hosts, "0775")] + [(str(dirs[sid]), "0775") for sid in SIDS]
        self.assertEqual(self._loose(d), expect, "hosts/ once, then each session's own directory once")
        be._loose_rows_new_episode(sessions[0])
        self.assertIs(be._host_lease_applies(sessions[0]), True)
        self.assertEqual(self._loose(d), expect + [(str(dirs[SIDS[0]]), "0775")],
                         "the new episode files the session's own directory again and not hosts/, nor another session's")
        self.assertEqual([r["sid"] for r in self._rows(d, "host.directory-loose")], [SIDS[0]] + list(SIDS) + [SIDS[0]])

    def test_hosts_observed_loose_then_tight_then_loose_by_three_sids_is_two_rows_the_second_at_the_third_observation(self):
        """A TRANSITION of the shared subject is new information, whoever observes it: hosts/ 0775 read by the first
        session (a row), chmod 0700 and read by the second (observed, nothing filed: tight), chmod 0775 and read by the
        third (a row: the mode changed since the directory was last observed, though this mode was filed before), then
        read by the second session again in its still-open episode (nothing: 0775 is the mode last observed, by the third
        session). Two rows for hosts/, the second carrying the third session; the <sid>/ directories 0700 throughout, no
        row of theirs. Red before at fork PR #884's fourth commit, the latch per sid: the second session's read at the
        end is a change from the 0700 it observed, a third row. Mutation (a scratch copy, python -B): the latch holding
        that the mode was FILED instead of the mode last observed (`was is not None`) reds here with one row, the third
        session's observation latched by the second's tight one."""
        d, be = self._be()
        Path(d, "session-hosts").write_text("off")
        for sid in SIDS:
            self._sid_dir(d, sid, hosts_mode=0o775, sid_mode=0o700, identity={"pid": 7, "start": "p"})
        hosts = Path(d) / "hosts"
        sessions = [self._session_for(sid, "web%d" % i) for i, sid in enumerate(SIDS)]
        for s, mode in zip(sessions, (0o775, 0o700, 0o775)):
            os.chmod(hosts, mode)
            be._loose_rows_new_episode(s)
            self.assertIs(be._host_lease_applies(s), True)
        self.assertIs(be._host_lease_applies(sessions[1]), True)
        self.assertEqual(self._loose(d), [(str(hosts), "0775"), (str(hosts), "0775")],
                         "the first observation and the transition back to 0775; the tight observation and the repeat file nothing")
        self.assertEqual([r["sid"] for r in self._rows(d, "host.directory-loose")], [SIDS[0], SIDS[2]], "the first and the third observers")
        self.assertEqual(stat.S_IMODE(os.lstat(hosts).st_mode), 0o775)

    def test_hosts_loose_then_refused_then_loose_again_by_three_sids_is_two_loose_rows_the_second_at_the_third_observation(self):
        """A REFUSAL IS A STATE OF THE SHARED DIRECTORY, and the loose latch forgets it (the reviewer's ruling of 2026-09-21
        09:32Z on fork PR #884's fifth commit; THE RULE at _file_loose_directory_rows, the mirror at _refused_directory_row):
        hosts/ 0775 read by the first session (a loose row), replaced by a symlink to a directory elsewhere, and on the
        second arm by a regular file, and read by the second (a refused row, the shared subject's, and the answer False),
        the plant removed and a new hosts/ at 0775 with the three <sid>/ under it made and read by the third: a SECOND
        loose row, the third session's. Three observations of two states, loose, refused, loose, with a transition away
        and back, so the third announces; the latch then reads the new mode, and the refused row stands at one. The <sid>/
        directories 0700 throughout, no row of theirs. Red before at the fifth commit, where the refusal left the loose
        latch standing at the 0775 it had observed before the plant, so the third read was the same mode and filed
        nothing: one loose row, `Lists differ: [(hosts, '0775')] != [(hosts, '0775'), (hosts, '0775')]`, both arms.
        Mutation (a scratch copy, python -B): the refusal's pop of the loose entry
        dropped reds here the same way; _row_owner answering the sid for the shared path reds here at the latch read (no
        shared bucket) and the shared-subject cases above at their row counts."""
        elsewhere = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, elsewhere, True)
        for arm in ("a symlink", "a regular file"):
            with self.subTest(arm=arm):
                d, be = self._be()
                Path(d, "session-hosts").write_text("off")
                hosts = Path(d) / "hosts"
                def plant_dirs():
                    for sid in SIDS:
                        self._sid_dir(d, sid, hosts_mode=0o775, sid_mode=0o700, identity={"pid": 7, "start": "p"})
                plant_dirs()
                sessions = [self._session_for(sid, "web%d" % i) for i, sid in enumerate(SIDS)]
                be._loose_rows_new_episode(sessions[0])
                self.assertIs(be._host_lease_applies(sessions[0]), True)
                self.assertEqual(self._loose(d), [(str(hosts), "0775")], "the first observation, loose")
                shutil.rmtree(hosts)
                if arm == "a symlink":
                    hosts.symlink_to(elsewhere)
                else:
                    hosts.write_text("not a directory")
                be._loose_rows_new_episode(sessions[1])
                self.assertIs(be._host_lease_applies(sessions[1]), False, "refused: no host this kernel can vouch for")
                self.assertEqual(self._refused(d), [("host.directory-refused", None, None)], "the second observation, refused, the shared subject's")
                hosts.unlink()
                plant_dirs()
                be._loose_rows_new_episode(sessions[2])
                self.assertIs(be._host_lease_applies(sessions[2]), True)
                self.assertEqual(self._loose(d), [(str(hosts), "0775"), (str(hosts), "0775")],
                                 "%s: the directory seen loose again after the refusal is a transition, filed at the third observation" % arm)
                self.assertEqual([r["sid"] for r in self._rows(d, "host.directory-loose")], [SIDS[0], SIDS[2]], "the first and the third observers")
                self.assertEqual(be._loose_filed[None], {str(hosts): 0o775}, "the latch reads the new mode")
                self.assertEqual(len(self._refused(d)), 1, "the refused row stands at one")
                self.assertEqual(stat.S_IMODE(os.lstat(hosts).st_mode), 0o775, "the reads changed no mode")
                self.assertEqual(sorted(os.listdir(elsewhere)), [], "nothing behind the link was written")

    def test_a_sids_own_directory_loose_then_refused_then_loose_again_in_one_episode_is_two_loose_rows_and_another_sids_latch_stands(self):
        """THE PER-SID MIRROR of the previous case (the same ruling): hosts/ 0700, the first and the second session's <sid>/
        at 0775 with an identity of ours, each read in its own episode (a loose row each); the first session's directory
        replaced by a regular file at its path and read again in the same episode (the refused row, this session's:
        `host directory <hosts/<sid>> is not a directory`, the answer False), then a new <sid>/ of ours at 0775 made at the
        path and read: a SECOND loose row for it, in the one episode, the refusal having been a state of the directory. The
        second session's latch stands untouched through the refusal (its entry, the 0775 it observed), and hosts/, tight,
        has no row. Red before at the fifth commit: two loose rows where three are expected, `Lists differ: [(<c1>, '0775'),
        (<c2>, '0775')] != [(<c1>, '0775'), (<c2>, '0775'), (<c1>, '0775')]`.
        Mutation (a scratch copy, python -B): the refusal's pop dropped reds here the same way."""
        d, be = self._be()
        Path(d, "session-hosts").write_text("off")
        c1, c2 = SIDS[0], SIDS[1]
        dirs = {sid: self._sid_dir(d, sid, hosts_mode=0o700, sid_mode=0o775, identity={"pid": 7, "start": "p"}) for sid in (c1, c2)}
        hosts = Path(d) / "hosts"
        sessions = {sid: self._session_for(sid, "web%d" % i) for i, sid in enumerate((c1, c2))}
        for sid in (c1, c2):
            be._loose_rows_new_episode(sessions[sid])
            self.assertIs(be._host_lease_applies(sessions[sid]), True)
        expect = [(str(dirs[c1]), "0775"), (str(dirs[c2]), "0775")]
        self.assertEqual(self._loose(d), expect, "each session's own loose directory once; hosts/ is tight")
        shutil.rmtree(dirs[c1])
        dirs[c1].write_text("not a directory")
        self.assertIs(be._host_lease_applies(sessions[c1]), False, "refused: the plant at the directory's path")
        self.assertEqual(self._refused(d), [("host.directory-refused", None, None)])
        self.assertEqual(self._rows(d, "host.directory-refused")[0]["sid"], c1, "this session's subject")
        self.assertEqual(be._loose_filed[c2], {str(dirs[c2]): 0o775}, "another session's latch is untouched by the refusal")
        dirs[c1].unlink()
        self._sid_dir(d, c1, hosts_mode=0o700, sid_mode=0o775, identity={"pid": 7, "start": "p"})
        self.assertIs(be._host_lease_applies(sessions[c1]), True, "a new directory of ours at the path, its identity vouches")
        self.assertEqual(self._loose(d), expect + [(str(dirs[c1]), "0775")],
                         "the directory seen loose again after the refusal, in the same episode, is a transition and files")
        self.assertEqual(be._loose_filed[c1], {str(dirs[c1]): 0o775}, "the latch reads the new mode")
        self.assertEqual(be._loose_filed[c2], {str(dirs[c2]): 0o775}, "and the other session's still stands")
        self.assertEqual(be._loose_filed[None], {str(hosts): 0o700}, "hosts/ observed tight, no row")
        self.assertEqual(len(self._refused(d)), 1)

    def test_the_connect_loop_opens_the_loose_row_episode_at_its_top_before_the_first_descent(self):
        """WHERE the episode opens, pinned by the structure of the connect loop (kernel/sdk_backend.py, SdkSession._amain,
        its `while not self.ended` reconnect loop), since driving that loop needs the SDK's client. What it guards: the
        latch the previous case proves by execution (_loose_rows_new_episode, then the rows again) is reset once per
        iteration, before the iteration's first descent under hosts/ (the lease-applies read, or _host_transport_for,
        whose leftover trigger is the first descent with hosts on), and under no condition (no If, For, While or Match
        between the call and the loop body), so one episode is one iteration. Read by ast and not by text: the call's
        line precedes both descents' lines, and its ancestors up to the loop are statements that always run."""
        import ast
        tree = ast.parse(open(os.path.join(ROOT, "kernel", "sdk_backend.py")).read())
        cls = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "SdkSession"][0]
        amain = [n for n in cls.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "_amain"][0]
        def calls_in(node, attr):
            return [n for n in ast.walk(node) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == attr]
        loops = [n for n in ast.walk(amain) if isinstance(n, ast.While) and ast.unparse(n.test) == "not self.ended"
                 and calls_in(n, "_host_lease_applies")]
        self.assertEqual(len(loops), 1, "the one `while not self.ended` loop of _amain that connects (the other feeds turns)")
        loop = loops[0]
        parents = {}
        for node in ast.walk(loop):
            for child in ast.iter_child_nodes(node):
                parents[child] = node

        def calls(attr):
            return calls_in(loop, attr)
        begin = calls("_loose_rows_new_episode")
        self.assertEqual(len(begin), 1, "the loop opens the episode once per iteration")
        descents = calls("_host_lease_applies") + calls("_host_transport_for")
        self.assertEqual(len(descents), 2, "the two entries to a descent under hosts/ in the loop")
        self.assertLess(begin[0].lineno, min(c.lineno for c in descents), "the episode opens before the iteration's first descent")
        chain, node = [], parents[begin[0]]
        while node is not loop:                       # the ancestors between the call and the loop, the loop itself excluded
            chain.append(type(node).__name__)
            node = parents[node]
        self.assertEqual([c for c in chain if c in ("If", "For", "AsyncFor", "While", "Match", "IfExp")], [],
                         "the call runs on every iteration, under no condition: %r" % (chain,))
        self.assertTrue(hasattr(sb.SdkBackend, "_loose_rows_new_episode"), "the method the loop calls exists on the backend")

    def test_a_directory_of_ours_with_no_search_bit_is_the_fault_it_is_out_of_the_lease_applies_road_and_the_other_roads_arms_answer_it(self):
        """THE FAULT CELL on the three read roads (the round-7 sixth addendum, 2026-09-20, disclosing a cell the fifth
        addendum changed without saying so): a `<sid>/` of ours at 0600 under a 0700 hosts/, identity.json (host.log for
        the served road) of ours inside it, driven as the shape table's cells are. The descent admits the directory (its
        O_RDONLY|O_DIRECTORY open needs the read bit, which 0600 has) and the fstatat of the name under it refuses (the
        search bit, which it lacks): a PermissionError with errno EACCES, a FAULT of the directory and not a shape at the
        name, so no host.directory-refused row on any road and no loose row (0600 is tight). LEASE-APPLIES, hosts off: the
        fault propagates OUT of the road, which has no OSError arm, to the connect loop's handler (SdkSession._amain's
        except records it as the launch error and ends the connect; pinned here at the road, the loop needing the SDK's
        client to drive). That is the answer this PR's base gave: there the existence read was `Path.exists()` by path,
        and pathlib re-raises every errno but ENOENT, ENOTDIR, EBADF and ELOOP, so the same directory raised the same
        PermissionError out of _host_lease_applies; the second through fourth addenda answered False through
        host_file_exists's `except OSError` arm and said nothing of it; the fifth dropped the arm and said nothing
        either. SERVED: the OSError arm the road has had since the base returns, none of the file's rows filed and no
        position kept. ORPHAN, a journal segment present: the identity read's fault is swallowed by the road's OSError arm
        (raw None; the base's `except Exception` around its read_text did the same), no identity vouches for the ack, and
        the road then raises the same PermissionError from its journal reads: through #814 from the by-path open of the
        segment (the glob's listing needed the read bit only, the open the search bit); since the fork PR that follows
        #814 from the listing's OWNER QUESTION, the fstatat of the segment's name under the held descriptor
        (journal_has_tail, read_journal_dir, journal_segments, then _stat_name, the innermost frames, in that order: the
        scandir off the descriptor needs the read bit only), the same fault at the same road, its frame moved with the
        reads. No romp code path makes such a directory (the helpers make 0700). Red at the fourth addendum's commit on the
        lease-applies arm, `PermissionError not raised` (host_file_exists answered False through its arm), and the same
        red under the mutation that puts the arm back at this commit; the served and orphan arms are the base's and hold
        at both. Root ignores the search bit and is skipped."""
        import errno, traceback
        if os.geteuid() == 0:
            self.skipTest("root bypasses the search bit")
        identity = json.dumps({"pid": 7, "start": "p"})
        log_rows = "".join(json.dumps(r) + "\n" for r in [{"t": 1, "kind": "end-forced", "cliPid": 5}])
        for road in ("lease-applies", "orphan", "served"):
            with self.subTest(road=road):
                d, be = self._be()
                name = "host.log" if road == "served" else "identity.json"
                sdir = self._loose_sid(d, sid_mode=0o700, journal=1 if road == "orphan" else 0)
                (sdir / name).write_text(log_rows if road == "served" else identity)
                os.chmod(sdir, 0o600)
                self.addCleanup(os.chmod, sdir, 0o700)             # before the state dir's rmtree (cleanups run last-in first)
                s = types.SimpleNamespace(sid=SID, name="web", _host_intent=True, _host=None, _host_is_attach=False, _seed_for_dead_cli=lambda cli: None)
                if road == "lease-applies":
                    Path(d, "session-hosts").write_text("off")
                    try:
                        answer = be._host_lease_applies(s)
                    except PermissionError as e:                 # by hand, not assertRaises: that drops the traceback the frame check reads
                        fault, frames = e, [f.name for f in traceback.extract_tb(e.__traceback__)]
                    else:
                        self.fail("PermissionError not raised: the road answered %r to a fault of the directory" % (answer,))
                    self.assertEqual(fault.errno, errno.EACCES, "the stat's own fault, out of the road")
                    self.assertIn("_stat_name", frames, "raised by the owner question's stat: %r" % (frames,))
                elif road == "orphan":
                    sb.write_reg(Path(d), SID, {"sid": SID, "name": "web", "alive": True, "lastSid": SID,
                                                 "hostAck": {"host": "7:p", "cli": "8:c", "offset": 1}})
                    acks = []
                    capture = classmethod(lambda cls, hdir, ack=-1, **kw: acks.append(ack) or types.SimpleNamespace(hdir=hdir))
                    with mock.patch.dict(sys.modules, {"claude_agent_sdk": self._sdk_stub()}), \
                         mock.patch.object(ht.HostTransport, "from_journal", capture), mock.patch.object(be, "_replay_drain", mock.AsyncMock()):
                        try:
                            asyncio.run(be._host_orphan_recover(s, types.SimpleNamespace(), None, (None, None, None), died=False))
                        except PermissionError as e:
                            fault, frames = e, [f.name for f in traceback.extract_tb(e.__traceback__)]
                        else:
                            self.fail("PermissionError not raised out of the orphan road")
                    self.assertEqual(fault.errno, errno.EACCES)
                    ours = ("_host_orphan_recover", "journal_has_tail", "read_journal_dir", "journal_segments", "_stat_name")
                    self.assertEqual([f for f in frames if f in ours], list(ours),
                                     "the fault that escapes is the journal listing's owner question under the held descriptor, "
                                     "not the identity read's (answered by the road's OSError arm; _stat_name once, from the listing): %r" % (frames,))
                    self.assertEqual(acks, [], "no replay was reached")
                    self.assertNotIn("host.tail-replayed", self._kinds(d))
                else:
                    sb.write_reg(Path(d), SID, {"sid": SID, "name": "web", "alive": True})
                    self.assertIsNone(be._file_host_log_rows(types.SimpleNamespace(sid=SID, name="web", _host=None)), "the arm returns")
                    self.assertNotIn("host.end-forced", self._kinds(d), "none of the file's rows: it was not read")
                    self.assertIsNone((sb.read_reg(Path(d), SID) or {}).get("hostLogPos"), "no position from a file that was not read")
                self.assertEqual(self._refused(d), [], "%s: a fault of the directory is no refusal row" % road)
                self.assertEqual(self._rows(d, "host.directory-loose"), [], "%s: 0600 and 0700 are tight" % road)
                self.assertEqual(self._modes(d), (0o700, 0o600), "the read changed no mode")

    def test_a_foreign_host_log_under_the_spawn_roads_directory_refuses_the_launch_at_the_mark_and_a_refused_arm_reads_none_of_it(self):
        """THE SPAWN ROAD's two answers to a host.log another uid owns (the round-7 seventh addendum of fork PR #814's
        review, 2026-09-20), driven through _host_transport_for with the launcher replaced (_spawn_host: a host that
        exits 1 at once, the way tests/test_session_host_sdk_pin.py drives the refused arm) over a 0700 hosts/<sid>/ of
        ours, the shape the helpers leave, which keeps every entry a peer planted while the directory was loose. AT THE
        MARK: the file stands before the spawn, on the road that meets a standing directory and clears nothing (a stale
        kernel-held lease: host_lease_state "none" with a lease, so the leftover trigger does not run, and lease_state
        not valid, so the launch proceeds); the watermark's stat is the owner question (host_log_mark through
        _stat_name), HostFileForeign, and the launch is refused the way every refusal of this road is
        (_refuse_host_directory): one host.directory-refused row with `file` host.log, `uid` and the owner's remedy, the
        launch error "was not started", NO process started (the launcher never called), no position, the file and the
        modes untouched. ON A REFUSED ARM: the file is planted by the launcher's stand-in, after the mark (nothing but
        this uid can create an entry under a 0700 directory, so no peer has this road; the arm's handler is the design's,
        every read asking), and the arm's three reads are one refusal (_refused_launch_log): one host.directory-refused
        row whose clause is the arm's ("exited before serving its socket (code 1), and its host.log is not read"), no
        reason of the peer's on the card (the no-reason message, host.stderr unwritten), no host.sdk-untested row for the
        untested row the file carries, no hostLogPos, then the arm's own row. The stub is descriptor-only and its
        path-stat count is 0 on both arms. Red before at the sixth addendum's commit, both arms reaching their
        assertions: at the mark the launcher was called (`Lists differ` on the spawned list) and the peer's `error` was
        the card's reason; on the arm the card read `see hosts/<sid>/host.log: PeerPlantedError`, the peer's untested row
        was filed as host.sdk-untested and hostLogPos read the peer's line count."""
        euid = os.geteuid()
        peer_rows = [{"t": 1, "kind": "host-started"},
                     {"t": 2, "kind": "sdk-version-untested", "installed": "9.9.9", "tested": sh.SDK_TESTED_VERSION, "relation": "newer"},
                     {"t": 3, "kind": "host-crashed", "error": "PeerPlantedError", "errno": 99, "at": "peer.py:1"}]
        planted = "".join(json.dumps(r) + "\n" for r in peer_rows)
        remedy = "A host.log under hosts/<sid>/ that another user owns is not read; remove it, or point the state root elsewhere (ROMP_STATE_DIR or XDG_STATE_HOME)"
        proc = types.SimpleNamespace(poll=lambda: 1, returncode=1, pid=4242, terminate=lambda: None)

        def session():
            return types.SimpleNamespace(sid=SID, name="web", _host_intent=True, _host=None, _host_is_attach=False,
                                         _options_login="", _seed_for_dead_cli=lambda cli: None)

        def launch(be, spawn):
            with mock.patch.object(be, "_spawn_host", spawn), self.assertRaises(sb.CLIConnectionErrorLike) as cm:
                asyncio.run(be._host_transport_for(session(), types.SimpleNamespace(), (None, None, None)))
            return str(cm.exception)

        with self.subTest(arm="the mark, before the spawn"):
            d, be = self._be()
            Path(d, "session-hosts").write_text("on")
            sb.write_reg(Path(d), SID, {"sid": SID, "name": "web", "alive": True, "lastSid": SID})
            sb.write_lease(d, {"sid": SID, "pid": 2 ** 22 - 1, "start": "gone", "t": 0, "holder": {"kind": "kernel", "pid": 2 ** 22 - 2, "start": "gone"}})
            sdir = self._loose_sid(d, sid_mode=0o700, host_log=peer_rows)
            spawned = []
            with foreign_uid(sdir / "host.log") as fu:
                msg = launch(be, lambda sess, spec_path, secret_env=None: spawned.append(spec_path) or proc)
            self.assertEqual(spawned, [], "no process was started: the mark refused the launch")
            self.assertEqual(msg, "the session host was not started: host.log in host directory %s belongs to uid %d, not to us (uid %d). %s"
                             % (sdir, euid + 1, euid, remedy))
            self.assertEqual(self._kinds(d), ["host.directory-refused"], "the owner row and nothing else: no exited row, no untested row")
            self.assertEqual(self._refused(d), [("host.directory-refused", "host.log", euid + 1)])
            self.assertEqual(fu.path_stats, 0, "the owner check took a path stat: %r" % (fu.path_stat_calls,))
            self.assertIsNone((sb.read_reg(Path(d), SID) or {}).get("hostLogPos"), "no position from a file that was not read")
            self.assertEqual((sdir / "host.log").read_text(), planted, "the file untouched")
            self.assertEqual(self._modes(d), (0o700, 0o700), "the helpers found both directories tight and changed nothing")
        with self.subTest(arm="a refused arm, after the spawn"):
            d, be = self._be()
            Path(d, "session-hosts").write_text("on")
            sb.write_reg(Path(d), SID, {"sid": SID, "name": "web", "alive": True, "lastSid": SID})
            stubs = []

            def spawn_and_plant(sess, spec_path, secret_env=None):
                log = Path(spec_path).parent / "host.log"
                log.write_text(planted)
                stub = foreign_uid(log)
                stub.__enter__()
                self.addCleanup(stub.__exit__, None, None, None)
                stubs.append(stub)
                return proc
            msg = launch(be, spawn_and_plant)
            sdir = Path(d) / "hosts" / SID
            self.assertEqual(msg, "the session host exited before serving its socket (code 1); hosts/%s/host.stderr carries nothing from this "
                                  "launch; see hosts/%s/host.log" % (SID, SID), "no reason of the peer's on the card: the no-reason arm")
            self.assertEqual(self._kinds(d), ["host.directory-refused", "host.exited-before-socket"],
                             "the owner row, then the arm's own row; no host.sdk-untested for the peer's untested row")
            row = self._rows(d, "host.directory-refused")[0]
            self.assertEqual(row["text"], "the session host for web exited before serving its socket (code 1), and its host.log is not read: host.log "
                                          "in host directory %s belongs to uid %d, not to us (uid %d). %s" % (sdir, euid + 1, euid, remedy))
            self.assertEqual((row["file"], row["uid"]), ("host.log", euid + 1), "the row's fields name the file and the owner")
            self.assertIsNone((sb.read_reg(Path(d), SID) or {}).get("hostLogPos"), "no position from a file that was not read")
            self.assertEqual(stubs[0].path_stats, 0, "the owner check took a path stat: %r" % (stubs[0].path_stat_calls,))
            self.assertEqual((sdir / "host.log").read_text(), planted, "the file untouched")
            self.assertEqual(self._modes(d), (0o700, 0o700), "the read changed no mode")


    def _session(self):
        return types.SimpleNamespace(sid=SID, name="web", _host_intent=True, _host=None, _host_is_attach=False,
                                     _seed_for_dead_cli=lambda cli: None, _host_end_grace=None, _on_cli_stderr=lambda line: None)

    def test_every_shape_a_peer_can_put_at_a_journal_segment_or_at_gaps_json_is_answered_from_the_table_on_the_lease_applies_and_orphan_roads(self):
        """THE JOURNAL TABLE on the two roads that read the journal (the fork PR that follows #814, 2026-09-21, building the
        item "the journal reads descend by descriptor"): SHAPE_TABLE's 13 (kind, owner) rows planted at a segment's name
        (journal-0.jsonl) and at gaps.json under a loose <sid>/ of ours (0775 under a 0700 hosts/), times the two roads,
        52 cells, each driven through the production road on a fresh backend: _host_lease_applies with hosts off and NO
        identity.json (so the journal listing decides), _host_orphan_recover's lease-less arm with identity.json of ours
        and no registry ack (the replay's offset is -1 whatever vouches). For the gaps.json column a segment of ours
        (three records) stands beside the planted entry. Per cell: the road's answer, the refusal rows as (kind, `file`,
        `uid`), the loose row once, the planted object and its directory never stat'd, opened or listed BY PATH
        (path_ops: 0), the stub's path-stat count 0 on a foreign cell, the mode unchanged where the directory stands, a
        link's target untouched.
        THE ANSWERS. Lease-applies, a segment: `ours` True; `absent` and `not-file` False with no refusal row (a FIFO at a
        segment's name is skipped unopened, so nothing blocks); `foreign` False after ONE host.directory-refused row with
        `file` journal-0.jsonl and `uid` (the peer's segment vouches for no host, the answer a foreign identity.json
        gets); `link` False after the file-shape row (`file`, no `uid`). Lease-applies, gaps.json: True for every kind
        with no refusal row, since this road asks only whether a segment of ours stands and consults gaps.json for
        nothing. Orphan, a segment, read as the replay's offset and the tail row: `ours` [-1] and host.tail-replayed;
        `absent` and `not-file` [] and the log line about nothing past the acknowledged offset, no refusal row; `foreign`
        the owner row, then [] and no tail (a peer's segment is not this session's tail); `link` the file-shape row with
        the clause that the journal is not replayed, [] and no tail (the road refused, as by a link at identity.json).
        Orphan, gaps.json: `ours`, `absent`, `not-file` [-1] and the tail; `foreign` the owner row naming gaps.json, then
        [-1] and the tail (the numbering proceeds as with no gaps file); `link` the file-shape row, [] and no tail.
        RED BEFORE at #814's head (the module copied onto a scratch copy of that tree; the function-level cells cannot
        run there, the reader having no descriptor form): the foreign regular segment on the lease-applies road answered
        `True is not False` (the glob matched the peer's name and no owner was asked); on the orphan road it was replayed,
        `Lists differ: [-1] != []` with host.tail-replayed filed and no owner row; the foreign regular gaps.json filed no
        row (`[] != [('host.directory-refused', 'gaps.json', <uid>)]`); the link cells answered `True is not False` and
        `[-1] != []` with no row on either road (the glob matched the link's name and the reads followed it)."""
        euid = os.geteuid()
        for road in ("lease-applies", "orphan"):
            for name in ("journal-0.jsonl", "gaps.json"):
                for kind, owner, _, expect in SHAPE_TABLE:
                    with self.subTest(road=road, name=name, kind=kind, owner=owner):
                        d, be = self._be()
                        elsewhere = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, elsewhere, True)
                        sdir = self._loose_sid(d, identity={"pid": 7, "start": "p"} if road == "orphan" else None)
                        if name == "gaps.json":
                            write_segment(sdir / "journal-0.jsonl", 3)
                            content = "[1]"
                        else:
                            content = "".join(json.dumps({"type": "assistant", "n": i, "peer": owner == "foreign"}) + "\n" for i in range(3))
                        plant_shape(sdir, name, kind, content, elsewhere)
                        target = (elsewhere / name).read_text() if kind == "symlink-to-file" else None
                        s = self._session()
                        acks = []
                        ctx = foreign_uid(sdir / name) if owner == "foreign" else contextlib.nullcontext()   # its own lstat, before the recorder
                        with path_ops(sdir, sdir / name) as ops:
                            if road == "lease-applies":
                                Path(d, "session-hosts").write_text("off")
                                with ctx as fu:
                                    answer = be._host_lease_applies(s)
                            else:
                                sb.write_reg(Path(d), SID, {"sid": SID, "name": "web", "alive": True, "lastSid": SID})
                                capture = classmethod(lambda cls, dirs, ack=-1, **kw: acks.append(ack) or types.SimpleNamespace(dirs=dirs))
                                with mock.patch.dict(sys.modules, {"claude_agent_sdk": self._sdk_stub()}), ctx as fu, \
                                     mock.patch.object(ht.HostTransport, "from_journal", capture), mock.patch.object(be, "_replay_drain", mock.AsyncMock()):
                                    asyncio.run(be._host_orphan_recover(s, types.SimpleNamespace(), None, (None, None, None), died=False))
                        if road == "lease-applies":
                            if name == "journal-0.jsonl":
                                self.assertIs(answer, expect == "ours", "%s/%s: a host held the session only for a segment of ours" % (kind, owner))
                                rows_expected = expect
                            else:
                                self.assertIs(answer, True, "%s/%s: the segment of ours vouches; gaps.json is not this road's question" % (kind, owner))
                                rows_expected = None
                        else:
                            tail = (expect == "ours") if name == "journal-0.jsonl" else (expect != "link")
                            self.assertEqual(acks, [-1] if tail else [], "%s/%s at %s: the replay's offset, or no replay" % (kind, owner, name))
                            self.assertEqual("host.tail-replayed" in self._kinds(d), tail, "%s/%s at %s: the tail row" % (kind, owner, name))
                            if not tail and expect != "link":
                                self.assertTrue(any("clearing a host directory with nothing past the acknowledged offset" in l for l in be._test_logs), be._test_logs)
                            rows_expected = expect
                        refused = self._refused(d)
                        if rows_expected == "foreign":
                            self.assertEqual(refused, [("host.directory-refused", name, euid + 1)], "%s/%s at %s: the owner row, with the file and the uid" % (kind, owner, name))
                            text = self._rows(d, "host.directory-refused")[0]["text"]
                            self.assertIn("%s in host directory %s belongs to uid %d, not to us (uid %d)" % (name, sdir, euid + 1, euid), text)
                            self.assertIn("A %s under hosts/<sid>/ that another user owns is not read" % name, text)
                            self.assertEqual(fu.path_stats, 0, "the owner check took a path stat: %r" % (fu.path_stat_calls,))
                        elif rows_expected == "link":
                            self.assertEqual(refused, [("host.directory-refused", name, None)], "%s/%s at %s: the file-shape row, no uid" % (kind, owner, name))
                            text = self._rows(d, "host.directory-refused")[0]["text"]
                            self.assertIn("%s in host directory %s is a symlink, not a regular file" % (name, sdir), text)
                            if road == "orphan":
                                self.assertIn("is gone, and its journal is not replayed", text)
                        else:
                            self.assertEqual(refused, [], "%s/%s at %s: no refusal row" % (kind, owner, name))
                        self.assertEqual(ops, [], "%s/%s at %s: the planted object or its directory was stat'd, opened or listed by PATH: %r" % (kind, owner, name, ops))
                        if fu is not None:
                            self.assertEqual(fu.path_stats, 0, "a path stat on the planted object: %r" % (fu.path_stat_calls,))
                        self.assertEqual([(r["path"], r["mode"]) for r in self._rows(d, "host.directory-loose")], [(str(sdir), "0775")], "the loose <sid>/, once")
                        if sdir.exists():
                            self.assertEqual(self._modes(d), (0o700, 0o775), "the read changed no mode")
                        if target is not None:
                            self.assertEqual((elsewhere / name).read_text(), target, "nothing behind the link was touched")

    def test_a_sid_renamed_away_and_relinked_between_the_descent_and_the_listing_is_never_read_on_the_orphan_road(self):
        """THE SWAP on the production road (the fork PR that follows #814): our <sid>/ holds identity.json and NO journal;
        a peer's directory outside hosts/ holds a three-record segment. Inside the road's first directory listing
        (os.scandir wrapped: the swap lands after the descent, before the listing runs), our <sid>/ is renamed aside and a
        link to the peer's directory put at its name. The listing runs on the held descriptor, so it reads our moved
        directory: no tail, no replay (the from_journal capture sees nothing), the log line about nothing past the
        acknowledged offset, and neither the peer's directory nor its segment nor the link's path is stat'd, opened or
        listed by PATH (path_ops: 0). The removal road then refuses the link at <sid> on its own descent and says so;
        the peer's directory holds what the peer put there and our moved directory stands. RED BEFORE at #814's head:
        the glob's scandir took the PATH, so the same wrapper swapped and then listed the peer's directory through the
        link, and the peer's tail was replayed: `Lists differ: [-1] != []`, host.tail-replayed filed, and the recorder
        read `[('scandir', '<hosts>/<sid>'), ('open', '<hosts>/<sid>/journal-0.jsonl')]`."""
        d, be = self._be()
        sdir = self._loose_sid(d, sid_mode=0o700, identity={"pid": 7, "start": "p"})
        peer = Path(d) / "peer" / SID
        peer.mkdir(parents=True, mode=0o755)
        write_segment(peer / "journal-0.jsonl", 3, peer=True)
        sb.write_reg(Path(d), SID, {"sid": SID, "name": "web", "alive": True, "lastSid": SID})
        link, moved = Path(d) / "hosts" / SID, Path(d) / "hosts" / (SID + ".moved")
        acks, swapped = [], []
        capture = classmethod(lambda cls, dirs, ack=-1, **kw: acks.append(ack) or types.SimpleNamespace(dirs=dirs))
        with path_ops(peer, peer / "journal-0.jsonl", link, link / "journal-0.jsonl") as ops:
            counted_scandir = os.scandir

            def scandir_and_swap(*a, **k):
                if not swapped:
                    os.rename(sdir, moved)
                    link.symlink_to(peer)
                    swapped.append(True)
                return counted_scandir(*a, **k)
            with mock.patch.object(os, "scandir", scandir_and_swap), mock.patch.dict(sys.modules, {"claude_agent_sdk": self._sdk_stub()}), \
                 mock.patch.object(ht.HostTransport, "from_journal", capture), mock.patch.object(be, "_replay_drain", mock.AsyncMock()):
                asyncio.run(be._host_orphan_recover(self._session(), types.SimpleNamespace(), None, (None, None, None), died=False))
        self.assertEqual(swapped, [True], "the swap landed inside the listing, after the descent")
        self.assertEqual(acks, [], "no tail: the directory the descent verified holds no journal, and the peer's was never listed")
        self.assertNotIn("host.tail-replayed", self._kinds(d))
        self.assertTrue(any("clearing a host directory with nothing past the acknowledged offset" in l for l in be._test_logs), be._test_logs)
        self.assertEqual(ops, [], "the peer's directory, its segment or the link's path was stat'd, opened or listed by PATH: %r" % (ops,))
        self.assertTrue(link.is_symlink(), "the link is left, not replaced")
        self.assertTrue(any("not cleared" in l for l in be._test_logs), "the removal road refused the link at <sid> and said so")
        self.assertEqual(sorted(os.listdir(peer)), ["journal-0.jsonl"], "the peer's directory holds what the peer put there")
        self.assertEqual(sorted(os.listdir(moved)), ["identity.json"], "our directory, moved aside, stands as it was")

    def test_the_owner_row_files_once_per_connect_episode_per_observed_state_and_again_for_a_new_episode_or_a_new_state(self):
        """THE RULE FOR THE OWNER ROW (the reviewer's property of 2026-09-21 03:54Z, built by the fork PR that follows
        #814): one host.directory-refused row per connect episode per OBSERVED STATE, not one per road that observes it.
        WHICH CASE, derived from the row (the derivation stands at _refused_directory_row): the row's fields (`file`,
        `uid`) and its reason and remedy are functions of the observation alone; only the road's clause differs, and it
        words the same consequence of the same fact, so the content does not distinguish the roads and the main case
        holds: the first road to see a state files it, the later ones file nothing. Driven on one backend, hosts off, a
        loose <sid>/ of ours with a foreign identity.json (the stub) and a three-record journal of ours. EPISODE ONE:
        _loose_rows_new_episode, the lease-applies read (the owner row, then the journal of ours vouches: True), then
        _host_transport_for, whose leftover trigger hands the orphan road, which reads the same foreign identity.json
        and replays the tail: ONE owner row, the lease-applies clause on it. EPISODE TWO: the same state, the row again.
        THE SAME EPISODE, A NEW STATE: another uid at identity.json (the stub's delta), a row with that uid; the same uid
        read again, nothing; another FILE (a foreign host.log on the served road, at its hello read and again at its
        exit read), one row for it. RED BEFORE at #814's head: two owner rows in episode one, `Lists differ:
        [('host.directory-refused', 'identity.json', <uid>), ('host.directory-refused', 'identity.json', <uid>)] !=
        [('host.directory-refused', 'identity.json', <uid>)]`, the second with the orphan road's clause."""
        euid = os.geteuid()
        d, be = self._be()
        Path(d, "session-hosts").write_text("off")
        sdir = self._loose_sid(d, identity={"pid": 7, "start": "p"}, journal=3)
        s = self._session()

        def connect():
            capture = classmethod(lambda cls, dirs, ack=-1, **kw: types.SimpleNamespace(dirs=dirs))
            with mock.patch.dict(sys.modules, {"claude_agent_sdk": self._sdk_stub()}), \
                 mock.patch.object(ht.HostTransport, "from_journal", capture), mock.patch.object(be, "_replay_drain", mock.AsyncMock()), \
                 mock.patch.object(ht, "remove_host_dir", lambda *a, **k: True):      # the directory stays for the later steps
                return asyncio.run(be._host_transport_for(s, types.SimpleNamespace(), (None, None, None)))
        with foreign_uid(sdir / "identity.json") as fu:
            be._loose_rows_new_episode(s)
            self.assertIs(be._host_lease_applies(s), True, "the owner row for identity.json, then the journal of ours vouches")
            self.assertIsNone(connect(), "hosts off: the kernel child after the leftover's replay")
        self.assertEqual(fu.path_stats, 0)
        self.assertEqual(self._refused(d), [("host.directory-refused", "identity.json", euid + 1)],
                         "ONE owner row for the episode: the orphan road observed the same state and filed nothing")
        self.assertIn("may have left records this kernel does not read", self._rows(d, "host.directory-refused")[0]["text"], "the first observer's clause")
        self.assertIn("host.tail-replayed", self._kinds(d), "the roads proceeded: the tail of ours was replayed")
        with foreign_uid(sdir / "identity.json"):
            be._loose_rows_new_episode(s)
            self.assertIs(be._host_lease_applies(s), True)
        self.assertEqual(len(self._refused(d)), 2, "a new episode files the standing state again")
        with foreign_uid(sdir / "identity.json", delta=2):
            self.assertIs(be._host_lease_applies(s), True)
            self.assertIs(be._host_lease_applies(s), True)
        self.assertEqual(self._refused(d)[2:], [("host.directory-refused", "identity.json", euid + 2)],
                         "another uid at the name is a new observed state, filed once however often it is read")
        (sdir / "host.log").write_text(json.dumps({"t": 1, "kind": "end-forced", "cliPid": 5}) + "\n")
        with foreign_uid(sdir / "host.log"):
            be._file_host_log_rows(types.SimpleNamespace(sid=SID, name="web", _host=None))     # the hello's read
            be._file_host_log_rows(types.SimpleNamespace(sid=SID, name="web", _host=None))     # the exit's read, same episode
        self.assertEqual(self._refused(d)[3:], [("host.directory-refused", "host.log", euid + 1)], "another file is a new state, filed once")
        self.assertEqual(len(self._refused(d)), 4)

    def test_a_hosts_that_is_a_file_or_a_link_refused_for_two_sids_is_one_owner_row_and_the_second_refusal_still_answers(self):
        """THE SHARED SUBJECT OF THE REFUSED ROW (the reviewer's ruling of 2026-09-21 07:19Z; THE RULE at
        _file_loose_directory_rows, the subject decided by path at _refused_directory_row): hosts/ replaced by a regular
        file, and separately by a symlink to a directory elsewhere, two sessions connecting with hosts off (the
        lease-applies descent refuses its first component, `hosts directory <path> is not a directory` or `is a symlink,
        not a directory`, a text with no sid in it): ONE host.directory-refused row, the first observer's, and the second
        session's road still answers False (no host this kernel can vouch for) with no row. A third connect with hosts on
        (the leftover trigger of _host_transport_for) is still the LAUNCH's refusal, `the session host was not started:
        <the same reason>. <the directory remedy, with the spawn road's 0700 clause>`, and still no row: the latch keys on
        the reason, which is the observation, and not on the remedy, whose 0700 clause is the road's (mode_checked). On
        the link arm, THE TRANSITION AND THE RETURN: the
        link replaced by a directory of ours and a session's descent admits it (observed healthy: the shared entry
        forgotten), then the link planted again and observed by another: a second row, a refusal that returned after a
        repair. Red before at fork PR #884's fourth commit, the latch per sid: two rows for the two sessions,
        `Lists differ: [('host.directory-refused', None, None), ('host.directory-refused', None, None)] !=
        [('host.directory-refused', None, None)]`. Mutation (a scratch copy, python -B): the owner put back to the
        observing sid reds here the same way."""
        elsewhere = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, elsewhere, True)
        remedy = ("A hosts/ or hosts/<sid>/ that is not a directory this user owns is refused; replace it with a directory, "
                  "or point the state root elsewhere (ROMP_STATE_DIR or XDG_STATE_HOME)")
        for arm in ("a regular file", "a symlink"):
            with self.subTest(arm=arm):
                d, be = self._be()
                Path(d, "session-hosts").write_text("off")
                hosts = Path(d) / "hosts"
                if arm == "a regular file":
                    hosts.write_text("not a directory")
                    reason = "hosts directory %s is not a directory" % hosts
                else:
                    hosts.symlink_to(elsewhere)
                    reason = "hosts directory %s is a symlink, not a directory" % hosts
                sessions = [self._session_for(sid, "web%d" % i) for i, sid in enumerate(SIDS)]
                for s in sessions[:2]:
                    sb.write_reg(Path(d), s.sid, {"sid": s.sid, "name": s.name, "alive": True, "lastSid": s.sid})
                    be._loose_rows_new_episode(s)
                    self.assertIs(be._host_lease_applies(s), False, "%s: the refusal answers, no host this kernel can vouch for" % s.name)
                self.assertEqual(self._refused(d), [("host.directory-refused", None, None)],
                                 "%s: one row for the one shared directory, the second session's observation latched" % arm)
                row = self._rows(d, "host.directory-refused")[0]
                self.assertEqual(row["text"], "the session host for web0 may have left records this kernel does not read: %s. %s" % (reason, remedy))
                self.assertEqual(row["sid"], SIDS[0], "the first observer's")
                Path(d, "session-hosts").write_text("on")
                sb.write_reg(Path(d), SIDS[2], {"sid": SIDS[2], "name": "web2", "alive": True, "lastSid": SIDS[2]})
                be._loose_rows_new_episode(sessions[2])
                with self.assertRaises(sb.CLIConnectionErrorLike) as cm:
                    asyncio.run(be._host_transport_for(sessions[2], types.SimpleNamespace(), (None, None, None)))
                self.assertEqual(str(cm.exception), "the session host was not started: %s. %s" % (reason, remedy.replace("owns is", "owns at 0700 is")),
                                 "the launch's refusal still carries the reason and the spawn road's remedy")
                self.assertEqual(len(self._refused(d)), 1, "the third observation, on the spawn road, files nothing: the same state")
                if arm == "a symlink":
                    hosts.unlink()
                    self._sid_dir(d, SIDS[1], hosts_mode=0o700, sid_mode=0o700, identity={"pid": 7, "start": "p"})
                    Path(d, "session-hosts").write_text("off")
                    self.assertIs(be._host_lease_applies(sessions[1]), True, "repaired: the descent admits hosts/ and the identity of ours vouches")
                    self.assertEqual(len(self._refused(d)), 1, "an admitted directory files no refusal row")
                    shutil.rmtree(hosts)
                    hosts.symlink_to(elsewhere)
                    self.assertIs(be._host_lease_applies(sessions[0]), False)
                    self.assertEqual(len(self._refused(d)), 2, "the link returned after the repair: a changed observation, filed again")
                    self.assertEqual(self._rows(d, "host.directory-refused")[1]["sid"], SIDS[0])
                    self.assertIs(be._host_lease_applies(sessions[1]), False)
                    self.assertEqual(len(self._refused(d)), 2, "and latched again for the next observer")
                self.assertEqual(sorted(os.listdir(elsewhere)), [], "nothing behind the link was written")

    def test_a_fifo_or_a_directory_of_ours_at_spawn_json_refuses_the_launch_naming_the_kind_and_nothing_blocks(self):
        """THE WRITE SIDE on the production road (the fork PR that follows #814, building the small-asks item on the two
        O_WRONLY opens): hosts on, a stale kernel-held lease (host_lease_state "none" with a lease, so the leftover trigger
        does not run and the standing directory is cleared by nothing, the road the mark case drives), a 0700 <sid>/ of
        ours (the helpers' shape, which keeps every entry planted while it was loose) with a FIFO, then a directory,
        standing at spawn.json. write_spawn_spec's opener asks the shape
        question before any open and refuses by kind: the launch error names the file and the kind with the kind's remedy,
        one host.directory-refused row with `file` spawn.json and `fileKind`, no uid, the launcher never called, the entry
        standing, and the road back within the bound. RED BEFORE at #814's head, the FIFO arm: the O_WRONLY open of the
        FIFO blocked inside the road until the case's watchdog opened a reader end at 5 s (the drives verifier's
        `BLOCKED 2.00 s, released by a reader end`), after which the spec was written INTO the FIFO and the launcher was
        called; the directory arm was the open's own EISDIR, a launch error with errno 21 and no row."""
        for arm, plant, kind in (("fifo", os.mkfifo, "FIFO"), ("directory", lambda p: os.mkdir(p, 0o700), "directory")):
            with self.subTest(arm=arm):
                d, be = self._be()
                Path(d, "session-hosts").write_text("on")
                sdir = self._loose_sid(d, sid_mode=0o700)
                plant(sdir / "spawn.json")
                sb.write_reg(Path(d), SID, {"sid": SID, "name": "web", "alive": True, "lastSid": SID})
                sb.write_lease(d, {"sid": SID, "pid": 2 ** 22 - 1, "start": "gone", "t": 0, "holder": {"kind": "kernel", "pid": 2 ** 22 - 2, "start": "gone"}})
                spawned, released = [], []

                def release():                                        # the base's road blocks on the FIFO: a reader end lets the case end
                    try:
                        released.append(os.open(sdir / "spawn.json", os.O_RDONLY | os.O_NONBLOCK))
                    except OSError:
                        pass
                watchdog = threading.Timer(5.0, release)
                watchdog.daemon = True
                watchdog.start()
                t0 = time.time()
                try:
                    with mock.patch.object(be, "_spawn_host", lambda sess, spec_path, secret_env=None: spawned.append(spec_path) or types.SimpleNamespace(poll=lambda: 1, returncode=1, pid=1)), \
                         self.assertRaises(sb.CLIConnectionErrorLike) as cm:
                        asyncio.run(be._host_transport_for(self._session(), types.SimpleNamespace(), (None, None, None)))
                finally:
                    watchdog.cancel()
                    for fd in released:
                        os.close(fd)
                self.assertLess(time.time() - t0, 4.0, "the road returned without a reader end: nothing blocked")
                self.assertEqual(released, [], "the watchdog never fired")
                self.assertEqual(str(cm.exception), "the session host was not started: spawn.json in host directory %s is a %s, not a regular file. "
                                                    "A spawn.json under hosts/<sid>/ that is a %s, not a regular file, is refused; remove it, or point the "
                                                    "state root elsewhere (ROMP_STATE_DIR or XDG_STATE_HOME)" % (sdir, kind, kind))
                self.assertEqual(spawned, [], "no process was started")
                self.assertEqual(self._refused(d), [("host.directory-refused", "spawn.json", None)])
                row = self._rows(d, "host.directory-refused")[0]
                self.assertEqual(row.get("fileKind"), kind, "the row names the kind")
                self.assertEqual(self._kinds(d), ["host.directory-refused"], "the refusal row and nothing else")
                st = os.lstat(sdir / "spawn.json").st_mode
                self.assertTrue(stat.S_ISFIFO(st) if arm == "fifo" else stat.S_ISDIR(st), "the entry stands, untouched")


class ReadDescent(unittest.TestCase):
    """The read roads' descent and its three readers at function level (host_transport.open_host_dirs_if_present,
    host_file_exists, read_host_file, host_sock_present; the round-7 second addendum of fork PR #814's review,
    2026-09-20): the spawn road's precondition ported in the two parts that guard a read (each component opened
    O_DIRECTORY|O_NOFOLLOW off the state root and fstat-verified a directory of this uid, the file or the name then taken
    relative to the descriptor) and not in the third (the mode), with an absent component answered None."""

    def _root(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        return Path(d)

    def test_absent_answers_none_a_loose_directory_of_ours_is_admitted_and_every_other_shape_is_refused(self):
        root = self._root()
        self.assertIsNone(ht.open_host_dirs_if_present(root, SID), "no hosts/ at all: None, not a refusal")
        hosts = root / "hosts"
        hosts.mkdir(mode=0o775)                                        # loose, ours: an install from before 2026-09-19
        self.assertIsNone(ht.open_host_dirs_if_present(root, SID), "hosts/ with no <sid>: None")
        (hosts / SID).mkdir(mode=0o775)
        dirs = ht.open_host_dirs_if_present(root, SID)
        self.assertIsNotNone(dirs, "a loose directory of ours at both components is admitted: the mode is not this descent's condition")
        with dirs:
            self.assertEqual(os.fstat(dirs.hosts).st_ino, os.lstat(hosts).st_ino, "the first descriptor is hosts/")
            self.assertEqual(os.fstat(dirs.dir).st_ino, os.lstat(hosts / SID).st_ino, "the second is hosts/<sid>/")
        # the absence is its own class, a subclass, so the spawn road's callers see the refusal they always saw
        with self.assertRaises(ht.HostDirRefused) as cm:
            ht.open_host_dirs(self._root(), SID)
        self.assertIsInstance(cm.exception, ht.HostDirAbsent)
        self.assertIn("does not exist", str(cm.exception))
        self.assertIsNone(cm.exception.errno)
        # a link at hosts/, a link at <sid>, a file at <sid>: each refused under the parent class, never Absent
        peer = self._root() / "peer"
        (peer / SID).mkdir(parents=True, mode=0o755)
        for arm, plant in (("link at hosts/", lambda r: (r / "hosts").symlink_to(peer)),
                           ("link at <sid>", lambda r: ((r / "hosts").mkdir(mode=0o700), (r / "hosts" / SID).symlink_to(peer / SID))),
                           ("file at <sid>", lambda r: ((r / "hosts").mkdir(mode=0o700), (r / "hosts" / SID).write_text("")))):
            with self.subTest(arm=arm):
                r = self._root()
                plant(r)
                with self.assertRaises(ht.HostDirRefused) as cm:
                    ht.open_host_dirs_if_present(r, SID)
                self.assertNotIsInstance(cm.exception, ht.HostDirAbsent, arm)
                self.assertIn("is a symlink, not a directory" if "link" in arm else "is not a directory", str(cm.exception))
                self.assertIn("hosts directory %s" % (r / "hosts") if arm == "link at hosts/" else "host directory %s" % (r / "hosts" / SID), str(cm.exception))
        # a foreign uid at <sid>, by the fstat of the object opened (a stub keyed on the object, as the removal road's pin)
        r = self._root()
        (r / "hosts" / SID).mkdir(parents=True, mode=0o700)
        st = os.lstat(r / "hosts" / SID)
        ident, real_fstat = (st.st_dev, st.st_ino), os.fstat

        def fstat(fd):
            st = real_fstat(fd)
            if isinstance(fd, int) and stat.S_ISDIR(st.st_mode) and (st.st_dev, st.st_ino) == ident:
                fields = list(st); fields[4] = st.st_uid + 1
                return os.stat_result(fields)
            return st
        with mock.patch.object(os, "fstat", fstat), self.assertRaises(ht.HostDirRefused) as cm:
            ht.open_host_dirs_if_present(r, SID)
        self.assertIn("belongs to uid %d, not to us (uid %d)" % (os.geteuid() + 1, os.geteuid()), str(cm.exception))

    def test_the_readers_take_names_under_the_descriptor_and_a_link_at_the_name_is_refused_naming_the_file(self):
        root = self._root()
        sdir = root / "hosts" / SID
        sdir.mkdir(parents=True, mode=0o700)
        (sdir / "identity.json").write_text(json.dumps({"pid": 7, "start": "p"}))
        peer = self._root() / "theirs.log"
        peer.write_text("the peer's bytes")
        (sdir / "host.log").symlink_to(peer)
        (sdir / "a-dir").mkdir()
        with ht.open_host_dirs_if_present(root, SID) as dirs:
            self.assertEqual(ht.read_host_file("identity.json", dirs), json.dumps({"pid": 7, "start": "p"}).encode())
            self.assertTrue(ht.host_file_exists("identity.json", dirs))
            self.assertIsNone(ht.read_host_file("absent.json", dirs), "no entry at the name: None")
            self.assertFalse(ht.host_file_exists("absent.json", dirs))
            with self.assertRaises(ht.HostDirRefused) as cm:
                ht.read_host_file("host.log", dirs)
            self.assertEqual(cm.exception.file, "host.log", "the refusal names the file, so the caller's remedy is the file's")
            self.assertIn("host.log in host directory %s is a symlink, not a regular file" % sdir, str(cm.exception))
            # a link at the name is refused by the existence reader too since the fourth addendum, naming the file (it
            # answered False here through the third, so the lease-applies road filed no row for the plant the other two
            # roads filed one for)
            with self.assertRaises(ht.HostDirRefused) as cm:
                ht.host_file_exists("host.log", dirs)
            self.assertEqual(cm.exception.file, "host.log")
            self.assertNotIsInstance(cm.exception, ht.HostFileForeign)
            self.assertIn("host.log in host directory %s is a symlink, not a regular file" % sdir, str(cm.exception))
            self.assertEqual(peer.read_text(), "the peer's bytes", "nothing behind the link was opened")
            # a directory at the name: None since the fourth addendum (the answer host_file_exists gives; through the
            # third the fdopen's read raised IsADirectoryError), and since the fifth with NOTHING OPENED: the stat by name
            # before the open reads the kind (the shape table's not-file cell, ReadDescent.test_every_shape_..._table)
            self.assertIsNone(ht.read_host_file("a-dir", dirs))
            self.assertFalse(ht.host_file_exists("a-dir", dirs))

    def test_host_sock_present_reads_the_published_name_under_the_hosts_descriptor_and_not_the_path(self):
        root = self._root()
        (root / "hosts" / SID).mkdir(parents=True, mode=0o700)
        name = ht.host_sock(root, SID).name
        peer = self._root() / "peer"
        (peer / SID).mkdir(parents=True, mode=0o755)
        (peer / name).write_text("the peer's entry at the published name")
        with ht.open_host_dirs_if_present(root, SID) as dirs:
            self.assertFalse(ht.host_sock_present(dirs, name), "nothing published")
            (root / "hosts" / name).touch()
            self.assertTrue(ht.host_sock_present(dirs, name), "an entry at the name in the verified hosts/")
            os.unlink(root / "hosts" / name)
            os.rename(root / "hosts", root / "hosts.moved")          # the swap, after the descent
            (root / "hosts").symlink_to(peer)
            self.assertTrue(ht.host_sock(root, SID).exists(), "by PATH the peer's entry answers: the read the poll made through round 7")
            self.assertFalse(ht.host_sock_present(dirs, name), "by NAME under the descriptor it does not: the descriptor names the directory the spec was written in")
            (root / "hosts.moved" / name).touch()
            self.assertTrue(ht.host_sock_present(dirs, name), "and an entry in that directory does")

    def test_the_readers_check_the_owner_of_the_object_they_hold_and_a_foreign_file_is_the_answer_absent_gets(self):
        """The owner check (the round-7 fourth addendum, 2026-09-20): read_host_file fstats the DESCRIPTOR its O_NOFOLLOW
        open returned, host_file_exists fstatats the NAME under the <sid> descriptor with no link followed, and a file
        whose st_uid is not this euid raises HostFileForeign (a subclass of HostDirRefused and not of HostDirAbsent,
        `file` the entry, `uid` the owner, the directory in the text, errno None). The foreign owner is simulated by the
        stat result the reader sees (foreign_uid: os.fstat of a descriptor and os.stat of a name under a directory
        descriptor answer st_uid + 1 for that one object, keyed on its (st_dev, st_ino); a stat by PATH answers the real
        owner and is counted, and the count is asserted 0, the fifth addendum), because a file another uid owns is not
        constructible without root; every other object answers as before, so the descent's own fstats of the two
        directories still pass. Since the fifth addendum both readers ask the owner question of the NAME before any open
        (_stat_name) and read_host_file asks it again of the descriptor. Red before: both readers read the file as ours
        (`b'...' is not None`, `True is not False`)."""
        root = self._root()
        sdir = root / "hosts" / SID
        sdir.mkdir(parents=True); os.chmod(root / "hosts", 0o700); os.chmod(sdir, 0o775)     # a loose <sid>/ of ours
        (sdir / "identity.json").write_text(json.dumps({"pid": 7, "start": "p"}))
        (sdir / "ours.json").write_text("ours")
        with ht.open_host_dirs_if_present(root, SID) as dirs:
            with foreign_uid(sdir / "identity.json") as fu:
                with self.assertRaises(ht.HostDirRefused) as cm:          # the parent class, so the red before reaches this line
                    ht.read_host_file("identity.json", dirs)
                e = cm.exception
                self.assertIsInstance(e, ht.HostFileForeign)
                self.assertEqual((e.file, e.uid, e.errno), ("identity.json", os.geteuid() + 1, None))
                self.assertEqual(str(e), "identity.json in host directory %s belongs to uid %d, not to us (uid %d)" % (sdir, os.geteuid() + 1, os.geteuid()))
                self.assertNotIsInstance(e, ht.HostDirAbsent)
                with self.assertRaises(ht.HostDirRefused) as cm:
                    ht.host_file_exists("identity.json", dirs)
                self.assertIsInstance(cm.exception, ht.HostFileForeign)
                self.assertEqual((cm.exception.file, cm.exception.uid), ("identity.json", os.geteuid() + 1))
                # the check is on the object, not the name: our other file beside it reads as before under the same stub
                self.assertEqual(ht.read_host_file("ours.json", dirs), b"ours")
                self.assertTrue(ht.host_file_exists("ours.json", dirs))
            self.assertEqual(fu.path_stats, 0, "a reader took a path stat of the planted file: %r" % (fu.path_stat_calls,))
            self.assertEqual(dirs.loose, (("host directory", sdir, 0o775),), "the loose <sid>/ is recorded for the caller's row")
            self.assertEqual(dirs.modes, (("hosts directory", root / "hosts", 0o700), ("host directory", sdir, 0o775)),
                             "every component's mode is recorded, tight ones too, for the once-per-episode-per-mode latch")
            self.assertEqual(ht.read_host_file("identity.json", dirs), json.dumps({"pid": 7, "start": "p"}).encode(), "without the stub, ours")
            self.assertTrue(ht.host_file_exists("identity.json", dirs))
        self.assertEqual((sdir / "identity.json").read_text(), json.dumps({"pid": 7, "start": "p"}), "the file untouched")
        self.assertEqual(stat.S_IMODE(os.stat(sdir).st_mode), 0o775, "the read changed no mode")

    def test_the_read_descent_records_a_loose_component_from_its_own_fstat_and_changes_no_mode(self):
        """The mode row's source (the fourth addendum): with private False the descent still READS each component's mode
        from the fstat it already makes and records a loose one on HostDirs.loose as (what, path, mode); it refuses
        nothing on it and chmods nothing (read, record, proceed). Modes pasted before and after."""
        for hosts_mode, sid_mode, expect in ((0o775, 0o775, ("hosts directory", "host directory")),
                                             (0o700, 0o775, ("host directory",)),
                                             (0o775, 0o700, ("hosts directory",)),
                                             (0o700, 0o700, ())):
            with self.subTest(hosts=oct(hosts_mode), sid=oct(sid_mode)):
                root = self._root()
                (root / "hosts" / SID).mkdir(parents=True)
                os.chmod(root / "hosts", hosts_mode); os.chmod(root / "hosts" / SID, sid_mode)
                before = (stat.S_IMODE(os.lstat(root / "hosts").st_mode), stat.S_IMODE(os.lstat(root / "hosts" / SID).st_mode))
                self.assertEqual(before, (hosts_mode, sid_mode))
                with ht.open_host_dirs_if_present(root, SID) as dirs:
                    self.assertEqual(tuple(w for w, _, _ in dirs.loose), expect)
                    for what, shown, mode in dirs.loose:
                        self.assertEqual((shown, mode), (root / "hosts" if what == "hosts directory" else root / "hosts" / SID,
                                                         hosts_mode if what == "hosts directory" else sid_mode))
                after = (stat.S_IMODE(os.lstat(root / "hosts").st_mode), stat.S_IMODE(os.lstat(root / "hosts" / SID).st_mode))
                self.assertEqual(after, before, "the read descent changes no mode")
                # the spawn road's descent still refuses the loose shape, and records nothing
                if expect:
                    with self.assertRaises(ht.HostDirRefused) as cm:
                        ht.open_host_dirs(root, SID)
                    self.assertIn("is group/world-accessible (mode %04o)" % (hosts_mode if hosts_mode & 0o077 else sid_mode), str(cm.exception))
                else:
                    with ht.open_host_dirs(root, SID) as dirs:
                        self.assertEqual(dirs.loose, ())

    def test_a_fifo_at_the_name_does_not_block_the_read_and_is_not_the_file(self):
        """A FIFO a peer planted at identity.json under a loose <sid>/ of ours: through the third addendum read_host_file's
        O_RDONLY open blocked until a writer appeared, which no writer ever does, so the kernel's connect hung on the
        peer's plant. The fourth addendum gave the open O_NONBLOCK and let the fstat after it answer None; since the fifth
        the FIFO is NOT OPENED AT ALL: the owner question is asked of the name before the open (_stat_name), reads the
        kind, and answers None there, what host_file_exists already said of such an entry (the open keeps O_NONBLOCK for
        a FIFO swapped in between the stat and the open). Pinned here by the open count: os.open is spied and no open of
        the FIFO's name happens. Red before: the reader thread is still alive after the join (`True is not False`)."""
        import threading
        root = self._root()
        sdir = root / "hosts" / SID
        sdir.mkdir(parents=True); os.chmod(root / "hosts", 0o700); os.chmod(sdir, 0o700)
        os.mkfifo(sdir / "identity.json")
        out, opens, real_open = [], [], os.open
        def spy(path, *a, **k):
            opens.append(os.fspath(path))
            return real_open(path, *a, **k)
        with ht.open_host_dirs_if_present(root, SID) as dirs, mock.patch.object(os, "open", spy):
            t = threading.Thread(target=lambda: out.append(ht.read_host_file("identity.json", dirs)), daemon=True)
            t.start(); t.join(5)
            self.assertIs(t.is_alive(), False, "the read returned: the FIFO did not block the open")
            self.assertEqual(out, [None], "a FIFO is not the file")
            self.assertFalse(ht.host_file_exists("identity.json", dirs))
            self.assertEqual(opens, [], "a non-regular entry of ours is answered by the stat of its name, nothing opened")

    def test_every_shape_a_peer_can_put_at_the_name_is_answered_from_the_table_by_both_readers(self):
        """THE SHAPE TABLE at function level (SHAPE_TABLE, module level; the round-7 fifth addendum, 2026-09-20): each of
        the 13 (kind, owner) rows planted at identity.json under a loose <sid>/ of ours and put to both readers, 26 cells.
        `absent`: False, None. `ours`: True, the bytes. `foreign` (the foreign_uid stub, descriptor-only, its path-stat
        count 0): HostFileForeign from both readers, `file` and `uid` set, errno None, whatever the kind, a socket and a
        symlink included, since the owner question is asked of the entry itself before anything is opened. `link`: the
        file-shape HostDirRefused, `file` set, not the foreign class. `not-file`: False, None. Beside the answer: what is
        OPENED (os.open spied): nothing, except the one open by name of a regular file of ours on the read; the mode
        unchanged; a link's target untouched. Red before at the fourth addendum's commit: read_host_file on a foreign
        socket raised `OSError: [Errno 6] No such device or address` (the owner check was the fstat of the opened
        descriptor, which a socket's open never returns), and a foreign symlink answered the link row from both readers
        (`HostDirRefused is not an instance of HostFileForeign`); the non-regular entries of ours were opened."""
        for kind, owner, expect_exists, expect_read in SHAPE_TABLE:
            with self.subTest(kind=kind, owner=owner):
                root = self._root()
                sdir = root / "hosts" / SID
                sdir.mkdir(parents=True); os.chmod(root / "hosts", 0o700); os.chmod(sdir, 0o775)
                elsewhere = self._root()
                plant_shape(sdir, "identity.json", kind, "the bytes", elsewhere)
                target = (elsewhere / "identity.json").read_text() if kind == "symlink-to-file" else None
                ctx = foreign_uid(sdir / "identity.json") if owner == "foreign" else contextlib.nullcontext()
                opens, real_open = [], os.open

                def spy(path, *a, **k):
                    opens.append(os.fspath(path))
                    return real_open(path, *a, **k)
                got = {}
                with ht.open_host_dirs_if_present(root, SID) as dirs, ctx as fu, mock.patch.object(os, "open", spy):
                    for reader, fn in (("exists", ht.host_file_exists), ("read", ht.read_host_file)):
                        try:
                            got[reader] = ("value", fn("identity.json", dirs))
                        except ht.HostFileForeign as e:
                            got[reader] = ("foreign", e.file, e.uid, e.errno)
                        except ht.HostDirRefused as e:
                            got[reader] = ("link", e.file, getattr(e, "uid", None), str(e))
                for reader, expect in (("exists", expect_exists), ("read", expect_read)):
                    answer = got[reader]
                    if expect in ("absent", "not-file"):
                        self.assertEqual(answer, ("value", False if reader == "exists" else None), "%s/%s/%s" % (kind, owner, reader))
                    elif expect == "ours":
                        self.assertEqual(answer, ("value", True if reader == "exists" else b"the bytes"), "%s/%s/%s" % (kind, owner, reader))
                    elif expect == "foreign":
                        self.assertEqual(answer, ("foreign", "identity.json", os.geteuid() + 1, None), "%s/%s/%s" % (kind, owner, reader))
                    else:
                        self.assertEqual(answer[:3], ("link", "identity.json", None), "%s/%s/%s" % (kind, owner, reader))
                        self.assertIn("identity.json in host directory %s is a symlink, not a regular file" % sdir, answer[3])
                self.assertEqual(opens, ["identity.json"] if expect_read == "ours" else [],
                                 "%s/%s: the one open is a regular file of ours, by name; every other shape is answered by the stat of the name" % (kind, owner))
                if fu is not None:
                    self.assertEqual(fu.path_stats, 0, "a reader took a path stat: %r" % (fu.path_stat_calls,))
                self.assertEqual(stat.S_IMODE(os.lstat(sdir).st_mode), 0o775, "the read changed no mode")
                if target is not None:
                    self.assertEqual((elsewhere / "identity.json").read_text(), target, "nothing behind the link was touched")

    def test_an_entry_swapped_in_between_the_stat_and_the_open_is_decided_by_the_fstat_of_the_descriptor(self):
        """THE SECOND CHECK (the fifth addendum): the owner question is asked of the name before the open, and again of the
        descriptor the open returned, because the entry can change in between; the fstat is the authoritative one and
        decides from the same table. Driven by swapping the entry INSIDE the open (os.open wrapped: the swap lands after
        _stat_name saw a regular file of ours and before the real open): a peer's regular file renamed onto the name,
        HostFileForeign from the fstat; a FIFO of ours, None (the O_NONBLOCK open returns, the fstat reads the kind); a
        socket of ours, None through the open's ENXIO arm; a peer's socket, HostFileForeign from the owner question asked
        once more by name in that arm. The stub is descriptor-only and its path-stat count is 0 on every arm, so the
        verifier's mutation of the fstat into a path stat (M5) reds the foreign-file arm here (`HostFileForeign not
        raised`) where the pins that plant the foreign entry before the read cannot see it: the stat by name answers
        them before the mutated line runs. Red before at the fourth addendum's commit: the two socket arms, `OSError:
        [Errno 6] No such device or address`; the file and FIFO arms were the fourth addendum's own behaviour."""
        for arm, kind, owner, expect in (("a peer's regular file", "regular", "foreign", "foreign"),
                                         ("a FIFO of ours", "fifo", "ours", None),
                                         ("a socket of ours", "socket", "ours", None),
                                         ("a peer's socket", "socket", "foreign", "foreign")):
            with self.subTest(arm=arm):
                root = self._root()
                sdir = root / "hosts" / SID
                sdir.mkdir(parents=True); os.chmod(root / "hosts", 0o700); os.chmod(sdir, 0o775)
                (sdir / "identity.json").write_text("ours, at the stat")
                plant_shape(sdir, "swap", kind, "the peer's bytes", self._root())
                ctx = foreign_uid(sdir / "swap") if owner == "foreign" else contextlib.nullcontext()
                real_open, swapped = os.open, []

                def open_and_swap(path, *a, **k):
                    if os.fspath(path) == "identity.json" and k.get("dir_fd") is not None and not swapped:
                        os.rename(sdir / "swap", sdir / "identity.json")       # between the stat by name and the open
                        swapped.append(True)
                    return real_open(path, *a, **k)
                with ht.open_host_dirs_if_present(root, SID) as dirs, ctx as fu, mock.patch.object(os, "open", open_and_swap):
                    if expect == "foreign":
                        with self.assertRaises(ht.HostDirRefused) as cm:
                            ht.read_host_file("identity.json", dirs)
                        self.assertIsInstance(cm.exception, ht.HostFileForeign, arm)
                        self.assertEqual((cm.exception.file, cm.exception.uid), ("identity.json", os.geteuid() + 1))
                    else:
                        self.assertIsNone(ht.read_host_file("identity.json", dirs), arm)
                self.assertEqual(swapped, [True], "the swap landed inside the open, after the stat by name")
                if fu is not None:
                    self.assertEqual(fu.path_stats, 0, "a reader took a path stat: %r" % (fu.path_stat_calls,))

    def test_a_directory_of_ours_with_no_search_bit_is_the_fault_it_is_from_both_readers_with_nothing_opened(self):
        """A FAULT of the directory is not a shape (the round-7 sixth addendum, 2026-09-20): a `<sid>/` of ours at 0600 admits
        the descent (its O_RDONLY|O_DIRECTORY open needs the read bit) and refuses the fstatat of any name under it (the
        search bit), so both readers raise the stat's PermissionError, errno EACCES, not a HostDirRefused of any shape,
        with nothing opened (os.open spied), and neither swallows it into False or None. Through the fourth addendum
        host_file_exists answered False here through an `except OSError` arm around its stat, undisclosed; the fifth
        addendum's _stat_name dropped the arm without saying so; this pin holds it dropped and says so. Red at the fourth
        addendum's commit: `PermissionError not raised` for host_file_exists (read_host_file, whose check was the fstat
        after an open the directory refused, raised it there too). Root ignores the search bit and is skipped."""
        import errno
        if os.geteuid() == 0:
            self.skipTest("root bypasses the search bit")
        root = self._root()
        sdir = root / "hosts" / SID
        sdir.mkdir(parents=True); os.chmod(root / "hosts", 0o700)
        (sdir / "identity.json").write_text("ours")
        os.chmod(sdir, 0o600)
        self.addCleanup(os.chmod, sdir, 0o700)                  # before the root's rmtree (cleanups run last-in first)
        opens, real_open = [], os.open

        def spy(path, *a, **k):
            opens.append(os.fspath(path))
            return real_open(path, *a, **k)
        with ht.open_host_dirs_if_present(root, SID) as dirs, mock.patch.object(os, "open", spy):
            self.assertEqual(dirs.loose, (), "0600 has no group or other bits: nothing loose")
            for reader in (ht.host_file_exists, ht.read_host_file):
                with self.assertRaises(PermissionError, msg=reader.__name__) as cm:
                    reader("identity.json", dirs)
                self.assertEqual(cm.exception.errno, errno.EACCES, reader.__name__)
                self.assertNotIsInstance(cm.exception, ht.HostDirRefused, "%s: a fault is not a refusal" % reader.__name__)
            self.assertEqual([m for _, _, m in dirs.modes], [0o700, 0o600], "the descent admitted both and read their modes")
        self.assertEqual(opens, [], "nothing under the directory was opened")
        self.assertEqual(stat.S_IMODE(os.lstat(sdir).st_mode), 0o600, "the read changed no mode")

    def test_every_shape_a_peer_can_put_at_host_log_is_answered_from_the_table_by_the_spawn_roads_readers(self):
        """THE SHAPE TABLE's fourth road, the spawn road, at function level (SHAPE_TABLE; the round-7 seventh addendum
        of fork PR #814's review, 2026-09-20): each of the 13 (kind, owner) rows planted at host.log under a 0700 <sid>/
        of ours (the spawn road's directory: the helpers tighten it before the descent, and a tightened directory keeps
        every entry a peer planted while it was loose) and put to the three readers the spawn road holds its descent for
        (host_log_mark before the spawn; host_log_rows and host_exit_reason on the refused arms), through that road's own
        descent (open_host_dirs, private): 39 cells. The table's `read` column decides: `absent` and `not-file`, 0, []
        and "" with NOTHING OPENED (os.open spied; a FIFO of ours blocked _open_host_log's open through the sixth
        addendum, no O_NONBLOCK and no stat before it, so that cell is not driven at that head, where it would wedge the
        run); `ours`, the size, the rows and the reason; `foreign` (the descriptor-only stub, its path-stat count 0),
        HostFileForeign from all three readers, `file` host.log and `uid` set, errno None, whatever the kind; `link`, the
        file-shape HostDirRefused. Beside the answer: the two openers open a regular file of ours once each, by name, and
        the mark opens nothing; the mode unchanged; a link's target untouched. Red before at the sixth addendum's
        commit: the readers took (state_dir, sid, dir_fd) there, so this case errors at the call (a TypeError, before
        its assertion) and holds nothing about that head; the behaviour there is the road case's red
        (BackendHostRules, a foreign host.log at the mark and on a refused arm, which reaches its assertions at that
        commit), and at this commit the mutation that drops the owner compare from _stat_name reds every foreign cell
        here."""
        rows = [{"t": 1, "kind": "host-started"}, {"t": 2, "kind": "host-crashed", "error": "PeerPlantedError"}]
        content = "".join(json.dumps(r) + "\n" for r in rows)
        absent = {"mark": 0, "rows": [], "reason": ""}
        ours = {"mark": len(content.encode()), "rows": rows, "reason": "PeerPlantedError"}
        for kind, owner, _, expect in SHAPE_TABLE:
            with self.subTest(kind=kind, owner=owner):
                root = self._root()
                sdir = root / "hosts" / SID
                sdir.mkdir(parents=True); os.chmod(root / "hosts", 0o700); os.chmod(sdir, 0o700)
                elsewhere = self._root()
                plant_shape(sdir, "host.log", kind, content, elsewhere)
                target = (elsewhere / "host.log").read_text() if kind == "symlink-to-file" else None
                ctx = foreign_uid(sdir / "host.log") if owner == "foreign" else contextlib.nullcontext()
                opens, real_open = [], os.open

                def spy(path, *a, **k):
                    opens.append(os.fspath(path))
                    return real_open(path, *a, **k)
                got = {}
                with ht.open_host_dirs(root, SID) as dirs, ctx as fu, mock.patch.object(os, "open", spy):
                    for reader, fn in (("mark", ht.host_log_mark), ("rows", ht.host_log_rows), ("reason", ht.host_exit_reason)):
                        try:
                            got[reader] = ("value", fn(dirs))
                        except ht.HostFileForeign as e:
                            got[reader] = ("foreign", e.file, e.uid, e.errno)
                        except ht.HostDirRefused as e:
                            got[reader] = ("link", e.file, getattr(e, "uid", None), str(e))
                for reader in ("mark", "rows", "reason"):
                    answer = got[reader]
                    if expect in ("absent", "not-file"):
                        self.assertEqual(answer, ("value", absent[reader]), "%s/%s/%s" % (kind, owner, reader))
                    elif expect == "ours":
                        self.assertEqual(answer, ("value", ours[reader]), "%s/%s/%s" % (kind, owner, reader))
                    elif expect == "foreign":
                        self.assertEqual(answer, ("foreign", "host.log", os.geteuid() + 1, None), "%s/%s/%s" % (kind, owner, reader))
                    else:
                        self.assertEqual(answer[:3], ("link", "host.log", None), "%s/%s/%s" % (kind, owner, reader))
                        self.assertIn("host.log in host directory %s is a symlink, not a regular file" % sdir, answer[3])
                self.assertEqual(opens, ["host.log", "host.log"] if expect == "ours" else [],
                                 "%s/%s: the two openers open a regular file of ours by name, once each, and the mark opens nothing; "
                                 "every other shape is answered by the stat of the name" % (kind, owner))
                if fu is not None:
                    self.assertEqual(fu.path_stats, 0, "a reader took a path stat: %r" % (fu.path_stat_calls,))
                self.assertEqual(stat.S_IMODE(os.lstat(sdir).st_mode), 0o700, "the read changed no mode")
                if target is not None:
                    self.assertEqual((elsewhere / "host.log").read_text(), target, "nothing behind the link was touched")


class WriteOpens(unittest.TestCase):
    """The spawn road's two write opens through the one write opener at function level
    (host_transport._open_host_file_for_write: host_stderr_open through the descent, write_spawn_spec whole; the fork PR
    that follows #814, 2026-09-21, building the small-asks item on the two O_WRONLY opens): the readers' shape question
    before any open, O_NONBLOCK on the open, the fstat of the descriptor after it, the truncation after the checks, the
    table cell by cell at both names, the FIFO drive with a bounded join, and the swap inside the open. Through #814 both
    opens went straight to _open_file_nofollow with neither the question nor the flag: a FIFO at either name blocked the
    open (and the kernel's event loop) until a reader appeared, a directory was EISDIR out of it."""
    SPEC = {"sid": SID, "name": "web", "version": "abc12345", "state_dir": "/state", "protocol": 1, "env": {"FEATURE_FLAG": "1"}}
    KIND = {"directory": "directory", "fifo": "FIFO", "socket": "socket"}

    def _root(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        return Path(d)

    def _sid(self, root):
        sh.hosts_dir(root)
        sdir = ht.host_dir(root, SID)
        sdir.mkdir(mode=0o700)
        return sdir

    def _open(self, root, name):
        """The road's open at `name`: host_stderr_open through the descent (a line written through the descriptor, its
        flags read back, then closed), or write_spawn_spec whole (its helpers, its descent, the open, the write)."""
        if name == "spawn.json":
            ht.write_spawn_spec(root, SID, self.SPEC)
            return None
        with ht.open_host_dirs(root, SID) as dirs:
            fd = ht.host_stderr_open(dirs)
            try:
                flags = fcntl.fcntl(fd, fcntl.F_GETFL)
                os.write(fd, b"a line from the launcher\n")
            finally:
                os.close(fd)
            return flags

    def _try(self, root, name):
        try:
            return ("value", self._open(root, name))
        except ht.HostFileForeign as e:
            return ("foreign", e.file, e.uid)
        except ht.HostDirRefused as e:
            return ("kind", e.file, e.kind) if e.kind else ("link", e.file, getattr(e, "uid", None))

    def _bounded(self, root, name, bound=5.0):
        """`_try` on a thread joined within `bound`: (alive after the join, the answer or None)."""
        out = []
        t = threading.Thread(target=lambda: out.append(self._try(root, name)), daemon=True)
        t.start(); t.join(bound)
        return t.is_alive(), (out[0] if out else None), t

    def test_every_shape_at_host_stderr_or_spawn_json_is_answered_from_the_table_by_the_write_side(self):
        """THE WRITE TABLE: SHAPE_TABLE's 13 (kind, owner) rows at host.stderr and at spawn.json under a 0700 <sid>/ of
        ours, 26 cells. `absent`: the file is created at 0600 and written (host.stderr's descriptor blocking: O_NONBLOCK
        cleared). `ours`: opened and written as before (host.stderr appended after the previous bytes; spawn.json
        rewritten), at 0600 whatever it was. `foreign` (the stub, descriptor-only, path-stat count 0): HostFileForeign
        naming the file and the uid, nothing opened, the bytes untouched. `link` (to a file, or dangling): the file-shape
        HostDirRefused, nothing opened, the target untouched. `not-file` (a directory, a FIFO, a socket of ours): the
        refusal naming the file and its KIND, nothing opened, the entry standing, back within the bound (the FIFO never
        blocks: it is never opened). Every cell: the only open by name is the regular file the road writes (name_opens),
        the planted object never stat'd or opened by PATH (path_ops: 0)."""
        euid = os.geteuid()
        for name in ("host.stderr", "spawn.json"):
            for kind, owner, _, expect in SHAPE_TABLE:
                with self.subTest(name=name, kind=kind, owner=owner):
                    root = self._root()
                    sdir = self._sid(root)
                    elsewhere = self._root()
                    plant_shape(sdir, name, kind, "a previous launch's bytes", elsewhere)
                    if kind == "regular":
                        os.chmod(sdir / name, 0o644)
                    target = (elsewhere / name).read_text() if kind == "symlink-to-file" else None
                    ctx = foreign_uid(sdir / name) if owner == "foreign" else contextlib.nullcontext()   # its own lstat, before the recorder
                    with path_ops(sdir / name) as ops:
                        with ctx as fu, name_opens(name) as opened:
                            alive, answer, _ = self._bounded(root, name)
                    self.assertFalse(alive, "%s/%s at %s: the open returned within the bound" % (kind, owner, name))
                    if expect in ("absent", "ours"):
                        self.assertEqual(answer[0], "value", "%s/%s at %s: %r" % (kind, owner, name, answer))
                        self.assertEqual(opened, [name], "the one open, by name")
                        st = os.lstat(sdir / name).st_mode
                        self.assertTrue(stat.S_ISREG(st)); self.assertEqual(stat.S_IMODE(st), 0o600, "0600 whatever the file was born at")
                        if name == "host.stderr":
                            self.assertEqual(answer[1] & os.O_NONBLOCK, 0, "the descriptor leaves blocking: the flag was for the open alone")
                            self.assertEqual((sdir / name).read_text(), ("a previous launch's bytes" if expect == "ours" else "") + "a line from the launcher\n", "appended")
                        else:
                            self.assertEqual(json.loads((sdir / name).read_text()), self.SPEC, "rewritten whole")
                    elif expect == "foreign":
                        self.assertEqual(answer, ("foreign", name, euid + 1), "%s/%s at %s" % (kind, owner, name))
                        self.assertEqual(opened, [], "a peer's entry is never opened")
                        self.assertEqual(fu.path_stats, 0, "the owner check took a path stat: %r" % (fu.path_stat_calls,))
                        if kind == "regular":
                            self.assertEqual((sdir / name).read_text(), "a previous launch's bytes", "the peer's bytes untouched, no truncation")
                    elif expect == "link":
                        self.assertEqual(answer, ("link", name, None), "%s/%s at %s" % (kind, owner, name))
                        self.assertEqual(opened, [], "nothing behind the link is opened")
                        self.assertTrue((sdir / name).is_symlink(), "the link stands")
                    else:
                        self.assertEqual(answer, ("kind", name, self.KIND[kind]), "%s/%s at %s: the refusal names the kind" % (kind, owner, name))
                        self.assertEqual(opened, [], "a non-regular entry of ours is never opened")
                    self.assertEqual(ops, [], "%s/%s at %s: the planted object was stat'd or opened by PATH: %r" % (kind, owner, name, ops))
                    if target is not None:
                        self.assertEqual((elsewhere / name).read_text(), target, "nothing behind the link was touched")
                    self.assertEqual(stat.S_IMODE(os.lstat(sdir).st_mode), 0o700)

    def test_a_fifo_at_host_stderr_or_spawn_json_does_not_block_the_open(self):
        """THE FIFO DRIVE (the drives verifier of #814's final body pass, on a lab directory with the road's flags:
        `BLOCKED 2.00 s, released by a reader end`), here through the road's own functions with a 2 s join: the open
        returns at once with the refusal naming the FIFO, nothing opened, the FIFO standing. RED BEFORE at #814's head,
        both arms: the thread was still alive after the join (`True is not False`), the O_WRONLY open blocked with no
        reader; the case then opened a reader end so the thread could end, and the road wrote into the FIFO."""
        for name in ("host.stderr", "spawn.json"):
            with self.subTest(file=name):
                root = self._root()
                sdir = self._sid(root)
                os.mkfifo(sdir / name)
                with name_opens(name) as opened:
                    alive, answer, t = self._bounded(root, name, bound=2.0)
                    if alive:                                             # the base's behaviour: a reader end releases the writer
                        rd = os.open(sdir / name, os.O_RDONLY | os.O_NONBLOCK)
                        self.addCleanup(os.close, rd)
                        t.join(5)
                self.assertFalse(alive, "BLOCKED 2 s at the open of a FIFO at %s, released by a reader end" % name)
                self.assertEqual(answer, ("kind", name, "FIFO"))
                self.assertEqual(opened, [], "the FIFO was never opened")
                self.assertTrue(stat.S_ISFIFO(os.lstat(sdir / name).st_mode), "the FIFO stands")

    def test_an_entry_swapped_onto_the_name_between_the_stat_and_the_open_is_decided_by_the_open_and_the_fstat(self):
        """THE SECOND CHECK on the write side: the shape question saw a regular file of ours at the name; the entry is swapped
        INSIDE the open (os.open wrapped: after _stat_name, before the real open). A FIFO of ours: the O_NONBLOCK open ends
        ENXIO (no reader), the question is asked again by name and the refusal names the FIFO, within the bound; this is
        the arm the mutation "drop O_NONBLOCK" reds, since with the flag off the open blocks until a reader appears (the
        cells that plant a FIFO before the call cannot see it: the stat refuses first). A socket of ours: ENXIO, the same
        way. A directory of ours: EISDIR, the same way, named a directory. A peer's regular file: the open returns a
        descriptor, the fstat reads the foreign owner, HostFileForeign, closed unwritten, and the peer's bytes stand,
        because O_TRUNC is applied after the checks (spawn.json) and host.stderr appends; this is the arm the mutation
        "drop the fstat compare" reds. The stub is descriptor-only, its path-stat count 0."""
        euid = os.geteuid()
        for name in ("host.stderr", "spawn.json"):
            for arm, kind, owner, expect in (("a FIFO of ours", "fifo", "ours", ("kind", name, "FIFO")),
                                             ("a socket of ours", "socket", "ours", ("kind", name, "socket")),
                                             ("a directory of ours", "directory", "ours", ("kind", name, "directory")),
                                             ("a peer's regular file", "regular", "foreign", ("foreign", name, euid + 1))):
                with self.subTest(file=name, arm=arm):
                    root = self._root()
                    sdir = self._sid(root)
                    (sdir / name).write_text("ours, at the stat")
                    plant_shape(sdir, "swap", kind, "the peer's bytes", self._root())
                    ctx = foreign_uid(sdir / "swap") if owner == "foreign" else contextlib.nullcontext()
                    real_open, swapped = os.open, []

                    def open_and_swap(path, *a, **k):
                        if os.fspath(path) == name and k.get("dir_fd") is not None and not swapped:
                            if kind == "directory":
                                os.unlink(sdir / name)                     # a directory cannot be renamed over a file
                            os.rename(sdir / "swap", sdir / name)
                            swapped.append(True)
                        return real_open(path, *a, **k)
                    with ctx as fu, mock.patch.object(os, "open", open_and_swap):
                        alive, answer, t = self._bounded(root, name, bound=2.0)
                        if alive and kind == "fifo":
                            rd = os.open(sdir / name, os.O_RDONLY | os.O_NONBLOCK)
                            self.addCleanup(os.close, rd)
                            t.join(5)
                    self.assertFalse(alive, "%s at %s: the open returned within the bound" % (arm, name))
                    self.assertEqual(swapped, [True], "the swap landed inside the open, after the stat by name")
                    self.assertEqual(answer, expect, "%s at %s" % (arm, name))
                    if fu is not None:
                        self.assertEqual(fu.path_stats, 0, "a path stat: %r" % (fu.path_stat_calls,))
                    if kind == "regular":
                        self.assertEqual((sdir / name).read_text(), "the peer's bytes", "%s: refused with its bytes intact, no truncation before the fstat" % name)

    def test_a_regular_file_of_ours_at_the_name_after_a_failed_open_is_the_opens_own_errno_and_not_a_kind_refusal(self):
        """THE RE-ASK ARM'S WORDING (the review fix-up of this PR, on the drives verifier's nit): the open answered ENXIO or
        EISDIR (a FIFO with no reader, a socket or a directory stood at the name), and the shape question asked again by
        name finds a REGULAR FILE of ours (a second swap inside the same call, the object the open met gone again). There
        is no kind to name, so the open's own OSError stands with its errno, the launch error's road, and no HostDirRefused
        is raised. RED BEFORE at the PR's first commit, both names, both errnos: the arm raised the kind refusal for any
        entry it found, wording the regular file `is a special file, not a regular file`. The open is wrapped to answer
        the errno once for the name under the descriptor; the file at the name is regular throughout, so the wrapper is
        the double swap's only trace (a real one cannot be driven to land between the open and the re-stat)."""
        import errno as _errno
        for name in ("host.stderr", "spawn.json"):
            for err in (_errno.ENXIO, _errno.EISDIR):
                with self.subTest(file=name, errno=_errno.errorcode[err]):
                    root = self._root()
                    sdir = self._sid(root)
                    (sdir / name).write_text("ours, regular throughout")
                    real_open, answered = os.open, []

                    def open_and_fail(path, *a, **k):
                        if os.fspath(path) == name and k.get("dir_fd") is not None and not answered:
                            answered.append(err)
                            raise OSError(err, os.strerror(err), name)
                        return real_open(path, *a, **k)
                    with mock.patch.object(os, "open", open_and_fail):
                        with self.assertRaises(OSError) as cm:
                            self._open(root, name)
                    self.assertEqual(answered, [err], "the open answered the errno once, for the name under the descriptor")
                    self.assertNotIsInstance(cm.exception, ht.HostDirRefused, "a regular file of ours refused by kind: %s" % cm.exception)
                    self.assertEqual(cm.exception.errno, err, "the open's own errno stands")
                    self.assertEqual((sdir / name).read_text(), "ours, regular throughout", "nothing written, nothing truncated")

    def test_the_opener_truncates_only_after_the_checks_and_sets_the_mode_on_the_descriptor(self):
        """The two flags the opener rewrites: a caller's O_TRUNC is applied after the fstat (os.ftruncate on the verified
        descriptor: spawn.json of ours with old bytes is rewritten whole), and O_NONBLOCK, on for the open, is off on the
        descriptor handed back; the mode is 0600 on the descriptor whatever the file was born at (a 0644 host.stderr a
        previous launch left reads 0600 after). The raising-fchmod close is SpawnSpec's pin."""
        root = self._root()
        sdir = self._sid(root)
        (sdir / "spawn.json").write_text("x" * 4000)
        os.chmod(sdir / "spawn.json", 0o644)
        ht.write_spawn_spec(root, SID, self.SPEC)
        self.assertEqual(json.loads((sdir / "spawn.json").read_text()), self.SPEC, "rewritten whole: the old 4000 bytes truncated after the checks")
        self.assertEqual(stat.S_IMODE(os.lstat(sdir / "spawn.json").st_mode), 0o600)
        (sdir / "host.stderr").write_text("old")
        os.chmod(sdir / "host.stderr", 0o644)
        with ht.open_host_dirs(root, SID) as dirs:
            fd = ht.host_stderr_open(dirs)
            try:
                self.assertEqual(fcntl.fcntl(fd, fcntl.F_GETFL) & os.O_NONBLOCK, 0, "blocking on the way out")
                self.assertEqual(stat.S_IMODE(os.fstat(fd).st_mode), 0o600)
                os.write(fd, b"+new")
            finally:
                os.close(fd)
        self.assertEqual((sdir / "host.stderr").read_text(), "old+new", "appended, never truncated")


class Pins(unittest.TestCase):
    @unittest.skipUnless(SDK, "the SDK is not importable here")
    def test_host_transport_implements_the_sdks_six_transport_methods(self):
        from claude_agent_sdk._internal.transport import Transport
        abstract = set(getattr(Transport, "__abstractmethods__", set()))
        self.assertEqual(abstract, {"connect", "write", "read_messages", "close", "is_ready", "end_input"})
        self.assertTrue(issubclass(ht.HostTransport, Transport))
        self.assertEqual(set(getattr(ht.HostTransport, "__abstractmethods__", set())), set())

    def test_backend_wiring(self):
        src = open(os.path.join(BIN, "romp_sdk_backend.py")).read()
        self.assertIn("async with ClaudeSDKClient(options=opts, transport=transport) as client:", src)
        self.assertIn("transport = await self.backend._host_transport_for(self, opts,", src)
        self.assertIn("if self.client and not self.detached:", src, "shutdown never interrupts a detached session")
        self.assertIn("if self.backend.session_hosts_on() or self.backend._host_lease_applies(self):", src, "a live host lease is attached whatever the setting")
        self.assertIn("if not sess.ended and not sess.detached:", src, "a latched detach is not a crash")
        self.assertIn("s._host.detach_mode = True", src, "the drain detaches")
        self.assertIn('if s.inflight and getattr(s, "_host", None) is None and not getattr(s, "_host_intent", False)]', src, "an attached (or attaching) session is never a cut")
        self.assertIn("s._host.end_grace = _ht().sh.END_GRACE_KILL_S", src, "kill gets the short bound")
        self.assertIn('== "attach":', src, "boot attach-first")
        self.assertIn('append_session_event(self.state_dir, "host.attached"', src)
        self.assertIn("m.timeout = _ht().sh.HOOK_TIMEOUT_S", src, "hooks carry the bound under a host")
        self.assertIn("self._host_stand_down(e)\n                    break", src, "past the attach bound the session stands down and LEAVES the loop, never the crash heal")
        self.assertIn("        if user:\n            self._lift_attach_stand_down(sid)", src, "the USER's send is the word that lifts a stand-down; an automatic one is not")
        self.assertIn("                    connected = True\n                    self._host_attach_retries = 0", src,
                      "the retry counter resets inside the connected block: consecutive incomplete attaches only (the commit-10 review's first item)")
        ksrc = open(os.path.join(ROOT, "kernel", "kernel.py")).read()
        self.assertIn("if _send_with_id(be, sid, text, qid, user=user, paths=paths, user_todo=user_todo) is False:", ksrc, "the park-or-send route hands on who speaks and what rode along; the caller that knows classifies (T315; the attachment list, T373; the answer's todo id, the 2026-09-15 pull-in)")
        self.assertIn('user="<!-- romp-tag: " not in text', ksrc, "POST /send: an untagged send is the user's, a tagged one a machine's")   # the one delivery door since T370 (_deliver_text; the route reaches it behind this fork's by-name doors)
        self.assertIn('return "user" in inspect.signature(fn).parameters', ksrc, "read from the signature, so a stand-in send without the keyword is called as before")

    def test_construction_reads_no_setting_and_the_file_is_the_toggle_read_on_each_ask(self):
        d = tempfile.mkdtemp(); be = sb.SdkBackend(d, "/bin/true", lambda *a, **k: None)
        self.assertTrue(be.session_hosts_on(), "on by default (T348): a bare state dir")
        Path(d, "session-hosts").write_text("off")
        self.assertFalse(be.session_hosts_on(), "the file is the toggle, read on each ask, no restart")

    def test_host_log_rows_are_filed_once_per_line(self):
        d = tempfile.mkdtemp(); logs = []
        be = sb.SdkBackend(d, "/bin/true", lambda *a, **k: None, log=logs.append)
        sess = types.SimpleNamespace(sid=SID, name="web", _host=None)
        hd = ht.host_dir(d, SID); hd.mkdir(parents=True)
        os.chmod(hd.parent, 0o700); os.chmod(hd, 0o700)   # the shape the spawn road makes; at the umask the read files a loose row per component
        (hd / "host.log").write_text(json.dumps({"t": 1, "kind": "attached"}) + "\n"
                                     + json.dumps({"t": 2, "kind": "hook-self-answered", "event": "Stop", "callbackId": "hook_0", "parkedS": 480}) + "\n"
                                     + json.dumps({"t": 3, "kind": "end-forced", "cliPid": 5}) + "\n")
        be._file_host_log_rows(sess)
        rows = [json.loads(l) for l in (Path(d) / sb.SESSION_EVENTS_FILE).read_text().splitlines()]
        self.assertEqual([r["kind"] for r in rows], ["host.hook-self-answered", "host.end-forced"])
        self.assertEqual((rows[0]["sid"], rows[0]["event"], rows[0]["t"]), (SID, "Stop", 2))
        be._file_host_log_rows(sess)
        rows2 = [json.loads(l) for l in (Path(d) / sb.SESSION_EVENTS_FILE).read_text().splitlines()]
        self.assertEqual(len(rows2), 2, "no line is filed twice")
        self.assertEqual(sum(1 for l in logs if "hook" in l and "itself" in l), 1)


@unittest.skipUnless(SDK, "the SDK is not importable here (the end-to-end run needs ClaudeSDKClient)")
class EndToEnd(unittest.TestCase):
    """A backend with hosts ON drives the fake CLI through a real host: a turn started under one kernel finishes
    under the next after a drain that detaches instead of cutting, and a kill ends the host's CLI gracefully.
    Hermetic: a private state root, the fake CLI as claude_bin, no scopes, every process ended by the test."""
    FAKE = os.path.join(HERE, "fixtures", "fake_claude.py")

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.addCleanup(self._sweep)
        Path(self.d, "session-hosts").write_text("on")
        Path(self.d, "session-host-grace").write_text("600")
        # the fake CLI's transcript stand-in: it inherits the backend's environment through the host, and the
        # test reads the result text from it (an interrupted turn would say so)
        self.tdir = os.path.join(self.d, "transcripts")
        self._env_before = os.environ.get("FAKE_CLI_TRANSCRIPT_DIR")
        os.environ["FAKE_CLI_TRANSCRIPT_DIR"] = self.tdir
        self.addCleanup(self._restore_env)
        self.sid = str(__import__("uuid").uuid4())
        for sub in ("sdk", "states", "names"):
            os.makedirs(os.path.join(self.d, sub), exist_ok=True)
        cwd = os.path.join(self.d, "proj"); os.makedirs(cwd)
        sb.write_reg(Path(self.d), self.sid, {"sid": self.sid, "name": "web", "cwd": cwd, "alive": True, "mode": "bypassPermissions",
                                              "effort": "high", "lastSid": self.sid})
        self.logs = []

    def _restore_env(self):
        if self._env_before is None:
            os.environ.pop("FAKE_CLI_TRANSCRIPT_DIR", None)
        else:
            os.environ["FAKE_CLI_TRANSCRIPT_DIR"] = self._env_before

    def _sweep(self):
        for be in getattr(self, "_bes", []):
            try:
                be.drain(timeout=3)
            except Exception:
                pass
        lease = sb.read_lease(self.d, self.sid)
        if lease:
            for key in ("holder", None):
                pid = (lease.get(key) or {}).get("pid") if key else lease.get("pid")
                try:
                    os.kill(int(pid), 9)
                except Exception:
                    pass

    def _backend(self):
        be = sb.SdkBackend(self.d, self.FAKE, lambda *a, **k: None, log=self.logs.append, code_version="t315")
        self._bes = getattr(self, "_bes", []) + [be]
        return be

    def _journal(self):
        """The host's journal through the read descent (host_transport.read_journal_dir over the HostDirs
        open_host_dirs_if_present returns; the fork PR that follows #814), [] before the host made its directory."""
        dirs = ht.open_host_dirs_if_present(self.d, self.sid)
        if dirs is None:
            return []
        with dirs:
            return list(ht.read_journal_dir(dirs))

    def _wait(self, pred, timeout=20, what=""):
        deadline = time.time() + timeout
        while time.time() < deadline:   # loop-ok: a bounded wait on an observable event
            if pred():
                return True
            time.sleep(0.1)
        self.fail("timed out waiting for %s\nlog tail: %s" % (what, "\n".join(self.logs[-15:])))

    def test_a_turn_survives_a_drain_and_finishes_under_the_next_backend(self):
        be = self._backend()
        self.assertTrue(be.send(self.sid, "start long sleep=6"))
        self._wait(lambda: (sb.read_lease(self.d, self.sid) or {}).get("holder", {}).get("kind") == "host", what="a host-held lease")
        lease = sb.read_lease(self.d, self.sid)
        self._wait(lambda: len(self._journal()) >= 2, what="the init and assistant records in the journal")
        self._wait(lambda: isinstance((sb.read_reg(Path(self.d), self.sid) or {}).get("hostAck"), dict), what="hostAck in the registry")
        res = be.drain(timeout=5)
        self.assertEqual(res["cutTurns"], [], "an attached session is detached, never cut")
        self.assertEqual(res["reaped"], 0)
        time.sleep(0.5)
        lease2 = sb.read_lease(self.d, self.sid)
        self.assertIsNotNone(lease2, "the host keeps its lease across the kernel's drain")
        self.assertEqual((lease2["pid"], lease2["holder"]["pid"]), (lease["pid"], lease["holder"]["pid"]), "same CLI, same host")
        self.assertEqual(sb.lease_state(lease2, time.time()), "valid")
        # the next kernel: boot attach-first
        import subprocess as _sp
        ps_lines = _sp.run(sb.PS_ARGV, capture_output=True, text=True, timeout=10).stdout.splitlines()
        census = sb.lease_census(ps_lines, [self.sid], os.getpid(), sb.list_leases(self.d), version="t315")
        mine = [l for l in ps_lines if self.sid in l]
        self.assertEqual(census["problems"], [], "the census before the second boot: owned=%r orphans=%r dead=%r; ps lines: %r; lease=%r"
                         % (census["owned"], census["orphans"], census["dead_leases"], mine, sb.read_lease(self.d, self.sid)))
        # the setting is turned OFF while the host lives: a live host lease is attached regardless (the setting
        # governs new spawns), never a second CLI beside the host's (the commit 2-3 review's third finding)
        Path(self.d, "session-hosts").write_text("off")
        be2 = self._backend()
        be2._boot_reconcile([sb.read_reg(Path(self.d), self.sid)])
        self._wait(lambda: sum(1 for l in self._events() if l.get("kind") == "host.attached") >= 2, what="the second host.attached row")
        att = [l for l in self._events() if l.get("kind") == "host.attached"]
        self.assertEqual([a["boot"] for a in att], [False, True], "the first backend attached at spawn, the second at boot; log: %s"
                         % "\n".join(l for l in self.logs if "boot reconcile" in l or "host (" in l)[-2500:])
        self.assertGreater(att[1]["replayFrom"], 0, "the boot attach replayed from the acknowledged offset, not from zero")
        self._wait(lambda: sb.last_state_value(Path(self.d), self.sid) == "waiting", timeout=30, what="the turn's result under the second backend")
        self.assertEqual(sb.read_lease(self.d, self.sid)["pid"], lease["pid"], "one CLI process the whole way: one writer")
        transcripts = list(Path(self.tdir).glob("*.jsonl"))
        self.assertEqual(len(transcripts), 1, "one transcript stand-in")
        results = [json.loads(l)["result"] for l in transcripts[0].read_text().splitlines() if '"type":"result"' in l]
        self.assertEqual(results, ["done"], "the turn's normal completion: the drain neither cut nor interrupted it (the first finding)")
        self.assertFalse(any("restarted" in t for t in ((sb.read_reg(Path(self.d), self.sid) or {}).get("queue") or [])),
                         "no continuation notice for a turn that was never cut")
        # kill: end with the short bound; the host ends the CLI and leaves, the lease goes
        be2.kill(self.sid)
        self._wait(lambda: sb.read_lease(self.d, self.sid) is None, timeout=20, what="the lease removed after kill")
        kinds = [l["kind"] for l in self._events()]
        self.assertNotIn("host.died", kinds)

    def _events(self):
        p = Path(self.d) / sb.SESSION_EVENTS_FILE
        return [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []


@unittest.skipUnless(SDK, "the SDK is not importable here")
class AttachStandDown(unittest.TestCase):
    """The real connect loop against a fake host whose initialize never answers (the commit-10 review): exactly
    four attaches, one host.attach-failed row, one waiting row, then NO further attach from the timer sweep, a
    boot or a plain connect until a send arrives; and the retry counter counts CONSECUTIVE incomplete attaches
    only (a completed connect resets it). The SDK's initialize timeout is forced to one second through the Query
    seam; the host lease names this test process as both CLI and host and is beaten by a thread."""

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.addCleanup(self._sweep)
        Path(self.d, "session-hosts").write_text("on")
        for sub in ("sdk", "states", "names", "hosts"):
            os.makedirs(os.path.join(self.d, sub), exist_ok=True)
        self.sid = str(__import__("uuid").uuid4())
        cwd = os.path.join(self.d, "proj"); os.makedirs(cwd)
        sb.write_reg(Path(self.d), self.sid, {"sid": self.sid, "name": "web", "cwd": cwd, "alive": True, "mode": "bypassPermissions",
                                              "effort": "high", "lastSid": self.sid})
        me, start = os.getpid(), sb.proc_start(os.getpid())
        self.holder = "%s:%s" % (me, start)
        self._beating = True
        def beat():
            while self._beating:      # loop-ok: the lease heartbeat, ended by the test's cleanup
                sb.write_lease(self.d, {"sid": self.sid, "fsid": self.sid, "pid": me, "start": start,
                                        "holder": {"pid": me, "start": start, "kind": "host"}, "version": "t315", "t": time.time()})
                time.sleep(1.0)
        import threading
        self.beater = threading.Thread(target=beat, daemon=True); self.beater.start()
        self.logs = []
        self.be = sb.SdkBackend(self.d, "/bin/true", lambda *a, **k: None, log=self.logs.append, code_version="t315")
        import claude_agent_sdk._internal.query as q
        orig = q.Query.__init__
        def fast_init(self_, *a, **kw):
            kw["initialize_timeout"] = 1.0
            return orig(self_, *a, **kw)
        patcher = mock.patch.object(q.Query, "__init__", fast_init); patcher.start(); self.addCleanup(patcher.stop)
        self.loop = asyncio.new_event_loop()
        self.host = None

    def _serve(self, **kw):
        sock = str(ht.host_sock(self.d, self.sid))
        self.host = FakeHost(sock, [], **kw)
        import threading
        started = threading.Event()
        def run_loop():
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self.host.start()); started.set()
            self.loop.run_forever()
        threading.Thread(target=run_loop, daemon=True).start()
        started.wait(5)

    def _sweep(self):
        self._beating = False
        try:
            self.be.drain(timeout=3)
        except Exception:
            pass
        if self.host:
            self.loop.call_soon_threadsafe(self.host.close)
        self.loop.call_soon_threadsafe(self.loop.stop)
        sb.remove_lease(self.d, self.sid)

    def _wait(self, pred, timeout=30, what=""):
        deadline = time.time() + timeout
        while time.time() < deadline:   # loop-ok: a bounded wait on an observable event
            if pred():
                return True
            time.sleep(0.1)
        self.fail("timed out waiting for %s\nlog tail: %s" % (what, "\n".join(self.logs[-15:])))

    def _kinds(self):
        p = Path(self.d) / sb.SESSION_EVENTS_FILE
        return [json.loads(l)["kind"] for l in p.read_text().splitlines()] if p.exists() else []

    def _states(self):
        p = Path(self.d) / "states" / (self.sid + ".jsonl")
        return [json.loads(l).get("state") for l in p.read_text().splitlines() if l.strip()] if p.exists() else []

    def test_four_unanswered_attaches_stand_the_session_down_once_until_a_send(self):
        # echo_turns: the backend feeds one text at a time and waits for the CLI to take it (SdkSession._untaken), so
        # the three texts asserted below reach this host only if it answers each with a turn (upstream's fake echoes
        # none and upstream has no hold)
        self._serve(answer_init=lambda n: False, echo_turns=True)
        self.assertTrue(self.be.send(self.sid, "hello"))
        self._wait(lambda: "host.attach-failed" in self._kinds(), timeout=40, what="the stand-down row")
        self._wait(lambda: not (self.be.sessions.get(self.sid) and self.be.sessions[self.sid].thread.is_alive()), what="the thread's exit")
        time.sleep(3.0)                       # two more retry periods: nothing may attach again on its own
        self.assertEqual(self.host.attaches, 4, "exactly four attaches, then the loop is left")
        self.assertEqual(self._kinds().count("host.attach-failed"), 1)
        self.assertEqual(self._states().count("waiting"), 1, "one waiting row from the stand-down; states: %r" % self._states())
        self.assertNotIn("crash.heal", self._kinds()); self.assertNotIn("crash.loop", self._kinds())
        reg = sb.read_reg(Path(self.d), self.sid) or {}
        self.assertEqual((reg.get("hostAttachFailed") or {}).get("host"), self.holder, "the marker names the lease holder that would not answer")
        self.assertNotIn(sb.CRASH_RESUME_NUDGE, reg.get("queue") or [], "no crash-resume nudge for a CLI that never died")
        # the automatic doors stay shut while the marker names the current lease holder
        self.assertIsNone(self.be._ensure(self.sid), "a plain ensure (the sweep, a heal) stands down")
        self.assertFalse(self.be.connect(self.sid))
        self.be._boot_reconcile([sb.read_reg(Path(self.d), self.sid)])
        time.sleep(1.5)
        self.assertEqual(self.host.attaches, 4, "no attach from the sweep, the connect or the boot")
        # romp's own automatic message (the default send) is QUEUED behind the stand-down: accepted, no attach
        self.assertTrue(self.be.send(self.sid, "<!-- romp-injected --><!-- romp-auto --> a nudge"))
        time.sleep(1.5)
        self.assertEqual(self.host.attaches, 4, "an automatic send never lifts the stand-down")
        reg = sb.read_reg(Path(self.d), self.sid) or {}
        self.assertIn("hostAttachFailed", reg)
        self.assertIn("<!-- romp-injected --><!-- romp-auto --> a nudge", reg.get("queue") or [], "queued in the persisted mirror")
        # the USER's message is new information: the marker clears, the attach is tried again, and both ride it in order
        self.host.answer_init = lambda n: n >= 5
        self.assertTrue(self.be.send(self.sid, "again", user=True))
        self._wait(lambda: self.host.attaches >= 5, what="the fifth attach, for the user's send")
        self.assertNotIn("hostAttachFailed", sb.read_reg(Path(self.d), self.sid) or {})
        def user_texts():
            out = []
            for f in list(self.host.got):
                if f.get("t") == "in":
                    try:
                        obj = json.loads(f["data"])
                    except ValueError:
                        continue
                    if obj.get("type") == "user":
                        c = obj["message"]["content"]
                        out.append(c if isinstance(c, str) else c[0].get("text"))
            return out
        self._wait(lambda: len(user_texts()) >= 3, what="every message fed to the CLI through the host")
        self.assertEqual(user_texts()[:3], ["hello", "<!-- romp-injected --><!-- romp-auto --> a nudge", "again"],
                         "original send order: the first message the stand-down held, the queued automatic one, then the user's new one")

    def test_the_retry_counter_counts_consecutive_incomplete_attaches_only(self):
        # attaches 1, 3, 5, 7 never complete; 2, 4, 6 do (and are reconnected on request): the fourth timeout in the
        # session's life is the FIRST of a new run, a retry, never a stand-down
        self._serve(answer_init=lambda n: n % 2 == 0)
        self.assertTrue(self.be.connect(self.sid), "an eager connect, no turn: request_reconnect acts at once only on an idle session")
        for target in (2, 4, 6):
            self._wait(lambda t=target: self.host.attaches >= t and self.be.sessions.get(self.sid) is not None
                       and self.be.sessions[self.sid].client is not None, what="a completed connect on attach %d" % target)
            self.be.sessions[self.sid].request_reconnect()
        self._wait(lambda: self.host.attaches >= 8, timeout=40, what="the eighth attach: the seventh's timeout was a retry")
        self.assertNotIn("host.attach-failed", self._kinds(), "three recovered timeouts and one more never reach the bound")
        self.assertNotIn("hostAttachFailed", sb.read_reg(Path(self.d), self.sid) or {})


if __name__ == "__main__":
    unittest.main()
