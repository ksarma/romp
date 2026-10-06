"""The macOS Shell cell's two tool installs for the pre-push hook (.github/workflows/ci.yml, 2026-09-30), pinned against the
hook and against the other gitleaks installs. Source pins, as tests/test_ci_workflow_concurrency.py: no YAML library in the
test deps.

- Install bash 5.1 or later (macOS): the hook's gate (bash_gate) admits the bash its bash_admitted function admits, 5.1
  since the coordinator's ruling at 13:37Z, and the step's check compares the installed bash the same way. The threshold
  lives in two places, so this reads both numbers, the hook's from bash_admitted's body and the step's from its check, and
  fails when they differ: a threshold raised in the hook alone would let the step pass a Homebrew bottle the gate refuses,
  and the cell would fail in the test's setup instead of in the step that names the cause. The same step keeps bash 3.2
  first on PATH for the steps after it, the PATH order this cell exists for (bats and the tests run under the image's
  /bin/bash, and the hook's gate finds the newer bash at its fixed path): a directory holding only a link to /bin/bash,
  checked to report 3.2, through the Shell job's one GITHUB_PATH write. Each of the three is pinned (the focused
  re-check of fork PR 940 at d2091c2c1, 2026-10-01, found two copies that put Homebrew's bash first passing every pin
  until then: the link aimed at /opt/homebrew/bin/bash with the check deleted, and the write naming /opt/homebrew/bin),
  and the job's lines naming the directory are those four, the mkdir first, in that order, so no line re-points the
  link between the check and the write (the audit of that build: a copy relinking it to Homebrew's bash there passed).
- Install gitleaks (macOS), added the same day (romp-manager, 13:50Z): the pinned release the Linux step and the secrets
  job install, as the darwin arm64 asset, checked against its own checksum, installed where `command -v gitleaks` finds
  it, after the bash step, so the link to /bin/bash stays first on PATH. The three installs carry one version; each asset
  has its own checksum, so a bump that changes one version and not the others fails here.
"""
import os
import re
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
WF = os.path.join(ROOT, ".github", "workflows", "ci.yml")
HOOK = os.path.join(ROOT, ".githooks", "pre-push")

STEP_RE = r"^      - name: {name}\n(?P<body>(?:(?!^      - ).*\n)*)"


def step(wf, name):
    m = re.search(STEP_RE.format(name=re.escape(name)), wf, re.M)
    return m.group("body") if m else None


def admitted_threshold(text):
    """(major, minor) from a check written `[ M -gt A ] || { [ M -eq A ] && [ m -ge B ]; }`, or None."""
    m = re.search(r'\[ "\$\{?[^"]*\}?" -gt (\d+) \] \|\| \{ \[ "\$\{?[^"]*\}?" -eq (\d+) \] && \[ "\$\{?[^"]*\}?" -ge (\d+) \]; \}', text)
    if not m or m.group(1) != m.group(2):
        return None
    return int(m.group(1)), int(m.group(3))


class MacosShellTools(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(WF, encoding="utf-8") as fh:
            cls.wf = fh.read()
        with open(HOOK, encoding="utf-8") as fh:
            cls.hook = fh.read()
        m = re.search(r"^  shell:\n(.*?)^  \S", cls.wf, re.S | re.M)
        assert m, "the Shell job"
        cls.shell = m.group(1)
        cls.bash_step = step(cls.shell + "      - ", "Install bash 5.1 or later (macOS)")
        cls.gl_mac = step(cls.shell + "      - ", "Install gitleaks (macOS)")
        cls.gl_linux = step(cls.shell + "      - ", "Install gitleaks (Linux)")
        s = re.search(r"^  secrets:\n(.*?)(?=^  \S|\Z)", cls.wf, re.S | re.M)
        assert s, "the secrets job"
        cls.gl_secrets = step(s.group(1) + "      - ", "Install gitleaks")

    def test_the_steps_exist_and_the_macos_ones_run_on_macos_alone(self):
        for name, body in (("Install bash 5.1 or later (macOS)", self.bash_step), ("Install gitleaks (macOS)", self.gl_mac),
                           ("Install gitleaks (Linux)", self.gl_linux), ("the secrets job's Install gitleaks", self.gl_secrets)):
            self.assertIsNotNone(body, "no step %s" % name)
        self.assertRegex(self.bash_step, r"(?m)^        if: runner\.os == 'macOS'$")
        self.assertRegex(self.gl_mac, r"(?m)^        if: runner\.os == 'macOS'$")

    def test_the_bash_step_checks_the_threshold_the_hook_admits(self):
        m = re.search(r"^bash_admitted\(\) \{.*\n(.*)\n\}$", self.hook, re.M)
        self.assertTrue(m, "bash_admitted's one-line body in the hook")
        hook_t = admitted_threshold(m.group(1))
        self.assertIsNotNone(hook_t, "bash_admitted's body is not the two-number comparison: %r" % m.group(1))
        check = [l for l in self.bash_step.splitlines() if "/opt/homebrew/bin/bash -c" in l]
        self.assertEqual(len(check), 1, "the step runs one check of the installed bash: %r" % check)
        step_t = admitted_threshold(check[0])
        self.assertIsNotNone(step_t, "the step's check is not the two-number comparison the gate makes: %r" % check[0])
        self.assertEqual(step_t, hook_t, "the step admits %d.%d where the hook's gate admits %d.%d" % (step_t + hook_t))
        self.assertIn("BASH_VERSINFO[0]", check[0])
        self.assertIn("BASH_VERSINFO[1]", check[0])

    def test_the_bash_step_keeps_bash_3_2_first_on_path(self):
        lines = self.bash_step.splitlines()
        link = '          ln -sf /bin/bash "$RUNNER_TEMP/bash-3.2/bash"'
        check = "          PATH=\"$RUNNER_TEMP/bash-3.2:$PATH\" bash -c '[ \"${BASH_VERSINFO[0]}.${BASH_VERSINFO[1]}\" = 3.2 ]'"
        write = '          echo "$RUNNER_TEMP/bash-3.2" >> "$GITHUB_PATH"'
        self.assertEqual(lines.count(link), 1, "the step links the directory's one bash to /bin/bash: %r" % [l for l in lines if " ln " in l])
        self.assertEqual([l for l in lines if "= 3.2 ]" in l], [check], "the step checks that the first bash on PATH with the directory ahead reports 3.2")
        writes = [l for l in self.shell.splitlines() if "GITHUB_PATH" in l]
        self.assertEqual(writes, [write], "the Shell job writes GITHUB_PATH once, the directory holding the link to /bin/bash")
        self.assertIn(write, lines, "the one GITHUB_PATH write is the bash step's")
        self.assertLess(lines.index(link), lines.index(check), "the link is made before it is checked")
        self.assertLess(lines.index(check), lines.index(write), "the directory goes on PATH only after its bash is checked")
        mkdir = '          mkdir -p "$RUNNER_TEMP/bash-3.2"'
        named = [l for l in self.shell.splitlines() if "bash-3.2" in l]
        self.assertEqual(named, [mkdir, link, check, write], "the Shell job's lines naming the directory are its making, its link, its check and its write, in that order, so no line re-points the link after the check: %r" % named)

    def test_the_three_gitleaks_installs_pin_one_version(self):
        versions = [re.findall(r"(?m)^          GITLEAKS_VERSION: (\S+)$", b) for b in (self.gl_linux, self.gl_mac, self.gl_secrets)]
        for v in versions:
            self.assertEqual(len(v), 1, "each install names one GITLEAKS_VERSION: %r" % versions)
        self.assertEqual(len({v[0] for v in versions}), 1, "the three installs pin different versions: %r" % versions)

    def test_the_macos_install_checks_the_darwin_arm64_asset_against_its_checksum(self):
        sha = re.findall(r"(?m)^          GITLEAKS_SHA256: ([0-9a-f]{64})$", self.gl_mac)
        self.assertEqual(len(sha), 1, "one 64-digit GITLEAKS_SHA256")
        linux_sha = re.findall(r"(?m)^          GITLEAKS_SHA256: ([0-9a-f]{64})$", self.gl_linux)
        self.assertNotEqual(sha, linux_sha, "the darwin asset's checksum is the Linux asset's: each asset has its own")
        self.assertIn("_darwin_arm64.tar.gz", self.gl_mac)
        self.assertRegex(self.gl_mac, r'(?m)^          \[ "\$\(uname -m\)" = arm64 \]$', "the step refuses another architecture")
        self.assertRegex(self.gl_mac, r'(?m)^          echo "\$\{GITLEAKS_SHA256\}  [^"]*" \| shasum -a 256 -c -$', "the checksum is checked")
        self.assertRegex(self.gl_mac, r"(?m)^          set -euo pipefail$")
        t = re.search(r"(?m)^        timeout-minutes: (\d+)$", self.gl_mac)
        self.assertTrue(t and int(t.group(1)) <= 10, "a step timeout bounds the download")

    def test_gitleaks_lands_on_path_after_the_bash_link_and_the_step_checks_it(self):
        names = re.findall(r"(?m)^      - name: (.*)$", self.shell)
        self.assertLess(names.index("Install bash 5.1 or later (macOS)"), names.index("Install gitleaks (macOS)"))
        self.assertLess(names.index("Install gitleaks (macOS)"), names.index("Run bats"))
        self.assertRegex(self.gl_mac, r"(?m)^          sudo install \"\$RUNNER_TEMP/gitleaks\" /usr/local/bin/gitleaks$")
        self.assertRegex(self.gl_mac, r'(?m)^          \[ "\$\(command -v gitleaks\)" = /usr/local/bin/gitleaks \]$')
        self.assertNotIn("GITHUB_PATH", self.gl_mac, "a directory the gitleaks step put on PATH would come ahead of the bash link")
        self.assertEqual(self.shell.count(">> \"$GITHUB_PATH\""), 1, "one PATH entry in the Shell job, the link to /bin/bash")


if __name__ == "__main__":
    unittest.main()
