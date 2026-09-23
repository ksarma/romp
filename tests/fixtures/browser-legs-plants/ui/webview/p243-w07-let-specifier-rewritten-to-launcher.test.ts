import { test } from "node:test";
let spec = "./decoy-helper";
spec = "./real-viewer-leg";
const leg = require(spec);
test("p243", async (t) => { await leg.inBrowser(t, async () => {}); });
