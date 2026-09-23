import { test } from "node:test";
import { load } from "./plain-loader-helper";
const LEG = "./real-viewer-leg";
const leg = load(LEG);
test("p336", async (t) => { await leg.inBrowser(t, async () => {}, "firefox"); });
