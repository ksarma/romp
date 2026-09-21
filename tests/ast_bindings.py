"""Name resolution by Python's scopes, for the census modules under tests/ that read a value through a name.

A census that reads a value through a NAME (the kernel's path in a subprocess argv, a refusal text a renderer
concatenates, a module-level function a case class calls) keys on the BINDING: the name resolved to the
declarations that bind it in the scope the read happens in, by the language's rule (the function the read is in,
then its enclosing functions, then the module; a class body is its own scope and encloses no method, so a bare
name read in a method never resolves to a class attribute), and the value is read from those declarations. A
check keyed on the name's spelling read a word of an argv as a variable and a variable of another function as
the module's (tests/test_hermetic_kernel_postal.py before 2026-09-21), and kept the last of two bindings when a
version gate bound one name in each arm (tests/test_sdk_singleton_ratchet.py's maps before the same day); both
now resolve here. The shape is the one PR #853's seating census proved in the webview tests: the declarations
each scope owns are indexed once, an identifier resolves outward through the scopes to the nearest that owns
one, and what a call is handed is held to that declaration, never to the text.

    bindings = Bindings.of(tree)                     # every statement, compound bodies included
    bindings = Bindings.of(tree, statements=module_statements)   # module-scope bindings from those statements alone
    scope = bindings.scope_of(node)                  # the scope a Name, Call or any expression is read in
    declarations, where = scope.resolve("KERNEL")    # the nearest enclosing scope's declarations, and that scope
    declarations, road = scope.resolve_target(attr)  # self.X through the class and its bases; other dotted targets
                                                     # by their spelling (road "instance" or "spelled")
    bindings.declarations("KERNEL")                  # the module scope's

A Declaration has the name, the kind (assign, augassign, unpack, def, class, import, parameter, loop, with,
except, match, del), the statement (`node`), the bound expression (`value`: the right side, the matching element
of a tuple or list right side for a tuple target of equal length, the composed `target op value` for an augmented
assignment; None for a kind that binds no readable value), the line and the scope. Two declarations of one name
in one scope are both returned, in source order: the caller decides whether they agree (the spawn census refuses
loudly when they disagree; the ratchet's text maps take the union). A `global` statement redirects the function's
bindings and reads of that name to the module scope; `nonlocal` to the nearest enclosing function that binds it.
A walrus in a comprehension binds in the enclosing scope, as the language does. An import binds its alias with
`origin` naming the module or the imported name (`subprocess`, `subprocess.run`) and no value.

Imported by tests/test_hermetic_kernel_postal.py and tests/test_sdk_singleton_ratchet.py after
`sys.path.insert(0, HERE)`, so a direct script run and a pytest run resolve the same file; registering the
name in tests/__init__.py, as romp_load is, would be the cleaner road and is not taken here. Standard library
only; loads no kernel module; writes nothing to the environment; named with no test_ prefix and no _test suffix,
so no census under tests/ collects it as a test module. Runs on 3.10 to 3.14 (ast.TryStar guarded).
"""
import ast

# the compound statements module_statements enters: an if, a try and, where the interpreter has it, a try with except*
MODULE_GATES = (ast.If, ast.Try) + ((ast.TryStar,) if hasattr(ast, "TryStar") else ())
_FUNCTIONS = (ast.FunctionDef, ast.AsyncFunctionDef)
_COMPREHENSIONS = (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
_TRIES = (ast.Try,) + ((ast.TryStar,) if hasattr(ast, "TryStar") else ())


def module_statements(tree):
    """The statements a module defines at its own level: every statement of tree.body and, for an if or a try met among
    them (MODULE_GATES: If, Try and, where the interpreter has it, TryStar), the statements of its body, its handlers'
    bodies, its else and its finally, recursively and in source order, so a function or a constant bound under a
    version gate or a guarded import is read as the module's. A def or a class met on the way is yielded and never
    entered, so a method or a nested function is no candidate for the populations built on this (ast.walk would make
    every one a candidate, and a nested helper passed the output a reader with no roster entry); a statement under
    any other compound statement (with, for, while, match) is outside what this reads, and so is a binding under one,
    which the derivations' docstrings state. `tree` is the module (a list of statements while recursing)."""
    for node in tree.body if isinstance(tree, ast.AST) else tree:
        yield node
        if isinstance(node, MODULE_GATES):
            yield from module_statements(list(node.body) + [s for h in getattr(node, "handlers", ()) for s in h.body]
                                         + list(node.orelse) + list(getattr(node, "finalbody", ())))


class Declaration:
    """One binding of a name: see the module docstring for the kinds and what `value` is for each."""
    __slots__ = ("name", "kind", "node", "value", "lineno", "scope", "origin")

    def __init__(self, name, kind, node, value, scope, origin=None):
        self.name, self.kind, self.node, self.value, self.scope, self.origin = name, kind, node, value, scope, origin
        self.lineno = getattr(node, "lineno", 0)

    def __repr__(self):
        return "<%s %s, line %d>" % (self.kind, self.name, self.lineno)


class Scope:
    """One scope of a module: the module, a function (a def or a lambda), a class body or a comprehension; `names`
    holds the declarations it owns by name, in source order; `attrs` (a class scope) the writes to the instance's
    attributes made through a method's own receiver (`self.X = ...` in any method of the class); `self_name` (a
    method's scope) the name of the receiver parameter, None for a staticmethod or a function outside a class."""
    __slots__ = ("kind", "node", "parent", "bindings", "names", "attrs", "globals", "nonlocals", "self_name")

    def __init__(self, kind, node, parent, bindings):
        self.kind, self.node, self.parent, self.bindings = kind, node, parent, bindings
        self.names, self.attrs, self.globals, self.nonlocals, self.self_name = {}, {}, set(), set(), None

    def module(self):
        scope = self
        while scope.parent is not None:
            scope = scope.parent
        return scope

    @property
    def klass(self):
        """The class scope a method's scope sits in, else None."""
        return self.parent if self.kind == "function" and self.parent is not None and self.parent.kind == "class" else None

    def binding_scope_for(self, name):
        """The scope a binding of `name` made here lands in: the module for a name declared global, the nearest
        enclosing function that binds it for a nonlocal one, the enclosing non-comprehension scope for a binding
        made inside a comprehension (a walrus), else this scope."""
        scope = self
        while scope.kind == "comprehension" and scope.parent is not None:
            scope = scope.parent
        if name in scope.globals:
            return scope.module()
        if name in scope.nonlocals:
            up = scope.parent
            while up is not None and up.kind != "module":
                if up.kind in ("function", "lambda") and name in up.names:
                    return up
                up = up.parent
            up = scope.parent
            while up is not None and up.kind not in ("function", "lambda", "module"):
                up = up.parent
            return up
        return scope

    def resolve(self, name):
        """(declarations, scope): the declarations of `name` in the nearest enclosing scope that binds it, and that
        scope; ([], None) for a name no scope binds (a builtin, a star import, a global of another module). A class
        scope is read only when the read is in the class body itself; from a method or a nested function it is
        skipped, as the interpreter skips it. A name declared global in the function read from resolves at the
        module; one declared nonlocal skips the declaring function."""
        scope, first = self, True
        while scope is not None:
            if scope.kind == "class" and not first:
                scope = scope.parent
                continue
            if name in scope.globals:
                module = scope.module()
                return list(module.names.get(name, [])), (module if module.names.get(name) else None)
            if name in scope.nonlocals:
                first = False
                scope = scope.parent
                continue
            found = scope.names.get(name)
            if found:
                return list(found), scope
            first = False
            scope = scope.parent
        return [], None

    def resolve_target(self, node):
        """(declarations, road) for an ast.Attribute or ast.Subscript read here: see Bindings.resolve_target."""
        return self.bindings.resolve_target(node, self)


class Bindings:
    """One module's scopes and declarations, built in one pass over the tree; `module` is the module scope,
    `dotted` the writes to attribute and subscript targets whose receiver is not a method's own instance, keyed on
    the target's spelling (`PATHS['kernel']`, `mod.KERNEL`), `owner` the scope every expression node is read in."""

    def __init__(self, tree):
        self.tree = tree
        self.module = Scope("module", tree, None, self)
        self.dotted = {}
        self.owner = {}
        self.scopes = {}
        self._deferred = []

    @classmethod
    def of(cls, tree, statements=None):
        """The bindings of `tree` (an ast.Module). With `statements` (a callable over the tree yielding module-level
        statements, module_statements say), a module-scope binding is recorded only when its statement is among
        those yielded, so a census whose stated reach is "the module's own statements and the bodies of a
        module-level if or try" resolves nothing bound under a module-level for, while or with; every function and
        class is still entered and every expression is still read, so scope_of is total either way."""
        bindings = cls(tree)
        reach = None if statements is None else {id(s) for s in statements(tree)}
        bindings._body(tree.body, bindings.module, reach)
        bindings._place_dotted()
        return bindings

    def declarations(self, name):
        """The module scope's declarations of `name`, in source order; [] when it binds none."""
        return list(self.module.names.get(name, []))

    def scope_of(self, node):
        """The scope `node` (any statement or expression of the tree) is read in; loud for a node not of this tree."""
        try:
            return self.owner[id(node)]
        except KeyError:
            raise AssertionError("the node %s at line %s was not read by these bindings (not a node of the tree they were "
                                 "built over)" % (type(node).__name__, getattr(node, "lineno", "?"))) from None

    def class_chain(self, klass):
        """A class scope and the scopes of its bases defined in the module, transitively, nearest first."""
        chain, todo = [], [klass]
        while todo:
            scope = todo.pop(0)
            if any(scope is c for c in chain):
                continue
            chain.append(scope)
            for base in scope.node.bases:
                if isinstance(base, ast.Name) and scope.parent is not None:
                    decls, _ = scope.parent.resolve(base.id)
                    todo.extend(self.scopes[id(d.node)] for d in decls if d.kind == "class" and id(d.node) in self.scopes)
        return chain

    def instance_class(self, node, scope):
        """The class scope whose instance `node`, an ast.Attribute, is read on: the receiver resolves, from `scope`, to
        the receiver parameter of a method of that class (`self`, `cls`, whatever the method calls it); else None."""
        if not (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)):
            return None
        decls, where = scope.resolve(node.value.id)
        if (where is not None and where.kind == "function" and where.self_name == node.value.id and len(decls) == 1
                and decls[0].kind == "parameter"):
            return where.klass
        return None

    def resolve_target(self, node, scope):
        """(declarations, road) for a dotted or subscripted target read in `scope`. An attribute of a method's own
        receiver (`self.X`, `cls.X`) resolves through the class: the writes `<receiver>.X = ...` made in any method of
        the class or of a base defined in the module, and the class body's own bindings of X (road "instance"; the
        receiver is resolved to the method's parameter, so a function outside a class whose parameter happens to be
        called self reads nothing here). Any other attribute or subscript target (`PATHS['kernel']`, `mod.KERNEL`,
        `obj.attr`) resolves by its SPELLING, ast.unparse of the target, to the writes made to that spelling anywhere
        in the module (road "spelled"): the receiver is not resolved on that road, which its callers state."""
        klass = self.instance_class(node, scope)
        if klass is not None:
            found = []
            for c in self.class_chain(klass):
                found.extend(c.attrs.get(node.attr, []))
                found.extend(c.names.get(node.attr, []))
            return found, "instance"
        return list(self.dotted.get(ast.unparse(node), [])), "spelled"

    # -- the walk -----------------------------------------------------------------------------------------------------

    def _body(self, statements, scope, reach=None):
        for statement in statements:
            self._statement(statement, scope, reach is None or id(statement) in reach, reach)

    def _statement(self, s, scope, live, reach):
        self.owner[id(s)] = scope
        if isinstance(s, _FUNCTIONS):
            for d in s.decorator_list:
                self._expr(d, scope)
            if live:
                self._bind_name(s.name, "def", s, None, scope)
            self._enter_function(s, scope)
        elif isinstance(s, ast.ClassDef):
            for d in list(s.decorator_list) + list(s.bases) + [k.value for k in s.keywords]:
                self._expr(d, scope)
            if live:
                self._bind_name(s.name, "class", s, None, scope)
            inner = Scope("class", s, scope, self)
            self.scopes[id(s)] = inner
            self._body(s.body, inner)
        elif isinstance(s, (ast.Import, ast.ImportFrom)):
            if live:
                for a in s.names:
                    if a.name == "*":
                        continue
                    origin = a.name if isinstance(s, ast.Import) else "%s.%s" % (s.module or "", a.name)
                    self._bind_name((a.asname or a.name).split(".")[0], "import", a, None, scope, origin)
        elif isinstance(s, ast.Global):
            scope.globals.update(s.names)
        elif isinstance(s, ast.Nonlocal):
            scope.nonlocals.update(s.names)
        elif isinstance(s, ast.Assign):
            self._expr(s.value, scope, live)
            for t in s.targets:
                self._expr(t, scope, live)
                if live:
                    self._bind_target(t, s.value, "assign", s, scope)
        elif isinstance(s, ast.AnnAssign):
            self._expr(s.annotation, scope, live)
            self._expr(s.target, scope, live)
            if s.value is not None:
                self._expr(s.value, scope, live)
                if live:
                    self._bind_target(s.target, s.value, "assign", s, scope)
        elif isinstance(s, ast.AugAssign):
            self._expr(s.value, scope, live)
            self._expr(s.target, scope, live)
            if live:
                composed = ast.copy_location(ast.BinOp(left=s.target, op=s.op, right=s.value), s)
                self.owner[id(composed)] = scope
                self._bind_target(s.target, composed, "augassign", s, scope)
        elif isinstance(s, ast.Delete):
            for t in s.targets:
                self._expr(t, scope, live)
                if live:
                    self._bind_target(t, None, "del", s, scope)
        elif isinstance(s, (ast.For, ast.AsyncFor)):
            self._expr(s.iter, scope, live)
            self._expr(s.target, scope, live)
            if live:
                self._bind_target(s.target, None, "loop", s, scope)
            self._body(s.body, scope, reach)
            self._body(s.orelse, scope, reach)
        elif isinstance(s, (ast.While, ast.If)):
            self._expr(s.test, scope, live)
            self._body(s.body, scope, reach)
            self._body(s.orelse, scope, reach)
        elif isinstance(s, (ast.With, ast.AsyncWith)):
            for item in s.items:
                self._expr(item.context_expr, scope, live)
                if item.optional_vars is not None:
                    self._expr(item.optional_vars, scope, live)
                    if live:
                        self._bind_target(item.optional_vars, None, "with", s, scope)
            self._body(s.body, scope, reach)
        elif isinstance(s, _TRIES):
            self._body(s.body, scope, reach)
            for h in s.handlers:
                self.owner[id(h)] = scope
                if h.type is not None:
                    self._expr(h.type, scope, live)
                if h.name and live:
                    self._bind_name(h.name, "except", h, None, scope)
                self._body(h.body, scope, reach)
            self._body(s.orelse, scope, reach)
            self._body(s.finalbody, scope, reach)
        elif isinstance(s, ast.Match):
            self._expr(s.subject, scope, live)
            for case in s.cases:
                self._pattern(case.pattern, scope, live, s)
                if case.guard is not None:
                    self._expr(case.guard, scope, live)
                self._body(case.body, scope, reach)
        else:
            for child in ast.iter_child_nodes(s):
                if isinstance(child, ast.expr):
                    self._expr(child, scope, live)

    def _pattern(self, p, scope, live, stmt):
        self.owner[id(p)] = scope
        name = getattr(p, "name", None) if isinstance(p, (ast.MatchAs, ast.MatchStar)) else getattr(p, "rest", None)
        if name and live:
            self._bind_name(name, "match", stmt, None, scope)
        for child in ast.iter_child_nodes(p):
            if isinstance(child, ast.expr):
                self._expr(child, scope, live)
            elif isinstance(child, ast.pattern):
                self._pattern(child, scope, live, stmt)

    def _enter_function(self, node, scope):
        inner = Scope("function", node, scope, self)
        self.scopes[id(node)] = inner
        if scope.kind == "class" and not any(isinstance(d, ast.Name) and d.id == "staticmethod" for d in node.decorator_list):
            positional = list(node.args.posonlyargs) + list(node.args.args)
            inner.self_name = positional[0].arg if positional else None
        self._arguments(node.args, inner, scope)
        if node.returns is not None:
            self._expr(node.returns, scope)
        self._body(node.body, inner)

    def _arguments(self, args, inner, outer):
        for a in list(args.posonlyargs) + list(args.args) + list(args.kwonlyargs) + [x for x in (args.vararg, args.kwarg) if x]:
            if a.annotation is not None:
                self._expr(a.annotation, outer)
            self._bind_name(a.arg, "parameter", a, None, inner, redirect=False)
        for d in list(args.defaults) + [x for x in args.kw_defaults if x is not None]:
            self._expr(d, outer)

    def _expr(self, node, scope, live=True):
        if node is None:
            return
        self.owner[id(node)] = scope
        if isinstance(node, ast.Lambda):
            inner = Scope("lambda", node, scope, self)
            self.scopes[id(node)] = inner
            self._arguments(node.args, inner, scope)
            self._expr(node.body, inner)
        elif isinstance(node, _COMPREHENSIONS):
            inner = Scope("comprehension", node, scope, self)
            self.scopes[id(node)] = inner
            for i, g in enumerate(node.generators):
                self.owner[id(g)] = inner
                self._expr(g.iter, scope if i == 0 else inner)
                self._expr(g.target, inner)
                self._bind_target(g.target, None, "loop", node, inner, redirect=False)   # the comprehension carries the line
                for cond in g.ifs:
                    self._expr(cond, inner)
            if isinstance(node, ast.DictComp):
                self._expr(node.key, inner)
                self._expr(node.value, inner)
            else:
                self._expr(node.elt, inner)
        elif isinstance(node, ast.NamedExpr):
            self._expr(node.value, scope, live)
            self._expr(node.target, scope, live)
            if live:
                self._bind_target(node.target, node.value, "assign", node, scope)
        else:
            for child in ast.iter_child_nodes(node):
                if isinstance(child, ast.expr):
                    self._expr(child, scope, live)
                elif isinstance(child, ast.keyword):
                    self.owner[id(child)] = scope
                    self._expr(child.value, scope, live)

    def _bind_target(self, target, value, kind, stmt, scope, redirect=True):
        if isinstance(target, ast.Name):
            self._bind_name(target.id, kind, stmt, value, scope, redirect=redirect)
        elif isinstance(target, (ast.Attribute, ast.Subscript)):
            self._deferred.append((target, value, kind, stmt, scope))
        elif isinstance(target, ast.Starred):
            self._bind_target(target.value, None, "unpack", stmt, scope, redirect)
        elif isinstance(target, (ast.Tuple, ast.List)):
            elements = list(target.elts)
            paired = (isinstance(value, (ast.Tuple, ast.List)) and len(value.elts) == len(elements)
                      and not any(isinstance(e, ast.Starred) for e in elements + list(value.elts)))
            for i, t in enumerate(elements):
                if paired:
                    self._bind_target(t, value.elts[i], kind, stmt, scope, redirect)
                else:
                    self._bind_target(t, None, "unpack" if kind in ("assign", "augassign") else kind, stmt, scope, redirect)

    def _bind_name(self, name, kind, node, value, scope, origin=None, redirect=True):
        where = scope.binding_scope_for(name) if redirect else scope
        declaration = Declaration(name, kind, node, value, where, origin)
        where.names.setdefault(name, []).append(declaration)
        return declaration

    def _place_dotted(self):
        for target, value, kind, stmt, scope in self._deferred:
            klass = self.instance_class(target, scope)
            declaration = Declaration(ast.unparse(target), kind, stmt, value, scope)
            if klass is not None:
                klass.attrs.setdefault(target.attr, []).append(declaration)
            else:
                self.dotted.setdefault(declaration.name, []).append(declaration)
        self._deferred = []
