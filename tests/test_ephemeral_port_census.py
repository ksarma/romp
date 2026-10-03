#!/usr/bin/env python3
"""No test writes a fixed port in the ephemeral range (2026-10-03).

WHY. tests/test_postal_token.py's PeerTokenPlumbing pointed a peer at the fixed loopback port 45001 with up: true. The
bus then starts a real dialer (_peer_loop), whose exchange POSTs to that port with a timeout of EXCHANGE_WAIT + 10, 30 s by
default. 45001 is inside the range the system hands out as source ports and as the ports of bind(0), so any process on
the machine can hold a listener there: another xdist worker, another checkout's sweep, a served lab. When nothing
listens, the dial is refused at once. When a listener accepts and never answers, the dialer sits inside its request, the
wake that ends it cannot reach it, and the test's cleanup, which waits 10 s for the dialer to end, fails for a reason
outside the test (a sweep's red, reproduced with a planted silent listener). A fixed port below that range is no fix:
the machine's own services listen there (the postal bus on 25302, the kernel on 29855). tests/test_postal_peer_tier.py
already used the fix: a test that needs a dial that never lands names port 1. Below 1024 nothing unprivileged can
listen on Linux, so a dial there is refused at once on any machine; where a test needs several distinct ports (a tunnel
row's local, bus and reverse ports), each takes its own number below 1024 (1, 2, 3 and so on). A test that needs a real
listener takes its port from the system: a bind to port 0, or tests/lab_ports.py's reserve() for a kernel.

THE RANGE is 32768-65535 (LOW, HIGH): the union of Linux's default ephemeral range, 32768-60999 (a machine can change
it in /proc/sys/net/ipv4/ip_local_port_range; CI's ubuntu-latest runners are Linux at the default), and the range
macOS hands out, 49152-65535 (CI's macOS cells).

THE FILES are derived by walking the checkout (files()): every regular file under tests/, fixtures included, and every
file named *.test.* or under a directory named fixtures anywhere else, outside node_modules, .git, dist, out and
__pycache__. A symlink is skipped (its target is read where it lives). A file that is not UTF-8 text is skipped, and the
census fails if the walk finds no files, no Python file with a number in the range, or no product function to resolve a
call against, so it never passes on nothing. A file is read only when it holds a five-digit number in the range, or, for
Python, a modulus by a constant of four or five digits (the computed form, below); a port computed from smaller constants
alone (30000 + 5000) is not read.

THE RULE. A number in the range counts when it is WRITTEN AS A PORT, in one of these positions.
  In Python, read by AST (scan_python):
    a value under a dict key that names a port ({"port": N}, {"local_port": N}, {"busPort": N}; a key names a port when
    one of its words, split at underscores, other punctuation and camelCase, is "port" or "ports": "report" does not);
    a keyword argument that names a port (bus_port=N, ROMP_POSTAL_PORT="N");
    an assignment to a target that names a port (PORT = N, km.BUS_PORT = N, os.environ["ROMP_POSTAL_PORT"] = "N"), a
    tuple target read element by element against a tuple value of its length;
    the default of a parameter that names a port (def _notify(self, host, up, port=N));
    a positional argument whose parameter names a port, in the function the callee's name resolves to: a function the
    module defines (code text included, below), else one of kernel/, postal/ or cli/ (km._notify_bus_peer("h", N, True));
    a first parameter named self or cls is skipped; a *ports parameter takes every extra argument;
    an element of the sequence a for loop or a comprehension walks, under a target that names a port (for host, port in
    (("h", N),): the element at the port's index);
    the second argument of a call whose first argument is a string that names a port (os.environ.setdefault(
    "ROMP_POSTAL_PORT", "N"), monkeypatch.setenv);
    the port of an address tuple whose host is a loopback or wildcard literal (("127.0.0.1", N));
    an operand formatted into an address ("http://127.0.0.1:%d/" % N);
    and one hop through a name: a value written in one of those positions as a bare name counts the literals the module
    binds that name to (P = N ... {"port": P}).
  An int counts, and so does a string of the number's five digits, except as a positional argument: a string handed
  to a function by position is that function's input text (a parser's, km._manager_port("65535")), not a setting.
  An expression counts when it is bounded and can reach the range: interval() reads constants, + - * // and % over
  them, and an unknown operand of % by a constant as 0 to the constant less one, so 20000 + os.getpid() % 20000 is
  20000-39999 and counts; an expression with an unbounded unknown (base + i) is not read.
  In any file, read as text (text_hits): a non-Python file whole, and in Python each string literal that is neither a
  docstring nor code text:
    key   a port-named key or name after a delimiter ({ , ( [ ;) or at a line's start, then : or = and the number
          ({ port: N }, "busPort": N, , port=N);
    decl  a port-named name declared and assigned (const port = N, local port=N, export ROMP_POSTAL_PORT=N);
    env   an upper-case port-named name, then : or = and the number, quoted or not (ROMP_POSTAL_PORT'] = 'N');
    flag  a --*port option (--port N, --port=N);
    authority  host:N after a loopback or wildcard host or after // in a URL (http://127.0.0.1:N, //TESTHOST:N);
    address    a loopback or wildcard address tuple in text (("127.0.0.1", N));
    call  a number handed first to .listen(, .connect(, createConnection( or .bind(;
    pair  a port-named string and the number handed together ("ROMP_POSTAL_PORT", "N").
  Code text in a Python string, one that parses as Python (a probe a test runs with python -c, a planted module), is
  read by the Python rules, whether or not anything runs it: the census cannot tell a probe that runs from one that is
  only parsed, so code is code. A hit inside a string literal is reported on the source line that writes the number.

THE EXCLUDED CLASS, a stated predicate rather than a list: a number in the range written anywhere else is not a port
setting, neither dials nor binds, and stays. That is prose, a comment and a docstring; a log, error or ps line a test
hands to a parser (the ssh errors of tests/test_tunnel_stale_and_logging.py, the ps lines of tests/test_kernel_tunnels.py,
whose -L 50512:127.0.0.1:29855 puts the number before the host); a string handed by position to a parser; an
assertion's expected value (it follows the setting it checks, so the setting is what counts); an id, a size, a byte
offset, a timeout and a duration.

WHAT IT CANNOT SEE (stated, not closed): a port that reaches its setting through a name the module does not bind to a
literal (a parameter, a container, a call's result, a name another module binds), through more than one hop, or by a
run-time substitution into code text (a template's __SENTINEL__, a %r filled with the variable's name); an unbounded
computed port; a positional port in JavaScript or shell beyond the call rule; a value under a key spelled other than
as a word (a computed key); code text that does not parse on its own (an indented fragment, a %-template), which the
text rules read instead, so its positional ports are not resolved. Each planted shape below is red, with the rule
it names among the rules that read it, and each excluded shape is green.

Synthetic: reads the tree only; no socket, no kernel, no subprocess.
"""
import ast
import os
import re
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import parse_cache                                  # noqa: E402  one parse per file per process, shared with the other AST censuses

LOW, HIGH = 32768, 65535
LOOPBACK = frozenset({"127.0.0.1", "localhost", "0.0.0.0", "::1", "::", ""})
SKIP_DIRS = frozenset({"node_modules", ".git", "dist", "out", "__pycache__"})
PRODUCT_DIRS = ("kernel", "postal", "cli")
FIVE = re.compile(r"(?<![\w.])(\d{5})(?![\w.])")     # a five-digit number standing alone (not inside an id, a decimal or a hash)
WORDS = re.compile(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|\d+")
MOD_CONST = re.compile(r"%[ \t]*\d{4,5}\b")         # a modulus by a constant of four or five digits: the computed form interval() bounds
MAX_CODE_DEPTH = 3                                  # code text inside code text inside code text, and no deeper


def in_range(v):
    return isinstance(v, int) and not isinstance(v, bool) and LOW <= v <= HIGH


def names_a_port(name):
    """True when one of the words of `name` (split at punctuation and camelCase) is port or ports."""
    if not isinstance(name, str):
        return False
    return any(w.lower() in ("port", "ports") for part in re.split(r"[^A-Za-z0-9]+", name) for w in WORDS.findall(part))


def _digits(v):
    """The number a string of exactly five digits spells, else None."""
    if isinstance(v, str) and len(v.strip()) == 5 and v.strip().isdigit():
        return int(v.strip())
    return None


# The text rules.
_NUM = r"[\"'`]?(?P<n>\d{5})(?![\w.])"
_HOST = r"(?:\b(?:127\.0\.0\.1|localhost|0\.0\.0\.0)\b|\[::1?\])"
TEXT_RULES = (
    ("key", re.compile(r"(?:^|[{,(\[;])[ \t]*[\"'`]?(?P<name>[\w$.-]+)[\"'`]?[ \t]*[:=][ \t]*" + _NUM, re.M)),
    ("decl", re.compile(r"\b(?:const|let|var|local|export|readonly|declare(?:[ \t]+-\w+)?)[ \t]+(?P<name>[\w$]+)[ \t]*=[ \t]*" + _NUM)),
    ("env", re.compile(r"\b(?P<name>[A-Z][A-Z0-9_]*)[\"'`]?\]?[ \t]*[:=][ \t]*" + _NUM)),
    ("flag", re.compile(r"--(?P<name>[\w-]+)(?:=|[ \t]+)" + _NUM)),
    ("authority", re.compile(r"(?:" + _HOST + r"|//[\w.-]+)[ \t]*:[ \t]*(?P<n>\d{5})(?![\w.])")),
    ("address", re.compile(r"\([ \t]*[\"'](?:127\.0\.0\.1|localhost|0\.0\.0\.0|::1?|)[\"'][ \t]*,[ \t]*(?P<n>\d{5})[ \t]*[,)]")),
    ("call", re.compile(r"(?:\.listen|\.connect|createConnection|\.bind)\([ \t]*(?P<n>\d{5})(?![\w.])")),
    ("pair", re.compile(r"\([ \t]*[\"'`](?P<name>[\w$.-]+)[\"'`][ \t]*,[ \t]*" + _NUM)),
)
_NAMED = frozenset({"key", "decl", "env", "flag", "pair"})   # the rules whose match carries a name that must name a port


def _line_in(first, last, after):
    """The physical line of a place inside a string literal that spans lines `first` to `last`, with `after` newlines of
    the literal's value after the place. It is counted back from the literal's end, so a triple-quoted literal whose
    opening line ends in a backslash reads right, and it is held between the two lines, so a literal written on one line
    with newline escapes reads as that line."""
    return max(first, min(last, last - after))


def text_hits(text, first_line=1, last_line=None):
    """[(line, number, why)] for every text rule's match in `text`: in a whole file, the line counted from `first_line`;
    in a string literal spanning `first_line` to `last_line`, the line _line_in reads."""
    out = []
    for rule, rx in TEXT_RULES:
        for m in rx.finditer(text):
            v = int(m.group("n"))
            if not in_range(v):
                continue
            if rule in _NAMED and not names_a_port(m.group("name")):
                continue
            if rule == "env" and m.group("name") != m.group("name").upper():
                continue
            if last_line is None:
                line = first_line + text.count("\n", 0, m.start("n"))
            else:
                line = _line_in(first_line, last_line, text.count("\n", m.start("n")))
            out.append((line, v, "text rule %s" % rule))
    return out


# The Python rules.
def _params(fn):
    a = fn.args
    names = [x.arg for x in a.posonlyargs + a.args]
    if names and names[0] in ("self", "cls"):
        names = names[1:]
    return tuple(names), (a.vararg.arg if a.vararg else None)


def defs_of(tree, into=None):
    """{name: [(positional parameter names, *args name)]} for every function `tree` defines, at any depth."""
    into = {} if into is None else into
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            into.setdefault(n.name, []).append(_params(n))
    return into


def _docstrings(tree):
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.body:
            first = n.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                out.add(id(first.value))
    return out


def _target_name(t):
    if isinstance(t, ast.Name):
        return t.id
    if isinstance(t, ast.Attribute):
        return t.attr
    if isinstance(t, ast.Subscript) and isinstance(t.slice, ast.Constant) and isinstance(t.slice.value, str):
        return t.slice.value
    return None


def _callee(f):
    return f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else None)


def interval(node, bound=None):
    """(lo, hi, computed) for an int expression the census can bound, else None: constants, + - * // and % over them, a
    name bound to one int literal, str() or int() around one, and an unknown operand of % by a positive constant read as
    0 to the constant less one. computed is True when an unknown took part."""
    bound = bound or {}
    if isinstance(node, ast.Constant) and isinstance(node.value, int) and not isinstance(node.value, bool):
        return node.value, node.value, False
    if isinstance(node, ast.Name) and len(bound.get(node.id, ())) == 1:
        lit = bound[node.id][0]
        if isinstance(lit, ast.Constant) and isinstance(lit.value, int) and not isinstance(lit.value, bool):
            return lit.value, lit.value, False
        return None
    if isinstance(node, ast.Call) and _callee(node.func) in ("str", "int") and len(node.args) == 1 and not node.keywords:
        return interval(node.args[0], bound)
    if isinstance(node, ast.BinOp):
        right = interval(node.right, bound)
        left = interval(node.left, bound)
        if isinstance(node.op, ast.Mod) and right and right[0] == right[1] and right[0] > 0 and left is None:
            return 0, right[0] - 1, True
        if left is None or right is None:
            return None
        (a, b, ca), (c, d, cb) = left, right
        if isinstance(node.op, ast.Add):
            return a + c, b + d, ca or cb
        if isinstance(node.op, ast.Sub):
            return a - d, b - c, ca or cb
        if isinstance(node.op, ast.Mult):
            ends = (a * c, a * d, b * c, b * d)
            return min(ends), max(ends), ca or cb
        if isinstance(node.op, (ast.FloorDiv, ast.Mod)) and c == d and c > 0:
            if isinstance(node.op, ast.FloorDiv):
                return a // c, b // c, ca or cb
            return (a % c, b % c, ca or cb) if a == b else (0, c - 1, ca or cb)
    return None


class _Scan:
    """One module's (or one code text's) Python reading; hits are (line, number, why)."""

    def __init__(self, own, product, line_of, depth, src=None):
        self.own, self.product, self.line_of, self.depth, self.src = own, product, line_of, depth, src
        self.hits = []

    def _place(self, est, v, first, last):
        """The line among `first`-`last` of the module's source that writes the number `v`, nearest the estimate `est`
        (several pieces of one literal can sit on separate lines); `est` when no line there writes it or the source is
        not at hand."""
        if not self.src:
            return est
        rx = re.compile(r"(?<!\d)%d(?!\d)" % v)
        cands = [i for i in range(first, last + 1) if i - 1 < len(self.src) and rx.search(self.src[i - 1])]
        return min(cands, key=lambda i: abs(i - est)) if cands else est

    def _resolve(self, name):
        return self.own[name] if name in self.own else self.product.get(name, ())

    def _record(self, node, v, why):
        self.hits.append((self.line_of(node), v, why))

    def literal(self, node, why, strings=True):
        """The numbers `node` writes as a port: an int constant, a five-digit string (when `strings`), each element of a
        tuple, list or set display of them, or a bounded expression that can reach the range."""
        if isinstance(node, ast.Constant):
            v = node.value
            if in_range(v):
                self._record(node, v, why)
            elif strings and in_range(_digits(v)):
                self._record(node, _digits(v), why)
        elif isinstance(node, (ast.Tuple, ast.List, ast.Set)):
            for e in node.elts:
                self.literal(e, why, strings)
        else:
            iv = interval(node, self.bound)
            if iv and iv[2] and iv[0] <= HIGH and iv[1] >= LOW:
                self._record(node, max(iv[0], LOW), "%s, computed into %d-%d" % (why, iv[0], iv[1]))
            elif iv and not iv[2] and in_range(iv[0]):
                self._record(node, iv[0], why + ", a constant expression")

    def _bind(self, t, v):
        if isinstance(t, ast.Name):
            if isinstance(v, (ast.Constant, ast.Tuple, ast.List, ast.Set)):
                self.bound.setdefault(t.id, []).append(v)
        elif isinstance(t, (ast.Tuple, ast.List)) and isinstance(v, (ast.Tuple, ast.List)) and len(t.elts) == len(v.elts):
            for te, ve in zip(t.elts, v.elts):
                self._bind(te, ve)

    def _value(self, v, why, strings=True):
        if isinstance(v, ast.Name) and v.id in self.bound:
            self.uses.append((v.id, why, strings))
        else:
            self.literal(v, why, strings)

    def scan(self, tree):
        docs = _docstrings(tree)
        self.bound, self.uses = {}, []
        for n in ast.walk(tree):
            if isinstance(n, (ast.Assign, ast.AnnAssign, ast.NamedExpr)) and n.value is not None:
                for t in (n.targets if isinstance(n, ast.Assign) else [n.target]):
                    self._bind(t, n.value)
            elif isinstance(n, (ast.For, ast.AsyncFor, ast.comprehension)) and isinstance(n.iter, (ast.Tuple, ast.List, ast.Set)):
                for e in n.iter.elts:
                    self._bind(n.target, e)
        for n in ast.walk(tree):
            if isinstance(n, ast.Dict):
                for k, v in zip(n.keys, n.values):
                    key = k.value if isinstance(k, ast.Constant) else (k.id if isinstance(k, ast.Name) else None)
                    if names_a_port(key):
                        self._value(v, "the value of the key %r" % key)
            elif isinstance(n, ast.Call):
                for kw in n.keywords:
                    if names_a_port(kw.arg):
                        self._value(kw.value, "the keyword %s=" % kw.arg)
                if len(n.args) >= 2 and isinstance(n.args[0], ast.Constant) and names_a_port(n.args[0].value):
                    self._value(n.args[1], "the value handed with the name %r" % n.args[0].value)
                name = _callee(n.func)
                for params, star in (self._resolve(name) if name else ()):
                    for i, a in enumerate(n.args):
                        p = params[i] if i < len(params) else star
                        if names_a_port(p) and not isinstance(a, ast.Starred):
                            self._value(a, "the argument %s of %s()" % (p, name), strings=False)
            elif isinstance(n, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.NamedExpr)) and n.value is not None:
                for t in (n.targets if isinstance(n, ast.Assign) else [n.target]):
                    if isinstance(t, (ast.Tuple, ast.List)):
                        if isinstance(n.value, (ast.Tuple, ast.List)) and len(t.elts) == len(n.value.elts):
                            for te, ve in zip(t.elts, n.value.elts):
                                if names_a_port(_target_name(te)):
                                    self._value(ve, "an assignment to %s" % _target_name(te))
                    elif names_a_port(_target_name(t)):
                        self._value(n.value, "an assignment to %s" % _target_name(t))
            elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                a = n.args
                pos = a.posonlyargs + a.args
                for arg, d in list(zip(pos[len(pos) - len(a.defaults):], a.defaults)) + list(zip(a.kwonlyargs, a.kw_defaults)):
                    if d is not None and names_a_port(arg.arg):
                        self._value(d, "the default of %s" % arg.arg)
            elif isinstance(n, (ast.For, ast.AsyncFor, ast.comprehension)) and isinstance(n.iter, (ast.Tuple, ast.List, ast.Set)):
                t = n.target
                if isinstance(t, (ast.Tuple, ast.List)):
                    for i, te in enumerate(t.elts):
                        if names_a_port(_target_name(te)):
                            for e in n.iter.elts:
                                if isinstance(e, (ast.Tuple, ast.List)) and i < len(e.elts):
                                    self.literal(e.elts[i], "the loop target %s" % _target_name(te))
                elif names_a_port(_target_name(t)):
                    for e in n.iter.elts:
                        self.literal(e, "the loop target %s" % _target_name(t))
            elif isinstance(n, (ast.Tuple, ast.List)) and len(n.elts) >= 2:
                h = n.elts[0]
                if isinstance(h, ast.Constant) and isinstance(h.value, str) and h.value in LOOPBACK:
                    self.literal(n.elts[1], "the port of the address (%r, ...)" % h.value, strings=False)
            elif isinstance(n, ast.BinOp) and isinstance(n.op, ast.Mod) and isinstance(n.left, ast.Constant) \
                    and isinstance(n.left.value, str) and re.search(r"(?:" + _HOST + r"|//[\w.-]+):%[ds]", n.left.value):
                self.literal(n.right, "an operand formatted into an address")
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs and FIVE.search(n.value):
                self._string(n)
        for name, why, strings in self.uses:
            for lit in self.bound.get(name, ()):
                self.literal(lit, "%s, through the name %s" % (why, name), strings)

    def _string(self, n):
        first, last = self.line_of(n), self.line_of(n, end=True)
        sub = None
        if self.depth < MAX_CODE_DEPTH:
            try:
                sub = ast.parse(n.value)
            except (SyntaxError, ValueError, RecursionError, MemoryError):
                sub = None
        if sub is not None and sub.body:
            total = n.value.count("\n")

            def line_of(x, end=False, first=first, last=last, total=total):
                return _line_in(first, last, total - (getattr(x, "end_lineno" if end else "lineno", 1) - 1))
            inner = _Scan(defs_of(sub, dict(self.own)), self.product, line_of, self.depth + 1, self.src)
            inner.scan(sub)
            self.hits.extend((self._place(ln, v, first, last), v, "in code text, " + why) for ln, v, why in inner.hits)
        else:
            self.hits.extend((self._place(ln, v, first, last), v, why) for ln, v, why in text_hits(n.value, first, last))


def scan_python(tree, product, text=None):
    """[(line, number, why)], sorted and one per (line, number), for a parsed module; `text`, the module's source, places a
    hit inside a string literal on the physical line that writes it."""
    def line_of(x, end=False):
        return getattr(x, "end_lineno" if end else "lineno", 1) or 1
    sc = _Scan(defs_of(tree), product, line_of, 0, text.split("\n") if text is not None else None)
    sc.scan(tree)
    return _one_per_place(sc.hits)


def _one_per_place(hits):
    seen, out = set(), []
    for line, v, why in sorted(hits):
        if (line, v) not in seen:
            seen.add((line, v))
            out.append((line, v, why))
    return out


# The population.
def files(root):
    """Every file the census reads under `root`: the files under tests/, and every *.test.* file and fixtures file
    elsewhere, outside SKIP_DIRS; symlinks skipped."""
    out = []
    for d, dirs, names in os.walk(root):
        dirs[:] = sorted(x for x in dirs if x not in SKIP_DIRS)
        parts = os.path.relpath(d, root).split(os.sep)
        for f in sorted(names):
            p = os.path.join(d, f)
            if os.path.islink(p) or not os.path.isfile(p):
                continue
            if parts[0] == "tests" or ".test." in f or "fixtures" in parts:
                out.append(p)
    return out


def product_defs(root):
    into = {}
    for sub in PRODUCT_DIRS:
        base = os.path.join(root, sub)
        for f in sorted(os.listdir(base)):
            if f.endswith(".py"):
                defs_of(parse_cache.source_and_tree(os.path.join(base, f))[1], into)
    return into


def census(root):
    """{"hits": [(path relative to root, line, number, why)], "files": n, "python_read": n, "product_defs": n}."""
    product = product_defs(root)
    hits, n_files, n_py = [], 0, 0
    for p in files(root):
        n_files += 1
        rel = os.path.relpath(p, root)
        try:
            with open(p, encoding="utf-8") as fh:
                text = fh.read()
        except (UnicodeDecodeError, OSError):
            continue
        if not any(in_range(int(m.group(1))) for m in FIVE.finditer(text)) and not (p.endswith(".py") and MOD_CONST.search(text)):
            continue
        if p.endswith(".py"):
            n_py += 1
            found = scan_python(parse_cache.source_and_tree(p)[1], product, text)
        else:
            found = _one_per_place(text_hits(text))
        hits += [(rel, line, v, why) for line, v, why in found]
    return {"hits": hits, "files": n_files, "python_read": n_py, "product_defs": len(product)}


def render(hits):
    return "\n".join("  %s:%d: %d, %s" % h for h in hits)


# The pins.
class NoFixedEphemeralPort(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = parse_cache.derived("ephemeral_port_census", lambda: census(ROOT))

    def test_no_test_writes_a_fixed_port_in_the_ephemeral_range(self):
        hits = self.result["hits"]
        if hits:
            self.fail("%d fixed port(s) in %d-%d written as a port. Any process can hold a listener on such a port, so a "
                      "dial to it can hang. Use port 1 for a dial that never lands (2, 3 and on for a row's other ports), "
                      "and a bind to port 0 or tests/lab_ports.reserve for a listener; this module's docstring states the "
                      "rule and what it excludes:\n%s" % (len(hits), LOW, HIGH, render(hits)))

    def test_the_population_is_not_empty(self):
        self.assertGreater(self.result["files"], 1000, "the walk read the tests and the node suites")
        self.assertGreater(self.result["python_read"], 50, "Python modules with a number in the range were read")
        self.assertGreater(self.result["product_defs"], 1000, "the product's functions are the resolver's index")
        self.assertIn(os.path.join(ROOT, "tests", "test_postal_token.py"), files(ROOT))
        self.assertIn(os.path.join(ROOT, "tests", "fixtures"), {os.path.dirname(p) for p in files(ROOT)})


def _n(k=0):
    """A number in the range, built at run time so this file holds none in a port position: LOW + 12233 + k."""
    return LOW + 12233 + k


class Plants(unittest.TestCase):
    """Each planted shape is one hit, read by the rule it names (among any others that read the same place), and each
    excluded shape is green."""

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.d, True)
        os.makedirs(os.path.join(self.d, "tests"))
        for sub in PRODUCT_DIRS:
            os.makedirs(os.path.join(self.d, sub))
        with open(os.path.join(self.d, "kernel", "k.py"), "w", encoding="utf-8") as f:
            f.write("def _notify_bus_peer(host, port, up):\n    pass\n\n\nclass R:\n    def ring(self, port):\n        pass\n")

    def _hits(self, name, text):
        """The census's hits in the planted file `name` (written fresh under the scratch root's tests/; the root and every
        plant in it go with the test's cleanup)."""
        p = os.path.join(self.d, "tests", name)
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
        return [h for h in census(self.d)["hits"] if h[0] == os.path.join("tests", name)]

    def _whys(self, name, text):
        """Every reason the rules give for the plant, before the census keeps one per place (two rules can read one place,
        a shell export is both a declaration and an upper-case name)."""
        if not name.endswith(".py"):
            return [w for _l, _v, w in text_hits(text)]
        sc = _Scan(defs_of(ast.parse(text)), product_defs(self.d), lambda x, end=False: getattr(x, "lineno", 1), 0)
        sc.scan(ast.parse(text))
        return [w for _l, _v, w in sc.hits]

    def assertRed(self, name, text, why_part, n=None):
        hits = self._hits(name, text)
        self.assertEqual([h[2] for h in hits], [n or _n()], "%s: one hit, the planted number: %r\n%s" % (name, hits, text))
        whys = self._whys(name, text)
        self.assertTrue(any(why_part in w for w in whys), "%s: read by the rule %r: %r" % (name, why_part, whys))

    def assertGreen(self, name, text):
        hits = self._hits(name, text)
        self.assertEqual(hits, [], "%s: excluded, yet counted:\n%s\n%s" % (name, render(hits), text))

    def test_the_python_positions(self):
        n = _n()
        for label, src, why in (
                ("dict key", 'ps.peer_update({"host": "TESTHOST", "port": %d, "up": True})\n' % n, "key 'port'"),
                ("camelCase key", 'row = {"busPort": %d}\n' % n, "key 'busPort'"),
                ("digit string under a key", 'env = {"ROMP_POSTAL_PORT": "%d"}\n' % n, "key 'ROMP_POSTAL_PORT'"),
                ("keyword", 'row(bus_port=%d)\n' % n, "keyword bus_port="),
                ("env keyword", 'f(ROMP_POSTAL_PORT="%d")\n' % n, "keyword ROMP_POSTAL_PORT="),
                ("assignment", 'km.BUS_PORT = %d\n' % n, "assignment to BUS_PORT"),
                ("env subscript", 'os.environ["ROMP_KERNEL_PORT"] = "%d"\n' % n, "assignment to ROMP_KERNEL_PORT"),
                ("tuple assignment", 'h, port = "x", %d\n' % n, "assignment to port"),
                ("default", 'def notify(host, up, port=%d):\n    pass\n' % n, "default of port"),
                ("own function positional", 'def rec(port, pid=None):\n    pass\n\n\nrec(%d)\n' % n, "argument port of rec()"),
                ("product function positional", 'km._notify_bus_peer("TESTHOST", %d, True)\n' % n, "argument port of _notify_bus_peer()"),
                ("product method positional", 'r.ring(%d)\n' % n, "argument port of ring()"),
                ("loop target", 'for host, port in (("A", %d),):\n    pass\n' % n, "loop target port"),
                ("a call handed a port name and its value", 'os.environ.setdefault("ROMP_POSTAL_PORT", "%d")\n' % n,
                 "handed with the name 'ROMP_POSTAL_PORT'"),
                ("address", 's.connect(("127.0.0.1", %d))\n' % n, "address ('127.0.0.1'"),
                ("formatted address", 'u = "http://127.0.0.1:%%d/peer" %% %d\n' % n, "formatted into an address"),
                ("one hop", 'P = %d\nps.peer_update({"host": "h", "port": P})\n' % n, "through the name P"),
                ("code text", 'subprocess.run([sys.executable, "-c", %r])\n' % ('bus.peer_update({"host": "h", "port": %d, "up": True})' % n),
                 "in code text"),
                ("text rule in a string", 'JS = "await fetch(\\"http://127.0.0.1:%d/x\\")"\n' % n, "text rule authority")):
            with self.subTest(label):
                self.assertRed("test_plant.py", src, why)

    def test_a_computed_port_that_can_reach_the_range(self):
        shape = 'env = dict(ROMP_POSTAL_PORT=str(%d + os.getpid() %% %d))\n'      # written as a template, so this file holds no such code
        hits = self._hits("test_plant.py", shape % (20000, 20000))
        self.assertEqual(len(hits), 1, hits)
        self.assertIn("computed into 20000-39999", hits[0][3])
        self.assertGreen("test_plant.py", shape % (20000, 10000))
        self.assertGreen("test_plant.py", 'env = dict(ROMP_POSTAL_PORT=str(base + i))\n')

    def test_the_text_rules(self):
        n = _n()
        for label, name, src, why in (
                ("JS key", "a.test.mjs", "const srv = { host: '127.0.0.1', port: %d };\n" % n, "rule key"),
                ("JSON key", "x.json", '{\n  "busPort": %d\n}\n' % n, "rule key"),
                ("JS declaration", "a.test.ts", "const proxyPort = %d;\n" % n, "rule decl"),
                ("shell env", "a.bats", "export ROMP_POSTAL_PORT=%d\n" % n, "rule env"),
                ("shell local", "b.bats", "    local port=%d\n" % n, "rule decl"),
                ("flag", "c.bats", "run romp serve --port %d\n" % n, "rule flag"),
                ("URL", "d.test.mjs", "await fetch('http://localhost:%d/healthz');\n" % n, "rule authority"),
                ("address in shell python", "e.bats", "python3 -c \"s.bind(('127.0.0.1', %d))\"\n" % n, "rule address"),
                ("listen", "f.test.js", "server.listen(%d, '127.0.0.1');\n" % n, "rule call"),
                ("a name and its value handed together", "g.test.js", "setEnv('ROMP_POSTAL_PORT', '%d');\n" % n, "rule pair")):
            with self.subTest(label):
                self.assertRed(name, src, why)

    def test_the_excluded_class_stays(self):
        n = _n()
        for label, name, src in (
                ("prose in a comment", "test_x.py", "# the old port %d sat inside the range\nx = 1\n" % n),
                ("docstring", "test_x.py", '"""It dialed port %d once."""\n' % n),
                ("ssh error line", "test_x.py", 'LINES = ("Error: remote port forwarding failed for listen port %d",\n'
                                                '         "channel_setup_fwd_listener_tcpip: cannot listen to port: %d")\n' % (n, n)),
                ("ps line", "test_x.py", 'PS = "  12345 /usr/bin/ssh -N -T -L %d:127.0.0.1:29855 TESTHOST"\n' % n),
                ("parser input by position", "test_x.py", 'self.assertEqual(km._manager_port("%d"), %d)\n' % (n, n)),
                ("an expected value", "test_x.py", 'self.assertEqual((snap["port"], snap["up"]), (%d, True))\n' % n),
                ("a timeout", "test_x.py", 'page.goto(url, timeout=%d)\n' % n),
                ("a word that only contains port", "test_x.py", 'row = {"report": %d, "transport": %d}\n' % (n, n)),
                ("an id", "test_x.py", 'MID = "1700000001.%d_44444.TESTHOST"\n' % n),
                ("JS timeout", "g.test.ts", "await page.waitForSelector('#x', { timeout: %d });\n" % n),
                ("JS prose", "h.test.ts", "// the bus port: %d was the old default\n" % n),
                ("bats size", "i.bats", '[[ "$output" == *"dom %d"* ]]\n' % n)):
            with self.subTest(label):
                self.assertGreen(name, src)

    def test_a_hit_inside_a_string_that_spans_lines_names_its_own_line(self):
        n = _n()
        src = ('import textwrap\n'
               'PROBE = textwrap.dedent("""\\\n'
               '    import os\n'
               '    os.environ["ROMP_POSTAL_PORT"] = "%d"\n'
               '""")\n'
               'JS = """\n'
               'const srv = { port: %d };\n'
               '"""\n'
               'ONE = "x = 1\\nbus.peer_update({\\"port\\": %d})"\n') % (n, n, n)
        self.assertEqual([h[1] for h in self._hits("test_plant.py", src)], [4, 7, 9], src)

    def test_a_port_below_the_range_or_port_one_is_not_counted(self):
        self.assertGreen("test_x.py", 'ps.peer_update({"host": "TESTHOST", "port": 1, "up": True})\nrow = {"local_port": 2, "bus_port": %d}\n'
                         % (LOW - 1))

    def test_the_rule_reads_the_upper_end_of_the_range(self):
        self.assertRed("test_plant.py", 'row = {"local_port": %d}\n' % HIGH, "key 'local_port'", n=HIGH)
        self.assertGreen("test_x.py", 'row = {"local_port": %d}\n' % (LOW - 1))


if __name__ == "__main__":
    unittest.main()
