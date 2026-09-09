---
title: Tags-scale test: shim nodes inspect as a projection, so a failing assertion cannot allocate a 100 GB diff; the UI test runner caps the heap
status: candidate
where: ui/timeline-tags-scale.test.ts (hideEdges in makeNode, the header note, one new test); vscode-extension/package.json (the test script passes --max-old-space-size). Their PR #1198 carries the same test file
added: 2026-09-09
pr:
tier: docs
offered:
closed:
---
Root cause: assert/strict equal and deepEqual build a diff on failure even with a message, inspecting both sides at depth 1000 with getters on; the shim node enumerable parentNode and firstChild getter made that dump the whole dialog (2^depth), and node Myers diff then clones an Int32Array of 2(N+M)+1 per edit-distance level, 8N^2 bytes for a 71k-line dump against null, outside the V8 heap. Reproduced under a cgroup cap at 1.2 GB/s. Fix: the shim edges, listener tables and methods are non-enumerable; a node dumps in about 25 lines.
