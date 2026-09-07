---
name: tracked-changes
description: Act as the user's EDITOR — your changes to their files land as accept/reject tracked suggestions (inline diffs + a review panel) instead of applying silently. Works for BOTH an Obsidian vault note AND a code file in VS Code/Cursor — same sidecar, same CLIs. Use when the user asks you to be their editor / proofreader, to edit a file "so I can review/accept the changes", when you receive an "[obsidian] …" or "[obsidian-diff] …" message from a vault/editor (a note, a comment thread, a rewrite or reply request), or when a new session is started to edit a file this way. While acting as editor, FIRST check the tracking flag for EACH file with track-config.mjs: if ON, make every change to that file with the track-edit / track-comment / track-reply CLIs and never the Edit/Write/MultiEdit tools; if OFF, edit normally with Edit/Write.
allowed-tools: Bash, Read, Edit, Write, MultiEdit
---

A PreToolUse guard hook (`track-guard.mjs`, installed alongside these CLIs)
denies raw Write/Edit on tracked files, so forgetting the flag check fails loudly
instead of silently overwriting tracked work — the deny message names the CLI to
use.

# tracked-changes — edit files as reviewable tracked suggestions

You are the user's EDITOR. A flag decides how your changes land: either as TRACKED
SUGGESTIONS the user accepts or rejects in their editor (Obsidian for notes, VS Code
/ Cursor for code), or as normal edits. The flag is PER FILE, not per repo — check
it FIRST, before you touch each file. It is the one control, and you obey it.

## First: is tracking on for THIS file?

Before your first edit to EACH file — every file, every time — run:

```bash
node ~/.claude/hooks/track-config.mjs --file <ABSOLUTE path>
```

It prints `on` or `off`, and **its exit status mirrors that answer: 0 for `on`, 1
for `off`**. A non-zero exit here is the ANSWER, not a failure — read stdout and
proceed; don't retry it, don't report it as a broken command, and don't run it
inside something that aborts on a non-zero status.

The scope it reads is `.trackchanges/config.json`, a flat list of exact file paths
and `folder/` prefixes maintained by the editor's toggle (`engine.isTracked`;
absent file or empty list ⇒ off). So two files in the same repo routinely differ,
and one check covers ONE file — never generalize a `yes` or a `no` to the rest of
the repo or to the rest of your session. Re-check whenever you move to another file,
and re-check a file you've been away from if the user may have flipped its toggle.

- **`on`** → tracked mode for that file: make EVERY change to it through the
  track-changes CLIs below, and NEVER with the Edit / Write / MultiEdit tools. Your
  change is recorded in a sidecar store and the editor renders it as an
  accept/reject diff.
- **`off`** → edit that file normally with the Edit / Write tools; do NOT use
  track-edit or track-comment (the user isn't reviewing suggestions for it).
  One carve-out: if you're pinged to answer a comment thread, you still reply with
  `track-reply` — see "Messages from the editor" below. A reply only adds a
  message to the conversation; it never changes how your edits land.

The CLI-editing rules in the next section apply only to files whose flag is `on`;
the comment-thread reply further down works in EITHER mode.

## When tracking is ON: never touch the file with Edit/Write — use the CLIs

For ANY change to the file, use the CLI, NOT the Edit/Write/MultiEdit tools:

- **Make or replace text** — applies the change AND records it as your tracked
  suggestion (attributed to your session, colored by you):

  ```bash
  node ~/.claude/hooks/track-edit.mjs --file <ABSOLUTE path> \
    --old "<exact, unique text to replace>" --new "<replacement>"
  ```

  `--old` must be an exact, unique substring of the file AS IT STANDS NOW.
  `track-edit` REWRITES the file (it applies old→new, then records the op), so your
  next `--old` must be matched against the post-edit text — re-read the file if
  you're unsure rather than quoting your own earlier `--old`. Make ONE focused
  change per call so each reads as a clean diff, and write NO CriticMarkup or diff
  syntax: the text stays clean of markup and the editor derives the diff from the
  sidecar.

  Revising an earlier suggestion of your own? Running `track-edit` again does NOT
  create a revision step — the op-log has no revision chain, and adjacent
  same-author ops COALESCE, so a second edit over the same span silently rewrites
  the existing suggestion instead of adding a turn the reviewer can see. The only
  thing that produces a visible revision is `--thread <id>`, which folds the edit
  into that thread's conversation. So when you're revising in answer to review,
  pass the `--thread` id you were pinged with.

- **Comment on / highlight a span**:

  ```bash
  node ~/.claude/hooks/track-comment.mjs --file <ABSOLUTE path> \
    --anchor "<an exact span copied from the file>" --note "<your comment>"
  ```

- **Reply into a thread** (when the reviewer replies to one of your changes):

  ```bash
  node ~/.claude/hooks/track-reply.mjs --file <ABSOLUTE path> \
    --thread <id> --note "<your reply>"
  ```

The file text stays CLEAN in the sense that matters to the reader — no CriticMarkup,
no diff syntax, nothing but prose — but it is NOT unmodified: `track-edit` writes
your replacement into the file and records the op alongside it, and the editor
renders that op as an accept/reject diff in its review panel.

**One session at a time per file.** There is no locking and no merge. `track-edit`
reads the file at run time, so `--old` is matched against the file AS IT STANDS, not
against what you read earlier: after another session's write your `--old` may no
longer be found (an error, nothing written), or may still match and land against
text you have not seen. When the file changed under changes pending in the sidecar,
`track-edit` usually DETACHES the displaced changes (they stay in the sidecar,
shown as stale) and applies your edit anyway. It REFUSES ("The note changed since
it was read…", nothing written) only when a displaced change is seconds old, since
the other writer's file write may still be in flight; re-read the file and redo
your edit against its current contents. If you know another session is editing
the same file, coordinate with it rather than interleaving edits.

The CLIs locate the project root by `.obsidian/` / `.git/` / `.trackchanges/`, so
they work in a vault OR a plain code repo; set `TRACKCHANGES_ROOT` only if a file is
outside all of those.

## Messages from the editor (either mode)

Two prefixes reach you from Obsidian / VS Code, and both mean "you are the editor
for the file named here":

- **`[obsidian]`** — the commonest one: the message box in either editor, naming the
  file by ABSOLUTE path (`re: <path>`), optionally quoting a `Context:` block of the
  user's selection, then their message. No thread id, so answer in words in your
  normal reply and make any requested change with the right tool for that file's
  mode.
- **`[obsidian-diff]`** — a review-panel ping about a change or a comment: the file
  by ABSOLUTE path, the reviewer's message, and a THREAD id. One message may list
  several comments on the same file, each with its own thread id; address each one
  and reply into each by its own id. A message may also carry only the reviewer's
  accept and reject decisions on your earlier changes, with no comment and so no
  thread id to reply into: nothing needs an answer, and the file already reads as
  decided.

A thread ping can arrive in EITHER mode — answering a thread is a conversation,
separate from how your edits land. Respond so it lands back in that same thread:

- **answer in words** with `track-reply --thread <id>` — always available, in
  tracked OR normal mode; it just appends your message to that thread.
- **revise the text** if asked: in tracked (`on`) mode use `track-edit --thread
  <id>` (the thread id folds your edit into the conversation as a revision step,
  even when it lands away from the anchor); in normal (`off`) mode just edit the
  file directly with Edit/Write, then optionally `track-reply --thread <id>` to note
  what you changed so the thread keeps a record.

When you have addressed everything in a message, ask me for another look the same
way you asked for this one, naming the file.

## Starting fresh (a new session opened to edit a file)

If you're a new session and the first thing you're handed is a request to edit a
file this way (a message naming an absolute path + what to do), just begin: check
the flag (`track-config.mjs` above), read the file at that absolute path, and make
your first change with the right tool for the mode — `track-edit` when ON, Edit/Write
when OFF. You don't need any handshake; if it's ON the user is already watching the
review panel.

## Notes

- Always identify the file by the ABSOLUTE path you're handed — this session may
  be in a different working directory, so a relative path won't resolve.
- Editor mode = one focused change at a time, so each is a clean, reviewable diff.
