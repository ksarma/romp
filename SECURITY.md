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
from its address as it loads, and every page the kernel serves carries
`Referrer-Policy: same-origin`, so the token never reaches another origin in a
`Referer`.
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

By default the kernel opens one connection of its own to a host other than the
model provider: it fetches a public model-pricing table
(`raw.githubusercontent.com/.../model_prices_and_context_window.json`) when
the Token usage view opens and this kernel has made no fetch attempt yet, or
its last attempt is more than six hours old, with no credential. The kernel
stamps the attempt before the fetch runs, so a fetch that fails or lands
nothing holds the six hours like one that landed, and the first open of the
view after a start always fetches. The response is parsed strictly as numeric
pricing. The kernel's other connections, and the programs it runs that connect
on their own, are listed below. The list is derived from the code by
`python3 scripts/network-inventory.py`, run from the repository root: the
script walks kernel/, cli/, postal/, bin/, hooks/, ui/, vscode-extension/src
and the install scripts for every site that opens a connection or starts a
program, compares what it finds with the counts committed beside it in
`scripts/network-inventory-expected.json`, and exits 1 naming any site it
cannot place, any count that differs, any HTTP or socket client it does not
know and any row of its table that names no site; the test suite runs it
(`tests/test_price_feed_census.py`). The shell and browser sides are matched
by a named list with no completeness gate: a tool or a client the lists do not
name is no site and no line; the Python side's gate is module-granular: an
import outside the allow-list fails the run, and a primitive of a known module
outside NET and SUB is not a site. NET and SUB are the script's lists of the
connection and command primitives it reads. Four classes of outbound activity
the scan cannot derive are named and counted in its table rather than left
out: an external program started whose far end its arguments do not show (a
shell, node, perl or python as the program, whether the kernel starts it, a
shell script of romp's runs its text inline (`python3 -c`, a heredoc,
`node -e`), or the manager or the editor extension starts it; a command run
through a shell; git with a subcommand the code does not spell out; an argv
the code does not spell out); a program whose text is supplied at run time (a
watch predicate, the apiKeyHelper or a login's token command); a browser
request whose URL is computed at run time (a fetch, or a dynamic import of a
module); and the loads the browser makes on its own for what a page inserts
(an image, a frame, a script, a link). A fifth is named in the table and not
counted, since the scan cannot see it: a socket primitive called on a receiver
the census cannot resolve (an attribute-held or parameter socket) is not a
site here.

`ROMP_PRICE_FEED=off` in the kernel's environment (`service.env` for the
installed service, then a manager restart) stops that fetch: the Token usage
modal then prices tokens from the built-in defaults and says so on the line
under its footnote, and `/version` says the same in its `priceFeed` block.
Only the value `off`, whitespace and case ignored, turns the feed off; any
other value leaves it on, and the kernel says so on its stderr, on that line
and in that block. The reference documents the switch under
[The price feed](docs/reference.md#the-price-feed).

The kernel's other connections of its own by default go to the model provider:
the Models API catalog refresh, on the apiKeyHelper's key or else the
`ANTHROPIC_AUTH_TOKEN` bearer from its environment (`ROMP_MODEL_CATALOG=off`
stops it; with neither credential it sends nothing), and, when an apiKeyHelper
is configured, the fast-mode probe on that key at every key-billed session
connect and, for the judges, once per judge process and again after a fast
refusal. By default the kernel also runs programs that connect on their own:
`git ls-remote` against the release remote, at boot and then every six hours
for the release check, on a clone whose VERSION file names a release, and
every five minutes for the drift check, on a checkout on branch main, in
update mode auto, or with a machine attached or remembered
(`ROMP_UPDATE_CHECK=off`, or the gear's update mode off, stops both);
`git ls-remote --heads origin` in a viewed file's checkout when its branch has
no local tracking ref; the session CLIs and the judge CLIs, which talk to
their providers on the session's or the call's billing; one `npm install`
when a bundle rebuild fails at boot; and, in the browser rather than the
kernel, the pictures a viewed markdown file loads from the hosts on the gear's
Pictures from the web in files list, which starts as github.com, its image and
asset hosts, localhost and 127.0.0.1 (a figure from any other host makes no
request until you click it; removing a host from the list stops its loads).

The other connections open when something sets them up, you or a session you
are running: an attached machine (ssh commands to it and tunnels to it, and
everything over them, a Pull of its checkout included); a PR watch
(`gh pr view` on a cadence, registered with `romp watch-pr`, which asks `gh`
for the repository's name when given no `--repo`); a watch predicate, which a
session registers on its own (`romp watch`, POST `/watch`; no setting of yours
gates it), after which the kernel runs the registered text through `/bin/sh`
on the cadence the registration names (no faster than every 15 seconds, every
60 by default) until it exits 0, its bound (24 hours by default) or a cancel,
re-armed at boot, and what the command itself sends is not romp's; a
subscribed phone (web push, encrypted end to end); the apiKeyHelper or
stored-login command you configured; and an update taken from the banner or
by the auto mode (`git fetch`, then for a release `install.sh` with pip and
npm, through `bin/romp-sdk-setup` and `vscode-extension/install.sh`; the
editor extension's update prompt runs `vscode-extension/install.sh`
(`npm install` and `npx`) on your click, not the root `install.sh`, so a click
reaches the npm registry and not PyPI). Whoever starts it,
`vscode-extension/install.sh` runs `npm install` against the npm registry on
every run; `npx --yes @vscode/vsce package`, a fetch of vsce from the same
registry even when it is cached, runs only when an editor CLI is present
(`code`, `code-insiders`, `cursor` or `codium` on PATH, or an editor bundle
under `ROMP_EDITOR_APPS`) or `ROMP_EXT_PACKAGE_ONLY` is set; with neither the
script exits after the build and sends nothing more. Installing by hand
(`bootstrap.sh`, `install.sh`) fetches from GitHub, PyPI (and
bootstrap.pypa.io for get-pip.py when the python lacks ensurepip;
`ROMP_NO_GET_PIP=1` skips that fetch) and the npm registry, and
`bin/romp-codex-setup`, run by hand for Codex sessions, fetches the Codex SDK
from PyPI and the pinned Codex CLI from GitHub.

What those programs send is theirs, not the kernel's: a session's own CLI, the
judges' CLIs, a watch predicate, the API key helper, a login's token program,
`gh`, `git`, `ssh`, `npm` and the browser open connections of their own, and
the census lists such a site by the program it starts, never by where that
program connects. romp sends no telemetry: the kernel's own requests to hosts
other than the machines you attach are the four named above: the price table,
the catalog refresh, the fast-mode probe and web push. Session text goes to
the model provider the session or the judge call is billed to; over your own
ssh tunnels to a machine you attached (the text you send a session there, the
session listings, views and file bodies relayed back, and the postal mail
between the two machines' buses); and, encrypted end to end, to the push
service of a phone you subscribed.

## Reporting a vulnerability

Please report security issues privately via GitHub Security Advisories on the
repository rather than opening a public issue. Include a description, affected
version/commit, and a reproduction if you have one.
