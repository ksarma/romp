#!/usr/bin/env python3
"""Every command under bin/, hooks/ and .githooks/ stays executable, in the checkout and in the mode git
records (2026-09-10).

bin/romp-kernel is a symlink to kernel/kernel.py, and the served browser tests spawn bin/romp-kernel
by path, so a kernel.py without its executable bit fails every one of those spawns with
PermissionError (bin/romp-serve, the launcher the manager goes through, refuses such a kernel at its
-x guard and exits 1 instead). On 2026-09-10 a whole-file rewrite of kernel/kernel.py was committed
on a PR branch as mode 100644: every served browser test in the local sweep errored launching the
kernel, and CI stayed green, because the served modules skip there without Playwright and nothing on
CI read the mode. These two tests read it, one from the working tree and one from the index, so a
checkout whose bits were restored by hand still fails on the recorded mode.

Scope: the entries git tracks directly under the three trees, enumerated from the index and never
from the working tree's listing, so an untracked stray file in bin/ is not a shipped command and is
ignored. An entry marked skip-worktree is left out too: git deliberately did not check it out, so a
cone sparse checkout that leaves out hooks/ is checked for the trees it has (the full check is CI's
and a full checkout's). The rule is content, not name shape:
  - a tracked regular file is a command when its first two bytes are "#!". It must be recorded as
    100755 and be executable in the checkout, whatever its name: a launcher committed as
    bin/romp-<x>.sh without its bit is an offender. A regular file without a shebang (bin/README.md,
    hooks/README.md) is documentation, not a command.
  - a tracked symlink is a command unless its name carries an extension. The four bin/romp_*.py
    symlinks (romp_colormap.py, romp_palette.py, romp_sdk_backend.py, romp_session_backend.py) are
    import shims through which the kernel's modules are reached by name, never run (bin/README.md
    lists them; their targets carry no shebang or serve as an ABC, and git records the targets as
    100644, the links as 120000). A command symlink is followed to its target, which must exist
    inside the repo, be recorded as 100755 and be executable in the checkout, so a dangling or
    escaping link is an offender too.
hooks/* and .githooks/* fall under the same rules: install.sh links the hooks into the harness's hooks
dir and .githooks/pre-push into git's hook dir, both of which run them by path, and git skips a
pre-push hook that is not executable with a hint and pushes the commits unscanned.
Both tests skip only when git is not installed or git says the tree is not a repository (the command
list itself comes from the index); any other git failure, dubious ownership included, fails them with
git's stderr, since a skip there would disarm the check while the run stays green. Loads nothing from
the kernel; the repo root is derived from this file's location. The ScratchCheckout class pins the
negative cases against a scratch repository of its own, whose git runs with every GIT_* variable of the
process scrubbed (GIT_INDEX_FILE above all: git exports it to a hook as an absolute path) and reads none
of the machine's own git files, so nothing here touches this repo's index or working tree.
"""
import os
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
# The trees whose direct children are commands.
TREES = ("bin", "hooks", ".githooks")
# Entries the walk must reach for the scope rule to be doing its job: the CLI itself, a plain file,
# the symlink whose target lost its bit in the incident this module answers, and the git hook.
MUST_REACH = ("bin/romp", "bin/romp-kernel", ".githooks/pre-push")
SYMLINK = "120000"
# git ls-files -t's tag for an entry git deliberately did not check out
SKIP_WORKTREE = "S"
# git's own wording for a tree with no repository above it; the one nonzero exit that is a skip
NOT_A_REPOSITORY = "not a git repository"
EXECUTABLE = "100755"


def _index(root=ROOT, env=None):
    """Recorded mode by repo-relative path for every entry in git's index at `root`. Skips the caller
    only when git is not installed or says `root` is not in a repository; any other failure is an
    AssertionError carrying git's stderr, never a skip. `env` is the environment git runs under; the
    real checkout inherits the process's (a hook's GIT_INDEX_FILE is the right index to read there),
    the scratch class passes its scrubbed one. Entries tagged skip-worktree are left out: they are
    not checked out, so they are neither commands nor missing."""
    # -t prefixes each entry with its status tag (H cached, S skip-worktree). git-ls-files(1) calls the
    # flag semi-deprecated in favour of git status, but it is the one listing that exposes skip-worktree,
    # and git 2.43 honours it.
    try:
        proc = subprocess.run(["git", "ls-files", "-s", "-t", "-z"], cwd=root, env=env,
                              capture_output=True, text=True, timeout=60)
    except FileNotFoundError:
        raise unittest.SkipTest("git is not installed; the recorded modes cannot be read")
    if proc.returncode != 0:
        if NOT_A_REPOSITORY in proc.stderr:
            raise unittest.SkipTest("not a git checkout (git ls-files exited %d: %s)"
                                    % (proc.returncode, proc.stderr.strip()))
        raise AssertionError("git ls-files exited %d in %s, so the recorded modes cannot be read and the "
                             "check would be disarmed; fix the checkout rather than skipping:\n%s"
                             % (proc.returncode, root, proc.stderr.strip()))
    recorded = {}
    for entry in proc.stdout.split("\0"):
        if not entry:
            continue
        meta, _, path = entry.partition("\t")
        tag, mode = meta.split()[:2]
        if tag == SKIP_WORKTREE:
            continue
        recorded[path] = mode
    return recorded


def _commands(root, recorded):
    """(repo-relative path, resolved target) for every command directly under the trees, plus the
    tracked entries the walk could not resolve, each with its reason."""
    real_root = os.path.realpath(root)
    commands, unresolved = [], []
    for rel in sorted(recorded):
        tree, _, name = rel.partition("/")
        if tree not in TREES or not name or "/" in name:
            continue
        path = os.path.join(real_root, rel)
        if not os.path.lexists(path):
            unresolved.append("%s: tracked but missing from the working tree" % rel)
            continue
        if recorded[rel] == SYMLINK:
            if os.path.splitext(name)[1]:
                continue  # an import shim, reached by module name and never run
            target = os.path.realpath(path)
            if not os.path.exists(target):
                unresolved.append("%s: dangling symlink (target %s does not exist)"
                                  % (rel, os.path.relpath(target, real_root)))
                continue
            if not target.startswith(real_root + os.sep):
                unresolved.append("%s: resolves outside the repo" % rel)
                continue
            if not os.path.isfile(target):
                unresolved.append("%s: resolves to something that is not a regular file" % rel)
                continue
            commands.append((rel, target))
            continue
        if not os.path.isfile(path):
            unresolved.append("%s: recorded as a regular file but is not one in the working tree" % rel)
            continue
        with open(path, "rb") as f:
            if f.read(2) != b"#!":
                continue  # documentation, not a command
        commands.append((rel, path))
    return commands, unresolved


def _describe(rel, target, root):
    target_rel = os.path.relpath(target, os.path.realpath(root))
    return rel if target_rel == rel else "%s -> %s" % (rel, target_rel)


def _checkout_offenders(commands, root):
    """Commands whose resolved target is not executable in the working tree."""
    return [_describe(rel, target, root) for rel, target in commands if not os.access(target, os.X_OK)]


def _index_offenders(commands, recorded, root):
    """Resolved targets git does not record as 100755, or does not record at all."""
    real_root = os.path.realpath(root)
    offenders = []
    for target_rel in sorted({os.path.relpath(target, real_root) for _, target in commands}):
        mode = recorded.get(target_rel)
        if mode is None:
            offenders.append("%s: not in the index" % target_rel)
        elif mode != EXECUTABLE:
            offenders.append("%s: recorded as %s" % (target_rel, mode))
    return offenders


class EntryPointsExecutable(unittest.TestCase):

    def setUp(self):
        self.recorded = _index()
        self.commands, unresolved = _commands(ROOT, self.recorded)
        self.assertEqual(unresolved, [], "every command must resolve to a file inside the repo:\n"
                         + "\n".join(unresolved))
        paths = [rel for rel, _ in self.commands]
        for must in MUST_REACH:
            self.assertIn(must, paths, "the walk no longer reaches %s; re-check the scope rule" % must)

    def test_every_command_and_its_target_is_executable_in_the_checkout(self):
        offenders = _checkout_offenders(self.commands, ROOT)
        self.assertEqual(offenders, [], "commands under bin/, hooks/ and .githooks/ (and the files their "
                         "symlinks reach) must be executable; the served tests spawn bin/romp-kernel by path "
                         "and fail with PermissionError otherwise, bin/romp-serve refuses a kernel without the "
                         "bit, and git skips a non-executable pre-push hook and pushes unscanned. Restore with "
                         "chmod +x and commit the mode change:\n" + "\n".join(offenders))

    def test_git_records_mode_100755_for_every_command_and_its_target(self):
        offenders = _index_offenders(self.commands, self.recorded, ROOT)
        self.assertEqual(offenders, [], "git must record every command and every symlink target as "
                         "100755; a whole-file rewrite that drops the bit lands as 100644 and breaks every "
                         "kernel launch (or hook run) from a fresh checkout. Fix with git update-index "
                         "--chmod=+x <path> and commit:\n" + "\n".join(offenders))


class ScratchCheckout(unittest.TestCase):
    """The rules against a scratch repository, so the negative cases are pinned without touching this
    repo's index or working tree: a shebang file recorded as 100644 is an offender in both layers
    whatever its name, a file without a shebang and a symlink with an extension are not commands, an
    untracked file is not a command, a symlink target without its bit is named through its link, a
    hook under hooks/ or .githooks/ is held to the same rules, an entry marked skip-worktree and absent
    from the tree is neither a command nor missing, and the index reader skips for a missing git or
    repository only. The scratch git runs under env(): it sees neither the index a
    run from a hook inherits nor the machine's own git config, hooks or excludes file."""

    def setUp(self):
        try:
            subprocess.run(["git", "--version"], capture_output=True, timeout=60)
        except FileNotFoundError:
            self.skipTest("git is not installed")
        self.root = os.path.realpath(tempfile.mkdtemp(prefix="entrypoints-"))
        self.addCleanup(shutil.rmtree, self.root, True)
        self.xdg = tempfile.mkdtemp(prefix="entrypoints-xdg-")
        self.addCleanup(shutil.rmtree, self.xdg, True)
        self.git("init", "-q")
        self.write("bin/romp", "#!/bin/sh\n", 0o755)
        self.write("kernel/kernel.py", "#!/usr/bin/env python3\n", 0o755)
        os.symlink("../kernel/kernel.py", self.path("bin/romp-kernel"))
        self.write("bin/README.md", "# bin\n", 0o644)
        self.write("kernel/shim.py", '"""a module reached by name"""\n', 0o644)
        os.symlink("../kernel/shim.py", self.path("bin/romp_shim.py"))
        # the launcher committed without its bit: a shebang file with an extension, recorded 100644
        self.write("bin/romp-x.sh", "#!/bin/sh\n", 0o644)
        self.write(".githooks/pre-push", "#!/bin/sh\n", 0o755)
        self.write("hooks/romp-hook.sh", "#!/bin/sh\n", 0o755)
        self.write("hooks/README.md", "# hooks\n", 0o644)
        self.git("add", "--", "bin", "kernel", ".githooks", "hooks")
        # untracked, so not a shipped command whatever it looks like
        self.write("bin/stray", "#!/bin/sh\n", 0o644)

    def path(self, rel):
        return os.path.join(self.root, rel)

    def write(self, rel, text, mode):
        os.makedirs(os.path.dirname(self.path(rel)), exist_ok=True)
        with open(self.path(rel), "w") as f:
            f.write(text)
        os.chmod(self.path(rel), mode)

    def env(self):
        """The scratch git's environment, built at call time from the process's. Every GIT_* variable
        is dropped, GIT_INDEX_FILE above all: git exports it, with GIT_DIR, to a hook as an absolute
        path, so a run from a pre-commit hook would otherwise send the scratch repo's add and
        update-index into this checkout's index (and a GIT_DIR of its own is not set in its place: an
        explicit GIT_DIR skips the ownership check the dubious-ownership test provokes). The GIT_TEST_*
        knobs stay, since that test sets one in os.environ. No global or system config is read, and
        XDG_CONFIG_HOME is a scratch dir, so a hooksPath, a template dir or a git/ignore of the
        machine's own does not reach it (a global ignore listing bin/ would fail every git add here;
        one listing *.sh would drop files silently). HOME is left alone."""
        env = {name: value for name, value in os.environ.items()
               if not name.startswith("GIT_") or name.startswith("GIT_TEST_")}
        env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1", XDG_CONFIG_HOME=self.xdg)
        return env

    def git(self, *args):
        return subprocess.run(["git"] + list(args), cwd=self.root, env=self.env(), check=True,
                              capture_output=True, text=True, timeout=60).stdout

    def walk(self):
        recorded = _index(self.root, self.env())
        commands, unresolved = _commands(self.root, recorded)
        return recorded, commands, unresolved

    def index_failure(self):
        """The message of the AssertionError _index raises for the scratch root; a skip there is the
        hole this class pins, so it is a failure of the test, never a skip of it."""
        try:
            _index(self.root, self.env())
        except unittest.SkipTest as skip:
            self.fail("the index reader skipped instead of failing: %s" % skip)
        except AssertionError as error:
            return str(error)
        self.fail("the index reader returned a listing instead of failing")

    def test_the_walk_is_the_index_and_the_rule_is_the_shebang(self):
        recorded, commands, unresolved = self.walk()
        self.assertEqual(unresolved, [])
        self.assertEqual([rel for rel, _ in commands],
                         [".githooks/pre-push", "bin/romp", "bin/romp-kernel", "bin/romp-x.sh", "hooks/romp-hook.sh"])
        self.assertEqual(recorded["bin/romp-x.sh"], "100644")
        self.assertEqual(recorded["bin/romp_shim.py"], SYMLINK)
        self.assertNotIn("bin/stray", recorded)

    def test_a_shebang_file_recorded_100644_is_an_offender_in_both_layers_whatever_its_name(self):
        recorded, commands, _ = self.walk()
        self.assertEqual(_checkout_offenders(commands, self.root), ["bin/romp-x.sh"])
        self.assertEqual(_index_offenders(commands, recorded, self.root), ["bin/romp-x.sh: recorded as 100644"])
        # the two layers are separate: restoring the bit in the checkout leaves the recorded mode wrong
        os.chmod(self.path("bin/romp-x.sh"), 0o755)
        recorded, commands, _ = self.walk()
        self.assertEqual(_checkout_offenders(commands, self.root), [])
        self.assertEqual(_index_offenders(commands, recorded, self.root), ["bin/romp-x.sh: recorded as 100644"])
        self.git("update-index", "--chmod=+x", "bin/romp-x.sh")
        recorded, commands, _ = self.walk()
        self.assertEqual(_index_offenders(commands, recorded, self.root), [])

    def test_a_symlink_target_without_its_bit_is_named_through_its_link(self):
        os.chmod(self.path("kernel/kernel.py"), 0o644)
        recorded, commands, _ = self.walk()
        self.assertEqual(_checkout_offenders(commands, self.root), ["bin/romp-kernel -> kernel/kernel.py", "bin/romp-x.sh"])
        self.assertEqual(_index_offenders(commands, recorded, self.root), ["bin/romp-x.sh: recorded as 100644"])
        self.git("update-index", "--chmod=-x", "kernel/kernel.py")
        recorded, commands, _ = self.walk()
        self.assertEqual(_index_offenders(commands, recorded, self.root),
                         ["bin/romp-x.sh: recorded as 100644", "kernel/kernel.py: recorded as 100644"])

    def test_a_dangling_or_escaping_symlink_and_a_missing_file_are_unresolved(self):
        outside = tempfile.mkdtemp(prefix="entrypoints-outside-")
        self.addCleanup(shutil.rmtree, outside, True)
        with open(os.path.join(outside, "tool"), "w") as f:
            f.write("#!/bin/sh\n")
        os.symlink("../kernel/gone.py", self.path("bin/romp-gone"))
        os.symlink(os.path.join(outside, "tool"), self.path("bin/romp-out"))
        self.git("add", "--", "bin/romp-gone", "bin/romp-out")
        os.remove(self.path("bin/romp"))
        _, commands, unresolved = self.walk()
        self.assertEqual(unresolved, ["bin/romp: tracked but missing from the working tree",
                                      "bin/romp-gone: dangling symlink (target kernel/gone.py does not exist)",
                                      "bin/romp-out: resolves outside the repo"])
        self.assertEqual([rel for rel, _ in commands],
                         [".githooks/pre-push", "bin/romp-kernel", "bin/romp-x.sh", "hooks/romp-hook.sh"])

    def test_a_hook_without_its_bit_is_an_offender_in_both_layers(self):
        os.chmod(self.path(".githooks/pre-push"), 0o644)
        self.git("update-index", "--chmod=-x", "hooks/romp-hook.sh")
        recorded, commands, _ = self.walk()
        self.assertEqual(_checkout_offenders(commands, self.root), [".githooks/pre-push", "bin/romp-x.sh"])
        self.assertEqual(_index_offenders(commands, recorded, self.root),
                         ["bin/romp-x.sh: recorded as 100644", "hooks/romp-hook.sh: recorded as 100644"])

    def test_a_skip_worktree_entry_absent_from_the_tree_is_neither_a_command_nor_missing(self):
        # what a cone sparse checkout that leaves out hooks/ looks like: the entry stays in the index,
        # tagged S, and git removed it from the working tree
        self.git("update-index", "--skip-worktree", "hooks/romp-hook.sh")
        os.remove(self.path("hooks/romp-hook.sh"))
        recorded, commands, unresolved = self.walk()
        self.assertEqual(unresolved, [])
        self.assertNotIn("hooks/romp-hook.sh", recorded)
        self.assertEqual([rel for rel, _ in commands], [".githooks/pre-push", "bin/romp", "bin/romp-kernel", "bin/romp-x.sh"])
        # the same entry removed without the mark is missing, so the tag is what the walk reads
        self.git("update-index", "--no-skip-worktree", "hooks/romp-hook.sh")
        recorded, commands, unresolved = self.walk()
        self.assertEqual(unresolved, ["hooks/romp-hook.sh: tracked but missing from the working tree"])
        self.assertEqual(recorded["hooks/romp-hook.sh"], EXECUTABLE)

    def test_the_scratch_git_sees_neither_an_inherited_index_nor_the_machines_git_files(self):
        # a second scratch repo stands in for this checkout: git exports GIT_DIR and GIT_INDEX_FILE to
        # a hook as absolute paths, so a run from a pre-commit hook inherits another repository's index
        decoy = os.path.realpath(tempfile.mkdtemp(prefix="entrypoints-decoy-"))
        self.addCleanup(shutil.rmtree, decoy, True)
        clean = self.env()
        subprocess.run(["git", "init", "-q"], cwd=decoy, env=clean, check=True, capture_output=True, timeout=60)
        with open(os.path.join(decoy, "kept"), "w") as f:
            f.write("kept\n")
        subprocess.run(["git", "add", "--", "kept"], cwd=decoy, env=clean, check=True, capture_output=True, timeout=60)
        index = os.path.join(decoy, ".git", "index")
        with open(index, "rb") as f:
            before = f.read()
        # and a global excludes file of the machine's own, listing the scratch repo's own trees
        xdg = tempfile.mkdtemp(prefix="entrypoints-hostile-xdg-")
        self.addCleanup(shutil.rmtree, xdg, True)
        os.makedirs(os.path.join(xdg, "git"))
        with open(os.path.join(xdg, "git", "ignore"), "w") as f:
            f.write("bin/\n*.sh\n")
        inherited = {"GIT_DIR": os.path.join(decoy, ".git"), "GIT_WORK_TREE": decoy, "GIT_INDEX_FILE": index,
                     "XDG_CONFIG_HOME": xdg}
        with patch.dict(os.environ, inherited):
            self.assertEqual(self.git("rev-parse", "--git-path", "index").strip(), ".git/index")
            self.write("bin/romp-late", "#!/bin/sh\n", 0o755)
            self.write("hooks/romp-late.sh", "#!/bin/sh\n", 0o755)
            self.git("add", "--", "bin/romp-late", "hooks/romp-late.sh")
            self.git("update-index", "--chmod=-x", "bin/romp")
            recorded, commands, unresolved = self.walk()
        self.assertEqual(unresolved, [])
        self.assertEqual(recorded["bin/romp-late"], EXECUTABLE)
        self.assertEqual(recorded["hooks/romp-late.sh"], EXECUTABLE)
        self.assertEqual(recorded["bin/romp"], "100644")
        self.assertNotIn("kept", recorded)
        self.assertIn("bin/romp-late", [rel for rel, _ in commands])
        with open(index, "rb") as f:
            self.assertEqual(f.read(), before, "the scratch git wrote the index it inherited")

    def test_the_index_reader_skips_for_a_missing_git_or_repository_only(self):
        def completed(stderr):
            return subprocess.CompletedProcess(args=["git"], returncode=128, stdout="", stderr=stderr)
        with patch.object(subprocess, "run", side_effect=FileNotFoundError("git")):
            with self.assertRaises(unittest.SkipTest):
                _index(self.root)
        with patch.object(subprocess, "run",
                          return_value=completed("fatal: not a git repository (or any of the parent directories): .git")):
            with self.assertRaises(unittest.SkipTest):
                _index(self.root)
        # every other nonzero exit is a failure that carries git's words, never a skip
        with patch.object(subprocess, "run",
                          return_value=completed("fatal: detected dubious ownership in repository at '/a/checkout'")):
            message = self.index_failure()
        self.assertIn("dubious ownership", message)
        self.assertIn("exited 128", message)

    def test_a_real_dubious_ownership_failure_fails_not_skips(self):
        # git honours GIT_TEST_ASSUME_DIFFERENT_OWNER since 2.35.2 and then refuses the repository the
        # way a container or a shared checkout provokes; a git that ignores it cannot pin this case
        with patch.dict(os.environ, {"GIT_TEST_ASSUME_DIFFERENT_OWNER": "1"}):
            probe = subprocess.run(["git", "ls-files", "-s", "-z"], cwd=self.root, env=self.env(),
                                   capture_output=True, text=True, timeout=60)
            if probe.returncode == 0:
                self.skipTest("this git ignores GIT_TEST_ASSUME_DIFFERENT_OWNER")
            message = self.index_failure()
        self.assertIn(probe.stderr.strip().splitlines()[0], message)


if __name__ == "__main__":
    unittest.main()
