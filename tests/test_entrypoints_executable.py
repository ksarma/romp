#!/usr/bin/env python3
"""Every command under bin/ stays executable, in the checkout and in the mode git records (2026-09-10).

bin/romp-kernel is a symlink to kernel/kernel.py and bin/romp-serve execs it, so a kernel.py without
its executable bit fails every kernel launch with PermissionError. On 2026-09-10 a whole-file rewrite
of kernel/kernel.py was committed on a PR branch as mode 100644: every served browser test in the
local sweep errored launching the kernel, and CI stayed green, because the served modules skip there
without Playwright and nothing on CI read the mode. These two tests read it, one from the working
tree and one from the index, so a checkout whose bits were restored by hand still fails on the
recorded mode.

Scope: the entries git tracks directly under bin/, enumerated from the index and never from the
working tree's listing, so an untracked stray file in bin/ is not a shipped command and is ignored.
The rule is content, not name shape:
  - a tracked regular file is a command when its first two bytes are "#!". It must be recorded as
    100755 and be executable in the checkout, whatever its name: a launcher committed as
    bin/romp-<x>.sh without its bit is an offender. A regular file without a shebang (bin/README.md)
    is documentation, not a command.
  - a tracked symlink is a command unless its name carries an extension. The four bin/romp_*.py
    symlinks (romp_colormap.py, romp_palette.py, romp_sdk_backend.py, romp_session_backend.py) are
    import shims through which the kernel's modules are reached by name, never run (bin/README.md
    lists them; their targets carry no shebang or serve as an ABC, and git records the targets as
    100644, the links as 120000). A command symlink is followed to its target, which must exist
    inside the repo, be recorded as 100755 and be executable in the checkout, so a dangling or
    escaping link is an offender too.
Both tests skip only when git is not installed or git says the tree is not a repository (the command
list itself comes from the index); any other git failure, dubious ownership included, fails them with
git's stderr, since a skip there would disarm the check while the run stays green. Loads nothing from
the kernel; the repo root is derived from this file's location. The ScratchCheckout class pins the negative cases against a scratch repository of
its own, so nothing here touches this repo's index or working tree.
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
TREES = ("bin",)
# Entries the walk must reach for the scope rule to be doing its job: the CLI itself, a plain file,
# and the symlink whose target lost its bit in the incident this module answers.
MUST_REACH = ("bin/romp", "bin/romp-kernel")
SYMLINK = "120000"
# git's own wording for a tree with no repository above it; the one nonzero exit that is a skip
NOT_A_REPOSITORY = "not a git repository"
EXECUTABLE = "100755"


def _index(root=ROOT):
    """Recorded mode by repo-relative path for every entry in git's index at `root`. Skips the caller
    only when git is not installed or says `root` is not in a repository; any other failure is an
    AssertionError carrying git's stderr, never a skip."""
    try:
        proc = subprocess.run(["git", "ls-files", "-s", "-z"], cwd=root,
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
        recorded[path] = meta.split()[0]
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
        self.assertEqual(unresolved, [], "every bin/ command must resolve to a file inside the repo:\n"
                         + "\n".join(unresolved))
        paths = [rel for rel, _ in self.commands]
        for must in MUST_REACH:
            self.assertIn(must, paths, "the walk over bin/ no longer reaches %s; re-check the scope rule" % must)

    def test_every_command_and_its_target_is_executable_in_the_checkout(self):
        offenders = _checkout_offenders(self.commands, ROOT)
        self.assertEqual(offenders, [], "bin/ commands (and the files their symlinks reach) must be "
                         "executable; bin/romp-serve execs bin/romp-kernel and fails with PermissionError "
                         "otherwise. Restore with chmod +x and commit the mode change:\n" + "\n".join(offenders))

    def test_git_records_mode_100755_for_every_command_and_its_target(self):
        offenders = _index_offenders(self.commands, self.recorded, ROOT)
        self.assertEqual(offenders, [], "git must record every bin/ command's target as 100755; a "
                         "whole-file rewrite that drops the bit lands as 100644 and breaks every kernel "
                         "launch from a fresh checkout. Fix with git update-index --chmod=+x <path> and "
                         "commit:\n" + "\n".join(offenders))


class ScratchCheckout(unittest.TestCase):
    """The rules against a scratch repository, so the negative cases are pinned without touching this
    repo's index or working tree: a shebang file recorded as 100644 is an offender in both layers
    whatever its name, a file without a shebang and a symlink with an extension are not commands, an
    untracked file is not a command, a symlink target without its bit is named through its link, and
    the index reader skips for a missing git or repository only."""

    def setUp(self):
        try:
            subprocess.run(["git", "--version"], capture_output=True, timeout=60)
        except FileNotFoundError:
            self.skipTest("git is not installed")
        self.root = os.path.realpath(tempfile.mkdtemp(prefix="entrypoints-"))
        self.addCleanup(shutil.rmtree, self.root, True)
        self.git("init", "-q")
        self.write("bin/romp", "#!/bin/sh\n", 0o755)
        self.write("kernel/kernel.py", "#!/usr/bin/env python3\n", 0o755)
        os.symlink("../kernel/kernel.py", self.path("bin/romp-kernel"))
        self.write("bin/README.md", "# bin\n", 0o644)
        self.write("kernel/shim.py", '"""a module reached by name"""\n', 0o644)
        os.symlink("../kernel/shim.py", self.path("bin/romp_shim.py"))
        # the launcher committed without its bit: a shebang file with an extension, recorded 100644
        self.write("bin/romp-x.sh", "#!/bin/sh\n", 0o644)
        self.git("add", "--", "bin", "kernel")
        # untracked, so not a shipped command whatever it looks like
        self.write("bin/stray", "#!/bin/sh\n", 0o644)

    def path(self, rel):
        return os.path.join(self.root, rel)

    def write(self, rel, text, mode):
        os.makedirs(os.path.dirname(self.path(rel)), exist_ok=True)
        with open(self.path(rel), "w") as f:
            f.write(text)
        os.chmod(self.path(rel), mode)

    def git(self, *args):
        # the scratch repo reads no global or system config, so a hooksPath or a template dir of the
        # machine's own does not reach it
        env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
        env.pop("GIT_DIR", None)
        env.pop("GIT_WORK_TREE", None)
        subprocess.run(["git"] + list(args), cwd=self.root, env=env, check=True,
                       capture_output=True, text=True, timeout=60)

    def walk(self):
        recorded = _index(self.root)
        commands, unresolved = _commands(self.root, recorded)
        return recorded, commands, unresolved

    def index_failure(self):
        """The message of the AssertionError _index raises for the scratch root; a skip there is the
        hole this class pins, so it is a failure of the test, never a skip of it."""
        try:
            _index(self.root)
        except unittest.SkipTest as skip:
            self.fail("the index reader skipped instead of failing: %s" % skip)
        except AssertionError as error:
            return str(error)
        self.fail("the index reader returned a listing instead of failing")

    def test_the_walk_is_the_index_and_the_rule_is_the_shebang(self):
        recorded, commands, unresolved = self.walk()
        self.assertEqual(unresolved, [])
        self.assertEqual([rel for rel, _ in commands], ["bin/romp", "bin/romp-kernel", "bin/romp-x.sh"])
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
        self.assertEqual([rel for rel, _ in commands], ["bin/romp-kernel", "bin/romp-x.sh"])

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
            probe = subprocess.run(["git", "ls-files", "-s", "-z"], cwd=self.root,
                                   capture_output=True, text=True, timeout=60)
            if probe.returncode == 0:
                self.skipTest("this git ignores GIT_TEST_ASSUME_DIFFERENT_OWNER")
            message = self.index_failure()
        self.assertIn(probe.stderr.strip().splitlines()[0], message)


if __name__ == "__main__":
    unittest.main()
