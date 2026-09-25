# Security

romp runs a local kernel and a local message bus on your machine, and drives
Claude Code sessions on your behalf. This document states the trust model it
assumes, what that means on a shared machine, and how to report a vulnerability.

## Trust model: token-gated, same-user by file permission

Two local services run on your machine:

- the **kernel** (dashboard/API) on `127.0.0.1:29855`, and
- the **postal bus** (inter-session messaging) on `127.0.0.1` (a fixed local port).

Both bind **loopback only** (`127.0.0.1`); neither is exposed to your network by
default. On top of that, **every request requires the serve token, loopback
included**, presented either directly or through a browser sign-in made with it
(below). This is the model Jupyter uses, for the same reason: loopback is one
network stack shared by every local UID, so it cannot be a trust boundary by
itself.

The token (`~/.local/state/romp/serve-token`) is 144-bit random, stored at mode
`0600`, and compared in constant time: **file permissions are the same-user
gate**. Same-user clients (the CLI, hooks, the bus, the manager, the VS Code
extension) read the file and send it as an `X-Romp-Token` header, or as
`?token=` in the URL (the extension's WebSocket and the requests its webview
makes); an attached machine presents the other machine's token the same way. A
token presented explicitly, as `?token=` or `X-Romp-Token`, is accepted from any
Origin: federated (cross-machine) calls need it, and a cross-site page cannot
obtain it: a browser sign-in stores no copy of it in the browser (below), the
dashboard drops `?token=` and the one-time code from its address as it signs
in, and every page the kernel serves carries `Referrer-Policy: same-origin`, so
the token never reaches another origin in a `Referer`.

The practical consequence: another local user on a **shared machine** cannot
reach your kernel or bus. `/send` (which injects text into a live Claude
session that runs tools as you) and bus mail both require the token only your
UID can read, or a browser sign-in made with it.

### Browser sign-in: a session cookie, a page key, per-file capabilities

A browser presents the token once, in one of three ways: the link `romp url`
prints, the sign-in page (`/login`, which a bare open of the dashboard also
shows) with the token pasted in, or a window `romp` opens, which carries a
one-time code in place of the token. That page load signs the browser in and
gives it three kinds of value, each derived from the serve token by HMAC under
a fixed label of its own:

- A **session cookie**. It holds a random session id and an HMAC tag over it,
  is `HttpOnly` and `SameSite=Lax`, lasts a year, and is named for this kernel,
  so two kernels on one host keep separate sessions. On its own it opens only
  the page documents (the dashboard shell and its pane pages) and the static
  files (`/dist/`, `/media/` and `/sw.js`), which hold code, one setting
  (whether task tracking is on), and no session data.
- A **page key**. The sign-in response writes it into this origin's local
  storage; that response is served with `Cache-Control: no-store`, and no other
  response carries the key. The pages send it as an `X-Romp-Key` header (a
  wrapper around `fetch` adds it to requests for the page's own origin only)
  and as `k=` when they open a WebSocket. Every request outside the page
  documents and static files (every JSON read, every POST, the WebSockets and
  every other route) needs the session cookie and the page key together, or,
  for a file, the cookie and that file's capability.
- A **file capability** in each `/file` or `/remote/<host>/file` URL a page
  builds: images, previews, PDF frames, a file opened in its own tab,
  downloads, and the `/file` pictures and links in rendered markdown. These
  loads cannot carry a header. A capability is an HMAC under the page key over
  one host, one path and one session id, as the kernel reads them from the URL
  (percent-decoded), so a spelling of the same file whose decoded path differs
  (a trailing slash, a dot segment, a symlink to it) needs its own. A
  capability is refused on a URL that names the path, the session id or the
  capability twice, and it is honoured for `GET` and `HEAD` only, and only with
  the session cookie of the sign-in that made it.

Because each kind has its own label, a value of one kind is refused wherever
another is required, the serve token included, and the kernel keeps no store of
sign-ins. The session cookie is honoured only when the request's Origin is one
the gate accepts: the dashboard's own origin (the `Host` the request arrived
at, or the kernel's own port on `127.0.0.1` or `localhost`), any
`vscode-webview://` origin (every VS Code webview, not only romp's own), or no
`Origin` header at all, which a same-origin navigation and non-browser clients
send; the WebSocket upgrade is checked the same way. A page whose stored key
no longer matches its session (two sign-ins that overlapped, or storage cleared
while the tab was open) gets a refusal of its own and moves to the sign-in
page, as does a page whose origin holds no key.

When the dashboard shows an attached machine through this kernel
(`/remote/<host>/...`), this kernel checks the browser's sign-in and calls the
other machine with that machine's own token. It forwards none of the browser's
cookie, page key or capabilities, and a relayed WebSocket handshake reaches the
browser with its handshake headers only.

The hold behind `/busy?drain=1` arms only for an explicitly presented token (a
request without one still gets the count and arms nothing): while a `romp
refresh --quiet` waits for the sessions to finish their turns, that hold keeps
every session from starting a new turn, a side effect no subresource load may
trigger.

The token-exempt routes are the no-side-effect liveness probes (`/healthz`,
`/version` and `/busy` on the kernel, `/ping` on the bus), the sign-in page
(`/login`, a static form that reads no state), the push worker's
acknowledgement (`POST /push/ack`, admitted only by the push's own unguessable
id: it records that push's delivery, marks the same device's older unanswered
notifications for that session as replaced, and fills in the device's origin
when it is missing) and the install files:
`/manifest.webmanifest` and the three home-screen icons under `/media/`
(`romp-touch-180.png`, `romp-app-192.png`, `romp-app-512.png`, a fixed allowlist
of names, not a path prefix). A browser fetches those with credentials omitted
when the dashboard is added to a home screen, so a token gate there would break
the install. They are static and read no session state: the manifest is a
fixed JSON literal (app name and short name, display mode, colors, start URL
and icon list) and the icons are three PNG files.

### What a browser sign-in costs, and how it ends

- **Losing the page key signs a browser out.** The key lives in the site's
  storage, which a browser can lose while it keeps the cookie: cleared site
  data, a private window, a browser that clears a site's storage after a week
  without a visit, or an app added to the Home Screen, which keeps storage of
  its own and so may ask for the token once after it is installed. That browser
  signs in again with the token: paste it on the sign-in page, open the link
  `romp url` prints, or run `romp` on the machine to open a signed-in window;
  an app on the Home Screen signs in by pasting the token. Earlier versions
  kept a browser signed in on the cookie alone for a year.
- **A sign-in lasts until the serve token is rotated.** Signing in again in a
  browser that still holds its cookie keeps its session, and with it the
  capabilities already in its URLs, and a new session ends no earlier one.
  Sessions, page keys and capabilities all end when the token is rotated, which
  signs every browser out at once. There is no per-browser sign-out.
- **An address with a capability reads that one file.** A file opened in its
  own tab, a download in the browser's history and a copied image address carry
  their capability; with the session cookie of the same sign-in, it reads that
  file until the token is rotated. It can also read a pinned copy of a picture
  that a message showed (`pin=`), which is named by the SHA-256 of its content,
  so only someone who already has that content can name it.
- **Whatever records a browser's request headers holds its sign-in.** A proxy
  you place between the browser and the kernel that logs headers records the
  session cookie and the page key together, which is a whole sign-in; trust it
  as you trust the browser.
- **Rendered markdown keeps its `/file` pictures and links.** The chat, notice
  cards, a preview provider's HTML, a markdown file's hover preview and the
  file viewer add a capability to each `/file` URL an author wrote, after
  sanitizing, and so do the places that turn typed text into links (a todo's
  or a note's text, a todo's link, a code span holding one address). A message
  can therefore show, or offer for download, any file the kernel's `/file`
  route serves this browser, as it could before; the bytes go only to this
  browser. Pictures that an SVG or a stylesheet names with `url()` get no
  capability, so a `/file` URL there draws nothing.

### Upgrading from a version whose cookie held the token

Before the session cookie, the dashboard kept the serve token itself in a
cookie named `romp_token`. The first dashboard page a browser loads after the
upgrade signs it in and clears `romp_token` in that same response, and any
later response to a request that still carries `romp_token` beside a valid
session cookie clears it as well. Either way the kernel clears `romp_token`
only when its value is this kernel's token, so a `romp_token` that belongs to
another romp kernel on the same host is left alone. A response to a request
without a valid session cookie never clears it, so a browser that has not yet
signed in with it keeps it until it does. Every browser that signs
in this way gets the same session, so tabs that reopen together after the
upgrade all end signed in; each of those browsers held the serve token itself,
and the session ends, like every session, when the token is rotated. A
dashboard left open across the upgrade keeps running the page it loaded
before, which has no page key: its requests are refused and its sockets keep
redialling until it is reloaded, so reload each open dashboard once the kernel
has restarted. A browser that never loads the dashboard again keeps
`romp_token`, whose value is the serve token and stays valid until the token is
rotated. Rotate the token after upgrading to retire every such cookie. The
steps, and what a rotation signs out, are under "Rotating the token" in the
guide's Security and trust section (`docs/guide.md`). Going back to an earlier
version signs browsers in with `romp_token` again, so pair a rollback with a
rotation once this version is back.

## Residual cautions on shared machines

- The token gate protects against other **non-root users**. Root (or the host
  operator of a container/VM) can read any file and inspect any process — no
  userspace design changes that. Don't keep long-lived credentials on hosts
  whose root you don't trust.
- **Do not** set `ROMP_SERVE_HOST` to `0.0.0.0` or a LAN address on an untrusted
  network — the token still gates every request, but it widens the surface; use
  an ssh tunnel or `tailscale serve` instead, which keep the listener on
  loopback.
- For defense-in-depth on Linux you can still run romp inside a per-user
  **network namespace** (`unshare -n`) or rootless container, so its loopback is
  not even reachable by other users' processes.

## What is already hardened

- **Loopback-only binds** for the kernel and bus (above).
- **Serve token required on every request, loopback included**, directly or
  through a browser sign-in made with it: 144-bit random, stored `0600`,
  constant-time compare. A browser's session cookie opens only the page
  documents and static files; every other request needs its page key or a
  per-file capability as well, and the cookie is honoured only from an accepted
  Origin, the WS upgrade included. Federated (cross-machine) calls authorize
  with the remote machine's token, carried over ssh tunnels the local machine
  initiates.
- **Path-traversal guards** on every id/name/message-id that becomes a filesystem
  path component under the mail and outbox roots (`_safe_id`), so a crafted
  reference like `../../etc` is rejected before any path join.
- **No shell interpolation:** subprocess calls use argv lists (no `shell=True`);
  remote `ssh` targets are validated and argv-guarded with `--`.
- **Output sanitization:** model output and message content rendered in the
  dashboard/webview pass through DOMPurify; the VS Code webview runs under a
  strict nonce CSP with `localResourceRoots` limited to the extension's assets.
  The profile is modelled on the rules GitHub applies to a README
  (`ui/webview/md-sanitize.ts`, shared by the chat and the file viewer): no
  `<style>`, no form controls, no image map, ids and names prefixed
  `user-content-`, an inline `style` reduced to its color declarations, no
  `background` attribute; unlike GitHub it keeps that color-only inline `style`
  and inline SVG. One renderer writes into that sanitized DOM after DOMPurify
  has run: KaTeX. The sanitizer keeps only color in an inline `style`, and
  KaTeX's layout is inline style, so a formula's TeX passes through DOMPurify
  as the text of an inert placeholder and KaTeX renders it there afterwards,
  under `trust: false` (KaTeX's own safety model: no TeX command writes a link,
  an image, or an HTML attribute of the author's choosing), with a cap on the
  sizes a formula asks for, a per-formula cap on macro expansion, and length
  caps on one formula and on one message or note; a formula over a length or
  expansion cap is shown as its source, and a size over its cap is clamped.
  That boundary is checked against the code by
  `ui/webview/md-sanitize-postpass-browser.test.ts`; the profile, as the browser
  lays a file out, by `ui/webview/md-sanitize-browser.test.ts`. The bounds are
  stated under "Slice 1" in `plans/markdown-viewer.md` and checked against the
  code by `ui/webview/render-math.test.ts` and
  `ui/webview/md-sanitize-postpass-browser.test.ts`.
  While the **Comments** panel is open, pdf.js parses a PDF in a Worker on the
  dashboard's origin and paints each page onto a canvas, with pixels as its
  only sink: no text layer, annotation layer, form field, link, or script from
  the file reaches the DOM. That puts a PDF beside the untrusted files the
  viewer already renders on this origin (markdown through marked and
  DOMPurify, source through highlight.js); with the panel closed a PDF opens
  in the browser's own viewer, as before. The properties that limit this
  (pdf.js is handed bytes, never a URL, so it fetches nothing; the installed
  build has no eval path; only its core is bundled; a size cap and a page cap;
  the browser's viewer as the fallback) are stated under "Security posture" in
  `plans/file-review.md` and checked against the code by
  `ui/webview/file-review-posture.test.ts`.
- **No unsafe deserialization:** no `pickle`, `eval`, `exec`, or non-safe YAML on
  untrusted data.

## Federated messaging: per-host trust

romp can attach other machines so their sessions appear in one dashboard and can
exchange postal messages with yours. Because a message that lands in an agent's
context is a prompt-injection surface, **each attached host carries a trust
level** you set in the network popover (persisted per host):

- **trusted** — full two-way postal, no gating. For a machine you control (your
  laptop, your home server).
- **directed** (the **default** for a newly attached host) — you can send work
  *to* that host's sessions, but its mail to you is **held for approval**, never
  auto-injected. Each held message appears as a needs-you card ("incoming postal
  message from X to Y") with **Approve** (deliver), **Edit** (change the text
  first), and **Deny** (drop) — a human decides before any of that host's content
  reaches one of your agents. This is the safe posture for rented/shared compute
  (a cloud VM, a RunPod box): you can drive it, it cannot drive you.
- **isolated** — no postal at all in either direction; the host's sessions are
  visible in the dashboard but its bus never peers with yours.

The trust unit is the **machine**, not a session on it: any process on a remote
box can write to that box's bus, so trust is set per host. Identity is provided
by the ssh tunnel the message arrives on — no separate signing. The gate is
enforced at the receiving bus's delivery point, so it holds regardless of which
host originated the message.

A **forwarded** message is judged by the more restrictive of two tiers: the
origin's and the forwarding host's. The origin stamp is written by the forwarder
and nothing signs it, so trusting it alone would let any peer claim to speak for
a host you tiered `trusted` and have its mail auto-injected — a `directed` host
could promote itself simply by labelling its cargo. Capping at the forwarder's
own tier means a directed relay stays directed whatever name it stamps, at the
cost that mail from a trusted origin relayed through a directed hub is held for
approval rather than delivered.

The one thing romp can NOT firewall this way is same-machine peers: two sessions
running as the same user share a UID, so mailbox trust between them is policy,
not a security boundary (the enforceable lines are per-UID, from the serve token,
and per-machine, from this trust level).

## Network access

romp makes one outbound request by default: it fetches a public model-pricing
table (`raw.githubusercontent.com/.../model_prices_and_context_window.json`)
every few hours to label context/cost. The response is parsed strictly as
numeric pricing. No telemetry or session data is sent anywhere.

## Reporting a vulnerability

Please report security issues privately via GitHub Security Advisories on the
repository rather than opening a public issue. Include a description, affected
version/commit, and a reproduction if you have one.
