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
// Then the actions that left the bar for the settings card (iOS item 4g's move: cfg.moved, Usage, Remote kernels and Restart
// kernel), on a phone at cfg.actsViewport: the bar's Settings clicked at its centre, the card's row of moved actions read
// (each button's box, the element at its centre, and the Remote kernels glyph's classes and colours beside the rail glyph's,
// which the same poll paints), then each button clicked once at its centre and its effect read in the shell (the Usage modal
// on #ru-back, the Remote kernels panel #rnet-back, the kernel's restart: one POST /restart from the shell) with the card
// closed. The shell's own GET /tunnels (the main frame's, not the panes') answers cfg.tunnels, synthetic hosts, so the glyph
// has a state to show; the panes read the lab's real answer (no hosts). The shell's POST /restart never reaches the lab
// kernel: it is answered here with a refusal (cfg.restartRefusal, the manager's 502 shape), which the shell's restart
// handles by bringing its splash down and wearing the refusal's words on the rail's restart button, so the lab lives on.
// Then the drop cue on the card's glyph (cfg.tunnelsDrop, a host that was up answering down): a drop with the card closed,
// the glyph read at the card's next opening, and a drop with the card open, the glyph read while its flash runs; then, the
// host back up, the Token usage panel opened over the card (#ra-open), a drop while it is up, the panel closed (#ra-close),
// and the glyph read two frames after the card shows again.
// Then Usage with no reading, on a page of its own at cfg.actsViewport: the shell's usage pull (the main frame's GET under
// /usage/) answers no rows, so the shell holds no reading (the rail's readout, which renders over the readings, read empty as
// the premise); the card opened from the bar's Settings, its Usage button read once the opening's ask has ended (disabled,
// its sub-line), a click at its centre, and after a settle (an absence has no event to wait on) the card, the Usage modal
// and the phoneAct messages the shell heard read; then, the card still open, a reading arrives (the lab's own GET /usage
// payload posted to the shell as the timeline posts it, the shell's later pulls let through), Usage read again in the open
// card; then the readings emptied (a payload with no window and no spend, posted the same way) and filled again, Usage read
// after each, and one click on it, its effect read.
// Then a reading the kernel holds and the shell has not pulled, on a page of its own at cfg.actsViewport: the shell's boot
// pull answers no rows and every later one goes to the lab, the Sessions pane unloaded (read as the premise); the card
// opened, its ask for a fresh pull held while Usage is read (the romp loader in the sub-line's place, its animations, the
// button disabled and busy), then let through, Usage read once the ask has ended, and one click on it, its effect read.
// Then the deploy skew, on a page of its own at cfg.actsViewport: the shell's marker beside its phoneAct listener
// (window.__rompPhoneActs) read, and the card's row read at an opening with the marker, at one with it deleted (a parent with
// the phone layout and no marker), and Usage at one with the marker back and the usage script's two names deleted (a shell that
// cannot be asked for a reading).
// Then the Remote kernels glyph's colours, on a page of its own per theme (cfg.themes: the theme written to the store before
// the page parses, as the gear writes it) at cfg.actsViewport: the card opened from the bar's Settings, and in it the card's
// background, the button's own fill (the glyph sits on it) and each colour the glyph can wear, as computed values: the
// button lit and attaching (its colour, the strokes' currentColor) and each node's fill as connected, dialing and needs you,
// each read with that class set on the element and the element's transitions off, then put back.
// And the desktop: a plain context (no descriptor, a fine pointer) at cfg.desktopViewport, where the bar must stay hidden,
// and at each of cfg.railViewports the rail's actions (.rail-acts .rail-act, each shown one): id, box and centre hit; then
// the rail's gear clicked at its centre and the settings card's row of moved actions read (hidden, displayed, its buttons'
// boxes), which the phone alone shows.
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
const settingsFrameOf = (page) => page.frames().find((f) => f !== page.mainFrame() && /\/settings(\?|$)/.test(f.url()));
const frames = (page) => page.evaluate(() => new Promise((res) => requestAnimationFrame(() => requestAnimationFrame(() => res()))));

// a phone page on one tab set (and, given one, in one theme), booted: the bar laid out, the boot splash gone (the panes' first
// ready, or its backstop), the webfont in
async function boot(files, before, theme) {
  const context = await browser.newContext({ ...phone, viewport: { width: 390, height: 844 } });
  const stored = { ...(files ? { showFilesControl: true } : {}), ...(theme ? { theme } : {}) };
  if (Object.keys(stored).length) await context.addInitScript((s) => { try { localStorage.setItem("romp:settings", JSON.stringify(s)); } catch (e) { /* no store */ } }, stored);
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
    const restarts = [];   // the shell's POST /restart, by frame: the restart's effect, answered with a refusal so the lab lives on
    const { context, page } = await boot(false, async (pg) => {
      await pg.route("**/tunnels", (route) => {
        const q = route.request();
        if (q.method() !== "GET" || q.frame() !== pg.mainFrame()) return route.continue();
        polls++;
        if (polls === 1) return fulfil(route, cfg.tunnels);
        if (answer) return fulfil(route, answer);
        held.push(route);
        return undefined;
      });
      await pg.route("**/restart", (route) => {
        const q = route.request();
        if (q.method() !== "POST") return route.continue();
        restarts.push(q.frame() === pg.mainFrame() ? "shell" : "pane");
        return route.fulfill({ status: 502, contentType: "application/json", body: JSON.stringify({ error: cfg.restartRefusal }) });
      });
    });
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
    for (const act of cfg.moved) {
      const run = {};
      run.restartsBefore = restarts.slice();
      const gear = acts.bar.controls.find((c) => c.key === "settings");
      if (!gear) throw new Error("no Settings on the bar");
      await clickCentre(gear);
      await page.waitForFunction(() => document.body.classList.contains("settings-open"), null, { timeout: 20000 });
      const sf = settingsFrame();
      if (!sf) throw new Error("no settings frame after the click");
      await sf.waitForFunction(() => { const p = document.getElementById("rsettings"); return !!p && !p.hidden; }, null, { timeout: 10000 });
      await frames(page);
      const lift = await page.evaluate(() => { const r = document.getElementById("f-settings").getBoundingClientRect(); return { left: r.left, top: r.top }; });
      // the opening's ask for a fresh reading (Usage wears the romp loader, disabled, until it ends): read the row after it
      await sf.waitForFunction(() => { const w = document.getElementById("rs-pact-usage-wait"); return !w || w.hidden; }, null, { timeout: 10000 }).catch(() => null);
      // the glyph's colour fades over the dress's transition when the opening paints it, and Usage's when its ask ends (from the
      // disabled grey): read the row once those transitions end
      await sf.evaluate(() => { const fades = [];
        document.querySelectorAll("#rs-pacts .rs-pact").forEach((n) => { if (n.getAnimations) n.getAnimations().forEach((a) => { if (typeof CSSTransition !== "undefined" && a instanceof CSSTransition) fades.push(a); }); });
        return Promise.all(fades.map((a) => a.finished.catch(() => null))).then(() => fades.length); });
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
        // each moved action's dress beside Customize shortcuts' (the card's word button the row copies), at rest
        const DRESS = ["backgroundColor", "borderTopColor", "borderTopStyle", "borderTopWidth", "borderTopLeftRadius", "color",
                       "paddingTop", "paddingRight", "paddingBottom", "paddingLeft", "fontFamily", "fontSize", "fontWeight", "cursor",
                       "transitionProperty", "transitionDuration"];   // no line-height: its resolved value is the used one only where the
                                                                      // element renders, and Customize shortcuts sits on a tab not shown
        const dressOf = (el) => { const c = getComputedStyle(el), o = {}; DRESS.forEach((k) => { o[k] = c[k]; }); return o; };
        const ref = document.getElementById("rs-keys-btn");
        const dress = { ref: ref ? dressOf(ref) : null, acts: row ? Array.from(row.querySelectorAll("button")).map((b) => ({ act: b.getAttribute("data-pact"), cls: b.getAttribute("class"), dress: dressOf(b) })) : [] };
        const ub = document.getElementById("rs-pact-usage"), un = document.getElementById("rs-pact-usage-none");
        const usage = ub ? { disabled: ub.disabled, line: un ? { shown: !un.hidden && getComputedStyle(un).display !== "none", text: un.textContent.trim() } : null } : null;
        const net = document.getElementById("rs-pact-net");
        const glyph = net ? { cls: net.getAttribute("class"), color: getComputedStyle(net).color,
          nodes: ["rn-me", "rn-a", "rn-b"].map((k) => { const e = net.querySelector("." + k); return e ? { cls: e.getAttribute("class"), fill: getComputedStyle(e).fill } : null; }) } : null;
        return { rowShown: !!row && !row.hidden && getComputedStyle(row).display !== "none", buttons, glyph, dress, usage,
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
        : act === "net" ? () => { const b = document.getElementById("rnet-back"); return !!b && !b.hidden; }
        // the restart ran: the shell's handler took the refusal (its splash down, the refusal's words on the rail's button)
        : (words) => { const r = document.getElementById("rail-refresh"), s = document.getElementById("romp-boot");
            return !!r && r.title === words && (!s || s.classList.contains("gone")); };
      try { await page.waitForFunction(seen, cfg.restartRefusal, { timeout: 10000 }); run.opened = true; } catch (e) { run.opened = false; }
      run.restarts = restarts.slice();
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
      // then the Token usage panel over the open card (PR 976's round 1, fresh-1): the panel hides the card with no message to
      // the shell, so a drop while it is up left the class on the hidden copy, and the panel's close showed the card again
      // with the class on, where the flash played late. The host comes back, the panel opens (#ra-open's own click), the host
      // drops while the panel is up, the panel closes (#ra-close's), and the copy is read two frames after the card shows
      {
        const ra = {};
        answer = cfg.tunnels2;
        ra.backUp = await railA("rn-a rn-ok");
        ra.opened = await sf.evaluate(() => { const b = document.getElementById("ra-open"), back = document.getElementById("ranalytics-back");
          if (!b) return false; b.click(); return !!back && !back.hidden && document.getElementById("rsettings").hidden; });
        answer = cfg.tunnelsDrop;
        ra.dropped = await railA("rn-a rn-warn");
        await frames(page);
        ra.during = await glyphNow();
        ra.closed = await sf.evaluate(() => { const b = document.getElementById("ra-close"), back = document.getElementById("ranalytics-back");
          if (!b) return false; b.click(); return !!back && back.hidden && !document.getElementById("rsettings").hidden; });
        await frames(page);
        await frames(page);
        ra.after = await glyphNow();
        drop.analytics = ra;
      }
      await page.evaluate(() => window.__rompOpenSettings && window.__rompOpenSettings());
      await page.waitForFunction(() => !document.body.classList.contains("settings-open"), null, { timeout: 10000 });
      acts.drop = drop;
    }
    out.acts = acts;
    await context.close();
  }
  // the Usage legs' tools on one page: the card opened from the bar's Settings at its centre, Usage read (by its act, so a tree
  // without its states still yields a box to click; in the shell's coordinates), the shell's side read (the card, the Usage
  // modal, the phoneAct messages heard since the record was armed), and the end of the opening's ask awaited (the loader gone,
  // or never there), its outcome recorded
  const usageKit = async (page, leg) => {
    await page.evaluate(() => { window.__mtabsActs = []; window.addEventListener("message", (e) => { if (e.data && e.data.romp === "phoneAct") window.__mtabsActs.push(e.data.act); }); });
    const gear = (await read(page)).controls.find((c) => c.key === "settings");
    if (!gear) throw new Error("no Settings on the bar (" + leg + ")");
    const openCard = async () => {
      await page.mouse.click(gear.left + gear.w / 2, gear.top + gear.h / 2);
      await page.waitForFunction(() => document.body.classList.contains("settings-open"), null, { timeout: 20000 });
      const sf = settingsFrameOf(page);
      if (!sf) throw new Error("no settings frame after the click (" + leg + ")");
      await sf.waitForFunction(() => { const p = document.getElementById("rsettings"); return !!p && !p.hidden; }, null, { timeout: 10000 });
      await frames(page);
      return sf;
    };
    const usageNow = async (sf) => {
      const lift = await page.evaluate(() => { const r = document.getElementById("f-settings").getBoundingClientRect(); return { left: r.left, top: r.top }; });
      return sf.evaluate((ctx) => {
        const r = (x) => Math.round(x * 100) / 100;
        const b = document.querySelector("#rs-pacts [data-pact=usage]"), un = document.getElementById("rs-pact-usage-none"), wt = document.getElementById("rs-pact-usage-wait");
        if (!b) return null;
        const c = b.getBoundingClientRect();
        return { disabled: b.disabled, busy: b.getAttribute("aria-busy"), left: r(c.left + ctx.left), top: r(c.top + ctx.top), w: r(c.width), h: r(c.height),
                 line: un ? { shown: !un.hidden && getComputedStyle(un).display !== "none", text: un.textContent.trim() } : null,
                 wait: wt ? { shown: !wt.hidden && getComputedStyle(wt).display !== "none", text: wt.textContent.trim(),
                              anims: wt.getAnimations ? wt.getAnimations({ subtree: true }).map((a) => a.animationName || "?") : null } : null };
      }, lift);
    };
    const shellNow = async (sf) => ({ settingsOpen: await page.evaluate(() => document.body.classList.contains("settings-open")),
      cardHidden: await sf.evaluate(() => { const p = document.getElementById("rsettings"); return !p || p.hidden; }),
      usage: await page.evaluate(() => { const b = document.getElementById("ru-back"); return !!b && b.classList.contains("on"); }),
      acts: await page.evaluate(() => window.__mtabsActs.slice()) });
    const askEnded = (sf) => sf.waitForFunction(() => { const w = document.getElementById("rs-pact-usage-wait"); return !w || w.hidden; }, null, { timeout: 10000 }).then(() => true, () => false);
    const modalUp = () => page.waitForFunction(() => { const b = document.getElementById("ru-back"), t = document.getElementById("ru-tip"); return !!b && b.classList.contains("on") && !!t && t.classList.contains("ru-modal") && t.style.display === "block"; }, null, { timeout: 10000 }).then(() => true, () => false);
    return { openCard, usageNow, shellNow, askEnded, modalUp };
  };
  // Usage with no reading, then a reading landing while the card is open: the shell tells the open card
  {
    // the shell's usage pull is its one GET under /usage/ (the route the usage script's pull reads); /usage itself is let through
    let empty = true, pulls = 0;
    const { context, page } = await boot(false, (pg) => pg.route((url) => url.pathname.startsWith("/usage/"), (route) => {
      if (route.request().frame() !== pg.mainFrame() || !empty) return route.continue();
      pulls++;
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ rows: [], host: "" }) });
    }));
    const [w, h] = cfg.actsViewport;
    await page.setViewportSize({ width: w, height: h });
    await frames(page);
    await sleep(cfg.settleMs || 100);
    await frames(page);
    const nr = { vp: [w, h] };
    // the premise: the shell's boot pull got the empty answer, and its readout holds nothing
    for (let i = 0; i < 150 && pulls < 1; i++) await sleep(100);
    await frames(page);
    nr.premise = { pulls, readout: await page.evaluate(() => { const r = document.getElementById("rail-usage"); return r ? r.innerHTML : null; }) };
    const kit = await usageKit(page, "the no-reading leg");
    const sf = await kit.openCard();
    nr.firstAsked = await kit.askEnded(sf);
    nr.first = await kit.usageNow(sf);
    if (nr.first) {
      await page.mouse.click(nr.first.left + nr.first.w / 2, nr.first.top + nr.first.h / 2);
      await frames(page);
      await sleep(3 * (cfg.settleMs || 100));
      await frames(page);
      nr.tapped = await kit.shellNow(sf);
      nr.afterTap = await kit.usageNow(sf);
    }
    // a reading arrives with the card still open: the lab's own payload, posted as the timeline posts it (the shell's pulls go
    // to the lab from here); the open card's Usage read again, then clicked
    empty = false;
    await page.evaluate(async () => { const u = await (await fetch("/usage", { cache: "no-store" })).json(); window.postMessage({ romp: "usage", usage: u }, "*"); });
    nr.arrived = await page.waitForFunction(() => { const r = document.getElementById("rail-usage"); return !!r && r.innerHTML !== ""; }, null, { timeout: 10000 }).then(() => true, () => false);
    await frames(page);
    nr.stillOpen = await kit.shellNow(sf);
    nr.second = await kit.usageNow(sf);
    // ...and the readings emptying with the card still open (a payload with no window and no spend, posted the same way), then
    // filling again (the lab's payload once more), Usage read after each
    const post = (empty) => page.evaluate(async (none) => { const u = none ? {} : await (await fetch("/usage", { cache: "no-store" })).json(); window.postMessage({ romp: "usage", usage: u }, "*"); }, empty);
    const readout = (filled) => page.waitForFunction((f) => { const r = document.getElementById("rail-usage"); return !!r && (r.innerHTML !== "") === f; }, filled, { timeout: 10000 }).then(() => true, () => false);
    await post(true);
    nr.emptiedReadout = await readout(false);
    await frames(page);
    nr.emptied = await kit.usageNow(sf);
    await post(false);
    nr.refilledReadout = await readout(true);
    await frames(page);
    nr.refilled = await kit.usageNow(sf);
    if (nr.refilled) {
      await page.mouse.click(nr.refilled.left + nr.refilled.w / 2, nr.refilled.top + nr.refilled.h / 2);
      nr.opened = await kit.modalUp();
      await frames(page);
      nr.clicked = await kit.shellNow(sf);
    }
    out.noReading = nr;
    await context.close();
  }
  // a reading the kernel holds and the shell has not pulled (PR 976's round 1, extra6-1): the shell's boot pull answers no
  // rows, every later pull goes to the lab (whose usage.json is a reading), and the Sessions pane stays unloaded (the phone's
  // lazy panes), so no timeline forwards the reading. The card's opening asks the shell for a fresh pull: that request is held
  // while Usage is read (the romp loader, no claim either way), then let through, and Usage read once the ask has ended, then
  // clicked
  {
    let boots = 0, hold = false;
    const held = [];
    const { context, page } = await boot(false, (pg) => pg.route((url) => url.pathname.startsWith("/usage/"), (route) => {
      if (route.request().frame() !== pg.mainFrame()) return route.continue();
      if (boots === 0) { boots++; return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ rows: [], host: "" }) }); }
      if (hold) { held.push(route); return undefined; }
      return route.continue();
    }));
    const [w, h] = cfg.actsViewport;
    await page.setViewportSize({ width: w, height: h });
    await frames(page);
    await sleep(cfg.settleMs || 100);
    await frames(page);
    const up = { vp: [w, h] };
    for (let i = 0; i < 150 && boots < 1; i++) await sleep(100);
    await frames(page);
    up.premise = { boots, readout: await page.evaluate(() => { const r = document.getElementById("rail-usage"); return r ? r.innerHTML : null; }),
                   sessionsLoaded: await page.evaluate(() => { const f = document.getElementById("f-timeline"); return !!f && !!f.getAttribute("src"); }) };
    const kit = await usageKit(page, "the unpulled-reading leg");
    hold = true;
    const sf = await kit.openCard();
    for (let i = 0; i < 50 && !held.length; i++) await sleep(100);
    up.asked = held.length;
    await frames(page);
    up.during = await kit.usageNow(sf);
    hold = false;
    for (const route of held.splice(0)) await route.continue();
    up.ended = await kit.askEnded(sf);
    await frames(page);
    up.readout = await page.evaluate(() => { const r = document.getElementById("rail-usage"); return !!r && r.innerHTML !== ""; });
    up.after = await kit.usageNow(sf);
    if (up.after) {
      await page.mouse.click(up.after.left + up.after.w / 2, up.after.top + up.after.h / 2);
      up.opened = await kit.modalUp();
      await frames(page);
      up.clicked = await kit.shellNow(sf);
    }
    out.unpulled = up;
    await context.close();
  }
  // the deploy skew (PR 976's round 1, kernel-1): the card shows its row only where the shell publishes the marker beside the
  // listener that runs the row's taps (window.__rompPhoneActs). On a page of its own at cfg.actsViewport: the shell's marker
  // read, the card opened from the bar's Settings and its row read; the marker deleted (a parent with the phone layout and no
  // marker, as a shell from before the move is) and the card opened and read again; then the marker put back and the usage
  // script's two names deleted (__rompUsageReading and __rompUsagePull: a shell that cannot be asked for a reading) and Usage
  // read at the next opening, once its ask has ended
  {
    const { context, page } = await boot(false);
    const [w, h] = cfg.actsViewport;
    await page.setViewportSize({ width: w, height: h });
    await frames(page);
    await sleep(cfg.settleMs || 100);
    await frames(page);
    const gear = (await read(page)).controls.find((c) => c.key === "settings");
    if (!gear) throw new Error("no Settings on the bar (the skew leg)");
    const openRead = async () => {
      await page.mouse.click(gear.left + gear.w / 2, gear.top + gear.h / 2);
      await page.waitForFunction(() => document.body.classList.contains("settings-open"), null, { timeout: 20000 });
      const sf = settingsFrameOf(page);
      if (!sf) throw new Error("no settings frame after the click (the skew leg)");
      await sf.waitForFunction(() => { const p = document.getElementById("rsettings"); return !!p && !p.hidden; }, null, { timeout: 10000 });
      await sf.waitForFunction(() => { const w = document.getElementById("rs-pact-usage-wait"); return !w || w.hidden; }, null, { timeout: 10000 }).catch(() => null);
      await frames(page);
      const got = await sf.evaluate(() => { const row = document.getElementById("rs-pacts"), ub = document.getElementById("rs-pact-usage"), un = document.getElementById("rs-pact-usage-none");
        return { rowShown: !!row && !row.hidden && getComputedStyle(row).display !== "none",
                 boxes: row ? Array.from(row.querySelectorAll("button")).map((b) => { const c = b.getBoundingClientRect(); return [c.width, c.height]; }) : [],
                 usage: ub ? { disabled: ub.disabled, line: un ? { shown: !un.hidden && getComputedStyle(un).display !== "none" } : null } : null }; });
      await page.evaluate(() => window.__rompOpenSettings && window.__rompOpenSettings());
      await page.waitForFunction(() => !document.body.classList.contains("settings-open"), null, { timeout: 10000 });
      await frames(page);
      return got;
    };
    const sk = { vp: [w, h] };
    sk.marker = await page.evaluate(() => window.__rompPhoneActs === true);
    sk.head = await openRead();
    await page.evaluate(() => { delete window.__rompPhoneActs; });
    sk.older = await openRead();
    await page.evaluate(() => { window.__rompPhoneActs = true; delete window.__rompUsageReading; delete window.__rompUsagePull; });
    sk.cannotAsk = await openRead();
    out.skew = sk;
    await context.close();
  }
  // the Remote kernels glyph's colours in each theme, against the card's background and the button's fill (the Python side
  // composites and measures): the card opened from the bar's Settings, each colour read with its class set and put back
  out.contrast = {};
  for (const [name, theme] of cfg.themes || []) {
    const { context, page } = await boot(false, null, theme);
    const [w, h] = cfg.actsViewport;
    await page.setViewportSize({ width: w, height: h });
    await frames(page);
    await sleep(cfg.settleMs || 100);
    await frames(page);
    const gear = (await read(page)).controls.find((c) => c.key === "settings");
    if (!gear) throw new Error("no Settings on the bar (the contrast leg, " + name + ")");
    await page.mouse.click(gear.left + gear.w / 2, gear.top + gear.h / 2);
    await page.waitForFunction(() => document.body.classList.contains("settings-open"), null, { timeout: 20000 });
    const sf = settingsFrameOf(page);
    if (!sf) throw new Error("no settings frame after the click (the contrast leg, " + name + ")");
    await sf.waitForFunction(() => { const p = document.getElementById("rsettings"); return !!p && !p.hidden; }, null, { timeout: 10000 });
    await frames(page);
    out.contrast[name] = await sf.evaluate(() => {
      const row = document.getElementById("rs-pacts"), card = document.querySelector("#rsettings .rs-card");
      const net = document.getElementById("rs-pact-net"), me = net && net.querySelector(".rn-me");
      const res = { light: document.body.classList.contains("theme-light"), rowShown: !!row && !row.hidden && getComputedStyle(row).display !== "none",
                    card: card ? getComputedStyle(card).backgroundColor : null, fill: null, colours: {} };
      if (!net || !me) return res;
      // one colour: the element's transitions off (the button's colour and fill fade over 0.12s), the class set, the computed
      // value read, and everything put back
      const readAs = (el, set, prop) => { const was = el.getAttribute("class"), tr = el.style.transition;
        el.style.transition = "none"; set(); const v = getComputedStyle(el)[prop];
        if (was === null) el.removeAttribute("class"); else el.setAttribute("class", was);
        el.style.transition = tr; return v; };
      res.fill = readAs(net, () => {}, "backgroundColor");
      res.colours.lit = readAs(net, () => net.classList.add("on"), "color");
      res.colours.attaching = readAs(net, () => net.classList.add("busy"), "color");
      res.colours.connected = readAs(me, () => me.setAttribute("class", "rn-me rn-ok"), "fill");
      res.colours.dialing = readAs(me, () => me.setAttribute("class", "rn-me rn-wait"), "fill");
      res.colours["needs you"] = readAs(me, () => me.setAttribute("class", "rn-me rn-warn"), "fill");
      return res;
    });
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
    // the settings card from the rail's gear: its row of the phone's moved actions is not displayed here
    const rg = out.rail[out.rail.length - 1].acts.find((a) => a.id === "rail-gear");
    if (rg) {
      await page.mouse.click(rg.left + rg.w / 2, rg.top + rg.h / 2);
      const opened = await page.waitForFunction(() => document.body.classList.contains("settings-open"), null, { timeout: 20000 }).then(() => true, () => false);
      const sf = settingsFrameOf(page);
      let card = null;
      if (opened && sf) {
        await sf.waitForFunction(() => { const p = document.getElementById("rsettings"); return !!p && !p.hidden; }, null, { timeout: 10000 });
        await frames(page);
        card = await sf.evaluate(() => { const row = document.getElementById("rs-pacts");
          return { row: !!row, hidden: row ? row.hidden : null, display: row ? getComputedStyle(row).display : null,
                   boxes: row ? Array.from(row.querySelectorAll("button")).map((b) => { const c = b.getBoundingClientRect(); return [c.width, c.height]; }) : [] }; });
      }
      out.rail[out.rail.length - 1].card = { opened, card };
    }
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
