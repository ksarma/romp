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
already used the fix: a test that needs a dial that never lands names port 1. On Linux at the default nothing
unprivileged can listen below 1024, and by convention nothing listens on port 1, so in practice a dial there is refused
at once; where a test needs several distinct ports (a tunnel row's local, bus and reverse ports), each takes its own
number below 1024 (1, 2, 3 and so on). A test that needs a real listener takes its port from the system: a bind to port
0, or tests/lab_ports.py's reserve() for a kernel.

THE RANGE is 32768-65535 (LOW, HIGH): the union of Linux's default ephemeral range, 32768-60999 (a machine can change
it in /proc/sys/net/ipv4/ip_local_port_range; CI's ubuntu-latest runners are Linux at the default), and the range
macOS hands out, 49152-65535 (CI's macOS cells).

THE FILES are derived by walking the checkout (files()): every regular file under tests/, fixtures included, and every
file named *.test.* or under a directory named fixtures anywhere else, outside node_modules, dist, out, site, venv,
__pycache__ and every hidden directory (.git; .claude, where a clone may keep worktrees of other commits; .venv). A
symlink is skipped (its target is read where it lives). A file that is not UTF-8 text is skipped, and the census fails
if the walk finds no files, no Python file with a number in the range, no product function to resolve a call against,
or no module under tests/ that a read module imports, so it never passes on nothing. A file is read only when it holds a
five-digit number in the range (digit separators allowed: 45_001), or, for Python, one of the computed forms below (a
modulus by a constant of four or five digits, or a call to randint, randrange or randbelow); a port computed from
smaller constants alone (30000 + 5000) is not read.

THE RULE. A number in the range counts when it is WRITTEN AS A PORT, in one of these positions.
  In Python, read by AST (scan_python):
    a value under a dict key that names a port ({"port": N}, {"local_port": N}, {"busPort": N}; a key names a port when
    one of its words, split at underscores, other punctuation and camelCase, is "port" or "ports": "report" does not);
    a keyword argument that names a port (bus_port=N, ROMP_POSTAL_PORT="N");
    an assignment to a target that names a port (PORT = N, km.BUS_PORT = N, os.environ["ROMP_POSTAL_PORT"] = "N"), a
    tuple target read element by element against a tuple value of its length;
    the default of a parameter that names a port (def _notify(self, host, up, port=N));
    a positional argument whose parameter names a port, in the function the callee resolves to: a function the module
    defines (code text included, below); else, for a name the module imports from a module under tests/ (from helpers
    import dial, or import helpers and then helpers.dial; tests.helpers and a star import alike), that module's
    function (HelperModules); else, a name such a module only re-exports included, one of kernel/, postal/ or cli/ by
    name (km._notify_bus_peer("h", N, True)); a first parameter named self or cls is skipped; a *ports parameter takes
    every extra argument;
    an element of the sequence a for loop or a comprehension walks, under a target that names a port (for host, port in
    (("h", N),): the element at the port's index);
    the second argument of a call whose first argument is a string that names a port (os.environ.setdefault(
    "ROMP_POSTAL_PORT", "N"), monkeypatch.setenv);
    the port of an address tuple whose first element is a HOST: a loopback or wildcard literal ("127.0.0.1",
    "localhost", "0.0.0.0", "::1", "::" or ""), or a name the module binds only to such literals, the empty one aside
    (HOST = "127.0.0.1"): ("127.0.0.1", N), (HOST, N);
    the positional argument right after a host in a call, the empty string aside (http.client.HTTPConnection(
    "127.0.0.1", N, timeout=30), asyncio.open_connection(HOST, N));
    an operand formatted into an address, by %, by an f-string or by str.format, whose template (a literal; for % and
    format, also a name bound to one literal) puts a loopback or wildcard host, or // and any host, a placeholder for
    the host included, then a colon right before the operand ("http://127.0.0.1:%d/" % N, "http://%s:%d/" % (h, N),
    f"http://127.0.0.1:{P}/", f"ws://{h}:{P}/", "http://127.0.0.1:{}/".format(N)); for %, the port's placeholder is
    %d, %i or %s, and the whole right operand is read, each element of a tuple;
    a port concatenated onto an address: the right operand of a + whose left side (string literals, names bound to one,
    f-strings, and sums of them) ends in a loopback or wildcard host, or // and any host, then a colon
    ("http://127.0.0.1:" + str(N), "http://" + host + ":" + P);
    an element of a list or tuple display right after a string element that spells a --*port option whole (an argv:
    ["romp", "serve", "--port", "N"], ("--bus-port", N));
    and one hop through a name: a value written in one of those positions as a bare name counts the literals the module
    binds that name to (P = N ... {"port": P}).
  An int counts (45_001 is 45001), and so does a string of the number's five digits, except as a positional argument
  (by its parameter or after a host): a string handed to a function by position is that function's input text, not a
  setting (km._notify_bus_peer("h", "N", True) is not counted, where km._notify_bus_peer("h", N, True) is).
  An expression counts when it is bounded and can reach the range: interval() reads constants, + - * // and % over
  them, an unknown operand of % by a constant as 0 to the constant less one, and a call to randint(a, b), randrange(stop),
  randrange(start, stop[, step]) or randbelow(n) (random's and secrets', by the callee's name) as the values it can
  return, so 20000 + os.getpid() % 20000 is 20000-39999 and counts, and so does random.randint(40000, 50000). A sum or
  difference with an unbounded operand counts when one of its constant operands alone is in the range: 40000 + i is
  built on 40000 (offset_base()); one with no such operand (base + i) is not read.
  In any file, read as text (text_hits): a non-Python file whole; in Python, each string literal that is not a
  docstring, each bytes literal, and the code of code text (below). A number there may carry digit separators (45_001),
  and after a name and = or : it may open a shell arithmetic expansion ($((40000 + RANDOM % 1000)) reads as 40000):
    key   a port-named key or name after a delimiter ({ , ( [ ;) or at a line's start, then : or = and the number
          ({ port: N }, "busPort": N, , port=N);
    decl  a port-named name declared and assigned (const port = N, local port=N, export ROMP_POSTAL_PORT=N);
    env   an upper-case port-named name, then : or = and the number, quoted or not (ROMP_POSTAL_PORT'] = 'N');
    flag  a --*port option (--port N, --port=N), or one quoted in a list with the number as the next element
          ('--port', 'N');
    authority  host:N after a loopback or wildcard host or after // in a URL (http://127.0.0.1:N, //TESTHOST:N), the
               number right after the colon or concatenated onto it ('http://127.0.0.1:' + N);
    address    a loopback or wildcard address tuple in text (("127.0.0.1", N));
    call  a number handed first to .listen(, .connect(, createConnection( or .bind(;
    pair  a port-named string and the number handed together ("ROMP_POSTAL_PORT", "N").
  Code text in a Python string, one that parses as Python (a probe a test runs with python -c, a planted module), is
  read both ways, whether or not anything runs it, since the census cannot tell a probe that runs from one that is only
  parsed: by the Python rules, and by the text rules over its code with its comments and string literals blanked out
  (code_text_tokens(); the whole text when the tokenizer refuses it). Each string literal inside it is read in its own
  right, as here, so a comment or a docstring inside code text stays out as it does in a module. A short string can parse as code without being any: "localhost:N" is an annotation to the parser, and the
  authority rule reads it. A hit inside a string literal is reported on the source line that writes the number.

THE EXCLUDED CLASS, a stated predicate rather than a list: a number in the range written anywhere else is not read, and
stays. That is prose, a comment and a docstring (in code text too); a log, error or ps line a test hands to a parser
(the ssh errors of tests/test_tunnel_stale_and_logging.py, the ps lines of tests/test_kernel_tunnels.py, whose
-L 50512:127.0.0.1:29855 puts the number before the host); a string handed by position to a parser; an assertion's
expected value (it follows the setting it checks, so the setting is what counts); an id, a size, a byte offset, a
timeout and a duration. Not every place left unread is inert: the shapes below can dial or bind, and are not read.

WHAT IT CANNOT SEE (stated, not closed; test_the_stated_blind_spots_stay_unread plants each one green, so closing one
is a change to this list):
  a port that reaches its place through a name the module does not bind to a literal (a parameter, a container, a
  call's result, a name another module binds), through more than one hop (B = A), or by a run-time substitution into
  code text (a template's __VALUE__ replaced at run time);
  a port that is the result of a call other than the random calls above (random.choice((N, M)));
  an unbounded computed port with no constant operand of a sum or difference in the range (base + i, N * k);
  a host that is neither a loopback or wildcard literal nor a name bound only to such literals (("TESTHOST", N),
  HTTPConnection(self.host, N)), so the port beside it is read only when another rule reads it;
  a positional port handed to a function no index holds (one the standard library or a module outside tests/, kernel/,
  postal/ and cli/ defines, or a tests/ helper the module does not import) with no host right before it;
  in a file read as text, a positional port beyond the call rule (nc -l 127.0.0.1 N, python3 -m http.server N,
  startServer(N)), and a port reached through a name that does not name a port (const P = N, then :${P});
  a %-template whose port's placeholder carries a mapping key, a flag or a width ("http://127.0.0.1:%(p)d/" % {"p": N},
  "http://127.0.0.1:%5d/" % N), unless another rule reads the operand (a port-named key does);
  a format template, or the left side of a concatenation, that the module does not write as a literal or a name
  bound to one (a parameter, a call's result: t % N, base_url() + str(N));
  an option and its number that are not neighbours in one list or tuple display (["--port"] + [N], a flag built at run
  time), and a short option (-p N), in Python and in text;
  a value under a key spelled other than as a word (a computed key, {K: N});
  code text that does not parse on its own (an indented fragment, a %-template), which the text rules read instead, so
  its positional ports are not resolved;
  a file outside THE FILES (a support file such as ui/test-dom-shim.ts, a lab tool under tools/).
Each planted shape below is red, with the rule it names among the rules that read it, and each excluded shape is green.

THE SENTINELS (SentinelPorts; the ruling of round 1 on fork PR 966, (b)). tests/test_hermetic_kernel_postal.py's children
read back values a test wrote to a port name (ROMP_POSTAL_PORT, ROMP_KERNEL_PORT, BUS_PORT), and
tests/test_postal_fixed_port_belt.py names a hermetic bus's own port, which the belt lets the bus bind. Those values are
7, 8 and 9: below 1024, where on Linux at the default an unprivileged bind is refused, and in no band a test binds. The
pin reads, in those two modules, every number written as text a process could take for a port (sentinel_values(): a
quoted digit string, since the environment holds strings; a number after a loopback host and a colon; an int assigned
to a port-named name, BUS_PORT = N), and fails on any that falls in a bind band.
THE BIND BANDS are derived from THE FILES (bind_bands()):
  the ephemeral range, LOW-HIGH (a bind to port 0, tests/lab_ports.py's reserve());
  each per-test base of a shell file, a port-named name set to B plus ${BATS_TEST_NUMBER} in an arithmetic expansion
  (tests/romp-postal.bats): B to B plus the file's count of tests, moved by every constant the file adds to that name
  in an arithmetic expansion (the squat test's), and by every retry step a helper adds to a port-named name (port +
  try * S, inside a function: S times each try below the most its callers ask for);
  each draw from randint(a, b) with a at or above 1024: a call in Python, or the text in a shell file (the probe of
  tests/free-port.bash);
  each block keyed by a test file's name, 'name.test.js': [lo, hi] (tests/manager-ports.js).
The machine's own fixed ports (the postal bus's, the kernel's, the manager's) are not among them: no test binds them,
and the two modules write them on purpose, to show the belt and the licences refusing them. A band made any other way
is not read.

Synthetic: reads the tree only; no socket, no kernel, no subprocess.
"""
import ast
import io
import os
import re
import shutil
import string
import sys
import tempfile
import tokenize
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import parse_cache                                  # noqa: E402  one parse per file per process, shared with the other AST censuses

LOW, HIGH = 32768, 65535
LOOPBACK = frozenset({"127.0.0.1", "localhost", "0.0.0.0", "::1", "::", ""})
SKIP_DIRS = frozenset({"node_modules", "dist", "out", "site", "venv", "__pycache__"})   # and every hidden directory
PRODUCT_DIRS = ("kernel", "postal", "cli")
_D5 = r"\d(?:_?\d){4}"                              # five digits, digit separators allowed (45_001)
FIVE = re.compile(r"(?<![\w.])(" + _D5 + r")(?![\w.])")   # a five-digit number standing alone (not inside an id, a decimal or a hash)
WORDS = re.compile(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|\d+")
COMPUTED = re.compile(r"%[ \t]*\d{4,5}\b|\brand(?:int|range|below)\(")   # the computed forms interval() bounds
RANDOM_CALLS = ("randint", "randrange", "randbelow")
MAX_CODE_DEPTH = 3                                  # code text inside code text inside code text, and no deeper


def in_range(v):
    return isinstance(v, int) and not isinstance(v, bool) and LOW <= v <= HIGH


def _num(s):
    return int(s.replace("_", ""))


def names_a_port(name):
    """True when one of the words of `name` (split at punctuation and camelCase) is port or ports."""
    if not isinstance(name, str):
        return False
    return any(w.lower() in ("port", "ports") for part in re.split(r"[^A-Za-z0-9]+", name) for w in WORDS.findall(part))


def _digits(v):
    """The number a string of exactly five digits spells (digit separators allowed), else None."""
    if isinstance(v, str) and re.fullmatch(_D5, v.strip()):
        return _num(v.strip())
    return None


# The text rules.
_NUM = r"[\"'`]?(?:\$\(\([ \t]*)?(?P<n>" + _D5 + r")(?![\w.])"
_HOST = r"(?:\b(?:127\.0\.0\.1|localhost|0\.0\.0\.0)\b|\[::1?\])"
TEXT_RULES = (
    ("key", re.compile(r"(?:^|[{,(\[;])[ \t]*[\"'`]?(?P<name>[\w$.-]+)[\"'`]?[ \t]*[:=][ \t]*" + _NUM, re.M)),
    ("decl", re.compile(r"\b(?:const|let|var|local|export|readonly|declare(?:[ \t]+-\w+)?)[ \t]+(?P<name>[\w$]+)[ \t]*=[ \t]*" + _NUM)),
    ("env", re.compile(r"\b(?P<name>[A-Z][A-Z0-9_]*)[\"'`]?\]?[ \t]*[:=][ \t]*" + _NUM)),
    ("flag", re.compile(r"--(?P<name>[\w-]+)(?:=|[ \t]+|[\"'`][ \t]*,[ \t]*)" + _NUM)),   # or quoted, the number the next element
    ("authority", re.compile(r"(?:" + _HOST + r"|//[\w.-]+)[ \t]*:[ \t]*(?:[\"'`][ \t]*\+[ \t]*[\"'`]?)?(?P<n>" + _D5
                             + r")(?![\w.])")),   # the number right after the colon, or concatenated onto it
    ("address", re.compile(r"\([ \t]*[\"'](?:127\.0\.0\.1|localhost|0\.0\.0\.0|::1?|)[\"'][ \t]*,[ \t]*(?P<n>" + _D5 + r")[ \t]*[,)]")),
    ("call", re.compile(r"(?:\.listen|\.connect|createConnection|\.bind)\([ \t]*(?P<n>" + _D5 + r")(?![\w.])")),
    ("pair", re.compile(r"\([ \t]*[\"'`](?P<name>[\w$.-]+)[\"'`][ \t]*,[ \t]*" + _NUM)),
)
_NAMED = frozenset({"key", "decl", "env", "flag", "pair"})   # the rules whose match carries a name that must name a port
_ADDR_END = re.compile(r"(?:" + _HOST + r"|//[\w.\x00-]+)[ \t]*:[ \t]*$")   # a template's address up to the port's colon (\x00: a formatted host)
_ADDR_PCT = re.compile(r"(?:" + _HOST + r"|//(?:[\w.-]|%s)+):%[dis]")   # a host after // may be a %s placeholder
_BLANKED = frozenset([tokenize.COMMENT, tokenize.STRING] + [getattr(tokenize, t) for t in (
    "FSTRING_START", "FSTRING_MIDDLE", "FSTRING_END", "TSTRING_START", "TSTRING_MIDDLE", "TSTRING_END") if hasattr(tokenize, t)])


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
            v = _num(m.group("n"))
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


def code_text_tokens(src):
    """`src`, a code text, with its comments and string literals blanked out (every character but a newline made a space,
    so each place keeps its line), for the text rules; `src` whole when the tokenizer refuses it."""
    starts, at = [], 0                              # the tokenizer's rows are readline()'s lines, split at newlines only
    for line in src.split("\n"):
        starts.append(at)
        at += len(line) + 1
    out = list(src)
    try:
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type in _BLANKED:
                a = starts[tok.start[0] - 1] + tok.start[1]
                b = starts[tok.end[0] - 1] + tok.end[1]
                for i in range(a, min(b, len(out))):
                    if out[i] != "\n":
                        out[i] = " "
    except (tokenize.TokenError, SyntaxError, IndexError, ValueError):
        return src
    return "".join(out)


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


class HelperModules:
    """The functions a module under `root`/tests/ defines, by the dotted name a test imports it under (helpers and
    tests.helpers are tests/helpers.py; served.helpers is tests/served/helpers.py); None for a name that is no module
    there. `resolved` holds every module found, for the census's not-empty pin."""

    def __init__(self, root):
        self.base = os.path.join(root, "tests")
        self.memo, self.resolved = {}, set()

    def __call__(self, dotted):
        if dotted not in self.memo:
            parts = dotted.split(".")
            if parts[0] == "tests":
                parts = parts[1:]
            p = (os.path.join(self.base, *parts) + ".py") if parts and all(parts) else None
            defs = None
            if p is not None and os.path.isfile(p):
                defs = defs_of(parse_cache.source_and_tree(p)[1])
                self.resolved.add(p)
            self.memo[dotted] = defs
        return self.memo[dotted]


def _no_helpers(_dotted):
    return None


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


def _port_flag(node):
    """The --*port option a string literal spells whole (--port, --bus-port), else None."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        m = re.fullmatch(r"--([\w-]+)", node.value)
        if m and names_a_port(m.group(1)):
            return node.value
    return None


def _callee(f):
    return f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else None)


def interval(node, bound=None):
    """(lo, hi, computed) for an int expression the census can bound, else None: constants, + - * // and % over them, a
    name bound to one int literal, str() or int() around one, an unknown operand of % by a positive constant read as
    0 to the constant less one, and randint(a, b), randrange(stop), randrange(start, stop[, step]) and randbelow(n)
    over bounded arguments read as the values each can return. computed is True when an unknown took part."""
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
    if isinstance(node, ast.Call) and _callee(node.func) in RANDOM_CALLS and node.args \
            and not any(isinstance(a, ast.Starred) for a in node.args):
        ivs = [interval(a, bound) for a in node.args]
        name, k = _callee(node.func), len(ivs)
        if all(ivs):
            if name == "randint" and k == 2:
                return ivs[0][0], ivs[1][1], True
            if name in ("randrange", "randbelow") and k == 1:
                return 0, ivs[0][1] - 1, True
            if name == "randrange" and k in (2, 3):
                return ivs[0][0], ivs[1][1] - 1, True
        return None
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


def offset_base(node, bound=None):
    """The constant in the range that a sum or difference with an unbounded operand is built on (40000 + i: 40000), read
    through str() and int() and down a chain of sums and differences; None when no constant operand alone is in the
    range."""
    if isinstance(node, ast.Call) and _callee(node.func) in ("str", "int") and len(node.args) == 1 and not node.keywords:
        return offset_base(node.args[0], bound)
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub)):
        for side in (node.left, node.right):
            iv = interval(side, bound)
            if iv and not iv[2] and in_range(iv[0]):
                return iv[0]
            got = offset_base(side, bound)
            if got is not None:
                return got
    return None


class _Scan:
    """One module's (or one code text's) Python reading; hits are (line, number, why)."""

    def __init__(self, own, product, line_of, depth, src=None, helpers=None):
        self.own, self.product, self.line_of, self.depth, self.src = own, product, line_of, depth, src
        self.helpers = helpers or _no_helpers
        self.inherited = ({}, {})                   # the imports of the module a code text sits in
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

    def _imports(self, tree):
        """The functions of tests/ modules the module imports: {local name: defs} and {module alias: {name: defs}}."""
        imported, modules = dict(self.inherited[0]), dict(self.inherited[1])
        for n in ast.walk(tree):
            if isinstance(n, ast.ImportFrom) and n.module and not n.level:
                for a in n.names:
                    if a.name == "*":
                        imported.update(self.helpers(n.module) or {})
                        continue
                    sub = self.helpers(n.module + "." + a.name)
                    if sub is not None:
                        modules[a.asname or a.name] = sub
                        continue
                    defs = self.helpers(n.module)
                    if defs is not None and a.name in defs:
                        imported[a.asname or a.name] = defs[a.name]
            elif isinstance(n, ast.Import):
                for a in n.names:
                    if a.asname or "." not in a.name:
                        defs = self.helpers(a.name)
                        if defs is not None:
                            modules[a.asname or a.name] = defs
        return imported, modules

    def _resolve(self, f):
        """The (parameters, *args) of every function the callee `f` resolves to: the module's own, a tests/ module's it
        imports, else (a name such a module only re-exports too) the product's by name."""
        if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id in self.modules \
                and f.attr in self.modules[f.value.id]:
            return self.modules[f.value.id][f.attr]
        name = _callee(f)
        if name is None:
            return ()
        if name in self.own:
            return self.own[name]
        if isinstance(f, ast.Name) and name in self.imported:
            return self.imported[name]
        return self.product.get(name, ())

    def _host(self, node):
        """The loopback or wildcard host `node` writes: such a literal, or a name the module binds only to non-empty such
        literals; else None."""
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value in LOOPBACK:
            return node.value
        if isinstance(node, ast.Name):
            lits = self.bound.get(node.id, ())
            if lits and all(isinstance(x, ast.Constant) and isinstance(x.value, str) and x.value and x.value in LOOPBACK
                            for x in lits):
                return lits[0].value
        return None

    def _template(self, node):
        """The text of a format template: a string literal, or a name the module binds to exactly one."""
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.Name):
            lits = self.bound.get(node.id, ())
            if len(lits) == 1 and isinstance(lits[0], ast.Constant) and isinstance(lits[0].value, str):
                return lits[0].value
        return None

    def _rendered(self, node):
        """The text a string expression renders, each piece the census cannot read standing as \x00: a string literal, a
        name the module binds to exactly one, an f-string's literal parts, and a sum (+) of them, walked without
        recursion so a long chain of sums costs no stack."""
        out, stack = [], [node]
        while stack:
            x = stack.pop()
            if isinstance(x, ast.BinOp) and isinstance(x.op, ast.Add):
                stack.extend((x.right, x.left))
            elif isinstance(x, ast.JoinedStr):
                out.extend(p.value if isinstance(p, ast.Constant) and isinstance(p.value, str) else "\x00" for p in x.values)
            else:
                t = self._template(x)
                out.append("\x00" if t is None else t)
        return "".join(out)

    def _formatted(self, tmpl, args, keywords):
        """Each operand str.format places right after an address's colon in the template `tmpl`."""
        try:
            fields = list(string.Formatter().parse(tmpl))
        except ValueError:
            return
        rendered, auto = "", 0
        for lit, field, _spec, _conv in fields:
            rendered += lit
            if field is None:
                continue
            head = re.match(r"[^.\[]*", field).group(0)
            if head == "":
                arg, auto = (args[auto] if auto < len(args) else None), auto + 1
            elif head.isdigit():
                arg = args[int(head)] if int(head) < len(args) else None
            else:
                arg = keywords.get(head)
            if arg is not None and head == field and not isinstance(arg, ast.Starred) and _ADDR_END.search(rendered):
                self._value(arg, "an operand formatted into an address")
            rendered += "\x00"

    def _record(self, node, v, why):
        self.hits.append((self.line_of(node), v, why))

    def literal(self, node, why, strings=True):
        """The numbers `node` writes as a port: an int constant, a five-digit string (when `strings`), each element of a
        tuple, list or set display of them, a bounded expression that can reach the range, or a sum or difference built
        on a constant in the range."""
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
            elif iv is None:
                base = offset_base(node, self.bound)
                if base is not None:
                    self._record(node, base, "%s, an offset from %d" % (why, base))

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
        self.imported, self.modules = self._imports(tree)
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
                for params, star in self._resolve(n.func):
                    for i, a in enumerate(n.args):
                        p = params[i] if i < len(params) else star
                        if names_a_port(p) and not isinstance(a, ast.Starred):
                            self._value(a, "the argument %s of %s()" % (p, name), strings=False)
                for i in range(len(n.args) - 1):
                    h = self._host(n.args[i])
                    if h and not isinstance(n.args[i + 1], ast.Starred):        # the empty string is a host in a tuple only
                        self._value(n.args[i + 1], "the argument after the host %r" % h, strings=False)
                if isinstance(n.func, ast.Attribute) and n.func.attr == "format":
                    tmpl = self._template(n.func.value)
                    if tmpl is not None:
                        self._formatted(tmpl, n.args, {k.arg: k.value for k in n.keywords if k.arg})
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
                h = self._host(n.elts[0])
                if h is not None:
                    self._value(n.elts[1], "the port of the address (%r, ...)" % h, strings=False)
                for i in range(len(n.elts) - 1):
                    flag = _port_flag(n.elts[i])
                    if flag and not isinstance(n.elts[i + 1], ast.Starred):
                        self._value(n.elts[i + 1], "the argument after the flag %s" % flag)
            elif isinstance(n, ast.BinOp) and isinstance(n.op, ast.Mod):
                tmpl = self._template(n.left)
                if tmpl is not None and _ADDR_PCT.search(tmpl):
                    self._value(n.right, "an operand formatted into an address")
            elif isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add):
                if _ADDR_END.search(self._rendered(n.left)):
                    self._value(n.right, "a port concatenated onto an address")
            elif isinstance(n, ast.JoinedStr):
                rendered = ""
                for piece in n.values:
                    if isinstance(piece, ast.FormattedValue):
                        if _ADDR_END.search(rendered):
                            self._value(piece.value, "an operand formatted into an address")
                        rendered += "\x00"
                    elif isinstance(piece, ast.Constant) and isinstance(piece.value, str):
                        rendered += piece.value
            if isinstance(n, ast.Constant) and isinstance(n.value, (str, bytes)) and id(n) not in docs:
                s = n.value if isinstance(n.value, str) else n.value.decode("latin-1")
                if FIVE.search(s):
                    self._string(n, s, code=isinstance(n.value, str))
        for name, why, strings in self.uses:
            for lit in self.bound.get(name, ()):
                self.literal(lit, "%s, through the name %s" % (why, name), strings)

    def _string(self, n, s, code=True):
        """A string literal's reading: code text both ways (the Python rules and the text rules over its code), any other
        string, and a bytes literal, by the text rules."""
        first, last = self.line_of(n), self.line_of(n, end=True)
        sub = None
        if code and self.depth < MAX_CODE_DEPTH:
            try:
                sub = ast.parse(s)
            except (SyntaxError, ValueError, RecursionError, MemoryError):
                sub = None
        if sub is not None and sub.body:
            total = s.count("\n")

            def line_of(x, end=False, first=first, last=last, total=total):
                return _line_in(first, last, total - (getattr(x, "end_lineno" if end else "lineno", 1) - 1))
            inner = _Scan(defs_of(sub, dict(self.own)), self.product, line_of, self.depth + 1, self.src, self.helpers)
            inner.inherited = (self.imported, self.modules)
            inner.scan(sub)
            found = inner.hits + text_hits(code_text_tokens(s), first, last)
            self.hits.extend((self._place(ln, v, first, last), v, "in code text, " + why) for ln, v, why in found)
        else:
            self.hits.extend((self._place(ln, v, first, last), v, why) for ln, v, why in text_hits(s, first, last))


def scan_python(tree, product, text=None, helpers=None):
    """[(line, number, why)], sorted and one per (line, number), for a parsed module; `text`, the module's source, places a
    hit inside a string literal on the physical line that writes it; `helpers`, a HelperModules, resolves what the module
    imports from tests/."""
    def line_of(x, end=False):
        return getattr(x, "end_lineno" if end else "lineno", 1) or 1
    sc = _Scan(defs_of(tree), product, line_of, 0, text.split("\n") if text is not None else None, helpers)
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
    elsewhere, outside SKIP_DIRS and every hidden directory (.git; .claude, where a clone may keep worktrees of other
    commits; .venv); symlinks skipped."""
    out = []
    for d, dirs, names in os.walk(root):
        dirs[:] = sorted(x for x in dirs if x not in SKIP_DIRS and not x.startswith("."))
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
    """{"hits": [(path relative to root, line, number, why)], "files": n, "python_read": n, "product_defs": n,
    "helper_modules": n}."""
    product = product_defs(root)
    helpers = HelperModules(root)
    hits, n_files, n_py = [], 0, 0
    for p in files(root):
        n_files += 1
        rel = os.path.relpath(p, root)
        try:
            with open(p, encoding="utf-8") as fh:
                text = fh.read()
        except (UnicodeDecodeError, OSError):
            continue
        if not any(in_range(_num(m.group(1))) for m in FIVE.finditer(text)) and not (p.endswith(".py") and COMPUTED.search(text)):
            continue
        if p.endswith(".py"):
            n_py += 1
            found = scan_python(parse_cache.source_and_tree(p)[1], product, text, helpers)
        else:
            found = _one_per_place(text_hits(text))
        hits += [(rel, line, v, why) for line, v, why in found]
    return {"hits": hits, "files": n_files, "python_read": n_py, "product_defs": len(product),
            "helper_modules": len(helpers.resolved)}


def render(hits):
    return "\n".join("  %s:%d: %d, %s" % h for h in hits)


# The sentinels and the bind bands (THE SENTINELS, in the docstring).
SENTINEL_MODULES = (os.path.join("tests", "test_hermetic_kernel_postal.py"), os.path.join("tests", "test_postal_fixed_port_belt.py"))
PRIVILEGED = 1024                                   # below this, on Linux at the default, an unprivileged bind is refused
SHELL_FILES = (".bats", ".bash", ".sh")
_PER_TEST = re.compile(r"\b(?P<name>\w+)=\$\(\([ \t]*(?P<base>\d+)[ \t]*\+[ \t]*\$\{?BATS_TEST_NUMBER\b")
_SHELL_ADD = re.compile(r"\$\(\([ \t]*\$?(?P<v>\w+)[ \t]*\+[ \t]*(?:(?P<k>\w+)[ \t]*\*[ \t]*)?(?P<c>\d+)[ \t]*\)\)")
_SHELL_FN = re.compile(r"^[ \t]*(?:function[ \t]+)?(\w+)[ \t]*\(\)[ \t]*\{", re.M)
_DRAW_TEXT = re.compile(r"\brandint\([ \t]*(\d+)[ \t]*,[ \t]*(\d+)[ \t]*\)")
_BLOCK = re.compile(r"""["'][\w.-]+\.test\.[cm]?[jt]s["'][ \t]*:[ \t]*\[[ \t]*(\d+)[ \t]*,[ \t]*(\d+)[ \t]*\]""")
_QUOTED_DIGITS = re.compile(r"""(["'])(\d{1,5})\\?\1""")
_AFTER_HOST = re.compile(r"(?:" + _HOST + r"):(\d{1,5})(?![\d.])")
_PORT_INT = re.compile(r"\b(?P<name>\w+)[ \t]*=[ \t]*(?P<n>\d{1,5})(?![\w.])")


def _shell_bands(text):
    """[(lo, hi)]: the ports each per-test base of the shell file `text` makes, with its offsets and retry steps."""
    out = []
    tests = len(re.findall(r"^[ \t]*@test\b", text, re.M))
    for m in _PER_TEST.finditer(text):
        name, base = m.group("name"), int(m.group("base"))
        if not names_a_port(name):
            continue
        offsets, steps = {0}, {0}
        for a in _SHELL_ADD.finditer(text):
            if not names_a_port(a.group("v")):
                continue
            c = int(a.group("c"))
            if a.group("k") is None:
                if a.group("v") == name:
                    offsets.add(c)
                continue
            fns = list(_SHELL_FN.finditer(text, 0, a.start()))
            if fns:
                helper = re.escape(fns[-1].group(1))
                tries = [int(t) for t in re.findall(r"\b" + helper + r"[ \t]+(?:\"[^\"\n]*\"|\S+)[ \t]+(\d+)\b", text)]
                steps |= {c * i for i in range(max(tries, default=1))}
        out += [(base + o + st, base + tests + o + st) for o in sorted(offsets) for st in sorted(steps)]
    return out


def _python_draws(tree):
    """[(a, b)]: every call to randint(a, b) in `tree` whose arguments are int literals."""
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and _callee(n.func) == "randint" and len(n.args) == 2 and not n.keywords \
                and all(isinstance(a, ast.Constant) and type(a.value) is int for a in n.args):
            out.append((n.args[0].value, n.args[1].value))
    return out


def bind_bands(root):
    """[(lo, hi, where)]: every band of ports a test binds, derived from THE FILES under `root` (THE BIND BANDS)."""
    out = [(LOW, HIGH, "the ephemeral range")]
    for p in files(root):
        rel = os.path.relpath(p, root)
        try:
            with open(p, encoding="utf-8") as fh:
                text = fh.read()
        except (UnicodeDecodeError, OSError):
            continue
        draws = []
        if p.endswith(SHELL_FILES):
            out += [(lo, hi, "%s: a per-test base" % rel) for lo, hi in _shell_bands(text)]
            draws = [(int(a), int(b)) for a, b in _DRAW_TEXT.findall(text)]
        elif p.endswith(".py") and "randint(" in text:
            draws = _python_draws(parse_cache.source_and_tree(p)[1])
        out += [(a, b, "%s: a draw" % rel) for a, b in draws if a >= PRIVILEGED]
        if p.endswith((".js", ".mjs", ".cjs", ".ts")):
            out += [(int(a), int(b), "%s: a block" % rel) for a, b in _BLOCK.findall(text)]
    return out


def sentinel_values(text):
    """[(line, number, why)]: every number the module `text` writes as text a process could take for a port."""
    out = []
    for rx, group, why in ((_QUOTED_DIGITS, 2, "a quoted digit string"), (_AFTER_HOST, 1, "a number after a loopback host"),
                           (_PORT_INT, "n", "an int assigned to a port-named name")):
        for m in rx.finditer(text):
            if group == "n" and not names_a_port(m.group("name")):
                continue
            out.append((text.count("\n", 0, m.start()) + 1, int(m.group(group)), why))
    return out


def sentinel_faults(root, bands, modules=SENTINEL_MODULES):
    """[(module, line, number, why, band's where, lo, hi)]: each number the `modules` write as a port that a band holds."""
    out = []
    for rel in modules:
        with open(os.path.join(root, rel), encoding="utf-8") as fh:
            text = fh.read()
        for line, v, why in sentinel_values(text):
            out += [(rel, line, v, why, where, lo, hi) for lo, hi, where in bands if lo <= v <= hi]
    return out


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
        self.assertGreater(self.result["helper_modules"], 5, "the tests/ modules the read modules import were indexed")
        self.assertIn(os.path.join(ROOT, "tests", "test_postal_token.py"), files(ROOT))
        self.assertIn(os.path.join(ROOT, "tests", "fixtures"), {os.path.dirname(p) for p in files(ROOT)})


def _n(k=0):
    """A number in the range, built at run time so this file holds none in a port position: LOW + 12233 + k."""
    return LOW + 12233 + k


def _sep(v):
    """`v` written with a digit separator (45_001)."""
    return "%d_%03d" % (v // 1000, v % 1000)


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

    def _write(self, rel, text):
        """`text` at `rel` under the scratch root, by a rename-over: the file takes a new inode, so tests/parse_cache.py,
        which serves the old tree for a same-size rewrite within one tick of a coarse clock, parses each plant afresh."""
        p = os.path.join(self.d, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p + ".new", "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(p + ".new", p)

    def _hits(self, name, text):
        """The census's hits in the planted file `name` (written fresh under the scratch root's tests/; the root and every
        plant in it go with the test's cleanup)."""
        self._write(os.path.join("tests", name), text)
        return [h for h in census(self.d)["hits"] if h[0] == os.path.join("tests", name)]

    def _whys(self, name, text):
        """Every reason the rules give for the plant, before the census keeps one per place (two rules can read one place,
        a shell export is both a declaration and an upper-case name)."""
        if not name.endswith(".py"):
            return [w for _l, _v, w in text_hits(text)]
        tree = ast.parse(text)
        sc = _Scan(defs_of(tree), product_defs(self.d), lambda x, end=False: getattr(x, "lineno", 1), 0,
                   helpers=HelperModules(self.d))
        sc.scan(tree)
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
                ("digit separators", 'ps.peer_update({"host": "TESTHOST", "port": %s, "up": True})\n' % _sep(n), "key 'port'"),
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
                ("address with a host from a name", 'HOST = "127.0.0.1"\ns.connect((HOST, %d))\n' % n, "address ('127.0.0.1'"),
                ("a call's argument after a host", 'conn = http.client.HTTPConnection("127.0.0.1", %d, timeout=30)\n' % n,
                 "argument after the host '127.0.0.1'"),
                ("a call's argument after a host from a name",
                 'HOST = "localhost"\n\n\nasync def f():\n    r, w = await asyncio.open_connection(HOST, %d)\n' % n,
                 "argument after the host 'localhost'"),
                ("formatted address", 'u = "http://127.0.0.1:%%d/peer" %% %d\n' % n, "formatted into an address"),
                ("formatted address, the template from a name", 'URL = "http://127.0.0.1:%%d/peer"\nurlopen(URL %% %d)\n' % n,
                 "formatted into an address"),
                ("formatted address with a placeholder host", 'u = "http://%%s:%%d/x" %% (h, %d)\n' % n, "formatted into an address"),
                ("formatted address with a placeholder host from an attribute, %s for the port",
                 'u = "ws://%%s:%%s/ws" %% (self.host, %d)\n' % n, "formatted into an address"),
                ("formatted address, %i for the port", 'u = "http://localhost:%%i/x" %% %d\n' % n, "formatted into an address"),
                ("a port concatenated onto an address", 'u = "http://127.0.0.1:" + str(%d) + "/peer"\n' % n,
                 "concatenated onto an address"),
                ("a port concatenated onto an address whose host is a name", 'u = "http://" + host + ":" + "%d"\n' % n,
                 "concatenated onto an address"),
                ("a port concatenated onto an f-string's address", 'P = %d\nu = f"ws://{h}:" + str(P)\n' % n,
                 "concatenated onto an address, a constant expression"),
                ("an argv list", 'subprocess.run(["romp", "serve", "--port", "%d"])\n' % n, "argument after the flag --port"),
                ("an argv tuple, the number an int", 'ARGS = ("--bus-port", %d)\n' % n, "argument after the flag --bus-port"),
                ("f-string address", 'P = %d\nurllib.request.urlopen(f"http://127.0.0.1:{P}/peer")\n' % n,
                 "formatted into an address, through the name P"),
                ("f-string address with a formatted host", 'h = "x"\nu = f"ws://{h}:{%d}/ws"\n' % n, "formatted into an address"),
                ("str.format address", 'urllib.request.urlopen("http://127.0.0.1:{}/peer".format(%d))\n' % n,
                 "formatted into an address"),
                ("str.format address by field name", 'u = "http://localhost:{p}/x".format(p=%d)\n' % n,
                 "formatted into an address"),
                ("one hop", 'P = %d\nps.peer_update({"host": "h", "port": P})\n' % n, "through the name P"),
                ("code text", 'subprocess.run([sys.executable, "-c", %r])\n' % ('bus.peer_update({"host": "h", "port": %d, "up": True})' % n),
                 "in code text"),
                ("text rule in a string", 'JS = "await fetch(\\"http://127.0.0.1:%d/x\\")"\n' % n, "text rule authority"),
                ("a string that parses as code, read by a text rule", 'conn = http.client.HTTPConnection("localhost:%d", timeout=30)\n' % n,
                 "in code text, text rule authority"),
                ("a Host header", 'h = {"Host": "localhost:%d"}\n' % n, "in code text, text rule authority"),
                ("a key in a one-line string", 'CFG = "port: %d"\n' % n, "in code text, text rule key"),
                ("a bytes literal", 's.sendall(b"GET / HTTP/1.1\\r\\nHost: 127.0.0.1:%d\\r\\n\\r\\n")\n' % n, "text rule authority")):
            with self.subTest(label):
                self.assertRed("test_plant.py", src, why)

    def test_a_helper_another_tests_module_defines(self):
        n = _n()
        self._write(os.path.join("tests", "plant_helpers.py"),
                    "from kernel.k import _notify_bus_peer                # a re-export\n\n\ndef dial(host, port, wait=30):\n    pass\n")
        for label, src, *why in (
                ("from-import", 'from plant_helpers import dial\ndial("TESTHOST", %d)\n' % n),
                ("from-import under another name", 'from plant_helpers import dial as d\nd("TESTHOST", %d)\n' % n, "argument port of d()"),
                ("star import", 'from plant_helpers import *\ndial("TESTHOST", %d)\n' % n),
                ("module import", 'import plant_helpers\nplant_helpers.dial("TESTHOST", %d)\n' % n),
                ("module import under another name", 'import plant_helpers as ph\nph.dial("TESTHOST", %d)\n' % n),
                ("the module from the tests package", 'from tests import plant_helpers\nplant_helpers.dial("TESTHOST", %d)\n' % n),
                ("the function from the tests package's module", 'from tests.plant_helpers import dial\ndial("TESTHOST", %d)\n' % n),
                ("the import's code text", 'import plant_helpers\nsubprocess.run([sys.executable, "-c", %r])\n'
                 % ('plant_helpers.dial("TESTHOST", %d)' % n)),
                ("a name the module only re-exports, by name in the product", 'import plant_helpers\n'
                 'plant_helpers._notify_bus_peer("TESTHOST", %d, True)\n' % n, "argument port of _notify_bus_peer()")):
            with self.subTest(label):
                self.assertRed("test_plant.py", src, why[0] if why else "argument port of dial()")
        self.assertGreen("test_x.py", 'dial("TESTHOST", %d)\n' % n)             # not imported: no index holds dial

    def test_a_computed_port_that_can_reach_the_range(self):
        shape = 'env = dict(ROMP_POSTAL_PORT=str(%d + os.getpid() %% %d))\n'      # written as a template, so this file holds no such code
        hits = self._hits("test_plant.py", shape % (20000, 20000))
        self.assertEqual(len(hits), 1, hits)
        self.assertIn("computed into 20000-39999", hits[0][3])
        self.assertGreen("test_plant.py", shape % (20000, 10000))
        self.assertGreen("test_plant.py", 'env = dict(ROMP_POSTAL_PORT=str(base + i))\n')
        lo, hi = LOW + 7232, LOW + 17232                                           # 40000 and 50000, built at run time
        for label, src, why, first in (
                ("randint", 'port = random.randint(%d, %d)\n' % (lo, hi), "computed into %d-%d" % (lo, hi), lo),
                ("randrange from a base", 'port = %d + random.randrange(1000)\n' % lo, "computed into %d-%d" % (lo, lo + 999), lo),
                ("randrange with a start and a step", 'env = dict(ROMP_POSTAL_PORT=str(random.randrange(%d, %d, 2)))\n' % (lo, hi),
                 "computed into %d-%d" % (lo, hi - 1), lo),
                ("randbelow", 'port = %d + secrets.randbelow(100)\n' % lo, "computed into %d-%d" % (lo, lo + 99), lo),
                ("a randrange from a base below the range, no five-digit number in it", 'port = %d + random.randrange(%d)\n'
                 % (lo - 8000, 9000), "computed into %d-%d" % (lo - 8000, lo + 999), LOW),
                ("a sum built on a constant in the range", 'for i in range(3):\n    port = %d + i\n' % lo, "an offset from %d" % lo, lo),
                ("a sum built on a name bound to one", 'BASE = %d\nsrv.bind(("127.0.0.1", BASE + worker))\n' % lo,
                 "an offset from %d" % lo, lo)):
            with self.subTest(label):
                self.assertRed("test_plant.py", src, why, n=first)
        self.assertGreen("test_plant.py", 'port = random.randint(1, 6)\n')

    def test_the_text_rules(self):
        n = _n()
        for label, name, src, why in (
                ("JS key", "a.test.mjs", "const srv = { host: '127.0.0.1', port: %d };\n" % n, "rule key"),
                ("JSON key", "x.json", '{\n  "busPort": %d\n}\n' % n, "rule key"),
                ("JS declaration", "a.test.ts", "const proxyPort = %d;\n" % n, "rule decl"),
                ("JS digit separators", "b.test.ts", "const proxyPort = %s;\n" % _sep(n), "rule decl"),
                ("shell env", "a.bats", "export ROMP_POSTAL_PORT=%d\n" % n, "rule env"),
                ("shell arithmetic", "h.bats", "export ROMP_POSTAL_PORT=$((%d + RANDOM %% 1000))\n" % n, "rule env"),
                ("shell local", "b.bats", "    local port=%d\n" % n, "rule decl"),
                ("flag", "c.bats", "run romp serve --port %d\n" % n, "rule flag"),
                ("URL", "d.test.mjs", "await fetch('http://localhost:%d/healthz');\n" % n, "rule authority"),
                ("a port concatenated onto a URL", "d2.test.mjs", "await fetch('http://127.0.0.1:' + %d + '/x');\n" % n,
                 "rule authority"),
                ("a flag and its number as list elements", "c2.test.mjs", "spawn(bin, ['serve', '--port', '%d']);\n" % n,
                 "rule flag"),
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
                ("a string by position after a host", "test_x.py", 'self.assertEqual(split_line("127.0.0.1", "%d"), 1)\n' % n),
                ("an expected value", "test_x.py", 'self.assertEqual((snap["port"], snap["up"]), (%d, True))\n' % n),
                ("a timeout", "test_x.py", 'page.goto(url, timeout=%d)\n' % n),
                ("a word that only contains port", "test_x.py", 'row = {"report": %d, "transport": %d}\n' % (n, n)),
                ("an argv element after an option that does not name a port", "test_x.py",
                 'subprocess.run(["x", "--report", "%d"])\n' % n),
                ("an id", "test_x.py", 'MID = "1700000001.%d_44444.TESTHOST"\n' % n),
                ("an empty string before a number in a call", "test_x.py", 'row = make_row("id", "", %d)\n' % n),
                ("a comment inside code text", "test_x.py", 'subprocess.run([sys.executable, "-c", "x = 1  # was {port: %d}"])\n' % n),
                ("a docstring inside code text", "test_x.py", 'PROBE = "def f():\\n    \\"\\"\\"{port: %d}\\"\\"\\"\\n"\n' % n),
                ("JS timeout", "g.test.ts", "await page.waitForSelector('#x', { timeout: %d });\n" % n),
                ("JS prose", "h.test.ts", "// the bus port: %d was the old default\n" % n),
                ("bats size", "i.bats", '[[ "$output" == *"dom %d"* ]]\n' % n)):
            with self.subTest(label):
                self.assertGreen(name, src)

    def test_a_digit_string_by_position_to_a_port_named_parameter_is_not_counted(self):
        """The excluded class's string by position, where the resolver does find a port-named parameter: each call below
        resolves in the scratch index (kernel/k.py, or the module's own function), as its int form, red, shows, and the
        same call with the number as a digit string is green."""
        n = _n()
        for label, call in (("a product function", 'km._notify_bus_peer("TESTHOST", %s, True)\n'),
                            ("a product method", 'r.ring(%s)\n'),
                            ("the module's own function", 'def rec(port, pid=None):\n    pass\n\n\nrec(%s)\n')):
            with self.subTest(label):
                self.assertRed("test_plant.py", call % n, "argument port of")
                self.assertGreen("test_x.py", call % ('"%d"' % n))

    def test_the_stated_blind_spots_stay_unread(self):
        """Each shape WHAT IT CANNOT SEE names, planted green: a change that reads one turns its subtest red, and the
        docstring's list moves with it."""
        n = _n()
        self._write(os.path.join("tests", "plant_helpers.py"), "P = %d\n\n\ndef dial(host, port):\n    pass\n" % n)
        for label, name, src in (
                ("a parameter", "test_x.py", 'def go(p):\n    return {"port": p}\n\n\ngo(%d)\n' % n),
                ("a container", "test_x.py", 'CFG = {"a": %d}\nrow = {"port": CFG["a"]}\n' % n),
                ("a call's result", "test_x.py", 'def pick():\n    return %d\n\n\nrow = {"port": pick()}\n' % n),
                ("a name another module binds", "test_x.py", 'from plant_helpers import P\nrow = {"port": P}\n'),
                ("two hops", "test_x.py", 'A = %d\nB = A\nrow = {"port": B}\n' % n),
                ("a run-time substitution into code text", "test_x.py",
                 'PROBE = "bus.peer_update({\'port\': __VALUE__})"\n'
                 'subprocess.run([sys.executable, "-c", PROBE.replace("__VALUE__", "%d")])\n' % n),
                ("a call other than the random calls", "test_x.py", 'port = random.choice((%d, %d))\n' % (n, n + 1)),
                ("an unbounded computed port with no constant of a sum in the range", "test_x.py",
                 'port = base + i\nother_port = %d * k\n' % n),
                ("a host that is no loopback or wildcard literal", "test_x.py",
                 's.connect(("TESTHOST", %d))\nconn = HTTPConnection(self.host, %d)\n' % (n, n)),
                ("a function no index holds, no host before it", "test_x.py", 'import vendorlib\nvendorlib.serve(%d)\n' % n),
                ("a tests/ helper the module does not import", "test_x.py", 'dial("TESTHOST", %d)\n' % n),
                ("a positional port in shell", "x.bats",
                 "    nc -l 127.0.0.1 %d &\n    python3 -m http.server %d --bind 127.0.0.1 &\n" % (n, n)),
                ("a positional port in JavaScript", "x.test.mjs", "const srv = startServer(%d);\n" % n),
                ("a JavaScript name that does not name a port", "y.test.ts",
                 "const P = %d;\nawait fetch(`http://127.0.0.1:${P}/x`);\n" % n),
                ("a %-template placeholder with a mapping key or a width", "test_x.py",
                 'u = "http://127.0.0.1:%%(p)d/x" %% {"p": %d}\nv = "http://127.0.0.1:%%5d/x" %% %d\n' % (n, n)),
                ("a template or an address that is no literal", "test_x.py",
                 'def go(t, base):\n    return t %% %d, base + str(%d)\n' % (n, n)),
                ("an option and its number apart, or a short option", "test_x.py",
                 'subprocess.run(["romp", "--port"] + ["%d"])\nsubprocess.run(["romp", "-p", "%d"])\n' % (n, n)),
                ("a short option in shell", "z.bats", "    romp serve -p %d\n" % n),
                ("a computed key", "test_x.py", 'K = "port"\nrow = {K: %d}\n' % n),
                ("code text that does not parse", "test_x.py", 'FRAG = "    km._notify_bus_peer(\'h\', %d, True)"\n' % n)):
            with self.subTest(label):
                self.assertGreen(name, src)
        with self.subTest("a file outside the walk"):
            self._write(os.path.join("ui", "test-dom-shim.ts"), "export const PORT = %d;\n" % n)
            self.assertEqual([h for h in census(self.d)["hits"] if not h[0].startswith("tests" + os.sep)], [])
            self.assertRed("y.test.ts", "export const PORT = %d;\n" % n, "rule decl")

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

    def test_the_walk_skips_hidden_and_build_directories(self):
        n = _n()
        for d in (".claude/worktrees/old/tools", "vscode-extension/node_modules/pkg", "site/assets", "venv/lib"):
            os.makedirs(os.path.join(self.d, d), exist_ok=True)
            with open(os.path.join(self.d, d, "x.test.js"), "w", encoding="utf-8") as f:
                f.write("server.listen(%d);\n" % n)
        self.assertEqual([h for h in census(self.d)["hits"] if h[0].endswith("x.test.js")], [])
        self.assertRed("y.test.js", "server.listen(%d);\n" % n, "rule call")

    def test_the_range_ends_are_32768_and_65535(self):
        """The ends, with values built apart from LOW and HIGH so a change to either constant shows: 2**15 and 2**16 - 1
        are read, 2**15 - 1 is not, and neither is 2**16, which no port can be."""
        for v in (2 ** 15, 2 ** 16 - 1):
            with self.subTest(v):
                self.assertRed("test_plant.py", 'row = {"local_port": %d}\n' % v, "key 'local_port'", n=v)
        for v in (2 ** 15 - 1, 2 ** 16):
            with self.subTest(v):
                self.assertGreen("test_x.py", 'row = {"local_port": %d}\n' % v)

    def test_the_plural_ports_names_a_port(self):
        """ports is a port word as port is: a ports key, and a *ports parameter taking the extra arguments."""
        n = _n()
        for label, src, why in (
                ("a ports key", 'row = {"ports": [%d, 1]}\n' % n, "key 'ports'"),
                ("a *ports parameter", 'def listen_all(host, *ports):\n    pass\n\n\nlisten_all("TESTHOST", %d)\n' % n,
                 "argument ports of listen_all()")):
            with self.subTest(label):
                self.assertRed("test_plant.py", src, why)


class SentinelPorts(unittest.TestCase):
    """THE SENTINELS: no number tests/test_hermetic_kernel_postal.py or tests/test_postal_fixed_port_belt.py writes as text
    a process could take for a port falls in a bind band, and every kind of band is found in the tree."""

    @classmethod
    def setUpClass(cls):
        cls.bands = parse_cache.derived("ephemeral_port_bind_bands", lambda: bind_bands(ROOT))

    def test_no_sentinel_falls_in_a_bind_band(self):
        faults = sentinel_faults(ROOT, self.bands)
        if faults:
            self.fail("%d number(s) written as a port by the sentinel modules fall in a band a test binds, so a bus that "
                      "reads one could bind inside another suite's band. Use a port below 1024 that no band holds (7, 8 and 9 "
                      "are the sentinels); this module's docstring, THE SENTINELS, says how the bands are derived:\n%s"
                      % (len(faults), "\n".join("  %s:%d: %d, %s, inside %s (%d-%d)" % f for f in faults)))

    def test_every_kind_of_band_and_each_sentinel_module_is_found(self):
        kinds = {where for _lo, _hi, where in self.bands}
        for where in ("the ephemeral range", os.path.join("tests", "romp-postal.bats") + ": a per-test base",
                      os.path.join("tests", "free-port.bash") + ": a draw", os.path.join("tests", "manager-ports.js") + ": a block"):
            self.assertIn(where, kinds, "a band of this kind is derived from the tree")
        for rel in SENTINEL_MODULES:
            with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
                values = {v for _l, v, _w in sentinel_values(fh.read())}
            self.assertTrue(values - {0, 1}, "%s writes numbers the pin reads, beyond the floors' 0 and 1" % rel)


class SentinelPlants(unittest.TestCase):
    """Each band shape THE BIND BANDS names is read from a planted file, and each way sentinel_values() reads a number is
    red inside a band and green below 1024."""
    B, STEP, OFFSET = 26000, 100, 300             # a planted per-test base, a helper's retry step, a test's offset

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.d, True)
        os.makedirs(os.path.join(self.d, "tests"))

    def _write(self, rel, text):
        """`text` at `rel` under the scratch root, by a rename-over (Plants._write says why)."""
        p = os.path.join(self.d, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p + ".new", "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(p + ".new", p)

    def _shell(self):
        """A bats file whose two tests each take B plus their number, through a helper that retries STEP higher as many
        times as its callers ask (twice), and one of whose tests offsets the port by OFFSET and spawns there."""
        return ('setup() {\n'
                '    export ROMP_POSTAL_PORT=$((%d + ${BATS_TEST_NUMBER:-0}))\n'
                '    spawn "$ROMP_POSTAL_PORT" 2\n'
                '}\n\n'
                'spawn() {\n'
                '    local port=$1 tries=${2:-1} try=0\n'
                '    export ROMP_POSTAL_PORT=$((port + try * %d))\n'
                '}\n\n'
                '@test "a" {\n'
                '    local squat=$((ROMP_POSTAL_PORT + %d))\n'
                '    spawn "$squat" 2\n'
                '}\n\n'
                '@test "b" {\n'
                '    :\n'
                '}\n') % (self.B, self.STEP, self.OFFSET)

    def _bands(self):
        return sorted((lo, hi) for lo, hi, where in bind_bands(self.d) if where != "the ephemeral range")

    def test_each_band_shape_is_read(self):
        b, s, o = self.B, self.STEP, self.OFFSET
        draw = "random.randint(%d, %d)"                                   # a template, so this file holds no such call
        cases = (
            ("a per-test base with its offset and its retry steps", "romp-x.bats", self._shell(),
             [(b + x + y, b + 2 + x + y) for x in (0, o) for y in (0, s)]),
            ("a draw in a shell file", "free-x.bash", "p = %s\nq = %s\n" % (draw % (b - 5000, b - 4001), draw % (0, 99)),
             [(b - 5000, b - 4001)]),
            ("a draw in Python, a call and not a string", "helper_x.py",
             "import random\nP = %s\nDOC = %r\n" % (draw % (b - 4000, b - 3901), draw % (b - 3000, b - 2901)), [(b - 4000, b - 3901)]),
            ("a block keyed by a test file's name", "ports-x.js", "const RANGES = {\n  'a.test.js': [%d, %d],\n};\n" % (b - 13000, b - 12489),
             [(b - 13000, b - 12489)]))
        for label, name, text, want in cases:
            with self.subTest(label):
                self._write(os.path.join("tests", name), text)
                got = self._bands()
                os.unlink(os.path.join(self.d, "tests", name))              # before the assertion, so a red case leaves no plant
                self.assertEqual(got, sorted(want), text)

    def test_a_sentinel_inside_a_band_is_red_and_one_below_1024_green(self):
        self._write(os.path.join("tests", "romp-x.bats"), self._shell())
        inside, above = self.B + 1, self.B + 3                            # a test's port; one past the last test's
        for rel in SENTINEL_MODULES:
            for label, tmpl, why in (
                    ("a quoted digit string", 'os.environ["ROMP_POSTAL_PORT"] = "%d"\n', "a quoted digit string"),
                    ("an escaped one inside code text", 'SRC = "os.environ[\\"ROMP_POSTAL_PORT\\"] = \\"%d\\""\n',
                     "a quoted digit string"),
                    ("a number after a loopback host", 'URL = "http://127.0.0.1:%d/v1/models"\n', "a number after a loopback host"),
                    ("an int assigned to a port-named name", '_km.BUS_PORT = %d\n', "an int assigned to a port-named name")):
                with self.subTest(rel=rel, shape=label):
                    self._write(rel, tmpl % inside)
                    faults = sentinel_faults(self.d, bind_bands(self.d), (rel,))
                    self.assertEqual([(f[2], f[3]) for f in faults], [(inside, why)], tmpl)
                    for v in (7, above):
                        self._write(rel, tmpl % v)
                        self.assertEqual(sentinel_faults(self.d, bind_bands(self.d), (rel,)), [], tmpl % v)


if __name__ == "__main__":
    unittest.main()
