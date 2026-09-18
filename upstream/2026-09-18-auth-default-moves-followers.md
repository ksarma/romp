---
title: Setting the machine default billing moves the sessions that follow it
status: candidate
where: kernel/sdk_backend.py set_auth_default and _reconnect_default_followers, _declared_auth and the spawn seed gated on authExplicit, _connect_landed, the reconnect loop's bounded relaunch; docs/reference.md
added: 2026-09-18
pr:
tier: fix
offered:
closed:
---
set_auth_default wrote sdk-defaults.json and touched no session, while docs/reference.md promised that a session with no pick of its own takes the new side at its next launch; per-session hosts and their CLIs outlive a kernel restart, so that launch never came and every follower stayed on the old side. The write now walks the live sessions and asks every follower whose CLI runs on the other side (the CLI's own report before the composed stamp, which a re-attach stamps untruthfully) to reconnect exactly as a per-session pick asks, with no pick written, so it keeps following the default; the relaunches draw the machine-wide spawn-stagger slot and free it at the handshake; a follower's ask survives a kernel restart and is made again at the attach to the surviving CLI; the spawn seed, the launch, the per-init check and the new-session picker all read the file's auth only beside authExplicit, so one per-session pick no longer rings on every unpicked session or turns picker-created sessions into picked ones. The kernel side goes live at the next kernel restart of the box that serves the sessions. An offer waits on the user's word.
