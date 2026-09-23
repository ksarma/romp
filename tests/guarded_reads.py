"""Seams for tests that fault, count or interpose on reads of files under the state root, at the Reader class.

Since round 4 of the state-root review every read of a path under the state root goes through kernel/state_root_mode.py's
Reader (tests/test_state_root_readers.py pins the population). Since round 4c each reader performs the read through the
same pathlib or os primitive the site used before round 4 (Path.read_text, Path.read_bytes, builtins.open, os.open,
gzip.open, Path.stat, ...; the module's PRIMITIVE RULE), so a fixture that replaces Path.read_text, Path.read_bytes,
Path.stat or builtins.open meets the read as it always did: those seams are the suite's contract, and the twenty-two test
modules that hold it are unchanged. These helpers are a second seam, one level up: they patch the shared Reader CLASS
(every reader in the process: the kernel's _gr, the judge's, the event model's, the bus's, the backends' per-call ones),
so one fixture reaches a read whichever reader and whichever primitive it takes. Because the five opening methods
(os_open, open, read_text, read_bytes, gzip_open) each call their own primitive and none funnels through another, a hook
on "every open" patches all five (OPENERS); `method=` names one road. The shared module is looked up at call time under
its fixed name, so a test module needs no load of its own."""
import contextlib
import os
import sys
from unittest import mock

OPENERS = ("os_open", "open", "read_text", "read_bytes", "gzip_open")   # every Reader method that opens a file's bytes


def reader_class():
    """The shared module's Reader class (kernel/state_root_mode.py, loaded under romp_state_root_mode by the judge)."""
    return sys.modules["romp_state_root_mode"].Reader


class _Patch:
    """One or more started mock patches whose stop() is idempotent (a fixture may heal mid-test and again at cleanup)."""

    def __init__(self, patchers):
        self._ps = list(patchers)
        for p in self._ps:
            p.start()
        self.stopped = False

    def stop(self):
        if not self.stopped:
            self.stopped = True
            for p in reversed(self._ps):
                p.stop()


def _same(path, target):
    return os.fspath(path) == os.fspath(target)


def _wrap_openers(before, methods=OPENERS):
    """Patchers (not started) for each named Reader method: before(path) runs first (it may raise), then the real method."""
    cls = reader_class()
    out = []
    for name in methods:
        real = getattr(cls, name)

        def wrapped(self, path, *a, _real=real, **k):
            before(path)
            return _real(self, path, *a, **k)
        out.append(mock.patch.object(cls, name, wrapped))
    return out


def start_fault(target, make_exc):
    """Every Reader open of `target` (any of OPENERS) raises make_exc() from here on; other reads run. Returns the patch
    (stop() heals)."""
    def before(path):
        if _same(path, target):
            raise make_exc()
    return _Patch(_wrap_openers(before))


@contextlib.contextmanager
def fault(target, make_exc):
    """start_fault for the length of a block."""
    p = start_fault(target, make_exc)
    try:
        yield
    finally:
        p.stop()


def start_count(match, into=None, method=None):
    """Count every Reader open (all of OPENERS when `method` is None; one road when it names a method, read_text or
    read_bytes for one decode road) whose path satisfies match(path as str): the paths land in `into` (a list, made when
    None). Returns (the list, the patch)."""
    seen = [] if into is None else into

    def before(path):
        if match(os.fspath(path)):
            seen.append(os.fspath(path))
    return seen, _Patch(_wrap_openers(before, OPENERS if method is None else (method,)))


@contextlib.contextmanager
def count(match, method=None):
    """start_count for the length of a block; yields the list of matching paths opened (or read through `method`)."""
    seen, p = start_count(match, method=method)
    try:
        yield seen
    finally:
        p.stop()


@contextlib.contextmanager
def before_open(target, fn):
    """Run fn(path) right before every Reader open of `target` (a writer that lands between the reader's stat and its open;
    a gate another thread holds)."""
    def before(path):
        if _same(path, target):
            fn(path)
    p = _Patch(_wrap_openers(before))
    try:
        yield
    finally:
        p.stop()


@contextlib.contextmanager
def wrap_open(match, wrap):
    """Hand every Reader.open of a path satisfying match(path as str) to wrap(file, mode), which returns the file object
    the caller reads (a file that parks in read(), a file that runs a writer after its lines), for the length of a block.
    The open road only: read_text and read_bytes return bytes, not a file (count or fault them through the seams above)."""
    cls = reader_class()
    real = cls.open

    def opened(self, path, mode="r", *a, **k):
        f = real(self, path, mode, *a, **k)
        return wrap(f, mode) if match(os.fspath(path)) else f
    with mock.patch.object(cls, "open", opened):
        yield


def start_spy(fn):
    """Call fn(path as str) on every Reader open (any of OPENERS), then run the open; returns the patch (stop() ends it)."""
    return _Patch(_wrap_openers(lambda path: fn(os.fspath(path))))


@contextlib.contextmanager
def stat_fault(target, make_exc):
    """Every Reader.stat of `target` raises make_exc() for the length of a block (the stat-then-read shape's stat arm)."""
    cls = reader_class()
    real = cls.stat

    def stat(self, path):
        if _same(path, target):
            raise make_exc()
        return real(self, path)
    with mock.patch.object(cls, "stat", stat):
        yield
