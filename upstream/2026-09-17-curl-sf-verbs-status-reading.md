---
title: bin/romp's non-session verbs read a kernel refusal through curl -sf, so a 4xx with a reason answers kernel not reachable
status: candidate
where: bin/romp: the curl -sf call sites of the non-session verbs (rename 999, color 1105, emoji 1216, watch 1281, 1291 and 1314, card 1381, logins 1411, 1449 and 1463, watch-pr 1523, and the same pattern at sessions 315, fork 973 and move 1032; lines at the 2026-09-17 catch-up fold's merge 2def2572f) and _romp_post (1962), the helper the session verbs already use
added: 2026-09-17
pr:
tier: fix
offered:
closed:
---
The fork's rule from the 2026-09-15 pull-in (ruling 19 b): a kernel refusal is quoted with the kernel's reason. The session verbs send, interrupt and end go through _romp_post, which reads the status off the -w trailer and quotes a non-2xx with the kernel's reason. The just-landed romp card (romp-on/romp pull 1757, POST /notice) and the fork's own non-session verbs use curl -sf the same way, and -f folds every non-2xx into the exit a dead kernel gets and throws the body away: a pre-fold kernel's 404 on POST /notice (a route it does not serve) reads kernel not reachable, and so does a 400 on a body a route rejects or a 403 on a token the kernel refuses; the refusals these routes answer with 200 and ok false (an unknown session name, say) are quoted already. The tidy: one status-reading helper for the non-session verbs, or _romp_post widened to GET, with the bats fakes' refusal cases pinning each verb's quoted reason. No test pins the current wording on either side (bin/romp 1381-1390 at the fold's merge). Filed by the 2026-09-17 catch-up fold (rulings 16 and 27 of that fold); the offer waits on the no-new-upstreaming hold like the 2026-09-16 entries, the ledger being the queue.
