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
// Then the glyph's marching and unlit states, on the same page: with the card open, a host attaching (cfg.tunnelsAttach), the
// glyph's classes beside the rail's and its connector path's computed animation, dashes and running animations; the hosts
// settled (cfg.tunnelsDrop) and read again; no host at all (cfg.tunnelsNone) and read again; then the hosts back up, the card
// closed, no host again, and the glyph read at the card's next opening.
// Then Usage with no reading, on a page of its own at cfg.actsViewport: the shell's usage pull (the main frame's GET under
// /usage/) answers no rows, so the shell holds no reading (the rail's readout, which renders over the readings, read empty as
// the premise); the card opened from the bar's Settings, its Usage button read once the opening's ask has ended (disabled,
// its sub-line), a click at its centre, and after a settle (an absence has no event to wait on) the card, the Usage modal
// and the phoneAct messages the shell heard read; then a script's clicks on the disabled Usage (click() on its label, a click
// event dispatched on the button and on its glyph), each read the same way; then, the card still open, a reading arrives (the lab's own GET /usage
// payload posted to the shell as the timeline posts it, the shell's later pulls let through), Usage read again in the open
// card; then the readings emptied (a payload with no window and no spend, posted the same way) and filled again, Usage read
// after each; then, each from an opening, the readings emptied and filled while the Token usage panel stands over the card
// (#ra-open, #ra-close), Usage read after each close; and one click on it, its effect read.
// Then a reading the kernel holds and the shell has not pulled, on a page of its own at cfg.actsViewport: the shell's boot
// pull answers no rows and every later one goes to the lab, the Sessions pane unloaded (read as the premise); the card
// opened, its ask for a fresh pull held while Usage is read (the romp loader in the name's place, its animations, the
// button disabled and busy) and tapped at its centre, the shell's side read after a settle, then let through, Usage read once
// the ask has ended, and one click on it, its effect read.
// Then the reads that fail, on a page of its own at cfg.actsViewport: the shell's boot pull answers no rows, and the card is
// opened over an opening's pull answered with an error status (cfg.errorStatus), one failed in transit (the route aborts it),
// and one never answered (held) under a shorter bound set on the shell (window.__rompUsagePullMs = cfg.hangMs), Usage read
// once each ask has ended (the hung one also while it is held, with the time from the click to the loader's end), and after
// each of the three over a pull answered ok with no rows, Usage read again; then three times the card opened over a held
// pull, closed, and opened again over a later pull (answered with no rows, failed in transit, reaching the lab), Usage read
// before and after the held pull ends (failed in transit, answered ok with no rows, answered with cfg.errorStatus); then over a
// pull that reaches the lab, Usage read again; then, that reading in the shell, over a pull failed in transit, Usage read and
// clicked, its effect read.
// Then the deploy skew, on a page of its own at cfg.actsViewport: the shell's marker beside its phoneAct listener
// (window.__rompPhoneActs) read, and the card's row read at an opening with the marker, at one with it deleted (a parent with
// the phone layout and no marker), and Usage at one with the marker back and the usage script's two names deleted (a shell that
// cannot be asked for a reading); then, the card open and the marker deleted, the shell's layout word ({romp:'link'}) posted to
// the card from the settings frame's own window, from the chat pane's window and from the shell's, the row read after each.
// Then the row following the layout while the card is open, on a page of its own in a plain context (a fine pointer): the card
// opened at cfg.actsViewport, the window widened to cfg.wideViewport and narrowed back with the card open, a host dropping
// while it is wide (the shell's GET /tunnels answering cfg.tunnels2, then cfg.tunnelsDrop), and the row, the glyph and Usage
// read after each turn; then the window widened, and from an opening at that width narrowed, while the Token usage panel
// stands over the card, the row read after each close (and Usage after the second).
// Then the Remote kernels glyph's colours, on a page of its own per theme (cfg.themes: the theme written to the store before
// the page parses, as the gear writes it) at cfg.actsViewport: the card opened from the bar's Settings, and in it the card's
// background, the button's own fill (the glyph sits on it) and each colour the glyph can wear, as computed values: the
// glyph lit and attaching (its svg's colour, the strokes' currentColor) and each node's fill as connected, dialing and needs you,
// each read with that class set on the element and the element's transitions off, then put back; then the same with the
// pointer moved onto the button's centre (its transitions off first): its hovered fill, its colours, and whether :hover holds;
// then, the pointer moved off, the card opened again over each answer to the opening's pull (held, the lab's reading, no rows,
// an error status), the window taken through cfg.heightWidths in each, and at each width the row's height, Usage's box beside
// Remote kernels' height, the tabs' offset in the card and their top in the window, and the line Usage shows.
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
      // Usage's colour fades over the dress's transition when its ask ends (from the disabled grey): read the row once every
      // transition on its buttons ends (the glyph's accent is on its svg, which has none)
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
        // the glyph's colour is its svg's (the accent goes on the glyph alone; the button's label keeps the card's text colour)
        const net = document.getElementById("rs-pact-net"), netSvg = net && net.querySelector("svg");
        const glyph = net ? { cls: net.getAttribute("class"), color: netSvg ? getComputedStyle(netSvg).color : null,
          nodes: ["rn-me", "rn-a", "rn-b"].map((k) => { const e = net.querySelector("." + k); return e ? { cls: e.getAttribute("class"), fill: getComputedStyle(e).fill } : null; }) } : null;
        return { rowShown: !!row && !row.hidden && getComputedStyle(row).display !== "none", buttons, glyph, dress, usage,
                 card: cr ? { left: r(cr.left + ctx.left), right: r(cr.right + ctx.left), top: r(cr.top + ctx.top), bottom: r(cr.bottom + ctx.top) } : null,
                 tab: (document.querySelector("#rs-tabs .rs-tab.on") || {}).textContent || "" };
      }, lift);
      // the rail's own glyph, painted by the same poll (display:none on the phone, its computed colours still resolve), its
      // colour read on its svg as the card's is
      run.rail = await page.evaluate(() => { const n = document.getElementById("rail-net"), s = n.querySelector("svg");
        return { cls: n.getAttribute("class"), color: s ? getComputedStyle(s).color : null,
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
    // the glyph's marching and unlit states (PR 976's round 1, tests-2 and fresh-2), each read from the poll that brings it.
    // With the card open: cfg.tunnelsAttach, the host that answered with no kernel now attaching (a busy turn with no drop: the
    // drop cue fires only for a host that was up), the card's glyph read beside the rail's, with its connector path's computed
    // animation and dashes and the animations it runs (an open card: a hidden one runs none); then cfg.tunnelsDrop again, both
    // hosts settled, the same read; then cfg.tunnelsNone, no host at all, the glyph read with the card open. Then the hosts
    // back up (cfg.tunnels2), the card closed, cfg.tunnelsNone again, and the glyph read at the card's next opening. An empty
    // list drops no host either, so no flash crosses the reads. Each wait records its outcome, so a red run lists every line.
    {
      const sf = settingsFrame();
      const st = {};
      const gear = acts.bar.controls.find((c) => c.key === "settings");
      const railTurns = (pred) => page.waitForFunction(pred, null, { timeout: 15000 }).then(() => true, () => false);
      const railCls = () => page.evaluate(() => document.getElementById("rail-net").getAttribute("class"));
      const glyphState = () => sf.evaluate(() => { const n = document.getElementById("rs-pact-net"); if (!n) return null;
        const p = n.querySelector("svg path"), cs = p ? getComputedStyle(p) : null;
        return { cls: n.getAttribute("class"), cardHidden: document.getElementById("rsettings").hidden,
                 anim: cs ? cs.animationName : null, dash: cs ? cs.strokeDasharray : null,
                 runs: p && p.getAnimations ? p.getAnimations().map((a) => (a.animationName || "?") + ":" + a.playState) : null }; });
      const openCard = async () => {
        await clickCentre(gear);
        await page.waitForFunction(() => document.body.classList.contains("settings-open"), null, { timeout: 20000 });
        await sf.waitForFunction(() => { const p = document.getElementById("rsettings"); return !!p && !p.hidden; }, null, { timeout: 10000 });
        await frames(page);
      };
      const closeCard = async () => {
        await page.evaluate(() => window.__rompOpenSettings && window.__rompOpenSettings());
        await page.waitForFunction(() => !document.body.classList.contains("settings-open"), null, { timeout: 10000 });
        await frames(page);
      };
      await openCard();
      answer = cfg.tunnelsAttach;
      st.attachPolled = await railTurns(() => document.getElementById("rail-net").classList.contains("busy"));
      await frames(page);
      st.attaching = { card: await glyphState(), rail: await railCls() };
      answer = cfg.tunnelsDrop;
      st.settledPolled = await railTurns(() => !document.getElementById("rail-net").classList.contains("busy"));
      await frames(page);
      st.settled = { card: await glyphState(), rail: await railCls() };
      answer = cfg.tunnelsNone;
      st.nonePolled = await railTurns(() => !document.getElementById("rail-net").classList.contains("on"));
      await frames(page);
      st.noneOpen = { card: await glyphState(), rail: await railCls() };
      answer = cfg.tunnels2;
      st.backUp = await railTurns(() => document.getElementById("rail-net").classList.contains("on"));
      await frames(page);
      st.upBeforeClose = await glyphState();
      await closeCard();
      answer = cfg.tunnelsNone;
      st.noneClosedPolled = await railTurns(() => !document.getElementById("rail-net").classList.contains("on"));
      await frames(page);
      st.noneClosed = await glyphState();
      await openCard();
      st.noneReopened = { card: await glyphState(), rail: await railCls() };
      await closeCard();
      acts.states = st;
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
        const er = document.getElementById("rs-pact-usage-err"), row = document.getElementById("rs-pacts");
        if (!b) return null;
        const c = b.getBoundingClientRect();
        return { disabled: b.disabled, busy: b.getAttribute("aria-busy"), left: r(c.left + ctx.left), top: r(c.top + ctx.top), w: r(c.width), h: r(c.height),
                 rowH: row ? r(row.getBoundingClientRect().height) : null,
                 line: un ? { shown: !un.hidden && getComputedStyle(un).display !== "none", text: un.textContent.trim() } : null,
                 err: er ? { shown: !er.hidden && getComputedStyle(er).display !== "none", text: er.textContent.trim() } : null,
                 wait: wt ? { shown: !wt.hidden && getComputedStyle(wt).display !== "none", text: wt.textContent.trim(),
                              anims: wt.getAnimations ? wt.getAnimations({ subtree: true }).map((a) => a.animationName || "?") : null } : null };
      }, lift);
    };
    const shellNow = async (sf) => ({ settingsOpen: await page.evaluate(() => document.body.classList.contains("settings-open")),
      cardHidden: await sf.evaluate(() => { const p = document.getElementById("rsettings"); return !p || p.hidden; }),
      usage: await page.evaluate(() => { const b = document.getElementById("ru-back"); return !!b && b.classList.contains("on"); }),
      acts: await page.evaluate(() => window.__mtabsActs.slice()) });
    const askEnded = (sf) => sf.waitForFunction(() => { const w = document.getElementById("rs-pact-usage-wait"); return !w || w.hidden; }, null, { timeout: 10000 }).then(() => true, () => false);
    const closeCard = async () => {
      await page.evaluate(() => window.__rompOpenSettings && window.__rompOpenSettings());
      await page.waitForFunction(() => !document.body.classList.contains("settings-open"), null, { timeout: 10000 });
      await frames(page);
    };
    const modalUp = () => page.waitForFunction(() => { const b = document.getElementById("ru-back"), t = document.getElementById("ru-tip"); return !!b && b.classList.contains("on") && !!t && t.classList.contains("ru-modal") && t.style.display === "block"; }, null, { timeout: 10000 }).then(() => true, () => false);
    return { openCard, usageNow, shellNow, askEnded, modalUp, closeCard };
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
      // ...then a script's clicks on the disabled Usage (romp-manager's ruling after PR 976's round 1: a click a script
      // dispatches reaches the row's handler, which must return on a disabled button): click() on its label, a click event
      // dispatched on the button and on its glyph, each read after a settle with the phoneAct messages it alone brought. A
      // dispatch that closed the card is followed by an opening, so the next one, and the rest of the leg, meet the card open
      nr.dispatched = [];
      for (const road of ["label", "button", "glyph"]) {
        const had = (await kit.shellNow(sf)).acts.length;
        const ran = await sf.evaluate((how) => {
          const b = document.querySelector("#rs-pacts [data-pact=usage]");
          if (!b) return { ran: false };
          const label = Array.from(b.querySelectorAll("span")).find((n) => !n.children.length && n.textContent.trim() === "Usage");
          const target = how === "label" ? label : how === "glyph" ? b.querySelector("svg") : b;
          if (!target) return { ran: false, disabled: b.disabled };
          const disabled = b.disabled;
          if (how === "label") target.click(); else target.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
          return { ran: true, disabled };
        }, road);
        await frames(page);
        await sleep(3 * (cfg.settleMs || 100));
        await frames(page);
        const after = await kit.shellNow(sf);
        nr.dispatched.push({ road, ...ran, settingsOpen: after.settingsOpen, cardHidden: after.cardHidden, usage: after.usage, acts: after.acts.slice(had) });
        if (!after.settingsOpen || after.cardHidden) {
          await page.evaluate(() => { try { window.__rompUsageClose && window.__rompUsageClose(); } catch (e) { /* no modal */ } });
          await page.waitForFunction(() => !document.body.classList.contains("settings-open"), null, { timeout: 10000 }).catch(() => null);
          await frames(page);
          await kit.openCard();
          await kit.askEnded(sf);
          await frames(page);
        }
      }
      // each dispatch kept the phoneAct messages it brought; the record starts empty again for the leg's later reads
      await page.evaluate(() => { window.__mtabsActs.length = 0; });
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
    // ...then the readings changing while the Token usage panel stands over the card (the check of PR 976's round 1 fixes): the
    // panel hides the card with no word to the shell and its close shows it again. Each turn starts at an opening, which reads
    // Usage afresh in any tree: the card closed and opened again from the bar's Settings with the readings filled (Usage
    // enabled, read once the opening's ask has ended), the panel opened (#ra-open's own click), the readings emptied while it
    // is up, the panel closed (#ra-close's) and Usage read in the card it shows; then the card opened again with the shell's
    // pull answering no rows (Usage disabled with its line), the panel opened, the readings filled while it is up, the panel
    // closed and Usage read. The click below lands on the last Usage read
    {
      const pn = {};
      const raOpen = () => sf.evaluate(() => { const b = document.getElementById("ra-open"), back = document.getElementById("ranalytics-back");
        if (!b) return false; b.click(); return !!back && !back.hidden && document.getElementById("rsettings").hidden; });
      const raClose = () => sf.evaluate(() => { const b = document.getElementById("ra-close"), back = document.getElementById("ranalytics-back");
        if (!b) return false; b.click(); return !!back && back.hidden && !document.getElementById("rsettings").hidden; });
      const reopen = async () => {
        await page.evaluate(() => window.__rompOpenSettings && window.__rompOpenSettings());
        await page.waitForFunction(() => !document.body.classList.contains("settings-open"), null, { timeout: 10000 });
        await frames(page);
        await kit.openCard();
        const asked = await kit.askEnded(sf);
        await frames(page);
        return { asked, usage: await kit.usageNow(sf) };
      };
      pn.fullStart = await reopen();
      pn.opened = await raOpen();
      await post(true);
      pn.emptiedReadout = await readout(false);
      await frames(page);
      pn.closed = await raClose();
      await frames(page);
      pn.emptied = await kit.usageNow(sf);
      empty = true;   // the opening's pull answers no rows from here (the route above), so the next opening holds no reading
      pn.emptyStart = await reopen();
      pn.opened2 = await raOpen();
      await post(false);
      pn.filledReadout = await readout(true);
      await frames(page);
      pn.closed2 = await raClose();
      await frames(page);
      pn.filled = await kit.usageNow(sf);
      empty = false;
      nr.panel = pn;
    }
    const last = (nr.panel && nr.panel.filled) || nr.refilled;
    if (last) {
      await page.mouse.click(last.left + last.w / 2, last.top + last.h / 2);
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
    // a tap on Usage while the pull is held: the button is disabled, so the browser dispatches no click for the tap (and the
    // row's handler returns on a disabled button besides), the card stays open and no phoneAct is posted; read after a settle,
    // since an absence has no event to wait on
    if (up.during) {
      await page.mouse.click(up.during.left + up.during.w / 2, up.during.top + up.during.h / 2);
      await frames(page);
      await sleep(3 * (cfg.settleMs || 100));
      await frames(page);
      up.tappedDuring = await kit.shellNow(sf);
    }
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
  // the reads that fail (romp-manager's rulings after PR 976's round 1), on a page of its own at cfg.actsViewport: the shell's
  // boot pull answers no rows, so it holds no reading (the rail's readout read empty as the premise). Then the card opened from
  // the bar's Settings over each way the opening's pull can fail, Usage read once its ask has ended and the card closed: the
  // kernel answering with an error status (cfg.errorStatus); the request failing in transit (aborted by the route); and the
  // kernel never answering (the request held), under a shorter bound set on the shell (window.__rompUsagePullMs = cfg.hangMs),
  // with Usage read while it is held, the time from the click to the loader's end, and Usage after it. After each of the three,
  // an opening whose pull the kernel answers ok with no rows, Usage read there: No reading yet alone shows that an ok answer
  // clears the failure (a flag an ok answer left set would say Couldn't load there), and the next failure starts from a read
  // that did not fail, so its own line shows that it set the flag itself, not a failure before it. Then the reopen race, twice
  // (its comment below). Then an opening whose pull reaches the lab (a reading), where Usage is read once more: enabled, with
  // neither line
  {
    let mode = "boot", boots = 0;
    const held = [];
    const { context, page } = await boot(false, (pg) => pg.route((url) => url.pathname.startsWith("/usage/"), (route) => {
      if (route.request().frame() !== pg.mainFrame()) return route.continue();
      if (mode === "boot") { boots++; return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ rows: [], host: "" }) }); }
      if (mode === "status") return route.fulfill({ status: cfg.errorStatus, contentType: "application/json", body: JSON.stringify({ error: "synthetic failure" }) });
      if (mode === "transit") return route.abort("failed");
      if (mode === "empty") return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ rows: [], host: "" }) });
      if (mode === "hang") { held.push(route); return undefined; }
      return route.continue();
    }));
    const [w, h] = cfg.actsViewport;
    await page.setViewportSize({ width: w, height: h });
    await frames(page);
    await sleep(cfg.settleMs || 100);
    await frames(page);
    const fr = { vp: [w, h] };
    for (let i = 0; i < 150 && boots < 1; i++) await sleep(100);
    await frames(page);
    fr.premise = { boots, readout: await page.evaluate(() => { const r = document.getElementById("rail-usage"); return r ? r.innerHTML : null; }) };
    const kit = await usageKit(page, "the failed-read leg");
    const turn = async (m) => {
      mode = m;
      const sf = await kit.openCard();
      const asked = await kit.askEnded(sf);
      await frames(page);
      const got = { asked, usage: await kit.usageNow(sf), shell: await kit.shellNow(sf) };
      await kit.closeCard();
      return got;
    };
    fr.status = await turn("status");
    fr.okAfterStatus = await turn("empty");
    fr.transit = await turn("transit");
    fr.okAfterTransit = await turn("empty");
    // the hung pull: the bound set short on the shell, the request held and never answered
    {
      const hg = { ms: cfg.hangMs };
      mode = "hang";
      await page.evaluate((ms) => { window.__rompUsagePullMs = ms; }, cfg.hangMs);
      const t0 = Date.now();
      const sf = await kit.openCard();
      for (let i = 0; i < 50 && !held.length; i++) await sleep(100);
      hg.held = held.length;
      hg.during = await kit.usageNow(sf);
      hg.ended = await sf.waitForFunction(() => { const x = document.getElementById("rs-pact-usage-wait"); return !!x && x.hidden; }, null, { timeout: cfg.hangWaitMs }).then(() => true, () => false);
      hg.elapsed = Date.now() - t0;
      await frames(page);
      hg.after = await kit.usageNow(sf);
      hg.shell = await kit.shellNow(sf);
      await kit.closeCard();
      await page.evaluate(() => { delete window.__rompUsagePullMs; });
      for (const route of held.splice(0)) { try { await route.abort(); } catch (e) { /* the page aborted it first */ } }
      fr.hang = hg;
    }
    fr.okAfterHang = await turn("empty");
    // the reopen race (the check of PR 976's decisions after round 1): the card's pull A held, the card closed and opened
    // again over pull B, B ended and Usage read; then A ends, and Usage is read again. Three turns: B answered no rows and A
    // failing in transit (its route aborted); B failing in transit and A answered ok with no rows; B reaching the lab (a
    // reading) and A answered with an error status. B started after A and has ended, so A changes neither the flag nor, with
    // an error status, the readings: Usage keeps B's answer (No reading yet, Couldn't load, enabled with neither line). A
    // wrapper over the shell's pull (the card calls whatever window.__rompUsagePull holds at each opening) records the order
    // the two pulls end in, and when A's end has run in the shell, the event Usage is read after; A's bound is set long here
    // (window.__rompUsagePullMs = cfg.raceMs), so that A ends when its route ends it and not on its own
    {
      await page.evaluate((ms) => {
        window.__rompUsagePullMs = ms;
        const ask = window.__rompUsagePull; window.__mtabsAsk = ask; window.__mtabsEnds = 0;
        window.__rompUsagePull = function () {
          const rec = { end: null, at: 0 }; window.__mtabsPulls.push(rec);
          const p = ask.apply(this, arguments);
          Promise.resolve(p).then(() => { rec.end = "answered"; rec.at = ++window.__mtabsEnds; }, () => { rec.end = "failed"; rec.at = ++window.__mtabsEnds; });
          return p;
        };
      }, cfg.raceMs);
      const race = async (bMode, endA) => {
        const rc = {};
        await page.evaluate(() => { window.__mtabsPulls = []; });
        mode = "hang";
        await kit.openCard();
        for (let i = 0; i < 50 && !held.length; i++) await sleep(100);
        rc.held = held.length;
        await kit.closeCard();
        mode = bMode;
        const sf = await kit.openCard();
        rc.bAsked = await kit.askEnded(sf);
        await frames(page);
        rc.afterB = await kit.usageNow(sf);
        for (const route of held.splice(0)) { try { await endA(route); } catch (e) { /* the page ended it first */ } }
        rc.aEnded = await page.waitForFunction(() => window.__mtabsPulls.length >= 2 && window.__mtabsPulls[0].end !== null, null, { timeout: 10000 }).then(() => true, () => false);
        rc.pulls = await page.evaluate(() => window.__mtabsPulls.map((r) => ({ end: r.end, at: r.at })));
        await frames(page);
        rc.afterA = await kit.usageNow(sf);
        rc.shell = await kit.shellNow(sf);
        await kit.closeCard();
        return rc;
      };
      fr.raceTransit = await race("empty", (route) => route.abort("failed"));
      fr.raceOk = await race("transit", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ rows: [], host: "" }) }));
      fr.raceStatus = await race("lab", (route) => route.fulfill({ status: cfg.errorStatus, contentType: "application/json", body: JSON.stringify({ error: "synthetic failure" }) }));
      await page.evaluate(() => { window.__rompUsagePull = window.__mtabsAsk; delete window.__mtabsAsk; delete window.__rompUsagePullMs; });
    }
    fr.lab = await turn("lab");
    // ...and a failed read over a cached reading (romp-manager's decision on PR 976's round 1 builds): the shell holds the lab's
    // reading now, and the card opened over a pull that fails in transit (which leaves the readings as they were), Usage read
    // once the ask has ended with the shell's side, then one click on it and its effect read. Last on this page: the click
    // closes the card
    {
      const cd = {};
      mode = "transit";
      const sf = await kit.openCard();
      cd.asked = await kit.askEnded(sf);
      await frames(page);
      cd.reading = await page.evaluate(() => typeof window.__rompUsageReading === "function" && window.__rompUsageReading());
      cd.usage = await kit.usageNow(sf);
      cd.shell = await kit.shellNow(sf);
      if (cd.usage) {
        await page.mouse.click(cd.usage.left + cd.usage.w / 2, cd.usage.top + cd.usage.h / 2);
        cd.opened = await kit.modalUp();
        await frames(page);
        cd.clicked = await kit.shellNow(sf);
      }
      fr.cached = cd;
    }
    out.failedReads = fr;
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
    // ...then the layout word's source (romp-manager's ruling after PR 976's round 1): the card's {romp:'link'} listener acts on
    // the word from the shell's own window alone. The card opened with its row shown (the marker is back) and the marker then
    // deleted, so a word the listener acts on hides the row (the predicate it re-reads turns false). The word posted from the
    // settings frame's own window, then from the chat pane's window, each followed from that same window by a probe word the
    // card records as it arrives (posted after the word, so delivered after it), and the row read once the probe is in; then
    // the word from the shell's window, which hides the row (the control: the listener is live), and with the marker restored
    // the same word shows it again; the card closed
    {
      const ln = {};
      await page.mouse.click(gear.left + gear.w / 2, gear.top + gear.h / 2);
      await page.waitForFunction(() => document.body.classList.contains("settings-open"), null, { timeout: 20000 });
      const sf = settingsFrameOf(page);
      if (!sf) throw new Error("no settings frame after the click (the skew leg's layout word)");
      await sf.waitForFunction(() => { const p = document.getElementById("rsettings"); return !!p && !p.hidden; }, null, { timeout: 10000 });
      await frames(page);
      const rowShown = () => sf.evaluate(() => { const row = document.getElementById("rs-pacts"); return !!row && !row.hidden && getComputedStyle(row).display !== "none"; });
      const rowIs = (want) => sf.waitForFunction((w) => { const row = document.getElementById("rs-pacts"); return !!row && (!row.hidden && getComputedStyle(row).display !== "none") === w; }, want, { timeout: 5000 }).then(() => true, () => false);
      const probeIn = (n) => sf.waitForFunction((k) => (window.__mtabsProbes || []).includes(k), n, { timeout: 5000 }).then(() => true, () => false);
      ln.start = await rowShown();
      await sf.evaluate(() => { window.__mtabsProbes = []; window.addEventListener("message", (e) => { if (e.data && e.data.romp === "mtabs-probe") window.__mtabsProbes.push(e.data.n); }); });
      await page.evaluate(() => { delete window.__rompPhoneActs; });
      await sf.evaluate(() => { window.postMessage({ romp: "link", link: "", mob: false }, "*"); window.postMessage({ romp: "mtabs-probe", n: 1 }, "*"); });
      ln.selfArrived = await probeIn(1);
      await frames(page);
      ln.self = await rowShown();
      const chat = page.frames().find((f) => f !== page.mainFrame() && /\/chat/.test(f.url()));
      ln.chatFrame = !!chat;
      if (chat) {
        await chat.evaluate(() => { const t = window.parent.document.getElementById("f-settings").contentWindow;
          t.postMessage({ romp: "link", link: "", mob: false }, "*"); t.postMessage({ romp: "mtabs-probe", n: 2 }, "*"); });
        ln.paneArrived = await probeIn(2);
        await frames(page);
        ln.pane = await rowShown();
      }
      await page.evaluate(() => { document.getElementById("f-settings").contentWindow.postMessage({ romp: "link", link: "", mob: false }, "*"); });
      ln.parentHid = await rowIs(false);
      await page.evaluate(() => { window.__rompPhoneActs = true; document.getElementById("f-settings").contentWindow.postMessage({ romp: "link", link: "", mob: false }, "*"); });
      ln.parentShowed = await rowIs(true);
      await page.evaluate(() => window.__rompOpenSettings && window.__rompOpenSettings());
      await page.waitForFunction(() => !document.body.classList.contains("settings-open"), null, { timeout: 10000 });
      sk.link = ln;
    }
    out.skew = sk;
    await context.close();
  }
  // the row follows the layout while the card is open (PR 976's round 1, correctness-2 and ui-1): a plain context (a fine
  // pointer, so the layout query turns at 820px wide), the shell's own GET /tunnels answering cfg.tunnels2 (both hosts up),
  // the card opened from the bar's Settings at cfg.actsViewport, then the window widened to cfg.wideViewport with the card open,
  // a host dropping there (cfg.tunnelsDrop) while the row is hidden, and the window narrowed to cfg.actsViewport again; the row
  // read after each turn once it has had the time to follow (each wait records its outcome), and after the narrowing the glyph
  // two frames on (no flash for the drop it could not show) and Usage once its ask has ended
  {
    let answer = cfg.tunnels2;
    const context = await browser.newContext({ viewport: { width: cfg.actsViewport[0], height: cfg.actsViewport[1] } });
    const page = await context.newPage();
    page.on("pageerror", (e) => { if (out.errors.length < 40) out.errors.push(String(e).slice(0, 300)); });
    await page.route("**/tunnels", (route) => {
      const q = route.request();
      if (q.method() !== "GET" || q.frame() !== page.mainFrame()) return route.continue();
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(answer) });
    });
    await page.goto(cfg.url, { waitUntil: "load", timeout: 40000 });
    await page.waitForSelector("#mtabs", { timeout: 20000 });
    await page.waitForFunction(() => { const b = document.getElementById("romp-boot"); return !b || b.classList.contains("gone"); }, null, { timeout: 30000 });
    await page.evaluate(() => (document.fonts ? document.fonts.ready.then(() => true) : true));
    await page.waitForFunction(() => { const a = document.querySelector("#rail-net .rn-a"); return !!a && a.getAttribute("class") === "rn-a rn-ok"; }, null, { timeout: 15000 });
    await frames(page);
    const fl = { vp: cfg.actsViewport, wide: cfg.wideViewport };
    const gear = (await read(page)).controls.find((c) => c.key === "settings");
    if (!gear) throw new Error("no Settings on the bar (the layout leg)");
    await page.mouse.click(gear.left + gear.w / 2, gear.top + gear.h / 2);
    await page.waitForFunction(() => document.body.classList.contains("settings-open"), null, { timeout: 20000 });
    const sf = settingsFrameOf(page);
    if (!sf) throw new Error("no settings frame after the click (the layout leg)");
    await sf.waitForFunction(() => { const p = document.getElementById("rsettings"); return !!p && !p.hidden; }, null, { timeout: 10000 });
    await frames(page);
    const rowNow = async () => ({ mobile: await page.evaluate(() => (window.__rompMobileOn ? window.__rompMobileOn() : null)),
      open: await sf.evaluate(() => { const p = document.getElementById("rsettings"); return !!p && !p.hidden; }),
      ...(await sf.evaluate(() => { const row = document.getElementById("rs-pacts");
        return { rowShown: !!row && !row.hidden && getComputedStyle(row).display !== "none",
                 boxes: row ? Array.from(row.querySelectorAll("button")).map((b) => { const c = b.getBoundingClientRect(); return [c.width, c.height]; }) : [] }; })) });
    const rowIs = (shown) => sf.waitForFunction((want) => { const row = document.getElementById("rs-pacts");
      return !!row && (!row.hidden && getComputedStyle(row).display !== "none") === want; }, shown, { timeout: 5000 }).then(() => true, () => false);
    fl.phone = await rowNow();
    await page.setViewportSize({ width: cfg.wideViewport[0], height: cfg.wideViewport[1] });
    fl.hid = await rowIs(false);
    await frames(page);
    fl.wideRow = await rowNow();
    answer = cfg.tunnelsDrop;
    fl.dropped = await page.waitForFunction(() => { const a = document.querySelector("#rail-net .rn-a"); return !!a && a.getAttribute("class") === "rn-a rn-warn"; }, null, { timeout: 15000 }).then(() => true, () => false);
    await frames(page);
    fl.dropCls = await sf.evaluate(() => { const n = document.getElementById("rs-pact-net"); return n ? n.getAttribute("class") : null; });
    await page.setViewportSize({ width: cfg.actsViewport[0], height: cfg.actsViewport[1] });
    fl.showed = await rowIs(true);
    await frames(page);
    await frames(page);
    fl.narrowRow = await rowNow();
    fl.glyph = await sf.evaluate(() => { const n = document.getElementById("rs-pact-net"); if (!n) return null;
      return { cls: n.getAttribute("class"), anims: n.getAnimations ? n.getAnimations().map((a) => (a.animationName || "?") + ":" + a.playState) : null }; });
    fl.asked = await sf.waitForFunction(() => { const w = document.getElementById("rs-pact-usage-wait"); return !w || w.hidden; }, null, { timeout: 10000 }).then(() => true, () => false);
    fl.usage = await sf.evaluate(() => { const b = document.getElementById("rs-pact-usage"), un = document.getElementById("rs-pact-usage-none");
      return b ? { disabled: b.disabled, line: un ? { shown: !un.hidden && getComputedStyle(un).display !== "none" } : null } : null; });
    // ...then the same turns with the Token usage panel over the card (the check of PR 976's round 1 fixes): the panel hides
    // the card with no word to the shell and its close shows it again. The panel opened (#ra-open's own click) at the phone
    // width with the row shown, the window widened to cfg.wideViewport while it is up (the shell's layout read as turned), the
    // panel closed (#ra-close's) and the row read once it has had the time to follow; then the card closed and opened again at
    // that width (an opening reads the layout in any tree: no row), the panel opened, the window narrowed to the phone width
    // while it is up, the panel closed, and the row read, and Usage once its ask has ended
    {
      const pn = {};
      const raOpen = () => sf.evaluate(() => { const b = document.getElementById("ra-open"), back = document.getElementById("ranalytics-back");
        if (!b) return false; b.click(); return !!back && !back.hidden && document.getElementById("rsettings").hidden; });
      const raClose = () => sf.evaluate(() => { const b = document.getElementById("ra-close"), back = document.getElementById("ranalytics-back");
        if (!b) return false; b.click(); return !!back && back.hidden && !document.getElementById("rsettings").hidden; });
      const mobileIs = (want) => page.waitForFunction((w) => !!window.__rompMobileOn && window.__rompMobileOn() === w, want, { timeout: 5000 }).then(() => true, () => false);
      const under = () => sf.evaluate(() => { const back = document.getElementById("ranalytics-back");
        return { panel: !!back && !back.hidden, cardHidden: document.getElementById("rsettings").hidden }; });
      pn.start = await rowNow();
      pn.opened = await raOpen();
      await page.setViewportSize({ width: cfg.wideViewport[0], height: cfg.wideViewport[1] });
      pn.wideTurned = await mobileIs(false);
      await frames(page);
      await frames(page);
      pn.wideUnder = await under();
      pn.closed = await raClose();
      pn.hid = await rowIs(false);
      await frames(page);
      pn.wideRow = await rowNow();
      await page.evaluate(() => window.__rompOpenSettings && window.__rompOpenSettings());
      await page.waitForFunction(() => !document.body.classList.contains("settings-open"), null, { timeout: 10000 });
      await frames(page);
      await page.evaluate(() => window.__rompOpenSettings && window.__rompOpenSettings());
      await page.waitForFunction(() => document.body.classList.contains("settings-open"), null, { timeout: 20000 });
      await sf.waitForFunction(() => { const p = document.getElementById("rsettings"); return !!p && !p.hidden; }, null, { timeout: 10000 });
      await frames(page);
      pn.wideOpened = await rowNow();
      pn.opened2 = await raOpen();
      await page.setViewportSize({ width: cfg.actsViewport[0], height: cfg.actsViewport[1] });
      pn.narrowTurned = await mobileIs(true);
      await frames(page);
      await frames(page);
      pn.narrowUnder = await under();
      pn.closed2 = await raClose();
      pn.showed = await rowIs(true);
      await frames(page);
      pn.narrowRow = await rowNow();
      pn.asked = await sf.waitForFunction(() => { const w = document.getElementById("rs-pact-usage-wait"); return !w || w.hidden; }, null, { timeout: 10000 }).then(() => true, () => false);
      pn.usage = await sf.evaluate(() => { const b = document.getElementById("rs-pact-usage"), un = document.getElementById("rs-pact-usage-none");
        return b ? { disabled: b.disabled, busy: b.getAttribute("aria-busy"), line: un ? { shown: !un.hidden && getComputedStyle(un).display !== "none" } : null } : null; });
      fl.panel = pn;
    }
    out.follow = fl;
    await context.close();
  }
  // the Remote kernels glyph's colours in each theme, against the card's background and the button's fill (the Python side
  // composites and measures): the card opened from the bar's Settings, each colour read with its class set and put back, at
  // rest and with the pointer on the button
  out.contrast = {};
  for (const [name, theme] of cfg.themes || []) {
    // the shell's usage pull (its GET under /usage/), let through to the lab until the row's heights below steer it
    let usageMode = "lab";
    const usageHeld = [];
    const { context, page } = await boot(false, (pg) => pg.route((url) => url.pathname.startsWith("/usage/"), (route) => {
      if (route.request().frame() !== pg.mainFrame() || usageMode === "lab") return route.continue();
      if (usageMode === "hold") { usageHeld.push(route); return undefined; }
      if (usageMode === "empty") return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ rows: [], host: "" }) });
      return route.fulfill({ status: cfg.errorStatus, contentType: "application/json", body: JSON.stringify({ error: "synthetic failure" }) });
    }), theme);
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
    // one reading: the card's background, the button's fill and every colour the glyph can wear; with `hover`, taken while
    // the pointer rests on the button, and whether :hover holds there is reported with it
    const colours = (hover) => sf.evaluate((hv) => {
      const row = document.getElementById("rs-pacts"), card = document.querySelector("#rsettings .rs-card");
      const net = document.getElementById("rs-pact-net"), me = net && net.querySelector(".rn-me"), svg = net && net.querySelector("svg");
      const res = { light: document.body.classList.contains("theme-light"), rowShown: !!row && !row.hidden && getComputedStyle(row).display !== "none",
                    card: card ? getComputedStyle(card).backgroundColor : null, fill: null, colours: {} };
      if (hv) res.hovered = !!net && net.matches(":hover");
      if (!net || !me || !svg) return res;
      // one colour: the element's transitions off (the button's colour and fill fade over 0.12s), the class set, the computed
      // value read, and everything put back. The value is read on `from` where the colour lands on another element: the
      // glyph's svg for the button's lit and attaching states, since the accent goes on the glyph alone
      const readAs = (el, set, prop, from) => { const was = el.getAttribute("class"), tr = el.style.transition;
        el.style.transition = "none"; set(); const v = getComputedStyle(from || el)[prop];
        if (was === null) el.removeAttribute("class"); else el.setAttribute("class", was);
        el.style.transition = tr; return v; };
      res.fill = readAs(net, () => {}, "backgroundColor");
      res.colours.lit = readAs(net, () => net.classList.add("on"), "color", svg);
      res.colours.attaching = readAs(net, () => net.classList.add("busy"), "color", svg);
      res.colours.connected = readAs(me, () => me.setAttribute("class", "rn-me rn-ok"), "fill");
      res.colours.dialing = readAs(me, () => me.setAttribute("class", "rn-me rn-wait"), "fill");
      res.colours["needs you"] = readAs(me, () => me.setAttribute("class", "rn-me rn-warn"), "fill");
      return res;
    }, hover);
    out.contrast[name] = await colours(false);
    // ...and the button hovered (PR 976's round 1, extra6-2): a real pointer move onto its centre, since :hover cannot be set
    // by a class, with the button's transitions off first, so the hovered fill is read as it lands, not part way through
    const at = await sf.evaluate(() => { const n = document.getElementById("rs-pact-net"); if (!n) return null;
      n.style.transition = "none"; const c = n.getBoundingClientRect(); return { x: c.left + c.width / 2, y: c.top + c.height / 2 }; });
    const lift = await page.evaluate(() => { const r = document.getElementById("f-settings").getBoundingClientRect(); return { left: r.left, top: r.top }; });
    if (at) {
      await page.mouse.move(lift.left + at.x, lift.top + at.y);
      await frames(page);
      const hv = await colours(true);
      out.contrast[name].hover = { hovered: hv.hovered, fill: hv.fill, colours: hv.colours };
    }
    // ...then the row and the tabs in Usage's states at each phone width (romp-manager's decision on PR 976's round 1 builds:
    // hold the loader's width, so loading to a reading never moves the tabs), the pointer moved off the card first: the card
    // closed and opened again from the bar's Settings over the opening's pull held (the loader up), the window taken through
    // cfg.heightWidths with the card open and read at each, the pull let through (the lab's reading: Usage enabled) and the
    // widths read again; then the same over no rows (No reading yet) and over an error status (Couldn't load). At each: the
    // window's width, the row's height, Usage's box, its top beside Restart kernel's top and height, the tabs' offset from the
    // top of the card's content and their top in the window, and which of Usage's lines shows
    {
      const hs = {};
      await page.mouse.move(1, 1);
      const openC = async () => {
        await page.mouse.click(gear.left + gear.w / 2, gear.top + gear.h / 2);
        await page.waitForFunction(() => document.body.classList.contains("settings-open"), null, { timeout: 20000 });
        await sf.waitForFunction(() => { const p = document.getElementById("rsettings"); return !!p && !p.hidden; }, null, { timeout: 10000 });
        await frames(page);
      };
      const closeC = async () => {
        await page.evaluate(() => window.__rompOpenSettings && window.__rompOpenSettings());
        await page.waitForFunction(() => !document.body.classList.contains("settings-open"), null, { timeout: 10000 });
        await frames(page);
      };
      const ended = () => sf.waitForFunction(() => { const x = document.getElementById("rs-pact-usage-wait"); return !x || x.hidden; }, null, { timeout: 10000 }).then(() => true, () => false);
      const rowRead = () => sf.evaluate(() => {
        const shown = (el) => (el ? !el.hidden && getComputedStyle(el).display !== "none" : null);
        const row = document.getElementById("rs-pacts"), card = document.querySelector("#rsettings .rs-card"), tabs = document.getElementById("rs-tabs");
        const b = document.getElementById("rs-pact-usage"), rs = document.querySelector("#rs-pacts [data-pact=restart]");
        if (!row || !card || !b) return null;
        const rr = row.getBoundingClientRect(), cr = card.getBoundingClientRect(), br = b.getBoundingClientRect();
        return { vw: window.innerWidth, rowShown: !row.hidden && getComputedStyle(row).display !== "none", rowH: rr.height,
                 tabsAt: tabs ? tabs.getBoundingClientRect().top - cr.top + card.scrollTop : null, tabsTop: tabs ? tabs.getBoundingClientRect().top : null,
                 usageW: br.width, usageH: br.height, usageTop: br.top, restartH: rs ? rs.getBoundingClientRect().height : null,
                 restartTop: rs ? rs.getBoundingClientRect().top : null,
                 disabled: b.disabled, wait: shown(document.getElementById("rs-pact-usage-wait")), none: shown(document.getElementById("rs-pact-usage-none")),
                 err: shown(document.getElementById("rs-pact-usage-err")) };
      });
      const sweep = async () => {
        const rows = [];
        for (const x of cfg.heightWidths || []) {
          await page.setViewportSize({ width: x, height: h });
          await frames(page);
          await sleep(cfg.settleMs || 100);
          await frames(page);
          rows.push({ w: x, ...(await rowRead()) });
        }
        await page.setViewportSize({ width: w, height: h });
        await frames(page);
        return rows;
      };
      await closeC();
      // the shell's bound set long while the pull is held (cfg.raceMs), so the loader ends when the pull is let through and
      // never on the bound part way through the widths; then the bound put back
      await page.evaluate((ms) => { window.__rompUsagePullMs = ms; }, cfg.raceMs);
      usageMode = "hold";
      await openC();
      for (let i = 0; i < 50 && !usageHeld.length; i++) await sleep(100);
      hs.held = usageHeld.length;
      hs.loading = await sweep();
      usageMode = "lab";
      for (const route of usageHeld.splice(0)) await route.continue();
      hs.readingEnded = await ended();
      await page.evaluate(() => { delete window.__rompUsagePullMs; });
      hs.reading = await sweep();
      await closeC();
      usageMode = "empty";
      await openC();
      hs.noneEnded = await ended();
      hs.none = await sweep();
      await closeC();
      usageMode = "error";
      await openC();
      hs.failedEnded = await ended();
      hs.failed = await sweep();
      out.contrast[name].heights = hs;
    }
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
