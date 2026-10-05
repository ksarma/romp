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
none of the environment copies it claims to watch (each binding form below, counted in the real tree), no environment
mapping read at an assertion site at all (the safe reads the fixed tree keeps: a .get(name) and a `name in mapping`),
or no holder (THE HOLDERS) read at one (a field, a `name in holder`, its sorted names), so the census never passes on
nothing.

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
     is read as rendering every argument it is handed. An absent-value check over an environment mapping renders the
     VALUE: assertIsNone(X.get(k)), assertFalse(X.get(k)), assertEqual(X.get(k), None) and assertIs(X.get(k), None),
     either operand order, fail exactly when the variable is present, and print it (_absent_value_reads).
  F  fail and skipTest render their message (pytest.fail's reason included).
  B  a bare assert renders every environment mapping anywhere in its test or its message: pytest's rewrite explains a
     call by printing its arguments and an attribute by printing its receiver, so even `assert env.get(n) is None`
     prints the mapping, as the receiver of the bound method it explains.
An argument renders a mapping when it IS one, or holds one where the failure prints it: an element of a tuple, list,
set or dict display, a value formatted into a string (an operand of % or +, an f-string's field, an argument of str,
repr, ascii, format, pformat, dumps or a .format() call), the value a slice is taken of (repr(env)[:80] prints part of
the mapping), a join's argument when it yields values (M.values(), or a comprehension over M.items() or M.values():
", ".join("%s=%s" % kv for kv in env.items())), either branch of a conditional or an operand of and/or.
A name bound, in the scope Python reads it from, to a value that renders one renders it too (msg = "%r" % (env,);
text = json.dumps(spec)).
What a failure prints of a mapping it only READS is safe and never flagged: a .get(name) or a [name] read prints the one
value (outside an absent-value check), `name in mapping` inside assertTrue or assertFalse prints a bool, and sorted(),
set(), list(), tuple() or len() of a mapping, or of its keys(), print its names, as a join over the mapping itself does
(iterating a mapping yields its keys). The same holds for a holder: a field read, a `name in holder` bool, its sorted
names. So the fix for each site is:
  assertNotIn(name, env, msg)  ->  assertFalse(name in env, msg)   (absent stays absent; the message names the variable
  assertIn(name, env, msg)     ->  assertTrue(name in env, msg)     when the original had none)
  assertEqual(env, want, msg)  ->  assertTrue(env == want, msg)    (the same equality; the message says what differs)
  assertIsNone(env, msg)       ->  assertTrue(env is None, msg)
  assertIsNone(env.get(name))  ->  assertFalse(name in env, msg), or assertTrue(env.get(name) is None, msg)
and for a holder the same bools (assertFalse("settings" in kw, msg), assertTrue(s._launching is None, msg)), with an
equality split into its fields: the key set, assertEqual(sorted(holder), [the expected keys], msg); each field,
assertEqual(holder["mode"], "plan", msg); the env field as a bool, assertTrue(holder["env"] == {}, msg).

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
THE HOLDERS, read by is_holder(): a container that holds an environment mapping under an env key renders that
environment when a failure prints it whole (the SDK launch options, whose "env" the product builds from os.environ;
a session's launch shape; a host spawn spec; a registry entry, which stores a session's env). A HOLDER is:
  a dict display with a string key that is an env word (spec = {"sid": s, "env": {...}}), dict(..., env=E) and
  SimpleNamespace(env=E), unless E cannot be an environment (_may_be_env: a literal string, number, None, list, tuple
  or set, or a dict display that names keys and no upper-case variable name, such as a page's {"standalone": True,
  "iosMajor": 17}); a copy of a holder (dict(H, ...), {**H}, H.copy(), copy.copy(H));
  a name bound to a holder, in the scope Python reads it from, and a name the module's text shows is one: its env key
  read, set or deleted (kw["env"], kw.get("env"), kw["env"] = ...), or tested ("env" in X, assertNotIn("env", X))
  where the module also reads X by a string key or a view (X["ok"], X.get("k"), X.items()), since a membership test
  takes a string or a set as readily, or X compared for equality with a holder (assertEqual(s._launching, {...,
  "env": {}})); what such a name is bound to is shown the same way (a call, an attribute or a keyed item; a tuple
  element is not: WHAT IT CANNOT SEE) (kw = self._options_kw(sess); kw["env"] makes every self._options_kw(...) call
  one);
  an attribute name or a string key a module assigns a holder to or shows is one the same way (s._launching = {...,
  "env": {}}; s._launching["env"]), read module-wide like the mapping attributes above;
  a call: of a function of the tree that returns a holder, or that the text shows returns one (by function: self.f()
  resolves to the enclosing class's own method first, so two classes' _reg helpers stay apart), whose own return is
  then shown in turn (a _reg helper returning sb.read_reg(...) shows read_reg's return); of a product function
  the text of ANY module shows returns one (sb.read_reg, be._options), since its return is the same whoever calls it;
  never of a library function by its name (json.loads(path)["env"] shows that call and the name bound to it, not every
  json.loads);
  an element of a tuple target bound from a call (host, sock, spec = self._start(...)), read through the callee's
  `return a, b, c`.
THE BINDING FORMS. The census counts four copies of os.environ where a name is bound to one (READ_FORMS):
dict(os.environ, ...), os.environ.copy(), {**os.environ, ...} and os.environ.items() (a binding of the view or a
comprehension over it). It claims to find three of them in the tree (BINDING_FORMS) and fails when the tree holds none
of one: drop the form from the claim, or read why the reader stopped seeing it. os.environ.copy() is read and planted
but not claimed: on 2026-10-05 the tree spells it only inside other censuses' planted strings.

EXEMPT names a site the rule should not hold, one entry per site, keyed by (file, the enclosing function's qualified
name, the assertion's source text with whitespace collapsed), with its reason; an entry that matches no offence is
stale and fails the census, so the list cannot outlive the sites it excuses. Two identical assertions in one function
share an entry. EXEMPT is EMPTY today: every site found was fixed.

WHAT IT CANNOT SEE (stated, not closed). Five of these shapes held real sites on 2026-10-05, each fixed by hand:
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
  (tests/test_login_records.py's whitelist test; now assertFalse(name in seen, name));
  an absent-value check over a capture unpacked from a list index: `cmd, env = self.calls[0]`, then
  assertIsNone(env.get(name)), which prints the variable's value when it is set (tests/test_judge.py,
  IndexTierLever.test_triage_tier_is_untouched and
  AliasHeadDrift.test_every_tier_feeds_the_record_and_only_the_index_lever_reads_it; now assertFalse(name in env, name));
  a bare assert inside a planted module, Python a test writes as a string and runs in a child pytest that inherits the
  runner's environment: pytest explains `assert os.environ.get(name) is None` by printing the value and os.environ
  itself (tests/test_hermetic_kernel_postal.py, the after_port module in
  HermeticKernelPostal.test_a_seam_written_in_setupmodule_setupclass_or_a_module_fixture_with_no_restore_is_named_by_its_module;
  now present = name in os.environ, then assert not present, name), and `assert name not in os.environ, msg` by printing
  os.environ (the module in HermeticKernelPostal.test_a_port_one_test_sets_is_gone_when_the_next_test_starts; now
  present = name in os.environ, then assert not present, msg). Four more planted asserts print os.environ and are now
  fixed the same way: `assert os.environ.get(name) == "1"` when the name is absent (the after_client_only module beside
  after_port; now value = os.environ.get(name), then assert value == "1", name); `assert name not in os.environ` with no
  message (tests/test_env_value_redaction.py, the test_probe_three module in
  HookEndToEnd.test_a_patch_dict_value_a_split_header_and_a_patterned_token_all_print_markers; now present = name in
  os.environ, then assert not present, name); and an assert over os.environ.get calls in a planted conftest's fixture,
  written to fail once, whose report carries os.environ and prints if the conftest's own makereport hook stops marking
  it passed (in_place_makereport, twice: in
  HermeticKernelPostal.test_a_hook_that_may_keep_pytest_from_running_a_fixture_refuses_it_on_both_roads and in
  _proof_facets; now passes = the same expression, then assert passes, name).
The census also cannot see:
  a mapping or a holder reached through a parameter (a helper handed env by its caller), a list index
  (captured.append(env); captured[0]), getattr, or an attribute or key whose name is neither an env word nor assigned
  an environment mapping in the module (s.env_vars, a per-session overlay, is not read);
  an object that holds the environment as an attribute its repr prints (the SDK's options object, opts.env, built by a
  constructor the census does not know; SimpleNamespace is read): no assertion prints one whole on 2026-10-05;
  a holder known only by a membership test, where the module never reads it by a string key or a view
  (body = self.post(); self.assertNotIn("env", body) alone), and a holder whose env key only another module reads,
  unless a product function returns it;
  a holder bound as a tuple element of a call whose own return does not show it (code, body = self._post();
  body["env"] in one test shows that test's body, not the body another test unpacks from the same call; reading it
  would make test_run_end_leaked_processes.py's pids, whose "env" key labels a process, a holder);
  a callee that resolves by a name the module does not define or import from tests/, a product function whose name is
  not an env word, a product module's own attribute and key bindings, or a callee that returns the mapping through
  another call's parameter (sb._bin_on_path_env(environ) returns a mapping of its argument's values and is not read);
  a view bound to a name and then iterated (pairs = env.items(); sorted(pairs), or ", ".join(vals) after vals =
  env.values()), a join whose comprehension reads the values through the keys (", ".join(k + "=" + env[k] for k in
  env)), and a formatted mapping passed through another call (repr(env).replace(...), map(str, env.values()));
  Python inside a string (a planted module a test writes and runs, whose bare assert over os.environ renders under
  that run's own conftest);
  a mapping printed by print(), logging, a raise or a subprocess's output a test asserts on;
  a message built from a mapping in another function, or kept on an attribute or a key (self.msg = "%r" % env): a
  name in scope is the one binding followed.
PLANTS pins each shape it reads, red or green, and the stated limits a reader would most expect it to see (a parameter,
a list index, a mapping read back from a child's dump, a for target over captured pairs, mock's assert_called* family,
a view bound to a name, values read through the keys, a formatted mapping passed through another call, an options
object holding the environment as an attribute, a holder known only by a membership test, a holder bound as a tuple
element that only another test shows).

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
# the equality forms: an equality between X and a holder shows X is one
EQUALITIES = tuple(m for m, spec in RENDERS.items() if spec[2] == 2 and len(spec[0]) == 2 and m not in (
    "assertIn", "assertNotIn", "assertIs", "assertIsNot", "assertDictContainsSubset", "assertGreater",
    "assertGreaterEqual", "assertLess", "assertLessEqual"))
# a mapping's own methods return one value or None, never a mapping of values (copy, keys, items and values are read
# above); a callee of one of these names is never resolved by name
MAPPING_METHODS = ("get", "pop", "setdefault", "update", "popitem", "fromkeys", "clear", "__getitem__", "__contains__")
# the builders that keep a keyword as a key or an attribute their repr prints: dict(env=E), SimpleNamespace(env=E)
HOLDER_BUILDERS = COPIERS + ("SimpleNamespace",)
# the absent-value checks: each fails when the value is present, and prints it
ABSENT_CHECKS = ("assertIsNone", "assertFalse", "failIf")
ABSENT_EQUALS = ("assertEqual", "assertEquals", "failUnlessEqual", "assertIs")
# callees a witness never marks: builders, copies, formatters and a mapping's own methods return a new value of their
# arguments, not the holder a name bound to them was shown to be
NEVER_HOLDER_CALLEES = HOLDER_BUILDERS + SEQUENCES + FORMATTERS + MAPPING_METHODS + ("keys",) + VIEWS + (
    "getattr", "vars", "next", "iter", "len")
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


class _Element:
    """The value a tuple target's element is bound to from a call: `host, sock, spec = self._start()` binds spec to
    element 2 of what the call returns, read through the callee's `return a, b, c` (THE HOLDERS)."""
    __slots__ = ("call", "index")

    def __init__(self, call, index):
        self.call, self.index = call, index


def _pairs(target, value, calls=False):
    """(name, value) for each Name a target binds: a tuple or list target against a tuple or list value of its length,
    nothing starred on either side, element by element; with `calls`, a tuple or list target with nothing starred
    against a call, each element to its _Element; any other tuple or list target binds each element to an unknown value
    (None)."""
    if isinstance(target, (ast.Tuple, ast.List)):
        elts = target.elts
        if isinstance(value, (ast.Tuple, ast.List)) and len(value.elts) == len(elts) and \
                not any(isinstance(e, ast.Starred) for e in list(elts) + list(value.elts)):
            for t, v in zip(elts, value.elts):
                yield from _pairs(t, v)
        elif calls and isinstance(value, ast.Call) and not any(isinstance(e, ast.Starred) for e in elts):
            for i, t in enumerate(elts):
                if isinstance(t, ast.Name):
                    yield t.id, _Element(value, i)
                else:
                    yield from _pairs(t, None)
        else:
            for t in elts:
                yield from _pairs(t, None)
    elif isinstance(target, ast.Starred):
        yield from _pairs(target.value, None)
    elif isinstance(target, ast.Name):
        yield target.id, value


def _env_var_name(key):
    """A string that names an environment variable by the convention: upper case, with a letter (ROMP_SID, A)."""
    return isinstance(key, str) and key == key.upper() and any(c.isalpha() for c in key)


def _may_be_env(value):
    """False for a value held under an env key that cannot be an environment mapping: a literal string, number, None,
    list, tuple or set, or a dict display that names keys and no variable among them ({"standalone": True,
    "iosMajor": 17}, a page's environment); True for anything else (a name, a call, {}, {"A": "1"}, {**os.environ})."""
    if isinstance(value, (ast.Constant, ast.List, ast.Tuple, ast.Set, ast.JoinedStr, ast.ListComp, ast.SetComp,
                          ast.GeneratorExp, ast.Lambda)):
        return False
    if isinstance(value, ast.Dict) and value.keys and all(k is not None for k in value.keys):
        return any(not isinstance(k, ast.Constant) or _env_var_name(k.value) for k in value.keys)
    return True


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
                    self._bind(t, x.value, calls=True)
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

    def _bind(self, target, value, calls=False):
        for name, v in _pairs(target, value, calls):
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
        self.keyed = []                   # (scope node, X) for X["env"] read, set or deleted, and X.get("env")
        self.member = []                  # (scope node, X) for "env" in X and "env" not in X
        self.mapped = []                  # (scope node, X) for X["k"], X.get("k") and X.items(): X is a mapping
        self.equal = []                   # (scope node, a, b) for a == b and a != b
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
                if t is ast.Subscript:
                    key = _str_const(n.slice)
                    if key is not None:
                        self.mapped.append((sn, n.value))
                        if env_word(key):
                            self.keyed.append((sn, n.value))
                elif t is ast.Call:
                    f = n.func
                    if type(f) is ast.Attribute:
                        if f.attr in KEYED and n.args:
                            key = _str_const(n.args[0])
                            if key is not None:
                                self.mapped.append((sn, f.value))
                                if env_word(key):
                                    self.keyed.append((sn, f.value))
                        elif f.attr in ("items", "keys", "values") and not n.args:
                            self.mapped.append((sn, f.value))
                elif t is ast.Compare:
                    for left, op, right in zip([n.left] + n.comparators[:-1], n.ops, n.comparators):
                        if type(op) in (ast.In, ast.NotIn) and env_word(_str_const(left)):
                            self.member.append((sn, right))
                        elif type(op) in (ast.Eq, ast.NotEq):
                            self.equal.append((sn, left, right))
                for field in n._fields:                 # ast.iter_child_nodes, inlined: the walk is most of the cost
                    v = getattr(n, field, None)
                    if type(v) is list:
                        stack.extend(x for x in v if isinstance(x, ast.AST))
                    elif isinstance(v, ast.AST):
                        stack.append(v)
        self._scopes = {}
        self._lines = None
        self.attrs, self.keys = set(), set()   # attribute names and string keys the module assigns a mapping to
        # attribute names, string keys and callee names the module's text shows holding an environment mapping under an
        # env key (a HOLDER, THE HOLDERS in the module docstring)
        self.holder_attrs, self.holder_keys = set(), set()

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
        self._product_modules, self._product_names = {}, None
        self._returns = {}                              # (rel, id(fn)) -> bool (False while in progress)
        self._names = {}                                # (id(scope), name) -> bool (False while in progress)
        self._memo = {}                                 # (id(node), id(scope)) -> bool
        self._candidates = {}                           # (rel, name) -> [(module, function)]
        self.settled = False
        self.holder_names = set()                       # (id(scope), name): a name the module's text shows is a holder
        self.holder_returns = set()                     # (rel, id(fn)): a function whose call the text shows is a holder
        self.holder_callees = set()                     # a product function's name whose call some module shows is a holder
        self._hreturns, self._hnames, self._hmemo = {}, {}, {}

    def forget(self):
        self._returns.clear()
        self._names.clear()
        self._memo.clear()
        self._hreturns.clear()
        self._hnames.clear()
        self._hmemo.clear()

    def product(self):
        """name -> [(module, function)] over the product modules, for the callees whose name is an env word."""
        if self._product is None:
            self._product = {}
            for p in self.product_paths:
                text, tree = parse_cache.source_and_tree(p, os.path.relpath(p, self.root))
                m = self._product_modules[p] = _Module(os.path.relpath(p, self.root), text, tree)
                for name, fns in m.functions.items():
                    if env_word(name):
                        self._product.setdefault(name, []).extend((m, f) for f in fns)
        return self._product

    def in_product(self, name):
        """A function of that name is defined in a product module (json.loads, str.replace and the rest of the library
        are not)."""
        if self._product_names is None:
            self.product()
            self._product_names = {n for p in self.product_paths for n in self._product_modules[p].functions}
        return name in self._product_names

    def resolve(self, module, call, scope):
        """The functions a holder call may run: for self.name(...) or cls.name(...), the enclosing class's own method of
        that name when it defines one (two classes' _reg helpers stay apart); else candidates()."""
        f, name = call.func, _callee(call)
        if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id in ("self", "cls"):
            s = scope
            while s is not None and not isinstance(s.node, ast.ClassDef):
                s = s.parent
            if s is not None:
                own = [(module, x) for x in s.node.body if isinstance(x, FUNCTIONS) and x.name == name]
                if own:
                    return own
        return self.candidates(module, name) if name else []

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

    @staticmethod
    def _returns_of(fn):
        """The values fn's return statements return (a nested function's are its own)."""
        out, stack = [], list(ast.iter_child_nodes(fn))
        while stack:
            x = stack.pop()
            if isinstance(x, ast.Return):
                if x.value is not None:
                    out.append(x.value)
            elif not isinstance(x, SCOPES):
                stack.extend(ast.iter_child_nodes(x))
        return out

    def returns_holder(self, module, fn, index=None):
        """A return statement of fn returns a holder; with `index`, element `index` of a returned tuple or list display."""
        key = (module.rel, id(fn), index)
        if key in self._hreturns:
            return self._hreturns[key]
        self._hreturns[key] = False                     # a recursive callee reads as not returning one while in progress
        scope = module.scope(fn)
        got = False
        stack = list(ast.iter_child_nodes(fn))
        while stack and not got:
            x = stack.pop()
            if isinstance(x, ast.Return) and x.value is not None:
                v = x.value
                if index is not None:
                    v = (v.elts[index] if isinstance(v, (ast.Tuple, ast.List)) and index < len(v.elts)
                         and not any(isinstance(e, ast.Starred) for e in v.elts) else None)
                got = self.is_holder(v, module, scope)
            elif not isinstance(x, SCOPES):
                stack.extend(ast.iter_child_nodes(x))
        self._hreturns[key] = got
        return got

    def is_holder(self, node, module, scope):
        """A HOLDER: a container that holds an environment mapping under an env key (THE HOLDERS)."""
        if node is None or node is _ENV_MARK:
            return False
        key = (id(node), id(scope))
        if self.settled and key in self._hmemo:
            return self._hmemo[key]
        got = self._is_holder(node, module, scope)
        if self.settled:
            self._hmemo[key] = got
        return got

    def _is_holder(self, node, module, scope):
        if isinstance(node, ast.Dict):
            return any((k is not None and env_word(_str_const(k)) and _may_be_env(v))
                       or (k is None and self.is_holder(v, module, scope)) for k, v in zip(node.keys, node.values))
        if isinstance(node, ast.Attribute):
            return node.attr in module.holder_attrs
        if isinstance(node, ast.Subscript):
            key = _str_const(node.slice)
            return key is not None and key in module.holder_keys
        if isinstance(node, ast.Name):
            s, values = self.lookup(scope, node.id)
            if s is None:
                return False
            mark = (id(s), node.id)
            if mark in self.holder_names:
                return True
            if mark in self._hnames:
                return self._hnames[mark]
            self._hnames[mark] = False                  # a name bound through itself reads its other bindings
            got = any(self.is_holder(v, module, s) for v in values)
            self._hnames[mark] = got
            return got
        if isinstance(node, ast.Call):
            return self._call_is_holder(node, module, scope)
        if isinstance(node, _Element):
            return any(self.returns_holder(m, fn, node.index) for m, fn in self.resolve(module, node.call, scope))
        if isinstance(node, ast.BoolOp):
            return any(self.is_holder(v, module, scope) for v in node.values)
        if isinstance(node, ast.IfExp):
            return self.is_holder(node.body, module, scope) or self.is_holder(node.orelse, module, scope)
        if isinstance(node, ast.NamedExpr):
            return self.is_holder(node.value, module, scope)
        return False

    def _call_is_holder(self, node, module, scope):
        f, name = node.func, _callee(node)
        if isinstance(f, ast.Attribute):
            if f.attr == "copy" and not node.args:
                return self.is_holder(f.value, module, scope)
            if f.attr in KEYED and node.args:
                key = _str_const(node.args[0])
                return key is not None and key in module.holder_keys
            if f.attr in MAPPING_METHODS + ("keys",) + VIEWS:
                return False                            # a mapping's own method: one value, its names, a view, or None
        if name in HOLDER_BUILDERS:
            # dict(..., env=E) and SimpleNamespace(env=E) hold E under the key; dict(H, ...) and copy.copy(H) copy a holder
            return (any((env_word(k.arg) and _may_be_env(k.value)) or (k.arg is None and self.is_holder(k.value, module, scope))
                        for k in node.keywords) or any(self.is_holder(a, module, scope) for a in node.args))
        if name in self.holder_callees:
            return True
        if name:
            return any((m.rel, id(fn)) in self.holder_returns or self.returns_holder(m, fn)
                       for m, fn in self.resolve(module, node, scope))
        return False

    @staticmethod
    def _identity(node):
        """How the mapping evidence for a membership test is matched, module-wide: a name, an attribute's name, a key, a
        callee's name; None for anything else."""
        if isinstance(node, ast.Name):
            return ("name", node.id)
        if isinstance(node, ast.Attribute):
            return ("attr", node.attr)
        if isinstance(node, ast.Subscript):
            key = _str_const(node.slice)
            return None if key is None else ("key", key)
        if isinstance(node, ast.Call):
            name = _callee(node)
            return None if name is None else ("call", name)
        return None

    def witness(self, node, module, scope):
        """Record what the module's text shows of `node`: it holds an environment mapping under an env key. A name is
        recorded in the scope that binds it, and so is each call, attribute or keyed item it is bound to (kw = f(...);
        kw["env"] makes every f(...) in the module a holder); an attribute by its name, a keyed item by its key and a
        call by its callee's name, module-wide. True when something new was recorded."""
        if isinstance(node, ast.Name):
            s, values = self.lookup(scope, node.id)
            if s is None or (id(s), node.id) in self.holder_names:
                return False
            self.holder_names.add((id(s), node.id))
            for v in values:
                if isinstance(v, (ast.Call, ast.Attribute, ast.Subscript, ast.BoolOp, ast.IfExp)):
                    self.witness(v, module, s)
            return True
        if isinstance(node, ast.Attribute):
            new = node.attr not in module.holder_attrs
            module.holder_attrs.add(node.attr)
            return new
        if isinstance(node, ast.Subscript):
            key = _str_const(node.slice)
            if key is None or key in module.holder_keys:
                return False
            module.holder_keys.add(key)
            return True
        if isinstance(node, ast.Call):
            name = _callee(node)
            if not name or name in NEVER_HOLDER_CALLEES:
                return False
            fns = self.resolve(module, node, scope)
            if fns:                                     # the tree's own functions: each is marked, never the bare name
                new = [(m, fn) for m, fn in fns if (m.rel, id(fn)) not in self.holder_returns]
                for m, fn in new:                       # and what each returns is shown the same way: _reg returning
                    self.holder_returns.add((m.rel, id(fn)))    # sb.read_reg(...) shows read_reg's return
                    for x in self._returns_of(fn):
                        self.witness(x, m, m.scope(fn))
                return bool(new)
            if name in self.holder_callees or not self.in_product(name):
                return False
            self.holder_callees.add(name)
            return True
        if isinstance(node, (ast.BoolOp, ast.IfExp)):
            parts = node.values if isinstance(node, ast.BoolOp) else [node.body, node.orelse]
            return any([self.witness(p, module, scope) for p in parts])
        if isinstance(node, ast.NamedExpr):
            return self.witness(node.target, module, scope) | self.witness(node.value, module, scope)
        return False

    def renders_whole(self, node, module, scope):
        """An environment mapping, or a holder of one: a failure that prints it prints the environment."""
        return self.is_env(node, module, scope) or self.is_holder(node, module, scope)

    def rendered(self, node, module, scope):
        """The environment mappings a failure message prints when it prints `node` (the module docstring's list)."""
        if node is None:
            return []
        if isinstance(node, ast.Starred):
            node = node.value
        if self.renders_whole(node, module, scope):
            return [node]
        if isinstance(node, ast.Name):
            # a name bound to a value that renders one renders it: msg = "%r" % (env,), text = json.dumps(spec)
            s, values = self.lookup(scope, node.id)
            if s is None:
                return []
            mark = ("rendered", id(s), node.id)
            if mark not in self._names:
                self._names[mark] = False               # a name bound through itself reads its other bindings
                self._names[mark] = any(isinstance(v, ast.AST) and self.rendered(v, module, s) for v in values)
            return [node] if self._names[mark] else []
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
            if isinstance(n, _MAPPING_SHAPES) and (self.renders_whole(n, module, scope) or (
                    isinstance(n, ast.Name) and self.rendered(n, module, scope))):
                out.append(n)
                continue
            if not isinstance(n, SCOPES):
                stack.extend(ast.iter_child_nodes(n))
        return out

    def reads(self, node, module, scope):
        """(environment mappings, holders) `node` READS where a failure prints only a value, a bool or names (the
        population count of the safe forms): the receiver of X.get(k) or another mapping method, the container of a [k]
        read, the right side of `in` and `not in`, the argument of len, sorted, set, list or tuple."""
        n_reads, n_holders, stack = 0, 0, [node]
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
            for h in held:
                if self.is_env(h, module, scope):
                    n_reads += 1
                elif self.is_holder(h, module, scope):
                    n_holders += 1
            if not isinstance(n, SCOPES):
                stack.extend(ast.iter_child_nodes(n))
        return n_reads, n_holders

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
        # THE HOLDERS: what each module's text shows holding an environment mapping under an env key. An env key read,
        # set, deleted or tested on X shows it at once; a holder assigned to an attribute or a key, and an equality
        # between X and a holder, show it once the holders they read have settled.
        equal = []
        for m in modules:
            for sn, x in m.keyed:
                self.witness(x, m, m.scope(sn))
            for sn, a, b in m.equal:
                equal.append((m, m.scope(sn), a, b))
            # "env" in X tests a string or a set as readily as a mapping, so it shows a holder only where the module also
            # reads X by a string key or a view, which only a mapping takes (a name read so anywhere in the module)
            member = [(m.scope(sn), x) for sn, x in m.member]
            mapped = {self._identity(x) for _sn, x in m.mapped} - {None}
            for sn, x in m.sites:
                if not isinstance(x, ast.Call):
                    continue
                method, args = x.func.attr, list(x.args[:2])
                if method in ("assertIn", "assertNotIn") and args and env_word(_str_const(args[0])) and len(args) > 1:
                    member.append((m.scope(sn), args[1]))
                elif method in EQUALITIES:
                    kws = RENDERS[method][1]
                    args += [k.value for k in x.keywords if k.arg in kws]
                    if len(args) == 2:
                        equal.append((m, m.scope(sn), args[0], args[1]))
            for scope, x in member:
                if self._identity(x) in mapped:
                    self.witness(x, m, scope)
        holding = [(m, m.holder_attrs if isinstance(t, ast.Attribute) else m.holder_keys,
                    t.attr if isinstance(t, ast.Attribute) else _str_const(t.slice), v, sn)
                   for m in modules for sn, t, v in m.targets]
        self.forget()
        changed = True
        while changed:
            changed = False
            for m, bucket, name, value, sn in holding:
                if name not in bucket and self.is_holder(value, m, m.scope(sn)):
                    bucket.add(name)
                    changed = True
                    self.forget()
            for m, scope, a, b in equal:
                if (self.is_holder(a, m, scope) and self.witness(b, m, scope)) or \
                        (self.is_holder(b, m, scope) and self.witness(a, m, scope)):
                    changed = True
                    self.forget()
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


def _absent_value_reads(call, module, scope, reader):
    """The X.get(k) reads of an environment mapping X that an absent-value check prints: assertIsNone(X.get(k)),
    assertFalse(X.get(k)), assertEqual(X.get(k), None) and assertIs(X.get(k), None), either operand order. Each fails
    when the variable is PRESENT and then prints its value (THE RULE, A)."""
    method, operands = call.func.attr, []
    if method in ABSENT_CHECKS:
        operands = list(call.args[:1]) + [k.value for k in call.keywords if k.arg in RENDERS[method][1]]
    elif method in ABSENT_EQUALS:
        pair = list(call.args[:2]) + [k.value for k in call.keywords if k.arg in RENDERS[method][1]]
        if len(pair) == 2:
            operands = [b for a, b in (pair, pair[::-1]) if isinstance(a, ast.Constant) and a.value is None]
    return [o for o in operands if isinstance(o, ast.Call) and isinstance(o.func, ast.Attribute) and o.func.attr == "get"
            and o.args and reader.is_env(o.func.value, module, scope) and not reader.is_env(o, module, scope)]


def scan(module, reader):
    """(offences, stats) for one module. An offence is (file, line, rule, method, the mapping's text, the enclosing
    scope's qualified name, the assertion's text)."""
    offences, stats = [], {"reads": 0, "holder_reads": 0, "forms": {f: 0 for f in READ_FORMS}}
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
            hits += [("A", method, n) for n in _absent_value_reads(x, module, scope, reader)]
            for a in list(x.args) + [k.value for k in x.keywords]:
                n_env, n_holders = reader.reads(a, module, scope)
                stats["reads"] += n_env
                stats["holder_reads"] += n_holders
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
    offences, stats = [], {"files": len(paths), "reads": 0, "holder_reads": 0, "forms": {f: 0 for f in READ_FORMS}}
    for name in sorted(modules):
        off, st = scan(modules[name], reader)
        offences += off
        stats["reads"] += st["reads"]
        stats["holder_reads"] += st["holder_reads"]
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
    assert stats["holder_reads"], ("the census read no holder of an environment mapping at any assertion site in %d files: "
                                   "it reads no holder, so it proves nothing of them" % stats["files"])


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
    "absent-value-check": (_body('seen = {}', 'self.assertIsNone(seen["env"].get("X"), "X")',
                                 'self.assertFalse(os.environ.get("X"))', 'self.assertEqual(seen["env"].get("X"), None)',
                                 'self.assertEqual(None, os.environ.get("X", None))',
                                 'self.assertIs(seen["env"].get("X"), None, "X")'),
                           ['seen["env"].get("X")', 'os.environ.get("X")', 'seen["env"].get("X")',
                            'os.environ.get("X", None)', 'seen["env"].get("X")']),
    "prebuilt-message": (_body('msg = "%r" % (os.environ,)', 'self.assertTrue(False, msg)', 'env = dict(os.environ)',
                               'text = ", ".join(env.values())', 'assert False, text'), ["msg", "text"]),
    # the holders: a container that holds an environment mapping under an env key, one plant per way the text shows it
    "holder-display": (_body('import json', 'spec = {"sid": "s", "env": {"A": "1"}}',
                             'self.assertNotIn("X", json.dumps(spec), "the spec")', 'self.assertEqual(spec, {})',
                             'self.assertEqual(1, {"mode": "m", "env": {}})'),
                       ["spec", "spec", '{"mode": "m", "env": {}}']),
    "holder-builder-and-copy": (_body('import types', 'kw = dict(model="m", env={})', 'self.assertIn("model", kw)',
                                      'ns = types.SimpleNamespace(env={})', 'self.assertIsInstance(ns, dict)',
                                      'c = dict(kw, mode="x")', 'self.assertNotIn("X", c)',
                                      'self.assertNotIn("X", {**kw})', 'self.assertNotIn("X", kw.copy())'),
                                ["kw", "ns", "c", "{**kw}", "kw.copy()"]),
    "holder-key-set": (_body('kw = {"model": "m"}', 'kw["env"] = {}', 'self.assertNotIn("settings", kw)'), ["kw"]),
    "holder-key-read": (_body('kw = self._opts()', 'self.assertEqual(kw["env"]["A"], "1")',
                              'self.assertNotIn("settings", kw)'), ["kw"]),
    "holder-own-callee": ("import unittest\nclass T(unittest.TestCase):\n    def _opts(self):\n"
                          "        return self.be.launch_options()\n    def test_a(self):\n        kw = self._opts()\n"
                          "        self.assertTrue(kw['env'] == {}, 'the overlay')\n    def test_b(self):\n"
                          "        kw = self._opts()\n        self.assertIn('settings', kw)\n"
                          "        self.assertNotIn('model', self._opts())\n", ["kw", "self._opts()"]),
    "holder-attribute": (_body('s = mock.Mock()', 's._launching = {"mode": "m", "env": {}}', 'self.assertIsNone(s._launching)'),
                         ["s._launching"]),
    "holder-attribute-read": ("import unittest\nclass T(unittest.TestCase):\n    def test_a(self):\n"
                              "        self.assertTrue(self.s._shape['env'] == {}, 'm')\n    def test_b(self):\n"
                              "        self.assertIsNone(self.s._shape)\n", ["self.s._shape"]),
    "holder-key-binding": (_body('seen = {}', 'seen["opts"] = {"env": {}}', 'self.assertEqual(seen["opts"], {})'),
                           ['seen["opts"]']),
    "holder-membership": ("import unittest\nclass T(unittest.TestCase):\n    def _read(self):\n"
                          "        return self.store.row()\n    def test_x(self):\n        reg = self._read()\n"
                          "        self.assertEqual(reg.get('name'), 'web')\n        self.assertNotIn('env', reg)\n"
                          "        self.assertIn('env', self._read())\n", ["reg", "self._read()"]),
    "holder-equality-partner": (_body('got = self._load()', 'self.assertEqual(got, {"env": {}})',
                                      'self.assertIsInstance(got, dict)'), ["got", '{"env": {}}', "got"]),
    "holder-tuple-element": ("import json, unittest\nclass T(unittest.TestCase):\n    def _spec(self):\n"
                             "        spec = {'sid': 's', 'env': {}}\n        return 'path', spec\n    def _start(self):\n"
                             "        path, spec = self._spec()\n        return 1, 'sock', spec\n    def test_x(self):\n"
                             "        host, sock, spec = self._start()\n"
                             "        self.assertNotIn('X', json.dumps(spec), 'the spec')\n        self.assertEqual(sock, 'sock')\n",
                             ["spec"]),
    "holder-prebuilt-text": (_body('import json', 'spec = {"env": {}}', 'text = json.dumps(spec)',
                                   'self.assertNotIn("X", text, "the spec")'), ["text"]),
    "holder-bare-assert": (_body('spec = {"env": {}}', 'assert "X" not in spec', 'assert spec["sid"] == "s"',
                                 'assert sorted(spec) == ["env"]', 's = mock.Mock()', 's._shape = {"env": {}}',
                                 'assert "X" not in s._shape'), ["spec", "spec", "spec", "s._shape"]),
    # the clean shapes: what a failure prints is one value, a bool, or names
    "clean-get-read": (_body('seen = {}', 'self.assertEqual(seen["env"].get("X"), "1")',
                             'self.assertTrue(seen["env"].get("X") is None, "X")'), []),
    "clean-holder-fields": (_body('import json', 'kw = dict(model="m", env={})', 'self.assertEqual(kw["model"], "m")',
                                  'self.assertTrue("settings" in kw, "settings")', 'self.assertFalse("x" in kw, "x")',
                                  'self.assertEqual(sorted(kw), ["env", "model"])',
                                  'self.assertTrue(kw == {"env": {}}, "the options")',
                                  'self.assertTrue(kw["env"] == {}, "the overlay")', 'self.assertIsNone(kw.get("settings"))',
                                  'self.assertTrue(kw is not None, "kw")', 'self.assertIsNotNone(kw)',
                                  'self.assertFalse("X" in json.dumps(kw), "X")', 'has_env = "env" in kw', 'assert has_env'),
                            []),
    "clean-not-an-environment": (_body('row = {"env": {"standalone": True, "iosMajor": 17}}', 'self.assertEqual(row, {})',
                                       'steps = {"set_env": ["env"], "label_env": "x", "none_env": None}',
                                       'self.assertEqual(steps, {})', 'by = {"_no_env": {"A"}}', 'self.assertEqual(by, {})',
                                       'ns = dict(env="x")', 'self.assertEqual(ns, {})'), []),
    "clean-env-word-in-a-string": (_body('err = "bad env"', 'self.assertIn("env", err)', 'taint = set()',
                                         'self.assertIn("env", taint)', 'self.assertTrue("env" in err, "env")'), []),
    "clean-library-callee": (_body('import json', 'data = json.loads("{}")', 'self.assertTrue(data["env"] == {}, "m")',
                                   'other = json.loads("[]")', 'self.assertEqual(other, [])',
                                   'self.assertEqual(json.loads("{}"), {})'), []),
    "clean-same-name-other-class": ("import unittest\nclass A(unittest.TestCase):\n    def _reg(self):\n"
                                    "        return self.store()\n    def test_a(self):\n"
                                    "        self.assertTrue(self._reg()['env'] == {}, 'm')\nclass B(unittest.TestCase):\n"
                                    "    def _reg(self):\n        return (1, 2)\n    def test_b(self):\n"
                                    "        self.assertEqual(self._reg(), (1, 2))\n", []),
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
    "limit-list-index-absent-value": (_body('calls = [(["claude"], dict(os.environ))]', 'cmd, env = calls[0]',
                                            'self.assertIsNone(env.get("X"))'), []),
    "limit-prebuilt-elsewhere": (_body('self.msg = "%r" % (os.environ,)', 'self.assertTrue(False, self.msg)'), []),
    "limit-options-object": (_body('opts = make_options(env=dict(os.environ))', 'self.assertEqual(opts.env.get("A"), "1")',
                                   'self.assertIsInstance(opts, dict)'), []),
    "limit-holder-by-membership-alone": (_body('body = self.post()', 'self.assertNotIn("env", body)'), []),
    "limit-tuple-element-shown-elsewhere": ("import unittest\nclass T(unittest.TestCase):\n    def _post(self):\n"
                                            "        return 200, self.client.post()\n    def test_a(self):\n"
                                            "        code, body = self._post()\n"
                                            "        self.assertTrue(body['env'] == {}, 'm')\n    def test_b(self):\n"
                                            "        code, body = self._post()\n        self.assertIsNone(body)\n", []),
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
        print("ENVMAP files=%d, env reads at assertion sites=%d, holder reads=%d, bindings by form: %s, offences=%d, "
              "exempt=%d" % (stats["files"], stats["reads"], stats["holder_reads"],
                             ", ".join("%s %d" % kv for kv in stats["forms"].items()), len(offences), len(EXEMPT)),
              file=sys.stderr)

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

    def test_a_product_function_shown_to_return_a_holder_is_read_in_every_module(self):
        """read_reg's return is the same whoever calls it: one module's text showing it holds an env key makes the call a
        holder in every module; with no product function of that name nothing is marked (a library name never is)."""
        root = tempfile.mkdtemp(prefix="envmap-census-")
        self.addCleanup(shutil.rmtree, root, True)
        os.makedirs(os.path.join(root, "tests"))
        with open(os.path.join(root, "tests", "test_reads_env.py"), "w") as f:
            f.write("import unittest\nclass T(unittest.TestCase):\n    def test_x(self):\n"
                    "        self.assertTrue(sb.read_reg('d', 's').get('env') == {}, 'the stored env')\n")
        with open(os.path.join(root, "tests", "test_prints_reg.py"), "w") as f:
            f.write("import unittest\nclass T(unittest.TestCase):\n    def test_y(self):\n"
                    "        reg = sb.read_reg('d', 's')\n        self.assertNotIn('auth', reg)\n"
                    "        self.assertIsNone(sb.read_reg('d', 't'))\n")
        _files, offences, _stats = census(root)
        self.assertEqual(offences, [], "no product module: read_reg resolves to nothing, so nothing is marked")
        os.makedirs(os.path.join(root, "kernel"))
        with open(os.path.join(root, "kernel", "sdk_backend.py"), "w") as f:
            f.write("import json\ndef read_reg(d, sid):\n    return json.loads(open(d).read())\n")
        _files, offences, _stats = census(root)
        self.assertEqual([(o[0], o[1], o[4]) for o in offences],
                         [(os.path.join("tests", "test_prints_reg.py"), 5, "reg"),
                          (os.path.join("tests", "test_prints_reg.py"), 6, "sb.read_reg('d', 't')")])
        # shown through a helper: _reg(...)'s env key read, and _reg returns sb.read_reg(...), shows read_reg's return
        with open(os.path.join(root, "tests", "test_reads_env.py"), "w") as f:
            f.write("import unittest\nclass T(unittest.TestCase):\n    def _reg(self):\n"
                    "        return sb.read_reg('d', 's')\n    def test_x(self):\n"
                    "        self.assertTrue(self._reg()['env'] == {}, 'the stored env')\n")
        _files, offences, _stats = census(root)
        self.assertEqual([(o[0], o[1], o[4]) for o in offences],
                         [(os.path.join("tests", "test_prints_reg.py"), 5, "reg"),
                          (os.path.join("tests", "test_prints_reg.py"), 6, "sb.read_reg('d', 't')")])

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
        require_population(dict(stats, reads=1, holder_reads=1))

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
            require_population({"files": 1, "reads": 0, "holder_reads": 1, "forms": {f: 1 for f in READ_FORMS}})
        with self.assertRaisesRegex(AssertionError, "read no holder of an environment mapping at any assertion site"):
            require_population({"files": 1, "reads": 1, "holder_reads": 0, "forms": {f: 1 for f in READ_FORMS}})
        _f, _o, stats = _plant_scan(_body('kw = dict(env={})', 'self.assertTrue("settings" in kw, "settings")',
                                          'self.assertEqual(kw["model"], "m")', 'self.assertEqual(sorted(kw), [])'))
        self.assertEqual(stats["holder_reads"], 3, "a membership bool, a field and the sorted names each read the holder")

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
        print("files %d; env reads at assertion sites %d; holder reads %d; bindings by form: %s"
              % (stats["files"], stats["reads"], stats["holder_reads"],
                 ", ".join("%s %d" % kv for kv in stats["forms"].items())))
        left, stale = split_exempt(offences, EXEMPT)
        print("offences %d (exempt %d, stale entries %d)" % (len(left), len(offences) - len(left), len(stale)))
        print(_lines(left, cap=len(left) or 1))
    else:
        unittest.main()
