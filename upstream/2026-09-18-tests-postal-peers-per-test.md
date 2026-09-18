---
title: tests: the tunnels module sets ROMP_POSTAL_PEERS per test, never at import (an xdist collection-time leak)
status: candidate
where: tests/test_kernel_tunnels.py (_PeersOff on TunnelConcierge and BootstrapRemoteKernel); tests/test_kernel_remote_identity.py (RemoteIdentity setUp and tearDown); tests/test_hermetic_kernel_postal.py (the placement test and the import probe); tests/README.md
added: 2026-09-18
pr:
tier: docs
offered:
closed:
---
Upstream's tests/test_kernel_tunnels.py writes ROMP_POSTAL_PEERS=0 at module level (line 35 at 25e748130), and the kernel's _postal_peers_on reads the variable at call time. Under pytest-xdist every worker imports every collected module before it runs a test, so the value reaches every module on every worker whether or not that worker runs a tunnel test: tests/test_kernel_remote_identity.py's absorb case, whose bus notice is gated on peers, was red in 5 of 6 full runs on the fork (2026-09-18), and tests/test_postal_via_dedupe.py's relay case had gone red the same way (2026-09-16). The fix moves the value into a per-test setUp and tearDown for the two classes that attach or detach (the 0 stays: with peers on, a detach's refused bus notice revives the bus from inside the test process), pins the default in RemoteIdentity's setUp with the module-alone red as its fails-before, and re-aims the hermetic pin: the port stays before the load (the kernel reads it at import), client-only before the load or in setUp, peers in setUp and restored in tearDown and never at module level, read by ast position and by an executed import probe. Reproductions, all red before and green after: the identity module alone with ROMP_POSTAL_PEERS=0 in the environment; the tunnels module collected before it in one worker; -n 2 with the tunnels module collected but deselected. Tests and docs only.
