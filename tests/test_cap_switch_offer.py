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
        # refuters): a new kernel call site that reaches SdkBackend.set_auth by ANY spelling must red this pin. The
        # billing write flips which account a session bills; the pin exists so no AUTOMATIC path can (the user's
        # binding ruling, 2026-08-30), and a new caller lands here first. A regex on `be.set_auth(` was blind three
        # ways at once: the delta's guarded door is a getattr, set_auth_followers' door is a getattr, and a
        # differently named receiver escapes the literal `be`. So the mechanism is an ast walk of both kernel files.
        ROOT = os.path.dirname(HERE)
        sdk_src = Path(os.path.join(ROOT, "kernel", "sdk_backend.py")).read_text()
        ker_src = Path(os.path.join(ROOT, "kernel", "kernel.py")).read_text()
        # (1) the SdkBackend methods that REACH set_auth: set_auth itself, and transitively any method whose body
        # calls one already in the set. set_auth_guarded and set_auth_followers each run self.set_auth in their step;
        # no other method reaches it. Derived, not listed, so a new reaching method both grows this set and, being a
        # name the kernel census below looks for, cannot be called from kernel.py without redding.
        cls = next(n for n in ast.walk(ast.parse(sdk_src)) if isinstance(n, ast.ClassDef) and n.name == "SdkBackend")
        methods = {m.name: m for m in cls.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))}
        reach = {"set_auth"}
        changed = True
        while changed:
            changed = False
            for name, m in methods.items():
                if name in reach:
                    continue
                if any(isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute) and c.func.attr in reach
                       for c in ast.walk(m)):
                    reach.add(name)
                    changed = True
        self.assertEqual(reach, {"set_auth", "set_auth_guarded", "set_auth_followers"},
                         "set_auth and the two entry points whose step runs it; a new reaching backend method reds here")
        # (2) every kernel.py call site reaching one of those names by ANY spelling: a direct attribute call on ANY
        # receiver (be.set_auth(, or a differently named receiver), and a getattr(x, "<name>", ...) door (the guarded
        # door and the walk door are both getattrs; door()/walk() is a call on the local the getattr returned). A
        # lambda-wrapped call is walked too. Recorded as (enclosing def, kind), so a docstring or comment mention (not
        # a Call) never counts and a bare line-shift never moves the pin. A new site anywhere adds a tuple and reds.
        sites, stack = [], []

        class V(ast.NodeVisitor):
            def visit_FunctionDef(self, n):
                stack.append(n.name)
                self.generic_visit(n)
                stack.pop()
            visit_AsyncFunctionDef = visit_FunctionDef

            def visit_Call(self, n):
                f = n.func
                where = stack[-1] if stack else "<module>"
                if isinstance(f, ast.Attribute) and f.attr in reach:
                    sites.append((where, "call:" + f.attr))
                if (isinstance(f, ast.Name) and f.id == "getattr" and len(n.args) >= 2
                        and isinstance(n.args[1], ast.Constant) and n.args[1].value in reach):
                    sites.append((where, "getattr:" + n.args[1].value))
                self.generic_visit(n)

        V().visit(ast.parse(ker_src))
        self.assertEqual(sorted(sites), [
            ("_apply_pending_ops", "call:set_auth"),               # the parked-op drain replays the user's OWN pick; its refusal is read
            ("_billing_request", "getattr:set_auth_followers"),    # the --all-following walk door (the user's explicit verb)
            ("_set_auth_or_park_verdict", "call:set_auth"),        # the fallback for a backend without the guarded door (a fake, the Codex backend)
            ("_set_auth_or_park_verdict", "getattr:set_auth_guarded"),  # the guarded door every explicit per-session pick takes
        ], "the ONLY kernel roads to set_auth are the explicit-pick helper (two spellings) and the parked replay: %r" % sorted(sites))
        # the verb's --now pick takes the same helper with the FIFO gate off, never a raw call of its own
        self.assertIn("_set_auth_or_park_verdict(be, sid, pick, park=False)", ker_src)
        self.assertIn('elif t == "setAuth" and lg.parse_pick(msg.get("value"))[0]:', ker_src,
                      "the route is a user gesture, and the ONLY door (T346: 'login' | 'key' | 'login:<id>')")
        self.assertNotIn("set_auth", ker_src[ker_src.index("def _cap_switch_offer"):
                                             ker_src.index("def _judge_limit_view")],
                         "the offer itself never switches anything")


if __name__ == "__main__":
    unittest.main()
