#!/usr/bin/env python3
"""A pin over a served page or a served script or style constant reads the ELEMENT, the PARSED RULE or the CODE it pins, never
text a comment can satisfy.

D1, the maintainer's round 1 (2026-09-19): two served comments spelled the viewport meta's own tokens, and three assertions that named the
meta were satisfied by comment text; one test passed in full against a page whose meta had lost the token it exists to
pin. The three were re-pointed at the meta element. The maintainer's round 2 asked for the CLASS to be closed, not the instances: every
assertIn of a string literal over a served page's text whose literal also occurs inside a comment of that page is a pin a
comment can satisfy, and this module derives them and fails on each (the author's pass 4, 2026-09-20; the first instance beyond the
three was the timeline's touch-action pin, satisfied by two script comments that spell the declaration). The author's pass 6
(2026-09-20): the class had been closed over the page getters only, and the kernel's served CONSTANTS (the `_*_JS` and
`_*_CSS` strings spliced into the pages) carried eight pins a served comment satisfied, one of them created by the change
that landed the census (a new comment spelled offsetHeight inside _LANDING_MOBILE_JS); module-level test functions, a
conjunction of memberships, a name bound to a slice of a page, and the ordering pins `page.index(<lit>)` were outside it
too, with live members in each. The author's pass 7 (2026-09-20): the constants had been a NAME ROSTER (`_*_JS`, `_*_CSS`), which
missed a bare script constant with eight comment spans and four live pins (the timeline's boot script), every `_*_HTML`
constant and the served SVG and theme-reader fragments; the constants are derived by rule now, and a `for` variable over
a tuple of served texts, which had bound nothing, is read.

Population, derived by an AST walk over tests/test_*.py, every method of every class and every module-level function:
`self.assertIn(<lit>, X)`, `self.assertTrue(<lit> in X)` and a bare `assert <lit> in X` (a conjunction of memberships
inside assertTrue or assert is one row per conjunct), and the position forms `X.index(<lit>)`, `X.find(<lit>)`,
`X.rindex(<lit>)`, `X.rfind(<lit>)` and `X.count(<lit>)`, where <lit> is a string literal or the variable of a
`for <name> in (<str>, ...)` loop or comprehension in the same function (one row per literal; the author's pass 5, 2026-09-20: a loop
variable had been outside the derivation, and the one such pin in the suite was satisfiable by two comments), and X is one
of the kernel's served TEXTS: a call to one of its page getters, or one of its served constants (`<alias>.<_NAME>`), or a
Name bound to either in the same function (a tuple assignment counts by position; a Name bound to a SLICE of one counts
too, judged over the whole text, so a literal a comment spells anywhere in the text flags it and the fix is the same), or
the variable of a `for <name> in (<text>, <text>)` loop over served texts (one row per text, inside the loop's body;
the author's pass 7), or a `self.<attr>` bound to one in any method of the same class (a setUp), or a body FETCHED by a literal path
(the author's pass 8, 2026-09-20: `_, body = _serve_get("/sw.js", ...)`, `page = self._get_text("/")`, through `.read(...)` and
`.decode(...)`, alone or by tuple unpack; the fixer pass of the author's pass 8: a FORMATTED url too, `with urllib.request.urlopen(
"http://127.0.0.1:%d/timeline?token=testtok" % self.port) as r:` binding `r` and `body = r.read().decode(...)` after it, the
route the url's path, and only where the query carries `token=`, since a token-less fetch of a page route is answered by the
handler's gate with the paste-the-token page, a text the route walk does not map), which is the text of the getter the
kernel's GET dispatch serves at that path (route_getters below). The getters are derived from the
kernel source by rule: the functions named `_landing`, `_<name>_page`, `_<name>_js` or `_<name>_css` that a call with no
arguments renders (no parameter, or every parameter defaulted; the author's pass 7: the served script functions, the service worker,
the reload and shim cores and the timeline axis, had been outside the getter rule with ten live pins), a page read for
every kind of comment and a script or style getter by the scanner of its kind; the constants from the LOADED kernel by rule,
not from a roster of names (the author's pass 7): every module-level str attribute named `_[A-Z][A-Z0-9_]*` whose text a rendered page
carries, or whose name ends `_JS`, `_CSS` or `_HTML` (a text served at a route of its own, or spliced under a condition the
hermetic render does not meet), each with the KINDS of element its text lands in (inside a script element's content, inside
a style element's, or markup; by suffix where the page does not carry it), read through any module alias. The author's pass 6
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
reading fails here), the row count is at least the site count, and the modules with rows in a form the textual census reads
are exactly the modules with sites (a module the derivation reads in such a form and the textual census does not, or the
reverse, fails here). Each row carries whether its form is one the textual census reads (the author's pass 8, 2026-09-20): the literal's
SOURCE segment must be a plain literal or a run of them (a literal with a backslash, a triple-quoted one, a loop or
comprehension variable are not), and its container must not be a name bound to a slice; a module all of whose rows are in
declined forms is outside the module symmetry (its rows are still judged, and the form-space pin below holds the declined
forms), so a sound module reds nothing there while a module with one readable row and no site still does. The form space is
pinned on a synthetic module below (a form the derivation stops reading fails there), built over every derived getter and
over a derived constant of each kind. The container NAMES the tests pin are derived from the test text on their own and
held to the kernel-derived getters and constants (a getter the tests call or a served str the tests assert over that the
derivation does not read fails there; the author's pass 7).

The fetched route (the author's pass 8, 2026-09-20): a fetched body is read as the text of the route it fetched. The (route, getter)
pairs are derived from the kernel's GET dispatch by an AST walk (route_getters), never restated: an `if` comparing one Name
against a string literal by EQUALITY (`if p == "/chat": return self._send(200, _chat_page(), ...)`) or by MEMBERSHIP in a
tuple of literals (`if p in ("/", ""):`, the landing's form) whose body returns a call carrying a call to a derived getter
with no arguments. The walk is shape-sensitive: it reads those two shapes and no other, so a third shape (a table of routes,
a `match`, a comparison through a helper) is outside it until a branch is added and pinned in the form-space test below (a
naive equality walk misses the landing and reports eight routes believing nine). A fetch is a call to a Name or a
self.<method> (a test helper over the handler or an HTTP client) whose first argument is a string literal beginning with `/`
that, without its ?query, is such a route, or a call to an attribute named `urlopen` whose first argument is a string literal,
bare or `%`-formatted, of the form `http://127.0.0.1:%d/<route>?...token=...` (the `with ... as r` target is what it binds;
the fixer pass of the author's pass 8: the tokened fetches in tests/test_kernel.py carried 39 pins over five pages outside the population, one
of them satisfiable by three comments of the timeline page); a method call on another object (`path.split("/")`) is not one.

Bound: a url built otherwise than as a bare or `%`-formatted literal (a `Request` object, an f-string, `.format`), a formatted
url whose query carries no `token=` (tests/test_kernel.py's token-less fetch of `/`, answered with the paste-the-token page), a
membership asserted through a helper (`_has(self, lit, body)` in tests/test_files_pane.py and tests/test_settings_page.py, whose
formatted fetches bind a name no form here reads), a fetch of a path the dispatch does not map to a getter
call (a JSON or text/plain API body, a `/dist/` bundle, a `/media/` file: outside the derivation, and not comment-satisfiable
only where the body carries no comment syntax), a page from a dynamically resolved getter (`getattr(km, "_%s_page" % name)()`,
tests/test_kernel_boot_splash.py, which reads served_css.code for the tokens a comment spells), a getter called WITH
arguments (`_shim_core_js("chat")` renders another text), a text served under a name with none of the suffixes the rules
read (the web app manifest; the `_reload_core` function), a name bound outside the function, a literal bound by assignment
rather than a loop, and assertNotIn (a comment can red it, never green it) are outside this derivation.

Where the two census tests run (2026-09-21, the author's pass after the maintainer's round 5): on ONE CI cell, the kernel's
interpreter, Python 3.12 (the interpreter the deployed kernel is pinned to, docs/install.md's ROMP_PYTHON), and every other
interpreter SKIPS them with the reason stated on the skip (_ONE_CELL_REASON) and substitutes nothing for them, the maintainer's
rule for a guard that does not run. The design rests on a derivation: the census is a source-text fact, reading the test files'
text and AST, the kernel's source and its rendered pages, none of which varies by interpreter, and its rows dumped as sorted JSON
were byte-identical under 3.10, 3.12, 3.13 and 3.14 (the review record). The one AST input that does vary is a node's position
inside an f-string's braces (PEP 701: a format spec's nested f-string spans the whole literal on 3.10 and its own text since
3.12), which feeds a reader row's `source` column alone, so the premise the design stands on is that no reader row's node lies
inside an f-string, and test_no_reader_row_lies_inside_an_f_string pins it by execution on EVERY interpreter (it carries no
skip): the day a row moves into an f-string the one-cell design is re-opened by a red there, not found by drift between cells.
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
# the author's pass 6 roster of served constants, kept as the floor the rule-derived set may not shrink below (the author's pass 7, 2026-09-20)
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
# a fetch of a literal path (the author's pass 8, 2026-09-20): `<targets> = <helper>("/route"...` or `= self.<helper>("/route"...`, the path a
# route the dispatch maps (route_getters); and a body read from a fetched name, `<target> = <name>.decode(...)` or
# `<target> = <name>.read(...).decode(...)`
# a fetch of a FORMATTED url (the fixer pass of the author's pass 8): `with <x>.urlopen("http://127.0.0.1:%d/<route>?token=..." % <port>, ...) as r:`;
# the route is the path, and the query must carry the token (a token-less fetch of a page route is answered by the handler's gate
# with the paste-the-token page, a text the route walk does not map). One url grammar for both censuses; how a site is found
# stays their own (an AST walk against a regex by logical line)
_URL = re.compile(r"^https?://127\.0\.0\.1:%d(?P<route>/[^?\s\"']*)(?:\?(?P<query>[^\s\"']*))?$")
_URLOPEN_DEF = re.compile(r"^\s*with\s+(?:[A-Za-z_]\w*\.)*urlopen\(\s*(?P<url>" + _LIT1 + r")\s*%.*\)\s+as\s+(?P<target>[A-Za-z_]\w*)\s*:\s*(?:#.*)?$")
_FETCH_DEF = re.compile(r"^\s*(?P<targets>[A-Za-z_]\w*(?:\s*,\s*[A-Za-z_]\w*)*)\s*=\s*(?:self\.)?[A-Za-z_]\w*\(\s*(?P<route>\"/[^\"\\\n]*\"|'/[^'\\\n]*')")
_DECODE_DEF = re.compile(r"^\s*(?P<target>[A-Za-z_]\w*)\s*=\s*(?P<src>[A-Za-z_]\w*)(?:\.read\([^)]*\))?\.decode\([^)]*\)\s*(?:#.*)?$")
_ALIAS_DEF = re.compile(r"^\s*(?P<target>[A-Za-z_]\w*)\s*=\s*(?P<src>(?:self\.)?[A-Za-z_]\w*)\s*(?:#.*)?$")   # `js = html`, `js = self.html` (the fixer pass of the author's pass 9)
_DEF_LINE = re.compile(r"^(?P<indent>\s*)(?:async\s+)?def\s")
_CLASS_LINE = re.compile(r"^class\s")


def _url_route(url):
    """The route a formatted url names, or None: `http://127.0.0.1:%d/<route>?...` whose query carries `token=` (a token-less
    url is not a fetch of the page: the handler's gate answers it with the paste-the-token page)."""
    m = _URL.match(url)
    return m.group("route") if m and re.search(r"(?:^|&)token=", m.group("query") or "") else None


def _kernel_source():
    with open(os.path.join(BIN, "romp-kernel"), encoding="utf-8") as f:
        return f.read()


@functools.lru_cache(maxsize=8)
def _parse(src, path):
    """(tree, lines) for a module's text, parsed and split once per text: rows_of, readers_of and _imports_parser had each read and
    parsed the module they were handed on their own, four parses of every module of the population across the two census tests.
    Keyed on the TEXT, so a module rewritten under the same path (the form-space tests' temp files) is parsed afresh; small, so the
    population's trees are never all held at once (the derivations read one module at a time). `lines` is the text split as
    ast.get_source_segment splits it, on \\r\\n, \\n and \\r alone (ast._splitlines_no_ff), for _segment."""
    return ast.parse(src, path), re.findall(r"[^\r\n]*(?:\r\n|\r|\n)|[^\r\n]+\Z", src)


def _parsed(path):
    with open(path, encoding="utf-8") as f:
        src = f.read()
    return _parse(src, path)


def _segment(lines, node):
    """ast.get_source_segment(src, node) over `lines`, the module's text split once by _parse. The stdlib's splits the WHOLE text on
    every call, on 3.10 and 3.11 a char-by-char Python loop (3.12 bounds a regex at the node's last line); the derivations call it
    once per row and once per literal, and under 3.10 that loop was about a third of the two census tests' time (49 s of 156 s on one
    box, 2026-09-21)."""
    try:
        if node.end_lineno is None or node.end_col_offset is None:
            return None
        lineno, end_lineno, col_offset, end_col_offset = node.lineno - 1, node.end_lineno - 1, node.col_offset, node.end_col_offset
    except AttributeError:
        return None
    if end_lineno == lineno:
        return lines[lineno].encode()[col_offset:end_col_offset].decode()
    first = lines[lineno].encode()[col_offset:].decode()
    last = lines[end_lineno].encode()[:end_col_offset].decode()
    return "".join([first] + lines[lineno + 1:end_lineno] + [last])


def page_getters():
    """The kernel's served-text getters, derived from its source by rule: the functions named `_landing`, `_<name>_page`,
    `_<name>_js` or `_<name>_css` that a call with no arguments renders (no parameter, or every parameter defaulted)."""
    names = [n for n, params in _GETTER.findall(_kernel_source()) if not params.strip() or all("=" in p for p in params.split(","))]
    assert names, "no served-text getter derived from the kernel source"
    return sorted(set(names))


@functools.lru_cache(maxsize=None)
def route_getters(source=None):
    """{route: getter} for every path the kernel's GET dispatch serves from a served-text getter, by an AST walk over the kernel
    source (or over `source`, a handler text, for the form-space pin) reading TWO shapes and no other: an `if` whose test compares
    one Name against a string literal by equality (`if p == "/chat":`) or by membership in a tuple of string literals (`if p in
    ("/", ""):`, the landing's form), and whose body returns a call carrying a call to a derived getter with no arguments
    (`return self._send(200, _chat_page(), ...)`). Shape-sensitive by design (the author's pass 8, 2026-09-20): a third shape needs a third
    branch here and a case in the form-space test; an equality-only walk misses the landing."""
    tree = ast.parse(_kernel_source() if source is None else source)
    getters = set(page_getters())
    routes = {}
    for node in ast.walk(tree):
        if not (isinstance(node, ast.If) and isinstance(node.test, ast.Compare) and len(node.test.ops) == 1 and isinstance(node.test.left, ast.Name)):
            continue
        op, right = node.test.ops[0], node.test.comparators[0]
        if isinstance(op, ast.Eq) and isinstance(right, ast.Constant) and isinstance(right.value, str):
            paths = [right.value]
        elif isinstance(op, ast.In) and isinstance(right, ast.Tuple) and right.elts and all(isinstance(e, ast.Constant) and isinstance(e.value, str) for e in right.elts):
            paths = [e.value for e in right.elts]
        else:
            continue
        served = [a.func.id for st in node.body for n in ast.walk(st) if isinstance(n, ast.Return) and isinstance(n.value, ast.Call)
                  for a in n.value.args if isinstance(a, ast.Call) and not a.args and not a.keywords and isinstance(a.func, ast.Name) and a.func.id in getters]
        for path in paths if served else ():
            routes[path] = served[0]
    return routes


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
        # a text served as a script or a style sheet is that kind throughout: the element layer reads MARKUP (the author's pass 9, 2026-09-20:
        # it had been run over the script getters' JS too, where `<t.length` reads as a tag opening; the layer refuses a name
        # outside ASCII now and the JS carried one)
        spans = _element_spans(g) if getter_kind(g) == "markup" else [(0, len(page), getter_kind(g))]
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
    """{name: frozenset of kinds} for the kernel's served constants, derived by RULE from the loaded kernel (the author's pass 7,
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


def _fetched(node, names, routes):
    """The served text a fetched value stands for (the author's pass 8, 2026-09-20): a call to a Name or a self.<method> whose first argument
    is a string literal beginning with `/` that, without its ?query, is a route in `routes` (`_serve_get("/sw.js", ...)`,
    `self._get_text("/")`); a call to an attribute named `urlopen` whose first argument is a string literal, bare or `%`-formatted,
    naming such a route with the token in its query (_url_route; the fixer pass of the author's pass 8); or the `.read(...)` or `.decode(...)`
    of such a value or of a Name bound to one, through any chain of the two (`body.decode()`, `fetch("/chat").read().decode()`);
    else None. A bare Name is not followed (as _text does not)."""
    if not isinstance(node, ast.Call):
        return None
    f = node.func
    if isinstance(f, ast.Attribute) and f.attr in ("read", "decode"):
        inner = f.value
        return names.get(inner.id) if isinstance(inner, ast.Name) else _fetched(inner, names, routes)
    if isinstance(f, ast.Attribute) and f.attr == "urlopen" and node.args:
        a = node.args[0]
        fmt = a.left if isinstance(a, ast.BinOp) and isinstance(a.op, ast.Mod) else a
        route = _url_route(fmt.value) if isinstance(fmt, ast.Constant) and isinstance(fmt.value, str) else None
        return routes.get(route) if route else None
    if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str) and node.args[0].value.startswith("/") \
            and (isinstance(f, ast.Name) or (isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id == "self")):
        return routes.get(node.args[0].value.split("?")[0])
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


def _bind(targets, value, names, attrs, getters, constants, sliced=None, routes=None):
    """Record Name and self.<attr> targets bound to a served text, or to a slice of one; a tuple assignment binds by position; a
    FETCHED value (_fetched, with `routes`) binds every Name it is unpacked into (`_, body = _serve_get("/sw.js")`: the status
    too, a name no membership reads). `sliced`, when given, tracks the Names bound through a slice (a form the textual census
    does not read; the author's pass 8)."""
    if isinstance(value, ast.Tuple) and len(targets) == 1 and isinstance(targets[0], ast.Tuple) \
            and len(targets[0].elts) == len(value.elts):
        pairs = list(zip(targets[0].elts, value.elts))
    else:
        pairs = [(t, value) for t in targets]
    for t, v in pairs:
        g = _text(v, getters, constants)
        via_slice = fetched = False
        if not g and isinstance(v, ast.Subscript):   # `fn = html[a:b]`, a slice of a bound text, judged over the whole text
            g = _resolve(v.value, names, attrs, getters, constants)
            via_slice = True
        if not g and (isinstance(v, ast.Name) or isinstance(v, ast.Attribute) and isinstance(v.value, ast.Name) and v.value.id == "self"):
            # `js = html` or `js = self.html`, an ALIAS of a bound name (the fixer pass of the author's pass 9: two suite modules alias the page so
            # and neither census had followed it, so their position pins and a regex over the alias were outside both populations)
            g = _resolve(v, names, attrs, getters, constants)
            via_slice = isinstance(v, ast.Name) and sliced is not None and v.id in sliced
        if not g and routes:
            g = _fetched(v, names, routes)
            fetched = bool(g)
        if not g:
            continue
        if isinstance(t, ast.Name):
            names[t.id] = g
            if sliced is not None:
                (sliced.add if via_slice else sliced.discard)(t.id)
        elif isinstance(t, ast.Tuple) and fetched:   # `status, body = fetch("/x")`: every name the fetch binds
            for e in t.elts:
                if isinstance(e, ast.Name):
                    names[e.id] = g
                    if sliced is not None:
                        sliced.discard(e.id)
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


def rows_of(path, getters, constants, routes=None):
    """[(line, literal, text, form, readable)] for every membership or position assertion of a literal over a served text in one
    test module; form is "in" for a membership, else the position method; readable is whether the row's form is one the textual
    census reads (the author's pass 8, 2026-09-20): the literal's source segment is a plain literal or a run of them (re.fullmatch over _LIT:
    no backslash, not triple-quoted, not a loop or comprehension variable) and the container is not a name bound to a slice."""
    tree, lines = _parsed(path)
    plain = lambda node: isinstance(node, ast.Constant) and bool(re.fullmatch(_LIT, _segment(lines, node) or ""))
    out = []
    functions = (ast.FunctionDef, ast.AsyncFunctionDef)
    groups = [[n for n in cls.body if isinstance(n, functions)] for cls in ast.walk(tree) if isinstance(cls, ast.ClassDef)]
    groups.append([n for n in tree.body if isinstance(n, functions)])   # module-level test functions (the author's pass 6, 2026-09-20)
    modnames = _module_bindings(tree, getters, constants, routes)   # a served text bound at module level is read in every function (the fixer pass of the author's pass 9)
    binds = {}
    def bindings(fn):   # in walk order, so a with-item's `as` target is bound before the assignments in its body read it; read once per function
        if fn not in binds:
            binds[fn] = []
            for st in ast.walk(fn):
                if isinstance(st, ast.Assign):
                    binds[fn].append((st.targets, st.value))
                elif isinstance(st, ast.With):
                    for item in st.items:
                        if item.optional_vars is not None:
                            binds[fn].append(([item.optional_vars], item.context_expr))
        return binds[fn]
    for fns in groups:
        attrs = {}
        for fn in fns:   # a setUp's self.<attr> binding is visible to every method
            for targets, value in bindings(fn):
                _bind(targets, value, {}, attrs, getters, constants, None, routes)
        for fn in fns:
            names, sliced = dict(modnames), set()
            for targets, value in bindings(fn):   # an assignment, or a with-item's `as` target (`with urlopen(...) as r`; the fixer pass of the author's pass 8)
                _bind(targets, value, names, attrs, getters, constants, sliced, routes)
            text_of = lambda x: _resolve(x, names, attrs, getters, constants)
            readable = lambda lit, x: plain(lit) and not (isinstance(x, ast.Name) and x.id in sliced)
            rows = []
            for node in ast.walk(fn):
                for lit, x in _memberships(node):
                    if _literals(lit) and text_of(x):
                        rows += [(node.lineno, lit.col_offset, i, l, text_of(x), "in", readable(lit, x)) for i, l in enumerate(_literals(lit))]
                pos = _position(node)
                if pos and _literals(pos[0]) and text_of(pos[1]):
                    rows += [(node.lineno, pos[0].col_offset, i, l, text_of(pos[1]), pos[2], readable(pos[0], pos[1])) for i, l in enumerate(_literals(pos[0]))]
            # a loop variable, bound to the loop's own body (a variable rebound by a later loop resolves to its own loop):
            # `for win in ("fiveHour", "sevenDay"):` binds the LITERALS, one row per literal for each membership or position
            # form of the variable over a text (the author's pass 5, 2026-09-20); `for page in (km._feed_page(), km._files_page()):` binds
            # the TEXTS, one row per text for each membership or position form of a literal over the variable (the author's pass 7,
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
                        if lits and isinstance(lit, ast.Name) and lit.id == var and text_of(x):   # a loop or comprehension literal: declined by the textual census
                            rows += [(node.lineno, lit.col_offset, i, l, text_of(x), form, False) for i, l in enumerate(lits)]
                        elif texts and all(texts) and _literals(lit) and isinstance(x, ast.Name) and x.id == var:   # a for over texts: read by it
                            rows += [(node.lineno, lit.col_offset, i * len(texts) + j, l, g, form, plain(lit)) for i, l in enumerate(_literals(lit)) for j, g in enumerate(texts)]
            out += [(line, lit, g, form, readable) for line, _, _, lit, g, form, readable in sorted(rows)]
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


def textual_census(path, getters, constants, routes=None):
    """(sites, containers): sites is [(line, literal, text, form)] for every membership or position form of a literal over a
    served text this regex census reads in one test module, by logical line and no AST, the second, independent census the
    derived floor rests on: `assertIn("<lit>", X)`, an `assert "<lit>" in X` or `assertTrue("<lit>" in X)` line (every
    conjunct on it), and `X.index("<lit>")` with find, rindex, rfind and count, where X is `<alias>.<getter>()` or
    `<alias>.<CONST>` inline, a Name bound to one by an assignment of its own earlier in the same function (a `self.<attr>`
    so bound in any method of the class), by a tuple assignment, by a `for` over served texts inside that loop (one site per
    text), or by a fetch of a literal path the dispatch maps (`_FETCH_DEF`, every target; `_DECODE_DEF` for the body read from
    one; the author's pass 8) or of a formatted url with the token in its query (`_URLOPEN_DEF`, the `as` target; the fixer pass of the author's pass
    8). A binding a later line rebinds keeps the served text, as the derivation reads it. containers is the set of
    (name, called) for every `<alias>.<name>` the module uses as a container in one of those forms, whatever the name, the
    NAMES the tests pin, read on their own for the check against the kernel-derived getters and constants (the author's pass 7)."""
    sites, containers, names, attrs, loops, modnames = [], set(), {}, {}, [], {}
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
            # a binding at column 0 is the module's, read in every function (the fixer pass of the author's pass 9)
            (attrs if m.group("target").startswith("self.") else modnames if indent == 0 else names)[m.group("target")] = [(m.group("name"), bool(m.group("call")))]
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
        m = _FETCH_DEF.match(line)
        if m and routes:
            getter = routes.get(_literal(m.group("route")).split("?")[0])
            if getter:
                for t in m.group("targets").split(","):
                    names[t.strip()] = [(getter, True)]
        m = _URLOPEN_DEF.match(line)
        if m and routes:
            route = _url_route(_literal(m.group("url")))
            if route and routes.get(route):
                names[m.group("target")] = [(routes[route], True)]
        m = _DECODE_DEF.match(line)
        if m and m.group("src") in names:
            names[m.group("target")] = names[m.group("src")]
        m = _ALIAS_DEF.match(line)
        if m:   # an alias of a bound name: the module's, the function's, or a self.<attr> (the fixer pass of the author's pass 9)
            src = m.group("src")
            items = attrs.get(src) if src.startswith("self.") else names.get(src, modnames.get(src))
            if items:
                names[m.group("target")] = items
        bound = dict(modnames)
        bound.update(names)
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


_STR_READS = {"index", "find", "rindex", "rfind", "count", "split", "rsplit", "splitlines", "strip", "lstrip", "rstrip", "lower", "upper", "casefold",
              "startswith", "endswith", "partition", "rpartition", "replace", "removeprefix", "removesuffix", "translate", "expandtabs",
              "format", "join", "zfill", "center", "ljust", "rjust", "title", "capitalize", "swapcase", "isascii", "isspace", "isalpha", "isdigit", "isalnum"}
_CONVERSIONS = {"encode", "decode", "read"}
_RE_FUNCS = {"search", "match", "fullmatch", "findall", "finditer", "split", "sub", "subn"}
_ASSERTS = {"assertIn", "assertNotIn", "assertEqual", "assertNotEqual", "assertTrue", "assertFalse", "assertIs", "assertIsNot", "assertIsNone", "assertIsNotNone",
            "assertMultiLineEqual", "assertRegex", "assertNotRegex", "assertCountEqual", "assertLess", "assertGreater", "assertLessEqual", "assertGreaterEqual"}
# the forms a read of a served text can take (readers_of); the census test states which are the parser road or a stated read and reds on the rest
# (`splice`, the close of the author's pass 9: the text copied into another string by concatenation, %-format or an f-string, not read there)
READER_FORMS = ("parser", "assert", "position", "view-pin", "position-unpinned", "membership-unpinned", "regex", "slice", "span-slice", "method", "conversion",
                "value-use", "splice", "compare", "unclassified")
# served_css functions returning a TEXT derived from the one they are given, its comments blanked with offsets kept: a VIEW of the text,
# the author's pass 6 re-point form (a literal membership or position pin over one is not comment-satisfiable by construction: `view-pin`)
_VIEWS = {"code", "markup", "js_code", "css_code"}
# str methods whose result is the text transformed or cut into pieces: a COPY of the text, which the pins census does not bind, so a
# literal membership or position pin over one is unjudged (`membership-unpinned`, `position-unpinned`)
_COPIES = {"lower", "upper", "casefold", "strip", "lstrip", "rstrip", "replace", "translate", "expandtabs", "removeprefix", "removesuffix", "swapcase",
           "title", "capitalize", "zfill", "center", "ljust", "rjust", "split", "rsplit", "splitlines", "partition", "rpartition", "format"}
# callables that take a served text WHOLE and read nothing of it, the stated allowlist behind `value-use`; any other callee handed the
# text is `unclassified` and reds the census (a parser of its own, an imported helper, a compiled pattern from another module)
_VALUE_USES = {"dumps", "len", "print", "isinstance", "write", "repr", "str", "type", "bool",
               # a child process's argument vector, by qualified name (the close of the author's pass 9: a script constant's slice handed to
               # node inside the list, `subprocess.run([node, "-e", harness, post, ...])`, is executed there, not read here)
               "subprocess.run", "subprocess.check_output", "subprocess.Popen"}


def _module_bindings(tree, getters, constants, routes):
    """{Name: served text} for the module-level assignments that bind a served text (`JS = km._LANDING_APIH_JS`; the fixer pass of
    the author's pass 9: three suite modules bind one at import time and read it in every test, and neither census had seen the binding)."""
    names = {}
    for st in tree.body:
        if isinstance(st, ast.Assign):
            _bind(st.targets, st.value, names, {}, getters, constants, None, routes)
    return names


def _imports_parser(path):
    """Whether a test module IMPORTS served_css (`import served_css` or `from served_css import ...`, anywhere in it): the parser
    road's membership test (the fixer pass of the author's pass 9: the census had tested text containment, the string anywhere in the file, a
    comment included, while every surface stated the import; the two agree at this head, 15 modules)."""
    tree = _parsed(path)[0]
    return any(isinstance(n, ast.Import) and any(a.name == "served_css" for a in n.names) or isinstance(n, ast.ImportFrom) and n.module == "served_css"
               for n in ast.walk(tree))


def readers_of(path, getters, constants, routes=None):
    """[(line, form, text, source)] for every READ of a served text in one test module: the population the maintainer's round 5
    ruling asked to be derived once, of every road (the author's pass 9, 2026-09-20), after the one HTML regex this change had added beside
    the parser it introduced. A served text is what rows_of resolves (a getter call, a constant, a Name or self.<attr> bound to
    one or to a fetched body, the variable of a `for` over texts, a Name bound at module level), and since the fixer pass of the author's pass 9
    also a VIEW of one (`served_css.code(X)`, markup, js_code, css_code: the text with its comments blanked, inline or bound to a
    Name) and a COPY of one (a str method of _COPIES on it, a slice of it, a line of its splitlines, the variable of a `for` over it
    or over its pieces, inline or bound), each read over a view or a copy being a row over the text it derives from. A read is X in
    any of these forms, each named in READER_FORMS: `served_css.<fn>(X, ...)` or a name imported from served_css called on X
    (`parser`, the one road for an element, an attribute or a rule); `X.<index|find|rindex|rfind|count>(needle)` with a literal or
    loop-literal needle over the text itself (`position`: a pins-census row, judged there), over a view (`view-pin`: an order or
    count over comment-blanked text, the author's pass 6 re-point form) or over a copy (`position-unpinned`: a read the pins census does
    not see), and with any other needle (`position-unpinned`); a literal membership `<lit> in X` under assertIn, assertNotIn,
    assertTrue or a bare assert over the text (`assert`: the pins census's row), over a view (`view-pin`) or over a copy
    (`membership-unpinned`), and `<needle> in X` with a non-literal needle (`membership-unpinned`); `re.<fn>(..., X)` or
    `<pattern>.<fn>(X)` with the pattern a Name bound by re.compile in the module (`regex`); `X[a:b]` with both bounds Names a
    `for` over a `served_css.<fn>(...)` iterable binds (`span-slice`: offsets the parser derived) and any other subscript of X
    (`slice`); any other str method on X (`method`, the method's name in the source column); X.encode/decode/read (`conversion`:
    bytes to text and back, no content read); X handed whole to any other `self.assert*` (`assert`: a whole-text compare); X handed
    whole to a callable of the stated allowlist _VALUE_USES (json.dumps, len, print, isinstance, a file's write, repr, str, type,
    bool, and by qualified name a child process's argument vector, subprocess.run, check_output and Popen) or as the ARGUMENT of
    another string's str method (`other.replace("__X__", X)`: spliced or compared, not read) (`value-use`: the text is not read at that
    site); X as the operand of a comparison other than a membership (`compare`); X handed whole to any other callable (`unclassified`: a
    compiled pattern imported from another module, an inline `re.compile(...).search`, an imported helper, a parser of its own, a
    lambda; red in the census). A module-level function of the same module called with X is FOLLOWED one level, its parameter bound
    to the text, so a membership or a read inside a helper (`_has(self, lit, body)`) is a row at the helper's own line.
    The close of the author's pass 9 made the walk read what the sentences above already claimed of "X": X is handed to a callable
    by KEYWORD as well as by position (`parse_it(text=page)`, `self.assertIn("x", container=page)`, `re.search("x", string=page)`; a
    followed helper binds a keyword to its parameter by name); a SPLICE of X into another string (`page + "x"`, `"%s" % page`,
    `f"{page}"`) is a row of its own (`splice`: the text copied, not read) and derives from X as a copy does, so a read over the
    result is `position-unpinned` or `membership-unpinned` and a callee handed it is classified as if handed X; a CONTAINER literal
    holding X (a list, tuple, set or dict, a starred element) derives from X the same way, so `json.dumps({"k": page})` is a
    value-use and `parse_it([page])` unclassified; `self.assertRegex(X, pattern)` and assertNotRegex are `regex`, a pattern run over
    the text, not a whole-text compare; and for assertIn and assertNotIn the row is over the CONTAINER (the second argument or
    `container=`), the text read, a served text in the member position being compared whole (`assertIn("x" + km._SVG, page)` is an
    `assert` over the page). Before the close each of these was no row at all, or the assertRegex an `assert`."""
    tree, lines = _parsed(path)
    seg = lambda node: (_segment(lines, node) or "").replace("\n", " ")[:160]
    nodes = list(ast.walk(tree))   # one walk of the module for the patterns and the classes below
    patterns = {t.id for node in nodes if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Attribute) and isinstance(node.value.func.value, ast.Name) and node.value.func.value.id == "re"
                and node.value.func.attr == "compile" for t in node.targets if isinstance(t, ast.Name)}
    parser_names = {alias.asname or alias.name for node in tree.body if isinstance(node, ast.ImportFrom) and node.module == "served_css" for alias in node.names}
    functions = (ast.FunctionDef, ast.AsyncFunctionDef)
    helpers = {n.name: n for n in tree.body if isinstance(n, functions) and not n.name.startswith("test")}
    groups = [[n for n in cls.body if isinstance(n, functions)] for cls in nodes if isinstance(cls, ast.ClassDef)]
    groups.append([n for n in tree.body if isinstance(n, functions)])

    binds = {}
    def bindings(fn):   # read once per function: the attrs pass and the walk both read it, and a followed helper once per caller
        if fn not in binds:
            binds[fn] = []
            for st in ast.walk(fn):
                if isinstance(st, ast.Assign):
                    binds[fn].append((st.targets, st.value))
                elif isinstance(st, ast.With):
                    for item in st.items:
                        if item.optional_vars is not None:
                            binds[fn].append(([item.optional_vars], item.context_expr))
        return binds[fn]

    def is_view(x):   # `served_css.<view>(X, ...)`, or the view imported by name
        f = x.func
        return bool(x.args) and (isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id == "served_css" and f.attr in _VIEWS
                                 or isinstance(f, ast.Name) and f.id in parser_names and f.id in _VIEWS)

    def text_of(x, names, attrs, derived):
        """The served text a node reads: the text itself, or the text a view or a copy of it derives from."""
        t = _resolve(x, names, attrs, getters, constants)
        if t:
            return t
        if isinstance(x, ast.Subscript):
            return text_of(x.value, names, attrs, derived)
        if isinstance(x, ast.Call):
            if is_view(x):
                return text_of(x.args[0], names, attrs, derived)
            f = x.func
            if isinstance(f, ast.Attribute) and f.attr in _COPIES:
                return text_of(f.value, names, attrs, derived)
        # the close of the author's pass 9: a SPLICE of the text into another string (a concatenation or a %-format, an f-string) and a
        # CONTAINER literal holding it (a list, tuple, set or dict, a starred element) derive from the text too: the walk had read
        # neither, so a read over `page + "x"`, over `f"{page}"` or through `[page]` handed to a call produced no row at all
        if isinstance(x, ast.BinOp):
            return text_of(x.left, names, attrs, derived) or text_of(x.right, names, attrs, derived)
        if isinstance(x, ast.JoinedStr):
            parts = [v.value for v in x.values if isinstance(v, ast.FormattedValue)]
        elif isinstance(x, (ast.List, ast.Tuple, ast.Set)):
            parts = x.elts
        elif isinstance(x, ast.Dict):
            parts = [v for v in x.values if v is not None]
        elif isinstance(x, ast.Starred):
            parts = [x.value]
        else:
            return None
        for part in parts:
            t = text_of(part, names, attrs, derived)
            if t:
                return t
        return None

    def basis_of(x, names, attrs, derived):
        """None for the text itself, "view" for a served_css view of it, "copy" for a str-method copy, a slice or a piece of it, a splice
        of it into another string or a container literal holding it."""
        if isinstance(x, ast.Name):
            return derived.get(x.id)
        if isinstance(x, (ast.Subscript, ast.BinOp, ast.JoinedStr, ast.List, ast.Tuple, ast.Set, ast.Dict, ast.Starred)):
            return "copy"
        if isinstance(x, ast.Call):
            if is_view(x):
                return "view"
            if isinstance(x.func, ast.Attribute) and x.func.attr in _COPIES:
                return "copy"
        return None

    def derive(targets, value, names, attrs, derived):
        """Bind a Name to the text a view, a copy, a slice or an alias derives from (after _bind has bound the plain forms)."""
        if len(targets) == 1 and isinstance(targets[0], ast.Name) and not _text(value, getters, constants):
            base = text_of(value, names, attrs, derived)
            if base and not (routes and _fetched(value, names, routes)):
                names[targets[0].id] = base
                basis = basis_of(value, names, attrs, derived)
                if basis:
                    derived[targets[0].id] = basis
                else:
                    derived.pop(targets[0].id, None)

    modnames, modderived = _module_bindings(tree, getters, constants, routes), {}
    for st in tree.body:
        if isinstance(st, ast.Assign):
            derive(st.targets, st.value, modnames, {}, modderived)

    def walk(fn, names, attrs, depth, derived, methods):
        for targets, value in bindings(fn):
            _bind(targets, value, names, attrs, getters, constants, None, routes)
            derive(targets, value, names, attrs, derived)
        loops = _loops(fn)   # read once: the loop bindings here and the loop literals below
        for var, it, _ in loops:   # a for over served texts binds its variable (to the first text: one form per variable)
            texts = [_text(e, getters, constants) for e in it.elts] if isinstance(it, (ast.Tuple, ast.List)) and it.elts else []
            if texts and all(texts):
                names[var] = texts[0]
            elif text_of(it, names, attrs, derived):   # a for over a text or over its pieces (`for line in page.splitlines()`): a copy
                names[var] = text_of(it, names, attrs, derived)
                derived[var] = "copy"
        span_names = set()
        for node in ast.walk(fn):   # the Names a `for a, b in served_css.<fn>(...)` binds: parser-derived offsets
            if isinstance(node, (ast.For, ast.comprehension)) and isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Attribute) \
                    and isinstance(node.iter.func.value, ast.Name) and node.iter.func.value.id == "served_css" and isinstance(node.target, ast.Tuple):
                span_names |= {e.id for e in node.target.elts if isinstance(e, ast.Name)}
        text = lambda x: text_of(x, names, attrs, derived)
        basis = lambda x: basis_of(x, names, attrs, derived)
        lits = {var for var, it, _ in loops if _literals(it)}
        literal = lambda a: bool(_literals(a)) or (isinstance(a, ast.Name) and a.id in lits)

        def pin(form, x):   # a literal membership or position pin, by what it reads: the text (the pins census's row), a view, a copy
            b = basis(x)
            return form if b is None else "view-pin" if b == "view" else "position-unpinned" if form == "position" else "membership-unpinned"
        rows = []
        for node in ast.walk(fn):
            if isinstance(node, ast.Call):
                f = node.func
                if isinstance(f, ast.Attribute) and text(f.value):   # X.<method>(...)
                    t = text(f.value)
                    if f.attr in _POSITION:
                        rows.append((node.lineno, pin("position", f.value) if node.args and literal(node.args[0]) else "position-unpinned", t, seg(node)))
                    elif f.attr in _CONVERSIONS:
                        rows.append((node.lineno, "conversion", t, seg(node)))
                    elif f.attr in _STR_READS:
                        rows.append((node.lineno, "method", t, f.attr + ": " + seg(node)))
                    else:
                        rows.append((node.lineno, "unclassified", t, seg(node)))
                    continue
                # the arguments that are a served text, positional by index and keyword by name (the close of the author's pass 9: the
                # walk had read positional arguments alone, so `parse_it(text=page)` and `self.assertIn("x", container=page)` were no row)
                served = [(i, a) for i, a in enumerate(node.args) if text(a)] + [(kw.arg, kw.value) for kw in node.keywords if text(kw.value)]
                if not served:
                    continue
                arg = served[0][1]
                t = text(arg)
                callee = f.attr if isinstance(f, ast.Attribute) else f.id if isinstance(f, ast.Name) else None
                if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id == "served_css" or isinstance(f, ast.Name) and f.id in parser_names:
                    rows.append((node.lineno, "parser", t, seg(node)))
                elif isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and (f.value.id == "re" and f.attr in _RE_FUNCS or f.value.id in patterns):
                    rows.append((node.lineno, "regex", t, seg(node)))
                elif isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id == "self" and f.attr in _ASSERTS:
                    if f.attr in ("assertRegex", "assertNotRegex"):
                        # a pattern run over the text: a regex read, not a whole-text compare (the close of the author's pass 9: it had read
                        # as `assert`, so a regex over raw markup on the parser road was not red)
                        form = "regex"
                    elif f.attr in ("assertIn", "assertNotIn"):
                        # what is READ is the container (the second argument, or `container=`); a served text in the member position is
                        # compared whole, spliced or not (the close of the author's pass 9: a splice in the member position had read as a
                        # pin over a copy, a raw read of the constant the page was searched for)
                        container = node.args[1] if len(node.args) > 1 else next((kw.value for kw in node.keywords if kw.arg == "container"), None)
                        if container is not None and text(container):
                            form, t = pin("assert", container), text(container)   # the row is over the text read, the container's
                        else:
                            form = "assert"
                    else:
                        form = "assert"
                    rows.append((node.lineno, form, t, seg(node)))
                elif depth == 0 and (isinstance(f, ast.Name) and f.id in helpers or isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name)
                                     and f.value.id == "self" and f.attr in methods and f.attr not in _ASSERTS):
                    # a helper of this module, or a method of the same class (`self._code(js)`; the fixer pass of the author's pass 9): followed once
                    h = helpers[f.id] if isinstance(f, ast.Name) else methods[f.attr]
                    params = [a.arg for a in h.args.args]
                    if isinstance(f, ast.Attribute) and params and params[0] == "self":
                        params = params[1:]
                    bound = {params[i]: text(a) for i, a in served if isinstance(i, int) and i < len(params)}
                    bound.update({k: text(a) for k, a in served if isinstance(k, str) and k in params})   # a keyword argument binds its parameter by name
                    rows.append((node.lineno, "value-use", t, "helper %s: " % callee + seg(node)))
                    rows += walk(h, dict(bound), dict(attrs), depth + 1, {}, methods)
                elif callee in _VALUE_USES or isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id + "." + f.attr in _VALUE_USES:
                    rows.append((node.lineno, "value-use", t, "%s: " % callee + seg(node)))
                elif isinstance(f, ast.Attribute) and f.attr in _STR_READS and not text(f.value):   # another string's method: the text is its argument
                    rows.append((node.lineno, "value-use", t, "%s: " % callee + seg(node)))
                else:
                    rows.append((node.lineno, "unclassified", t, "%s: " % callee + seg(node)))
            elif isinstance(node, (ast.BinOp, ast.JoinedStr)) and text(node):
                # the splice itself: the text copied into another string, not read (what reads the result is a read over a copy)
                rows.append((node.lineno, "splice", text(node), seg(node)))
            elif isinstance(node, ast.Subscript) and text(node.value):
                sl = node.slice
                spans = isinstance(sl, ast.Slice) and (sl.lower is not None or sl.upper is not None) \
                    and all(isinstance(bd, ast.Name) and bd.id in span_names for bd in (sl.lower, sl.upper) if bd is not None)
                rows.append((node.lineno, "span-slice" if spans else "slice", text(node.value), seg(node)))
            elif isinstance(node, ast.Compare):
                for i, (op, right) in enumerate(zip(node.ops, node.comparators)):
                    left = node.left if i == 0 else node.comparators[i - 1]
                    if isinstance(op, (ast.In, ast.NotIn)) and text(right):
                        rows.append((node.lineno, pin("assert", right) if literal(left) else "membership-unpinned", text(right), seg(node)))
                    elif text(left) or text(right):
                        rows.append((node.lineno, "compare", text(left) or text(right), seg(node)))
        return rows

    out = []
    for fns in groups:
        attrs, methods = {}, {n.name: n for n in fns}
        for fn in fns:
            for targets, value in bindings(fn):
                _bind(targets, value, {}, attrs, getters, constants, None, routes)
        for fn in fns:
            out += walk(fn, dict(modnames), attrs, 0, dict(modderived), methods)
    return sorted(set(out))


def inline_sites(path, getters, constants):
    """The textual census's sites alone (textual_census)."""
    return textual_census(path, getters, constants)[0]


def _spans(kinds, text):
    return sorted({sp for k in kinds for sp in _SCANNER[k](text)})


@functools.lru_cache(maxsize=None)
def population():
    """The population's paths, sorted: every tests/test_*.py but this module, the two censuses' own glob and exclusion."""
    return tuple(p for p in sorted(glob.glob(os.path.join(HERE, "test_*.py"))) if os.path.realpath(p) != os.path.realpath(__file__))


@functools.lru_cache(maxsize=None)
def _derived():
    """(getters, constants, routes), the kernel-derived inputs of every derivation over the population, once per process."""
    return page_getters(), served_constants(), route_getters()


@functools.lru_cache(maxsize=None)
def _readers(path):
    """readers_of over one population module, derived once per process and keyed on the path: the population's files do not change
    within a run, and the form-space tests call readers_of on their temp files directly, never through this cache. Read by
    population_census on the census cell and by the f-string premise pin on every interpreter, so a cell that skips the census
    parses each module and derives its reader rows and nothing else (the module docstring's last paragraph)."""
    return readers_of(path, *_derived())


@functools.lru_cache(maxsize=None)
def population_census():
    """The census over the population, derived ONCE per process and read by both census tests: {module basename: (rows_of rows,
    textual_census (sites, containers), _imports_parser, readers_of rows)} for every module of population(), in sorted order, each
    derivation over the kernel-derived getters, constants and routes. The population and the forms are the four derivations' own;
    what this shares is the work: the two tests had each walked the population on their own and the reader census had run rows_of
    a second time (CI's 3.10 cell, 2026-09-21: 144 s and 78 s, the job at 24 min 26 s against a 25-minute cap), and with _parse
    every module is read and parsed once (the reader rows through _readers inside this loop, so the parse is shared with them)."""
    getters, constants, routes = _derived()
    out = {}
    for path in population():
        out[os.path.basename(path)] = (rows_of(path, getters, constants, routes), textual_census(path, getters, constants, routes),
                                       _imports_parser(path), _readers(path))
    return out


# the one CI cell that runs the two census tests, the kernel's interpreter (the module docstring's last paragraph): every other
# interpreter skips them with _ONE_CELL_REASON on the skip, substitutes nothing, and runs the f-string premise pin
_CENSUS_CELL = (3, 12)
_ONE_CELL_REASON = ("the reader census is a source-text fact whose rows were derived byte-identical under Python 3.10, 3.12, 3.13 and 3.14 "
                    "(2026-09-21, the review record), the only interpreter-sensitive AST input, a node's position inside an f-string's braces, "
                    "reaching a reader row's source column alone, which no population row exercises (test_no_reader_row_lies_inside_an_f_string "
                    "pins that here and on every interpreter), so the census runs on the kernel's interpreter cell, 3.12, and is skipped on "
                    "this one, not replaced by anything")


class ServedPinsReadElements(unittest.TestCase):
    @unittest.skipUnless(sys.version_info[:2] == _CENSUS_CELL, _ONE_CELL_REASON)
    def test_no_assertion_over_a_served_text_is_satisfiable_by_a_comment(self):
        getters, constants, routes = page_getters(), served_constants(), route_getters()
        # the fetched-route map, derived from the handler by the walk: the landing's membership form and an equality form both read
        self.assertEqual((routes.get("/"), routes.get("")), ("_landing", "_landing"), "the landing's membership route: %r" % (routes,))
        self.assertTrue([r for r, g in routes.items() if r not in ("/", "")], "an equality route: %r" % (routes,))
        self.assertEqual(sorted(set(routes.values()) - set(getters)), [], "every route's getter is a derived getter")
        texts = dict(pages())
        texts.update({c: getattr(km, c) for c in constants})
        kinds = {g: frozenset([getter_kind(g)]) for g in getters}
        kinds.update(constants)
        comments = {name: _spans(kinds[name], texts[name]) for name in texts}
        pages_ = [g for g in getters if getter_kind(g) == "markup"]
        self.assertTrue(pages_ and [g for g in getters if getter_kind(g) == "script"], "page getters and script getters both derived: %r" % (getters,))
        self.assertTrue(all(comments[g] for g in pages_), "every served page carries comments (the derivation read them): %r" % ({g: len(comments[g]) for g in pages_},))
        # the constants are derived by rule from the loaded kernel; the author's pass 6 roster (the source's `_*_JS`/`_*_CSS` names) is
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
        self.assertEqual(rows_of(__file__, getters, constants, routes), [], "the census module itself pins nothing over a served text")
        for fname, (derived, (found, containers), _, _) in population_census().items():   # derived once per process, shared with the reader census
            rows += [(fname, line, lit, name, form, readable) for line, lit, name, form, readable in derived]
            sites += [(fname, line, lit, name, form) for line, lit, name, form in found]
            pinned |= containers
        # the floor, derived: every site the textual census finds is a row the derivation found (so a module the derivation
        # stops reading, or a form it stops reading, fails here), the population is at least that, and the modules with rows in
        # a form the textual census reads are the modules with sites, both ways (the author's pass 7, 2026-09-20: 5 modules had rows and no
        # site, a drop there invisible; the author's pass 8: over the readable rows, so a module all of whose rows use a form the textual
        # census declines is not a false red here, and the form-space pin below holds those forms)
        self.assertTrue(sites, "the textual census found no assertion over a served text")
        self.assertEqual(sorted(set(sites) - {r[:5] for r in rows}), [], "sites the textual census reads and the derivation does not")
        self.assertGreaterEqual(len(rows), len(sites), "the population is every assertion of a literal over a served text across the suite: %d rows, %d sites" % (len(rows), len(sites)))
        readable_modules = {r[0] for r in rows if r[5]}
        self.assertTrue(readable_modules, "no module has a row in a form the textual census reads")
        self.assertEqual(sorted(readable_modules ^ {s[0] for s in sites}), [],
                         "modules with readable rows and no textual site, or the reverse: widen the textual census to the form the derivation read, or write the pin in a form it reads")
        self.assertTrue({r[3] for r in rows} & set(getters) and {r[3] for r in rows} & set(constants), "rows over pages and over constants both derived")
        self.assertTrue({r[3] for r in rows} - set(getters) - roster, "rows over constants outside the author's pass 6 roster (the class the roster missed): %r" % (sorted({r[3] for r in rows} - set(getters)),))
        # the container NAMES the tests pin, read from the test text on their own: every getter the tests call is derived, and
        # every `_CAPS` str the tests assert over that is served (by suffix or by landing in a page) is derived; both sides
        # non-empty, and the pinned names reach past the roster
        pinned_getters = {n for n, call in pinned if call and _GETTER_NAME.fullmatch(n)}
        pinned_caps = {n for n, call in pinned if not call and _CAPS.fullmatch(n)}
        self.assertTrue(pinned_getters and pinned_caps, "the tests pin getters and constants: %r" % (sorted(pinned),))
        self.assertEqual(sorted(pinned_getters - set(getters)), [], "page getters the tests pin that the derivation does not read")
        pinned_served = {n for n in pinned_caps if isinstance(getattr(km, n, None), str) and (_suffix_kind(n) or landing_kinds(getattr(km, n)))}
        self.assertTrue(pinned_served - roster, "the tests pin a served constant outside the author's pass 6 roster: %r" % (sorted(pinned_served),))
        self.assertEqual(sorted(pinned_served - set(constants)), [], "served constants the tests pin that the derivation does not read")
        bad = []
        for fname, line, lit, name, form, _ in rows:
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

    def test_no_reader_row_lies_inside_an_f_string(self):
        # the one-cell design's premise (the module docstring's last paragraph), pinned on EVERY interpreter: this test carries no
        # skip. A reader row's `source` column is the module text between its node's positions, and a node's position inside an
        # f-string's braces is the one AST input that differs by interpreter (PEP 701, 3.12), so the census's rows are the same on
        # every interpreter exactly as long as no row's node sits inside an f-string. Derived from the census, not listed: every
        # f-string of every population module is walked, and every node inside one is matched against that module's reader rows
        # by line and by the source segment the way readers_of writes the column (the segment itself, or after the `<callee>: ` or
        # `helper <name>: ` prefix of a method, value-use or unclassified row). The f-strings scanned and their replacement fields
        # are counted, so a population that stopped holding any would red here rather than pass for nothing.
        fstrings, braces, offending = 0, 0, []
        for path in population():
            tree, lines = _parsed(path)
            rows = _readers(path)   # read right after the parse, so a cell that skips the census parses each module once here too
            inside = {}
            for js in ast.walk(tree):
                if isinstance(js, ast.JoinedStr):
                    fstrings += 1
                    braces += sum(isinstance(v, ast.FormattedValue) for v in js.values)
                    for node in ast.walk(js):
                        if node is not js and hasattr(node, "lineno"):
                            inside.setdefault(node.lineno, set()).add((_segment(lines, node) or "").replace("\n", " ")[:160])
            for line, form, text, source in rows:
                if any(s and (source == s or source.endswith(": " + s)) for s in inside.get(line, ())):
                    offending.append("%s:%d %s %s: %s" % (os.path.basename(path), line, form, text, source))
        self.assertGreater(fstrings, 0, "no f-string in the population: the premise is vacuous here, re-derive it")
        self.assertGreater(braces, 0, "no f-string of the population carries a replacement field (%d f-strings): the premise is vacuous here" % fstrings)
        self.assertEqual(offending, [], "a reader row's node lies inside an f-string (%d f-strings with %d replacement fields scanned), the one AST "
                         "input whose positions differ by interpreter: the census's one-cell design (the module docstring) rests on there being "
                         "none, so RE-OPEN it, every interpreter cell running the census or the row moved out of the f-string; the first: %s"
                         % (fstrings, braces, offending[0] if offending else ""))

    def test_the_derivation_reads_the_forms_it_claims(self):
        # the population is a derivation, so its form space is pinned: a getter call inline, a Name bound in the function,
        # a tuple assignment by position, a self.<attr> bound in setUp; a Name bound to something else is not a row. The author's pass 5
        # (2026-09-20): a loop variable over a tuple or list of literals (one row per literal), assertTrue(lit in page) and a
        # bare assert; a literal bound by assignment stays outside (the bound in the docstring). The author's pass 6 (2026-09-20): a served
        # constant inline and bound, a module-level function, a conjunction inside assert or assertTrue (one row per conjunct),
        # a Name bound to a slice of a page, the position forms index, find, rindex, rfind and count; a dynamically resolved
        # getter (getattr) stays outside (the bound). The author's pass 7 (2026-09-20): a `for` over served texts (one row per text, a
        # membership and a position form), a comprehension over literals, a position form over a loop literal, and the
        # constants of every kind the rule derives (a style constant, an HTML constant, a bare script constant and a markup
        # constant outside the author's pass 6 roster), each name derived here, not written. The author's pass 8: a body fetched by a literal path,
        # and (the fixer pass) by a formatted url with the token in its query, bound by the with-item's `as` target; a token-less
        # url and an unmapped path bind nothing. The fixer pass of the author's pass 9: a binding at module level (MOD) and an alias of a bound Name
        # or self.<attr> (alias, al2), each a row and a site. The module is built over EVERY derived
        # getter, so a new getter is pinned by construction, and every expectation fails on an empty derivation
        getters, constants, routes = page_getters(), served_constants(), route_getters()
        css = sorted(c for c in constants if c.endswith("_CSS"))[0]   # one constant of each kind, derived
        html = sorted(c for c in constants if c.endswith("_HTML"))[0]
        script = max((c for c in constants if not _suffix_kind(c) and constants[c] == {"script"}), key=lambda c: len(getattr(km, c)))
        mark = max((c for c in constants if not _suffix_kind(c) and constants[c] == {"markup"}), key=lambda c: len(getattr(km, c)))
        self.assertTrue(css and html and script and mark and len(getters) >= 2, (css, html, script, mark, getters))
        head = '''MOD = km._feed_page()
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
        self.assertIn("y\\tz", page)
        self.assertIn("""tq""", page)
        _, body = fetch("/sw.js", headers={})
        worker = body.decode()
        self.assertIn("f1", worker)
        text = fetch("/chat?token=x").read().decode("utf-8", "replace")
        self.assertIn("f2", text)
        got = self._get("/")
        self.assertIn("f3", got)
        nope = fetch("/nope")
        self.assertIn("f4", nope)
        clean = served_css.js_code(body.decode())
        self.assertIn("f5", clean)
        parts = path.split("/")
        self.assertIn("f6", parts)
        with urllib.request.urlopen("http://127.0.0.1:%d/chat?token=x" % self.port, timeout=5) as r:
            fetched = r.read().decode("utf-8", "replace")
        self.assertIn("f7", fetched)
        with urllib.request.urlopen("http://127.0.0.1:%d/" % self.port, timeout=5) as r2:
            login = r2.read().decode("utf-8", "replace")
        self.assertIn("f8", login)
        with urllib.request.urlopen("http://127.0.0.1:%d/healthz?token=x" % self.port, timeout=5) as r3:
            health = r3.read().decode()
        self.assertIn("f9", health)
        self.assertIn("m1", MOD)
        alias = page
        self.assertIn("m2", alias)
        al2 = self.html
        self.assertIn("m3", al2)
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
            rows = rows_of(f.name, getters, constants, routes)
            sites, containers = textual_census(f.name, getters, constants, routes)
        finally:
            os.unlink(f.name)
        L = head.count("\n") + 1   # the loop line's number: head ends with a newline, so its line count is the loop's line less one
        expected = [(6, "x", "_chat_page", "in"), (8, "y", "_feed_page", "in"), (10, "z", "_timeline_page", "in"), (12, "v", "_landing", "in"),
                    (15, "p", "_feed_page", "in"), (15, "q", "_feed_page", "in"), (17, "r", "_feed_page", "in"), (18, "s", "_landing", "in"), (19, "t", "_feed_page", "in"),
                    (23, "m", "_LANDING_MOBILE_JS", "in"), (25, "l", "_LANDING_MOBILE_JS", "in"), (26, "k", "_feed_page", "in"), (26, "j", "_LANDING_MOBILE_JS", "in"),
                    (28, "h", "_feed_page", "in"), (29, "g", "_feed_page", "index"), (29, "f", "_feed_page", "index"), (30, "e", "_LANDING_MOBILE_JS", "count"),
                    (31, "d", "_feed_page", "find"), (31, "c", "_feed_page", "rindex"), (31, "b", "_feed_page", "rfind"),
                    (34, "y\tz", "_feed_page", "in"), (35, "tq", "_feed_page", "in"),
                    (38, "f1", "_sw_js", "in"), (40, "f2", "_chat_page", "in"), (42, "f3", "_landing", "in"),   # the fetched forms (the author's pass 8)
                    (51, "f7", "_chat_page", "in"),   # a formatted url with the token, bound by the with-item's `as` (the fixer pass of the author's pass 8)
                    (58, "m1", "_feed_page", "in"), (60, "m2", "_feed_page", "in"), (62, "m3", "_landing", "in")]   # a module-level binding and two aliases (the fixer pass of the author's pass 9)
        expected += [(L + 1, "a1", g, "in") for g in getters] + [(L + 2, "a2", g, "index") for g in getters]
        expected += [(L + 5, "a4", "_feed_page", "index"), (L + 5, "a5", "_feed_page", "index"), (L + 6, "a6", "_feed_page", "index"), (L + 6, "a7", "_feed_page", "index"),
                     (L + 7, "a8", css, "in"), (L + 8, "a9", html, "in"), (L + 10, "b1", script, "in"), (L + 11, "b2", mark, "in"), (L + 12, "b4b5", "_feed_page", "in"),
                     (L + 19, "x1", "_landing", "in"), (L + 19, "x2", "_landing", "in"), (L + 20, "x3", "_landing", "in")]
        self.assertEqual([r[:4] for r in rows], expected)
        self.assertNotIn(("a3", "in"), {(lit, form) for _, lit, _, form, _ in rows}, "the loop variable is bound to the loop's body only")
        self.assertNotIn(("b3", "in"), {(lit, form) for _, lit, _, form, _ in rows}, "a loop whose iterable mixes a text with something else binds nothing")
        # the author's pass 8 (2026-09-20): a fetch of an unmapped path, a body passed through served_css.js_code, and a method call on another
        # object with a route-shaped literal (path.split("/")) bind nothing; the fixer pass: nor a formatted url of a page route with
        # no token in its query (the gate's paste-the-token page, f8), nor one of a path the dispatch does not map (f9)
        self.assertEqual({lit for _, lit, _, _, _ in rows} & {"f4", "f5", "f6", "f8", "f9"}, set())
        # the author's pass 8 (2026-09-20): the rows the textual census declines, by form: a loop or comprehension literal (p, q, r, a4 to a7),
        # a name bound to a slice (h), a literal with a backslash and a triple-quoted one; every other row is readable
        declined = {(15, "p"), (15, "q"), (17, "r"), (28, "h"), (L + 5, "a4"), (L + 5, "a5"), (L + 6, "a6"), (L + 6, "a7"), (34, "y\tz"), (35, "tq")}
        self.assertEqual({(line, lit) for line, lit, _, _, readable in rows if not readable}, declined)
        # the textual census reads the inline forms, the one-line bound form (a Name, a self.<attr>), the tuple binding (by
        # position, an item that is no served text binding nothing), the bare assert and assertTrue lines, the position forms,
        # the for over texts, the fetched forms (a literal path, a formatted url with the token) and an implicit concatenation
        # of literals across the lines of one statement; the loop over
        # literals, the comprehension and the slice are the derivation's alone. Each site is a row
        expected_sites = [(6, "x", "_chat_page", "in"), (8, "y", "_feed_page", "in"), (10, "z", "_timeline_page", "in"), (12, "v", "_landing", "in"),
                          (18, "s", "_landing", "in"), (19, "t", "_feed_page", "in"), (23, "m", "_LANDING_MOBILE_JS", "in"), (25, "l", "_LANDING_MOBILE_JS", "in"),
                          (26, "k", "_feed_page", "in"), (26, "j", "_LANDING_MOBILE_JS", "in"), (29, "g", "_feed_page", "index"), (29, "f", "_feed_page", "index"),
                          (30, "e", "_LANDING_MOBILE_JS", "count"), (31, "d", "_feed_page", "find"), (31, "c", "_feed_page", "rindex"), (31, "b", "_feed_page", "rfind"),
                          (38, "f1", "_sw_js", "in"), (40, "f2", "_chat_page", "in"), (42, "f3", "_landing", "in"), (51, "f7", "_chat_page", "in"),
                          (58, "m1", "_feed_page", "in"), (60, "m2", "_feed_page", "in"), (62, "m3", "_landing", "in")]
        expected_sites += [(L + 1, "a1", g, "in") for g in getters] + [(L + 2, "a2", g, "index") for g in getters]
        expected_sites += [(L + 7, "a8", css, "in"), (L + 8, "a9", html, "in"), (L + 10, "b1", script, "in"), (L + 11, "b2", mark, "in"), (L + 12, "b4b5", "_feed_page", "in"),
                           (L + 19, "x1", "_landing", "in"), (L + 19, "x2", "_landing", "in"), (L + 20, "x3", "_landing", "in")]
        self.assertEqual(sites, expected_sites)
        self.assertTrue(set(sites) <= {r[:4] for r in rows if r[4]}, "every site is a readable row")
        # the containers the module pins, whatever the name: the getters, the constants, and `other` and `dyn` are not containers
        self.assertEqual(containers, {(g, True) for g in getters} | {("_LANDING_MOBILE_JS", False), (css, False), (html, False), (script, False), (mark, False)})

    @unittest.skipUnless(sys.version_info[:2] == _CENSUS_CELL, _ONE_CELL_REASON)
    def test_every_reader_of_a_served_page_is_the_parser_or_a_stated_read(self):
        # the author's pass 9 (2026-09-20), the maintainer's round 5 ruling asked once, of every road that reads the served page, whether it is
        # HTML-correct or refuses what it cannot resolve: the change had moved the element reads onto html.parser as ruled and then
        # added a fresh regex over the raw page beside it (the viewport meta, satisfiable by a commented copy, the case it existed to
        # stop). The population is EVERY read of a served text across the suite, derived by readers_of (its form space in
        # READER_FORMS and pinned below), and each form has a status: the parser road (`parser`); a stated read that is not a read of
        # markup by another road (`assert`: a literal membership the pins census judges or a whole-text compare; `position` with a
        # literal needle: a pins-census row, an order or count over text the census judges against every comment span, not an
        # element's extent or attributes; `view-pin`: a literal membership or position pin over the parser's comment-blanked VIEW of
        # the text, served_css.code, markup, js_code or css_code, the author's pass 6 re-point form, not comment-satisfiable by construction;
        # `span-slice`: parser-derived offsets; `conversion` and `value-use`: the text handed whole to a callable of the stated
        # allowlist, not read here; `splice`: the text copied into another string, not read there, what reads the result being a
        # read over a copy; `compare`); a raw read of markup (`regex`, `slice`, `method`, `position-unpinned`,
        # `membership-unpinned`, the last two also a literal pin over a COPY of the text, a str-method result, a slice or a line of
        # it, which the pins census does not judge): a road beside the parser, which a module that has adopted the parser road (it
        # IMPORTS served_css, _imports_parser) may not keep, and which a module that has not is reported with (the sweep left, a
        # figure, not a red here); a read over a text that is JS or CSS source and not markup (a script or style constant, a script
        # getter) is `source`: the element layer has no element to offer for it, and its literal pins are the pins census's. A form
        # the walk cannot name reds everywhere, and so does `unclassified`, the text handed whole to a callable outside the
        # allowlist (the fixer pass of the author's pass 9: an unknown callee had defaulted to value-use, so a parser of its own, an imported
        # helper or a compiled pattern from another module read the page unseen; and a read over a view, a copy, an alias or a
        # module-level binding of the text had produced no row at all: the author's pass 6 order pins over served_css.code were outside the
        # population the record called every read).
        getters, constants, routes = page_getters(), served_constants(), route_getters()
        kinds = {g: frozenset([getter_kind(g)]) for g in getters}
        kinds.update(constants)
        rows, pins, road = [], set(), {}
        for fname, (derived, _, on_road, readers) in population_census().items():   # derived once per process, shared with the pins census
            road[fname] = on_road
            rows += [(fname, line, form, text, source) for line, form, text, source in readers]
            pins |= {(fname, line, text) for line, lit, text, form, readable in derived if form in _POSITION}
        self.assertGreater(len(rows), 1000, "the population read: %d rows" % len(rows))
        self.assertEqual(sorted({r[2] for r in rows} - set(READER_FORMS)), [], "a form readers_of names that READER_FORMS does not")
        self.assertTrue(len({r[2] for r in rows}) >= 10, "the forms met across the suite: %r" % (sorted({r[2] for r in rows}),))
        def status(fname, line, form, text, source):
            if form == "position" and (fname, line, text) not in pins:
                form = "position-unpinned"   # a position pin the pins census does not see (inside a followed helper): raw
            if form in ("parser", "assert", "position", "view-pin", "span-slice", "conversion", "value-use", "splice", "compare"):
                return form
            if form == "unclassified":
                return "unclassified"
            return "raw" if "markup" in kinds[text] else "source"
        by = {}
        for r in rows:
            by.setdefault(status(*r), []).append(r)
        self.assertEqual(by.get("unclassified", []), [], "a read of a served text the walk cannot classify (a callee outside the stated allowlist):\n"
                         + "\n".join("%s:%d %s %s: %s" % r for r in by.get("unclassified", [])))
        self.assertTrue(by.get("view-pin"), "literal pins over the parser's comment-blanked view (the author's pass 6 re-point form) are rows")
        self.assertTrue(sum(road.values()) >= 15 and all(road[f] for f in ("test_kernel_mobile.py", "test_shell_viewport_fit.py", "test_spend_detail.py")), road)
        raw_on_road = [r for r in by.get("raw", []) if road[r[0]]]
        self.assertEqual(raw_on_road, [], "a module on the parser road reads the page by another road; route it through served_css or state it:\n"
                         + "\n".join("%s:%d %s %s: %s" % (f, l, form, t, src) for f, l, form, t, src in raw_on_road))
        # the parser road is live across the suite, and the classes it replaced are met (so the census reads them)
        self.assertTrue([r for r in by.get("parser", []) if road[r[0]]], "parser-road reads")
        self.assertTrue(by.get("source"), "reads over a script or style constant, JS or CSS source: %r" % (len(by.get("source", [])),))
        self.assertTrue(by.get("position"), "position pins tied to pins-census rows")
        self.assertTrue([r for r in by.get("value-use", []) if r[4].startswith("helper ")], "a helper followed one level")
        # the sweep left, reported: raw markup reads in modules not on the parser road (a figure the record carries; not a red here)
        off = by.get("raw", [])
        self.assertEqual([r for r in off if road[r[0]]], [])
        self.assertTrue(all(not road[r[0]] for r in off), "every remaining raw markup read is in a module not on the parser road: %d reads in %d modules"
                        % (len(off), len({r[0] for r in off})))

    def test_no_tracked_element_sits_under_a_container_the_reader_does_not_read(self):
        # the author's pass 9 (2026-09-20), the maintainer's round 5 ruling: the reader's roster of untracked containers (template, noscript)
        # justified itself with "no served page carries either" and omitted svg, which served pages do carry as live markup and
        # inside which both engines parse a style's or script's content as markup. The reader refuses a tracked element under such
        # a container now (served_css.REFUSED_CONTAINERS), and the justification is this census, DERIVED over every page the
        # kernel's GET dispatch serves (route_getters, the markup kind), never listed by hand: the containers each tracked element
        # sits under (the reader's own stack, one-sided: it can over-report an ancestor, never lose one) and the pages carrying each
        # refused container as a live start tag. The figures are asserted where they carry the argument: at least one served page
        # carries svg as live markup (so the refusal is exercised against the live case, not a hypothetical one), and no tracked
        # element sits under any refused container (the reader would have refused first; this states it as a count). A new refused
        # container on a page reds here by the reader's refusal at parse, and a new container of any kind under a tracked element
        # joins the roster this census derives.
        routes = route_getters()
        pages_ = sorted({g for g in routes.values() if getter_kind(g) == "markup"})
        self.assertGreaterEqual(len(pages_), 8, "the served pages, from the route table: %r" % (pages_,))
        texts = pages()
        under, carrying, roster = [], {c: [] for c in sorted(served_css.REFUSED_CONTAINERS)}, set()
        for g in pages_:
            page = texts[g]
            els = served_css.elements(page)   # parses, or the reader has refused a tracked element under a refused container
            self.assertTrue([e for e in els if e.kind in ("script", "style")], "%s carries script or style elements" % g)
            for e in els:
                roster |= set(e.stack)
                under += [(g, e.kind, c) for c in e.stack if c in served_css.REFUSED_CONTAINERS]
            counts = served_css.tag_counts(page)
            for c in carrying:
                if counts.get(c):
                    carrying[c].append((g, counts[c]))
        self.assertEqual(under, [], "a tracked element under a refused container")
        self.assertTrue(carrying["svg"], "at least one served page carries <svg> as live markup, the case the roster omitted: %r" % (carrying,))
        self.assertGreaterEqual(len(carrying["svg"]), 2, "the pages carrying svg markup (two at the author's pass 9): %r" % (carrying["svg"],))
        self.assertEqual([c for c in ("math", "template", "noscript") if carrying[c]], [], "no served page carries these today: %r" % (carrying,))
        self.assertTrue({"html", "head", "body"} <= roster, "the containers tracked elements sit under, derived: %r" % (sorted(roster),))
        self.assertEqual(sorted(roster & served_css.REFUSED_CONTAINERS), [], "the derived roster holds no refused container: %r" % (sorted(roster),))

    def test_the_reader_census_reads_the_forms_it_claims(self):
        # the reader census is a derivation, so its form space is pinned on a synthetic module holding one site of every form in
        # READER_FORMS, each named here, never inferred from the suite: the parser road inline and through an imported name, an
        # assert, a literal position pin and one with a Name needle, a non-literal membership, a regex through re and through a
        # compiled pattern, a slice by index and a slice by parser-derived spans, a str method, a conversion, a value-use (json.dumps)
        # and a helper followed one level (its membership a row at its own line), a whole-text compare, and a read over a script
        # constant (its form is the read's; the census test gives it the `source` status by the text's kind). The fixer pass of the author's pass
        # 9 adds the gaps it found: a VIEW bound to a Name and inline (a position pin and a membership over it: view-pin; a regex
        # over it: regex), a COPY by a str method, a slice, a line of splitlines and a for over the pieces (a literal pin over one:
        # position-unpinned or membership-unpinned; the method itself a row), a module-level binding and an alias (a pins-census
        # row: position), a bare assert's literal membership (assert), another string's method taking the text (value-use), a
        # method of the class followed one level, and three callees outside the allowlist (unclassified: an imported compiled
        # pattern, an imported helper, a parser of its own), so the catch-all is met too. The close of the author's pass 9 adds the
        # forms the walk had been silent on (no row at all): a text handed by keyword (to an unknown callee: unclassified; as
        # assertIn's container: assert; to re.search: regex; to a helper, bound to its parameter by name so the helper's read is a
        # row), a splice by concatenation, by %-format and by f-string (the splice itself, and a position pin over the result:
        # position-unpinned; a bound splice with a bare-assert membership over it: membership-unpinned), a dict literal handed to
        # json.dumps and a list literal handed to another string's join, to subprocess.run and, starred, to print (value-use), a list
        # handed to list() (unclassified), assertRegex over the text (regex, where it had read as assert), and a splice in
        # assertIn's member position (the row is over the container, the page; the splice its own row over the constant)
        getters, constants, routes = page_getters(), served_constants(), route_getters()
        src = '''
import re
import served_css
from served_css import code
from other import PAT2, parse_it
PAT = re.compile("x")
HTML = km._landing()
def _has(self, lit, body):
    self.assertIn(lit, body)
def _win(page):
    return page[page.index("<a>"):page.index("</a>")]
class T(unittest.TestCase):
    def _lines(self, js):
        return js.splitlines()
    def test_a(self):
        page = km._landing()
        served_css.rules(page)
        code(page)
        self.assertIn("x", page)
        page.index("x")
        tok = "y"
        page.count(tok)
        assert tok in page
        re.search("z", page)
        PAT.findall(page)
        page[3:9]
        for s, e in served_css.comment_spans(page):
            page[s:e]
        page.split("<")
        page.encode()
        json.dumps(page)
        _has(self, "w", page)
        _win(page)
        page == "q"
        re.search("v", km._LANDING_MOBILE_JS)
        f.write(page)
        c = served_css.code(page)
        c.index("u")
        self.assertIn("t", served_css.markup(page))
        re.findall("s", c)
        s = page.lower()
        s.index("r")
        assert "q2" in s
        lines = page.splitlines()
        lines[0].index("p")
        for line in page.splitlines():
            line.index("o")
        HTML.index("n")
        assert "m" in page
        other.replace("__X__", page)
        alias = page
        alias.index("l")
        self._lines(page)
        PAT2.search(page)
        parse_it(page)
        etree.fromstring(page)
        parse_it(text=page)
        self.assertIn("k1", container=page)
        re.search("k2", string=page)
        (page + "k3").index("k4")
        f"{page}".index("k5")
        ("%s" % page).index("k6")
        cat = page + "k7"
        assert "k8" in cat
        json.dumps({"k": page})
        "".join([page])
        subprocess.run([node, "-e", page])
        print(*[page])
        list(page)
        self.assertRegex(page, "k9")
        self.assertIn("k10" + km._LANDING_MOBILE_JS, page)
        _kw(self, "k11", body=page)
def _kw(self, lit, body):
    body.index(lit)
'''
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write(src)
        try:
            rows = readers_of(f.name, getters, constants, routes)
        finally:
            os.unlink(f.name)
        self.assertEqual([(line, form, text) for line, form, text, _ in rows],
                         [(9, "assert", "_landing"), (11, "position", "_landing"), (11, "position", "_landing"), (11, "slice", "_landing"), (14, "method", "_landing"),
                          (17, "parser", "_landing"), (18, "parser", "_landing"), (19, "assert", "_landing"), (20, "position", "_landing"),
                          (22, "position-unpinned", "_landing"), (23, "membership-unpinned", "_landing"), (24, "regex", "_landing"), (25, "regex", "_landing"),
                          (26, "slice", "_landing"), (27, "parser", "_landing"), (28, "span-slice", "_landing"), (29, "method", "_landing"), (30, "conversion", "_landing"),
                          (31, "value-use", "_landing"), (32, "value-use", "_landing"), (33, "value-use", "_landing"), (34, "compare", "_landing"),
                          (35, "regex", "_LANDING_MOBILE_JS"), (36, "value-use", "_landing"),
                          (37, "parser", "_landing"), (38, "view-pin", "_landing"), (39, "parser", "_landing"), (39, "view-pin", "_landing"), (40, "regex", "_landing"),
                          (41, "method", "_landing"), (42, "position-unpinned", "_landing"), (43, "membership-unpinned", "_landing"),
                          (44, "method", "_landing"), (45, "position-unpinned", "_landing"), (45, "slice", "_landing"), (46, "method", "_landing"), (47, "position-unpinned", "_landing"),
                          (48, "position", "_landing"), (49, "assert", "_landing"), (50, "value-use", "_landing"), (52, "position", "_landing"), (53, "value-use", "_landing"),
                          (54, "unclassified", "_landing"), (55, "unclassified", "_landing"), (56, "unclassified", "_landing"),
                          # the close of the author's pass 9: the keyword, splice, container and assertRegex forms
                          (57, "unclassified", "_landing"), (58, "assert", "_landing"), (59, "regex", "_landing"),
                          (60, "position-unpinned", "_landing"), (60, "splice", "_landing"), (61, "position-unpinned", "_landing"), (61, "splice", "_landing"),
                          (62, "position-unpinned", "_landing"), (62, "splice", "_landing"), (63, "splice", "_landing"), (64, "membership-unpinned", "_landing"),
                          (65, "value-use", "_landing"), (66, "value-use", "_landing"), (67, "value-use", "_landing"), (68, "value-use", "_landing"),
                          (69, "unclassified", "_landing"), (70, "regex", "_landing"), (71, "assert", "_landing"), (71, "splice", "_LANDING_MOBILE_JS"),
                          (72, "value-use", "_landing"), (74, "position-unpinned", "_landing")])
        self.assertEqual([r[3] for r in rows if r[1] == "method"], ["splitlines: js.splitlines()", "split: page.split(\"<\")", "lower: page.lower()",
                                                                    "splitlines: page.splitlines()", "splitlines: page.splitlines()"])
        self.assertEqual([r[3] for r in rows if r[1] == "splice"], ['page + "k3"', 'f"{page}"', '"%s" % page', 'page + "k7"', '"k10" + km._LANDING_MOBILE_JS'])
        self.assertEqual([r[3] for r in rows if r[0] == 74], ["body.index(lit)"], "the helper's parameter bound by keyword, its read a row at the helper's line")
        self.assertEqual([r[3] for r in rows if r[0] in (58, 59, 70)], ['self.assertIn("k1", container=page)', 're.search("k2", string=page)', 'self.assertRegex(page, "k9")'])
        self.assertTrue([r for r in rows if r[1] == "value-use" and r[3].startswith("helper _has")] and [r for r in rows if r[1] == "value-use" and r[3].startswith("helper _win")]
                        and [r for r in rows if r[1] == "value-use" and r[3].startswith("helper _lines")], "helpers and a method of the class followed one level")
        self.assertEqual([r[3].split(":")[0] for r in rows if r[1] == "unclassified"], ["search", "parse_it", "fromstring", "parse_it", "list"])
        self.assertEqual([r[3].split(":")[0] for r in rows if r[1] == "value-use" and not r[3].startswith("helper")], ["dumps", "write", "replace", "dumps", "join", "run", "print"])
        self.assertTrue([r for r in rows if r[1] == "value-use" and r[3].startswith("helper _kw")], "a helper handed the text by keyword is followed")
        self.assertEqual(sorted({r[1] for r in rows} - set(READER_FORMS)), [])
        self.assertEqual(sorted(set(READER_FORMS) - {r[1] for r in rows}), [], "every named form, the catch-all included, is met by the synthetic module")
        # the parser road's membership test is the IMPORT (the fixer pass of the author's pass 9: it had been the string anywhere in the file): a module
        # naming served_css in a comment alone is not on the road, one importing it under either form is
        for text, on_road in (("# served_css is not imported here\n", False), ("import served_css\n", True), ("from served_css import code\n", True), ("import os\n", False)):
            with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
                f.write(text)
            try:
                self.assertEqual(_imports_parser(f.name), on_road, text)
            finally:
                os.unlink(f.name)

    def test_the_route_walk_reads_equality_and_membership(self):
        # the author's pass 8 (2026-09-20): the (route, getter) pairs are derived from the handler by a shape-sensitive walk, never restated. A
        # synthetic handler with both shapes pins the two: the landing's membership tuple and the equality routes; a route
        # returning json.dumps, a getter called with arguments and a prefix test bind nothing. An equality-only walk misses the
        # landing here and on the kernel (eight routes believing nine).
        handler = '''
def do_GET(self):
    p = "/x"
    if p in ("/", ""):
        return self._send(200, _landing(), "text/html")
    if p == "/chat":
        return self._send(200, _chat_page(), "text/html")
    if p == "/sw.js":
        return self._send(200, _sw_js(), "text/javascript")
    if p == "/tunnels/of":
        return self._send(200, json.dumps({}), "application/json")
    if p == "/shim":
        return self._send(200, _shim_core_js("chat"), "text/javascript")
    if p.startswith("/dist/"):
        return self._send_file(p)
'''
        self.assertEqual(route_getters(handler), {"/": "_landing", "": "_landing", "/chat": "_chat_page", "/sw.js": "_sw_js"})
        real = route_getters()
        self.assertEqual((real.get("/"), real.get("")), ("_landing", "_landing"), "the landing's membership form on the kernel: %r" % (real,))
        self.assertIn("/sw.js", real, "an equality route on the kernel: %r" % (real,))
        self.assertEqual(sorted(set(real.values()) - set(page_getters())), [], real)


if __name__ == "__main__":
    unittest.main()
