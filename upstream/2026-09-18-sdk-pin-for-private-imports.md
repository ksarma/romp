---
title: The SDK the host imports private internals from is pinned, and a mismatch fails loudly
status: candidate
where: bin/romp-sdk-setup, kernel/session_host.py
added: 2026-09-18
pr:
tier: fix
offered:
closed:
---
kernel/session_host.py drives claude_agent_sdk._internal.transport.subprocess_cli.SubprocessCLITransport and its _process attribute, neither public, with no fallback, while bin/romp-sdk-setup upgraded the package unpinned: a release that moved one would have failed every hosted session launch with the install step none the wiser (the box admin hazard review of the merged pull-in, 2026-09-16). One constant, SDK_TESTED_VERSION in kernel/session_host.py (0.2.156, the version the host tests run against on the box), now declares the version the imports were verified against; the setup script reads that line and installs claude-agent-sdk==<it>, refusing to run with no line to read and refusing a venv that holds another version after the install; the host compares the installed package (importlib.metadata) to the pin before the import, imports directly on a match, and on another version resolves each name inside a try and fails through the host-crashed record with both versions and the repin command when one is gone (the kernel launch error now carries that record, host_transport.host_exit_reason), or runs with one host.log row saying newer or older, filed as a problem row. Tests: two bats cases over a logging pip stub (red on the base, which passed an open upgrade) and tests/test_session_host_sdk_pin.py (the helper with fake modules, a real host over a fake SDK site, the launch error, the filing). The kernel side goes live at the next kernel restart; the setup script side at the next run of bin/romp-sdk-setup. An offer waits on the user word.
