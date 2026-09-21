// The browser driver for tests/test_layout_height_served.py: opens the served landing page in the named playwright
// browser as a desktop (a mouse, 1280 by 820) and as a phone (390 by 844, touch), and reads the premise the shell's
// layoutH() rests on and what the shell published from it: the document's compat mode, the root's overflow, the root
// element's clientHeight beside window.innerHeight and the visual viewport, the --app-h and --mtabs-h the mobile script
// set, and on the phone the bell popover's bottom after a tap beside the value innerHeight would have given. Prints
// one JSON line: the readings per shell, or {skipped: reason} when playwright or the browser is absent. NODE_PATH names
// the node_modules that hold playwright (the Python side sets it). Nothing here is a real session: the page is the
// kernel module's own _landing() over blank pane pages.
"use strict";
const url = process.argv[2];
const browserName = process.argv[3];

async function walk(browser, shell) {
  const errors = [];
  const ctx = await browser.newContext(shell === "phone"
    ? { viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true, deviceScaleFactor: 3 }
    : { viewport: { width: 1280, height: 820 } });
  const page = await ctx.newPage();
  page.on("pageerror", (e) => { errors.push(String((e && e.message) || e)); });
  await page.goto(url);
  await page.waitForSelector("#mtabs", { state: "attached", timeout: 20000 });   // display:none on the desktop shell: attached, not visible
  // the boot fit is synchronous, so --app-h is set once the mobile script has run; wait for it rather than for a time
  await page.waitForFunction(() => document.documentElement.style.getPropertyValue("--app-h") !== "", null, { timeout: 20000 });
  await page.evaluate(() => { const bt = document.getElementById("romp-boot"); if (bt) bt.remove(); });
  const out = await page.evaluate((isPhone) => {
    const de = document.documentElement, vv = window.visualViewport;
    const o = {
      compatMode: document.compatMode,
      rootOverflow: getComputedStyle(de).overflow, bodyOverflow: getComputedStyle(document.body).overflow,
      clientHeight: de.clientHeight, innerHeight: window.innerHeight,
      vvHeight: vv ? vv.height : null, vvScale: vv ? vv.scale : null,
      coarse: window.matchMedia("(pointer: coarse)").matches,
      appH: de.style.getPropertyValue("--app-h"), barH: de.style.getPropertyValue("--mtabs-h"),
      barShown: getComputedStyle(document.getElementById("mtabs")).display !== "none",
    };
    if (isPhone) {
      // the tab bar's bell: a tap opens the popover, whose bottom place() measures from the layout viewport's bottom
      const bell = document.getElementById("mbell"), pop = document.getElementById("rbell-pop"), back = document.getElementById("rbell-back");
      const r = bell.getBoundingClientRect();
      bell.click();
      o.bell = { top: r.top, bottom: pop.style.bottom, open: !back.hidden,
                 fromInner: Math.max(8, window.innerHeight - r.top + 6) + "px", fromClient: Math.max(8, de.clientHeight - r.top + 6) + "px" };
    }
    return o;
  }, shell === "phone");
  out.errors = errors;
  await ctx.close();
  return out;
}

(async () => {
  let pw;
  try { pw = require("playwright"); } catch (e) { process.stdout.write(JSON.stringify({ skipped: "playwright is not installed: " + e.message })); return; }
  let browser;
  try { browser = await pw[browserName].launch(); }
  catch (e) { process.stdout.write(JSON.stringify({ skipped: String((e && e.message) || e).split("\n")[0] })); return; }
  try {
    const out = {};
    for (const shell of ["desktop", "phone"]) out[shell] = await walk(browser, shell);
    process.stdout.write(JSON.stringify(out));
  } finally { await browser.close(); }
})().catch((e) => { console.error((e && e.stack) || e); process.exit(1); });
