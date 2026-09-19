---
title: The webpush no-crypto tests mint their subscription keys before hiding the package
status: candidate
where: tests/test_kernel_webpush.py (SubscribeRoutes.test_subscribe_without_crypto_is_a_loud_500, test_a_package_installed_since_is_found_on_the_next_tap_without_a_restart; the _no_crypto docstring)
added: 2026-09-19
pr: 823
tier: docs
offered:
closed:
---
Upstream copy has the same order dependence: both tests call _sub_body() inside the _no_crypto() block, and cryptography's Rust bindings import cryptography.hazmat.primitives.asymmetric.ec lazily on the first key generated in the process, so on a process where no earlier test has minted (either test alone, or an xdist split of the module) the mint meets the hidden None and raises the halt from the test before the route is reached. The tests now mint before entering the block; the route's own import still meets the None and answers the 500. Tests only.
