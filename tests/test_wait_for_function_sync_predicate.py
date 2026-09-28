#!/usr/bin/env python3
"""No browser test hands Playwright's waitForFunction an ASYNC predicate (2026-09-22).

The pinned Playwright (vscode-extension/package-lock.json) does not poll an async predicate: its injected poller calls the
predicate once, and an async function returns a promise, a truthy value, so the wait resolves on that first promise whatever
it resolves to. `page.waitForFunction(async () => false, null, { timeout: 3000 })` returns in about 20 ms with the value
false where the synchronous `() => false` times out at 3000 ms (measured on the pinned version). A served-page test that
awaited the kernel's state that way (`async (u) => (await fetch(u)).json().taskTracking === false`, the Task tracking switch
lab) therefore proceeded at once: a wait that enforces nothing is a defect of the lab in its own right, whatever the reads
after it happen to hold (that lab's kernel writes before the gear echoes, so its reads held the value; its CI reds had another
mechanism, a feed frame pruning the marks the lab had seeded, fixed in its driver). The remedy is a poll from the driver (a
bounded loop over the same read, a short pause between polls, the elapsed time recorded: pollKernelSwitch in
tests/test_task_tracking_switch_browser.py), or a synchronous predicate over state the page already holds.

The pin is a text rule over the files that can drive a browser. Its population is a list of directories (population()):
the Python labs and the node scripts under tests/, the webview's tests and helpers under ui/webview/ and the browser tests
beside them at ui/'s top, the extension's sources under vscode-extension/src/, and the lab loops and benches under tools/
and tools/romp-lab/. A census holds that list to the tree: every tracked file that holds the call, prose aside, must be in
it, so a call site in a directory the list does not name fails by path rather than going unread (six tracked files stood
outside the first list on 2026-09-22). Its bound, stated so a reader never takes it for more. It reads:
(1) the first argument of a `waitForFunction(` call, read with brackets and string literals balanced and bared (bare():
leading comments, a `/* */` block or a `//` line, and enclosing parentheses removed to a fixed point, so `/* why */ async
() =>` and `(async () => ...)` are the literal they wrap, while `(a, b) => ...` opens a list and stays whole), that begins
with the `async` keyword (an async arrow or an async function expression); (2) a first argument that is a bare name bound
in the same file to an async function (`const p = async () =>`, `async function p`); (3) a call through a wrapper, a
function defined in the same file whose parameter is that first argument, when a caller in the same file hands the wrapper,
in that parameter's position, an async literal or a name bound to an async function, the handed argument bared the same
way. The wrapper definitions rule (3) reads, each with its parameter list read balanced (a typed parameter such as
`pred: () => boolean` or a defaulted one is read whole): an arrow bound by const, let or var with a parenthesized list or
one bare parameter, a function expression bound the same way, and a function declaration; the form table is a test of this
file, and every shape named here has a planted red. Comment lines (`//`, `#`, `*`) are skipped, so a comment naming the
shape is no offender and a pin in a comment is no cover. Out of its reach, by design, each with its reason: a class or
object-literal method used as the wrapper (its head is none of the four definition forms); a method reference as the
predicate (`waitForFunction(this.ready)`: whether a method is async is not decidable from the call site's text, and a
dotted name has no same-file binding for rule (2) to read); a predicate or wrapper built in another file (the rule reads one
file at a time); a predicate produced by a call (`waitForFunction(make())`: the call's result is not in the text); a name
rebound between its definition and the call (rule (2) reads a binding, not the flow); a regex literal holding an unbalanced
bracket (the scanner skips string and template literals, not regexes). The census that fixed the tree (2026-09-22) read every
identifier-passed and wrapper-passed predicate by hand and found each synchronous; this rule holds that state. This file
plants the shapes it refuses in its own tests, so the walk leaves it out by name. Reads the tree only: no kernel, no
browser, no romp code loaded; the census asks git for the tracked list.
"""
import glob
import os
import re
import subprocess
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SELF = os.path.basename(__file__)
CALL = "waitForFunction("
_LEAD = re.compile(r"^\s*(//|#|\*|/\*)")
_NAME = r"[A-Za-z_$][\w$]*"
# the heads of the wrapper definitions rule (3) reads; the named group that matched says which form. An arrow's or a function
# expression's list opens at the match's last character and is read balanced from there; the bare-parameter arrow carries its
# one name in the match
_DEF = re.compile(r"(?:const|let|var)\s+(?P<bound>%(n)s)\s*=\s*(?:async\s+)?(?:(?P<fexpr>function)\s*\(|\(|(?P<bare>%(n)s)\s*=>)"
                  r"|(?:async\s+)?function\s+(?P<decl>%(n)s)\s*\(" % {"n": _NAME})
_ARROW = re.compile(r"\s*=>")
# files that may quote the call and drive nothing
PROSE = (".md", ".txt", ".rst")


def population():
    """Every file that can drive a browser, by path: the labs and node scripts under tests/, the webview's tests and helpers
    under ui/webview/ and the browser tests at ui/'s top, the extension's sources, the lab loops and benches under tools/ and
    tools/romp-lab/. Sorted, repo-relative; this pin's own file left out. The census test holds this list to the tree."""
    dirs = [HERE, os.path.join(ROOT, "ui"), os.path.join(ROOT, "ui", "webview"), os.path.join(ROOT, "vscode-extension", "src"),
            os.path.join(ROOT, "tools"), os.path.join(ROOT, "tools", "romp-lab")]
    out = set()
    for d in dirs:
        for ext in (".py", ".js", ".mjs", ".cjs", ".ts"):
            for path in glob.glob(os.path.join(d, "*" + ext)):
                if os.path.basename(path) != SELF:
                    out.add(os.path.relpath(path, ROOT))
    return sorted(out)


def tracked_files():
    """Every path git tracks in this checkout, repo-relative. The road when git cannot answer is the precedent's
    (tests/test_entrypoints_executable.py): a loud skip when git is not installed or the tree is no checkout, an error for
    any other exit, so the census never reads an empty list as a clean tree."""
    try:
        proc = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, text=True, timeout=60)
    except FileNotFoundError:
        raise unittest.SkipTest("git is not installed; the census over the tracked files cannot run")
    if proc.returncode != 0:
        if "not a git repository" in proc.stderr:
            raise unittest.SkipTest("not a git checkout (git ls-files exited %d): the census over the tracked files cannot run" % proc.returncode)
        raise AssertionError("git ls-files exited %d in %s, so the census over the tracked files would be disarmed; fix the checkout "
                             "rather than skipping:\n%s" % (proc.returncode, ROOT, proc.stderr.strip()))
    return [p for p in proc.stdout.split("\0") if p]


def _segments(text, open_pos):
    """The top-level, comma-separated segments between the bracket at `open_pos` and its match, and the match's position:
    brackets balanced, string and template literals skipped (their brackets and commas do not count). An unclosed list
    yields its tail and None."""
    segs = []
    depth = 0
    i = seg = open_pos + 1
    n = len(text)
    while i < n:
        c = text[i]
        if c in "'\"`":
            q = c
            i += 1
            while i < n and text[i] != q:
                i += 2 if text[i] == "\\" else 1
        elif c in "([{":
            depth += 1
        elif c in ")]}":
            if depth == 0:
                segs.append(text[seg:i])
                return segs, i
            depth -= 1
        elif c == "," and depth == 0:
            segs.append(text[seg:i])
            seg = i + 1
        i += 1
    segs.append(text[seg:])
    return segs, None


def arguments_of(text, start):
    """The arguments of the call whose opening paren is at `start`, as texts, brackets and string literals balanced."""
    return _segments(text, start)[0]


def first_argument(text, start):
    return arguments_of(text, start)[0]


_LEAD_COMMENT = re.compile(r"\s*(?:/\*.*?\*/\s*|//[^\n]*\n\s*)+", re.S)


def bare(segment):
    """The argument with what stands before the predicate removed, to a fixed point: leading comments (a `/* */` block, a `//`
    line) and enclosing parentheses, so `/* why */ async () => ...` and `(async () => ...)` read as the literal they wrap.
    Enclosing means the parenthesis at the start closes at the segment's last character, read balanced with the arguments'
    scanner: `(a, b) => f()` opens a parameter list, not an enclosure, and is returned whole."""
    s = segment.strip()
    while True:
        m = _LEAD_COMMENT.match(s)
        if m:
            s = s[m.end():]
            continue
        if s.startswith("("):
            _, close = _segments(s, 0)
            if close == len(s) - 1:
                s = s[1:close].strip()
                continue
        return s


def _param_name(segment):
    """The name a parameter segment binds: its leading identifier (`pred: () => boolean` binds pred, `ms = bound(1)` binds
    ms); None for a rest or destructured parameter, which no bare argument name can equal."""
    m = re.match(r"\s*(%s)" % _NAME, segment)
    return m.group(1) if m else None


def wrapper_defs(text):
    """Every function definition rule (3) reads, in text order, as (name, parameter names, end of its head). The forms:
    `const w = [async] (a, b: T = d()) =>`, `const w = [async] a =>`, `const w = [async] function (a, b)`, and
    `[async] function w(a, b)`; let and var like const. A parenthesized expression that is no arrow (`const x = (a + b)`)
    is passed over."""
    out = []
    for m in _DEF.finditer(text):
        name = m.group("bound") or m.group("decl")
        if m.group("bare"):
            out.append((name, [m.group("bare")], m.end()))
            continue
        segs, close = _segments(text, m.end() - 1)
        if close is None:
            continue
        if m.group("bound") and not m.group("fexpr") and not _ARROW.match(text, close + 1):
            continue
        out.append((name, [_param_name(s) for s in segs], close + 1))
    return out


def _is_comment_line(text, pos):
    line_start = text.rfind("\n", 0, pos) + 1
    return bool(_LEAD.match(text[line_start:pos + 1]))


def _bound_to_async(text, name):
    """Rule (2)'s test: `name` is bound somewhere in `text` to an async function."""
    return re.search(r"(?:const|let|var)\s+%s\s*=\s*async\b|async\s+function\s+%s\b" % (re.escape(name), re.escape(name)), text) is not None


def offenders(text, name="<text>"):
    """Every waitForFunction call in `text` whose first argument is asynchronous under the three rules of the module
    docstring (the argument bared first: bare()), as "<name>:<line>: <reason>" strings. Pure over its input, so a planted
    shape is tested without a file."""
    out = []
    defs = wrapper_defs(text)
    wrappers = {}   # wrapper name -> (the parameter it hands waitForFunction, that parameter's index), for rule (3)
    for m in re.finditer(re.escape(CALL), text):
        pos = m.end() - 1
        if _is_comment_line(text, pos):
            continue
        line = text.count("\n", 0, pos) + 1
        arg = bare(first_argument(text, pos))
        if re.match(r"async\b", arg):
            out.append("%s:%d: waitForFunction is handed an async predicate literal" % (name, line))
            continue
        if re.fullmatch(_NAME, arg):
            if _bound_to_async(text, arg):
                out.append("%s:%d: waitForFunction is handed %s, a name bound to an async function" % (name, line, arg))
                continue
            # rule (3): the last function defined before the call whose parameter list names the argument is its wrapper
            for wname, params, end in reversed(defs):
                if end <= pos and arg in params:
                    wrappers[wname] = (arg, params.index(arg))
                    break
    for wname, (param, k) in wrappers.items():
        for cm in re.finditer(r"\b%s\(" % re.escape(wname), text):
            if _is_comment_line(text, cm.end() - 1):
                continue
            args = arguments_of(text, cm.end() - 1)
            if k >= len(args):
                continue
            handed = bare(args[k])
            line = text.count("\n", 0, cm.start()) + 1
            if re.match(r"async\b", handed):
                out.append("%s:%d: %s hands waitForFunction its parameter %s, and this call passes an async predicate literal" % (name, line, wname, param))
            elif re.fullmatch(_NAME, handed) and _bound_to_async(text, handed):
                out.append("%s:%d: %s hands waitForFunction its parameter %s, and this call passes %s, a name bound to an async function" % (name, line, wname, param, handed))
    return out


def pinned_playwright():
    lock = os.path.join(ROOT, "vscode-extension", "package-lock.json")
    try:
        with open(lock, encoding="utf-8") as f:
            m = re.search(r'"node_modules/playwright":\s*\{\s*"version":\s*"([^"]+)"', f.read())
        return m.group(1) if m else "the pinned version"
    except OSError:
        return "the pinned version"


def tree_offenders():
    out = []
    sites = 0
    files = 0
    for rel in population():
        with open(os.path.join(ROOT, rel), encoding="utf-8", errors="replace") as f:
            text = f.read()
        if CALL not in text:
            continue
        files += 1
        sites += text.count(CALL)
        out.extend(offenders(text, rel))
    return out, files, sites


REMEDY = ("Playwright %s (vscode-extension/package-lock.json) does not poll an async waitForFunction predicate: the first call's "
          "promise is truthy, so the wait resolves at once, whatever the promise resolves to, and the reads after it race the state "
          "they wait for. Poll from the driver instead (a bounded loop over the read, a short pause between polls, the elapsed time "
          "recorded; pollKernelSwitch in tests/test_task_tracking_switch_browser.py), or hand it a synchronous predicate over "
          "state the page already holds.")


class WaitForFunctionPredicatesAreSynchronous(unittest.TestCase):
    def test_no_browser_test_hands_waitForFunction_an_async_predicate(self):
        found, files, sites = tree_offenders()
        self.assertEqual(found, [], "\n" + REMEDY % pinned_playwright() + "\n  " + "\n  ".join(found))
        # the walk saw the population: the labs alone hold hundreds of calls, so an empty walk is a broken glob, not a clean tree
        self.assertGreater(files, 100, "the walk found waitForFunction in %d files" % files)
        self.assertGreater(sites, 500, "the walk found %d waitForFunction calls" % sites)

    def test_the_population_holds_the_lab_the_finding_came_from_and_the_named_trees(self):
        pop = population()
        self.assertIn(os.path.join("tests", "test_task_tracking_switch_browser.py"), pop)
        self.assertNotIn(os.path.join("tests", SELF), pop, "this file plants the shape; the walk leaves it out by name")
        for tree in (os.path.join("tests", ""), os.path.join("ui", "webview", ""), os.path.join("vscode-extension", "src", ""),
                     os.path.join("tools", "romp-lab", "")):
            self.assertTrue(any(p.startswith(tree) for p in pop), tree)
        # the six files the first list missed (2026-09-22): one of each directory the list gained
        for rel in (os.path.join("ui", "timeline-tags-scale-browser.test.ts"), os.path.join("tools", "viewer-resize-bench.ts"),
                    os.path.join("tools", "romp-lab", "todos-loop.mjs")):
            self.assertIn(rel, pop)

    def test_every_tracked_file_holding_the_call_is_in_the_population(self):
        # the population is a list of directories, and a call site in a directory the list does not name is a call site the
        # rule never reads: six tracked files stood outside the first list (a browser test at ui/'s top, four lab loops and a
        # bench under tools/). Prose may quote the call and drives nothing; every other tracked file that holds it is read
        pop = set(population())
        outside = []
        unread = []
        holding = 0
        for rel in tracked_files():
            if rel.endswith(PROSE) or os.path.basename(rel) == SELF:
                continue
            path = os.path.join(ROOT, rel)
            if os.path.isdir(path):   # a tracked symlink to a directory holds no text of its own
                continue
            try:
                with open(path, "rb") as f:
                    data = f.read()
            except OSError as e:
                unread.append("%s (%s)" % (rel, e.strerror))
                continue
            if CALL.encode() in data:
                holding += 1
                if rel not in pop:
                    outside.append(rel)
        self.assertEqual(unread, [], "tracked files the census could not read, so their call sites are unknown:\n  " + "\n  ".join(unread))
        self.assertEqual(outside, [], "tracked files holding waitForFunction( in a directory population() does not name; add the directory, "
                         "or name the file under PROSE's reasoning if it drives no browser:\n  " + "\n  ".join(outside))
        self.assertGreater(holding, 100, "the census found %d tracked files holding the call" % holding)

    def test_a_planted_async_arrow_reds(self):
        planted = 'await page.waitForFunction(async (u) => (await (await fetch(u, { cache: "no-store" })).json()).on === false, cfg.v, { timeout: 10000 });\n'
        self.assertEqual(offenders(planted, "x.py"), ["x.py:1: waitForFunction is handed an async predicate literal"])
        self.assertEqual(offenders("await f.waitForFunction(async function () { return false; }, null, { timeout: 5 });", "y.js"),
                         ["y.js:1: waitForFunction is handed an async predicate literal"])

    def test_a_planted_async_arrow_behind_a_leading_comment_or_enclosing_parentheses_reds(self):
        # the shapes the first bound sentence passed over in silence (round 1 of fork PR #904, all-3): a block comment before the
        # predicate, a line comment before it, an async arrow wrapped in parentheses, and both at once; each is the async literal
        red = ["x.py:1: waitForFunction is handed an async predicate literal"]
        self.assertEqual(offenders("await page.waitForFunction(/* the kernel's switch */ async (u) => (await fetch(u)).ok, cfg.v, { timeout: 5 });\n", "x.py"), red)
        self.assertEqual(offenders("await page.waitForFunction(\n  // the kernel's switch\n  async (u) => (await fetch(u)).ok, cfg.v);\n", "x.py"), red)
        self.assertEqual(offenders('await page.waitForFunction((async () => (await fetch("/v")).ok), null, { timeout: 5 });\n', "x.py"), red)
        self.assertEqual(offenders("await page.waitForFunction(/* twice */ ((async () => false)), null);\n", "x.py"), red)
        # the same shapes in a wrapper's predicate position
        planted = ('const waitFn = async (fn, arg, why) => page.waitForFunction(fn, arg, { timeout: T });\n'
                   'await waitFn(/* why */ (async () => true), null, "x");\n')
        self.assertEqual(offenders(planted, "x.py"), ["x.py:2: waitFn hands waitForFunction its parameter fn, and this call passes an async predicate literal"])
        # a parenthesized LIST is no enclosure, and a comment before a synchronous arrow changes nothing: both clean
        self.assertEqual(offenders("await page.waitForFunction((a, b) => a === b, null);\nawait page.waitForFunction(/* sync */ () => true);\n", "x.py"), [])
        self.assertEqual(bare("(a, b) => f(a, b)"), "(a, b) => f(a, b)")
        self.assertEqual(bare("/* c */ ( (async () => 1) )"), "async () => 1")
        self.assertEqual(bare("  // c\n  ready"), "ready")

    def test_a_method_reference_as_the_predicate_is_out_of_reach_as_the_docstring_says(self):
        # whether `this.ready` or `d.ready` names an async method is not decidable from the call site's text, and a dotted name has
        # no same-file binding for rule (2) to read: named out of reach in the docstring; a reader that gains it moves this shape
        # into a planted red
        text = ("class Driver {\n  async ready() { return (await fetch('/v')).ok; }\n  wait() { return this.page.waitForFunction(this.ready); }\n}\n"
                "const d = new Driver();\nawait page.waitForFunction(d.ready);\n")
        self.assertEqual(offenders(text, "x.ts"), [])

    def test_a_planted_name_bound_to_an_async_function_reds(self):
        planted = 'const ready = async () => (await fetch("/v")).ok;\nawait page.waitForFunction(ready, null, { timeout: 5000 });\n'
        self.assertEqual(offenders(planted, "x.py"), ["x.py:2: waitForFunction is handed ready, a name bound to an async function"])
        planted = 'async function ready() { return (await fetch("/v")).ok; }\nawait page.waitForFunction(ready);\n'
        self.assertEqual(offenders(planted, "x.py"), ["x.py:2: waitForFunction is handed ready, a name bound to an async function"])

    def test_a_planted_wrapper_call_with_an_async_literal_reds(self):
        planted = ('const waitFn = async (fn, arg, why) => page.waitForFunction(fn, arg, { timeout: T }).catch(() => die(why));\n'
                   'await waitFn(() => document.body.dataset.ready === "1", null, "the sync one");\n'
                   'await waitFn(async () => (await fetch("/v")).ok, null, "the async one");\n')
        self.assertEqual(offenders(planted, "x.py"),
                         ["x.py:3: waitFn hands waitForFunction its parameter fn, and this call passes an async predicate literal"])

    def test_a_planted_wrapper_call_with_a_name_bound_to_an_async_function_reds(self):
        planted = ('const waitFn = async (fn, arg, why) => page.waitForFunction(fn, arg, { timeout: T });\n'
                   'const ready = async () => (await fetch("/v")).ok;\n'
                   'await waitFn(ready, null, "the async one by name");\n')
        self.assertEqual(offenders(planted, "x.py"),
                         ["x.py:3: waitFn hands waitForFunction its parameter fn, and this call passes ready, a name bound to an async function"])

    def test_the_wrapper_forms_the_third_rule_reads_and_the_two_it_does_not(self):
        # the form table (each definition form, the predicate's position, a caller handing an async literal there): the rule
        # must name the wrapper and its parameter. The first form's list once had to be free of parentheses, so the webview's
        # own `async function waitFor(page: any, pred: () => boolean, what: string)` went unread and its callers unjudged
        read = [
            ("an arrow with a parenthesized list", 'const waitFn = async (fn, arg, why) => page.waitForFunction(fn, arg, { timeout: T });\n', "waitFn", "fn", 'await waitFn(async () => true, null, "x");\n'),
            ("an arrow with one bare parameter", "const until = fn => page.waitForFunction(fn, null, { timeout: 5 });\n", "until", "fn", "await until(async () => true);\n"),
            ("an arrow with typed and defaulted parameters", "const waitFor = async (page: any, pred: () => boolean, ms = bound(1)) => page.waitForFunction(pred, null, { timeout: ms });\n", "waitFor", "pred", 'await waitFor(page, async () => true, 50);\n'),
            ("a function declaration with typed parameters", 'async function waitFor(page: any, pred: () => boolean, what: string): Promise<void> {\n  try { await page.waitForFunction(pred, null, { timeout: 5000 }); }\n  catch (e) { throw new Error(what); }\n}\n', "waitFor", "pred", 'await waitFor(page, async () => String(getSelection()) === "x", "the async one");\n'),
            ("a function expression bound to a name", "const w = function (fn) { return page.waitForFunction(fn); };\n", "w", "fn", "await w(async () => true);\n"),
            ("a let-bound arrow", "let w = (fn) => page.waitForFunction(fn);\n", "w", "fn", "await w(async () => true);\n"),
        ]
        for form, definition, wname, param, caller in read:
            names = [d[0] for d in wrapper_defs(definition)]
            self.assertIn(wname, names, form + ": the definition is read as a wrapper form; read: %r" % names)
            found = offenders(definition + caller, "x.ts")
            line = definition.count("\n") + 1
            self.assertEqual(found, ["x.ts:%d: %s hands waitForFunction its parameter %s, and this call passes an async predicate literal" % (line, wname, param)],
                             form + ": the caller's async literal in the predicate's position is refused")
            self.assertEqual(offenders(definition + caller.replace("async () =>", "() =>").replace("async () => String(getSelection()) === \"x\"", "() => true"), "x.ts"), [],
                             form + ": the same caller with a synchronous arrow is clean")
        # the predicate's POSITION is the parameter's: an async literal in another slot of the same wrapper is not the predicate
        self.assertEqual(offenders("const waitFor = (page, pred, what) => page.waitForFunction(pred);\nawait waitFor(page, () => true, async () => 1);\n", "x.ts"), [])
        # out of reach, as the module docstring says: a method wrapper (class or object literal) is not read, and a caller
        # handing it an async literal is not refused; a reader that gains these forms moves them into the table above
        for form, text in (("a class method", "class Driver {\n  async until(fn) { await this.page.waitForFunction(fn); }\n}\nawait d.until(async () => true);\n"),
                           ("an object-literal method", "const d = {\n  until(fn) { return page.waitForFunction(fn); },\n};\nawait d.until(async () => true);\n")):
            self.assertEqual(wrapper_defs(text), [], form + ": not a form the rule reads")
            self.assertEqual(offenders(text, "x.ts"), [], form + ": stated out of reach in the docstring, so no offender here")
        # a parenthesized expression that is no arrow is passed over, not read as a wrapper of nothing
        self.assertEqual(wrapper_defs("const total = (a + b) * 2;\nconst w = (fn) => page.waitForFunction(fn);\n"), [("w", ["fn"], len("const total = (a + b) * 2;\nconst w = (fn)"))])

    def test_the_synchronous_shapes_and_the_commented_shape_are_clean(self):
        clean = ('await page.waitForFunction(() => document.body.classList.contains("settings-open"), null, { timeout: 20000 });\n'
                 'await setF.waitForFunction((want) => document.getElementById("rs-tasktrack").checked === want, true, { timeout: 10000 });\n'
                 "const foldedIs = ({ name, folded }) => { const g = document.querySelector('.tl-group-head[data-group=\"' + name + '\"]'); return !!g; };\n"
                 'await page.waitForFunction(foldedIs, { name: "backend", folded: true }, { timeout: 20000 });\n'
                 'await page.waitForFunction(() => document.title === "async (u) => never", null, { timeout: 1 });\n'
                 'const waitFn = async (fn, arg, why) => page.waitForFunction(fn, arg, { timeout: T });\n'
                 'await waitFn(() => !!document.querySelector("#x"), null, "sync through the wrapper");\n'
                 '// the old line was waitForFunction(async (u) => (await fetch(u)).ok, u, { timeout: 1 })\n'
                 '# a Python comment quoting waitForFunction(async () => false) is no call either\n')
        self.assertEqual(offenders(clean, "x.py"), [])

    def test_first_argument_balances_brackets_and_skips_strings(self):
        text = 'waitForFunction((a, b) => f(a, "x,y)", [b, {c: 1}]), null)'
        self.assertEqual(first_argument(text, len("waitForFunction")), '(a, b) => f(a, "x,y)", [b, {c: 1}])')
        self.assertEqual(arguments_of(text, len("waitForFunction")), ['(a, b) => f(a, "x,y)", [b, {c: 1}])', ' null'])
        text = 'waitForFunction(pred)'
        self.assertEqual(first_argument(text, len("waitForFunction")), "pred")
        # a template literal's brackets and commas do not count either; an unclosed call yields its tail
        self.assertEqual(arguments_of("f(`a, ${b(1)}`, c)", 1), ["`a, ${b(1)}`", " c"])
        self.assertEqual(arguments_of("f(a, b", 1), ["a", " b"])


if __name__ == "__main__":
    unittest.main()
