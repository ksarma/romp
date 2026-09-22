import { test } from "node:test";
const go = (r: any) => r("playwright").firefox.launch();
test("p120", async () => { const b = await go(require("./real-viewer-leg").requireCjs); await b.close(); });
