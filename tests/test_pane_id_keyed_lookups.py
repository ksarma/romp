#!/usr/bin/env python3
"""Every lookup the shell's and the phone's scripts make by pane id reads an object with no prototype.

A pane id is any name the id rule accepts ([a-z][a-z0-9_-]{0,31}), and one Object member's name fits it: constructor.
A lookup by id in a plain object ({...}, JSON.parse's result) finds the inherited member when nothing was set under the
id, so F['constructor'] is the Object function, and `'constructor' in po` is true before anything was stored. Every
object these scripts look a pane id up in is therefore made with Object.create(null) (or is a Map), and this census
holds each lookup to it.

THE POPULATION is derived from the kernel, never listed here, and an empty one fails: the builder of the panes defined
at the kernel (_LANDING_PANE_RECORDS_JS), every inline script that defines a join the builder calls (its JOINS list),
and every inline script that reads body[data-panes], the generic panes' rows. The tables below name exactly those.

THE LOOKUPS are read from each script's lexemes (strings, comments and regular expressions are skipped): a subscript
whose key is not a single literal (X[k], a.b[k]) and that is not the target of an assignment or a delete, and the right
side of `in`. Each object looked up so is in one of two tables: ID_KEYED, the objects keyed by a pane id or by a name
made from one, or OTHER, with what keys it (an array indexed by number, the Log's kinds). An object in neither table
fails, so a new lookup is classified before it lands.

THE RULE for each object in ID_KEYED, per script: at least one assignment makes it with no prototype
(Object.create(null), Object.assign(Object.create(null), ...), new Map(...), or a call to a FACTORIES function that
returns such an object); every other assignment that replaces it comes before the first of those (merging into the
object itself, Object.assign(X, ...), keeps its prototype and is allowed anywhere); and every lookup of it comes after
the first. The order is the source's, the order the scripts run their top-level statements in. A lookup of a named
function's parameter stands for that function's calls, each of which must pass the object under the same name.

No node, no browser: the scripts are read as text from the loaded kernel module."""
import os
import re
import tempfile
import unittest
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")

# Hermetic state BEFORE the loads: they resolve their state root at import time, and only pytest runs conftest's floor
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
load_source("romp_event_model", os.path.join(BIN, "romp-event-model"))
load_source("romp_judge", os.path.join(BIN, "romp-judge"))
km = load_source("romp_kernel_idkeyed", os.path.join(BIN, "romp-kernel"))

# the objects keyed by a pane id, or by a name made from one (a frame's id f-<id>, an element's id <id>-pane)
ID_KEYED = {
    "_LANDING_JS": {"grow": "pane id (the columns' grow)", "KEYS": "a pane's element id",
                    "px": "a pane's element id"},
    "_LANDING_FOCUS_JS": {"PANE": "a pane's frame id"},
    "_LANDING_ERRS_JS": {"PN": "pane id (the titles)", "st": "the app a frame reports, a state-root pane's id"},
    "_LANDING_ESC_JS": {},
    "_LANDING_PANE_RECORDS_JS": {"seen": "pane id (the rows accepted so far)"},
    "_LANDING_MOBILE_JS": {"F": "pane id (the frames)", "URLS": "pane id", "EPI": "pane id", "TOK": "pane id",
                           "PEND": "pane id", "DEAD": "pane id"},
    "_LANDING_COLLAPSE_JS": {"po": "pane id (the rail's flags)", "DEF": "pane id (the defaults)",
                             "stored": "pane id (the stored flags)", "DPX": "pane id (experimental or not)",
                             "LBL": "pane id (the labels)", "on": "pane id (the gear's flags)",
                             "p": "pane id (the gear's stored panes)", "pane": "a pane's frame id"},
}
# the objects these scripts look up by a key that is not a pane id, and what keys each
OTHER = {
    "_LANDING_JS": {"seq": "an array of element ids, indexed by number"},
    "_LANDING_FOCUS_JS": {"t": "a drag's list of types, indexed by number",
                          "cols": "an array of frame ids, indexed by number"},
    "_LANDING_ERRS_JS": {"FILT": "the Log's kinds", "KINDLBL": "the Log's kinds", "DESC": "the Log's kinds",
                         "NOTES": "an array of the Log's entries, indexed by number",
                         "stc": "a split chat column's key"},
    "_LANDING_ESC_JS": {},
    "_LANDING_PANE_RECORDS_JS": {"window": "the names of the joins the builder lists (JOINS)"},
    "_LANDING_MOBILE_JS": {"B": "a list of tab buttons, indexed by number", "A": "a rail action's name (data-act)",
                           "SH_LADDER": "an array of delays, indexed by number",
                           "navigator": "a feature test of the browser object"},
    "_LANDING_COLLAPSE_JS": {"TABSETS": "a chat column frame's element id", "seen": "a chat tab's session id"},
}
# a function whose return value is one of the ID_KEYED objects: (script, function) -> the local it builds and returns
FACTORIES = {("_LANDING_COLLAPSE_JS", "optOn"): "on"}

_KEYWORDS_BEFORE_VALUE = {"return", "typeof", "in", "of", "case", "do", "else", "new", "delete", "void", "throw",
                          "instanceof"}
_IDENT = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*")
_NUM = re.compile(r"0[xX][0-9a-fA-F]+|\d+(?:\.\d+)?(?:[eE][+-]?\d+)?|\.\d+")


def lexemes(src):
    """[(kind, text, offset)]: identifiers, numbers, strings, regular expressions and one-character punctuators, with
    comments and whitespace dropped. A slash starts a regular expression where a value is expected (after a punctuator
    other than a closing one, after a keyword that takes a value, or at the start), else it is division."""
    out, i, n = [], 0, len(src)
    while i < n:
        c = src[i]
        if c in " \t\r\n":
            i += 1
            continue
        if src.startswith("//", i):
            j = src.find("\n", i)
            i = n if j < 0 else j
            continue
        if src.startswith("/*", i):
            j = src.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        if c in "'\"`":
            j = i + 1
            while j < n and src[j] != c:
                j += 2 if src[j] == "\\" else 1
            out.append(("str", src[i:j + 1], i))
            i = j + 1
            continue
        prev = out[-1] if out else None
        value_due = (prev is None or (prev[0] == "op" and prev[1] not in ")]")
                     or (prev[0] == "id" and prev[1] in _KEYWORDS_BEFORE_VALUE))
        if c == "/" and value_due:
            j, in_class = i + 1, False
            while j < n:
                if src[j] == "\\":
                    j += 2
                    continue
                if src[j] == "[":
                    in_class = True
                elif src[j] == "]":
                    in_class = False
                elif src[j] == "/" and not in_class:
                    break
                elif src[j] == "\n":
                    raise AssertionError("a regular expression runs past its line at offset %d: a slash misread" % i)
                j += 1
            j += 1
            while j < n and src[j].isalpha():
                j += 1
            out.append(("re", src[i:j], i))
            i = j
            continue
        m = _IDENT.match(src, i)
        if m:
            out.append(("id", m.group(), i))
            i = m.end()
            continue
        m = _NUM.match(src, i)
        if m:
            out.append(("num", m.group(), i))
            i = m.end()
            continue
        out.append(("op", c, i))
        i += 1
    return out


def _is(t, k, kind, text=None):
    return 0 <= k < len(t) and t[k][0] == kind and (text is None or t[k][1] == text)


def _closing(t, k, opening, closing):
    depth = 0
    for j in range(k, len(t)):
        if _is(t, j, "op", opening):
            depth += 1
        elif _is(t, j, "op", closing):
            depth -= 1
            if depth == 0:
                return j
    raise AssertionError("no closing %r for the %r at lexeme %d" % (closing, opening, k))


def lookups(t):
    """[(target, lexeme index)]: each subscript read by a key that is not one literal, and each right side of `in`. The
    target is the object's name, a dotted chain (a.b), or '(expression)' where the object is a call's or a subscript's
    value."""
    out = []
    for k, tok in enumerate(t):
        if tok[:2] == ("op", "[") and k > 0:
            before = t[k - 1]
            start = k - 1   # the first lexeme of the object's expression
            if before[0] == "id" and before[1] not in _KEYWORDS_BEFORE_VALUE:
                chain = [before[1]]
                while _is(t, start - 1, "op", ".") and _is(t, start - 2, "id"):
                    start -= 2
                    chain.insert(0, t[start][1])
                dangling = _is(t, start - 1, "op", ".")   # a chain hung off a call's or a subscript's value
                target = "(expression)" if dangling else ".".join(chain)
            elif before[:2] in (("op", ")"), ("op", "]")):
                target = "(expression)"
            else:
                continue   # an array literal, not a subscript
            end = _closing(t, k, "[", "]")
            if end == k + 2 and t[k + 1][0] in ("str", "num"):
                continue   # a literal key: X['name'], X[0]
            written = _is(t, end + 1, "op", "=") and not _is(t, end + 2, "op", "=")
            if written or _is(t, start - 1, "id", "delete"):
                continue
            out.append((target, k))
        elif tok[:2] == ("id", "in") and k + 1 < len(t):
            if t[k + 1][0] != "id":
                out.append(("(expression)", k))
                continue
            j, chain = k + 1, [t[k + 1][1]]
            while _is(t, j + 1, "op", ".") and _is(t, j + 2, "id"):
                j += 2
                chain.append(t[j][1])
            out.append((".".join(chain), k))
    return out


def functions(t):
    """[(name or None, [parameter], body's first lexeme, body's last lexeme)] for every `function` in the lexemes."""
    out = []
    for k, tok in enumerate(t):
        if tok[:2] != ("id", "function"):
            continue
        j = k + 1
        name = None
        if _is(t, j, "id"):
            name, j = t[j][1], j + 1
        if not _is(t, j, "op", "("):
            continue
        close = _closing(t, j, "(", ")")
        params = [x[1] for x in t[j + 1:close] if x[0] == "id"]
        if not _is(t, close + 1, "op", "{"):
            continue
        out.append((name, params, close + 1, _closing(t, close + 1, "{", "}")))
    return out


def _arguments(t, k):
    """The argument lexeme lists of the call whose '(' is lexeme k."""
    args, cur, depth = [], [], 0
    for j in range(k + 1, _closing(t, k, "(", ")")):
        x = t[j]
        if x[0] == "op" and x[1] in "([{":
            depth += 1
        elif x[0] == "op" and x[1] in ")]}":
            depth -= 1
        if depth == 0 and x[:2] == ("op", ","):
            args.append(cur)
            cur = []
        else:
            cur.append(x)
    args.append(cur)
    return args


def sites(t, obj, k, fns, why):
    """The lexeme indexes a lookup of `obj` at lexeme k stands for: k itself, or, where obj is a parameter of a named
    function enclosing k, the calls of that function (each must pass obj under the same name), resolved the same way."""
    for name, params, a, b in sorted((f for f in fns if f[2] < k < f[3]), key=lambda f: f[3] - f[2]):
        if obj not in params:
            continue
        if not name:
            why.append("%s is a parameter of an unnamed function at lexeme %d: its callers cannot be read" % (obj, a))
            return []
        pos = params.index(obj)
        calls = [j for j in range(len(t) - 1) if _is(t, j, "id", name) and _is(t, j + 1, "op", "(")
                 and not _is(t, j - 1, "id", "function") and not _is(t, j - 1, "op", ".")]
        if not calls:
            why.append("%s is a parameter of %s, which is never called" % (obj, name))
        out = []
        for j in calls:
            args = _arguments(t, j + 1)
            if pos >= len(args) or [x[:2] for x in args[pos]] != [("id", obj)]:
                why.append("a call of %s at lexeme %d passes something other than %s for it" % (name, j, obj))
                continue
            out += sites(t, obj, j, fns, why)
        return out
    return [k]


def assignments(t, name, factories):
    """[(lexeme index, kind)] for each assignment that replaces `name` (name = ..., never a member's or a subscript's):
    kind is 'bare' for an object with no prototype, 'merge' for Object.assign(name, ...), else 'plain'."""
    bare_forms = (["Object", ".", "create", "(", "null", ")"],
                  ["Object", ".", "assign", "(", "Object", ".", "create", "(", "null", ")"],
                  ["new", "Map", "("]) + tuple([f, "(", ")"] for f in factories)
    out = []
    for k in range(len(t) - 2):
        if not (_is(t, k, "id", name) and _is(t, k + 1, "op", "=") and not _is(t, k + 2, "op", "=")):
            continue
        if _is(t, k - 1, "op", "."):
            continue   # a member's assignment (a.name = ...), not the object's
        rhs = [x[1] for x in t[k + 2:k + 14]]
        if any(rhs[:len(f)] == f for f in bare_forms):
            out.append((k, "bare"))
        elif rhs[:6] == ["Object", ".", "assign", "(", name, ","]:
            out.append((k, "merge"))
        else:
            out.append((k, "plain"))
    return out


def population():
    """{attribute name: script} for every inline script a pane id reaches, derived from the kernel."""
    builder = km._LANDING_PANE_RECORDS_JS
    m = re.search(r"var JOINS=\[([^\]]*)\]", builder)
    if not m:
        raise AssertionError("_LANDING_PANE_RECORDS_JS: the JOINS list was not found; re-anchor")
    joins = re.findall(r"'([A-Za-z_$][\w$]*)'", m.group(1))
    if not joins:
        raise AssertionError("_LANDING_PANE_RECORDS_JS: the JOINS list is empty")
    scripts = {n: v for n, v in vars(km).items() if n.startswith("_") and n.endswith("_JS") and isinstance(v, str)}
    out = {"_LANDING_PANE_RECORDS_JS": builder}
    for j in joins:
        hosts = [n for n, v in scripts.items() if re.search(r"window\." + re.escape(j) + r"\s*=", v)]
        if len(hosts) != 1:
            raise AssertionError("the join %s is defined in %r: expected one inline script" % (j, hosts))
        out[hosts[0]] = scripts[hosts[0]]
    for n, v in scripts.items():
        if re.search(r"getAttribute\(\s*['\"]data-panes['\"]\s*\)", v):   # either quote
            out[n] = v
    return out


class ThePaneIdKeyedLookups(unittest.TestCase):
    maxDiff = None

    def test_every_lookup_by_pane_id_reads_an_object_with_no_prototype(self):
        pop = population()
        # the census's own footing first: the population, the lexer, the tables
        self.assertGreaterEqual(len(pop), 2, "the population was derived: %r" % sorted(pop))
        self.assertEqual(sorted(pop), sorted(ID_KEYED), "the scripts a pane id reaches (the builder, its joins' hosts, "
                         "the readers of body[data-panes]) and ID_KEYED's scripts")
        self.assertEqual(sorted(ID_KEYED), sorted(OTHER), "ID_KEYED and OTHER name the same scripts")
        for name, src in sorted(pop.items()):
            with self.subTest(script=name, check="read whole"):
                # every bracket the lexer reads in code closes: no string, comment or regular expression misread
                stack = []
                for kind, text, at in lexemes(src):
                    if kind != "op":
                        continue
                    if text in "([{":
                        stack.append((text, at))
                    elif text in ")]}":
                        self.assertTrue(stack, "%s: a %r at offset %d closes nothing" % (name, text, at))
                        self.assertEqual("([{"[")]}".index(text)], stack.pop()[0],
                                         "%s: the %r at offset %d" % (name, text, at))
                self.assertEqual(stack, [], "%s: brackets left open" % name)
            with self.subTest(script=name, check="classified"):
                seen = {target for target, _ in lookups(lexemes(src))}
                known = set(ID_KEYED[name]) | set(OTHER[name])
                self.assertEqual(sorted(seen - known), [], "%s: objects looked up by a computed key that neither table "
                                 "names; add each to ID_KEYED (made with no prototype) or to OTHER with what keys it"
                                 % name)
                self.assertEqual(sorted(known - seen), [], "%s: table entries this script no longer looks up" % name)
                self.assertEqual(set(ID_KEYED[name]) & set(OTHER[name]), set(), "%s: an object in both tables" % name)
        # the rule, per object keyed by pane id
        for name, src in sorted(pop.items()):
            t = lexemes(src)
            fns = functions(t)
            found = lookups(t)
            factories = [f for (s, f) in FACTORIES if s == name]
            for obj in sorted(ID_KEYED[name]):
                with self.subTest(script=name, object=obj):
                    why = []
                    at = sorted({s for target, k in found if target == obj for s in sites(t, obj, k, fns, why)})
                    self.assertEqual(why, [], "%s: %s's lookups could not all be placed" % (name, obj))
                    made = assignments(t, obj, factories)
                    bare = [k for k, kind in made if kind == "bare"]
                    self.assertTrue(bare, "%s: %s is looked up by pane id but never made with no prototype "
                                    "(Object.create(null), Object.assign(Object.create(null), ...) or new Map)"
                                    % (name, obj))
                    first = bare[0]
                    late = [src[t[k][2]:t[k][2] + 60] for k, kind in made if kind == "plain" and k > first]
                    self.assertEqual(late, [], "%s: %s is replaced by an object with a prototype after it was made "
                                     "with none" % (name, obj))
                    early = [src[t[k][2]:t[k][2] + 60] for k in at if k < first]
                    self.assertEqual(early, [], "%s: %s is looked up before it is made with no prototype" % (name, obj))
        for (name, fn), local in sorted(FACTORIES.items()):
            with self.subTest(factory=fn):
                src = pop[name]
                a = src.index("function " + fn + "(){")
                ft = lexemes(src[a:])
                end = _closing(ft, [x[:2] for x in ft].index(("op", "{")), "{", "}")
                text = src[a:a + ft[end][2] + 1]   # the function, from its keyword to its closing brace
                self.assertTrue(text.startswith("function %s(){var %s=Object.create(null);" % (fn, local)),
                                "%s builds %s with no prototype first: %r" % (fn, local, text[:80]))
                self.assertTrue(text.endswith("return %s;}" % local), "%s returns %s: %r" % (fn, local, text[-40:]))
                self.assertEqual([k for k, kind in assignments(lexemes(text), local, []) if kind == "plain"], [],
                                 "%s never replaces %s with an object that has a prototype" % (fn, local))


if __name__ == "__main__":
    unittest.main()
