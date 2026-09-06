# Comments and tracked changes in the file viewer

**Status: BUILDING** (approved by the user on 2026-09-06 after reviews on 2026-09-05 and 2026-09-06 and
a structured design interview; every question ruled). A dedicated romp session is building all
six slices in one push, one fork PR per slice with an adversarial review pass, in the order under
Build slices; the ADR is accepted with Slice 1, and one user todo at the end asks for the
end-to-end walk. File and line references describe this fork at its 2026-09-05 merge base and the
track-changents repo as of the same day; as with every plans/ document, treat them as dated.

## Summary

romp's file viewer can show any file and, since the file browser landed, edit it. It cannot hold
a comment on one. The person who directs the sessions reads their output as files, and today a
comment on a file leaves romp: it goes into GitHub, into a chat message that quotes the passage
and then scrolls away, or into the file itself as plain text the agent has to find. Nothing
records which passage was meant, whether it was answered, or what the session changed in
response, and seeing a session's edits to a file means reading a diff somewhere else.

This plan gives the viewer **file comments** and **tracked changes**: a comment on a passage, on a
region of an image or a PDF page, or on a file as a whole, kept beside the file with its replies;
a session's edits to a tracked file shown in place as changes the person accepts or rejects; and
one **Send to session** that hands everything unsent to the session that owns the file. It is
built on track-changents, a clean-file track-changes core written by a collaborator (MIT), whose
sidecar format, agent CLIs, guard hook, and skill are vendored into this repo unchanged, so the
agent side works on the first day and the two other editors that read the format keep working.
Six slices, each useful alone, built together.

The motivating story is the morning review of an overnight report, told in the next section, but
nothing here is specific to reports or to reviews: a session can file a user todo naming any file
it wants the person to look at, and the person can comment on any file for any reason.

The user ruled on every question this document and its reviews raised; the rulings are recorded
under Decisions. The plan keeps its original file name, `file-review.md`,
since the todo and README already point at it; every name inside follows the new vocabulary. A committed **comments log** beside each file's comments, added at the user's
request, gives git a durable record of what was said, sent, and decided.

Terminology, as pinned in `CONTEXT.md`: a **file comment** is the object (never "thread", which in
romp is a forked side session anchored to the chat); a **change** is a session's edit awaiting
accept or reject (never "suggestion", the storage format's word); a **tracked file** is one whose
session edits are recorded as changes; a **direct edit** is the person's own edit from the
dashboard. This document says **sidecar** for the JSON file that holds a file's comments and
changes, **comments log** for the append-only record beside it, **`store-io`** for the module that
reads and writes them, **host script** for the node program the kernel runs, and **owning kernel**
for the machine that holds the file. "Host" alone means an editor host (the Obsidian plugin, the
VS Code extension, or this viewer).

## The motivating loop, and the bar

Paraphrased from the user's description (the user 2026-09-05):

1. The user gives a session instructions and answers its questions.
2. The user tells it to work overnight and report in the morning.
3. Overnight the session writes or revises a report and files a user todo asking for a look,
   naming the file's path in the todo's detail.
4. In the morning the user opens the file from the todo.
5. The user sees the session's pending changes: every edit not yet accepted or rejected.
6. The user comments on passages, on figures, and on PDFs, or edits the text directly. The
   comments persist with the files.
7. The user sends everything to the session in one gesture, which also answers the todo.
8. The session addresses the comments: it replies into them and revises the text.
9. The user sees the revisions in the same viewer as changes and accepts or rejects them, singly
   or all at once.

Two facts about the storage format shape this loop. First, **tracking must be on for a file
before a session writes it** for step 5 to show anything: the guard passes untracked files
through, so an untracked file is written raw and no changes exist to show. The design therefore
lets the user track a folder before its files exist and makes Send to session turn tracking on
when it is off. Second, **the sidecar keeps no history**: accepting a change drops it and
rejecting one reverts it, so "what changed since I last looked" can only mean "what is still
pending". A round is closed by resolving its changes; what stays pending is what the next look
shows, mixed with newer edits. The comments log is what remembers the rest.

**The bar.** Steps 4 through 9 complete inside romp's Files pane, on the disk the session works
on, with no GitHub tab and no Obsidian window, and every comment, reply, and change lands in the
same `.trackchanges/` files the track-changents CLIs, guard, and skill already read and write,
unchanged. GitHub remains a read-only pointer through the viewer's existing GitHub link.

**A durable record.** The user asked that the comments leave a record in git (the user
2026-09-05). Comments already persist in the sidecar, but the sidecar forgets accepted and
rejected changes and deletes itself when a file has nothing pending. The comments log beside it
records every send, every accept or reject, every tracking toggle, and every direct edit; see The
comments log under Kernel. Whether either file is committed is the session's or the user's call
per repository (the user 2026-09-06); romp writes the files and does no git operation.

## What the dashboard already does for this loop

Verified against this fork on 2026-09-05.

- **Steps 1 and 2** need nothing: the chat composer's `sendMessage` op (`kernel/kernel.py:11954`)
  and POST `/send` (`kernel.py:37689`) carry human-to-agent text on every backend, through
  `_send_or_park` (`kernel.py:22180`), which revives a dormant SDK session.
- **Step 3** works when the gear's User todos switch is on. The postal `add_user_todo` tool files
  the todo (`postal/postal_service.py:2984-2989`, POST `/usertodo`, `_add_user_todo` at
  `kernel.py:3584-3603`), and its description promises that a file path in `detail` becomes an
  openable link. The switch is per install and default OFF (`kernel.py:4855-4884`).
- **Step 4** half works. The chat's todo card and its Reply modal linkify the detail path through
  `linkifyFileUris` and `openPath` (`ui/webview/render.ts:3041-3046, 1411, 966`), and `openPath`
  lands in the Files pane when it is open. The cross-session Waiting-on-you pane, the surface a
  morning reader looks at, renders the detail as plain text in the row and in its Reply modal
  (`ui/webview/waiting.ts:209, 126-127`). The pane is its own iframe with none of the chat's
  routing state, and `render.ts` exports nothing, so the linkifier cannot simply be imported.
- **Step 5** has no surface. The viewer renders the current bytes of one file (`renderBody`,
  `ui/webview/file-view.ts:554-563`) over GET `/file`, which stamps `X-Romp-Mtime-Ns`
  (`kernel.py:36819-36883`). Nothing in romp reads a `.trackchanges/` sidecar.
- **Step 6** is ephemeral. Selecting a passage mints a `path:line` quote chip
  (`file-view.ts:565-626`, `ui/webview/docreview.ts:28-60`); Cmd-Enter stages several; Enter
  sends them as one message. The viewer's own per-file comment store was retired on 2026-08-23 in
  favor of chips (`file-view.ts:248-262`).
- **Step 7** half works. Reply on the todo posts `userTodoAnswer`, whose handler checks the
  switch, the todo's openness, and the session's liveness, sends through `_send_or_park`, and
  stamps the todo answered itself on an immediate send or lets a parked send stamp when it drains
  (`kernel.py:12198-12250, 22392`). Nothing ties staged notes to it.
- **Step 8** works once the agent-side tooling is linked on the session's machine, which romp's
  installer will do from the vendored copy. romp's SDK backend leaves the SDK's
  `setting_sources` unset, and the SDK in romp's own environment (0.2.132, `ClaudeAgentOptions.setting_sources`,
  `types.py:1990`) documents that as loading all sources, matching the CLI's defaults, so the user-level guard hook
  and the skill apply; Slice 1 confirms this on a live session. `ROMP_SESSION_NAME` and `ROMP_SID`
  become the author label and stable id (`kernel/sdk_backend.py:7169-7176`; the tmux launch line
  in `bin/romp`), and both names are reserved against per-session env overrides. Because agent
  and dashboard share the owning kernel's disk, a pull from GitHub is already unnecessary.
- **Step 9** has no surface.
- Two substrates matter for the design. Editing: Edit mounts a lazily loaded CodeMirror 6 chunk
  (`ui/webview/editor-chunk.ts`) and Save rides `saveFile` to `_save_file`
  (`kernel.py:30673-30749`): a server-side consent gate (`_file_editing_on`,
  `kernel.py:4752-4764`), existing UTF-8 text files only, a 2 MB cap (`_TEXT_MAX_BYTES`,
  `kernel.py:30554`), a nanosecond mtime fence, and an atomic replace, followed by an edit trace
  telling the session whose cwd contains the file that a human edited it
  (`kernel.py:30815-30827`). Dispatch: POST `/fork-comment` and `/fork-promote`
  (`kernel.py:10981-11052, 37743-37755`) were built on 2026-08-31 for exactly this tooling's
  comments and have no caller yet.

### Why this is not the retired comment layer

The viewer's 2026-08-23 consolidation removed a browser-local comment store because batching
notes for one hand-off is what quote chips already do. This proposal does not bring that store
back. The sidecar is a file on disk beside the commented file, attributed per author, read and
written by the agent's own tools and by two other editors, and it carries the session's changes
as well as the person's comments. The chips stay for one-off notes; file comments are for
anything worth keeping with the file.

## Shape of the feature

A **comments panel on the file viewer**, opened from the viewer's action row, beside the viewer
body in the Files pane column and folding below it when the column is narrower than the
two-column minimum. Five structural choices, each with a precedent in this repo:

1. **The sidecar is track-changents v3, byte for byte, plus one optional field for regions.**
   romp mints no second schema. That is what lets the agent half (CLIs, guard, skill) and the
   other two hosts work unchanged, and it is what keeps the romp side small. The one addition, an
   optional `target` on a file comment for image and PDF regions, follows the format's own rule
   for additive fields (see The contract). A second romp-only file, the comments log, sits beside
   the sidecar in the same directory and is outside the contract; the other hosts' directory scans
   match only `.json` names and ignore it.
2. **The kernel does the disk work, on the owning kernel, by running a small node host script
   built on track-changents' own `store-io` and engine.** The browser renders JSON and never
   holds a sidecar it writes back. This is the `listDir`/`saveFile` shape: a sid-routed WebSocket
   op, so a remote session's file works with no new relay code (`ui/webview/federation.ts:53,
   278-288`).
3. **The UI enters through the viewer's action registry** (`registerFileViewAction`,
   `file-view.ts:181-192`, the GitHub link's seam): mounted hidden, revealed when the kernel
   answers.
4. **Change awareness by polling, not a watcher.** HEAD `/file` on the file, on the sidecar, and
   on `config.json` (an agent's `track-config` can flip the toggle) every 2.5 s while the panel
   is open, comparing `X-Romp-Mtime-Ns` as strings. `CLAUDE.md`
   prefers the event to the timer; the person's own writes need no poll, since every verb answers
   with fresh state, and agent writes have no event source without a filesystem watcher, which
   the file-browser plan deferred. The poll stands in for that missing event and is close to the
   Obsidian host's 2 s sidecar poll.
5. **Any file, anywhere the viewer can show it.** Comments are not tied to a project type or a
   review: every text format gets passage comments, every file gets a whole-file comment, images
   and PDFs get regions, and a file with no repository or vault above it gets a `.trackchanges/` folder created beside it
   on the first comment, which then serves as its project's root (decision 37).

## The contract: the track-changents sidecar

One JSON file per commented or tracked file at
`<root>/.trackchanges/<encodeURIComponent(relpath)>.json` (track-changents `README.md`, "The
sidecar store"): `v: 3`, `id`, `path`, `suggestions[]` as insert/delete/replace records (the README's ops) in current-text
coordinates, each with `author`, optional `authorId`, `ts`, and an `anchor {prefix, quote,
suffix}` (these are the changes); `comments[]` as file comments with `id`, `author`, `body`,
`ts`, `replies[]`, `resolved`, an optional `anchor {quote, prefix, suffix}` for a passage comment,
and an optional `suggestionId` binding the comment to a change; a top-level `detached[]` of ops
the load-time rebase could not re-place, which a host preserves and shows rather than drops; and
a `fingerprint` over the current text. A file comment is a change comment when `suggestionId` is
set (the README calls it the cross-editor key, and the Obsidian host classifies on it); a passage
comment keeps its anchor and gains a `suggestionId` when the agent answers it with `track-edit
--thread`, and is then shown on the change's card. The VS Code host classifies on the absent
anchor instead (`vscode/src/panel.ts:206`), so it shows such a comment as a passage comment; a
comment written by the CLIs has exactly one of the two fields until then. The file on disk is
always the current text with every change applied. The root is the nearest `.obsidian/`, `.git/`, or `.trackchanges/` ancestor; nothing reads git,
the folder is only a landmark for where the one `.trackchanges/` directory of a project lives.
One `.trackchanges/` per project, at its root, never one per directory (decision 38): the tracked
list, the comments of every file in the project, and the commit-or-ignore choice have one home,
and a file moved within the project keeps its comments. The single on/off control is
`.trackchanges/config.json` `{v: 2, tracked: [...]}`: a path tracks one file, a `folder/` entry
tracks everything under it, and an optional `untracked: [...]` veto with the same shapes wins over
both the list and the link-closure inheritance (`store-io.mjs:87-98, 190-192`).

Four properties of the contract shape the design:

- **A file comment with neither anchor nor `suggestionId` is valid and means a comment on the
  file as a whole.** The schema marks `anchor` optional (README, thread shape), `store-io` passes
  such a comment through untouched, `track-reply` replies into it, the engine's comment pruning
  keeps it (`engine.js:827-833`), and both existing hosts render it as a plain discussion card
  (VS Code at the top of the panel, Obsidian at the bottom). The Obsidian host already writes
  this shape for a message with no selection. Only `track-comment` cannot create it, since it
  requires `--anchor`; the host script builds the comment itself. Every file gets this comment in
  Slice 1 (the user 2026-09-06); for images and PDFs it is the only comment until regions land.
- **One optional field, `target`, carries a region.** `target: {kind: "image"|"pdf", region: {x,
  y, w, h}, page?, hash, src?}` with the rectangle in fractions of the rendered page or image,
  `page` 1-based for PDFs, `hash` the sha256 of the figure's bytes so a regenerated figure marks
  its region comments stale the way a moved text anchor does, and `src` only on a figure embedded
  in a markdown file: the embed's destination as written (the Slice 3 build, 2026-09-06; this plan
  first stated the shape without it). The comment names its figure because the anchor's quote does
  not always carry the destination (a reference-style embed's sits in a `[ref]: dest` definition
  elsewhere in the file) and a passage can embed two figures; the reply's per-figure hashes and
  the panel's re-place are keyed by that spelling. The host script, never the client, computes
  `hash` from the bytes of the file the target is about: the commented file itself for a
  standalone image or PDF, the file `src` names for an embedded figure, resolved and bounded as
  Security posture states. A target on an anchored comment that names no `src` stays valid and is
  read; it is the shape this plan first described, and one a writer with the contract alone can
  leave. The host tells its figure from the anchored passage when that passage embeds exactly one
  distinct figure (one figure embedded twice still tells), says per comment where it could not,
  and never writes the sidecar on a read. The text anchor
  stays absent for a standalone image or PDF, so the other hosts show the comment as a discussion
  card and preserve the field (both write the whole object back). For a figure embedded in a
  markdown file, the comment carries both the anchor on the embed's source line, which every host
  can place, and the region, which this viewer paints on the rendered image. The README's version
  rule says to bump `v` only for a breaking change; an optional field older readers ignore is not
  one. The field is built romp-only for now (the user 2026-09-05); documenting it in the
  track-changents README, in the five-key shape above, is a later offer to its author, not a
  dependency.
- **A file created through `track-edit` is one insertion** spanning the whole file, and while any
  same-author insertion is pending, that author's further edits inside or beside it coalesce
  into it (`engine.js:204-218`) and do not appear as separate changes. A first look at a file the
  session created under a tracked folder therefore begins with one card covering everything;
  accepting it is how the session's later revisions become separate changes.
- **A corrupt or newer-version sidecar must be refused, never replaced.** Two CLIs today replace
  it, `track-edit` and `track-comment` (item A2 of the 2026-09-03 track-changents survey, a
  session note outside both repos; every item relied on is restated here); `track-reply` fails
  instead, unless a `.superseded` park holds the comment, in which case it revives over the
  corrupt file. The host script loads through `loadStoreStatus` (`store-io.mjs:286`), never
  through `loadStore` or `ensureStore`: `loadStore` returns null for corrupt, unsupported, and
  absent alike (`store-io.mjs:302-304`), and `ensureStore` and `track-comment` then mint a fresh
  sidecar over that null (`store-io.mjs:413-418`, `cli/track-comment.mjs:76-79`). The host script
  also never calls `reviveThreadFromSuperseded` (survey A1: replying into a comment that survives
  only in a park overwrites the live sidecar with an empty change list); a `reply` or `resolve`
  whose `commentId` is not in the live sidecar refuses `no-comment`.

Binary files: the CLIs read every file as UTF-8 text. `track-comment` and `track-reply` operate
on an image or PDF and write a valid, deterministic sidecar without touching the file, but
`track-edit` rewrites the file from the lossy decode and destroys it. The guard would steer an
agent toward `track-edit` on a tracked image. A non-text refusal in the vendored guard and
`track-edit` lands in Slice 1, before folder tracking ships.

Human authorship uses the label `you` with no `authorId`, matching the VS Code host's default
(decision 6).

## Kernel: two ops and a host script

Both ops echo a client-minted `reqId`, route to the owning kernel by `sid`, and answer on the
sending socket, the `listDir`/`saveFile` pattern (`kernel.py:39531-39558`). All mtimes travel as
strings.

**`fileComments`**, the disk op:

```
request  {type:"fileComments", reqId, sid, path, verb, args?,
          fence?: {storeMtimeNs: str|"", fileMtimeNs?: str, configMtimeNs?: str|"",
                   figureHash?: str}}
reply    {type:"fileCommentsResult", reqId, verb, root, storePath, trackedBy, agentTooling,
          fileMtimeNs, storeMtimeNs|null, configMtimeNs|null, store|null, hunks, unsent,
          fileHash?, fileHashReason?, embeddedHashes?, embeddedHashReasons?, derivedSrcs?,
          derivedSrcReasons?, baseline?}
refusal  {type:"fileCommentsFailed", reqId, verb, code, error}
```

`store` is the sidecar as loaded and normalized (with `detached[]`), or null when absent.
`hunks` is `engine.toHunks(store.suggestions)`: one row per change with `id, author, ts, kind,
curFrom, curTo, baseFrom, baseTo, oldText, newText, anchor`, sorted by offset. `unsent` is the
derivation from the comments log described below: `{comments: [id], replies: [{commentId, ts}],
accepted, rejected, watermark}`, where replies are identified by their comment and `ts` since the
v3 shape gives them no id, and `watermark` is the last send's (null when none). `baseline`, the clean text with every
change rejected (`engine.baselineOf`), is the whole file and is returned only when the request
asks for it. `trackedBy` is `{kind: "file"|"folder"|"inherited", entry}` or null, so the panel
can say which `config.json` entry covers the file. `agentTooling` is `"present"` or `"absent"`
for the agent-side CLIs on the owning kernel; when absent the panel works but warns that the
session cannot reply until romp's `install.sh` has run on that machine. `configMtimeNs` is null
when `config.json` does not exist; the client sends `""` for null, the same convention as
`storeMtimeNs`. The browser builds its cards from `store` and `hunks`; no card model crosses the
wire. The hash fields are Slice 3's: what a region comment's `target.hash` is compared with on
every reply. On an image or PDF that is `fileHash`, the file's bytes now; on a text file it is
`embeddedHashes`, one per distinct `src` its region comments name, and `store` carries the `src`
each src-less anchored target names by its passage (`derivedSrcs` lists which, per comment id).
Null is unknown, never stale, and each null has its reason beside it (`fileHashReason`,
`embeddedHashReasons`, `derivedSrcReasons`), since the kernel keeps the host's stderr only when a
call fails.

Verbs by slice. Slice 1: `status`; `set-tracked {on, scope: "file"|"folder"}`, where `folder`
writes `<dir>/` (refusing the root) so a folder can be tracked before its files exist, and `off`
removes the covering entry when its kind is `file` or `folder` (a folder asks a pane-local confirm
naming it) and refuses `tracked-inherited` when the file is covered only through link
inheritance, naming the parent note; `comment {anchor?, note, hintOffset?, target?}` (anchor
present for a passage, absent for a whole-file comment, `target` from Slices 3 and 4);
`reply {commentId, note}`; `resolve {commentId, on}`; `log-edit {summary}` (called by the kernel
after a direct edit, see The comments log). Slice 2: `accept {ids}`, `reject {ids}`,
`accept-all`, `reject-all`. Slice 3: `retarget {commentId, target}`, the re-place of a region
comment (a new rectangle over the same figure, the hash recomputed from the bytes as they are
now; not appended to the comments log, since a re-placed rectangle is not a decision). Slice 5:
`save {content, ops}`. Every mutating verb (all but
`status`) carries a fence: `storeMtimeNs` must equal the sidecar's current mtime, with `""`
meaning the sidecar must not exist yet, so two browsers cannot both create it; `reject`,
`reject-all`, and `save` also fence on `fileMtimeNs`; `set-tracked` fences on `configMtimeNs`
the same way, since it writes `config.json`, not the sidecar, and the host script stats
`config.json` before and after inside the same process. From Slice 3 the two verbs that stamp a
figure's hash, `comment` with a `target` and `retarget`, also fence on the figure's bytes through
`figureHash`: the hash the last reply carried for that figure (`fileHash` on an image or PDF,
`embeddedHashes[src]` on a text file), checked against the bytes the host hashes for the target,
and a mismatch refuses `figure-changed`. This key is optional where the mtime keys are not: a
caller has no hash for a figure no reply has hashed yet, so a request naming none is checked on the
mtime fences alone, and a value that is not a sha256 hex is a caller bug, refused before any disk
read. A moved fence refuses, and the client re-issues `status`, re-renders, and retries by stable
change or comment id, surfacing a second refusal verbatim. `figure-changed` is not retried, because
a retry would stamp the new bytes: the person is told to reload and draw the region on the picture
as it is now. Nothing merges.

Refusal codes name the resolved path, tilde-collapsed: `no-node` (node absent on the owning
kernel; `status` returns it quietly and the action never appears), `editing-off` (an `error`
containing the phrase "file editing is off", the regex the viewer already matches, phrased for
comments: cannot write the comments for the file, dashboard file editing is off on this machine),
`store-moved`, `file-moved`, `config-moved`, `unsupported-version`, `corrupt`, `unreadable` (with
the OS error text), `anchor-not-found`, `anchor-ambiguous`, `tracked-inherited`, `no-comment`,
`too-large`, and from Slice 3 `figure-mismatch` (the anchored passage does not embed the `src` the
target names), `no-figure` (a re-place of a src-less anchored target whose passage embeds no
figure, or several distinct ones) and `figure-changed` (the figure's bytes are not the ones the
request's `figureHash` says were shown). There is no `no-root` code: a file with no landmark above
it gets `.trackchanges/` created beside it on the first mutating verb other than `log-edit`
(decision 37).

Kernel work, about 160 lines including the send op below: resolve `path` with
`_resolve_open_path` (`kernel.py:30654`); refuse mutating verbs while `_file_editing_on()` is
false, before any content check; run `node <host script>` with the request on stdin, argv as a
list, a 10 s timeout, in a `threading.Thread` as
`fileGitLink` does so the receive loop never blocks (the
`_git_out` discipline, `kernel.py:30830-30838`; the kernel already spawns node for its own bundle,
`kernel.py:5391`); parse one JSON object from stdout; a non-zero exit or bad stdout becomes
`fileCommentsFailed` with the stderr tail. The kernel never exports `TRACKCHANGES_ROOT` (it would
override every file's root for the CLIs, survey item A8). After a successful `saveFile` on a file that already has a sidecar, a comments log, or a
`config.json` entry covering it, the kernel calls the host script's `log-edit` verb (decision 33)
before replying `fileSaved`, so the reply can carry `logged: true|false` and the panel's Log is
current when the viewer hears the save; a save on any other file is traced as today and not
logged, a save on a path inside `.trackchanges/` is never logged, and `log-edit` never creates a
sidecar, a log, or a landmark. The summary is `{mtimeBeforeNs, mtimeAfterNs, bytesBefore,
bytesAfter, diff, truncated}`: `_save_file` returns the prior text beside the new mtime, the
`saveFile` handler (`kernel.py:39542-39556`, where the edit trace fires) builds a zero-context
unified diff capped at 200 lines or 16 KB (`truncated: true` when cut), and a failed append is
reported in the reply and never fails the save.
The authenticated `/defaults` payload the gear already reads reports the panel's verdict per
kernel (`ok`, `no-node`, or `agent-tooling-absent`), not `/version`, which is served before
authorization.

**The host script** (`tools/file-comments-host.mjs` in this repo, about 260 lines; decision 3)
imports `store-io.mjs`, `engine.js`, and the `addReply` function of `cli/track-reply.mjs` from the
copy of track-changents vendored into this repo (see Vendoring), so the kernel side needs no
track-changents install on the owning kernel. It reports whether the agent-side tooling is linked
there, by the presence of `~/.claude/hooks/track-reply.mjs` (placed by romp's `install.sh` from
the vendored copy, or by track-changents' own installer), since the session cannot answer a
comment without it. For every verb it reads the file as UTF-8 text and passes that string as the current text,
binary files included, so its fingerprint equals the CLIs'; `too-large` applies only to verbs
that write the file. It performs each verb as one load-mutate-write in a single process: root
discovery, sidecar path, the load-time rebase that re-places changes after external edits, anchor
location, comment construction, accept and reject through the engine, fingerprint, atomic write,
prune-when-empty, and the comments log append. For `comment` it builds the object itself in
`addComment`'s exact shape (`cli/track-comment.mjs:38-46`: id `${now}-${idx}`, `author`, `ts`,
`anchor`, `body`, `replies: []`, `resolved: false`, with `author` passed as `you` and no
`authorId`; `addComment` itself anchors at the first occurrence and cannot take an offset, so it
is not reused), and seeds a missing sidecar as `{v: 3, path, suggestions: [], comments: []}`
exactly as `track-comment` does; a whole-file comment has no anchor, no `target`, and the id
`${now}-0`. For a passage comment it re-reads the file and runs
`engine.locateAnchor` on the fresh text with the anchor the browser built from the displayed
text, hinted by the start offset; it saves only when the located text equals the quote,
rebuilding the anchor at the located position, and refuses `anchor-not-found` when the passage is
gone and `anchor-ambiguous` when two candidates tie. Reject writes the sidecar first, then the
file, and restores the prior sidecar bytes (or removes the sidecar it created, when none existed)
if the file write fails, the order `track-edit` uses (`cli/track-edit.mjs:108-128`); its file
write is atomic (temp file and rename in the same directory, through the realpath, mode
preserved, with a temporary name that does not end in `.json` so the other hosts' scans skip it) and applies the same 2 MB and UTF-8 checks as `_save_file`, refusing `too-large`
before any write. When `findVaultRoot` finds no landmark above the file (`store-io.mjs:43-54` walks up to forty
parents and returns null), `status` answers `root: null, storePath: null, trackedBy: null, store:
null` and the panel still offers Comment on this file and Track changes; `comment` and `set-tracked` then create `.trackchanges/` beside the file
and call `findVaultRoot` again, which now returns the file's directory, and the CLIs resolve the
same root from then on with no `TRACKCHANGES_ROOT`; `log-edit` never creates it. The host script's
accept verbs never drop a comment bound by `suggestionId`;
they set `resolved: true` on it, a stated divergence from the Obsidian host's accept-all, kept so
the comment ids in a sent message stay addressable by `track-reply`.

**`fileCommentsSend`**, the send op:

```
request  {type:"fileCommentsSend", reqId, sid, path, tracked, comments:[{id, desc, body}],
          accepted, rejected, watermark, todoId?}
reply    {type:"fileCommentsSent", reqId, queued}
refusal  {type:"fileCommentsSendFailed", reqId, error}
```

`tracked` is the client's post-toggle `status` verdict and picks the second bullet of the message.
`desc` is the first 40 characters of the passage for an anchored comment, the change's old and
new text for a comment bound by `suggestionId`, "this file" for a whole-file comment, and "the
region at x, y, w, h" (with the page for a PDF) for a region comment. `body` is the comment's
unsent `you` turns joined with a blank line, oldest first; a comment whose opening was already
sent lists only its new replies. `watermark` is the largest `ts` among the `you` comments and
replies the client included, taken from the `status` reply it built the message from. The kernel builds the message below and marker-neutralizes the
path and every body (`_neutralize_romp_markers`, `kernel.py:30786-30798`). Delivery follows the
`userTodoAnswer` handler (`kernel.py:12198-12250`) in its order and its ended-session refusal,
factored into one helper both ops call with a flag, and deviates on purpose where the message is
worth sending without a stamp: with the user-todos switch off, the message is sent, nothing is
stamped, and the reply warns with the switch's own reason; with the todo already settled, the
message is sent, nothing is stamped, and the reply warns naming the todo (the handler sends
nothing in both cases, and keeps doing so for its own op); an ended session refuses with the
existing revive-the-session text and sends nothing. Otherwise the helper calls
`_send_or_park(be, sid, body, echo="human" if be is _TMUX else None, user_todo=todoId)`, the
handler's own call: a "parked" result replies `queued: true` and stamps when the batch drains
(`_deliver_send_batch`, `kernel.py:22392`), a truthy result stamps at once through
`_stamp_user_todo_answered`, and a falsy result fails the op. Without a `todoId` the same
truthy-or-falsy split decides sent or failed. The body is not wrapped in the handler's "Re:"
form; it is its own message. The comments are already on disk before any send, so a refusal
loses nothing. After a sent or queued reply the kernel appends the `send` entry to the comments
log through the host script.

### The message to the session

The `[obsidian-diff]` shape the skill handles (`skill/SKILL.md:121-133` for the shape, `:85-91`
for the command lines), written in the person's voice like every injected body, batched:

```
[obsidian-diff] I left 3 comments on <absPath>.

Comment <id1> (on "<quoted passage>"):
<body>

Comment <id2> (on your change "<old>" to "<new>"):
<body>

Comment <id3> (on the region at 0.12, 0.40, 0.35, 0.20 of page 2):
<body>

I accepted 4 of your changes and rejected 1.

To respond:
  • reply in words:     node ~/.claude/hooks/track-reply.mjs --file <absPath> --thread <id> --note "<your reply>"
  • to revise the text: node ~/.claude/hooks/track-edit.mjs --file <absPath> --thread <id> --old "<exact text>" --new "<replacement>"

When you have addressed these, ask me for another look the same way you asked for this one,
naming the file.
```

The format is modeled on the VS Code host's `buildThreadPing` (`vscode/src/dispatch.ts:519-533`)
but is romp's own text. It keeps what the skill describes: the `[obsidian-diff]` prefix, the
absolute path, a comment id per comment (the CLI flag is still `--thread`, the format's word),
and the exact `track-reply` and `track-edit --thread` command lines. The tracking-on second
bullet restates the skill's own instruction, since no host emits one today (the VS Code bullet
says to edit normally, and the Obsidian host's message builder is a stub in its repo). With `tracked` false
the second bullet becomes the VS Code host's wording: edit the file normally and note it with
`track-reply`. For an image or PDF the second bullet says to regenerate the file with normal
writes and never to run `track-edit` on it; the agent can read images and PDF pages directly. The
closing sentence is what brings the loop back: the session's next todo is the return signal. The
text names no romp machinery; `tests/test_injected_voice.py` gains this body and the trace body
in its rendered set. The vendored skill gains one sentence saying a message may list several
comments, and one saying how to ask for another look.

### Vendoring

The user ruled to vendor now rather than wait for track-changents to be public (the user
2026-09-05), and to vendor the agent-side tooling too (the user 2026-09-06). `vendor/
track-changents/` holds a pinned copy of the MIT core with its LICENSE and source commit:
`package.json` (it pins the CommonJS reading of `engine.js` and the exports map), `engine.js`,
`display.js`, `protocol.js`, `store-io.mjs`, `cli/track-config.mjs`, `cli/track-edit.mjs`,
`cli/track-comment.mjs`, `cli/track-reply.mjs`, `cli/cli-args.mjs`, `hooks/track-guard.mjs`,
`skill/SKILL.md`, `obsidian/src/track-cm.js`, `obsidian/src/track-logic.js`, the
`applyEditsToText` function of `obsidian/src/track-rollup.js`, and the decorations block of
`obsidian/src/track-snapshot.js` adapted as described in Slice 5. The host script imports the node modules from it, and the
comments and editor chunks bundle the browser modules from it, so nothing depends on anything
outside this repo. romp's `install.sh` links the CLIs and the guard into `~/.claude/hooks/` and
the skill into `~/.claude/skills/tracked-changes`, and registers the guard as a PreToolUse hook
on `Write|Edit|MultiEdit` by extending the embedded registrar that already registers romp's hooks
in `~/.claude/settings.json` (`install.sh:109-167`): today its entries carry no matcher and it
appends only to the matcher-less group (`:149-152`), and its already-registered test compares the
exact `~/.claude/hooks/<name>` string (`:154-155`), so it gains a matcher-aware entry that finds or
creates the group with that exact matcher (the guard's is `async` false, since a deny must block,
and timeout 10, matching the upstream installer), and its presence check matches by basename, so
an entry the track-changents installer wrote with an expanded home path counts as registered and
is not doubled. Existing `~/.claude/hooks/track-*.mjs` and skill links that point at a
track-changents checkout are replaced with links into the vendored copy and the replacement is
reported, because the vendored copy carries fixes the checkout lacks. A machine that runs romp
then runs the whole loop with nothing else installed.

The vendored tree is the pinned upstream commit unchanged plus a patch series under
`vendor/track-changents/patches/`, one file per edit, applied at vendoring time and listed in
`vendor/track-changents/README.md`. The drift test checks two things: the vendored files equal
the pinned commit with the patches applied, and a track-changents checkout present on the
machine, if any, is at or past the pin. It never compares against whatever the checkout contains,
which by construction differs from a patched copy.

Three patches are offered back to the author: the A1 fix in `track-reply` and `track-edit`; a
non-text refusal in the guard and `track-edit`; and the skill edits (the two sentences above and
the C3 correction named under Risks). A fourth patch is romp's own and stays here: the guard
exits at once when `ROMP_SID` is absent from its environment (decision 24), as the first statement
of its `if (invokedDirectly)` block, before stdin is read, so the exported `evaluate()` and its
unit test are unchanged. Verified on the installed CLI: hook commands
inherit the session's environment, both romp backends set `ROMP_SID` there, and one of romp's
own hooks already gates on it (`hooks/romp-usertodo-context.sh:29`, rationale at `:11-13`); so the guard is registered
machine-wide yet inert in every session romp did not launch, at the cost of a node process that
exits immediately. Anything a romp session itself spawns also carries the variable and counts as
romp, which is the wanted behavior for the agent's own subprocesses.

### The comments log

Comments persist in the sidecar, but the sidecar forgets accepted and rejected changes and
deletes itself when a file has nothing pending, so a round of comments would leave no record in
git. The user asked for one (the user 2026-09-05). The host script therefore keeps an append-only
log beside the sidecar, `<root>/.trackchanges/<encodeURIComponent(relpath)>.comments-log.jsonl`,
in the same directory and outside the v3 contract: the other hosts' directory scans match only
`.json` names (`store-io.mjs:365`, and the Obsidian host's orphan-heal and badge scans,
`obsidian/src/track-snapshot.js:414, 2052, 2104, 3433`), so they never read it, and
the VS Code host reads only the sidecar path. One JSON object per line, each with `ts` (stamped
by the host script on the owning kernel), `kind`, and `author`:

- `send`: the message as sent, with `sid`, the session's display name as `sessionName` when the
  kernel knows one (so the panel's Log row can name the session after it is renamed or ended and
  the sid maps to nothing; the same name already reaches the sidecar as the author label of every
  reply the session writes), the comment ids, the `desc` and `body` of each, the counts accepted
  and rejected since the previous send, `queued`, and `watermark`, the largest `ts` among the
  `you` comments and replies it carried.
- `accept` and `reject`: the change ids and their `oldText` and `newText` at the time, so a
  decision survives the change leaving the sidecar.
- `set-tracked`: the entry written or removed.
- `edit`: a direct edit from the viewer (decision 33) on a file that already has a sidecar, a
  comments log, or a tracked flag, with the file's mtimes and sizes before and after and a
  zero-context diff capped at 200 lines or 16 KB; the kernel's `saveFile` path calls the host
  script's `log-edit` verb after a successful save and before the `fileSaved` reply, so the log has
  one writer and the panel sees the entry when the save lands.

`fileCommentsSend` appends its entry after a sent or queued reply, never after a refusal; the
accept, reject, and toggle verbs append theirs in the same process as the sidecar write. The host
script never rewrites or prunes the log. It serves two readers. The panel shows it as a Log
section, one row per entry, so the person can see what was said, sent, decided, and edited on
earlier occasions. And it holds the only state for what is unsent: the watermark is the `watermark`
of the last `send` entry, a `you` comment or reply is unsent when its `ts` is later, and accepts and rejects since the last send are counted from the log. The
`status` reply carries the derivation. A browser crash, a second browser, or a fresh machine all
see the same answer, which resolves the user's concern about a browser-local send state (decision
10). The log is JSON lines by the user's ruling (decision 16); a rendered export for reading on
GitHub can follow if wanted.

### Consent, trace, routing

Every verb that writes disk, sidecar included, sits behind the file-editing consent
(`kernel.py:30695-30700`): one mental model, the dashboard may write files on this machine, and
the sidecar is a file in the user's project. The first comment triggers the existing popup once.
That popup's copy promises the session is told when the user edits under it
(`file-view.ts:460-463`); Slice 1 amends it for comments, since they reach the session only when
sent (decision 5).

Verbs that change file bytes (`reject`, `reject-all`, `save`) send a trace to the session whose
cwd contains the file, first person like `_edit_trace_body`: I rejected N of your tracked changes
in the file while reading it; the file and its sidecar both changed, so re-read before writing.
Sidecar-only verbs send nothing; the sent message carries the news, and the CLIs read the sidecar
on every call. Host-script writes never pass through `saveFile`, so the generic `_edit_trace` is
untouched; a sidecar hand-edited in the viewer traces like any other file, as the
never-lose-the-thread rule requires.

Both ops carry `sid`; `routeOutbound` routes any op with a scalar id field to the owning kernel
and strips the prefix (`federation.ts:53, 278-288`), so a `host:sid` file's comments land on the
kernel that owns the disk. The sidecar's bytes reach a remote browser over the same
`/remote/<host>/file` relay the file does, which mirrors the mtime header on HEAD
(`kernel.py:39930`).

## UX

### The surface, in its Slice 2 state

```
┌ Files ──────────────────────────────────────────────────────────────────────────────┐
│ ~/code/notes-api/docs/report.md   Rendered · Raw   Edit   GitHub ↗   Comments · 2 · 5 changes   ✕ │
├───────────────────────────────────────────────────┬──────────────────────────────────┤
│ ## Findings                                       │ Track changes [on] · Comment on this file · Send to session (3) │
│ The api session ~~reduced~~ cut p95 latency       │ ──────────────────────────────── │
│ by 40% ▍web                                       │ ▍web  "reduced" to "cut"         │
│ ...                                               │       [Accept] [Reject] [Reply]  │
│ We recommend ▌shipping the cache in v1.2.         │ ▍you  on "shipping the cache…"   │
│                                                   │       Which cache? Say which.    │
│                                                   │       ↳ web: The response cache. │
│                                                   │       [Reply] [Resolve]          │
│                                                   │ … 4 more changes                 │
│                                                   │ Accept all · Reject all          │
│                                                   │ Log ▸                            │
└───────────────────────────────────────────────────┴──────────────────────────────────┘
```

- **Progressive disclosure**: the action-row label is the glance, the panel is one click, a
  comment expands on click, keyed by comment id in a set that survives the poll's re-render. For
  a file with neither sidecar nor tracked flag the action reads plain "Comments" and the panel
  holds the Track changes toggle (file or folder), the Comment on this file button, and an empty
  Log; counts and highlights appear once a sidecar exists.
- **Raw view is exact, Rendered view is best effort.** Changes are offsets into the source. In
  Raw, insertions tint, deletions render struck at their point, substitutions show both, each with
  the author's session chip in the session's color. In Rendered, insertions and substitutions are
  re-found by their text and highlighted; a deletion cannot be placed in rendered prose and
  appears only as a card, whose **Reveal** switches to Raw and scrolls there. An unpainted change
  always has a card, so the compact view never dead-ends. Session colors come from one
  `GET /sessions` fetch per panel open, mapping `authorId` to name and color; an author with no
  live match gets a neutral chip with its label.
- **Comment on a selection**: selecting a passage still seeds the quote chip when a chat composer
  is reachable; with the panel open a floating **Comment** button also appears beside the
  selection's bounding box (the chip lives in another iframe, so "beside the chip" is not
  possible), and the selection hook runs before the composer gate so it works with no chat pane.
  The button opens a one-line composer in the panel with the quote shown; Enter saves to the
  sidecar and the highlight and card appear at once. **Comment on this file** in the panel
  header writes a whole-file comment on any file. The mapping from a selection to a source anchor,
  in both views and every format, is specified in the next subsection.
- **Send to session** sends everything unsent in the file: comments, replies, and the accept and
  reject decisions made since the last send; the number on the button is that count. It lists what goes, confirms once pane-locally,
  disables and relabels itself while sending, then shows "Sent to <session> at <time>", or
  "Queued for <session>" when the reply carries `queued: true`, and keeps polling while open. The
  confirm carries up to three checkboxes, all checked by default: **answer the todo** when the
  file was opened from one; **turn on tracking so the session's edits come back as changes** when
  it is off (file scope); and, from Slice 2, **accept the N pending changes** when any exist, so
  the session's later edits arrive as fresh changes rather than coalescing into an old one. The
  sequence is fixed: the message is built from the current sidecar, then `set-tracked`, then
  `accept-all`, then `fileCommentsSend` with `tracked` set to the post-toggle verdict; a refusal
  at any step aborts the sequence before the send and shows the refusal; the log entry is appended
  after the send succeeds or queues. One send per file: when a todo names several files, the
  first send answers it and later sends for the other files show no todo checkbox.
- **What counts as unsent** is derived from the comments log on the owning kernel (see The
  comments log), never from browser state; the `status` reply carries it, and the confirm always
  lists what goes.
- **Direct edits.** Edit and Save work as today for an untracked file or a tracked file with no
  pending changes; the save traces to the session and, when the file has a sidecar, a log, or a
  tracked flag, is logged (decision 33). While changes are
  pending (Slices 1 to 4) the Edit button refuses with a one-line reason naming the count, because
  a raw save over pending changes rewrites their offsets. In Slice 1 the reason says that accept
  and reject arrive with the next slice and that the session's own `track-edit` still works; from
  Slice 2 it says to resolve the changes first. Slice 5 lifts the refusal.
- **Errors** render inside the panel as an error row under the control that asked, in the
  viewer's `fileview-err` dress; `store-moved`, `file-moved`, and `config-moved` offer Reload. A
  federation `warn` arriving while a request is outstanding is treated as that request's failure
  with the warn's text. An `editing-off` refusal runs the same confirm-then-consent-then-retry
  branch the viewer's Save uses, lifted into a shared helper (see the seam below).
- **Click-safety**: the panel re-renders on every poll, so its controls delegate to one stable
  root (`actions.ts` `delegate()`) with `flash()` acknowledgement; waits show the romp loader;
  sizes and menu tokens follow `ui/CLAUDE.md`.
- **Phone**: the panel, reading, and commenting work on the phone as the same webview; region
  drawing by touch is not attempted in v1 (the user 2026-09-06).

### Commenting from either view, and in every format

Commenting works in whichever view the person is reading. The viewer has two views of text: Raw,
which every text format has (markdown, HTML, XML and SVG source, CSS, code, CSV, JSON, logs, and
the rest of the kernel's text allowlist), and Rendered, which only markdown has. HTML is never
rendered by the viewer (the kernel serves it as plain text and the file-browser plan records that
stance), so commenting on HTML means commenting on its source. Images and PDFs have no text view;
their commenting is covered below and in Slices 3 and 4. Every file, text or not, takes a
whole-file comment.

A comment made from a selection in either view is stored with an anchor whose quote is an exact
substring of the file text the host script read, so the agent CLIs, the sidecar's re-anchoring
on load, and the two existing editor hosts treat it the same as a comment written by the comment
CLI. The browser builds the anchor from the displayed text with the engine's `makeAnchor` (the
quote plus 24 characters of prefix and suffix) and sends it with the note and the start offset;
the host script re-reads the file and locates the anchor with the engine's `locateAnchor`, hinted
by that offset, and refuses when the located text differs from the quote or two candidates tie.
The typed note is never discarded by a refusal.

In Raw view the mapping is exact. Each logical line is one row whose text equals the source line
(the viewer always soft-wraps, and the row number is CSS content that never enters a selection),
so a selection endpoint becomes a line index and a column from the row's text nodes, the pair
becomes a source offset range, leading and trailing whitespace is trimmed, and the quote is the
source slice with its interior line endings. A selection that reaches outside the rows snaps to
the first or last row when its container is an ancestor of the code element, and refuses
otherwise. The self-check compares the text-node concatenation of the untrimmed range with the
source slice minus its line endings, exactly.

In Rendered view the browser rebuilds the rendered text from the source with the same markdown
lexer the viewer renders with, recording the source index of every character it emits and
verifying every token's source text at the position the walk assigns it; a block whose tokens
cannot be placed refuses rather than yielding a wrong quote. The walk drops the marks the
renderer consumes: heading hashes, list bullets and indentation, blockquote markers, emphasis and
strong delimiters, inline code backticks, link brackets and destinations, backslash escapes,
reference definitions, hard-break spaces and backslashes, and task-list checkboxes. A top-level
block counts as aligned only when its text with all whitespace removed equals the corresponding
rendered element's; the comparison ignores whitespace entirely because the renderer's line breaks
carry no text. A selection whose endpoints fall in aligned blocks maps back to a source range,
and that source slice is the quote; endpoints in the whitespace between blocks snap to the
nearest block edge. Fenced and indented code, tables, HTML blocks, prose blocks containing HTML
entities, link labels with escaped brackets, list or blockquote lines that begin with a tab after
the marker, and any block that fails alignment refuse in Rendered view. A selection spanning two
aligned blocks is accepted, and its quote includes the blank line and block markers between them,
which the composer shows before saving. A selection whose edge falls inside a mark the renderer
consumed paints narrower in Rendered than in Raw, never wider.

When the mapping refuses, the composer keeps the typed note, states the reason in one line, and
offers a switch to Raw that preselects the same passage when its text occurs in the source (code
fences) and otherwise opens scrolled to the block's first line with the note intact (tables and
HTML blocks).

Painting distinguishes three states after the engine locates a comment's anchor in the current
text: located at the quote, painted normally; quote gone but its context found
(`engine.js:793-800`), painted over the between-context region in a text-changed style with a
card; neither found, shown as a card only, marked detached in the panel. Detached is a rendering
state here, not a stored flag; the host script never calls the engine's comment pruning, and the
comment stays in the sidecar. In Raw view a located comment is painted by offset over the line
rows, with no text matching. In Rendered view the located source range is converted through the
same index map to a highlight over the rendered text; a comment inside a refused block falls back
to a whitespace-tolerant match of its quote stripped of inline markup, and a comment that cannot
be painted has a card whose Reveal switches to Raw and scrolls to the passage.

Images and PDFs. A figure embedded in a markdown file is commented on through its embed line: in
Rendered view a click on the rendered image offers Comment, the anchor is the embed's source
text, and the highlight is a frame around the image; in Raw view the embed line is text like any
other. A standalone image or PDF opened in the viewer takes the whole-file comment in Slice 1,
which lands in the file's own sidecar; it renders as a card in every host and the agent replies to
it with `track-reply`. Region comments, drawn as a rectangle on the image or on a PDF page, carry
the `target` field: on images from Slice 3 (its build note under Build slices says what the host
stores and reads for them), on PDF pages from Slice 4.

Acceptance criteria:

- Raw: for every pair of source offsets in a fixture with CRLF line endings, leading tabs,
  highlighted syntax, and a trailing newline, whose end characters are non-whitespace, a DOM
  selection constructed at those offsets (each end tried as a text-node boundary and as an
  element boundary) stores a quote equal to the source slice, and the highlight after reload
  wraps exactly the text nodes of that slice. A CR-only line and a selection ending past the last
  row are included.
- Raw: a quote that occurs twice anchors to the selected occurrence, including when two lines
  are inserted above the passage between the selection and Enter.
- Rendered: for a fixture covering both heading styles, tight and loose lists, nested and task
  lists, blockquotes, emphasis, strong, strikethrough, inline code, every link form, images,
  escapes, hard breaks, and a reference definition, every selection inside aligned blocks yields
  a quote whose walk-mapped characters equal the selected rendered characters one to one, and
  painting the stored anchor in Rendered wraps exactly the originally selected text; the reply
  CLI reads the resulting comment unchanged.
- Rendered: a selection touching code, a table, an HTML block, an entity-bearing paragraph, or
  an escaped link label is refused, the note survives, and the Raw offer opens with the passage
  selected when its text occurs in the source, else scrolled to the block.
- Every text format: a comment from the Raw view of an HTML, SVG, CSS, CSV, and code fixture
  stores the exact source slice.
- Both: with the author label held equal, the comment object written from either view
  deep-equals the one `addComment` writes for the same quote and note, apart from id and `ts`;
  the sidecar's changes, fingerprint, and version are unchanged.
- Both: after an agent edit moves the passage, the highlight follows the engine's relocation in
  both views; when only the context survives, the text-changed style appears in both views; when
  neither survives, the card shows detached in both views and the comment remains in the sidecar.
- Whole-file: a whole-file comment written from the viewer on a text file, an image, and a PDF is
  replied to by `track-reply`, renders as a card in the VS Code host's loader and the Obsidian
  host's reader, and the file's bytes are unchanged.

### The viewer seam

The panel needs more of the viewer than the registry's `{path, sid}` context gives. Slice 1
extends `FileViewActionCtx` with `todoId?`, `body()`, `mode()`, `text()`, `mtimeNs()`,
`onRendered(cb)`, `onSelection(cb)`, `post(msg)`, `ensureEditingAllowed()` (the first-consent
popup and the re-consent-on-refusal branch, today closures inside `openFileView` and `doSave`,
lifted into one exported helper that Save and the comment verbs both call), `setEditBlocked(reason
| null)`, `aside(el | null)` (mounts or removes the panel beside the body; the viewer owns the
two-column CSS and the narrow-column fold), `setMode("raw" | "rendered")`, `scrollToOffset(n)`,
`onSaved(cb)` (fired on the `fileSaved` reply, which by then carries `logged`, so the panel can
refresh its Log), and `reload()` (re-fetch
bytes and mtime, re-run `renderBody` and `onRendered`, keep the action row and panel). The action
row itself stays registry-only. `file-comments.ts` registers its own `message` listener for its
four reply types.

### Getting into it

- From the Waiting-on-you pane: the todo's detail path is a link (Slice 0). The pane is its own
  iframe, so the link posts `{romp:"viewFile", pane:"pane", path, sid, identity:{name,color},
  todoId}` to the shell, the Files-pane branch that turns the pane on and forwards the message
  (`kernel.py:34486-34493`); the shell forwards `todoId`, `files.ts` passes it to
  `openFileView(path, sid, {todoId})`, and relative paths resolve on the kernel through
  `_resolve_open_path`. When the pane is not framed by the shell, the detail stays plain text.
- From the viewer: the Comments action, on any file, on a machine whose kernel has node. If the
  action is missing, the gear's row beside "File links open in" names the machine and the reason
  (`no-node`), and the same row warns when the agent-side tooling is not linked and offers to run
  the link step; the guide says to look there. (Slice 1 ships the row naming the reason and the
  command to run, without the one-click link step; see decision 39.)
- From the chat: a file link opens the viewer as today; Comments is one click further.
- From the session's side: romp's default session prompt (`claude/romp-session-prompt.md`,
  symlinked by `install.sh:173` and appended to the system prompt by both backends) gains one
  sentence in its Working style section, after the paragraph on locating paths (the user
  2026-09-06), in the person's voice and conditional on the tool: when you want me to look at a
  file, flag it with `add_user_todo` if you have that tool, with the file's absolute path in the
  detail; I open it from there, and my comments come back to you as a message with instructions;
  without the tool, say so in your reply. It does not go in the Housekeeping section, which
  `CLAUDE.md` reserves for explaining romp's artifacts. The vendored skill gains the sentence on
  asking for another look. Both speak as the person and name only what the agent already sees,
  so the veil holds.
- An ended session's todo is hidden from Waiting on you until the session is revived, since the
  board lists living sessions only and gates ended ones (`kernel.py:25731, 26082-26087`; the
  chat's own card gate is at `24047-24062`), so a todo can vanish; the file is still on disk and
  Comments works on it without a todo. The guide says: if a todo you expected is missing, check
  for an ended session (revive it) or for a session hidden from the feed (Show in feed on its tab
  menu); the Slice 0 review found the hidden case was missing from the first wording.

## Build slices

The user ruled that all six slices are built in one push (the user 2026-09-05), leaving how to
staff and sequence it to the implementing session, with a dedicated new session suggested. Each
slice stays independently useful and lands as its own fork PR with an adversarial review pass, in
the order below unless the implementing session finds a reason to reorder. The push is done when
every slice's acceptance passes and the user completes the motivating loop with no GitHub and no
Obsidian (decision 29); the implementing session files one user todo at the end asking for that
walk, not one per slice (decision 21). Sizes are approximate new lines, webview TypeScript /
kernel Python / node.

### Slice 0: from the todo to the file in one click

User-visible: in the Waiting-on-you pane, a file path in a todo's detail is a link that opens
the file in the Files pane; the Reply modal shows the same link. Commenting is today's quote-chip
flow, and Reply on the todo is the done gesture. This alone removes the GitHub detour for
comments that need no persistence.

Acceptance: both `waiting.ts` render sites (`:209`, `:126-127`) turn the detail's path into a
link that posts the `viewFile` message above; the shell forwards `todoId`; relative paths resolve
against the todo's session on the kernel; `ui/webview/user-todo-links.test.ts` pins the posted
payload and both callers of the shared matcher.

Files: `render.ts` exports nothing and is the chat entry, so the path-token matcher
(`CLICKABLE_PATH_RE`, `looksLikeFilePath`, `looksLikeBareFileName`, `fileUriToPath`, the
trailing-punctuation trim; `render.ts:1338-1520`) moves into a new `ui/webview/path-links.ts`
that emits `.file-uri-link` spans carrying `data-act="openpath"`, `data-path`, and `data-sid` and
binds nothing; `render.ts` re-imports it and keeps its previews, its own listener, and
`openPath`; `waiting.ts` adds `openpath` to its existing delegate handler map and one direct
listener in the static Reply modal, since its rows are rebuilt on every feed frame; the shell
relay's forwarded object gains `todoId`; `file-view.ts` gains `openFileView(path, sid, opts?:
{todoId?})` and `FileViewActionCtx.todoId?`; `files.ts` passes `m.todoId` through; `docs/guide.md`.
Size: ~100 to 200 / ~10 / 0.

### Slice 1: file comments, the tracking toggle, one Send to session

User-visible: the Comments action; the panel with a Track changes toggle (file or folder),
comment cards, and the Log; Comment on a selection in either view of any text format; Comment on
this file on any file, images and PDFs included; highlights in both views; replies from
`track-reply` appearing within the poll interval; Send to session as one message with two of the
confirm checkboxes (answer the todo, turn on tracking); direct edits logged; the Edit refusal
while changes are pending; the gear row reporting the verdict; the installer linking the vendored
tooling; the default-prompt sentence.

Acceptance: the criteria under Commenting from either view; a first comment on a clean file
creates `.trackchanges/` and the sidecar exactly where `storePathFor` puts it; the toggle writes
`config.json` through `setTracked`, fenced on `configMtimeNs`, and `off` on an inherited file
refuses `tracked-inherited`; a mutating verb on a moved sidecar refuses and the panel reloads and
retries; the sent text carries the `[obsidian-diff]` prefix, the absolute path, and each comment
id in the form the skill describes, and the kernel and webview builders produce identical text
for one and for several comments; a send with `todoId` follows the helper's branches (switch off,
settled, ended, and the send arm's parked, sent, and refused outcomes); the first mutating click
triggers the consent popup once; the comments log gains a `send` entry after each send, an `edit`
entry after each direct edit, and the unsent count is derived from it; on a live SDK session the
guard denies a raw Write on a tracked fixture and passes a non-text file through, and
`track-config` answers; spawned without `ROMP_SID` the guard exits 0 before reading stdin (node
test); romp's installer links the tooling idempotently,
leaves an existing track-changents install in place, and registers the guard once.

Files: new `ui/webview/file-comments.ts` (registration, panel, highlight pass and the two mapping
walks, Comment buttons, poll, Log, send composer), `vendor/track-changents/` with its pin and
drift test, `install.sh` and `tests/install-sh.bats` (the vendored CLIs, guard, and skill linked
into `~/.claude/`, the registrar's matcher support, and the guard registered on its own
`Write|Edit|MultiEdit` group),
`tools/file-comments-host.mjs` and its node tests, `tests/test_file_comments.py`,
`ui/webview/file-comments.test.ts`, `docs/adr/0002-file-comments-in-the-track-changents-sidecar.md`
(accepted with this slice); touched: `kernel/kernel.py` (the two ops, the shared todo-answer
helper, the `log-edit` call after `saveFile`, the `/defaults` verdict), `file-view.ts` (the seam
above), `files.ts` (the `/sessions` color map), `gear.js` (the verdict row), `styles.css` and
`files-pane.css` (about 80 lines adapted from the Obsidian host's stylesheet, mapped to
`--accent`, `--bg`, `--fg`), `claude/romp-session-prompt.md` (one sentence), `docs/guide.md`.
track-changents code reused unchanged from the vendored copy: `store-io.mjs`, `engine.js`
(`makeAnchor`, `locateAnchor`, `toHunks`, `baselineOf`), `addReply`. Size: ~600 to 750 for
`file-comments.ts` (the Rendered walk is the largest part) plus ~110 to 140 for the seam and ~30
for `files.ts` and the relay / ~160 / ~260, plus about 150 lines of tests on each side.

### Slice 2: the session's changes as accept/reject cards and inline marks

User-visible: change cards grouped by paragraph with Accept, Reject, Accept all, Reject all, and
a Reply bound to the change so the agent's `track-edit --thread` revisions fold into it; inline
marks in Raw, highlights in Rendered, Reveal for deletions; Send to session states accepts and
rejects and offers the accept-pending-changes checkbox.

Acceptance: accept changes the sidecar only (the engine's `acceptSuggestions`) and marks bound
comments resolved without dropping them; reject applies the engine's reverse edits to the file
and writes sidecar then file with rollback; both fence on the sidecar mtime and reject also on
the file mtime; after a reject the owning session receives the trace; a `track-edit` landing
mid-round makes the next Accept refuse and reload; accept-all on a file with no comments prunes
the sidecar as `pruneIfClean` decides; a sidecar holding one whole-file insertion renders one card
whose Accept clears it; each accept and reject appends to the comments log.

Files: `file-comments.ts` (the card model ported from the VS Code host's `buildCards`,
`vscode/src/panel.ts:194-300`, and its `weave` and `awaitState` helpers at `:301-351`; the port
replaces its two host inputs, the `vscode.TextDocument` and the configured label, with the
current text and `you`, and adds the buttons that panel deliberately lacks; the Raw painter over
the viewer's line nodes), CSS (about 120 lines), `kernel.py` (trace after reject), host script
verbs. Reused unchanged: `engine.js` accept/reject (`engine.js:388-419`), `display.js`
`planDiffDisplay`; adapted: `applyEditsToText` (12 lines from `obsidian/src/track-rollup.js`).
Size: ~400 / ~40 / ~120.

The Slice 2 build (2026-09-06), panel side: the card model lives in `file-comments-model.ts`, the
panel's pure half, beside the Slice 1 comment cards; the paragraph grouping is romp's own pass over
paragraph ranges (the source split on blank lines), since `planDiffDisplay` merges only a dense
paragraph and names no paragraph for the changes it passes through. A comment bound to a pending
change is shown on the change's card and leaves the comment list; once the change is decided, the
comment's card stands on its own again with the change's texts read from the log's accept or reject
entry, which is also what `describeComment` falls back to, so a manual Accept before the send keeps
"on your change …" in the message. Reply on a change card writes `comment {suggestionId, note}`,
an argument the verb list above does not name. After a reject the panel reloads the view itself:
every reply re-baselines the poll, so the poll never sees the bytes the reject changed. The new
elements (`.fc-change`, `.fc-group`, `.fc-hosted`, `.fc-foot`, `.fc-diff`) wear the Slice 1 classes
beside their own and need no rule of their own to be usable; the sheets are the painter's.

### Slice 3: region comments on images

User-visible: on a standalone image, or on a figure embedded in a rendered markdown file, the
person drags a rectangle and comments on it; the rectangle paints over the image with the
author's chip, and the card shows a thumbnail crop. When the image's bytes change, its region
comments show as stale until resolved or re-placed. The sent message names the region. Desktop
only in v1; on the phone the whole-file comment stands in.

Acceptance: a region comment carries `target {kind: "image", region, hash, src?}` in fractions of
the image's natural size, plus the embed-line anchor and `src` when the figure is embedded, and no
anchor when standalone; `track-reply` replies into it; the Obsidian and VS Code hosts show it as a
discussion card (embedded: on the embed line) and preserve `target` on their next write; a
regenerated image flips the comment to stale by `hash`; the rectangle re-paints correctly at any
viewer width.

Files: `file-comments.ts` (the overlay, the drag, the crop), `file-view.ts` (a hook exposing the
rendered image elements), the host script (`comment` accepts `target`; `hash` computed from the
bytes), `kernel.py` (none beyond passing the field), CSS. Dependency: the non-text refusal in the
guard and `track-edit`, which lands in Slice 1; the `target` field is romp-only (decision 13).
Size: ~250 / ~10 / ~40.

The Slice 3 build (2026-09-06), host side: the stored target is `{kind, region, page?, hash, src?}`
in that key order, `src` on an embedded figure only (the contract's `target` bullet says why the
destination is stored rather than derived). `hash` is the host's sha256 of the figure's bytes,
streamed and never decoded, since the UTF-8 read every other verb makes is lossy for an image; the
client's value, if any, is ignored. `comment` runs its checks in a fixed order. The fence's shape
and the target's shape come first, before any disk read, and a bad shape is a caller bug: `kind`
image or pdf, the region inside the unit square at four decimals, `page` on a pdf only, `src`
exactly when the comment has an anchor, `figureHash` a sha256 hex and only with a target. Then the
anchor is placed, and the anchored passage must embed the `src` the target names
(`figure-mismatch`, a refusal rather than a caller bug: a reference definition can change on disk
between the drag and Enter). Only then is the figure resolved and hashed: `unreadable` when the src
is a URL, resolves outside the project root, or is not a regular file; a caller bug when its
extension is not the kind the target claims, or one the viewer never shows as media; `too-large`
past the 50 MB the viewer shows, refused before a byte is read (before this cap a multi-GB src
pinned the host until the kernel's deadline); and last, when the request's fence carries
`figureHash`, `figure-changed` unless the bytes hashed are the ones it names (the Slice 3 review,
2026-09-06: before this fence a figure regenerated between the drag and Enter was stamped with the
new bytes' hash, which every reply then equalled, so the panel read a rectangle drawn on the old
picture as current on the new one, the one write the hash exists to catch). The host checks that
fence whenever a request carries it, and the kernel passes the fence object through whole. The
panel's Slice 3 build sends the three mtime keys only, so none of its requests is fenced this way
yet; sending the hash its status holds for the figure is the panel's follow-up. `retarget` is the
same path for the same figure: a stored `src` must be named again, unchanged, and the same fence
applies. The reply's hash fields are described under the op above. A text file's figures are
hashed under one 200 MB budget per call; past it, or when a src fails a check, the hash is null
with the reason beside it, not a refusal. A stored target with an anchor and no `src` (the
contract's first shape) is told its figure from its passage on every reply and on a re-place that
names none, and refuses `no-figure` when the passage embeds none or several distinct ones (one
figure embedded twice still tells). A `src` is decoded as the viewer decodes it before it resolves
(`p95%20latency.png` is the file with the space) and stored as written. Panel side: the poll HEADs
every figure a text file's open region comments name beside the file and the sidecar, so a
regenerated embedded figure re-asks `status` and flips by hash; a resolved comment's card shows the
resolved tag alone (no stale tag, no Re-place, no rectangle), so a figure only resolved comments
name is not watched, and reopening one is a write whose reply carries the hash to flip it by; the
sent message names the figure of a region comment on an embedded figure; a stale card offers
Re-place. `kernel.py` is unchanged, as the Files line says.

### Slice 4: PDFs rendered in the viewer, with page and region comments

User-visible: a PDF opens as rendered pages inside the viewer instead of the browser's own frame,
with the same Comment on this file button and the same rectangle gesture per page; a region
comment names its page; the card shows the page crop.

Why a slice of its own: the browser's PDF frame gives the page no coordinates or selection, so
region comments need romp to render pages itself. Ruled (decision 12): a lazily loaded PDF chunk
built on pdf.js (Apache-2.0, matching romp's license), in the same on-demand pattern as the editor
chunk, loaded only when a PDF opens; the fallback for a failed chunk load is today's frame with
whole-file comments only. The alternative, rasterizing pages on the owning kernel with a
command-line tool, was rejected as a new kernel-side tool and route.

Acceptance: pages render within a stated size cap for PDFs, loudly refused above it; a region
comment carries `target {kind: "pdf", page, region, hash}`; a regenerated PDF flips its region
comments stale; `track-reply` replies into them; the main bundles stay byte-stable with the chunk
lazy.

Files: new `ui/webview/pdf-chunk.ts` esbuild entry, `file-view.ts` (the PDF branch mounts the
chunk when the panel is open, else the frame), `file-comments.ts` (per-page overlays), the host
script (no change beyond Slice 3), `kernel.py` (a size cap for the chunk's fetch). Size: ~350 /
~20 / 0.

### Slice 5: live CodeMirror editing over pending changes

User-visible: Edit works on a tracked file with pending changes; CodeMirror shows insertions
tinted and deletions struck inline; typing remaps the changes rather than desyncing them; click
accepts, modifier-click rejects; undo restores an accepted change; Save writes file and remapped
sidecar together, and the Edit refusal disappears.

Acceptance: the cases of track-changents' `obsidian/tests/track-cm.test.mjs` and
`track-cm.undo.test.mjs`, copied into romp with their `createRequire` loads of
`../src/track-cm.js`, `track-changents/engine`, `@codemirror/state`, and `@codemirror/commands`
rewritten to romp's comments chunk and its CodeMirror (the tests use Node's own `require`, which
a vitest alias cannot redirect), pass as the behavioral oracle; a save refuses when either mtime
moved and keeps the buffer; `editor-lazy.test.ts` pins that the main bundles stay byte-stable.

Files: `editor-chunk.ts` (a typed `track` mount option curated inside `extensionsFor`,
`editor-chunk.ts:113-135`, consumed only by `file-view.ts`; the header doctrine comment names
it), a new lazy comments chunk esbuild entry bundling, from the vendored copy, the engine, the
78-line CodeMirror state field (`obsidian/src/track-cm.js`, unchanged), the decorations block
(`obsidian/src/track-snapshot.js:433-839`) together with `obsidian/src/track-logic.js` (215
lines of display-planning and click and layout helpers the block calls), with the one Obsidian
read at `:595-596` replaced by a constant and the `mouseover` handler at `:774-781` fixed to take
the editor view (survey A6), `file-view.ts` `doSave` sending the `save` verb instead of
`saveFile` when the panel is open. Size: ~500 / ~60 / ~40. Lowest confidence of the six; it is
the one slice that touches the editor chunk's contract.

### Optional: per-comment fork dispatch

A card's **Discuss in a side session** forks the owning session at its tip with the comment's
message as the opener, through the door built for it (`_fork_comment_request`,
`kernel.py:10981-11023`), and the existing comment-thread popover shows the fork's conversation.
SDK sessions only; each fork is a CLI holding the parent's context, so per comment and never by
default. `_fork_promote_request` returns `name` only today (`kernel.py:11043, 11047, 11052`)
while the track-changents consumer reads `promotedName` (`obsidian/src/track-snapshot.js:1445`),
so this slice adds `promotedName` beside `name` in all three success arms, with a test. A WS op
wraps the POST so the webview needs no serve token. Parked until asked for (decision 1). Size:
~60 / ~20 / 0.

## Security posture

Unchanged in kind, and stated rather than silently widened, as the file-browser plan did for
saves. `fileComments` is issuable from any authenticated socket, like `saveFile`; every verb that
writes disk sits behind the same server-side consent gate, checked before any content check; the
server-side gate is the enforcement and the UI's checks are convenience. The host script runs
only on the owning kernel, on paths resolved by the kernel (and, from Slice 3, on the figure
paths the next paragraph describes, the one class of path it resolves itself), and writes only the
sidecar, the comments log, `config.json`, and (on reject or save) the commented file. The mtime
fences refuse and never merge. Both ops route by `sid` to the owning kernel over the existing federation
splice; nothing new is exempt from `_authorize`, and the panel's verdict rides the authenticated
`/defaults` payload rather than `/version`. The installer's new step registers a PreToolUse hook
that runs on every Edit and Write in every Claude Code session on the machine; it exits at once
in any session romp did not launch (no `ROMP_SID`), and in romp's sessions it is a path check
that passes untracked files through.

From Slice 3 the host also reads one class of path the kernel did not resolve: the figure a region
comment's `target.src` names (the Slice 3 build, 2026-09-06). The client names that path on
`comment` and on `retarget`, and every reply reads it back out of the sidecar; the host resolves
it. It is only ever read, to hash it: the sha256 of its bytes is what the reply carries, and
nothing under it is written or served. The host bounds the read itself. The src is decoded as the
viewer decodes it, refused when it is a URL, resolved against the commented file's directory, and
confirmed by realpath to lie inside the project root (never above it, not out through a symlink,
and an absolute src held to the same check) and to be a regular file, opened non-blocking so a
FIFO or a directory fails at once instead of hanging. On a write verb the src must also be a figure
the anchored passage embeds (`figure-mismatch`), of the kind the target claims by its extension,
and under the 50 MB the viewer shows, refused before a byte is read. On a reply the host hashes
every in-root regular file the sidecar's srcs name, of any extension, under one 200 MB budget per
call; a src that fails a check gives a null hash with its reason rather than a refusal, so a
comment another writer left is shown as unknown and not hidden. The reply's read runs on `status`
too, outside the consent gate, as reading the commented file does. This widens by one step what
an authenticated client can learn, and the step is stated here rather than left implicit: a
writer that can already put a src into a sidecar (the agent CLIs, or the viewer, whose Save edits
a sidecar like any text file when the consent is on) can learn the sha256 of any regular file
inside the project root by naming it there, never its bytes, including a file the viewer would not
serve because it never renders that extension. A socket with no such write names only a figure its
anchored passage embeds. Refusing on a reply what a write verb refuses (a non-media extension, a
src the passage does not embed) is the follow-up if that hash is judged worth withholding; the
Risks bullet on figure paths names the trade.

## Doctrines this respects

- **Philosophy** (`CLAUDE.md`): the count is the glance and the panel one click deeper; Send to
  session batches N comments into one interruption; never-lose-the-thread holds on disk, since
  comments live in the sidecar before any send, detached comments and changes are kept rather
  than dropped, the todo stamps only at delivery, every file-changing verb traces to the session,
  and the comments log keeps what the sidecar forgets.
- **Event over time** (`CLAUDE.md`, Design): the poll stands in for an event source the Files
  pane does not have; the person's own writes never wait on it, since every verb reply carries
  fresh mtimes that rebase the poll.
- **The veil** (`CONTEXT.md`): the sent message, the trace, the skill sentences, and the
  default-prompt sentence speak as the person and name no romp nouns.
- **No plugin API** (`ui/webview/editor-chunk.ts:1-15`): Slices 0 to 4 never touch the chunk.
  Slice 5 adds a typed, internal `track` option, not a generic extension hook.
- **UI rules** (`ui/CLAUDE.md`): click-safe delegation, keyed expand state, one font-size
  vocabulary, `var(--accent)`, the romp loader on waits, no dead ends.
- **Coordination**: the implementing session works on its own worktree and publishes a working
  note naming `kernel/kernel.py` (the two ops), `file-view.ts`, `waiting.ts`, `files.ts`,
  `editor-chunk.ts`, `install.sh`, and `claude/romp-session-prompt.md` before editing; several
  live sessions edit `kernel.py`.

## Risks

- **Two writers on one sidecar** (agent CLIs and the host script). Mitigation: one
  load-mutate-write per verb, mtime fences, refuse-and-reload, retry by stable id. The Obsidian
  host spends several hundred lines on this race; the fence-plus-retry shape is the smaller
  alternative. The comments log has one writer, the host script, appending.
- **Rendered markdown versus offsets.** Mitigation: Raw is exact; Rendered maps through the
  lexer walk with per-token verification and refuses rather than mis-anchoring; the fallback
  painter reuses the whitespace-tolerant matcher in `ui/webview/comments.ts:86-162`; deletions
  are panel-only there; every change and comment has a card; a comment whose selection cannot be
  mapped offers Raw.
- **Raw direct edits desync changes before Slice 5.** Mitigation: the Edit refusal from Slice 1
  on.
- **Tracking off before a session writes.** Mitigation: folder tracking before the files exist,
  the Send to session checkbox that turns tracking on, and a guide paragraph saying to track the
  folder a session will write into.
- **Tracked folders that hold figures.** The guard would send an agent to `track-edit` on an
  image, which corrupts it. Mitigation: the non-text refusal lands in the vendored guard and
  `track-edit` in Slice 1, before folder tracking ships.
- **A figure path the client names** (Slice 3). `target.src` is a path the host resolves itself,
  and a reply hashes every src a sidecar holds. Mitigation, the bound Security posture states in
  full: decoded as the viewer decodes it, no URLs, realpath containment in the project root, regular
  files only, on a write the anchored passage must embed it and its extension must match the
  target's kind, 50 MB per figure on a write and one 200 MB budget per reply, and on a reply a null
  hash with its reason where a check fails. What the read yields is a hash, never bytes. The trade
  left open: a reply hashes an in-root file of any extension so a comment another writer left is
  not shown as unknown, which tells a client that can already edit the sidecar (the consent on)
  the sha256 of an in-root file the viewer would not serve it; refusing such srcs on a reply is the
  follow-up if that is judged worth withholding.
- **A file moved or renamed by the session.** The sidecar is keyed by path. This plan first said
  the store layer re-finds a moved file by content hash on load. The Slice 1 build (2026-09-06)
  found otherwise: `store-io` heals only when `healOrphanStore` is called explicitly (the VS Code
  host calls it; `loadStoreStatus` and the CLIs never do), and the host script does not call it,
  on purpose. A heal is a disk write: on `status` it would run outside the consent gate, and on
  a mutating verb it would make a sidecar appear under a `""` fence, refusing the very verb that
  caused it. So today a renamed file starts a fresh sidecar and the old one stays behind as an
  orphan; the comments log keeps the record either way (decision 27), and there is no rename UI.
  The follow-up option: heal on a mutating verb only, behind the consent, and let the
  fence-and-retry shape absorb the appearance (the verb refuses `store-moved` once, the client
  re-issues `status` and retries by id).
- **Author chips on a file a remote kernel owns.** `GET /sessions` lists only the local kernel's
  sessions and no `/remote/<host>/sessions` relay exists, so on such a file the panel cannot map a
  sidecar `authorId` to a session's name and color: those chips fall back to the neutral chip with
  the sidecar's own author label. The Send label still names the session, since that comes from
  the viewer's identity rather than the map (the Slice 1 build, 2026-09-06). A relay route is the
  fix if the chips matter on a remote file.
- **Ended session.** Its todo is hidden from Waiting on you and `_send_or_park` revives dormant
  sessions, not ended ones (`kernel.py:24047-24062, 12227-12234`). Mitigation: the guide note
  above; Send to session surfaces the refusal; the comments are already on disk.
- **Prerequisites on the owning kernel** (node on the kernel's PATH for the host script, the
  agent-side tooling linked for the session to reply). Mitigation: `no-node` and the
  agent-tooling warning are explicit verdicts surfaced in the gear and the panel; the action never
  appears broken. Node on the kernel's PATH under every service unit is unverified and is the
  first thing Slice 1 checks.
- **Tracking inheritance.** The CLIs treat notes reachable through whole-line links and embeds as
  tracked (`store-io.mjs:100-197`). Mitigation: the host script uses `isTrackedFile`, the same
  function as the guard, so verdicts agree by construction, and reports `inherited` so the panel
  can say so (decision 11: turning it off refuses with the parent named).
- **track-changents defects the loop can reach** (the 2026-09-03 survey). A1: `track-reply` or
  `track-edit --thread` into a comment the live sidecar lacks revives it from the `.superseded`
  park and overwrites the sidecar with an empty change list, erasing pending changes including the
  one `track-edit` just recorded. A2: `track-edit` and `track-comment` replace a corrupt or newer
  sidecar with a fresh one. A7: `--thread` can bind a comment to a change id that coalescing
  dropped. A10: `track-edit --thread` failures are silent. The host script avoids A1 and A2 in its
  own path; A1 is fixed in both vendored CLIs in Slice 1, since the agent's replies are the loop's
  step 8, and the fix is offered back. Skill drift C3 (the skill says `track-edit` refuses stale
  text; it usually detaches the displaced changes instead) is corrected in the vendored skill and
  offered back.
- **A session rebases its own branch** (the user 2026-09-06: romp sessions are allowed to). A
  rebase can rewrite a commented file under the open panel and, when `.trackchanges/` is
  committed, rewrites the sidecar and the comments log like any other file. The design tolerates
  it without new mechanism: the poll sees the new mtimes, changes rebase or detach and comment
  anchors relocate or show detached, every fence refuses a write against the pre-rebase state,
  the log is append-only, and a sidecar left with conflict markers reads as corrupt and is
  refused, never replaced. The implementing session decides how the panel words a conflicted
  sidecar and whether the guide tells sessions to resolve `.trackchanges/` conflicts by taking the
  branch that holds the newer comments; nothing here changes the plan's shape.
- **A PDF rendering dependency** (Slice 4). Mitigation: lazy chunk, size cap, frame fallback, and
  a slice of its own so the rest of the feature never waits on it.
- **Polling cost.** Two HEAD requests every 2.5 s per open panel, plus one per figure the file's
  open region comments name (Slice 3). Mitigation: only while the panel is open and the tab
  visible. The poll's state per file is one of absent, present with an
  mtime, or unknown with a status; it starts after the first `status` supplies the sidecar path,
  takes its baseline from every `fileCommentsResult` so the person's own writes never fire it, and
  treats a 404 as the value "absent" so absent-to-present is a transition like any other; a 413
  or 415 stops the poll on that file and shows the kernel's reason row.

## Tests

Synthetic fixtures only (the `notes-api` world, `TESTHOST`, placeholder ids).

- `tests/test_file_comments.py` (the `tests/test_savefile.py` hermetic pattern): path resolution,
  consent refusal before content checks, the vendored import path, `no-node` and the
  agent-tooling verdict, timeout and bad-stdout handling, `sid` routing, trace after reject and
  not after comment, the `log-edit` call after a save of a file with a sidecar, log, or tracked flag, not after a
  save of any other file, and not after a refused save, with `logged` in the `fileSaved` reply, the todo
  helper's branches (switch off, settled, ended, and the send arm's parked, sent, and refused
  outcomes, plus the handler's own unchanged behavior), message text for one and several comments
  and for `tracked` on and off, the `/defaults` verdict; `tests/test_injected_voice.py` gains the
  two new bodies.
- Host script conformance (node tests beside the script): a sidecar written by `track-comment`,
  replied to by the host script, read by `track-reply` keeps every field; the host script's
  sidecar path equals `storePathFor`; `v` stays 3 and the fingerprint matches; accept then
  `track-edit` succeeds; reject yields the engine's baseline for the subset and remaps survivors;
  rollback when the file write fails, including removal of a sidecar the verb created; fence
  refusals with `""` and with a stale value; nothing written on `v: 4` or unparseable JSON;
  `comment` with an ambiguous anchor refuses; a whole-file comment and a `target` comment
  round-trip through `store-io` unchanged; `set-tracked off` on an inherited file refuses; the
  comments log gains one entry per send, accept, reject, toggle, and edit, is never rewritten, and
  the unsent derivation from it matches the panel's; the vendored copy matches a present checkout
  (the drift test: pin plus patches, and a present checkout at or past the pin); the guard exits at
  once without `ROMP_SID` and passes a non-text file through. Slice 3, with figures generated as
  tiny PNGs at run time (`tools/file-comments-host-regions.test.mjs`, `-targets`, `-embeds`,
  `-plan-shape`, `-review-3`): the target's shape and unit-square check; the hash is the bytes', not
  the client's, and a `track-reply` into a region comment keeps it; containment of a relative and an
  absolute src in both directions; `figure-mismatch` before any hash; `too-large` on a write
  pinned with a sparse file, and a null hash with its reason on a reply; the decoded src; the
  src-less contract shape told from its passage, and its re-place; the figure fence:
  `figure-changed` on a standalone and on an embedded figure regenerated between the drag and
  Enter, nothing written and no landmark created, a malformed `figureHash` refused before any disk
  read, `too-large` before `figure-changed`. `tools/file-review-plan.test.mjs` pins what this plan
  states for the target's shape, the verbs, the fence, the codes, the caps, the read bound and the
  poll against the host, kernel and panel sources, so a change to either side without the other
  fails a test.
- `tests/install-sh.bats` gains the tooling links, the guard registration with its matcher,
  idempotency, the basename presence check against an expanded-path entry, and the
  replace-an-existing-install case (Slice 1).
- `ui/webview/file-comments.test.ts`: source pins (registry entry, both ops carry `sid`, one
  `delegate()` root, string mtime comparison, no client-computed sidecar path, keyed expand
  state), pure tests for the card model, the Raw and Rendered mapping walks over the fixtures
  named in the acceptance criteria, and the message builder against the kernel's text.
- `ui/webview/user-todo-links.test.ts` rewritten to pin `path-links.ts` and both callers
  (Slice 0); `editor-lazy.test.ts` extended for the typed `track` option (Slice 5) and for the
  PDF chunk staying lazy (Slice 4).

## Docs

`docs/guide.md`: "Reviewing a document" (`:29-45`) becomes a section on file comments and tracked
changes, states that quote chips remain for one-off notes, tells the user to track the folder a
session will write into, and to keep figures out of tracked folders until Slice 1's refusal is
in place; "Waiting on you" notes the linked path and the ended-session case; "Files"
(`:126-138`) gains the panel, the poll, the consent gate the guide omits today, commenting in
either view and on images and PDFs, the comments log and the `.gitignore` opt-out, and where to
look when the action is missing. `docs/reference.md`, under install-time switches, notes the
User todos switch as a prerequisite for the todo path and the node requirement on the owning
kernel; `docs/install.md` names the tooling the installer links into `~/.claude/`.
`claude/romp-session-prompt.md` gains its one sentence. `CONTEXT.md` already carries the
vocabulary; `docs/adr/0002` records the storage decision. In track-changents (its author): the
offers back named under Vendoring, and a README "Hosts" row.

## Deliberately not in v1

Git operations on any project (romp's git calls on session repos are read-only queries; whether
`.trackchanges/` is committed is the project's call); ingesting comments typed on GitHub; a
filesystem watcher or kernel push for the Files pane; a viewer or editor extension API; rendering
HTML files (the viewer serves them as source by design); text-quote anchors inside PDFs (the CLIs
cannot read a PDF's text, so PDF comments are whole-file or region); region drawing by touch on
the phone; changes authored by the person (their edits are direct edits, decision 23); the
Obsidian host's embed trees, explorer badges, status bar, multi-pane sync, and vault rename
re-keying; a scheduler for overnight work; changes to the Obsidian and VS Code hosts; inline
deletions in the Rendered view; undo of accept and reject before Slice 5; multi-file sends (one
send per file, decision 28).

## Dependencies

On the owning kernel: node on the kernel's PATH; the agent-side tooling linked into `~/.claude/`
by romp's `install.sh` from the vendored copy (decision 15); for changes to appear, the file's
path or folder listed in `config.json` before the session writes it; the User todos switch on for
the todo path to exist; the file-editing consent given once. Nothing blocks on track-changents'
author: the A1 fix, the non-text refusal, and the skill edits land in the vendored copy as
patches in Slice 1 and are offered back; the `target` field and the comments log are romp-only. For Slice 4,
the PDF rendering dependency.

## Decisions (the user, 2026-09-05 and 2026-09-06)

The user reviewed the first full draft on GitHub, the revision through the viewer's own quote
flow, and then answered a structured design interview. Every ruling is recorded here so the
document stands on its own, each with the reasoning it was given.

1. **Slice order and cadence.** All six slices are built in one push; the order in Build slices
   is the default landing order, and the implementing session decides staffing, with a dedicated
   new session suggested. The fork dispatch stays parked until asked for.
2. **Write path.** The node host script on the owning kernel, over track-changents' `store-io`
   and engine unchanged. A second implementation of a cross-tool contract is where shared files
   get corrupted.
3. **Where the host script lives.** In this fork, importing the vendored copy. The user intends
   to offer the whole feature upstream to romp eventually, so everything it needs is built into
   this repo first and offered to track-changents later.
4. **Vendoring.** Now, without waiting for track-changents to be public: the MIT core pinned to a
   commit under `vendor/track-changents/` (see Vendoring).
5. **Consent scope.** Every mutating verb, sidecar-only included, behind the one file-editing
   consent, with the popup's copy amended so it stays true for comments.
6. **Human author label.** `you`, so one person is one author across hosts; no `authorId`.
7. **Trace policy.** A trace after `reject`, `reject-all`, and `save`; nothing after sidecar-only
   verbs, since the sent message is the notification for comments.
8. **Send defaults.** All confirm checkboxes checked by default, each visible before the send.
9. **Per-comment sends.** Batch only.
10. **The unsent state.** Not browser-local. The user asked whether a browser crash could lose the
    comments. It could not, since comments and changes live in the sidecar on disk, but the send
    watermark would have been lost. The comments log holds it on the owning kernel, so no state
    lives in the browser.
11. **Turning tracking off on an inherited file.** Refuse with the parent named.
12. **PDF rendering.** The lazily loaded pdf.js chunk, with the browser's frame as the fallback.
13. **The region field.** Built romp-only for now; documenting it for the other hosts is a later
    offer, not a dependency. (The Slice 3 build stores a fifth key, `src`, on a figure embedded in a
    markdown file, and has the host resolve and hash the file it names; the offer documents the
    shape as built; see the contract's `target` bullet and Security posture.)
14. **The Slice 5 doctrine question.** Yes: a typed, internal `track` option in the editor chunk,
    with the header updated.
15. **Ship the agent-side tooling with romp.** Yes (2026-09-06): the four CLIs, the guard hook,
    and the skill are vendored with the core and linked by romp's installer, so a machine that
    runs romp runs the whole loop with nothing else installed; fixes land in the vendored copy
    and are offered back.
16. **The log's format.** JSON lines in `.trackchanges/`, rendered by the panel's Log section; a
    markdown export may follow if reading it on GitHub matters.
17. **The object is a file comment** (2026-09-06), never a thread: a comment on a passage, a
    region, or a whole file, kept with the file. The name also covers comments that have nothing
    to do with a review.
18. **"Change" is the user-facing word** for a session's pending edit; "suggestion" is the storage
    format's word and stays out of the UI.
19. **The plan merges first.** The implementing session merges this plan to main with the header
    changed, then begins, likely in a new session it creates.
20. **Plain delegation** to the implementing session; no report-back tie to the authoring
    session.
21. **One user todo at the end**, for the end-to-end walk, rather than one per slice.
22. **No "report" object.** The feature is rich commenting and editing of files in romp with easy
    communication back to the session; the overnight report is one use. No folder convention is
    imposed; the user tracks what they want tracked.
23. **Direct edits stay direct.** The person's own edits land at once and trace to the session;
    the person chooses between editing the text and commenting instructions.
24. **The guard is scoped to romp sessions by environment**: registered machine-wide, it exits at
    once when `ROMP_SID` is absent.
25. **Committing is the project's call.** romp writes the sidecar and the comments log and does
    no git operation; a `.gitignore` line is the opt-out.
26. **Phone**: reading and commenting work there; region drawing waits.
27. **Renames** rely on the store layer's content-hash healing; no rename UI, and the log keeps
    the record. (The Slice 1 build found that healing runs only when a host calls it, and the host
    script does not; see the rename bullet under Risks for the actual behavior and the follow-up.)
28. **One send per file**, sending everything unsent in it; a todo naming several files is
    answered by the first send.
29. **Done** means the per-slice criteria pass and the user completes the motivating loop end to
    end with no GitHub and no Obsidian.
30. **Compatibility stays, and gets an ADR.** The storage format is track-changents' unchanged,
    plus the romp-only log; the reasoning is recorded in `docs/adr/0002`.
31. **Names**: "Comments" for the action and panel, "Track changes" for the toggle, "Send to
    session" for the button, no mode concept.
32. **The log is the comments log** (not "history", which reads as git history), file suffix
    `.comments-log.jsonl`, panel section "Log".
33. **Direct edits are logged** too, so the log holds everything that happened to the file
    through romp.
34. **Whole-file comments on every file**, not only images and PDFs.
35. **Sessions learn the pattern from romp's default session prompt** and from the skill: name
    the file's absolute path in the todo's detail; ask for another look the same way.
36. **The three Send checkboxes** keep their generic wording: answer the todo; turn on tracking so
    the session's edits come back as changes; accept the N pending changes.

37. **A file with no repository or vault above it** (2026-09-06) gets `.trackchanges/` created
    beside it on the first comment or tracking toggle, and that folder is its project's root from
    then on; the loose-file case refuses nothing.
38. **One `.trackchanges/` per project, at its root** (2026-09-06), never one per directory: the
    nearest git repository, vault, or folder that already holds one is the project, and a loose
    file starts a project of its own. The tracked list, the comments of every file in the project,
    and the commit-or-ignore choice have one home; a file moved within the project keeps its
    comments; and the agent CLIs, the guard, and the other editors look in the same place.
39. **The gear row names the reason and the command; the one-click link step waits** (the Slice 1
    build, 2026-09-06). When the agent-side tooling is not linked on a machine, the File comments
    row says so, says that its sessions cannot reply until it is, and names the command to run
    (romp's `install.sh` on that machine); it does not offer to run it. Getting into it promised a
    button. Running the installer from the dashboard needs a kernel op that executes `install.sh`,
    and Security posture enumerates what the feature may write: the sidecar, the comments log,
    `config.json`, and the commented file. An installer run writes `~/.claude` and `settings.json`
    and is outside that list, so the button adds a server-side surface the posture does not name.
    It awaits the user's ruling; until then the row's sentence is the offer.

## Open questions for the user

None remain. Every question raised by this document, by its reviews, or in the design interview
has been ruled on; see Decisions.

## Upstream

The user intends to offer the whole feature upstream to romp eventually (the user 2026-09-05).
Vendoring the core and the agent-side tooling (decisions 4 and 15) makes the loop
self-contained, so the whole feature can be offered as one; Slice 0 is also a candidate row on
its own. The offer decisions belong to the offer flow, not this plan.
