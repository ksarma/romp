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
    readings, road = scope.resolve_target(attr)      # one declaration list per value: self.X per concrete class, the
                                                     # method's and each module subclass's (road "instance"); other
                                                     # dotted targets one list, by their spelling (road "spelled")
    bindings.declarations("KERNEL")                  # the module scope's
    bindings.release()                               # break the index's cycles once read (a build under parse_cache)

A Declaration has the name, the kind (assign, augassign, unpack, def, class, import, parameter, loop, with,
except, match, del), the statement (`node`), the bound expression (`value`: the right side, the matching element
of a tuple or list right side for a tuple target of equal length, the composed `target op value` for an augmented
assignment; None for a kind that binds no readable value), the line and the scope. Two declarations of one name
in one scope are both returned: the caller decides whether they agree (the spawn census refuses loudly when they
disagree; the ratchet's text maps take the union). A `global` statement redirects the function's bindings and
reads of that name to the module scope; `nonlocal` redirects its bindings to the nearest enclosing function that
binds it, so the declaring function owns no declaration of the name and a read there resolves past it. A walrus
in a comprehension binds in the enclosing scope, as the language does. With a reach (Bindings.of's `statements`),
a binding that lands in the module scope is recorded only from a statement the reach yields. An import binds its
alias with `origin` naming what the bound name denotes, and no value: the module (`subprocess`; `os` for `import
os.path`, which binds the name os), the dotted module of an `as` alias (`os.path` for `import os.path as osp`),
or the imported name (`subprocess.run`).

Imported by tests/test_hermetic_kernel_postal.py and tests/test_sdk_singleton_ratchet.py after
`sys.path.insert(0, HERE)`, so a direct script run and a pytest run resolve the same file; registering the
name in tests/__init__.py, as romp_load is, would be the cleaner road and is not taken here. Standard library
only; loads no kernel module; writes nothing to the environment; named with no test_ prefix and no _test suffix,
so the runner collects it as no test module, while the censuses that read every .py under tests/ (the hermetic
module's spawn scan and its import-time environment scan) read it like any other and find no spawn and no write in
it. Runs on 3.10 to 3.14 (ast.TryStar guarded).
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
    """One scope of a module: the module, a function (a def or a lambda), a class body or a comprehension; `names` holds
    the declarations it owns by name; `attrs` (a class scope) the writes to the instance's attributes made through a
    method's own receiver (`self.X = ...` in any method of the class); `self_name` (a method's scope) the name of the
    receiver parameter, None for a staticmethod or a function outside a class."""
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
        module. A scope that declares a name nonlocal owns no declaration of it (binding_scope_for sends each of its
        bindings of the name to the enclosing function), so the read resolves past it."""
        scope, first = self, True
        while scope is not None:
            if scope.kind == "class" and not first:
                scope = scope.parent
                continue
            if name in scope.globals:
                module = scope.module()
                return list(module.names.get(name, [])), (module if module.names.get(name) else None)
            found = scope.names.get(name)
            if found:
                return list(found), scope
            first = False
            scope = scope.parent
        return [], None

    def resolve_target(self, node):
        """(readings, road) for an ast.Attribute or ast.Subscript read here: see Bindings.resolve_target."""
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
        self._mro = {}   # id(class scope) -> its mro (Bindings.mro), filled on first read
        self._concrete = {}   # id(class scope) -> its concrete_classes, likewise
        self._reach = None   # the ids of the statements `statements` yielded (Bindings.of), None for every statement

    @classmethod
    def of(cls, tree, statements=None):
        """The bindings of `tree` (an ast.Module). With `statements` (a callable over the tree yielding statements,
        module_statements say), a binding that lands in the MODULE scope is recorded only when the statement it is made
        in is among those yielded, wherever that statement sits: a module-level statement's own binding, one a def or
        a class body makes through `global`, and a comprehension walrus's that binds in the module. So a census whose
        stated reach is "the module's own statements and the bodies of a module-level if or try" resolves nothing
        bound under a module-level for, while or with, and nothing a def or a class body binds through `global`, whose
        statements module_statements never yields. A binding that lands in a function, a lambda, a class body or a
        comprehension is recorded either way (so is a dotted write, except one a module-level statement outside the
        reach makes); every function and class is still entered and every expression is still read, so scope_of is
        total either way."""
        bindings = cls(tree)
        bindings._reach = None if statements is None else {id(s) for s in statements(tree)}
        bindings._body(tree.body, bindings.module)
        bindings._place_dotted()
        return bindings

    def declarations(self, name):
        """The module scope's declarations of `name`; [] when it binds none."""
        return list(self.module.names.get(name, []))

    def scope_of(self, node):
        """The scope `node` (any statement or expression of the tree) is read in; loud for a node not of this tree."""
        try:
            return self.owner[id(node)]
        except KeyError:
            raise AssertionError("the node %s at line %s was not read by these bindings (not a node of the tree they were "
                                 "built over)" % (type(node).__name__, getattr(node, "lineno", "?"))) from None

    def release(self):
        """Break the index's reference cycles, so reference counting frees it once the caller drops it: a scope holds
        these bindings and its declarations, and each declaration holds its scope. For a caller that builds under
        tests/parse_cache.py's derived(), whose collector is off for the build and whose freeze afterwards keeps any
        cycle the build dropped (the rule for a build in that module's docstring). No scope or declaration is usable
        after this. The tree is not touched."""
        scopes = {id(s): s for s in list(self.owner.values()) + list(self.scopes.values()) + [self.module] if s is not None}
        for scope in scopes.values():
            scope.names, scope.attrs, scope.parent, scope.bindings = {}, {}, None, None
        self.module = None
        for table in (self.dotted, self.owner, self.scopes, self._mro, self._concrete):
            table.clear()
        self._deferred = []

    def class_chain(self, klass):
        """A class scope and the scopes of its bases defined in the module, transitively, breadth first."""
        chain, todo = [], [klass]
        while todo:
            scope = todo.pop(0)
            if any(scope is c for c in chain):
                continue
            chain.append(scope)
            todo.extend(c for classes in self._module_bases(scope) for c in classes)
        return chain

    def _module_bases(self, klass):
        """One list per base of klass that names a class the module defines, in the order the bases are written: the
        class scopes the base's name resolves to from the scope the class statement is in (more than one for a name
        bound to two classes)."""
        found = []
        for base in klass.node.bases:
            if isinstance(base, ast.Name) and klass.parent is not None:
                decls, _ = klass.parent.resolve(base.id)
                classes = [self.scopes[id(d.node)] for d in decls if d.kind == "class" and id(d.node) in self.scopes]
                if classes:
                    found.append(classes)
        return found

    def mro(self, klass, _below=()):
        """klass and its bases defined in the module, in the order an instance's attribute lookup reads them: the C3
        linearization the interpreter computes, over the bases _module_bases reads (a base defined elsewhere, such as
        unittest.TestCase, holds no binding of this module and is left out). For a base name bound to more than one
        class, a cycle, or bases C3 cannot order (a class statement the interpreter refuses), the order is
        class_chain's, breadth first. Memoized per class."""
        memo = self._mro.get(id(klass))
        if memo is not None:
            return memo
        per_base = self._module_bases(klass)
        bases = [classes[0] for classes in per_base]
        order = [klass]
        if any(len(classes) > 1 for classes in per_base) or any(b is c for b in bases for c in _below + (klass,)):
            order = self.class_chain(klass)
        else:
            tails = [list(self.mro(b, _below + (klass,))) for b in bases] + [bases]
            while any(tails):
                tails = [t for t in tails if t]
                head = next((t[0] for t in tails if not any(t[0] is c for u in tails for c in u[1:])), None)
                if head is None:
                    order = self.class_chain(klass)
                    break
                order.append(head)
                tails = [t[1:] if t[0] is head else t for t in tails]
        self._mro[id(klass)] = order
        return order

    def concrete_classes(self, klass):
        """klass and every class of the module whose mro holds it (klass first, the rest in the order the walk met
        them): the classes whose instances can run a method klass defines. Memoized per class."""
        memo = self._concrete.get(id(klass))
        if memo is None:
            memo = self._concrete[id(klass)] = [klass] + [c for c in self.scopes.values() if c.kind == "class" and c is not klass
                                                          and any(k is klass for k in self.mro(c))]
        return memo

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
        """(readings, road) for a dotted or subscripted target read in `scope`, `readings` a list of declaration lists,
        one per value the target can hold at run time, each for the caller to decide on its own. An attribute of a
        method's own receiver (`self.X`, `cls.X`) resolves per concrete class (road "instance"; the receiver is
        resolved to the method's parameter, so a function outside a class whose parameter happens to be called self
        reads nothing here): for the method's class and every class of the module whose mro holds it
        (concrete_classes), one reading, the writes `<receiver>.X = ...` made in any method of that class's mro plus the
        class-body bindings of X in the first class of its mro that binds X, the one an instance of that class reads.
        So a base's method reading self.SCRIPT reads the base's binding for the base and a subclass's own binding for
        the subclass, never both as one; readings that are equal are returned once. Any other attribute or subscript
        target (`PATHS['kernel']`, `mod.KERNEL`, `obj.attr`) resolves by its SPELLING, ast.unparse of the target, to
        one reading, the writes made to that spelling anywhere in the module (road "spelled"): the receiver is not
        resolved on that road, which its callers state."""
        klass = self.instance_class(node, scope)
        if klass is not None:
            readings, known = [], set()
            for concrete in self.concrete_classes(klass):
                order = self.mro(concrete)
                found = [d for c in order for d in c.attrs.get(node.attr, [])]
                found.extend(next((c.names[node.attr] for c in order if c.names.get(node.attr)), []))
                if tuple(map(id, found)) not in known:
                    known.add(tuple(map(id, found)))
                    readings.append(found)
            return readings, "instance"
        return [list(self.dotted.get(ast.unparse(node), []))], "spelled"

    # -- the walk -----------------------------------------------------------------------------------------------------
    # `live`: the statement being read is among those Bindings.of's `statements` yielded (always, without them). It
    # gates the bindings that land in the module scope alone (_bind_name) and a module-level statement's dotted writes
    # (_bind_target); a binding that lands in any other scope is recorded either way.

    def _body(self, statements, scope):
        for statement in statements:
            self._statement(statement, scope, self._reach is None or id(statement) in self._reach)

    def _statement(self, s, scope, live):
        self.owner[id(s)] = scope
        if isinstance(s, _FUNCTIONS):
            for d in s.decorator_list:
                self._expr(d, scope, live)
            self._bind_name(s.name, "def", s, None, scope, live=live)
            self._enter_function(s, scope, live)
        elif isinstance(s, ast.ClassDef):
            for d in list(s.decorator_list) + list(s.bases) + [k.value for k in s.keywords]:
                self._expr(d, scope, live)
            self._bind_name(s.name, "class", s, None, scope, live=live)
            inner = Scope("class", s, scope, self)
            self.scopes[id(s)] = inner
            self._body(s.body, inner)
        elif isinstance(s, (ast.Import, ast.ImportFrom)):
            for a in s.names:
                if a.name == "*":
                    continue
                if isinstance(s, ast.Import):
                    # `import os.path` binds os, the package, and that is what the bound name denotes; `import os.path
                    # as osp` binds osp to the dotted module
                    origin = a.name if a.asname else a.name.split(".")[0]
                else:
                    origin = "%s.%s" % (s.module or "", a.name)
                self._bind_name((a.asname or a.name).split(".")[0], "import", a, None, scope, origin, live=live)
        elif isinstance(s, ast.Global):
            scope.globals.update(s.names)
        elif isinstance(s, ast.Nonlocal):
            scope.nonlocals.update(s.names)
        elif isinstance(s, ast.Assign):
            self._expr(s.value, scope, live)
            for t in s.targets:
                self._expr(t, scope, live)
                self._bind_target(t, s.value, "assign", s, scope, live=live)
        elif isinstance(s, ast.AnnAssign):
            self._expr(s.annotation, scope, live)
            self._expr(s.target, scope, live)
            if s.value is not None:
                self._expr(s.value, scope, live)
                self._bind_target(s.target, s.value, "assign", s, scope, live=live)
        elif isinstance(s, ast.AugAssign):
            self._expr(s.value, scope, live)
            self._expr(s.target, scope, live)
            composed = ast.copy_location(ast.BinOp(left=s.target, op=s.op, right=s.value), s)
            self.owner[id(composed)] = scope
            self._bind_target(s.target, composed, "augassign", s, scope, live=live)
        elif isinstance(s, ast.Delete):
            for t in s.targets:
                self._expr(t, scope, live)
                self._bind_target(t, None, "del", s, scope, live=live)
        elif isinstance(s, (ast.For, ast.AsyncFor)):
            self._expr(s.iter, scope, live)
            self._expr(s.target, scope, live)
            self._bind_target(s.target, None, "loop", s, scope, live=live)
            self._body(s.body, scope)
            self._body(s.orelse, scope)
        elif isinstance(s, (ast.While, ast.If)):
            self._expr(s.test, scope, live)
            self._body(s.body, scope)
            self._body(s.orelse, scope)
        elif isinstance(s, (ast.With, ast.AsyncWith)):
            for item in s.items:
                self._expr(item.context_expr, scope, live)
                if item.optional_vars is not None:
                    self._expr(item.optional_vars, scope, live)
                    self._bind_target(item.optional_vars, None, "with", s, scope, live=live)
            self._body(s.body, scope)
        elif isinstance(s, _TRIES):
            self._body(s.body, scope)
            for h in s.handlers:
                self.owner[id(h)] = scope
                if h.type is not None:
                    self._expr(h.type, scope, live)
                if h.name:
                    self._bind_name(h.name, "except", h, None, scope, live=live)
                self._body(h.body, scope)
            self._body(s.orelse, scope)
            self._body(s.finalbody, scope)
        elif isinstance(s, ast.Match):
            self._expr(s.subject, scope, live)
            for case in s.cases:
                self._pattern(case.pattern, scope, live, s)
                if case.guard is not None:
                    self._expr(case.guard, scope, live)
                self._body(case.body, scope)
        else:
            for child in ast.iter_child_nodes(s):
                if isinstance(child, ast.expr):
                    self._expr(child, scope, live)

    def _pattern(self, p, scope, live, stmt):
        self.owner[id(p)] = scope
        name = getattr(p, "name", None) if isinstance(p, (ast.MatchAs, ast.MatchStar)) else getattr(p, "rest", None)
        if name:
            self._bind_name(name, "match", stmt, None, scope, live=live)
        for child in ast.iter_child_nodes(p):
            if isinstance(child, ast.expr):
                self._expr(child, scope, live)
            elif isinstance(child, ast.pattern):
                self._pattern(child, scope, live, stmt)

    def _enter_function(self, node, scope, live):
        inner = Scope("function", node, scope, self)
        self.scopes[id(node)] = inner
        if scope.kind == "class" and not any(isinstance(d, ast.Name) and d.id == "staticmethod" for d in node.decorator_list):
            positional = list(node.args.posonlyargs) + list(node.args.args)
            inner.self_name = positional[0].arg if positional else None
        self._arguments(node.args, inner, scope, live)
        if node.returns is not None:
            self._expr(node.returns, scope, live)
        self._body(node.body, inner)

    def _arguments(self, args, inner, outer, live):
        for a in list(args.posonlyargs) + list(args.args) + list(args.kwonlyargs) + [x for x in (args.vararg, args.kwarg) if x]:
            if a.annotation is not None:
                self._expr(a.annotation, outer, live)
            self._bind_name(a.arg, "parameter", a, None, inner, redirect=False)
        for d in list(args.defaults) + [x for x in args.kw_defaults if x is not None]:
            self._expr(d, outer, live)

    def _expr(self, node, scope, live=True):
        if node is None:
            return
        self.owner[id(node)] = scope
        if isinstance(node, ast.Lambda):
            inner = Scope("lambda", node, scope, self)
            self.scopes[id(node)] = inner
            self._arguments(node.args, inner, scope, live)
            self._expr(node.body, inner, live)
        elif isinstance(node, _COMPREHENSIONS):
            inner = Scope("comprehension", node, scope, self)
            self.scopes[id(node)] = inner
            for i, g in enumerate(node.generators):
                self.owner[id(g)] = inner
                self._expr(g.iter, scope if i == 0 else inner, live)
                self._expr(g.target, inner, live)
                self._bind_target(g.target, None, "loop", node, inner, redirect=False, live=live)   # the comprehension carries the line
                for cond in g.ifs:
                    self._expr(cond, inner, live)
            if isinstance(node, ast.DictComp):
                self._expr(node.key, inner, live)
                self._expr(node.value, inner, live)
            else:
                self._expr(node.elt, inner, live)
        elif isinstance(node, ast.NamedExpr):
            self._expr(node.value, scope, live)
            self._expr(node.target, scope, live)
            self._bind_target(node.target, node.value, "assign", node, scope, live=live)
        else:
            for child in ast.iter_child_nodes(node):
                if isinstance(child, ast.expr):
                    self._expr(child, scope, live)
                elif isinstance(child, ast.keyword):
                    self.owner[id(child)] = scope
                    self._expr(child.value, scope, live)

    def _bind_target(self, target, value, kind, stmt, scope, redirect=True, live=True):
        if isinstance(target, ast.Name):
            self._bind_name(target.id, kind, stmt, value, scope, redirect=redirect, live=live)
        elif isinstance(target, (ast.Attribute, ast.Subscript)):
            if live or scope is not self.module:   # a module-level statement outside the reach records no dotted write
                self._deferred.append((target, value, kind, stmt, scope))
        elif isinstance(target, ast.Starred):
            self._bind_target(target.value, None, "unpack", stmt, scope, redirect, live)
        elif isinstance(target, (ast.Tuple, ast.List)):
            elements = list(target.elts)
            paired = (isinstance(value, (ast.Tuple, ast.List)) and len(value.elts) == len(elements)
                      and not any(isinstance(e, ast.Starred) for e in elements + list(value.elts)))
            for i, t in enumerate(elements):
                if paired:
                    self._bind_target(t, value.elts[i], kind, stmt, scope, redirect, live)
                else:
                    self._bind_target(t, None, "unpack" if kind in ("assign", "augassign") else kind, stmt, scope, redirect, live)

    def _bind_name(self, name, kind, node, value, scope, origin=None, redirect=True, live=True):
        where = scope.binding_scope_for(name) if redirect else scope
        if not live and where is self.module:   # the reach: a module-scope binding only from a statement it yields
            return None
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
