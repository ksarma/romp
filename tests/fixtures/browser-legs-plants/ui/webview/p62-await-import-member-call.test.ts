import { test } from "node:test";
test("p62", async (t) => { await (await import("./real-viewer-leg")).inBrowser(t, async () => {}); });
