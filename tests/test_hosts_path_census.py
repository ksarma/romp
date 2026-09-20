#!/usr/bin/env python3
"""The census of every use of a path under `hosts/`, derived by ORIGIN over the three modules that mint one (round 7 of
fork PR #814's review, 2026-09-20; the round-6 rulings' condition 2).

WHY BY ORIGIN. Through round 6 the PR's record enumerated the residual (the reads under hosts/ that still take a path
before any descriptor guard) with a line grep over kernel/sdk_backend.py, widened three times to the spellings each
round's verifier had used. The round-6 verifiers planted eleven by-path readers under hosts/, every one assembled from a
part whose value is `hosts`, and the published command found none of them; in the tree it also missed the binding of
spawn.json's path in the very function it censused and the line that hands that path to the host process. A grep over
spellings cannot carry a claim about paths. This census follows VALUES: it seeds on the literal segment and follows the
value wherever the code carries it, so a reader is found by what it reads, not by how its line is spelled.

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
  GROW, to a fixpoint. The taint (a set of origin tags, each the seed's file, line and text) flows through assignment
  and augmented assignment (a name, a tuple target, an attribute store `self.x = v`, which taints `x` for every reader
  of `self.x` in that class, a subscript store into a name or an attribute), the with-target and the for-target, into
  containers (a list, tuple, set or dict literal holding it, `.append`, `.extend`, `.add`, `.update` on a name or an
  attribute) and out of them (a subscript, `.get`, `.pop`, a splat), through the pure conversions (`str`, `repr`,
  `bytes`, `format`, `os.fspath`, `os.fsencode`, `os.fsdecode`, `Path`, `PurePath`, `os.path.join`, `dirname`,
  `abspath`, `normpath`, `.encode`, `.decode`, `.format`, `.join`, `.strip`, `/`, `+`, `%`, an f-string, `.parent`,
  `.parents`, `.parts`, `.with_name`, `.with_suffix`, `.joinpath`, `.relative_to`, a conditional expression, a walrus,
  a comprehension), into a callee's parameters from every call site (positional or keyword, context-insensitively: a
  parameter tainted at any site is tainted everywhere, the safe direction) and out of a callee's return to every call
  site, with the call itself added as an origin tag (so a terminal names the road that minted its path, not only the
  helper's body), through a parameter that is called (`log(...)`) to the callables its call sites bind, and out of a
  read that yields paths (`glob`, `rglob`, `iterdir`, `scandir` on a path). A leaf-only read (`.name`, `.stem`,
  `.suffix`) drops the taint: a bare file name cannot reach outside the directory it is used in. A second kind, `fd`,
  seeds at every `os.open` whose path is tainted or whose dir_fd is, and flows the same way (HostDirs' two descriptors
  reach every `dir_fd=dirs.dir` through the attribute store in its __init__); the return of a terminal read (the bytes
  of a file, a stat result) is not tainted.
  CLASSIFY every TERMINAL, a call that takes the value at a position where the operating system reads it: `open`, the
  path-taking os and os.path functions, the Path methods, shutil, `asyncio.open_unix_connection`, `start_unix_server`,
  the subprocess constructors. `by-descriptor`: a `dir_fd` keyword, or the first argument of fstat, fchmod, fdopen,
  scandir or write, carries `fd` taint, and a subprocess's stdin, stdout or stderr keyword too. `by-path`: a path
  position carries `path` or `text` taint and no descriptor does. `exec-arg`: a subprocess's argv carries the path. And
  `escape`: a `path`-tainted value handed to a call the walk cannot resolve to a function of the three files, a pure
  conversion, a container operation or a data sink (a logger, an exception's message, a file's `.write`, `json.dumps`),
  reported by site, never dropped: a value the census cannot follow is a finding, not a silence. A `text`-tainted value
  at such a call is a message (that is what tells the two kinds apart at the use) and is not reported.
  PIN. `EXPECTED` below is the published list: every terminal at this head, keyed by file, enclosing function, the
  operation, the argument's text and its ordinal in that function (never a line number, which main's insertions move),
  with the mechanical class the census derived and, for the reader, the road it sits on and whether the round's ruling
  counts it as residual. The test holds the derived set equal to it: a new terminal, a lost one, one whose class
  changed, or a changed set of origins reds; and the expected set is non-empty. Run the module directly to print the
  list with line numbers at the head it reads.
  WHAT THE CENSUS CANNOT SEE, from its own follow rules and nothing else: (1) a segment not spelled as the literal
  (`"ho" + "sts"`, a value read from a file or an environment variable, a bytes segment split across two constants);
  (2) a value that leaves the process by any road but the argv it stops at (an environment variable, a socket frame,
  stdin, a file's content; the spec's `state_dir` field is one: the host re-seeds by the literal, so its `hosts/` under
  that root is seen, and the field's own value is a root, not a path under hosts/); (3) a syscall made by code outside
  the three files (kernel/kernel.py, a C extension, a library called with a path the walk already classed as an
  escape); (4) a receiver the walk cannot type (`sess._host.something(p)`: an escape when p is path-tainted, a silence
  when it is a plain name); (5) a path reassembled from a leaf name and an untainted base (`base / sock.name`) after
  `.name` dropped the taint; (6) control flow: the walk is flow-insensitive within a function, so it reports a use on a
  road a guard makes unreachable exactly as it reports a live one (the dir_fd=None arms of the readers are that shape;
  a second pin below holds, transitively over their in-file callers, that every caller passes a dir_fd that is not
  None, which is the argument for "unreachable today", made by the census rather than by a sentence).
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
PURE_FUNCS = {"str", "repr", "bytes", "format", "os.fspath", "os.fsencode", "os.fsdecode", "Path", "PurePath",
              "PurePosixPath", "pathlib.Path", "os.path.join", "os.path.dirname", "os.path.abspath", "os.path.normpath",
              "os.path.expanduser", "list", "tuple", "set", "frozenset", "sorted", "reversed", "enumerate", "zip",
              "dict", "iter", "next", "filter", "map"}
PURE_METHODS = {"encode", "decode", "format", "join", "strip", "rstrip", "lstrip", "lower", "upper", "replace",
                "with_name", "with_suffix", "joinpath", "relative_to", "expanduser", "as_posix", "copy", "items",
                "values", "keys", "get", "pop", "setdefault", "popleft", "__getitem__"}
PURE_ATTRS = {"parent", "parents", "parts", "anchor", "drive", "root"}
DROP_ATTRS = {"name", "stem", "suffix", "suffixes"}
STORE_METHODS = {"append", "extend", "add", "update", "insert", "appendleft"}
SINK_FUNCS = {"print", "json.dumps", "len", "int", "float", "bool", "isinstance", "any", "all", "min", "max", "hash",
              "id", "type", "getattr", "setattr", "hasattr", "delattr", "callable", "os.strerror", "re.sub", "re.match", "re.search",
              "re.compile", "json.loads", "time.time", "os.geteuid", "os.getpid", "stat.S_IMODE", "stat.S_ISDIR",
              "stat.S_ISLNK", "stat.S_ISREG", "sys.exit", "warnings.warn", "os.close", "os.umask", "asyncio.wait_for",
              "asyncio.sleep", "asyncio.run", "asyncio.Queue", "asyncio.Event", "super", "range", "abs", "round",
              "divmod", "chr", "ord", "hex", "oct", "vars", "traceback.format_exc", "traceback.extract_tb"}
SINK_METHODS = {"write", "writelines", "log", "debug", "info", "warning", "error", "exception", "seek", "read",
                "readline", "readlines", "close", "flush", "put", "put_nowait", "send", "startswith", "endswith",
                "split", "rsplit", "splitlines", "count", "find", "index", "isdigit", "isalnum", "discard", "remove",
                "clear", "poll", "wait", "terminate", "kill", "drain", "feed", "dump"}
LOG_PARAMS = {"log", "logger", "on_fault", "on_stderr", "on_exit", "on_hello", "on_ack"}


class Tag(tuple):
    """An origin: (kind, file, line, text). Two tags are the same origin when their (kind, file, qual, text, ordinal)
    agree; the line is for the printed list."""
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


class Fn:
    def __init__(self, file, qual, node, cls):
        self.file, self.qual, self.node, self.cls = file, qual, node, cls
        a = node.args
        self.params = [p.arg for p in a.posonlyargs + a.args] + ([a.vararg.arg] if a.vararg else []) + \
                      [p.arg for p in a.kwonlyargs] + ([a.kwarg.arg] if a.kwarg else [])
        self.pos = [p.arg for p in a.posonlyargs + a.args]
        self.defaults = {}
        for p, d in zip(reversed(a.args), reversed(a.defaults)):
            self.defaults[p.arg] = d
        for p, d in zip(a.kwonlyargs, a.kw_defaults):
            if d is not None:
                self.defaults[p.arg] = d
        self.identity = self._identity_param()
        self.tokens = self._tokens()

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

    def __repr__(self):
        return "%s:%s" % (self.file, self.qual)


class Terminal:
    def __init__(self, fn, node, op, arg_text, ordinal, mech, origins):
        self.fn, self.node, self.op, self.arg_text, self.ordinal, self.mech, self.origins = fn, node, op, arg_text, ordinal, mech, origins

    def key(self):
        return (self.fn.file, self.fn.qual, self.op, self.arg_text, self.ordinal)

    def origin_keys(self):
        return tuple(sorted(set(t.key() for t in self.origins)))


class Census:
    def __init__(self, root, files=FILES):
        self.root = Path(root)
        self.files = tuple(files)
        self.src, self.lines, self.trees, self.fns, self.classes, self.mod_fns = {}, {}, {}, {}, {}, {}
        self.by_name, self.methods = {}, {}
        self.local, self.attr, self.ret, self.ret_type, self.var_type, self.attr_type = {}, {}, {}, {}, {}, {}
        self.terminals, self.escapes, self.seeds, self.sites = {}, {}, [], {}
        self.shape_local, self.shape_ret = {}, {}          # per-element tags of tuple-valued names and returns
        self.calls_of = {}
        self._ordinals = {}
        self._changed = False
        for f in self.files:
            self._index(f)

    # ── indexing ──────────────────────────────────────────────────────────────────────────────────
    def _index(self, f):
        src = (self.root / f).read_text(encoding="utf-8")
        tree = ast.parse(src)
        self.src[f], self.trees[f], self.lines[f] = src, tree, src.splitlines(keepends=True)
        self.mod_fns[f] = []
        top = [n for n in tree.body if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
        mod_node = ast.FunctionDef(name="module level", args=ast.arguments(posonlyargs=[], args=[], vararg=None, kwonlyargs=[],
                                                                            kw_defaults=[], kwarg=None, defaults=[]),
                                   body=top or [ast.Pass()], decorator_list=[], returns=None, lineno=1, col_offset=0,
                                   end_lineno=1, end_col_offset=0)
        mod_fn = Fn(f, "module level", mod_node, None)
        self.fns[(f, "module level")] = mod_fn
        self.mod_fns[f].append(mod_fn)
        for n in tree.body:
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                fn = Fn(f, n.name, n, None)
                self.fns[(f, n.name)] = fn
                self.by_name.setdefault(n.name, []).append(fn)
                self.mod_fns[f].append(fn)
            elif isinstance(n, ast.ClassDef):
                self.classes[n.name] = (f, n)
                for c in n.body:
                    if isinstance(c, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        fn = Fn(f, n.name + "." + c.name, c, n.name)
                        self.fns[(f, fn.qual)] = fn
                        self.methods.setdefault((n.name, c.name), []).append(fn)
                        self.mod_fns[f].append(fn)
        for fn in self.mod_fns[f]:
            for node in ast.walk(fn.node):
                node._fn = fn

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
        if cls and store.get(key) != cls:
            store[key] = cls
            self._changed = True

    def local_tags(self, fn, name):
        own = self.local.get((fn.file, fn.qual, name))
        if own is not None or name in fn.params:
            return own or set()
        return self.local.get((fn.file, "module level", name), set())     # a module-level binding read by name

    # ── resolution ────────────────────────────────────────────────────────────────────────────────
    def dotted(self, e):
        if isinstance(e, ast.Name):
            return e.id
        if isinstance(e, ast.Attribute):
            base = self.dotted(e.value)
            return base + "." + e.attr if base else None
        return None

    def resolve(self, call, fn):
        """The in-file functions a call may reach, or [] when it reaches none the census knows."""
        f = call.func
        if isinstance(f, ast.Name):
            if f.id in self.classes:
                return self.methods.get((f.id, "__init__"), [])
            if f.id == "cls" and fn.cls:
                return self.methods.get((fn.cls, "__init__"), [])
            if f.id in fn.params:
                return self._param_callables(fn, f.id)
            if f.id in fn.params or self.local_tags(fn, f.id):
                return []
            return [x for x in self.by_name.get(f.id, []) if x.file == fn.file] or self.by_name.get(f.id, [])
        if isinstance(f, ast.Attribute):
            recv, name = f.value, f.attr
            if isinstance(recv, ast.Name) and recv.id in ("self", "cls") and fn.cls:
                if name == "__class__":
                    return []
                found = self.methods.get((fn.cls, name))
                if found:
                    return found
                return [x for k, x in [(k, m) for k, ms in self.methods.items() if k[1] == name for m in ms]]
            if isinstance(recv, ast.Name) and recv.id in self.classes:
                return self.methods.get((recv.id, name), [])
            if isinstance(recv, ast.Attribute) and recv.attr in self.classes:
                return self.methods.get((recv.attr, name), [])
            t = self.type_of(recv, fn)
            if t:
                return self.methods.get((t, name), [])
            if name in self.classes:
                return self.methods.get((name, "__init__"), [])
            if name in self.by_name and name not in PATH_METHODS and name not in PURE_METHODS:
                return self.by_name[name]
        return []

    def _param_callables(self, fn, pname):
        """The callables a parameter is bound to at the function's call sites (a bound method or a lambda)."""
        out = []
        for site_fn, call in self.calls_of.get((fn.file, fn.qual), []):
            bound = self._bound_arg(call, fn, pname)
            if bound is None or isinstance(bound, ast.Lambda):
                continue                              # a lambda's body is not followed: a logger, by every binding here
            out.extend(self.resolve(ast.Call(func=bound, args=[], keywords=[]), site_fn))
        return out

    def _positional(self, call, callee):
        """The callee's positional parameter names aligned with the call's positional arguments: the bound `self`
        or `cls` is dropped unless the call spells it (`Class.method(self, ...)`)."""
        pos = list(callee.pos)
        if callee.cls and pos and pos[0] in ("self", "cls"):
            explicit = isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name) \
                and call.func.value.id in self.classes and not callee.qual.endswith(".__init__")
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

    def type_of(self, e, fn):
        if isinstance(e, ast.Name):
            if e.id in ("self", "cls"):
                return fn.cls
            return self.var_type.get((fn.file, fn.qual, e.id))
        if isinstance(e, ast.Attribute) and isinstance(e.value, ast.Name) and e.value.id in ("self", "cls"):
            return self.attr_type.get((fn.cls, e.attr))
        if isinstance(e, ast.Call):
            for callee in self.resolve(e, fn):
                if callee.qual.endswith(".__init__"):
                    return callee.cls
                if self.ret_type.get((callee.file, callee.qual)):
                    return self.ret_type[(callee.file, callee.qual)]
        return None

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
            if e.attr in DROP_ATTRS:
                return set()
            if isinstance(e.value, ast.Name) and e.value.id in ("self", "cls") and fn.cls:
                return set(self.attr.get((fn.cls, e.attr), set()))
            t = self.type_of(e.value, fn)
            if t:
                return set(self.attr.get((t, e.attr), set()))
            inner = self.tags(e.value, fn)
            return inner if inner else set()
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
            self._add(self.local, (fn.file, fn.qual, e.target.id), t)
            return t
        if isinstance(e, (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)):
            for g in e.generators:
                self._bind_target(g.target, self.tags(g.iter, fn) | self._yielded(g.iter, fn), fn)
            if isinstance(e, ast.DictComp):
                return self.tags(e.value, fn)
            return self.tags(e.elt, fn)
        if isinstance(e, ast.Await):
            return self.tags(e.value, fn)
        if isinstance(e, ast.Call):
            return self._call(e, fn)
        if isinstance(e, ast.Lambda):
            return set()
        return set()

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
            return self.shape_local.get((fn.file, fn.qual, e.id)) or self.shape_local.get((fn.file, "module level", e.id)) or None
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
        tag = Tag(kind, fn.file, e.lineno, text, fn.qual, self.ordinal(fn, "seed", text))
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
        if isinstance(p, ast.keyword):
            return False
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
        # terminals
        term = self._terminal(e, fn, name, arg_tags, kw_tags)
        if term is not None:
            return term
        # pure conversions and container operations
        if name in PURE_FUNCS:
            return all_tags
        if isinstance(e.func, ast.Attribute):
            recv_tags = self.tags(e.func.value, fn)
            m = e.func.attr
            if m in STORE_METHODS:
                self._store_into(e.func.value, all_tags, fn)
                return set()
            if m in PURE_METHODS:
                return recv_tags | all_tags
            if m in SINK_METHODS:
                return set()
        if name in SINK_FUNCS:
            return set()
        if self._is_exception(e.func):
            return set()
        callees = self.resolve(e, fn)
        if callees:
            self.sites.setdefault((fn.file, fn.qual, e.lineno, e.col_offset, e.end_lineno, e.end_col_offset), (fn, e, callees))
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
        path_tags = {t for t in all_tags if t.kind == "path"}
        if path_tags and not self._recv_tainted_only_text(e, fn):
            text = self.segment(fn, e)
            key = (fn.file, fn.qual, "escape", text)
            if key not in self.escapes:
                self.escapes[key] = Terminal(fn, e, "escape", text, self._ord_of(fn, "escape", text, e), "escape", set())
                self._changed = True
            self.escapes[key].origins |= path_tags
        return set()

    def _recv_tainted_only_text(self, e, fn):
        return False

    def _ord_of(self, fn, kind, text, node):
        k = (fn.file, fn.qual, kind, text, node.lineno, node.col_offset)
        if k in self._ordinals:
            return self._ordinals[k]
        n = self.ordinal(fn, kind, text)
        self._ordinals[k] = n
        return n

    def _is_exception(self, f):
        name = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else "")
        return bool(re.search(r"(Error|Exception|Refused|Like|Warning|Interrupt)$", name))

    def _bind_call(self, call, callee, fn, arg_tags, kw_tags):
        """Bind a call's arguments to the callee's parameters: their tags, and their type when the walk knows it (a
        HostDirs handed to _open_file_nofollow types `dirs` there, so `dirs.dir` reads the descriptor's taint)."""
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
                self._type(self.var_type, (callee.file, callee.qual, pos[i]), self.type_of(a, fn))
            elif callee.node.args.vararg:
                self._add(self.local, (callee.file, callee.qual, callee.node.args.vararg.arg), tags)
        for kw in call.keywords:
            k = kw.arg
            tags = kw_tags.get(k if k is not None else "**", set())
            if k in callee.params:
                self._add(self.local, (callee.file, callee.qual, k), tags)
                self._type(self.var_type, (callee.file, callee.qual, k), self.type_of(kw.value, fn))
            elif k is None:
                for p in callee.params:
                    self._add(self.local, (callee.file, callee.qual, p), tags)
            elif callee.node.args.kwarg:
                self._add(self.local, (callee.file, callee.qual, callee.node.args.kwarg.arg), tags)

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
            if m in PATH_METHODS and recv_tags:
                is_method = True
            else:
                return None
        path_tags, fd_tags, arg_text = set(), set(), None
        if is_method:
            path_tags = {t for t in recv_tags if t.kind != "fd"}
            fd_tags = {t for t in recv_tags if t.kind == "fd"}
            arg_text = self.segment(fn, e.func.value)
            op = m
        else:
            op = name
            for p in (positions or ()) + (exec_positions or ()):
                if isinstance(p, int) and p < len(arg_tags):
                    path_tags |= {t for t in arg_tags[p] if t.kind != "fd"}
                    fd_tags |= {t for t in arg_tags[p] if t.kind == "fd"}
                    arg_text = arg_text or self.segment(fn, e.args[p])
                elif isinstance(p, str) and p in kw_tags:
                    path_tags |= {t for t in kw_tags[p] if t.kind != "fd"}
                    arg_text = arg_text or self.segment(fn, next(k.value for k in e.keywords if k.arg == p))
            for p in (fd_positions or ()):
                if p < len(arg_tags):
                    fd_tags |= {t for t in arg_tags[p] if t.kind == "fd"}
                    arg_text = arg_text or self.segment(fn, e.args[p])
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
        if isinstance(target, ast.Name):
            self._add(self.local, (fn.file, fn.qual, target.id), tags)
        elif isinstance(target, ast.Attribute):
            if isinstance(target.value, ast.Name) and target.value.id in ("self", "cls") and fn.cls:
                self._add(self.attr, (fn.cls, target.attr), tags)
            else:
                t = self.type_of(target.value, fn)
                if t:
                    self._add(self.attr, (t, target.attr), tags)
        elif isinstance(target, ast.Subscript):
            self._store_into(target.value, tags, fn)

    def _bind_target(self, target, tags, fn, typ=None, value=None):
        if isinstance(target, (ast.Tuple, ast.List)):
            if isinstance(value, (ast.Tuple, ast.List)) and len(value.elts) == len(target.elts) \
                    and not any(isinstance(x, ast.Starred) for x in target.elts + value.elts):
                for x, v in zip(target.elts, value.elts):      # element-wise: `self.hosts, self.dir, self.path = hosts, dir, path`
                    self._bind_target(x, self.tags(v, fn), fn, self.type_of(v, fn), v)
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
        if isinstance(target, ast.Name):
            self._add(self.local, (fn.file, fn.qual, target.id), tags)
            self._type(self.var_type, (fn.file, fn.qual, target.id), typ)
            shape = self._elems(value, fn) if value is not None else None
            if shape is not None:
                self._merge_shape(self.shape_local, (fn.file, fn.qual, target.id), shape)
        elif isinstance(target, ast.Attribute):
            if isinstance(target.value, ast.Name) and target.value.id in ("self", "cls") and fn.cls:
                self._add(self.attr, (fn.cls, target.attr), tags)
                self._type(self.attr_type, (fn.cls, target.attr), typ)
            else:
                t = self.type_of(target.value, fn)
                if t:
                    self._add(self.attr, (t, target.attr), tags)
        elif isinstance(target, ast.Subscript):
            self._store_into(target.value, tags, fn)

    # ── the walk ──────────────────────────────────────────────────────────────────────────────────
    def _walk_fn(self, fn):
        for node in ast.walk(fn.node):
            if getattr(node, "_fn", None) is not fn:
                continue
            if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                if node.value is None:
                    continue
                tags = self.tags(node.value, fn)
                typ = self.type_of(node.value, fn)
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
                        self._bind_target(item.optional_vars, tags, fn, self.type_of(item.context_expr, fn))
            elif isinstance(node, (ast.Return, ast.Yield)):
                if node.value is not None:
                    self._add(self.ret, (fn.file, fn.qual), self.tags(node.value, fn))
                    if isinstance(node, ast.Return):
                        self._type(self.ret_type, (fn.file, fn.qual), self.type_of(node.value, fn))
                    shape = self._elems(node.value, fn)
                    if shape is not None:
                        self._merge_shape(self.shape_ret, (fn.file, fn.qual), shape)
            elif isinstance(node, ast.Expr):
                self.tags(node.value, fn)
            elif isinstance(node, (ast.If, ast.While, ast.Assert)):
                self.tags(node.test, fn)
            elif isinstance(node, ast.Raise):
                self.tags(node.exc, fn)
        for node in ast.walk(fn.node):
            if getattr(node, "_fn", None) is not fn:
                continue
            if isinstance(node, ast.Call):
                self.tags(node, fn)

    def run(self):
        for f in self.files:
            for node in ast.walk(self.trees[f]):
                for child in ast.iter_child_nodes(node):
                    child._parent = node
        for f, qual, pname, why in DECLARED_SEEDS:
            if (f, qual) in self.fns:
                fn = self.fns[(f, qual)]
                self._add(self.local, (f, qual, pname), {Tag("path", f, fn.node.lineno, why, qual, 1)})
        for _ in range(60):
            self._changed = False
            holders = {c for (c, a), tags in self.attr.items() if tags}
            minting = set()
            for fn in self.fns.values():
                if (self.ret.get((fn.file, fn.qual)) or self.ret_type.get((fn.file, fn.qual)) in holders
                        or any(t.qual == fn.qual and t.file == fn.file and t.kind == "path" for _, t in self.seeds)
                        or any(f == fn.file and q == fn.qual for f, q, _, _ in DECLARED_SEEDS)):
                    minting.add(fn.cls if fn.qual.endswith(".__init__") else fn.qual.split(".")[-1])
            tainted_rets = minting
            tainted_attrs = {a for (c, a), tags in self.attr.items() if tags}
            has_local = {(f, q) for (f, q, n), tags in self.local.items() if tags}
            for fn in [x for f in self.files for x in self.mod_fns[f]]:
                seed, calls, attrs = fn.tokens
                if not (seed or (fn.file, fn.qual) in has_local or (calls & tainted_rets) or (attrs & tainted_attrs)):
                    continue
                self._walk_fn(fn)
            if not self._changed:
                break
        else:
            raise AssertionError("the census did not reach a fixpoint in 60 rounds")
        return self

    # ── views ─────────────────────────────────────────────────────────────────────────────────────
    def roads(self):
        """The carriers and mints, read off the resolved call sites once the fixpoint holds: a CARRIER hands a tainted
        value (a path or a descriptor) to a function of the files (`host_log_mark(..., dir_fd=dirs.dir)`,
        `owner_only_dir(host_dir(...))`, `HostTransport.from_journal(hdir)`); a MINT is a call whose value is tainted
        (`hdir = ht.host_dir(...)`, `spec_path = ht.write_spawn_spec(...)`) or that enters a function holding a seed or
        returning a descriptor holder (`open_host_dirs(...)`, `remove_host_dir(...)`, `hosts_dir(...)`), the roads by
        which a use inside a helper is reached from a caller that passes nothing tainted itself."""
        seed_quals = {(t.file, t.qual) for _, t in self.seeds if t.kind == "path"} | {(f, q) for f, q, _, _ in DECLARED_SEEDS}
        holders = {c for (c, a), tags in self.attr.items() if tags}
        out = []
        for (f, q, ln, col, _eln, _ecol), (fn, call, callees) in self.sites.items():
            kinds = set()
            for a in call.args:
                kinds |= {t.kind for t in self.tags(a, fn)}
            for kw in call.keywords:
                kinds |= {t.kind for t in self.tags(kw.value, fn)}
            carrier = bool(kinds - {"text"})
            value = self.tags(call, fn)
            mint = bool(value) or any((c.file, c.qual) in seed_quals or self.ret_type.get((c.file, c.qual)) in holders for c in callees)
            if not (carrier or mint):
                continue
            tainted = [self.segment(fn, a) for a in call.args if self.tags(a, fn) - {t for t in self.tags(a, fn) if t.kind == "text"}]
            tainted += ["%s=%s" % (kw.arg, self.segment(fn, kw.value)) for kw in call.keywords
                        if {t for t in self.tags(kw.value, fn) if t.kind != "text"}]
            text = "%s(%s)" % (self.segment(fn, call.func), ", ".join(tainted) if tainted else "...")
            kind = "carrier" if carrier else "mint"
            mech = "+".join(sorted(kinds - {"text"})) if carrier else ("+".join(sorted({t.kind for t in value})) or "enters")
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
        """{member key: (mech, origin keys)}: the pinned view. A terminal's key names its operation; a carrier's or a
        mint's names its kind."""
        return {t.key(): (t.mech, t.origin_keys()) for t in self.members()}

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


# The published list at this head: every member the census derives, keyed by file, enclosing function, the operation
# (a terminal's syscall; `carrier` or `mint` for a road), the argument text and its ordinal in that function; the value
# is the mechanical class and the ROAD, written for the reader: `kernel` or `host` is the process; `guard` a syscall
# that decides a refusal; `HELPER` one of the two directory helpers write_spawn_spec runs before the descent, the
# window condition 1 states; `RESIDUAL (queued)` a by-path read the queued item owns; `unreachable today` a
# dir_fd=None arm held by test_every_road_into_a_by_path_fallback_arm_passes_a_descriptor. ORIGINS below is the
# derived provenance of each terminal (the seeds and minting calls whose value reaches it), generated by
# `python3 tests/test_hosts_path_census.py --expected` and pasted; a road's origins are the empty tuple.
ROADS = {
    ('kernel/host_transport.py', '_open_dir_nofollow', 'os.open', 'name', 1):
        ('mixed', "kernel; guard: the descent's open, hosts/ by PATH with O_DIRECTORY|O_NOFOLLOW off the state root, <sid> by NAME under the first descriptor; the removal road's hosts/ the same"),
    ('kernel/host_transport.py', '_open_dir_nofollow', 'os.lstat', 'name', 1):
        ('mixed', "kernel; guard's wording: the lstat after a refused open (a link or a non-directory), by path for hosts/, by name under the descriptor for <sid>; it decides nothing"),
    ('kernel/host_transport.py', '_open_dir_nofollow', 'os.fstat', 'fd', 1):
        ('by-descriptor', "kernel; guard: the descent's checks on the object opened (a directory, this uid, no group or other bits)"),
    ('kernel/host_transport.py', 'open_host_dirs', 'carrier', '_open_dir_nofollow(str(hosts_path), hosts_path)', 1):
        ('path', "kernel; the descent's first component, by path"),
    ('kernel/host_transport.py', 'open_host_dirs', 'carrier', '_open_dir_nofollow(hosts_path / str(sid), dir_fd=hfd)', 1):
        ('fd+path', "kernel; the descent's second component, by name under the first"),
    ('kernel/host_transport.py', 'open_host_dirs', 'carrier', 'HostDirs(hfd, dfd, hosts_path / str(sid))', 1):
        ('fd+path', 'kernel; the two descriptors and the wording path handed to the holder'),
    ('kernel/host_transport.py', '_open_file_nofollow', 'os.open', 'name', 1):
        ('by-descriptor', 'kernel; spawn.json and host.stderr opened by NAME under the verified <sid> descriptor, O_NOFOLLOW'),
    ('kernel/host_transport.py', 'host_stderr_open', 'mint', '_open_file_nofollow(...)', 1):
        ('fd', "kernel; host.stderr's descriptor"),
    ('kernel/host_transport.py', 'host_stderr_open', 'os.fchmod', 'fd', 1):
        ('by-descriptor', 'kernel; host.stderr tightened on its descriptor (round 5, kernel-1)'),
    ('kernel/host_transport.py', 'host_stderr_size', 'os.stat', '"host.stderr"', 1):
        ('by-descriptor', "kernel; host.stderr's watermark by name under the descriptor"),
    ('kernel/host_transport.py', '_rmtree_at', 'os.open', 'name', 1):
        ('by-descriptor', "kernel; the removal road: each directory opened by name under its parent's descriptor"),
    ('kernel/host_transport.py', '_rmtree_at', 'os.fstat', 'fd', 1):
        ('by-descriptor', "kernel; the removal road's uid check on the object opened"),
    ('kernel/host_transport.py', '_rmtree_at', 'os.scandir', 'fd', 1):
        ('by-descriptor', "kernel; the removal road's listing off the descriptor"),
    ('kernel/host_transport.py', '_rmtree_at', 'carrier', '_rmtree_at(fd)', 1):
        ('fd', "kernel; the removal road's recursion, the descriptor passed down"),
    ('kernel/host_transport.py', '_rmtree_at', 'os.unlink', 'e.name', 1):
        ('by-descriptor', "kernel; the removal road's unlink by name under the descriptor"),
    ('kernel/host_transport.py', '_rmtree_at', 'os.rmdir', 'name', 1):
        ('by-descriptor', "kernel; the removal road's rmdir by name under the parent's descriptor"),
    ('kernel/host_transport.py', 'remove_host_dir', 'carrier', '_open_dir_nofollow(str(hosts_path), hosts_path)', 1):
        ('path', "kernel; guard: the removal road's hosts/ opened by path with O_NOFOLLOW"),
    ('kernel/host_transport.py', 'remove_host_dir', 'carrier', '_rmtree_at(hfd)', 1):
        ('fd', "kernel; the removal road's walk of <sid> under the hosts/ descriptor"),
    ('kernel/host_transport.py', 'remove_host_dir', 'os.stat', 'str(sid)', 1):
        ('by-descriptor', "kernel; the already-absent arm's stat by name under the hosts/ descriptor"),
    ('kernel/host_transport.py', '_open_host_log', 'open', 'host_dir(state_dir, sid) / "host.log"', 1):
        ('by-path', 'kernel; unreachable today: the dir_fd=None arm, held by the forwarding pin (every caller passes a descriptor)'),
    ('kernel/host_transport.py', '_open_host_log', 'mint', 'host_dir(...)', 1):
        ('path', "kernel; unreachable today: the dir_fd=None arm's binding"),
    ('kernel/host_transport.py', '_open_host_log', 'os.open', '"host.log"', 1):
        ('by-descriptor', "kernel; host.log opened by name under the <sid> descriptor with O_NOFOLLOW (the refused roads' reads)"),
    ('kernel/host_transport.py', '_open_host_log', 'os.fdopen', 'fd', 1):
        ('by-descriptor', 'kernel; the same descriptor as a file object'),
    ('kernel/host_transport.py', 'host_log_mark', 'os.stat', '"host.log"', 1):
        ('by-descriptor', 'kernel; the spawn watermark by name under the descriptor'),
    ('kernel/host_transport.py', 'host_log_mark', 'os.stat', 'host_dir(state_dir, sid) / "host.log"', 1):
        ('by-path', 'kernel; unreachable today: the dir_fd=None arm, held by the forwarding pin'),
    ('kernel/host_transport.py', 'host_log_mark', 'mint', 'host_dir(...)', 1):
        ('path', "kernel; unreachable today: the dir_fd=None arm's binding"),
    ('kernel/host_transport.py', 'host_log_rows', 'carrier', '_open_host_log(dir_fd)', 1):
        ('fd', 'kernel; the descriptor forwarded to the open'),
    ('kernel/host_transport.py', 'host_exit_reason', 'carrier', 'host_log_rows(dir_fd=dir_fd)', 1):
        ('fd', 'kernel; the descriptor forwarded to the rows read'),
    ('kernel/host_transport.py', 'write_spawn_spec', 'mint', 'sh.hosts_dir(...)', 1):
        ('path', "kernel; HELPER (condition 1's window): hosts/ made and checked by path before the descent"),
    ('kernel/host_transport.py', 'write_spawn_spec', 'carrier', 'sh.owner_only_dir(host_dir(state_dir, sid))', 1):
        ('path', "kernel; HELPER (condition 1's window): hosts/<sid>/ made and checked by path before the descent"),
    ('kernel/host_transport.py', 'write_spawn_spec', 'mint', 'host_dir(...)', 1):
        ('path', 'kernel; the path the second helper takes'),
    ('kernel/host_transport.py', 'write_spawn_spec', 'mint', 'host_dir(...)', 2):
        ('path', "kernel; spawn.json's path, the value returned: spec_path in _host_transport_for, handed to the host in argv"),
    ('kernel/host_transport.py', 'write_spawn_spec', 'mint', 'open_host_dirs(...)', 1):
        ('enters', "kernel; the spec write's own descent"),
    ('kernel/host_transport.py', 'write_spawn_spec', 'mint', '_open_file_nofollow(...)', 1):
        ('fd', "kernel; spawn.json's descriptor"),
    ('kernel/host_transport.py', 'write_spawn_spec', 'os.fchmod', 'fd', 1):
        ('by-descriptor', 'kernel; spawn.json tightened on its descriptor before the write'),
    ('kernel/host_transport.py', 'write_spawn_spec', 'os.fdopen', 'fd', 1):
        ('by-descriptor', 'kernel; spawn.json written through its descriptor'),
    ('kernel/host_transport.py', 'helper_shape_refusal', 'mint', 'host_dir(...)', 1):
        ('path', "kernel; the sentence for a shape errno of the helpers names the component: hosts/<sid>/ when the errno carried no path (a message, no syscall)"),
    ('kernel/host_transport.py', 'write_spawn_spec', 'mint', 'helper_shape_refusal(...)', 1):
        ('path', "kernel; the refusal's sentence, built from the failing path (a message, no syscall; the exception is the sink)"),
    ('kernel/host_transport.py', 'HostTransport.from_journal', 'carrier', 'cls(journal_dir=journal_dir)', 1):
        ('path', "kernel; the replay transport given the orphan's directory"),
    ('kernel/host_transport.py', 'HostTransport.connect', 'asyncio.open_unix_connection', 'self.sock_path', 1):
        ('by-path', 'kernel; RESIDUAL (queued): the connect to the published socket by path, reached from three roads (the attach by lease, the first connect after the spawn wait, the end by lease)'),
    ('kernel/host_transport.py', 'HostTransport._read_journal', 'carrier', 'sh.read_journal_dir(self.journal_dir)', 1):
        ('path', "kernel; RESIDUAL (queued): the replay's read of the orphan journal by path"),
    ('kernel/session_host.py', 'Journal.__init__', 'carrier', 'owner_only_dir(directory)', 1):
        ('path', "host; HELPER: hosts/<sid>/ made and checked by path in the host's constructor"),
    ('kernel/session_host.py', 'Journal._open_segment', 'open', 'self._path(first)', 1):
        ('by-path', "host; a journal segment opened by path under hosts/<sid>/, after the constructor's guard"),
    ('kernel/session_host.py', 'Journal._open_segment', 'mint', 'self._path(...)', 1):
        ('path', "host; a segment's path"),
    ('kernel/session_host.py', 'Journal._persist_gaps', 'open', 'tmp', 1):
        ('by-path', "host; gaps.json's temp written by path under hosts/<sid>/"),
    ('kernel/session_host.py', 'Journal._persist_gaps', 'os.replace', 'tmp', 1):
        ('by-path', 'host; gaps.json replaced by path'),
    ('kernel/session_host.py', 'Journal._persist_gaps', 'os.unlink', 'tmp', 1):
        ('by-path', "host; gaps.json's temp unlinked by path on failure"),
    ('kernel/session_host.py', 'Journal._turn_boundary', 'os.unlink', 'self._path(seg)', 1):
        ('by-path', 'host; an acknowledged segment deleted by path'),
    ('kernel/session_host.py', 'Journal._turn_boundary', 'mint', 'self._path(...)', 1):
        ('path', "host; a segment's path"),
    ('kernel/session_host.py', 'Journal.read_from', 'open', 'self._path(seg)', 1):
        ('by-path', 'host; a segment read by path'),
    ('kernel/session_host.py', 'Journal.read_from', 'mint', 'self._path(...)', 1):
        ('path', "host; a segment's path"),
    ('kernel/session_host.py', 'read_journal_dir', 'glob', 'd', 1):
        ('by-path', "kernel; RESIDUAL (queued): the orphan road's journal listing by path (from _host_orphan_recover and the replay transport)"),
    ('kernel/session_host.py', 'read_journal_dir', 'read_text', 'd / "gaps.json"', 1):
        ('by-path', "kernel; RESIDUAL (queued): the orphan road's gaps.json read by path"),
    ('kernel/session_host.py', 'read_journal_dir', 'open', 'p', 1):
        ('by-path', "kernel; RESIDUAL (queued): the orphan road's segment read by path"),
    ('kernel/session_host.py', 'owner_only_dir', 'mkdir', 'd', 1):
        ('by-path', "HELPER (condition 1's window): the mkdir by path; hosts/ for hosts_dir's three callers, hosts/<sid>/ for write_spawn_spec and the host's Journal"),
    ('kernel/session_host.py', 'owner_only_dir', 'os.lstat', 'd', 1):
        ('by-path', 'HELPER: the lstat by path that decides symlink, non-directory, foreign uid and loose'),
    ('kernel/session_host.py', 'owner_only_dir', 'os.chmod', 'd', 1):
        ('by-path', "HELPER (condition 1's window): the chmod by path of a loose directory of ours; it follows a link swapped in between the lstat above and this call onto any object this uid owns"),
    ('kernel/session_host.py', 'owner_only_dir', 'os.lstat', 'd', 2):
        ('by-path', 'HELPER: the read-back by path'),
    ('kernel/session_host.py', 'hosts_dir', 'carrier', 'owner_only_dir(root / "hosts")', 1):
        ('path', "HELPER: hosts/ through owner_only_dir, for the kernel's write_spawn_spec and the host's constructor and prelude"),
    ('kernel/session_host.py', 'SessionHost.__init__', 'open', 'self.spec_path', 1):
        ('by-path', 'host; RESIDUAL (queued), the deferred road: the spec opened by path with no O_NOFOLLOW before any guard'),
    ('kernel/session_host.py', 'SessionHost.__init__', 'mint', 'hosts_dir(...)', 1):
        ('path', "host; the constructor's guard of hosts/, by path"),
    ('kernel/session_host.py', 'SessionHost.__init__', 'carrier', 'Journal(self.dir)', 1):
        ('path', "host; the constructor's Journal over hosts/<sid>/"),
    ('kernel/session_host.py', 'SessionHost.log', 'open', 'self.log_path', 1):
        ('by-path', "host; host.log appended by path after the constructor's guard"),
    ('kernel/session_host.py', 'SessionHost._sweep_stale_temps', 'glob', 'self.sock_path.parent', 1):
        ('by-path', "host; the prelude's listing of hosts/ by path"),
    ('kernel/session_host.py', 'SessionHost._sweep_stale_temps', 'unlink', 'p', 1):
        ('by-path', "host; a dead owner's temp unlinked by path"),
    ('kernel/session_host.py', 'SessionHost._prepare_socket', 'mint', 'hosts_dir(...)', 1):
        ('path', "host; the prelude's guard of hosts/, by path"),
    ('kernel/session_host.py', 'SessionHost._prepare_socket', 'unlink', 'self.sock_path', 1):
        ('by-path', "host; a dead host's published socket unlinked by path (the prelude)"),
    ('kernel/session_host.py', 'SessionHost._serve_socket', 'os.lstat', 'self.sock_path.parent', 1):
        ('by-path', 'host; guard: the lstat of hosts/ before the bind (round 4, extra6-1)'),
    ('kernel/session_host.py', 'SessionHost._serve_socket', 'asyncio.start_unix_server', 'str(self.sock_tmp)', 1):
        ('by-path', 'host; the bind by path; the microseconds after the lstat above are unguarded'),
    ('kernel/session_host.py', 'SessionHost._serve_socket', 'os.chmod', 'self.sock_tmp', 1):
        ('by-path', 'host; the temp tightened by path'),
    ('kernel/session_host.py', 'SessionHost._serve_socket', 'os.rename', 'self.sock_tmp', 1):
        ('by-path', 'host; the publish: the temp renamed onto the published path'),
    ('kernel/session_host.py', 'SessionHost._serve_socket', 'unlink', 'self.sock_tmp', 1):
        ('by-path', "host; the failure arm's temp unlink"),
    ('kernel/session_host.py', 'SessionHost.run', 'write_text', 'self.dir / "identity.json"', 1):
        ('by-path', "host; identity.json written by path after the constructor's guard"),
    ('kernel/session_host.py', 'SessionHost.run', 'unlink', 'self.sock_path', 1):
        ('by-path', "host; the exit's unlink of the published socket"),
    ('kernel/session_host.py', 'main', 'mint', 'SessionHost(...)', 1):
        ('enters', 'host; the entry: argv[0] is the spec path the kernel handed over (the declared seed)'),
    ('kernel/sdk_backend.py', 'SdkBackend._host_lease_applies', 'mint', '_ht().host_dir(...)', 1):
        ('path', "kernel; the lease-applies read's binding"),
    ('kernel/sdk_backend.py', 'SdkBackend._host_lease_applies', 'exists', 'hdir / "identity.json"', 1):
        ('by-path', "kernel; RESIDUAL (queued): the connect road's identity.json existence read before the spawn, by path"),
    ('kernel/sdk_backend.py', 'SdkBackend._host_lease_applies', 'glob', 'hdir', 1):
        ('by-path', "kernel; RESIDUAL (queued): the connect road's journal glob before the spawn, by path"),
    ('kernel/sdk_backend.py', 'SdkBackend._host_transport_for', 'mint', 'ht.host_dir(...)', 1):
        ('path', "kernel; the connect road's binding"),
    ('kernel/sdk_backend.py', 'SdkBackend._host_transport_for', 'exists', 'hdir', 1):
        ('by-path', "kernel; RESIDUAL (queued): the leftover arm's trigger, by path"),
    ('kernel/sdk_backend.py', 'SdkBackend._host_transport_for', 'carrier', 'self._new_host_transport(ht.host_sock(self.state_dir, sess.sid))', 1):
        ('path', 'kernel; RESIDUAL (queued): the attach-by-lease road hands the published path to the transport (its connect, above)'),
    ('kernel/sdk_backend.py', 'SdkBackend._host_transport_for', 'mint', 'ht.host_sock(...)', 1):
        ('path', 'kernel; the published path for the attach'),
    ('kernel/sdk_backend.py', 'SdkBackend._host_transport_for', 'mint', 'ht.write_spawn_spec(...)', 1):
        ('path', 'kernel; spec_path: the path under hosts/ the launcher hands the host (a round-6 miss of the retired grep)'),
    ('kernel/sdk_backend.py', 'SdkBackend._host_transport_for', 'mint', 'ht.open_host_dirs(...)', 1):
        ('enters', "kernel; the road's descent, held across the spawn wait"),
    ('kernel/sdk_backend.py', 'SdkBackend._host_transport_for', 'mint', 'ht.host_sock(...)', 2):
        ('path', "kernel; the published path for the spawn wait's poll and the first connect"),
    ('kernel/sdk_backend.py', 'SdkBackend._host_transport_for', 'os.unlink', 'sock.name', 1):
        ('by-descriptor', "kernel; a dead host's published socket unlinked by name under the hosts/ descriptor"),
    ('kernel/sdk_backend.py', 'SdkBackend._host_transport_for', 'carrier', 'ht.host_log_mark(dir_fd=dirs.dir)', 1):
        ('fd', 'kernel; the spawn watermark through the descriptor'),
    ('kernel/sdk_backend.py', 'SdkBackend._host_transport_for', 'carrier', 'self._spawn_host(spec_path)', 1):
        ('path', 'kernel; the spec path handed to the launcher'),
    ('kernel/sdk_backend.py', 'SdkBackend._host_transport_for', 'exists', 'sock', 1):
        ('by-path', "kernel; RESIDUAL (queued): the spawn wait's poll of the published path, by path, after the descent"),
    ('kernel/sdk_backend.py', 'SdkBackend._host_transport_for', 'carrier', 'ht.host_exit_reason(dir_fd=dirs.dir)', 1):
        ('fd', "kernel; the exited arm's reason through the descriptor"),
    ('kernel/sdk_backend.py', 'SdkBackend._host_transport_for', 'carrier', 'self._file_refused_launch_context(dir_fd=dirs.dir)', 1):
        ('fd', "kernel; the exited arm's untested-row read through the descriptor"),
    ('kernel/sdk_backend.py', 'SdkBackend._host_transport_for', 'carrier', 'self._record_refused_launch_position(dir_fd=dirs.dir)', 1):
        ('fd', "kernel; the exited arm's position through the descriptor"),
    ('kernel/sdk_backend.py', 'SdkBackend._host_transport_for', 'carrier', 'ht.host_exit_reason(dir_fd=dirs.dir)', 2):
        ('fd', "kernel; the deadline arm's reason through the descriptor"),
    ('kernel/sdk_backend.py', 'SdkBackend._host_transport_for', 'carrier', 'self._file_refused_launch_context(dir_fd=dirs.dir)', 2):
        ('fd', "kernel; the deadline arm's untested-row read through the descriptor"),
    ('kernel/sdk_backend.py', 'SdkBackend._host_transport_for', 'carrier', 'self._record_refused_launch_position(dir_fd=dirs.dir)', 2):
        ('fd', "kernel; the deadline arm's position through the descriptor"),
    ('kernel/sdk_backend.py', 'SdkBackend._host_transport_for', 'carrier', 'self._new_host_transport(sock)', 1):
        ('path', 'kernel; RESIDUAL (queued): the first connect after the wait hands the published path to the transport (its connect, above)'),
    ('kernel/sdk_backend.py', 'SdkBackend._new_host_transport', 'carrier', 'ht.HostTransport(str(sock))', 1):
        ('path', "kernel; the transport's sock_path (its connect, above)"),
    ('kernel/sdk_backend.py', 'SdkBackend._spawn_host', 'mint', 'ht.open_host_dirs(...)', 1):
        ('enters', "kernel; the launcher's own descent"),
    ('kernel/sdk_backend.py', 'SdkBackend._spawn_host', 'mint', 'ht.host_stderr_open(...)', 1):
        ('fd', "kernel; host.stderr's descriptor for the child"),
    ('kernel/sdk_backend.py', 'SdkBackend._spawn_host', 'subprocess.Popen', 'argv', 1):
        ('exec-arg', "kernel; THE HANDOFF: the spec path leaves the process in argv (host.stderr's descriptor as the child's stderr beside it); the host re-opens that path by path in its constructor (above), the deferred road"),
    ('kernel/sdk_backend.py', 'SdkBackend._host_orphan_recover', 'mint', 'ht.host_dir(...)', 1):
        ('path', "kernel; the orphan road's binding"),
    ('kernel/sdk_backend.py', 'SdkBackend._host_orphan_recover', 'read_text', 'hdir / "identity.json"', 1):
        ('by-path', "kernel; RESIDUAL (queued): the orphan road's identity.json read, by path"),
    ('kernel/sdk_backend.py', 'SdkBackend._host_orphan_recover', 'carrier', 'ht.sh.read_journal_dir(hdir)', 1):
        ('path', "kernel; RESIDUAL (queued): the orphan road's journal tail, by path"),
    ('kernel/sdk_backend.py', 'SdkBackend._host_orphan_recover', 'glob', 'hdir', 1):
        ('by-path', "kernel; RESIDUAL (queued): the orphan road's journal glob, by path"),
    ('kernel/sdk_backend.py', 'SdkBackend._host_orphan_recover', 'carrier', 'ht.HostTransport.from_journal(hdir)', 1):
        ('path', "kernel; RESIDUAL (queued): the replay transport over the orphan's directory, by path"),
    ('kernel/sdk_backend.py', 'SdkBackend._host_orphan_recover', 'mint', 'ht.remove_host_dir(...)', 1):
        ('enters', "kernel; the orphan road's removal, by descriptors"),
    ('kernel/sdk_backend.py', 'SdkBackend._host_ended', 'mint', '_ht().remove_host_dir(...)', 1):
        ('enters', "kernel; the ended road's removal, by descriptors"),
    ('kernel/sdk_backend.py', 'SdkBackend._file_refused_launch_context', 'carrier', '_ht().host_log_rows(dir_fd=dir_fd)', 1):
        ('fd', 'kernel; the descriptor forwarded to the rows read'),
    ('kernel/sdk_backend.py', 'SdkBackend._record_refused_launch_position', 'carrier', '_ht()._open_host_log(dir_fd)', 1):
        ('fd', 'kernel; the descriptor forwarded to the open'),
    ('kernel/sdk_backend.py', 'SdkBackend._file_host_log_rows', 'mint', '_ht().host_dir(...)', 1):
        ('path', "kernel; the served road's binding"),
    ('kernel/sdk_backend.py', 'SdkBackend._file_host_log_rows', 'read_text', 'p', 1):
        ('by-path', "kernel; RESIDUAL (queued), THE SERVED ROAD: host.log read by path at the hello and at the exit, after the spawn road's descriptors are closed"),
    ('kernel/sdk_backend.py', 'SdkBackend._end_host_by_lease', 'mint', 'ht.host_sock(...)', 1):
        ('path', 'kernel; the published path for the end by lease'),
    ('kernel/sdk_backend.py', 'SdkBackend._end_host_by_lease', 'carrier', 'ht.HostTransport(str(sock))', 1):
        ('path', 'kernel; RESIDUAL (queued): the end-by-lease road hands the published path to the transport (its connect, above)'),
}

ORIGINS = {
    ('kernel/host_transport.py', '_open_dir_nofollow', 'os.open', 'name', 1):
        (('fd', 'kernel/host_transport.py', '_open_dir_nofollow', 'os.open(name, _DIR_FLAGS, dir_fd=dir_fd)', 1), ('fd', 'kernel/host_transport.py', 'open_host_dirs', '_open_dir_nofollow(str(hosts_path), "hosts directory", hosts_path)', 1), ('path', 'kernel/host_transport.py', 'open_host_dirs', '"hosts"', 1), ('path', 'kernel/host_transport.py', 'remove_host_dir', '"hosts"', 1)),
    ('kernel/host_transport.py', '_open_dir_nofollow', 'os.lstat', 'name', 1):
        (('fd', 'kernel/host_transport.py', '_open_dir_nofollow', 'os.open(name, _DIR_FLAGS, dir_fd=dir_fd)', 1), ('fd', 'kernel/host_transport.py', 'open_host_dirs', '_open_dir_nofollow(str(hosts_path), "hosts directory", hosts_path)', 1), ('path', 'kernel/host_transport.py', 'open_host_dirs', '"hosts"', 1), ('path', 'kernel/host_transport.py', 'remove_host_dir', '"hosts"', 1)),
    ('kernel/host_transport.py', '_open_dir_nofollow', 'os.fstat', 'fd', 1):
        (('fd', 'kernel/host_transport.py', '_open_dir_nofollow', 'os.open(name, _DIR_FLAGS, dir_fd=dir_fd)', 1),),
    ('kernel/host_transport.py', 'open_host_dirs', 'carrier', '_open_dir_nofollow(str(hosts_path), hosts_path)', 1):
        (),
    ('kernel/host_transport.py', 'open_host_dirs', 'carrier', '_open_dir_nofollow(hosts_path / str(sid), dir_fd=hfd)', 1):
        (),
    ('kernel/host_transport.py', 'open_host_dirs', 'carrier', 'HostDirs(hfd, dfd, hosts_path / str(sid))', 1):
        (),
    ('kernel/host_transport.py', '_open_file_nofollow', 'os.open', 'name', 1):
        (('fd', 'kernel/host_transport.py', '_open_dir_nofollow', 'os.open(name, _DIR_FLAGS, dir_fd=dir_fd)', 1), ('fd', 'kernel/host_transport.py', 'open_host_dirs', '_open_dir_nofollow(str(sid), "host directory", hosts_path / str(sid), di', 1)),
    ('kernel/host_transport.py', 'host_stderr_open', 'mint', '_open_file_nofollow(...)', 1):
        (),
    ('kernel/host_transport.py', 'host_stderr_open', 'os.fchmod', 'fd', 1):
        (('fd', 'kernel/host_transport.py', '_open_file_nofollow', 'os.open(name, flags | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0), 0o600', 1), ('fd', 'kernel/host_transport.py', 'host_stderr_open', '_open_file_nofollow("host.stderr", os.O_WRONLY | os.O_CREAT | os.O_APPEN', 1)),
    ('kernel/host_transport.py', 'host_stderr_size', 'os.stat', '"host.stderr"', 1):
        (('fd', 'kernel/host_transport.py', '_open_dir_nofollow', 'os.open(name, _DIR_FLAGS, dir_fd=dir_fd)', 1), ('fd', 'kernel/host_transport.py', 'open_host_dirs', '_open_dir_nofollow(str(sid), "host directory", hosts_path / str(sid), di', 1)),
    ('kernel/host_transport.py', '_rmtree_at', 'os.open', 'name', 1):
        (('fd', 'kernel/host_transport.py', '_open_dir_nofollow', 'os.open(name, _DIR_FLAGS, dir_fd=dir_fd)', 1), ('fd', 'kernel/host_transport.py', '_rmtree_at', 'os.open(name, _DIR_FLAGS, dir_fd=dir_fd)', 1), ('fd', 'kernel/host_transport.py', 'remove_host_dir', '_open_dir_nofollow(str(hosts_path), "hosts directory", hosts_path, priva', 1)),
    ('kernel/host_transport.py', '_rmtree_at', 'os.fstat', 'fd', 1):
        (('fd', 'kernel/host_transport.py', '_rmtree_at', 'os.open(name, _DIR_FLAGS, dir_fd=dir_fd)', 1),),
    ('kernel/host_transport.py', '_rmtree_at', 'os.scandir', 'fd', 1):
        (('fd', 'kernel/host_transport.py', '_rmtree_at', 'os.open(name, _DIR_FLAGS, dir_fd=dir_fd)', 1),),
    ('kernel/host_transport.py', '_rmtree_at', 'carrier', '_rmtree_at(fd)', 1):
        (),
    ('kernel/host_transport.py', '_rmtree_at', 'os.unlink', 'e.name', 1):
        (('fd', 'kernel/host_transport.py', '_rmtree_at', 'os.open(name, _DIR_FLAGS, dir_fd=dir_fd)', 1),),
    ('kernel/host_transport.py', '_rmtree_at', 'os.rmdir', 'name', 1):
        (('fd', 'kernel/host_transport.py', '_open_dir_nofollow', 'os.open(name, _DIR_FLAGS, dir_fd=dir_fd)', 1), ('fd', 'kernel/host_transport.py', '_rmtree_at', 'os.open(name, _DIR_FLAGS, dir_fd=dir_fd)', 1), ('fd', 'kernel/host_transport.py', 'remove_host_dir', '_open_dir_nofollow(str(hosts_path), "hosts directory", hosts_path, priva', 1)),
    ('kernel/host_transport.py', 'remove_host_dir', 'carrier', '_open_dir_nofollow(str(hosts_path), hosts_path)', 1):
        (),
    ('kernel/host_transport.py', 'remove_host_dir', 'carrier', '_rmtree_at(hfd)', 1):
        (),
    ('kernel/host_transport.py', 'remove_host_dir', 'os.stat', 'str(sid)', 1):
        (('fd', 'kernel/host_transport.py', '_open_dir_nofollow', 'os.open(name, _DIR_FLAGS, dir_fd=dir_fd)', 1), ('fd', 'kernel/host_transport.py', 'remove_host_dir', '_open_dir_nofollow(str(hosts_path), "hosts directory", hosts_path, priva', 1)),
    ('kernel/host_transport.py', '_open_host_log', 'open', 'host_dir(state_dir, sid) / "host.log"', 1):
        (('path', 'kernel/host_transport.py', '_open_host_log', 'host_dir(state_dir, sid)', 1), ('path', 'kernel/host_transport.py', 'host_dir', '"hosts"', 1)),
    ('kernel/host_transport.py', '_open_host_log', 'mint', 'host_dir(...)', 1):
        (),
    ('kernel/host_transport.py', '_open_host_log', 'os.open', '"host.log"', 1):
        (('fd', 'kernel/host_transport.py', '_open_dir_nofollow', 'os.open(name, _DIR_FLAGS, dir_fd=dir_fd)', 1), ('fd', 'kernel/host_transport.py', 'open_host_dirs', '_open_dir_nofollow(str(sid), "host directory", hosts_path / str(sid), di', 1)),
    ('kernel/host_transport.py', '_open_host_log', 'os.fdopen', 'fd', 1):
        (('fd', 'kernel/host_transport.py', '_open_host_log', 'os.open("host.log", os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC', 1),),
    ('kernel/host_transport.py', 'host_log_mark', 'os.stat', '"host.log"', 1):
        (('fd', 'kernel/host_transport.py', '_open_dir_nofollow', 'os.open(name, _DIR_FLAGS, dir_fd=dir_fd)', 1), ('fd', 'kernel/host_transport.py', 'open_host_dirs', '_open_dir_nofollow(str(sid), "host directory", hosts_path / str(sid), di', 1)),
    ('kernel/host_transport.py', 'host_log_mark', 'os.stat', 'host_dir(state_dir, sid) / "host.log"', 1):
        (('path', 'kernel/host_transport.py', 'host_dir', '"hosts"', 1), ('path', 'kernel/host_transport.py', 'host_log_mark', 'host_dir(state_dir, sid)', 1)),
    ('kernel/host_transport.py', 'host_log_mark', 'mint', 'host_dir(...)', 1):
        (),
    ('kernel/host_transport.py', 'host_log_rows', 'carrier', '_open_host_log(dir_fd)', 1):
        (),
    ('kernel/host_transport.py', 'host_exit_reason', 'carrier', 'host_log_rows(dir_fd=dir_fd)', 1):
        (),
    ('kernel/host_transport.py', 'helper_shape_refusal', 'mint', 'host_dir(...)', 1):
        (),
    ('kernel/host_transport.py', 'write_spawn_spec', 'mint', 'sh.hosts_dir(...)', 1):
        (),
    ('kernel/host_transport.py', 'write_spawn_spec', 'carrier', 'sh.owner_only_dir(host_dir(state_dir, sid))', 1):
        (),
    ('kernel/host_transport.py', 'write_spawn_spec', 'mint', 'host_dir(...)', 1):
        (),
    ('kernel/host_transport.py', 'write_spawn_spec', 'mint', 'helper_shape_refusal(...)', 1):
        (),
    ('kernel/host_transport.py', 'write_spawn_spec', 'mint', 'host_dir(...)', 2):
        (),
    ('kernel/host_transport.py', 'write_spawn_spec', 'mint', 'open_host_dirs(...)', 1):
        (),
    ('kernel/host_transport.py', 'write_spawn_spec', 'mint', '_open_file_nofollow(...)', 1):
        (),
    ('kernel/host_transport.py', 'write_spawn_spec', 'os.fchmod', 'fd', 1):
        (('fd', 'kernel/host_transport.py', '_open_file_nofollow', 'os.open(name, flags | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0), 0o600', 1), ('fd', 'kernel/host_transport.py', 'write_spawn_spec', '_open_file_nofollow("spawn.json", os.O_WRONLY | os.O_CREAT | os.O_TRUNC,', 1)),
    ('kernel/host_transport.py', 'write_spawn_spec', 'os.fdopen', 'fd', 1):
        (('fd', 'kernel/host_transport.py', '_open_file_nofollow', 'os.open(name, flags | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0), 0o600', 1), ('fd', 'kernel/host_transport.py', 'write_spawn_spec', '_open_file_nofollow("spawn.json", os.O_WRONLY | os.O_CREAT | os.O_TRUNC,', 1)),
    ('kernel/host_transport.py', 'HostTransport.from_journal', 'carrier', 'cls(journal_dir=journal_dir)', 1):
        (),
    ('kernel/host_transport.py', 'HostTransport.connect', 'asyncio.open_unix_connection', 'self.sock_path', 1):
        (('path', 'kernel/host_transport.py', 'host_sock', '"hosts"', 1), ('path', 'kernel/sdk_backend.py', 'SdkBackend._end_host_by_lease', 'ht.host_sock(self.state_dir, sid)', 1), ('path', 'kernel/sdk_backend.py', 'SdkBackend._host_transport_for', 'ht.host_sock(self.state_dir, sess.sid)', 1), ('path', 'kernel/sdk_backend.py', 'SdkBackend._host_transport_for', 'ht.host_sock(self.state_dir, sess.sid)', 2)),
    ('kernel/host_transport.py', 'HostTransport._read_journal', 'carrier', 'sh.read_journal_dir(self.journal_dir)', 1):
        (),
    ('kernel/session_host.py', 'Journal.__init__', 'carrier', 'owner_only_dir(directory)', 1):
        (),
    ('kernel/session_host.py', 'Journal._open_segment', 'open', 'self._path(first)', 1):
        (('path', 'kernel/session_host.py', 'Journal.__init__', 'owner_only_dir(directory, "host directory")', 1), ('path', 'kernel/session_host.py', 'Journal._open_segment', 'self._path(first)', 1), ('path', 'kernel/session_host.py', 'SessionHost.__init__', 'spec_path: the path under hosts/ the kernel hands the host in argv (decl', 1)),
    ('kernel/session_host.py', 'Journal._open_segment', 'mint', 'self._path(...)', 1):
        (),
    ('kernel/session_host.py', 'Journal._persist_gaps', 'open', 'tmp', 1):
        (('path', 'kernel/session_host.py', 'Journal.__init__', 'owner_only_dir(directory, "host directory")', 1), ('path', 'kernel/session_host.py', 'SessionHost.__init__', 'spec_path: the path under hosts/ the kernel hands the host in argv (decl', 1)),
    ('kernel/session_host.py', 'Journal._persist_gaps', 'os.replace', 'tmp', 1):
        (('path', 'kernel/session_host.py', 'Journal.__init__', 'owner_only_dir(directory, "host directory")', 1), ('path', 'kernel/session_host.py', 'SessionHost.__init__', 'spec_path: the path under hosts/ the kernel hands the host in argv (decl', 1)),
    ('kernel/session_host.py', 'Journal._persist_gaps', 'os.unlink', 'tmp', 1):
        (('path', 'kernel/session_host.py', 'Journal.__init__', 'owner_only_dir(directory, "host directory")', 1), ('path', 'kernel/session_host.py', 'SessionHost.__init__', 'spec_path: the path under hosts/ the kernel hands the host in argv (decl', 1)),
    ('kernel/session_host.py', 'Journal._turn_boundary', 'os.unlink', 'self._path(seg)', 1):
        (('path', 'kernel/session_host.py', 'Journal.__init__', 'owner_only_dir(directory, "host directory")', 1), ('path', 'kernel/session_host.py', 'Journal._turn_boundary', 'self._path(seg)', 1), ('path', 'kernel/session_host.py', 'SessionHost.__init__', 'spec_path: the path under hosts/ the kernel hands the host in argv (decl', 1)),
    ('kernel/session_host.py', 'Journal._turn_boundary', 'mint', 'self._path(...)', 1):
        (),
    ('kernel/session_host.py', 'Journal.read_from', 'open', 'self._path(seg)', 1):
        (('path', 'kernel/session_host.py', 'Journal.__init__', 'owner_only_dir(directory, "host directory")', 1), ('path', 'kernel/session_host.py', 'Journal.read_from', 'self._path(seg)', 1), ('path', 'kernel/session_host.py', 'SessionHost.__init__', 'spec_path: the path under hosts/ the kernel hands the host in argv (decl', 1)),
    ('kernel/session_host.py', 'Journal.read_from', 'mint', 'self._path(...)', 1):
        (),
    ('kernel/session_host.py', 'read_journal_dir', 'glob', 'd', 1):
        (('path', 'kernel/host_transport.py', 'host_dir', '"hosts"', 1), ('path', 'kernel/sdk_backend.py', 'SdkBackend._host_orphan_recover', 'ht.host_dir(self.state_dir, sess.sid)', 1)),
    ('kernel/session_host.py', 'read_journal_dir', 'read_text', 'd / "gaps.json"', 1):
        (('path', 'kernel/host_transport.py', 'host_dir', '"hosts"', 1), ('path', 'kernel/sdk_backend.py', 'SdkBackend._host_orphan_recover', 'ht.host_dir(self.state_dir, sess.sid)', 1)),
    ('kernel/session_host.py', 'read_journal_dir', 'open', 'p', 1):
        (('path', 'kernel/host_transport.py', 'host_dir', '"hosts"', 1), ('path', 'kernel/sdk_backend.py', 'SdkBackend._host_orphan_recover', 'ht.host_dir(self.state_dir, sess.sid)', 1)),
    ('kernel/session_host.py', 'owner_only_dir', 'mkdir', 'd', 1):
        (('path', 'kernel/host_transport.py', 'host_dir', '"hosts"', 1), ('path', 'kernel/host_transport.py', 'write_spawn_spec', 'host_dir(state_dir, sid)', 2), ('path', 'kernel/session_host.py', 'SessionHost.__init__', 'spec_path: the path under hosts/ the kernel hands the host in argv (decl', 1), ('path', 'kernel/session_host.py', 'hosts_dir', '"hosts"', 1)),
    ('kernel/session_host.py', 'owner_only_dir', 'os.lstat', 'd', 1):
        (('path', 'kernel/host_transport.py', 'host_dir', '"hosts"', 1), ('path', 'kernel/host_transport.py', 'write_spawn_spec', 'host_dir(state_dir, sid)', 2), ('path', 'kernel/session_host.py', 'SessionHost.__init__', 'spec_path: the path under hosts/ the kernel hands the host in argv (decl', 1), ('path', 'kernel/session_host.py', 'hosts_dir', '"hosts"', 1)),
    ('kernel/session_host.py', 'owner_only_dir', 'os.chmod', 'd', 1):
        (('path', 'kernel/host_transport.py', 'host_dir', '"hosts"', 1), ('path', 'kernel/host_transport.py', 'write_spawn_spec', 'host_dir(state_dir, sid)', 2), ('path', 'kernel/session_host.py', 'SessionHost.__init__', 'spec_path: the path under hosts/ the kernel hands the host in argv (decl', 1), ('path', 'kernel/session_host.py', 'hosts_dir', '"hosts"', 1)),
    ('kernel/session_host.py', 'owner_only_dir', 'os.lstat', 'd', 2):
        (('path', 'kernel/host_transport.py', 'host_dir', '"hosts"', 1), ('path', 'kernel/host_transport.py', 'write_spawn_spec', 'host_dir(state_dir, sid)', 2), ('path', 'kernel/session_host.py', 'SessionHost.__init__', 'spec_path: the path under hosts/ the kernel hands the host in argv (decl', 1), ('path', 'kernel/session_host.py', 'hosts_dir', '"hosts"', 1)),
    ('kernel/session_host.py', 'hosts_dir', 'carrier', 'owner_only_dir(root / "hosts")', 1):
        (),
    ('kernel/session_host.py', 'SessionHost.__init__', 'open', 'self.spec_path', 1):
        (('path', 'kernel/session_host.py', 'SessionHost.__init__', 'spec_path: the path under hosts/ the kernel hands the host in argv (decl', 1),),
    ('kernel/session_host.py', 'SessionHost.__init__', 'mint', 'hosts_dir(...)', 1):
        (),
    ('kernel/session_host.py', 'SessionHost.__init__', 'carrier', 'Journal(self.dir)', 1):
        (),
    ('kernel/session_host.py', 'SessionHost.log', 'open', 'self.log_path', 1):
        (('path', 'kernel/session_host.py', 'SessionHost.__init__', 'spec_path: the path under hosts/ the kernel hands the host in argv (decl', 1),),
    ('kernel/session_host.py', 'SessionHost._sweep_stale_temps', 'glob', 'self.sock_path.parent', 1):
        (('path', 'kernel/session_host.py', 'SessionHost.__init__', '"hosts"', 1),),
    ('kernel/session_host.py', 'SessionHost._sweep_stale_temps', 'unlink', 'p', 1):
        (('path', 'kernel/session_host.py', 'SessionHost.__init__', '"hosts"', 1),),
    ('kernel/session_host.py', 'SessionHost._prepare_socket', 'mint', 'hosts_dir(...)', 1):
        (),
    ('kernel/session_host.py', 'SessionHost._prepare_socket', 'unlink', 'self.sock_path', 1):
        (('path', 'kernel/session_host.py', 'SessionHost.__init__', '"hosts"', 1),),
    ('kernel/session_host.py', 'SessionHost._serve_socket', 'os.lstat', 'self.sock_path.parent', 1):
        (('path', 'kernel/session_host.py', 'SessionHost.__init__', '"hosts"', 1),),
    ('kernel/session_host.py', 'SessionHost._serve_socket', 'asyncio.start_unix_server', 'str(self.sock_tmp)', 1):
        (('path', 'kernel/session_host.py', 'SessionHost.__init__', '"hosts"', 1),),
    ('kernel/session_host.py', 'SessionHost._serve_socket', 'os.chmod', 'self.sock_tmp', 1):
        (('path', 'kernel/session_host.py', 'SessionHost.__init__', '"hosts"', 1),),
    ('kernel/session_host.py', 'SessionHost._serve_socket', 'os.rename', 'self.sock_tmp', 1):
        (('path', 'kernel/session_host.py', 'SessionHost.__init__', '"hosts"', 1),),
    ('kernel/session_host.py', 'SessionHost._serve_socket', 'unlink', 'self.sock_tmp', 1):
        (('path', 'kernel/session_host.py', 'SessionHost.__init__', '"hosts"', 1),),
    ('kernel/session_host.py', 'SessionHost.run', 'write_text', 'self.dir / "identity.json"', 1):
        (('path', 'kernel/session_host.py', 'SessionHost.__init__', 'spec_path: the path under hosts/ the kernel hands the host in argv (decl', 1),),
    ('kernel/session_host.py', 'SessionHost.run', 'unlink', 'self.sock_path', 1):
        (('path', 'kernel/session_host.py', 'SessionHost.__init__', '"hosts"', 1),),
    ('kernel/session_host.py', 'main', 'mint', 'SessionHost(...)', 1):
        (),
    ('kernel/sdk_backend.py', 'SdkBackend._host_lease_applies', 'mint', '_ht().host_dir(...)', 1):
        (),
    ('kernel/sdk_backend.py', 'SdkBackend._host_lease_applies', 'exists', 'hdir / "identity.json"', 1):
        (('path', 'kernel/host_transport.py', 'host_dir', '"hosts"', 1), ('path', 'kernel/sdk_backend.py', 'SdkBackend._host_lease_applies', '_ht().host_dir(self.state_dir, sess.sid)', 1)),
    ('kernel/sdk_backend.py', 'SdkBackend._host_lease_applies', 'glob', 'hdir', 1):
        (('path', 'kernel/host_transport.py', 'host_dir', '"hosts"', 1), ('path', 'kernel/sdk_backend.py', 'SdkBackend._host_lease_applies', '_ht().host_dir(self.state_dir, sess.sid)', 1)),
    ('kernel/sdk_backend.py', 'SdkBackend._host_transport_for', 'mint', 'ht.host_dir(...)', 1):
        (),
    ('kernel/sdk_backend.py', 'SdkBackend._host_transport_for', 'exists', 'hdir', 1):
        (('path', 'kernel/host_transport.py', 'host_dir', '"hosts"', 1), ('path', 'kernel/sdk_backend.py', 'SdkBackend._host_transport_for', 'ht.host_dir(self.state_dir, sess.sid)', 1)),
    ('kernel/sdk_backend.py', 'SdkBackend._host_transport_for', 'carrier', 'self._new_host_transport(ht.host_sock(self.state_dir, sess.sid))', 1):
        (),
    ('kernel/sdk_backend.py', 'SdkBackend._host_transport_for', 'mint', 'ht.host_sock(...)', 1):
        (),
    ('kernel/sdk_backend.py', 'SdkBackend._host_transport_for', 'mint', 'ht.write_spawn_spec(...)', 1):
        (),
    ('kernel/sdk_backend.py', 'SdkBackend._host_transport_for', 'mint', 'ht.open_host_dirs(...)', 1):
        (),
    ('kernel/sdk_backend.py', 'SdkBackend._host_transport_for', 'mint', 'ht.host_sock(...)', 2):
        (),
    ('kernel/sdk_backend.py', 'SdkBackend._host_transport_for', 'os.unlink', 'sock.name', 1):
        (('fd', 'kernel/host_transport.py', '_open_dir_nofollow', 'os.open(name, _DIR_FLAGS, dir_fd=dir_fd)', 1), ('fd', 'kernel/host_transport.py', 'open_host_dirs', '_open_dir_nofollow(str(hosts_path), "hosts directory", hosts_path)', 1)),
    ('kernel/sdk_backend.py', 'SdkBackend._host_transport_for', 'carrier', 'ht.host_log_mark(dir_fd=dirs.dir)', 1):
        (),
    ('kernel/sdk_backend.py', 'SdkBackend._host_transport_for', 'carrier', 'self._spawn_host(spec_path)', 1):
        (),
    ('kernel/sdk_backend.py', 'SdkBackend._host_transport_for', 'exists', 'sock', 1):
        (('path', 'kernel/host_transport.py', 'host_sock', '"hosts"', 1), ('path', 'kernel/sdk_backend.py', 'SdkBackend._host_transport_for', 'ht.host_sock(self.state_dir, sess.sid)', 2)),
    ('kernel/sdk_backend.py', 'SdkBackend._host_transport_for', 'carrier', 'ht.host_exit_reason(dir_fd=dirs.dir)', 1):
        (),
    ('kernel/sdk_backend.py', 'SdkBackend._host_transport_for', 'carrier', 'self._file_refused_launch_context(dir_fd=dirs.dir)', 1):
        (),
    ('kernel/sdk_backend.py', 'SdkBackend._host_transport_for', 'carrier', 'self._record_refused_launch_position(dir_fd=dirs.dir)', 1):
        (),
    ('kernel/sdk_backend.py', 'SdkBackend._host_transport_for', 'carrier', 'ht.host_exit_reason(dir_fd=dirs.dir)', 2):
        (),
    ('kernel/sdk_backend.py', 'SdkBackend._host_transport_for', 'carrier', 'self._file_refused_launch_context(dir_fd=dirs.dir)', 2):
        (),
    ('kernel/sdk_backend.py', 'SdkBackend._host_transport_for', 'carrier', 'self._record_refused_launch_position(dir_fd=dirs.dir)', 2):
        (),
    ('kernel/sdk_backend.py', 'SdkBackend._host_transport_for', 'carrier', 'self._new_host_transport(sock)', 1):
        (),
    ('kernel/sdk_backend.py', 'SdkBackend._new_host_transport', 'carrier', 'ht.HostTransport(str(sock))', 1):
        (),
    ('kernel/sdk_backend.py', 'SdkBackend._spawn_host', 'mint', 'ht.open_host_dirs(...)', 1):
        (),
    ('kernel/sdk_backend.py', 'SdkBackend._spawn_host', 'mint', 'ht.host_stderr_open(...)', 1):
        (),
    ('kernel/sdk_backend.py', 'SdkBackend._spawn_host', 'subprocess.Popen', 'argv', 1):
        (('fd', 'kernel/host_transport.py', '_open_file_nofollow', 'os.open(name, flags | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0), 0o600', 1), ('fd', 'kernel/host_transport.py', 'host_stderr_open', '_open_file_nofollow("host.stderr", os.O_WRONLY | os.O_CREAT | os.O_APPEN', 1), ('fd', 'kernel/sdk_backend.py', 'SdkBackend._spawn_host', 'ht.host_stderr_open(dirs)', 1), ('path', 'kernel/host_transport.py', 'host_dir', '"hosts"', 1), ('path', 'kernel/host_transport.py', 'write_spawn_spec', 'host_dir(state_dir, sid)', 1), ('path', 'kernel/sdk_backend.py', 'SdkBackend._host_transport_for', 'ht.write_spawn_spec(self.state_dir, sess.sid, spec)', 1)),
    ('kernel/sdk_backend.py', 'SdkBackend._host_orphan_recover', 'mint', 'ht.host_dir(...)', 1):
        (),
    ('kernel/sdk_backend.py', 'SdkBackend._host_orphan_recover', 'read_text', 'hdir / "identity.json"', 1):
        (('path', 'kernel/host_transport.py', 'host_dir', '"hosts"', 1), ('path', 'kernel/sdk_backend.py', 'SdkBackend._host_orphan_recover', 'ht.host_dir(self.state_dir, sess.sid)', 1)),
    ('kernel/sdk_backend.py', 'SdkBackend._host_orphan_recover', 'carrier', 'ht.sh.read_journal_dir(hdir)', 1):
        (),
    ('kernel/sdk_backend.py', 'SdkBackend._host_orphan_recover', 'glob', 'hdir', 1):
        (('path', 'kernel/host_transport.py', 'host_dir', '"hosts"', 1), ('path', 'kernel/sdk_backend.py', 'SdkBackend._host_orphan_recover', 'ht.host_dir(self.state_dir, sess.sid)', 1)),
    ('kernel/sdk_backend.py', 'SdkBackend._host_orphan_recover', 'carrier', 'ht.HostTransport.from_journal(hdir)', 1):
        (),
    ('kernel/sdk_backend.py', 'SdkBackend._host_orphan_recover', 'mint', 'ht.remove_host_dir(...)', 1):
        (),
    ('kernel/sdk_backend.py', 'SdkBackend._host_ended', 'mint', '_ht().remove_host_dir(...)', 1):
        (),
    ('kernel/sdk_backend.py', 'SdkBackend._file_refused_launch_context', 'carrier', '_ht().host_log_rows(dir_fd=dir_fd)', 1):
        (),
    ('kernel/sdk_backend.py', 'SdkBackend._record_refused_launch_position', 'carrier', '_ht()._open_host_log(dir_fd)', 1):
        (),
    ('kernel/sdk_backend.py', 'SdkBackend._file_host_log_rows', 'mint', '_ht().host_dir(...)', 1):
        (),
    ('kernel/sdk_backend.py', 'SdkBackend._file_host_log_rows', 'read_text', 'p', 1):
        (('path', 'kernel/host_transport.py', 'host_dir', '"hosts"', 1), ('path', 'kernel/sdk_backend.py', 'SdkBackend._file_host_log_rows', '_ht().host_dir(self.state_dir, sess.sid)', 1)),
    ('kernel/sdk_backend.py', 'SdkBackend._end_host_by_lease', 'mint', 'ht.host_sock(...)', 1):
        (),
    ('kernel/sdk_backend.py', 'SdkBackend._end_host_by_lease', 'carrier', 'ht.HostTransport(str(sock))', 1):
        (),
}


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


class HostsPathCensus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.census = derive()

    def test_no_other_product_module_makes_a_syscall_on_a_path_under_hosts(self):
        outside = {rel: [(t.node.lineno, t.fn.qual, t.op, t.arg_text) for t in c.terminals.values()]
                   for rel, c in wide_census().items() if c.terminals}
        self.assertEqual(outside, {}, "a module outside the three uses a path under hosts/: %r" % (outside,))

    def test_the_derived_set_equals_the_published_list_and_is_not_empty(self):
        derived = self.census.derived()
        self.assertGreater(len(derived), 0, "the census found no use of a path under hosts/: the seed rule is broken")
        self.assertGreater(len(ROADS), 0, "the published list is empty")
        self.assertEqual(sorted(ROADS), sorted(ORIGINS), "every published member has a road and a provenance")
        missing = sorted(k for k in ROADS if k not in derived)
        new = sorted(k for k in derived if k not in ROADS)
        changed = sorted((k, ROADS[k][0], derived[k][0]) for k in ROADS if k in derived and ROADS[k][0] != derived[k][0])
        origins = sorted((k, ORIGINS[k], derived[k][1]) for k in ROADS if k in derived and tuple(ORIGINS[k]) != derived[k][1])
        self.assertEqual((missing, new, changed, origins), ([], [], [], []),
                         "the census at this head differs from the published list (a new member needs its road written in "
                         "ROADS and its provenance in ORIGINS, from `python3 tests/test_hosts_path_census.py --expected`): "
                         "missing %r, new %r, class changed %r, origins changed %r" % (missing, new, changed, origins))

    def test_no_use_escapes_the_walk(self):
        esc = [k for k, v in ROADS.items() if v[0] == "escape"] + [k for k in self.census.derived() if k[2] == "escape"]
        self.assertEqual(esc, [], "an escape is a value the census could not follow; classify it or follow it: %r" % (esc,))

    def test_the_residual_the_queued_item_owns_is_exactly_the_by_path_reads_labelled_so(self):
        """The road words are not decoration: every member whose road says RESIDUAL is a by-path terminal or a carrier
        of a path (never a descriptor use), and every kernel-side by-path terminal outside the helpers, the guards and
        the unreachable arms is labelled RESIDUAL. A kernel by-path read that is none of those is a new road the
        queued item does not own yet."""
        for k, (mech, road) in ROADS.items():
            if "RESIDUAL" in road:
                self.assertIn(mech, ("by-path", "path"), "%r: a residual is a by-path use, not %s" % (k, mech))
            if k[0] != "kernel/session_host.py" and mech == "by-path" and k[2] not in ("carrier", "mint"):
                self.assertTrue(any(w in road for w in ("RESIDUAL", "HELPER", "guard", "unreachable today")),
                                "%r: a kernel by-path syscall on a path under hosts/ is residual, a helper, a guard or unreachable; this one is labelled %r" % (k, road))

    def test_the_eleven_planted_reader_shapes_are_all_found(self):
        """The instrument's own check, the shapes of round 6's plants (extra5-1's eleven: an f-string in two steps, a
        join through a variable-held base, single-quoted division, a leaf from a dict, a helper's directory globbed by
        the caller, a bytes path, a path through os.fsdecode, a renamed helper, %-formatting one segment per part, a
        splatted tuple, and the full literal wrapped across two lines), appended to a scratch copy of kernel/sdk_backend.py:
        the census over the copy finds a by-path terminal in every one, and nothing else new outside them. The published
        grep found 0 of 11; a narrowing of the seed or the follow rules reds here."""
        import shutil
        import tempfile
        scratch = tempfile.mkdtemp(prefix="hosts-census-")
        self.addCleanup(shutil.rmtree, scratch, True)
        for f in FILES:
            os.makedirs(os.path.dirname(os.path.join(scratch, f)), exist_ok=True)
            shutil.copy(os.path.join(ROOT, f), os.path.join(scratch, f))
        with open(os.path.join(scratch, "kernel/sdk_backend.py"), "a") as fh:
            fh.write(PLANTED_READERS)
        base = set(self.census.derived())
        found, elsewhere = {}, []
        for t in Census(scratch).run().members():
            if t.key() in base:
                continue
            if t.fn.qual.startswith("_PlantedReaders.p"):
                found.setdefault(t.fn.qual.split(".")[1][:3], []).append((t.op, t.mech))
            elif not t.fn.qual.startswith("_PlantedReaders."):
                elsewhere.append(t.key())
        self.assertEqual(elsewhere, [], "the plants changed the census outside their own class")
        missing = ["p%02d" % i for i in range(1, 12) if not any(mech == "by-path" for _, mech in found.get("p%02d" % i, []))]
        self.assertEqual(missing, [], "planted by-path readers the census did not find: %r (found %r)" % (missing, found))

    def test_every_road_into_a_by_path_fallback_arm_passes_a_descriptor(self):
        holes, fns = self.census.dir_fd_forwarding()
        self.assertGreater(len(fns), 0, "no reader with a dir_fd=None fallback arm was found")
        self.assertEqual(holes, [], "a caller reaches a by-path fallback arm without a descriptor: %r" % (holes,))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    c = derive(Path(args[0]) if args else ROOT)
    if "--expected" in sys.argv:
        # the pinned view as Python, for pasting into EXPECTED after each entry's road is written by hand
        for t in c.members():
            print("    %r: (%r, %r,\n        %r)," % (t.key(), t.mech, "ROAD", t.origin_keys()))
        return
    print("SEEDS")
    for _, t in sorted(c.seeds, key=lambda x: (c.files.index(x[1].file), x[1].line)):
        print("  %s %s:%d %s  %s" % (t.kind, t.file, t.line, t.qual, t.text))
    print("MEMBERS")
    for t in c.members():
        print("%s:%d %s  %s(%s) #%d  [%s]" % (t.fn.file, t.node.lineno, t.fn.qual, t.op, t.arg_text, t.ordinal, t.mech))
        for o in sorted(set(t.origins), key=lambda o: (o.file, o.line)):
            print("      <- %s %s:%d %s  %s #%d" % (o.kind, o.file, o.line, o.qual, o.text, o.ordinal))
    roads = c.roads()
    print("terminals: %d, escapes: %d, carriers: %d, mints: %d, seeds: %d"
          % (len(c.terminals), len(c.escapes), sum(1 for r in roads if r.op == "carrier"), sum(1 for r in roads if r.op == "mint"), len(c.seeds)))
    holes, fns = c.dir_fd_forwarding()
    print("dir_fd fallback arms: %s; holes: %s" % (fns, holes))
    if "--wide" in sys.argv:
        for rel, wc in wide_census(Path(args[0]) if args else ROOT).items():
            if wc.terminals or wc.escapes or wc.seeds:
                print("WIDE %s: terminals %d, escapes %d, seeds %d" % (rel, len(wc.terminals), len(wc.escapes), len(wc.seeds)))
                for t in list(wc.terminals.values()) + list(wc.escapes.values()):
                    print("  %s:%d %s  %s(%s) [%s]" % (t.fn.file, t.node.lineno, t.fn.qual, t.op, t.arg_text, t.mech))


if __name__ == "__main__":
    main()
