"""One parse per file per process for the AST censuses under tests/, and one derivation per key (T282; PR 891's ninth pass,
2026-09-22, agreed with the state-root censuses' pull request, which adopts it after this one lands).

WHAT IT CACHES. source_and_tree(path, rel=None) -> (text, tree): the file's text and its ast.parse'd tree, cached per
process against os.path.realpath(path) and the file's (size, mtime_ns, inode, ctime_ns): a rewrite that moves any of the
four re-parses (an in-place write moves mtime; a rename-over moves the inode; a rewrite whose mtime was put back with
os.utime leaves ctime moved), a symlink and its target are one entry (so are the relative, dotted and absolute spellings
of one path), a hard link is its own. THE BLIND SPOT, stated and left open: a rewrite that keeps the inode and the size
within the timestamp granularity (a same-size in-place write within one tick of a coarse kernel clock; a kernel with
fine-grained timestamps, 6.13 and later on the common filesystems, leaves no such tick, and the probe of 2026-09-22 saw no
stale read in thousands of immediate same-size rewrites on one) is served the OLD tree; closing it would cost a read and a
hash per call, and no caller rewrites a path in place today (the census's plants do, on files of their own, and wait out
the tick). The ninth pass keyed on size and mtime_ns alone and said here that a rewrite re-parses, which overstated: the
tenth pass's probe showed the utime-restored and the rename-over cases stale, and the two fields added see both. trees(paths)
-> [(path, text, tree)] over several files. derived(key, build) -> the value build() returned the first time the key was
asked for in the process, the memo after: a census puts its WHOLE derivation (an index over the product sources, the units
of every module, the table of rows) behind one key, so its tests and its --table road read one derivation, and two
censuses that read the same product file (kernel/kernel.py, 79k lines) parse it once between them. A build that raises is
memoised as nothing and counted as a build: the next call builds again. clear() forgets every cached parse and derivation;
clear(key, ...) forgets those derived keys, and any parsed path among them. A planted copy a test writes under a fresh
temporary directory is a path of its own, cached like any other file and dropped with the process.

THE SCOPE IS THE PROCESS. Module-level dicts, nothing on disk. Under pytest-xdist each worker is its own process with its
own cache: two censuses that land on different workers each parse and derive on their own, so no saving is claimed there.
The saving is the SERIAL run (CI's Python cells run pytest serially) and a module's own tests when pytest keeps them in one
worker (--dist loadfile or loadscope); under --dist load a class splits across workers and each derives once, a second
derivation in another process, which that process's counters do not see and no pin reads as red.

ONE LOCK. A module-level threading.RLock is held across the whole body of source_and_tree, derived and clear: two threads
asking for one path or one key get one parse or one build and the same object. Without it (the ninth pass's helper) two
threads reading kernel/kernel.py both missed and both parsed, five trials of five under 3.12 and 3.10, two tree objects
and the parse counter moving by two, and two threads on derived() built twice; a threaded reader of a product file in the
census's process would then have shown the counter pin a second parse that was no defect of the census. Re-entrant
because a build reads files and derives through the cache from the building thread (the census's tree derivation does
exactly that); the cost is that a build holds the lock for its whole run, so a build must not wait on another thread's
read of the cache, which would wait on the build's lock.

THE TWO IMPORT ROADS. Under pytest tests/ is a package (tests/__init__.py), so `from tests.parse_cache import
source_and_tree` (or `from . import parse_cache` in a test module) is one module object every test module shares. A census
run as a script (`python3 tests/test_thread_stop_census.py --table`) has no package: it puts its own directory on sys.path
first and does `import parse_cache`. One process uses one road, so one module object holds the cache either way; a
process that used both roads would hold two caches, one per module object (no census does).

THE COUNTERS, readable by tests. stats() -> {"parses": n, "derivations": n, "parse_hits": n, "derived_hits": n}: parses
counts the ast.parse calls made here (attempts, whether or not the parse succeeded), derivations the build() calls, the
hits the calls answered from the cache. parses_of(path) and builds_of(key) count the same per file and per key. The
counters are CUMULATIVE for the process and clear() leaves them alone: a census that clears the cache between two
derivations shows a second derivation in the counters, which is how a pin on the mechanism is shown red. A test pins the
mechanism by reading them: after a census's derivation entry point has run twice, builds_of(its key) is 1, every module
it read has parses_of 1, and a second parse of a cached module or a second derivation is red.

Only the standard library is imported here: the module is imported into test modules above their state preamble.
"""
import ast
import os
import threading

_PARSED = {}          # realpath -> ((size, mtime_ns, inode, ctime_ns), text, tree)
_DERIVED = {}         # key -> value
_PARSES = {}          # realpath -> the number of ast.parse calls made for it here
_BUILDS = {}          # key -> the number of build() calls made for it here
_STATS = {"parses": 0, "derivations": 0, "parse_hits": 0, "derived_hits": 0}
_LOCK = threading.RLock()   # across source_and_tree, derived and clear: one miss path at a time; re-entrant for a build's reads


def source_and_tree(path, rel=None):
    """The text and the parsed tree of the file at `path`, parsed once per process while its size, mtime_ns, inode and
    ctime_ns hold (a same-size rewrite within the timestamp granularity is the stated blind spot: the module docstring);
    `rel` is the filename the tree carries (for a SyntaxError's message), else `path`. A file that does not parse raises as
    ast.parse does, and nothing is cached for it. Under the module's lock: two threads asking for one path get one parse
    and the same tree."""
    real = os.path.realpath(path)
    with _LOCK:
        st = os.stat(real)
        key = (st.st_size, st.st_mtime_ns, st.st_ino, st.st_ctime_ns)
        hit = _PARSED.get(real)
        if hit is not None and hit[0] == key:
            _STATS["parse_hits"] += 1
            return hit[1], hit[2]
        with open(real, encoding="utf-8") as f:
            text = f.read()
        _PARSES[real] = _PARSES.get(real, 0) + 1
        _STATS["parses"] += 1
        tree = ast.parse(text, filename=rel or path)
        _PARSED[real] = (key, text, tree)
        return text, tree


def trees(paths):
    """[(path, text, tree)] for every path, each through source_and_tree."""
    return [(p,) + source_and_tree(p) for p in paths]


def derived(key, build):
    """build()'s value the first time `key` is asked for in this process, the memo after. A build that raises caches
    nothing, so the next call builds again (and is counted again). Under the module's lock, held through the build: two
    threads asking for one key get one build and the same value, and a build that reads files or derives other keys
    re-enters the lock from its own thread."""
    with _LOCK:
        if key in _DERIVED:
            _STATS["derived_hits"] += 1
            return _DERIVED[key]
        _BUILDS[key] = _BUILDS.get(key, 0) + 1
        _STATS["derivations"] += 1
        value = build()
        _DERIVED[key] = value
        return value


def clear(*keys):
    """Forget every cached parse and derivation (no arguments), or the derived keys given and any parsed path among them
    (by realpath). The counters are left as they are: they count what happened in the process. Under the module's lock."""
    with _LOCK:
        if not keys:
            _PARSED.clear()
            _DERIVED.clear()
            return
        for k in keys:
            _DERIVED.pop(k, None)
            if isinstance(k, str):
                _PARSED.pop(os.path.realpath(k), None)


def stats():
    """A copy of the counters: parses, derivations, parse_hits, derived_hits."""
    return dict(_STATS)


def parses_of(path):
    """The number of times the file at `path` was parsed here in this process."""
    return _PARSES.get(os.path.realpath(path), 0)


def builds_of(key):
    """The number of times build() ran for `key` here in this process."""
    return _BUILDS.get(key, 0)
