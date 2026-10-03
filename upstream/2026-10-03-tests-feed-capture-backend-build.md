---
title: test_feed_session_started builds the kernel's SDK backend before _feed opens its stderr capture, so the tests asserting an empty capture pass alone and under xdist
status: candidate
where: tests/test_feed_session_started.py (_Feed._feed: km._sdk() before the redirect_stderr; FeedCaptureHoldsTheBuildAlone, new); upstream/2026-10-03-tests-feed-capture-backend-build.md (this entry)
added: 2026-10-03
pr:
tier: docs
offered:
closed:
---
tests/test_feed_session_started.py's _feed wraps build_feed in redirect_stderr, and six of the module's assertions require the capture to be empty. build_feed reaches _sdk() through _alive_sessions, and the module's private kernel builds its SdkBackend singleton at the first _sdk() call in a process. That construction writes one-time boot lines to stderr through _backend_log: the SDK import verdict, any credential-shaped environment names, and the cli-scope verdict that conftest's ROMP_CLI_SCOPE=0 forces. The first test of the module to build the feed in a process captured those lines. Run alone, 5 of the module's 21 tests failed this way (four in HealOlderStores, one in HostsCurrentAtTheMint), and under pytest-xdist a worker whose first test from the module was one of the five failed too, every time for a given collection. _feed now calls km._sdk() before it opens the capture, so the capture holds build_feed's own writes and nothing else. Tests only, so docs tier.

## Design

The assertions mean that the feed path writes nothing to stderr. Excluding the cli-scope line by its text would fix only the suite's environment, where the SDK is on sys.path and the credential-shaped names are unset; run plainly alone, the capture held three or four construction lines. Calling km._sdk() first keeps the construction as it was (the same call, state root and stubs) and changes only where its lines go. Every later write still lands in the capture, including any from the _sdk() calls build_feed makes itself.

A new class, FeedCaptureHoldsTheBuildAlone, pins both halves. Each test wraps one real function in a stand-in that writes a line of its own:
- _sdk: the first call writes outside the capture, every call build_feed makes writes inside it, and err equals exactly the inside calls' lines.
- _alive_sessions: its write reaches err, and err holds nothing else.
Calls from other threads go straight to the real function, so a backend thread cannot add a line to a test's record.

## Evidence on the fork

Base: fork main 591436b2e. Fix: commit 621f3f2d6. "The suite's path" means the test selected with -k from a run that also collects tests/test_host_transport.py (which puts the SDK on sys.path), with credential-shaped environment names unset, as the fork's sweep runs it.
- The five tests alone at the base fail 5 of 5 plainly (the capture holds the multi-line construction text) and 5 of 5 on the suite's path (the capture holds the cli-scope line alone). At the fix they pass 5 of 5 both ways.
- Every test of the module alone: at the base, the same five fail and 16 pass, both ways; at the fix, all 23 pass, both ways. The module whole at the fix: 23 passed.
- Under -n 8 over tests/test_host_transport.py, the module and five feed neighbours: 2 failed at the base in each of 2 runs; 302 passed at the fix in each of 5 runs. Under -n 6 over tests/test_host_transport.py and the module: 1 failed at the base in 1 run; 127 passed at the fix in each of 4 runs.
- Mutants of the fix. Removing the km._sdk() call fails the first new test alone, on the suite's path and inside the module, the second new test alone, and the five tests on the suite's path. A sys.stderr.write added to build_feed fails all six empty-capture assertions, each capture holding the mutant's line and no construction line, and both new tests. Returning an empty string for err fails both new tests and the module's assertion on the heal's log line.
- The construction starts one thread, sdk-boot-reconcile. In the five seconds after construction it wrote nothing to stderr, in both environments. A write from it during a later build would land in that build's capture, as it would before this change.

## upstream/main

upstream/main (f4a572008, last updated 2026-09-24) carries the same test file, byte for byte, and the same mechanism: _alive_sessions calls _sdk(), the backend logs through _backend_log, and its conftest sets ROMP_CLI_SCOPE=0. There the five tests fail alone in the same two ways. The fork's diff applies cleanly, and with it the five pass alone both ways, the module passes (23 tests), and -n 8 over the module and five feed neighbours passes in each of 2 runs, against 3 failed without it. At upstream/main, tests/test_host_transport.py under xdist aborts the session with an INTERNALERROR whether or not this change is applied (the controller cannot import claude_agent_sdk to unserialize a worker's warning), so the xdist check there leaves that module out.
