import { test } from "node:test";
test("p49", async (t) => { await require("./real-viewer-leg").inBrowser(t, async () => {}); });
