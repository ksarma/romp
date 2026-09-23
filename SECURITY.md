# Security

romp runs a local kernel and a local message bus on your machine, and drives
Claude Code sessions on your behalf. This document states the trust model it
assumes, what that means on a shared machine, and how to report a vulnerability.

## Trust model: token-gated, same-user by file permission

Two local services run on your machine:

- the **kernel** (dashboard/API) on `127.0.0.1:29855`, and
- the **postal bus** (inter-session messaging) on `127.0.0.1` (a fixed local port).

Both bind **loopback only** (`127.0.0.1`); neither is exposed to your network by
default. On top of that, **every request requires the serve token — loopback
included** (the model Jupyter uses, for the same reason: loopback is one network
stack shared by every local UID, so it cannot be a trust boundary by itself).

The token (`~/.local/state/romp/serve-token`) is 144-bit random, stored at mode
`0600`, and compared with a constant-time check — **file permissions are the
same-user gate**. Same-user clients (the CLI, hooks, the bus, the VS Code
extension) read the file and send it as an `X-Romp-Token` header; the browser
presents it once as `?token=` (print the ready-made link with `romp url`, or
paste the token into the login page a bare open of the dashboard serves) and
rides an `HttpOnly` cookie afterwards. That cookie authorizes only when the
request's Origin is one the gate accepts: the dashboard's own origin (the
`Host` the request arrived at, or the kernel's own port on `127.0.0.1` or
`localhost`), any `vscode-webview://` origin (every VS Code webview, not
only romp's own), or no `Origin` header at all. The check protects the
browser surfaces, the WebSocket upgrade included, against cross-site
requests. It is needed because cookies are scoped by host and
**not by port** (RFC 6265 §8.5): every `http://127.0.0.1:<port>` page on your
machine is same-site with the dashboard, so anything else you run on loopback
(a dev server in a repo an agent cloned) would otherwise ride your cookie into
`/ws`, which streams every session and accepts text to send into any of them. A
request with no `Origin` header passes on its cookie because a same-origin
navigation and non-browser clients send none; a page on another loopback port
loading an `<img>` aimed at the kernel sends none either and still carries the
cookie, which is why the hold behind `/busy?drain=1` arms only for an
explicitly presented token (a request without one still gets the count and arms
nothing): while a `romp refresh --quiet` waits for the sessions to finish their
turns, that hold keeps every session from starting a new turn, a side effect no
subresource load may trigger. A token presented explicitly, as `?token=` or
`X-Romp-Token`, is accepted from any Origin: federated (cross-machine) calls
need it, and a cross-site page cannot obtain it: the dashboard drops `?token=`
from its address as it loads (a pane page opened on its own, such as
`/chat?token=`, keeps it), and every page the kernel serves carries
`Referrer-Policy: same-origin`, so a request to another origin carries no
`Referer`. One exception is known: an inline SVG's paint reference to another
origin in a file the viewer shows, once the viewer loads that figure (its host
is on the gear's list, or the reader clicked its placeholder). Its request can
send the page's origin (in Chromium a `mask` does). In one recorded run, before
the sanitizer removed these references from chat messages, a chat message's
`fill` sent the full URL of a page opened as `/chat?token=`, token included. No
later run has reproduced it, the viewer's runs in
`tests/test_paint_refs_kernel_pages_browser.py` included, so treat a page opened
that way as able to send its token with such a request. Everywhere else the
sanitizer removes these references, and an `.svg` opened in its own tab loads
nothing from another host (see Output sanitization below).
The token-exempt routes are the no-side-effect liveness probes (`/healthz`,
`/version` and `/busy` on the kernel, `/ping` on the bus) and the install files:
`/manifest.webmanifest` and the three home-screen icons under `/media/`
(`romp-touch-180.png`, `romp-app-192.png`, `romp-app-512.png`, a fixed allowlist
of names, not a path prefix). A browser fetches those with credentials omitted
when the dashboard is added to a home screen, so a token gate there would break
the install. They are static and read no session state: the manifest is a
fixed JSON literal (app name and short name, display mode, colors, start URL
and icon list) and the icons are three PNG files.

The practical consequence: another local user on a **shared machine** cannot
reach your kernel or bus — `/send` (which injects text into a live Claude
session that runs tools as you) and bus mail both require a token only your
UID can read.

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
- **Serve token required on every request, loopback included**: 144-bit random,
  stored `0600`, constant-time compare; Origin gate on the dashboard and the
  WS upgrade. Federated (cross-machine) calls authorize with the remote
  machine's token, carried over ssh tunnels the local machine initiates.
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
  and inline SVG. An inline SVG's paint and CSS image references to another
  origin (a `url()` in a `fill`, `stroke`, `mask`, `clip-path`, `filter` or
  `marker-*` attribute, or in an inline `style` declaration) are removed from
  the sanitized markup before any node reaches the page, by the sanitizer and
  again by the strip that the file preview card and the feed's notice cards run,
  so none of them makes a request to another host when a chat message, a
  previewed file or a notice card renders; a same-document `url(#id)`, a `data:`
  URL and this origin's own stay (in an editor webview the sanitizer also keeps
  the kernel's origin), and the file viewer gates the same references behind a
  click instead (`ui/webview/paint-refs.ts`, checked against the code by
  `ui/webview/paint-refs-census.test.ts` and, in the browser, by
  `ui/webview/chat-paint-refs-browser.test.ts`,
  `tests/test_file_preview_browser.py` and
  `tests/test_paint_refs_kernel_pages_browser.py`). Once the reader clicks, or
  when the host is on the gear's list, those references load, and such a request
  can send the page's origin: the exception to the `Referer` rule in the trust
  model above. An `.svg` opened in its own tab (on the web dashboard, a Cmd,
  Ctrl or middle click on a path link to it in a viewed file) does not become
  a document. The kernel's `/file` route and its `/remote/<host>/file` relay
  answer the tab, and a frame, an object or an embed, with a small page that
  shows the file in an `<img>`. An SVG drawn as an image runs no script and
  loads nothing its markup names, while its embedded `data:` images and inline
  styles still render. This has a cost: in that tab the SVG's own links do not
  open and its text cannot be selected. The SVG bytes that every other request
  gets (the page's `<img>`, the viewer, the chat's thumbnails) still carry a
  `Content-Security-Policy` of `sandbox` and four fetch directives
  (`default-src 'none'`, `img-src data: blob:`, `style-src 'unsafe-inline'` and
  `font-src data:`), a second layer for anything that still loads them as a
  document. That policy alone was not enough: in Firefox a paint reference to a
  `data:` SVG document fetched that document's `@import`, and in WebKit a
  `preconnect` link opened a connection to its host.
  `tests/test_svg_tab_policy_browser.py` opens the tab in Chromium, Firefox and
  WebKit (Playwright's builds, not Safari) and finds no request and no
  connection to another host; a `dns-prefetch` lookup is not visible to it. CI
  runs its Chromium leg only, and the Firefox and WebKit legs run where those
  engines are installed, under `ROMP_BROWSER_ENGINES`. One renderer writes into that
  sanitized DOM after DOMPurify has run: KaTeX. The sanitizer keeps only color
  in an inline `style`, and
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
