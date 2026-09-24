#!/usr/bin/env python3
"""What an inline svg's paint references send from the kernel's own pages, under the kernel's real headers (2026-09-23).

A hermetic lab kernel (the served labs' environment, tests/test_ship_reship_served.py kernel_env: its own state root,
port and token) serves one synthetic session and the real /feed, /chat and / pages from a copy of the built bundle. A
request logger on 127.0.0.1:Q records each request's path, Referer, Sec-Fetch-Dest and Sec-Fetch-Site. The
browser reaches it under two names, each another origin and another site to the pages (served from 127.0.0.1):
http://localhost:Q, a name Chromium counts as trustworthy and so sends its Sec-Fetch headers to, and
http://remote.invalid:Q (Chromium's --host-resolver-rules maps the name to 127.0.0.1), a host the file viewer's figure
gate does not list (the gear's figureHosts default names github.com's hosts, localhost and 127.0.0.1). Four scenes:

test_a_notice_card_s_paint_references_reach_no_other_host: a notice card's body on the feed page (feed.ts
noticeBodyNodes: a session writes it through POST /notice, and the feed runs it through sanitizeMd and then
stripRemoteLoads with an empty base). The body carries an inline svg with each of the eight paint attributes (fill,
stroke, filter, clip-path, mask, marker-start, marker-mid, marker-end) and an inline style's mask-image, each aimed at
the logger as localhost. The feed page is opened bare, /feed?token=, so its own address carries the token. Asserted: no
request reaches the logger, and no remote reference stands in the card. Two controls say an empty log is the removal's
work. The body's absolute same-origin reference (a fill naming the kernel's own /media/romp-swirl-glyph.svg?own=notice)
must stand in the card and be requested from the kernel within a bound, which shows the card painted, its svg rendered,
and this browser fetched a paint reference the pass keeps (with the body fallen to plain text, or with the pass
admitting no own origin, it is neither requested nor in the card); the driver then drains 1.5 s more before the log is
read. It is absolute on purpose: the notice card's strip passes no base, so a relative same-origin reference is removed
there (a residual that fails closed, pinned in ui/webview/file-preview.test.ts). After the record the page fetches the
logger once (no-cors), which must be its one /reach-notice line, so the logger is one the page can reach. Red before the
fix, at 6cf6839ba (this file run over a copy of that tree, 2026-09-23): the logger received the fill, stroke, clip-path,
mask and the three markers, each Sec-Fetch-Dest image and cross-site, the mask with the page's origin as its Referer and
the rest with none; the filter and the style's mask-image sent nothing (the colour-only style rule removes the
declaration at that commit too).

test_a_figure_the_viewer_loads_on_a_click_sends_at_most_the_page_s_origin: the file viewer, a modal over the chat pane,
holds a figure on an unlisted host behind a placeholder, and one click loads it. The scene opens it twice: from a bare
/chat?token= page, whose own address carries the token, and from the framed shell (/?token=, which drops the token from
its address before it frames /chat without it). Each opens a markdown file whose figures are an img and an inline svg
with the same eight paint attributes, aimed at the logger as remote.invalid, clicks the placeholder, and waits (bounded)
until the img, the fill and the mask have arrived. Asserted: nothing reached the logger before the click, and each
request after it carries no Referer or the page's origin alone, never a path or the token. At this commit and at
6cf6839ba the img, the fill, the stroke, the clip-path and the three markers sent no Referer, the mask sent the page's
origin, and the filter sent nothing, from either page. Red under mutations (2026-09-23): with the kernel's
Referrer-Policy changed to unsafe-url the img and the six others carried the bare page's full URL with its token (the
mask still sent the origin alone, so Chromium does not take a mask's Referer from the page's policy), and with the gate
letting every host through the img and the seven paint references that fetch arrived before any click.

test_a_data_document_in_a_notice_card_or_a_hover_preview_reaches_no_other_host: the data: rule (paint-refs.ts
DATA_RASTER_TYPES) on the kernel's own pages. In Firefox 153 a paint attribute that names a data: SVG, XHTML or XML
document with a fragment loads it as a resource document, and that document's own @import fetches another host as the
card renders. A notice card (POST /notice, then /feed?token=) and a hover preview (the reply's link to
docs/paint-data.md on /chat?token=, hovered past the dwell) each carry, first, a 40 by 40 rect under a raster data: mask
(its left half opaque), then the five attributes fill, stroke, mask, filter and clip-path, each naming a data: SVG
document with its fragment and an @import of its own, the six other spellings Firefox loads the same way on a fill (upper
case, a charset parameter, base64, application/xhtml+xml, text/xml and application/xml), a data: URL with no type, a
same-document url(#g), the page's own mask (absolute on the notice, whose strip has no base; relative on the hover) and
a data: URL typed image/png whose body is an svg with an @import. The @imports name a second server of this class's own on
http://localhost:Q, listening on 127.0.0.1 and ::1 at one port, which logs each request's path, Referer class and
Sec-Fetch headers. The scene drives Chromium always, and Firefox and WebKit when ROMP_BROWSER_ENGINES names them (a comma
list; any other name fails the test, a named Firefox or WebKit that does not launch is a failure, never a skip, and a
Chromium that does not launch is a skip, named or not). CI's extension job installs Chromium alone and sets no such
variable, so it runs the Chromium leg with nothing skipped; the Firefox and
WebKit figures are runs on a machine that has those engines, with the variable set. In each engine, after both cards
rendered and the page's own mask was requested from the kernel (the positive control), each page sets the same documents,
unsanitized, outside the card, and the driver waits (bounded) for the loads the engine makes of them (CONTROL_LOADS: all
eleven per page in Firefox, none in Chromium or WebKit, which load no data: paint document, so in them the scene is a DOM
witness), then drains 1.5 s. Asserted per engine and card: no request reached the sink from the card's documents, every
document reference is removed from its element, the controls stay as written, the kept raster mask draws (its left half
red and its right half not, in Chromium and Firefox; WebKit 26.5 applies no data: mask), the hover card was still up, no
page error, and the feed page reached the sink once afterwards. Red with b4f9139b8's paint-refs.ts and md-sanitize.ts
(2026-09-24, Playwright 1.62.1): in Firefox 153 the sink received the eleven @imports of each card's documents, 22 in
all, each Sec-Fetch-Dest style, cross-site, no-cors and with no Referer, and the removal subtests were red in all three
engines; the controls, the control loads and the drawing were green there, since the rule changes only what is removed.

test_a_data_document_in_a_viewed_file_is_dropped_and_reaches_no_other_host: the data: rule in the file viewer. The viewer
keeps references to another origin for its gate and drops a data: document as the other surfaces do, never gating it
(paint-refs.ts dropDataDocuments, which sanitizeMd runs under the viewer's remoteRefs: "keep"): a placeholder could name
only data:, and its click would load a document that fetches hosts the label never names. The reply's link to
docs/paint-data-viewer.md on /chat?token= opens the viewer through a click event dispatched at the link, with the pointer
parked in a corner, so no hover card renders the same file (asserted). The file carries the third scene's shapes and
controls under DV- (the page's own mask relative, which the gate never holds), and after them a rider: a rect whose fill
names unlisted.invalid, a host the gear does not list, so the gate holds it behind a placeholder, and whose stroke names a
data: SVG document with an @import of its own. The driver reads the viewer at the open and drains 1.5 s, clicks the
placeholder, waits (bounded) for the fill to come back and drains 1.5 s, then sets the unsanitized control on the page.
Asserted per engine, on the same engine rule as the third scene: no request reached the sink from a document in the file,
at the open or after the click; every document reference is gone from its element and no attribute under the viewer holds
a data: reference aside; the rider's stroke is neither on the rect nor held aside at the open, and the click brings back
its fill alone; the one placeholder names unlisted.invalid; the controls stay as written, the raster mask draws (Chromium
and Firefox), the page's own mask was requested, the control loads, the reach and no page error. Red with b4f9139b8's
paint-refs.ts, md-sanitize.ts, figure-gate.ts and file-view.ts, and again with 3ceb237ee's (2026-09-24, Playwright 1.62.1):
in Firefox 153 the sink received the eleven @imports of the file's documents as it opened and the rider's after the click,
each Sec-Fetch-Dest style, cross-site, no-cors and with no Referer; in all three engines the document references stood in
the viewer, and the gate held the rider's stroke aside with its fill and the click restored it.

Skips LOUDLY without the extension deps or a Playwright browser; the CI extension job installs Chromium and runs served
files with ROMP_SERVED_TESTS_REQUIRE=1, which turns any skip into a failure there. SYNTHETIC fixtures only (session web,
the notes-api demo world, a placeholder uuid, the host remote.invalid)."""
import base64
import errno
import json
import os
import re
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.parse
import urllib.request
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import lab_dist

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
EXT = os.path.join(ROOT, "vscode-extension")
sys.path.insert(0, HERE)
import test_ship_reship_served as _lab   # noqa: E402  the lab kernel's environment (the module, not its classes)

SID = "aaaaaaaa-1111-2222-3333-555555555555"
U_UUID = "11111111-2222-3333-4444-555555555555"
A_UUID = "22222222-3333-4444-5555-666666666666"
REMOTE_HOST = "remote.invalid"   # the logger's name in the viewer scene, mapped to 127.0.0.1 by the launch flag below
# the eight paint attributes, by the file name each asks the logger for (the scene's prefix goes in front)
PAINT = ("fill.svg", "stroke.svg", "clip.svg", "mask.svg", "filter.svg", "ms.svg", "mm.svg", "me.svg")
VIEWER_AWAITED = ("img.png", "fill.svg", "mask.svg")   # what the viewer scene waits for after the click (bounded)
DATA_FILE = "docs/paint-data.md"   # the hover scene's markdown file of data: documents
VIEWER_FILE = "docs/paint-data-viewer.md"   # the viewer scene's markdown file of data: documents
UNLISTED = "unlisted.invalid"   # a host the gear's figureHosts does not list and no name resolves: the rider's gated fill names it
ENGINES = ("chromium", "firefox", "webkit")
# What each engine loads from the unsanitized control's data: documents (the five attributes and the six other spellings),
# measured 2026-09-24 in Playwright 1.62.1: Firefox 153 every one, Chromium 151 and WebKit 26.5 none (they load no data:
# paint document, sanitized or not, so in them the data: scene is a DOM witness).
CONTROL_LOADS = {"chromium": False, "firefox": True, "webkit": False}
# The engines whose kept raster data: mask draws (measured 2026-09-24: Chromium 151 and Firefox 153; WebKit 26.5 applied no
# data: mask, unsanitized either, so its pixels are not asserted).
MASK_DRAWS = ("chromium", "firefox")
PAINT_FRAG = (("fill", "p"), ("stroke", "p"), ("mask", "m"), ("filter", "f"), ("clip-path", "c"))


def _engines():
    """The engines the data: scene drives: Chromium always, then each engine ROMP_BROWSER_ENGINES names (a comma list), in its
    order. A name outside ENGINES raises, so a misspelling fails the test instead of quietly running Chromium alone."""
    asked = [e.strip() for e in (os.environ.get("ROMP_BROWSER_ENGINES") or "").split(",") if e.strip()]
    bad = [e for e in asked if e not in ENGINES]
    if bad:
        raise AssertionError("ROMP_BROWSER_ENGINES names %r, outside %s" % (bad, ", ".join(ENGINES)))
    out = ["chromium"]
    for e in asked:
        if e not in out:
            out.append(e)
    return out


def _uri(s):
    """encodeURIComponent: every character but the unreserved marks percent-encoded."""
    return urllib.parse.quote(s, safe="-_.!~*'()")


def _doc_svg(import_url):
    """A data: document's markup: an svg whose <style> imports `import_url`, and one element per paint fragment (#p a
    pattern, #m a mask, #c a clipPath, #f a filter)."""
    return ("<svg xmlns='http://www.w3.org/2000/svg'><defs><style>@import url(%s);</style>"
            "<pattern id='p' width='1' height='1'><rect width='1' height='1' fill='blue'/></pattern>"
            "<mask id='m'><rect width='1' height='1' fill='white'/></mask><clipPath id='c'><rect width='1' height='1'/></clipPath>"
            "<filter id='f'><feFlood flood-color='blue'/></filter></defs></svg>" % import_url)


# The spellings of a data: document that Firefox 153 loaded as a resource document when a paint attribute named it with a
# fragment (measured 2026-09-24, on a page with no sanitizer, all five attributes each).
DOC_SPELLINGS = (
    ("plain", lambda x: "data:image/svg+xml," + _uri(x)),
    ("upper", lambda x: "data:IMAGE/SVG+XML," + _uri(x)),
    ("charset", lambda x: "data:image/svg+xml;charset=utf-8," + _uri(x)),
    ("base64", lambda x: "data:image/svg+xml;base64," + base64.b64encode(x.encode()).decode()),
    ("xhtml", lambda x: "data:application/xhtml+xml," + _uri(x)),
    ("textxml", lambda x: "data:text/xml," + _uri(x)),
    ("appxml", lambda x: "data:application/xml," + _uri(x)),
)


def _mask_png(w=40, h=40):
    """A 40 by 40 RGBA PNG, white, its left half opaque and its right half transparent: as a mask it shows the left half."""
    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff)
    raw = b"".join(b"\x00" + b"".join(bytes((255, 255, 255, 255 if x < w // 2 else 0)) for x in range(w)) for _ in range(h))
    return base64.b64encode(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
                            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")).decode()


def _doc_ref(spelled, frag):
    return 'url("%s#%s")' % (spelled, frag)


def _doc_shapes(sink, prefix, cls):
    """The data: document shapes: the five attributes each naming the plain document, then the six other spellings on a
    fill, each document's @import naming `prefix` + its name on the sink."""
    shapes = [{"cls": cls + attr, "attr": attr, "file": "/%s%s.css" % (prefix, attr),
               "value": _doc_ref(DOC_SPELLINGS[0][1](_doc_svg("%s/%s%s.css" % (sink, prefix, attr))), frag)} for attr, frag in PAINT_FRAG]
    return shapes + [{"cls": cls + name, "attr": "fill", "file": "/%s%s.css" % (prefix, name),
                      "value": _doc_ref(spell(_doc_svg("%s/%s%s.css" % (sink, prefix, name))), "p")} for name, spell in DOC_SPELLINGS[1:]]


def _doc_svg_tag(s):
    """One shape as the markdown holds it: an svg of the shape's class around one rect carrying the attribute."""
    size = 40 if s["cls"] == "k-raster" else 12
    paint = "" if s["attr"] == "fill" else 'fill="none" stroke-width="4" ' if s["attr"] == "stroke" else 'fill="red" '
    defs = '<defs><linearGradient id="g"><stop offset="0" stop-color="red"/></linearGradient></defs>' if s["cls"] == "k-local" else ""
    return '<svg class="%s" width="%d" height="%d">%s<rect width="%d" height="%d" %s%s="%s"/></svg>' % (
        s["cls"], size, size, defs, size, size, paint, s["attr"], s["value"].replace('"', "&quot;"))


def _doc_scene(sink, prefix, own, extra=()):
    """One scene's data: shapes, controls and markdown (`extra`: more markdown blocks, before the last line). The witness: _doc_shapes under `prefix`, and a data: URL with no
    type (text/plain, which no engine loads; read in the DOM alone). The controls, which stay as written: a raster data:
    mask (first, so the card shows it without a scroll), a same-document url(#g), the page's own mask `own` (requested in
    every engine), and a raster-labelled data: URL whose body is an svg with an @import (kept: its type is a raster; loaded
    by no engine). The unsanitized control: _doc_shapes again under "C" + `prefix`, for the page to set outside the card."""
    shapes = _doc_shapes(sink, prefix, "d-") + [{"cls": "d-notype", "attr": "fill", "file": "/%snotype.css" % prefix,
                                                 "value": _doc_ref("data:," + _uri(_doc_svg("%s/%snotype.css" % (sink, prefix))), "p")}]
    kept = [{"cls": "k-raster", "attr": "mask", "file": "", "value": 'url("data:image/png;base64,%s")' % _mask_png()},
            {"cls": "k-local", "attr": "fill", "file": "", "value": "url(#g)"},
            {"cls": "k-own", "attr": "mask", "file": "", "value": "url(%s#m)" % own},
            {"cls": "k-pngbody", "attr": "fill", "file": "/%spngbody.css" % prefix,
             "value": _doc_ref("data:image/png," + _uri(_doc_svg("%s/%spngbody.css" % (sink, prefix))), "p")}]
    md = "\n\n".join(["A figure sample with data: documents."] + [_doc_svg_tag(s) for s in kept[:1] + shapes + kept[1:]] + list(extra) + ["The end.", ""])
    control = _doc_shapes(sink, "C" + prefix, "c-")
    return {"shapes": shapes, "kept": kept, "md": md, "control": "".join(_doc_svg_tag(s) for s in control),
            "controlFiles": sorted(s["file"] for s in control)}


def _viewer_doc_scene(sink):
    """The viewer scene's markdown: _doc_scene under "DV-" with the page's own mask relative (the viewer resolves it against
    the page, and its gate never holds this origin's own), and a rider after the controls: an svg whose rect's fill names
    UNLISTED, which the gate holds behind a placeholder, and whose stroke names a data: SVG document with an @import of its
    own (/DV-rider.css), which the viewer must drop, not hold aside for the click on that placeholder to bring back."""
    rider_doc = _doc_ref(DOC_SPELLINGS[0][1](_doc_svg("%s/DV-rider.css" % sink)), "p")
    rider = {"fill": "url(http://%s/rider.svg#p)" % UNLISTED, "stroke": rider_doc, "file": "/DV-rider.css"}
    tag = '<svg class="r-rider" width="12" height="12"><rect width="12" height="12" stroke-width="4" fill="%s" stroke="%s"/></svg>' % (
        rider["fill"], rider["stroke"].replace('"', "&quot;"))
    scene = _doc_scene(sink, "DV-", "/media/romp-swirl-glyph.svg?own=dviewer", extra=(tag,))
    scene["rider"] = rider
    return scene


def _png(w=2, h=2, rgb=(200, 60, 60)):
    """A tiny valid PNG (RGB, no filter) without a binary fixture."""
    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff)
    raw = b"".join(b"\x00" + bytes(rgb) * w for _ in range(h))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def _svgs(r):
    """One inline svg per paint attribute, each aimed at `r` (the logger's URL and the scene's prefix)."""
    def svg(inner):
        return '<svg width="40" height="40">%s</svg>' % inner
    return [
        svg('<rect width="40" height="40" fill="url(%sfill.svg#p)"/>' % r),
        svg('<rect width="40" height="40" fill="none" stroke="url(%sstroke.svg#p)" stroke-width="4"/>' % r),
        svg('<rect width="40" height="40" fill="red" clip-path="url(%sclip.svg#c)"/>' % r),
        svg('<rect width="40" height="40" fill="red" mask="url(%smask.svg#m)"/>' % r),
        svg('<rect width="40" height="40" fill="red" filter="url(%sfilter.svg#f)"/>' % r),
        svg('<path d="M5 5 L20 30 L35 5" stroke="red" fill="none" marker-start="url(%sms.svg#a)" marker-mid="url(%smm.svg#b)" '
            'marker-end="url(%sme.svg#c)"/>' % (r, r, r)),
    ]


def _notice_body(remote, origin):
    """The notice's markdown: the eight paint attributes and an inline style's mask-image aimed at the logger, and the
    absolute same-origin control. The style's mask-image never reaches the paint pass: the sanitizer's colour-only style
    rule removes that declaration first, at 6cf6839ba too, so it sends nothing before or after the fix, and the pass's
    style arm is held by ui/webview/paint-refs.test.ts, not by this scene."""
    r = remote + "/N-"
    return "\n\n".join(
        ["A new version of the accuracy figure is ready."] + _svgs(r) +
        ['<span style="color: red; mask-image: url(%sstyle.png)">a masked word</span>' % r,
         '<svg width="40" height="40"><rect width="40" height="40" fill="url(%s/media/romp-swirl-glyph.svg?own=notice#p)"/></svg>' % origin,
         "The end."])


def _figures(remote, prefix):
    """A viewed markdown file whose figures sit on the logger's host: an img and the eight paint attributes."""
    r = remote + "/" + prefix
    return "\n\n".join(["# Figures", "The figures from the sweep.", '<img src="%simg.png" alt="a remote figure">' % r]
                       + _svgs(r) + ["The end.", ""])


DRIVER = r"""
import { createRequire } from "node:module";
import fs from "node:fs";
const require = createRequire(process.env.EXT_PKG);
const { chromium } = require("playwright");
const cfg = JSON.parse(fs.readFileSync(process.env.CFG, "utf8"));
let browser;
try { browser = await chromium.launch({ args: ["--host-resolver-rules=MAP " + cfg.remoteHost + " 127.0.0.1"] }); }
catch (e) { console.error("browser-launch-failed: " + e); process.exit(3); }
const context = await browser.newContext({ viewport: { width: 1400, height: 900 } });
const errors = [];
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const logNow = async () => (await (await fetch(cfg.logUrl)).json());   // the logger's own record, read from node
const reach = (page) => page.evaluate((u) => fetch(u, { mode: "no-cors", cache: "no-store" }).then(() => "ok", (e) => String(e)), cfg.remote + "/reach-" + cfg.scene);
const out = { errors };
if (cfg.scene === "notice") {
  const page = await context.newPage();
  page.on("pageerror", (e) => errors.push(String(e).slice(0, 300)));
  const own = [];        // the same-origin control's responses: the kernel's answer, as the browser received it
  page.on("response", (r) => { if (r.url() === cfg.own) own.push({ status: r.status(), referrerPolicy: r.headers()["referrer-policy"] || null }); });
  await page.goto(cfg.feed);
  const sel = '[data-key="a:' + cfg.itemId + '"]';
  await page.waitForSelector(sel + " .fask-nbody svg", { timeout: 60000 }).catch(() => {});
  const t0 = Date.now();
  while (Date.now() - t0 < 15000 && !own.length) await sleep(50);
  out.ownWaitMs = Date.now() - t0;
  await sleep(1500);     // the drain: a remote paint request the card made would have reached the logger by now
  out.own = own.slice();
  out.card = await page.evaluate((s) => {
    const c = document.querySelector(s); if (!c) return null;
    const b = c.querySelector(".fask-nbody"); const cs = getComputedStyle(c);
    // every attribute of every element in the body, as `tag[name]` and its value: the DOM the page adopted, not its text
    const attrs = b ? Array.from(b.querySelectorAll("*")).flatMap((e) => Array.from(e.attributes).map((a) => ({ at: e.tagName.toLowerCase() + "[" + a.name + "]", value: a.value }))) : [];
    return { col: c.parentElement && c.parentElement.id, vis: c.offsetHeight > 0 && cs.display !== "none", html: b ? b.innerHTML : null,
             svgs: b ? b.querySelectorAll("svg").length : 0, attrs };
  }, sel);
  out.pageUrl = page.url();
  out.reach = await reach(page);
} else {
  // the viewer: the session's tab, the file link in its reply, the viewer's placeholder, one click, then the arrivals
  const viewer = async (frame, file, prefix) => {
    const r = {};
    await frame.waitForSelector("#tabs .tab[data-id]", { timeout: 30000 });
    await frame.click('#tabs .tab[data-id="' + cfg.sid + '"]');
    const link = '#content .file-uri-link[data-path="' + file + '"]';
    await frame.waitForSelector(link, { timeout: 30000 });
    await frame.click(link);
    // the file rendered: its heading is in the viewer, and the gate ran on the same inert body before it was adopted
    await frame.waitForSelector('#romp-fileview [id="md-figures"]', { timeout: 30000 });
    await sleep(1000);   // a request an ungated figure made on open would have landed by now
    r.gatedHosts = await frame.evaluate(() => Array.from(document.querySelectorAll('#romp-fileview [data-act="fv-load"]')).map((g) => g.getAttribute("data-fv-host")));
    r.beforeClick = (await logNow()).filter((l) => l.path.startsWith("/" + prefix)).map((l) => l.path);
    if (r.gatedHosts.length) await frame.click('#romp-fileview [data-act="fv-load"]');   // one click loads every figure of that host
    await sleep(200);
    r.leftGated = await frame.evaluate(() => document.querySelectorAll('#romp-fileview [data-act="fv-load"]').length);
    const t0 = Date.now();
    while (Date.now() - t0 < 15000) {
      const got = (await logNow()).map((l) => l.path);
      if (cfg.awaited.every((n) => got.includes("/" + prefix + n))) break;
      await sleep(100);
    }
    r.waitMs = Date.now() - t0;
    await sleep(1500);   // the drain: every request the click set off has landed
    r.url = frame.url();
    return r;
  };
  const bare = await context.newPage();
  bare.on("pageerror", (e) => errors.push("bare: " + String(e).slice(0, 300)));
  await bare.goto(cfg.chat);
  out.bare = await viewer(bare.mainFrame(), cfg.files.bare, "B-");
  const shell = await context.newPage();
  shell.on("pageerror", (e) => errors.push("shell: " + String(e).slice(0, 300)));
  await shell.goto(cfg.shell);
  let chat = null;
  const t0 = Date.now();
  while (!chat && Date.now() - t0 < 30000) {
    chat = shell.frames().find((f) => { try { return f !== shell.mainFrame() && new URL(f.url()).pathname === "/chat"; } catch (e) { return false; } }) || null;
    if (!chat) await sleep(100);
  }
  if (!chat) { console.error("the shell framed no /chat pane: " + JSON.stringify(shell.frames().map((f) => f.url()))); process.exit(1); }
  out.framed = await viewer(chat, cfg.files.framed, "F-");
  out.framed.shellUrl = shell.url();
  out.reach = await reach(bare);
}
fs.writeSync(1, "RESULT:" + JSON.stringify(out) + "\n");
await browser.close();
process.exit(0);
"""


DOC_DRIVER = r"""
import { createRequire } from "node:module";
import fs from "node:fs";
const require = createRequire(process.env.EXT_PKG);
const pw = require("playwright");
const cfg = JSON.parse(fs.readFileSync(process.env.CFG, "utf8"));
let browser;
try { browser = await pw[cfg.engine].launch(); }
catch (e) { console.error("browser-launch-failed: " + e); process.exit(3); }
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const logNow = async () => (await (await fetch(cfg.logUrl)).json()).requests;   // the sink's own record, read from node
const out = { engine: browser.browserType().name(), version: browser.version(), errors: [] };
const context = await browser.newContext({ viewport: { width: 1400, height: 1000 } });
// each shape's attribute in `scope`, as the page adopted it: the value, null when removed, "(no element)" when the rect went
const readShapes = (page, scope, shapes) => page.evaluate(([sc, ss]) => ss.map((s) => {
  const e = document.querySelector(sc + " ." + s.cls + " rect"); return { cls: s.cls, value: e ? e.getAttribute(s.attr) : "(no element)" };
}), [scope, shapes]);
// the raster mask's pixels: a screenshot of the masked rect, decoded in the page, read at a quarter and three quarters across,
// once no animation or transition runs on the rect or an element around it (bounded: a card's entry fade dims what is read)
const pixels = async (page, sel) => {
  await page.waitForFunction((s) => { const e = document.querySelector(s); return !!e && document.getAnimations().every((a) => a.playState !== "running"
    || !(a.effect && a.effect.target && a.effect.target.contains && a.effect.target.contains(e))); }, sel, { timeout: 5000 }).catch(() => {});
  const box = await page.locator(sel).first().boundingBox().catch(() => null);
  if (!box) return null;
  const png = await page.screenshot({ clip: box });
  return page.evaluate(async (b64) => {
    const img = new Image(); img.src = "data:image/png;base64," + b64; await img.decode();
    const c = document.createElement("canvas"); c.width = img.width; c.height = img.height;
    const x = c.getContext("2d"); x.drawImage(img, 0, 0);
    const at = (fx) => Array.from(x.getImageData(Math.floor(fx * img.width), Math.floor(img.height / 2), 1, 1).data);
    return { left: at(0.25), right: at(0.75) };
  }, png.toString("base64"));
};
const requested = (page, needle) => { const hits = []; page.on("request", (r) => { if (r.url().includes(needle)) hits.push(r.url()); }); return hits; };
const until = async (cond, ms) => { const t0 = Date.now(); while (!cond() && Date.now() - t0 < ms) await sleep(50); return Date.now() - t0; };
if (cfg.scene === "viewer") {
  // the file viewer on the chat page: the session's reply links the viewer's data: file, and a click opens it
  const chat = await context.newPage();
  chat.on("pageerror", (e) => out.errors.push("chat: " + String(e).slice(0, 300)));
  const own = requested(chat, "own=dviewer");
  await chat.goto(cfg.chat);
  await chat.waitForSelector("#tabs .tab[data-id]", { timeout: 30000 });
  await chat.click('#tabs .tab[data-id="' + cfg.sid + '"]');
  const link = '#content .file-uri-link[data-path="' + cfg.file + '"]';
  await chat.waitForSelector(link, { timeout: 30000 });
  // the click is an event dispatched at the link with the pointer parked in a corner, so no hover card renders the same file
  // on the preview's road (another surface, with a strip of its own): what reaches the sink is the viewer's
  await chat.mouse.move(1300, 950);
  await chat.dispatchEvent(link, "click");
  const fv = "#romp-fileview";
  await chat.waitForSelector(fv + " .k-raster rect", { state: "attached", timeout: 30000 }).catch(() => {});
  out.ownMs = await until(() => own.length > 0, 15000);
  await sleep(1500);   // the drain for the open: a data: document the viewer rendered has fetched its @import by now
  out.openLog = await logNow();
  // the viewer's state: every attribute under the viewer held aside by the gate whose value names data:, the placeholders' hosts,
  // and the rider (a rect whose fill names an unlisted host and whose stroke names a data: document)
  const viewerState = () => chat.evaluate(([s]) => {
    const heldData = Array.from(document.querySelectorAll(s + " *")).flatMap((e) => Array.from(e.attributes)
      .filter((a) => a.name.startsWith("data-fv-gated-") && /data:/i.test(a.value)).map((a) => e.tagName.toLowerCase() + "[" + a.name + "]"));
    const hosts = Array.from(document.querySelectorAll(s + ' [data-act="fv-load"]')).map((g) => g.getAttribute("data-fv-hosts"));
    const r = document.querySelector(s + " .r-rider rect");
    const p = document.getElementById("file-preview-pop");
    return { heldData, hosts, rider: r ? { fill: r.getAttribute("fill"), stroke: r.getAttribute("stroke"), heldStroke: r.getAttribute("data-fv-gated-stroke") } : null,
             hoverUp: !!p && getComputedStyle(p).display !== "none" };
  }, [fv]);
  out.open = Object.assign(await viewerState(), { shapes: await readShapes(chat, fv, cfg.viewer.shapes), kept: await readShapes(chat, fv, cfg.viewer.kept),
                                                   pixels: await pixels(chat, fv + " .k-raster rect") });
  // one click on the rider's placeholder loads every figure of its host, and what the gate held with it
  const ph = fv + ' [data-act="fv-load"][data-fv-hosts="' + cfg.unlisted + '"]';
  out.placeholders = await chat.locator(ph).count();
  if (out.placeholders) await chat.click(ph);
  await chat.waitForFunction((s) => { const r = document.querySelector(s + " .r-rider rect"); return !!r && r.hasAttribute("fill"); }, fv, { timeout: 10000 }).catch(() => {});
  await sleep(1500);   // the drain for the click
  out.after = Object.assign(await viewerState(), { shapes: await readShapes(chat, fv, cfg.viewer.shapes) });
  // the unsanitized control, outside the viewer: the same documents set by innerHTML, so the engine's own loads of them reach the
  // sink; then the wait for the ones this engine makes (bounded) and the drain
  await chat.evaluate((h) => { const d = document.createElement("div"); d.id = "data-doc-control"; d.innerHTML = h; document.body.appendChild(d); }, cfg.viewer.control);
  if (cfg.controlLoads) {
    const t0 = Date.now();
    while (Date.now() - t0 < 10000) { const got = (await logNow()).map((l) => l.path.split("?")[0]); if (cfg.viewer.controlFiles.every((f) => got.includes(f))) break; await sleep(100); }
  }
  await sleep(1500);
  out.own = own.slice();
  out.log = await logNow();
  out.reach = await chat.evaluate((u) => fetch(u, { mode: "no-cors", cache: "no-store" }).then(() => "ok", (e) => String(e)), cfg.sink + "/reach-" + cfg.engine);
  fs.writeSync(1, "RESULT:" + JSON.stringify(out) + "\n");
  await browser.close();
  process.exit(0);
}
// the notice card on the feed page, opened bare
const feed = await context.newPage();
feed.on("pageerror", (e) => out.errors.push("feed: " + String(e).slice(0, 300)));
const ownNotice = requested(feed, "own=dnotice");
await feed.goto(cfg.feed);
const card = '[data-key="a:' + cfg.itemId + '"] .fask-nbody';
await feed.waitForSelector(card + " .k-raster", { state: "attached", timeout: 60000 }).catch(() => {});
out.noticeOwnMs = await until(() => ownNotice.length > 0, 15000);
out.notice = { shapes: await readShapes(feed, card, cfg.notice.shapes), kept: await readShapes(feed, card, cfg.notice.kept),
               pixels: await pixels(feed, card + " .k-raster rect") };
// the hover preview on the chat page: the session's reply links the data: file; the card opens after the dwell
const chat = await context.newPage();
chat.on("pageerror", (e) => out.errors.push("chat: " + String(e).slice(0, 300)));
const ownHover = requested(chat, "own=dhover");
await chat.goto(cfg.chat);
await chat.waitForSelector("#tabs .tab[data-id]", { timeout: 30000 });
await chat.click('#tabs .tab[data-id="' + cfg.sid + '"]');
const link = '#content .file-uri-link[data-path="' + cfg.file + '"]';
await chat.waitForSelector(link, { timeout: 30000 });
await chat.mouse.move(1300, 950); await sleep(300);
await chat.hover(link);
const pop = "#file-preview-pop .fp-body";
await chat.waitForSelector(pop + " .k-raster", { state: "attached", timeout: 15000 }).catch(() => {});
out.hoverOwnMs = await until(() => ownHover.length > 0, 15000);
out.hover = { shapes: await readShapes(chat, pop, cfg.hover.shapes), kept: await readShapes(chat, pop, cfg.hover.kept),
              pixels: await pixels(chat, pop + " .k-raster rect") };
// the unsanitized controls, one per page, outside the card: the same documents set by innerHTML, so the engine's own loads of
// them reach the sink; then the wait for the ones this engine makes (bounded) and the drain
for (const [page, html] of [[feed, cfg.notice.control], [chat, cfg.hover.control]]) {
  await page.evaluate((h) => { const d = document.createElement("div"); d.id = "data-doc-control"; d.innerHTML = h; document.body.appendChild(d); }, html);
}
const want = [...cfg.notice.controlFiles, ...cfg.hover.controlFiles];
let got = [];
if (cfg.controlLoads) {
  const t0 = Date.now();
  while (Date.now() - t0 < 10000) { got = (await logNow()).map((l) => l.path.split("?")[0]); if (want.every((f) => got.includes(f))) break; await sleep(100); }
}
await sleep(1500);   // the drain: a request a card's data: document made would have reached the sink by now
out.ownNotice = ownNotice.slice(); out.ownHover = ownHover.slice();
out.hoverUp = await chat.evaluate(() => { const p = document.getElementById("file-preview-pop"); return !!p && getComputedStyle(p).display !== "none"; });
out.log = await logNow();
// the sink's reach control, after the record: one no-cors fetch from the feed page, which must be its one /reach- line
out.reach = await feed.evaluate((u) => fetch(u, { mode: "no-cors", cache: "no-store" }).then(() => "ok", (e) => String(e)), cfg.sink + "/reach-" + cfg.engine);
fs.writeSync(1, "RESULT:" + JSON.stringify(out) + "\n");
await browser.close();
process.exit(0);
"""


def _referer_class(ref):
    if not ref:
        return "none"
    u = urllib.parse.urlparse(ref)
    return "origin" if u.path in ("", "/") and not u.query else "url"


class _DocSink(BaseHTTPRequestHandler):
    """The data: scene's second server: every request's path, Referer class and Sec-Fetch headers logged into `box`, over a
    listener on 127.0.0.1 and one on ::1 at the same port (so `localhost` reaches it whichever family an engine tries
    first); a stylesheet answers every .css, and its own record is at /__doclog (not logged: the driver's wait reads it).
    The requests are the record the rulings ask for; no connection is counted, since the driver's own reads of the record
    would be counted with the page's."""
    box = None
    protocol_version = "HTTP/1.0"

    def do_GET(self):
        if self.path == "/__doclog":
            with self.box["lock"]:
                body = json.dumps({"requests": list(self.box["requests"])}).encode()
            self.send_response(200); self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body); return
        with self.box["lock"]:
            self.box["requests"].append({"path": self.path, "referer": _referer_class(self.headers.get("Referer")),
                                         "dest": self.headers.get("Sec-Fetch-Dest"), "site": self.headers.get("Sec-Fetch-Site"),
                                         "mode": self.headers.get("Sec-Fetch-Mode")})
        body = b"rect { stroke: none; }" if self.path.split("?")[0].endswith(".css") else b""
        self.send_response(200); self.send_header("Content-Type", "text/css" if body else "text/plain")
        self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

    def log_message(self, *a):   # quiet: the box above is the record
        pass


class _DocSink4(ThreadingHTTPServer):
    daemon_threads = True
    address_family = socket.AF_INET


class _DocSink6(_DocSink4):
    address_family = socket.AF_INET6


class _Logger(BaseHTTPRequestHandler):
    """The second server: logs every request's path and the headers that say who asked (Referer, Sec-Fetch-Dest,
    Sec-Fetch-Site) into the class's list, answers a paint document for any .svg and a PNG for any .png, and serves its
    own log at /__log (not logged: the driver's wait reads it)."""
    log = None

    def do_GET(self):
        if self.path == "/__log":
            body = json.dumps(self.log).encode()
            self.send_response(200); self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body); return
        self.log.append({"path": self.path, "referer": self.headers.get("Referer"), "dest": self.headers.get("Sec-Fetch-Dest"),
                         "site": self.headers.get("Sec-Fetch-Site")})
        p = self.path.split("?")[0]
        if p.endswith(".svg"):
            body, ctype = (b'<svg xmlns="http://www.w3.org/2000/svg"><defs><pattern id="p" width="1" height="1"><rect width="1" '
                           b'height="1" fill="blue"/></pattern><mask id="m"><rect width="1" height="1" fill="white"/></mask></defs>'
                           b'</svg>'), "image/svg+xml"
        elif p.endswith(".png"):
            body, ctype = _png(), "image/png"
        else:
            body, ctype = b"", "text/plain"
        self.send_response(200); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(body)))
        self.end_headers(); self.wfile.write(body)

    def log_message(self, *a):   # quiet: the log above is the record
        pass


class PaintRefsOnKernelPages(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        try:
            cls._boot()
        except BaseException:          # a skip OR a failure: never leave a kernel or a lab behind
            cls.tearDownClass()
            raise

    @classmethod
    def _boot(cls):
        if not os.path.isdir(os.path.join(EXT, "node_modules", "playwright")):
            raise unittest.SkipTest("extension deps absent (npm ci not run here): the served lab needs them; CI's extension job has them and requires this file to run")
        probe = subprocess.run(["node", "-e", "const p=require(process.argv[1]);process.stdout.write(p.chromium.executablePath())",
                                os.path.join(EXT, "node_modules", "playwright")], capture_output=True, text=True)
        if probe.returncode != 0 or not os.path.exists(probe.stdout.strip()):
            raise unittest.SkipTest("no playwright browser on this box: the served lab needs one; CI's extension job installs Chromium and requires this file to run")
        cls.lab = tempfile.mkdtemp(prefix="paint-pages-")
        # the logger, with its stop registered before its start so it runs on every exit path (a failed boot included)
        cls.remote_log = []
        srv = ThreadingHTTPServer(("127.0.0.1", 0), type("Logger", (_Logger,), {"log": cls.remote_log}))
        thread = threading.Thread(target=srv.serve_forever, daemon=True)

        def end_remote():   # shutdown() waits for serve_forever to return, which a thread never started never does
            if thread.ident is not None:
                srv.shutdown()
            srv.server_close()
        cls.addClassCleanup(end_remote)
        thread.start()
        cls.log_url = "http://127.0.0.1:%d/__log" % srv.server_address[1]
        cls.remote = "http://%s:%d" % (REMOTE_HOST, srv.server_address[1])   # the viewer scene's name for the logger
        cls.notice_remote = "http://localhost:%d" % srv.server_address[1]     # the notice scene's: Sec-Fetch headers ride to it
        # the data: scene's sink, on both loopback families at one port, its stops registered before its starts
        cls.doc_box = {"lock": threading.Lock(), "requests": []}
        handler = type("DocSink", (_DocSink,), {"box": cls.doc_box})
        for _ in range(50):
            s4 = _DocSink4(("127.0.0.1", 0), handler)
            doc_servers = [s4]
            try:
                doc_servers.append(_DocSink6(("::1", s4.server_address[1]), handler))
            except OSError as e:
                if e.errno == errno.EADDRINUSE:
                    s4.server_close()
                    continue
            break
        else:
            raise AssertionError("no port was free on both loopback families for the data: scene's sink")
        for dsrv in doc_servers:
            dthread = threading.Thread(target=dsrv.serve_forever, daemon=True)

            def end_doc(dsrv=dsrv, dthread=dthread):
                if dthread.ident is not None:
                    dsrv.shutdown()
                dsrv.server_close()
            cls.addClassCleanup(end_doc)
            dthread.start()
        cls.doc_sink = "http://localhost:%d" % s4.server_address[1]
        cls.doc_v6 = len(doc_servers) == 2
        dist = os.path.join(cls.lab, "dist")
        lab_dist.copy_dist(dist)   # the checkout's ONE build of the bundles, copied under its lock (tests/lab_dist.py)
        state = os.path.join(cls.lab, "xdg", "romp")
        cwd = os.path.join(cls.lab, "proj")
        for d in ("names", "sdk", "states"):
            os.makedirs(os.path.join(state, d), exist_ok=True)
        os.makedirs(os.path.join(cwd, "docs"), exist_ok=True)
        Path(cwd, "docs", "figs-bare.md").write_text(_figures(cls.remote, "B-"))
        Path(cwd, "docs", "figs-framed.md").write_text(_figures(cls.remote, "F-"))
        cls.hover_scene = _doc_scene(cls.doc_sink, "DH-", "/media/romp-swirl-glyph.svg?own=dhover")   # relative: the hover strip has the page's base
        Path(cwd, DATA_FILE).write_text(cls.hover_scene["md"])
        cls.viewer_scene = _viewer_doc_scene(cls.doc_sink)
        Path(cwd, VIEWER_FILE).write_text(cls.viewer_scene["md"])
        Path(state, "names", SID).write_text("web\t%s\t#9cd2ff\t#0c1a2e\n" % cwd)
        Path(state, "sdk", SID + ".json").write_text(json.dumps(
            {"sid": SID, "name": "web", "cwd": cwd, "mode": "auto", "effort": "high", "lastSid": SID, "alive": True,
             "model": "claude-opus-5", "liveModel": "Opus 5"}))
        claude = os.path.join(cls.lab, "claude")
        proj = os.path.join(claude, "projects", re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(cwd)))
        os.makedirs(proj, exist_ok=True)
        reply = ("The sweep's figures are in docs/figs-bare.md, and the same set again in docs/figs-framed.md. "
                 "The encoded figures are in %s, and a copy to open is in %s." % (DATA_FILE, VIEWER_FILE))
        Path(proj, SID + ".jsonl").write_text(
            json.dumps({"type": "user", "uuid": U_UUID, "parentUuid": None, "timestamp": "2026-09-05T00:00:00.000Z", "sessionId": SID,
                        "message": {"role": "user", "content": "Where are the figures from the sweep?"}}) + "\n" +
            json.dumps({"type": "assistant", "uuid": A_UUID, "parentUuid": U_UUID, "timestamp": "2026-09-05T00:00:05.000Z", "sessionId": SID,
                        "message": {"role": "assistant", "model": "claude-opus-5", "content": [{"type": "text", "text": reply}], "stop_reason": "end_turn"}}) + "\n")
        cls.port, cls.token = _free_port(), "testtok-paintpages"
        cls.origin = "http://127.0.0.1:%d" % cls.port
        env = _lab.kernel_env(cls.lab, claude, dist, cls.port, cls.token, ROMP_HOST_NAME="TESTHOST")
        cls.klog = os.path.join(cls.lab, "kernel.log")
        cls.kernel = subprocess.Popen([os.path.join(BIN, "romp-kernel")], stdout=open(cls.klog, "w"), stderr=subprocess.STDOUT, env=env)
        for _ in range(120):
            try:
                urllib.request.urlopen(cls.origin + "/healthz", timeout=1)
                break
            except Exception:
                time.sleep(0.5)
        else:
            raise unittest.SkipTest("hermetic kernel never served /healthz here")

    @classmethod
    def tearDownClass(cls):
        k = getattr(cls, "kernel", None)
        if k:
            k.kill(); k.wait()
        shutil.rmtree(getattr(cls, "lab", ""), ignore_errors=True)

    def _drive(self, scene, extra):
        cfg = os.path.join(self.lab, "cfg-%s.json" % scene)
        with open(cfg, "w") as f:
            json.dump(dict({"scene": scene, "remote": self.remote, "remoteHost": REMOTE_HOST, "logUrl": self.log_url, "sid": SID}, **extra), f)
        driver = os.path.join(self.lab, "driver.mjs")
        with open(driver, "w") as f:
            f.write(DRIVER)
        p = subprocess.run(["node", driver], capture_output=True, text=True, timeout=300,
                           env=dict(os.environ, EXT_PKG=os.path.join(EXT, "package.json"), CFG=cfg))
        if p.returncode == 3:
            raise unittest.SkipTest("no playwright browser on this box: the served lab needs one; CI's extension job installs Chromium and requires this file to run")
        self.assertEqual(p.returncode, 0, "driver failed:\n" + p.stdout[-3000:] + p.stderr[-3000:] + "\nkernel:\n" + open(self.klog).read()[-1500:])
        line = next((ln for ln in p.stdout.splitlines() if ln.startswith("RESULT:")), None)
        self.assertIsNotNone(line, "driver printed no result:\n" + p.stdout[-3000:])
        return json.loads(line[len("RESULT:"):])

    def _logged(self, prefix):
        return [l for l in list(self.remote_log) if l["path"].startswith("/" + prefix)]

    def test_a_data_document_in_a_notice_card_or_a_hover_preview_reaches_no_other_host(self):
        # the data: rule on the kernel's own pages, in every engine that ran (Chromium always, Firefox and WebKit when
        # ROMP_BROWSER_ENGINES names them): the module docstring's third scene
        engines = _engines()
        notice = _doc_scene(self.doc_sink, "DN-", self.origin + "/media/romp-swirl-glyph.svg?own=dnotice")
        req = urllib.request.Request(self.origin + "/notice", method="POST",
                                     data=json.dumps({"id": SID, "key": "paint-data", "title": "The encoded figures are ready",
                                                      "producer": "figure", "body": notice["md"]}).encode(),
                                     headers={"X-Romp-Token": self.token, "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            posted = json.loads(resp.read() or b"{}")
        self.assertTrue(posted.get("ok"), "the kernel accepted the notice: %r" % posted)
        scenes = {"notice": notice, "hover": self.hover_scene}
        ran = []
        for engine in engines:
            with self.doc_box["lock"]:            # one engine's record at a time
                self.doc_box["requests"].clear()
            cfgp = os.path.join(self.lab, "cfg-data-%s.json" % engine)
            with open(cfgp, "w") as f:
                json.dump({"engine": engine, "sid": SID, "file": DATA_FILE, "sink": self.doc_sink,
                           "logUrl": "http://127.0.0.1:%d/__doclog" % int(self.doc_sink.rsplit(":", 1)[1]),
                           "feed": self.origin + "/feed?token=" + self.token, "chat": self.origin + "/chat?token=" + self.token,
                           "itemId": "notice:%s:paint-data:%s" % (SID, posted["notice"]["rev"]), "controlLoads": CONTROL_LOADS[engine],
                           "notice": {k: notice[k] for k in ("shapes", "kept", "control", "controlFiles")},
                           "hover": {k: self.hover_scene[k] for k in ("shapes", "kept", "control", "controlFiles")}}, f)
            driver = os.path.join(self.lab, "doc-driver.mjs")
            with open(driver, "w") as f:
                f.write(DOC_DRIVER)
            p = subprocess.run(["node", driver], capture_output=True, text=True, timeout=300,
                               env=dict(os.environ, EXT_PKG=os.path.join(EXT, "package.json"), CFG=cfgp))
            if p.returncode == 3 and engine == "chromium":
                raise unittest.SkipTest("no playwright browser on this box: the served lab needs one; CI's extension job installs Chromium and requires this file to run")
            if p.returncode == 3:
                raise AssertionError("ROMP_BROWSER_ENGINES names %s, and it did not launch here (a named engine is a failure, never a skip):\n%s"
                                     % (engine, p.stderr[-2000:]))
            self.assertEqual(p.returncode, 0, "the %s driver failed:\n%s%s\nkernel:\n%s" % (engine, p.stdout[-3000:], p.stderr[-3000:], open(self.klog).read()[-1500:]))
            line = next((ln for ln in p.stdout.splitlines() if ln.startswith("RESULT:")), None)
            self.assertIsNotNone(line, "the %s driver printed no result:\n%s" % (engine, p.stdout[-3000:]))
            r = json.loads(line[len("RESULT:"):])
            ran.append("%s %s" % (r["engine"], r["version"]))
            time.sleep(0.3)                        # the sink's handler threads finish logging the reach before it is read
            with self.doc_box["lock"]:
                log = list(self.doc_box["requests"])
            paths = [l["path"].split("?")[0] for l in log]
            print("DATA-DOCS %s: %s" % (engine, json.dumps({"driver": r, "v6": self.doc_v6})), file=sys.stderr)
            with self.subTest(engine + ": no page error"):
                self.assertEqual(r["errors"], [], "no page error")
            with self.subTest(engine + ": the unsanitized controls made the loads this engine makes"):
                want = sorted(notice["controlFiles"] + self.hover_scene["controlFiles"]) if CONTROL_LOADS[engine] else []
                self.assertEqual(sorted({q for q in paths if q.startswith("/CD")}), want,
                                 "the controls' @imports at the sink (%s loads a data: paint document: %s)" % (engine, CONTROL_LOADS[engine]))
            with self.subTest(engine + ": the page reached the sink, once, after the record"):
                self.assertEqual(r["reach"], "ok", "the feed page's no-cors fetch to the sink completed")
                self.assertEqual([q for q in paths if q.startswith("/reach-")], ["/reach-" + engine], "the sink logged the reach once")
            for name, scene in scenes.items():
                got = r[name]
                with self.subTest(engine + ", " + name + ": the page's own mask reference was requested"):
                    self.assertTrue(r["own" + name.capitalize()], "the same-origin mask was requested from the kernel (%s ms): the card rendered "
                                    "and this engine fetched a paint reference the pass keeps" % r[name + "OwnMs"])
                with self.subTest(engine + ", " + name + ": no request reached the sink from a data: document in the card"):
                    files = [sh["file"] for sh in scene["shapes"] + scene["kept"] if sh["file"]]
                    self.assertEqual([l for l in log if l["path"].split("?")[0] in files], [],
                                     "a data: document in the %s made a request to another host (each with its path, Referer class and Sec-Fetch headers)" % name)
                with self.subTest(engine + ", " + name + ": every data: document reference is removed from its element, which stays"):
                    self.assertEqual([x for x in got["shapes"] if x["value"] is not None], [], "each data: document reference is removed")
                with self.subTest(engine + ", " + name + ": the controls stay as written"):
                    self.assertEqual([x["value"] for x in got["kept"]], [k["value"] for k in scene["kept"]],
                                     "the raster mask, url(#g), the page's own mask and the raster-labelled svg body stay as written")
                if engine in MASK_DRAWS:
                    with self.subTest(engine + ", " + name + ": the kept raster data: mask draws"):
                        px = got["pixels"] or {}
                        # read as a contrast between the halves, not as pure red: the notice body is drawn at 0.9 opacity
                        # over its card, so its red is dimmer than the hover card's
                        redness = lambda c: c[0] - max(c[1], c[2]) if c else 0
                        self.assertTrue(redness(px.get("left")) - redness(px.get("right")) >= 30 and redness(px.get("right")) < 15,
                                        "the masked rect's left half is painted red and its right half is not: %r" % px)
            with self.subTest(engine + ", hover: the card was still up when the record was read"):
                self.assertTrue(r["hoverUp"], "the hover card stayed up through the drain")
        print("DATA-DOCS ENGINES RAN: %s (ROMP_BROWSER_ENGINES=%r; Firefox and WebKit run only when it names them)"
              % (", ".join(ran), os.environ.get("ROMP_BROWSER_ENGINES", "")), file=sys.stderr)
        self.assertEqual([x.split(" ")[0] for x in ran], engines, "engines that ran: %s (ROMP_BROWSER_ENGINES=%r)" % (", ".join(ran), os.environ.get("ROMP_BROWSER_ENGINES", "")))

    def test_a_data_document_in_a_viewed_file_is_dropped_and_reaches_no_other_host(self):
        # the data: rule in the file viewer (the module docstring's fourth scene): dropped as on the other surfaces, never gated,
        # in every engine that ran (Chromium always, Firefox and WebKit when ROMP_BROWSER_ENGINES names them)
        engines = _engines()
        scene = self.viewer_scene
        ran = []
        for engine in engines:
            with self.doc_box["lock"]:            # one engine's record at a time
                self.doc_box["requests"].clear()
            cfgp = os.path.join(self.lab, "cfg-viewer-data-%s.json" % engine)
            with open(cfgp, "w") as f:
                json.dump({"scene": "viewer", "engine": engine, "sid": SID, "file": VIEWER_FILE, "sink": self.doc_sink, "unlisted": UNLISTED,
                           "logUrl": "http://127.0.0.1:%d/__doclog" % int(self.doc_sink.rsplit(":", 1)[1]),
                           "chat": self.origin + "/chat?token=" + self.token, "controlLoads": CONTROL_LOADS[engine],
                           "viewer": {k: scene[k] for k in ("shapes", "kept", "control", "controlFiles")}}, f)
            driver = os.path.join(self.lab, "doc-driver.mjs")
            with open(driver, "w") as f:
                f.write(DOC_DRIVER)
            p = subprocess.run(["node", driver], capture_output=True, text=True, timeout=300,
                               env=dict(os.environ, EXT_PKG=os.path.join(EXT, "package.json"), CFG=cfgp))
            if p.returncode == 3 and engine == "chromium":
                raise unittest.SkipTest("no playwright browser on this box: the served lab needs one; CI's extension job installs Chromium and requires this file to run")
            if p.returncode == 3:
                raise AssertionError("ROMP_BROWSER_ENGINES names %s, and it did not launch here (a named engine is a failure, never a skip):\n%s"
                                     % (engine, p.stderr[-2000:]))
            self.assertEqual(p.returncode, 0, "the %s driver failed:\n%s%s\nkernel:\n%s" % (engine, p.stdout[-3000:], p.stderr[-3000:], open(self.klog).read()[-1500:]))
            line = next((ln for ln in p.stdout.splitlines() if ln.startswith("RESULT:")), None)
            self.assertIsNotNone(line, "the %s driver printed no result:\n%s" % (engine, p.stdout[-3000:]))
            r = json.loads(line[len("RESULT:"):])
            ran.append("%s %s" % (r["engine"], r["version"]))
            time.sleep(0.3)                        # the sink's handler threads finish logging the reach before it is read
            with self.doc_box["lock"]:
                log = list(self.doc_box["requests"])
            paths = [l["path"].split("?")[0] for l in log]
            files = [sh["file"] for sh in scene["shapes"] + scene["kept"] if sh["file"]] + [scene["rider"]["file"]]
            print("VIEWER-DATA-DOCS %s: %s" % (engine, json.dumps({"driver": r, "v6": self.doc_v6})), file=sys.stderr)
            with self.subTest(engine + ": no page error"):
                self.assertEqual(r["errors"], [], "no page error")
            with self.subTest(engine + ": no hover card rendered the file, so the sink's record is the viewer's"):
                self.assertEqual([r["open"]["hoverUp"], r["after"]["hoverUp"]], [False, False], "the hover card was down at the open and after the click")
            with self.subTest(engine + ": the unsanitized control made the loads this engine makes"):
                want = sorted(scene["controlFiles"]) if CONTROL_LOADS[engine] else []
                self.assertEqual(sorted({q for q in paths if q.startswith("/CDV-")}), want,
                                 "the control's @imports at the sink (%s loads a data: paint document: %s)" % (engine, CONTROL_LOADS[engine]))
            with self.subTest(engine + ": the page reached the sink, once, after the record"):
                self.assertEqual(r["reach"], "ok", "the chat page's no-cors fetch to the sink completed")
                self.assertEqual([q for q in paths if q.startswith("/reach-")], ["/reach-" + engine], "the sink logged the reach once")
            with self.subTest(engine + ": the page's own mask reference was requested"):
                self.assertTrue(r["own"], "the same-origin mask was requested from the kernel (%s ms): the file rendered in the viewer "
                                "and this engine fetched a paint reference the viewer keeps" % r["ownMs"])
            with self.subTest(engine + ": no request reached the sink from a data: document in the viewed file, at the open or after the click"):
                self.assertEqual([l for l in r["openLog"] if l["path"].split("?")[0] in files], [],
                                 "a data: document in the viewed file made a request to another host as the file opened (each with its path, Referer class and Sec-Fetch headers)")
                self.assertEqual([l for l in log if l["path"].split("?")[0] in files], [],
                                 "a data: document in the viewed file made a request to another host by the end of the record, the click on the rider's placeholder included")
            with self.subTest(engine + ": every data: document reference is removed from its element and held aside nowhere"):
                self.assertEqual([x for x in r["open"]["shapes"] if x["value"] is not None], [], "each data: document reference is removed at the open")
                self.assertEqual([x for x in r["after"]["shapes"] if x["value"] is not None], [], "and is still gone after the click")
                self.assertEqual([r["open"]["heldData"], r["after"]["heldData"]], [[], []], "no attribute under the viewer holds a data: reference aside for a click to restore")
            with self.subTest(engine + ": the rider's data: document is dropped, not held with its gated fill, and the click brings back the fill alone"):
                self.assertEqual(r["open"]["rider"], {"fill": None, "stroke": None, "heldStroke": None},
                                 "at the open the rider's fill is held behind its placeholder and its data: stroke is neither on the rect nor held aside")
                self.assertEqual(r["placeholders"], 1, "one placeholder names %s, and the driver clicked it" % UNLISTED)
                self.assertEqual(r["after"]["rider"], {"fill": scene["rider"]["fill"], "stroke": None, "heldStroke": None},
                                 "after the click the fill is back and the data: stroke is not")
            with self.subTest(engine + ": the viewer gates no data: reference (every placeholder names the rider's host)"):
                self.assertEqual(r["open"]["hosts"], [UNLISTED], "the placeholders at the open, by the hosts each names")
            with self.subTest(engine + ": the controls stay as written"):
                self.assertEqual([x["value"] for x in r["open"]["kept"]], [k["value"] for k in scene["kept"]],
                                 "the raster mask, url(#g), the page's own mask and the raster-labelled svg body stay as written")
            if engine in MASK_DRAWS:
                with self.subTest(engine + ": the kept raster data: mask draws"):
                    px = r["open"]["pixels"] or {}
                    redness = lambda c: c[0] - max(c[1], c[2]) if c else 0
                    self.assertTrue(redness(px.get("left")) - redness(px.get("right")) >= 30 and redness(px.get("right")) < 15,
                                    "the masked rect's left half is painted red and its right half is not: %r" % px)
        print("VIEWER-DATA-DOCS ENGINES RAN: %s (ROMP_BROWSER_ENGINES=%r; Firefox and WebKit run only when it names them)"
              % (", ".join(ran), os.environ.get("ROMP_BROWSER_ENGINES", "")), file=sys.stderr)
        self.assertEqual([x.split(" ")[0] for x in ran], engines, "engines that ran: %s (ROMP_BROWSER_ENGINES=%r)" % (", ".join(ran), os.environ.get("ROMP_BROWSER_ENGINES", "")))

    def test_a_notice_card_s_paint_references_reach_no_other_host(self):
        req = urllib.request.Request(self.origin + "/notice", method="POST",
                                     data=json.dumps({"id": SID, "key": "paint", "title": "A new version of the accuracy figure is ready",
                                                      "producer": "figure", "body": _notice_body(self.notice_remote, self.origin)}).encode(),
                                     headers={"X-Romp-Token": self.token, "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            posted = json.loads(resp.read() or b"{}")
        self.assertTrue(posted.get("ok"), "the kernel accepted the notice: %r" % posted)
        own = self.origin + "/media/romp-swirl-glyph.svg?own=notice"
        r = self._drive("notice", {"remote": self.notice_remote, "feed": self.origin + "/feed?token=" + self.token, "own": own,
                                   "itemId": "notice:%s:paint:%s" % (SID, posted["notice"]["rev"])})
        card = r["card"] or {}
        attrs = card.get("attrs") or []
        print("NOTICE:", json.dumps({"driver": r, "log": self._logged("N-")}), file=sys.stderr)
        with self.subTest("no page error"):
            self.assertEqual(r["errors"], [], "no page error")
        with self.subTest("the feed page was opened bare"):
            self.assertIn("token=" + self.token, r["pageUrl"], "the feed page's own address carries the token")
        with self.subTest("the card is on the board"):
            self.assertTrue(card.get("vis"), "the notice card is on the board and shown: %r" % r["card"])
        with self.subTest("the body's inline svgs survived the sanitizer"):
            self.assertGreaterEqual(card.get("svgs", 0), 7, "the body's seven inline svgs are in the card: %s" % card.get("html"))
        # the positive control: the card painted and this browser fetched the paint reference the pass keeps
        with self.subTest("the absolute same-origin control was requested from the kernel"):
            self.assertTrue(r["own"] and r["own"][0]["referrerPolicy"] == "same-origin",
                            "the same-origin paint reference was requested and the kernel answered it (%s ms): %r" % (r["ownWaitMs"], r["own"]))
        with self.subTest("the absolute same-origin control stands in the card as written"):
            self.assertIn({"at": "rect[fill]", "value": "url(%s#p)" % own}, attrs, "the same-origin reference stands in the card")
        # the fix: sanitizeMd's paint pass and the strip's paint arm removed every remote url() on the inert body
        with self.subTest("no request reached the logger"):
            self.assertEqual(self._logged("N-"), [], "the notice card's body made requests to another host; each with its path, "
                             "Referer, Sec-Fetch-Dest and Sec-Fetch-Site")
        with self.subTest("no attribute in the card names the logger"):
            self.assertEqual([a for a in attrs if self.notice_remote in a["value"]], [], "an attribute in the card names the logger")
        with self.subTest("the page reached the logger"):
            self.assertEqual(r["reach"], "ok", "the feed page's no-cors fetch to the logger completed")
        with self.subTest("the logger logged the reach once"):
            self.assertEqual([l["path"] for l in self.remote_log if l["path"] == "/reach-notice"], ["/reach-notice"], "the logger logged the reach fetch once")

    def test_a_figure_the_viewer_loads_on_a_click_sends_at_most_the_page_s_origin(self):
        r = self._drive("viewer", {"chat": self.origin + "/chat?token=" + self.token, "shell": self.origin + "/?token=" + self.token,
                                   "files": {"bare": "docs/figs-bare.md", "framed": "docs/figs-framed.md"},
                                   "awaited": list(VIEWER_AWAITED)})
        print("VIEWER:", json.dumps({"driver": r, "log": {n: self._logged(p) for n, p in (("bare", "B-"), ("framed", "F-"))}}), file=sys.stderr)
        with self.subTest("no page error"):
            self.assertEqual(r["errors"], [], "no page error")
        with self.subTest("the bare chat page's address carries the token"):
            self.assertIn("token=" + self.token, r["bare"]["url"], "the bare chat page's own address carries the token")
        with self.subTest("the framed chat pane's address carries no token"):
            self.assertNotIn("token=", r["framed"]["url"], "the framed chat pane's address carries no token")
        with self.subTest("the shell dropped the token from its address"):
            self.assertNotIn("token=", r["framed"]["shellUrl"], "the shell dropped the token from its address")
        for name, prefix in (("bare", "B-"), ("framed", "F-")):
            s = r[name]
            logged = self._logged(prefix)
            paths = [l["path"] for l in logged]
            with self.subTest(name + ": the viewer gated the logger's host"):
                self.assertEqual(s["gatedHosts"][:1], [REMOTE_HOST], "the viewer gated the logger's host: %r" % s["gatedHosts"])
            with self.subTest(name + ": nothing reached the logger before the click"):
                self.assertEqual(s["beforeClick"], [], "no figure reached the logger before the click")
            with self.subTest(name + ": one click restored every figure of the host"):
                self.assertEqual(s["leftGated"], 0, "one click restored every figure of the host")
            with self.subTest(name + ": the awaited figures reached the logger after the click"):
                self.assertEqual([n for n in VIEWER_AWAITED if "/" + prefix + n not in paths], [],
                                 "figures that did not reach the logger after the click (%s ms): %r" % (s["waitMs"], logged))
            with self.subTest(name + ": each request carried no Referer or the page's origin alone"):
                self.assertEqual([l for l in logged if l["referer"] not in (None, self.origin + "/")], [],
                                 "a figure's request named more of the page than its origin (a path, a query, the token)")
        with self.subTest("the page reached the logger"):
            self.assertEqual(r["reach"], "ok", "the chat page's no-cors fetch to the logger completed")
        with self.subTest("the logger logged the reach once"):
            self.assertEqual([l["path"] for l in self.remote_log if l["path"] == "/reach-viewer"], ["/reach-viewer"], "the logger logged the reach fetch once")

if __name__ == "__main__":
    unittest.main()
