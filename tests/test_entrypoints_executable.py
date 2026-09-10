#!/usr/bin/env python3
"""Every command under bin/ stays executable, in the checkout and in the mode git records (2026-09-10).

bin/romp-kernel is a symlink to kernel/kernel.py and bin/romp-serve execs it, so a kernel.py without
its executable bit fails every kernel launch with PermissionError. On 2026-09-10 a whole-file rewrite
of kernel/kernel.py was committed on a PR branch as mode 100644: every served browser test in the
local sweep errored launching the kernel, and CI stayed green, because the served modules skip there
without Playwright and nothing on CI read the mode. These two tests read it, one from the working
tree and one from the index, so a checkout whose bits were restored by hand still fails on the
recorded mode.

Scope: the commands under bin/, which is every entry that is neither a directory nor a file with
an extension. The two kinds of entry with one are not commands: bin/README.md is documentation, and the `romp_*.py` symlinks are
import shims through which the kernel's modules are reached by name (bin/README.md lists them; their
targets carry no shebang or serve as an ABC, and git records them as 100644). A symlink is followed
to its target, which must exist inside the repo, so a dangling or escaping link is an offender too.
Loads nothing from the kernel; the repo root is derived from this file's location.
"""
import os
import subprocess
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
# Two entries the walk must reach for the scope rule to be doing its job: the CLI itself, a plain
# file, and the symlink whose target lost its bit in the incident this module answers.
MUST_REACH = ("romp", "romp-kernel")


def _commands():
    """(name, resolved target) for every command under bin/, plus the names of entries the walk
    could not resolve, each with its reason. A command is an entry without a file extension; a
    symlink's target is its fully resolved path."""
    commands, unresolved = [], []
    root = os.path.realpath(ROOT)
    for name in sorted(os.listdir(BIN)):
        path = os.path.join(BIN, name)
        # a directory (bin/__pycache__ once anything imports the shims) is not a command either
        if os.path.splitext(name)[1] or os.path.isdir(path):
            continue
        target = os.path.realpath(path)
        if not os.path.exists(target):
            unresolved.append("%s: dangling symlink (target %s does not exist)"
                              % (name, os.path.relpath(target, root)))
            continue
        if not target.startswith(root + os.sep):
            unresolved.append("%s: resolves outside the repo" % name)
            continue
        if not os.path.isfile(target):
            unresolved.append("%s: resolves to something that is not a regular file" % name)
            continue
        commands.append((name, target))
    return commands, unresolved


def _describe(name, target):
    rel = os.path.relpath(target, os.path.realpath(ROOT))
    return "bin/%s" % name if rel == os.path.join("bin", name) else "bin/%s -> %s" % (name, rel)


class EntryPointsExecutable(unittest.TestCase):

    def setUp(self):
        self.commands, unresolved = _commands()
        self.assertEqual(unresolved, [], "every bin/ command must resolve to a file inside the repo:\n"
                         + "\n".join(unresolved))
        names = [n for n, _ in self.commands]
        for must in MUST_REACH:
            self.assertIn(must, names, "the walk over bin/ no longer reaches %s; re-check the scope rule" % must)

    def test_every_command_and_its_target_is_executable_in_the_checkout(self):
        offenders = [_describe(n, t) for n, t in self.commands if not os.access(t, os.X_OK)]
        self.assertEqual(offenders, [], "bin/ commands (and the files their symlinks reach) must be "
                         "executable; bin/romp-serve execs bin/romp-kernel and fails with PermissionError "
                         "otherwise. Restore with chmod +x and commit the mode change:\n" + "\n".join(offenders))

    def test_git_records_mode_100755_for_every_command_and_its_target(self):
        root = os.path.realpath(ROOT)
        rels = sorted({os.path.relpath(t, root) for _, t in self.commands})
        try:
            proc = subprocess.run(["git", "ls-files", "-s", "-z", "--"] + rels, cwd=root,
                                  capture_output=True, text=True, timeout=60)
        except FileNotFoundError:
            self.skipTest("git is not installed; the recorded mode cannot be read")
        if proc.returncode != 0:
            self.skipTest("not a git checkout (git ls-files exited %d: %s)"
                          % (proc.returncode, proc.stderr.strip()))
        recorded = {}
        for entry in proc.stdout.split("\0"):
            if not entry:
                continue
            meta, _, path = entry.partition("\t")
            recorded[path] = meta.split()[0]
        offenders = []
        for rel in rels:
            mode = recorded.get(rel)
            if mode is None:
                offenders.append("%s: not in the index" % rel)
            elif mode != "100755":
                offenders.append("%s: recorded as %s" % (rel, mode))
        self.assertEqual(offenders, [], "git must record every bin/ command's target as 100755; a "
                         "whole-file rewrite that drops the bit lands as 100644 and breaks every kernel "
                         "launch from a fresh checkout. Fix with git update-index --chmod=+x <path> and "
                         "commit:\n" + "\n".join(offenders))


if __name__ == "__main__":
    unittest.main()
