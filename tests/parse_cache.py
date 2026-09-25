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
memoised as nothing and counted as a build: the next call builds again. clear() forgets every cached parse and derivation,
and clear(key, ...) those derived keys and any parsed path among them; forgetting drops the cache's references only, so a
tree a frozen cycle still holds (a derivation's value that references its trees through a cycle, as the census's _Tree does
through its modules and their units) stays alive for the process, since nothing here unfreezes (the retention shape, below).
A planted copy a test writes under a fresh temporary directory is a path of its own, cached like any other file and dropped
with the process.

THE SCOPE IS THE PROCESS. Module-level dicts, nothing on disk. Under pytest-xdist each worker is its own process with its
own cache: two censuses that land on different workers each parse and derive on their own, so no saving is claimed there.
The saving is the SERIAL run (CI's Python cells ran pytest serially until 2026-09-25 and run two workers under --dist load
since) and a module's own tests when pytest keeps them in one worker (--dist loadfile or loadscope); under --dist load a
class splits across workers and each derives once, a second derivation in another process, which that process's counters
do not see and no pin reads as red.

ONE LOCK. A module-level threading.RLock is held across the whole body of source_and_tree, derived and clear: two threads
asking for one path or one key get one parse or one build and the same object. Without it (the ninth pass's helper) two
threads reading kernel/kernel.py both missed and both parsed, five trials of five under 3.12 and 3.10, two tree objects
and the parse counter moving by two, and two threads on derived() built twice; a threaded reader of a product file in the
census's process would then have shown the counter pin a second parse that was no defect of the census. Re-entrant
because a build reads files and derives through the cache from the building thread (the census's tree derivation does
exactly that); the cost is that a build holds the lock for its whole run, so a build must not wait on another thread's
read of the cache, which would wait on the build's lock.

THE CONTRACT FOR EVERY CONSUMER (stated on the thread-stop census's eleventh pass, 2026-09-22, after CI's Python 3.11
cell errored its tree tests with a RecursionError inside copy.py; the census's docstring carries the history). A cached
tree is READ-ONLY for every consumer: no attribute is written on a cached node, no in-place transformer
(ast.NodeTransformer.visit, fix_missing_locations, a copy_location onto a cached node) runs over a cached tree, and a
consumer that needs a changed or bound copy of a node copies it first, with an ITERATIVE copier (an explicit stack over
the node's _fields and _attributes, non-AST leaves shared, any other attribute ignored), never copy.deepcopy. Per-node
data a consumer derives (the unit a helper's returned literal is read in, in the thread-stop census) lives in a side
table keyed by id(node) that the consumer owns and clears with its derivation, so nothing one consumer writes is
inherited by the next reader of the same tree. The thread-stop census's no-foreign-attribute pin walks every node of
every cached tree after its derivation (cached_trees() hands it every (realpath, tree) held) and asserts each carries
only its _fields and _attributes, so a consumer that breaks the contract in the same process is shown there.
THE RETENTION SHAPE is part of the contract (the fourteenth pass, 2026-09-22, from the whole-suite serial measurement under
Python 3.10, which romp-manager ruled the shape must come from; its ruling named two admissible shapes, gc.freeze() once
after the derivation or releasing the trees once every consumer has derived, and a bounded gc.disable() inside the cache's
build only if collections during the build measured a material share, never in a test body). The trees a derivation reads
stay alive for the rest of the process, held here, and the measurement put two costs on that. Inside the census's build the
collector ran five full collections that took near half of the derivation, each walking every tracked object, the trees
under construction among them; after the census not one full collection ran for the rest of that run, so the retained
trees cost the test phase nothing in that order. And after pytest's clock had stopped, the interpreter's finalization,
whose full collections walk every tracked object, took about twice main's, with about twice main's tracked objects alive,
a cost that lands in every run whatever the order. So derived() does two things around a build when it finds the
collector enabled: it disables the collector before the build and re-enables it in a finally, on the returning road and
on the raising road alike, never touching a collector the caller had disabled; and after a build that RETURNED and
passed the after-check it calls gc.freeze() once, before it returns, which moves every object then tracked into the
permanent generation, which no later collection walks, automatic, explicit or the finalization's. THE COLLECTOR'S EXIT
STATE, in one rule: a collector found on is handed back on, whatever the build did to it (a build that disabled it and
left it off is handed back on by the finally); a collector found off is left as the build left it (a build that enabled
it leaves it on, and the helper calls gc.enable() for no collector it found off). The census's pins hold the four
corners (ParseCacheRetention; the fifteenth pass's verification, 2026-09-22, found the fourteenth's wording of this rule
contradictory). The freeze runs before derived() returns, so no allocation after the build is collected over the build's
objects: the first allocation after a re-enable triggers a young collection over everything the build allocated (a
fifth of a second over six million objects in the probe, and nothing once they were frozen first; on the interpreters
with a GIL the freeze itself is a list splice, microseconds whatever the count, and the free-threaded build's walks its
heaps to mark them, milliseconds per million objects). The freeze is PROCESS-GLOBAL: every object TRACKED at that moment
leaves the collector's generations for the rest of the process, the cache's trees and everything else tracked, each
build freezing what is tracked then, a hit on the memo freezing nothing, and gc.unfreeze is never called. Tracked, not
alive, and that is THE RULE FOR A BUILD: the collector is off for the whole build, so a cycle the build drops before
returning is still in the generations at the freeze and is frozen with the result, never reclaimed; a build must break
its own cycles before it returns, so that reference counting frees what it drops. The rule was found by measurement
(the fifteenth pass): the thread-stop census's build kept its modules index as a local, whose _Module/_Unit graph is
cyclic, and the derivation froze about 780 thousand dead objects with the trees (a tenth of what it froze; about 150 MB
by sys.getsizeof and 2.7 million allocator blocks the process never reused, per deriving process), until the census's
build released them (tests/test_thread_stop_census.py, _Tree; its ParseCacheRetention pin builds the census's _Tree over
a plant with the collector off and asserts gc.collect() finds nothing). A collection in derived() before the freeze was
the other road, refused: it walks every tracked object, about 4 s at the census's heap on 3.10 and 3.12, a third of what
the shape saves. The count gc.get_freeze_count() reads is live, growing with each build here and dropping when a frozen
object dies by reference count, and reading it WALKS the permanent generation's list: a tenth of a second per read over
the eight million objects the census freezes, up to a second once a collection has scattered the heap, so nothing in
this module reads it and a pin reads it at most twice. EVERY READER PAYS THAT after a derivation, not this module's pins
alone: kernel/kernel.py's perf snapshot (_PerfStats.snapshot) reads gc.get_freeze_count() on every call, so a test that
reads the snapshot after the census in the same process runs 2 to 60 times slower per read, about 2 s over a serial run
(CI's cells until 2026-09-25; four snapshot-reading modules sort after the census) and 18 to 25 s for an xdist worker that
runs the census before tests/test_kernel_delta_send.py (measured by the fifteenth pass's verification on 3.10 and 3.12; no
test outcome changed). The kernel side (a memoised count behind a cheap check) is a follow-up for the kernel's perf owner, not this
tests-only change. Acceptable in a test process because the process is a test run and
ends with it: an object alive at a freeze that later falls into an unreachable cycle is never reclaimed by the collector
(a cycle made after the freeze is, as before), gc.get_objects() no longer lists what is frozen, and a full collection
over a frozen heap costs microseconds on the interpreters with a GIL; the free-threaded build's collector, which has one
generation and reports every automatic collection as generation 0, freezes the same objects (the count grows, a later
collection leaves them) but still visits its heaps to skip them, about half the cost rather than none. A consumer that
needs the trees walked again, or reclaimed, has no road here: the shape is the freeze, not the release.

THE SINGLETON PIN (the thread-stop census's twelfth pass, 2026-09-22; the mechanism read back by CI's diagnostic run
35740276523). The parser hands out ONE instance of each expression context (ast.Load, ast.Store, ast.Del) and of each
operator (the ast.operator, ast.boolop, ast.unaryop and ast.cmpop subclasses) per process, shared by every tree it builds
(SINGLETON_TYPES; ast.Load() builds a fresh, unshared one, the parser's is the ctx of any parsed Name). An attribute
written on one rides on every tree parsed afterwards in the process, cached here or not. In CI's serial cell
tests/test_hosts_path_census.py, which marked every node of its own trees with `_fn` and `_parent` (guarded since), ran
before the thread-stop census, whose copy.deepcopy of a two-node hand (a Name and its Load) followed the shared Load's
`_parent` into that census's whole graph: a RecursionError inside copy.py on Python 3.10 and 3.11, where the C frames of
deepcopy's reduce road count against the recursion limit, and on 3.12 a completed copy of the graph, 147 s in the
census's setUpClass and a minute in one of its plants. The census's iterative copier made it immune; this pin makes the
WRITER visible. check_singletons(where) probes two separate parses of one small text that uses every context and
operator, reads the instance of each type from the PARSES and asserts it is the same object in both (parser_singletons;
never a constructed ast.Load(), which is fresh and unshared and would read clean beside a polluted parser instance;
two parses that disagree are their own red), and raises AssertionError when any carries an attribute, the message
naming each node, attribute and value type (singleton_attributes: one (node type, attribute name, value type name)
tuple per attribute, from which singleton_lines renders `Load carries _fn (Fn), _parent (Module)` and the remedy its
grep for each attribute name; both read the tuples, neither re-parses a rendered line), the site it ran at, and the
remedy: another module that ran earlier in this process wrote it on a node the parser shares with every tree; grep
tests/ for that write over AST walks and guard singleton nodes. It runs here on the FIRST parse of the process
(source_and_tree: once, the flag set before the check so it runs once whatever the outcome, before the file is opened,
so a refused parse counts nothing) and BEFORE and AFTER every build (derived: before, an earlier writer, the build
neither called nor counted; after a build that returned, the build itself, counted and not memoised; after a build that
RAISED, the same check on the raising path: when the singletons carry attributes the AssertionError names the build that
just raised as the writer and chains the build's exception as its __cause__, and when they are clean the build's own
exception propagates as it did), so every consumer of the cache inherits it; a consumer's own visible call is the
thread-stop census's setUpClass, before its tree derivation. It NEVER removes what it finds: a repair would hide the
writer. It is order-dependent by nature: red exactly when a writer ran earlier in the same process, a serial run (one
process, every test module in collection order, as CI's cells were until 2026-09-25) or the same xdist worker, and green
for a module run alone. Under CI's two workers since then a writer and the census can land on different workers, so CI
reds on a writer only when a check runs after it in the same worker. Its cost per check
is two small parses (parser_singletons reads the probe text twice and asserts the instances identical across both) and
a vars() per singleton. The read-only pin over the cached nodes (the contract above) walks the singletons too, each once
per tree, and says which of its lines name a shared node.

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
import gc
import os
import threading

_PARSED = {}          # realpath -> ((size, mtime_ns, inode, ctime_ns), text, tree)
_DERIVED = {}         # key -> value
_PARSES = {}          # realpath -> the number of ast.parse calls made for it here
_BUILDS = {}          # key -> the number of build() calls made for it here
_STATS = {"parses": 0, "derivations": 0, "parse_hits": 0, "derived_hits": 0}
_LOCK = threading.RLock()   # across source_and_tree, derived and clear: one miss path at a time; re-entrant for a build's reads
SINGLETON_TYPES = (ast.expr_context, ast.operator, ast.boolop, ast.unaryop, ast.cmpop)   # one instance each per process, on every tree
_SINGLETON_PROBE = ("x = y\ndel z\n"                                                    # every context and operator, once
                    "a + b - c * d / e // f % g ** h << i >> j | k ^ l & m @ n\n"
                    "a and b or c\n"
                    "-a; +a; ~a; not a\n"
                    "a < b <= c > d >= e == f != g is h is not i in j not in k\n")
_PARSE_CHECKED = False      # the singleton pin has run on the first-parse road of this process (source_and_tree)
SINGLETON_REMEDY = ("another module that ran earlier in this process wrote it on a node the parser shares with every tree; grep "
                    "tests/ for %s over AST walks and guard singleton nodes (skip `isinstance(node, (ast.expr_context, ast.operator, "
                    "ast.boolop, ast.unaryop, ast.cmpop))`, or keep the datum in a side table keyed by id(node))")


def _singletons_of(tree):
    out = {}
    for n in ast.walk(tree):
        if isinstance(n, SINGLETON_TYPES):
            out.setdefault(type(n), n)
    return out


def parser_singletons():
    """The parser's shared singleton nodes, one per type (SINGLETON_TYPES), read from PARSES and never constructed
    (ast.Load() builds a fresh, unshared instance, which a probe over it would find clean while the parser's carries a
    writer's chain): two separate parses of one small text that uses every expression context and every operator, and
    the instance of each type must be THE SAME OBJECT in both (`is`), else AssertionError saying the probe is not reading
    a shared instance; only those instances are inspected by the pin."""
    first, second = _singletons_of(ast.parse(_SINGLETON_PROBE)), _singletons_of(ast.parse(_SINGLETON_PROBE))
    differ = sorted(t.__name__ for t in set(first) | set(second) if first.get(t) is not second.get(t))
    if differ:
        raise AssertionError("tests/parse_cache.py's singleton probe is not reading a shared instance: two parses of one text "
                             "gave different %s objects, so this interpreter does not share them and the pin cannot inspect them"
                             % ", ".join(differ))
    return list(first.values())


def singleton_attributes():
    """One (node type name, attribute name, value type name) tuple per attribute a parser singleton carries, the singletons
    in the probe's walk order (parser_singletons) and each one's attributes sorted by name; these node types have no fields
    or attributes of their own, so a clean one has an empty vars(). Empty when the singletons are clean. singleton_lines
    renders the tuples for a message and singleton_message reads the attribute names from them; nothing re-parses a
    rendered line, so an attribute name or a type name holding `, ` or ` (` (reachable through setattr with a computed
    string alone) renders and is named as it is."""
    return [(type(n).__name__, k, type(v).__name__) for n in parser_singletons() for k, v in sorted(vars(n).items())]


def singleton_lines(found):
    """One line per singleton named in `found` (singleton_attributes' tuples), `Load carries _fn (Fn), _parent (Module)`:
    the node's type, then each attribute's name and its value's type, in the tuples' order."""
    by = {}
    for type_name, attr, value_type in found:
        by.setdefault(type_name, []).append("%s (%s)" % (attr, value_type))
    return ["%s carries %s" % (type_name, ", ".join(parts)) for type_name, parts in by.items()]


def singleton_message(where, found):
    """The singleton pin's message for the tuples singleton_attributes() returned: where the check ran, the lines
    (singleton_lines), the remedy with the grep for each distinct attribute name among the tuples, sorted, and the
    order-dependence."""
    names = sorted({attr for _type_name, attr, _value_type in found})
    return ("tests/parse_cache.py's singleton pin, %s: the parser's shared singleton nodes carry attributes:\n  %s\n%s. The pin is "
            "order-dependent by nature: it reds only when the writer ran earlier in the same process (a serial run, or the same "
            "xdist worker), and never for a module run alone; the helper removes nothing it found, so the writer stays visible."
            % (where, "\n  ".join(singleton_lines(found)), SINGLETON_REMEDY % (" and ".join("`.%s =`" % n for n in names),)))


def check_singletons(where):
    """THE SINGLETON PIN: raises AssertionError when any parser singleton carries an attribute, the message naming each (node
    type, attribute name, value type), the site `where` and the remedy; returns None when they are clean. Never repairs:
    deleting what it found would hide the writer. Cheap (two small parses, parser_singletons' identity check, and a vars()
    per singleton), so it runs on the first parse of the process (source_and_tree), before and after every build, the
    build returning or raising (derived), and at a consumer's own visible site (the thread-stop census's setUpClass)."""
    found = singleton_attributes()
    if found:
        raise AssertionError(singleton_message(where, found))


def source_and_tree(path, rel=None):
    """The text and the parsed tree of the file at `path`, parsed once per process while its size, mtime_ns, inode and
    ctime_ns hold (a same-size rewrite within the timestamp granularity is the stated blind spot: the module docstring);
    `rel` is the filename the tree carries (for a SyntaxError's message), else `path`. A file that does not parse raises as
    ast.parse does, and nothing is cached for it. Under the module's lock: two threads asking for one path get one parse
    and the same tree. The first parse of the process runs the singleton pin first (check_singletons; the module
    docstring): a red refuses the read, counts nothing, and is not raised again on this road."""
    global _PARSE_CHECKED
    real = os.path.realpath(path)
    with _LOCK:
        st = os.stat(real)
        key = (st.st_size, st.st_mtime_ns, st.st_ino, st.st_ctime_ns)
        hit = _PARSED.get(real)
        if hit is not None and hit[0] == key:
            _STATS["parse_hits"] += 1
            return hit[1], hit[2]
        if not _PARSE_CHECKED:
            _PARSE_CHECKED = True
            check_singletons("at the first parse of this process (parse_cache.source_and_tree of %s)" % (rel or path))
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
    re-enters the lock from its own thread. The singleton pin runs BEFORE the build (an earlier writer: the build is
    neither called nor counted) and AFTER it, whether the build returned or raised (the build itself wrote on a singleton:
    counted, memoised as nothing, so the next call builds again). On the raising path the build's exception is not masked:
    the singletons are read; when any carries an attribute an AssertionError naming the build that just raised as the
    writer is raised `from` the build's exception (its __cause__), else the build's exception is re-raised as it was; the
    module docstring. THE RETENTION SHAPE (the module docstring's paragraph of that name): when the collector is enabled
    on entry it is disabled for the build and re-enabled in a finally, on both roads, so no automatic collection walks the
    trees while the build allocates them; a collector the caller had disabled is never touched. The exit state in one
    rule: a collector found on is handed back on whatever the build did to it; a collector found off is left as the build
    left it (never enabled here). After a build that returned and passed the after-check, and after the memo, gc.freeze()
    runs once, before this call returns: every object TRACKED then, the trees this build read among them and any cycle
    the build dropped without breaking it (the rule for a build, in the module docstring), leaves the collector's
    generations for the rest of the process. A build that raised, or that the after-check refused, freezes nothing; a hit
    freezes nothing; nothing here unfreezes."""
    with _LOCK:
        if key in _DERIVED:
            _STATS["derived_hits"] += 1
            return _DERIVED[key]
        check_singletons("before the build of %r (parse_cache.derived): an earlier writer" % (key,))
        _BUILDS[key] = _BUILDS.get(key, 0) + 1
        _STATS["derivations"] += 1
        collecting = False                   # the caller's collector state, read INSIDE the try: an interrupt between the disable and the finally cannot leave it off
        try:
            collecting = gc.isenabled()      # held off for the build when on, never touched when off
            if collecting:
                gc.disable()
            try:
                value = build()
            except BaseException as exc:
                found = singleton_attributes()
                if found:
                    where = "after the build of %r raised %s (parse_cache.derived): the build that just raised wrote them, or a thread beside it"
                    raise AssertionError(singleton_message(where % (key, type(exc).__name__), found)) from exc
                raise
            check_singletons("after the build of %r (parse_cache.derived): the build itself wrote them, or a thread beside it" % (key,))
            _DERIVED[key] = value
            gc.freeze()                      # THE RETENTION SHAPE: what is tracked now leaves the collector's generations for good, before this call returns
        finally:
            if collecting:
                gc.enable()                  # the state found, on the returning road and on the raising road
        return value


def clear(*keys):
    """Forget every cached parse and derivation (no arguments), or the derived keys given and any parsed path among them
    (by realpath). Forgetting drops the cache's references only: a tree a frozen cycle still holds (a derivation's value that
    references its trees through a cycle, as the census's _Tree does through its modules and their units) stays alive for the
    process, since nothing here unfreezes (the retention shape in the module docstring). The counters are left as they are:
    they count what happened in the process. Under the module's lock."""
    with _LOCK:
        if not keys:
            _PARSED.clear()
            _DERIVED.clear()
            return
        for k in keys:
            _DERIVED.pop(k, None)
            if isinstance(k, str):
                _PARSED.pop(os.path.realpath(k), None)


def cached_trees():
    """[(realpath, tree)] for every file parsed and held here, a snapshot under the module's lock: what a consumer's pin over
    the cached nodes walks (the contract's third sentence in the module docstring)."""
    with _LOCK:
        return [(real, hit[2]) for real, hit in _PARSED.items()]


def stats():
    """A copy of the counters: parses, derivations, parse_hits, derived_hits."""
    return dict(_STATS)


def parses_of(path):
    """The number of times the file at `path` was parsed here in this process."""
    return _PARSES.get(os.path.realpath(path), 0)


def builds_of(key):
    """The number of times build() ran for `key` here in this process."""
    return _BUILDS.get(key, 0)
