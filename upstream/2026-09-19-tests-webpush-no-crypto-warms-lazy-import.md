---
title: The webpush _no_crypto helper warms the bindings lazy import before hiding the package
status: candidate
where: tests/test_kernel_webpush.py (_no_crypto; SubscribeRoutes.test_a_subscription_minted_inside_the_block_still_reaches_the_route)
added: 2026-09-19
pr: 835
tier: docs
offered:
closed:
---
Completes fork PR 823 (upstream copy has the same helper): 823 moved the two no-crypto tests' key minting before the _no_crypto() block and wrote the rule in the docstring and at both call sites. A rule beside the code does not hold: a later test that mints inside the block reintroduces the order dependence in its hardest form (green in the suite, red alone). The helper now generates and discards one key before it hides anything, which is what resolves the bindings' lazy import of cryptography.hazmat.primitives.asymmetric.ec, so a mint inside the block works; it still nulls sys.modules and resets _PUSH_CRYPTO[0], so the route's own import meets the None and the loud-500 tests stay non-vacuous. The two tests mint inside the block again, and a pin does so on purpose. Tests only.
