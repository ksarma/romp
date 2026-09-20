---
title: A stored login token never rests in spawn.json
status: approved
where: kernel/sdk_backend.py split_spawn_secrets and _spawn_host; bin/romp-session-host docstring; tests/test_session_host.py SpawnSecrets and the HostProcess environment cases
added: 2026-09-16
pr:
tier: fix
offered:
closed:
---
Upstream's stored-login road (T346) composes a login launch with CLAUDE_CODE_OAUTH_TOKEN in the options' env overlay and says, in the compose comment in kernel/sdk_backend.py and in kernel/logins.py's token_value docstring, that the token rides that one process's environment and that no romp file or log line ever holds the value; under per-session hosts (on by default) the same launch copies the overlay into the host's spawn specification and write_spawn_spec writes it to hosts/<sid>/spawn.json (0600 in a 0700 directory), so the token, and the machine's boot-claimed login tokens on a login launch, rested in a file for the host's life. The claim and the file disagree at the pinned tip 14f1548a9 and still do on upstream's tip (2026-09-16): upstream has no split and its _spawn_host hands the host no environment of its own. The fork's stage 1 pull-in (the kernel area's review round 1, item 1, the user's call 2026-09-16: fixed in this PR under the fork's rule that a key lives in the vault and the process environment only, never a file) moves every credential-named variable (AUTH_ENV_NAMES, upstream's own constant) out of the spec before the file is written (split_spawn_secrets) and hands them to bin/romp-session-host through the environment of its Popen (_spawn_host; a systemd-run scope runs the command as systemd-run's own child with that environment, so nothing rides the command line); both host transports build the CLI's environment from the host's own with the spec's overlay on top, so the reader needs no change and the token reaches the CLI as it does for a kernel child. Pinned in tests/test_session_host.py (SpawnSecrets: the names leave the spec and reach the host's environment, a stored-login spawn.json carries no token; HostProcess: a token in the host's environment reaches the CLI and is nowhere the host writes, on both transports). The offer is the helper, the Popen environment and the launcher's docstring on upstream's file; it waits on the no-new-upstreaming hold like the other 2026-09-16 entries, the ledger being the queue.

2026-09-18: approved for offer by the user (the plan's list of offers needing the user's word first).
