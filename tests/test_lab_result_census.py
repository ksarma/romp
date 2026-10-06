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
     browser (a code line holding `.launch(`) and is no other text's head (a text another text is built on with +:
     DRIVER = DRIVER_HEAD + r"..."), the texts composed by + across the population (names from this module, names a
     module imports from another served module, attributes of a served module imported by alias); it must call
     writeResult. So must every driver file a served module names.
  F  Every module that runs node hands a record through the helper: a module that holds a node argv (the str constant
     "node"), a browser driver or a driver file holds a text or names a file that calls writeResult.
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
stderr (console.error), which carries the diagnostics every module prints in its failure text; and a browser driver
written inside a function or composed by any operator but + (W still reads its constants; F still holds its module).
Each W form is keyed on the spelling above, not on what a write does: a road to stdout that none of the spellings
names is outside W, and tests/lab_result.cjs's header says why there is no other road a driver needs.

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
    return bool(WRITE_RESULT.search(_blank_comments(text)))


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


def composed(modules):
    """({(module, name): text} for every module-level text composed of str constants and refs by +, {(module, name)
    used as an operand of + anywhere in the population}): the browser drivers and their heads."""
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


# the three spellings of the class, each a whole-record write in the place a driver's lab.writeResult(cfg, out) stood
WHOLE_RECORD = {
    "writeSync": 'fs.writeSync(1, "RESULT:" + JSON.stringify(out) + "\\n");',
    "stdout.write": 'process.stdout.write("RESULT:" + JSON.stringify(out) + "\\n", () => process.exit(0));',
    "console.log": 'console.log("RESULT:" + JSON.stringify(out));',
}
WHOLE_RECORD_FORM = {"writeSync": "fd-1", "stdout.write": "process.stdout", "console.log": "console"}
ANCHOR = "lab.writeResult(cfg, out);"

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
        print("LABRESULT modules=%d browser drivers=%d (in %d modules) driver files=%d texts calling writeResult=%d"
              % (len(got["modules"]), len(got["drivers"]), len({k[0] for k in got["drivers"]}), len(got["files"]),
                 got["record_texts"]), file=sys.stderr)

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
        """Two real served drivers from the tree, as they are: an inline text (tests/test_chat_split_served.py's
        DRIVER) and an ES module driver file (tests/keyboard_gap_browser.mjs), each holding the anchor once."""
        tree = parse_cache.source_and_tree(os.path.join(HERE, "test_chat_split_served.py"))[1]
        inline = [v for _, v, n in texts(tree) if n == "DRIVER"]
        self.assertEqual(len(inline), 1, "tests/test_chat_split_served.py holds its DRIVER as one module-level text")
        with open(os.path.join(HERE, "keyboard_gap_browser.mjs"), encoding="utf-8") as f:
            mjs = f.read()
        subjects = {"inline": inline[0], "mjs": mjs}
        for where, text in subjects.items():
            self.assertEqual(text.count(ANCHOR), 1, "%s holds %r once, where the plant goes" % (where, ANCHOR))
            self.assertEqual(scan_text(text), [], "%s is clean as it stands, so a red below is the plant's" % where)
        return subjects

    def test_a_whole_record_write_in_each_spelling_is_refused_in_an_inline_and_an_mjs_driver(self):
        for where, text in self._real().items():
            for spelling, line in WHOLE_RECORD.items():
                with self.subTest(driver=where, spelling=spelling):
                    hits = scan_text(text.replace(ANCHOR, line))
                    self.assertEqual([h[1] for h in hits], [WHOLE_RECORD_FORM[spelling]], hits)
                    self.assertIn(line.strip()[:40], hits[0][2])

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

    def test_a_browser_driver_built_in_a_function_is_outside_h_but_its_module_is_held_by_f(self):
        mod = ('def drive():\n    text = "const b = await chromium.launch();\\nawait b.close();\\n"\n    return text\n'
               'N = "node"\n')
        got = census(_tree(self, {"test_fn_served.py": mod}), ["tests/test_*_served.py"], [])
        self.assertEqual(got["drivers"], [])
        self.assertEqual(got["H"], [])
        self.assertEqual([o[0] for o in got["F"]], ["test_fn_served.py"])


if __name__ == "__main__":
    unittest.main()
