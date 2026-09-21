#!/usr/bin/env python3
"""THE WRITERS CENSUS: every call that CREATES an entry under the state root, derived from the code, pinned to the
owner-only creators (kernel/state_root_mode.py, part 4).

Round 4d of the state-root review (2026-09-21) found that the kernel, the bus and the session host made their entries
under the root at the process umask: under a umask that leaves an other write bit, or a group write bit under a shared
primary group, the guarded readers (tests/test_state_root_readers.py) quarantine the process's OWN fresh entries at the
next read. romp-manager's ruling: "Entries born owner-only BY CODE. Derive every writer that creates an entry under the
root (a bare mkdir, a write_text, an open for write, a tempfile, anything) and make each set its mode explicitly, rather
than fixing the four you noticed." This module is that derivation and that pin; tests/test_state_root_mode.py's
EntriesAreBornOwnerOnlyUnderAPermissiveUmask is the behavioural pin (the creation roads under umask 0022 and 0000 in
child processes).

WHAT IT DOES. The same AST census as the readers': the eleven modules (test_state_root_readers.MODULES), the same seeds,
the same derivation of every expression that is a path under the root (module_facts, reused from the readers module's
per-process cache, so the derivation of kernel/kernel.py's 79k lines runs once for both censuses in one process). Over
those expressions it lists every CREATION: Path.mkdir, os.mkdir, os.makedirs; Path.write_text, Path.write_bytes,
Path.touch; open, Path.open, io.open and gzip.open in a write or append mode (a mode the census cannot read is listed
as "open:?"); os.open with O_CREAT; tempfile.* with its directory under the root; shutil.copy, copy2, copyfile, copytree
and move onto a path under the root; os.rename, os.replace, os.link, os.symlink, Path.rename, Path.replace,
Path.hardlink_to and Path.symlink_to whose DESTINATION is under the root. A json.dump onto a file object is not a
creation of its own: the open that made the object is the one listed.

WHAT IT ASSERTS. Every creation is born owner-only BY CODE, in one of four ways, or sits on ALLOWLIST with a one-line
reason. (1) THE CREATORS: a call of the shared module's make_dir, write_text, write_bytes, open_private or touch (the
receiver is the module: `srm`, `_srm`, `jd.srm`), each of which makes the entry 0700 or 0600 before its first byte
under any umask and tightens an existing one of ours. (2) THE INODE: a rename, replace or hard link whose SOURCE is
itself a path under the root carries its source's mode (the mode travels with the inode; the source's own creation is
censused where it happens), so an atomic publish through a temp born by a creator is owner-only. (3) THE LIBRARY:
tempfile.mkstemp and NamedTemporaryFile make their file 0600, mkdtemp and TemporaryDirectory their directory 0700,
whatever the umask. (4) THE ALLOWLIST: a site that sets its mode by code AT THAT SITE (an os.open with O_CREAT and a
0600 mode, a mkdir with mode=0o700 followed by its own tightening), each with its reason; a stale entry reds. A new bare
creator anywhere in the eleven modules reds this module (test_the_census_reds_on_a_planted_bare_creator proves the pin
can red by planting six shapes in a copy of the kernel and shows their owner-only twins come out clean). A copy onto the
root (shutil.copy*) and a symlink under the root are never owner-only by construction (a copy carries the umask's or the
source's mode; a symlink is what the readers quarantine) and are listed unguarded until allowlisted.

HOW TO RE-RUN IT BY HAND. `python3 tests/test_state_root_writers.py --list` prints the population (file:line, function,
kind, target, how it is owner-only) and exits 1 when an unaccounted creator exists. plans/state-root-mode.md records
the method beside the readers'.

WHAT IT DOES NOT SEE. What the readers census does not see (a path through a name the derivation cannot follow), and a
creator called with a path outside the root (not the root's). A creation by a process that is not one of the eleven
modules (bin/romp-manager's mkdirSync of the root, the CLI's mkdir -p) is a creation default the gates exempt.
"""
import ast
import collections
import os
import sys
import unittest
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
if __package__:
    from . import test_state_root_readers as R   # under pytest tests/ is a package: THE SAME module object as the readers' run,
else:                                             # so its _PARSED and _FACTS caches are this census's too (one derivation per process)
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    import test_state_root_readers as R           # `python3 tests/test_state_root_writers.py --list`: a script, the module by name

ROOT = R.ROOT
MODULES = R.MODULES

CREATORS = {"make_dir": "dir", "write_text": "file", "write_bytes": "file", "open_private": "file", "touch": "file"}
RENAME_FUNCS = {"os.rename", "os.replace", "os.link", "shutil.move"}     # (source, destination): owner-only when the source is
COPY_FUNCS = {"shutil.copy", "shutil.copy2", "shutil.copyfile", "shutil.copytree"}   # a new inode at the umask's or the source's mode
TEMPFILE_FUNCS = {"tempfile.mkstemp", "tempfile.mkdtemp", "tempfile.NamedTemporaryFile", "tempfile.TemporaryDirectory",
                  "tempfile.TemporaryFile", "tempfile.SpooledTemporaryFile"}   # each born 0600 or 0700 by the library
CREATE_FLAG = "O_CREAT"

# THE ALLOWLIST: (file, function, kind, target text) -> the one-line reason the site is owner-only without a creator: its
# mode is set by code at that site. Every entry must match a creation the census finds (test_the_allowlist_carries_no_stale_entry).
ALLOWLIST = {
    # the serve-token loader, the one copy the repo keeps on purpose (kernel/kernel.py and postal/postal_service.py held
    # equal by tests/test_kernel_serve_token_mode.py's ServeTokenLoadersMatch): the mint's temp is created O_EXCL at 0600
    # and the lock O_CREAT at 0600; the root it makes on a box with none is mkdir(mode=0o700), a creation default the gate
    # then reads (the root itself is never tightened by a writer)
    ("kernel/kernel.py", "_serve_token_read_or_mint.mint", "os.open", "str(tmp)"):
        "the serve-token mint's temp, created O_WRONLY|O_CREAT|O_EXCL at 0600 (never wider under any umask), then published by os.replace",
    ("kernel/kernel.py", "_serve_token_read_or_mint", "mkdir", "f.parent"):
        "the state root itself, made mkdir(mode=0o700) when a box has none (a creation default; the gate reads it next and a writer never tightens the root)",
    ("kernel/kernel.py", "_serve_token_read_or_mint", "os.open", "str(lock)"):
        "serve-token.lock, opened O_RDWR|O_CREAT|O_NOFOLLOW at 0600 by the loader's own guards (round 3's correctness-2)",
    ("postal/postal_service.py", "_serve_token_read_or_mint.mint", "os.open", "str(tmp)"):
        "the bus's copy of the mint's temp, created O_EXCL at 0600 (held equal to the kernel's by ServeTokenLoadersMatch)",
    ("postal/postal_service.py", "_serve_token_read_or_mint", "mkdir", "f.parent"):
        "the bus's copy of the root's mkdir(mode=0o700) on a box with none (a creation default the gate reads next)",
    ("postal/postal_service.py", "_serve_token_read_or_mint", "os.open", "str(lock)"):
        "the bus's copy of the lock's O_RDWR|O_CREAT|O_NOFOLLOW open at 0600",
    ("kernel/kernel.py", "_persist_repo_root", "os.open", "str(tmp)"):
        "repo-root's temp, created O_WRONLY|O_CREAT|O_EXCL at 0600 and published by os.replace (the token mint's shape, round 2's fresh-1)",
    ("kernel/kernel.py", "_atomic_write", "os.open", "str(tmp)"):
        "the atomic publisher's mode road: O_WRONLY|O_CREAT|O_TRUNC at the caller's mode with an fchmod on the descriptor before "
        "the first write (PR 789; tests/test_kernel_remotes_perms.py pins the shape); the mode-less road takes the creator write_text",
    ("kernel/kernel.py", "_minted_host_id", "os.open", "str(_HOST_ID_FILE)"):
        "host-id, created O_WRONLY|O_CREAT|O_EXCL at 0600 (0644 until round 4f: nothing but this uid reads under a 0700 root)",
    ("postal/postal_service.py", "_minted_host_id", "os.open", "str(_HOST_ID_FILE)"):
        "the bus's copy of the host-id mint, O_EXCL at 0600 (0644 until round 4f)",
    ("postal/postal_service.py", "serve", "mkdir", "STATE.parent"):
        "the state root itself, made mkdir(mode=0o700) by the bus's serve() when the import gate found none (a creation default, "
        "then read by the start gate; a writer never tightens the root)",
    ("postal/postal_service.py", "serve", "os.open", "str(_pid_tmp)"):
        "server.pid's temp, created O_WRONLY|O_CREAT|O_EXCL at 0600 after the guard and published by os.replace (round 4)",
    ("kernel/judge.py", "<module>", "mkdir", "STATE"):
        "the judge module's own mkdir of the state root at import, mode=0o700 and without exist_ok so a creation is recorded "
        "(_STATE_ROOT_CREATED_AT_IMPORT) and a pre-existing root's EEXIST is the import-read rule's input; the chmod that follows "
        "is the import's repair, read before it runs",
    ("kernel/judge.py", "_rebind_state", "mkdir", "Path(STATE)"):
        "the test seam's root (make=True), made mode=0o700 and floored by the chmod two lines below; never a production road",
    ("kernel/judge.py", "_ensure_judge_scratch", "os.makedirs", "d"):
        "the judge scratch cwd: os.makedirs(mode=0o700) and then its own lstat, owner and tightening checks, a refusal for a symlink "
        "or another uid's directory (tests/test_judge_scratch_private.py, OwnerOnlyParity with the host's owner_only_dir)",
    ("kernel/session_host.py", "owner_only_dir", "mkdir", "d"):
        "PR 814's helper for hosts/ and hosts/<sid>/: mkdir(mode=0o700) and then its own lstat, owner and tightening checks, a "
        "refusal for a symlink or another uid's directory (tests/test_session_host.py; its census tests/test_hosts_path_census.py)",
    ("kernel/session_host.py", "SessionHost._serve_socket", "os.rename", "self.sock_path"):
        "the host's socket publish: the bound temp is chmod'ed 0600 at the site two lines above the rename (PR 814's socket mode), "
        "and the rename carries the inode's mode onto the published name",
    ("kernel/codex_runtime.py", "install_runtime", "Path.rename", "target"):
        "the Codex runtime's staging directory, pip's under a 0700 mkdtemp, is tightened to 0700 by make_dir at the site right before "
        "the rename publishes it (the mode travels with the inode; the tree inside keeps pip's modes, a residual named in the notes)",
    ("kernel/logins.py", "write_record", "os.open", "str(tmp)"):
        "a login record's temp, created O_WRONLY|O_CREAT|O_EXCL at 0600 in a logins/ directory chmod'ed 0700 at the site, then "
        "chmod'ed 0600 again after the rename (kernel/logins.py write_record)",
    ("kernel/sdk_backend.py", "ApiHealth.salt", "os.open", "str(tmp)"):
        "the API-health salt's temp, created O_WRONLY|O_CREAT|O_EXCL at 0600 and hard-linked into place (the inode keeps it)",
    ("kernel/sdk_backend.py", "write_reg", "os.open", "str(tmp)"):
        "a session reg's temp, O_WRONLY|O_CREAT|O_TRUNC at 0600 with the fchmod on the descriptor (PR 789's shape), published by os.replace",
    ("kernel/sdk_backend.py", "write_lease", "os.open", "str(tmp)"):
        "a lease's temp, O_WRONLY|O_CREAT|O_TRUNC at 0600 with the fchmod on the descriptor (round 4d), published by os.replace",
    ("kernel/sdk_backend.py", "flag_settings_path", "os.open", "p"):
        "the per-session settings file, O_WRONLY|O_CREAT|O_TRUNC at 0600 with the fchmod on the descriptor (it carries the environment overlay)",
    ("kernel/codex_backend.py", "CodexBackend._write_registry_locked", "os.open", "str(tmp)"):
        "the Codex registry's temp, created O_WRONLY|O_CREAT|O_EXCL at 0600 and published by os.replace",
    ("kernel/codex_backend.py", "CodexBackend._save_registry", "os.open", "str(self._reg_lock_path())"):
        "the Codex registry's lock, O_RDWR|O_CREAT at 0600 with an fchmod on the descriptor",
}


def _mode_arg(call, idx):
    """The mode of an open-like call: the constant string at positional `idx` or the `mode` keyword; None when absent
    (the primitive's default, a read); "?" when present and not a constant (the census cannot read it)."""
    for i, a in enumerate(call.args):
        if i == idx:
            return a.value if isinstance(a, ast.Constant) and isinstance(a.value, str) else "?"
    for kw in call.keywords:
        if kw.arg == "mode":
            return kw.value.value if isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str) else "?"
    return None


def _writes(mode):
    return mode == "?" or any(c in mode for c in "wax+")


def _is_creator_module(recv):
    """The receiver of a creator call is the shared module: a name or attribute whose text ends in `srm` (`srm`, `_srm`, `jd.srm`)."""
    return R.unparse(recv).split(".")[-1].endswith("srm")


def _flags_create(call):
    """Whether an os.open call's flags carry O_CREAT (the second positional, or the `flags` keyword)."""
    for i, a in enumerate(call.args):
        if i == 1:
            return CREATE_FLAG in R.unparse(a)
    for kw in call.keywords:
        if kw.arg == "flags":
            return CREATE_FLAG in R.unparse(kw.value)
    return False


def _entry(mf, rel, n, fn, kind, target, how, source=None):
    return {"file": rel, "func": R._qual(mf, fn), "line": n.lineno, "col": n.col_offset, "end_line": n.end_lineno,
            "end_col": n.end_col_offset, "kind": kind, "target": R._txt(mf, target) if target is not None else "",
            "source": R._txt(mf, source) if source is not None else "", "guarded": how is not None, "how": how or "UNGUARDED"}


def _classify(mf, n, fn):
    """(kind, target, how, source) for a call that creates an entry under the root, or None. `how` is "creator", "inode"
    or "library" when the site is owner-only by code, None when it is bare."""
    f = n.func
    ftxt = R._txt(mf, f)
    args = n.args
    if isinstance(f, ast.Attribute):
        recv = f.value
        # (1) THE CREATORS: the shared module's make_dir, write_text, write_bytes, open_private, touch on a root path
        if f.attr in CREATORS and args and _is_creator_module(recv) and R._is_root(mf, args[0], fn):
            return f.attr, args[0], "creator", None
        if f.attr in ("mkdir",) and R._is_root(mf, recv, fn):
            return "mkdir", recv, None, None
        if f.attr in ("write_text", "write_bytes", "touch") and R._is_root(mf, recv, fn):
            return f.attr, recv, None, None
        if f.attr == "open" and R._is_root(mf, recv, fn):
            mode = _mode_arg(n, 0)
            if mode is not None and _writes(mode):
                return "open:" + mode, recv, None, None
            return None
        if f.attr in ("rename", "replace") and len(args) == 1 and not n.keywords and R._is_root(mf, args[0], fn):
            return "Path." + f.attr, args[0], ("inode" if R._is_root(mf, recv, fn) else None), recv   # str.replace takes two
        if f.attr == "hardlink_to" and R._is_root(mf, recv, fn):
            return "Path.hardlink_to", recv, ("inode" if args and R._is_root(mf, args[0], fn) else None), (args[0] if args else None)
        if f.attr == "symlink_to" and R._is_root(mf, recv, fn):
            return "Path.symlink_to", recv, None, None
        if ftxt in ("os.mkdir", "os.makedirs") and args and R._is_root(mf, args[0], fn):
            return ftxt, args[0], None, None
        if ftxt == "os.open" and args and R._is_root(mf, args[0], fn) and _flags_create(n):
            return "os.open", args[0], None, None
        if ftxt == "os.symlink" and len(args) >= 2 and R._is_root(mf, args[1], fn):
            return ftxt, args[1], None, None
        if ftxt in RENAME_FUNCS and len(args) >= 2 and R._is_root(mf, args[1], fn):
            return ftxt, args[1], ("inode" if R._is_root(mf, args[0], fn) else None), args[0]
        if ftxt in COPY_FUNCS and len(args) >= 2 and R._is_root(mf, args[1], fn):
            return ftxt, args[1], None, args[0]
        if ftxt in ("io.open", "gzip.open") and args and R._is_root(mf, args[0], fn):
            mode = _mode_arg(n, 1)
            if mode is not None and _writes(mode):
                return ftxt + ":" + mode, args[0], None, None
            return None
        if ftxt in TEMPFILE_FUNCS:
            for kw in n.keywords:
                if kw.arg == "dir" and R._is_root(mf, kw.value, fn):
                    return ftxt, kw.value, "library", None
            for a in args:
                if R._is_root(mf, a, fn):
                    return ftxt, a, "library", None
            return None
        return None
    if isinstance(f, ast.Name) and f.id == "open" and args and R._is_root(mf, args[0], fn):
        mode = _mode_arg(n, 1)
        if mode is not None and _writes(mode):
            return "open:" + mode, args[0], None, None
    return None


def census(root, rels, sources=None):
    """Every creation of an entry under the state root in `rels` (files under `root`, or the texts `sources` maps them to):
    dicts with file, func, line, kind, target, source, guarded and how."""
    entries = []
    for rel in rels:
        src = (sources or {}).get(rel)
        mf = R.module_facts(root, rel, src)
        for n in mf.all_calls:
            fn = mf.enclosing.get(id(n))
            hit = _classify(mf, n, fn)
            if hit is None:
                continue
            kind, target, how, source = hit
            entries.append(_entry(mf, rel, n, fn, kind, target, how, source))
    return entries


def _key(e):
    return (e["file"], e["func"], e["kind"], e["target"])


def unaccounted(entries):
    """The creations that are neither owner-only by code nor allowlisted."""
    return [e for e in entries if not e["guarded"] and _key(e) not in ALLOWLIST]


def render(entries):
    lines = []
    for e in entries:
        how = e["how"] if e["guarded"] else ("allowlisted" if _key(e) in ALLOWLIST else "UNGUARDED")
        src = (" <- " + e["source"]) if e["source"] else ""
        lines.append("%s:%d %s [%s] %s%s: %s" % (e["file"], e["line"], e["func"], e["kind"], e["target"], src, how))
    return lines


def counts(entries):
    """Per-module counts: {file: (total, owner-only by code, allowlisted, unguarded)}."""
    out = {}
    for rel in MODULES:
        mine = [e for e in entries if e["file"] == rel]
        bad = unaccounted(mine)
        guarded = sum(e["guarded"] for e in mine)
        out[rel] = (len(mine), guarded, len(mine) - guarded - len(bad), len(bad))
    return out


class TheWritersCensus(unittest.TestCase):
    """The population of creations under the state root, derived by code and pinned to the owner-only creators."""

    # THE PLANT: one copy of kernel/logins.py (a handed-root module: its `state_dir` parameters are the root, and its shared
    # module is `_srm`) with six bare creators and their owner-only twins, derived once per class. A small module on
    # purpose: the derivation of a planted copy is not cached, and a copy of kernel/kernel.py costs five seconds where
    # this one costs a fraction of one (the CI budget the round-4e speed pass set).
    PLANT_MODULE = "kernel/logins.py"
    PLANT = ('\n\ndef _planted_mkdir(state_dir):\n    (Path(state_dir) / "planted").mkdir(parents=True, exist_ok=True)\n\n\n'
             'def _planted_write(state_dir):\n    (Path(state_dir) / "planted.json").write_text("x")\n\n\n'
             'def _planted_append(state_dir):\n    with open(Path(state_dir) / "planted.jsonl", "a") as f:\n        f.write("x")\n\n\n'
             'def _planted_os_open(state_dir):\n    fd = os.open(str(Path(state_dir) / "planted.bin"), os.O_WRONLY | os.O_CREAT)\n    os.close(fd)\n\n\n'
             'def _planted_move(state_dir, src):\n    shutil.move(src, Path(state_dir) / "planted-moved")\n\n\n'
             'def _planted_rename_in(state_dir, src):\n    os.replace(src, Path(state_dir) / "planted-renamed")\n\n\n'
             'def _planted_mkdir_ok(state_dir):\n    _srm.make_dir(Path(state_dir) / "planted", parents=True, root=state_dir)\n\n\n'
             'def _planted_write_ok(state_dir):\n    _srm.write_text(Path(state_dir) / "planted.json", "x")\n\n\n'
             'def _planted_append_ok(state_dir):\n    with _srm.open_private(Path(state_dir) / "planted.jsonl", "a") as f:\n        f.write("x")\n\n\n'
             'def _planted_publish_ok(state_dir):\n    tmp = Path(state_dir) / "planted.tmp"\n    _srm.write_text(tmp, "x")\n'
             '    os.replace(tmp, Path(state_dir) / "planted")\n\n\n'
             'def _planted_temp_ok(state_dir):\n    return tempfile.mkstemp(dir=str(state_dir))\n\n\n'
             'def _planted_touch_ok(state_dir):\n    _srm.touch(Path(state_dir) / "planted-marker")\n')
    PLANTED_BARE = [("_planted_append", "open:a"), ("_planted_mkdir", "mkdir"), ("_planted_move", "shutil.move"),
                    ("_planted_os_open", "os.open"), ("_planted_rename_in", "os.replace"), ("_planted_write", "write_text")]
    PLANTED_OK = [("_planted_append_ok", "open_private", "creator"), ("_planted_mkdir_ok", "make_dir", "creator"),
                  ("_planted_publish_ok", "os.replace", "inode"), ("_planted_publish_ok", "write_text", "creator"),
                  ("_planted_temp_ok", "tempfile.mkstemp", "library"), ("_planted_touch_ok", "touch", "creator"),
                  ("_planted_write_ok", "write_text", "creator")]
    _planted = None

    @classmethod
    def setUpClass(cls):
        cls.entries = census(Path(ROOT), MODULES)

    @classmethod
    def planted_module(cls):
        if cls._planted is None:
            src, _tree = R.source_and_tree(os.path.join(ROOT, cls.PLANT_MODULE), cls.PLANT_MODULE)
            cls._planted = census(Path(ROOT), [cls.PLANT_MODULE], sources={cls.PLANT_MODULE: src + cls.PLANT})
        return cls._planted

    def test_every_creation_under_the_root_is_owner_only_by_code_or_allowlisted(self):
        """THE PIN. Every creation the census finds in the eleven modules is through a creator, a rename of an entry born
        under the root, a tempfile, or on ALLOWLIST with its reason. A new bare creator anywhere in them fails here,
        naming its file, line, function, kind and target."""
        bad = unaccounted(self.entries)
        self.assertEqual(bad, [], "creators under the state root that are not owner-only by code:\n" + "\n".join(render(bad)))
        guarded = [e for e in self.entries if e["guarded"]]
        self.assertGreater(len(guarded), 150, "the census sees the population (%d owner-only creations)" % len(guarded))
        by_file = collections.Counter(e["file"] for e in guarded)
        for rel in ("kernel/kernel.py", "kernel/judge.py", "kernel/event_model.py", "postal/postal_service.py",
                    "kernel/session_host.py", "kernel/sdk_backend.py", "kernel/codex_backend.py"):
            self.assertGreater(by_file[rel], 0, "%s has owner-only creations (%r)" % (rel, dict(by_file)))
        kinds = collections.Counter(e["kind"] for e in guarded)
        for kind in ("make_dir", "write_text", "open_private", "touch", "os.replace"):
            self.assertGreater(kinds[kind], 0, "the creators are in use (%r)" % dict(kinds))

    def test_the_allowlist_carries_no_stale_entry_and_every_entry_has_a_reason(self):
        found = {_key(e) for e in self.entries if not e["guarded"]}
        for key, reason in ALLOWLIST.items():
            self.assertIn(key, found, "a stale allowlist entry: %r no longer names a creation the census finds" % (key,))
            self.assertTrue(isinstance(reason, str) and len(reason.split()) >= 8, "a reason, not a label: %r" % (key,))

    def test_no_allowlisted_site_is_a_bare_primitive_without_a_mode(self):
        """Every allowlisted site sets its mode by code AT THAT SITE: the call's own lines, or the three around them, carry
        a mode literal (0o600, 0o700), an fchmod on the descriptor it opened, or a creator's tightening (make_dir); never a
        reason alone."""
        lines_by_file = {}
        for e in self.entries:
            if _key(e) in ALLOWLIST:
                text = lines_by_file.get(e["file"])
                if text is None:
                    text = lines_by_file[e["file"]] = R.source_and_tree(os.path.join(ROOT, e["file"]), e["file"])[0].splitlines()
                seg = "\n".join(text[max(0, e["line"] - 4):e["end_line"] + 3])
                self.assertTrue("0o600" in seg or "0o700" in seg or "make_dir(" in seg or "fchmod(" in seg,
                                "%s:%d %s: an allowlisted creator sets its mode at the site: %r" % (e["file"], e["line"], e["func"], seg))

    def test_the_census_reds_on_a_planted_bare_creator(self):
        """The pin can red: the planted copy of kernel/logins.py (PLANT) carries a bare mkdir, write_text, append open,
        os.open with O_CREAT, a shutil.move onto the root and an os.replace from outside it, each on a path built from a
        `state_dir` parameter; each comes out unguarded and unallowlisted, and nothing else in the copy does. The twins
        through the creators, a publish by a temp born under the root and a tempfile come out owner-only, each by its way."""
        entries = self.planted_module()
        bad = unaccounted(entries)
        self.assertEqual(sorted((e["func"], e["kind"]) for e in bad), self.PLANTED_BARE,
                         "the planted bare creators, and nothing else:\n" + "\n".join(render(bad)))
        ok = sorted((e["func"], e["kind"], e["how"]) for e in entries if e["func"].endswith("_ok"))
        self.assertEqual(ok, self.PLANTED_OK, "\n".join(render([e for e in entries if e["func"].endswith("_ok")])))

    def test_the_census_reuses_the_readers_derivation(self):
        """One derivation per module per process: the facts the readers census cached (module_facts, _FACTS) are the ones
        this census read, so the two censuses cost one parse and one derivation of each module between them."""
        for rel in MODULES:
            path = os.path.join(ROOT, rel)
            st = os.stat(path)
            self.assertIn((path, (st.st_size, st.st_mtime_ns)), R._FACTS, "%s derived once and cached" % rel)
            self.assertIn(path, R._PARSED, "%s parsed once and cached" % rel)
        loaded = [m for name, m in sys.modules.items() if name.rsplit(".", 1)[-1] == "test_state_root_readers"]
        self.assertTrue(all(m is R for m in loaded), "one readers module object in this process, the one this census reads (%r)"
                        % [name for name in sys.modules if name.rsplit(".", 1)[-1] == "test_state_root_readers"])


def _main(argv):
    entries = census(Path(ROOT), MODULES)
    for line in render(entries):
        print(line)
    bad = unaccounted(entries)
    print()
    for rel, (total, guarded, allowed, unguarded) in counts(entries).items():
        print("%-28s %3d creations: %3d owner-only by code, %2d allowlisted, %2d UNGUARDED" % (rel, total, guarded, allowed, unguarded))
    print("\n%d creations under the state root: %d owner-only by code, %d allowlisted, %d UNGUARDED"
          % (len(entries), sum(e["guarded"] for e in entries), len(entries) - sum(e["guarded"] for e in entries) - len(bad), len(bad)))
    return 1 if bad else 0


if __name__ == "__main__":
    if "--list" in sys.argv[1:]:
        sys.exit(_main(sys.argv[1:]))
    unittest.main()
