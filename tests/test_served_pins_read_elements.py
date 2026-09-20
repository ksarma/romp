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
too, with live members in each. Round 7 (2026-09-20): the constants had been a NAME ROSTER (`_*_JS`, `_*_CSS`), which
missed a bare script constant with eight comment spans and four live pins (the timeline's boot script), every `_*_HTML`
constant and the served SVG and theme-reader fragments; the constants are derived by rule now, and a `for` variable over
a tuple of served texts, which had bound nothing, is read.

Population, derived by an AST walk over tests/test_*.py, every method of every class and every module-level function:
`self.assertIn(<lit>, X)`, `self.assertTrue(<lit> in X)` and a bare `assert <lit> in X` (a conjunction of memberships
inside assertTrue or assert is one row per conjunct), and the position forms `X.index(<lit>)`, `X.find(<lit>)`,
`X.rindex(<lit>)`, `X.rfind(<lit>)` and `X.count(<lit>)`, where <lit> is a string literal or the variable of a
`for <name> in (<str>, ...)` loop or comprehension in the same function (one row per literal; round 5, 2026-09-20: a loop
variable had been outside the derivation, and the one such pin in the suite was satisfiable by two comments), and X is one
of the kernel's served TEXTS: a call to one of its page getters, or one of its served constants (`<alias>.<_NAME>`), or a
Name bound to either in the same function (a tuple assignment counts by position; a Name bound to a SLICE of one counts
too, judged over the whole text, so a literal a comment spells anywhere in the text flags it and the fix is the same), or
the variable of a `for <name> in (<text>, <text>)` loop over served texts (one row per text, inside the loop's body;
round 7), or a `self.<attr>` bound to one in any method of the same class (a setUp). The getters are derived from the
kernel source by rule: the functions named `_landing`, `_<name>_page`, `_<name>_js` or `_<name>_css` that a call with no
arguments renders (no parameter, or every parameter defaulted; round 7: the served script functions, the service worker,
the reload and shim cores and the timeline axis, had been outside the getter rule with ten live pins), a page read for
every kind of comment and a script or style getter by the scanner of its kind; the constants from the LOADED kernel by rule,
not from a roster of names (round 7): every module-level str attribute named `_[A-Z][A-Z0-9_]*` whose text a rendered page
carries, or whose name ends `_JS`, `_CSS` or `_HTML` (a text served at a route of its own, or spliced under a condition the
hermetic render does not meet), each with the KINDS of element its text lands in (inside a script element's content, inside
a style element's, or markup; by suffix where the page does not carry it), read through any module alias. The round-6
roster is kept as a floor the rule may not shrink below. A short constant a page carries by coincidence is in the set and
harmless: no scanner finds a comment in it, and a pin over it is judged over text the page does carry. Each text is
rendered or read once; a membership or count row is comment-satisfiable when its literal occurs inside a comment span of
that text (a page: tests/served_css.py comment_spans, an HTML comment, a /* */ inside a style element, a /* */ or // inside
a script element; a constant: the scanner of each kind it lands in, js_comment_spans for script, css_comment_spans for
style, comment_spans for markup, their union for a text that lands in more than one), an index or find row when the FIRST
occurrence is comment text and an rindex or rfind row when the LAST is, the occurrence such a pin reads. A row whose
literal occurs ONLY in comments pins prose and is reported the same way.

The fix for a row is to read the parsed rule (served_css.rules), the script's code with its comments removed
(served_css.scripts for a page's script elements, served_css.js_code or css_code for a constant, served_css.code for a
page or a markup constant when the token's position matters), or the element's own attribute
(test_kernel_mobile._viewport_meta_tokens), never to reword the comment: the next comment re-arms it. A pin that means to
read a comment reads the comment spans affirmatively (test_kernel_webpush's vanish-road test).

The population's floor is derived, not a literal: a second census over the same files, by logical line with regular
expressions and no AST, finds the `assertIn("<lit>", X)`, `assert "<lit>" in X`, `assertTrue("<lit>" in X)` and
`X.index("<lit>")` (find, rindex, rfind, count) forms whose X is `<alias>.<getter>()` or `<alias>.<CONST>` inline, or a
name bound to one by an assignment of its own (a self.<attr> in any method of the class), by a tuple assignment, or by a
`for` over served texts inside that loop; every such site must be a row (so a module with such a site the derivation stops
reading fails here), the row count is at least the site count, and the modules with rows are exactly the modules with sites
(a module the derivation reads in a form the textual census does not, or the reverse, fails here); the form space is
pinned on a synthetic module below (a form the derivation stops reading fails there), built over every derived getter and
over a derived constant of each kind. The container NAMES the tests pin are derived from the test text on their own and
held to the kernel-derived getters and constants (a getter the tests call or a served str the tests assert over that the
derivation does not read fails there; round 7).

Bound: a body fetched over HTTP, a page from a dynamically resolved getter (`getattr(km, "_%s_page" % name)()`,
tests/test_kernel_boot_splash.py, which reads served_css.code for the tokens a comment spells), a getter called WITH
arguments (`_shim_core_js("chat")` renders another text), a text served under a name with none of the suffixes the rules
read (the web app manifest; the `_reload_core` function), a name bound outside the function, a literal bound by assignment
rather than a loop, and assertNotIn (a comment can red it, never green it) are outside this derivation.
"""
import ast
import bisect
import functools
import glob
import io
import os
import re
import sys
import tempfile
import tokenize
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

_GETTER = re.compile(r"^def (_landing|_[a-z_]+_(?:page|js|css))\(([^)]*)\):", re.M)
_GETTER_NAME = re.compile(r"_landing|_[a-z_]+_(?:page|js|css)")
# the round-6 roster of served constants, kept as the floor the rule-derived set may not shrink below (round 7, 2026-09-20)
_ROSTER = re.compile(r"^(_[A-Za-z_]*_(?:JS|CSS)) = ", re.M)
_CAPS = re.compile(r"_[A-Z][A-Z0-9_]*")
_SUFFIX_KIND = (("_JS", "script"), ("_CSS", "style"), ("_HTML", "markup"))
_SCANNER = {"script": served_css.js_comment_spans, "style": served_css.css_comment_spans, "markup": served_css.comment_spans}
_OPENER = {"script": re.compile(r"//|/\*"), "style": re.compile(r"/\*"), "markup": re.compile(r"<!--")}
_POSITION = ("index", "find", "rindex", "rfind", "count")
# the textual census, by logical line: a literal free of backslashes (an escaped literal is a row the AST reads and this
# regex declines), adjacent literals read as the one string Python joins them into (`"a" "b"`, across the joined lines of a
# statement), and a served text `<alias>.<getter>()` or `<alias>.<CONST>`
_LIT1 = r"""(?:"[^"\\\n]*"|'[^'\\\n]*')"""
_LIT = r"(?P<lit>" + _LIT1 + r"(?:\s+" + _LIT1 + r")*)"
_TEXT = r"(?P<alias>(?!self\b)[A-Za-z_]\w*)\.(?P<name>[A-Za-z_]\w*)(?P<call>\(\))?"   # a self.<attr> is a bound name, not a served text
_NAME = r"(?P<target>(?:self\.)?[A-Za-z_]\w*)"
_INLINE = re.compile(r"\.assertIn\(\s*" + _LIT + r"\s*,\s*" + _TEXT + r"\s*[,)]")
_BOUND_USE = re.compile(r"\.assertIn\(\s*" + _LIT + r"\s*,\s*" + _NAME + r"\s*[,)]")
_ASSERT_LINE = re.compile(r"^\s*assert\s|\.assertTrue\(")
_IN_INLINE = re.compile(_LIT + r"\s+in\s+" + _TEXT + r"(?![\w.(\[])")
_IN_BOUND = re.compile(_LIT + r"\s+in\s+" + _NAME + r"(?![\w.(\[])")
_POS_INLINE = re.compile(_TEXT + r"\.(?P<form>index|find|rindex|rfind|count)\(\s*" + _LIT + r"\s*[,)]")
_POS_BOUND = re.compile(r"(?<![\w.])" + _NAME + r"\.(?P<form>index|find|rindex|rfind|count)\(\s*" + _LIT + r"\s*[,)]")
_BOUND_DEF = re.compile(r"^\s*" + _NAME + r"\s*=\s*" + _TEXT + r"\s*(?:#.*)?$")
_ITEM = r"[A-Za-z_]\w*\.[A-Za-z_]\w*(?:\(\))?"
_TUPLE_DEF = re.compile(r"^\s*(?P<targets>[A-Za-z_]\w*(?:\s*,\s*[A-Za-z_]\w*)+)\s*=\s*(?P<values>.+?)\s*(?:#.*)?$")
_ITEM_ONLY = re.compile(r"^" + _ITEM + r"$")
_FOR_TEXTS = re.compile(r"^(?P<indent>\s*)for\s+(?P<target>[A-Za-z_]\w*)\s+in\s+[(\[]\s*(?P<values>" + _ITEM + r"(?:\s*,\s*" + _ITEM + r")*)\s*,?\s*[)\]]\s*:")
_TEXT_ITEM = re.compile(r"([A-Za-z_]\w*)\.([A-Za-z_]\w*)(\(\))?")
_DEF_LINE = re.compile(r"^(?P<indent>\s*)(?:async\s+)?def\s")
_CLASS_LINE = re.compile(r"^class\s")


def _kernel_source():
    with open(os.path.join(BIN, "romp-kernel"), encoding="utf-8") as f:
        return f.read()


def page_getters():
    """The kernel's served-text getters, derived from its source by rule: the functions named `_landing`, `_<name>_page`,
    `_<name>_js` or `_<name>_css` that a call with no arguments renders (no parameter, or every parameter defaulted)."""
    names = [n for n, params in _GETTER.findall(_kernel_source()) if not params.strip() or all("=" in p for p in params.split(","))]
    assert names, "no served-text getter derived from the kernel source"
    return sorted(set(names))


def getter_kind(name):
    """'script' for a `_<name>_js` getter, 'style' for `_<name>_css`, 'markup' for a page (read for every kind of comment)."""
    return "script" if name.endswith("_js") else "style" if name.endswith("_css") else "markup"


@functools.lru_cache(maxsize=None)
def pages():
    """{getter: the rendered page}, rendered once per process."""
    return {g: getattr(km, g)() for g in page_getters()}


def _suffix_kind(name):
    return next((kind for suffix, kind in _SUFFIX_KIND if name.endswith(suffix)), None)


def _kind_at(spans, starts, pos):
    """The kind of element a page offset sits in: 'script' or 'style' inside an element's content span, else 'markup'."""
    i = bisect.bisect_right(starts, pos) - 1
    if i >= 0 and spans[i][0] <= pos < spans[i][1]:
        return spans[i][2]
    return "markup"


def landing_kinds(text):
    """The kinds of element the occurrences of a text sit in across the rendered pages (served_css.element_spans); empty when
    no page carries it."""
    kinds = set()
    for g, page in pages().items():
        spans = _element_spans(g)
        starts = [s for s, _, _ in spans]
        start = 0
        while len(kinds) < 3:
            i = page.find(text, start)
            if i < 0:
                break
            kinds.add(_kind_at(spans, starts, i))
            start = i + 1
    return kinds


@functools.lru_cache(maxsize=None)
def _element_spans(getter):
    return served_css.element_spans(pages()[getter])


@functools.lru_cache(maxsize=None)
def served_constants():
    """{name: frozenset of kinds} for the kernel's served constants, derived by RULE from the loaded kernel (round 7,
    2026-09-20; a `_*_JS`/`_*_CSS` name roster had missed _TIMELINE_BOOT, a script constant with comments and live pins, and
    every `_*_HTML` constant): every module-level str attribute named `_[A-Z][A-Z0-9_]*` whose text a rendered page carries
    (kinds: the element kinds of its landings) or whose name ends `_JS`, `_CSS` or `_HTML` (a text served at a route of its
    own or spliced under a condition the hermetic render does not meet; its kind by suffix, joined with any landing's)."""
    out = {}
    for name in dir(km):
        if not _CAPS.fullmatch(name):
            continue
        text = getattr(km, name)
        if not isinstance(text, str) or not text:
            continue
        kinds = landing_kinds(text)
        if _suffix_kind(name):
            kinds.add(_suffix_kind(name))
        if kinds:
            out[name] = frozenset(kinds)
    assert out, "no served constant derived from the loaded kernel"
    return out


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


def _loops(fn):
    """[(variable, iterable node, body nodes)] for every `for` statement and comprehension generator in a function whose
    target is one Name: the body is the loop's statements, or the comprehension's element and conditions."""
    out = []
    for node in ast.walk(fn):
        if isinstance(node, ast.For) and isinstance(node.target, ast.Name):
            out.append((node.target.id, node.iter, [n for b in node.body for n in ast.walk(b)]))
        elif isinstance(node, (ast.ListComp, ast.SetComp, ast.GeneratorExp)):
            for gen in node.generators:
                if isinstance(gen.target, ast.Name):
                    out.append((gen.target.id, gen.iter, [n for e in [node.elt] + gen.ifs for n in ast.walk(e)]))
        elif isinstance(node, ast.DictComp):
            for gen in node.generators:
                if isinstance(gen.target, ast.Name):
                    out.append((gen.target.id, gen.iter, [n for e in [node.key, node.value] + gen.ifs for n in ast.walk(e)]))
    return out


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
            # a loop variable, bound to the loop's own body (a variable rebound by a later loop resolves to its own loop):
            # `for win in ("fiveHour", "sevenDay"):` binds the LITERALS, one row per literal for each membership or position
            # form of the variable over a text (round 5, 2026-09-20); `for page in (km._feed_page(), km._files_page()):` binds
            # the TEXTS, one row per text for each membership or position form of a literal over the variable (round 7,
            # 2026-09-20: a For target had bound nothing, so every membership over it was outside the population)
            for var, it, body in _loops(fn):
                lits = _literals(it)
                texts = [text_of(e) for e in it.elts] if isinstance(it, (ast.Tuple, ast.List)) and it.elts else []
                for node in body:
                    forms = [(lit, x, "in") for lit, x in _memberships(node)]
                    pos = _position(node)
                    if pos:
                        forms.append(pos)
                    for lit, x, form in forms:
                        if lits and isinstance(lit, ast.Name) and lit.id == var and text_of(x):
                            rows += [(node.lineno, lit.col_offset, i, l, text_of(x), form) for i, l in enumerate(lits)]
                        elif texts and all(texts) and _literals(lit) and isinstance(x, ast.Name) and x.id == var:
                            rows += [(node.lineno, lit.col_offset, i * len(texts) + j, l, g, form) for i, l in enumerate(_literals(lit)) for j, g in enumerate(texts)]
            out += [(line, lit, g, form) for line, _, _, lit, g, form in sorted(rows)]
    return out


def _logical_lines(source):
    """[(indent, text, at)] for every logical line of a module, the physical lines of a statement that continues inside
    brackets joined by a space, read by the tokenizer and no AST; `at(offset)` is the physical line number an offset into
    text sits on (the derivation's line for a position form is the receiver's own line, which a two-line assertLess puts
    after the statement's first)."""
    lines = source.split("\n")
    def logical(first, last):
        text, starts = "", []
        for n in range(first, last + 1):
            starts.append((len(text), n))
            text += lines[n - 1].strip() + " "
        at = lambda pos: starts[bisect.bisect_right([o for o, _ in starts], pos) - 1][1]
        return (len(lines[first - 1]) - len(lines[first - 1].lstrip()), text.rstrip(" ") if last > first else lines[first - 1], at)
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (tokenize.TokenError, SyntaxError):
        return [logical(n, n) for n in range(1, len(lines) + 1)]
    out, start = [], None
    for tok in tokens:
        if tok.type in (tokenize.NL, tokenize.COMMENT, tokenize.ENCODING, tokenize.INDENT, tokenize.DEDENT, tokenize.ENDMARKER):
            continue
        if start is None:
            start = tok.start[0]
        if tok.type == tokenize.NEWLINE:
            out.append(logical(start, tok.end[0]))
            start = None
    return out


def _bound_items(values):
    return [(m.group(2), bool(m.group(3))) for m in _TEXT_ITEM.finditer(values)]


def _split_top(text):
    """The comma-separated items of a tuple's right-hand side, split outside brackets and quotes."""
    out, depth, buf, quote = [], 0, "", ""
    for c in text:
        if quote:
            buf += c
            if c == quote:
                quote = ""
            continue
        if c in "'\"":
            quote = c
        elif c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        if c == "," and depth == 0:
            out.append(buf.strip())
            buf = ""
        else:
            buf += c
    out.append(buf.strip())
    return out


def _literal(lits):
    """The string a run of adjacent literals stands for."""
    return "".join(piece[1:-1] for piece in re.findall(_LIT1, lits))


def textual_census(path, getters, constants):
    """(sites, containers): sites is [(line, literal, text, form)] for every membership or position form of a literal over a
    served text this regex census reads in one test module, by logical line and no AST, the second, independent census the
    derived floor rests on: `assertIn("<lit>", X)`, an `assert "<lit>" in X` or `assertTrue("<lit>" in X)` line (every
    conjunct on it), and `X.index("<lit>")` with find, rindex, rfind and count, where X is `<alias>.<getter>()` or
    `<alias>.<CONST>` inline, a Name bound to one by an assignment of its own earlier in the same function (a `self.<attr>`
    so bound in any method of the class), by a tuple assignment, or by a `for` over served texts inside that loop (one site per
    text). A binding a later line rebinds keeps the served text, as the derivation reads it. containers is the set of
    (name, called) for every `<alias>.<name>` the module uses as a container in one of those forms, whatever the name, the
    NAMES the tests pin, read on their own for the check against the kernel-derived getters and constants (round 7)."""
    sites, containers, names, attrs, loops = [], set(), {}, {}, []
    with open(path, encoding="utf-8") as f:
        source = f.read()
    served = lambda name, call: (name in getters) if call else (name in constants)
    for indent, line, at in _logical_lines(source):
        loops = [l for l in loops if indent > l[0]]   # a for-binding ends with the loop's body
        if _CLASS_LINE.match(line):
            attrs, names = {}, {}
        elif _DEF_LINE.match(line):
            names = {}
        m = _BOUND_DEF.match(line)
        if m:
            (attrs if m.group("target").startswith("self.") else names)[m.group("target")] = [(m.group("name"), bool(m.group("call")))]
        m = _TUPLE_DEF.match(line)
        if m:
            targets = [t.strip() for t in m.group("targets").split(",")]
            values = _split_top(m.group("values"))
            if len(targets) == len(values):
                for t, v in zip(targets, values):
                    if _ITEM_ONLY.match(v):
                        names[t] = _bound_items(v)
        m = _FOR_TEXTS.match(line)
        if m:
            loops.append((len(m.group("indent")), m.group("target"), _bound_items(m.group("values"))))
        bound = dict(names)
        bound.update(attrs)
        for lindent, target, items in loops:
            bound[target] = items
        def use(items, lit, form, n):
            for name, call in items:
                containers.add((name, call))
                if served(name, call):
                    sites.append((n, lit, name, form))
        # the site's line is the derivation's: where `.assertIn(` or the position form's receiver sits; an assert or an
        # assertTrue statement's first line
        for m in _INLINE.finditer(line):
            use([(m.group("name"), bool(m.group("call")))], _literal(m.group("lit")), "in", at(m.start()))
        for m in _BOUND_USE.finditer(line):
            if m.group("target") in bound:
                use(bound[m.group("target")], _literal(m.group("lit")), "in", at(m.start()))
        if _ASSERT_LINE.search(line):
            for m in _IN_INLINE.finditer(line):
                use([(m.group("name"), bool(m.group("call")))], _literal(m.group("lit")), "in", at(0))
            for m in _IN_BOUND.finditer(line):
                if m.group("target") in bound:
                    use(bound[m.group("target")], _literal(m.group("lit")), "in", at(0))
        for m in _POS_INLINE.finditer(line):
            use([(m.group("name"), bool(m.group("call")))], _literal(m.group("lit")), m.group("form"), at(m.start()))
        for m in _POS_BOUND.finditer(line):
            if m.group("target") in bound:
                use(bound[m.group("target")], _literal(m.group("lit")), m.group("form"), at(m.start()))
    return sites, containers


def inline_sites(path, getters, constants):
    """The textual census's sites alone (textual_census)."""
    return textual_census(path, getters, constants)[0]


def _spans(kinds, text):
    return sorted({sp for k in kinds for sp in _SCANNER[k](text)})


class ServedPinsReadElements(unittest.TestCase):
    def test_no_assertion_over_a_served_text_is_satisfiable_by_a_comment(self):
        getters, constants = page_getters(), served_constants()
        texts = dict(pages())
        texts.update({c: getattr(km, c) for c in constants})
        kinds = {g: frozenset([getter_kind(g)]) for g in getters}
        kinds.update(constants)
        comments = {name: _spans(kinds[name], texts[name]) for name in texts}
        pages_ = [g for g in getters if getter_kind(g) == "markup"]
        self.assertTrue(pages_ and [g for g in getters if getter_kind(g) == "script"], "page getters and script getters both derived: %r" % (getters,))
        self.assertTrue(all(comments[g] for g in pages_), "every served page carries comments (the derivation read them): %r" % ({g: len(comments[g]) for g in pages_},))
        # the constants are derived by rule from the loaded kernel; the round-6 roster (the source's `_*_JS`/`_*_CSS` names) is
        # the floor the rule may not shrink below, and the rule reaches past it (a script constant outside the roster, an
        # HTML constant), each failing on an empty side
        roster = set(_ROSTER.findall(_kernel_source()))
        self.assertTrue(roster, "no `_*_JS`/`_*_CSS` constant in the kernel source")
        self.assertEqual(sorted(roster - set(constants)), [], "roster constants the rule-derived set does not reach")
        beyond = {c: sorted(constants[c]) for c in constants if c not in roster}
        self.assertTrue([c for c, k in beyond.items() if k == ["script"] and not c.endswith("_JS")], "a bare script constant outside the roster: %r" % (beyond,))
        self.assertTrue([c for c in beyond if c.endswith("_HTML")], "an HTML constant outside the roster: %r" % (beyond,))
        self.assertTrue([c for c, k in beyond.items() if "markup" in k], "a markup constant outside the roster: %r" % (beyond,))
        # the span scanner is chosen by the KINDS of element the constant's text lands in (a JS constant read by the CSS scanner
        # yields nothing): a constant whose text spells an opener of one of its kinds yields a span, and every kind yields
        # spans somewhere or, where none does today (no style constant carries a comment), that is recorded by the opener check
        self.assertEqual([c for c in kinds if any(_OPENER[k].search(texts[c]) for k in kinds[c]) and not comments[c]], [],
                         "a served text spells a comment opener of its kind that the scanner read as no comment")
        self.assertTrue([c for c in constants if constants[c] == {"script"} and comments[c]],
                        "script constants with comments read: %r" % ({c: len(comments[c]) for c in constants},))
        self.assertTrue([c for c in constants if "markup" in constants[c] and comments[c]] or
                        not [c for c in constants if "markup" in constants[c] and "<!--" in texts[c]],
                        "a markup constant spelling an HTML comment yields a span")
        rows, sites, pinned = [], [], set()
        # this module holds no pin over a served text (asserted, by the derivation, which reads the synthetic module below as
        # the string it is); the line-based textual census cannot tell that string from code, so the module is outside both
        self.assertEqual(rows_of(__file__, getters, constants), [], "the census module itself pins nothing over a served text")
        for path in sorted(glob.glob(os.path.join(HERE, "test_*.py"))):
            fname = os.path.basename(path)
            if os.path.realpath(path) == os.path.realpath(__file__):
                continue
            rows += [(fname, line, lit, name, form) for line, lit, name, form in rows_of(path, getters, constants)]
            found, containers = textual_census(path, getters, constants)
            sites += [(fname, line, lit, name, form) for line, lit, name, form in found]
            pinned |= containers
        # the floor, derived: every site the textual census finds is a row the derivation found (so a module the derivation
        # stops reading, or a form it stops reading, fails here), the population is at least that, and the modules with rows
        # are the modules with sites, both ways (round 7, 2026-09-20: 5 modules had rows and no site, a drop there invisible)
        self.assertTrue(sites, "the textual census found no assertion over a served text")
        self.assertEqual(sorted(set(sites) - set(rows)), [], "sites the textual census reads and the derivation does not")
        self.assertGreaterEqual(len(rows), len(sites), "the population is every assertion of a literal over a served text across the suite: %d rows, %d sites" % (len(rows), len(sites)))
        self.assertEqual(sorted({r[0] for r in rows} ^ {s[0] for s in sites}), [], "modules with rows and no textual site, or the reverse")
        self.assertTrue({r[3] for r in rows} & set(getters) and {r[3] for r in rows} & set(constants), "rows over pages and over constants both derived")
        self.assertTrue({r[3] for r in rows} - set(getters) - roster, "rows over constants outside the round-6 roster (the class the roster missed): %r" % (sorted({r[3] for r in rows} - set(getters)),))
        # the container NAMES the tests pin, read from the test text on their own: every getter the tests call is derived, and
        # every `_CAPS` str the tests assert over that is served (by suffix or by landing in a page) is derived; both sides
        # non-empty, and the pinned names reach past the roster
        pinned_getters = {n for n, call in pinned if call and _GETTER_NAME.fullmatch(n)}
        pinned_caps = {n for n, call in pinned if not call and _CAPS.fullmatch(n)}
        self.assertTrue(pinned_getters and pinned_caps, "the tests pin getters and constants: %r" % (sorted(pinned),))
        self.assertEqual(sorted(pinned_getters - set(getters)), [], "page getters the tests pin that the derivation does not read")
        pinned_served = {n for n in pinned_caps if isinstance(getattr(km, n, None), str) and (_suffix_kind(n) or landing_kinds(getattr(km, n)))}
        self.assertTrue(pinned_served - roster, "the tests pin a served constant outside the round-6 roster: %r" % (sorted(pinned_served),))
        self.assertEqual(sorted(pinned_served - set(constants)), [], "served constants the tests pin that the derivation does not read")
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
        # getter (getattr) stays outside (the bound). Round 7 (2026-09-20): a `for` over served texts (one row per text, a
        # membership and a position form), a comprehension over literals, a position form over a loop literal, and the
        # constants of every kind the rule derives (a style constant, an HTML constant, a bare script constant and a markup
        # constant outside the round-6 roster), each name derived here, not written; the module is built over EVERY derived
        # getter, so a new getter is pinned by construction, and every expectation fails on an empty derivation
        getters, constants = page_getters(), served_constants()
        css = sorted(c for c in constants if c.endswith("_CSS"))[0]   # one constant of each kind, derived
        html = sorted(c for c in constants if c.endswith("_HTML"))[0]
        script = max((c for c in constants if not _suffix_kind(c) and constants[c] == {"script"}), key=lambda c: len(getattr(km, c)))
        mark = max((c for c in constants if not _suffix_kind(c) and constants[c] == {"markup"}), key=lambda c: len(getattr(km, c)))
        self.assertTrue(css and html and script and mark and len(getters) >= 2, (css, html, script, mark, getters))
        head = '''
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
'''
        loop = "        for pg in (%s):\n" % ", ".join("km.%s()" % g for g in getters)
        tail = '''            self.assertIn("a1", pg, "one row per text")
            self.assertLess(pg.index("a2"), 9)
        self.assertIn("a3", pg)
        for w in ("a4", "a5"):
            self.assertLess(page.index(w), 9)
        order = [page.index(w) for w in ("a6", "a7")]
        self.assertIn("a8", km.%(css)s)
        self.assertIn("a9", km.%(html)s)
        boot = km.%(script)s
        self.assertIn("b1", boot)
        self.assertIn("b2", km.%(mark)s)
        self.assertIn("b4"
                      "b5", page)
        for pg in (km._landing(), other()):
            self.assertIn("b3", pg)

def test_module_level():
    html = km._landing()
    assert "x1" in html and "x2" in html
    self.assertIn("x3", km._landing())
''' % {"css": css, "html": html, "script": script, "mark": mark}
        src = head + loop + tail
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write(src)
        try:
            rows = rows_of(f.name, getters, constants)
            sites, containers = textual_census(f.name, getters, constants)
        finally:
            os.unlink(f.name)
        L = head.count("\n") + 1   # the loop line's number: head ends with a newline, so its line count is the loop's line less one
        expected = [(6, "x", "_chat_page", "in"), (8, "y", "_feed_page", "in"), (10, "z", "_timeline_page", "in"), (12, "v", "_landing", "in"),
                    (15, "p", "_feed_page", "in"), (15, "q", "_feed_page", "in"), (17, "r", "_feed_page", "in"), (18, "s", "_landing", "in"), (19, "t", "_feed_page", "in"),
                    (23, "m", "_LANDING_MOBILE_JS", "in"), (25, "l", "_LANDING_MOBILE_JS", "in"), (26, "k", "_feed_page", "in"), (26, "j", "_LANDING_MOBILE_JS", "in"),
                    (28, "h", "_feed_page", "in"), (29, "g", "_feed_page", "index"), (29, "f", "_feed_page", "index"), (30, "e", "_LANDING_MOBILE_JS", "count"),
                    (31, "d", "_feed_page", "find"), (31, "c", "_feed_page", "rindex"), (31, "b", "_feed_page", "rfind")]
        expected += [(L + 1, "a1", g, "in") for g in getters] + [(L + 2, "a2", g, "index") for g in getters]
        expected += [(L + 5, "a4", "_feed_page", "index"), (L + 5, "a5", "_feed_page", "index"), (L + 6, "a6", "_feed_page", "index"), (L + 6, "a7", "_feed_page", "index"),
                     (L + 7, "a8", css, "in"), (L + 8, "a9", html, "in"), (L + 10, "b1", script, "in"), (L + 11, "b2", mark, "in"), (L + 12, "b4b5", "_feed_page", "in"),
                     (L + 19, "x1", "_landing", "in"), (L + 19, "x2", "_landing", "in"), (L + 20, "x3", "_landing", "in")]
        self.assertEqual(rows, expected)
        self.assertNotIn(("a3", "in"), {(lit, form) for _, lit, _, form in rows}, "the loop variable is bound to the loop's body only")
        self.assertNotIn(("b3", "in"), {(lit, form) for _, lit, _, form in rows}, "a loop whose iterable mixes a text with something else binds nothing")
        # the textual census reads the inline forms, the one-line bound form (a Name, a self.<attr>), the tuple binding (by
        # position, an item that is no served text binding nothing), the bare assert and assertTrue lines, the position forms,
        # the for over texts and an implicit concatenation of literals across the lines of one statement; the loop over
        # literals, the comprehension and the slice are the derivation's alone. Each site is a row
        expected_sites = [(6, "x", "_chat_page", "in"), (8, "y", "_feed_page", "in"), (10, "z", "_timeline_page", "in"), (12, "v", "_landing", "in"),
                          (18, "s", "_landing", "in"), (19, "t", "_feed_page", "in"), (23, "m", "_LANDING_MOBILE_JS", "in"), (25, "l", "_LANDING_MOBILE_JS", "in"),
                          (26, "k", "_feed_page", "in"), (26, "j", "_LANDING_MOBILE_JS", "in"), (29, "g", "_feed_page", "index"), (29, "f", "_feed_page", "index"),
                          (30, "e", "_LANDING_MOBILE_JS", "count"), (31, "d", "_feed_page", "find"), (31, "c", "_feed_page", "rindex"), (31, "b", "_feed_page", "rfind")]
        expected_sites += [(L + 1, "a1", g, "in") for g in getters] + [(L + 2, "a2", g, "index") for g in getters]
        expected_sites += [(L + 7, "a8", css, "in"), (L + 8, "a9", html, "in"), (L + 10, "b1", script, "in"), (L + 11, "b2", mark, "in"), (L + 12, "b4b5", "_feed_page", "in"),
                           (L + 19, "x1", "_landing", "in"), (L + 19, "x2", "_landing", "in"), (L + 20, "x3", "_landing", "in")]
        self.assertEqual(sites, expected_sites)
        self.assertTrue(set(sites) <= set(rows))
        # the containers the module pins, whatever the name: the getters, the constants, and `other` and `dyn` are not containers
        self.assertEqual(containers, {(g, True) for g in getters} | {("_LANDING_MOBILE_JS", False), (css, False), (html, False), (script, False), (mark, False)})


if __name__ == "__main__":
    unittest.main()
