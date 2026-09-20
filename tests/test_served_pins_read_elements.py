#!/usr/bin/env python3
"""A pin over a served page or a served script or style constant reads the ELEMENT, the PARSED RULE or the CODE it pins, never
text a comment can satisfy.

D1 round 1 (2026-09-19): two served comments spelled the viewport meta's own tokens, and three assertions that named the
meta were satisfied by comment text; one test passed in full against a page whose meta had lost the token it exists to
pin. The three were re-pointed at the meta element. Round 2 asked for the CLASS to be closed, not the instances: every
assertIn of a string literal over a served page's text whose literal also occurs inside a comment of that page is a pin a
comment can satisfy, and this module derives them and fails on each (round 4, 2026-09-20; the first instance beyond the
three was the timeline's touch-action pin, satisfied by two script comments that spell the declaration). Round 6
(2026-09-20): the class had been closed over the page getters only, and the kernel's served CONSTANTS (the `_*_JS` and
`_*_CSS` strings spliced into the pages) carried eight pins a served comment satisfied, one of them created by the change
that landed the census (a new comment spelled offsetHeight inside _LANDING_MOBILE_JS); module-level test functions, a
conjunction of memberships, a name bound to a slice of a page, and the ordering pins `page.index(<lit>)` were outside it
too, with live members in each.

Population, derived by an AST walk over tests/test_*.py, every method of every class and every module-level function:
`self.assertIn(<lit>, X)`, `self.assertTrue(<lit> in X)` and a bare `assert <lit> in X` (a conjunction of memberships
inside assertTrue or assert is one row per conjunct), and the position forms `X.index(<lit>)`, `X.find(<lit>)`,
`X.rindex(<lit>)`, `X.rfind(<lit>)` and `X.count(<lit>)`, where <lit> is a string literal or the variable of a
`for <name> in (<str>, ...)` loop in the same function (one row per literal; round 5, 2026-09-20: a loop variable had been
outside the derivation, and the one such pin in the suite was satisfiable by two comments), and X is one of the kernel's
served TEXTS: a call to one of its page getters, or one of its served constants (`<alias>.<_NAME_JS>`, `<alias>.<_NAME_CSS>`),
or a Name bound to either in the same function (a tuple assignment counts by position; a Name bound to a SLICE of one counts
too, judged over the whole text, so a literal a comment spells anywhere in the text flags it and the fix is the same), or a
`self.<attr>` bound to one in any method of the same class (a setUp). The getters (the zero-argument `_landing` and
`_<name>_page` functions) and the constants (the module-level `_*_JS` and `_*_CSS` names) are derived from the kernel
source and read through any module alias. Each text is rendered or read once; a membership or count row is
comment-satisfiable when its literal occurs inside a comment span of that text (a page: tests/served_css.py comment_spans,
an HTML comment, a /* */ inside a style element, a /* */ or // inside a script element; a script constant:
js_comment_spans; a style constant: css_comment_spans), an index or find row when the FIRST occurrence is comment text and
an rindex or rfind row when the LAST is, the occurrence such a pin reads. A row whose literal occurs ONLY in comments pins
prose and is reported the same way.

The fix for a row is to read the parsed rule (served_css.rules), the script's code with its comments removed
(served_css.scripts for a page's script elements, served_css.js_code or css_code for a constant, served_css.code for a
page when the token's position matters), or the element's own attribute (test_kernel_mobile._viewport_meta_tokens), never
to reword the comment: the next comment re-arms it. A pin that means to read a comment reads the comment spans
affirmatively (test_kernel_webpush's vanish-road test).

The population's floor is derived, not a literal: a second census over the same files, line by line with regular
expressions and no AST, finds every `assertIn("<lit>", X)` whose X is `<alias>.<getter>()` or `<alias>.<CONST>` inline or a
name bound to one on a line of its own (a self.<attr> in any method of the class), and every such site must be a row (so a
module the derivation stops reading fails here), the row count is at least the site count, the modules with rows cover
the modules with sites, and the form space is pinned on a synthetic module below (a form the derivation stops reading
fails there).

Bound: a body fetched over HTTP, a page from a dynamically resolved getter (`getattr(km, "_%s_page" % name)()`,
tests/test_kernel_boot_splash.py, which reads served_css.code for the tokens a comment spells), a name bound outside the
function, a literal bound by assignment rather than a loop, and assertNotIn (a comment can red it, never green it) are
outside this derivation.
"""
import ast
import glob
import os
import re
import sys
import tempfile
import unittest
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the loads: they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
km = load_source("romp_kernel_served_pins", os.path.join(BIN, "romp-kernel"))
sys.path.insert(0, HERE)
import served_css   # noqa: E402  the served page's comment spans (loads no romp code)

_GETTER = re.compile(r"^def (_landing|_[a-z_]+_page)\(\):", re.M)
_CONSTANT = re.compile(r"^(_[A-Za-z_]*_(?:JS|CSS)) = ", re.M)
_POSITION = ("index", "find", "rindex", "rfind", "count")
# the textual census of the inline forms, the derived floor: `.assertIn("<lit>", <alias>.<getter>()` and `.assertIn("<lit>",
# <alias>.<CONST>` with a literal free of backslashes (an escaped literal is a row the AST reads and this regex declines)
_INLINE = re.compile(r"""\.assertIn\(\s*(?P<q>["'])(?P<lit>(?:(?!(?P=q))[^\\\n])*)(?P=q)\s*,\s*(?P<alias>[A-Za-z_]\w*)\.(?P<name>[A-Za-z_]\w*)(?P<call>\(\))?\s*[,)]""")
# ...and the bound form: `<name> = <alias>.<getter>()` or `<name> = <alias>.<CONST>` on a line of its own (a `self.<attr>` target in
# any method of the class), then `.assertIn("<lit>", <name>)` in the same function (or `self.<attr>` anywhere in the class)
_BOUND_DEF = re.compile(r"^\s*(?P<target>(?:self\.)?[A-Za-z_]\w*)\s*=\s*(?P<alias>[A-Za-z_]\w*)\.(?P<name>[A-Za-z_]\w*)(?P<call>\(\))?\s*(?:#.*)?$")
_BOUND_USE = re.compile(r"""\.assertIn\(\s*(?P<q>["'])(?P<lit>(?:(?!(?P=q))[^\\\n])*)(?P=q)\s*,\s*(?P<target>(?:self\.)?[A-Za-z_]\w*)\s*[,)]""")
_DEF_LINE = re.compile(r"^(?P<indent>\s*)(?:async\s+)?def\s")
_CLASS_LINE = re.compile(r"^class\s")


def _kernel_source():
    with open(os.path.join(BIN, "romp-kernel"), encoding="utf-8") as f:
        return f.read()


def page_getters():
    """The kernel's zero-argument page renderers, derived from its source."""
    names = _GETTER.findall(_kernel_source())
    assert names, "no page getter derived from the kernel source"
    return sorted(set(names))


def served_constants():
    """The kernel's served script and style constants, the module-level `_*_JS` and `_*_CSS` strings, derived from its source."""
    names = _CONSTANT.findall(_kernel_source())
    assert names, "no served constant derived from the kernel source"
    return sorted(set(names))


def _text(node, getters, constants):
    """The served text a node names: a getter when node is `<alias>.<getter>()` with no arguments, a constant when node is
    `<alias>.<CONST>`; else None."""
    if isinstance(node, ast.Call) and not node.args and not node.keywords and isinstance(node.func, ast.Attribute) \
            and node.func.attr in getters and isinstance(node.func.value, ast.Name):
        return node.func.attr
    if isinstance(node, ast.Attribute) and node.attr in constants and isinstance(node.value, ast.Name) and node.value.id != "self":
        return node.attr
    return None


def _resolve(node, names, attrs, getters, constants):
    """The served text a node stands for: a getter call or constant inline, a Name bound in the function, a self.<attr> bound in
    the class; None otherwise."""
    t = _text(node, getters, constants)
    if not t and isinstance(node, ast.Name):
        t = names.get(node.id)
    if not t and isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "self":
        t = attrs.get(node.attr)
    return t


def _bind(targets, value, names, attrs, getters, constants):
    """Record Name and self.<attr> targets bound to a served text, or to a slice of one; a tuple assignment binds by position."""
    if isinstance(value, ast.Tuple) and len(targets) == 1 and isinstance(targets[0], ast.Tuple) \
            and len(targets[0].elts) == len(value.elts):
        pairs = list(zip(targets[0].elts, value.elts))
    else:
        pairs = [(t, value) for t in targets]
    for t, v in pairs:
        g = _text(v, getters, constants)
        if not g and isinstance(v, ast.Subscript):   # `fn = html[a:b]`, a slice of a bound text, judged over the whole text
            g = _resolve(v.value, names, attrs, getters, constants)
        if not g:
            continue
        if isinstance(t, ast.Name):
            names[t.id] = g
        elif isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) and t.value.id == "self":
            attrs[t.attr] = g


def _literals(node):
    """The string literals a node stands for: a str Constant, or a Tuple or List of them; None otherwise."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, (ast.Tuple, ast.List)) and node.elts and all(isinstance(e, ast.Constant) and isinstance(e.value, str) for e in node.elts):
        return [e.value for e in node.elts]
    return None


def _memberships(node):
    """[(literal node, text node)] for every membership a node asserts: `self.assertIn(lit, X, ...)`, `self.assertTrue(lit in X, ...)`
    or a bare `assert lit in X`, the last two also as a conjunction (`assert a in X and b in Y`, one pair per conjunct)."""
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        if node.func.attr == "assertIn" and len(node.args) >= 2:
            return [(node.args[0], node.args[1])]
        if node.func.attr == "assertTrue" and node.args:
            test = node.args[0]
        else:
            return []
    elif isinstance(node, ast.Assert):
        test = node.test
    else:
        return []
    tests = test.values if isinstance(test, ast.BoolOp) and isinstance(test.op, ast.And) else [test]
    return [(t.left, t.comparators[0]) for t in tests if isinstance(t, ast.Compare) and len(t.ops) == 1 and isinstance(t.ops[0], ast.In)]


def _position(node):
    """(literal node, text node, method) when node is `X.index(lit)`, `X.find(lit)`, `X.rindex(lit)`, `X.rfind(lit)` or
    `X.count(lit)`; None otherwise."""
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in _POSITION and node.args:
        return node.args[0], node.func.value, node.func.attr
    return None


def rows_of(path, getters, constants):
    """[(line, literal, text, form)] for every membership or position assertion of a literal over a served text in one test
    module; form is "in" for a membership, else the position method."""
    with open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read(), path)
    out = []
    functions = (ast.FunctionDef, ast.AsyncFunctionDef)
    groups = [[n for n in cls.body if isinstance(n, functions)] for cls in ast.walk(tree) if isinstance(cls, ast.ClassDef)]
    groups.append([n for n in tree.body if isinstance(n, functions)])   # module-level test functions (round 6, 2026-09-20)
    for fns in groups:
        attrs = {}
        for fn in fns:   # a setUp's self.<attr> binding is visible to every method
            for st in ast.walk(fn):
                if isinstance(st, ast.Assign):
                    _bind(st.targets, st.value, {}, attrs, getters, constants)
        for fn in fns:
            names = {}
            for st in ast.walk(fn):
                if isinstance(st, ast.Assign):
                    _bind(st.targets, st.value, names, attrs, getters, constants)
            text_of = lambda x: _resolve(x, names, attrs, getters, constants)
            rows = []
            for node in ast.walk(fn):
                for lit, x in _memberships(node):
                    if _literals(lit) and text_of(x):
                        rows += [(node.lineno, lit.col_offset, i, l, text_of(x), "in") for i, l in enumerate(_literals(lit))]
                pos = _position(node)
                if pos and _literals(pos[0]) and text_of(pos[1]):
                    rows += [(node.lineno, pos[0].col_offset, i, l, text_of(pos[1]), pos[2]) for i, l in enumerate(_literals(pos[0]))]
            # `for win in ("fiveHour", "sevenDay"):` binds the literals to the loop's own body: one row per literal for each
            # membership assertion of the variable inside it (a variable rebound by a later loop resolves to its own loop)
            for loop in ast.walk(fn):
                if not (isinstance(loop, ast.For) and isinstance(loop.target, ast.Name) and _literals(loop.iter)):
                    continue
                for node in [n for b in loop.body for n in ast.walk(b)]:
                    for lit, x in _memberships(node):
                        if isinstance(lit, ast.Name) and lit.id == loop.target.id and text_of(x):
                            rows += [(node.lineno, lit.col_offset, i, l, text_of(x), "in") for i, l in enumerate(_literals(loop.iter))]
            out += [(line, lit, g, form) for line, _, _, lit, g, form in sorted(rows)]
    return out


def inline_sites(path, getters, constants):
    """[(line, literal, text)] for every `assertIn("<lit>", X)` in one test module where X is `<alias>.<getter>()` or
    `<alias>.<CONST>` inline, or a Name bound to one on a line of its own earlier in the same function, or a `self.<attr>` so
    bound in any method of the class, read line by line with regular expressions and no AST: the second, independent census
    the derived floor rests on. A binding a later line rebinds keeps the served text, as the derivation reads it."""
    out, names, attrs = [], {}, {}
    with open(path, encoding="utf-8") as f:
        lines = f.read().split("\n")
    for n, line in enumerate(lines, 1):
        if _CLASS_LINE.match(line):
            attrs, names = {}, {}
        elif _DEF_LINE.match(line):
            names = {}
        m = _BOUND_DEF.match(line)
        if m and ((m.group("call") and m.group("name") in getters) or (not m.group("call") and m.group("name") in constants)):
            (attrs if m.group("target").startswith("self.") else names)[m.group("target")] = m.group("name")
        for m in _INLINE.finditer(line):
            if (m.group("call") and m.group("name") in getters) or (not m.group("call") and m.group("name") in constants):
                out.append((n, m.group("lit"), m.group("name")))
        for m in _BOUND_USE.finditer(line):
            t = m.group("target")
            if t in names or t in attrs:
                out.append((n, m.group("lit"), names.get(t) or attrs.get(t)))
    return out


def _spans(name, text):
    if name.endswith("_JS"):
        return served_css.js_comment_spans(text)
    if name.endswith("_CSS"):
        return served_css.css_comment_spans(text)
    return served_css.comment_spans(text)


class ServedPinsReadElements(unittest.TestCase):
    def test_no_assertion_over_a_served_text_is_satisfiable_by_a_comment(self):
        getters, constants = page_getters(), served_constants()
        texts = {g: getattr(km, g)() for g in getters}
        texts.update({c: getattr(km, c) for c in constants})
        comments = {name: _spans(name, text) for name, text in texts.items()}
        self.assertTrue(all(comments[g] for g in getters), "every served page carries comments (the derivation read them): %r" % ({g: len(comments[g]) for g in getters},))
        # the span scanner is chosen by the constant's kind (a JS constant read by the CSS scanner yields nothing): a constant
        # whose text spells a comment opener yields a span, and both kinds yield spans somewhere; the constants with no span
        # spell no opener at all (the population, derived here, names them)
        opener = re.compile(r"//|/\*")
        self.assertEqual([c for c in constants if opener.search(texts[c]) and not comments[c]], [],
                         "a served constant spells a comment opener the scanner read as no comment; the scanner is chosen by the name's kind")
        self.assertTrue([c for c in constants if c.endswith("_JS") and comments[c]],
                        "script constants with comments read: %r" % ({c: len(comments[c]) for c in constants},))   # no style constant carries a comment today; the opener check above reads one when it appears
        rows, sites = [], []
        # this module holds no pin over a served text (asserted, by the derivation, which reads the synthetic module below as
        # the string it is); the line-based textual census cannot tell that string from code, so the module is outside both
        self.assertEqual(rows_of(__file__, getters, constants), [], "the census module itself pins nothing over a served text")
        for path in sorted(glob.glob(os.path.join(HERE, "test_*.py"))):
            fname = os.path.basename(path)
            if os.path.realpath(path) == os.path.realpath(__file__):
                continue
            rows += [(fname, line, lit, name, form) for line, lit, name, form in rows_of(path, getters, constants)]
            sites += [(fname, line, lit, name) for line, lit, name in inline_sites(path, getters, constants)]
        # the floor, derived: every inline site the textual census finds is a row the derivation found (so a module the
        # derivation stops reading, or an inline form it stops reading, fails here), and the population is at least that
        self.assertTrue(sites, "the textual census found no inline assertIn over a served text")
        self.assertEqual(sorted(set(sites) - {(f, line, lit, name) for f, line, lit, name, form in rows if form == "in"}), [],
                         "inline sites the textual census reads and the derivation does not")
        self.assertGreaterEqual(len(rows), len(sites), "the population is every assertion of a literal over a served text across the suite: %d rows, %d inline sites" % (len(rows), len(sites)))
        self.assertGreaterEqual(len({r[0] for r in rows}), len({s[0] for s in sites}), "from every module with an inline site")
        self.assertTrue({r[3] for r in rows} & set(getters) and {r[3] for r in rows} & set(constants), "rows over pages and over constants both derived")
        bad = []
        for fname, line, lit, name, form in rows:
            text = texts[name]
            hits = [m.start() for m in re.finditer(re.escape(lit), text)]
            inside = [h for h in hits if any(s <= h < e for s, e in comments[name])]
            if form in ("index", "find"):
                flagged = bool(hits) and hits[0] in inside      # the pin reads the first occurrence
            elif form in ("rindex", "rfind"):
                flagged = bool(hits) and hits[-1] in inside     # the last
            else:
                flagged = bool(inside)                          # a membership or a count: any occurrence
            if flagged:
                bad.append("%s:%d %r %s %s: %d of %d occurrences inside a comment%s" % (
                    fname, line, lit, form, name + ("()" if name in getters else ""), len(inside), len(hits), " (prose only)" if len(inside) == len(hits) else ""))
        self.assertEqual(bad, [], "a pin a served comment can satisfy; read the parsed rule, the code with its comments removed or the element instead:\n" + "\n".join(bad))

    def test_the_derivation_reads_the_forms_it_claims(self):
        # the population is a derivation, so its form space is pinned: a getter call inline, a Name bound in the function,
        # a tuple assignment by position, a self.<attr> bound in setUp; a Name bound to something else is not a row. Round 5
        # (2026-09-20): a loop variable over a tuple or list of literals (one row per literal), assertTrue(lit in page) and a
        # bare assert; a literal bound by assignment stays outside (the bound in the docstring). Round 6 (2026-09-20): a served
        # constant inline and bound, a module-level function, a conjunction inside assert or assertTrue (one row per conjunct),
        # a Name bound to a slice of a page, the position forms index, find, rindex, rfind and count; a dynamically resolved
        # getter (getattr) stays outside (the bound)
        src = '''
class T(unittest.TestCase):
    def setUp(self):
        self.html = km._landing()
    def test_a(self):
        self.assertIn("x", km._chat_page())
        page = km._feed_page()
        self.assertIn("y", page)
        js, css = km._timeline_page(), other()
        self.assertIn("z", js)
        self.assertIn("w", css)
        self.assertIn("v", self.html)
        self.assertNotIn("u", page)
        for w in ("p", "q"):
            self.assertIn(w, page, "both")
        for w in ["r"]:
            self.assertTrue(w in page)
        self.assertTrue("s" in self.html, "a membership test through assertTrue")
        assert "t" in page
        bound = "o"
        self.assertIn(bound, page)
        self.assertTrue("n" not in page)
        self.assertIn("m", km._LANDING_MOBILE_JS)
        mob = km._LANDING_MOBILE_JS
        self.assertIn("l", mob)
        assert "k" in page and "j" in mob and "i" in other()
        fn = page[3:9]
        self.assertIn("h", fn)
        self.assertLess(page.index("g"), page.index("f"))
        self.assertEqual(mob.count("e"), 2)
        page.find("d"); page.rindex("c"); page.rfind("b")
        dyn = getattr(km, "_%s_page" % "chat")()
        self.assertIn("a", dyn)

def test_module_level():
    html = km._landing()
    assert "x1" in html and "x2" in html
    self.assertIn("x3", km._landing())
'''
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write(src)
        try:
            rows = rows_of(f.name, page_getters(), served_constants())
            sites = inline_sites(f.name, page_getters(), served_constants())
        finally:
            os.unlink(f.name)
        self.assertEqual(rows, [(6, "x", "_chat_page", "in"), (8, "y", "_feed_page", "in"), (10, "z", "_timeline_page", "in"), (12, "v", "_landing", "in"),
                                (15, "p", "_feed_page", "in"), (15, "q", "_feed_page", "in"), (17, "r", "_feed_page", "in"), (18, "s", "_landing", "in"), (19, "t", "_feed_page", "in"),
                                (23, "m", "_LANDING_MOBILE_JS", "in"), (25, "l", "_LANDING_MOBILE_JS", "in"), (26, "k", "_feed_page", "in"), (26, "j", "_LANDING_MOBILE_JS", "in"),
                                (28, "h", "_feed_page", "in"), (29, "g", "_feed_page", "index"), (29, "f", "_feed_page", "index"), (30, "e", "_LANDING_MOBILE_JS", "count"),
                                (31, "d", "_feed_page", "find"), (31, "c", "_feed_page", "rindex"), (31, "b", "_feed_page", "rfind"),
                                (37, "x1", "_landing", "in"), (37, "x2", "_landing", "in"), (38, "x3", "_landing", "in")])
        # the textual census reads the inline form and the one-line bound form (a Name, a self.<attr>), and each site is a row;
        # the tuple assignment, the loop, assertTrue, assert, the slice and the position forms are the derivation's alone
        self.assertEqual(sites, [(6, "x", "_chat_page"), (8, "y", "_feed_page"), (12, "v", "_landing"), (23, "m", "_LANDING_MOBILE_JS"),
                                 (25, "l", "_LANDING_MOBILE_JS"), (38, "x3", "_landing")])
        self.assertTrue(set(sites) <= {(line, lit, name) for line, lit, name, form in rows if form == "in"})


if __name__ == "__main__":
    unittest.main()
