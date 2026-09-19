---
title: A conftest ratchet fails the test that leaves the kernel's backend singleton changed or over a removed directory
status: candidate
where: tests/test_kernel.py (ViewBuilder saves km._sdk_backend with its sandbox and puts it back), tests/conftest.py, tests/test_sdk_singleton_ratchet.py
added: 2026-09-19
pr: 850
tier: docs
offered:
closed:
---
Upstream's suite has the same lazy singleton (kernel.py's _sdk_locked caches SdkBackend over jd.STATE as it stands at the first km._sdk() call) and the same sandboxing tests, so the same leak can put a later module's backend over a removed directory: an autouse fixture beside _shared_state_restored reads km._sdk_backend before each test and after its teardown and fails the test that left another object, or one whose state_dir is not a directory, with one allowance derived from the transition (None to a backend over jd.STATE, present) for a worker's lazy first build. Tests only: the fixture is tested by nested pytest runs over scratch modules that load the real kernel.
