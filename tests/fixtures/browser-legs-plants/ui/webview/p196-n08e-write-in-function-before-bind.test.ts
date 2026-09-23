import { test } from "node:test";
function reset(): void { leg = { inBrowser: async (_t: any, _body: any) => {} }; }
let leg: any = require("./real-viewer-leg");
test("p196", async (t) => { reset(); await leg.inBrowser(t, async () => {}); });
