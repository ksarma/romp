#!/usr/bin/env python3
"""The census of every syscall on a path under `hosts/`, derived by ORIGIN over the three modules that mint one
(kernel/host_transport.py, kernel/session_host.py, kernel/sdk_backend.py): a data-flow walk over their sources that
seeds on the literal segment, follows the value through the binding forms it knows, and classes each syscall the value
reaches as by-descriptor, by-path, mixed or exec-arg. Round 7 of fork PR #814's review (2026-09-20) and its addenda.

THE JOB SINCE THE ROAD WAS CLOSED (the second and third addenda, 2026-09-20, on the reviewer's ruling that the kernel's
residual reads under hosts/ take descriptors the way the spawn road does). The pin no longer tracks taint through the
data model to publish a road and a provenance for every member; it holds that a CONSTRUCT DOES NOT EXIST: no code in
the three files makes a by-path syscall on a hosts path except the sites `RESIDUAL` lists, each with its role and its
reason. The roles (the fourth addendum, 2026-09-20, split the second and third addenda's UNCONVERTED into the first
two, on the reviewer's ruling of 19:12Z): PERMANENT, the connect to the published socket (HostTransport.connect): a
Unix socket is connected by the path in its address and connect(2) has no dir_fd form, so the site stays by path for
as long as the transport is a Unix socket, closed as an open item; FOLLOW-UP, a site of a queued change, EMPTY since the
fork PR that follows #814 (2026-09-21) landed the one item the role held, "the journal reads descend by descriptor"
(the general notes' small-asks file): its five sites, the two journal globs in the kernel and the host module's
read_journal_dir with its glob and the two reads that took the paths it yielded, are gone, the reader rewritten in
kernel/host_transport.py over the held <sid> descriptor (journal_segments, read_journal_dir), and the pin now holds the
role empty and refuses a by-path read under hosts/ that would refill it; HELPER, the two directory helpers'
path-taking syscalls before the spawn road's descent (condition 1's window, stated in write_spawn_spec); GUARD, the
descent's own open of hosts/ by path with O_NOFOLLOW off the state root and the lstat that words its refusal, and host
side the lstat of hosts/ before the bind; UNREACHABLE, a by-path arm a guard makes unreachable (none at this head:
the two dir_fd=None arms of the spawn road's host.log readers, held so by the forwarding pin through the sixth addendum,
went with the readers' conversion at the seventh, 2026-09-20, when they took the held HostDirs; the role stays in the
vocabulary);
HANDOFF, the spec path in the host's argv; HOST, the host process's own road under its constructor's and prelude's
guards, and its open of the spec before them (the host-side item the queue keeps). A by-path terminal outside the list
reds; a listed one that is gone or changed class reds; the converted reads are held by-descriptor (`CONVERTED`,
which since the fourth addendum includes the owner check's fstat of the descriptor read_host_file opened); the
permanent set is asserted to be exactly the connect; and the follow-up set is asserted to be exactly the item's five
sites while the item is open (the assertion flips to empty when it lands). What a silent miss costs now is a
regression guard and nothing more: the road is closed by the code, pinned by execution in
tests/test_host_transport.py (BackendHostRules, ReadDescent) and tests/test_session_host.py (PreludeRefusalRead), and
this census guards that a NEW by-path read does not slip back in; a reader written in a form the walk drops would be
missed by the guard, not admitted by the code.

THE METHOD, in the order it runs.
  SEED. Every expression in the three files where the literal segment enters a path: a str or bytes constant equal to
  `hosts` in any position but a dict key, a subscript, a comparison or a membership test (kind `path`: `root / "hosts"`,
  `os.path.join(root, "hosts")`, `Path(root, "hosts", sid)`, a tuple splatted into either, a `%` operand), and any
  constant CONTAINING `hosts/` or `/hosts` (kind `text`: an f-string part, a `%` or `+` operand, and a message string,
  which the walk tells from a path only at its use, below). One seed is declared rather than read: the `spec_path`
  parameter of SessionHost.__init__ (kernel/session_host.py), the path under hosts/ the kernel hands the host in argv;
  the census does not follow a value across exec (the argv list ends at subprocess.Popen on the kernel side, an
  `exec-arg` terminal), so the host's entry re-seeds it by declaration. The seed scan also runs over every product module
  (kernel/, bin/, cli/, postal/), and a pin holds that no module outside the three builds such a path.
  GROW, to a fixpoint, through every form Python binds or reads a name or an attribute by. The taint (a set of origin
  tags, each the seed's file, line and text) flows through assignment, annotated and augmented assignment to a name, a
  tuple or list target (element-wise when the value's shape is known, else the union), a starred target, an attribute
  target on `self`, on a typed receiver, on a class or on a receiver the walk cannot type (stored by attribute NAME and
  read back by every read of that name, the safe direction), a subscript target on any of those, a walrus, the
  with-target, the for-target, a comprehension's target, a match statement's capture names, a `global` or `nonlocal`
  name (bound in the scope it names), a class-body assignment (readable as `self.<name>`, `<Class>.<name>`,
  `type(self).<name>`, `self.__class__.<name>` and, in the class body, by the bare name; a base class's through the
  subclass), a parameter's default or keyword default (evaluated in the defining scope), a property's return at every
  read of the property and a setter's parameter at every store to it, an exception bound by `except ... as e` (its
  `filename` and `filename2`, the path attributes an OSError carries, read as the path of a syscall the try body or a
  callee of it made), into containers (a list, tuple, set or dict literal holding it; `.append`, `.extend`, `.add`,
  `.update`, `.insert`, `.appendleft`, `.extendleft`, `.put`, `.put_nowait`, `.setdefault` on a name or an attribute,
  `setattr` with a constant name) and out of them (a subscript, `.get`, `.pop`, `.setdefault`, `getattr`, a splat, a
  dynamic `getattr` reading every attribute of the receiver's class), through the pure conversions (`str`, `repr`,
  `bytes`, `bytearray`, `format`, `os.fspath`, `os.fsencode`, `os.fsdecode`, `Path`, `PurePath`, `os.path.join`,
  `dirname`, `abspath`, `normpath`, `min`, `max`, `json.dumps`, `json.loads`, the `re` functions that return text or a
  match, `.encode`, `.decode`, `.format`, `.join`, `.strip`, `.split`, `.partition`, `.group`, `.replace`, `/`, `+`, `%`,
  an f-string, `.parent`, `.parents`, `.parts`, `.with_name`, `.with_suffix`, `.joinpath`, `.relative_to`, `.absolute`,
  a conditional expression, an `await`, `asyncio.wait_for`, `asyncio.run`), into a callee's parameters from every call
  site (positional, keyword, splatted or double-splatted, context-insensitively: a parameter tainted at any site is
  tainted everywhere, the safe direction; a classmethod's `cls` and a bound method's `self` are never bound to an
  argument) and out of a callee's return or yield to every call site, with the call itself added as an origin tag (so a
  terminal names the road that minted its path, not only the helper's body), into a nested function or a lambda (indexed
  as a function of its own that reads its enclosing scopes' names, called where its name is called, bound where its
  value is bound: an assignment, a default, an attribute, an argument to a function of the files), through a parameter
  that is called (`log(...)`) to the callables its call sites bind, and out of a read that yields paths (`glob`, `rglob`,
  `iterdir`, `scandir` on a path). A leaf-only read (`.name`, `.stem`, `.suffix`) drops the taint: a bare file name
  cannot reach outside the directory it is used in. A second kind, `fd`, seeds at every `os.open` whose path is tainted
  or whose dir_fd is, and flows the same way (HostDirs' two descriptors reach every `dir_fd=dirs.dir` through the
  attribute store in its __init__); the return of a terminal read (the bytes of a file, a stat result) is not tainted.
  CLASSIFY every TERMINAL, a call that takes the value at a position where the operating system reads it: `open`, the
  path-taking os and os.path functions, the Path methods, shutil, `asyncio.open_unix_connection`, `start_unix_server`,
  the subprocess constructors; a `**` splat into one is taken as its path position. `by-descriptor`: a `dir_fd` keyword,
  or the first argument of fstat, fchmod, fdopen, scandir or write, carries `fd` taint, and a subprocess's stdin, stdout
  or stderr keyword too. `by-path`: a path position carries `path` or `text` taint and no descriptor does. `exec-arg`: a
  subprocess's argv carries the path. `mixed`: one call reached by a path at one site and by a name under a descriptor
  at another. And `escape`: a `path`-tainted value at one of the SIX forms the escape rule covers, reported by file and
  line with the form named (a call the walk cannot resolve to a function of the three files, a pure conversion, a
  container operation or a data sink; a method the walk does not know called on a path-tainted receiver; a callable
  handed as a VALUE into a call outside the files beside a path-tainted argument, `map(open, paths)`; a store with a
  name the walk cannot read, `setattr(o, name, p)`; a decorator the walk does not know on a function that holds or
  returns a path; a dynamic attribute read on a receiver the walk cannot type while a path is stored by attribute name
  on such a receiver). A `text`-tainted value at such a form is a message (that is what tells the two kinds apart at
  the use) and is not reported.
  PIN. `RESIDUAL` below: every by-path, mixed and exec-arg terminal at this head, keyed by file, enclosing function,
  the operation, the argument's text and its ordinal in that function (never a line number, which main's insertions
  move), with its class, its role and its reason. `CONVERTED`: the read roads' terminals since the second addendum,
  held by-descriptor. Run the module directly to print the derived table with line numbers at the head it reads
  (`--residual` prints the pinned view for pasting).

WHAT THE ESCAPE RULE COVERS, AND NO MORE. The walk prints an escape at the six forms named under CLASSIFY and at no
other; over this tree that list is empty by pin (`test_no_use_escapes_the_walk`). A value the walk drops at any OTHER
form is a silence, not an escape. The addendum's sentence that what the census cannot see is what it prints was false
at the commit that made it (HISTORY, below), and this module makes no such promise: the follow rules above are what the
walk follows, the six forms are what it prints, and everything else it does not follow it does not report. Two kinds
lie outside the census by construction as well: a path that reaches a syscall as an argument STRING of a subprocess is
followed to the exec boundary and no further (the `exec-arg` terminal; the host's side re-seeds its `spec_path` by
declaration), and a syscall made inside a C extension or by code outside the three files given a value this census did
class (the wide pin holds that no other product module builds such a path itself). The walk is flow-insensitive within
a function, so it reports a use on a road a guard makes unreachable as it reports a live one (the two dir_fd=None arms
the spawn road's host.log readers kept through the sixth addendum were that shape, listed UNREACHABLE and held so by the
forwarding pin; since the seventh addendum no reader has one, and the pin,
`test_no_reader_has_a_by_path_fallback_arm_and_the_forwarding_analysis_would_report_one`, holds that over this tree and
shows the analysis live on a scratch copy with one planted); the
seed rule is a definition, so a hosts path that never passes through the literal segment in these files is never
tainted; and a leaf name reassembled onto an untainted base after `.name` dropped the taint is a drop by rule.

HISTORY. Round 7 replaced a grep over spellings, which the round-6 verifiers' eleven planted readers had all evaded,
with this walk. The round-7 addendum widened the follow rules by BINDING FORM after that round's verifiers planted ten
shapes and six were missed in silence, and pinned twenty-seven plants found or printed. The second addendum's two
verifiers planted twenty-four forms at the addendum's commit: three were printed as escapes and twenty-one were silent
(a path passed by keyword to a known terminal; a called parameter's return; an attribute read through an untyped
receiver's typed element; `getattr(self, "name")(...)` as a call target; a dict literal's key; a store through
`self.__dict__[...]`; text-kind taint at an unfollowed form; and the data model's protocols: `__getattr__`,
`__getitem__`, `__call__`, `__enter__`, `__get__`, `__fspath__`, `property(f)` in a class body, a constructor without
`__init__`, an exception class's `__init__`, a tainted `cwd=` or `env=` at Popen, a subscript store into a call result).
Their survey of the real tree found that none of the twenty-one forms carries a hosts path in the three files at that
head, which is the evidence that the published list was right there and that closing the road was a bounded change.
The one engine change since (the third addendum): the exception rule, which read a constructor's NAME against a regex,
also reads a class's bases, since HostDirAbsent, a subclass of HostDirRefused, was printed as an escape at the second
addendum's commit. The fourth addendum changed no rule and met one: a hosts path stored on an exception's attribute
named `path` (the first cut of HostFileForeign) is a store on a receiver the walk cannot type, and every `.path` read on
such a receiver in the three files went tainted with it (65 unlisted terminals, 143 escapes at that cut); the class
carries the directory in its text instead, and this is recorded so the next reader of a `path` attribute knows why.
The seventh addendum (2026-09-20) met a second engine defect and fixed it: a scope was re-walked after round 0 only
when something TAINTED could move it (a seed, a tainted local, a call whose value is tainted, a tainted attribute), so a
HostDirs handed down a chain of functions that carry no taint of their own (the spawn road's _host_transport_for to
_refused_launch_log to _file_refused_launch_context to host_log_rows, all four taking the holder and none a path or a
descriptor) was typed only as far as round 0's walk order happened to reach, and that order is not source order; the
views then bound the rest lazily (tags() of a call binds the callee's parameters), so members() answered differently on
its second call and the plant harness, which diffs a base census that had been viewed against a fresh planted one, read
the view's own drift as a change the plants made (two plant cases red at this addendum's first cut). A name typed as a
holder now makes its scope live like a tainted local, the fixpoint types the whole chain whatever the order, and a pin
holds the view idempotent and the chain's last reader typed.

THE PARSER'S SHARED NODES (2026-09-22, read back by CI's diagnostic run 35740276523 on PR 891's branch). The walk marks
every node of its own trees with `_fn` (the scope that owns it) and `_parent` (its parent node). The parser hands out ONE
instance of each expression context (Load, Store, Del) and of each operator (the operator, boolop, unaryop and cmpop
subclasses) per process, shared by every tree it parses, so a mark written on one of them rode on every tree any later
module in the same process parsed: in CI's serial cell this module runs before the thread-stop census, whose
copy.deepcopy of a two-node hand (a Name and its Load) followed the shared Load's `_parent` into this census's whole
graph, a RecursionError inside copy.py on 3.10 and 3.11 and on 3.12 a completed copy of the graph costing minutes. The
three marks (the third, `_lfn`, names a Lambda's scope on the Lambda node, which the parser never shares, and is guarded
all the same) skip the shared nodes (SHARED_NODE_TYPES), and a pin holds the parser's shared nodes clean after the census
(read from parses and held to one instance across two of them; a constructed ast.Load() is fresh and unshared) and shows
each of the three old writes red in turn on the parsed instances, the restore registered before the first write. No
verdict moves: no rule reads a context or operator node by its mark.
"""
import ast
import glob
import os
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FILES = ("kernel/host_transport.py", "kernel/session_host.py", "kernel/sdk_backend.py")
SCAN_GLOBS = ("kernel/*.py", "bin/*", "cli/*.py", "postal/*.py")
DECLARED_SEEDS = (("kernel/session_host.py", "SessionHost.__init__", "spec_path",
                   "spec_path: the path under hosts/ the kernel hands the host in argv (declared: the exec boundary)"),)
_HOSTS_RE = re.compile(r"(^|/)hosts/|/hosts($|/)")
SHARED_NODE_TYPES = (ast.expr_context, ast.operator, ast.boolop, ast.unaryop, ast.cmpop)   # one instance each per process, on every tree
_SHARED_PROBE = "x = y\ndel z\na + b\na and b\n-a\na < b\n"    # a parse holding one of each family of them

PATH_FUNCS = {"open": (0,), "os.open": (0,), "os.stat": (0,), "os.lstat": (0,), "os.unlink": (0,), "os.remove": (0,),
              "os.rmdir": (0,), "os.mkdir": (0,), "os.makedirs": (0,), "os.chmod": (0,), "os.lchmod": (0,), "os.chown": (0,),
              "os.rename": (0, 1), "os.replace": (0, 1), "os.symlink": (1,), "os.link": (0, 1), "os.readlink": (0,),
              "os.access": (0,), "os.listdir": (0,), "os.scandir": (0,), "os.utime": (0,), "os.truncate": (0,),
              "os.mkfifo": (0,), "os.walk": (0,), "os.chdir": (0,), "os.path.exists": (0,), "os.path.lexists": (0,),
              "os.path.isdir": (0,), "os.path.isfile": (0,), "os.path.islink": (0,), "os.path.getsize": (0,),
              "os.path.getmtime": (0,), "os.path.realpath": (0,), "os.path.samefile": (0, 1), "os.path.ismount": (0,),
              "shutil.rmtree": (0,), "shutil.copy": (0, 1), "shutil.copyfile": (0, 1), "shutil.copy2": (0, 1),
              "shutil.move": (0, 1), "shutil.copytree": (0, 1), "asyncio.open_unix_connection": (0, "path"),
              "asyncio.start_unix_server": (1, "path"), "tempfile.mkdtemp": ("dir",), "tempfile.mkstemp": ("dir",)}
FD_FUNCS = {"os.fstat": (0,), "os.fchmod": (0,), "os.fchown": (0,), "os.fdopen": (0,), "os.scandir": (0,), "os.write": (0,),
            "os.read": (0,), "os.ftruncate": (0,), "os.fsync": (0,)}
EXEC_FUNCS = {"subprocess.Popen": (0,), "subprocess.run": (0,), "subprocess.call": (0,), "subprocess.check_call": (0,),
              "subprocess.check_output": (0,), "os.execv": (0, 1), "os.execve": (0, 1)}
EXEC_FD_KWS = ("stdin", "stdout", "stderr")
PATH_METHODS = {"exists", "is_dir", "is_file", "is_symlink", "is_fifo", "is_socket", "stat", "lstat", "chmod", "lchmod",
                "mkdir", "rmdir", "unlink", "touch", "open", "read_text", "read_bytes", "write_text", "write_bytes",
                "glob", "rglob", "iterdir", "rename", "replace", "symlink_to", "hardlink_to", "resolve", "samefile",
                "readlink", "owner", "group", "connect", "bind"}
YIELDS_PATHS = {"glob", "rglob", "iterdir", "os.scandir", "os.listdir"}
# THE FOUR LISTS BELOW are decided member by member by ONE question (the round-7 addendum, after the verifiers found
# `setdefault` among the pure methods and `re.sub` among the sinks): can a hosts path flow THROUGH this call, either OUT
# of it in its return (then it is PURE: the return carries the receiver's and the arguments' tags) or INTO its receiver to
# be read back later (then it is a STORE: the arguments' tags land on the receiver)? A member is a SINK only when the
# answer is no on both counts: its return cannot carry the value (a bool, an int, a hash, a type, None) and it keeps no
# argument (it compares, counts, closes, logs, writes out, or leaves the process). A call in none of the lists with a
# path-tainted argument or receiver is printed as an escape when the walk cannot resolve it (the escape rule's first two
# forms); a called PARAMETER is a sink by declaration and its return is dropped, one of the twenty-one silent forms the
# second addendum's verifiers found (the module docstring's HISTORY). Moved by that question in the addendum: `setdefault`
# from PURE to STORE_RETURN (it stores its default AND returns it); `put` and `put_nowait` from SINK to STORE (a queue is
# read back by `.get`); `split`, `rsplit` and `splitlines` from SINK to PURE (they return pieces of the receiver, from
# which a path is reassembled); `re.sub`, `re.match` and `re.search` from SINK to PURE beside the other `re` functions
# that return text or a match; `json.dumps` and `json.loads` from SINK to PURE (`json.loads(json.dumps(p))` is `p`);
# `min` and `max` from SINK to PURE (they return one of their arguments); `asyncio.wait_for` and `asyncio.run` from SINK
# to PURE (they return the awaited value); `getattr` and `setattr` from SINK to their own rules in the walk (a read or a
# store by attribute name, the name a constant or not); `vars` from SINK to a dynamic read of the receiver's attributes.
# A compiled pattern's `match`, `search`, `fullmatch`, `findall`, `finditer`, `sub` and `subn` are PURE (a Match or a
# string carries the text searched), which puts Path.match, a bool, on the safe side too.
PURE_FUNCS = {"str", "repr", "bytes", "bytearray", "memoryview", "format", "os.fspath", "os.fsencode", "os.fsdecode",
              "Path", "PurePath", "PurePosixPath", "pathlib.Path", "pathlib.PurePath", "os.path.join", "os.path.dirname",
              "os.path.abspath", "os.path.normpath", "os.path.expanduser", "os.path.basename", "os.path.split",
              "os.path.splitext", "os.path.relpath", "os.path.commonpath", "os.path.normcase", "list", "tuple", "set",
              "frozenset", "sorted", "reversed", "enumerate", "zip", "dict", "iter", "next", "filter", "map", "min", "max",
              "json.dumps", "json.loads", "re.sub", "re.subn", "re.split", "re.findall", "re.finditer", "re.match",
              "re.search", "re.fullmatch", "re.escape", "re.compile", "asyncio.wait_for", "asyncio.run",
              "asyncio.ensure_future", "asyncio.shield", "copy.copy", "copy.deepcopy", "functools.reduce", "itertools.chain"}
PURE_METHODS = {"encode", "decode", "format", "join", "strip", "rstrip", "lstrip", "lower", "upper", "replace",
                "split", "rsplit", "splitlines", "partition", "rpartition", "removeprefix", "removesuffix", "casefold",
                "title", "capitalize", "swapcase", "zfill", "ljust", "rjust", "center", "expandtabs", "translate",
                "group", "groups", "groupdict", "expand", "search", "match", "fullmatch", "findall", "finditer", "sub",
                "subn", "with_name", "with_suffix", "with_stem", "joinpath",
                "relative_to", "expanduser", "absolute", "as_posix", "as_uri", "copy", "items", "values", "keys", "get",
                "pop", "popleft", "popitem", "__getitem__", "union", "intersection", "difference", "symmetric_difference"}
PURE_ATTRS = {"parent", "parents", "parts", "anchor", "drive", "root"}
DROP_ATTRS = {"name", "stem", "suffix", "suffixes"}
STORE_METHODS = {"append", "extend", "add", "update", "insert", "appendleft", "extendleft", "put", "put_nowait"}
STORE_RETURN_METHODS = {"setdefault"}
SINK_FUNCS = {"print", "len", "int", "float", "bool", "isinstance", "issubclass", "any", "all", "hash", "id", "type",
              "hasattr", "delattr", "callable", "os.strerror", "time.time", "time.monotonic", "os.geteuid", "os.getpid",
              "stat.S_IMODE", "stat.S_ISDIR", "stat.S_ISLNK", "stat.S_ISREG", "stat.S_ISFIFO", "stat.S_ISSOCK", "sys.exit",
              "warnings.warn", "os.close", "os.umask", "asyncio.sleep", "asyncio.Queue", "asyncio.Event", "asyncio.Lock",
              "super", "range", "abs", "round", "divmod", "chr", "ord", "hex", "oct", "traceback.format_exc",
              "traceback.extract_tb", "traceback.format_exception", "logging.getLogger"}
SINK_METHODS = {"write", "writelines", "log", "debug", "info", "warning", "error", "exception", "critical", "seek",
                "read", "readline", "readlines", "close", "flush", "send", "startswith", "endswith", "count", "find",
                "rfind", "index", "rindex", "isdigit", "isalnum", "isalpha", "isspace", "discard", "remove", "clear",
                "poll", "wait", "terminate", "kill", "drain", "feed", "dump", "is_absolute", "is_relative_to",
                "fileno", "isatty", "truncate", "cancel", "done", "set", "is_set", "release", "acquire", "notify",
                "notify_all", "sort", "reverse", "issubset", "issuperset", "isdisjoint", "__contains__"}
LOG_PARAMS = {"log", "logger", "on_fault", "on_stderr", "on_exit", "on_hello", "on_ack"}
KEY_METHODS = {"get", "pop", "setdefault", "__getitem__", "__contains__", "has_key"}   # a constant first argument is a key
# Decorators the walk knows the binding of. `property` and `cached_property` make a read of the name the method's return
# and (with `.setter`) a store to it the setter's parameter; `staticmethod` and `classmethod` change how the first
# parameter binds; the two contextmanagers make `with f() as x` bind x to the yield; `wraps`, the caches, `abstractmethod`
# and `overload` leave the callable's parameters and return as written. Any other decorator on a function that holds or
# returns a path is an escape: the name is rebound to whatever the decorator returned.
KNOWN_DECORATORS = {"property", "functools.cached_property", "cached_property", "staticmethod", "classmethod",
                    "contextlib.contextmanager", "contextlib.asynccontextmanager", "contextmanager", "asynccontextmanager",
                    "functools.wraps", "wraps", "functools.lru_cache", "lru_cache", "functools.cache", "cache",
                    "abc.abstractmethod", "abstractmethod", "typing.overload", "overload"}
PROPERTY_DECORATORS = {"property", "functools.cached_property", "cached_property"}


class Tag(tuple):
    """An origin: (kind, file, line, text). Two tags are the same origin when their (kind, file, qual, text, ordinal)
    agree; the line is for the printed list. Kinds: `path`, `text`, `fd`, and `exc` (a path carried by an exception the
    try body raised, readable through its `filename`; never counted at a terminal or an escape until read so)."""
    __slots__ = ()

    def __new__(cls, kind, file, line, text, qual, ordinal):
        return tuple.__new__(cls, (kind, file, line, text, qual, ordinal))

    kind = property(lambda s: s[0])
    file = property(lambda s: s[1])
    line = property(lambda s: s[2])
    text = property(lambda s: s[3])
    qual = property(lambda s: s[4])
    ordinal = property(lambda s: s[5])

    def key(self):
        return (self.kind, self.file, self.qual, self.text[:72], self.ordinal)

    def as_kind(self, kind):
        return Tag(kind, self.file, self.line, self.text, self.qual, self.ordinal)


def _pseudo_def(name, body, lineno):
    return ast.FunctionDef(name=name, args=ast.arguments(posonlyargs=[], args=[], vararg=None, kwonlyargs=[], kw_defaults=[],
                                                          kwarg=None, defaults=[]),
                           body=body or [ast.Pass()], decorator_list=[], returns=None, lineno=lineno, col_offset=0,
                           end_lineno=lineno, end_col_offset=0)


def _dotted(e):
    if isinstance(e, ast.Name):
        return e.id
    if isinstance(e, ast.Attribute):
        base = _dotted(e.value)
        return base + "." + e.attr if base else None
    if isinstance(e, ast.Call):
        return _dotted(e.func)
    return None


class Fn:
    """A scope the walk binds names in: a module-level function or method, a nested function, a lambda, a class body or
    the module level (the last two as pseudo-functions). `outer` is the enclosing scope (a method's is its class body,
    a module function's the module level, a nested function's or lambda's the function it is written in); a function
    body reads its enclosing FUNCTION scopes and the module level, never a class body, which only its own statements,
    its methods' defaults and its decorators read (Python's rule)."""

    def __init__(self, file, qual, node, cls, outer=None, is_class_body=False):
        self.file, self.qual, self.node, self.cls, self.outer, self.is_class_body = file, qual, node, cls, outer, is_class_body
        a = node.args
        self.params = [p.arg for p in a.posonlyargs + a.args] + ([a.vararg.arg] if a.vararg else []) + \
                      [p.arg for p in a.kwonlyargs] + ([a.kwarg.arg] if a.kwarg else [])
        self.pos = [p.arg for p in a.posonlyargs + a.args]
        self.defaults = {}
        for p, d in zip(reversed(a.posonlyargs + a.args), reversed(a.defaults)):
            self.defaults[p.arg] = d
        for p, d in zip(a.kwonlyargs, a.kw_defaults):
            if d is not None:
                self.defaults[p.arg] = d
        self.decorators = [_dotted(d) or "?" for d in getattr(node, "decorator_list", [])]
        self.is_lambda = isinstance(node, ast.Lambda)
        self.globals_, self.nonlocals = set(), set()
        self.bound = set(self.params)
        self.nodes, self.chain, self.exc_used = None, None, set()
        self.identity = self._identity_param()
        self.tokens = self._tokens()

    def own_nodes(self):
        """The nodes of this scope and no nested one (listed once `_fn` is marked, by finish())."""
        if self.nodes is not None:
            return self.nodes
        return [n for n in ast.walk(self.node) if getattr(n, "_fn", None) is self]

    def finish(self):
        """After `_fn` marking: the names this scope binds (a store to a name that is not one of these is a store into
        an enclosing scope's object, `_CACHE[k] = v` on a module-level dict), and its global/nonlocal declarations."""
        self.nodes = list(self.own_nodes())
        self.chain = list(self.scopes())
        handlers = set()
        for n in self.nodes:
            if isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)):
                self.bound.add(n.id)
            elif isinstance(n, ast.Global):
                self.globals_ |= set(n.names)
            elif isinstance(n, ast.Nonlocal):
                self.nonlocals |= set(n.names)
            elif isinstance(n, ast.ExceptHandler) and n.name:
                self.bound.add(n.name)
                handlers.add(n.name)
            elif isinstance(n, (ast.MatchAs, ast.MatchStar)) and n.name:
                self.bound.add(n.name)
            elif isinstance(n, ast.MatchMapping) and n.rest:
                self.bound.add(n.rest)
        self.bound -= self.globals_ | self.nonlocals
        # an exception's path can only be read through `<name>.filename`, or reach one through a call the name is
        # handed to: a handler whose name is used neither way binds nothing the walk needs
        for n in self.nodes:
            if isinstance(n, ast.Attribute) and n.attr in ("filename", "filename2") and isinstance(n.value, ast.Name) \
                    and n.value.id in handlers:
                self.exc_used.add(n.value.id)
            elif isinstance(n, ast.Call):
                for a in list(n.args) + [k.value for k in n.keywords]:
                    if isinstance(a, ast.Name) and a.id in handlers:
                        self.exc_used.add(a.id)

    def _identity_param(self):
        """The parameter this function returns unchanged (itself, or through Path/str/os.fspath), when every return
        does: owner_only_dir returns the path it was given, so its value at a call site is that site's argument and
        not the union over every caller (the census resolves such a helper per site, the one place it is
        context-sensitive)."""
        def base(e):
            if isinstance(e, ast.Name):
                return e.id
            if isinstance(e, ast.Call) and len(e.args) == 1 and not e.keywords:
                n = e.func.id if isinstance(e.func, ast.Name) else (e.func.attr if isinstance(e.func, ast.Attribute) else "")
                if n in ("Path", "str", "fspath", "PurePath"):
                    return base(e.args[0])
            return None
        if self.is_lambda:
            b = base(self.node.body)
            return b if b in self.params else None
        assigns = {}
        for n in ast.walk(self.node):
            if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
                assigns.setdefault(n.targets[0].id, []).append(base(n.value))
        found = set()
        for n in ast.walk(self.node):
            if isinstance(n, ast.Return):
                b = base(n.value) if n.value is not None else None
                if b is None:
                    return None
                if b in self.params:
                    found.add(b)
                    continue
                srcs = assigns.get(b)
                if not srcs or any(s is None or s not in self.params for s in srcs):
                    return None
                found |= set(srcs)
        return found.pop() if len(found) == 1 else None

    def _tokens(self):
        """What a walk of this function could be moved by: whether it holds a seed constant, the names it calls and the
        attributes it reads. A function with no seed, no tainted parameter, no callee whose return is tainted and no
        tainted attribute read cannot change, and the fixpoint skips it."""
        calls, attrs, seed = set(), set(), False
        for n in ast.walk(self.node):
            if isinstance(n, ast.Constant) and isinstance(n.value, (str, bytes)):
                v = n.value if isinstance(n.value, str) else n.value.decode("utf-8", "replace")
                if v == "hosts" or _HOSTS_RE.search(v):
                    seed = True
            elif isinstance(n, ast.Call):
                f = n.func
                calls.add(f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else ""))
            elif isinstance(n, ast.Attribute):
                attrs.add(n.attr)
        return seed, calls, attrs

    def scopes(self):
        """This scope, then each enclosing FUNCTION scope, then the module level: the scopes a name read here resolves
        in (a class body in the chain is skipped, as Python skips it)."""
        yield self
        o = self.outer
        while o is not None:
            if not o.is_class_body or o.qual == "module level":
                yield o
            o = o.outer

    def __repr__(self):
        return "%s:%s" % (self.file, self.qual)


class Terminal:
    def __init__(self, fn, node, op, arg_text, ordinal, mech, origins, why=""):
        self.fn, self.node, self.op, self.arg_text, self.ordinal, self.mech, self.origins, self.why = \
            fn, node, op, arg_text, ordinal, mech, origins, why

    def key(self):
        return (self.fn.file, self.fn.qual, self.op, self.arg_text, self.ordinal)


class Census:
    def __init__(self, root, files=FILES):
        self.root = Path(root)
        self.files = tuple(files)
        self.src, self.lines, self.trees, self.fns, self.classes, self.mod_fns = {}, {}, {}, {}, {}, {}
        self.by_name, self.methods, self.bases, self.class_body = {}, {}, {}, {}
        self.callables, self.attr_callables, self.properties, self.setters = {}, {}, {}, {}
        self.local, self.attr, self.ret, self.ret_type, self.var_type, self.attr_type = {}, {}, {}, {}, {}, {}
        self.terminals, self.escapes, self.seeds, self.sites = {}, {}, [], {}
        self.sites_by_fn = {}
        self.shape_local, self.shape_ret = {}, {}          # per-element tags of tuple-valued names and returns
        self.calls_of = {}
        self._ordinals = {}
        self._tag_pos, self._tag_group = {}, {}
        self.dyn_reads = {}
        self._changed = False
        self._reach_memo = {}
        self._resolving = set()
        for f in self.files:
            self._index(f)

    # ── indexing ──────────────────────────────────────────────────────────────────────────────────
    def _index(self, f):
        """Every scope of the file: the module level, each class body, each function and method, and, inside any of
        those, each nested function, lambda and class, in discovery order (a scope before the scopes it encloses), so
        the `_fn` marking below lets an inner scope's nodes override the outer's."""
        src = (self.root / f).read_text(encoding="utf-8")
        tree = ast.parse(src)
        self.src[f], self.trees[f], self.lines[f] = src, tree, src.splitlines(keepends=True)
        order = []
        top = [n for n in tree.body if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
        mod_fn = Fn(f, "module level", _pseudo_def("module level", top, 1), None)
        self.fns[(f, "module level")] = mod_fn
        order.append(mod_fn)
        self._register_nested(f, mod_fn, top, order)
        for n in tree.body:
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                fn = Fn(f, n.name, n, None, outer=mod_fn)
                self.fns[(f, n.name)] = fn
                self.by_name.setdefault(n.name, []).append(fn)
                order.append(fn)
                self._register_nested(f, fn, n.body, order)
            elif isinstance(n, ast.ClassDef):
                self._register_class(f, n, mod_fn, order)
        self.mod_fns[f] = order
        for fn in order:
            for node in ast.walk(fn.node):
                if not isinstance(node, SHARED_NODE_TYPES):      # the parser's shared nodes carry no mark (module docstring)
                    node._fn = fn
        for fn in order:
            fn.finish()

    def _register_class(self, f, cdef, outer, order):
        cname = cdef.name
        self.classes[cname] = (f, cdef)
        self.bases[cname] = [(_dotted(b) or "").split(".")[-1] for b in cdef.bases]
        body = [c for c in cdef.body if not isinstance(c, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
        cb = Fn(f, cname + ".<class body>", _pseudo_def(cname + ".<class body>", body, cdef.lineno), cname, outer=outer,
                is_class_body=True)
        self.fns[(f, cb.qual)] = cb
        self.class_body[cname] = cb
        order.append(cb)
        self._register_nested(f, cb, body, order)
        for c in cdef.body:
            if isinstance(c, (ast.FunctionDef, ast.AsyncFunctionDef)):
                fn = Fn(f, cname + "." + c.name, c, cname, outer=cb)
                self.fns[(f, fn.qual)] = fn
                self.methods.setdefault((cname, c.name), []).append(fn)
                order.append(fn)
                for d in fn.decorators:
                    if d in PROPERTY_DECORATORS:
                        self.properties[(cname, c.name)] = fn
                    elif d.endswith(".setter") and d.count(".") == 1:
                        self.setters[(cname, d.split(".")[0])] = fn
                self._register_nested(f, fn, c.body, order)
            elif isinstance(c, ast.ClassDef):
                self._register_class(f, c, cb, order)

    def _register_nested(self, f, fn, stmts, order):
        """The functions, lambdas and classes written inside `fn`'s own statements (not inside a nested scope): each is a
        scope of its own reading `fn`'s names; a nested def is callable by its name in `fn`, a lambda where its value is
        bound (the walk records that binding)."""
        todo = list(stmts)
        while todo:
            n = todo.pop()
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                nf = Fn(f, fn.qual + "." + n.name, n, fn.cls, outer=fn)
                self.fns[(f, nf.qual)] = nf
                self.callables.setdefault((f, fn.qual, n.name), []).append(nf)
                fn.bound.add(n.name)                  # `def home():` binds `home` in the enclosing scope
                order.append(nf)
                self._register_nested(f, nf, n.body, order)
                todo.extend(n.decorator_list + [d for d in n.args.defaults + n.args.kw_defaults if d is not None])
            elif isinstance(n, ast.Lambda):
                lf = Fn(f, fn.qual + ".<lambda>@%d" % n.lineno, n, fn.cls, outer=fn)
                self.fns[(f, lf.qual)] = lf
                if not isinstance(n, SHARED_NODE_TYPES):         # a Lambda never is one; the guard stands at every mark (module docstring)
                    n._lfn = lf
                order.append(lf)
                self._register_nested(f, lf, [n.body], order)
                todo.extend([d for d in n.args.defaults + n.args.kw_defaults if d is not None])
            elif isinstance(n, ast.ClassDef):
                fn.bound.add(n.name)
                self._register_class(f, n, fn, order)
            else:
                todo.extend(ast.iter_child_nodes(n))

    def segment(self, fn, node):
        """The node's source text, whitespace collapsed, from the cached lines (ast.get_source_segment splits the
        whole file per call, which made the walk of a 21000-line module take half a minute)."""
        lines = self.lines[fn.file]
        a, b = node.lineno - 1, node.end_lineno - 1
        if a == b:
            text = lines[a][node.col_offset:node.end_col_offset]
        else:
            text = lines[a][node.col_offset:] + "".join(lines[a + 1:b]) + lines[b][:node.end_col_offset]
        return " ".join(text.split())

    def ordinal(self, fn, kind, text):
        k = (fn.file, fn.qual, kind, text)
        self._ordinals[k] = self._ordinals.get(k, 0) + 1
        return self._ordinals[k]

    # ── state ─────────────────────────────────────────────────────────────────────────────────────
    def _add(self, store, key, tags):
        if not tags:
            return
        cur = store.setdefault(key, set())
        before = len(cur)
        cur |= tags
        if len(cur) != before:
            self._changed = True

    def _type(self, store, key, cls):
        """The candidate classes of a name, an attribute or a return, in the order met and never dropped: two
        constructors reaching one name resolve to the methods and attributes of BOTH (the safe direction), and the set
        only grows, so the fixpoint holds (the `*` bucket, keyed by attribute name over every receiver, meets many)."""
        for c in (cls if isinstance(cls, tuple) else ((cls,) if cls else ())):
            cur = store.get(key, ())
            if c not in cur:
                store[key] = cur + (c,)
                self._changed = True

    def _scope_of(self, fn, name):
        """The scope a read or a store of `name` inside `fn` binds in: `fn` when it binds the name itself (a parameter,
        an assignment, a for or with target, a capture), else the nearest enclosing function scope that does, else the
        module level; a `global` name is the module's, a `nonlocal` name the nearest enclosing function's that binds it."""
        if name in fn.globals_:
            return self.fns[(fn.file, "module level")]
        chain = fn.chain if fn.chain is not None else list(fn.scopes())
        if name in fn.nonlocals:
            chain = chain[1:]
        for s in chain:
            if name in s.bound or (s.qual == "module level"):
                return s
        return chain[-1]

    def local_tags(self, fn, name):
        s = self._scope_of(fn, name)
        return self.local.get((s.file, s.qual, name), set())

    def _mro(self, cls):
        seen, todo = [], [cls]
        while todo:
            c = todo.pop(0)
            if c in seen or c is None:
                continue
            seen.append(c)
            todo.extend(self.bases.get(c, []))
        return seen

    def attr_tags(self, cls, attr, fn=None, node=None):
        """The tags a read of `<instance of cls>.attr` yields: every store to the attribute on the class or a base, a
        store to the same attribute name on a receiver the walk could not type (the `*` bucket, the safe direction), and
        the return of a property of that name, with the read recorded as an origin like a call."""
        out = set(self.attr.get(("*", attr), set()))
        for c in self._mro(cls):
            out |= self.attr.get((c, attr), set())
            prop = self.properties.get((c, attr))
            if prop is not None:
                r = self.ret.get((prop.file, prop.qual), set())
                if r and fn is not None and node is not None:
                    text = self.segment(fn, node)
                    out |= r | {Tag(next(iter(r)).kind, fn.file, node.lineno, text, fn.qual, self._ord_of(fn, "call", text, node))}
                else:
                    out |= r
        return out

    def _all_attr_tags(self, cls):
        """A dynamic read (`getattr(self, name)`, `vars(self)`): every attribute of the class and its bases."""
        mro = self._mro(cls) + ["*"]
        out = set()
        for (c, a), tags in self.attr.items():
            if c in mro:
                out |= tags
        for (c, a), prop in self.properties.items():
            if c in mro:
                out |= self.ret.get((prop.file, prop.qual), set())
        return out

    # ── resolution ────────────────────────────────────────────────────────────────────────────────
    def dotted(self, e):
        return _dotted(e) if not isinstance(e, ast.Call) else None

    def _is_type_of_self(self, e, fn):
        """`type(self)`, `self.__class__`, `cls`: the class object of the method's class."""
        if isinstance(e, ast.Call) and isinstance(e.func, ast.Name) and e.func.id == "type" and len(e.args) == 1:
            return self.type_of(e.args[0], fn)
        if isinstance(e, ast.Attribute) and e.attr == "__class__":
            return self.type_of(e.value, fn)
        return None

    def _class_named(self, e, fn):
        """The class an expression denotes as a class object, or None: a bare class name, `cls`, `type(self)`,
        `self.__class__`, `mod.Class`."""
        if isinstance(e, ast.Name):
            if e.id in self.classes:
                return e.id
            if e.id == "cls" and fn.cls:
                return fn.cls
            return None
        if isinstance(e, ast.Attribute) and e.attr in self.classes and e.attr != "__class__":
            return e.attr
        return self._is_type_of_self(e, fn)

    def _local_callables(self, fn, name):
        s = self._scope_of(fn, name)
        return self.callables.get((s.file, s.qual, name), [])

    def resolve(self, call, fn):
        """The in-file functions a call may reach, or [] when it reaches none the census knows."""
        f = call.func
        if isinstance(f, ast.Lambda):
            return [f._lfn] if hasattr(f, "_lfn") else []
        if isinstance(f, ast.Name):
            found = self._local_callables(fn, f.id)
            if found:
                return found
            if f.id in self.classes:
                return self._init_of(f.id)
            if f.id == "cls" and fn.cls:
                return self._init_of(fn.cls)
            if f.id in fn.params:
                return self._param_callables(fn, f.id)
            if self.local_tags(fn, f.id):
                return []
            return [x for x in self.by_name.get(f.id, []) if x.file == fn.file] or self.by_name.get(f.id, [])
        if isinstance(f, ast.Attribute):
            recv, name = f.value, f.attr
            if isinstance(recv, ast.Call) and isinstance(recv.func, ast.Name) and recv.func.id == "super" and fn.cls:
                for c in self._mro(fn.cls)[1:]:
                    if (c, name) in self.methods:
                        return self.methods[(c, name)]
                return []
            if isinstance(recv, ast.Name) and recv.id in ("self", "cls") and fn.cls:
                if name == "__class__":
                    return []
                for c in self._mro(fn.cls):
                    if (c, name) in self.attr_callables:
                        return self.attr_callables[(c, name)]
                    if (c, name) in self.methods:
                        return self.methods[(c, name)]
                return [m for k, ms in self.methods.items() if k[1] == name for m in ms]
            cn = self._class_named(recv, fn)
            if cn:
                for c in self._mro(cn):
                    if (c, name) in self.methods:
                        return self.methods[(c, name)]
                return []
            ts = self.types_of(recv, fn)
            if ts:
                out = []
                for t in ts:
                    for c in self._mro(t):
                        if (c, name) in self.attr_callables:
                            out.extend(x for x in self.attr_callables[(c, name)] if x not in out)
                            break
                        if (c, name) in self.methods:
                            out.extend(x for x in self.methods[(c, name)] if x not in out)
                            break
                return out
            if name in self.classes:
                return self._init_of(name)
            if name in self.by_name and name not in PATH_METHODS and name not in PURE_METHODS:
                return self.by_name[name]
        return []

    def _init_of(self, cname):
        for c in self._mro(cname):
            if (c, "__init__") in self.methods:
                return self.methods[(c, "__init__")]
        return []

    def _param_callables(self, fn, pname):
        """The callables a parameter is bound to at the function's call sites (a bound method, a function, a lambda);
        a parameter forwarded around a cycle of calls resolves once per cycle."""
        key = (fn.file, fn.qual, pname)
        if key in self._resolving:
            return []
        self._resolving.add(key)
        try:
            return self._param_callables_inner(fn, pname)
        finally:
            self._resolving.discard(key)

    def _param_callables_inner(self, fn, pname):
        out = []
        for site_fn, call in self.calls_of.get((fn.file, fn.qual), []):
            bound = self._bound_arg(call, fn, pname)
            if bound is None:
                continue
            if isinstance(bound, ast.Lambda):
                if hasattr(bound, "_lfn"):
                    out.append(bound._lfn)
                continue
            out.extend(self.resolve(ast.Call(func=bound, args=[], keywords=[]), site_fn))
        return out

    def _positional(self, call, callee):
        """The callee's positional parameter names aligned with the call's positional arguments: the bound `self` is
        dropped unless the call spells it (`Class.method(self, ...)`, an unbound call); a classmethod's `cls` and a
        constructor's `self` are never bound to an argument."""
        pos = list(callee.pos)
        if callee.cls and pos and pos[0] in ("self", "cls") and "staticmethod" not in callee.decorators:
            if "classmethod" in callee.decorators or callee.qual.endswith(".__init__"):
                pos = pos[1:]
            else:
                explicit = isinstance(call.func, ast.Attribute) and self._class_named(call.func.value, self.fns.get(
                    (callee.file, "module level"))) is not None and not (
                    isinstance(call.func.value, ast.Name) and call.func.value.id == "cls")
                if not explicit:
                    pos = pos[1:]
        return pos

    def _bound_arg(self, call, callee, pname):
        for kw in call.keywords:
            if kw.arg == pname:
                return kw.value
        pos = self._positional(call, callee)
        if pname in pos:
            i = pos.index(pname)
            if i < len(call.args) and not isinstance(call.args[i], ast.Starred):
                return call.args[i]
        return None

    def types_of(self, e, fn):
        """Every class of the files the expression may be an instance of (a tuple, possibly empty)."""
        if isinstance(e, ast.Name):
            if e.id in ("self", "cls"):
                return (fn.cls,) if fn.cls else ()
            s = self._scope_of(fn, e.id)
            return self.var_type.get((s.file, s.qual, e.id), ())
        if isinstance(e, ast.Attribute):
            out = ()
            if isinstance(e.value, ast.Name) and e.value.id in ("self", "cls") and fn.cls:
                owners = (fn.cls,)
            else:
                owners = self.types_of(e.value, fn)
            for t in owners:
                for c in self._mro(t):
                    out += tuple(x for x in self.attr_type.get((c, e.attr), ()) if x not in out)
            out += tuple(x for x in self.attr_type.get(("*", e.attr), ()) if x not in out)
            return out
        if isinstance(e, ast.Call):
            out = ()
            for callee in self.resolve(e, fn):
                if callee.qual.endswith(".__init__"):
                    out += (callee.cls,) if callee.cls not in out else ()
                else:
                    out += tuple(x for x in self.ret_type.get((callee.file, callee.qual), ()) if x not in out)
            return out
        if isinstance(e, ast.Await):
            return self.types_of(e.value, fn)
        return ()

    def type_of(self, e, fn):
        """The first candidate class, for the places that want one; `types_of` for the union."""
        t = self.types_of(e, fn)
        return t[0] if t else None

    # ── taint of an expression ────────────────────────────────────────────────────────────────────
    def tags(self, e, fn):
        """The origin tags carried by expression `e` inside `fn` (a set, possibly empty)."""
        if e is None:
            return set()
        if isinstance(e, ast.Constant):
            return self._seed_const(e, fn)
        if isinstance(e, ast.Name):
            return set(self.local_tags(fn, e.id))
        if isinstance(e, ast.Attribute):
            return self._attribute(e, fn)
        if isinstance(e, (ast.BinOp,)):
            return self.tags(e.left, fn) | self.tags(e.right, fn)
        if isinstance(e, ast.JoinedStr):
            out = set()
            for v in e.values:
                out |= self.tags(v.value if isinstance(v, ast.FormattedValue) else v, fn)
            return out
        if isinstance(e, ast.FormattedValue):
            return self.tags(e.value, fn)
        if isinstance(e, (ast.Tuple, ast.List, ast.Set)):
            out = set()
            for x in e.elts:
                out |= self.tags(x, fn)
            return out
        if isinstance(e, ast.Dict):
            out = set()
            for x in e.values:
                out |= self.tags(x, fn)
            return out
        if isinstance(e, ast.Starred):
            return self.tags(e.value, fn)
        if isinstance(e, ast.Subscript):
            return self.tags(e.value, fn)
        if isinstance(e, ast.IfExp):
            return self.tags(e.body, fn) | self.tags(e.orelse, fn)
        if isinstance(e, ast.BoolOp):
            out = set()
            for x in e.values:
                out |= self.tags(x, fn)
            return out
        if isinstance(e, ast.NamedExpr):
            t = self.tags(e.value, fn)
            self._bind_target(e.target, t, fn, self.types_of(e.value, fn), e.value)
            return t
        if isinstance(e, (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)):
            for g in e.generators:
                self._bind_target(g.target, self.tags(g.iter, fn) | self._yielded(g.iter, fn), fn, None, g.iter)
                for cond in g.ifs:
                    self.tags(cond, fn)
            if isinstance(e, ast.DictComp):
                return self.tags(e.value, fn)
            return self.tags(e.elt, fn)
        if isinstance(e, (ast.Await, ast.YieldFrom)):
            return self.tags(e.value, fn)
        if isinstance(e, ast.Yield):
            return self.tags(e.value, fn) if e.value is not None else set()
        if isinstance(e, ast.Call):
            return self._call(e, fn)
        if isinstance(e, ast.Lambda):
            return set()                      # the function object carries no path; its body is a scope of its own
        if isinstance(e, ast.Compare):
            for x in [e.left] + list(e.comparators):
                self.tags(x, fn)              # walked for the calls inside; a comparison yields a bool
            return set()
        if isinstance(e, ast.UnaryOp):
            return self.tags(e.operand, fn)
        return set()

    def _attribute(self, e, fn):
        if e.attr in DROP_ATTRS:
            return set()
        if e.attr in ("filename", "filename2"):
            inner = self.tags(e.value, fn)
            return {t.as_kind("path") for t in inner if t.kind == "exc"} | {t for t in inner if t.kind in ("path", "text")}
        if isinstance(e.value, ast.Name) and e.value.id in ("self", "cls") and fn.cls:
            return self.attr_tags(fn.cls, e.attr, fn, e)
        cn = self._class_named(e.value, fn)
        if cn and e.attr != "__class__":
            return self.attr_tags(cn, e.attr, fn, e)
        ts = self.types_of(e.value, fn)
        if ts:
            out = set()
            for t in ts:
                out |= self.attr_tags(t, e.attr, fn, e)
            return out
        inner = self.tags(e.value, fn)
        if e.attr in PURE_ATTRS:
            return inner
        return {t for t in inner if t.kind != "exc"} | self.attr.get(("*", e.attr), set())

    def _merge_shape(self, store, key, shape):
        """Union a shape into the store per element; two lengths for one key settle to False (no shape) once, so the
        fixpoint cannot oscillate between them."""
        old = store.get(key)
        if old is False:
            return
        if old is None:
            store[key] = [set(x) for x in shape]
            self._changed = True
            return
        if len(old) != len(shape):
            store[key] = False
            self._changed = True
            return
        for a, b in zip(old, shape):
            if b - a:
                a |= b
                self._changed = True

    def _elems(self, e, fn):
        """The per-element tag sets of a tuple-valued expression, or None when it has no known shape: a tuple or list
        literal, a comprehension whose element is a tuple literal, sorted/list/tuple/reversed of one, a name bound
        from one, a call to a function of the files whose returns are tuple literals. Unpacking such a value binds each
        target to its own element's tags; without a shape a tuple target takes the union (`for first, p in segs` gave
        the offset the path's taint, and through it every ack the transport sent)."""
        if isinstance(e, (ast.Tuple, ast.List)) and not any(isinstance(x, ast.Starred) for x in e.elts):
            return [self.tags(x, fn) for x in e.elts]
        if isinstance(e, (ast.ListComp, ast.SetComp, ast.GeneratorExp)) and isinstance(e.elt, ast.Tuple):
            self.tags(e, fn)                              # binds the generators' targets
            return [self.tags(x, fn) for x in e.elt.elts]
        if isinstance(e, ast.Call):
            name = self.dotted(e.func)
            if name in ("sorted", "list", "tuple", "reversed", "iter") and e.args:
                return self._elems(e.args[0], fn)
            shapes = [self.shape_ret[(c.file, c.qual)] for c in self.resolve(e, fn) if self.shape_ret.get((c.file, c.qual))]
            if shapes and all(len(x) == len(shapes[0]) for x in shapes):
                return [set().union(*[x[i] for x in shapes]) for i in range(len(shapes[0]))]
            return None
        if isinstance(e, ast.Name):
            s = self._scope_of(fn, e.id)
            return self.shape_local.get((s.file, s.qual, e.id)) or None
        return None

    def _seed_const(self, e, fn):
        v = e.value
        if isinstance(v, str):
            exact, contains = v == "hosts", bool(_HOSTS_RE.search(v))
        elif isinstance(v, bytes):
            exact, contains = v == b"hosts", bool(_HOSTS_RE.search(v.decode("utf-8", "replace")))
        else:
            return set()
        if not (exact or contains):
            return set()
        if self._excluded_position(e) or isinstance(getattr(e, "_parent", None), ast.Expr):   # a docstring is no path
            return set()
        kind = "path" if exact else "text"
        key = (fn.file, fn.qual, e.lineno, e.col_offset)
        for s in self.seeds:
            if s[0] == key:
                return {s[1]}
        text = self.segment(fn, e)
        tag = Tag(kind, fn.file, e.lineno, text, fn.qual, self._ord_of(fn, "seed", text, e))
        self.seeds.append((key, tag))
        self._changed = True
        return {tag}

    def _excluded_position(self, e):
        p = getattr(e, "_parent", None)
        if isinstance(p, ast.Dict) and e in p.keys:
            return True
        if isinstance(p, ast.Subscript) and p.slice is e:
            return True
        if isinstance(p, ast.Compare):
            return True
        if isinstance(p, ast.Call) and isinstance(p.func, ast.Attribute) and p.func.attr in KEY_METHODS \
                and p.args and p.args[0] is e:
            return True                       # `d.get("hosts")`, `d.pop("hosts")`: a dict key, as a literal key is
        return False

    def _yielded(self, e, fn):
        """A read that yields paths under a tainted directory (glob, iterdir, scandir) yields tainted paths."""
        if isinstance(e, ast.Call):
            name = self.dotted(e.func)
            if isinstance(e.func, ast.Attribute) and e.func.attr in YIELDS_PATHS:
                return self.tags(e.func.value, fn)
            if name in YIELDS_PATHS and e.args:
                return self.tags(e.args[0], fn)
        return set()

    # ── calls ─────────────────────────────────────────────────────────────────────────────────────
    def _callable_value(self, a, fn):
        """Whether expression `a`, as an argument, is a callable that would take a path somewhere the walk cannot see
        if it were applied: a lambda, a nested function's name, a function or method of the files, a terminal's name
        (`open`, `os.stat`, `Path.read_text`). A pure conversion's or a type's name is not one (`isinstance(p, Path)`,
        `map(str, paths)`: applying it yields the value again, which the call's own class already carries)."""
        if isinstance(a, ast.Lambda):
            return True
        if isinstance(a, (ast.Name, ast.Attribute)):
            if self.local_tags(fn, _dotted(a) or "") or (isinstance(a, ast.Name) and a.id in fn.params):
                return False              # a value, not a callable name
            name = _dotted(a)
            if name in PATH_FUNCS or name in FD_FUNCS or name in EXEC_FUNCS:
                return True
            if isinstance(a, ast.Attribute) and a.attr in PATH_METHODS and self._class_named(a.value, fn) is None \
                    and isinstance(a.value, ast.Name) and a.value.id in ("Path", "PurePath", "os", "shutil"):
                return True
            if self.resolve(ast.Call(func=a, args=[], keywords=[]), fn):
                return True
        return False

    def _escape(self, e, fn, path_tags, why, text=None):
        text = text or self.segment(fn, e)
        key = (fn.file, fn.qual, "escape", text, e.lineno, e.col_offset)
        if key not in self.escapes:
            self.escapes[key] = Terminal(fn, e, "escape", text, self._ord_of(fn, "escape", text, e), "escape", set(), why)
            self._changed = True
        before = len(self.escapes[key].origins)
        self.escapes[key].origins |= path_tags
        if len(self.escapes[key].origins) != before:
            self._changed = True

    def _call(self, e, fn):
        name = self.dotted(e.func)
        arg_tags = [self.tags(a, fn) for a in e.args]
        kw_tags = {kw.arg: self.tags(kw.value, fn) for kw in e.keywords}
        for kw in e.keywords:
            if kw.arg is None:
                for t in self.tags(kw.value, fn):
                    kw_tags.setdefault("**", set()).add(t)
        all_tags = set().union(*arg_tags) if arg_tags else set()
        for v in kw_tags.values():
            all_tags |= v
        path_tags = {t for t in all_tags if t.kind == "path"}
        recv_tags = self.tags(e.func.value, fn) if isinstance(e.func, ast.Attribute) else set()
        recv_path = {t for t in recv_tags if t.kind == "path"}
        # terminals
        term = self._terminal(e, fn, name, arg_tags, kw_tags)
        if term is not None:
            return term
        callees = self.resolve(e, fn)
        # a callable handed as a value beside a tainted argument, into a call the walk does not follow into
        if not callees and path_tags:
            applied = [a for a in e.args if self._callable_value(a, fn)] + \
                      [kw.value for kw in e.keywords if self._callable_value(kw.value, fn)]
            if applied:
                self._escape(e, fn, path_tags, "a callable (%s) applied outside the walk to a tainted argument"
                             % ", ".join(self.segment(fn, a) for a in applied))
                return set()
        # reads and stores by attribute name
        if name == "getattr" and e.args:
            recv = e.args[0]
            if len(e.args) > 1 and isinstance(e.args[1], ast.Constant) and isinstance(e.args[1].value, str):
                read = ast.Attribute(value=recv, attr=e.args[1].value, ctx=ast.Load())
                ast.copy_location(read, e)
                return self._attribute(read, fn) | (arg_tags[2] if len(arg_tags) > 2 else set())
            cn = self._class_named(recv, fn)
            owners = (cn,) if cn else self.types_of(recv, fn)
            if owners:
                out = set()
                for t in owners:
                    out |= self._all_attr_tags(t)
                return out | (arg_tags[2] if len(arg_tags) > 2 else set())
            # a dynamic read on a receiver the walk cannot type: the walk does not know the object's attributes, and
            # says so (an escape, decided once the fixpoint holds) whenever a path is stored by attribute name on some
            # receiver it could not type either (the `*` bucket), since this read may be the one that reads it; with
            # that bucket empty of paths, as over this tree, the read carries nothing and nothing is printed
            self._dyn_read(e, fn)
            inner = self.tags(recv, fn)
            return {t for t in inner if t.kind != "exc"} | (arg_tags[2] if len(arg_tags) > 2 else set())
        if name == "vars" and e.args:
            cn = self._class_named(e.args[0], fn)
            owners = (cn,) if cn else self.types_of(e.args[0], fn)
            out = set()
            for t in owners:
                out |= self._all_attr_tags(t)
            if not owners:
                self._dyn_read(e, fn)
            return out
        if name == "setattr" and len(e.args) == 3:
            if isinstance(e.args[1], ast.Constant) and isinstance(e.args[1].value, str):
                store = ast.Attribute(value=e.args[0], attr=e.args[1].value, ctx=ast.Store())
                self._bind_target(store, arg_tags[2], fn, self.types_of(e.args[2], fn), e.args[2])
                return set()
            if {t for t in arg_tags[2] if t.kind == "path"}:
                self._escape(e, fn, {t for t in arg_tags[2] if t.kind == "path"}, "a store under a name the walk cannot read")
            return set()
        # pure conversions and container operations
        if name in PURE_FUNCS:
            return {t for t in all_tags if t.kind != "exc"}
        if isinstance(e.func, ast.Attribute):
            m = e.func.attr
            if m in STORE_METHODS:
                self._store_into(e.func.value, all_tags, fn)
                return set()
            if m in STORE_RETURN_METHODS:
                self._store_into(e.func.value, all_tags, fn)
                return {t for t in recv_tags | all_tags if t.kind != "exc"}
            if m in PURE_METHODS:
                return {t for t in recv_tags | all_tags if t.kind != "exc"}
            if m in SINK_METHODS and not callees:
                return set()
        if name in SINK_FUNCS:
            return set()
        if self._is_exception(e.func):
            return set()
        if callees:
            key = (fn.file, fn.qual, e.lineno, e.col_offset, e.end_lineno, e.end_col_offset)
            if key not in self.sites:
                self.sites[key] = (fn, e, callees)
                self.sites_by_fn.setdefault((fn.file, fn.qual), []).append(self.sites[key])
            out = set()
            for c in callees:
                self._bind_call(e, c, fn, arg_tags, kw_tags)
                if c.identity is not None:
                    # an identity-returning helper (owner_only_dir): the value at this site is this site's argument
                    bound = self._bound_arg(e, c, c.identity)
                    r = self.tags(bound, fn) if bound is not None else set()
                else:
                    r = self.ret.get((c.file, c.qual), set())
                if r:
                    text = self.segment(fn, e)
                    out |= r | {Tag(next(iter(r)).kind, fn.file, e.lineno, text, fn.qual, self._ord_of(fn, "call", text, e))}
            if isinstance(e.func, ast.Name) and e.func.id in fn.params:
                return set()
            return out
        # a parameter called (a logger handed in): a data sink by declaration
        if isinstance(e.func, ast.Name) and e.func.id in fn.params:
            if e.func.id in LOG_PARAMS:
                return set()
            for c in self._param_callables(fn, e.func.id):
                self._bind_call(e, c, fn, arg_tags, kw_tags)
            return set()
        if isinstance(e.func, ast.Attribute) and e.func.attr in LOG_PARAMS:
            return set()
        if path_tags:
            self._escape(e, fn, path_tags, "a tainted argument to a call the walk cannot resolve")
        elif recv_path:
            self._escape(e, fn, recv_path, "a method the walk does not know, called on a tainted receiver")
        return set()

    def _dyn_read(self, e, fn):
        key = (fn.file, e.lineno, e.col_offset)
        if key not in self.dyn_reads:
            self.dyn_reads[key] = (e, fn)

    def _dyn_read_escapes(self):
        """Every dynamic attribute read on a receiver the walk could not type (collected over round 0, which walks every
        scope) is an escape when a path is stored by attribute name on such a receiver anywhere in the files."""
        star = {t for (c, a), tags in self.attr.items() if c == "*" for t in tags if t.kind == "path"}
        if not star:
            return
        for e, fn in self.dyn_reads.values():
            self._escape(e, fn, star, "a dynamic attribute read on a receiver the walk cannot type, while a path is stored by "
                         "attribute name on such a receiver")

    def _ord_of(self, fn, kind, text, node):
        k = (fn.file, fn.qual, kind, text, node.lineno, node.col_offset)
        if k in self._ordinals:
            return self._ordinals[k]
        n = self.ordinal(fn, kind, text)
        self._ordinals[k] = n
        self._tag_pos[(fn.file, fn.qual, text, n)] = (node.lineno, node.col_offset)
        self._tag_group.setdefault((fn.file, fn.qual, text), set()).add((node.lineno, node.col_offset))
        return n

    def _is_exception(self, f):
        """A call that constructs an exception is a message sink (its text is the sink, never a syscall): the callee's
        NAME has the shape (`...Error`, `...Exception`, `...Refused`, `...Like`, `...Warning`, `...Interrupt`), or it is a
        class of the files whose base chain reaches such a name (HostDirAbsent under HostDirRefused; the third addendum:
        through the second the rule read the name alone and that subclass's constructor was printed as an escape)."""
        name = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else "")
        seen, todo = set(), [name]
        while todo:
            n = todo.pop()
            if not n or n in seen:
                continue
            seen.add(n)
            if re.search(r"(Error|Exception|Refused|Like|Warning|Interrupt)$", n):
                return True
            todo.extend(self.bases.get(n, ()))
        return False

    def _bind_call(self, call, callee, fn, arg_tags, kw_tags):
        """Bind a call's arguments to the callee's parameters: their tags, and their type when the walk knows it (a
        HostDirs handed to _open_file_nofollow types `dirs` there, so `dirs.dir` reads the descriptor's taint). A lambda
        or a nested function handed as an argument is bound as a callable of the parameter."""
        self.calls_of.setdefault((callee.file, callee.qual), [])
        if not any(c is call for _, c in self.calls_of[(callee.file, callee.qual)]):
            self.calls_of[(callee.file, callee.qual)].append((fn, call))
        pos = self._positional(call, callee)
        for i, tags in enumerate(arg_tags):
            a = call.args[i]
            if isinstance(a, ast.Starred):
                for p in pos[i:]:
                    self._add(self.local, (callee.file, callee.qual, p), tags)
                break
            if i < len(pos):
                self._add(self.local, (callee.file, callee.qual, pos[i]), tags)
                self._type(self.var_type, (callee.file, callee.qual, pos[i]), self.types_of(a, fn))
                self._bind_callable(callee, pos[i], a, fn)
            elif callee.node.args.vararg:
                self._add(self.local, (callee.file, callee.qual, callee.node.args.vararg.arg), tags)
        for kw in call.keywords:
            k = kw.arg
            tags = kw_tags.get(k if k is not None else "**", set())
            if k in callee.params:
                self._add(self.local, (callee.file, callee.qual, k), tags)
                self._type(self.var_type, (callee.file, callee.qual, k), self.types_of(kw.value, fn))
                self._bind_callable(callee, k, kw.value, fn)
            elif k is None:
                for p in callee.params:
                    self._add(self.local, (callee.file, callee.qual, p), tags)
            elif callee.node.args.kwarg:
                self._add(self.local, (callee.file, callee.qual, callee.node.args.kwarg.arg), tags)

    def _bind_callable(self, callee, pname, value, fn):
        found = []
        if isinstance(value, ast.Lambda) and hasattr(value, "_lfn"):
            found = [value._lfn]
        elif isinstance(value, (ast.Name, ast.Attribute)) and not self.local_tags(fn, _dotted(value) or ""):
            found = self.resolve(ast.Call(func=value, args=[], keywords=[]), fn)
        if found:
            cur = self.callables.setdefault((callee.file, callee.qual, pname), [])
            for c in found:
                if c not in cur:
                    cur.append(c)
                    self._changed = True

    def _terminal(self, e, fn, name, arg_tags, kw_tags):
        """Record `e` as a terminal when a path or descriptor position carries taint; returns the tags the call
        yields (a descriptor for os.open, paths for a listing) or None when the call is no terminal."""
        recv_tags, is_method, m = set(), False, None
        if isinstance(e.func, ast.Attribute):
            m = e.func.attr
            recv_tags = self.tags(e.func.value, fn)
        positions = PATH_FUNCS.get(name)
        fd_positions = FD_FUNCS.get(name)
        exec_positions = EXEC_FUNCS.get(name)
        if positions is None and fd_positions is None and exec_positions is None:
            if m in PATH_METHODS and recv_tags and self._class_named(e.func.value, fn) is None:
                is_method = True
            else:
                return None
        path_tags, fd_tags, arg_text = set(), set(), None
        if is_method:
            path_tags = {t for t in recv_tags if t.kind in ("path", "text")}
            fd_tags = {t for t in recv_tags if t.kind == "fd"}
            arg_text = self.segment(fn, e.func.value)
            op = m
        else:
            op = name
            for p in (positions or ()) + (exec_positions or ()):
                if isinstance(p, int) and p < len(arg_tags):
                    path_tags |= {t for t in arg_tags[p] if t.kind in ("path", "text")}
                    fd_tags |= {t for t in arg_tags[p] if t.kind == "fd"}
                    arg_text = arg_text or self.segment(fn, e.args[p])
                elif isinstance(p, str) and p in kw_tags:
                    path_tags |= {t for t in kw_tags[p] if t.kind in ("path", "text")}
                    arg_text = arg_text or self.segment(fn, next(k.value for k in e.keywords if k.arg == p))
            for p in (fd_positions or ()):
                if p < len(arg_tags):
                    fd_tags |= {t for t in arg_tags[p] if t.kind == "fd"}
                    arg_text = arg_text or self.segment(fn, e.args[p])
            splat = kw_tags.get("**", set())          # `open(**kw)`: the walk cannot tell the keyword, so it is the path position
            if splat:
                path_tags |= {t for t in splat if t.kind in ("path", "text")}
                fd_tags |= {t for t in splat if t.kind == "fd"}
                arg_text = arg_text or "**" + self.segment(fn, next(k.value for k in e.keywords if k.arg is None))
        dir_fd = kw_tags.get("dir_fd", set())
        fd_tags |= {t for t in dir_fd if t.kind == "fd"}
        if exec_positions is not None:
            for k in EXEC_FD_KWS:
                fd_tags |= {t for t in kw_tags.get(k, set()) if t.kind == "fd"}
        if not path_tags and not fd_tags:
            return set()
        if exec_positions is not None:
            mech = "exec-arg" if path_tags else "by-descriptor"
        elif fd_tags and path_tags:
            mech = "mixed"          # one call, two roads by caller: a path at one site, a name under a descriptor at another
        elif fd_tags:
            mech = "by-descriptor"
        else:
            mech = "by-path"
        if arg_text is None:
            arg_text = self.segment(fn, e)
        key = (fn.file, fn.qual, op, arg_text, e.lineno, e.col_offset)
        if key not in self.terminals:
            self.terminals[key] = Terminal(fn, e, op, arg_text, self._ord_of(fn, op, arg_text, e), mech, set())
            self._changed = True
        t = self.terminals[key]
        if t.mech != mech:
            t.mech = mech
            self._changed = True
        before = len(t.origins)
        t.origins |= path_tags | fd_tags
        if len(t.origins) != before:
            self._changed = True
        origins = path_tags | fd_tags
        # what the call yields
        if name == "os.open" or (is_method and m == "open"):
            text = self.segment(fn, e)
            return {Tag("fd", fn.file, e.lineno, text, fn.qual, self._ord_of(fn, "fd", text, e))}
        if name == "os.fdopen":
            return {t for t in origins if t.kind == "fd"}
        if (is_method and m in YIELDS_PATHS) or name in YIELDS_PATHS:
            return {t for t in origins if t.kind != "fd"} if not fd_tags else set()
        if is_method and m in ("resolve", "readlink") or name == "os.path.realpath":
            return path_tags
        return set()

    def _store_into(self, target, tags, fn):
        """A store INTO the object a target names (`.append`, a subscript store): the name's own scope, which for a
        name this function does not bind is the enclosing scope's or the module's (`_CACHE[k] = v` on a module dict)."""
        if isinstance(target, ast.Name):
            s = self._scope_of(fn, target.id)
            if s.is_class_body:
                self._add(self.attr, (s.cls, target.id), tags)
            self._add(self.local, (s.file, s.qual, target.id), tags)
        elif isinstance(target, ast.Attribute):
            self._attr_store(target, tags, fn, None)
        elif isinstance(target, ast.Subscript):
            self._store_into(target.value, tags, fn)
        elif isinstance(target, ast.Call) and self.dotted(target.func) == "getattr" and len(target.args) > 1 \
                and isinstance(target.args[1], ast.Constant):
            read = ast.Attribute(value=target.args[0], attr=target.args[1].value, ctx=ast.Store())
            self._attr_store(read, tags, fn, None)

    def _attr_store(self, target, tags, fn, typ):
        """An attribute store on any receiver: `self`, a class object, a typed receiver, or one the walk cannot type
        (the `*` bucket keyed by the attribute's name, read back by every read of that name: the safe direction, where
        round 7's walk dropped the store in silence). A property with a setter binds the setter's parameter too."""
        recv = target.value
        if isinstance(recv, ast.Name) and recv.id in ("self", "cls") and fn.cls:
            owners = (fn.cls,)
        else:
            cn = self._class_named(recv, fn)
            owners = (cn,) if cn else self.types_of(recv, fn)
        for cls in owners or ("*",):
            if cls != "*":
                setter = None
                for c in self._mro(cls):
                    setter = self.setters.get((c, target.attr))
                    if setter:
                        break
                if setter is not None and len(setter.pos) > 1:
                    self._add(self.local, (setter.file, setter.qual, setter.pos[1]), tags)
                    self._type(self.var_type, (setter.file, setter.qual, setter.pos[1]), typ)
            self._add(self.attr, (cls, target.attr), tags)
            self._type(self.attr_type, (cls, target.attr), typ)

    def _bind_target(self, target, tags, fn, typ=None, value=None):
        if isinstance(target, (ast.Tuple, ast.List)):
            if isinstance(value, (ast.Tuple, ast.List)) and len(value.elts) == len(target.elts) \
                    and not any(isinstance(x, ast.Starred) for x in target.elts + value.elts):
                for x, v in zip(target.elts, value.elts):      # element-wise: `self.hosts, self.dir, self.path = hosts, dir, path`
                    self._bind_target(x, self.tags(v, fn), fn, self.types_of(v, fn), v)
                return
            shape = self._elems(value, fn) if value is not None else None
            if shape is not None and len(shape) == len(target.elts) and not any(isinstance(x, ast.Starred) for x in target.elts):
                for x, elem_tags in zip(target.elts, shape):   # element-wise through a known shape
                    self._bind_target(x, elem_tags, fn)
                return
            for x in target.elts:
                self._bind_target(x, tags, fn)
            return
        if isinstance(target, ast.Starred):
            return self._bind_target(target.value, tags, fn)
        if isinstance(value, ast.Lambda) and hasattr(value, "_lfn"):
            if isinstance(target, ast.Name):
                s = self._scope_of(fn, target.id)
                cur = self.callables.setdefault((s.file, s.qual, target.id), [])
                if value._lfn not in cur:
                    cur.append(value._lfn)
                    self._changed = True
            elif isinstance(target, ast.Attribute):
                recv = target.value
                if isinstance(recv, ast.Name) and recv.id in ("self", "cls") and fn.cls:
                    owners = (fn.cls,)
                else:
                    cn = self._class_named(recv, fn)
                    owners = (cn,) if cn else (self.types_of(recv, fn) or ("*",))
                for cls in owners:
                    cur = self.attr_callables.setdefault((cls, target.attr), [])
                    if value._lfn not in cur:
                        cur.append(value._lfn)
                        self._changed = True
        if isinstance(target, ast.Name):
            s = self._scope_of(fn, target.id)
            if s.is_class_body:                                   # a class-body assignment: an attribute of the class
                self._add(self.attr, (s.cls, target.id), tags)
                self._type(self.attr_type, (s.cls, target.id), typ)
            self._add(self.local, (s.file, s.qual, target.id), tags)
            self._type(self.var_type, (s.file, s.qual, target.id), typ)
            shape = self._elems(value, fn) if value is not None else None
            if shape is not None:
                self._merge_shape(self.shape_local, (s.file, s.qual, target.id), shape)
        elif isinstance(target, ast.Attribute):
            self._attr_store(target, tags, fn, typ)
        elif isinstance(target, ast.Subscript):
            self._store_into(target.value, tags, fn)

    def _reach_path_tags(self, fn, seen=None):
        """The path tags of every terminal inside `fn` and, transitively, inside the functions of the files its resolved
        call sites reach: what an exception raised in `fn`'s body can carry as its `filename`. Memoised per round."""
        key = (fn.file, fn.qual)
        if key in self._reach_memo:
            return self._reach_memo[key]
        seen = seen if seen is not None else set()
        if key in seen:
            return set()
        seen.add(key)
        out = set()
        for t in self.terminals.values():
            if t.fn is fn:
                out |= {o for o in t.origins if o.kind == "path"}
        for _, call, callees in self.sites_by_fn.get(key, []):
            for a in call.args:
                out |= {o for o in self.tags(a, fn) if o.kind == "path"}
            for c in callees:
                out |= self._reach_path_tags(c, seen)
        self._reach_memo[key] = out
        return out

    def _bind_handlers(self, node, fn):
        """`except ... as e`: `e` carries, as `exc` tags, the path of any syscall the try body or a callee of it made,
        readable through `e.filename` and `e.filename2` (OSError's path attributes) and nowhere else; bound only for
        a handler whose name the function reads so or hands to a call (finish() lists them)."""
        if not any(h.name and h.name in fn.exc_used for h in node.handlers):
            return
        body_tags = set()
        for n in node.body:
            for sub in ast.walk(n):
                if getattr(sub, "_fn", None) is not fn:
                    continue
                if isinstance(sub, ast.Call):
                    for a in sub.args:
                        body_tags |= {t for t in self.tags(a, fn) if t.kind == "path"}
                    for c in self.resolve(sub, fn):
                        body_tags |= self._reach_path_tags(c)
                    body_tags |= {t for t in self._reach_terminal(sub, fn)}
        exc = {t.as_kind("exc") for t in body_tags}
        for h in node.handlers:
            if h.name:
                self._add(self.local, (fn.file, fn.qual, h.name), exc)

    def _reach_terminal(self, call, fn):
        for (f, q, op, text, ln, col), t in self.terminals.items():
            if t.fn is fn and ln == call.lineno and col == call.col_offset:
                return {o for o in t.origins if o.kind == "path"}
        return set()

    # ── the walk ──────────────────────────────────────────────────────────────────────────────────
    def _walk_fn(self, fn):
        scope = fn.outer or fn
        for p, d in fn.defaults.items():                          # a default is evaluated in the defining scope
            self._add(self.local, (fn.file, fn.qual, p), {t for t in self.tags(d, scope) if t.kind != "exc"})
            self._type(self.var_type, (fn.file, fn.qual, p), self.types_of(d, scope))
            if isinstance(d, ast.Lambda) and hasattr(d, "_lfn"):
                cur = self.callables.setdefault((fn.file, fn.qual, p), [])
                if d._lfn not in cur:
                    cur.append(d._lfn)
                    self._changed = True
        if fn.is_lambda:
            self._add(self.ret, (fn.file, fn.qual), self.tags(fn.node.body, fn))
            self._type(self.ret_type, (fn.file, fn.qual), self.types_of(fn.node.body, fn))
            for node in ast.walk(fn.node.body):
                if getattr(node, "_fn", None) is fn and isinstance(node, ast.Call):
                    self.tags(node, fn)
            return
        for node in fn.own_nodes():
            if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                if node.value is None:
                    continue
                tags = self.tags(node.value, fn)
                typ = self.types_of(node.value, fn)
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for t in targets:
                    if isinstance(node, ast.AugAssign):
                        tags = tags | self.tags(t, fn)
                    self._bind_target(t, tags, fn, typ, node.value)
            elif isinstance(node, (ast.For, ast.AsyncFor)):
                self._bind_target(node.target, self.tags(node.iter, fn) | self._yielded(node.iter, fn), fn, None, node.iter)
            elif isinstance(node, (ast.With, ast.AsyncWith)):
                for item in node.items:
                    tags = self.tags(item.context_expr, fn)
                    if item.optional_vars is not None:
                        self._bind_target(item.optional_vars, tags, fn, self.types_of(item.context_expr, fn))
            elif isinstance(node, (ast.Return, ast.Yield)):
                if node.value is not None:
                    self._add(self.ret, (fn.file, fn.qual), {t for t in self.tags(node.value, fn) if t.kind != "exc"})
                    if isinstance(node, ast.Return):
                        self._type(self.ret_type, (fn.file, fn.qual), self.types_of(node.value, fn))
                    shape = self._elems(node.value, fn)
                    if shape is not None:
                        self._merge_shape(self.shape_ret, (fn.file, fn.qual), shape)
            elif isinstance(node, ast.Expr):
                self.tags(node.value, fn)
            elif isinstance(node, (ast.If, ast.While, ast.Assert)):
                self.tags(node.test, fn)
            elif isinstance(node, ast.Raise):
                self.tags(node.exc, fn)
            elif isinstance(node, ast.Match):
                subject = self.tags(node.subject, fn)
                for case in node.cases:
                    for p in ast.walk(case.pattern):
                        nm = getattr(p, "name", None) if isinstance(p, (ast.MatchAs, ast.MatchStar)) else \
                            (p.rest if isinstance(p, ast.MatchMapping) else None)
                        if nm:
                            self._add(self.local, (fn.file, fn.qual, nm), subject)
            elif isinstance(node, ast.Try) or (hasattr(ast, "TryStar") and isinstance(node, ast.TryStar)):
                self._bind_handlers(node, fn)
        for node in fn.own_nodes():
            if isinstance(node, ast.Call):
                self.tags(node, fn)

    def _decorator_escapes(self):
        """A decorator the walk does not know on a function that holds a seed, a tainted local or a tainted return: the
        name is rebound to whatever the decorator returned, which the walk cannot follow."""
        seed_quals = {(t.file, t.qual) for _, t in self.seeds}
        for fn in self.fns.values():
            unknown = [d for d in fn.decorators if d not in KNOWN_DECORATORS and not d.endswith(".setter")
                       and not d.endswith(".getter") and not d.endswith(".deleter")]
            if not unknown:
                continue
            path_tags = {t for t in self.ret.get((fn.file, fn.qual), set()) if t.kind == "path"}
            path_tags |= {t for (f, q, n), tags in self.local.items() if (f, q) == (fn.file, fn.qual) for t in tags if t.kind == "path"}
            path_tags |= {t for _, t in self.seeds if (t.file, t.qual) == (fn.file, fn.qual) and t.kind == "path"}
            if path_tags or (fn.file, fn.qual) in seed_quals:
                self._escape(fn.node, fn, path_tags, "a decorator the walk does not know (%s) rebinds a function that carries a path"
                             % ", ".join(unknown), text="@%s def %s" % (", @".join(unknown), fn.qual))

    def run(self):
        for f in self.files:
            for node in ast.walk(self.trees[f]):
                for child in ast.iter_child_nodes(node):
                    if not isinstance(child, SHARED_NODE_TYPES):  # the parser's shared nodes carry no mark (module docstring)
                        child._parent = node
        for f, qual, pname, why in DECLARED_SEEDS:
            if (f, qual) in self.fns:
                fn = self.fns[(f, qual)]
                self._add(self.local, (f, qual, pname), {Tag("path", f, fn.node.lineno, why, qual, 1)})
        for rnd in range(80):
            self._changed = False
            self._reach_memo = {}
            holders = {c for (c, a), tags in self.attr.items() if tags}
            minting = set()
            for fn in self.fns.values():
                if (self.ret.get((fn.file, fn.qual)) or any(t in holders for t in self.ret_type.get((fn.file, fn.qual), ()))
                        or any(t.qual == fn.qual and t.file == fn.file and t.kind == "path" for _, t in self.seeds)
                        or any(f == fn.file and q == fn.qual for f, q, _, _ in DECLARED_SEEDS)):
                    minting.add(fn.cls if fn.qual.endswith(".__init__") else fn.qual.split(".")[-1])
            tainted_rets = minting
            tainted_attrs = {a for (c, a), tags in self.attr.items() if tags} | \
                            {a for (c, a), p in self.properties.items() if self.ret.get((p.file, p.qual))}
            has_local = {(f, q) for (f, q, n), tags in self.local.items() if tags}
            # a name typed as a HOLDER of descriptors (a HostDirs) makes its scope as live as a tainted local does (the
            # seventh addendum, 2026-09-20): a holder handed down a chain of functions carrying no taint of their own is
            # typed one link per walk, so the chain's later links need a walk after their parameter's type arrives,
            # whatever order round 0 met them in (self.mod_fns is not source order); without this the view typed the
            # rest lazily and members() was not idempotent
            has_local |= {(f, q) for (f, q, n), types in self.var_type.items() if any(t in holders for t in types)}
            any_terminal = bool(self.terminals)
            for fn in [x for f in self.files for x in self.mod_fns[f]]:
                seed, calls, attrs = fn.tokens
                # a scope is walked when something could move it: a seed of its own, a tainted local in it or in a scope
                # it reads (its defining scope included, for a default), a call to a function whose value is tainted, a
                # read of a tainted attribute, or a handler binding it reads a path from once any terminal exists
                outer_live = any((s.file, s.qual) in has_local for s in fn.chain) or \
                    (fn.outer is not None and (fn.outer.file, fn.outer.qual) in has_local)
                if rnd > 0 and not (seed or outer_live or (calls & tainted_rets) or (attrs & tainted_attrs)
                                    or (fn.exc_used and any_terminal)):
                    continue                  # round 0 walks every scope once, so a type or a callable bound in a
                self._walk_fn(fn)             # function nothing tainted reaches (`sess = SdkSession(self, ...)`) is known
            if not self._changed:
                break
        else:
            raise AssertionError("the census did not reach a fixpoint in 80 rounds")
        self._decorator_escapes()
        self._dyn_read_escapes()
        return self

    # ── views ─────────────────────────────────────────────────────────────────────────────────────
    def roads(self):
        """The carriers and mints, read off the resolved call sites once the fixpoint holds: a CARRIER hands a tainted
        value (a path or a descriptor), or a HOLDER of one (a HostDirs, whose attributes carry the descriptors: kind
        `holder`), to a function of the files (`host_log_mark(dirs)`, `owner_only_dir(host_dir(...))`,
        `HostTransport.from_journal(hdir)`, `host_stderr_size(dirs)`); a MINT is a call whose value is tainted
        (`hdir = ht.host_dir(...)`, `spec_path = ht.write_spawn_spec(...)`) or that enters a function holding a seed or
        returning a descriptor holder (`open_host_dirs(...)`, `remove_host_dir(...)`, `hosts_dir(...)`), the roads by
        which a use inside a helper is reached from a caller that passes nothing tainted itself."""
        seed_quals = {(t.file, t.qual) for _, t in self.seeds if t.kind == "path"} | {(f, q) for f, q, _, _ in DECLARED_SEEDS}
        holders = {c for (c, a), tags in self.attr.items() if tags and c != "*"}
        out = []
        for (f, q, ln, col, _eln, _ecol), (fn, call, callees) in self.sites.items():
            kinds = set()
            args = list(call.args) + [kw.value for kw in call.keywords]
            for a in args:
                kinds |= {t.kind for t in self.tags(a, fn)}
                if any(t in holders for t in self.types_of(a, fn)) and not (isinstance(a, ast.Name) and a.id in ("self", "cls")):
                    kinds.add("holder")
            carrier = bool(kinds - {"text", "exc"})
            value = self.tags(call, fn)
            mint = bool(value) or any((c.file, c.qual) in seed_quals or any(t in holders for t in self.ret_type.get((c.file, c.qual), ()))
                                      for c in callees)
            if not (carrier or mint):
                continue

            def tainted(a):
                return bool({t for t in self.tags(a, fn) if t.kind not in ("text", "exc")}) or \
                    (any(t in holders for t in self.types_of(a, fn)) and not (isinstance(a, ast.Name) and a.id in ("self", "cls")))
            tainted_args = [self.segment(fn, a) for a in call.args if tainted(a)]
            tainted_args += ["%s=%s" % (kw.arg, self.segment(fn, kw.value)) for kw in call.keywords if tainted(kw.value)]
            text = "%s(%s)" % (self.segment(fn, call.func), ", ".join(tainted_args) if tainted_args else "...")
            kind = "carrier" if carrier else "mint"
            mech = "+".join(sorted(kinds - {"text", "exc"})) if carrier else ("+".join(sorted({t.kind for t in value})) or "enters")
            out.append(Terminal(fn, call, kind, text, self._ord_of(fn, kind, text, call), mech, set()))
        return out

    def members(self):
        """Every member in source order, its ordinal recomputed there: the n-th member of one function with the same
        operation and argument text counts from the top of the function, whatever order the walk met them in."""
        out = sorted(list(self.terminals.values()) + list(self.escapes.values()) + self.roads(),
                     key=lambda t: (self.files.index(t.fn.file), t.node.lineno, t.node.col_offset))
        seen = {}
        for t in out:
            k = (t.fn.file, t.fn.qual, t.op, t.arg_text)
            seen[k] = seen.get(k, 0) + 1
            t.ordinal = seen[k]
        return out

    def derived(self):
        """{member key: mech} over every member (terminals, carriers, mints, escapes): the view the plant harness diffs a
        scratch copy against. A terminal's key names its operation; a carrier's or a mint's names its kind."""
        return {t.key(): t.mech for t in self.members()}

    def residual(self):
        """{terminal key: mech} for every terminal that is not by-descriptor (by-path, mixed, exec-arg): the set the pin
        holds equal to RESIDUAL's keys."""
        return {t.key(): t.mech for t in self.members() if t.op not in ("carrier", "mint", "escape") and t.mech != "by-descriptor"}

    def by_descriptor(self):
        return {t.key(): t.mech for t in self.members() if t.op not in ("carrier", "mint", "escape") and t.mech == "by-descriptor"}

    def escape_lines(self):
        """Every escape as `file:line qual  text  [why]`, the printed form of what the census cannot follow."""
        return ["%s:%d %s  %s  [%s]" % (t.fn.file, t.node.lineno, t.fn.qual, t.arg_text, t.why)
                for t in sorted(self.escapes.values(), key=lambda t: (self.files.index(t.fn.file), t.node.lineno, t.node.col_offset))]

    def dir_fd_forwarding(self):
        """For every function with a `dir_fd` parameter defaulting to None whose body holds a by-path terminal: the
        call sites that do NOT pass a dir_fd, or pass None, transitively over callers that forward their own; [] means
        every road into the by-path arm passes a descriptor."""
        holes = []
        seen = set()
        todo = [fn for fn in self.fns.values() if "dir_fd" in fn.params and isinstance(fn.defaults.get("dir_fd"), ast.Constant)
                and any(t.fn is fn and t.mech == "by-path" for t in self.terminals.values())]
        while todo:
            fn = todo.pop()
            if fn in seen:
                continue
            seen.add(fn)
            for site_fn, call in self.calls_of.get((fn.file, fn.qual), []):
                v = self._bound_arg(call, fn, "dir_fd")
                if v is None or (isinstance(v, ast.Constant) and v.value is None):
                    holes.append("%s:%d %s -> %s (no dir_fd)" % (site_fn.file, call.lineno, site_fn.qual, fn.qual))
                elif isinstance(v, ast.Name) and v.id == "dir_fd" and "dir_fd" in site_fn.params:
                    todo.append(site_fn)
        return holes, sorted(f.qual for f in seen)


def derive(root=ROOT):
    return Census(root).run()


def shared_nodes(tree):
    """One expression-context or operator node of each type in `tree`, the first the walk meets (SHARED_NODE_TYPES): in a
    fresh parse these are the parser's shared instances, one per type for the whole process."""
    out = {}
    for n in ast.walk(tree):
        if isinstance(n, SHARED_NODE_TYPES):
            out.setdefault(type(n), n)
    return list(out.values())


def shared_node_attributes(nodes):
    """`Load carries _fn (Fn), _parent (Name)` for each of `nodes` that carries an attribute (these types have no fields,
    so vars() of a clean one is empty): the probe of the pin that holds the parser's shared nodes clean."""
    return ["%s carries %s" % (type(n).__name__, ", ".join("%s (%s)" % (k, type(v).__name__) for k, v in sorted(vars(n).items())))
            for n in nodes if vars(n)]


def product_modules(root=ROOT):
    """Every product module that parses as Python (kernel/, bin/, cli/, postal/), one per distinct content (bin/romp-kernel
    is a byte copy of kernel/kernel.py), as repo-relative paths."""
    import hashlib
    seen, out = set(), []
    for pat in SCAN_GLOBS:
        for p in sorted(glob.glob(str(Path(root) / pat))):
            if not os.path.isfile(p):
                continue
            try:
                data = Path(p).read_bytes()
                ast.parse(data.decode("utf-8"))
            except (SyntaxError, UnicodeDecodeError, ValueError):
                continue
            h = hashlib.sha256(data).hexdigest()
            if h in seen:
                continue
            seen.add(h)
            out.append(os.path.relpath(p, root))
    return out


def wide_census(root=ROOT):
    """The census's own method over every OTHER product module, one module at a time (its calls resolved inside the
    module): {module: terminals}. The scope pin: a syscall on a path under hosts/ is made in the three files and nowhere
    else. Escapes are not pinned here (a `hosts` dict key that reaches a call the walk cannot resolve is not a path)
    and are printed by main() for the record."""
    out = {}
    for rel in product_modules(root):
        if rel in FILES:
            continue
        c = Census(root, files=(rel,)).run()
        out[rel] = c
    return out


# The pinned list since the road was closed (the second and third addenda of round 7, 2026-09-20; the roles PERMANENT and
# FOLLOW-UP since the fourth): every by-path, mixed and exec-arg terminal at this head, keyed by file, enclosing function,
# the operation, the argument text and its ordinal in that function, with its class, its ROLE and its reason. The roles
# are the module docstring's. Paste new keys from `python3 tests/test_hosts_path_census.py --residual`; write the role
# and the reason by hand.
PERMANENT, FOLLOW_UP, HELPER, GUARD, UNREACHABLE, HANDOFF, HOST = "permanent", "follow-up", "helper", "guard", "unreachable", "handoff", "host"
ROLES = (PERMANENT, FOLLOW_UP, HELPER, GUARD, UNREACHABLE, HANDOFF, HOST)
FOLLOW_UP_ITEM = "the journal reads descend by descriptor"     # the one small-asks item the role held; landed by the fork PR that follows #814 (2026-09-21), the role EMPTY since
RESIDUAL = {
    ('kernel/host_transport.py', '_open_dir_nofollow', 'os.open', 'name', 1):
        ('mixed', GUARD, "the descent's own open: hosts/ by PATH with O_DIRECTORY|O_NOFOLLOW off the state root, <sid> by NAME under the first descriptor; the spawn, read and removal roads all enter here"),
    ('kernel/host_transport.py', '_open_dir_nofollow', 'os.lstat', 'name', 1):
        ('mixed', GUARD, "the wording of a refused open (a link or a non-directory), by path for hosts/, by name under the descriptor for <sid>; it decides nothing"),
    ('kernel/host_transport.py', 'HostTransport.connect', 'asyncio.open_unix_connection', 'self.sock_path', 1):
        ('by-path', PERMANENT, "a Unix socket is connected by the path in its address and connect(2) has no dir_fd form (a connect through /proc/self/fd or a chdir on the descriptor is a different mechanism); reached from the attach by lease, the first connect after the spawn wait and the end by lease; its precondition is a state root a peer can write, since the spawn road's helpers tighten hosts/ before the poll"),
    ('kernel/session_host.py', 'Journal._open_segment', 'open', 'self._path(first)', 1):
        ('by-path', HOST, "a journal segment opened by path under hosts/<sid>/, after the constructor's guard"),
    ('kernel/session_host.py', 'Journal._persist_gaps', 'open', 'tmp', 1):
        ('by-path', HOST, "gaps.json's temp written by path under hosts/<sid>/"),
    ('kernel/session_host.py', 'Journal._persist_gaps', 'os.replace', 'tmp', 1):
        ('by-path', HOST, "gaps.json replaced by path"),
    ('kernel/session_host.py', 'Journal._persist_gaps', 'os.unlink', 'tmp', 1):
        ('by-path', HOST, "gaps.json's temp unlinked by path on failure"),
    ('kernel/session_host.py', 'Journal._turn_boundary', 'os.unlink', 'self._path(seg)', 1):
        ('by-path', HOST, "an acknowledged segment deleted by path"),
    ('kernel/session_host.py', 'Journal.read_from', 'open', 'self._path(seg)', 1):
        ('by-path', HOST, "a segment read by path"),
    ('kernel/session_host.py', 'owner_only_dir', 'mkdir', 'd', 1):
        ('by-path', HELPER, "the mkdir by path; hosts/ for hosts_dir's callers, hosts/<sid>/ for write_spawn_spec and the host's Journal (condition 1's window)"),
    ('kernel/session_host.py', 'owner_only_dir', 'os.lstat', 'd', 1):
        ('by-path', HELPER, "the lstat by path that decides symlink, non-directory, foreign uid and loose"),
    ('kernel/session_host.py', 'owner_only_dir', 'os.chmod', 'd', 1):
        ('by-path', HELPER, "the chmod by path of a loose directory of ours; it follows a link swapped in between the lstat and this call onto any object this uid owns"),
    ('kernel/session_host.py', 'owner_only_dir', 'os.lstat', 'd', 2):
        ('by-path', HELPER, "the read-back by path"),
    ('kernel/session_host.py', 'SessionHost.__init__', 'open', 'self.spec_path', 1):
        ('by-path', HOST, "the spec opened by path with no O_NOFOLLOW before any guard: the host-side item the queue keeps (the launcher's argv contract), not this PR's"),
    ('kernel/session_host.py', 'SessionHost.log', 'open', 'self.log_path', 1):
        ('by-path', HOST, "host.log appended by path after the constructor's guard"),
    ('kernel/session_host.py', 'SessionHost._sweep_stale_temps', 'glob', 'self.sock_path.parent', 1):
        ('by-path', HOST, "the prelude's listing of hosts/ by path"),
    ('kernel/session_host.py', 'SessionHost._sweep_stale_temps', 'unlink', 'p', 1):
        ('by-path', HOST, "a dead owner's temp unlinked by path"),
    ('kernel/session_host.py', 'SessionHost._prepare_socket', 'unlink', 'self.sock_path', 1):
        ('by-path', HOST, "a dead host's published socket unlinked by path (the prelude)"),
    ('kernel/session_host.py', 'SessionHost._serve_socket', 'os.lstat', 'self.sock_path.parent', 1):
        ('by-path', GUARD, "host side: the lstat of hosts/ before the bind (round 4, extra6-1)"),
    ('kernel/session_host.py', 'SessionHost._serve_socket', 'asyncio.start_unix_server', 'str(self.sock_tmp)', 1):
        ('by-path', HOST, "the bind by path; the microseconds after the lstat above are unguarded"),
    ('kernel/session_host.py', 'SessionHost._serve_socket', 'os.chmod', 'self.sock_tmp', 1):
        ('by-path', HOST, "the temp tightened by path"),
    ('kernel/session_host.py', 'SessionHost._serve_socket', 'os.rename', 'self.sock_tmp', 1):
        ('by-path', HOST, "the publish: the temp renamed onto the published path"),
    ('kernel/session_host.py', 'SessionHost._serve_socket', 'unlink', 'self.sock_tmp', 1):
        ('by-path', HOST, "the failure arm's temp unlink"),
    ('kernel/session_host.py', 'SessionHost.run', 'write_text', 'self.dir / "identity.json"', 1):
        ('by-path', HOST, "identity.json written by path after the constructor's guard"),
    ('kernel/session_host.py', 'SessionHost.run', 'unlink', 'self.sock_path', 1):
        ('by-path', HOST, "the exit's unlink of the published socket"),
    ('kernel/sdk_backend.py', 'SdkBackend._spawn_host', 'subprocess.Popen', 'argv', 1):
        ('exec-arg', HANDOFF, "the spec path leaves the process in argv (host.stderr's descriptor as the child's stderr beside it); the host re-opens it by path in its constructor, the host-side item"),
}
# The read roads' terminals since the second addendum, each held by-descriptor: the owner question's stat of the name
# under the <sid> descriptor (_stat_name, shared by host_file_exists and read_host_file since the fifth addendum, and by
# the spawn road's host_log_mark and _open_host_log since the seventh; through the fourth it was host_file_exists's own),
# the open by name under the <sid> descriptor that the one file reader (_open_host_file, since the seventh addendum;
# read_host_file's own body through the sixth) shares with spawn.json and host.stderr (_open_file_nofollow) and its
# fdopen, the poll's stat of the published name under the hosts/ descriptor (host_sock_present), and, since the fourth
# addendum, the owner check's fstat of the descriptor that reader opened. The spawn road's host.log readers hold no
# terminal of their own since the seventh addendum: host_log_mark reads the size off _stat_name's answer and
# _open_host_log opens through _open_host_file, so the two by-descriptor terminals they had (the mark's stat by name, the
# open by name and its fdopen) and the two by-path arms listed UNREACHABLE through the sixth are gone from the derived set.
# Since the fork PR that follows #814 (2026-09-21): the orphan journal's listing, a scandir off the <sid> descriptor
# (journal_segments; the five follow-up sites it and read_journal_dir replaced asked the owner question through
# _stat_name and _open_host_file, so they add no terminal of their own beyond the scandir), and the write side's opener
# (_open_host_file_for_write: the fstat of the descriptor its open returned and the fchmod on it, which through #814 were
# host_stderr_open's and write_spawn_spec's own; write_spawn_spec's fdopen of that descriptor stays its own).
CONVERTED = (
    ('kernel/host_transport.py', '_stat_name', 'os.stat', 'name', 1),
    ('kernel/host_transport.py', '_open_file_nofollow', 'os.open', 'name', 1),
    ('kernel/host_transport.py', '_open_host_file', 'os.fstat', 'fd', 1),
    ('kernel/host_transport.py', '_open_host_file', 'os.fdopen', 'fd', 1),
    ('kernel/host_transport.py', 'host_sock_present', 'os.stat', 'name', 1),
    ('kernel/host_transport.py', 'journal_segments', 'os.scandir', 'dirs.dir', 1),
    ('kernel/host_transport.py', '_open_host_file_for_write', 'os.fstat', 'fd', 1),
    ('kernel/host_transport.py', '_open_host_file_for_write', 'os.fchmod', 'fd', 1),
    ('kernel/host_transport.py', 'write_spawn_spec', 'os.fdopen', 'fd', 1),
)


PLANTED_READERS = '''

class _PlantedReaders:
    """Eleven by-path readers under hosts/, each assembled from a part whose value is `hosts`, in the shapes the round-6
    verifiers used (extra5-1's eleven), planted for the census's self-test; never called."""
    _HOST_SEG = "hosts"
    _LEAVES = {"log": "host.log", "id": "identity.json"}

    def p01_fstring_two_steps(self, sess):
        base = f"{self.state_dir}/hosts"
        p = f"{base}/{sess.sid}/host.log"
        return open(p).read()

    def p02_join_through_variable_base(self, sess):
        base = os.path.join(str(self.state_dir), "hosts")
        return open(os.path.join(base, sess.sid, "identity.json")).read()

    def p03_single_quoted_division(self, sess):
        return (self.state_dir / 'hosts' / sess.sid / 'host.log').read_text()

    def p04_leaf_from_a_dict(self, sess):
        leaf = self._LEAVES["log"]
        return (self.state_dir / "hosts" / sess.sid / leaf).read_text()

    def _p05_dir(self, sid):
        return self.state_dir / "hosts" / sid

    def p05_helper_dir_globbed_by_caller(self, sess):
        return list(self._p05_dir(sess.sid).glob("journal-*.jsonl"))

    def p06_bytes_path_via_fsencode(self, sess):
        b = os.fsencode(str(self.state_dir)) + b"/" + b"hosts" + b"/" + sess.sid.encode() + b"/spawn.json"
        return os.stat(b)

    def p07_path_through_fsdecode(self, sess):
        b = os.path.join(os.fsencode(str(self.state_dir)), b"hosts", sess.sid.encode(), b"host.stderr")
        return open(os.fsdecode(b), "rb").read()

    def _p08_session_home(self, sid):
        return Path(self.state_dir, "hosts", sid)

    def p08_renamed_helper(self, sess):
        return (self._p08_session_home(sess.sid) / "spawn.json").read_text()

    def p09_percent_one_segment_per_part(self, sess):
        p = "%s/%s/%s/%s" % (self.state_dir, "hosts", sess.sid, "host.log")
        return open(p).read()

    def p10_path_from_a_splatted_tuple(self, sess):
        parts = (str(self.state_dir), "hosts", sess.sid, "host.log")
        return open(Path(*parts)).read()

    def p11_full_literal_wrapped_across_two_lines(self, sess):
        p = (f"{self.state_dir}/hosts"
             f"/{sess.sid}/host.log")
        return open(p).read()
'''

# The round-7 verifier's ten shapes (q01 to q10, recreated from the finding's description of each) and the five extras
# named beside them (x01 to x05), appended to a scratch copy of kernel/sdk_backend.py; q05's tuple is assembled by a
# helper appended to kernel/session_host.py (PLANTED_VERIFIER_HOST). At the round-7 commit the census found q05, q06, q07
# and q10 and missed the other six in silence; the addendum's follow rules find every one, and x04 (a callable handed to
# `map` beside the path) is the one shape that is an escape rather than a terminal: the walk cannot see `map` apply it.
PLANTED_VERIFIER = '''

class _Q814Plants:
    """The round-7 verifier's ten shapes and five extras; never called."""
    _SEG = "hosts"

    def q01_fstring_via_class_body_constant(self, sess):
        base = f"{self.state_dir}/{self._SEG}"
        p = f"{base}/{sess.sid}/host.log"
        return open(p).read()

    def q02_join_through_a_default_parameter(self, sess, seg="hosts"):
        base = os.path.join(str(self.state_dir), seg)
        return open(os.path.join(base, sess.sid, "identity.json")).read()

    @property
    def q03_home(self):
        return self._q03_home

    def q03_bind_the_property(self, sess):
        self._q03_home = self.state_dir / "hosts" / sess.sid

    def q03_division_from_a_property(self, sess):
        return (self.q03_home / "host.log").read_text()

    def q04_name_from_a_setdefault_dict(self, sess):
        segs = {}
        segs.setdefault("seg", "hosts")
        seg = segs["seg"]
        return open(os.path.join(str(self.state_dir), seg, sess.sid, "host.log")).read()

    def q05_tuple_unpacked_across_files(self, sess):
        d, leaf = _ht().sh.q05_host_log_parts(self.state_dir, sess.sid)
        return open(os.path.join(d, leaf)).read()

    def q06_bytearray_augmented(self, sess):
        b = bytearray(os.fsencode(str(self.state_dir)))
        b += b"/hosts/" + sess.sid.encode() + b"/spawn.json"
        return os.stat(bytes(b))

    def q07_fsdecode_of_a_percent_bytes_path(self, sess):
        b = b"%s/hosts/%s/host.stderr" % (os.fsencode(str(self.state_dir)), sess.sid.encode())
        return open(os.fsdecode(b), "rb").read()

    def q08_path_through_a_lambda(self, sess):
        pick = lambda s: self.state_dir / "hosts" / s / "host.log"  # noqa: E731
        return open(pick(sess.sid)).read()

    def q09_store_on_an_untyped_receiver(self, sess):
        sess._q814_home = self.state_dir / "hosts" / sess.sid

    def q09_read_from_the_untyped_receiver(self, sess):
        return (sess._q814_home / "identity.json").read_text()

    def q10_literal_split_across_the_line_break(self, sess):
        p = ("%s/ho"
             "sts/%s/host.log") % (self.state_dir, sess.sid)
        return open(p).read()

    def x01_nested_def(self, sess):
        def home():
            return self.state_dir / "hosts" / sess.sid
        return (home() / "host.log").read_text()

    def x02_open_through_a_double_splat(self, sess):
        kw = {"file": self.state_dir / "hosts" / sess.sid / "host.log"}
        return open(**kw).read()

    def x03_re_sub_on_a_template(self, sess):
        p = re.sub(r"SID", sess.sid, f"{self.state_dir}/hosts/SID/host.log")
        return open(p).read()

    def x04_map_open_over_paths(self, sess):
        return [f.read() for f in map(open, [self.state_dir / "hosts" / sess.sid / "host.log"])]

    def x05_setattr_then_attribute_read(self, sess):
        setattr(self, "_x05_home", self.state_dir / "hosts" / sess.sid)
        return (self._x05_home / "host.log").read_text()
'''

PLANTED_VERIFIER_HOST = '''

def q05_host_log_parts(state_dir, sid):
    """The round-7 verifier's q05: a (directory, leaf) tuple assembled here and unpacked in kernel/sdk_backend.py."""
    return (os.path.join(str(state_dir), "hosts", sid), "host.log")
'''

# Three shapes the builder wrote down BEFORE widening the follow rules (the round-7 addendum's own check that the
# rules were written by binding form and not to the ten above): a module-level dict mutated by a subscript store from
# one method without a `global` statement and read in another; a class-body constant read through `type(self)` and
# `self.__class__`; a path yielded by a @contextlib.contextmanager method and bound by a with-target.
PLANTED_ADDENDUM = '''

_Q814_HOMES = {}


class _Q814Addendum:
    """The builder's three shapes, written before the rules; never called."""
    _SEG2 = "hosts"

    def m01_store_into_a_module_dict_by_subscript(self, sess):
        _Q814_HOMES[sess.sid] = self.state_dir / "hosts" / sess.sid

    def m01_read_from_the_module_dict(self, sess):
        return open(_Q814_HOMES[sess.sid] / "host.log").read()

    def m02_class_constant_through_type_of_self(self, sess):
        return (self.state_dir / type(self)._SEG2 / sess.sid / "host.log").read_text()

    def m02_class_constant_through_dunder_class(self, sess):
        return (self.state_dir / self.__class__._SEG2 / sess.sid / "identity.json").read_text()

    @contextlib.contextmanager
    def _m03_home(self, sid):
        yield self.state_dir / "hosts" / sid

    def m03_with_target_from_a_contextmanager(self, sess):
        with self._m03_home(sess.sid) as home:
            return open(home / "host.log").read()
'''


def plant(base_census, appendices):
    """Run the census over a scratch copy of the three files with `appendices` ({file: source}) appended, and return
    ({plant method prefix: [(op, mech)]}, [member keys new outside the planted classes, escapes excepted], [escape lines
    inside them], [escape lines outside them]): the instrument's self-test harness, shared by the plant cases below."""
    import shutil
    import tempfile
    scratch = tempfile.mkdtemp(prefix="hosts-census-")
    try:
        for f in FILES:
            os.makedirs(os.path.dirname(os.path.join(scratch, f)), exist_ok=True)
            shutil.copy(os.path.join(ROOT, f), os.path.join(scratch, f))
        for f, text in appendices.items():
            with open(os.path.join(scratch, f), "a") as fh:
                fh.write(text)
        base = set(base_census.derived())
        c = Census(scratch).run()
        found, elsewhere, escapes, outside = {}, [], [], []
        planted = ("_PlantedReaders.", "_Q814Plants.", "_Q814Addendum.")
        for t in c.members():
            if t.key() in base:
                continue
            line = "%s:%d %s  %s  [%s]" % (t.fn.file, t.node.lineno, t.fn.qual, t.arg_text, t.why)
            if t.fn.qual.startswith(planted):
                name = t.fn.qual.split(".")[1]
                prefix = name.split("_")[0]
                found.setdefault(prefix, []).append((t.op, t.mech))
                if t.op == "escape":
                    escapes.append(line)
            elif t.op == "escape":
                outside.append(line)
            elif not t.fn.qual.startswith(("module level", "q05_host_log_parts")):
                elsewhere.append(t.key())
        return found, elsewhere, escapes, outside
    finally:
        shutil.rmtree(scratch, True)


class HostsPathCensus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.census = derive()

    def test_no_other_product_module_makes_a_syscall_on_a_path_under_hosts(self):
        outside = {rel: [(t.node.lineno, t.fn.qual, t.op, t.arg_text) for t in c.terminals.values()]
                   for rel, c in wide_census().items() if c.terminals}
        self.assertEqual(outside, {}, "a module outside the three uses a path under hosts/: %r" % (outside,))

    def test_no_by_path_syscall_on_a_hosts_path_remains_except_the_listed_sites(self):
        """The pin since the road was closed (the third addendum): the derived set of terminals that are not by-descriptor
        (by-path, mixed, exec-arg) equals RESIDUAL's keys, class for class; a by-path syscall on a path under hosts/
        outside the list is a new road or a read moved back onto a path; a listed one that is gone or now takes a
        descriptor is removed from the list. The read roads' terminals are by-descriptor (CONVERTED). Every entry has a
        role of the seven and a reason; the permanent set is exactly the connect (the fourth addendum: closed as an open
        item, by-path for as long as the transport is a Unix socket); the follow-up set is EMPTY (the fork PR that
        follows #814, 2026-09-21: the one queued item landed, its five sites converted, and the assertion that held the
        set at those five became `assertEqual(follow_up, [])`, so a by-path journal read written back under hosts/ is
        an unlisted site here and a listed one under this role is a refill of a landed item, both red)."""
        derived = {t.key(): t.mech for t in self.census.members() if t.op not in ("carrier", "mint", "escape")}
        self.assertGreater(len(derived), 0, "the census found no syscall on a path under hosts/: the seed rule is broken")
        residual = self.census.residual()
        new = sorted(k for k in residual if k not in RESIDUAL)
        gone = sorted(k for k in RESIDUAL if k not in residual)
        self.assertEqual(new, [], "a by-path syscall on a path under hosts/ that RESIDUAL does not list: a new road, or a read moved "
                                  "back onto a path; convert it, or list it by role with its reason (`--residual` prints the key): %r" % (new,))
        self.assertEqual(gone, [], "a listed site is gone or now takes a descriptor: remove it from RESIDUAL: %r" % (gone,))
        changed = sorted((k, RESIDUAL[k][0], residual[k]) for k in RESIDUAL if RESIDUAL[k][0] != residual[k])
        self.assertEqual(changed, [], "a listed site changed class: %r" % (changed,))
        for k in CONVERTED:
            self.assertEqual(derived.get(k), "by-descriptor", "%r: a read the second addendum moved onto the descent is not by-descriptor" % (k,))
        for k, (mech, role, why) in RESIDUAL.items():
            self.assertIn(role, ROLES, k)
            self.assertTrue(why, "%r: a reason" % (k,))
            if role == HOST:
                self.assertEqual(k[0], "kernel/session_host.py", "%r: the host's own road is the host's module" % (k,))
            if role in (PERMANENT, FOLLOW_UP):
                self.assertEqual(mech, "by-path", "%r: a permanent or follow-up site is a by-path read" % (k,))
            if role == FOLLOW_UP:
                self.assertTrue(why.startswith(FOLLOW_UP_ITEM + ":"), "%r: a follow-up site's reason names the one item" % (k,))
            if role == HANDOFF:
                self.assertEqual(mech, "exec-arg")
        permanent = sorted(k for k, v in RESIDUAL.items() if v[1] == PERMANENT)
        self.assertEqual([k[1] for k in permanent], ["HostTransport.connect"],
                         "the permanent residual is the connect and nothing else: connect(2) has no dir_fd form")
        follow_up = sorted(k for k, v in RESIDUAL.items() if v[1] == FOLLOW_UP)
        self.assertEqual(follow_up, [], "the follow-up role is empty since its one item landed (the journal reads descend by "
                                        "descriptor, the fork PR that follows #814): a by-path journal read under hosts/ is converted, "
                                        "not listed: %r" % (follow_up,))
        self.assertEqual([k for k in derived if k[1] in ("read_journal_dir", "journal_segments", "journal_has_tail") and derived[k] != "by-descriptor"], [],
                         "the orphan reader's terminals are all by-descriptor")

    def test_the_census_leaves_the_parsers_shared_nodes_clean(self):
        """The parser hands out ONE instance of each expression context and each operator per process, shared by every
        tree it parses; the probe reads them from PARSES (the `ctx` of a parsed Name, the `op` of a parsed BinOp, BoolOp,
        UnaryOp or Compare) and asserts the instance of each type is the same object across two separate parses, since a
        constructed `ast.Load()` is fresh and unshared and would read clean beside a polluted parser instance. The walk's
        three marks, `_fn` (_index), `_lfn` (_register_nested) and `_parent` (run), skip those nodes: written there they
        rode on every tree any later module in the process parsed, and a reader that copied a node with copy.deepcopy
        followed `_parent` into this census's whole graph, which CI's diagnostic run 35740276523 read back on the
        thread-stop census, the module after this one in the serial cell (a RecursionError inside copy.py on 3.10 and
        3.11, a copy of the graph costing minutes on 3.12). After setUpClass's census (the wide census and the plants walk
        by the same code), the parser's Load, Store and Del and one operator of each family carry no attribute. THE RED,
        three times on the PARSED instances, with the restore registered as a cleanup BEFORE the first write so a failing
        plant leaves the process clean: each old write in turn, unguarded, runs over a fresh parse of the probe text (whose
        context and operator nodes are the parser's shared instances), a THIRD parse then carries that mark on every one of
        its context and operator nodes, the probe names it on each, and the restore puts every instance back to exactly
        the state found, asserted clean before the next mark."""
        first, second = shared_nodes(ast.parse(_SHARED_PROBE)), shared_nodes(ast.parse(_SHARED_PROBE))
        self.assertEqual(sorted(type(n).__name__ for n in first), ["Add", "And", "Del", "Load", "Lt", "Store", "USub"])
        self.assertEqual([id(n) for n in first], [id(n) for n in second],
                         "the probe is not reading a shared instance: two parses of one text gave different context or operator objects")
        self.assertIs(first[[type(n) for n in first].index(ast.Load)], ast.parse("q").body[0].value.ctx, "the Load of any parsed Name is that instance")
        shared = first
        self.assertEqual(shared_node_attributes(shared), [],
                         "the census wrote on a node the parser shares with every tree of the process: a mark written in _index "
                         "or run without the SHARED_NODE_TYPES guard, or a new write on an AST node; guard it, or keep the datum "
                         "in a side table keyed by id(node)")
        held = [(n, dict(vars(n))) for n in shared]

        def restore():
            for n, was in held:
                for k in list(vars(n)):
                    if k not in was:
                        delattr(n, k)
                for k, v in was.items():
                    setattr(n, k, v)
        self.addCleanup(restore)                             # BEFORE the first write: exactly the state found
        owner = object()

        def write_fn(tree):                                  # _index's mark, as it stood unguarded
            for node in ast.walk(tree):
                node._fn = owner

        def write_lfn(tree):                                 # _register_nested's mark, were it to reach a shared node
            for node in ast.walk(tree):
                node._lfn = owner

        def write_parent(tree):                              # run's mark, as it stood unguarded
            for node in ast.walk(tree):
                for child in ast.iter_child_nodes(node):
                    child._parent = node
        for mark, write, holder in (("_fn", write_fn, r"object"), ("_lfn", write_lfn, r"object"),
                                    ("_parent", write_parent, r"Name|BinOp|BoolOp|UnaryOp|Compare")):
            write(ast.parse(_SHARED_PROBE))                  # over a fresh parse: its context and operator nodes are the parser's
            later = shared_nodes(ast.parse(_SHARED_PROBE))   # a later parse carries the mark: the mechanism
            self.assertEqual([id(n) for n in later], [id(n) for n in shared], mark)
            lines = shared_node_attributes(later)
            self.assertEqual([line.split(" carries ")[0] for line in lines], [type(n).__name__ for n in shared], "%s: every shared node is named" % mark)
            for line in lines:
                self.assertRegex(line, r" carries %s \((%s)\)$" % (mark, holder))
            restore()
            self.assertEqual(shared_node_attributes(shared), [], "%s: the restore left the parser's instances exactly as found" % mark)

    def test_no_use_escapes_the_walk(self):
        """The six forms the escape rule covers (the module docstring, CLASSIFY) are printed as escapes by file and line;
        over the real tree that list is empty. What this holds: no value the walk follows reaches one of those six forms
        in these files. What it does not hold: that every form is one of the six (the retracted promise; the module
        docstring says what a silent miss costs now)."""
        self.assertEqual(self.census.escape_lines(), [], "an escape is a value the census could not follow at one of the six forms; classify it or follow it")

    def test_the_eleven_planted_reader_shapes_are_all_found(self):
        """The instrument's own check, the shapes of round 6's plants (extra5-1's eleven: an f-string in two steps, a
        join through a variable-held base, single-quoted division, a leaf from a dict, a helper's directory globbed by
        the caller, a bytes path, a path through os.fsdecode, a renamed helper, %-formatting one segment per part, a
        splatted tuple, and the full literal wrapped across two lines), appended to a scratch copy of kernel/sdk_backend.py:
        the census over the copy finds a by-path terminal in every one, and nothing else new outside them. The published
        grep found 0 of 11; a narrowing of the seed or the follow rules reds here."""
        found, elsewhere, _, outside = plant(self.census, {"kernel/sdk_backend.py": PLANTED_READERS})
        self.assertEqual((elsewhere, outside), ([], []), "the plants changed the census outside their own class")
        missing = ["p%02d" % i for i in range(1, 12) if not any(mech == "by-path" for _, mech in found.get("p%02d" % i, []))]
        self.assertEqual(missing, [], "planted by-path readers the census did not find: %r (found %r)" % (missing, found))

    def test_the_ten_shapes_the_round_7_verifier_planted_are_found_and_the_extras_are_found_or_escape(self):
        """The round-7 verifier's ten shapes (a class-body constant through self, a default parameter, a property, a
        setdefault-fed dict, a tuple unpacked across the two files, a bytearray grown by +=, os.fsdecode of a %-built
        bytes path, a lambda, a store on a receiver the walk cannot type, a literal split across a line break): the
        census at the round-7 commit found 4 of the 10 and missed the rest in silence. Each is now a by-path terminal;
        of the five extras, four are terminals and the fifth, `map(open, [...])`, is an ESCAPE (the callable is applied
        where the walk cannot see, and the walk says so rather than dropping the path). No terminal, carrier or mint
        changes outside the planted classes and the host-side helper; what q09's store on a receiver the walk cannot
        type DOES change outside them is printed: every dynamic attribute read on such a receiver in the tree
        (`getattr(exc, attr, None)` and its siblings) becomes an escape saying it may be the reader of that store,
        which over the real tree, where no path is stored that way, none of them is."""
        found, elsewhere, escapes, outside = plant(self.census, {"kernel/sdk_backend.py": PLANTED_VERIFIER,
                                                                 "kernel/session_host.py": PLANTED_VERIFIER_HOST})
        self.assertEqual(elsewhere, [], "the plants changed the census outside their own class")
        self.assertGreater(len(outside), 0, "q09's untyped store makes the tree's dynamic reads on untyped receivers escapes")
        for line in outside:
            self.assertIn("a dynamic attribute read on a receiver the walk cannot type", line, line)
        missing = ["q%02d" % i for i in range(1, 11) if not any(mech == "by-path" for _, mech in found.get("q%02d" % i, []))]
        self.assertEqual(missing, [], "the verifier's shapes the census did not find: %r (found %r)" % (missing, found))
        missing = ["x%02d" % i for i in (1, 2, 3, 5) if not any(mech == "by-path" for _, mech in found.get("x%02d" % i, []))]
        self.assertEqual(missing, [], "extras the census did not find: %r (found %r)" % (missing, found))
        missing = []
        self.assertEqual(missing, [], "extras the census did not find: %r (found %r)" % (missing, found))
        self.assertEqual([mech for _, mech in found.get("x04", [])], ["escape"],
                         "map(open, paths) is the one extra the walk cannot follow, and it is printed, not dropped: %r" % (found.get("x04"),))
        self.assertEqual(len(escapes), 1, escapes)
        self.assertIn("a callable (open) applied outside the walk", escapes[0])

    def test_three_shapes_written_before_the_rules_were_widened_are_found(self):
        """The addendum's own check that the rules were written by binding form: a module-level dict mutated by a
        subscript store from one method, with no `global`, and read in another (a store into a name the method does not
        bind lands in the scope that does); a class-body constant read through `type(self)` and `self.__class__`; a path
        yielded by a @contextlib.contextmanager method and bound by `with ... as home`. Each a by-path terminal."""
        found, elsewhere, escapes, outside = plant(self.census, {"kernel/sdk_backend.py": PLANTED_ADDENDUM})
        self.assertEqual((elsewhere, outside), ([], []), "the plants changed the census outside their own class")
        self.assertEqual(escapes, [], "an escape among the builder's three: the rule for its form is missing")
        missing = ["m%02d" % i for i in range(1, 4) if not any(mech == "by-path" for _, mech in found.get("m%02d" % i, []))]
        self.assertEqual(missing, [], "the builder's shapes the census did not find: %r (found %r)" % (missing, found))
        self.assertEqual(sum(1 for _, mech in found.get("m02", []) if mech == "by-path"), 2, "both reads of the class constant: %r" % (found.get("m02"),))

    def test_each_of_the_six_escape_forms_is_printed_as_an_escape(self):
        """The escape rule, one shape per form it covers (five of the six here; the sixth, a dynamic read on an untyped
        receiver while a path is stored that way, is the ten-shapes case's q09): a path handed to a call the walk cannot
        resolve; a method it does not know on a path-tainted receiver; a callable applied outside it beside a path; a
        store under a name it cannot read; a decorator it does not know on a function returning a path. Each is printed
        with its form and counted. A form outside the six is a silence (the module docstring); this case pins the rule's
        reach, not its completeness."""
        src = '''

def _q814_unknown_decorator(f):
    return f


class _Q814Escapes:
    def e01_call_the_walk_cannot_resolve(self, sess):
        return _q814_elsewhere(self.state_dir / "hosts" / sess.sid)

    def e02_unknown_method_on_a_tainted_receiver(self, sess):
        return (self.state_dir / "hosts" / sess.sid).q814_unknown_method()

    def e03_callable_applied_outside_the_walk(self, sess):
        return sorted([self.state_dir / "hosts" / sess.sid], key=os.path.getmtime)

    def e04_store_under_a_dynamic_name(self, sess, name):
        setattr(self, name, self.state_dir / "hosts" / sess.sid)

    @_q814_unknown_decorator
    def e05_decorated_minter(self, sess):
        return self.state_dir / "hosts" / sess.sid
'''
        found, elsewhere, escapes, outside = plant(self.census, {"kernel/sdk_backend.py": src.replace("_Q814Escapes", "_Q814Plants")})
        self.assertEqual((elsewhere, outside), ([], []), "the plants changed the census outside their own class")
        for i in range(1, 6):
            self.assertEqual([mech for _, mech in found.get("e%02d" % i, [])], ["escape"], "e%02d: %r" % (i, found.get("e%02d" % i)))
        forms = ("cannot resolve", "does not know, called on a tainted receiver", "applied outside the walk",
                 "a name the walk cannot read", "a decorator the walk does not know")
        for form, line in zip(forms, sorted(escapes)):
            self.assertIn(form, line)

    def test_the_views_are_idempotent_and_a_holder_typed_down_a_chain_of_untainted_functions_reaches_its_last_reader(self):
        """The instrument's own fixpoint covers the HOLDER types (the seventh addendum, 2026-09-20; the module docstring's
        HISTORY): on a fresh census every name the fixpoint typed as a holder of descriptors (a HostDirs, a Journal, a
        SessionHost, a HostTransport: the classes whose attributes carry taint, the types the carrier classification and
        the attribute reads depend on) is typed the same after members() ran, members() answers the same keys twice, and
        the HostDirs the spawn road hands down four functions that carry no taint of their own (_host_transport_for,
        _refused_launch_log, _file_refused_launch_context, host_log_rows) is typed at the last of them by the fixpoint
        itself. What the view may still bind lazily, named so it is not mistaken for coverage: a parameter's NON-holder
        type (two `sess` parameters typed SdkSession at this head, by the tags() of a call the fixpoint did not re-walk
        for); no member depends on those, which the key equality holds. Red with the holder-typed liveness dropped from
        run(): members() binds host_log_rows's `dirs` on its first call (the fixpoint had not), and the two views differ
        on that member (a mint with no tainted argument, then a carrier of the holder)."""
        c = derive()
        holders = {cls for (cls, a), tags in c.attr.items() if tags}
        self.assertIn("HostDirs", holders)
        typed = lambda: {k: v for k, v in c.var_type.items() if any(t in holders for t in v)}
        before = typed()
        keys1 = sorted(t.key() for t in c.members())
        after = typed()
        keys2 = sorted(t.key() for t in c.members())
        self.assertEqual(before, after, "members() typed a name as a holder that the fixpoint had not: the walk stopped short of it")
        self.assertEqual(keys1, keys2, "the view is not idempotent")
        self.assertGreater(len(keys1), 0)
        self.assertEqual(c.var_type.get(("kernel/host_transport.py", "host_log_rows", "dirs")), ("HostDirs",),
                         "the holder handed down the spawn road's chain is typed at its last reader by the fixpoint")

    def test_no_reader_has_a_by_path_fallback_arm_and_the_forwarding_analysis_would_report_one(self):
        """Through the sixth addendum two readers (_open_host_log, host_log_mark) kept a by-path arm for a call with no
        descriptor (dir_fd None), listed UNREACHABLE and held so by this pin's predecessor, which asserted that every road
        into such an arm passes a descriptor (six functions forwarded one). The seventh addendum (2026-09-20) removed both
        arms with the readers' conversion (they take the held HostDirs, and a call with none is a TypeError, not a path),
        so over this tree the analysis finds no function of that shape and no hole: both lists empty. That the analysis
        still SEES the shape, so the empty answer is a finding and not a broken instrument, is shown on a scratch copy of
        the three files with one planted at the end of kernel/host_transport.py: a dir_fd=None fallback arm opening
        host.log by path, and a caller passing no descriptor; the function is listed and the caller is the one hole."""
        import shutil
        import tempfile
        holes, fns = self.census.dir_fd_forwarding()
        self.assertEqual((fns, holes), ([], []), "a reader with a dir_fd=None fallback arm is back, or a road reaches one "
                                                 "with no descriptor: give it the held HostDirs, as the seventh addendum did: %r %r" % (fns, holes))
        src = '''

def _q814_by_path_arm(state_dir, sid, dir_fd=None):
    if dir_fd is None:
        return open(host_dir(state_dir, sid) / "host.log", "rb").read()
    return os.open("host.log", os.O_RDONLY, dir_fd=dir_fd)


def _q814_no_descriptor(state_dir, sid):
    return _q814_by_path_arm(state_dir, sid)
'''
        scratch = tempfile.mkdtemp(prefix="hosts-census-")
        self.addCleanup(shutil.rmtree, scratch, True)
        for f in FILES:
            os.makedirs(os.path.dirname(os.path.join(scratch, f)), exist_ok=True)
            shutil.copy(os.path.join(ROOT, f), os.path.join(scratch, f))
        with open(os.path.join(scratch, "kernel/host_transport.py"), "a") as fh:
            fh.write(src)
        holes, fns = Census(scratch).run().dir_fd_forwarding()
        self.assertEqual(fns, ["_q814_by_path_arm"], "the planted fallback arm is the one function of that shape: %r" % (fns,))
        self.assertEqual(len(holes), 1, holes)
        self.assertIn("_q814_no_descriptor -> _q814_by_path_arm (no dir_fd)", holes[0])


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    c = derive(Path(args[0]) if args else ROOT)
    if "--residual" in sys.argv:
        # the pinned view as Python, for pasting into RESIDUAL (each entry's role and reason written by hand)
        for t in c.members():
            if t.op not in ("carrier", "mint", "escape") and t.mech != "by-descriptor":
                print("    %r:\n        (%r, ROLE, \"why\")," % (t.key(), t.mech))
        return
    print("SEEDS")
    for _, t in sorted(c.seeds, key=lambda x: (c.files.index(x[1].file), x[1].line)):
        print("  %s %s:%d %s  %s" % (t.kind, t.file, t.line, t.qual, t.text))
    print("MEMBERS")
    for t in c.members():
        print("%s:%d %s  %s(%s) #%d  [%s]%s" % (t.fn.file, t.node.lineno, t.fn.qual, t.op, t.arg_text, t.ordinal, t.mech,
                                               ("  " + t.why) if t.why else ""))
        for o in sorted(set(t.origins), key=lambda o: (o.file, o.line)):
            print("      <- %s %s:%d %s  %s #%d" % (o.kind, o.file, o.line, o.qual, o.text, o.ordinal))
    print("RESIDUAL (every terminal that is not by-descriptor, with its role from the pin; UNLISTED reds the census)")
    by_role = {}
    for t in c.members():
        if t.op in ("carrier", "mint", "escape") or t.mech == "by-descriptor":
            continue
        mech, role, why = RESIDUAL.get(t.key(), (t.mech, "UNLISTED", "not in RESIDUAL"))
        by_role[role] = by_role.get(role, 0) + 1
        print("  %s:%d %s  %s(%s) #%d  [%s]  %s: %s" % (t.fn.file, t.node.lineno, t.fn.qual, t.op, t.arg_text, t.ordinal, t.mech, role, why))
    print("BY-DESCRIPTOR")
    for t in c.members():
        if t.op not in ("carrier", "mint", "escape") and t.mech == "by-descriptor":
            print("  %s:%d %s  %s(%s) #%d%s" % (t.fn.file, t.node.lineno, t.fn.qual, t.op, t.arg_text, t.ordinal,
                                                "  CONVERTED" if t.key() in CONVERTED else ""))
    print("ESCAPES (the six forms the rule covers, by file and line; [] over this tree by pin)")
    for line in c.escape_lines():
        print("  " + line)
    roads = c.roads()
    residual = c.residual()
    print("terminals: %d, by-descriptor: %d, residual: %d (%s), escapes: %d, carriers: %d, mints: %d, seeds: %d"
          % (len(c.terminals), len(c.by_descriptor()), len(residual),
             ", ".join("%s %d" % (r, by_role.get(r, 0)) for r in ROLES + tuple(sorted(set(by_role) - set(ROLES)))),
             len(c.escapes), sum(1 for r in roads if r.op == "carrier"), sum(1 for r in roads if r.op == "mint"), len(c.seeds)))
    holes, fns = c.dir_fd_forwarding()
    print("dir_fd fallback arms: %s; holes: %s" % (fns, holes))
    if "--wide" in sys.argv:
        for rel, wc in wide_census(Path(args[0]) if args else ROOT).items():
            if wc.terminals or wc.escapes or wc.seeds:
                print("WIDE %s: terminals %d, escapes %d, seeds %d" % (rel, len(wc.terminals), len(wc.escapes), len(wc.seeds)))
                for t in list(wc.terminals.values()) + list(wc.escapes.values()):
                    print("  %s:%d %s  %s(%s) [%s]" % (t.fn.file, t.node.lineno, t.fn.qual, t.op, t.arg_text, t.mech))
    if "--plants" in sys.argv:
        for label, app in (("round 6 (p01-p11)", {"kernel/sdk_backend.py": PLANTED_READERS}),
                           ("round 7 verifier (q01-q10, x01-x05)", {"kernel/sdk_backend.py": PLANTED_VERIFIER, "kernel/session_host.py": PLANTED_VERIFIER_HOST}),
                           ("addendum (m01-m03)", {"kernel/sdk_backend.py": PLANTED_ADDENDUM})):
            found, elsewhere, escapes, outside = plant(c, app)
            print("PLANTS %s: %s; elsewhere %r" % (label, ", ".join("%s=%s" % (k, "/".join(sorted({m for _, m in v}))) for k, v in sorted(found.items())), elsewhere))
            for e in escapes:
                print("  escape " + e)
            for e in outside:
                print("  escape outside the plants " + e)


if __name__ == "__main__":
    main()
