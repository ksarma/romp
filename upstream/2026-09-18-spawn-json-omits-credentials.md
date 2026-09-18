---
title: spawn.json omits the env overlay's _API_KEY, _TOKEN, 1Password and login names
status: candidate
where: kernel/sdk_backend.py (spawn_env_secret_names, split_spawn_secrets, the host spawn road log line); kernel/host_transport.py (write_spawn_spec docstring); docs/reference.md (the spawn.json sentence); tests/test_session_host.py (SpawnSecrets and the HostProcess environment case); bin/romp-session-host (the launcher docstring); tests/test_env_credential_names.py (the case fold)
added: 2026-09-18
pr:
tier: fix
offered:
closed:
---
The kernel writes each hosted session's launch spec to hosts/<sid>/spawn.json, env overlay included, and the pull-in's writer moved only the three login names (AUTH_ENV_NAMES) out of it to the host's process environment; a credential-shaped variable of any other name a compose put in options.env reached the file (the box admin's hazard review of the pull-in, 2026-09-16), against the fork's rule that no credential is ever written to a file. split_spawn_secrets now moves every name env_credential_names flags over the overlay itself (a non-empty value under a name ending _API_KEY or _TOKEN, or one of 1Password's names) beside the three, through a helper (spawn_env_secret_names) next to the rule the boot notice already used, so the file and the notice agree on what a credential looks like. The moved names take the login token's road, the host's environment, with the overlay's precedence kept, so the session launches with them and only the file is clean; the spawn logs the names moved beyond the three, never a value. Tests: the unit split, the real _host_transport_for spawn road over a stub kernel (the value is in no file under hosts/), and a real host whose CLI probe sees the moved name. The kernel side goes live at the next kernel restart; an offer waits on the user's word.
