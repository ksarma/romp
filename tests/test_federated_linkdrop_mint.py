"""The link-drop lab's old-hub mint writes nothing into the clone it runs from (2026-09-19).

LinkDropOldLocal (tests/test_federated_linkdrop_served.py) needs a hub kernel and bundle from before PR 815; under
ROMP_LINKDROP_OLD_HUB_BUILD=1 it mints that checkout itself. Round 1 of the fork PR that added the lab found the mint was a
worktree of the clone every session on this box shares: an interrupted add (a SIGKILL, a timeout) leaves a record git locks
as "initializing" that neither a forced remove nor a repo-wide clearing of stale records reaches, and the teardown's fallback
ran that repo-wide clearing there, which can delete the records of worktrees the test never made. A test may not run a
repo-global mutation on a clone it shares. The mint is now a private clone under the lab's scratch (git clone --shared
--no-checkout: the objects are borrowed through an alternates file, nothing is written under the source's .git) checked out
detached at OLD_HUB_SHA, and teardown is the scratch's removal, with no git command against the source.

Pinned here against a SCRATCH repository (the lab module's ROOT, OLD_HUB_SHA and EXT are repointed for the test and restored;
the shared clone is never the subject): the source's worktree records and its .git/worktrees directory are byte-identical
before the mint, after it and after teardown, with no locked record at any of the three; the minted checkout is at the sha
and borrows the source's objects; an interrupted mint (git killed as the clone starts, the failure path) raises with git's
words and leaves the source's records untouched; every git command the mint runs is either the clone, which reads the
source, or bound by -C to a path under the lab, and none names a worktree, a record clearing or an object collection; the
class's teardown, spied the same way WITH a minted checkout present (round 3: spied with none, a teardown step conditioned
on the mint, the round-1 defect's own shape, was never exercised), runs no command at all (the lab's rmtree takes the
checkout); and no string constant in the lab module's source, in either quoting, is such an argv token (an ast walk, so a
spelling cannot slip past it). What the spies see is a rule over NAMES, not a list of commands: the recorder patched over
the lab module's `subprocess` attribute records the argv of every call to one of that module's spawning functions, `run`,
`Popen`, `call`, `check_call`, `check_output`, `getoutput` and `getstatusoutput` (SPAWNERS, pinned against this Python's
`subprocess.__all__`), each once (a shell string as one token), and hands the call to the real function; every other name
read through the attribute (PIPE, STDOUT, DEVNULL, TimeoutExpired, CompletedProcess) is delegated and unrecorded, so a
command reaches the record only through a recorded name. A token assembled at run time or joined into one shell string is
caught whichever recorded function the module used (round 4: the spies saw `run` alone, and round 1's defect re-planted as a
`Popen` with its tokens assembled passed every pin, the byte-identical records included, since the peer worktree's directory
was still alive; the fixer pass of that round found `call`, `check_call` and `check_output` reaching the real module through
the delegation unseen while this docstring said the record saw them, and the same plant as a `check_call` passed every pin).
What the recorder cannot see, a command issued any other way (`os.system`, `os.popen`, the `os.spawn*`, `os.posix_spawn*`
and `os.exec*` families, or a road to the subprocess module other than `import subprocess`: an import under another name, a
name imported from it, the string "subprocess" handed to __import__ or importlib), a second census refuses by node in the
lab module and in every module it imports from this directory, transitively (OS_SPAWNERS, pinned against this Python's os
module; _commands_around_the_recorder, its detector pinned on a synthetic source of every form it refuses). Since the
follow-up's fixer pass the census also refuses a string constant naming such an os function, the road through getattr,
os.__dict__ or vars(os), and its import derivation reads every spelling of a sibling import, bare, package-qualified or
relative (_sibling_imports, pinned on each spelling), where it read the bare spelling alone. Two roads remain unseen. A
command a function of an imported module issues through THAT module's own `subprocess` attribute (the recorder patches the
lab module's alone): the mint's two commands and the teardown's none are the lab module's own, and no pin here exercises a
road through an imported module. And a name assembled at run time (a concatenated string handed to getattr, __import__ or
importlib, an exec or eval over built text) is beyond a census over the parsed source by construction: the census refuses
every spelling a source carries whole, and a source that builds the name carries none.

Synthetic: a scratch repository minted here, hostname TESTHOST; no kernel, no browser.
"""
import ast
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, HERE)
import test_federated_linkdrop_served as L   # noqa: E402  the lab module: _mint_old_hub and the globals it reads

FORBIDDEN_ARGV = ("worktree", "prune", "gc")
# every public callable of the subprocess module that starts a process: what the recorder records, by name (the pin below
# checks the tuple against this Python's subprocess.__all__, so a spawning function added to the module is not delegated unseen)
SPAWNERS = ("run", "Popen", "call", "check_call", "check_output", "getoutput", "getstatusoutput")
# every os function that starts a program, by name: what the recorder over the lab module's `subprocess` attribute cannot
# see, refused by the census below in the lab module and its imports from this directory (the tuple is pinned against this
# Python's os module, every name beginning spawn, exec or posix_spawn plus system and popen, so a member it lacks is a red)
OS_SPAWNERS = ("system", "popen",
               "spawnl", "spawnle", "spawnlp", "spawnlpe", "spawnv", "spawnve", "spawnvp", "spawnvpe", "posix_spawn", "posix_spawnp",
               "execl", "execle", "execlp", "execlpe", "execv", "execve", "execvp", "execvpe")
LAB_MODULE = "test_federated_linkdrop_served"
PACKAGE = os.path.basename(HERE)   # this directory is a package (tests/__init__.py), so a sibling is importable as tests.x and as .x too


def _sibling_imports(src, package=PACKAGE):
    """The names the import statements of the parsed source could resolve to a module beside the lab module in this directory:
    a bare name (`import lab_dist`, `from lab_dist import x`, the spelling the lab modules use, resolved through sys.path), the
    same name qualified by this directory's package (`import tests.lab_dist`, `from tests import lab_dist`, `from tests.lab_dist
    import x`) and a one-level relative import (`from . import lab_dist`, `from .lab_dist import x`, the spelling
    tests/__init__.py uses). An import from above this directory (`from .. import x`) names nothing here; a foreign module's
    name (`import os`) is returned and left for the caller's file check to drop. The follow-up's fixer pass: the derivation read
    the bare spelling alone, so a helper carrying `os.popen`, imported into the lab module as `from tests import <helper>` or
    `import tests.<helper>`, passed the census cell."""
    names = set()
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.Import):
            for a in n.names:
                parts = a.name.split(".")
                names.add(parts[1] if parts[0] == package and len(parts) > 1 else parts[0])
        elif isinstance(n, ast.ImportFrom):
            parts = n.module.split(".") if n.module else []
            if n.level == 0 and parts[:1] == [package]:
                parts = parts[1:]
            elif n.level > 1:
                continue
            if parts:
                names.add(parts[0])
            else:
                names.update(a.name for a in n.names)
    return names


def _lab_modules(root=LAB_MODULE, here=HERE):
    """The lab module and, transitively, every module it imports that lives beside it in this directory, {name: source},
    derived from the parsed import statements (every spelling _sibling_imports resolves, each naming a file here/x.py), so a
    helper the lab module grows is censused without anyone listing it. `here` is the directory (its basename the package the
    qualified spellings name); the composition pin hands it a synthetic one."""
    out, todo, package = {}, [root], os.path.basename(here)
    while todo:
        name = todo.pop()
        path = os.path.join(here, name + ".py")
        if name in out or not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8") as f:
            out[name] = f.read()
        todo += sorted(_sibling_imports(out[name], package))
    return out


def _commands_around_the_recorder(src):
    """Every node of the parsed source that could start a program around the recorder, as (line, form): an attribute read
    named as one of OS_SPAWNERS on ANY value (`os.system`, a renamed os and a nested attribute are refused alike, the safe
    side); a call to such a bare name, or its import from os (`from os import system`, `from os import *`); an import of
    the subprocess module under another name, or of a name from it; the string "subprocess" as a constant, the road
    through __import__, importlib.import_module or sys.modules; and a string constant equal to one of OS_SPAWNERS, the road
    through getattr(os, "system"), os.__dict__["system"] or vars(os)["system"] (the follow-up's fixer pass; the five modules
    hold no such constant, and a getattr over another name is untouched since only the string is matched). A comment or a
    docstring is no node of these kinds, so the words in one do not count; a docstring is one constant equal to its whole
    text, so a docstring that names os.system is not equal to "system"."""
    found = []
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.Attribute) and n.attr in OS_SPAWNERS:
            found.append((n.lineno, "." + n.attr))
        elif isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in OS_SPAWNERS:
            found.append((n.lineno, n.func.id + "("))
        elif isinstance(n, ast.ImportFrom) and n.module:
            if n.module == "os" and any(a.name in OS_SPAWNERS or a.name == "*" for a in n.names):
                found.append((n.lineno, "from os import " + ", ".join(a.name for a in n.names)))
            if n.module.split(".")[0] == "subprocess":
                found.append((n.lineno, "from %s import %s" % (n.module, ", ".join(a.name for a in n.names))))
        elif isinstance(n, ast.Import):
            for a in n.names:
                if a.name.split(".")[0] == "subprocess" and (a.asname or a.name != "subprocess"):
                    found.append((n.lineno, "import %s as %s" % (a.name, a.asname)))
        elif isinstance(n, ast.Constant) and (n.value == "subprocess" or n.value in OS_SPAWNERS):
            found.append((n.lineno, '"%s"' % (n.value,)))
    return found


def _git(*args):
    """A git command for the test's own scratch, through this module's real `subprocess` (the spies replace the LAB module's
    `subprocess` attribute, so a command the test itself issues stays out of the record, whichever function it uses)."""
    p = subprocess.Popen(["git", *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, err = p.communicate(timeout=60)
    if p.returncode != 0:
        raise AssertionError("git %s failed: %s" % (" ".join(args), err.strip()))
    return out


class _Scratch:
    """A repository with two commits, an extension directory the mint symlinks into, and one linked worktree (a peer's
    record, so the record set the mint must leave alone is not empty)."""

    def __init__(self, test):
        self.root = tempfile.mkdtemp(prefix="linkdrop-mint-src-")
        test.addCleanup(shutil.rmtree, self.root, True)
        _git("init", "-q", "-b", "main", self.root)
        ident = ("-c", "user.name=lab", "-c", "user.email=lab@TESTHOST")
        os.makedirs(os.path.join(self.root, "vscode-extension"))
        with open(os.path.join(self.root, "vscode-extension", "package.json"), "w") as f:
            f.write("{}\n")
        _git("-C", self.root, "add", "vscode-extension/package.json")
        _git("-C", self.root, *ident, "commit", "-q", "-m", "the old main")
        self.old = _git("-C", self.root, "rev-parse", "HEAD").strip()
        with open(os.path.join(self.root, "later.txt"), "w") as f:
            f.write("after the old main\n")
        _git("-C", self.root, "add", "later.txt")
        _git("-C", self.root, *ident, "commit", "-q", "-m", "a later main")
        self.peer = self.root + "-peer"
        test.addCleanup(shutil.rmtree, self.peer, True)
        _git("-C", self.root, "worktree", "add", "-q", "--detach", self.peer, "HEAD")

    def records(self):
        """What a mint could disturb: the porcelain record list, the admin directory's entries, the locked lines."""
        porcelain = _git("-C", self.root, "worktree", "list", "--porcelain")
        admin = os.path.join(self.root, ".git", "worktrees")
        entries = sorted(os.listdir(admin)) if os.path.isdir(admin) else []
        locked = [ln for ln in porcelain.splitlines() if ln.startswith("locked")]
        return {"porcelain": porcelain, "admin": entries, "locked": locked}


class OldHubMintIsPrivate(unittest.TestCase):
    def setUp(self):
        self.src = _Scratch(self)
        saved = (L.ROOT, L.OLD_HUB_SHA, L.EXT)
        self.addCleanup(lambda: setattr(L, "ROOT", saved[0]))
        self.addCleanup(lambda: setattr(L, "OLD_HUB_SHA", saved[1]))
        self.addCleanup(lambda: setattr(L, "EXT", saved[2]))
        L.ROOT, L.OLD_HUB_SHA, L.EXT = self.src.root, self.src.old, os.path.join(self.src.root, "vscode-extension")
        self.lab = tempfile.mkdtemp(prefix="federated-linkdrop-")
        self.addCleanup(shutil.rmtree, self.lab, True)

        class Mint(L._LinkDrop):
            pass
        Mint.lab, Mint.old_hub_wt = self.lab, None
        self.Mint = Mint
        self.before = self.src.records()
        self.assertEqual(len(self.before["admin"]), 1, "the scratch holds one peer record before the mint: %r" % (self.before,))
        self.assertEqual(self.before["locked"], [], "…and nothing locked")

    def _spy(self, run=None):
        """One recording namespace to patch over the lab module's `subprocess` attribute: each spawning function of the module
        (SPAWNERS) appends the argv to one list (a shell string as one token) and hands the call to the real function (`run`,
        when given, stands in for the real `run`: the interrupted mint's drill); every other name (PIPE, STDOUT, DEVNULL,
        TimeoutExpired, CompletedProcess, which the lab module reads through the same attribute) delegates to the real
        module. One namespace over the attribute, never a second patch of `Popen` on the real module: `subprocess.run`,
        `call`, `check_call` and `check_output` start their process through `Popen` as their own module's global, so that
        spelling records every `run` twice (read as 4 != 2 on the mint pin), and for the same reason each recorded function
        records once here. The recorder exists for the shape round 4 found passing every pin: round 1's repo-global sweep
        re-planted at the top of the class's teardown as `subprocess.Popen(["git", "-C", ROOT, "workt" + "ree", "pr" +
        "une"]).communicate()`, a `Popen` the `run` spy never saw with tokens the ast census never sees; the fixer pass of
        that round re-planted it as `subprocess.check_call(...)`, which the two-name recorder delegated unseen. Neither plant
        can live in the repo; both are recorded as mutations in the builder's review note outside it (red on
        test_the_teardown_runs_no_command through this recorder)."""
        seen = []
        real = subprocess

        class Recorder:
            def __getattr__(self, name):
                return getattr(real, name)

        def recording(name):
            target = run if (name == "run" and run is not None) else getattr(real, name)

            def spawn(cmd, *a, **k):
                seen.append([cmd] if isinstance(cmd, str) else list(cmd))
                return target(cmd, *a, **k)
            spawn.__name__ = name
            return staticmethod(spawn)
        for name in SPAWNERS:
            setattr(Recorder, name, recording(name))
        return seen, Recorder()

    def test_the_recorder_sees_every_spawning_function_once_and_delegates_the_rest(self):
        """The instrument itself (round 4's fixer pass, after a `check_call` sweep passed the `run`-and-`Popen` recorder): under
        the recorder each spawning function of the subprocess module records its argv exactly once (run, call, check_call and
        check_output start their process through the REAL module's Popen, so a recorder over `run` alone misses the others and
        a second patch of Popen doubles them), a shell string is recorded as one token, the names the lab module reads through
        the attribute are the real module's own objects, and SPAWNERS is every public callable of this Python's subprocess
        module that is not an exception class or CompletedProcess, so a spawning function added to the module is not
        delegated unseen."""
        public = {n for n in subprocess.__all__ if callable(getattr(subprocess, n))}
        not_spawning = {n for n in public if isinstance(getattr(subprocess, n), type) and n != "Popen"}   # CompletedProcess and the exception classes
        self.assertEqual(public - not_spawning, set(SPAWNERS), "SPAWNERS is every public callable of the subprocess module that starts a process")
        seen, recorder = self._spy()
        with mock.patch.object(L, "subprocess", recorder):
            for name in SPAWNERS:
                del seen[:]
                fn = getattr(L.subprocess, name)
                if name in ("getoutput", "getstatusoutput"):
                    fn("true")
                else:
                    p = fn(["true"], stdout=subprocess.DEVNULL) if name != "check_output" else fn(["true"])
                    if hasattr(p, "wait"):
                        p.wait()
                self.assertEqual(seen, [["true"]], "%s is recorded exactly once (a run, call, check_call or check_output recorded twice is the second-patch spelling): %r" % (name, seen))
            del seen[:]
            L.subprocess.run("true", shell=True, stdout=subprocess.DEVNULL)
            self.assertEqual(seen, [["true"]], "a shell string is recorded as one token: %r" % (seen,))
            for name in ("PIPE", "STDOUT", "DEVNULL", "TimeoutExpired", "CompletedProcess", "CalledProcessError"):
                self.assertIs(getattr(L.subprocess, name), getattr(subprocess, name), "%s is delegated to the real module" % name)

    def _assert_commands_are_private(self, seen, expect_commands=True):
        """Every git command the mint ran either reads the source (the clone) or is bound to a path under the lab; none
        carries a forbidden token. Derived from the spy's record, which must not be empty for a mint (expect_commands);
        a clean teardown runs none, and then the record is checked as it stands."""
        if expect_commands:
            self.assertTrue(seen, "the mint ran git (the spy saw its commands)")
        for cmd in seen:
            self.assertEqual(cmd[0], "git", cmd)
            self.assertEqual([t for t in cmd if t in FORBIDDEN_ARGV], [], "no worktree, record-clearing or collection command in the mint: %r" % (cmd,))
            if cmd[1] == "clone":
                self.assertEqual(cmd[-2], self.src.root, "the clone reads the source: %r" % (cmd,))
                self.assertTrue(cmd[-1].startswith(self.lab + os.sep), "…and writes under the lab: %r" % (cmd,))
            else:
                self.assertEqual(cmd[1], "-C", "every other command is bound by -C: %r" % (cmd,))
                self.assertTrue(cmd[2].startswith(self.lab + os.sep), "…to a path under the lab, never the source: %r" % (cmd,))

    def test_the_mint_registers_nothing_in_the_source_and_borrows_its_objects(self):
        seen, recorder = self._spy()
        with mock.patch.object(L, "subprocess", recorder):
            wt = self.Mint._mint_old_hub()
        self._assert_commands_are_private(seen)
        self.assertEqual(len(seen), 2, "the mint is one clone and one checkout: %r" % (seen,))
        after = self.src.records()
        self.assertEqual(after, self.before, "the source's worktree records are byte-identical after the mint")
        self.assertEqual(wt, os.path.join(self.lab, "oldhub"))
        self.assertEqual(self.Mint.old_hub_wt, wt)
        self.assertEqual(_git("-C", wt, "rev-parse", "HEAD").strip(), self.src.old, "the checkout is at OLD_HUB_SHA")
        self.assertTrue(os.path.isfile(os.path.join(wt, "vscode-extension", "package.json")), "…with the old main's tree")
        self.assertFalse(os.path.exists(os.path.join(wt, "later.txt")), "…and not the later main's")
        with open(os.path.join(wt, ".git", "objects", "info", "alternates")) as f:
            alt = f.read().strip()
        self.assertEqual(os.path.realpath(alt), os.path.realpath(os.path.join(self.src.root, ".git", "objects")), "the clone borrows the source's objects")
        self.assertTrue(os.path.islink(os.path.join(wt, "vscode-extension", "node_modules")), "the extension's node_modules is a symlink to this checkout's")
        shutil.rmtree(self.lab, ignore_errors=True)   # the class's teardown: the lab's rmtree, no git command
        self.assertEqual(self.src.records(), self.before, "…and byte-identical after teardown")

    def test_an_interrupted_mint_raises_and_leaves_the_source_untouched(self):
        def killed_at_the_clone(cmd, *a, **k):
            if cmd[:2] == ["git", "clone"]:
                p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)   # the test's own Popen, not the lab's
                p.kill()   # the drill: the mint's git dies as the clone starts (a SIGKILL mid-mint, the failure path)
                out, err = p.communicate()
                return subprocess.CompletedProcess(cmd, p.returncode if p.returncode else -9, out, err or "killed as the clone started (the drill)")
            return subprocess.run(cmd, *a, **k)
        seen, recorder = self._spy(run=killed_at_the_clone)
        with mock.patch.object(L, "subprocess", recorder):
            with self.assertRaises(RuntimeError) as cm:
                self.Mint._mint_old_hub()
        self.assertIn(self.src.old, str(cm.exception), "the error names the sha: %s" % cm.exception)
        self.assertEqual(len(seen), 1, "the mint stopped at the killed clone: %r" % (seen,))
        self._assert_commands_are_private(seen)
        self.assertIsNone(self.Mint.old_hub_wt, "nothing is recorded as minted")
        self.assertEqual(self.src.records(), self.before, "the source's worktree records are byte-identical after the interrupted mint (nothing locked, nothing added)")
        shutil.rmtree(self.lab, ignore_errors=True)
        self.assertEqual(self.src.records(), self.before, "…and after the lab's removal")

    def test_a_sha_the_source_does_not_hold_is_an_error_with_gits_words(self):
        L.OLD_HUB_SHA = "0123456789abcdef0123456789abcdef01234567"
        with self.assertRaises(RuntimeError) as cm:
            self.Mint._mint_old_hub()
        self.assertIn(L.OLD_HUB_SHA, str(cm.exception))
        self.assertEqual(self.src.records(), self.before)

    def test_the_teardown_runs_no_command(self):
        """The class's teardown with a MINTED checkout present and nothing to stop (no procs, no door, no splice) runs no
        subprocess at all: the lab's rmtree takes the checkout, and no git command of the class names the source (round 1's
        teardown ran a repo-wide record clearing there). The mint runs first under the spy, so a teardown step conditioned
        on the mint (old_hub_wt set, the round-1 defect's own shape) is exercised; round 3 found the pin spied a teardown
        with nothing minted, which such a step never entered. Behavioural, so the spelling of an argv token cannot matter,
        and the recorder sees every spawning function of the subprocess module alike (SPAWNERS), so the function it was
        issued through cannot matter either (round 4: a `Popen` sweep with assembled tokens passed the `run` spy, and a
        `check_call` sweep passed the `run`-and-`Popen` recorder; _spy's docstring names the plants)."""
        seen, recorder = self._spy()
        with mock.patch.object(L, "subprocess", recorder):
            wt = self.Mint._mint_old_hub()
        self._assert_commands_are_private(seen)
        self.assertEqual(self.Mint.old_hub_wt, wt, "the mint recorded its checkout")
        self.assertTrue(os.path.isdir(os.path.join(wt, ".git")), "…and the checkout exists under the lab when the teardown runs: %r" % (wt,))
        del seen[:]
        with mock.patch.object(L, "subprocess", recorder):
            self.Mint.tearDownClass()
        self._assert_commands_are_private(seen, expect_commands=False)
        self.assertEqual(seen, [], "a teardown with the minted checkout present runs no command: %r" % (seen,))
        self.assertFalse(os.path.exists(self.lab), "…and the lab is gone, the checkout with it")
        self.assertEqual(self.src.records(), self.before, "the source's worktree records are byte-identical after teardown")

    def test_the_lab_module_names_no_forbidden_git_command(self):
        """No string constant in the lab module is a forbidden argv token, read from the parsed source (ast.Constant), so a
        single-quoted spelling is seen as the double-quoted one is (round 2: the pin matched one quoting and passed the
        other). A cheap census beside the two spies, and only a census: a token assembled at run time is theirs to catch."""
        with open(L.__file__, encoding="utf-8") as f:
            src = f.read()
        constants = {n.value for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
        self.assertTrue(constants, "the lab module was parsed and has string constants")
        found = sorted(tok for tok in FORBIDDEN_ARGV if tok in constants)
        self.assertEqual(found, [], "string constants in the lab module that name a worktree, a record clearing or a collection: %r" % (found,))
        self.assertNotIn("_remove_old_hub", src, "the teardown has no git step of its own: the lab's rmtree takes the checkout")

    def test_no_road_to_a_process_around_the_recorder_in_the_lab_module_or_its_imports(self):
        """The census the module docstring names (round 4's fixer pass disclosed these roads; this refuses them): the recorder
        sees a command only through the lab module's `subprocess` attribute, so the lab module and every module it imports
        from this directory, transitively (_lab_modules, derived from the import statements), carry no other road to a
        process, by node over the parsed source (_commands_around_the_recorder): no attribute named as one of this Python's
        program-starting os functions on any value, no call to or import of such a bare name, no import of subprocess under
        another name or of a name from it, no constant "subprocess", no constant naming one of those os functions (the road
        through getattr, os.__dict__ or vars(os); the follow-up's fixer pass). OS_SPAWNERS is pinned against this Python's os
        module (every name beginning spawn, exec or posix_spawn, plus system and popen); the derivation must reach the lab
        module and lab_dist; and the detector is pinned on a synthetic source of each form it refuses and on the allowed
        spellings (import os, import subprocess, subprocess.run, os.path.join, the words in a docstring), so an empty census
        is a red and not a pass. What remains unseen is stated in the module docstring: a command a function of an imported
        module issues through that module's own subprocess attribute, and a name assembled at run time (a concatenated
        string, exec, eval, importlib over built text), which no census over the parsed source can read."""
        wanted = {n for n in dir(os) if n.startswith(("spawn", "exec", "posix_spawn")) or n in ("system", "popen")}
        self.assertTrue(wanted, "this Python's os module names program-starting functions")
        self.assertEqual(sorted(wanted - set(OS_SPAWNERS)), [], "every program-starting os function of this Python is in OS_SPAWNERS")
        forms = (('import os\nos.system("true")\n', ".system"),
                 ('import os as o\no.popen("true")\n', ".popen"),
                 ('import os\nos.posix_spawn("/bin/true", ["true"], {})\n', ".posix_spawn"),
                 ('from os import execv\n', "from os import execv"),
                 ('from os import *\n', "from os import *"),
                 ('def f(system):\n    system("true")\n', "system("),
                 ('import subprocess as sp\n', "import subprocess as sp"),
                 ('from subprocess import Popen as P\n', "from subprocess import Popen"),
                 ('import importlib\nimportlib.import_module("subprocess")\n', '"subprocess"'),
                 ('import sys\nsys.modules["subprocess"]\n', '"subprocess"'),
                 ('import os\ngetattr(os, "system")("true")\n', '"system"'),
                 ('import os\nos.__dict__["execv"]\n', '"execv"'))
        for src, form in forms:
            with self.subTest(form=form):
                hits = _commands_around_the_recorder(src)
                self.assertTrue(any(form in h[1] for h in hits), "the detector refuses %r: %r" % (src, hits))
        allowed = 'import os\nimport subprocess\nsubprocess.run(["true"])\nos.path.join("a", "b")\n"""os.system in a docstring"""\n'
        self.assertEqual(_commands_around_the_recorder(allowed), [], "the allowed spellings, and the words in a docstring, are not refused")
        mods = _lab_modules()
        self.assertTrue({LAB_MODULE, "lab_dist"} <= set(mods), "the derivation reaches the lab module and lab_dist: %r" % sorted(mods))
        found = {name: hits for name, src in sorted(mods.items()) for hits in [_commands_around_the_recorder(src)] if hits}
        self.assertEqual(found, {}, "a road to a process around the recorder in the lab module or a module it imports from this directory (censused: %s): %r"
                                    % (", ".join(sorted(mods)), found))

    def test_the_import_derivation_reads_every_spelling_of_a_sibling_import(self):
        """The census walks a module by the file its import names, whatever the spelling. The follow-up's fixer pass: the
        derivation followed `import x` and `from x import y` alone, so a helper reached as `from tests import x`, `import
        tests.x` or `from . import x` (the spelling tests/__init__.py itself uses) fell outside the census with no red, and a
        helper carrying `os.popen`, imported into the lab module the first two ways, passed the census cell. Each spelling of a
        sibling import resolves to the sibling's bare name; an import from above this directory resolves to nothing; a foreign
        module's name is left for _lab_modules's file check to drop (`import os` names `os`; no HERE/os.py exists)."""
        self.assertTrue(os.path.isfile(os.path.join(HERE, "__init__.py")), "this directory is a package, so the qualified and relative spellings import")
        self.assertEqual(PACKAGE, "tests", "the qualified spellings below are written for this directory's package name")
        cases = (("import lab_dist\n", {"lab_dist"}),
                 ("import lab_dist as d\n", {"lab_dist"}),
                 ("from lab_dist import x\n", {"lab_dist"}),
                 ("import tests.lab_dist\n", {"lab_dist"}),
                 ("import tests.lab_dist as d\n", {"lab_dist"}),
                 ("from tests import lab_dist\n", {"lab_dist"}),
                 ("from tests import lab_dist, fs_clock\n", {"lab_dist", "fs_clock"}),
                 ("from tests.lab_dist import x\n", {"lab_dist"}),
                 ("from . import lab_dist\n", {"lab_dist"}),
                 ("from .lab_dist import x\n", {"lab_dist"}),
                 ("from .. import kernel\n", set()),
                 ("import os\nfrom os.path import join\n", {"os"}))
        for src, want in cases:
            with self.subTest(src=src.strip()):
                self.assertEqual(_sibling_imports(src), want, "the sibling names %r resolves to" % (src,))
        self.assertNotIn("os", _lab_modules(), "the file check drops a foreign name")

    def test_the_census_walks_a_sibling_whatever_spelling_imports_it(self):
        """The composition: _lab_modules over a synthetic package directory (its basename `tests`, like this one) whose root
        imports four siblings, one by each spelling, one of which imports a fifth through a qualified spelling, beside a sixth
        nobody imports, reaches the five and not the sixth. Pinned apart from the resolver's own cells because a walk that
        never called the resolver (the derivation before the follow-up's fixer pass) passes those cells and the census alike:
        no module in this directory is reached through a qualified or relative spelling today, so only a synthetic one shows
        the walk following them."""
        top = tempfile.mkdtemp(prefix="linkdrop-census-")
        self.addCleanup(shutil.rmtree, top, True)
        here = os.path.join(top, "tests")
        os.makedirs(here)
        files = {"root": "import bare\nfrom tests import qualified_from\nimport tests.qualified_import as q\nfrom . import relative\n",
                 "bare": "import os\n", "qualified_from": "from tests.deeper import x\n", "qualified_import": "", "relative": "",
                 "deeper": "import os\n", "unimported": "import os\n"}
        for name, src in files.items():
            with open(os.path.join(here, name + ".py"), "w", encoding="utf-8") as f:
                f.write(src)
        self.assertEqual(sorted(_lab_modules("root", here)), ["bare", "deeper", "qualified_from", "qualified_import", "relative", "root"],
                         "the walk reaches a sibling by every spelling, transitively, and no unimported one")


if __name__ == "__main__":
    unittest.main()
