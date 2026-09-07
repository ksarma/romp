// Links inside a shown file, in a browser (file-view-links.ts; the user 2026-09-07): headless Chromium boots the Files
// pane's real bundle, opens synthetic files through the pane's relay, and drives the mouse and the keyboard over the
// viewer's real DOM: the rows hljs built and the pass marked, the body's click delegate, the fetch a path link causes,
// the line a `:30` link scrolls to, the Raw view a markdown file takes for that open, the tab a URL anchor opens, and
// the two clicks that must NOT open anything: a drag that selects text across or inside a link, and nothing else. This
// is the leg no stand-in can stand in for: the browser decides where a press-drag-release sends its click and whether
// a focusable span's press ends the selection (path-links.ts's press handler exists for exactly that). Skips LOUDLY
// without a playwright browser (CI installs none), as waiting-link-focus.test.ts does. Synthetic values only: the
// notes-api world under /tmp/TESTHOST, a placeholder session id, example.invalid addresses.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";

const requireCjs = createRequire(__filename);
const EXT = process.cwd();                                        // npm test runs in vscode-extension
const UI = path.resolve(EXT, "..", "ui", "webview");
const SID = "11111111-2222-3333-4444-555555555555";
const ROOT = "/tmp/TESTHOST/notes-api";
const APP = ROOT + "/src/app.py";
const GUIDE = ROOT + "/docs/guide.md";
const CONFIG = ROOT + "/src/data/config.json";

const APP_TEXT = [
  "# notes-api: see https://example.invalid/docs/setup.html, then ../docs/guide.md:30.",
  "import json",
  'cfg = json.load(open("data/config.json"))',
  "from . import util  # and/or 24/7 x = 1/2.5 /api/users ./foo",
  "readme = 'file:///tmp/TESTHOST/notes-api/README.md'",
  "",
].join("\n");
const GUIDE_TEXT = [
  "# Guide", "",
  "Read [the app](../src/app.py) and [the web](https://example.invalid/doc).",
  "Bare ../src/app.py:3 links too, and https://example.invalid/prose is a URL.", "",
  "```bash", "curl https://example.invalid/dl -o data/x.json", "```", "",
  ...Array.from({ length: 32 }, (_, i) => "line " + (i + 10)),
  "",
].join("\n");
const FILES: Record<string, string> = { [APP]: APP_TEXT, [GUIDE]: GUIDE_TEXT, [CONFIG]: '{"a": 1}\n' };

function bundle(entry: string): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    entryPoints: [path.join(UI, entry)], bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}
const PAGE = `<!DOCTYPE html><html><head><meta charset=utf-8><style>
${fs.readFileSync(path.join(UI, "styles.css"), "utf8")}
${fs.readFileSync(path.join(UI, "files-pane.css"), "utf8")}
</style></head><body class=fileview-pane><div id=files-empty></div><script src=/dist/files.js></script></body></html>`;

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

test("in a browser: a shown file's URLs and paths are links; a path link opens the file (into Recent) and a :line scrolls its row in Raw; a Markdown link to a file opens it; a URL opens a tab; a drag across or inside a link selects and opens nothing; Enter opens", async (t) => {
  if (!pw) { t.skip("playwright is not installed under vscode-extension: the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw.chromium.launch(); }
  catch (e) { t.skip("no playwright browser on this box, and the browser leg needs one (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  const errors: string[] = [];
  const served: Array<{ path: string; sid: string | null }> = [];
  try {
    const filesJs = bundle("files.ts");
    const ctx = await browser.newContext({ viewport: { width: 900, height: 480 } });
    await ctx.route("https://example.invalid/**", (route: any) => route.fulfill({ status: 200, contentType: "text/html", body: "<title>elsewhere</title>" }));
    const page = await ctx.newPage();
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    await page.route("http://romp.test/**", (route: any) => {
      const u = new URL(route.request().url());
      if (u.pathname === "/files") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: PAGE });
      if (u.pathname === "/dist/files.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: filesJs });
      if (u.pathname === "/file") {                                   // the viewer's fetch: what the kernel serves for a text file
        const p = u.searchParams.get("path") || "";
        served.push({ path: p, sid: u.searchParams.get("sid") });
        const body = FILES[path.posix.normalize(p)];                 // the kernel resolves `..`; the fixture keeps the spelling it was asked for
        if (body === undefined) return route.fulfill({ status: 404, contentType: "text/plain", body: "no such file: " + p });
        return route.fulfill({ status: 200, contentType: "text/plain; charset=utf-8", headers: { "X-Romp-Mtime-Ns": "1", "X-Romp-Text-Utf8": "1" }, body });
      }
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://romp.test/files");
    const open = async (p: string) => {
      await page.evaluate(([p, sid]: string[]) => { window.postMessage({ romp: "viewFile", path: p, sid }, "*"); }, [p, SID]);
      await page.locator("#romp-fileview .fileview-base", { hasText: p.slice(p.lastIndexOf("/") + 1) }).waitFor({ timeout: 10000 });
      await page.locator("#romp-fileview .fileview-body code.hljs .fv-cl, #romp-fileview .fileview-body .fileview-md").first().waitFor({ timeout: 10000 });
    };
    const settle = () => page.evaluate(() => new Promise((r) => requestAnimationFrame(() => setTimeout(r, 60))));
    const rowTexts = () => page.evaluate(() => Array.from(document.querySelectorAll("#romp-fileview code.hljs .fv-cl")).map((r) => r.textContent));
    type Info = { text: string | null; path: string | null; line: string | null; act: string | null; href: string | null; target: string | null; rel: string | null; cls: string };
    const linkInfo = (sel: string): Promise<Info[]> => page.evaluate((sel: string) => Array.from(document.querySelectorAll(sel)).map((x) => {
      const e = x as HTMLElement;
      return { text: e.textContent, path: e.dataset.path ?? null, line: e.dataset.line ?? null, act: e.dataset.act ?? null, href: e.getAttribute("href"), target: e.getAttribute("target"), rel: e.getAttribute("rel"), cls: e.className };
    }), sel);

    // ── the code view: what the pass marked, on hljs's rows, with every row's text intact ──────────
    await open(APP);
    assert.deepEqual(await rowTexts(), APP_TEXT.split("\n").slice(0, -1), "every row reads as the file's line");
    const urls = await linkInfo("#romp-fileview a.fv-url");
    assert.deepEqual(urls.map((u) => [u.text, u.href, u.target, u.rel]), [["https://example.invalid/docs/setup.html", "https://example.invalid/docs/setup.html", "_blank", "noopener noreferrer"]]);
    const links = await linkInfo("#romp-fileview .file-uri-link");
    assert.deepEqual(links.map((l) => [l.text, l.path, l.line, l.act]), [
      ["../docs/guide.md:30", ROOT + "/src/../docs/guide.md", "30", "openpath"],
      ["data/config.json", ROOT + "/src/data/config.json", null, "openpath"],
      ["file:///tmp/TESTHOST/notes-api/README.md", ROOT + "/README.md", null, "openpath"],
    ], "the three paths; and/or, 1/2.5, /api/users, ./foo and the import are prose");
    // the dress is light: the link keeps its highlight colour, under a dotted underline that is solid only under the pointer
    const dress = await page.evaluate(() => {
      const l = document.querySelector("#romp-fileview .file-uri-link") as HTMLElement;
      const cs = getComputedStyle(l), ps = getComputedStyle(l.parentElement!);
      return { same: cs.color === ps.color, line: cs.textDecorationLine, style: cs.textDecorationStyle, cursor: cs.cursor };
    });
    assert.deepEqual(dress, { same: true, line: "underline", style: "dotted", cursor: "pointer" });
    await page.locator("#romp-fileview .file-uri-link").nth(1).hover();
    assert.equal(await page.evaluate(() => getComputedStyle(document.querySelectorAll("#romp-fileview .file-uri-link")[1]).textDecorationStyle), "solid", "solid under the pointer");
    assert.equal(served.length, 1, "one fetch so far: the file itself");

    // ── a path link opens the file it names, with the viewer's session, and the pane records it as recent ─
    await page.locator("#romp-fileview .file-uri-link", { hasText: "data/config.json" }).click();
    await page.locator("#romp-fileview .fileview-base", { hasText: "config.json" }).waitFor({ timeout: 10000 });
    assert.deepEqual(served[1], { path: CONFIG, sid: SID }, "the resolved path, the session the file belongs to");
    const recent = await page.evaluate(() => JSON.parse(localStorage.getItem("romp:files-recent") || "[]").map((r: { path: string }) => r.path));
    assert.ok(recent.includes(CONFIG), "opened through the pane's own open: the Recent list has it");

    // ── a :line link: the markdown file opens in Raw for this open, scrolled to its row; the preference is untouched ─
    await open(APP);
    await page.locator("#romp-fileview .file-uri-link", { hasText: "../docs/guide.md:30" }).click();
    await page.locator("#romp-fileview .fileview-base", { hasText: "guide.md" }).waitFor({ timeout: 10000 });
    await page.locator("#romp-fileview code.hljs .fv-cl").first().waitFor({ timeout: 10000 });
    assert.deepEqual(served[served.length - 1], { path: ROOT + "/src/../docs/guide.md", sid: SID });
    const raw = await page.evaluate(() => {
      const on = Array.from(document.querySelectorAll("#romp-fileview .fileview-btn.on")).map((b) => b.textContent);
      const rows = document.querySelectorAll("#romp-fileview code.hljs .fv-cl");
      const body = document.querySelector("#romp-fileview .fileview-body")!.getBoundingClientRect();
      const r30 = rows[29].getBoundingClientRect(), r1 = rows[0].getBoundingClientRect();
      return { on, rows: rows.length, row30In: r30.top >= body.top && r30.bottom <= body.bottom, row1Out: r1.bottom < body.top, pref: localStorage.getItem("romp:fileviewFmt") };
    });
    assert.deepEqual(raw.on, ["Raw"], "the Raw view for this open");
    assert.equal(raw.rows, GUIDE_TEXT.split("\n").length - 1);
    assert.equal(raw.row30In, true, "line 30's row is in view"); assert.equal(raw.row1Out, true, "and the top of the file is scrolled away");
    assert.ok(raw.pref === null || !/"raw"/.test(raw.pref), "the saved preference did not follow");

    // ── rendered markdown: a link to a file becomes a path link, a link to the web stays a tab, bare paths and fenced URLs link ─
    await open(GUIDE);
    await page.locator("#romp-fileview .fileview-md").waitFor({ timeout: 10000 });
    const mdLinks = await linkInfo("#romp-fileview .fileview-md a, #romp-fileview .fileview-md .file-uri-link");
    const byText = (t: string) => mdLinks.find((l) => l.text === t)!;
    assert.deepEqual([byText("the app").href, byText("the app").path, byText("the app").act, /file-uri-link/.test(byText("the app").cls)], [null, ROOT + "/docs/../src/app.py", "openpath", true]);
    assert.deepEqual([byText("the web").href, byText("the web").target, byText("the web").act], ["https://example.invalid/doc", "_blank", null]);
    assert.deepEqual([byText("../src/app.py:3").path, byText("../src/app.py:3").line], [ROOT + "/docs/../src/app.py", "3"], "a bare path in the prose, with its line");
    assert.deepEqual([byText("https://example.invalid/prose").target, /fv-url/.test(byText("https://example.invalid/prose").cls)], ["_blank", false], "marked's own autolink, not wrapped twice");
    assert.deepEqual([byText("https://example.invalid/dl").href, /fv-url/.test(byText("https://example.invalid/dl").cls)], ["https://example.invalid/dl", true], "a URL inside the fenced block");
    assert.equal(byText("data/x.json").path, ROOT + "/docs/data/x.json");
    const before = served.length;
    await page.locator("#romp-fileview .fileview-md a", { hasText: "the app" }).click();
    await page.locator("#romp-fileview .fileview-base", { hasText: "app.py" }).waitFor({ timeout: 10000 });
    assert.deepEqual(served[before], { path: ROOT + "/docs/../src/app.py", sid: SID }, "the Markdown link opened the file in the viewer");

    // ── a URL anchor opens a new tab and the viewer stays; nothing is fetched ──────────────────────
    await open(APP);
    const n0 = served.length;
    const [popup] = await Promise.all([page.waitForEvent("popup", { timeout: 10000 }), page.locator("#romp-fileview a.fv-url").click()]);
    await popup.waitForLoadState();
    assert.equal(popup.url(), "https://example.invalid/docs/setup.html");
    await popup.close();
    assert.equal(await page.locator("#romp-fileview .fileview-base").textContent(), "app.py", "the viewer is still up");
    assert.equal(served.length, n0, "a URL fetches no file");

    // ── selections: a drag across a link selects; a drag that begins and ends on the link selects; neither opens ─
    const row3 = page.locator("#romp-fileview code.hljs .fv-cl").nth(2);
    const link = page.locator("#romp-fileview .file-uri-link", { hasText: "data/config.json" });
    const rb = (await row3.boundingBox())!, lb = (await link.boundingBox())!;
    await page.mouse.move(rb.x + 2, rb.y + rb.height / 2); await page.mouse.down();
    await page.mouse.move(lb.x + lb.width + 20, lb.y + lb.height / 2, { steps: 10 }); await page.mouse.up();
    await settle();
    let sel = await page.evaluate(() => getSelection()!.toString());
    assert.ok(sel.includes("data/config.json"), "the drag across the link selected its text: " + JSON.stringify(sel));
    assert.equal(served.length, n0, "and opened nothing");
    await page.evaluate(() => getSelection()!.removeAllRanges());
    await page.mouse.move(lb.x + 3, lb.y + lb.height / 2); await page.mouse.down();
    await page.mouse.move(lb.x + lb.width - 3, lb.y + lb.height / 2, { steps: 10 }); await page.mouse.up();
    await settle();
    sel = await page.evaluate(() => getSelection()!.toString());
    assert.ok(sel.length > 3 && "data/config.json".includes(sel), "a drag inside the link selects its text (the press does not focus the span): " + JSON.stringify(sel));
    assert.equal(served.length, n0, "the click that ends the drag opens nothing");
    assert.equal(await page.locator("#romp-fileview .fileview-base").textContent(), "app.py");
    await page.evaluate(() => getSelection()!.removeAllRanges());

    // ── the keyboard: a focused path link opens on Enter ─────────────────────────────────────────
    await link.focus();
    await page.keyboard.press("Enter");
    await page.locator("#romp-fileview .fileview-base", { hasText: "config.json" }).waitFor({ timeout: 10000 });
    assert.deepEqual(served[served.length - 1], { path: CONFIG, sid: SID });
    assert.deepEqual(errors, [], "no page errors");
    await ctx.close();
  } finally {
    await browser.close();
  }
});
