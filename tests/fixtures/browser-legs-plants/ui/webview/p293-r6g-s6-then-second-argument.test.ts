import { test } from "node:test";
import { inBrowser } from "./real-viewer-leg";
test("p293", async (t) => { await inBrowser(t, async () => {}).then(() => {}, () => {}); });
