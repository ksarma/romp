import { test } from "node:test";
const p = import("./real-viewer-leg");
test("p88", async (t) => { const m = await p; await m.inBrowser(t, async () => {}); });
