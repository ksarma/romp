import { test } from "node:test";
let leg: any;
leg ??= require("./real-viewer-leg");
test("p192", async (t) => { await leg.inBrowser(t, async () => {}); });
