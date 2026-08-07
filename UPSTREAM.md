# Upstream candidates

Things on this fork we may want to offer to the upstream romp project. This is a QUEUE for
decisions, not a promise: per `CLAUDE.md`'s fork rule, nothing goes upstream — no PR, no issue, no
advisory — until the user says so, per change. Add a row when you land something upstream-worthy;
the user prunes or promotes.

A good candidate fixes or improves something upstream has too. Fork-specific infrastructure (the
private-strings hooks, fork-remotes guard, this file) never qualifies.

Status meanings: **candidate** (worth offering, decision not yet made) · **waiting** (candidate,
but gated on something first) · **offered** · **landed** · **declined** · **keep-private**.

| What | Where it lives here | Status | Notes |
|---|---|---|---|
| Nine security fixes from the 2026-08 audit (cookie/Origin gate on `/ws`, relay Content-Type, forged postal origin, summarizer `--safe-mode` + private cwd, judge scratch off `/tmp`, serve token out of argv, VS Code exec path, postal marker forgery, judge prompt marks) | PR #1 (`f7761f97`) | waiting | Real vulnerabilities in upstream too. `SECURITY.md` asks for private GitHub Security Advisories — this goes as a DISCLOSURE, not a code PR, and the user explicitly parked it (2026-08-06). Bundle the follow-up hardening from PRs #2–#4 into the same conversation. |
| Uninstaller scratch-path guard hardening (canonicalise before the checks; property tests over the spelling class) | PR #2 (`180e2bea` etc.) | waiting | Upstream's uninstaller has the same hole. Part of the disclosure bundle above — it aims an `rm -rf`. |
| Seventeen mid-test `! grep` bats assertions that asserted nothing, armed | PR #3 (`b35a55a3`) | candidate | Pure test-quality fix, no security angle; could go independently of the disclosure. |
| Judge scratch-refusal blanking card summaries (`""` counted as a model failure) | PR #4 (`a0e95cd7`) | candidate | User-visible bug upstream too, independent of the security work. |
| Timeline drop-downs clip below the short bottom band (flip/clamp, then host-document render) | PRs #7 + #8 | offered | Confirmed live, then offered as romp-on/romp#221 (2026-08-07, the user's call): both halves squashed to one commit on `timeline-menu-clip`, cut off upstream/main. The fork branch backing the PR stays until upstream resolves it. |

When offering: work from a branch cut off the upstream default, carrying only that change —
never a fork branch with fork-only commits tangled in. Security items follow `SECURITY.md`'s
advisory process, not a public PR.
