---
title: Codex backend: prune_live takes the kernel call shape; the model picker says why its list is empty
status: candidate
where: kernel/codex_backend.py, kernel/session_backend.py, kernel/kernel.py (/models codex section, the Codex spawn and revive models frame), ui/webview/render.ts, ui/webview/styles.css, docs/codex.md, docs/read-side.md, tests/test_backend_call_parity.py, tests/test_codex_models_route.py, tests/test_codex_backend.py, tests/test_codex_echo_merge.py, ui/webview/codex-meta-choices.test.ts
added: 2026-09-09
pr:
tier: fix
offered:
closed:
---
Upstream drift at the backend birth (6334a2fb): CodexBackend.prune_live took three positional arguments while kernel._merge_live_atoms passes four (human_floor), so every live merge of a Codex session with a queued send raised TypeError (chat build and feed merge failed; timeline bars logged live-merge failed). upstream/main still has the 3-arg def. The Codex model picker also opened blank with no reason: model_catalog answered [] silently (client backoff, a failed model_list, or an empty page cached for the process), /models swallowed it, and the gate flip at the first Codex spawn sent no models frame. Fix: the four-argument prune_live with the record-time text floor, the ABC signature, an AST parity test over every backend, a loud codex.error on /models, the models frame from both doors that open the gate (the spawn and the revive of a dead session), the closed gate naming itself, and the picker row that names the reason, re-reads on open, and says when that read fails. Round 2 also gives the Codex echo atoms the `_echo_text` marker the kernel's echo rules key on (hidden behind the queued bubble, never counted as live work), stamps the echo in whole seconds like the SDK's, and has the backend's own retire take one echo per landed record.
