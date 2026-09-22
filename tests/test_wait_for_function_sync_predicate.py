#!/usr/bin/env python3
"""No browser test hands Playwright's waitForFunction an ASYNC predicate (2026-09-22).

The pinned Playwright (vscode-extension/package-lock.json) does not poll an async predicate: its injected poller calls the
predicate once, and an async function returns a promise, a truthy value, so the wait resolves on that first promise whatever
it resolves to. `page.waitForFunction(async () => false, null, { timeout: 3000 })` returns in about 20 ms with the value
false where the synchronous `() => false` times out at 3000 ms (measured on the pinned version). A served-page test that
awaited the kernel's state that way (`async (u) => (await fetch(u)).json().taskTracking === false`, the Task tracking switch
lab) therefore proceeded at once, and the reads after it raced the kernel's write: a finding on the project PR 2031, and
CI reds on fork PR #862 and fork PR #899. The remedy is a poll from the driver (a bounded loop over the same read, a short
pause between polls, the elapsed time recorded: pollKernelSwitch in tests/test_task_tracking_switch_browser.py), or a
synchronous predicate over state the page already holds.

The pin is a text rule over every file that can drive a browser: the Python labs and the node scripts under tests/, the
webview's tests and helpers under ui/webview/, and the extension's sources under vscode-extension/src/. Its bound, stated
so a reader never takes it for more: (1) the first argument of a `waitForFunction(` call, read with brackets and string
literals balanced, that begins with the `async` keyword (an async arrow or an async function expression); (2) a first
argument that is a bare name bound in the same file to an async function (`const p = async () =>`, `async function p`);
(3) a call through a wrapper whose parameter is that first argument (`const waitFn = (fn, ...) => page.waitForFunction(fn,
...)`), when a caller in the same file hands the wrapper an `async` literal. Comment lines (`//`, `#`, `*`) are skipped, so
a comment naming the shape is no offender and a pin in a comment is no cover. Out of its reach, by design: a predicate
built in another file, a name rebound between its definition and the call, a regex literal holding an unbalanced bracket.
The census that fixed the tree (2026-09-22) read every identifier-passed and wrapper-passed predicate by hand and found each
synchronous; this rule holds that state. This file plants the shapes it refuses in its own tests, so the walk leaves it out
by name. Reads the tree only: no kernel, no browser, no romp code loaded.
"""
import glob
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SELF = os.path.basename(__file__)
CALL = "waitForFunction("
_LEAD = re.compile(r"^\s*(//|#|\*|/\*)")
_DEF = re.compile(r"(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?\(([^()]*)\)\s*=>|(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(([^()]*)\)")


def population():
    """Every file that can drive a browser, by path: the labs and node scripts under tests/, the webview's tests and
    helpers, the extension's sources. Sorted, repo-relative; this pin's own file left out."""
    pats = [os.path.join(HERE, "*.py"), os.path.join(HERE, "*.js"), os.path.join(HERE, "*.mjs"),
            os.path.join(ROOT, "ui", "webview", "*.ts"), os.path.join(ROOT, "ui", "webview", "*.js"),
            os.path.join(ROOT, "vscode-extension", "src", "*.ts"), os.path.join(ROOT, "vscode-extension", "src", "*.js")]
    out = set()
    for pat in pats:
        for path in glob.glob(pat):
            if os.path.basename(path) != SELF:
                out.add(os.path.relpath(path, ROOT))
    return sorted(out)


def first_argument(text, start):
    """The text of the first argument of the call whose opening paren is at `start`: brackets balanced, string and
    template literals skipped (their brackets do not count), up to the first top-level comma or the closing paren."""
    depth = 0
    i = start + 1
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
                return text[start + 1:i]
            depth -= 1
        elif c == "," and depth == 0:
            return text[start + 1:i]
        i += 1
    return text[start + 1:]


def _is_comment_line(text, pos):
    line_start = text.rfind("\n", 0, pos) + 1
    return bool(_LEAD.match(text[line_start:pos + 1]))


def offenders(text, name="<text>"):
    """Every waitForFunction call in `text` whose first argument is asynchronous under the three rules of the module
    docstring, as "<name>:<line>: <reason>" strings. Pure over its input, so a planted shape is tested without a file."""
    out = []
    wrappers = {}   # parameter name of a wrapper -> the wrapper's name, for rule (3)
    for m in re.finditer(re.escape(CALL), text):
        pos = m.end() - 1
        if _is_comment_line(text, pos):
            continue
        line = text.count("\n", 0, pos) + 1
        arg = first_argument(text, pos).strip()
        if re.match(r"async\b", arg):
            out.append("%s:%d: waitForFunction is handed an async predicate literal" % (name, line))
            continue
        if re.fullmatch(r"[A-Za-z_$][\w$]*", arg):
            if re.search(r"(?:const|let|var)\s+%s\s*=\s*async\b|async\s+function\s+%s\b" % (re.escape(arg), re.escape(arg)), text):
                out.append("%s:%d: waitForFunction is handed %s, a name bound to an async function" % (name, line, arg))
                continue
            # rule (3): the last function defined before the call whose parameter list names the argument is its wrapper
            for wm in reversed(list(_DEF.finditer(text[:pos]))):
                wname = wm.group(1) or wm.group(3)
                params = [p.split(":")[0].split("=")[0].strip() for p in (wm.group(2) or wm.group(4) or "").split(",")]
                if arg in params:
                    wrappers[wname] = arg
                    break
    for wname, param in wrappers.items():
        for cm in re.finditer(r"\b%s\(" % re.escape(wname), text):
            if _is_comment_line(text, cm.end() - 1):
                continue
            arg = first_argument(text, cm.end() - 1).strip()
            if re.match(r"async\b", arg):
                line = text.count("\n", 0, cm.start()) + 1
                out.append("%s:%d: %s hands waitForFunction its parameter %s, and this call passes an async predicate literal" % (name, line, wname, param))
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

    def test_the_population_holds_the_lab_the_finding_came_from_and_the_three_trees(self):
        pop = population()
        self.assertIn(os.path.join("tests", "test_task_tracking_switch_browser.py"), pop)
        self.assertNotIn(os.path.join("tests", SELF), pop, "this file plants the shape; the walk leaves it out by name")
        for tree in (os.path.join("tests", ""), os.path.join("ui", "webview", ""), os.path.join("vscode-extension", "src", "")):
            self.assertTrue(any(p.startswith(tree) for p in pop), tree)

    def test_a_planted_async_arrow_reds(self):
        planted = 'await page.waitForFunction(async (u) => (await (await fetch(u, { cache: "no-store" })).json()).on === false, cfg.v, { timeout: 10000 });\n'
        self.assertEqual(offenders(planted, "x.py"), ["x.py:1: waitForFunction is handed an async predicate literal"])
        self.assertEqual(offenders("await f.waitForFunction(async function () { return false; }, null, { timeout: 5 });", "y.js"),
                         ["y.js:1: waitForFunction is handed an async predicate literal"])

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
        text = 'waitForFunction(pred)'
        self.assertEqual(first_argument(text, len("waitForFunction")), "pred")


if __name__ == "__main__":
    unittest.main()
