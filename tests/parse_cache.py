"""One parse per file per process for the AST censuses under tests/, and one derivation per key (T282; PR 891's ninth pass,
2026-09-22, agreed with the state-root censuses' pull request, which adopts it after this one lands).

WHAT IT CACHES. source_and_tree(path, rel=None) -> (text, tree): the file's text and its ast.parse'd tree, cached per
process against (os.path.realpath(path), size, mtime_ns): a rewrite between two calls re-parses, a symlink and its target
are one entry. trees(paths) -> [(path, text, tree)] over several files. derived(key, build) -> the value build() returned the
first time the key was asked for in the process, the memo after: a census puts its WHOLE derivation (an index over the
product sources, the units of every module, the table of rows) behind one key, so its tests and its --table road read one
derivation, and two censuses that read the same product file (kernel/kernel.py, 79k lines) parse it once between them.
clear() forgets every cached parse and derivation; clear(key, ...) forgets those derived keys, and any parsed path among
them. A planted copy a test writes under a fresh temporary directory is a path of its own, cached like any other file
and dropped with the process.

THE SCOPE IS THE PROCESS. Module-level dicts, nothing on disk. Under pytest-xdist each worker is its own process with its
own cache: two censuses that land on different workers each parse and derive on their own, so no saving is claimed there.
The saving is the SERIAL run (CI's Python cells run pytest serially) and a module's own tests, which pytest keeps in one
worker.

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

_PARSED = {}          # realpath -> ((size, mtime_ns), text, tree)
_DERIVED = {}         # key -> value
_PARSES = {}          # realpath -> the number of ast.parse calls made for it here
_BUILDS = {}          # key -> the number of build() calls made for it here
_STATS = {"parses": 0, "derivations": 0, "parse_hits": 0, "derived_hits": 0}


def source_and_tree(path, rel=None):
    """The text and the parsed tree of the file at `path`, parsed once per process while its size and mtime_ns hold; `rel`
    is the filename the tree carries (for a SyntaxError's message), else `path`. A file that does not parse raises as
    ast.parse does, and nothing is cached for it."""
    real = os.path.realpath(path)
    st = os.stat(real)
    key = (st.st_size, st.st_mtime_ns)
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
    nothing, so the next call builds again (and is counted again)."""
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
    (by realpath). The counters are left as they are: they count what happened in the process."""
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
