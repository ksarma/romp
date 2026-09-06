---
title: `_learned_versions` re-reads every reg on hot paths (the /models read, each pick, the SDK loop)
status: offered
where: maintainer’s no-gate note on their #882 (2026-09-02); not yet built anywhere
added: 2026-09-02
pr:
tier: fix
offered: their PR #949
closed:
---
Cache or memoize the learned-version scan per boot/rev; he called it fine but worth a line — a perf follow-up once the model-alias stack lands.

Status detail (migrated from the table): **offered** — their PR #949 (2026-09-06), label `fix`
