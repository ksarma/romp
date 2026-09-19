#!/usr/bin/env python3
"""Per-session env vars, spawn-time slice (the user 2026-08-17): two SDK sessions in the SAME
directory can run with different environments. Before this, env came only from directory-scoped
.claude/settings*.json — every session in the repo got it, and it outlived the session.

The mechanics under test:
  * `env_request_error` is the ONE validator both doors share (the /new handler mirrors it): a
    payload is a dict of NAME→string-value pairs, names matching [A-Za-z_][A-Za-z0-9_]*; anything
    else is named loudly, never skipped. A credential-shaped NAME of any spelling is refused by
    name, the value never quoted, and the advice says where the value belongs by the half of the
    rule it matched (2026-09-18; review round 2 of the env-pick door, 2026-09-19).
  * spawn() persists the dict in the session's reg (`env`) — the same home model/effort live in —
    and refuses a bad payload outright rather than writing a poisoned reg.
  * flag_settings_path folds a non-empty env into the per-sid settings payload beside ultracode /
    fastMode, and the return-""-when-no-keys contract stands (with no key riding nothing is
    touched, as before the door). It refuses a sid that is not a bare file name and a path that
    is a symbolic link (review round 2 of the env-pick door, 2026-09-19), and writes on write_reg's
    temp-and-rename pattern, to a fresh inode and never through the existing one (review round 3,
    2026-09-19). Every row it logs has a ring text whose length is a function of its format.
  * _options threads the session's env into that file at EVERY connect — the file is rewritten on
    each use, so reconnects re-assert the reg's env by construction (pinned by tampering the file
    between two _options calls). Its stored-offender row states a fact and promises no remedy
    (review round 3: the redaction road left this change), with a short form for the error centre
    that is bounded by construction (one variable named, the rest counted through a bounded count,
    the session name and the named variable cut to a budget each), pinned as a property through
    the real ring for one, two and twenty variables and with the worst case computed from the
    format, the repeat suffix taken at a four-digit count.
  * set_env mirrors set_effort's shape (persist + reconnect to apply; env is connect-time), minus
    the badge/chip machinery that belongs to the not-yet-built UI slice; an UNCHANGED re-assert
    (the `romp new --env` re-brief on a standing session, or the fresh-spawn echo) skips the
    reconnect, since the asked-for env is already in force or already queued. A refused pick is a
    problem row whose ring text is bounded by construction, the session name cut to a budget and
    the refused names one named and the rest counted.
  * fork() inherits the parent's env like model/auth (it is that conversation, continued
    elsewhere), LESS any credential-shaped name (review round 1 of the env-pick door, 2026-09-18).

Values are assembled at run time, never a token-shaped literal (gitleaks reads this repo too); the
door tests deliberately plant credential-shaped NAMES, since refusing them is what they pin.
"""
import errno
import glob
import json
import os
import re
import tempfile
import unittest
import uuid
from pathlib import Path
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
sb = load_source("romp_sdk_backend_env", os.path.join(BIN, "romp_sdk_backend.py"))

PARENT = "11111111-2222-3333-4444-555555555555"
CHILD = "66666666-7777-8888-9999-aaaaaaaaaaaa"
ENV = {"FEATURE_FLAG": "1", "UI_THEME": "dark"}
PLAIN = {"NOTES_ENDPOINT": "http://notes.test"}   # a plain name beside a credential-shaped one in the door tests


def _secret_value(tag):
    """A synthetic credential-shaped VALUE built at run time from short parts: gitleaks reads this repo, so no
    token-shaped literal ever sits in a test (the spawn.json fix's tests build theirs the same way)."""
    return "synthetic-" + tag + "-" + uuid.uuid4().hex


class _OsProxy:
    """The module's `os` with one function interposed and everything else forwarded: `replace` runs a hook in place
    of os.replace on the flag-settings writer's rename (a forced failure). Rebound as sb.os for a test's duration,
    since the module's functions read `os` from their globals; restored by addCleanup."""

    def __init__(self, real, replace=None):
        self._real, self._replace = real, replace

    def __getattr__(self, name):
        return getattr(self._real, name)

    def replace(self, src, dst):
        if self._replace is not None and sb.FLAG_SETTINGS_DIR in str(dst):   # the flag-settings writer's rename only:
            return self._replace(self._real, src, dst)                        #  write_reg's goes through this os too
        return self._real.replace(src, dst)


def _interpose(test, **kw):
    real = sb.os
    test.addCleanup(setattr, sb, "os", real)
    sb.os = _OsProxy(real, **kw)
    return real


def _enospc(real, src, dst):
    """A rename that fails the way a full disk fails it."""
    raise OSError(errno.ENOSPC, "No space left on device")


def _temps(d):
    return sorted(os.path.basename(t) for t in glob.glob(os.path.join(str(d), sb.FLAG_SETTINGS_DIR, "*.tmp")))


class _Backend(unittest.TestCase):
    """Base: a backend on a temp state dir, no real CLI, no real key claim."""

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self._fetch_before = sb._fetch_key_fast_org
        sb._fetch_key_fast_org = lambda key: None  # the fast-org probe is a real HTTPS GET — never from a test
        self.be = sb.SdkBackend(self.d, "/bin/true", lambda *a, **k: None)

    def tearDown(self):
        sb._fetch_key_fast_org = self._fetch_before

    def _reg(self, sid):
        return sb.read_reg(self.be.state_dir, sid)

    def _sess(self, sid):
        return sb.SdkSession(self.be, sb.read_reg(self.be.state_dir, sid))


class EnvRequestError(unittest.TestCase):
    """The shared validator: loud and specific, never a silent skip."""

    def test_valid_payloads_pass(self):
        self.assertEqual(sb.env_request_error({"FEATURE_FLAG": "1"}), "")
        self.assertEqual(sb.env_request_error({"_UNDER": "x", "A9": ""}), "",
                         "an empty VALUE is meaningful — explicitly setting empty")
        self.assertEqual(sb.env_request_error({}), "", "an empty dict is a valid (vacuous) payload")

    def test_a_non_dict_is_named(self):
        for bad in ("FEATURE_FLAG=1", ["FEATURE_FLAG"], 7, None):
            err = sb.env_request_error(bad)
            self.assertIn("env", err)
            self.assertTrue(err, "a non-object payload must be refused, not coerced")

    def test_a_bad_name_is_named(self):
        for bad in ("9BAD", "", "BAD-NAME", "BAD NAME", "über"):
            err = sb.env_request_error({bad: "1"})
            self.assertIn("[A-Za-z_][A-Za-z0-9_]*", err,
                          "the error must teach the alphabet, not just refuse: %r" % bad)

    def test_a_non_string_value_is_named(self):
        for bad in (1, None, True, {"nested": "no"}):
            err = sb.env_request_error({"FEATURE_FLAG": bad})
            self.assertIn("FEATURE_FLAG", err,
                          "the offending NAME must be in the error (fail loudly): %r" % (bad,))

    def test_a_nul_byte_in_a_value_is_named(self):
        # an execve envp entry is a NUL-terminated C string, so a NUL value is unfulfillable by
        # definition — accepted, it bakes an env the CLI can only truncate or throw on into the reg
        err = sb.env_request_error({"FEATURE_FLAG": "1\x00x"})
        self.assertIn("FEATURE_FLAG", err, "the offending NAME must be in the error")
        self.assertIn("NUL", err, "the error names the actual problem")

    def test_other_control_bytes_stay_legitimate(self):
        self.assertEqual(sb.env_request_error({"FEATURE_FLAG": "line1\nline2\ttabbed"}), "",
                         "NUL only — newlines and tabs are legitimate env content")

    def test_the_identity_names_are_refused(self):
        # options.env owns ROMP_SID / ROMP_SESSION_NAME (the identity overlay below): a user var of
        # either name would silently shadow or be shadowed by the identity, breaking `romp end self`
        # with nothing pointing at the cause — refused at the door instead, like every bad payload
        for name in ("ROMP_SID", "ROMP_SESSION_NAME"):
            err = sb.env_request_error({name: "x"})
            self.assertIn(name, err, "the reserved NAME must be in the error")
            self.assertIn("romp sets", err, "the error teaches WHO owns the name, not just 'no'")
        self.assertTrue(sb.env_request_error({"FEATURE_FLAG": "1", "ROMP_SID": "x"}),
                        "a reserved name refuses the WHOLE payload, never a silent skip")


class FlagSettingsEnv(unittest.TestCase):
    """flag_settings_path folds env in beside ultracode/fastMode; the ""-when-empty contract stands."""

    def setUp(self):
        self.d = tempfile.mkdtemp()

    def _read(self, p):
        return json.loads(Path(p).read_text())

    def test_env_alone_writes_the_file(self):
        p = sb.flag_settings_path(self.d, PARENT, env=ENV)
        self.assertTrue(p)
        self.assertEqual(self._read(p), {"env": ENV})

    def test_env_rides_beside_the_boolean_keys(self):
        p = sb.flag_settings_path(self.d, PARENT, ultracode=True, fast=True, env=ENV)
        got = self._read(p)
        self.assertEqual(got["env"], ENV)
        self.assertTrue(got["ultracode"] and got["fastMode"],
                        "env must merge INTO the payload, not replace the keys already riding it")

    def test_no_keys_still_returns_empty(self):
        self.assertEqual(sb.flag_settings_path(self.d, PARENT), "")
        self.assertEqual(sb.flag_settings_path(self.d, PARENT, env=None), "")
        self.assertEqual(sb.flag_settings_path(self.d, PARENT, env={}), "",
                         "an empty env adds no key — the no-keys contract is the common case")

    def test_an_unwritable_dir_degrades_loudly(self):
        # a plain FILE where the flag-settings dir goes forces the OSError (os.makedirs raises)
        Path(self.d, sb.FLAG_SETTINGS_DIR).write_text("not a directory")
        logged = []
        p = sb.flag_settings_path(self.d, PARENT, env=ENV,
                                  log=lambda msg, problem=False, **kw: logged.append((msg, problem)))
        self.assertEqual(p, "", "degrade to launch — a session without its env still beats none")
        self.assertEqual(len(logged), 1)
        msg, problem = logged[0]
        self.assertTrue(problem, "the drop is a problem row, not a quiet info line")
        self.assertIn("env", msg, "the log names the dropped keys")
        self.assertIn(PARENT, msg, "the log names whose launch went without them")

    def test_the_oserror_path_stays_quiet_without_a_logger(self):
        Path(self.d, sb.FLAG_SETTINGS_DIR).write_text("not a directory")
        self.assertEqual(sb.flag_settings_path(self.d, PARENT, env=ENV), "",
                         "log=None (direct callers) must neither raise nor change the '' contract")

    def test_no_keys_asked_means_no_log_even_on_a_bad_dir(self):
        Path(self.d, sb.FLAG_SETTINGS_DIR).write_text("not a directory")
        logged = []
        self.assertEqual(
            sb.flag_settings_path(self.d, PARENT, log=lambda *a, **k: logged.append(a)), "")
        self.assertEqual(logged, [], "nothing requested, nothing dropped — nothing to report")



class FlagSettingsWriter(unittest.TestCase):
    """The one writer of the per-sid flag-settings file (flag_settings_path) since review round 3 of the env-pick
    door (2026-09-19) sent the env pick's own edit of the file away with the redaction road. Two refusals stand
    ahead of its write (review round 2): a sid that is not a bare file name (rules-2 / kernel-4: the path is built
    from the sid, and a crafted one would carry the env block outside the state root) and a path that is a symbolic
    link (extra5-2: the write road put the env block into the link's target). The write itself is write_reg's
    temp-and-rename (round 3, correctness-4 and kernel-3: an in-place O_TRUNC write refreshed a hard link's other
    name with every connect's env and followed a symlink planted between the check and the open), and every row the
    writer logs has a ring text whose length is a function of its format (round 3, correctness-3 and kernel-2: the
    link row ran to 383 to 453 characters over a real state root, past both caps, and the sid rows were unbounded)."""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.d = os.path.join(self.root, "state")
        os.makedirs(os.path.join(self.d, sb.FLAG_SETTINGS_DIR))

    def _log(self):
        logged = []
        return logged, (lambda msg, problem=False, **kw: logged.append((msg, problem, kw)))

    def test_a_traversal_sid_is_refused_before_anything_is_touched(self):
        victim = Path(self.root, "victim.json")
        victim.write_text(json.dumps({"env": {"KEEP": "me"}}) + "\n")
        st = victim.stat()
        sid = "../../victim"
        self.assertEqual(os.path.normpath(os.path.join(self.d, sb.FLAG_SETTINGS_DIR, sid + ".json")), str(victim),
                         "the sid would resolve to the victim outside the directory")
        logged, log = self._log()
        self.assertEqual(sb.flag_settings_path(self.d, sid, env=ENV, log=log), "", "the write road")
        self.assertEqual(json.loads(victim.read_text()), {"env": {"KEEP": "me"}}, "the victim's bytes are untouched")
        self.assertEqual(victim.stat().st_mtime_ns, st.st_mtime_ns, "and it was not rewritten in place either")
        self.assertEqual(len(logged), 1, logged)
        m, problem, kw = logged[0]
        self.assertTrue(problem)
        self.assertIn("not a bare file name", m, "the refusal names the specific reason")
        self.assertIn(repr(sid), m)
        self.assertIn("launching WITHOUT env", m, "the write road says what the launch goes without")
        self.assertEqual(kw["ring_text"], sb.FLAG_SID_RING % (sb.FLAG_SID_REASONS[2], repr(sid), "env"),
                         "the ring text: the reason, the sid's repr within its budget, the keys")
        self.assertLessEqual(len(kw["ring_text"]), sb.ERROR_CENTER_TEXT_CAP)
        self.assertEqual(sb.flag_settings_path(self.d, sid, log=log), "", "with no key riding nothing is written and nothing said")
        self.assertEqual(len(logged), 1)
        for bad in ("..", ".", "", None, "a\0b", "x/y", 7):
            self.assertEqual(sb.flag_settings_path(self.d, bad, env=ENV), "", repr(bad))
        self.assertEqual(os.listdir(os.path.join(self.d, sb.FLAG_SETTINGS_DIR)), [], "nothing was written under the directory either")
        self.assertEqual(sb._flag_settings_sid_error(PARENT), "", "a kernel-minted uuid passes")
        self.assertTrue(sb.flag_settings_path(self.d, PARENT, env=ENV), "and writes as before")

    def test_a_symbolic_link_is_refused_and_nothing_is_written_through_it(self):
        import stat
        target = Path(self.root, "outside.json")
        target.write_text(json.dumps({"env": {"OUTSIDE": "kept"}}) + "\n")
        os.chmod(target, 0o644)
        p = Path(self.d, sb.FLAG_SETTINGS_DIR, PARENT + ".json")
        os.symlink(str(target), str(p))
        logged, log = self._log()
        self.assertEqual(sb.flag_settings_path(self.d, PARENT, env=ENV, fast=True, log=log), "", "the write road")
        self.assertTrue(os.path.islink(p), "the link is left in place")
        self.assertEqual(json.loads(target.read_text()), {"env": {"OUTSIDE": "kept"}}, "the target's bytes are untouched")
        self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o644, "and its mode (the write road used to chmod through the link)")
        self.assertEqual(len(logged), 1, logged)
        m, problem, kw = logged[0]
        self.assertTrue(problem)
        self.assertIn(str(p), m, "the kernel log line names the path")
        self.assertIn("symbolic link", m)
        self.assertIn(str(target), m, "and where the link points")
        self.assertEqual(kw["ring_text"], sb.FLAG_LINK_RING % PARENT, "the ring text names no path and no target")
        self.assertNotIn(self.root, kw["ring_text"])
        self.assertLessEqual(len(kw["ring_text"]), sb.ERROR_CENTER_TEXT_CAP)
        self.assertEqual(_temps(self.d), [])

    def test_the_write_goes_to_a_fresh_inode_so_a_hard_link_is_never_refreshed(self):
        """correctness-4 / extra8-3 (review round 3 of the env-pick door, 2026-09-19): the link guard sees symbolic
        links only, and the in-place O_CREAT|O_TRUNC write went through the existing inode, so a hard link at the
        path carried every connect's env block, credential value included, to a file under another name. The choice,
        stated in the writer: the bytes go to a FRESH inode renamed over the path, never through the existing one (a
        refusal on the link count was tried by the reviewers and rejected: it stops ordinary connects over a
        snapshot). The other name keeps the OLD bytes, as a copy would, and is never written again."""
        p = Path(self.d, sb.FLAG_SETTINGS_DIR, PARENT + ".json")
        self.assertEqual(sb.flag_settings_path(self.d, PARENT, env={"OLD_FLAG": "x"}), str(p))
        other = Path(self.root, "other-name.json")
        os.link(str(p), str(other))
        self.assertEqual(os.stat(other).st_nlink, 2, "the state under test: one inode, two names")
        before = os.stat(p).st_ino
        self.assertEqual(sb.flag_settings_path(self.d, PARENT, env=ENV), str(p))
        self.assertNotEqual(os.stat(p).st_ino, before, "a fresh inode: the bytes never went through the existing one")
        self.assertEqual(json.loads(p.read_text())["env"], ENV)
        self.assertEqual(json.loads(other.read_text()), {"env": {"OLD_FLAG": "x"}},
                         "the other name keeps the old bytes and is never refreshed")
        self.assertEqual(os.stat(other).st_nlink, 1)
        self.assertEqual(_temps(self.d), [])

    def test_a_failed_rename_leaves_no_temp_and_the_old_file_whole(self):
        """write_reg's pattern (review round 3, 2026-09-19; kernel-4 and extra8-3): a writer-unique temp (pid and a
        random suffix) renamed into place and unlinked in a finally, so a launch reading at that moment sees the old
        file or the new one, never a torn one, and a rename that fails the way a full disk fails it leaves no temp.
        The row it logs names the path on the kernel log line and no path in the ring text."""
        sb.flag_settings_path(self.d, PARENT, env={"OLD_FLAG": "x"})
        p = Path(self.d, sb.FLAG_SETTINGS_DIR, PARENT + ".json")
        seen = []

        def boom(real, src, dst):
            seen.append(os.path.basename(src))
            raise OSError(errno.ENOSPC, "No space left on device")
        _interpose(self, replace=boom)
        logged, log = self._log()
        self.assertEqual(sb.flag_settings_path(self.d, PARENT, env=ENV, fast=True, log=log), "", "degrade to launch")
        self.assertEqual(json.loads(p.read_text()), {"env": {"OLD_FLAG": "x"}}, "the old file stands whole: never a torn one")
        self.assertEqual(_temps(self.d), [], "a failed rename leaves no temp behind")
        self.assertEqual(len(seen), 1)
        self.assertRegex(seen[0], r"^%s\.json\.%d\.[0-9a-f]{8}\.tmp$" % (re.escape(PARENT), os.getpid()),
                         "writer-unique: the pid and a random suffix, write_reg's name")
        self.assertEqual(len(logged), 1, logged)
        m, problem, kw = logged[0]
        self.assertTrue(problem)
        self.assertIn(str(p), m)
        self.assertIn("unwritable", m)
        self.assertIn("launching WITHOUT env, fastMode", m)
        self.assertEqual(kw["ring_text"], sb.FLAG_UNWRITABLE_RING % (PARENT, "OSError", "env, fastMode"))
        self.assertNotIn(self.root, kw["ring_text"], "no path in the short form: a path's length is the state root's")

    def test_every_writer_rows_worst_case_is_computed_from_its_format_and_fits_the_cap(self):
        """correctness-3 / kernel-2 (review round 3, 2026-09-19): the class, not the instance. Each row's worst case,
        the longest fixed text (the longest sid reason), the sid budget spent (a repr past it is cut with the marker),
        the class budget spent and every flag-settings key riding, is computed HERE from the module's constants and
        asserted under the error centre's cap and whole through the feed's cut; then the real writer is driven over a
        root longer than any home, with every key riding, a sid past the budget and a directory where the file goes,
        to show the constants are what it renders."""
        km = load_source("romp_kernel", os.path.join(BIN, "romp-kernel"))
        keys = ", ".join(sb.FLAG_SETTINGS_KEYS)
        self.assertEqual(sorted(sb.FLAG_SETTINGS_KEYS), list(sb.FLAG_SETTINGS_KEYS), "sorted, as the writer joins them")
        sid_worst = sb.FLAG_SID_RING % (max(sb.FLAG_SID_REASONS, key=len), "x" * sb.RING_SID_BUDGET, keys)
        link_worst = sb.FLAG_LINK_RING % ("x" * sb.RING_SID_BUDGET)
        unw_worst = sb.FLAG_UNWRITABLE_RING % ("x" * sb.RING_SID_BUDGET, "x" * sb.RING_CLASS_BUDGET, keys)
        for name, worst in (("sid", sid_worst), ("link", link_worst), ("unwritable", unw_worst)):
            self.assertLessEqual(len(worst), sb.ERROR_CENTER_TEXT_CAP, (name, len(worst), worst))
            self.assertEqual(km._sdk_problem_text(worst), worst, "and whole in the feed")
        long_root = os.path.join(self.root, "a" * 120)
        os.makedirs(os.path.join(long_root, sb.FLAG_SETTINGS_DIR))
        p = Path(long_root, sb.FLAG_SETTINGS_DIR, PARENT + ".json")
        p.mkdir()                                                    # the rename over a directory fails
        logged, log = self._log()
        riding = dict(ultracode=True, fast=True, no_helper=True, env=ENV)
        self.assertEqual(sb.flag_settings_path(long_root, PARENT, log=log, **riding), "")
        long_sid = "x" * (sb.RING_SID_BUDGET + 30) + "/y"
        self.assertEqual(sb.flag_settings_path(long_root, long_sid, log=log, **riding), "")
        self.assertEqual(len(logged), 2, logged)
        self.assertIn(str(p), logged[0][0], "the kernel log line names the path")
        self.assertGreater(len(logged[0][0]), sb.ERROR_CENTER_TEXT_CAP, "the whole line would not fit the error centre over this root")
        self.assertEqual(logged[0][2]["ring_text"], sb.FLAG_UNWRITABLE_RING % (PARENT, "IsADirectoryError", keys))
        cut = sb._cred.cut_to(repr(long_sid), sb.RING_SID_BUDGET)
        self.assertTrue(cut.endswith(sb._cred.CUT_MARK) and len(cut) == sb.RING_SID_BUDGET, cut)
        self.assertEqual(logged[1][2]["ring_text"], sb.FLAG_SID_RING % (sb.FLAG_SID_REASONS[2], cut, keys))
        for m, problem, kw in logged:
            self.assertTrue(problem)
            self.assertNotIn(long_root, kw["ring_text"], "no path in the short form")
            self.assertLessEqual(len(kw["ring_text"]), sb.ERROR_CENTER_TEXT_CAP, kw["ring_text"])
            self.assertEqual(km._sdk_problem_text(kw["ring_text"]), kw["ring_text"])
        self.assertEqual(_temps(long_root), [])


class SpawnEnv(_Backend):
    def test_spawn_persists_the_env_in_the_reg(self):
        sid = self.be.spawn("web", "/tmp", env=ENV)
        self.assertEqual(self._reg(sid).get("env"), ENV)

    def test_spawn_without_env_writes_no_key(self):
        sid = self.be.spawn("web", "/tmp")
        self.assertNotIn("env", self._reg(sid))

    def test_spawn_refuses_a_bad_payload_loudly(self):
        with self.assertRaises(ValueError):
            self.be.spawn("web", "/tmp", env={"9BAD": "1"})
        with self.assertRaises(ValueError):
            self.be.spawn("web", "/tmp", env={"FEATURE_FLAG": 1})

    def test_spawn_refuses_the_identity_names(self):
        # a reg born with ROMP_SID in its user env would shadow-race the identity at every connect
        with self.assertRaises(ValueError):
            self.be.spawn("web", "/tmp", env={"ROMP_SID": PARENT})
        with self.assertRaises(ValueError):
            self.be.spawn("web", "/tmp", env={"ROMP_SESSION_NAME": "impostor"})


class _OptionsBackend(_Backend):
    """_Backend plus the _options seam: ClaudeAgentOptions is a parameter (a dict stands in) and
    the in-function import only needs HookMatcher — stub the module when the real dependency is
    absent (CI without the venv)."""

    def setUp(self):
        super().setUp()
        import sys
        import types
        self._fake_sdk = "claude_agent_sdk" not in sys.modules and not sb.sdk_importable()
        if self._fake_sdk:
            fake = types.ModuleType("claude_agent_sdk")
            # an attribute-bearing stand-in, like the SDK's dataclass: with hosts on (the default since T348) the
            # options loop sets each matcher's `timeout` to the host's hook bound, which a plain dict refused
            fake.HookMatcher = lambda **kw: types.SimpleNamespace(**kw)
            sys.modules["claude_agent_sdk"] = fake

    def tearDown(self):
        import sys
        if self._fake_sdk:
            sys.modules.pop("claude_agent_sdk", None)
        super().tearDown()

    def _options_kw(self, sess):
        return self.be._options(sess, dict)


class OptionsThreadsEnv(_OptionsBackend):
    """_options → flag_settings_path(env=…): the file the CLI launches with carries the reg's env."""

    def test_the_settings_file_carries_the_regs_env(self):
        sid = self.be.spawn("web", "/tmp", env=ENV)
        kw = self._options_kw(self._sess(sid))
        self.assertIn("settings", kw)
        self.assertEqual(json.loads(Path(kw["settings"]).read_text())["env"], ENV)

    def test_no_env_and_no_flags_means_no_settings_file(self):
        sid = self.be.spawn("web", "/tmp")
        kw = self._options_kw(self._sess(sid))
        self.assertNotIn("settings", kw,
                         "the return-\"\"-when-no-keys contract: a plain session launches without "
                         "a flag-settings file at all")

    def test_every_connect_rewrites_the_file_so_reconnects_reassert(self):
        sid = self.be.spawn("web", "/tmp", env=ENV)
        s = self._sess(sid)
        p = self._options_kw(s)["settings"]
        Path(p).write_text('{"env": {"TAMPERED": "yes"}}')   # drift the file behind romp's back
        p2 = self._options_kw(s)["settings"]
        self.assertEqual(p2, p)
        self.assertEqual(json.loads(Path(p2).read_text())["env"], ENV,
                         "the file is rewritten from the session on EVERY use — a reconnect "
                         "re-asserts the env by construction, never trusts what's on disk")

    def test_a_failed_flag_write_degrades_loudly_through_options(self):
        # the connect-time seam: /new already echoed the env as applied, so a write failure here
        # must reach the Log as a problem — the session launching without its env is otherwise
        # invisible to every surface (no readback channel)
        sid = self.be.spawn("web", "/tmp", env=ENV)
        Path(self.be.state_dir, sb.FLAG_SETTINGS_DIR).write_text("not a directory")
        logged = []
        self.be._log = lambda msg, problem=False, **kw: logged.append((msg, problem))
        kw = self._options_kw(self._sess(sid))
        self.assertNotIn("settings", kw, "degrade to launch, never abort the connect")
        self.assertTrue(any(problem and "env" in msg for msg, problem in logged),
                        "the drop must land in the Log as a problem naming env: %r" % (logged,))


class SetEnv(_Backend):
    """set_env: set_effort's persist+reconnect shape, minus the UI slice's badge/chip machinery."""

    def _live(self, sid):
        s = self._sess(sid)
        s.request_reconnect = lambda *a, **k: self.reconnects.append(1)
        self.reconnects = []
        self.be.sessions[sid] = s
        return s

    def test_a_change_persists_and_reconnects(self):
        sid = self.be.spawn("web", "/tmp")
        s = self._live(sid)
        self.assertTrue(self.be.set_env(sid, ENV))
        self.assertEqual(self._reg(sid)["env"], ENV)
        self.assertEqual(s.env_vars, ENV)
        self.assertTrue(self.reconnects, "env is connect-time — the reconnect is what applies it")

    def test_an_unchanged_reassert_skips_the_reconnect(self):
        sid = self.be.spawn("web", "/tmp", env=ENV)
        self._live(sid)
        self.assertTrue(self.be.set_env(sid, dict(ENV)))
        self.assertFalse(self.reconnects,
                         "same env = nothing to apply: the fresh-spawn echo and the nightly "
                         "re-brief must not churn the CLI process")

    def test_replace_not_merge(self):
        sid = self.be.spawn("web", "/tmp", env=ENV)
        self._live(sid)
        self.assertTrue(self.be.set_env(sid, {"FEATURE_FLAG": "0"}))
        self.assertEqual(self._reg(sid)["env"], {"FEATURE_FLAG": "0"},
                         "the payload IS the session's per-session env — names not re-asserted drop")

    def test_refuses_junk_and_unknown_sids(self):
        sid = self.be.spawn("web", "/tmp", env=ENV)
        self.assertFalse(self.be.set_env(sid, {"9BAD": "1"}))
        self.assertEqual(self._reg(sid)["env"], ENV, "a refused payload must not half-apply")
        self.assertFalse(self.be.set_env(CHILD, ENV), "no reg, no session — refuse, don't mint")

    def test_refuses_a_nul_value(self):
        sid = self.be.spawn("web", "/tmp", env=ENV)
        self.assertFalse(self.be.set_env(sid, {"FEATURE_FLAG": "1\x00x"}),
                         "a NUL value is unfulfillable — refuse, never persist it into the reg")
        self.assertEqual(self._reg(sid)["env"], ENV, "the poisoned payload must not half-apply")

    def test_refuses_the_identity_names(self):
        sid = self.be.spawn("web", "/tmp", env=ENV)
        self.assertFalse(self.be.set_env(sid, {"ROMP_SESSION_NAME": "impostor"}),
                         "the identity env is romp's own — never a per-session override")
        self.assertEqual(self._reg(sid)["env"], ENV, "the refused payload must not half-apply")

    def test_an_explicit_empty_dict_clears_and_reconnects(self):
        # the replace-not-merge contract's limiting case: {} DECLARES "no per-session env" —
        # the only way to remove a spawn-time debugging var from a running session
        sid = self.be.spawn("web", "/tmp", env=ENV)
        s = self._live(sid)
        self.assertTrue(self.be.set_env(sid, {}))
        self.assertEqual(self._reg(sid)["env"], {}, "the empty declaration replaces the whole set")
        self.assertEqual(s.env_vars, {})
        self.assertTrue(self.reconnects, "clearing is a CHANGE — it applies by reconnecting")
        self.assertEqual(sb.flag_settings_path(self.be.state_dir, sid, env=s.env_vars), "",
                         "cleared env adds no key — the next connect launches without a flag file")
        self.reconnects.clear()
        self.assertTrue(self.be.set_env(sid, {}), "re-clearing is the unchanged re-assert")
        self.assertFalse(self.reconnects, "already clear = nothing to apply, no CLI churn")

    def test_a_dormant_session_persists_without_a_live_object(self):
        sid = self.be.spawn("web", "/tmp")
        self.assertTrue(self.be.set_env(sid, ENV))
        self.assertEqual(self._reg(sid)["env"], ENV,
                         "the next connect reads the reg — persistence alone is a full apply "
                         "for a session with no live client")


class ForkInheritsEnv(_Backend):
    def test_a_fork_carries_the_parents_env(self):
        os.environ["CLAUDE_CONFIG_DIR"] = tempfile.mkdtemp()   # transcript_path resolves through this
        try:
            self.be.spawn("parent", self.d, sid=PARENT, env=ENV)
            self.be.fork("child", PARENT, "a1", sid=CHILD)
            self.assertEqual(self._reg(CHILD).get("env"), ENV,
                             "it is that conversation, continued elsewhere — env inherits like "
                             "model/auth do")
        finally:
            os.environ.pop("CLAUDE_CONFIG_DIR", None)

    def test_a_fork_of_an_env_less_parent_stays_env_less(self):
        os.environ["CLAUDE_CONFIG_DIR"] = tempfile.mkdtemp()
        try:
            self.be.spawn("parent", self.d, sid=PARENT)
            self.be.fork("child", PARENT, "a1", sid=CHILD)
            self.assertNotIn("env", self._reg(CHILD))
        finally:
            os.environ.pop("CLAUDE_CONFIG_DIR", None)


class LegacyReservedEnv(_OptionsBackend):
    """Regs written before ENV_RESERVED_NAMES existed can carry ROMP_SID / ROMP_SESSION_NAME in
    their stored env. Spawn and set_env refuse them at the door now — but a standing reg is
    replayed verbatim at every connect, and fork() copies the parent's. Three obligations at the
    apply seam: the session still LAUNCHES (a reconnect refusal would brick a long-running session
    over a var accepted under older rules), the reserved name never reaches the applied env (it
    would shadow-race the options.env identity — `romp end self` resolving to a forged sid), and
    the skip is LOUD, naming the session and the ignored var (never silently)."""

    def _poisoned(self, env):
        """A reg whose stored env predates the reserved-name rule — written behind the validator,
        the way those regs actually exist on disk."""
        sid = self.be.spawn("web", "/tmp")
        reg = self._reg(sid)
        reg["env"] = dict(env)
        sb.write_reg(self.be.state_dir, sid, reg)
        return sid

    def test_a_pre_rule_reg_launches_with_the_reserved_name_skipped(self):
        sid = self._poisoned({"FEATURE_FLAG": "1", "ROMP_SID": PARENT})
        logged = []
        self.be._log = lambda msg, problem=False: logged.append((msg, problem))
        kw = self._options_kw(self._sess(sid))
        applied = json.loads(Path(kw["settings"]).read_text())["env"]
        self.assertEqual(applied, {"FEATURE_FLAG": "1"},
                         "the rest of the stored env still applies — skip the var, not the session")
        self.assertEqual(kw["env"]["ROMP_SID"], sid,
                         "the identity overlay stands untouched — the forged sid never shadows it")
        self.assertTrue(any(problem and "ROMP_SID" in msg and "web" in msg
                            for msg, problem in logged),
                        "the skip must be loud, naming the session and the ignored var: %r"
                        % (logged,))

    def test_a_reg_carrying_only_reserved_names_still_launches(self):
        sid = self._poisoned({"ROMP_SESSION_NAME": "impostor"})
        logged = []
        self.be._log = lambda msg, problem=False: logged.append((msg, problem))
        kw = self._options_kw(self._sess(sid))
        self.assertNotIn("settings", kw,
                         "nothing left after the skip = the no-keys contract, not an empty env")
        self.assertEqual(kw["env"]["ROMP_SESSION_NAME"], "web")
        self.assertTrue(any(problem and "ROMP_SESSION_NAME" in msg for msg, problem in logged))

    def test_a_fork_drops_the_reserved_names_from_the_inherited_env(self):
        os.environ["CLAUDE_CONFIG_DIR"] = tempfile.mkdtemp()   # transcript_path resolves through this
        try:
            self.be.spawn("parent", self.d, sid=PARENT)
            reg = self._reg(PARENT)
            reg["env"] = {"FEATURE_FLAG": "1", "ROMP_SID": PARENT}
            sb.write_reg(self.be.state_dir, PARENT, reg)
            logged = []
            self.be._log = lambda msg, problem=False: logged.append((msg, problem))
            self.be.fork("child", PARENT, "a1", sid=CHILD)
            self.assertEqual(self._reg(CHILD).get("env"), {"FEATURE_FLAG": "1"},
                             "the copy is where a legacy reg's poison stops propagating")
            self.assertTrue(any(problem and "ROMP_SID" in msg and "child" in msg
                                for msg, problem in logged),
                            "the drop must be loud, naming the session and the var: %r" % (logged,))
        finally:
            os.environ.pop("CLAUDE_CONFIG_DIR", None)


class ValidatorLockstep(unittest.TestCase):
    """_env_error (the /new door's kernel-side mirror) and env_request_error are hand-kept copies.
    Spawn backs the door with a loud ValueError, but set_env refuses with a silent False its callers
    discard — so drift between the copies on the existing:true path would be a 200 with an env echo
    and NOTHING applied. This pin is the backstop the door docstring cites: identical verdicts
    (messages included) across the whole good/bad payload table, so loosening one copy fails here
    instead of going silent."""

    PAYLOADS = (
        # valid: plain, underscore/empty-value, the vacuous empty declaration
        {"FEATURE_FLAG": "1"}, {"_UNDER": "x", "A9": ""}, {},
        # non-dicts, truthy and falsy alike (the door 400s all of them)
        "FEATURE_FLAG=1", ["FEATURE_FLAG"], 7, None, False, 0, "", [],
        # bad names
        {"9BAD": "1"}, {"": "1"}, {"BAD-NAME": "1"}, {"BAD NAME": "1"}, {"über": "1"},
        # the reserved identity names (options.env owns them), alone and riding a valid payload
        {"ROMP_SID": "x"}, {"ROMP_SESSION_NAME": "web"}, {"FEATURE_FLAG": "1", "ROMP_SID": "x"},
        # bad values, the NUL hole included
        {"FEATURE_FLAG": 1}, {"FEATURE_FLAG": None}, {"FEATURE_FLAG": True},
        {"FEATURE_FLAG": {"nested": "no"}}, {"FEATURE_FLAG": "1\x00x"},
        # credential-shaped names of other spellings (2026-09-18): refused by the rule credentials.py holds for
        # both copies; an empty or whitespace value holds no secret and passes; the control token is refused like
        # any other since review round 1 (its exclusion is the boot notice's alone); a bad value under such a
        # name is the value's refusal, whichever copy answers
        {"NOTES_API_TOKEN": _secret_value("notes-token")}, {"NOTES_API_KEY": _secret_value("notes-key")},
        {"OP_SESSION_notes": _secret_value("op-session")}, {"OP_CONNECT_TOKEN": _secret_value("op-connect")},
        {"NOTES_ENDPOINT": "http://notes.test", "NOTES_API_TOKEN": _secret_value("notes-token"),
         "NOTES_API_KEY": _secret_value("notes-key")},
        {"EMPTY_TOKEN": ""}, {"SPACES_TOKEN": "  "}, {"ROMP_SERVE_TOKEN": "control"},
        {"NOTES_API_TOKEN": 1}, {"NOTES_API_TOKEN": "a\x00b"},
        # the suffixes fold case (the spawn-spec fix's review round 1, 2026-09-18, carried into the door's
        # predicate): a lowercase or mixed-case spelling is the same shape; the control-token exclusion is
        # the exact name romp reads, so another spelling of it is refused like any other; a name whose suffix
        # only begins with the shape passes in any case
        {"notes_api_token": _secret_value("notes-token")}, {"Notes_Api_Key": _secret_value("notes-key")},
        {"romp_serve_token": _secret_value("control-lower")}, {"editor_tokenizer": "x"}, {"empty_token": ""},
        # the 1Password half folds too (review round 1 of the env-pick door, 2026-09-18): both copies, one verdict
        {"op_session_notes": _secret_value("op-session-lower")}, {"Op_Account": "acct"}, {"options_for_x": "x"},
    )

    @staticmethod
    def _kernel():
        import sys
        if "romp_kernel" in sys.modules:
            return sys.modules["romp_kernel"]
        # the kernel imports its deps by these exact module names (the test_new_route_prefs pattern)
        for name, fn in (("romp_event_model", "romp-event-model"), ("romp_judge", "romp-judge")):
            if name not in sys.modules:
                load_source(name, os.path.join(BIN, fn))
        return load_source("romp_kernel", os.path.join(BIN, "romp-kernel"))

    def test_the_two_validator_copies_agree_verdict_for_verdict(self):
        km = self._kernel()
        for payload in self.PAYLOADS:
            self.assertEqual(km._env_error(payload), sb.env_request_error(payload),
                             "the copies must stay in lockstep — payload %r" % (payload,))

    CREDENTIALS = ({"ANTHROPIC_API_KEY": "x"}, {"ANTHROPIC_AUTH_TOKEN": "x"}, {"CLAUDE_CODE_OAUTH_TOKEN": "x"})

    def test_the_copies_agree_that_a_credential_name_is_always_reserved(self):
        """romp holds no API key (2026-09-08): a session's credential is Claude Code's own resolution, so a
        per-session env payload naming any credential variable is refused for EVERY pick, in both copies,
        with the same words. Before this the key competed only while romp ran a provider, and a login
        session's own token override passed."""
        km = self._kernel()
        for auth in ("", "key", "login"):
            for p in self.CREDENTIALS:
                a, b = km._env_error(p, auth), sb.env_request_error(p, auth)
                self.assertEqual(a, b, "the copies must stay in lockstep (auth=%r, payload %r)" % (auth, p))
                self.assertIn("is reserved: a session's credential is Claude Code's own", a)
                self.assertIn(next(iter(p)), a, "the offender is named")

    def test_the_copies_agree_that_a_credential_shaped_name_is_refused(self):
        """The spawn.json fix's build found the doors refusing the three login names alone (2026-09-18): a pick
        naming NOTES_API_TOKEN or an OP_* variable landed in the registry and the flag-settings file. Both
        copies now refuse such a pick, for every billing pick, with credentials.py's one wording, naming the
        variable and never its value."""
        km = self._kernel()
        val = _secret_value("notes-token")
        for auth in ("", "key", "login"):
            for p in ({"NOTES_API_TOKEN": val}, {"OP_SESSION_notes": val}, {**PLAIN, "NOTES_API_KEY": val},
                      {"notes_api_token": val}, {**PLAIN, "Notes_Api_Key": val}):   # the fold, in both copies
                a, b = km._env_error(p, auth), sb.env_request_error(p, auth)
                self.assertEqual(a, b, "the copies must stay in lockstep (auth=%r, payload %r)" % (auth, sorted(p)))
                self.assertTrue(a, "refused (auth=%r, payload %r)" % (auth, sorted(p)))
                name = next(n for n in p if n not in PLAIN)
                self.assertIn(name, a, "the offender is named")
                self.assertNotIn(val, a, "the value is never in the message")
                self.assertIn("the pick was not saved", a)


class DrivePlumbing(unittest.TestCase):
    """The /new door rides the same park/drain path as the other per-session switches (source pins,
    the test_session_auth.DrivePlumbing pattern)."""

    def test_the_op_is_routed_parked_and_replayed(self):
        src = open(os.path.join(BIN, "romp-kernel")).read()
        self.assertIn("def _set_env_or_park(be, sid, value):", src)
        self.assertIn('_gate_or_park(sid, ("env", value))', src)   # parks on the gate, or hands over (2026-09-05)
        self.assertIn('elif op[0] == "env":', src)
        self.assertIn("refused = be.set_env(sid, op[1]) is False", src,
                      "the drain reads the verdict (review round 1 of the env-pick door, 2026-09-18); the refusal "
                      "itself is pinned by execution in tests/test_kernel_meta_command_gate.py")
        self.assertIn('("model", "effort", "fast", "env", "cwd")', src,
                       "a repeat env pick REPLACES the earlier parked one in place, like model/effort (and a move)")

    def test_the_create_path_passes_env_through(self):
        src = open(os.path.join(BIN, "romp-kernel")).read()
        # (parent + tags joined the signature with tab groups, 2026-09-04 — env's slot is unchanged)
        self.assertIn('def _create_sdk_session(nm, cwd, auth="", prefs=None, client=None, env=None, parent="", tags=()):', src)
        self.assertIn("sid = _sdk().spawn(nm, cwd, bg, fg, auth=auth, env=env)", src,
                      "env rides the SPAWN — the reg is born with it, ahead of the prefs pass")


# ── The session-identity environment surface (upstream; the user 2026-08-15 sid, 2026-08-16 name).
# Every SDK session's CLI process — and every Bash it runs — carries its romp identity in env:
# ROMP_SID (the stable uuid; what `romp end self` resolves through) and ROMP_SESSION_NAME (the
# human name at spawn). The name is a GENERIC capability for child processes that need to know
# which session they belong to (attribution, logging), deliberately coupled to no consumer.
# Env is spawn-frozen, so a post-spawn rename is not reflected — the sid is the address, the
# name a label. Source pins over _options' env line (the SDK merges options.env OVER the
# inherited environment, so both ride the same additive overlay as the bin PATH). Distinct layer
# from the per-session user env above: identity rides options.env (the transport), user env the
# per-sid flag-settings file — neither writes the other's layer.
SDK = Path(os.path.join(os.path.dirname(HERE), "kernel", "sdk_backend.py")).read_text()


class SessionIdentityEnv(unittest.TestCase):
    def test_sid_and_name_ride_the_spawn_env(self):
        self.assertIn('"ROMP_SID": str(sess.sid),', SDK,
                      "the stable identity — addressing (romp end self)")
        self.assertIn('"ROMP_SESSION_NAME": str(sess.name)', SDK,
                      "the human name at spawn — attribution/logging for child processes")

    def test_the_name_is_documented_as_spawn_frozen(self):
        # the caveat is the contract: a rename after spawn is NOT reflected in a live session's
        # env, so nothing may treat the name as an address — the comment must keep saying so
        self.assertIn("a rename after spawn is NOT reflected", SDK)

    def test_one_env_overlay_only(self):
        # both vars ride _options' single env= overlay (additive over os.environ via
        # _bin_on_path_env) — a second env assembly would fork the truth
        self.assertEqual(SDK.count('"ROMP_SESSION_NAME":'), 1)
        self.assertEqual(SDK.count('env={**_bin_on_path_env(os.environ)'), 1)


if __name__ == "__main__":
    unittest.main()


class EnvSecretsStayPrivate(unittest.TestCase):
    """Env values can be secrets (PR #889 review): the per-sid flag-settings file is created 0600
    like the serve token, and the parked chat chip renders NAMES only — never a value."""

    def test_the_flag_settings_file_is_private(self):
        import stat
        d = tempfile.mkdtemp()
        p = sb.flag_settings_path(d, "11111111-2222-3333-4444-555555555555", env={"TOKEN": "s3cret"})
        self.assertTrue(p, "an env writes the file")
        self.assertEqual(stat.S_IMODE(os.stat(p).st_mode), 0o600, "0600, the serve-token treatment")
        self.assertIn("s3cret", open(p).read(), "…and the value is in it (the CLI reads it), private")
        p2 = sb.flag_settings_path(d, "11111111-2222-3333-4444-555555555555", env={"TOKEN": "other"})
        self.assertEqual(stat.S_IMODE(os.stat(p2).st_mode), 0o600, "a rewrite keeps it private")

    def test_the_parked_chip_names_the_vars_but_never_their_values(self):
        km = load_source("romp_kernel", os.path.join(BIN, "romp-kernel"))
        md = km._parked_md(("env", {"B_TOKEN": "s3cret", "A_FLAG": "1"}))
        self.assertEqual(md, "/env A_FLAG B_TOKEN", "sorted names, no values")
        self.assertNotIn("s3cret", md)
        self.assertEqual(km._parked_md(("env", {})), "/env (cleared)")




class CredentialShapedNamesAtTheDoor(unittest.TestCase):
    """The door refuses a pick naming a credential-shaped variable of ANY spelling (2026-09-18, found by the
    spawn.json fix's build; the box admin ruled the door the fix): until then env_request_error refused the
    three login names alone, so NOTES_API_TOKEN=... typed into the pick was written into the registry and
    the per-sid flag-settings file, against the fork's rule that no credential is ever written to a file.
    The rule is the spawn.json writer's (spawn_env_secret_names) over the pick itself, one rule, never a
    second list; the message names the variable(s), never a value, says where the value belongs, and that
    nothing was saved. Values are built at run time (never a token-shaped literal: gitleaks reads tests)."""

    def test_a_credential_shaped_name_is_refused_by_name_and_the_pick_without_it_passes(self):
        for name in ("NOTES_API_TOKEN", "NOTES_API_KEY", "OP_SESSION_notes", "OP_SERVICE_ACCOUNT_TOKEN"):
            val = _secret_value("value")
            for auth in ("", "key", "login"):
                err = sb.env_request_error({**PLAIN, name: val}, auth)
                self.assertTrue(err, "%s must be refused for auth=%r" % (name, auth))
                self.assertIn(name, err, "the offending NAME is in the message")
                self.assertNotIn(val, err, "the VALUE is never in the message")
                self.assertNotIn("NOTES_ENDPOINT", err, "the plain name is not blamed")
                self.assertIn("the pick was not saved", err)
                self.assertIn("process environment", err, "the message says where such a value belongs")
                self.assertTrue(err.startswith("env: "), "the env doors' prefix, like every other refusal")
                self.assertEqual(err, "env: " + sb._cred.credential_env_refusal([name]),
                                 "the door's head once, in front of the shared sentence (review round 1, 2026-09-18)")
        self.assertEqual(sb.env_request_error(dict(PLAIN)), "", "the same pick without the name passes")

    def test_the_shared_sentence_carries_no_head_of_its_own(self):
        """Review round 1 (2026-09-18): the sentence began "env: " and set_env's log line put its own head in front,
        so the row read "pick refused: env: ...". Each door adds the head once; the sentence leads with the names."""
        sentence = sb._cred.credential_env_refusal(["NOTES_API_TOKEN"])
        self.assertTrue(sentence.startswith("NOTES_API_TOKEN is credential-shaped"), sentence)
        self.assertNotIn("env: ", sentence)
        short = sb._cred.credential_env_ring_text(["NOTES_API_TOKEN"])
        self.assertTrue(short.startswith("NOTES_API_TOKEN is credential-shaped: the pick was not saved"), short)
        self.assertIn("process environment", short)
        self.assertNotIn("env: ", short)

    def test_the_control_token_is_refused_like_any_credential_shaped_name(self):
        """Review round 1 (2026-09-18): the door reused a rule that left ROMP_SERVE_TOKEN unnamed for the boot line's
        sake, so romp's own control token was the one credential-shaped name a pick could still write to the
        registry and the flag-settings file, while the reference's lister reported it as an offender. The
        exclusion is the boot notice's alone now; the rule, the writer and the doors name it."""
        pick = {"ROMP_SERVE_TOKEN": "control"}
        err = sb.env_request_error(pick)
        self.assertIn("ROMP_SERVE_TOKEN is credential-shaped", err)
        self.assertEqual(sb._cred.credential_env_names(pick), ["ROMP_SERVE_TOKEN"], "the rule names it")
        self.assertEqual(sb.spawn_env_secret_names(pick), ["ROMP_SERVE_TOKEN"], "the writer moves it")
        self.assertEqual(sb.env_credential_names(pick), [], "the boot line alone leaves it unnamed")
        self.assertEqual(sb.env_credential_names({"romp_serve_token": "c"}), ["romp_serve_token"],
                         "and that exclusion stays the exact name romp reads")

    def test_every_offending_name_is_said_sorted_and_no_value(self):
        tok, key = _secret_value("tok"), _secret_value("key")
        err = sb.env_request_error({"NOTES_API_TOKEN": tok, **PLAIN, "NOTES_API_KEY": key})
        self.assertIn("NOTES_API_KEY, NOTES_API_TOKEN are credential-shaped", err, "all of them, sorted")
        self.assertNotIn(tok, err)
        self.assertNotIn(key, err)

    def test_the_door_judges_by_the_writers_rule(self):
        """One rule with the spawn.json writer: a well-formed pick is refused exactly when spawn_env_secret_names
        flags a name in it, and the names the message says are the writer's."""
        val = _secret_value("value")
        picks = ({**PLAIN, "NOTES_API_TOKEN": val}, {"EMPTY_TOKEN": ""}, {"SPACES_TOKEN": "  "},
                 {"ROMP_SERVE_TOKEN": "control"}, dict(PLAIN), {"OP_ACCOUNT": "acct"}, {"MY_SECRET_TOKEN": val},
                 {"TOKEN_FIRST": val}, {"API_KEY_HOLDER": val}, {"op_session_notes": val}, {"Op_Connect_Host": "h"})
        for pick in picks:
            flagged = sb.spawn_env_secret_names(pick)
            err = sb.env_request_error(pick)
            self.assertEqual(bool(err), bool(flagged), "door and writer disagree on %r" % (sorted(pick),))
            for n in flagged:
                self.assertIn(n, err)
            self.assertNotIn(val, err)

    def test_an_empty_credential_shaped_value_passes_as_the_writer_keeps_it(self):
        # the writer leaves an empty value in its file (it holds no secret; there it is the unset it means), so
        # the door lets it through too: one rule
        self.assertEqual(sb.env_request_error({"EMPTY_TOKEN": ""}), "")
        self.assertEqual(sb.env_request_error({**PLAIN, "EMPTY_API_KEY": ""}), "")

    def test_a_lowercase_or_mixed_case_credential_shaped_name_is_refused_with_the_same_words(self):
        """The spawn-spec fix's review round 1 (2026-09-18) made the writer's suffix test fold case, since a
        notes_api_token was otherwise written to spawn.json with its value; the door's predicate compared the
        suffixes exactly, so the same name typed into the pick passed the door and landed in the registry and
        the flag-settings file. One shape rule, never two: the door refuses the lowercase and mixed-case
        spellings, under their own spelling, with the refusal an upper-case name gets, the value in no message;
        an empty value and a name whose suffix only begins with the shape pass in any case."""
        for name, upper in (("notes_api_token", "NOTES_API_TOKEN"), ("Notes_Api_Key", "NOTES_API_KEY"),
                            ("hf_token", "HF_TOKEN"),
                            # the 1Password half folds too (review round 1 of the env-pick door, 2026-09-18: the fold
                            # had reached the suffixes alone, so a lowercase session token passed every door)
                            ("op_session_notes", "OP_SESSION_NOTES"), ("Op_Account", "OP_ACCOUNT")):
            val = _secret_value("value")
            for auth in ("", "key", "login"):
                err = sb.env_request_error({**PLAIN, name: val}, auth)
                self.assertTrue(err, "%s must be refused for auth=%r" % (name, auth))
                self.assertEqual(err, "env: " + sb._cred.credential_env_refusal([name]), "the one wording, naming this spelling")
                self.assertEqual(err.replace(name, upper), sb.env_request_error({**PLAIN, upper: val}, auth),
                                 "the same refusal text as the upper-case spelling gets")
                self.assertNotIn(val, err, "the VALUE is never in the message")
                self.assertNotIn("NOTES_ENDPOINT", err, "the plain name is not blamed")
        self.assertEqual(sb.env_request_error({**PLAIN, "empty_token": "", "editor_tokenizer": "x"}), "",
                         "an empty value holds no secret and a prefix-only suffix is not the shape, in any case")

    def test_the_three_login_names_keep_their_own_words(self):
        # the loop's refusal of the three stands first, whatever the value, with the wording other tests pin
        for name in sb.AUTH_ENV_NAMES:
            err = sb.env_request_error({name: ""})
            self.assertIn("Claude Code's own", err)
            self.assertNotIn("credential-shaped", err)

    def test_the_advice_is_scoped_to_the_half_of_the_rule_the_name_matched(self):
        """fresh-2 (review round 2 of the env-pick door, 2026-09-19): the first wording sent every refused value to
        the process environment romp's service starts with, and for a 1Password name that is the road the boot check
        refuses (romp-manager exits 1 on it), so an operator following the printed advice for an OP_* name took the
        deployment down. The suffix half keeps that road; the 1Password half hears the boot check's own (a file of
        the helper's own, or the session's shells); a mixed pick hears both, each scoped. The boot check is executed
        here so the two sentences cannot drift apart from what it refuses."""
        suffix = sb._cred.credential_env_refusal(["NOTES_API_TOKEN"])
        op = sb._cred.credential_env_refusal(["OP_ACCOUNT"])
        mixed = sb._cred.credential_env_refusal(["NOTES_API_TOKEN", "op_session_notes"])
        self.assertIn("Put such a value in the process environment romp's service starts with", suffix)
        self.assertNotIn("Put such a value in the process environment", op,
                         "the road the boot check refuses is never advised for a 1Password name")
        self.assertIn("refuses a 1Password name in its process environment at boot", op)
        self.assertIn("its own file", op)
        self.assertIn("_API_KEY or _TOKEN value goes in romp's process environment", mixed)
        self.assertIn("1Password name is refused there at boot", mixed)
        self.assertEqual(sb._cred.credential_env_refusal(["op_account"]).replace("op_account", "OP_ACCOUNT"), op,
                         "the fold: a lowercase 1Password name hears the 1Password road")
        short_op = sb._cred.credential_env_ring_text(["OP_ACCOUNT"])
        self.assertIn("refused in the process environment at boot", short_op)
        self.assertNotIn("belongs in the process environment", short_op)
        # the ring text hears the road of the half matched too; its bound is the format's (CredentialShapedNamesEndToEnd
        # computes the worst case), and the full sentence is capped on no surface it reaches (the /new reply, romp
        # new's stderr, the kernel log), so every name rides it whole (review round 3, 2026-09-19: the pins here had
        # measured both against the caps with the three-character session name "web")
        for names, road in ((["NOTES_API_TOKEN"], "suffix"), (["OP_ACCOUNT"], "op"), (["OP_SERVICE_ACCOUNT_TOKEN"], "op"),
                            (["NOTES_API_TOKEN", "op_session_notes"], "mixed"), (["NOTES_API_TOKEN", "OP_SERVICE_ACCOUNT_TOKEN"], "mixed")):
            ring = sb._cred.credential_env_ring_text(names)
            self.assertTrue(ring.endswith(sb._cred.CREDENTIAL_RING_ROADS[road]), (names, ring))
            for n in names:
                self.assertIn(n, sb._cred.credential_env_refusal(names), "every name whole in the sentence")
        absent = os.path.join(tempfile.mkdtemp(), "absent.env")
        with self.assertRaises(RuntimeError, msg="the boot check refuses the road the first wording advised"):
            sb._cred.check_boot_environment(path=absent, environ={"OP_ACCOUNT": "acct"})
        sb._cred.check_boot_environment(path=absent, environ={"NOTES_API_TOKEN": "x"})   # a suffix name boots


class CredentialShapedNamesEndToEnd(_OptionsBackend):
    """The backend end to end (2026-09-18): a refused pick writes nothing, the stored env stands and the value
    is in no file under the state root; a plain name still lands in the flag-settings file; a stored env from
    before the rule still launches, with its name said in the problem ring and never its value."""

    def setUp(self):
        super().setUp()
        Path(self.d, "session-hosts").write_text("off\n")   # this root mints no host (the runner floors only its own)
        self.logged = []
        self.be._log = lambda msg, problem=False, **kw: self.logged.append((msg, problem, kw))

    def _files_carrying(self, text):
        hits = []
        for root, _dirs, files in os.walk(self.d):
            for f in files:
                p = os.path.join(root, f)
                try:
                    if text in Path(p).read_text(errors="replace"):
                        hits.append(p)
                except OSError:
                    pass
        return hits

    def _live(self, sid):
        s = self._sess(sid)
        self.reconnects = []
        s.request_reconnect = lambda *a, **k: self.reconnects.append(1)
        self.be.sessions[sid] = s
        return s

    def _flag_file(self, sid):
        return Path(self.be.state_dir, sb.FLAG_SETTINGS_DIR, "%s.json" % sid)

    def test_a_refused_pick_writes_nothing_and_the_previous_env_stands(self):
        sid = self.be.spawn("web", "/tmp", env=ENV)
        s = self._live(sid)
        self.be._options(s, dict)                              # the session launched with ENV: the file carries it
        self.assertEqual(json.loads(self._flag_file(sid).read_text())["env"], ENV)
        val = _secret_value("notes-token")
        self.assertFalse(self.be.set_env(sid, {**PLAIN, "NOTES_API_TOKEN": val}), "the pick is refused")
        self.assertEqual(self._reg(sid)["env"], ENV, "the stored pick stays what it was")
        self.assertEqual(s.env_vars, ENV, "the live session's env stays what it was")
        self.assertFalse(self.reconnects, "nothing to apply, no reconnect")
        text = self._flag_file(sid).read_text()
        self.assertEqual(json.loads(text)["env"], ENV, "the flag-settings file is untouched")
        self.assertNotIn("NOTES_API_TOKEN", text)
        self.be._options(s, dict)                              # the next connect rewrites the file from the reg
        self.assertEqual(json.loads(self._flag_file(sid).read_text())["env"], ENV)
        self.assertEqual(self._files_carrying(val), [], "the value is in no file under the state root")
        rows = [m for m, problem, _kw in self.logged if problem and "NOTES_API_TOKEN" in m]
        self.assertTrue(rows, "the refusal is a problem row naming the variable: %r" % (self.logged,))
        self.assertFalse(any(val in m for m, _p, _kw in self.logged), "no log line carries the value")

    def test_spawn_refuses_and_mints_no_file_carrying_the_value(self):
        before = sum(len(f) for _r, _d, f in os.walk(self.d))
        val = _secret_value("notes-key")
        with self.assertRaises(ValueError) as cm:
            self.be.spawn("api", "/tmp", env={**PLAIN, "NOTES_API_KEY": val})
        self.assertIn("NOTES_API_KEY", str(cm.exception))
        self.assertNotIn(val, str(cm.exception))
        self.assertEqual(self._files_carrying(val), [])
        self.assertEqual(sum(len(f) for _r, _d, f in os.walk(self.d)), before, "a refused spawn writes no file")

    def test_a_plain_name_still_lands_in_the_flag_settings_file(self):
        sid = self.be.spawn("web", "/tmp", env=dict(PLAIN))
        kw = self.be._options(self._sess(sid), dict)
        self.assertEqual(json.loads(Path(kw["settings"]).read_text())["env"], PLAIN,
                         "a name of no credential shape rides the file as before")
        self.assertTrue(self.be.set_env(sid, {**PLAIN, "FEATURE_FLAG": "1"}), "and a plain re-pick is accepted")

    def test_a_stored_credential_shaped_name_still_launches_and_is_said_once_per_session(self):
        """The launch path never ran the door, so a reg written before the rule (a pick accepted then) keeps
        launching: the variable is NOT stripped from what the CLI receives (a drop would change a running
        session's environment at its next reconnect with no gesture of the user's, and clean nothing: the
        registry holds the value). It is said instead, names only, keyed per session so the ring holds one row."""
        sid = self.be.spawn("web", "/tmp", env=ENV)
        val = _secret_value("notes-token")
        self.be._update_reg(sid, env={**ENV, "NOTES_API_TOKEN": val})   # a store from before the door refused it
        s = self._sess(sid)
        kw = self.be._options(s, dict)
        got = json.loads(Path(kw["settings"]).read_text())["env"]
        self.assertEqual(got, {**ENV, "NOTES_API_TOKEN": val}, "the stored env launches whole; nothing is dropped")
        rows = [(m, kw2) for m, problem, kw2 in self.logged if problem and "NOTES_API_TOKEN" in m]
        self.assertEqual(len(rows), 1, "one problem row names the stored variable: %r" % (self.logged,))
        self.assertNotIn(val, rows[0][0], "the value is never in the line")
        self.assertIn("the session launches with it", rows[0][0], "the fact")
        self.assertIn("flag-settings file", rows[0][0], "and where the value sits")
        ring = rows[0][1]["ring_text"]
        self.assertEqual(ring, sb.stored_offender_ring_text("web", ["NOTES_API_TOKEN"]))
        for promise in ("romp new", "re-declar", "redact", "remove", "clears", "until"):
            self.assertNotIn(promise, rows[0][0], "no remedy is promised (review round 3, 2026-09-19: the redaction road, a "
                                                  "re-declaration that removes the value from every file, left this change)")
            self.assertNotIn(promise, ring)
        self.assertEqual(rows[0][1].get("key"), ("env-stored-credential", sid), "keyed per session: the ring dedupes")
        self.assertFalse(any(val in m for m, _p, _k in self.logged))
        self.assertTrue(self.be.set_env(sid, dict(ENV)), "a re-declaration without the name is accepted by the door")
        self.assertEqual(self._reg(sid)["env"], ENV, "and the registry follows it, as before the door; the file is not this change's")

    def test_a_stored_lowercase_credential_shaped_name_is_said_too(self):
        """The stored-offender line judges by the writer's rule, which folds case since the spawn-spec fix's
        review round 1 (2026-09-18): a reg holding notes_api_token from before the door refused it launches
        whole, like the upper-case case above, and is said once under its own spelling, never its value."""
        sid = self.be.spawn("web", "/tmp", env=ENV)
        val = _secret_value("notes-token")
        self.be._update_reg(sid, env={**ENV, "notes_api_token": val})
        s = self._sess(sid)
        kw = self.be._options(s, dict)
        self.assertEqual(json.loads(Path(kw["settings"]).read_text())["env"], {**ENV, "notes_api_token": val},
                         "the stored env launches whole; nothing is dropped")
        rows = [(m, kw2) for m, problem, kw2 in self.logged if problem and "notes_api_token" in m]
        self.assertEqual(len(rows), 1, "one problem row names the stored lowercase variable: %r" % (self.logged,))
        self.assertNotIn(val, rows[0][0], "the value is never in the line")
        self.assertEqual(rows[0][1].get("key"), ("env-stored-credential", sid))
        self.assertFalse(any(val in m for m, _p, _k in self.logged))

    def test_a_fork_copies_no_credential_shaped_name_into_its_own_files(self):
        """Review round 1 of the env-pick door (2026-09-18): the fork copied the parent's stored env verbatim except
        the reserved and login names, so a stored credential-shaped name was written into a fresh registry and,
        at the child's first connect, a fresh flag-settings file, by a user gesture (a cut turn, a comment thread)
        no door sees. The copy drops such a name, on its own names-only line (not the reserved drop's, whose words
        would misdescribe it, and with no key: the fork is one gesture, and stubs of _log take none), and the
        parent's registry keeps it (a fact the line states; review round 3, 2026-09-19, sent the remedy away). The
        line's ring text is bounded by construction (FORK_DROP_RING)."""
        os.environ["CLAUDE_CONFIG_DIR"] = tempfile.mkdtemp()   # transcript_path resolves through this
        try:
            self.be.spawn("parent", self.d, sid=PARENT, env=ENV)
            val = _secret_value("notes-token")
            self.be._update_reg(PARENT, env={**ENV, "NOTES_API_TOKEN": val, "op_session_notes": val})
            self.be.fork("child", PARENT, "a1", sid=CHILD)
            self.assertEqual(self._reg(CHILD).get("env"), ENV, "the env inherits less the credential-shaped names")
            kw = self.be._options(self._sess(CHILD), dict)
            self.assertEqual(json.loads(Path(kw["settings"]).read_text())["env"], ENV, "the child's own file is clean")
            for path in self._files_carrying(val):
                self.assertIn(PARENT, path, "the value sits in the parent's files alone: %r" % (path,))
            self.assertTrue(self._files_carrying(val), "the parent's registry still holds it (nothing is cleaned there)")
            rows = [(m, kw2) for m, problem, kw2 in self.logged if problem and "child" in m and "NOTES_API_TOKEN" in m]
            self.assertEqual(len(rows), 1, "one names-only line for the fork: %r" % (self.logged,))
            self.assertIn("op_session_notes", rows[0][0])
            self.assertIn("not copying credential-shaped", rows[0][0])
            self.assertNotIn("reserved", rows[0][0], "not the reserved drop's words")
            self.assertNotIn("key", rows[0][1], "no dedupe key: a fork is one gesture")
            self.assertNotIn("re-declared", rows[0][0], "no remedy is promised")
            self.assertEqual(rows[0][1]["ring_text"], sb.FORK_DROP_RING % ("child", "NOTES_API_TOKEN and 1 more"),
                             "the ring text: the fork's name and the first variable, the rest counted")
            self.assertLessEqual(len(rows[0][1]["ring_text"]), sb.ERROR_CENTER_TEXT_CAP)
            self.assertFalse(any(val in m for m, _p, _k in self.logged), "no log line carries the value")
            self.assertFalse(any(kw2.get("key") == ("env-stored-credential", CHILD) for _m, _p, kw2 in self.logged),
                             "the child's own connect has no stored offender to report")
        finally:
            os.environ.pop("CLAUDE_CONFIG_DIR", None)

    def _real_ring(self):
        """The row as the dashboard reads it: the class stubs _log to capture lines, so the stub goes and the kernel
        log's lines are captured instead (every name whole is the LOG line's promise, the short form's is the cap)."""
        del self.be._log
        self.lines = []
        self.be._log_cb = self.lines.append
        return load_source("romp_kernel", os.path.join(BIN, "romp-kernel"))

    def _repeat_suffix(self, repeats=1, text="probe"):
        """_log's count suffix as the REAL ring renders it after `repeats` repeats of a keyed row whose text is `text`,
        read from the ring rather than spelled here, so a change to that suffix moves the bound this class pins. The
        suffix grows with the count's digits (review round 3, 2026-09-19, extra7-7: the addendum's pin read it at one
        repeat and called the two spare characters a third digit's room, while a third digit in the repeat count costs
        three), so the worst-case pin reads it at a four-digit count."""
        key = ("probe", repeats, text)
        for _ in range(repeats + 1):
            self.be._log(text, problem=True, key=key)
        row = [r for r in self.be.problems() if r.get("key") == key][0]
        self.assertTrue(row["text"].startswith(text + " (%d repeat" % repeats), row["text"][:len(text) + 20])
        return row["text"][len(text):]     # the ring appends the suffix AFTER the whole first text (asserted just above)

    def _stored_row_after_a_repeat(self, session_name, names):
        """A session launched twice with `names` stored under credential-shaped spellings: the keyed row after the ring
        counted the repeat, and the values, which must appear nowhere."""
        sid = self.be.spawn(session_name, "/tmp", env=ENV)
        vals = {n: _secret_value("v%d" % i) for i, n in enumerate(names)}
        self.be._update_reg(sid, env={**ENV, **vals})
        s = self._sess(sid)
        self.be._options(s, dict)
        self.be._options(s, dict)                              # the repeat: the ring counts it on the row, with a suffix
        rows = [r for r in self.be.problems() if r.get("key") == ("env-stored-credential", sid)]
        self.assertEqual(len(rows), 1, "keyed: one row, counted")
        self.assertEqual(rows[0]["count"], 2)
        self.assertIn("repeat", rows[0]["text"], "rendered with the ring's count suffix")
        return rows[0], vals

    STORED_ROW_TAIL = ("launches with it", "value in registry and flag-settings file")   # the fact; no remedy (round 3)

    def test_the_stored_offender_row_fits_the_error_centre_for_one_two_and_twenty_variables(self):
        """regression-1 (review round 2 of the env-pick door, 2026-09-19) and its addendum. The reworded row ran to
        333 characters against the 240-character error-centre cap this PR introduced, so the dashboard clipped it
        mid-parenthesis and lost its tail. Round 2's short form was then pinned at a length two demo names happened to fit,
        and the reviewer showed that the bound was a measurement, not a property: a third stored name, or a longer
        one, clipped the same clause again. The form is bounded by construction now (stored_offender_ring_text: one
        variable named, the rest counted, the session name and the named variable cut to a budget each), and THIS
        test pins the property rather than a length: rendered through the REAL ring (no stub of _log) after a
        repeat, the form a second connect leaves, with the longest 1Password name as the one named, the row fits
        the cap and the feed's cut for one, two and twenty stored variables alike, the tail clause is present in
        every case, the count says how many more, and the kernel log line names every variable whole."""
        km = self._real_ring()
        for count in (1, 2, 20):
            with self.subTest(variables=count):
                names = ["OP_SERVICE_ACCOUNT_TOKEN"] + ["SVC_%02d_API_TOKEN" % i for i in range(count - 1)]   # sorts first
                row, vals = self._stored_row_after_a_repeat("notes-api-web-%02d" % count, names)
                text = row["text"]
                self.assertLessEqual(len(text), sb.ERROR_CENTER_TEXT_CAP, "whole in the error centre: %d characters: %s" % (len(text), text))
                self.assertEqual(km._sdk_problem_text(text), text, "and whole in the feed")
                self.assertIn("OP_SERVICE_ACCOUNT_TOKEN", text, "the first variable in sorted order is named")
                if count > 1:
                    self.assertIn(" and %d more stored" % (count - 1), text, "the rest are a count")
                else:
                    self.assertNotIn("more", text)
                for clause in self.STORED_ROW_TAIL:
                    self.assertIn(clause, text, "the tail is present whatever the count: %s" % text)
                self.assertFalse(any(v in text for v in vals.values()))
                self.assertLessEqual(len(row["first"]), sb.ERROR_CENTER_TEXT_CAP, "the first fire fits too")
                line = [ln for ln in self.lines if "credential-shaped" in ln and "notes-api-web-%02d" % count in ln]
                self.assertEqual(len(line), 2, "one kernel log line per connect: %r" % (self.lines,))
                for n in names:
                    self.assertIn(n, line[0], "the kernel log line names every variable whole")
                self.assertFalse(any(v in ln for v in vals.values() for ln in self.lines))

    def test_the_stored_offender_rows_worst_case_is_computed_from_the_format_and_fits_the_cap(self):
        """The bound as a property of the format (the round-2 addendum, recomputed in review round 3, 2026-09-19: tests-3,
        kernel-7 and extra7-7 found the addendum's pin taking _log's repeat suffix at ONE repeat though it grows with
        the count's digits, 241 against 240 from 100 repeats on, and its "third digit in the count of more" case
        rendering a two-digit count). The worst case the construction allows is computed HERE from the format's own
        pieces: the fixed text, the session budget and the name budget both spent, the count text at its widest
        (credentials.count_text renders "999+" past COUNT_CAP, so the count is bounded by construction too), and the
        suffix as the real ring renders it at a FOUR-digit repeat count. The budgets were set so that sum fits: 120
        + 20 + 24 + 14 + 59 = 237 of 240, and the fixed text is what gave up characters (round 2's read 127). The
        suffix grows a character per digit, so the row fits through a seven-digit repeat count, and past that the
        cut lands inside the suffix, since _log appends it after the whole first text (asserted through the real
        ring at five digits)."""
        km = self._real_ring()
        suffix1 = self._repeat_suffix(1)
        suffix4 = self._repeat_suffix(9999)
        self.assertEqual(len(suffix4), len(suffix1) + 4, "three more digits and the plural: the suffix's only growth")
        fixed = sb.STORED_OFFENDER_RING % ("", "")
        self.assertEqual(fixed.count("%"), 0, "two slots, the session name and the names, and nothing else")
        long_session = "s" * (sb.RING_SESSION_BUDGET + 20)
        long_name = "NOTES_" + "X" * 40 + "_TOKEN"
        count_worst = " and %s more" % sb._cred.count_text(sb._cred.COUNT_CAP + 1)
        self.assertEqual(count_worst, " and 999+ more", "the count text at its widest")
        names = [long_name] + ["ZZ_%04d_TOKEN" % i for i in range(sb._cred.COUNT_CAP + 1)]    # the long one sorts first
        worst = sb.stored_offender_ring_text(long_session, names)
        self.assertEqual(len(worst), len(fixed) + sb.RING_SESSION_BUDGET + sb.RING_NAME_BUDGET + len(count_worst),
                         "both budgets spent, plus the widest count: the format's worst case")
        self.assertIn(count_worst, worst)
        self.assertLessEqual(len(worst) + len(suffix4), sb.ERROR_CENTER_TEXT_CAP,
                             "the worst case fits with the ring's suffix at a four-digit count: %d + %d against %d"
                             % (len(worst), len(suffix4), sb.ERROR_CENTER_TEXT_CAP))
        self.assertEqual(km._sdk_problem_text(worst + suffix4), worst + suffix4, "and whole in the feed")
        for more, text in ((19, " and 19 more"), (119, " and 119 more"), (999, " and 999 more"), (1000, " and 999+ more")):
            row = sb.stored_offender_ring_text(long_session, [long_name] + ["ZZ_%04d_TOKEN" % i for i in range(more)])
            self.assertIn(text, row, "two digits, three digits, the cap and past it")
            self.assertLessEqual(len(row) + len(suffix4), sb.ERROR_CENTER_TEXT_CAP, (more, len(row)))
        for clause in self.STORED_ROW_TAIL:
            self.assertIn(clause, worst)
        # the suffix grows one character per digit of the repeat count (the plural aside), and the ring appends it
        # after the whole first text (_repeat_suffix asserts that through the real ring, here at five digits), so the
        # room left after the worst-case text and the one-repeat suffix is the number of digits the count may grow
        # by before the cut lands, and then it lands inside the suffix, never in the row's own text
        suffix5 = self._repeat_suffix(99999, text=worst)
        self.assertEqual(len(suffix5), len(suffix4) + 1)
        room = sb.ERROR_CENTER_TEXT_CAP - len(worst) - len(suffix1)
        self.assertGreaterEqual(room, 4, "at least a four-digit repeat count fits after the worst-case text; the pin above took exactly that")
        self.assertEqual(room, 7, "the arithmetic the docstring states: 240 - 178 - 55, so a count of up to seven digits fits")
        self.assertEqual(sb.RING_NAME_BUDGET, len("OP_SERVICE_ACCOUNT_TOKEN"),
                         "every 1Password name romp spells EXACTLY is whole under the budget; an OP_SESSION_<account> "
                         "longer than it is cut like any other name (extra7-8, review round 3)")
        self.assertIn("OP_SESSION_" + "a" * 13, sb.stored_offender_ring_text("web", ["OP_SESSION_" + "a" * 13]), "24 characters: whole")
        self.assertIn("OP_SESSION_" + "a" * 12 + sb._cred.CUT_MARK, sb.stored_offender_ring_text("web", ["OP_SESSION_" + "a" * 14]),
                      "25 characters: cut with the marker")
        self.assertEqual(sb.stored_offender_ring_text("web", ["NOTES_API_TOKEN"]),
                         fixed.replace("env ()", "env (web)").replace("credential-shaped  stored", "credential-shaped NOTES_API_TOKEN stored"))
        self.assertIn("credential-shaped NOTES_API_TOKEN and 1 more stored",
                      sb.stored_offender_ring_text("web", ["OP_SERVICE_ACCOUNT_TOKEN", "NOTES_API_TOKEN"]), "two: the first and a count")

    def test_a_variable_or_session_name_past_its_budget_is_cut_with_a_marker_and_the_tail_stays(self):
        """How a very long name is handled (the round-2 addendum, 2026-09-19, which asked for the decision to be
        stated and pinned): the named variable and the session name are each CUT to their budget, the cut marked
        with the feed's own one-character mark, rather than the row naming nothing or the tail going; the kernel
        log line carries both whole. Through the real ring after a repeat, like the rows above."""
        km = self._real_ring()
        long_session = "notes-api-" + "w" * 30                                          # 40 characters, budget 20
        long_name = "NOTES_" + "X" * 40 + "_TOKEN"                                       # 52 characters, budget 24
        row, vals = self._stored_row_after_a_repeat(long_session, [long_name, "ZZ_TOKEN"])
        text = row["text"]
        self.assertLessEqual(len(text), sb.ERROR_CENTER_TEXT_CAP, (len(text), text))
        self.assertEqual(km._sdk_problem_text(text), text)
        cut_name = long_name[:sb.RING_NAME_BUDGET - 1] + sb._cred.CUT_MARK
        cut_session = long_session[:sb.RING_SESSION_BUDGET - 1] + sb._cred.CUT_MARK
        self.assertEqual(len(cut_name), sb.RING_NAME_BUDGET)
        self.assertIn("env (%s): credential-shaped %s and 1 more stored" % (cut_session, cut_name), text)
        self.assertNotIn(long_name, text, "the whole name is the log line's")
        self.assertNotIn(long_session, text)
        for clause in self.STORED_ROW_TAIL:
            self.assertIn(clause, text, "the tail stays when the names are cut: %s" % text)
        self.assertFalse(any(v in text for v in vals.values()))
        line = [ln for ln in self.lines if long_name in ln]
        self.assertEqual(len(line), 2, "the kernel log line carries the whole name at each connect")
        self.assertIn(long_session, line[0])
        self.assertIn("ZZ_TOKEN", line[0])
        self.assertNotIn(sb._cred.CUT_MARK, line[0], "nothing is cut on the log line")
        self.assertEqual(sb._cred.cut_to("short", 24), "short", "a name within its budget is whole, unmarked")

    def test_the_refusal_row_is_headed_once_and_its_ring_text_is_the_bounded_form(self):
        """Review round 1 of the env-pick door (2026-09-18): the set_env line read "pick refused: env: ..." and its
        ring text, then the whole line, ran to 414 characters and was clipped mid-word. The line carries the door's
        head once and every name whole (nothing caps the kernel log line; review round 3, 2026-09-19, corrected the
        docstrings that claimed the feed's cap governed it), and the ring text is the bounded form: set_env's head
        with the session name cut to its budget, then credentials.credential_env_ring_text. Any other refusal's body
        quotes the offending name, which nothing bounds, so the ring cuts it to what the cap leaves after the head."""
        sid = self.be.spawn("web", "/tmp", env=ENV)
        val = _secret_value("notes-token")
        self.assertFalse(self.be.set_env(sid, {**PLAIN, "NOTES_API_TOKEN": val}))
        rows = [(m, kw) for m, problem, kw in self.logged if problem and "pick refused" in m]
        self.assertEqual(len(rows), 1, self.logged)
        line, kw = rows[0]
        self.assertTrue(line.startswith("env (web): pick refused: NOTES_API_TOKEN is credential-shaped"), line)
        self.assertNotIn("refused: env:", line, "the door's own head is not repeated")
        self.assertEqual(line.count("env ("), 1)
        self.assertNotIn("env: ", line, "the door's head appears nowhere in the line")
        self.assertEqual(line, "env (web): pick refused: " + sb._cred.credential_env_refusal(["NOTES_API_TOKEN"]),
                         "the whole sentence on the kernel log line")
        ring = kw.get("ring_text")
        self.assertEqual(ring, sb.REFUSAL_RING_HEAD % "web" + sb._cred.credential_env_ring_text(["NOTES_API_TOKEN"]))
        self.assertTrue(ring.startswith("env (web): pick refused: NOTES_API_TOKEN is credential-shaped: the pick was not saved"), ring)
        self.assertIn("process environment", ring)
        self.assertNotIn(val, line)
        self.assertNotIn(val, ring)
        # another refusal shape keeps its own words, headed once; short, it rides the ring whole
        self.assertFalse(self.be.set_env(sid, {"9BAD": "1"}))
        bad = [(m, kw) for m, problem, kw in self.logged if problem and "9BAD" in m]
        self.assertEqual(len(bad), 1)
        self.assertTrue(bad[0][0].startswith("env (web): pick refused: bad name"), bad[0][0])
        self.assertEqual(bad[0][1].get("ring_text"), bad[0][0])
        # a body that quotes a long offending name is cut to what the cap leaves after the head, marked
        huge = "9" + "B" * 400
        self.assertFalse(self.be.set_env(sid, {huge: "1"}))
        hb = [(m, kw) for m, problem, kw in self.logged if problem and huge in m]
        self.assertEqual(len(hb), 1, "the kernel log line carries the whole name")
        ring = hb[0][1]["ring_text"]
        self.assertEqual(len(ring), sb.ERROR_CENTER_TEXT_CAP)
        self.assertTrue(ring.endswith(sb._cred.CUT_MARK) and ring.startswith("env (web): pick refused: bad name"), ring)
        # the 1Password half hears its own road (review round 2, 2026-09-19): the process environment refuses such a
        # name at boot, so the advice that took the deployment down is not given
        self.assertFalse(self.be.set_env(sid, {"OP_SERVICE_ACCOUNT_TOKEN": _secret_value("op")}))
        op_rows = [(m, kw) for m, problem, kw in self.logged if problem and "OP_SERVICE_ACCOUNT_TOKEN" in m]
        self.assertEqual(len(op_rows), 1, self.logged)
        line, kw = op_rows[0]
        self.assertIn("refuses a 1Password name in its process environment at boot", line)
        self.assertIn("its own file", line)
        self.assertNotIn("Put such a value in the process environment", line)
        self.assertTrue(kw["ring_text"].endswith(sb._cred.CREDENTIAL_RING_ROADS["op"]), kw["ring_text"])

    def test_the_refusal_rings_worst_case_is_computed_from_the_format_and_fits_the_cap(self):
        """regression-2, extra6-3, extra7-3 and tests-2 (review round 3 of the env-pick door, 2026-09-19): the refusal
        row's two cap pins were measurements taken with the session name "web", and the form joined every refused
        name whole behind the whole session name, so an ordinary session name, six names, or one long name pushed the
        ring text past the error centre's cap and around eleven names the cut landed inside the name list. The
        construction: set_env's head cuts the session name (or the sid a nameless registry falls back to) to
        RING_SESSION_BUDGET; credential_env_ring_text names the first variable cut to RING_NAME_BUDGET, counts the rest
        through the bounded count text, and appends the road of the half matched. The worst case, both budgets and
        the widest count spent under the longest road (the mixed pick's), is computed here from those pieces and
        asserted under the cap; then the real set_env is driven to that worst case, and to one, two and twenty names,
        a session name past its budget, and the sid fallback, each rendered form under the cap with its tail present.
        The kernel log line carries every name and the whole session name."""
        km = load_source("romp_kernel", os.path.join(BIN, "romp-kernel"))
        cap = sb.ERROR_CENTER_TEXT_CAP
        road = max(sb._cred.CREDENTIAL_RING_ROADS.values(), key=len)
        self.assertEqual(road, sb._cred.CREDENTIAL_RING_ROADS["mixed"], "the mixed pick hears the longest road")
        count_worst = sb._cred.count_text(sb._cred.COUNT_CAP + 1)
        names_worst = "%s and %s more" % ("x" * sb.RING_NAME_BUDGET, count_worst)
        worst = (sb.REFUSAL_RING_HEAD % ("x" * sb.RING_SESSION_BUDGET)) + sb._cred.CREDENTIAL_RING_FORMAT % (names_worst, "are", road)
        self.assertLessEqual(len(worst), cap, "the format's worst case fits: %d against %d" % (len(worst), cap))
        self.assertEqual(km._sdk_problem_text(worst), worst, "and whole in the feed")
        for other in ("op", "suffix"):
            self.assertLess(len(sb._cred.CREDENTIAL_RING_ROADS[other]), len(road))
        # the real row at the worst case: a session name past its budget, a first name past its budget, a thousand
        # more names of both halves (the mixed road), every value built at run time and in no line
        long_session = "notes-api-" + "w" * 30                                      # 40 characters, budget 20
        long_name = "NOTES_" + "X" * 40 + "_TOKEN"                                   # 52 characters, budget 24; sorts first
        sid = self.be.spawn(long_session, "/tmp", env=ENV)
        val = _secret_value("notes-token")
        pick = {long_name: val, "op_session_notes": val, **{"ZZ_%04d_TOKEN" % i: val for i in range(sb._cred.COUNT_CAP)}}
        self.assertEqual(len(pick), sb._cred.COUNT_CAP + 2)
        self.assertFalse(self.be.set_env(sid, pick))
        rows = [(m, kw) for m, problem, kw in self.logged if problem and "pick refused" in m]
        self.assertEqual(len(rows), 1, len(self.logged))
        line, kw = rows[0]
        ring = kw["ring_text"]
        self.assertEqual(len(ring), len(worst), "both budgets and the widest count spent: the format's worst case, through the real row")
        self.assertTrue(ring.startswith(sb.REFUSAL_RING_HEAD % sb._cred.cut_to(long_session, sb.RING_SESSION_BUDGET)), ring)
        self.assertIn(sb._cred.cut_to(long_name, sb.RING_NAME_BUDGET) + " and %s more are credential-shaped: the pick was not saved. " % count_worst, ring)
        self.assertTrue(ring.endswith(road), "the mixed road, whole, at the tail")
        self.assertIn(long_session, line, "the kernel log line carries the whole session name")
        for n in (long_name, "op_session_notes", "ZZ_0000_TOKEN", "ZZ_%04d_TOKEN" % (sb._cred.COUNT_CAP - 1)):
            self.assertIn(n, line, "and every name whole")
        self.assertNotIn(val, line)
        self.assertNotIn(val, ring)
        self.logged.clear()
        # one, two and twenty names of one half, through the real row: the count, the tail, the cap
        sid2 = self.be.spawn("web", "/tmp", env=ENV)
        for count in (1, 2, 20):
            with self.subTest(names=count):
                self.logged.clear()
                self.assertFalse(self.be.set_env(sid2, {"SVC_%02d_API_TOKEN" % i: val for i in range(count)}))
                rows = [(m, kw) for m, problem, kw in self.logged if problem and "pick refused" in m]
                self.assertEqual(len(rows), 1)
                ring = rows[0][1]["ring_text"]
                self.assertLessEqual(len(ring), cap, (count, len(ring), ring))
                self.assertEqual(km._sdk_problem_text(ring), ring)
                self.assertTrue(ring.startswith("env (web): pick refused: SVC_00_API_TOKEN"), ring)
                if count > 1:
                    self.assertIn(" and %d more are credential-shaped" % (count - 1), ring)
                else:
                    self.assertIn("SVC_00_API_TOKEN is credential-shaped", ring)
                self.assertIn("the pick was not saved", ring)
                self.assertTrue(ring.endswith(sb._cred.CREDENTIAL_RING_ROADS["suffix"]), ring)
                for i in range(count):
                    self.assertIn("SVC_%02d_API_TOKEN" % i, rows[0][0], "every name on the log line")
                self.assertNotIn(val, rows[0][0])
        # the sid fallback of a nameless registry: the head cuts the 36-character sid to the session budget
        self.logged.clear()
        self.be._update_reg(sid2, name="")
        self.assertFalse(self.be.set_env(sid2, {"NOTES_API_TOKEN": val}))
        rows = [(m, kw) for m, problem, kw in self.logged if problem and "pick refused" in m]
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0][0].startswith("env (%s): pick refused: " % sid2), "the log line carries the whole sid")
        self.assertTrue(rows[0][1]["ring_text"].startswith(sb.REFUSAL_RING_HEAD % sb._cred.cut_to(sid2, sb.RING_SESSION_BUDGET)),
                        rows[0][1]["ring_text"])
        self.assertLessEqual(len(rows[0][1]["ring_text"]), cap)

    def test_the_error_centre_cap_is_the_badge_mirrors_literal(self):
        ts = Path(os.path.dirname(HERE), "ui", "webview", "badge-mirror.ts").read_text()
        # the SDK problem row's own function, sliced (review round 2, 2026-09-19: the same literal caps the unrelated
        # sync-notices row in this file, so a whole-file assertIn stayed green when the SDK row's cap alone changed);
        # str.index raises when a marker is gone, so a rename fails loudly instead of slicing nothing
        start = ts.index("export function sdkProblemNotices")
        end = ts.index("export function", start + 1)
        body = ts[start:end]
        self.assertIn("cap(r.text, %d)" % sb.ERROR_CENTER_TEXT_CAP, body,
                      "the constant mirrors the cut the dashboard's error centre applies to an SDK problem row")
        self.assertEqual(body.count("cap(r.text, "), 1, "one cut in that function, the one the constant mirrors")
        km = load_source("romp_kernel", os.path.join(BIN, "romp-kernel"))
        self.assertEqual(km._sdk_problem_text.__defaults__, (km.SDK_PROBLEM_TEXT_CAP,), "the feed's cut is the constant")
