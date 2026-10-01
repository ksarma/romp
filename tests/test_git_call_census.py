#!/usr/bin/env python3
"""The census behind the 02:43Z ruling on PR 926, item 1(a): every git call scripts/sweep.py and scripts/batch.py make
into a repository goes through the one helper each script has, run_git, which gives it a bounded wait (GIT_BOUND,
killed with its process group at the bound, the call then refused or the run invalid, naming it) and names the
repository it means (item 1(b): GIT_DIR, GIT_COMMON_DIR and GIT_WORK_TREE set and GIT_CEILING_DIRECTORIES above it, or
for a discovery call, find_repo's in each script, the ceiling alone). A git started anywhere else would wait without a
bound on a FIFO a leg left behind, or walk up to an enclosing repository, which is what the closing check at the PR's
head found file by file.

The census reads each script's source with ast and runs nothing. Outside the helper it finds:
  - any list or tuple handed to any call (directly, as the start of a sum, starred, or through a name it is assigned
    to in the same function) that is a git argv: its first element names git, or is a starred sequence that does, or
    it starts with a program that runs the rest of its argv (WRAPPERS: env, nice, timeout, setsid, ...) and a later
    element names git, or with a shell (SHELLS) and a later element is shell text holding a git command word;
  - any process launcher (subprocess.run, Popen, call, check_call, check_output, getoutput, getstatusoutput; os.system,
    popen, exec*, spawn*, posix_spawn*; asyncio.create_subprocess_exec and _shell; each script's own runner for
    processes that are not git, batch.py's _run; a name bound to any of them, or a functools.partial of one) whose argv
    is a git argv, a sum that starts with one, shell text holding a git command word (a literal, an f-string, the format
    string of a % or .format), or a name that names git, or whose executable= keyword names git, however the launcher is
    imported (`import subprocess as sp`, `from subprocess import run`).
A name "names git" when the word git or a path ending in /git (a literal or an f-string spelling one), shutil.which of
such a name, or an os.environ.get or os.getenv whose default is one, can reach it through any binding the census reads:
an assignment, an annotated one, a walrus, a parameter's default, a for-loop or comprehension target (each element of a
literal sequence, unpacked by position for a tuple target), a tuple-unpacking target, or a class attribute read as an
attribute of that name. An argv the census cannot see statically (a parameter without a default, the user's bisect
command) is not a git call to it; the behavioural pins in tests/test_sweep_runner.py and tests/test_batch_tool.py hold
the helper to its bound.

A list naming git that no call is handed is not an argv (sweep.py's fault class "git" in the re-read's verdict). One git
process starts outside the helper on purpose, and the census sees it and excuses it by name (EXCUSED): tool_versions runs
`git --version` as the legs' own git (from their PATH, in their environment) to record its version, through its loop
over TOOL_VERSION_ARGS and shutil.which. `git --version` reads no repository and no file a leg can plant, and
tool_versions bounds it at 60 s already. The excuse covers exactly that launch: any other git call in the function is a
finding.
"""
import ast
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HELPER = "run_git"
SCRIPTS = ("scripts/sweep.py", "scripts/batch.py")
# Each script's own runner for processes that are not git: a git argv handed to it would start git outside the helper.
LOCAL_RUNNERS = {"scripts/sweep.py": set(), "scripts/batch.py": {"_run"}}
LAUNCHERS = ({("subprocess", n) for n in ("run", "Popen", "call", "check_call", "check_output", "getoutput",
                                          "getstatusoutput")}
             | {("os", n) for n in ("system", "popen", "execv", "execve", "execvp", "execvpe", "execl", "execle", "execlp",
                                    "execlpe", "spawnv", "spawnve", "spawnvp", "spawnvpe", "spawnl", "spawnle", "spawnlp",
                                    "spawnlpe", "posix_spawn", "posix_spawnp")}
             | {("asyncio", n) for n in ("create_subprocess_exec", "create_subprocess_shell")})
# Programs that run the rest of their argv as a command (an argv starting with one starts git when a later word names
# it), and shells, whose -c text starts git when a command word in it names git.
WRAPPERS = {"env", "nice", "ionice", "timeout", "nohup", "setsid", "stdbuf", "sudo", "doas", "exec", "time", "chrt",
            "taskset", "xargs", "flock", "unbuffer", "command", "systemd-run", "script"}
SHELLS = {"sh", "bash", "dash", "zsh", "ksh", "ash", "fish", "busybox"}
# A git command word in a shell text: git (or a path ending in /git) at the text's start or after a separator, followed by
# the text's end, a blank or a separator.
GIT_COMMAND = re.compile(r"(?:^|[\s;&|(`]|\$\()(?:\S*/)?git(?=$|[\s;&|)`])")
# The one git launch outside run_git each script holds on purpose, by the function it is in and the kinds of finding it
# gives: tool_versions runs `git --version` as the legs' own git, through its loop over TOOL_VERSION_ARGS (the module
# docstring says why). The census sees it and excuses exactly these findings there, so a second git call added to that
# function is a finding.
EXCUSED = {"scripts/sweep.py": {"tool_versions": ["a git argv", "a launch of git"]}, "scripts/batch.py": {}}


def _names_git_word(value):
    return isinstance(value, str) and (value == "git" or value.endswith("/git"))


def _program(value):
    return value.rsplit("/", 1)[-1] if isinstance(value, str) else None


class _Derived:
    """A value the census derives from another node when it resolves a name: each element of an iterable (a for-loop or
    comprehension target), or the index-th element of a sequence (an unpacking target), or both (a loop over pairs)."""

    def __init__(self, node, each=False, index=None):
        self.node, self.each, self.index = node, each, index


def git_calls(source, local_runners=(), helper=HELPER):
    """(findings, in_helper) for `source`: findings is a sorted list of (line, enclosing function or None, what) for each
    git argv or git launch outside `helper`; in_helper counts the git launches inside the helper (the census is not
    vacuous only while the helper's own call is seen as one)."""
    tree = ast.parse(source)
    owner, bindings, attrs = {}, {None: {}}, {}
    for f in [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
        for n in ast.walk(f):
            owner[id(n)] = f.name

    def bind(scope, target, value):
        """Record what `target` (a name, or a tuple or list of targets, a starred one included) may hold."""
        if isinstance(target, ast.Starred):
            target = target.value
        if isinstance(target, ast.Name):
            bindings.setdefault(scope, {}).setdefault(target.id, []).append(value)
        elif isinstance(target, (ast.Tuple, ast.List)):
            for i, t in enumerate(target.elts):
                if isinstance(value, _Derived):
                    bind(scope, t, _Derived(value.node, value.each, i))
                else:
                    bind(scope, t, _Derived(value, False, i))
    for n in ast.walk(tree):
        scope = owner.get(id(n))
        if isinstance(n, ast.Assign):
            for t in n.targets:
                bind(scope, t, n.value)
        elif isinstance(n, ast.AnnAssign) and n.value is not None:
            bind(scope, n.target, n.value)
        elif isinstance(n, ast.NamedExpr):
            bind(scope, n.target, n.value)
        elif isinstance(n, (ast.For, ast.AsyncFor)):
            bind(scope, n.target, _Derived(n.iter, each=True))
        elif isinstance(n, ast.comprehension):
            bind(scope, n.target, _Derived(n.iter, each=True))
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            positional = n.args.posonlyargs + n.args.args
            for a, d in zip(positional[len(positional) - len(n.args.defaults):], n.args.defaults):
                bindings.setdefault(n.name, {}).setdefault(a.arg, []).append(d)
            for a, d in zip(n.args.kwonlyargs, n.args.kw_defaults):
                if d is not None:
                    bindings.setdefault(n.name, {}).setdefault(a.arg, []).append(d)
        elif isinstance(n, ast.ClassDef):
            for stmt in n.body:
                targets = stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target] if isinstance(stmt, ast.AnnAssign) \
                    and stmt.value is not None else []
                for t in targets:
                    if isinstance(t, ast.Name):
                        attrs.setdefault(t.id, []).append(stmt.value)
    modules, direct = {}, {}         # a bound name -> the module it names; a name imported from a module -> (module, name)
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                modules[a.asname or a.name.split(".")[0]] = a.name.split(".")[0] if not a.asname else a.name
        elif isinstance(n, ast.ImportFrom):
            for a in n.names:
                direct[a.asname or a.name] = (n.module or "", a.name)

    def resolve(node, scope, depth=0):
        """The values a name may hold (its bindings in its function, else at module level), an attribute the values a
        class attribute of that name is assigned, a derived value the elements it names; others as they are."""
        if depth > 8:
            return [node]
        if isinstance(node, _Derived):
            out = []
            for v in resolve(node.node, scope, depth + 1):
                items = [e for e in (v.elts if isinstance(v, (ast.List, ast.Tuple, ast.Set)) else [])] if node.each else [v]
                for item in items:
                    if isinstance(item, ast.Starred):
                        item = item.value
                    for iv in resolve(item, scope, depth + 1):
                        if node.index is None:
                            out.append(iv)
                        elif isinstance(iv, (ast.List, ast.Tuple)) and len(iv.elts) > node.index:
                            out.extend(resolve(iv.elts[node.index], scope, depth + 1))
            return out
        if isinstance(node, ast.Name):
            found = bindings.get(scope, {}).get(node.id) or bindings[None].get(node.id) or []
            return [v for x in found for v in resolve(x, scope, depth + 1)] or [node]
        if isinstance(node, ast.Attribute) and node.attr in attrs:
            return [v for x in attrs[node.attr] for v in resolve(x, scope, depth + 1)] or [node]
        return [node]

    def module_call(node, module, names):
        """Whether `node` is a call of module.<one of names>, however the module or the name is imported."""
        f = node.func if isinstance(node, ast.Call) else None
        if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and modules.get(f.value.id) == module:
            return f.attr in names
        if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Attribute) and isinstance(f.value.value, ast.Name) \
                and modules.get(f.value.value.id) == module and f.value.attr + "." + f.attr in names:
            return True
        if isinstance(f, ast.Name):
            return direct.get(f.id, ("", ""))[0] == module and direct[f.id][1] in names
        return False

    def names_git(node, scope, depth=0):
        """Whether `node` may name the git program: the word git or a path ending in /git (a literal, a name or attribute
        bound to one, an f-string that spells one), shutil.which of such a name, or an environment read whose default
        is one."""
        if depth > 8:
            return False
        for v in resolve(node, scope):
            if isinstance(v, ast.Constant) and _names_git_word(v.value):
                return True
            if isinstance(v, ast.JoinedStr) and v.values and isinstance(v.values[-1], ast.Constant) and (
                    _names_git_word(v.values[-1].value) and (len(v.values) == 1 or v.values[-1].value.startswith("/"))):
                return True
            if module_call(v, "shutil", {"which"}) and v.args and names_git(v.args[0], scope, depth + 1):
                return True
            if (module_call(v, "os", {"getenv", "environ.get"}) or (isinstance(v, ast.Call) and isinstance(v.func, ast.Attribute)
                                                                      and v.func.attr == "get" and isinstance(v.func.value, ast.Name)
                                                                      and direct.get(v.func.value.id) == ("os", "environ"))):
                default = v.args[1] if len(v.args) > 1 else next((k.value for k in v.keywords if k.arg == "default"), None)
                if default is not None and names_git(default, scope, depth + 1):
                    return True
        return False

    def shell_text(node, scope):
        """The text of a shell command `node` spells (a literal, an f-string with each value as X, the format string of
        a % or .format), or None."""
        for v in resolve(node, scope):
            if isinstance(v, ast.Constant) and isinstance(v.value, str):
                return v.value
            if isinstance(v, ast.JoinedStr):
                return "".join(p.value if isinstance(p, ast.Constant) else "X" for p in v.values)
            if isinstance(v, ast.BinOp) and isinstance(v.op, (ast.Mod, ast.Add)):
                return shell_text(v.left, scope)
            if isinstance(v, ast.Call) and isinstance(v.func, ast.Attribute) and v.func.attr == "format":
                return shell_text(v.func.value, scope)
        return None

    def git_list(v, scope):
        """Whether the list or tuple `v` is a git argv: its first element names git, or is a starred sequence that does,
        or it starts with a wrapper and a later element names git, or with a shell and a later element is shell text
        holding a git command word."""
        if not isinstance(v, (ast.List, ast.Tuple)) or not v.elts:
            return False
        first = v.elts[0]
        if isinstance(first, ast.Starred):
            return git_argv(first.value, scope)
        if names_git(first, scope):
            return True
        programs = {_program(x.value) for x in resolve(first, scope) if isinstance(x, ast.Constant)}
        rest = v.elts[1:]
        if programs & WRAPPERS and any(names_git(e, scope) or git_list(e, scope) for e in rest):
            return True
        if programs & SHELLS:
            return any(GIT_COMMAND.search(shell_text(e, scope) or "") for e in rest)
        return False

    def git_argv(node, scope):
        for v in resolve(node, scope):
            if git_list(v, scope):
                return True
            if isinstance(v, ast.BinOp) and isinstance(v.op, ast.Add) and git_argv(v.left, scope):
                return True
            text = shell_text(v, scope)
            if text is not None and GIT_COMMAND.search(text):
                return True
            if names_git(v, scope):
                return True
        return False

    def is_launcher(func, scope, depth=0):
        if depth > 4:
            return False
        if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
            if (modules.get(func.value.id, func.value.id), func.attr) in LAUNCHERS:
                return True
        if isinstance(func, ast.Name) and (direct.get(func.id) in LAUNCHERS or func.id in local_runners):
            return True
        for v in resolve(func, scope):
            if v is func:
                continue
            if is_launcher(v, scope, depth + 1):
                return True
            if module_call(v, "functools", {"partial"}) and v.args and is_launcher(v.args[0], scope, depth + 1):
                return True
        return False

    handed, handed_names = set(), set()     # the nodes some call is handed, and (function, name) of the names it is

    def hand(node, scope):
        if isinstance(node, ast.Starred):
            node = node.value
            for e in node.elts if isinstance(node, (ast.List, ast.Tuple)) else ():
                hand(e, scope)
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            hand(node.left, scope)
            hand(node.right, scope)
        elif isinstance(node, ast.Name):
            handed_names.add((scope, node.id))
        handed.add(id(node))
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            for a in list(n.args) + [k.value for k in n.keywords]:
                hand(a, owner.get(id(n)))
    for n in ast.walk(tree):
        if isinstance(n, (ast.Assign, ast.AnnAssign, ast.NamedExpr)):
            targets = n.targets if isinstance(n, ast.Assign) else [n.target]
            if n.value is not None and any(isinstance(t, ast.Name) and (owner.get(id(n)), t.id) in handed_names for t in targets):
                hand(n.value, owner.get(id(n)))
    findings, in_helper = set(), 0
    for n in ast.walk(tree):
        scope = owner.get(id(n))
        what = None
        if isinstance(n, ast.Call) and is_launcher(n.func, scope):
            argv = n.args[0] if n.args else next((k.value for k in n.keywords if k.arg in ("args", "argv", "program", "cmd")),
                                                 None)
            exe = next((k.value for k in n.keywords if k.arg == "executable"), None)
            others = n.args[1:] if isinstance(n.func, ast.Attribute) and n.func.attr.startswith(("exec", "spawn", "posix_spawn")) else []
            if (argv is not None and (git_argv(argv, scope) or any(git_argv(a, scope) or names_git(a, scope) for a in others))) \
                    or (exe is not None and names_git(exe, scope)):
                what = "a launch of git: %s" % ast.unparse(n)[:120]
        elif isinstance(n, (ast.List, ast.Tuple)) and id(n) in handed and git_list(n, scope):
            what = "a git argv: %s" % ast.unparse(n)[:120]
        if what is None:
            continue
        if scope == helper:
            in_helper += what.startswith("a launch")
            continue
        findings.add((n.lineno, scope, what))
    return sorted(findings), in_helper


def unexcused(rel, findings):
    """`findings` less the ones EXCUSED holds for `rel`, and whether the excused function's findings are exactly the kinds
    excused there (each once)."""
    excused = EXCUSED.get(rel, {})
    rest = [f for f in findings if f[1] not in excused]
    exact = all(sorted(w.split(":")[0] for _l, fn, w in findings if fn == name) == sorted(kinds)
                for name, kinds in excused.items())
    return rest, exact


# Unwrapped git calls in the spellings the census must read, each planted at the end of a script's real source.
PLANTS = {
    "a literal argv": "def planted():\n    subprocess.run(['git', 'status'])\n",
    "a tuple argv to Popen": "def planted():\n    subprocess.Popen(('git', 'status'))\n",
    "an argv bound to a name first": "def planted():\n    cmd = ['git', 'rev-parse', 'HEAD']\n    return subprocess.check_output(cmd)\n",
    "a sum": "def planted(args):\n    return subprocess.run(['git'] + list(args))\n",
    "a shell string": "def planted():\n    os.system('git status --porcelain')\n",
    "a git binary variable": "GITBIN = 'git'\ndef planted():\n    subprocess.run([GITBIN, 'status'])\n",
    "shutil.which": "def planted():\n    g = shutil.which('git')\n    subprocess.run([g, 'status'])\n",
    "a module alias": "import subprocess as _sp\ndef planted():\n    _sp.run(['git', 'status'])\n",
    "a name imported from subprocess": "from subprocess import run as _r\ndef planted():\n    _r(['git', 'status'])\n",
    "an absolute git path": "def planted():\n    subprocess.call(['/usr/bin/git', 'status'])\n",
    # the spellings the verify pass at PR 926's build head found escaping (its code finding 2)
    "an annotated binding": "GITX: str = 'git'\ndef planted():\n    subprocess.run([GITX, 'status'])\n",
    "env as a wrapper": "def planted():\n    subprocess.run(['env', 'GIT_DIR=x', 'git', 'status'])\n",
    "nice as a wrapper": "def planted():\n    subprocess.run(['nice', '-n', '19', 'git', 'status'])\n",
    "a shell's -c text": "def planted():\n    subprocess.run(['sh', '-c', 'cd x && git status'])\n",
    "a starred first element": "def planted():\n    subprocess.run([*('git',), 'status'])\n",
    "a parameter default": "def planted(g='git'):\n    subprocess.run([g, 'status'])\n",
    "a keyword-only parameter default": "def planted(*, g='git'):\n    subprocess.run([g, 'status'])\n",
    "a for-loop target": "def planted():\n    for g in ('git',):\n        subprocess.run([g, 'status'])\n",
    "a tuple-unpack target": "def planted():\n    g, _x = 'git', 1\n    subprocess.run([g, 'status'])\n",
    "a loop over pairs through shutil.which": ("PAIRS = (('node', '--version'), ('git', '--version'))\ndef planted():\n"
                                              "    for tool, arg in PAIRS:\n        subprocess.run([shutil.which(tool), arg])\n"),
    "a comprehension target": "def planted():\n    return [subprocess.run([g, 'status']) for g in ['git']]\n",
    "a walrus": "def planted():\n    if (g := 'git'):\n        subprocess.run([g, 'status'])\n",
    "the executable keyword": "def planted():\n    subprocess.run(['status'], executable='git')\n",
    "an environment read's default": "def planted():\n    subprocess.run([os.environ.get('GITBIN', 'git'), 'status'])\n",
    "os.getenv's default": "def planted():\n    subprocess.run([os.getenv('GITBIN', 'git'), 'status'])\n",
    "an f-string shell text": "def planted(d):\n    os.system(f'git -C {d} status')\n",
    "a %-formatted shell text": "def planted(d):\n    os.system('cd %s && git status' % d)\n",
    "an f-string path to git": "def planted(d):\n    subprocess.run([f'{d}/git', 'status'])\n",
    "a class attribute argv": ("class Planted:\n    ARGV = ['git', 'status']\n    def planted(self):\n"
                               "        subprocess.run(self.ARGV)\n"),
    "asyncio's exec": "import asyncio\nasync def planted():\n    await asyncio.create_subprocess_exec('git', 'status')\n",
    "asyncio's shell": "import asyncio\nasync def planted():\n    await asyncio.create_subprocess_shell('git status')\n",
    "a partial with shell=True": ("import functools\ndef planted():\n    r = functools.partial(subprocess.run, shell=True)\n"
                                  "    r('git status')\n"),
    "a launcher bound to a name": "def planted():\n    r = subprocess.run\n    r(['git', 'status'])\n",
}


class GitCallCensus(unittest.TestCase):
    def test_every_git_call_in_both_scripts_goes_through_the_helper(self):
        """Each script's every git argv and git launch is inside run_git, and the census sees run_git's own launch (one),
        so a script whose helper it could not read would fail here rather than pass empty."""
        for rel in SCRIPTS:
            with self.subTest(script=rel):
                findings, in_helper = git_calls((ROOT / rel).read_text(), LOCAL_RUNNERS[rel])
                rest, exact = unexcused(rel, findings)
                self.assertEqual(rest, [], "%s starts git outside %s: %s" % (rel, HELPER, rest))
                self.assertTrue(exact, "%s: the excused function's findings are not exactly the excused ones (EXCUSED): %s"
                                % (rel, findings))
                self.assertEqual(in_helper, 1, "%s's %s launches git once, and the census must see that launch" % (rel, HELPER))

    def test_the_census_sees_tool_versions_git_and_excuses_only_it(self):
        """tool_versions' `git --version`, started through its loop over TOOL_VERSION_ARGS and shutil.which, is seen (a
        census that read loop targets as no binding missed it, the verify pass's code finding 2) and excused by name, and
        a second git call planted in that function is not excused."""
        base = (ROOT / "scripts/sweep.py").read_text()
        findings, _ = git_calls(base, LOCAL_RUNNERS["scripts/sweep.py"])
        self.assertEqual(sorted((f, w.split(":")[0]) for _l, f, w in findings),
                         [("tool_versions", "a git argv"), ("tool_versions", "a launch of git")])
        planted = base.replace("    return out\n\n\ndef npm_builtin(ctx):",
                               "    subprocess.run(['git', 'status'])\n    return out\n\n\ndef npm_builtin(ctx):", 1)
        self.assertNotEqual(planted, base, "premise: the plant went into tool_versions")
        findings, _ = git_calls(planted, LOCAL_RUNNERS["scripts/sweep.py"])
        self.assertFalse(unexcused("scripts/sweep.py", findings)[1], findings)

    def test_an_unwrapped_git_call_planted_in_either_script_is_found_by_name(self):
        """The census's red: each spelling in PLANTS, appended to each script's real source, is found, at the planted
        line and in the planted function. A census that missed one would let that spelling start git without a bound."""
        for rel in SCRIPTS:
            base = (ROOT / rel).read_text()
            first = len(base.splitlines()) + 1
            for label, plant in PLANTS.items():
                with self.subTest(script=rel, plant=label):
                    findings, _ = unexcused(rel, git_calls(base + "\n" + plant, LOCAL_RUNNERS[rel])[0])
                    self.assertTrue(findings, "the census missed %s planted in %s" % (label, rel))
                    self.assertTrue(all(line >= first for line, _f, _w in findings), findings)
                    self.assertTrue(any(f == "planted" or f is None for _l, f, _w in findings), findings)

    def test_a_git_argv_handed_to_batch_pys_runner_for_other_processes_is_found(self):
        """batch.py's _run starts gh, the ledger script and pr-orphans.sh; a git argv handed to it would start git
        outside run_git, as at the PR's head, where git() and git_ok() went through _run."""
        base = (ROOT / "scripts/batch.py").read_text()
        findings, _ = git_calls(base + "\ndef planted(root):\n    return _run(['git', 'fetch'], cwd=root)\n",
                                LOCAL_RUNNERS["scripts/batch.py"])
        self.assertEqual([(f, w.split(":")[0]) for _l, f, w in findings], [("planted", "a git argv"), ("planted", "a launch of git")])

    def test_a_git_call_inside_the_helper_is_the_helpers_and_a_second_helper_name_is_not(self):
        """The one name the census excuses is run_git: the same launch in a function of any other name is a finding."""
        source = ("import subprocess\n"
                  "def run_git(args):\n    argv = ['git', *args]\n    return subprocess.Popen(argv)\n"
                  "def run_git_too(args):\n    argv = ['git', *args]\n    return subprocess.Popen(argv)\n")
        findings, in_helper = git_calls(source)
        self.assertEqual(in_helper, 1)
        self.assertEqual(sorted({f for _l, f, _w in findings}), ["run_git_too"])

    def test_a_git_argv_handed_to_any_call_is_found_and_a_list_no_call_is_handed_is_not(self):
        """A list naming git that some call is handed (an unknown runner's argv, directly, as the start of a sum, starred,
        or through the name it is assigned to) is a finding; one no call is handed (a verdict's class name) is not."""
        for source in ("def f(run):\n    return run(['git', 'status'])\n",
                       "def f(run, rest):\n    return run(['git'] + rest)\n",
                       "def f(run):\n    return run(*[['git', 'status']])\n",
                       "def f(run):\n    argv = ('git', 'status')\n    return run(argv=argv)\n"):
            with self.subTest(source=source):
                findings, _ = git_calls(source)
                self.assertTrue(findings, source)
        for source in ("def f(faults):\n    return [('git', [b'.git'])]\n",
                       "def f():\n    order = ['missing'] + ['git', 'ancestor']\n    return [k for k in order]\n"):
            with self.subTest(source=source):
                findings, _ = git_calls(source)
                self.assertEqual(findings, [], source)


if __name__ == "__main__":
    unittest.main()
