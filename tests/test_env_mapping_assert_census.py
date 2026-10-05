#!/usr/bin/env python3
"""No test assertion renders a mapping of environment values (2026-10-05).

WHY. A failing assertion renders its operands. assertNotIn(name, env) prints the whole container, assertEqual(env, want)
prints both mappings and their diff, and pytest explains a bare assert by printing every operand. When the mapping is a
copy of the process environment (a child's environment captured by a stubbed spawn, a dict(os.environ, ...) built for a
subprocess, os.environ itself), the failure writes every variable the shell exported into the report, and on a developer
machine that environment holds live API keys. On 2026-10-02 that pattern, in a test of an upstream offer, wrote a
session's keys into a build log. tests/README.md states the rule ("No test report shows a process-environment value"):
test membership and name the key. tests/conftest.py's report hook is the net for an assertion still written the other
way, and it covers pytest only: a plain unittest run, an upstream checkout without the hook, or a value under 16
characters prints in the clear. This census is the rule's enforcement, read by AST over the test tree.

THE POPULATION is derived, never listed: every tests/*.py (conftest.py and the helper modules included), each parsed
through tests/parse_cache.py. A test tree with no tests/*.py fails the run, and so does one in which the census finds
none of the environment copies it claims to watch (each binding form below, counted in the real tree), or no
environment mapping read at an assertion site at all (the safe reads the fixed tree keeps: a .get(name) and a
`name in mapping`), so the census never passes on nothing.

THE RULE. No assertion renders an environment mapping (THE MAPPINGS, below). Read per call by AST (scan()):
  A  a unittest assertion method renders the arguments its failure message prints: assertIn and assertNotIn (the
     container and the member), assertEqual and every equality form (assertDictEqual, assertCountEqual,
     assertListEqual, assertTupleEqual, assertSequenceEqual, assertSetEqual, assertMultiLineEqual,
     assertDictContainsSubset, assertNotEqual, the deprecated aliases) on both operands, assertIs and assertIsNot,
     assertIsNone, assertFalse, assertIsInstance and assertNotIsInstance on the object, the ordering and almost-equal
     forms on both, and every method's message (the msg argument, positional or keyword). RENDERS lists the positions
     per method. assertTrue and assertIsNotNone render only their message: assertTrue prints its argument only when it
     is falsy, and a falsy mapping is empty; assertIsNotNone prints "unexpectedly None". assertRaises and its relatives
     render their message keyword alone. Any other method whose name begins with `assert` (a helper a module defines)
     is read as rendering every argument it is handed.
  F  fail and skipTest render their message (pytest.fail's reason included).
  B  a bare assert renders every environment mapping anywhere in its test or its message: pytest's rewrite explains a
     call by printing its arguments and an attribute by printing its receiver, so even `assert env.get(n) is None`
     prints the mapping, as the receiver of the bound method it explains.
An argument renders a mapping when it IS one, or holds one where the failure prints it: an element of a tuple, list,
set or dict display, a value formatted into a string (an operand of % or +, an f-string's field, an argument of str,
repr, ascii, format, pformat, dumps or a .format() call), the value a slice is taken of (repr(env)[:80] prints part of
the mapping), a join's argument when it yields values (M.values(), or a comprehension over M.items() or M.values():
", ".join("%s=%s" % kv for kv in env.items())), either branch of a conditional or an operand of and/or.
What a failure prints of a mapping it only READS is safe and never flagged: a .get(name) or a [name] read prints the one
value, `name in mapping` inside assertTrue or assertFalse prints a bool, and sorted(), set(), list(), tuple() or len()
of a mapping, or of its keys(), print its names, as a join over the mapping itself does (iterating a mapping yields its
keys). So the fix for each site is:
  assertNotIn(name, env, msg)  ->  assertFalse(name in env, msg)   (absent stays absent; the message names the variable
  assertIn(name, env, msg)     ->  assertTrue(name in env, msg)     when the original had none)
  assertEqual(env, want, msg)  ->  assertTrue(env == want, msg)    (the same equality; the message says what differs)
  assertIsNone(env, msg)       ->  assertTrue(env is None, msg)
assertIsNone(env.get(name)) is not offered for the absent case: it prints the value when the variable is present, which
for a credential name is the credential.

THE MAPPINGS, read by is_env():
  os.environ itself, by any spelling of the os module (`import os as o`: o.environ) or a name `from os import environ`
  binds;
  an attribute or a string-keyed subscript whose name ends in the word env or environ, lower case (self.env,
  s._launched_env, kw["env"], seen["env"], spec["env"], json.loads(text)["env"]), and X.get("env") in either arity;
  a name an assignment binds to any of these forms, in the scope Python reads the name from (the function, the
  functions around it, then the module; a class body is skipped, as Python skips it; a parameter, a for target or
  an import binds an unknown value): `=`, an annotated `=`, `:=`, an augmented assignment, a tuple or list target
  element by element, and `with ... as name` (bound to the context expression, so mock.patch.dict(os.environ) as e
  counts);
  an attribute name or a string key a module assigns an environment mapping to anywhere in the module
  (self.saved = dict(os.environ) makes every .saved read in that module one, seen["child"] = env every ["child"]);
  a copy or view of a mapping: dict(M, ...), dict(**M), copy.copy, copy.deepcopy, OrderedDict, ChainMap and
  MappingProxyType of M, M.copy(), M.items(), M.values(), {**M, ...}, M | other and other | M, a dict comprehension
  over M or its items, any comprehension over M.items() or M.values(), and sorted, list, tuple or set of M.items() or
  M.values(); and M.keys(), on the safe side: os.environ's keys view renders as the whole environ, values included (a
  KeysView's repr is its mapping's), while a dict copy's renders names only, and the census cannot tell os.environ from
  a copy through a capture or a binding, so it reads every keys() of an environment mapping as one (sorted(M) prints
  names either way);
  the result of a call whose callee RETURNS an environment mapping, derived and never listed by name: a return
  statement of the callee whose value is one of these forms (jd._judge_env(...) returns the judge child's
  environment, built from os.environ). A callee resolves by its name: to the module's own functions of that name, else
  to the functions of that name in the tests/ modules the module imports, else, for a name that is an env word, to the
  functions of that name in the top-level .py files of kernel/, postal/ and cli/ (the product is read only by those
  names: resolving every product callee by name alone cost seconds and matched unrelated functions). A function named
  like an environment (set_env, which returns a bool) is not one unless it returns one.
THE BINDING FORMS. The census counts four copies of os.environ where a name is bound to one (READ_FORMS):
dict(os.environ, ...), os.environ.copy(), {**os.environ, ...} and os.environ.items() (a binding of the view or a
comprehension over it). It claims to find three of them in the tree (BINDING_FORMS) and fails when the tree holds none
of one: drop the form from the claim, or read why the reader stopped seeing it. os.environ.copy() is read and planted
but not claimed: on 2026-10-05 the tree spells it only inside other censuses' planted strings.

EXEMPT names a site the rule should not hold, one entry per site, keyed by (file, the enclosing function's qualified
name, the assertion's source text with whitespace collapsed), with its reason; an entry that matches no offence is
stale and fails the census, so the list cannot outlive the sites it excuses. Two identical assertions in one function
share an entry. EXEMPT is EMPTY today: every site found was fixed.

WHAT IT CANNOT SEE (stated, not closed). Three of these shapes held real sites on 2026-10-05, each fixed by hand:
  a loop variable bound from captured pairs: `for cmd, env in seen:` over the (cmd, env) pairs a stubbed spawn
  recorded, then assertNotIn(name, env), which prints the child's whole environment (tests/test_credentials.py,
  JudgesRunOnClaudeCodesOwnCredential.test_the_first_pass_after_boot_runs_keyless_and_latches_nothing; now
  assertFalse(name in env, name)). A for target binds an unknown value, so the census reads no mapping there;
  mock's assert_called* family (assert_not_called, assert_called_once, assert_called_with and the rest): a failure
  prints every call the mock recorded with its arguments, so a mock patched over a spawn prints the env= keyword the
  product handed it, and the assertion's own AST holds no mapping (tests/test_judge_auth_billing.py, run =
  patch.object(jd.subprocess, "run") in RuntimeJudgeBilling.test_exhausted_login_window_pauses_without_launching,
  RuntimeJudgeBilling.test_codex_call_never_resolves_or_carries_an_anthropic_credential and
  CredentialErrorNote.test_an_unexpected_env_failure_never_quotes_its_cause_and_never_falls_back_to_ambient_auth; now
  assertEqual(run.call_count, N, msg), which prints two counts);
  a mapping read back from what a child wrote: seen = json.loads(dump), where the child dumped dict(os.environ)
  (tests/test_login_records.py's whitelist test; now assertFalse(name in seen, name)).
The census also cannot see:
  a mapping reached through a parameter (a helper handed env by its caller), a list index (captured.append(env);
  captured[0]), getattr, or an attribute or key whose name is neither an env word nor assigned an environment mapping
  in the module (s.env_vars, a per-session overlay, is not read);
  a callee that resolves by a name the module does not define or import from tests/, a product function whose name is
  not an env word, a product module's own attribute and key bindings, or a callee that returns the mapping through
  another call's parameter (sb._bin_on_path_env(environ) returns a mapping of its argument's values and is not read);
  a view bound to a name and then iterated (pairs = env.items(); sorted(pairs), or ", ".join(vals) after vals =
  env.values()), a join whose comprehension reads the values through the keys (", ".join(k + "=" + env[k] for k in
  env)), and a formatted mapping passed through another call (repr(env).replace(...), map(str, env.values()));
  Python inside a string (a planted module a test writes and runs, whose bare assert over os.environ renders under
  that run's own conftest);
  a mapping printed by print(), logging, a raise or a subprocess's output a test asserts on;
  a mapping rendered by a message built before the call (msg = "%r" % env; self.assertTrue(ok, msg)).
PLANTS pins each shape it reads, red or green, and the stated limits a reader would most expect it to see (a parameter,
a list index, a message built beforehand, a mapping read back from a child's dump, a for target over captured pairs,
mock's assert_called* family, a view bound to a name, values read through the keys, a formatted mapping passed through
another call).

Synthetic: reads the tree only; no environment value is read or printed.
"""
import ast
import glob
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

PRODUCT_DIRS = ("kernel", "postal", "cli")
ENV_WORDS = ("env", "environ")

_PAIR = ((0, 1), ("first", "second"), 2)
_ORDER = ((0, 1), ("a", "b"), 2)
_ALMOST = ((0, 1), ("first", "second"), 3)
# method: (the positional indices its failure renders, the keyword names of those parameters, the message's positional
# index or None). The message keyword (msg) is read for every method.
RENDERS = {
    "assertEqual": _PAIR, "assertEquals": _PAIR, "failUnlessEqual": _PAIR,
    "assertNotEqual": _PAIR, "assertNotEquals": _PAIR, "failIfEqual": _PAIR,
    "assertMultiLineEqual": _PAIR, "assertCountEqual": _PAIR,
    "assertIn": ((0, 1), ("member", "container"), 2), "assertNotIn": ((0, 1), ("member", "container"), 2),
    "assertDictEqual": ((0, 1), ("d1", "d2"), 2), "assertListEqual": ((0, 1), ("list1", "list2"), 2),
    "assertTupleEqual": ((0, 1), ("tuple1", "tuple2"), 2), "assertSetEqual": ((0, 1), ("set1", "set2"), 2),
    "assertSequenceEqual": ((0, 1), ("seq1", "seq2"), 2),
    "assertDictContainsSubset": ((0, 1), ("subset", "dictionary"), 2),
    "assertIs": ((0, 1), ("expr1", "expr2"), 2), "assertIsNot": ((0, 1), ("expr1", "expr2"), 2),
    "assertIsNone": ((0,), ("obj",), 1), "assertIsNotNone": ((), (), 1),
    "assertTrue": ((), (), 1), "assert_": ((), (), 1), "failUnless": ((), (), 1),
    "assertFalse": ((0,), ("expr",), 1), "failIf": ((0,), ("expr",), 1),
    "assertIsInstance": ((0,), ("obj",), 2), "assertNotIsInstance": ((0,), ("obj",), 2),
    "assertGreater": _ORDER, "assertGreaterEqual": _ORDER, "assertLess": _ORDER, "assertLessEqual": _ORDER,
    "assertAlmostEqual": _ALMOST, "assertNotAlmostEqual": _ALMOST, "assertAlmostEquals": _ALMOST,
    "assertNotAlmostEquals": _ALMOST,
    "assertRegex": ((0,), ("text",), 2), "assertNotRegex": ((0,), ("text",), 2),
    "assertRegexpMatches": ((0,), ("text",), 2), "assertNotRegexpMatches": ((0,), ("text",), 2),
    "fail": ((0,), ("msg", "reason"), None), "skipTest": ((0,), ("reason",), None),
}
# render none of their arguments: the callable and its arguments are called, not printed
NON_RENDERING = ("assertRaises", "assertRaisesRegex", "assertRaisesRegexp", "assertWarns", "assertWarnsRegex",
                 "assertLogs", "assertNoLogs")
COPIERS = ("dict", "OrderedDict", "ChainMap", "MappingProxyType", "copy", "deepcopy")
SEQUENCES = ("sorted", "list", "tuple", "set", "frozenset")
FORMATTERS = ("str", "repr", "ascii", "format", "pformat", "dumps", "saferepr", "safe_repr")
VIEWS = ("items", "values")
# a keyed read whose key names the mapping hands the mapping over: X.get("env"), X.pop("env"), X.setdefault("env", {})
KEYED = ("get", "pop", "setdefault")
# a mapping's own methods return one value or None, never a mapping of values (copy, keys, items and values are read
# above); a callee of one of these names is never resolved by name
MAPPING_METHODS = ("get", "pop", "setdefault", "update", "popitem", "fromkeys", "clear", "__getitem__", "__contains__")
# the copies of os.environ the census counts where a name, an attribute or a key is bound to one
READ_FORMS = ("dict(os.environ, ...)", "os.environ.copy()", "{**os.environ, ...}", "os.environ.items()")
# the ones it claims to find in the tree, each at least once (os.environ.copy() is read and planted, but the tree binds
# none today: it spells it only inside other censuses' planted strings)
BINDING_FORMS = ("dict(os.environ, ...)", "{**os.environ, ...}", "os.environ.items()")
SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)
FUNCTIONS = (ast.FunctionDef, ast.AsyncFunctionDef)

# Sites the rule should not hold, one per entry: (file, enclosing function's qualified name, the assertion's source text
# with whitespace collapsed) -> the reason. EMPTY today: every site the census found was fixed (2026-10-05).
EXEMPT = {}

_ENV_MARK = object()      # the value a name bound by `from os import environ` holds
_LINE = re.compile(r"[^\r\n]*(?:\r\n|\r|\n)|[^\r\n]+\Z")   # a line with its ending, as the parser splits them (str.splitlines
#                                                         also breaks at a form feed and other separators the parser does not)


def env_word(name):
    """An identifier or a string key naming an environment mapping: lower case, and its last underscore-separated word is
    env or environ (env, _env, saved_env, environ). Upper case names an environment VARIABLE (ROMP_SERVICE_ENV) or a
    constant, never the mapping."""
    return isinstance(name, str) and name == name.lower() and name.split("_")[-1] in ENV_WORDS


def _pairs(target, value):
    """(name, value) for each Name a target binds: a tuple or list target against a tuple or list value of its length,
    nothing starred on either side, element by element; any other tuple or list target binds each element to an unknown
    value (None)."""
    if isinstance(target, (ast.Tuple, ast.List)):
        elts = target.elts
        if isinstance(value, (ast.Tuple, ast.List)) and len(value.elts) == len(elts) and \
                not any(isinstance(e, ast.Starred) for e in list(elts) + list(value.elts)):
            for t, v in zip(elts, value.elts):
                yield from _pairs(t, v)
        else:
            for t in elts:
                yield from _pairs(t, None)
    elif isinstance(target, ast.Starred):
        yield from _pairs(target.value, None)
    elif isinstance(target, ast.Name):
        yield target.id, value


def _callee(call):
    f = call.func
    return f.attr if isinstance(f, ast.Attribute) else f.id if isinstance(f, ast.Name) else None


def _str_const(node):
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _is_site(node):
    """An assertion call (an attribute call of a method in RENDERS or NON_RENDERING, or of any other name beginning with
    `assert` but not `assert_`, mock's own assertion methods) or a bare assert."""
    if isinstance(node, ast.Assert):
        return True
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        m = node.func.attr
        return m in RENDERS or m in NON_RENDERING or (m.startswith("assert") and not m.startswith("assert_"))
    return False


def _concrete(*bases):
    out, todo = set(), list(bases)
    while todo:
        b = todo.pop()
        out.add(b)
        todo.extend(b.__subclasses__())
    return out


# leaves and the parser's shared singletons, by exact type: nothing under them to read
_SKIP = frozenset(_concrete(ast.Constant, ast.expr_context, ast.operator, ast.boolop, ast.unaryop, ast.cmpop))
_BINDERS = (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.NamedExpr, ast.withitem, ast.For, ast.AsyncFor,
            ast.ExceptHandler, ast.Import, ast.ImportFrom, ast.Global, ast.Nonlocal)
_SCOPE_TYPES = frozenset(SCOPES)
# the node types is_env can answer yes for
_MAPPING_SHAPES = (ast.Name, ast.Attribute, ast.Subscript, ast.Call, ast.Dict, ast.BinOp, ast.BoolOp, ast.IfExp,
                   ast.NamedExpr, ast.DictComp, ast.ListComp, ast.SetComp, ast.GeneratorExp)
_BINDER_TYPES = frozenset(_BINDERS)


class _Scope:
    """One scope's bindings: name -> [value, or None for an unknown value, or _ENV_MARK]. Built from the binding nodes the
    module's walk filed under the scope; names declared global or nonlocal are read from outside."""

    def __init__(self, node, parent, binders):
        self.node, self.parent, self.binds = node, parent, {}
        outer = set()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            a = node.args
            for arg in a.posonlyargs + a.args + a.kwonlyargs + [x for x in (a.vararg, a.kwarg) if x]:
                self.binds.setdefault(arg.arg, []).append(None)
        for x in binders:
            if isinstance(x, ast.Assign):
                for t in x.targets:
                    self._bind(t, x.value)
            elif isinstance(x, (ast.AnnAssign, ast.AugAssign, ast.NamedExpr)):
                if x.value is not None:
                    self._bind(x.target, x.value)
            elif isinstance(x, ast.withitem):
                if x.optional_vars is not None:
                    self._bind(x.optional_vars, x.context_expr)
            elif isinstance(x, (ast.For, ast.AsyncFor)):
                self._bind(x.target, None)
            elif isinstance(x, ast.ExceptHandler):
                if x.name:
                    self.binds.setdefault(x.name, []).append(None)
            elif isinstance(x, SCOPES):
                if not isinstance(x, ast.Lambda):
                    self.binds.setdefault(x.name, []).append(None)
            elif isinstance(x, ast.Import):
                for al in x.names:
                    self.binds.setdefault((al.asname or al.name).split(".")[0], []).append(None)
            elif isinstance(x, ast.ImportFrom):
                for al in x.names:
                    mark = _ENV_MARK if (x.module == "os" and not x.level and al.name == "environ") else None
                    self.binds.setdefault(al.asname or al.name, []).append(mark)
            elif isinstance(x, (ast.Global, ast.Nonlocal)):
                outer.update(x.names)
        for name in outer:
            self.binds.pop(name, None)

    def _bind(self, target, value):
        for name, v in _pairs(target, value):
            self.binds.setdefault(name, []).append(v)


class _Module:
    """A parsed module and the census's side tables over it, from ONE walk of the tree (the cached tree is never written:
    parse_cache's contract). Each node is filed under the scope that owns it: a function, a lambda or a class owns its
    body; comprehensions belong to the scope around them."""

    def __init__(self, rel, text, tree):
        self.rel, self.text, self.tree = rel, text, tree
        self.parent = {id(tree): None}    # id(scope node) -> the enclosing scope node
        self.binders = {id(tree): []}     # id(scope node) -> the binding nodes it owns
        self.scope_nodes = [tree]
        self.functions = {}               # name -> [function nodes of that name, any depth]
        self.sites = []                   # (scope node, assertion call or bare assert)
        self.targets = []                 # (scope node, attribute or subscript target, the value assigned to it)
        self.values = []                  # (scope node, a value a name is bound to)
        self.imports = set()              # the last part of every module name an import names, and from-tests names
        queue = [tree]
        while queue:
            sn = queue.pop()
            binders = self.binders[id(sn)]
            stack = list(ast.iter_child_nodes(sn))
            while stack:
                n = stack.pop()
                t = type(n)
                if t in _SKIP:
                    continue
                if t in _SCOPE_TYPES:
                    binders.append(n)
                    self.parent[id(n)] = sn
                    self.binders[id(n)] = []
                    self.scope_nodes.append(n)
                    if t is not ast.Lambda and t is not ast.ClassDef:
                        self.functions.setdefault(n.name, []).append(n)
                    queue.append(n)
                    continue
                if t in _BINDER_TYPES:
                    binders.append(n)
                    if (t is ast.Assign or t is ast.AnnAssign or t is ast.AugAssign) and n.value is not None:
                        for tg in (n.targets if t is ast.Assign else [n.target]):
                            if isinstance(tg, ast.Attribute) or (isinstance(tg, ast.Subscript) and _str_const(tg.slice) is not None):
                                self.targets.append((sn, tg, n.value))
                        self.values.append((sn, n.value))
                    elif t is ast.NamedExpr:
                        self.values.append((sn, n.value))
                    elif t is ast.withitem and n.optional_vars is not None:
                        self.values.append((sn, n.context_expr))
                    elif t is ast.Import:
                        self.imports.update(a.name.split(".")[-1] for a in n.names)
                    elif t is ast.ImportFrom:
                        if n.module:
                            self.imports.add(n.module.split(".")[-1])
                        if n.module in (None, "tests"):
                            self.imports.update(a.name for a in n.names)
                elif (t is ast.Call or t is ast.Assert) and _is_site(n):
                    self.sites.append((sn, n))
                for field in n._fields:                 # ast.iter_child_nodes, inlined: the walk is most of the cost
                    v = getattr(n, field, None)
                    if type(v) is list:
                        stack.extend(x for x in v if isinstance(x, ast.AST))
                    elif isinstance(v, ast.AST):
                        stack.append(v)
        self._scopes = {}
        self._lines = None
        self.attrs, self.keys = set(), set()   # attribute names and string keys the module assigns a mapping to

    def scope(self, node):
        s = self._scopes.get(id(node))
        if s is None:
            up = self.parent[id(node)]
            s = self._scopes[id(node)] = _Scope(node, None if up is None else self.scope(up), self.binders[id(node)])
        return s

    def qualname(self, node):
        parts = []
        while node is not None and not isinstance(node, ast.Module):
            parts.append("<lambda>" if isinstance(node, ast.Lambda) else node.name)
            node = self.parent[id(node)]
        return ".".join(reversed(parts)) or "<module>"

    def segment(self, node):
        """The node's source text as the author wrote it, whitespace collapsed (never ast.unparse, whose spelling differs
        between interpreters), sliced from the module's lines split once (ast.get_source_segment splits per call)."""
        if self._lines is None:
            self._lines = _LINE.findall(self.text)
        try:
            lo, hi, c0, c1 = node.lineno - 1, node.end_lineno - 1, node.col_offset, node.end_col_offset
            if lo == hi:
                seg = self._lines[lo].encode()[c0:c1].decode()
            else:
                seg = "".join([self._lines[lo].encode()[c0:].decode()] + self._lines[lo + 1:hi]
                              + [self._lines[hi].encode()[:c1].decode()])
        except (AttributeError, TypeError, IndexError):
            return "<%s at line %s>" % (type(node).__name__, getattr(node, "lineno", "?"))
        return " ".join(seg.split())


class Reader:
    """is_env() and the derivation of the callees that return an environment mapping, over one tree's tests/ modules and
    product modules. Results are memoised per node and scope once the modules' attribute and key bindings have settled."""

    def __init__(self, root, test_modules, product_paths):
        self.root = root
        self.tests = test_modules                       # file name -> _Module
        self.product_paths = product_paths
        self._product = None
        self._returns = {}                              # (rel, id(fn)) -> bool (False while in progress)
        self._names = {}                                # (id(scope), name) -> bool (False while in progress)
        self._memo = {}                                 # (id(node), id(scope)) -> bool
        self._candidates = {}                           # (rel, name) -> [(module, function)]
        self.settled = False

    def forget(self):
        self._returns.clear()
        self._names.clear()
        self._memo.clear()

    def product(self):
        """name -> [(module, function)] over the product modules, for the callees whose name is an env word."""
        if self._product is None:
            self._product = {}
            for p in self.product_paths:
                text, tree = parse_cache.source_and_tree(p, os.path.relpath(p, self.root))
                m = _Module(os.path.relpath(p, self.root), text, tree)
                for name, fns in m.functions.items():
                    if env_word(name):
                        self._product.setdefault(name, []).extend((m, f) for f in fns)
        return self._product

    def candidates(self, module, name):
        """The functions a call of `name` in `module` may run: the module's own functions of that name; else those of the
        tests/ modules it imports; else, for a name that is an env word, the product's."""
        key = (module.rel, name)
        got = self._candidates.get(key)
        if got is None:
            got = [(module, f) for f in module.functions.get(name, ())]
            if not got:
                got = [(m, f) for imp in sorted(module.imports) for m in [self.tests.get(imp + ".py")]
                       if m is not None and m is not module for f in m.functions.get(name, ())]
            if not got and env_word(name):
                got = self.product().get(name, [])
            self._candidates[key] = got
        return got

    def returns_env(self, module, fn):
        key = (module.rel, id(fn))
        if key in self._returns:
            return self._returns[key]
        self._returns[key] = False                      # a recursive callee reads as not returning one while in progress
        scope = module.scope(fn)
        got = False
        stack = list(ast.iter_child_nodes(fn))
        while stack and not got:
            x = stack.pop()
            if isinstance(x, ast.Return) and x.value is not None and self.is_env(x.value, module, scope):
                got = True
            elif not isinstance(x, SCOPES):
                stack.extend(ast.iter_child_nodes(x))
        self._returns[key] = got
        return got

    def lookup(self, scope, name):
        """(the scope that binds `name` as Python reads it from `scope`, its values): the scope itself, then the scopes
        around it, a class body skipped unless it is where the read is."""
        s, first = scope, True
        while s is not None:
            if (first or not isinstance(s.node, ast.ClassDef)) and name in s.binds:
                return s, s.binds[name]
            first, s = False, s.parent
        return None, ()

    def is_env(self, node, module, scope):
        if node is None:
            return False
        if node is _ENV_MARK:
            return True
        key = (id(node), id(scope))
        if self.settled and key in self._memo:
            return self._memo[key]
        got = self._is_env(node, module, scope)
        if self.settled:
            self._memo[key] = got
        return got

    def _is_env(self, node, module, scope):
        if isinstance(node, ast.Attribute):
            return env_word(node.attr) or node.attr in module.attrs
        if isinstance(node, ast.Subscript):
            key = _str_const(node.slice)
            return key is not None and (env_word(key) or key in module.keys)
        if isinstance(node, ast.Name):
            s, values = self.lookup(scope, node.id)
            if s is None:
                return False
            mark = (id(s), node.id)
            if mark in self._names:
                return self._names[mark]
            self._names[mark] = False                   # a name bound through itself reads its other bindings
            got = any(self.is_env(v, module, s) for v in values)
            self._names[mark] = got
            return got
        if isinstance(node, ast.Call):
            return self._call_is_env(node, module, scope)
        if isinstance(node, ast.Dict):
            return any(k is None and self.is_env(v, module, scope) for k, v in zip(node.keys, node.values))
        if isinstance(node, (ast.DictComp, ast.ListComp, ast.SetComp, ast.GeneratorExp)):
            return any((isinstance(node, ast.DictComp) and self.is_env(g.iter, module, scope))
                       or self._view(g.iter, module, scope) for g in node.generators)
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            return self.is_env(node.left, module, scope) or self.is_env(node.right, module, scope)
        if isinstance(node, ast.BoolOp):
            return any(self.is_env(v, module, scope) for v in node.values)
        if isinstance(node, ast.IfExp):
            return self.is_env(node.body, module, scope) or self.is_env(node.orelse, module, scope)
        if isinstance(node, ast.NamedExpr):
            return self.is_env(node.value, module, scope)
        return False

    def _view(self, node, module, scope):
        """M.items() or M.values() of an environment mapping M: a view that carries the values."""
        return (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in VIEWS
                and not node.args and self.is_env(node.func.value, module, scope))

    def _call_is_env(self, node, module, scope):
        f, name = node.func, _callee(node)
        if isinstance(f, ast.Attribute):
            if f.attr in KEYED and node.args:
                key = _str_const(node.args[0])
                if key is not None and (env_word(key) or key in module.keys):
                    return True
            # keys() too: os.environ's keys view renders as the whole environ, values included (a KeysView's repr is its
            # mapping's), while a dict copy's renders names only; the census cannot tell the two apart through a capture
            # or a binding, so it reads every keys() of an environment mapping as one (sorted(M) prints names either way)
            if f.attr in ("copy", "keys") + VIEWS and not node.args:
                return self.is_env(f.value, module, scope)
            if f.attr in MAPPING_METHODS:
                return False                            # a mapping's own method: one value, its names, or None
        if name in COPIERS and (any(self.is_env(a, module, scope) for a in node.args)
                                or any(k.arg is None and self.is_env(k.value, module, scope) for k in node.keywords)):
            return True
        if name in SEQUENCES and node.args and self._view(node.args[0], module, scope):
            return True
        if name:
            return any(self.returns_env(m, fn) for m, fn in self.candidates(module, name))
        return False

    def rendered(self, node, module, scope):
        """The environment mappings a failure message prints when it prints `node` (the module docstring's list)."""
        if node is None:
            return []
        if isinstance(node, ast.Starred):
            node = node.value
        if self.is_env(node, module, scope):
            return [node]
        parts = []
        if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
            parts = node.elts
        elif isinstance(node, ast.Dict):
            parts = [e for e in list(node.keys) + list(node.values) if e is not None]
        elif isinstance(node, ast.JoinedStr):
            parts = [v.value for v in node.values if isinstance(v, ast.FormattedValue)]
        elif isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Mod, ast.Add)):
            parts = [node.left, node.right]
        elif isinstance(node, ast.Call) and _callee(node) in FORMATTERS:
            parts = list(node.args) + [k.value for k in node.keywords]
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "join":
            # a join prints the strings its iterable yields: M.values(), or a comprehension over M.items() or M.values(),
            # yields values; M itself yields its names, as sorted(M) does
            parts = [a for a in node.args if self._view(a, module, scope) or (
                isinstance(a, (ast.ListComp, ast.SetComp, ast.GeneratorExp)) and self.is_env(a, module, scope))]
        elif isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Slice):
            parts = [node.value]                        # a slice prints part of what it slices: repr(env)[:80]
        elif isinstance(node, ast.IfExp):
            parts = [node.body, node.orelse]
        elif isinstance(node, ast.BoolOp):
            parts = node.values
        return [r for p in parts for r in self.rendered(p, module, scope)]

    def anywhere(self, node, module, scope):
        """Every environment mapping anywhere in `node`, outermost first (a mapping's own parts are not walked): what
        pytest's explanation of a bare assert can print."""
        out, stack = [], [node]
        while stack:
            n = stack.pop()
            if isinstance(n, _MAPPING_SHAPES) and self.is_env(n, module, scope):
                out.append(n)
                continue
            if not isinstance(n, SCOPES):
                stack.extend(ast.iter_child_nodes(n))
        return out

    def reads(self, node, module, scope):
        """The environment mappings `node` READS where a failure prints only a value, a bool or names (the population
        count of the safe forms): the receiver of X.get(k) or another mapping method, the container of a [k] read, the
        right side of `in` and `not in`, the argument of len, sorted, set, list or tuple."""
        n_reads, stack = 0, [node]
        while stack:
            n = stack.pop()
            held = []
            if isinstance(n, ast.Compare):
                held = [c for op, c in zip(n.ops, n.comparators) if isinstance(op, (ast.In, ast.NotIn))]
            elif isinstance(n, ast.Subscript):
                held = [n.value]
            elif isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in MAPPING_METHODS:
                held = [n.func.value]
            elif isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in SEQUENCES + ("len",) and n.args:
                held = [n.args[0]]
            n_reads += sum(1 for h in held if self.is_env(h, module, scope))
            if not isinstance(n, SCOPES):
                stack.extend(ast.iter_child_nodes(n))
        return n_reads

    def settle(self, modules):
        """The attribute names and string keys each module assigns an environment mapping to, to a fixed point over every
        module (a callee in one module can read another's), then memoisation on."""
        self.settled = False
        pending = [(m, m.attrs if isinstance(t, ast.Attribute) else m.keys,
                    t.attr if isinstance(t, ast.Attribute) else _str_const(t.slice), v, sn)
                   for m in modules for sn, t, v in m.targets]
        changed = True
        while changed:
            changed = False
            for m, bucket, name, value, sn in pending:
                if name not in bucket and self.is_env(value, m, m.scope(sn)):
                    bucket.add(name)
                    changed = True
                    self.forget()                       # a callee or a name read before the set grew is read again
        self.forget()
        self.settled = True


def _is_os_environ(node, scope, reader):
    """os.environ by any spelling the census counts: the attribute environ on a name (os.environ, o.environ after
    `import os as o`), or a name `from os import environ` binds."""
    if isinstance(node, ast.Attribute) and node.attr == "environ" and isinstance(node.value, ast.Name):
        return True
    if isinstance(node, ast.Name):
        _, values = reader.lookup(scope, node.id)
        return any(v is _ENV_MARK for v in values)
    return False


def binding_form(value, scope, reader):
    """Which of the copies of os.environ the census counts `value` is (READ_FORMS), or None."""
    def osenv(n):
        return _is_os_environ(n, scope, reader)

    def items(n):
        return (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "items"
                and not n.args and osenv(n.func.value))
    if isinstance(value, ast.Call):
        if isinstance(value.func, ast.Name) and value.func.id == "dict" and (
                (value.args and (osenv(value.args[0]) or items(value.args[0])))
                or any(k.arg is None and osenv(k.value) for k in value.keywords)):
            return "dict(os.environ, ...)"
        if isinstance(value.func, ast.Attribute) and value.func.attr == "copy" and not value.args and osenv(value.func.value):
            return "os.environ.copy()"
        if items(value):
            return "os.environ.items()"
    if isinstance(value, ast.Dict) and any(k is None and osenv(v) for k, v in zip(value.keys, value.values)):
        return "{**os.environ, ...}"
    if isinstance(value, (ast.DictComp, ast.ListComp, ast.SetComp, ast.GeneratorExp)) and \
            any(items(g.iter) for g in value.generators):
        return "os.environ.items()"
    return None


def scan(module, reader):
    """(offences, stats) for one module. An offence is (file, line, rule, method, the mapping's text, the enclosing
    scope's qualified name, the assertion's text)."""
    offences, stats = [], {"reads": 0, "forms": {f: 0 for f in READ_FORMS}}
    for sn, value in module.values:
        form = binding_form(value, module.scope(sn), reader)
        if form:
            stats["forms"][form] += 1
    for sn, x in module.sites:
        scope = module.scope(sn)
        if isinstance(x, ast.Assert):
            hits = [("B", "assert", n) for part in (x.test, x.msg) if part is not None
                    for n in reader.anywhere(part, module, scope)]
            stats["reads"] += len(hits)
        else:
            method = x.func.attr
            if method in RENDERS:
                pos, kws, msg_at = RENDERS[method]
                args = [a for i, a in enumerate(x.args) if i in pos or i == msg_at]
                args += [k.value for k in x.keywords if k.arg in kws or k.arg == "msg"]
                rule = "F" if method in ("fail", "skipTest") else "A"
            elif method in NON_RENDERING:
                args, rule = [k.value for k in x.keywords if k.arg == "msg"], "A"
            else:
                args, rule = list(x.args) + [k.value for k in x.keywords], "A"
            hits = [(rule, method, n) for a in args for n in reader.rendered(a, module, scope)]
            stats["reads"] += sum(reader.reads(a, module, scope) for a in list(x.args) + [k.value for k in x.keywords])
        for rule, method, n in hits:
            offences.append((module.rel, x.lineno, rule, method, module.segment(n), module.qualname(sn), module.segment(x)))
    return offences, stats


def census(root=ROOT):
    """(files, offences, stats) over tests/*.py under `root`, product callees resolved under root's kernel/, postal/ and
    cli/. Raises when the tree holds no tests/*.py."""
    paths = sorted(glob.glob(os.path.join(root, "tests", "*.py")))
    assert paths, "the census read no file: %s holds no tests/*.py" % root
    modules = {}
    for p in paths:
        text, tree = parse_cache.source_and_tree(p, os.path.relpath(p, root))
        modules[os.path.basename(p)] = _Module(os.path.join("tests", os.path.basename(p)), text, tree)
    product = sorted(p for d in PRODUCT_DIRS for p in glob.glob(os.path.join(root, d, "*.py")))
    reader = Reader(root, modules, product)
    reader.settle([modules[n] for n in sorted(modules)])
    offences, stats = [], {"files": len(paths), "reads": 0, "forms": {f: 0 for f in READ_FORMS}}
    for name in sorted(modules):
        off, st = scan(modules[name], reader)
        offences += off
        stats["reads"] += st["reads"]
        for f, n in st["forms"].items():
            stats["forms"][f] += n
    reader.forget()
    offences.sort(key=lambda o: (o[0], o[1]))
    return [os.path.join("tests", os.path.basename(p)) for p in paths], offences, stats


def require_population(stats):
    """Raises AssertionError when the census watched nothing: a binding form it claims (BINDING_FORMS) with no binding in
    the tree, or no environment mapping read at any assertion site."""
    missing = [f for f in BINDING_FORMS if not stats["forms"].get(f)]
    assert not missing, ("the census found no binding of %s in %d files: it claims to watch that form, so either the reader "
                         "stopped seeing it or the tree no longer writes it (drop it from BINDING_FORMS and the docstring)"
                         % (", ".join(missing), stats["files"]))
    assert stats["reads"], ("the census read no environment mapping at any assertion site in %d files: it reads nothing, "
                            "so it proves nothing" % stats["files"])


def split_exempt(offences, exempt):
    """(offences no entry excuses, the entries that excuse no offence)."""
    keys = {(o[0], o[5], o[6]) for o in offences}
    return [o for o in offences if (o[0], o[5], o[6]) not in exempt], sorted(k for k in exempt if k not in keys)


def _census_here():
    def build():
        files, offences, stats = census(ROOT)
        require_population(stats)
        return files, offences, stats
    return parse_cache.derived(("env_mapping_assert_census", ROOT), build)


def _lines(offences, cap=60):
    shown = ["  %s:%d in %s: %s %s renders %s" % (o[0], o[1], o[5], o[2], o[3], o[4]) for o in offences[:cap]]
    if len(offences) > cap:
        shown.append("  ... and %d more" % (len(offences) - cap))
    return "\n".join(shown)


def _plant_scan(src, name="test_planted.py", product=None):
    """Offences of one planted module, with `product` ({file name: source}) as its kernel/ files."""
    root = tempfile.mkdtemp(prefix="envmap-census-")
    try:
        os.makedirs(os.path.join(root, "tests"))
        with open(os.path.join(root, "tests", name), "w") as f:
            f.write(src)
        if product:
            os.makedirs(os.path.join(root, "kernel"))
            for fname, text in product.items():
                with open(os.path.join(root, "kernel", fname), "w") as f:
                    f.write(text)
        return census(root)
    finally:
        shutil.rmtree(root, True)


_HEAD = "import os, unittest\nfrom unittest import mock\nclass T(unittest.TestCase):\n    def test_x(self):\n"


def _body(*lines):
    return _HEAD + "".join("        %s\n" % ln for ln in lines)


# name: (source, [the rendered texts it must name, in order]); an empty list is a clean shape
PLANTS = {
    "os-environ-container": (_body('self.assertNotIn("X", os.environ)'), ["os.environ"]),
    "os-aliased": ("import os as o, unittest\nclass T(unittest.TestCase):\n    def test_x(self):\n"
                   "        self.assertNotIn('X', o.environ)\n", ["o.environ"]),
    "from-os-import-environ": ("from os import environ as E\nimport unittest\nclass T(unittest.TestCase):\n"
                               "    def test_x(self):\n        self.assertIn('X', E)\n", ["E"]),
    "subscript-capture": (_body('seen = {}', 'self.assertNotIn("X", seen["env"], "the child")'), ['seen["env"]']),
    "get-env": (_body('body = {}', 'self.assertEqual(body.get("env"), {})'), ['body.get("env")']),
    "get-env-default-or": (_body('reg = {}', 'self.assertEqual(reg.get("env", {}) or {}, {})'), ['reg.get("env", {}) or {}']),
    "attribute-chain": (_body('self.assertIn("X", self.env)', 'self.assertEqual(s._launched_env, {})'),
                        ["self.env", "s._launched_env"]),
    "second-operand": (_body('kw = {}', 'self.assertEqual({"A": "1"}, kw["env"])'), ['kw["env"]']),
    "dict-copy-in-function": (_body('env = dict(os.environ, A="1")', 'self.assertNotIn("X", env)'), ["env"]),
    "copy-method-at-module": ("import os, unittest\nE = os.environ.copy()\nclass T(unittest.TestCase):\n"
                              "    def test_x(self):\n        self.assertIn('X', E)\n", ["E"]),
    "star-star-display": (_body('child = {**os.environ, "A": "1"}', 'self.assertDictEqual(child, {})'), ["child"]),
    "items-comprehension": (_body('env = {k: v for k, v in os.environ.items() if k != "A"}',
                                  'self.assertCountEqual(env, [])'), ["env"]),
    "items-view": (_body('pairs = os.environ.items()', 'self.assertIn(("X", "1"), pairs)'), ["pairs"]),
    "sorted-items": (_body('kw = {}', 'self.assertListEqual(sorted(kw["env"].items()), [])',
                           'self.assertTupleEqual(tuple(kw["env"].values()), ())'),
                     ['sorted(kw["env"].items())', 'tuple(kw["env"].values())']),
    "merge-operator": (_body('env = os.environ | {"A": "1"}', 'self.assertNotIn("X", env)'), ["env"]),
    "transitive-name": (_body('kw = {}', 'env = kw["env"]', 'child = dict(env)', 'self.assertNotIn("X", child)'), ["child"]),
    "tuple-target": (_body('env, n = dict(os.environ), 1', 'self.assertNotIn("X", env)'), ["env"]),
    "walrus": (_body('self.assertNotIn("X", (e := os.environ.copy()))'), ["e := os.environ.copy()"]),
    "with-patch-dict": (_body('with mock.patch.dict(os.environ, {"A": "1"}) as e:',
                              '    self.assertNotIn("X", e)'), ["e"]),
    "attribute-binding": (_body('self.saved = dict(os.environ)', 'self.assertNotIn("X", self.saved)'), ["self.saved"]),
    "key-binding": (_body('seen = {}', 'seen["child"] = dict(os.environ)', 'self.assertNotIn("X", seen["child"])'),
                    ['seen["child"]']),
    "own-callee": ("import os, unittest\ndef _child_env():\n    e = dict(os.environ, A='1')\n    return e\n"
                   "class T(unittest.TestCase):\n    def test_x(self):\n        self.assertNotIn('X', _child_env())\n",
                   ["_child_env()"]),
    "enclosing-function": ("import os, unittest\nclass T(unittest.TestCase):\n    def test_x(self):\n"
                           "        env = dict(os.environ)\n        def check():\n            self.assertNotIn('X', env)\n"
                           "        check()\n", ["env"]),
    "member-side": (_body('self.assertIn(dict(os.environ), [])'), ["dict(os.environ)"]),
    "in-a-display": (_body('kw = {}', 'self.assertEqual((kw["env"], 1), (None, 1))'), ['kw["env"]']),
    "wider-methods": (_body('self.assertIsNone(self.env)', 'self.assertFalse(os.environ)',
                            'self.assertIs(self.env, None)', 'self.assertNotEqual(self.env, {})'),
                      ["self.env", "os.environ", "self.env", "self.env"]),
    "message-formats": (_body('env = dict(os.environ)', 'self.assertTrue(False, "left: %r" % (env,))',
                              'self.assertTrue(False, f"left: {env}")', 'self.assertEqual(1, 2, msg=str(env))'),
                        ["env", "env", "env"]),
    "fail-message": (_body('self.fail("left %s" % os.environ)'), ["os.environ"]),
    "helper-assert": (_body('kw = {}', 'self.assertEnvClean(kw["env"])'), ['kw["env"]']),
    "bare-assert": (_body('env = dict(os.environ)', 'assert "X" not in env', 'assert env.get("X") is None'),
                    ["env", "env"]),
    "keys-view": (_body('self.assertIn("X", os.environ.keys())', 'kw = {}', 'self.assertNotIn("X", kw["env"].keys())',
                        'names = os.environ.keys()', 'self.assertIn("X", names)'),
                  ["os.environ.keys()", 'kw["env"].keys()', "names"]),
    "message-slice": (_body('env = dict(os.environ)', 'self.assertTrue(False, repr(env)[:80])',
                            'self.assertEqual(1, 2, ("%r" % (env,))[5:])'), ["env", "env"]),
    "message-join": (_body('env = dict(os.environ)',
                           'self.assertTrue(False, ", ".join("%s=%s" % kv for kv in env.items()))',
                           'self.assertTrue(False, " ".join(env.values()))'),
                     ['("%s=%s" % kv for kv in env.items())', "env.values()"]),
    # the clean shapes: what a failure prints is one value, a bool, or names
    "clean-get-read": (_body('seen = {}', 'self.assertIsNone(seen["env"].get("X"), "X")',
                             'self.assertEqual(seen["env"].get("X"), "1")'), []),
    "clean-membership": (_body('seen = {}', 'self.assertFalse("X" in seen["env"], "X")',
                               'self.assertTrue("X" in os.environ, "X")'), []),
    "clean-value-subscript": (_body('kw = {}', 'self.assertEqual(kw["env"]["ROMP_SID"], "s")',
                                    'self.assertEqual(kw["env"]["ROMP_SERVICE_ENV"], "s")'), []),
    "clean-names-only": (_body('env = dict(os.environ)', 'self.assertEqual(sorted(env), [])',
                               'self.assertNotIn("X", set(env))', 'self.assertEqual(len(env), 0)',
                               'self.assertNotIn("X", list(env))'), []),
    "clean-equality-as-bool": (_body('kw = {}', 'self.assertTrue(kw["env"] == {"A": "1"}, "the overlay differs")',
                                     'self.assertTrue(self.env is None, "launched")'), []),
    "clean-upper-case-names": ("import unittest\nENV = {'A': '1'}\nLEAK_BOUND_ENV = 'X'\nclass T(unittest.TestCase):\n"
                               "    def test_x(self):\n        self.assertEqual(ENV, {'A': '1'})\n"
                               "        self.assertEqual(LEAK_BOUND_ENV, 'X')\n", []),
    "clean-synthetic-dict": (_body('env = {"A": "1"}', 'self.assertNotIn("X", env)'), []),
    "clean-env-named-callee": ("import unittest\nclass B:\n    def set_env(self, sid, pick):\n        return True\n"
                               "def _bin_on_path_env(environ):\n    return {}\n"
                               "class T(unittest.TestCase):\n    def test_x(self):\n"
                               "        self.assertTrue(B().set_env('s', {}))\n        self.assertIs(B().set_env('s', {}), True)\n"
                               "        self.assertEqual(_bin_on_path_env({}), {})\n", []),
    "clean-assert-true-of-mapping": (_body('self.assertTrue(os.environ)', 'self.assertIsNotNone(os.environ)'), []),
    "clean-raises": (_body('self.assertRaises(KeyError, os.environ.__getitem__, "X")'), []),
    "clean-bare-names": (_body('names = sorted(os.environ)', 'assert "X" not in names'), []),
    "clean-keys-and-join-names": (_body('env = dict(os.environ)', 'self.assertEqual(sorted(os.environ.keys()), [])',
                                        'self.assertEqual(len(env.keys()), 0)',
                                        'self.assertTrue("X" in os.environ.keys(), "X")',
                                        'self.assertTrue(False, ", ".join(env))',
                                        'self.assertTrue(False, ", ".join(sorted(env)))'), []),
    # stated limits, pinned so the docstring cannot outlive the reader
    "limit-parameter": ("import unittest\nclass T(unittest.TestCase):\n    def check(self, env):\n"
                        "        self.assertNotIn('X', env)\n", []),
    "limit-list-index": (_body('captured = [dict(os.environ)]', 'self.assertNotIn("X", captured[0])'), []),
    "limit-prebuilt-message": (_body('msg = "%r" % (os.environ,)', 'self.assertTrue(False, msg)'), []),
    "limit-read-back": (_body('import json', 'seen = json.loads(open("dump.json").read())', 'self.assertNotIn("X", seen)'), []),
    "limit-for-target": (_body('seen = [(["claude"], dict(os.environ))]', 'for cmd, env in seen:',
                               '    self.assertNotIn("X", env)'), []),
    "limit-mock-assertion": (_body('with mock.patch("subprocess.run") as run:', '    run(["claude"], env=dict(os.environ))',
                                   'run.assert_not_called()', 'run.assert_called_once()',
                                   'run.assert_called_once_with(["claude"])'), []),
    "limit-derived-strings": (_body('env = dict(os.environ)', 'pairs = env.items()', 'self.assertEqual(sorted(pairs), [])',
                                    'vals = env.values()', 'self.assertTrue(False, ", ".join(vals))',
                                    'self.assertTrue(False, ", ".join(k + "=" + env[k] for k in env))',
                                    'self.assertTrue(False, repr(env).replace("a", "b"))',
                                    'self.assertTrue(False, ", ".join(map(str, env.values())))'), []),
}


class EnvMappingAssertCensus(unittest.TestCase):
    maxDiff = None

    def test_the_population_is_derived_and_watched(self):
        files, offences, stats = _census_here()
        self.assertIn(os.path.join("tests", "conftest.py"), files)
        self.assertIn(os.path.join("tests", os.path.basename(__file__)), files, "the census reads itself")
        print("ENVMAP files=%d, env reads at assertion sites=%d, bindings by form: %s, offences=%d, exempt=%d"
              % (stats["files"], stats["reads"], ", ".join("%s %d" % kv for kv in stats["forms"].items()),
                 len(offences), len(EXEMPT)), file=sys.stderr)

    def test_no_assertion_renders_an_environment_mapping(self):
        files, offences, _ = _census_here()
        left, _stale = split_exempt(offences, EXEMPT)
        self.assertEqual(left, [], "%d assertions render an environment mapping when they fail (%d files read):\n%s\n"
                         "Test the one variable and name it: assertFalse(name in env, name), assertTrue(name in env, "
                         "name), assertTrue(env == want, msg) (this module's docstring)"
                         % (len(left), len(files), _lines(left)))

    def test_every_exemption_names_a_live_site(self):
        _, offences, _ = _census_here()
        _left, stale = split_exempt(offences, EXEMPT)
        self.assertEqual(stale, [], "EXEMPT entries that match no site: remove them")
        for key, reason in EXEMPT.items():
            self.assertTrue(len(key) == 3 and isinstance(reason, str) and reason.strip(), "an entry is (file, function, "
                            "assertion text) -> its reason: %r" % (key,))

    def test_each_planted_shape_is_read_as_its_rendering(self):
        got, want = {}, {}
        for name, (src, texts) in PLANTS.items():
            _files, offences, _stats = _plant_scan(src)
            got[name] = [o[4] for o in offences]
            want[name] = texts
        self.assertEqual(got, want)
        self.assertTrue(any(t for _, t in PLANTS.values()) and any(not t for _, t in PLANTS.values()))

    def test_the_rules_are_named_per_road(self):
        rules = {}
        for name in ("os-environ-container", "fail-message", "bare-assert"):
            _f, offences, _s = _plant_scan(PLANTS[name][0])
            rules[name] = sorted({o[2] for o in offences})
        self.assertEqual(rules, {"os-environ-container": ["A"], "fail-message": ["F"], "bare-assert": ["B"]})

    def test_a_product_callee_that_returns_the_environment_is_read(self):
        test = ("import unittest\nclass T(unittest.TestCase):\n    def test_x(self):\n"
                "        self.assertNotIn('X', jd._judge_env('index'))\n        self.assertNotIn('X', jd._overlay_env())\n"
                "        key_env = jd._judge_env('triage')\n        self.assertNotIn('X', key_env)\n")
        product = {"judge.py": "import os\ndef _judge_env(tier):\n    env = {k: v for k, v in os.environ.items() if k != 'TMUX'}\n"
                               "    return env\ndef _overlay_env():\n    return {'A': '1'}\n"}
        _f, offences, _s = _plant_scan(test, product=product)
        self.assertEqual([(o[1], o[4]) for o in offences], [(4, "jd._judge_env('index')"), (7, "key_env")])
        _f, offences, _s = _plant_scan(test)
        self.assertEqual(offences, [], "with no product module the callee resolves to nothing")

    def test_a_callee_a_module_imports_from_tests_is_read(self):
        root = tempfile.mkdtemp(prefix="envmap-census-")
        self.addCleanup(shutil.rmtree, root, True)
        os.makedirs(os.path.join(root, "tests"))
        with open(os.path.join(root, "tests", "envhelper.py"), "w") as f:
            f.write("import os\ndef child_env():\n    return dict(os.environ, A='1')\n")
        with open(os.path.join(root, "tests", "test_user.py"), "w") as f:
            f.write("import unittest\nfrom envhelper import child_env\nclass T(unittest.TestCase):\n"
                    "    def test_x(self):\n        self.assertNotIn('X', child_env())\n")
        files, offences, stats = census(root)
        self.assertEqual(files, [os.path.join("tests", "envhelper.py"), os.path.join("tests", "test_user.py")])
        self.assertEqual([(o[0], o[1], o[4]) for o in offences], [(os.path.join("tests", "test_user.py"), 5, "child_env()")])
        self.assertEqual(stats["forms"][READ_FORMS[0]], 0, "a returned copy is no binding")

    def test_the_binding_forms_are_counted(self):
        src = ("import os\nA = dict(os.environ, X='1')\nB = os.environ.copy()\nC = {**os.environ}\nD = os.environ.items()\n"
               "E = {k: v for k, v in os.environ.items()}\nF = dict(**os.environ)\n")
        _f, _o, stats = _plant_scan(src)
        self.assertEqual(stats["forms"], {READ_FORMS[0]: 2, READ_FORMS[1]: 1, READ_FORMS[2]: 1, READ_FORMS[3]: 2})
        require_population(dict(stats, reads=1))

    def test_an_empty_population_fails_loudly(self):
        root = tempfile.mkdtemp(prefix="envmap-census-")
        self.addCleanup(shutil.rmtree, root, True)
        os.makedirs(os.path.join(root, "tests"))
        with self.assertRaisesRegex(AssertionError, "holds no tests/"):
            census(root)
        with open(os.path.join(root, "tests", "test_plain.py"), "w") as f:
            f.write("import os\nA = dict(os.environ)\n")
        _f, _o, stats = census(root)
        with self.assertRaisesRegex(AssertionError, r"found no binding of \{\*\*os\.environ, \.\.\.\}, os\.environ\.items\(\)"):
            require_population(stats)
        with self.assertRaisesRegex(AssertionError, "read no environment mapping at any assertion site"):
            require_population({"files": 1, "reads": 0, "forms": {f: 1 for f in READ_FORMS}})

    def test_an_exemption_excuses_its_site_only_and_a_stale_one_is_named(self):
        src = _body('kw = {}', 'self.assertNotIn("X", kw["env"])', 'self.assertNotIn("Y", kw["env"])')
        _f, offences, _s = _plant_scan(src)
        self.assertEqual(len(offences), 2)
        key = (offences[0][0], "T.test_x", 'self.assertNotIn("X", kw["env"])')
        stale = (offences[0][0], "T.test_x", 'self.assertNotIn("Z", kw["env"])')
        left, gone = split_exempt(offences, {key: "a synthetic reason", stale: "matches nothing"})
        self.assertEqual([o[6] for o in left], ['self.assertNotIn("Y", kw["env"])'])
        self.assertEqual(gone, [stale])


if __name__ == "__main__":
    if sys.argv[1:2] == ["--table"]:
        files, offences, stats = census(sys.argv[2] if len(sys.argv) > 2 else ROOT)
        print("files %d; env reads at assertion sites %d; bindings by form: %s"
              % (stats["files"], stats["reads"], ", ".join("%s %d" % kv for kv in stats["forms"].items())))
        left, stale = split_exempt(offences, EXEMPT)
        print("offences %d (exempt %d, stale entries %d)" % (len(left), len(offences) - len(left), len(stale)))
        print(_lines(left, cap=len(left) or 1))
    else:
        unittest.main()
