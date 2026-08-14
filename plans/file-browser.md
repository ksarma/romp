# A file browser for the dashboard

**Status: SHIPPED** — both slices landed 2026-08-14: the read-only browser as fork PR #67 and
the raw-mode edits as PR #70, each hardened by an adversarial review pass before merging
(eight confirmed defects fixed on slice 1, nine on slice 2 — several of the latter data-loss
paths: the in-flight-typing ack loss, latin-1 re-encoding with an executed repro, the
whole-second mtime guard). The reviews changed real design details versus this plan: the
overlay stack became strictly one-directional (opening the browser closes an open viewer),
the conflict anchor moved from Last-Modified seconds to a string-typed `X-Romp-Mtime-Ns`,
Edit gates on a `X-Romp-Text-Utf8` verdict, and CRLF files round-trip via dominant-EOL
restore. This doc records the design as commissioned (the user 2026-08-14, who asked for the
UX to be thought through first) plus the four decisions that resolved its open questions;
file:line references describe the repo at v0.11.0-merge time (`main` = `c032e815`).

## The gap

Today the dashboard can *show* any file but cannot *find* one. The file viewer
(`ui/webview/file-view.ts`) opens in the feed pane with highlighting, rendered markdown, wrap,
and Download — but only from a path someone else surfaced: a chat path-link
(`render.ts:683` → the shell relay → `openFileView`) or a feed card's artifact chip
(`feed.ts:2275`). If the user wants to look around a session's repo — inspect a file no agent
mentioned, check what a directory contains — there is no surface for it. The nearest thing,
the new-session picker's directory autocomplete (`dirComplete` → `_dir_completions`,
`kernel/kernel.py:4284`), deliberately lists directories only, caps at 50, and answers
keystrokes in one input field.

## Shape of the feature

A **browser overlay in the feed pane**, sibling to the file viewer: a breadcrumb bar over a
flat entry listing. Click a directory to descend, click a file to open it in the existing
viewer, walk up via the breadcrumb. It starts at a session's working directory and can walk
anywhere from there.

Three deliberate structural choices, each following an existing precedent:

1. **It rides the feed pane, exactly as the viewer does** (`#romp-fileview`'s fixed-inset
   pane-local overlay, `feed.css:1083`) — NOT a shell-lifted dashboard-wide modal. The modal
   rule (`ui/CLAUDE.md`) governs panels that present over the dashboard as a whole; the
   viewer's pane-takeover is the blessed pattern for file content, and staying pane-local
   sidesteps the lift's four documented pixel-level failure forms entirely. On a phone the
   viewer's existing bridge already turns this into a tab switch for free.

2. **The listing is a WebSocket op, not a new HTTP route.** The op pair
   `dirComplete`→`dirCompletions` (`kernel.py:24591`) is the template: client-minted `reqId`
   echoed back (stale replies dropped), `host` field routed by `federation.ts:189`'s
   `routeOutbound` and answered by the session-owning kernel over the existing `_remote_ws`
   byte splice — so **browsing a remote session's disk works with zero new relay code**. A new
   HTTP route would need its own `/remote/<host>/…` relay clause, and the relay's own comment
   says `/file`-only is deliberate. File *bytes* stay on HTTP `/file` (streamed, HEAD-probeable,
   cacheable); only the listing JSON rides the socket.

3. **Files open through the viewer that already exists.** A file row calls the same
   `openFileView(path, sid)` the artifact chips call; the viewer already speaks federation
   (`fileUrl`, `preview.ts:62`), presents 413/415 with a Download way out, and persists format
   preferences.

## Kernel: the `listDir` op

Request `{type:"listDir", path, sid?, reqId, host?, hidden?}`; reply:

```
{type:"dirListing", reqId, host, base, parent,          // base+parent ~-collapsed; parent null at /
 entries:[{name, isDir, isLink, size, mtime, viewable}], // dirs first, then case-insensitive by name
 truncated}                                              // or {…, error} — loud, naming the resolved path
```

- **Path resolution is `_resolve_open_path` semantics** (`kernel.py:18628`): `~` expanded,
  a relative path resolved against the sid's session cwd. This matches `/file`, so a listed
  entry's path can be handed to `fileUrl` unchanged. It is deliberately NOT `_expand_dir`
  (the picker's default-dir-relative resolution) — two resolution semantics exist and the
  browser must not mint a third or mix the two.
- **A new sibling helper, not a widened `_dir_completions`.** The completer's semantics
  (dirs-only, 50-row cap, dot-fragment-gated hidden entries) are picker behavior pinned by
  `tests/test_new_session_dir.py` and `dir-complete.test.ts`; the browser needs files, sizes,
  mtimes, an explicit hidden toggle. Same construction discipline: `os.scandir`, OSError →
  loud error (never a silent empty), `_tilde` on everything user-visible.
- **`viewable` is computed server-side** from the same `_PREVIEW_MIME` + `_is_text_path`
  tables `/file` uses, so the UI can signal up front which rows will render and which will
  only download — rather than letting every `.parquet` click fail into a 415.
- **Cap 500 entries + `truncated: true`**, stated in the UI (no silent caps). One JSON frame,
  capped server-side — never streamed listings over the socket.
- **Hidden entries default OFF**, toggled explicitly (`hidden: true`); symlinks are shown and
  marked (`isLink`), with `is_dir()` following them for typing, matching the completer.
- **Errors name the resolved path** (`_file_preview`'s convention, `kernel.py:23126`): an
  unreadable or vanished directory returns `{error: "cannot list ~/x/y: <why>"}` — the fail-loudly
  rule; the client renders it, never a blank.

### The remote-text relay fix (independent, and a bug today)

`/remote/<host>/file`'s view gate predates the text half of `/file`: it 404s any
non-`_PREVIEW_MIME` extension before dialing the remote (`kernel.py:24820`), so a **remote
session's `.py`/`.md` already fails to view in today's viewer** — and because it's a 404, not
a 415, the viewer offers no Download. The fix: widen the relay's local gate to also pass
`_is_text_path`, keeping the security shape intact — the Content-Type is still derived
LOCALLY (`text/plain` + nosniff never executes, so the lying-remote/iframe rationale at
`kernel.py:24798` is preserved) and the remote's own caps/sniff still apply at its end.
This lands as its own commit with `tests/test_kernel_remote_file_relay.py` updates, fixes the
existing viewer, and is upstream-relevant on its own (upstream ships the same gate).

## UX

### The surface

```
┌──────────────────────────────────────────────────────────┐
│ ~ / code / notes-api / ⌂src∕            [·hidden] [✕]    │  ← breadcrumb bar
├──────────────────────────────────────────────────────────┤
│ ▸ handlers/                                              │
│ ▸ models/                                                │
│   README.md                                     2.1 KB   │
│   app.py                                        14 KB    │
│   data.parquet                    ⤓ download only 91 MB  │  ← dimmed, honest
│   (empty dirs say "empty directory", never a blank)      │
└──────────────────────────────────────────────────────────┘
```

- **Compact rows, one line each** (progressive disclosure): a dir marker or nothing, the
  name, a right-aligned size on files. No mtime column by default — the one-line version
  carries what a glance needs; mtime goes in the row's hover title with the full path.
- **One interaction verb: click.** Directory → descend. Viewable file → `openFileView`.
  Non-viewable file → rows are dimmed with a `⤓ download only` tail; the click downloads
  directly (the same `fileUrl(path, sid) + "&download=1"` transient-anchor idiom the viewer's
  Download button uses) rather than opening a viewer that could only apologize.
- **Breadcrumb = the up affordance.** Every ancestor segment is clickable; the root renders
  `~`-collapsed. The breadcrumb is also how the user escapes a listing error (the error pane
  keeps the bar, so there is never a dead end).
- **Truncation is stated in-band**: a final dim row "500 of 1,842 entries — the rest aren't
  shown" when `truncated`.
- **Menu vocabulary for the one deeper level**: a right-click on a row offers Copy path /
  Download / Open folder (the existing `data-act="openFolder"` body delegate,
  `render.ts:10023`), in the standard `.ctx-menu` skin. That's the mechanics-one-click-away
  layer; v1 needs nothing more.

### Getting into it

- **Chat tab right-click menu** (`showTabMenu`, `render.ts:3913`): a "Browse files" row.
  The chat knows the session's fixed cwd (`s.cwd`, `render.ts:216`). It posts
  `{romp:'browseFiles', path, sid}` to the shell, which handles it exactly like
  `{romp:'viewFile'}` (`kernel.py:21120`): force the feed pane on (remember via the same
  `__rompFeedWasOff`), switch the mobile tab, forward into the feed iframe.
- **Feed card right-click menu** (`showCardMenu`, `feed.ts:749`, today only the notify
  toggle): "Browse files" sending only the sid — the feed payload doesn't carry cwd, and the
  kernel resolves it authoritatively (`_cwd_of`); the client never scrapes it from another
  pane (authoritative-source rule).
- **From the viewer itself**: the title bar's directory segment (`.fileview-dir`) becomes
  clickable — "browse this file's folder." This is the discoverability path: anyone who has
  ever opened a file link learns the browser exists by hovering the path they're already
  looking at.
- The statusline's 📁 keeps its current OS-open behavior (changing it is a separate
  decision — see open questions).

### Browser ↔ viewer: the navigation stack

The viewer is a replace-never-stack singleton, and its every close posts `viewFileClosed`,
which makes the shell restore a feed pane it had auto-enabled (`kernel.py:21125`). Unmanaged,
that contract fights the browser: open browser → open file → close file would collapse the
whole surface and could flip the pane off while the browser is still up.

Design: **the browser sits beneath the viewer and the close contract becomes ownership-aware.**

- The browser is its own singleton (`#romp-filebrowse`, z-index below the viewer's 900).
  Opening a file overlays the viewer on top; the listing persists beneath, untouched.
- `tellShellClosed` (`file-view.ts:106`) posts `viewFileClosed` **only when no browser is
  open beneath** (`document.getElementById("romp-filebrowse")` — the same existence-keyed
  idiom the viewer's own Escape handler uses). Closing the file returns to the listing;
  closing the browser does the pane restore (it posts its own `browseClosed`, and the shell
  treats both messages identically).
- **Escape closes the topmost surface only**: the viewer's document-level handler already
  keys on `#romp-fileview` existing; the browser's handler additionally requires the viewer
  NOT to exist. (The pane-local Escape consumers stay independent of the shell's hardcoded
  modal chain in `_LANDING_ESC_JS`, which governs shell-native panels only.)
- Keyboard in the listing: ↑/↓ move a roving selection, Enter opens it, Backspace or ← walks
  up one directory, Escape closes. (The completer's `-1`-in-the-cycle trick is for a menu
  attached to an input; a plain roving selection is right here.)

### Waiting, staleness, click-safety

- **Loader first** (`ui/CLAUDE.md`): the romp swirl + wordmark + dots over the listing body
  during any in-flight `listDir` — event-hidden when the reply lands, failsafe timeout,
  re-shown on `romp:wsdown`. A slow remote scandir shows the loader, not a frozen list.
- **Staleness protocol copied from the completer** (`render.ts:4585`): replies dropped on
  `reqId` or `host` mismatch; no debounce — one in-flight request with newest-value
  coalescing ("the pacing is the round-trip itself — an event, not a timer").
- **Rows delegate to one stable root** (`actions.ts` `delegate()` on the listing container,
  `data-act` + `data-path` rows) with `flash()` acknowledgement — the browser re-renders its
  list on every navigation, so per-row listeners are exactly the destroyed-mid-click bug the
  rule exists for.
- **No auto-refresh.** The listing re-fetches on navigation and on an explicit refresh
  gesture (breadcrumb re-click). A filesystem watcher is a time-vs-event question v1 does not
  need to answer.

### VS Code

`canPreview()` is false in the webview (`preview.ts:27` — the webview origin can't reach the
kernel), and VS Code has its own explorer; every existing affordance there falls back to
`{type:'openFile'}` → the editor. V1: the browse menu rows simply don't render in the webview
(same `canPreview()` gate the artifact chips use). An honest absence beats a dead pane.

## Editing in raw mode (the user's ask, 2026-08-14 — designed here, recommended as the second slice)

The viewer's raw mode grows an **Edit** affordance: view a text file, click Edit, change it,
save. Considered fully because half-designed write paths are how data gets lost; recommended
to land as its own slice after the read-only browser, because its risk surface (conflicts,
dirty buffers) is disjoint from navigation and shouldn't hold the browse loop hostage.

- **Scope: exactly what raw mode can show.** Editable = `_is_text_path` files within
  `_TEXT_MAX_BYTES`, already loaded in the raw view. No binary editing, no create/rename/
  delete, no size exceptions. Rendered markdown must switch to Raw to edit — the natural
  gesture, since what you edit is what raw shows.
- **The editor is a plain textarea** (mono, the raw view's own font), not an embedded editor
  component. Syntax-highlighted live editing means adopting a real editor dependency; that is
  a different project. V1.1 honesty: a textarea that holds your changes beats a half-editor.
- **Save is a WS op, `saveFile {path, sid, content, baseMtime, reqId}`** → `{type:"fileSaved",
  reqId, mtime}` or a loud error. WS for the same reason as `listDir`: federation rides the
  splice free (the `dropFile` attachment path already ships file bytes over the socket, so the
  precedent exists); the 2 MB text cap bounds the frame. The kernel writes atomically
  (temp file + `os.replace` in the same directory, mode preserved).
- **Optimistic concurrency, refuse-and-say-so.** Agents actively edit these same trees — a
  silent last-writer-wins would eat an agent's concurrent change or the user's. The viewer
  records the file's mtime at load (`/file` gains a `Last-Modified` header; the listing
  already carries mtime); save sends it as `baseMtime`; the kernel refuses when the disk is
  newer: "changed on disk since you opened it." The refusal keeps the user's buffer intact
  and offers Reload (fetch fresh, buffer preserved alongside) — never a merge UI, never a
  silent overwrite. This is the fail-loudly rule applied to writes.
- **Dirty-buffer guards on every exit**: Escape, ✕, breadcrumb navigation, and the
  markdown-mode toggle all confirm before discarding unsaved changes (pane-local confirm, per
  the modal rule's small-dialog carve-out). Save disables + relabels "Saving…" immediately
  (the click-acknowledge rule), then re-renders the highlighted view from the saved content.
- **Security: the same trust model, but say it plainly.** The dashboard owner can already
  write any file by asking an agent to; this makes the write direct. It stays behind
  `_authorize` like every op, is a distinct message type (greppable, auditable, refusable in
  one place), and follows the same no-path-jail stance as reads. It is still a genuine
  widening of what a leaked token can do — the plan calls that out rather than burying it,
  and it is part of why edits sequence second rather than shipping inside the browse slice.
- **Tests**: mtime-conflict refusal (the concurrent-agent case), atomic-write (no partial
  file on a full disk — write-to-temp proves it), dirty-guard pins, the Last-Modified header,
  federation save-to-owning-host, and the cap/binary refusals. Synthetic paths only.

## Security posture

Unchanged, and stated rather than silently widened: the listing op sits behind `_authorize`
like every WS message (never in the auth-exempt block — the `/version` lesson), and
enumeration grants the authenticated dashboard owner nothing an agent they run couldn't
already do. The view allowlists remain a rendering choice, not a boundary
(`kernel.py:18532`, the user's 2026-08-09 download ruling); there is deliberately no path
jail, and the dashboard's exposure model (tailnet, phone) is the same one `/file` already
lives with.

## Tests (land with the change, per the standing rule)

- `tests/test_listdir.py`: reply shape, sid-relative resolution, hidden toggle, the 500-cap +
  `truncated`, dirs-first ordering, `viewable` correctness against `_TEXT_EXT`/`_PREVIEW_MIME`,
  loud error body naming the resolved path, symlink marking. Synthetic paths only
  (`notes-api` world, `TESTHOST`).
- `tests/test_kernel_remote_file_relay.py`: the text-widening updates (`.py` relays as
  locally-typed `text/plain`; the lying-remote Content-Type test unchanged).
- `ui/webview/filebrowse.test.ts`: source pins for the overlay contract (singleton, z-order
  under the viewer, `browseClosed`/suppressed `viewFileClosed` ownership rule, Escape
  topmost-only), the delegate root, the loader, the truncation row, the dimmed
  download-only rows.
- `file-view.test.ts` gains the ownership-aware `tellShellClosed` pin; the shell-relay pins
  extend to `{romp:'browseFiles'}`.

## Deliberately not in v1

Search/filter, file operations beyond the designed raw-mode edit (no rename, delete, create,
or upload), a tree view (flat listing + breadcrumb is the compact form; a tree is mechanics),
sort controls, pagination past the stated cap, mtime columns, git-status decoration,
filesystem watching, and a shell-rail session-free entry point. Each is a coherent later
layer; none blocks the core loop of *navigate → glance → open*. The raw-mode edit is designed
above and recommended as the slice immediately after.

## Open questions for the user

1. **The statusline 📁**: today it OS-opens the folder on the *kernel's* machine — the wrong
   machine whenever the dashboard is read remotely (the same class as the old `openFile` bug).
   Should it open the browser instead, with OS-open demoted to the row's context menu? V1
   keeps it unchanged pending this call.
2. **A session-free entry point** (browse from the shell rail, starting at the default dir):
   wanted in v1, or is session-anchored + walk-anywhere enough?
3. **Edit sequencing**: the raw-mode edit is designed above; the recommendation is
   read-only browser first, edits as the immediate next slice. Fine, or should they ship
   together?

## Upstream

Pure feature, no fork-specific content: on landing, two candidate rows — the browser itself,
and the relay text-view fix (a standalone bug upstream shares). The offer decisions belong to
the offer flow, not this plan.
