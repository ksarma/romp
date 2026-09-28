"""The sitecustomize.py the no-SDK controls hand a spawned host on PYTHONPATH (tests/test_session_host.py and
tests/test_session_host_sdk_pin.py), the probe that asks a child interpreter whether it imports the SDK (two questions,
interpreter_imports_sdk's docstring tells them apart), and the two assertions every such control makes afterwards.

The blocker hides an installed claude_agent_sdk from the child: sys.modules[name] = None makes the import raise
ModuleNotFoundError and importlib.util.find_spec answer None, so bin/romp-session-host's launcher falls through to
ROMP_SDK_SITE and the host runs its built-in pipe transport. It ALSO witnesses its own run: before hiding anything it
asks importlib.machinery.PathFinder.find_spec, which reads sys.path (complete at site time; the PYTHONPATH entry that
carries this file precedes the stdlib and every site-packages on every interpreter the suite runs under) and bypasses
sys.modules, whether the interpreter had an SDK to hide, and writes the answer to the file named by
ROMP_TEST_BLOCKER_WITNESS. Without the witness a control passed identically whether the blocker took effect or the
interpreter simply had no SDK, the pipe transport being its only road, so a blocker that never loaded (its directory
off PYTHONPATH) read green on every venv without the SDK, and a CI cell whose pytest interpreter lost the installed
SDK read green everywhere: the gated tests skipped, both controls passed, nothing was red (2026-09-20). The first
process in the environment to reach site writes the file, which is the host; the fake CLI it spawns inherits the same
PYTHONPATH and finds the file present, so the witness is the host's.

No romp code is loaded here, so this module needs no state preamble."""
import os
import subprocess
import sys

WITNESS_ENV = "ROMP_TEST_BLOCKER_WITNESS"
SITECUSTOMIZE = (
    "import importlib.machinery, os, sys\n"
    "on_path = importlib.machinery.PathFinder.find_spec('claude_agent_sdk') is not None\n"
    "sys.modules['claude_agent_sdk'] = None\n"
    "w = os.environ.get(%r)\n"
    "if w and not os.path.exists(w):\n"
    "    with open(w, 'w') as f:\n"
    "        f.write('sdk_on_path=%%s' %% on_path)\n" % WITNESS_ENV)


def interpreter_imports_sdk(env=None, *, strip_pythonpath: bool = True) -> bool:
    """Whether a child of sys.executable started with `env` (this process's environment when None), minus ROMP_SDK_SITE,
    imports claude_agent_sdk. One probe, two questions, told apart by `strip_pythonpath`:

    - True, the default, the WITNESS question: what the interpreter has ON ITS OWN, PYTHONPATH dropped too. The no-SDK
      controls (tests/test_session_host.py and tests/test_session_host_sdk_pin.py) ask this to check the blocker's
      witness, because each REPLACES its host's PYTHONPATH with the blocker's site: that host took no SDK from the
      parent's PYTHONPATH, so what the blocker hid has to agree with the interpreter alone.
    - False, the GATE question: what a host spawned with `env` as given imports, PYTHONPATH kept. tests/test_session_host.py's
      _host_imports_sdk asks this of the environment HostProcess._start hands a host, which inherits the parent's
      PYTHONPATH. Asking the witness question there (review round 3 found it, 2026-09-20) gated "no SDK" for a host whose
      SDK was reachable through PYTHONPATH alone, so where the run required the SDK that module's switch case failed and
      its two SDK-transport cases skipped, both wrongly; and it would gate "SDK" for a host the parent's PYTHONPATH hides
      it from.

    Asked of a CHILD because this process's own find_spec is the wrong witness for either question:
    tests/test_host_transport.py puts the machine's SDK venv on THIS process's sys.path, which no child inherits."""
    env = dict(os.environ if env is None else env)
    env.pop("ROMP_SDK_SITE", None)
    if strip_pythonpath:
        env.pop("PYTHONPATH", None)
    probe = subprocess.run([sys.executable, "-c",
                            "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('claude_agent_sdk') else 1)"],
                           env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
    return probe.returncode == 0


def assert_witnessed(case, witness: str, interpreter_has_sdk: bool):
    """After the blocked host ran: the blocker ran in the child (the witness exists), and it hid exactly what the
    interpreter has (the witness agrees with a probe of sys.executable without the blocker)."""
    case.assertTrue(os.path.exists(witness),
                    "the blocker never ran in the host child: the control is on the pipe transport for another reason")
    with open(witness) as f:
        case.assertEqual(f.read(), "sdk_on_path=%s" % interpreter_has_sdk,
                         "the blocker hid something other than what the host's interpreter has")
