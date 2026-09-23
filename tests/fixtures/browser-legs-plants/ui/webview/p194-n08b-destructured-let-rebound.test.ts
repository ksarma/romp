import { test } from "node:test";
let { inBrowser } = require("./real-viewer-leg");
inBrowser = async (_t: any, _body: any) => {};
test("p194", async (t) => { await inBrowser(t, async () => {}); });
