---
title: The per-session env pick refuses credential-shaped names
status: candidate
where: kernel/credentials.py (is_credential_env_name, credential_env_names, credential_env_refusal); kernel/sdk_backend.py (env_request_error, env_credential_names' delegation, _options' stored-offender line, set_env's refusal line); kernel/kernel.py (_env_error); docs/reference.md (the --env section); tests/test_session_env.py, tests/test_new_route_prefs.py, tests/test_env_credential_names.py
added: 2026-09-18
pr:
tier: fix
offered:
closed:
---
The per-session env pick (romp new --env, POST /new, SdkBackend.spawn and set_env) lands in the session registry and the per-sid sdk-flag-settings/<sid>.json file, and its door (env_request_error, mirrored by the kernel's _env_error) refused only the three login names, so a credential-shaped variable of any other spelling typed into the pick (a NOTES_API_TOKEN, an OP_* name) was written to disk (found by the spawn.json fix's build, 2026-09-18), against the fork's rule that no credential is ever written to a file. Every door now refuses a pick carrying any name the spawn.json writer moves (spawn_env_secret_names over the pick itself: a non-empty value under a name ending _API_KEY or _TOKEN, or one of 1Password's), with one rule and one wording held in credentials.py for both copies of the validator; the message names the variables, never a value, says the pick was not saved and that such a value belongs in the process environment. Nothing is written when refused and the stored env stands; set_env logs its refusal as a problem row. A stored env from before the rule still launches whole and is named once per session in the problem ring, with the redaction road (re-declare the env without the name); the reference documents the refusal and a names-only one-liner that lists stored files carrying such a name. Tests: the door by name and never value, the lockstep table, the backend end to end (the value in no file under the state root), the /new HTTP door, a plain name still landing. The kernel side goes live at the next kernel restart; an offer waits on the user's word.
