---
title: The pre-push hook read a commit's tree and added lines but none of its metadata: a clone with no user.email has git stamp <login>@<hostname -f> on every commit (a tailnet FQDN, exactly what a denylist holds), and a message naming a failing path or a box passed too; neither has a forward remedy once out, only a rewrite (2026-09-09: three commits of one slice and a pushed merge carried the address through both scans and gitleaks)
status: candidate
where: branch `filereview-focus` (the focus follow-on's review rounds, 2026-09-09): `.githooks/pre-push` (`chosen_emails`, `stamped_addresses`, `tag_field`, `tag_message`, the address, message and tag checks in `scan_identifiers`, the refusal footer's remedies), `tests/pre-push-identity.bats`, `tests/pre-push-message.bats`
added: 2026-09-09
pr:
tier: fix
offered:
closed:
---
Upstream ships the same hook (their #968 took the added-lines and rev_range shape this plugs into) and now ships tests/pre-push-hook.bats and tests/git-hermetic.bash, so both new bats files port. Two checks per commit no fetched remote holds: the DOMAIN of each stamped author and committer address the clone is not configured to use (user.email in any scope, or GIT_AUTHOR_EMAIL / GIT_COMMITTER_EMAIL / EMAIL in the environment; the login and the names are the author's own and are not read), and the whole message, subject and body, against the denylist; an annotated tag's own tagger and message are read under the same two, since every other read peels a tag to its commit. A refused address says which one-line config settles it (user.email, and user.useConfigOnly so git never fills one in); a refused message or tag names the commit or tag and the line. Precedent: fork PR #222 / their #968, approved as a fix to upstream code.
