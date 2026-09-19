#!/usr/bin/env python3
"""Every request Romp's own code can make to anything but 127.0.0.1, derived from the code, and the
reference's list of them held equal to the table here (2026-09-19).

Why this module exists. docs/guide.md's kernel paragraph once named the traffic that leaves the
machine as a closed list, and the list was false: kernel/kernel.py fetches the Models API and a
model-price table and posts web push notifications, and the sentence named none of them. A list kept
by hand goes stale the day a fetch is added, so the guide now states the rule (what the upload verb
sends, and that other parts of Romp make requests of their own) and points here, and
docs/reference.md's subsection "Requests Romp makes on its own" carries what this census finds
today, pinned equal to ALLOWLIST below so the prose and the code cannot drift apart (the Docs case).

What is read. Every regular Python file under kernel/, cli/ and postal/, and under bin/ the regular
files with a python shebang; bin/'s symlinks resolve into those three directories and are skipped
(pinned: every symlink's target is a scanned file). Each file is parsed and every call, list literal
and subprocess argument is matched against FORMS, a literal tuple, so a reader compares the form space
word for word with the ruling that asked for it; the FormSpace case plants one instance of every form
in a synthetic module and shows each found, so a matcher silently dropped from the scanner reds by
name. A second layer reads bin/'s shell scripts and the node manager the same way (a command word in
command position, comments, echo text and heredocs excluded), since a fetch in a shell script leaves
the machine like any other. Nothing here loads romp code or dials anything: the census is a static
read of the tree.

What the form space is, and why it is wider than the ruling's list. The ruling named the dial forms
(urllib's urlopen and Request, http.client's connections, socket.create_connection, an ssl wrap of a
client socket, a websocket dial, requests if present, and subprocess calls to curl or wget). Reading
the code found the same kind of traffic behind other tools: `git ls-remote`, `git fetch` and
`git push` (the update check, the drift watcher, the file viewer's origin probe, the linked kernels'
update and pull), `gh pr view` (the PR watch), `ssh` (the tunnels the linked kernels ride and every
command run over them), `npm install` (the bundle build's repair) and `pip install` from a URL (the
Codex runtime). A reader asking what leaves the machine needs those too, and leaving them out would
repeat the guide's mistake, so the tool class is in the space with this paragraph as the reason. The
same words are read inside shell scripts the code hands to `bash -c` (the release update's script
fetches a tag) and in bin/'s scripts.

What is outside the space, by construction and stated here rather than left implicit. A command
whose text arrives at run time is not in the code and cannot be read from it: the apiKeyHelper
command and a stored login's token command (kernel/credentials.py runs them through /bin/sh), the
watch predicates a user registers (`romp watch`), the folder and terminal opener templates a user
configures. Programs Romp starts that make requests of their own: `claude` (the agents' turns, the
judge pipeline's calls, kernel/judge.py's `claude -p`, and the login flow), `codex`, the Codex SDK,
and `install.sh` inside the release update. A browser opened on the dashboard's own 127.0.0.1
address. Directories outside the runtime: tests/, scripts/, tools/, assets/, ui/, hooks/ and the
repo-root installers, which are the maintainers' and the installer's, not the kernel's. One connect
that sends nothing: kernel/kernel.py's `_primary_addr` connects a UDP socket to a documentation
address to learn the local address the routing table picks; a UDP connect sends no datagram, the
scanner classes it route-probe by the socket's SOCK_DGRAM constructor, and ROUTE_PROBES pins it in
both directions like the allowlist.

How a site is classified. A dial form's host or URL argument is rendered to the set of strings its
constants can spell, following names through assignments in the enclosing functions and the module,
for-loop iterables, a function's return values and, for a parameter, the arguments its callers pass
(each a hop, six hops at most; anything unresolved renders as a placeholder). The site is loopback
only when every rendering has 127.0.0.1 as its host, a bare host or a URL's; a placeholder host, a
`localhost`, or a lookalike such as `127.0.0.1.example` is outbound, the safe side. A tool form is
outbound unless it is curl or wget aimed at 127.0.0.1 alone. Every outbound site must match an
ALLOWLIST entry by file and function (the outermost def, with its class when it is a method) and
carry a kind the entry names, else the census reds naming the file, the line and the call; every entry
must match at least one site, else the census reds naming the entry. The same two conditions hold
for the shell layer's SHELL_ALLOWLIST and for ROUTE_PROBES.
"""
import ast
import itertools
import os
import re
import tempfile
import unittest
from collections import namedtuple

import romp_load  # noqa: F401  the direct run's floor (the tests package's temp root) lands at this import
# Hermetic state BEFORE the loads: they resolve their state root at import time, and only pytest runs
# conftest's floor (a bare unittest or script run otherwise writes REAL state). Nothing here loads romp
# code; the preamble is carried because every module in this directory carries it.
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
SCOPE_DIRS = ("kernel", "cli", "postal", "bin")
LOOPBACK_HOST = "127.0.0.1"
MAX_HOPS = 6

# The form space: (kind, what the scanner matches). A literal tuple, compared word for word with the
# ruling's list by a reader and with the planted module by the FormSpace case. The module docstring
# says why the tool, shell-string and GIT_SSH_COMMAND kinds are in it.
FORMS = (
    ("urlopen", "urllib.request.urlopen(url_or_request, ...)"),
    ("Request", "urllib.request.Request(url, ...)"),
    ("opener.open", "opener.open(request, ...) on an opener bound from urllib.request.build_opener(...)"),
    ("HTTPConnection", "http.client.HTTPConnection(host, ...)"),
    ("HTTPSConnection", "http.client.HTTPSConnection(host, ...)"),
    ("create_connection", "socket.create_connection((host, port), ...)"),
    ("socket.connect", "s.connect((host, port)) or s.connect_ex(...) on a socket bound from socket.socket(...); "
                       "a SOCK_DGRAM socket's connect sends nothing and is classed route-probe"),
    ("wrap_socket", "ssl.wrap_socket(sock, ...) or ctx.wrap_socket(sock, ...) on an SSLContext"),
    ("open_connection", "asyncio.open_connection(host, port, ...)"),
    ("http-library", "any call into requests, httpx, aiohttp or urllib3"),
    ("websocket", "websockets.connect(url), websocket.create_connection(url) or websocket.WebSocketApp(url)"),
    ("tool", "a command line, as a list literal anywhere or as a subprocess call's argv, that runs a network "
             "tool: curl, wget, ssh, scp, sftp, rsync or gh; git with ls-remote, fetch, push, pull or clone "
             "(also through the _git_out and _git_net_out wrappers); npm, npx, pnpm or yarn with install, ci, "
             "add or update; pip, pip3 or python -m pip with install or download"),
    ("shell-string", "a subprocess call running a shell (sh, bash or zsh with -c, shell=True, os.system, "
                     "os.popen or asyncio.create_subprocess_shell) whose script text, as far as its constants "
                     "reach, spells one of those tool commands in command position"),
    ("GIT_SSH_COMMAND", "a subprocess call whose env= spells GIT_SSH_COMMAND (git about to ride ssh)"),
)
FORM_KINDS = tuple(kind for kind, _ in FORMS)
DIAL_KINDS = ("urlopen", "Request", "opener.open", "HTTPConnection", "HTTPSConnection", "create_connection",
              "socket.connect", "wrap_socket", "open_connection", "http-library", "websocket")

TOOL_COMMANDS = ("curl", "wget", "ssh", "scp", "sftp", "rsync", "gh")
NET_GIT = ("ls-remote", "fetch", "push", "pull", "clone")
NPM_HEADS = ("npm", "npx", "pnpm", "yarn")
NET_NPM = ("install", "ci", "add", "update")
PIP_HEADS = ("pip", "pip3")
NET_PIP = ("install", "download")
GIT_WRAPPERS = ("_git_out", "_git_net_out")
SHELLS = ("sh", "bash", "zsh", "dash")
SUBPROCESS_CALLS = ("subprocess.run", "subprocess.Popen", "subprocess.check_output", "subprocess.check_call",
                    "subprocess.call", "subprocess.getoutput", "subprocess.getstatusoutput",
                    "asyncio.create_subprocess_exec", "asyncio.create_subprocess_shell", "os.system", "os.popen")
SHELL_TEXT_CALLS = ("subprocess.getoutput", "subprocess.getstatusoutput", "asyncio.create_subprocess_shell",
                    "os.system", "os.popen")
HTTP_LIBRARIES = ("requests", "httpx", "aiohttp", "urllib3")
WEBSOCKET_DIALS = ("websockets.connect", "websockets.client.connect", "websockets.sync.client.connect",
                   "websocket.create_connection", "websocket.WebSocketApp", "websocket.WebSocket")
STR_METHODS = ("rstrip", "strip", "lstrip", "lower", "upper", "format", "replace", "removesuffix",
               "removeprefix", "encode", "decode", "expanduser", "resolve")
UNKNOWN = "<?>"

Site = namedtuple("Site", "file line function kind klass tool text")     # klass: loopback | outbound | route-probe


# ---------------------------------------------------------------------------------------------------
# The command grammar, shared by list literals, shell strings the code builds, and bin/'s scripts.
# ---------------------------------------------------------------------------------------------------

def _word(w):
    return os.path.basename(str(w).strip("\"'"))


_RUNS_NEXT = ("-e", "--args", "--")     # a terminal launcher's `-e cmd`, `open --args -e cmd`, an end of options


def tool_in(words):
    """The network tool a command line runs, or None. `words` is the line in order, the command first; a word may
    be a path (its basename is read) or a rendered placeholder. Exact words, never substrings: `git config
    remote.origin.fetch` is not a fetch, and `echo "curl ..."` never reaches here because echo is the command.
    A launcher that runs the rest of its line as a command (`xterm -e ssh ...`, `open -na App --args -e ssh ...`)
    is read past the `-e`; a script handed there as one word is read as shell text."""
    words = list(words)
    while words and str(words[0]).strip("\"'") in _RUNS_NEXT:
        words.pop(0)
    if not words:
        return None
    head, rest = _word(words[0]), [_word(w) for w in words[1:]]
    if head in TOOL_COMMANDS:
        return head
    if head == "git":
        sub = [w for w in rest if w in NET_GIT]
        return "git " + sub[0] if sub else None
    if head in NPM_HEADS:
        sub = [w for w in rest if w in NET_NPM]
        return head + " " + sub[0] if sub else None
    if head in PIP_HEADS or ("-m" in rest and rest[rest.index("-m") + 1:rest.index("-m") + 2] == ["pip"]):
        sub = [w for w in rest if w in NET_PIP]
        return "pip " + sub[0] if sub else None
    for i, w in enumerate(words[1:], 1):
        if str(w).strip("\"'") in _RUNS_NEXT and i + 1 < len(words):
            nxt = str(words[i + 1])
            if any(ch.isspace() for ch in nxt.strip("\"'")):
                found = tools_in_text(nxt.strip("\"'"))
                return found[0][0] if found else None
            return tool_in(words[i + 1:])
    return None


# The separators between commands: pipes, `&&`, `||`, `;`, newlines, subshells, backticks, a brace group's `{`
# and `}` when they stand as words (not curl's `%{http_code}` or a `${var}`), and AppleScript's `do script`,
# which runs a shell line.
_SEGMENTS = re.compile(r"\|\||&&|\$\(|[;|\n()`]|(?<![^\s;&|(])\{(?=\s)|(?<![^\s;])\}(?![^\s);|&])|\bdo script\b")
_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_WRAPPERS = ("exec", "nohup", "time", "sudo", "env", "then", "else", "do", "if", "elif", "while", "until", "!")
_LOOKUPS = ("command", "which", "type", "hash")


def shell_commands(text):
    """The commands a shell text runs, each as its words with the command first: the text split at pipes, `&&`,
    `||`, `;`, newlines, subshells and braces, leading variable assignments and wrappers (exec, nohup, then,
    do ...) dropped, and `command -v x`, `which x`, `type x` dropped whole, since they look a tool up and run
    nothing."""
    out = []
    for seg in _SEGMENTS.split(text):
        words = seg.split()
        while words and (_ASSIGNMENT.match(words[0]) or words[0] in _WRAPPERS):
            words.pop(0)
        if not words or words[0] in _LOOKUPS:
            continue
        out.append(words)
    return out


def tools_in_text(text):
    """Every (tool, words) a shell text runs, in order."""
    found = []
    for words in shell_commands(text):
        tool = tool_in(words)
        if tool:
            found.append((tool, words))
    return found


# ---------------------------------------------------------------------------------------------------
# The Python scanner.
# ---------------------------------------------------------------------------------------------------

class _Module:
    """One parsed file: its import aliases, a parent map, and the assignment tables the renderer reads."""

    def __init__(self, rel, src):
        self.rel, self.src = rel, src
        self.tree = ast.parse(src, filename=rel)
        self.lines = src.splitlines()
        self.parent = {}
        for node in ast.walk(self.tree):
            for child in ast.iter_child_nodes(node):
                self.parent[child] = node
        self.aliases = {}
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    self.aliases[a.asname or a.name.split(".")[0]] = a.name if a.asname else a.name.split(".")[0]
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                for a in node.names:
                    self.aliases[a.asname or a.name] = node.module + "." + a.name
        self.functions = {}
        for node in self.tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.functions.setdefault(node.name, []).append(node)
        self._assigns = {}

    # -- names -------------------------------------------------------------------------------------

    def dotted(self, node):
        parts = []
        while isinstance(node, ast.Attribute):
            parts.append(node.attr)
            node = node.value
        if isinstance(node, ast.Name):
            parts.append(node.id)
        else:
            return None
        parts.reverse()
        return ".".join(parts)

    def canonical(self, node):
        """The dotted name a callee spells, with its module alias resolved: `from urllib import request as r`
        makes `r.urlopen` spell urllib.request.urlopen."""
        d = self.dotted(node)
        if d is None:
            return None
        root, _, tail = d.partition(".")
        base = self.aliases.get(root, root)
        return base + ("." + tail if tail else "")

    def enclosing_defs(self, node):
        out = []
        while node in self.parent:
            node = self.parent[node]
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                out.append(node)
        return out

    def function_name(self, node):
        defs = self.enclosing_defs(node)
        if not defs:
            return "(module)"
        outer = defs[-1]
        holder = self.parent.get(outer)
        return (holder.name + "." if isinstance(holder, ast.ClassDef) else "") + outer.name

    def scopes(self, node):
        return self.enclosing_defs(node) + [self.tree]

    # -- assignments -------------------------------------------------------------------------------

    def assignments(self, scope):
        """name -> [("value", expr) | ("iter", expr) | ("unknown", None)] for one scope, nested defs excluded."""
        if scope in self._assigns:
            return self._assigns[scope]
        table = {}

        def add(name, kind, expr):
            table.setdefault(name, []).append((kind, expr))

        def targets(t, kind, expr):
            if isinstance(t, ast.Name):
                add(t.id, kind, expr)
            elif isinstance(t, (ast.Tuple, ast.List)):
                for e in t.elts:
                    targets(e, "unknown", None)
            elif isinstance(t, ast.Starred):
                targets(t.value, "unknown", None)

        def walk(node):
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                    continue
                if isinstance(child, ast.Assign):
                    for t in child.targets:
                        targets(t, "value", child.value)
                elif isinstance(child, ast.AnnAssign) and child.value is not None:
                    targets(child.target, "value", child.value)
                elif isinstance(child, ast.AugAssign):
                    targets(child.target, "value", child.value)
                elif isinstance(child, ast.NamedExpr):
                    targets(child.target, "value", child.value)
                elif isinstance(child, (ast.For, ast.AsyncFor)):
                    targets(child.target, "iter", child.iter)
                elif isinstance(child, (ast.With, ast.AsyncWith)):
                    for item in child.items:
                        if item.optional_vars is not None:
                            targets(item.optional_vars, "unknown", None)
                walk(child)

        walk(scope)
        self._assigns[scope] = table
        return table

    def lookup(self, name, scopes):
        """The bindings of `name` in the innermost scope that binds it, else None."""
        for scope in scopes:
            table = self.assignments(scope)
            if name in table:
                return table[name]
        return None

    def parameter_of(self, name, scopes):
        for scope in scopes:
            if isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = scope.args
                names = [a.arg for a in args.posonlyargs + args.args + args.kwonlyargs]
                if args.vararg:
                    names.append(args.vararg.arg)
                if args.kwarg:
                    names.append(args.kwarg.arg)
                if name in names:
                    return scope, names.index(name) if name in [a.arg for a in args.posonlyargs + args.args] else None
        return None

    def calls_of(self, fn):
        """Every call in the module that names the function `fn` (by bare name or as a method attribute), from
        one index built on first use."""
        if not hasattr(self, "_calls"):
            self._calls = {}
            for node in ast.walk(self.tree):
                if isinstance(node, ast.Call):
                    f = node.func
                    key = f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else None
                    if key is not None:
                        self._calls.setdefault(key, []).append(node)
        return self._calls.get(fn.name, [])

    # -- rendering ---------------------------------------------------------------------------------

    def render(self, expr, scopes, hops=MAX_HOPS, seen=None):
        """The strings `expr` can spell, from its constants: a set, UNKNOWN standing for any part no constant
        reaches. Names, parameters and calls of module functions are followed `hops` deep."""
        seen = seen if seen is not None else set()
        if expr is None:
            return {UNKNOWN}
        if isinstance(expr, ast.Constant):
            if expr.value is None:
                return set()               # a None is never dialled: `return None` beside `return url` adds nothing
            return {expr.value} if isinstance(expr.value, str) else {UNKNOWN}
        if isinstance(expr, ast.JoinedStr):
            parts = []
            for v in expr.values:
                if isinstance(v, ast.Constant):
                    parts.append({str(v.value)})
                elif isinstance(v, ast.FormattedValue):
                    parts.append(self.render(v.value, scopes, hops, seen))
                else:
                    parts.append({UNKNOWN})
            return _product(parts)
        if isinstance(expr, ast.BinOp):
            if isinstance(expr.op, ast.Add):
                return _product([self.render(expr.left, scopes, hops, seen), self.render(expr.right, scopes, hops, seen)])
            if isinstance(expr.op, ast.Mod):
                operands = expr.right.elts if isinstance(expr.right, ast.Tuple) else [expr.right]
                fills = [self.render(o, scopes, hops, seen) for o in operands]
                out = set()
                for s in self.render(expr.left, scopes, hops, seen):
                    pieces = _PERCENT.split(s)
                    specs = _PERCENT.findall(s)
                    parts = [{pieces[0]}]
                    for i, spec in enumerate(specs):
                        parts.append({"%"} if spec == "%%" else (fills[i] if i < len(fills) else {UNKNOWN}))
                        parts.append({pieces[i + 1]})
                    out |= _product(parts)
                return out
            return {UNKNOWN}
        if isinstance(expr, ast.BoolOp):
            out = set()
            for v in expr.values:
                out |= self.render(v, scopes, hops, seen)
            return out
        if isinstance(expr, ast.IfExp):
            return self.render(expr.body, scopes, hops, seen) | self.render(expr.orelse, scopes, hops, seen)
        if isinstance(expr, (ast.Tuple, ast.List, ast.Set)):
            out = set()
            for e in expr.elts:
                out |= self.render(e, scopes, hops, seen)
            return out or {UNKNOWN}
        if isinstance(expr, ast.Starred):
            return self.render(expr.value, scopes, hops, seen)
        if isinstance(expr, (ast.ListComp, ast.GeneratorExp, ast.SetComp)):
            out = self.render(expr.elt, scopes, hops, seen)
            for g in expr.generators:
                out |= self.render(g.iter, scopes, hops, seen)
            return out
        if isinstance(expr, ast.Call):
            return self._render_call(expr, scopes, hops, seen)
        if isinstance(expr, ast.Name):
            if hops <= 0 or (expr.id, id(scopes[0])) in seen:
                return {UNKNOWN}
            seen = seen | {(expr.id, id(scopes[0]))}
            bindings = self.lookup(expr.id, scopes)
            if bindings is not None:
                out = set()
                for kind, value in bindings:
                    if kind == "unknown":
                        out.add(UNKNOWN)
                    else:
                        out |= self.render(value, scopes, hops - 1, seen)
                return out
            param = self.parameter_of(expr.id, scopes)
            if param is not None:
                fn, index = param
                out = set()
                for call in self.calls_of(fn):
                    arg = None
                    if index is not None and index < len(call.args):
                        arg = call.args[index]
                    for kw in call.keywords:
                        if kw.arg == expr.id:
                            arg = kw.value
                    if arg is None:
                        out.add(UNKNOWN)
                    else:
                        out |= self.render(arg, self.scopes(call), hops - 1, seen)
                return out or {UNKNOWN}
            return {UNKNOWN}
        return {UNKNOWN}

    def _render_call(self, call, scopes, hops, seen):
        name = self.canonical(call.func)
        if name == "urllib.request.Request":
            return self.render(_arg(call, 0, "url"), scopes, hops, seen)
        if name in ("os.environ.get", "os.getenv"):
            return {UNKNOWN} | (self.render(call.args[1], scopes, hops, seen) if len(call.args) > 1 else set())
        if name in ("str", "shlex.split", "shlex.quote", "json.dumps", "os.path.expanduser", "os.fsdecode") and call.args:
            return self.render(call.args[0], scopes, hops, seen)
        if isinstance(call.func, ast.Attribute):
            if call.func.attr in STR_METHODS:
                return self.render(call.func.value, scopes, hops, seen)
            if call.func.attr == "join" and call.args:
                return self.render(call.args[0], scopes, hops, seen)
        if isinstance(call.func, ast.Name) and call.func.id in self.functions and hops > 0:
            out = set()
            for fn in self.functions[call.func.id]:
                for node in ast.walk(fn):
                    if isinstance(node, ast.Return) and node.value is not None:
                        out |= self.render(node.value, [fn, self.tree], hops - 1, seen)
            return out or {UNKNOWN}
        return {UNKNOWN}

    def argv_alternatives(self, expr, scopes, hops=MAX_HOPS, seen=None):
        """The command lines `expr` can be: a list of ("words", [set, ...]) for a list-shaped argv (each word the
        set of strings that position can spell) and ("text", set) for a string handed to a shell."""
        seen = seen if seen is not None else set()
        if expr is None:
            return []
        if isinstance(expr, (ast.List, ast.Tuple)):
            words = []
            for e in expr.elts:
                if isinstance(e, ast.Starred):
                    for alt in self.argv_alternatives(e.value, scopes, hops, seen)[:1]:
                        words.extend(alt[1] if alt[0] == "words" else [alt[1]])
                else:
                    words.append(self.render(e, scopes, hops, seen))
            return [("words", words)]
        if isinstance(expr, ast.BinOp) and isinstance(expr.op, ast.Add):
            left = self.argv_alternatives(expr.left, scopes, hops, seen)
            right = self.argv_alternatives(expr.right, scopes, hops, seen)
            if left and right and all(a[0] == "words" for a in left + right):
                return [("words", a[1] + b[1]) for a in left for b in right]
            return [("text", self.render(expr, scopes, hops, seen))]
        if isinstance(expr, (ast.Constant, ast.JoinedStr)) or (isinstance(expr, ast.BinOp) and isinstance(expr.op, ast.Mod)):
            return [("text", self.render(expr, scopes, hops, seen))]
        if isinstance(expr, (ast.ListComp, ast.GeneratorExp)):
            out = []
            for g in expr.generators:
                out += self.argv_alternatives(g.iter, scopes, hops, seen)
            return out or [("text", self.render(expr, scopes, hops, seen))]
        if isinstance(expr, ast.Name) and hops > 0 and (expr.id, id(scopes[0])) not in seen:
            seen = seen | {(expr.id, id(scopes[0]))}
            bindings = self.lookup(expr.id, scopes)
            out = []
            if bindings is not None:
                for kind, value in bindings:
                    if kind != "unknown":
                        out += self.argv_alternatives(value, scopes, hops - 1, seen)
                return out
            param = self.parameter_of(expr.id, scopes)
            if param is not None:
                fn, index = param
                for call in self.calls_of(fn):
                    arg = call.args[index] if index is not None and index < len(call.args) else None
                    for kw in call.keywords:
                        if kw.arg == expr.id:
                            arg = kw.value
                    out += self.argv_alternatives(arg, self.scopes(call), hops - 1, seen)
                return out
            return []
        if isinstance(expr, ast.Call):
            name = self.canonical(expr.func)
            if name == "shlex.split" and expr.args:
                return [("text", self.render(expr.args[0], scopes, hops, seen))]
            if isinstance(expr.func, ast.Name) and expr.func.id in self.functions and hops > 0:
                out = []
                for fn in self.functions[expr.func.id]:
                    for node in ast.walk(fn):
                        if isinstance(node, ast.Return) and node.value is not None:
                            out += self.argv_alternatives(node.value, [fn, self.tree], hops - 1, seen)
                return out
            return [("text", self.render(expr, scopes, hops, seen))]
        return [("text", self.render(expr, scopes, hops, seen))]


_PERCENT = re.compile(r"%(?:\([^)]*\))?[-#0 +]*\d*(?:\.\d+)?[sdifrxXou%]")
_URL_HOST = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://(?:[^/?#@]*@)?(\[[^\]]*\]|[^:/?#]*)")


def _product(parts):
    out = set()
    for combo in itertools.islice(itertools.product(*parts), 64):
        out.add("".join(combo))
    return out or {UNKNOWN}


def _arg(call, index, *keywords):
    for kw in call.keywords:
        if kw.arg in keywords:
            return kw.value
    if index < len(call.args):
        a = call.args[index]
        return None if isinstance(a, ast.Starred) else a
    return None


def _first_of_pair(expr):
    """The host of an (host, port) address: the tuple's first element, else the expression itself."""
    if isinstance(expr, (ast.Tuple, ast.List)) and expr.elts:
        return expr.elts[0]
    return expr


def is_loopback(candidates):
    """True only when every rendering names 127.0.0.1 as its host: a bare host (a port may follow) or a URL's.
    An empty set, a placeholder host, `localhost` and a lookalike (127.0.0.1.example) are all False."""
    if not candidates:
        return False
    for c in candidates:
        m = _URL_HOST.match(c)
        host = m.group(1) if m else c.split(":", 1)[0] if re.match(r"^\d+\.\d+\.\d+\.\d+(:|$)", c) else c
        if host != LOOPBACK_HOST:
            return False
    return True


def _words_tool(words):
    """tool_in over word-sets: the combinations of each word's renderings, the first 64."""
    if not words:
        return None
    for combo in itertools.islice(itertools.product(*[sorted(w) or [UNKNOWN] for w in words]), 64):
        tool = tool_in(list(combo))
        if tool:
            return tool
    return None


def _has_shell_head(words):
    return bool(words) and any(_word(h) in SHELLS for h in words[0])


def _shell_script_of(words):
    """For [sh, -c, SCRIPT, ...]: the script word's renderings, else None."""
    for i, w in enumerate(words[1:], 1):
        if w == {"-c"} or w == {"-lc"}:
            return words[i + 1] if i + 1 < len(words) else None
    return None


def _env_spells_git_ssh(module, expr, scopes, hops=3):
    """Does an env= expression spell GIT_SSH_COMMAND: as a dict(...) keyword, a constant key, or through the
    bindings of a name (`env = dict(os.environ, GIT_SSH_COMMAND=...)` then `env=env`)."""
    for node in ast.walk(expr):
        if isinstance(node, ast.keyword) and node.arg == "GIT_SSH_COMMAND":
            return True
        if isinstance(node, ast.Constant) and node.value == "GIT_SSH_COMMAND":
            return True
        if isinstance(node, ast.Name) and hops > 0:
            for kind, value in (module.lookup(node.id, scopes) or []):
                if kind != "unknown" and value is not expr and _env_spells_git_ssh(module, value, scopes, hops - 1):
                    return True
    return False


def scan_module(rel, src):
    """Every site in one Python source, as Site rows in source order."""
    m = _Module(rel, src)
    rows = {}

    def add(node, kind, klass, tool=None):
        key = (node.lineno, kind, tool)
        if key not in rows:
            text = m.lines[node.lineno - 1].strip() if node.lineno - 1 < len(m.lines) else ""
            rows[key] = Site(rel, node.lineno, m.function_name(node), kind, klass, tool, text[:160])

    def dial(node, kind, host_expr):
        add(node, kind, "loopback" if is_loopback(m.render(host_expr, m.scopes(node))) else "outbound")

    def socket_ctor(recv, scopes, hops=3):
        """The socket.socket(...) call a receiver name is bound from, else None."""
        if isinstance(recv, ast.Call):
            return recv if m.canonical(recv.func) in ("socket.socket", "socket.create_connection") else None
        if isinstance(recv, ast.Name) and hops > 0:
            for kind, value in (m.lookup(recv.id, scopes) or []):
                if kind == "value":
                    c = socket_ctor(value, scopes, hops - 1)
                    if c is not None:
                        return c
        return None

    def bound_from(recv, scopes, names, hops=3):
        if isinstance(recv, ast.Call):
            return m.canonical(recv.func) in names
        if isinstance(recv, ast.Name) and hops > 0:
            return any(kind == "value" and bound_from(value, scopes, names, hops - 1)
                       for kind, value in (m.lookup(recv.id, scopes) or []))
        return False

    def tool_site(node, alternatives, scopes, klass_hint=None):
        for shape, payload in alternatives:
            if shape == "words":
                if _has_shell_head(payload):
                    script = _shell_script_of(payload)
                    if script is not None:
                        for text in script:
                            for tool, _ in tools_in_text(text):
                                add(node, "shell-string", _tool_klass(tool, {text}), tool)
                    continue
                tool = _words_tool(payload)
                if tool:
                    flat = set()
                    for w in payload:
                        flat |= w
                    add(node, "tool", _tool_klass(tool, flat), tool)
            else:
                for text in payload:
                    for tool, _ in tools_in_text(text):
                        add(node, "shell-string", _tool_klass(tool, {text}), tool)

    for node in ast.walk(m.tree):
        if isinstance(node, ast.Call):
            name = m.canonical(node.func)
            scopes = m.scopes(node)
            if name == "urllib.request.urlopen":
                dial(node, "urlopen", _arg(node, 0, "url"))
            elif name == "urllib.request.Request":
                dial(node, "Request", _arg(node, 0, "url"))
            elif name in ("http.client.HTTPConnection", "http.client.HTTPSConnection"):
                dial(node, name.rsplit(".", 1)[1], _arg(node, 0, "host"))
            elif name == "socket.create_connection":
                dial(node, "create_connection", _first_of_pair(_arg(node, 0, "address")))
            elif name == "asyncio.open_connection":
                dial(node, "open_connection", _arg(node, 0, "host"))
            elif name == "ssl.wrap_socket":
                add(node, "wrap_socket", "outbound")
            elif name and name.split(".")[0] in HTTP_LIBRARIES:
                dial(node, "http-library", _arg(node, 0, "url"))
            elif name in WEBSOCKET_DIALS:
                dial(node, "websocket", _arg(node, 0, "uri", "url"))
            elif isinstance(node.func, ast.Attribute) and node.func.attr == "wrap_socket" and bound_from(
                    node.func.value, scopes, ("ssl.create_default_context", "ssl.SSLContext")):
                add(node, "wrap_socket", "outbound")
            elif isinstance(node.func, ast.Attribute) and node.func.attr == "open" and bound_from(
                    node.func.value, scopes, ("urllib.request.build_opener",)):
                dial(node, "opener.open", _arg(node, 0, "fullurl", "url"))
            elif isinstance(node.func, ast.Attribute) and node.func.attr in ("connect", "connect_ex"):
                ctor = socket_ctor(node.func.value, scopes)
                if ctor is not None:
                    dgram = any(isinstance(a, ast.Attribute) and a.attr == "SOCK_DGRAM" or
                                isinstance(a, ast.Name) and a.id == "SOCK_DGRAM" for a in ast.walk(ctor))
                    host = _first_of_pair(_arg(node, 0, "address"))
                    if dgram:
                        add(node, "socket.connect", "route-probe")
                    else:
                        dial(node, "socket.connect", host)
            elif name in SUBPROCESS_CALLS:
                if name in SHELL_TEXT_CALLS or any(kw.arg == "shell" and isinstance(kw.value, ast.Constant)
                                                    and kw.value.value is True for kw in node.keywords):
                    for text in m.render(_arg(node, 0, "args", "cmd"), scopes):
                        for tool, _ in tools_in_text(text):
                            add(node, "shell-string", _tool_klass(tool, {text}), tool)
                elif name == "asyncio.create_subprocess_exec":
                    words = [m.render(a.value if isinstance(a, ast.Starred) else a, scopes) for a in node.args]
                    if node.args and isinstance(node.args[0], ast.Starred):
                        tool_site(node, m.argv_alternatives(node.args[0].value, scopes), scopes)
                    else:
                        tool_site(node, [("words", words)], scopes)
                else:
                    tool_site(node, m.argv_alternatives(_arg(node, 0, "args"), scopes), scopes)
                env = _arg(node, 99, "env")
                if env is not None and _env_spells_git_ssh(m, env, scopes):
                    add(node, "GIT_SSH_COMMAND", "outbound", "git over ssh")
            elif isinstance(node.func, ast.Name) and node.func.id in GIT_WRAPPERS and node.args:
                for shape, payload in m.argv_alternatives(node.args[0], scopes):
                    if shape == "words":
                        tool = _words_tool([{"git"}] + payload)
                        if tool:
                            add(node, "tool", "outbound", tool)
        elif isinstance(node, (ast.List, ast.BinOp)):
            # a command line built as a literal anywhere (an assignment, a return): the argv the tunnel
            # supervisor spawns is built by _tunnel_argv and spawned elsewhere
            parent = m.parent.get(node)
            if isinstance(parent, ast.BinOp) and isinstance(parent.op, ast.Add):
                continue                                   # part of a chain read at its top
            if isinstance(node, ast.BinOp) and not isinstance(node.op, ast.Add):
                continue
            scopes = m.scopes(node)
            if not _could_be_a_command(m, node, scopes):
                continue
            alts = m.argv_alternatives(node, scopes, hops=2)
            for shape, payload in alts:
                if shape == "words" and not _has_shell_head(payload):
                    tool = _words_tool(payload)
                    if tool:
                        flat = set()
                        for w in payload:
                            flat |= w
                        add(node, "tool", _tool_klass(tool, flat), tool)
    return [rows[k] for k in sorted(rows)]


_COMMAND_HEADS = set(TOOL_COMMANDS) | {"git"} | set(NPM_HEADS) | set(PIP_HEADS)
_COMMAND_MARKS = set(_RUNS_NEXT) | {"-m"}


def _could_be_a_command(m, node, scopes):
    """A cheap gate before a list literal is rendered as a command line: its first word, rendered two hops, is a
    tool's name, or one of its constant words is a launcher's `-e`, an `--args`, a `--` or python's `-m`. Lists
    of numbers, of names alone or of unrelated words are skipped, which is what keeps the census fast on a
    file the size of the kernel."""
    first = node
    while isinstance(first, ast.BinOp):
        first = first.left
    if not isinstance(first, (ast.List, ast.Tuple)) or not first.elts:
        return False
    head = first.elts[0]
    if isinstance(head, ast.Constant):
        if isinstance(head.value, str) and _word(head.value) in _COMMAND_HEADS:
            return True
    elif isinstance(head, (ast.Name, ast.Attribute, ast.Starred)):
        if any(_word(s) in _COMMAND_HEADS for s in m.render(head, scopes, 2)):
            return True
    for sub in ast.walk(node):
        if isinstance(sub, ast.Constant) and isinstance(sub.value, str) and sub.value in _COMMAND_MARKS:
            return True
    return False


def _tool_klass(tool, texts):
    """curl or wget aimed at 127.0.0.1 alone is loopback; every other tool leaves the machine."""
    if tool in ("curl", "wget"):
        urls = set()
        for t in texts:
            urls |= set(re.findall(r"[A-Za-z][A-Za-z0-9+.-]*://[^\s\"']+", t))
        if urls and is_loopback(urls):
            return "loopback"
    return "outbound"


def scope_files(root):
    """The (relative path, absolute path) of every file the Python census reads."""
    out = []
    for d in SCOPE_DIRS:
        base = os.path.join(root, d)
        if not os.path.isdir(base):
            continue
        for name in sorted(os.listdir(base)):
            path = os.path.join(base, name)
            if os.path.islink(path) or not os.path.isfile(path):
                continue
            if name.endswith(".py"):
                out.append((d + "/" + name, path))
            elif d == "bin" and _shebang(path).find("python") >= 0:
                out.append((d + "/" + name, path))
    return out


def _shebang(path):
    with open(path, "rb") as fh:
        head = fh.readline()
    return head.decode("utf-8", "replace") if head.startswith(b"#!") else ""


def scan_tree(root):
    sites = []
    for rel, path in scope_files(root):
        with open(path, encoding="utf-8") as fh:
            sites.extend(scan_module(rel, fh.read()))
    return sites


# ---------------------------------------------------------------------------------------------------
# The shell and node layer: bin/'s scripts and the manager, read with the same command grammar.
# ---------------------------------------------------------------------------------------------------

_FN_DEF = re.compile(r"^(\s*)(?:function\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*\(\)\s*\{")
_VERB = re.compile(r'^if \[\[ "\$\{1:-\}" == "([a-z][a-z0-9-]*)" \]\]')
_HEREDOC = re.compile(r"<<-?\s*['\"]?([A-Za-z_][A-Za-z0-9_]*)['\"]?")
_POSITIONAL = re.compile(r'^\$(?:@|\*|[1-9])$')


def _strip_comment(line):
    """A bash line without its trailing comment: a # outside quotes and not part of a word (${x#...})."""
    q = None
    for i, ch in enumerate(line):
        if q:
            if ch == q:
                q = None
        elif ch in "\"'":
            q = ch
        elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
            return line[:i]
    return line


def shell_logical_lines(text):
    """(first line number, function or verb, joined command text) for every logical line of a bash script:
    comments and heredoc bodies dropped, backslash continuations joined, the scope tracked by a function's
    indentation to its closing brace and a top-level `if [[ "${1:-}" == "verb" ]]` block to its `fi`."""
    out = []
    stack = []            # (indent, name) of open functions
    verb = None
    heredoc = None
    buf, start = [], None
    for n, raw in enumerate(text.splitlines(), 1):
        if heredoc is not None:
            if raw.strip() == heredoc:
                heredoc = None
            continue
        line = _strip_comment(raw)
        if not line.strip():
            continue
        if buf:
            buf.append(line.rstrip("\\").strip())
        else:
            start = n
            buf = [line.rstrip("\\").rstrip()]
        if line.rstrip().endswith("\\"):
            continue
        joined = " ".join(buf)
        buf = []
        m = _HEREDOC.search(joined)
        if m:
            heredoc = m.group(1)
        d = _FN_DEF.match(joined)
        if d:
            scope = d.group(2)
            if not joined[d.end():].rstrip().endswith("}"):      # a one-line body closes on its own line
                stack.append((d.group(1), d.group(2)))
        else:
            scope = stack[-1][1] if stack else ("verb " + verb if verb else "top-level")
            v = _VERB.match(joined)
            if v and not stack:
                verb = v.group(1)
                scope = "verb " + verb
            elif joined == "fi" and not stack and verb:
                verb = None
            if stack and joined.rstrip() == stack[-1][0] + "}":
                stack.pop()
        out.append((start, scope, joined))
    return out


def scan_shell_text(rel, text):
    """Every tool call a bash script makes, as Site rows: the command grammar over each logical line, a curl or
    wget loopback when its line carries 127.0.0.1 or its URL is a positional the function's every caller fills
    with 127.0.0.1."""
    lines = shell_logical_lines(text)
    rows = []
    for start, scope, joined in lines:
        for tool, words in tools_in_text(joined):
            klass = "outbound"
            if tool in ("curl", "wget"):
                if "127.0.0.1" in joined:
                    klass = "loopback"
                elif (any(_POSITIONAL.match(w.strip("\"')")) for w in words) and scope != "top-level"
                      and not scope.startswith("verb ")):
                    callers = [j for _, _, j in lines if not _FN_DEF.match(j)
                               and any(ws and _word(ws[0]) == scope for ws in shell_commands(j))]
                    if callers and all("127.0.0.1" in j for j in callers):
                        klass = "loopback"
            rows.append(Site(rel, start, scope, "shell", klass, tool, joined[:160]))
    return rows


_NODE_CALL = re.compile(r"\b(https?\.(?:get|request)|fetch|net\.(?:connect|createConnection)|tls\.connect|new WebSocket)\s*\(")
_NODE_DECL = re.compile(r"^\s*(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=")
_NODE_LOOPBACK = re.compile(r"(://|host(?:name)?\s*:\s*['\"`]|=\s*['\"`])127\.0\.0\.1(?![\d.])")
_NODE_FIRST_ARG = re.compile(r"^\s*([A-Za-z_$][\w$]*)\s*[,)]")
_NODE_HOST_KEY = re.compile(r"\bhost(?:name)?\s*:\s*`?\$?\{?([A-Za-z_$][\w$]*)")
_NODE_TEMPLATE_HOST = re.compile(r"://\$\{([A-Za-z_$][\w$]*)\}")


def _NODE_HOST_REFS(text):
    refs = []
    m = _NODE_FIRST_ARG.match(text)
    if m:
        refs.append(m.group(1))
    refs += _NODE_HOST_KEY.findall(text)
    refs += _NODE_TEMPLATE_HOST.findall(text)
    return refs


def scan_node_text(rel, text):
    """Every http, fetch, net or websocket call the manager makes, loopback when its line spells 127.0.0.1 or an
    identifier on it is declared (const, let or var) on a line that does, two hops deep."""
    lines = text.splitlines()
    decls = {}
    for n, line in enumerate(lines, 1):
        d = _NODE_DECL.match(line)
        if d:
            decls.setdefault(d.group(1), []).append(line)

    def loopback(text, hops):
        """127.0.0.1 in a host position of the text itself (after `://`, as a `host:` value, or as a declaration's
        value), or every declaration of each host reference on it resolving so (all of them: a name declared in two
        functions must be loopback in both, the safe side). The host references are a bare first argument (the URL
        or the options object), a `host:` or `hostname:` value, and the `${name}` right after `://` in a template;
        the other identifiers on the line (a `path:` key, a callback's parameter) carry no host."""
        if _NODE_LOOPBACK.search(text):
            return True
        if hops == 0:
            return False
        refs = _NODE_HOST_REFS(text)
        return bool(refs) and all(ref in decls and all(loopback(dl, hops - 1) for dl in decls[ref]) for ref in refs)

    rows = []
    fn = "top-level"
    for n, line in enumerate(lines, 1):
        code = line.split("//", 1)[0]
        f = re.match(r"^\s*(?:async\s+)?function\s+([A-Za-z_$][\w$]*)"
                     r"|^\s*(?:const|let)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:\([^()]*\)|[A-Za-z_$][\w$]*)\s*=>", code)
        if f:
            fn = f.group(1) or f.group(2)
        m = _NODE_CALL.search(code)
        if m:
            # the call's arguments alone: the variable the line declares (`const req = http.get(...)`) is not a host
            rows.append(Site(rel, n, fn, "node", "loopback" if loopback(code[m.end():], 2) else "outbound", m.group(1),
                             code.strip()[:160]))
    return rows


def shell_files(root):
    """(relative path, absolute path, 'shell' | 'node') for bin/'s regular scripts."""
    out = []
    base = os.path.join(root, "bin")
    for name in sorted(os.listdir(base)):
        path = os.path.join(base, name)
        if os.path.islink(path) or not os.path.isfile(path):
            continue
        shebang = _shebang(path)
        if "node" in shebang:
            out.append(("bin/" + name, path, "node"))
        elif "bash" in shebang or shebang.rstrip().endswith("/sh") or " sh" in shebang:
            out.append(("bin/" + name, path, "shell"))
    return out


def scan_shell_tree(root):
    rows = []
    for rel, path, kind in shell_files(root):
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        rows.extend(scan_shell_text(rel, text) if kind == "shell" else scan_node_text(rel, text))
    return rows


# ---------------------------------------------------------------------------------------------------
# The allowlist: every outbound site, by file and function, with its purpose, its gate and the words
# the reference carries for it (the doc; entries sharing one mechanism share one doc).
# ---------------------------------------------------------------------------------------------------

Entry = namedtuple("Entry", "file function kinds what gate doc")

DOC_MODELS = ("the Anthropic Models API, for the model pickers' version list, with the credential Claude Code's "
              "`apiKeyHelper` yields, at boot and when a session reports a model id the list lacks, off under "
              "`ROMP_MODEL_CATALOG=off`")
DOC_PRICES = ("a public model-price table on GitHub, for the settings modal's token-cost chart, at most once per six "
              "hours when that chart is read, with no switch to turn it off")
DOC_PUSH = ("a web push notification to the push service of every device you subscribed from the notifications "
            "popover, for each bell and for the popover's test button, and none when no device is subscribed")
DOC_FAST = ("Anthropic's fast-mode availability endpoint with the session's API key, at every connect of a key-billed "
            "session and never a login session")
DOC_UPDATE = ("the release remote's tags and main by `git ls-remote`, for the update check and the drift watcher, off "
              "under `ROMP_UPDATE_CHECK=off` or the update mode `off`, and a `git fetch` of main when an update is taken")
DOC_ORIGIN = ("the checkout's origin by `git ls-remote`, for the file viewer's GitHub link, when a file inside a git "
              "checkout with an origin is opened")
DOC_GH = "a watched pull request by `gh pr view`, only for a PR you asked `romp watch-pr` to follow"
DOC_SSH = ("`ssh` to every machine you attached as a linked kernel, the tunnel the linked kernels ride, plus that "
           "machine's kernel start, restart, update and pull over it, off when you detach or forget the host")
DOC_NPM = ("`npm install` in the extension directory, to refresh the UI bundle's dependencies when the bundle is stale "
           "at boot and its build fails, one retry, with no switch to turn it off")
DOC_CODEX = ("the Codex runtime by `pip` from its pinned GitHub release URL, checked against a published digest, when "
             "you run `romp-codex-setup` and the runtime is missing")
# The upload is the subject of the section the list sits in, named by its head sentence, not an item.
DOC_UPLOAD = "Besides the upload, Romp makes these requests on its own"

ALLOWLIST = (
    Entry("kernel/kernel.py", "_fetch_models_api", ("urlopen", "Request"),
          "GET every page of the Models API (MODELS_API_URL: ROMP_MODELS_URL or api.anthropic.com/v1/models)",
          "_refresh_model_catalog at boot and when a session reports a model id the catalog lacks; skipped under "
          "ROMP_MODEL_CATALOG=off; no apiKeyHelper means no fetch and a stderr line", DOC_MODELS),
    Entry("kernel/kernel.py", "_refresh_remote_prices", ("urlopen",),
          "GET the litellm model-price JSON (PRICE_FEED_URL on raw.githubusercontent.com) for the token-cost chart",
          "_model_prices from the analytics route, only when the cache is older than PRICE_TTL (six hours), on a "
          "daemon thread; no switch turns it off, ~/.config/romp/model-prices.json overrides prices only", DOC_PRICES),
    Entry("kernel/kernel.py", "_push_post", ("Request", "urlopen"),
          "POST one encrypted web push notification to the device's push service endpoint",
          "a subscription in the state directory's push-subscriptions.json, created from the notifications popover; "
          "fired by _push_notify for bells and by _push_test for the popover's test button; a 404 or 410 prunes it",
          DOC_PUSH),
    Entry("kernel/sdk_backend.py", "_fetch_key_fast_org", ("Request", "urlopen"),
          "GET the fast-mode availability endpoint (FAST_ORG_PATH on ANTHROPIC_BASE_URL or api.anthropic.com) "
          "for the key's own account",
          "key_fast_org_env at every connect of a key-billed session, never a login session; a three second cap",
          DOC_FAST),
    Entry("cli/perf_upload.py", "post", ("Request", "opener.open"),
          "POST one public export to the configured receiver",
          "only when the user runs romp perf upload and confirms (or --yes); the receiver from --receiver, "
          "ROMP_PERF_RECEIVER or ~/.config/romp/perf-receiver, none shipping", DOC_UPLOAD),
    Entry("kernel/kernel.py", "_latest_release_tag", ("tool",),
          "git ls-remote --tags of the release remote, for the update check's newest-release notice",
          "_update_check: off under ROMP_UPDATE_CHECK=off or the update mode off; a release clone only", DOC_UPDATE),
    Entry("kernel/kernel.py", "_origin_main_sha", ("tool",),
          "git ls-remote of the release remote's main, for the drift watcher's verdict",
          "_main_drift_check: the same two switches plus a main-tracking checkout", DOC_UPDATE),
    Entry("kernel/kernel.py", "_run_main_update", ("tool",),
          "git fetch of main before the fast-forward, ahead of the manager's restart",
          "the drift watcher's pull in auto update mode, or the user's Update through the update route", DOC_UPDATE),
    Entry("kernel/kernel.py", "_run_update", ("shell-string",),
          "the release update's detached bash script: git fetch of the release tag, the fast-forward, install.sh and "
          "a curl to the manager on 127.0.0.1",
          "the update banner's Update, or the automatic update once per version in auto mode", DOC_UPDATE),
    Entry("kernel/kernel.py", "_origin_has_branch", ("tool",),
          "git ls-remote --heads of the checkout's origin through _git_net_out, for the file viewer's GitHub link",
          "opening a file inside a git checkout that has an origin; memoized per checkout and ref, every askpass "
          "road closed", DOC_ORIGIN),
    Entry("kernel/kernel.py", "_git_net_out", ("tool",),
          "the wrapper's own Popen of git -C cwd plus its caller's arguments, in its own session under a deadline; "
          "the ls-remote above is its one caller with a network subcommand",
          "called by _origin_has_branch alone", DOC_ORIGIN),
    Entry("kernel/kernel.py", "_pr_watch_read", ("tool",),
          "gh pr view of a watched pull request's state and checks",
          "_pr_watch_tick every PR_WATCH_EVERY seconds, only for PRs filed with romp watch-pr; the user's gh login",
          DOC_GH),
    Entry("kernel/kernel.py", "_host_reachable", ("tool",), "ssh host true, the reachability probe",
          "a host row in the state directory's remotes.json, attached through the tunnels UI", DOC_SSH),
    Entry("kernel/kernel.py", "_fetch_remote_token", ("tool",), "ssh host cat of the peer's serve token",
          "attaching a host", DOC_SSH),
    Entry("kernel/kernel.py", "_tunnel_argv", ("tool",), "the ssh -N -T port-forward argv the tunnel supervisor spawns",
          "a host row in remotes.json; SSH_BIN from ROMP_SSH_BIN, BatchMode, no prompts", DOC_SSH),
    Entry("kernel/kernel.py", "_spawn_tunnel", ("tool",), "the Popen of _tunnel_argv's command line",
          "the tunnel supervisor's dial for each attached host", DOC_SSH),
    Entry("kernel/kernel.py", "_remote_kernel_up", ("tool",), "ssh host, a /dev/tcp probe of the peer's kernel port",
          "the tunnel supervisor", DOC_SSH),
    Entry("kernel/kernel.py", "_start_remote_kernel", ("tool",), "ssh host, starting the peer's kernel",
          "the tunnel supervisor when the peer's kernel is down", DOC_SSH),
    Entry("kernel/kernel.py", "_discover_remote_clone", ("tool",), "ssh host, finding the peer's romp checkout",
          "tunnels.update and tunnels.pull", DOC_SSH),
    Entry("kernel/kernel.py", "_update_remote", ("tool", "GIT_SSH_COMMAND"),
          "git push --force of this checkout's head to the peer's clone over ssh, and the ssh apply that follows",
          "the user's tunnels.update, or auto-update-remotes.json enabled", DOC_SSH),
    Entry("kernel/kernel.py", "_pull_remote", ("tool", "GIT_SSH_COMMAND"),
          "git fetch of the peer's clone HEAD over ssh, to fast-forward this checkout",
          "the user's tunnels.pull or the askpull prompt", DOC_SSH),
    Entry("kernel/kernel.py", "_restart_remote_kernel", ("tool",), "ssh host, restarting the peer's kernel",
          "tunnels.restart", DOC_SSH),
    Entry("kernel/kernel.py", "_open_folder_remote", ("tool", "shell-string"),
          "a terminal on this machine running ssh -t host into a remote session's folder (xterm, Terminal.app "
          "through osascript, or the configured terminal)",
          "the folder icon of a remote session, the openFolder message with a host prefix", DOC_SSH),
    Entry("kernel/kernel.py", "_ensure_bundles", ("tool",),
          "npm install in vscode-extension, then one retry of the esbuild bundle build",
          "at boot, when node_modules exists, the bundle is stale and the build failed; no switch turns it off",
          DOC_NPM),
    Entry("kernel/codex_runtime.py", "install_runtime", ("tool",),
          "pip install of the pinned Codex CLI wheel from its GitHub release URL, hash-checked, into the state "
          "directory",
          "bin/romp-codex-setup runs this module as a script; the kernel only reads the installed runtime",
          DOC_CODEX),
)

# The shell layer's entries, by file and function (or verb block): bin/'s installers and the watch-pr verb.
DOC_GETPIP = "download of `get-pip.py` in `bin/romp-sdk-setup` (off under `ROMP_NO_GET_PIP=1`)"
DOC_SDK_PIP = ("`pip` in `bin/romp-sdk-setup`, which installs pip's own upgrade, the pinned Claude Agent SDK and "
               "`cryptography` from PyPI")
DOC_CODEX_PIP = ("`pip` in `bin/romp-codex-setup`, which installs the pinned Codex SDK from PyPI and then runs the "
                 "Codex runtime installer")
DOC_GH_REPO = ("`gh repo view` when you run `romp watch-pr` without naming a repository, to learn which one the "
               "directory belongs to")

SHELL_ALLOWLIST = (
    Entry("bin/romp-sdk-setup", "fetch", ("curl", "wget"),
          "the get-pip.py download with whichever fetcher the box has (GET_PIP_URL)",
          "make_venv when python has no ensurepip; ROMP_GET_PIP_URL overrides, ROMP_NO_GET_PIP=1 opts out", DOC_GETPIP),
    Entry("bin/romp-sdk-setup", "top-level", ("pip install",),
          "pip install of pip's upgrade, claude-agent-sdk at its pin, and cryptography, into the SDK venv",
          "the installer, run once by the user", DOC_SDK_PIP),
    Entry("bin/romp-codex-setup", "top-level", ("pip install",),
          "pip install of the pinned openai-codex package into the Codex venv",
          "the installer, run once by the user; the runtime wheel follows through kernel/codex_runtime.py",
          DOC_CODEX_PIP),
    Entry("bin/romp", "verb watch-pr", ("gh",),
          "gh repo view to resolve the repository when --repo is not given",
          "romp watch-pr, run by the user", DOC_GH_REPO),
)

# The one connect that sends nothing, pinned in both directions like the allowlist.
ROUTE_PROBES = (
    ("kernel/kernel.py", "_primary_addr",
     "a UDP connect to 192.0.2.1 (TEST-NET-1, never routed) that sends no datagram: the kernel's way to learn the "
     "local address the routing table picks, the event the tunnels key on"),
)


def _unmatched(sites, entries, klass="outbound"):
    """(sites no entry names, entries no site matches) for one census against one allowlist."""
    by_key = {}
    for e in entries:
        by_key.setdefault((e.file, e.function), []).append(e)
    orphans, hit = [], set()
    for s in sites:
        if s.klass != klass:
            continue
        matches = [e for e in by_key.get((s.file, s.function), []) if s.kind in e.kinds or s.tool in e.kinds]
        if matches:
            hit.update(id(e) for e in matches)
        else:
            orphans.append("%s:%d in %s: %s %s: %s" % (s.file, s.line, s.function, s.kind, s.tool or "", s.text))
    unused = ["%s %s (%s)" % (e.file, e.function, ", ".join(e.kinds)) for e in entries if id(e) not in hit]
    return orphans, unused


class Census(unittest.TestCase):
    """The tree's sites against the allowlist, in both directions, and the derived counts."""

    @classmethod
    def setUpClass(cls):
        cls.sites = scan_tree(ROOT)
        cls.shell = scan_shell_tree(ROOT)

    def test_every_outbound_python_site_is_named_and_every_entry_names_a_site(self):
        orphans, unused = _unmatched(self.sites, ALLOWLIST)
        self.assertFalse(orphans, "request sites the allowlist does not name (add an Entry with the purpose, the gate "
                                  "and the reference's words, and the item to docs/reference.md):\n" + "\n".join(orphans))
        self.assertFalse(unused, "allowlist entries with no site (the code moved or the request is gone; drop the "
                                 "entry and the reference's item):\n" + "\n".join(unused))

    def test_every_outbound_site_carries_a_kind_its_entry_names(self):
        # the kinds pin the mechanism: an ssh spawned from a function the list knows for a git fetch is a new road
        wrong = []
        for s in self.sites:
            if s.klass != "outbound":
                continue
            entries = [e for e in ALLOWLIST if (e.file, e.function) == (s.file, s.function)]
            if entries and not any(s.kind in e.kinds or s.tool in e.kinds for e in entries):
                wrong.append("%s:%d %s is %s (%s); the entry names %s" % (s.file, s.line, s.function, s.kind, s.tool,
                                                                          sorted({k for e in entries for k in e.kinds})))
        self.assertFalse(wrong, "\n".join(wrong))

    def test_the_shell_and_node_layer_is_named_in_both_directions(self):
        orphans, unused = _unmatched(self.shell, SHELL_ALLOWLIST)
        self.assertFalse(orphans, "tool calls in bin/ the shell allowlist does not name:\n" + "\n".join(orphans))
        self.assertFalse(unused, "shell allowlist entries with no call:\n" + "\n".join(unused))

    def test_the_route_probe_is_the_one_connect_that_sends_nothing(self):
        probes = sorted({(s.file, s.function) for s in self.sites if s.klass == "route-probe"})
        self.assertEqual(probes, sorted({(f, fn) for f, fn, _ in ROUTE_PROBES}),
                         "the SOCK_DGRAM connects in the tree and ROUTE_PROBES differ")
        self.assertTrue(all(reason for _, _, reason in ROUTE_PROBES))

    def test_the_counts_are_derived_and_nothing_is_empty(self):
        # derived expectations fail on empty: a scanner that finds nothing is broken, not a clean tree
        outbound = [s for s in self.sites if s.klass == "outbound"]
        loopback = [s for s in self.sites if s.klass == "loopback"]
        self.assertGreater(len(outbound), 0)
        self.assertGreater(len(loopback), 0)
        self.assertGreater(len([s for s in self.shell if s.klass == "loopback"]), 0, "bin/romp's curls to the kernel")
        self.assertGreater(len([s for s in self.shell if s.klass == "outbound"]), 0)
        for kind in ("urlopen", "Request", "HTTPConnection", "create_connection", "socket.connect", "tool",
                     "shell-string", "GIT_SSH_COMMAND", "opener.open"):
            self.assertTrue(any(s.kind == kind for s in self.sites), "no site of kind %s in the tree" % kind)
        files = {rel for rel, _ in scope_files(ROOT)}
        self.assertTrue({"kernel/kernel.py", "kernel/sdk_backend.py", "cli/perf_upload.py", "postal/postal_service.py",
                         "bin/romp-session-host"} <= files, sorted(files))

    def test_every_bin_symlink_resolves_into_a_scanned_file(self):
        scanned = {os.path.realpath(p) for _, p in scope_files(ROOT)}
        base = os.path.join(ROOT, "bin")
        links = [n for n in sorted(os.listdir(base)) if os.path.islink(os.path.join(base, n))]
        self.assertTrue(links, "bin/ carries symlinks into kernel/, cli/ and postal/")
        stray = [n for n in links if os.path.realpath(os.path.join(base, n)) not in scanned]
        self.assertFalse(stray, "bin/ symlinks whose target the census does not read: %s" % stray)

    def test_the_reviewers_three_sites_and_the_upload_are_found_where_the_code_has_them(self):
        # the three requests the guide's sentence omitted (the finding this census answers), by function
        found = {(s.file, s.function) for s in self.sites if s.klass == "outbound"}
        for key in (("kernel/kernel.py", "_refresh_remote_prices"), ("kernel/kernel.py", "_fetch_models_api"),
                    ("kernel/kernel.py", "_push_post"), ("cli/perf_upload.py", "post"),
                    ("kernel/sdk_backend.py", "_fetch_key_fast_org")):
            self.assertIn(key, found)
        # and the judge makes no request of its own: its model calls run the claude binary
        self.assertFalse([s for s in self.sites if s.file == "kernel/judge.py" and s.klass == "outbound"])


# ---------------------------------------------------------------------------------------------------
# The form space, planted: one instance of every form, its loopback twin, and the shapes that are not forms.
# ---------------------------------------------------------------------------------------------------

PLANTED = '''\
import asyncio
import os
import shlex
import socket
import ssl
import subprocess
import sys
import urllib.request
from urllib import request as ur
import http.client
import requests
import websockets
import websocket

SSH_BIN = os.environ.get("ROMP_SSH_BIN", "ssh")
_SSH_OPTS = ["-o", "BatchMode=yes"]
KPORTS = ["http://127.0.0.1:29855", "http://127.0.0.1:7878"]
HOST = "127.0.0.1"
BASE = f"http://{HOST}:{os.environ.get('PORT', '1')}"
FEED = "https://example.invalid/prices.json"


def f_urlopen():
    return urllib.request.urlopen("https://example.invalid/x")                # L1 urlopen outbound

def f_request():
    return ur.Request("https://example.invalid/y", method="POST")              # L2 Request outbound

def f_opener():
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    return opener.open(ur.Request("https://example.invalid/z"))               # L3 opener.open outbound

def f_http():
    return http.client.HTTPConnection("example.invalid", 80)                    # L4 HTTPConnection outbound

def f_https():
    return http.client.HTTPSConnection(host="example.invalid")                  # L5 HTTPSConnection outbound

def f_create():
    return socket.create_connection(("example.invalid", 443))                   # L6 create_connection outbound

def f_connect():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(("example.invalid", 443))                                         # L7 socket.connect outbound

def f_wrap():
    ctx = ssl.create_default_context()
    return ctx.wrap_socket(socket.socket(), server_hostname="example.invalid")  # L8 wrap_socket outbound

async def f_open():
    return await asyncio.open_connection("example.invalid", 443)                # L9 open_connection outbound

def f_lib():
    return requests.get("https://example.invalid/api")                          # L10 http-library outbound

def f_ws():
    return websockets.connect("wss://example.invalid/ws")                       # L11 websocket outbound

def f_curl():
    subprocess.run(["curl", "-fsSL", "https://example.invalid/get-pip.py"])     # L12 tool curl outbound

def f_wget():
    subprocess.check_output(["/usr/bin/wget", "-qO-", "https://example.invalid/a"])   # L13 tool wget outbound

def f_git():
    subprocess.run(["git", "-C", "/x", "fetch", "origin", "main"], timeout=5)   # L14 tool git fetch

def f_gh():
    subprocess.run(["gh", "pr", "view", "1"])                                   # L15 tool gh

def f_ssh():
    subprocess.run([SSH_BIN] + _SSH_OPTS + ["--", "host", "true"])              # L16 tool ssh

def f_npm():
    subprocess.run(["npm", "install", "--no-audit"], check=True)                # L17 tool npm install

def f_pip():
    subprocess.run([sys.executable, "-m", "pip", "install", "x"], check=True)   # L18 tool pip install

def f_shell():
    script = "cd /x && git fetch %s refs/tags/v1 && ./install.sh" % "origin"
    subprocess.Popen(["bash", "-c", script])                                    # L19 shell-string git fetch

def f_git_ssh():
    env = dict(os.environ, GIT_SSH_COMMAND="%s -o BatchMode=yes" % SSH_BIN)
    subprocess.run(["git", "status"], env=env)                                  # L20 GIT_SSH_COMMAND

def f_wrapper_ls_remote(top):
    return _git_net_out(["ls-remote", "--heads", "origin", "x"], top, timeout=3, env=None)   # L21 tool through the wrapper

def _git_net_out(args, cwd, timeout, env):
    return subprocess.Popen(["git", "-C", cwd] + args)

def f_argv_built_elsewhere():
    argv = _tunnel_argv()
    subprocess.Popen(argv)                                                      # L22 tool ssh through a call's return

def _tunnel_argv():
    return [SSH_BIN, "-N", "-T"] + _SSH_OPTS + ["--", "host"]                  # L23 tool ssh, a list literal in a return

def f_terminal():
    tmpl = "open -na Ghostty --args -e ssh -t {host} 'cd {dir}'"
    parts = shlex.split(tmpl)
    argv = [p.replace("{host}", "h") for p in parts]
    subprocess.Popen(argv)                                                      # L24 shell-string ssh through shlex.split

def f_system():
    os.system("rsync -a /x host:/y")                                            # L25 shell-string rsync

def f_star(*argv):
    return urllib.request.urlopen(*argv)                                        # L26 urlopen, an unknown shape: outbound


# ---- loopback twins -------------------------------------------------------------------------

def t_urlopen():
    return urllib.request.urlopen("http://127.0.0.1:1/x")                       # T1

def t_request():
    return ur.Request(BASE + "/y")                                              # T2 through an f-string and HOST

def t_opener():
    opener = urllib.request.build_opener()
    return opener.open("http://127.0.0.1:2/z")                                  # T3

def t_http():
    return http.client.HTTPConnection("127.0.0.1", 80)                          # T4

def t_https():
    return http.client.HTTPSConnection("127.0.0.1", 443)                        # T5

def t_create(port):
    return socket.create_connection(("127.0.0.1", int(port)), timeout=6)        # T6

def t_connect(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    return s.connect_ex(("127.0.0.1", int(port)))                              # T7

async def t_open():
    return await asyncio.open_connection("127.0.0.1", 1)                        # T9

def t_lib():
    return requests.get("http://127.0.0.1:1/api")                               # T10

def t_ws():
    return websocket.create_connection("ws://127.0.0.1:1/ws")                   # T11

def t_curl():
    subprocess.run(["curl", "-s", "http://127.0.0.1:1/healthz"])                # T12

def t_loop():
    for u in KPORTS:
        return urllib.request.urlopen(u + "/version", timeout=1)                # T13 through a for loop over a module list

def t_param(u):
    return urllib.request.urlopen(u + "/status")                                # T14 a parameter, every caller loopback

def t_caller():
    return t_param(_kernel())

def _kernel():
    for u in KPORTS:
        return u
    return None

def t_percent(port, route):
    req = ur.Request("http://127.0.0.1:%d%s" % (port, route))                   # T15 percent formatting
    return urllib.request.urlopen(req, timeout=3)                               # T16 a Request bound to a name


# ---- lookalikes, the route probe and the shapes that are not forms --------------------------------

def x_lookalike():
    return urllib.request.urlopen("http://127.0.0.1.example/")                  # X1 outbound: a lookalike host

def x_localhost():
    return http.client.HTTPConnection("localhost", 80)                          # X2 outbound: localhost is not 127.0.0.1

def x_placeholder(sub):
    return ur.Request(sub["endpoint"], method="POST")                           # X3 outbound: nothing resolves

def x_probe():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("192.0.2.1", 9))                                                 # X4 route-probe

def n_open():
    open("/x")
    import json
    json.loads("{}")
    subprocess.run(["ls", "-l"])
    subprocess.run(["git", "config", "--get-all", "remote.origin.fetch"])
    subprocess.run(["git", "-C", "/x", "rev-parse", "HEAD"])
    subprocess.run(["sh", "-c", "echo curl is not run here"])
    subprocess.run(["sh", "-c", "command -v curl >/dev/null"])
    print("ssh -t host")
    be = object()
    be.connect("sid")
'''


def _planted_line(marker):
    for n, line in enumerate(PLANTED.splitlines(), 1):
        if "# " + marker + " " in line or line.rstrip().endswith("# " + marker):
            return n
    raise AssertionError("no planted line carries the marker " + marker)


class FormSpace(unittest.TestCase):
    """Every form in FORMS planted once in a synthetic module and found; every dial form's loopback twin classed
    loopback; the lookalikes outbound; the shapes that are not forms not counted."""

    @classmethod
    def setUpClass(cls):
        cls.sites = scan_module("planted/probe.py", PLANTED)
        cls.by_line = {}
        for s in cls.sites:
            cls.by_line.setdefault(s.line, []).append(s)

    def _one(self, marker, kind, klass, tool=None):
        line = _planted_line(marker)
        rows = self.by_line.get(line, [])
        match = [s for s in rows if s.kind == kind and (tool is None or s.tool == tool)]
        self.assertTrue(match, "%s: no %s%s site at planted line %d; found %s" % (
            marker, kind, " " + tool if tool else "", line, [(s.kind, s.tool, s.klass) for s in rows]))
        self.assertEqual(match[0].klass, klass, "%s: classed %s, expected %s" % (marker, match[0].klass, klass))
        return match[0]

    def test_every_form_is_planted_and_found_outbound(self):
        expected = {
            "L1": ("urlopen", None), "L2": ("Request", None), "L3": ("opener.open", None),
            "L4": ("HTTPConnection", None), "L5": ("HTTPSConnection", None), "L6": ("create_connection", None),
            "L7": ("socket.connect", None), "L8": ("wrap_socket", None), "L9": ("open_connection", None),
            "L10": ("http-library", None), "L11": ("websocket", None), "L12": ("tool", "curl"),
            "L13": ("tool", "wget"), "L14": ("tool", "git fetch"), "L15": ("tool", "gh"), "L16": ("tool", "ssh"),
            "L17": ("tool", "npm install"), "L18": ("tool", "pip install"), "L19": ("shell-string", "git fetch"),
            "L20": ("GIT_SSH_COMMAND", "git over ssh"), "L21": ("tool", "git ls-remote"), "L22": ("tool", "ssh"),
            "L23": ("tool", "ssh"), "L24": ("shell-string", "ssh"), "L25": ("shell-string", "rsync"),
            "L26": ("urlopen", None),
        }
        for marker, (kind, tool) in expected.items():
            self._one(marker, kind, "outbound", tool)
        # the planted kinds are the form space, both ways: a matcher dropped from the scanner reds above by
        # marker, a FORMS row with no plant or a plant with no FORMS row reds here
        self.assertEqual(sorted({k for k, _ in expected.values()}), sorted(FORM_KINDS))
        self.assertEqual(len(FORM_KINDS), len(set(FORM_KINDS)))
        # the attribution: a nested list literal in a return is the enclosing def's; the module scope has none
        self.assertEqual(self._one("L23", "tool", "outbound", "ssh").function, "_tunnel_argv")
        self.assertEqual(self._one("L3", "opener.open", "outbound").function, "f_opener")

    def test_every_dial_forms_loopback_twin_is_classed_loopback(self):
        for marker, kind in (("T1", "urlopen"), ("T2", "Request"), ("T3", "opener.open"), ("T4", "HTTPConnection"),
                             ("T5", "HTTPSConnection"), ("T6", "create_connection"), ("T7", "socket.connect"),
                             ("T9", "open_connection"), ("T10", "http-library"), ("T11", "websocket"),
                             ("T13", "urlopen"), ("T14", "urlopen"), ("T15", "Request"), ("T16", "urlopen")):
            self._one(marker, kind, "loopback")
        self._one("T12", "tool", "loopback", "curl")

    def test_a_lookalike_a_localhost_and_an_unresolved_host_are_outbound_and_the_udp_connect_is_a_route_probe(self):
        self._one("X1", "urlopen", "outbound")
        self._one("X2", "HTTPConnection", "outbound")
        self._one("X3", "Request", "outbound")
        self._one("X4", "socket.connect", "route-probe")
        self.assertFalse(is_loopback(set()), "nothing resolved is not loopback")
        self.assertFalse(is_loopback({"http://127.0.0.1:1/a", "https://example.invalid/b"}), "every rendering must be")
        self.assertTrue(is_loopback({"127.0.0.1", "127.0.0.1:8080", "http://127.0.0.1:<?><?>/x"}))
        self.assertFalse(is_loopback({"127.0.0.10"}))

    def test_the_shapes_that_are_not_forms_are_not_counted(self):
        start = _planted_line("X4") + 1
        stray = [s for s in self.sites if s.line > start]
        self.assertEqual(stray, [], "sites counted inside n_open, which runs no request: %s" % stray)
        # the command grammar on its own: exact words, command position, lookups dropped
        self.assertIsNone(tool_in(["git", "config", "--get-all", "remote.origin.fetch"]))
        self.assertEqual(tool_in(["git", "-C", "/x", "ls-remote", "--tags", "origin"]), "git ls-remote")
        self.assertEqual(tool_in(['"$VENV/bin/pip"', "install", "-q", "x"]), "pip install")
        self.assertEqual(tool_in(["python3", "-m", "pip", "download", "x"]), "pip download")
        self.assertIsNone(tool_in(["python3", "-m", "venv", "install"]))
        self.assertEqual(tools_in_text('if command -v curl >/dev/null 2>&1; then curl -fsSL "$1" -o "$2"; fi'),
                         [("curl", ["curl", "-fsSL", '"$1"', "-o", '"$2"'])])
        self.assertEqual(tools_in_text('echo "  curl -fsSL https://example.invalid/x | bash"'), [])
        self.assertEqual(tools_in_text('_r="$(_cfg | curl -sf "http://127.0.0.1:$p/x")" || true'),
                         [("curl", ["curl", "-sf", '"http://127.0.0.1:$p/x"'])])
        # curl's own -w format and a ${var} keep their braces; a brace group's { and } split
        self.assertEqual(tools_in_text("""_o="$(_cfg | curl -s -w '\\n%{http_code}' "${u}" "$@")" || { echo no >&2; return 1; }"""),
                         [("curl", ["curl", "-s", "-w", "'\\n%{http_code}'", '"${u}"', '"$@"'])])
        self.assertEqual([t for t, _ in tools_in_text("A=1 exec ssh -N host; git status; nohup gh pr view 1")], ["ssh", "gh"])

    def test_the_shell_layer_reads_command_position_continuations_wrappers_heredocs_and_scopes(self):
        text = "\n".join([
            "#!/usr/bin/env bash",
            "# curl https://example.invalid/comment",
            "fetch() {   # $1 url",
            '  if command -v curl >/dev/null 2>&1; then curl -fsSL --max-time 60 "$1" -o "$2"',
            '  elif command -v wget >/dev/null 2>&1; then wget -qO "$2" "$1"',
            "  else return 1; fi",
            "}",
            "_kcurl() {",
            '    _out="$(_cfg | curl -s --config - "$@")" || return 1',
            "}",
            '_kcurl "http://127.0.0.1:$port/a"',
            '_kcurl "http://127.0.0.1:$port/b"',
            "_ocurl() {",
            '    curl -s "$1"',
            "}",
            '_ocurl "https://example.invalid/outside"',
            'echo "  curl -fsSL https://example.invalid/bootstrap.sh | bash"',
            '_resp="$(_cfg | curl -sf -m 10 --config - -X POST \\',
            '    "http://127.0.0.1:$_kport/fork" \\',
            "    -d '{}')\"",
            "python3 - <<'PY'",
            "print('pip install nothing here')",
            "PY",
            '"$VENV/bin/pip" install -q "claude-agent-sdk==1.0"',
            'if [[ "${1:-}" == "watch-pr" ]]; then',
            '    _repo="$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || true)"',
            "    git status",
            "fi",
            "git fetch origin main",
        ])
        rows = scan_shell_text("bin/probe", text)
        got = [(s.line, s.function, s.tool, s.klass) for s in rows]
        self.assertEqual(got, [
            (4, "fetch", "curl", "outbound"),
            (5, "fetch", "wget", "outbound"),
            (9, "_kcurl", "curl", "loopback"),          # "$@" filled with 127.0.0.1 by every caller
            (14, "_ocurl", "curl", "outbound"),         # "$1" filled from outside by its caller
            (18, "top-level", "curl", "loopback"),      # the URL on a continuation line
            (24, "top-level", "pip install", "outbound"),
            (26, "verb watch-pr", "gh", "outbound"),
            (29, "top-level", "git fetch", "outbound"),
        ])

    def test_the_node_layer_resolves_a_host_constant_and_a_url_variable_two_hops_deep(self):
        text = "\n".join([
            "const http = require('http');",
            "const HOST = '127.0.0.1';",
            "const CONTROL_PORT = 7432;",
            "// http.get('https://example.invalid/comment')",
            "function probe(port, cb) {",
            "  const req = http.get({ host: HOST, port, path: '/version', timeout: 5000 }, (res) => {});",
            "}",
            "function outside() {",
            "  const req = http.get('https://example.invalid/x', (res) => {});",
            "}",
            "function control(pathname) {",
            "  const u = new URL(`http://${HOST}:${CONTROL_PORT}${pathname}`);",
            "  const req = http.request(u, { method: 'GET' }, (res) => {});",
            "}",
            "const far = 'https://example.invalid/y';",
            "const later = () => {",
            "  fetch(far);",
            "};",
        ])
        rows = scan_node_text("bin/probe-manager", text)
        self.assertEqual([(s.line, s.function, s.tool, s.klass) for s in rows], [
            (6, "probe", "http.get", "loopback"),
            (9, "outside", "http.get", "outbound"),
            (13, "control", "http.request", "loopback"),
            (17, "later", "fetch", "outbound"),
        ])

    def test_the_allowlist_check_reports_both_directions_on_a_planted_census(self):
        sites = scan_module("planted/probe.py", PLANTED)
        entries = (Entry("planted/probe.py", "f_urlopen", ("urlopen",), "w", "g", "d"),
                   Entry("planted/probe.py", "no_such_function", ("urlopen",), "w", "g", "d"))
        orphans, unused = _unmatched(sites, entries)
        self.assertTrue(any(o.startswith("planted/probe.py:%d in f_request:" % _planted_line("L2")) for o in orphans), orphans)
        self.assertFalse(any("f_urlopen" in o for o in orphans))
        self.assertEqual(unused, ["planted/probe.py no_such_function (urlopen)"])
        # a kind the entry does not name is an orphan too
        orphans, _ = _unmatched(sites, (Entry("planted/probe.py", "f_urlopen", ("Request",), "w", "g", "d"),))
        self.assertTrue(any("in f_urlopen:" in o for o in orphans))


# ---------------------------------------------------------------------------------------------------
# The reference's list held equal to the allowlist, and the guide pointing here.
# ---------------------------------------------------------------------------------------------------

ITEMS_HEAD = "and on an entry with no site: "
ITEMS_TAIL = ". The agents' and the judge pipeline's model calls go through `claude`"


def reference_items(flat):
    """The items of the reference's list, in order: the span between the fixed head and tail split on `; `, the
    last item's leading `and ` removed. None when the head or the tail is absent."""
    if ITEMS_HEAD not in flat or ITEMS_TAIL not in flat:
        return None
    start = flat.index(ITEMS_HEAD) + len(ITEMS_HEAD)
    end = flat.index(ITEMS_TAIL, start)
    items = flat[start:end].split("; ")
    if items and items[-1].startswith("and "):
        items[-1] = items[-1][4:]
    return items


def listed_docs():
    """The allowlist's docs in first-appearance order, the upload's head sentence excluded."""
    out = []
    for e in ALLOWLIST:
        if e.doc != DOC_UPLOAD and e.doc not in out:
            out.append(e.doc)
    return out


class Docs(unittest.TestCase):
    """docs/reference.md's "Requests Romp makes on its own" equals the allowlist, item for item and in order, and
    docs/guide.md points at this module and at that subsection. By boolean, naming the item, never the page."""

    @staticmethod
    def _flat(*parts):
        with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
            return " ".join(fh.read().split())

    def test_the_reference_list_is_the_allowlist_in_order(self):
        flat = self._flat("docs", "reference.md")
        items = reference_items(flat)
        self.assertIsNotNone(items, "the reference has no list between %r and %r" % (ITEMS_HEAD, ITEMS_TAIL))
        docs = listed_docs()
        missing_entries = [i for i in items if i not in docs]
        missing_items = [d for d in docs if d not in items]
        self.assertFalse(missing_entries, "reference items no allowlist entry carries (a reworded or added item):\n"
                         + "\n".join(missing_entries))
        self.assertFalse(missing_items, "allowlist docs the reference does not list (add each as an item):\n"
                         + "\n".join(missing_items))
        self.assertEqual(items, docs, "the reference lists the same items in another order than the allowlist")
        for d in docs:
            self.assertEqual(flat.count(d), 1, "the item must occur exactly once in the reference: " + d)
        self.assertEqual(flat.count(DOC_UPLOAD), 1, "the subsection's head sentence names the upload")

    def test_the_reference_marks_the_list_derived_by_this_module_and_names_the_shell_layers_finds(self):
        flat = self._flat("docs", "reference.md")
        section = flat[flat.index("### Requests Romp makes on its own"):flat.index("### The chat wire's two protocols")]
        self.assertIn("tests/test_outbound_requests_census.py", section)
        self.assertIn("derived", section)
        for e in SHELL_ALLOWLIST:
            self.assertEqual(section.count(e.doc), 1, "the shell layer's find is not in the subsection once: " + e.doc)
        # the sentence this census contradicts: bin/'s scripts make more than one non-local fetch (pip in both
        # installers, gh in watch-pr), so a claim of one cannot stand beside the derived list
        self.assertFalse("the one non-local fetch the census allows in a shell script" in section,
                         "the subsection claims one non-local fetch in the shell scripts; the shell layer finds "
                         "%d" % len(SHELL_ALLOWLIST))
        # the route probe: a connect that sends nothing is disclosed beside the loopback sentence
        self.assertIn(ROUTE_PROBES[0][0].split("/")[-1], "kernel.py")

    def test_the_guide_points_at_this_module_and_the_reference_subsection(self):
        flat = self._flat("docs", "guide.md")
        self.assertIn("`tests/test_outbound_requests_census.py`", flat)
        self.assertIn("reference.md#requests-romp-makes-on-its-own", flat)
        self.assertIn("Other parts of Romp make requests of their own", flat)

    def test_reference_items_reads_the_span_the_way_the_reference_spells_it(self):
        flat = ("... and on an entry with no site: alpha one; beta two; and gamma three. The agents' and the judge "
                "pipeline's model calls go through `claude`, not ...")
        self.assertEqual(reference_items(flat), ["alpha one", "beta two", "gamma three"])
        self.assertIsNone(reference_items("no list here"))


if __name__ == "__main__":
    unittest.main()
