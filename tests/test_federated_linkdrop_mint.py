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
class's teardown runs no command at all (the lab's rmtree takes the checkout), spied the same way; and no string constant
in the lab module's source, in either quoting, is such an argv token (an ast walk, so a spelling cannot slip past it; a
token assembled at run time or joined into one shell string is what the two spies are for, not this census).

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


def _git(*args):
    """A git command for the test's own scratch (Popen, not run: the tests spy on subprocess.run around the mint, and
    the spy must see the mint's commands only)."""
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

    def _spy(self, real):
        seen = []

        def run(cmd, *a, **k):
            seen.append(list(cmd))
            return real(cmd, *a, **k)
        return seen, run

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
        real = subprocess.run
        seen, run = self._spy(real)
        with mock.patch.object(L.subprocess, "run", run):
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
        real = subprocess.run
        seen, spy = self._spy(real)

        def killed_at_the_clone(cmd, *a, **k):
            if cmd[:2] == ["git", "clone"]:
                seen.append(list(cmd))
                p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                p.kill()   # the drill: the mint's git dies as the clone starts (a SIGKILL mid-mint, the failure path)
                out, err = p.communicate()
                return subprocess.CompletedProcess(cmd, p.returncode if p.returncode else -9, out, err or "killed as the clone started (the drill)")
            return spy(cmd, *a, **k)
        with mock.patch.object(L.subprocess, "run", killed_at_the_clone):
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
        """The class's teardown with nothing to stop (no procs, no door, no splice) runs no subprocess at all: the lab's
        rmtree takes the checkout, and no git command of the class names the source (round 1's teardown ran a repo-wide
        record clearing there). Behavioural, so the spelling of an argv token cannot matter."""
        real = subprocess.run
        seen, run = self._spy(real)
        with mock.patch.object(L.subprocess, "run", run):
            self.Mint.tearDownClass()
        self._assert_commands_are_private(seen, expect_commands=False)
        self.assertEqual(seen, [], "a clean teardown runs no command: %r" % (seen,))
        self.assertFalse(os.path.exists(self.lab), "…and the lab is gone")
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


if __name__ == "__main__":
    unittest.main()
