"""The op set a REMOTE jump posts the shell's chat reveal for is the kernel's own, read by AST (review round 3 of the
parked-pane change, 2026-09-18).

ui/webview/federation.ts REMOTE_CHAT_REVEAL_OPS names the ops FederationManager.outbound follows with {romp:'reveal',
pane:'chat'} when a route is remote and the send went out (review round 2, then round 3): the remote kernel answers the
op with a chat focus and tells its OWN shell clients to reveal the chat, and it has none here. Round 2 hand-listed five
names and pinned them by name in federation-remote-reveal.test.ts, a pin that could not go red for an op the list
lacked, and the kernel answers five more (createSession, pickResult, openByName, forkSession, commentPromote) through
the same two functions. This module derives the set from kernel/kernel.py: every arm of Handler._dispatch_ws and _drive
whose test compares the frame's type against a name and whose body reaches _reveal_chat_for or _reveal_or_confirm,
directly or through module functions (openSession through _open_or_revive, reviveSession through _revive_session on its
own thread, createSession through _create_sdk_session_inner beside its direct call, forkSession and commentPromote through
_drive's helpers). What the pin guarantees, bounded to what the walk reads (review round 4, 2026-09-18): an arm (an `if`
or `elif` at the dispatcher's statement level, under any guard, loop or try block whose own test does not compare the
type) whose body reaches a reveal either compares the frame's type, read bare (msg.get("type"), msg["type"], or a local
bound to one), against a name the walk resolves and lands in the set, or fails here with its line: a comparator the walk
cannot resolve, a comparison other than == or `in`, an arm whose test does not compare the type at all (a helper
predicate, a prefix test, a wrapped read such as str(...) or `or ""`) while its body reaches a reveal, and a reach
outside any arm all raise. Reach is by NAME: a call's callee (a bare name, or an attribute's name whatever it hangs on)
and a name or attribute handed to a call, transitively through the module's functions; a reveal reached through a
subscripted callee (a dispatch table) is not seen, and a method of another object sharing a reveal-reaching function's
name counts as reach, erring toward listing. The walk's own claims are pinned first on synthetic source. The TypeScript
constant is pinned equal to the derived set, and federation-remote-reveal.test.ts drives every member of the constant
through the real manager.

Reads source only: no kernel is loaded and no state is written."""
import ast
import os
import re
import textwrap
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
KERNEL = os.path.join(ROOT, "kernel", "kernel.py")
FEDERATION = os.path.join(ROOT, "ui", "webview", "federation.ts")

REVEAL_FUNCTIONS = ("_reveal_chat_for", "_reveal_or_confirm")
DISPATCHERS = ("_dispatch_ws", "_drive")
ROUND_2_LIST = {"openSession", "showOnTimeline", "deepLink", "viewReadOnly", "reviveSession"}


def _reads_msg_type(node):
    """`msg.get("type")` or `msg["type"]`: the frame's type, the thing an arm's test compares."""
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "get" \
       and isinstance(node.func.value, ast.Name) and node.func.value.id == "msg" and node.args \
       and isinstance(node.args[0], ast.Constant) and node.args[0].value == "type":
        return True
    return isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id == "msg" \
        and isinstance(node.slice, ast.Constant) and node.slice.value == "type"


def _strs(node):
    """The op names a comparator spells out: a str, a tuple (list, set) of str, or one of those wrapped in frozenset(),
    set() or tuple(). None for anything else."""
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("frozenset", "set", "tuple") \
       and len(node.args) == 1 and not node.keywords:
        node = node.args[0]
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)) and node.elts \
       and all(isinstance(e, ast.Constant) and isinstance(e.value, str) for e in node.elts):
        return [e.value for e in node.elts]
    return None


def _referenced(nodes):
    """The function names a body can run, by name: the callee of every call (a bare name, or an attribute's name whatever
    it hangs on: `self.`, a class, a module, an object), and every bare name or attribute handed to a call as an argument
    or keyword value, since `threading.Thread(target=f, ...)` runs f. Review round 4 (2026-09-18): a `self.` callee alone
    and Name arguments alone missed a method handed over as a callable (`target=self._go`) and a callee spelled
    `_helper.run()`. Attribute reach is by the attribute's name, so another object's method sharing a module function's
    name counts, erring toward listing, never toward a silent miss; a subscripted callee (a dispatch table) is not read."""
    out = set()
    for body in nodes:
        for n in ast.walk(body):
            if not isinstance(n, ast.Call):
                continue
            f = n.func
            if isinstance(f, ast.Name):
                out.add(f.id)
            elif isinstance(f, ast.Attribute):
                out.add(f.attr)
            for a in list(n.args) + [k.value for k in n.keywords]:
                if isinstance(a, ast.Name):
                    out.add(a.id)
                elif isinstance(a, ast.Attribute):
                    out.add(a.attr)
    return out


def ops_answered_with_a_chat_reveal(source, dispatchers=DISPATCHERS, reveal=REVEAL_FUNCTIONS):
    """Every op name an arm of `dispatchers` (module functions or methods, by bare name) tests a frame's type against,
    where the arm's body reaches one of the `reveal` functions: a direct call, or a call or a handed-over name of a
    module function (or a `self.` method) that reaches one, transitively. Returns {op: (dispatcher, line of the arm)}.

    An arm is an `if` or `elif` at the dispatcher's statement level (the function body; the bodies of its loops, with and
    try blocks; a chain's terminal else; and the body of an `if` whose test does not compare the type, a guard such as
    `if client.get("app") == "chat":`) whose test holds an ast.Compare with the frame's type (`msg.get("type")`,
    `msg["type"]`, or a local bound to either, _drive's `t`) on one side and == or `in` between; the comparator is a str,
    a tuple (list, set) of str, a name bound to one inside the function (_drive's ID_OPS) or a name bound to one at module
    level (_TARGET_NAME_OPS). No spacing or layout is assumed. An arm's body is read for reach as a whole; the branches
    inside it are its own logic, never arms. Three things raise with their line (review round 4, 2026-09-18, the
    fail-loudly rule): a comparator the walk cannot resolve; a comparison shape it does not read (`!=`); and a reach the
    walk cannot list, that is a statement reaching a reveal under an `if` whose test does not compare the frame's type
    (a helper predicate, a prefix test, a wrapped read) or outside any `if` at all. So an arm the walk can read lands in
    the set, and one it cannot read fails here; what it cannot see at all is reach the collector does not read
    (_referenced: a subscripted callee).

    Reach is a reverse breadth-first search from the reveal functions over the call graph of the module's functions;
    the dispatchers themselves are not traversed as callers, so a helper that re-dispatches a frame is not "reaching".
    An arm whose test names several ops (`in ("pickResult", "openByName")`) lands every one of them: the walk reads the
    arm's test, not which of its inner branches runs for which op."""
    tree = ast.parse(textwrap.dedent(source))
    funcs, module_bound = {}, {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            funcs[node.name] = node
        elif isinstance(node, ast.ClassDef):
            for sub in node.body:
                if isinstance(sub, ast.FunctionDef):
                    funcs.setdefault(sub.name, sub)
        elif isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) \
                and _strs(node.value) is not None:
            module_bound[node.targets[0].id] = _strs(node.value)
    missing = [d for d in dispatchers if d not in funcs]
    if missing:
        raise AssertionError("dispatcher(s) not found in the source: %r" % (missing,))

    callers = {}
    for name, fn in funcs.items():
        if name in dispatchers:
            continue
        for callee in _referenced(fn.body):
            callers.setdefault(callee, set()).add(name)
    reaches, frontier = set(reveal), list(reveal)
    while frontier:
        for caller in callers.get(frontier.pop(), ()):
            if caller not in reaches:
                reaches.add(caller)
                frontier.append(caller)

    def arms(fn):
        aliases, bound = set(), {}
        for node in ast.walk(fn):
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                if _reads_msg_type(node.value):
                    aliases.add(node.targets[0].id)
                elif _strs(node.value) is not None:
                    bound[node.targets[0].id] = _strs(node.value)
        reads = lambda node: _reads_msg_type(node) or (isinstance(node, ast.Name) and node.id in aliases)

        def resolve(node):
            names = _strs(node)
            if names is None and isinstance(node, ast.Name):
                names = bound.get(node.id) or module_bound.get(node.id)
            if names is None:
                raise AssertionError("line %d of %s compares a frame's type against a comparator this pin cannot resolve: %s"
                                     % (node.lineno, fn.name, ast.dump(node)))
            return names

        def ops_of(test):
            ops = set()
            for node in ast.walk(test):
                if not isinstance(node, ast.Compare):
                    continue
                operands = [node.left] + node.comparators
                for i, op in enumerate(node.ops):
                    left, right = operands[i], operands[i + 1]
                    if reads(right) and not reads(left):
                        left, right = right, left
                    if not reads(left):
                        continue
                    if not isinstance(op, (ast.Eq, ast.In)):
                        raise AssertionError("line %d of %s compares a frame's type with %s, a shape this pin does not read"
                                             % (node.lineno, fn.name, type(op).__name__))
                    ops.update(resolve(right))
            return ops

        found = {}

        def sweep(stmts, guard=None):
            """The arm-level statements. An `if` or `elif` whose test compares the type is an arm: its body is read whole
            and never swept. One whose test does not is a guard: its body is swept as arm-level, and a statement there
            reaching a reveal raises, named with the guard's line. A loop, with or try block is swept through. Any other
            statement reaching a reveal at this level is a reach outside any arm and raises."""
            for s in stmts:
                if isinstance(s, ast.If):
                    node = s
                    while True:
                        ops = ops_of(node.test)
                        if ops:
                            if _referenced(node.body) & reaches:
                                for op in ops:
                                    found.setdefault(op, node.lineno)
                        else:
                            sweep(node.body, guard=node)
                        rest = node.orelse
                        if len(rest) == 1 and isinstance(rest[0], ast.If):
                            node = rest[0]           # an elif: the next arm of the chain, not a nested one
                            continue
                        sweep(rest, guard=guard)     # a terminal else's own statements
                        break
                elif isinstance(s, (ast.For, ast.AsyncFor, ast.While, ast.With, ast.AsyncWith, ast.Try)) \
                        or type(s).__name__ in ("TryStar", "Match"):
                    for _field, value in ast.iter_fields(s):
                        if isinstance(value, list) and value:
                            if isinstance(value[0], ast.stmt):
                                sweep(value, guard=guard)
                            elif hasattr(value[0], "body"):      # except handlers, match cases
                                for x in value:
                                    sweep(x.body, guard=guard)
                else:
                    hit = sorted(_referenced([s]) & reaches)
                    if hit:
                        raise AssertionError(
                            "line %d of %s reaches %s %s, so this pin cannot list the op it answers"
                            % (s.lineno, fn.name, hit,
                               "under an arm (line %d) whose test does not compare the frame's type against a name: a helper "
                               "predicate, a prefix test or a wrapped read is outside this walk's reading" % guard.lineno
                               if guard is not None else "outside any arm that compares the frame's type against a name"))

        sweep(fn.body)
        return found

    result = {}
    for d in dispatchers:
        for op, line in sorted(arms(funcs[d]).items(), key=lambda kv: kv[1]):
            result.setdefault(op, (d, line))
    return result


def typescript_remote_chat_reveal_ops(source):
    """The names federation.ts's REMOTE_CHAT_REVEAL_OPS holds, read from its `new Set([...])` literal."""
    m = re.search(r'export const REMOTE_CHAT_REVEAL_OPS[^=\n]*=\s*new Set\(\[([^\]]*)\]\)', source)
    if not m:
        raise AssertionError("REMOTE_CHAT_REVEAL_OPS is not a `new Set([...])` literal in federation.ts")
    names = re.findall(r'"([^"]+)"', m.group(1))
    if not names or len(set(names)) != len(names):
        raise AssertionError("REMOTE_CHAT_REVEAL_OPS is empty or repeats a name: %r" % (names,))
    return set(names)


class RemoteChatRevealOps(unittest.TestCase):
    SYNTHETIC = '''
MODULE_OPS = ("promote", "fork")
ROADS = frozenset({"road"})
def _reveal_chat_for(client, focus):
    pass
def _reveal_or_confirm(sid, focus, client=None):
    _reveal_chat_for(client, focus)
def _open_or_revive(sid, client=None):
    _reveal_or_confirm(sid, {}, client)
def _inner(sid, client=None):
    if client is not None:
        _reveal_chat_for(client, {"type": "focus", "id": sid})
def _outer(sid, client=None):
    return _inner(sid, client=client)
def _quiet(sid):
    return sid
def _redispatch(msg, client):
    return Handler._dispatch_ws(None, msg, client)
def _drive(msg, client):
    t = msg.get("type")
    LOCAL_OPS = ("alpha",
                 "beta")
    if t in LOCAL_OPS and msg.get("id"):
        sid = msg["id"]
    elif t in MODULE_OPS and msg.get("name"):
        sid = msg["name"]
    else:
        return False
    if t == "alpha":
        _outer(sid, client=client)
    elif t == "beta":
        _quiet(sid)
    elif t in MODULE_OPS:
        _outer(sid, client=client)
    return True
class Handler:
    def _dispatch_ws(self, msg, client):
        if _drive(msg, client):
            return
        if msg.get("type")=="direct":
            _reveal_chat_for(client, {})
        elif msg["type"] == "helper":
            _open_or_revive(msg["id"], client=client)
        elif msg.get("type") == "threaded" and msg.get("id"):
            threading.Thread(target=_outer, args=(msg["id"], client), daemon=True).start()
        elif msg.get("type") in ("pair", "twin") and (msg.get("id") or msg.get("name")):
            sid = msg.get("id")
            if sid:
                _reveal_chat_for(client, {"type": "focus", "id": sid})
        elif "reversed" == msg.get("type"):
            self._by_method(client)
        elif msg.get("type") == "handed":
            threading.Thread(target=self._by_method, args=(client,), daemon=True).start()
        elif msg.get("type") == "byclass":
            Handler._by_method(self, client)
        elif msg.get("type") in ROADS:
            _reveal_chat_for(client, {})
        elif msg.get("type") == "silent":
            _quiet(msg.get("id"))
        elif msg.get("type") == "loops":
            _redispatch(msg, client)
        elif msg.get("type") == "nested":
            if msg.get("live"):
                pass
            else:
                _outer(msg["id"], client=client)
        if client.get("app") == "chat":
            try:
                if msg.get("type") == "guarded":
                    _reveal_chat_for(client, {})
                elif msg.get("type") == "guardedquiet":
                    _quiet(msg.get("id"))
            except Exception:
                pass
    def _by_method(self, client):
        _reveal_chat_for(client, {})
'''

    def test_the_walk_reads_every_arm_shape_and_fails_loudly_on_one_it_cannot(self):
        """The walk's own claims, on synthetic source: an arm reaches a reveal by a direct call, through a helper, through a
        helper of a helper, as a thread's target (a module function, and a method handed over as `self._m`), through a
        `self.` method, through a method called on its class, inside a nested branch, and under a guard and a try block
        whose own tests compare nothing; the type is read unspaced, subscripted, reversed, through _drive's local alias,
        and the comparator as a str, a tuple, a local tuple, a module tuple and a module frozenset. An arm that calls
        nothing reaching a reveal, one that only re-dispatches the frame, and _drive's sid-binding arms do not land. A
        comparator it cannot resolve and a `!=` raise with the line."""
        found = ops_answered_with_a_chat_reveal(self.SYNTHETIC)
        self.assertEqual(set(found), {"direct", "helper", "threaded", "pair", "twin", "reversed", "handed", "byclass", "road",
                                      "nested", "guarded", "alpha", "promote", "fork"})
        self.assertEqual(found["direct"][0], "_dispatch_ws")
        self.assertEqual(found["alpha"][0], "_drive")
        self.assertNotIn("beta", found, "an arm whose helper reaches no reveal")
        self.assertNotIn("silent", found)
        self.assertNotIn("guardedquiet", found)
        self.assertNotIn("loops", found, "re-dispatching the frame is not reaching a reveal")
        with self.assertRaisesRegex(AssertionError, r"line 5 of _dispatch_ws .*cannot resolve"):
            ops_answered_with_a_chat_reveal("def _drive(msg, client):\n    pass\nclass H:\n    def _dispatch_ws(self, msg, client):\n"
                                            "        if msg.get(\"type\") == somewhere_else:\n            _reveal_chat_for(client, {})\n")
        with self.assertRaisesRegex(AssertionError, "does not read"):
            ops_answered_with_a_chat_reveal("def _drive(msg, client):\n    pass\ndef _dispatch_ws(msg, client):\n"
                                            "    if msg.get(\"type\") != \"ready\":\n        _reveal_chat_for(client, {})\n")
        with self.assertRaisesRegex(AssertionError, "not found"):
            ops_answered_with_a_chat_reveal("def _dispatch_ws(msg, client):\n    pass\n")

    def test_an_arm_whose_test_does_not_compare_the_type_raises_when_its_body_reaches_a_reveal(self):
        """Review round 4 (2026-09-18, tests-1): before, such an arm was skipped in silence, so the set could miss an op
        while the equality pin stayed green. Four spellings, each raising with the reaching line and the arm's line: a helper
        predicate, a prefix test, a read wrapped in str(), and a read wrapped in `or ""`; a reach with no `if` around it
        raises as outside any arm. A reveal reached only under an arm the walk CAN read stays a listing, so a guard whose
        test compares nothing (an app check, a try block) around a readable chain lands its ops and raises nothing."""
        head = "def _drive(msg, client):\n    pass\nclass H:\n    def _dispatch_ws(self, msg, client):\n"
        for test in ('_is_jump(msg)', 'msg.get("type").startswith("open")', 'str(msg.get("type")) == "open"',
                     '(msg.get("type") or "") == "open"'):
            with self.assertRaisesRegex(AssertionError, r"line 6 of _dispatch_ws reaches \['_reveal_chat_for'\] under an arm "
                                                        r"\(line 5\) whose test does not compare the frame's type"):
                ops_answered_with_a_chat_reveal(head + "        if %s:\n            _reveal_chat_for(client, {})\n" % test)
        with self.assertRaisesRegex(AssertionError, r"line 6 of _dispatch_ws reaches \['_open_or_revive'\] outside any arm"):
            ops_answered_with_a_chat_reveal("def _drive(msg, client):\n    pass\n"
                                            "def _open_or_revive(sid, client):\n    _reveal_or_confirm(sid, {}, client)\n"
                                            "def _dispatch_ws(msg, client):\n    _open_or_revive(msg.get(\"id\"), client)\n")
        found = ops_answered_with_a_chat_reveal(head + '        if client.get("app") == "chat":\n            try:\n'
                                                '                if msg.get("type") == "z":\n                    _reveal_chat_for(client, {})\n'
                                                '            except Exception:\n                pass\n')
        self.assertEqual(found, {"z": ("_dispatch_ws", 7)})

    def test_a_reveal_reached_through_a_method_handed_over_or_called_on_its_class_is_found(self):
        """Review round 4 (2026-09-18, kernel-3): the collector saw a callee only as a bare name or a `self.` method and an
        argument only as a bare name, so `threading.Thread(target=self._go, ...)` and `Handler._go(self, client)` were
        missed in silence while the equality pin stayed green. Both spellings land now; the SYNTHETIC source carries them
        as `handed` and `byclass` and the shape test above pins them beside the rest."""
        src = ("def _drive(msg, client):\n    pass\nclass Handler:\n    def _dispatch_ws(self, msg, client):\n"
               "        if msg.get(\"type\") == \"handed\":\n            threading.Thread(target=self._go, args=(client,)).start()\n"
               "        elif msg.get(\"type\") == \"byclass\":\n            Handler._go(self, client)\n"
               "        elif msg.get(\"type\") == \"viahelper\":\n            _helper.run(client)\n"
               "    def _go(self, client):\n        _reveal_chat_for(client, {})\n"
               "def run(client):\n    _reveal_chat_for(client, {})\n")
        found = ops_answered_with_a_chat_reveal(src)
        self.assertEqual(set(found), {"handed", "byclass", "viahelper"})

    def test_the_kernels_answer_set_is_derived_and_the_typescript_constant_equals_it(self):
        """The set is read from kernel.py, never hand-listed here: every op an arm of _dispatch_ws or _drive answers with
        _reveal_chat_for or _reveal_or_confirm. Round 2's five names are in it (the walk found what the hand list had), and
        federation.ts's REMOTE_CHAT_REVEAL_OPS is exactly it, with the difference spelled out either way."""
        with open(KERNEL, encoding="utf-8") as f:
            found = ops_answered_with_a_chat_reveal(f.read())
        derived = set(found)
        self.assertLessEqual(ROUND_2_LIST, derived, "round 2's hand list is a subset of what the kernel answers: missing %r"
                             % sorted(ROUND_2_LIST - derived))
        self.assertGreater(len(derived), len(ROUND_2_LIST), "the kernel answers more ops than the hand list named")
        self.assertEqual({d for d, _ in found.values()}, set(DISPATCHERS), "both dispatchers contribute arms")
        for op in derived:
            self.assertTrue(op.isalpha(), "an op name is a word: %r" % (op,))
        with open(FEDERATION, encoding="utf-8") as f:
            listed = typescript_remote_chat_reveal_ops(f.read())
        self.assertEqual(listed, derived,
                         "REMOTE_CHAT_REVEAL_OPS is exactly the kernel's chat-focus answers; the kernel answers but the constant "
                         "lacks %r, the constant lists but the kernel does not answer %r (arms: %r)"
                         % (sorted(derived - listed), sorted(listed - derived), found))


if __name__ == "__main__":
    unittest.main()
