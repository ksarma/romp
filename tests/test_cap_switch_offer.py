#!/usr/bin/env python3
"""The cap-death billing-switch OFFER (the user's binding ruling, 2026-08-30: a session must NEVER
silently switch billing in either direction — romp offers, only the explicit pick switches).
_cap_switch_offer mints only when every leg holds: a plain retryable API error (the on-you classes
carry their own remedies), a login-account window at its cap with a readable reset ahead, THIS
session billing the login, and a key on hand to offer. Self-expires with the window. The pick's one
path is the setAuth route a gear billing pick takes — pinned by census below. Synthetic fixtures."""
import ast
import json
import os
import tempfile
import time
import unittest
from romp_load import load_source
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)
km = load_source("romp_kernel_capoffer", os.path.join(BIN, "romp-kernel"))

SID = "aaaa3008-0000-0000-0000-000000000001"
ERR = {"text": "API Error 529 overloaded", "status": 529}


class CapSwitchOffer(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self._saved = (km.jd.STATE, km._live_map, km._auth_key_present)
        km.jd.STATE = Path(self.td.name)
        km._live_map = lambda: {SID: {"authLive": "login", "auth": "key"}}
        km._auth_key_present = lambda: True
        self._cap(100, 3600)

    def tearDown(self):
        (km.jd.STATE, km._live_map, km._auth_key_present) = self._saved
        self.td.cleanup()

    def _cap(self, pct, resets_in, bucket="five_hour"):
        (km.jd.STATE / "usage.json").write_text(json.dumps(
            {bucket: {"pct": pct, "resets_at": int(time.time()) + resets_in}}))

    def test_minted_for_a_login_billed_cap_death(self):
        v = km._cap_switch_offer(SID, ERR)
        self.assertEqual(v["window"], "five_hour")
        self.assertGreater(v["resetsAt"], time.time())

    def test_never_for_a_key_billed_session(self):
        km._live_map = lambda: {SID: {"authLive": "key", "auth": "login"}}
        self.assertIsNone(km._cap_switch_offer(SID, ERR),
                          "a key-billed error is not a cap death — nothing to offer")

    def test_never_for_the_on_you_error_classes(self):
        for k in ("tooLong", "spendLimit", "modelLimit", "authErr", "refusal"):
            self.assertIsNone(km._cap_switch_offer(SID, dict(ERR, **{k: True})),
                              k + " carries its own remedy — no billing offer rides it")

    def test_never_without_a_key_to_offer(self):
        km._auth_key_present = lambda: False
        self.assertIsNone(km._cap_switch_offer(SID, ERR))

    def test_never_when_no_window_is_capped(self):
        self._cap(90, 3600)
        self.assertIsNone(km._cap_switch_offer(SID, ERR))

    def test_retires_with_the_window(self):
        self._cap(100, -5)                            # resets_at already passed — the deciding event
        self.assertIsNone(km._cap_switch_offer(SID, ERR))

    def test_no_path_flips_billing_without_the_explicit_pick_both_directions(self):
        # CENSUS PIN, ON THE PROPERTY (round 3 of the review, 2026-09-20; tests-2, regression-3 and kernel-3, all
        # refuters): a new kernel call site that reaches SdkBackend.set_auth must red this pin. The billing write flips
        # which account a session bills; the pin exists so no AUTOMATIC path can (the user's binding ruling, 2026-08-30),
        # and a new caller lands here first. A regex on `be.set_auth(` was blind three ways at once: the delta's guarded
        # door is a getattr, set_auth_followers' door is a getattr, and a differently named receiver escapes the literal
        # `be`. So the mechanism is an ast walk of both kernel files, keyed on the NAME a call needs rather than on the
        # call's shape. WHAT IT SEES, stated in place of "any spelling" (the owner's lenses over round 3's commit,
        # 2026-09-20; the census lens's six green spellings and the mutation lens's E6): every attribute reference to a
        # reaching name on ANY receiver, called or not (be.set_auth(...), mgr.set_auth(...), functools.partial(be.set_auth,
        # sid), f = be.set_auth), and every string constant EQUAL to a reaching name wherever it sits (getattr(be,
        # "set_auth_guarded", None); name = "set_auth" then getattr(be, name)). Its stated limit: a name assembled at run
        # time ("set_" + "auth", a format, a lookup table) is no constant, and no static walk sees it; that spelling is
        # adversarial rather than accidental, and only a runtime spy on SdkBackend.set_auth under a kernel exercise would
        # census it, which this file does not attempt. One more limit is stated at (1) below: a reaching helper defined in a
        # third kernel module (a non-def carrier in kernel/sdk_backend.py, an alias, joins the derivation there since round 6).
        ROOT = os.path.dirname(HERE)
        sdk_src = Path(os.path.join(ROOT, "kernel", "sdk_backend.py")).read_text()
        ker_src = Path(os.path.join(ROOT, "kernel", "kernel.py")).read_text()

        def mentions(node, names):
            """The names in `names` that `node` reaches for: an attribute reference (called or not) or a string constant
            equal to one (a getattr door, a name bound to a variable); a docstring is a longer string and never equal."""
            out = set()
            for c in ast.walk(node):
                if isinstance(c, ast.Attribute) and c.attr in names:
                    out.add(c.attr)
                elif isinstance(c, ast.Constant) and isinstance(c.value, str) and c.value in names:
                    out.add(c.value)
            return out
        # (1) the callables of kernel/sdk_backend.py that REACH set_auth: set_auth itself, and transitively any callable
        # whose body reaches for one already in the set, by attribute or by name (getattr(self, "set_auth") included).
        # EVERY DEF WHOSE NEAREST ENCLOSING SCOPE IS THE MODULE OR A CLASS, WHATEVER STATEMENT WRAPS IT (round 5 of the
        # review, 2026-09-20; its correctness-1, regression-2 and extra5-2, all refuters): round 3 derived the set from
        # SdkBackend's own methods alone, so a kernel call reaching set_auth through a module-level function of this file or
        # through a method of another class here (SdkSession's, a mixin's) stayed green, ordinary spellings and not
        # adversarial ones. Round 4 walked the module's TOP-LEVEL classes only, so a staticmethod on a class nested in
        # SdkBackend that reached set_auth stayed green too (the verifier's plant); its addendum collected the classes by
        # ast.walk but still took the DIRECT children of the module body and of each class body, so a def inside any
        # compound statement at either scope (a module-level try: or if:, a class-body if:) never joined the set and its
        # kernel.py call site was never censused, while this message claimed any def shape (round 5's plants: the same
        # def inside try: and inside if: both green at 7 passed, the plain def red). The defs are collected from the WHOLE
        # tree now, with a parent map: a def joins when the nearest def, lambda or class above it is a class or nothing
        # (the module), so the statement wrapping it no longer matters. A def nested in a DEF or a lambda (a closure) is
        # still not walked on its own (set_auth_guarded's `step` would otherwise join the set as a name no kernel site
        # spells): its reach is its enclosing def's, which the walk over that def already sees, so a reaching closure in a
        # new def reds through that def's name; a class nested in a def resets the rule, so its methods join (round 4's
        # widening). Two classes can share a method name, so nodes are kept per name. set_auth_guarded and
        # set_auth_followers each run self.set_auth in their step; no other callable in the file reaches it. Derived, not
        # listed, so a new reaching def at module or class scope both grows this set and, being a name the kernel census
        # below looks for, cannot be called from kernel.py without redding. A NON-DEF BINDING at module or class scope joins
        # the set the same way (round 6 of the review, its closing pass, 2026-09-21, on the round's verifier finding: this
        # comment argued that residual from a COUNT of those bindings, AnnAssign 9 and Assign 199 at the round's first
        # commit, and the count was stale at the round's own head, where cluster A had added a class and an assignment; a
        # count in a comment is a claim nobody re-measures, so the population is derived and run over below instead of
        # counted here): every Assign, AnnAssign, AugAssign or NamedExpr whose nearest scope is the module or a class and
        # whose value reaches for a name in the set (an alias `_door = SdkBackend.set_auth`, a lambda calling it, a table
        # holding its name as a string, a bare name the set already holds) binds its stored names into the set (a Name
        # target's id, an attribute target's attribute, a subscript target's container, each element of a tuple target), so
        # a kernel.py call through the alias is censused under the alias's own name; a module-level `for` or `with` whose
        # iterable or context reaches for the set is asserted absent, since a name bound that way would need widening here
        # first; an import binds a module, which reaches for nothing in this file, and a class's methods are defs at class
        # scope, walked above. The binding population is asserted non-empty before the rule runs over it. THE RESIDUALS,
        # stated, each a carrier this walk does not visit: a reaching helper defined in a THIRD kernel module (neither
        # kernel/sdk_backend.py nor kernel/kernel.py) is outside both walks; and the run-time-assembled name above. The
        # class SdkBackend must still exist by that name: the widened derivation no longer stops on it.
        mod = ast.parse(sdk_src)
        self.assertTrue(any(isinstance(n, ast.ClassDef) and n.name == "SdkBackend" for n in mod.body),
                        "the kernel census below is keyed on SdkBackend's method names; a rename must re-derive it")
        parent = {c: p for p in ast.walk(mod) for c in ast.iter_child_nodes(p)}
        scopes = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)

        def scope_of(node):
            """The nearest def, lambda or class enclosing `node`; the module when none does."""
            p = parent.get(node)
            while p is not None and not isinstance(p, scopes):
                p = parent.get(p)
            return p if p is not None else mod
        defs = {}
        for d in ast.walk(mod):
            if isinstance(d, (ast.FunctionDef, ast.AsyncFunctionDef)) and isinstance(scope_of(d), (ast.ClassDef, ast.Module)):
                defs.setdefault(d.name, []).append(d)

        def at_scope(n):
            return isinstance(scope_of(n), (ast.ClassDef, ast.Module))
        binds = [n for n in ast.walk(mod) if isinstance(n, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.NamedExpr))
                 and n.value is not None and at_scope(n)]
        self.assertTrue(binds, "the non-def bindings at module or class scope the alias rule runs over: a derived population, "
                               "asserted non-empty before the rule runs")

        def reaches(value, names):
            """`mentions`, plus a bare Name the set already holds (an alias of an alias)."""
            return bool(mentions(value, names)) or any(isinstance(c, ast.Name) and c.id in names for c in ast.walk(value))

        def bound(target):
            """The names a binding target stores under: a Name's id, an attribute target's attribute (SdkBackend._door = ...),
            a subscript or starred target's container (_DOORS["auth"] = ...), each element of a tuple or list target."""
            if isinstance(target, ast.Name):
                return {target.id}
            if isinstance(target, ast.Attribute):
                return {target.attr}
            if isinstance(target, (ast.Subscript, ast.Starred)):
                return bound(target.value)
            if isinstance(target, (ast.Tuple, ast.List)):
                return set().union(*(bound(e) for e in target.elts))
            return set()
        reach = {"set_auth"}
        changed = True
        while changed:
            changed = False
            for name, nodes in defs.items():
                if name not in reach and any(mentions(d, reach) for d in nodes):
                    reach.add(name)
                    changed = True
            for b in binds:
                names = set().union(*(bound(t) for t in (b.targets if isinstance(b, ast.Assign) else [b.target])))
                if not names <= reach and reaches(b.value, reach):
                    reach |= names
                    changed = True
        for n in ast.walk(mod):
            if isinstance(n, (ast.For, ast.AsyncFor)) and at_scope(n):
                self.assertFalse(reaches(n.iter, reach), "a module-level for binds a reaching value (line %d): widen the alias rule" % n.lineno)
            elif isinstance(n, (ast.With, ast.AsyncWith)) and at_scope(n):
                for it in n.items:
                    self.assertFalse(reaches(it.context_expr, reach), "a module-level with binds a reaching value (line %d): widen the alias rule" % n.lineno)
        self.assertEqual(reach, {"set_auth", "set_auth_guarded", "set_auth_followers"},
                         "set_auth and the two entry points whose step runs it; a new reaching def, or a non-def binding whose value "
                         "reaches for one (an alias, a lambda, a table naming it), at module or class scope in kernel/sdk_backend.py, "
                         "whatever statement wraps it, reds here (a closure reds through its enclosing def)")
        # (2) every kernel.py site that reaches for one of those names, recorded as (enclosing def, kind): "call:" an
        # attribute call on any receiver; "ref:" an attribute reference that is not the func of a call (a bound method
        # handed on as a value: a partial, an alias); "name:" a string constant equal to the name (the getattr doors, a
        # name bound to a variable). A docstring or comment mention never counts (a docstring is a longer string, a
        # comment is not in the ast), and a bare line-shift never moves the pin. A new site anywhere adds a tuple and reds.
        sites, stack, called = [], [], set()

        class V(ast.NodeVisitor):
            def visit_FunctionDef(self, n):
                stack.append(n.name)
                self.generic_visit(n)
                stack.pop()
            visit_AsyncFunctionDef = visit_FunctionDef

            def visit_Call(self, n):
                f = n.func
                if isinstance(f, ast.Attribute) and f.attr in reach:
                    sites.append((stack[-1] if stack else "<module>", "call:" + f.attr))
                    called.add(id(f))
                self.generic_visit(n)

            def visit_Attribute(self, n):
                if n.attr in reach and id(n) not in called:
                    sites.append((stack[-1] if stack else "<module>", "ref:" + n.attr))
                self.generic_visit(n)

            def visit_Constant(self, n):
                if isinstance(n.value, str) and n.value in reach:
                    sites.append((stack[-1] if stack else "<module>", "name:" + n.value))

        V().visit(ast.parse(ker_src))
        self.assertEqual(sorted(sites), [
            ("_billing_request", "name:set_auth_followers"),       # the --all-following walk door (the user's explicit verb), a getattr
            ("_set_auth_or_park_verdict", "call:set_auth"),        # the fallback for a backend without the guarded door (a fake, the Codex backend)
            ("_set_auth_or_park_verdict", "name:set_auth_guarded"),  # the guarded door every explicit per-session pick takes, a getattr
        ], "the ONLY kernel road to set_auth is the explicit-pick helper (two spellings); the parked replay takes the helper too "
           "since round 6 of the review: %r" % sorted(sites))
        # the verb's --now pick takes the same helper with the FIFO gate off, never a raw call of its own
        self.assertIn("_set_auth_or_park_verdict(be, sid, pick, park=False)", ker_src)
        # the parked-op drain's replay takes the same helper with the gate off (round 6 of the review, 2026-09-20; its kernel-1,
        # extra7-1 and extra8-2): the SDK backend's set_auth then runs inside set_auth_guarded's guard, the one frame that can
        # restore a pick whose own record write skipped and raised; until round 6 the drain called set_auth bare and was the
        # second site this census listed. tests/test_billing_route.py drives the skip through the drain by execution
        self.assertIn("_set_auth_or_park_verdict(be, sid, op[1], park=False)", ker_src,
                      "the drain's replay reaches set_auth through the guarded door's helper, never a raw call of its own")
        self.assertIn('elif t == "setAuth" and lg.parse_pick(msg.get("value"))[0]:', ker_src,
                      "the route is a user gesture, and the ONLY door (T346: 'login' | 'key' | 'login:<id>')")
        self.assertNotIn("set_auth", ker_src[ker_src.index("def _cap_switch_offer"):
                                             ker_src.index("def _judge_limit_view")],
                         "the offer itself never switches anything")


if __name__ == "__main__":
    unittest.main()
