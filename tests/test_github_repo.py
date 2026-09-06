#!/usr/bin/env python3
"""_github_repo_of and the frames that carry it — the repository a session's PR references link to
(the user 2026-09-06: `#123` / `PR #123` in a session's chat, cards and notes should link to the PR
page of the repository the session works in). The kernel names that repository per session from the
authoritative source, the session tree's origin remote, through the SAME parser the file viewer's
GitHub link uses (_GITHUB_REMOTE). None is a VERDICT, not an error: no repo, no origin, or an origin
elsewhere names no GitHub repository, and the clients then link nothing rather than guess.

Throwaway temp repos with fabricated origins (example-org/notes-api — the demo world); nothing here
reaches a network (no fetch, no ls-remote — `remote get-url` reads config). The registry-keyed check
uses a PRIVATE synthetic sid (the goal-store fixture rule, applied to the names registry too).
"""
import inspect
import os
import subprocess
import tempfile
import unittest
from importlib.machinery import SourceFileLoader

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the load — the kernel resolves its state root at import time, and only pytest
# runs conftest's floor (a bare unittest run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
km = SourceFileLoader("romp_kernel_github_repo", os.path.join(BIN, "romp-kernel")).load_module()

HTTPS_ORIGIN = "https://github.com/example-org/notes-api.git"
SSH_ORIGIN = "git@github.com:example-org/notes-api.git"
ELSEWHERE_ORIGIN = "https://gitlab.example.com/example-org/notes-api.git"
REPO = "example-org/notes-api"
# a private synthetic sid: never the shared 11111111-2222-… placeholder (another module's journaled
# state can land on that one), never a real session's
PRIVATE_SID = "7a7a7a7a-1a1a-4b4b-8c8c-9d9d9d9d9d9d"


def _git(*args, cwd):
    subprocess.run(["git", "-c", "user.email=t@TESTHOST", "-c", "user.name=t"] + list(args),
                   cwd=cwd, check=True, capture_output=True)


def _repo(root, name, origin=None):
    """A one-commit repo on branch main under `root`, with `origin` set when given."""
    d = os.path.join(root, name)
    os.makedirs(d)
    _git("init", "-q", "-b", "main", cwd=d)
    with open(os.path.join(d, "f.txt"), "w") as f:
        f.write("x\n")
    _git("add", "f.txt", cwd=d)
    _git("commit", "-q", "-m", "seed", cwd=d)
    if origin:
        _git("remote", "add", "origin", origin, cwd=d)
    return d


def _bump_mtime(path):
    """Move a file's mtime forward by a whole second, so a rewrite within the same clock tick still
    reads as a change — the memo keys on mtime, and the test must not depend on filesystem resolution."""
    st = os.stat(path)
    os.utime(path, (st.st_atime, st.st_mtime + 2))


class _Fixtures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # the kernel's own git runs in the process environment (as in production): pin it to read no
        # global or system config, so a developer's url.insteadOf rewrite cannot bend a fixture origin
        cls._saved_env = {k: os.environ.get(k) for k in ("GIT_CONFIG_GLOBAL", "GIT_CONFIG_NOSYSTEM")}
        os.environ["GIT_CONFIG_GLOBAL"] = os.devnull
        os.environ["GIT_CONFIG_NOSYSTEM"] = "1"
        cls.root = tempfile.mkdtemp()
        cls.https = _repo(cls.root, "https-repo", HTTPS_ORIGIN)
        cls.sub = os.path.join(cls.https, "src", "deep")
        os.makedirs(cls.sub)
        cls.wt = os.path.join(cls.root, "https-repo-feature")
        _git("worktree", "add", "-q", "-b", "feature", cls.wt, "HEAD", cwd=cls.https)
        cls.ssh = _repo(cls.root, "ssh-repo", SSH_ORIGIN)
        cls.elsewhere = _repo(cls.root, "elsewhere-repo", ELSEWHERE_ORIGIN)
        cls.noorigin = _repo(cls.root, "no-origin-repo")
        cls.plain = os.path.join(cls.root, "not-a-repo")
        os.makedirs(cls.plain)

    @classmethod
    def tearDownClass(cls):
        for k, v in cls._saved_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


class GitHubRepoOf(_Fixtures):
    def test_an_https_origin_names_owner_and_repo_without_the_git_suffix(self):
        self.assertEqual(km._github_repo_of(self.https), REPO)

    def test_the_ssh_origin_spelling_names_the_same_repo(self):
        self.assertEqual(km._github_repo_of(self.ssh), REPO)

    def test_a_subdirectory_of_the_tree_resolves_to_the_trees_repo(self):
        self.assertEqual(km._github_repo_of(self.sub), REPO)

    def test_a_worktree_reads_the_shared_config_through_its_commondir(self):
        self.assertEqual(km._github_repo_of(self.wt), REPO)
        cfg = km._git_config_file(os.path.realpath(self.wt))
        self.assertEqual(os.path.realpath(cfg), os.path.realpath(os.path.join(self.https, ".git", "config")),
                         "the worktree's remotes live in the main tree's .git/config")

    def test_an_origin_elsewhere_is_no_github_repo(self):
        self.assertIsNone(km._github_repo_of(self.elsewhere))

    def test_no_origin_remote_is_no_github_repo(self):
        self.assertIsNone(km._github_repo_of(self.noorigin))

    def test_no_repository_is_no_github_repo(self):
        self.assertIsNone(km._github_repo_of(self.plain))
        self.assertIsNone(km._github_repo_of(""))
        self.assertIsNone(km._github_repo_of(None))

    def test_a_tilde_path_is_expanded_like_every_other_cwd(self):
        home = os.path.expanduser("~")
        if not self.https.startswith(home + os.sep):
            self.skipTest("the fixture root is not under $HOME")
        self.assertEqual(km._github_repo_of("~" + self.https[len(home):]), REPO)

    def test_the_parser_is_the_file_viewers(self):
        src = inspect.getsource(km._github_repo_of)
        self.assertIn("_GITHUB_REMOTE.match(remote)", src, "one spelling of what counts as GitHub")
        self.assertIn('_git_out(["remote", "get-url", "origin"], top)', src, "the same authoritative read")


class Memo(unittest.TestCase):
    """The answer is memoized per tree on the config file's mtime: a second build forks no git, and a
    rewritten remote (the file's mtime moving) is re-read."""

    def setUp(self):
        self._saved_env = {k: os.environ.get(k) for k in ("GIT_CONFIG_GLOBAL", "GIT_CONFIG_NOSYSTEM")}
        os.environ["GIT_CONFIG_GLOBAL"] = os.devnull
        os.environ["GIT_CONFIG_NOSYSTEM"] = "1"
        self.root = tempfile.mkdtemp()
        self.repo = _repo(self.root, "memo-repo", HTTPS_ORIGIN)
        self.cfg = os.path.join(self.repo, ".git", "config")
        self._real_git_out = km._git_out
        self.calls = []

        def counting(args, cwd, *a, **kw):
            self.calls.append(list(args))
            return self._real_git_out(args, cwd, *a, **kw)
        km._git_out = counting

    def tearDown(self):
        km._git_out = self._real_git_out
        for k, v in self._saved_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def _remote_reads(self):
        return [c for c in self.calls if c[:2] == ["remote", "get-url"]]

    def test_a_second_call_reads_the_memo_not_git(self):
        self.assertEqual(km._github_repo_of(self.repo), REPO)
        self.assertEqual(len(self._remote_reads()), 1)
        self.assertEqual(km._github_repo_of(self.repo), REPO)
        self.assertEqual(len(self._remote_reads()), 1, "an unchanged config is not re-read")

    def test_a_rewritten_remote_is_re_read(self):
        self.assertEqual(km._github_repo_of(self.repo), REPO)
        _git("remote", "set-url", "origin", "https://github.com/other-org/other-repo.git", cwd=self.repo)
        _bump_mtime(self.cfg)
        self.assertEqual(km._github_repo_of(self.repo), "other-org/other-repo")
        self.assertEqual(len(self._remote_reads()), 2)

    def test_losing_the_origin_is_a_real_change_to_none(self):
        self.assertEqual(km._github_repo_of(self.repo), REPO)
        _git("remote", "remove", "origin", cwd=self.repo)
        _bump_mtime(self.cfg)
        self.assertIsNone(km._github_repo_of(self.repo), "a null verdict replaces the memoized repo")


class RegistryPath(_Fixtures):
    """The feed's session rows derive the repo from the names registry's cwd (_cwd_of) — the same path
    the chat frame takes through scwd. A PRIVATE synthetic sid, cleaned up after."""

    def setUp(self):
        km.NAMES.mkdir(parents=True, exist_ok=True)
        (km.NAMES / PRIVATE_SID).write_text("web\t%s\t#123456\t#ffffff\n" % self.https)

    def tearDown(self):
        try:
            (km.NAMES / PRIVATE_SID).unlink()
        except FileNotFoundError:
            pass

    def test_the_registered_cwd_names_the_sessions_repo(self):
        self.assertEqual(km._cwd_of(PRIVATE_SID), self.https)
        self.assertEqual(km._github_repo_of(km._cwd_of(PRIVATE_SID)), REPO)

    def test_an_unregistered_sid_has_no_repo(self):
        self.assertIsNone(km._github_repo_of(km._cwd_of("00000000-0000-4000-8000-000000000000")))


class FrameWiring(unittest.TestCase):
    """build_session's and build_feed's wiring, pinned by source (the build_* test pattern)."""

    def test_the_session_frame_carries_the_repo_top_level(self):
        src = inspect.getsource(km.build_session)
        self.assertIn('"githubRepo": _github_repo_of(scwd),', src,
                      "top-level like gitBranch — never windowed off the wire")
        self.assertLess(src.index('"gitBranch": sysinfo["gitBranch"]'), src.index('"githubRepo": _github_repo_of(scwd)'))

    def test_the_feed_session_rows_carry_the_repo(self):
        src = inspect.getsource(km.build_feed)
        self.assertIn('"githubRepo": _github_repo_of(_cwd_of(s["sid"]))', src,
                      "each tab-strip session row names its repo, from the registry's cwd")


if __name__ == "__main__":
    unittest.main()
