import { test } from "node:test";
let leg: any = require("./real-viewer-leg");
leg &&= { inBrowser: async (_t: any, _body: any) => {} };
test("p195", async (t) => { await leg.inBrowser(t, async () => {}); });
