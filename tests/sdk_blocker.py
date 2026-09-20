"""The sitecustomize.py the no-SDK controls hand a spawned host on PYTHONPATH (tests/test_session_host.py and
tests/test_session_host_sdk_pin.py), and the two assertions every such control makes afterwards.

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


def interpreter_imports_sdk() -> bool:
    """Whether a child of sys.executable started with this process's environment, minus ROMP_SDK_SITE and PYTHONPATH,
    imports claude_agent_sdk on its own. Asked of a CHILD because this process's own find_spec is the wrong witness:
    tests/test_host_transport.py puts the machine's SDK venv on THIS process's sys.path, which no child inherits."""
    env = dict(os.environ)
    env.pop("ROMP_SDK_SITE", None)
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
