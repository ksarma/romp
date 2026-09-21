#!/usr/bin/env python3
"""The state root's trust boundary: the process stops on a hostile root, and every reader of the root's contents is guarded
(rounds 2 to 4, 2026-09-20 and 2026-09-21).

kernel/judge.py makes the state root 0700 at import, best-effort, and until this change swallowed the OSError, read the
mode back once and said one stderr sentence when it was not 0700, refusing nothing. The root's mode is the premise of
_atomic_write's interim-mode argument (a file this uid wrote at a looser mode is not exposed because the root is
owner-only), so a guard that cannot refuse left a security argument resting on a diagnostic. Round 1 answered with a
runtime 503 latch that closed the kernel's two doors and left every internal writer running under the hostile root, the
housekeeping pass whose own stage set the latch included; round 2 replaced the latch with an EXIT, because an exit is
the only shape that stops every writer by construction. Round 4 (romp-manager's word, 2026-09-20 22:51Z, after the
artifact enumeration in plans/state-root-mode.md) settled WHAT is refused and WHEN it is judged:

  ONE IMPLEMENTATION   kernel/state_root_mode.py, loaded by path under one fixed module name by kernel/judge.py and by
        postal/postal_service.py (the bus carried a reduced copy marked KEEP IN SYNC until round 4): the two daemons on one
        root judge it by one rule and say it in one voice. TheBusSharesTheCheck pins the same file, the same object.
  THE DISCRIMINATOR    "writable by another local user" is an OTHER write bit, or a GROUP write bit under a group that is
        not the owner's private group (the group lists no member but the owner, and no other account has the gid as its
        primary group). A group write bit under the owner's private group is warn-class (0775 under umask 0002 on a
        user-private-group box: every harness root), like 0755. A group database that cannot be read or does not answer
        within a bound (a daemon thread joined with a timeout) counts as writable, the restricted side, with its OWN
        message and remedy (check getent group <gid> and the name service), never the distrust remedy. Discriminator.
  THE IMPORT-READ RULE a PRE-EXISTING root whose mode as read at the judge module's import, before its own chmod, was
        writable by another local user REFUSES at kernel import (exit 2) whatever the chmod did afterwards, with the
        distrust remedy (entries planted while it was writable are not to be trusted: remove serve-token, repo-root and
        every entry you did not make, or recreate the root, then chmod 700); a root the import CREATED is exempt. The same
        at boot (the two doors agree) and in the bus's start gate. A pre-existing 0775 root under the owner's private
        group, or 0755, is re-tightened and reported once (the round-2b row). TheImportGateComesFirst, Boot, TheBusRefuses.
  REFUSE AT RUNTIME    found by the jobs pass's first stage or by a request's cached re-check, os._exit(2) from whichever
        thread found it (_state_root_exit_now), so no later jobs stage, no pusher cycle, no judge pass runs on under the
        root; the manager restarts the kernel and the boot refuses again while the root reads so.
  READ BEFORE REPAIR   the check reads the mode FIRST and the verdict is from that read; its own best-effort chmod runs
        after and is reported (repaired, modeAfter), so a root this uid owns that was loosened is re-tightened AND leaves
        a trace, never a silent repair that erases the case the re-check exists to report.
  WARN                 a root not 0700 but writable by nobody else files one error-centre row per transition under the
        bell's "refused" kind (not the mutable "sdk" kind, whose one mute would hide it with the backend's), built to
        fit the bell whole with the remedy first, and refuses nothing.
  THE GUARDED READERS  round 4 (the round-3 ruling's A, B and C): every read of a path under the root in the kernel, the
        judge, the event model, the bus and the session host goes through kernel/state_root_mode.py's Reader, whose guard
        lstat's every component from the root down (not a symlink, this uid's, not writable by another local user by the
        discriminator: a 0775 venv or a 0664 mirror under the private group PASSES) and QUARANTINES what fails to
        <root>/quarantine/<stamp>.<relative-path-with-dots>, says one stderr line, files one refused-kind row and reads
        the path as absent, so nothing planted is adopted and nothing is merely skipped (a skipped plant was re-adopted
        at the next boot). The population is derived by an AST census (tests/test_state_root_readers.py), not by hand.
        TheGuardedReadersQuarantine, TheCheckpointsDirectoryIsGuarded, TheBusRefuses (planted mail and links).
  THE CREATION EXEMPTION keys on the root being EMPTY at the import's read, whoever made it: an empty pre-existing root
        at the umask's mode is a creation default (the manager, the CLI and every harness make the root a moment before
        the first romp process tightens it), and boots silently; the distrust refusal is for a pre-existing root that read
        writable by another AND held entries (round 3's H). Boot, TheImportGateComesFirst, AServedKernelRefusesAtRuntime.
  ENOTDIR              a state root path that exists and is not a directory is verdict refuse with ENOTDIR and its own
        remedy at every check (round 3's I). Discriminator, TheImportGateComesFirst, TheRuntimeRefusalExits, TheBusRefuses.
  EVERY LONG-LIVED WRITER RUNS THE CHECK: the bus at import in every mode (not only argv "serve") and the session host at
        start and on its beat (round 3's E). TheBusRefuses, TheSessionHostRunsTheCheck.
  ONE TEXT             the predicate lives in kernel/state_root_mode.py alone; the loaders define no copy (OneText).

For each arm the test below names, in its docstring, what the arm does to everything that is NOT the door it guards (the
round's shape demand), and what fails at 9748684d3 (round 2's head, before round 4) and how that was checked: this module
copied into a detached worktree of that commit under the notes' scratch (removed after) and run there.

Hermetic: every root is a fresh temp dir (mkdtemp is 0700 whatever the umask); every kernel-side cache is saved and
restored; the runtime exit is a module-level indirection (_state_root_exit) a test replaces with a raising double, so
the refusal is observable in-process without taking the test runner down; os.chmod is interposed only for the planted
root and only for the test's length; the group database is INJECTED (kernel/state_root_mode.py takes the lookups as
keyword arguments, and resolves them at call time from grp and pwd otherwise, so a mock.patch of grp.getgrgid and
pwd.getpwall reaches the real boot path), so no test needs a second account on the box and none reads or writes an
account name; the arms that rely on the real database (a child kernel over a 0775 root) skip unless this account's
primary group is private here. tests/test_judge_scratch_private.py, which pins _state_root_mode_line and the import's
one line, is unchanged by this change and still passes.
"""
import ast
import base64
import contextlib
import errno
import grp
import http.client
import io
import json
import os
import pwd
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
ROOT = os.path.dirname(HERE)

# tests/test_kernel_cors.py's load order: hermetic state BEFORE the loads (they resolve the root at import), the token
# env so _load_token() never touches a real state dir, NO_OPEN so the import launches no browser. The XDG root here is
# a fresh mkdtemp (0700), so the kernel's own import gate reads ok and this module loads without refusing.
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)
os.makedirs(os.path.join(os.environ["XDG_STATE_HOME"], "romp"), exist_ok=True)
os.chmod(os.path.join(os.environ["XDG_STATE_HOME"], "romp"), 0o700)   # under a group-writable umask a fresh mkdir is 0775
with open(os.path.join(os.environ["XDG_STATE_HOME"], "romp", "session-hosts"), "w") as _fh:
    _fh.write("off\n")                                                # this module mints roots and rebinds; floor its own too
em = load_source("romp_event_model", os.path.join(BIN, "romp-event-model"))
jd = load_source("romp_judge", os.path.join(BIN, "romp-judge"))
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "test-token-DO-NOT-USE")
km = load_source("romp_kernel", os.path.join(BIN, "romp-kernel"))
assert km.jd is jd, "romp_load re-executes a loaded name into the same module: the kernel's judge IS this module's"
srm = jd.srm                                                          # kernel/state_root_mode.py, the shared check
assert sys.modules["romp_state_root_mode"] is srm

REFUSED = PermissionError(1, "chmod refused (interposed)")   # errno 1 is EPERM; os.strerror(1) is "Operation not permitted"
DISTRUST = "remove serve-token, repo-root and every entry you did not make"   # the round-4 distrust remedy's head
LOOKUP_REMEDY = "check getent group"                                   # the lookup failure's own remedy's head


class _Exited(BaseException):
    """The runtime exit, as a test double sees it: os._exit(2) never returns, so a double stands in for a process that
    is gone. A BaseException, not an Exception, so it propagates through the `except Exception` guards every jobs stage
    and every request handler wraps its work in, exactly as os._exit's not-returning does: no writer downstream runs."""
    def __init__(self, code):
        self.code = code


def _mode(p):
    return stat.S_IMODE(os.stat(p).st_mode)


def _ids(p):
    st = os.stat(p)
    return (st.st_uid, st.st_gid)


def _refusing_chmod(root):
    """An os.chmod that raises EPERM for `root` alone and delegates every other path: the shape of a root this uid cannot
    tighten, interposed the way tests/test_judge_scratch_private.py interposes it."""
    real = os.chmod
    rr = os.path.realpath(str(root))

    def refuse(path, mode, *a, **k):
        if os.path.realpath(str(path)) == rr:
            raise PermissionError(REFUSED.errno, REFUSED.strerror)
        return real(path, mode, *a, **k)
    return refuse


def _fakes(members=(), primaries=0, fail=None, block=0.0, gid=None):
    """Injected group-database lookups for the discriminator (kernel/state_root_mode.py takes getgrgid, getpwall and
    getpwuid as keyword arguments): the root's group with `members` beside its owner (synthetic names), `primaries` other
    accounts (synthetic uids) holding `gid` (default: this process's gid, the gid of every root a test makes) as their
    primary group, `fail` an exception getgrgid raises, `block` seconds getgrgid sleeps before answering. The owner is
    named "owner" here; no real account name is read or written by any test."""
    gid = os.getgid() if gid is None else gid

    def getpwuid(uid):
        return SimpleNamespace(pw_name="owner", pw_uid=uid, pw_gid=gid)

    def getgrgid(g):
        if block:
            time.sleep(block)
        if fail is not None:
            raise fail
        return SimpleNamespace(gr_name="private", gr_gid=g, gr_mem=list(members))

    def getpwall():
        rows = [SimpleNamespace(pw_name="owner", pw_uid=os.getuid(), pw_gid=gid)]
        rows += [SimpleNamespace(pw_name="peer-%d" % i, pw_uid=900000 + i, pw_gid=gid) for i in range(primaries)]
        return rows
    return {"getgrgid": getgrgid, "getpwall": getpwall, "getpwuid": getpwuid}


def _no_lookup():
    """Lookups that must not run: any call is a fault the discriminator would report as a lookup failure, so a test that
    asserts lookupError is None has proved no lookup was made."""
    def boom(*a, **k):
        raise AssertionError("the group database was consulted")
    return {"getgrgid": boom, "getpwall": boom, "getpwuid": boom}


@contextlib.contextmanager
def _patched_lookups(fakes):
    """The injected database on the REAL boot path (which passes no lookups): the shared module resolves grp.getgrgid and
    pwd.getpwall at call time, so patching the two module attributes for the block's length is enough; pwd.getpwuid stays
    real (the owner's name is compared against the fake group's member list and written nowhere)."""
    with mock.patch("grp.getgrgid", new=fakes["getgrgid"]), mock.patch("pwd.getpwall", new=fakes["getpwall"]):
        yield


def _private_group_here():
    """Whether this account's primary group is private on this box (the real database): the child arms that rely on the
    real lookups (a 0775 root that must read warn-class) skip when it is not."""
    private, _why = srm.private_group(os.getgid(), os.getuid())
    return private is True


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def inspect_getsource_module():
    """The kernel module's source text, read from its file (inspect.getsource on a load_source module is reliable, but
    reading the file keeps the AST test independent of import machinery)."""
    return open(os.path.join(BIN, "romp-kernel"), encoding="utf-8").read()


# ── the discriminator: READ-BEFORE-REPAIR, WARN, REFUSE, UNKNOWN, the group judgment, the lookup bound ──────────────

class Discriminator(unittest.TestCase):
    """jd.state_root_mode_check's verdict over the modes that matter, judged by kernel/state_root_mode.py's discriminator,
    and what the check's own repair does to the verdict: NOTHING. The verdict is taken from the mode as READ; the
    best-effort chmod runs after and is reported (repaired, modeAfter), so a loosened root this uid owns is re-tightened
    and its loosening still shows. The group database is injected (kernel/state_root_mode.py's keyword arguments), so
    every case runs on one account. At 9748684d3 the check takes no lookup arguments (TypeError on every injected case),
    jd.srm does not exist (AttributeError), and 0770 or 0775 under any group is refuse (`mode & 0o022`); checked by
    running this module against a detached worktree of that commit."""

    def _root(self, mode):
        d = tempfile.mkdtemp()
        os.chmod(d, mode)
        return d

    def test_0700_is_ok_and_says_nothing_and_consults_no_database(self):
        d = tempfile.mkdtemp()
        chk = jd.state_root_mode_check(d, **_no_lookup())
        self.assertEqual(chk["verdict"], "ok")
        self.assertIsNone(chk["line"])
        self.assertIsNone(chk["err"])
        self.assertIsNone(chk["lookupError"], "no group bit: no lookup")
        self.assertEqual((chk["modeRead"], chk["modeReadText"], chk["root"]), (0o700, "0700", d))
        self.assertEqual((chk["uid"], chk["gid"]), _ids(d), "the read's owner and group travel with the mode")
        self.assertFalse(chk["repaired"], "0700 already: nothing to repair")
        self.assertEqual(chk["modeAfter"], 0o700)
        self.assertIsNone(chk["importRefusal"], "another root: no import fact")
        self.assertLessEqual(abs(chk["t"] - time.time()), 5)

    def test_not_0700_but_not_writable_by_others_warns(self):
        for mode in (0o755, 0o750, 0o711):
            d = self._root(mode)
            with mock.patch("os.chmod", new=_refusing_chmod(d)):   # else the repair tightens it and repaired is True
                chk = jd.state_root_mode_check(d, **_no_lookup())
            self.assertEqual(chk["verdict"], "warn", "%04o" % mode)
            self.assertIsNone(chk["writableBy"])
            self.assertIsNone(chk["lookupError"], "no group write bit: no lookup")
            self.assertEqual(chk["modeReadText"], "%04o" % mode, "the verdict names the mode READ, not the mode after")
            self.assertIn(d, chk["line"])
            self.assertIn("%04o" % mode, chk["line"], "names the mode read back")
            self.assertIn("0700", chk["line"], "and the mode expected")
            self.assertIn(chk["remedy"], chk["line"], "and the remedy")
            self.assertNotIn("\n", chk["line"], "one line")
            self.assertEqual(_mode(d), mode, "the refused chmod healed nothing")

    def test_an_other_write_bit_refuses_with_no_lookup(self):
        """An OTHER write bit is the whole answer: every local user can write the root, so the group database is not
        consulted (the injected lookups fault if called, and a fault would show as lookupError). The remedy distrusts the
        contents in round 4's words. At 9748684d3: TypeError (no lookup arguments), and the remedy reads "remove
        serve-token and repo-root under ..., then chmod 700 it"."""
        for mode in (0o707, 0o722, 0o777, 0o702):
            d = self._root(mode)
            with mock.patch("os.chmod", new=_refusing_chmod(d)):
                chk = jd.state_root_mode_check(d, **_no_lookup())
            self.assertEqual(chk["verdict"], "refuse", "%04o" % mode)
            self.assertEqual(chk["writableBy"], "other")
            self.assertIsNone(chk["lookupError"], "no lookup ran (a call would have faulted into lookupError)")
            self.assertIsNone(chk["groupPrivate"])
            self.assertIn("refuses to serve", chk["line"])
            self.assertIn("an other write bit", chk["line"], "the line says which bit")
            self.assertIn(DISTRUST, chk["remedy"], "the remedy distrusts the contents (fresh-1, round 4's words)")
            self.assertIn("or recreate the root, then chmod 700 it", chk["remedy"])
            self.assertIn(d, chk["line"])
            self.assertIn("%04o" % mode, chk["line"])

    def test_a_group_write_bit_under_the_owners_private_group_is_warn_class(self):
        """THE DISCRIMINATOR's other half: a group write bit whose group lists no member but the owner and is nobody
        else's primary group is writable by nobody but the owner, so 0775 (what every directory made under umask 0002
        reads on a user-private-group box) and 0770 are warn-class: re-tightened by the check's chmod and reported, never
        refused. groupPrivate is True and the line says why. At 9748684d3 every one of these is refuse (`mode & 0o022`)."""
        for mode in (0o775, 0o770, 0o720):
            d = self._root(mode)
            chk = jd.state_root_mode_check(d, **_fakes())
            self.assertEqual(chk["verdict"], "warn", "%04o" % mode)
            self.assertTrue(chk["groupPrivate"])
            self.assertIsNone(chk["writableBy"])
            self.assertIsNone(chk["lookupError"])
            self.assertTrue(chk["repaired"], "a warn root this uid owns is re-tightened")
            self.assertEqual(_mode(d), 0o700)
            self.assertIn("re-tightened to 0700", chk["line"])
            self.assertIn("owner's private group", chk["line"], "the line says why a group write bit is not a refusal")
            self.assertNotIn(DISTRUST, chk["line"])
        # and standing (the chmod refused): still warn, with the private-group clause on the point and the line
        d = self._root(0o775)
        with mock.patch("os.chmod", new=_refusing_chmod(d)):
            chk = jd.state_root_mode_check(d, **_fakes())
        self.assertEqual(chk["verdict"], "warn")
        self.assertIn("owner's private group", chk["point"])
        self.assertEqual(_mode(d), 0o775)

    def test_a_group_write_bit_under_a_group_with_another_member_refuses(self):
        """The group holds another account: every member can write the root, so it is writable by another local user
        and refused, the line naming the count (never the member's name). At 9748684d3: TypeError."""
        d = self._root(0o775)
        chk = jd.state_root_mode_check(d, **_fakes(members=["peer-a"]))
        self.assertEqual(chk["verdict"], "refuse")
        self.assertEqual(chk["writableBy"], "group")
        self.assertIs(chk["groupPrivate"], False)
        self.assertIn("is shared: 1 other member", chk["line"])
        self.assertNotIn("peer-a", chk["line"], "counts, never account names")
        self.assertIn(DISTRUST, chk["remedy"])
        self.assertIn("re-tightened to 0700 after the read; the refusal stands on what was read", chk["line"])
        # the owner listed as a member of their own group is not "another" member
        d2 = self._root(0o770)
        chk2 = jd.state_root_mode_check(d2, **_fakes(members=["owner"]))
        self.assertEqual(chk2["verdict"], "warn", "the owner in the member list does not make the group shared")

    def test_a_group_write_bit_where_another_account_has_the_gid_as_primary_refuses(self):
        """No member listed, but another account has the gid as its primary group (a shared default group such as
        `users`): writable by that account, refused, the count on the line. At 9748684d3: TypeError."""
        d = self._root(0o775)
        chk = jd.state_root_mode_check(d, **_fakes(primaries=2))
        self.assertEqual(chk["verdict"], "refuse")
        self.assertEqual(chk["writableBy"], "group")
        self.assertIn("2 other accounts with it as their primary group", chk["line"])
        self.assertNotIn("peer-", chk["line"])
        self.assertIn(DISTRUST, chk["remedy"])

    def test_a_lookup_that_raises_refuses_with_the_lookup_message_not_the_distrust_remedy(self):
        """LOOKUP FAILURE IS RESTRICTED AND DISTINCT: getgrgid raising KeyError (no entry for the gid) or an OSError (the
        name service) makes the verdict refuse (romp cannot tell who else can write here) with its OWN line and remedy:
        the database could not be read, check getent group <gid> and the name service; never the distrust remedy, which
        would send the operator to remove entries when the fault is elsewhere. At 9748684d3: TypeError."""
        for fail, name in ((KeyError("getgrgid(): gid not found"), "KeyError"), (OSError(errno.EIO, "io"), "EIO")):
            d = self._root(0o775)
            chk = jd.state_root_mode_check(d, **_fakes(fail=fail))
            self.assertEqual(chk["verdict"], "refuse", name)
            self.assertIsNone(chk["writableBy"])
            self.assertIsNone(chk["groupPrivate"])
            self.assertIn(name, chk["lookupError"])
            self.assertIn("the group database could not be read (%s" % name, chk["line"])
            self.assertIn(LOOKUP_REMEDY, chk["remedy"])
            self.assertIn("%d" % _ids(d)[1], chk["remedy"], "the remedy names the gid to look up")
            self.assertIn("romp refuses until it can tell who else can write here", chk["line"])
            self.assertNotIn(DISTRUST, chk["line"], "the distinct message, never the distrust remedy")
        # a missing passwd entry for the OWNER is a lookup failure too
        fakes = _fakes()

        def no_owner(uid):
            raise KeyError("getpwuid(): uid not found")
        fakes["getpwuid"] = no_owner
        chk = jd.state_root_mode_check(self._root(0o775), **fakes)
        self.assertEqual(chk["verdict"], "refuse")
        self.assertIn("no passwd entry for uid", chk["lookupError"])

    def test_a_lookup_that_blocks_past_the_bound_refuses_with_the_timeout_message_and_returns(self):
        """THE BOUND: a group database that does not answer (getgrgid sleeping past the bound) is a lookup failure with the
        timeout message, and the check RETURNS within the bound plus a little, because the lookup runs in a daemon thread
        joined with a timeout; the thread is left to finish on its own and holds no process (daemon). A 0700 root and a
        0777 root pay no lookup at all, so the bound is never on their path. At 9748684d3: TypeError. The import's own
        bound is pinned in a child by TheImportGateComesFirst.test_a_group_lookup_that_blocks_does_not_hang_the_import."""
        d = self._root(0o775)
        t0 = time.monotonic()
        chk = jd.state_root_mode_check(d, bound=0.3, **_fakes(block=2.0))
        elapsed = time.monotonic() - t0
        self.assertLess(elapsed, 1.5, "the check returned at the bound, not at the lookup's leisure: %.2fs" % elapsed)
        self.assertEqual(chk["verdict"], "refuse")
        self.assertTrue(chk["lookupError"].startswith("timeout: the group database did not answer within 0.3 s"), chk["lookupError"])
        self.assertIn(LOOKUP_REMEDY, chk["remedy"])
        self.assertNotIn(DISTRUST, chk["line"])
        self.assertEqual(srm.LOOKUP_BOUND_S, 3.0, "the production bound: a few seconds")
        # the default bound is read at call time from the module constant, so a process can lower it before its checks
        with mock.patch.object(srm, "LOOKUP_BOUND_S", 0.2):
            t0 = time.monotonic()
            chk = jd.state_root_mode_check(self._root(0o775), **_fakes(block=2.0))
            self.assertLess(time.monotonic() - t0, 1.5)
        self.assertIn("within 0.2 s", chk["lookupError"])

    def test_read_before_repair_a_loosened_owned_root_is_retightened_and_reported(self):
        """The re-check's whole reason (the 2026-09-20 review's extra6-1): a 0755 or 0777 root THIS UID OWNS, loosened
        after boot, is re-tightened by the check's own chmod AND reported. The verdict is what was READ (warn for 0755,
        refuse for 0777), never a silent ok; repaired is True and modeAfter is 0700, so the loosening leaves a trace
        rather than being erased. Round 1 chmod'ed first and read 0700, so this case was invisible."""
        d = self._root(0o755)
        chk = jd.state_root_mode_check(d)
        self.assertEqual(chk["verdict"], "warn", "the verdict is the mode as read")
        self.assertTrue(chk["repaired"])
        self.assertEqual((chk["modeReadText"], chk["modeAfter"]), ("0755", 0o700))
        self.assertEqual(_mode(d), 0o700, "the repair ran, after the read")
        self.assertIn("re-tightened to 0700", chk["line"])
        d2 = self._root(0o777)
        chk2 = jd.state_root_mode_check(d2)
        self.assertEqual(chk2["verdict"], "refuse", "a writable root refuses on what was read, even once re-tightened")
        self.assertTrue(chk2["repaired"])
        self.assertEqual(_mode(d2), 0o700)
        self.assertIn("re-tightened to 0700 after the read; the refusal stands on what was read", chk2["line"])

    def test_an_unreadable_root_is_unknown_and_refuse_class(self):
        d = os.path.join(tempfile.mkdtemp(), "never-made")
        chk = jd.state_root_mode_check(d)
        self.assertEqual(chk["verdict"], "unknown")
        self.assertIsNone(chk["modeRead"])
        self.assertIsNone(chk["modeReadText"])
        self.assertEqual(chk["statErrno"], "ENOENT")
        self.assertIn("ENOENT", chk["err"])
        self.assertIn("could not be read", chk["line"])
        self.assertIn("unverified root is not served from", chk["line"])
        self.assertIn(d, chk["remedy"])

    def test_a_refused_repair_puts_the_errno_name_and_text_in_err_and_the_line(self):
        """Arm four: the chmod's OSError, with its errno alone (never the exception's text, which carries the path), on
        the same surface as the mode; the remedy then says the root is not this uid's to change."""
        for mode, verdict in ((0o755, "warn"), (0o777, "refuse")):
            d = self._root(mode)
            with mock.patch("os.chmod", new=_refusing_chmod(d)):
                chk = jd.state_root_mode_check(d)
            self.assertEqual(chk["verdict"], verdict, "%04o" % mode)
            self.assertEqual(chk["repairErrno"], "EPERM")
            self.assertEqual(chk["repairError"], "EPERM: %s" % os.strerror(1))
            self.assertIn("EPERM", chk["err"], "the errno name")
            self.assertIn(os.strerror(1), chk["err"], "and its text")
            self.assertIn("EPERM", chk["line"])
            self.assertNotIn("interposed", chk["err"], "built from the errno, not from the exception's text")
            self.assertFalse(chk["repaired"], "the chmod was refused: nothing repaired")
            self.assertEqual(_mode(d), mode, "the refused chmod changed nothing")

    def test_a_repair_refused_with_eacces_reads_the_same_way(self):
        d = self._root(0o755)
        real = os.chmod

        def eacces(path, mode, *a, **k):
            if os.path.realpath(str(path)) == os.path.realpath(d):
                raise PermissionError(13, "denied (interposed)")
            return real(path, mode, *a, **k)
        with mock.patch("os.chmod", new=eacces):
            chk = jd.state_root_mode_check(d)
        self.assertEqual(chk["repairErrno"], "EACCES")
        self.assertIn("EACCES", chk["err"])
        self.assertIn(os.strerror(13), chk["err"])
        self.assertIn("not this uid's to change", chk["remedy"])

    def test_a_0700_root_whose_chmod_fails_is_ok_with_the_error_on_the_line(self):
        """Arm four's one case where the failed chmod is the whole signal: the root reads 0700 (verdict ok) but this
        uid's chmod is refused (the shape of a root another uid owns). The line is not None: it names the root, 0700,
        the errno name and text, and the remedy. A plain ok (the chmod ran) still says nothing."""
        d = tempfile.mkdtemp()
        with mock.patch("os.chmod", new=_refusing_chmod(d)):
            chk = jd.state_root_mode_check(d)
        self.assertEqual(chk["verdict"], "ok")
        self.assertEqual(chk["modeReadText"], "0700")
        self.assertEqual(chk["repairErrno"], "EPERM")
        self.assertIsNotNone(chk["line"], "ok with a repair error is said, not silent")
        for piece in (d, "0700", "EPERM", os.strerror(1)):
            self.assertIn(piece, chk["line"])
        self.assertIn("not this uid's to change", chk["remedy"])
        self.assertNotIn("\n", chk["line"])
        self.assertIsNone(jd.state_root_mode_check(d)["line"], "the chmod ran: plain ok, nothing said")

    def test_the_suites_own_root_reads_ok_and_recorded_no_repair_error(self):
        """This module made its root 0700 before the judge import (a 0700 read, no refusal). Under pytest every collected
        module's top level runs before any test, so a later module that loads the judge over a root of its own re-executes
        the import over that root: then the recorded read is that root's umask mode (0775 under 0002, 0755 under 022), a
        creation default with no entries, and still no refusal."""
        self.assertIsNone(jd._STATE_ROOT_REPAIR_ERROR, "the import's mkdir and chmod succeeded on the root it read")
        self.assertIsNone(jd._STATE_ROOT_REPAIR_STEP)
        self.assertIn(jd._STATE_ROOT_MODE_AT_IMPORT, (0o700, 0o775, 0o755), "this module's 0700 root, or another module's umask-mode root")
        self.assertEqual(jd._STATE_ROOT_IDS_AT_IMPORT, _ids(jd.STATE), "and the import recorded the read's owner and group")
        chk = jd.state_root_mode_check()
        self.assertEqual(chk["verdict"], "ok")
        self.assertIsNone(chk["importRepairError"])
        self.assertIsNone(chk["importRefusal"], "a 0700 read, or an empty umask-mode root: no refusal")
        self.assertEqual(chk["importCreated"], jd._STATE_ROOT_CREATED_AT_IMPORT,   # a later module's judge execution may have
                         "the check reports what the last judge execution recorded")   # MADE its root (a fresh ROMP_STATE_DIR): recorded, not refused

    def test_the_kernel_the_judge_and_the_bus_name_one_write_bit_set(self):
        """The bits the discriminator judges are one constant (0o022), spelled once in kernel/state_root_mode.py and
        re-exported by the judge; the old STATE_ROOT_REFUSE_MASK, whose name said a set bit was a refusal, is gone from
        the tree. At 9748684d3 jd.STATE_ROOT_WRITE_BITS does not exist and the mask is in three files."""
        self.assertEqual(jd.STATE_ROOT_WRITE_BITS, 0o022)
        self.assertIs(jd.STATE_ROOT_WRITE_BITS, srm.WRITE_BITS)
        self.assertEqual((srm.OTHER_WRITE, srm.GROUP_WRITE, srm.TARGET_MODE), (0o002, 0o020, 0o700))
        for rel in ("kernel/judge.py", "kernel/kernel.py", "postal/postal_service.py", "kernel/state_root_mode.py"):
            self.assertNotIn("STATE_ROOT_REFUSE_MASK", open(os.path.join(ROOT, rel), encoding="utf-8").read(), rel)


class TheImportRecordsItsOwnRepair(unittest.TestCase):
    """Arm four at the import: the judge module records the mode it READ before its own chmod (_STATE_ROOT_MODE_AT_IMPORT),
    that read's owner and group (_STATE_ROOT_IDS_AT_IMPORT, round 4: the discriminator needs them) and, for a call that
    failed, WHICH call it was and its errno (_STATE_ROOT_REPAIR_STEP, _STATE_ROOT_REPAIR_ERROR), so a mkdir failure is
    not mislabelled as a chmod's (correctness-3). state_root_mode_check on the module's own root folds the import's
    failed call into err, labelled as the import's, and builds THE IMPORT-READ RULE's refusal (importRefusal) for a
    pre-existing root that read writable by another local user, whatever the chmod did. The judge module itself never
    exits (a CLI must start); the kernel's gates act on the dict. The import's one stderr line is exactly as
    tests/test_judge_scratch_private.py pins it. Runs in a child so the planted root and refused chmod stay out of this
    process. At 9748684d3 the module has no _STATE_ROOT_IDS_AT_IMPORT and the dict no importRefusal, so the child's
    print faults (AttributeError, exit 1: "1 != 0" here); checked against a detached worktree of that commit."""

    def _child(self, setup, extra_env=None):
        root = os.path.join(tempfile.mkdtemp(), "romp")
        env = dict(os.environ)
        env["ROMP_STATE_DIR"] = root
        env.update(extra_env or {})
        code = ("import json, os, sys\n"
                "sys.path.insert(0, %r)\n"
                "from romp_load import load_source\n"
                "root = %r\n"
                "%s"
                "jd = load_source('romp_judge_child', %r)\n"
                "chk = jd.state_root_mode_check()\n"
                "ref = chk['importRefusal']\n"
                "print(json.dumps({'step': jd._STATE_ROOT_REPAIR_STEP, 'rec': jd._STATE_ROOT_REPAIR_ERROR,\n"
                "                  'atImport': jd._STATE_ROOT_MODE_AT_IMPORT, 'ids': jd._STATE_ROOT_IDS_AT_IMPORT,\n"
                "                  'err': chk['err'], 'verdict': chk['verdict'], 'importErr': chk['importRepairError'],\n"
                "                  'chkImport': chk['importModeRead'], 'created': chk['importCreated'],\n"
                "                  'refusal': ref and ref['line'], 'refusalCause': ref and ref['cause'],\n"
                "                  'empty': chk['importEmpty'], 'statErrno': chk['statErrno'], 'notDir': chk['notDirectory'],\n"
                "                  'remedy': chk['remedy'], 'modeNow': chk['modeRead']}))\n"
                % (HERE, root, setup, os.path.join(BIN, "romp-judge")))
        r = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, timeout=180)
        self.assertEqual(r.returncode, 0, r.stderr)
        return root, json.loads(r.stdout.strip().splitlines()[-1]), r.stderr

    def test_a_refused_chmod_at_import_is_recorded_with_its_errno_and_step(self):
        setup = ("os.mkdir(root)\n"
                 "os.chmod(root, 0o755)\n"
                 "real = os.chmod\n"
                 "def refuse(path, mode, *a, **k):\n"
                 "    if os.path.realpath(str(path)) == os.path.realpath(root):\n"
                 "        raise PermissionError(1, 'chmod refused (interposed)')\n"
                 "    return real(path, mode, *a, **k)\n"
                 "os.chmod = refuse\n")
        root, out, err = self._child(setup)
        self.assertEqual(out["step"], "chmod 700", "the call that failed, named")
        self.assertEqual(out["rec"], "EPERM: %s" % os.strerror(1), "recorded from the errno alone")
        self.assertEqual(out["atImport"], 0o755, "the mode read BEFORE the import's chmod")
        self.assertEqual(tuple(out["ids"]), _ids(root), "with that read's owner and group")
        self.assertEqual(out["chkImport"], 0o755, "and folded into the check dict for the module's own root (the boot reads it there)")
        self.assertFalse(out["created"], "a pre-existing root: the import did not make it")
        self.assertEqual(out["verdict"], "warn")
        self.assertIsNone(out["refusal"], "0755 is writable by nobody else: no import-read refusal")
        self.assertIn("chmod 700 failed at import: EPERM", out["importErr"], "labelled as the import's, not as a fresh chmod")
        self.assertIn("EPERM", out["err"])
        said = [l for l in err.splitlines() if "state root" in l]
        self.assertEqual(len(said), 1, "the import's one line, unchanged:\n" + err)
        self.assertIn(root, said[0])
        self.assertIn("0755", said[0])
        self.assertEqual(_mode(root), 0o755, "read, not healed")

    def test_a_failed_mkdir_is_labelled_mkdir_not_chmod(self):
        parent = tempfile.mkdtemp()
        os.chmod(parent, 0o555)   # the parent cannot be written: the mkdir of the root under it fails
        self.addCleanup(lambda: os.chmod(parent, 0o700))
        root = os.path.join(parent, "romp")
        env = dict(os.environ)
        env["ROMP_STATE_DIR"] = root
        code = ("import json, sys\n"
                "sys.path.insert(0, %r)\n"
                "from romp_load import load_source\n"
                "jd = load_source('romp_judge_child', %r)\n"
                "chk = jd.state_root_mode_check()\n"
                "print(json.dumps({'step': jd._STATE_ROOT_REPAIR_STEP, 'rec': jd._STATE_ROOT_REPAIR_ERROR,\n"
                "                  'verdict': chk['verdict'], 'importErr': chk['importRepairError'],\n"
                "                  'refusal': chk['importRefusal']}))\n"
                % (HERE, os.path.join(BIN, "romp-judge")))
        r = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, timeout=180)
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(out["step"], "mkdir", "a mkdir that could not run is labelled mkdir, not chmod")
        self.assertTrue(out["rec"].startswith("EACCES") or out["rec"].startswith("EPERM"), out["rec"])
        self.assertEqual(out["verdict"], "unknown", "the root was never created: its mode cannot be read")
        self.assertIn("mkdir failed at import", out["importErr"])
        self.assertIsNone(out["refusal"], "nothing was read at import: the current read (unknown) decides")

    def test_a_pre_existing_root_that_read_writable_by_another_is_an_import_refusal_whatever_the_chmod_did(self):
        """THE IMPORT-READ RULE at the judge: a pre-existing 0777 root this uid owns, no chmod interposed. The import's
        chmod tightens it (the root reads 0700 now, the check's verdict is ok), and the dict still carries importRefusal
        with the distrust remedy, since the window in which the root was writable is what the rule is about. The judge
        module started (a CLI must); the kernel's gates exit on the dict (TheImportGateComesFirst). With the chmod
        refused the refusal says so and the root stays 0777. The root HELD AN ENTRY at the read (round 4: an empty root is
        a creation default, the next test). At 9748684d3 the child faults on the missing attribute (exit 1)."""
        root, out, err = self._child("os.mkdir(root)\nos.chmod(root, 0o777)\nopen(os.path.join(root, 'planted'), 'w').close()\n")
        self.assertEqual(out["atImport"], 0o777)
        self.assertIs(out["empty"], False, "the root held an entry at the import's read")
        self.assertEqual(out["modeNow"], 0o700, "the import's chmod ran")
        self.assertEqual(_mode(root), 0o700)
        self.assertEqual(out["verdict"], "ok", "the current read is fine; the rule is about the read before the chmod")
        self.assertIsNotNone(out["refusal"])
        self.assertEqual(out["refusalCause"], "other")
        self.assertIn("read 0777 at import (writable by other local users: an other write bit), re-tightened to 0700 by the "
                      "import's chmod", out["refusal"])
        self.assertIn("entries planted while it was writable are not to be trusted", out["refusal"])
        self.assertIn("%s under %s, or recreate the root, then chmod 700 it" % (DISTRUST, root), out["refusal"])
        self.assertEqual([l for l in err.splitlines() if "state root" in l], [], "the judge says nothing: the root reads 0700; the kernel's gate speaks")
        setup = ("os.mkdir(root)\nos.chmod(root, 0o777)\nopen(os.path.join(root, 'planted'), 'w').close()\nreal = os.chmod\n"
                 "def refuse(path, mode, *a, **k):\n"
                 "    if os.path.realpath(str(path)) == os.path.realpath(root):\n"
                 "        raise PermissionError(1, 'chmod refused (interposed)')\n"
                 "    return real(path, mode, *a, **k)\n"
                 "os.chmod = refuse\n")
        root2, out2, _err2 = self._child(setup)
        self.assertEqual(out2["verdict"], "refuse", "the current read refuses too")
        self.assertIn("and the import's chmod failed (EPERM", out2["refusal"], "the refusal says what the chmod did")
        self.assertEqual(_mode(root2), 0o777)

    def test_an_empty_pre_existing_root_is_a_creation_default_whoever_made_it(self):
        """THE CREATION EXEMPTION, re-keyed (round 4, correctness-3 of round 3): a pre-existing 0777 root that held NO
        entry at the import's read is what another romp tool made a moment ago at the umask's mode (the manager's
        mkdirSync, the CLI's mkdir -p, a harness's makedirs), and nothing could have been planted in an empty directory,
        so importEmpty is True, importRefusal is None, the import's chmod tightens it and nothing is said. Before round 4
        the exemption keyed on THIS process's mkdir, so this root filed the loud distrust row on the ordinary first boot."""
        root, out, err = self._child("os.mkdir(root)\nos.chmod(root, 0o777)\n")
        self.assertEqual(out["atImport"], 0o777)
        self.assertIs(out["empty"], True)
        self.assertFalse(out["created"], "pre-existing: another tool made it")
        self.assertIsNone(out["refusal"], "empty at the read: a creation default, not a window")
        self.assertEqual(out["verdict"], "ok")
        self.assertEqual(_mode(root), 0o700)
        self.assertEqual([l for l in err.splitlines() if "state root" in l], [])

    def test_a_file_at_the_root_path_is_refused_with_enotdir_and_never_chmoded(self):
        """regression-1 of round 3 (I): a state root path that exists and is NOT A DIRECTORY. The judge import's mkdir
        meets EEXIST, which is recorded (step mkdir), the file is never chmod'ed 0700 (a 0700 file at the root path would
        be the import's own doing), and the check's verdict is refuse with statErrno ENOTDIR and its own remedy (remove
        it and recreate the root as a directory), at every check. At 9748684d3 the EEXIST was dropped and the verdict
        read ok, err None, line None."""
        root, out, err = self._child("open(root, 'w').close()\nos.chmod(root, 0o644)\n")
        self.assertEqual(out["step"], "mkdir")
        self.assertTrue(out["rec"].startswith("EEXIST"), out["rec"])
        self.assertEqual(out["verdict"], "refuse")
        self.assertEqual(out["statErrno"], "ENOTDIR")
        self.assertTrue(out["notDir"])
        self.assertIn("is not a directory", out["remedy"])
        self.assertIn("recreate the root as a directory", out["remedy"])
        self.assertEqual(_mode(root), 0o644, "the file's mode is untouched: no chmod 700 on a file")
        self.assertIsNone(out["refusal"], "the import-read rule is about directories; ENOTDIR is the current read's refusal")

    def test_a_root_the_import_created_has_no_import_refusal_whatever_its_umask_mode(self):
        """The exemption: the judge module's own mkdir made the root at the umask's mode (0775 under 002, 0777 under 000);
        nothing could have been planted in a directory that did not exist a moment before, so importCreated is True and
        importRefusal None even for a 0777 creation default. At 9748684d3 the child faults on the missing attribute
        (exit 1)."""
        root, out, err = self._child("os.umask(0o000)\n")
        self.assertTrue(out["created"])
        self.assertEqual(out["atImport"], 0o777, "the umask's creation default, read before the chmod")
        self.assertIsNone(out["refusal"], "a root the import created is exempt")
        self.assertEqual(out["verdict"], "ok")
        self.assertEqual(_mode(root), 0o700)


# ── the kernel-side shared harness ───────────────────────────────────────────────────────────────────────────────

class _KernelState(unittest.TestCase):
    """Save and restore every module-level piece the arms touch, give each test a fresh 0700 root as the state root, and
    replace the runtime exit with a raising double so a refusal is observable in-process rather than killing the runner.
    import_facts() plants what the judge module recorded at import (the pre-chmod mode, its owner and group, whether the
    import created the root, a failed call), so the REAL boot check computes the import-read rule from them."""

    def setUp(self):
        self.saved_state = jd.STATE
        self.saved_mode, self.saved_key = km._STATE_ROOT_MODE, km._STATE_ROOT_KEY
        self.saved_refused = km._STATE_ROOT_REFUSED
        self.saved_exit = km._state_root_exit
        self.saved_rows = list(km._SYNC_NOTICES)
        self.saved_seq = km._SYNC_SEQ
        self.saved_env = os.environ.get("ROMP_STATE_ROOT_CHECK_S")
        self.saved_repo_err = km._REPO_ROOT_WRITE_ERROR
        self.saved_import = (jd._STATE_ROOT_MODE_AT_IMPORT, jd._STATE_ROOT_IDS_AT_IMPORT, jd._STATE_ROOT_CREATED_AT_IMPORT,
                             jd._STATE_ROOT_REPAIR_STEP, jd._STATE_ROOT_REPAIR_ERROR, jd._STATE_ROOT_EMPTY_AT_IMPORT)
        self.saved_pending = list(km._READER_REFUSED_PENDING)
        self.saved_refused_reads = (list(km._gr.refused), list(jd._gr.refused), list(em._gr.refused))
        self.saved_sys_path = list(sys.path)
        km._STATE_ROOT_MODE, km._STATE_ROOT_KEY, km._STATE_ROOT_REFUSED = None, None, False
        km._REPO_ROOT_WRITE_ERROR = None
        km._READER_REFUSED_PENDING[:] = []
        km._gr.refused[:] = []; jd._gr.refused[:] = []; em._gr.refused[:] = []
        km._SYNC_NOTICES[:] = []
        self.exits = []
        km._state_root_exit = self._exit_double
        self.root = tempfile.mkdtemp()                    # mkdtemp creates 0700 whatever the umask
        Path(self.root, "session-hosts").write_text("off\n")   # a minted root writes off before a kernel is bound to it (regression-6)
        jd._rebind_state(Path(self.root))
        self.import_facts(0o700)                          # a clean baseline: pytest imports every collected module before any test
        #                                                    runs, and a later module's judge re-execution leaves ITS root's pre-chmod
        #                                                    read (0775 under the umask) in the globals; a test plants what it needs
        for hooks in (jd.READER_REFUSED_HOOKS, em.READER_REFUSED_HOOKS, srm.REFUSED_HOOKS):   # ...and a judge re-executed after the kernel
            if km._reader_refused_row not in hooks:            # loaded holds a fresh hook list without the kernel's row hook: put it back
                hooks.append(km._reader_refused_row)           # (srm.REFUSED_HOOKS: the handed-root modules' per-call readers file there)
        self.patcher = None

    def _exit_double(self, code):
        self.exits.append(code)
        raise _Exited(code)

    def tearDown(self):
        if self.patcher is not None:
            self.patcher.stop()
        try:
            os.chmod(self.root, 0o700)                    # the hygiene sweep must be able to remove it
        except OSError:
            pass
        jd._rebind_state(self.saved_state)
        (jd._STATE_ROOT_MODE_AT_IMPORT, jd._STATE_ROOT_IDS_AT_IMPORT, jd._STATE_ROOT_CREATED_AT_IMPORT,
         jd._STATE_ROOT_REPAIR_STEP, jd._STATE_ROOT_REPAIR_ERROR, jd._STATE_ROOT_EMPTY_AT_IMPORT) = self.saved_import
        km._READER_REFUSED_PENDING[:] = self.saved_pending
        km._gr.refused[:], jd._gr.refused[:], em._gr.refused[:] = self.saved_refused_reads
        sys.path[:] = self.saved_sys_path
        km._STATE_ROOT_MODE, km._STATE_ROOT_KEY = self.saved_mode, self.saved_key
        km._STATE_ROOT_REFUSED = self.saved_refused
        km._REPO_ROOT_WRITE_ERROR = self.saved_repo_err
        km._state_root_exit = self.saved_exit
        km._SYNC_NOTICES[:] = self.saved_rows
        km._SYNC_SEQ = self.saved_seq
        if self.saved_env is None:
            os.environ.pop("ROMP_STATE_ROOT_CHECK_S", None)
        else:
            os.environ["ROMP_STATE_ROOT_CHECK_S"] = self.saved_env

    def import_facts(self, mode, created=False, chmod_failed=False, ids="root", empty=False):
        """What the judge module recorded at import, planted: the pre-chmod `mode` of the test's root (its real owner and
        group unless `ids` is given), whether the import `created` it, whether the root was `empty` at that read (the
        creation exemption's key since round 4; False here means it held entries), and a failed import chmod."""
        jd._STATE_ROOT_MODE_AT_IMPORT = mode
        jd._STATE_ROOT_IDS_AT_IMPORT = _ids(self.root) if ids == "root" else ids
        jd._STATE_ROOT_CREATED_AT_IMPORT = created
        jd._STATE_ROOT_EMPTY_AT_IMPORT = bool(empty or created)
        if chmod_failed:
            jd._STATE_ROOT_REPAIR_STEP, jd._STATE_ROOT_REPAIR_ERROR = "chmod 700", "EPERM: %s" % os.strerror(1)
        else:
            jd._STATE_ROOT_REPAIR_STEP, jd._STATE_ROOT_REPAIR_ERROR = None, None

    def interpose(self):
        """os.chmod refuses the root from here to tearDown (or until release())."""
        self.patcher = mock.patch("os.chmod", new=_refusing_chmod(self.root))
        self.patcher.start()

    def release(self):
        if self.patcher is not None:
            self.patcher.stop()
            self.patcher = None

    def rows(self):
        return [r["text"] for r in km._SYNC_NOTICES]

    def refused_rows(self):
        return [r for r in km._SYNC_NOTICES if r["kind"] == "refused"]


# ── REFUSE AT BOOT (the two doors agree), and WARN at boot ────────────────────────────────────────────────────────

class Boot(_KernelState):
    """_state_root_boot_check, called from main() right after check_boot_environment and BEFORE any thread starts. What
    the refuse/unknown arm does to everything that is not the door: it raises SystemExit(2) in the MAIN thread, so
    _ensure_bundles, the reconcile, and every loop thread below it in main() never run. What the warn arm does: files
    one row and one line and lets the boot go on, starting every thread as before. The boot applies THE SAME TWO READS
    as the import gate (_state_root_refusal): the current read by the discriminator, and the import-read rule on what
    the judge module read before its chmod (planted here through import_facts, then computed by the real check). At
    9748684d3 the boot refuses on `mode & 0o022` of the current read alone and BOOTS a root that read 0777 at import
    (one loud row); checked against a detached worktree of that commit."""

    def test_a_root_writable_by_others_stops_the_boot_with_exit_2_and_the_line(self):
        os.chmod(self.root, 0o777)
        self.interpose()
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            with self.assertRaises(SystemExit) as cm:
                km._state_root_boot_check()
        self.assertEqual(cm.exception.code, 2)
        line = err.getvalue()
        self.assertIn(self.root, line, "names the root")
        self.assertIn("0777", line, "names the mode read back")
        self.assertIn("an other write bit", line, "and which bit")
        self.assertIn(DISTRUST, line, "the remedy distrusts the contents")
        self.assertIn("did NOT start", line)
        self.assertEqual(self.exits, [], "SystemExit in main(), not the runtime os._exit double")
        self.assertEqual(_mode(self.root), 0o777, "read, not healed (the chmod was refused)")

    def test_a_group_writable_root_under_a_shared_group_stops_the_boot_and_under_the_private_group_warns(self):
        """The discriminator on the boot's current read, through the real path (grp and pwd patched for the block): 0775
        under a group with another member exits 2 naming the shared group; the same 0775 under the owner's private group
        is a warn (re-tightened and filed, the boot goes on). At 9748684d3 both exit 2."""
        os.chmod(self.root, 0o775)
        err = io.StringIO()
        with _patched_lookups(_fakes(members=["peer-a"])), contextlib.redirect_stderr(err):
            with self.assertRaises(SystemExit) as cm:
                km._state_root_boot_check()
        self.assertEqual(cm.exception.code, 2)
        self.assertIn("is shared: 1 other member", err.getvalue())
        self.assertIn(DISTRUST, err.getvalue())
        self.assertEqual(_mode(self.root), 0o700, "the check's chmod ran after the read; the refusal stood on the read")
        os.chmod(self.root, 0o775)
        km._STATE_ROOT_MODE, km._STATE_ROOT_KEY = None, None
        err = io.StringIO()
        with _patched_lookups(_fakes()), contextlib.redirect_stderr(err):
            chk = km._state_root_boot_check()
        self.assertEqual(chk["verdict"], "warn")
        self.assertTrue(chk["groupPrivate"])
        self.assertEqual(_mode(self.root), 0o700, "re-tightened")
        rows = [r["text"] for r in self.refused_rows()]
        self.assertEqual(len(rows), 1, rows)
        self.assertIn("0775", rows[0])
        self.assertIn("re-tightened to 0700", rows[0])
        self.assertNotIn(DISTRUST, rows[0])
        self.assertIn("owner's private group", err.getvalue())

    def test_a_lookup_failure_on_the_boots_read_stops_the_boot_with_the_lookup_remedy(self):
        os.chmod(self.root, 0o775)
        err = io.StringIO()
        with _patched_lookups(_fakes(fail=KeyError("gid"))), contextlib.redirect_stderr(err):
            with self.assertRaises(SystemExit) as cm:
                km._state_root_boot_check()
        self.assertEqual(cm.exception.code, 2)
        self.assertIn("the group database could not be read (KeyError", err.getvalue())
        self.assertIn(LOOKUP_REMEDY, err.getvalue())
        self.assertNotIn(DISTRUST, err.getvalue(), "the distinct remedy, never the distrust one")

    def test_an_unreadable_root_stops_the_boot_with_exit_2(self):
        """The UNKNOWN decision (the review's section E): unverified defaults to the restricted side, so a root whose
        mode cannot be read exits at boot exactly like a writable one. A stat on a local directory does not fail
        transiently; ENOENT means the root was removed, and continuing would re-create it under a parent someone else
        may own."""
        gone = os.path.join(self.root, "gone")
        jd._rebind_state(Path(gone))
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            with self.assertRaises(SystemExit) as cm:
                km._state_root_boot_check()
        self.assertEqual(cm.exception.code, 2)
        self.assertIn("could not be read", err.getvalue())
        self.assertIn("unverified root is not served from", err.getvalue())
        self.assertIn("ENOENT", err.getvalue())

    def test_main_runs_the_boot_check_right_after_the_credential_check_and_before_any_thread(self):
        import inspect
        src = inspect.getsource(km.main)
        i_cred, i_root, i_thread = (src.index("jd._cred.check_boot_environment()"), src.index("_state_root_boot_check()"),
                                    src.index("threading.Thread("))
        self.assertLess(i_cred, i_root)
        self.assertLess(i_root, i_thread)

    def test_the_import_gate_precedes_the_token_load_in_the_module_body(self):
        """correctness-4 / fresh-2, the source half (the execution half is TheImportGateComesFirst): the import gate's
        call statement sits above the TOKEN assignment and the _persist_repo_root() call in the module body, so no read
        of the root's contents precedes it. Read from the module's AST statements (not a text scan, whose match would
        land in the gate's own docstring, which quotes both)."""
        import ast
        tree = ast.parse(inspect_getsource_module())
        pos = {}
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "_STATE_ROOT_IMPORT_CHECK" for t in node.targets):
                pos["gate"] = node.lineno
            if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "TOKEN" for t in node.targets):
                pos.setdefault("token", node.lineno)
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call) \
                    and getattr(node.value.func, "id", None) == "_persist_repo_root":
                pos.setdefault("repo", node.lineno)
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call) \
                    and getattr(node.value.func, "id", None) == "_load_downtime":
                pos.setdefault("downtime", node.lineno)
        self.assertIn("gate", pos)
        self.assertLess(pos["gate"], pos["token"], "the gate statement runs before the serve token is read")
        self.assertLess(pos["gate"], pos["repo"], "and before repo-root is written")
        self.assertLess(pos["gate"], pos["downtime"], "and before the first read of an entry under the root (the enumeration's item 1)")

    def test_a_root_not_0700_but_not_writable_by_others_files_one_row_and_boots(self):
        os.chmod(self.root, 0o755)
        self.interpose()                                   # else the repair tightens it and the verdict is ok
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            chk = km._state_root_boot_check()
        self.assertEqual(chk["verdict"], "warn")
        rows = [r["text"] for r in self.refused_rows()]
        self.assertEqual(len(rows), 1, rows)
        self.assertIn("0755", rows[0])
        self.assertIn("EPERM", rows[0])
        self.assertEqual(err.getvalue().count("state root"), 1, err.getvalue())
        v = km._version_info()["stateRootMode"]
        self.assertEqual(v["verdict"], "warn")
        self.assertEqual(v["modeRead"], "0755")
        self.assertIn("EPERM", v["err"])
        self.assertIsInstance(v["checkedAt"], int)
        self.assertNotIn(self.root, json.dumps(v), "/version is auth-exempt: no filesystem path (its contract)")
        self.assertIn("the state root", v["remedy"])
        # the first runtime pass after the boot sees the same warn: no second row for it
        os.environ["ROMP_STATE_ROOT_CHECK_S"] = "0"
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(km._state_root_verdict(time.time()), "warn")
        self.assertEqual(len(self.refused_rows()), 1, "one row per transition, and the boot's check was the previous state")

    def test_the_import_pre_chmod_mode_is_a_warn_transition_at_boot(self):
        """The 2026-09-20 review's item 2, last clause: a root the import READ looser than 0700 (0755: writable by nobody
        else) and re-tightened to 0700 is reported at boot as its own warn-class transition (loud, not fatal), so a
        loosening that happened while romp was down leaves a trace. The check itself reads ok now, but the import's
        pre-chmod mode is a fact the boot line and row carry."""
        self.import_facts(0o755)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            out = km._state_root_boot_check()
        self.assertEqual(out["verdict"], "ok")
        self.assertIsNone(out["importRefusal"])
        self.assertIn("read 0755 at import", err.getvalue())
        self.assertIn("re-tightened to 0700", err.getvalue())
        rows = [r["text"] for r in self.refused_rows()]
        self.assertTrue(any("read 0755 at import" in r for r in rows), rows)

    def test_a_pre_existing_root_that_read_0775_under_the_private_group_at_import_boots_with_one_row(self):
        """The round-2b row, kept under the discriminator: a pre-existing root that read 0775 at import under the owner's
        private group (what every harness root reads on this box until the judge import tightens it) BOOTS, with one
        stderr line and one refused-kind row naming the private group and the fact, and NOT the distrust remedy (no
        other account could write through that group). The row fits the bell with the remedy whole. At 9748684d3 the
        dict has no importRefusal (KeyError) and the row reads "(writable by other local users)" with the distrust remedy."""
        self.import_facts(0o775)
        err = io.StringIO()
        with _patched_lookups(_fakes()), contextlib.redirect_stderr(err):
            out = km._state_root_boot_check()
        self.assertEqual(out["verdict"], "ok", "the root reads 0700 now")
        self.assertIsNone(out["importRefusal"], "a private group's write bit is not another user's")
        line = err.getvalue()
        self.assertEqual(line.count("state root"), 1, "one line:\n" + line)
        self.assertIn("read 0775 at import (a group write bit under the owner's private group", line)
        self.assertIn("re-tightened to 0700", line)
        self.assertNotIn(DISTRUST, line)
        self.assertNotIn("did NOT start", line, "loud, not fatal")
        rows = [r["text"] for r in self.refused_rows()]
        self.assertEqual(len(rows), 1, rows)
        self.assertIn("read 0775 at import (a group write bit under the owner's private group), re-tightened to 0700", rows[0])
        self.assertIn("Find what made or loosened the state root while romp was down", rows[0], "the remedy, path-free, whole")
        self.assertLessEqual(len(rows[0]), km.SYNC_NOTICE_FIT)
        v = km._version_info()["stateRootMode"]
        self.assertEqual((v["verdict"], v["modeRead"]), ("ok", "0700"))
        os.environ["ROMP_STATE_ROOT_CHECK_S"] = "0"
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(km._state_root_verdict(time.time()), "ok")
        self.assertEqual(len(self.refused_rows()), 1, "the first runtime pass files no second row for the import fact")

    def test_a_pre_existing_root_that_read_writable_by_another_at_import_stops_the_boot_with_the_distrust_remedy(self):
        """THE IMPORT-READ RULE at the boot door (the two doors agree): the judge module read 0777 at import on a
        pre-existing root and its chmod tightened it (the root reads 0700 now, the current read is ok), and the boot
        REFUSES on the import read: SystemExit(2), the line naming the read, the chmod and the distrust remedy, no row
        filed (the process is stopping), every thread below it in main() never started. At 9748684d3 the same facts
        boot with one loud row ("re-tightened to 0700" and the old remedy): "SystemExit not raised" there."""
        self.import_facts(0o777)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            with self.assertRaises(SystemExit) as cm:
                km._state_root_boot_check()
        self.assertEqual(cm.exception.code, 2)
        line = err.getvalue()
        self.assertIn("read 0777 at import (writable by other local users: an other write bit), re-tightened to 0700 by the "
                      "import's chmod", line)
        self.assertIn("entries planted while it was writable are not to be trusted", line)
        self.assertIn("%s under %s, or recreate the root, then chmod 700 it" % (DISTRUST, self.root), line)
        self.assertIn("did NOT start", line)
        self.assertEqual(self.refused_rows(), [], "no row: the process is stopping")
        self.assertEqual(self.exits, [], "SystemExit in main(), not the runtime double")
        self.assertEqual(_mode(self.root), 0o700, "the current root is untouched (it was 0700 already)")
        # the same read under a SHARED group, and one whose lookup fails: refused, the latter with the lookup remedy
        for fakes, expect, absent in ((_fakes(members=["peer-a"]), "is shared: 1 other member", LOOKUP_REMEDY),
                                      (_fakes(fail=OSError(errno.EIO, "io")), "could not be read (EIO", DISTRUST)):
            km._STATE_ROOT_MODE, km._STATE_ROOT_KEY = None, None
            self.import_facts(0o775)
            err = io.StringIO()
            with _patched_lookups(fakes), contextlib.redirect_stderr(err):
                with self.assertRaises(SystemExit) as cm:
                    km._state_root_boot_check()
            self.assertEqual(cm.exception.code, 2)
            self.assertIn("read 0775 at import", err.getvalue())
            self.assertIn(expect, err.getvalue())
            self.assertNotIn(absent, err.getvalue(), "one remedy each: the distrust one, or the lookup one")

    def test_a_writable_root_the_import_could_not_tighten_refuses_at_boot_on_the_current_read(self):
        """Both reads refuse and the CURRENT read's line is the one said (it carries this check's own errno and the
        import's failed call, labelled): a root whose import chmod FAILED still reads 0777; the import fact files no
        separate row and builds no import-mode row."""
        os.chmod(self.root, 0o777)
        self.interpose()
        self.import_facts(0o777, chmod_failed=True)
        chk = jd.state_root_mode_check()
        self.assertIsNone(km._state_root_import_mode_row(chk), "the import's chmod failed: nothing was re-tightened")
        self.assertIsNotNone(chk["importRefusal"])
        self.assertIn("and the import's chmod failed (EPERM", chk["importRefusal"]["line"])
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            with self.assertRaises(SystemExit) as cm:
                km._state_root_boot_check()
        self.assertEqual(cm.exception.code, 2)
        self.assertIn("is mode 0777, writable by other local users (an other write bit)", err.getvalue(), "the current read's line")
        self.assertIn("chmod 700 failed at import: EPERM", err.getvalue(), "with the import's failed call, labelled")
        self.assertIn("did NOT start", err.getvalue())
        self.assertEqual(self.refused_rows(), [])

    def test_a_root_the_import_created_at_the_umasks_mode_is_neither_a_warning_nor_a_refusal(self):
        """The exemption: the judge module's own mkdir made the root, so the mode it read before its chmod is the
        umask's creation default (0775 under a group-writable umask, 0777 under umask 0), not a loosening, and nothing
        could have been planted in a directory that did not exist a moment before. No exit, no row, no line. tests-3 of
        round 3: the created fact is planted here (True), where before no test set it."""
        for created_mode in (0o775, 0o777):
            km._STATE_ROOT_MODE, km._STATE_ROOT_KEY = None, None
            self.import_facts(created_mode, created=True)
            self.assertTrue(jd._STATE_ROOT_CREATED_AT_IMPORT)
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                out = km._state_root_boot_check()
            self.assertEqual(out["verdict"], "ok")
            self.assertTrue(out["importCreated"])
            self.assertIsNone(out["importRefusal"], "%04o" % created_mode)
            self.assertEqual(err.getvalue(), "")
            self.assertEqual(self.refused_rows(), [])
            self.assertIsNone(km._state_root_import_mode_row(out))

    def test_a_root_that_was_empty_at_the_imports_read_boots_silently_whoever_made_it(self):
        """THE CREATION EXEMPTION RE-KEYED (round 4; correctness-3 and tests-7 of round 3): a PRE-EXISTING root (not this
        process's mkdir) that read 0777 or 0775 at import and held NO entry is a creation default, whoever made it: no
        refusal, no row, no line, the boot goes on. Before round 4 the same facts filed the loud distrust row and told the
        operator to delete a serve token the manager minted seconds earlier. The same root WITH an entry refuses (the
        previous test): the difference is the entry, not the maker."""
        for imp_mode in (0o777, 0o775):
            km._STATE_ROOT_MODE, km._STATE_ROOT_KEY = None, None
            self.import_facts(imp_mode, created=False, empty=True)
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                out = km._state_root_boot_check()
            self.assertEqual(out["verdict"], "ok", "%04o" % imp_mode)
            self.assertIs(out["importEmpty"], True)
            self.assertFalse(out["importCreated"], "another tool made it")
            self.assertIsNone(out["importRefusal"])
            self.assertEqual(err.getvalue(), "", "silent: nothing was planted in an empty directory")
            self.assertEqual(self.refused_rows(), [])
            self.assertIsNone(km._state_root_import_mode_row(out))

    def test_repo_root_is_written_by_a_rename_that_replaces_a_planted_entry(self):
        """fresh-1's second half (round 2): repo-root is published by a temp and os.replace, the token mint's shape, so
        a planted entry at the path (a symlink pointing outside the root, a file this uid cannot open) is REPLACED
        rather than written through or left standing; the link's target is untouched."""
        target = Path(tempfile.mkdtemp(), "elsewhere")
        target.write_text("attacker-planted\n")
        os.symlink(target, os.path.join(self.root, "repo-root"))
        with contextlib.redirect_stderr(io.StringIO()):
            km._persist_repo_root()
        self.assertFalse(os.path.islink(os.path.join(self.root, "repo-root")), "the link itself was replaced")
        self.assertEqual(Path(self.root, "repo-root").read_text(), str(km.ROOT) + "\n")
        self.assertEqual(target.read_text(), "attacker-planted\n", "nothing was written through the link")
        self.assertIsNone(km._REPO_ROOT_WRITE_ERROR)
        plant = Path(self.root, "repo-root")
        plant.write_text("/nonexistent/bogus-repo\n")
        plant.chmod(0o444)                                    # a plant this uid cannot open for writing
        with contextlib.redirect_stderr(io.StringIO()):
            km._persist_repo_root()
        self.assertEqual(plant.read_text(), str(km.ROOT) + "\n", "replaced by the rename, not skipped")
        self.assertEqual(_mode(plant), 0o600)

    def test_a_failed_repo_root_write_is_said_with_its_errno_and_filed_at_boot(self):
        real = os.replace

        def refuse(src, dst, *a, **k):
            if os.path.basename(str(dst)) == "repo-root":
                raise PermissionError(13, "denied (interposed)")
            return real(src, dst, *a, **k)
        err = io.StringIO()
        with mock.patch("os.replace", new=refuse), contextlib.redirect_stderr(err):
            km._persist_repo_root()
        self.assertIn("repo-root", err.getvalue())
        self.assertIn("EACCES", err.getvalue(), "the errno name")
        self.assertNotIn("interposed", err.getvalue(), "built from the errno, never the exception's text")
        self.assertTrue(km._REPO_ROOT_WRITE_ERROR.startswith("EACCES"), km._REPO_ROOT_WRITE_ERROR)
        self.assertEqual([p for p in os.listdir(self.root) if p.startswith("repo-root")], [], "no temp left behind")
        with contextlib.redirect_stderr(io.StringIO()):
            km._state_root_boot_check()
        rows = [r["text"] for r in self.refused_rows()]
        self.assertEqual(len(rows), 1, rows)
        self.assertIn("repo-root", rows[0])
        self.assertIn("EACCES", rows[0])
        self.assertLessEqual(len(rows[0]), km.SYNC_NOTICE_FIT)

    def test_a_reader_refusal_parked_at_import_is_filed_at_boot(self):
        """The kernel-side row for a guarded reader's refusal made before _sync_notice existed (the import-time readers:
        the downtime log, the memo files, pending-ops.json, the checkpoints directory, the sdkvenv): parked in
        _READER_REFUSED_PENDING by the reader's hook, and filed by the boot check as one refused-kind row that fits the
        bell, naming the entry relative to the root and the reason. At 9748684d3 there is no reader, no hook and no row."""
        km._READER_REFUSED_PENDING.append((os.path.join(self.root, "checkpoints"), "symlink", "the reader's stderr line"))
        with contextlib.redirect_stderr(io.StringIO()):
            chk = km._state_root_boot_check()
        self.assertEqual(chk["verdict"], "ok")
        rows = [r["text"] for r in self.refused_rows()]
        self.assertEqual(len(rows), 1, rows)
        self.assertTrue(rows[0].startswith("State root entry checkpoints was a symlink: quarantined and read as absent; nothing "
                                           "planted is adopted."), rows[0])
        self.assertLessEqual(len(rows[0]), km.SYNC_NOTICE_FIT)
        self.assertLessEqual(rows[0].count(self.root), 1)
        self.assertEqual(km._READER_REFUSED_PENDING, [], "filed, not left parked")
        for reason, what in (("owner", "not this uid's"), ("writable", "writable by another local user"),
                             ("lookup", "the group database could not describe")):
            row = km._state_root_reader_row("/some/where/very/long/" * 12 + "entry.json", reason)
            self.assertIn(what, row)
            self.assertLessEqual(len(row), km.SYNC_NOTICE_FIT, "a long path costs the quarantine path on the row, never the point")

    def test_a_0700_root_files_nothing(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            chk = km._state_root_boot_check()
        self.assertEqual(chk["verdict"], "ok")
        self.assertEqual(self.refused_rows(), [])
        self.assertEqual(err.getvalue(), "")
        v = km._version_info()["stateRootMode"]
        self.assertEqual((v["verdict"], v["modeRead"], v["err"]), ("ok", "0700", None))
        self.assertFalse(v["repaired"])

    def test_version_says_unchecked_before_any_check(self):
        v = km._version_info()["stateRootMode"]
        self.assertEqual(v["verdict"], "unchecked")
        self.assertEqual(set(v), {"verdict", "modeRead", "modeAfter", "repaired", "err", "importRepairError",
                                  "remedy", "checkedAt"})
        self.assertNotIn("refusingSince", v, "no latch in round 2: nothing 'refuses since'")


# ── REFUSE AT RUNTIME: the exit, from the jobs road and under concurrency ────────────────────────────────────────

class TheRuntimeRefusalExits(_KernelState):
    """_state_root_verdict is the runtime arm. What the refuse/unknown verdict does to everything that is not the check:
    it hands the whole process to _state_root_exit_now, which in production is os._exit(2) (here the double). A verdict
    read once and cached answers without a re-read inside the interval, so an ordinary request never pays a stat. The
    discriminator applies here too: a loosening to 0775 under a shared group exits, under the private group warns. At
    84b27dd39 there is no _state_root_verdict (AttributeError); at 9748684d3 the shared-group arm is a TypeError-free
    refuse and the private-group arm exits (`mode & 0o022`)."""

    def test_a_loosened_root_found_at_runtime_exits_the_process(self):
        with contextlib.redirect_stderr(io.StringIO()):
            km._state_root_boot_check()                    # ok on the 0700 root
        os.environ["ROMP_STATE_ROOT_CHECK_S"] = "0"
        os.chmod(self.root, 0o777)
        self.interpose()
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            with self.assertRaises(_Exited) as cm:
                km._state_root_verdict(time.time(), "a request")
        self.assertEqual(cm.exception.code, 2)
        self.assertEqual(self.exits, [2], "exactly one exit(2)")
        self.assertTrue(km._STATE_ROOT_REFUSED)
        self.assertIn("0777", err.getvalue())
        self.assertIn("romp stops now", err.getvalue())
        self.assertIn("found by a request", err.getvalue())

    def test_a_group_loosening_is_judged_by_the_discriminator_at_runtime(self):
        with contextlib.redirect_stderr(io.StringIO()):
            km._state_root_boot_check()
        os.environ["ROMP_STATE_ROOT_CHECK_S"] = "0"
        os.chmod(self.root, 0o775)
        with _patched_lookups(_fakes()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(km._state_root_verdict(time.time(), "the housekeeping pass"), "warn", "the private group: warn, re-tightened")
        self.assertEqual(self.exits, [])
        self.assertEqual(_mode(self.root), 0o700)
        self.assertEqual(len(self.refused_rows()), 1)
        os.chmod(self.root, 0o775)
        err = io.StringIO()
        with _patched_lookups(_fakes(primaries=1)), contextlib.redirect_stderr(err):
            with self.assertRaises(_Exited):
                km._state_root_verdict(time.time(), "the housekeeping pass")
        self.assertEqual(self.exits, [2], "a shared group: the exit")
        self.assertIn("1 other account with it as its primary group", err.getvalue())

    def test_an_unreadable_root_found_at_runtime_exits_the_process(self):
        with contextlib.redirect_stderr(io.StringIO()):
            km._state_root_boot_check()
        os.environ["ROMP_STATE_ROOT_CHECK_S"] = "0"
        gone = self.root + ".away"
        os.rename(self.root, gone)                         # the root path is gone: os.stat fails ENOENT
        self.addCleanup(lambda: os.path.isdir(gone) and os.rename(gone, self.root))
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            with self.assertRaises(_Exited):
                km._state_root_verdict(time.time(), "the housekeeping pass")
        self.assertEqual(self.exits, [2])
        self.assertIn("could not be read", err.getvalue())
        self.assertIn("unverified root is not served from", err.getvalue())

    def test_a_file_at_the_root_path_found_at_runtime_exits_the_process_with_enotdir(self):
        """regression-1 of round 3 (I) at the runtime check: the root is replaced by a FILE at its path; the check's
        verdict is refuse with ENOTDIR (never ok, never a chmod 700 on the file) and the process exits."""
        with contextlib.redirect_stderr(io.StringIO()):
            km._state_root_boot_check()
        os.environ["ROMP_STATE_ROOT_CHECK_S"] = "0"
        gone = self.root + ".away"
        os.rename(self.root, gone)
        Path(self.root).write_text("not a directory\n")
        os.chmod(self.root, 0o644)
        self.addCleanup(lambda: (os.path.isfile(self.root) and os.unlink(self.root), os.path.isdir(gone) and os.rename(gone, self.root)))
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            with self.assertRaises(_Exited):
                km._state_root_verdict(time.time(), "the housekeeping pass")
        self.assertEqual(self.exits, [2])
        self.assertIn("ENOTDIR", err.getvalue())
        self.assertIn("is not a directory", err.getvalue())
        self.assertIn("recreate the root as a directory", err.getvalue())
        self.assertEqual(_mode(self.root), 0o644, "no chmod 700 on a file at the root's path")

    def test_a_raising_check_exits_the_process_with_the_traceback_said_once(self):
        with contextlib.redirect_stderr(io.StringIO()):
            km._state_root_boot_check()
        os.environ["ROMP_STATE_ROOT_CHECK_S"] = "0"
        err = io.StringIO()
        with mock.patch.object(jd, "state_root_mode_check", side_effect=RuntimeError("boom (interposed)")):
            with contextlib.redirect_stderr(err):
                with self.assertRaises(_Exited):
                    km._state_root_verdict(time.time())
        self.assertEqual(self.exits, [2], "a check that raises is unverified: the process exits")
        self.assertIn("RuntimeError", err.getvalue())
        self.assertNotIn("interposed", err.getvalue().split("Traceback")[0], "the verdict line carries the type name, not the text")
        self.assertEqual(err.getvalue().count("Traceback (most recent call last)"), 1, "the traceback said once, before the exit")

    def test_the_interval_gates_the_recheck(self):
        os.environ.pop("ROMP_STATE_ROOT_CHECK_S", None)
        self.assertEqual(km._state_root_check_interval(), 15.0)
        self.assertEqual(km.STATE_ROOT_CHECK_S, 15.0)
        os.environ["ROMP_STATE_ROOT_CHECK_S"] = "not-a-number"
        self.assertEqual(km._state_root_check_interval(), 15.0)
        os.environ["ROMP_STATE_ROOT_CHECK_S"] = "3600"
        with contextlib.redirect_stderr(io.StringIO()):
            km._state_root_boot_check()
        os.chmod(self.root, 0o777)
        self.interpose()
        now = time.time()
        self.assertEqual(km._state_root_verdict(now), "ok", "inside the interval the cache answers, no re-read")
        self.assertEqual(self.exits, [])
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(_Exited):
                km._state_root_verdict(now + 3601)          # past it the mode is re-read
        self.assertEqual(self.exits, [2])

    def test_two_roads_take_the_exit_once(self):
        """tests-4, the concurrency the re-check rests on: two threads driving _state_root_verdict with a refuse check
        under interval 0 both re-read, but the exit is taken exactly ONCE (the first finder sets the flag under the lock)
        and the second finder never RETURNS a verdict to its caller (it raises _StateRootExiting, round 2), so no request
        or stage runs on under the hostile root while the first finder's line is in flight. Without the flag both would
        call os._exit; without the raise the second road got "refuse" back and carried on."""
        with contextlib.redirect_stderr(io.StringIO()):
            km._state_root_boot_check()
        os.environ["ROMP_STATE_ROOT_CHECK_S"] = "0"
        os.chmod(self.root, 0o777)
        self.interpose()
        real_check = jd.state_root_mode_check

        def slow(*a, **k):
            time.sleep(0.05)                                # widen the window both threads race
            return real_check(*a, **k)
        got = []
        with mock.patch.object(jd, "state_root_mode_check", side_effect=slow):
            with contextlib.redirect_stderr(io.StringIO()):
                def drive():
                    try:
                        got.append(km._state_root_verdict(time.time()))
                    except _Exited:
                        got.append("exited")
                    except km._StateRootExiting:
                        got.append("parked")
                ts = [threading.Thread(target=drive) for _ in range(2)]
                for t in ts:
                    t.start()
                for t in ts:
                    t.join(5)
        self.assertFalse(any(t.is_alive() for t in ts))
        self.assertEqual(len(self.exits), 1, "the exit is taken once, not per road: %r" % self.exits)
        self.assertTrue(km._STATE_ROOT_REFUSED)
        self.assertEqual(sorted(got), ["exited", "parked"], "no road got a verdict string back: %r" % got)


class TheWritersStopUnderARefusal(_KernelState):
    """extra5-1 / extra5-2, the HIGH that decided round 1: a runtime refusal must stop the WRITERS, not only the doors.
    What the refuse verdict does to the housekeeping pass it is the first stage of: the exit propagates through the
    pass's own `except Exception` guards (it is a BaseException), so NO later stage in the pass runs: not the sweeps,
    not the persists, not clearDoneNotes. In production os._exit stops the pusher, the judges and the timers by the same
    mechanism (the process is gone). At 84b27dd39 the stage does not exist, and every later stage runs under the loose
    root."""

    def test_the_jobs_pass_runs_no_later_stage_once_the_first_stage_refuses(self):
        with contextlib.redirect_stderr(io.StringIO()):
            km._state_root_boot_check()
        os.environ["ROMP_STATE_ROOT_CHECK_S"] = "0"
        os.chmod(self.root, 0o777)
        self.interpose()
        with mock.patch.object(km, "_lift_spent_awaiting") as lift, \
             mock.patch.object(km, "_clear_done_working_notes") as clear, \
             mock.patch.object(km, "_death_sweep_tick") as death:
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(_Exited):
                    km._jobs_pass(int(time.time()), {})
        self.assertEqual(self.exits, [2], "the pass exited at its first stage")
        lift.assert_not_called()
        death.assert_not_called()
        clear.assert_not_called()

    def test_the_stage_is_first_and_is_a_pass_job(self):
        import inspect
        src = inspect.getsource(km._jobs_pass)
        self.assertIn("_job_stage('stateRootMode', lambda: _state_root_verdict(now", src)
        self.assertLess(src.index("stateRootMode"), src.index("liftSpentAwaiting"), "first in the pass")
        self.assertIn("stateRootMode", km._PerfStats.PASS_JOBS)
        self.assertEqual(km._PerfStats.PASS_JOBS[0], "stateRootMode", "and first in the census")


class TheRequestRoadExits(_KernelState):
    """The Handler's road (round 2 of the review): every method runs _state_root_recheck FIRST, before the token gate and
    before any route, so a request that finds the root hostile exits the process from its own thread and answers
    nothing. Pinned by execution against a live km.Handler (tests/test_kernel_cors.py's ThreadingHTTPServer shape),
    one request per method: the exit double fires exactly once, the line says the road ("found by a request"), and no
    answer of any kind was built (send_response never ran, _authorize never ran): the client sees the connection drop.
    The double is a BaseException, so it propagates out of the handler thread (the server thread's traceback on stderr
    is expected); the assertion is on self.exits. With any one of the four call sites removed, that method answers."""

    def setUp(self):
        super().setUp()
        self.saved_hook = threading.excepthook            # the double leaving the handler thread is the expected outcome, not noise
        threading.excepthook = lambda a: None if a.exc_type in (_Exited, km._StateRootExiting) else self.saved_hook(a)
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), km.Handler)
        self.port = self.srv.server_address[1]
        self.t = threading.Thread(target=self.srv.serve_forever, daemon=True)
        self.t.start()
        with contextlib.redirect_stderr(io.StringIO()):
            km._state_root_boot_check()                    # ok on the 0700 root
        os.environ["ROMP_STATE_ROOT_CHECK_S"] = "0"
        os.chmod(self.root, 0o777)
        self.interpose()

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        threading.excepthook = self.saved_hook
        super().tearDown()

    def _request(self, method, path):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            conn.request(method, path, body=b"{}" if method == "POST" else None,
                         headers={"X-Romp-Token": km.TOKEN, "Content-Type": "application/json"})
            r = conn.getresponse()
            r.read()
            return r.status
        except (http.client.RemoteDisconnected, http.client.BadStatusLine, ConnectionResetError):
            return None
        finally:
            conn.close()

    def test_every_method_exits_before_the_token_gate_and_every_route(self):
        for method, path in (("GET", "/healthz"), ("HEAD", "/healthz"), ("POST", "/nudge"), ("OPTIONS", "/nudge")):
            km._STATE_ROOT_REFUSED, km._STATE_ROOT_MODE = False, None
            self.exits[:] = []
            err = io.StringIO()
            with mock.patch.object(km.Handler, "send_response") as answered, \
                 mock.patch.object(km.Handler, "_authorize") as authorized, \
                 contextlib.redirect_stderr(err):
                status = self._request(method, path)
                for _ in range(100):                          # the handler thread's exit lands after the socket drops
                    if self.exits:
                        break
                    time.sleep(0.05)
            self.assertIsNone(status, "%s %s: the connection dropped, no answer (got %r)" % (method, path, status))
            self.assertEqual(self.exits, [2], "%s %s: the process exit, exactly once" % (method, path))
            self.assertIn("found by a request", err.getvalue(), method)
            self.assertIn("0777", err.getvalue(), method)
            answered.assert_not_called()
            authorized.assert_not_called()

    def test_a_second_finder_on_the_request_road_answers_nothing(self):
        """tests-1 of round 3, the pin that can red: the exit is already on its way (_STATE_ROOT_REFUSED set by a first
        finder whose stderr write is in flight), and a request arrives. Its re-check finds the same refuse verdict and is
        the SECOND finder: _state_root_exit_now raises _StateRootExiting, a BaseException, which passes through
        _state_root_recheck's `except Exception` and the handler's own guards, so the thread ends and NOTHING is
        answered: send_response never runs. The one-token mutation of _StateRootExiting's base to Exception is caught
        by _state_root_recheck's guard, the request is routed and the client is served under the hostile root; this pin
        reds on it (send_response called), where the module's other tests stayed green (verified by mutation in a scratch
        copy of the tree)."""
        for method, path in (("GET", "/healthz"), ("POST", "/nudge")):
            km._STATE_ROOT_REFUSED, km._STATE_ROOT_MODE = True, None    # a first finder is exiting; the cache is stale
            self.exits[:] = []
            err = io.StringIO()
            with mock.patch.object(km.Handler, "send_response") as answered, \
                 mock.patch.object(km.Handler, "_authorize") as authorized, \
                 contextlib.redirect_stderr(err):
                status = self._request(method, path)
                time.sleep(0.3)                                # the handler thread's end lands after the socket drops
            self.assertIsNone(status, "%s %s: no answer (got %r)" % (method, path, status))
            self.assertEqual(self.exits, [], "%s: a second finder takes no exit of its own (the first finder's is in flight)" % method)
            answered.assert_not_called()
            authorized.assert_not_called()


class TheSocketRoadHonoursAnExitAlreadyTaken(_KernelState):
    """tests-6 of round 3, pinned (the round-4 review found the contract stated and the guard in place, but no test): a
    client frame on an ALREADY-OPEN WebSocket runs its op with no read of the root's mode of its own (the check is the
    request road's, before the upgrade, and the jobs road's), and what the socket road holds is the exit already taken:
    once a finder set _STATE_ROOT_REFUSED, a frame that arrives while that finder's line is in flight runs NOTHING
    (_dispatch_ws never runs; _StateRootExiting ends the handler thread as it ends a second finder's). Driven against a
    live km.Handler: the socket is upgraded on the 0700 root (the request road's check passes), the flag is then set as a
    first finder would set it, and one decoded text frame is sent. With the guard removed (`if False and
    _STATE_ROOT_REFUSED:`) the frame is dispatched under the hostile root and this pin reds; verified by mutation in a
    scratch copy of the tree. The control: with the flag clear the same frame reaches _dispatch_ws once."""

    def setUp(self):
        super().setUp()
        self.saved_hook = threading.excepthook            # the BaseException leaving the handler thread is the expected outcome
        threading.excepthook = lambda a: None if a.exc_type in (_Exited, km._StateRootExiting) else self.saved_hook(a)
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), km.Handler)
        self.port = self.srv.server_address[1]
        self.t = threading.Thread(target=self.srv.serve_forever, daemon=True)
        self.t.start()
        with contextlib.redirect_stderr(io.StringIO()):
            km._state_root_boot_check()                    # ok on the 0700 root: the upgrade's own recheck passes on the cache
        self.socks = []

    def tearDown(self):
        for s in self.socks:
            s.close()
        self.srv.shutdown()
        self.srv.server_close()
        threading.excepthook = self.saved_hook
        super().tearDown()

    def _open(self):
        """One raw upgrade with the token; the socket, after the 101."""
        key = base64.b64encode(os.urandom(16)).decode()
        req = ("GET /ws?app=chat&token=%s HTTP/1.1\r\nHost: 127.0.0.1:%d\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
               "Sec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n\r\n" % (km.TOKEN, self.port, key)).encode()
        s = socket.create_connection(("127.0.0.1", self.port), timeout=5)
        self.socks.append(s)
        s.sendall(req)
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = s.recv(4096)
            if not chunk:
                break
            buf += chunk
        self.assertIn(b" 101 ", buf.split(b"\r\n", 1)[0], buf[:200])
        return s

    @staticmethod
    def _frame(obj):
        payload = json.dumps(obj).encode()
        assert len(payload) < 126
        return bytes([0x81, len(payload)]) + payload       # one text frame, FIN set (the kernel's reader accepts an unmasked client frame)

    def test_a_frame_on_an_open_socket_runs_nothing_once_the_exit_is_taken(self):
        with mock.patch.object(km.Handler, "_dispatch_ws") as dispatched, contextlib.redirect_stderr(io.StringIO()):
            s = self._open()
            km._STATE_ROOT_REFUSED = True                  # a first finder is exiting; its line is in flight
            s.sendall(self._frame({"type": "ready"}))
            time.sleep(0.5)
            dispatched.assert_not_called()
            self.assertEqual(self.exits, [], "the socket road takes no exit of its own: the first finder's is in flight")
        # the control: with no exit taken, the same frame runs its op once
        km._STATE_ROOT_REFUSED = False
        with mock.patch.object(km.Handler, "_dispatch_ws") as dispatched, contextlib.redirect_stderr(io.StringIO()):
            s = self._open()
            s.sendall(self._frame({"type": "ready"}))
            for _ in range(100):
                if dispatched.called:
                    break
                time.sleep(0.05)
            dispatched.assert_called_once()
            self.assertEqual(dispatched.call_args[0][0], {"type": "ready"})
            self.assertEqual(self.exits, [])


# ── WARN: one row per transition, the bell's kind, the fit ───────────────────────────────────────────────────────

class TheWarnSurface(_KernelState):
    """What a warn row does to the OTHER bell kinds and to the bell's width. It rides _sync_notice under kind "refused"
    (extra7-1: not the mutable "sdk" kind of _sdk_problem, whose one mute would hide a security row with a backend
    error), one row per transition keyed on the cause so an errno flap under a constant mode refiles (extra6-2), and it
    is built to fit SYNC_NOTICE_FIT whole with the remedy first and the root's path at most once (extra7-2). At
    84b27dd39 there is no _state_root_verdict (AttributeError); at 9748684d3 the fit test's new shapes (the shared
    group, the lookup failure, the private-group warn, the private-group import row) are TypeErrors or absent."""

    def _serving_warn(self, mode=0o755):
        with contextlib.redirect_stderr(io.StringIO()):
            km._state_root_boot_check()
        os.environ["ROMP_STATE_ROOT_CHECK_S"] = "0"
        os.chmod(self.root, mode)
        self.interpose()

    def test_three_checks_one_row_and_a_second_loosening_is_a_second_transition(self):
        self._serving_warn(0o755)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            for _ in range(3):
                self.assertEqual(km._state_root_verdict(time.time()), "warn")
        self.assertEqual(len(self.refused_rows()), 1, self.rows())
        self.assertIn("0755", self.refused_rows()[0]["text"])
        self.assertEqual(err.getvalue().count("state root"), 1, "and one stderr line")
        # a return to plain ok says nothing
        self.release()
        os.chmod(self.root, 0o700)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(km._state_root_verdict(time.time()), "ok")
        self.assertEqual(len(self.refused_rows()), 1, "a return to ok files no row")
        # a second loosening, to a different mode, is a second transition
        os.chmod(self.root, 0o750)
        self.interpose()
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(km._state_root_verdict(time.time()), "warn")
            self.assertEqual(km._state_root_verdict(time.time()), "warn")
        self.assertEqual(len(self.refused_rows()), 2, "a second loosening is a second transition")
        self.assertIn("0750", self.refused_rows()[1]["text"])

    def test_an_errno_flap_under_a_constant_mode_refiles(self):
        """extra6-2: the transition key carries the cause, so a chmod errno that changes (EPERM to EACCES) under one
        constant warn mode is a new transition and files a second row, rather than the error centre naming a stale
        cause while /version's err changes underneath it."""
        self._serving_warn(0o755)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(km._state_root_verdict(time.time()), "warn")   # EPERM (the interposed chmod)
        self.assertEqual(len(self.refused_rows()), 1)
        self.release()
        real = os.chmod

        def eacces(path, mode, *a, **k):
            if os.path.realpath(str(path)) == os.path.realpath(self.root):
                raise PermissionError(13, "denied (interposed)")
            return real(path, mode, *a, **k)
        os.chmod(self.root, 0o755)
        self.patcher = mock.patch("os.chmod", new=eacces)
        self.patcher.start()
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(km._state_root_verdict(time.time()), "warn")   # EACCES now, same 0755
        self.assertEqual(len(self.refused_rows()), 2, "the cause changed: a second row")
        self.assertIn("EACCES", self.refused_rows()[1]["text"])

    def test_every_row_fits_the_bell_with_the_remedy_first_and_the_path_at_most_once(self):
        """extra7-2, pinned against a long synthetic root so the length-is-doubled-path failure cannot hide behind a
        short test root: every row a check can file fits SYNC_NOTICE_FIT, leads with the point and the path-free remedy,
        and names the root at most once (a long root costs the path on the row, never the way out). Fourteen shapes after
        round 4: the four interposed modes (0775 and 0770 now under the private group), 0700 with a failed chmod, unknown,
        two self-owned repaired, the raise row, the boot's two import-mode rows, and round 4's three: a shared-group
        refusal, a lookup-failure refusal and a private-group warn that stands."""
        longroot = "/home/someone/.local/state/romp-profiles/a-research-kernel-with-a-very-long-name-indeed/romp"
        gid = os.stat(tempfile.gettempdir()).st_gid          # _stat_as answers with the temp dir's owner and group
        private = _fakes(gid=gid)
        cases = []
        for mode in (0o755, 0o750, 0o777, 0o770):
            with mock.patch("os.chmod", new=_refusing_chmod(longroot)), mock.patch("os.stat", new=_stat_as(longroot, mode)):
                cases.append(jd.state_root_mode_check(longroot, **private))
        # a 0700-with-failed-chmod, and an unknown, both over the long root
        with mock.patch("os.chmod", new=_refusing_chmod(longroot)), mock.patch("os.stat", new=_stat_as(longroot, 0o700)):
            cases.append(jd.state_root_mode_check(longroot))
        with mock.patch("os.stat", new=_stat_missing(longroot)):
            cases.append(jd.state_root_mode_check(longroot))
        # the self-owned repaired shapes (0755 warn, 0777 refuse) over the long root: the check's chmod runs and succeeds,
        # so the read-back after it is 0700
        for mode in (0o755, 0o777):
            with mock.patch("os.chmod"), mock.patch("os.stat", new=_stat_then(longroot, mode, 0o700)):
                chk = jd.state_root_mode_check(longroot)
                self.assertTrue(chk["repaired"], "%04o" % mode)
                cases.append(chk)
        # round 4's shapes: a shared group (refuse), a lookup failure (refuse), the private-group warn standing
        with mock.patch("os.chmod", new=_refusing_chmod(longroot)), mock.patch("os.stat", new=_stat_as(longroot, 0o775)):
            cases.append(jd.state_root_mode_check(longroot, **_fakes(members=["peer-a"], primaries=2, gid=gid)))
            cases.append(jd.state_root_mode_check(longroot, **_fakes(fail=KeyError("gid"), gid=gid)))
            cases.append(jd.state_root_mode_check(longroot, **private))
        self.assertEqual([c["verdict"] for c in cases[-3:]], ["refuse", "refuse", "warn"])
        # the raise row (_state_root_unknown_check) over the long root
        saved = jd.STATE
        jd._rebind_state(Path(longroot))
        try:
            cases.append(km._state_root_unknown_check("RuntimeError", time.time()))
        finally:
            jd._rebind_state(saved)
        rows = [(chk, km._state_root_row(chk), None) for chk in cases]
        # the boot's import-mode row, built exactly as _state_root_boot_check builds it (the row nearest the cut)
        with mock.patch("os.chmod"), mock.patch("os.stat", new=_stat_as(longroot, 0o700)):
            base = jd.state_root_mode_check(longroot)
        for imp_mode in (0o755, 0o775):
            imp_chk = dict(base, importModeRead=imp_mode, importCreated=False, importRefusal=None, modeRead=0o700)
            imp = km._state_root_import_mode_row(imp_chk)
            self.assertIsNotNone(imp, "the boot files a row for a root that read %04o at import" % imp_mode)
            line, point, bell = imp
            rows.append((imp_chk, km._state_root_row(imp_chk, point=point, remedy=bell), bell))
        self.assertEqual(len(rows), 14, "every shape a row can take")
        for chk, row, bell in rows:
            self.assertLessEqual(len(row), km.SYNC_NOTICE_FIT, "%r is over the bell: %d" % (chk["verdict"], len(row)))
            self.assertLessEqual(row.count(longroot), 1, "the path appears at most once: %r" % row)
            # the remedy LEADS: it is in the row whole, and before the error clause and the path when either appears
            rem = (bell or chk.get("bellRemedy") or chk["remedyPublic"]).rstrip(".")
            rem = rem[:1].upper() + rem[1:]
            self.assertIn(rem, row, "the remedy is in the row whole: %r" % row)
            for tail in ((" (%s)." % chk["err"]) if chk.get("err") else None, " Root: "):
                if tail and tail in row:
                    self.assertLess(row.index(rem), row.index(tail), "the remedy comes before %r: %r" % (tail, row))

    def test_a_loosened_root_the_check_can_tighten_is_reported_as_retightened(self):
        """tests-4 of round 3: the repaired=True road through _state_root_verdict, with NO chmod interposed. A root this
        uid owns is loosened to 0755 after boot; the runtime check reads warn, its own chmod tightens it, and the row and
        the line say so ("was mode 0755, re-tightened to 0700"), so the loosening leaves a trace. Suppressing the row for
        exactly the repaired case stayed green before this pin, since every kernel-side warn test interposed a chmod
        refusal."""
        with contextlib.redirect_stderr(io.StringIO()):
            km._state_root_boot_check()
        os.environ["ROMP_STATE_ROOT_CHECK_S"] = "0"
        os.chmod(self.root, 0o755)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(km._state_root_verdict(time.time()), "warn", "the verdict is the mode as read")
        self.assertEqual(_mode(self.root), 0o700, "the check's own chmod ran, after the read")
        chk = km._STATE_ROOT_MODE
        self.assertTrue(chk["repaired"])
        rows = [r["text"] for r in self.refused_rows()]
        self.assertEqual(len(rows), 1, rows)
        self.assertIn("0755", rows[0])
        self.assertIn("re-tightened to 0700", rows[0])
        self.assertIn("was mode 0755, re-tightened to 0700", err.getvalue())
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(km._state_root_verdict(time.time()), "ok", "and the next check reads plain ok")
        self.assertEqual(len(self.refused_rows()), 1, "a return to ok files no row")

    def test_the_row_is_filed_under_the_refused_kind(self):
        self._serving_warn(0o755)
        with contextlib.redirect_stderr(io.StringIO()):
            km._state_root_verdict(time.time())
        self.assertEqual([r["kind"] for r in self.refused_rows()], ["refused"])
        self.assertTrue(all(r["kind"] == "refused" for r in km._SYNC_NOTICES if "state root" in r["text"] or "root" in r["text"].lower()))


def _stat_as(target, mode):
    real = os.stat

    def f(p, *a, **k):
        if str(p) == target:
            st = real(tempfile.gettempdir())
            return os.stat_result((stat.S_IFDIR | mode,) + tuple(st)[1:])
        return real(p, *a, **k)
    return f


def _stat_then(target, first, then):
    """os.stat for `target` answering mode `first` on its first call and `then` on every later one: the shape of a root
    the check's own chmod tightened between its read and its read-back."""
    real = os.stat
    calls = []

    def f(p, *a, **k):
        if str(p) == target:
            calls.append(1)
            st = real(tempfile.gettempdir())
            return os.stat_result((stat.S_IFDIR | (first if len(calls) == 1 else then),) + tuple(st)[1:])
        return real(p, *a, **k)
    return f


def _stat_missing(target):
    real = os.stat

    def f(p, *a, **k):
        if str(p) == target:
            raise FileNotFoundError(2, os.strerror(2))
        return real(p, *a, **k)
    return f


# ── REFUSE AT IMPORT: the two reads, proved by execution in a child ──────────────────────────────────────────────

class TheImportGateComesFirst(unittest.TestCase):
    """fresh-1, fresh-2, correctness-4 and round 4's import-read rule, proved by what did and did not happen in a child
    kernel process (never a source index). What the import gate does to the token work and the bundles when it refuses:
    they never run. A pre-existing 0777 root THIS UID OWNS, no chmod interposed, is tightened to 0700 by the judge
    module's import and REFUSED by the gate on what the import read (exit 2, the distrust remedy), so the planted
    symlink at serve-token is never reached: the loader's fault does not appear, the link's target is untouched and the
    link stands for the operator. A 0777 root whose chmod is refused (a foreign owner, a refusing mount: it still reads
    writable) exits 2 on the current read, the same way. A pre-existing 0775 root under the owner's private group imports
    (warn-class; the boot says it); a root the import CREATED imports; a 0700 root imports fine; an unreadable root
    exits 2; a group database that never answers costs the bound, not a hang. At 9748684d3 the self-owned 0777 root
    PASSES the gate (the settled rule of round 2b: the verdict on the mode as read after the chmod), so with the plant
    the child exits 1 on the loader's fault ("1 != 2" here), the blocked-lookup child exits 0 ("0 != 2": no lookup, no
    bound), the chmod-refused root's line reads "(a group or other write bit)", and the 0775, created and 0700 children
    are controls that pass there too: checked against a detached worktree of that commit."""

    def _child(self, plant_symlink, mode, interpose=False, prelude="", plant_file=False):
        root = os.path.join(tempfile.mkdtemp(), "romp")
        if mode is not None:
            os.makedirs(root)
        target = os.path.join(tempfile.mkdtemp(), "elsewhere")
        Path(target).write_text("attacker-planted\n")
        if plant_symlink:
            os.symlink(target, os.path.join(root, "serve-token"))   # the plant the token load would follow
        if plant_file:
            Path(root, "planted.json").write_text("{}\n")            # any entry: the root is not empty at the read
        if mode is not None:
            os.chmod(root, mode)
        env = dict(os.environ)
        env["ROMP_STATE_DIR"] = root
        env.pop("ROMP_SERVE_TOKEN", None)                           # force the token to be read/minted from the root
        env["ROMP_KERNEL_NO_OPEN"] = "1"
        # `interpose`: the shape of a root this uid cannot tighten (a foreign owner, a refusing mount). Without it the root
        # is self-owned and the judge module's import chmod DOES tighten it before the kernel's gate runs; the gate then
        # judges the import's read as well as the current one
        interpose = "" if not interpose else (
            "real = os.chmod\n"
            "def refuse(path, m, *a, **k):\n"
            "    if os.path.realpath(str(path)) == os.path.realpath(root):\n"
            "        raise PermissionError(1, 'chmod refused (interposed)')\n"
            "    return real(path, m, *a, **k)\n"
            "os.chmod = refuse\n")
        code = ("import os, sys, time\n"
                "sys.path.insert(0, %r)\n"
                "from romp_load import load_source\n"
                "root = %r\n"
                "%s%s"
                "load_source('romp_kernel', %r)\n"
                "print('IMPORTED-OK')\n"
                % (HERE, root, prelude, interpose, os.path.join(BIN, "romp-kernel")))
        t0 = time.monotonic()
        r = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, timeout=180)
        r.elapsed = time.monotonic() - t0
        return root, target, r

    def test_a_pre_existing_root_that_read_writable_by_another_exits_2_at_import_whatever_the_chmod_did(self):
        """THE IMPORT-READ RULE by execution: a pre-existing 0777 root this uid owns, a symlink planted at serve-token, no
        chmod interposed. The judge module's import tightens the root (it reads 0700 afterwards), and the gate exits 2 on
        what the import READ, with the distrust remedy, before the token work: the loader's own fault ("symlink") is
        absent, the link stands, its target is untouched, nothing was minted. At 9748684d3 this child exits 1 with the
        loader's fault and the state-root line is absent (the gate passed on the tightened mode)."""
        root, target, r = self._child(plant_symlink=True, mode=0o777)
        self.assertEqual(r.returncode, 2, "the gate's exit 2, not the loader's exit 1:\n%s" % r.stderr)
        self.assertIn("read 0777 at import (writable by other local users: an other write bit), re-tightened to 0700 by the "
                      "import's chmod", r.stderr)
        self.assertIn("entries planted while it was writable are not to be trusted", r.stderr)
        self.assertIn("%s under %s, or recreate the root, then chmod 700 it" % (DISTRUST, root), r.stderr)
        self.assertIn("did NOT start", r.stderr)
        self.assertNotIn("symlink", r.stderr, "the token loader never ran: the gate came first")
        self.assertNotIn("IMPORTED-OK", r.stdout, "the import did not complete")
        self.assertEqual(Path(target).read_text(), "attacker-planted\n", "the planted entry's target is untouched")
        self.assertTrue(os.path.islink(os.path.join(root, "serve-token")), "and the link is still in place: the operator removes it")
        self.assertEqual(_mode(root), 0o700, "the import's chmod ran; the refusal stood on what was read before it")
        self.assertEqual(sorted(os.listdir(root)), ["serve-token"], "nothing was minted or written under the root")

    def test_a_pre_existing_0775_root_under_the_private_group_imports_and_reads_0700(self):
        """The discriminator keeps the suite collectable: a pre-existing 0775 root (what every harness root reads on this
        box before the judge import) under the owner's private group is warn-class, so the gate passes on both reads,
        the token work and the rest of the import run, and the import itself says nothing about the mode (the judge
        module's read-back is 0700); the boot is where the pre-chmod read is reported (Boot, AServedKernelRefusesAtRuntime).
        Skips where this account's primary group is not private (the real database decides in a child)."""
        if not _private_group_here():
            raise unittest.SkipTest("this account's primary group is shared on this box: 0775 is a refusal here")
        root, target, r = self._child(plant_symlink=False, mode=0o775)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("IMPORTED-OK", r.stdout)
        self.assertNotIn("did NOT start", r.stderr)
        self.assertNotIn("state root", r.stderr, "nothing said at import: the boot says it")
        self.assertEqual(_mode(root), 0o700)
        self.assertTrue(os.path.exists(os.path.join(root, "serve-token")), "a token was minted under the now-tight root")

    def test_a_root_the_import_created_imports_whatever_the_umask(self):
        """The exemption by execution: no root before the child; the judge module's mkdir makes it at the umask's mode
        (0777 under umask 0 here, the loosest creation default) and the import goes on, since nothing could have been
        planted in a directory that did not exist. At 9748684d3 the same child passes too (a control)."""
        root, target, r = self._child(plant_symlink=False, mode=None, prelude="os.umask(0o000)\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("IMPORTED-OK", r.stdout)
        self.assertNotIn("state root", r.stderr)
        self.assertEqual(_mode(root), 0o700)

    def test_a_writable_root_whose_chmod_is_refused_exits_2_the_same_way(self):
        root, target, r = self._child(plant_symlink=True, mode=0o777, interpose=True)
        self.assertEqual(r.returncode, 2, "the import gate exits 2:\n%s" % r.stderr)
        self.assertIn("is mode 0777, writable by other local users (an other write bit)", r.stderr, "the current read's line")
        self.assertIn("EPERM", r.stderr, "with the chmod's errno")
        self.assertIn("did NOT start", r.stderr)
        self.assertNotIn("serve token", r.stderr.lower(), "the token work never ran")
        self.assertEqual(Path(target).read_text(), "attacker-planted\n")
        self.assertEqual(_mode(root), 0o777, "the chmod was refused: read, not healed")

    def test_a_group_lookup_that_blocks_does_not_hang_the_import(self):
        """THE BOUND by execution: grp.getgrgid patched to never answer before the loads (the shared module resolves it at
        call time), a pre-existing 0775 root that holds an entry (an empty one is a creation default and needs no
        judgment), the production bound (3 s). The import gate's import-read judgment needs the group, waits the bound,
        counts the lookup as failed and exits 2 with the lookup message and remedy, never the distrust one, a few seconds
        after the load; the daemon thread left in the lookup does not hold the process (the child returns). At 9748684d3
        there is no lookup and no bound: the child exits 0 (the root imports)."""
        prelude = ("import grp\n"
                   "def never(gid):\n"
                   "    time.sleep(600)\n"
                   "grp.getgrgid = never\n")
        root, target, r = self._child(plant_symlink=False, mode=0o775, prelude=prelude, plant_file=True)
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("read 0775 at import (a group write bit), re-tightened to 0700 by the import's chmod, and the group "
                      "database could not be read (timeout: the group database did not answer within 3 s)", r.stderr)
        self.assertIn(LOOKUP_REMEDY, r.stderr)
        self.assertNotIn(DISTRUST, r.stderr)
        self.assertIn("did NOT start", r.stderr)
        self.assertLess(r.elapsed, 120, "the child returned: the bound, not a hang (%.1fs)" % r.elapsed)

    def test_an_empty_pre_existing_writable_root_imports_silently_whoever_made_it(self):
        """THE CREATION EXEMPTION by execution (round 4; correctness-3 of round 3): a pre-existing 0777 root with NOTHING
        in it, made by another tool (this test) a moment before the child imports. The judge import reads 0777 and an
        empty listing, tightens the root, and the gate passes silently: no distrust line, no exit, the import completes
        and mints its token under the now-tight root. Before round 4 this child exited 2 with the distrust remedy."""
        root, target, r = self._child(plant_symlink=False, mode=0o777)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("IMPORTED-OK", r.stdout)
        self.assertNotIn("state root", r.stderr, "nothing said: an empty root at the umask's mode is a creation default")
        self.assertNotIn(DISTRUST, r.stderr)
        self.assertEqual(_mode(root), 0o700)
        self.assertTrue(os.path.exists(os.path.join(root, "serve-token")))

    def test_a_file_at_the_root_path_exits_2_with_enotdir(self):
        """regression-1 of round 3 (I) at the import gate: a FILE where the root should be. The judge import's mkdir meets
        EEXIST (recorded), the file is not chmod'ed, and the gate exits 2 on the check's ENOTDIR verdict with its remedy,
        before the token work (which would have died on the token's ENOTDIR under a remedy that could not work)."""
        parent = tempfile.mkdtemp()
        root = os.path.join(parent, "romp")
        Path(root).write_text("not a directory\n")
        os.chmod(root, 0o644)
        env = dict(os.environ)
        env["ROMP_STATE_DIR"] = root
        env.pop("ROMP_SERVE_TOKEN", None)
        code = ("import sys\n"
                "sys.path.insert(0, %r)\n"
                "from romp_load import load_source\n"
                "load_source('romp_kernel', %r)\n"
                "print('IMPORTED-OK')\n"
                % (HERE, os.path.join(BIN, "romp-kernel")))
        r = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, timeout=180)
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("ENOTDIR", r.stderr)
        self.assertIn("exists and is not a directory", r.stderr)
        self.assertIn("recreate the root as a directory", r.stderr)
        self.assertIn("did NOT start", r.stderr)
        self.assertNotIn("serve token", r.stderr.lower(), "the gate came before the token work")
        self.assertNotIn("not 0700", r.stderr, "the judge's import diagnostic names ENOTDIR, not a loose mode (the round-4 review)")
        self.assertIn("romp-judge: state root %s exists and is not a directory (ENOTDIR)" % root, r.stderr)
        self.assertEqual(_mode(root), 0o644, "the file was never chmod'ed 0700")

    def test_a_0700_root_imports_fine(self):
        root, target, r = self._child(plant_symlink=False, mode=0o700)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("IMPORTED-OK", r.stdout, "the token work and the rest of the import ran")
        self.assertTrue(os.path.exists(os.path.join(root, "serve-token")), "a token was minted under the tight root")

    def test_an_unreadable_root_exits_2_at_import(self):
        parent = tempfile.mkdtemp()
        root = os.path.join(parent, "romp")
        os.makedirs(root)
        os.chmod(root, 0o700)
        os.chmod(parent, 0o000)                                     # the root cannot be traversed to: stat fails
        self.addCleanup(lambda: os.chmod(parent, 0o700))
        env = dict(os.environ)
        env["ROMP_STATE_DIR"] = root
        env.pop("ROMP_SERVE_TOKEN", None)
        code = ("import sys\n"
                "sys.path.insert(0, %r)\n"
                "from romp_load import load_source\n"
                "load_source('romp_kernel', %r)\n"
                "print('IMPORTED-OK')\n"
                % (HERE, os.path.join(BIN, "romp-kernel")))
        r = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, timeout=180)
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("unverified root is not served from", r.stderr)


# ── HIGH 1 of the enumeration: the boot sweep refuses a checkpoints entry that is not a real directory ───────────

class TheCheckpointsDirectoryIsGuarded(_KernelState):
    """The enumeration's HIGH 1 under round 4's contract: kernel/event_model.py's checkpoint_sweep runs at kernel import
    (kernel.py, after the gate) and, until round 4, followed a symlink planted at <root>/checkpoints: Path.is_dir and
    glob follow a link, so the sweep opened the directory the link pointed at and unlinked every *.json there that did
    not parse as a checkpoint document with an existing path (measured in the enumeration: a victim file outside the
    root, gone). The guard now sits at _ckpt_dir() itself, ONCE AND CACHED (the judge's _ckpt_dir_guarded is the
    provider every checkpoint door calls; the ruling's C), and every read of a document or sidecar goes through the
    event model's guarded reader: a planted link is QUARANTINED to <root>/quarantine/<stamp>.checkpoints (not left
    standing to be followed again next boot, the ruling's B), one stderr line says so, one refused-kind row is filed,
    and the path reads as absent, so nothing is swept through it and the next write makes a fresh directory of this
    uid's. What the guard does to everything that is not the link: a real directory still sweeps (a control that passes
    at 9748684d3 too); an absent entry is nothing to sweep; a plain FILE of this uid's at the path is not a plant by the
    guard's property (not a symlink, this uid's, not writable by another) and is left where it is. At 9748684d3 the
    in-process arm sweeps both files THROUGH the link ("2 != 0") and the child's victim is gone after the import; the
    round-3 head refused the link but left it in place; checked against a detached worktree of 9748684d3."""

    def setUp(self):
        super().setUp()                                        # a fresh 0700 root, rebound (the judge's provider follows it)
        self.saved_provider, self.saved_root_fn = em._CKPT_DIR_FN, em._STATE_ROOT_FN
        em.set_checkpoint_dir(jd._ckpt_dir_guarded)           # THIS judge's provider and root (a judge loaded under a private name
        em.set_state_root(lambda: jd.STATE)                    #  by another test module may have re-pointed the event model's)
        self.victim_dir = tempfile.mkdtemp()
        self.victim = Path(self.victim_dir, "victim.json")
        self.victim.write_text('{"not": "a checkpoint document"}')
        Path(self.victim_dir, "other.json").write_text("[1, 2, 3]")

    def tearDown(self):
        em.set_checkpoint_dir(self.saved_provider)
        em.set_state_root(self.saved_root_fn)
        super().tearDown()

    def _quarantined(self, root=None):
        q = Path(root or self.root, srm.QUARANTINE_DIR)
        return sorted(p.name for p in q.iterdir()) if q.is_dir() else []

    def test_a_symlinked_checkpoints_directory_is_quarantined_and_the_victim_survives(self):
        link = os.path.join(self.root, "checkpoints")
        os.symlink(self.victim_dir, link)
        self.assertIs(em._CKPT_DIR_FN, jd._ckpt_dir_guarded, "the provider is the judge's guarded checkpoint directory")
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(em.checkpoint_sweep(), 0, "nothing swept through the link")
        self.assertTrue(self.victim.exists(), "the file outside the root survives the sweep")
        self.assertTrue(Path(self.victim_dir, "other.json").exists())
        self.assertFalse(os.path.lexists(link), "the link is gone from the root: quarantined, not left to be followed next boot")
        q = self._quarantined()
        self.assertEqual(len(q), 1, q)
        self.assertTrue(q[0].endswith(".checkpoints"), q[0])
        self.assertTrue(os.path.islink(os.path.join(self.root, srm.QUARANTINE_DIR, q[0])), "moved, not deleted: the evidence stands")
        self.assertEqual(_mode(os.path.join(self.root, srm.QUARANTINE_DIR)), 0o700, "the quarantine directory is 0700")
        self.assertIn("is a symlink: quarantined to", err.getvalue())
        self.assertIn("read as absent; nothing planted is adopted", err.getvalue())
        rows = [r["text"] for r in self.refused_rows()]
        self.assertEqual(len(rows), 1, rows)
        self.assertIn("checkpoints was a symlink: quarantined", rows[0])
        self.assertLessEqual(len(rows[0]), km.SYNC_NOTICE_FIT)
        self.assertIsNone(jd._CKPT_DIR_TRUSTED[0], "nothing trusted is cached for a refused entry")

    def test_a_real_directory_still_sweeps_and_is_trusted_once_and_cached(self):
        real = Path(self.root, "checkpoints")
        real.mkdir()
        Path(real, "stale.json").write_text('{"path": "/nonexistent/file/for/this/checkpoint"}')
        Path(real, "junk.json").write_text("not json")
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(em.checkpoint_sweep(), 2, "both non-documents leave with the sweep")
        self.assertEqual(sorted(p.name for p in real.iterdir()), [])
        self.assertEqual(self._quarantined(), [])
        self.assertTrue(self.victim.exists())
        self.assertEqual(jd._CKPT_DIR_TRUSTED[0], real, "the trusted directory is cached (once, until a rebind)")
        with mock.patch.object(jd._gr, "isdir", side_effect=AssertionError("the guard ran again on a cached directory")):
            self.assertEqual(em._ckpt_dir(), real)
        jd._rebind_state(Path(self.root))
        self.assertIsNone(jd._CKPT_DIR_TRUSTED[0], "a rebind judges the directory afresh")

    def test_a_file_at_checkpoints_and_an_absent_entry_sweep_nothing_and_quarantine_nothing(self):
        plain = Path(self.root, "checkpoints")
        plain.write_text("not a directory")
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(em.checkpoint_sweep(), 0)
        self.assertEqual(plain.read_text(), "not a directory", "a file of this uid's is not a plant: untouched")
        self.assertEqual(self._quarantined(), [])
        plain.unlink()
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(em.checkpoint_sweep(), 0)
        self.assertEqual(self._quarantined(), [], "absent is nothing to sweep and nothing to quarantine")
        self.assertEqual(self.refused_rows(), [])

    def test_the_kernel_import_over_a_root_with_a_planted_link_quarantines_it_and_files_the_row(self):
        """At the real door: a child imports bin/romp-kernel over a 0700 root holding checkpoints -> a directory outside
        the root with a victim *.json; the import completes (nothing else is wrong with the root), the victim survives,
        the link is in the root's quarantine directory, the reader said so on stderr, and the boot check files the
        parked refusal as one refused-kind row naming the entry. At 9748684d3 the victim is deleted by the import."""
        root = os.path.join(tempfile.mkdtemp(), "romp")
        os.makedirs(root)
        os.chmod(root, 0o700)
        Path(root, "session-hosts").write_text("off\n")
        os.symlink(self.victim_dir, os.path.join(root, "checkpoints"))
        env = dict(os.environ)
        env["ROMP_STATE_DIR"] = root
        env["ROMP_KERNEL_NO_OPEN"] = "1"
        code = ("import contextlib, io, json, sys\n"
                "sys.path.insert(0, %r)\n"
                "from romp_load import load_source\n"
                "km = load_source('romp_kernel', %r)\n"
                "err = io.StringIO()\n"
                "with contextlib.redirect_stderr(err):\n"
                "    km._state_root_boot_check()\n"
                "print(json.dumps({'rows': [r['text'] for r in km._SYNC_NOTICES if r['kind'] == 'refused'], 'boot': err.getvalue()}))\n"
                % (HERE, os.path.join(BIN, "romp-kernel")))
        r = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, timeout=180)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(self.victim.exists(), "the victim outside the root survives the kernel import")
        self.assertTrue(Path(self.victim_dir, "other.json").exists())
        self.assertFalse(os.path.lexists(os.path.join(root, "checkpoints")), "the link left the root")
        q = self._quarantined(root)
        self.assertTrue(any(n.endswith(".checkpoints") for n in q), q)
        self.assertIn("checkpoints is a symlink: quarantined to", r.stderr)
        out = json.loads(r.stdout.strip().splitlines()[-1])
        rows = [t for t in out["rows"] if "checkpoints" in t]
        self.assertEqual(len(rows), 1, out["rows"])
        self.assertIn("was a symlink: quarantined and read as absent", rows[0])
        self.assertLessEqual(len(rows[0]), km.SYNC_NOTICE_FIT)


# ── REFUSE AT RUNTIME, behaviourally, in a served child kernel (the failing-before at 84b27dd39) ─────────────────

def _kernel_env(root, dist, port, token):
    env = {k: v for k, v in os.environ.items() if k.startswith("XDG_") or k in ("PATH", "HOME", "LANG", "LC_ALL")}
    env.update(XDG_STATE_HOME=os.path.join(root, "xdg"), CLAUDE_CONFIG_DIR=os.path.join(root, "claude"),
               ROMP_DIST_DIR=dist, ROMP_SERVE_TOKEN=token, ROMP_KERNEL_PORT=str(port), ROMP_KERNEL_NO_OPEN="1",
               ROMP_MANAGER_PORT="1", ROMP_MODEL_CATALOG="off", ROMP_UPDATE_CHECK="off", ROMP_CLAUDE_BIN="/bin/false",
               ROMP_POSTAL_PORT=str(_free_port()), ROMP_POSTAL_PEERS="0", ROMP_POSTAL_CLIENT_ONLY="1",
               ROMP_POSTAL_HERMETIC="1", ROMP_STATE_ROOT_CHECK_S="0")
    return env


class AServedKernelRefusesAtRuntime(unittest.TestCase):
    """The runtime refuse arm, end to end and in-suite (tests-2): a real bin/romp-kernel serves 200 on a hermetic 0700
    root, and once the root is loosened to 0777 the process EXITS 2 with the state-root line within seconds: the
    housekeeping pass or a request finds it, and every writer stops with the process. What it does to everything else:
    the process is gone, so no file under the root is written after the exit. At 84b27dd39 the same spawn keeps serving
    200 after the loosening and never exits. Round 4's arms: a pre-existing 0777 root never serves (exit 2 at import,
    where 9748684d3 served it with one loud line: "unexpectedly None: the kernel exited at import" there), and a
    pre-existing 0775 root under the private group serves with the private-group boot line (where 9748684d3 said
    "writable by other local users" with the distrust remedy); the loosening arms are controls that pass at 9748684d3."""

    def setUp(self):
        self.lab = tempfile.mkdtemp(prefix="romp-srm2-")
        self.root = os.path.join(self.lab, "xdg", "romp")
        for d in (self.root, os.path.join(self.lab, "claude"), os.path.join(self.lab, "dist")):
            os.makedirs(d, exist_ok=True)
        os.chmod(self.root, 0o700)                              # a fresh mkdir is 0775 under a group-writable umask
        Path(self.root, "session-hosts").write_text("off\n")   # a minted root writes off before binding a kernel (regression-6)
        self.port, self.token = _free_port(), "srm2-tok"
        self.klog = os.path.join(self.lab, "kernel.log")
        self.kernel = None

    def tearDown(self):
        if self.kernel and self.kernel.poll() is None:
            self.kernel.kill()
            self.kernel.wait(timeout=10)
        try:
            os.chmod(self.root, 0o700)
        except OSError:
            pass
        shutil.rmtree(self.lab, ignore_errors=True)

    def _spawn(self):
        env = _kernel_env(self.lab, os.path.join(self.lab, "dist"), self.port, self.token)
        self.kernel = subprocess.Popen([os.path.join(BIN, "romp-kernel")], stdout=open(self.klog, "w"),
                                       stderr=subprocess.STDOUT, env=env)

    def _healthz(self):
        try:
            urllib.request.urlopen("http://127.0.0.1:%d/healthz" % self.port, timeout=1)
            return True
        except Exception:
            return False

    def _await_healthz(self):
        for _ in range(120):
            if self.kernel.poll() is not None:
                raise unittest.SkipTest("kernel exited before serving /healthz:\n" + open(self.klog).read()[-800:])
            if self._healthz():
                return
            time.sleep(0.5)
        raise unittest.SkipTest("hermetic kernel never served /healthz here")

    def _await_exit(self, seconds=120):
        """Poll for the child's exit up to `seconds`, True when it exited. 120 s (round 4d): the free-threaded 3.14t CI
        cell runs the child kernel's boot and its housekeeping pass slower than this box's 3.12, and round 4's 30 s
        budget on the two loosening arms ran out there ("unexpectedly None: the kernel exited") with no log to read."""
        for _ in range(int(seconds * 2)):
            if self.kernel.poll() is not None:
                return True
            time.sleep(0.5)
        return False

    def _loosen_until_exit(self, seconds=120):
        """chmod the root 0777 and poll for the kernel's exit up to `seconds`; (exited, re-loosenings). THE SIBLING'S
        REPAIR (round 4d, found on the 3.14t CI cell and again here under load): the kernel's boot starts a daemon thread
        that runs `romp-postal-service ensure` (kernel.py, _ensure_postal_bus), and the bus's import gate READS the root,
        REFUSES a loosened one (exit 2, the distrust remedy, which the kernel logs as "postal bus ensure refused") and
        re-tightens it to 0700 on its way out, read before repair. When the test's chmod lands while that child is
        starting, the bus reads 0777 before the kernel's next housekeeping pass does, and the pass then reads 0700: the
        kernel never saw the loosening and serves on. The kernel's own re-check is this test's subject, so a root found
        0700 again while the kernel lives is loosened again and the count is returned for the assertion message; a
        kernel that exits on a loosening it READ is the claim, and a sibling gate's repair between the chmod and the read
        is the harness's race, not a miss of the kernel's. (What it shows about the product, recorded in the PR's notes:
        a sibling writer's gate can hide a transient loosening from the kernel's cadence, and the bus's refusal is then
        the only trace of it, in the kernel's log.)"""
        os.chmod(self.root, 0o777)
        reloosened = 0
        for _ in range(int(seconds * 4)):
            if self.kernel.poll() is not None:
                return True, reloosened
            try:
                if _mode(self.root) != 0o777:
                    os.chmod(self.root, 0o777)
                    reloosened += 1
            except OSError:
                pass
            time.sleep(0.25)
        return False, reloosened

    def _tail(self, n=1500):
        """The child's captured stdout and stderr (one file), its last `n` characters, for an assertion message."""
        try:
            return open(self.klog).read()[-n:]
        except OSError as e:
            return "(kernel log unreadable: %s)" % e

    def test_a_pre_existing_writable_root_never_serves_the_kernel_exits_2_at_import(self):
        """THE IMPORT-READ RULE end to end: a pre-existing root THIS UID OWNS at 0777, no chmod interposed, planted before
        the spawn. The kernel's judge module tightens it at import and the gate refuses on what was read: exit 2 with the
        distrust remedy, /healthz never answers, the root reads 0700. At 9748684d3 the same kernel SERVED with one loud
        line ("re-tightened to 0700" and the old remedy)."""
        os.chmod(self.root, 0o777)
        self._spawn()
        self._await_exit(120)
        self.assertIsNotNone(self.kernel.poll(), "the kernel exited at import:\n" + self._tail())
        self.assertEqual(self.kernel.returncode, 2, open(self.klog).read()[-800:])
        log = open(self.klog).read()
        self.assertIn("read 0777 at import (writable by other local users: an other write bit), re-tightened to 0700", log)
        self.assertIn("entries planted while it was writable are not to be trusted", log)
        self.assertIn("%s under %s, or recreate the root, then chmod 700 it" % (DISTRUST, self.root), log)
        self.assertIn("did NOT start", log)
        self.assertFalse(self._healthz(), "nothing served")
        self.assertEqual(_mode(self.root), 0o700, "tightened by the import's chmod; refused on what was read before it")

    def test_a_root_that_read_0775_under_the_private_group_at_import_serves_with_the_boot_line(self):
        """The round-2b row's line in a real kernel, under the discriminator: a pre-existing 0775 root under the owner's
        private group is warn-class, so the kernel SERVES, with one boot line naming the private group and the
        re-tightening and NOT the distrust remedy; /version reads ok on the root as it is now. Skips where this account's
        primary group is not private (the real database decides in the child)."""
        if not _private_group_here():
            raise unittest.SkipTest("this account's primary group is shared on this box: 0775 is a refusal here")
        os.chmod(self.root, 0o775)
        self._spawn()
        self._await_healthz()
        log = open(self.klog).read()
        self.assertIn("read 0775 at import (a group write bit under the owner's private group, which no other account holds), "
                      "re-tightened to 0700", log)
        self.assertNotIn(DISTRUST, log)
        self.assertNotIn("did NOT start", log, "loud, not fatal")
        self.assertEqual(log.count("state root"), 1, "one line:\n" + log[-1500:])
        self.assertEqual(_mode(self.root), 0o700, "tightened by the import's chmod")
        v = json.loads(urllib.request.urlopen("http://127.0.0.1:%d/version" % self.port, timeout=3).read())["stateRootMode"]
        self.assertEqual((v["verdict"], v["modeRead"]), ("ok", "0700"))
        self.assertNotIn(self.root, json.dumps(v))

    def test_a_root_that_read_0755_at_import_serves_with_the_import_mode_on_the_boot_line(self):
        """The import's pre-chmod mode plumbing, pinned in a real kernel: a pre-existing 0755 root (a privacy fault, not
        a code-execution one) is re-tightened by the import and reported at boot as a warn-class transition, and the
        kernel serves; /version's stateRootMode reads ok on the root as it is now."""
        os.chmod(self.root, 0o755)
        self._spawn()
        self._await_healthz()
        log = open(self.klog).read()
        self.assertIn("read 0755 at import", log)
        self.assertIn("re-tightened to 0700", log)
        self.assertEqual(_mode(self.root), 0o700)
        v = json.loads(urllib.request.urlopen("http://127.0.0.1:%d/version" % self.port, timeout=3).read())["stateRootMode"]
        self.assertEqual((v["verdict"], v["modeRead"]), ("ok", "0700"))
        self.assertNotIn(self.root, json.dumps(v))

    def test_a_loosened_root_exits_the_kernel_2_with_the_line(self):
        self._spawn()
        self._await_healthz()
        self.assertTrue(self._healthz(), "serving 200 on the 0700 root")
        exited, reloosened = self._loosen_until_exit(120)      # the jobs pass (every 0.5s at interval 0) finds it
        self.assertTrue(exited, "the kernel did not exit on the loosened root within 120 s (re-loosened %d times after a "
                        "sibling gate tightened it); its log tail:\n%s" % (reloosened, self._tail()))
        self.assertEqual(self.kernel.returncode, 2, "exit 2:\n" + self._tail())
        log = open(self.klog).read()
        self.assertIn("writable by other local users", log)
        self.assertIn("romp stops now", log)

    def test_no_file_under_the_root_is_written_after_the_exit(self):
        """extra5-2, behaviourally, with the exit instant sampled FROM THE CHILD (correctness-4 of round 3: a stamp taken
        after the parent saw the process gone trails every write the child could have made, so that pin could not red).
        The child runs bin/romp-kernel under a shim that wraps os._exit to print a wall-clock stamp right before the
        real exit; the parent lists every file under the root whose mtime is after that stamp. Nothing is, because
        os._exit stopped every writer of this process at once and no child of the kernel (a bus, a host) writes under
        this root in the hermetic setup. A writer that outlived the exit (a spawned process still writing, or an exit
        that only latched) would show as a later mtime or as no stamp at all."""
        shim = os.path.join(self.lab, "shim.py")
        Path(shim).write_text(
            "import os, runpy, sys, time\n"
            "real = os._exit\n"
            "def stamped(code):\n"
            "    sys.stderr.write('EXIT-STAMP %%r\\n' %% time.time()); sys.stderr.flush()\n"
            "    real(code)\n"
            "os._exit = stamped\n"
            "sys.argv = [%r]\n"
            "runpy.run_path(%r, run_name='__main__')\n" % (os.path.join(BIN, "romp-kernel"), os.path.join(BIN, "romp-kernel")))
        env = _kernel_env(self.lab, os.path.join(self.lab, "dist"), self.port, self.token)
        self.kernel = subprocess.Popen([sys.executable, shim], stdout=open(self.klog, "w"), stderr=subprocess.STDOUT, env=env)
        self._await_healthz()
        exited, reloosened = self._loosen_until_exit(120)
        self.assertTrue(exited, "the kernel did not exit on the loosened root within 120 s (re-loosened %d times after a "
                        "sibling gate tightened it); its log tail:\n%s" % (reloosened, self._tail()))
        self.assertEqual(self.kernel.returncode, 2, "exit 2:\n" + self._tail())
        log = open(self.klog).read()
        stamps = [float(l.split("EXIT-STAMP", 1)[1]) for l in log.splitlines() if l.startswith("EXIT-STAMP")]
        self.assertEqual(len(stamps), 1, "the child stamped its exit exactly once:\n" + log[-1200:])
        exit_wall = stamps[0]
        os.chmod(self.root, 0o700)                             # so the walk can read the tree
        late = []
        for dirpath, _dirs, files in os.walk(self.root):
            for name in files:
                try:
                    mt = os.stat(os.path.join(dirpath, name)).st_mtime
                except OSError:
                    continue
                if mt > exit_wall:
                    late.append((os.path.relpath(os.path.join(dirpath, name), self.root), mt - exit_wall))
        self.assertEqual(late, [], "no writer ran past the exit instant the child stamped")

    def test_an_empty_pre_existing_writable_root_boots_silently_whoever_made_it(self):
        """THE CREATION EXEMPTION end to end (round 4; correctness-3 of round 3): the root exists at 0777 with NOTHING in
        it when the kernel starts (another tool made it a moment ago). The judge import tightens it, the gates pass on the
        emptiness, the kernel SERVES with no state-root line at all: no distrust remedy, no row, nothing to alarm the
        operator on the ordinary first boot. Before round 4 this kernel exited 2 with the distrust remedy."""
        os.unlink(os.path.join(self.root, "session-hosts"))    # empty: no entry at all (hosts stay off: no session is made here)
        os.chmod(self.root, 0o777)
        self._spawn()
        self._await_healthz()
        log = open(self.klog).read()
        self.assertNotIn("state root", log, "silent:\n" + log[-1500:])
        self.assertNotIn(DISTRUST, log)
        self.assertEqual(_mode(self.root), 0o700, "tightened by the import's chmod")
        v = json.loads(urllib.request.urlopen("http://127.0.0.1:%d/version" % self.port, timeout=3).read())["stateRootMode"]
        self.assertEqual((v["verdict"], v["modeRead"]), ("ok", "0700"))


# ── THE BUS: the second daemon on the same root refuses the same way, by the same code ───────────────────────────

class TheBusSharesTheCheck(unittest.TestCase):
    """romp-manager's word: one implementation imported twice. postal/postal_service.py loads kernel/state_root_mode.py
    by path under the fixed module name the kernel's judge uses, so a process holding both holds ONE module object, and
    the bus carries no copy of the check any more (round 2's reduced copy marked KEEP IN SYNC is gone: a comment is not
    a mechanism). At 9748684d3 the bus has no _srm and defines its own _state_root_mode_check (AttributeError, and the
    source assertions fail)."""

    def test_the_bus_loads_the_same_file_as_the_same_module_object(self):
        ps = load_source("romp_postal_srm_probe", os.path.join(BIN, "romp-postal-service"))
        self.assertIs(ps._srm, srm, "one module object for the kernel's judge and the bus in one process")
        self.assertIs(ps._srm, sys.modules["romp_state_root_mode"])
        self.assertEqual(Path(srm.__file__).resolve(), Path(ROOT, "kernel", "state_root_mode.py").resolve())
        self.assertIs(ps._errno_text, srm.errno_text)

    def test_the_bus_carries_no_copy_of_the_check(self):
        src = open(os.path.join(ROOT, "postal", "postal_service.py"), encoding="utf-8").read()
        self.assertNotIn("def _state_root_mode_check", src, "round 2's reduced copy is gone")
        gate = src[src.index("def _state_root_gate("):src.index('\n_state_root_gate("start", absent_ok=True)')]
        self.assertIn("_srm.check(STATE.parent", gate, "the gate calls the shared check")
        self.assertIn("_srm.import_read_refusal(", gate, "and the shared import-read rule for the start read")
        self.assertNotIn("0o022", gate, "no mask of its own")
        self.assertNotIn('if sys.argv[1:2] == ["serve"]', src[:src.index("def _load_serve_token")],
                         "the gate runs at import in every mode (round 3's E), not under argv serve alone")
        judge = open(os.path.join(ROOT, "kernel", "judge.py"), encoding="utf-8").read()
        self.assertIn('load_source("romp_state_root_mode", HERE / "state_root_mode.py")', judge)
        self.assertIn('"romp_state_root_mode"', src, "the same fixed module name")
        self.assertNotIn("KEEP IN SYNC", src[src.index("the state root's mode (2026-09-20)"):src.index("def _load_state_root_mode")],
                         "nothing in the state-root block is kept in sync by hand")

    def test_the_shared_module_imports_the_standard_library_alone(self):
        import ast
        tree = ast.parse(open(os.path.join(ROOT, "kernel", "state_root_mode.py"), encoding="utf-8").read())
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                names.add(node.module)
        self.assertEqual(names, {"errno", "glob", "grp", "gzip", "os", "pathlib", "pwd", "stat", "sys", "threading", "time"},
                         "stdlib only, nothing from kernel/")


class TheBusRefuses(unittest.TestCase):
    """fresh-3: the postal bus is a second serving daemon on the same state root, kept alive by the kernel. What the
    bus's refusal does to everything that is not the bus: the kernel's _ensure_postal_bus respawns a bus that exits on
    a hostile root until the kernel itself refuses at its import gate (on the same root, first); the CLI and MCP, which
    write nothing under the root, are unaffected. A warn root logs one line and serves. Round 4: the start gate's read
    IS the import-read rule's read, so a pre-existing root read writable by another local user at start exits 2 before
    the serve token under it is read, whatever the gate's own chmod did; a 0775 root under the owner's private group is
    re-tightened, said once and served. Tested in a child bus process with a hermetic root, the way
    tests/test_hermetic_kernel_postal.py spawns it. At 84b27dd39 the bus has no mode check; at 9748684d3 the self-owned
    0777 root is SERVED with one loud line (with the plant, the loader's exit 1 after that line: "1 != 2" here), the
    0775 root's line reads "writable by other local users" with the distrust remedy, and the chmod-refused root's line
    is the old shape ("a group or other write bit"); the 0755, absent, unreadable, loosened and warn arms are controls
    that pass there too."""

    def _bus_env(self, root, port, token="bus-tok"):
        env = {k: v for k, v in os.environ.items() if k in ("PATH", "HOME", "LANG", "LC_ALL")}
        env.update(XDG_STATE_HOME=root, ROMP_POSTAL_PORT=str(port),
                   ROMP_POSTAL_HERMETIC="1", ROMP_POSTAL_PEERS="0", ROMP_POSTAL_IDLE_GRACE="100000",
                   ROMP_POSTAL_POLL="1", ROMP_KERNEL_PORT=str(_free_port()))
        if token:
            env["ROMP_SERVE_TOKEN"] = token          # None: the bus reads or mints the token from the root itself
        return env

    def _serve(self, xdg, port, shim=None, token="bus-tok"):
        """A bus child in serve mode over `xdg`, its log to a temp file; killed and its log removed at cleanup."""
        logf = tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False)
        cmd = [sys.executable, shim] if shim else [sys.executable, os.path.join(BIN, "romp-postal-service"), "serve"]
        proc = subprocess.Popen(cmd, env=self._bus_env(xdg, port, token=token), stdout=logf, stderr=subprocess.STDOUT)
        self.addCleanup(lambda: proc.poll() is None and (proc.kill(), proc.wait(timeout=10)))
        self.addCleanup(lambda: os.unlink(logf.name))
        return proc, logf.name

    def _await_ping(self, proc, port, logname):
        for _ in range(60):
            if self._ping(port):
                return
            if proc.poll() is not None:
                break
            time.sleep(0.25)
        raise unittest.SkipTest("hermetic bus never served /ping here:\n" + open(logname).read()[-600:])

    def _ping(self, port):
        try:
            urllib.request.urlopen("http://127.0.0.1:%d/ping" % port, timeout=1)
            return True
        except Exception:
            return False

    def _chmod_refusing_shim(self, root):
        """A serve invocation that first installs an os.chmod refusing the root alone: the shape of a foreign-owned or
        chmod-refusing mount, where the check's repair cannot run and a warn mode stands."""
        shim = os.path.join(tempfile.mkdtemp(), "shim.py")
        Path(shim).write_text(
            "import os, runpy, sys\n"
            "root = %r\n"
            "real = os.chmod\n"
            "def refuse(path, mode, *a, **k):\n"
            "    if os.path.realpath(str(path)) == os.path.realpath(root):\n"
            "        raise PermissionError(1, 'chmod refused (interposed)')\n"
            "    return real(path, mode, *a, **k)\n"
            "os.chmod = refuse\n"
            "sys.argv = [%r, 'serve']\n"
            "runpy.run_path(%r, run_name='__main__')\n"
            % (root, os.path.join(BIN, "romp-postal-service"), os.path.join(BIN, "romp-postal-service")))
        return shim

    def test_a_pre_existing_root_read_writable_at_start_exits_2_before_the_token_whatever_the_chmod_did(self):
        """THE IMPORT-READ RULE at the bus's start: a pre-existing 0777 root this uid owns with a symlink planted at
        serve-token, no chmod interposed. The start gate reads 0777, its own chmod tightens the root, and the verdict
        stands on the read: exit 2 with the distrust remedy in the kernel's words ("read 0777 at start"), before the
        serve token is read, so the loader's fault ("symlink") is absent; the link stands, its target untouched, nothing
        binds, the root reads 0700. At 9748684d3 the bus said one loud line and went on to the loader, exit 1."""
        xdg = tempfile.mkdtemp()
        root = os.path.join(xdg, "romp")
        os.makedirs(root)
        target = Path(tempfile.mkdtemp(), "elsewhere")
        target.write_text("attacker-planted\n")
        os.symlink(target, os.path.join(root, "serve-token"))
        os.chmod(root, 0o777)
        port = _free_port()
        r = subprocess.run([sys.executable, os.path.join(BIN, "romp-postal-service"), "serve"],
                           env=self._bus_env(xdg, port, token=None), capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 2, "the gate's exit 2, not the loader's exit 1:\n" + r.stderr[-800:])
        self.assertIn("read 0777 at start (writable by other local users: an other write bit), re-tightened to 0700 by the "
                      "start's chmod", r.stderr)
        self.assertIn("entries planted while it was writable are not to be trusted", r.stderr)
        self.assertIn("%s under %s, or recreate the root, then chmod 700 it" % (DISTRUST, root), r.stderr)
        self.assertIn("did NOT start", r.stderr)
        self.assertNotIn("symlink", r.stderr, "the token loader never ran")
        self.assertEqual(target.read_text(), "attacker-planted\n", "the planted entry's target is untouched")
        self.assertTrue(os.path.islink(os.path.join(root, "serve-token")), "and the plant is still there for the operator")
        self.assertEqual(_mode(root), 0o700, "the gate's chmod ran; the refusal stood on what was read")
        self.assertFalse(self._ping(port), "nothing bound")

    def test_a_pre_existing_0775_root_under_the_private_group_at_start_is_retightened_said_once_and_served(self):
        """The discriminator at the bus's start: 0775 under the owner's private group is warn-class, re-tightened by the
        gate's chmod AND said, one line naming the private group and no distrust remedy, and the bus serves; a few polls
        later still one line. Skips where this account's primary group is not private. At 9748684d3 the line reads
        "read 0775 at start (writable by other local users)" with the distrust remedy."""
        if not _private_group_here():
            raise unittest.SkipTest("this account's primary group is shared on this box: 0775 is a refusal here")
        xdg = tempfile.mkdtemp()
        root = os.path.join(xdg, "romp")
        os.makedirs(root)
        os.chmod(root, 0o775)
        port = _free_port()
        proc, logname = self._serve(xdg, port)
        self._await_ping(proc, port, logname)
        self.assertEqual(_mode(root), 0o700, "re-tightened at start")
        time.sleep(2.5)                                        # a few polls (POLL=1)
        self.assertIsNone(proc.poll(), "a root under the private group does not exit the bus")
        said = [l for l in open(logname).read().splitlines() if "state root" in l]
        self.assertEqual(len(said), 1, "one line, at start, not per poll:\n" + "\n".join(said))
        self.assertIn("was mode 0775, re-tightened to 0700 (its group write bit is under the owner's private group", said[0])
        self.assertNotIn(DISTRUST, said[0])

    def test_the_bus_refuses_at_start_on_a_writable_root_whose_chmod_is_refused(self):
        xdg = tempfile.mkdtemp()
        root = os.path.join(xdg, "romp")
        os.makedirs(root)
        Path(root, "session-hosts").write_text("off\n")       # the root holds an entry: the import-read rule's words apply
        os.chmod(root, 0o777)
        port = _free_port()
        r = subprocess.run([sys.executable, self._chmod_refusing_shim(root)],
                           env=self._bus_env(xdg, port), capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 2, r.stderr[-800:])
        self.assertIn("read 0777 at start (writable by other local users: an other write bit), and the start's chmod failed (EPERM",
                      r.stderr)
        self.assertIn("did NOT start", r.stderr)
        self.assertEqual(_mode(root), 0o777, "read, not healed")
        self.assertFalse(self._ping(port), "nothing bound")
        # the same root EMPTY: the exemption applies to the read, and the current read (still 0777) refuses on its own line
        xdg2 = tempfile.mkdtemp()
        root2 = os.path.join(xdg2, "romp")
        os.makedirs(root2)
        os.chmod(root2, 0o777)
        r2 = subprocess.run([sys.executable, self._chmod_refusing_shim(root2)],
                            env=self._bus_env(xdg2, _free_port()), capture_output=True, text=True, timeout=60)
        self.assertEqual(r2.returncode, 2, r2.stderr[-800:])
        self.assertIn("is mode 0777, writable by other local users (an other write bit)", r2.stderr, "the current read's line")
        self.assertIn("did NOT start", r2.stderr)

    def test_an_empty_pre_existing_writable_root_the_bus_can_tighten_starts_silently(self):
        """THE CREATION EXEMPTION at the bus's start (round 4): a pre-existing 0777 root with nothing in it, made by another
        tool a moment ago. The start gate reads 0777 and an empty listing, its chmod tightens the root, and the bus
        serves with no state-root line: nothing could have been planted in an empty directory. Before round 4 this start
        exited 2 with the distrust remedy."""
        xdg = tempfile.mkdtemp()
        root = os.path.join(xdg, "romp")
        os.makedirs(root)
        os.chmod(root, 0o777)
        port = _free_port()
        proc, logname = self._serve(xdg, port)
        self._await_ping(proc, port, logname)
        self.assertEqual(_mode(root), 0o700, "tightened at start")
        self.assertEqual([l for l in open(logname).read().splitlines() if "state root" in l], [], "silent")

    def test_the_gate_runs_at_import_in_every_mode_not_only_serve(self):
        """extra6-2 of round 3 (E): the module reads or mints the serve token under the root at import in EVERY mode, so
        `romp mail` and each session's MCP process write under an unchecked root when the gate runs under argv "serve"
        alone. The gate now runs at import whatever argv says: a bus invocation that is not `serve` over a pre-existing
        0777 root that holds an entry exits 2 with the distrust line before its command runs; the same invocation over a
        0700 root runs its command. At 9748684d3 the non-serve invocation ran (exit 0) over the hostile root."""
        for mode, want in ((0o777, 2), (0o700, 0)):
            xdg = tempfile.mkdtemp()
            root = os.path.join(xdg, "romp")
            os.makedirs(root)
            Path(root, "session-hosts").write_text("off\n")
            os.chmod(root, mode)
            r = subprocess.run([sys.executable, os.path.join(BIN, "romp-postal-service"), "sweep"],
                               env=self._bus_env(xdg, _free_port()), capture_output=True, text=True, timeout=60)
            self.assertEqual(r.returncode, want, "%04o: %s" % (mode, r.stderr[-800:]))
            if want == 2:
                self.assertIn("read 0777 at start", r.stderr)
                self.assertIn(DISTRUST, r.stderr)
                self.assertIn("did NOT start", r.stderr)
            else:
                self.assertNotIn("did NOT start", r.stderr)

    def test_a_file_at_the_root_path_stops_the_bus_with_enotdir(self):
        """regression-1 of round 3 (I) at the bus's start: a FILE where the root should be exits 2 with ENOTDIR and the
        remedy, before the token work."""
        xdg = tempfile.mkdtemp()
        root = os.path.join(xdg, "romp")
        Path(root).write_text("not a directory\n")
        r = subprocess.run([sys.executable, os.path.join(BIN, "romp-postal-service"), "serve"],
                           env=self._bus_env(xdg, _free_port()), capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 2, r.stderr[-800:])
        self.assertIn("ENOTDIR", r.stderr)
        self.assertIn("recreate the root as a directory", r.stderr)
        self.assertIn("did NOT start", r.stderr)

    def test_planted_mail_and_links_under_the_root_are_quarantined_by_a_serving_bus(self):
        """The bus's guarded readers (round 4; the enumeration's HIGH 3 and two MEDIUMs): a message file planted as a
        symlink in a box's new/, a symlinked timeline/messages.jsonl and a symlinked postal/server.pid under a 0700 root.
        The bus starts, and its start sweep and pid write meet the plants through the guard: each is quarantined (moved
        under <root>/quarantine), nothing is read or written THROUGH a link (the targets keep their bytes), the planted
        message is never listed as mail, and the bus serves. At 9748684d3 the ledger link is read and appended through,
        the pid link's target is overwritten with the bus's pid, and the planted message stands to be delivered."""
        xdg = tempfile.mkdtemp()
        root = os.path.join(xdg, "romp")
        os.makedirs(os.path.join(root, "postal", "mail", "11111111-2222-3333-4444-000000000001", "new"))
        os.makedirs(os.path.join(root, "timeline"))
        os.chmod(root, 0o700)
        elsewhere = Path(tempfile.mkdtemp())
        (elsewhere / "ledger.jsonl").write_text('{"t": 1, "ev": "sent", "id": "planted-id"}\n')
        (elsewhere / "pidfile").write_text("keep-me\n")
        (elsewhere / "mail").write_text("From: planted\nFrom-Id: x\nDate: 1\n\nplanted body\n")
        os.symlink(elsewhere / "ledger.jsonl", os.path.join(root, "timeline", "messages.jsonl"))
        os.symlink(elsewhere / "pidfile", os.path.join(root, "postal", "server.pid"))
        os.symlink(elsewhere / "mail", os.path.join(root, "postal", "mail", "11111111-2222-3333-4444-000000000001", "new", "planted-id"))
        port = _free_port()
        proc, logname = self._serve(xdg, port)
        self._await_ping(proc, port, logname)
        time.sleep(1.0)
        log = open(logname).read()
        q = sorted(os.listdir(os.path.join(root, "quarantine"))) if os.path.isdir(os.path.join(root, "quarantine")) else []
        self.assertTrue(any(n.endswith(".timeline.messages.jsonl") for n in q), (q, log[-1500:]))
        self.assertTrue(any(n.endswith(".postal.server.pid") for n in q), (q, log[-1500:]))
        self.assertEqual((elsewhere / "ledger.jsonl").read_text(), '{"t": 1, "ev": "sent", "id": "planted-id"}\n',
                         "nothing appended through the link")
        self.assertEqual((elsewhere / "pidfile").read_text(), "keep-me\n", "nothing written through the link")
        self.assertEqual(log.count("quarantined to"), len(q), "one line per quarantine:\n" + log[-1500:])
        pid = Path(root, "postal", "server.pid")
        self.assertFalse(pid.is_symlink())
        self.assertEqual(pid.read_text().strip(), str(proc.pid), "the pid file is the bus's own regular file")
        self.assertEqual(_mode(os.path.join(root, "quarantine")), 0o700)

    def test_a_self_owned_0755_root_at_start_is_retightened_said_once_and_served(self):
        """The repair leaves a trace at the bus's start too (round 2): a pre-existing 0755 root this uid owns is
        re-tightened to 0700 by the check's chmod AND said, one line, and the bus serves; a few polls later still one
        line. At the round-1 head the start chmod'ed first and said nothing."""
        xdg = tempfile.mkdtemp()
        root = os.path.join(xdg, "romp")
        os.makedirs(root)
        os.chmod(root, 0o755)
        port = _free_port()
        proc, logname = self._serve(xdg, port)
        self._await_ping(proc, port, logname)
        self.assertEqual(_mode(root), 0o700, "re-tightened at start")
        time.sleep(2.5)                                        # a few polls (POLL=1)
        self.assertIsNone(proc.poll(), "a warn root does not exit the bus")
        said = [l for l in open(logname).read().splitlines() if "state root" in l]
        self.assertEqual(len(said), 1, "one line, at start, not per poll:\n" + "\n".join(said))
        self.assertIn("was mode 0755, re-tightened to 0700", said[0])

    def test_the_bus_makes_an_absent_root_0700_and_says_nothing(self):
        """The creation case: no root at the bus's start (ENOENT is unmade, not unverified, at import alone). The bus
        makes it, 0700 whatever the umask, and serves with no state-root line: the umask's mode on a directory this
        process just made is a creation default, not a loosening (the exemption a created root has under the rule)."""
        xdg = tempfile.mkdtemp()
        root = os.path.join(xdg, "romp")
        self.assertFalse(os.path.exists(root))
        port = _free_port()
        proc, logname = self._serve(xdg, port, token=None)      # the token is minted from the root the bus makes
        self._await_ping(proc, port, logname)
        self.assertEqual(_mode(root), 0o700)
        self.assertTrue(os.path.exists(os.path.join(root, "serve-token")))
        self.assertEqual([l for l in open(logname).read().splitlines() if "state root" in l], [])

    def test_the_bus_refuses_at_start_on_an_unreadable_root(self):
        xdg = tempfile.mkdtemp()
        root = os.path.join(xdg, "romp")
        os.makedirs(root)
        os.chmod(xdg, 0o000)                                   # the root cannot be traversed to
        self.addCleanup(lambda: os.chmod(xdg, 0o700))
        port = _free_port()
        r = subprocess.run([sys.executable, os.path.join(BIN, "romp-postal-service"), "serve"],
                           env=self._bus_env(xdg, port), capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 2, r.stderr[-800:])
        self.assertIn("unverified root is not served from", r.stderr)

    def test_a_bus_serving_on_0700_exits_when_the_root_is_loosened(self):
        xdg = tempfile.mkdtemp()
        root = os.path.join(xdg, "romp")
        os.makedirs(root)
        os.chmod(root, 0o700)
        port = _free_port()
        logf = tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False)
        proc = subprocess.Popen([sys.executable, os.path.join(BIN, "romp-postal-service"), "serve"],
                                env=self._bus_env(xdg, port), stdout=logf, stderr=subprocess.STDOUT)
        self.addCleanup(lambda: proc.poll() is None and (proc.kill(), proc.wait(timeout=10)))
        self.addCleanup(lambda: os.unlink(logf.name))
        try:
            up = False
            for _ in range(60):
                if self._ping(port):
                    up = True
                    break
                if proc.poll() is not None:
                    break
                time.sleep(0.25)
            if not up:
                raise unittest.SkipTest("hermetic bus never served /ping here:\n" + open(logf.name).read()[-600:])
            os.chmod(root, 0o777)                              # the monitor loop re-checks every POLL (1s here)
            for _ in range(30):
                if proc.poll() is not None:
                    break
                time.sleep(0.5)
            self.assertIsNotNone(proc.poll(), "the bus exited on the loosened root")
            self.assertEqual(proc.returncode, 2)
            self.assertIn("writable by other local users", open(logf.name).read())
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=10)

    def test_a_warn_root_logs_one_line_and_serves(self):
        xdg = tempfile.mkdtemp()
        root = os.path.join(xdg, "romp")
        os.makedirs(root)
        os.chmod(root, 0o755)
        # interpose a chmod refusal for the root, so the bus's start gate cannot tighten it and the warn stands (a warn
        # root the bus CAN tighten becomes ok and serves; the signal here is a root it cannot).
        port = _free_port()
        shim = self._chmod_refusing_shim(root)
        logf = tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False)
        proc = subprocess.Popen([sys.executable, shim], env=self._bus_env(xdg, port), stdout=logf, stderr=subprocess.STDOUT)
        self.addCleanup(lambda: os.unlink(logf.name))
        try:
            up = False
            for _ in range(60):
                if self._ping(port):
                    up = True
                    break
                if proc.poll() is not None:
                    break
                time.sleep(0.25)
            self.assertTrue(up, "the bus served on the 0755 root (warn, not refuse):\n" + open(logf.name).read()[-800:])
            time.sleep(2.5)                                    # a few monitor polls (POLL=1): still serving, still one line
            self.assertIsNone(proc.poll(), "a warn root does not exit the bus")
            self.assertTrue(self._ping(port))
            said = [l for l in open(logf.name).read().splitlines() if "not 0700" in l and "state root" in l]
            self.assertEqual(len(said), 1, "one line per transition, not per poll:\n" + "\n".join(said))
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=10)


# ── THE GUARDED READERS: quarantine, never adopt (round 4, the ruling's A, B and C) ──────────────────────────────

def _lstat_owned_by(target, uid):
    """An os.lstat that reports `target` as owned by `uid` (the shape of an entry another local user planted while the
    root was writable; a single account cannot make one) and answers every other path from the real lstat."""
    real = os.lstat
    rt = os.path.realpath(str(target))          # resolved once, before the patch (realpath calls lstat)

    def f(p, *a, **k):
        st = real(p, *a, **k)
        if os.path.normpath(os.fspath(p)) == rt:
            return os.stat_result(tuple(st)[:4] + (uid,) + tuple(st)[5:])
        return st
    return f


class TheGuardedReadersQuarantine(_KernelState):
    """kernel/state_root_mode.py's Reader, as the kernel wires it (_gr over jd.STATE, the row hook into the error centre):
    the guard is OWNERSHIP plus the absence of a symlink plus the discriminator, checked on every component from the
    root down (the ruling's C: never the directory's mode alone), and a failure QUARANTINES the entry, says one line,
    files one row and reads the path as absent (the ruling's B: a plant that was merely skipped was re-adopted at the
    next boot; a quarantined one is gone from the root). The named plants of round 3: a foreign-owned sdkvenv
    site-packages (kernel-1: it went onto sys.path[0] and shadowed every later import), a symlinked pending-ops.json
    (correctness-1: its parked ops replayed into a live session as prompts and picks), the memo files (extra5-5). The
    legitimacy cases the refuters established: a 0664 pending-ops mirror under the owner's private group (the
    pre-2026-09-18 mirror) and a 0775 venv under the private group (what bin/romp-sdk-setup builds under umask 0002)
    are ADOPTED. At 9748684d3 every plant here is adopted: the site-packages joins sys.path, the parked ops load, the
    memo rows load (checked against a detached worktree of that commit)."""

    def _quarantined(self):
        q = Path(self.root, srm.QUARANTINE_DIR)
        return sorted(p.name for p in q.iterdir()) if q.is_dir() else []

    def _mirror_here(self):
        """_PENDING_OPS_FILE is bound at the kernel's import (a fact of the module, not of this change): pointed at this
        test's root for the arm's length."""
        patcher = mock.patch.object(km, "_PENDING_OPS_FILE", Path(self.root, "pending-ops.json"))
        patcher.start()
        self.addCleanup(patcher.stop)

    def _site(self):
        sp = Path(self.root, "sdkvenv", "lib", "python" + km._running_python_tag(), "site-packages")
        sp.mkdir(parents=True)
        (sp / "claude_agent_sdk").mkdir()
        (sp / "claude_agent_sdk" / "__init__.py").write_text("")
        return sp

    def _ensure(self, importable_from):
        import importlib.util
        real_find_spec = importlib.util.find_spec

        def fake_find_spec(name, *a, **k):
            if name != "claude_agent_sdk":
                return real_find_spec(name, *a, **k)
            if importable_from and any(p.startswith(str(importable_from)) for p in sys.path):
                return SimpleNamespace(name=name)
            return None
        km._SDK_VENV_BUILT_FOR = []
        with mock.patch.object(importlib.util, "find_spec", fake_find_spec), mock.patch.object(km, "_sdk_backend", None), \
             contextlib.redirect_stderr(io.StringIO()):
            return km._ensure_sdk_on_path()

    def test_a_fault_under_a_trusted_directory_propagates_as_the_primitive_raised_it_and_nothing_is_quarantined(self):
        """Round 4d: an EACCES on a component whose parent the walk TRUSTED (this uid's, no symlink, not writable by
        another) is that directory's fault, not a plant under it (nothing another uid could have put there). Each reader
        runs its primitive and answers exactly as the bare primitive does on the same path (a PermissionError from
        read_text, read_bytes, open, os_open, gzip_open, stat, listdir, scandir, iterdir and glob's consumption; exists
        and isdir as the interpreter's pathlib answers them: 3.12 raises, 3.14 answers False), quarantines nothing, files
        no row, says no line, and trusted_path reports the fault with ok True. Through round 4c the walk turned the
        lstat's EACCES into a refusal ("could not be read") whose quarantine EACCES refused too, and the path read ABSENT:
        the judge's _reg_spawned_at then answered None for a reg it could not read, and tests/test_planner_skip.py's
        unreadable-sdk case keyed two sessions as reg-less and skipped them on the 3.14t CI cell (on 3.12 _sdk_owned's
        Path.exists raised the same EACCES first and hid it). The controls: the same directory at 0700 reads; a symlink
        planted beside it is still quarantined (the trust failures keep their contract)."""
        if os.geteuid() == 0:
            raise unittest.SkipTest("root reads every directory")
        sdk = Path(self.root, "sdk")
        sdk.mkdir(mode=0o700)
        reg = sdk / "a.json"
        reg.write_text('{"spawnedAt": 1}')
        os.chmod(sdk, 0)
        self.addCleanup(os.chmod, sdk, 0o700)

        def outcome(fn):
            try:
                v = fn()
                if hasattr(v, "close"):
                    v.close()
                return ("value", v if not hasattr(v, "close") else "handle")
            except OSError as e:
                return ("raise", type(e).__name__, e.errno)

        def consumed(fn):
            return lambda: list(fn())

        pairs = [
            (lambda: km._gr.read_text(reg), lambda: reg.read_text()),
            (lambda: km._gr.read_bytes(reg), lambda: reg.read_bytes()),
            (lambda: km._gr.open(reg), lambda: open(reg)),
            (lambda: km._gr.os_open(reg), lambda: os.open(reg, os.O_RDONLY)),
            (lambda: km._gr.gzip_open(reg), lambda: __import__("gzip").open(reg)),
            (lambda: km._gr.stat(reg), lambda: reg.stat()),
            (lambda: km._gr.exists(reg), lambda: reg.exists()),
            (lambda: km._gr.isdir(reg), lambda: reg.is_dir()),
            (lambda: km._gr.listdir(sdk), lambda: os.listdir(sdk)),
            (consumed(lambda: km._gr.scandir(sdk)), consumed(lambda: os.scandir(sdk))),
            (consumed(lambda: km._gr.iterdir(sdk)), consumed(lambda: sdk.iterdir())),
            (consumed(lambda: km._gr.glob(sdk, "*.json")), consumed(lambda: sdk.glob("*.json"))),
        ]
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            for guarded, bare in pairs:
                g, b = outcome(guarded), outcome(bare)
                if isinstance(g[1], os.stat_result) or (g[0] == "value" and isinstance(g[1], list)):
                    g, b = (g[0], type(g[1]).__name__), (b[0], type(b[1]).__name__)
                self.assertEqual(g, b, "the guarded reader answers as the bare primitive does")
            self.assertEqual(outcome(lambda: km._gr.read_text(reg)), ("raise", "PermissionError", errno.EACCES))
        t = srm.trusted_path(self.root, reg)
        self.assertTrue(t["ok"], t)
        self.assertIn("EACCES", t.get("fault") or "", t)
        self.assertIsNone(t["reason"])
        self.assertEqual(self._quarantined(), [], "nothing quarantined: a fault is not a plant")
        self.assertEqual(km._gr.refused, [], "no refusal recorded")
        self.assertEqual(self.refused_rows(), [], "no row")
        self.assertEqual(err.getvalue(), "", "no line")
        # the control: the same directory readable again reads the file through the same reader
        os.chmod(sdk, 0o700)
        self.assertEqual(km._gr.read_text(reg), '{"spawnedAt": 1}')
        self.assertNotIn("fault", srm.trusted_path(self.root, reg))
        # the contrast: a trust failure beside it keeps the quarantine contract
        elsewhere = Path(tempfile.mkdtemp(), "b.json")
        elsewhere.write_text("{}")
        os.symlink(elsewhere, sdk / "b.json")
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(FileNotFoundError):
                km._gr.read_text(sdk / "b.json")
        self.assertEqual([r[1] for r in km._gr.refused], ["symlink"])
        self.assertTrue(any(n.endswith(".sdk.b.json") for n in self._quarantined()), self._quarantined())

    def test_a_planted_sdkvenv_owned_by_another_uid_is_quarantined_and_never_on_sys_path(self):
        """kernel-1 of round 3: the venv directory reads as another uid's (os.lstat interposed for that one path: a
        single account cannot plant a foreign-owned entry for real). _ensure_sdk_on_path finds no venv, sys.path is
        untouched, the directory is in <root>/quarantine as <stamp>.sdkvenv, one refused-kind row names it and the
        reason (owner). The same venv owned by this uid is adopted (the control, below)."""
        sp = self._site()
        with mock.patch("os.lstat", new=_lstat_owned_by(Path(self.root, "sdkvenv"), os.geteuid() + 1)):
            self.assertFalse(self._ensure(sp))
        self.assertNotIn(str(sp), sys.path, "a planted site-packages never reaches sys.path")
        self.assertFalse(os.path.exists(os.path.join(self.root, "sdkvenv")), "gone from the root")
        q = self._quarantined()
        self.assertEqual(len(q), 1, q)
        self.assertTrue(q[0].endswith(".sdkvenv"), q[0])
        self.assertTrue(os.path.isdir(os.path.join(self.root, srm.QUARANTINE_DIR, q[0])), "moved whole, not deleted")
        rows = [r["text"] for r in self.refused_rows()]
        self.assertEqual(len(rows), 1, rows)
        self.assertIn("sdkvenv was not this uid's: quarantined", rows[0])
        self.assertEqual([r[1] for r in km._gr.refused], ["owner"])
        # the control: this uid's venv at 0775 under the private group (the ruling's legitimacy case) is adopted
        if not _private_group_here():
            return
        sp = self._site()
        for d in (Path(self.root, "sdkvenv"), Path(self.root, "sdkvenv", "lib"), sp.parent, sp):
            os.chmod(d, 0o775)
        self.assertTrue(self._ensure(sp), "a 0775 venv under the owner's private group is adopted")
        self.assertIn(str(sp), sys.path)
        self.assertEqual(sys.path.index(str(sp)), 0, "at the front, as before: the guard changes what is admitted, not where")
        self.assertEqual(len(self._quarantined()), 1, "nothing more quarantined")

    def test_a_0775_venv_under_the_private_group_is_adopted_and_a_symlinked_one_is_not(self):
        if not _private_group_here():
            raise unittest.SkipTest("this account's primary group is shared on this box")
        sp = self._site()
        for d in (Path(self.root, "sdkvenv"), Path(self.root, "sdkvenv", "lib"), sp.parent, sp):
            os.chmod(d, 0o775)
        self.assertTrue(self._ensure(sp))
        self.assertIn(str(sp), sys.path)
        self.assertEqual(self._quarantined(), [])
        # a venv reached through a symlink planted at the root's sdkvenv entry: refused at the first component
        sys.path[:] = [p for p in sys.path if not p.startswith(self.root)]
        shutil.rmtree(os.path.join(self.root, "sdkvenv"))
        elsewhere = Path(tempfile.mkdtemp(), "sdkvenv")
        (elsewhere / "lib" / ("python" + km._running_python_tag()) / "site-packages").mkdir(parents=True)
        os.symlink(elsewhere, os.path.join(self.root, "sdkvenv"))
        self.assertFalse(self._ensure(elsewhere / "lib" / ("python" + km._running_python_tag()) / "site-packages"))
        self.assertFalse(any(p.startswith(str(elsewhere)) for p in sys.path))
        self.assertTrue(any(n.endswith(".sdkvenv") for n in self._quarantined()))
        self.assertTrue(elsewhere.is_dir(), "the link's target is untouched")

    def _codex_backend(self):
        return sys.modules.get("romp_codex_backend") or load_source("romp_codex_backend", os.path.join(ROOT, "kernel", "codex_backend.py"))

    def _codex_site(self, cb, under=None):
        sp = Path(under or self.root, "codexvenv", "lib", "python" + cb._running_python_tag(), "site-packages")
        sp.mkdir(parents=True)
        (sp / "openai_codex").mkdir()
        (sp / "openai_codex" / "__init__.py").write_text("")
        return sp

    def _ensure_codex(self, cb, importable_from):
        import importlib.util
        real_find_spec = importlib.util.find_spec

        def fake_find_spec(name, *a, **k):
            if name != "openai_codex":
                return real_find_spec(name, *a, **k)
            if importable_from and any(p.startswith(str(importable_from)) for p in sys.path):
                return SimpleNamespace(name=name)
            return None
        cb._CODEX_VENV_BUILT_FOR = []
        with mock.patch.object(importlib.util, "find_spec", fake_find_spec), contextlib.redirect_stderr(io.StringIO()):
            return cb.ensure_codex_sdk(self.root)

    def test_a_planted_codexvenv_owned_by_another_uid_is_quarantined_and_never_on_sys_path(self):
        """The round-4 review's twin of kernel-1: kernel/codex_backend.py's ensure_codex_sdk globbed codexvenv/lib/python3.*/
        site-packages under the root bare and inserted the match at sys.path[0] (reachable on /models when Codex is the
        default backend, and on every Codex launch or resume), and the first census did not cover the module. Now the
        discovery goes through the module's per-call guarded reader: the venv directory reads as another uid's (os.lstat
        interposed for that one path), ensure_codex_sdk finds no venv, sys.path is untouched, the directory is in
        <root>/quarantine as <stamp>.codexvenv, and one refused-kind row names it and the reason (owner), filed through
        the shared module's REFUSED_HOOKS (the kernel's row hook). The controls: this uid's venv is adopted at sys.path[0]
        as before, and a venv reached through a symlink planted at the root's codexvenv entry is refused at that first
        component and never followed. Before this pass (the round-4 tree as reviewed) the planted venv joined sys.path[0]
        and a module planted in it ran on import (the reviewer's reproduction)."""
        cb = self._codex_backend()
        sp = self._codex_site(cb)
        with mock.patch("os.lstat", new=_lstat_owned_by(Path(self.root, "codexvenv"), os.geteuid() + 1)):
            self.assertFalse(self._ensure_codex(cb, sp))
        self.assertNotIn(str(sp), sys.path, "a planted site-packages never reaches sys.path")
        self.assertFalse(os.path.exists(os.path.join(self.root, "codexvenv")), "gone from the root")
        q = self._quarantined()
        self.assertEqual(len(q), 1, q)
        self.assertTrue(q[0].endswith(".codexvenv"), q[0])
        rows = [r["text"] for r in self.refused_rows()]
        self.assertEqual(len(rows), 1, rows)
        self.assertIn("codexvenv was not this uid's: quarantined", rows[0])
        # the control: this uid's venv is adopted, at the front
        sp = self._codex_site(cb)
        self.assertTrue(self._ensure_codex(cb, sp), "this uid's codexvenv is adopted")
        self.assertEqual(sys.path.index(str(sp)), 0, "at the front, as before: the guard changes what is admitted, not where")
        self.assertEqual(len(self._quarantined()), 1, "nothing more quarantined")
        # a venv reached through a symlink planted at the root's codexvenv entry: refused at the first component
        sys.path[:] = [p for p in sys.path if not p.startswith(self.root)]
        shutil.rmtree(os.path.join(self.root, "codexvenv"))
        elsewhere = Path(tempfile.mkdtemp())
        far = self._codex_site(cb, under=elsewhere)
        os.symlink(elsewhere / "codexvenv", os.path.join(self.root, "codexvenv"))
        self.assertFalse(self._ensure_codex(cb, far))
        self.assertFalse(any(p.startswith(str(elsewhere)) for p in sys.path), "nothing under the link's target is on sys.path")
        self.assertEqual(sum(".codexvenv" in n for n in self._quarantined()), 2, self._quarantined())   # the second entry in one second takes a -1 suffix
        self.assertTrue(far.is_dir(), "the link's target is untouched")

    def test_a_planted_logins_link_is_quarantined_and_no_record_is_read(self):
        """The round-4 review's demonstration of the handed-root modules: a `logins` symlink planted at the root, pointing
        at a directory holding a record whose tokenCmd is attacker-chosen (the login-billing road runs that command as
        /bin/sh). kernel/logins.py reads through its per-call guarded reader now: records() answers nothing, read_record()
        answers None, the link is quarantined (its target untouched), one row is filed, and a record this uid writes
        afterwards is read as before. Before this pass records() returned the planted record and the link stood."""
        lg = km.lg
        elsewhere = Path(tempfile.mkdtemp(), "logins")
        elsewhere.mkdir()
        planted = {"id": "aaaaaaaaaaaa", "label": "planted", "tokenCmd": "echo sk-ant-planted-DO-NOT-USE", "addedAt": 1}
        (elsewhere / "aaaaaaaaaaaa.json").write_text(json.dumps(planted))
        os.symlink(elsewhere, os.path.join(self.root, "logins"))
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(lg.records(Path(self.root)), [], "nothing planted is listed")
        self.assertTrue((elsewhere / "aaaaaaaaaaaa.json").exists(), "the link's target is untouched")
        self.assertFalse(os.path.lexists(os.path.join(self.root, "logins")), "the link is gone from the root")
        self.assertTrue(any(n.endswith(".logins") for n in self._quarantined()), self._quarantined())
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertIsNone(lg.read_record(Path(self.root), "aaaaaaaaaaaa"))
        rows = [r["text"] for r in self.refused_rows()]
        self.assertEqual(len(rows), 1, rows)
        self.assertIn("logins was a symlink: quarantined", rows[0])
        lg.write_record(Path(self.root), {"id": "bbbbbbbbbbbb", "label": "mine", "addedAt": 2})
        self.assertEqual([r["id"] for r in lg.records(Path(self.root))], ["bbbbbbbbbbbb"], "this uid's record reads as before")

    def test_a_planted_pending_ops_symlink_is_quarantined_and_nothing_is_delivered(self):
        """correctness-1 of round 3, the plant with the shortest road to the user: pending-ops.json planted as a symlink
        to a file holding a parked op for a session. _load_pending_ops reads the mirror through the guard: the link is
        quarantined, the target keeps its bytes, the queue restored is EMPTY, and the drain, driven here with the
        delivery seam watched, delivers nothing. At 9748684d3 the op loads and the drain replays it."""
        sid = "11111111-2222-3333-4444-000000000abc"
        elsewhere = Path(tempfile.mkdtemp(), "ops.json")
        elsewhere.write_text(json.dumps({sid: [["send", "planted parked text", None, None]]}))
        os.symlink(elsewhere, os.path.join(self.root, "pending-ops.json"))
        self._mirror_here()
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            queue = km._load_pending_ops()
        self.assertEqual(queue, {}, "nothing planted is adopted")
        self.assertFalse(os.path.lexists(os.path.join(self.root, "pending-ops.json")), "the link is gone from the root")
        q = self._quarantined()
        self.assertEqual(len(q), 1, q)
        self.assertTrue(q[0].endswith(".pending-ops.json"), q[0])
        self.assertEqual(elsewhere.read_text(), json.dumps({sid: [["send", "planted parked text", None, None]]}), "the target's bytes stand")
        self.assertIn("pending-ops.json is a symlink: quarantined to", err.getvalue())
        rows = [r["text"] for r in self.refused_rows()]
        self.assertEqual(len(rows), 1, rows)
        self.assertIn("pending-ops.json was a symlink: quarantined and read as absent", rows[0])
        saved = km._pending_ops
        km._pending_ops = queue
        try:
            with mock.patch.object(km, "_deliver_send_batch") as deliver, contextlib.redirect_stderr(io.StringIO()):
                km._apply_pending_ops()
            deliver.assert_not_called()
        finally:
            km._pending_ops = saved
        # a second boot: the plant is not there to be re-adopted (the ruling's B), and the quarantine keeps it
        self.assertEqual(km._load_pending_ops(), {})
        self.assertEqual(len(self._quarantined()), 1)

    def test_a_0664_pending_ops_mirror_under_the_private_group_is_adopted(self):
        """The refuters' legitimacy case (round 3's C): a mirror that sat at the umask's 0664 before _save_pending_ops
        passed mode 0o600 (2026-09-18) is this uid's, not a symlink, and its group write bit is under the owner's private
        group, so the guard passes it and the queue loads. A rule on the file's mode alone would have dropped it."""
        if not _private_group_here():
            raise unittest.SkipTest("this account's primary group is shared on this box")
        sid = "11111111-2222-3333-4444-000000000abd"
        p = Path(self.root, "pending-ops.json")
        p.write_text(json.dumps({sid: [["model", "sonnet"]]}))
        os.chmod(p, 0o664)
        self._mirror_here()
        with contextlib.redirect_stderr(io.StringIO()):
            queue = km._load_pending_ops()
        self.assertEqual(queue, {sid: [("model", "sonnet")]})
        self.assertEqual(self._quarantined(), [])
        self.assertEqual(self.refused_rows(), [])
        # and the same mirror with an OTHER write bit is refused: any local user could have written it
        os.chmod(p, 0o666)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(km._load_pending_ops(), {})
        self.assertTrue(any(n.endswith(".pending-ops.json") for n in self._quarantined()))
        self.assertIn("writable by another local user", self.refused_rows()[0]["text"])

    def test_a_symlinked_memo_file_is_quarantined_and_reads_as_absent(self):
        """extra5-5 of round 3: the memo files the import reads through read_text with shape checks alone. Each planted as
        a symlink to a well-formed file elsewhere: the loaders read them as absent (an empty memo), the links are
        quarantined, the targets untouched."""
        elsewhere = Path(tempfile.mkdtemp())
        (elsewhere / "downtime.jsonl").write_text(json.dumps({"start": 1.0, "end": 2.0}) + "\n")
        (elsewhere / "tick.json").write_text(json.dumps({"auto-nudge|sid": [1, 2, 3, 4, 5, 6]}))
        os.symlink(elsewhere / "downtime.jsonl", os.path.join(self.root, "kernel-downtime.jsonl"))
        os.symlink(elsewhere / "tick.json", os.path.join(self.root, "tick-seen.json"))
        saved_downtime = list(km._downtime)
        saved_tick = dict(km._TICK_SEEN)
        try:
            km._downtime[:] = []
            km._TICK_SEEN.clear()
            with contextlib.redirect_stderr(io.StringIO()):
                km._load_downtime()
                n = km._load_tick_seen()
            self.assertEqual(km._downtime, [], "the planted downtime rows are not adopted")
            self.assertEqual(n, 0, "the planted memo is not adopted")
        finally:
            km._downtime[:] = saved_downtime
            km._TICK_SEEN.clear(); km._TICK_SEEN.update(saved_tick)
        q = self._quarantined()
        self.assertEqual(sorted(n.split(".", 1)[1] for n in q), ["kernel-downtime.jsonl", "tick-seen.json"])
        self.assertTrue((elsewhere / "downtime.jsonl").exists() and (elsewhere / "tick.json").exists())
        self.assertEqual(len(self.refused_rows()), 2)

    def test_the_quarantine_names_the_stamp_and_the_path_and_is_0700_and_a_failed_move_still_reads_absent(self):
        """The quarantine contract's shape: <root>/quarantine/<utc-stamp>.<relative-path-with-slashes-as-dots>, the
        directory created 0700 whatever the umask, the FIRST failing component moved (a symlinked directory takes its
        contents with it). A quarantine that itself fails (os.rename refused) says so and the read still answers absent,
        never the planted bytes."""
        elsewhere = Path(tempfile.mkdtemp())
        (elsewhere / "b.json").write_text("{}")
        os.mkdir(os.path.join(self.root, "a"))
        os.symlink(elsewhere, os.path.join(self.root, "a", "linked"))
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(FileNotFoundError):
                km._gr.read_text(Path(self.root, "a", "linked", "b.json"))
        q = self._quarantined()
        self.assertEqual(len(q), 1, q)
        stamp, rel = q[0].split(".", 1)
        self.assertRegex(stamp, r"^\d{8}T\d{6}Z$")
        self.assertEqual(rel, "a.linked", "the first failing component, its path below the root with slashes as dots")
        self.assertEqual(_mode(os.path.join(self.root, srm.QUARANTINE_DIR)), 0o700)
        self.assertTrue(os.path.isdir(os.path.join(self.root, "a")), "the trusted parent stays")
        self.assertTrue((elsewhere / "b.json").exists())
        # a move that fails: said, and the read is still absent
        os.symlink(elsewhere, os.path.join(self.root, "a", "linked2"))
        err = io.StringIO()
        real = os.rename

        def refuse(src, dst, *a, **k):
            if os.path.basename(str(src)) == "linked2":
                raise PermissionError(1, "refused (interposed)")
            return real(src, dst, *a, **k)
        with mock.patch("os.rename", new=refuse), contextlib.redirect_stderr(err):
            with self.assertRaises(FileNotFoundError):
                km._gr.read_text(Path(self.root, "a", "linked2", "b.json"))
        self.assertIn("could not be quarantined (EPERM", err.getvalue())
        self.assertIn("read as absent", err.getvalue())
        self.assertTrue(os.path.islink(os.path.join(self.root, "a", "linked2")), "the plant stands; the operator removes it")
        self.assertNotIn("interposed", err.getvalue(), "the errno, never the exception's text")

    def test_the_readers_pass_a_path_outside_the_root_through_and_read_absent_on_a_root_that_fails(self):
        """A path that is not under the root is not the root's to guard: the plain read runs (a transcript under the
        Claude config directory). A root that fails its own check (here: reading as another uid's) makes every read
        under it absent, and quarantines nothing (the root is not an entry; the gates own that case)."""
        outside = Path(tempfile.mkdtemp(), "t.jsonl")
        outside.write_text("outside\n")
        self.assertEqual(km._gr.read_text(outside), "outside\n")
        Path(self.root, "spend.json").write_text("{}")
        with mock.patch("os.lstat", new=_lstat_owned_by(self.root, os.geteuid() + 1)), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(FileNotFoundError):
                km._gr.read_text(Path(self.root, "spend.json"))
        self.assertTrue(Path(self.root, "spend.json").exists(), "nothing under a failing root is moved: the root is the gate's")
        self.assertEqual(self._quarantined(), [])
        self.assertEqual([r[1] for r in km._gr.refused], ["root"])
        self.assertEqual(self.refused_rows(), [], "a root failure files no row: the gate's check is the root's surface")
        # said once per process per root and cause, not once per read (a backend over a root that is gone read on every cycle)
        err = io.StringIO()
        with mock.patch("os.lstat", new=_lstat_owned_by(self.root, os.geteuid() + 1)), contextlib.redirect_stderr(err):
            for _ in range(3):
                with self.assertRaises(FileNotFoundError):
                    km._gr.read_text(Path(self.root, "spend.json"))
        self.assertEqual(err.getvalue(), "", "already said for this root")
        self.assertEqual([r[1] for r in km._gr.refused], ["root"], "recorded once")


# ── EVERY LONG-LIVED WRITER RUNS THE CHECK: the session host (round 3's E) ───────────────────────────────────────

HOST_BEAT_WAIT_S = 12.0   # a few of the host's beats (LEASE_HEARTBEAT_S is 3 s): the wait for a loosened root to be seen


class TheSessionHostRunsTheCheck(unittest.TestCase):
    """extra8-3 and kernel-3 of round 3: bin/romp-session-host is on by default, writes its lease under the state root
    every LEASE_HEARTBEAT_S, is built to outlive the kernel and, until round 4, carried no check, so the kernel's exit 2
    stopped nothing here. Now the host loads the one shared module (kernel/state_root_mode.py) and runs the check at
    start (a pre-existing root that held entries and read writable by another exits 2 before the CLI is spawned; a file
    at the root's path exits 2 with ENOTDIR) and on every beat (a root loosened under a running host exits 2 within a
    beat or two). The fake CLI of tests/fixtures/fake_claude.py stands in for Claude Code; the host runs on its pipe
    transport (no SDK). At 9748684d3 the host starts and beats on under every one of these roots."""

    def setUp(self):
        self.state = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.state, True)
        self.sid = "11111111-2222-3333-4444-0000000000a1"
        self.fake_log = os.path.join(self.state, "fake-cli.log")

    def _spec(self):
        d = Path(self.state) / "hosts" / self.sid
        d.mkdir(parents=True, mode=0o700)
        spec = {"sid": self.sid, "name": "web", "version": "abc12345", "state_dir": self.state, "protocol": 1,
                "cli_path": os.path.join(HERE, "fixtures", "fake_claude.py"), "cwd": self.state,
                "permission_prompt_tool_name": "stdio", "permission_mode": "default",
                "env": {"FAKE_CLI_LOG": self.fake_log, "FAKE_CLI_TRANSCRIPT_DIR": os.path.join(self.state, "transcripts"),
                        "FAKE_CLI_SESSION_ID": "11111111-2222-3333-4444-0000000000f1"},
                "max_buffer_size": 1024 * 1024, "hook_self_answer_s": 2, "unattached_grace_s": 3600}
        p = d / "spawn.json"
        p.write_text(json.dumps(spec)); p.chmod(0o600)
        return str(p)

    def _env(self):
        env = dict(os.environ, PYTHONUNBUFFERED="1", ROMP_SDK_SITE=os.path.join(self.state, "no-sdk-here"))
        for name in ("CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_API_KEY"):
            env.pop(name, None)
        return env

    def _start(self):
        spec_path = self._spec()
        errlog = os.path.join(self.state, "host.stderr")
        proc = subprocess.Popen([sys.executable, os.path.join(BIN, "romp-session-host"), spec_path],
                                stdout=subprocess.DEVNULL, stderr=open(errlog, "w"), env=self._env(), start_new_session=True)
        self.addCleanup(lambda: proc.poll() is None and (os.killpg(proc.pid, 9), proc.wait(timeout=10)))
        return proc, errlog

    def _hostlog(self):
        p = Path(self.state) / "hosts" / self.sid / "host.log"
        return [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []

    def test_a_hostile_root_at_start_exits_2_before_the_cli_is_spawned(self):
        os.chmod(self.state, 0o777)                      # the root holds entries (hosts/): the import-read rule's case
        proc, errlog = self._start()
        proc.wait(timeout=60)
        err = open(errlog).read()
        self.assertEqual(proc.returncode, 2, err[-1200:])
        self.assertIn("romp-session-host: state root", err)
        self.assertIn("read 0777 at start (writable by other local users: an other write bit)", err)
        self.assertIn(DISTRUST, err)
        self.assertIn("The host stops now (exit 2; found at start)", err)
        self.assertFalse(os.path.exists(self.fake_log), "the CLI was never spawned")
        kinds = [r["kind"] for r in self._hostlog()]
        self.assertIn("state-root-refused", kinds, kinds)
        self.assertNotIn("host-started", kinds)
        row = next(r for r in self._hostlog() if r["kind"] == "state-root-refused")
        self.assertEqual(row["where"], "start")
        self.assertNotIn(self.state, json.dumps(row), "the row carries no path")
        self.assertEqual(_mode(self.state), 0o700, "read before repair: the check's chmod tightened it, the refusal stood on the read")

    def test_a_file_at_the_root_path_exits_2_with_enotdir(self):
        spec_path = self._spec()
        spec = json.loads(Path(spec_path).read_text())
        notdir = os.path.join(tempfile.mkdtemp(), "romp")
        Path(notdir).write_text("not a directory\n")
        spec["state_dir"] = notdir
        Path(spec_path).write_text(json.dumps(spec))
        r = subprocess.run([sys.executable, os.path.join(BIN, "romp-session-host"), spec_path], env=self._env(),
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 2, r.stderr[-800:])
        self.assertIn("ENOTDIR", r.stderr)
        self.assertIn("recreate the root as a directory", r.stderr)
        self.assertFalse(os.path.exists(self.fake_log))

    def test_a_root_loosened_under_a_running_host_exits_2_within_a_beat(self):
        proc, errlog = self._start()
        sock = Path(self.state) / "hosts" / (self.sid[:8] + ".sock")
        for _ in range(300):                             # the socket is the host's "up" (the CLI is behind it)
            if sock.exists() or proc.poll() is not None:
                break
            time.sleep(0.05)
        if proc.poll() is not None:
            raise unittest.SkipTest("the host did not come up here:\n" + open(errlog).read()[-800:])
        self.assertTrue(sock.exists())
        os.chmod(self.state, 0o777)
        for _ in range(int(HOST_BEAT_WAIT_S * 10)):
            if proc.poll() is not None:
                break
            time.sleep(0.1)
        self.assertIsNotNone(proc.poll(), "the host exited on the loosened root within a beat or two:\n" + open(errlog).read()[-800:])
        self.assertEqual(proc.returncode, 2)
        err = open(errlog).read()
        self.assertIn("is mode 0777, writable by other local users", err)
        self.assertIn("found at beat", err)
        kinds = [r["kind"] for r in self._hostlog()]
        self.assertIn("host-started", kinds)
        self.assertIn("state-root-refused", kinds)
        self.assertEqual(_mode(self.state), 0o700, "read before repair: re-tightened on the way out")

    def test_a_planted_spec_is_refused_and_the_host_does_not_start(self):
        """The spec itself is read through the guard (the host directory is <root>/hosts/<sid>): a spawn.json replaced by
        a symlink to a file elsewhere is quarantined, and the host exits 2 naming the spec, never running a CLI the
        planted spec names."""
        spec_path = self._spec()
        elsewhere = Path(tempfile.mkdtemp(), "spawn.json")
        elsewhere.write_text(Path(spec_path).read_text())
        os.unlink(spec_path)
        os.symlink(elsewhere, spec_path)
        r = subprocess.run([sys.executable, os.path.join(BIN, "romp-session-host"), spec_path], env=self._env(),
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 2, r.stderr[-800:])
        self.assertIn("spawn.json is a symlink: quarantined to", r.stderr)
        self.assertIn("cannot read the spawn spec", r.stderr)
        self.assertFalse(os.path.lexists(spec_path))
        self.assertTrue(any(n.endswith(".hosts.%s.spawn.json" % self.sid) for n in os.listdir(os.path.join(self.state, "quarantine"))))
        self.assertFalse(os.path.exists(self.fake_log))


# ── ONE TEXT: the predicate lives in kernel/state_root_mode.py alone (round 3's F) ────────────────────────────────

class TheFloorReachesEveryMintedRoot(unittest.TestCase):
    """tests-5 and extra8-6 of round 3, and the round-4 review's finding on their reach: the 0700 floor for a privately
    minted state root lives in ONE place, jd._rebind_state, which chmods the root when it exists and is this uid's, so it
    reaches a root a test makes only when the test binds it through the seam AFTER the directory exists. About thirty
    sites in twenty-two test modules made their root with a bare mkdir at the umask's mode (0775 under 0002) and bound it
    bare, or bound it through the seam before making it, so the floor never saw it: green on a user-private-group box
    (warn-class), a killed worker on a box whose primary group is shared. Those sites now bind through
    `jd._rebind_state(root, make=True)`, and this pin holds the rule by construction, as an AST fact over every
    tests/*.py: (a) no `<x>.jd.STATE.mkdir(...)` (a root bound first and made after); (b) no bare `<x>.jd.STATE = <name>`
    where the same scope made `<name>` with mkdir, os.mkdir or os.makedirs and did not chmod it itself (a root a test
    loosens or locks on purpose is its own subject and stays bare). A root taken from mkdtemp or TemporaryDirectory is
    0700 already and is outside the hazard."""

    @staticmethod
    def _offences(src, rel="<src>"):
        tree = ast.parse(src)
        enclosing = {}

        def visit(node, cur):
            for child in ast.iter_child_nodes(node):
                enclosing[id(child)] = cur
                visit(child, child if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) else cur)
        visit(tree, None)

        def scope(fn):
            return list(ast.walk(fn)) if fn is not None else [n for n in ast.walk(tree) if enclosing.get(id(n)) is None]
        out = []
        for n in ast.walk(tree):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "mkdir" \
                    and ast.unparse(n.func.value).endswith("jd.STATE"):
                out.append("%s:%d bare mkdir of the bound root: %s" % (rel, n.lineno, ast.unparse(n)))
            if isinstance(n, ast.Assign):
                for tgt in n.targets:
                    pairs = list(zip(tgt.elts, n.value.elts)) if isinstance(tgt, ast.Tuple) and isinstance(n.value, ast.Tuple) else [(tgt, n.value)]
                    for t, v in pairs:
                        if not (ast.unparse(t).endswith("jd.STATE") and isinstance(v, ast.Name)):
                            continue
                        made = chmoded = False
                        for m in scope(enclosing.get(id(n))):
                            if not (isinstance(m, ast.Call) and getattr(m, "lineno", 0) < n.lineno):
                                continue
                            f = ast.unparse(m.func)
                            first = ast.unparse(m.args[0]) if m.args else ""
                            if f == v.id + ".mkdir" or (f in ("os.makedirs", "os.mkdir") and first.startswith(v.id)):
                                made = True
                            if f in ("os.chmod", v.id + ".chmod") and (not m.args or first.startswith(v.id) or f.startswith(v.id)):
                                chmoded = True
                        if made and not chmoded:
                            out.append("%s:%d a root this scope made is bound bare: %s" % (rel, n.lineno, ast.unparse(n)))
        return out

    def test_no_test_binds_a_root_it_made_bare(self):
        bad = []
        for f in sorted(os.listdir(HERE)):
            if f.endswith(".py"):
                bad += self._offences(open(os.path.join(HERE, f), encoding="utf-8").read(), "tests/" + f)
        self.assertEqual(bad, [], "bind the root through jd._rebind_state(root, make=True), which floors it at 0700:\n" + "\n".join(bad))

    def test_the_pin_reds_on_both_shapes_and_passes_the_seam_and_a_deliberate_mode(self):
        a = "def setUp(self):\n    km.jd.STATE = Path(self.tmp) / 'state'\n    km.jd.STATE.mkdir(parents=True, exist_ok=True)\n"
        b = "def setUp(self):\n    root = Path(self.tmp) / 'state'\n    root.mkdir()\n    jd.STATE = root\n"
        c = "def setUp(self):\n    root = Path(self.tmp) / 'state'\n    os.makedirs(root)\n    self.jd.STATE = root\n"
        ok1 = "def setUp(self):\n    km.jd._rebind_state(Path(self.tmp) / 'state', make=True)\n"
        ok2 = "def test(self):\n    locked = Path(self.tmp) / 'locked'\n    locked.mkdir()\n    os.chmod(locked, 0o000)\n    self.jd.STATE = locked\n"
        ok3 = "def setUp(self):\n    self.td = tempfile.TemporaryDirectory()\n    jd.STATE = Path(self.td.name)\n"
        self.assertEqual(len(self._offences(a)), 1, self._offences(a))
        self.assertEqual(len(self._offences(b)), 1, self._offences(b))
        self.assertEqual(len(self._offences(c)), 1, self._offences(c))
        for ok in (ok1, ok2, ok3):
            self.assertEqual(self._offences(ok), [], ok)


class OneText(unittest.TestCase):
    """extra8-4, tests-2, kernel-4, extra7-1 and extra7-2 of round 3: the security predicate lived in two independently
    editable copies under KEEP IN SYNC comments and drifted within a day. Now it has one text: kernel/state_root_mode.py.
    The gate here is the ServeTokenLoadersMatch shape (an AST fact, any divergence red): none of the loaders
    (kernel/judge.py, kernel/event_model.py, postal/postal_service.py, kernel/session_host.py, bin/romp-session-host)
    defines a function or class the shared module exports, each loads the file by path under the fixed module name
    romp_state_root_mode, and no KEEP IN SYNC comment about the state root remains. The one copy the repo keeps on
    purpose, the serve-token loader, stays under its own AST-identity gate (tests/test_kernel_serve_token_mode.py), and
    its two new guards (O_NOFOLLOW on the lock, the bounded wait) are pinned equal here too."""
    LOADERS = ("kernel/judge.py", "kernel/event_model.py", "postal/postal_service.py", "kernel/session_host.py", "bin/romp-session-host",
               "kernel/logins.py", "kernel/palette.py", "kernel/host_transport.py", "kernel/sdk_backend.py", "kernel/codex_backend.py",
               "kernel/codex_runtime.py")       # the last six: handed the root per call, each builds the shared Reader (round 4's review)
    WRITE_BIT_LITERALS = {0o022, 0o002, 0o020}
    WRITE_BIT_NAMES = {"stat.S_IWGRP", "stat.S_IWOTH", "S_IWGRP", "S_IWOTH"}

    def _tree(self, rel):
        import ast
        return ast.parse(open(os.path.join(ROOT, rel), encoding="utf-8").read(), filename=rel)

    def test_no_loader_defines_a_copy_of_the_shared_modules_functions(self):
        import ast
        shared = self._tree("kernel/state_root_mode.py")
        exported = {n.name for n in shared.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and not n.name.startswith("_")}
        self.assertTrue({"check", "import_read_refusal", "private_group", "writable_by_another", "trusted_path", "quarantine",
                         "Reader", "errno_text", "errno_name", "relative_under"} <= exported, exported)
        for rel in self.LOADERS:
            names = {n.name for n in ast.walk(self._tree(rel)) if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
            self.assertEqual(names & exported, set(), "%s defines a copy of %r" % (rel, sorted(names & exported)))
            src = open(os.path.join(ROOT, rel), encoding="utf-8").read()
            self.assertIn('"romp_state_root_mode"', src, "%s loads the shared module under its fixed name" % rel)
            self.assertIn("state_root_mode.py", src)
            self.assertNotIn("_state_root_mode_check", src, "%s: round 2's reduced copy is gone" % rel)
            self.assertNotIn("STATE_ROOT_REFUSE_MASK", src)

    @classmethod
    def _write_bit_tests(cls, tree):
        """Every `x & <write bit>` in `tree`: a BitAnd whose operand is one of the write-bit literals (0o022, 0o002, 0o020)
        or stat's S_IWGRP / S_IWOTH, the shape of a local copy of the discriminator under any name."""
        out = []
        for n in ast.walk(tree):
            if isinstance(n, ast.BinOp) and isinstance(n.op, ast.BitAnd):
                for side in (n.left, n.right):
                    if (isinstance(side, ast.Constant) and side.value in cls.WRITE_BIT_LITERALS) or ast.unparse(side) in cls.WRITE_BIT_NAMES:
                        out.append((n.lineno, ast.unparse(n)))
        return out

    def test_no_loader_tests_a_mode_against_a_write_bit_under_any_name(self):
        """The round-4 review's sharpening of this gate: the name pins above red only on a copy that reuses an exported
        name; a renamed copy (`def _root_is_loose(root): return bool(S_IMODE(...) & 0o022)`) passed both. This holds the
        SHAPE: in every loader and in kernel/kernel.py, no expression ands a mode with a write bit (the literals 0o022,
        0o002 and 0o020, or stat's S_IWGRP and S_IWOTH); the discriminator's bits live in kernel/state_root_mode.py alone
        (WRITE_BITS), and a loader that needs them references that constant. The pin reds on the renamed copy (checked
        below on the bus's source with the copy appended)."""
        for rel in self.LOADERS + ("kernel/kernel.py",):
            hits = self._write_bit_tests(self._tree(rel))
            self.assertEqual(hits, [], "%s tests a mode against a write bit: %r" % (rel, hits))
        bus = open(os.path.join(ROOT, "postal", "postal_service.py"), encoding="utf-8").read()
        for copy in ("\n\ndef _root_is_loose(root):\n    return bool(stat.S_IMODE(os.stat(root).st_mode) & 0o022)\n",
                     "\n\ndef _loose(mode):\n    return mode & stat.S_IWOTH or mode & 0o020\n"):
            hits = self._write_bit_tests(ast.parse(bus + copy))
            self.assertTrue(hits, "the pin reds on the renamed copy")

    def test_no_keep_in_sync_comment_about_the_state_root_remains(self):
        for rel in ("kernel/judge.py", "kernel/kernel.py", "postal/postal_service.py", "kernel/session_host.py", "kernel/event_model.py"):
            src = open(os.path.join(ROOT, rel), encoding="utf-8").read()
            for i, line in enumerate(src.splitlines(), 1):
                if "KEEP IN SYNC" in line:
                    self.assertNotIn("state root", line.lower(), "%s:%d keeps the state-root predicate in sync by hand" % (rel, i))
                    self.assertNotIn("state_root", line, "%s:%d" % (rel, i))

    def test_the_two_daemons_hold_one_module_object_and_the_readers_share_the_class(self):
        ps = load_source("romp_postal_srm_probe", os.path.join(BIN, "romp-postal-service"))
        self.assertIs(ps._srm, srm)
        self.assertIs(type(ps._gr), srm.Reader)
        self.assertIs(type(km._gr), srm.Reader)
        self.assertIs(type(jd._gr), srm.Reader)
        self.assertIs(type(em._gr), srm.Reader)
        self.assertEqual(ps._gr.root_fn(), ps.STATE.parent)

    def test_the_serve_token_loaders_carry_the_same_two_guards_and_one_wait(self):
        for rel, name in (("kernel/kernel.py", "_serve_token_read_or_mint"), ("postal/postal_service.py", "_serve_token_read_or_mint")):
            src = open(os.path.join(ROOT, rel), encoding="utf-8").read()
            body = src[src.index("def %s(" % name):]
            body = body[:body.index("\ndef ", 10)]
            self.assertIn("os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600", body, "%s: the lock is opened O_NOFOLLOW" % rel)
            self.assertIn("SERVE_TOKEN_LOCK_WAIT_S", body, "%s: the wait for the lock's holder is bounded" % rel)
            self.assertIn("mkdir(parents=True, exist_ok=True, mode=0o700)", body, "%s: a root this call makes is 0700 from its first instant" % rel)
            self.assertNotIn("fcntl.flock(lfd, fcntl.LOCK_EX)\n", body, "%s: no unbounded blocking take" % rel)
        self.assertEqual(km.SERVE_TOKEN_LOCK_WAIT_S, 30)
        ps = load_source("romp_postal_srm_probe", os.path.join(BIN, "romp-postal-service"))
        self.assertEqual(ps.SERVE_TOKEN_LOCK_WAIT_S, km.SERVE_TOKEN_LOCK_WAIT_S)
        bus = open(os.path.join(ROOT, "postal", "postal_service.py"), encoding="utf-8").read()
        serve = bus[bus.index("def serve():"):bus.index("\ndef ", bus.index("def serve():") + 10)]
        self.assertIn("STATE.parent.mkdir(parents=True, exist_ok=True, mode=0o700)", serve, "serve() makes the root 0700 at the mkdir")

    def test_a_held_serve_token_lock_ends_in_a_loud_fault_not_a_hang(self):
        """extra5-4 of round 3 by execution: another process holds serve-token.lock flocked and never lets go; the loader
        waits the bound (lowered here) and faults naming the lock and the timeout, so a planted lock held open cannot
        hang a start forever. Under a symlinked lock path the open refuses (ELOOP) instead of opening the target."""
        import fcntl
        root = Path(tempfile.mkdtemp())
        lock = root / "serve-token.lock"
        fd = os.open(str(lock), os.O_RDWR | os.O_CREAT, 0o600)
        self.addCleanup(os.close, fd)
        fcntl.flock(fd, fcntl.LOCK_EX)
        t0 = time.monotonic()
        with mock.patch.object(km, "SERVE_TOKEN_LOCK_WAIT_S", 1), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(RuntimeError) as cm:
                km._serve_token_read_or_mint(root / "serve-token", "test")
        self.assertLess(time.monotonic() - t0, 10, "bounded")
        self.assertIn("take the lock within 1 s", str(cm.exception))
        self.assertIn("ETIMEDOUT", str(cm.exception))
        self.assertIn(str(lock), str(cm.exception))
        # a symlink at the lock path: never followed
        root2 = Path(tempfile.mkdtemp())
        elsewhere = Path(tempfile.mkdtemp(), "elsewhere.lock")
        elsewhere.write_text("")
        os.symlink(elsewhere, root2 / "serve-token.lock")
        (root2 / "serve-token").write_text("tok-DO-NOT-USE\n"); os.chmod(root2 / "serve-token", 0o600)
        with contextlib.redirect_stderr(io.StringIO()):
            v = km._serve_token_read_or_mint(root2 / "serve-token", "test")   # the lock cannot be taken (ELOOP): an existing tight token is used as is
        self.assertEqual(v, "tok-DO-NOT-USE")
        self.assertEqual(elsewhere.read_text(), "", "nothing opened through the link")


if __name__ == "__main__":
    unittest.main()
