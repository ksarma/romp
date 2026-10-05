// The browser driver for tests/test_mtabs_fit_served.py: the phone layout's bottom bar (#mtabs) measured in one engine,
// against a hermetic lab kernel. Opens the served dashboard with the iPhone 14 descriptor (Firefox without isMobile, which
// Playwright does not support there), once per tab set: the default set, and the set with the Files tab on (the gear's
// Files-control setting, written to the store before the page parses, the read the shell makes at boot). In each it takes
// the window through cfg.viewports (portrait and landscape phones), waits for the webfont and two frames, and reads, in
// the shell's coordinate space: the bar's box, its scroll and client widths, every control the bar shows (each button
// not display:none: the pane tabs, the action buttons, the bell), each control's box, whether its label fits inside it,
// and the element at its centre (elementFromPoint, which answers null past the window's edge), the bar's natural
// one-row width (the bar laid out once at max-content without wrapping, read synchronously and restored before the
// next paint), the reserved height --mtabs-h, the shown pane's iframe box, and the document's scroll width.
// Then the change the boot read cannot see: on the default set at cfg.dynamicViewport, the Files tab turned on the way
// the gear turns it on (a write of the settings key from a same-origin pane document, so this window hears the storage
// event the shell's pane controller acts on), with no resize, and the same reading after two frames.
// Then the two actions that left the bar for the settings card (iOS item 4g's move: Usage and Remote kernels), on a phone at
// cfg.actsViewport: the bar's Settings clicked at its centre, the card's row of panel buttons read (each button's box, the
// element at its centre, and the Remote kernels glyph's classes and colours beside the rail glyph's, which the same poll
// paints), then each button clicked once at its centre and its effect read in the shell (the Usage modal on #ru-back, the
// Remote kernels panel #rnet-back) with the card closed. The shell's own GET /tunnels (the main frame's, not the panes')
// answers cfg.tunnels, synthetic hosts, so the glyph has a state to show; the panes read the lab's real answer (no hosts).
// Then the drop cue on the card's glyph (cfg.tunnelsDrop, a host that was up answering down): a drop with the card closed,
// the glyph read at the card's next opening, and a drop with the card open, the glyph read while its flash runs.
// And the desktop: a plain context (no descriptor, a fine pointer) at cfg.desktopViewport, where the bar must stay hidden,
// and at each of cfg.railViewports the rail's actions (.rail-acts .rail-act, each shown one): id, box and centre hit.
// Writes the readings as JSON to cfg.result and prints one `RESULT-FILE:` line naming it; exits 3 when the browser does not
// launch (the Python side turns that into a skip).
// Never touches a live kernel: cfg.healthz names the LAB port and is asserted before any request. No sessions.
import { createRequire } from "node:module";
import fs from "node:fs";
import http from "node:http";

const require = createRequire(process.env.EXT_PKG);
const playwright = require("playwright");
const cfg = JSON.parse(fs.readFileSync(process.env.CFG, "utf8"));
const engine = cfg.engine || "chromium";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const out = { engine, errors: [], sets: {}, dynamic: null, acts: null, desktop: null, rail: [] };

const healthz = await new Promise((resolve) => {
  const req = http.get(cfg.healthz, (res) => { res.resume(); resolve({ status: res.statusCode }); });
  req.on("error", (e) => resolve({ status: 0, error: String(e) }));
  req.setTimeout(5000, () => { req.destroy(); resolve({ status: 0, error: "timeout" }); });
});
if (healthz.status !== 200) { console.error("lab kernel not healthy: " + JSON.stringify(healthz)); process.exit(4); }

let browser;
try { browser = await playwright[engine].launch(); }
catch (e) { console.error("browser-launch-failed: " + e); process.exit(3); }

const phone = { ...(playwright.devices["iPhone 14"] || {}) };
delete phone.defaultBrowserType;
if (engine === "firefox") delete phone.isMobile;   // playwright: isMobile is not supported in Firefox

// the reading, in the page; a string so the same function runs in every engine unchanged
const READ = () => {
  const r = (x) => Math.round(x * 100) / 100;
  const bar = document.getElementById("mtabs");
  const vw = window.innerWidth, vh = window.innerHeight;
  const bs = getComputedStyle(bar);
  const br = bar.getBoundingClientRect();
  const shownButtons = Array.from(bar.querySelectorAll("button")).filter((b) => getComputedStyle(b).display !== "none");
  // the natural one-row width, and each control's natural width (its width when nothing squeezes it): the bar at max-content
  // with no wrapping, read and restored synchronously (no paint between)
  const saved = bar.getAttribute("style");
  bar.style.setProperty("flex-wrap", "nowrap", "important");
  bar.style.setProperty("width", "max-content", "important");
  bar.style.setProperty("right", "auto", "important");
  const natural = r(bar.getBoundingClientRect().width);
  const naturalW = new Map(shownButtons.map((b) => [b, r(b.getBoundingClientRect().width)]));
  if (saved === null) bar.removeAttribute("style"); else bar.setAttribute("style", saved);
  const controls = shownButtons.map((b) => {
    const c = b.getBoundingClientRect();
    let hit = false;
    if (c.width > 0 && c.height > 0) {
      const at = document.elementFromPoint(c.left + c.width / 2, c.top + c.height / 2);
      hit = !!at && (at === b || b.contains(at));
    }
    return { key: b.getAttribute("data-pane") || b.id || b.getAttribute("data-act") || "?", tab: b.hasAttribute("data-pane"),
             left: r(c.left), right: r(c.right), top: r(c.top), bottom: r(c.bottom), w: r(c.width), h: r(c.height),
             naturalW: naturalW.get(b), labelFits: b.scrollWidth <= b.clientWidth + 0.5, hit };
  });
  const div = bar.querySelector(".mtabs-div");
  const dr = div ? div.getBoundingClientRect() : null;
  const shown = document.querySelector("iframe.m-on");
  const sr = shown ? shown.getBoundingClientRect() : null;
  return {
    vw, vh, mobile: window.__rompMobileOn ? window.__rompMobileOn() : null, display: bs.display,
    bar: { left: r(br.left), right: r(br.right), top: r(br.top), bottom: r(br.bottom), w: r(br.width), h: r(br.height),
           offsetH: bar.offsetHeight, scrollW: bar.scrollWidth, clientW: bar.clientWidth, borderTop: parseFloat(bs.borderTopWidth) || 0,
           padBottom: parseFloat(bs.paddingBottom) || 0 },
    natural, mtabsH: document.documentElement.style.getPropertyValue("--mtabs-h"),
    divider: dr ? { left: r(dr.left), right: r(dr.right), top: r(dr.top), bottom: r(dr.bottom), w: r(dr.width), h: r(dr.height) } : null,
    pane: sr ? { id: shown.id, top: r(sr.top), bottom: r(sr.bottom) } : null,
    docScrollW: document.documentElement.scrollWidth,
    bell: (() => { const b = document.getElementById("mbell"); return b ? { hidden: b.hidden, display: getComputedStyle(b).display } : null; })(),
    fonts: document.fonts ? document.fonts.check("600 12px Inter") : null,
    controls,
  };
};
const read = (page) => page.evaluate("(" + READ.toString() + ")()");
const frames = (page) => page.evaluate(() => new Promise((res) => requestAnimationFrame(() => requestAnimationFrame(() => res()))));

// a phone page on one tab set, booted: the bar laid out, the boot splash gone (the panes' first ready, or its backstop), the webfont in
async function boot(files, before) {
  const context = await browser.newContext({ ...phone, viewport: { width: 390, height: 844 } });
  if (files) await context.addInitScript(() => { try { localStorage.setItem("romp:settings", JSON.stringify({ showFilesControl: true })); } catch (e) { /* no store */ } });
  const page = await context.newPage();
  page.on("pageerror", (e) => { if (out.errors.length < 40) out.errors.push(String(e).slice(0, 300)); });
  if (before) await before(page);
  await page.goto(cfg.url, { waitUntil: "load", timeout: 40000 });
  await page.waitForSelector("#mtabs", { timeout: 20000 });
  await page.waitForFunction(() => { const b = document.getElementById("romp-boot"); return !b || b.classList.contains("gone"); }, null, { timeout: 30000 });
  await page.evaluate(() => (document.fonts ? document.fonts.ready.then(() => true) : true));
  return { context, page };
}

try {
  for (const [name, files] of [["default", false], ["files", true]]) {
    const { context, page } = await boot(files);
    const rows = [];
    for (const [w, h] of cfg.viewports) {
      await page.setViewportSize({ width: w, height: h });
      await frames(page);
      await sleep(cfg.settleMs || 100);
      await frames(page);
      rows.push({ vp: [w, h], ...(await read(page)) });
    }
    out.sets[name] = rows;
    await context.close();
  }
  // the Files tab turned on with no resize: the bar's height changes, and the reservation must follow it
  {
    const { context, page } = await boot(false);
    const [w, h] = cfg.dynamicViewport;
    await page.setViewportSize({ width: w, height: h });
    await frames(page);
    await sleep(cfg.settleMs || 100);
    await frames(page);
    const before = await read(page);
    const pane = page.frames().find((f) => f !== page.mainFrame() && /\/chat/.test(f.url()));
    if (!pane) throw new Error("no chat pane frame to write the setting from");
    await pane.evaluate(() => { localStorage.setItem("romp:settings", JSON.stringify({ showFilesControl: true })); });
    await page.waitForFunction(() => { const b = document.querySelector("#mtabs button[data-pane=files]"); return !!b && getComputedStyle(b).display !== "none"; }, null, { timeout: 10000 });
    await frames(page);
    await sleep(cfg.settleMs || 100);
    await frames(page);
    out.dynamic = { vp: [w, h], before, after: await read(page) };
    await context.close();
  }
  // the moved actions: one click on the bar's Settings, one on the card's button, and the effect in the shell
  {
    // the shell's first poll gets cfg.tunnels; every later one is held until the first opening has been read (so the card's
    // paint there is the opening's own, not a poll's), then answered, with every one after it, by cfg.tunnels2
    let polls = 0, answer = null;
    const held = [];
    const fulfil = (route, body) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
    const { context, page } = await boot(false, (pg) => pg.route("**/tunnels", (route) => {
      const q = route.request();
      if (q.method() !== "GET" || q.frame() !== pg.mainFrame()) return route.continue();
      polls++;
      if (polls === 1) return fulfil(route, cfg.tunnels);
      if (answer) return fulfil(route, answer);
      held.push(route);
      return undefined;
    }));
    const [w, h] = cfg.actsViewport;
    await page.setViewportSize({ width: w, height: h });
    await frames(page);
    await sleep(cfg.settleMs || 100);
    await frames(page);
    // the shell's first poll has painted the rail glyph from the synthetic hosts (the card's copy is painted from it on open)
    await page.waitForFunction(() => { const r = document.getElementById("rail-net"); return !!r && r.classList.contains("on"); }, null, { timeout: 15000 });
    const acts = { vp: [w, h], bar: await read(page), runs: {} };
    const settingsFrame = () => page.frames().find((f) => f !== page.mainFrame() && /\/settings(\?|$)/.test(f.url()));
    const clickCentre = async (box) => { await page.mouse.click(box.left + box.w / 2, box.top + box.h / 2); };
    for (const act of ["usage", "net"]) {
      const run = {};
      const gear = acts.bar.controls.find((c) => c.key === "settings");
      if (!gear) throw new Error("no Settings on the bar");
      await clickCentre(gear);
      await page.waitForFunction(() => document.body.classList.contains("settings-open"), null, { timeout: 20000 });
      const sf = settingsFrame();
      if (!sf) throw new Error("no settings frame after the click");
      await sf.waitForFunction(() => { const p = document.getElementById("rsettings"); return !!p && !p.hidden; }, null, { timeout: 10000 });
      await frames(page);
      const lift = await page.evaluate(() => { const r = document.getElementById("f-settings").getBoundingClientRect(); return { left: r.left, top: r.top }; });
      run.card = await sf.evaluate((ctx) => {
        const r = (x) => Math.round(x * 100) / 100;
        const row = document.getElementById("rs-pacts"), card = document.querySelector("#rsettings .rs-card");
        const cr = card ? card.getBoundingClientRect() : null;
        const buttons = row ? Array.from(row.querySelectorAll("button")).map((b) => {
          const c = b.getBoundingClientRect();
          const at = c.width > 0 && c.height > 0 ? document.elementFromPoint(c.left + c.width / 2, c.top + c.height / 2) : null;
          return { act: b.getAttribute("data-pact"), text: b.textContent.trim(), left: r(c.left + ctx.left), right: r(c.right + ctx.left),
                   top: r(c.top + ctx.top), bottom: r(c.bottom + ctx.top), w: r(c.width), h: r(c.height), hit: !!at && (at === b || b.contains(at)) };
        }) : [];
        const net = document.getElementById("rs-pact-net");
        const glyph = net ? { cls: net.getAttribute("class"), color: getComputedStyle(net).color,
          nodes: ["rn-me", "rn-a", "rn-b"].map((k) => { const e = net.querySelector("." + k); return e ? { cls: e.getAttribute("class"), fill: getComputedStyle(e).fill } : null; }) } : null;
        return { rowShown: !!row && !row.hidden && getComputedStyle(row).display !== "none", buttons, glyph,
                 card: cr ? { left: r(cr.left + ctx.left), right: r(cr.right + ctx.left), top: r(cr.top + ctx.top), bottom: r(cr.bottom + ctx.top) } : null,
                 tab: (document.querySelector("#rs-tabs .rs-tab.on") || {}).textContent || "" };
      }, lift);
      // the rail's own glyph, painted by the same poll (display:none on the phone, its computed colours still resolve)
      run.rail = await page.evaluate(() => { const n = document.getElementById("rail-net");
        return { cls: n.getAttribute("class"), color: getComputedStyle(n).color,
                 nodes: ["rn-me", "rn-a", "rn-b"].map((k) => { const e = n.querySelector("." + k); return { cls: e.getAttribute("class"), fill: getComputedStyle(e).fill }; }) }; });
      const btn = run.card.buttons.find((b) => b.act === act);
      if (!btn) {
        // no button to click (a tree without the move): the card closed by its own opener (which toggles), and its close
        // awaited, so the next click lands on the bar and not on the lifted card still closing
        run.clicked = false;
        acts.runs[act] = run;
        await page.evaluate(() => window.__rompOpenSettings && window.__rompOpenSettings());
        await page.waitForFunction(() => !document.body.classList.contains("settings-open"), null, { timeout: 10000 });
        await frames(page);
        continue;
      }
      await clickCentre(btn);
      run.clicked = true;
      const seen = act === "usage"
        ? () => { const b = document.getElementById("ru-back"), t = document.getElementById("ru-tip"); return !!b && b.classList.contains("on") && !!t && t.classList.contains("ru-modal") && t.style.display === "block"; }
        : () => { const b = document.getElementById("rnet-back"); return !!b && !b.hidden; };
      try { await page.waitForFunction(seen, null, { timeout: 10000 }); run.opened = true; } catch (e) { run.opened = false; }
      await frames(page);
      run.after = await page.evaluate(() => ({ settingsOpen: document.body.classList.contains("settings-open"),
        usage: (() => { const b = document.getElementById("ru-back"); return !!b && b.classList.contains("on"); })(),
        net: (() => { const b = document.getElementById("rnet-back"); return !!b && !b.hidden; })(),
        netTitle: ((document.querySelector("#rnet-panel .rnet-top span") || {}).textContent || "") }));
      run.cardHidden = await sf.evaluate(() => { const p = document.getElementById("rsettings"); return !p || p.hidden; });
      await page.evaluate(() => { try { window.__rompUsageClose && window.__rompUsageClose(); } catch (e) {} try { window.__rompCloseNet && window.__rompCloseNet(); } catch (e) {} });
      await frames(page);
      acts.runs[act] = run;
      if (act === "usage") {
        // release the held polls with both hosts connected: the rail turns, and the card's copy (its page loaded, the card
        // closed) turns with it, painted by the poll itself
        answer = cfg.tunnels2;
        for (const route of held.splice(0)) await fulfil(route, answer);
        await page.waitForFunction(() => { const a = document.querySelector("#rail-net .rn-a"); return !!a && a.getAttribute("class") === "rn-a rn-ok"; }, null, { timeout: 15000 });
        await frames(page);
        acts.released = { polls, card: await sf.evaluate(() => { const n = document.getElementById("rs-pact-net");
          return n ? ["rn-me", "rn-a", "rn-b"].map((k) => { const e = n.querySelector("." + k); return e ? e.getAttribute("class") : null; }) : null; }) };
      }
    }
    // the drop cue: a host that was up answering down flashes the glyph three times (the shell's flashDrop). First with the
    // card closed: the poll answers cfg.tunnelsDrop, the rail's nodes turn (the paint and the drop handler run in that one
    // poll's callback), the card's copy is read while closed and again at the card's next opening (the bar's Settings at its
    // centre), where a flash for the drop it could not show must not play. Then the host comes back and drops again with
    // the card open, where the card's copy flashes. Each wait records its outcome, so a red run lists every line.
    {
      const sf = settingsFrame();
      const drop = {};
      const glyphNow = () => sf.evaluate(() => { const n = document.getElementById("rs-pact-net"); if (!n) return null;
        return { cls: n.getAttribute("class"), anims: n.getAnimations ? n.getAnimations().map((a) => (a.animationName || "?") + ":" + a.playState) : null,
                 cardHidden: document.getElementById("rsettings").hidden }; });
      const railA = (want) => page.waitForFunction((w) => { const a = document.querySelector("#rail-net .rn-a"); return !!a && a.getAttribute("class") === w; }, want, { timeout: 15000 }).then(() => true, () => false);
      answer = cfg.tunnelsDrop;
      drop.closedPolled = await railA("rn-a rn-warn");
      await frames(page);
      drop.closed = await glyphNow();
      const gear = acts.bar.controls.find((c) => c.key === "settings");
      await clickCentre(gear);
      await page.waitForFunction(() => document.body.classList.contains("settings-open"), null, { timeout: 20000 });
      await sf.waitForFunction(() => { const p = document.getElementById("rsettings"); return !!p && !p.hidden; }, null, { timeout: 10000 });
      await frames(page);
      drop.reopened = await glyphNow();
      answer = cfg.tunnels2;
      drop.backUp = await railA("rn-a rn-ok");
      answer = cfg.tunnelsDrop;
      // read in the frame the moment the class lands (polled every frame), while its flash runs
      drop.openDrop = await sf.waitForFunction(() => { const n = document.getElementById("rs-pact-net");
        if (!n || !n.classList.contains("rn-drop")) return false;
        return { cls: n.getAttribute("class"), anims: n.getAnimations ? n.getAnimations().map((a) => (a.animationName || "?") + ":" + a.playState) : null }; },
        null, { timeout: 15000, polling: "raf" }).then((h) => h.jsonValue(), () => null);
      await page.evaluate(() => window.__rompOpenSettings && window.__rompOpenSettings());
      await page.waitForFunction(() => !document.body.classList.contains("settings-open"), null, { timeout: 10000 });
      acts.drop = drop;
    }
    out.acts = acts;
    await context.close();
  }
  // the desktop rail at each width: the actions pinned at its right end, shown ones only (the bell once the push script reveals it)
  for (const [w, h] of cfg.railViewports || []) {
    const context = await browser.newContext({ viewport: { width: w, height: h } });
    const page = await context.newPage();
    page.on("pageerror", (e) => { if (out.errors.length < 40) out.errors.push(String(e).slice(0, 300)); });
    await page.goto(cfg.url, { waitUntil: "load", timeout: 40000 });
    await page.waitForFunction(() => { const b = document.getElementById("rail-bell"); return !!b && !b.hidden; }, null, { timeout: 20000 });
    await page.waitForFunction(() => { const b = document.getElementById("romp-boot"); return !b || b.classList.contains("gone"); }, null, { timeout: 30000 });
    await page.evaluate(() => (document.fonts ? document.fonts.ready.then(() => true) : true));
    await frames(page);
    await sleep(cfg.settleMs || 100);
    await frames(page);
    out.rail.push({ vp: [w, h], ...(await page.evaluate(() => {
      const r = (x) => Math.round(x * 100) / 100;
      const acts = Array.from(document.querySelectorAll(".rail-acts .rail-act")).filter((a) => getComputedStyle(a).display !== "none");
      return { vw: window.innerWidth, mobile: window.__rompMobileOn ? window.__rompMobileOn() : null,
        acts: acts.map((a) => { const c = a.getBoundingClientRect();
          const at = c.width > 0 && c.height > 0 ? document.elementFromPoint(c.left + c.width / 2, c.top + c.height / 2) : null;
          return { id: a.id, left: r(c.left), right: r(c.right), top: r(c.top), bottom: r(c.bottom), w: r(c.width), h: r(c.height), hit: !!at && (at === a || a.contains(at)) }; }) };
    })) });
    await context.close();
  }
  // the desktop: a fine pointer at a desktop size, where the phone bar is not shown at all
  {
    const context = await browser.newContext({ viewport: { width: cfg.desktopViewport[0], height: cfg.desktopViewport[1] } });
    const page = await context.newPage();
    page.on("pageerror", (e) => { if (out.errors.length < 40) out.errors.push(String(e).slice(0, 300)); });
    await page.goto(cfg.url, { waitUntil: "load", timeout: 40000 });
    await page.waitForSelector("#mtabs", { state: "attached", timeout: 20000 });
    out.desktop = await page.evaluate(() => {
      const bar = document.getElementById("mtabs"), rail = document.querySelector(".pane-rail");
      return { display: getComputedStyle(bar).display, mobile: window.__rompMobileOn ? window.__rompMobileOn() : null,
               railDisplay: rail ? getComputedStyle(rail).display : null };
    });
    await context.close();
  }
} catch (e) {
  out.died = String(e).slice(0, 600);
}
// the result goes to the file the Python side names (cfg.result): one write to a pipe can stop at the pipe's buffer, 64 KiB on
// Linux, and these readings (about 50 KB) come close to that and grow with every reading the test adds
fs.writeFileSync(cfg.result, JSON.stringify(out));
fs.writeSync(1, "RESULT-FILE:" + cfg.result + "\n");
try { await browser.close(); } catch (e) { /* closing */ }
process.exit(0);
