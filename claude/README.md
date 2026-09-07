# claude/ — what romp ships into Claude Code

The Claude-side configuration romp installs for its sessions (symlinked into
place by `install.sh`):

- **`romp-session-prompt.md`** — the extra system-prompt content every
  romp-managed session gets: plain done/not-done reporting the judges can read,
  plus the housekeeping note that pre-explains romp's artifacts (`[romp]`
  notices, `<!-- romp-* -->` comments) as bookkeeping to ignore.
- **`romp-postal.mcp.json`** — registers the postal MCP server
  (`postal/postal_service.py`, via the `romp-postal-service` command on PATH).
- **`skills/romp-postal/`** — the full postal-service guide, loaded on demand
  (sessions get only a compact pointer at start — see
  `hooks/romp-postal-context.sh`).

Skills live in this repo (not `~/.claude/skills/` directly) so a skill and the
tool it documents change in the same commit; the installer creates the
symlinks.

One more skill is installed from outside this directory: `tracked-changes`, the
guide to the file-comment and tracked-change commands, linked from
`vendor/track-changents/skill/` — the pinned copy of track-changents that also
supplies those commands and the guard hook. Fixes to it are patches under
`vendor/track-changents/patches/`, offered back to its author.
