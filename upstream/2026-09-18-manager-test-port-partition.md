---
title: The manager node tests take their ports from one disjoint block per file instead of listen-on-zero
status: candidate
where: tests/manager-ports.js (new: the per-file block table, the in-block bind probe, the used set), tests/manager-ports.test.js (its pins), tests/manager-down.test.js (freePorts), tests/manager-stale-consult.test.js (the bare random port), tests/manager-op-env.test.js (the literal pair), tests/README.md
added: 2026-09-18
pr:
tier: docs
offered:
closed:
---
Upstream copy has the same window: manager-down.test.js probes with listen-on-zero and closes the socket before the manager binds, and manager-stale-consult.test.js binds a manager on a bare random port in 20000-39999 with no probe at all, while node --test runs the files concurrently and every file draws from one pool. Here two files were handed one port in one sweep (a fork-only file was one of them; any two upstream files that start a manager have the same window) and a rerun was clean. The helper gives each file a disjoint block below the ephemeral range, probes by binding the candidate itself, never repeats a port in a process, and fails loudly on an unknown file or an exhausted block; the pin checks the table against the files on disk. Tests only.
