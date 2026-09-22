import { test } from "node:test";
import { createRequire as cr } from "node:module";
const leg = cr(__filename)("./real-viewer-leg");
test("p171", async (t) => { await leg.inBrowser(t, async () => {}); });
