#!/usr/bin/env python3
"""THE CENSUS: every read of a path under the state root, derived from the code, pinned to the guarded readers.

Round 3 of the state-root review (2026-09-21) found that the roster of entries a peer could have planted under a
writable state root was a hand list of two, and that the population was at least eight; its ruling: stop enumerating,
derive the population of everything the import reads or adopts, put ONE shared guarded reader over all of it, and pin
the population so a new reader cannot join unguarded. This module is that derivation and that pin.

WHAT IT DOES. An AST census over the five modules that bind the state root at import (kernel/kernel.py, kernel/judge.py,
kernel/event_model.py, postal/postal_service.py, kernel/session_host.py) and the six kernel-side modules the kernel hands
its root to per call (kernel/logins.py, kernel/palette.py, kernel/host_transport.py, kernel/sdk_backend.py,
kernel/codex_backend.py, kernel/codex_runtime.py; the round-4 review found their reads outside the first census's view:
a planted logins record reached the login-billing road and a planted codexvenv reached sys.path[0]). It seeds each
module with its ROOT NAMES (the state root and the directories bound from it at import: the judge's rebind globals, the
bus's constants, the event model's, the session host's spec-derived attributes; for the handed-root modules every
parameter named `state_dir` or `state` and the `self.state` / `self.state_dir` attributes), then derives, to a fixpoint,
every expression that is a path under the root: a module-level name bound from a root name, a `/` or a join onto one,
a function whose return is one, a parameter a caller hands one, a local bound from one (keyed on the nearest preceding
binding, so a long dispatch that reuses `p` for a client's path and a root path in different branches is read branch
by branch), a loop or comprehension target over a root listing (a comprehension's target is bound in the comprehension's
own scope, as Python 3 binds it: it stands for the name inside the comprehension alone, and never for the def's binding
of the same name on a later line; round 4f's review found the kernel's `p` rebound by a generator over the notice rows
hiding the notice file's republish from both censuses), a scandir entry's `.path`, and the ENTRIES a guarded listing
answers. Over those it lists every READ: read_text, read_bytes, open in a read mode, os.open read-only,
gzip.open, glob, rglob, glob.glob, iterdir, listdir, scandir, is_dir and os.path.isdir, and sys.path.insert or append
of one. The bytes a read answers are data, not a path (a names entry's cwd used as a browse path is not a root read),
and writes (open in a write mode, _atomic_write, an O_EXCL temp) are not reads: tests/test_state_root_writers.py censuses the
CREATIONS over the same derivation (it imports this module and reads its cache) and pins them to the owner-only creators.

WHAT IT ASSERTS. Every read in the census either goes through a Reader (kernel/state_root_mode.py: a call on a reader
instance, whose guard lstat's every component from the root down, quarantines a failing one and reads the path as
absent) or sits on ALLOWLIST below with a one-line reason. A reader instance is recognised by its binding: a module
global assigned from `<module>.Reader(...)`, a call of a module function whose return is one (`_reader(state_dir)`, the
per-call shape of the handed-root modules), or a name ending in `_gr` (a global, an instance attribute, a local) or
named `gr` (a parameter a caller hands its reader). A new unguarded reader anywhere in the eleven modules reds this
module (test_the_census_reds_on_a_planted_unguarded_reader proves the pin can red by planting one in a copy of the
kernel). The allowlist is checked for stale entries too, so it cannot grow quietly.

HOW TO RE-RUN IT BY HAND. `python3 tests/test_state_root_readers.py --list` prints the population (file:line, function,
kind, target, guarded or allowlisted) and exits 1 when an unguarded, unallowlisted read exists. plans/state-root-mode.md
records the method. The census reads source text alone and loads no romp module.

WHAT IT DOES NOT SEE. A read through a name the derivation cannot follow (a path stored in a dict and read back, a path
handed in from another module) is invisible to it; the seeds and the parameter seeds (PARAM_SEEDS) are where such a
road is declared when found. A path derived from a process ARGUMENT is one such road: the session host's main() knows
its root from its spec path alone (`Path(argv[0])`, hosts/<sid>/spawn.json three levels under the root), so that
expression is a seed of the module and its `root` and `log_path` follow from it. The guard's own boundary is stated in kernel/state_root_mode.py: a descriptor a peer
already holds inside the root survives the tightening, so remove-and-recreate is the boundary of what any check
promises.
"""
import ast
import collections
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)

ROOT_BINDERS = ("kernel/kernel.py", "kernel/judge.py", "kernel/event_model.py", "postal/postal_service.py", "kernel/session_host.py")
HANDED_ROOT = ("kernel/logins.py", "kernel/palette.py", "kernel/host_transport.py", "kernel/sdk_backend.py",
               "kernel/codex_backend.py", "kernel/codex_runtime.py")   # handed the root per call by the kernel (jd.STATE / self.state)
MODULES = ROOT_BINDERS + HANDED_ROOT

# The ROOT NAMES per module: the expressions that ARE the state root or a directory bound from it at import. The judge's
# are its _rebind_state globals (test_the_judges_seeds_are_its_rebind_globals derives that list from the AST and holds
# this one equal to it); the kernel's are the same names through `jd.`; the bus's are its module constants; the session
# host's are the attributes its spec binds.
SEEDS = {
    "kernel/kernel.py": {"jd.STATE", "jd.NAMES", "jd.CAPDIR", "jd.ARCHDIR", "jd.GOALDIR", "jd.GOALARCHDIR", "jd.STATESDIR",
                         "jd.PCACHE", "jd.MESSAGES", "jd.ERRORS", "jd.USAGE", "jd.SDKDIR", "jd.EPIDIR", "jd.GONEDIR",
                         "jd.JUDGE_AUTH", "jd.CODEXDIR", "jd.JUDGE_SCRATCH", "jd.JUDGE_LIMIT", "jd.FAST_REFUSED",
                         "jd._overrides_dir()", "em._ckpt_dir()", "em.STATE", "em.NAMES", "em.STATES_DIR", "em.MESSAGES_LOG"},
    "kernel/judge.py": {"STATE", "NAMES", "CAPDIR", "ARCHDIR", "GOALDIR", "GOALARCHDIR", "STATESDIR", "PCACHE", "MESSAGES",
                        "ERRORS", "USAGE", "SDKDIR", "EPIDIR", "GONEDIR", "JUDGE_AUTH", "CODEXDIR", "JUDGE_SCRATCH",
                        "JUDGE_LIMIT", "FAST_REFUSED", "_overrides_dir()", "em._ckpt_dir()", "em.STATE", "em.STATES_DIR"},
    "kernel/event_model.py": {"STATE", "NAMES", "STATES_DIR", "MESSAGES_LOG", "_ckpt_dir()"},
    "postal/postal_service.py": {"STATE", "MAILROOT", "MAILPENDING", "MAILHELD", "WARNED", "LOG", "PIDFILE", "NAMES_DIR",
                                 "TLDIR", "SESSION_FLAGS", "USER_TODOS_SWITCH", "CODEX_REGISTRY", "STATE.parent"},
    "kernel/session_host.py": {"self.state_dir", "self.dir", "self.spec_path", "self.log_path", "self.sock_path",
                               "Path(argv[0])"},   # main()'s spec path: hosts/<sid>/spawn.json, argv-derived (round 4f's review)
    "kernel/logins.py": set(), "kernel/palette.py": set(), "kernel/host_transport.py": set(), "kernel/codex_runtime.py": set(),
    "kernel/sdk_backend.py": {"self.state_dir"}, "kernel/codex_backend.py": {"self.state"},
}
PARAM_SEEDS = {   # function -> parameters a caller OUTSIDE the module hands a root-derived path (kernel/host_transport.py)
    "kernel/session_host.py": {"Journal.__init__": {"directory"}},   # read_journal_dir's `directory` seeded here until PR 884 moved
                                                                     # the orphan reader to kernel/host_transport.py (by descriptor)
}
PARAM_NAME_SEEDS = {rel: {"state_dir", "state"} for rel in HANDED_ROOT}   # every parameter of these names, in every def, is the root

# THE ALLOWLIST: (file, function, kind, target text) -> the one-line reason the read is not through a Reader. Every
# entry must match a read the census finds (test_the_allowlist_carries_no_stale_entry), so the list cannot outlive the
# code it describes.
ALLOWLIST = {
    ("kernel/kernel.py", "_serve_token_read_or_mint.read", "text", "f"):
        "the serve-token loader keeps its own guards (lstat refuses a symlink before any read; every read fault but ENOENT is "
        "fatal; a foreign-owned token is unreadable or untightenable), the one copy the repo keeps on purpose, held equal to "
        "the bus's by ServeTokenLoadersMatch",
    ("kernel/kernel.py", "_serve_token_read_or_mint.mint", "dir", "f.parent"):
        "the mint's sweep of its own serve-token.*.tmp temps under the lock: each match is unlinked by name, never read",
    ("postal/postal_service.py", "_serve_token_read_or_mint.read", "text", "f"):
        "the bus's copy of the serve-token loader (see the kernel's entry): its own guards, pinned equal by ServeTokenLoadersMatch",
    ("postal/postal_service.py", "_serve_token_read_or_mint.mint", "dir", "f.parent"):
        "the bus's copy of the mint's temp sweep: unlinked by name, never read",
    ("kernel/kernel.py", "_judge_child_records", "dir", "root"):
        "os.listdir of the ROOT itself, kept for its raise on an unlistable root (Path.glob answers [] to EACCES and ENOTDIR "
        "alike), which the orphan sweep's mark depends on; each record it names is then read through _gr",
    ("kernel/judge.py", "<module>", "isdir", "STATE"):
        "the import's own read of the root after its mkdir met EEXIST: is the path a directory (ENOTDIR is the check's verdict "
        "otherwise); the gate's input, not a read of an entry",
    ("kernel/judge.py", "<module>", "dir", "STATE"):
        "the import's listing of the root at its first read, which decides the creation exemption (an empty root is a creation "
        "default); the names are counted, never opened",
    ("postal/postal_service.py", "_atomic_json_put", "open", "str(path.parent)"):
        "a directory descriptor opened O_RDONLY for fsync after an atomic publish into a directory this process just wrote: "
        "nothing is read through it",
    ("kernel/codex_backend.py", "CodexBackend._write_registry_locked", "open", "str(self.root)"):
        "the Codex registry's directory descriptor opened O_RDONLY for fsync after the atomic publish of registry.json into it: "
        "nothing is read through it (the bus's entry above is the same shape)",
    # PR 814 (the session host's socket published owner-only; merged 2026-09-21): its reads under hosts/ go through a
    # DESCRIPTOR DESCENT with its own owner check (hosts/ opened O_DIRECTORY|O_NOFOLLOW off the state root and fstat-verified
    # a directory this uid owns, <sid> the same way relative to it, every file then taken by NAME under the verified
    # descriptor with an fstat or fstatat owner compare: _stat_name, _open_host_file, host_sock_present), pinned by its own
    # census (tests/test_hosts_path_census.py) and by tests/test_host_transport.py ReadDescent. Those name-relative reads
    # carry no path under the root and this census does not see them; the three sites below are the ones it does.
    ("kernel/host_transport.py", "_open_dir_nofollow", "open", "name"):
        "814's descent: hosts/ opened by path O_RDONLY|O_DIRECTORY|O_NOFOLLOW off the state root (<sid> by name under that "
        "descriptor at the second call), then fstat-verified a directory this uid owns; nothing is read through the descriptor "
        "but the fstat, and every read below it takes a name relative to it with its own owner check (the read roads are "
        "pinned by tests/test_hosts_path_census.py and tests/test_host_transport.py ReadDescent)",
    ("kernel/session_host.py", "hosts_dir", "open", "root"):
        "814's create road: the state root this call has just made is opened O_RDONLY|O_DIRECTORY|O_NOFOLLOW for the fchmod that "
        "tightens it and the fstat that reads the mode back (a link swapped in after the lstat fails the open); nothing under "
        "the root is read through it (tests/test_session_host.py StateRootByHostsDir)",
    ("kernel/session_host.py", "SessionHost._sweep_stale_temps", "dir", "self.sock_path.parent"):
        "814's prelude: the host's sweep of its own socket temps (sock_names' *.tmp) under a hosts/ that hosts_dir has just made "
        "ours and 0700 on the same road; each match is probed by the pid in its name and unlinked by name, never read (the "
        "serve-token mint's temp sweep is the same shape)",
}

PATH_METHODS = {"with_name", "with_suffix", "with_stem", "joinpath", "resolve", "absolute", "expanduser"}
PATH_ATTRS = {"parent", "parents", "path"}   # `path`: a scandir entry's (DirEntry.path), a path under the listed directory
PATH_FUNCS = {"Path", "str", "os.fspath", "os.path.join", "os.path.realpath", "os.path.abspath", "os.path.normpath",
              "os.path.dirname", "pathlib.Path", "PurePath", "sorted", "list", "tuple", "set", "reversed", "next", "iter"}
READ_METHODS = {"read_text": "text", "read_bytes": "bytes", "iterdir": "dir", "glob": "dir", "rglob": "dir",
                "is_dir": "isdir"}
READ_FUNCS = {"open": "open", "io.open": "open", "gzip.open": "open", "os.listdir": "dir", "os.scandir": "dir",
              "glob.glob": "dir", "glob.iglob": "dir", "os.path.isdir": "isdir"}
DATA_METHODS = {"read_text", "read_bytes", "read", "readlines", "readline", "split", "splitlines", "strip", "rstrip", "lstrip",
                "decode", "encode", "get", "items", "keys", "values", "stat", "lstat", "exists", "is_file", "is_dir", "load",
                "loads", "partition", "rpartition", "lower", "upper", "startswith", "endswith", "count", "index", "find"}
DATA_FUNCS = {"json.load", "json.loads", "open", "io.open", "gzip.open", "os.stat", "os.lstat", "os.path.getsize", "os.path.exists",
              "len", "int", "float", "bool", "dict", "hash", "hashlib.sha1", "os.path.getmtime", "os.listdir", "os.scandir",
              "glob.glob", "glob.iglob", "os.fstat"}
GUARD_METHODS = {"read_text", "read_bytes", "open", "os_open", "gzip_open", "json", "listdir", "glob", "iterdir", "scandir",
                 "isdir", "is_dir", "sys_path_dir", "dir", "exists", "stat", "trust"}
LISTING_METHODS = ("iterdir", "glob", "scandir", "listdir", "dir")

# EACH FILE IS READ AND PARSED ONCE PER TEST PROCESS. The census, the seed pin and the planted-copy tests all start from
# the same text or tree, so a module's source is cached here against its size and mtime_ns (a rewrite between two calls
# re-parses), and the facts derived from a module ON DISK are cached too (the derivation is the expensive step: nine
# rounds over kernel/kernel.py's 79k lines). A planted copy has its own text: it is parsed and derived on its own and
# never cached.
_PARSED = {}   # absolute path -> ((size, mtime_ns), source text, tree)
_FACTS = {}    # (absolute path, (size, mtime_ns)) -> ModuleFacts


def source_and_tree(path, rel=None):
    """The text and the parsed tree of the file at `path`, parsed once per process while its size and mtime_ns hold."""
    st = os.stat(path)
    key = (st.st_size, st.st_mtime_ns)
    hit = _PARSED.get(path)
    if hit is None or hit[0] != key:
        src = open(path, encoding="utf-8").read()
        hit = _PARSED[path] = (key, src, ast.parse(src, filename=rel or path))
    return hit[1], hit[2]


def unparse(n):
    if isinstance(n, ast.Name):                                          # what ast.unparse answers for these two shapes,
        return n.id                                                      # without an _Unparser per call
    if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name):
        return n.value.id + "." + n.attr
    try:
        return ast.unparse(n)
    except Exception:
        return "<?>"


class ModuleFacts:
    def __init__(self, rel, tree, seeds):
        self.rel = rel
        self.tree = tree
        self.seeds = set(seeds)
        self.globals = set()
        self.funcs = {}            # qualname -> def node (top-level and one class level)
        self.root_funcs = set()    # top-level function names whose return is root-derived
        self.root_methods = set()  # class method names whose return is root-derived (self.<m>() is then root-derived)
        self.root_params = collections.defaultdict(set)
        self.readers = set()
        self.reader_funcs = set()  # top-level function names whose return is a Reader (the per-call `_reader(state_dir)`)
        self.self_attrs = set()
        self.enclosing = {}        # id(node) -> innermost enclosing def node (None at module level)
        self.calls_by_name = collections.defaultdict(list)   # callee simple name -> [Call]
        self.locals = {}           # id(def) -> {name: [(line, root-derived)]} (recomputed per round)
        self.all_calls = []
        # memos over THIS tree (the tree is held by the facts, so a node's id is stable for their lifetime): a node's
        # unparsed text, a def's own nodes and a def's binding list are each computed once and read in every round
        self.txt = {}              # id(node) -> unparse(node)
        self.own = {}              # id(def) -> _own_nodes(def)
        self.bindings = {}         # id(def) -> (names bound in the def, the bindings that say something about a path)
        self.qualname = {}         # id(def) -> its name in funcs (the reverse of funcs, for _qual)


def _txt(mf, node):
    """unparse(node), once per node of this module's tree."""
    k = id(node)
    t = mf.txt.get(k)
    if t is None:
        t = mf.txt[k] = unparse(node)
    return t


def _own(mf, fn):
    """_own_nodes(fn), once per def of this module's tree."""
    k = id(fn)
    out = mf.own.get(k)
    if out is None:
        out = mf.own[k] = _own_nodes(fn)
    return out


def build_index(mf):
    """One pass: enclosing map (innermost def), call index, function table."""
    def visit(node, cur):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                mf.enclosing[id(child)] = cur
                visit(child, child)
            else:
                mf.enclosing[id(child)] = cur
                if isinstance(child, ast.Call):
                    mf.all_calls.append(child)
                    if isinstance(child.func, ast.Name):
                        mf.calls_by_name[child.func.id].append(child)
                visit(child, cur)
    visit(mf.tree, None)
    for node in mf.tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            mf.funcs[node.name] = node
        if isinstance(node, ast.ClassDef):
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    mf.funcs[node.name + "." + sub.name] = sub
    for name, d in mf.funcs.items():
        mf.qualname.setdefault(id(d), name)   # the first name a def is filed under, as the scan in _qual answered


def _is_root(mf, node, fn):
    """Whether expression `node` derives from the state root inside def `fn` (None: module level)."""
    txt = _txt(mf, node)
    if txt in mf.seeds:
        return True
    if isinstance(node, ast.Name):
        if node.id in mf.globals:
            return True
        f = fn
        while f is not None:
            hist = list(mf.locals.get(id(f), {}).get(node.id) or [])
            if node.id in mf.root_params.get(getattr(f, "name", ""), ()):
                hist.append((getattr(f, "lineno", 0), True, None))   # a parameter is bound at the def, before every local binding
            # a comprehension's target is bound in the comprehension's OWN scope (Python 3): inside the comprehension's span
            # it is the binding of the name (the def's binding of the same name is shadowed), outside the span it does not
            # exist (the def's later lines read the def's own binding, as _compact_notices's `p` after a generator over rows)
            inside = [r for (_ln, r, span) in hist if span is not None and _within(node, span)]
            if inside:
                return any(inside)
            hist = [(ln, r) for (ln, r, span) in hist if span is None]
            if hist:
                # flow-insensitive within a function, but keyed on the NEAREST PRECEDING binding of the name (a long
                # dispatch reuses `p` for a client's path and a root path in different branches)
                hist.sort()
                before = [r for (ln, r) in hist if ln < node.lineno]
                if before:
                    return before[-1]
                return any(r for (_ln, r) in hist)     # a loop-carried or later-bound name: any root binding counts
            f = mf.enclosing.get(id(f))
        return False
    if isinstance(node, ast.Attribute):
        if txt in mf.self_attrs:
            return True
        if node.attr in PATH_ATTRS:
            return _is_root(mf, node.value, fn)
        return False
    if isinstance(node, ast.Call):
        f = _txt(mf, node.func)
        if (isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and node.func.value.id == "self"
                and node.func.attr in mf.root_methods):
            return True
        if (isinstance(node.func, ast.Attribute) and node.func.attr in ("iterdir", "glob", "scandir", "listdir", "dir")
                and _is_reader(mf, node.func.value)):
            return True           # the ENTRIES a guarded listing answers are paths under the root: their reads are censused
        if isinstance(node.func, ast.Attribute) and node.func.attr in DATA_METHODS:
            return False          # the BYTES a read answers are data, not a path under the root
        if f in DATA_FUNCS:
            return False
        if isinstance(node.func, ast.Attribute) and node.func.attr in PATH_METHODS:
            return _is_root(mf, node.func.value, fn)
        if f in PATH_FUNCS:
            return any(_is_root(mf, a, fn) for a in node.args)
        if isinstance(node.func, ast.Name) and node.func.id in mf.root_funcs:
            return True
        if (f + "()") in mf.seeds:
            return True
        if isinstance(node.func, ast.Attribute) and node.func.attr == "format":
            return _is_root(mf, node.func.value, fn) or any(_is_root(mf, a, fn) for a in node.args)
        return False
    if isinstance(node, ast.BinOp):
        if isinstance(node.op, (ast.Div, ast.Add, ast.Mod)):
            return _is_root(mf, node.left, fn) or _is_root(mf, node.right, fn)
        return False
    if isinstance(node, ast.JoinedStr):
        return any(isinstance(v, ast.FormattedValue) and _is_root(mf, v.value, fn) for v in node.values)
    if isinstance(node, (ast.Tuple, ast.List)):
        return any(_is_root(mf, e, fn) for e in node.elts)
    if isinstance(node, ast.Subscript):
        return _is_root(mf, node.value, fn)
    if isinstance(node, ast.IfExp):
        return _is_root(mf, node.body, fn) or _is_root(mf, node.orelse, fn)
    if isinstance(node, ast.BoolOp):
        return any(_is_root(mf, v, fn) for v in node.values)
    if isinstance(node, ast.NamedExpr):
        return _is_root(mf, node.value, fn)
    if isinstance(node, (ast.ListComp, ast.GeneratorExp, ast.SetComp)):
        for g in node.generators:
            if _is_root(mf, g.iter, fn):
                return True          # elements of a listing of a root directory are root-derived entries
        return _is_root(mf, node.elt, fn)
    return False


COMPREHENSIONS = (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)


def _span(n):
    """A node's (line, column, end line, end column): the text a comprehension's target is bound over."""
    return (n.lineno, n.col_offset, n.end_lineno, n.end_col_offset)


def _within(node, span):
    return (node.lineno, node.col_offset) >= span[:2] and (node.end_lineno, node.end_col_offset) <= span[2:]


def _hist_key(e):
    return (e[0], e[1], e[2] or ())


def _targets(t):
    """The names a target BINDS: a Name, the Names inside a Tuple, List or Starred. A Subscript or Attribute target
    (cache[str(p)] = ..., self.x = ...) mutates an object and binds no name (the names inside it are reads)."""
    if isinstance(t, ast.Name):
        return [t.id]
    if isinstance(t, (ast.Tuple, ast.List)):
        return [n for e in t.elts for n in _targets(e)]
    if isinstance(t, ast.Starred):
        return _targets(t.value)
    return []


def _own_nodes(fn):
    """The nodes of `fn` not inside a nested def (those belong to the nested def's scope)."""
    out = []
    stack = [fn]
    while stack:
        node = stack.pop()
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                continue
            out.append(child)
            stack.append(child)
    return out


def _seed_locals(mf, fn):
    """Fixpoint over the function's own nodes: every binding of a local (assignments, loop, with and comprehension
    targets) recorded as (line, root-derived, span) in mf.locals[id(fn)][name], sorted by line; the span is None for a
    binding of the def's scope and the comprehension's text span for a comprehension target, which _is_root reads inside
    that span alone. A nested def sees its parent's bindings (closures read the parent's path variables)."""
    parent = mf.enclosing.get(id(fn))
    hist = {k: list(v) for k, v in mf.locals.get(id(parent), {}).items()} if parent is not None else {}
    mf.locals[id(fn)] = hist
    cached = mf.bindings.get(id(fn))
    if cached is None:
        cached = mf.bindings[id(fn)] = _bindings(mf, fn)
    bound, bindings = cached
    for name in bound:
        hist.setdefault(name, [])
    for _round in range(8):
        changed = False
        for ln, names, value, span in bindings:
            r = _is_root(mf, value, fn)
            for name in names:
                cur = hist[name]
                if (ln, r, span) not in cur:
                    cur[:] = sorted([e for e in cur if (e[0], e[2]) != (ln, span)] + [(ln, r, span)], key=_hist_key)
                    changed = True
        if not changed:
            break


def _bindings(mf, fn):
    """The def's bindings, read from its own nodes once: (the names it binds, in first-seen order; the bindings whose
    value says something about a path, as (lineno, [names], value node, span)). The span is None for a binding of the
    def's own scope; for a comprehension's target it is the comprehension's text span, the scope Python 3 binds it in."""
    bindings = []          # (lineno, [names], value node, span)
    for n in _own(mf, fn):
        if isinstance(n, ast.Assign):
            bindings.append((n.lineno, [x for t in n.targets for x in _targets(t)], n.value, None))
        elif isinstance(n, (ast.AnnAssign, ast.AugAssign)) and n.value is not None:
            bindings.append((n.lineno, _targets(n.target), n.value, None))
        elif isinstance(n, ast.NamedExpr):
            bindings.append((n.lineno, [n.target.id], n.value, None))
        elif isinstance(n, (ast.For, ast.AsyncFor)):
            bindings.append((n.lineno, _targets(n.target), n.iter, None))
        elif isinstance(n, (ast.With, ast.AsyncWith)):
            for item in n.items:
                if item.optional_vars is not None:
                    bindings.append((n.lineno, _targets(item.optional_vars), item.context_expr, None))
        elif isinstance(n, COMPREHENSIONS):
            for g in n.generators:
                bindings.append((g.iter.lineno, _targets(g.target), g.iter, _span(n)))
    bound = list(dict.fromkeys(name for _ln, names, _v, _s in bindings for name in names))
    def _empty_literal(v):
        # a fallback binding to an empty literal (`boxes = []` in an except arm) says nothing about the name's path-ness
        return (isinstance(v, (ast.List, ast.Tuple, ast.Dict, ast.Set)) and not getattr(v, "elts", getattr(v, "keys", None))) \
            or (isinstance(v, ast.Constant) and v.value in (None, "", b""))
    return bound, [b for b in bindings if not _empty_literal(b[2])]


def module_facts(root, rel, src=None):
    """The census's facts for one module: its root-derived names, functions, parameters, attributes and reader instances,
    derived to a fixpoint (bounded rounds). `src` overrides the file's text (the mutation tests); without it the module
    on disk is parsed and derived once per process (source_and_tree, _FACTS) and the facts are reused."""
    if src is not None:
        return _derive(rel, ast.parse(src, filename=rel))
    path = os.path.join(str(root), rel)
    st = os.stat(path)
    key = (path, (st.st_size, st.st_mtime_ns))
    mf = _FACTS.get(key)
    if mf is None:
        _src, tree = source_and_tree(path, rel)
        mf = _FACTS[key] = _derive(rel, tree)
    return mf


def _derive(rel, tree):
    mf = ModuleFacts(rel, tree, SEEDS.get(rel, set()))
    build_index(mf)
    for fname, params in PARAM_SEEDS.get(rel, {}).items():
        mf.root_params[fname.split(".")[-1]].update(params)
    all_defs, self_assigns = [], []          # one walk: every def, and every `self.<attr> = ...`
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            all_defs.append(n)
        elif isinstance(n, ast.Assign) and any(isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) and t.value.id == "self"
                                               for t in n.targets):
            self_assigns.append(n)
    for d in all_defs:                       # the handed-root modules: every `state_dir` / `state` parameter is the root
        for a in d.args.posonlyargs + d.args.args + d.args.kwonlyargs:
            if a.arg in PARAM_NAME_SEEDS.get(rel, ()):
                mf.root_params[d.name].add(a.arg)
    for name, fn in mf.funcs.items():        # a function whose return is `<x>.Reader(...)` answers a reader (`_reader(state_dir)`)
        if "." not in name and any(isinstance(n, ast.Return) and isinstance(n.value, ast.Call)
                                   and _txt(mf, n.value.func).endswith(".Reader") for n in _own(mf, fn)):
            mf.reader_funcs.add(name)
    # order defs outer-first so a nested def sees its parent's locals
    depth = {}
    for d in all_defs:
        k, p = 0, mf.enclosing.get(id(d))
        while p is not None:
            k += 1
            p = mf.enclosing.get(id(p))
        depth[id(d)] = k
    all_defs.sort(key=lambda d: depth[id(d)])
    for _round in range(12):
        changed = False
        for node in tree.body:
            if isinstance(node, ast.Assign):
                if isinstance(node.value, ast.Call) and _txt(mf, node.value.func).endswith(".Reader"):
                    for t in node.targets:
                        for name in _targets(t):
                            if name not in mf.readers:
                                mf.readers.add(name); changed = True
                    continue
                if _is_root(mf, node.value, None):
                    for t in node.targets:
                        for name in _targets(t):
                            if name not in mf.globals:
                                mf.globals.add(name); changed = True
        for d in all_defs:
            _seed_locals(mf, d)
        for name, fn in mf.funcs.items():
            for n in _own(mf, fn):
                if isinstance(n, ast.Return) and n.value is not None and _is_root(mf, n.value, fn):
                    if "." in name:
                        m = name.split(".", 1)[1]
                        if m not in mf.root_methods:
                            mf.root_methods.add(m); changed = True
                    elif name not in mf.root_funcs:
                        mf.root_funcs.add(name); changed = True
                    break
        for n in self_assigns:
            fn = mf.enclosing.get(id(n))
            if _is_root(mf, n.value, fn):
                for t in n.targets:
                    txt = _txt(mf, t)
                    if txt.startswith("self.") and txt not in mf.self_attrs:
                        mf.self_attrs.add(txt); changed = True
        for fn_name, fn in mf.funcs.items():
            if "." in fn_name:
                continue
            params = [a.arg for a in fn.args.posonlyargs + fn.args.args + fn.args.kwonlyargs]
            for call in mf.calls_by_name.get(fn_name, ()):
                caller = mf.enclosing.get(id(call))
                for i, a in enumerate(call.args):
                    if i < len(params) and _is_root(mf, a, caller):
                        if params[i] not in mf.root_params[fn_name]:
                            mf.root_params[fn_name].add(params[i]); changed = True
                for kw in call.keywords:
                    if kw.arg in params and _is_root(mf, kw.value, caller):
                        if kw.arg not in mf.root_params[fn_name]:
                            mf.root_params[fn_name].add(kw.arg); changed = True
        if not changed:
            break
    return mf


def _read_mode_is_read(call, mode_index=1):
    for i, a in enumerate(call.args):
        if i == mode_index and isinstance(a, ast.Constant) and isinstance(a.value, str):
            return "r" in a.value and not any(c in a.value for c in "wax+")
    for kw in call.keywords:
        if kw.arg == "mode" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
            return "r" in kw.value.value and not any(c in kw.value.value for c in "wax+")
    return True


def _qual(mf, fn):
    if fn is None:
        return "<module>"
    name = mf.qualname.get(id(fn))
    if name is not None:
        return name
    parent = mf.enclosing.get(id(fn))
    return (_qual(mf, parent) + "." if parent is not None else "") + getattr(fn, "name", "<lambda>")



def _is_reader(mf, recv):
    """Whether `recv` is a reader instance: a module global bound from `.Reader(...)`, a call of a function that returns
    one (`_reader(state_dir)`), a name ending in `_gr` (a global, `self._gr`, a local), or a parameter named `gr`."""
    if isinstance(recv, ast.Name) and (recv.id in mf.readers or recv.id == "gr"):
        return True
    if isinstance(recv, ast.Call) and isinstance(recv.func, ast.Name) and recv.func.id in mf.reader_funcs:
        return True
    return _txt(mf, recv).endswith("_gr")


def census(root, rels, sources=None):
    """Every read of a path under the state root in `rels` (files under `root`, or the texts `sources` maps them to):
    dicts with file, func, line, kind, target and guarded."""
    entries = []
    for rel in rels:
        src = (sources or {}).get(rel)
        mf = module_facts(root, rel, src)
        for n in mf.all_calls:
            fn = mf.enclosing.get(id(n))
            f = n.func
            ftxt = _txt(mf, f)
            kind = target = None
            guarded = False
            if isinstance(f, ast.Attribute):
                recv = f.value
                if _is_reader(mf, recv) and f.attr in GUARD_METHODS:
                    guarded, kind = True, f.attr
                    target = n.args[0] if n.args else None
                elif f.attr in READ_METHODS and _is_root(mf, recv, fn):
                    kind, target = READ_METHODS[f.attr], recv
                elif f.attr == "open" and _is_root(mf, recv, fn) and _read_mode_is_read(n, 0):
                    kind, target = "open", recv
                elif ftxt == "os.open" and n.args and _is_root(mf, n.args[0], fn) and (
                        len(n.args) < 2 or not any(w in unparse(n.args[1])
                                                   for w in ("O_WRONLY", "O_RDWR", "O_CREAT", "O_APPEND", "O_TRUNC"))):
                    kind, target = "open", n.args[0]
                elif ftxt in READ_FUNCS and n.args and _is_root(mf, n.args[0], fn):
                    if ftxt in ("io.open", "gzip.open") and not _read_mode_is_read(n):
                        continue
                    kind, target = READ_FUNCS[ftxt], n.args[0]
                elif ftxt in ("sys.path.insert", "sys.path.append") and n.args and _is_root(mf, n.args[-1], fn):
                    kind, target = "syspath", n.args[-1]
            elif isinstance(f, ast.Name) and f.id == "open" and n.args and _is_root(mf, n.args[0], fn) and _read_mode_is_read(n):
                kind, target = "open", n.args[0]
            if kind is None:
                continue
            entries.append({"file": rel, "func": _qual(mf, fn), "line": n.lineno, "kind": kind,
                            "target": _txt(mf, target) if target is not None else "", "guarded": guarded})
    return entries


def unaccounted(entries):
    """The census entries that are neither guarded nor allowlisted."""
    return [e for e in entries if not e["guarded"] and (e["file"], e["func"], e["kind"], e["target"]) not in ALLOWLIST]


def render(entries):
    lines = []
    for e in entries:
        how = "guarded" if e["guarded"] else ("allowlisted" if (e["file"], e["func"], e["kind"], e["target"]) in ALLOWLIST else "UNGUARDED")
        lines.append("%s:%d %s [%s] %s: %s" % (e["file"], e["line"], e["func"], e["kind"], e["target"], how))
    return lines


class TheCensus(unittest.TestCase):
    """The population of reads under the state root, derived by code and pinned to the guarded readers."""

    # THE PLANT: one copy of kernel/kernel.py with every planted shape the two reach tests below assert on, derived ONCE
    # per class (planted_kernel) and inspected by both; a separate copy per shape cost a full derivation of the kernel's
    # 79k lines each. The bare pair (_planted_reader, _planted_listing) and its guarded twin (_planted_reader_gr,
    # _planted_listing_gr) are the "can red" and "comes out clean" halves of the pin; the rest are the derivation's reach.
    PLANT = ('\n\ndef _planted_reader():\n    return json.loads((jd.STATE / "planted.json").read_text())\n\n\n'
             'def _planted_listing():\n    d = jd.STATE / "planted"\n    return os.listdir(d)\n\n\n'
             'def _planted_reader_gr():\n    return json.loads(_gr.read_text(jd.STATE / "planted.json"))\n\n\n'
             'def _planted_listing_gr():\n    d = jd.STATE / "planted"\n    return _gr.listdir(d)\n\n\n'
             'def _planted_helper(path):\n    return path.read_text()\n\n\n'
             'def _planted_caller():\n    return _planted_helper(jd.STATE / "a.json")\n\n\n'
             'def _planted_path():\n    return jd.STATE / "b.json"\n\n\n'
             'def _planted_call_site():\n    return json.loads(_planted_path().read_text())\n\n\n'
             'def _planted_loop():\n    out = []\n    for f in _gr.iterdir(jd.STATE / "d"):\n        out.append(f.read_text())\n    return out\n\n\n'
             'def _planted_rebound(msg):\n    p = jd.STATE / "c.json"\n    _gr.read_text(p)\n    p = str(msg["path"])\n    return open(p, "rb").read()\n\n\n'
             # the two comprehension scopes (round 4f's review): a generator that rebinds `p` over data rows does not hide the
             # def's own `p` from a read on a later line; a comprehension's target over a root listing is a root entry inside it
             'def _planted_comp_shadow(rows):\n    p = jd.STATE / "e.json"\n    tgt = next((p for p in rows if p.get("k")), None)\n'
             '    return p.read_text()\n\n\n'
             'def _planted_comp_entries():\n    return [f.read_text() for f in _gr.iterdir(jd.STATE / "d")]\n')
    PLANTED_BARE = [("_planted_call_site", "text"), ("_planted_comp_entries", "text"), ("_planted_comp_shadow", "text"),
                    ("_planted_helper", "text"), ("_planted_listing", "dir"), ("_planted_loop", "text"),
                    ("_planted_reader", "text")]   # every unguarded read the plant carries
    _planted = None

    @classmethod
    def setUpClass(cls):
        cls.entries = census(Path(ROOT), MODULES)

    @classmethod
    def planted_kernel(cls):
        """The census of the one planted copy of kernel/kernel.py, derived on first use and shared by the class."""
        if cls._planted is None:
            src, _tree = source_and_tree(os.path.join(ROOT, "kernel", "kernel.py"), "kernel/kernel.py")
            cls._planted = census(Path(ROOT), ["kernel/kernel.py"], sources={"kernel/kernel.py": src + cls.PLANT})
        return cls._planted

    def test_every_read_of_a_path_under_the_root_is_guarded_or_allowlisted(self):
        """THE PIN. Every read the census finds in the eleven modules goes through a Reader, or sits on ALLOWLIST with its
        reason. A new unguarded reader anywhere in them fails here, naming its file, line, function and target."""
        bad = unaccounted(self.entries)
        self.assertEqual(bad, [], "unguarded reads of paths under the state root:\n" + "\n".join(render(bad)))
        guarded = [e for e in self.entries if e["guarded"]]
        self.assertGreater(len(guarded), 300, "the census sees the population (%d guarded reads)" % len(guarded))
        by_file = collections.Counter(e["file"] for e in guarded)
        for rel in MODULES:
            self.assertGreater(by_file[rel], 0, "%s has guarded reads (%r)" % (rel, dict(by_file)))

    def test_the_allowlist_carries_no_stale_entry_and_every_entry_has_a_reason(self):
        found = {(e["file"], e["func"], e["kind"], e["target"]) for e in self.entries if not e["guarded"]}
        for key, reason in ALLOWLIST.items():
            self.assertIn(key, found, "a stale allowlist entry: %r no longer names a read the census finds" % (key,))
            self.assertTrue(isinstance(reason, str) and len(reason.split()) >= 8, "a reason, not a label: %r" % (key,))

    def test_the_census_reds_on_a_planted_unguarded_reader(self):
        """The pin can red: the planted copy of kernel/kernel.py (PLANT) has one new function that reads
        `(jd.STATE / "planted.json")` through Path.read_text and one that lists `jd.STATE / "planted"` through
        os.listdir; both come out unguarded and unallowlisted, and nothing in the copy but the plant's bare reads does.
        The same two reads through _gr (_planted_reader_gr, _planted_listing_gr) come out clean: seen, as guarded."""
        entries = self.planted_kernel()
        bad = unaccounted(entries)
        self.assertEqual(sorted((e["func"], e["kind"]) for e in bad), self.PLANTED_BARE,
                         "the planted bare reads, and nothing else:\n" + "\n".join(render(bad)))
        self.assertIn(("_planted_reader", "text"), [(e["func"], e["kind"]) for e in bad])
        self.assertIn(("_planted_listing", "dir"), [(e["func"], e["kind"]) for e in bad])
        self.assertEqual(sorted((e["func"], e["kind"], e["guarded"]) for e in entries if e["func"].endswith("_gr")),
                         [("_planted_listing_gr", "listdir", True), ("_planted_reader_gr", "read_text", True)],
                         "the guarded reads are still seen, as guarded, one entry each")

    def test_a_reader_through_a_parameter_a_helper_and_a_loop_is_seen(self):
        """The derivation's reach, pinned on the planted shapes (PLANT): a helper whose parameter a caller hands a root
        path; a function whose return is a root path, read at its call site; the entries of a listing of a root
        directory, read in a loop; a local rebound to a client's path in a later branch is NOT flagged (the nearest
        preceding binding decides), nor is the caller that only hands the path on."""
        entries = self.planted_kernel()
        reach = {"_planted_helper", "_planted_caller", "_planted_path", "_planted_call_site", "_planted_loop", "_planted_rebound"}
        bad = sorted(e["func"] for e in unaccounted(entries) if e["func"] in reach)
        self.assertEqual(bad, ["_planted_call_site", "_planted_helper", "_planted_loop"], "\n".join(render(unaccounted(entries))))
        self.assertEqual(sorted(e["func"] for e in entries if e["func"] == "_planted_rebound"), ["_planted_rebound"],
                         "the rebound local's guarded read of the root path is seen; its later read of the client's path is not")

    def test_the_judges_seeds_are_its_rebind_globals(self):
        """The judge's seed list is not a hand list: it is what _rebind_state declares global (the names a test's rebind
        moves), read from the AST, plus the call-time derivations (_overrides_dir(), em._ckpt_dir()) and the event
        model's constants; the kernel's seeds are the same names through `jd.`."""
        _src, tree = source_and_tree(os.path.join(ROOT, "kernel", "judge.py"), "kernel/judge.py")
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_rebind_state")
        declared = set()
        for n in ast.walk(fn):
            if isinstance(n, ast.Global):
                declared.update(n.names)
        self.assertTrue(declared, "the rebind declares its globals")
        expected = set(declared) | {"_overrides_dir()", "em._ckpt_dir()", "em.STATE", "em.STATES_DIR"}
        self.assertEqual(SEEDS["kernel/judge.py"], expected)
        self.assertEqual(SEEDS["kernel/kernel.py"], {"jd." + s for s in declared} | {"jd._overrides_dir()", "em._ckpt_dir()", "em.STATE",
                                                                                     "em.NAMES", "em.STATES_DIR", "em.MESSAGES_LOG"})

    def test_the_bus_and_the_kernel_hold_a_reader_over_the_root(self):
        """The census recognises a module's reader instances by their binding to the shared module's Reader class; each of
        the eleven modules binds at least one: the five root binders hold a `_gr` (the session host's are instance
        attributes named _gr, and the census recognises those by name), the six handed-root modules build one per call
        through `_reader(state_dir)`, a function whose return the census recognises as a reader."""
        for rel in MODULES:
            src, _tree = source_and_tree(os.path.join(ROOT, rel), rel)
            self.assertIn(".Reader(", src, rel)
            self.assertIn("_gr" if rel in ROOT_BINDERS else "_reader(", src, rel)
        for rel in HANDED_ROOT:
            mf = module_facts(Path(ROOT), rel)
            self.assertIn("_reader", mf.reader_funcs, rel)

    def test_a_handed_root_modules_planted_reads_are_seen(self):
        """The handed-root derivation, pinned on planted shapes in a copy of kernel/logins.py: a read of a path built from
        a `state_dir` parameter is censused (unguarded when bare, guarded through `_reader(state_dir)`), a read through a
        `gr` parameter is guarded, and a scandir entry's `.path` read is seen."""
        src, _tree = source_and_tree(os.path.join(ROOT, "kernel", "logins.py"), "kernel/logins.py")
        plant = ('\n\ndef _planted_bare(state_dir):\n    return (Path(state_dir) / "x.json").read_text()\n\n\n'
                 'def _planted_guarded(state_dir):\n    return _reader(state_dir).read_text(Path(state_dir) / "x.json")\n\n\n'
                 'def _planted_param(p, gr):\n    with gr.open(p, "rb") as f:\n        return f.read()\n\n\n'
                 'def _planted_entries(state_dir):\n    out = []\n    for de in list(_reader(state_dir).scandir(Path(state_dir) / "d")):\n'
                 '        out.append(open(de.path).read())\n    return out\n')
        entries = census(Path(ROOT), ["kernel/logins.py"], sources={"kernel/logins.py": src + plant})
        bad = sorted((e["func"], e["kind"]) for e in unaccounted(entries))
        self.assertEqual(bad, [("_planted_bare", "text"), ("_planted_entries", "open")],
                         "\n".join(render(unaccounted(entries))))
        self.assertIn(("_planted_guarded", "read_text", True), [(e["func"], e["kind"], e["guarded"]) for e in entries])   # a guarded read's kind is the reader method
        self.assertIn(("_planted_param", "open", True), [(e["func"], e["kind"], e["guarded"]) for e in entries])


def _main(argv):
    entries = census(Path(ROOT), MODULES)
    for line in render(entries):
        print(line)
    bad = unaccounted(entries)
    print("\n%d reads under the state root: %d guarded, %d allowlisted, %d UNGUARDED"
          % (len(entries), sum(e["guarded"] for e in entries), len(entries) - sum(e["guarded"] for e in entries) - len(bad), len(bad)))
    return 1 if bad else 0


if __name__ == "__main__":
    if "--list" in sys.argv[1:]:
        sys.exit(_main(sys.argv[1:]))
    unittest.main()
