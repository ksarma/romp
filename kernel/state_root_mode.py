"""The state root's trust boundary: ONE implementation for the kernel, the postal bus and the session host (2026-09-20,
round 4 of the review).

Loaded by path under the fixed module name romp_state_root_mode by kernel/judge.py (load_source), by kernel/event_model.py,
by postal/postal_service.py and by kernel/session_host.py (importlib, the same file), so every long-lived writer under
one state root judges it by one rule and says it in one voice (romp-manager, 2026-09-20: "one implementation imported
twice"; a comment marked KEEP IN SYNC is not a mechanism, and the two copies the repo carried drifted within a day).
Stdlib only, and nothing from kernel/ beside this file. tests/test_state_root_mode.py's OneText pins that none of the
loaders defines a copy of any function here.

Four things live here.

1. THE ROOT'S VERDICT (check, import_read_refusal). THE DISCRIMINATOR: "writable by another local user" means the
   mode carries an OTHER write bit, or it carries a GROUP write bit and the group is not the owner's private group. A
   group is the owner's PRIVATE group when the group database lists no member but the owner and no other account has
   the gid as its primary group. On a box with user-private groups a directory made at the umask's mode under umask
   0002 reads 0775 and is writable by nobody but its owner, so it is warn-class (re-tightened and reported once), not
   a refusal; the same 0775 under a shared group (users, staff, a project group) is writable by every member and is
   refused; an other write bit is refused with no lookup at all. LOOKUP FAILURE IS RESTRICTED, AND DISTINCT: a group
   database that cannot be read (KeyError: no entry for the gid or the owner's uid; an OSError from the name service)
   or that does not answer within the bound counts as writable, with its own line and remedy ("the group database
   could not be read (...): check getent group <gid> and the name service; romp refuses until it can tell who else
   can write here"), never the distrust remedy. The lookup is BOUNDED (a daemon thread joined with LOOKUP_BOUND_S) and
   memoized per (gid, uid) for PRIVATE_MEMO_S when the real database answers, so a hung name service cannot hang the
   import, the boot, a request or a poll, and the readers below cost one lookup per group, not one per read. READ
   BEFORE REPAIR: check() reads the mode first and takes its verdict from that read; the best-effort chmod 0700 runs
   after and is reported, never relied on. The check never creates the root. A root path that exists and is NOT A
   DIRECTORY is verdict refuse with ENOTDIR and its own remedy (regression-1 of round 3), at every check. THE
   IMPORT-READ RULE: import_read_refusal() judges the mode a process read BEFORE its own first chmod on a pre-existing
   root that HELD ENTRIES: writable by another local user then, whatever the chmod did afterwards, is a refusal with
   the distrust remedy (entries planted while it was writable are not to be trusted; the guarded readers quarantine
   what they meet). A root that was EMPTY at that read is a creation default, whoever made it (correctness-3 of round
   3: the manager, the CLI and every harness make the root at the umask's mode a moment before the judge import
   tightens it, and nothing could have been planted in an empty directory).

2. THE GUARD (trusted_path): every component from the state root down to a path, lstat'ed: not a symlink, owned by
   this process's uid, and not writable by another local user by the same discriminator (a 0775 venv or a 0664 mirror
   under the owner's private group PASSES; the property is ownership plus the absence of a symlink plus the
   discriminator, never the directory's mode alone and never a plain "no group or other bit"). The root itself is
   resolved (a legitimate root reached through a symlink stays legitimate; tests/test_asm_checkpoint.py relies on it)
   and judged the same way. A path that is not under the root is not the root's to guard ("outside").

3. THE GUARDED READERS (Reader): read_text, read_bytes, open, os_open, gzip_open, stat, exists, isdir, listdir, scandir,
   iterdir, glob, dir, sys_path_dir, each built on trusted_path and each performing the read itself through THE SAME
   PATHLIB OR OS PRIMITIVE THE SITE USED BEFORE ROUND 4 (the primitive rule, below), each of which QUARANTINES on failure: the first failing
   component under the root is renamed to <root>/quarantine/<utc-stamp>.<relative-path-with-slashes-as-dots> (the
   quarantine directory created 0700), one stderr line says so, one refused-kind row is filed through the caller's hook
   naming the path and the reason (owner, symlink, writable by another, or the lookup failure), and the reader then
   behaves AS IF THE PATH WERE ABSENT: FileNotFoundError from the readers that raise it for a missing file, an empty
   listing from the directory readers, False from isdir and exists, nothing added from sys_path_dir. A quarantine that
   itself fails (EPERM, a busy mount) says so and still reads absent. A FAULT IS NOT A PLANT (round 4d, 2026-09-21):
   an EACCES or EPERM (any errno but ENOENT and ENOTDIR) on the lstat of a component whose parent the walk has just
   trusted (this uid's, not a symlink, not writable by another local user, so holding nothing another uid put there;
   an owner-only directory of ours with no search bit, 0600 or 000, is the case met) is the directory's fault and not
   an entry's untrustworthiness: nothing is quarantined, no line is said and no row is filed, and the reader runs the
   site's primitive, which raises the fault as the site's bare read raised it before round 4 (PermissionError from
   Path.read_text; Path.exists answers as its interpreter's pathlib does), so a caller's own fault handling still
   sees it (the judge's _reg_spawned_at files a judge-errors row and plans the session on a sentinel, where the
   round-4 readers answered absent and the session was keyed as if its reg were gone). A ROOT that itself fails the guard (gone, not a
   directory, another uid's, writable by another) is the gate's case, not an entry's: the readers read absent,
   quarantine nothing, file no row, and say it once per process per root and cause. Nothing ever adopts a declined artifact and
   nothing is merely skipped: a skipped plant is re-adopted at the next boot (the ruling's B), a quarantined one is
   not. The population of readers is derived by code, not by hand: tests/test_state_root_readers.py's AST census over
   the kernel, the judge, the event model, the bus, the session host and the kernel-side modules the kernel hands the
   root to (logins, palette, host_transport, sdk_backend, codex_backend, codex_runtime) lists every read of a path
   derived from the state root and fails for one that neither goes through a Reader nor sits on its allowlist with a
   reason. A Reader built with no row hook of its own files through REFUSED_HOOKS, the process-wide list the kernel
   registers its error-centre hook in, so a helper module's reader (built per call over the root it was handed) files
   the same row as the kernel's own.

THE PRIMITIVE RULE (round 4c, 2026-09-21): after the guard's walk a reader performs the read through the pathlib or os
call the site used before round 4, chosen by the argument's kind: a pathlib.Path takes Path.read_text, Path.read_bytes,
Path.stat, Path.exists, Path.is_dir, Path.iterdir, Path.glob; a str takes os.stat, os.path.exists, os.path.isdir,
os.listdir, glob.glob; open is builtins.open, os_open is os.open with the flags as given, gzip_open is gzip.open; listdir
and scandir are os.listdir and os.scandir. Never a descriptor open of the Reader's own. The suite's fixtures count and
fault the kernel's reads by interposing on those names (Path.read_text, Path.read_bytes, Path.stat, builtins.open), and
twenty-two test modules unchanged since the round-2 head hold that contract: round 4's os.open(O_NOFOLLOW | O_CLOEXEC)
plus io.open(fd) made 95 of their tests blind to the reads and they failed (the round-4 sweep). The O_NOFOLLOW closed
nothing a peer could use: the walk refused a symlink at every component, and what remains between the walk and the
primitive's own open is a same-uid race (this process's uid replacing a judged component; the gate admits only a root
not writable by another local user, 0700 in the ordinary case and, when the chmod was refused and the boot warned, a
looser mode writable by nobody but its owner, 0755 for one, and the walk has just judged every directory from the root
down to the path the same way, so no other uid can create, rename or link an entry in any of them), which no flag on a
final open by path closes for a process against itself.

THE BOUNDARY NO CHECK CAN CLOSE: a descriptor a peer opened inside the root while it was writable survives the
tightening (POSIX checks permission at open, not per operation), so remove-and-recreate is the boundary of what any of
this promises; the checks refuse the window and quarantine what was planted in it. Beside it, the window between the
guard's walk and the primitive's open is this uid's alone (the primitive rule above): no directory the walk passed is
writable by another local user, whatever its exact mode (the root is 0700 in the ordinary case, and a looser mode
writable by nobody but its owner when its chmod was refused and the boot warned), so every other uid is kept out of it.
plans/state-root-mode.md records the method.

4. THE OWNER-ONLY CREATORS (make_dir, write_text, write_bytes, open_private, touch; round 4f, 2026-09-21): every entry
   the kernel, the judge, the event model, the bus, the session host and the handed-root modules CREATE under the root
   is born owner-only BY CODE, whatever the process umask. romp-manager's ruling: "if the kernel and the host make
   entries under the root at the process umask, then under a permissive umask the readers quarantine the process's OWN
   FRESH ENTRIES. That is a self-inflicted denial road, and 'the live umask is 0002 with private groups' is a bound held
   by the environment rather than by the code." A directory is made by make_dir: os.mkdir at 0700 (a umask removes
   bits and never adds one, so 0700 holds under every umask), and one that already existed as a directory of ours at a
   looser mode is TIGHTENED to 0700 (an entry an older process made at the umask's mode); a symlink, a non-directory
   or another uid's directory at the path is refused, never tightened through. The ROOT itself is never tightened by a
   writer (its mode is the gate's to READ BEFORE IT REPAIRS: a writer that tightened it first would hide a loosening
   from the check, the sibling's-repair finding of round 4d), and an absent root is made 0700, a creation default.
   A file is BORN at 0600 before its first byte: the creators open it O_WRONLY|O_CREAT at 0600, fchmod the descriptor
   0600 (exact under any umask, and the repair of an existing file at a looser mode) and close, and THEN run the
   primitive the site used (Path.write_text, Path.write_bytes, builtins.open in a write or append mode, Path.touch),
   so the suite's fixtures that count or fault a write by interposing on those names still meet it (the primitive rule
   of round 4c, on the write side). The population of creators is derived by code, not by hand:
   tests/test_state_root_writers.py's AST census over the eleven modules lists every call that creates an entry under
   a root-derived path (mkdir, makedirs, write_text, write_bytes, a write-mode open, os.open with O_CREAT, a tempfile
   with dir under the root, touch, a copy, rename, replace or link whose destination is under the root, a write-mode
   gzip.open) and fails for one that is neither through these creators nor a rename whose source is itself an entry
   born under the root (the mode travels with the inode) nor on its allowlist with a reason (a site that sets its mode
   by code itself: the serve-token mint, write_reg, write_lease, the bus root's mkdir, the atomic publisher's
   descriptor). tests/test_state_root_mode.py's EntriesAreBornOwnerOnlyUnderAPermissiveUmask drives the kernel, the
   bus and the session host under umask 0022 and 0000 in child processes and holds that nothing of their own is
   quarantined and every entry they made lstat's owner-only.

Injectable lookups (getgrgid, getpwall, getpwuid, bound) are keyword arguments on every entry point, resolved AT CALL
TIME to grp.getgrgid, pwd.getpwall, pwd.getpwuid and LOOKUP_BOUND_S when None (so a test that patches grp or pwd, or
sets LOOKUP_BOUND_S on this module, is seen), so tests drive the discriminator without a second account on the box
(tests/test_state_root_mode.py, Discriminator).

Command line (for bin/romp-sdk-setup, a shell script): `python3 state_root_mode.py trusted <root> <path>` exits 0 when
the path is trusted or absent, 1 when it was refused (and quarantined, with the line on stderr), 2 on a usage error.
"""
import errno
import glob as _glob
import grp
import gzip as _gzip
import os
import pathlib
import pwd
import stat
import sys
import threading
import time

MODULE_NAME = "romp_state_root_mode"   # the fixed sys.modules name every loader uses, so one process holds one copy
TARGET_MODE = 0o700
OTHER_WRITE = 0o002
GROUP_WRITE = 0o020
WRITE_BITS = OTHER_WRITE | GROUP_WRITE   # the bits the discriminator judges (0o022); a set bit is not by itself a refusal
LOOKUP_BOUND_S = 3.0                     # the group database's answer is waited for this long, then counted as unreadable
PRIVATE_MEMO_S = 300.0                   # a private-group answer from the REAL database stands this long (the readers' cost)
QUARANTINE_DIR = "quarantine"            # <root>/quarantine, created 0700, holds what the readers declined
OWNER_ONLY_DIR = 0o700                   # the mode every directory a writer makes under the root is born at (make_dir)
OWNER_ONLY_FILE = 0o600                  # the mode every file a writer makes under the root is born at (the creators, part 4)

DISTRUST_REMEDY_BELL = ("remove serve-token, repo-root and every entry you did not make, or recreate the root, then "
                        "chmod 700 it (its contents are not to be trusted)")

_PRIVATE_MEMO = {}          # (gid, uid) -> (private, why, wall time, the three lookup callables the answer came from)
_PRIVATE_MEMO_LOCK = threading.Lock()
REFUSED_HOOKS = []          # (path, reason, line) callables for a Reader built with no on_refused of its own (the helper modules
#                             the kernel hands its root to): the kernel registers its error-centre row hook here at import
_ROOT_FAILURE_SAID = set()  # (root, detail) pairs a reader has said "read as absent: the root itself failed" for, once per process


def errno_text(e):
    """"ENAME: strerror" for an OSError, from its errno alone (errno.errorcode and os.strerror), never str(e), which
    carries the path: "EPERM: Operation not permitted". An OSError raised with no errno reads as its type name and
    its strerror when it has one."""
    code = getattr(e, "errno", None)
    if code is None:
        return "%s: %s" % (type(e).__name__, getattr(e, "strerror", None) or "no errno")
    return "%s: %s" % (errno.errorcode.get(code, "E%d" % code), os.strerror(code))


def errno_name(text):
    """The errno name at the head of an errno_text ("EPERM" of "EPERM: Operation not permitted"), or None."""
    return text.split(":", 1)[0] if text else None


def _bounded(fn, bound):
    """fn() in a daemon thread joined for `bound` seconds: (result, None), or (None, exception) when fn raised, or
    (None, "timeout") when it did not answer in time (the thread is left to finish on its own; a daemon never holds
    the process). The thread carries Python's default name, which the kernel's stack sample folds to "thread"."""
    box = {}

    def run():
        try:
            box["r"] = fn()
        except BaseException as e:      # the name service can raise anything; every fault is the caller's to name
            box["e"] = e
    t = threading.Thread(target=run, daemon=True, name="state-root-group-lookup")
    t.start()
    t.join(bound)
    if t.is_alive():
        return None, "timeout"
    if "e" in box:
        return None, box["e"]
    return box.get("r"), None


def private_group(gid, uid, *, getgrgid=None, getpwall=None, getpwuid=None, bound=None):
    """Whether `gid` is `uid`'s PRIVATE group. (True, None): the group lists no member but the owner and no other account
    has it as its primary gid. (False, why): shared, `why` naming what makes it so as COUNTS ("group 100 is shared: 3
    other members, 2 other accounts with it as their primary group"), never account names. (None, why): the database
    could not be read or did not answer within `bound`, `why` the failure text ("KeyError: no group entry for gid 100";
    "ENOENT: No such file or directory"; "timeout: the group database did not answer within 3 s"). One bounded call
    covers the three lookups. The lookups and the bound default at call time (grp.getgrgid, pwd.getpwall, pwd.getpwuid,
    LOOKUP_BOUND_S). A definite answer is memoized per (gid, uid) for PRIVATE_MEMO_S of wall time, together with the
    three callables it came from: a later call with the SAME callables (the real database; the perf bench's counting
    wrapper) hits it, a call with others (a test's injected fakes, fresh closures) does not, so a patched database is
    always seen and the guarded readers cost one lookup per group, not one thread per read. A failure is asked again."""
    getgrgid = getgrgid or grp.getgrgid
    getpwall = getpwall or pwd.getpwall
    getpwuid = getpwuid or pwd.getpwuid
    bound = LOOKUP_BOUND_S if bound is None else bound
    with _PRIVATE_MEMO_LOCK:
        hit = _PRIVATE_MEMO.get((gid, uid))
    if (hit is not None and hit[3] is getgrgid and hit[4] is getpwall and hit[5] is getpwuid
            and 0 <= time.time() - hit[2] < PRIVATE_MEMO_S):
        return hit[0], hit[1]

    def look():
        try:
            owner = getpwuid(uid).pw_name
        except KeyError:
            raise KeyError("no passwd entry for uid %d" % uid)
        try:
            members = [m for m in (getgrgid(gid).gr_mem or ()) if m != owner]
        except KeyError:
            raise KeyError("no group entry for gid %d" % gid)
        primaries = [p for p in getpwall() if p.pw_gid == gid and p.pw_uid != uid]
        return members, primaries
    got, err = _bounded(look, bound)
    if err == "timeout":
        return None, "timeout: the group database did not answer within %g s" % bound
    if err is not None:
        if isinstance(err, KeyError):
            return None, "KeyError: %s" % (err.args[0] if err.args else "no entry")
        if isinstance(err, OSError):
            return None, errno_text(err)
        return None, "%s: the group database raised" % type(err).__name__
    members, primaries = got
    if not members and not primaries:
        result = (True, None)
    else:
        parts = []
        if members:
            parts.append("%d other member%s" % (len(members), "" if len(members) == 1 else "s"))
        if primaries:
            parts.append("%d other account%s with it as %s primary group"
                         % (len(primaries), "" if len(primaries) == 1 else "s", "its" if len(primaries) == 1 else "their"))
        result = (False, "group %d is shared: %s" % (gid, ", ".join(parts)))
    with _PRIVATE_MEMO_LOCK:
        _PRIVATE_MEMO[(gid, uid)] = (result[0], result[1], time.time(), getgrgid, getpwall, getpwuid)
    return result


def forget_private_groups():
    """Drop the memo (a test that changes the group database between two reads; nothing in production calls it)."""
    with _PRIVATE_MEMO_LOCK:
        _PRIVATE_MEMO.clear()


def prime_private_group():
    """Ask the real database about this process's own primary group once, at a loader's import: the files under the
    root are this account's, so the readers' group judgments hit the memo from the first read, and the one bounded
    lookup thread runs at import rather than inside a builder (tools/perf-bench.py counts threads a builder starts)."""
    try:
        private_group(os.getgid(), os.geteuid())
    except Exception:
        pass


def writable_by_another(mode, uid, gid, **lookups):
    """The discriminator over one read: (writable, cause, detail). `writable` is True, False, or None when the lookup
    failed (counted as writable: the restricted side). `cause`: "other" (an other write bit; no lookup), "group" (a
    group write bit under a shared group), "private-group" (a group write bit under the owner's private group: NOT
    writable by another), "lookup" (the database could not be read), or None (no group or other write bit).
    `detail`: the shared-group text or the lookup failure text, else None."""
    if mode & OTHER_WRITE:
        return True, "other", None
    if mode & GROUP_WRITE:
        private, why = private_group(gid, uid, **lookups)
        if private is None:
            return None, "lookup", why
        if private:
            return False, "private-group", None
        return True, "group", why
    return False, None, None


def _how(cause, detail):
    """What made the read writable by another, for the full line: the bit, or the shared group's counts."""
    return "an other write bit" if cause == "other" else detail


def _how_short(cause):
    """The same for the bounded surface (the bell row's point): the counts stay on the line."""
    return "an other write bit" if cause == "other" else "a shared group"


def _lookup_remedy(gid):
    return ("check getent group %s and the name service; romp refuses until it can tell who else can write here"
            % ("<gid>" if gid is None else gid))


def _not_a_directory_remedy(r):
    return ("the state root path %s exists and is not a directory: remove it and recreate the root as a directory (or "
            "point ROMP_STATE_DIR at one)" % r)


def check(root, *, extra_err=None, list_entries=False, **lookups):
    """The state root's mode as a verdict, for the kernel's import gate, its boot check, its re-check, the bus's start
    and poll gates and the session host's start and beat. Returns a dict: root (str), modeRead (int or None: the mode
    as READ, before any repair), modeReadText ("%04o" or None), uid and gid (of that read, or None), verdict ("ok" |
    "warn" | "refuse" | "unknown"), writableBy ("other" | "group" | None: what made the read writable by another local
    user), groupPrivate (True when a group write bit was judged under the owner's private group, False under a shared
    one, None when no group bit or the lookup failed), lookupError (the group database's failure text, or None),
    notDirectory (True when the path exists and is not a directory: verdict refuse, statErrno ENOTDIR), entries (the
    root's entry names as listed at this read when `list_entries`, else None; None too when the listing failed),
    repaired (bool: this call's chmod changed the mode to 0700), modeAfter (int or None: the mode read back after the
    repair), err (str or None: the failed stat and/or chmod, each as "ENAME: strerror", plus `extra_err` verbatim),
    repairError (the chmod's "ENAME: strerror" or None), statErrno and repairErrno (the errno names, for a caller
    keying transitions on the cause), line (the one full sentence to say, naming the root; None when nothing is to be
    said), point (the same fact with no path, for a bounded surface), remedy (str, naming the root), remedyPublic (the
    remedy with the root named as "the state root"), bellRemedy (a short path-free remedy) and t (time.time()).

    Verdict, from the read: writable by another local user (the discriminator in the module docstring), or a lookup
    that failed, is "refuse"; a path that is not a directory is "refuse" (ENOTDIR: no chmod is attempted on it); any
    other mode that is not 0700 is "warn", a privacy fault and not a code-execution one (0755, 0750, 0711, and 0775 or
    0770 under the owner's private group); 0700 is "ok"; a root whose mode cannot be read is "unknown", which every
    caller treats as refuse-class. A root that reads 0700 but whose chmod failed (a root another uid owns) is verdict
    ok WITH a line: the mode is right today and not this uid's to keep, so the failed chmod is the signal. THEN the
    best-effort chmod 0700, reported, only when there was a directory to chmod. `extra_err` is a caller's own error
    text to fold into err and the line (the judge module's failed import call, labelled as the import's). `lookups`:
    getgrgid, getpwall, getpwuid, bound (see private_group)."""
    r = os.fspath(root)
    stat_err, st, mode, not_dir = None, None, None, False
    try:
        st = os.stat(r)
        mode = stat.S_IMODE(st.st_mode)
        if not stat.S_ISDIR(st.st_mode):
            not_dir = True
            stat_err = errno_text(NotADirectoryError(errno.ENOTDIR, os.strerror(errno.ENOTDIR)))
    except OSError as e:
        stat_err = errno_text(e)
    uid = gid = None
    writable, cause, detail = None, None, None
    entries = None
    if mode is None:
        verdict = "unknown"
    elif not_dir:
        verdict = "refuse"
        uid, gid = st.st_uid, st.st_gid
    else:
        uid, gid = st.st_uid, st.st_gid
        writable, cause, detail = writable_by_another(mode, uid, gid, **lookups)
        if writable or writable is None:
            verdict = "refuse"
        elif mode != TARGET_MODE:
            verdict = "warn"
        else:
            verdict = "ok"
        if list_entries:
            try:
                entries = sorted(os.listdir(r))
            except OSError:
                entries = None
    # THEN the repair, best-effort and reported: only when there was a directory to chmod (a stat that failed means no
    # directory to chmod, and never a mkdir; a file at the path is not chmod'ed to 0700 either)
    repair_err, mode_after = None, mode
    if mode is not None and not not_dir:
        try:
            os.chmod(r, TARGET_MODE)
        except OSError as e:
            repair_err = errno_text(e)
        try:
            mode_after = stat.S_IMODE(os.stat(r).st_mode)
        except OSError:
            mode_after = None
    repaired = mode is not None and mode != TARGET_MODE and repair_err is None and mode_after == TARGET_MODE
    errs = []
    if stat_err and not_dir:
        errs.append("not a directory: " + stat_err)
    elif stat_err:
        errs.append("stat failed: " + stat_err)
    if repair_err:
        errs.append("chmod 700 failed: " + repair_err)
    if extra_err:
        errs.append(extra_err)
    err = "; ".join(errs) or None
    not_ours = errno_name(repair_err) in ("EPERM", "EACCES")
    mode_text = ("%04o" % mode) if mode is not None else None
    fail = (" (%s)" % err) if err else ""
    retight = " (re-tightened to 0700 after the read; the refusal stands on what was read)" if repaired else ""
    private_clause = (" (its group write bit is under the owner's private group, which no other account holds)"
                      if cause == "private-group" else "")
    if verdict == "unknown":
        remedy = "restore the state root at %s (it could not be read: %s)" % (r, errno_name(stat_err))
        bell = "restore the state root (it could not be read: %s)" % errno_name(stat_err)
        point = "the state root's mode could not be read (%s)" % errno_name(stat_err)
        line = "state root %s could not be read%s: an unverified root is not served from; %s" % (r, fail, remedy)
    elif not_dir:
        remedy = _not_a_directory_remedy(r)
        bell = "the state root path is not a directory: remove it and recreate the root as a directory"
        point = "the state root path is not a directory (ENOTDIR)"
        line = ("state root %s exists and is not a directory (ENOTDIR): romp refuses to serve from it; %s" % (r, remedy))
    elif verdict == "refuse" and cause == "lookup":
        # the DISTINCT message: the database, not the root's contents, is what the operator must look at
        remedy = bell = _lookup_remedy(gid)
        point = ("the state root is mode %s (a group write bit) and the group database could not be read (%s)"
                 % (mode_text, detail.split(":", 1)[0]))
        line = ("state root %s is mode %s (a group write bit), and the group database could not be read (%s)%s: romp "
                "cannot tell who else can write here and refuses to serve from it%s; %s"
                % (r, mode_text, detail, fail, retight, remedy))
    elif verdict == "refuse":
        # the remedy restores the CONTENTS as well as the mode (fresh-1, then round 4's word): entries planted while
        # the root was writable are not to be trusted; the guarded readers quarantine what they meet under it
        remedy = ("remove serve-token, repo-root and every entry you did not make under %s, or recreate the root, then "
                  "chmod 700 it (entries planted while it was writable are not to be trusted; the next boot re-mints "
                  "them and quarantines what its readers refuse into %s/%s)" % (r, r, QUARANTINE_DIR))
        bell = DISTRUST_REMEDY_BELL
        if not_ours:
            remedy += (", which failed here (%s): make the root itself this uid's, not its entries (adopt nothing you "
                       "did not create)" % repair_err)
            bell = ("make the root itself this uid's, then remove serve-token, repo-root and every entry you did not make "
                    "under it (adopt nothing)")
        point = "the state root is mode %s, writable by other local users (%s)" % (mode_text, _how_short(cause))
        line = ("state root %s is mode %s, writable by other local users (%s)%s: romp refuses to serve from it%s; %s"
                % (r, mode_text, _how(cause, detail), fail, retight, remedy))
    elif verdict == "warn" and repaired:
        remedy = "nothing to do now (re-tightened to 0700); find what loosened %s" % r
        bell = "re-tightened to 0700; find what loosened it"
        point = "the state root was mode %s, re-tightened to 0700" % mode_text
        line = ("state root %s was mode %s, re-tightened to 0700%s%s: something loosened it after it was made 0700; %s"
                % (r, mode_text, private_clause, fail, remedy))
    elif verdict == "warn":
        if not_ours:
            remedy = "the root is not this uid's to change: make %s owned by this uid, then chmod 700 it" % r
            bell = "the root is not this uid's: make it this uid's, then chmod 700"
        else:
            remedy = "chmod 700 %s" % r
            bell = "chmod 700 the state root"
        point = "the state root is mode %s, not 0700%s" % (
            mode_text, " (a group write bit under the owner's private group)" if cause == "private-group" else "")
        line = ("state root %s is mode %s, not 0700%s%s: every file under it is only as private as its own mode; %s"
                % (r, mode_text, private_clause, fail, remedy))
    elif repair_err:
        # the mode reads right, the chmod that keeps it so could not run: said, since the failed chmod is the signal
        remedy = "the root is not this uid's to change: make %s owned by this uid" % r
        bell = "the root is not this uid's to change: make it this uid's"
        point = "the state root is 0700, but chmod 700 failed (%s)" % errno_name(repair_err)
        line = ("state root %s is mode 0700, but chmod 700 failed (%s): the mode is right today and not this uid's to "
                "keep; %s" % (r, repair_err, remedy))
    else:
        remedy, bell, point, line = "chmod 700 %s" % r, "chmod 700 the state root", None, None
    return {"root": r, "modeRead": mode, "modeReadText": mode_text, "uid": uid, "gid": gid, "verdict": verdict,
            "writableBy": cause if cause in ("other", "group") else None,
            "groupPrivate": (True if cause == "private-group" else False if cause == "group" else None),
            "lookupError": detail if cause == "lookup" else None, "notDirectory": not_dir, "entries": entries,
            "repaired": repaired, "modeAfter": mode_after, "err": err, "repairError": repair_err,
            "statErrno": errno_name(stat_err), "repairErrno": errno_name(repair_err),
            "line": line, "point": point, "remedy": remedy, "remedyPublic": remedy.replace(r, "the state root"),
            "bellRemedy": bell, "t": time.time()}


def import_read_refusal(root, mode, ids, when, repair_error=None, empty=None, **lookups):
    """THE IMPORT-READ RULE (romp-manager's word, 2026-09-20 22:51Z; the creation exemption re-keyed in round 4): the
    mode a process read on a PRE-EXISTING root before its own first chmod (`when` is "import" for the judge module's
    import, "start" for the bus's start gate and the session host's), judged by the discriminator. Writable by another
    local user then, or a lookup that failed, is a refusal WHATEVER THE CHMOD DID AFTERWARDS: the dict {line, point,
    remedy, bellRemedy, remedyPublic, modeRead, modeReadText, cause, detail, when} for the gate to exit with. None when
    the read carried no group or other write bit, when it was a group write bit under the owner's private group (the
    caller's warn-class row says that), when `mode` is None (nothing was read; the current read decides), or when
    `empty` is True: A ROOT THAT WAS EMPTY AT THE READ IS A CREATION DEFAULT, whoever made it (nothing could have been
    planted in an empty directory, and the manager, the CLI and every harness make the root at the umask's mode a
    moment before the first romp process tightens it), so it boots silently. `ids` is (uid, gid) of that read; None
    makes a group bit a lookup failure (romp cannot tell whose group it was). `repair_error` is the chmod's "ENAME:
    strerror" when it failed, else None (the root reads 0700 now, which is what makes the rule necessary: the current
    read cannot see the window). The distrust remedy names the quarantine directory the guarded readers fill."""
    if mode is None or not (mode & WRITE_BITS) or empty:
        return None
    r = os.fspath(root)
    if ids is None:
        writable, cause, detail = None, "lookup", "the owner and group of the read were not recorded"
    else:
        writable, cause, detail = writable_by_another(mode, ids[0], ids[1], **lookups)
    if writable is False:
        return None
    after = (", and the %s's chmod failed (%s)" % (when, repair_error) if repair_error
             else ", re-tightened to 0700 by the %s's chmod" % when)
    mode_text = "%04o" % mode
    if cause == "lookup":
        gid = ids[1] if ids else None
        remedy = bell = _lookup_remedy(gid)
        point = ("the state root read %s at %s (a group write bit) and the group database could not be read (%s)"
                 % (mode_text, when, detail.split(":", 1)[0]))
        line = ("state root %s read %s at %s (a group write bit)%s, and the group database could not be read (%s): romp "
                "cannot tell who else could write here; %s" % (r, mode_text, when, after, detail, remedy))
    else:
        remedy = ("remove serve-token, repo-root and every entry you did not make under %s, or recreate the root, then "
                  "chmod 700 it (what the next boot's readers refuse lands in %s/%s)" % (r, r, QUARANTINE_DIR))
        bell = DISTRUST_REMEDY_BELL
        point = "the state root read %s at %s, writable by other local users (%s)" % (mode_text, when, _how_short(cause))
        line = ("state root %s read %s at %s (writable by other local users: %s)%s and held entries: entries planted "
                "while it was writable are not to be trusted; %s" % (r, mode_text, when, _how(cause, detail), after, remedy))
    return {"line": line, "point": point, "remedy": remedy, "remedyPublic": remedy.replace(r, "the state root"),
            "bellRemedy": bell, "modeRead": mode, "modeReadText": mode_text, "cause": cause, "detail": detail,
            "when": when}


# ── the guard ─────────────────────────────────────────────────────────────────────────────────────────────────────

_ROOT_REAL_MEMO = {}          # root str -> (realpath, the root entry's lstat identity): the resolution, re-done when the entry
#                                at the root's path changes (a symlinked root re-pointed), one lstat instead of realpath's walk


def _real_root(root):
    r = os.fspath(root)
    try:
        st = os.lstat(r)
        ident = (st.st_dev, st.st_ino, st.st_mtime_ns, st.st_mode)
    except OSError:
        ident = None
    hit = _ROOT_REAL_MEMO.get(r)
    if hit is not None and ident is not None and hit[1] == ident:
        return hit[0]
    real = os.path.realpath(r)
    if ident is not None:
        _ROOT_REAL_MEMO[r] = (real, ident)
    return real


def relative_under(root, path):
    """The components of `path` below `root` as a list, or None when `path` is not under the root. Textual first
    (paths under the root are built from the root's own spelling), then against the root's resolved spelling (a path
    built from a resolved root); "." and empty components dropped, a ".." component makes the path outside."""
    r, p = os.fspath(root), os.fspath(path)
    for base in (r, _real_root(r)):
        base_n = os.path.normpath(base)
        p_n = os.path.normpath(p)
        if p_n == base_n:
            return []
        if p_n.startswith(base_n.rstrip("/") + "/"):
            rel = p_n[len(base_n.rstrip("/")) + 1:]
            parts = [c for c in rel.split("/") if c and c != "."]
            if ".." in parts:
                return None
            return parts
    return None


def _judge_entry(st, uid, **lookups):
    """One lstat's verdict for the guard: (None, None) when trusted, else (reason, detail). Reasons: "symlink", "owner",
    "writable" (another local user can write it: an other write bit, or a group write bit under a shared group),
    "lookup" (the group database could not be read)."""
    if stat.S_ISLNK(st.st_mode):
        return "symlink", "a symlink"
    if st.st_uid != uid:
        return "owner", "not this uid's (owner uid %d, this process uid %d)" % (st.st_uid, uid)
    writable, cause, detail = writable_by_another(stat.S_IMODE(st.st_mode), st.st_uid, st.st_gid, **lookups)
    if writable is None:
        return "lookup", "the group database could not be read (%s)" % detail
    if writable:
        return "writable", "writable by another local user (%s)" % _how(cause, detail)
    return None, None


def trusted_path(root, path, **lookups):
    """THE GUARD'S PROPERTY: every component from the state root down to `path`, lstat'ed: not a symlink, owned by this
    process's effective uid, and not writable by another local user by the discriminator (never the directory's mode
    alone: a 0775 venv or a 0664 mirror under the owner's private group passes). Returns a dict: ok (bool), absent
    (bool: the walk met a missing component; ok is True then, the path reads as absent on its own), reason (None |
    "outside" | "root" | "symlink" | "owner" | "writable" | "lookup"), detail (the text for the line),
    component (the absolute path of the first failing component, or None), rel (the components below the root), and
    fault (present only when the lstat of a component under a TRUSTED parent failed with an errno other than ENOENT
    or ENOTDIR, EACCES for one: ok is True, nothing is quarantined, and the reader's primitive raises the fault as the
    site's bare read would; an entry a directory of ours refuses to show us is not a plant, round 4d). The
    root itself is RESOLVED first (a legitimate root reached through a symlink stays legitimate) and judged the same
    way as a component, with reason "root" when it fails (the gates own that case; the readers read absent and
    quarantine nothing, since the root is not an entry). `path` not under the root: ok False with reason "outside",
    which the readers treat as not the root's to guard."""
    uid = os.geteuid()
    rel = relative_under(root, path)
    if rel is None:
        return {"ok": False, "absent": False, "reason": "outside", "detail": "not under the state root", "component": None,
                "rel": None}
    cur = _real_root(root)
    try:
        st = os.lstat(cur)
    except OSError as e:
        return {"ok": False, "absent": False, "reason": "root", "detail": "the state root could not be read (%s)" % errno_text(e),
                "component": cur, "rel": rel}
    if not stat.S_ISDIR(st.st_mode):
        return {"ok": False, "absent": False, "reason": "root", "detail": "the state root path is not a directory (ENOTDIR)",
                "component": cur, "rel": rel}
    reason, detail = _judge_entry(st, uid, **lookups)
    if reason is not None:
        return {"ok": False, "absent": False, "reason": "root", "detail": "the state root is %s" % detail, "component": cur,
                "rel": rel}
    for c in rel:
        cur = os.path.join(cur, c)
        try:
            st = os.lstat(cur)
        except (FileNotFoundError, NotADirectoryError):
            return {"ok": True, "absent": True, "reason": None, "detail": None, "component": None, "rel": rel}
        except OSError as e:
            # A FAULT, NOT A PLANT (round 4d): the lstat of an entry under a directory the walk has just trusted (this
            # uid's, not a symlink, not writable by another local user, so holding nothing another uid put there) failed
            # with EACCES (the directory has no search bit for us: an owner-only 0600 or 000 directory of ours), EPERM or
            # another errno that is not ENOENT or ENOTDIR. Nothing here is untrusted; the entry cannot be judged, and the
            # reader runs the site's primitive, which raises the same fault the site's bare read raised before round 4
            # (the judge's _reg_spawned_at records a sentinel from that PermissionError). Through round 4c this arm was a
            # refusal ("could not be read") whose quarantine EACCES refused too, and the path read ABSENT.
            return {"ok": True, "absent": False, "reason": None, "detail": None, "component": None, "rel": rel,
                    "fault": errno_text(e)}
        reason, detail = _judge_entry(st, uid, **lookups)
        if reason is not None:
            return {"ok": False, "absent": False, "reason": reason, "detail": detail, "component": cur, "rel": rel}
    return {"ok": True, "absent": False, "reason": None, "detail": None, "component": None, "rel": rel}


def _utc_stamp():
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


def quarantine(root, component, rel_parts):
    """Rename the failing entry (`component`, an absolute path under the resolved root; `rel_parts` its components
    below the root) to <root>/quarantine/<utc-stamp>.<relative-path-with-slashes-as-dots>, the quarantine directory
    created 0700 when absent (a quarantine entry that is itself not a trusted directory is moved aside first, so a
    planted `quarantine` cannot receive what the readers decline). Returns (destination, None) or (None, "ENAME: text")
    when the move failed; a second entry of the same name in the same second takes a -n suffix."""
    real = _real_root(root)
    qdir = os.path.join(real, QUARANTINE_DIR)
    uid = os.geteuid()
    try:
        try:
            st = os.lstat(qdir)
        except FileNotFoundError:
            st = None
        if st is not None:
            reason, _detail = _judge_entry(st, uid)
            if reason is not None or not stat.S_ISDIR(st.st_mode):
                os.rename(qdir, os.path.join(real, "%s-untrusted.%s" % (QUARANTINE_DIR, _utc_stamp())))
                st = None
        if st is None:
            os.mkdir(qdir, 0o700)
            os.chmod(qdir, 0o700)                      # the umask does not decide the quarantine's mode
        name = "%s.%s" % (_utc_stamp(), ".".join(rel_parts) or "entry")
        dst, n = os.path.join(qdir, name), 0
        while os.path.lexists(dst):
            n += 1
            dst = os.path.join(qdir, "%s-%d" % (name, n))
        os.rename(component, dst)
        return dst, None
    except OSError as e:
        return None, errno_text(e)


def _absent_error(path):
    return FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), os.fspath(path))


def _is_path(p):
    """True for a pathlib path (the pathlib form of a primitive is used), False for a str or bytes (the os form)."""
    return isinstance(p, pathlib.PurePath)


def _as_path(p):
    """The pathlib.Path for `p` (the sites wrapped a str in Path before their read_text / read_bytes; the same here)."""
    return p if isinstance(p, pathlib.Path) else pathlib.Path(os.fspath(p))


# ── the owner-only creators (part 4) ─────────────────────────────────────────────────────────────────────────────

def make_dir(path, parents=False, root=None):
    """`path` as a directory BORN OWNER-ONLY BY CODE, whatever the process umask, and returned as given. Absent: os.mkdir
    at OWNER_ONLY_DIR (0700; a umask removes bits and never adds one, so the mode holds under 0022, 0002 and 0000
    alike), each missing ancestor made the same way when `parents` (pathlib's parents=True makes them at the umask's
    mode; os.makedirs applies its mode to the leaf alone). Present as a directory of ours at a looser mode: TIGHTENED
    to 0700 (the entry an older process made at the umask's mode, tightened on its next use; PR 814's owner_only_dir is
    this shape for hosts/). Present as a symlink or a non-directory: FileExistsError, never tightened or written through
    (a bare mkdir(exist_ok=True) followed a planted link to its target's directory; the readers refuse a link under the
    root, so a writer refuses it too). Present as another uid's directory: PermissionError (EPERM), the error the chmod
    would have raised, and nothing is adopted. `root`, the state root when the caller holds it (every module does):
    THE ROOT ITSELF IS NEVER TIGHTENED HERE. Its mode is the gate's to read BEFORE it repairs (check, import_read_refusal):
    a writer that tightened it on the way to a write would hide a loosening from the check that exists to report it
    (round 4d's sibling's-repair finding, the same shape). An absent root is made 0700, a creation default (the bus's
    serve() and the serve-token loader make it the same way); its own parents (an XDG directory romp does not own) are
    made as pathlib made them, at the umask's mode, when `parents`. TIGHTENING IS FOR ENTRIES UNDER THE ROOT ALONE: a
    path not under `root`, or a call with no `root`, is made 0700 when absent (still this process's directory) and left
    as it stands when present (the census derives a site's path from the root by data flow, and a helper a caller
    hands a path outside the root at one site and a root path at another would otherwise tighten a directory that is
    not romp's to tighten). One lstat on the common road (the directory exists and is 0700); a mkdir on the first; a
    chmod only on a loose one of ours under the root."""
    p = os.fspath(path)
    rel = relative_under(root, p) if root is not None else None
    try:
        st = os.lstat(p)
    except FileNotFoundError:
        st = None
    if st is None:
        parent = os.path.dirname(p.rstrip("/"))
        if parents and parent and not os.path.isdir(parent):
            if rel is not None and not rel:
                os.makedirs(parent, exist_ok=True)        # the root's own parents: not romp's, the umask's mode as before
            else:
                make_dir(parent, parents=True, root=root)
        try:
            os.mkdir(p, OWNER_ONLY_DIR)
            return path
        except FileExistsError:
            st = os.lstat(p)                             # a sibling made it between the two calls: judged below
    if rel is not None and not rel:
        return path                                      # the root itself: the gate's to read and to repair
    if stat.S_ISLNK(st.st_mode):
        raise FileExistsError(errno.EEXIST, "a symlink stands where a directory of ours is to be made (not followed)", p)
    if not stat.S_ISDIR(st.st_mode):
        raise FileExistsError(errno.EEXIST, os.strerror(errno.EEXIST), p)
    if st.st_uid != os.geteuid():
        raise PermissionError(errno.EPERM, "directory belongs to uid %d, not to this process (uid %d): not tightened, not adopted"
                              % (st.st_uid, os.geteuid()), p)
    if rel and stat.S_IMODE(st.st_mode) & ~OWNER_ONLY_DIR & 0o777:
        os.chmod(p, OWNER_ONLY_DIR)                      # a loose directory of ours under the root: tightened on its next use
    return path


def born_owner_only(path):
    """The file at `path` BORN at OWNER_ONLY_FILE (0600) before its first byte, and an existing one TIGHTENED to it: os.open
    O_WRONLY|O_CREAT at 0600 (a umask never adds a bit), fchmod 0600 on the descriptor (exact under any umask; the repair
    of a file an older process made at the umask's mode), close. Nothing is written and nothing is truncated: the
    creators below run the site's own primitive next (Path.write_text, builtins.open, Path.touch), which the suite's
    fixtures interpose on. O_NONBLOCK|O_NOCTTY: a FIFO or a device planted at the path fails here (ENXIO) instead of
    blocking the open, as the primitive's own open would then do or not do as before. A symlink is followed as the
    primitive follows it (the readers quarantine a planted link under the root at its next read)."""
    fd = os.open(os.fspath(path), os.O_WRONLY | os.O_CREAT | os.O_NONBLOCK | os.O_NOCTTY | os.O_CLOEXEC, OWNER_ONLY_FILE)
    try:
        os.fchmod(fd, OWNER_ONLY_FILE)
    finally:
        os.close(fd)


def _born(path):
    """born_owner_only(path), answering whether this call CREATED the file (absent before it). The creators below unlink a
    file they created when the site's primitive then raises (a faulting Path.write_text in a test, ENOSPC, a read-only
    mount), so a failed first write leaves nothing where the bare primitive left nothing (an aside that could not be
    written is not on disk empty; an atomic publisher's temp that failed is gone); a file that existed is left as the
    primitive left it."""
    existed = os.path.lexists(path)
    born_owner_only(path)
    return not existed


def _unlink_created(path):
    try:
        os.unlink(path)
    except OSError:
        pass


def write_text(path, text, encoding=None, errors=None, newline=None):
    """Path.write_text of a file born owner-only (born_owner_only first); returns the count written."""
    created = _born(path)
    try:
        return _as_path(path).write_text(text, encoding=encoding, errors=errors, newline=newline)
    except BaseException:
        if created:
            _unlink_created(path)
        raise


def write_bytes(path, data):
    """Path.write_bytes of a file born owner-only; returns the count written."""
    created = _born(path)
    try:
        return _as_path(path).write_bytes(data)
    except BaseException:
        if created:
            _unlink_created(path)
        raise


def open_private(path, mode="a", buffering=-1, encoding=None, errors=None, newline=None):
    """builtins.open of a file born owner-only, in a WRITE or APPEND mode ("a", "ab", "w", "wb", "w+b", ...; a read mode is
    a ValueError, Reader.open is the guarded read). The append logs under the root (messages.jsonl, cleared.jsonl,
    judge-errors.jsonl, host.log, the states and ledgers) take this road: the file is 0600 from its first line, and an
    older one at the umask's mode is tightened on the next append."""
    if not any(c in mode for c in "wax+"):
        raise ValueError("open_private writes only; mode %r reads (Reader.open is the guarded read)" % mode)
    if "x" in mode:
        # an EXCLUSIVE create: born_owner_only would make the file first and the primitive's O_EXCL then refuse it, so the
        # descriptor is opened O_CREAT|O_EXCL at 0600 here and handed to the primitive's file object (the site's mode with
        # the x read as w, the shape os.fdopen takes); no site takes this road today, and a new one is owner-only too
        fd = os.open(os.fspath(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | (os.O_APPEND if "a" in mode else 0), OWNER_ONLY_FILE)
        try:
            return os.fdopen(fd, mode.replace("x", "w"), buffering=buffering, encoding=encoding, errors=errors, newline=newline)
        except BaseException:
            os.close(fd)
            raise
    created = _born(path)
    try:
        return open(path, mode, buffering=buffering, encoding=encoding, errors=errors, newline=newline)
    except BaseException:
        if created:
            _unlink_created(path)
        raise


def touch(path):
    """Path.touch of a file born owner-only (an absent one is made 0600; an existing one is tightened and its mtime set)."""
    created = _born(path)
    try:
        _as_path(path).touch()
    except BaseException:
        if created:
            _unlink_created(path)
        raise


class Reader:
    """The guarded readers over one state root (the module docstring's part 3). `root_fn` answers the root at call time
    (the judge rebinds its STATE in tests). `on_refused(path, reason, line)` is the caller's row hook (the kernel files
    an error-centre row of the refused kind; the bus and the session host log); it runs after the stderr line and never
    raises out. A reader built with NO hook of its own files through the module's REFUSED_HOOKS instead (the kernel-side
    helper modules, handed the root per call, build such readers; the kernel registers its row hook there). `who`
    labels the stderr line ("kernel", "postal", "session-host", "judge", "logins", ...).

    THE PRIMITIVE RULE (the module docstring): after the guard each reader performs the read through the same pathlib or
    os primitive the site used before round 4, by the argument's kind (a Path: Path.read_text, Path.read_bytes,
    Path.stat, Path.exists, Path.is_dir, Path.iterdir, Path.glob; a str: os.stat, os.path.exists, os.path.isdir,
    os.listdir, glob.glob; open is builtins.open, os_open is os.open, gzip_open is gzip.open; listdir and scandir are
    os.listdir and os.scandir), resolved at call time, so a test that interposes on one of those names to count or
    fault a read meets the read. No descriptor open of the Reader's own: the residual between the walk and the
    primitive's open is a same-uid race on a root the gate has judged not writable by another local user (0700 in the
    ordinary case; a looser mode writable by nobody but its owner, 0755 for one, when the chmod was refused and the boot
    warned) and whose directories the walk has just judged the same way, which no O_NOFOLLOW on a final open by path
    closes for a process against itself."""

    def __init__(self, root_fn, on_refused=None, who="romp"):
        self.root_fn = root_fn
        self.on_refused = on_refused
        self.who = who
        self.refused = []           # (path, reason, destination or None), the refusals this process made, for tests and /version

    # ── the guard and the quarantine ──
    def trust(self, path, **lookups):
        """trusted_path over this reader's root; a refusal QUARANTINES the failing component, says the line, files the row
        and returns the dict with ok False. An "outside" path returns ok False, reason "outside", with nothing done."""
        root = self.root_fn()
        t = trusted_path(root, path, **lookups)
        if t["ok"] or t["reason"] == "outside":
            return t
        line = None
        if t["reason"] == "root":
            # THE ROOT'S OWN FAILURE IS THE GATE'S CASE (unknown, ENOTDIR or refuse exits the process; a root another uid
            # owns is the gate's warn row with its remedy): the readers read absent, quarantine nothing, file NO row, and
            # say it once per process per root and cause, not once per read (a backend over a root that is gone would
            # otherwise say it on every read; the round-4 review's test-order finding)
            t["quarantined"] = None
            key = (os.fspath(root), t["detail"])
            with _PRIVATE_MEMO_LOCK:
                said = key in _ROOT_FAILURE_SAID
                _ROOT_FAILURE_SAID.add(key)
            if not said:
                try:
                    sys.stderr.write("romp-%s: state root entries under %s are read as absent: %s (the gate's check decides the "
                                     "root itself; nothing under it is adopted; said once)\n" % (self.who, os.fspath(root), t["detail"]))
                except Exception:
                    pass
                self.refused.append((os.fspath(root), "root", None))
            return t
        else:
            comp = t["component"]
            rel_parts = relative_under(root, comp) or t["rel"]
            dst, qerr = quarantine(root, comp, rel_parts)
            t["quarantined"] = dst
            if dst is not None:
                line = ("state root entry %s is %s: quarantined to %s and read as absent; nothing planted is adopted (remove "
                        "it from %s/%s after review)" % (comp, t["detail"], dst, os.fspath(root), QUARANTINE_DIR))
            else:
                line = ("state root entry %s is %s: could not be quarantined (%s); read as absent, and nothing planted is "
                        "adopted (remove it by hand)" % (comp, t["detail"], qerr))
        try:
            sys.stderr.write("romp-%s: %s\n" % (self.who, line))
        except Exception:
            pass
        entry = os.fspath(t["component"] if t["reason"] != "root" and t["component"] else path)   # the entry judged, not the path asked for
        self.refused.append((entry, t["reason"], t.get("quarantined")))
        for hook in ([self.on_refused] if self.on_refused is not None else list(REFUSED_HOOKS)):
            try:
                hook(entry, t["reason"], line)
            except Exception:
                pass
        return t

    def _ok(self, path):
        """True when the path may be read (trusted, or outside the root: not the root's to guard, so the plain primitive
        runs); False when it was refused (and quarantined)."""
        t = self.trust(path)
        return t["ok"] or t["reason"] == "outside"

    # ── the readers: each behaves as if the path were absent once refused, and each reads through the site's own primitive ──
    def os_open(self, path, flags=os.O_RDONLY):
        """os.open of a trusted path with the flags as given (O_RDONLY by default: the judge's descriptor-keyed store reads);
        FileNotFoundError when absent or refused."""
        if not self._ok(path):
            raise _absent_error(path)
        return os.open(os.fspath(path), flags)

    def open(self, path, mode="r", buffering=-1, encoding=None, errors=None, newline=None):
        """builtins.open of a trusted path in a read mode ("r" or "rb", the shape the sites use), resolved at call time;
        FileNotFoundError when absent or refused."""
        if any(c in mode for c in "wax+"):
            raise ValueError("Reader.open reads only; mode %r writes" % mode)
        if not self._ok(path):
            raise _absent_error(path)
        return open(path, mode, buffering=buffering, encoding=encoding, errors=errors, newline=newline)

    def read_text(self, path, encoding=None, errors=None):
        """Path.read_text of a trusted path (a str is wrapped in a Path, as the sites did); FileNotFoundError when absent or
        refused."""
        if not self._ok(path):
            raise _absent_error(path)
        return _as_path(path).read_text(encoding=encoding, errors=errors)

    def read_bytes(self, path):
        """Path.read_bytes of a trusted path; FileNotFoundError when absent or refused."""
        if not self._ok(path):
            raise _absent_error(path)
        return _as_path(path).read_bytes()

    def gzip_open(self, path, mode="rb"):
        """gzip.open of a trusted path in a read mode; FileNotFoundError when absent or refused."""
        if any(c in mode for c in "wax+"):
            raise ValueError("Reader.gzip_open reads only; mode %r writes" % mode)
        if not self._ok(path):
            raise _absent_error(path)
        return _gzip.open(path, mode)

    def stat(self, path):
        """Path.stat (a Path) or os.stat (a str) of a trusted path (the stat-then-read shape: the guard ran here, so the
        read that follows through this reader walks a path already judged once); FileNotFoundError when absent or
        refused."""
        if not self._ok(path):
            raise _absent_error(path)
        return path.stat() if _is_path(path) else os.stat(path)

    def exists(self, path):
        """Path.exists (a Path) or os.path.exists (a str) of a trusted path; False when refused."""
        if not self._ok(path):
            return False
        return path.exists() if _is_path(path) else os.path.exists(path)

    def isdir(self, path):
        """A trusted directory at the path, by Path.is_dir (a Path) or os.path.isdir (a str); a symlinked directory under
        the root is refused and quarantined by the guard, never followed. False when refused. A fault under a trusted
        parent (EACCES from a directory of ours with no search bit) is the primitive's to answer, as at the site before
        round 4: Path.is_dir raises it on 3.12 and answers False on 3.14, os.path.isdir answers False (round 4d; through
        round 4c an OSError arm here answered False on every interpreter)."""
        if not self._ok(path):
            return False
        return path.is_dir() if _is_path(path) else os.path.isdir(path)

    is_dir = isdir

    def dir(self, path):
        """The path itself when it is a trusted real directory, else None (for a caller that caches one directory, the
        checkpoints directory at _ckpt_dir())."""
        return path if self.isdir(path) else None

    def listdir(self, path):
        """The names under a trusted directory (os.listdir); [] when absent or refused. Each name is then judged by the
        reader that opens it: a planted entry inside a trusted directory is quarantined by that read."""
        if not self._ok(path):
            return []
        try:
            return os.listdir(os.fspath(path))
        except FileNotFoundError:
            return []

    def scandir(self, path):
        """os.scandir over a trusted directory (a context manager and an iterator, as os.scandir is); an empty one when
        absent or refused."""
        if not self._ok(path):
            return _EmptyScandir()
        try:
            return os.scandir(os.fspath(path))
        except FileNotFoundError:
            return _EmptyScandir()

    def iterdir(self, path):
        """The entries under a trusted directory, by Path.iterdir (a Path) or os.listdir joined to the directory (a str),
        sorted, as a list; [] when absent or refused. Each entry is judged: a refused entry is quarantined and left out."""
        if not self._ok(path):
            return []
        try:
            if _is_path(path):
                children = list(path.iterdir())
            else:
                base = os.fspath(path)
                children = [os.path.join(base, name) for name in os.listdir(base)]
        except FileNotFoundError:
            return []
        return [child for child in sorted(children) if self._ok(child)]

    def glob(self, path, pattern):
        """The matches of `pattern` under a trusted directory, by Path.glob (a Path) or glob.glob (a str, the directory
        escaped), sorted, as a list; [] when absent or refused. Each match is judged (its components below `path`
        included): a refused match is quarantined and left out. Symlinked matches are refused by the guard, never
        followed."""
        if not self._ok(path):
            return []
        if _is_path(path):
            matches = sorted(path.glob(pattern))
        else:
            matches = sorted(_glob.glob(os.path.join(_glob.escape(os.fspath(path)), pattern)))
        return [m for m in matches if self._ok(m)]

    def sys_path_dir(self, path, position=None):
        """Add a trusted directory to sys.path (at `position`, or appended); False when absent, refused or not a
        directory. A planted site-packages is quarantined here and never imported from."""
        if not self.isdir(path):
            return False
        p = os.fspath(path)
        if p not in sys.path:
            if position is None:
                sys.path.append(p)
            else:
                sys.path.insert(position, p)
        return True


class _EmptyScandir:
    """What Reader.scandir answers for an absent or refused directory: iterable, empty, a context manager."""
    def __iter__(self):
        return iter(())

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def close(self):
        pass


def _main(argv):
    if len(argv) >= 3 and argv[0] == "trusted":
        root, path = argv[1], argv[2]
        r = Reader(lambda: root, who="sdk-setup")
        t = r.trust(path)
        return 0 if (t["ok"] or t["reason"] == "outside") else 1
    sys.stderr.write("usage: state_root_mode.py trusted <root> <path>\n")
    return 2


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
