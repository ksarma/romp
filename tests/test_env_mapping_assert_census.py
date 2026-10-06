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
by the census itself (THE PARSE). A test tree with no tests/*.py fails the run, and so does one in which the census finds
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
     render their message keyword alone. Any other method whose name begins with `assert` is read as rendering every
     argument it is handed: a helper a module defines (assertEnvClean, assert_no_leak), and mock's assert_called_with,
     assert_called_once_with, assert_any_call and their awaited forms, whose failure can print the expected call's
     arguments (what it can print of the calls the mock recorded is WHAT IT CANNOT SEE, as are the arguments
     of a call object, mock.call(...), in the list assert_has_calls takes or in any other assertion method's
     arguments). An absent-value check over one variable's read renders the
     VALUE (_absent_value_reads): assertIsNone(R), assertFalse(R), assertEqual(R, M) and assertIs(R, M) in either
     operand order, where M is an absent marker (None or ""), and assertIn(R, D), where D is a tuple, list or set
     display of markers such as (None, ""), fail when the variable holds a value, and then print it. R is X.get(k[, d]),
     X.pop(k[, d]) or X.setdefault(k[, d]) of an environment mapping X, os.getenv(k[, d]) by any spelling of the os
     module, or getenv(k) imported from os.
  F  fail and skipTest render their message (pytest.fail's reason included).
  B  a bare assert renders every environment mapping anywhere in its test or its message: pytest's rewrite explains a
     call by printing its arguments and an attribute by printing its receiver, so even `assert env.get(n) is None`
     prints the mapping, as the receiver of the bound method it explains. A getenv read holds no mapping, but pytest
     prints the value it returns: `assert os.getenv(n) is None`, `assert None == getenv(n)`,
     `assert os.getenv(n) == ""`, `assert os.getenv(n) in (None, "")` and `assert not os.getenv(n)` each print it
     (_bare_absent_getenv).
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
  every subscript of X, under any key, and X.get(k), X.pop(k) and X.setdefault(k) under any key, where an assignment
  X[k] = M stores an environment mapping M under a key k that is not a string constant: a capture helper's seen[slot]
  = dict(kwargs["env"]) makes seen["probe"], seen[slot] and seen.get("probe") one, and seen.get("probe").get(name)
  an absent-value check's read. A name X is matched to the scope that binds it, as Python resolves the name at the
  assignment (the helper's seen is the test's seen); an attribute X is matched by its name, module-wide. X itself, a
  copy of X and a view of X are read too (THE CONTAINERS);
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
  every subscript of X, and X.get(k), X.pop(k) and X.setdefault(k), where X[k] = H stores a holder H under a key that
  is not a string constant, read as THE MAPPINGS read X[k] = M;
  a call: of a function of the tree that returns a holder, or that the text shows returns one (by function: self.f()
  resolves to the enclosing class's own method first, so two classes' _reg helpers stay apart), whose own return is
  then shown in turn (a _reg helper returning sb.read_reg(...) shows read_reg's return); of a product function
  the text of ANY module shows returns one (sb.read_reg, be._options), since its return is the same whoever calls it;
  never of a library function by its name (json.loads(path)["env"] shows that call and the name bound to it, not every
  json.loads);
  an element of a tuple target bound from a call (host, sock, spec = self._start(...)), read through the callee's
  `return a, b, c`.
A view of a holder, H.items() or H.values(), and sorted, list, tuple, set or frozenset of one, is not itself a holder,
but it carries the environment the holder holds and renders it the same way (_carrying_view); H.keys() prints names
only.
THE CONTAINERS, one rule for both keyings and both kinds: where an assignment X[k] = V stores an environment mapping
or a holder V under any key, a string constant or not (seen[slot] = dict(kwargs["env"]), seen["child"] =
dict(os.environ), opts[name] = dict(model=m, env=E)), X carries every entry, and a failure that prints X prints each.
So X itself renders where a holder renders (_container, which renders_whole consults beside is_holder): in every
position RENDERS lists, in a bare assert's test or message, and through every formatting road of THE RULE
(assertEqual(seen, {...}), assert seen == {}, "%r" % (seen,), msg = repr(seen)[:80]). A copy of X renders the same
way: X.copy(); dict, copy.copy, copy.deepcopy, OrderedDict, ChainMap or MappingProxyType of X (COPIERS), positional
or as **X; and {**X, ...}, a display whose element X renders. A view of X carries every entry, as a holder's view does:
X.items() and X.values(), and sorted, list, tuple, set or frozenset of one (_carrying_view). In an assertion method's
arguments these are not read (WHAT IT CANNOT SEE): a walrus over X; a merge (X | other), a dict comprehension over X and
SimpleNamespace(**X); a copy or a view of an `or`, a conditional, a walrus, a name bound to X or to a copy of X, or a
display that splats X; a view of a copy of X; and X stored in another container. A name X is matched to the scope that
binds it and an attribute X by its name, module-wide, as for the subscripts above. In an assertion method's arguments,
what prints only X's names or a count is safe, as for a mapping: len(X), sorted(X), set(X), list(X), tuple(X), X.keys()
and those of it, `k in X` inside assertTrue or assertFalse, and a join over X itself. A bare assert reads X wherever its
test or message holds it, these forms included, as it reads a mapping (B). A subscript or a keyed read of X keeps the
reading THE MAPPINGS and THE HOLDERS give it: after X[k] = V under a key that is not a string constant, every subscript
and keyed read of X; after X["child"] = V, a read by the key "child", module-wide (WHAT IT CANNOT SEE).
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
  the calls a mock RECORDED, with their arguments: a failure of assert_not_called or assert_called_once prints each
  recorded call, and a failure of assert_called_with, assert_called_once_with,
  assert_has_calls or their awaited forms can print them too, beside the expected call (assert_called,
  assert_not_awaited, assert_awaited_once, assert_any_call and assert_any_await print none), so a mock patched over a
  spawn prints the env= keyword the product handed it, which no argument of the assertion holds
  (tests/test_judge_auth_billing.py, run = patch.object(jd.subprocess, "run") in
  RuntimeJudgeBilling.test_exhausted_login_window_pauses_without_launching,
  RuntimeJudgeBilling.test_codex_call_never_resolves_or_carries_an_anthropic_credential and
  CredentialErrorNote.test_an_unexpected_env_failure_never_quotes_its_cause_and_never_falls_back_to_ambient_auth, each
  a form with no argument; now assertEqual(run.call_count, N, msg), which prints two counts). The expected call an
  argument-taking form is handed is read (THE RULE, A);
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
  a mapping, a holder or a container reached through a parameter (a helper handed env by its caller), a list index
  (captured.append(env); captured[0]), getattr, or an attribute or key whose name is neither an env word nor assigned
  an environment mapping in the module (s.env_vars, a per-session overlay, is not read);
  in an assertion method's arguments, a subscript or a keyed read of a container whose entries are stored under string
  constants, by a key that is not that constant's text: after byname["child"] = dict(os.environ), byname["child"] and
  byname.get("child") are read, and byname[k] and byname.get(k) with k = "child" are not, where after seen[slot] = ...
  every subscript and keyed read of seen is, but not one through a name bound to seen, a copy of seen or a walrus over
  it (alias = seen, then alias["probe"] or alias.get("probe"); dict(seen)["probe"]; (got := seen)["probe"]), though the
  same reads of byname by "child" are read, since that key is read module-wide. A bare assert reads the container in
  each, since its test holds it (B);
  a container the text fills by a road other than an assignment X[k] = V to a name or an attribute (a dict
  comprehension, {k: dict(os.environ) for k in ks}; X.update(...); X.setdefault(k, V); a nested target, X[a][k] = V),
  and a container a call returns (got = self._capture(), where _capture fills and returns its own seen): none is read,
  printed whole or through a view, by an assertion method or a bare assert. In an assertion method's arguments, a copy
  rebuilt from a view of a holder or a container (dict(X.items())) is not read, and a dict display that holds a mapping,
  or a name bound to one, is read printed whole, element by element, as THE RULE reads a display, but not through its
  views and subscripts; a bare assert reads each of these, through the view or the display it holds (B). On 2026-10-06
  no assertion in the tree prints one of these;
  a container X printed by an assertion method through a spelling the census reads there for a mapping, a holder or
  both, but not for X: a walrus over X, as the operand or inside a formatting road ((got := X),
  "%r" % ((got := X),)); a merge (X | other, other | X) or a dict comprehension over X ({k: X[k] for k in X}), read
  for a mapping only; SimpleNamespace(**X), read for a holder only; a copy or a view of an `or`, a conditional, a
  walrus, a name bound to X or to a copy of X, or a display that splats X (dict(X or {}), dict(**(X if s else {})),
  dict((got := X)), alias = X then dict(alias), alias.copy() or alias.values(), c = dict(X) then dict(c) or
  c.items(), dict({**X}), (X or {}).values(), {**X}.items()); a view of a copy of X (dict(X).values(),
  X.copy().items()); and X stored in another container (outer["a"] = X, then outer printed whole). The `or`, the
  conditional, the alias, a name bound to a copy, the name a walrus binds and the display, each printed itself, are
  read, and a bare assert reads X in each of these but the last, where it holds only outer. On 2026-10-06 no
  assertion in the tree writes one of these over a container: the walrus, the merge, the dict comprehension and a
  copy of a conditional, an alias or a display appear at assertion sites over other values only;
  a read wrapped in `or` before an absent-value check (assertEqual(os.getenv(k) or "", ""), assertIsNone(env.get(k)
  or None)): the check prints the value when the variable is set, and the census reads only a bare read;
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
  a view of a mapping, a holder or a container bound to a name and then iterated (pairs = env.items(); sorted(pairs),
  or ", ".join(vals) after vals = env.values()), a comprehension over a holder's or a container's view ([v for v in
  kw.values()]; one over a mapping's view is read), a join whose comprehension reads the values through the keys
  (", ".join(k + "=" + env[k] for k in env)), and a formatted mapping passed through another call
  (repr(env).replace(...), map(str, env.values()));
  a mapping, a holder or a container in a call object (mock.call(["claude"], env=env)) in an assertion method's
  arguments: in the list assert_has_calls or assert_has_awaits takes, whose failure prints each expected call with
  its arguments, or in an equality or a membership test over the calls a mock recorded
  (assertEqual(run.call_args, mock.call(...)), assertIn(mock.call(...), run.call_args_list)), whose failure prints
  the call object. The census reads a list or a tuple as a display but not a call object's arguments; a bare assert
  reads them (B). On 2026-10-06 no test in the tree calls assert_has_calls or assert_has_awaits, and the one
  assertion over call objects compares pids (tests/test_restart_cuts.py);
  Python inside a string (a planted module a test writes and runs, whose bare assert over os.environ renders under
  that run's own conftest);
  a mapping printed by print(), logging, a raise or a subprocess's output a test asserts on;
  a mapping, a holder or a container handed to a subtest as its message or a keyword parameter, through unittest's
  subTest (with self.subTest(env=env)) or pytest's built-in subtests fixture (with subtests.test(msg, env=env)): a
  failure inside the block prints the parameters in pytest's subtest header and SUBFAILED summary line, and a subTest
  in unittest's FAIL header too (pytest cuts a keyword parameter's repr to 240 characters). pytest builds both from the
  subtest's parameters, not the report's longrepr, so tests/conftest.py's net does not redact them under pytest
  either, nor, in a subtests.test block, the stdout, stderr and log captured inside it, which pytest adds to the
  report after the hook runs. On 2026-10-06 no subTest call in the tree passes one, and the tree has no subtests.test
  call;
  a local variable shown in a traceback: pytest's -l (--showlocals) prints the locals of every frame a failure passes
  through, and unittest's --locals does the same, so a frame that holds an environment copy (HostProcess._start's
  env = _host_env(...) in tests/test_session_host.py) prints it whatever its assertion renders. The conftest net
  redacts values of 16 characters or more, and only under pytest; shorter values, and every value under unittest,
  print in the clear;
  a message built from a mapping in another function, or kept on an attribute or a key (self.msg = "%r" % env): a
  name in scope is the one binding followed.
PLANTS pins each shape it reads, red or green, and the stated limits a reader would most expect it to see (a parameter,
a list index, a mapping read back from a child's dump, a for target over captured pairs, the calls a mock recorded, a
call object in an assertion's arguments, a subTest parameter, a view bound to a name, a comprehension over a holder's or
a container's view, values read through the keys, a formatted mapping passed through another call, an options object
holding the environment as an attribute, a holder known only by a membership test, a holder bound as a tuple element
that only another test shows, a container filled by another road, returned by a call or rebuilt from a view, a dict
display's view and subscript, a container printed through a walrus, a merge, a dict comprehension, SimpleNamespace(**X),
a copy or a view of another spelling or a view of a copy, or stored in another container, a string-key container read by
a key that is not its constant or a variable-key one read through an alias, a copy or a walrus, a read wrapped in `or`
before an absent-value check, and Python a test writes as a string, in both idioms the tree uses: a written constant and
a textwrap.dedent module).

THE PARSE (2026-10-06; the shape tests/test_obsidian_state_routes.py's census calls E, and this module's exception to
tests/parse_cache.py's rule that the AST censuses under tests/ parse through its one process-wide cache). The census
parses every file itself (_own_tree) and never through tests/parse_cache.py: not its shared parse, whose cache keeps
every tree for the rest of the process, and not its derived(), which keeps the value for the process and freezes every
object tracked when the build returns. Built that way (at 99c9ea824) the module left its trees in the process that ran
it: in one cold process on Python 3.11.15 the resident set went from 52 to 1867 MiB over the module's tests and stayed
there, with 8.16 million objects frozen. On a local copy of CI's Python 3.11 cell (two workers) that step put the run's
peak about 1 GiB above main's, 18.2 against 17.2 GiB, and on CI that cell's 16 GB runner shut down near the end of the
run in four attempts of five at that head (the other was cancelled), where the local copy, with no such ceiling, ran
to the end. Now census() returns facts alone (strings, numbers and the lists, tuples and dicts around them), and its
_Module records, their scopes and the Reader refer to their trees and never back to themselves, so every tree is
freed by reference count when census() returns. The whole-tree build (_build_census) runs once per module run, in the
first test that reads it, and EnvMappingAssertCensus.held keeps its facts until the class's tearDownClass. What the
module's tests leave in the process depends on the interpreter: about 0.4 to 0.5 GiB on Python 3.11, about 1.3 GiB on
3.12 to 3.14 and about 1.5 GiB on 3.14 free-threaded, against about 1.8, 1.9 and 2.0 GiB at 99c9ea824. In MiB above the
resident set the tests found, one cold process per run, each range over every run measured: on 3.11.15, 363 to 529 (258
to 411 after a gc.collect()), against 1815 to 1827; on 3.12.3, 3.13.14 and 3.14.6, 1267 to 1321, against 1882 to 1905;
on 3.14.6 free-threaded, 1514 to 1563, against 2050 to 2055. On every interpreter no tree is alive afterwards: what
stays is the allocator's arenas that still hold a live block each, and the peak inside the build is unchanged (about 1.9
GiB on 3.11). 3.12 and later keep more because the identifiers the parser interns outlive the trees that held them and
keep those arenas: sys.intern of a rebuilt copy returns the parser's object on 3.12, 3.13 and 3.14, and 3.14's
sys._is_immortal reports it immortal. Parsing every tests/, kernel/, postal/ and cli/ file, dropping the trees and
running a gc.collect() leaves 50,444 to 50,838 more live blocks and 1044 to 1078 MiB on 3.12 to 3.14 (50,921 to 50,957
blocks and 1568 to 1650 MiB on 3.14t), against 232 to 306 blocks and 254 to 313 MiB on 3.11, where the identifiers go
with the trees. On 3.11, keeping only the tree's 51,894 identifier strings alive after dropping the trees leaves 968 MiB
(one run).
THE COLLECTOR is left as the process has it, as the obsidian census leaves it (the reviewer's ruling on round 1 of fork
PR #909: no gc.freeze or gc.disable, which change the collector's state for the whole process, and no gc.collect, which
walks every tracked object). The cost is time, since the automatic collections walk the trees while the build allocates
them: the module's tests took 32.6 to 33.0 s in three of those 3.11.15 runs, against 12.1 to 12.6 s in three runs at
99c9ea824 measured with them, where derived() held the collector off for the build, and 13.4 to 13.8 s with the
collector held off for census() alone, which leaves the same memory behind (484 to 508 MiB). What the exception costs
besides: tests/test_ephemeral_port_census.py and tests/test_lab_ports_census.py read some of the tests/ modules through
tests/parse_cache.py by the same import road (`import parse_cache`), so in a process that runs them after this module
they parse those files themselves, as they did before this census existed. tests/test_thread_stop_census.py imports the
cache as tests.parse_cache under pytest, a module object of its own, so it never shared this census's trees there. In
one process running this module, those two and the thread-stop census in collection order on Python 3.11.15, the two
parsed 286 files themselves and added 273 MiB, and the resident set after the last of the four was 2756 MiB, against
3642 at 99c9ea824.
THE RULE FOR THE BUILD: it leaves no cycle behind, so that the trees go by reference count with no collection. Measured
over the whole tree on Python 3.10, 3.11, 3.12 and 3.13, with the collector off from before census() to after the
reads: no tree was alive once census() had returned, and a collection then found nothing unreachable.
THE PINS: test_the_census_is_built_once_from_its_own_parse_and_holds_no_tree (nothing built or parsed before the
module's first test, one build in the module's run, every tests/*.py and each file the build read parsed once by its own
parse, the facts plain data with no node in them, and no tree alive once census() had returned, read through weak
references that the build drops before it returns), and tearDownModule (no freeze in the module's run, and the facts
gone after the class, a weak reference read with no collection). The singleton check that derived() ran around the
build still runs around it (_build_census). What no pin sees, both measurements only: a record of the parse kept past
the build, which holds no tree and, on 3.11, costs the allocator's arenas (_build_census gives the figures), and the
collector held off around the build and given back, which changes no count a pin reads (the 13.4 to 13.8 s runs above
passed every test).

Synthetic: reads the tree only; no environment value is read or printed.
"""
import ast
import collections
import gc
import glob
import os
import re
import shutil
import sys
import tempfile
import unittest
import weakref

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import parse_cache                                  # noqa: E402  check_singletons alone; the census parses its own trees (THE PARSE)

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

_PARSES = 0           # the files _own_tree has parsed in this process, the whole-tree build's and every plant's
_RECORD = None        # while _build_census runs census(ROOT): (path, a weak reference to its tree) per parse; else None
_CENSUS_BUILDS = 0    # the whole-tree censuses _build_census started in this process (one that raised is counted too)
_CENSUS_REF = None    # a weak reference to the facts EnvMappingAssertCensus.held holds (_census_here), pin (2)'s subject
_FROZEN_BEFORE = None  # gc.get_freeze_count() before the module's first test (setUpModule), pin (1)'s first read
_BUILT_BEFORE = None  # (censuses built, files parsed) before the module's first test (setUpModule), which the mechanism
#                       pin requires to be (0, 0)
_BUILDS_AT_SETUP = None  # _CENSUS_BUILDS when setUpModule last ran


def _own_tree(path, rel):
    """(text, tree) of the file at `path`, parsed here with `rel` as the filename the tree carries (for a SyntaxError's
    message): the census's OWN parse, never tests/parse_cache.py's (THE PARSE in the module docstring), counted in
    _PARSES and, while the whole-tree build runs, recorded in _RECORD with a weak reference to the tree, which keeps
    nothing alive. Read-only all the same: no attribute is written on a node (the parser shares its singleton nodes, a
    Load or an operator, with every tree in the process); per-node data lives in the census's tables keyed by id(node)."""
    global _PARSES
    with open(path, encoding="utf-8") as f:
        text = f.read()
    tree = ast.parse(text, filename=rel)
    _PARSES += 1
    if _RECORD is not None:
        _RECORD.append((path, weakref.ref(tree)))
    return text, tree


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
    `assert`: a helper a module defines, assertEnvClean or assert_no_leak, and mock's assertion methods, whose
    argument-taking forms can print the expected call, assert_called_once_with(["claude"], env=E) and the rest) or a
    bare assert. scan() reads every argument of a call outside RENDERS and NON_RENDERING (THE RULE, A). Mock's forms
    with no argument (assert_not_called, assert_called_once) leave nothing to read: the calls the mock recorded, which
    they print, are WHAT IT CANNOT SEE."""
    if isinstance(node, ast.Assert):
        return True
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        m = node.func.attr
        return m in RENDERS or m in NON_RENDERING or m.startswith("assert")
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
        self.slots = []                   # (scope node, X, value) for X[k] = value, k not a string constant, X a name or attribute
        self.getenv_names = set()         # the names `from os import getenv [as name]` binds, anywhere in the module
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
                            elif isinstance(tg, ast.Subscript) and isinstance(tg.value, (ast.Name, ast.Attribute)):
                                self.slots.append((sn, tg.value, n.value))
                        self.values.append((sn, n.value))
                    elif t is ast.NamedExpr:
                        self.values.append((sn, n.value))
                    elif t is ast.withitem and n.optional_vars is not None:
                        self.values.append((sn, n.context_expr))
                    elif t is ast.Import:
                        self.imports.update(a.name.split(".")[-1] for a in n.names)
                    elif t is ast.ImportFrom:
                        if n.module == "os" and not n.level:
                            self.getenv_names.update(a.asname or a.name for a in n.names if a.name == "getenv")
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
        # attribute names X whose every subscript is an environment mapping, or a holder, because the module assigns
        # X[k] = one under a key that is not a string constant (a name X is marked per scope, on the Reader)
        self.slot_attrs, self.holder_slot_attrs = set(), set()
        # attribute names X whose views carry an environment because the module assigns X[k] = an environment mapping or
        # a holder under any key (THE CONTAINERS; a name X is marked per scope, on the Reader)
        self.container_attrs = set()

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
        # (id(scope), name): a name X whose every subscript is an environment mapping, or a holder, because X[k] = one is
        # assigned under a key that is not a string constant (seen[slot] = dict(kwargs["env"]) makes seen["probe"] one)
        self.env_slots, self.holder_slots = set(), set()
        # (id(scope), name): a name X whose views carry an environment, because X[k] = an environment mapping or a
        # holder is assigned under any key, a string constant or not (THE CONTAINERS)
        self.containers = set()
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
                text, tree = _own_tree(p, os.path.relpath(p, self.root))
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

    def slot_key(self, x, scope):
        """What marks X for X[k] = V under a key that is not a string constant: a name by the scope that binds it, as
        Python reads it from `scope` (the capture helper's seen[slot] and the test's seen["probe"] reach one binding);
        an attribute by its name, module-wide; None for a name bound nowhere or any other X."""
        if isinstance(x, ast.Name):
            s, _ = self.lookup(scope, x.id)
            return None if s is None else (id(s), x.id)
        if isinstance(x, ast.Attribute):
            return x.attr
        return None

    def _slotted(self, x, scope, names, attrs):
        """X is marked in `names` (a name) or `attrs` (an attribute's name): X[k] = V stored one under a key that is not
        a string constant."""
        k = self.slot_key(x, scope)
        return k is not None and (k in names if isinstance(x, ast.Name) else k in attrs)

    def _slot(self, node, scope, names, attrs):
        """node is X[...], any key, and X is marked (_slotted)."""
        return self._slotted(node.value, scope, names, attrs)

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
            return (key is not None and (env_word(key) or key in module.keys)) or \
                self._slot(node, scope, self.env_slots, module.slot_attrs)
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
                # X.get(k), X.pop(k), X.setdefault(k) of X whose every entry is one (X[k] = M under a variable key)
                if self._slotted(f.value, scope, self.env_slots, module.slot_attrs):
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
            return (key is not None and key in module.holder_keys) or \
                self._slot(node, scope, self.holder_slots, module.holder_slot_attrs)
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
                return (key is not None and key in module.holder_keys) or \
                    self._slotted(f.value, scope, self.holder_slots, module.holder_slot_attrs)
            if f.attr in MAPPING_METHODS + ("keys",) + VIEWS:
                # a mapping's own method: one value, its names, a view, or None, never the holder itself; a holder's
                # items() or values() view still carries the environment it holds and renders it (_carrying_view)
                return False
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

    def _carrying_view(self, node, module, scope):
        """X.items() or X.values(), or sorted, list, tuple, set or frozenset of one, where X is a holder or a container
        whose entries are environment mappings or holders (THE CONTAINERS: X[k] = one under any key, a string constant
        or not): the view carries the environment the holder, or each entry, holds."""
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in SEQUENCES and node.args:
            node = node.args[0]
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in VIEWS
                and not node.args):
            return False
        x = node.func.value
        return self.is_holder(x, module, scope) or self._slotted(x, scope, self.containers, module.container_attrs)

    def _container(self, node, module, scope):
        """X itself, a name or an attribute whose entries are environment mappings or holders (THE CONTAINERS: X[k] =
        one under any key, a string constant or not), or a copy of X: X.copy(), or a COPIERS call with X positional or
        as **X (dict(X), dict(**X), copy.deepcopy(X)): a failure that prints it prints every entry. {**X, ...} needs no
        branch here: a display renders its elements (rendered()). Not read (WHAT IT CANNOT SEE): a walrus, a merge, a
        dict comprehension, SimpleNamespace(**X), a copy of an `or`, a conditional, a walrus, an alias, a name bound to
        a copy or a display, and a view of a copy or of any of those."""
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute) and node.func.attr == "copy" and not node.args:
                return self._container(node.func.value, module, scope)
            return _callee(node) in COPIERS and (any(self._container(a, module, scope) for a in node.args) or any(
                k.arg is None and self._container(k.value, module, scope) for k in node.keywords))
        return self._slotted(node, scope, self.containers, module.container_attrs)

    def renders_whole(self, node, module, scope):
        """An environment mapping, a holder of one, a container of either (_container), or a view that carries one
        (_carrying_view): a failure that prints it prints the environment."""
        return (self.is_env(node, module, scope) or self.is_holder(node, module, scope)
                or self._container(node, module, scope) or self._carrying_view(node, module, scope))

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
        module (a callee in one module can read another's), then memoisation on, then the containers."""
        self.settled = False
        pending = [(m, m.attrs if isinstance(t, ast.Attribute) else m.keys,
                    t.attr if isinstance(t, ast.Attribute) else _str_const(t.slice), v, sn)
                   for m in modules for sn, t, v in m.targets]
        # X[k] = V under a key that is not a string constant: X's every subscript is what V is (a name in the scope that
        # binds it, an attribute's name module-wide)
        slots = []
        for m in modules:
            for sn, x, v in m.slots:
                k = self.slot_key(x, m.scope(sn))
                if k is not None:
                    slots.append((m, m.scope(sn), k, isinstance(x, ast.Name), v))
        changed = True
        while changed:
            changed = False
            for m, bucket, name, value, sn in pending:
                if name not in bucket and self.is_env(value, m, m.scope(sn)):
                    bucket.add(name)
                    changed = True
                    self.forget()                       # a callee or a name read before the set grew is read again
            for m, scope, k, named, value in slots:
                bucket = self.env_slots if named else m.slot_attrs
                if k not in bucket and self.is_env(value, m, scope):
                    bucket.add(k)
                    changed = True
                    self.forget()
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
            for m, scope, k, named, value in slots:
                bucket = self.holder_slots if named else m.holder_slot_attrs
                if k not in bucket and self.is_holder(value, m, scope):
                    bucket.add(k)
                    changed = True
                    self.forget()
            for m, scope, a, b in equal:
                if (self.is_holder(a, m, scope) and self.witness(b, m, scope)) or \
                        (self.is_holder(b, m, scope) and self.witness(a, m, scope)):
                    changed = True
                    self.forget()
        self.forget()
        self.settled = True
        # THE CONTAINERS, one rule for both keyings: X[k] = V stores an environment mapping or a holder V under a key
        # that is not a string constant (seen[slot] = dict(kwargs["env"])) or under one that is (seen["child"] =
        # dict(os.environ)), so X itself, a copy of X and a view of X carry every entry (_container, _carrying_view).
        # Read once the mappings and the holders have settled: a mark makes X neither, and only renders_whole and
        # _carrying_view consult it, so marking X changes no other reading.
        for m in modules:
            stored = m.slots + [(sn, t.value, v) for sn, t, v in m.targets
                                if isinstance(t, ast.Subscript) and isinstance(t.value, (ast.Name, ast.Attribute))]
            for sn, x, v in stored:
                scope = m.scope(sn)
                k = self.slot_key(x, scope)
                if k is not None and (self.is_env(v, m, scope) or self.is_holder(v, m, scope)):
                    (self.containers if isinstance(x, ast.Name) else m.container_attrs).add(k)


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


def _getenv_read(node, module):
    """One variable's read by getenv: os.getenv(k) by any spelling of the os module (the attribute getenv on a name, as
    _is_os_environ reads environ: o.getenv after `import os as o`), or getenv(k) where `from os import getenv [as name]`
    binds the name."""
    if not (isinstance(node, ast.Call) and node.args):
        return False
    f = node.func
    return ((isinstance(f, ast.Attribute) and f.attr == "getenv" and isinstance(f.value, ast.Name))
            or (isinstance(f, ast.Name) and f.id in module.getenv_names))


def _absent_marker(node):
    """A value an absent-value check compares a read with to mean "not set": the constant None or the empty string."""
    return isinstance(node, ast.Constant) and (node.value is None or node.value == "")


def _absent_markers(node):
    """A non-empty tuple, list or set display made only of absent markers: (None, ""), [""]."""
    return isinstance(node, (ast.Tuple, ast.List, ast.Set)) and bool(node.elts) and all(map(_absent_marker, node.elts))


def _absent_value_reads(call, module, scope, reader):
    """The reads of one variable that an absent-value check prints: X.get(k), X.pop(k[, d]) and X.setdefault(k[, d]) of
    an environment mapping X, and os.getenv(k) or getenv(k) (_getenv_read), under assertIsNone, assertFalse,
    assertEqual(..., M) and assertIs(..., M) with an absent marker M (None or ""), either operand order, and
    assertIn(..., (None, "")) with a display of markers. Each fails when the variable holds a value and then prints
    it (THE RULE, A)."""
    method, operands = call.func.attr, []
    if method in ABSENT_CHECKS:
        operands = list(call.args[:1]) + [k.value for k in call.keywords if k.arg in RENDERS[method][1]]
    elif method in ABSENT_EQUALS or method == "assertIn":
        # the keywords in their parameters' order, so assertIn(container=..., member=R) pairs as assertIn(R, ...)
        pair = list(call.args[:2]) + [k.value for kw in RENDERS[method][1] for k in call.keywords if k.arg == kw]
        if len(pair) == 2 and method == "assertIn":
            operands = [pair[0]] if _absent_markers(pair[1]) else []
        elif len(pair) == 2:
            operands = [b for a, b in (pair, pair[::-1]) if _absent_marker(a)]
    return [o for o in operands if _getenv_read(o, module) or (
        isinstance(o, ast.Call) and isinstance(o.func, ast.Attribute) and o.func.attr in KEYED and o.args
        and reader.is_env(o.func.value, module, scope) and not reader.is_env(o, module, scope))]


def _bare_absent_getenv(test, module):
    """The getenv read (_getenv_read) a bare absent-value assert prints: `assert G is M`, `assert G == M` (either order)
    with an absent marker M (None or ""), `assert G in (None, "")` with a display of markers, or `assert not G` (THE
    RULE, B: pytest explains the call by printing its value). An X.get(k), X.pop(k) or X.setdefault(k) read there is
    already read, as its receiver X."""
    if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
        return [test.operand] if _getenv_read(test.operand, module) else []
    if isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], (ast.Is, ast.Eq)):
        pair = (test.left, test.comparators[0])
        return [b for a, b in (pair, pair[::-1]) if _absent_marker(a) and _getenv_read(b, module)]
    if isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.In):
        return [test.left] if _absent_markers(test.comparators[0]) and _getenv_read(test.left, module) else []
    return []


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
            hits += [("B", "assert", n) for n in _bare_absent_getenv(x.test, module)]
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
    cli/, each file parsed by _own_tree. Raises when the tree holds no tests/*.py. What it returns holds strings,
    numbers and the lists, tuples and dicts around them, no tree and no node; the _Module records, their scopes and the
    Reader refer to their trees and never back to themselves, so every tree parsed here is freed by reference count
    when this returns (THE PARSE in the module docstring)."""
    paths = sorted(glob.glob(os.path.join(root, "tests", "*.py")))
    assert paths, "the census read no file: %s holds no tests/*.py" % root
    modules = {}
    for p in paths:
        text, tree = _own_tree(p, os.path.relpath(p, root))
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


class _Census:
    """The whole-tree census's facts, (files, offences, stats) as census() returned them, with no tree and no node, and
    the build's own read of its parse (_build_census): `parsed`, {file relative to the root: times parsed}, and
    `outlived`, the files whose tree was alive once census() had returned. One object that takes a weak reference (a
    tuple cannot), so tearDownModule can read that the facts are gone once EnvMappingAssertCensus drops them (pin 2
    there). It unpacks as the triple."""
    __slots__ = ("files", "offences", "stats", "parsed", "outlived", "__weakref__")

    def __init__(self, files, offences, stats, parsed, outlived):
        self.files, self.offences, self.stats = files, offences, stats
        self.parsed, self.outlived = parsed, outlived

    def __iter__(self):
        return iter((self.files, self.offences, self.stats))


def _build_census():
    """The whole-tree census over ROOT with require_population held, as a _Census, counted in _CENSUS_BUILDS. While
    census() runs, _own_tree records each parse with a weak reference to its tree (_RECORD); right after census()
    returns, the build reads from that record how often each file was parsed and which trees are still alive, keeps
    only those plain facts and drops the record before it returns: a record kept past the build would hold, for each
    file, a small object allocated beside that file's tree, and the allocator then keeps nearly every arena the trees
    took (one cold process on Python 3.11.15, after the same 1.9 GiB peak: 1137 MiB resident after the module's tests
    with such a record kept for the process, 533 to 546 MiB with it dropped here). That holds on 3.11 alone: on 3.12
    and 3.13, where the parser's identifiers hold those arenas anyway (THE PARSE), the module's tests left 1303 to 1306
    MiB above where they started with the record kept and 1267 to 1312 with it dropped. THE SINGLETON CHECK
    (tests/parse_cache.py's check_singletons, which parse_cache.derived ran around this build until THE PARSE took
    derived() out of this module): before the build (a writer that ran earlier: the build neither runs nor counts) and
    after it, on the returning road and on the raising road (the build itself wrote on a node the parser shares with
    every tree: it is counted and nothing is held, so the next read builds again; a raising build's exception is the
    AssertionError's __cause__ when the singletons carry attributes, else it propagates as it was). No collector state
    is touched."""
    global _CENSUS_BUILDS, _RECORD
    where = "the whole-tree census build (tests/test_env_mapping_assert_census.py)"
    parse_cache.check_singletons("before %s: an earlier writer" % where)
    _CENSUS_BUILDS += 1
    try:
        _RECORD = record = []
        try:
            files, offences, stats = census(ROOT)
        finally:
            _RECORD = None
        outlived = sorted({os.path.relpath(p, ROOT) for p, ref in record if ref() is not None})
        parsed = dict(collections.Counter(os.path.relpath(p, ROOT) for p, _ref in record))
        del record
        require_population(stats)
    except BaseException as exc:
        found = parse_cache.singleton_attributes()
        if found:
            raise AssertionError(parse_cache.singleton_message(
                "after %s raised %s: the build that just raised wrote them, or a thread beside it"
                % (where, type(exc).__name__), found)) from exc
        raise
    parse_cache.check_singletons("after %s: the build itself wrote them, or a thread beside it" % where)
    return _Census(files, offences, stats, parsed, outlived)


def _census_here():
    """The whole-tree census's facts for this module's run: built by the first test that reads them (_build_census) and
    held by EnvMappingAssertCensus.held, the one reference, until the class's tearDownClass drops it. A build that
    raised holds nothing, so the next read builds again. The weak reference is tearDownModule's pin (2)."""
    global _CENSUS_REF
    cls = EnvMappingAssertCensus
    if cls.held is None:
        cls.held = _build_census()
        _CENSUS_REF = weakref.ref(cls.held)
    return cls.held


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
    # every other name beginning with assert renders every argument (THE RULE, A): mock's argument-taking assertions,
    # whose failure can print the expected call, over a mapping, a holder and a marked container, and a snake_case
    # helper
    "mock-expected-call-and-snake-case-helper": (
        _body('env = dict(os.environ)', 'run = mock.Mock()', 'run.assert_called_once_with(["claude"], env=env)',
              'run.assert_any_call(env=os.environ)', 'run.assert_called_once_with(["claude"], env=dict(os.environ))',
              'kw = dict(model="m", env=dict(os.environ))', 'run.assert_called_once_with(["claude"], options=kw)',
              'seen = {}', 'def capture(slot):', '    seen[slot] = dict(os.environ)',
              'run.assert_called_with(["claude"], envs=seen)', 'arun = mock.AsyncMock()',
              'arun.assert_awaited_once_with(env=env)', 'arun.assert_any_await(**kw)', 'self.assert_no_leak(env)'),
        ["env", "os.environ", "dict(os.environ)", "kw", "seen", "env", "kw", "env"]),
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
    # the absent-value check over every spelling of one variable's read, one plant per spelling
    "absent-value-os-getenv": (_body('self.assertIsNone(os.getenv("X"))', 'self.assertEqual(None, os.getenv("X", None))',
                                     'self.assertIs(os.getenv("X"), None, "X")', 'import os as o',
                                     'self.assertFalse(o.getenv("X"), "X")'),
                               ['os.getenv("X")', 'os.getenv("X", None)', 'os.getenv("X")', 'o.getenv("X")']),
    "absent-value-getenv-imported": ("from os import getenv\nfrom os import getenv as ge\nimport unittest\n"
                                     "class T(unittest.TestCase):\n    def test_x(self):\n"
                                     "        self.assertFalse(getenv('X'), 'X')\n        self.assertIsNone(ge('X'))\n",
                                     ["getenv('X')", "ge('X')"]),
    "absent-value-pop": (_body('env = dict(os.environ)', 'self.assertIsNone(env.pop("X", None))',
                               'self.assertFalse(os.environ.pop("X", ""), "X")'),
                         ['env.pop("X", None)', 'os.environ.pop("X", "")']),
    "absent-value-setdefault": (_body('self.assertIsNone(os.environ.setdefault("X", None))', 'seen = {}',
                                      'self.assertEqual(seen["env"].setdefault("X", None), None, "X")'),
                                ['os.environ.setdefault("X", None)', 'seen["env"].setdefault("X", None)']),
    "absent-value-bare-getenv": (_body('assert os.getenv("X") is None', 'assert None == os.getenv("X"), "X"',
                                       'from os import getenv', 'assert not getenv("X"), "X"'),
                                 ['os.getenv("X")', 'os.getenv("X")', 'getenv("X")']),
    # the empty string marks absence as None does: each fails when the variable holds a value, and prints it
    "absent-value-empty-marker": (_body('env = dict(os.environ)', 'self.assertEqual(env.get("X", ""), "")',
                                        'self.assertEqual("", os.getenv("X", ""), "X")',
                                        'self.assertIn(os.getenv("X"), (None, ""))', 'assert os.getenv("X") == ""',
                                        'assert os.getenv("X") in (None, ""), "X"',
                                        'self.assertIn(os.environ.get("X"), ["", None], "X")',
                                        'self.assertIn(container=(None, ""), member=os.getenv("X"))'),
                                  ['env.get("X", "")', 'os.getenv("X", "")', 'os.getenv("X")', 'os.getenv("X")',
                                   'os.getenv("X")', 'os.environ.get("X")', 'os.getenv("X")']),
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
    # a view of a holder carries the environment it holds; its keys view prints names
    "holder-view": (_body('kw = dict(model="m", env={})', 'self.assertIn("m", kw.values())',
                          'self.assertEqual(sorted(kw.items()), [])', 'self.assertEqual(list(kw.values()), [])',
                          'self.assertTrue(False, "%r" % (kw.values(),))', 'self.assertEqual(sorted(kw.keys()), [])'),
                    ["kw.values()", "sorted(kw.items())", "list(kw.values())", "kw.values()"]),
    # X[k] = an environment mapping or a holder under a key that is not a string constant: every subscript of X is one,
    # in the scope that binds X (the capture helper's seen[slot] and the test's seen["probe"]), an attribute module-wide
    "variable-key-capture": (_body('seen = {}', 'def capture(slot):', '    def side_effect(*args, **kwargs):',
                                   '        seen[slot] = dict(kwargs["env"])', '    return side_effect',
                                   'self.assertNotIn("X", seen["probe"], "m")', 'self.assertIsNone(seen["probe"].get("X"))',
                                   'self.assertFalse("X" in seen["probe"], "m")'),
                             ['seen["probe"]', 'seen["probe"].get("X")']),
    "variable-key-holder-and-attribute": (_body('opts = {}', 'for name in ("a", "b"):',
                                                '    opts[name] = dict(model="m", env=dict(os.environ))',
                                                'self.assertIn("model", opts["a"])', 'self.box = {}',
                                                'self.box[0] = dict(os.environ)', 'self.assertNotIn("X", self.box[0])',
                                                'self.assertEqual(opts["a"]["model"], "m")', 'self.shapes = {}',
                                                'self.shapes[1] = dict(model="m", env={})',
                                                'self.assertIn("model", self.shapes[1])'),
                                          ['opts["a"]', "self.box[0]", "self.shapes[1]"]),
    # a same-named X in another method is its own binding: its seen["probe"], its view and X itself stay clean
    "variable-key-binding-scope": ("import os, unittest\nclass T(unittest.TestCase):\n    def test_a(self):\n"
                                   "        seen = {}\n        def capture(slot):\n"
                                   "            seen[slot] = dict(os.environ)\n        capture('probe')\n"
                                   "        self.assertNotIn('X', seen['probe'], 'm')\n"
                                   "        self.assertEqual(list(seen.values()), [], 'm')\n"
                                   "        self.assertEqual(seen, {}, 'm')\n    def test_b(self):\n"
                                   "        seen = {'probe': 'a b'}\n        self.assertIn('a', seen['probe'])\n"
                                   "        self.assertEqual(list(seen.values()), ['a b'])\n"
                                   "        self.assertEqual(seen, {'probe': 'a b'})\n",
                                   ["seen['probe']", "list(seen.values())", "seen"]),
    # the same X read by key without a subscript: X.get(k), X.pop(k), X.setdefault(k), and an absent-value check
    # through one, for an environment mapping stored under a variable key and for a holder
    "variable-key-keyed-reads": (_body('seen = {}', 'def capture(slot):', '    def side_effect(*args, **kwargs):',
                                       '        seen[slot] = dict(kwargs["env"])', '    return side_effect',
                                       'self.assertNotIn("X", seen.get("probe"), "m")',
                                       'self.assertNotIn("X", seen.pop("probe"))',
                                       'self.assertIsNone(seen.get("probe").get("X"))',
                                       'self.assertEqual(seen.setdefault("probe", {}), {})',
                                       'self.assertFalse("X" in seen.get("probe"), "m")'),
                                 ['seen.get("probe")', 'seen.pop("probe")', 'seen.get("probe").get("X")',
                                  'seen.setdefault("probe", {})']),
    "variable-key-holder-keyed-reads": (_body('opts = {}', 'for name in ("a", "b"):',
                                              '    opts[name] = dict(model="m", env=dict(os.environ))',
                                              'self.assertIn("model", opts.get("a"))', 'self.box = {}',
                                              'self.box[0] = dict(os.environ)',
                                              'self.assertNotIn("X", self.box.get(0))',
                                              'self.assertEqual(opts.get("a")["model"], "m")', 'self.shapes = {}',
                                              'self.shapes[1] = dict(model="m", env={})',
                                              'self.assertIn("model", self.shapes.get(1))'),
                                        ['opts.get("a")', "self.box.get(0)", "self.shapes.get(1)"]),
    # THE CONTAINERS: X[k] = an environment mapping or a holder under any key, a string constant or not, makes a view
    # of X (X.items(), X.values(), sorted, list, tuple, set or frozenset of one) carry every entry; one plant per keying
    # and kind, each with a name and an attribute; X.keys(), len() and sorted(X) print names or a count
    "variable-key-container-views": (_body('seen = {}', 'def capture(slot):', '    seen[slot] = dict(os.environ)',
                                           'self.assertEqual(list(seen.values()), [])',
                                           'self.assertIn("X", seen.items())',
                                           'self.assertEqual(sorted(seen.items()), [], "m")',
                                           'self.assertTrue(False, "%r" % (tuple(seen.values()),))',
                                           'self.box = {}', 'self.box[0] = dict(os.environ)',
                                           'self.assertEqual(frozenset(self.box.items()), frozenset())',
                                           'self.assertEqual(len(seen.values()), 1)',
                                           'self.assertEqual(sorted(seen.keys()), [])'),
                                     ['list(seen.values())', 'seen.items()', 'sorted(seen.items())',
                                      'tuple(seen.values())', 'frozenset(self.box.items())']),
    "variable-key-holder-container-views": (_body('opts = {}', 'for name in ("a", "b"):',
                                                  '    opts[name] = dict(model="m", env=dict(os.environ))',
                                                  'self.assertIn("m", opts.values())',
                                                  'self.assertEqual(set(opts.items()), set())',
                                                  'self.shapes = {}', 'self.shapes[1] = dict(model="m", env={})',
                                                  'self.assertEqual(list(self.shapes.values()), [])',
                                                  'self.assertEqual(sorted(opts.keys()), ["a", "b"])'),
                                            ['opts.values()', 'set(opts.items())', 'list(self.shapes.values())']),
    "string-key-container-views": (_body('byname = {}', 'byname["child"] = dict(os.environ)',
                                         'self.assertEqual(list(byname.values()), [])',
                                         'self.assertNotIn("X", byname.items(), "m")',
                                         'assert tuple(byname.items()) == ()',
                                         'self.reg = {}', 'self.reg["probe"] = dict(os.environ)',
                                         'self.assertEqual(sorted(self.reg.values()), [])',
                                         'self.assertEqual(sorted(byname), ["child"])',
                                         'self.assertEqual(len(byname.items()), 1)'),
                                   ['list(byname.values())', 'byname.items()', 'tuple(byname.items())',
                                    'sorted(self.reg.values())']),
    "string-key-holder-container-views": (_body('byname = {}', 'byname["a"] = dict(model="m", env=dict(os.environ))',
                                                'self.assertIn("m", byname.values())',
                                                'self.assertEqual(frozenset(byname.items()), frozenset())',
                                                'self.specs = {}', 'self.specs["host"] = {"sid": "s", "env": {}}',
                                                'self.assertEqual(list(self.specs.values()), [])',
                                                'self.assertTrue(False, "%r" % (self.specs.items(),))',
                                                'self.assertEqual(sorted(self.specs.keys()), [])'),
                                          ['byname.values()', 'frozenset(byname.items())', 'list(self.specs.values())',
                                           'self.specs.items()']),
    # THE CONTAINERS, X itself printed whole: in an assertion's rendered argument, a bare assert, a formatted message,
    # a name bound to one, and a copy of X; one plant per keying and kind, each with a name and an attribute
    "variable-key-container-printed-whole": (
        _body('seen = {}', 'def capture(slot):', '    seen[slot] = dict(os.environ)', 'self.assertEqual(seen, {})',
              'assert seen == {}, "m"', 'self.assertTrue(False, "seen %r" % (seen,))', 'self.box = {}',
              'self.box[0] = dict(os.environ)', 'self.assertIn(0, self.box)', 'self.assertEqual(dict(self.box), {})'),
        ['seen', 'seen', 'seen', 'self.box', 'dict(self.box)']),
    "variable-key-holder-container-printed-whole": (
        _body('opts = {}', 'for name in ("a", "b"):', '    opts[name] = dict(model="m", env=dict(os.environ))',
              'self.assertEqual(opts, {})', 'assert not opts', 'self.assertTrue(False, f"opts: {opts}")',
              'self.shapes = {}', 'self.shapes[1] = dict(model="m", env={})', 'self.assertDictEqual(self.shapes, {})',
              'self.assertEqual(self.shapes.copy(), {}, "m")'),
        ['opts', 'opts', 'opts', 'self.shapes', 'self.shapes.copy()']),
    "string-key-container-printed-whole": (
        _body('byname = {}', 'byname["child"] = dict(os.environ)', 'self.assertEqual(byname, {})',
              'assert "X" not in byname, "m"', 'self.assertTrue(False, "byname: {}".format(byname))', 'self.reg = {}',
              'self.reg["probe"] = dict(os.environ)', 'self.assertNotIn("X", self.reg)',
              'self.assertEqual({**self.reg}, {})', 'msg = repr(byname)[:80]', 'self.assertTrue(False, msg)',
              # a bare assert reads what WHAT IT CANNOT SEE leaves unread in an assertion method's arguments: a
              # subscript by another key, a copy rebuilt from a view, a dict display's subscript
              'k = "child"', 'assert byname[k] == {}', 'assert dict(byname.items()) == {}',
              'shown = {"a": dict(os.environ)}', 'assert shown["a"] == {}'),
        ['byname', 'byname', 'byname', 'self.reg', 'self.reg', 'msg', 'byname', 'byname.items()', 'shown']),
    "string-key-holder-container-printed-whole": (
        _body('import copy', 'byname = {}', 'byname["a"] = dict(model="m", env=dict(os.environ))',
              'self.assertEqual(byname, {})', 'assert byname == {"a": {}}',
              'self.assertTrue(False, "%s" % str(byname))', 'self.specs = {}',
              'self.specs["host"] = {"sid": "s", "env": {}}', 'self.assertEqual(self.specs, {}, "m")',
              'self.assertEqual(copy.deepcopy(self.specs), {})', 'self.assertEqual(dict(**self.specs), {})'),
        ['byname', 'byname', 'byname', 'self.specs', 'copy.deepcopy(self.specs)', 'dict(**self.specs)']),
    # the clean shapes: what a failure prints is one value, a bool, or names
    "clean-get-read": (_body('seen = {}', 'self.assertEqual(seen["env"].get("X"), "1")',
                             'self.assertTrue(seen["env"].get("X") is None, "X")'), []),
    "clean-getenv-and-pop": (_body('self.assertTrue(os.getenv("X") is None, "X")', 'self.assertEqual(os.getenv("X"), "1")',
                                   'cache = {"k": 1}', 'self.assertIsNone(cache.pop("k", None))',
                                   'assert os.getenv("X") == "1"', 'assert os.getenv("X") is not None'), []),
    # beside the empty-string marker: an expected value, a display with one, and the checks that fail when it is absent
    "clean-empty-marker-neighbours": (_body('self.assertEqual(os.getenv("X", ""), "1")',
                                            'self.assertIn(os.getenv("X"), ("a", ""))',
                                            'self.assertNotIn(os.getenv("X"), (None, ""))',
                                            'self.assertNotEqual(os.getenv("X", ""), "")',
                                            'assert os.getenv("X") != ""',
                                            'assert os.getenv("X") not in (None, "")'), []),
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
    # a container of environment mappings or holders, each keying and kind: its names, a count, a membership bool, a
    # join over its names, an equality as a bool, and a subscript under another string constant
    "clean-container-names-and-counts": (
        _body('seen = {}', 'def capture(slot):', '    seen[slot] = dict(os.environ)', 'self.assertEqual(len(seen), 1)',
              'self.assertEqual(sorted(seen), [])', 'self.assertNotIn("X", set(seen))',
              'self.assertEqual(list(seen), [])', 'self.assertEqual(tuple(seen), ())',
              'self.assertEqual(seen.keys(), set())', 'self.assertEqual(sorted(seen.keys()), [])',
              'self.assertTrue("probe" in seen, "probe")',
              'self.assertFalse("X" in seen, "X")', 'self.assertTrue(False, ", ".join(seen))',
              'self.assertTrue(seen == {}, "the captures differ")', 'opts = {}', 'for name in ("a", "b"):',
              '    opts[name] = dict(model="m", env=dict(os.environ))', 'self.assertEqual(len(opts), 2)',
              'self.assertEqual(list(opts.keys()), [])', 'self.assertTrue("a" in opts, "a")', 'byname = {}',
              'byname["child"] = dict(os.environ)', 'self.assertEqual(tuple(byname), ())',
              'self.assertEqual(len(byname.keys()), 1)', 'self.assertEqual(byname["other"], "x")', 'self.specs = {}',
              'self.specs["host"] = {"sid": "s", "env": {}}', 'self.assertEqual(sorted(self.specs), ["host"])',
              'self.assertFalse("guest" in self.specs, "guest")', 'self.assertTrue(False, " ".join(self.specs))',
              'present = "host" in self.specs', 'assert present, "host"'),
        []),
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
    # the calls a mock recorded, which its assertions print: the forms with no argument, and an argument-taking form
    # beside the expected call it is handed
    "limit-mock-assertion": (_body('with mock.patch("subprocess.run") as run:', '    run(["claude"], env=dict(os.environ))',
                                   'run.assert_not_called()', 'run.assert_called_once()',
                                   'run.assert_called_once_with(["claude"])'), []),
    # a call object in an assertion method's arguments (the list assert_has_calls or assert_has_awaits takes, an
    # equality or a membership test over the recorded calls): a list is read as a display, a call object's arguments
    # are not
    "limit-mock-call-object": (_body('env = dict(os.environ)', 'run = mock.Mock()',
                                     'run.assert_has_calls([mock.call(["claude"], env=env)])',
                                     'arun = mock.AsyncMock()', 'arun.assert_has_awaits([mock.call(env=env)])',
                                     'self.assertEqual(run.call_args, mock.call(["claude"], env=env))',
                                     'self.assertIn(mock.call(env=env), run.call_args_list)'), []),
    # subTest's parameters, its message and a keyword, which a failure inside the block prints
    "limit-subtest-param": (_body('env = dict(os.environ)', 'with self.subTest(env=env):',
                                  '    self.assertTrue("X" in env, "X")', 'with self.subTest("case %r" % (env,)):',
                                  '    self.assertTrue("X" in env, "X")'), []),
    # a container the text fills by another road (a dict comprehension, update, setdefault, a nested target), one a
    # call returns, and a copy rebuilt from a view; a string-key container read by a key that is not that constant; a
    # dict display's view and subscript; the filled containers and the one a call returns by a bare assert too
    "limit-container-other-roads": (
        "import os, unittest\nclass T(unittest.TestCase):\n    def _capture(self):\n        seen = {}\n"
        "        seen['probe'] = dict(os.environ)\n        return seen\n    def test_x(self):\n"
        "        built = {k: dict(os.environ) for k in ('a', 'b')}\n        self.assertEqual(built, {})\n"
        "        filled = {}\n        filled.update({'child': dict(os.environ)})\n"
        "        filled.setdefault('probe', dict(os.environ))\n        self.assertEqual(filled, {})\n"
        "        nested = {'a': {}}\n        nested['a']['b'] = dict(os.environ)\n"
        "        self.assertEqual(nested, {})\n        got = self._capture()\n        self.assertEqual(got, {})\n"
        "        byname = {}\n"
        "        byname['child'] = dict(os.environ)\n        self.assertEqual(dict(byname.items()), {})\n"
        "        kw = dict(model='m', env={})\n        self.assertEqual(dict(kw.items()), {})\n        k = 'child'\n"
        "        self.assertNotIn('X', byname[k])\n        self.assertNotIn('X', byname.get(k))\n"
        "        shown = {'a': dict(os.environ)}\n        self.assertEqual(list(shown.values()), [])\n"
        "        self.assertNotIn('X', shown['a'])\n        assert built == {} and filled == {}\n"
        "        assert nested == {}\n        assert got == {}\n",
        []),
    # a container printed by an assertion method through a spelling the census reads for a mapping or a holder but not
    # for X, one line per form: a walrus (the operand, inside a formatting road), a merge either way round, a dict
    # comprehension, SimpleNamespace(**X), a copy of an `or`, a conditional, a walrus, an alias (two spellings) or a
    # display, a view of a copy (two spellings); a view of an alias, a walrus, an `or`, a conditional or a display,
    # and a name bound to a copy, copied and viewed; and X stored in another container, printed by both roads, and X
    # read by a key through an alias, a copy or a walrus
    "limit-container-other-spellings": (
        _body('from types import SimpleNamespace', 'seen = {}', 'def capture(slot):',
              '    seen[slot] = dict(os.environ)',
              'self.assertEqual((got := seen), {})', 'self.assertTrue(False, "%r" % ((got := seen),))',
              'self.assertEqual(seen | {}, {})', 'self.assertEqual({} | seen, {})',
              'self.assertEqual({j: seen[j] for j in seen}, {})', 'self.assertIsNone(SimpleNamespace(**seen))',
              'self.assertEqual(dict(seen or {}), {})', 'self.assertEqual(dict(**(seen if seen else {})), {})',
              'self.assertEqual(dict((got := seen)), {})', 'alias = seen', 'self.assertEqual(dict(alias), {})',
              'self.assertEqual(alias.copy(), {})', 'self.assertEqual(dict({**seen}), {})',
              'self.assertEqual(list(alias.values()), [])', 'self.assertEqual(list((got := seen).values()), [])',
              'self.assertEqual(list((seen or {}).values()), [])',
              'self.assertEqual((seen if seen else {}).items(), [])', 'self.assertEqual(list({**seen}.values()), [])',
              'c = dict(seen)', 'self.assertEqual(dict(c), {})', 'self.assertEqual(c.items(), [])',
              'self.assertEqual(list(dict(seen).values()), [])', 'self.assertEqual(sorted(seen.copy().items()), [])',
              'outer = {}', 'outer["a"] = seen', 'self.assertEqual(outer, {})', 'assert outer == {}',
              'self.assertEqual(alias["probe"], {})', 'self.assertEqual(alias.get("probe"), {})',
              'self.assertEqual(dict(seen)["probe"], {})', 'self.assertEqual((got := seen)["probe"], {})'),
        []),
    "limit-or-wrapped-absent-read": (_body('self.assertEqual(os.getenv("X") or "", "")',
                                           'self.assertIsNone(os.getenv("X") or None)', 'env = dict(os.environ)',
                                           'self.assertEqual(env.get("X") or "", "", "X")',
                                           'assert (os.getenv("X") or "") == ""'), []),
    # Python a test writes as a string, in the two idioms the tree uses: a written constant, a textwrap.dedent module
    "limit-written-module-string": (_body('src = "import os\\ndef test_child():\\n    assert os.environ.get(\'X\') is None\\n'
                                          '    assert \'X\' not in os.environ\\n"',
                                          'with open("test_child.py", "w") as f:', '    f.write(src)'), []),
    "limit-dedent-module-string": (_body('import textwrap', 'module = textwrap.dedent("""\\', '    import os',
                                         '    def test_child():', '        assert os.environ.get("X") is None', '""")',
                                         'self.run_planted(module)'), []),
    "limit-derived-strings": (_body('env = dict(os.environ)', 'pairs = env.items()', 'self.assertEqual(sorted(pairs), [])',
                                    'vals = env.values()', 'self.assertTrue(False, ", ".join(vals))',
                                    'self.assertTrue(False, ", ".join(k + "=" + env[k] for k in env))',
                                    'self.assertTrue(False, repr(env).replace("a", "b"))',
                                    'self.assertTrue(False, ", ".join(map(str, env.values())))',
                                    'byname = {}', 'byname["child"] = env', 'entries = byname.items()',
                                    'self.assertEqual(sorted(entries), [])',
                                    'self.assertEqual([v for v in byname.values()], [])',
                                    'kw = dict(model="m", env={})',
                                    'self.assertEqual([v for v in kw.values()], [])'), []),
}


def setUpModule():
    """The first reads, before the module's first test and not at import (pytest imports every module at collection,
    before any test runs). Pin (1)'s: gc.get_freeze_count(), which tearDownModule reads again; two reads only, since
    each walks the permanent generation. The mechanism pin's: how many whole-tree censuses _build_census has started
    and how many files _own_tree has parsed so far in the process (_CENSUS_BUILDS, _PARSES), both counted per process,
    which that pin requires to be 0 at the first read in the process, the only one taken: a census or a tree made at
    import would be held, or counted as the module's one build, through every module that sorts before this one."""
    global _FROZEN_BEFORE, _BUILT_BEFORE, _BUILDS_AT_SETUP
    _FROZEN_BEFORE = gc.get_freeze_count()
    if _BUILT_BEFORE is None:
        _BUILT_BEFORE = (_CENSUS_BUILDS, _PARSES)
    _BUILDS_AT_SETUP = _CENSUS_BUILDS


def tearDownModule():
    """The module's two pins on what it leaves behind, read after its last test, and so after EnvMappingAssertCensus's
    tearDownClass dropped the facts, in the same process as setUpModule. That the build's trees died when census()
    returned is the mechanism pin's (test_the_census_is_built_once_from_its_own_parse_and_holds_no_tree).
    (1) The module froze nothing: gc.get_freeze_count() is not above what setUpModule read. The count is live and falls
    when a frozen object dies, so an object an earlier module froze can lower it in between, while nothing but a freeze
    inside the module raises it. Red under a build through tests/parse_cache.py's derived(), which freezes every object
    tracked when its build returns (8.16 million in the module's own process on Python 3.11 at 99c9ea824, the last head
    that built the census through derived()).
    (2) The facts are gone: the weak reference _census_here took is dead, read with no gc.collect(), which walks every
    tracked object; with no cycle, reference counting has already freed them. Red under a module-scope cache that keeps
    them, under a test that keeps its own reference past the class, and under a fact that refers back to the held
    object.
    Neither pin skips without a word: a census built with no weak reference taken reds (2), and a missing first read
    reds (1). The one silent case is (2) when no census was built at all (every test that reads it deselected), where
    there is nothing to be gone."""
    problems = []
    if _CENSUS_REF is None:
        if _CENSUS_BUILDS:
            problems.append("pin (2): %d whole-tree census(es) started in this process but no weak reference was taken to "
                            "the facts EnvMappingAssertCensus holds (_census_here takes it), so this pin cannot read that "
                            "they are gone" % _CENSUS_BUILDS)
    elif _CENSUS_REF() is not None:
        problems.append("pin (2): the census's facts are alive after EnvMappingAssertCensus's tearDownClass dropped them: "
                        "something else keeps them (a module-scope cache, a test's own reference) or they refer back to "
                        "the held object, a cycle that only a collection frees, and this module runs none")
    frozen = gc.get_freeze_count()
    if _FROZEN_BEFORE is None:
        problems.append("pin (1): setUpModule took no first read of gc.get_freeze_count(), so this pin cannot compare")
    elif frozen > _FROZEN_BEFORE:
        problems.append("pin (1): gc.get_freeze_count() rose from %d before the module's first test to %d after its last: "
                        "something in the module froze the heap (tests/parse_cache.py's derived() freezes after a build), "
                        "and every later read of the kernel's perf snapshot walks what is frozen" % (_FROZEN_BEFORE, frozen))
    if problems:
        raise AssertionError("; ".join(problems))


class EnvMappingAssertCensus(unittest.TestCase):
    maxDiff = None
    held = None   # the whole-tree census's facts (_Census), the ONE reference: set by _census_here, dropped by tearDownClass

    @classmethod
    def tearDownClass(cls):
        """Drop the one reference to the facts before the next module's first test (pin (2) in tearDownModule)."""
        cls.held = None
        super().tearDownClass()

    def test_the_census_is_built_once_from_its_own_parse_and_holds_no_tree(self):
        """THE PARSE, read from counts and weak references. Nothing was built or parsed before the module's first test
        (setUpModule's read, since both counts are the process's and a census made at import would pass as the module's
        one build). Two reads of the facts are one object and one build in the module's run (_CENSUS_BUILDS; a build
        per read or per test reds here). The build parsed every tests/*.py, and each file it read (the tests/ modules
        and the product modules its callees reach) once, by its own parse (the build's record, _Census.parsed; a second
        parse reds, and a file read through tests/parse_cache.py is missing from the record). Walking the facts finds
        only plain data (strings, numbers, None, and the lists, tuples and dicts around them), the contract census()
        states: no tree and no node. And no tree the build parsed was alive once census() had returned
        (_Census.outlived, read through weak references with no gc.collect()): census() returns facts alone and builds
        no cycle, so the trees go when it returns, not at the module's end. Red under a module-scope cache of the
        _Module records or the Reader, under a fact that holds a node (the walk names its type; the weak-reference read
        sees only a tree's root, since a node below it keeps its own subtree and no tree alive), and under a cycle that
        holds a tree, which only a collection frees. That the module froze nothing and that the facts are
        gone after the class are read in tearDownModule (pins 1 and 2)."""
        first = _census_here()
        same = _census_here() is first
        parsed, outlived = first.parsed, first.outlived
        not_plain, stack = set(), [first.files, first.offences, first.stats, parsed, outlived]
        while stack:
            v = stack.pop()
            if isinstance(v, dict):
                stack += list(v.keys()) + list(v.values())
            elif isinstance(v, (list, tuple)):
                stack += list(v)
            elif v is not None and not isinstance(v, (str, int, float)):
                not_plain.add(type(v).__name__)
        del first   # no local keeps the held object, so a red here leaves pin (2) reading the class's release, not this frame
        self.assertTrue(same, "two reads in the module's run are the one held object")
        self.assertEqual(sorted(not_plain), [], "the census's facts are plain data (strings, numbers, None and the "
                         "lists, tuples and dicts around them): a fact of another type keeps what it refers to (a "
                         "_Module its tree, an AST node its subtree), and a node below a tree's root keeps no tree "
                         "alive, so the weak references read below cannot see it")
        self.assertEqual(_BUILT_BEFORE, (0, 0), "(censuses built, files parsed) before the module's first test, as "
                         "setUpModule read them: none, since a census or a tree made at import is held through every "
                         "module that sorts before this one")
        self.assertEqual(_CENSUS_BUILDS - _BUILDS_AT_SETUP, 1, "the whole-tree census is built once in this module's "
                         "run, however many tests read it")
        population = sorted(os.path.relpath(p, ROOT) for p in glob.glob(os.path.join(ROOT, "tests", "*.py")))
        product = sorted(os.path.relpath(p, ROOT) for d in PRODUCT_DIRS for p in glob.glob(os.path.join(ROOT, d, "*.py")))
        self.assertTrue(population and product, "the tree holds tests/*.py and product modules")
        self.assertEqual([f for f in population if f not in parsed], [],
                         "every tests/*.py, parsed by the census's own parse")
        self.assertEqual(sorted(f for f in parsed if f not in population and f not in product), [],
                         "the build parsed tests/*.py and product modules alone")
        self.assertEqual(sorted("%s parsed %d times" % (f, n) for f, n in parsed.items() if n != 1), [],
                         "each file the build read, parsed once in this module's run")
        self.assertEqual(len(outlived), 0, "%d trees the build parsed were alive once census() had returned, for "
                         "example %s: a fact holds a tree, something else keeps the trees, or a cycle holds them"
                         % (len(outlived), outlived[:5]))

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
