#!/usr/bin/env python3
"""No served driver writes to its stdout except through tests/lab_result.cjs (2026-10-06).

THE CLASS. A served driver (a node program a module in CI's served-pages job runs) hands its record to pytest. When it
printed the record whole on stdout, the record reached pytest through one write to a pipe, and a write to a full or
non-blocking pipe puts in what the pipe has room for: the tail was lost without a throw once the record outgrew the room
(tests/lab_result.cjs says why, and tests/test_lab_result_pipe_served.py shows the cut at 8 KiB). How big a record grows
is a property of the tree, not of the driver, so the class is closed by a rule over writers, not by a list of drivers
measured small.

THE RULE. A served driver's record goes to pytest through tests/lab_result.cjs: writeResult writes it to the file the
Python side names and prints one short RESULT: line naming that file. Nothing else in a served driver writes to the
driver's stdout. That makes "what counts as the record" a question the census never has to answer: it refuses every
direct write to stdout, whatever the write carries. The only lines a driver may still print besides the helper's RESULT:
line are progress lines through the helper's writeLine (an upper-case tag other than RESULT and one line of at most 200
characters, such as KPID:<pid>), which tests/lab_result.cjs enforces when it runs. Diagnostics go to stderr.

THE POPULATION, derived from the tree, never listed:
  modules       the files CI's served step names (its globs and its by-file names, read from .github/workflows/ci.yml by
                tests/test_served_labs_under_ci.py's readers). A glob matching nothing, a named file absent or an empty
                population fails the run.
  texts         every str constant of those modules (the ast module's reading, so escapes are decoded), docstrings left
                out: the inline drivers, their shared heads, the node -e texts, and every other string.
  driver files  every .mjs, .cjs or .js file under tests/ whose name a module's str constant holds, and every file under
                tests/ such a file imports or requires by a relative path, read whole; tests/lab_result.cjs itself is
                the helper and is not read.

THE RULES.
  W  No text and no driver file writes to the process's stdout. Each is read with its comment lines blanked (a line
     whose first non-blank characters are //, /*, or * followed by a space), so a call split across lines is still
     read; a comment at the end of a code line is read with the code. The forms, each keyed on its spelling
     (WRITE_FORMS):
       console         a console member other than error, warn, trace and assert (those four write to stderr; log,
                       info, debug, dir, table and the rest write to stdout), or a computed member
       console-bound   the console object bound to another name, or the console module loaded
       process.stdout  process.stdout by any member access, optional chaining and a string key included
       stdout-bound    stdout taken from process by destructuring, or from the process module
       fd-1            an fs write call (writeSync, write, writeFile, appendFile and their kin) whose first argument is 1
       fd-1-option     a stream opened on fd 1 ({fd: 1})
       stdout-path     a path that names the process's stdout (/dev/stdout, /dev/fd/1, /proc/<pid>/fd/1)
       child-inherits  a child process whose stdout is the driver's (stdio "inherit", or 1, "inherit" or process as its
                       second stdio entry), or child_process.fork, which hands the child the parent's stdout
       writeAll        the helper's raw writer, exported for the helper's own pins; a driver calls writeResult or
                       writeLine
  H  Every browser driver hands its record through the helper. A browser driver is a module-level text that launches a
     browser (a code line holding `.launch(`, comment lines blanked as for W) and is no other text's head (a text
     another text is built on with +: DRIVER = DRIVER_HEAD + r"..."), the texts composed by + and by str.replace across
     the population (names from this module, names a module imports from another served module, attributes of a served
     module imported by alias; a replacement whose value is known only at run time, such as json.dumps(REPLY), is read
     as a neutral 0, so it can neither supply a call nor hide one the text has); it must call writeResult in its code.
     So must every driver file a served module names. "In its code": the text is read with its comments, string
     literals, template literals' text and regex literals blanked by a small lexer (_js_code; a template's ${...} is
     code), so writeResult named in a comment or a string does not count.
  F  Every module that runs node hands a record through the helper: a module that holds a node argv (the str constant
     "node"), a browser driver or a driver file holds a text or names a file that calls writeResult in its code, read
     as for H.
  R  No module reads a record off a driver's stream itself, keyed on two spellings: no str constant beginning RESULT is
     the argument of a string search (startswith, split, partition, find, index, removeprefix and their kin) or the
     left side of an `in` test, and no json.loads or json.load is handed an expression that reads a stdout or stderr
     attribute or name. The record is read by tests/lab_result.py's read alone. A diagnostic that prints a record it
     already read (print("RESULT:" + json.dumps(r), file=sys.stderr)) is not a read and passes.

THE EXCEPTIONS, each with its structural reason (never a size), and each held to still excusing something:
  HELPER        tests/lab_result.cjs: the one writer the rule sends every record through.
  EXEMPT_VALUES the browser-install probes, excused by their exact text: not drivers.
  EXEMPT_NAMED  the two texts of the helper's own pipe pins, excused by module and name.
  NOT_RUN       a JavaScript sample that a module hands to a parser as data and node never runs (H).
  NO_RECORD     a module whose own node runs hand pytest no record (F).

WHAT IT CANNOT SEE (stated, not closed; each planted in StatedBounds and shown to pass): a form split across two
constants or built from strings at run time (process["std" + "out"]); fd 1 held in a name (const o = 1;
fs.writeSync(o, s)); a write in a module the driver imports from outside tests/ or from a module outside the served step
(none at this tree: every driver text a served module runs is defined in a served module); a record handed through
stderr (console.error), which carries the diagnostics every module prints in its failure text; a browser driver
written inside a function or a container (a tuple, a dict), or composed by any operator but + or any method but
str.replace (str.format, an f-string, %, a join), or by a str.replace whose old string or count is known only at run
time (W still reads its constants; F still holds its module); and, for H and F, a regex literal right after ), ] or },
which the lexer reads as a division, so the regex's text is read as code. Each W form is keyed on the spelling above,
not on what a write does: a road to stdout that none of the spellings names is outside W, and tests/lab_result.cjs's
header says why there is no other road a driver needs.

Synthetic: reads the tree only; no node, no browser. Planted texts are assembled in this file and in temporary trees.
"""
import ast
import glob
import os
import re
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import parse_cache                                  # noqa: E402  one parse per file per process, shared with the other AST censuses
import test_served_labs_under_ci as _ci             # noqa: E402  the served step's readers (the module, so its tests are not collected twice)

HELPER = "lab_result.cjs"
JS_SUFFIXES = (".mjs", ".cjs", ".js")
FILE_NAME = re.compile(r"([\w-]+(?:\.[\w-]+)*\.(?:mjs|cjs|js))\b")
REL_IMPORT = re.compile(r"(?:\bfrom\s*|\bimport\s*\(?\s*|\brequire\s*\(\s*)[\"'](\.{1,2}/[^\"']+)[\"']")
COMMENT_LINE = re.compile(r"^\s*(?://|/\*|\*(?:\s|/|$))")
LAUNCH = re.compile(r"\.launch\s*\(")
WRITE_RESULT = re.compile(r"\bwriteResult\s*\(")
_G = r"(?:(?:globalThis|global)\s*\.\s*)?"
_Q = "[\"'`]"

WRITE_FORMS = (
    ("console", re.compile(r"(?<![\w$.])" + _G + r"console\s*(?:\??\.(?!(?:error|warn|trace|assert)\b)[A-Za-z_$]|\[)")),
    ("console-bound", re.compile(r"=\s*" + _G + r"console\s*(?:[;,)}\]]|$)|(?:\brequire\s*\(\s*|\bimport\s*\(\s*|\bfrom\s+)"
                                 + _Q + r"(?:node:)?console" + _Q, re.M)),
    ("process.stdout", re.compile(r"\bprocess\s*(?:\??\.\s*stdout\b|\[\s*" + _Q + "stdout)")),
    ("stdout-bound", re.compile(r"\bstdout\b.*(?:=\s*" + _G + r"process\s*(?:[;,)}\]]|$)|(?:\brequire\s*\(\s*|\bimport\s*\(\s*|"
                                r"\bfrom\s+)" + _Q + r"(?:node:)?process" + _Q + ")", re.M)),
    ("fd-1", re.compile(r"\b(?:writeSync|write|writev|writevSync|writeFile|writeFileSync|appendFile|appendFileSync|"
                        r"writeString|writeBuffer|writeBuffers)\s*\(\s*1\s*[,)]")),
    ("fd-1-option", re.compile(r"\bfd\s*:\s*1\b")),
    ("stdout-path", re.compile(r"/dev/stdout\b|/dev/fd/1\b|/proc/[^/\s\"'`]+/fd/1\b")),
    ("child-inherits", re.compile(r"\bstdio\s*:\s*(?:" + _Q + "inherit" + _Q + r"|\[\s*[^,\[\]]*,\s*(?:1|" + _Q + "inherit"
                                  + _Q + r"|process\b)\s*[,\]])|\bfork\s*\(")),
    ("writeAll", re.compile(r"\bwriteAll\b")),
)
FORM_NAMES = tuple(name for name, _ in WRITE_FORMS)

# W's exceptions by exact value: the browser-install probe. Not a driver: it hands pytest no record and launches no
# browser; it prints the one path the browser library reports for its executable, which the module only tests with
# os.path.exists, and it ends without process.exit, so node drains the stream write before the process ends. The second
# spelling takes the engine's name from argv for the modules that probe more than one engine.
EXEMPT_VALUES = {
    "const p=require(process.argv[1]);process.stdout.write(p.chromium.executablePath())":
        "the browser-install probe: prints one executable path, which the module tests with os.path.exists; no record",
    "const p=require(process.argv[1]);process.stdout.write(p[process.argv[2]].executablePath())":
        "the browser-install probe for an engine named on argv: one executable path, no record",
}
# W's exceptions by module and module-level name: the helper's own pipe pins, which must write to stdout to be pins
EXEMPT_NAMED = {
    ("test_lab_result_pipe_served.py", "OLD_FORM"):
        "the class's red-before, planted on purpose: the whole record in one fs.writeSync, which the pin shows cut",
    ("test_lab_result_pipe_served.py", "DRIVER"):
        "the pins of writeAll itself, which drive the helper's raw writer through a full pipe",
}
# H's exceptions by module and name: texts that launch a browser in their source but are data, never run by node
NOT_RUN = {
    ("test_federated_linkdrop_driver_parsed_served.py", "CONVERGENCE_JS"):
        "a JavaScript sample the module hands to its parse helper as data; node never runs it",
}
# F's exceptions by module: a module whose own node runs hand pytest no record
NO_RECORD = {
    "test_live_paused_window_browser.py":
        "its own two tests run DRIVER_HEAD cut before the browser launch, with an empty cfg, and assert the engine refusal "
        "on exit 1 and stderr: no record, nothing on stdout. The drivers built on DRIVER_HEAD are texts of the modules "
        "that import it, and are read there",
}

SEARCH_METHODS = {"startswith", "endswith", "split", "rsplit", "partition", "rpartition", "find", "rfind", "index",
                  "rindex", "count", "removeprefix"}
STREAMS = {"stdout", "stderr"}


def _js_files(tests):
    """{basename: [path, ...]} for every .mjs, .cjs and .js file under tests/, at any depth (node_modules left out)."""
    out = {}
    for d, subdirs, files in os.walk(tests):
        subdirs[:] = [s for s in subdirs if s != "node_modules"]
        for f in files:
            if f.endswith(JS_SUFFIXES):
                out.setdefault(f, []).append(os.path.join(d, f))
    return out


def _docstrings(tree):
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and n.body:
            b = n.body[0]
            if isinstance(b, ast.Expr) and isinstance(b.value, ast.Constant) and isinstance(b.value.value, str):
                out.add(id(b.value))
    return out


def _module_names(tree):
    """{id(constant): name} for each module-level `NAME = "<str constant>"`, the key EXEMPT_NAMED and NOT_RUN read."""
    out = {}
    for n in tree.body:
        if (isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)
                and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str)):
            out[id(n.value)] = n.targets[0].id
    return out


def texts(tree):
    """[(line, value, name)] for every str constant of `tree` but its docstrings; name is the module-level name a
    constant is the whole value of, else None."""
    ds, names = _docstrings(tree), _module_names(tree)
    return [(n.lineno, n.value, names.get(id(n))) for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in ds]


def population(root=ROOT, globs=None, files=None):
    """{"modules": {name: (text, tree)}, "files": {relpath under tests/: (text, [namers])}} under root. `globs` and
    `files` default to CI's served step's; a glob matching nothing, a named file absent or an empty result raises."""
    tests = os.path.join(root, "tests")
    globs = _ci.ci_served_globs() if globs is None else globs
    files = _ci.ci_served_files() if files is None else files
    if not globs and not files:
        raise AssertionError("the served step names no glob and no file: the census has nothing to read")
    names = set()
    for g in globs:
        hits = glob.glob(os.path.join(root, g))
        if not hits:
            raise AssertionError("the served step's glob %s matches no file under %s" % (g, root))
        names |= {os.path.basename(h) for h in hits}
    for f in files:
        if not os.path.isfile(os.path.join(root, f)):
            raise AssertionError("the served step names %s and it is absent under %s" % (f, root))
        names.add(os.path.basename(f))
    if not names:
        raise AssertionError("the served population under %s is empty" % root)
    modules = {n: parse_cache.source_and_tree(os.path.join(tests, n)) for n in sorted(names)}
    js = _js_files(tests)
    todo = []
    for n, (_, tree) in modules.items():
        for _, value, _ in texts(tree):
            for base in FILE_NAME.findall(value):
                todo.extend((p, n) for p in js.get(base, ()))
    driver_files = {}
    while todo:
        path, namer = todo.pop()
        rel = os.path.relpath(path, tests)
        if os.path.basename(path) == HELPER:
            continue
        if rel in driver_files:
            driver_files[rel][1].add(namer)
            continue
        with open(path, encoding="utf-8") as f:
            text = f.read()
        driver_files[rel] = (text, {namer})
        for spec in REL_IMPORT.findall(text):
            dep = os.path.normpath(os.path.join(os.path.dirname(path), spec))
            for cand in (dep,) + tuple(dep + s for s in JS_SUFFIXES):
                if os.path.isfile(cand) and cand.startswith(tests + os.sep):
                    todo.append((cand, rel))
                    break
    return {"modules": modules, "files": {k: (t, sorted(v)) for k, (t, v) in sorted(driver_files.items())}}


def _blank_comments(text):
    return "\n".join("" if COMMENT_LINE.match(ln) else ln for ln in text.split("\n"))


_JS_TOKEN = re.compile(r"\s+|//|/\*|[\"'`]|/|[A-Za-z_$\u0080-\uffff][\w$\u0080-\uffff]*|\.?\d[\w.]*|.", re.S)
# after these words a / opens a regex literal; after any other word, a number, a literal, ) ] or } it divides
_REGEX_AFTER = {"return", "typeof", "instanceof", "in", "of", "new", "delete", "void", "throw", "case", "do", "else",
                "yield", "await"}


def _js_code(text):
    """`text` with every comment, string literal, template literal's text and regex literal blanked to spaces (line
    feeds kept), so what is left is the code node runs; a template's ${...} is code and is read as code. A small
    lexer, not a parser: a / right after ), ] or } is read as a division (a regex literal there is read as code), a /
    whose regex would cross a line end is a division, and a string left open ends at its line's end."""
    out = list(text)
    n = len(text)

    def blank(a, b):
        for k in range(a, min(b, n)):
            if out[k] != "\n":
                out[k] = " "

    def template_text(start, j):
        """Blank from `start` through the template text from j: to its closing backtick ((end, False)) or through the
        next ${ ((end, True))."""
        while j < n:
            c = text[j]
            if c == "\\":
                j += 2
            elif c == "`":
                blank(start, j + 1)
                return j + 1, False
            elif text.startswith("${", j):
                blank(start, j + 2)
                return j + 2, True
            else:
                j += 1
        blank(start, n)
        return n, False

    i, depth, subst, prev = 0, 0, [], ""
    if text.startswith("#!"):
        j = text.find("\n")
        i = n if j < 0 else j
        blank(0, i)
    while i < n:
        tok = _JS_TOKEN.match(text, i).group()
        c = tok[0]
        if c.isspace():
            i += len(tok)
        elif tok == "//":
            j = text.find("\n", i)
            j = n if j < 0 else j
            blank(i, j)
            i = j
        elif tok == "/*":
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            blank(i, j)
            i = j
        elif c in "'\"":
            j = i + 1
            while j < n and text[j] not in (c, "\n"):
                j += 2 if text[j] == "\\" else 1
            j = j + 1 if j < n and text[j] == c else min(j, n)
            blank(i, j)
            i, prev = j, "lit"
        elif c == "`":
            i, opened = template_text(i, i + 1)
            if opened:
                subst.append(depth)
            prev = "{" if opened else "lit"
        elif c == "}" and subst and subst[-1] == depth:
            subst.pop()
            i, opened = template_text(i, i + 1)
            if opened:
                subst.append(depth)
            prev = "{" if opened else "lit"
        elif c == "/":
            word = prev[2:] if prev.startswith("w:") else None
            regex = prev not in ("lit", "num", ")", "]", "}") and (word is None or word in _REGEX_AFTER)
            j, cls = i + 1, False
            while regex and j < n:
                d = text[j]
                if d == "\n":
                    break
                if d == "\\":
                    j += 2
                    continue
                if cls:
                    cls = d != "]"
                elif d == "[":
                    cls = True
                elif d == "/":
                    break
                j += 1
            if regex and j < n and text[j] == "/":
                j += 1
                while j < n and (text[j].isalnum() or text[j] in "_$"):
                    j += 1
                blank(i, j)
                i, prev = j, "lit"
            else:
                i, prev = i + 1, "/"
        else:
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
            prev = ("w:" + tok if (c.isalpha() or c in "_$" or ord(c) >= 0x80)
                    else "num" if (c.isdigit() or (c == "." and len(tok) > 1)) else tok)
            i += len(tok)
    return "".join(out)


def scan_text(text):
    """[(line offset, form, the line)] for every W form in `text`, its comment lines blanked."""
    code = _blank_comments(text)
    lines = text.split("\n")
    out = []
    for name, rx in WRITE_FORMS:
        for m in rx.finditer(code):
            k = code.count("\n", 0, m.start())
            out.append((k, name, lines[k].strip()[:160]))
    return sorted(out)


def _calls_write_result(text):
    """True when `text` calls writeResult in its code: comments, strings, templates' text and regexes blanked."""
    return bool(WRITE_RESULT.search(text)) and bool(WRITE_RESULT.search(_js_code(text)))


def _launches(text):
    return bool(LAUNCH.search(_blank_comments(text)))


def _imports(tree, modules):
    """(alias -> module file, name -> (module file, its name)) for the imports of served modules in `tree`: `import x`,
    `import x as y`, `import tests.x as y`, `from x import n`, `from tests.x import n` and `from tests import x`."""
    alias, frm = {}, {}
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                f = a.name.split(".")[-1] + ".py"
                if f in modules and (a.asname or "." not in a.name):
                    alias[a.asname or a.name] = f
        elif isinstance(n, ast.ImportFrom) and n.module and not n.level:
            if n.module == "tests":
                for a in n.names:
                    if a.name + ".py" in modules:
                        alias[a.asname or a.name] = a.name + ".py"
                continue
            f = n.module.split(".")[-1] + ".py"
            if f in modules:
                for a in n.names:
                    frm[a.asname or a.name] = (f, a.name)
    return alias, frm


def _ref(node, m, alias, frm):
    """The (module, name) a Name or alias.attr refers to, or None."""
    if isinstance(node, ast.Name):
        return frm.get(node.id, (m, node.id))
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id in alias:
        return (alias[node.value.id], node.attr)
    return None


# what H reads in place of a str.replace value known only at run time: a number, so it opens no string or comment and
# holds no call
RUNTIME_VALUE = "0"


def composed(modules):
    """({(module, name): text} for every module-level text composed of str constants and refs by + and by
    str.replace, {(module, name) used as an operand of + anywhere in the population}): the browser drivers and their
    heads. A replace whose old string is not a known text, or whose count is not a constant int, is not composed; a
    replacement value that is not a known text is read as RUNTIME_VALUE."""
    imps = {m: _imports(tree, modules) for m, (_, tree) in modules.items()}
    env, busy = {}, set()

    def build(m):
        if m in busy:
            return
        busy.add(m)
        alias, frm = imps[m]
        local = {}

        def ev(e):
            if isinstance(e, ast.Constant) and isinstance(e.value, str):
                return e.value
            if isinstance(e, ast.BinOp) and isinstance(e.op, ast.Add):
                a, b = ev(e.left), ev(e.right)
                return a + b if isinstance(a, str) and isinstance(b, str) else None
            if (isinstance(e, ast.Call) and isinstance(e.func, ast.Attribute) and e.func.attr == "replace"
                    and len(e.args) in (2, 3) and not e.keywords):
                s, old, count = ev(e.func.value), ev(e.args[0]), -1
                if len(e.args) == 3:
                    a = e.args[2]
                    count = a.value if isinstance(a, ast.Constant) and type(a.value) is int else None
                if not (isinstance(s, str) and isinstance(old, str) and count is not None):
                    return None
                new = ev(e.args[1])
                return s.replace(old, new if isinstance(new, str) else RUNTIME_VALUE, count)
            r = _ref(e, m, alias, frm)
            if r is None:
                return None
            if r[0] == m:
                return local.get(r[1])
            build(r[0])
            return env.get(r)

        for n in modules[m][1].body:
            if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
                v = ev(n.value)
                if isinstance(v, str):
                    local[n.targets[0].id] = v
                    env[(m, n.targets[0].id)] = v

    for m in modules:
        build(m)
    operands = set()
    for m, (_, tree) in modules.items():
        alias, frm = imps[m]
        for n in ast.walk(tree):
            if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add):
                for side in (n.left, n.right):
                    r = _ref(side, m, alias, frm)
                    if r is not None:
                        operands.add(r)
    return env, operands


def _reads_stream(node):
    return any((isinstance(x, ast.Attribute) and x.attr in STREAMS) or (isinstance(x, ast.Name) and x.id in STREAMS)
               for x in ast.walk(node))


def _result_const(node):
    return isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.startswith("RESULT")


def reader_offences(name, tree):
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
            if n.func.attr in SEARCH_METHODS and any(_result_const(a) for a in n.args):
                out.append((name, n.lineno, "a hand search for the RESULT: line (%s)" % n.func.attr))
            if (n.func.attr in ("loads", "load") and isinstance(n.func.value, ast.Name) and n.func.value.id == "json"
                    and any(_reads_stream(a) for a in n.args)):
                out.append((name, n.lineno, "json.%s of a driver's stream" % n.func.attr))
        elif isinstance(n, ast.Compare) and _result_const(n.left) and any(isinstance(o, (ast.In, ast.NotIn)) for o in n.ops):
            out.append((name, n.lineno, "a hand search for the RESULT: line (in)"))
    return out


def census(root=ROOT, globs=None, files=None):
    """Every rule's offences over the population under root, the exceptions each excused, and the counts."""
    pop = population(root, globs, files)
    modules, dfiles = pop["modules"], pop["files"]
    out = {"W": [], "H": [], "F": [], "R": [], "used": set(), "modules": sorted(modules), "files": sorted(dfiles)}
    record_texts = {}
    for m, (_, tree) in modules.items():
        n_wr = 0
        for line, value, cname in texts(tree):
            hits = scan_text(value)
            if hits and value in EXEMPT_VALUES:
                out["used"].add(("value", value))
                hits = []
            if hits and (m, cname) in EXEMPT_NAMED:
                out["used"].add(("named", (m, cname)))
                hits = []
            out["W"].extend((m, line + k, "%s: %s" % (form, snippet)) for k, form, snippet in hits)
            n_wr += _calls_write_result(value)
        record_texts[m] = n_wr
        out["R"].extend(reader_offences(m, tree))
    for rel, (text, namers) in dfiles.items():
        out["W"].extend(("tests/" + rel, k + 1, "%s: %s" % (form, snippet)) for k, form, snippet in scan_text(text))
        if any(n in modules for n in namers) and not _calls_write_result(text):
            out["H"].append(("tests/" + rel, 1, "a driver file a served module runs that never calls writeResult"))
    env, operands = composed(modules)
    drivers = {}
    for key, text in sorted(env.items()):
        if key in operands or not _launches(text):
            continue
        if key in NOT_RUN:
            out["used"].add(("not-run", key))
            continue
        drivers[key] = text
        if not _calls_write_result(text):
            out["H"].append((key[0], 0, "%s launches a browser and never calls writeResult" % key[1]))
    named_by = {}
    for rel, (_, namers) in dfiles.items():
        for n in namers:
            if n in modules:
                named_by.setdefault(n, []).append(rel)
    for m, (_, tree) in modules.items():
        runs_node = (any(v == "node" for _, v, _ in texts(tree)) or m in named_by or any(k[0] == m for k in drivers))
        hands = record_texts[m] or any(_calls_write_result(dfiles[rel][0]) for rel in named_by.get(m, ()))
        if runs_node and not hands:
            if m in NO_RECORD:
                out["used"].add(("no-record", m))
            else:
                out["F"].append((m, 0, "runs node and hands no record through tests/lab_result.cjs (no writeResult in "
                                       "its texts or its driver files)"))
    out["drivers"] = sorted(drivers)
    out["record_texts"] = sum(record_texts.values())
    return out


def _census_here():
    return parse_cache.derived(("lab_result_census", ROOT), lambda: census())


def _lines(offences, cap=40):
    shown = ["  %s:%d %s" % o for o in offences[:cap]]
    if len(offences) > cap:
        shown.append("  ... and %d more" % (len(offences) - cap))
    return "\n".join(shown)


def _tree(test, files):
    """A temporary root holding tests/<name> for each (name, text); removed when the test ends."""
    root = tempfile.mkdtemp(prefix="lab-result-census-")
    test.addCleanup(shutil.rmtree, root, True)
    for name, text in files.items():
        path = os.path.join(root, "tests", name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
    return root


# the three spellings of the class, each a whole-record write planted beside a real driver's lab.writeResult call
WHOLE_RECORD = {
    "writeSync": 'fs.writeSync(1, "RESULT:" + JSON.stringify(out) + "\\n");',
    "stdout.write": 'process.stdout.write("RESULT:" + JSON.stringify(out) + "\\n", () => process.exit(0));',
    "console.log": 'console.log("RESULT:" + JSON.stringify(out));',
}
WHOLE_RECORD_FORM = {"writeSync": "fd-1", "stdout.write": "process.stdout", "console.log": "console"}
HELPER_CALL = re.compile(r"\blab\.writeResult\s*\(")


def _beside_the_helper_call(text, line):
    """`text` with `line` on a line of its own just before the line of its last lab.writeResult( call."""
    k = text.rfind("\n", 0, list(HELPER_CALL.finditer(text))[-1].start()) + 1
    return text[:k] + line + "\n" + text[k:]

# one line per W form, each refused alone (the form named), beside lines that name a form only in a comment or a string
# the reader never runs, which pass
FORM_PLANTS = {
    "console": ["console.info(JSON.stringify(out));", "console.table(out);", "console?.log(out);", 'console["log"](out);',
                "globalThis.console.debug(out);"],
    "console-bound": ["const say = console;", 'const { log } = require("console");', 'import { log } from "node:console";'],
    "process.stdout": ["process.stdout.write(JSON.stringify(out));", "fs.writeSync(process.stdout.fd, s);",
                       'process["stdout"].write(s);', "const o = process.stdout;", "process?.stdout.write(s);"],
    "stdout-bound": ["const { stdout } = process;", 'import { stdout } from "node:process";',
                     'const { stdout: o } = require("process");'],
    "fd-1": ["fs.writeSync(1, JSON.stringify(out));", "fs.writeSync(\n  1, s);", 'require("fs").writeFileSync(1, s);',
             "fs.write(1, s, () => {});"],
    "fd-1-option": ['const w = fs.createWriteStream("", { fd: 1 });'],
    "stdout-path": ['fs.writeFileSync("/dev/stdout", s);', 'fs.appendFileSync("/proc/self/fd/1", s);',
                    'fs.writeFileSync("/dev/fd/1", s);'],
    "child-inherits": ['spawn("node", ["dump.js"], { stdio: "inherit" });', 'spawnSync("node", [f], { stdio: [0, 1, 2] });',
                       'spawn("node", [f], { stdio: ["ignore", "inherit", "pipe"] });', 'fork("dump.js");'],
    "writeAll": ["lab.writeAll(1, JSON.stringify(out));", "const w = lab.writeAll;"],
}
CLEAN_LINES = [
    "// console.log(out) was the old road; fs.writeSync(1, s) too",
    "  * process.stdout.write(s) in a block comment's body",
    "/* fs.writeSync(1, s) */",
    'console.error("browser-launch-failed: " + e);',
    "console.warn(s); console.trace(); console.assert(ok, s);",
    'page.on("console", (msg) => out.console.push(msg.text()));',
    "lab.writeResult(cfg, out);",
    'lab.writeLine("KPID", k.pid);',
    'spawn(cmd, args, { stdio: ["ignore", fs.openSync(log, "a"), fs.openSync(log, "a")] });',
    'spawn(cmd, args, { stdio: ["ignore", "pipe", "inherit"] });',
    'fs.writeSync(fd, s); fs.writeFileSync(path, s);',
]


class ServedDriverWrites(unittest.TestCase):
    maxDiff = None

    def test_the_population_is_the_served_step_and_holds_drivers(self):
        got = _census_here()
        want = set()
        for g in _ci.ci_served_globs():
            want |= {os.path.basename(h) for h in glob.glob(os.path.join(ROOT, g))}
        want |= {os.path.basename(f) for f in _ci.ci_served_files()}
        self.assertTrue(want, "CI's served step names no module")
        self.assertEqual(got["modules"], sorted(want), "the census reads exactly the modules CI's served step runs")
        self.assertTrue(got["drivers"], "the census found no browser driver in %d modules: it reads nothing, so it proves "
                                        "nothing" % len(got["modules"]))
        self.assertTrue(got["files"], "the census found no driver file a served module names")
        self.assertNotIn(HELPER, got["files"], "the helper is the writer, not a driver")
        self.assertGreaterEqual(got["record_texts"], len({k[0] for k in got["drivers"]}),
                                "every module with a browser driver holds a text that calls writeResult")
        # every module-level text built by str.replace on a str constant that launches a browser is one of H's drivers
        replaced = set()
        for m in got["modules"]:
            for n in parse_cache.source_and_tree(os.path.join(HERE, m))[1].body:
                if not (isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)):
                    continue
                v = n.value
                while isinstance(v, ast.Call) and isinstance(v.func, ast.Attribute) and v.func.attr == "replace":
                    v = v.func.value
                if v is not n.value and isinstance(v, ast.Constant) and isinstance(v.value, str) and _launches(v.value):
                    replaced.add((m, n.targets[0].id))
        self.assertTrue(replaced, "no served module builds a browser driver by str.replace any more: this check reads "
                                  "nothing at this tree, so drop it (Plants holds the reading)")
        self.assertEqual(sorted(replaced - set(got["drivers"])), [], "a driver built by str.replace that H does not read")
        print("LABRESULT modules=%d browser drivers=%d (in %d modules, %d built by str.replace) driver files=%d texts "
              "calling writeResult=%d" % (len(got["modules"]), len(got["drivers"]), len({k[0] for k in got["drivers"]}),
                                         len(replaced), len(got["files"]), got["record_texts"]), file=sys.stderr)

    def _rule(self, rule, what):
        got = _census_here()
        self.assertEqual(got[rule], [], "%d %s (%d served modules, %d driver files; tests/lab_result.cjs is the helper):\n%s"
                         % (len(got[rule]), what, len(got["modules"]), len(got["files"]), _lines(got[rule])))

    def test_no_served_driver_writes_to_stdout_but_through_the_helper(self):
        self._rule("W", "direct writes to stdout in served drivers, keyed on the spellings in WRITE_FORMS (hand the record "
                        "to lab.writeResult(cfg, record), a progress line to lab.writeLine(TAG, value), a diagnostic to "
                        "console.error)")

    def test_every_browser_driver_and_driver_file_calls_write_result(self):
        self._rule("H", "browser drivers or driver files that never call writeResult (tests/lab_result.cjs's header "
                        "says how each kind of driver loads it)")

    def test_every_module_that_runs_node_hands_a_record_through_the_helper(self):
        self._rule("F", "modules that run node and hand no record through tests/lab_result.cjs (or, if a module's runs "
                        "hand no record by design, list it in NO_RECORD with the reason)")

    def test_no_served_module_reads_a_record_off_a_drivers_stream(self):
        self._rule("R", "hand reads of a driver's stream, keyed on a RESULT str constant in a string search and on "
                        "json.load(s) of a stdout or stderr read (read the record with lab_result.read(p, tgt))")

    def test_each_exception_still_excuses_something(self):
        got = _census_here()
        used = got["used"]
        stale = ([("value", v) for v in EXEMPT_VALUES if ("value", v) not in used]
                 + [("named", k) for k in EXEMPT_NAMED if ("named", k) not in used]
                 + [("not-run", k) for k in NOT_RUN if ("not-run", k) not in used]
                 + [("no-record", m) for m in NO_RECORD if ("no-record", m) not in used])
        self.assertEqual(stale, [], "an exception that excuses nothing at this tree: drop it, so the list stays the set "
                                    "the rules need")
        for reasons in (EXEMPT_VALUES, EXEMPT_NAMED, NOT_RUN, NO_RECORD):
            for key, why in reasons.items():
                self.assertTrue(why.strip(), "an exception carries its reason: %r" % (key,))
                self.assertIsNone(re.search(r"\d+\s*(?:bytes?|KiB|KB|B)\b", why), "a reason is structural, never a size")


class Plants(unittest.TestCase):
    maxDiff = None

    def _real(self):
        """Three real served drivers from the tree, as they are: an inline text (tests/test_chat_split_served.py's
        DRIVER), an ES module driver file (tests/keyboard_gap_browser.mjs) and a CommonJS one
        (tests/spend_modal_headless.js), each clean as it stands and calling lab.writeResult in its code."""
        tree = parse_cache.source_and_tree(os.path.join(HERE, "test_chat_split_served.py"))[1]
        inline = [v for _, v, n in texts(tree) if n == "DRIVER"]
        self.assertEqual(len(inline), 1, "tests/test_chat_split_served.py holds its DRIVER as one module-level text")
        subjects = {"inline": inline[0]}
        for where, name in (("mjs", "keyboard_gap_browser.mjs"), ("cjs", "spend_modal_headless.js")):
            with open(os.path.join(HERE, name), encoding="utf-8") as f:
                subjects[where] = f.read()
        for where, text in subjects.items():
            self.assertTrue(HELPER_CALL.search(text), "%s calls lab.writeResult, where the plants go" % where)
            self.assertTrue(_calls_write_result(text), "%s calls writeResult in its code" % where)
            self.assertEqual(scan_text(text), [], "%s is clean as it stands, so a red below is the plant's" % where)
        return subjects

    def _census_of(self, where, text):
        """The census over a temporary tree whose one served module runs `text` as `where` runs it: an inline DRIVER
        text, or the driver file the module names (by the real file's name), beside a stub helper."""
        if where == "inline":
            files = {"test_planted_served.py": "DRIVER = %r\nN = \"node\"\n" % text}
        else:
            name = {"mjs": "keyboard_gap_browser.mjs", "cjs": "spend_modal_headless.js"}[where]
            files = {"test_planted_served.py": "ARGV = [\"node\", %r]\n" % name, name: text,
                     "lab_result.cjs": "module.exports = {};\n"}
        return census(_tree(self, files), ["tests/test_*_served.py"], [])

    def test_a_whole_record_write_in_each_spelling_is_refused_in_three_real_drivers(self):
        for where, text in self._real().items():
            for spelling, line in WHOLE_RECORD.items():
                with self.subTest(driver=where, spelling=spelling):
                    hits = scan_text(_beside_the_helper_call(text, line))
                    self.assertEqual([h[1] for h in hits], [WHOLE_RECORD_FORM[spelling]], hits)
                    self.assertIn(line.strip()[:40], hits[0][2])

    def test_a_driver_off_the_helper_that_names_write_result_only_where_node_never_runs_it_is_refused(self):
        # each real driver taken off the helper: its lab.writeResult calls become a writer of its own (the record to
        # the file with no nonce), and writeResult( stays only in a comment, a string, a template's text or a regex
        for where, text in self._real().items():
            with self.subTest(driver=where, shape="the driver as it is"):
                got = self._census_of(where, text)
                self.assertEqual((got["W"], got["H"], got["F"]), ([], [], []),
                                 "the real driver passes, so a red below is the plant's")
                self.assertTrue(got["drivers"] or got["files"], "the census read the driver")
            off = OWN_WRITER + "\n" + HELPER_CALL.sub("writeOwnFile(", text)
            for shape, line in NAMED_NOT_CALLED.items():
                with self.subTest(driver=where, shape=shape):
                    planted = off + "\n" + line + "\n"
                    if line:
                        self.assertTrue(WRITE_RESULT.search(planted),
                                        "the plant spells writeResult(, so the red is the lexer's reading, not a missing name")
                    got = self._census_of(where, planted)
                    self.assertEqual(got["W"], [], got["W"])
                    want_h = ["test_planted_served.py"] if where == "inline" else ["tests/" + self._file(where)]
                    self.assertEqual([o[0] for o in got["H"]], want_h, got["H"])
                    self.assertEqual([o[0] for o in got["F"]], ["test_planted_served.py"], got["F"])

    @staticmethod
    def _file(where):
        return {"mjs": "keyboard_gap_browser.mjs", "cjs": "spend_modal_headless.js"}[where]

    def test_the_lexer_reads_a_call_in_code_and_not_in_a_comment_a_string_a_template_or_a_regex(self):
        for src in LEXER_CALLS:
            with self.subTest(called=src):
                code = _js_code(src)
                self.assertEqual((len(code), code.count("\n")), (len(src), src.count("\n")), "positions and lines kept")
                self.assertTrue(_calls_write_result(src), code)
        for src in LEXER_NOT_CALLS:
            with self.subTest(not_called=src):
                self.assertTrue(WRITE_RESULT.search(src), "the sample spells writeResult(")
                self.assertFalse(_calls_write_result(src), _js_code(src))

    def test_a_driver_composed_by_str_replace_is_read_by_h(self):
        launch = "const browser = await chromium.launch();\\n"
        mod = ("import json\nimport os\nREPLY = {\"a\": 1}\nSID = \"s-1\"\n"
               "GOOD = \"" + launch + "const reply = REPLY_PLACEHOLDER;\\nlab.writeResult(cfg, out);\\n\"" +
               ".replace(\"REPLY_PLACEHOLDER\", json.dumps(REPLY)).replace(\"SID_PLACEHOLDER\", SID)\n"
               "ONCE = \"" + launch + "lab.writeResult(cfg, out);\\nlab.writeResult(cfg, out);\\n\"" +
               ".replace(\"lab.writeResult(cfg, out);\", \"\", 1)\n"
               "BAD = \"" + launch + "const reply = REPLY_PLACEHOLDER;\\n\".replace(\"REPLY_PLACEHOLDER\", json.dumps(REPLY))\n"
               "CUT = \"" + launch + "lab.writeResult(cfg, out);\\n\".replace(\"lab.writeResult(cfg, out);\", \"\")\n"
               "HID = \"" + launch + "CALL\\n\".replace(\"CALL\", json.dumps(\"lab.writeResult(cfg, out);\"))\n"
               "SWAP = \"" + launch + "lab.writeResult(cfg, out);\\n\".replace(\"lab.writeResult(cfg, out);\", json.dumps(REPLY))\n"
               "N = \"node\"\n")
        got = census(_tree(self, {"test_replace_served.py": mod}), ["tests/test_*_served.py"], [])
        self.assertEqual([k[1] for k in got["drivers"]], ["BAD", "CUT", "GOOD", "HID", "ONCE", "SWAP"],
                         "each text composed by str.replace is a driver")
        self.assertEqual(sorted(o[2].split()[0] for o in got["H"]), ["BAD", "CUT", "HID", "SWAP"],
                         "the replaced text is what H reads: a call the replace removes is gone, a count of 1 leaves the "
                         "second call, and a value known only at run time neither supplies a call nor leaves the one it "
                         "replaced")
        self.assertEqual(got["F"], [])

    def test_the_census_names_a_planted_write_in_a_served_module_and_in_a_driver_file_it_names(self):
        for spelling, line in WHOLE_RECORD.items():
            with self.subTest(spelling=spelling):
                drv = ("const lab = require(cfg.resultLib);\nconst browser = await chromium.launch();\n"
                       "const out = { rows: [] };\n" + line + "\nawait browser.close();\n")
                mod = ('DRIVER = r"""\n' + drv + '"""\nARGV = ["node", "planted_browser.mjs"]\n')
                root = _tree(self, {"test_planted_served.py": mod,
                                    "planted_browser.mjs": 'import lab from "./lab_result.cjs";\n' + line + "\n",
                                    "lab_result.cjs": "module.exports = {};\n"})
                got = census(root, ["tests/test_*_served.py"], [])
                self.assertEqual(got["modules"], ["test_planted_served.py"])
                self.assertEqual(got["files"], ["planted_browser.mjs"], "the driver file is read; the helper is not")
                self.assertEqual(sorted((o[0], o[1]) for o in got["W"]),
                                 [("test_planted_served.py", 5), ("tests/planted_browser.mjs", 2)], got["W"])
                self.assertEqual(sorted(o[0] for o in got["H"]), ["test_planted_served.py", "tests/planted_browser.mjs"],
                                 "neither the planted driver nor the file calls writeResult")

    def test_each_write_form_is_refused_alone_and_the_clean_lines_pass(self):
        for form, lines in FORM_PLANTS.items():
            for line in lines:
                with self.subTest(form=form, line=line):
                    self.assertIn(form, [h[1] for h in scan_text(line)])
        self.assertEqual(sorted(FORM_PLANTS), sorted(FORM_NAMES), "a plant for every form")
        for line in CLEAN_LINES:
            with self.subTest(clean=line):
                self.assertEqual(scan_text(line), [])

    def test_a_probe_is_excused_by_its_exact_text_only(self):
        probe = next(iter(EXEMPT_VALUES))
        mod = "PROBE = %r\nOFF = %r\n" % (probe, probe.replace("chromium", "firefox"))
        root = _tree(self, {"test_probe_served.py": mod + 'DRIVER = "lab.writeResult(cfg, out)"\nN = "node"\n'})
        got = census(root, ["tests/test_*_served.py"], [])
        self.assertEqual([(o[0], o[1]) for o in got["W"]], [("test_probe_served.py", 2)], "the exact probe passes; a "
                                                                                          "probe one word off is refused")
        self.assertIn(("value", probe), got["used"])

    def test_a_docstring_or_comment_naming_a_form_passes(self):
        mod = ('"""A served module whose prose names console.log(x) and fs.writeSync(1, s)."""\n'
               'def drive():\n    """It used to print with process.stdout.write(s)."""\n'
               'DRIVER = "// console.log(out) was the old road\\nlab.writeResult(cfg, out);\\n"\nN = "node"\n')
        got = census(_tree(self, {"test_prose_served.py": mod}), ["tests/test_*_served.py"], [])
        self.assertEqual(got["W"], [])
        self.assertEqual(got["F"], [])

    def test_a_driver_set_that_shrinks_to_empty_is_red(self):
        # a module that runs node and whose texts and files no longer call writeResult is named by F, its browser driver
        # by H; a glob that matches nothing, a by-file name that is absent and an empty step fail before any rule runs
        mod = 'DRIVER = "const b = await chromium.launch();\\nawait b.close();\\n"\nN = "node"\n'
        got = census(_tree(self, {"test_empty_served.py": mod}), ["tests/test_*_served.py"], [])
        self.assertEqual([o[0] for o in got["F"]], ["test_empty_served.py"])
        self.assertEqual([o[0] for o in got["H"]], ["test_empty_served.py"])
        self.assertEqual(got["drivers"], [("test_empty_served.py", "DRIVER")])
        root = _tree(self, {"test_other.py": "X = 1\n"})
        with self.assertRaisesRegex(AssertionError, "matches no file"):
            census(root, ["tests/test_*_served.py"], [])
        with self.assertRaisesRegex(AssertionError, "is absent"):
            census(root, [], ["tests/test_gone_served.py"])
        with self.assertRaisesRegex(AssertionError, "names no glob and no file"):
            census(root, [], [])

    def test_a_head_is_not_a_driver_and_the_text_built_on_it_is(self):
        head = ('HEAD = "const lab = require(cfg.resultLib);\\nconst browser = await chromium.launch();\\n"\n'
                'N = "node"\n')
        mod2 = ("import test_head_served as h\nfrom test_head_served import HEAD\n"
                'ONE = h.HEAD + "lab.writeResult(cfg, out);\\n"\nTWO = HEAD + "await browser.close();\\n"\nN = "node"\n')
        got = census(_tree(self, {"test_head_served.py": head, "test_body_served.py": mod2}), ["tests/test_*_served.py"], [])
        self.assertEqual(got["drivers"], [("test_body_served.py", "ONE"), ("test_body_served.py", "TWO")])
        self.assertEqual([(o[0], o[2].split()[0]) for o in got["H"]], [("test_body_served.py", "TWO")],
                         "the driver built on the head that never calls writeResult is named; the head is not a driver")
        self.assertEqual([o[0] for o in got["F"]], ["test_head_served.py"],
                         "the head's own module runs node and holds no record of its own (the live window lab's shape)")

    def test_the_reader_rule_refuses_a_hand_parse_and_passes_a_diagnostic(self):
        refused = ['line = [l for l in p.stdout.split("\\n") if l.startswith("RESULT:")][0]\n',
                   'r = json.loads(p.stdout.strip().split("\\n")[-1])\n',
                   'r = json.loads(p.stdout.split("RESULT:", 1)[1])\n',
                   'ok = "RESULT: ok" in p.stdout\n',
                   'r = json.loads(stdout)\n']
        for src in refused:
            with self.subTest(refused=src):
                self.assertTrue(reader_offences("planted.py", ast.parse(src)), src)
        clean = ['print("RESULT:" + json.dumps(r), file=sys.stderr)\n', 'r = lab_result.read(p, tgt)\n',
                 'cfg = json.loads(open(path).read())\n', 'k = [l for l in p.stdout.split("\\n") if l.startswith("KPID:")]\n']
        for src in clean:
            with self.subTest(clean=src):
                self.assertEqual(reader_offences("planted.py", ast.parse(src)), [], src)

    def test_a_file_a_driver_file_imports_is_read_by_w(self):
        root = _tree(self, {"test_files_served.py": 'ARGV = ["node", "top_browser.mjs"]\n',
                            "top_browser.mjs": 'import lab from "./lab_result.cjs";\nimport { dump } from "./util/dump.mjs";\n'
                                               "lab.writeResult(cfg, out);\n",
                            "util/dump.mjs": "export function dump(o) { console.log(JSON.stringify(o)); }\n",
                            "lab_result.cjs": "module.exports = {};\n"})
        got = census(root, ["tests/test_*_served.py"], [])
        self.assertEqual(got["files"], ["top_browser.mjs", os.path.join("util", "dump.mjs")])
        self.assertEqual([(o[0], o[1]) for o in got["W"]], [("tests/" + os.path.join("util", "dump.mjs"), 1)])


# a driver taken off the helper names writeResult( only where node never runs it
OWN_WRITER = 'const writeOwnFile = (t, r) => require("fs").writeFileSync(t.resultPath, JSON.stringify(r));'
NAMED_NOT_CALLED = {
    "nowhere": "",
    "a comment line": "// lab.writeResult(cfg, out);",
    "a trailing comment": "writeOwnFile(cfg, out); // was lab.writeResult(cfg, out)",
    "a block comment": "writeOwnFile(cfg, out); /* writeResult( */",
    "a string": 'console.error("skipping lab.writeResult(cfg, out)");',
    "a template literal": "console.error(`skipping lab.writeResult(${cfg.resultPath}, out)`);",
    "a regex literal": "const was = /lab.writeResult(cfg, out)/;",
}
# the lexer's reading, each sample spelling writeResult(: called in code, and named where node never runs it
LEXER_CALLS = [
    "lab.writeResult(cfg, out);",
    "x = a / b / c; lab.writeResult(cfg, out); // c / d",
    "x = 1 / 2; lab.writeResult(cfg, out); y = 3 / 4;",
    "x = f(a) / 2; lab.writeResult(cfg, out); y = 3 / 4;",
    "y = g[0] / 3; lab.writeResult(cfg, out); z = a / b;",
    'const u = "http://127.0.0.1/"; lab.writeResult(cfg, out);',
    "s = s.replace(/\"/g, ''); lab.writeResult(cfg, out);",
    "const t = `${lab.writeResult(cfg, out)}`;",
    "const t = `a ${`b ${c}`} d`; lab.writeResult(cfg, out);",
    "const t = `${ ({a: 1}, lab.writeResult(cfg, out)) }`;",
    "const o = { a: { b: 1 } }; if (x) { y(); } lab.writeResult(cfg, out);",
    'const q = "a \\" b"; lab.writeResult(cfg, out);',
    "#!/usr/bin/env node `\nlab.writeResult(cfg, out);",
    'const s = "a string left open\nlab.writeResult(cfg, out);',
    "return /'/.test(s) && lab.writeResult(cfg, out);",
    "/* a */ lab.writeResult(cfg, out); /* b */",
]
LEXER_NOT_CALLS = [
    "// lab.writeResult(cfg, out);",
    "x(); // lab.writeResult(cfg, out)",
    "/* lab.writeResult(cfg, out) */",
    "/*\n lab.writeResult(cfg, out)\n*/",
    'console.error("lab.writeResult(cfg, out)");',
    "console.error('lab.writeResult(cfg, out)');",
    "console.error(`lab.writeResult(cfg, out)`);",
    "console.error(`${x} lab.writeResult(cfg, out)`);",
    'const q = "a \\" lab.writeResult(cfg, out)";',
    "const re = /lab.writeResult(cfg)/g;",
    "const re = /[/]lab.writeResult(cfg)/;",
    'const s = "a string left open lab.writeResult(cfg, out)\nnext();',
]


class StatedBounds(unittest.TestCase):
    """The roads the docstring says W does not read, each planted and shown to pass, so the disclosure is held to the
    census's behaviour: widening a form moves one of these, and then the docstring with it."""

    def test_the_stated_bounds_pass(self):
        bounds = {
            "a form split across two constants": 'A = "fs.write"\nB = "Sync(1, s);"\n',
            "a member built from strings": 'D = "process[\\"std\\" + \\"out\\"].write(s);"\n',
            "fd 1 held in a name": 'D = "const o = 1;\\nfs.writeSync(o, s);"\n',
            "a record on stderr": 'D = "console.error(JSON.stringify(out));"\n',
        }
        for what, mod in bounds.items():
            with self.subTest(bound=what):
                got = census(_tree(self, {"test_bound_served.py": mod}), ["tests/test_*_served.py"], [])
                self.assertEqual(got["W"], [], what)

    def test_a_text_from_a_module_outside_the_served_step_is_not_read(self):
        root = _tree(self, {"heads.py": 'HEAD = "console.log(JSON.stringify(out));"\n',
                            "test_uses_served.py": 'from heads import HEAD\nDRIVER = HEAD + "lab.writeResult(cfg, out);"\n'
                                                   'N = "node"\n'})
        got = census(root, ["tests/test_*_served.py"], [])
        self.assertEqual(got["modules"], ["test_uses_served.py"])
        self.assertEqual(got["W"], [], "the helper module's write is outside the read, as stated")

    def test_a_browser_driver_composed_another_way_is_outside_h_but_its_module_is_held_by_f(self):
        shapes = {
            "str.format": 'DRIVER = "const b = await chromium.launch();\\n{}\\n".format("await b.close();")\n',
            "an f-string": 'X = "await b.close();"\nDRIVER = f"const b = await chromium.launch();\\n{X}\\n"\n',
            "%": 'DRIVER = "const b = await chromium.launch();\\n%s\\n" % "await b.close();"\n',
            "a join": 'DRIVER = "\\n".join(["const b = await chromium.launch();", "await b.close();"])\n',
            "a tuple": 'DRIVERS = ("const b = await chromium.launch();\\nawait b.close();\\n",)\n',
            "a dict": 'DRIVERS = {"one": "const b = await chromium.launch();\\nawait b.close();\\n"}\n',
            "a replace whose old string is known at run time":
                'import os\nDRIVER = "const b = await chromium.launch();\\nX\\n".replace(os.sep, "/")\n',
            "a replace whose count is known at run time":
                'import os\nDRIVER = "const b = await chromium.launch();\\nX\\n".replace("X", "", len(os.sep))\n',
        }
        for what, mod in shapes.items():
            with self.subTest(bound=what):
                got = census(_tree(self, {"test_bound_served.py": mod + 'N = "node"\n'}), ["tests/test_*_served.py"], [])
                self.assertEqual((got["drivers"], got["H"]), ([], []), what)
                self.assertEqual([o[0] for o in got["F"]], ["test_bound_served.py"], what)

    def test_a_regex_literal_right_after_a_paren_is_read_as_code_by_h_and_f(self):
        mod = 'DRIVER = "const b = await chromium.launch();\\nif (ok) /lab.writeResult(cfg)/.test(s);\\n"\nN = "node"\n'
        got = census(_tree(self, {"test_bound_served.py": mod}), ["tests/test_*_served.py"], [])
        self.assertEqual(got["drivers"], [("test_bound_served.py", "DRIVER")])
        self.assertEqual((got["H"], got["F"]), ([], []), "the regex after ) is read as a division, as stated")

    def test_a_browser_driver_built_in_a_function_is_outside_h_but_its_module_is_held_by_f(self):
        mod = ('def drive():\n    text = "const b = await chromium.launch();\\nawait b.close();\\n"\n    return text\n'
               'N = "node"\n')
        got = census(_tree(self, {"test_fn_served.py": mod}), ["tests/test_*_served.py"], [])
        self.assertEqual(got["drivers"], [])
        self.assertEqual(got["H"], [])
        self.assertEqual([o[0] for o in got["F"]], ["test_fn_served.py"])


if __name__ == "__main__":
    unittest.main()
