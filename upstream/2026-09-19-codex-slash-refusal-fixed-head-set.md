---
title: A Codex session refuses only the slash commands the kernel knows it cannot take; a message that merely begins with a slash reaches the model as text
status: offered
where: kernel/kernel.py _route_meta_command's Codex arm, _apply_pending_ops's parked command arm, a new _CODEX_REFUSED_HEADS constant; docs/codex.md; tests/test_codex_slash_guard.py
added: 2026-09-19
pr:
tier: fix
offered: their PR #1891
closed:
---
Their PR #1864 (merged 2026-09-19) made a Codex session refuse every slash command it cannot take, and keyed the refusal on _is_slash_command, the shape predicate that decides when a text may fire as a fresh prompt. Shape is not command-ness: a message whose first token is a slash-word or a single-component path (a /tmp report, a /s to skip) is refused with 'This session runs in Codex, which has no /tmp', where the base delivered it to the model as prose. The review of their PR reproduced it on the route, the plain door, the sendMessage arm and the drain of a parked copy, against head and base; peer mail is unaffected because the banner leads. The fix refuses a fixed, checked-in head set at every arm (the commands romp's own surfaces mint and a Codex session cannot take, plus the setter heads with a wrong shape) and lets every other slash-shaped text take the ordinary road, sent idle or parked and drained to the model, with the doc naming the set and saying a skill's name reaches the model as text.

2026-09-19: the fork does not carry their #1864 yet (it arrives with the Monday fold), so the fix is built on the project's current tree as branch codex-slash-refusal-offer (worktree romp-codex-slash-refusal-offer, the offer pipeline, run wf_049e1aa6-012) and the fold carries it: romp-manager ruled at 06:27Z that the fork fixes this regression without anyone's word, since a fold that refuses an ordinary message typed at a Codex session does not ship. Offering the same branch to the project is a separate act and waits for the user's yes through the consolidated out-of-plan ask; the status here stays candidate until then.
