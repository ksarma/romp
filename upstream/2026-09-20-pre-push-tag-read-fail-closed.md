---
title: The pre-push hook refuses a push when an annotated tag field cannot be read
status: candidate
where: .githooks/pre-push, the annotated-tag arm: a failed tagger, object or message read names the tag and the field and sets failed_scan; tests/pre-push-identity.bats, the shim case
added: 2026-09-20
pr:
tier: fix
offered:
closed:
---
The fail-open window was found by execution on the text upstream landed from the fork's offer 1847: a cat-file -p failure on an otherwise readable tag object (cat-file -t still reporting tag) let a tag whose tagger domain was on the denylist through a real push, with nothing printed and every counter at zero. The fork's fix wires the tag arm into the refuse-on-unscanned road the hook already owns: a failed tagger, object or message read prints one line naming the tag and the field and sets failed_scan, the value still counting as empty so the peel ends, and the message read is captured before its grep so grep's no-match no longer masks the read's failure. The offer waits on the user's decision whether to report it upstream.
