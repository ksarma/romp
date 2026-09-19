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
    fastMode, and the return-""-when-no-keys contract stands; with no key riding it also REMOVES
    the file an earlier connect left (review round 1 of the env-pick door, 2026-09-18). It refuses
    a sid that is not a bare file name and a path that is a symbolic link, and shares one lock
    with flag_settings_sync_env (review round 2, 2026-09-19).
  * flag_settings_sync_env brings the file's env block in line with the registry at the WRITE
    (set_env), on write_reg's temp-and-rename pattern, and when it cannot rewrite the file it
    removes it, and when it cannot remove it either it refuses, so the registry keeps naming the
    offender (review round 2, 2026-09-19).
  * _options threads the session's env into that file at EVERY connect — the file is rewritten on
    each use, so reconnects re-assert the reg's env by construction (pinned by tampering the file
    between two _options calls), and reads the env again under the writers' lock at the write, so
    a redaction landing mid-compose is what launches. Its stored-offender row has a short form for
    the error centre that is bounded by construction (one variable named, the rest counted, the
    session name and the named variable cut to a budget each; the round-2 addendum, 2026-09-19),
    pinned as a property through the real ring for one, two and twenty variables.
  * set_env mirrors set_effort's shape (persist + reconnect to apply; env is connect-time), minus
    the badge/chip machinery that belongs to the not-yet-built UI slice; an UNCHANGED re-assert
    (the `romp new --env` re-brief on a standing session, or the fresh-spawn echo) skips the
    reconnect, since the asked-for env is already in force or already queued; a redaction whose file can
    neither be rewritten nor removed is refused rather than reported done.
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
import threading
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
    """The module's `os` with one or two functions interposed and everything else forwarded: `replace` runs a hook
    in place of os.replace (a forced failure, or a step that runs another writer first), `unlink` raises for ONE
    path and forwards for every other (so a writer's finally-unlink of its temp still runs). Rebound as sb.os for a
    test's duration, since the module's functions read `os` from their globals; restored by addCleanup. Round 2's
    reviewers forced the writers' interleaves this way, deterministically, rather than by timing."""

    def __init__(self, real, replace=None, unlink=None):
        self._real, self._replace, self._unlink = real, replace, unlink

    def __getattr__(self, name):
        return getattr(self._real, name)

    def replace(self, src, dst):
        if self._replace is not None and sb.FLAG_SETTINGS_DIR in str(dst):   # the flag-settings writer's rename only:
            return self._replace(self._real, src, dst)                        #  write_reg's goes through this os too
        return self._real.replace(src, dst)

    def unlink(self, path, *a, **k):
        if self._unlink is not None and str(path) == self._unlink[0]:
            raise self._unlink[1]
        return self._real.unlink(path, *a, **k)


def _interpose(test, **kw):
    real = sb.os
    test.addCleanup(setattr, sb, "os", real)
    sb.os = _OsProxy(real, **kw)
    return real


def _enospc(real, src, dst):
    """A rename that fails the way a full disk fails it: the shape of the ladder's first rung."""
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
                                  log=lambda msg, problem=False: logged.append((msg, problem)))
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

    def test_no_keys_removes_the_file_an_earlier_connect_left(self):
        """Review round 1 of the env-pick door (2026-09-18), the round's one high finding: with no key riding the
        writer returned "" and left the previous connect's file, and with it the env block that connect launched
        with, on disk for good, so a per-session env redacted to the empty set stayed in this file while the
        registry said it was gone. The stale file goes; the "" contract stands; nothing is said (the common case)."""
        p = sb.flag_settings_path(self.d, PARENT, env={"FEATURE_FLAG": "1"})
        self.assertTrue(Path(p).exists())
        logged = []
        self.assertEqual(sb.flag_settings_path(self.d, PARENT, log=lambda *a, **k: logged.append(a)), "")
        self.assertFalse(Path(p).exists(), "the stale per-session file is removed, not left with its env block")
        self.assertEqual(logged, [], "a removal that worked is not a problem row")
        self.assertEqual(sb.flag_settings_path(self.d, PARENT), "", "and a second call finds nothing to remove")
        self.assertFalse(Path(self.d, sb.FLAG_SETTINGS_DIR, "%s.json" % CHILD).exists(),
                         "a session that never had a file gets none")

    def test_a_stale_file_that_cannot_be_removed_is_a_problem_row(self):
        # a DIRECTORY where the per-sid file goes: unlink raises an OSError that is not a missing file
        Path(self.d, sb.FLAG_SETTINGS_DIR, "%s.json" % PARENT).mkdir(parents=True)
        logged = []
        self.assertEqual(sb.flag_settings_path(self.d, PARENT, log=lambda msg, problem=False, **kw: logged.append((msg, problem, kw))), "")
        self.assertEqual(len(logged), 1, "the file may still carry an earlier launch's env: said, as the write branch says its drop")
        self.assertTrue(logged[0][1])
        self.assertIn(PARENT, logged[0][0])
        self.assertIn("could not be removed", logged[0][0])
        ring = logged[0][2].get("ring_text")
        self.assertTrue(ring and "could not be removed" in ring and PARENT in ring, logged[0][2])
        self.assertLessEqual(len(ring), sb.ERROR_CENTER_TEXT_CAP, "the error centre's short form (review round 2, 2026-09-19)")
        self.assertEqual(sb.flag_settings_path(self.d, PARENT), "", "log=None neither raises nor changes the contract")


class FlagSettingsSyncEnv(unittest.TestCase):
    """flag_settings_sync_env (review round 1 of the env-pick door, 2026-09-18): the per-sid file's env block follows
    the registry at the WRITE, for the session that never connects again. The other keys stay as the last connect
    wrote them; with nothing left the file goes; a missing file is nothing to do. Since review round 2 (2026-09-19)
    it answers whether the file follows the env, writes on write_reg's pattern (a writer-unique temp, renamed into
    place, unlinked in a finally), climbs the reviewers' ladder when the rewrite fails (remove the file; only if
    that fails too, refuse), and shares one lock with the connect's writer."""

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.p = Path(self.d, sb.FLAG_SETTINGS_DIR, "%s.json" % PARENT)

    def _read(self):
        return json.loads(self.p.read_text())

    def _log(self):
        logged = []
        return logged, (lambda msg, problem=False, **kw: logged.append((msg, problem, kw)))

    def test_a_missing_file_is_nothing_to_do_and_none_is_created(self):
        self.assertTrue(sb.flag_settings_sync_env(self.d, PARENT, ENV), "nothing on disk: the file follows the env trivially")
        self.assertFalse(Path(self.d, sb.FLAG_SETTINGS_DIR).exists(), "no directory, no file: the next connect writes what it needs")
        Path(self.d, sb.FLAG_SETTINGS_DIR).write_text("not a directory")
        self.assertTrue(sb.flag_settings_sync_env(self.d, PARENT, {}))    # a plain file where the directory goes is no file either

    def test_the_env_block_is_replaced_and_the_other_keys_stay(self):
        import stat
        sb.flag_settings_path(self.d, PARENT, fast=True, no_helper=True, env={"FEATURE_FLAG": "1", "OLD_FLAG": "x"})
        before = os.stat(self.p)
        self.assertTrue(sb.flag_settings_sync_env(self.d, PARENT, ENV), "the verdict: the file follows the env")
        after = os.stat(self.p)
        self.assertEqual(self._read(), {"fastMode": True, "apiKeyHelper": "", "env": ENV})
        self.assertEqual(stat.S_IMODE(after.st_mode), 0o600, "0600, the writer's own treatment")
        self.assertNotEqual(after.st_ino, before.st_ino,
                            "written to a sibling and renamed into place, so a new inode (review round 2, 2026-09-19: the "
                            "no-temp-left check alone was satisfied by a writer that made no temp at all)")
        self.assertEqual(_temps(self.d), [], "no temp left beside the file")

    def test_an_empty_env_drops_the_block_and_an_empty_file_goes(self):
        sb.flag_settings_path(self.d, PARENT, ultracode=True, env=ENV)
        self.assertTrue(sb.flag_settings_sync_env(self.d, PARENT, {}))
        self.assertEqual(self._read(), {"ultracode": True}, "the block goes, the key that still rides stays")
        sb.flag_settings_path(self.d, PARENT, env=ENV)
        self.assertTrue(sb.flag_settings_sync_env(self.d, PARENT, None))
        self.assertFalse(self.p.exists(), "nothing rides: the file goes rather than staying as {}")

    def test_an_unparsable_file_is_replaced_by_what_is_known(self):
        self.p.parent.mkdir(parents=True)
        self.p.write_text("{not json")
        self.assertTrue(sb.flag_settings_sync_env(self.d, PARENT, ENV))
        self.assertEqual(self._read(), {"env": ENV})
        self.p.write_text("{not json")
        self.assertTrue(sb.flag_settings_sync_env(self.d, PARENT, {}))
        self.assertFalse(self.p.exists())

    def test_a_directory_where_the_file_goes_fails_both_rungs_and_refuses(self):
        # a directory where the file goes: the rename over it fails, and so does the removal (the last rung)
        self.p.mkdir(parents=True)
        logged, log = self._log()
        self.assertFalse(sb.flag_settings_sync_env(self.d, PARENT, ENV, log=log),
                         "neither rewritten nor removed: refused, so the registry keeps naming what the file carries")
        self.assertEqual(len(logged), 1)
        self.assertTrue(logged[0][1])
        self.assertIn(PARENT, logged[0][0])
        self.assertIn("nor removed", logged[0][0])
        self.assertIn("refused", logged[0][0])
        self.assertEqual(_temps(self.d), [], "the temp of the failed rewrite is gone (write_reg's finally)")
        self.assertFalse(sb.flag_settings_sync_env(self.d, PARENT, {}), "the remove road alone fails the same way")
        self.assertFalse(sb.flag_settings_sync_env(self.d, PARENT, ENV))    # log=None: quiet, no raise

    def test_a_forced_rename_failure_leaves_no_temp_and_the_temp_is_writer_unique(self):
        """kernel-2, regression-4, regression-5 (review round 2, 2026-09-19): the first cut wrote through a FIXED
        <sid>.json.tmp shared by every caller for the sid and never removed it on failure, against write_reg's
        recorded 2026-07-06 lesson in this very module; the reviewers reproduced a stolen temp (a torn live file) and
        an orphan holding the env block that the reference's lister, which globs *.json, cannot see. Now the temp
        name carries the pid and a random suffix, and a failed rename leaves none. The rename failing on a writable
        directory is also the ladder's first rung: the file is removed instead and the verdict is True."""
        sb.flag_settings_path(self.d, PARENT, fast=True, env={"OLD_FLAG": "x"})
        seen = []

        def boom(real, src, dst):
            seen.append(os.path.basename(src))
            raise OSError(errno.ENOSPC, "No space left on device")
        _interpose(self, replace=boom)
        logged, log = self._log()
        self.assertTrue(sb.flag_settings_sync_env(self.d, PARENT, ENV, log=log),
                        "the first rung: the file could not be rewritten, so it was removed, and the redaction stands")
        self.assertFalse(self.p.exists(), "removed rather than left with the old block")
        self.assertEqual(_temps(self.d), [], "a failed rename leaves no temp behind")
        self.assertEqual(len(seen), 1)
        self.assertRegex(seen[0], r"^%s\.json\.%d\.[0-9a-f]{8}\.tmp$" % (re.escape(PARENT), os.getpid()),
                         "writer-unique: the pid and a random suffix, write_reg's name")
        rows = [(m, kw) for m, problem, kw in logged if problem]
        self.assertEqual(len(rows), 1, logged)
        self.assertIn("removed instead", rows[0][0])
        self.assertIn(str(self.p), rows[0][0])
        self.assertLessEqual(len(rows[0][1]["ring_text"]), sb.ERROR_CENTER_TEXT_CAP)

    def test_a_rename_failure_whose_removal_also_fails_refuses_and_keeps_the_file(self):
        # the second rung by an interposed unlink that raises for the file alone (the temp's finally-unlink still runs)
        sb.flag_settings_path(self.d, PARENT, env={"OLD_FLAG": "x"})
        _interpose(self, replace=_enospc, unlink=(str(self.p), PermissionError(errno.EPERM, "Operation not permitted")))
        logged, log = self._log()
        self.assertFalse(sb.flag_settings_sync_env(self.d, PARENT, ENV, log=log), "refused: the file still carries what it carried")
        self.assertEqual(self._read(), {"env": {"OLD_FLAG": "x"}}, "the honest state, kept and said")
        self.assertEqual(_temps(self.d), [], "and still no temp is left")
        rows = [(m, kw) for m, problem, kw in logged if problem]
        self.assertEqual(len(rows), 1, logged)
        self.assertIn("nor removed", rows[0][0])
        self.assertIn("refused", rows[0][0])
        self.assertIn(str(self.p), rows[0][0])
        self.assertLessEqual(len(rows[0][1]["ring_text"]), sb.ERROR_CENTER_TEXT_CAP)

    def _other_writer_during(self, other):
        """A sync whose rename first starts `other` (a second writer) on a thread and gives it two seconds: under the
        writers' lock it cannot finish while this writer holds the lock, so the wait ends with it still running, and
        it finishes once this writer returns. Records whether it finished DURING the rename."""
        state = {"during": None}
        th = threading.Thread(target=other)

        def hook(real, src, dst):
            if state["during"] is None:               # once: the proxy is module-wide, so the other writer's own rename lands here too
                th.start()
                th.join(2.0)
                state["during"] = not th.is_alive()
            return real.replace(src, dst)
        _interpose(self, replace=hook)
        return state, th

    def test_a_connect_writing_during_a_sync_waits_for_it_and_its_keys_survive(self):
        """correctness-1 / extra6-1 (review round 2, 2026-09-19): the sync was an unlocked read-modify-write of a file
        the connect also writes whole, so a connect landing between the sync's read and its rename had its keys
        (apiKeyHelper, fastMode, ultracode) dropped by the rename; the reviewers hit it in about a third of natural
        collisions and forced it exactly this way. One lock around both writers: the connect waits, then writes."""
        sb.flag_settings_path(self.d, PARENT, env={"OLD_FLAG": "x"})
        state, th = self._other_writer_during(
            lambda: sb.flag_settings_path(self.d, PARENT, ultracode=True, fast=True, no_helper=True, env=ENV))
        self.assertTrue(sb.flag_settings_sync_env(self.d, PARENT, {"FEATURE_FLAG": "0"}))
        th.join(30)
        self.assertFalse(th.is_alive(), "the connect's write finishes once the sync releases the lock")
        self.assertIs(state["during"], False, "the connect's write waited for the sync rather than landing under its rename")
        self.assertEqual(self._read(), {"ultracode": True, "fastMode": True, "apiKeyHelper": "", "env": ENV},
                         "the connect's whole file stands: the sync dropped none of its keys")
        self.assertEqual(_temps(self.d), [])

    def test_two_syncs_for_one_sid_take_turns_and_the_file_parses(self):
        # regression-5 / extra6-2: two picks for one sid write in turn; neither shares a temp nor tears the file
        sb.flag_settings_path(self.d, PARENT, fast=True, env={"OLD_FLAG": "x"})
        state, th = self._other_writer_during(lambda: sb.flag_settings_sync_env(self.d, PARENT, {"SECOND": "2"}))
        self.assertTrue(sb.flag_settings_sync_env(self.d, PARENT, ENV))
        th.join(30)
        self.assertFalse(th.is_alive())
        self.assertIs(state["during"], False, "the second pick waited for the first's lock")
        self.assertEqual(self._read(), {"fastMode": True, "env": {"SECOND": "2"}},
                         "the later writer's block, whole (last-writer-wins between two picks is the stated residual)")
        self.assertEqual(_temps(self.d), [])


class FlagSettingsSidAndLink(unittest.TestCase):
    """Two refusals ahead of every branch of both writers (review round 2 of the env-pick door, 2026-09-19): a sid
    that is not a bare file name (rules-2 / kernel-4: round 1's unlink made a crafted sid's path traversal destructive
    where the function had only written) and a path that is a symbolic link (extra5-2: the write road put the env
    block into the link's target and the unlink road removed the link and left the block there). Each refusal is a
    problem row naming its reason, and nothing outside the directory is touched."""

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
        self.assertEqual(sb.flag_settings_path(self.d, sid, log=log), "", "the unlink road")
        self.assertFalse(sb.flag_settings_sync_env(self.d, sid, ENV, log=log), "the rewrite road")
        self.assertFalse(sb.flag_settings_sync_env(self.d, sid, {}, log=log), "the remove road")
        self.assertEqual(json.loads(victim.read_text()), {"env": {"KEEP": "me"}}, "the victim's bytes are untouched")
        self.assertEqual(victim.stat().st_mtime_ns, st.st_mtime_ns, "and it was not rewritten in place either")
        self.assertEqual(len(logged), 4, logged)
        for m, problem, _kw in logged:
            self.assertTrue(problem)
            self.assertIn("not a bare file name", m, "the refusal names the specific reason")
            self.assertIn(repr(sid), m)
        self.assertIn("launching WITHOUT env", logged[0][0], "the write road says what the launch goes without")
        for bad in ("..", ".", "", None, "a\0b", "x/y", 7):
            self.assertEqual(sb.flag_settings_path(self.d, bad, env=ENV), "", repr(bad))
            self.assertFalse(sb.flag_settings_sync_env(self.d, bad, ENV), repr(bad))
        self.assertEqual(os.listdir(os.path.join(self.d, sb.FLAG_SETTINGS_DIR)), [], "nothing was written under the directory either")
        self.assertEqual(sb._flag_settings_sid_error(PARENT), "", "a kernel-minted uuid passes")
        self.assertTrue(sb.flag_settings_path(self.d, PARENT, env=ENV), "and writes as before")

    def test_a_symbolic_link_is_refused_on_every_road(self):
        import stat
        target = Path(self.root, "outside.json")
        target.write_text(json.dumps({"env": {"OUTSIDE": "kept"}}) + "\n")
        os.chmod(target, 0o644)
        p = Path(self.d, sb.FLAG_SETTINGS_DIR, PARENT + ".json")
        os.symlink(str(target), str(p))
        logged, log = self._log()
        self.assertEqual(sb.flag_settings_path(self.d, PARENT, env=ENV, fast=True, log=log), "", "the write road")
        self.assertEqual(sb.flag_settings_path(self.d, PARENT, log=log), "", "the unlink road")
        self.assertFalse(sb.flag_settings_sync_env(self.d, PARENT, ENV, log=log), "the rewrite road")
        self.assertFalse(sb.flag_settings_sync_env(self.d, PARENT, {}, log=log), "the remove road")
        self.assertTrue(os.path.islink(p), "the link is left in place")
        self.assertEqual(json.loads(target.read_text()), {"env": {"OUTSIDE": "kept"}}, "the target's bytes are untouched")
        self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o644, "and its mode (the write road used to chmod through the link)")
        self.assertEqual(len(logged), 4, logged)
        for m, problem, _kw in logged:
            self.assertTrue(problem)
            self.assertIn(str(p), m, "the row names the path")
            self.assertIn("symbolic link", m)
            self.assertIn(str(target), m, "and where the link points")
        self.assertEqual(_temps(self.d), [])

    def test_the_failure_rows_short_forms_fit_the_error_centre_whatever_the_state_root(self):
        """extra7-3 (review round 2, 2026-09-19): the sync's failure row ran to 409 characters with a real state
        path, past the feed's cap, and the error centre's cut landed inside the errno path before the row said
        what the file may still carry; the PR's own pin measured 381 over tempfile's short root. Each failure row
        of the two writers has a short form that names no path, measured here over a root longer than any home."""
        km = load_source("romp_kernel", os.path.join(BIN, "romp-kernel"))
        long_root = os.path.join(self.root, "a" * 120)
        d = os.path.join(long_root, sb.FLAG_SETTINGS_DIR)
        os.makedirs(d)
        p = Path(d, PARENT + ".json")
        p.mkdir()                                                    # both rungs fail, and so does the stale removal
        logged, log = self._log()
        self.assertFalse(sb.flag_settings_sync_env(long_root, PARENT, ENV, log=log))
        self.assertEqual(sb.flag_settings_path(long_root, PARENT, log=log), "")
        p.rmdir()
        p.write_text(json.dumps({"env": {"OLD_FLAG": "x"}}) + "\n")
        _interpose(self, replace=_enospc)                            # the first rung on a writable directory
        self.assertTrue(sb.flag_settings_sync_env(long_root, PARENT, ENV, log=log))
        self.assertEqual(len(logged), 3, logged)
        for m, problem, kw in logged:
            self.assertTrue(problem)
            self.assertIn(str(p), m, "the kernel log line names the path")
            self.assertGreater(len(m), sb.ERROR_CENTER_TEXT_CAP, "the whole line would not fit the error centre over this root")
            ring = kw.get("ring_text")
            self.assertTrue(ring and PARENT in ring, kw)
            self.assertLessEqual(len(ring), sb.ERROR_CENTER_TEXT_CAP, ring)
            self.assertLessEqual(len(ring), km.SDK_PROBLEM_TEXT_CAP)
            self.assertEqual(km._sdk_problem_text(ring), ring, "and the feed's cut leaves it whole")
            self.assertNotIn(long_root, ring, "no path in the short form: a path's length is the state root's")


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
        self.be._log = lambda msg, problem=False: logged.append((msg, problem))
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
        the helper's own, or the session's shells); a mixed pick hears both, each scoped. Both forms fit their caps
        for one name of each half and for a mixed pair, and the boot check is executed here so the two sentences
        cannot drift apart from what it refuses."""
        km = load_source("romp_kernel", os.path.join(BIN, "romp-kernel"))
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
        for names in (["NOTES_API_TOKEN"], ["OP_ACCOUNT"], ["OP_SERVICE_ACCOUNT_TOKEN"], ["NOTES_API_TOKEN", "op_session_notes"],
                      ["NOTES_API_TOKEN", "OP_SERVICE_ACCOUNT_TOKEN"]):    # a mixed pair with the longest name of each half
            line = "env (web): pick refused: " + sb._cred.credential_env_refusal(names)
            ring = "env (web): pick refused: " + sb._cred.credential_env_ring_text(names)
            self.assertLessEqual(len(line), km.SDK_PROBLEM_TEXT_CAP, (len(line), names))
            self.assertLessEqual(len(ring), sb.ERROR_CENTER_TEXT_CAP, (len(ring), names))
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
        self.assertIn("romp new --env", rows[0][0], "the line says how to redact")
        self.assertIn("flag-settings file", rows[0][0],
                      "and says the redaction reaches the file too (review round 1, 2026-09-18: the first wording "
                      "promised a redaction that left the value in that file)")
        self.assertEqual(rows[0][1].get("key"), ("env-stored-credential", sid), "keyed per session: the ring dedupes")
        self.assertFalse(any(val in m for m, _p, _k in self.logged))
        self.assertTrue(self.be.set_env(sid, dict(ENV)), "the redaction re-declares the env without the name")
        self.assertEqual(self._reg(sid)["env"], ENV)

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

    def _stored_offender(self, name="NOTES_API_TOKEN"):
        """A live session launched with a stored credential-shaped name (a pick accepted before the door refused it):
        the registry and the flag-settings file both carry the value."""
        sid = self.be.spawn("web", "/tmp", env=ENV)
        val = _secret_value("notes-token")
        self.be._update_reg(sid, env={**ENV, name: val})
        s = self._live(sid)
        self.be._options(s, dict)
        self.assertIn(val, self._flag_file(sid).read_text(), "the launch wrote the value: the state under test")
        return sid, s, val

    def test_redacting_to_the_empty_env_removes_the_value_from_every_file_under_the_state_root(self):
        """The round's one HIGH finding (review round 1 of the env-pick door, 2026-09-18): the reference named
        `romp new --no-env` as a redaction road, and that road cleared the registry and the launch while the
        per-session flag-settings file kept the value, because the writer returned "" without unlinking when no
        key rode and nothing removed the file; and the stored-offender line, which reads the registry, fell
        silent, so the value stayed on disk and the warning went away. Now the write itself brings the file in
        line (flag_settings_sync_env) and a connect that needs no key removes a stale one (flag_settings_path).
        Pinned by execution over a walk of the whole state root, at the write and after the connect."""
        sid, s, val = self._stored_offender()
        self.assertTrue(self.be.set_env(sid, {}), "the redaction road the reference names")
        self.assertEqual(self._reg(sid)["env"], {})
        self.assertEqual(self._files_carrying(val), [], "gone at the write itself, before any connect")
        self.assertFalse(self._flag_file(sid).exists(), "no key rides this session: the file goes")
        kw = self.be._options(s, dict)                          # the connect the redaction applies by
        self.assertNotIn("settings", kw)
        self.assertEqual(self._files_carrying(val), [], "and no file under the state root carries the value after it")
        self.assertFalse(self._flag_file(sid).exists())
        self.assertFalse(any(val in m for m, _p, _k in self.logged), "no log line carries the value")

    def test_re_declaring_the_env_without_the_name_rewrites_the_file_at_the_write(self):
        # the other redaction road, `romp new --env` with the rest of the set: the file follows the registry at
        # the write, so a session that never connects again is clean too
        sid, s, val = self._stored_offender()
        self.assertTrue(self.be.set_env(sid, dict(ENV)))
        self.assertEqual(json.loads(self._flag_file(sid).read_text())["env"], ENV, "the file's block follows the registry")
        self.assertEqual(self._files_carrying(val), [], "the value is in no file under the state root at the write")
        self.be._options(s, dict)
        self.assertEqual(self._files_carrying(val), [])

    def test_a_dormant_sessions_redaction_needs_no_connect(self):
        """A registry with no live process never reconnects: until review round 1 (2026-09-18) its flag-settings file
        kept the redacted value for good. The write is what redacts it."""
        sid = self.be.spawn("web", "/tmp", env=ENV)
        val = _secret_value("notes-token")
        self.be._update_reg(sid, env={**ENV, "NOTES_API_TOKEN": val})
        self.be._options(self._sess(sid), dict)                 # launched once; no live object holds it now
        self.assertNotIn(sid, self.be.sessions)
        self.assertIn(val, self._flag_file(sid).read_text())
        self.assertTrue(self.be.set_env(sid, {}))
        self.assertEqual(self._files_carrying(val), [], "gone at the write, with no connect to come")
        self.assertFalse(self._flag_file(sid).exists())

    def test_the_write_keeps_the_other_keys_and_a_stale_file_goes_at_the_next_connect(self):
        # the file also carries the keys the last connect wrote (a fast-mode pick here): the env block goes, the rest
        # stays for the launch that reads it; and a file an earlier kernel left stale (the registry already
        # redacted) is removed by an unchanged re-declaration at the write, or by the next connect
        sid = self.be.spawn("web", "/tmp", env=ENV)
        val = _secret_value("notes-token")
        p = self._flag_file(sid)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"fastMode": True, "env": {**ENV, "NOTES_API_TOKEN": val}}) + "\n")
        self.assertTrue(self.be.set_env(sid, {}))
        self.assertEqual(json.loads(p.read_text()), {"fastMode": True}, "the block goes, the key that rides stays")
        p.write_text(json.dumps({"env": {"NOTES_API_TOKEN": val}}) + "\n")   # stale: the registry already says {}
        self.assertTrue(self.be.set_env(sid, {}), "an unchanged re-declaration")
        self.assertFalse(p.exists(), "puts the stale file right at the write")
        p.write_text(json.dumps({"env": {"NOTES_API_TOKEN": val}}) + "\n")
        kw = self.be._options(self._sess(sid), dict)            # or the next connect does, needing no key
        self.assertNotIn("settings", kw)
        self.assertFalse(p.exists(), "a connect that needs no key removes the stale file rather than leaving it")
        self.assertEqual(self._files_carrying(val), [])

    def test_a_fork_copies_no_credential_shaped_name_into_its_own_files(self):
        """Review round 1 of the env-pick door (2026-09-18): the fork copied the parent's stored env verbatim except
        the reserved and login names, so a stored credential-shaped name was written into a fresh registry and,
        at the child's first connect, a fresh flag-settings file, by a user gesture (a cut turn, a comment thread)
        no door sees. The copy drops such a name, on its own names-only line (not the reserved drop's, whose words
        would misdescribe it, and with no key: the fork is one gesture, and stubs of _log take none), and the
        parent keeps it until its env is re-declared."""
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
            self.assertFalse(any(val in m for m, _p, _k in self.logged), "no log line carries the value")
            self.assertFalse(any(kw2.get("key") == ("env-stored-credential", CHILD) for _m, _p, kw2 in self.logged),
                             "the child's own connect has no stored offender to report")
        finally:
            os.environ.pop("CLAUDE_CONFIG_DIR", None)

    @unittest.skipIf(os.geteuid() == 0, "root writes and unlinks through a directory's mode bits")
    def test_a_redaction_whose_file_can_neither_be_rewritten_nor_removed_is_refused_and_the_registry_keeps_the_offender(self):
        """kernel-1 / rules-1 / extra7-1 / tests-3 (review round 2 of the env-pick door, 2026-09-19), round 1's high
        re-entered through the fix's own failure path: when the sync's rewrite failed, set_env still cleared the
        registry and answered True, so the redaction reported success while the value stayed in the flag-settings
        file and the stored-offender row, which reads the registry, fell silent (both reviewers reproduced it with
        chmod 0500). The ladder's last rung, through set_env itself: the pick is refused, the registry keeps naming
        the offender, the row names the file, and the value is still findable on disk, which is the honest state;
        the next connect still says the stored name, and the same redaction lands once the directory is writable."""
        sid, s, val = self._stored_offender()
        d = self._flag_file(sid).parent
        os.chmod(d, 0o500)
        self.addCleanup(os.chmod, d, 0o700)
        # the `romp new --env` road (the rest of the set): the block is rewritten, so the ladder is climbed, and its
        # last rung refuses; the `--no-env` road empties the file, so it is the remove road, refused the same way
        self.assertFalse(self.be.set_env(sid, dict(ENV)), "the re-declaration is refused, not reported as done")
        self.assertFalse(self.be.set_env(sid, {}), "the redaction to the empty set is refused too")
        self.assertIn("NOTES_API_TOKEN", self._reg(sid)["env"], "the registry keeps naming the offender")
        self.assertEqual(s.env_vars.get("NOTES_API_TOKEN"), val, "the live session's env is unchanged")
        self.assertFalse(self.reconnects, "nothing applied, no reconnect")
        self.assertTrue(self._files_carrying(val), "the value is still on disk: the honest state, said")
        rows = [(m, kw) for m, problem, kw in self.logged if problem and "could not be rewritten" in m]
        self.assertEqual(len(rows), 1, self.logged)
        self.assertIn(str(self._flag_file(sid)), rows[0][0], "the row names the file")
        self.assertIn("nor removed", rows[0][0])
        self.assertIn("refused", rows[0][0])
        self.assertLessEqual(len(rows[0][1]["ring_text"]), sb.ERROR_CENTER_TEXT_CAP)
        gone = [(m, kw) for m, problem, kw in self.logged if problem and "could not be removed" in m]
        self.assertEqual(len(gone), 1, self.logged)
        self.assertIn(str(self._flag_file(sid)), gone[0][0])
        self.assertLessEqual(len(gone[0][1]["ring_text"]), sb.ERROR_CENTER_TEXT_CAP)
        self.assertEqual(_temps(self.be.state_dir), [], "no temp is left by the failed rewrite")
        self.assertFalse(any(val in m for m, _p, _k in self.logged), "no log line carries the value")
        key = ("env-stored-credential", sid)
        before = len([1 for _m, _p, kw in self.logged if kw.get("key") == key])
        self.be._options(s, dict)
        self.assertEqual(len([1 for _m, _p, kw in self.logged if kw.get("key") == key]), before + 1,
                         "the next connect still says the stored name, since the registry still holds it")
        os.chmod(d, 0o700)
        self.assertTrue(self.be.set_env(sid, {}), "the same redaction lands once the directory is writable")
        self.assertEqual(self._files_carrying(val), [])
        self.assertEqual(self._reg(sid)["env"], {})

    def test_a_redaction_whose_file_cannot_be_rewritten_removes_it_and_stands(self):
        """The ladder's first rung through set_env (review round 2, 2026-09-19): a rewrite that fails on a writable
        directory (a full disk's shape) removes the file instead, which is safe because the next connect writes it
        whole from the registry and nothing reads it between connects; the redaction stands and is reported so."""
        sid, s, val = self._stored_offender()
        _interpose(self, replace=_enospc)
        self.assertTrue(self.be.set_env(sid, dict(ENV)), "removed instead, and the redaction stands")
        self.assertEqual(self._reg(sid)["env"], ENV)
        self.assertEqual(s.env_vars, ENV)
        self.assertFalse(self._flag_file(sid).exists(), "the file went rather than keeping the value")
        self.assertEqual(self._files_carrying(val), [], "the value is in no file under the state root")
        self.assertEqual(_temps(self.be.state_dir), [], "and no temp is left")
        rows = [m for m, problem, _kw in self.logged if problem and "removed instead" in m]
        self.assertEqual(len(rows), 1, self.logged)
        self.assertIn(str(self._flag_file(sid)), rows[0])
        kw = self.be._options(s, dict)
        self.assertEqual(json.loads(Path(kw["settings"]).read_text())["env"], ENV, "the next connect writes it whole from the registry")

    def test_a_connect_composing_across_a_redaction_launches_the_redacted_env(self):
        """kernel-3 / correctness-1 (review round 2 of the env-pick door, 2026-09-19): the compose read the session's
        env at its top, and set_env wrote the file, the registry and the session with no lock, so a redaction landing
        between the compose's read and its write was undone by the write: the pre-redaction env, value included, went
        back into the file the sync had just cleaned, and set_env answered True (the reviewers reproduced it, and
        showed a lock around the two writes alone leaves it open, since the stale read is earlier). The exact
        interleave, by execution through the real _options: its top read sees the offender, the redaction lands, and
        the write that follows carries the redacted env, because the env is read again under the writers' lock at
        the write and the launch stamp follows it."""
        sid, s, val = self._stored_offender()
        orig = self.be._launch_shape
        fired = []

        def hooked(sess, **kw):
            shape = orig(sess, **kw)                      # the compose's top read: the env still carries the offender
            if not fired:
                fired.append(dict(shape["env"]))
                self.assertTrue(self.be.set_env(sid, dict(ENV)), "the redaction lands between the compose's read and its write")
            return shape
        self.be._launch_shape = hooked
        self.addCleanup(delattr, self.be, "_launch_shape")
        kw = self.be._options(s, dict)
        self.assertEqual(fired[0].get("NOTES_API_TOKEN"), val, "the compose had read the pre-redaction env")
        self.assertEqual(json.loads(Path(kw["settings"]).read_text())["env"], ENV,
                         "the file the CLI reads carries the redacted env, not the compose's stale read")
        self.assertEqual(self._files_carrying(val), [], "the value is in no file under the state root")
        self.assertEqual(s._launching["env"], ENV, "the launch stamp follows the write, so the landing records what launched")
        self.assertEqual(self._reg(sid)["env"], ENV)
        self.assertFalse(any(val in m for m, _p, _k in self.logged), "no log line carries the value")

    def _real_ring(self):
        """The row as the dashboard reads it: the class stubs _log to capture lines, so the stub goes and the kernel
        log's lines are captured instead (every name whole is the LOG line's promise, the short form's is the cap)."""
        del self.be._log
        self.lines = []
        self.be._log_cb = self.lines.append
        return load_source("romp_kernel", os.path.join(BIN, "romp-kernel"))

    def _repeat_suffix(self):
        """_log's count suffix as the REAL ring renders it at one repeat, the form a second connect leaves, read from
        the ring rather than spelled here, so a change to that suffix moves the bound this class pins."""
        self.be._log("probe", problem=True, key=("probe",))
        self.be._log("probe", problem=True, key=("probe",))
        row = [r for r in self.be.problems() if r.get("key") == ("probe",)][0]
        self.assertTrue(row["text"].startswith("probe (1 repeat"), row["text"])
        return row["text"][len("probe"):]

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

    STORED_ROW_TAIL = ("launched until", "romp new --env", "--no-env", "flag-settings file")

    def test_the_stored_offender_row_fits_the_error_centre_for_one_two_and_twenty_variables(self):
        """regression-1 (review round 2 of the env-pick door, 2026-09-19) and its addendum. The reworded row ran to
        333 characters against the 240-character error-centre cap this PR introduced, so the dashboard clipped it
        mid-parenthesis and lost exactly the clause round 1 ordered added (the redaction reaches the flag-settings
        file; the --no-env road). Round 2's short form was then pinned at a length two demo names happened to fit,
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
        """The bound as a property of the format (the round-2 addendum, 2026-09-19): the worst case the construction
        allows, a session name and a first variable past their budgets and a count of more, is computed HERE from
        the format's own pieces and asserted under the cap with _log's repeat suffix as the real ring renders it.
        The measurements round 2 took stand as evidence of what the earlier form did: its fixed text was 143
        characters plus every name whole, so with the 55-character one-repeat suffix it measured 216 for a
        3-character session with NOTES_API_TOKEN and 238 for a 16-character session with OP_SERVICE_ACCOUNT_TOKEN,
        against the cap of 240, and 242 for the same 3-character session with those two names together: the second
        name already spent the cap. The bounded form's fixed text is 127 characters, its budgets 20 and 24, and
        with " and 99 more" and the one-repeat suffix its worst case is 238; the two characters left are a third
        digit in either count, and each further digit costs one character of the tail's last word."""
        self._real_ring()
        suffix = self._repeat_suffix()
        fixed = sb.STORED_OFFENDER_RING % ("", "")
        self.assertEqual(fixed.count("%"), 0, "two slots, the session name and the names, and nothing else")
        long_session = "s" * (sb.STORED_OFFENDER_SESSION_BUDGET + 20)
        long_name = "NOTES_" + "X" * 40 + "_TOKEN"
        names = [long_name] + ["ZZ_%02d_TOKEN" % i for i in range(19)]                # the long one sorts first
        worst = sb.stored_offender_ring_text(long_session, names)
        self.assertEqual(len(worst), len(fixed) + sb.STORED_OFFENDER_SESSION_BUDGET + sb.STORED_OFFENDER_NAME_BUDGET
                         + len(" and 19 more"), "both budgets spent, plus the count: the format's worst case")
        self.assertLessEqual(len(worst) + len(suffix), sb.ERROR_CENTER_TEXT_CAP,
                             "the worst case fits with the ring's suffix: %d + %d against %d"
                             % (len(worst), len(suffix), sb.ERROR_CENTER_TEXT_CAP))
        self.assertLessEqual(len(sb.stored_offender_ring_text(long_session, names * 5)) + len(suffix),
                             sb.ERROR_CENTER_TEXT_CAP, "a third digit in the count of more fits too")
        for clause in self.STORED_ROW_TAIL:
            self.assertIn(clause, worst)
        self.assertEqual(sb.STORED_OFFENDER_NAME_BUDGET, len("OP_SERVICE_ACCOUNT_TOKEN"),
                         "the longest 1Password name is whole under the budget")
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
        cut_name = long_name[:sb.STORED_OFFENDER_NAME_BUDGET - 1] + sb._CUT_MARK
        cut_session = long_session[:sb.STORED_OFFENDER_SESSION_BUDGET - 1] + sb._CUT_MARK
        self.assertEqual(len(cut_name), sb.STORED_OFFENDER_NAME_BUDGET)
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
        self.assertNotIn(sb._CUT_MARK, line[0], "nothing is cut on the log line")
        self.assertEqual(sb._cut_to("short", 24), "short", "a name within its budget is whole, unmarked")

    def test_the_refusal_line_is_headed_once_and_fits_the_caps(self):
        """Review round 1 of the env-pick door (2026-09-18): the set_env line read "pick refused: env: ..." and ran
        to 414 characters against the feed's 400 (kernel.SDK_PROBLEM_TEXT_CAP), so the row an admin read was
        clipped mid-word; the error centre cuts again at 240 (sdk_backend.ERROR_CENTER_TEXT_CAP, the badge
        mirror's literal). The line carries the door's head once, fits the kernel's cap with a name, and the
        ring text, the error centre's short form, fits its cap and leads with the names, that nothing was saved
        and where the value belongs."""
        km = load_source("romp_kernel", os.path.join(BIN, "romp-kernel"))
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
        self.assertLessEqual(len(line), km.SDK_PROBLEM_TEXT_CAP, "whole in the feed's problem row")
        self.assertEqual(km._sdk_problem_text(line), line, "the kernel's cut leaves it as it is")
        ring = kw.get("ring_text")
        self.assertTrue(ring and ring.startswith("env (web): pick refused: NOTES_API_TOKEN is credential-shaped: the pick was not saved"), ring)
        self.assertIn("process environment", ring)
        self.assertLessEqual(len(ring), sb.ERROR_CENTER_TEXT_CAP, "whole in the error centre")
        self.assertNotIn(val, line)
        self.assertNotIn(val, ring)
        # another refusal shape keeps its own words, headed once, and rides the ring as it is
        self.assertFalse(self.be.set_env(sid, {"9BAD": "1"}))
        bad = [(m, kw) for m, problem, kw in self.logged if problem and "9BAD" in m]
        self.assertEqual(len(bad), 1)
        self.assertTrue(bad[0][0].startswith("env (web): pick refused: bad name"), bad[0][0])
        self.assertEqual(bad[0][1].get("ring_text"), bad[0][0])
        # the 1Password half hears its own road (review round 2, 2026-09-19): the process environment refuses such a
        # name at boot, so the advice that took the deployment down is not given; the longest such name fits the caps
        self.assertFalse(self.be.set_env(sid, {"OP_SERVICE_ACCOUNT_TOKEN": _secret_value("op")}))
        op_rows = [(m, kw) for m, problem, kw in self.logged if problem and "OP_SERVICE_ACCOUNT_TOKEN" in m]
        self.assertEqual(len(op_rows), 1, self.logged)
        line, kw = op_rows[0]
        self.assertLessEqual(len(line), km.SDK_PROBLEM_TEXT_CAP, (len(line), line))
        self.assertIn("refuses a 1Password name in its process environment at boot", line)
        self.assertIn("its own file", line)
        self.assertNotIn("Put such a value in the process environment", line)
        ring = kw["ring_text"]
        self.assertLessEqual(len(ring), sb.ERROR_CENTER_TEXT_CAP, (len(ring), ring))
        self.assertIn("its own file", ring)

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
