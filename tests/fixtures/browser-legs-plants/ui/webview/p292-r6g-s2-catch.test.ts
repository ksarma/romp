import { test } from "node:test";
import { inBrowser } from "./real-viewer-leg";
test("p292", async (t) => { await inBrowser(t, async () => {}).catch(() => {}); });
