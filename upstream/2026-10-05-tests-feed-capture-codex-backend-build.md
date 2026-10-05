---
title: test_feed_session_started and test_skill_load_wrapper build the kernel's Codex backend, and the second its SDK backend too, before _feed opens its stderr capture
status: candidate
where: tests/test_feed_session_started.py (_Feed._feed: km._codex() beside km._sdk(); FeedCaptureHoldsTheBuildAlone._first_call_outside and its _codex test); tests/test_skill_load_wrapper.py (HealOlderStores._feed: km._sdk() and km._codex() before the redirect_stderr; HealOlderStores._first_call_outside and its two tests); upstream/2026-10-05-tests-feed-capture-codex-backend-build.md (this entry)
added: 2026-10-05
pr: 978
tier: docs
offered:
closed:
---
Two test modules wrap build_feed in redirect_stderr and let the first feed build in a process construct the private kernel's session backends inside that capture. build_feed reaches _codex() through _feed_session_key (Sessions.backend_for asks the Codex backend about every session the SDK backend does not own), so the CodexBackend is built inside the capture in both modules, and tests/test_skill_load_wrapper.py's _feed, which builds nothing first, builds the SdkBackend there too, its one-time boot lines landing in err. The Codex construction writes nothing today, but _codex() writes "codex-backend unavailable" and a traceback when loading or constructing the backend raises, and a one-time line the constructor gains would fail the tests asserting an empty capture for whichever of them runs first in its process: the red the 2026-10-03 entry (tests-feed-capture-backend-build) describes for the SDK backend. Each _feed now builds both backends before it opens the capture, and both modules pin it. Tests only, so docs tier.

## Design

Each _feed calls km._sdk() and km._codex() before redirect_stderr, the shape of the 2026-10-03 entry's change. The constructions are the same calls over the same state root and stubs; only where their lines go changes, and every later write, a later _sdk() or _codex() call's included, still reaches err.

The pins: in tests/test_feed_session_started.py, FeedCaptureHoldsTheBuildAlone's _sdk test body moves into a helper, _first_call_outside(name, label), and a second test runs it for _codex. tests/test_skill_load_wrapper.py's HealOlderStores gets the same helper and two tests, over a store holding the ask alone so build_feed writes no line of its own. Each test replaces the function with a stand-in that writes a line per call made on the test's thread, then checks that the first call, _feed's own, writes outside err and that err holds exactly the lines of the calls build_feed makes.

The population: a probe recorded every module-level global of the checkout's modules that changed during each build_feed, with each test of both modules run alone. At the fork's base, the first build in every process of both modules bound _codex_backend from None and imported codex_backend.py with its two helper modules, and in tests/test_skill_load_wrapper.py it also bound _sdk_backend and its wiring. With the change, no first build bound a global from None, imported a module or started a thread. The first build's other changes are caches, and three one-shot reads of feed inputs: the pending-tag journal, whose loader writes only for an unreadable, torn or wrong-shape journal (each quarantined aside); the rewind holds, whose loader never writes; and the parked-handoff fold over the postal log, which writes once per episode when the log exists but cannot be read. The change leaves those three inside the capture, since a feed-input fault notice belongs in err.

## Evidence on the fork

Base: fork main af7d18250. Commits 77e93041b (tests/test_feed_session_started.py), 972c8e1af (tests/test_skill_load_wrapper.py) and 86643d738 (a docstring correction to the first); the figures below were measured on the base with 77e93041b's file, and on 77e93041b's tree with 972c8e1af's file.
- tests/test_feed_session_started.py: the module whole, 24 passed; each of its 24 tests alone, 24 passed; each of its 5 classes under -n 2, passed. With km._codex() dropped, the new test fails alone and in the module whole. With km._codex() dropped and a one-time stderr line planted in CodexBackend.__init__, 8 of the 24 fail alone, among them the 5 tests that assert an empty first capture, each capture holding the planted line. The same plant with the call kept: 24 of 24 pass alone. With km._sdk() dropped, the _sdk test fails alone on its first assertion.
- tests/test_skill_load_wrapper.py: the module whole, 39 passed; each of its 39 tests alone, 39 passed; each of its 7 classes under -n 2, passed. With km._codex() dropped, the _codex test fails alone and in the module whole. With the plant as well, only the two new tests fail alone, since no other check there requires an empty capture. The plant with both calls kept: 39 of 39 pass alone. With km._sdk() dropped, both new tests fail alone.

## upstream/main

upstream/main (f4a572008, last updated 2026-09-24) carries tests/test_skill_load_wrapper.py byte for byte as the fork's base has it, and tests/test_feed_session_started.py as the fork had it before fork PR 963 (the base differs from it only by that PR's 65 added lines), so neither _feed builds anything before its capture. The mechanism is the same there: _feed_session_key calls Sessions.backend_for, backend_for calls _codex() for a session the SDK backend does not own, and CodexBackend's constructor has the same shape: over the tests' empty state root its construction writes nothing. This change sits on top of the 2026-10-03 entry's, so an offer carries both, that one first. Derived from the files with git show; not run on upstream/main.
