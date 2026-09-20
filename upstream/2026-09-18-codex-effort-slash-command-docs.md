---
title: The reference says a typed Codex /effort level is checked against the model's catalog
status: approved
where: docs/reference.md, the Model and effort section: one sentence after the typed-command paragraph, cross-referencing docs/codex.md
added: 2026-09-18
pr:
tier: docs
offered:
closed:
---
docs/reference.md said that a typed /effort value the kernel cannot vouch for goes to the CLI verbatim, which upstream PR 1814 made false for Codex sessions: there a one-token /effort X is a setting change checked against the selected model's catalog, and a level the model does not list is refused with the reason, in the chat as a warning and on POST /send as ok false, with nothing delivered to the session. The fork carries the fix now: one sentence after that paragraph stating the Codex rule, that a longer message opening with /effort still goes verbatim, and where docs/codex.md describes the catalog. The offer waits on the user's word; the ledger is the queue.

2026-09-18: approved for offer by the user (batch 4 of the 2026-09-18 plan; his answer covers the fix and docs entries of batches 2 to 7, batch by batch, features excluded).
