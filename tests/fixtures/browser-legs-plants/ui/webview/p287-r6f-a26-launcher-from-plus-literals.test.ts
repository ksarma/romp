import { test } from "node:test";
const leg = require("./real-" + "viewer-leg");
test("a26 the launcher's name from two literals", async (t) => { await leg.inBrowser(t, async () => {}); });
