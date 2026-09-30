#!/usr/bin/env python3
"""No writer in this tree emits a perf minute row whose `capped` carries a byte count and an EMPTY dropped list,
{"capped": {"bytes": N, "dropped": []}}: the absence is pinned here in place of a reader case for that shape (the
maintainer's round 6 of the wsBytesByHost review, extra11-2; the reviewer's ruling of 2026-09-21 declined the case and
asked for this pin).

THE RULE. A `capped` value on a client-diag row is the kernel's own marker, written by kernel/kernel.py's
_client_diag_line after the admit and admitted from no poster (tests/test_client_diag_allowlist.py, MARKERS), in two
shapes: `true` beside `bytes`, the whole-row marker; or {bytes, dropped} on a perf minute row, `dropped` the keys the
ladder shed in its order and never empty, since the object is built only after a key came off the row. The reader,
`bin/romp perf client`, counts a minute row whose `capped` is an object as a shed row and names the keys `dropped`
lists (`capped.get("dropped") or []`), so an object naming no key, an empty list or no list at all, is counted as shed
and names nothing. Nothing produces that shape today, and this module reds exactly when a writer starts to; at that
point the reader case becomes owed to whoever can see why the list is empty, and the failure says so.

THE READER, MEASURED (READ 2026-09-21 at this branch's head, by the pass that wrote this module, over an own state root
holding one synthetic minute row carrying {"bytes": 26000, "dropped": []} beside its figures; no kernel, a curl stub
on PATH never called): `bin/romp perf client` printed "1 minute row shed keys, 0 rows capped whole" in its header and
folded the row's figures, and `--json` read shed_minute_rows 1, shed_keys {}, capped_rows 0, cut_rows 0. The closing
fixer pass had read the same earlier that day. Recorded so a later reader knows the reader was checked, not assumed.

THE CENSUS is derived from the tree, never a literal list, so a new writer is caught wherever it appears: every site
that WRITES a member named `capped`. In the kernel's Python by its syntax tree (a dict display key, a keyword argument
such as dict(..., capped=...), a subscript or attribute assignment, a setdefault), over every module under kernel/ and
every Python script under bin/. In the page bundles' sources by a member-write pattern over comment-stripped code
(`capped: <value>` in an object literal, `.capped = <value>`, `["capped"] = <value>`), over every non-test .ts and .js
under ui/, over every string constant of the kernel's Python modules that has the shape of script (a function keyword,
an arrow, or a parenthesis closing onto a brace), which is where the pane shim's inline JavaScript lives, and over the
shell scripts under bin/ with their comment tails removed. A local variable named capped is not a
member write and is not a site (kernel.py's notice-key set is one); a shorthand member `{ capped }` is outside the
pattern, the one form the census does not read. Each site is classified by the value it writes: an object literal
with its keys read, a scalar, or a value built elsewhere, which the census cannot read and refuses until a drive
exists for its writer. Every writer of an object, or of a value built elsewhere, must have a DRIVE below, keyed on its
file and function, that runs it with nothing to drop and with keys dropped; a writer without one fails the census
naming its file, line, function and shape. A scalar cannot carry a dropped list, so a scalar-valued site is classified
and owes no drive (ui/webview/anchor-map.ts's TRIM_STATS counter is one); a docstring is prose whatever it spells,
and a message string that says a thing is capped has no script shape, so neither is a site. The marker's own shape (`true` beside `bytes`) is the allowlist module's pin, not this one's: this
module holds every emitted `capped` to the one property that a capped object names at least one key.

Synthetic fixtures only: a placeholder dashboard id, invented figures."""
import ast
import contextlib
import functools
import io
import json
import os
import re
import tempfile
import unittest
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")

# Hermetic state BEFORE the loads: they resolve their state root at import time, and only pytest runs
# conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
load_source("romp_event_model", os.path.join(BIN, "romp-event-model"))
load_source("romp_judge", os.path.join(BIN, "romp-judge"))
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
km = load_source("romp_kernel_capped_shape", os.path.join(BIN, "romp-kernel"))

MEMBER = "capped"
WID = "11111111-2222-3333-4444-555555555555"
KERNEL_WRITER = ("kernel/kernel.py", "_client_diag_line")

# a minute row as ui/webview/perf-telemetry.ts builds it today (the allowlist module pins the same keys), under the bound
MINUTE = {"app": "chat", "since": 1700000000000, "span_ms": 60000,
          "frames": {"session": {"n": 12, "ms_sum": 340.5, "ms_max": 88.1, "n16": 5, "n100": 0, "hist": [0] * 14}},
          "free": {"n": 3, "p50": 12.5, "p90": 40, "max": 41.2},
          "loaf": {"n": 1, "blocking_ms": 60, "worst_ms": 110, "top": [{"k": "render.js:paintAll@9000", "ms": 90, "n": 1, "inv": "WebSocket.onmessage"}], "src": "loaf"},
          "slow": {"sent": 1, "suppressed": 0, "suppressed_worst_ms": 0},
          "dom": 53306, "visible": True, "hidden_pane": False, "ua": "safari-ios", "heap_mb": 210.4}


class Site(object):
    """One write of the member: where (file relative to the root, line, the enclosing function or `<module>`), the form the
    write takes, and the shape of the value written (`kind`: object, scalar, built elsewhere; `detail`: the object's keys, the
    scalar's text, or the expression's head)."""
    def __init__(self, file, line, function, form, kind, detail):
        self.file, self.line, self.function, self.form, self.kind, self.detail = file, line, function, form, kind, detail

    @property
    def writer(self):
        return (self.file, self.function)

    def shape(self):
        if self.kind == "object":
            return "an object literal with keys %s" % (", ".join(self.detail) if self.detail else "the census cannot read (a spread or a computed key)")
        return "%s %s" % (self.kind, self.detail)

    def __repr__(self):
        return "%s:%d (%s) %s, %s" % (self.file, self.line, self.function, self.form, self.shape())


def _rel(path):
    return os.path.relpath(path, ROOT).replace(os.sep, "/")


def _shebang_python(path):
    try:
        with open(path, "rb") as f:
            first = f.readline()
    except OSError:
        return False
    return first.startswith(b"#!") and b"python" in first


def _distinct(paths):
    """The paths whose real file is new to the list, in order: bin/romp-kernel, bin/romp-judge and bin/romp-event-model are links
    to the kernel's modules, and a file is read once under its first name."""
    out, seen = [], set()
    for p in paths:
        real = os.path.realpath(p)
        if real not in seen:
            seen.add(real)
            out.append(p)
    return out


def python_files():
    """Every module under kernel/ and every Python script under bin/ (by extension or shebang), each real file once."""
    out = []
    for base, dirs, files in os.walk(os.path.join(ROOT, "kernel")):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        out.extend(os.path.join(base, f) for f in sorted(files) if f.endswith(".py"))
    for f in sorted(os.listdir(BIN)):
        p = os.path.join(BIN, f)
        if os.path.isfile(p) and (f.endswith(".py") or _shebang_python(p)):
            out.append(p)
    return _distinct(out)


def shell_files():
    """The scripts under bin/ that are not Python (bin/romp, whose perf client is Python inside a shell heredoc): scanned as text."""
    return _distinct(sorted(os.path.join(BIN, f) for f in os.listdir(BIN)
                            if os.path.isfile(os.path.join(BIN, f)) and not f.endswith(".py") and not _shebang_python(os.path.join(BIN, f))))


def script_files():
    """Every .ts and .js under ui/ that is not a test file, outside build output and dependencies."""
    out = []
    for base, dirs, files in os.walk(os.path.join(ROOT, "ui")):
        dirs[:] = [d for d in dirs if d not in ("node_modules", "dist", "out-tests")]
        out.extend(os.path.join(base, f) for f in files
                   if (f.endswith(".ts") or f.endswith(".js")) and not re.search(r"\.test\.(ts|js)$", f))
    return sorted(out)


# ---- the Python reader: sites by syntax tree ---------------------------------------------------------------------------

def _py_shape(v):
    if isinstance(v, ast.Dict):
        keys = []
        for k in v.keys:
            if k is None or not isinstance(k, ast.Constant):
                return ("object", None)
            keys.append(str(k.value))
        return ("object", tuple(keys))
    if isinstance(v, ast.Constant):
        return ("scalar", repr(v.value))
    return ("built elsewhere", ast.unparse(v)[:80])


def _is_member_key(node):
    return isinstance(node, ast.Constant) and node.value == MEMBER


def _subscript_key(t):
    s = t.slice
    idx = getattr(ast, "Index", None)
    if idx is not None and isinstance(s, idx):   # the pre-3.9 wrapper, gone from 3.9 on
        s = s.value
    return s


def py_sites(path, src):
    """(sites, string constants) of one Python source: the member writes by their syntax, each with its enclosing function; and
    every string constant with its line and owner, for the JavaScript scan (the pane shim is a Python string)."""
    tree = ast.parse(src, filename=path)
    rel, sites, strings = _rel(path), [], []
    stack, docstrings = [(tree, "<module>")], set()
    while stack:
        node, owner = stack.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
            body = getattr(node, "body", None) or []
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
                docstrings.add(id(body[0].value))   # prose, not the shim: a docstring that spells the marker is not a write
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            inner = node.name if owner == "<module>" else owner + "." + node.name
        else:
            inner = owner
        if isinstance(node, ast.Dict):
            for k, v in zip(node.keys, node.values):
                if k is not None and _is_member_key(k):
                    sites.append(Site(rel, node.lineno, owner, "a dict display key", *_py_shape(v)))
        elif isinstance(node, ast.Call):
            for kw in node.keywords:
                if kw.arg == MEMBER:
                    sites.append(Site(rel, node.lineno, owner, "a keyword argument", *_py_shape(kw.value)))
            if (isinstance(node.func, ast.Attribute) and node.func.attr == "setdefault" and len(node.args) > 1
                    and _is_member_key(node.args[0])):
                sites.append(Site(rel, node.lineno, owner, "a setdefault", *_py_shape(node.args[1])))
        elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for t in targets:
                if ((isinstance(t, ast.Subscript) and _is_member_key(_subscript_key(t)))
                        or (isinstance(t, ast.Attribute) and t.attr == MEMBER)):
                    shape = _py_shape(node.value) if node.value is not None else ("built elsewhere", "an annotation without a value")
                    sites.append(Site(rel, node.lineno, owner, "an assignment to the member", *shape))
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings:
            strings.append((node.lineno, owner, node.value))
        stack.extend((child, inner) for child in ast.iter_child_nodes(node))
    return sites, strings


# ---- the JavaScript reader: sites by a member-write pattern over comment-stripped code ---------------------------------

def js_code(src):
    """Source with its comments blanked (a block comment to spaces, its line breaks kept; a line comment to its end, a `//`
    inside a string or after a colon kept), the allowlist module's reader, so a member named in prose is not a writer."""
    src = re.sub(r"/\*.*?\*/", lambda m: re.sub(r"[^\n]", " ", m.group(0)), src, flags=re.S)
    return re.sub(r"(^|[^:\"'`\\])//[^\n]*", r"\1", src)


def shell_code(src):
    """A shell script's text with each comment tail removed (a `#` at a line's start or after whitespace, to the line's end)."""
    return re.sub(r"(^|\s)#[^\n]*", r"\1", src)


JS_WRITE = re.compile(r"""(?<![\w$.])(?:(?P<q>["'])%s(?P=q)|%s)\s*:(?!:)   # an object literal's member (or a type's: classified below)
                          |\.%s\s*=(?!=)                                    # an attribute write
                          |\[\s*["']%s["']\s*\]\s*=(?!=)                    # an index write
                       """ % (MEMBER, MEMBER, MEMBER, MEMBER), re.X)
SCRIPT_SHAPE = re.compile(r"function\s*\(|=>|\)\s*\{")   # a string constant with any of these is read as script; prose has none
JS_SCALAR = re.compile(r"(true|false|null|undefined|-?\d[\w.]*|\"(?:[^\"\\]|\\.)*\"|'(?:[^'\\]|\\.)*'|`(?:[^`\\]|\\.)*`)")
JS_TYPE = re.compile(r"(boolean|number|string|any|unknown|never)\b\s*[;,}\n]")
JS_OWNER = re.compile(r"""function\s*\*?\s*([\w$]+)\s*\(
                          |(?:^|[;{}\n])\s*(?:export\s+)?(?:const|let|var)\s+([\w$]+)\s*=
                          |(?:^|[;{}\n])\s*(?:(?:public|private|protected|static|async|readonly)\s+)*([\w$]+)\s*\([^()]*\)\s*(?::\s*[^{;=]+?)?\s*\{
                       """, re.X)


def _balanced(code, i):
    """The text of the bracketed literal opening at `i` (braces, brackets and parentheses balanced, strings skipped), or None
    when it does not close."""
    depth, quote, j = 0, "", i
    while j < len(code):
        c = code[j]
        if quote:
            if c == "\\":
                j += 1
            elif c == quote:
                quote = ""
        elif c in "\"'`":
            quote = c
        elif c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
            if depth == 0:
                return code[i:j + 1]
        j += 1
    return None


def _js_keys(body):
    """The top-level member names of an object literal's text, or None when one is a spread or a computed key."""
    keys, inner, i, at_member = [], body[1:-1], 0, True
    while i < len(inner):
        if at_member:
            m = re.match(r"\s*(?:\"([^\"]*)\"|'([^']*)'|([\w$]+))\s*:", inner[i:])
            if m:
                keys.append(m.group(1) or m.group(2) or m.group(3))
                i += m.end()
                at_member = False
                continue
            if re.match(r"\s*$", inner[i:]):
                break
            return None   # a spread, a computed key, a shorthand or a method: not read
        c = inner[i]
        if c in "\"'`":
            lit = re.match(r"%s(?:[^%s\\]|\\.)*%s" % (c, c, c), inner[i:])
            i += lit.end() if lit else 1
        elif c in "([{":
            lit = _balanced(inner, i)
            if lit is None:
                return None
            i += len(lit)
        elif c == ",":
            at_member = True
            i += 1
        else:
            i += 1
    return tuple(keys)


def _js_value(code, i):
    j = i
    while j < len(code) and code[j] in " \t\r\n":
        j += 1
    if j >= len(code):
        return ("built elsewhere", "no value follows")
    if code[j] == "{":
        lit = _balanced(code, j)
        return ("object", _js_keys(lit) if lit else None)
    m = JS_TYPE.match(code, j)
    if m:
        return ("a type member", m.group(1))
    m = JS_SCALAR.match(code, j)
    if m:
        return ("scalar", m.group(1)[:40])
    return ("built elsewhere", re.match(r"[^;\n]{0,60}", code[j:]).group(0).strip())


def _js_owner(code, pos):
    name = "<script>"
    for m in JS_OWNER.finditer(code, 0, pos):
        name = m.group(1) or m.group(2) or m.group(3) or name
    return name


def js_sites(rel, code, line0=1, owner=None):
    """The member writes in comment-stripped JavaScript or TypeScript text, each classified by the value it writes; a type
    member (`capped: boolean`) is classified and dropped, since it writes nothing. `line0` and `owner` place a string constant's
    text inside its Python module."""
    out = []
    for m in JS_WRITE.finditer(code):
        kind, detail = _js_value(code, m.end())
        if kind == "a type member":
            continue
        form = "an object literal member" if m.group(0).rstrip().endswith(":") else (
            "an index write" if m.group(0).lstrip().startswith("[") else "an attribute write")
        line = line0 + code.count("\n", 0, m.start())
        out.append(Site(rel, line, owner if owner is not None else _js_owner(code, m.start()), form, kind, detail))
    return out


def script_strings(strings):
    """The string constants of a Python module that name the member and have the shape of script: the pane shim's JavaScript is
    one; a message that says a thing is capped is not."""
    return [(line, owner, text) for line, owner, text in strings if MEMBER in text and SCRIPT_SHAPE.search(text)]


@functools.lru_cache(maxsize=None)
def census():
    """Every write of the member in the tree, as Site objects: the kernel's Python by syntax, its string constants and the page
    bundles' sources by the pattern, the shell scripts under bin/ by the pattern over their comment-stripped text."""
    out = []
    for p in python_files():
        with open(p, encoding="utf-8") as f:
            src = f.read()
        sites, strings = py_sites(p, src)
        out.extend(sites)
        for line, owner, text in script_strings(strings):
            out.extend(js_sites(_rel(p), js_code(text), line, owner))
    for p in script_files():
        with open(p, encoding="utf-8") as f:
            out.extend(js_sites(_rel(p), js_code(f.read())))
    for p in shell_files():
        with open(p, encoding="utf-8", errors="replace") as f:
            out.extend(js_sites(_rel(p), shell_code(f.read())))
    return tuple(sorted(out, key=lambda s: (s.file, s.line)))


# ---- the drives: each writer run with nothing to drop and with keys dropped --------------------------------------------

def _rec(data, what="minute", surface="perf"):
    return {"t": 1700000000, "wid": WID, "surface": surface, "what": what, "reconnect": False, "data": data}


def drive_client_diag_line():
    """kernel/kernel.py _client_diag_line, driven below the admit as the writer of the field: (label, the row it stored, the
    road) for a row under the bound, rows over the bound that the ladder returns under it by dropping one key and two, a row
    over the bound with none of the ladder's keys on it (the empty-list road: nothing to drop), a row still over the bound
    once all five ladder keys are gone, and two rows that are not minute rows."""
    wide_map = {"h%d" % i: 100000000 + i for i in range(2000)}   # 2000 positions at nine digits, over the bound on its own
    wide_frames = {"type%03d" % i: {"n": 12, "ms_sum": 340.5, "ms_max": 88.1, "n16": 5, "n100": 1, "hist": [i % 14] * 14} for i in range(260)}
    long_text = "x" * (km.CLIENT_DIAG_ROW_MAX + 1)   # a value the admit's scrub would have cut; below it, a key the ladder never drops
    cases = [
        ("a minute row under the bound", _rec(dict(MINUTE)), "nothing to drop"),
        ("a minute row over the bound through its map, which the ladder drops first", _rec(dict(MINUTE, wsBytesByHost=wide_map)), "keys dropped"),
        ("a minute row over the bound through its map and its frames, two keys dropped", _rec(dict(MINUTE, wsBytesByHost=wide_map, frames=wide_frames)), "keys dropped"),
        ("a minute row over the bound with none of the ladder's keys on it", _rec({"app": "chat", "dom": 1, "ua": long_text}), "nothing to drop"),
        ("a minute row over the bound with every ladder key on it and still over once all five are gone", _rec(dict(MINUTE, wsBytesByHost={"h1": 1}, ua=long_text)), "every key dropped and still over"),
        ("a slowframe row over the bound", _rec({"app": "chat", "type": long_text}, what="slowframe"), "not a minute row"),
        ("a row of another surface over the bound", _rec({"k": long_text}, what="stale", surface="shim"), "not a minute row"),
    ]
    out = []
    for label, rec, road in cases:
        with contextlib.redirect_stderr(io.StringIO()):   # the writer's once-per-surface stderr line is not this module's subject
            line = km._client_diag_line(rec)
        out.append((label, json.loads(line), road))
    return out


DRIVES = {KERNEL_WRITER: drive_client_diag_line}

OWED = ("the reader case declined on 2026-09-21 (bin/romp perf client, tests/romp-perf-client.bats: a capped object naming no key is "
        "counted as a shed row and names nothing) is now owed")


class CappedShape(unittest.TestCase):
    def test_every_writer_of_the_member_has_a_drive_and_none_emits_a_capped_object_naming_no_key(self):
        sites = census()
        self.assertTrue(sites, "the rig: the census read no write of `%s` in the tree, and the kernel writes the marker; a reader that sees "
                               "nothing pins nothing" % MEMBER)
        writers = {s.writer for s in sites}
        self.assertIn(KERNEL_WRITER, writers, "the rig: the census does not see the kernel's writer %s:%s among %s" % (KERNEL_WRITER + (sorted(writers),)))
        for s in sites:
            if s.kind == "scalar":
                continue   # a scalar cannot carry a dropped list: classified, no drive owed (anchor-map.ts's TRIM_STATS counter is one)
            self.assertIn(s.writer, DRIVES, "%r writes a `%s` member: a writer this pin has no drive for. Add a drive to DRIVES keyed %r "
                                            "that runs it with nothing to drop and with keys dropped; if it can emit capped {bytes, "
                                            "dropped: []} (bytes with an empty dropped list), %s" % (s, MEMBER, s.writer, OWED))
        objects, markers, absent = 0, 0, 0   # what the drives REACHED: the rig below reads these, not the drives' labels
        for key, drive in sorted(DRIVES.items()):
            self.assertIn(key, writers, "a drive whose writer the census no longer finds: %s; the writer moved or was renamed, so key the "
                                        "drive on its new home" % (key,))
            who = "%s %s" % key
            for label, row, road in drive():
                data = row.get("data")
                capped = data.get(MEMBER) if isinstance(data, dict) else None
                if capped is None:
                    absent += 1
                    continue
                if isinstance(capped, dict):
                    self.assertEqual(row.get("what"), "minute", "%s emitted on '%s' a capped object %s on a row that is not a minute row: "
                                                                "the reader counts it under neither shape, a silent loss" % (who, label, json.dumps(capped)[:120]))
                    dropped = capped.get("dropped")
                    self.assertTrue(isinstance(dropped, list) and len(dropped) > 0 and all(isinstance(k, str) and k for k in dropped),
                                    "%s emitted on '%s' capped %s: bytes with an EMPTY dropped list (or none), the shape this module pins as "
                                    "absent; %s" % (who, label, json.dumps(capped)[:160], OWED))
                    objects += 1
                else:
                    self.assertIs(capped, True, "%s emitted on '%s' a capped of %r, a shape neither reader knows" % (who, label, capped))
                    self.assertNotIn("dropped", data, "%s emitted on '%s' the whole-row marker beside a dropped list" % (who, label))
                    if row.get("what") == "minute":
                        markers += 1
        # the arms ran, read from what was emitted and not from the drives' labels: a zero over drives that never reached the
        # writer's choice of shape would prove nothing
        self.assertGreater(markers, 0, "the rig: no minute-row drive reached the whole-row marker, so the empty-list road (nothing the ladder can drop, "
                                       "or every key dropped and the row still over) did not run")
        self.assertGreater(objects, 0, "the rig: no drive produced a capped object with keys dropped, so the discriminating arm did not run")
        self.assertGreater(absent, 0, "the rig: no drive produced a row without the member")

    def test_the_census_reads_the_kernel_writers_shed_shape_and_every_site_of_it_readably(self):
        # the census's read of the writer that exists, by property: at least one site writes an object literal whose keys are bytes and
        # dropped, and every site of that writer is an object literal or a scalar (a value built elsewhere would be one this module
        # cannot see the keys of)
        mine = [s for s in census() if s.writer == KERNEL_WRITER]
        self.assertTrue(any(s.kind == "object" and s.detail is not None and set(s.detail) >= {"bytes", "dropped"} for s in mine),
                        "the census reads %s's sites as %r: none is an object literal with bytes and dropped, so the shed shape moved or the "
                        "reader lost it" % (KERNEL_WRITER[1], mine))
        for s in mine:
            self.assertIn(s.kind, ("object", "scalar"), "%r: a value the census cannot read, so its shape must be driven, not inferred" % s)

    def test_the_readers_read_every_write_form_and_not_a_local_variable_or_a_comment(self):
        # probes assembled at run time (the census reads tests/ in no population, but a literal here would still be a copy of the shape)
        M = MEMBER
        py = "\n".join([
            "import json",
            "def w1(rec, n, shed):",
            "    return dict(rec, data=dict(rec['data'], %s={'bytes': n, 'dropped': shed}))" % M,
            "def w2(n):",
            "    marker = {'%s': True, 'bytes': n}" % M,
            "    return marker",
            "def w3(d, other):",
            "    d['%s'] = {'bytes': 1, 'dropped': []}" % M,
            "    d.setdefault('%s', 2)" % M,
            "    d['%s'] = other" % M,
            "class K:",
            "    def m(self, o):",
            "        o.%s = True" % M,
            "def not_a_writer(rows):",
            "    %s = {r for r in rows}   # a local variable, not a member" % M,
            "    return %s" % M,
            "SHIM = 'x.onmessage=function(){post({%s:{bytes:1,dropped:[]}})}'" % M,
            "def doc():",
            "    \"\"\"prose quoting the shim: x.onmessage=function(){post({%s:{bytes:1,dropped:[]}})}\"\"\"" % M,
            "    return 1",
            "MSG = 'Bodies are %s: a full traceback stays in the log'" % M,
        ])
        sites, strings = py_sites("probe.py", py)
        got = sorted((s.function, s.form, s.kind, s.detail) for s in sites)
        self.assertEqual(got, sorted([
            ("w1", "a keyword argument", "object", ("bytes", "dropped")),
            ("w2", "a dict display key", "scalar", "True"),
            ("w3", "an assignment to the member", "object", ("bytes", "dropped")),
            ("w3", "a setdefault", "scalar", "2"),
            ("w3", "an assignment to the member", "built elsewhere", "other"),
            ("K.m", "an assignment to the member", "scalar", "True"),
        ]), "the Python reader's forms")
        self.assertNotIn("not_a_writer", [s.function for s in sites], "a local variable of the member's name is not a write")
        texts = [t for _, _, t in strings]
        for head in ("x.onmessage=function()", "Bodies are %s: a" % M):
            self.assertTrue(any(t.startswith(head) for t in texts), "the rig: the string constant opening %r reaches the scan" % head)
        self.assertFalse(any(t.startswith("prose quoting the shim") for t in texts), "a docstring does not reach the scan: the reader drops it as prose")
        shim = [js_sites("probe.py", js_code(t), ln, owner) for ln, owner, t in script_strings(strings)]
        self.assertEqual([(s.function, s.form, s.kind, s.detail) for group in shim for s in group],
                         [("<module>", "an object literal member", "object", ("bytes", "dropped"))],
                         "the shim road: a string constant's JavaScript is read; a docstring quoting it is prose, and a message with no "
                         "script shape is prose")
        js = "\n".join([
            "// prose: %s: { bytes: 1, dropped: [] } is a comment" % M,
            "/* %s: { bytes: 1 } in a block comment */" % M,
            "interface Row { %s: boolean; }" % M,
            "function a(n: number) { return { app: 'x', %s: { bytes: n, dropped: [] } }; }" % M,
            "const b = (row: any) => { row.%s = true; row['%s'] = { bytes: 2, dropped: ['frames'] }; };" % (M, M),
            "function c(row: any) { const %s = { bytes: 3 }; return row.%s; }" % (M, M),
            "function d(row: any) { row.%s = built(); }" % M,
        ])
        got = [(s.line, s.function, s.form, s.kind, s.detail) for s in js_sites("probe.ts", js_code(js))]
        self.assertEqual(got, [
            (4, "a", "an object literal member", "object", ("bytes", "dropped")),
            (5, "b", "an attribute write", "scalar", "true"),
            (5, "b", "an index write", "object", ("bytes", "dropped")),
            (7, "d", "an attribute write", "built elsewhere", "built()"),
        ], "the JavaScript reader's forms: a comment and a type member are not writes, a local variable is not, and a read is not")
        sh = js_sites("probe.sh", shell_code("# %s: { bytes: 1 } in a comment line\nrow['%s'] = { bytes: 1, dropped: [] }  # a tail: %s: 1\n" % (M, M, M)))
        self.assertEqual([(s.line, s.form, s.kind, s.detail) for s in sh], [(2, "an index write", "object", ("bytes", "dropped"))],
                         "the shell reader drops comment tails and reads the rest")


if __name__ == "__main__":
    unittest.main()
