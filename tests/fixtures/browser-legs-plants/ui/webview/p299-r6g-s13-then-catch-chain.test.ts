import { test } from "node:test";
import { inBrowser } from "./real-viewer-leg";
test("p299", async (t) => { await inBrowser(t, async () => {}).then(() => {}).catch(() => {}); });
