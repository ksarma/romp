import { test } from "node:test";
import { inBrowser } from "./real-viewer-leg";
import * as b from "./launcher-star-barrel";
test("p161", async (t) => { await inBrowser(t, async () => { const br = await b.requireCjs("playwright").webkit.launch(); await br.close(); }); });
