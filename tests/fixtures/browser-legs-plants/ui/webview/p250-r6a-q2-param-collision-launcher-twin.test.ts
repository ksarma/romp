import { test } from "node:test";
const spec = "./decoy-helper";
const LEG = "./real-viewer-leg";
function load(spec: string): any { return require(spec); }
const leg = load(LEG);
test("p250", async (t) => { await leg.inBrowser(t, async () => {}, "firefox"); });
