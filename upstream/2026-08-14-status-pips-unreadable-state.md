---
title: Dashboard status pips: an UNREADABLE session state renders as nothing, same as a healthy idle one
status: landed
where: `pips` branch PR
added: 2026-08-14
pr:
tier:
offered: their PR #336
closed: 2026-08-14
---
Upstream ships the same seam: `feed.ts`'s `dotFor` falls to `""` for any session not in the payload's `working`/`awaiting` name lists, so a session whose state the kernel knows (e.g. a latest `waiting` record in states/) draws NO pip — indistinguishable from a rendering hole or an unreadable state — and the fleet pane's dot is working-only (it doesn't even show the straw awaiting dot the feed shows for the same session). Fix: build_feed emits the other two quarters of a TOTAL partition (`ready` = alive and quiet, `stateUnknown` = listed but live state unreadable); feed + fleet render all four explicitly (hollow steel ready ring, gray unknown ring, self-explaining tooltips), with a bare name reserved for payloads that predate the lists — so an old REMOTE kernel in a federated merge keeps the legacy look instead of reading falsely as "unknown". Pure fix, no fork-specific content; tests use the synthetic `web`/`api`/`tests` demo world. REWORKED 2026-08-14 to the maintainer's design call: drop the "ready" ring (a blank keeps meaning "alive and quiet"), keep only the gray unreadable-state ring; rebuilt as a single commit off current `main`. The FORK was converged onto the same 3-state design (fork PR #54, merged) before the offer landed; post-merge the two copies were verified code-identical (residual deltas are comment wording and the fork's OPENING-state strip ladder, both deliberate). Offer branch cleaned up.

Status detail (migrated from the table): **landed — merged upstream as their #336 (2026-08-14)**
