---
title: Stale-setting toast: fade liveness, the refused value shown, no recency claim, the button's own title
status: offered
where: not built; from the maintainer's review comment on their PR #945 (2026-09-06): `ui/webview/gear.js` (the stale toast's liveness check is `parentNode` only, with the `staleOpen` map; the `staleText` copy and the Apply anyway label; the `rs-stale-toast-act` button inherits the dismiss title); exact-string pins in `ui/webview/setting-stale.test.ts` and `setting-stale-fold.test.ts`
added: 2026-09-07
pr:
tier: fix
offered: their PR #967
closed:
---
Three #945 review follow-ups in one UI fix: a same-gesture refusal arriving between the 11 s fade and the 12 s removal is written into a toast at opacity 0 and never shown (treat `.fade` as not live, or drop the `staleOpen` entry on fade); the copy and the Apply anyway label show only the kept value and call it the later one, a recency claim the kernel cannot make, so show the refused value and drop the claim; the button inherits the toast's click-to-dismiss title. Updates the two exact-string pins.

APPROVED 2026-09-07: the fork owner said offer it (batch 13, tier fix). Build off upstream/main (#945's head `a167c31b` is not on fork main). Fork side, open fork PRs #250 and #252 (file review slices) touch `ui/webview/gear.js`; upstream side, their open #924 and #931 (other contributors) touch it too.

OFFERED 2026-09-07: offered upstream as their PR #967 (2026-09-07, label fix, head 74db19a3); one PR for six entries: `stale-setting-toast-liveness`, `kernel-small-fixes-taskupdate-tick-pn`, `find-orphan-clis-own-pid`, `note-served-model-no-modelusage`, `github-link-ls-remote-askpass`, `manager-scoped-tmux-etimedout-line`.
