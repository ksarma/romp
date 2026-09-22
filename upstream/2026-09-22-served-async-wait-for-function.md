---
title: The served-page browser tests poll the kernel state from the driver: the pinned Playwright does not poll an async waitForFunction predicate, so the wait returned before the state was written
status: candidate
where: tests/test_task_tracking_switch_browser.py (pollKernelSwitch in DRIVER replaces the two async waitForFunction waits; kernelWait in out.off and out.on; the kernel pins name the poll; test_the_driver_polled_the_kernels_switch_to_each_value_within_its_bound), tests/test_wait_for_function_sync_predicate.py (new: the text pin over every browser-driving file)
added: 2026-09-22
pr:
tier: fix
offered:
closed:
---
A test race hidden by an unpolled predicate. Playwright 1.62.1 (vscode-extension/package-lock.json) evaluates a waitForFunction predicate once and resolves on a truthy result; an async predicate returns a promise, truthy, so the wait resolved on the first call whatever the promise resolved to (measured: `async () => false` under a 3000 ms bound returned in 20 ms with the value false; the sync `() => false` timed out at 3003 ms). The Task tracking switch lab awaited the kernel /version switch that way after both flips, so the reads after the wait were not gated on the kernel (a finding on the project PR 2031; CI reds on fork PR #862 and fork PR #899). The driver now polls the same read in a bounded loop and records the elapsed time and a timeout; a text pin refuses an async predicate handed to waitForFunction anywhere in the browser-driving files, by literal, by a name bound to an async function, or through a wrapper.
