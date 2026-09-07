#!/usr/bin/env python3
"""The "Files" pane (app=files): the file VIEWER as its own column of the dashboard, beside Chat,
Sessions, Outline, Feed and Waiting, with the gear's "File links open in" gaining a third value
("pane") that routes a chat file-link click into it. Kernel side, pinned here:

- the pane is NOT a feed consumer. The viewer is request/response (HTTP /file for the bytes; the
  saveFile / fileGitLink / listDir ops answer the SENDING client), so app=files is absent from the
  feed send set, the send loop and the ready fast-serve — _push builds nothing for it — and present
  only where a live pane must count: the conserve-memory viewer list.
- the /files page: the chat's styles.css for the viewer's dress, files-pane.css read live for the
  layout and the pane-resident variant (body.fileview-pane), NO romp loader (an empty pane is not a
  loading state), the shim with the ready hold and the stale opt-out (NO_STALE_CAP — a page with no
  kernel-pushed view never arms the shared "view may be stale" prompt), federation.js before files.js.
- the shell: a sixth pane after Waiting, default OFF, with its gutter, grow var, focus/Esc/mobile
  wiring and the _PANE_ORDER label "Files"; the viewFile relay's `pane` branch, which brings the
  pane forward and forwards the click (identity included) into it — with none of the feed route's
  was-off / ack / restore machinery, since the pane stays up.

SYNTHETIC fixtures only (the notes-api demo world); no session data is minted here.
"""
import os
import re
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest import mock

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ["ROMP_SERVE_TOKEN"] = "testtok"
km = SourceFileLoader("romp_kernel_fpane", os.path.join(BIN, "romp-kernel")).load_module()
SRC = open(os.path.join(BIN, "romp-kernel")).read()
UI = Path(BIN).parent / "ui" / "webview"


class Plumbing(unittest.TestCase):
    """app=files is a viewer to the kernel, not a feed client: keepalives and its own op replies ride
    its socket, nothing is built for it, and it counts as a live dashboard for conserve-memory."""

    def test_files_is_not_in_the_feed_send_set_loop_or_ready_serve(self):
        # the feed-consumer tuples are verbatim from before the pane: adding "files" to any of them would
        # build and ship a feed frame nobody reads
        self.assertIn('want_feed = any(c["app"] in ("feed", "fleet", "waiting", "chat") for c in targets)', SRC)
        self.assertIn('if c["app"] in ("feed", "fleet", "waiting"):', SRC)
        self.assertIn('served = client.get("app") in ("feed", "fleet", "waiting") and _send_feed_now(client)', SRC)
        self.assertIn('if not (served and client.get("app") in ("feed", "waiting")):', SRC)
        push = SRC[SRC.index("def _push(targets"):]
        push = push[:push.index("\ndef ")]
        self.assertNotIn('"files"', push, "_push names every app it builds for; the Files pane is not one")

    def test_the_socket_accepts_any_app_name(self):
        # the handshake has no allowlist, so app=files connects on a kernel exactly as the other panes do
        self.assertIn('app = (q.get("app") or ["chat"])[0]', SRC)

    def test_an_open_files_pane_counts_as_a_viewer_for_conserve_memory(self):
        self.assertIn('c.get("app") in ("chat", "fleet", "timeline", "feed", "waiting", "files")', SRC)

    def test_the_page_carries_the_hold_and_the_stale_opt_out_the_shared_dress_and_no_loader(self):
        page = km._files_page()
        self.assertIn('_shim("files", v, caps=READY_GATE_CAP + "," + NO_STALE_CAP)', SRC)
        self.assertNotIn('_shim("files", v, caps=FEED_DELTA_CAP', SRC)
        self.assertIn("app=files", page)
        self.assertIn('var CAPS="readyGate,noStale";', page)
        self.assertIn("/dist/styles.css", page)                     # the viewer's .fileview-* dress
        self.assertIn("<body class=fileview-pane>", page)           # keys the pane-resident variant
        self.assertIn("<div id=files-empty></div>", page)
        self.assertIn("/dist/federation.js", page)
        self.assertIn("/dist/files.js", page)
        self.assertLess(page.index("/dist/federation.js"), page.index("/dist/files.js"), "manager before the bundle")
        self.assertNotIn("id=pane-spin", page, "an empty pane is not a loading state")
        self.assertNotIn("rel=manifest", page)
        self.assertIn('if p == "/files":', SRC)
        self.assertIn("_files_page()", SRC)
        # the sheet is read live, like fleet-pane.css; a missing one fails loudly on the page, never blank
        css = (UI / "files-pane.css").read_text()
        self.assertIn(css.splitlines()[-1], page)
        with mock.patch.object(Path, "read_text", side_effect=OSError("gone")):
            self.assertIn("needs the ui/ modules", km._files_page())

    def test_the_page_opts_out_of_the_stale_prompt_and_only_this_page_does(self):
        """The shim arms the "connection lost — what you see may be stale" prompt on an unannounced reconnect
        and retires it on the kernel's connect-time push: the first non-keepalive frame. app=files gets no
        such push (nothing is built for it — the Plumbing pins above), so its arm never cleared and the
        second keepalive raised the shell's shared banner dashboard-wide after every unannounced reconnect
        (the 2026-09-03 review) — for a file fetched over HTTP on demand, which a dropped socket cannot make
        stale. The page announces NO_STALE_CAP; the shim reads it from CAPS and neither arms nor retires
        (the executed state machine is pane-shim-stale.test.ts). The build-drift prompt is a separate
        raise and stands. Every other pane has a live pushed view and keeps the arm."""
        self.assertEqual(km.NO_STALE_CAP, "noStale")
        page = km._files_page()
        self.assertIn('var NOSTALE=CAPS.split(",").indexOf("noStale")>=0;', page, "the shim reads the cap off CAPS")
        self.assertIn("function armStale(why){if(NOSTALE)return;stalePending=why;staleKa=0;}", page)
        self.assertIn('function clearStale(){stalePending="";   // armed but never shown → nothing to see\nif(NOSTALE)return;', page)
        self.assertIn("function raiseBuild(){if(buildRaised)return;buildRaised=true;", page, "the build prompt is not gated")
        self.assertIn("&caps=", km._shim("files", 1, caps=km.NO_STALE_CAP), "the cap rides the ws URL like the others")
        # the one page that passes it; the other pane pages keep the arm exactly as they were
        shims = re.findall(r'_shim\("(\w+)", v, caps=([^)]*)\)', SRC)
        self.assertEqual([app for app, caps in shims if "NO_STALE_CAP" in caps], ["files"])
        self.assertEqual(sorted(app for app, caps in shims), ["chat", "feed", "files", "fleet", "timeline", "waiting"])
        for app in ("chat", "feed", "fleet", "waiting", "timeline"):
            self.assertNotIn("noStale", km._shim(app, 1, caps=km.FEED_DELTA_CAP + "," + km.READY_GATE_CAP).split("var NOSTALE")[0])

    def test_the_editor_chunk_derives_from_the_pages_own_bundle_tag(self):
        # file-view.ts loads its CodeMirror chunk from a URL rewritten off the page's running bundle
        # <script src>. The Files page's bundle must be one that derivation recognizes, or every Edit in the
        # pane rejects with the raw "no bundle script tag" error and falls to the textarea (the 2026-09-03
        # review). The pattern is lifted from the source and run against the tags this page emits.
        view = (UI / "file-view.ts").read_text()
        m = re.search(r"\.find\(\(u\) => /(.+?)/\.test\(u\)\)", view)
        self.assertIsNotNone(m, "the derivation's find literal is where the pin expects it")
        pat = re.compile(m.group(1))
        srcs = re.findall(r"<script src=([^ >]+)", km._files_page())
        self.assertTrue(srcs)
        hits = [s for s in srcs if pat.search("http://TESTHOST:1" + s)]   # the browser's absolute .src
        self.assertEqual(hits, [s for s in srcs if s.startswith("/dist/files.js?v=")], "the bundle, and only the bundle")

    def test_the_pane_resident_variant_lives_only_in_the_pane_sheet(self):
        # the modal variant is mirrored byte-equal in styles.css and feed.css (fileview-parity.test.ts);
        # the pane's override must not enter either, or the mirrors drift
        css = (UI / "files-pane.css").read_text()
        self.assertIn("body.fileview-pane #romp-fileview{position:relative;inset:auto;flex:1 1 auto;min-height:0;background:none}", css)
        self.assertIn("body.fileview-pane .fileview{width:100%;height:100%;border:0;border-radius:0;box-shadow:none}", css)
        for sheet in ("styles.css", "feed.css"):
            self.assertNotIn("fileview-pane", (UI / sheet).read_text(), sheet)
        self.assertNotIn("fleet", css.lower(), "no fleet vocabulary in the new sheet")


class Shell(unittest.TestCase):
    """The dashboard grows a sixth pane: the far-right column after Waiting, OFF by default (the viewFile
    relay brings it forward when a click routes there), with its own gutter, grow var, and every
    hand-written pane list in the landing JS extended — focus ring, Alt+Arrow columns, Esc wiring, the
    Log's pane names, the mobile tab map, the pane controller. One label, "Files", from _PANE_ORDER."""

    def setUp(self):
        self.html = km._landing()

    def test_the_pane_is_in_the_one_ordering_last(self):
        self.assertEqual(km._PANE_ORDER[-1], ("files", "Files"))
        self.assertIn("<div class=rail-btn data-pane=files>Files</div>", self.html)
        self.assertIn("<button data-pane=files>Files</button>", self.html)

    def test_the_column_sits_after_waiting_with_its_gutter_and_grow_var(self):
        self.assertIn('<div class=gv id=gv-d></div><div class=pane id=files-pane><iframe id=f-files src=/files></iframe></div>',
                      self.html.replace('"\n            "', ""))
        self.assertLess(self.html.index("id=waiting-pane"), self.html.index("id=gv-d"))
        self.assertLess(self.html.index("id=gv-d"), self.html.index("id=files-pane"))
        self.assertLess(self.html.index("id=files-pane"), self.html.index("id=gh"), "before the timeline band")
        self.assertIn("#files-pane{flex:var(--g-files,40) 1 0}", self.html)
        self.assertIn("body:not(.po-files) #files-pane{display:none}", self.html)
        self.assertIn("body:not(.po-files) #gv-d,body:not(.po-chat):not(.po-fleet):not(.po-feed):not(.po-waiting) #gv-d{display:none}", self.html)

    def test_off_by_default_and_toggled_by_the_controller(self):
        self.assertIn("<body class='po-chat po-feed po-timeline'>", self.html)   # not po-files
        self.assertIn("po={chat:true,fleet:false,feed:true,timeline:true,waiting:false,files:false}", self.html)
        self.assertIn("po={chat:false,fleet:false,feed:false,timeline:false,waiting:false,files:false}", self.html)   # the ?panes= reset
        self.assertIn("document.body.classList.toggle('po-files',!!po.files)", self.html)
        self.assertIn("files:'Files pane'", self.html)   # the rail tooltip's words

    def test_every_pane_list_in_the_landing_js_names_it(self):
        self.assertIn("'f-files':'files-pane'", km._LANDING_FOCUS_JS)
        self.assertIn("var COLS=['f-chat','f-fleet','f-feed','f-waiting','f-files']", km._LANDING_FOCUS_JS)
        self.assertIn("['f-chat','f-fleet','f-feed','f-waiting','f-files','f-timeline'].forEach", self.html)   # Esc wiring
        self.assertIn("files:'Files'", km._LANDING_ERRS_JS)   # the Log's connection-lost label
        self.assertIn("files:document.getElementById('f-files')", km._LANDING_MOBILE_JS)
        self.assertIn("var PANES=['chat-pane','fleet-pane','feed-pane','waiting-pane','files-pane'];", self.html)
        self.assertIn("grow={chat:60,fleet:34,feed:40,waiting:34,files:40}", self.html)
        self.assertIn("id==='waiting-pane'?'waiting':'files'", self.html)
        self.assertIn("gutter('gv-d',function(){var c=document.body.classList;return c.contains('po-waiting')?'waiting-pane':"
                      "c.contains('po-feed')?'feed-pane':c.contains('po-fleet')?'fleet-pane':'chat-pane';},'files-pane');", self.html)

    def test_mobile_tab_and_the_palette_command(self):
        self.assertIn("#chat-pane,#fleet-pane,#feed-pane,#waiting-pane,#files-pane,#tl-pane{display:contents!important}", self.html)
        self.assertIn("#f-chat.m-on,#f-fleet.m-on,#f-feed.m-on,#f-waiting.m-on,#f-files.m-on{display:block}", self.html)
        pal = (UI / "palette-main.ts").read_text()
        self.assertIn('["files", "files", "Files"]', pal)
        self.assertIn('"f-files"', pal)


class Relay(unittest.TestCase):
    """The shell's viewFile relay gains a `pane` branch: a click routed to the Files pane brings that pane
    forward (desktop toggle + phone tab) and forwards the click, identity included, into #f-files — with
    none of the feed route's was-off stash, viewFileOpened ack or viewFileClosed restore, because the
    pane stays up. The feed route is untouched, and a message without `pane` still goes to the feed."""

    def test_the_pane_branch_brings_the_files_pane_forward_and_forwards_the_identity(self):
        js = km._LANDING_SETTINGS_JS
        head = "if(m.romp==='viewFile'&&m.pane==='pane'){var ff=document.getElementById('f-files');"
        self.assertIn(head, js)
        branch = js.split(head)[1].split("else if(m.romp==='viewFile')")[0]
        # the feed route's own comment block sits between the two branches and names its machinery; the CODE
        # of this branch must not
        branch = "\n".join(l for l in branch.splitlines() if not l.lstrip().startswith("//"))
        self.assertIn("window.__rompPaneToggle&&window.__rompPaneToggle('files',true)", branch)
        self.assertIn("window.__rompMobileTab&&window.__rompMobileTab('files')", branch)
        self.assertIn("postMessage({romp:'viewFile',path:m.path,sid:m.sid,identity:m.identity||null,todoId:m.todoId||null},'*')", branch)
        for tok in ("__rompFeedWasOff", "viewFileOpened", "viewFileClosed", "'f-feed'"):
            self.assertNotIn(tok, branch, tok + " belongs to the feed route")

    def test_the_pane_branch_forwards_the_todo_id_and_the_feed_route_does_not(self):
        """The Waiting-on-you pane's detail link (plans/file-review.md, Slice 0) posts the same viewFile with
        `todoId` — the user todo the path came from; the shell forwards it as-is (null for a chat click, which
        carries none) so the viewer can tie its work back to the todo. The feed route, which no todo link
        uses, forwards path + sid only, as before."""
        js = km._LANDING_SETTINGS_JS
        head = "if(m.romp==='viewFile'&&m.pane==='pane'){var ff=document.getElementById('f-files');"
        pane = js.split(head)[1].split("else if(m.romp==='viewFile')")[0]
        code = "\n".join(l for l in pane.splitlines() if not l.lstrip().startswith("//"))
        self.assertIn("todoId:m.todoId||null", code)
        self.assertEqual(code.count("postMessage("), 1, "one forward, carrying the whole message")
        feed = js.split("else if(m.romp==='viewFile'){var vf=document.getElementById('f-feed');")[1].split("if(m.romp==='viewFileOpened')")[0]
        self.assertNotIn("todoId", feed)
        # the receiving end reads it as a string or nothing, and hands it to the viewer's open
        files = (UI / "files.ts").read_text()
        self.assertIn('typeof m.todoId === "string" ? m.todoId : null', files)
        self.assertIn("openFileView(path, sid, { todoId })", files)

    def test_the_relay_comment_names_the_todo_id_referent_a_user_todo_never_an_ask(self):
        """CONTEXT.md (User todo, Avoid) lists "ask" because the feed payload's `asks` field already means the
        card list. The relay comment above the pane branch is where the shell defines `todoId`, and it must
        say "the todo", not "the ask" (ui/webview/file-view-vocab.test.ts pins the viewer's twin definition),
        so the two definitions a reader sees side by side cannot drift apart."""
        js = km._LANDING_SETTINGS_JS
        head = "if(m.romp==='viewFile'&&m.pane==='pane'){var ff=document.getElementById('f-files');"
        lines = js.split(head)[0].rstrip("\n").split("\n")
        start = len(lines)
        while start > 0 and lines[start - 1].lstrip().startswith("//"):
            start -= 1
        comment = "\n".join(lines[start:])
        self.assertIn("todoId", comment, "the comment directly above the pane branch defines todoId")
        self.assertRegex(comment, r"\buser todo\b", "todoId is the user todo the path came from")
        self.assertNotRegex(comment, r"(?i)\bask\b", "CONTEXT.md (User todo, Avoid): `asks` already means the feed's card list")

    def test_the_feed_route_is_the_else_branch_and_unchanged(self):
        js = km._LANDING_SETTINGS_JS
        self.assertLess(js.index("if(m.romp==='viewFile'&&m.pane==='pane')"), js.index("else if(m.romp==='viewFile'){var vf="))
        feed = js.split("else if(m.romp==='viewFile'){var vf=document.getElementById('f-feed');")[1].split("if(m.romp==='viewFileOpened')")[0]
        self.assertIn("window.__rompFeedWasOffViewPend=!document.body.classList.contains('po-feed');", feed)
        self.assertIn("window.__rompMobileTab&&window.__rompMobileTab('feed')", feed)
        self.assertIn("postMessage({romp:'viewFile',path:m.path,sid:m.sid},'*')", feed)

    def test_the_quote_seed_forward_sits_in_the_same_listener(self):
        # file-view.ts composerWindow posts editorSelection UP from a pane without a composer; the shell
        # forwards it whole into the chat frame (the executed pins live in file-view.test.ts)
        js = km._LANDING_SETTINGS_JS
        self.assertIn("if(m.type==='editorSelection'&&typeof m.text==='string'){var fc=document.getElementById('f-chat');", js)
        self.assertIn("fc&&fc.contentWindow&&fc.contentWindow.postMessage(m,'*')", js)



class BrowseRelay(unittest.TestCase):
    """The shell's browseFiles relay gains the same `pane` branch (2026-09-06): the folder at the bottom of the
    chat, the System-context Directory row and a tab menu's Browse files post {romp:'browseFiles', pane, ...}
    with the file-link ladder's verdict (ui/webview/file-route.ts browseRoute), and 'pane' brings the Files pane
    forward and forwards the ask, identity included, into #f-files, where files.ts opens the file BROWSER as a
    column. None of the feed route's was-off / browseClosed machinery applies: the pane stays up. The feed route
    is the else branch and unchanged; an ask naming 'feed' or no pane at all still lands there. The executed
    checks live in ui/webview/browse-route.test.ts (the shell arms run against a shimmed window, and the pane
    under the real shell script in a browser); these pin the kernel-side shape."""

    HEAD = "if(m.romp==='browseFiles'&&m.pane==='pane'){var fb=document.getElementById('f-files');"
    FEED = "else if(m.romp==='browseFiles'){var bf=document.getElementById('f-feed');"

    @staticmethod
    def _code(js):
        return "\n".join(l for l in js.splitlines() if not l.lstrip().startswith("//"))

    def test_the_pane_branch_precedes_the_feed_else_branch(self):
        js = km._LANDING_SETTINGS_JS
        self.assertIn(self.HEAD, js)
        self.assertIn(self.FEED, js)
        self.assertLess(js.index(self.HEAD), js.index(self.FEED))
        # the viewFile pair keeps its own order and anchors (the playwright harnesses slice on them)
        self.assertLess(js.index("if(m.romp==='viewFile'&&m.pane==='pane')"), js.index("else if(m.romp==='viewFile'){var vf="))

    def test_the_pane_branch_brings_the_files_pane_forward_and_forwards_the_identity(self):
        js = km._LANDING_SETTINGS_JS
        branch = self._code(js.split(self.HEAD)[1].split(self.FEED)[0])
        self.assertIn("window.__rompPaneToggle&&window.__rompPaneToggle('files',true)", branch)
        # phone: the Files tab comes forward only in the mobile layout, and the tab the click came from is
        # remembered for filesViewerClosed (the viewFile pane branch's exact idiom)
        self.assertIn("try{if(window.__rompMobileOn&&window.__rompMobileOn()){var curb=document.body.getAttribute('data-tab')||'chat';\n"
                      "    if(curb!=='files'){window.__rompFilesTabFrom=curb;window.__rompMobileTab&&window.__rompMobileTab('files');}}}catch(e){}", branch)
        self.assertIn("postMessage({romp:'browseFiles',path:m.path,sid:m.sid,identity:m.identity||null},'*')", branch)
        self.assertEqual(branch.count("postMessage("), 1, "one forward, carrying the whole ask")
        for tok in ("__rompFeedWasOff", "browseClosed", "'f-feed'", "__rompMobileTab('feed')"):
            self.assertNotIn(tok, branch, tok + " belongs to the feed route")

    def test_the_feed_route_is_the_else_branch_with_the_phone_return_trip(self):
        js = km._LANDING_SETTINGS_JS
        feed = js.split(self.FEED)[1].split("if(m.romp==='browseClosed'")[0]
        self.assertIn("window.__rompFeedWasOff=true;", feed)
        self.assertIn("postMessage({romp:'browseFiles',path:m.path,sid:m.sid},'*')", feed)
        self.assertNotIn("identity", feed, "the feed resolves its own identity")
        # phone: the Feed tab comes forward only in the mobile layout (on desktop show() would persist a stale
        # romp-mobile-tab for a later narrow layout), and the tab the click came from is remembered, the viewFile
        # pane branch's idiom (review 2026-09-07; the executed cases live in ui/webview/browse-route.test.ts)
        self.assertIn("try{if(window.__rompMobileOn&&window.__rompMobileOn()){var curf=document.body.getAttribute('data-tab')||'chat';\n"
                      "    if(curf!=='feed'){window.__rompFeedTabFrom=curf;window.__rompMobileTab&&window.__rompMobileTab('feed');}}}catch(e){}", feed)
        self.assertNotIn("try{window.__rompMobileTab&&window.__rompMobileTab('feed');}catch(e){}", feed, "no unconditional tab switch")
        # browseClosed first puts a phone back on the remembered tab (the memory dropped either way, so a rotation
        # to desktop in between replays nothing), THEN restores the pane, consuming either feed flag and only those
        back = ("if(m.romp==='browseClosed'){var backf=window.__rompFeedTabFrom;window.__rompFeedTabFrom=null;\n"
                "  if(backf&&window.__rompMobileOn&&window.__rompMobileOn()){try{window.__rompMobileTab&&window.__rompMobileTab(backf);}catch(e){}}}")
        self.assertIn(back, js)
        restore = "if(m.romp==='browseClosed'&&(window.__rompFeedWasOff||window.__rompFeedWasOffView)){"
        self.assertIn(restore, js)
        self.assertLess(js.index(back), js.index(restore))
        self.assertNotIn("__rompFeedTabFrom", js.split(self.HEAD)[1].split(self.FEED)[0],
                         "the Files route keeps its own memory (__rompFilesTabFrom)")

    def test_the_comment_above_the_pane_branch_names_the_ladder_and_the_gesture(self):
        js = km._LANDING_SETTINGS_JS
        lines = js.split(self.HEAD)[0].rstrip("\n").split("\n")
        start = len(lines)
        while start > 0 and lines[start - 1].lstrip().startswith("//"):
            start -= 1
        comment = "\n".join(lines[start:])
        self.assertIn("file-route.ts", comment, "the route is decided at the click, by the ladder the chat imports")
        self.assertIn("gesture", comment, "a pane moves on a user gesture only; the comment names it")
        self.assertIn("filesViewerClosed", comment, "the phone's way back is the pane's own close edge")

    def test_the_two_ends_agree_on_the_message(self):
        # the sender names its target and carries the identity (render.ts openBrowse); the pane caches the
        # identity, opens the browser, and owes the shell no browseClosed (files.ts; file-browse.ts gates it)
        render = (UI / "render.ts").read_text()
        self.assertIn('window.parent.postMessage({ romp: "browseFiles", path: path || ".", sid: to, pane: route,', render)
        files = (UI / "files.ts").read_text()
        self.assertIn("shellRestore: false,", files)
        self.assertIn("if (sid && id) identities.set(sid, id);", files)
        self.assertIn('openFileBrowse(m.path || ".", sid);', files)
        browse = (UI / "file-browse.ts").read_text()
        self.assertIn("if (!shellRestore) return;", browse)
        route = (UI / "file-route.ts").read_text()
        self.assertIn("export function browseRoute(web: boolean, pane: unknown, framed: boolean, filesOpen: boolean): BrowseRoute {", route)

    def test_the_guide_names_the_folder_link_and_where_its_listing_opens(self):
        guide = (Path(BIN).parent / "docs" / "guide.md").read_text()
        self.assertIn("The folder under the chat (the session's working directory) opens a\nlisting of that folder by the same rule", guide)
        self.assertIn("otherwise over the feed. Pick a file in the listing and\nit opens where the listing is.", guide)


if __name__ == "__main__":
    unittest.main()
