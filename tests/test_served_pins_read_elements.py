#!/usr/bin/env python3
"""A pin over a served page reads the ELEMENT or the PARSED RULE it pins, never page text a comment can satisfy.

D1 round 1 (2026-09-19): two served comments spelled the viewport meta's own tokens, and three assertions that named the
meta were satisfied by comment text; one test passed in full against a page whose meta had lost the token it exists to
pin. The three were re-pointed at the meta element. Round 2 asked for the CLASS to be closed, not the instances: every
assertIn of a string literal over a served page's text whose literal also occurs inside a comment of that page is a pin a
comment can satisfy, and this module derives them and fails on each (round 4, 2026-09-20; the first instance beyond the
three was the timeline's touch-action pin, satisfied by two script comments that spell the declaration).

Population, derived by an AST walk over tests/test_*.py: `self.assertIn(<str literal>, X)` where X is a call to one of the
kernel's page getters, or a Name bound to such a call in the same function (a tuple assignment counts by position), or a
`self.<attr>` bound to one in any method of the same class (a setUp). The getters are derived from the kernel source: the
zero-argument `_landing` and `_<name>_page` functions, called through any module alias. Each getter is rendered once; a row
is comment-satisfiable when its literal occurs inside a comment span of that page (tests/served_css.py comment_spans: an
HTML comment, a /* */ inside a style element, a /* */ or // inside a script element). A row whose literal occurs ONLY in
comments pins prose and is reported the same way.

The fix for a row is to read the parsed rule (served_css.rules), the script's code with its comments removed
(served_css.scripts), or the element's own attribute (test_kernel_mobile._viewport_meta_tokens), never to reword the
comment: the next comment re-arms it.

Bound: a body fetched over HTTP, a name bound outside the function, a slice of the page, html.count and html.index pins,
and assertNotIn (a comment can red it, never green it) are outside this derivation.
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


def page_getters():
    """The kernel's zero-argument page renderers, derived from its source."""
    with open(os.path.join(BIN, "romp-kernel"), encoding="utf-8") as f:
        names = _GETTER.findall(f.read())
    assert names, "no page getter derived from the kernel source"
    return sorted(set(names))


def _getter_call(node, getters):
    """The getter name when node is `<alias>.<getter>()` with no arguments, else None."""
    if isinstance(node, ast.Call) and not node.args and not node.keywords and isinstance(node.func, ast.Attribute) \
            and node.func.attr in getters and isinstance(node.func.value, ast.Name):
        return node.func.attr
    return None


def _bind(targets, value, names, attrs, getters):
    """Record Name and self.<attr> targets bound to a getter call; a tuple assignment binds by position."""
    pairs = []
    if isinstance(value, ast.Tuple) and len(targets) == 1 and isinstance(targets[0], ast.Tuple) \
            and len(targets[0].elts) == len(value.elts):
        pairs = list(zip(targets[0].elts, value.elts))
    else:
        pairs = [(t, value) for t in targets]
    for t, v in pairs:
        g = _getter_call(v, getters)
        if not g:
            continue
        if isinstance(t, ast.Name):
            names[t.id] = g
        elif isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) and t.value.id == "self":
            attrs[t.attr] = g


def rows_of(path, getters):
    """[(line, literal, getter)] for every assertIn of a literal over a getter's page in one test module."""
    with open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read(), path)
    out = []
    for cls in [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]:
        attrs = {}
        methods = [n for n in cls.body if isinstance(n, ast.FunctionDef)]
        for fn in methods:   # a setUp's self.<attr> binding is visible to every method
            for st in ast.walk(fn):
                if isinstance(st, ast.Assign):
                    _bind(st.targets, st.value, {}, attrs, getters)
        for fn in methods:
            names = {}
            for st in ast.walk(fn):
                if isinstance(st, ast.Assign):
                    _bind(st.targets, st.value, names, {}, getters)
            for call in ast.walk(fn):
                if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute) and call.func.attr == "assertIn"
                        and len(call.args) >= 2 and isinstance(call.args[0], ast.Constant) and isinstance(call.args[0].value, str)):
                    continue
                x = call.args[1]
                g = _getter_call(x, getters)
                if not g and isinstance(x, ast.Name):
                    g = names.get(x.id)
                if not g and isinstance(x, ast.Attribute) and isinstance(x.value, ast.Name) and x.value.id == "self":
                    g = attrs.get(x.attr)
                if g:
                    out.append((call.lineno, call.args[0].value, g))
    return out


class ServedPinsReadElements(unittest.TestCase):
    def test_no_assertion_over_a_served_page_is_satisfiable_by_a_comment(self):
        getters = page_getters()
        pages = {g: getattr(km, g)() for g in getters}
        comments = {g: served_css.comment_spans(p) for g, p in pages.items()}
        self.assertTrue(all(comments.values()), "every served page carries comments (the derivation read them): %r" % ({g: len(c) for g, c in comments.items()},))
        rows = []
        for path in sorted(glob.glob(os.path.join(HERE, "test_*.py"))):
            for line, lit, g in rows_of(path, getters):
                rows.append((os.path.basename(path), line, lit, g))
        self.assertGreater(len(rows), 100, "the population is every assertIn of a literal over a served page across the suite: %d rows" % len(rows))
        self.assertGreater(len({r[0] for r in rows}), 5, "from more than a handful of modules")
        bad = []
        for fname, line, lit, g in rows:
            page = pages[g]
            hits = [m.start() for m in re.finditer(re.escape(lit), page)]
            inside = [h for h in hits if any(s <= h < e for s, e in comments[g])]
            if inside:
                bad.append("%s:%d %r over %s(): %d of %d occurrences inside a comment%s" % (
                    fname, line, lit, g, len(inside), len(hits), " (prose only)" if len(inside) == len(hits) else ""))
        self.assertEqual(bad, [], "a pin a served comment can satisfy; read the parsed rule, the script's code or the element instead:\n" + "\n".join(bad))

    def test_the_derivation_reads_the_forms_it_claims(self):
        # the population is a derivation, so its form space is pinned: a getter call inline, a Name bound in the function,
        # a tuple assignment by position, a self.<attr> bound in setUp; a Name bound to something else is not a row
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
'''
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write(src)
        try:
            rows = rows_of(f.name, page_getters())
        finally:
            os.unlink(f.name)
        self.assertEqual(rows, [(6, "x", "_chat_page"), (8, "y", "_feed_page"), (10, "z", "_timeline_page"), (12, "v", "_landing")])


if __name__ == "__main__":
    unittest.main()
