# Latency report

The `api` session cut p95 latency by 40% on the notes endpoint. See the [pull request](https://example.com/notes-api/pull/12 "PR 12") and the [runbook][runbook].

Second heading
--------------

Key points:

[runbook]: https://example.com/notes-api/runbook "Runbook"

- **Cache** the rendered notes for *five* minutes.
- Drop the ~~legacy~~ v1 route.
  - Nested: keep `GET /notes/{id}` unchanged.
  - Nested two with a [shortcut] link and a [collapsed][] one.
- Tabs	mid-line stay literal.

1. First ordered item.

2. Second ordered item, loose.

- [x] Ship the cache
- [ ] Write the migration

> The web session asked for **one** more week.
> Quoted second line.

Escapes: \*not emphasis\* and \# not a heading.

Hard break with spaces  
continues here, and a backslash break\
continues too. Autolink <https://example.com/notes-api> and bare https://example.com/status work.

![Latency chart](figures/p95.png) sits above the summary.

### Summary ###

Done.

[shortcut]: https://example.com/shortcut
[collapsed]: https://example.com/collapsed
