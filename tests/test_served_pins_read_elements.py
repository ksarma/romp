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
literal occurs ONLY in comments pins prose and is reported the same way. The texts a row is judged against (judged_texts; the
rulings at the merge of main's login cookie split, 2026-09-28): a constant's value; a getter's render and every string constant
its own return statements return (getter_renders: the page `_files_page` serves when its sheet cannot be read); and for a row over
a FETCHED body each of those as the kernel's Handler._send serves it on a sign-in response (served_body: _send itself, run on a
stand-in request, so the sign-in seed and _PAGE_KEY_JS go first in a page's head in the order _send assembles them). A row whose
literal occurs in NONE of its texts fails (judge_rows): its verdict proves nothing, since no comment can satisfy what the text
does not carry; before the rulings such rows passed in silence (four at the merge).

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
comprehension variable are not), and its container must not be a name bound to a slice or a subscript (a fetched tuple's body
position, `resp[1]`, a name bound to one, or a name unpacked from one); a module all of whose rows are in
declined forms is outside the module symmetry (its rows are still judged, and the form-space pin below holds the declined
forms), so a sound module reds nothing there while a module with one readable row and no site still does. The form space is
pinned on a synthetic module below (a form the derivation stops reading fails there), built over every derived getter and
over a derived constant of each kind. The container NAMES the tests pin are derived from the test text on their own and
held to the kernel-derived getters and constants (a getter the tests call or a served str the tests assert over that the
derivation does not read fails there; the author's pass 7).

The fetched route (the author's pass 8, 2026-09-20): a fetched body is read as the text of the route it fetched, as served (the
paragraph above). The (route, getter) pairs are derived from the kernel's GET dispatch by an AST walk (route_getters), never restated. It reads three shapes. Two are
an `if` comparing one Name against a string literal by EQUALITY (`if p == "/sw.js": return self._send(200, _sw_js(), ...)`) or
by MEMBERSHIP in a tuple of literals (`if p in ("/", ""):`) whose body returns a call carrying a call to a derived getter with
no arguments. The third is a ROUTE TABLE, the kernel's page dispatch since the merge of main's login cookie split (2026-09-28):
a dict literal bound to a Name, its keys string literals and its values derived getters named bare (`_PAGE_RENDERERS = {"":
_landing, "/": _landing, "/chat": _chat_page, ...}`), looked up as `<v> = <table>.get(<Name>)` in a function that returns a
call carrying `<v>()` with no arguments (`_page = _PAGE_RENDERERS.get(p)`, `return self._send(200, _page(), ...)`). In all
three, "carrying" means as a POSITIONAL argument of the returned call, itself the getter's call: one inside a wrapper call, a
splice or an f-string argument, or handed by keyword, binds nothing (the rulings on the census pass and on the census bounds,
2026-09-28; pinned in the two route tests). Before that
branch the walk found the service worker alone on the merged kernel, so every fetched row over a page left the population and
the container census below read no page; with it the kernel's routes are the ten they were before the table (the landing twice,
the seven pane pages, the service worker). The walk is shape-sensitive: it reads those three shapes and no other, so a fourth
(a `match`, a comparison through a helper, a table whose value is a lambda or a getter called with arguments) is outside it
until a branch is added and pinned in the form-space tests below (a naive equality walk misses the landing). A fetch is a call to a Name or a
self.<method> (a test helper over the handler or an HTTP client) whose first argument is a string literal beginning with `/`
that, without its ?query, is such a route (or a concatenation led by such a literal that holds the whole path, its `?` inside
the literal: `self._req("/?token=" + tok)`, the form main's login cookie split added to the suite, merged 2026-09-28), or a
call to an attribute named `urlopen` whose first argument is a string literal,
bare or `%`-formatted, of the form `http://127.0.0.1:%d/<route>?...token=...` (the `with ... as r` target is what it binds;
the fixer pass of the author's pass 8: the tokened fetches in tests/test_kernel.py carried 39 pins over five pages outside the population, one
of them satisfiable by three comments of the timeline page); a method call on another object (`path.split("/")`) is not one.
A fetched value unpacked into a tuple binds only the position the helper's own return statements read a response at (`status,
body, headers = self._req("/")` binds `body` where `_req` returns `r.status, r.read(), r.headers`), and no name where its returns
read none; a helper the module does not define binds every name (the rulings at the merge of main's login cookie split,
2026-09-28; _bind). A call to a helper the module defines is a fetch only where the helper's returns read a response
(`_pathconf("/", "PC_PATH_MAX", 4096)` is none; _fetched). A fetched tuple bound to ONE name is no text itself: each position the
helper reads a response at is, by a constant index (`resp = self._req("/")` gives `resp[1]` and `resp[-2]`), bound to a name or
unpacked after by a tuple target holding no starred name, and the status and headers positions are none (the rulings on the census
pass, 2026-09-28; _bind). Every other read of such a name is REFUSED, an unclassified row the reader census fails on (the rulings on
the census bounds, 2026-09-28; readers_of): an alias (`r2 = resp`), a subscript by anything but a constant index (`resp[i]`,
`resp[1:]`), a `for` over it, a starred unpack (which binds no name), the name handed whole to a helper or any other call, a
membership over the tuple, and the reads of a name bound whole and later rebound to such a tuple (the walk is flow-insensitive, so
the rebinding hides the whole binding). A Name in a helper's return is followed to its
bindings inside the helper (`body = r.read(); return r.status, body, r.headers` reads at `body`'s position), and a returned Name
the follow cannot place (bound only by an unpack of a call's answer, a synchronous for or a with target, an except name) makes the
call a fetch that binds every name, so no read behind a Name returned bare leaves both censuses in silence (the rulings on the
census pass, 2026-09-28; _response_reads). A returned element that holds a read the follow does not place (a read under any
wrapper but a `.decode` chain, `r.read().strip()`, `str(r.read(), "utf-8")`, `r.read() or b""`, a conditional, `raw[3:]`; a Name
bound to one; an attribute the helper assigns one, `self.body = r.read()`) is REFUSED: every fetch of a page route through that
helper is an unclassified row the reader census fails on (the rulings on the census bounds, 2026-09-28; _response_reads,
readers_of).

Bound: a url built otherwise than as a bare or `%`-formatted literal or a concatenation led by the whole path (a `Request`
object, an f-string, `.format`, `"/chat" + rest`), a formatted
url whose query carries no `token=` (tests/test_kernel.py's token-less fetch of `/`, answered with the paste-the-token page), a
membership asserted through a helper (`_has(self, lit, body)` in tests/test_files_pane.py and tests/test_settings_page.py, whose
formatted fetches bind a name no form here reads), a fetch of a path the dispatch does not map to a getter
call (a JSON or text/plain API body, a `/dist/` bundle, a `/media/` file: outside the derivation, and not comment-satisfiable
only where the body carries no comment syntax), a page from a dynamically resolved getter (`getattr(km, "_%s_page" % name)()`,
tests/test_kernel_boot_splash.py, which reads served_css.code for the tokens a comment spells), a helper the module defines
that returns an unread response for its caller to read (`return urlopen(path)`, read as `self._open("/").read()`) or reads the
response through another call in its return (`return r.status, self._body(r)`), no fetch here (a literal pin over a name such a
call is assigned to reds the floor through the textual census; any other read of that name, a regex or a split, is in neither
census), a helper whose returns differ in length (the union of their positions: `return r.status, r.read(), r.headers` and
`return r.status, r.read()` give {1, -1, -2}, so `resp[-1]` binds as the page though it is the headers on the first road;
over-bound, so its reads are rows over the page, never silent), a name bound to a fetched tuple and later rebound to a whole text
(it reads as that text throughout, so `resp[0]`, the status before the rebinding, is a slice row over it: over-bound, never
silent), a tuple target holding a starred name over a fetch (`first, *rest = self._req("/")`: each plain name binds as the text
whatever its position, the status too, and the starred name binds nothing, so a read of the body inside it is in neither census,
in silence; p7 in test_a_fetched_tuple_binds_the_position_its_helper_reads_a_response_at), a returned element that wraps a Name
the follow cannot place, or a Name bound to such a wrapper (`status, raw = _raw(path)` and then `return 200, raw.strip()`, `return
200, raw[3:]`, `return raw.strip()`, or `text = raw.strip(); return 200, text`: no position, so its call is no fetch; a literal pin
over a name the call is assigned to reds the floor through the textual census, and any other read of that name, a regex or a split,
is in neither census, in silence; x1 in test_d of
test_a_returned_name_is_followed_to_its_binding_in_the_helper), a subscript of the fetch call itself by a constant index (`page =
self._req("/?token=x")[1]` binds nothing: a literal pin over `page` reds the floor through the textual census, and any other read
of it, or of the subscript inline, is in neither census, in silence; x2 and x3 in that test_d), a getter called WITH
arguments (`_shim_core_js("chat")` renders another text), a text served under a name with none of the suffixes the rules
read (the web app manifest; the `_reload_core` function), a name bound outside the function, a literal bound by assignment
rather than a loop, and assertNotIn (a comment can red it, never green it) are outside this derivation. One claim is stated
narrower than the code: an `async for` target returned by name is read as a for target is (_BINDERS), but no case pins that, so
the claims above stop at a synchronous for.

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
import json
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


@functools.lru_cache(maxsize=None)
def page_getters():
    """The kernel's served-text getters, derived from its source by rule: the functions named `_landing`, `_<name>_page`,
    `_<name>_js` or `_<name>_css` that a call with no arguments renders (no parameter, or every parameter defaulted). Read once per
    process (the judgment asks it per text: judged_texts)."""
    names = [n for n, params in _GETTER.findall(_kernel_source()) if not params.strip() or all("=" in p for p in params.split(","))]
    assert names, "no served-text getter derived from the kernel source"
    return tuple(sorted(set(names)))


def _returns_calling(fn, names):
    """The Names of `names` that a Return inside `fn` calls with no arguments as a POSITIONAL argument of the call it returns, the
    argument itself the call (`return self._send(200, _page(), ...)` gives `_page`; `wrap(_page())`, `_page() + tail`,
    `f"{_page()}"` and `body=_page()` give nothing)."""
    return {a.func.id for n in ast.walk(fn) if isinstance(n, ast.Return) and isinstance(n.value, ast.Call)
            for a in n.value.args if isinstance(a, ast.Call) and not a.args and not a.keywords and isinstance(a.func, ast.Name) and a.func.id in names}


@functools.lru_cache(maxsize=None)
def route_getters(source=None):
    """{route: getter} for every path the kernel's GET dispatch serves from a served-text getter, by an AST walk over the kernel
    source (or over `source`, a handler text, for the form-space pin) reading THREE shapes and no other. Two are an `if` whose test
    compares one Name against a string literal by equality (`if p == "/sw.js":`) or by membership in a tuple of string literals
    (`if p in ("/", ""):`, the landing's form before the route table), and whose body returns a call carrying a call to a derived
    getter with no arguments (`return self._send(200, _sw_js(), ...)`). The third is a ROUTE TABLE (the merge of main's login cookie
    split, 2026-09-28, which moved every page onto one): a dict literal bound to a Name, its keys string literals, read in a function
    as `<v> = <table>.get(<Name>)`, that function returning a call carrying `<v>()` with no arguments (`_page =
    _PAGE_RENDERERS.get(p)`, then `return self._send(200, _page(), ...)`); each key whose value is a derived getter named bare
    (`"/chat": _chat_page`) is a route of that getter, and a value of any other form (a lambda, a getter called with arguments, a
    name that is no derived getter) binds nothing. In each shape the getter's call is carried as a positional argument of the
    returned call and is that argument itself: inside a wrapper call, a splice or an f-string argument, or handed by keyword, it
    binds nothing (_returns_calling for the table; the same condition inline for the two `if` shapes). Shape-sensitive by design
    (the author's pass 8, 2026-09-20): a fourth shape needs a fourth branch here and a case in the form-space test; an equality-only
    walk misses the landing, and a walk without the table finds only the service worker on the kernel."""
    tree = ast.parse(_kernel_source() if source is None else source)
    getters = set(page_getters())
    routes = {}
    tables, lookups, functions = {}, [], []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(node)
        elif isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            v = node.value
            if isinstance(v, ast.Dict) and v.keys and all(isinstance(k, ast.Constant) and isinstance(k.value, str) for k in v.keys):
                tables[node.targets[0].id] = v
            elif isinstance(v, ast.Call) and isinstance(v.func, ast.Attribute) and v.func.attr == "get" and isinstance(v.func.value, ast.Name) \
                    and v.args and isinstance(v.args[0], ast.Name):
                lookups.append((node.lineno, node.targets[0].id, v.func.value.id))
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
    # the route table: each lookup is read in the innermost function holding its line, and counts only where that function returns
    # a call carrying the looked-up Name called bare
    for line, var, table in lookups:
        holders = [f for f in functions if f.lineno <= line <= f.end_lineno]
        if table not in tables or not holders:
            continue
        fn = min(holders, key=lambda f: f.end_lineno - f.lineno)
        if var not in _returns_calling(fn, {var}):
            continue
        d = tables[table]
        for k, v in zip(d.keys, d.values):
            if isinstance(v, ast.Name) and v.id in getters:
                routes.setdefault(k.value, v.id)
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


def _reads_response(node, read=frozenset()):
    """Whether an expression reads a response: `<x>.read(...)` or `<x>.getvalue(...)`, or a Name of `read` (the Names a function
    binds to such a read, _response_reads), alone or under any chain of `.decode(...)` (`r.read()`, `h.wfile.getvalue().decode(
    "utf-8", "replace")`, `body.decode()`)."""
    while isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "decode":
        node = node.func.value
    if isinstance(node, ast.Name):
        return node.id in read
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in ("read", "getvalue")


_BINDERS = (ast.Assign, ast.AnnAssign, ast.NamedExpr, ast.AugAssign, ast.For, ast.AsyncFor, ast.withitem, ast.ExceptHandler)


def _name_bindings(node):
    """[(Name, value)] for the Names one node binds in the function holding it, the value None where the node binds a Name to no
    expression of its own: an assignment's Name target, and a Name inside a tuple or list target over a tuple or list of the same
    length, by position, bind to their value, as do an annotated assignment with a value, a walrus and an augmented assignment
    (`body += r.read()`); a Name of a tuple target over any other value (`status, body = self._raw(r)`), a for target (an `async
    for` target too, which no case pins: a stated bound), a with target and an except name bind to None."""
    out = []
    def pair(t, v):
        if isinstance(t, ast.Name):
            out.append((t.id, v))
        elif isinstance(t, ast.Starred):
            pair(t.value, None)
        elif isinstance(t, (ast.Tuple, ast.List)):
            same = isinstance(v, (ast.Tuple, ast.List)) and len(v.elts) == len(t.elts) and not any(isinstance(e, ast.Starred) for e in t.elts + v.elts)
            for i, e in enumerate(t.elts):
                pair(e, v.elts[i] if same else None)
    if isinstance(node, ast.Assign):
        for t in node.targets:
            pair(t, node.value)
    elif isinstance(node, (ast.AnnAssign, ast.NamedExpr, ast.AugAssign)) and node.value is not None:
        pair(node.target, node.value)
    elif isinstance(node, (ast.For, ast.AsyncFor)):
        pair(node.target, None)
    elif isinstance(node, ast.withitem) and node.optional_vars is not None:
        pair(node.optional_vars, None)
    elif isinstance(node, ast.ExceptHandler) and node.name:
        out.append((node.name, None))
    return out


def _dotted(node):
    """`a.b.c` for an attribute chain ending at a Name (`self.body` gives "self.body"); None for any other node."""
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    return ".".join([node.id] + parts[::-1]) if parts and isinstance(node, ast.Name) else None


def _attr_bindings(node):
    """[(dotted attribute, value)] for the attribute targets one assignment binds (`self.body = r.read()`), an attribute inside a
    tuple or list target bound to the whole value; [] for any other node."""
    if isinstance(node, ast.Assign):
        targets = node.targets
    elif isinstance(node, (ast.AnnAssign, ast.AugAssign)) and node.value is not None:
        targets = [node.target]
    else:
        return []
    out, todo = [], list(targets)
    while todo:
        t = todo.pop()
        if isinstance(t, (ast.Tuple, ast.List)):
            todo.extend(t.elts)
        elif isinstance(t, ast.Starred):
            todo.append(t.value)
        elif _dotted(t):
            out.append((_dotted(t), node.value))
    return out


def _held(node):
    """(holds a read call, the Names it loads, the attribute chains it spells) for one expression, read in one walk: a `.read(...)`
    or `.getvalue(...)` call anywhere inside it, and the names and dotted chains a binding of the function may have tied to one."""
    call, names, chains = False, set(), set()
    for x in ast.walk(node):
        if isinstance(x, ast.Call) and isinstance(x.func, ast.Attribute) and x.func.attr in ("read", "getvalue"):
            call = True
        elif isinstance(x, ast.Name):
            names.add(x.id)
        elif isinstance(x, ast.Attribute) and _dotted(x):
            chains.add(_dotted(x))
    return call, names, chains


def _own_returns(fn):
    """The Return statements of one function, the ones of a function, lambda or class nested inside it excluded."""
    out, todo = [], list(ast.iter_child_nodes(fn))
    while todo:
        node = todo.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
            continue
        if isinstance(node, ast.Return):
            out.append(node)
        todo.extend(ast.iter_child_nodes(node))
    return out


@functools.lru_cache(maxsize=8)
def _response_reads(tree):
    """{name: frozenset of positions} for every function and method a module defines, read from its own return statements (the
    rulings at the merge of main's login cookie split, 2026-09-28): the index of each element of a returned tuple that reads a
    response (_reads_response), and "whole" where a returned value that is no tuple reads one. `return r.status, r.read(),
    r.headers` gives {1}; `return r.status, r.headers` gives the empty set. A returned Name is followed to its bindings inside the
    function (_name_bindings; the rulings on the census pass, 2026-09-28): `body = r.read(); return r.status, body, r.headers`
    gives {1}, through an alias or a `.decode(...)` too (`raw = r.read(); body = raw.decode()`), and a binding is an assignment, an
    annotated or augmented one, a walrus, or a tuple or list target paired by position with a value of the same length. A returned
    Name the follow cannot place, one the function binds to no expression of its own (an unpack of a call's answer, a synchronous
    for or a with target, an except name; an `async for` target is read the same way, unpinned) or to a Name so bound, and never to
    a read, gives "unknown", so a read behind it does not leave both censuses in silence: the call is a fetch (_fetched) and binds
    as a helper the module does not define does, every name (_bind). That holds only for such a Name returned BARE. A returned
    element that wraps one (`status, raw = _raw(path); return 200, raw.strip()`, `raw[3:]`), or a Name bound to such a wrapper,
    gives no position, so its call is no fetch and a read of the body behind it is in neither census unless a literal pin reds the
    floor through the textual census (a stated bound: x1 in test_d of
    test_a_returned_name_is_followed_to_its_binding_in_the_helper).
    A returned element that HOLDS a read the follow does not place gives "refused" (the rulings on the census bounds, 2026-09-28): a
    read call inside it under anything but a `.decode(...)` chain (`r.read().strip()`, `str(r.read(), "utf-8")`, `r.read() or b""`,
    `r.read() if ok else ""`), a Name bound to a read inside it (`raw[3:]`), or a Name or an attribute chain the function binds to
    an expression holding one (`body = r.read().strip()`, `self.body = r.read()`); a fetch of a page route through such a helper is
    an unclassified row in the reader census (readers_of), and the call binds only what the helper's placed returns give. A Name
    the function does not bind (a parameter, a global) is no read of the function's. Two definitions of one name (a helper per
    class) give the union of their positions. One walk of the
    module, each Return and each binding credited to the innermost function holding it, kept per tree (the parsed tree is
    _parse's, shared by rows_of, readers_of and _module_bindings for one module) and asked only when a call has a fetch's shape
    (_bind and _fetched take it as a callable): read four times for every module, it had added about 35 s to the population's
    derivation."""
    rets, binds, sets, todo = {}, {}, {}, [(tree, None)]
    while todo:
        node, fn = todo.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            fn = node
            rets[fn], binds[fn], sets[fn] = [], [], []
        elif isinstance(node, ast.ClassDef):
            fn = None   # a class body's statements are no function's; its methods are their own
        elif fn is not None and isinstance(node, ast.Return) and node.value is not None:
            rets[fn].append(node.value)
        elif fn is not None and isinstance(node, _BINDERS):
            binds[fn] += _name_bindings(node)
            sets[fn] += _attr_bindings(node)
        todo.extend((child, fn) for child in ast.iter_child_nodes(node))
    out = {}
    for fn, values in rets.items():
        read, unknown, changed = set(), set(), True
        while changed:   # a Name bound to a read, or to a Name so bound; one bound to no expression of its own, or to a Name so bound, and never to a read, is unknown
            changed = False
            for name, v in binds[fn]:
                if name not in read and v is not None and _reads_response(v, read):
                    read.add(name)
                    unknown.discard(name)
                    changed = True
                elif name not in read and name not in unknown and (v is None or _reads_response(v, unknown)):
                    unknown.add(name)
                    changed = True
        # a Name or an attribute chain bound to an expression HOLDING a read the follow does not place (a read call inside it, or a
        # Name or chain so bound), and never to a read itself; a returned element holding one refuses the helper's fetches (readers_of)
        held_names, held_chains = set(), set()
        holds = lambda h: h[0] or bool(h[1] & (read | held_names)) or bool(h[2] & held_chains)
        if values:   # read only for a function that returns something
            facts = [(held_names, name, _held(v)) for name, v in binds[fn] if v is not None and name not in read]
            facts += [(held_chains, chain, _held(v)) for chain, v in sets[fn]]
            changed = True
            while changed:
                changed = False
                for target, key, h in facts:
                    if key not in target and holds(h):
                        target.add(key)
                        changed = True
        at = out.setdefault(fn.name, set())
        placed = lambda e: "refused" if holds(_held(e)) else "unknown" if isinstance(e, ast.Name) and e.id in unknown else None
        for v in values:
            if isinstance(v, ast.Tuple) and any(isinstance(e, ast.Starred) for e in v.elts):
                at.add("unknown")   # the positions a starred element spreads over are not in the source
            elif isinstance(v, ast.Tuple):
                n = len(v.elts)
                at |= {p for i, e in enumerate(v.elts) for p in ((i, i - n) if _reads_response(e, read) else (placed(e),))} - {None}
            elif _reads_response(v, read):
                at.add("whole")
            elif placed(v):
                at.add(placed(v))
    return {name: frozenset(at) for name, at in out.items()}


def _callee(call):
    """The name a call to a Name or a self.<method> calls (`_serve_get(...)` gives `_serve_get`, `self._req(...)` gives `_req`);
    None for any other callee."""
    f = call.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id == "self":
        return f.attr
    return None


def _fetched(node, names, routes, reads=None):
    """The served text a fetched value stands for (the author's pass 8, 2026-09-20): a call to a Name or a self.<method> whose first argument
    is a string literal beginning with `/` that, without its ?query, is a route in `routes` (`_serve_get("/sw.js", ...)`,
    `self._get_text("/")`), or a concatenation led by such a literal holding the whole path (_fetch_path); a call to an attribute named `urlopen` whose first argument is a string literal, bare or `%`-formatted,
    naming such a route with the token in its query (_url_route; the fixer pass of the author's pass 8); or the `.read(...)` or `.decode(...)`
    of such a value or of a Name bound to one, through any chain of the two (`body.decode()`, `fetch("/chat").read().decode()`);
    else None. A bare Name is not followed (as _text does not). A call to a Name or a self.<method> the module defines counts as a
    fetch only where that callee returns a response it reads (`reads`, a callable giving the module's _response_reads, holds a position for it; the
    rulings at the merge of main's login cookie split, 2026-09-28): `_pathconf("/", "PC_PATH_MAX", 4096)`, a helper returning
    os.pathconf's answer, had read as a fetch of the landing and its caller's helper as an unclassified reader of the page. A callee
    the module does not define keeps the reading before the ruling (a fetch). A helper whose returned Name _response_reads cannot
    place ("unknown") is a fetch (the rulings on the census pass, 2026-09-28); one whose return holds a read the follow cannot place
    ("refused") is a fetch only where another of its returns places one, and readers_of refuses its fetches of a page route (the
    rulings on the census bounds, 2026-09-28). Bound: a helper the module defines that returns an
    unread response for its caller to read (`return urlopen(path)`) or reads it through another call in its return (`return
    r.status, self._body(r)`) is not a fetch here (none is in the suite), nor is one that returns a wrapper over a Name its follow
    cannot place (`status, raw = _raw(path); return 200, raw.strip()`; _response_reads), nor a subscript of a fetch call by a
    constant index (`self._req("/?token=x")[1]`, which is no call). Where such a call is assigned to names (`body =
    self._open("/").read()`) the textual census binds them (_FETCH_DEF), so a literal pin over one reds the floor; any other read
    of such a name (a regex, a split, a slice) is in neither census, in silence."""
    if not isinstance(node, ast.Call):
        return None
    f = node.func
    if isinstance(f, ast.Attribute) and f.attr in ("read", "decode"):
        inner = f.value
        return names.get(inner.id) if isinstance(inner, ast.Name) else _fetched(inner, names, routes, reads)
    if isinstance(f, ast.Attribute) and f.attr == "urlopen" and node.args:
        a = node.args[0]
        fmt = a.left if isinstance(a, ast.BinOp) and isinstance(a.op, ast.Mod) else a
        route = _url_route(fmt.value) if isinstance(fmt, ast.Constant) and isinstance(fmt.value, str) else None
        return _Served(routes[route]) if route and route in routes else None
    path = _fetch_path(node.args[0]) if node.args else None
    callee = _callee(node)
    if path and callee is not None:
        known = reads() if reads is not None else {}   # the module's helper returns, read on the first fetch-shaped call only
        if callee in known and not known[callee] - {"refused"}:
            return None   # the module's own helper, whose returns place no read: no fetch (readers_of refuses one holding a read it cannot place)
        route = path.split("?")[0]
        return _Served(routes[route]) if route in routes else None
    return None


def _fetch_path(node):
    """The literal url a fetch helper is handed: a string literal beginning with `/`, or a concatenation whose leftmost operand is
    such a literal holding the whole path, its `?` inside the literal (`"/?token=" + quote(tok)`; the merge of main's login cookie
    split, 2026-09-28, whose tests fetch the signed-in landing so, three sites the textual census read and the derivation did not);
    None otherwise. A concatenation whose literal ends before its `?` (`"/chat" + rest`) names no path whole and is no fetch here."""
    left = node
    while isinstance(left, ast.BinOp) and isinstance(left.op, ast.Add):
        left = left.left
    if not (isinstance(left, ast.Constant) and isinstance(left.value, str) and left.value.startswith("/")):
        return None
    return left.value if left is node or "?" in left.value else None


def _position_key(node):
    """(store, key) for a subscript of a Name or a self.<attr> by a constant index, the key _bind binds a fetched tuple's body
    position under (`resp[1]` gives ("names", "resp[1]"), `self.resp[-2]` gives ("attrs", "resp[-2]")); None for any other node."""
    if not isinstance(node, ast.Subscript):
        return None
    sl = node.slice
    if isinstance(sl, ast.UnaryOp) and isinstance(sl.op, ast.USub) and isinstance(sl.operand, ast.Constant) and type(sl.operand.value) is int:
        i = -sl.operand.value
    elif isinstance(sl, ast.Constant) and type(sl.value) is int:
        i = sl.value
    else:
        return None
    base = node.value
    if isinstance(base, ast.Name):
        return "names", "%s[%d]" % (base.id, i)
    if isinstance(base, ast.Attribute) and isinstance(base.value, ast.Name) and base.value.id == "self":
        return "attrs", "%s[%d]" % (base.attr, i)
    return None


def _tuple_names(names, attrs):
    """{(store, name): text} for every fetched tuple bound to ONE name (_bind: `resp = self._req("/")` binds `resp[1]` and `resp[-2]`,
    never `resp`), in a function's names (store "names") and in its class's self.<attr> bindings ("attrs"); a name also bound whole
    (to a text) is none, since it reads as that text."""
    out = {}
    for kind, store in (("names", names), ("attrs", attrs)):
        for key, text in store.items():
            base = key.split("[", 1)[0]
            if base != key and base not in store:
                out.setdefault((kind, base), text)
    return out


def _placed_tuple_uses(fn):
    """The ids of the nodes in a function where a name is read at a position _bind resolves for a fetched tuple: the value of a
    subscript by a constant index (_position_key: `resp[1]`, `resp[0]`), and the value of an assignment whose every target is a tuple
    holding no starred name (`status, body, headers = resp`)."""
    out = set()
    for node in ast.walk(fn):
        if isinstance(node, ast.Subscript) and _position_key(node):
            out.add(id(node.value))
        elif isinstance(node, ast.Assign) and all(isinstance(t, ast.Tuple) and not any(isinstance(e, ast.Starred) for e in t.elts) for t in node.targets):
            out.add(id(node.value))
    return out


def _resolve(node, names, attrs, getters, constants):
    """The served text a node stands for: a getter call or constant inline, a Name bound in the function, a self.<attr> bound in
    the class, a fetched tuple's body position by a constant index (`resp[1]`, _position_key); None otherwise."""
    t = _text(node, getters, constants)
    if not t and isinstance(node, ast.Name):
        t = names.get(node.id)
    if not t and isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "self":
        t = attrs.get(node.attr)
    if not t and isinstance(node, ast.Subscript):
        key = _position_key(node)
        t = (names if key[0] == "names" else attrs).get(key[1]) if key else None
    return t


def _bind(targets, value, names, attrs, getters, constants, sliced=None, routes=None, reads=None):
    """Record Name and self.<attr> targets bound to a served text, or to a slice of one; a tuple assignment binds by position; a
    FETCHED value (_fetched, with `routes`) unpacked into a tuple binds the positions its helper's own return statements read a
    response at (`reads`, a callable giving the module's _response_reads; the rulings at the merge of main's login cookie split,
    2026-09-28): `status, body, headers = self._req("/")` binds `body` alone where `_req` returns `r.status, r.read(), r.headers`,
    and a helper whose returns read no response binds no name. A target that is ONE name (or a self.<attr>) over such a tuple is
    no text: each position the helper reads a response at binds under the name's constant-index key, from both ends (`resp =
    self._req("/")` binds `resp[1]` and `resp[-2]`, which _resolve reads through _position_key), so the status and headers
    positions bind nothing here either; `body = resp[1]` binds `body`, and `status, body, headers = resp` binds by the same
    positions, a target holding a starred name none (the rulings on the census pass, 2026-09-28). Any other read of the name (an
    alias, a subscript by anything but a constant index, `resp[i]` or `resp[1:]`, a `for` over it, the starred unpack, the name
    handed whole to a call, a membership over the tuple) binds nothing, and readers_of refuses it, an unclassified row (the rulings
    on the census bounds, 2026-09-28). The binding is flow-insensitive: a name bound whole and then rebound to such a tuple loses
    the whole binding (its reads are refused the same way), and a name bound to such a tuple and then rebound whole reads as the
    whole text throughout (over-bound). A helper whose returns differ in length binds the union of their positions (`resp[-1]` is
    the body on a 2-tuple road and the headers on a 3-tuple one: over-bound). Before the merge's ruling every unpacked name
    bound, the status and the response headers too, and main's helpers returning (status, body, headers) put 19 reads of the
    headers (`.get`, `.get_all`, a base-class helper handed them) and of the status into the reader census as reads of the page. A
    helper the module does not define and a helper with a returned Name _response_reads cannot place ("unknown"; the rulings on
    the census pass, 2026-09-28) bind every name, the reading before the merge's ruling (the census cannot see which position is
    the body). A tuple target holding a starred name over a fetch (`first, *rest = self._req("/")`) reads no position, whatever
    the helper's returns show: each plain Name in it binds as the text, the status `first` too (over-bound), and the starred name
    binds nothing, so a read of the body inside it (`rest[0]`) is in neither census, in silence; the textual census reads no
    starred target either (a stated bound: p6 and p7 in test_a_fetched_tuple_binds_the_position_its_helper_reads_a_response_at).
    A subscript of the fetch call itself by a constant index (`page = self._req("/?token=x")[1]`) binds nothing (a stated bound:
    x2 and x3 in test_d of test_a_returned_name_is_followed_to_its_binding_in_the_helper). `sliced`, when given,
    tracks the Names bound through a slice, a fetched tuple's position or an unpack of one (forms the textual census does not read;
    the author's pass 8)."""
    if isinstance(value, ast.Tuple) and len(targets) == 1 and isinstance(targets[0], ast.Tuple) \
            and len(targets[0].elts) == len(value.elts):
        pairs = list(zip(targets[0].elts, value.elts))
    else:
        pairs = [(t, value) for t in targets]
    for t, v in pairs:
        g = _text(v, getters, constants)
        via_slice = fetched = False
        if not g and isinstance(v, ast.Subscript):
            # `body = resp[1]`, a fetched tuple's body position, the text itself; or `fn = html[a:b]`, a slice of a bound text, judged
            # over the whole text; the textual census reads neither
            g = _resolve(v, names, attrs, getters, constants) or _resolve(v.value, names, attrs, getters, constants)
            via_slice = True
        if not g and (isinstance(v, ast.Name) or isinstance(v, ast.Attribute) and isinstance(v.value, ast.Name) and v.value.id == "self"):
            # `js = html` or `js = self.html`, an ALIAS of a bound name (the fixer pass of the author's pass 9: two suite modules alias the page so
            # and neither census had followed it, so their position pins and a regex over the alias were outside both populations)
            g = _resolve(v, names, attrs, getters, constants)
            via_slice = isinstance(v, ast.Name) and sliced is not None and v.id in sliced
        if not g and routes:
            g = _fetched(v, names, routes, reads)
            fetched = bool(g)
        if not g and isinstance(t, ast.Tuple) and not any(isinstance(e, ast.Starred) for e in t.elts) \
                and (isinstance(v, ast.Name) or isinstance(v, ast.Attribute) and isinstance(v.value, ast.Name) and v.value.id == "self"):
            # `status, body, headers = resp`, a fetched tuple bound to one name (below) and unpacked after: by the positions bound; a
            # target holding a starred name binds none (readers_of refuses it); the textual census reads neither
            store, base, n = (names, v.id, len(t.elts)) if isinstance(v, ast.Name) else (attrs, v.attr, len(t.elts))
            for i, e in enumerate(t.elts):
                got = store.get("%s[%d]" % (base, i)) or store.get("%s[%d]" % (base, i - n))
                if got and isinstance(e, ast.Name):
                    names[e.id] = got
                    if sliced is not None:
                        sliced.add(e.id)
        if not g:
            continue
        if isinstance(t, (ast.Name, ast.Attribute)) and fetched and reads is not None and _callee(v) is not None:
            # `resp = self._req("/")` over a helper that returns a tuple: the name is no text, and each position the helper reads a
            # response at is, by a constant index (`resp[1]`, and `resp[-2]` for a 3-tuple; _position_key), the reading the tuple
            # branch below gives an unpacked target
            at = (reads().get(_callee(v)) or frozenset()) - {"refused"}   # a refused return binds nothing (readers_of refuses the call)
            if at and not at & {"whole", "unknown"} and (isinstance(t, ast.Name) or isinstance(t.value, ast.Name) and t.value.id == "self"):
                store, base = (names, t.id) if isinstance(t, ast.Name) else (attrs, t.attr)
                store.pop(base, None)
                for i in at:
                    store["%s[%d]" % (base, i)] = g
                continue
        if isinstance(t, ast.Name):
            names[t.id] = g
            if sliced is not None:
                (sliced.add if via_slice else sliced.discard)(t.id)
        elif isinstance(t, ast.Tuple) and fetched:   # `status, body = fetch("/x")`: the positions the helper reads a response at
            callee = _callee(v)
            at = reads().get(callee) if reads is not None and callee is not None and not any(isinstance(e, ast.Starred) for e in t.elts) else None
            if at is not None and "unknown" in at:
                at = None   # a returned Name the follow cannot place (_response_reads): every name, as for a helper the module does not define
            for i, e in enumerate(t.elts):
                if isinstance(e, ast.Name) and (at is None or i in at):
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
    """[(line, literal, text, form, readable, served)] for every membership or position assertion of a literal over a served text in one
    test module; form is "in" for a membership, else the position method; readable is whether the row's form is one the textual
    census reads (the author's pass 8, 2026-09-20): the literal's source segment is a plain literal or a run of them (re.fullmatch over _LIT:
    no backslash, not triple-quoted, not a loop or comprehension variable) and the container is not a name bound to a slice, a
    subscript (`resp[1]`) or a name bound to or unpacked from a fetched tuple's position; served
    is whether the text is a FETCHED body (_fetched), judged as Handler._send serves it (judged_texts; the rulings at the merge of
    main's login cookie split, 2026-09-28)."""
    tree, lines = _parsed(path)
    plain = lambda node: isinstance(node, ast.Constant) and bool(re.fullmatch(_LIT, _segment(lines, node) or ""))
    out = []
    functions = (ast.FunctionDef, ast.AsyncFunctionDef)
    groups = [[n for n in cls.body if isinstance(n, functions)] for cls in ast.walk(tree) if isinstance(cls, ast.ClassDef)]
    groups.append([n for n in tree.body if isinstance(n, functions)])   # module-level test functions (the author's pass 6, 2026-09-20)
    reads = functools.partial(_response_reads, tree)   # the positions each helper of the module reads a response at (_bind), read on demand
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
                _bind(targets, value, {}, attrs, getters, constants, None, routes, reads)
        for fn in fns:
            names, sliced = dict(modnames), set()
            for targets, value in bindings(fn):   # an assignment, or a with-item's `as` target (`with urlopen(...) as r`; the fixer pass of the author's pass 8)
                _bind(targets, value, names, attrs, getters, constants, sliced, routes, reads)
            text_of = lambda x: _resolve(x, names, attrs, getters, constants)
            readable = lambda lit, x: plain(lit) and not (isinstance(x, ast.Name) and x.id in sliced) and not isinstance(x, ast.Subscript)
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
            out += [(line, lit, str(g), form, readable, isinstance(g, _Served)) for line, _, _, lit, g, form, readable in sorted(rows)]
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
    names, reads = {}, functools.partial(_response_reads, tree)
    for st in tree.body:
        if isinstance(st, ast.Assign):
            _bind(st.targets, st.value, names, {}, getters, constants, None, routes, reads)
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
    reads = functools.partial(_response_reads, tree)   # the positions each helper of the module reads a response at (_bind), read on demand
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
        if _position_key(x) and _resolve(x, names, attrs, getters, constants):
            return None   # a fetched tuple's body position (`resp[1]`): the text itself
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
            if base and not (routes and _fetched(value, names, routes, reads)):
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
            _bind(targets, value, names, attrs, getters, constants, None, routes, reads)
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
                # the rulings on the census bounds (2026-09-28): a fetch of a page route through a helper of the module whose return holds
                # a read the follow cannot place ("refused", _response_reads) is refused here, an unclassified row at the call; the call
                # binds only what the helper's placed returns give, so the reads of its answer would otherwise be in neither census
                path = _fetch_path(node.args[0]) if routes and node.args and _callee(node) is not None else None
                if path and path.split("?")[0] in routes and "refused" in reads().get(_callee(node), ()):
                    rows.append((node.lineno, "unclassified", routes[path.split("?")[0]],
                                 "refused fetch, %s returns a read the follow cannot place: %s" % (_callee(node), seg(node))))
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
        # the rulings on the census bounds (2026-09-28): a fetched tuple bound to one name is read by a constant index or an unpack by
        # the positions (_bind), and ANY other read of the name is refused, an unclassified row over the text its body position holds:
        # an alias, a subscript by a Name or a slice, a for over it, a starred unpack, the name handed whole to a helper or any call, a
        # membership over the tuple, and the reads of a name bound whole and later rebound to such a tuple (the walk is
        # flow-insensitive, so the rebinding hides the whole binding). Each had left both censuses in silence.
        tuples = _tuple_names(names, attrs)
        if tuples:
            placed = _placed_tuple_uses(fn)
            for node in ast.walk(fn):
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                    key, spelled = ("names", node.id), node.id
                elif isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Load) and isinstance(node.value, ast.Name) and node.value.id == "self":
                    key, spelled = ("attrs", node.attr), "self." + node.attr
                else:
                    continue
                if key in tuples and id(node) not in placed:
                    rows.append((node.lineno, "unclassified", tuples[key], "fetched tuple %s: %s" % (spelled, lines[node.lineno - 1].strip()[:160])))
        return rows

    out = []
    for fns in groups:
        attrs, methods = {}, {n.name: n for n in fns}
        for fn in fns:
            for targets, value in bindings(fn):
                _bind(targets, value, {}, attrs, getters, constants, None, routes, reads)
        for fn in fns:
            out += walk(fn, dict(modnames), attrs, 0, dict(modderived), methods)
    return sorted({(line, form, str(text), source) for line, form, text, source in out})


def inline_sites(path, getters, constants):
    """The textual census's sites alone (textual_census)."""
    return textual_census(path, getters, constants)[0]


def _spans(kinds, text):
    return sorted({sp for k in kinds for sp in _SCANNER[k](text)})


@functools.lru_cache(maxsize=None)
def _getter_constant_returns():
    """{getter: (str, ...)}: for each derived getter defined at the kernel's top level, the string constants its own return statements
    return, in source order, read from one parse of the kernel source whose tree is dropped after (a tree of the whole kernel held for
    the process made the collector's passes over it cost the population's derivation about 25 s)."""
    getters, out = set(page_getters()), {}
    for fn in ast.parse(_kernel_source()).body:
        if isinstance(fn, ast.FunctionDef) and fn.name in getters:
            out[fn.name] = tuple(r.value.value for r in sorted(_own_returns(fn), key=lambda r: (r.lineno, r.col_offset))
                                 if isinstance(r.value, ast.Constant) and isinstance(r.value.value, str))
    return out


@functools.lru_cache(maxsize=None)
def getter_renders(getter):
    """The texts a served-text getter returns (the rulings at the merge of main's login cookie split, 2026-09-28): its render in the
    hermetic state (pages()) and every string constant one of its own return statements returns, in source order (the page a state
    the hermetic render does not meet serves: `_files_page` returns a one-line page naming the ui/ modules when its sheet cannot be
    read, and two tests pin that text inside a patch of the read). Derived from the getter's definition in the kernel source, which
    the getter rule reads at the module's top level, so a getter with no such definition fails here."""
    consts = _getter_constant_returns()
    assert getter in consts, "a derived getter with no definition at the kernel's top level: %s" % getter
    return (pages()[getter],) + tuple(c for c in consts[getter] if c != pages()[getter])


# the type the kernel's GET dispatch serves each kind of getter under (the route table's pages as text/html, the service worker as
# text/javascript): Handler._send puts its page-key script into a text/html document's head alone
_SERVED_CTYPE = {"markup": "text/html; charset=utf-8", "script": "text/javascript; charset=utf-8", "style": "text/css; charset=utf-8"}
# the session id the stand-in sign-in carries (synthetic: _send derives the page key the seed stores from it and the serve token)
_SERVED_SESSION = "11111111-2222-3333-4444-555555555555"


@functools.lru_cache(maxsize=None)
def served_body(text, kind):
    """The body the kernel's Handler._send writes for `text` served as a getter of `kind` on a sign-in response (the rulings at the
    merge of main's login cookie split, 2026-09-28: since that change a fetched page is no longer its getter's text). _send itself runs,
    on a stand-in request that holds an authorized page (`_page_ok`) and the session the response signs in (`_set_cookie`), and its
    written bytes are the body: for a page document the sign-in seed and then _PAGE_KEY_JS go first in the head, in the order _send
    assembles them; a text with no `<head>`, or served as another type, is written as it stands. A fetch on the cookie alone gets the
    key script without the seed; the sign-in form is the wider one, and every fetched row is judged against it."""
    written = []

    class _Request:
        _page_ok, _set_cookie = True, _SERVED_SESSION
        wfile = type("W", (), {"write": staticmethod(written.append)})

        def send_response(self, code):
            pass

        def send_header(self, name, value):
            pass

        def end_headers(self):
            pass

    km.Handler._send(_Request(), 200, text, _SERVED_CTYPE[kind])
    assert len(written) == 1, "Handler._send wrote %d bodies" % len(written)
    return written[0].decode("utf-8")


class _Served(str):
    """A getter's name standing for the body a FETCH of its route returns (_fetched), which a row is judged against as served
    (served_body), not as the getter's render; compares and hashes as the name, so every other reader of a binding reads the name."""
    __slots__ = ()


@functools.lru_cache(maxsize=None)
def judged_texts(name, served=False):
    """((text, comment spans), ...): every text a row over the served text `name` is judged against. A constant: its value, the
    scanner of each kind it lands in. A getter: each text it returns (getter_renders), scanned as its kind, and for a row over a
    FETCHED body (`served`) each of those as Handler._send serves it (served_body)."""
    if name in page_getters():
        kinds = frozenset([getter_kind(name)])
        texts = getter_renders(name)
        if served:
            texts = tuple(served_body(t, getter_kind(name)) for t in texts)
    else:
        kinds, texts = served_constants()[name], (getattr(km, name),)
    return tuple((t, tuple(_spans(kinds, t))) for t in texts)


def judge_rows(rows):
    """(flagged, zero) for rows (module, line, literal, text, form, readable, served): `flagged` every row a comment can satisfy in a
    text it is judged against (judged_texts; a membership or a count when any occurrence sits in a comment, an index or find row when
    the first does, an rindex or rfind row when the last does), `zero` every row whose literal occurs in NONE of its texts. A zero-hit
    row proves nothing, since a comment spelling its literal cannot satisfy what the text does not carry anywhere (the rulings at the
    merge of main's login cookie split, 2026-09-28: it had passed in silence, and one of them was a fetched row whose literal is in the
    page-key script alone, sound only while that script carried no comment); it is judged against the wrong text, or its literal is
    wrong, and fails."""
    flagged, zero, getters = [], [], set(page_getters())
    for fname, line, lit, name, form, _, served in rows:
        total, marks = 0, []
        for text, comments in judged_texts(name, served):
            hits = [m.start() for m in re.finditer(re.escape(lit), text)]
            inside = [h for h in hits if any(s <= h < e for s, e in comments)]
            total += len(hits)
            if form in ("index", "find"):
                hit = bool(hits) and hits[0] in inside      # the pin reads the first occurrence
            elif form in ("rindex", "rfind"):
                hit = bool(hits) and hits[-1] in inside     # the last
            else:
                hit = bool(inside)                          # a membership or a count: any occurrence
            if hit:
                marks.append((len(inside), len(hits)))
        label = "%s:%d %r %s %s%s" % (fname, line, lit, form, name, ("()" + (" fetched" if served else "")) if name in getters else "")
        if marks:
            inside_n, hits_n = map(sum, zip(*marks))
            flagged.append("%s: %d of %d occurrences inside a comment%s" % (label, inside_n, hits_n, " (prose only)" if inside_n == hits_n else ""))
        if not total:
            zero.append("%s: 0 occurrences in %d text(s)" % (label, len(judged_texts(name, served))))
    return flagged, zero


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
        # the fetched-route map, derived from the handler by the walk: the landing (through the route table since the merge of main's
        # login cookie split, through the membership form before it) and an equality route both read
        self.assertEqual((routes.get("/"), routes.get("")), ("_landing", "_landing"), "the landing's routes: %r" % (routes,))
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
            rows += [(fname,) + tuple(row) for row in derived]   # (module, line, literal, text, form, readable, served)
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
        # each row is judged against every text it can read (judged_texts: a getter's returns, a fetched page as Handler._send
        # serves it), and a row whose literal occurs in none of them fails (the rulings at the merge of main's login cookie split)
        self.assertTrue([r for r in rows if r[6]] and [r for r in rows if not r[6]], "rows over fetched bodies and over renders both derived")
        bad, zero = judge_rows(rows)
        self.assertEqual(bad, [], "a pin a served comment can satisfy; read the parsed rule, the code with its comments removed or the element instead:\n" + "\n".join(bad))
        self.assertEqual(zero, [], "a row whose literal occurs in no text it is judged against, a verdict that proves nothing: judge it against the text "
                         "the test reads, or correct its literal:\n" + "\n".join(zero))

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
        # or self.<attr> (alias, al2), each a row and a site. The merge of main's login cookie split (2026-09-28): a fetch by a
        # concatenation led by the whole path (f10) is a row and a site, and one led by a name (f12) binds nothing. The module is built over EVERY derived
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
        st, fb, _ = self._get("/?token=" + tok, {})
        self.assertIn("f10", fb)
        pb = self._get(prefix + "/chat?token=x")
        self.assertIn("f12", pb)
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
                    (58, "m1", "_feed_page", "in"), (60, "m2", "_feed_page", "in"), (62, "m3", "_landing", "in"),   # a module-level binding and two aliases (the fixer pass of the author's pass 9)
                    (64, "f10", "_landing", "in")]   # a fetch by a concatenation led by the whole path (the merge of main's login cookie split)
        expected += [(L + 1, "a1", g, "in") for g in getters] + [(L + 2, "a2", g, "index") for g in getters]
        expected += [(L + 5, "a4", "_feed_page", "index"), (L + 5, "a5", "_feed_page", "index"), (L + 6, "a6", "_feed_page", "index"), (L + 6, "a7", "_feed_page", "index"),
                     (L + 7, "a8", css, "in"), (L + 8, "a9", html, "in"), (L + 10, "b1", script, "in"), (L + 11, "b2", mark, "in"), (L + 12, "b4b5", "_feed_page", "in"),
                     (L + 19, "x1", "_landing", "in"), (L + 19, "x2", "_landing", "in"), (L + 20, "x3", "_landing", "in")]
        self.assertEqual([r[:4] for r in rows], expected)
        self.assertNotIn(("a3", "in"), {(r[1], r[3]) for r in rows}, "the loop variable is bound to the loop's body only")
        self.assertNotIn(("b3", "in"), {(r[1], r[3]) for r in rows}, "a loop whose iterable mixes a text with something else binds nothing")
        # a row over a fetched body is marked served, judged as Handler._send serves the page (judged_texts); every other row is not
        self.assertEqual({(r[0], r[1]) for r in rows if r[5]}, {(38, "f1"), (40, "f2"), (42, "f3"), (51, "f7"), (64, "f10")})
        # the author's pass 8 (2026-09-20): a fetch of an unmapped path, a body passed through served_css.js_code, and a method call on another
        # object with a route-shaped literal (path.split("/")) bind nothing; the fixer pass: nor a formatted url of a page route with
        # no token in its query (the gate's paste-the-token page, f8), nor one of a path the dispatch does not map (f9)
        self.assertEqual({r[1] for r in rows} & {"f4", "f5", "f6", "f8", "f9", "f12"}, set())
        # the merge of main's login cookie split (2026-09-28): a concatenation is a fetch of its path only where its leading literal
        # holds the whole path, its `?` inside the literal; a literal that ends before its `?` names no path whole, and a
        # concatenation led by a name (f12 above) is no fetch
        url = lambda text: _fetch_path(ast.parse(text, mode="eval").body)
        self.assertEqual((url('"/?token=" + tok'), url('"/chat?token=" + tok + "&x=1"'), url('"/sw.js"')), ("/?token=", "/chat?token=", "/sw.js"))
        self.assertEqual((url('"/chat" + rest'), url('prefix + "/chat?token=x"'), url('"chat?token=" + tok'), url('"/?token=%s" % tok')), (None, None, None, None))
        # the author's pass 8 (2026-09-20): the rows the textual census declines, by form: a loop or comprehension literal (p, q, r, a4 to a7),
        # a name bound to a slice (h), a literal with a backslash and a triple-quoted one; every other row is readable
        declined = {(15, "p"), (15, "q"), (17, "r"), (28, "h"), (L + 5, "a4"), (L + 5, "a5"), (L + 6, "a6"), (L + 6, "a7"), (34, "y\tz"), (35, "tq")}
        self.assertEqual({(r[0], r[1]) for r in rows if not r[4]}, declined)
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
                          (58, "m1", "_feed_page", "in"), (60, "m2", "_feed_page", "in"), (62, "m3", "_landing", "in"), (64, "f10", "_landing", "in")]
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
            pins |= {(fname, row[0], row[2]) for row in derived if row[3] in _POSITION}
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
        # test_token_login_page.py joined the road at the merge of main's login cookie split (the rulings, 2026-09-28): its own
        # HTMLParser over the login page was the parser beside served_css this census exists to refuse
        self.assertTrue(sum(road.values()) >= 15 and all(road[f] for f in ("test_kernel_mobile.py", "test_shell_viewport_fit.py", "test_spend_detail.py",
                                                                            "test_token_login_page.py")), road)
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
        # sits under (the reader's own stack: it can over-report an ancestor, and it loses one where HTML ignores an end tag whose
        # element is not in scope, served_css's disclosed error) and the pages carrying each
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

    def test_a_fetched_tuple_binds_the_position_its_helper_reads_a_response_at(self):
        # the rulings at the merge of main's login cookie split (2026-09-28), P1: main's fetch helpers return (status, body,
        # headers), and the census had bound every name a fetch is unpacked into, so 19 reads of a status or of the response
        # headers (`headers.get_all("Set-Cookie")`, `assertEqual(status, 200)`) were reads of the page, unclassified ones red. A
        # synthetic module pins the rule: the position the helper's own returns read a response at binds (`r.read()` in a method,
        # `h.wfile.getvalue().decode(...)` in a module function), the status and headers positions do not, a helper whose returns
        # read no response binds no name (p3), and a helper the module does not define binds every name, the reading before the
        # ruling (p5). A target holding a starred name binds each plain name in it whatever its position, the status too (p6), and
        # its starred name not at all, so the body inside it is in neither census (p7, a stated bound). The rows of both
        # derivations are named, never inferred.
        getters, constants, routes = page_getters(), served_constants(), route_getters()
        src = '''import unittest
def _serve(path):
    return captured.get("status"), h.wfile.getvalue().decode("utf-8"), captured.get("headers", {})
def _heads(path, headers=None):
    return r.status, r.headers
class T(unittest.TestCase):
    def _req(self, path):
        try:
            return r.status, r.read(), r.headers
        except E as e:
            return e.code, e.read(), e.headers
    def test_a(self):
        status, body, headers = self._req("/?token=x")
        self.assertEqual(status, 200)
        headers.get_all("Set-Cookie")
        self.assertIn("p1", body)
        st, page, hd = _serve("/")
        self.assertIn("p2", page)
        hd.get("Content-Type")
        code, heads = _heads("/")
        self.assertIn("p3", heads)
        s2, b2 = elsewhere("/sw.js")
        self.assertIn("p4", b2)
        self.assertIn("p5", s2)
        first, *rest = self._req("/")
        self.assertIn("p6", first)
        self.assertIn("p7", rest[0])
'''
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write(src)
        try:
            rows = rows_of(f.name, getters, constants, routes)
            readers = readers_of(f.name, getters, constants, routes)
        finally:
            os.unlink(f.name)
        self.assertEqual([r[:4] for r in rows], [(16, "p1", "_landing", "in"), (18, "p2", "_landing", "in"), (23, "p4", "_sw_js", "in"),
                                                 (24, "p5", "_sw_js", "in"), (26, "p6", "_landing", "in")])
        self.assertEqual([r[:3] for r in readers], [(16, "assert", "_landing"), (18, "assert", "_landing"), (23, "assert", "_sw_js"),
                                                    (24, "assert", "_sw_js"), (26, "assert", "_landing")],
                         "no read of a status or of the response headers is a read of the page")
        self.assertEqual({k: sorted(v, key=str) for k, v in _response_reads(ast.parse(src)).items()},
                         {"_serve": [-2, 1], "_heads": [], "_req": [-2, 1], "test_a": []})

    def test_a_fetched_tuple_bound_to_one_name_binds_its_body_position(self):
        # the rulings on the census pass (2026-09-28), P1's position rule for a target that is one name: `resp = self._req("/")`
        # over a helper returning (status, body, headers) had bound the whole tuple as the page, so `resp[0]` and `resp[2]` read
        # as slices of it and `resp[2].get("Set-Cookie")` as an unclassified read, the class P1 removed for unpacked targets. The
        # name is no text now, and each position the helper reads a response at is, by a constant index from either end (`resp[1]`,
        # `resp[-2]`), bound to a name (`body = resp[1]`) or unpacked after (`status, page, heads = resp`), in a method and in a
        # setUp's self.<attr> alike; the status and headers positions are none. A helper whose return is no tuple binds the name
        # whole, and so does a helper the module does not define. A returned tuple with a starred element has positions the source
        # does not show, so it gives "unknown" and its call binds every name (_spread). The textual census reads no subscript and no
        # unpack of a name, so those rows are declined forms. The rows of both derivations are named, never inferred.
        getters, constants, routes = page_getters(), served_constants(), route_getters()
        src = '''import re, unittest
def _text(path):
    return urlopen(path).read()
class T(unittest.TestCase):
    def setUp(self):
        self.resp = self._req("/chat?token=x")
    def _req(self, path):
        return r.status, r.read(), r.headers
    def test_a(self):
        resp = self._req("/?token=x")
        self.assertEqual(resp[0], 200)
        resp[2].get("Set-Cookie")
        self.assertIn("c1", resp[1])
        self.assertIn("c2", resp)
        re.search("c3", resp[-2])
        body = resp[1]
        self.assertIn("c4", body)
        status, page, heads = resp
        self.assertIn("c5", page)
        heads.get_all("Set-Cookie")
        self.assertIn("c6", self.resp[1])
        self.assertEqual(self.resp[0], 200)
        whole = _text("/sw.js")
        self.assertIn("c7", whole)
        other = elsewhere("/?token=x")
        self.assertIn("c8", other)
        sp1, sp2 = _spread("/sw.js")
        self.assertIn("c9", sp1)
        r2 = resp
        re.search("c10", r2[1])
        k = 1
        re.search("c11", resp[k])
        tail = resp[1:]
        for part in resp:
            part.split("<")
        first, *rest = resp
        self.assertIn("c12", rest[0])
        self.assertEqual(first, 200)
        self._check(resp)
        self.assertIn("c13", self.resp)
    def _check(self, got):
        re.search("c14", got[1])
    def test_b(self):
        resp = _text("/sw.js")
        re.search("c15", resp)
        resp = self._req("/?token=x")
        self.assertIn("c16", resp[1])
    def test_c(self):
        resp = self._req("/?token=x")
        self.assertIn("c17", resp[1])
        resp = _text("/sw.js")
        re.search("c18", resp)
def _spread(path):
    return (r.status, *extra, r.read())
'''
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write(src)
        try:
            rows = rows_of(f.name, getters, constants, routes)
            readers = readers_of(f.name, getters, constants, routes)
        finally:
            os.unlink(f.name)
        self.assertEqual([r[:5] for r in rows], [(13, "c1", "_landing", "in", False), (17, "c4", "_landing", "in", False), (19, "c5", "_landing", "in", False),
                                                 (21, "c6", "_chat_page", "in", False), (24, "c7", "_sw_js", "in", True), (26, "c8", "_landing", "in", True),
                                                 (28, "c9", "_sw_js", "in", True), (47, "c16", "_landing", "in", False), (50, "c17", "_landing", "in", False)])
        # the rulings on the census bounds (2026-09-28): every other read of the tuple's name is REFUSED, an unclassified row the
        # reader census fails on, where it had left both censuses in silence: the membership over the tuple itself (14), an alias
        # (29, whose subscript c10 then binds nothing), a subscript by a Name (32) and a slice (33), a for over the tuple (34), a
        # starred unpack (36, which binds no name, so neither the status nor the starred list is read as the page), the name handed
        # whole to a method (39, whose read c14 binds nothing), a setUp's tuple attribute read whole (40), and a name bound whole
        # and then rebound to such a tuple (45: the walk is flow-insensitive, so the whole binding is gone and the read before the
        # rebinding is refused rather than lost). The reverse order is the stated over-binding, not a refusal: a name bound to such
        # a tuple and then rebound whole (test_c) reads as the whole text throughout, `resp[1]` a slice of it too (50, 52)
        refused = [(14, "_landing"), (29, "_landing"), (32, "_landing"), (33, "_landing"), (34, "_landing"), (36, "_landing"), (39, "_landing"),
                   (40, "_chat_page"), (45, "_landing")]
        self.assertEqual([r[:3] for r in readers], sorted([(13, "assert", "_landing"), (15, "regex", "_landing"), (17, "assert", "_landing"), (19, "assert", "_landing"),
                                                           (21, "assert", "_chat_page"), (24, "assert", "_sw_js"), (26, "assert", "_landing"), (28, "assert", "_sw_js"),
                                                           (47, "assert", "_landing"), (50, "assert", "_landing"), (50, "slice", "_sw_js"), (52, "regex", "_sw_js")]
                                                          + [(line, "unclassified", text) for line, text in refused]),
                         "a body position read as the text itself, no read of a status or of the response headers a read of the page, and "
                         "every other read of the tuple refused")
        self.assertEqual({r[3].split(":")[0] for r in readers if r[1] == "unclassified"}, {"fetched tuple resp", "fetched tuple self.resp"})
        self.assertEqual({k: sorted(v, key=str) for k, v in _response_reads(ast.parse(src)).items()},
                         {"_text": ["whole"], "setUp": [], "_req": [-2, 1], "test_a": [], "_check": [], "test_b": [], "test_c": [], "_spread": ["unknown"]})

    def test_a_returned_name_is_followed_to_its_binding_in_the_helper(self):
        # the rulings on the census pass (2026-09-28): a helper whose return holds a Name bound to the read (`body = r.read();
        # return r.status, body, r.headers`) gave no position, so by P2 its call was no fetch and every read of the body left both
        # censuses, a literal pin to the floor's red and a regex or a split in silence. _response_reads follows a returned Name to
        # its bindings inside the helper, through a `.decode(...)` and an alias (_named, _aliased): the body position binds, the
        # status and headers do not. A returned Name the follow cannot place, bound only to no expression of its own (an unpack of
        # a call's answer, _opaque), makes the call a fetch that binds every name, as a helper the module does not define does, so
        # the read behind it stays in both censuses. A parameter returned is no read of the helper's (_echo), and its call stays no
        # fetch. test_b holds the other forms the follow claims (the rulings on the census bounds, 2026-09-28: each was unpinned):
        # a for target, a with target and an except name returned are unknown (_forv, _withv, _exc); an augmented assignment, a
        # walrus and an annotated assignment bind their Name to the read (_aug, _walrus, _ann); a tuple or list target over a tuple
        # or list of the same length pairs by position, so the read binds and the status does not (_tuplepair, _listpair: d9 and
        # d11 are no rows); a Name bound to an unknown Name is unknown (_opaque2); a nested def's bindings are its own, so a
        # helper whose inner def binds `body = r.read()` while its own `body` is not a read is no fetch (_outer2: d13 is no row);
        # and two definitions of one name, a helper per class, give the union of their positions (_two: both names bind). test_d
        # holds two stated bounds (the check on the census bounds found them silent; the module docstring lists them): a
        # wrapper over a Name the follow cannot place gives no position, so _opaque3's call is no fetch and x1 is in neither census,
        # and a subscript of a fetch call by a constant index binds nothing, assigned (x2) or read inline (x3). The rows of both
        # derivations are named, never inferred.
        getters, constants, routes = page_getters(), served_constants(), route_getters()
        src = '''import re, unittest
def _named(path):
    with urlopen(path) as r:
        body = r.read().decode()
        return r.status, body, r.headers
def _aliased(path):
    raw = r.read()
    text = raw.decode()
    return r.status, text
def _opaque(path):
    status, body = _raw(path)
    return status, body, {}
def _echo(path, default):
    return default
class T(unittest.TestCase):
    def test_a(self):
        n1, n2, n3 = _named("/")
        self.assertIn("n1", n2)
        re.search("n2", n2)
        n3.get("Set-Cookie")
        self.assertEqual(n1, 200)
        a1, a2 = _aliased("/chat?token=x")
        self.assertIn("n3", a2)
        o1, o2, o3 = _opaque("/")
        self.assertIn("n4", o2)
        self.assertIn("n5", o3)
        e = _echo("/", "x")
        self.assertIn("n6", e)
    def test_b(self):
        f1, f2 = _forv("/")
        self.assertIn("d1", f2)
        w1, w2 = _withv("/")
        self.assertIn("d2", w2)
        x1, x2 = _exc("/")
        self.assertIn("d3", x2)
        g1, g2 = _aug("/")
        self.assertIn("d4", g2)
        self.assertIn("d5", g1)
        k1, k2 = _walrus("/")
        self.assertIn("d6", k2)
        h1, h2 = _ann("/")
        self.assertIn("d7", h2)
        t1, t2 = _tuplepair("/")
        self.assertIn("d8", t2)
        self.assertIn("d9", t1)
        l1, l2 = _listpair("/")
        self.assertIn("d10", l2)
        self.assertIn("d11", l1)
        u1, u2 = _opaque2("/")
        self.assertIn("d12", u2)
        v1, v2 = _outer2("/")
        self.assertIn("d13", v2)
        s1, s2 = self._two("/")
        self.assertIn("d14", s1)
        self.assertIn("d15", s2)
    def _two(self, path):
        return r.status, r.read()
    def test_c(self):
        w1, w2 = _strip("/")
        re.search("w1", w2)
        s1, s2 = _str("/")
        re.search("w2", s2)
        o1, o2 = _or("/")
        re.search("w3", o2)
        i1, i2 = _ifexp("/")
        re.search("w4", i2)
        c1, c2 = _cut("/")
        re.search("w5", c2)
        k1, k2 = self._kept("/chat?token=x")
        re.search("w6", k2)
        whole = _whole("/sw.js")
        re.search("w7", whole)
        m1, m2 = _mixed("/")
        self.assertIn("w8", m2)
        mm = _mixed("/")
        self.assertIn("w9", mm[1])
        j = _json("/api/state")
        re.search("w10", j)
        p1, p2 = _gv("/")
        re.search("w11", p2)
        t1, t2 = self._attr_tuple("/")
        re.search("w12", t2)
        a1, a2 = self._attr_ann("/")
        re.search("w13", a2)
        u1, u2 = self._attr_aug("/")
        re.search("w14", u2)
        e1, e2 = self._deep("/")
        re.search("w15", e2)
        v1, v2 = self._via_name("/")
        re.search("w16", v2)
        l1, l2 = self._attr_list("/")
        re.search("w17", l2)
    def test_d(self):
        q1, q2 = _opaque3("/")
        re.search("x1", q2)
        page = _named("/")[1]
        re.search("x2", page)
        re.search("x3", _named("/")[1])
    def _kept(self, path):
        self.body = urlopen(path).read()
        return 200, self.body
    def _attr_tuple(self, path):
        self.status, self.body = 200, urlopen(path).read()
        return 200, self.body
    def _attr_list(self, path):
        [self.status, self.body] = [200, urlopen(path).read()]
        return 200, self.body
    def _attr_ann(self, path):
        self.body: bytes = urlopen(path).read()
        return 200, self.body
    def _attr_aug(self, path):
        self.body = b""
        self.body += urlopen(path).read()
        return 200, self.body
    def _deep(self, path):
        self.cache.body = urlopen(path).read()
        return 200, self.cache.body
    def _via_name(self, path):
        raw = urlopen(path).read()
        self.body = raw.strip()
        return 200, self.body
class U(unittest.TestCase):
    def _two(self, path):
        return r.read(), r.status
def _strip(path):
    body = urlopen(path).read().decode().strip()
    return 200, body
def _str(path):
    return 200, str(urlopen(path).read(), "utf-8")
def _or(path):
    body = urlopen(path).read() or b""
    return 200, body
def _ifexp(path, ok=True):
    body = urlopen(path).read() if ok else ""
    return 200, body
def _cut(path):
    raw = urlopen(path).read()
    return 200, raw[3:]
def _whole(path):
    return urlopen(path).read().strip()
def _mixed(path, strip=False):
    if strip:
        return 200, urlopen(path).read().strip()
    return 200, urlopen(path).read()
def _json(path):
    return json.loads(urlopen(path).read())
def _gv(path):
    return 200, h.wfile.getvalue().decode().strip()
def _forv(path):
    for body in fetch_all(path):
        pass
    return 200, body
def _withv(path):
    with fetch(path) as body:
        return 200, body
def _exc(path):
    try:
        raise Failed(path)
    except Failed as body:
        return 200, body
def _aug(path):
    body = ""
    body += urlopen(path).read().decode()
    return 200, body
def _walrus(path):
    if (body := urlopen(path).read()):
        return 200, body
def _ann(path):
    body: bytes = urlopen(path).read()
    return 200, body
def _tuplepair(path):
    status, body = 200, urlopen(path).read()
    return status, body
def _listpair(path):
    [status, body] = [200, urlopen(path).read()]
    return status, body
def _opaque2(path):
    status, body = _raw(path)
    text = body
    return 200, text
def _opaque3(path):
    status, raw = _raw(path)
    return 200, raw.strip()
def _outer2(path):
    def inner(r):
        body = r.read()
        return body
    body = fetch_meta(path)
    return 200, body
'''
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write(src)
        try:
            rows = rows_of(f.name, getters, constants, routes)
            readers = readers_of(f.name, getters, constants, routes)
        finally:
            os.unlink(f.name)
        pinned = [(31, "d1"), (33, "d2"), (35, "d3"), (37, "d4"), (40, "d6"), (42, "d7"), (44, "d8"), (47, "d10"), (50, "d12"), (54, "d14"), (55, "d15"),
                  (74, "w8"), (76, "w9")]
        self.assertEqual([r[:4] for r in rows], [(18, "n1", "_landing", "in"), (23, "n3", "_chat_page", "in"), (25, "n4", "_landing", "in"),
                                                 (26, "n5", "_landing", "in")] + [(line, lit, "_landing", "in") for line, lit in pinned])
        # the rulings on the census bounds (2026-09-28): a helper whose return holds a read the follow does not place (test_c: a read
        # under a wrapper other than a `.decode` chain, `.strip()`, `str(...)`, `or`, a conditional, a slice of a Name bound to the
        # read, a whole return so wrapped, a self.<attr> the helper assigns the read) had given no position, so its call was no fetch
        # and the regex over its body in neither census. Every fetch of a page route through such a helper is REFUSED now, an
        # unclassified row at the call (59 to 71, and 73 and 75 for _mixed, whose other return still binds w8 and w9), and the call
        # binds nothing more than its placed positions give; a fetch of a path that is no page route (_json) is none. The other
        # forms the containment check claims are each refused the same way (79 to 91; each was unpinned at the check on the census
        # bounds): a `.getvalue()` read (_gv), an attribute inside a tuple or a list target (_attr_tuple, _attr_list), an annotated
        # and an augmented attribute assignment (_attr_ann, _attr_aug), a chain deeper than self.<attr> (_deep), and a chain bound
        # to an expression holding a Name bound to the read (_via_name)
        refused = [(59, "_landing"), (61, "_landing"), (63, "_landing"), (65, "_landing"), (67, "_landing"), (69, "_chat_page"), (71, "_sw_js"),
                   (73, "_landing"), (75, "_landing"), (79, "_landing"), (81, "_landing"), (83, "_landing"), (85, "_landing"), (87, "_landing"),
                   (89, "_landing"), (91, "_landing")]
        self.assertEqual([r[:3] for r in readers], sorted([(18, "assert", "_landing"), (19, "regex", "_landing"), (23, "assert", "_chat_page"),
                                                           (25, "assert", "_landing"), (26, "assert", "_landing")] + [(line, "assert", "_landing") for line, _ in pinned]
                                                          + [(line, "unclassified", text) for line, text in refused]),
                         "the body a helper returns by name is read in both censuses, no status or headers read is a read of the page, and a "
                         "fetch through a helper whose return holds a read the follow cannot place is refused")
        self.assertEqual([r[3].split(":")[0] for r in readers if r[1] == "unclassified"],
                         ["refused fetch, _%s returns a read the follow cannot place" % h for h in ("strip", "str", "or", "ifexp", "cut", "kept", "whole", "mixed", "mixed",
                                                                                                    "gv", "attr_tuple", "attr_ann", "attr_aug", "deep", "via_name",
                                                                                                    "attr_list")])
        self.assertEqual({k: sorted(v, key=str) for k, v in _response_reads(ast.parse(src)).items()},
                         {"_named": [-2, 1], "_aliased": [-1, 1], "_opaque": ["unknown"], "_echo": [], "test_a": [], "test_b": [], "_two": [-1, -2, 0, 1],
                          "_forv": ["unknown"], "_withv": ["unknown"], "_exc": ["unknown"], "_aug": [-1, 1], "_walrus": [-1, 1], "_ann": [-1, 1],
                          "_tuplepair": [-1, 1], "_listpair": [-1, 1], "_opaque2": ["unknown"], "_outer2": [], "inner": ["whole"], "test_c": [],
                          "_kept": ["refused"], "_strip": ["refused"], "_str": ["refused"], "_or": ["refused"], "_ifexp": ["refused"], "_cut": ["refused"],
                          "_whole": ["refused"], "_mixed": [-1, 1, "refused"], "_json": ["refused"], "_gv": ["refused"], "_attr_tuple": ["refused"],
                          "_attr_ann": ["refused"], "_attr_aug": ["refused"], "_deep": ["refused"], "_via_name": ["refused"],
                          "_attr_list": ["refused"], "test_d": [], "_opaque3": []})

    def test_a_call_is_a_fetch_only_where_its_callee_reads_a_response(self):
        # the rulings at the merge of main's login cookie split (2026-09-28), P2: a call to a Name or a self.<method> whose first
        # argument is a route literal had counted as a fetch whatever the callee, so `_pathconf("/", "PC_PATH_MAX", 4096)` read as a
        # fetch of the landing, and the module's helper it was handed to (`case.assertGreaterEqual(ceiling - 1, 0)`) as an
        # unclassified reader of the page. A synthetic module pins the rule: the module's own helper whose returns read no response
        # (os.pathconf's answer) is no fetch, in an assignment of its own or inside a tuple assignment; one whose return reads a
        # response (`urlopen(path).read().decode()`) is; and a callee the module does not define keeps the reading before the
        # ruling, a fetch. A Return is credited to the innermost function holding it (_response_reads), so a helper whose nested
        # def reads a response while its own returns read none (`_outer`) is no fetch either (the rulings on the census pass,
        # 2026-09-28: a walk that credits the nested def's returns to the helper binds `st` here). The rows of both derivations are named,
        # never inferred.
        getters, constants, routes = page_getters(), served_constants(), route_getters()
        src = '''import unittest
def _pathconf(path, name, default):
    try:
        return os.pathconf(path, name)
    except OSError:
        return default
def _get(path):
    return urlopen(path).read().decode()
class T(unittest.TestCase):
    def test_a(self):
        path_max = _pathconf("/", "PC_PATH_MAX", 4096)
        _fits(self, path_max)
        page = _get("/")
        self.assertIn("q1", page)
        other = elsewhere("/chat?token=x")
        self.assertIn("q2", other)
        a, b = _pathconf("/", "PC_NAME_MAX", 255), _get("/sw.js")
        self.assertIn("q3", b)
        self.assertIn("q4", a)
        st = _outer("/")
        self.assertIn("q5", st)
def _fits(case, ceiling):
    case.assertGreaterEqual(ceiling - 1, 0)
def _outer(path):
    def inner(r):
        return r.read()
    return os.stat(path)
'''
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write(src)
        try:
            rows = rows_of(f.name, getters, constants, routes)
            readers = readers_of(f.name, getters, constants, routes)
        finally:
            os.unlink(f.name)
        self.assertEqual([r[:3] for r in readers], [(14, "assert", "_landing"), (16, "assert", "_chat_page"), (18, "assert", "_sw_js")],
                         "os.pathconf's answer is no read of the page, and no helper handed it is followed")
        self.assertEqual([r[:4] for r in rows], [(14, "q1", "_landing", "in"), (16, "q2", "_chat_page", "in"), (18, "q3", "_sw_js", "in")])
        self.assertEqual({k: sorted(v, key=str) for k, v in _response_reads(ast.parse(src)).items()},
                         {"_pathconf": [], "_get": ["whole"], "test_a": [], "_fits": [], "_outer": [], "inner": ["whole"]})

    def test_the_fold_reader_splits_the_text_by_fold_and_refuses_what_it_cannot_place(self):
        # the rulings at the merge of main's login cookie split (2026-09-28): tests/test_token_login_page.py read the token login
        # page's <details> folds with an HTMLParser of its own, the parser beside served_css this census refuses (its reader row was
        # unclassified), and the ruling put the reader in served_css (fold_text) with its refusals and routed the test through it.
        # The reader's split, its records and each refusal are pinned here on synthetic pages: text outside every fold and inside a
        # fold's summary is shown, a nested fold is hidden whole, a fold inside a summary shows its own summary alone; references
        # decode as HTML decodes text; the title, script and style content and comments are text of neither part; and each shape
        # the reader names as one where the split would part from what HTML shows refuses, the element layer's refusals included
        # (round 6, correctness-2: a summary after a self-closing `<div/>` or `<span/>`, which HTML opens, is not its fold's first
        # summary child; the element layer had not pushed the tag, and the summary read as the fold's).
        split = lambda page: (served_css.fold_text(page).shown, served_css.fold_text(page).folded)
        self.assertEqual(split("<p>a</p><details><summary>b <code>c</code></summary>d<p>e</p></details>f"), ("ab cf", "de"))
        self.assertEqual(split("<details><summary>s1</summary>h1<details><summary>s2</summary>h2</details></details>t"), ("s1t", "h1s2h2"))
        self.assertEqual(split("<details><summary>s<details><summary>u</summary>v</details></summary>w</details>"), ("su", "vw"))
        self.assertEqual(split("<details>x<summary>s</summary></details><summary>free</summary>"), ("sfree", "x"), "a summary outside a fold is page text")
        self.assertEqual(split("<p>a&amp;b &lt;c&gt; &notit; &#65;&#x42 ro<b>mp</b></p>&amp"), ("a&b <c> \xacit; AB romp&", ""))
        self.assertEqual(split("<title>T</title><script>var s='<details>x';</script><style>p{}</style><!-- c --><p>y\r\nz\rw</p>"), ("y\nz\nw", ""))
        page = "<!DOCTYPE html>\n<details id=a><summary onclick=x>s</summary><i class=b>h</i></details><details><p>n</p></details><form method=get>"
        text = served_css.fold_text(page)
        self.assertEqual(text.folds, (served_css.Fold(page.index("<details id=a>"), page.index("<summary")), served_css.Fold(page.index("<details><p>"), None)))
        self.assertEqual(text.attrs, (("details", "id", True), ("summary", "onclick", True), ("i", "class", True), ("form", "method", False)))
        self.assertEqual(text.doctype, "DOCTYPE html")
        self.assertEqual([served_css.fold_text(p).doctype for p in (" \n<!doctype html><p>x", "<!-- c --><!doctype html>", "<p>x</p>")], ["doctype html", None, None])
        self.assertEqual(split("<svg>\n</svg><p>x</p>"), ("\nx", ""), "whitespace inside a refused container is no text to refuse")
        refusals = (("<details open><summary>s</summary>x</details>", "reads every fold closed"),
                    ("<details><summary>a</summary><summary>b</summary></details>", "not its first summary child"),
                    ("<details><div><summary>a</summary></div></details>", "not its first summary child"),
                    ("<details><div/><summary>S</summary>C</details>", "not its first summary child"),
                    ("<details><span/><summary>S</summary>C</details>", "not its first summary child"),
                    ("<details/><p>x</p>", "self-closing <details/>"),
                    ("<details><summary/>x</details>", "self-closing <summary/>"),
                    ("<p hidden>x</p>", "default style sheet hides it"),
                    ("<template>x</template>", "inside <template>"),
                    ("<noscript>x</noscript>", "inside <noscript>"),
                    ("<svg><text>x</text></svg>", "inside <svg>"),
                    ("<p>&#x0b;</p>", "control or noncharacter"),
                    ("<p>a\x00b</p>", "a NUL in text"),
                    ("<![CDATA[x]]><p>y</p>", "CDATA"),
                    # the end-of-page refusal's two halves, a lower-case and an upper-case letter: the builds part on both the same
                    # way (some hand the letter over as data, dropping the &, others report a reference)
                    ("<p>x</p>&a", "flush differently"),
                    ("<p>x</p>&G", "flush differently"))
        for page, message in refusals:
            with self.assertRaises(AssertionError, msg=page) as cm:
                served_css.fold_text(page)
            self.assertIn(message, str(cm.exception), page)
        # the disclosed error (round 6, served_css's docstring): both engines ignore this `</details>` (the table inside it is a scope
        # boundary) and keep S as the fold's summary and H as its content (measured with this page); the reader pops the details and
        # shows both. A witness of the reading, so a reader that learns the scope rule changes it here on purpose
        self.assertEqual(split("<details><table></details><summary>S</summary>H</details>"), ("SH", ""))

    def test_a_fetched_page_is_judged_as_served_and_a_row_with_no_hit_fails(self):
        # the rulings at the merge of main's login cookie split (2026-09-28), Q5: since that change Handler._send puts the sign-in
        # seed and the page-key script (_PAGE_KEY_JS) first in the head of every authorized page, so a fetched page is no longer its
        # getter's text, and a row judged against a text that does not carry its literal anywhere had passed in silence
        # (test_session_cookie_auth.py's `__rompPageKey` over the fetched landing, in the page-key script alone). The model is _send
        # itself, run on a stand-in sign-in (served_body): the getter's text around what _send puts first in its head, the seed and
        # then the key script, and a text with no head or served as a script written as it stands. A getter's texts are its render
        # and the string constants its returns spell (getter_renders: `_files_page` without its sheet). judge_rows fails a row whose
        # literal occurs in none of its texts, and still flags one a comment satisfies, in a render and in a served body alike.
        render = pages()["_landing"]
        body = served_body(render, "markup")
        head = render.index("<head>") + len("<head>")
        injected = body[head:len(body) - (len(render) - head)]
        self.assertEqual((body[:head], body[head + len(injected):]), (render[:head], render[head:]), "the getter's text around what _send puts in its head")
        key = "<script>" + km._PAGE_KEY_JS + "</script>"
        self.assertTrue(injected.endswith(key), "the page-key script goes last of the two: %r" % injected[-120:])
        seed = injected[:-len(key)]
        self.assertTrue(seed.startswith("<script>") and seed.endswith("</script>") and "localStorage.setItem(%s," % json.dumps(km._PAGE_KEY_SLOT) in seed,
                        "the sign-in seed goes first, storing the page key in this kernel's slot: %r" % seed[:160])
        self.assertEqual(served_body(pages()["_sw_js"], "script"), pages()["_sw_js"], "a script is served as it stands")
        missing = [t for t in getter_renders("_files_page")[1:] if "needs the ui/ modules" in t]
        self.assertTrue(missing, "the page _files_page returns without its sheet: %r" % (getter_renders("_files_page")[1:],))
        self.assertEqual(served_body(missing[0], "markup"), missing[0], "a text with no head is served as it stands")
        s, e = served_css.comment_spans(render)[0]
        comment = render[s:e]
        rows = [("m.py", 1, "__rompPageKey", "_landing", "in", True, True), ("m.py", 2, "__rompPageKey", "_landing", "in", True, False),
                ("m.py", 3, "needs the ui/ modules", "_files_page", "in", True, False), ("m.py", 4, "\x00in no served text\x00", "_LANDING_MOBILE_JS", "in", True, False),
                ("m.py", 5, comment, "_landing", "in", True, False), ("m.py", 6, comment, "_landing", "in", True, True)]
        flagged, zero = judge_rows(rows)
        self.assertEqual([z.split(" ")[0] for z in zero], ["m.py:2", "m.py:4"], "a literal in no text it is judged against fails: %r" % (zero,))
        self.assertEqual([f.split(" ")[0] for f in flagged], ["m.py:5", "m.py:6"], "a literal a comment satisfies is flagged, over a render and a served body: %r" % (flagged,))

    def test_the_route_walk_reads_equality_and_membership(self):
        # the author's pass 8 (2026-09-20): the (route, getter) pairs are derived from the handler by a shape-sensitive walk, never restated. A
        # synthetic handler with both shapes pins the two: the landing's membership tuple and the equality routes; a route
        # returning json.dumps, a getter called with arguments, a getter called bare inside another call in the return (the
        # rulings on the census pass, 2026-09-28: the walk reads a getter only as a DIRECT positional argument of the returned
        # call, and a walk over the whole return reds here on /wrapped), the condition's other spellings (the rulings on the census
        # bounds, 2026-09-28: a getter inside a splice or an f-string argument, or handed by keyword; a walk that descends through
        # an argument that is no call reds here on /spliced or /formatted, and one that reads keywords on /byname) and a prefix test
        # bind nothing. An equality-only walk misses the landing here. On the kernel the landing is served through the route table
        # since the merge of main's login cookie split (the next test pins that shape), and the service worker by equality.
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
    if p == "/wrapped":
        return self._send(200, wrap(_timeline_page()), "text/html")
    if p == "/spliced":
        return self._send(200, _feed_page() + "<!-- tail -->", "text/html")
    if p == "/formatted":
        return self._send(200, f"<!doctype html>{_files_page()}", "text/html")
    if p == "/byname":
        return self._send(200, body=_waiting_page(), ctype="text/html")
    if p.startswith("/dist/"):
        return self._send_file(p)
'''
        self.assertEqual(route_getters(handler), {"/": "_landing", "": "_landing", "/chat": "_chat_page", "/sw.js": "_sw_js"})
        real = route_getters()
        self.assertEqual((real.get("/"), real.get("")), ("_landing", "_landing"), "the landing on the kernel: %r" % (real,))
        self.assertIn("/sw.js", real, "an equality route on the kernel: %r" % (real,))
        self.assertEqual(sorted(set(real.values()) - set(page_getters())), [], real)

    def test_the_route_walk_reads_the_route_table(self):
        # the merge of main's login cookie split (2026-09-28): the kernel's pages moved from `if` branches onto one table,
        # `_PAGE_RENDERERS = {"": _landing, "/": _landing, "/chat": _chat_page, ...}`, looked up by the dispatch as `_page =
        # _PAGE_RENDERERS.get(p)` and served by `return self._send(200, _page(), ...)`, and the two-shape walk found the service
        # worker alone on the kernel: the fetched rows over every page left the pins census's population, and the container census
        # read no page. A synthetic handler pins the third shape: a table's keys whose values are derived getters named bare are
        # routes when a function looks the table up and returns a call carrying the looked-up name called bare. A lambda value, a
        # value that is no derived getter, a table nothing looks up, a lookup whose result is never called in a return, and a
        # lookup in one function with the call in another bind nothing. A walk without the table branch reds here (the synthetic
        # table's three routes missing) and on the kernel (no landing, no pane page). The rulings at the merge (2026-09-28) add the
        # no-argument condition's case: a lookup whose result a return calls WITH an argument, positional or by keyword, renders
        # another text and binds nothing (a walk that drops either half of the condition reds here on /settings or /waiting). The
        # rulings on the census pass (2026-09-28) add a lookup whose result a return calls bare INSIDE another call
        # (`wrap(wrapped())`), which binds nothing, since the looked-up name counts only as a direct positional argument of the
        # returned call (a walk over the whole return reds here on /wrapped); and the rulings on the census bounds (2026-09-28) the
        # condition's other spellings: the call inside a splice or an f-string argument, or handed by keyword, binds nothing (a walk
        # that descends through an argument that is no call reds here on /spliced or /formatted, and one that reads keywords on
        # /byname).
        handler = '''
PAGES = {"": _landing, "/": _landing, "/chat": _chat_page, "/shim": lambda: _shim_core_js("chat"), "/nope": _not_a_getter}
UNREAD = {"/feed": _feed_page}
UNCALLED = {"/timeline": _timeline_page}
APART = {"/files": _files_page}
POSITIONAL = {"/settings": _settings_page}
KEYWORD = {"/waiting": _waiting_page}
WRAPPED = {"/wrapped": _feed_page}
SPLICED = {"/spliced": _timeline_page}
FORMATTED = {"/formatted": _files_page}
BYNAME = {"/byname": _settings_page}
def do_GET(self):
    p = "/x"
    page = PAGES.get(p)
    if page is not None:
        return self._send(200, page(), "text/html")
    other = UNCALLED.get(p)
    if other is not None:
        return self._send(200, json.dumps(str(other)), "application/json")
    argued = POSITIONAL.get(p)
    if argued is not None:
        return self._send(200, argued(p), "text/html")
    named = KEYWORD.get(p)
    if named is not None:
        return self._send(200, named(path=p), "text/html")
    wrapped = WRAPPED.get(p)
    if wrapped is not None:
        return self._send(200, wrap(wrapped()), "text/html")
    spliced = SPLICED.get(p)
    if spliced is not None:
        return self._send(200, spliced() + "<!-- tail -->", "text/html")
    formatted = FORMATTED.get(p)
    if formatted is not None:
        return self._send(200, f"<!doctype html>{formatted()}", "text/html")
    byname = BYNAME.get(p)
    if byname is not None:
        return self._send(200, body=byname(), ctype="text/html")
    if p == "/sw.js":
        return self._send(200, _sw_js(), "text/javascript")
def lookup_only(self, p):
    found = APART.get(p)
    return found
def call_only(self):
    return self._send(200, found(), "text/html")
'''
        self.assertEqual(route_getters(handler), {"": "_landing", "/": "_landing", "/chat": "_chat_page", "/sw.js": "_sw_js"})
        real = route_getters()
        pages_ = {g for g in real.values() if getter_kind(g) == "markup"}
        self.assertGreaterEqual(len(pages_), 8, "the landing and the pane pages on the kernel, through its route table: %r" % (real,))
        self.assertEqual(sorted(pages_ - set(page_getters())), [], real)


if __name__ == "__main__":
    unittest.main()
