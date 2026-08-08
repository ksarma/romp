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
| Fast mode for SDK sessions (the `fastMode` flag-settings opt-in, a chat chip, the timeline star) | PRs #12 (`900a37ce`) + #14 (`26921e7a`, `08d80126`), on fork main | **waiting — RE-CHECK 2026-08-09** | Upstream shipped their OWN fast-mode toggle on 2026-08-07 (`258d9719`, their PR #222) hours after ours, and **it does not work**: they send the literal `/fast on` without ever supplying the flag-settings key, so the CLI refuses every SDK session with "Fast mode is not available in the Agent SDK" — the badge flips optimistically, the chat prints the refusal, the next init flips it back. They published `fastReason` to hide a dead control but `render.ts` never reads it, so the badge shows anyway. The user's call (2026-08-08): they just committed it and will likely fix it fast, so WAIT A DAY before offering anything. Tomorrow: re-read `upstream/main` — if they added the settings key, adopt THEIR implementation (it toggles live in both directions once the key is present, which beats our reconnect) and drop ours; if they have not, offer the fix. Reproduction: an SDK session with no `--settings` reports `init fast_mode_state=off reason=sdk_opt_in_required`. |
| Cost view cannot see fast mode (footnote + price-table comment) | PR #18 (`890be196`) | keep-private | The user does not want to invest here (2026-08-08). The gap is documented, not fixed; the rail's spend figure was never affected. Multiplier is known exactly if it ever matters: the CLI states `$10/$50 per Mtok` against Opus 5's standard `$5/$25`, so 2x — but applying it needs per-turn fast recording that does not exist. |
| The dashboard as an installable home-screen app + Web Push for the bell events (manifest/icons/Apple metas, iOS-standalone safe-area, `/sw.js` + `/push/*` + VAPID on stdlib+`cryptography`, tap-to-open aimed by wid, `setAppBadge` needs-you count) | PRs #9, #15, #20, #21; `plans/ios-app.md` | candidate | All kernel-side code upstream ships too; live-verified end to end on an iPhone 2026-08-08 (install, lock-screen push, tap lands on the firing session, badge). Self-contained: no new hard dependency (`cryptography` is a soft dep behind a loud 500) and no bundle changes. Includes the raw-run test-state hardening (#20) and the SW `skipWaiting` lesson (#21) upstream would otherwise re-learn. |

When offering: work from a branch cut off the upstream default, carrying only that change —
never a fork branch with fork-only commits tangled in. Security items follow `SECURITY.md`'s
advisory process, not a public PR.
