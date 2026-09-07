---
title: The dashboard file browser: browse a session's tree (listDir WS op + breadcrumb overlay), open files in the viewer, honest download-only marking, federation for free via the sid-routed splice
status: merged
where: fork PR #67 (+ plan in plans/file-browser.md)
added: 2026-08-14
pr: 67
tier:
offered: their PR #542
closed: 2026-08-22
---
MERGED 2026-08-22: the maintainer rebased our two commits (content-intact, landing as `484f3426`+`0e42b09b`) and added HIS OWN third commit (`614ea7d9`) gating raw-mode saves behind an explicit machine-wide opt-in (the viewer's popup posts a kernel-side setting, broadcast to every attached kernel, and the save route refuses without it) that also tells the owning session — his answer to the write-widening tradeoff the PR body flagged. Branch retired; the fold adopted the gate whole and re-grafted the fork extras (the fileLinkPane relay algebra; the injected-voice roster now covers their edit trace). OFFERED 2026-08-20 (branch `file-browser`, two commits `ac431950`+`35498dbf` off tip `f3ec1297`: browse/open + separately-droppable raw edits): re-derived onto tip’s re-signed (sid,text)→boolean comment sink with a NEW test for the uncovered !landed-while-editing cell; the __rompFeedWasOff pin flipped to browser ownership; droppability proven — full suites green at the commit-1 state alone; review clean, scaffold CI green (since-closed fork #97). Pure feature, no fork-specific content; review-hardened (eight defects found+fixed+pinned before landing). Its gate cleared 2026-08-18: #385 merged upstream, so the viewer surface exists there. Any offer must be RE-DERIVED against the v0.12.0 viewer, not cherry-picked from fork history — upstream evolved the viewer into a pane-agnostic chat modal with a review-comment layer, and the fold (`upfold0819`) reworked the browser's seams to match (the kernel shell relays only `browseFiles` now; feed.css mirrors the modal + comment selectors). Slice 2 (raw-mode edits with mtime conflict refusal) has been live on the fork since PR #67-era work; the offer could carry either slice alone or both.

Status detail (migrated from the table): ✅ **merged** — their PR #542, 2026-08-22 (merge `9aad69f1`); came home in the 2026-08-22 tip fold (`upfold0823`)
